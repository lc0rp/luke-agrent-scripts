---
name: translate-carbon-copy
description: >
  Translate documents (especially PDFs) from one language to another while preserving the exact
  visual layout, images, logos, signatures, stamps, handwritten names/dates, headers, footers, and
  formatting of the original. Produces a faithful visual reproduction where only the text content is
  translated. Use this skill whenever the user asks to translate a document, PDF, scanned file, or
  contract and wants the translation to look like the original — not a plain-text rewrite. Also use
  when the user mentions "translate in place", "translate keeping formatting", "translate this PDF",
  "translate preserving layout", or wants a translated version of any document that contains images,
  signatures, logos, tables, or other visual elements. Trigger even if the user just says "translate
  this file" and the file is a PDF or scanned document, since layout-preserving translation is almost
  always what people want for formal documents.
---

# Translate-carbon-copy

Produce an accurate translated reproduction of a document, keeping images, headers, footers,
logos, handwritten names, dates, signatures, and stamps exactly where they appear in the
original. Only the translatable text changes — everything else stays.

## Core Principle

The original document is the ground truth for layout. Every page of the output should be
visually recognizable as "the same document, but in [target language]." A reader who puts
the original and translation side-by-side should see the same structure, colors, and visual
elements, with only the language of the text differing.

---

## Workflow Overview

```
1. Analyze  →  2. Extract  →  3. Translate  →  4. Compose  →  5. Verify
```

Each step is described below. Read the full workflow before writing any code — the approach
you choose in step 1 determines everything else.

---

## Step 1 — Analyze the Source Document

Before touching any code, classify the document:

| Property | How to check | Why it matters |
|----------|-------------|----------------|
| Digital vs. scanned | `pdfplumber`: if `page.chars` is empty on most pages, it's scanned | Determines extraction method |
| Page count | `len(PdfReader(f).pages)` | Affects whether to parallelize |
| Has images/logos | `pdfplumber`: `page.images`, or `pdfimages -list` | Must be preserved |
| Has signatures/stamps | Visual inspection of page images | Must be preserved as images |
| Background color | Render a page and sample pixels | Overlay color must match |
| Headers/footers | Check for repeated text at top/bottom across pages | Must be translated |
| Tables | `pdfplumber`: `page.find_tables()` | Table headers need translation |
| Text density | Characters per page | Affects magnification strategy |

**Render preview images first.** Convert the first 2–3 pages to PNG at 200 DPI and visually
inspect them. This five-minute investment prevents wrong assumptions:

```python
import pypdfium2 as pdfium
pdf = pdfium.PdfDocument("input.pdf")
for i in range(min(3, len(pdf))):
    page = pdf[i]
    bitmap = page.render(scale=200/72)  # 200 DPI
    bitmap.to_pil().save(f"preview_page_{i+1}.png")
```

---

## Step 2 — Extract Page Elements

There are two extraction strategies. Choose based on the analysis above.

### Strategy A: Page-as-Background (preferred for most documents)

Best for: scanned documents, documents with complex layouts, signatures, stamps,
watermarks, or any document where preserving exact visual fidelity matters most.

**How it works:** Render each original page as a high-resolution image. This image becomes
the background of the translated page. You then cover the original text regions with
background-colored rectangles and write the translated text on top.

This is the default strategy because it guarantees that every visual element (logos,
signatures, stamps, watermarks, decorative borders, background patterns) is preserved
exactly — they're literally part of the background image.

```
Original page image (background)
  └─ Background-colored rectangles over text regions
       └─ Translated text drawn on top
```

### Strategy B: Structural Rebuild

Best for: text-heavy digital PDFs with simple layouts (reports, policies, manuals) where
you want crisp, searchable text output and the original has no scanned elements.

**How it works:** Extract text, formatting metadata, and images separately, then rebuild the
page from scratch using reportlab. Images and logos are extracted and re-placed at their
original coordinates.

Use this only when the document is fully digital (all text is selectable), has a
straightforward layout, and contains no handwritten elements.

### Extracting Images, Logos, and Signatures

Regardless of strategy, extract embedded images for reuse or reference:

