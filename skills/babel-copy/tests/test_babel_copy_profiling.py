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


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def load_module(
    module_name: str,
    path: Path,
    *,
    stub_modules: dict[str, types.ModuleType] | None = None,
):
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    if stub_modules:
        for name, stub in stub_modules.items():
            sys.modules[name] = stub
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


PROFILING = load_module("test_babel_copy_profiling_helper", SCRIPT_DIR / "profiling.py")
TRANSLATE_BLOCKS_DESKTOP = load_module(
    "test_babel_copy_translate_blocks_desktop",
    SCRIPT_DIR / "translate_blocks_desktop.py",
)
def make_build_final_pdf_stubs() -> dict[str, types.ModuleType]:
    fake_fitz = types.ModuleType("fitz")

    class DummyRect:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    fake_fitz.Rect = DummyRect
    fake_fitz.Document = object
    fake_core = types.ModuleType("core")
    fake_core.PDF_SERIF_FONT_NAME = "Times-Roman"
    fake_core.TEXT_SERIF_FONT_NAME = "Times New Roman"
    fake_core.font_baseline_from_payload = lambda payload: {}
    fake_block_overrides = types.ModuleType("block_overrides")
    fake_block_overrides.apply_custom_overrides_to_payload = lambda payload: payload
    return {
        "fitz": fake_fitz,
        "core": fake_core,
        "block_overrides": fake_block_overrides,
        "profiling": PROFILING,
    }


BUILD_FINAL_PDF = load_module(
    "test_babel_copy_build_final_pdf_profile",
    SCRIPT_DIR / "build_final_pdf.py",
    stub_modules=make_build_final_pdf_stubs(),
)


