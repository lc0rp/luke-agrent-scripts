#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# [tool.uv]
# exclude-newer = "2026-03-19T14:37:22Z"
# ///
from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import sys
from pathlib import Path
from typing import Any

from profiling import create_profiler, resolve_profile_path
from run_manifest import stable_json_hash, update_run_manifest
from translation_runtime import (
    TRANSLATION_PROVIDER_CHOICES,
    detect_runtime_mode,
    translation_provider,
)

DESKTOP_TRANSLATION_BACKENDS = {"auto", "codex", "claude"}
DEFAULT_BATCH_SIZE = 64
DEFAULT_BATCH_CHAR_BUDGET = 12000
PAGE_BREAK_BATCH_FILL_RATIO = 0.72


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
    prepare_parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    prepare_parser.add_argument(
        "--batch-char-budget",
        type=int,
        default=DEFAULT_BATCH_CHAR_BUDGET,
    )
    prepare_parser.add_argument("--provider", choices=TRANSLATION_PROVIDER_CHOICES)
    add_profiler_arguments(prepare_parser)

    apply_parser = subparsers.add_parser(
        "apply-responses",
        help="Apply desktop-subagent translation responses and produce translated_blocks.json",
    )
    apply_parser.add_argument("blocks_json")
    apply_parser.add_argument("--requests-json", required=True)
    apply_parser.add_argument("--responses-json", required=True)
    apply_parser.add_argument("--output-json", required=True)
    apply_parser.add_argument("--provider", choices=TRANSLATION_PROVIDER_CHOICES)
    add_profiler_arguments(apply_parser)
    return parser.parse_args(raw_argv)


def add_translation_io_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("blocks_json")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--source-lang", default="French")
    parser.add_argument("--target-lang", default="English")
    parser.add_argument("--model")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--batch-char-budget",
        type=int,
        default=DEFAULT_BATCH_CHAR_BUDGET,
    )
    parser.add_argument("--provider", choices=TRANSLATION_PROVIDER_CHOICES)
    add_profiler_arguments(parser)


def add_profiler_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profiler", action="store_true")
    parser.add_argument("--profiler-commands")
    parser.add_argument("--profiler-output-dir")


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


def block_translation_fingerprint(block: dict[str, Any]) -> str:
    existing = str(block.get("fingerprint", "")).strip()
    if existing:
        return existing
    return stable_json_hash(
        {
            "id": str(block.get("id", "")),
            "page_number": int(block.get("page_number", 0) or 0),
            "role": str(block.get("role", "")),
            "bbox": [round(float(value), 2) for value in block.get("bbox", [])],
            "text": str(block.get("text", "")),
            "table": block.get("table"),
        }
    )


def translated_blocks_cache_path(blocks_json: Path) -> Path:
    return blocks_json.parent / "translated_blocks.json"


def translation_cache_scope_matches(
    payload: dict[str, Any],
    *,
    source_lang: str,
    target_lang: str,
) -> bool:
    cached_source_lang = str(payload.get("translation_source_lang", "")).strip()
    cached_target_lang = str(payload.get("translation_target_lang", "")).strip()
    if not cached_source_lang or not cached_target_lang:
        return False
    return (
        cached_source_lang == source_lang.strip()
        and cached_target_lang == target_lang.strip()
    )


def cached_translations_for_blocks(
    blocks: list[dict[str, Any]],
    *,
    translated_blocks_path: Path,
    source_lang: str,
    target_lang: str,
) -> dict[str, str]:
    if not translated_blocks_path.exists():
        return {}
    payload = json.loads(translated_blocks_path.read_text())
    if not translation_cache_scope_matches(
        payload,
        source_lang=source_lang,
        target_lang=target_lang,
    ):
        return {}
    previous_blocks = {
        str(block.get("id", "")): block
        for block in payload.get("blocks", [])
        if isinstance(block, dict)
    }
    cached: dict[str, str] = {}
    for block in blocks:
        previous = previous_blocks.get(str(block.get("id", "")))
        if not previous:
            continue
        if block_translation_fingerprint(previous) != block_translation_fingerprint(block):
            continue
        translated = previous.get("translated_text")
        if translated is None:
            continue
        cached[str(block["id"])] = str(translated)
    return cached


def translation_block_prompt_payload(block: dict[str, Any]) -> dict[str, Any]:
    return {
        "block_id": block["id"],
        "page_number": block["page_number"],
        "role": block.get("role"),
        "text": block.get("text"),
    }