```bash
# Extract all images from the PDF
pdfimages -j input.pdf extracted_images/img
# This produces img-000.jpg, img-001.png, etc.
```

For scanned documents where signatures/stamps are part of the page image (not separate
embedded images), you'll preserve them automatically with Strategy A. No separate
extraction is needed — they're part of the background.

For digital PDFs where logos are embedded objects, extract them so you can place them in
the rebuilt document:

```python
import pdfplumber
with pdfplumber.open("input.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        for j, img in enumerate(page.images):
            # img has: x0, y0, x1, y1, width, height
            # Use these coordinates to place the image in the output
            print(f"Page {i+1}, Image {j+1}: {img}")
```

---

## Step 3 — Translate the Text

### Text Extraction

**For digital PDFs:**
```python
import pdfplumber
with pdfplumber.open("input.pdf") as pdf:
    for page in pdf.pages:
        # Get text with position info for overlay placement
        words = page.extract_words(keep_blank_chars=True,
                                     x_tolerance=3, y_tolerance=3)
        # Each word has: text, x0, y0, x1, y1, top, bottom

        # Also extract tables separately for structured translation
        tables = page.extract_tables()
```

**For scanned PDFs (OCR):**
```python
import pytesseract
from pdf2image import convert_from_path

images = convert_from_path("input.pdf", dpi=300)
for i, img in enumerate(images):
    # Get word-level bounding boxes for overlay positioning
    data = pytesseract.image_to_data(img, lang='fra', output_type=pytesseract.Output.DICT)
    # data contains: text, left, top, width, height, conf for each word
```

Use `lang='fra'` for French (or the appropriate Tesseract language code for the source
language). If OCR confidence is low, increase DPI or apply image preprocessing.

### Translation Guidelines

Translate with these priorities:

1. **Accuracy first.** Legal, financial, and regulatory terminology must be precise.
   Use established English equivalents for domain-specific terms (e.g., LCB-FT → AML-CFT).

2. **Preserve proper nouns.** Entity names, addresses, registration numbers, regulatory
   reference numbers, currency codes (FCFA, CFA), and tool/software names stay unchanged.

3. **Translate everything visible.** Body text, headers, footers, table headers, bullet
   points, captions, watermark text, page titles — if a human reader would read it, translate it.

4. **Keep acronyms usable.** At first occurrence, give the English expansion. Keep the
   original acronym if it's an official name (e.g., BCEAO, CENTIF, TRACFIN).

5. **Headers and footers.** These are often missed. Identify repeated text at the top/bottom
   of pages and translate it consistently across all pages.

### Magnification Factor

When source text is very small (common in scanned documents, footnotes, or dense tables),
the translated text may not be readable at the same font size — especially since English
text is often longer than French or other Romance languages.

**Apply a magnification factor when needed:**

- Default: 1.0× (same size as original)
- For small text (< 7pt equivalent): try 1.2–1.5×
- For very dense tables: try 1.1–1.3×

If magnified text overflows its original bounding box, allow it to flow into additional space:

1. First, try expanding the text box downward within the same page
2. If the page is full, allow overflow onto a continuation page (insert a new page after the
   current one, marked "[continued]" or similar)
3. In the translation notes, document which pages required magnification and overflow

```python
# Example: calculating whether text fits and needs magnification
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth

def text_fits(text, font_name, font_size, max_width):
    """Check if text fits within the given width."""
    w = stringWidth(text, font_name, font_size)
    return w <= max_width

def find_fitting_size(text, font_name, target_size, max_width, min_size=6):
    """Find the largest font size that fits, down to min_size."""
    size = target_size
    while size >= min_size:
        if text_fits(text, font_name, size, max_width):
            return size
        size -= 0.5
    return min_size  # Use minimum and let it overflow if needed
```

---

## Step 4 — Compose the Translated PDF

### Strategy A Implementation: Page-as-Background with Overlay

This is the recommended approach. Here is the full pattern:

