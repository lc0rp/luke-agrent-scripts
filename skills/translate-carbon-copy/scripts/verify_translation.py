#!/usr/bin/env python3
"""
Verify a translated PDF against the original by producing side-by-side comparison images.

Usage:
    python verify_translation.py <original.pdf> <translated.pdf> <output_dir> [--dpi 150]

Produces:
    output_dir/
    ├── comparison_page_001.png   # Side-by-side original vs translated
    ├── comparison_page_002.png
    └── verification_report.json  # Automated check results
"""

import argparse
import json
import os
import sys

def ensure_deps():
    missing = []
    for pkg in ['pypdfium2', 'PIL', 'pypdf']:
        try:
            __import__(pkg if pkg != 'PIL' else 'PIL.Image')
        except ImportError:
            missing.append(pkg.replace('PIL', 'Pillow'))
    if missing:
        print(f"Missing: {', '.join(missing)}")
        sys.exit(1)

ensure_deps()

import pypdfium2 as pdfium
from pypdf import PdfReader
from PIL import Image, ImageDraw, ImageFont


def render_pdf_pages(pdf_path, dpi=150):
    """Render all pages of a PDF as PIL images."""
    pdf = pdfium.PdfDocument(pdf_path)
    scale = dpi / 72
    images = []
    for i in range(len(pdf)):
        bitmap = pdf[i].render(scale=scale)
        images.append(bitmap.to_pil())
    return images


def create_comparison(orig_img, trans_img, page_num):
    """Create a side-by-side comparison image with labels."""
    # Resize to same height if different
    target_h = max(orig_img.height, trans_img.height)
    if orig_img.height != target_h:
        scale = target_h / orig_img.height
        orig_img = orig_img.resize((int(orig_img.width * scale), target_h))
    if trans_img.height != target_h:
        scale = target_h / trans_img.height
        trans_img = trans_img.resize((int(trans_img.width * scale), target_h))

    gap = 20
    label_h = 30
    w = orig_img.width + trans_img.width + gap
    h = target_h + label_h

    comp = Image.new('RGB', (w, h), (240, 240, 240))
    draw = ImageDraw.Draw(comp)

    # Labels
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except Exception:
        font = ImageFont.load_default()

    draw.text((orig_img.width // 2 - 40, 5), f"ORIGINAL (p.{page_num})",
              fill=(0, 0, 0), font=font)
    draw.text((orig_img.width + gap + trans_img.width // 2 - 50, 5),
              f"TRANSLATED (p.{page_num})", fill=(0, 100, 0), font=font)

    # Paste images
    comp.paste(orig_img, (0, label_h))
    comp.paste(trans_img, (orig_img.width + gap, label_h))

    return comp


def verify_page_count(orig_path, trans_path):
    """Check that page counts are consistent."""
    orig_reader = PdfReader(orig_path)
    trans_reader = PdfReader(trans_path)
    orig_count = len(orig_reader.pages)
    trans_count = len(trans_reader.pages)
    return {
        'check': 'page_count',
        'passed': trans_count >= orig_count,
        'original_pages': orig_count,
        'translated_pages': trans_count,
        'overflow_pages': max(0, trans_count - orig_count),
        'note': ('OK' if trans_count == orig_count else
                 f'{trans_count - orig_count} overflow pages added' if trans_count > orig_count else
                 f'MISSING {orig_count - trans_count} pages!')
    }


def verify_file_valid(trans_path):
    """Check that the translated PDF is valid and readable."""
    try:
        reader = PdfReader(trans_path)
        _ = len(reader.pages)
        # Try reading each page
        for page in reader.pages:
            _ = page.mediabox
        return {'check': 'file_valid', 'passed': True, 'note': 'OK'}
    except Exception as e:
        return {'check': 'file_valid', 'passed': False, 'note': str(e)}


def main():
    parser = argparse.ArgumentParser(description='Verify translated PDF')
    parser.add_argument('original', help='Original PDF')
    parser.add_argument('translated', help='Translated PDF')
    parser.add_argument('output_dir', help='Output directory for comparisons')
    parser.add_argument('--dpi', type=int, default=150, help='Comparison render DPI')
    parser.add_argument('--pages', help='Specific pages to compare (e.g., "1,3,5" or "1-5")')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Verifying translation:")
    print(f"  Original:   {args.original}")
    print(f"  Translated: {args.translated}")

    # Automated checks
    checks = []
    checks.append(verify_file_valid(args.translated))
    checks.append(verify_page_count(args.original, args.translated))

    for check in checks:
        status = "PASS" if check['passed'] else "FAIL"
        print(f"  [{status}] {check['check']}: {check['note']}")

    # Render comparison images
    print(f"\nRendering comparisons at {args.dpi} DPI...")
    orig_images = render_pdf_pages(args.original, dpi=args.dpi)
    trans_images = render_pdf_pages(args.translated, dpi=args.dpi)

    # Determine which pages to compare
    if args.pages:
        if '-' in args.pages:
            start, end = args.pages.split('-')
            page_indices = list(range(int(start)-1, int(end)))
        else:
            page_indices = [int(p)-1 for p in args.pages.split(',')]
    else:
        page_indices = list(range(min(len(orig_images), len(trans_images))))

    comparison_paths = []
    for i in page_indices:
        if i < len(orig_images) and i < len(trans_images):
            comp = create_comparison(orig_images[i], trans_images[i], i+1)
            path = os.path.join(args.output_dir, f"comparison_page_{i+1:03d}.png")
            comp.save(path)
            comparison_paths.append(path)
            print(f"  Saved: {os.path.basename(path)}")

    # Save report
    report = {
        'original_file': os.path.basename(args.original),
        'translated_file': os.path.basename(args.translated),
        'checks': checks,
        'comparisons': comparison_paths,
        'all_checks_passed': all(c['passed'] for c in checks),
    }

    report_path = os.path.join(args.output_dir, 'verification_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    all_passed = all(c['passed'] for c in checks)
    print(f"\n{'ALL CHECKS PASSED' if all_passed else 'SOME CHECKS FAILED'}")
    print(f"Report: {report_path}")
    print(f"Comparisons: {len(comparison_paths)} pages in {args.output_dir}/")
    print(f"\nManual review checklist:")
    print(f"  [ ] Logos/branding visible and undamaged")
    print(f"  [ ] Signatures and stamps visible and not covered")
    print(f"  [ ] Headers and footers translated")
    print(f"  [ ] Table headers translated")
    print(f"  [ ] All body text translated")
    print(f"  [ ] Background color of overlays matches original")
    print(f"  [ ] Font sizes are readable")
    print(f"  [ ] Page numbers preserved")


if __name__ == '__main__':
    main()
