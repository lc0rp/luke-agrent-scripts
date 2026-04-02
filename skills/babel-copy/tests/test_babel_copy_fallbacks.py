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


def load_module(module_name: str, path: Path):
    if "openai" not in sys.modules:
        fake_openai = types.ModuleType("openai")

        class DummyOpenAI:  # pragma: no cover - tests always patch live usage
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

        fake_openai.OpenAI = DummyOpenAI
        sys.modules["openai"] = fake_openai
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


REPO_ROOT = Path(__file__).resolve().parents[3]
TRANSLATE_BLOCKS_CODEX = load_module(
    "test_translate_blocks_codex",
    REPO_ROOT / "skills" / "babel-copy" / "scripts" / "translate_blocks_codex.py",
)
RUN_OPTIMIZATION_CYCLE = load_module(
    "test_run_optimization_cycle",
    REPO_ROOT / "skills" / "babel-copy-optimizer" / "scripts" / "run_optimization_cycle.py",
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

    def test_resolve_anthropic_api_candidates_prefers_dotenv_then_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            cwd = Path(tmp_raw)
            (cwd / ".env").write_text("ANTHROPIC_API_KEY=dotenv-key-12345678901234567890\n")
            with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key-12345678901234567890"}, clear=False):
                candidates = TRANSLATE_BLOCKS_CODEX.resolve_anthropic_api_candidates(cwd)
        self.assertEqual(
            [entry["source"] for entry in candidates],
            ["dotenv_anthropic_api_key", "env_anthropic_api_key"],
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

    def test_try_anthropic_fallback_skips_invalid_dotenv_and_uses_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            cwd = Path(tmp_raw)
            (cwd / ".env").write_text("ANTHROPIC_API_KEY=xxxxxx\n")
            with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key-12345678901234567890"}, clear=False):
                with mock.patch.object(
                    TRANSLATE_BLOCKS_CODEX,
                    "run_anthropic",
                    return_value={"block-1": "translated"},
                ) as run_anthropic:
                    result = TRANSLATE_BLOCKS_CODEX.try_anthropic_fallback(
                        "prompt",
                        cwd=cwd,
                        model="claude-sonnet-4-20250514",
                        batch_index=1,
                        total_batches=1,
                    )
        self.assertEqual(result, ({"block-1": "translated"}, "env_anthropic_api_key"))
        run_anthropic.assert_called_once()
        self.assertEqual(run_anthropic.call_args.kwargs["api_key"], "env-key-12345678901234567890")

    def test_detect_runtime_mode_prefers_explicit_claude_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            cwd = Path(tmp_raw)
            with mock.patch.dict(os.environ, {"BABEL_COPY_RUNTIME_MODE": "claude"}, clear=False):
                mode = TRANSLATE_BLOCKS_CODEX.detect_runtime_mode(cwd, "auto")
        self.assertEqual(mode, "claude")

    def test_detect_runtime_mode_prefers_anthropic_only_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            cwd = Path(tmp_raw)
            (cwd / ".env").write_text("ANTHROPIC_API_KEY=dotenv-key-12345678901234567890\n")
            with (
                mock.patch.dict(os.environ, {}, clear=True),
                mock.patch.object(TRANSLATE_BLOCKS_CODEX.shutil, "which", side_effect=lambda name: "/usr/bin/" + name),
            ):
                mode = TRANSLATE_BLOCKS_CODEX.detect_runtime_mode(cwd, "auto")
        self.assertEqual(mode, "claude")

    def test_run_claude_uses_print_mode_by_default(self) -> None:
        completed = subprocess_completed('{"translations":{"block-1":"translated"}}')
        with (
            mock.patch.object(TRANSLATE_BLOCKS_CODEX.shutil, "which", return_value="/opt/homebrew/bin/claude"),
            mock.patch.object(TRANSLATE_BLOCKS_CODEX, "log_claude_auth_context", return_value={"auth_path": "claude_code_cli"}),
            mock.patch.object(TRANSLATE_BLOCKS_CODEX.subprocess, "run", return_value=completed) as run_subprocess,
        ):
            translations, context = TRANSLATE_BLOCKS_CODEX.run_claude("prompt", Path("/tmp/work"), None)
        self.assertEqual(translations, {"block-1": "translated"})
        self.assertEqual(context["auth_path"], "claude_code_cli")
        cmd = run_subprocess.call_args.args[0]
        self.assertIn("-p", cmd)
        self.assertIn("--output-format", cmd)
        self.assertIn("--tools", cmd)
        self.assertEqual(run_subprocess.call_args.kwargs["cwd"], "/tmp/work")


def subprocess_completed(stdout: str):
    return mock.Mock(stdout=stdout, stderr="", returncode=0)


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
