#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

import fitz
import pytesseract
import requests
from PIL import Image, ImageOps


DEFAULT_DPI = 220
DEFAULT_OCR_MAGNIFY = 2.0
MIN_FONT_SIZE = 6.5
FONT_NAME = "helv"


class TranslationBackendError(RuntimeError):
    pass


@dataclass
class TextRegion:
    bbox: tuple[float, float, float, float]
    text: str
    source: str
    font_size_hint: float
    align: str = "left"


@dataclass
class OverflowBlock:
    source_page: int
    text: str
    bbox: tuple[float, float, float, float]
    reason: str


@dataclass
class PageReport:
    page_number: int
    page_type: str
    region_source: str
    regions: int
    translated_regions: int
    ocr_magnify: float
    overlay_background: str
    continuations: int = 0
    compromises: list[str] = field(default_factory=list)


class BaseTranslator:
    name = "base"

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        raise NotImplementedError


class OpenAITranslator(BaseTranslator):
    name = "openai"

    def __init__(self, model: str = "gpt-5.4-mini") -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise TranslationBackendError("OPENAI_API_KEY is not set")
        self.api_key = api_key
        self.model = model
        self.session = requests.Session()

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Translate the user's text accurately into the target language. "
                        "Preserve legal acronyms, proper nouns, identifiers, emails, URLs, "
                        "and obvious structured labels. Return only translated text."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Source language: {source_lang}\n"
                        f"Target language: {target_lang}\n"
                        f"Text:\n{text}"
                    ),
                },
            ],
            "temperature": 0,
        }
        response = self.session.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
        if response.status_code != 200:
            raise TranslationBackendError(
                f"OpenAI request failed: {response.status_code} {response.text[:300]}"
            )
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class ArgosTranslator(BaseTranslator):
    name = "argos"

    def __init__(self, source_lang: str, target_lang: str) -> None:
        try:
            from argostranslate import package, translate
        except ImportError as exc:
            raise TranslationBackendError(
                "argostranslate is not installed. Install it or choose another translator backend."
            ) from exc

        self._package = package
        self._translate = translate
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.translation = self._load_translation()

    def _load_translation(self):
        installed = self._translate.get_installed_languages()
        source = next((lang for lang in installed if lang.code == self.source_lang), None)
        target = next((lang for lang in installed if lang.code == self.target_lang), None)
        if source and target:
            candidate = source.get_translation(target)
            if candidate:
                return candidate

        available = self._package.get_available_packages()
        match = next(
            (
                pkg
                for pkg in available
                if pkg.from_code == self.source_lang and pkg.to_code == self.target_lang
            ),
            None,
        )
        if not match:
            raise TranslationBackendError(
                f"No Argos package available for {self.source_lang}->{self.target_lang}"
            )
        package_path = match.download()
        self._package.install_from_path(package_path)
        installed = self._translate.get_installed_languages()
        source = next(lang for lang in installed if lang.code == self.source_lang)
        target = next(lang for lang in installed if lang.code == self.target_lang)
        return source.get_translation(target)

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        return self.translation.translate(text).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate PDFs in place while preserving layout and non-text artifacts."
    )
    parser.add_argument("inputs", nargs="+", help="Input PDF paths")
    parser.add_argument("--source-lang", default="fr", help="Source language code")
    parser.add_argument("--target-lang", default="en", help="Target language code")
    parser.add_argument(
        "--output-dir",
        default="translated-output",
        help="Directory where translated PDFs and notes will be written",
    )
    parser.add_argument(
        "--pages",
        help="Optional page selection like 1-3,5,8",
    )
    parser.add_argument(
        "--magnify-factor",
        type=float,
        default=DEFAULT_OCR_MAGNIFY,
        help="OCR magnification factor for small scan text",
    )
    parser.add_argument(
        "--notes-path",
        help="Optional explicit notes path. Defaults to one Markdown file per input PDF.",
    )
    parser.add_argument(
        "--overlay-background",
        choices=("sample", "white"),
        default="sample",
        help="How to choose the fill color behind translated overlays",
    )
    parser.add_argument(
        "--translator",
        choices=("auto", "openai", "argos"),
        default="auto",
        help="Translation backend selection",
    )
    parser.add_argument(
        "--openai-model",
        default="gpt-5.4-mini",
        help="Model to use when translator=openai or auto picks OpenAI",
    )
    return parser.parse_args()


def ensure_pdf(path: Path) -> None:
    if path.suffix.lower() != ".pdf":
        raise SystemExit(f"Expected a PDF input, got: {path}")


