---
name: babel-copy
description: Build a translated PDF that closely matches the source document by separating extraction, translation, layout rebuilding, asset preservation, and PDF export into distinct steps. Use for legal, compliance, contract, policy, and form-heavy PDFs where a clean translated deliverable should approximate a professionally rebuilt document rather than a raw in-place overlay.
---

# Babel Copy

Use this skill when the translated document should read like a proper target-language document and still resemble the source visually.

## When To Use

- legal or compliance PDFs where wording quality matters
- contracts, amendments, manuals, forms, and policies
- scanned or mixed PDFs where the source layout should be approximated, not merely overpainted
- document translation requests where the user has a reference for a "good output"

## Default Output

- Primary artifact: translated PDF
- Final translated PDF names should be intuitive. Derive them from the original filename plus the target language short form, with an optional timestamp or counter only when needed to distinguish multiple runs of the same file. Avoid generic names such as `translated.pdf`.
- Inside the selected output directory, create two top-level folders if they do not already exist:
  - `wip/` for in-progress and intermediate artifacts
  - `completed/` for final user-facing deliverables
- Always copy completed final files into `completed/` as soon as each file is completed, even if the pipeline also writes them deeper inside nested run folders.
- Working artifacts:
  - source text in Markdown
  - structured block manifest
  - document-level `font_baseline` captured in the manifest
  - translated text in Markdown or JSON blocks
  - rebuilt rich-layout source, preferably `.typ`
  - QA renders and notes
  - `run-manifest.json` with canonical artifact paths for the current translation run

## Core Rule

Do not treat translation and page reconstruction as the same problem.

Translation accuracy and visual fidelity are equally important. Do not optimize one by quietly sacrificing the other.

Treat each source file as an independent job.

- if asked to translate multiple files, handle them independently
- do not infer extraction strategy, translation mode, glossary state, or QA conclusions for one file from artifacts produced for another file
- only artifacts, inferences, and prior outputs from the same file may be used to continue that file
- when resuming work, verify that reused artifacts belong to the same source file before trusting them

This skill is deliberately hybrid. Some parts should be scripted, but this is not a 100% scripted workflow. The operator must inspect preview renders, notice when the chosen strategy is wrong, and switch tactics before committing to the final PDF.

The pipeline is:

1. extract text and structure
2. translate semantic blocks
3. rebuild layout in an editable format
4. place preserved non-text assets
5. export PDF and run visual QA

Output layout expectations:

- treat the selected output directory as the container for one file's work
- create `wip/` and `completed/` before writing artifacts
- keep extracted manifests, translation request files, renders, and other intermediate outputs under `wip/`
- copy final user-facing deliverables into `completed/` as soon as each file is completed, using clear filenames so they are easy to find without navigating nested subdirectories
- when more than one final artifact matters for the user, copy all of them into `completed/`

## Dependency Bootstrap

Before doing anything:

1. Check that `uv` is installed.
2. If it is missing, install it using Astral's current instructions:
   - macOS or Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows PowerShell: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - fallback when `curl` is unavailable: `wget -qO- https://astral.sh/uv/install.sh | sh`
3. If `uv` still cannot be installed or executed, abort.

Execution rules:

- run every babel-copy Python entrypoint with `uv run --script`
- do not call babel-copy scripts with `python`, `python3`, or `sys.executable`
- place intermediate artifacts under `wip/` and copy completed final deliverables into `completed/` as soon as each file is completed
- when adding a new babel-copy script or repairing one that lacks inline metadata, run:
  - `uv init --script <script.py>`
  - add all direct dependencies to the script metadata
  - `uv lock --script <script.py>`
- distribute the matching `<script>.lock` file with the script
- every script must include inline `# /// script` metadata with:
  - `requires-python`
  - all direct Python dependencies
  - `[tool.uv]`
  - `exclude-newer = "..."` using an RFC 3339 timestamp

