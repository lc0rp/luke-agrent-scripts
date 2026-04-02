#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# [tool.uv]
# exclude-newer = "2026-03-19T14:37:22Z"
# ///
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a Typst source file to PDF")
    parser.add_argument("input_typ")
    parser.add_argument("--output-pdf", required=True)
    return parser.parse_args()


def ensure_typst() -> str:
    typst = shutil.which("typst")
    if typst:
        return typst
    raise SystemExit("Missing dependency: typst. Install the Typst CLI to render structured rebuild pages.")


def main() -> int:
    args = parse_args()
    input_typ = Path(args.input_typ).expanduser().resolve()
    output_pdf = Path(args.output_pdf).expanduser().resolve()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    typst = ensure_typst()
    subprocess.run(
        [
            typst,
            "compile",
            str(input_typ),
            str(output_pdf),
            "--root",
            str(input_typ.parent),
        ],
        check=True,
    )
    print(output_pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
