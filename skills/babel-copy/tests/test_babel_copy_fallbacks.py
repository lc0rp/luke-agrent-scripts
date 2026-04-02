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


def load_module(
    module_name: str,
    path: Path,
    *,
    stub_modules: dict[str, types.ModuleType] | None = None,
):
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    if stub_modules:
        for name, module in stub_modules.items():
            sys.modules.setdefault(name, module)
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
TRANSLATION_RUNTIME = load_module(
    "test_translation_runtime",
    REPO_ROOT / "skills" / "babel-copy" / "scripts" / "translation_runtime.py",
)
TRANSLATE_BLOCKS_CODEX = load_module(
    "test_translate_blocks_codex",
    REPO_ROOT / "skills" / "babel-copy" / "scripts" / "translate_blocks_codex.py",
)
RUN_BABEL_COPY = load_module(
    "test_run_babel_copy",
    REPO_ROOT / "skills" / "babel-copy" / "scripts" / "run_babel_copy.py",
)
RUN_OPTIMIZATION_CYCLE = load_module(
    "test_run_optimization_cycle",
    REPO_ROOT / "skills" / "babel-copy-optimizer" / "scripts" / "run_optimization_cycle.py",
)


def make_extract_document_stubs() -> dict[str, types.ModuleType]:
    fake_core = types.ModuleType("core")
    passthrough_names = [
        "build_font_baseline",
        "classify_page",
        "extract_native_regions",
        "extract_ocr_regions",
        "font_baseline_from_payload",
        "infer_alignment",
        "normalize_font_family_class",
        "ocr_image_to_string",
    ]
    for name in passthrough_names:
        setattr(fake_core, name, lambda *args, **kwargs: None)
    fake_core.clean_text = lambda text: str(text).strip()
    fake_core.normalize_ocr_engine = lambda value: value or "tesseract"
    fake_core.parse_page_selection = lambda pages, count: set(range(1, count + 1))
    fake_core.split_leading_marker = lambda text: ("", text)

    fake_fitz = types.ModuleType("fitz")

    class DummyRect:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class DummyPoint:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    fake_fitz.Rect = DummyRect
    fake_fitz.Point = DummyPoint

    fake_numpy = types.ModuleType("numpy")
    fake_numpy.array = lambda value: value
    fake_numpy.where = lambda value: ([], [])

    fake_pil = types.ModuleType("PIL")
    fake_pil_image = types.ModuleType("PIL.Image")

    class DummyImage:
        pass

    fake_pil_image.Image = DummyImage
    fake_pil.Image = fake_pil_image

    return {
        "core": fake_core,
        "fitz": fake_fitz,
        "numpy": fake_numpy,
        "PIL": fake_pil,
        "PIL.Image": fake_pil_image,
    }


EXTRACT_DOCUMENT = load_module(
    "test_extract_document",
    REPO_ROOT / "skills" / "babel-copy" / "scripts" / "extract_document.py",
    stub_modules=make_extract_document_stubs(),
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
                mock.patch.object(TRANSLATION_RUNTIME.shutil, "which", side_effect=lambda name: "/usr/bin/" + name),
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


class ExtractDocumentTests(unittest.TestCase):
    def test_run_fragment_merge_dispatches_to_claude_runtime(self) -> None:
        candidates = [{"pair_id": "p1->p2"}]
        with (
            mock.patch.object(EXTRACT_DOCUMENT, "translation_provider", return_value="auto"),
            mock.patch.object(EXTRACT_DOCUMENT, "detect_runtime_mode", return_value="claude"),
            mock.patch.object(
                EXTRACT_DOCUMENT,
                "run_claude_fragment_merge",
                return_value={"p1->p2": True},
            ) as run_claude,
            mock.patch.object(EXTRACT_DOCUMENT, "run_codex_fragment_merge") as run_codex,
        ):
            decisions = EXTRACT_DOCUMENT.run_fragment_merge(
                candidates,
                cwd=Path("/tmp/work"),
                provider="auto",
            )
        self.assertEqual(decisions, {"p1->p2": True})
        run_claude.assert_called_once_with(candidates, cwd=Path("/tmp/work"))
        run_codex.assert_not_called()


class RunBabelCopyTests(unittest.TestCase):
    def test_main_passes_translation_provider_to_extract_and_translate_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            workspace = Path(tmp_raw)
            input_pdf = workspace / "sample.pdf"
            input_pdf.write_bytes(b"%PDF-1.4\n")
            output_dir = workspace / "out"
            commands: list[list[str]] = []

            def fake_run_step(cmd: list[str]) -> None:
                commands.append(cmd)
                if cmd[1].endswith("extract_document.py"):
                    extract_dir = output_dir / "extracted"
                    extract_dir.mkdir(parents=True, exist_ok=True)
                    (extract_dir / "blocks.json").write_text(
                        json.dumps(
                            {
                                "page_count": 1,
                                "pages": [],
                                "blocks": [],
                                "font_baseline": {},
                            }
                        )
                    )

            with mock.patch.object(RUN_BABEL_COPY, "run_step", side_effect=fake_run_step):
                with mock.patch.object(
                    sys,
                    "argv",
                    [
                        "run_babel_copy.py",
                        str(input_pdf),
                        "--output-dir",
                        str(output_dir),
                        "--translation-provider",
                        "claude",
                        "--skip-compare",
                    ],
                ):
                    exit_code = RUN_BABEL_COPY.main()

        self.assertEqual(exit_code, 0)
        self.assertGreaterEqual(len(commands), 3)
        extract_cmd = commands[0]
        translate_cmd = commands[1]
        self.assertEqual(
            extract_cmd[extract_cmd.index("--translation-provider") + 1], "claude"
        )
        self.assertEqual(
            translate_cmd[translate_cmd.index("--provider") + 1], "claude"
        )


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
