from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import shorten
from typing import Any

import fitz


RED = (1.0, 0.0, 0.0)
BLUE = (0.0, 0.22, 1.0)
BLACK = (0.0, 0.0, 0.0)
WHITE = (1.0, 1.0, 1.0)


@dataclass
class OverlayEntry:
    label: str
    bbox: list[float]
    kind: str
    text: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate page-level frozen-translation diagnostics for On.Translate jobs."
    )
    parser.add_argument("pages", help="Page number, comma list, range, or all.")
    parser.add_argument(
        "--job-dir",
        type=Path,
        help="Job directory, loop directory, or output root. Defaults to newest job under output/fidelity-loops.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory. Defaults to <job>/wip/analyze_page/pages-<spec>.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="On.Translate repo root. Defaults to current working directory.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def page_count_for_pdf(path: Path) -> int:
    doc = fitz.open(path)
    try:
        return doc.page_count
    finally:
        doc.close()


def parse_page_spec(spec: str, page_count: int) -> list[int]:
    spec = spec.strip().lower()
    if spec == "all":
        return list(range(1, page_count + 1))
    pages: set[int] = set()
    for part in re.split(r"[,\s]+", spec):
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            start = int(left)
            end = int(right)
            pages.update(range(min(start, end), max(start, end) + 1))
        else:
            pages.add(int(part))
    invalid = [page for page in pages if page < 1 or page > page_count]
    if invalid:
        raise ValueError(f"Invalid page(s) for {page_count}-page PDF: {invalid}")
    return sorted(pages)


def candidate_job_dirs(path: Path) -> list[Path]:
    if (path / "wip" / "translation" / "translated_blocks.json").exists():
        return [path]
    if (path / "jobs").exists():
        return sorted(
            [
                item
                for item in (path / "jobs").iterdir()
                if (item / "wip" / "translation" / "translated_blocks.json").exists()
            ],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
    return sorted(
        [
            item
            for item in path.glob("*/jobs/*")
            if (item / "wip" / "translation" / "translated_blocks.json").exists()
        ],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def resolve_job_dir(repo_root: Path, requested: Path | None) -> Path:
    search_root = requested.expanduser().resolve() if requested else repo_root / "output" / "fidelity-loops"
    candidates = candidate_job_dirs(search_root)
    if not candidates:
        raise FileNotFoundError(f"No frozen translation jobs found under {search_root}")
    return candidates[0]


def resolve_source_pdf(job_dir: Path, compare_report: dict[str, Any]) -> Path:
    report_path = compare_report.get("source_pdf")
    if report_path:
        path = Path(str(report_path))
        if path.exists():
            return path
    inputs = sorted((job_dir / "input").glob("*.pdf"))
    if inputs:
        return inputs[0]
    raise FileNotFoundError(f"No source PDF found for {job_dir}")


def resolve_translated_pdf(job_dir: Path, compare_report: dict[str, Any]) -> Path:
    report_path = compare_report.get("translated_pdf")
    if report_path:
        path = Path(str(report_path))
        if path.exists():
            return path
    candidates = [
        *sorted((job_dir / "completed").glob("*.pdf")),
        *sorted((job_dir / "wip" / "build").glob("*.pdf")),
    ]
    if candidates:
        return candidates[0]
    raise FileNotFoundError(f"No translated PDF found for {job_dir}")


def short_block_label(block_id: str, prefix: str) -> str:
    match = re.search(r"-b(\d+)$", str(block_id))
    if match:
        return f"{prefix}{match.group(1)}"
    return f"{prefix}{str(block_id)[-8:]}"


def rect_from_bbox(bbox: list[float]) -> fitz.Rect | None:
    if not isinstance(bbox, list) or len(bbox) != 4:
        return None
    rect = fitz.Rect([float(value) for value in bbox])
    if rect.is_empty or rect.width <= 0 or rect.height <= 0:
        return None
    return rect


def text_preview(text: str, length: int = 90) -> str:
    return shorten(" ".join(str(text).split()), width=length, placeholder="...")


def table_code_provenance(table: dict[str, Any]) -> str:
    detector = str(table.get("detector", "") or "").strip()
    if detector == "line_intersections":
        return "detector=line_intersections; code=extract_layout.tables.detect_tables -> _line_intersection_candidates"
    if detector == "legacy_runs":
        return "detector=legacy_runs; code=extract_layout.tables.detect_tables -> _legacy_run_candidates"
    if detector:
        return f"detector={detector}; code=extract_layout.tables.detect_tables"
    table_id = str(table.get("id", ""))
    if "textual" in table_id.lower():
        return "detector=textual_rows; code=extract_document.build_textual_tables"
    return "detector=unknown; code=extract_document.detect_tables/build_table_cells"


def page_payload_by_number(extract_payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {
        int(page["page_number"]): page
        for page in extract_payload.get("pages", [])
        if "page_number" in page
    }


def structure_entries(page_payload: dict[str, Any]) -> list[OverlayEntry]:
    entries: list[OverlayEntry] = []
    for index, table in enumerate(page_payload.get("tables", []) or [], 1):
        entries.append(
            OverlayEntry(
                label=f"T{index}",
                bbox=[float(value) for value in table.get("bbox", [])],
                kind="table",
                text=f"{table.get('id', '')}; {table_code_provenance(table)}",
            )
        )
        for cell in table.get("cells", []) or []:
            row = cell.get("row_index", "?")
            col = cell.get("col_index", "?")
            entries.append(
                OverlayEntry(
                    label=f"T{index}R{row}C{col}",
                    bbox=[float(value) for value in cell.get("bbox", [])],
                    kind="table_cell",
                    text=str(cell.get("text") or cell.get("id", "")),
                )
            )
    for index, block in enumerate(page_payload.get("filled_blocks", []) or [], 1):
        entries.append(
            OverlayEntry(
                label=f"F{index}",
                bbox=[float(value) for value in block.get("bbox", [])],
                kind="filled_block",
                text=str(block.get("background_color", "") or block.get("id", "")),
            )
        )
    for index, cell in enumerate(page_payload.get("filled_layout_cells", []) or [], 1):
        entries.append(
            OverlayEntry(
                label=f"LC{index}",
                bbox=[float(value) for value in cell.get("bbox", [])],
                kind=f"layout_cell:{cell.get('source', '')}",
                text=str(cell.get("id", "")),
            )
        )
    return [entry for entry in entries if rect_from_bbox(entry.bbox) is not None]


def source_text_entries(extract_payload: dict[str, Any], page_number: int) -> list[OverlayEntry]:
    entries: list[OverlayEntry] = []
    for block in extract_payload.get("blocks", []):
        if int(block.get("page_number", -1)) != page_number:
            continue
        bbox = block.get("bbox") or []
        if rect_from_bbox(bbox) is None:
            continue
        entries.append(
            OverlayEntry(
                label=short_block_label(str(block.get("id", "")), "B"),
                bbox=[float(value) for value in bbox],
                kind=str(block.get("role", "text")),
                text=text_preview(str(block.get("text", ""))),
            )
        )
    return entries


def translated_text_entries(translated_payload: dict[str, Any], page_number: int) -> list[OverlayEntry]:
    entries: list[OverlayEntry] = []
    for block in translated_payload.get("blocks", []):
        if int(block.get("page_number", -1)) != page_number:
            continue
        bbox = block.get("bbox") or []
        if rect_from_bbox(bbox) is None:
            continue
        translated = block.get("translated_text") or block.get("text", "")
        entries.append(
            OverlayEntry(
                label=short_block_label(str(block.get("id", "")), "TB"),
                bbox=[float(value) for value in bbox],
                kind=str(block.get("role", "text")),
                text=text_preview(str(translated)),
            )
        )
    return entries


def draw_label(page: fitz.Page, rect: fitz.Rect, label: str, color: tuple[float, float, float]) -> None:
    font_size = 8.0
    label_width = max(28.0, min(96.0, len(label) * 5.0 + 8.0))
    label_height = 11.0
    y0 = rect.y0 - label_height - 1.0
    if y0 < 1.0:
        y0 = rect.y0 + 1.0
    x0 = min(max(1.0, rect.x0), max(1.0, page.rect.x1 - label_width - 1.0))
    label_rect = fitz.Rect(x0, y0, x0 + label_width, y0 + label_height)
    page.draw_rect(label_rect, color=BLACK, fill=color, width=0.35, overlay=True)
    page.insert_text(
        fitz.Point(label_rect.x0 + 2.0, label_rect.y1 - 3.0),
        label,
        fontsize=font_size,
        color=WHITE,
        fontname="helv",
        overlay=True,
    )


def draw_entries(page: fitz.Page, entries: list[OverlayEntry], color: tuple[float, float, float]) -> None:
    for entry in entries:
        rect = rect_from_bbox(entry.bbox)
        if rect is None:
            continue
        page.draw_rect(rect, color=color, width=0.8, overlay=True)
        draw_label(page, rect, entry.label, color)


def add_key_pages(doc: fitz.Document, title: str, entries: list[OverlayEntry]) -> None:
    if not entries:
        page = doc.new_page(width=612, height=792)
        page.insert_textbox(fitz.Rect(36, 36, 576, 756), f"{title}\n\nNo regions.", fontsize=10, color=BLACK)
        return
    chunks = [entries[index : index + 38] for index in range(0, len(entries), 38)]
    for chunk_index, chunk in enumerate(chunks, 1):
        page = doc.new_page(width=612, height=792)
        lines = [title if chunk_index == 1 else f"{title} (continued)", ""]
        for entry in chunk:
            bbox = ", ".join(f"{value:.1f}" for value in entry.bbox)
            detail = f" - {entry.text}" if entry.text else ""
            lines.append(f"{entry.label} [{entry.kind}] ({bbox}){detail}")
        page.insert_textbox(
            fitz.Rect(36, 36, 576, 756),
            "\n".join(lines),
            fontsize=8,
            color=BLACK,
            fontname="helv",
        )


def make_overlay_pdf(
    source_pdf: Path,
    output_pdf: Path,
    pages: list[int],
    entries_by_page: dict[int, list[OverlayEntry]],
    color: tuple[float, float, float],
    title: str,
) -> None:
    source_doc = fitz.open(source_pdf)
    out = fitz.open()
    try:
        for page_number in pages:
            out.insert_pdf(source_doc, from_page=page_number - 1, to_page=page_number - 1)
            page = out[-1]
            entries = entries_by_page.get(page_number, [])
            draw_entries(page, entries, color)
            add_key_pages(out, f"{title} - page {page_number}", entries)
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        out.save(output_pdf)
    finally:
        out.close()
        source_doc.close()


def score_by_page(compare_report: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {
        int(page["page"]): page
        for page in compare_report.get("pages", [])
        if "page" in page
    }


def diagnosis_for_page(page_number: int, metrics: dict[str, Any] | None) -> list[str]:
    if not metrics:
        return [f"Page {page_number}: no compare metrics found."]
    bullets: list[str] = []
    score = metrics.get("fidelity_score")
    score_text = "n/a" if score is None else f"{float(score):.2f}"
    bullets.append(f"Page {page_number}: fidelity score {score_text}.")
    missing = metrics.get("missing_translation_blocks") or []
    if missing:
        ids = ", ".join(str(item.get("id", "")) for item in missing[:5])
        bullets.append(f"Missing or under-covered translations: {ids}.")
    line_mismatch = float(metrics.get("line_mismatch", 0.0) or 0.0)
    density_drift = float(metrics.get("density_drift", 0.0) or 0.0)
    text_block_change = float(metrics.get("text_block_change", 0.0) or 0.0)
    untranslated = float(metrics.get("untranslated_source_penalty", 0.0) or 0.0)
    if line_mismatch >= 0.3:
        bullets.append("High line/shape mismatch: preserve or redraw table and filled-cell visual styling.")
    if density_drift >= 1.0:
        bullets.append("High density drift: translated text is visually too sparse/dense or backgrounds are not being restored.")
    if text_block_change >= 0.3:
        bullets.append("Text block geometry changed materially: inspect cell-sized boxes, alignment, and font normalization.")
    if untranslated > 0:
        bullets.append("Untranslated-source penalty is active: verify translation coverage and renderer visibility for listed blocks.")
    if len(bullets) == 1:
        bullets.append("No single dominant metric stands out; inspect overlays against the compare image.")
    return bullets


def write_diagnosis(
    output_dir: Path,
    job_dir: Path,
    pages: list[int],
    score_pages: dict[int, dict[str, Any]],
    artifacts: dict[str, str],
) -> None:
    lines = [
        "# Page Analysis",
        "",
        f"- Job: `{job_dir}`",
        f"- Pages: `{', '.join(str(page) for page in pages)}`",
        "",
        "## Artifacts",
        "",
    ]
    for name, path in artifacts.items():
        lines.append(f"- {name}: `{path}`")
    lines.extend(["", "## Diagnosis", ""])
    for page_number in pages:
        for bullet in diagnosis_for_page(page_number, score_pages.get(page_number)):
            lines.append(f"- {bullet}")
    lines.append("")
    (output_dir / "diagnosis.md").write_text("\n".join(lines))


def print_diagnosis(
    pages: list[int], score_pages: dict[int, dict[str, Any]]
) -> None:
    print("diagnosis:")
    for page_number in pages:
        for bullet in diagnosis_for_page(page_number, score_pages.get(page_number)):
            print(f"- {bullet}")


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.expanduser().resolve()
    job_dir = resolve_job_dir(repo_root, args.job_dir)

    extract_payload = load_json(job_dir / "wip" / "extract" / "blocks.json")
    translated_payload = load_json(job_dir / "wip" / "translation" / "translated_blocks.json")
    compare_report = load_json(job_dir / "wip" / "compare" / "comparison-report.json")
    source_pdf = resolve_source_pdf(job_dir, compare_report)
    translated_pdf = resolve_translated_pdf(job_dir, compare_report)

    pages = parse_page_spec(args.pages, page_count_for_pdf(source_pdf))
    page_spec_slug = "all" if args.pages.strip().lower() == "all" else "-".join(str(page) for page in pages)
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else job_dir / "wip" / "analyze_page" / f"pages-{page_spec_slug}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    extract_pages = page_payload_by_number(extract_payload)
    structure_by_page = {
        page_number: structure_entries(extract_pages.get(page_number, {}))
        for page_number in pages
    }
    source_text_by_page = {
        page_number: source_text_entries(extract_payload, page_number)
        for page_number in pages
    }
    translated_text_by_page = {
        page_number: translated_text_entries(translated_payload, page_number)
        for page_number in pages
    }

    artifacts = {
        "original_structures_red": str(output_dir / "original-structures-red.pdf"),
        "original_text_blue": str(output_dir / "original-text-blue.pdf"),
        "translated_structures_red": str(output_dir / "translated-structures-red.pdf"),
        "translated_text_blue": str(output_dir / "translated-text-blue.pdf"),
        "diagnosis": str(output_dir / "diagnosis.md"),
    }

    make_overlay_pdf(
        source_pdf,
        Path(artifacts["original_structures_red"]),
        pages,
        structure_by_page,
        RED,
        "Original structures",
    )
    make_overlay_pdf(
        source_pdf,
        Path(artifacts["original_text_blue"]),
        pages,
        source_text_by_page,
        BLUE,
        "Original text blocks",
    )
    make_overlay_pdf(
        translated_pdf,
        Path(artifacts["translated_structures_red"]),
        pages,
        structure_by_page,
        RED,
        "Translated structures",
    )
    make_overlay_pdf(
        translated_pdf,
        Path(artifacts["translated_text_blue"]),
        pages,
        translated_text_by_page,
        BLUE,
        "Translated text blocks",
    )

    score_pages = score_by_page(compare_report)
    write_diagnosis(output_dir, job_dir, pages, score_pages, artifacts)

    summary = {
        "job_dir": str(job_dir),
        "source_pdf": str(source_pdf),
        "translated_pdf": str(translated_pdf),
        "pages": pages,
        "artifacts": artifacts,
        "scores": {
            str(page_number): score_pages.get(page_number, {})
            for page_number in pages
        },
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    for page_number in pages:
        metrics = score_pages.get(page_number, {})
        score = metrics.get("fidelity_score")
        score_text = "n/a" if score is None else f"{float(score):.2f}"
        print(f"page {page_number}: fidelity_score={score_text}")
    print_diagnosis(pages, score_pages)
    print(f"output_dir={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
