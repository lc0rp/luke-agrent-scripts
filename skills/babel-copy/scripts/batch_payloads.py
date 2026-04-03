from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Sequence

DEFAULT_PAGE_BATCH_SIZE = 10
DEFAULT_PAGE_BATCH_THRESHOLD_PAGES = 20
DEFAULT_PAGE_BATCH_THRESHOLD_BYTES = 8 * 1024 * 1024
DEFAULT_BLOCK_GROUP_SIZE = 18


def payload_page_numbers(payload: dict[str, Any]) -> list[int]:
    return [int(page["page_number"]) for page in payload.get("pages", [])]


def payload_size_bytes(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def should_enable_multi_page_batches(
    payload: dict[str, Any],
    *,
    threshold_pages: int = DEFAULT_PAGE_BATCH_THRESHOLD_PAGES,
    threshold_bytes: int = DEFAULT_PAGE_BATCH_THRESHOLD_BYTES,
) -> bool:
    page_count = int(payload.get("page_count") or len(payload.get("pages", [])) or 0)
    return page_count > threshold_pages or payload_size_bytes(payload) > threshold_bytes


def build_page_batch_specs(
    payload: dict[str, Any],
    *,
    page_batch_size: int = DEFAULT_PAGE_BATCH_SIZE,
    threshold_pages: int = DEFAULT_PAGE_BATCH_THRESHOLD_PAGES,
    threshold_bytes: int = DEFAULT_PAGE_BATCH_THRESHOLD_BYTES,
) -> list[dict[str, Any]]:
    page_numbers = payload_page_numbers(payload)
    if not page_numbers:
        return []
    batch_size = max(1, int(page_batch_size))
    should_split = should_enable_multi_page_batches(
        payload,
        threshold_pages=threshold_pages,
        threshold_bytes=threshold_bytes,
    )
    if not should_split:
        page_groups = [page_numbers]
    else:
        page_groups = [
            page_numbers[index : index + batch_size]
            for index in range(0, len(page_numbers), batch_size)
        ]

    specs: list[dict[str, Any]] = []
    total_batches = len(page_groups)
    for index, page_group in enumerate(page_groups, start=1):
        start_page = int(page_group[0])
        end_page = int(page_group[-1])
        batch_id = f"batch-{index:03d}-p{start_page:03d}-{end_page:03d}"
        specs.append(
            {
                "batch_id": batch_id,
                "batch_index": index,
                "total_batches": total_batches,
                "page_numbers": [int(value) for value in page_group],
                "start_page": start_page,
                "end_page": end_page,
                "page_count": len(page_group),
                "is_multi_page_batching": should_split,
            }
        )
    return specs


def _page_lookup(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {
        int(page["page_number"]): deepcopy(page) for page in payload.get("pages", [])
    }


def _referenced_asset_ids_for_pages(
    payload: dict[str, Any], page_numbers: set[int], pages: list[dict[str, Any]]
) -> set[str]:
    asset_ids: set[str] = set()
    for page in pages:
        asset_ids.update(str(asset_id) for asset_id in page.get("asset_ids", []))

    for block in payload.get("blocks", []):
        if int(block.get("page_number", 0)) not in page_numbers:
            continue
        table = block.get("table")
        if not isinstance(table, dict):
            continue
        cell_id = str(table.get("cell_id") or "").strip()
        if not cell_id:
            continue
        for page in pages:
            for table_payload in page.get("tables", []):
                for cell in table_payload.get("cells", []):
                    if str(cell.get("id")) == cell_id:
                        asset_ids.update(
                            str(asset_id)
                            for asset_id in cell.get("signature_asset_ids", [])
                        )
    return asset_ids


def slice_payload_for_pages(
    payload: dict[str, Any],
    page_numbers: Sequence[int],
    *,
    renumber_pages: bool = False,
) -> dict[str, Any]:
    requested = [int(value) for value in page_numbers]
    if not requested:
        raise ValueError("Expected at least one page number for payload slicing")

    pages_by_number = _page_lookup(payload)
    missing = [value for value in requested if value not in pages_by_number]
    if missing:
        raise ValueError(f"Missing page numbers in payload: {missing}")

    selected_pages = [pages_by_number[value] for value in requested]
    selected_page_set = set(requested)
    blocks = [
        deepcopy(block)
        for block in payload.get("blocks", [])
        if int(block.get("page_number", 0)) in selected_page_set
    ]
    asset_ids = _referenced_asset_ids_for_pages(payload, selected_page_set, selected_pages)
    assets = [
        deepcopy(asset)
        for asset in payload.get("assets", [])
        if str(asset.get("id")) in asset_ids
    ]

    result = deepcopy(payload)
    result["pages"] = selected_pages
    result["blocks"] = blocks
    result["assets"] = assets
    result["page_count"] = len(selected_pages)
    result["block_count"] = len(blocks)

    if not renumber_pages:
        return result

    renumber_lookup = {original: index for index, original in enumerate(requested, start=1)}
    for page in result["pages"]:
        page["page_number"] = renumber_lookup[int(page["page_number"])]
        for table in page.get("tables", []):
            if "page_number" in table:
                table["page_number"] = page["page_number"]
    for block in result["blocks"]:
        block["page_number"] = renumber_lookup[int(block["page_number"])]
    for asset in result["assets"]:
        asset["page_number"] = renumber_lookup[int(asset["page_number"])]
    return result


def validate_page_cover(
    page_numbers: Sequence[int], expected_page_numbers: Sequence[int]
) -> None:
    actual = [int(value) for value in page_numbers]
    expected = [int(value) for value in expected_page_numbers]
    actual_set = set(actual)
    expected_set = set(expected)
    missing = sorted(expected_set - actual_set)
    duplicate = sorted({value for value in actual if actual.count(value) > 1})
    extra = sorted(actual_set - expected_set)
    if missing or duplicate or extra:
        raise ValueError(
            "Invalid page cover: "
            f"missing={missing}, duplicate={duplicate}, extra={extra}"
        )


def stitch_payloads(
    payloads: Sequence[dict[str, Any]],
    *,
    expected_page_numbers: Sequence[int] | None = None,
) -> dict[str, Any]:
    if not payloads:
        raise ValueError("Expected at least one payload to stitch")

    combined_pages: list[dict[str, Any]] = []
    page_numbers: list[int] = []

    for payload in payloads:
        for page in payload.get("pages", []):
            combined_pages.append(deepcopy(page))
            page_numbers.append(int(page["page_number"]))

    expected = (
        [int(value) for value in expected_page_numbers]
        if expected_page_numbers is not None
        else sorted(page_numbers)
    )
    validate_page_cover(page_numbers, expected)

    combined_blocks: list[dict[str, Any]] = []
    combined_assets: list[dict[str, Any]] = []
    seen_asset_ids: set[str] = set()
    seen_block_ids: set[str] = set()
    for payload in payloads:
        for block in payload.get("blocks", []):
            block_id = str(block.get("id"))
            if block_id in seen_block_ids:
                raise ValueError(f"Duplicate block id while stitching payloads: {block_id}")
            seen_block_ids.add(block_id)
            combined_blocks.append(deepcopy(block))
        for asset in payload.get("assets", []):
            asset_id = str(asset.get("id"))
            if asset_id in seen_asset_ids:
                continue
            seen_asset_ids.add(asset_id)
            combined_assets.append(deepcopy(asset))

    page_rank = {page_number: index for index, page_number in enumerate(expected)}
    combined_pages.sort(key=lambda item: page_rank[int(item["page_number"])])
    combined_blocks.sort(
        key=lambda item: (
            page_rank[int(item["page_number"])],
            float(item["bbox"][1]),
            float(item["bbox"][0]),
        )
    )
    combined_assets.sort(
        key=lambda item: (
            page_rank.get(int(item.get("page_number", 0)), 10**9),
            str(item.get("id", "")),
        )
    )

    stitched = deepcopy(payloads[0])
    stitched["pages"] = combined_pages
    stitched["blocks"] = combined_blocks
    stitched["assets"] = combined_assets
    stitched["page_count"] = len(combined_pages)
    stitched["block_count"] = len(combined_blocks)
    return stitched


def stitch_pdfs(pdf_paths: Sequence[Path], output_pdf: Path) -> Path:
    import fitz

    output_pdf = output_pdf.expanduser().resolve()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    out_doc = fitz.open()
    try:
        for pdf_path in pdf_paths:
            doc = fitz.open(Path(pdf_path).expanduser().resolve())
            try:
                out_doc.insert_pdf(doc)
            finally:
                doc.close()
        out_doc.save(output_pdf, garbage=4, deflate=True)
    finally:
        out_doc.close()
    return output_pdf


def collect_protected_terms(payload: dict[str, Any], *, limit: int = 50) -> list[str]:
    candidates: set[str] = set()
    for block in payload.get("blocks", []):
        text = str(block.get("text") or "")
        for match in re.findall(r"\b[A-Z][A-Z0-9._/-]{2,}\b", text):
            candidates.add(match)
        for match in re.findall(r"\b[\w.+-]+@[\w.-]+\.\w+\b", text):
            candidates.add(match)
    return sorted(candidates)[:limit]


def build_translation_context(
    payload: dict[str, Any],
    *,
    source_lang: str,
    target_lang: str,
) -> dict[str, Any]:
    input_pdf = str(payload.get("input_pdf") or "").strip()
    return {
        "schema_version": "1.0",
        "kind": "babel_copy_translation_context",
        "input_pdf": input_pdf,
        "document_title": Path(input_pdf).stem if input_pdf else None,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "protected_terms": collect_protected_terms(payload),
        "glossary_hints": [],
        "style_constraints": [
            "Preserve numbering.",
            "Preserve protected entities and identifiers unless they obviously require translation.",
            "Keep terminology consistent across the document.",
        ],
    }


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def coerce_manifest_paths(entries: Iterable[dict[str, Any]], field: str) -> list[Path]:
    paths: list[Path] = []
    for entry in entries:
        raw = str(entry.get(field) or "").strip()
        if not raw:
            continue
        paths.append(Path(raw).expanduser().resolve())
    return paths
