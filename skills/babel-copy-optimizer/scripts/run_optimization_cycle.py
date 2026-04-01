#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
REQUIRED_CONSECUTIVE_PASSES = 2
DEFAULT_STALE_LOCK_HOURS = 1.5
LOCK_FILENAME = "loop.lock"
CURRENT_CYCLE_FILENAME = "current-cycle.json"
STATE_FILENAME = "state.json"
STATUS_FILENAME = "loop-status.md"
ACTIVE_RUN_FILENAME = "active-run.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Coordinate one locked babel-copy optimization cycle.")
    parser.add_argument(
        "--workspace",
        default=str(Path(__file__).resolve().parents[1]),
        help="Translate workspace root. Defaults to the parent of this script directory.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Acquire the loop lock and create a new cycle.")
    start.add_argument("--stale-after-hours", type=float, default=DEFAULT_STALE_LOCK_HOURS)

    finish = subparsers.add_parser("finish", help="Finalize a cycle from the QA artifacts written during that cycle.")
    finish.add_argument("--cycle-id", help="Cycle id to finish. Defaults to the current locked cycle.")

    release = subparsers.add_parser("release", help="Release the lock without scoring a cycle.")
    release.add_argument("--cycle-id", help="Cycle id expected in the current lock file.")
    release.add_argument("--reason", default="manual_release")
    release.add_argument("--force", action="store_true", help="Override the active-worker guard.")

    status = subparsers.add_parser("status", help="Print the current loop state.")
    status.add_argument("--format", choices=("json", "path"), default="json")

    return parser.parse_args()


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def utc_now_text() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")
    temp_path.replace(path)


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        if default is not None:
            return default
        raise SystemExit(f"Missing file: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def doc_id_for_path(path: Path) -> str:
    match = re.match(r"^(F\d+)\b", path.name)
    return match.group(1) if match else path.stem


class LoopPaths:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.loop_root = workspace / "output" / "optimization-loop"
        self.cycles_root = self.loop_root / "cycles"
        self.lock_path = self.loop_root / LOCK_FILENAME
        self.current_cycle_path = self.loop_root / CURRENT_CYCLE_FILENAME
        self.state_path = self.loop_root / STATE_FILENAME
        self.status_path = self.loop_root / STATUS_FILENAME


def discover_documents(workspace: Path) -> list[dict[str, str]]:
    source_dir = workspace / "french-orig"
    if not source_dir.exists():
        raise SystemExit(f"Missing source directory: {source_dir}")
    pdfs = sorted(candidate.resolve() for candidate in source_dir.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDF inputs found in {source_dir}")
    documents = []
    for pdf_path in pdfs:
        documents.append({"document_id": doc_id_for_path(pdf_path), "input_pdf": str(pdf_path)})
    return documents


def default_state(workspace: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "workspace": str(workspace),
        "goal": {
            "required_consecutive_full_pass_cycles": REQUIRED_CONSECUTIVE_PASSES,
            "documents": discover_documents(workspace),
        },
        "completed": False,
        "completed_at": None,
        "consecutive_full_pass_cycles": 0,
        "last_finished_cycle_id": None,
        "cycles": [],
    }


def ensure_state(paths: LoopPaths) -> dict[str, Any]:
    state = load_json(paths.state_path, default=default_state(paths.workspace))
    if not paths.state_path.exists():
        write_json(paths.state_path, state)
    return state


def parse_timestamp(raw: Any, fallback_path: Path) -> tuple[float, str | None]:
    if isinstance(raw, str) and raw.strip():
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            pass
        else:
            return dt.astimezone(timezone.utc).timestamp(), raw
    return fallback_path.stat().st_mtime, None


def lock_payload(paths: LoopPaths, cycle_id: str, cycle_dir: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "workspace": str(paths.workspace),
        "cycle_id": cycle_id,
        "cycle_dir": str(cycle_dir),
        "started_at": utc_now_text(),
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
    }


def maybe_break_stale_lock(paths: LoopPaths, stale_after_hours: float) -> dict[str, Any] | None:
    if not paths.lock_path.exists():
        return None
    payload = load_json(paths.lock_path)
    started_at_raw = payload.get("started_at")
    if not isinstance(started_at_raw, str):
        return payload
    try:
        started_at = datetime.fromisoformat(started_at_raw.replace("Z", "+00:00"))
    except ValueError:
        return payload
    if utc_now() - started_at < timedelta(hours=stale_after_hours):
        return payload
    paths.lock_path.unlink(missing_ok=True)
    if paths.current_cycle_path.exists():
        paths.current_cycle_path.unlink()
    return None


def acquire_lock(paths: LoopPaths, payload: dict[str, Any]) -> bool:
    paths.loop_root.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(paths.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
    write_json(paths.current_cycle_path, payload)
    return True


def build_cycle_payload(paths: LoopPaths, cycle_id: str, cycle_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    documents: list[dict[str, str]] = []
    cycle_timestamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    for doc in state["goal"]["documents"]:
        doc_id = str(doc["document_id"])
        document_dir = cycle_dir / "documents" / doc_id
        attempts_dir = document_dir / "attempts"
        documents.append(
            {
                "document_id": doc_id,
                "input_pdf": str(doc["input_pdf"]),
                "document_dir": str(document_dir),
                "attempts_dir": str(attempts_dir),
                "initial_output_dir": str(attempts_dir / f"{cycle_timestamp}-initial"),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "started",
        "cycle_id": cycle_id,
        "cycle_dir": str(cycle_dir),
        "lock_path": str(paths.lock_path),
        "state_path": str(paths.state_path),
        "status_path": str(paths.status_path),
        "required_consecutive_full_pass_cycles": REQUIRED_CONSECUTIVE_PASSES,
        "documents": documents,
    }


def choose_cycle_id() -> str:
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def start_cycle(paths: LoopPaths, stale_after_hours: float) -> dict[str, Any]:
    state = ensure_state(paths)
    if state.get("completed"):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "complete",
            "message": "Optimization loop already completed.",
            "state_path": str(paths.state_path),
            "status_path": str(paths.status_path),
            "completed_at": state.get("completed_at"),
        }

    existing_lock = maybe_break_stale_lock(paths, stale_after_hours)
    if existing_lock is not None and paths.lock_path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "locked",
            "message": "Another optimization cycle is already in progress.",
            "lock_path": str(paths.lock_path),
            "lock": existing_lock,
        }

    cycle_id = choose_cycle_id()
    cycle_dir = paths.cycles_root / cycle_id
    cycle_dir.mkdir(parents=True, exist_ok=True)
    payload = lock_payload(paths, cycle_id, cycle_dir)
    if not acquire_lock(paths, payload):
        locked_payload = load_json(paths.lock_path, default={})
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "locked",
            "message": "Another optimization cycle is already in progress.",
            "lock_path": str(paths.lock_path),
            "lock": locked_payload,
        }

    cycle_entry = {
        "cycle_id": cycle_id,
        "cycle_dir": str(cycle_dir),
        "started_at": payload["started_at"],
        "finished_at": None,
        "status": "running",
        "full_pass": False,
        "documents": {},
        "notes": [],
    }
    state["cycles"] = [entry for entry in state.get("cycles", []) if entry.get("cycle_id") != cycle_id]
    state["cycles"].append(cycle_entry)
    write_json(paths.state_path, state)
    update_status(paths, state)
    return build_cycle_payload(paths, cycle_id, cycle_dir, state)


def current_cycle_id(paths: LoopPaths) -> str:
    payload = load_json(paths.current_cycle_path, default={})
    cycle_id = payload.get("cycle_id")
    if not cycle_id:
        raise SystemExit("No active cycle metadata found.")
    return str(cycle_id)


def pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def active_run_markers(cycle_dir: Path) -> list[dict[str, Any]]:
    active: list[dict[str, Any]] = []
    if not cycle_dir.exists():
        return active
    for marker_path in sorted(cycle_dir.rglob(ACTIVE_RUN_FILENAME)):
        payload = load_json(marker_path, default={})
        pid_raw = payload.get("pid")
        try:
            pid = int(pid_raw)
        except (TypeError, ValueError):
            continue
        hostname = str(payload.get("hostname") or "").strip()
        same_host = not hostname or hostname == socket.gethostname()
        if same_host and not pid_is_alive(pid):
            continue
        active.append(
            {
                "marker_path": str(marker_path),
                "pid": pid,
                "hostname": hostname,
                "document_id": payload.get("document_id"),
                "cycle_id": payload.get("cycle_id"),
                "run_label": payload.get("run_label"),
                "output_dir": payload.get("output_dir"),
            }
        )
    return active


def release_lock(
    paths: LoopPaths,
    cycle_id: str | None,
    reason: str,
    *,
    mark_aborted: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    payload = load_json(paths.lock_path, default={}) if paths.lock_path.exists() else {}
    locked_cycle_id = payload.get("cycle_id")
    resolved_cycle_id = cycle_id or (str(locked_cycle_id) if locked_cycle_id else None)
    if cycle_id and locked_cycle_id and str(locked_cycle_id) != cycle_id:
        raise SystemExit(f"Lock belongs to cycle {locked_cycle_id}, not {cycle_id}.")
    if resolved_cycle_id and not force:
        cycle_dir = paths.cycles_root / resolved_cycle_id
        active_markers = active_run_markers(cycle_dir)
        if active_markers:
            summary = "; ".join(
                f"doc={entry.get('document_id') or '?'} pid={entry['pid']} path={entry['marker_path']}"
                for entry in active_markers
            )
            raise SystemExit(
                f"Cannot release cycle {resolved_cycle_id}: active babel-copy workers are still running or unverified ({summary})."
            )
    if mark_aborted and resolved_cycle_id:
        state = ensure_state(paths)
        update_cycle_entry(
            state,
            resolved_cycle_id,
            {
                "cycle_id": resolved_cycle_id,
                "status": "aborted",
                "finished_at": utc_now_text(),
                "abort_reason": reason,
            },
        )
        write_json(paths.state_path, state)
        update_status(paths, state)
    paths.lock_path.unlink(missing_ok=True)
    paths.current_cycle_path.unlink(missing_ok=True)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "released",
        "reason": reason,
        "cycle_id": resolved_cycle_id,
        "lock_path": str(paths.lock_path),
    }


def latest_qa_for_cycle(cycle_dir: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, tuple[tuple[float, str], dict[str, Any]]] = {}
    for qa_path in sorted(cycle_dir.rglob("qa-report.json")):
        payload = load_json(qa_path)
        doc_id = payload.get("document_id") or doc_id_for_path(Path(str(payload.get("input_pdf") or payload.get("source_pdf") or qa_path.parent.name)))
        score_key = parse_timestamp(payload.get("generated_at"), qa_path)
        entry = {
            "document_id": doc_id,
            "status": payload.get("overall", {}).get("status"),
            "review_status": payload.get("overall", {}).get("review_status"),
            "overall_score": payload.get("overall", {}).get("overall_score"),
            "needs_review_count": payload.get("overall", {}).get("needs_review_count"),
            "review_gate_reasons": payload.get("overall", {}).get("review_gate_reasons"),
            "release_recommendation": payload.get("overall", {}).get("release_recommendation"),
            "qa_report": str(qa_path.resolve()),
            "comparison_report": payload.get("comparison_report_path"),
            "run_manifest_path": payload.get("run_manifest_path"),
            "run_output_dir": payload.get("run_output_dir"),
            "cycle_id": payload.get("cycle_id"),
            "run_label": payload.get("run_label"),
            "run_id": payload.get("run_id"),
            "generated_at": payload.get("generated_at"),
            "summary": payload.get("overall", {}).get("summary"),
        }
        if doc_id not in latest or score_key > latest[doc_id][0]:
            latest[doc_id] = (score_key, entry)
    return {doc_id: entry for doc_id, (_, entry) in latest.items()}


def update_cycle_entry(state: dict[str, Any], cycle_id: str, payload: dict[str, Any]) -> None:
    cycles = state.get("cycles", [])
    for entry in cycles:
        if entry.get("cycle_id") == cycle_id:
            entry.update(payload)
            return
    cycles.append(payload)
    state["cycles"] = cycles


def finish_cycle(paths: LoopPaths, cycle_id: str | None) -> dict[str, Any]:
    state = ensure_state(paths)
    resolved_cycle_id = cycle_id or current_cycle_id(paths)
    cycle_dir = paths.cycles_root / resolved_cycle_id
    if not cycle_dir.exists():
        raise SystemExit(f"Missing cycle directory: {cycle_dir}")

    documents = state["goal"]["documents"]
    latest_reports = latest_qa_for_cycle(cycle_dir)
    document_results: dict[str, Any] = {}
    missing_documents: list[str] = []
    for doc in documents:
        doc_id = str(doc["document_id"])
        result = latest_reports.get(doc_id)
        if result is None:
            missing_documents.append(doc_id)
            document_results[doc_id] = {
                "document_id": doc_id,
                "status": "missing",
                "review_status": None,
                "qa_report": None,
                "comparison_report": None,
                "run_manifest_path": None,
                "run_output_dir": None,
                "run_id": None,
                "generated_at": None,
                "release_recommendation": None,
                "summary": "No qa-report.json found for this document in the cycle directory.",
            }
            continue
        document_results[doc_id] = result

    full_pass = not missing_documents and all(result.get("status") == "pass" for result in document_results.values())
    trailing = int(state.get("consecutive_full_pass_cycles") or 0)
    trailing = trailing + 1 if full_pass else 0
    state["consecutive_full_pass_cycles"] = trailing
    if trailing >= REQUIRED_CONSECUTIVE_PASSES:
        state["completed"] = True
        state["completed_at"] = utc_now_text()
    state["last_finished_cycle_id"] = resolved_cycle_id

    cycle_entry = {
        "cycle_id": resolved_cycle_id,
        "cycle_dir": str(cycle_dir),
        "finished_at": utc_now_text(),
        "status": "completed",
        "full_pass": full_pass,
        "documents": document_results,
        "missing_documents": missing_documents,
    }
    update_cycle_entry(state, resolved_cycle_id, cycle_entry)
    write_json(paths.state_path, state)
    update_status(paths, state)
    release_lock(paths, resolved_cycle_id, "finish", mark_aborted=False)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "finished",
        "cycle_id": resolved_cycle_id,
        "cycle_dir": str(cycle_dir),
        "full_pass": full_pass,
        "consecutive_full_pass_cycles": trailing,
        "completed": state["completed"],
        "state_path": str(paths.state_path),
        "status_path": str(paths.status_path),
        "documents": document_results,
    }


def update_status(paths: LoopPaths, state: dict[str, Any]) -> None:
    lines = [
        "# Babel Copy Optimization Loop",
        "",
        f"- Workspace: `{paths.workspace}`",
        f"- Completed: `{state.get('completed')}`",
        f"- Consecutive full-pass cycles: {state.get('consecutive_full_pass_cycles', 0)} / {REQUIRED_CONSECUTIVE_PASSES}",
        f"- Last finished cycle: `{state.get('last_finished_cycle_id')}`",
        "",
        "## Documents",
        "",
    ]
    for doc in state["goal"]["documents"]:
        lines.append(f"- `{doc['document_id']}`: `{doc['input_pdf']}`")
    lines.extend(["", "## Recent Cycles", ""])
    for entry in sorted(state.get("cycles", []), key=lambda item: str(item.get("cycle_id")), reverse=True)[:5]:
        lines.append(
            f"- `{entry.get('cycle_id')}` status=`{entry.get('status')}` full_pass=`{entry.get('full_pass')}` finished_at=`{entry.get('finished_at')}`"
        )
    paths.status_path.parent.mkdir(parents=True, exist_ok=True)
    paths.status_path.write_text("\n".join(lines) + "\n")


def print_payload(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    paths = LoopPaths(workspace)
    if args.command == "start":
        return print_payload(start_cycle(paths, args.stale_after_hours))
    if args.command == "finish":
        return print_payload(finish_cycle(paths, args.cycle_id))
    if args.command == "release":
        return print_payload(release_lock(paths, args.cycle_id, args.reason, force=args.force))
    if args.command == "status":
        state = ensure_state(paths)
        if args.format == "path":
            print(paths.state_path)
            return 0
        return print_payload(state)
    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
