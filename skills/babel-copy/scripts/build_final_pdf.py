#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "Pillow==12.1.1",
#   "PyMuPDF==1.27.2.2",
#   "pytesseract==0.3.13",
# ]
# [tool.uv]
# exclude-newer = "2026-03-19T14:37:22Z"
# ///
from __future__ import annotations

import argparse
from contextlib import nullcontext
import difflib
import json
import tempfile
from pathlib import Path

import fitz

from block_overrides import apply_custom_overrides_to_payload
import core
import export_typst_pdf
from profiling import create_profiler, resolve_profile_path
import rebuild_typst


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the final babel-copy PDF using the best available page strategy")
    parser.add_argument("source_pdf")
    parser.add_argument("translated_blocks_json")
    parser.add_argument("--output-pdf", required=True)
    parser.add_argument("--profiler", action="store_true")
    parser.add_argument("--profiler-commands")
    parser.add_argument("--profiler-output-dir")
    return parser.parse_args()

def asset_map(payload: dict) -> dict[str, dict]:
    return {asset["id"]: asset for asset in payload.get("assets", [])}


def clean_pdf_font_name(value: str | None) -> str:
    if not value:
        return ""
    return str(value).split("+", 1)[-1]


def font_file_suffix(ext: str | None) -> str:
    suffix = (ext or "bin").strip().lstrip(".")
    if not suffix or "/" in suffix or "\\" in suffix:
        return "bin"
    return suffix


def font_priority(font_record: tuple) -> tuple[int, int]:
    _, ext, pdf_font_type, *_ = font_record
    return (2 if pdf_font_type == "Type0" else 1 if pdf_font_type == "TrueType" else 0, 1 if ext == "ttf" else 0)


def build_source_font_catalog(source_doc: fitz.Document) -> dict[str, tuple]:
    catalog: dict[str, tuple] = {}
    for page_index in range(source_doc.page_count):
        for font_record in source_doc[page_index].get_fonts():
            font_name = clean_pdf_font_name(font_record[3] if len(font_record) > 3 else "")
            if not font_name:
                continue
            existing = catalog.get(font_name)
            if existing is None or font_priority(font_record) > font_priority(existing):
                catalog[font_name] = font_record
    return catalog


def resolve_font_resource(
    source_doc: fitz.Document,
    font_catalog: dict[str, tuple],
    font_name: str | None,
    font_cache: dict[str, tuple[str, str | None]],
    temp_dir: Path,
    fallback_font_name: str,
) -> tuple[str, str | None]:
    clean_name = clean_pdf_font_name(font_name)
    if not clean_name:
        return (fallback_font_name, None)
    cached = font_cache.get(clean_name)
    if cached:
        return cached
    font_record = font_catalog.get(clean_name)
    if not font_record:
        fallback = (fallback_font_name, None)
        font_cache[clean_name] = fallback
        return fallback

    xref = int(font_record[0])
    extracted_name, ext, _, buffer = source_doc.extract_font(xref)
    suffix = font_file_suffix(ext)
    if not buffer:
        fallback = (fallback_font_name, None)
        font_cache[clean_name] = fallback
        return fallback
    font_path = temp_dir / f"{clean_name.replace(' ', '_')}-{xref}.{suffix}"
    if not font_path.exists():
        font_path.write_bytes(buffer)
    try:
        fitz.Font(fontfile=str(font_path))
    except Exception:
        fallback = (fallback_font_name, None)
        font_cache[clean_name] = fallback
        return fallback
    alias = f"bcf_{len(font_cache)}"
    resolved = (alias, str(font_path))
    font_cache[clean_name] = resolved
    return resolved