```python
import pypdfium2 as pdfium
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader, PdfWriter
from PIL import Image
import io

def create_translated_pdf(input_path, output_path, translations, bg_color=(255, 255, 255)):
    """
    translations: list of dicts, one per page, each containing:
        - regions: list of {x, y, width, height, text, font_size, font_name, alignment}
          where (x, y) is from top-left in PDF points
    bg_color: RGB tuple for overlay rectangles — MUST match original background
    """
    src_pdf = pdfium.PdfDocument(input_path)
    writer = PdfWriter()

    for page_idx in range(len(src_pdf)):
        page = src_pdf[page_idx]
        # Get page dimensions in points
        w_pts = page.get_width()
        h_pts = page.get_height()

        # Render page as high-res image
        scale = 300 / 72  # 300 DPI
        bitmap = page.render(scale=scale)
        pil_img = bitmap.to_pil()

        # Save as temporary image
        img_buffer = io.BytesIO()
        pil_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        # Create overlay PDF with reportlab
        overlay_buffer = io.BytesIO()
        c = canvas.Canvas(overlay_buffer, pagesize=(w_pts, h_pts))

        # Draw the original page as background image
        c.drawImage(
            img_buffer, 0, 0,
            width=w_pts, height=h_pts,
            preserveAspectRatio=True
        )

        # For each text region: cover with background color, then draw translated text
        if page_idx < len(translations):
            for region in translations[page_idx].get('regions', []):
                rx, ry = region['x'], region['y']
                rw, rh = region['width'], region['height']

                # Draw background-colored rectangle to cover original text
                r, g, b = bg_color
                c.setFillColorRGB(r/255, g/255, b/255)
                c.rect(rx, h_pts - ry - rh, rw, rh, fill=True, stroke=False)

                # Draw translated text
                c.setFillColorRGB(0, 0, 0)  # Black text (or match original)
                c.setFont(region.get('font_name', 'Helvetica'),
                          region.get('font_size', 10))

                # For multi-line text, use textobject
                text_obj = c.beginText(rx + 2, h_pts - ry - region.get('font_size', 10))
                for line in region['text'].split('\n'):
                    text_obj.textLine(line)
                c.drawText(text_obj)

        c.save()
        overlay_buffer.seek(0)

        # Add the overlay page to the writer
        overlay_reader = PdfReader(overlay_buffer)
        writer.add_page(overlay_reader.pages[0])

    with open(output_path, 'wb') as f:
        writer.write(f)
```

### Background Color Matching

The overlay rectangles that cover original text **must** match the background color of the
original document. A mismatched rectangle is immediately visible and looks terrible.

**How to detect background color:**

```python
from PIL import Image
import collections

def get_dominant_bg_color(page_image):
    """Sample the page image to find the dominant background color."""
    img = page_image.convert('RGB')
    # Sample from corners and edges (where background usually is)
    w, h = img.size
    samples = []
    for x, y in [(10, 10), (w-10, 10), (10, h-10), (w-10, h-10),
                  (w//2, 10), (w//2, h-10), (10, h//2), (w-10, h//2)]:
        samples.append(img.getpixel((x, y)))
    # Most common color is likely the background
    return collections.Counter(samples).most_common(1)[0][0]
```

**If the background is not white**, you have two options:

1. **Match it:** Use the detected color for overlay rectangles. This works well for
   light-colored backgrounds (cream, light gray, light blue).

2. **Whiten the background first:** Convert the entire page background to white before
   overlaying. This simplifies overlay matching and produces cleaner output. Use this when
   the background has noise, gradients, or inconsistent coloring:

```python
from PIL import Image
import numpy as np

def whiten_background(img, threshold=220):
    """Convert near-white/light pixels to pure white."""
    arr = np.array(img)
    # Pixels where all RGB channels are above threshold → white
    mask = np.all(arr > threshold, axis=2)
    arr[mask] = [255, 255, 255]
    return Image.fromarray(arr)
```

### Preserving Signatures and Handwritten Elements

With Strategy A, signatures, stamps, and handwritten text are automatically preserved
because they're part of the background image. The overlay rectangles should **avoid**
covering these areas.

When extracting text regions (via OCR or pdfplumber), filter out regions that overlap
with known signature/stamp areas. You can identify these by:

- Visual inspection of the preview images (most reliable)
- OCR confidence: handwritten text typically has low OCR confidence (< 60%)
- Position: signatures are usually at the bottom of pages or in designated signature blocks

