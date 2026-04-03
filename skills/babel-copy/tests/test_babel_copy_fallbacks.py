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
    def test_translation_provider_choices_are_desktop_only(self) -> None:
        self.assertEqual(
            TRANSLATION_RUNTIME.TRANSLATION_PROVIDER_CHOICES,
            ("auto", "codex", "claude"),
        )

    def test_detect_runtime_mode_prefers_explicit_claude_override(self) -> None:
        with mock.patch.dict(os.environ, {"BABEL_COPY_RUNTIME_MODE": "claude"}, clear=False):
            mode = TRANSLATE_BLOCKS_CODEX.detect_runtime_mode("auto")
        self.assertEqual(mode, "claude")

    def test_detect_runtime_mode_defaults_to_codex(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            mode = TRANSLATE_BLOCKS_CODEX.detect_runtime_mode("auto")
        self.assertEqual(mode, "codex")

    def test_prepare_request_payload_writes_desktop_batches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            workspace = Path(tmp_raw)
            blocks_json = workspace / "blocks.json"
            requests_json = workspace / "translation-requests.json"
            blocks_json.write_text(
                json.dumps(
                    {
                        "blocks": [
                            {
                                "id": "block-1",
                                "page_number": 1,
                                "role": "paragraph",
                                "text": "Bonjour",
                            },
                            {
                                "id": "block-2",
                                "page_number": 1,
                                "role": "paragraph",
                                "text": "Merci",
                            },
                        ]
                    }
                )
            )
            result = TRANSLATE_BLOCKS_CODEX.prepare_request_payload(
                blocks_json=blocks_json,
                output_json=requests_json,
                source_lang="French",
                target_lang="English",
                batch_size=1,
                provider="claude",
                model="claude-sonnet-4-20250514",
            )
            self.assertEqual(result, requests_json)
            payload = json.loads(requests_json.read_text())
        self.assertEqual(payload["kind"], "babel_copy_translation_requests")
        self.assertEqual(payload["request_count"], 2)
        self.assertEqual(payload["runtime_mode"], "claude")
        self.assertEqual(payload["requests"][0]["block_ids"], ["block-1"])
        self.assertIn("Translate the following document blocks", payload["requests"][0]["prompt"])

    def test_apply_response_payload_builds_translated_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            workspace = Path(tmp_raw)
            blocks_json = workspace / "blocks.json"
            requests_json = workspace / "translation-requests.json"
            responses_json = workspace / "translation-responses.json"
            output_json = workspace / "translated_blocks.json"
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
            requests_json.write_text(
                json.dumps(
                    {
                        "runtime_mode": "claude",
                        "provider": "claude",
                        "requests": [{"request_id": "batch-001"}],
                    }
                )
            )
            responses_json.write_text(
                json.dumps(
                    {
                        "responses": [
                            {
                                "request_id": "batch-001",
                                "response_text": '{"translations":{"block-1":"Hello"}}',
                            }
                        ]
                    }
                )
            )
            result = TRANSLATE_BLOCKS_CODEX.apply_response_payload(
                blocks_json=blocks_json,
                requests_json=requests_json,
                responses_json=responses_json,
                output_json=output_json,
                provider_override=None,
            )
            self.assertEqual(result, output_json)
            payload = json.loads(output_json.read_text())
        self.assertEqual(payload["blocks"][0]["translated_text"], "Hello")
        self.assertEqual(payload["translation_mode"], "desktop_subagent")
        self.assertEqual(payload["translation_backend_used"], "claude_desktop_subagent")


class ExtractDocumentTests(unittest.TestCase):
    def test_llm_fragment_merge_returns_desktop_request_when_unresolved(self) -> None:
        candidates = [
            {
                "pair_id": "p1-b1->p1-b2",
                "page_number": 1,
                "previous_role": "paragraph",
                "current_role": "paragraph",
                "vertical_gap": 4.0,
                "previous_text": "Bonjour",
                "current_text": "le monde",
                "cache_key": "cache-1",
            }
        ]
        with mock.patch.object(
            EXTRACT_DOCUMENT,
            "collect_fragment_merge_candidates",
            return_value=(candidates, set(), {"p1-b1->p1-b2": ("p1-b1", "p1-b2")}),
        ):
            decisions, requests = EXTRACT_DOCUMENT.llm_fragment_merge_decisions(
                [{"id": "unused"}],
                cwd=Path("/tmp/work"),
                provider="claude",
                provided_pair_decisions={},
            )
        self.assertEqual(decisions, set())
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["runtime_mode"], "claude")
        self.assertEqual(requests[0]["pair_ids"], ["p1-b1->p1-b2"])

    def test_load_fragment_merge_pair_decisions_accepts_response_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            responses_json = Path(tmp_raw) / "fragment-merge-responses.json"
            responses_json.write_text(
                json.dumps(
                    {
                        "responses": [
                            {
                                "request_id": "page-001-fragment-merge",
                                "response_text": '{"decisions":{"p1-b1->p1-b2":"yes"}}',
                            }
                        ]
                    }
                )
            )
            decisions = EXTRACT_DOCUMENT.load_fragment_merge_pair_decisions(
                responses_json
            )
        self.assertEqual(decisions, {"p1-b1->p1-b2": True})


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
