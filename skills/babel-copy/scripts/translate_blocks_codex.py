#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from openai import OpenAI

AUTH_LOG_PREFIX = "babel_copy_translation"
DOTENV_FILENAME = ".env"
MIN_API_KEY_LENGTH = 20
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
TRANSLATION_PROVIDER_CHOICES = ("auto", "codex", "claude", "openai", "anthropic", "google")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Translate babel-copy blocks with Codex or Claude Code")
    parser.add_argument("blocks_json")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--source-lang", default="French")
    parser.add_argument("--target-lang", default="English")
    parser.add_argument("--model")
    parser.add_argument("--batch-size", type=int, default=18)
    parser.add_argument("--provider", choices=TRANSLATION_PROVIDER_CHOICES)
    return parser.parse_args()


def translatable_blocks(payload: dict) -> list[dict]:
    blocks = []
    for block in payload.get("blocks", []):
        if block.get("keep_original") or block.get("role") == "artifact":
            continue
        text = str(block.get("text", "")).strip()
        if not text:
            continue
        blocks.append(block)
    return blocks


def emit_log(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    print(f"{AUTH_LOG_PREFIX} {json.dumps(payload, ensure_ascii=True, sort_keys=True)}", file=sys.stderr)


def redact_last4(value: str | None) -> str | None:
    if not value:
        return None
    return value[-4:]


def load_json_file(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload + padding)
    except (ValueError, OSError):
        return {}
    try:
        return json.loads(decoded)
    except json.JSONDecodeError:
        return {}


def active_codex_account_email(codex_home: Path) -> str | None:
    registry = load_json_file(codex_home / "accounts" / "registry.json")
    active_key = str(registry.get("active_account_key") or "").strip()
    accounts = registry.get("accounts")
    if isinstance(accounts, list):
        for entry in accounts:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("account_key") or "").strip() == active_key:
                email = str(entry.get("email") or "").strip()
                if email:
                    return email
    auth_payload = load_json_file(codex_home / "auth.json")
    tokens = auth_payload.get("tokens")
    if isinstance(tokens, dict):
        claims = decode_jwt_payload(str(tokens.get("id_token") or ""))
        email = str(claims.get("email") or "").strip()
        if email:
            return email
    return None


def inspect_codex_auth_context() -> dict[str, Any]:
    codex_home = Path.home() / ".codex"
    auth_payload = load_json_file(codex_home / "auth.json")
    auth_mode = str(auth_payload.get("auth_mode") or "unknown").strip() or "unknown"
    email = active_codex_account_email(codex_home) if auth_mode == "chatgpt" else None
    api_key = str(auth_payload.get("OPENAI_API_KEY") or "").strip()
    auth_path = "codex_cli_unknown"
    if auth_mode == "chatgpt":
        auth_path = "codex_cli_chatgpt"
    elif auth_mode == "api_key" or api_key:
        auth_path = "codex_cli_api_key"
    return {
        "auth_mode": auth_mode,
        "account_email": email,
        "api_key_last4": redact_last4(api_key),
        "provider": "openai",
        "auth_path": auth_path,
        "config_path": str((codex_home / "config.toml").resolve()),
    }


def inspect_claude_auth_context() -> dict[str, Any]:
    claude_home = Path.home() / ".claude"
    auth_path = "claude_code_cli"
    return {
        "auth_mode": "subscription_or_local_auth",
        "account_email": None,
        "api_key_last4": None,
        "provider": "anthropic",
        "auth_path": auth_path,
        "config_path": str(claude_home.resolve()),
        "config_present": claude_home.exists(),
    }


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


def invalid_api_key_reason(api_key: str | None) -> str | None:
    key = str(api_key or "").strip()
    if not key:
        return "missing"
    if len(key) < MIN_API_KEY_LENGTH:
        return "too_short"
    lowered = key.lower()
    if lowered in {"placeholder", "changeme", "your_api_key", "openai_api_key", "anthropic_api_key"}:
        return "placeholder"
    if set(lowered) <= {"x", "*", ".", "-", "_"}:
        return "placeholder"
    return None


