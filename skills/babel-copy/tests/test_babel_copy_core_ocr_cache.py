from __future__ import annotations

import importlib.util
import sys
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


def make_core_stubs() -> dict[str, types.ModuleType]:
    fake_fitz = types.ModuleType("fitz")

    class DummyRect:
        def __init__(self, bbox):
            self.x0, self.y0, self.x1, self.y1 = bbox
            self.height = self.y1 - self.y0

    fake_fitz.Rect = DummyRect

    fake_pytesseract = types.ModuleType("pytesseract")

    fake_pil = types.ModuleType("PIL")
    fake_pil.Image = types.SimpleNamespace(Image=object)
    fake_pil.ImageOps = types.SimpleNamespace(
        autocontrast=lambda image: image,
        grayscale=lambda image: image,
    )

    return {
        "fitz": fake_fitz,
        "pytesseract": fake_pytesseract,
        "PIL": fake_pil,
    }


CORE = load_module(
    "test_babel_copy_core",
    SCRIPT_DIR / "core.py",
    stub_modules=make_core_stubs(),
)


class CoreOcrCacheTests(unittest.TestCase):
    def test_extract_ocr_regions_uses_supplied_ocr_render(self) -> None:
        supplied_image = object()
        page = types.SimpleNamespace(rect=object())

        with mock.patch.object(CORE, "ocr_page_image", side_effect=AssertionError("unexpected rerender")):
            with mock.patch.object(
                CORE,
                "ocr_image_to_lines",
                return_value=[{"text": "Hello", "bbox_px": [0.0, 0.0, 20.0, 10.0]}],
            ):
                with mock.patch.object(CORE, "infer_alignment", return_value="left"):
                    regions = CORE.extract_ocr_regions(
                        page,
                        2.0,
                        ocr_image=supplied_image,
                        ocr_scale=2.0,
                    )

        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0].text, "Hello")
        self.assertEqual(regions[0].bbox, (0.0, 0.0, 10.0, 5.0))

    def test_extract_ocr_regions_requires_image_and_scale_together(self) -> None:
        with self.assertRaises(ValueError):
            CORE.extract_ocr_regions(object(), 2.0, ocr_image=object())


if __name__ == "__main__":
    unittest.main()
