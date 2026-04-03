#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# [tool.uv]
# exclude-newer = "2026-03-19T14:37:22Z"
# ///
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from translation_runtime import (
    TRANSLATION_PROVIDER_CHOICES,
    detect_runtime_mode,
    translation_provider,
)

DESKTOP_TRANSLATION_BACKENDS = {"auto", "codex", "claude"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    commands = {"run", "prepare", "apply-responses"}
    if not raw_argv or raw_argv[0] not in commands:
        raw_argv = ["run", *raw_argv]

    parser = argparse.ArgumentParser(
        description="Translate babel-copy blocks through direct providers or a desktop prepare/apply flow"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run", help="Translate blocks directly with API or Google providers"
    )
    add_translation_io_arguments(run_parser)

    prepare_parser = subparsers.add_parser(
        "prepare",
        help="Write desktop-subagent translation requests",
    )
    prepare_parser.add_argument("blocks_json")
    prepare_parser.add_argument("--output-json", required=True)
    prepare_parser.add_argument("--source-lang", default="French")
    prepare_parser.add_argument("--target-lang", default="English")
    prepare_parser.add_argument("--model")
    prepare_parser.add_argument("--batch-size", type=int, default=18)
    prepare_parser.add_argument("--provider", choices=TRANSLATION_PROVIDER_CHOICES)

    apply_parser = subparsers.add_parser(
        "apply-responses",
        help="Apply desktop-subagent translation responses and produce translated_blocks.json",
    )
    apply_parser.add_argument("blocks_json")
    apply_parser.add_argument("--requests-json", required=True)
    apply_parser.add_argument("--responses-json", required=True)
    apply_parser.add_argument("--output-json", required=True)
    apply_parser.add_argument("--provider", choices=TRANSLATION_PROVIDER_CHOICES)
    return parser.parse_args(raw_argv)


def add_translation_io_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("blocks_json")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--source-lang", default="French")
    parser.add_argument("--target-lang", default="English")
    parser.add_argument("--model")
    parser.add_argument("--batch-size", type=int, default=18)
    parser.add_argument("--provider", choices=TRANSLATION_PROVIDER_CHOICES)


def translatable_blocks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = []
    for block in payload.get("blocks", []):
        if block.get("keep_original") or block.get("role") == "artifact":
            continue
        text = str(block.get("text", "")).strip()
        if not text:
            continue
        blocks.append(block)
    return blocks


def chunked(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def build_prompt(
    batch: list[dict[str, Any]], source_lang: str, target_lang: str
) -> str:
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
                candidates.append(
                    {str(key): str(value) for key, value in translations.items()}
                )
        index = start + consumed
    if not candidates:
        raise ValueError("No JSON object found in model response")
    return candidates[0]


def prepare_request_payload(
    *,
    blocks_json: Path,
    output_json: Path,
    source_lang: str,
    target_lang: str,
    batch_size: int,
    provider: str,
    model: str | None,
) -> Path:
    payload = json.loads(blocks_json.read_text())
    blocks = translatable_blocks(payload)
    batches = chunked(blocks, max(1, batch_size))
    runtime_mode = detect_runtime_mode(provider)

    requests = []
    total_batches = len(batches)
    for index, batch in enumerate(batches, start=1):
        request_id = f"batch-{index:03d}"
        requests.append(
            {
                "request_id": request_id,
                "kind": "translation_batch",
                "batch_index": index,
                "total_batches": total_batches,
                "runtime_mode": runtime_mode,
                "provider": provider,
                "model": model,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "block_ids": [str(block["id"]) for block in batch],
                "prompt": build_prompt(batch, source_lang, target_lang),
                "response_shape": {
                    "translations": {"block_id": "translated text"},
                },
                "dispatch_hint": (
                    "Send this prompt to a desktop subagent in the active Codex or Claude app. "
                    "Require a JSON-only reply that matches response_shape."
                ),
            }
        )

    request_payload = {
        "schema_version": "1.0",
        "kind": "babel_copy_translation_requests",
        "blocks_json": str(blocks_json),
        "output_json": str(output_json),
        "source_lang": source_lang,
        "target_lang": target_lang,
        "provider": provider,
        "runtime_mode": runtime_mode,
        "model": model,
        "request_count": len(requests),
        "requests": requests,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(request_payload, indent=2, ensure_ascii=False))
    return output_json


def parse_response_entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("responses"), list):
        return [entry for entry in payload["responses"] if isinstance(entry, dict)]
    if isinstance(payload, list):
        return [entry for entry in payload if isinstance(entry, dict)]
    if isinstance(payload, dict):
        entries = []
        for key, value in payload.items():
            entries.append({"request_id": str(key), "response": value})
        return entries
    raise SystemExit("Unsupported desktop response payload format")


def parse_translation_response_entry(entry: dict[str, Any]) -> dict[str, str]:
    if isinstance(entry.get("translations"), dict):
        return {str(key): str(value) for key, value in entry["translations"].items()}
    for field in ("response_json", "response"):
        if isinstance(entry.get(field), dict):
            return parse_json_response(json.dumps(entry[field], ensure_ascii=False))
    for field in ("response_text", "response"):
        value = entry.get(field)
        if isinstance(value, str):
            return parse_json_response(value)
    raise SystemExit(f"Unsupported translation response entry: {entry}")


def apply_translations_to_payload(
    payload: dict[str, Any],
    *,
    translations: dict[str, str],
    provider: str,
    runtime_mode: str,
) -> dict[str, Any]:
    missing = []
    for block in payload.get("blocks", []):
        if block.get("keep_original") or block.get("role") == "artifact":
            block["translated_text"] = block.get("text", "")
            continue
        translated = translations.get(str(block["id"]))
        if translated is None:
            missing.append(str(block["id"]))
            continue
        block["translated_text"] = translated

    if missing:
        raise SystemExit(
            f"Missing translations for block ids: {', '.join(missing[:20])}"
        )

    backend = f"{runtime_mode}_desktop_subagent"
    payload["translation_mode"] = "desktop_subagent"
    payload["auth_path_used"] = backend
    payload["translation_backend_used"] = backend
    payload["translation_backends_used"] = [backend]
    payload["runtime_mode"] = runtime_mode
    payload["translation_provider"] = provider
    return payload


def apply_response_payload(
    *,
    blocks_json: Path,
    requests_json: Path,
    responses_json: Path,
    output_json: Path,
    provider_override: str | None,
) -> Path:
    payload = json.loads(blocks_json.read_text())
    request_payload = json.loads(requests_json.read_text())
    response_payload = json.loads(responses_json.read_text())
    entries = parse_response_entries(response_payload)
    requests = request_payload.get("requests", [])
    if not isinstance(requests, list):
        raise SystemExit(f"Unsupported request payload format in {requests_json}")

    request_ids = {
        str(entry.get("request_id")) for entry in requests if isinstance(entry, dict)
    }
    translations: dict[str, str] = {}
    seen_request_ids: set[str] = set()
    for entry in entries:
        request_id = str(entry.get("request_id", "")).strip()
        if not request_id:
            raise SystemExit("Each response entry must include request_id")
        seen_request_ids.add(request_id)
        if request_ids and request_id not in request_ids:
            raise SystemExit(f"Unexpected request_id in responses: {request_id}")
        translations.update(parse_translation_response_entry(entry))

    missing_request_ids = sorted(request_ids - seen_request_ids)
    if missing_request_ids:
        raise SystemExit(
            f"Missing desktop translation responses for request_ids: {', '.join(missing_request_ids[:20])}"
        )

    provider = translation_provider(
        provider_override or request_payload.get("provider")
    )
    runtime_mode = (
        str(
            request_payload.get("runtime_mode") or detect_runtime_mode(provider)
        ).strip()
        or "codex"
    )
    final_payload = apply_translations_to_payload(
        payload,
        translations=translations,
        provider=provider,
        runtime_mode=runtime_mode,
    )
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(final_payload, indent=2, ensure_ascii=False))
    return output_json


