# `qa-report.json` Schema

Write one `qa-report.json` next to each `comparison-report.json`.

Recommended flow:

1. `python scripts/run_babel_copy_qa.py prepare <inputs...>`
2. fill findings in the scaffold
3. `python scripts/run_babel_copy_qa.py finalize <inputs...>`

## Contract Notes

- Keep `overall.status` as `pass` or `fail` so downstream optimizer tooling keeps working.
- Use `review_status` fields to signal challenger ambiguity or manual-review escalation.
- Preserve run-manifest baton fields when they exist.

## Top-Level Shape

```json
{
  "schema_version": "1.1",
  "skill": "babel-copy-qa",
  "comparison_report_path": "/abs/path/comparison-report.json",
  "source_pdf": "/abs/path/source.pdf",
  "translated_pdf": "/abs/path/translated.pdf",
  "run_manifest_path": "/abs/path/run-manifest.json",
  "run_output_dir": "/abs/path/output/F1-20260331T120000Z",
  "document_id": "F1",
  "cycle_id": "20260331T120000Z",
  "run_label": "initial",
  "run_id": "20260331T120000Z-initial",
  "input_pdf": "/abs/path/source.pdf",
  "document_checks": {
    "page_count_match": {
      "label": "Source and translated PDFs have the same page count",
      "result": "pass",
      "evidence": "source_pages=3 translated_pages=3",
      "remediation": ""
    },
    "comparison_assets_present": {
      "label": "Every side-by-side comparison image exists",
      "result": "pass",
      "evidence": "All 3 comparison images resolved on disk.",
      "remediation": ""
    }
  },
  "overall": {
    "status": "fail",
    "review_status": "needs_review",
    "overall_score": 83,
    "quality_band": "good",
    "pages_reviewed": 3,
    "pages_passed": 2,
    "pages_failed": 1,
    "needs_review_count": 1,
    "blocking_issue_count": 1,
    "major_issue_count": 0,
    "minor_issue_count": 1,
    "review_gate_reasons": [
      "Page 3 challenger flagged a blocker in the bottom bullet block."
    ],
    "release_recommendation": "manual_review_required",
    "summary": "Pages 1-2 are acceptable. Page 3 needs manual review because the challenger found a blocker in the software-used bullets."
  },
  "pages": [
    {
      "page_number": 1,
      "side_by_side_image": "/abs/path/page-001.png",
      "mean_diff": 11.32,
      "status": "pass",
      "review_status": "confirmed",
      "score": 95,
      "quality_band": "excellent",
      "failed_checks": [],
      "blocking_failed_checks": [],
      "issue_counts": {
        "blocking": 0,
        "major": 0,
        "minor": 0
      },
      "hotspot_reviews": {
        "top_band": {
          "label": "Top band",
          "anchor_hint": "header, logo, title, or top-page branding area",
          "status": "checked",
          "notes": "Top title block stays within the heading area and clears the logo."
        },
        "middle_band": {
          "label": "Middle band",
          "anchor_hint": "mid-page body text region",
          "status": "checked",
          "notes": "Middle body paragraphs stay inside the text column with stable line spacing."
        },
        "bottom_band": {
          "label": "Bottom band",
          "anchor_hint": "footer or bottom-page content area",
          "status": "checked",
          "notes": "Bottom footer remains aligned and does not collide with the translated body text."
        },
        "densest_region": {
          "label": "Densest region",
          "anchor_hint": "the most crowded translated text block on the page",
          "status": "checked",
          "notes": "The densest list block under section 1 keeps bullet indentation and line breaks."
        },
        "structured_region": {
          "label": "Structured region",
          "anchor_hint": "lists, bullets, tables, forms, signatures, icons, or artifact-heavy block",
          "status": "checked",
          "notes": "The bullet list beneath section 1 keeps consistent icon spacing and indentation."
        }
      },
      "checks": {
        "text_overlap_absent": {
          "label": "No text overlaps or text-on-text collisions are visible",
          "weight": 15,
          "blocking": true,
          "result": "pass",
          "evidence": "Middle section body lines remain separated and do not cross the neighboring paragraph block.",
          "remediation": ""
        }
      },
      "challenger": {
        "status": "clear",
        "summary": "Second pass found no blocker after reviewing the top title area, middle body, and densest list block.",
        "findings": []
      },
      "issues": [],
      "defect_hunt_summary": "No visible blocker found during the first-pass defect scan.",
      "summary": "Readable and structurally faithful page.",
      "remediation_summary": ""
    }
  ],
  "generated_at": "2026-03-31T12:00:00Z"
}
```

## Top-Level Baton Fields

When a sibling `run-manifest.json` exists at `<compare-dir>/../run-manifest.json`, copy these fields into `qa-report.json`:

- `run_manifest_path`
- `run_output_dir`
- `document_id`
- `cycle_id`
- `run_label`
- `run_id`
- `input_pdf`

These fields are part of the optimizer handoff contract.

## Required Page Fields

Every page must include:

- `page_number`
- `side_by_side_image`
- `mean_diff`
- `status`
- `review_status`
- `score`
- `quality_band`
- `failed_checks`
- `blocking_failed_checks`
- `issue_counts`
- `hotspot_reviews`
- `checks`
- `challenger`
- `issues`
- `defect_hunt_summary`
- `summary`
- `remediation_summary`

## Required Check Fields

Each check object must include:

- `label`
- `weight`
- `blocking`
- `result`
- `evidence`
- `remediation`

Allowed `result` values:

- `pass`
- `fail`
- `not_applicable`

## Hotspot Reviews

`hotspot_reviews` must include these keys:

- `top_band`
- `middle_band`
- `bottom_band`
- `densest_region`
- `structured_region`

Each hotspot object must include:

- `label`
- `anchor_hint`
- `status`
- `notes`

Allowed hotspot `status` values:

- `checked`
- `not_present`

## Challenger

Each page must include:

```json
{
  "status": "not_run",
  "summary": "",
  "findings": []
}
```

Allowed challenger statuses:

- `not_run`
- `clear`
- `flagged`

## Issues Array

Each issue object must include:

- `severity`: `blocking`, `major`, or `minor`
- `category`
- `title`
- `evidence`
- `remediation`
- `check_ids`: array of related checklist ids

## Validation

`finalize` fails if:

- a page is missing a required check
- a check has an invalid result
- a failed check lacks evidence or remediation
- a pass/fail evidence string is generic or duplicated on the page
- a page reuses the same evidence string across too many checks or has too few distinct check observations
- mandatory hotspots are incomplete
- a passing page lacks challenger review
- a failed page has no issue entry
- a failed page has no remediation summary
- scores or verdicts disagree with the checklist
