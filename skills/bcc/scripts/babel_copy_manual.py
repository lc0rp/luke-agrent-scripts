#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import core as tip


def is_meaningful_phrase(text: str) -> bool:
    stripped = tip.clean_text(text)
    if len(stripped) < 2:
        return False
    if "\ufffd" in stripped:
        return False
    if not re.search(r"[A-Za-zÀ-ÿ0-9]", stripped):
        return False
    return True


class ManualTranslator:
    name = "manual"

    def __init__(self, translations: dict[str, str]) -> None:
        self.translations = {tip.clean_text(key): tip.clean_text(value) for key, value in translations.items()}

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        normalized = tip.clean_text(text)
        if not is_meaningful_phrase(normalized):
            return normalized
        if normalized not in self.translations:
            raise KeyError(f"Missing manual translation for phrase: {normalized}")
        return self.translations[normalized]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manual bootstrap flow for babel-copy")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Extract unique phrases for manual translation")
    extract_parser.add_argument("input_pdf")
    extract_parser.add_argument("--output-dir", required=True)
    extract_parser.add_argument("--pages")
    extract_parser.add_argument("--magnify-factor", type=float, default=tip.DEFAULT_OCR_MAGNIFY)

    apply_parser = subparsers.add_parser("apply", help="Apply manual translations using translate-in-place composition")
    apply_parser.add_argument("input_pdf")
    apply_parser.add_argument("--translations-json", required=True)
    apply_parser.add_argument("--output-dir", required=True)
    apply_parser.add_argument("--pages")
    apply_parser.add_argument("--magnify-factor", type=float, default=tip.DEFAULT_OCR_MAGNIFY)
    apply_parser.add_argument("--overlay-background", choices=("sample", "white"), default="sample")
    apply_parser.add_argument("--source-lang", default="fr")
    apply_parser.add_argument("--target-lang", default="en")

    prepare_blocks_parser = subparsers.add_parser("prepare-blocks", help="Create a manual translation template from blocks.json")
    prepare_blocks_parser.add_argument("blocks_json")
    prepare_blocks_parser.add_argument("--output-dir", required=True)

    apply_blocks_parser = subparsers.add_parser("apply-blocks", help="Merge manual translations back into blocks.json")
    apply_blocks_parser.add_argument("blocks_json")
    apply_blocks_parser.add_argument("--translations-json", required=True)
    apply_blocks_parser.add_argument("--output-json", required=True)
    return parser.parse_args()


def collect_regions(input_pdf: Path, page_selection: str | None, magnify_factor: float):
    source_doc = tip.fitz.open(input_pdf)
    selected_pages = tip.parse_page_selection(page_selection, source_doc.page_count)
    for source_index in range(source_doc.page_count):
        page_number = source_index + 1
        if page_number not in selected_pages:
            continue
        page = source_doc[source_index]
        page_type, region_source = tip.classify_page(page)
        ocr_scale = magnify_factor if region_source == "ocr" else 1.0
        regions = (
            tip.extract_native_regions(page)
            if region_source == "native"
            else tip.extract_ocr_regions(page, magnify_factor=ocr_scale)
        )
        for region in regions:
            normalized = tip.normalize_text_for_translation(region.text)
            if not tip.should_translate(normalized):
                continue
            if not is_meaningful_phrase(normalized):
                continue
            yield {
                "page_number": page_number,
                "page_type": page_type,
                "region_source": region_source,
                "text": normalized,
                "bbox": [round(v, 2) for v in region.bbox],
                "font_size_hint": round(region.font_size_hint, 2),
                "align": region.align,
            }


def extract_command(args: argparse.Namespace) -> int:
    input_pdf = Path(args.input_pdf).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    phrase_index: dict[str, dict[str, Any]] = {}
    for region in collect_regions(input_pdf=input_pdf, page_selection=args.pages, magnify_factor=args.magnify_factor):
        text = region["text"]
        entry = phrase_index.setdefault(
            text,
            {
                "source_text": text,
                "occurrences": 0,
                "pages": set(),
                "page_types": set(),
                "region_sources": set(),
                "examples": [],
            },
        )
        entry["occurrences"] += 1
        entry["pages"].add(region["page_number"])
        entry["page_types"].add(region["page_type"])
        entry["region_sources"].add(region["region_source"])
        if len(entry["examples"]) < 3:
            entry["examples"].append(
                {
                    "page_number": region["page_number"],
                    "bbox": region["bbox"],
                    "align": region["align"],
                    "font_size_hint": region["font_size_hint"],
                }
            )

    phrases = []
    for entry in phrase_index.values():
        phrases.append(
            {
                "source_text": entry["source_text"],
                "occurrences": entry["occurrences"],
                "pages": sorted(entry["pages"]),
                "page_types": sorted(entry["page_types"]),
                "region_sources": sorted(entry["region_sources"]),
                "examples": entry["examples"],
            }
        )
    phrases.sort(key=lambda item: (-item["occurrences"], item["source_text"]))

    phrases_path = output_dir / f"{input_pdf.stem}-phrases.json"
    template_path = output_dir / f"{input_pdf.stem}-translations.template.json"
    phrases_path.write_text(json.dumps({"input_pdf": str(input_pdf), "phrase_count": len(phrases), "phrases": phrases}, indent=2, ensure_ascii=False))
    template_path.write_text(json.dumps({"input_pdf": str(input_pdf), "translations": {item["source_text"]: "" for item in phrases}}, indent=2, ensure_ascii=False))
    print(phrases_path)
    print(template_path)
    return 0