def choose_translator(name: str, source_lang: str, target_lang: str, model: str) -> BaseTranslator:
    errors: list[str] = []
    if name in ("auto", "openai"):
        try:
            return OpenAITranslator(model=model)
        except TranslationBackendError as exc:
            errors.append(str(exc))
            if name == "openai":
                raise
    if name in ("auto", "argos"):
        try:
            return ArgosTranslator(source_lang=source_lang, target_lang=target_lang)
        except TranslationBackendError as exc:
            errors.append(str(exc))
    raise SystemExit("Unable to initialize a translation backend: " + " | ".join(errors))


def parse_page_selection(raw: str | None, page_count: int) -> set[int]:
    if not raw:
        return set(range(1, page_count + 1))
    selected: set[int] = set()
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if "-" in item:
            start_s, end_s = item.split("-", 1)
            start = int(start_s)
            end = int(end_s)
            for value in range(start, end + 1):
                selected.add(value)
        else:
            selected.add(int(item))
    return {value for value in selected if 1 <= value <= page_count}


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("\uf0b7", "•")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def page_image_fast(page: fitz.Page, dpi: int) -> Image.Image:
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def classify_page(page: fitz.Page) -> tuple[str, str]:
    words = page.get_text("words")
    image_rects: list[fitz.Rect] = []
    for image in page.get_images(full=True):
        xref = image[0]
        image_rects.extend(page.get_image_rects(xref))

    page_area = page.rect.get_area() or 1.0
    image_area = sum(rect.get_area() for rect in image_rects)
    image_ratio = image_area / page_area
    word_count = len(words)

    if word_count >= 50 and image_ratio < 0.25:
        return "digital", "native"
    if word_count >= 20 and image_ratio >= 0.25:
        return "mixed", "native"
    if image_ratio >= 0.5 or image_rects:
        return "scanned", "ocr"
    return ("digital", "native") if word_count else ("scanned", "ocr")


