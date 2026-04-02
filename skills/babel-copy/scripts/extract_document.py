#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from statistics import median

import fitz
import numpy as np
from PIL import Image
from translation_runtime import (
    TRANSLATION_PROVIDER_CHOICES,
    anthropic_model_name,
    claude_cli_flags,
    codex_model_name,
    detect_runtime_mode,
    translation_provider,
)

try:
    from syntok import segmenter as syntok_segmenter
except ImportError:
    syntok_segmenter = None

from core import (
    build_font_baseline,
    classify_page,
    clean_text,
    extract_native_regions,
    extract_ocr_regions,
    font_baseline_from_payload,
    infer_alignment,
    normalize_font_family_class,
    ocr_image_to_string,
    parse_page_selection,
    split_leading_marker,
)

_FRAGMENT_MERGE_LLM_CACHE: dict[str, bool] = {}


def region_style_signature(region) -> tuple[str, tuple[float, float, float]]:
    return (
        str(getattr(region, "render_font_name", "") or ""),
        tuple(
            round(float(value), 3)
            for value in getattr(region, "text_color", (0.0, 0.0, 0.0))
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract source text, blocks, and assets for babel-copy"
    )
    parser.add_argument("input_pdf")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--pages")
    parser.add_argument("--magnify-factor", type=float, default=2.0)
    parser.add_argument("--dpi", type=int, default=144)
    parser.add_argument(
        "--font-baseline", help="Visual fallback font family override: serif or sans."
    )
    parser.add_argument("--translation-provider", choices=TRANSLATION_PROVIDER_CHOICES)
    return parser.parse_args()


def merge_regions(regions):
    blocks = []
    current = None
    for index, region in enumerate(regions):
        rect = fitz.Rect(region.bbox)
        if current is None:
            current = {
                "regions": [region],
                "rect": rect,
                "align": region.align,
                "source": region.source,
                "style_signature": region_style_signature(region),
            }
            continue
        current_rect = current["rect"]
        same_align = region.align == current["align"]
        close_y = rect.y0 - current_rect.y1 < max(10, region.font_size_hint * 0.9)
        similar_x = abs(rect.x0 - current_rect.x0) < 18
        similar_style = (
            region.source != "native"
            or current["source"] != "native"
            or region_style_signature(region) == current["style_signature"]
        )
        next_region = regions[index + 1] if index + 1 < len(regions) else None
        force_break = (
            region.source == "native"
            and current["source"] == "native"
            and should_force_native_line_break(
                current["regions"][-1], region, next_region
            )
        )
        current_is_bullet_only = is_bullet_only_text(current["regions"][-1].text)
        region_is_bullet_only = is_bullet_only_text(region.text)
        mergeable_direction = not (region_is_bullet_only and not current_is_bullet_only)
        if (
            same_align
            and close_y
            and similar_x
            and similar_style
            and mergeable_direction
            and not force_break
        ):
            current["regions"].append(region)
            current["rect"] = current_rect | rect
        else:
            blocks.append(current)
            current = {
                "regions": [region],
                "rect": rect,
                "align": region.align,
                "source": region.source,
                "style_signature": region_style_signature(region),
            }
    if current is not None:
        blocks.append(current)
    return blocks


def role_for_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "artifact"
    if is_probable_artifact(stripped):
        return "artifact"
    if stripped.isupper() and len(stripped) > 4:
        return "heading"
    if re_match_lettered_heading(stripped):
        return "heading"
    marker, _ = split_leading_marker(stripped)
    if marker in {"o", "O", "•", "-", "*"}:
        return "list_item"
    if re_match_numbered(stripped):
        return "heading"
    return "paragraph"


def is_probable_artifact(text: str) -> bool:
    alpha_count = sum(ch.isalpha() for ch in text)
    digit_count = sum(ch.isdigit() for ch in text)
    weird_count = sum(
        not ch.isalnum() and not ch.isspace() and ch not in "•-–—()/:,.;&@+'\""
        for ch in text
    )
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if alpha_count == 0 and len(text) <= 8:
        return True
    if len(text) <= 4 and alpha_count <= 2 and not any(ch.islower() for ch in text):
        return True
    if len(text) <= 8 and digit_count == 0 and weird_count >= max(2, alpha_count):
        return True
    if (
        lines
        and all(len(line) <= 2 for line in lines)
        and sum(sum(ch.isalpha() for ch in line) for line in lines) <= 3
    ):
        return True
    return False


def re_match_numbered(text: str) -> bool:
    import re

    return bool(re.match(r"^[0-9IVX]+\b", text))


def re_match_lettered_heading(text: str) -> bool:
    import re

    return bool(re.match(r"^[A-Za-z]\.\s+\S", text))


def region_font_size(region) -> float:
    dominant = getattr(region, "dominant_font_size", None)
    if dominant is not None:
        return float(dominant)
    return float(getattr(region, "font_size_hint", 10.0) or 10.0)


def text_letter_counts(text: str) -> tuple[int, int]:
    upper = 0
    lower = 0
    for char in text:
        if not char.isalpha():
            continue
        if char.isupper():
            upper += 1
        elif char.islower():
            lower += 1
    return upper, lower


def is_label_like_line(text: str) -> bool:
    stripped = clean_text(text)
    if not stripped:
        return False
    upper, lower = text_letter_counts(stripped)
    alpha = upper + lower
    short = len(stripped) <= 48 and len(stripped.split()) <= 6
    if alpha == 0 or not short:
        return False
    if stripped.endswith(":") and upper >= lower:
        return True
    if stripped.isupper() and len(stripped) >= 4:
        return True
    if re_match_numbered(stripped) or re_match_lettered_heading(stripped):
        return upper >= lower
    return False


def is_body_like_line(text: str) -> bool:
    stripped = clean_text(text)
    if not stripped:
        return False
    upper, lower = text_letter_counts(stripped)
    if lower >= 2 and len(stripped) >= 24:
        return True
    return len(stripped.split()) >= 5 and lower >= 1


def should_force_native_line_break(
    previous_region, current_region, next_region=None
) -> bool:
    previous_text = clean_text(getattr(previous_region, "text", ""))
    current_text = clean_text(getattr(current_region, "text", ""))
    next_text = (
        clean_text(getattr(next_region, "text", "")) if next_region is not None else ""
    )
    if not previous_text or not current_text:
        return False

    prev_rect = fitz.Rect(previous_region.bbox)
    curr_rect = fitz.Rect(current_region.bbox)
    next_rect = fitz.Rect(next_region.bbox) if next_region is not None else None
    gap_before = float(curr_rect.y0 - prev_rect.y1)
    gap_after = float(next_rect.y0 - curr_rect.y1) if next_rect is not None else 0.0

    prev_size = region_font_size(previous_region)
    curr_size = region_font_size(current_region)
    next_size = region_font_size(next_region) if next_region is not None else curr_size
    size_contrast = (
        abs(curr_size - prev_size) >= 0.75 or abs(curr_size - next_size) >= 0.75
    )
    isolated = gap_before >= max(4.5, curr_size * 0.35) or gap_after >= max(
        4.5, curr_size * 0.35
    )

    if is_label_like_line(current_text):
        if is_body_like_line(previous_text) and (
            isolated
            or size_contrast
            or previous_text.endswith(":")
            or is_body_like_line(next_text)
        ):
            return True
        if previous_text.endswith(":") and (isolated or is_body_like_line(next_text)):
            return True

    if is_label_like_line(previous_text) and is_body_like_line(current_text):
        if (
            previous_text.endswith(":")
            or gap_before >= max(4.5, prev_size * 0.35)
            or size_contrast
        ):
            return True

    return False


def syntok_sentences(text: str) -> list[str]:
    if syntok_segmenter is None:
        return []
    stripped = clean_text(text)
    if not stripped:
        return []
    try:
        sentences: list[str] = []
        for paragraph in syntok_segmenter.process(stripped):
            for sentence in paragraph:
                values = [
                    token.value
                    for token in sentence
                    if getattr(token, "value", "").strip()
                ]
                if values:
                    sentences.append(" ".join(values))
        return sentences
    except Exception:
        return []


def syntok_prefers_merge(previous_text: str, current_text: str) -> bool:
    if syntok_segmenter is None:
        return False
    current_clean = clean_text(current_text)
    if not current_clean or is_label_like_line(current_clean):
        return False
    combined = clean_text(f"{previous_text} {current_clean}")
    sentences = syntok_sentences(combined)
    if len(sentences) != 1:
        return False
    if current_clean[:1].islower():
        return True
    if previous_text.endswith((",", "(", "/", "-")):
        return True
    previous_last_word = clean_text(previous_text).split()[-1].lower()
    return previous_last_word in {
        "de",
        "du",
        "des",
        "le",
        "la",
        "les",
        "d",
        "et",
        "of",
        "the",
        "and",
        "to",
        "for",
    }


def groups_from_indices(values: list[int], max_gap: int = 1) -> list[tuple[int, int]]:
    groups: list[tuple[int, int]] = []
    if not values:
        return groups
    start = prev = values[0]
    for value in values[1:]:
        if value <= prev + max_gap:
            prev = value
            continue
        groups.append((start, prev))
        start = prev = value
    groups.append((start, prev))
    return groups


def page_pt_to_px(value: float, page_extent: float, image_extent: int) -> int:
    if page_extent <= 0:
        return 0
    return int(round(value * image_extent / page_extent))


def page_px_to_pt(value: float, image_extent: int, page_extent: float) -> float:
    if image_extent <= 0:
        return 0.0
    return value * page_extent / image_extent


def rect_to_list(rect: fitz.Rect) -> list[float]:
    return [round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)]


