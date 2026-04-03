from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


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
        "ocr_image_to_lines",
        "ocr_page_image",
        "page_image_fast",
        "parse_page_selection",
        "split_leading_marker",
    ]
    for name in passthrough_names:
        setattr(fake_core, name, lambda *args, **kwargs: None)
    fake_core.clean_text = lambda text: " ".join(str(text).split())
    fake_core.parse_page_selection = lambda pages, count: set(range(1, count + 1))
    fake_core.split_leading_marker = lambda text: ("", text)

    fake_fitz = types.ModuleType("fitz")

    class DummyPoint:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class DummyRect:
        def __init__(self, *args):
            if len(args) == 1:
                values = args[0]
            else:
                values = args
            self.x0, self.y0, self.x1, self.y1 = [float(value) for value in values]

        @property
        def height(self):
            return self.y1 - self.y0

        @property
        def is_empty(self):
            return self.x1 <= self.x0 or self.y1 <= self.y0

        def get_area(self):
            if self.is_empty:
                return 0.0
            return (self.x1 - self.x0) * (self.y1 - self.y0)

        def contains(self, point):
            return self.x0 <= point.x <= self.x1 and self.y0 <= point.y <= self.y1

        def __and__(self, other):
            return DummyRect(
                max(self.x0, other.x0),
                max(self.y0, other.y0),
                min(self.x1, other.x1),
                min(self.y1, other.y1),
            )

    fake_fitz.Rect = DummyRect
    fake_fitz.Point = DummyPoint

    fake_translation_runtime = types.ModuleType("translation_runtime")
    fake_translation_runtime.TRANSLATION_PROVIDER_CHOICES = ("auto", "codex", "claude")
    fake_translation_runtime.detect_runtime_mode = lambda provider=None: "codex"
    fake_translation_runtime.translation_provider = lambda provider=None: "codex"

    fake_profiling = types.ModuleType("profiling")
    fake_profiling.create_profiler = lambda *args, **kwargs: None
    fake_profiling.resolve_profile_path = lambda *args, **kwargs: None

    return {
        "core": fake_core,
        "fitz": fake_fitz,
        "profiling": fake_profiling,
        "translation_runtime": fake_translation_runtime,
    }


EXTRACT_DOCUMENT = load_module(
    "test_extract_document_table_cell_ocr",
    SCRIPT_DIR / "extract_document.py",
    stub_modules=make_extract_document_stubs(),
)


class TableCellOcrTests(unittest.TestCase):
    def test_assign_blocks_to_tables_uses_page_band_index_without_cross_cell_leakage(
        self,
    ) -> None:
        page_blocks = [
            {"id": "p1-b1", "bbox": [10.0, 10.0, 40.0, 20.0], "role": "body", "table": None},
            {"id": "p1-b2", "bbox": [110.0, 10.0, 140.0, 20.0], "role": "body", "table": None},
            {"id": "p1-b3", "bbox": [210.0, 10.0, 240.0, 20.0], "role": "body", "table": None},
        ]
        tables = [
            {
                "id": "p1-table-1",
                "cells": [
                    {
                        "id": "p1-r0-c0",
                        "row_index": 0,
                        "col_index": 0,
                        "bbox": [0.0, 0.0, 100.0, 40.0],
                        "block_ids": [],
                    },
                    {
                        "id": "p1-r0-c1",
                        "row_index": 0,
                        "col_index": 1,
                        "bbox": [100.0, 0.0, 200.0, 40.0],
                        "block_ids": [],
                    },
                ],
            }
        ]

        EXTRACT_DOCUMENT.assign_blocks_to_tables(page_blocks, tables)

        self.assertEqual(tables[0]["cells"][0]["block_ids"], ["p1-b1"])
        self.assertEqual(tables[0]["cells"][1]["block_ids"], ["p1-b2"])
        self.assertIsNone(page_blocks[2]["table"])
        self.assertEqual(page_blocks[0]["role"], "table_cell")
        self.assertEqual(page_blocks[1]["role"], "table_cell")

    def test_fill_empty_cells_with_page_ocr_lines(self) -> None:
        tables = [
            {
                "id": "p1-table-1",
                "cells": [
                    {
                        "id": "p1-r0-c0",
                        "row_index": 0,
                        "col_index": 0,
                        "bbox": [0.0, 0.0, 100.0, 40.0],
                        "block_ids": [],
                    },
                    {
                        "id": "p1-r0-c1",
                        "row_index": 0,
                        "col_index": 1,
                        "bbox": [100.0, 0.0, 200.0, 40.0],
                        "block_ids": [],
                    },
                ],
            }
        ]
        page_blocks: list[dict] = []
        ocr_lines = [
            {"text": "Name: Jane Doe", "bbox": [10.0, 8.0, 90.0, 18.0]},
            {"text": "Title: CEO", "bbox": [110.0, 8.0, 190.0, 18.0]},
        ]

        EXTRACT_DOCUMENT.fill_empty_cells_with_ocr(
            page_number=1,
            tables=tables,
            page_blocks=page_blocks,
            ocr_lines=ocr_lines,
        )

        self.assertEqual(len(page_blocks), 2)
        self.assertEqual([block["text"] for block in page_blocks], ["Name: Jane Doe", "Title: CEO"])
        self.assertEqual(tables[0]["cells"][0]["block_ids"], ["p1-b1"])
        self.assertEqual(tables[0]["cells"][1]["block_ids"], ["p1-b2"])

    def test_enrich_tall_cells_with_page_ocr_lines(self) -> None:
        tables = [
            {
                "id": "p1-table-1",
                "cells": [
                    {
                        "id": "p1-r0-c0",
                        "row_index": 0,
                        "col_index": 0,
                        "bbox": [0.0, 0.0, 120.0, 100.0],
                        "block_ids": ["p1-b1"],
                    }
                ],
            }
        ]
        page_blocks = [
            {
                "id": "p1-b1",
                "bbox": [0.0, 0.0, 120.0, 100.0],
                "text": "Name",
            }
        ]
        ocr_lines = [
            {"text": "Name: Jane Doe", "bbox": [8.0, 8.0, 90.0, 18.0]},
            {"text": "Lower noise", "bbox": [8.0, 70.0, 90.0, 82.0]},
        ]

        EXTRACT_DOCUMENT.enrich_tall_cells_with_ocr(
            tables=tables,
            page_blocks=page_blocks,
            ocr_lines=ocr_lines,
        )

        self.assertEqual(page_blocks[0]["text"], "Name: Jane Doe")

    def test_populate_table_cell_texts_uses_block_id_lookup(self) -> None:
        tables = [
            {
                "id": "p1-table-1",
                "cells": [
                    {
                        "id": "p1-r0-c0",
                        "row_index": 0,
                        "col_index": 0,
                        "bbox": [0.0, 0.0, 120.0, 60.0],
                        "block_ids": ["p1-b2", "missing", "p1-b1"],
                        "text": "",
                    }
                ],
            }
        ]
        page_blocks = [
            {"id": "p1-b1", "bbox": [0.0, 10.0, 120.0, 20.0], "text": "First"},
            {"id": "p1-b2", "bbox": [0.0, 4.0, 120.0, 9.0], "text": "Header"},
        ]

        EXTRACT_DOCUMENT.populate_table_cell_texts(tables, page_blocks)

        self.assertEqual(tables[0]["cells"][0]["text"], "Header\nFirst")


if __name__ == "__main__":
    unittest.main()
