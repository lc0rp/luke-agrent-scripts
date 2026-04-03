from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import tracemalloc
from typing import Iterator

SESSION_FILENAME = ".profiler-session.json"
SESSION_REUSE_WINDOW_SECONDS = 6 * 60 * 60


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def profiler_timestamp(compact: bool = True) -> str:
    if compact:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return utc_now_iso()


def _dotenv_candidates(search_from: Path | None = None) -> list[Path]:
    candidates: list[Path] = []
    if search_from is not None:
        candidates.append(search_from / ".env")
    candidates.append(Path.cwd() / ".env")
    candidates.append(Path(__file__).resolve().parents[1] / ".env")
    seen: set[Path] = set()
    ordered: list[Path] = []
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


def load_babel_copy_dotenv(search_from: Path | None = None) -> Path | None:
    for candidate in _dotenv_candidates(search_from):
        if not candidate.exists():
            continue
        for raw_line in candidate.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            os.environ[key] = value.strip()
        return candidate
    return None


def json_safe(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    return str(value)


@dataclass
class ProfileSpan:
    profiler: "SessionProfiler"
    record: dict

    def set(self, **values) -> None:
        data = self.record.setdefault("data", {})
        assert isinstance(data, dict)
        data.update({str(key): json_safe(value) for key, value in values.items()})

    def increment(self, key: str, amount: int = 1) -> None:
        data = self.record.setdefault("data", {})
        assert isinstance(data, dict)
        current = int(data.get(key, 0) or 0)
        data[str(key)] = current + int(amount)


class SessionProfiler:
    def __init__(
        self,
        path: Path | None,
        *,
        command: str,
        metadata: dict | None = None,
    ) -> None:
        self.path = path
        self.enabled = path is not None
        self.command = command
        self.metadata = json_safe(metadata or {})
        self.started_at = utc_now_iso()
        self._run_start = time.perf_counter()
        self._cpu_start = time.process_time()
        self._stack: list[int] = []
        self._stages: list[dict] = []
        self._events: list[dict] = []
        self._counters: dict[str, int | float | str | bool | None] = {}
        self._finished = False
        self._memory_enabled = False
        if self.enabled:
            tracemalloc.start()
            self._memory_enabled = True

    @contextmanager
    def stage(self, name: str, **data) -> Iterator[ProfileSpan]:
        if not self.enabled:
            yield ProfileSpan(self, {"data": {}})
            return
        record = {
            "name": str(name),
            "parent_index": self._stack[-1] if self._stack else None,
            "started_at": utc_now_iso(),
            "data": {str(key): json_safe(value) for key, value in data.items()},
        }
        start = time.perf_counter()
        cpu_start = time.process_time()
        memory_before = tracemalloc.get_traced_memory()[1] if self._memory_enabled else None
        self._stages.append(record)
        index = len(self._stages) - 1
        self._stack.append(index)
        span = ProfileSpan(self, record)
        try:
            yield span
        finally:
            record["wall_ms"] = round((time.perf_counter() - start) * 1000, 3)
            record["cpu_ms"] = round((time.process_time() - cpu_start) * 1000, 3)
            if self._memory_enabled:
                current, peak = tracemalloc.get_traced_memory()
                record["memory_current_bytes"] = current
                record["memory_peak_bytes"] = peak
                record["memory_peak_delta_bytes"] = (
                    None if memory_before is None else peak - memory_before
                )
            self._stack.pop()

    def event(self, name: str, **data) -> None:
        if not self.enabled:
            return
        self._events.append(
            {
                "name": str(name),
                "at": utc_now_iso(),
                "stage_index": self._stack[-1] if self._stack else None,
                "data": {str(key): json_safe(value) for key, value in data.items()},
            }
        )

    def set_counter(self, key: str, value) -> None:
        if not self.enabled:
            return
        self._counters[str(key)] = json_safe(value)

    def increment_counter(self, key: str, amount: int = 1) -> None:
        if not self.enabled:
            return
        current = int(self._counters.get(str(key), 0) or 0)
        self._counters[str(key)] = current + int(amount)

    def finish(self, *, status: str, error: dict | None = None) -> None:
        if not self.enabled or self._finished:
            return
        summary = {
            "command": self.command,
            "pid": os.getpid(),
            "started_at": self.started_at,
            "finished_at": utc_now_iso(),
            "status": str(status),
            "wall_ms": round((time.perf_counter() - self._run_start) * 1000, 3),
            "cpu_ms": round((time.process_time() - self._cpu_start) * 1000, 3),
            "metadata": self.metadata,
            "counters": self._counters,
            "events": self._events,
            "stages": self._stages,
        }
        if error:
            summary["error"] = json_safe(error)
        if self._memory_enabled:
            current, peak = tracemalloc.get_traced_memory()
            summary["memory_current_bytes"] = current
            summary["memory_peak_bytes"] = peak
            tracemalloc.stop()
            self._memory_enabled = False
        assert self.path is not None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
        self._finished = True


def create_profiler(
    path: Path | None,
    *,
    command: str,
    metadata: dict | None = None,
) -> SessionProfiler:
    return SessionProfiler(path, command=command, metadata=metadata)


def profiler_command_name(command: str) -> str:
    return str(command).strip().replace(":", "-")


def profiler_enabled(cli_enabled: bool, *, search_from: Path | None = None) -> bool:
    load_babel_copy_dotenv(search_from)
    if cli_enabled:
        return True
    value = str(os.environ.get("ENABLE_PROFILER", "")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def parse_profiler_commands(raw: str | None) -> set[str] | None:
    if raw is None:
        return None
    stripped = str(raw).strip()
    if not stripped:
        return None
    if stripped.lower() == "all":
        return None
    values = {
        profiler_command_name(item)
        for item in stripped.split(",")
        if item.strip()
    }
    return values or None


def infer_wip_dir(
    *,
    context_paths: list[Path] | None,
    search_from: Path | None = None,
) -> Path:
    for raw_path in context_paths or []:
        path = raw_path.expanduser().resolve()
        treat_as_directory = path.is_dir() or (not path.exists() and path.suffix == "")
        anchors = [path, *path.parents] if treat_as_directory else [path.parent, *path.parent.parents]
        for anchor in anchors:
            if anchor.name == "wip":
                return anchor
        for anchor in anchors:
            candidate = anchor / "wip"
            if candidate.exists():
                return candidate.resolve()
        if treat_as_directory:
            return (path / "wip").resolve()
    if search_from is not None:
        resolved = search_from.expanduser().resolve()
        if resolved.name == "wip":
            return resolved
        return (resolved / "wip").resolve()
    return (Path.cwd() / "wip").resolve()


def _read_session_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def resolve_run_id(profiles_base_dir: Path) -> str:
    session_path = profiles_base_dir / SESSION_FILENAME
    now = time.time()
    session = _read_session_file(session_path)
    if session is not None:
        run_id = str(session.get("run_id", "")).strip()
        last_updated = float(session.get("last_updated_epoch", 0) or 0)
        if run_id and (now - last_updated) <= SESSION_REUSE_WINDOW_SECONDS:
            session["last_updated_epoch"] = now
            session["last_updated_at"] = utc_now_iso()
            session_path.parent.mkdir(parents=True, exist_ok=True)
            session_path.write_text(json.dumps(session, indent=2, ensure_ascii=False))
            return run_id
    run_id = profiler_timestamp()
    session_payload = {
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "last_updated_at": utc_now_iso(),
        "last_updated_epoch": now,
    }
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(json.dumps(session_payload, indent=2, ensure_ascii=False))
    return run_id


def resolve_profile_path(
    *,
    cli_enabled: bool,
    cli_commands: str | None,
    cli_output_dir: str | None,
    command: str,
    search_from: Path | None = None,
    context_paths: list[Path] | None = None,
) -> Path | None:
    env_output_before = os.environ.get("PROFILER_OUTPUT_DIR")
    dotenv_path = load_babel_copy_dotenv(search_from)
    if not profiler_enabled(cli_enabled, search_from=search_from):
        return None
    normalized_command = profiler_command_name(command)
    command_filter = parse_profiler_commands(
        cli_commands if cli_commands is not None else os.environ.get("PROFILER_COMMANDS")
    )
    if command_filter is not None and normalized_command not in command_filter:
        return None
    raw_output_dir = (
        str(cli_output_dir).strip()
        if cli_output_dir is not None
        else str(os.environ.get("PROFILER_OUTPUT_DIR", "")).strip()
    )
    if not raw_output_dir:
        raw_output_dir = "profiles"
    wip_dir = infer_wip_dir(context_paths=context_paths, search_from=search_from)
    base_dir = wip_dir
    if cli_output_dir is None and env_output_before is None and dotenv_path is not None and not Path(raw_output_dir).is_absolute():
        base_dir = wip_dir
    path = Path(raw_output_dir).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    profiles_base_dir = path.resolve()
    run_id = resolve_run_id(profiles_base_dir)
    run_dir = profiles_base_dir / f"runs-{run_id}"
    command_dir = run_dir / normalized_command
    return (command_dir / f"call-{profiler_timestamp()}.json").resolve()