Current babel-copy scripts already ship inline uv metadata and adjacent lockfiles. Preserve both when editing dependencies.

## Workflow

### 1. Extract

Produce:

- `source.md`: clean reading-order text in the source language
- `blocks.json`: page-level structured content with bbox, role, alignment, list/table metadata, and inferred style
- `assets/`: extracted logos, signatures, stamps, lines, boxes, and reusable images

Extract semantic blocks, not OCR lines. Merge wrapped lines into paragraphs before translation.

Classify each page early:

- `digital`: stable native text layer, mostly vector/text content
- `scanned`: OCR required, page image is the main truth
- `mixed`: native text plus significant embedded imagery or page-art

Treat classification as a routing decision, not a label for the notes file.

Preferred handling by class:

- `digital`: preserve the source page geometry and typography cues; overlay or rebuild depending on page-art complexity
- `scanned`: preserve the rendered page image and replace only the translated text regions
- `mixed`: preserve the visual template while translating text blocks and keeping image regions untouched

Always render preview images first. Inspect at least the first page, one dense body page, and one page with forms/tables/signatures before choosing a final layout strategy. Do this before making assumptions about whether a document should be rebuilt or overlaid.

Choose a document-level fallback font baseline from those preview renders before trusting extracted font metadata:

- visually classify the document body text as `serif` or `sans`
- store that choice in top-level `font_baseline`
- when visual inspection conflicts with weak native metadata or a non-embedded source font, visual inspection wins
- use `uv run --script scripts/extract_document.py --font-baseline serif|sans` when you have already made the visual call

Baseline mapping:

- `serif` -> PDF overlay fallback `Times-Roman`; structured rebuild fallback `Times New Roman`
- `sans` -> PDF overlay fallback `helv`; structured rebuild fallback `Arial`

Clean OCR noise during extraction:

- normalize damaged glyphs and punctuation
- collapse obvious OCR fragments
- reject footer scraps, page debris, and signature scribbles as translatable text

Do not drop headers, footers, table headers, labels, captions, page titles, or repeated boilerplate just because they recur. If a human reader would read it, it should be translated unless it is clearly a non-translatable identifier.

If the page is a hard scan, preserve both the extracted text blocks and the rendered page image for fallback composition.

Primary extractor:

- `uv run --script scripts/extract_document.py`

Run it to create:

- `source.md`
- `blocks.json`
- `assets/`
- page renders for QA and fallback composition
- `font_baseline` metadata for later fallback-font decisions

OCR backend options:

- OCR is Tesseract-only
- use separate output directories when comparing extraction changes so manifests and QA renders stay isolated

Sentence and paragraph boundary help:

- `syntok` is used when available to add a lightweight sentence-boundary signal during fragment merging
- `scripts/extract_document.py` declares it inline, so `uv run --script` will install it on demand
- it is a helper, not the primary structure engine; geometry, typography, and visual QA still win

### 2. Translate

Produce:

- `translated.md`
- `translated_blocks.json`

Translate with context:

- preserve names, identifiers, account numbers, and product names unless the user asks otherwise
- use glossary-aware legal English
- keep section numbering stable
- prefer document-consistent terminology over sentence-local wording
- translate headers, footers, table headers, labels, captions, and body text
- preserve consistent glossary choices across the entire document, not just one page

Desktop translation flow for Codex Desktop or Claude Desktop:

1. run `uv run --script scripts/translate_blocks_desktop.py prepare ... --output-json translation-requests.json`
2. dispatch each request prompt to a desktop subagent in the active app
3. collect the JSON-only subagent replies into `translation-responses.json`
4. run `uv run --script scripts/translate_blocks_desktop.py apply-responses ... --requests-json translation-requests.json --responses-json translation-responses.json --output-json translated_blocks.json`

Desktop fragment-merge flow for Codex Desktop or Claude Desktop:

