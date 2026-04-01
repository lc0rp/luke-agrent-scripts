from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


def load_module(module_name: str, path: str):
    if "openai" not in sys.modules:
        fake_openai = types.ModuleType("openai")

        class DummyOpenAI:  # pragma: no cover - tests always patch live usage
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

        fake_openai.OpenAI = DummyOpenAI
        sys.modules["openai"] = fake_openai
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


TRANSLATE_BLOCKS_CODEX = load_module(
    "test_translate_blocks_codex",
    "/Users/luke/Documents/dev/luke-agent-scripts/skills/babel-copy/scripts/translate_blocks_codex.py",
)
RUN_OPTIMIZATION_CYCLE = load_module(
    "test_run_optimization_cycle",
    "/Users/luke/Documents/dev/luke-agent-scripts/skills/babel-copy-optimizer/scripts/run_optimization_cycle.py",
)


class TranslateBlocksCodexTests(unittest.TestCase):
    def test_resolve_openai_api_candidates_prefers_dotenv_then_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            cwd = Path(tmp_raw)
            (cwd / ".env").write_text("OPENAI_API_KEY=dotenv-key-12345678901234567890\n")
            with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "env-key-12345678901234567890"}, clear=False):
                candidates = TRANSLATE_BLOCKS_CODEX.resolve_openai_api_candidates(cwd)
        self.assertEqual(
            [entry["source"] for entry in candidates],
            ["dotenv_openai_api_key", "env_openai_api_key"],
        )

    def test_try_openai_fallback_skips_invalid_dotenv_and_uses_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            cwd = Path(tmp_raw)
            (cwd / ".env").write_text("OPENAI_API_KEY=xxxxxx\n")
            with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "env-key-12345678901234567890"}, clear=False):
                with mock.patch.object(
                    TRANSLATE_BLOCKS_CODEX,
                    "run_openai",
                    return_value={"block-1": "translated"},
                ) as run_openai:
                    result = TRANSLATE_BLOCKS_CODEX.try_openai_fallback(
                        "prompt",
                        cwd=cwd,
                        model="gpt-5.4-mini",
                        batch_index=1,
                        total_batches=1,
                    )
        self.assertEqual(result, ({"block-1": "translated"}, "env_openai_api_key"))
        run_openai.assert_called_once()
        self.assertEqual(run_openai.call_args.kwargs["api_key"], "env-key-12345678901234567890")

    def test_try_openai_fallback_prefers_valid_dotenv_over_invalid_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            cwd = Path(tmp_raw)
            (cwd / ".env").write_text("OPENAI_API_KEY=dotenv-key-12345678901234567890\n")
            with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "xxxxxx"}, clear=False):
                with mock.patch.object(
                    TRANSLATE_BLOCKS_CODEX,
                    "run_openai",
                    return_value={"block-1": "translated"},
                ) as run_openai:
                    result = TRANSLATE_BLOCKS_CODEX.try_openai_fallback(
                        "prompt",
                        cwd=cwd,
                        model="gpt-5.4-mini",
                        batch_index=1,
                        total_batches=1,
                    )
        self.assertEqual(result, ({"block-1": "translated"}, "dotenv_openai_api_key"))
        run_openai.assert_called_once()
        self.assertEqual(run_openai.call_args.kwargs["api_key"], "dotenv-key-12345678901234567890")

    def test_try_openai_fallback_retries_next_candidate_after_invalid_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            cwd = Path(tmp_raw)
            (cwd / ".env").write_text("OPENAI_API_KEY=dotenv-key-12345678901234567890\n")
            with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "env-key-12345678901234567890"}, clear=False):
                run_openai = mock.Mock(
                    side_effect=[
                        RuntimeError("401 invalid_api_key"),
                        {"block-1": "translated"},
                    ]
                )
                with mock.patch.object(TRANSLATE_BLOCKS_CODEX, "run_openai", run_openai):
                    result = TRANSLATE_BLOCKS_CODEX.try_openai_fallback(
                        "prompt",
                        cwd=cwd,
                        model="gpt-5.4-mini",
                        batch_index=1,
                        total_batches=1,
                    )
        self.assertEqual(result, ({"block-1": "translated"}, "env_openai_api_key"))
        self.assertEqual(run_openai.call_count, 2)

    def test_try_openai_fallback_returns_none_when_no_candidates_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            cwd = Path(tmp_raw)
            with mock.patch.dict(os.environ, {}, clear=True):
                result = TRANSLATE_BLOCKS_CODEX.try_openai_fallback(
                    "prompt",
                    cwd=cwd,
                    model="gpt-5.4-mini",
                    batch_index=1,
                    total_batches=1,
                )
        self.assertIsNone(result)


