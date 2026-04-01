---
name: translate-in-place
description: Translate PDFs or scanned document images into a new PDF that reproduces the original layout as closely as possible while preserving headers, footers, logos, tables, images, handwritten names, dates, stamps, and signatures in place. Use when the user wants a translated document that still looks like the original rather than a separate summary or side-by-side translation.
---

# Translate In Place

Use this skill when the user wants a translated PDF that still resembles the source document page by page.

## When To Use

- PDF translation where layout matters
- scanned legal or compliance documents
- signed documents with handwritten marks, stamps, or seals
- forms, tables, manuals, and policies where headers and footers must also be translated
- document translation requests that explicitly want an "in-place" or "looks like the original" result

## Default Output

- Primary artifact: translated PDF
- Secondary artifact: separate notes file, usually Markdown, covering OCR fallbacks, manual overrides, compromised pages, and verification notes

Do not default to "translation page followed by the original page" unless the user explicitly accepts that compromise.

## Workflow

### 1. Bootstrap fast

- Prefer `uv venv` and `uv pip install` for Python setup.
- Fall back to `python -m venv` only when `uv` is unavailable or the user/repo requires it.
- Check `references/tooling-workflow.md` for the package list and example commands.
- Before committing to an API-backed translation run, verify the backend is actually usable. If the environment variable exists but the first request fails with an auth or quota error, treat the API path as unavailable instead of assuming credentials are valid.

### 2. Inspect and classify pages

Treat each page as one of:

- `digital`: usable text layer, mostly text/vector content
- `scanned`: no reliable text layer, OCR required
- `mixed`: both real text and significant embedded imagery

Use a fast preflight first:

- `pdfinfo` for page count and basic metadata
- `pdftotext -layout` on representative pages to confirm whether a real text layer exists
- a quick render or extraction check to see whether the document is truly `digital` before paying OCR costs
- identify pages with flow charts, arrows, connector lines, callouts, tables, or other layout-sensitive structures before translation begins
- identify pages where emphasis matters: bold section headers, bold inline terms, numbered steps, nested bullets, centered labels, or right-aligned footer/header text

Translate headers, footers, table headers, labels, captions, and body text. Do not drop them as "boilerplate".

### 3. Preserve non-text artifacts

- Preserve logos, photos, diagrams, stamps, handwritten names, handwritten dates, initials, seals, and signatures in place.
- Preserve table lines, boxes, and other non-text structure.
- Preserve flow-chart connectors, downward arrows, decision-tree branches, callout lines, and other directional marks. These are content, not decoration.
- Replace only text regions.
- For legal or signed documents, never flatten away signature or handwritten regions.

The safest default is to keep the original page as the base layer and redact or repaint only the text regions that are being translated.

Be careful with diagram arrows in particular:

- some arrows are true vector shapes and should survive untouched if only text regions are replaced
- some arrows are text glyphs or symbols and may disappear if the surrounding text block is overpainted
- if a connector or arrow would be lost by repainting a text region, redraw or preserve it explicitly instead of accepting the loss

### 4. Magnify tiny OCR when needed

If OCR text is too small or too noisy:

- increase render scale before OCR
- rerun OCR on magnified crops or pages
- keep text readable instead of forcing a tiny overlay

If translated text still does not fit cleanly after magnification, allow overflow to one or more continuation pages. Document the overflow in the notes file.

### 5. Compose the translated PDF

Preferred treatment by page type:

- `digital`: translate in place using native text boxes where feasible
- `scanned`: preserve the scanned page and replace only OCR text regions
- `mixed`: keep embedded images and logos untouched, translate text overlays only
- `table pages`: translate headers, labels, and cell text while preserving lines and structure
- `diagram pages`: translate node labels and captions while preserving connector geometry, arrow direction, and reading order
- `signature pages`: preserve signature and handwritten regions exactly; translate nearby typed labels in place

Formatting fidelity matters:

- preserve heading hierarchy and emphasis where the source uses bold headers or bold inline text
- preserve list structure, including bullet style, indentation depth, wrapped-line indent, and numbering
- preserve text alignment for centered headings, right-aligned metadata, and other deliberate alignment choices
- keep line breaks and paragraph spacing close to the source when they affect meaning or scanability

If the toolchain cannot preserve a formatting distinction exactly, use the closest readable approximation and document the compromise in notes.

When text overlays are used:

- match the overlay fill color to the source page background by sampling the original page whenever possible
- if background matching is unreliable because of scan noise, gradients, paper tint, or uneven lighting, normalize the affected overlay background to white
- if a wider page-level background normalization is necessary, whiten only the page background or text areas, never logos, images, handwritten marks, stamps, seals, or signatures

If exact in-place reproduction is impossible for a page, preserve the original artifact regions and document the compromise in notes instead of silently changing layout strategy.

### 6. Final QA is mandatory

- Render the final PDF and compare it against the source pages.
- Use `scripts/compare_rendered_pages.py` to generate side-by-side page images and a quick machine report.
- Visually inspect representative pages and every page with signatures, handwritten marks, stamps, tables, or continuation overflow.
- Visually inspect every page with flow charts, directional arrows, bold emphasis, centered headings, right-aligned metadata, or multi-level bullet lists.
- Check that downward arrows and other connectors still exist and still point the right way.
- Check that bold headers and bold inline emphasis were preserved or acceptably approximated.
- Check that bullet indentation, wrapped-list indentation, and text alignment still match the source closely enough to read the page the same way.
- Final answers must state which pages were visually checked and which pages, if any, required compromise.

Check `references/qa-checklist.md` before handoff.

## Translation Backends

- Prefer local or offline-capable translation when quality is acceptable.
- If valid credentials are available and document quality demands it, a model/API backend is acceptable.
- Preserve product names, legal identifiers, and regulator acronyms unless the user asks for localization of those terms.
- If the preferred backend fails at runtime with an exact error like invalid credentials, quota failure, or transport failure, fall back to the next acceptable backend unless the user explicitly required the failing backend.
- When falling back from an API backend to a local backend for legal or compliance text, call out the likely tradeoff: layout preservation may still be good while wording can become more literal or awkward.
- Record backend fallback decisions and exact failure reasons in the notes file and final handoff.

## QA Notes Closure

- Do not leave the generated notes file with a generic `Final QA TODO` section after QA is complete.
- Replace or append to the placeholder with the actual comparison result, the pages visually inspected, any page-count mismatch result, and any translation-quality caveat discovered during review.
- If all pages were visually checked, say so explicitly. If only representative pages were checked, name them explicitly.

## Resources

- `scripts/translate_in_place.py`: main PDF translation and compositing pipeline
- `scripts/compare_rendered_pages.py`: side-by-side render comparison and quick visual drift checks
- `references/tooling-workflow.md`: setup, dependencies, and backend guidance
- `references/qa-checklist.md`: final QA and compromise logging checklist
