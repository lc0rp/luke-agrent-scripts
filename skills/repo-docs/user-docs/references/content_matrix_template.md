---
type: Reference
primary_audience: Documentation owners and contributors
owner: Documentation program
last_verified: 2026-02-06
next_review_by: 2026-05-06
source_of_truth: ./documentation_playbook.md
---

# Content Matrix Template (Audience + Intent + Lifecycle)

Use this to plan the doc set before writing.

## Example format (simple list)

Builders:

- Implement: Tutorial: “Run locally to first success”
- Change: How-to: “Deploy a preview build”
- Troubleshoot: Reference: “Common errors and fixes”

Testers:

- Implement: Reference: “Test levels and scope”
- Implement: How-to: “Run the full gate locally”
- Change: How-to: “Release verification checklist”
- Troubleshoot: Reference: “Common test failures and fixes”

Operators:

- Implement: Tutorial: “Publish a content change end to end”
- Change: How-to: “Add a new field to the content model”
- Troubleshoot: Reference: “Parser warnings”

Users:

- Use: Tutorial: “Find a product and understand ownership”
- Use: How-to: “Export as CSV”
- Troubleshoot: How-to: “No results for a search”

## Rules

- Use one intent per page.
- Use the smallest set that covers the top user jobs.
- Add more pages only when users ask the same questions repeatedly.
