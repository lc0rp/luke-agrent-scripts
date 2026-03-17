# AGENTS.md

Shared Luke defaults. Use across repos unless local project docs say otherwise.

## Purpose

- Keep `AGENTS.md` short.
- Use repo docs as the system of record.
- Put stable rules here; put project specifics in local docs/runbooks/specs.

## Start and style

- Start: say hi + 1 motivating line.
- Work style: telegraph; noun-phrases ok; drop filler; min tokens.
- Luke owns the repo unless local docs say otherwise.

## Luke defaults

- Whoami: Luke Kyohere (`luke@kyohere.com`, `luke.kyohere@onafriq.com`)
- Workspaces: first of `/data/projects` (Linux Dev Box) or `~/Documents/dev` (MacBook Pro)
- Model preference: latest only. OK: Anthropic Opus 4.6 / Sonnet 4.6, OpenAI GPT-5.4, xAI Grok-4.1 Fast, Google Gemini 3 Flash.

## Read order

1. Repo-local `AGENTS.md`
2. `docs/` index, `README.md`, `ARCHITECTURE.md`, `dev-docs/README.md`, nearest task/spec docs
3. Cross-linked docs with `Read when` hints
4. This file as fallback baseline

If repo docs disagree with this file, follow repo docs.

## Core working rules

- Fix root cause, not symptoms.
- If unsure, read more code/docs first; ask only when still blocked.
- Web search early for unstable or current facts.
- Quote exact errors.
- Add regression tests when it fits.
- Prefer red/green/refactor TDD for bugs, regressions, and risky behavior changes when practical.
- Do not turn tests green with lazy stubs, placeholders, bypasses, or mock-heavy fake implementations unless that scope is explicitly requested.
- Green tests are not enough; ensure the real implementation under the hood is complete, integrated, and production-ready.
- Continue implementation with minimal human input until the task is production-ready or a real blocker requires escalation.
- Keep files under ~500 LOC when practical; split before they sprawl.
- Leave short breadcrumb notes in the thread.
- Unrecognized changes: assume another agent; keep going unless they conflict.

## Docs rules

- `AGENTS.md` is a map, not the encyclopedia.
- Start by checking `docs/` and nearby docs before coding.
- Follow links until the domain makes sense.
- Honor `Read when` hints.
- Keep notes short; update docs when behavior or APIs change.
- Add `read_when` hints on cross-cutting docs.
- No ship with behavior drift and stale docs if docs are in scope.

## Tool selection

Use this hierarchy:

- built-ins first when available and clearly better
- `fd` for file/path discovery
- `rg` for raw text
- `ast-grep` for syntax-aware code search
- `jq`/`yq` for structured data

### File operations

- Broad file/path discovery: `fd -H --no-ignore-vcs -L`
  Includes hidden files, follows symlinks, ignores `.gitignore`; still respects `.ignore` and `.fdignore`.
- Find by name: `fd -H --no-ignore-vcs -L <pattern>`
- Find by path: `fd -H --no-ignore-vcs -L -p <path>`
- List a directory: `fd -H --no-ignore-vcs -L . <directory>`
- Find by extension and pattern: `fd -H --no-ignore-vcs -L -e <ext> <pattern>`

### Structured code search

- Use `ast-grep` when syntax matters:
  `ast-grep --no-ignore hidden --no-ignore dot --no-ignore vcs --follow --lang <language> -p '<pattern>'`
  Includes hidden files, follows symlinks, ignores `.ignore` and VCS ignore rules.
- List matching files:
  `ast-grep --no-ignore hidden --no-ignore dot --no-ignore vcs --follow -l --lang <language> -p '<pattern>' | head -n 10`

### Data processing

- JSON: `jq`
- YAML/XML: `yq`

### Selection

- Prefer deterministic filtering: `head`, `--json`, `jq`, `--filter`
- Fuzzy filter when needed: `fzf --filter 'term' | head -n 1`

## Validation and harness

- Prefer end-to-end verify.
- Prefer end-to-end or real user-flow verification for user-facing changes when feasible, not just unit coverage.
- Run the highest validation level you can afford.
- Before handoff: lint, typecheck, tests, docs checks, or best equivalent.
- If blocked, say what is missing.
- Keep runs observable: logs, screenshots, traces, browser tools, MCP tools when useful.
- Keep artifacts in repo-local `output/` or task-local dirs, not scattered.

## Build and release

- Release: read `docs/RELEASING.md` if present; otherwise find the nearest release checklist.
- Use semantic-release when the repo standard says so; avoid manual release flow unless break-glass.
- Prefer Conventional Commits.
- Enforce commitlint locally/CI when the repo supports it.

## Git rules

- Safe by default: `git status`, `git diff`, `git log`
- `git checkout` OK for review or explicit request
- Ask before branch changes unless the user explicitly asked
- Push only when the user asks, or the repo workflow explicitly delegates it
- No destructive ops without explicit consent: `reset --hard`, `clean`, `restore`, `rm`, mass rename/delete
- No repo-wide search/replace scripts
- Avoid manual `git stash`
- No amend unless asked
- Keep commits atomic: only files you touched

## Frontend aesthetics

Avoid AI-slop UI. Be opinionated and distinctive.

- Typography: pick a real font; avoid Inter/Roboto/Arial/system defaults.
- Theme: commit to a palette; use CSS vars; bold accents over timid gradients.
- Motion: 1-2 high-impact moments; avoid random micro-animations.
- Background: add depth; avoid flat defaults.
- Avoid purple-on-white cliches, generic component grids, predictable layouts.

## Environment notes

1. devbox, ubuntu, linux, gateway: this computer.
   - GUI display: `:1`
   - GUI prefix: `DISPLAY=:1 XAUTHORITY=$HOME/.Xauthority`
2. mac, macbook, mbp, Mac: Luke's MacBook Pro.

## SSH via Tailscale

- On Linux Dev Box, access Mac via the `ssh-tailscale-luke-mac` skill.
- On MacBook Pro, access Dev Box via the `ssh-tailscale-luke-devbox` skill.
