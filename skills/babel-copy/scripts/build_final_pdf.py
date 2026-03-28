#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import fitz

from block_overrides import apply_custom_overrides_to_payload
import core


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the final babel-copy PDF using the best available page strategy")
    parser.add_argument("source_pdf")
    parser.add_argument("translated_blocks_json")
    parser.add_argument("--output-pdf", required=True)
    return parser.parse_args()


def asset_map(payload: dict) -> dict[str, dict]:
    return {asset["id"]: asset for asset in payload.get("assets", [])}


def clean_pdf_font_name(value: str | None) -> str:
    if not value:
        return ""
    return str(value).split("+", 1)[-1]


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
) -> tuple[str, str | None]:
    clean_name = clean_pdf_font_name(font_name)
    if not clean_name:
        return (core.FONT_NAME, None)
    cached = font_cache.get(clean_name)
    if cached:
        return cached
    font_record = font_catalog.get(clean_name)
    if not font_record:
        fallback = (core.FONT_NAME, None)
        font_cache[clean_name] = fallback
        return fallback

    xref = int(font_record[0])
    extracted_name, ext, _, buffer = source_doc.extract_font(xref)
    suffix = ext or "bin"
    font_path = temp_dir / f"{clean_name.replace(' ', '_')}-{xref}.{suffix}"
    if not font_path.exists():
        font_path.write_bytes(buffer)
    alias = f"bcf_{len(font_cache)}"
    resolved = (alias, str(font_path))
    font_cache[clean_name] = resolved
    return resolved


def choose_page_mode(page: dict, assets_by_id: dict[str, dict]) -> str:
    if page.get("tables"):
        return "docx_rebuild"
    for asset_id in page.get("asset_ids", []):
        asset = assets_by_id.get(asset_id)
        if not asset:
            continue
        if asset.get("kind") == "signature_crop":
            return "docx_rebuild"
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


def text_similarity(block: dict) -> float:
    source = normalized_text(str(block.get("text", "")))
    translated = normalized_text(str(block.get("translated_text") or block.get("text") or ""))
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


def filtered_payload_for_page(payload: dict, page_number: int, assets_by_id: dict[str, dict]) -> dict:
    page = next(page for page in payload.get("pages", []) if int(page["page_number"]) == page_number)
    blocks = [block for block in payload.get("blocks", []) if int(block["page_number"]) == page_number]
    asset_ids = set(page.get("asset_ids", []))
    for block in blocks:
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
    assets = [assets_by_id[asset_id] for asset_id in asset_ids if asset_id in assets_by_id]
    filtered_page = dict(page)
    filtered_page["page_number"] = 1
    filtered_page["asset_ids"] = [asset["id"] for asset in assets]
    filtered_page["tables"] = json.loads(json.dumps(filtered_page.get("tables", [])))
    for table in filtered_page.get("tables", []):
        table["page_number"] = 1
    filtered_blocks = []
    for block in blocks:
        copied = json.loads(json.dumps(block))
        copied["page_number"] = 1
        filtered_blocks.append(copied)
    filtered_assets = []
    for asset in assets:
        copied = json.loads(json.dumps(asset))
        copied["page_number"] = 1
        filtered_assets.append(copied)
    return {
        "input_pdf": payload.get("input_pdf"),
        "page_count": 1,
        "block_count": len(filtered_blocks),
        "pages": [filtered_page],
        "blocks": filtered_blocks,
        "assets": filtered_assets,
        "translation_mode": payload.get("translation_mode"),
    }


