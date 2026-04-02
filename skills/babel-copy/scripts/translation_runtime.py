#!/usr/bin/env python3
from __future__ import annotations

import os
import shlex
import shutil
from pathlib import Path

DOTENV_FILENAME = ".env"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
TRANSLATION_PROVIDER_CHOICES = (
    "auto",
    "codex",
    "claude",
    "openai",
    "anthropic",
    "google",
)


def parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return values
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def translation_provider(cli_value: str | None = None) -> str:
    value = str(
        cli_value or os.environ.get("BABEL_COPY_TRANSLATION_PROVIDER", "auto")
    ).strip().lower()
    return value or "auto"


def detect_runtime_mode(cwd: Path, provider: str) -> str:
    if provider in {"codex", "openai"}:
        return "codex"
    if provider in {"claude", "anthropic"}:
        return "claude"
    dotenv_values = parse_dotenv(cwd / DOTENV_FILENAME) if (cwd / DOTENV_FILENAME).exists() else {}
    explicit = str(os.environ.get("BABEL_COPY_RUNTIME_MODE") or "").strip().lower()
    if explicit in {"codex", "claude"}:
        return explicit
    dotenv_openai = bool(str(dotenv_values.get("OPENAI_API_KEY") or "").strip())
    dotenv_anthropic = bool(str(dotenv_values.get("ANTHROPIC_API_KEY") or "").strip())
    env_openai = bool(str(os.environ.get("OPENAI_API_KEY") or "").strip())
    env_anthropic = bool(str(os.environ.get("ANTHROPIC_API_KEY") or "").strip())
    codex_installed = shutil.which("codex") is not None
    claude_installed = shutil.which("claude") is not None
    if (env_anthropic or dotenv_anthropic) and not (env_openai or dotenv_openai):
        return "claude"
    if (env_openai or dotenv_openai) and not (env_anthropic or dotenv_anthropic):
        return "codex"
    if claude_installed and not codex_installed:
        return "claude"
    return "codex"


def codex_model_name(model: str | None) -> str:
    return (
        model
        or os.environ.get("BABEL_COPY_OPENAI_MODEL")
        or os.environ.get("CODEX_MODEL")
        or "default"
    )


def anthropic_model_name(model: str | None) -> str:
    return model or os.environ.get("BABEL_COPY_ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)


def openai_model_name(model: str | None) -> str:
    return model or os.environ.get("BABEL_COPY_OPENAI_MODEL", DEFAULT_OPENAI_MODEL)


def claude_cli_flags() -> list[str]:
    raw_flags = str(os.environ.get("BABEL_COPY_CLAUDE_EXEC_FLAGS") or "").strip()
    if raw_flags:
        return shlex.split(raw_flags)
    return ["-p", "--output-format", "text"]
