# `qa-report.json` Schema

Write one `qa-report.json` next to each `comparison-report.json`.

The recommended flow is:

1. `python scripts/run_babel_copy_qa.py prepare <inputs...>`
2. fill findings in the scaffold
3. `python scripts/run_babel_copy_qa.py finalize <inputs...>`

## Top-Level Shape

```json
{
  "schema_version": "1.0",
  "skill": "babel-copy-qa",
  "comparison_report_path": "/abs/path/comparison-report.json",
  "source_pdf": "/abs/path/source.pdf",
  "translated_pdf": "/abs/path/translated.pdf",
  "run_manifest_path": "/abs/path/run-manifest.json",
  "run_output_dir": "/abs/path/output/F1-20260331T120000Z",
  "document_id": "F1",
  "cycle_id": "20260331T120000Z",
  "run_label": "initial",
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
    "status": "pass",
    "overall_score": 88,
    "quality_band": "good",
    "pages_reviewed": 3,
    "pages_passed": 2,
    "pages_failed": 1,
    "blocking_issue_count": 1,
    "major_issue_count": 0,
    "minor_issue_count": 1,
    "release_recommendation": "fix_required",
    "summary": "Pages 1-2 are acceptable. Page 3 fails due to collision in the software-used bullet block."
  },
  "pages": [
    {
      "page_number": 1,
      "side_by_side_image": "/abs/path/page-001.png",
      "mean_diff": 11.32,
      "status": "pass",
      "score": 90,
      "quality_band": "excellent",
      "failed_checks": [],
      "blocking_failed_checks": [],
      "issue_counts": {
        "blocking": 0,
        "major": 0,
        "minor": 0
      },
      "checks": {
        "layout_structure": {
          "label": "Layout structure and section hierarchy match the source page",
          "weight": 15,
          "blocking": false,
          "result": "pass",
          "evidence": "Section rhythm, heading stack, and list grouping align with the source page.",
          "remediation": ""
        }
      },
      "issues": [],
      "summary": "Readable and structurally faithful page.",
      "remediation_summary": ""
    }
  ],
  "generated_at": "2026-03-31T12:00:00Z"
}
```

## Required Page Fields

Every page must include:

- `page_number`
- `side_by_side_image`
- `mean_diff`
- `status`
- `score`
- `quality_band`
- `failed_checks`
- `blocking_failed_checks`
- `issue_counts`
- `checks`
- `issues`
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

## Issues Array

Each issue object must include:

- `severity`: `blocking`, `major`, or `minor`
- `category`: free text such as `layout`, `translation`, `table`, `branding`, `artifact`
- `title`
- `evidence`
- `remediation`
- `check_ids`: array of related checklist ids

## Validation

`finalize` will fail if:

- a page is missing a required check
- a check has an invalid result
- a failed check lacks evidence or remediation
- a failed page has no issue entry
- a failed page has no remediation summary
- scores or verdicts disagree with the checklist

## Run Metadata

When a sibling `run-manifest.json` exists at `<compare-dir>/../run-manifest.json`, the QA scaffold should copy these fields into `qa-report.json`:

- `run_manifest_path`
- `run_output_dir`
- `document_id`
- `cycle_id`
- `run_label`
- `input_pdf`

These fields let downstream automation and `babel-copy-optimizer` locate the exact originating run without guessing from directory names.
