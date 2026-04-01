#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz
from PIL import Image, ImageChops, ImageOps, ImageStat


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render source and translated PDFs side by side for babel-copy QA.")
    parser.add_argument("source_pdf")
    parser.add_argument("translated_pdf")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dpi", type=int, default=120)
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


def main() -> int:
    args = parse_args()
    source_pdf = Path(args.source_pdf).expanduser().resolve()
    translated_pdf = Path(args.translated_pdf).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_doc = fitz.open(source_pdf)
    translated_doc = fitz.open(translated_pdf)

    report: dict[str, object] = {
        "source_pdf": str(source_pdf),
        "translated_pdf": str(translated_pdf),
        "source_pages": source_doc.page_count,
        "translated_pages": translated_doc.page_count,
        "page_count_mismatch": source_doc.page_count != translated_doc.page_count,
        "pages": [],
    }

    for index in range(min(source_doc.page_count, translated_doc.page_count)):
        source_image = render_page(source_doc[index], args.dpi)
        translated_image = render_page(translated_doc[index], args.dpi)
        if source_image.size != translated_image.size:
            translated_image = translated_image.resize(source_image.size)
        diff = ImageChops.difference(source_image, translated_image)
        gray_diff = ImageOps.grayscale(diff)
        stat = ImageStat.Stat(gray_diff)
        image_path = output_dir / f"page-{index + 1:03d}.png"
        make_side_by_side(source_image, translated_image).save(image_path)
        report["pages"].append(
            {
                "page": index + 1,
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
