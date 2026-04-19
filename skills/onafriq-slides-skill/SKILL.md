---
name: onafriq-slides-skill
description: Create, extend, rebuild, or edit Onafriq PowerPoint decks in the official Onafriq style with a self-contained, explicit workflow. Use this skill whenever the user asks for Onafriq slides, an Onafriq deck, board slides, commercial slides, internal presentation polish, PowerPoint edits, `.pptx` changes, slide recreation, template-based slide work, or any presentation that should look like native Onafriq material. The library choice is already decided; use PptxGenJS for slide authoring, use the bundled template references, and follow the exact ordered workflow in this skill.
---

# Onafriq Slides Skill

This skill is intentionally rigid. Follow it in order. Do not improvise the toolchain. Use this skill when you need to create an Onafriq branded PowerPoint presentations

## Fixed Skill Root

When this skill is installed for the target LLM, assume the skill root is exactly:

- `/home/oai/skills/onafriq-slides-skill`

Use that path literally in shell commands and file references. Do not invent another path.

## Immediate Boot Sequence

The first thing you do after loading this skill is:

1. Check that these files exist:
   - `/home/oai/skills/onafriq-slides-skill/references/onafriq-slide-brand-rules.md`
   - `/home/oai/skills/onafriq-slides-skill/references/onafriq-slides-template.pptx`
   - `/home/oai/skills/onafriq-slides-skill/references/onafriq-slides-template.pdf`
   - `/home/oai/skills/onafriq-slides-skill/references/onafriq-slides-template-montage.png`
   - `/home/oai/skills/onafriq-slides-skill/references/onafriq-brand-guide-v4-web.pdf`
   - `/home/oai/skills/onafriq-slides-skill/references/pptxgenjs-helpers.md`
   - `/home/oai/skills/onafriq-slides-skill/assets/pptxgenjs_helpers/index.js`
   - `/home/oai/skills/onafriq-slides-skill/scripts/render_slides.py`
   - `/home/oai/skills/onafriq-slides-skill/scripts/create_montage.py`
   - `/home/oai/skills/onafriq-slides-skill/scripts/slides_test.py`
   - `/home/oai/skills/onafriq-slides-skill/scripts/detect_font.py`
   - `/home/oai/skills/onafriq-slides-skill/scripts/ensure_raster_image.py`
   - `/home/oai/skills/onafriq-slides-skill/scripts/replace_text_in_pptx.py`
2. If any file is missing, stop and tell the user which path is missing.
3. If all files exist, tell the user exactly:

`loaded obsidian-slides-skill, and I can access the references/* files.`

Use this exact sentence.

Example check command:

```bash
test -f /home/oai/skills/onafriq-slides-skill/references/onafriq-slide-brand-rules.md && \
test -f /home/oai/skills/onafriq-slides-skill/references/onafriq-slides-template.pptx && \
test -f /home/oai/skills/onafriq-slides-skill/references/onafriq-slides-template.pdf && \
test -f /home/oai/skills/onafriq-slides-skill/references/onafriq-slides-template-montage.png && \
test -f /home/oai/skills/onafriq-slides-skill/references/onafriq-brand-guide-v4-web.pdf && \
test -f /home/oai/skills/onafriq-slides-skill/references/pptxgenjs-helpers.md && \
test -f /home/oai/skills/onafriq-slides-skill/assets/pptxgenjs_helpers/index.js && \
test -f /home/oai/skills/onafriq-slides-skill/scripts/render_slides.py && \
test -f /home/oai/skills/onafriq-slides-skill/scripts/create_montage.py && \
test -f /home/oai/skills/onafriq-slides-skill/scripts/slides_test.py && \
test -f /home/oai/skills/onafriq-slides-skill/scripts/detect_font.py && \
test -f /home/oai/skills/onafriq-slides-skill/scripts/ensure_raster_image.py && \
test -f /home/oai/skills/onafriq-slides-skill/scripts/replace_text_in_pptx.py
```

## What To Load

Load these references in this order:

1. `/home/oai/skills/onafriq-slides-skill/references/onafriq-slide-brand-rules.md`
2. `/home/oai/skills/onafriq-slides-skill/references/onafriq-slides-template-montage.png`
3. `/home/oai/skills/onafriq-slides-skill/references/onafriq-slides-template.pdf`
4. `/home/oai/skills/onafriq-slides-skill/references/pptxgenjs-helpers.md` only if you need helper API details
5. `/home/oai/skills/onafriq-slides-skill/references/onafriq-brand-guide-v4-web.pdf` only if the slide-brand rules file is insufficient

Do not skip the montage and PDF. Use them to identify the closest template slide before writing or replacing anything.

## Non-Negotiable Choices

- Author decks in JavaScript with `PptxGenJS`.
- Use the bundled `pptxgenjs_helpers` files from this skill. Do not reimplement them.
- Treat `/home/oai/skills/onafriq-slides-skill/references/onafriq-slides-template.pptx` as the source design system.
- Never edit files inside `/home/oai/skills/onafriq-slides-skill/` directly.
- Always `cp` the template into a task-local working directory first.
- Never start from a blank deck when an existing Onafriq template slide can be adapted.
- Never use `python-pptx` to author or lay out the final deck.
- Only use the bundled `replace_text_in_pptx.py` script for direct template-text replacement.
- Always render the deck after changes; always review the montage; always run overflow and font checks before handoff.

