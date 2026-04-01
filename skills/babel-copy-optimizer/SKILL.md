---
name: babel-copy-optimizer
description: Close the loop between `babel-copy-qa` findings and `babel-copy` implementation changes. Use this whenever the user wants to optimize babel-copy from failed `qa-report.json` remediation notes, auto-iterate on translation-layout defects, rerun babel-copy until remediation goals are met, or turn QA failures into concrete pipeline fixes and an optimizer report.
---

# Babel Copy Optimizer

Use this skill to turn a failed `babel-copy-qa` result into concrete `babel-copy` changes, fresh reruns, and a documented optimization outcome.

This skill sits on top of [$babel-copy](/Users/luke/Documents/dev/luke-agent-scripts/skills/babel-copy/SKILL.md) and [$babel-copy-qa](/Users/luke/Documents/dev/luke-agent-scripts/skills/babel-copy-qa/SKILL.md). Do not treat it as a third independent pipeline.

## Outcome

Drive a failed translated-PDF run to one of these end states:

- remediation goals met and documented
- partially improved with remaining blockers documented
- blocked by a real ambiguity or missing capability, with exact next engineering work documented

Always produce a detailed `optimizer-report.md`. Write `optimizer-report.json` when the run involved multiple attempts, multiple remediations, or enough structured state that a machine-readable trail is useful.

## Canonical Inputs

- one failed `qa-report.json` produced by `babel-copy-qa`
- the sibling `comparison-report.json`
- the parent run artifacts referenced by `run-manifest.json`
- the current `babel-copy` source tree

If the user does not specify a QA report, resolve the latest unhandled one first.

## Canonical Source Tree

When editing `babel-copy`, prefer the git-tracked skill source if it exists:

- `/Users/luke/Documents/dev/luke-agent-scripts/skills/babel-copy`

Do not start by editing the installed mirror under `~/.codex/skills` when the source repo is available.

## Latest Unhandled QA Report

Use `scripts/find_latest_unhandled_qa.py` in this skill to locate the latest failed QA report.

For scheduled batch loops, use `scripts/run_optimization_cycle.py` in this skill to manage the lock file, cycle ids, and the two-consecutive-full-pass stop condition.

Rules:

- candidate reports are `qa-report.json` files whose `overall.status` is `fail`
- `overall.review_status` may be `needs_review`; this still counts as failed and must not be treated as a pass
- a QA report is `handled` if the same `compare/` directory already contains `optimizer-report.md` or `optimizer-report.json`
- `latest` means highest `generated_at`; if missing, fall back to file mtime

If no unhandled failed QA report exists, stop and say so plainly.

## Required Output Locations

The handled marker lives next to the QA artifacts:

- `<compare-dir>/optimizer-report.md`
- optional `<compare-dir>/optimizer-report.json`

Each retry of `babel-copy` must use a fresh timestamped output directory. Never reuse a previous run directory.

Recommended naming:

- `<previous-run-root>-optimizer-YYYYMMDDTHHMMSSZ`

Example:

```bash
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
python /Users/luke/Documents/dev/luke-agent-scripts/skills/babel-copy/scripts/run_babel_copy.py \
  "/abs/path/input.pdf" \
  --output-dir "/abs/path/output/F2-optimizer-${timestamp}"
```

## Optimization Loop

### 1. Resolve the target QA report

Find the latest unhandled failed `qa-report.json`.

Read:

- the QA report
- the sibling `comparison-report.json`
- the `run_manifest_path` recorded in the QA report when present; otherwise the parent run's `run-manifest.json`
- `overall.review_status`, `overall.review_gate_reasons`, `pages[*].review_status`, `pages[*].hotspot_reviews`, and `pages[*].challenger`
- the relevant rendered page images for failed pages
- the current `babel-copy` scripts or references implicated by the failures

Do not start patching before you understand whether the defect is local, systemic, or both.

### 2. Convert remediations into engineering hypotheses

For each failed page issue and failed check:

- restate the defect in pipeline terms
- identify the most likely stage: extraction, translation, block shaping, layout rebuild, overlay placement, asset preservation, or compare/QA mismatch
- decide whether the fix belongs in:
  - `babel-copy` code
  - document-specific block overrides in `translated_blocks.json`
  - both

