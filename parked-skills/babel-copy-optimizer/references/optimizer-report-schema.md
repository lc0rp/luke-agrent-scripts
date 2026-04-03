# `optimizer-report` Outputs

Write the final optimizer report next to the handled QA report:

- `<compare-dir>/optimizer-report.md`
- optional `<compare-dir>/optimizer-report.json`

The Markdown report is required. The JSON report is optional but recommended when the run has meaningful structured state.

## What Counts As Handled

A failed `qa-report.json` is considered handled when the same `compare/` directory contains either:

- `optimizer-report.md`
- `optimizer-report.json`

This lets the optimizer skip older already-processed failures and pick the latest outstanding one.

## Required `optimizer-report.md` Sections

Use this exact section order:

```md
# Babel Copy Optimizer Report

## Source QA
## Remediation Goals
## Attempt Log
## Files Touched
## Outcome
## Remaining Risks
```

### Section expectations

- `Source QA`
  - absolute path to the chosen `qa-report.json`
  - absolute path to the sibling `comparison-report.json`
  - why the report was chosen as the latest unhandled failed report
- `Remediation Goals`
  - flat list of the concrete failed checks and issue remediations being targeted
- `Attempt Log`
  - one subsection per attempt with timestamp, output dir, changes made, and QA result
- `Files Touched`
  - absolute paths to every edited `babel-copy` file
- `Outcome`
  - one of `met`, `partially_met`, `not_met`
  - short explanation tied to the latest QA report
- `Remaining Risks`
  - only the unresolved risks or follow-up engineering work

## Recommended `optimizer-report.json` Shape

```json
{
  "schema_version": "1.0",
  "skill": "babel-copy-optimizer",
  "source_qa_report": "/abs/path/qa-report.json",
  "source_comparison_report": "/abs/path/comparison-report.json",
  "status": "completed",
  "goal_status": "met",
  "attempts": [
    {
      "attempt": 1,
      "timestamp": "2026-03-31T18:15:00Z",
      "output_dir": "/abs/path/output/F2-optimizer-20260331T181500Z",
      "files_touched": [
        "/abs/path/skills/babel-copy/scripts/build_final_pdf.py"
      ],
      "changes_summary": [
        "Expanded overlay fit width for dense footer blocks."
      ],
      "compare_report": "/abs/path/output/F2-optimizer-20260331T181500Z/compare/comparison-report.json",
      "qa_report": "/abs/path/output/F2-optimizer-20260331T181500Z/compare/qa-report.json",
      "qa_status": "fail",
      "remaining_remediations": [
        "Page 19 footer still collides with divider rule."
      ]
    }
  ],
  "final_recommendation": "ready",
  "summary": "Second attempt cleared the targeted footer and table collisions without introducing regressions."
}
```

## JSON Field Guidance

- `status`
  - `completed`, `stopped`, or `no_action_needed`
- `goal_status`
  - `met`, `partially_met`, or `not_met`
- `attempts`
  - ordered oldest to newest
- `remaining_remediations`
  - empty array when goals are fully met

Keep the JSON factual. Put narrative reasoning in the Markdown report.
