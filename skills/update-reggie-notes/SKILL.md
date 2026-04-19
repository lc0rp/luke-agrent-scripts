---
name: update-reggie-notes
description: Scheduled wiki maintenance for Obsidian-Reggie-Notes.
homepage: /Users/luke/Documents/Obsidian-Reggie-Notes
---

# update-reggie-notes

Use this skill for recurring wiki maintenance in `Obsidian-Reggie-Notes`.

## Trigger

- “schedule wiki maintenance”, “update reggie notes index”, “run reggie pipeline”, or as a scheduled automation.

## Execution flow

Run:
1. `python3 scripts/wiki.py sync-sources --ingest`
2. `python3 scripts/wiki.py reindex`
3. `python3 scripts/wiki.py lint`

## Notes

- Keep cadence and execution command chain in the repo automation.
- `lint` is optional for runtime health checks; it can be skipped in resource-constrained situations.
- Prefer `SOURCES.md` as the authoritative source list (paths and URLs) and preserve deterministic maintenance behavior.
