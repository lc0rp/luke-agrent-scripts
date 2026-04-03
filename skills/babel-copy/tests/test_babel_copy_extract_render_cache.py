from __future__ import annotations

import importlib.util
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

    fake_profiling = types.ModuleType("profiling")
    fake_profiling.create_profiler = lambda *args, **kwargs: None
    fake_profiling.resolve_profile_path = lambda *args, **kwargs: None

    fake_translation_runtime = types.ModuleType("translation_runtime")
    fake_translation_runtime.TRANSLATION_PROVIDER_CHOICES = ("auto", "codex", "claude")
    fake_translation_runtime.detect_runtime_mode = lambda provider=None: "codex"
    fake_translation_runtime.translation_provider = lambda provider=None: "codex"

    return {
        "core": fake_core,
        "fitz": fake_fitz,
        "numpy": fake_numpy,
        "PIL": fake_pil,
        "PIL.Image": fake_pil_image,
        "profiling": fake_profiling,
        "translation_runtime": fake_translation_runtime,
    }


EXTRACT_DOCUMENT = load_module(
    "test_extract_document_render_cache",
    SCRIPT_DIR / "extract_document.py",
    stub_modules=make_extract_document_stubs(),
)


class ExtractDocumentRenderCacheTests(unittest.TestCase):
    def test_page_render_cache_renders_layout_once(self) -> None:
        page = object()
        image = mock.Mock()
        cache = EXTRACT_DOCUMENT.PageRenderCache(page, dpi=144)

        with mock.patch.object(EXTRACT_DOCUMENT, "page_image_fast", return_value=image) as page_image_fast:
            first = cache.layout_image()
            second = cache.layout_image()

        self.assertIs(first, image)
        self.assertIs(second, image)
        page_image_fast.assert_called_once_with(page, dpi=144)

    def test_page_render_cache_only_writes_when_path_is_configured(self) -> None:
        image = mock.Mock()
        cache = EXTRACT_DOCUMENT.PageRenderCache(object(), dpi=144, render_path=None)

        with mock.patch.object(EXTRACT_DOCUMENT, "page_image_fast", return_value=image) as page_image_fast:
            written = cache.write_layout_render()

        self.assertIsNone(written)
        page_image_fast.assert_not_called()
        image.save.assert_not_called()

    def test_page_render_cache_writes_png_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_raw:
            render_path = Path(tmp_raw) / "page-renders" / "page-001.png"
            image = mock.Mock()
            cache = EXTRACT_DOCUMENT.PageRenderCache(object(), dpi=144, render_path=render_path)

            with mock.patch.object(EXTRACT_DOCUMENT, "page_image_fast", return_value=image) as page_image_fast:
                first = cache.write_layout_render()
                second = cache.write_layout_render()

        self.assertEqual(first, render_path)
        self.assertEqual(second, render_path)
        page_image_fast.assert_called_once()
        image.save.assert_called_once_with(render_path, format="PNG")


if __name__ == "__main__":
    unittest.main()
