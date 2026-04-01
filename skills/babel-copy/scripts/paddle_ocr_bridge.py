#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import io
import json
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PaddleOCR on an image and emit JSON.")
    parser.add_argument("--image", required=True)
    parser.add_argument("--mode", choices=("lines", "text"), default="lines")
    parser.add_argument("--lang", default="en")
    return parser.parse_args()


def build_ocr(lang: str):
    from paddleocr import PaddleOCR

    constructor_variants = (
        {"use_textline_orientation": False, "lang": lang},
        {"use_angle_cls": False, "lang": lang},
        {"lang": lang},
    )
    last_error: Exception | None = None
    for kwargs in constructor_variants:
        try:
            return PaddleOCR(**kwargs)
        except TypeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError("Failed to construct PaddleOCR")


def points_to_bbox(points) -> list[float]:
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]


def flatten_lines(raw_result) -> list[tuple[list[float], str, float]]:
    if not raw_result:
        return []
    items = raw_result[0] if isinstance(raw_result, list) else raw_result
    if isinstance(items, dict) and items.get("rec_texts"):
        texts = list(items.get("rec_texts") or [])
        scores = list(items.get("rec_scores") or [])
        boxes = items.get("rec_boxes")
        if boxes is None:
            boxes = items.get("dt_polys")
        if boxes is None:
            boxes = []
        lines: list[tuple[list[float], str, float]] = []
        for index, text in enumerate(texts):
            if not str(text).strip():
                continue
            box = boxes[index]
            if hasattr(box, "tolist"):
                box = box.tolist()
            if isinstance(box, (list, tuple)) and len(box) == 4 and not isinstance(box[0], (list, tuple)):
                bbox_px = [round(float(value), 2) for value in box]
            else:
                bbox_px = points_to_bbox(box)
            confidence = float(scores[index]) if index < len(scores) else 0.0
            lines.append((bbox_px, str(text).strip(), confidence))
        return lines
    if hasattr(items, "tolist"):
        items = items.tolist()
    lines: list[tuple[list[float], str, float]] = []
    for item in items:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        points = item[0]
        content = item[1]
        if not isinstance(points, (list, tuple)) or len(points) < 4:
            continue
        if not isinstance(content, (list, tuple)) or len(content) < 2:
            continue
        text = str(content[0]).strip()
        confidence = float(content[1])
        xs = [float(point[0]) for point in points]
        ys = [float(point[1]) for point in points]
        bbox_px = [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]
        if text:
            lines.append((bbox_px, text, confidence))
    return lines


def main() -> int:
    args = parse_args()
    image_path = Path(args.image).expanduser().resolve()
    if not image_path.exists():
        raise SystemExit(f"Image not found: {image_path}")

    image = Image.open(image_path).convert("RGB")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        ocr = build_ocr(args.lang)
        result = ocr.predict(
            image_path.as_posix(),
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    lines = flatten_lines(result)

    if args.mode == "text":
        print(
            json.dumps(
                {
                    "engine": "paddle",
                    "text": "\n".join(text for _, text, _ in lines),
                    "line_count": len(lines),
                    "image_size": list(image.size),
                },
                ensure_ascii=False,
            )
        )
        return 0

    print(
        json.dumps(
            {
                "engine": "paddle",
                "line_count": len(lines),
                "image_size": list(image.size),
                "lines": [
                    {"text": text, "bbox_px": bbox_px, "confidence": confidence}
                    for bbox_px, text, confidence in lines
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
