#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz
from PIL import Image, ImageChops, ImageOps, ImageStat


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render source and translated PDFs side by side for quick visual QA."
    )
    parser.add_argument("source_pdf")
    parser.add_argument("translated_pdf")
    parser.add_argument("--output-dir", default="compare-output")
    parser.add_argument("--dpi", type=int, default=120)
    return parser.parse_args()


def render_page(page: fitz.Page, dpi: int) -> Image.Image:
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def is_nearly_blank(image: Image.Image) -> bool:
    gray = ImageOps.grayscale(image)
    stat = ImageStat.Stat(gray)
    return stat.stddev[0] < 2.0 and stat.mean[0] > 245


def make_side_by_side(left: Image.Image, right: Image.Image) -> Image.Image:
    width = left.width + right.width + 40
    height = max(left.height, right.height) + 50
    canvas = Image.new("RGB", (width, height), "white")
    canvas.paste(left, (10, 30))
    canvas.paste(right, (left.width + 30, 30))
    return canvas


def main() -> int:
    args = parse_args()
    source_path = Path(args.source_pdf).expanduser().resolve()
    translated_path = Path(args.translated_pdf).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_doc = fitz.open(source_path)
    translated_doc = fitz.open(translated_path)

    report: dict[str, object] = {
        "source_pdf": str(source_path),
        "translated_pdf": str(translated_path),
        "source_pages": source_doc.page_count,
        "translated_pages": translated_doc.page_count,
        "page_count_mismatch": source_doc.page_count != translated_doc.page_count,
        "pages": [],
    }

    compare_count = min(source_doc.page_count, translated_doc.page_count)
    for index in range(compare_count):
        source_img = render_page(source_doc[index], dpi=args.dpi)
        translated_img = render_page(translated_doc[index], dpi=args.dpi)

        if source_img.size != translated_img.size:
            translated_img = translated_img.resize(source_img.size)

        diff = ImageChops.difference(source_img, translated_img)
        gray_diff = ImageOps.grayscale(diff)
        bbox = gray_diff.getbbox()
        diff_stat = ImageStat.Stat(gray_diff)
        mean_diff = diff_stat.mean[0]
        side = make_side_by_side(source_img, translated_img)
        image_path = output_dir / f"page-{index + 1:03d}.png"
        side.save(image_path)

        page_info = {
            "page": index + 1,
            "source_blank": is_nearly_blank(source_img),
            "translated_blank": is_nearly_blank(translated_img),
            "mean_diff": round(mean_diff, 2),
            "suspicious_region": list(bbox) if bbox else None,
            "side_by_side_image": str(image_path),
        }
        if mean_diff > 55:
            page_info["warning"] = "High visual divergence. Review artifact preservation and layout drift."
        if page_info["translated_blank"] and not page_info["source_blank"]:
            page_info["warning"] = "Translated page appears unexpectedly blank."
        report["pages"].append(page_info)

    report_path = output_dir / "comparison-report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