def font_resource_is_usable(
    source_doc: fitz.Document,
    font_catalog: dict[str, tuple],
    font_name: str | None,
    usability_cache: dict[str, bool],
    temp_dir: Path,
) -> bool:
    clean_name = clean_pdf_font_name(font_name)
    if not clean_name:
        return False
    cached = usability_cache.get(clean_name)
    if cached is not None:
        return cached
    font_record = font_catalog.get(clean_name)
    if not font_record:
        usability_cache[clean_name] = False
        return False
    xref = int(font_record[0])
    _, ext, _, buffer = source_doc.extract_font(xref)
    if not buffer:
        usability_cache[clean_name] = False
        return False
    font_path = temp_dir / f"{clean_name.replace(' ', '_')}-{xref}.{font_file_suffix(ext)}"
    if not font_path.exists():
        font_path.write_bytes(buffer)
    try:
        fitz.Font(fontfile=str(font_path))
    except Exception:
        usability_cache[clean_name] = False
        return False
    usability_cache[clean_name] = True
    return True


def choose_page_mode(page: dict, assets_by_id: dict[str, dict]) -> str:
    if page.get("tables") and str(page.get("page_type", "")) != "scanned":
        return "structured_rebuild"
    for asset_id in page.get("asset_ids", []):
        asset = assets_by_id.get(asset_id)
        if not asset:
            continue
        if asset.get("kind") == "signature_crop":
            return "structured_rebuild"
    return "template_overlay"


def blocks_by_page(payload: dict) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = {}
    for block in payload.get("blocks", []):
        grouped.setdefault(int(block["page_number"]), []).append(block)
    for page_blocks in grouped.values():
        page_blocks.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
    return grouped


