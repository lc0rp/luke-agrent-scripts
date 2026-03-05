---
type: Reference
primary_audience: Operators
owner: Automation tooling maintainers
last_verified: 2026-03-04
next_review_by: 2026-06-04
source_of_truth:
  - ./index.ts
  - ./openclaw.plugin.json
  - ./run-command.test.cjs
---

# `run-command` Plugin Reference

`run-command` adds slash commands for authorized shell execution plus reusable quick-command templates.

## What It Registers

- `/run`
- `/r` (alias of `/run`)

Both commands require authorized sender context (`requireAuth: true`).

## Install

```bash
openclaw plugins install -l /data/projects/luke-agent-scripts/openclaw-plugins/run-command
openclaw plugins enable run-command
```

Restart gateway after enabling.

## Command Surface

### Direct execution

- `/run <shell command>`
- `/r <shell command>`

When no option token matches (`help`, `+q`, `-q`, `q`), the remaining text is executed directly.

### Management options

- `/run help`: show dynamic help
- `/run +q <label> <command>`: create/update template
- `/run -q <label>`: delete template
- `/run q`: list templates
- `/run q <label> [args...]`: execute template with positional args

## Template Rules

- Placeholders: `{1}`, `{2}`, ...
- Labels must match: letters, numbers, `_`, `-`
- Missing/extra positional args return explicit errors

## Storage File

- Path env: `CLAWD_RUN_COMMANDS_FILE`
- Default: `~/.clawd-run-commands.md`
- Format: markdown with embedded JSON
- Shared with `ntm` plugin (`run` + `ntm` scopes)

## Execution Details

- Command execution uses `script -q -e -c "<command>" /dev/null` (PTY output capture)
- Return value includes stdout/stderr in fenced code block
- Large output capped by Node `execFile` max buffer (10 MB)

## Security and Risk

- This plugin executes arbitrary shell commands
- Keep it restricted to trusted, authorized senders only
- Avoid enabling where sender authorization is weak or shared

## Troubleshooting

- `Command failed` with minimal output: check command path and shell syntax
- No quick command found: run `/run q` to list available labels
- Template argument errors: align provided args with `{N}` placeholders
