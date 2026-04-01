#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.1"
SKILL_NAME = "babel-copy-qa"
QA_REPORT_NAME = "qa-report.json"
COMPARISON_REPORT_NAME = "comparison-report.json"
RUN_MANIFEST_NAME = "run-manifest.json"

VALID_RESULTS = {"pass", "fail", "not_applicable"}
VALID_PAGE_STATUS = {"pass", "fail"}
VALID_REVIEW_STATUS = {"confirmed", "needs_review"}
VALID_SEVERITIES = {"blocking", "major", "minor"}
VALID_HOTSPOT_STATUS = {"checked", "not_present"}
VALID_CHALLENGER_STATUS = {"not_run", "clear", "flagged"}

CHECK_DEFS: list[dict[str, Any]] = [
    {
        "id": "layout_structure",
        "label": "Layout structure and section hierarchy match the source page",
        "weight": 10,
        "blocking": False,
    },
    {
        "id": "heading_placement",
        "label": "Heading/title placement and emphasis are preserved",
        "weight": 5,
        "blocking": False,
    },
    {
        "id": "text_readability",
        "label": "Translated text is fully readable at normal zoom",
        "weight": 15,
        "blocking": True,
    },
    {
        "id": "text_overlap_absent",
        "label": "No text overlaps or text-on-text collisions are visible",
        "weight": 15,
        "blocking": True,
    },
    {
        "id": "icon_or_bullet_collision_absent",
        "label": "Bullets, icons, and adjacent text remain cleanly separated",
        "weight": 10,
        "blocking": True,
    },
    {
        "id": "table_or_form_cell_overflow_absent",
        "label": "Table and form text stays within cells or rows",
        "weight": 10,
        "blocking": True,
    },
    {
        "id": "duplicate_draw_or_ocr_junk_absent",
        "label": "No duplicate draws, OCR junk, or stray rendering debris is visible",
        "weight": 10,
        "blocking": True,
    },
    {
        "id": "lists_tables_forms",
        "label": "Lists, tables, and form-like structures remain usable",
        "weight": 10,
        "blocking": False,
    },
    {
        "id": "headers_footers_branding",
        "label": "Headers, footers, logos, and page rhythm are preserved",
        "weight": 5,
        "blocking": False,
    },
    {
        "id": "non_text_artifacts",
        "label": "Signatures, stamps, arrows, icons, and other non-text artifacts survive appropriately",
        "weight": 5,
        "blocking": False,
    },
    {
        "id": "translation_quality",
        "label": "The target-language wording on this page is natural, correct, and terminology-consistent",
        "weight": 5,
        "blocking": False,
    },
]
CHECK_IDS = [check["id"] for check in CHECK_DEFS]
CHECK_INDEX = {check["id"]: check for check in CHECK_DEFS}
STRUCTURED_REGION_TRIGGER_CHECKS = {
    "icon_or_bullet_collision_absent",
    "table_or_form_cell_overflow_absent",
    "lists_tables_forms",
    "non_text_artifacts",
}

HOTSPOT_DEFS: list[dict[str, str]] = [
    {
        "id": "top_band",
        "label": "Top band",
        "anchor_hint": "header, logo, title, or top-page branding area",
    },
    {
        "id": "middle_band",
        "label": "Middle band",
        "anchor_hint": "mid-page body text region",
    },
    {
        "id": "bottom_band",
        "label": "Bottom band",
        "anchor_hint": "footer or bottom-page content area",
    },
    {
        "id": "densest_region",
        "label": "Densest region",
        "anchor_hint": "the most crowded translated text block on the page",
    },
    {
        "id": "structured_region",
        "label": "Structured region",
        "anchor_hint": "lists, bullets, tables, forms, signatures, icons, or artifact-heavy block",
    },
]
HOTSPOT_IDS = [hotspot["id"] for hotspot in HOTSPOT_DEFS]
HOTSPOT_INDEX = {hotspot["id"]: hotspot for hotspot in HOTSPOT_DEFS}