def normalized_text(value: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def block_render_text(block: dict) -> str:
    translated = block.get("translated_text")
    if translated is not None:
        return str(translated)
    return str(block.get("text", ""))


def text_similarity(block: dict) -> float:
    source = normalized_text(str(block.get("text", "")))
    translated = normalized_text(block_render_text(block))
    if not source and not translated:
        return 1.0
    return difflib.SequenceMatcher(a=source, b=translated).ratio()


def overlap_ratio(left: dict, right: dict) -> float:
    left_rect = fitz.Rect(left["bbox"])
    right_rect = fitz.Rect(right["bbox"])
    intersection = left_rect & right_rect
    if intersection.is_empty:
        return 0.0
    return intersection.get_area() / max(1.0, min(left_rect.get_area(), right_rect.get_area()))


def looks_like_data_block(block: dict) -> bool:
    text = str(block.get("text", ""))
    if "," in text or "/" in text:
        return True
    tokens = [token for token in text.replace("\n", " ").split() if token]
    capitalized = sum(1 for token in tokens if token[:1].isupper())
    return len(tokens) <= 10 and capitalized >= 3


def preserved_overlay_ids(page_blocks: list[dict]) -> set[str]:
    eligible = [block for block in page_blocks if not block.get("keep_original") and block.get("role") != "artifact"]
    preserved: set[str] = set()
    for block in eligible:
        neighbors = [other for other in eligible if other["id"] != block["id"] and overlap_ratio(block, other) >= 0.25]
        if len(neighbors) < 2:
            continue
        cluster = [block, *neighbors]
        data_like = sum(1 for item in cluster if looks_like_data_block(item))
        avg_similarity = sum(text_similarity(item) for item in cluster) / len(cluster)
        min_similarity = min(text_similarity(item) for item in cluster)
        role_set = {str(item.get("role", "")) for item in cluster}
        if data_like >= 2 and avg_similarity >= 0.92 and min_similarity >= 0.88 and role_set == {"paragraph"}:
            preserved.update(item["id"] for item in cluster)
    return preserved


def meaningful_rect_overlap(left_rect: fitz.Rect, right_rect: fitz.Rect) -> fitz.Rect | None:
    intersection = left_rect & right_rect
    if intersection.is_empty:
        return None
    if intersection.width <= 0.75 or intersection.height <= 0.75:
        return None
    return intersection


def overlay_occupancy_rect(block: dict, page_blocks: list[dict], page_rect: fitz.Rect) -> fitz.Rect:
    if block.get("role") == "artifact":
        return fitz.Rect(block["bbox"])
    return render_rect_for_block(block, page_blocks, page_rect)


def should_ignore_artifact_obstacle(block: dict) -> bool:
    if block.get("role") != "artifact":
        return False
    bbox = block.get("bbox") or [0, 0, 0, 0]
    width = max(0.0, float(bbox[2]) - float(bbox[0]))
    height = max(0.0, float(bbox[3]) - float(bbox[1]))
    text = str(block.get("translated_text") or block.get("text") or "").strip()
    return width * height <= 4.0 and len(text) <= 1


def filtered_payload_for_pages(payload: dict, page_numbers: list[int], assets_by_id: dict[str, dict]) -> dict:
    ordered_page_numbers = [int(page_number) for page_number in page_numbers]
    page_number_map = {page_number: index + 1 for index, page_number in enumerate(ordered_page_numbers)}
    selected_pages = [
        page
        for page in payload.get("pages", [])
        if int(page["page_number"]) in page_number_map
    ]
    filtered_pages = []
    filtered_blocks = []
    selected_asset_ids: set[str] = set()
    for page in selected_pages:
        original_page_number = int(page["page_number"])
        mapped_page_number = page_number_map[original_page_number]
        page_blocks = [
            block
            for block in payload.get("blocks", [])
            if int(block["page_number"]) == original_page_number
        ]
        asset_ids = set(page.get("asset_ids", []))
        for block in page_blocks:
            table = block.get("table")
            if not table:
                continue
            cell_id = table.get("cell_id")
            if not cell_id:
                continue
            for table_payload in page.get("tables", []):
                for cell in table_payload.get("cells", []):
                    if cell.get("id") == cell_id:
                        asset_ids.update(cell.get("signature_asset_ids", []))
        selected_asset_ids.update(asset_ids)
        filtered_page = json.loads(json.dumps(page))
        filtered_page["page_number"] = mapped_page_number
        ordered_asset_ids = [asset_id for asset_id in page.get("asset_ids", []) if asset_id in asset_ids]
        ordered_asset_ids.extend(sorted(asset_ids - set(ordered_asset_ids)))
        filtered_page["asset_ids"] = ordered_asset_ids
        for table in filtered_page.get("tables", []):
            table["page_number"] = mapped_page_number
        filtered_pages.append(filtered_page)
        for block in page_blocks:
            copied = json.loads(json.dumps(block))
            copied["page_number"] = mapped_page_number
            filtered_blocks.append(copied)
    filtered_assets = []
    for asset in payload.get("assets", []):
        if asset["id"] not in selected_asset_ids:
            continue
        copied = json.loads(json.dumps(asset))
        copied["page_number"] = page_number_map[int(asset["page_number"])]
        filtered_assets.append(copied)
    return {
        "input_pdf": payload.get("input_pdf"),
        "page_count": len(filtered_pages),
        "block_count": len(filtered_blocks),
        "font_baseline": payload.get("font_baseline"),
        "pages": filtered_pages,
        "blocks": filtered_blocks,
        "assets": filtered_assets,
        "translation_mode": payload.get("translation_mode"),
    }


def contiguous_rebuild_chunks(pages: list[dict], assets_by_id: dict[str, dict]) -> list[list[int]]:
    chunks: list[list[int]] = []
    current_chunk: list[int] = []
    for page in pages:
        page_number = int(page["page_number"])
        if choose_page_mode(page, assets_by_id) == "structured_rebuild":
            current_chunk.append(page_number)
            continue
        if current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
    if current_chunk:
        chunks.append(current_chunk)
    return chunks


def render_overlay_page(
    source_doc: fitz.Document,
    page_index: int,
    page: dict,
    page_blocks: list[dict],
    font_catalog: dict[str, tuple],
    font_cache: dict[str, tuple[str, str | None]],
    temp_dir: Path,
    font_baseline: dict[str, str],
) -> fitz.Document:
    out_doc = fitz.open()
    out_doc.insert_pdf(source_doc, from_page=page_index, to_page=page_index)
    out_page = out_doc[-1]
    source_page = source_doc[page_index]
    preserved_ids = preserved_overlay_ids(page_blocks)
    occupied_rects: list[tuple[str, fitz.Rect, str]] = []
    for block in page_blocks:
        if should_ignore_artifact_obstacle(block):
            continue
        if block["id"] in preserved_ids or block.get("keep_original") or block.get("role") == "artifact":
            occupied_rects.append((block["id"], overlay_occupancy_rect(block, page_blocks, out_page.rect), "preserved"))
            continue
        fill = core.estimate_background_color(source_page, tuple(block["bbox"]), "white")
        out_page.add_redact_annot(redaction_rect_for_block(block, page_blocks), fill=fill)
    if page_blocks:
        out_page.apply_redactions()
    for block in page_blocks:
        if block["id"] in preserved_ids or block.get("keep_original") or block.get("role") == "artifact":
            continue
        text = overlay_text_for_block(block, page_blocks)
        if not str(text).strip():
            continue
        rect = render_rect_for_block(block, page_blocks, out_page.rect)
        for obstacle_id, obstacle_rect, obstacle_kind in occupied_rects:
            intersection = meaningful_rect_overlap(rect, obstacle_rect)
            if intersection is None:
                continue
            raise SystemExit(
                "Overlay collision detected on page "
                f"{page.get('page_number')} between block {block['id']} and {obstacle_kind} "
                f"block {obstacle_id}; intersection="
                f"({intersection.x0:.2f}, {intersection.y0:.2f}, {intersection.x1:.2f}, {intersection.y1:.2f}). "
                "Use a custom_override or switch this page to rebuild mode."
            )
        style = block.get("style", {})
        render_font_name, render_font_file = resolve_font_resource(
            source_doc,
            font_catalog,
            style.get("font_name"),
            font_cache,
            temp_dir,
            str(font_baseline.get("pdf_font_name") or core.PDF_SERIF_FONT_NAME),
        )
        region = core.TextRegion(
            bbox=(round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)),
            text=str(block.get("text", "")),
            source=str(block.get("source", "native")),
            font_size_hint=float(block.get("style", {}).get("font_size_hint", 10.5)),
            align=str(block.get("align", "left")),
            render_font_name=render_font_name,
            render_font_file=render_font_file,
            text_color=core.color_int_to_rgb(style.get("color")),
            baseline_y=float(block["_render_baseline_y"]) if block.get("_render_baseline_y") is not None else None,
        )
        remainder = core.draw_translated_text(out_page, region, str(text))
        if remainder:
            # The core renderer already drew the block once at minimum size. Avoid a second draw pass,
            # which creates partially overlaid duplicate text on dense OCR pages.
            occupied_rects.append((block["id"], rect, "translated"))
            continue
        occupied_rects.append((block["id"], rect, "translated"))
    return out_doc


