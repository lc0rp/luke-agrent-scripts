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
import json
import shutil
from collections import defaultdict
from pathlib import Path

from block_overrides import apply_custom_overrides_to_payload
import core


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Typst source file from babel-copy translated blocks")
    parser.add_argument("translated_blocks_json")
    parser.add_argument("--output-typ", required=True)
    return parser.parse_args()


def block_render_text(block: dict) -> str:
    translated = block.get("translated_text")
    if translated is not None:
        return str(translated)
    return str(block.get("text", ""))


def typst_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def typst_length(value: float) -> str:
    return f"{round(float(value), 2)}pt"


def typst_color(value: object) -> str:
    if isinstance(value, str) and len(value) == 7 and value.startswith("#"):
        return f'rgb("{value}")'
    return 'rgb("#000000")'


def typst_font_stack(font_baseline: dict[str, str]) -> str:
    family_class = core.normalize_font_family_class(font_baseline.get("family_class")) or core.DEFAULT_FONT_BASELINE_CLASS
    if family_class == "sans":
        fonts = ["Arial", "Liberation Sans", "DejaVu Sans", "Noto Sans"]
    else:
        fonts = ["Times New Roman", "Liberation Serif", "DejaVu Serif", "Noto Serif"]
    return "(" + ", ".join(typst_string(font) for font in fonts) + ")"


def block_weight(block: dict) -> str:
    style = block.get("style", {})
    if block.get("role") in {"heading", "title", "form_label"} or style.get("bold"):
        return '"bold"'
    return '"regular"'


def block_style(block: dict) -> str:
    style = block.get("style", {})
    return '"italic"' if style.get("italic") else '"normal"'


def block_font_size(block: dict) -> str:
    style = block.get("style", {})
    font_size = style.get("font_size_hint")
    if font_size:
        return typst_length(max(8.0, min(14.0, float(font_size))))
    return "10.5pt"


def align_wrapper(alignment: str, body: str) -> str:
    if alignment == "center":
        return f"#align(center)[\n{indent(body)}\n]"
    if alignment == "right":
        return f"#align(right)[\n{indent(body)}\n]"
    return body


def indent(value: str, spaces: int = 2) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" if line else "" for line in value.splitlines())


def render_block(block: dict) -> str:
    body = (
        f"#text(size: {block_font_size(block)}, weight: {block_weight(block)}, style: {block_style(block)}, "
        f"fill: {typst_color(block.get('style', {}).get('text_fill_color'))})"
        f"[#({typst_string(block_render_text(block))})]"
    )
    return align_wrapper(str(block.get("align", "left")), body)


def stage_asset(asset: dict, assets_dir: Path) -> str | None:
    source_path = Path(str(asset.get("path") or "")).expanduser()
    if not source_path.exists():
        return None
    suffix = source_path.suffix or ".bin"
    target_path = assets_dir / f"{asset['id']}{suffix}"
    if not target_path.exists():
        shutil.copy2(source_path, target_path)
    return target_path.relative_to(assets_dir.parent).as_posix()


def render_cell(cell_data: dict, blocks_by_id: dict[str, dict], assets_by_id: dict[str, dict], assets_dir: Path) -> str:
    fragments: list[str] = []
    ordered_blocks = [blocks_by_id[block_id] for block_id in cell_data.get("block_ids", []) if block_id in blocks_by_id]
    ordered_blocks.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
    for block in ordered_blocks:
        fragments.append(f"[#({typst_string(block_render_text(block))})]")
    for asset_id in cell_data.get("signature_asset_ids", []):
        asset = assets_by_id.get(asset_id)
        if not asset:
            continue
        relative_path = stage_asset(asset, assets_dir)
        if not relative_path:
            continue
        fragments.append(f'image({typst_string(relative_path)}, width: 72pt)')
    if not fragments:
        return "[]"
    if len(fragments) == 1:
        return fragments[0]
    return "#stack(dir: ttb, spacing: 4pt, " + ", ".join(fragments) + ")"


def render_table(page: dict, table: dict, blocks_by_id: dict[str, dict], assets_by_id: dict[str, dict], assets_dir: Path) -> str:
    columns = table["columns"]
    rows = table["rows"]
    available_width = float(page["width"]) - 72.0
    scale = available_width / max(1.0, float(table["bbox"][2] - table["bbox"][0]))
    column_widths = []
    for col_index in range(len(columns) - 1):
        width_pt = max(42.0, (columns[col_index + 1] - columns[col_index]) * scale)
        column_widths.append(typst_length(width_pt))
    column_spec = "(" + ", ".join(column_widths) + ")"
    cells_by_position = {(cell["row_index"], cell["col_index"]): cell for cell in table["cells"]}
    cell_fragments: list[str] = []
    for row_index in range(len(rows) - 1):
        for col_index in range(len(columns) - 1):
            cell_fragments.append(render_cell(cells_by_position[(row_index, col_index)], blocks_by_id, assets_by_id, assets_dir))
    return (
        "#table(\n"
        f"  columns: {column_spec},\n"
        "  inset: 6pt,\n"
        "  stroke: 0.5pt,\n"
        f"  {',\n  '.join(cell_fragments)},\n"
        ")"
    )


def render_page(page: dict, page_blocks: list[dict], blocks_by_id: dict[str, dict], assets_by_id: dict[str, dict], assets_dir: Path) -> list[str]:
    lines = [
        f"#set page(width: {typst_length(page['width'])}, height: {typst_length(page['height'])}, margin: (left: 36pt, right: 36pt, top: 32pt, bottom: 32pt))",
        "",
    ]
    for block in page_blocks:
        if block.get("keep_original"):
            continue
        if block.get("table"):
            continue
        if block.get("role") == "artifact":
            continue
        lines.append(render_block(block))
        lines.append("")

    for table in sorted(page.get("tables", []), key=lambda item: item["bbox"][1]):
        lines.append(render_table(page, table, blocks_by_id, assets_by_id, assets_dir))
        lines.append("")
    return lines


def build_typst_source(payload: dict, *, assets_dir: Path) -> str:
    font_baseline = core.font_baseline_from_payload(payload)
    pages = sorted(payload.get("pages", []), key=lambda item: int(item["page_number"]))
    blocks = payload["blocks"]
    assets = payload.get("assets", [])
    if not pages:
        raise SystemExit("Expected pages metadata in translated blocks payload.")

    blocks_by_id = {block["id"]: block for block in blocks}
    assets_by_id = {asset["id"]: asset for asset in assets}
    blocks_by_page: dict[int, list[dict]] = defaultdict(list)
    for block in blocks:
        blocks_by_page[int(block["page_number"])].append(block)
    for page_blocks in blocks_by_page.values():
        page_blocks.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))

    lines = [
        "#set par(justify: false)",
        f"#set text(font: {typst_font_stack(font_baseline)}, size: 10.5pt)",
        "",
    ]
    for index, page in enumerate(pages):
        if index:
            lines.append("#pagebreak()")
            lines.append("")
        page_number = int(page["page_number"])
        lines.extend(
            render_page(
                page,
                blocks_by_page.get(page_number, []),
                blocks_by_id,
                assets_by_id,
                assets_dir,
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def write_typst_document(payload: dict, output_path: Path) -> Path:
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    assets_dir = output_path.parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_typst_source(payload, assets_dir=assets_dir))
    return output_path


def main() -> int:
    args = parse_args()
    payload = apply_custom_overrides_to_payload(json.loads(Path(args.translated_blocks_json).read_text()))
    output_path = write_typst_document(payload, Path(args.output_typ))
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
