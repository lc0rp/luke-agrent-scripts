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
            sys.modules.setdefault(name, stub)
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
    def test_resolve_profile_path_supports_env_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            workspace = Path(tmp_raw)
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
                )
        self.assertIsNotNone(path)
        assert path is not None
        self.assertEqual(path.name, "extract_document.json")
        self.assertEqual(path.parent.parent, (workspace / "profiles").resolve())
        self.assertTrue(path.parent.name.startswith("run-"))

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
                )
        self.assertIsNone(path)

    def test_translate_prepare_writes_profile_from_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            workspace = Path(tmp_raw)
            blocks_json = workspace / "blocks.json"
            output_json = workspace / "requests.json"
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
                (workspace / "profiles").glob(
                    "run-*/translate_blocks_desktop-prepare.json"
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
            source_pdf = workspace / "input.pdf"
            source_pdf.write_bytes(b"%PDF-1.4\n")
            translated_json = workspace / "translated.json"
            translated_json.write_text(json.dumps({"pages": [], "blocks": []}))
            output_pdf = workspace / "out.pdf"
            profile_json = workspace / "build.profile.json"

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
                    str(workspace / "profiles"),
                ]
                with mock.patch.object(sys, "argv", argv):
                    result = BUILD_FINAL_PDF.main()
            self.assertEqual(result, 0)
            profile_matches = list((workspace / "profiles").glob("run-*/build_final_pdf.json"))
            self.assertEqual(len(profile_matches), 1)
            profile_json = profile_matches[0]
            payload = json.loads(profile_json.read_text())
        self.assertEqual(payload["command"], "build_final_pdf")
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["counters"]["page_count"], 0)


if __name__ == "__main__":
    unittest.main()