GENERIC_EVIDENCE_STRINGS = {
    "no overlap, clipping, duplicate draws, or spillover are visible.",
    "translated text remains readable at normal zoom on the rendered page.",
    "layout matches the source page.",
    "section hierarchy, headings, lists, and footer rhythm align with the source page.",
    "title and section headings are placed consistently with the source page.",
    "list and form-like structures remain usable and visually consistent.",
    "header/footer branding and page rhythm are preserved.",
    "signatures, stamps, and other non-text artifacts remain appropriately placed.",
    "target-language wording is natural and terminology-consistent for this page.",
}
ANCHOR_TOKENS = {
    "top",
    "bottom",
    "middle",
    "left",
    "right",
    "center",
    "header",
    "footer",
    "logo",
    "title",
    "heading",
    "paragraph",
    "line",
    "column",
    "margin",
    "bullet",
    "icon",
    "table",
    "cell",
    "row",
    "form",
    "signature",
    "stamp",
    "diagram",
    "list",
    "block",
    "section",
    "gutter",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare and finalize babel-copy QA reports.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Create qa-report.json scaffolds next to comparison reports.")
    prepare.add_argument("inputs", nargs="+", help="comparison-report.json files or directories that contain them")
    prepare.add_argument("--force", action="store_true", help="Overwrite existing qa-report.json files")

    finalize = subparsers.add_parser("finalize", help="Validate and score qa-report.json files.")
    finalize.add_argument("inputs", nargs="+", help="comparison-report.json files or directories that contain them")

    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def quality_band(score: int) -> str:
    if score >= 90:
        return "excellent"
    if score >= 80:
        return "good"
    if score >= 70:
        return "acceptable"
    return "poor"


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def normalize_text(raw: Any) -> str:
    return re.sub(r"\s+", " ", str(raw or "").strip())


def normalize_key(raw: Any) -> str:
    return normalize_text(raw).lower()


def has_anchor_signal(text: str) -> bool:
    lowered = normalize_key(text)
    if any(token in lowered for token in ANCHOR_TOKENS):
        return True
    if '"' in text or "'" in text:
        return True
    return bool(re.search(r"\b\d+\b", text))


def is_specific_observation(text: Any) -> bool:
    normalized = normalize_text(text)
    lowered = normalized.lower()
    if not normalized:
        return False
    if lowered in GENERIC_EVIDENCE_STRINGS:
        return False
    if len(normalized.split()) < 7:
        return False
    if not has_anchor_signal(normalized):
        return False
    return True


def resolve_comparison_reports(inputs: list[str]) -> list[Path]:
    reports: list[Path] = []
    for raw in inputs:
        path = Path(raw).expanduser().resolve()
        if path.is_dir():
            reports.extend(sorted(candidate.resolve() for candidate in path.rglob(COMPARISON_REPORT_NAME)))
            continue
        if path.is_file() and path.name == COMPARISON_REPORT_NAME:
            reports.append(path)
            continue
        raise SystemExit(f"Expected a directory or {COMPARISON_REPORT_NAME}: {path}")
    unique = sorted(dict.fromkeys(reports))
    if not unique:
        raise SystemExit("No comparison-report.json files found.")
    return unique


def resolve_side_by_side_image(report_path: Path, image_path: str) -> str:
    candidate = Path(image_path).expanduser()
    if candidate.is_absolute():
        return str(candidate.resolve())
    return str((report_path.parent / candidate).resolve())


def build_document_checks(comparison: dict[str, Any], report_path: Path) -> dict[str, Any]:
    pages = comparison.get("pages", [])
    missing_images: list[str] = []
    for page in pages:
        image_path = resolve_side_by_side_image(report_path, str(page.get("side_by_side_image", "")))
        if not Path(image_path).exists():
            missing_images.append(image_path)
    assets_pass = not missing_images
    source_pages = comparison.get("source_pages")
    translated_pages = comparison.get("translated_pages")
    page_count_match = source_pages == translated_pages and not comparison.get("page_count_mismatch", False)
    return {
        "page_count_match": {
            "label": "Source and translated PDFs have the same page count",
            "result": "pass" if page_count_match else "fail",
            "evidence": f"source_pages={source_pages} translated_pages={translated_pages}",
            "remediation": "" if page_count_match else "Rebuild the translated PDF so the page count matches the source.",
        },
        "comparison_assets_present": {
            "label": "Every side-by-side comparison image exists",
            "result": "pass" if assets_pass else "fail",
            "evidence": (
                f"All {len(pages)} comparison images resolved on disk."
                if assets_pass
                else f"Missing comparison images: {', '.join(missing_images)}"
            ),
            "remediation": "" if assets_pass else "Regenerate the comparison renders before QA.",
        },
    }


def load_run_manifest_metadata(report_path: Path) -> dict[str, Any]:
    manifest_path = report_path.parent.parent / RUN_MANIFEST_NAME
    if not manifest_path.exists():
        return {
            "run_manifest_path": None,
            "run_output_dir": None,
            "document_id": None,
            "cycle_id": None,
            "run_label": None,
            "run_id": None,
            "input_pdf": None,
        }
    payload = load_json(manifest_path)
    return {
        "run_manifest_path": str(manifest_path.resolve()),
        "run_output_dir": payload.get("output_dir"),
        "document_id": payload.get("document_id"),
        "cycle_id": payload.get("cycle_id"),
        "run_label": payload.get("run_label"),
        "run_id": payload.get("run_id"),
        "input_pdf": payload.get("input_pdf"),
    }


def empty_check_payload() -> dict[str, Any]:
    return {
        check["id"]: {
            "label": check["label"],
            "weight": check["weight"],
            "blocking": check["blocking"],
            "result": None,
            "evidence": "",
            "remediation": "",
        }
        for check in CHECK_DEFS
    }


def empty_hotspot_payload() -> dict[str, Any]:
    return {
        hotspot["id"]: {
            "label": hotspot["label"],
            "anchor_hint": hotspot["anchor_hint"],
            "status": None,
            "notes": "",
        }
        for hotspot in HOTSPOT_DEFS
    }


def build_scaffold(report_path: Path) -> dict[str, Any]:
    comparison = load_json(report_path)
    baton = load_run_manifest_metadata(report_path)
    pages = []
    for page in sorted(comparison.get("pages", []), key=lambda item: int(item.get("page", 0))):
        pages.append(
            {
                "page_number": int(page["page"]),
                "side_by_side_image": resolve_side_by_side_image(report_path, str(page["side_by_side_image"])),
                "mean_diff": page.get("mean_diff"),
                "status": None,
                "review_status": None,
                "score": None,
                "quality_band": None,
                "failed_checks": [],
                "blocking_failed_checks": [],
                "issue_counts": {"blocking": 0, "major": 0, "minor": 0},
                "hotspot_reviews": empty_hotspot_payload(),
                "checks": empty_check_payload(),
                "challenger": {
                    "status": "not_run",
                    "summary": "",
                    "findings": [],
                },
                "issues": [],
                "defect_hunt_summary": "",
                "summary": "",
                "remediation_summary": "",
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "skill": SKILL_NAME,
        "comparison_report_path": str(report_path),
        "source_pdf": comparison.get("source_pdf"),
        "translated_pdf": comparison.get("translated_pdf"),
        **baton,
        "document_checks": build_document_checks(comparison, report_path),
        "overall": {
            "status": None,
            "review_status": None,
            "overall_score": None,
            "quality_band": None,
            "pages_reviewed": len(pages),
            "pages_passed": 0,
            "pages_failed": 0,
            "needs_review_count": 0,
            "blocking_issue_count": 0,
            "major_issue_count": 0,
            "minor_issue_count": 0,
            "review_gate_reasons": [],
            "release_recommendation": None,
            "summary": "",
        },
        "pages": pages,
        "generated_at": None,
    }


def ensure_required_check_shape(page: dict[str, Any], errors: list[str]) -> None:
    checks = page.get("checks")
    if not isinstance(checks, dict):
        errors.append(f"Page {page.get('page_number')}: checks must be an object.")
        return
    actual_ids = set(checks.keys())
    expected_ids = set(CHECK_IDS)
    if actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        if missing:
            errors.append(f"Page {page.get('page_number')}: missing checks {missing}.")
        if extra:
            errors.append(f"Page {page.get('page_number')}: unexpected checks {extra}.")
    evidence_counter: Counter[str] = Counter()
    for check_id in CHECK_IDS:
        payload = checks.get(check_id)
        if not isinstance(payload, dict):
            errors.append(f"Page {page.get('page_number')}: check {check_id} must be an object.")
            continue
        definition = CHECK_INDEX[check_id]
        if payload.get("label") != definition["label"]:
            errors.append(f"Page {page.get('page_number')}: check {check_id} label mismatch.")
        if payload.get("weight") != definition["weight"]:
            errors.append(f"Page {page.get('page_number')}: check {check_id} weight mismatch.")
        if payload.get("blocking") != definition["blocking"]:
            errors.append(f"Page {page.get('page_number')}: check {check_id} blocking flag mismatch.")
        result = payload.get("result")
        if result not in VALID_RESULTS:
            errors.append(f"Page {page.get('page_number')}: check {check_id} result must be one of {sorted(VALID_RESULTS)}.")
            continue
        evidence = normalize_text(payload.get("evidence", ""))
        remediation = normalize_text(payload.get("remediation", ""))
        if result in {"pass", "fail"}:
            if not evidence:
                errors.append(f"Page {page.get('page_number')}: check {check_id} needs evidence.")
            elif not is_specific_observation(evidence):
                errors.append(f"Page {page.get('page_number')}: check {check_id} evidence is too generic.")
            else:
                evidence_counter[normalize_key(evidence)] += 1
        if result == "fail" and not remediation:
            errors.append(f"Page {page.get('page_number')}: check {check_id} needs remediation.")
    duplicates = [text for text, count in evidence_counter.items() if count >= 3]
    distinct_count = len(evidence_counter)
    if duplicates:
        errors.append(f"Page {page.get('page_number')}: one check evidence string was reused across too many checks.")
    if evidence_counter and distinct_count < 4:
        errors.append(f"Page {page.get('page_number')}: check evidence must contain at least four distinct observations.")


def ensure_hotspot_shape(page: dict[str, Any], errors: list[str]) -> None:
    hotspots = page.get("hotspot_reviews")
    if not isinstance(hotspots, dict):
        errors.append(f"Page {page.get('page_number')}: hotspot_reviews must be an object.")
        return
    actual_ids = set(hotspots.keys())
    expected_ids = set(HOTSPOT_IDS)
    if actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        if missing:
            errors.append(f"Page {page.get('page_number')}: missing hotspot reviews {missing}.")
        if extra:
            errors.append(f"Page {page.get('page_number')}: unexpected hotspot reviews {extra}.")
    for hotspot_id in HOTSPOT_IDS:
        payload = hotspots.get(hotspot_id)
        if not isinstance(payload, dict):
            errors.append(f"Page {page.get('page_number')}: hotspot {hotspot_id} must be an object.")
            continue
        definition = HOTSPOT_INDEX[hotspot_id]
        if payload.get("label") != definition["label"]:
            errors.append(f"Page {page.get('page_number')}: hotspot {hotspot_id} label mismatch.")
        if payload.get("anchor_hint") != definition["anchor_hint"]:
            errors.append(f"Page {page.get('page_number')}: hotspot {hotspot_id} anchor_hint mismatch.")
        status = payload.get("status")
        if status not in VALID_HOTSPOT_STATUS:
            errors.append(
                f"Page {page.get('page_number')}: hotspot {hotspot_id} status must be one of {sorted(VALID_HOTSPOT_STATUS)}."
            )
            continue
        notes = normalize_text(payload.get("notes", ""))
        if status == "checked":
            if not notes:
                errors.append(f"Page {page.get('page_number')}: hotspot {hotspot_id} needs notes.")
            elif not is_specific_observation(notes):
                errors.append(f"Page {page.get('page_number')}: hotspot {hotspot_id} notes are too generic.")


def structured_region_required(page: dict[str, Any]) -> bool:
    for check_id in STRUCTURED_REGION_TRIGGER_CHECKS:
        result = page["checks"][check_id]["result"]
        if result != "not_applicable":
            return True
    return False


def hotspot_coverage_complete(page: dict[str, Any], errors: list[str]) -> bool:
    hotspots = page["hotspot_reviews"]
    required = ["top_band", "middle_band", "bottom_band", "densest_region"]
    complete = True
    for hotspot_id in required:
        if hotspots[hotspot_id]["status"] != "checked":
            errors.append(f"Page {page.get('page_number')}: hotspot {hotspot_id} must be checked.")
            complete = False
    structured_status = hotspots["structured_region"]["status"]
    if structured_region_required(page):
        if structured_status != "checked":
            errors.append(f"Page {page.get('page_number')}: structured_region must be checked.")
            complete = False
    else:
        if structured_status not in {"checked", "not_present"}:
            errors.append(f"Page {page.get('page_number')}: structured_region must be checked or not_present.")
            complete = False
    return complete


def issue_counts(issues: list[dict[str, Any]], page_number: int, errors: list[str]) -> dict[str, int]:
    counts = {"blocking": 0, "major": 0, "minor": 0}
    for index, issue in enumerate(issues, start=1):
        if not isinstance(issue, dict):
            errors.append(f"Page {page_number}: issue {index} must be an object.")
            continue
        severity = issue.get("severity")
        if severity not in VALID_SEVERITIES:
            errors.append(f"Page {page_number}: issue {index} severity must be one of {sorted(VALID_SEVERITIES)}.")
            continue
        counts[severity] += 1
        for key in ("category", "title", "evidence", "remediation"):
            value = normalize_text(issue.get(key, ""))
            if not value:
                errors.append(f"Page {page_number}: issue {index} missing {key}.")
            elif key == "evidence" and not is_specific_observation(value):
                errors.append(f"Page {page_number}: issue {index} evidence is too generic.")
        check_ids = issue.get("check_ids")
        if not isinstance(check_ids, list) or not check_ids:
            errors.append(f"Page {page_number}: issue {index} needs non-empty check_ids.")
        else:
            invalid = [check_id for check_id in check_ids if check_id not in CHECK_IDS]
            if invalid:
                errors.append(f"Page {page_number}: issue {index} has invalid check_ids {invalid}.")
    return counts


def validate_challenger(page: dict[str, Any], score_candidate_pass: bool, errors: list[str]) -> tuple[str, bool, list[str]]:
    challenger = page.get("challenger")
    if not isinstance(challenger, dict):
        errors.append(f"Page {page.get('page_number')}: challenger must be an object.")
        return "not_run", False, []
    status = challenger.get("status")
    if status not in VALID_CHALLENGER_STATUS:
        errors.append(
            f"Page {page.get('page_number')}: challenger.status must be one of {sorted(VALID_CHALLENGER_STATUS)}."
        )
        return "not_run", False, []
    summary = normalize_text(challenger.get("summary", ""))
    findings = challenger.get("findings")
    if not isinstance(findings, list):
        errors.append(f"Page {page.get('page_number')}: challenger.findings must be an array.")
        findings = []
    normalized_findings: list[str] = []
    for index, finding in enumerate(findings, start=1):
        text = normalize_text(finding)
        if not text:
            errors.append(f"Page {page.get('page_number')}: challenger finding {index} is empty.")
            continue
        if not is_specific_observation(text):
            errors.append(f"Page {page.get('page_number')}: challenger finding {index} is too generic.")
        normalized_findings.append(text)
    if status == "clear":
        if not summary:
            errors.append(f"Page {page.get('page_number')}: challenger clear requires summary.")
        elif not is_specific_observation(summary):
            errors.append(f"Page {page.get('page_number')}: challenger clear summary is too generic.")
    elif status == "flagged":
        if not summary:
            errors.append(f"Page {page.get('page_number')}: challenger flagged requires summary.")
        elif not is_specific_observation(summary):
            errors.append(f"Page {page.get('page_number')}: challenger flagged summary is too generic.")
        if not normalized_findings:
            errors.append(f"Page {page.get('page_number')}: challenger flagged requires findings.")
    elif status == "not_run" and score_candidate_pass:
        errors.append(f"Page {page.get('page_number')}: challenger review is required on passing pages.")
    return status, status == "flagged", normalized_findings


def score_page(page: dict[str, Any], errors: list[str]) -> tuple[int, str, str, list[str], list[str], list[str]]:
    checks = page["checks"]
    applicable_weight = 0
    passed_weight = 0
    failed_checks: list[str] = []
    blocking_failed_checks: list[str] = []
    for check_id in CHECK_IDS:
        payload = checks[check_id]
        result = payload["result"]
        if result == "not_applicable":
            continue
        applicable_weight += payload["weight"]
        if result == "pass":
            passed_weight += payload["weight"]
        elif result == "fail":
            failed_checks.append(check_id)
            if payload["blocking"]:
                blocking_failed_checks.append(check_id)
    if applicable_weight <= 0:
        errors.append(f"Page {page.get('page_number')}: all checks are not_applicable.")
        return 0, "fail", "needs_review", failed_checks, blocking_failed_checks, ["No applicable checks were scored."]

    score = round(100 * passed_weight / applicable_weight)
    coverage_ok = hotspot_coverage_complete(page, errors)
    score_candidate_pass = score >= 90 and not failed_checks and not blocking_failed_checks and coverage_ok
    challenger_status, challenger_flagged, challenger_findings = validate_challenger(page, score_candidate_pass, errors)

    issues = page.get("issues", [])
    if not isinstance(issues, list):
        errors.append(f"Page {page.get('page_number')}: issues must be an array.")
        issues = []

    gate_reasons: list[str] = []
    if blocking_failed_checks:
        gate_reasons.append(f"Blocking checks failed: {', '.join(blocking_failed_checks)}.")
    if score < 90:
        gate_reasons.append(f"Page score {score} is below the pass threshold of 90.")
    if not coverage_ok:
        gate_reasons.append("Mandatory hotspot coverage is incomplete.")
    if challenger_flagged:
        gate_reasons.extend(challenger_findings or ["Challenger review flagged a blocker or ambiguity."])

    review_status = "needs_review" if challenger_flagged else "confirmed"
    status = "pass" if score_candidate_pass and challenger_status == "clear" and review_status == "confirmed" else "fail"

    if status == "fail":
        if review_status == "needs_review" and not failed_checks and not issues:
            pass
        else:
            if not normalize_text(page.get("remediation_summary", "")):
                errors.append(f"Page {page.get('page_number')}: failed page needs remediation_summary.")
            if not issues:
                errors.append(f"Page {page.get('page_number')}: failed page needs at least one issue entry.")

    if not normalize_text(page.get("defect_hunt_summary", "")):
        errors.append(f"Page {page.get('page_number')}: defect_hunt_summary is required.")
    elif not is_specific_observation(page.get("defect_hunt_summary", "")):
        errors.append(f"Page {page.get('page_number')}: defect_hunt_summary is too generic.")

    if not normalize_text(page.get("summary", "")):
        errors.append(f"Page {page.get('page_number')}: summary is required.")

    return score, status, review_status, failed_checks, blocking_failed_checks, gate_reasons


def finalize_report(report_path: Path) -> Path:
    qa_path = report_path.parent / QA_REPORT_NAME
    if not qa_path.exists():
        raise SystemExit(f"Missing qa-report.json for {report_path}. Run prepare first.")

    qa = load_json(qa_path)
    errors: list[str] = []

    if qa.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{qa_path}: schema_version must be {SCHEMA_VERSION}.")
    if qa.get("skill") != SKILL_NAME:
        errors.append(f"{qa_path}: skill must be {SKILL_NAME}.")
    if str(qa.get("comparison_report_path")) != str(report_path):
        errors.append(f"{qa_path}: comparison_report_path must equal {report_path}.")

    comparison = load_json(report_path)
    expected_baton = load_run_manifest_metadata(report_path)
    for key, value in expected_baton.items():
        if qa.get(key) != value:
            qa[key] = value

    expected_doc_checks = build_document_checks(comparison, report_path)
    if qa.get("document_checks") != expected_doc_checks:
        qa["document_checks"] = expected_doc_checks

    pages = qa.get("pages")
    if not isinstance(pages, list) or not pages:
        errors.append(f"{qa_path}: pages must be a non-empty array.")
        pages = []

    total_scores = 0
    pages_passed = 0
    pages_failed = 0
    needs_review_count = 0
    total_issue_counts = {"blocking": 0, "major": 0, "minor": 0}
    gate_reasons: list[str] = []

    comparison_pages = {int(page["page"]): page for page in comparison.get("pages", [])}

    for page in pages:
        page_number = int(page.get("page_number", 0))
        if page_number not in comparison_pages:
            errors.append(f"{qa_path}: page {page_number} not found in comparison report.")
            continue
        comparison_page = comparison_pages[page_number]
        expected_image = resolve_side_by_side_image(report_path, str(comparison_page["side_by_side_image"]))
        if str(page.get("side_by_side_image")) != expected_image:
            errors.append(f"Page {page_number}: side_by_side_image mismatch.")
        if page.get("mean_diff") != comparison_page.get("mean_diff"):
            errors.append(f"Page {page_number}: mean_diff mismatch.")

        ensure_required_check_shape(page, errors)
        ensure_hotspot_shape(page, errors)
        if not isinstance(page.get("issues"), list):
            errors.append(f"Page {page_number}: issues must be an array.")
            page["issues"] = []
        counts = issue_counts(page["issues"], page_number, errors)
        page["issue_counts"] = counts
        score, status, review_status, failed_checks, blocking_failed_checks, page_gate_reasons = score_page(page, errors)
        page["score"] = score
        page["status"] = status
        page["review_status"] = review_status
        page["quality_band"] = quality_band(score)
        page["failed_checks"] = failed_checks
        page["blocking_failed_checks"] = blocking_failed_checks

        total_scores += score
        if status == "pass":
            pages_passed += 1
        else:
            pages_failed += 1
        if review_status == "needs_review":
            needs_review_count += 1
            gate_reasons.extend([f"Page {page_number}: {reason}" for reason in page_gate_reasons if reason])
        for severity, count in counts.items():
            total_issue_counts[severity] += count

    if len(pages) != len(comparison_pages):
        errors.append(f"{qa_path}: page count mismatch between qa report and comparison report.")

    overall_score = round(total_scores / len(pages)) if pages else 0
    doc_checks = qa["document_checks"]
    document_checks_pass = all(check["result"] == "pass" for check in doc_checks.values())
    overall_review_status = "needs_review" if needs_review_count else "confirmed"
    overall_status = (
        "pass"
        if pages and pages_failed == 0 and needs_review_count == 0 and document_checks_pass and overall_score >= 90
        else "fail"
    )
    overall = qa.get("overall")
    if not isinstance(overall, dict):
        errors.append(f"{qa_path}: overall must be an object.")
        overall = {}
        qa["overall"] = overall
    overall["status"] = overall_status
    overall["review_status"] = overall_review_status
    overall["overall_score"] = overall_score
    overall["quality_band"] = quality_band(overall_score)
    overall["pages_reviewed"] = len(pages)
    overall["pages_passed"] = pages_passed
    overall["pages_failed"] = pages_failed
    overall["needs_review_count"] = needs_review_count
    overall["blocking_issue_count"] = total_issue_counts["blocking"]
    overall["major_issue_count"] = total_issue_counts["major"]
    overall["minor_issue_count"] = total_issue_counts["minor"]
    overall["review_gate_reasons"] = gate_reasons
    overall["release_recommendation"] = (
        "ready" if overall_status == "pass" else "manual_review_required" if needs_review_count else "fix_required"
    )
    if not normalize_text(overall.get("summary", "")):
        errors.append(f"{qa_path}: overall.summary is required.")

    qa["generated_at"] = utc_now()

    if errors:
        raise SystemExit("\n".join(errors))

    write_json(qa_path, qa)
    return qa_path


def prepare_reports(report_paths: list[Path], force: bool) -> None:
    for report_path in report_paths:
        qa_path = report_path.parent / QA_REPORT_NAME
        if qa_path.exists() and not force:
            print(f"exists {qa_path}")
            continue
        scaffold = build_scaffold(report_path)
        write_json(qa_path, scaffold)
        print(f"wrote {qa_path}")


def finalize_reports(report_paths: list[Path]) -> None:
    for report_path in report_paths:
        qa_path = finalize_report(report_path)
        print(f"validated {qa_path}")


def main() -> int:
    args = parse_args()
    report_paths = resolve_comparison_reports(args.inputs)
    if args.command == "prepare":
        prepare_reports(report_paths, args.force)
        return 0
    if args.command == "finalize":
        finalize_reports(report_paths)
        return 0
    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