def api_key_candidates(cwd: Path, env_var: str, source_prefix: str) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    dotenv_path = cwd / DOTENV_FILENAME
    dotenv_values = parse_dotenv(dotenv_path) if dotenv_path.exists() else {}
    dotenv_key = str(dotenv_values.get(env_var) or "").strip()
    if dotenv_key:
        candidates.append({"source": f"dotenv_{source_prefix}", "api_key": dotenv_key})
    env_key = str(os.environ.get(env_var) or "").strip()
    if env_key:
        candidates.append({"source": f"env_{source_prefix}", "api_key": env_key})
    return candidates


def resolve_openai_api_candidates(cwd: Path) -> list[dict[str, str]]:
    return api_key_candidates(cwd, "OPENAI_API_KEY", "openai_api_key")


def resolve_anthropic_api_candidates(cwd: Path) -> list[dict[str, str]]:
    return api_key_candidates(cwd, "ANTHROPIC_API_KEY", "anthropic_api_key")


def chunked(items: list[dict], size: int) -> list[list[dict]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def build_prompt(batch: list[dict], source_lang: str, target_lang: str) -> str:
    blocks_payload = []
    for block in batch:
        blocks_payload.append(
            {
                "block_id": block["id"],
                "page_number": block["page_number"],
                "role": block.get("role"),
                "text": block.get("text"),
            }
        )
    return f"""Translate the following document blocks from {source_lang} to {target_lang}.

Requirements:
- Return JSON only.
- Preserve legal/compliance meaning accurately.
- Keep numbering stable.
- Preserve entity names, emails, addresses, phone numbers, regulator acronyms, product names, and software/vendor names unless they obviously need translation.
- Preserve all-caps organization names and signature-block party names verbatim unless the source text explicitly translates them.
- Translate headers, footers, table headers, labels, captions, and body text.
- Keep terminology consistent across the batch.
- Do not explain your work.

Return exactly this shape:
{{
  "translations": {{
    "block_id": "translated text"
  }}
}}

Blocks:
{json.dumps(blocks_payload, ensure_ascii=False, indent=2)}
"""


def parse_json_response(raw: str) -> dict[str, str]:
    raw = raw.strip()
    if not raw:
        raise ValueError("Empty model response")
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:].strip()
    decoder = json.JSONDecoder()
    index = 0
    candidates: list[dict[str, str]] = []
    while True:
        start = raw.find("{", index)
        if start == -1:
            break
        try:
            payload, consumed = decoder.raw_decode(raw[start:])
        except json.JSONDecodeError:
            index = start + 1
            continue
        if isinstance(payload, dict):
            translations = payload.get("translations", payload)
            if isinstance(translations, dict):
                candidates.append({str(key): str(value) for key, value in translations.items()})
        index = start + consumed
    if not candidates:
        raise ValueError("No JSON object found in model response")
    return candidates[0]


def codex_model_name(model: str | None) -> str:
    return model or os.environ.get("BABEL_COPY_OPENAI_MODEL") or os.environ.get("CODEX_MODEL") or "default"


