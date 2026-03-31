# Babel Copy Pipeline

## Goal

Generate a translated PDF that approximates a professionally rebuilt target-language document while preserving the source document's structure and non-text artifacts.

Treat translation quality and visual fidelity as co-equal goals.

## Preferred Stages

### Stage 1: Extraction

Outputs:

- `source.md`
- `blocks.json`
- `assets/`

Do not skip preview renders. Render representative pages early and choose handling strategy from what you see, not from file type alone.

Choose a document-level `font_baseline` from those preview renders before you trust extracted font metadata. Classify the visual body face as `serif` or `sans`, store it in the payload, and prefer that visual decision whenever the source font is missing, weak, or not embedded.

Required properties per block:

- `page_number`
- `bbox`
- `text`
- `role`
- `align`
- `style`
- `is_table_cell`
- `is_header`
- `is_footer`
- `keep_original`

Required page-level properties:

- page size
- render path
- embedded asset placement metadata
- detected table geometry when present
- table-cell membership for blocks
- page classification: `digital`, `scanned`, or `mixed`
- chosen handling strategy hint for QA notes: `overlay`, `rebuild`, or hybrid

Required document-level properties:

- `font_baseline.family_class`: `serif` or `sans`
- `font_baseline.pdf_font_name`: `Times-Roman` or `helv`
- `font_baseline.docx_font_name`: `Times New Roman` or `Arial`
- `font_baseline.source`: how the decision was made, preferably visual inspection

### Stage 2: Translation

Outputs:

- `translated.md`
- `translated_blocks.json`

Translation should operate on semantic blocks:

- paragraphs
- headings
- list items
- table cells
- form labels
- headers
- footers
- captions

Not on:

- raw OCR lines
- signature scribbles
- stray footer artifacts

### Stage 3: Editable Rebuild

Preferred output:

- `.docx`

Fallback:

- HTML only when that is materially easier for the document class

Rebuild from structure, not from scan pixels. Match:

- page rhythm
- margins
- heading hierarchy
- paragraph spacing
- table grid
- signature form boxes

Current shipped implementation:

- `scripts/rebuild_docx.py`
- `scripts/build_final_pdf.py`
- `scripts/run_babel_copy.py`

This script now rebuilds page-sized `.docx` output with:

- page breaks
- basic alignment and typography
- detected bordered tables and form grids
- signature-image reinsertion into detected table cells

It is still heuristic rather than source-perfect, especially on noisy OCR and non-tabular scans.

### Stage 4: Asset Placement

Preserve and place:

- signatures
- seals
- logos
- stamps
- tables and line art when not cleanly rebuildable

Use source-overlay only as fallback.

For branded native PDFs, source-overlay is often the primary strategy rather than a fallback.

### Stage 5: PDF Export and QA

Export the rebuilt editable source to PDF, then compare against the original.

Use the comparison step to generate side-by-side page renders for human review.

Automation-oriented runs should also emit a `run-manifest.json` with enough metadata for later stages to find the exact source run. At minimum include:

- `output_dir`
- `compare_dir`
- `compare_report`
- `expected_qa_report`
- `document_id` when supplied
- `cycle_id` when supplied
- `run_label` when supplied

If the source is a branded native-text PDF with stable artwork and no form/table reconstruction needs, do not force it through `.docx` first. Use the original source page as the template, whiten translated text regions, and draw translated semantic blocks back onto that page.

QA priorities:

- page count
- heading placement
- body readability
- no newly introduced overlapping text in the translated output
- no stray OCR junk
- signature preservation
- no catastrophic overflow
- translated headers and footers
- connector, arrow, and flow-chart preservation
- overlay background color match

When visual QA reveals overlapping text or any other layout defect, treat that as a blocking warning. Review the side-by-side pages, patch `translated_blocks.json`, rebuild, and rerun comparison before sign-off.

Visual inspection scope:

- if the document is 20 pages or fewer, inspect every page
- if the document is longer than 20 pages, inspect the first page, the last page, and every page with signatures, tables, forms, or diagrams
- on each reviewed page, explicitly check for overlapping text, duplicate text draws, collisions between nearby translated blocks, and text crossing table, form, or signature boundaries

## Near-Term Implementation Order

1. better block extraction
2. manual or glossary-aware translation over blocks
3. docx rebuild for text and form pages
4. stronger OCR cleanup and floating asset placement
5. source-overlay fallback for hard pages
6. adaptive finalizer that picks overlay or rebuild per page

## What "Full .docx Rebuild Path" Means

It means the final PDF should come from an editable `.docx` that was rebuilt from extracted structure, not from direct PDF redaction overlays.

Concretely:

- source PDF -> `source.md` + `blocks.json` + `assets/`
- translation step -> `translated_blocks.json`
- rebuild step -> `.docx` with page breaks, headings, paragraphs, tables, form labels, and preserved signature boxes
- export step -> PDF

The goal is:

- readable legal-English text
- correct pagination
- clean white background
- preserved signature and form regions
- a result closer to a professionally rebuilt Word document than to a painted-over scan
