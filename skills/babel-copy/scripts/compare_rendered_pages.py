#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "Pillow==12.1.1",
#   "PyMuPDF==1.27.2.2",
# ]
# [tool.uv]
# exclude-newer = "2026-03-19T14:37:22Z"
# ///
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import fitz
from PIL import Image, ImageChops, ImageOps, ImageStat


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render source and translated PDFs side by side for babel-copy QA.")
    parser.add_argument("source_pdf")
    parser.add_argument("translated_pdf")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dpi", type=int, default=120)
    parser.add_argument(
        "--sample-policy",
        choices=("auto", "all", "tiered", "explicit"),
        default="auto",
        help="How many pages to render for QA comparison.",
    )
    parser.add_argument(
        "--page-numbers",
        help="Comma-separated explicit 1-based page numbers to render when using --sample-policy explicit.",
    )
    parser.add_argument(
        "--manifest-json",
        help="Optional run manifest or page-batches manifest for tiered stitched QA sampling.",
    )
    parser.add_argument(
        "--translated-blocks-json",
        help="Optional translated blocks payload used to include structural and override-heavy pages in tiered sampling.",
    )
    return parser.parse_args()


def render_page(page: fitz.Page, dpi: int) -> Image.Image:
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def make_side_by_side(left: Image.Image, right: Image.Image) -> Image.Image:
    width = left.width + right.width + 40
    height = max(left.height, right.height) + 50
    canvas = Image.new("RGB", (width, height), "white")
    canvas.paste(left, (10, 30))
    canvas.paste(right, (left.width + 30, 30))
    return canvas


def parse_page_numbers(raw: str | None) -> list[int]:
    if not raw:
        return []
    values: list[int] = []
    for part in raw.split(","):
        stripped = part.strip()
        if not stripped:
            continue
        values.append(int(stripped))
    return values


def load_optional_json(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise SystemExit(f"Missing JSON payload: {resolved}")
    return json.loads(resolved.read_text())


def tiered_sample_pages(
    total_pages: int,
    *,
    manifest: dict[str, Any] | None,
    translated_payload: dict[str, Any] | None,
) -> list[int]:
    selected = {1, total_pages}
    if manifest:
        for entry in manifest.get("page_batches", []):
            if not isinstance(entry, dict):
                continue
            page_numbers = [int(value) for value in entry.get("page_numbers", [])]
            if page_numbers:
                selected.add(page_numbers[0])
                selected.add(page_numbers[-1])
    if translated_payload:
        pages_by_number = {
            int(page["page_number"]): page for page in translated_payload.get("pages", [])
        }
        signature_pages = set()
        assets_by_id = {
            str(asset.get("id")): asset for asset in translated_payload.get("assets", [])
        }
        for page_number, page in pages_by_number.items():
            if page.get("tables"):
                selected.add(page_number)
            for asset_id in page.get("asset_ids", []):
                asset = assets_by_id.get(str(asset_id))
                if asset and str(asset.get("kind")) == "signature_crop":
                    signature_pages.add(page_number)
        selected.update(signature_pages)
        for block in translated_payload.get("blocks", []):
            page_number = int(block.get("page_number", 0))
            if block.get("custom_override"):
                selected.add(page_number)
    return sorted(value for value in selected if 1 <= value <= total_pages)


def resolve_pages_to_render(
    total_pages: int,
    *,
    sample_policy: str,
    explicit_pages: list[int],
    manifest: dict[str, Any] | None,
    translated_payload: dict[str, Any] | None,
) -> tuple[list[int], str]:
    if total_pages <= 0:
        return [], sample_policy
    if sample_policy == "all":
        return list(range(1, total_pages + 1)), "all"
    if sample_policy == "explicit":
        pages = sorted({value for value in explicit_pages if 1 <= value <= total_pages})
        if not pages:
            raise SystemExit("--sample-policy explicit requires --page-numbers")
        return pages, "explicit"
    if sample_policy == "tiered":
        return tiered_sample_pages(
            total_pages, manifest=manifest, translated_payload=translated_payload
        ), "tiered"
    if total_pages <= 20:
        return list(range(1, total_pages + 1)), "all"
    return tiered_sample_pages(
        total_pages, manifest=manifest, translated_payload=translated_payload
    ), "tiered"


def main() -> int:
    args = parse_args()
    source_pdf = Path(args.source_pdf).expanduser().resolve()
    translated_pdf = Path(args.translated_pdf).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_doc = fitz.open(source_pdf)
    translated_doc = fitz.open(translated_pdf)
    manifest = load_optional_json(args.manifest_json)
    translated_payload = load_optional_json(args.translated_blocks_json)
    comparable_pages = min(source_doc.page_count, translated_doc.page_count)
    pages_to_render, resolved_policy = resolve_pages_to_render(
        comparable_pages,
        sample_policy=args.sample_policy,
        explicit_pages=parse_page_numbers(args.page_numbers),
        manifest=manifest,
        translated_payload=translated_payload,
    )

    report: dict[str, object] = {
        "source_pdf": str(source_pdf),
        "translated_pdf": str(translated_pdf),
        "source_pages": source_doc.page_count,
        "translated_pages": translated_doc.page_count,
        "page_count_mismatch": source_doc.page_count != translated_doc.page_count,
        "sample_policy": resolved_policy,
        "reviewed_pages": pages_to_render,
        "reviewed_page_count": len(pages_to_render),
        "exhaustive": len(pages_to_render) == comparable_pages,
        "pages": [],
    }

    for page_number in pages_to_render:
        index = page_number - 1
        source_image = render_page(source_doc[index], args.dpi)
        translated_image = render_page(translated_doc[index], args.dpi)
        if source_image.size != translated_image.size:
            translated_image = translated_image.resize(source_image.size)
        diff = ImageChops.difference(source_image, translated_image)
        gray_diff = ImageOps.grayscale(diff)
        stat = ImageStat.Stat(gray_diff)
        image_path = output_dir / f"page-{page_number:03d}.png"
        make_side_by_side(source_image, translated_image).save(image_path)
        report["pages"].append(
            {
                "page": page_number,
                "mean_diff": round(stat.mean[0], 2),
                "side_by_side_image": str(image_path),
            }
        )

    report_path = output_dir / "comparison-report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
