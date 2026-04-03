from __future__ import annotations

import importlib.util
import sys
import tempfile
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


def make_rebuild_typst_stubs() -> dict[str, types.ModuleType]:
    fake_core = types.ModuleType("core")
    fake_core.DEFAULT_FONT_BASELINE_CLASS = "serif"
    fake_core.normalize_font_family_class = lambda value: value
    fake_core.font_baseline_from_payload = lambda payload: payload.get("font_baseline", {})
    fake_block_overrides = types.ModuleType("block_overrides")
    fake_block_overrides.apply_custom_overrides_to_payload = lambda payload: payload
    return {
        "core": fake_core,
        "block_overrides": fake_block_overrides,
    }


REBUILD_TYPST = load_module(
    "test_rebuild_typst",
    SCRIPT_DIR / "rebuild_typst.py",
    stub_modules=make_rebuild_typst_stubs(),
)


class RebuildTypstBatchingTests(unittest.TestCase):
    def test_build_typst_source_emits_all_pages(self) -> None:
        payload = {
            "font_baseline": {"family_class": "serif"},
            "pages": [
                {"page_number": 1, "width": 595.08, "height": 841.68, "tables": []},
                {"page_number": 2, "width": 612.0, "height": 792.0, "tables": []},
            ],
            "blocks": [
                {
                    "id": "p1-b1",
                    "page_number": 1,
                    "bbox": [0, 0, 10, 10],
                    "text": "Bonjour",
                    "translated_text": "Hello",
                    "role": "paragraph",
                    "align": "left",
                    "style": {"font_size_hint": 10.0},
                },
                {
                    "id": "p2-b1",
                    "page_number": 2,
                    "bbox": [0, 0, 10, 10],
                    "text": "Monde",
                    "translated_text": "World",
                    "role": "paragraph",
                    "align": "left",
                    "style": {"font_size_hint": 10.0},
                },
            ],
            "assets": [],
        }

        with tempfile.TemporaryDirectory() as tmp_raw:
            assets_dir = Path(tmp_raw) / "assets"
            source = REBUILD_TYPST.build_typst_source(payload, assets_dir=assets_dir)

        self.assertIn('"Hello"', source)
        self.assertIn('"World"', source)
        self.assertEqual(source.count("#set page("), 2)
        self.assertEqual(source.count("#pagebreak()"), 1)


if __name__ == "__main__":
    unittest.main()