def leading_marker_artifact(block: dict, page_blocks: list[dict]) -> dict | None:
    if str(block.get("role", "")) != "list_item":
        return None
    block_text = block_render_text(block).lstrip()
    if not block_text.startswith("•"):
        return None
    block_rect = fitz.Rect(block["bbox"])
    candidates = []
    for other in page_blocks:
        if other["id"] == block["id"] or other.get("role") != "artifact":
            continue
        other_rect = fitz.Rect(other["bbox"])
        same_line = abs(other_rect.y0 - block_rect.y0) <= 4.0
        within_leading_lane = other_rect.x0 >= block_rect.x0 and other_rect.x1 <= block_rect.x0 + 40.0
        if same_line and within_leading_lane:
            candidates.append(other)
    if not candidates:
        return None
    return max(candidates, key=lambda item: float(item["bbox"][2]))


def overlay_text_for_block(block: dict, page_blocks: list[dict]) -> str:
    text = block_render_text(block)
    marker = leading_marker_artifact(block, page_blocks)
    if marker is None:
        return text
    stripped = text.lstrip()
    if stripped.startswith("•"):
        return stripped[1:].lstrip()
    return text


def content_rect_for_block(block: dict, page_blocks: list[dict]) -> fitz.Rect:
    rect = fitz.Rect(block["bbox"])
    marker = leading_marker_artifact(block, page_blocks)
    if marker is not None:
        marker_rect = fitz.Rect(marker["bbox"])
        rect = fitz.Rect(max(rect.x0, marker_rect.x1 + 16.0), rect.y0, rect.x1, rect.y1)
    return rect


