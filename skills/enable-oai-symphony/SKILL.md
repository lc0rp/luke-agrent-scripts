---
name: enable-oai-symphony
description: Bootstrap a software repository for OpenAI Symphony plus Linear execution. Use when Codex needs to enable Symphony in a repo, create .orchestration artifacts, add LINEAR_API_KEY/SYMPHONY_* .env.example entries, create a repo-local Symphony start script, add package.json start commands, wire conservative first-run defaults, or prepare a project for Symphony workers coordinated through Linear.
---

# Enable OAI Symphony

Use this skill to make a repository runnable by the local OpenAI Symphony Elixir preview with Linear as the tracker.

## Workflow

1. Read repo guidance first: `AGENTS.md`, `README.md`, `docs/`, `dev-docs/`, and release/validation docs.
2. Identify the Linear project. Symphony's workflow field `tracker.project_slug` maps to Linear GraphQL `Project.slugId`, not just the display slug in the URL.
3. Run the bootstrap helper:

```bash
python3 /Users/luke/dev/luke-agent-scripts/skills/enable-oai-symphony/scripts/enable_oai_symphony.py \
  --target-repo . \
  --linear-project-slug-id <linear-project-slug-id>
```

4. Review generated changes before starting Symphony.
5. Confirm Linear has the routing label from the chosen lane, such as `sym:medium`, and the upstream-style team states: `Backlog`, `Todo`, `In Progress`, `Human Review`, `Merging`, `Rework`, and `Done`.
6. Confirm there is at least one matching issue in an active state when you expect dispatch. The default active states are `Todo`, `In Progress`, `Merging`, and `Rework`; `Human Review` is intentionally a non-dispatch review gate.
7. Run the generated start command from the target repo:

```bash
npm run symphony:start
```

If the repo does not use `package.json`, run:

```bash
bash scripts/start_symphony.sh
```

## Helper Behavior

The helper script:

- Invokes the existing `symphony-linear-orchestrator` bootstrap renderer when present.
- Adds `LINEAR_API_KEY`, `SYMPHONY_WORKSPACES_ROOT`, and `SYMPHONY_CODEX_HOME` to `.env.example` if missing.
- Writes `scripts/start_symphony.sh`; it loads only the Symphony/Linear keys from `.env`, never the whole app environment.
- Adds `symphony:start` to `package.json` when the repo has one.
- Normalizes the generated workflow to the upstream-style state model: `Todo`, `In Progress`, `Merging`, and `Rework` are active; `Human Review` is the review gate; `Done` and cancellation states are terminal.
- Appends upstream-style workpad discipline, state routing, PR feedback sweep, blocked-access, follow-up issue, and merge/landing instructions so agents communicate through one persistent `## Codex Workpad` comment, link PRs back to Linear, move validated work to `Human Review`, handle requested changes in `Rework`, and finish approved PRs from `Merging`.
- Copies upstream Symphony repo skills into `.codex/skills`: `commit`, `push`, `pull`, `land`, and `linear` when available locally.
- Keeps the default lane `medium`, label `sym:medium`, `max_concurrent_agents: 3`, and worker model `gpt-5.5` with medium reasoning.

## Guardrails

- Do not paste real Linear API keys, tokens, app secrets, customer payloads, or raw production data into generated files.
- Do not source the full `.env` into Symphony workers. Load only `LINEAR_API_KEY`, `SYMPHONY_WORKSPACES_ROOT`, and `SYMPHONY_CODEX_HOME`.
- Do not start a real Symphony run until Linear has a bounded issue with the workflow label and the operator has approved externally visible Linear changes.
- Linear workflow states are team-level. Add `Human Review`, `Merging`, and `Rework` to the owning team when they are missing; do not treat them as project-local settings.
- Treat a Linear "done" comment without a branch/PR link as incomplete handoff; adjust the workflow before dispatching real implementation work.
- Treat review comments on `Human Review` issues as human/orchestrator input. Move the issue to `Rework` when Symphony should pick it up again.
- Treat the single `## Codex Workpad` Linear comment as the primary human-agent communication surface. Do not scatter progress across multiple comments.
- `Merging` requires the upstream `land` skill. If `.codex/skills/land/SKILL.md` is missing, install/copy the upstream skills before dispatching issues that can reach `Merging`.
- If the project slug ID is unknown, query Linear read-only or ask for it. Do not guess from the display URL.

## References

- Read `references/bootstrap-checklist.md` when you need the exact verification and Linear setup checklist.
