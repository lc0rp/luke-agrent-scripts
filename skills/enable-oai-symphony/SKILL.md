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
5. Confirm Linear has the routing label from the chosen lane, such as `sym:medium`, and at least one matching issue in `Todo` or `In Progress`.
6. Run the generated start command from the target repo:

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
- Keeps the default first run conservative: lane `medium`, label `sym:medium`, and `max_concurrent_agents: 1`.

## Guardrails

- Do not paste real Linear API keys, tokens, app secrets, customer payloads, or raw production data into generated files.
- Do not source the full `.env` into Symphony workers. Load only `LINEAR_API_KEY`, `SYMPHONY_WORKSPACES_ROOT`, and `SYMPHONY_CODEX_HOME`.
- Do not start a real Symphony run until Linear has a bounded issue with the workflow label and the operator has approved externally visible Linear changes.
- If the project slug ID is unknown, query Linear read-only or ask for it. Do not guess from the display URL.

## References

- Read `references/bootstrap-checklist.md` when you need the exact verification and Linear setup checklist.