def block_text_from_regions(regions) -> str:
    parts: list[str] = []
    index = 0
    while index < len(regions):
        region = regions[index]
        text = clean_text(region.text)
        if not text:
            index += 1
            continue
        if is_bullet_only_text(text) and index + 1 < len(regions):
            next_region = regions[index + 1]
            next_text = clean_text(next_region.text)
            same_line = abs(float(region.bbox[1]) - float(next_region.bbox[1])) <= 3.5
            indented_right = float(next_region.bbox[0]) >= float(region.bbox[2]) - 2.0
            if next_text and same_line and indented_right:
                parts.append(f"{text} {next_text}".strip())
                index += 2
                continue
        parts.append(text)
        index += 1
    return clean_text("\n".join(parts))


def line_payload(region) -> dict:
    return {
        "bbox": rect_to_list(fitz.Rect(region.bbox)),
        "span_styles": [dict(span) for span in region.span_styles],
        "dominant_font_size": round(float(region.dominant_font_size), 2)
        if region.dominant_font_size is not None
        else None,
        "max_font_size": round(float(region.max_font_size), 2)
        if region.max_font_size is not None
        else None,
        "baseline_y": round(float(region.baseline_y), 2)
        if region.baseline_y is not None
        else None,
    }


def is_bullet_only_text(text: str) -> bool:
    compact = clean_text(text).replace(" ", "")
    return compact in {"•", "-", "*", "o"}


def is_marker_artifact_text(text: str) -> bool:
    compact = clean_text(text).replace(" ", "")
    if not compact:
        return False
    if "•" in compact:
        return True
    return len(compact) <= 3 and all(not ch.isalnum() for ch in compact)


def dominant_style_value(native_lines: list[dict], key: str):
    weights: dict[object, int] = defaultdict(int)
    for line in native_lines:
        for span in line.get("span_styles", []):
            if not isinstance(span, dict):
                continue
            value = span.get(key)
            char_count = int(span.get("char_count", 0) or 0)
            if value in ("", None) or char_count <= 0:
                continue
            weights[value] += char_count
    if not weights:
        return None
    return max(weights.items(), key=lambda item: (item[1], str(item[0])))[0]


def block_native_style_signature(block: dict) -> tuple[object, object, object] | None:
    native_lines = block.get("_native_lines", [])
    if not native_lines:
        return None
    return (
        dominant_style_value(native_lines, "font_name"),
        dominant_style_value(native_lines, "flags"),
        dominant_style_value(native_lines, "color"),
    )


def color_to_hex(value) -> str | None:
    if value is None:
        return None
    return f"#{int(value) & 0xFFFFFF:06X}"


def block_font_size_hint(block: dict) -> float:
    native_lines = block.get("_native_lines", [])
    if native_lines:
        dominant_sizes = [
            float(line["dominant_font_size"])
            for line in native_lines
            if line.get("dominant_font_size") is not None
        ]
        max_sizes = [
            float(line["max_font_size"])
            for line in native_lines
            if line.get("max_font_size") is not None
        ]
        role = str(block.get("role", ""))
        if role in {"heading", "title", "form_label"}:
            candidates = max_sizes or dominant_sizes
            if candidates:
                return round(max(candidates), 2)
        candidates = dominant_sizes or max_sizes
        if candidates:
            return round(median(candidates), 2)
    hints = [
        float(value) for value in block.get("_font_size_hints", []) if value is not None
    ]
    if hints:
        return round(sum(hints) / len(hints), 2)
    return float(block.get("style", {}).get("font_size_hint", 10.0))


def summarize_block_style(block: dict) -> dict:
    existing = dict(block.get("style", {}))
    native_lines = block.get("_native_lines", [])
    font_name = (
        dominant_style_value(native_lines, "font_name") if native_lines else None
    )
    flags = dominant_style_value(native_lines, "flags") if native_lines else None
    color = dominant_style_value(native_lines, "color") if native_lines else None
    return {
        "font_size_hint": block_font_size_hint(block),
        "font_name": font_name,
        "flags": int(flags) if flags is not None else None,
        "color": int(color) if color is not None else None,
        "text_fill_color": color_to_hex(color),
        "bold": bool(existing.get("bold", False)),
        "italic": bool(existing.get("italic", False)),
    }


def block_alignment_from_native_lines(block: dict, page_rect: fitz.Rect) -> str:
    native_lines = block.get("_native_lines", [])
    rect = fitz.Rect(block["bbox"])
    role = str(block.get("role", ""))
    text = clean_text(str(block.get("text", "")))
    line_count = block_line_count(block)
    text_length = len(text)
    centered = (
        abs((rect.x0 + rect.x1) / 2 - (page_rect.width / 2)) < page_rect.width * 0.06
    )
    narrow = rect.width < page_rect.width * 0.55

    if role == "paragraph":
        if centered and narrow and line_count == 1 and text_length <= 28:
            return "center"
        if rect.x1 > page_rect.width * 0.85 and rect.width < page_rect.width * 0.4:
            return "right"
        if line_count >= 2:
            return "left"
        if rect.width >= page_rect.width * 0.32 and text_length >= 36:
            return "left"
        return "left"

    if len(native_lines) < 2:
        if (
            role == "paragraph"
            and rect.x0 <= page_rect.width * 0.16
            and rect.x1 >= page_rect.width * 0.72
            and rect.width >= page_rect.width * 0.55
        ):
            return "left"
        return infer_alignment(rect, page_rect)

    x0s = [float(line["bbox"][0]) for line in native_lines]
    x1s = [float(line["bbox"][2]) for line in native_lines]
    centers = [(x0 + x1) / 2 for x0, x1 in zip(x0s, x1s)]

    left_spread = max(x0s) - min(x0s)
    right_spread = max(x1s) - min(x1s)
    center_spread = max(centers) - min(centers)
    stable_threshold = max(4.0, page_rect.width * 0.01)
    dominance_ratio = 1.35

    if (
        left_spread <= stable_threshold
        and left_spread * dominance_ratio <= right_spread
        and left_spread * dominance_ratio <= center_spread
    ):
        return "left"
    if (
        right_spread <= stable_threshold
        and right_spread * dominance_ratio <= left_spread
        and right_spread * dominance_ratio <= center_spread
    ):
        return "right"
    if (
        center_spread <= stable_threshold
        and center_spread * dominance_ratio <= left_spread
        and center_spread * dominance_ratio <= right_spread
    ):
        return "center"

    return infer_alignment(fitz.Rect(block["bbox"]), page_rect)


def block_render_baseline(block: dict) -> float | None:
    native_lines = block.get("_native_lines", [])
    if len(native_lines) != 1:
        return None
    baseline_y = native_lines[0].get("baseline_y")
    if baseline_y is None:
        return None
    return round(float(baseline_y), 2)


def normalized_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÀ-ÿ0-9]+", clean_text(text).lower())


def suffix_prefix_word_overlap(left: str, right: str, max_words: int = 6) -> int:
    left_words = normalized_words(left)
    right_words = normalized_words(right)
    limit = min(max_words, len(left_words), len(right_words))
    for size in range(limit, 1, -1):
        if left_words[-size:] == right_words[:size]:
            return size
    return 0


def trim_duplicate_prefix(current_text: str, previous_text: str) -> str:
    overlap = suffix_prefix_word_overlap(previous_text, current_text)
    if overlap <= 1:
        return current_text
    current_words = clean_text(current_text).split()
    if overlap >= len(current_words):
        return current_text
    trimmed = " ".join(current_words[overlap:]).strip()
    return trimmed or current_text


def block_line_count(block: dict) -> int:
    return max(
        1,
        len([line for line in str(block.get("text", "")).splitlines() if line.strip()]),
    )


def block_is_ocr(block: dict) -> bool:
    return str(block.get("source", "")).startswith("ocr")


