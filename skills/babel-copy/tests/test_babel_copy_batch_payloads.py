from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


BATCH_PAYLOADS = load_module(
    "test_batch_payloads", SCRIPT_DIR / "batch_payloads.py"
)


def sample_payload() -> dict:
    return {
        "input_pdf": "/tmp/source.pdf",
        "page_count": 3,
        "block_count": 3,
        "font_baseline": {"family_class": "serif"},
        "pages": [
            {
                "page_number": 1,
                "asset_ids": ["p1-a1"],
                "tables": [],
            },
            {
                "page_number": 2,
                "asset_ids": ["p2-a1"],
                "tables": [
                    {
                        "id": "p2-table-1",
                        "cells": [
                            {
                                "id": "p2-cell-1",
                                "signature_asset_ids": ["p2-sig1"],
                            }
                        ],
                    }
                ],
            },
            {
                "page_number": 3,
                "asset_ids": [],
                "tables": [],
            },
        ],
        "blocks": [
            {"id": "p1-b1", "page_number": 1, "bbox": [0, 0, 10, 10], "text": "A"},
            {
                "id": "p2-b1",
                "page_number": 2,
                "bbox": [0, 5, 10, 15],
                "text": "B",
                "table": {"cell_id": "p2-cell-1"},
            },
            {"id": "p3-b1", "page_number": 3, "bbox": [0, 10, 10, 20], "text": "C"},
        ],
        "assets": [
            {"id": "p1-a1", "page_number": 1, "kind": "image"},
            {"id": "p2-a1", "page_number": 2, "kind": "image"},
            {"id": "p2-sig1", "page_number": 2, "kind": "signature_crop"},
        ],
    }


class BatchPayloadTests(unittest.TestCase):
    def test_slice_payload_for_pages_filters_pages_blocks_and_assets(self) -> None:
        sliced = BATCH_PAYLOADS.slice_payload_for_pages(sample_payload(), [2, 3])

        self.assertEqual([page["page_number"] for page in sliced["pages"]], [2, 3])
        self.assertEqual([block["id"] for block in sliced["blocks"]], ["p2-b1", "p3-b1"])
        self.assertEqual(
            sorted(asset["id"] for asset in sliced["assets"]),
            ["p2-a1", "p2-sig1"],
        )

    def test_slice_payload_for_pages_can_renumber_without_rewriting_ids(self) -> None:
        sliced = BATCH_PAYLOADS.slice_payload_for_pages(
            sample_payload(), [2, 3], renumber_pages=True
        )

        self.assertEqual([page["page_number"] for page in sliced["pages"]], [1, 2])
        self.assertEqual([block["page_number"] for block in sliced["blocks"]], [1, 2])
        self.assertEqual([block["id"] for block in sliced["blocks"]], ["p2-b1", "p3-b1"])

    def test_build_page_batch_specs_auto_splits_large_documents(self) -> None:
        payload = sample_payload()
        payload["page_count"] = 25
        payload["pages"] = [
            {"page_number": page_number, "asset_ids": [], "tables": []}
            for page_number in range(1, 26)
        ]
        payload["blocks"] = [
            {
                "id": f"p{page_number}-b1",
                "page_number": page_number,
                "bbox": [0, 0, 1, 1],
                "text": str(page_number),
            }
            for page_number in range(1, 26)
        ]
        payload["block_count"] = len(payload["blocks"])

        specs = BATCH_PAYLOADS.build_page_batch_specs(payload, page_batch_size=10)

        self.assertEqual([spec["page_count"] for spec in specs], [10, 10, 5])
        self.assertTrue(all(spec["is_multi_page_batching"] for spec in specs))
        self.assertEqual(specs[0]["batch_id"], "batch-001-p001-010")

    def test_build_page_batch_specs_respects_payload_size_trigger(self) -> None:
        payload = sample_payload()
        payload["blocks"] = [
            {
                "id": "p1-b1",
                "page_number": 1,
                "bbox": [0, 0, 10, 10],
                "text": "x" * 5000,
            },
            {
                "id": "p2-b1",
                "page_number": 2,
                "bbox": [0, 0, 10, 10],
                "text": "y" * 5000,
            },
            {
                "id": "p3-b1",
                "page_number": 3,
                "bbox": [0, 0, 10, 10],
                "text": "z" * 5000,
            },
        ]

        specs = BATCH_PAYLOADS.build_page_batch_specs(
            payload,
            page_batch_size=2,
            threshold_pages=20,
            threshold_bytes=100,
        )

        self.assertEqual([spec["page_count"] for spec in specs], [2, 1])

    def test_stitch_payloads_restores_original_page_order(self) -> None:
        payload = sample_payload()
        first = BATCH_PAYLOADS.slice_payload_for_pages(payload, [1, 2])
        second = BATCH_PAYLOADS.slice_payload_for_pages(payload, [3])

        stitched = BATCH_PAYLOADS.stitch_payloads(
            [second, first], expected_page_numbers=[1, 2, 3]
        )

        self.assertEqual([page["page_number"] for page in stitched["pages"]], [1, 2, 3])
        self.assertEqual(
            [block["id"] for block in stitched["blocks"]],
            ["p1-b1", "p2-b1", "p3-b1"],
        )

    def test_stitch_payloads_rejects_duplicate_page_coverage(self) -> None:
        payload = sample_payload()
        first = BATCH_PAYLOADS.slice_payload_for_pages(payload, [1, 2])
        duplicate = BATCH_PAYLOADS.slice_payload_for_pages(payload, [2, 3])

        with self.assertRaisesRegex(ValueError, "Invalid page cover"):
            BATCH_PAYLOADS.stitch_payloads(
                [first, duplicate], expected_page_numbers=[1, 2, 3]
            )


if __name__ == "__main__":
    unittest.main()
