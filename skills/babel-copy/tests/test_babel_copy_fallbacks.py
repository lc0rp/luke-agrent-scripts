from __future__ import annotations

from contextlib import ExitStack
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
            sys.modules[name] = module
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
TRANSLATE_BLOCKS_DESKTOP = load_module(
    "test_translate_blocks_desktop",
    REPO_ROOT / "skills" / "babel-copy" / "scripts" / "translate_blocks_desktop.py",
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
        "ocr_image_to_lines",
        "normalize_font_family_class",
        "ocr_image_to_string",
        "ocr_page_image",
        "page_image_fast",
    ]
    for name in passthrough_names:
        setattr(fake_core, name, lambda *args, **kwargs: None)
    fake_core.clean_text = lambda text: str(text).strip()
    fake_core.parse_page_selection = lambda pages, count: set(range(1, count + 1))
    fake_core.split_leading_marker = lambda text: ("", text)

    fake_fitz = types.ModuleType("fitz")

    class DummyRect:
        def __init__(self, *args, **kwargs):
            if len(args) == 1:
                values = args[0]
            else:
                values = args
            self.x0, self.y0, self.x1, self.y1 = [float(value) for value in values]

        @property
        def width(self):
            return self.x1 - self.x0

        @property
        def height(self):
            return self.y1 - self.y0

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
            mode = TRANSLATE_BLOCKS_DESKTOP.detect_runtime_mode("auto")
        self.assertEqual(mode, "claude")

    def test_detect_runtime_mode_defaults_to_codex(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            mode = TRANSLATE_BLOCKS_DESKTOP.detect_runtime_mode("auto")
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
            result = TRANSLATE_BLOCKS_DESKTOP.prepare_request_payload(
                blocks_json=blocks_json,
                output_json=requests_json,
                source_lang="French",
                target_lang="English",
                batch_size=1,
                batch_char_budget=1000,
                provider="claude",
                model="claude-sonnet-4-20250514",
            )
            self.assertEqual(result, requests_json)
            payload = json.loads(requests_json.read_text())
        self.assertEqual(payload["kind"], "babel_copy_translation_requests")
        self.assertEqual(payload["request_count"], 2)
        self.assertEqual(payload["runtime_mode"], "claude")
        self.assertEqual(payload["requests"][0]["page_numbers"], [1])
        self.assertEqual(payload["requests"][0]["block_ids"], ["block-1"])
        self.assertIn("Translate the following document blocks", payload["requests"][0]["prompt"])

    def test_chunk_translation_batches_splits_dense_text_by_prompt_budget(self) -> None:
        blocks = [
            {
                "id": f"block-{index}",
                "page_number": 1,
                "role": "paragraph",
                "text": f"Clause {index}: " + ("texte " * 80),
            }
            for index in range(1, 4)
        ]

        budget = len(
            TRANSLATE_BLOCKS_DESKTOP.build_prompt(blocks[:2], "French", "English")
        )
        batches = TRANSLATE_BLOCKS_DESKTOP.chunk_translation_batches(
            blocks,
            source_lang="French",
            target_lang="English",
            max_blocks=10,
            max_prompt_chars=budget,
        )

        self.assertEqual([[block["id"] for block in batch] for batch in batches], [
            ["block-1", "block-2"],
            ["block-3"],
        ])

    def test_chunk_translation_batches_prefers_page_boundary_when_batch_is_nearly_full(self) -> None:
        first_page_block = {
            "id": "block-1",
            "page_number": 1,
            "role": "paragraph",
            "text": "Préambule: " + ("texte " * 120),
        }
        second_page_block = {
            "id": "block-2",
            "page_number": 2,
            "role": "paragraph",
            "text": "Suite courte.",
        }
        first_prompt_chars = len(
            TRANSLATE_BLOCKS_DESKTOP.build_prompt(
                [first_page_block],
                "French",
                "English",
            )
        )
        budget = max(1, int(first_prompt_chars / 0.8))

        batches = TRANSLATE_BLOCKS_DESKTOP.chunk_translation_batches(
            [first_page_block, second_page_block],
            source_lang="French",
            target_lang="English",
            max_blocks=10,
            max_prompt_chars=budget,
        )

        self.assertEqual([[block["id"] for block in batch] for batch in batches], [
            ["block-1"],
            ["block-2"],
        ])

    def test_prepare_request_payload_reuses_cached_translations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            workspace = Path(tmp_raw)
            blocks_json = workspace / "blocks.json"
            requests_json = workspace / "translation-requests.json"
            translated_json = workspace / "translated_blocks.json"
            blocks_json.write_text(
                json.dumps(
                    {
                        "blocks": [
                            {
                                "id": "block-1",
                                "page_number": 1,
                                "role": "paragraph",
                                "text": "Bonjour",
                                "fingerprint": "same-1",
                            },
                            {
                                "id": "block-2",
                                "page_number": 2,
                                "role": "paragraph",
                                "text": "Nouveau texte",
                                "fingerprint": "new-2",
                            },
                        ]
                    }
                )
            )
            translated_json.write_text(
                json.dumps(
                    {
                        "translation_source_lang": "French",
                        "translation_target_lang": "English",
                        "blocks": [
                            {
                                "id": "block-1",
                                "page_number": 1,
                                "role": "paragraph",
                                "text": "Bonjour",
                                "fingerprint": "same-1",
                                "translated_text": "Hello",
                            },
                            {
                                "id": "block-2",
                                "page_number": 2,
                                "role": "paragraph",
                                "text": "Ancien texte",
                                "fingerprint": "old-2",
                                "translated_text": "Old text",
                            },
                        ]
                    }
                )
            )

            TRANSLATE_BLOCKS_DESKTOP.prepare_request_payload(
                blocks_json=blocks_json,
                output_json=requests_json,
                source_lang="French",
                target_lang="English",
                batch_size=10,
                batch_char_budget=1000,
                provider="claude",
                model=None,
            )
            payload = json.loads(requests_json.read_text())

        self.assertEqual(payload["cached_translation_count"], 1)
        self.assertEqual(payload["cached_translations"], {"block-1": "Hello"})
        self.assertEqual(payload["request_count"], 1)
        self.assertEqual(payload["requests"][0]["block_ids"], ["block-2"])

    def test_prepare_request_payload_does_not_reuse_cached_translations_for_other_target_lang(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            workspace = Path(tmp_raw)
            blocks_json = workspace / "blocks.json"
            requests_json = workspace / "translation-requests.json"
            translated_json = workspace / "translated_blocks.json"
            blocks_json.write_text(
                json.dumps(
                    {
                        "blocks": [
                            {
                                "id": "block-1",
                                "page_number": 1,
                                "role": "paragraph",
                                "text": "Bonjour",
                                "fingerprint": "same-1",
                            }
                        ]
                    }
                )
            )
            translated_json.write_text(
                json.dumps(
                    {
                        "translation_source_lang": "French",
                        "translation_target_lang": "English",
                        "blocks": [
                            {
                                "id": "block-1",
                                "page_number": 1,
                                "role": "paragraph",
                                "text": "Bonjour",
                                "fingerprint": "same-1",
                                "translated_text": "Hello",
                            }
                        ],
                    }
                )
            )

            TRANSLATE_BLOCKS_DESKTOP.prepare_request_payload(
                blocks_json=blocks_json,
                output_json=requests_json,
                source_lang="French",
                target_lang="German",
                batch_size=10,
                batch_char_budget=1000,
                provider="claude",
                model=None,
            )
            payload = json.loads(requests_json.read_text())

        self.assertEqual(payload["cached_translation_count"], 0)
        self.assertEqual(payload["cached_translations"], {})
        self.assertEqual(payload["request_count"], 1)
        self.assertEqual(payload["requests"][0]["block_ids"], ["block-1"])

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
                        "source_lang": "French",
                        "target_lang": "English",
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
            result = TRANSLATE_BLOCKS_DESKTOP.apply_response_payload(
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
        self.assertEqual(payload["translation_source_lang"], "French")
        self.assertEqual(payload["translation_target_lang"], "English")


class ExtractDocumentTableHeuristicsTests(unittest.TestCase):
    def test_skip_ruled_table_detection_for_strong_single_column_prose(self) -> None:
        page_rect = types.SimpleNamespace(width=612.0, height=792.0)
        page_blocks = [
            {
                "bbox": [72.0, 90.0, 510.0, 130.0],
                "text": "This paragraph is intentionally long enough to look like normal body copy on a prose-heavy legal page.",
                "role": "paragraph",
                "keep_original": False,
            },
            {
                "bbox": [72.0, 138.0, 512.0, 178.0],
                "text": "Another wide paragraph continues the same single-column rhythm without any signs of cell boundaries or tabular alignment.",
                "role": "paragraph",
                "keep_original": False,
            },
            {
                "bbox": [73.0, 186.0, 508.0, 226.0],
                "text": "A third paragraph keeps the left edge stable and leaves no compact multi-column label pattern for the table detector to chase.",
                "role": "paragraph",
                "keep_original": False,
            },
            {
                "bbox": [74.0, 234.0, 506.0, 274.0],
                "text": "The last paragraph preserves the same geometry so the page strongly resembles straight prose instead of a form or bordered table.",
                "role": "paragraph",
                "keep_original": False,
            },
        ]

        result = EXTRACT_DOCUMENT.should_skip_ruled_table_detection(
            page_blocks, page_rect
        )

        self.assertTrue(result)

    def test_keep_ruled_table_detection_for_obvious_columnar_layout(self) -> None:
        page_rect = types.SimpleNamespace(width=612.0, height=792.0)
        page_blocks = [
            {
                "bbox": [72.0, 120.0, 160.0, 142.0],
                "text": "Item",
                "role": "paragraph",
                "keep_original": False,
            },
            {
                "bbox": [220.0, 120.0, 308.0, 142.0],
                "text": "Amount",
                "role": "paragraph",
                "keep_original": False,
            },
            {
                "bbox": [404.0, 120.0, 492.0, 142.0],
                "text": "Status",
                "role": "paragraph",
                "keep_original": False,
            },
            {
                "bbox": [72.0, 162.0, 160.0, 184.0],
                "text": "Fee",
                "role": "paragraph",
                "keep_original": False,
            },
            {
                "bbox": [220.0, 162.0, 308.0, 184.0],
                "text": "100.00",
                "role": "paragraph",
                "keep_original": False,
            },
            {
                "bbox": [404.0, 162.0, 492.0, 184.0],
                "text": "Due",
                "role": "paragraph",
                "keep_original": False,
            },
        ]

        result = EXTRACT_DOCUMENT.should_skip_ruled_table_detection(
            page_blocks, page_rect
        )

        self.assertFalse(result)


class ExtractDocumentTests(unittest.TestCase):
    def test_can_reuse_extracted_page_requires_matching_fingerprint_and_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            workspace = Path(tmp_raw)
            asset_path = workspace / "asset.png"
            asset_path.write_bytes(b"png")
            previous_page = {
                "page_number": 1,
                "source_fingerprint": "fp-1",
                "render_path": None,
            }

            self.assertTrue(
                EXTRACT_DOCUMENT.can_reuse_extracted_page(
                    previous_page=previous_page,
                    page_fingerprint_matches_previous=True,
                    previous_page_assets=[{"path": str(asset_path)}],
                    fragment_merge_review_enabled=False,
                    write_page_renders=False,
                )
            )
            self.assertFalse(
                EXTRACT_DOCUMENT.can_reuse_extracted_page(
                    previous_page=previous_page,
                    page_fingerprint_matches_previous=False,
                    previous_page_assets=[{"path": str(asset_path)}],
                    fragment_merge_review_enabled=False,
                    write_page_renders=False,
                )
            )

            self.assertFalse(
                EXTRACT_DOCUMENT.can_reuse_extracted_page(
                    previous_page=previous_page,
                    page_fingerprint_matches_previous=True,
                    previous_page_assets=[{"path": str(asset_path)}],
                    fragment_merge_review_enabled=True,
                    write_page_renders=False,
                )
            )

    def test_main_writes_page_render_for_prose_only_page_when_enabled(self) -> None:
        class DummyStage:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def set(self, **kwargs) -> None:
                return None

        class DummyProfiler:
            def stage(self, *args, **kwargs):
                return DummyStage()

            def set_counter(self, *args, **kwargs) -> None:
                return None

            def increment_counter(self, *args, **kwargs) -> None:
                return None

            def finish(self, *args, **kwargs) -> None:
                return None

        class DummyDoc:
            def __init__(self, pages):
                self._pages = pages
                self.page_count = len(pages)

            def __getitem__(self, index):
                return self._pages[index]

            def close(self) -> None:
                return None

        with tempfile.TemporaryDirectory() as tmp_raw:
            workspace = Path(tmp_raw)
            input_pdf = workspace / "input.pdf"
            input_pdf.write_bytes(b"%PDF-1.4\n")
            output_dir = workspace / "output"
            image = mock.Mock()
            image.save.side_effect = (
                lambda path, format="PNG": Path(path).write_bytes(b"png-bytes")
            )
            page = types.SimpleNamespace(rect=EXTRACT_DOCUMENT.fitz.Rect(0, 0, 612, 792))
            region = types.SimpleNamespace(
                text="Body copy",
                font_size_hint=12.0,
                source="native",
            )
            merged_block = {
                "rect": EXTRACT_DOCUMENT.fitz.Rect(10, 20, 110, 40),
                "source": "native",
                "align": "left",
                "regions": [region],
            }
            args = types.SimpleNamespace(
                input_pdf=str(input_pdf),
                output_dir=str(output_dir),
                pages=None,
                magnify_factor=2.0,
                dpi=144,
                font_baseline=None,
                translation_provider=None,
                fragment_merge_requests_json=None,
                fragment_merge_responses_json=None,
                profiler=False,
                profiler_commands=None,
                profiler_output_dir=None,
                write_page_renders=True,
            )

            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(EXTRACT_DOCUMENT, "parse_args", return_value=args))
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "create_profiler", return_value=DummyProfiler())
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "resolve_profile_path", return_value=None)
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT.fitz, "open", return_value=DummyDoc([page]))
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "sha256_file", return_value="doc-hash")
                )
                stack.enter_context(
                    mock.patch.object(
                        EXTRACT_DOCUMENT,
                        "resolve_page_source_fingerprint",
                        return_value=("pdfnative:fp-1", False),
                    )
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "classify_page", return_value=("native", "native"))
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "extract_native_regions", return_value=[region])
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "merge_regions", return_value=[merged_block])
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "block_text_from_regions", return_value="Body copy")
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "export_page_assets", return_value=[])
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "should_skip_ruled_table_detection", return_value=True)
                )
                stack.enter_context(
                    mock.patch.object(
                        EXTRACT_DOCUMENT,
                        "attach_leading_bullets",
                        side_effect=lambda blocks: blocks,
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        EXTRACT_DOCUMENT,
                        "merge_inline_row_fragments",
                        side_effect=lambda blocks: blocks,
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        EXTRACT_DOCUMENT,
                        "merge_paragraph_fragments",
                        side_effect=lambda blocks, pairs: blocks,
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        EXTRACT_DOCUMENT,
                        "dedupe_ocr_blocks",
                        side_effect=lambda blocks: blocks,
                    )
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "mark_textual_table_like_rows", return_value=None)
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "build_textual_tables", return_value=[])
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "mark_margin_artifacts", return_value=None)
                )
                stack.enter_context(
                    mock.patch.object(
                        EXTRACT_DOCUMENT,
                        "mark_list_items_from_marker_artifacts",
                        return_value=None,
                    )
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "mark_two_column_rows", return_value=None)
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "finalize_block_layout", return_value=None)
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "stamp_block_fingerprints", return_value=None)
                )
                stack.enter_context(
                    mock.patch.object(
                        EXTRACT_DOCUMENT,
                        "mark_repeated_headers_and_footers",
                        return_value=None,
                    )
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "font_baseline_from_payload", return_value={})
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "update_run_manifest", return_value=None)
                )
                stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "line_payload", return_value={})
                )
                page_image_fast = stack.enter_context(
                    mock.patch.object(EXTRACT_DOCUMENT, "page_image_fast", return_value=image)
                )
                result = EXTRACT_DOCUMENT.main()

            self.assertEqual(result, 0)
            render_path = output_dir / "page-renders" / "page-001.png"
            self.assertTrue(render_path.exists())
            self.assertEqual(page_image_fast.call_count, 1)
            payload = json.loads((output_dir / "blocks.json").read_text())
            self.assertEqual(
                Path(payload["pages"][0]["render_path"]).resolve(),
                render_path.resolve(),
            )

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
        self.assertEqual(requests[0]["kind"], "fragment_merge_batch")
        self.assertEqual(requests[0]["runtime_mode"], "claude")
        self.assertEqual(requests[0]["pair_ids"], ["p1-b1->p1-b2"])
        self.assertEqual(requests[0]["page_numbers"], [1])

    def test_build_fragment_merge_requests_batches_across_pages(self) -> None:
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
            },
            {
                "pair_id": "p2-b4->p2-b5",
                "page_number": 2,
                "previous_role": "paragraph",
                "current_role": "paragraph",
                "vertical_gap": 5.0,
                "previous_text": "Second",
                "current_text": "fragment",
                "cache_key": "cache-2",
            },
            {
                "pair_id": "p3-b7->p3-b8",
                "page_number": 3,
                "previous_role": "heading",
                "current_role": "heading",
                "vertical_gap": 3.0,
                "previous_text": "Third",
                "current_text": "page",
                "cache_key": "cache-3",
            },
        ]

        with mock.patch.object(
            EXTRACT_DOCUMENT,
            "fragment_merge_request_max_pairs",
            return_value=2,
        ):
            requests = EXTRACT_DOCUMENT.build_fragment_merge_requests(
                candidates,
                cwd=Path("/tmp/work"),
                provider="claude",
            )

        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["pair_ids"], ["p1-b1->p1-b2", "p2-b4->p2-b5"])
        self.assertEqual(requests[0]["page_numbers"], [1, 2])
        self.assertEqual(requests[1]["pair_ids"], ["p3-b7->p3-b8"])
        self.assertEqual(requests[1]["page_numbers"], [3])

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

    def test_merge_paragraph_fragments_merges_centered_native_heading_stack(self) -> None:
        page_blocks = [
            {
                "id": "p1-b1",
                "page_number": 1,
                "source": "native",
                "role": "heading",
                "align": "center",
                "bbox": [115.2, 63.96, 500.75, 81.56],
                "text": "AVENANT AU CONTRAT ACCORD CADRE RELATIF AU PROGRAMME",
                "style": {"bold": True},
                "_font_size_hints": [12.5],
                "_native_lines": [],
                "table": None,
            },
            {
                "id": "p1-b2",
                "page_number": 1,
                "source": "native",
                "role": "heading",
                "align": "center",
                "bbox": [269.64, 78.36, 357.34, 94.16],
                "text": "SAMA MONEY",
                "style": {"bold": True},
                "_font_size_hints": [11.5],
                "_native_lines": [],
                "table": None,
            },
        ]

        merged = EXTRACT_DOCUMENT.merge_paragraph_fragments(page_blocks)

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["role"], "heading")
        self.assertIn("SAMA MONEY", merged[0]["text"])

    def test_merge_paragraph_fragments_merges_short_native_continuation_line(self) -> None:
        page_blocks = [
            {
                "id": "p1-b8",
                "page_number": 1,
                "source": "native",
                "role": "paragraph",
                "align": "left",
                "bbox": [83.52, 390.84, 531.27, 410.45],
                "text": "Les parties ont conclu le 20 juin 2024 un contrat de Bin sponsorship (co-branding) de carte",
                "style": {"bold": False},
                "_font_size_hints": [10.5],
                "_native_lines": [],
                "table": None,
            },
            {
                "id": "p1-b9",
                "page_number": 1,
                "source": "native",
                "role": "paragraph",
                "align": "left",
                "bbox": [83.16, 403.8, 353.71, 422.84],
                "text": "prépayée relatif au programme ( VISA SAMA MONEY ).",
                "style": {"bold": False},
                "_font_size_hints": [11.0],
                "_native_lines": [],
                "table": None,
            },
        ]

        merged = EXTRACT_DOCUMENT.merge_paragraph_fragments(page_blocks)

        self.assertEqual(len(merged), 1)
        self.assertIn("prépayée", merged[0]["text"])

    def test_merge_paragraph_fragments_merges_native_short_heading_like_tail(self) -> None:
        page_blocks = [
            {
                "id": "p2-b20",
                "page_number": 2,
                "source": "native",
                "role": "paragraph",
                "align": "left",
                "bbox": [83.52, 574.97, 530.43, 591.53],
                "text": "Rapports de performance. Documenter et rapporter les performances des ventes afin d'évaluer",
                "style": {"bold": False},
                "_font_size_hints": [10.5],
                "_native_lines": [],
                "table": None,
            },
            {
                "id": "p2-b21",
                "page_number": 2,
                "source": "native",
                "role": "heading",
                "align": "left",
                "bbox": [84.24, 589.19, 334.1, 603.83],
                "text": "l'impact des initiatives de co-branding sur ses activités.",
                "style": {"bold": False},
                "_font_size_hints": [10.5],
                "_native_lines": [],
                "table": None,
            },
        ]

        merged = EXTRACT_DOCUMENT.merge_paragraph_fragments(page_blocks)

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["role"], "paragraph")
        self.assertIn("co-branding", merged[0]["text"])

if __name__ == "__main__":
    unittest.main()
