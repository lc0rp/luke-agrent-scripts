---
name: brief
description: Run a configured CEO brief from an Obsidian brief spec. Use when the user says "/brief <topic> <days>", "brief <topic> <days>", "brief <topic> last", or asks to generate a dated brief from a topic-specific brief template. Supports explicit day windows, defaults to 7 days, and returns a link to the created brief.
---

# Brief

Generate a dated CEO brief from a project-specific brief spec in Luke's Obsidian Onafriq vault.

## Command Shape

- `/brief <topic> <days>`
- `brief <topic> <days>`
- `brief <topic>`
- `brief <topic> last`
- `brief list topics`
- `brief help`

Examples:

- `brief AI 7`: generate the AI brief for the past 7 days
- `brief AI 1`: generate the AI brief for the past 1 day
- `brief AI`: generate the AI brief for the past 7 days
- `brief AI last`: generate from the last generated brief to now
- `brief list topics`: list available configured brief topics
- `brief help`: show command usage and examples

## Workflow

1. Parse the request.
2. If the request is `brief help`, print usage and stop.
3. If the request is `brief list topics`, list topics and stop.
4. Resolve `<topic>` to a brief spec note.
5. Read the resolved spec note and its base template.
6. Determine the report window.
7. Gather sources exactly as the spec requires.
8. Create a new dated brief note in the configured output folder.
9. Return a clickable link to the created brief and list any source gaps.

## Topic Resolution

Run the helper from the vault root when possible:

```bash
python3 /Users/luke/dev/luke-agent-scripts/skills/brief/scripts/resolve_brief.py "<topic>"
```

For topic listing:

```bash
python3 /Users/luke/dev/luke-agent-scripts/skills/brief/scripts/resolve_brief.py --list
```

For command help:

```bash
python3 /Users/luke/dev/luke-agent-scripts/skills/brief/scripts/resolve_brief.py --help-command
```

The helper searches for `*weekly CEO brief.md` specs and matches against:

- `<project-name>` in the spec
- filename words
- parent folder words

If exactly one match is returned, use it. If multiple matches are returned, ask Luke which one to use. If none are returned, search manually with `rg --files` before asking.

Known examples in the Onafriq vault:

- `AI` -> `1-Projects/AI enablement/Weekly CEO brief/AI weekly CEO brief.md`
- `Stablecoin` -> `1-Projects/Stablecoin enablement/Weekly CEO brief/Stablecoin weekly CEO brief.md`
- `Cards` or `Card Issuing` -> `1-Projects/Weekly briefs/Card Issuing Weekly CEO brief/Card Issuing Weekly CEO brief.md`
- `Agency` -> `1-Projects/Weekly briefs/Agency Weekly CEO brief/Agency Weekly CEO brief.md`
- `Network` -> `1-Projects/Weekly briefs/Network Weekly CEO brief/Network Weekly CEO brief.md`
- `Platform` -> `1-Projects/Weekly briefs/Platform Weekly CEO brief/Platform Weekly CEO brief.md`
- `FX`, `FinOps`, or `FX & FinOps` -> `1-Projects/Weekly briefs/FX & FinOps Weekly CEO brief/FX & FinOps Weekly CEO brief.md`

## Duration Rules

- If `<days>` is omitted, use `7`.
- If `<days>` is a positive integer, set the source window to the past `<days>` days through now.
- If `<days>` is `last`, find the most recent generated dated brief in the configured output folder and set the source window from that brief date through now.
- If `last` is requested and no prior generated brief exists, fall back to `7` days and state the fallback.
- Do not edit the spec's permanent `<report-duration>` for a one-off run; treat the requested duration as a run-time override.

## Output Rules

- Follow the topic spec and inherited base template exactly.
- Use the spec's configured output folder.
- Do not overwrite an existing brief.
- Prefer the standard filename from the spec: `YYYY-MM-DD <project-name> CEO brief.md`.
- If that filename already exists, create a non-overwriting same-day variant such as `YYYY-MM-DD <project-name> CEO brief - HHMM.md`.
- Use native Markdown footnotes and define them under `## References` when the base template requires references.
- Return a clickable local Markdown link to the created note as the primary result.
- Also include source gaps or blockers, if any.

## Source Handling

- Treat the spec note as the project-specific source of truth.
- Treat the base template named by the spec as inherited instructions.
- Respect disabled sources.
- For explicit day windows, search sources after the computed start date.
- For `last`, use the last generated brief for continuity, then reground claims in fresh sources since that brief.
- Surface gaps where they affect interpretation.

## Final Response Shape

Keep the response short:

```md
Created [YYYY-MM-DD <topic> CEO brief.md](/absolute/path/to/file.md).

Source gaps: <brief sentence, or "None surfaced.">
```

For `brief list topics`, return a compact list of topic names and spec links.

For `brief help`, return:

```md
Usage: `brief <topic> [days|last]`

Examples: `brief AI 7`, `brief Cards 1`, `brief Stablecoin last`, `brief list topics`
Default duration: 7 days.
```
