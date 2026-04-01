# Technical Guide — Translate-in-Place

Advanced techniques for layout-preserving document translation.

## Table of Contents

1. [OCR Text Region Extraction with Bounding Boxes](#ocr-text-region-extraction)
2. [Text Block Grouping](#text-block-grouping)
3. [Font Detection and Matching](#font-detection-and-matching)
4. [Table Detection and Translation](#table-detection-and-translation)
5. [Multi-Column Layout Handling](#multi-column-layout-handling)
6. [Overlay Color Calibration](#overlay-color-calibration)
7. [Handling Rotated or Skewed Text](#handling-rotated-text)
8. [Large Document Optimization](#large-document-optimization)
9. [Troubleshooting Common Issues](#troubleshooting)

---

## OCR Text Region Extraction

When working with scanned documents, you need word-level bounding boxes from Tesseract
to know where to place overlay rectangles and translated text.

```python
import pytesseract
from PIL import Image

def extract_text_regions(image_path, lang='fra', min_confidence=40):
    """
    Extract text with bounding boxes from a page image.
    Returns a list of word-level entries with position and text.
    """
    img = Image.open(image_path)
    data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)

    regions = []
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        conf = int(data['conf'][i])
        if text and conf >= min_confidence:
            regions.append({
                'text': text,
                'x': data['left'][i],
                'y': data['top'][i],
                'width': data['width'][i],
                'height': data['height'][i],
                'confidence': conf,
                'block_num': data['block_num'][i],
                'par_num': data['par_num'][i],
                'line_num': data['line_num'][i],
                'word_num': data['word_num'][i],
            })
    return regions
```

### Converting OCR Pixel Coordinates to PDF Points

OCR works in pixel space (from the rendered image), but PDF overlay coordinates are in
points (1 point = 1/72 inch). You need to convert:

```python
def pixels_to_points(px_value, dpi):
    """Convert pixel coordinate to PDF points."""
    return px_value * 72.0 / dpi

def convert_region_coords(region, dpi, pdf_page_height):
    """
    Convert an OCR region from pixel/top-left-origin to PDF points/bottom-left-origin.
    PDF coordinate system has (0,0) at bottom-left with y going up.
    """
    x_pt = pixels_to_points(region['x'], dpi)
    y_px = region['y']
    w_pt = pixels_to_points(region['width'], dpi)
    h_pt = pixels_to_points(region['height'], dpi)

    # PDF y-coordinate: flip from top-origin to bottom-origin
    y_pt = pdf_page_height - pixels_to_points(y_px + region['height'], dpi)

    return {
        'x': x_pt,
        'y': y_pt,  # Bottom-left corner in PDF coords
        'width': w_pt,
        'height': h_pt,
        'text': region['text']
    }
```

---

## Text Block Grouping

Individual OCR words need to be grouped into logical text blocks for coherent translation.
Translating word-by-word produces nonsense; translating paragraph-by-paragraph produces
accurate translations that can be reflowed.

```python
def group_words_into_blocks(regions):
    """
    Group OCR words into text blocks based on Tesseract's block/paragraph structure.
    Returns blocks with combined text and bounding box.
    """
    from collections import defaultdict
    blocks = defaultdict(list)

    for r in regions:
        key = (r['block_num'], r['par_num'])
        blocks[key].append(r)

    result = []
    for key, words in blocks.items():
        # Sort by line, then by x position
        words.sort(key=lambda w: (w['line_num'], w['x']))

        # Combine text by line
        lines = defaultdict(list)
        for w in words:
            lines[w['line_num']].append(w['text'])
        full_text = '\n'.join(' '.join(lines[ln]) for ln in sorted(lines.keys()))

        # Bounding box of the entire block
        x0 = min(w['x'] for w in words)
        y0 = min(w['y'] for w in words)
        x1 = max(w['x'] + w['width'] for w in words)
        y1 = max(w['y'] + w['height'] for w in words)

        result.append({
            'text': full_text,
            'x': x0,
            'y': y0,
            'width': x1 - x0,
            'height': y1 - y0,
            'word_count': len(words),
            'line_count': len(lines),
        })

    return result
```

---

## Font Detection and Matching

For digital PDFs, you can detect the font used in the original and try to match it:

```python
import pdfplumber

def detect_fonts(pdf_path):
    """Detect fonts used in the document and their approximate sizes."""
    fonts = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for char in page.chars:
                font = char.get('fontname', 'Unknown')
                size = round(char.get('size', 10), 1)
                key = (font, size)
                fonts[key] = fonts.get(key, 0) + 1
    # Sort by frequency
    return sorted(fonts.items(), key=lambda x: -x[1])
```

### Common Font Mappings

When the original font isn't available, use these reportlab equivalents:

| Original Font Family | Reportlab Equivalent |
|---------------------|---------------------|
| Arial, Helvetica, sans-serif | Helvetica |
| Times, Times New Roman, serif | Times-Roman |
| Courier, monospace | Courier |
| Calibri, modern sans | Helvetica |
| Garamond, Book Antiqua | Times-Roman |

For bold/italic variants, reportlab uses naming conventions:
- `Helvetica-Bold`, `Helvetica-Oblique`, `Helvetica-BoldOblique`
- `Times-Bold`, `Times-Italic`, `Times-BoldItalic`
- `Courier-Bold`, `Courier-Oblique`, `Courier-BoldOblique`

---

## Table Detection and Translation

Tables require special handling because their text is structured in cells.

```python
import pdfplumber

def extract_and_translate_tables(pdf_path, translate_fn):
    """
    Extract tables, translate cell contents, return structured data.
    translate_fn(text) -> translated_text
    """
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            tables = page.find_tables()
            for table_idx, table in enumerate(tables):
                extracted = table.extract()
                bbox = table.bbox  # (x0, y0, x1, y1)

                translated_rows = []
                for row in extracted:
                    translated_row = []
                    for cell in row:
                        if cell and cell.strip():
                            translated_row.append(translate_fn(cell.strip()))
                        else:
                            translated_row.append(cell)
                    translated_rows.append(translated_row)

                results.append({
                    'page': page_idx,
                    'table_index': table_idx,
                    'bbox': bbox,
                    'original': extracted,
                    'translated': translated_rows,
                })
    return results
```

### Drawing Translated Tables

```python
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

def draw_table_on_canvas(canvas_obj, translated_rows, x, y, width, height,
                          font_name='Helvetica', font_size=8):
    """Draw a translated table at the specified position on a reportlab canvas."""
    if not translated_rows or not any(translated_rows):
        return

    col_count = max(len(row) for row in translated_rows)
    col_width = width / col_count if col_count > 0 else width

    # Clean data
    clean_rows = []
    for row in translated_rows:
        clean_row = [str(cell) if cell else '' for cell in row]
        # Pad if needed
        while len(clean_row) < col_count:
            clean_row.append('')
        clean_rows.append(clean_row)

    t = Table(clean_rows, colWidths=[col_width] * col_count)
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), font_size),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), f'{font_name}-Bold'),  # Bold header row
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    t.wrapOn(canvas_obj, width, height)
    t.drawOn(canvas_obj, x, y)
```

---

## Multi-Column Layout Handling

Some documents use multi-column layouts. Detect columns by analyzing the x-distribution
of text blocks:

```python
def detect_columns(text_blocks, page_width, gap_threshold=50):
    """
    Detect if a page uses multi-column layout.
    Returns column boundaries as list of (x_start, x_end) tuples.
    """
    import numpy as np

    # Get x-centers of all blocks
    x_centers = [b['x'] + b['width'] / 2 for b in text_blocks]
    if len(x_centers) < 3:
        return [(0, page_width)]  # Single column

    # Look for gaps in x-distribution
    x_sorted = sorted(set(int(x) for x in x_centers))
    gaps = []
    for i in range(1, len(x_sorted)):
        if x_sorted[i] - x_sorted[i-1] > gap_threshold:
            gaps.append((x_sorted[i-1], x_sorted[i]))

    if not gaps:
        return [(0, page_width)]

    # Build column boundaries
    columns = [(0, gaps[0][0])]
    for i in range(len(gaps) - 1):
        columns.append((gaps[i][1], gaps[i+1][0]))
    columns.append((gaps[-1][1], page_width))

    return columns
```

---

## Overlay Color Calibration

For pages with non-white backgrounds, precise color matching is essential.

```python
from PIL import Image
import numpy as np

def analyze_background_regions(image_path, text_regions):
    """
    For each text region, sample the surrounding pixels to get the local
    background color. This handles documents where background color varies
    across the page (e.g., alternating table row colors).
    """
    img = np.array(Image.open(image_path).convert('RGB'))
    colors = []

    for region in text_regions:
        x, y, w, h = region['x'], region['y'], region['width'], region['height']
        # Sample pixels just outside the text region
        samples = []
        # Above
        if y > 2:
            samples.extend(img[max(0,y-3):y, x:x+w].reshape(-1, 3).tolist())
        # Below
        if y + h + 3 < img.shape[0]:
            samples.extend(img[y+h:y+h+3, x:x+w].reshape(-1, 3).tolist())

        if samples:
            # Median color (robust to outliers)
            median_color = tuple(int(np.median([s[c] for s in samples])) for c in range(3))
            colors.append(median_color)
        else:
            colors.append((255, 255, 255))  # Default white

    return colors
```

---

## Handling Rotated Text

Some documents have rotated text (e.g., vertical sidebar labels, watermarks).

```python
def draw_rotated_text(canvas_obj, text, x, y, angle, font_name='Helvetica', font_size=10):
    """Draw text at an angle on a reportlab canvas."""
    canvas_obj.saveState()
    canvas_obj.translate(x, y)
    canvas_obj.rotate(angle)
    canvas_obj.setFont(font_name, font_size)
    canvas_obj.drawString(0, 0, text)
    canvas_obj.restoreState()
```

---

## Large Document Optimization

For documents with many pages (20+), optimize processing time:

### Parallel Page Processing

```python
from concurrent.futures import ThreadPoolExecutor
import pypdfium2 as pdfium

def render_pages_parallel(pdf_path, output_dir, dpi=300, max_workers=4):
    """Render PDF pages to images in parallel."""
    pdf = pdfium.PdfDocument(pdf_path)
    scale = dpi / 72

    def render_page(i):
        page = pdf[i]
        bitmap = page.render(scale=scale)
        img = bitmap.to_pil()
        path = f"{output_dir}/page_{i+1}.png"
        img.save(path)
        return path

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(render_page, i) for i in range(len(pdf))]
        return [f.result() for f in futures]
```

### Batch OCR

```python
def batch_ocr(image_paths, lang='fra', max_workers=4):
    """Run OCR on multiple page images in parallel."""
    from concurrent.futures import ThreadPoolExecutor
    import pytesseract
    from PIL import Image

    def ocr_page(path):
        img = Image.open(path)
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
        return data

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(ocr_page, p) for p in image_paths]
        return [f.result() for f in futures]
```

---

## Troubleshooting

### Problem: Overlay rectangles are visible (color mismatch)

**Cause:** Background color detection sampled the wrong area, or the background has a
gradient/pattern.

**Fix:** Use `analyze_background_regions()` for per-region color matching, or whiten the
entire background first with `whiten_background()`.

### Problem: Translated text overflows its bounding box

**Cause:** English text is typically 15-30% longer than French for the same content.

**Fix:** Reduce font size by 10-15%, or enable the magnification+overflow system described
in the main SKILL.md. For tables, consider abbreviating column headers.

### Problem: OCR misreads characters

**Cause:** Low resolution scan, unusual fonts, or heavy compression.

**Fix:** Re-render at higher DPI (400+), apply image preprocessing (sharpen, contrast
enhancement), or use `--psm` Tesseract options:
```python
# For single column of text
config = '--psm 4 --oem 3'
data = pytesseract.image_to_data(img, lang='fra', config=config, output_type=pytesseract.Output.DICT)
```

### Problem: Signatures or stamps got covered by overlay

**Cause:** The text region detection included the signature area.

**Fix:** Filter out low-confidence OCR regions (< 50% confidence), and manually exclude
known signature zones by coordinate ranges. Signatures are usually in the bottom third of
pages and near explicit signature labels.

### Problem: Headers/footers not translated

**Cause:** They were treated as page chrome rather than content.

**Fix:** Use `find_repeated_text()` from the main SKILL.md to detect them, then apply
translated overlays at those positions on every page.
