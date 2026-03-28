#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Translate babel-copy blocks with codex exec")
    parser.add_argument("blocks_json")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--source-lang", default="French")
    parser.add_argument("--target-lang", default="English")
    parser.add_argument("--model")
    parser.add_argument("--batch-size", type=int, default=18)
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
        raise ValueError("Empty codex response")
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in codex response")
    payload = json.loads(raw[start : end + 1])
    translations = payload.get("translations", payload)
    if not isinstance(translations, dict):
        raise ValueError("Unexpected codex response structure")
    return {str(key): str(value) for key, value in translations.items()}


def run_codex(prompt: str, cwd: Path, model: str | None) -> dict[str, str]:
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
        return parse_json_response(output_file.read_text())


def main() -> int:
    args = parse_args()
    blocks_json = Path(args.blocks_json).expanduser().resolve()
    output_json = Path(args.output_json).expanduser().resolve()
    payload = json.loads(blocks_json.read_text())
    blocks = translatable_blocks(payload)
    batches = chunked(blocks, max(1, args.batch_size))

    all_translations: dict[str, str] = {}
    total = len(batches)
    for index, batch in enumerate(batches, start=1):
        prompt = build_prompt(batch, args.source_lang, args.target_lang)
        translations = run_codex(prompt, cwd=blocks_json.parent, model=args.model)
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

    payload["translation_mode"] = "codex_exec"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
