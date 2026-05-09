# OpenAI Symphony Bootstrap Checklist

## Repo Setup

- Confirm the target path is a git repo.
- Confirm the clone URL is usable by workers.
- Choose stable required paths, for example `README.md`, `package.json`, `pyproject.toml`, `src`, `app`, or `lib`.
- Keep first-run `max_concurrent_agents` at `1`.

## Linear Setup

- Use a Linear personal API key in `.env` as `LINEAR_API_KEY`.
- Find the target project's GraphQL `Project.slugId`; this is the value for workflow `tracker.project_slug`.
- Confirm required states: `Backlog`, `Todo`, `In Progress`, `In Review`, `Done`.
- Confirm routing label: `sym:medium` unless a different lane was chosen.
- Create one first-wave issue in `Todo`; keep the rest in `Backlog`.

## Local Runtime

- Install or expose `symphony` on `PATH`.
- Set `SYMPHONY_WORKSPACES_ROOT` in `.env`; a shared root such as `/Users/luke/dev/symphony-workspaces` is acceptable.
- Set `SYMPHONY_CODEX_HOME` in `.env`, usually `/Users/luke/.codex`.
- Start from the repo with `npm run symphony:start` or `bash scripts/start_symphony.sh`.

## Verification

- Run the orchestrator `doctor.py` with only the orchestration env keys loaded.
- Run the orchestrator `preflight.py` against the generated workflow.
- Query Linear for active issues matching the project and routing label before expecting workers to dispatch.