def ocr_redaction_padding(block: dict) -> tuple[float, float, float, float]:
    if not str(block.get("source", "")).startswith("ocr"):
        return (0.0, 0.0, 0.0, 0.0)
    rect = fitz.Rect(block["bbox"])
    text = block_render_text(block)
    role = str(block.get("role", ""))
    line_count = max(1, len([line for line in text.splitlines() if line.strip()]))
    font_size_hint = float(block.get("style", {}).get("font_size_hint", 8.0) or 8.0)
    expected_height = max(font_size_hint * 1.25, line_count * font_size_hint * 1.05)
    looks_tight = rect.height <= expected_height + 1.5
    x_pad = max(3.0, min(8.0, font_size_hint * 0.55 + (1.0 if looks_tight else 0.4)))
    y_pad = max(1.8, min(5.5, font_size_hint * 0.42 + (1.2 if looks_tight else 0.5)))
    bottom_pad = min(6.5, y_pad + (1.2 if line_count == 1 else 1.8))
    if role in {"paragraph", "list_item", "table_cell"}:
        x_pad = max(x_pad, 5.5)
        y_pad = max(y_pad, 4.8 if line_count == 1 else 5.5)
        bottom_pad = max(bottom_pad, 6.0 if line_count == 1 else 6.8)
    elif role in {"heading", "title", "header", "footer"}:
        x_pad = max(x_pad, 3.8)
        y_pad = max(y_pad, 2.8)
        bottom_pad = max(bottom_pad, 4.2)
    return (x_pad, y_pad, x_pad, bottom_pad)


def redaction_rect_for_block(block: dict, page_blocks: list[dict]) -> fitz.Rect:
    rect = fitz.Rect(block["bbox"])
    marker = leading_marker_artifact(block, page_blocks)
    if marker is not None:
        marker_rect = fitz.Rect(marker["bbox"])
        rect = fitz.Rect(max(rect.x0, marker_rect.x1 + 1.0), rect.y0, rect.x1, rect.y1)
    role = str(block.get("role", ""))
    if role in {"footer", "header"} and not str(block.get("source", "")).startswith("ocr"):
        return fitz.Rect(rect.x0, rect.y0 + 1.5, rect.x1, max(rect.y0 + 2.0, rect.y1 - 0.5))
    left_pad, top_pad, right_pad, bottom_pad = ocr_redaction_padding(block)
    if left_pad or top_pad or right_pad or bottom_pad:
        rect = fitz.Rect(rect.x0 - left_pad, rect.y0 - top_pad, rect.x1 + right_pad, rect.y1 + bottom_pad)
    return rect


def render_rect_for_block(block: dict, page_blocks: list[dict], page_rect: fitz.Rect) -> fitz.Rect:
    rect = content_rect_for_block(block, page_blocks)
    role = str(block.get("role", ""))
    text = overlay_text_for_block(block, page_blocks)
    style = block.get("style", {})
    font_size_hint = float(style.get("font_size_hint", 0) or 0)
    if (
        role not in {"heading", "title", "form_label"}
        or font_size_hint < 12.0
        or "\n" in text
        or str(block.get("align", "left")) != "left"
    ):
        return rect
    padding = 36.0
    next_x0 = page_rect.x1 - padding
    for other in page_blocks:
        if other["id"] == block["id"]:
            continue
        other_rect = fitz.Rect(other["bbox"])
        vertical_overlap = min(rect.y1, other_rect.y1) - max(rect.y0, other_rect.y0)
        if vertical_overlap <= 0:
            continue
        if other_rect.x0 <= rect.x0:
            continue
        next_x0 = min(next_x0, other_rect.x0 - 6.0)
    if next_x0 <= rect.x1:
        return rect
    return fitz.Rect(rect.x0, rect.y0, round(next_x0, 2), rect.y1)


