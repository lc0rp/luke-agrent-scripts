#!/usr/bin/env python3
"""
Extract page elements from a PDF for translate-in-place processing.

For each page, produces:
  - A high-resolution PNG rendering (background image)
  - Text regions with bounding boxes (JSON)
  - Detected background color
  - Embedded image locations
  - Identified header/footer regions

Usage:
    python extract_page_elements.py <input.pdf> <output_dir> [--dpi 300] [--lang fra]

Output structure:
    output_dir/
    ├── pages/
    │   ├── page_001.png          # Full page render
    │   ├── page_001_regions.json # Text regions with bounding boxes
    │   ├── page_002.png
    │   └── page_002_regions.json
    ├── images/                   # Extracted embedded images
    │   ├── page_001_img_000.png
    │   └── ...
    └── analysis.json             # Document-level analysis
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

def ensure_deps():
    """Check that required packages are available."""
    missing = []
    for pkg in ['pypdfium2', 'pdfplumber', 'PIL', 'pytesseract']:
        try:
            __import__(pkg if pkg != 'PIL' else 'PIL.Image')
        except ImportError:
            missing.append(pkg.replace('PIL', 'Pillow'))
    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print(f"Install with: uv pip install {' '.join(missing)} --system")
        print(f"  or:         pip install {' '.join(missing)} --break-system-packages")
        sys.exit(1)

ensure_deps()

import pypdfium2 as pdfium
import pdfplumber
import pytesseract
from PIL import Image
import numpy as np


def render_pages(pdf_path, output_dir, dpi=300):
    """Render all pages as high-res PNGs."""
    pages_dir = os.path.join(output_dir, "pages")
    os.makedirs(pages_dir, exist_ok=True)

    pdf = pdfium.PdfDocument(pdf_path)
    scale = dpi / 72
    paths = []

    for i in range(len(pdf)):
        page = pdf[i]
        bitmap = page.render(scale=scale)
        img = bitmap.to_pil()
        path = os.path.join(pages_dir, f"page_{i+1:03d}.png")
        img.save(path, "PNG")
        paths.append(path)
        w_pts, h_pts = page.get_width(), page.get_height()
        print(f"  Page {i+1}: {img.size[0]}x{img.size[1]}px "
              f"({w_pts:.0f}x{h_pts:.0f}pt)")

    return paths


def detect_bg_color(image_path):
    """Detect dominant background color by sampling edges."""
    img = Image.open(image_path).convert('RGB')
    w, h = img.size
    samples = []
    for x, y in [(5, 5), (w-5, 5), (5, h-5), (w-5, h-5),
                  (w//4, 5), (3*w//4, 5), (w//4, h-5), (3*w//4, h-5),
                  (w//2, 5), (w//2, h-5), (5, h//4), (5, 3*h//4),
                  (w-5, h//4), (w-5, 3*h//4)]:
        x, y = min(x, w-1), min(y, h-1)
        samples.append(img.getpixel((x, y)))
    return Counter(samples).most_common(1)[0][0]


def is_digital_pdf(pdf_path):
    """Check if the PDF has extractable text (digital) or is scanned."""
    with pdfplumber.open(pdf_path) as pdf:
        total_chars = 0
        pages_checked = min(3, len(pdf.pages))
        for page in pdf.pages[:pages_checked]:
            total_chars += len(page.chars)
        return total_chars > (pages_checked * 50)  # >50 chars/page = digital


def extract_digital_regions(pdf_path, page_idx):
    """Extract text regions from a digital PDF page using pdfplumber."""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_idx]
        words = page.extract_words(keep_blank_chars=True,
                                     x_tolerance=3, y_tolerance=3)
        tables = page.find_tables()
        images = page.images

        # Group words into lines
        lines = defaultdict(list)
        for w in words:
            # Round top to nearest 2pt for line grouping
            line_key = round(w['top'] / 2) * 2
            lines[line_key].append(w)

        # Build text blocks from consecutive lines
        regions = []
        for line_top in sorted(lines.keys()):
            line_words = sorted(lines[line_top], key=lambda w: w['x0'])
            text = ' '.join(w['text'] for w in line_words)

            x0 = min(w['x0'] for w in line_words)
            y0 = min(w['top'] for w in line_words)
            x1 = max(w['x1'] for w in line_words)
            y1 = max(w['bottom'] for w in line_words)

            font_sizes = [w.get('size', 10) for w in line_words
                          if 'size' in w]
            avg_size = sum(font_sizes) / len(font_sizes) if font_sizes else 10

            regions.append({
                'text': text,
                'x0': round(x0, 1),
                'y0': round(y0, 1),
                'x1': round(x1, 1),
                'y1': round(y1, 1),
                'width': round(x1 - x0, 1),
                'height': round(y1 - y0, 1),
                'font_size': round(avg_size, 1),
                'type': 'text',
                'source': 'pdfplumber',
            })

        # Add table info
        table_regions = []
        for t_idx, table in enumerate(tables):
            bbox = table.bbox
            extracted = table.extract()
            table_regions.append({
                'x0': round(bbox[0], 1),
                'y0': round(bbox[1], 1),
                'x1': round(bbox[2], 1),
                'y1': round(bbox[3], 1),
                'width': round(bbox[2] - bbox[0], 1),
                'height': round(bbox[3] - bbox[1], 1),
                'type': 'table',
                'table_index': t_idx,
                'rows': len(extracted) if extracted else 0,
                'data': extracted,
                'source': 'pdfplumber',
            })

        # Add image info
        image_regions = []
        for img in images:
            image_regions.append({
                'x0': round(img['x0'], 1),
                'y0': round(img['y0'], 1),
                'x1': round(img['x1'], 1),
                'y1': round(img['y1'], 1),
                'width': round(img['x1'] - img['x0'], 1),
                'height': round(img['y1'] - img['y0'], 1),
                'type': 'image',
                'source': 'pdfplumber',
            })

        return {
            'text_regions': regions,
            'table_regions': table_regions,
            'image_regions': image_regions,
            'page_width': round(page.width, 1),
            'page_height': round(page.height, 1),
        }


def extract_ocr_regions(image_path, lang='fra', dpi=300, min_conf=30):
    """Extract text regions from a page image using Tesseract OCR."""
    img = Image.open(image_path)
    data = pytesseract.image_to_data(img, lang=lang,
                                       output_type=pytesseract.Output.DICT)

    # Group into blocks
    blocks = defaultdict(list)
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        conf = int(data['conf'][i])
        if text and conf >= min_conf:
            key = (data['block_num'][i], data['par_num'][i])
            blocks[key].append({
                'text': text,
                'x': data['left'][i],
                'y': data['top'][i],
                'width': data['width'][i],
                'height': data['height'][i],
                'conf': conf,
                'line_num': data['line_num'][i],
                'word_num': data['word_num'][i],
            })

    regions = []
    for (block_num, par_num), words in blocks.items():
        # Sort by line, then x position
        words.sort(key=lambda w: (w['line_num'], w['x']))

        # Build text by line
        lines_dict = defaultdict(list)
        for w in words:
            lines_dict[w['line_num']].append(w['text'])
        full_text = '\n'.join(' '.join(lines_dict[ln])
                               for ln in sorted(lines_dict.keys()))

        # Bounding box in pixels
        x0 = min(w['x'] for w in words)
        y0 = min(w['y'] for w in words)
        x1 = max(w['x'] + w['width'] for w in words)
        y1 = max(w['y'] + w['height'] for w in words)
        avg_conf = sum(w['conf'] for w in words) / len(words)

        # Convert to PDF points
        px_to_pt = 72.0 / dpi

        regions.append({
            'text': full_text,
            'x0_px': x0,
            'y0_px': y0,
            'x1_px': x1,
            'y1_px': y1,
            'x0': round(x0 * px_to_pt, 1),
            'y0': round(y0 * px_to_pt, 1),
            'x1': round(x1 * px_to_pt, 1),
            'y1': round(y1 * px_to_pt, 1),
            'width': round((x1 - x0) * px_to_pt, 1),
            'height': round((y1 - y0) * px_to_pt, 1),
            'avg_confidence': round(avg_conf, 1),
            'word_count': len(words),
            'line_count': len(lines_dict),
            'type': 'text',
            'source': 'ocr',
        })

    return regions


def find_headers_footers(all_page_regions, page_height, tolerance=10):
    """Identify text that repeats across pages (likely headers/footers)."""
    text_positions = defaultdict(list)

    for page_idx, regions in enumerate(all_page_regions):
        text_entries = [r for r in regions if r['type'] == 'text']
        for r in text_entries:
            # Normalize position
            y_bucket = round(r['y0'] / tolerance) * tolerance
            text_positions[(y_bucket, r['text'])].append(page_idx)

    threshold = len(all_page_regions) * 0.4
    headers_footers = []
    for (y_pos, text), pages in text_positions.items():
        if len(pages) >= threshold:
            is_header = y_pos < page_height * 0.15
            is_footer = y_pos > page_height * 0.85
            if is_header or is_footer:
                headers_footers.append({
                    'text': text,
                    'y_position': y_pos,
                    'role': 'header' if is_header else 'footer',
                    'appears_on_pages': pages,
                })

    return headers_footers


def extract_embedded_images(pdf_path, output_dir):
    """Extract embedded images from the PDF."""
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    try:
        import subprocess
        result = subprocess.run(
            ['pdfimages', '-j', pdf_path, os.path.join(images_dir, 'img')],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            extracted = list(Path(images_dir).glob('img-*'))
            print(f"  Extracted {len(extracted)} embedded images")
            return [str(p) for p in extracted]
    except FileNotFoundError:
        print("  pdfimages not found, skipping embedded image extraction")

    return []


def main():
    parser = argparse.ArgumentParser(description='Extract page elements for translation')
    parser.add_argument('input_pdf', help='Path to input PDF')
    parser.add_argument('output_dir', help='Output directory')
    parser.add_argument('--dpi', type=int, default=300, help='Render DPI (default: 300)')
    parser.add_argument('--lang', default='fra', help='OCR language (default: fra)')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Analyzing: {args.input_pdf}")

    # Check if digital or scanned
    digital = is_digital_pdf(args.input_pdf)
    print(f"  Document type: {'Digital (text-based)' if digital else 'Scanned (image-based)'}")

    # Get page count
    pdf = pdfium.PdfDocument(args.input_pdf)
    page_count = len(pdf)
    print(f"  Pages: {page_count}")

    # Render all pages
    print("Rendering pages...")
    page_images = render_pages(args.input_pdf, args.output_dir, dpi=args.dpi)

    # Detect background colors
    print("Detecting background colors...")
    bg_colors = []
    for img_path in page_images:
        color = detect_bg_color(img_path)
        bg_colors.append(list(color))
        is_white = all(c > 240 for c in color)
        if not is_white:
            print(f"  {os.path.basename(img_path)}: bg=RGB{color} (non-white!)")

    # Extract text regions for each page
    print("Extracting text regions...")
    all_regions = []
    for i in range(page_count):
        if digital:
            data = extract_digital_regions(args.input_pdf, i)
            regions = data['text_regions'] + data['table_regions'] + data['image_regions']
        else:
            regions = extract_ocr_regions(page_images[i], lang=args.lang, dpi=args.dpi)

        all_regions.append(regions)

        # Save per-page region data
        region_path = page_images[i].replace('.png', '_regions.json')
        with open(region_path, 'w', encoding='utf-8') as f:
            json.dump(regions, f, indent=2, ensure_ascii=False)

        text_count = len([r for r in regions if r['type'] == 'text'])
        print(f"  Page {i+1}: {text_count} text regions")

    # Find headers/footers
    page_height = pdf[0].get_height()
    headers_footers = find_headers_footers(all_regions, page_height)
    if headers_footers:
        print(f"Detected {len(headers_footers)} header/footer elements:")
        for hf in headers_footers:
            print(f"  [{hf['role']}] \"{hf['text'][:50]}...\"")

    # Extract embedded images
    print("Extracting embedded images...")
    embedded_images = extract_embedded_images(args.input_pdf, args.output_dir)

    # Build analysis summary
    analysis = {
        'source_file': os.path.basename(args.input_pdf),
        'page_count': page_count,
        'is_digital': digital,
        'dpi': args.dpi,
        'ocr_language': args.lang,
        'background_colors': bg_colors,
        'all_white_background': all(all(c > 240 for c in bg) for bg in bg_colors),
        'headers_footers': headers_footers,
        'embedded_image_count': len(embedded_images),
        'pages': [],
    }

    for i, regions in enumerate(all_regions):
        page_info = {
            'page_number': i + 1,
            'image_path': page_images[i],
            'text_region_count': len([r for r in regions if r['type'] == 'text']),
            'table_count': len([r for r in regions if r['type'] == 'table']),
            'image_count': len([r for r in regions if r['type'] == 'image']),
            'background_color': bg_colors[i],
        }
        if not digital:
            confs = [r.get('avg_confidence', 0) for r in regions if r['type'] == 'text']
            page_info['avg_ocr_confidence'] = round(sum(confs) / len(confs), 1) if confs else 0
        analysis['pages'].append(page_info)

    analysis_path = os.path.join(args.output_dir, 'analysis.json')
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    print(f"\nAnalysis complete. Results in: {args.output_dir}")
    print(f"  analysis.json — document-level summary")
    print(f"  pages/         — rendered pages + region data")
    if embedded_images:
        print(f"  images/        — {len(embedded_images)} extracted images")


if __name__ == '__main__':
    main()
