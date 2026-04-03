#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# [tool.uv]
# exclude-newer = "2026-03-19T14:37:22Z"
# ///
from __future__ import annotations

import os

DOTENV_FILENAME = ".env"
TRANSLATION_PROVIDER_CHOICES = (
    "auto",
    "codex",
    "claude",
)


def translation_provider(cli_value: str | None = None) -> str:
    value = str(
        cli_value or os.environ.get("BABEL_COPY_TRANSLATION_PROVIDER", "auto")
    ).strip().lower()
    return value or "auto"


def detect_runtime_mode(provider: str) -> str:
    if provider == "codex":
        return "codex"
    if provider == "claude":
        return "claude"
    explicit = str(os.environ.get("BABEL_COPY_RUNTIME_MODE") or "").strip().lower()
    if explicit in {"codex", "claude"}:
        return explicit
    return "codex"
