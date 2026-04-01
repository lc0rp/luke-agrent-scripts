#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-$PWD/.venv-babel-paddle}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Missing Python interpreter: $PYTHON_BIN" >&2
  echo "Set PYTHON_BIN to python3.11, python3.12, or another supported Python before running this script." >&2
  exit 1
fi

"$PYTHON_BIN" -m venv "$TARGET_DIR"
"$TARGET_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
"$TARGET_DIR/bin/pip" install "paddlepaddle>=3.0.0" "paddleocr>=2.8.0" pillow numpy

echo "Paddle OCR env ready at: $TARGET_DIR"
echo "Use it with:"
echo "  export BABEL_COPY_PADDLE_PYTHON=\"$TARGET_DIR/bin/python\""
echo "  python3 scripts/run_babel_copy.py input.pdf --output-dir out --ocr-engine paddle"