1. run `uv run --script scripts/extract_document.py ... --fragment-merge-requests-json fragment-merge-requests.json`
2. dispatch each fragment-merge prompt to a desktop subagent in the active app
3. collect the JSON-only subagent replies into `fragment-merge-responses.json`
4. rerun `uv run --script scripts/extract_document.py ... --fragment-merge-responses-json fragment-merge-responses.json`

Resume expectations:

- if a run stops mid-session, inspect existing artifacts first and continue from the latest viable translated output instead of assuming the session is cleanly aborted
- when resuming, confirm the artifacts belong to the same source file; outputs from separate file translations do not count as resume state for the current file

When the document is complex, it is acceptable to delegate specific components or blocks to desktop subagents for focused translation or inspection. Use this to speed up work, not to fragment terminology. Keep one shared glossary/context for the full document.

If no API or local MT backend is available or desired, use a manual phrase-map flow:

- for block-level rebuilds, run `scripts/babel_copy_manual.py prepare-blocks`
- fill the generated manual template JSON by hand
- run `scripts/babel_copy_manual.py apply-blocks`
- if you need the legacy overlay fallback, `extract` and `apply` still exist

### 3. Rebuild Layout

Default target: `.typ`

Use paragraph-first structured layout for legal documents unless HTML, React, canvas, or another intermediate layout format is materially better for the specific page class. The rebuilt document should:

- preserve page count when feasible
- preserve section hierarchy
- preserve tables and form cells
- preserve headers, footers, and signature blocks
- avoid continuation pages unless every fitting strategy fails

Approximate the source, but do not keep dirty scan backgrounds unless they are necessary to preserve meaning.

When a block lacks good font data, or the extracted source font is not embedded / not reusable, rebuild against the document `font_baseline` instead of blindly trusting `style.font_name`.

Choose layout strategy per document class:

- `source-page overlay`: best for branded native PDFs, complex visual templates, scan-heavy pages, arrows/flow charts, or any page where the original is the best layout template
- `structural rebuild`: best for forms, bordered tables, signature pages, and clean digital reports where rebuilt text improves readability without losing recognizability
- `hybrid staging`: acceptable when HTML/React/canvas or another intermediate format gives better control before final PDF rendering

Do not force the entire document through one strategy if that strategy is obviously wrong for part of it. Prefer modularity.

Current bundled rebuild path:

- `uv run --script scripts/rebuild_typst.py`
- `uv run --script scripts/export_typst_pdf.py`
- `uv run --script scripts/build_final_pdf.py`

These fields are written into `run-manifest.json` so the current run can be resumed and inspected deterministically.

This now supports:

- page-size-aware Typst rebuild
- visual-first serif / sans fallback selection carried from extraction into rebuild
- detected table and form reconstruction
- signature and stamp image crops placed back into table cells
- manual block-translation templates for rebuild-first workflows
- adaptive final PDF assembly:
  - template-preserving overlay for branded native-text or scan-heavy pages
  - per-page structured rebuild fallback for form/table/signature pages inside the same document
  - translated repeated footers and headers as real translatable blocks
- staged desktop translation:
  - extract -> desktop prepare/apply translation -> hybrid final PDF build -> rendered comparison report -> check notes

It is still not a fully page-faithful legal-document engine, but it now covers the high-leverage structure needed for form-heavy signature pages.

### 4. Preserve Assets

Prefer a clean rebuilt page with selectively preserved assets over blanket overlay on the original scan.

Preserve:

- signatures
- stamps and seals
- logos
- non-text box lines and table rules
- diagrams or arrows that carry meaning
- headers and footer line art
- flow-chart connectors, directional arrows, and callout geometry

Fallback only when reconstruction is too risky:

- whiten or redact paragraph regions on the original page
- paste translated text back into those regions

For branded native PDFs that already have stable page art, prefer the original source page as the visual template and overlay translated semantic blocks onto it. This keeps logos, rules, footers, numbering, and page rhythm intact.