### Headers and Footers

Identify headers and footers by looking for text that repeats across multiple pages at
consistent y-coordinates. Translate these and apply the translation consistently to every
page.

```python
def find_repeated_text(pages_words):
    """Find text that appears at similar positions across multiple pages."""
    from collections import Counter
    # Group words by approximate y-position (within 5pt tolerance)
    position_text = Counter()
    for page_words in pages_words:
        for w in page_words:
            key = (round(w['top'] / 5) * 5, w['text'])
            position_text[key] += 1

    # Text appearing on >50% of pages at the same position is likely header/footer
    threshold = len(pages_words) * 0.5
    return {k: v for k, v in position_text.items() if v >= threshold}
```

---

## Step 5 — Verify the Output

This step is **not optional.** Every translated document must be checked before delivery.

### Automated Checks

Run these programmatically:

1. **Page count match:** Output should have the same number of pages as input (plus any
   overflow pages from magnification, which should be documented).

2. **File validity:** Open the output PDF with pypdf and confirm it reads without errors.

3. **Visual comparison:** Render both original and translated pages as images and display
   them side-by-side. Look for:
   - Text bleeding outside its region
   - Overlay rectangles that don't match the background color
   - Missing translations (original text still visible)
   - Covered signatures or images that should have been preserved
   - Headers/footers that weren't translated

```python
def visual_comparison(original_path, translated_path, output_dir):
    """Render both PDFs and save side-by-side comparisons."""
    import pypdfium2 as pdfium
    from PIL import Image

    orig = pdfium.PdfDocument(original_path)
    trans = pdfium.PdfDocument(translated_path)

    for i in range(min(len(orig), len(trans))):
        orig_img = orig[i].render(scale=150/72).to_pil()
        trans_img = trans[i].render(scale=150/72).to_pil()

        # Create side-by-side comparison
        w = orig_img.width + trans_img.width + 20
        h = max(orig_img.height, trans_img.height)
        comparison = Image.new('RGB', (w, h), (240, 240, 240))
        comparison.paste(orig_img, (0, 0))
        comparison.paste(trans_img, (orig_img.width + 20, 0))
        comparison.save(f"{output_dir}/comparison_page_{i+1}.png")
        print(f"Comparison saved: page {i+1}")
```

### Manual Review Checklist

After automated checks, visually inspect at least the first page, last page, and any
page containing signatures or tables:

- [ ] Logo/branding visible and undamaged
- [ ] Signatures and stamps visible and not covered
- [ ] Headers and footers translated
- [ ] Table headers translated
- [ ] All body text translated (no French/source language remnants in text areas)
- [ ] Background color of overlays matches original
- [ ] Font sizes are readable (magnification applied where needed)
- [ ] Page numbers preserved or correctly re-added
- [ ] No text overflow or clipping

---

## Translation Notes File

Always produce a separate translation notes PDF alongside the translated document.
Include:

1. **Document overview table:** Original filename, page count, source/target languages,
   document type (digital/scanned), translation date.

2. **Terminology decisions:** For each non-obvious translation choice, explain why you chose
   that English term. Pay special attention to:
   - Legal and regulatory terms
   - Acronyms (both original and translated forms)
   - Terms you chose to leave untranslated and why

3. **Formatting notes:** Document any visual changes:
   - Pages where magnification was applied and the factor used
   - Pages where overflow occurred
   - Background color handling decisions
   - Any signatures, stamps, or handwritten elements and how they were preserved

4. **Disclaimer:** State that the translation is for informational purposes and the original-
   language document remains authoritative.

---

## Performance: Using uv for Faster Package Installation

When installing Python dependencies, prefer `uv` over `pip` for significantly faster
execution:

```bash
uv pip install pdfplumber reportlab Pillow pypdfium2 pytesseract pdf2image --system
```

If `uv` is not available, fall back to:
```bash
pip install pdfplumber reportlab Pillow pypdfium2 pytesseract pdf2image --break-system-packages
```

---

## Reference Files

For advanced techniques, edge cases, and complete code examples, see:

- `references/technical-guide.md` — Detailed code for OCR text region extraction,
  complex table handling, font matching, and multi-column layouts
