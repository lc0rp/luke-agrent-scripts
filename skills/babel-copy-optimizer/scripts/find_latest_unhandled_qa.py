#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QA_REPORT_NAME = "qa-report.json"
COMPARISON_REPORT_NAME = "comparison-report.json"
OPTIMIZER_MD_NAME = "optimizer-report.md"
OPTIMIZER_JSON_NAME = "optimizer-report.json"


@dataclass(order=True)
class Candidate:
    sort_key: tuple[float, str]
    qa_report: Path
    comparison_report: Path
    compare_dir: Path
    status: str
    generated_at: str | None
    run_manifest_path: str | None
    run_output_dir: str | None
    document_id: str | None
    cycle_id: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find the latest unhandled failed babel-copy QA report.")
    parser.add_argument(
        "inputs",
        nargs="*",
        default=["."],
        help="Directories to scan recursively, or specific qa-report.json files.",
    )
    parser.add_argument(
        "--format",
        choices=("path", "json"),
        default="path",
        help="Output just the qa-report path or a JSON payload.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def parse_generated_at(raw: Any, fallback_path: Path) -> tuple[float, str | None]:
    if isinstance(raw, str) and raw.strip():
        value = raw.strip()
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
        else:
            return dt.astimezone(timezone.utc).timestamp(), value
    return fallback_path.stat().st_mtime, None


def resolve_inputs(raw_inputs: list[str]) -> list[Path]:
    reports: list[Path] = []
    for raw in raw_inputs:
        path = Path(raw).expanduser().resolve()
        if path.is_dir():
            reports.extend(sorted(path.rglob(QA_REPORT_NAME)))
            continue
        if path.is_file() and path.name == QA_REPORT_NAME:
            reports.append(path)
            continue
        raise SystemExit(f"Expected a directory or {QA_REPORT_NAME}: {path}")
    unique = sorted(dict.fromkeys(report.resolve() for report in reports))
    if not unique:
        raise SystemExit("No qa-report.json files found.")
    return unique


def is_handled(compare_dir: Path) -> bool:
    return (compare_dir / OPTIMIZER_MD_NAME).exists() or (compare_dir / OPTIMIZER_JSON_NAME).exists()


def build_candidate(qa_path: Path) -> Candidate | None:
    payload = load_json(qa_path)
    overall = payload.get("overall", {}) if isinstance(payload.get("overall"), dict) else {}
    status = str(overall.get("status") or "").strip().lower()
    if status != "fail":
        return None
    compare_dir = qa_path.parent
    if is_handled(compare_dir):
        return None
    comparison_report = compare_dir / COMPARISON_REPORT_NAME
    if not comparison_report.exists():
        raise SystemExit(f"Missing comparison-report.json next to {qa_path}")
    timestamp_value, generated_at = parse_generated_at(payload.get("generated_at"), qa_path)
    return Candidate(
        sort_key=(timestamp_value, str(qa_path)),
        qa_report=qa_path,
        comparison_report=comparison_report.resolve(),
        compare_dir=compare_dir.resolve(),
        status=status,
        generated_at=generated_at,
        run_manifest_path=payload.get("run_manifest_path"),
        run_output_dir=payload.get("run_output_dir"),
        document_id=payload.get("document_id"),
        cycle_id=payload.get("cycle_id"),
    )


def main() -> int:
    args = parse_args()
    report_paths = resolve_inputs(args.inputs)
    candidates = [candidate for path in report_paths if (candidate := build_candidate(path)) is not None]
    if not candidates:
        raise SystemExit("No unhandled failed qa-report.json files found.")
    latest = max(candidates)
    if args.format == "json":
        print(
            json.dumps(
                {
                    "qa_report": str(latest.qa_report),
                    "comparison_report": str(latest.comparison_report),
                    "compare_dir": str(latest.compare_dir),
                    "status": latest.status,
                    "generated_at": latest.generated_at,
                    "run_manifest_path": latest.run_manifest_path,
                    "run_output_dir": latest.run_output_dir,
                    "document_id": latest.document_id,
                    "cycle_id": latest.cycle_id,
                },
                indent=2,
            )
        )
        return 0
    print(latest.qa_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