Overlay color must match the source background whenever possible. Sample the source page. If sampling is unreliable because of gradients, scan noise, or uneven tint, normalize the translated region cleanly instead of leaving an obvious mismatch.

### 5. Export and QA

Always render the final PDF and compare it against the source.

Run a check step before declaring success:

- render preview pages before layout decisions
- render the final PDF after composition
- compare source vs translated renders side by side with `uv run --script scripts/compare_rendered_pages.py`
- use judgment on the rendered images; do not trust the pipeline just because it completed

If visual QA reveals overlapping text or any other local layout problem that does not justify changing extraction or renderer logic, use a targeted post-process override pass:

- edit `translated_blocks.json`, not `blocks.json`
- add `custom_override` only to the affected block(s)
- use it for small bbox nudges, width/height expansion, font-size adjustments, alignment changes, color changes, or direct text overrides
- important override semantics:
  - numeric values in `custom_override` are treated as deltas by default
  - this applies to bbox edge values such as `left`, `top`, `right`, `bottom` and to numeric style fields such as `font_size_hint`
  - use explicit signed deltas like `+12` or `-4` when you want relative movement or expansion
  - if you need an absolute numeric target, pass it as a quoted numeric string such as `"533.0"` rather than `533.0`
  - do not assume bare numeric JSON values are absolute coordinates
- rerun `uv run --script scripts/build_final_pdf.py`
- rerun `uv run --script scripts/compare_rendered_pages.py`
- prefer the smallest override set that fixes the visible issue

Use overrides for document-specific cleanup, not for systematic bugs that should be fixed in the pipeline itself.

Visually inspect:

- for documents with 20 pages or fewer, inspect every page
- for documents with more than 20 pages, inspect the first page, the last page, and every page with signatures, tables, forms, or diagrams
- inspect each reviewed page for overlapping text, duplicate text draws, collision between translated blocks, and text crossing nearby rules or signature/table boundaries
- inspect every page where the rebuilt text was tightened to avoid overflow
- inspect every page with translated headers or footers
- inspect every page with arrows, flow charts, or connector lines

Final notes must state:

- which pages were checked
- whether page count changed
- whether the rebuilt output is closer to a clean reconstruction or a source-overlay fallback
- what strategy was chosen and why (`overlay`, `rebuild`, or hybrid)
- whether overlapping text or other layout defects were found and how they were resolved
- whether any `custom_override` adjustments were applied after comparison

## Current Implementation

This skill now ships its own bundled scripts:

- `scripts/core.py`: local extraction and composition primitives
- `scripts/extract_document.py`: source text, block manifest, and asset extraction
- `scripts/babel_copy_manual.py`: manual extract/apply bootstrap flow
- `scripts/rebuild_typst.py`: minimal `.typ` rebuild from translated blocks
- `scripts/export_typst_pdf.py`: Typst CLI PDF export
- `scripts/build_final_pdf.py`: chooses overlay-vs-rebuild final PDF rendering per page
- `scripts/compare_rendered_pages.py`: side-by-side visual QA helper for review
- `scripts/translate_blocks_desktop.py`: block translation request prep/apply for desktop subagents
- each Python script includes inline uv metadata and should be invoked with `uv run --script`
- each Python script is expected to ship with an adjacent `.lock` file

Current limitation:

- the legacy manual apply path still uses direct PDF composition instead of the rebuild-first Typst path
- OCR cleanup still needs tightening for noisy artifacts and damaged headings
- lightweight tables without visible borders still rely on overlap-preservation heuristics more than true semantic reconstruction
- signature images are reinserted with cell-aware placement, not true floating-page anchors
- truly mixed documents still need finer-grained per-page or per-region strategy switching

## Read When

- Read `references/pipeline.md` when setting up or extending the five-stage pipeline.
- Read `references/block-schema.md` when designing extraction or rebuild artifacts.
