from __future__ import annotations

import importlib.util
import json
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


def make_build_final_pdf_stubs() -> dict[str, types.ModuleType]:
    class DummySpan:
        def set(self, **kwargs):
            return None

    class DummyProfiler:
        def stage(self, *args, **kwargs):
            class _Ctx:
                def __enter__(self_inner):
                    return DummySpan()

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

        def set_counter(self, *args, **kwargs):
            return None

        def increment_counter(self, *args, **kwargs):
            return None

        def finish(self, *args, **kwargs):
            return None

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
    fake_profiling = types.ModuleType("profiling")
    fake_profiling.create_profiler = lambda *args, **kwargs: DummyProfiler()
    fake_profiling.resolve_profile_path = lambda *args, **kwargs: None
    return {
        "fitz": fake_fitz,
        "core": fake_core,
        "block_overrides": fake_block_overrides,
        "profiling": fake_profiling,
    }


BUILD_FINAL_PDF = load_module(
    "test_build_final_pdf",
    SCRIPT_DIR / "build_final_pdf.py",
    stub_modules=make_build_final_pdf_stubs(),
)


class StructuredRebuildTests(unittest.TestCase):
    def test_choose_page_mode_prefers_structured_rebuild_for_tables(self) -> None:
        page = {
            "page_type": "digital",
            "tables": [{"id": "p1-table-1"}],
            "asset_ids": [],
        }

        mode = BUILD_FINAL_PDF.choose_page_mode(page, {})

        self.assertEqual(mode, "structured_rebuild")

    def test_choose_page_mode_prefers_structured_rebuild_for_signature_assets(self) -> None:
        page = {
            "page_type": "digital",
            "tables": [],
            "asset_ids": ["p1-sig1"],
        }
        assets_by_id = {"p1-sig1": {"id": "p1-sig1", "kind": "signature_crop"}}

        mode = BUILD_FINAL_PDF.choose_page_mode(page, assets_by_id)

        self.assertEqual(mode, "structured_rebuild")

    def test_main_calls_render_hybrid_document_without_engine_toggle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            workspace = Path(tmp_raw)
            source_pdf = workspace / "input.pdf"
            source_pdf.write_bytes(b"%PDF-1.4\n")
            translated_json = workspace / "translated.json"
            translated_json.write_text(json.dumps({"pages": [], "blocks": []}))
            output_pdf = workspace / "out.pdf"

            with mock.patch.object(BUILD_FINAL_PDF, "render_hybrid_document", return_value=output_pdf) as render_hybrid_document:
                argv = [
                    "build_final_pdf.py",
                    str(source_pdf),
                    str(translated_json),
                    "--output-pdf",
                    str(output_pdf),
                ]
                with mock.patch.object(sys, "argv", argv):
                    result = BUILD_FINAL_PDF.main()

        self.assertEqual(result, 0)
        self.assertEqual(render_hybrid_document.call_args.args, (source_pdf.resolve(), {"pages": [], "blocks": []}, output_pdf.resolve()))
        self.assertIn("profiler", render_hybrid_document.call_args.kwargs)

    def test_filtered_payload_for_pages_renumbers_multi_page_chunk(self) -> None:
        payload = {
            "input_pdf": "/tmp/source.pdf",
            "font_baseline": {"family_class": "serif"},
            "translation_mode": "desktop",
            "pages": [
                {
                    "page_number": 2,
                    "asset_ids": ["p2-logo"],
                    "tables": [],
                },
                {
                    "page_number": 3,
                    "asset_ids": [],
                    "tables": [
                        {
                            "id": "p3-table-1",
                            "cells": [
                                {
                                    "id": "p3-r0-c0",
                                    "signature_asset_ids": ["p3-sig1"],
                                }
                            ],
                        }
                    ],
                },
            ],
            "blocks": [
                {"id": "p2-b1", "page_number": 2, "bbox": [0, 0, 10, 10], "text": "Page 2"},
                {
                    "id": "p3-b1",
                    "page_number": 3,
                    "bbox": [0, 0, 10, 10],
                    "text": "Page 3",
                    "table": {"cell_id": "p3-r0-c0"},
                },
            ],
            "assets": [
                {"id": "p2-logo", "page_number": 2, "kind": "logo"},
                {"id": "p3-sig1", "page_number": 3, "kind": "signature_crop"},
            ],
        }

        filtered = BUILD_FINAL_PDF.filtered_payload_for_pages(
            payload,
            [2, 3],
            BUILD_FINAL_PDF.asset_map(payload),
        )

        self.assertEqual(filtered["page_count"], 2)
        self.assertEqual([page["page_number"] for page in filtered["pages"]], [1, 2])
        self.assertEqual(filtered["pages"][1]["asset_ids"], ["p3-sig1"])
        self.assertEqual([block["page_number"] for block in filtered["blocks"]], [1, 2])
        self.assertEqual(
            [(asset["id"], asset["page_number"]) for asset in filtered["assets"]],
            [("p2-logo", 1), ("p3-sig1", 2)],
        )

    def test_contiguous_rebuild_chunks_groups_adjacent_rebuild_pages(self) -> None:
        pages = [
            {"page_number": 1, "page_type": "digital", "tables": [], "asset_ids": []},
            {"page_number": 2, "page_type": "digital", "tables": [{"id": "p2-table"}], "asset_ids": []},
            {"page_number": 3, "page_type": "digital", "tables": [], "asset_ids": ["p3-sig1"]},
            {"page_number": 4, "page_type": "digital", "tables": [], "asset_ids": []},
            {"page_number": 5, "page_type": "digital", "tables": [{"id": "p5-table"}], "asset_ids": []},
        ]
        assets_by_id = {"p3-sig1": {"id": "p3-sig1", "kind": "signature_crop"}}

        chunks = BUILD_FINAL_PDF.contiguous_rebuild_chunks(pages, assets_by_id)

        self.assertEqual(chunks, [[2, 3], [5]])

    def test_page_render_fingerprint_changes_with_translated_text(self) -> None:
        page = {
            "page_number": 1,
            "page_type": "digital",
            "region_source": "native",
            "strategy_hint": "overlay",
            "source_fingerprint": "src-1",
            "asset_ids": [],
            "tables": [],
        }
        base_block = {
            "id": "p1-b1",
            "role": "paragraph",
            "align": "left",
            "bbox": [0, 0, 10, 10],
            "text": "Bonjour",
            "translated_text": "Hello",
            "style": {"font_size_hint": 10.0},
        }
        changed_block = dict(base_block)
        changed_block["translated_text"] = "Greetings"

        left = BUILD_FINAL_PDF.page_render_fingerprint(
            page,
            [base_block],
            {},
            {"family_class": "serif"},
            {},
        )
        right = BUILD_FINAL_PDF.page_render_fingerprint(
            page,
            [changed_block],
            {},
            {"family_class": "serif"},
            {},
        )

        self.assertNotEqual(left, right)


if __name__ == "__main__":
    unittest.main()