def anthropic_model_name(model: str | None) -> str:
    return model or os.environ.get("BABEL_COPY_ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)


def openai_model_name(model: str | None) -> str:
    return model or os.environ.get("BABEL_COPY_OPENAI_MODEL", DEFAULT_OPENAI_MODEL)


def claude_cli_flags() -> list[str]:
    raw_flags = str(os.environ.get("BABEL_COPY_CLAUDE_EXEC_FLAGS") or "").strip()
    if raw_flags:
        return shlex.split(raw_flags)
    return ["-p", "--output-format", "text"]


def log_codex_auth_context(*, cwd: Path, model: str | None) -> dict[str, Any]:
    context = inspect_codex_auth_context()
    dotenv_path = cwd / DOTENV_FILENAME
    env_key = str(os.environ.get("OPENAI_API_KEY") or "").strip()
    emit_log(
        "codex_exec_auth_context",
        auth_mode=context.get("auth_mode"),
        account_email=context.get("account_email"),
        api_key_last4=context.get("api_key_last4"),
        auth_path=context.get("auth_path"),
        provider=context.get("provider"),
        model=codex_model_name(model),
        cwd=str(cwd),
        config_path=context.get("config_path"),
        dotenv_present=dotenv_path.exists(),
        env_openai_api_key_present=bool(env_key),
        env_openai_api_key_last4=redact_last4(env_key),
    )
    return context


def log_claude_auth_context(*, cwd: Path, model: str | None) -> dict[str, Any]:
    context = inspect_claude_auth_context()
    dotenv_path = cwd / DOTENV_FILENAME
    env_key = str(os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    emit_log(
        "claude_exec_auth_context",
        auth_mode=context.get("auth_mode"),
        account_email=context.get("account_email"),
        auth_path=context.get("auth_path"),
        provider=context.get("provider"),
        model=anthropic_model_name(model),
        cwd=str(cwd),
        config_path=context.get("config_path"),
        config_present=context.get("config_present"),
        dotenv_present=dotenv_path.exists(),
        env_anthropic_api_key_present=bool(env_key),
        env_anthropic_api_key_last4=redact_last4(env_key),
        cli_flags=claude_cli_flags(),
    )
    return context


def run_codex(prompt: str, cwd: Path, model: str | None) -> tuple[dict[str, str], dict[str, Any]]:
    if shutil.which("codex") is None:
        raise FileNotFoundError("codex executable not found")
    context = log_codex_auth_context(cwd=cwd, model=model)
    with tempfile.TemporaryDirectory(prefix="babel-copy-codex-") as tmp_raw:
        tmp_dir = Path(tmp_raw)
        output_file = tmp_dir / "last-message.txt"
        cmd = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "-C",
            str(cwd),
            "--ephemeral",
            "--dangerously-bypass-approvals-and-sandbox",
            "-o",
            str(output_file),
            "-",
        ]
        if model:
            cmd.extend(["--model", model])
        subprocess.run(cmd, input=prompt, text=True, check=True)
        return parse_json_response(output_file.read_text()), context


def run_claude(prompt: str, cwd: Path, model: str | None) -> tuple[dict[str, str], dict[str, Any]]:
    if shutil.which("claude") is None:
        raise FileNotFoundError("claude executable not found")
    context = log_claude_auth_context(cwd=cwd, model=model)
    cmd = [
        "claude",
        *claude_cli_flags(),
        "--dangerously-skip-permissions",
        "--add-dir",
        str(cwd),
    ]
    if "-p" in cmd or "--print" in cmd:
        cmd.extend(["--tools", ""])
    if model:
        cmd.extend(["--model", model])
    completed = subprocess.run(
        cmd,
        input=prompt,
        text=True,
        cwd=str(cwd),
        capture_output=True,
        check=True,
    )
    return parse_json_response(completed.stdout), context


def is_invalid_openai_api_key_error(exc: Exception) -> bool:
    lowered = str(exc).lower()
    return "invalid_api_key" in lowered or "incorrect api key" in lowered


def is_invalid_anthropic_api_key_error(exc: Exception) -> bool:
    lowered = str(exc).lower()
    return "authentication_error" in lowered or "invalid x-api-key" in lowered or "invalid api key" in lowered


def run_openai(prompt: str, model: str | None, *, api_key: str) -> dict[str, str]:
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=openai_model_name(model),
        input=prompt,
    )
    raw = response.output_text
    if not raw:
        raw = response.model_dump_json()
    return parse_json_response(raw)


def run_anthropic(prompt: str, model: str | None, *, api_key: str) -> dict[str, str]:
    payload = {
        "model": anthropic_model_name(model),
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    request = Request(
        ANTHROPIC_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
        },
        method="POST",
    )
    try:
        raw = urlopen(request, timeout=60).read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(body or str(exc)) from exc
    response_payload = json.loads(raw)
    fragments = []
    for item in response_payload.get("content", []):
        if isinstance(item, dict) and item.get("type") == "text":
            fragments.append(str(item.get("text") or ""))
    response_text = "".join(fragments).strip()
    if not response_text:
        response_text = raw
    return parse_json_response(response_text)