def union_bbox(boxes: Iterable[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    boxes = list(boxes)
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def infer_alignment(rect: fitz.Rect, page_rect: fitz.Rect) -> str:
    page_center = page_rect.width / 2
    rect_center = (rect.x0 + rect.x1) / 2
    if abs(rect_center - page_center) < page_rect.width * 0.08:
        return "center"
    if rect.x1 > page_rect.width * 0.85 and rect.width < page_rect.width * 0.6:
        return "right"
    return "left"


def extract_native_regions(page: fitz.Page) -> list[TextRegion]:
    text_dict = page.get_text("dict", sort=True)
    regions: list[TextRegion] = []
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = [span for span in line.get("spans", []) if span.get("text", "").strip()]
            if not spans:
                continue
            line_text = "".join(span.get("text", "") for span in spans).strip()
            text = clean_text(line_text)
            if not text:
                continue
            sizes = [float(span.get("size", 10)) for span in spans]
            bbox = tuple(line.get("bbox", block.get("bbox")))
            rect = fitz.Rect(bbox)
            regions.append(
                TextRegion(
                    bbox=bbox,
                    text=text,
                    source="native",
                    font_size_hint=max(8.0, (sum(sizes) / len(sizes)) if sizes else rect.height * 0.75),
                    align=infer_alignment(rect, page.rect),
                )
            )
    return regions


def ocr_page_image(page: fitz.Page, magnify_factor: float) -> tuple[Image.Image, float]:
    dpi = max(150, int(DEFAULT_DPI * max(1.0, magnify_factor)))
    image = page_image_fast(page, dpi=dpi)
    image = ImageOps.autocontrast(ImageOps.grayscale(image)).convert("RGB")
    return image, dpi / 72.0


def extract_ocr_regions(page: fitz.Page, magnify_factor: float) -> list[TextRegion]:
    image, scale = ocr_page_image(page, magnify_factor=magnify_factor)
    data = pytesseract.image_to_data(
        image,
        output_type=pytesseract.Output.DICT,
        config="--psm 11",
    )
    groups: dict[tuple[int, int], dict[str, object]] = {}
    count = len(data["text"])
    for idx in range(count):
        text = clean_text(str(data["text"][idx]))
        conf_raw = str(data["conf"][idx]).strip()
        try:
            confidence = float(conf_raw)
        except ValueError:
            confidence = -1
        if not text or confidence < 25:
            continue
        key = (int(data["block_num"][idx]), int(data["par_num"][idx]))
        item = groups.setdefault(key, {"lines": [], "boxes": []})
        cast_lines = item["lines"]
        cast_boxes = item["boxes"]
        assert isinstance(cast_lines, list)
        assert isinstance(cast_boxes, list)
        cast_lines.append(
            (
                int(data["line_num"][idx]),
                int(data["left"][idx]),
                int(data["top"][idx]),
                int(data["width"][idx]),
                int(data["height"][idx]),
                text,
            )
        )
        cast_boxes.append(
            (
                int(data["left"][idx]),
                int(data["top"][idx]),
                int(data["left"][idx]) + int(data["width"][idx]),
                int(data["top"][idx]) + int(data["height"][idx]),
            )
        )

    regions: list[TextRegion] = []
    for group in groups.values():
        lines = sorted(group["lines"], key=lambda item: (item[0], item[2], item[1]))  # type: ignore[index]
        if not lines:
            continue
        text_lines = [item[5] for item in lines]
        text = clean_text(" ".join(text_lines))
        if not text:
            continue
        boxes = group["boxes"]  # type: ignore[assignment]
        bbox_px = union_bbox(boxes)
        bbox = tuple(value / scale for value in bbox_px)
        rect = fitz.Rect(bbox)
        regions.append(
            TextRegion(
                bbox=bbox,
                text=text,
                source="ocr",
                font_size_hint=max(MIN_FONT_SIZE, rect.height * 0.7),
                align=infer_alignment(rect, page.rect),
            )
        )
    return regions


def normalize_text_for_translation(text: str) -> str:
    return clean_text(text)


def should_translate(text: str) -> bool:
    if not text.strip():
        return False
    if re.fullmatch(r"[\W\d_]+", text):
        return False
    return True


def estimate_background_color(
    page: fitz.Page,
    bbox: tuple[float, float, float, float],
    mode: str,
) -> tuple[float, float, float]:
    if mode == "white":
        return (1, 1, 1)
    rect = fitz.Rect(bbox)
    clip = rect + (-1, -1, 1, 1)
    pix = page.get_pixmap(clip=clip, dpi=72, alpha=False)
    if pix.width == 0 or pix.height == 0:
        return (1, 1, 1)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    pixels = image.load()
    if pixels is None:
        return (1, 1, 1)
    total = 0
    if image.width == 0 or image.height == 0:
        return (1, 1, 1)
    r = g = b = 0
    for y in range(image.height):
        for x in range(image.width):
            if x not in (0, image.width - 1) and y not in (0, image.height - 1):
                continue
            pixel = pixels[x, y]
            r += pixel[0]
            g += pixel[1]
            b += pixel[2]
            total += 1
    if total == 0:
        return (1, 1, 1)
    r = r / total / 255.0
    g = g / total / 255.0
    b = b / total / 255.0
    return (r, g, b)


def wrap_paragraph(text: str, width: float, font: fitz.Font, font_size: float) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if font.text_length(candidate, fontsize=font_size) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def layout_text(text: str, width: float, font: fitz.Font, font_size: float) -> list[str]:
    paragraphs = text.splitlines() or [text]
    lines: list[str] = []
    for paragraph in paragraphs:
        stripped = paragraph.strip()
        if not stripped:
            lines.append("")
            continue
        if stripped.startswith(("•", "-", "*")):
            bullet = stripped[0]
            content = stripped[1:].strip()
            wrapped = wrap_paragraph(content, max(20, width - font.text_length(f"{bullet} ", fontsize=font_size)), font, font_size)
            for index, line in enumerate(wrapped):
                lines.append(f"{bullet} {line}" if index == 0 else f"  {line}")
            continue
        lines.extend(wrap_paragraph(stripped, width, font, font_size))
    return lines


def split_text_for_height(
    text: str,
    width: float,
    height: float,
    font: fitz.Font,
    font_size: float,
) -> tuple[list[str], str]:
    line_height = font_size * 1.2
    max_lines = max(1, int(height // line_height))
    lines = layout_text(text, width, font, font_size)
    if len(lines) <= max_lines:
        return lines, ""
    kept = lines[:max_lines]
    remainder = "\n".join(line.lstrip() for line in lines[max_lines:]).strip()
    return kept, remainder


def draw_translated_text(
    page: fitz.Page,
    region: TextRegion,
    translated_text: str,
) -> str:
    rect = fitz.Rect(region.bbox)
    font = fitz.Font(FONT_NAME)
    color = (0, 0, 0)
    for font_size in [max(region.font_size_hint, MIN_FONT_SIZE) - step for step in range(0, 9)]:
        if font_size < MIN_FONT_SIZE:
            continue
        preview_lines, remainder = split_text_for_height(
            translated_text,
            width=max(20, rect.width - 2),
            height=max(10, rect.height - 2),
            font=font,
            font_size=font_size,
        )
        if remainder:
            continue
        draw_lines(page, rect, preview_lines, font, font_size, color, region.align)
        return ""

    font_size = MIN_FONT_SIZE
    lines, remainder = split_text_for_height(
        translated_text,
        width=max(20, rect.width - 2),
        height=max(10, rect.height - 2),
        font=font,
        font_size=font_size,
    )
    draw_lines(page, rect, lines, font, font_size, color, region.align)
    return remainder


def draw_lines(
    page: fitz.Page,
    rect: fitz.Rect,
    lines: list[str],
    font: fitz.Font,
    font_size: float,
    color: tuple[float, float, float],
    align: str,
) -> None:
    line_height = font_size * 1.2
    cursor_y = rect.y0 + font_size
    for line in lines:
        if cursor_y > rect.y1:
            break
        text_width = font.text_length(line, fontsize=font_size)
        if align == "center":
            x = rect.x0 + max(0, (rect.width - text_width) / 2)
        elif align == "right":
            x = max(rect.x0, rect.x1 - text_width)
        else:
            x = rect.x0
        if line.strip():
            page.insert_text(
                fitz.Point(x, cursor_y),
                line,
                fontname=FONT_NAME,
                fontsize=font_size,
                color=color,
            )
        cursor_y += line_height


def translate_regions(
    translator: BaseTranslator,
    regions: list[TextRegion],
    source_lang: str,
    target_lang: str,
) -> dict[int, str]:
    cache: dict[str, str] = {}
    translated: dict[int, str] = {}
    for index, region in enumerate(regions):
        text = normalize_text_for_translation(region.text)
        if not should_translate(text):
            translated[index] = text
            continue
        if text not in cache:
            cache[text] = translator.translate(text, source_lang=source_lang, target_lang=target_lang)
        translated[index] = clean_text(cache[text])
    return translated


def page_output_name(input_path: Path) -> str:
    return f"{input_path.stem}-translated-in-place.pdf"


def notes_output_name(input_path: Path) -> str:
    return f"{input_path.stem}-translation-notes.md"


def add_continuation_pages(
    out_doc: fitz.Document,
    overflow_blocks: list[OverflowBlock],
    page_rect: fitz.Rect,
) -> int:
    if not overflow_blocks:
        return 0

    pages_added = 0
    margin = 48
    usable_rect = fitz.Rect(margin, 90, page_rect.width - margin, page_rect.height - margin)
    font = fitz.Font(FONT_NAME)
    line_height = 11.5 * 1.25

    current_page: fitz.Page | None = None
    cursor_y = usable_rect.y0
    for block in overflow_blocks:
        remaining = block.text
        heading = f"Continuation from source page {block.source_page}"
        while remaining:
            if current_page is None or cursor_y > usable_rect.y1 - 120:
                current_page = out_doc.new_page(width=page_rect.width, height=page_rect.height)
                current_page.insert_text((margin, 52), heading, fontname="helv", fontsize=13)
                cursor_y = usable_rect.y0
                pages_added += 1
            available_height = usable_rect.y1 - cursor_y
            max_lines = max(1, int(available_height // line_height))
            lines = layout_text(remaining, usable_rect.width, font, 11.5)
            chunk = lines[:max_lines]
            remaining = "\n".join(line.lstrip() for line in lines[max_lines:]).strip()
            current_page.insert_textbox(
                fitz.Rect(usable_rect.x0, cursor_y, usable_rect.x1, cursor_y + available_height),
                "\n".join(chunk),
                fontname="helv",
                fontsize=11.5,
                lineheight=line_height,
            )
            cursor_y += min(available_height, len(chunk) * line_height + 16)
            if remaining:
                current_page = None
    return pages_added


def translate_pdf(
    input_path: Path,
    output_dir: Path,
    translator: BaseTranslator,
    source_lang: str,
    target_lang: str,
    page_selection: str | None,
    magnify_factor: float,
    notes_path: Path | None,
    overlay_background: str,
) -> tuple[Path, Path]:
    ensure_pdf(input_path)
    source_doc = fitz.open(input_path)
    out_doc = fitz.open()
    selected_pages = parse_page_selection(page_selection, source_doc.page_count)
    notes: list[str] = []
    reports: list[PageReport] = []
    continuation_total = 0

    for source_index in range(source_doc.page_count):
        source_page_number = source_index + 1
        out_doc.insert_pdf(source_doc, from_page=source_index, to_page=source_index)
        page = out_doc[-1]
        source_page = source_doc[source_index]
        page_type, region_source = classify_page(source_page)
        ocr_scale = magnify_factor if region_source == "ocr" else 1.0
        report = PageReport(
            page_number=source_page_number,
            page_type=page_type,
            region_source=region_source,
            regions=0,
            translated_regions=0,
            ocr_magnify=ocr_scale,
            overlay_background=overlay_background,
        )

        if source_page_number not in selected_pages:
            report.compromises.append("Skipped at user request via --pages selection.")
            reports.append(report)
            continue

        regions = (
            extract_native_regions(source_page)
            if region_source == "native"
            else extract_ocr_regions(source_page, magnify_factor=ocr_scale)
        )
        regions = [region for region in regions if clean_text(region.text)]
        report.regions = len(regions)

        translated_lookup = translate_regions(
            translator,
            regions,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        overflow_blocks: list[OverflowBlock] = []

        for region in regions:
            fill = estimate_background_color(source_page, region.bbox, overlay_background)
            page.add_redact_annot(fitz.Rect(region.bbox), fill=fill)
        if regions:
            page.apply_redactions()

        for index, region in enumerate(regions):
            translated_text = translated_lookup[index]
            if not translated_text:
                continue
            report.translated_regions += 1
            remainder = draw_translated_text(page, region, translated_text)
            if remainder:
                report.continuations += 1
                report.compromises.append(
                    f"Region at {tuple(round(v, 1) for v in region.bbox)} overflowed; moved remainder to continuation page."
                )
                overflow_blocks.append(
                    OverflowBlock(
                        source_page=source_page_number,
                        text=remainder,
                        bbox=region.bbox,
                        reason="text-overflow",
                    )
                )

        continuation_added = add_continuation_pages(out_doc, overflow_blocks, page.rect)
        continuation_total += continuation_added
        reports.append(report)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_pdf = output_dir / page_output_name(input_path)
    out_doc.save(output_pdf, deflate=True)
    out_doc.close()

    notes_path = notes_path or (output_dir / notes_output_name(input_path))
    notes.extend(
        [
            f"# Translation Notes: {input_path.name}",
            "",
            f"- Translator backend: `{translator.name}`",
            f"- Source language: `{source_lang}`",
            f"- Target language: `{target_lang}`",
            f"- Total source pages: `{source_doc.page_count}`",
            f"- Continuation pages added: `{continuation_total}`",
            f"- Overlay background mode: `{overlay_background}`",
            "",
            "## Page Reports",
            "",
        ]
    )
    for report in reports:
        notes.append(
            (
                f"- Page {report.page_number}: type=`{report.page_type}`, source=`{report.region_source}`, "
                f"regions={report.regions}, translated={report.translated_regions}, "
                f"ocr_magnify={report.ocr_magnify}, overlay_background={report.overlay_background}, "
                f"continuations={report.continuations}"
            )
        )
        for compromise in report.compromises:
            notes.append(f"  - {compromise}")
    notes.extend(
        [
            "",
            "## Final QA TODO",
            "",
            "- Run `compare_rendered_pages.py` against the source and translated PDFs.",
            "- Visually inspect all pages with signatures, handwriting, stamps, tables, headers, footers, or continuation overflow.",
            "- Record the exact pages checked in the final user-facing answer.",
            "",
            "## Machine-readable Summary",
            "",
            "```json",
            json.dumps([asdict(report) for report in reports], indent=2),
            "```",
            "",
        ]
    )
    notes_path.write_text("\n".join(notes))
    return output_pdf, notes_path


def main() -> int:
    args = parse_args()
    translator = choose_translator(
        name=args.translator,
        source_lang=args.source_lang,
        target_lang=args.target_lang,
        model=args.openai_model,
    )
    output_dir = Path(args.output_dir).expanduser().resolve()
    explicit_notes = Path(args.notes_path).expanduser().resolve() if args.notes_path else None

    for raw_input in args.inputs:
        input_path = Path(raw_input).expanduser().resolve()
        per_input_notes = explicit_notes
        if explicit_notes and len(args.inputs) > 1:
            per_input_notes = explicit_notes.with_name(
                f"{explicit_notes.stem}-{input_path.stem}{explicit_notes.suffix or '.md'}"
            )
        output_pdf, notes_path = translate_pdf(
            input_path=input_path,
            output_dir=output_dir,
            translator=translator,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            page_selection=args.pages,
            magnify_factor=args.magnify_factor,
            notes_path=per_input_notes,
            overlay_background=args.overlay_background,
        )
        print(output_pdf)
        print(notes_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