def render_pages_via_typst(
    payload: dict,
    page_numbers: list[int],
    output_pdf: Path,
    assets_by_id: dict[str, dict],
    source_doc: fitz.Document,
    font_catalog: dict[str, tuple],
    font_baseline: dict[str, str],
    font_usability_cache: dict[str, bool],
    temp_dir: Path,
    profiler=None,
) -> Path:
    chunk_label = f"{page_numbers[0]:03d}-{page_numbers[-1]:03d}"
    with profiler.stage(
        "filter_rebuild_chunk_payload",
        page_start=page_numbers[0],
        page_end=page_numbers[-1],
        page_count=len(page_numbers),
    ) if profiler else nullcontext():
        page_payload = filtered_payload_for_pages(payload, page_numbers, assets_by_id)
    default_text_font = str(font_baseline.get("text_font_name") or core.TEXT_SERIF_FONT_NAME)
    for block in page_payload.get("blocks", []):
        style = block.setdefault("style", {})
        if not font_resource_is_usable(source_doc, font_catalog, style.get("font_name"), font_usability_cache, temp_dir):
            style["font_name"] = default_text_font
    with tempfile.TemporaryDirectory(prefix="babel-copy-build-chunk-") as tmp_dir_raw:
        tmp_dir = Path(tmp_dir_raw)
        typ_path = tmp_dir / f"pages-{chunk_label}.typ"
        with profiler.stage(
            "rebuild_typst_document",
            page_start=page_numbers[0],
            page_end=page_numbers[-1],
            page_count=len(page_numbers),
        ) if profiler else nullcontext():
            rebuild_typst.write_typst_document(page_payload, typ_path)
        rendered_pdf = tmp_dir / f"{typ_path.stem}.pdf"
        with profiler.stage(
            "compile_typst_pdf",
            page_start=page_numbers[0],
            page_end=page_numbers[-1],
            page_count=len(page_numbers),
        ) if profiler else nullcontext():
            export_typst_pdf.compile_typst_to_pdf(typ_path, rendered_pdf)
        with profiler.stage(
            "copy_rendered_chunk_pdf",
            page_start=page_numbers[0],
            page_end=page_numbers[-1],
            page_count=len(page_numbers),
        ) if profiler else nullcontext():
            output_pdf.parent.mkdir(parents=True, exist_ok=True)
            output_pdf.write_bytes(rendered_pdf.read_bytes())
    return output_pdf


