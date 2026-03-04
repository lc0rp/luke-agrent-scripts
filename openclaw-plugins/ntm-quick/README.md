---
type: Reference
primary_audience: Operators
owner: Automation tooling maintainers
last_verified: 2026-03-04
next_review_by: 2026-06-04
source_of_truth:
  - ./index.ts
  - ./async-reply.ts
  - ./openclaw.plugin.json
  - ./ntm-quick.test.cjs
---

# `ntm-quick` Plugin Reference

`ntm-quick` provides a small control surface for `ntm` robot workflows: list sessions, set active project, inspect pane output, send prompt, and collect response.

## What It Registers

- `/nl`: run `ntm list`
- `/na`: set/read active project
- `/nc`: read saved project pane-2 tail (`/n-cat`)
- `/ns`: send + block until response or timeout
- `/nsa`: send + return immediately, post follow-up reply asynchronously

All commands require authorized sender context (`requireAuth: true`).

## Install

```bash
openclaw plugins install -l /data/projects/luke-agent-scripts/openclaw-plugins/ntm-quick
openclaw plugins enable ntm-quick
```

Restart gateway after enabling.

## Command Semantics

### `/nl`

- Runs: `ntm list`
- Returns list text or command error

### `/na <project>`

- Saves project for `/ns` and `/nsa`
- `/na` with no args returns current saved project (or usage)

### `/nc [lines]`

- Runs `ntm --robot-tail=<saved-project> --panes=2 --lines=<lines> --json`
- Default `lines`: `50`
- Parses nested pane JSON, then returns readable pane output
- Filters non-response noise (context hint, separator rule, transient `Working(...)`)

### `/ns <message>`

1. Reads saved project
2. Captures baseline pane tail
3. Sends: `ntm --robot-send=<project> --panes=2 --track --msg="<message>\n\n"`
4. Polls: `ntm --robot-tail=<project> --panes=2 --lines=<N> --json`
5. Returns first valid assistant response block or timeout

### `/nsa <message>`

- Same send/poll flow as `/ns`
- Immediate ack: `Message sent to <project>, waiting for result...`
- Final response is posted asynchronously back to original channel target

## Async Reply Routing (`/nsa`)

Routing source is captured from command context:

- Primary target: `to` (except `slash:*`)
- Fallback target: `from`

Supported channel senders:

- Telegram (preserves `messageThreadId`)
- Discord
- Slack
- Signal
- iMessage
- WhatsApp / Web
- Line

Unsupported/unknown channels return routing error.

## Polling and Response Detection

- Tail parser supports nested JSON shape: `panes.<id>.lines`
- Detection is message-anchored:
  - find latest prompt line matching sent message
  - return non-noise lines after that prompt until next prompt
- Filters remove non-final noise:
  - prompt lines (`› ...`)
  - context hints (`? for shortcuts ... context left`)
  - separator rules
  - transient activity (`Working (... esc to interrupt)`)

## State and Runtime Environment

### Saved project state

- Env: `CLAWD_NTM_QUICK_STATE_FILE`
- Default: `~/.clawd-ntm-quick.json`

### Poll settings

- Env: `NTM_QUICK_TIMEOUT_MS` (default 90000)
- Env: `NTM_QUICK_POLL_INTERVAL_MS` (default 1000)
- Env: `NTM_QUICK_ROBOT_TAIL_LINES` (default 120)

## Operational Requirements

- `ntm` must be installed and available in `PATH`
- Target session must exist and pane 2 must be the codex/LLM pane
- Sender must run inside an authorized OpenClaw channel context

## Failure Modes

- `No ntm project saved...`: run `/na <project>` first
- `Error sending robot message...`: `ntm --robot-send` failure
- `Error polling robot tail...`: `ntm --robot-tail` failure
- `Timed out after ...`: no valid response detected before timeout
- `Unable to resolve reply target...`: `/nsa` missing route context