def prompt_prefix(source_lang: str, target_lang: str) -> str:
    return (
        f"Translate the following document blocks from {source_lang} to {target_lang}.\n\n"
        "Requirements:\n"
        "- Return JSON only.\n"
        "- Preserve legal/compliance meaning accurately.\n"
        "- Keep numbering stable.\n"
        "- Preserve entity names, emails, addresses, phone numbers, regulator acronyms, product names, and software/vendor names unless they obviously need translation.\n"
        "- Preserve all-caps organization names and signature-block party names verbatim unless the source text explicitly translates them.\n"
        "- Translate headers, footers, table headers, labels, captions, and body text.\n"
        "- Keep terminology consistent across the batch.\n"
        "- Do not explain your work.\n\n"
        "Return exactly this shape:\n"
        "{\n"
        '  "translations": {\n'
        '    "block_id": "translated text"\n'
        "  }\n"
        "}\n\n"
        "Blocks:\n"
    )


def serialize_prompt_payloads(blocks_payload: list[dict[str, Any]]) -> str:
    return json.dumps(blocks_payload, ensure_ascii=False, indent=2)


def indented_payload_json(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    return "\n".join(f"  {line}" for line in serialized.splitlines())


def appended_payload_chars(current_payload_chars: int, payload: dict[str, Any]) -> int:
    payload_chars = len(indented_payload_json(payload))
    if current_payload_chars == 0:
        return len("[\n") + payload_chars + len("\n]")
    return current_payload_chars + len(",\n") + payload_chars


def prompt_chars_for_payload_chars(
    payload_chars: int, source_lang: str, target_lang: str
) -> int:
    return len(prompt_prefix(source_lang, target_lang)) + payload_chars + len("\n")


def build_prompt_from_payloads(
    blocks_payload: list[dict[str, Any]], source_lang: str, target_lang: str
) -> str:
    return (
        prompt_prefix(source_lang, target_lang)
        + serialize_prompt_payloads(blocks_payload)
        + "\n"
    )


def build_prompt(
    batch: list[dict[str, Any]], source_lang: str, target_lang: str
) -> str:
    return build_prompt_from_payloads(
        [translation_block_prompt_payload(block) for block in batch],
        source_lang,
        target_lang,
    )


def chunk_translation_batches(
    items: list[dict[str, Any]],
    *,
    source_lang: str,
    target_lang: str,
    max_blocks: int,
    max_prompt_chars: int,
) -> list[list[dict[str, Any]]]:
    max_blocks = max(1, max_blocks)
    max_prompt_chars = max(1, max_prompt_chars)
    batches: list[list[dict[str, Any]]] = []
    current_blocks: list[dict[str, Any]] = []
    current_payload_chars = 0
    current_prompt_chars = 0

    def flush_current() -> None:
        nonlocal current_blocks, current_payload_chars, current_prompt_chars
        if not current_blocks:
            return
        batches.append(current_blocks)
        current_blocks = []
        current_payload_chars = 0
        current_prompt_chars = 0

    for block in items:
        payload = translation_block_prompt_payload(block)
        block_page = int(block.get("page_number", 0) or 0)
        previous_page = (
            int(current_blocks[-1].get("page_number", 0) or 0)
            if current_blocks
            else block_page
        )
        if (
            current_blocks
            and block_page != previous_page
            and current_prompt_chars >= int(max_prompt_chars * PAGE_BREAK_BATCH_FILL_RATIO)
        ):
            flush_current()

        candidate_payload_chars = appended_payload_chars(current_payload_chars, payload)
        candidate_prompt_chars = prompt_chars_for_payload_chars(
            candidate_payload_chars,
            source_lang,
            target_lang,
        )
        if current_blocks and (
            len(current_blocks) >= max_blocks
            or candidate_prompt_chars > max_prompt_chars
        ):
            flush_current()
            candidate_payload_chars = appended_payload_chars(0, payload)
            candidate_prompt_chars = prompt_chars_for_payload_chars(
                candidate_payload_chars,
                source_lang,
                target_lang,
            )

        current_blocks.append(block)
        current_payload_chars = candidate_payload_chars
        current_prompt_chars = candidate_prompt_chars

    flush_current()
    return batches


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
    batch_char_budget: int,
    provider: str,
    model: str | None,
    profiler=None,
) -> Path:
    with profiler.stage("read_blocks_json", path=blocks_json) if profiler else nullcontext():
        payload = json.loads(blocks_json.read_text())
    with profiler.stage("collect_translatable_blocks") if profiler else nullcontext():
        blocks = translatable_blocks(payload)
        cached_translations = cached_translations_for_blocks(
            blocks,
            translated_blocks_path=translated_blocks_cache_path(blocks_json),
            source_lang=source_lang,
            target_lang=target_lang,
        )
        pending_blocks = [
            block for block in blocks if str(block["id"]) not in cached_translations
        ]
        batches = chunk_translation_batches(
            pending_blocks,
            source_lang=source_lang,
            target_lang=target_lang,
            max_blocks=batch_size,
            max_prompt_chars=batch_char_budget,
        )
        runtime_mode = detect_runtime_mode(provider)

    requests = []
    total_batches = len(batches)
    with profiler.stage("build_requests", batch_count=total_batches) if profiler else nullcontext():
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
                    "page_numbers": sorted(
                        {int(block["page_number"]) for block in batch}
                    ),
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
        "batch_size": max(1, batch_size),
        "batch_char_budget": max(1, batch_char_budget),
        "cached_translation_count": len(cached_translations),
        "cached_translations": cached_translations,
        "request_count": len(requests),
        "requests": requests,
    }
    if profiler:
        profiler.set_counter("block_count", len(blocks))
        profiler.set_counter("cached_translation_count", len(cached_translations))
        profiler.set_counter("request_count", len(requests))
        profiler.set_counter(
            "prompt_char_count",
            sum(len(str(request.get("prompt", ""))) for request in requests),
        )
    with profiler.stage("write_requests_json", path=output_json) if profiler else nullcontext():
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(request_payload, indent=2, ensure_ascii=False))
        update_run_manifest(
            blocks_json.parent / "run-manifest.json",
            {
                "translate_prepare": {
                    "blocks_json": str(blocks_json),
                    "translation_requests_json": str(output_json),
                    "request_count": len(requests),
                    "cached_translation_count": len(cached_translations),
                }
            },
        )
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
    source_lang: str,
    target_lang: str,
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
    payload["translation_source_lang"] = source_lang
    payload["translation_target_lang"] = target_lang
    return payload


