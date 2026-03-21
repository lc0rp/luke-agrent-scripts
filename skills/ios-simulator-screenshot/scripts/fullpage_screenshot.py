#!/usr/bin/env python3
"""Capture and stitch a vertically scrollable iOS Simulator screen."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


def run(cmd: list[str], *, capture_output: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=True,
        capture_output=capture_output,
        text=True,
    )


def identify(image_path: Path) -> tuple[int, int]:
    result = run(["magick", "identify", "-format", "%w %h", str(image_path)])
    width_str, height_str = result.stdout.strip().split()
    return int(width_str), int(height_str)


def normalized_rmse(left: Path, right: Path) -> float:
    result = subprocess.run(
        ["magick", "compare", "-metric", "RMSE", str(left), str(right), "null:"],
        capture_output=True,
        text=True,
        check=False,
    )
    metric_output = (result.stderr or result.stdout).strip()
    match = re.search(r"\(([^)]+)\)", metric_output)
    if not match:
        raise RuntimeError(f"Could not parse ImageMagick compare output: {metric_output}")
    return float(match.group(1))


def crop_region(
    source: Path,
    destination: Path,
    width: int,
    height: int,
    x: int,
    y: int,
    resize_percent: int | None = None,
) -> None:
    cmd = [
        "magick",
        str(source),
        "-crop",
        f"{width}x{height}+{x}+{y}",
        "+repage",
    ]
    if resize_percent is not None:
        cmd.extend(["-resize", f"{resize_percent}%"])
    cmd.append(str(destination))
    run(cmd)


def detect_overlap(
    previous_image: Path,
    next_image: Path,
    *,
    min_overlap: int,
    max_overlap: int,
    overlap_step: int,
    center_fraction: float,
    sample_resize_percent: int,
    sample_height: int,
) -> dict[str, float | int]:
    width, height = identify(previous_image)
    other_width, other_height = identify(next_image)
    if (width, height) != (other_width, other_height):
        raise RuntimeError(
            f"Image sizes differ: {previous_image.name}={width}x{height}, "
            f"{next_image.name}={other_width}x{other_height}"
        )

    fixed_sample_height = max(40, sample_height)
    search_min = max(fixed_sample_height, min_overlap)
    search_max = min(height - 1, max_overlap)
    if search_min >= search_max:
        raise RuntimeError(
            f"Invalid overlap search range {search_min}..{search_max} for height {height}"
        )

    strip_width = max(100, int(width * center_fraction))
    strip_x = (width - strip_width) // 2

    def score(overlap: int) -> float:
        with tempfile.TemporaryDirectory(prefix="ios-sim-overlap-") as tmp_dir:
            tmp = Path(tmp_dir)
            prev_crop = tmp / "prev.png"
            next_crop = tmp / "next.png"
            crop_region(
                previous_image,
                prev_crop,
                strip_width,
                fixed_sample_height,
                strip_x,
                height - overlap,
                resize_percent=sample_resize_percent,
            )
            crop_region(
                next_image,
                next_crop,
                strip_width,
                fixed_sample_height,
                strip_x,
                0,
                resize_percent=sample_resize_percent,
            )
            return normalized_rmse(prev_crop, next_crop)

    best_overlap = search_min
    best_score = float("inf")

    overlap = search_min
    while overlap <= search_max:
        current_score = score(overlap)
        if current_score < best_score:
            best_overlap = overlap
            best_score = current_score
        overlap += overlap_step

    return {
        "overlap_px": best_overlap,
        "score": best_score,
        "width": width,
        "height": height,
        "sample_height": fixed_sample_height,
    }


def stitch_images(
    images: list[Path],
    output_path: Path,
    *,
    min_overlap: int,
    max_overlap: int,
    overlap_step: int,
    center_fraction: float,
    sample_resize_percent: int,
    sample_height: int,
) -> list[dict[str, float | int | str]]:
    if not images:
        raise RuntimeError("No images to stitch.")

    if len(images) == 1:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        run(["cp", str(images[0]), str(output_path)], capture_output=False)
        return []

    output_path.parent.mkdir(parents=True, exist_ok=True)
    segments: list[Path] = []
    overlap_report: list[dict[str, float | int | str]] = []

    with tempfile.TemporaryDirectory(prefix="ios-sim-stitch-") as tmp_dir:
        tmp = Path(tmp_dir)
        first_segment = tmp / "segment-000.png"
        run(["cp", str(images[0]), str(first_segment)], capture_output=False)
        segments.append(first_segment)

        current_width, current_height = identify(images[0])
        for index in range(1, len(images)):
            previous_image = images[index - 1]
            next_image = images[index]
            overlap = detect_overlap(
                previous_image,
                next_image,
                min_overlap=min_overlap,
                max_overlap=max_overlap,
                overlap_step=overlap_step,
                center_fraction=center_fraction,
                sample_resize_percent=sample_resize_percent,
                sample_height=sample_height,
            )
            overlap_px = int(overlap["overlap_px"])
            overlap_report.append(
                {
                    "from": previous_image.name,
                    "to": next_image.name,
                    "overlap_px": overlap_px,
                    "score": overlap["score"],
                }
            )

            segment = tmp / f"segment-{index:03d}.png"
            crop_region(
                next_image,
                segment,
                current_width,
                current_height - overlap_px,
                0,
                overlap_px,
            )
            segments.append(segment)

        cmd = ["magick", *[str(segment) for segment in segments], "-append", str(output_path)]
        run(cmd)

    return overlap_report


def capture_frame(device: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    run(["xcrun", "simctl", "io", device, "screenshot", str(destination)])


def parse_args() -> argparse.Namespace:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    default_output_dir = Path("output/ios-sim-fullpage") / timestamp
    parser = argparse.ArgumentParser(
        description="Capture a full-page stitched screenshot from the booted iOS Simulator."
    )
    parser.add_argument(
        "--device",
        default="booted",
        help="Simulator device UDID or 'booted'. Default: booted",
    )
    parser.add_argument(
        "--output-dir",
        default=str(default_output_dir),
        help=f"Directory for raw captures and stitched output. Default: {default_output_dir}",
    )
    parser.add_argument(
        "--output-name",
        default="stitched-fullpage.png",
        help="Filename for the final stitched image. Default: stitched-fullpage.png",
    )
    parser.add_argument(
        "--from-dir",
        default=None,
        help="Use existing raw captures from this directory instead of interactive capture.",
    )
    parser.add_argument("--min-overlap", type=int, default=160)
    parser.add_argument("--max-overlap", type=int, default=1200)
    parser.add_argument("--overlap-step", type=int, default=8)
    parser.add_argument("--center-fraction", type=float, default=0.6)
    parser.add_argument("--sample-resize-percent", type=int, default=40)
    parser.add_argument("--sample-height", type=int, default=140)
    return parser.parse_args()


def load_existing_images(raw_dir: Path) -> list[Path]:
    images = sorted(raw_dir.glob("*.png"))
    if not images:
        raise RuntimeError(f"No PNG files found in {raw_dir}")
    return images


def interactive_capture(raw_dir: Path, device: str) -> list[Path]:
    print("Put the desired scrollable screen on the booted simulator.")
    print("Press Enter to capture, scroll in Simulator, then press Enter again.")
    print("Type 's' and press Enter when done stitching.")
    images: list[Path] = []
    frame_index = 1
    while True:
        prompt = "Capture next frame [Enter] or stitch [s]: "
        response = input(prompt).strip().lower()
        if response == "s":
            break
        if response not in ("", "c"):
            print("Use Enter to capture or 's' to stitch.")
            continue
        destination = raw_dir / f"frame-{frame_index:03d}.png"
        capture_frame(device, destination)
        print(f"Captured {destination}")
        images.append(destination)
        frame_index += 1

    if not images:
        raise RuntimeError("No frames captured.")
    return images


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    raw_dir = output_dir / "raw"
    output_path = output_dir / args.output_name

    if args.from_dir:
        images = load_existing_images(Path(args.from_dir).resolve())
    else:
        raw_dir.mkdir(parents=True, exist_ok=True)
        images = interactive_capture(raw_dir, args.device)

    report = stitch_images(
        images,
        output_path,
        min_overlap=args.min_overlap,
        max_overlap=args.max_overlap,
        overlap_step=args.overlap_step,
        center_fraction=args.center_fraction,
        sample_resize_percent=args.sample_resize_percent,
        sample_height=args.sample_height,
    )

    metadata_path = output_dir / "capture-metadata.json"
    metadata = {
        "images": [str(image) for image in images],
        "output": str(output_path),
        "overlaps": report,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Stitched screenshot: {output_path}")
    print(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    main()