class ReleaseGuardTests(unittest.TestCase):
    def make_workspace(self) -> tuple[Path, object]:
        tmpdir = tempfile.TemporaryDirectory()
        workspace = Path(tmpdir.name)
        loop_root = workspace / "output" / "optimization-loop"
        cycle_id = "20260401T120000Z"
        cycle_dir = loop_root / "cycles" / cycle_id
        cycle_dir.mkdir(parents=True, exist_ok=True)
        (workspace / "french-orig").mkdir(parents=True, exist_ok=True)
        (workspace / "french-orig" / "F1 sample.pdf").write_bytes(b"%PDF-1.4\n")
        (loop_root / "loop.lock").write_text(json.dumps({"cycle_id": cycle_id}) + "\n")
        (loop_root / "current-cycle.json").write_text(json.dumps({"cycle_id": cycle_id}) + "\n")
        (loop_root / "state.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "workspace": str(workspace),
                    "goal": {
                        "required_consecutive_full_pass_cycles": 2,
                        "documents": [{"document_id": "F1", "input_pdf": str(workspace / "french-orig" / "F1 sample.pdf")}],
                    },
                    "completed": False,
                    "completed_at": None,
                    "consecutive_full_pass_cycles": 0,
                    "last_finished_cycle_id": None,
                    "cycles": [],
                }
            )
            + "\n"
        )
        paths = RUN_OPTIMIZATION_CYCLE.LoopPaths(workspace)
        self.addCleanup(tmpdir.cleanup)
        return cycle_dir, paths

    def test_release_lock_blocks_when_active_worker_marker_is_alive(self) -> None:
        cycle_dir, paths = self.make_workspace()
        marker_dir = cycle_dir / "documents" / "F1" / "attempts" / "20260401T120000Z-initial"
        marker_dir.mkdir(parents=True, exist_ok=True)
        (marker_dir / "active-run.json").write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "hostname": RUN_OPTIMIZATION_CYCLE.socket.gethostname(),
                    "document_id": "F1",
                    "cycle_id": "20260401T120000Z",
                    "run_label": "initial",
                    "output_dir": str(marker_dir),
                }
            )
            + "\n"
        )
        with self.assertRaises(SystemExit) as exc:
            RUN_OPTIMIZATION_CYCLE.release_lock(paths, "20260401T120000Z", "usage_limit_blocked")
        self.assertIn("active babel-copy workers", str(exc.exception))

    def test_release_lock_allows_dead_worker_marker(self) -> None:
        cycle_dir, paths = self.make_workspace()
        marker_dir = cycle_dir / "documents" / "F1" / "attempts" / "20260401T120000Z-initial"
        marker_dir.mkdir(parents=True, exist_ok=True)
        (marker_dir / "active-run.json").write_text(
            json.dumps(
                {
                    "pid": 999999,
                    "hostname": RUN_OPTIMIZATION_CYCLE.socket.gethostname(),
                    "document_id": "F1",
                    "cycle_id": "20260401T120000Z",
                    "run_label": "initial",
                    "output_dir": str(marker_dir),
                }
            )
            + "\n"
        )
        result = RUN_OPTIMIZATION_CYCLE.release_lock(paths, "20260401T120000Z", "usage_limit_blocked")
        self.assertEqual(result["status"], "released")
        self.assertFalse(paths.lock_path.exists())


if __name__ == "__main__":
    unittest.main()