def render_hybrid_document(source_pdf: Path, payload: dict, output_pdf: Path, profiler=None) -> Path:
    blocks = blocks_by_page(payload)
    assets_by_id = asset_map(payload)
    with profiler.stage("open_source_pdf", path=source_pdf) if profiler else nullcontext():
        source_doc = fitz.open(source_pdf)
    out_doc = fitz.open()
    temp_paths: list[Path] = []
    font_catalog = build_source_font_catalog(source_doc)
    font_cache: dict[str, tuple[str, str | None]] = {}
    font_usability_cache: dict[str, bool] = {}
    font_baseline = core.font_baseline_from_payload(payload)
    pages = payload.get("pages", [])
    try:
        with tempfile.TemporaryDirectory(prefix="babel-copy-fonts-") as font_dir_raw:
            font_dir = Path(font_dir_raw)
            page_index = 0
            while page_index < len(pages):
                page = pages[page_index]
                page_number = int(page["page_number"])
                mode = choose_page_mode(page, assets_by_id)
                page_blocks = blocks.get(page_number, [])
                if mode == "template_overlay":
                    with profiler.stage(
                        "render_page",
                        page_number=page_number,
                        mode=mode,
                        block_count=len(page_blocks),
                        table_count=len(page.get("tables", [])),
                    ) if profiler else nullcontext():
                        rendered_doc = render_overlay_page(source_doc, page_index, page, page_blocks, font_catalog, font_cache, font_dir, font_baseline)
                        out_doc.insert_pdf(rendered_doc)
                        rendered_doc.close()
                    if profiler:
                        profiler.increment_counter("overlay_pages")
                    page_index += 1
                    continue

                rebuild_pages: list[int] = []
                chunk_end = page_index
                while chunk_end < len(pages):
                    chunk_page = pages[chunk_end]
                    if choose_page_mode(chunk_page, assets_by_id) != "structured_rebuild":
                        break
                    rebuild_pages.append(int(chunk_page["page_number"]))
                    chunk_end += 1
                with profiler.stage(
                    "render_rebuild_chunk",
                    page_start=rebuild_pages[0],
                    page_end=rebuild_pages[-1],
                    page_count=len(rebuild_pages),
                ) if profiler else nullcontext():
                    with tempfile.NamedTemporaryFile(
                        prefix=f"babel-copy-pages-{rebuild_pages[0]:03d}-{rebuild_pages[-1]:03d}-",
                        suffix=".pdf",
                        delete=False,
                    ) as tmp_file:
                        temp_path = Path(tmp_file.name)
                    temp_paths.append(temp_path)
                    render_pages_via_typst(
                        payload,
                        rebuild_pages,
                        temp_path,
                        assets_by_id,
                        source_doc,
                        font_catalog,
                        font_baseline,
                        font_usability_cache,
                        font_dir,
                        profiler=profiler,
                    )
                    with profiler.stage(
                        "load_rendered_chunk_pdf",
                        page_start=rebuild_pages[0],
                        page_end=rebuild_pages[-1],
                        page_count=len(rebuild_pages),
                    ) if profiler else nullcontext():
                        rendered_doc = fitz.open(temp_path)
                        out_doc.insert_pdf(rendered_doc)
                        rendered_doc.close()
                if profiler:
                    profiler.increment_counter("rebuild_chunks")
                    for _ in rebuild_pages:
                        profiler.increment_counter("rebuild_pages")
                page_index = chunk_end
        with profiler.stage("save_output_pdf", path=output_pdf) if profiler else nullcontext():
            output_pdf.parent.mkdir(parents=True, exist_ok=True)
            out_doc.save(output_pdf, garbage=4, deflate=True)
        return output_pdf
    finally:
        source_doc.close()
        out_doc.close()
        for temp_path in temp_paths:
            temp_path.unlink(missing_ok=True)


def main() -> int:
    args = parse_args()
    source_pdf = Path(args.source_pdf).expanduser().resolve()
    translated_blocks_json = Path(args.translated_blocks_json).expanduser().resolve()
    output_pdf = Path(args.output_pdf).expanduser().resolve()
    profiler = create_profiler(
        resolve_profile_path(
            cli_enabled=bool(args.profiler),
            cli_commands=args.profiler_commands,
            cli_output_dir=args.profiler_output_dir,
            command="build_final_pdf",
            search_from=Path.cwd(),
            context_paths=[source_pdf, translated_blocks_json, output_pdf],
        ),
        command="build_final_pdf",
        metadata={
            "source_pdf": str(source_pdf),
            "translated_blocks_json": str(translated_blocks_json),
            "output_pdf": str(output_pdf),
        },
    )
    try:
        with profiler.stage("read_translated_blocks_json", path=translated_blocks_json):
            payload = apply_custom_overrides_to_payload(
                json.loads(translated_blocks_json.read_text())
            )
        profiler.set_counter("page_count", len(payload.get("pages", [])))
        profiler.set_counter("block_count", len(payload.get("blocks", [])))
        rendered = render_hybrid_document(source_pdf, payload, output_pdf, profiler=profiler)
        print(rendered)
        profiler.finish(status="ok")
        return 0
    except BaseException as exc:
        profiler.finish(
            status="error",
            error={"type": type(exc).__name__, "message": str(exc)},
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