def run_direct_translation(args: argparse.Namespace) -> int:
    provider = translation_provider(args.provider)
    if provider in DESKTOP_TRANSLATION_BACKENDS:
        raise SystemExit(
            "babel-copy no longer supports direct translation execution. "
            "Use `prepare` to write subagent requests, dispatch those prompts through the desktop app, "
            "then use `apply-responses` to build translated_blocks.json."
        )
    raise SystemExit(f"Unsupported direct translation provider: {provider}")


def main() -> int:
    args = parse_args()
    if args.command == "run":
        return run_direct_translation(args)
    if args.command == "prepare":
        blocks_json = Path(args.blocks_json).expanduser().resolve()
        output_json = Path(args.output_json).expanduser().resolve()
        provider = translation_provider(args.provider)
        result = prepare_request_payload(
            blocks_json=blocks_json,
            output_json=output_json,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            batch_size=args.batch_size,
            provider=provider,
            model=args.model,
        )
        print(result)
        return 0
    if args.command == "apply-responses":
        result = apply_response_payload(
            blocks_json=Path(args.blocks_json).expanduser().resolve(),
            requests_json=Path(args.requests_json).expanduser().resolve(),
            responses_json=Path(args.responses_json).expanduser().resolve(),
            output_json=Path(args.output_json).expanduser().resolve(),
            provider_override=args.provider,
        )
        print(result)
        return 0
    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