def apply_response_payload(
    *,
    blocks_json: Path,
    requests_json: Path,
    responses_json: Path,
    output_json: Path,
    provider_override: str | None,
    profiler=None,
) -> Path:
    with profiler.stage("read_inputs") if profiler else nullcontext():
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
    cached_translations = request_payload.get("cached_translations", {})
    if isinstance(cached_translations, dict):
        translations.update(
            {str(key): str(value) for key, value in cached_translations.items()}
        )
    with profiler.stage("parse_responses", response_count=len(entries)) if profiler else nullcontext():
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
    source_lang = str(request_payload.get("source_lang", "")).strip()
    target_lang = str(request_payload.get("target_lang", "")).strip()
    with profiler.stage("apply_translations") if profiler else nullcontext():
        final_payload = apply_translations_to_payload(
            payload,
            translations=translations,
            provider=provider,
            runtime_mode=runtime_mode,
            source_lang=source_lang,
            target_lang=target_lang,
        )
    if profiler:
        profiler.set_counter("request_count", len(request_ids))
        profiler.set_counter("response_count", len(entries))
        profiler.set_counter("translated_block_count", len(translations))
    with profiler.stage("write_translated_blocks", path=output_json) if profiler else nullcontext():
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(final_payload, indent=2, ensure_ascii=False))
        update_run_manifest(
            output_json.parent / "run-manifest.json",
            {
                "translate_apply": {
                    "translated_blocks_json": str(output_json),
                    "request_count": len(request_ids),
                    "response_count": len(entries),
                    "cached_translation_count": len(cached_translations)
                    if isinstance(cached_translations, dict)
                    else 0,
                }
            },
        )
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
    profiler = create_profiler(
        resolve_profile_path(
            cli_enabled=bool(getattr(args, "profiler", False)),
            cli_commands=getattr(args, "profiler_commands", None),
            cli_output_dir=getattr(args, "profiler_output_dir", None),
            command=f"translate_blocks_desktop:{args.command}",
            search_from=Path.cwd(),
            context_paths=[
                Path(getattr(args, "blocks_json", ".")).expanduser(),
                Path(getattr(args, "output_json", ".")).expanduser(),
                Path(getattr(args, "requests_json", ".")).expanduser(),
                Path(getattr(args, "responses_json", ".")).expanduser(),
            ],
        ),
        command=f"translate_blocks_desktop:{args.command}",
        metadata={"command": args.command},
    )
    try:
        if args.command == "run":
            result = run_direct_translation(args)
            profiler.finish(status="ok")
            return result
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
                batch_char_budget=args.batch_char_budget,
                provider=provider,
                model=args.model,
                profiler=profiler,
            )
            print(result)
            profiler.finish(status="ok")
            return 0
        if args.command == "apply-responses":
            result = apply_response_payload(
                blocks_json=Path(args.blocks_json).expanduser().resolve(),
                requests_json=Path(args.requests_json).expanduser().resolve(),
                responses_json=Path(args.responses_json).expanduser().resolve(),
                output_json=Path(args.output_json).expanduser().resolve(),
                provider_override=args.provider,
                profiler=profiler,
            )
            print(result)
            profiler.finish(status="ok")
            return 0
        raise SystemExit(f"Unsupported command: {args.command}")
    except BaseException as exc:
        profiler.finish(
            status="error",
            error={"type": type(exc).__name__, "message": str(exc)},
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
