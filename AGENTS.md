# AGENTS.md

## Overview

Luke owns this. Start: say hi + 1 motivating line. Work style: telegraph; noun-phrases ok; drop grammar; min tokens.
- Whoami: Luke Kyohere (luke@kyohere.com)
- Workspaces: first of "/data/projects" (Linux Dev Box) or "~/Documents/dev" (MacBook Pro); 
- Bugs: add regression test when it fits.
- Keep files <~500 LOC; split/refactor as needed.
- Commits: Conventional Commits (feat|fix|refactor|build|ci|chore|docs|style|perf|test).
- Prefer end-to-end verify; if blocked, say what’s missing.
- New deps: quick health check (recent releases/commits, adoption).
- Web: search early; quote exact errors; prefer 2024–2025 sources; fallback Firecrawl (pnpm mcp:*) / mcporter.
- Style: telegraph. Drop filler/grammar. Min tokens (global AGENTS + replies).

## Tool Selection

When need to call tools from the shell, use this rubric:

## File Operations
- Include hidden and VCS-ignored files by default using fd `-H --no-ignore-vcs` flags
- Follow symlinks by default using fd `-L` flag
- Find files by file name: `fd -H --no-ignore-vcs -L`
- Find files with path name: `fd -H --no-ignore-vcs -L -p <file-path>`
- List files in a directory: `fd -H --no-ignore-vcs -L . <directory>`
- Find files with extension and pattern: `fd -H --no-ignore-vcs -L -e <extension> <pattern>`

## Structured Code Search
- Include hidden, dotfiles, and VCS-ignored files by default using ast-grep `--no-ignore hidden --no-ignore dot --no-ignore vcs` flags
- Follow symlinks by default using ast-grep `--follow` flag
- Find code structure: `ast-grep --no-ignore hidden --no-ignore dot --no-ignore vcs --follow --lang <language> -p '<pattern>'`
- List matching files: `ast-grep --no-ignore hidden --no-ignore dot --no-ignore vcs --follow -l --lang <language> -p '<pattern>' | head -n 10`
- Prefer `ast-grep` over `rg`/`grep` when you need syntax-aware matching

## Data Processing
- JSON: `jq`
- YAML/XML: `yq`

## Selection
- Select from multiple results deterministically (non-interactive filtering)
- Fuzzy finder: `fzf --filter 'term' | head -n 1`

## Guidelines
- Prefer deterministic, non-interactive commands (`head`, `--filter`, `--json` + `jq`) so runs are reproducible

## Docs
- Use Information Architecture skill for docs discovery/understanding/maintenance.
- Start: check docs/ folder and subs. Open docs before coding.
- Follow links until domain makes sense; honor `Read when` hints.
- Keep notes short; update docs when behavior/API changes (no ship w/o docs).
- add `read_when` hints on cross-cutting docs.
- Model preference: latest only. OK: Anthropic Opus 4.5 / Sonnet 4.5 (Sonnet 3.5 = old; avoid), OpenAI GPT-5.2, xAI Grok-4.1 Fast, Google Gemini 3 Flash.

## Critical Thinking
- Fix root cause (not band-aid).
- Unsure: read more code; if still stuck, ask w/ short options.
- Conflicts: call out; pick safer path.
- Unrecognized changes: assume other agent; keep going; focus your changes. If it causes issues, stop + ask user.
- Leave breadcrumb notes in thread.

## Build / Test
- Before handoff: run full gate (lint/typecheck/tests/docs).
- CI red: gh run list/view, rerun, fix, push, repeat til green.
- Keep it observable (logs, panes, tails, MCP/browser tools).
- Release: read docs/RELEASING.md (or find best checklist if missing).

<frontend_aesthetics> Avoid “AI slop” UI. Be opinionated + distinctive.

Do:
- Typography: pick a real font; avoid Inter/Roboto/Arial/system defaults.
- Theme: commit to a palette; use CSS vars; bold accents > timid gradients.
- Motion: 1–2 high-impact moments (staggered reveal beats random micro-anim).
- Background: add depth (gradients/patterns), not flat default.
Avoid: purple-on-white clichés, generic component grids, predictable layouts. </frontend_aesthetics>

## Clawdbot
- Before changing `/home/ubuntu/clawd` or `/home/ubuntu/clawd-agents`: commit + push first (backup config).

## Git
- Safe by default: git status/diff/log. Push only when user asks, or if in bd context, per beads protocol.
- git checkout ok for PR review / explicit request.
- Branch changes require user consent.
- Destructive ops forbidden unless explicit (reset --hard, clean, restore, rm, …).
- Remotes under ~/rojects: prefer HTTPS; flip SSH->HTTPS before pull/push.
- Commit helper on PATH: committer (bash). Prefer it; if repo has ./scripts/committer, use that.
- Don’t delete/rename unexpected stuff; stop + ask.
- No repo-wide S/R scripts; keep edits small/reviewable.
- Avoid manual git stash; if Git auto-stashes during pull/rebase, that’s fine (hint, not hard guardrail).
- If user types a command (“pull and push”), that’s consent for that command.
- No amend unless asked.
- Big review: git --no-pager diff --color=never.
- Multi-agent: check `git status/diff` before edits; ship small commits.
- Unrecognized changes: assume other agent; keep going; focus your changes. If it causes issues, stop + ask user.
- Keep commits atomic: commit only files you touched and list each path explicitly.
  - Tracked files: `git commit -m "<type(scope): message>" -- path/to/file1 path/to/file2`
  - New files: `git restore --staged :/ && git add "path/to/file1" "path/to/file2" && git commit -m "<type(scope): message>" -- path/to/file1 path/to/file2`

  ## Computer colloquial names:
  1. devbox, ubuntu, linux, gateway: This computer.
  2. mac, macbook, mbp: Luke's MacBook Pro. Accessible via SSH 
  