def apply_command(args: argparse.Namespace) -> int:
    input_pdf = Path(args.input_pdf).expanduser().resolve()
    translations_json = Path(args.translations_json).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    payload = json.loads(translations_json.read_text())
    translations = payload.get("translations", payload)
    if not isinstance(translations, dict):
        raise SystemExit(f"Expected a mapping in {translations_json}")
    cleaned = {tip.clean_text(str(key)): tip.clean_text(str(value)) for key, value in translations.items() if str(value).strip()}
    translator = ManualTranslator(cleaned)

    seen: set[str] = set()
    missing: list[str] = []
    for region in collect_regions(input_pdf=input_pdf, page_selection=args.pages, magnify_factor=args.magnify_factor):
        text = region["text"]
        if text in seen:
            continue
        seen.add(text)
        if text not in cleaned:
            missing.append(text)
    if missing:
        output_dir.mkdir(parents=True, exist_ok=True)
        missing_path = output_dir / f"{input_pdf.stem}-missing-translations.json"
        missing_path.write_text(json.dumps({"missing": missing}, indent=2, ensure_ascii=False))
        raise SystemExit(f"Missing {len(missing)} translations. See {missing_path}")

    output_pdf, notes_path = tip.translate_pdf(
        input_path=input_pdf,
        output_dir=output_dir,
        translator=translator,
        source_lang=args.source_lang,
        target_lang=args.target_lang,
        page_selection=args.pages,
        magnify_factor=args.magnify_factor,
        notes_path=None,
        overlay_background=args.overlay_background,
    )
    print(output_pdf)
    print(notes_path)
    return 0


def prepare_blocks_command(args: argparse.Namespace) -> int:
    blocks_json = Path(args.blocks_json).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = json.loads(blocks_json.read_text())
    entries = []
    markdown_lines = ["# Manual Translation Context", ""]
    for block in payload.get("blocks", []):
        source_text = tip.clean_text(str(block.get("text", "")))
        if not source_text or block.get("keep_original") or block.get("role") == "artifact":
            continue
        entries.append(
            {
                "block_id": block["id"],
                "page_number": block["page_number"],
                "role": block.get("role"),
                "source_text": source_text,
                "translation": "",
            }
        )
        markdown_lines.append(f"## {block['id']} (Page {block['page_number']})")
        markdown_lines.append("")
        markdown_lines.append(source_text)
        markdown_lines.append("")

    template_path = output_dir / f"{blocks_json.stem}-manual-template.json"
    context_path = output_dir / f"{blocks_json.stem}-manual-context.md"
    template_path.write_text(json.dumps({"input_payload": str(blocks_json), "translations": entries}, indent=2, ensure_ascii=False))
    context_path.write_text("\n".join(markdown_lines))
    print(template_path)
    print(context_path)
    return 0


def apply_blocks_command(args: argparse.Namespace) -> int:
    blocks_json = Path(args.blocks_json).expanduser().resolve()
    translations_json = Path(args.translations_json).expanduser().resolve()
    output_json = Path(args.output_json).expanduser().resolve()

    payload = json.loads(blocks_json.read_text())
    translation_payload = json.loads(translations_json.read_text())
    raw_entries = translation_payload.get("translations", translation_payload)

    translations_by_id: dict[str, str] = {}
    if isinstance(raw_entries, list):
        for entry in raw_entries:
            block_id = str(entry.get("block_id", "")).strip()
            if not block_id:
                continue
            translations_by_id[block_id] = tip.clean_text(str(entry.get("translation", "")))
    elif isinstance(raw_entries, dict):
        translations_by_id = {str(key): tip.clean_text(str(value)) for key, value in raw_entries.items()}
    else:
        raise SystemExit(f"Unsupported translation payload format in {translations_json}")

    missing = []
    for block in payload.get("blocks", []):
        if block.get("keep_original") or block.get("role") == "artifact":
            block["translated_text"] = block.get("text", "")
            continue
        block_id = block["id"]
        translated = translations_by_id.get(block_id, "").strip()
        if not translated:
            missing.append(block_id)
            continue
        block["translated_text"] = translated

    if missing:
        missing_path = output_json.with_name(f"{output_json.stem}-missing.json")
        missing_path.write_text(json.dumps({"missing_block_ids": missing}, indent=2, ensure_ascii=False))
        raise SystemExit(f"Missing {len(missing)} block translations. See {missing_path}")

    payload["translation_mode"] = "manual_blocks"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(output_json)
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "extract":
        return extract_command(args)
    if args.command == "apply":
        return apply_command(args)
    if args.command == "prepare-blocks":
        return prepare_blocks_command(args)
    if args.command == "apply-blocks":
        return apply_blocks_command(args)
    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
