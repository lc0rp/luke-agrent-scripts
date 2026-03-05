---
name: dev-docs
description:
  Maintain the in-flight project documentation throughout the dev process, using numbered lifecycle folders with indexes, markdown-only links, and archive discipline. Use when adding/moving/renaming/updating dev-docs, validating dev-doc links/IA, or reviewing PRs that touch dev-docs.
---

# Dev Docs Information Architecture Skill

'Dev-docs' documents in-flight development work. The target user is a fellow developer working on the project, or a hand-off to another team. It answers: what is being built and what has been built. For user-facing documentation or future audiences, readers should be advised to see the `docs/` or `user-docs/` folders.

## Quick triggers

- You need to add, move, rename or update in-session developer documentation, focused on work in-flight.
- You see wikilinks or broken/absolute links in dev-docs.
- You must ensure the numbered lifecycle folders remain intact (00–99 with index.md files).
- You are archiving or deprecating dev-docs.

**IMPORTANT**: First read the whole skill before applying it.

# Dev Docs (dev-docs) vs User Docs (user-docs)

- Dev-docs is designed for in-flight developer-facing documentation. 
- User-docs is designed for steady-state, user-facing documentation. 
- Dev-docs answers: what is being built and what has been built, for fellow developers. 
- User-docs answers: how do I use this and how does it work, for end users or future audiences, who may include builders/developers, but it's not a place/process for in-flight work documentation.


**Start here every time**: open `templates/dev-docs-README.md` to confirm the canonical lifecycle order and folder names
before touching anything. The top-level `dev-docs/README.md` in the repo must include this template exactly (same order,
same folder names, same links).

## Resources

This skill contains these resources, within the skill folder:

- `references/commands.md`: commands reference for link and IA validation.
- `templates/`: templates for scaffolding the numbered IA folders and readmes.
  - `dev-docs-README.md` — top-level navigation with numbered lifecycle order.
  - `index.md` — section index scaffold with Purpose/Subfolders/Usage headings.
  - `information-architecture-guidelines.md` — notes for team members on IA conventions.
- `scripts/`: link and IA validation scripts to add to the project.
  - `link-check.mjs` — link validation (checks for broken links and wikilinks).
  - `ia-validate.mjs` — IA structure validation (checks numbered folders, `dev-docs/README.md` order).

## Workflow (follow in order)

0. **Confirm structure**: read `templates/dev-docs-README.md`; ensure `dev-docs/README.md` matches it verbatim (folder order
   and names). Never invent new numbers like `02-planning`—use the exact list below.
1. **Place content**: choose the correct lifecycle folder (00–99) from the canonical list. Do not add new top-level
   buckets. Prefer existing subfolders; create a new subfolder only if it maps to the PRD lifecycle.
2. **Index updates**: edit the nearest `index.md` to list new/changed files, purpose, owner, and update cadence. Keep
   lists concise.
3. **Link discipline**: use markdown links only; shortest relative path from the current file. Avoid wikilinks and
   absolute `/docs/...` paths.
4. **Archive vs delete**: move superseded items to `99-archive/` with a one-line reason and successor link.
5. **Validate**: run `pnpm run lint:links` then `pnpm run lint:ia`. Fix any failures before merging.
6. **AGENTS.md integration**: optimize access and adherence for future readers/contributors by adding or updating project-level `AGENTS.md` to include/incorporate the short IA declaration plus canonical tree from `templates/dev-docs-README.md`.

### Canonical lifecycle folders (Example only below. Absolute source of truth is `templates/dev-docs-README.md`. Folder list must match exactly.)

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

### If the project already has `dev-docs/` that doesn't follow this IA

- Backup first: rename existing `dev-docs/` to `dev-docs-bak` (preserve history).
- Scaffold numbered IA: create `dev-docs/00-foundation` … `dev-docs/99-archive` using the template order. Do not skip any
  numbers, even if unused.
- Copy `templates/dev-docs-README.md` to `dev-docs/README.md` and keep it unchanged except for relative link checks.
- Copy old content from `dev-docs-bak/` into the new structure thoughtfully (match lifecycle), then delete `dev-docs-bak/` only
  after verifying `lint:links` and `lint:ia`.
- Copy `templates/information-architecture-guidelines.md` to `dev-docs/00-foundation/conventions/information-architecture-guidelines.md`.
- Ensure project-level `AGENTS.md` exists and includes the IA declaration and tree from the template.

### If initializing from scratch

- Copy `templates/dev-docs-README.md` to `dev-docs/README.md` first; verify the lifecycle list stays intact.
- Create the numbered folders using the canonical list above and drop in the templates.
- Copy `templates/index.md` into each top-level folder and adjust contents.
- Copy `templates/information-architecture-guidelines.md` to `dev-docs/00-foundation/conventions/information-architecture-guidelines.md`.
- Create or update project-level `AGENTS.md` to include a "## Project documentation structure" section that declares the IA rules, and include the tree in a fenced code block.

### If updating existing documentation

- Start by re-reading `dev-docs/README.md` and `templates/dev-docs-README.md` to confirm structure has not drifted.
- Document all changes you make in a migration note in `dev-docs/06-delivery/migrations/dev-docs-update-<date>/notes.md`.
- Backup any deleted/moved files into the migration folder as well.
- Follow the main workflow above to add/move docs, update indexes, fix links, and archive as needed.
- Ensure project-level `AGENTS.md` exists and includes a "## Project documentation structure" section with the IA declaration and tree from the template.

## AGENTS.md content (use when initializing or updating a project)

Optimize documentation access and adherence for future readers/contributors by adding or updating project-level `AGENTS.md` to include "## Project documentation structure" section with a short IA declaration plus canonical tree below. Use the exact tree and keep it in sync with `templates/dev-docs-README.md`.

```markdown
## Project documentation structure

For readers: This project follows a strict information architecture structure for its documentation, using the numbered lifecycle folders listed below. Each contains an index with links to its contents.

For contributors: When adding, updating, or moving documentation, follow the strict IA conventions documented in dev-docs/00-foundation/conventions/information-architecture-guidelines.md.

Documentation tree:
dev-docs/
  00-foundation/
  01-product/
  02-research/
  03-design/
  04-architecture/
  05-planning/
  06-delivery/
  07-quality/
  08-operations/
  09-user-docs/
  99-archive/
```

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
- Create the numbered `dev-docs/` folders (00–99) using the provided templates and ensure each has an `index.md`. Do not skip any numbers, even if unused.
- Replace `dev-docs/README.md` with the template and check lifecycle order.

## Key locations

- Docs root: `dev-docs/`
- Validator scripts: `scripts/link-check.mjs`, `scripts/ia-validate.mjs`
- Migration notes and lifecycle nav: `dev-docs/README.md`
- Conventions reference: `dev-docs/00-foundation/conventions/information-architecture-skill.md`

## Notes for reviewers

- Block changes that add wikilinks or bypass indexes.
- Ensure new folders follow the numeric prefix and include `index.md`.
- Confirm archived files cite their successor.

See references for command details.
