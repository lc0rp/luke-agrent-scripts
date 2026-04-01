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
2. Review every page image listed in each scaffolded `qa-report.json` enough to route applicability and dispatch work
3. For every page, dispatch one sub-agent per checklist check using the page image and that check's definition only
4. Fill the page fields in two passes:
   - defect hunt
   - checklist scoring
5. For every page that would otherwise pass, run a challenger pass
6. `python scripts/run_babel_copy_qa.py finalize <comparison-report-or-dir>...`

The script validates the contract, computes scores, and rejects generic evidence.

The main agent is the sole recorder. Sub-agents return structured findings for one page and one check; the main agent writes those results into the canonical `qa-report.json`.

## Two-Pass Review

Read `references/checklist.md` before grading pages.

Sub-agent isolation is mandatory for checklist scoring:

- dispatch one sub-agent per page per checklist check
- pass each sub-agent only the page image path, page number, `mean_diff`, the assigned check id and check definition, and the minimum applicability guidance needed for that check
- do not pass other check results into a check-review sub-agent
- do not let a sub-agent edit `qa-report.json`
- the main agent records the returned result, evidence, remediation, and any issue candidates in the canonical report
- if a sub-agent reports ambiguity, the main agent should record the most conservative outcome supported by the evidence and use the challenger/manual-review path when needed

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

The main agent owns the defect hunt summary, hotspot coverage, and issue normalization. Sub-agents may suggest issue entries, but only the main agent merges them into the page record.

### Pass 2: Checklist Scoring

Only after the defect hunt:

- fill every checklist item from the corresponding page-check sub-agent result
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

Run the challenger as a separate sub-agent. Give it the page image and page-level context, but not the hidden chain-of-thought or broad session history. It may see the aggregated page findings when that is necessary to attack the current tentative pass decision.

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

Sub-agents are mandatory for checklist scoring.

Required split:

- one sub-agent per page per checklist check
- one challenger sub-agent for every page that would otherwise pass

Recommended sub-agent model:

- `gpt-5.4-mini` for page-check inspection
- `gpt-5.4` only when a specific check is materially ambiguous or high-risk

Keep the main agent responsible for:

- preparing scaffolds
- reviewing each page enough to route applicability and dispatch work
- merging page-check findings into the canonical `qa-report.json`
- writing hotspot reviews, `defect_hunt_summary`, page summaries, and remediation summaries
- running `finalize`
- preserving baton metadata for the optimizer

Do not let sub-agents edit `qa-report.json` at all. The main agent is the only writer.

Dispatch contract for each page-check sub-agent:

- input:
  - page number
  - page image path
  - `mean_diff`
  - assigned check id and check definition
  - concise applicability guidance for that check
- output:
  - `result`: `pass`, `fail`, or `not_applicable`
  - check-specific evidence
  - remediation when `result = fail`
  - optional issue candidate with severity, title, evidence, remediation, and `check_ids`
  - short note if the check is ambiguous and should drive conservative aggregation

Aggregation rules for the main agent:

- record each sub-agent result into the matching check object
- deduplicate issue candidates while preserving check coverage
- prefer the stricter supported outcome when check-level findings conflict
- if evidence is insufficient or ambiguous, bias toward `fail` or challenger/manual review rather than `pass`

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
