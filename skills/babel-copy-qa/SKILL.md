---
name: babel-copy-qa
description: Review one or more babel-copy or translate-in-place `comparison-report.json` files and produce deterministic `qa-report.json` outputs with page-level pass/fail verdicts, checklist-derived scores, hotspot coverage, challenger review outcomes, and exact remediation notes. Use this whenever the user asks to QA translated PDF comparison renders, rate pages, score a translation output, decide sign-off readiness, or turn side-by-side comparison images into a structured report for downstream optimization.
---

# Babel Copy QA

Use this skill to turn side-by-side comparison renders into a consistent QA decision that can drive the optimizer loop.

This skill is optimized for `gpt-5.4-mini`. Keep the workflow narrow, explicit, visual-first, and schema-driven.

## Inputs

One or more `comparison-report.json` files produced by `babel-copy` or compatible pipelines.

Expected report contents:

- source and translated PDF paths
- page counts
- per-page `side_by_side_image`
- per-page `mean_diff`

If a sibling `run-manifest.json` exists one directory above `compare/`, preserve its baton fields in `qa-report.json`.

## Output

Write exactly one `qa-report.json` next to each input `comparison-report.json`.

Default output path:

- `<compare-dir>/qa-report.json`

Use the exact schema in `references/qa-report-schema.md`.

## Required Workflow

Use this sequence exactly:

1. `python scripts/run_babel_copy_qa.py prepare <comparison-report-or-dir>...`
2. Review every page image listed in each scaffolded `qa-report.json`
3. Fill the page fields in two passes:
   - defect hunt
   - checklist scoring
4. For every page that would otherwise pass, run a challenger pass
5. `python scripts/run_babel_copy_qa.py finalize <comparison-report-or-dir>...`

The script validates the contract, computes scores, and rejects generic evidence.

## Two-Pass Review

Read `references/checklist.md` before grading pages.

### Pass 1: Defect Hunt

Find visible defects first. Do not score yet.

Inspect these hotspots on every page:

- top band
- middle band
- bottom band
- densest text region
- structured region when the page has bullets, icons, tables, forms, signatures, or other artifact-heavy content

Record hotspot notes in `hotspot_reviews` with page-region-specific observations.

If you see a real defect, add it to `issues` immediately and write `defect_hunt_summary`.

### Pass 2: Checklist Scoring

Only after the defect hunt:

- fill every checklist item
- use `pass`, `fail`, or `not_applicable` only
- every `pass` and `fail` must include specific evidence
- every `fail` must include concrete remediation

Do not let a high-level “page looks fine” impression override a visible local defect.

## Challenger Pass

Every page that would otherwise pass must get a challenger pass.

Goal:

- ask a second mini pass to find any reason the page should fail or need manual review

Represent this in the `challenger` object.

Rules:

- `challenger.status = clear` means the challenger found no blocker
- `challenger.status = flagged` means the challenger found a blocker or ambiguity
- `challenger.status = not_run` is not allowed on pages that would otherwise pass

If the challenger flags a page:

- set the relevant failed checks if the defect is clear
- otherwise let finalization mark the page `review_status = needs_review`
- overall `status` must remain `fail` so downstream optimization does not treat it as complete

## Checklist Discipline

Rules:

- Judge the rendered page, not the source text in isolation.
- Mark `not_applicable` sparingly.
- If a page has bullets, icons, tables, forms, signatures, or branded footer/header elements, the related checks are usually applicable.
- Every failed page must include at least one issue entry and a remediation summary.
- Keep summaries factual and short.

## Specific Evidence Rule

Generic evidence is invalid.

Bad evidence:

- `No overlap, clipping, duplicate draws, or spillover are visible.`
- `Translated text remains readable at normal zoom on the rendered page.`
- `Layout matches the source page.`

Good evidence:

- `Bottom software-used block: second bullet text overlaps the green check icon and spills into the left gutter.`
- `Middle paragraph under "NEW:" stays within the text column and does not cross the signature scribbles at the footer edge.`

The finalizer rejects generic or duplicated evidence strings.

## Scoring

Do not improvise scoring.

The script computes:

- page score from weighted checklist passes over applicable checks
- page pass/fail from score plus blocking-check failures
- overall score from the average page score
- overall pass/fail from page outcomes plus document-level checks
- review status from challenger results

Thresholds and weights live in `scripts/run_babel_copy_qa.py` and are documented in `references/checklist.md`.

## Model Choice

Default to `gpt-5.4-mini`.

Escalate to `gpt-5.4` only when one of these is true:

- subtle bilingual legal wording is genuinely ambiguous
- a render defect could plausibly be either harmless raster noise or a real blocker
- the user explicitly wants a higher-confidence final sign-off pass

## Sub-Agent Pattern

Use sub-agents only when the batch is large enough to justify coordination.

Good split points:

- one sub-agent per `comparison-report.json`
- one sub-agent per page range for documents longer than 12 pages

Use `gpt-5.4-mini` sub-agents for page inspection when:

- reports are independent
- page ownership is disjoint
- the main agent remains the sole aggregator

Keep the main agent responsible for:

- preparing scaffolds
- merging page findings into the canonical `qa-report.json`
- running `finalize`
- preserving baton metadata for the optimizer

Do not let multiple agents edit the same `qa-report.json` concurrently.

## Mean Diff

Treat `mean_diff` as a routing hint only.

- higher values suggest more visual change
- lower values do not guarantee correctness
- never pass or fail a page from `mean_diff` alone

Use it to prioritize inspection, not to replace inspection.

## Known Failure Modes

Read `references/failure-examples.md` when tuning the review on overlap-heavy pages.

This file contains concrete examples of pages that must fail even when a generic first glance looks “mostly fine.”

## Final Check

Before handoff:

- run `finalize`
- confirm the script reports no validation errors
- confirm every passing page has hotspot coverage and challenger clearance
- confirm the report still carries run-manifest baton fields when they exist
