#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the end-to-end babel-copy workflow.")
    parser.add_argument("input_pdf")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--source-lang", default="French")
    parser.add_argument("--target-lang", default="English")
    parser.add_argument("--pages")
    parser.add_argument("--magnify-factor", type=float, default=2.0)
    parser.add_argument("--dpi", type=int, default=144)
    parser.add_argument("--font-baseline", help="Visual fallback font family override: serif or sans.")
    parser.add_argument("--model")
    parser.add_argument("--batch-size", type=int, default=18)
    parser.add_argument("--skip-compare", action="store_true")
    return parser.parse_args()


def run_step(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def recommend_pages(payload: dict) -> list[int]:
    pages = payload.get("pages", [])
    if not pages:
        return []
    page_numbers = [int(page["page_number"]) for page in pages]
    recommended: list[int] = [page_numbers[0], page_numbers[-1]]
    table_pages = [int(page["page_number"]) for page in pages if page.get("tables")]
    recommended.extend(table_pages)
    complex_pages = [
        int(page["page_number"])
        for page in pages
        if page.get("page_type") in {"mixed", "scanned"} or page.get("strategy_hint") == "rebuild"
    ]
    recommended.extend(complex_pages)
    counts = Counter(int(block["page_number"]) for block in payload.get("blocks", []) if not block.get("keep_original"))
    if counts:
        recommended.append(counts.most_common(1)[0][0])
    seen: set[int] = set()
    ordered: list[int] = []
    for page_number in recommended:
        if page_number in seen:
            continue
        seen.add(page_number)
        ordered.append(page_number)
    return ordered


def write_check_notes(extract_payload: dict, translated_pdf: Path, compare_dir: Path, notes_path: Path) -> None:
    font_baseline = extract_payload.get("font_baseline", {})
    lines = [
        "# Babel Copy Check Notes",
        "",
        f"- Final PDF: `{translated_pdf}`",
        f"- Source page count: {extract_payload.get('page_count')}",
        f"- Font baseline: `{font_baseline.get('family_class', 'unknown')}` via `{font_baseline.get('source', 'unknown')}`",
        "",
        "## Recommended Visual Checks",
        "",
    ]
    for page_number in recommend_pages(extract_payload):
        page_meta = next(page for page in extract_payload["pages"] if int(page["page_number"]) == page_number)
        lines.append(
            f"- Page {page_number}: type=`{page_meta.get('page_type')}`, source=`{page_meta.get('region_source')}`, strategy_hint=`{page_meta.get('strategy_hint')}`"
        )
    if not compare_dir.exists():
        lines.extend(["", "Comparison renders were skipped."])
    else:
        lines.extend(["", f"Comparison report: `{compare_dir / 'comparison-report.json'}`"])
    lines.extend(
        [
            "",
            "## Operator Checklist",
            "",
            "- Confirm translated headers and footers are present and legible.",
            "- Confirm page count changes are intentional.",
            "- Confirm tables/forms remain structurally readable.",
            "- Confirm the rendered pages were visually checked for overlapping text and other layout defects.",
            "- Confirm arrows, connectors, logos, signatures, stamps, and handwritten marks survived appropriately.",
            "- If a page looks wrong, rerun with a narrower page selection and adjust translation or strategy instead of accepting silent drift.",
        ]
    )
    notes_path.write_text("\n".join(lines))


def main() -> int:
    args = parse_args()
    input_pdf = Path(args.input_pdf).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    script_dir = Path(__file__).resolve().parent

    extract_dir = output_dir / "extracted"
    translated_dir = output_dir / "translated"
    final_dir = output_dir / "final"
    compare_dir = output_dir / "compare"

    extract_cmd = [
        sys.executable,
        str(script_dir / "extract_document.py"),
        str(input_pdf),
        "--output-dir",
        str(extract_dir),
        "--magnify-factor",
        str(args.magnify_factor),
        "--dpi",
        str(args.dpi),
    ]
    if args.pages:
        extract_cmd.extend(["--pages", args.pages])
    if args.font_baseline:
        extract_cmd.extend(["--font-baseline", args.font_baseline])
    run_step(extract_cmd)

    blocks_json = extract_dir / "blocks.json"
    translated_json = translated_dir / "translated_blocks.json"
    translate_cmd = [
        sys.executable,
        str(script_dir / "translate_blocks_codex.py"),
        str(blocks_json),
        "--output-json",
        str(translated_json),
        "--source-lang",
        args.source_lang,
        "--target-lang",
        args.target_lang,
        "--batch-size",
        str(args.batch_size),
    ]
    if args.model:
        translate_cmd.extend(["--model", args.model])
    run_step(translate_cmd)

    final_dir.mkdir(parents=True, exist_ok=True)
    output_pdf = final_dir / f"{input_pdf.stem}.{args.target_lang.lower().replace(' ', '-')}.pdf"
    build_cmd = [
        sys.executable,
        str(script_dir / "build_final_pdf.py"),
        str(input_pdf),
        str(translated_json),
        "--output-pdf",
        str(output_pdf),
    ]
    run_step(build_cmd)

    if not args.skip_compare:
        compare_cmd = [
            sys.executable,
            str(script_dir / "compare_rendered_pages.py"),
            str(input_pdf),
            str(output_pdf),
            "--output-dir",
            str(compare_dir),
        ]
        run_step(compare_cmd)

    extract_payload = json.loads(blocks_json.read_text())
    check_notes = output_dir / "check-notes.md"
    write_check_notes(extract_payload, output_pdf, compare_dir, check_notes)

    manifest = {
        "input_pdf": str(input_pdf),
        "blocks_json": str(blocks_json),
        "translated_blocks_json": str(translated_json),
        "final_pdf": str(output_pdf),
        "compare_report": str(compare_dir / "comparison-report.json") if not args.skip_compare else None,
        "check_notes": str(check_notes),
    }
    manifest_path = output_dir / "run-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(output_pdf)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
