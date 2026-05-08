---
name: briefs
description: List the latest generated CEO briefs from Luke's Obsidian vault. Use when the user says "/briefs", "briefs", "list briefs", "latest briefs", or wants clickable links to the newest generated brief notes for reading.
---

# Briefs

List the latest generated CEO briefs in Luke's Onafriq Obsidian vault and return clickable local links.

## Command Shape

- `/briefs`
- `briefs`
- `briefs all`
- `briefs <topic>`
- `latest briefs`
- `list briefs`

## Workflow

1. Run the helper from any directory:

```bash
python3 /Users/luke/dev/luke-agent-scripts/skills/briefs/scripts/list_briefs.py
```

2. Return the helper output as concise Markdown links.
3. If the user supplies a topic, pass it as `--topic "<topic>"`.
4. If no briefs are found, say that plainly and include the searched vault path.

## Options

- Default: latest generated brief per topic.
- `briefs all`: use `--all` to list all generated dated briefs, newest first.
- `briefs <topic>`: use `--topic "<topic>"` to filter to one topic.

## Output Rules

- Return clickable local file links.
- Include the date and topic in each line.
- Keep the response short.
- Do not generate new briefs; this skill only lists existing generated briefs.

## Final Response Shape

```md
Latest briefs:

- [2026-04-27 AI CEO brief.md](/absolute/path/to/2026-04-27 AI CEO brief.md)
- [2026-04-27 Stablecoin CEO brief.md](/absolute/path/to/2026-04-27 Stablecoin CEO brief.md)
```

