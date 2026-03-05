# Information architecture guidelines (for LLM (large language model) and humans)

Purpose: keep documentation structure consistent, with clean links, and easy to follow for people and LLMs.

## Ground rules

- Use only the numbered project-stage folders:
  - {{FOLDER_STRUCTURE}}
  <!-- Replace with lifecycle folder structure. 00-foundation, 01-product, 02-research, 03-design, 04-architecture,
  05-planning, 06-delivery, 07-quality, 08-operations, 09-user-docs, 99-archive. -->
- Every top-level folder must contain an `index.md` describing purpose, subfolders, owners, and update schedule.
- Use markdown links only (no wikilinks). Use the shortest correct relative path.
- Every page lists `Type` and `Primary audience` in frontmatter or the header block.
- Use one doc type per page.
- Archive, do not delete. Move replaced docs to `99-archive/` with a one-line reason and successor link.

## Required metadata

Exempt: `docs/README.md` and any `index.md`.

Use frontmatter (best) or the header block.

Frontmatter:

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

Standard header block:

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
- If the page is single-audience, do not add `For:` tags.

## Indexing

- List each new page in the nearest `index.md` with Type + Audience tags.
- Example:
  - [Payments reconciliation runbook](./reconciliation-runbook.md) — Type: How-to; Audience: Support and operations

## Hubs

- Hubs only link to other pages. Do not duplicate content.
- Hubs list start points for each journey stage: Discover, Evaluate, Implement, Use, Operate, Change, Troubleshoot, Decommission.

## Glossary

- Glossary is a Reference-type page.
- Recommended locations:
  - External: `docs/09-user-docs/reference/glossary.md`
  - Internal: `docs/00-foundation/reference/glossary.md`

## Commands

- Check links: `pnpm run lint:links`
- Check IA shape: `pnpm run lint:ia`
- Check doc metadata (if present): `pnpm run lint:docmeta`

## How to add docs

1. Pick the right project-stage folder and reuse or create a subfolder. No new top-level buckets.
2. Choose the right Diataxis template and keep one doc type per page.
3. Add required metadata.
4. Update `index.md` with Type + Audience tags.
5. Link to the source of truth (PRD (product requirements document), spec, ticket) and to tests/runbooks if relevant.
6. Run `pnpm run lint:links` and `pnpm run lint:ia` before opening a PR.

## Migration notes

<!-- If migrating existing docs, document all changes in a migration note in
`docs/06-delivery/migrations/docs-update-<date>/notes.md`. And append a note to this section. -->

{{MIGRATION_NOTES}}

## Ownership

- Information architect / tech writer maintains this skill file and `docs/README.md`.
- Scrum master ensures indexes are fresh at sprint boundaries.
- Reviewers enforce IA checks in PRs (run lint tasks in CI (continuous integration)).