class ProfilingSupportTests(unittest.TestCase):
    def test_resolve_profile_path_uses_wip_profiles_and_command_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            workspace = Path(tmp_raw)
            output_root = workspace / "job-output"
            wip_dir = output_root / "wip"
            (workspace / ".env").write_text(
                "ENABLE_PROFILER=1\n"
                "PROFILER_OUTPUT_DIR=profiles\n"
            )
            with mock.patch.dict(os.environ, {}, clear=True):
                path = PROFILING.resolve_profile_path(
                    cli_enabled=False,
                    cli_commands=None,
                    cli_output_dir=None,
                    command="extract_document",
                    search_from=workspace,
                    context_paths=[output_root],
                )
        self.assertIsNotNone(path)
        assert path is not None
        self.assertTrue(path.name.startswith("call-"))
        self.assertEqual(path.parent.name, "extract_document")
        self.assertTrue(path.parent.parent.name.startswith("runs-"))
        self.assertEqual(path.parent.parent.parent, (wip_dir / "profiles").resolve())

    def test_resolve_profile_path_honors_command_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            workspace = Path(tmp_raw)
            (workspace / ".env").write_text(
                "ENABLE_PROFILER=1\n"
                "PROFILER_COMMANDS=build_final_pdf\n"
            )
            with mock.patch.dict(os.environ, {}, clear=True):
                path = PROFILING.resolve_profile_path(
                    cli_enabled=False,
                    cli_commands=None,
                    cli_output_dir=None,
                    command="extract_document",
                    search_from=workspace,
                    context_paths=[workspace / "job-output"],
                )
        self.assertIsNone(path)

    def test_resolve_profile_path_reuses_run_dir_and_separates_command_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            workspace = Path(tmp_raw)
            output_root = workspace / "job-output"
            (workspace / ".env").write_text(
                "ENABLE_PROFILER=1\n"
                "PROFILER_OUTPUT_DIR=profiles\n"
            )
            with mock.patch.dict(os.environ, {}, clear=True):
                first = PROFILING.resolve_profile_path(
                    cli_enabled=False,
                    cli_commands=None,
                    cli_output_dir=None,
                    command="build_final_pdf",
                    search_from=workspace,
                    context_paths=[output_root],
                )
                second = PROFILING.resolve_profile_path(
                    cli_enabled=False,
                    cli_commands=None,
                    cli_output_dir=None,
                    command="build_final_pdf",
                    search_from=workspace,
                    context_paths=[output_root],
                )
                third = PROFILING.resolve_profile_path(
                    cli_enabled=False,
                    cli_commands=None,
                    cli_output_dir=None,
                    command="extract_document",
                    search_from=workspace,
                    context_paths=[output_root],
                )
        assert first is not None and second is not None and third is not None
        self.assertEqual(first.parent, second.parent)
        self.assertNotEqual(first.name, second.name)
        self.assertEqual(first.parent.parent, third.parent.parent)
        self.assertEqual(third.parent.name, "extract_document")

    def test_translate_prepare_writes_profile_from_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            workspace = Path(tmp_raw)
            output_root = workspace / "job-output"
            wip_dir = output_root / "wip"
            wip_dir.mkdir(parents=True)
            blocks_json = wip_dir / "blocks.json"
            output_json = wip_dir / "requests.json"
            blocks_json.write_text(
                json.dumps(
                    {
                        "blocks": [
                            {
                                "id": "block-1",
                                "page_number": 1,
                                "role": "paragraph",
                                "text": "Bonjour",
                            }
                        ]
                    }
                )
            )
            (workspace / ".env").write_text(
                "ENABLE_PROFILER=1\n"
                "PROFILER_OUTPUT_DIR=profiles\n"
            )
            argv = [
                "translate_blocks_desktop.py",
                "prepare",
                str(blocks_json),
                "--output-json",
                str(output_json),
            ]
            old_cwd = os.getcwd()
            try:
                os.chdir(workspace)
                with mock.patch.dict(os.environ, {}, clear=True):
                    with mock.patch.object(sys, "argv", argv):
                        result = TRANSLATE_BLOCKS_DESKTOP.main()
            finally:
                os.chdir(old_cwd)
            self.assertEqual(result, 0)
            profile_matches = list(
                (wip_dir / "profiles").glob(
                    "runs-*/translate_blocks_desktop-prepare/call-*.json"
                )
            )
            self.assertEqual(len(profile_matches), 1)
            profile_path = profile_matches[0]
            payload = json.loads(profile_path.read_text())
        self.assertEqual(payload["command"], "translate_blocks_desktop:prepare")
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["counters"]["request_count"], 1)

    def test_build_final_pdf_writes_profile_with_cli_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            workspace = Path(tmp_raw)
            output_root = workspace / "job-output"
            wip_dir = output_root / "wip"
            wip_dir.mkdir(parents=True)
            source_pdf = workspace / "input.pdf"
            source_pdf.write_bytes(b"%PDF-1.4\n")
            translated_json = wip_dir / "translated.json"
            translated_json.write_text(json.dumps({"pages": [], "blocks": []}))
            output_pdf = wip_dir / "out.pdf"

            with mock.patch.object(
                BUILD_FINAL_PDF,
                "render_hybrid_document",
                return_value=output_pdf,
            ):
                argv = [
                    "build_final_pdf.py",
                    str(source_pdf),
                    str(translated_json),
                    "--output-pdf",
                    str(output_pdf),
                    "--profiler",
                    "--profiler-output-dir",
                    "profiles",
                ]
                with mock.patch.object(sys, "argv", argv):
                    result = BUILD_FINAL_PDF.main()
            self.assertEqual(result, 0)
            profile_matches = list((wip_dir / "profiles").glob("runs-*/build_final_pdf/call-*.json"))
            self.assertEqual(len(profile_matches), 1)
            profile_json = profile_matches[0]
            payload = json.loads(profile_json.read_text())
        self.assertEqual(payload["command"], "build_final_pdf")
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["counters"]["page_count"], 0)


if __name__ == "__main__":
    unittest.main()
