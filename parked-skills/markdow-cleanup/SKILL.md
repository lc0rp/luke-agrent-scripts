---
name: markdown-cleanup
description: Fixes common markdownlint-cli2 errors that cannot be autofixed, specifically MD036 (emphasis as heading) and MD052 (reference links).
---

# Markdown Cleanup Guidelines

Enforce the following rules when editing Markdown files:

## MD036: No Emphasis as Heading

Avoid using bold text as a pseudo-heading.

- **Incorrect**: `**Minor heading**`
- **Correct**:
  - Use a real heading: `## Minor heading` (if hierarchy permits)
  - Or use a labeled list item: `**Minor heading:**`

## MD052: Reference Links and Images

Ensure reference links are properly spaced and defined.

- **Incorrect**: `[Label][Ref]` (missing space)
- **Correct**: `[Label] [Ref]`