## Allowed Modes

There are only two allowed modes:

1. `Mode A: template-copy edit`
   Use this when the closest Onafriq template slide already exists and you mainly need to replace placeholder text or swap assets.
2. `Mode B: template-matched rebuild`
   Use this when the requested slide needs new structure or cannot be safely achieved by direct text replacement. In this mode, you still copy the Onafriq template and use the montage and PDF as the geometry reference; then you recreate the needed slides in `PptxGenJS`.

If the request is small, start with `Mode A`.
If `Mode A` becomes messy, switch to `Mode B`.

## Exact Working Directory Setup

Run these commands first. Replace `TASK_DIR` with a concrete task folder name.

```bash
export SKILL_ROOT=/home/oai/skills/onafriq-slides-skill
export TASK_DIR=./onafriq-slide-work

mkdir -p "$TASK_DIR"
cp "$SKILL_ROOT/references/onafriq-slides-template.pptx" "$TASK_DIR/template-source.pptx"
cp "$SKILL_ROOT/references/onafriq-slides-template.pdf" "$TASK_DIR/template-source.pdf"
cp "$SKILL_ROOT/references/onafriq-slides-template-montage.png" "$TASK_DIR/template-source-montage.png"
cp "$SKILL_ROOT/references/onafriq-slide-brand-rules.md" "$TASK_DIR/onafriq-slide-brand-rules.md"
cp "$SKILL_ROOT/references/pptxgenjs-helpers.md" "$TASK_DIR/pptxgenjs-helpers.md"
cp -R "$SKILL_ROOT/assets/pptxgenjs_helpers" "$TASK_DIR/pptxgenjs_helpers"
cp "$SKILL_ROOT/scripts/render_slides.py" "$TASK_DIR/render_slides.py"
cp "$SKILL_ROOT/scripts/create_montage.py" "$TASK_DIR/create_montage.py"
cp "$SKILL_ROOT/scripts/slides_test.py" "$TASK_DIR/slides_test.py"
cp "$SKILL_ROOT/scripts/detect_font.py" "$TASK_DIR/detect_font.py"
cp "$SKILL_ROOT/scripts/ensure_raster_image.py" "$TASK_DIR/ensure_raster_image.py"
cp "$SKILL_ROOT/scripts/replace_text_in_pptx.py" "$TASK_DIR/replace_text_in_pptx.py"
cd "$TASK_DIR"
```

After that, create these files:

- `working-deck.pptx`
- `build_deck.mjs` if you will use `Mode B`
- `replacements.json` if you will use `Mode A`
- `rendered/` for rendered slide PNGs
- `final/` for final handoff files

Example:

```bash
cp template-source.pptx working-deck.pptx
mkdir -p rendered final
```

## Order Of Operations

Follow this order every time:

1. Run the immediate boot sequence.
2. Copy the template, references, helpers, and scripts into a task-local directory.
3. Read `onafriq-slide-brand-rules.md`.
4. Inspect `template-source-montage.png` and `template-source.pdf`.
5. Identify the exact template slide numbers you plan to use.
6. Choose `Mode A` or `Mode B`.
7. Make the changes.
8. Render the deck to PNGs.
9. Build a montage from the rendered PNGs.
10. Review the montage.
11. Run overflow checks.
12. Run font checks.
13. Remove unused template/reference slides if you are delivering a template-copy deck.
14. Move final artifacts into `final/`.
15. Hand off both the `.pptx` and the source `.mjs` if you used `Mode B`.

Do not change this order.

## Mode A: Template-Copy Edit

Use this when you are editing an Onafriq template slide directly.

### Step A1: inspect exact placeholder text

List the slide text first:

```bash
python3 replace_text_in_pptx.py list working-deck.pptx
```

This prints slide-by-slide visible text. Use it to capture the exact strings you will replace.

### Step A2: write `replacements.json`

Create a JSON file with one rule per replacement.

Use this format:

```json
{
  "rules": [
    {
      "slide": 9,
      "name": "Title 1",
      "mode": "exact",
      "match": "Extra slide with title\nand subtitle",
      "replace": "Cross-border payments growth\nQ1 2026"
    },
    {
      "slide": 9,
      "name": "Subtitle 2",
      "mode": "contains",
      "match": "Lorem ipsum",
      "replace": "Volume grew across priority corridors.\nApproval time fell after the new routing flow."
    }
  ]
}
```

Rules:

- `slide` is required.
- `match` is required.
- `replace` is required.
- `name` is strongly recommended so the match is unambiguous.
- `mode` is either `exact` or `contains`.
- If you know the exact full visible placeholder text, use `exact`.
- If the text is long boilerplate and the first distinctive fragment is enough, use `contains`.

### Step A3: apply replacements

```bash
python3 replace_text_in_pptx.py apply working-deck.pptx replacements.json working-deck.replaced.pptx
mv working-deck.replaced.pptx working-deck.pptx
```