def render_overlay_page(
    source_doc: fitz.Document,
    page_index: int,
    page: dict,
    page_blocks: list[dict],
    font_catalog: dict[str, tuple],
    font_cache: dict[str, tuple[str, str | None]],
    temp_dir: Path,
) -> fitz.Document:
    out_doc = fitz.open()
    out_doc.insert_pdf(source_doc, from_page=page_index, to_page=page_index)
    out_page = out_doc[-1]
    source_page = source_doc[page_index]
    preserved_ids = preserved_overlay_ids(page_blocks)
    for block in page_blocks:
        if block["id"] in preserved_ids or block.get("keep_original") or block.get("role") == "artifact":
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
        style = block.get("style", {})
        render_font_name, render_font_file = resolve_font_resource(
            source_doc,
            font_catalog,
            style.get("font_name"),
            font_cache,
            temp_dir,
        )
        region = core.TextRegion(
            bbox=tuple(block["bbox"]),
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
            # Fall back to a tighter fit rather than spilling into a new page for template pages.
            font, safe_font_name, safe_font_file = core.resolve_render_font(region, str(text))
            lines = core.layout_text(str(text), max(20, rect.width - 2), font, max(core.MIN_FONT_SIZE, region.font_size_hint - 1.0))
            core.draw_lines(
                out_page,
                rect,
                lines,
                font,
                max(core.MIN_FONT_SIZE, region.font_size_hint - 1.0),
                region.text_color,
                region.align,
                safe_font_name,
                safe_font_file,
                region.baseline_y,
            )
    return out_doc


def leading_marker_artifact(block: dict, page_blocks: list[dict]) -> dict | None:
    if str(block.get("role", "")) != "list_item":
        return None
    block_text = str(block.get("translated_text") or block.get("text") or "").lstrip()
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
    text = str(block.get("translated_text") or block.get("text") or "")
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


def redaction_rect_for_block(block: dict, page_blocks: list[dict]) -> fitz.Rect:
    rect = fitz.Rect(block["bbox"])
    marker = leading_marker_artifact(block, page_blocks)
    if marker is not None:
        marker_rect = fitz.Rect(marker["bbox"])
        rect = fitz.Rect(max(rect.x0, marker_rect.x1 + 1.0), rect.y0, rect.x1, rect.y1)
    role = str(block.get("role", ""))
    if role in {"footer", "header"}:
        return fitz.Rect(rect.x0, rect.y0 + 1.5, rect.x1, max(rect.y0 + 2.0, rect.y1 - 0.5))
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


def render_page_via_docx(payload: dict, page_number: int, output_pdf: Path, assets_by_id: dict[str, dict]) -> Path:
    script_dir = Path(__file__).resolve().parent
    page_payload = filtered_payload_for_page(payload, page_number, assets_by_id)
    with tempfile.TemporaryDirectory(prefix="babel-copy-build-page-") as tmp_dir_raw:
        tmp_dir = Path(tmp_dir_raw)
        docx_path = tmp_dir / f"page-{page_number:03d}.docx"
        page_json = tmp_dir / f"page-{page_number:03d}.json"
        page_json.write_text(json.dumps(page_payload, indent=2, ensure_ascii=False))
        subprocess.run(
            [sys.executable, str(Path(script_dir / "rebuild_docx.py")), str(page_json), "--output-docx", str(docx_path)],
            check=True,
        )
        subprocess.run(
            [sys.executable, str(Path(script_dir / "export_pdf.py")), str(docx_path), "--output-dir", str(tmp_dir)],
            check=True,
        )
        rendered_pdf = tmp_dir / f"{docx_path.stem}.pdf"
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        output_pdf.write_bytes(rendered_pdf.read_bytes())
    return output_pdf


def render_hybrid_document(source_pdf: Path, payload: dict, output_pdf: Path) -> Path:
    blocks = blocks_by_page(payload)
    assets_by_id = asset_map(payload)
    source_doc = fitz.open(source_pdf)
    out_doc = fitz.open()
    temp_paths: list[Path] = []
    font_catalog = build_source_font_catalog(source_doc)
    font_cache: dict[str, tuple[str, str | None]] = {}
    try:
        with tempfile.TemporaryDirectory(prefix="babel-copy-fonts-") as font_dir_raw:
            font_dir = Path(font_dir_raw)
            for page_index, page in enumerate(payload.get("pages", [])):
                page_number = int(page["page_number"])
                mode = choose_page_mode(page, assets_by_id)
                page_blocks = blocks.get(page_number, [])
                if mode == "template_overlay":
                    rendered_doc = render_overlay_page(source_doc, page_index, page, page_blocks, font_catalog, font_cache, font_dir)
                    out_doc.insert_pdf(rendered_doc)
                    rendered_doc.close()
                    continue
                with tempfile.NamedTemporaryFile(prefix=f"babel-copy-page-{page_number:03d}-", suffix=".pdf", delete=False) as tmp_file:
                    temp_path = Path(tmp_file.name)
                temp_paths.append(temp_path)
                render_page_via_docx(payload, page_number, temp_path, assets_by_id)
                rendered_doc = fitz.open(temp_path)
                out_doc.insert_pdf(rendered_doc)
                rendered_doc.close()
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
    payload = apply_custom_overrides_to_payload(json.loads(translated_blocks_json.read_text()))
    rendered = render_hybrid_document(source_pdf, payload, output_pdf)
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
