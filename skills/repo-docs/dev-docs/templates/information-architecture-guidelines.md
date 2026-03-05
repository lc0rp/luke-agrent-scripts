# Information architecture guidelines (for LLM and humans)

Purpose of this document: keep the project dev-docs IA consistent, link-clean, and traceable after the migration to the numbered
dev-docs tree.

'Dev-docs' documents in-flight development work. The target user is a fellow developer working on the project, or a hand-off to another team. It answers: what is being built and what has been built. For user-facing documentation or future audiences, readers should be advised to see the `docs/` or `user-docs/` folders.

## Ground rules

- Use the numbered lifecycle folders only:
  - {{FOLDER_STRUCTURE}}
  <!-- Replace with lifecycle folder structure. 00-foundation, 01-product, 02-research, 03-design, 04-architecture,
  05-planning, 06-delivery, 07-quality, 08-operations, 09-user-docs, 99-archive. !-->
- Every top-level folder must contain an `index.md` describing purpose, subfolders, owners, and update cadence.
- Standardize on markdown links (no wikilinks). Relative links should be the shortest correct path from the current
  file.
- When adding new content, update the nearest index to include it and ensure it traces back to PRD/epic/spec where
  relevant.
- Archive, don’t delete: move superseded dev-docs into `99-archive/` with a one-line reason and successor link.

## Commands

- Check links: `pnpm run lint:links`
- Check IA shape: `pnpm run lint:ia`
- Fix wikilinks to markdown (if any): `pnpm run lint:links:fix`

## How to add dev-docs

1. Pick the correct lifecycle folder and create or reuse a subfolder; avoid new top-level buckets.
2. Add/update `index.md` to mention the new file and its owner.
3. Link back to the source of truth (PRD, epic, spec) and forward to tests/runbooks as applicable.
4. Run `pnpm run lint:links` and `pnpm run lint:ia` before opening a PR.

## Migration notes

<!-- If migrating existing dev-docs, document all changes in a migration note in
`dev-docs/06-delivery/migrations/dev-docs-update-<date>/notes.md`. And append a note to this section !-->

{{MIGRATION_NOTES}}

## Ownership

- Information architect / tech writer maintains this skill file and `dev-docs/README.md`.
- Scrum master ensures indexes are fresh at sprint boundaries.
- Reviewers enforce IA checks in PRs (run lint tasks in CI).