def block_looks_like_toc_entry(block: dict) -> bool:
    text = clean_text(str(block.get("text", "")))
    if not text:
        return False
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    matched = 0
    for line in lines:
        has_page_no = bool(re.search(r"(?:\.{2,}\s*|\s)\d{1,3}$", line))
        numbered = bool(re.match(r"^(?:\d+(?:\.\d+)*|[A-Za-z]\.)\b", line))
        if has_page_no and numbered:
            matched += 1
    return matched >= 1 and matched >= max(1, len(lines) // 2)


def page_has_toc_title(page_blocks: list[dict]) -> bool:
    toc_titles = {"table des matières", "table of contents"}
    for block in page_blocks:
        if clean_text(str(block.get("text", ""))).strip().lower() in toc_titles:
            return True
    return False


def block_alignment_from_ocr_layout(
    block: dict, page_blocks: list[dict], page_rect: fitz.Rect, toc_page: bool
) -> str:
    rect = fitz.Rect(block["bbox"])
    role = str(block.get("role", ""))
    text = clean_text(str(block.get("text", "")))
    line_count = block_line_count(block)
    text_length = len(text)

    if block.get("table") or role == "table_cell":
        return "left"
    if "|" in text:
        return "left"
    if role == "list_item":
        return "left"
    if toc_page and block_looks_like_toc_entry(block):
        return "left"
    if role in {"header", "footer"}:
        return infer_alignment(rect, page_rect)

    centered = (
        abs((rect.x0 + rect.x1) / 2 - (page_rect.width / 2)) < page_rect.width * 0.06
    )
    narrow = rect.width < page_rect.width * 0.55

    if role in {"heading", "title", "form_label"}:
        if toc_page:
            return "left"
        if centered and narrow and line_count <= 2:
            return "center"
        if rect.x1 > page_rect.width * 0.85 and rect.width < page_rect.width * 0.4:
            return "right"
        return "left"

    if role == "paragraph":
        if centered and narrow and line_count == 1 and text_length <= 28:
            return "center"
        if rect.x1 > page_rect.width * 0.85 and rect.width < page_rect.width * 0.4:
            return "right"
        if line_count >= 2:
            return "left"
        if rect.width >= page_rect.width * 0.32 and text_length >= 36:
            return "left"
        return "left"

    return infer_alignment(rect, page_rect)


def finalize_block_layout(page_blocks: list[dict], page_rect: fitz.Rect) -> None:
    toc_page = page_has_toc_title(page_blocks)
    for block in page_blocks:
        if block.get("_force_left_align") or block.get("role") == "list_item":
            block["align"] = "left"
        elif block_is_ocr(block):
            block["align"] = block_alignment_from_ocr_layout(
                block, page_blocks, page_rect, toc_page
            )
        elif block.get("source") == "native":
            block["align"] = block_alignment_from_native_lines(block, page_rect)
        render_baseline_y = block_render_baseline(block)
        if render_baseline_y is None:
            block.pop("_render_baseline_y", None)
        else:
            block["_render_baseline_y"] = render_baseline_y
        block["style"] = summarize_block_style(block)
        block.pop("_force_left_align", None)
        block.pop("_native_lines", None)
        block.pop("_font_size_hints", None)


def classify_asset_kind(rect: fitz.Rect, page_rect: fitz.Rect) -> str:
    area_ratio = rect.get_area() / (page_rect.get_area() or 1.0)
    if area_ratio >= 0.85:
        return "page_image"
    if area_ratio >= 0.12:
        return "composite_region"
    if area_ratio <= 0.01 and rect.y0 >= page_rect.height * 0.55:
        return "handwritten_mark"
    return "embedded_image"


def export_page_assets(
    page: fitz.Page, page_number: int, assets_dir: Path
) -> list[dict]:
    exported: list[dict] = []
    for image_index, image in enumerate(page.get_images(full=True)):
        rects = page.get_image_rects(image[0])
        for rect_index, rect in enumerate(rects):
            clipped = page.get_pixmap(clip=rect, dpi=150, alpha=False)
            asset_path = (
                assets_dir
                / f"page-{page_number:03d}-image-{image_index:02d}-{rect_index:02d}.png"
            )
            asset_path.write_bytes(clipped.tobytes("png"))
            exported.append(
                {
                    "id": f"p{page_number}-a{len(exported) + 1}",
                    "page_number": page_number,
                    "kind": classify_asset_kind(rect, page.rect),
                    "origin": "embedded_image",
                    "bbox": rect_to_list(rect),
                    "path": str(asset_path),
                    "image_size_px": [clipped.width, clipped.height],
                }
            )
    return exported


def detect_tables(render_path: Path, page_rect: fitz.Rect) -> list[dict]:
    image = Image.open(render_path).convert("L")
    array = np.array(image)
    dark = array < 190
    height, width = array.shape

    def longest_dark_runs(mask: np.ndarray, axis: int) -> np.ndarray:
        if axis == 0:
            runs = np.zeros(mask.shape[1], dtype=int)
            for column in range(mask.shape[1]):
                current = best = 0
                for value in mask[:, column]:
                    if value:
                        current += 1
                        if current > best:
                            best = current
                    else:
                        current = 0
                runs[column] = best
            return runs
        runs = np.zeros(mask.shape[0], dtype=int)
        for row in range(mask.shape[0]):
            current = best = 0
            for value in mask[row, :]:
                if value:
                    current += 1
                    if current > best:
                        best = current
                else:
                    current = 0
            runs[row] = best
        return runs

    vertical_runs = longest_dark_runs(dark, axis=0)
    vertical_threshold = max(42, int(height * 0.06))
    vertical_indices = [
        idx for idx, run in enumerate(vertical_runs) if run >= vertical_threshold
    ]
    vertical_groups = groups_from_indices(vertical_indices, max_gap=2)
    if len(vertical_groups) < 3:
        return []

    centers = [(group[0] + group[1]) / 2 for group in vertical_groups]
    clusters: list[list[tuple[int, int]]] = []
    current_cluster: list[tuple[int, int]] = []
    for index, group in enumerate(vertical_groups):
        if not current_cluster:
            current_cluster.append(group)
            continue
        prev_center = centers[index - 1]
        center = centers[index]
        if center - prev_center <= width * 0.22:
            current_cluster.append(group)
            continue
        if len(current_cluster) >= 3:
            clusters.append(current_cluster)
        current_cluster = [group]
    if len(current_cluster) >= 3:
        clusters.append(current_cluster)

    table_candidates: list[dict] = []
    for cluster in clusters:
        columns_px = [(group[0] + group[1]) / 2 for group in cluster]
        if len(columns_px) < 3:
            continue
        x0 = max(0, int(round(columns_px[0] + 1)))
        x1 = min(width, int(round(columns_px[-1] - 1)))
        if x1 - x0 < width * 0.22:
            continue
        sub_dark = dark[:, x0:x1]
        horizontal_runs = longest_dark_runs(sub_dark, axis=1)
        horizontal_threshold = max(54, int((x1 - x0) * 0.45))
        horizontal_indices = [
            idx
            for idx, run in enumerate(horizontal_runs)
            if run >= horizontal_threshold
        ]
        horizontal_groups = groups_from_indices(horizontal_indices, max_gap=2)
        if len(horizontal_groups) < 3:
            continue
        rows_px = [(group[0] + group[1]) / 2 for group in horizontal_groups]
        if len(columns_px) > 10 or len(rows_px) > 12:
            continue
        table_candidates.append(
            {
                "columns": columns_px,
                "rows": rows_px,
                "bbox": [columns_px[0], rows_px[0], columns_px[-1], rows_px[-1]],
                "score": (len(columns_px) - 1) * (len(rows_px) - 1),
            }
        )

    if not table_candidates:
        return []

    best = max(
        table_candidates,
        key=lambda item: (item["score"], item["bbox"][2] - item["bbox"][0]),
    )
    columns_pt = [
        round(page_px_to_pt(value, width, page_rect.width), 2)
        for value in best["columns"]
    ]
    rows_pt = [
        round(page_px_to_pt(value, height, page_rect.height), 2)
        for value in best["rows"]
    ]
    return [
        {
            "id": "table-1",
            "bbox": [columns_pt[0], rows_pt[0], columns_pt[-1], rows_pt[-1]],
            "columns": columns_pt,
            "rows": rows_pt,
        }
    ]


def build_table_cells(page_number: int, table: dict) -> list[dict]:
    cells = []
    columns = table["columns"]
    rows = table["rows"]
    for row_index in range(len(rows) - 1):
        for col_index in range(len(columns) - 1):
            bbox = [
                columns[col_index],
                rows[row_index],
                columns[col_index + 1],
                rows[row_index + 1],
            ]
            cells.append(
                {
                    "id": f"p{page_number}-t{table['id']}-r{row_index}-c{col_index}",
                    "row_index": row_index,
                    "col_index": col_index,
                    "bbox": bbox,
                    "block_ids": [],
                    "signature_asset_ids": [],
                }
            )
    return cells


def merge_paragraph_fragments(
    page_blocks: list[dict], llm_decisions: set[tuple[str, str]] | None = None
) -> list[dict]:
    if not page_blocks:
        return page_blocks
    llm_decisions = llm_decisions or set()
    ordered = sorted(page_blocks, key=lambda item: (item["bbox"][1], item["bbox"][0]))
    merged: list[dict] = []
    for block in ordered:
        if not merged:
            merged.append(block)
            continue
        previous = merged[-1]
        if (
            should_merge_fragment(previous, block)
            or (str(previous["id"]), str(block["id"])) in llm_decisions
        ):
            previous["text"] = clean_text(f"{previous['text']}\n{block['text']}")
            previous["bbox"] = [
                round(min(previous["bbox"][0], block["bbox"][0]), 2),
                round(min(previous["bbox"][1], block["bbox"][1]), 2),
                round(max(previous["bbox"][2], block["bbox"][2]), 2),
                round(max(previous["bbox"][3], block["bbox"][3]), 2),
            ]
            previous["role"] = role_for_text(previous["text"])
            previous["style"]["bold"] = False
            previous.setdefault("_font_size_hints", []).extend(
                block.get("_font_size_hints", [])
            )
            previous.setdefault("_native_lines", []).extend(
                block.get("_native_lines", [])
            )
            continue
        merged.append(block)
    return merged


def attach_leading_bullets(page_blocks: list[dict]) -> list[dict]:
    if not page_blocks:
        return page_blocks
    ordered = sorted(page_blocks, key=lambda item: (item["bbox"][1], item["bbox"][0]))
    merged: list[dict] = []
    index = 0
    while index < len(ordered):
        block = ordered[index]
        text = str(block.get("text", "")).strip()
        if is_bullet_only_text(text):
            candidates = []
            if merged:
                candidates.append(merged[-1])
            if index + 1 < len(ordered):
                candidates.append(ordered[index + 1])
            target = None
            for candidate in candidates:
                same_line = (
                    abs(float(block["bbox"][1]) - float(candidate["bbox"][1])) <= 3.5
                )
                indented_right = (
                    float(candidate["bbox"][0]) >= float(block["bbox"][2]) - 2.0
                )
                if same_line and indented_right and not candidate.get("table"):
                    target = candidate
                    break
            if target is not None:
                bullet = clean_text(text) or "•"
                target_text = clean_text(str(target.get("text", "")))
                target["text"] = f"{bullet} {target_text}".strip()
                target["bbox"] = [
                    round(min(float(block["bbox"][0]), float(target["bbox"][0])), 2),
                    round(min(float(block["bbox"][1]), float(target["bbox"][1])), 2),
                    round(max(float(block["bbox"][2]), float(target["bbox"][2])), 2),
                    round(max(float(block["bbox"][3]), float(target["bbox"][3])), 2),
                ]
                target["role"] = "list_item"
                target.setdefault("_font_size_hints", []).extend(
                    block.get("_font_size_hints", [])
                )
                target.setdefault("_native_lines", []).extend(
                    block.get("_native_lines", [])
                )
                index += 1
                continue
        merged.append(block)
        index += 1
    return merged


def mark_list_items_from_marker_artifacts(page_blocks: list[dict]) -> None:
    ordered = sorted(page_blocks, key=lambda item: (item["bbox"][1], item["bbox"][0]))
    for index, block in enumerate(ordered):
        if block.get("role") != "artifact":
            continue
        if not is_marker_artifact_text(str(block.get("text", ""))):
            continue
        for candidate in ordered[index + 1 :]:
            same_line = (
                abs(float(block["bbox"][1]) - float(candidate["bbox"][1])) <= 4.0
            )
            if not same_line:
                if float(candidate["bbox"][1]) > float(block["bbox"][3]) + 6.0:
                    break
                continue
            if candidate.get("role") == "artifact" or candidate.get("table"):
                continue
            if float(candidate["bbox"][0]) < float(block["bbox"][2]) - 2.0:
                continue
            candidate["role"] = "list_item"
            break


def mark_two_column_rows(page_blocks: list[dict]) -> None:
    ordered = sorted(page_blocks, key=lambda item: (item["bbox"][1], item["bbox"][0]))
    for index, left in enumerate(ordered):
        if left.get("role") == "artifact" or left.get("table"):
            continue
        peers = [left]
        for right in ordered[index + 1 :]:
            same_line = abs(float(left["bbox"][1]) - float(right["bbox"][1])) <= 2.5
            if not same_line:
                if float(right["bbox"][1]) > float(left["bbox"][3]) + 4.0:
                    break
                continue
            if right.get("role") == "artifact" or right.get("table"):
                continue
            gap = float(right["bbox"][0]) - float(peers[-1]["bbox"][2])
            if gap < 10:
                continue
            peers.append(right)
        if len(peers) < 2:
            continue
        for block in peers:
            block["_force_left_align"] = True


def mark_textual_table_like_rows(page_blocks: list[dict]) -> None:
    table_like_blocks = [
        block
        for block in page_blocks
        if block_is_ocr(block) and "|" in str(block.get("text", ""))
    ]
    if len(table_like_blocks) < 2:
        return
    for block in table_like_blocks:
        block["role"] = "table_cell"
        block["_force_left_align"] = True


def block_x_overlap_ratio(left: dict, right: dict) -> float:
    left_rect = fitz.Rect(left["bbox"])
    right_rect = fitz.Rect(right["bbox"])
    overlap = min(left_rect.x1, right_rect.x1) - max(left_rect.x0, right_rect.x0)
    if overlap <= 0:
        return 0.0
    return overlap / max(1.0, min(left_rect.width, right_rect.width))


def build_textual_tables(page_number: int, page_blocks: list[dict]) -> list[dict]:
    candidates = [
        block
        for block in sorted(
            page_blocks, key=lambda item: (item["bbox"][1], item["bbox"][0])
        )
        if block_is_ocr(block)
        and (block.get("role") == "table_cell" or "|" in str(block.get("text", "")))
    ]
    if len(candidates) < 2:
        return []

    clusters: list[list[dict]] = []
    current_cluster: list[dict] = []
    for block in candidates:
        if not current_cluster:
            current_cluster = [block]
            continue
        previous = current_cluster[-1]
        gap = float(block["bbox"][1]) - float(previous["bbox"][3])
        if gap <= 36.0 and block_x_overlap_ratio(previous, block) >= 0.45:
            current_cluster.append(block)
            continue
        if len(current_cluster) >= 2:
            clusters.append(current_cluster)
        current_cluster = [block]
    if len(current_cluster) >= 2:
        clusters.append(current_cluster)

    tables: list[dict] = []
    for index, cluster in enumerate(clusters, 1):
        cluster = sorted(cluster, key=lambda item: (item["bbox"][1], item["bbox"][0]))
        x0 = round(min(float(block["bbox"][0]) for block in cluster), 2)
        x1 = round(max(float(block["bbox"][2]) for block in cluster), 2)
        if x1 - x0 < 140:
            continue
        row_edges = [round(float(cluster[0]["bbox"][1]), 2)]
        for previous, current in zip(cluster, cluster[1:]):
            boundary = (float(previous["bbox"][3]) + float(current["bbox"][1])) / 2
            row_edges.append(round(boundary, 2))
        row_edges.append(round(float(cluster[-1]["bbox"][3]), 2))
        tables.append(
            {
                "id": f"text-table-{index}",
                "bbox": [x0, row_edges[0], x1, row_edges[-1]],
                "columns": [x0, x1],
                "rows": row_edges,
            }
        )
    return tables


def block_visual_x0(block: dict) -> float:
    wide_native_lines = [
        float(line["bbox"][0])
        for line in block.get("_native_lines", [])
        if float(line["bbox"][2]) - float(line["bbox"][0]) >= 14.0
    ]
    if wide_native_lines:
        return min(wide_native_lines)
    return float(block["bbox"][0])


def block_visual_x1(block: dict) -> float:
    wide_native_lines = [
        float(line["bbox"][2])
        for line in block.get("_native_lines", [])
        if float(line["bbox"][2]) - float(line["bbox"][0]) >= 14.0
    ]
    if wide_native_lines:
        return max(wide_native_lines)
    return float(block["bbox"][2])


def inline_merge_text(blocks: list[dict]) -> str:
    marker = None
    parts: list[str] = []
    for block in blocks:
        text = clean_text(str(block.get("text", "")))
        if not text:
            continue
        part_marker, remainder = split_leading_marker(text)
        if part_marker and marker is None:
            marker = part_marker
        payload = remainder if part_marker else text
        payload = payload.strip()
        if payload:
            parts.append(payload)
    merged = clean_text(" ".join(parts))
    if marker:
        return clean_text(f"{marker} {merged}".strip())
    return merged


def can_merge_inline_block(block: dict) -> bool:
    if block.get("table"):
        return False
    if block.get("role") in {"header", "footer"}:
        return False
    text = clean_text(str(block.get("text", "")))
    if not text:
        return False
    if block.get("keep_original"):
        return text in {":", ";", ","}
    return True


def should_merge_inline_sequence(blocks: list[dict]) -> bool:
    if len(blocks) < 2:
        return False
    texts = [clean_text(str(block.get("text", ""))) for block in blocks]
    marker_count = sum(1 for text in texts if split_leading_marker(text)[0])
    punctuation_count = sum(1 for text in texts if clean_text(text) in {":", ";", ","})
    word_like_count = sum(1 for text in texts if any(ch.isalnum() for ch in text))
    return marker_count > 0 or punctuation_count > 0 or word_like_count >= 3


def merge_inline_sequence(blocks: list[dict]) -> dict:
    merged = dict(blocks[0])
    merged["text"] = inline_merge_text(blocks)
    merged["bbox"] = [
        round(min(float(block["bbox"][0]) for block in blocks), 2),
        round(min(float(block["bbox"][1]) for block in blocks), 2),
        round(max(float(block["bbox"][2]) for block in blocks), 2),
        round(max(float(block["bbox"][3]) for block in blocks), 2),
    ]
    merged["role"] = role_for_text(merged["text"])
    merged["keep_original"] = False
    merged["_font_size_hints"] = [
        float(value) for block in blocks for value in block.get("_font_size_hints", [])
    ]
    merged["_native_lines"] = [
        line for block in blocks for line in block.get("_native_lines", [])
    ]
    merged["style"] = dict(merged.get("style", {}))
    merged["style"]["bold"] = any(
        bool(block.get("style", {}).get("bold")) for block in blocks
    )
    return merged


def merge_inline_row_fragments(page_blocks: list[dict]) -> list[dict]:
    if not page_blocks:
        return page_blocks
    ordered = sorted(
        page_blocks,
        key=lambda item: (
            round(float(item["bbox"][1]), 2),
            block_visual_x0(item),
            float(item["bbox"][0]),
        ),
    )
    merged_rows: list[dict] = []
    row: list[dict] = []
    row_y = None

    def flush_row(items: list[dict]) -> None:
        if not items:
            return
        visual_order = sorted(
            items,
            key=lambda item: (
                block_visual_x0(item),
                float(item["bbox"][0]),
                float(item["bbox"][2]),
            ),
        )
        index = 0
        while index < len(visual_order):
            current = visual_order[index]
            if not can_merge_inline_block(current):
                merged_rows.append(current)
                index += 1
                continue
            sequence = [current]
            prev_visual_x1 = block_visual_x1(current)
            lookahead = index + 1
            while lookahead < len(visual_order):
                candidate = visual_order[lookahead]
                if not can_merge_inline_block(candidate):
                    break
                gap = block_visual_x0(candidate) - prev_visual_x1
                if gap < -3.0 or gap > 24.0:
                    break
                sequence.append(candidate)
                prev_visual_x1 = block_visual_x1(candidate)
                lookahead += 1
            if should_merge_inline_sequence(sequence):
                merged_rows.append(merge_inline_sequence(sequence))
            else:
                merged_rows.extend(sequence)
            index = lookahead

    for block in ordered:
        block_y = float(block["bbox"][1])
        if row and row_y is not None and abs(block_y - row_y) > 2.5:
            flush_row(row)
            row = []
            row_y = None
        row.append(block)
        if row_y is None:
            row_y = block_y
        else:
            row_y = min(row_y, block_y)
    flush_row(row)
    return merged_rows


def should_merge_fragment(previous: dict, current: dict) -> bool:
    if previous.get("table") or current.get("table"):
        return False
    if previous.get("role") == "artifact" or current.get("role") == "artifact":
        return False
    gap = float(current["bbox"][1]) - float(previous["bbox"][3])
    if gap < -6 or gap > 18:
        return False
    previous_text = str(previous.get("text", "")).strip()
    current_text = str(current.get("text", "")).strip()
    if not previous_text or not current_text:
        return False
    previous_style = block_native_style_signature(previous)
    current_style = block_native_style_signature(current)
    if (
        previous_style is not None
        and current_style is not None
        and previous_style != current_style
    ):
        return False
    if block_is_ocr(previous) and block_is_ocr(current):
        previous_rect = fitz.Rect(previous["bbox"])
        current_rect = fitz.Rect(current["bbox"])
        if (
            ("|" in previous_text or previous.get("role") == "table_cell")
            and gap <= 16
            and current_rect.x0 >= previous_rect.x0 + 12
            and current_rect.x1 <= previous_rect.x1 + 10
        ):
            return True
        if (
            str(previous.get("role")) == "paragraph"
            and str(current.get("role")) == "paragraph"
            and gap <= 12
            and (
                abs(current_rect.x0 - previous_rect.x0) <= 10
                or (
                    current_rect.x0 >= previous_rect.x0 + 18
                    and current_rect.x1 <= previous_rect.x1 + 6
                )
            )
        ):
            if previous_text[-1:].isalnum() and current_text[:1].islower():
                return True
            if "|" in previous_text or "|" in current_text:
                return True
            if (
                previous_rect.width >= current_rect.width * 1.25
                and len(current_text) <= 96
            ):
                return True
    if abs(float(current["bbox"][0]) - float(previous["bbox"][0])) > 24:
        return False
    if is_bullet_only_text(current_text):
        return False
    if previous_text.endswith((".", ":", ";", "!", "?")):
        return False
    previous_last_word = previous_text.split()[-1].lower()
    bridge_words = {
        "de",
        "du",
        "des",
        "le",
        "la",
        "les",
        "d",
        "et",
        "of",
        "the",
        "and",
        "to",
        "for",
    }
    if previous_last_word in bridge_words:
        return True
    if syntok_prefers_merge(previous_text, current_text):
        return True
    if len(current_text) <= 32 and (current_text.isupper() or " " not in current_text):
        return True
    return False


def llm_fragment_merge_enabled() -> bool:
    value = os.environ.get("BABEL_COPY_ENABLE_LLM_FRAGMENT_MERGE", "1").strip().lower()
    return value in {"1", "true", "yes", "on"}


def fragment_merge_cache_key(previous: dict, current: dict) -> str:
    payload = {
        "previous_text": clean_text(str(previous.get("text", ""))),
        "current_text": clean_text(str(current.get("text", ""))),
        "previous_role": str(previous.get("role", "")),
        "current_role": str(current.get("role", "")),
        "previous_bbox": [round(float(value), 2) for value in previous.get("bbox", [])],
        "current_bbox": [round(float(value), 2) for value in current.get("bbox", [])],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def text_is_merge_artifact_candidate(text: str) -> bool:
    stripped = clean_text(text)
    if not stripped:
        return False
    if is_probable_artifact(stripped):
        return False
    alpha_count = sum(ch.isalpha() for ch in stripped)
    weird_count = sum(
        not ch.isalnum() and not ch.isspace() and ch not in "•-–—()/:,.;&@+'\""
        for ch in stripped
    )
    if alpha_count <= 2 and weird_count >= max(2, alpha_count):
        return False
    return True


def is_ambiguous_fragment_pair(previous: dict, current: dict) -> bool:
    if previous.get("table") or current.get("table"):
        return False
    if previous.get("role") == "artifact" or current.get("role") == "artifact":
        return False
    previous_text = clean_text(str(previous.get("text", "")))
    current_text = clean_text(str(current.get("text", "")))
    if not text_is_merge_artifact_candidate(
        previous_text
    ) or not text_is_merge_artifact_candidate(current_text):
        return False
    gap = float(current["bbox"][1]) - float(previous["bbox"][3])
    if gap < -6 or gap > 14:
        return False
    previous_rect = fitz.Rect(previous["bbox"])
    current_rect = fitz.Rect(current["bbox"])
    if abs(current_rect.x0 - previous_rect.x0) > 36 and not (
        current_rect.x0 >= previous_rect.x0 + 12
        and current_rect.x1 <= previous_rect.x1 + 10
    ):
        return False
    previous_role = str(previous.get("role", ""))
    current_role = str(current.get("role", ""))
    if {previous_role, current_role} - {"paragraph", "heading"}:
        return False
    if previous_text.endswith((".", "!", "?")):
        return False
    if current_text[:1].islower():
        return True
    if syntok_prefers_merge(previous_text, current_text):
        return True
    if current_role == "heading" and len(current_text) <= 96:
        return True
    if len(current_text) <= 96 and (
        current_text.isupper()
        or "\n" in str(current.get("text", ""))
        or previous_text.split()[-1].lower()
        in {
            "de",
            "du",
            "des",
            "le",
            "la",
            "les",
            "d",
            "et",
            "of",
            "the",
            "and",
            "to",
            "for",
        }
    ):
        return True
    return False


def codex_fragment_merge_model() -> str | None:
    value = os.environ.get("BABEL_COPY_FRAGMENT_MERGE_MODEL", "").strip()
    return value or None


def fragment_merge_model(runtime_mode: str) -> str | None:
    explicit = codex_fragment_merge_model()
    if explicit:
        return explicit
    if runtime_mode == "claude":
        return anthropic_model_name(None)
    model = codex_model_name(None)
    return None if model == "default" else model


def build_fragment_merge_prompt(candidates: list[dict]) -> str:
    payload = []
    for item in candidates:
        payload.append(
            {
                "pair_id": item["pair_id"],
                "page_number": item["page_number"],
                "previous_role": item["previous_role"],
                "current_role": item["current_role"],
                "vertical_gap": item["vertical_gap"],
                "previous_text": item["previous_text"],
                "current_text": item["current_text"],
            }
        )
    return f"""Decide whether each adjacent document fragment pair should be merged into a single paragraph or heading block.

Rules:
- Return JSON only.
- Answer "yes" only when the current fragment is clearly a continuation of the previous fragment.
- Answer "no" when the current fragment starts a new paragraph, section, party, clause, or label.
- Be conservative. If uncertain, answer "no".

Return exactly this shape:
{{
  "decisions": {{
    "pair_id": "yes or no"
  }}
}}

Pairs:
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""


def parse_fragment_merge_response(raw: str) -> dict[str, bool]:
    raw = raw.strip()
    if not raw:
        raise ValueError("Empty codex response")
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in codex response")
    payload = json.loads(raw[start : end + 1])
    decisions = payload.get("decisions", {})
    if not isinstance(decisions, dict):
        raise ValueError("Unexpected codex response structure")
    parsed: dict[str, bool] = {}
    for key, value in decisions.items():
        parsed[str(key)] = str(value).strip().lower() == "yes"
    return parsed


def run_codex_fragment_merge(candidates: list[dict], cwd: Path) -> dict[str, bool]:
    with tempfile.TemporaryDirectory(prefix="babel-copy-fragment-merge-") as tmp_raw:
        tmp_dir = Path(tmp_raw)
        output_file = tmp_dir / "last-message.txt"
        cmd = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "-C",
            str(cwd),
            "--ephemeral",
            "--dangerously-bypass-approvals-and-sandbox",
            "-o",
            str(output_file),
            "-",
        ]
        model = fragment_merge_model("codex")
        if model:
            cmd.extend(["--model", model])
        subprocess.run(
            cmd, input=build_fragment_merge_prompt(candidates), text=True, check=True
        )
        return parse_fragment_merge_response(output_file.read_text())


def run_claude_fragment_merge(candidates: list[dict], cwd: Path) -> dict[str, bool]:
    cmd = [
        "claude",
        *claude_cli_flags(),
        "--dangerously-skip-permissions",
        "--add-dir",
        str(cwd),
    ]
    if "-p" in cmd or "--print" in cmd:
        cmd.extend(["--tools", ""])
    model = fragment_merge_model("claude")
    if model:
        cmd.extend(["--model", model])
    completed = subprocess.run(
        cmd,
        input=build_fragment_merge_prompt(candidates),
        text=True,
        cwd=str(cwd),
        capture_output=True,
        check=True,
    )
    return parse_fragment_merge_response(completed.stdout)


def run_fragment_merge(
    candidates: list[dict], *, cwd: Path, provider: str | None = None
) -> dict[str, bool]:
    runtime_mode = detect_runtime_mode(cwd, translation_provider(provider))
    if runtime_mode == "claude":
        return run_claude_fragment_merge(candidates, cwd=cwd)
    return run_codex_fragment_merge(candidates, cwd=cwd)


def llm_fragment_merge_decisions(
    page_blocks: list[dict], cwd: Path, provider: str | None = None
) -> set[tuple[str, str]]:
    if not llm_fragment_merge_enabled():
        return set()
    ordered = sorted(page_blocks, key=lambda item: (item["bbox"][1], item["bbox"][0]))
    decisions: set[tuple[str, str]] = set()
    candidates: list[dict] = []
    candidate_keys: dict[str, tuple[str, str]] = {}
    for previous, current in zip(ordered, ordered[1:]):
        if should_merge_fragment(previous, current):
            continue
        if not is_ambiguous_fragment_pair(previous, current):
            continue
        cache_key = fragment_merge_cache_key(previous, current)
        cached = _FRAGMENT_MERGE_LLM_CACHE.get(cache_key)
        if cached is True:
            decisions.add((str(previous["id"]), str(current["id"])))
            continue
        if cached is False:
            continue
        pair_id = f"{previous['id']}->{current['id']}"
        candidates.append(
            {
                "pair_id": pair_id,
                "page_number": int(previous["page_number"]),
                "previous_role": str(previous.get("role", "")),
                "current_role": str(current.get("role", "")),
                "vertical_gap": round(
                    float(current["bbox"][1]) - float(previous["bbox"][3]), 2
                ),
                "previous_text": clean_text(str(previous.get("text", ""))),
                "current_text": clean_text(str(current.get("text", ""))),
                "cache_key": cache_key,
            }
        )
        candidate_keys[pair_id] = (str(previous["id"]), str(current["id"]))
    if not candidates:
        return decisions
    try:
        raw_decisions = run_fragment_merge(candidates, cwd=cwd, provider=provider)
    except Exception:
        raw_decisions = {}
    for candidate in candidates:
        result = bool(raw_decisions.get(candidate["pair_id"], False))
        _FRAGMENT_MERGE_LLM_CACHE[candidate["cache_key"]] = result
        if result:
            decisions.add(candidate_keys[candidate["pair_id"]])
    return decisions


def dedupe_ocr_blocks(page_blocks: list[dict]) -> list[dict]:
    if not page_blocks:
        return page_blocks
    ordered = sorted(page_blocks, key=lambda item: (item["bbox"][1], item["bbox"][0]))
    deduped: list[dict] = []
    for block in ordered:
        current_text = clean_text(str(block.get("text", "")))
        if not current_text:
            continue
        if not deduped:
            deduped.append(block)
            continue
        previous = deduped[-1]
        previous_text = clean_text(str(previous.get("text", "")))
        if not previous_text:
            deduped.append(block)
            continue
        if not (block_is_ocr(previous) and block_is_ocr(block)):
            deduped.append(block)
            continue
        previous_rect = fitz.Rect(previous["bbox"])
        current_rect = fitz.Rect(block["bbox"])
        same_lane = (
            abs(current_rect.y0 - previous_rect.y0) <= 4.0
            or abs(current_rect.x0 - previous_rect.x0) <= 10.0
        )
        if same_lane:
            if normalized_words(previous_text) == normalized_words(current_text):
                continue
            trimmed = trim_duplicate_prefix(current_text, previous_text)
            if trimmed != current_text:
                block["text"] = trimmed
                current_text = trimmed
        deduped.append(block)
    return deduped


def mark_margin_artifacts(page_blocks: list[dict]) -> None:
    body_left_candidates = [
        block["bbox"][0]
        for block in page_blocks
        if (block["bbox"][2] - block["bbox"][0]) >= 60
        and block.get("role") != "artifact"
    ]
    if not body_left_candidates:
        return
    body_left = median(body_left_candidates)
    for block in page_blocks:
        width = block["bbox"][2] - block["bbox"][0]
        height = block["bbox"][3] - block["bbox"][1]
        if block["bbox"][0] > body_left * 0.75:
            continue
        if width > 28 or height < 24:
            continue
        block["role"] = "artifact"
        block["keep_original"] = True


def normalize_cell_ocr_text(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = clean_text(raw_line)
        if not line:
            continue
        line = line.replace(";", ":")
        line = re.sub(
            r"^(Name|Nom|Designation|Titre|Title)\s*[:.,]*\s*",
            lambda match: f"{match.group(1)}: ",
            line,
            flags=re.IGNORECASE,
        )
        line = line.replace("SAMAMONEYMALI", "SAMA MONEY MALI")
        line = line.replace("ECOBANKMALI", "ECOBANK MALI")
        line = line.replace("GTOBAL", "GLOBAL")
        line = line.replace("TECHNOTOGY", "TECHNOLOGY")
        line = re.sub(r"\bttc\b", "LLC", line, flags=re.IGNORECASE)
        line = line.replace("Mangeineg", "Managing")
        line = line.replace("Mangging", "Managing")
        line = line.replace("Directeu r", "Directeur")
        line = re.sub(
            r"^(Titre|Designation):\s*(?:eo|CRE)\b",
            lambda match: f"{match.group(1)}: CEO",
            line,
            flags=re.IGNORECASE,
        )
        line = re.sub(r"\s{2,}", " ", line)
        label_match = re.match(
            r"^(Name|Nom|Designation|Titre|Title):\s*(.+)$", line, flags=re.IGNORECASE
        )
        if label_match and label_match.group(1).lower() in {
            "designation",
            "titre",
            "title",
        }:
            if not is_reasonable_title_value(label_match.group(2)):
                continue
        lines.append(line)
    return "\n".join(lines)


def is_reasonable_title_value(value: str) -> bool:
    compact = value.strip()
    if not compact:
        return False
    acronyms = {"CEO", "CFO", "COO", "CTO"}
    if compact.upper() in acronyms:
        return True
    tokens = re.findall(r"[A-Za-zÀ-ÿ]+", compact)
    known = {
        "president",
        "président",
        "director",
        "directeur",
        "general",
        "général",
        "managing",
    }
    good_tokens = [
        token
        for token in tokens
        if len(token) >= 4 or token.lower() in known or token.upper() in acronyms
    ]
    return len(good_tokens) >= 2


def score_cell_ocr_text(text: str) -> tuple[int, int, int]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    label_count = 0
    score = 0
    for line in lines:
        weird = len(re.findall(r"[^A-Za-zÀ-ÿ0-9 &:,'()./-]", line))
        line_score = len(line) - weird * 12
        if re.match(
            r"^(Name|Nom|Designation|Titre|Title)\s*:", line, flags=re.IGNORECASE
        ):
            label_count += 1
            line_score += 40
        elif line.isupper() and len(line) > 6:
            line_score += 25
        score += line_score
    return (label_count, len(lines), score)


def best_text_from_top_crop(
    image: Image.Image,
    cell_rect: fitz.Rect,
    page_rect: fitz.Rect,
    current_text: str,
) -> str:
    width, height = image.size
    candidates = [normalize_cell_ocr_text(current_text)]
    fractions = (0.28, 0.34)
    for fraction in fractions:
        x0 = max(0, page_pt_to_px(cell_rect.x0, page_rect.width, width) + 8)
        x1 = min(width, page_pt_to_px(cell_rect.x1, page_rect.width, width) - 8)
        y0 = max(0, page_pt_to_px(cell_rect.y0, page_rect.height, height) + 8)
        y1 = min(
            height,
            page_pt_to_px(
                cell_rect.y0 + cell_rect.height * fraction, page_rect.height, height
            ),
        )
        if x1 - x0 < 16 or y1 - y0 < 16:
            continue
        candidate = normalize_cell_ocr_text(
            ocr_image_to_string(
                image.crop((x0, y0, x1, y1)),
                psm="6",
            )
        )
        if candidate:
            candidates.append(candidate)
    return max(candidates, key=score_cell_ocr_text)


def assign_blocks_to_tables(page_blocks: list[dict], tables: list[dict]) -> None:
    for table in tables:
        for cell in table["cells"]:
            cell_rect = fitz.Rect(cell["bbox"])
            for block in page_blocks:
                block_rect = fitz.Rect(block["bbox"])
                center = fitz.Point(
                    (block_rect.x0 + block_rect.x1) / 2,
                    (block_rect.y0 + block_rect.y1) / 2,
                )
                if not cell_rect.contains(center):
                    continue
                cell["block_ids"].append(block["id"])
                block["table"] = {
                    "table_id": table["id"],
                    "cell_id": cell["id"],
                    "row_index": cell["row_index"],
                    "col_index": cell["col_index"],
                }
                block["role"] = "table_cell"


def trim_to_content(
    image: Image.Image, threshold: int = 245, pad: int = 8
) -> tuple[Image.Image | None, tuple[int, int] | None]:
    grayscale = np.array(image.convert("L"))
    if grayscale.size == 0 or grayscale.shape[0] < 8 or grayscale.shape[1] < 8:
        return None, None
    mask = grayscale[4:-4, 4:-4] < threshold
    if mask.size == 0 or mask.sum() < 180:
        return None, None
    rows, cols = np.where(mask)
    y0 = max(0, int(rows.min()) + 4 - pad)
    y1 = min(grayscale.shape[0], int(rows.max()) + 4 + pad + 1)
    x0 = max(0, int(cols.min()) + 4 - pad)
    x1 = min(grayscale.shape[1], int(cols.max()) + 4 + pad + 1)
    if y1 - y0 < 12 or x1 - x0 < 12:
        return None, None
    trimmed = image.crop((x0, y0, x1, y1))
    return trimmed, (x0, y0)


def extract_signature_crops(
    render_path: Path,
    page_number: int,
    page_rect: fitz.Rect,
    tables: list[dict],
    page_blocks: list[dict],
    assets_dir: Path,
) -> list[dict]:
    image = Image.open(render_path).convert("RGB")
    width, height = image.size
    block_by_id = {block["id"]: block for block in page_blocks}
    exported: list[dict] = []
    for table in tables:
        for cell in table["cells"]:
            cell_rect = fitz.Rect(cell["bbox"])
            body_height = cell_rect.height
            if body_height < 40:
                continue
            blocks = [
                block_by_id[block_id]
                for block_id in cell["block_ids"]
                if block_id in block_by_id
            ]
            if not blocks:
                continue
            text_bottom = max(block["bbox"][3] for block in blocks)
            crop_top_pt = max(text_bottom + 6, cell_rect.y0 + body_height * 0.38)
            crop_bottom_pt = cell_rect.y1 - 4
            if crop_bottom_pt - crop_top_pt < 18:
                continue
            x0 = page_pt_to_px(cell_rect.x0, page_rect.width, width) + 6
            x1 = page_pt_to_px(cell_rect.x1, page_rect.width, width) - 6
            y0 = page_pt_to_px(crop_top_pt, page_rect.height, height)
            y1 = page_pt_to_px(crop_bottom_pt, page_rect.height, height)
            if x1 - x0 < 20 or y1 - y0 < 20:
                continue
            cropped = image.crop((x0, y0, x1, y1))
            trimmed, offset = trim_to_content(cropped)
            if trimmed is None or offset is None:
                continue
            asset_path = (
                assets_dir
                / f"page-{page_number:03d}-table-{table['id']}-cell-{cell['row_index']}-{cell['col_index']}-signature.png"
            )
            trimmed.save(asset_path)
            trimmed_width, trimmed_height = trimmed.size
            asset_x0 = x0 + offset[0]
            asset_y0 = y0 + offset[1]
            exported.append(
                {
                    "id": f"p{page_number}-sig{len(exported) + 1}",
                    "page_number": page_number,
                    "kind": "signature_crop",
                    "origin": "page_render",
                    "bbox": [
                        round(page_px_to_pt(asset_x0, width, page_rect.width), 2),
                        round(page_px_to_pt(asset_y0, height, page_rect.height), 2),
                        round(
                            page_px_to_pt(
                                asset_x0 + trimmed_width, width, page_rect.width
                            ),
                            2,
                        ),
                        round(
                            page_px_to_pt(
                                asset_y0 + trimmed_height, height, page_rect.height
                            ),
                            2,
                        ),
                    ],
                    "path": str(asset_path),
                    "image_size_px": [trimmed_width, trimmed_height],
                    "placement": {
                        "mode": "page_absolute",
                        "table_id": table["id"],
                        "cell_id": cell["id"],
                    },
                }
            )
            cell["signature_asset_ids"].append(exported[-1]["id"])
    return exported


def fill_empty_cells_with_ocr(
    render_path: Path,
    page_number: int,
    page_rect: fitz.Rect,
    tables: list[dict],
    page_blocks: list[dict],
) -> None:
    image = Image.open(render_path).convert("RGB")
    width, height = image.size
    next_index = len(page_blocks) + 1
    for table in tables:
        for cell in table["cells"]:
            if cell["block_ids"]:
                continue
            cell_rect = fitz.Rect(cell["bbox"])
            x0 = max(0, page_pt_to_px(cell_rect.x0, page_rect.width, width) + 4)
            x1 = min(width, page_pt_to_px(cell_rect.x1, page_rect.width, width) - 4)
            y0 = max(0, page_pt_to_px(cell_rect.y0, page_rect.height, height) + 4)
            y1 = min(height, page_pt_to_px(cell_rect.y1, page_rect.height, height) - 4)
            if x1 - x0 < 16 or y1 - y0 < 16:
                continue
            cropped = image.crop((x0, y0, x1, y1))
            extracted = ocr_image_to_string(
                cropped,
                psm="6",
            )
            if not extracted or is_probable_artifact(extracted):
                continue
            block = {
                "id": f"p{page_number}-b{next_index}",
                "page_number": page_number,
                "page_type": "scanned",
                "source": "ocr_cell",
                "bbox": rect_to_list(cell_rect),
                "text": extracted,
                "role": "table_cell",
                "align": "left",
                "style": {
                    "font_size_hint": 10.0,
                    "font_name": None,
                    "flags": None,
                    "color": None,
                    "text_fill_color": None,
                    "bold": extracted.isupper() and len(extracted) > 4,
                    "italic": False,
                },
                "keep_original": False,
                "_font_size_hints": [10.0],
                "_native_lines": [],
                "table": {
                    "table_id": table["id"],
                    "cell_id": cell["id"],
                    "row_index": cell["row_index"],
                    "col_index": cell["col_index"],
                },
            }
            next_index += 1
            page_blocks.append(block)
            cell["block_ids"].append(block["id"])


def enrich_tall_cells_with_ocr(
    render_path: Path,
    page_rect: fitz.Rect,
    tables: list[dict],
    page_blocks: list[dict],
) -> None:
    image = Image.open(render_path).convert("RGB")
    blocks_by_id = {block["id"]: block for block in page_blocks}
    for table in tables:
        for cell in table["cells"]:
            if len(cell["block_ids"]) != 1:
                continue
            cell_rect = fitz.Rect(cell["bbox"])
            if cell_rect.height < 70:
                continue
            block = blocks_by_id.get(cell["block_ids"][0])
            if block is None:
                continue
            current_text = str(block.get("text", ""))
            enriched = best_text_from_top_crop(
                image,
                cell_rect,
                page_rect,
                current_text,
            )
            if score_cell_ocr_text(enriched) > score_cell_ocr_text(current_text):
                block["text"] = enriched


def repeated_role_key(text: str) -> str:
    compact = clean_text(text)
    compact = re.sub(r"\s+", " ", compact).strip().lower()
    return compact


def mark_repeated_headers_and_footers(
    all_blocks: list[dict], pages_payload: list[dict]
) -> None:
    page_heights = {
        int(page["page_number"]): float(page["height"]) for page in pages_payload
    }
    header_groups: dict[str, list[dict]] = defaultdict(list)
    footer_groups: dict[str, list[dict]] = defaultdict(list)

    for block in all_blocks:
        if block.get("keep_original") or block.get("role") in {
            "artifact",
            "table_cell",
        }:
            continue
        page_height = page_heights.get(int(block["page_number"]))
        if not page_height:
            continue
        key = repeated_role_key(str(block.get("text", "")))
        if len(key) < 8:
            continue
        if float(block["bbox"][3]) <= page_height * 0.16:
            header_groups[key].append(block)
        if float(block["bbox"][1]) >= page_height * 0.84:
            footer_groups[key].append(block)

    for groups, role in ((header_groups, "header"), (footer_groups, "footer")):
        for blocks in groups.values():
            pages = {int(block["page_number"]) for block in blocks}
            if len(pages) < 2:
                continue
            for block in blocks:
                block["role"] = role


def main() -> int:
    args = parse_args()
    input_pdf = Path(args.input_pdf).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    assets_dir = output_dir / "assets"
    renders_dir = output_dir / "page-renders"
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    renders_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(input_pdf)
    selected = parse_page_selection(args.pages, doc.page_count)
    all_blocks = []
    all_assets = []
    pages_payload = []
    markdown_lines = [f"# Source Text: {input_pdf.name}", ""]

    for page_index in range(doc.page_count):
        page_number = page_index + 1
        if page_number not in selected:
            continue
        page = doc[page_index]
        page_type, region_source = classify_page(page)
        effective_region_source = (
            region_source if region_source == "native" else "ocr_tesseract"
        )
        regions = (
            extract_native_regions(page)
            if region_source == "native"
            else extract_ocr_regions(
                page, args.magnify_factor if region_source == "ocr" else 1.0
            )
        )
        regions = [region for region in regions if clean_text(region.text)]
        merged = merge_regions(regions)

        pix = page.get_pixmap(dpi=args.dpi, alpha=False)
        render_path = renders_dir / f"page-{page_number:03d}.png"
        render_path.write_bytes(pix.tobytes("png"))

        page_assets = export_page_assets(page, page_number, assets_dir)
        page_blocks = []

        markdown_lines.append(f"## Page {page_number}")
        markdown_lines.append("")
        for block_index, block in enumerate(merged, 1):
            block_text = block_text_from_regions(block["regions"])
            if not block_text:
                continue
            rect = block["rect"]
            role = role_for_text(block_text)
            payload = {
                "id": f"p{page_number}-b{block_index}",
                "page_number": page_number,
                "page_type": page_type,
                "source": block["source"],
                "bbox": rect_to_list(rect),
                "text": block_text,
                "role": role,
                "align": block["align"],
                "style": {
                    "font_size_hint": round(
                        sum(region.font_size_hint for region in block["regions"])
                        / len(block["regions"]),
                        2,
                    ),
                    "font_name": None,
                    "flags": None,
                    "color": None,
                    "text_fill_color": None,
                    "bold": block_text.isupper() and len(block_text) > 4,
                    "italic": False,
                },
                "keep_original": role == "artifact",
                "_font_size_hints": [
                    float(region.font_size_hint) for region in block["regions"]
                ],
                "_native_lines": [
                    line_payload(region)
                    for region in block["regions"]
                    if region.source == "native"
                ],
                "table": None,
            }
            page_blocks.append(payload)
            markdown_lines.append(block_text)
            markdown_lines.append("")

        page_tables = detect_tables(render_path, page.rect)
        for table in page_tables:
            table["id"] = f"p{page_number}-{table['id']}"
            table["page_number"] = page_number
            table["cells"] = build_table_cells(page_number, table)
        assign_blocks_to_tables(page_blocks, page_tables)
        fill_empty_cells_with_ocr(
            render_path,
            page_number,
            page.rect,
            page_tables,
            page_blocks,
        )
        enrich_tall_cells_with_ocr(
            render_path,
            page.rect,
            page_tables,
            page_blocks,
        )
        page_blocks = attach_leading_bullets(page_blocks)
        page_blocks = merge_inline_row_fragments(page_blocks)
        page_blocks = merge_paragraph_fragments(
            page_blocks,
            llm_fragment_merge_decisions(
                page_blocks,
                cwd=input_pdf.parent,
                provider=args.translation_provider,
            ),
        )
        page_blocks = dedupe_ocr_blocks(page_blocks)
        mark_textual_table_like_rows(page_blocks)
        textual_tables = build_textual_tables(page_number, page_blocks)
        for table in textual_tables:
            table["id"] = f"p{page_number}-{table['id']}"
            table["page_number"] = page_number
            table["cells"] = build_table_cells(page_number, table)
        if textual_tables:
            page_tables.extend(textual_tables)
            assign_blocks_to_tables(page_blocks, textual_tables)
        mark_margin_artifacts(page_blocks)
        mark_list_items_from_marker_artifacts(page_blocks)
        mark_two_column_rows(page_blocks)
        for block in page_blocks:
            if block.get("keep_original"):
                continue
            block["text"] = normalize_cell_ocr_text(str(block.get("text", "")))
        finalize_block_layout(page_blocks, page.rect)
        signature_assets = extract_signature_crops(
            render_path, page_number, page.rect, page_tables, page_blocks, assets_dir
        )

        for table in page_tables:
            for cell in table["cells"]:
                blocks_in_cell = [
                    block for block in page_blocks if block["id"] in cell["block_ids"]
                ]
                blocks_in_cell.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
                cell["text"] = "\n".join(block["text"] for block in blocks_in_cell)

        page_asset_ids = []
        for asset in [*page_assets, *signature_assets]:
            page_asset_ids.append(asset["id"])
            all_assets.append(asset)
        for asset in signature_assets:
            asset["kind"] = "signature_crop"

        all_blocks.extend(page_blocks)
        pages_payload.append(
            {
                "page_number": page_number,
                "page_type": page_type,
                "region_source": effective_region_source,
                "strategy_hint": "rebuild"
                if ((page_tables and page_type != "scanned") or signature_assets)
                else "overlay",
                "width": round(page.rect.width, 2),
                "height": round(page.rect.height, 2),
                "render_path": str(render_path),
                "asset_ids": page_asset_ids,
                "tables": page_tables,
            }
        )

    mark_repeated_headers_and_footers(all_blocks, pages_payload)

    if args.font_baseline:
        family_class = normalize_font_family_class(args.font_baseline)
        if not family_class:
            raise SystemExit("--font-baseline must be 'serif' or 'sans'.")
        font_baseline = build_font_baseline(
            family_class,
            source="visual_override",
            reason="Operator-selected from visual inspection of the rendered source pages.",
        )
    else:
        font_baseline = font_baseline_from_payload({"blocks": all_blocks})

    payload = {
        "input_pdf": str(input_pdf),
        "page_count": len(pages_payload),
        "block_count": len(all_blocks),
        "font_baseline": font_baseline,
        "pages": pages_payload,
        "blocks": all_blocks,
        "assets": all_assets,
    }
    (output_dir / "source.md").write_text("\n".join(markdown_lines))
    (output_dir / "blocks.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False)
    )
    print(output_dir / "source.md")
    print(output_dir / "blocks.json")
    print(assets_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
