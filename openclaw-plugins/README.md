---
type: Concept
primary_audience: Operators
owner: Automation tooling maintainers
last_verified: 2026-03-04
next_review_by: 2026-06-04
source_of_truth:
  - ./ntm/README.md
  - ./ntm-quick/README.md
  - ./run-command/README.md
---

# OpenClaw Local Plugin Docs

Reference docs for locally maintained automation plugins:

- [`ntm`](./ntm/README.md): `/ntm` and `/n` command surface, quick templates, placeholder fixes
- [`ntm-quick`](./ntm-quick/README.md): `/nl`, `/na`, `/ns`, `/nsa` robot send/poll workflow
- [`run-command`](./run-command/README.md): `/run` and `/r` shell execution + quick templates

## Common Operational Notes

- All three plugins require authorized senders (`requireAuth: true`)
- `ntm` and `ntm-quick` require the `ntm` binary in `PATH`
- `ntm` and `run-command` share quick-command storage at `~/.clawd-run-commands.md` (override via `CLAWD_RUN_COMMANDS_FILE`)
