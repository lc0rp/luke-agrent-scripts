---
type: Reference
primary_audience: Documentation owners and contributors
owner: Documentation program
last_verified: 2026-02-06
next_review_by: 2026-05-06
source_of_truth: ./documentation_playbook.md
---

# Metadata Schema (Required Fields)

Every page must include the fields below in frontmatter:

```yaml
---
type: Tutorial | How-to | Reference | Concept
primary_audience: <one primary audience>
owner: <role or team>
last_verified: YYYY-MM-DD or product version
next_review_by: YYYY-MM-DD
source_of_truth: <link to PRD/spec/code/policy/ticket>
---
```

Rules:

- Use one `primary_audience` per page.
- Do not use a person name as the only owner. Use a role or team.
- `source_of_truth` must not be a self-link. It must be an external source or a deeper canonical artifact.
