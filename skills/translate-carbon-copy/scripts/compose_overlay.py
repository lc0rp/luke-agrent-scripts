#!/usr/bin/env python3
"""
Compose a translated PDF by overlaying translated text onto original page images.

Takes the output of extract_page_elements.py plus a translations JSON file and
produces the final translated PDF.

Usage:
    python compose_overlay.py <analysis_dir> <translations.json> <output.pdf> [options]

    translations.json format:
    {
        "pages": [
            {
                "page_number": 1,
                "regions": [
                    {
                        "original_text": "Texte original",
                        "translated_text": "Original text",
                        "x0": 72.0,
                        "y0": 100.0,
                        "width": 200.0,
                        "height": 14.0,
                        "font_size": 10,
                        "font_name": "Helvetica",
                        "bold": false,
                        "italic": false,
                        "text_color": [0, 0, 0],
                        "is_signature": false
                    }
                ]
            }
        ]
    }

Options:
    --magnification FLOAT   Global text magnification factor (default: 1.0)
    --whiten-bg             Convert background to white before overlay
    --bg-threshold INT      Pixel brightness threshold for whitening (default: 220)
"""

import argparse
import io
import json
import os
import sys

def ensure_deps():
    missing = []
    for pkg in ['pypdfium2', 'reportlab', 'PIL', 'pypdf']:
        try:
            __import__(pkg if pkg != 'PIL' else 'PIL.Image')
        except ImportError:
            missing.append(pkg.replace('PIL', 'Pillow'))
    if missing:
        print(f"Missing: {', '.join(missing)}")
        print(f"Install: uv pip install {' '.join(missing)} --system")
        sys.exit(1)

ensure_deps()

import pypdfium2 as pdfium
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from pypdf import PdfReader, PdfWriter
from PIL import Image
import numpy as np


def whiten_background(img, threshold=220):
    """Convert near-white pixels to pure white for cleaner overlays."""
    arr = np.array(img)
    mask = np.all(arr > threshold, axis=2)
    arr[mask] = [255, 255, 255]
    return Image.fromarray(arr)


def get_font_name(base='Helvetica', bold=False, italic=False):
    """Get reportlab font name with bold/italic variants."""
    if base in ('Helvetica', 'Courier'):
        italic_suffix = 'Oblique'
    else:
        italic_suffix = 'Italic'

    if bold and italic:
        return f"{base}-Bold{italic_suffix}"
    elif bold:
        return f"{base}-Bold"
    elif italic:
        return f"{base}-{italic_suffix}"
    return base


def wrap_text(text, font_name, font_size, max_width):
    """Word-wrap text to fit within max_width. Returns list of lines."""
    words = text.split()
    if not words:
        return ['']

    lines = []
    current_line = words[0]

    for word in words[1:]:
        test_line = current_line + ' ' + word
        if stringWidth(test_line, font_name, font_size) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)
    return lines


def compose_page(page_image_path, regions, page_width, page_height,
                  magnification=1.0, whiten=False, bg_threshold=220,
                  bg_color=(255, 255, 255)):
    """
    Compose a single translated page.

    Returns a BytesIO containing a single-page PDF.
    """
    # Load and optionally whiten the background image
    img = Image.open(page_image_path).convert('RGB')
    if whiten:
        img = whiten_background(img, threshold=bg_threshold)

    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)

    # Create the overlay PDF
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(page_width, page_height))

    # Draw background image
    c.drawImage(ImageReader(img_buffer), 0, 0,
                width=page_width, height=page_height)

    for region in regions:
        if region.get('is_signature', False):
            # Don't overlay signatures — they're part of the background
            continue

        translated = region.get('translated_text', '')
        if not translated:
            continue

        # Region coordinates (in PDF points, origin top-left in the JSON)
        rx = region['x0']
        ry = region['y0']
        rw = region['width']
        rh = region['height']

        # Apply magnification
        font_size = region.get('font_size', 10) * magnification
        font_base = region.get('font_name', 'Helvetica')
        bold = region.get('bold', False)
        italic = region.get('italic', False)
        font_name = get_font_name(font_base, bold, italic)

        text_color = region.get('text_color', [0, 0, 0])

        # Convert y from top-origin to PDF bottom-origin
        pdf_y_bottom = page_height - ry - rh

        # Padding
        pad = 1

        # Draw background-colored rectangle to cover original text
        r, g, b = bg_color
        c.setFillColorRGB(r/255, g/255, b/255)
        c.rect(rx - pad, pdf_y_bottom - pad,
               rw + 2*pad, rh + 2*pad,
               fill=True, stroke=False)

        # Draw translated text
        c.setFillColorRGB(text_color[0]/255, text_color[1]/255, text_color[2]/255)
        c.setFont(font_name, font_size)

        # Word-wrap if needed
        lines = wrap_text(translated, font_name, font_size, rw - 2*pad)
        leading = font_size * 1.2

        text_obj = c.beginText(rx + pad, pdf_y_bottom + rh - font_size - pad)
        text_obj.setFont(font_name, font_size)
        text_obj.setLeading(leading)
        for line in lines:
            text_obj.textLine(line)
        c.drawText(text_obj)

    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer


