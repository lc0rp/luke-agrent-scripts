#!/usr/bin/env python3
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a DOCX to PDF using LibreOffice")
    parser.add_argument("input_docx")
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def find_soffice() -> str | None:
    candidates = [
        shutil.which("soffice"),
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice.bin",
        "/usr/bin/soffice",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


def ensure_soffice() -> str:
    existing = find_soffice()
    if existing:
        return existing

    if platform.system() == "Darwin":
        brew = shutil.which("brew")
        if not brew:
            raise SystemExit("Missing dependency: soffice. LibreOffice is not installed and Homebrew is unavailable.")
        subprocess.run([brew, "install", "--cask", "libreoffice"], check=True)
        installed = find_soffice()
        if installed:
            return installed
        raise SystemExit("LibreOffice install finished but soffice was still not found.")

    raise SystemExit("Missing dependency: soffice. Automatic install is only implemented on macOS.")


def main() -> int:
    args = parse_args()
    input_docx = Path(args.input_docx).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    soffice = ensure_soffice()
    cmd = [
        soffice,
        "-env:UserInstallation=file:///tmp/babel_copy_lo_profile",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(input_docx),
    ]
    subprocess.run(cmd, check=True)
    output_pdf = output_dir / f"{input_docx.stem}.pdf"
    print(output_pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