Prefer fixing the root cause in `babel-copy` when the defect is likely to recur across documents.

Prefer a document-specific override when:

- the defect is one-off
- the current pipeline is broadly correct
- a code change would be speculative or risky

Do not disguise a systematic pipeline defect as a one-off override just to get a single page green.

### 3. Plan the minimal corrective change set

Group remediations by root cause so one code change can satisfy several findings.

For each planned change, capture:

- affected QA pages and checks
- target `babel-copy` files
- expected behavioral change
- how the next rerun will prove or disprove the hypothesis

If several hypotheses are possible, test the smallest, most falsifiable one first.

### 4. Patch `babel-copy`

Edit the real `babel-copy` source tree.

Typical files:

- `scripts/extract_document.py`
- `scripts/translate_blocks_codex.py`
- `scripts/build_final_pdf.py`
- `scripts/rebuild_docx.py`
- `scripts/core.py`
- `SKILL.md` when operator guidance needs to change with the code

Keep changes tightly scoped to the identified failure mode. Do not refactor unrelated pipeline code while chasing QA closure.

### 5. Rerun in a fresh timestamped directory

Always rerun `babel-copy` into a new timestamped output directory.

Carry forward the original run inputs unless the remediation explicitly requires a different page subset or OCR backend. Reuse relevant options from the original `run-manifest.json` when available.

At minimum preserve:

- source PDF
- document id when present
- cycle id when present
- source and target language
- OCR engine choice
- font baseline override when present

When rerunning from a QA report that carries `document_id`, `cycle_id`, or `run_label`, preserve `document_id` and `cycle_id` and set a new informative `run_label`.

If you narrow the rerun to a subset of pages for fast iteration, say so in the report and do a full rerun before declaring the remediation goals met unless the user explicitly asked for a page-local experiment only.

### 6. Re-QA the fresh output

Run the `babel-copy-qa` workflow on the new `comparison-report.json`.

Use the QA result to answer two questions:

- did the targeted remediations actually clear?
- did the code change introduce regressions on previously acceptable pages?

Do not mark the goal met from a visual hunch alone. Use a fresh QA report.

### 7. Decide whether to loop again

Loop when:

- targeted failed checks still fail
- a near-miss suggests one more bounded fix is justified
- the latest rerun exposed the real root cause more clearly

Stop looping when:

- the remediation goals are met
- further changes would be speculative churn
- the remaining defects require a larger architectural change than this pass should attempt

## Root-Cause Routing

Use this routing discipline:

- text collisions, clipping, duplicate draws:
  - inspect block geometry, font fallback, region sizing, and overlay fitting first
- missing or wrong headers/footers:
  - inspect extraction classification and repeated-block handling
- broken tables or form cells:
  - inspect table detection, cell grouping, and rebuild path selection
- wrong signature/stamp behavior:
  - inspect asset extraction and reinsertion logic
- bad wording with good layout:
  - inspect translation batching, glossary handling, and protected identifiers
- visually wrong but QA evidence weak:
  - inspect compare assets and the exact page images before changing the pipeline

Use `custom_override` as a tactical fix. Use code changes for repeatable behavior.

## Reporting

Read `references/optimizer-report-schema.md` before writing the final report.

`optimizer-report.md` must include:

- source QA report chosen and why it was considered unhandled
- remediation goals extracted from the QA report
- each attempt in order
- code or override changes made on each attempt
- exact rerun output directory for each attempt
- QA outcome after each attempt
- final disposition: `met`, `partially_met`, or `not_met`
- remaining risks or follow-up work

Write `optimizer-report.json` when:

- there were 2 or more attempts
- there were 3 or more distinct remediation items
- you touched more than one `babel-copy` code file
- the user asked for machine-readable output

## Execution Discipline

- Keep one agent responsible for the canonical optimization decision log.
- Do not have multiple agents patch the same `babel-copy` files concurrently.
- If you delegate page inspection, keep ownership disjoint and merge findings yourself.
- Preserve every prior attempt directory.
- Quote exact script errors and QA failures in the report.

## Final Check

Before handoff, confirm all of these:

- the selected QA report was failed and previously unhandled
- every rerun used a new timestamped output directory
- the latest rerun has a fresh `qa-report.json`
- the report states whether goals were met
- the report names the exact `babel-copy` files touched