If the script errors, fix `replacements.json` instead of editing the deck manually.

### Step A4: asset swaps

If you need to inspect or normalize a tricky image before placing or comparing it, use:

```bash
python3 ensure_raster_image.py input.svg --output_file input.png
```

If the request only needed text replacement, skip `Mode B` and go to validation.

## Mode B: Template-Matched Rebuild With PptxGenJS

Use this when the requested slide cannot be safely achieved by direct placeholder replacement.

### Step B1: library choice

The library is fixed:

- `PptxGenJS`

Do not switch to any other authoring library.

### Step B2: create the JS source file

Create `build_deck.mjs` and start from this structure:

```js
import PptxGenJS from "pptxgenjs";
import {
  imageSizingContain,
  imageSizingCrop,
  warnIfSlideHasOverlaps,
  warnIfSlideElementsOutOfBounds,
} from "./pptxgenjs_helpers/index.js";

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "Codex";
pptx.company = "Onafriq";
pptx.subject = "Onafriq presentation";
pptx.title = "Onafriq deck";
pptx.lang = "en-GB";
pptx.theme = {
  headFontFace: "Radikal",
  bodyFontFace: "Century Gothic",
  lang: "en-GB",
};

function finalizeSlide(slide) {
  warnIfSlideHasOverlaps(slide, pptx);
  warnIfSlideElementsOutOfBounds(slide, pptx);
}

const slide = pptx.addSlide();
slide.background = { color: "FFFFFF" };

// Copy the structure, spacing, and hierarchy from the selected Onafriq template slide.
// Do not invent a fresh layout when the template already provides one.

slide.addText("Title here", {
  x: 0.8,
  y: 0.9,
  w: 8.8,
  h: 1.2,
  fontFace: "Radikal",
  fontSize: 26,
  bold: true,
  color: "323232",
  margin: 0,
  valign: "top",
});

slide.addText("Body copy here", {
  x: 0.8,
  y: 2.0,
  w: 5.5,
  h: 2.4,
  fontFace: "Century Gothic",
  fontSize: 14,
  color: "323232",
  margin: 0,
  breakLine: false,
  valign: "top",
});

finalizeSlide(slide);
await pptx.writeFile({ fileName: "working-deck.pptx" });
```

### Step B3: geometry rule

Before adding coordinates, lock the source slide number from the montage or PDF and state it in a code comment.

Example:

```js
// Template source: slide 14 from template-source.pdf and template-source-montage.png
```

### Step B4: helper rules

- Import helpers from `./pptxgenjs_helpers/index.js`.
- Use `imageSizingCrop` or `imageSizingContain` for images.
- Include both overlap warning helpers on every slide.
- Keep text editable as text.
- Keep simple charts editable as native charts when practical.
- Preserve Onafriq footer logic and brand styling from the chosen template.

### Step B5: write the deck

Run your JS file from the task directory.

## Validation Commands

Run all of these after edits:

```bash
python3 render_slides.py working-deck.pptx --output_dir rendered
python3 create_montage.py --input_dir rendered --output_file rendered/montage.png
python3 slides_test.py working-deck.pptx
python3 detect_font.py working-deck.pptx --json
```

Review `rendered/montage.png` before handoff.

## Finalization Commands

After validation passes:

```bash
mkdir -p final
mv working-deck.pptx final/
test -f build_deck.mjs && mv build_deck.mjs final/
test -f replacements.json && mv replacements.json final/
cp rendered/montage.png final/
```

If you used `Mode B`, the final handoff must include:

- the final `.pptx`
- the exact `.mjs` source file used to build it
- the final montage PNG

If you used `Mode A`, the final handoff must include:

- the final `.pptx`
- the `replacements.json` file
- the final montage PNG

## Onafriq Brand Rules You Must Enforce

- Use the Onafriq template as the design system.
- Keep the template typography hierarchy.
- Prefer `Radikal`; use `Century Gothic` as the fallback family already present in the template.
- Keep the logo treatment, footer, and page-number treatment intact.
- Rewrite or split copy before shrinking type.
- Keep the deck clean and restrained.
- Do not use em dashes.
- Remove unused template/reference slides before final delivery.

## Refusal Rules

Stop and correct course if you are about to do any of these:

- editing files directly under `/home/oai/skills/onafriq-slides-skill/`
- starting from a blank deck when a template slide exists
- using a library other than `PptxGenJS` for authoring
- skipping the montage or PDF review
- skipping render, overflow, or font checks
- delivering a rebuilt deck without the source `.mjs`
- leaving obvious `Lorem ipsum`, `Section title`, `Subsection title`, or other placeholder text in the final deck

## Quick Checklist

Before handoff, confirm all of these:

- The skill boot checks passed.
- You told the user `loaded obsidian-slides-skill, and I can access the references/* files.`
- You read the Onafriq slide-brand rules.
- You inspected the montage and PDF.
- You identified the source template slides first.
- You used `PptxGenJS` for authoring.
- You used the bundled helper files.
- You rendered the deck.
- You reviewed the montage.
- You ran overflow checks.
- You ran font checks.
- You removed unused template slides if applicable.
- You did not leave placeholder text behind.
