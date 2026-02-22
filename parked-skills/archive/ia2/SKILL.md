---
name: ia2
description:
  Maintain documentation structure with project-stage folders, one doc type per page, and clear audience metadata.
---

# IA2 Skill (Information Architecture v2)

## Quick triggers

- You need to add, move, rename, or update documentation.
- You see mixed intent on a page (tutorial + reference, etc).
- You need clear coverage for each audience or audience tagging.
- You are reviewing PRs that touch docs.

## Start here every time

1. Open `templates/docs-README.md` and confirm the standard folder order.
2. Ensure the repo `docs/README.md` matches the template order and links.

## Core rules

- Keep top-level project-stage folders unchanged. Do not add new top-level buckets.
- Every page states its purpose and audience. Use frontmatter or the standard header block.
- One doc type per page.
- Use markdown links only. No wikilinks or absolute `/docs/...` links.
- Archive, do not delete. Move replaced docs to `99-archive/` with a successor link.
- Use clear, simple wording. Prioritize ESL-friendly language.

## Required metadata (on every content page)

Not required for `docs/README.md` or any `index.md`.

Frontmatter (best):

```
---
type: Tutorial | How-to | Reference | Concept
primary_audience: <one primary audience>
owner: <role or team>
last_verified: YYYY-MM-DD or product version
next_review_by: YYYY-MM-DD
source_of_truth: <link>
---
```

Header block (allowed if frontmatter is not used):

```
Type: Tutorial | How-to | Reference | Concept
Primary audience: <one primary audience>
Owner: <role or team>
Last verified: YYYY-MM-DD or product version
Next review by: YYYY-MM-DD
Source of truth: <link>
```

Audience tags in sections:

- Use `For: <audience>` only when the audience changes in a page.
- If the page has a single audience, do not add `For:` tags.

## Audience list (use one primary audience)

External:
- Non-users/buyers
- Admins/operators
- End users
- Developers/partners

Internal:
- Sales and marketing
- Support and operations
- Engineers
- Leadership
- Risk/compliance/audit

## Steps (in order)

0. Confirm structure from `templates/docs-README.md`.
1. Place content in the correct project-stage folder. Create subfolders only when needed.
2. Choose the correct Diataxis template from `templates/diataxis/` and keep one doc type per page.
3. Add required metadata (frontmatter preferred).
4. Update the nearest `index.md` with Audience + Type tags for each new page.
5. Add or update hub pages (pages that only link) when needed.
6. Archive replaced content to `99-archive/` with a one-line reason and successor link.
7. Validate links and structure; validate doc metadata if scripts exist.

## Index rules

Each index entry must include the page `Type` and `Primary audience` in a short tag.
Example:

- [Payments reconciliation runbook](./reconciliation-runbook.md) — Type: How-to; Audience: Support and operations

## Hubs (pages that only link to other pages)

- Hubs list start points for each journey stage (Discover, Evaluate, Implement, Use, Operate, Change, Troubleshoot, Decommission).
- Hubs only link to source pages. Do not duplicate content.

## Glossary

- Glossary is a Reference page (lookup intent).
- Recommended locations:
  - External: `docs/09-user-docs/reference/glossary.md`
  - Internal: `docs/00-foundation/reference/glossary.md`

## Continuity docs (agents and engineers)

- Continuity and handoff content must map to an existing Diataxis type:
  - How-to: handoff steps, checklist, current state, next actions.
  - Concept: why we chose it, key decisions, system overview.
- Do not create a new doc type.

## Templates

- `templates/docs-README.md`
- `templates/index.md`
- `templates/information-architecture-guidelines.md`
- `templates/doc-metadata.md`
- `templates/diataxis/tutorial.md`
- `templates/diataxis/how-to.md`
- `templates/diataxis/reference.md`
- `templates/diataxis/concept.md`

## Scripts

- `scripts/docmeta-lint.mjs`
- `scripts/acronym-report.mjs`

## Checks

- Links: `pnpm run lint:links`
- IA: `pnpm run lint:ia`
- Doc metadata (if present): `pnpm run lint:docmeta`
- Acronym report (report-only): `node scripts/acronym-report.mjs`

## Review checklist

- Block pages that mix Diataxis types.
- Block pages missing required metadata.
- Ensure indexes include Type + Audience tags.
- Ensure hub pages are routing only, not content sources.
