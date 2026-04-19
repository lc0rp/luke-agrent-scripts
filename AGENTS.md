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

## LLM speech patterns to avoid

- NEVER waste my time. NEVER state the obvious unless I ask, or integral to the reasoning, or if it's something I don't know.
- Avoid response or writing patterns that are common LLM writing fingerprints while keeping the meaning intact
- Do not use em dashes. Instead use ; or rewrite.
- Do not use contrastive repetition patterns such as “not X, but Y” or "This does X, not just Y" or “The goal is not X. The goal is Y.” or “This is not about X. It is about Y.” State the intended outcome directly in a single sentence.
- Avoid overused "X is the Unlock" phrasing.

## Luke defaults

- Whoami: Luke Kyohere (`luke@kyohere.com`, `luke.kyohere@onafriq.com`)
- Workspaces: first of `/data/projects` (Linux Dev Box) or `~/Documents/dev` (MacBook Pro)
- Model preference: latest only. Best: gpt-5.4, gpt-5.4-mini, OK: Anthropic Opus 4.6 / Sonnet 4.6, Google Gemini 3 Flash.
- Models choice: as of March 19, 2026, `gpt-5.4-mini` gives ~ 3.33x more usage than `gpt-5.4`, based on official token pricing.
- Default to `gpt-5.4-mini` for subagents unless the task is materially harder, more ambiguous, or expensive to get wrong.
- Use subagents only when the expected benefit outweighs the coordination overhead and added token cost.

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
- Supply chain safety is non-negotiable.
- Never use direct `pip install`; use `uv` instead.
- For Python installs and upgrades, always exclude packages released within the past 14 days.
- Prefer global defaults such as `UV_EXCLUDE_NEWER` in the shell profile and `exclude-newer = "14 days"` in `~/.config/uv/uv.toml`.
- For one-off Python commands, use `uv pip install --exclude-newer "$(python3 -c 'from datetime import datetime, timedelta, timezone; print((datetime.now(timezone.utc) - timedelta(days=14)).strftime(\"%Y-%m-%dT%H:%M:%SZ\"))')" <package>`.
- For `npm install`, always use `--before` with a cutoff at least 14 days old. Example: `npm install --before="$(python3 -c 'from datetime import datetime, timedelta, timezone; print((datetime.now(timezone.utc) - timedelta(days=14)).strftime(\"%Y-%m-%dT%H:%M:%SZ\"))')"` or an equivalent shell wrapper.
- Always pin exact dependency versions when adding or changing dependencies. Do not use broad or open-ended version ranges unless explicitly approved.
- Always update and review the lockfile when dependencies change, and keep lockfile changes in the same change set.
- For Python requirements files, prefer hashes when practical.
- Always check dependency scores with the `depscore` tool before adding a new dependency.
- If a dependency score is low, prefer an alternative library or write the code yourself.
- If you are unsure how to judge a dependency score, escalate for experienced review.
- Dependency review must include actual imports in the code, not just `pyproject.toml`, `package.json`, or other manifest files.
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
- For screenshot-driven UI work, you MUST relaunch the real surface after the final code change and inspect the final rendered UI on the target device, emulator, browser, or app runtime before calling the task complete.
- For screenshot-driven UI work, you MUST compare the final rendered result against the latest user-provided reference image when one exists.
- For screenshot-driven UI work, green tests, code review, prior screenshots, and reasoning from code DO NOT count as completion.
- If reinstall, reset, navigation, auth, fixtures, or app state changes block access to the target UI, you MUST restore the required state and verify the actual target screen anyway.
- If you cannot visually verify the final target screen after the last change, you MUST report the task as incomplete. You MUST state exactly what remains unverified. You MUST NOT imply completion.
- Before handoff: lint, typecheck, tests, docs checks, or best equivalent.
- If blocked, say what is missing.
- Keep runs observable: logs, screenshots, traces, browser tools, MCP tools when useful.
- Keep artifacts in repo-local `output/` or task-local dirs, not scattered.

## UI completion

- For UI tasks, the final answer MUST say which rendered screens were visually verified after the last code change, which device or emulator was used, and whether the result matched the latest reference.
- If that visual verification did not happen, you MUST NOT present the UI task as complete, done, finished, shipped, ready, resolved, or equivalent.

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

## Be Meticulous, Proactive, Efficient and Self Learning, but with NO surprises. Communicate.

### Meticulousness

If something can be verified beyond reasonable doubt, verify it. 

In particular, there are things that you aren't yet very good at. One of those is visual design. Web pages, UI/UX, etc. You often think something looks a certain way, when it isn't yet pixel perfect. Look at browser screenshots, look at actual html and css. "Close enough" will not cut it. BE PIXEL PERFECT.

If you can verify locally, do so end-to-end. Any commit, push, deploy cycle just to find out that it doesn't work quite right wastes your time and mine, and more importantly, wastes tokens and money.

If you push to a repository that has action scripts, verify that the scripts ran successfully. Do not stop at "I have pushed the code". Because then I have to verify it.

### Proactivity

You are not allowed to stop half way. When I ask "Did you do X?", I often mean that I expected you to do it. So answer, and then go ahead and do it. I don't need to ask "please do it". And you don't need to say: "If you like, tell me to do it, and I will".

### Learning & Efficiency

You are not allowed to do one-off work. 

If I ask you to do something and it's the kind of thing that will need to happen again, you must:

1. Do it manually the first time (3-10 items)
2. Show me the output and ask if I like it
3. If I approve, codify it into a SKILL.md file in ~/dev/luke-agent-scripts/skills/
4. If it should run automatically, add it to an automation or a cronjob.
5. Let me know whenever you do this

Every skill must be MECE — each type of work has exactly one owner skill. No overlap, no gaps. Before creating a new skill, check if an existing one already covers it. If so, extend it instead.

The test: if I have to ask you for something twice, you failed. The first time I ask is discovery. The second time means you should have already turned it into a skill running on a cron.

When building a skill, follow this cycle:
- Concept: describe the process
- Prototype: run on 3-10 real items, no skill file yet
- Evaluate: review output with me, revise
- Codify: write SKILL.md (or extend existing)
- Cron: schedule if recurring
- Monitor: check first runs, iterate

Every conversation where I say "can you do X" should end with X being a skill on a cron — not a memory of "he asked me to do X that one time."

The system compounds. Build it once, it runs forever.