def google_translate_text(text: str, source_lang: str, target_lang: str) -> str:
    if not text.strip():
        return text
    source_code = {"french": "fr", "english": "en", "spanish": "es"}.get(source_lang.strip().lower(), "auto")
    target_code = {"french": "fr", "english": "en", "spanish": "es"}.get(target_lang.strip().lower(), "en")
    url = (
        "https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl={source_code}&tl={target_code}&dt=t&q={quote(text)}"
    )
    raw = urlopen(url, timeout=30).read().decode("utf-8")
    payload = json.loads(raw)
    segments = payload[0] if payload and isinstance(payload[0], list) else []
    translated = "".join(
        segment[0]
        for segment in segments
        if isinstance(segment, list) and segment and isinstance(segment[0], str)
    )
    return translated or text


def run_google_fallback(batch: list[dict], source_lang: str, target_lang: str) -> dict[str, str]:
    translations: dict[str, str] = {}
    for block in batch:
        translations[str(block["id"])] = google_translate_text(
            str(block.get("text", "")),
            source_lang=source_lang,
            target_lang=target_lang,
        )
    return translations


def try_api_fallback(
    prompt: str,
    *,
    cwd: Path,
    model: str | None,
    batch_index: int,
    total_batches: int,
    candidates: list[dict[str, str]],
    run_api,
    api_name: str,
    model_name: str,
    invalid_key_check,
) -> tuple[dict[str, str], str] | None:
    dotenv_path = cwd / DOTENV_FILENAME
    env_present = bool(str(os.environ.get(f"{api_name.upper()}_API_KEY") or "").strip())
    for candidate in candidates:
        source = candidate["source"]
        api_key = candidate["api_key"]
        unusable_reason = invalid_api_key_reason(api_key)
        if unusable_reason:
            emit_log(
                f"{api_name}_api_candidate_skipped",
                source=source,
                reason=unusable_reason,
                cwd=str(cwd),
                dotenv_present=dotenv_path.exists(),
                env_api_key_present=env_present,
            )
            continue
        emit_log(
            f"{api_name}_api_candidate_selected",
            source=source,
            api_key_last4=redact_last4(api_key),
            model=model_name,
            cwd=str(cwd),
            batch=f"{batch_index}/{total_batches}",
        )
        try:
            return run_api(prompt, model=model, api_key=api_key), source
        except Exception as exc:  # pragma: no cover - live service paths are covered by integration runs
            emit_log(
                f"{api_name}_api_candidate_failed",
                source=source,
                api_key_last4=redact_last4(api_key),
                error_type=type(exc).__name__,
                invalid_api_key=invalid_key_check(exc),
                batch=f"{batch_index}/{total_batches}",
            )
            if invalid_key_check(exc):
                print(
                    f"{api_name.capitalize()} API fallback key from {source} is invalid for batch {batch_index}/{total_batches}: {exc}",
                    file=sys.stderr,
                )
            else:
                print(
                    f"{api_name.capitalize()} API fallback failed for batch {batch_index}/{total_batches} using {source}: {exc}",
                    file=sys.stderr,
                )
    return None


def try_openai_fallback(
    prompt: str,
    *,
    cwd: Path,
    model: str | None,
    batch_index: int,
    total_batches: int,
) -> tuple[dict[str, str], str] | None:
    return try_api_fallback(
        prompt,
        cwd=cwd,
        model=model,
        batch_index=batch_index,
        total_batches=total_batches,
        candidates=resolve_openai_api_candidates(cwd),
        run_api=run_openai,
        api_name="openai",
        model_name=openai_model_name(model),
        invalid_key_check=is_invalid_openai_api_key_error,
    )


def try_anthropic_fallback(
    prompt: str,
    *,
    cwd: Path,
    model: str | None,
    batch_index: int,
    total_batches: int,
) -> tuple[dict[str, str], str] | None:
    return try_api_fallback(
        prompt,
        cwd=cwd,
        model=model,
        batch_index=batch_index,
        total_batches=total_batches,
        candidates=resolve_anthropic_api_candidates(cwd),
        run_api=run_anthropic,
        api_name="anthropic",
        model_name=anthropic_model_name(model),
        invalid_key_check=is_invalid_anthropic_api_key_error,
    )


