#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
SKILL_NAME = "babel-copy-qa"
QA_REPORT_NAME = "qa-report.json"
COMPARISON_REPORT_NAME = "comparison-report.json"
VALID_RESULTS = {"pass", "fail", "not_applicable"}
VALID_PAGE_STATUS = {"pass", "fail"}
VALID_SEVERITIES = {"blocking", "major", "minor"}

CHECK_DEFS: list[dict[str, Any]] = [
    {
        "id": "layout_structure",
        "label": "Layout structure and section hierarchy match the source page",
        "weight": 15,
        "blocking": False,
    },
    {
        "id": "heading_placement",
        "label": "Heading/title placement and emphasis are preserved",
        "weight": 10,
        "blocking": False,
    },
    {
        "id": "text_readability",
        "label": "Translated text is fully readable at normal zoom",
        "weight": 20,
        "blocking": True,
    },
    {
        "id": "overflow_or_collision_absent",
        "label": "No overlap, clipping, duplicate draws, or spillover are visible",
        "weight": 20,
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
        "weight": 10,
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
        "weight": 10,
        "blocking": False,
    },
]
CHECK_IDS = [check["id"] for check in CHECK_DEFS]
CHECK_INDEX = {check["id"]: check for check in CHECK_DEFS}


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


def infer_document_id(raw_path: Any) -> str | None:
    candidate = Path(str(raw_path or "")).name
    match = re.match(r"^(F\d+)\b", candidate)
    if match:
        return match.group(1)
    return None


def resolve_run_manifest(report_path: Path) -> Path | None:
    candidate = (report_path.parent.parent / "run-manifest.json").resolve()
    if candidate.exists():
        return candidate
    return None


def build_run_metadata(report_path: Path, comparison: dict[str, Any]) -> dict[str, Any]:
    manifest_path = resolve_run_manifest(report_path)
    manifest: dict[str, Any] = load_json(manifest_path) if manifest_path else {}
    run_output_dir = manifest.get("output_dir") or str(report_path.parent.parent.resolve())
    input_pdf = manifest.get("input_pdf") or comparison.get("source_pdf")
    return {
        "run_manifest_path": str(manifest_path) if manifest_path else None,
        "run_output_dir": run_output_dir,
        "document_id": manifest.get("document_id") or infer_document_id(input_pdf),
        "cycle_id": manifest.get("cycle_id"),
        "run_label": manifest.get("run_label"),
        "input_pdf": input_pdf,
    }


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


def build_scaffold(report_path: Path) -> dict[str, Any]:
    comparison = load_json(report_path)
    run_metadata = build_run_metadata(report_path, comparison)
    pages = []
    for page in sorted(comparison.get("pages", []), key=lambda item: int(item.get("page", 0))):
        pages.append(
            {
                "page_number": int(page["page"]),
                "side_by_side_image": resolve_side_by_side_image(report_path, str(page["side_by_side_image"])),
                "mean_diff": page.get("mean_diff"),
                "status": None,
                "score": None,
                "quality_band": None,
                "failed_checks": [],
                "blocking_failed_checks": [],
                "issue_counts": {"blocking": 0, "major": 0, "minor": 0},
                "checks": empty_check_payload(),
                "issues": [],
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
        **run_metadata,
        "document_checks": build_document_checks(comparison, report_path),
        "overall": {
            "status": None,
            "overall_score": None,
            "quality_band": None,
            "pages_reviewed": len(pages),
            "pages_passed": 0,
            "pages_failed": 0,
            "blocking_issue_count": 0,
            "major_issue_count": 0,
            "minor_issue_count": 0,
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
        evidence = str(payload.get("evidence", "")).strip()
        remediation = str(payload.get("remediation", "")).strip()
        if result in {"pass", "fail"} and not evidence:
            errors.append(f"Page {page.get('page_number')}: check {check_id} needs evidence.")
        if result == "fail" and not remediation:
            errors.append(f"Page {page.get('page_number')}: check {check_id} needs remediation.")


def score_page(page: dict[str, Any], errors: list[str]) -> tuple[int, str, list[str], list[str]]:
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
        return 0, "fail", failed_checks, blocking_failed_checks
    score = round(100 * passed_weight / applicable_weight)
    status = "pass" if score >= 85 and not blocking_failed_checks else "fail"
    issues = page.get("issues", [])
    if not isinstance(issues, list):
        errors.append(f"Page {page.get('page_number')}: issues must be an array.")
        issues = []
    if status == "fail":
        if not str(page.get("remediation_summary", "")).strip():
            errors.append(f"Page {page.get('page_number')}: failed page needs remediation_summary.")
        if not issues:
            errors.append(f"Page {page.get('page_number')}: failed page needs at least one issue entry.")
    if not str(page.get("summary", "")).strip():
        errors.append(f"Page {page.get('page_number')}: summary is required.")
    return score, status, failed_checks, blocking_failed_checks


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
            if not str(issue.get(key, "")).strip():
                errors.append(f"Page {page_number}: issue {index} missing {key}.")
        check_ids = issue.get("check_ids")
        if not isinstance(check_ids, list) or not check_ids:
            errors.append(f"Page {page_number}: issue {index} needs non-empty check_ids.")
        else:
            invalid = [check_id for check_id in check_ids if check_id not in CHECK_IDS]
            if invalid:
                errors.append(f"Page {page_number}: issue {index} has invalid check_ids {invalid}.")
    return counts


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
    expected_run_metadata = build_run_metadata(report_path, comparison)
    for key, value in expected_run_metadata.items():
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
    total_issue_counts = {"blocking": 0, "major": 0, "minor": 0}

    comparison_pages = {
        int(page["page"]): page
        for page in comparison.get("pages", [])
    }

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
        if not isinstance(page.get("issues"), list):
            errors.append(f"Page {page_number}: issues must be an array.")
            page["issues"] = []
        counts = issue_counts(page["issues"], page_number, errors)
        page["issue_counts"] = counts
        score, status, failed_checks, blocking_failed_checks = score_page(page, errors)
        page["score"] = score
        page["status"] = status
        page["quality_band"] = quality_band(score)
        page["failed_checks"] = failed_checks
        page["blocking_failed_checks"] = blocking_failed_checks

        total_scores += score
        if status == "pass":
            pages_passed += 1
        else:
            pages_failed += 1
        for severity, count in counts.items():
            total_issue_counts[severity] += count

    if len(pages) != len(comparison_pages):
        errors.append(f"{qa_path}: page count mismatch between qa report and comparison report.")

    overall_score = round(total_scores / len(pages)) if pages else 0
    doc_checks = qa["document_checks"]
    document_checks_pass = all(check["result"] == "pass" for check in doc_checks.values())
    overall_status = "pass" if pages and pages_failed == 0 and document_checks_pass and overall_score >= 85 else "fail"
    overall = qa.get("overall")
    if not isinstance(overall, dict):
        errors.append(f"{qa_path}: overall must be an object.")
        overall = {}
        qa["overall"] = overall
    overall["status"] = overall_status
    overall["overall_score"] = overall_score
    overall["quality_band"] = quality_band(overall_score)
    overall["pages_reviewed"] = len(pages)
    overall["pages_passed"] = pages_passed
    overall["pages_failed"] = pages_failed
    overall["blocking_issue_count"] = total_issue_counts["blocking"]
    overall["major_issue_count"] = total_issue_counts["major"]
    overall["minor_issue_count"] = total_issue_counts["minor"]
    overall["release_recommendation"] = "ready" if overall_status == "pass" else "fix_required"
    if not str(overall.get("summary", "")).strip():
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
