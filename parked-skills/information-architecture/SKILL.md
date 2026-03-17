---
name: information-architecture
description:
  Maintain the project documentation IA (numbered lifecycle folders with indexes, markdown-only links, archive
  discipline). Use when adding/moving docs, validating links/IA, or reviewing PRs that touch docs.
---

# Information Architecture Skill

## Quick triggers

- You need to add, move, or rename documentation.
- You see wikilinks or broken/absolute links in docs.
- You must ensure the numbered lifecycle folders remain intact (00–99 with index.md files).
- You are archiving or deprecating docs.

**IMPORTANT**: First read the whole skill before applying it.

**Start here every time**: open `templates/docs-README.md` to confirm the canonical lifecycle order and folder names
before touching anything. The top-level `docs/README.md` in the repo must mirror this template exactly (same order,
same folder names, same links).

## Resources

This skill contains these resources, within the skill folder:

- `references/commands.md`: commands reference for link and IA validation.
- `templates/`: templates for scaffolding the numbered IA folders and readmes.\
  - `docs-README.md` — top-level navigation with numbered lifecycle order.
  - `index.md` — section index scaffold with Purpose/Subfolders/Usage headings.
  - `information-architecture-guidelines.md` — notes for team members on IA conventions.
- `scripts/`: link and IA validation scripts to add to the project.
  - `link-check.mjs` — link validation (checks for broken links and wikilinks).
  - `ia-validate.mjs` — IA structure validation (checks numbered folders, `docs/README.md` order).

## Workflow (follow in order)

0. **Confirm structure**: read `templates/docs-README.md`; ensure `docs/README.md` matches it verbatim (folder order
   and names). Never invent new numbers like `02-planning`—use the exact list below.
1. **Place content**: choose the correct lifecycle folder (00–99) from the canonical list. Do not add new top-level
   buckets. Prefer existing subfolders; create a new subfolder only if it maps to the PRD lifecycle.
2. **Index updates**: edit the nearest `index.md` to list new/changed files, purpose, owner, and update cadence. Keep
   lists concise.
3. **Link discipline**: use markdown links only; shortest relative path from the current file. Avoid wikilinks and
   absolute `/docs/...` paths.
4. **Archive vs delete**: move superseded items to `99-archive/` with a one-line reason and successor link.
5. **Validate**: run `pnpm run lint:links` then `pnpm run lint:ia`. Fix any failures before merging.

### Canonical lifecycle folders (must match `templates/docs-README.md`)

- `00-foundation`
- `01-product`
- `02-research`
- `03-design`
- `04-architecture`
- `05-planning`
- `06-delivery`
- `07-quality`
- `08-operations`
- `09-user-docs`
- `99-archive`

### If the project already has `docs/` that doesn't follow this IA

- Backup first: rename existing `docs/` to `docs-bak` (preserve history).
- Scaffold numbered IA: create `docs/00-foundation` … `docs/99-archive` using the template order. Do not skip any
  numbers, even if unused.
- Copy `templates/docs-README.md` to `docs/README.md` and keep it unchanged except for relative link checks.
- Copy old content from `docs-bak/` into the new structure thoughtfully (match lifecycle), then delete `docs-bak/` only
  after verifying `lint:links` and `lint:ia`.
- Copy `templates/information-architecture-guidelines.md` to `docs/00-foundation/conventions/information-architecture-guidelines.md`.

### If initializing from scratch

- Copy `templates/docs-README.md` to `docs/README.md` first; verify the lifecycle list stays intact.
- Create the numbered folders using the canonical list above and drop in the templates.
- Copy `templates/index.md` into each top-level folder and adjust contents.
- Copy `templates/information-architecture-guidelines.md` to `docs/00-foundation/conventions/information-architecture-guidelines.md`.

### If updating existing documentation

- Start by re-reading `docs/README.md` and `templates/docs-README.md` to confirm structure has not drifted.
- Document all changes you make in a migration note in `docs/06-delivery/migrations/docs-update-<date>/notes.md`.
- Backup any deleted/moved files into the migration folder as well.
- Follow the main workflow above to add/move docs, update indexes, fix links, and archive as needed.

## Scaffold checklist (new project, or non-existing scripts)

- Copy `scripts/link-check.mjs` and `scripts/ia-validate.mjs` into `scripts/`.
- Add or merge these `package.json` scripts (adjust if not using pnpm):

  ```json
  {
    "scripts": {
      "lint:links": "node scripts/link-check.mjs",
      "lint:links:fix": "node scripts/link-check.mjs --fix",
      "lint:ia": "node scripts/ia-validate.mjs",
      "lint": "pnpm run lint:ts && pnpm run lint:md && pnpm run lint:links"
    }
  }
  ```

- Ensure markdown linting exists (`lint:md` via markdownlint-cli2) or drop it from `lint` if unused.
- Create the numbered `docs/` folders (00–99) using the provided templates and ensure each has an `index.md`. Do not skip any numbers, even if unused.
- Replace `docs/README.md` with the template and check lifecycle order.

## Key locations

- Docs root: `docs/`
- Validator scripts: `scripts/link-check.mjs`, `scripts/ia-validate.mjs`
- Migration notes and lifecycle nav: `docs/README.md`
- Conventions reference: `docs/00-foundation/conventions/information-architecture-skill.md`

## Notes for reviewers

- Block changes that add wikilinks or bypass indexes.
- Ensure new folders follow the numeric prefix and include `index.md`.
- Confirm archived files cite their successor.

See references for command details.
