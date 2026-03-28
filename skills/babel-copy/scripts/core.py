from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

import fitz
import pytesseract
from PIL import Image, ImageOps


DEFAULT_DPI = 220
DEFAULT_OCR_MAGNIFY = 2.0
MIN_FONT_SIZE = 6.5
FONT_NAME = "helv"
DEFAULT_OCR_LANG = "eng"
DEFAULT_OCR_PSM = "4"


@dataclass
class TextRegion:
    bbox: tuple[float, float, float, float]
    text: str
    source: str
    font_size_hint: float
    align: str = "left"
    span_styles: list[dict[str, object]] = field(default_factory=list)
    render_font_name: str = FONT_NAME
    render_font_file: str | None = None
    text_color: tuple[float, float, float] = (0.0, 0.0, 0.0)
    dominant_font_size: float | None = None
    max_font_size: float | None = None
    baseline_y: float | None = None


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


def ensure_pdf(path: Path) -> None:
    if path.suffix.lower() != ".pdf":
        raise SystemExit(f"Expected a PDF input, got: {path}")


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
            for value in range(int(start_s), int(end_s) + 1):
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


def non_whitespace_count(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def dominant_span_value(span_styles: list[dict[str, object]], key: str):
    weights: dict[object, int] = {}
    for span in span_styles:
        value = span.get(key)
        char_count = int(span.get("char_count", 0) or 0)
        if value in ("", None) or char_count <= 0:
            continue
        weights[value] = weights.get(value, 0) + char_count
    if not weights:
        return None
    return max(weights.items(), key=lambda item: (item[1], str(item[0])))[0]


def dominant_weighted_number(
    values: list[tuple[float, int]],
    *,
    precision: int = 2,
) -> float | None:
    weights: dict[float, int] = {}
    for value, weight in values:
        if weight <= 0:
            continue
        rounded = round(float(value), precision)
        weights[rounded] = weights.get(rounded, 0) + int(weight)
    if not weights:
        return None
    return float(max(weights.items(), key=lambda item: (item[1], item[0]))[0])


def color_int_to_rgb(value: int | None) -> tuple[float, float, float]:
    if value is None:
        return (0.0, 0.0, 0.0)
    rgb = int(value) & 0xFFFFFF
    return ((rgb >> 16) / 255.0, ((rgb >> 8) & 0xFF) / 255.0, (rgb & 0xFF) / 255.0)


def page_image_fast(page: fitz.Page, dpi: int) -> Image.Image:
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def classify_page(page: fitz.Page) -> tuple[str, str]:
    words = page.get_text("words")
    image_rects: list[fitz.Rect] = []
    for image in page.get_images(full=True):
        image_rects.extend(page.get_image_rects(image[0]))
    page_area = page.rect.get_area() or 1.0
    image_ratio = sum(rect.get_area() for rect in image_rects) / page_area
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
            line_text = clean_text("".join(span.get("text", "") for span in spans))
            if not line_text:
                continue
            bbox = tuple(line.get("bbox", block.get("bbox")))
            rect = fitz.Rect(bbox)
            sizes = [float(span.get("size", 10)) for span in spans]
            span_styles = []
            size_weights: list[tuple[float, int]] = []
            baseline_weights: list[tuple[float, int]] = []
            for span in spans:
                raw_text = str(span.get("text", ""))
                char_count = non_whitespace_count(raw_text)
                if char_count <= 0:
                    continue
                font_size = float(span.get("size", 10) or 10)
                origin = span.get("origin")
                baseline_y = None
                if isinstance(origin, (list, tuple)) and len(origin) >= 2:
                    try:
                        baseline_y = float(origin[1])
                    except (TypeError, ValueError):
                        baseline_y = None
                span_styles.append(
                    {
                        "font_name": str(span.get("font") or ""),
                        "flags": int(span.get("flags", 0) or 0),
                        "color": int(span.get("color", 0) or 0),
                        "font_size": font_size,
                        "char_count": char_count,
                    }
                )
                size_weights.append((font_size, char_count))
                if baseline_y is not None:
                    baseline_weights.append((baseline_y, char_count))
            max_font_size = max(sizes) if sizes else rect.height * 0.75
            dominant_font_size = dominant_weighted_number(size_weights) or max_font_size
            regions.append(
                TextRegion(
                    bbox=bbox,
                    text=line_text,
                    source="native",
                    font_size_hint=max(8.0, max(dominant_font_size, max_font_size)),
                    align=infer_alignment(rect, page.rect),
                    span_styles=span_styles,
                    render_font_name=str(dominant_span_value(span_styles, "font_name") or FONT_NAME),
                    text_color=color_int_to_rgb(dominant_span_value(span_styles, "color")),
                    dominant_font_size=dominant_font_size,
                    max_font_size=max_font_size,
                    baseline_y=dominant_weighted_number(baseline_weights),
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
    ocr_lang = os.environ.get("BABEL_COPY_OCR_LANG", DEFAULT_OCR_LANG).strip() or DEFAULT_OCR_LANG
    ocr_psm = os.environ.get("BABEL_COPY_OCR_PSM", DEFAULT_OCR_PSM).strip() or DEFAULT_OCR_PSM
    data = pytesseract.image_to_data(
        image,
        lang=ocr_lang,
        output_type=pytesseract.Output.DICT,
        config=f"--psm {ocr_psm}",
    )
    groups: dict[tuple[int, int, int], dict[str, object]] = {}
    for idx in range(len(data["text"])):
        text = clean_text(str(data["text"][idx]))
        try:
            confidence = float(str(data["conf"][idx]).strip())
        except ValueError:
            confidence = -1
        if not text or confidence < 25:
            continue
        key = (int(data["block_num"][idx]), int(data["par_num"][idx]), int(data["line_num"][idx]))
        group = groups.setdefault(key, {"tokens": [], "boxes": []})
        tokens = group["tokens"]
        boxes = group["boxes"]
        assert isinstance(tokens, list)
        assert isinstance(boxes, list)
        tokens.append(
            (
                int(data["word_num"][idx]),
                int(data["left"][idx]),
                int(data["top"][idx]),
                text,
            )
        )
        boxes.append(
            (
                int(data["left"][idx]),
                int(data["top"][idx]),
                int(data["left"][idx]) + int(data["width"][idx]),
                int(data["top"][idx]) + int(data["height"][idx]),
            )
        )
    regions: list[TextRegion] = []
    for group in groups.values():
        tokens = sorted(group["tokens"], key=lambda item: (item[0], item[1], item[2]))  # type: ignore[index]
        if not tokens:
            continue
        text = clean_text(" ".join(item[3] for item in tokens))
        if not text:
            continue
        bbox_px = union_bbox(group["boxes"])  # type: ignore[arg-type]
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
    return not bool(re.fullmatch(r"[\W\d_]+", text))


def estimate_background_color(page: fitz.Page, bbox: tuple[float, float, float, float], mode: str) -> tuple[float, float, float]:
    if mode == "white":
        return (1, 1, 1)
    rect = fitz.Rect(bbox)
    pix = page.get_pixmap(clip=rect + (-1, -1, 1, 1), dpi=72, alpha=False)
    if pix.width == 0 or pix.height == 0:
        return (1, 1, 1)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    pixels = image.load()
    if pixels is None:
        return (1, 1, 1)
    total = 0
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
    return (r / total / 255.0, g / total / 255.0, b / total / 255.0)


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
        if stripped.startswith(("•", "-", "*", "o ")):
            bullet = stripped[0]
            content = stripped[1:].strip()
            wrapped = wrap_paragraph(content, max(20, width - font.text_length(f"{bullet} ", fontsize=font_size)), font, font_size)
            for index, line in enumerate(wrapped):
                lines.append(f"{bullet} {line}" if index == 0 else f"  {line}")
            continue
        lines.extend(wrap_paragraph(stripped, width, font, font_size))
    return lines


def split_text_for_height(text: str, width: float, height: float, font: fitz.Font, font_size: float) -> tuple[list[str], str]:
    line_height = font_size * 1.2
    max_lines = max(1, int(height // line_height))
    lines = layout_text(text, width, font, font_size)
    if len(lines) <= max_lines:
        return lines, ""
    return lines[:max_lines], "\n".join(line.lstrip() for line in lines[max_lines:]).strip()


def draw_lines(
    page: fitz.Page,
    rect: fitz.Rect,
    lines: list[str],
    font: fitz.Font,
    font_size: float,
    color: tuple[float, float, float],
    align: str,
    render_font_name: str,
    render_font_file: str | None = None,
    baseline_y: float | None = None,
) -> None:
    line_height = font_size * 1.2
    descender = getattr(font, "descender", -0.25)
    fallback_baseline = rect.y1 + float(descender) * font_size
    if baseline_y is not None:
        cursor_y = float(baseline_y)
    elif len(lines) == 1:
        cursor_y = fallback_baseline
    else:
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
                fontname=render_font_name,
                fontfile=render_font_file,
                fontsize=font_size,
                color=color,
            )
        cursor_y += line_height


def draw_translated_text(page: fitz.Page, region: TextRegion, translated_text: str) -> str:
    rect = fitz.Rect(region.bbox)
    font = fitz.Font(fontfile=region.render_font_file) if region.render_font_file else fitz.Font(region.render_font_name)
    for font_size in [max(region.font_size_hint, MIN_FONT_SIZE) - step for step in range(0, 9)]:
        if font_size < MIN_FONT_SIZE:
            continue
        lines, remainder = split_text_for_height(translated_text, max(20, rect.width - 2), max(10, rect.height - 2), font, font_size)
        if remainder:
            continue
        draw_lines(
            page,
            rect,
            lines,
            font,
            font_size,
            region.text_color,
            region.align,
            region.render_font_name,
            region.render_font_file,
            region.baseline_y,
        )
        return ""
    font_size = MIN_FONT_SIZE
    lines, remainder = split_text_for_height(translated_text, max(20, rect.width - 2), max(10, rect.height - 2), font, font_size)
    draw_lines(
        page,
        rect,
        lines,
        font,
        font_size,
        region.text_color,
        region.align,
        region.render_font_name,
        region.render_font_file,
        region.baseline_y,
    )
    return remainder


def translate_regions(translator, regions: list[TextRegion], source_lang: str, target_lang: str) -> dict[int, str]:
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


def add_continuation_pages(out_doc: fitz.Document, overflow_blocks: list[OverflowBlock], page_rect: fitz.Rect) -> int:
    if not overflow_blocks:
        return 0
    pages_added = 0
    usable_rect = fitz.Rect(48, 90, page_rect.width - 48, page_rect.height - 48)
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
                current_page.insert_text((48, 52), heading, fontname="helv", fontsize=13)
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


def translate_pdf(input_path: Path, output_dir: Path, translator, source_lang: str, target_lang: str, page_selection: str | None, magnify_factor: float, notes_path: Path | None, overlay_background: str) -> tuple[Path, Path]:
    ensure_pdf(input_path)
    source_doc = fitz.open(input_path)
    out_doc = fitz.open()
    selected_pages = parse_page_selection(page_selection, source_doc.page_count)
    reports: list[PageReport] = []
    continuation_total = 0
    for source_index in range(source_doc.page_count):
        source_page_number = source_index + 1
        out_doc.insert_pdf(source_doc, from_page=source_index, to_page=source_index)
        page = out_doc[-1]
        source_page = source_doc[source_index]
        page_type, region_source = classify_page(source_page)
        ocr_scale = magnify_factor if region_source == "ocr" else 1.0
        report = PageReport(source_page_number, page_type, region_source, 0, 0, ocr_scale, overlay_background)
        if source_page_number not in selected_pages:
            report.compromises.append("Skipped at user request via --pages selection.")
            reports.append(report)
            continue
        regions = extract_native_regions(source_page) if region_source == "native" else extract_ocr_regions(source_page, ocr_scale)
        regions = [region for region in regions if clean_text(region.text)]
        report.regions = len(regions)
        translated_lookup = translate_regions(translator, regions, source_lang, target_lang)
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
                report.compromises.append(f"Region at {tuple(round(v, 1) for v in region.bbox)} overflowed; moved remainder to continuation page.")
                overflow_blocks.append(OverflowBlock(source_page_number, remainder, region.bbox, "text-overflow"))
        continuation_total += add_continuation_pages(out_doc, overflow_blocks, page.rect)
        reports.append(report)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pdf = output_dir / page_output_name(input_path)
    out_doc.save(output_pdf, deflate=True)
    out_doc.close()
    notes_path = notes_path or (output_dir / notes_output_name(input_path))
    notes = [
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
    for report in reports:
        notes.append(f"- Page {report.page_number}: type=`{report.page_type}`, source=`{report.region_source}`, regions={report.regions}, translated={report.translated_regions}, ocr_magnify={report.ocr_magnify}, overlay_background={report.overlay_background}, continuations={report.continuations}")
        for compromise in report.compromises:
            notes.append(f"  - {compromise}")
    notes.extend(["", "## Final QA TODO", "", "- Render and inspect the final PDF against the source.", "", "## Machine-readable Summary", "", "```json", json.dumps([asdict(report) for report in reports], indent=2), "```", ""])
    notes_path.write_text("\n".join(notes))
    return output_pdf, notes_path