def translation_provider(cli_value: str | None = None) -> str:
    value = str(cli_value or os.environ.get("BABEL_COPY_TRANSLATION_PROVIDER", "auto")).strip().lower()
    return value or "auto"


def detect_runtime_mode(cwd: Path, provider: str) -> str:
    if provider in {"codex", "openai"}:
        return "codex"
    if provider in {"claude", "anthropic"}:
        return "claude"
    explicit = str(os.environ.get("BABEL_COPY_RUNTIME_MODE") or "").strip().lower()
    if explicit in {"codex", "claude"}:
        return explicit
    dotenv_values = parse_dotenv(cwd / DOTENV_FILENAME) if (cwd / DOTENV_FILENAME).exists() else {}
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


def fallback_to_google(
    batch: list[dict],
    *,
    source_lang: str,
    target_lang: str,
    batch_index: int,
    total_batches: int,
    cwd: Path,
) -> tuple[dict[str, str], str, str]:
    emit_log("google_translate_fallback_selected", source="google_translate", batch=f"{batch_index}/{total_batches}", cwd=str(cwd))
    translations = run_google_fallback(batch, source_lang=source_lang, target_lang=target_lang)
    return translations, "google_translate_fallback", "google_translate"


def translate_with_codex_family(
    prompt: str,
    batch: list[dict],
    *,
    cwd: Path,
    model: str | None,
    source_lang: str,
    target_lang: str,
    batch_index: int,
    total_batches: int,
) -> tuple[dict[str, str], str, str]:
    try:
        translations, codex_context = run_codex(prompt, cwd=cwd, model=model)
        backend = str(codex_context.get("auth_path") or "codex_cli_unknown")
        return translations, "codex_exec", backend
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as exc:
        print(f"codex exec failed for batch {batch_index}/{total_batches}; falling back to OpenAI API: {exc}", file=sys.stderr)
        emit_log("codex_exec_failed", batch=f"{batch_index}/{total_batches}", cwd=str(cwd), error_type=type(exc).__name__)
        openai_result = try_openai_fallback(
            prompt,
            cwd=cwd,
            model=model,
            batch_index=batch_index,
            total_batches=total_batches,
        )
        if openai_result is not None:
            translations, backend = openai_result
            return translations, "openai_responses", backend
        print(
            f"OpenAI API fallback unavailable or failed for batch {batch_index}/{total_batches}; falling back to Google Translate",
            file=sys.stderr,
        )
        return fallback_to_google(
            batch,
            source_lang=source_lang,
            target_lang=target_lang,
            batch_index=batch_index,
            total_batches=total_batches,
            cwd=cwd,
        )


def translate_with_claude_family(
    prompt: str,
    batch: list[dict],
    *,
    cwd: Path,
    model: str | None,
    source_lang: str,
    target_lang: str,
    batch_index: int,
    total_batches: int,
) -> tuple[dict[str, str], str, str]:
    try:
        translations, claude_context = run_claude(prompt, cwd=cwd, model=model)
        backend = str(claude_context.get("auth_path") or "claude_code_cli")
        return translations, "claude_exec", backend
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as exc:
        print(f"claude exec failed for batch {batch_index}/{total_batches}; falling back to Anthropic API: {exc}", file=sys.stderr)
        emit_log("claude_exec_failed", batch=f"{batch_index}/{total_batches}", cwd=str(cwd), error_type=type(exc).__name__)
        anthropic_result = try_anthropic_fallback(
            prompt,
            cwd=cwd,
            model=model,
            batch_index=batch_index,
            total_batches=total_batches,
        )
        if anthropic_result is not None:
            translations, backend = anthropic_result
            return translations, "anthropic_messages", backend
        print(
            f"Anthropic API fallback unavailable or failed for batch {batch_index}/{total_batches}; falling back to Google Translate",
            file=sys.stderr,
        )
        return fallback_to_google(
            batch,
            source_lang=source_lang,
            target_lang=target_lang,
            batch_index=batch_index,
            total_batches=total_batches,
            cwd=cwd,
        )


