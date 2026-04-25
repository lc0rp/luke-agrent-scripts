---
name: analyze_page
description: Generate page-level visual diagnostics for frozen On.Translate PDF translations. Use when the user says analyze_page with page numbers or all, or asks to inspect a translated page using existing frozen translation artifacts without retranslating.
---

# Analyze Page

Use this skill in `/Users/luke/dev/ontranslate` when the user says:

`analyze_page <page number(s), or all>`

This is a frozen-translation diagnostic workflow. Do not retranslate. Use an existing job's `wip/translation/translated_blocks.json`, extraction payload, translated PDF, original PDF, and compare report.

## Default Command

Run from `/Users/luke/dev/ontranslate`:

```bash
uv run python /Users/luke/dev/luke-agent-scripts/skills/analyze-page/scripts/analyze_page.py <pages>
```

Examples:

```bash
uv run python /Users/luke/dev/luke-agent-scripts/skills/analyze-page/scripts/analyze_page.py 3
uv run python /Users/luke/dev/luke-agent-scripts/skills/analyze-page/scripts/analyze_page.py 2,3
uv run python /Users/luke/dev/luke-agent-scripts/skills/analyze-page/scripts/analyze_page.py all
```

If the user is referring to a specific loop or job, pass it explicitly:

```bash
uv run python /Users/luke/dev/luke-agent-scripts/skills/analyze-page/scripts/analyze_page.py 3 --job-dir output/fidelity-loops/<loop>/jobs/<job_id>
```

## Output

The script writes a folder under the job:

`<job>/wip/analyze_page/pages-<spec>/`

It creates separate PDFs for:

- original PDF with structural regions in red
- original PDF with source text blocks in blue
- translated PDF with structural regions in red
- translated PDF with translated text blocks in blue
- readable labels/tabs on every outlined region; label backgrounds and text colors must be chosen for contrast against the page and outline color, not left transparent or low-contrast. After changing label rendering, render at least one generated analysis PDF to an image and visually verify the labels are actually legible before reporting success.

It also writes:

- `diagnosis.md` with page score, visible failure signals, and brief possible fixes
- `summary.json` with artifact paths and metric details
- table key entries must include provenance for how each table was created: detector name plus the function/submodule responsible when known, for example `extract_layout.tables.detect_tables -> _line_intersection_candidates` or textual table construction in `extract_document`

## Response Style

After running, reply briefly:

- job/run used
- page score(s)
- paths to the four PDFs and `diagnosis.md`
- direct diagnosis in the reply, not only a link to `diagnosis.md`; include 2-4 short diagnostic bullets if there are obvious issues

If `uv run` changes only the top `exclude-newer` timestamp in `uv.lock`, restore that incidental change before final response.