def main():
    parser = argparse.ArgumentParser(description='Compose translated PDF overlay')
    parser.add_argument('analysis_dir', help='Directory from extract_page_elements.py')
    parser.add_argument('translations', help='Path to translations JSON')
    parser.add_argument('output', help='Output PDF path')
    parser.add_argument('--magnification', type=float, default=1.0,
                        help='Text magnification factor (default: 1.0)')
    parser.add_argument('--whiten-bg', action='store_true',
                        help='Convert background to white before overlay')
    parser.add_argument('--bg-threshold', type=int, default=220,
                        help='Brightness threshold for whitening (default: 220)')
    args = parser.parse_args()

    # Load analysis
    analysis_path = os.path.join(args.analysis_dir, 'analysis.json')
    with open(analysis_path) as f:
        analysis = json.load(f)

    # Load translations
    with open(args.translations) as f:
        translations = json.load(f)

    print(f"Composing translated PDF: {analysis['page_count']} pages")
    if args.magnification != 1.0:
        print(f"  Magnification: {args.magnification}x")
    if args.whiten_bg:
        print(f"  Background whitening: ON (threshold={args.bg_threshold})")

    writer = PdfWriter()
    trans_pages = {p['page_number']: p for p in translations.get('pages', [])}

    for page_info in analysis['pages']:
        page_num = page_info['page_number']
        image_path = page_info['image_path']
        bg_color = tuple(page_info.get('background_color', [255, 255, 255]))

        # Use white if whitening is on
        overlay_bg = (255, 255, 255) if args.whiten_bg else bg_color

        # Get translations for this page
        page_trans = trans_pages.get(page_num, {})
        regions = page_trans.get('regions', [])

        # Get page dimensions from the original PDF
        src_pdf = pdfium.PdfDocument(
            os.path.join(os.path.dirname(args.analysis_dir),
                          analysis['source_file'])
        ) if 'source_file' in analysis else None

        if src_pdf and page_num <= len(src_pdf):
            page = src_pdf[page_num - 1]
            page_width = page.get_width()
            page_height = page.get_height()
        else:
            # Fallback: estimate from image at the analysis DPI
            img = Image.open(image_path)
            dpi = analysis.get('dpi', 300)
            page_width = img.width * 72.0 / dpi
            page_height = img.height * 72.0 / dpi

        print(f"  Page {page_num}: {len(regions)} translated regions")

        pdf_buffer = compose_page(
            image_path, regions,
            page_width, page_height,
            magnification=args.magnification,
            whiten=args.whiten_bg,
            bg_threshold=args.bg_threshold,
            bg_color=overlay_bg,
        )

        reader = PdfReader(pdf_buffer)
        writer.add_page(reader.pages[0])

    with open(args.output, 'wb') as f:
        writer.write(f)

    size_kb = os.path.getsize(args.output) / 1024
    print(f"\nOutput: {args.output} ({size_kb:.0f} KB)")


if __name__ == '__main__':
    main()