def main() -> int:
    args = parse_args()
    blocks_json = Path(args.blocks_json).expanduser().resolve()
    output_json = Path(args.output_json).expanduser().resolve()
    payload = json.loads(blocks_json.read_text())
    blocks = translatable_blocks(payload)
    batches = chunked(blocks, max(1, args.batch_size))

    all_translations: dict[str, str] = {}
    total = len(batches)
    provider = translation_provider(args.provider)
    runtime_mode = detect_runtime_mode(blocks_json.parent, provider)
    translation_mode = f"{runtime_mode}_exec" if runtime_mode in {"codex", "claude"} else provider
    auth_path_used = f"{runtime_mode}_unknown" if runtime_mode in {"codex", "claude"} else provider
    translation_backend_used = auth_path_used
    backends_used: set[str] = set()

    for index, batch in enumerate(batches, start=1):
        prompt = build_prompt(batch, args.source_lang, args.target_lang)
        if provider == "google":
            translations, translation_mode, translation_backend_used = fallback_to_google(
                batch,
                source_lang=args.source_lang,
                target_lang=args.target_lang,
                batch_index=index,
                total_batches=total,
                cwd=blocks_json.parent,
            )
        elif provider == "openai":
            openai_result = try_openai_fallback(
                prompt,
                cwd=blocks_json.parent,
                model=args.model,
                batch_index=index,
                total_batches=total,
            )
            if openai_result is None:
                translations, translation_mode, translation_backend_used = fallback_to_google(
                    batch,
                    source_lang=args.source_lang,
                    target_lang=args.target_lang,
                    batch_index=index,
                    total_batches=total,
                    cwd=blocks_json.parent,
                )
            else:
                translations, translation_backend_used = openai_result
                translation_mode = "openai_responses"
        elif provider == "anthropic":
            anthropic_result = try_anthropic_fallback(
                prompt,
                cwd=blocks_json.parent,
                model=args.model,
                batch_index=index,
                total_batches=total,
            )
            if anthropic_result is None:
                translations, translation_mode, translation_backend_used = fallback_to_google(
                    batch,
                    source_lang=args.source_lang,
                    target_lang=args.target_lang,
                    batch_index=index,
                    total_batches=total,
                    cwd=blocks_json.parent,
                )
            else:
                translations, translation_backend_used = anthropic_result
                translation_mode = "anthropic_messages"
        elif provider == "claude" or (provider == "auto" and runtime_mode == "claude"):
            translations, translation_mode, translation_backend_used = translate_with_claude_family(
                prompt,
                batch,
                cwd=blocks_json.parent,
                model=args.model,
                source_lang=args.source_lang,
                target_lang=args.target_lang,
                batch_index=index,
                total_batches=total,
            )
        else:
            translations, translation_mode, translation_backend_used = translate_with_codex_family(
                prompt,
                batch,
                cwd=blocks_json.parent,
                model=args.model,
                source_lang=args.source_lang,
                target_lang=args.target_lang,
                batch_index=index,
                total_batches=total,
            )

        auth_path_used = translation_backend_used
        backends_used.add(translation_backend_used)
        all_translations.update(translations)
        print(f"completed batch {index}/{total}", file=sys.stderr)

    missing = []
    for block in payload.get("blocks", []):
        if block.get("keep_original") or block.get("role") == "artifact":
            block["translated_text"] = block.get("text", "")
            continue
        translated = all_translations.get(block["id"])
        if translated is None:
            missing.append(block["id"])
            continue
        block["translated_text"] = translated

    if missing:
        raise SystemExit(f"Missing translations for block ids: {', '.join(missing[:20])}")

    payload["translation_mode"] = translation_mode
    payload["auth_path_used"] = auth_path_used
    payload["translation_backend_used"] = translation_backend_used
    payload["translation_backends_used"] = sorted(backends_used)
    payload["runtime_mode"] = runtime_mode
    payload["translation_provider"] = provider
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
