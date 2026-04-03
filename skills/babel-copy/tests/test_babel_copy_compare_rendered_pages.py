from __future__ import annotations

import importlib.util
import sys
import types
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
    sys.modules.pop("PIL", None)
    sys.modules.pop("PIL.Image", None)
    sys.modules.pop("PIL.ImageChops", None)
    sys.modules.pop("PIL.ImageOps", None)
    sys.modules.pop("PIL.ImageStat", None)
    fake_pil = types.ModuleType("PIL")
    fake_fitz = types.ModuleType("fitz")
    fake_image = types.ModuleType("PIL.Image")
    fake_imagechops = types.ModuleType("PIL.ImageChops")
    fake_imageops = types.ModuleType("PIL.ImageOps")
    fake_imagestat = types.ModuleType("PIL.ImageStat")
    fake_pil.Image = fake_image
    fake_pil.ImageChops = fake_imagechops
    fake_pil.ImageOps = fake_imageops
    fake_pil.ImageStat = fake_imagestat
    sys.modules["PIL"] = fake_pil
    sys.modules["fitz"] = fake_fitz
    sys.modules["PIL.Image"] = fake_image
    sys.modules["PIL.ImageChops"] = fake_imagechops
    sys.modules["PIL.ImageOps"] = fake_imageops
    sys.modules["PIL.ImageStat"] = fake_imagestat
    spec.loader.exec_module(module)
    return module


COMPARE_RENDERED_PAGES = load_module(
    "test_compare_rendered_pages", SCRIPT_DIR / "compare_rendered_pages.py"
)


class CompareRenderedPagesTests(unittest.TestCase):
    def test_resolve_pages_to_render_uses_all_pages_for_small_documents(self) -> None:
        pages, policy = COMPARE_RENDERED_PAGES.resolve_pages_to_render(
            5,
            sample_policy="auto",
            explicit_pages=[],
            manifest=None,
            translated_payload=None,
        )

        self.assertEqual(policy, "all")
        self.assertEqual(pages, [1, 2, 3, 4, 5])

    def test_resolve_pages_to_render_uses_tiered_sampling_for_large_documents(self) -> None:
        manifest = {
            "page_batches": [
                {"page_numbers": [1, 2, 3]},
                {"page_numbers": [4, 5, 6]},
                {"page_numbers": [7, 8, 9, 10]},
            ]
        }
        translated_payload = {
            "pages": [
                {"page_number": 6, "asset_ids": ["sig-1"], "tables": []},
                {"page_number": 8, "asset_ids": [], "tables": [{"id": "table-1"}]},
            ],
            "blocks": [
                {"page_number": 9, "custom_override": {"bbox": {"x": "+2"}}}
            ],
            "assets": [{"id": "sig-1", "kind": "signature_crop"}],
        }

        pages, policy = COMPARE_RENDERED_PAGES.resolve_pages_to_render(
            30,
            sample_policy="auto",
            explicit_pages=[],
            manifest=manifest,
            translated_payload=translated_payload,
        )

        self.assertEqual(policy, "tiered")
        self.assertEqual(pages, [1, 3, 4, 6, 7, 8, 9, 10, 30])


if __name__ == "__main__":
    unittest.main()
