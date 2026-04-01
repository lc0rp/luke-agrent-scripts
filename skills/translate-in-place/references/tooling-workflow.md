# Tooling Workflow

## Preferred setup

Use `uv` unless the user or repo requires something else.

```bash
uv venv .venv
source .venv/bin/activate
uv pip install pymupdf pillow pytesseract requests argostranslate pyyaml
```

Fallback:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pymupdf pillow pytesseract requests argostranslate pyyaml
```

## System dependencies

- `tesseract` must be installed and available on `PATH`
- for best OCR quality, ensure the relevant language data is installed

## Suggested execution flow

```bash
pdfinfo input.pdf
pdftotext -layout input.pdf - | sed -n '1,120p'
python scripts/translate_in_place.py input.pdf --source-lang fr --target-lang en --output-dir output/
python scripts/compare_rendered_pages.py input.pdf output/input-translated-in-place.pdf --output-dir output/compare/
```

During preflight, flag pages that contain:

- flow charts or process diagrams with arrows or connector lines
- bold headers or bold inline emphasis that carry hierarchy or meaning
- nested bullets, wrapped bullet lines, numbered steps, centered headings, or right-aligned metadata

These pages require stricter visual QA because plain text extraction alone does not prove formatting fidelity.

If you want to prefer API quality but avoid wasting a full run on bad credentials, do a fast backend sanity check first. If the first translation request fails with an authentication, quota, or permissions error, switch to `--translator argos` unless the user explicitly required API-only behavior.

If source paper color or scan shading makes overlay matching unstable, rerun with:

```bash
python scripts/translate_in_place.py input.pdf --overlay-background white --output-dir output/
```

## Backend guidance

- `--translator auto`: try OpenAI first when a valid `OPENAI_API_KEY` is present, otherwise try Argos Translate
- `--translator openai`: use API translation only
- `--translator argos`: use local Argos Translate only

Use API translation for dense legal or regulatory pages when credentials are valid and quality matters. Use local translation when offline execution or privacy is more important.
If `OPENAI_API_KEY` is present but the request returns `401`, `403`, or a similar hard failure, treat that as an unavailable backend and note the exact error in the translation notes and final answer.
For legal and compliance PDFs, mention when a local fallback was used because the wording quality can degrade even if layout preservation remains good.

## Overlay background guidance

- `--overlay-background sample`: sample the original page around each translated region and use that as the fill color
- `--overlay-background white`: normalize overlay fills to white when scanned background matching is unreliable

Use `white` when the sampled fill creates dirty-looking patches, muddy gray overlays, or inconsistent backgrounds across the page.
