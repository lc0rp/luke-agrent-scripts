---
name: ask-reggie
description: Shortcut for querying Obsidian-Reggie-Notes via the local wiki search.
homepage: /Users/luke/Documents/Obsidian-Reggie-Notes
---

# ask-reggie

Use this skill when the user asks a question about the Reggie notes wiki and wants a direct query.

## Default behavior

1. Run `python3 scripts/wiki.py query "<query>" --limit 10` from `/Users/luke/Documents/Obsidian-Reggie-Notes`.
2. If a query has a custom limit request, pass `--limit <n>`.

## Notes

- Querying already prefers `qmd` when available and falls back to deterministic index/body search.
- For broader maintenance tasks, use [$update-reggie-notes](/Users/luke/dev/luke-agent-scripts/skills/update-reggie-notes/SKILL.md).
