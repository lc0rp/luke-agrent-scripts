---
name: babel-copy-qa
description: Review one or more babel-copy or translate-in-place `comparison-report.json` files and produce deterministic `qa-report.json` outputs with page-level pass/fail verdicts, checklist-derived scores, and exact remediation notes. Use this whenever the user asks to QA translated PDF comparison renders, rate pages, score a translation output, decide sign-off readiness, or turn side-by-side comparison images into a structured report.
---

# Babel Copy QA

Use this skill to turn side-by-side comparison renders into a consistent QA decision.

This skill is optimized for `gpt-5.4-mini`. Keep the workflow narrow, explicit, and schema-driven. Prefer deterministic scoring over open-ended prose.

## Input

One or more `comparison-report.json` files produced by `babel-copy` or compatible pipelines.

Each report should contain:

- source and translated PDF paths
- page counts
- per-page `side_by_side_image`
- per-page `mean_diff`

## Output

Write exactly one `qa-report.json` next to each input `comparison-report.json`.

Default output path:

- `<compare-dir>/qa-report.json`

When the comparison report belongs to a standard `babel-copy` run directory, also carry forward the sibling `run-manifest.json` metadata into the QA report. This is the canonical hand-off to `babel-copy-optimizer` and to batch automation loops.

Use the exact schema in `references/qa-report-schema.md`.

## Fast Path

1. Run `python scripts/run_babel_copy_qa.py prepare <comparison-report-or-dir>...`
2. Review every page image listed in the scaffolded `qa-report.json`
3. Fill page checks, issues, summaries, and remediation notes
4. Run `python scripts/run_babel_copy_qa.py finalize <comparison-report-or-dir>...`

The script enforces the checklist shape and computes page and document scores.

## Checklist Discipline

Read `references/checklist.md` before grading pages.

Rules:

- Judge the rendered page, not the source text in isolation.
- Use `pass`, `fail`, or `not_applicable` only.
- Mark `not_applicable` sparingly. If a page has a list, table, form, stamp, icon, logo, or footer, the related check is usually applicable.
- Every failed check must include concrete evidence and a concrete remediation.
- Every failed page must include at least one issue entry plus a short remediation summary.
- Keep summaries short and factual.

## Scoring

Do not improvise scoring.

The script computes:

- page score from weighted checklist passes over applicable checks
- page pass/fail from score plus blocking-check failures
- overall score from the average page score
- overall pass/fail from page outcomes plus document-level checks

Thresholds and weights live in `scripts/run_babel_copy_qa.py` and are documented in `references/checklist.md`.

## Model Choice

Default to `gpt-5.4-mini`.

Escalate to `gpt-5.4` only when one of these is true:

- the page has subtle bilingual legal wording issues that are hard to judge visually
- the render defect is ambiguous and could be either acceptable compression noise or a real layout failure
- the document is being prepared for final external sign-off and the user explicitly wants a higher-confidence second pass

## Sub-Agent Pattern

Use sub-agents only when the batch is large enough to justify it.

Good split points:

- one sub-agent per `comparison-report.json`
- one sub-agent per page range for documents longer than 12 pages

Use `gpt-5.4-mini` sub-agents for page inspection when:

- reports are independent
- page ownership is disjoint
- the main agent can remain the sole aggregator

Keep the main agent responsible for:

- preparing scaffolds
- merging sub-agent findings into the canonical `qa-report.json`
- running `finalize`
- resolving cross-page consistency

Do not have multiple agents edit the same `qa-report.json` concurrently. Give each sub-agent a disjoint page set and merge once.

## Review Scope

Default review scope:

- if the document has 20 pages or fewer, inspect every page
- if the document has more than 20 pages, inspect every page with visible defects plus the first page, last page, and every page with tables, forms, signatures, diagrams, or branded layouts

If the user asks for full QA, inspect every page regardless of length.

## Page Review Order

Review in this order:

1. obvious geometry and layout failures
2. text readability and collisions
3. tables, lists, form structure
4. headers, footers, branding, logos
5. non-text artifacts
6. target-language quality and terminology consistency

This order is deliberate. `gpt-5.4-mini` is reliable when the visual failure scan happens before wording nuance.

## Mean Diff

Treat `mean_diff` as a routing hint only.

- higher values suggest more visual change
- lower values do not guarantee correctness
- never pass or fail a page from `mean_diff` alone

Use it to prioritize pages for inspection, not to replace inspection.

## Writing Findings

Issue entries should be terse and actionable.

Good:

- evidence: `Bottom bullet text overlaps the green check icons and wraps into the left margin.`
- remediation: `Rebuild the software-used bullet block with wider text boxes and preserve icon gutters before rerunning comparison.`

Bad:

- evidence: `Looks off.`
- remediation: `Fix formatting.`

## Final Check

Before handoff:

- run `finalize`
- confirm the script reports no validation errors
- spot-check that each failed page has evidence and remediation that match the rendered image
