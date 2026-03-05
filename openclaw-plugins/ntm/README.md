---
type: Reference
primary_audience: Operators
owner: Automation tooling maintainers
last_verified: 2026-03-04
next_review_by: 2026-06-04
source_of_truth:
  - ./index.ts
  - ./openclaw.plugin.json
  - ./ntm.test.cjs
---

# `ntm` Plugin Reference

`ntm` adds slash commands for `ntm` session control plus reusable quick-command templates.

## What It Registers

- `/ntm`
- `/n` (alias of `/ntm`)

Both commands require authorized sender context (`requireAuth: true`).

## Install

```bash
openclaw plugins install -l /data/projects/luke-agent-scripts/openclaw-plugins/ntm
openclaw plugins enable ntm
```

Restart gateway after enabling.

## Command Surface

### Core options

- `/ntm` (no args): same as `/ntm list`
- `/ntm list`: run `ntm list`
- `/ntm run <args>`: run arbitrary `ntm <args>`
- `/ntm help`: show dynamic help

### Quick-command options

- `/ntm +q <label> <command>`: create/update template
- `/ntm -q <label>`: delete template
- `/ntm q`: list templates
- `/ntm q <label> [args...]`: execute template with positional args

### Fixed placeholder options

- `/ntm +qf <number> <value>`: fix placeholder position globally
- `/ntm -qf <number>`: clear fixed placeholder
- `/ntm qf`: list fixed placeholders

## Template Rules

- Placeholders: `{1}`, `{2}`, ...
- Labels must match: letters, numbers, `_`, `-`
- Extra args or missing placeholders return explicit usage errors
- Stored ntm templates can be entered as `list` or `ntm list`; runtime normalizes to `ntm ...`

## Storage Files

### Quick-command store

- Path env: `CLAWD_RUN_COMMANDS_FILE`
- Default: `~/.clawd-run-commands.md`
- Format: markdown with embedded JSON code block
- Shared with `run-command` plugin (`run` and `ntm` scopes in one file)

### Fixed placeholder store

- Path env: `CLAWD_NTM_FIXES_FILE`
- Default: `~/.clawd-ntm-fixes.json`
- Format: JSON map of placeholder position to fixed value

## Execution Details

- Plugin runs commands via `api.runtime.system.runCommandWithTimeout`
- It prefers `script -q -e -c "<cmd>" /dev/null` to preserve PTY behavior
- Fallback: direct argv execution if PTY wrapper fails
- Timeout: 10s default (`DEFAULT_TIMEOUT_MS`)

## Output Behavior

- Successful and error command output is returned in fenced code blocks
- `/ntm list` returns plain list text for readability
- Missing/invalid options return usage text

## Operational Notes

- `ntm` binary must exist in runtime `PATH`
- Plugin executes shell-level commands; keep `requireAuth` enabled
- If PTY utilities are unavailable, plugin degrades to non-PTY execution

## Troubleshooting

- `Error running ntm list: ...`: verify `ntm` installed and shell PATH
- `Command cannot be empty.`: template or `run` payload resolved to empty
- `Missing required argument(s): {N}`: template placeholders not fully provided
- `Too many arguments...`: supplied args exceed template placeholders
