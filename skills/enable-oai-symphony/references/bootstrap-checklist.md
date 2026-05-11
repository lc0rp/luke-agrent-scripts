# OpenAI Symphony Bootstrap Checklist

## Repo Setup

- Confirm the target path is a git repo.
- Confirm the clone URL is usable by workers.
- Choose stable required paths, for example `README.md`, `package.json`, `pyproject.toml`, `src`, `app`, or `lib`.
- Keep `max_concurrent_agents` at `3` unless the operator explicitly chooses a different concurrency.

## Linear Setup

- Use a Linear personal API key in `.env` as `LINEAR_API_KEY`.
- Find the target project's GraphQL `Project.slugId`; this is the value for workflow `tracker.project_slug`.
- Confirm required team-level states: `Backlog`, `Todo`, `In Progress`, `Human Review`, `Merging`, `Rework`, `Done`.
- Create missing workflow states on the Linear team, not the project. `Human Review`, `Merging`, and `Rework` should use Linear's started state type.
- Confirm routing label: `sym:medium` unless a different lane was chosen.
- Create one first-wave issue in `Todo`; keep the rest in `Backlog`.
- Use `Human Review` as the non-active review gate, `Rework` for requested changes that should wake Symphony again, and `Merging` for approved PR landing.
- Confirm `.codex/skills/commit`, `.codex/skills/push`, `.codex/skills/pull`, `.codex/skills/land`, and `.codex/skills/linear` exist when using the upstream-style workflow.
- Treat the single `## Codex Workpad` Linear comment as the primary human-agent communication surface.

## Local Runtime

- Install or expose `symphony` on `PATH`.
- Set `SYMPHONY_WORKSPACES_ROOT` in `.env`; a shared root such as `/Users/luke/dev/symphony-workspaces` is acceptable.
- Set `SYMPHONY_CODEX_HOME` in `.env`, usually `/Users/luke/.codex`.
- Start from the repo with `npm run symphony:start` or `bash scripts/start_symphony.sh`.

## Verification

- Run the orchestrator `doctor.py` with only the orchestration env keys loaded.
- Run the orchestrator `preflight.py` against the generated workflow.
- Query Linear for active issues matching the project and routing label before expecting workers to dispatch.
