#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path


STARTER_DIR = Path(
    os.environ.get(
        "SYMPHONY_LINEAR_ORCHESTRATOR_DIR",
        "/Users/luke/dev/luke-agent-scripts/skills/symphony-linear-starter/skills/symphony-linear-orchestrator",
    )
)
UPSTREAM_SKILLS_DIR = Path(
    os.environ.get(
        "OPENAI_SYMPHONY_SKILLS_DIR",
        "/Users/luke/dev/openai-symphony/.codex/skills",
    )
)

START_SCRIPT = r'''#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$repo_root/.env"
workflow="${1:-$repo_root/.orchestration/__WORKFLOW_NAME__.WORKFLOW.md}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'USAGE'
Usage: npm run symphony:start -- [workflow-path]

Starts Symphony for this repo using only these values from .env:
- LINEAR_API_KEY
- SYMPHONY_WORKSPACES_ROOT
- SYMPHONY_CODEX_HOME

When workflow-path is omitted, the repo default workflow is used.
USAGE
  exit 0
fi

read_env_value() {
  local key="$1"
  awk -v key="$key" '
    BEGIN { prefix = key "=" }
    index($0, prefix) == 1 {
      value = substr($0, length(prefix) + 1)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      gsub(/^"|"$/, "", value)
      gsub(/^'\''|'\''$/, "", value)
      print value
      exit
    }
  ' "$env_file"
}

require_value() {
  local name="$1"
  local value="$2"
  if [[ -z "$value" ]]; then
    printf 'Missing %s in %s\n' "$name" "$env_file" >&2
    exit 1
  fi
}

if [[ ! -f "$env_file" ]]; then
  printf 'Missing .env at %s\n' "$env_file" >&2
  exit 1
fi

linear_api_key="$(read_env_value "LINEAR_API_KEY")"
symphony_workspaces_root="$(read_env_value "SYMPHONY_WORKSPACES_ROOT")"
symphony_codex_home="$(read_env_value "SYMPHONY_CODEX_HOME")"

require_value "LINEAR_API_KEY" "$linear_api_key"
require_value "SYMPHONY_WORKSPACES_ROOT" "$symphony_workspaces_root"
require_value "SYMPHONY_CODEX_HOME" "$symphony_codex_home"

if [[ ! -f "$workflow" ]]; then
  printf 'Missing workflow file: %s\n' "$workflow" >&2
  exit 1
fi

mkdir -p "$symphony_workspaces_root"

export LINEAR_API_KEY="$linear_api_key"
export SYMPHONY_WORKSPACES_ROOT="$symphony_workspaces_root"
export SYMPHONY_CODEX_HOME="$symphony_codex_home"

exec symphony --i-understand-that-this-will-be-running-without-the-usual-guardrails "$workflow"
'''

UPSTREAM_PROTOCOL_SECTION = r'''

Instructions:

1. This is an unattended orchestration session. Never ask a human to perform follow-up actions.
2. Only stop early for a true blocker (missing required auth/permissions/secrets). If blocked, record it in the workpad and move the issue according to workflow.
3. Final message must report completed actions and blockers only. Do not include "next steps for user".

Work only in the provided repository copy. Do not touch any other path.

## Repo-required behavior

- Read the repository `AGENTS.md` chain before making changes.
- Use repo-local guidance when relevant.
- Keep changes bounded to the issue.
- Run the issue validation commands before concluding work.
- Never paste secrets, tokens, session cookies, personal data, raw customer payloads, or production payloads into Linear comments, workpad comments, PRs, or logs.
- If sensitive material appears in terminal output or logs, redact it and describe the problem at a high level.
- Treat `## Acceptance Criteria` as hard gates.
- Treat `## Validation Commands` as exact commands to run from repo root.
- Treat `## Touched Areas` as the expected scope. Note any extra files in the workpad.
- Expect most planned work to live in `Backlog` until the orchestrator activates it.

## Prerequisite: Linear MCP or `linear_graphql` tool is available

The agent should be able to talk to Linear, either via a configured Linear MCP server or injected `linear_graphql` tool. If none are present, stop and ask the user to configure Linear.

## Default posture

- Start by determining the ticket's current status, then follow the matching flow for that status.
- Start every task by opening the tracking workpad comment and bringing it up to date before doing new implementation work.
- Spend extra effort up front on planning and verification design before implementation.
- Reproduce first: always confirm the current behavior/issue signal before changing code so the fix target is explicit.
- Keep ticket metadata current (state, checklist, acceptance criteria, links).
- Treat a single persistent Linear comment as the source of truth for progress.
- Use that single workpad comment for all progress and handoff notes; do not post separate "done"/summary comments.
- Treat any ticket-authored `Validation`, `Test Plan`, or `Testing` section as non-negotiable acceptance input: mirror it in the workpad and execute it before considering the work complete.
- When meaningful out-of-scope improvements are discovered during execution, file a separate Linear issue instead of expanding scope. The follow-up issue must include a clear title, description, and acceptance criteria, be placed in `Backlog`, be assigned to the same project as the current issue, link the current issue as `related`, and use `blockedBy` when the follow-up depends on the current issue.
- Move status only when the matching quality bar is met.
- Operate autonomously end-to-end unless blocked by missing requirements, secrets, or permissions.
- Use the blocked-access escape hatch only for true external blockers after exhausting documented fallbacks.

## Related skills

- `linear`: interact with Linear.
- `commit`: produce clean, logical commits during implementation.
- `push`: keep remote branch current and publish updates.
- `pull`: keep branch updated with latest `origin/main` before handoff.
- `land`: when ticket reaches `Merging`, explicitly open and follow `.codex/skills/land/SKILL.md`, which includes the `land` loop.

## Status map

- `Backlog` -> out of scope for this workflow; do not modify.
- `Todo` -> queued; immediately transition to `In Progress` before active work.
  - Special case: if a PR is already attached, treat as feedback/rework loop (run full PR feedback sweep, address or explicitly push back, revalidate, return to `Human Review`).
- `In Progress` -> implementation actively underway.
- `Human Review` -> PR is attached and validated; waiting on human approval.
- `Merging` -> approved by human; execute the `land` skill flow (do not call `gh pr merge` directly).
- `Rework` -> reviewer requested changes; planning plus implementation required.
- `Done` -> terminal state; no further action required.

## Step 0: Determine current ticket state and route

1. Fetch the issue by explicit ticket ID.
2. Read the current state.
3. Route to the matching flow:
   - `Backlog` -> do not modify issue content/state; stop and wait for human to move it to `Todo`.
   - `Todo` -> immediately move to `In Progress`, then ensure bootstrap workpad comment exists (create if missing), then start execution flow.
     - If PR is already attached, start by reviewing all open PR comments and deciding required changes vs explicit pushback responses.
   - `In Progress` -> continue execution flow from current scratchpad comment.
   - `Human Review` -> wait and poll for decision/review updates.
   - `Merging` -> on entry, open and follow `.codex/skills/land/SKILL.md`; do not call `gh pr merge` directly.
   - `Rework` -> run rework flow.
   - `Done` -> do nothing and shut down.
4. Check whether a PR already exists for the current branch and whether it is closed.
   - If a branch PR exists and is `CLOSED` or `MERGED`, treat prior branch work as non-reusable for this run.
   - Create a fresh branch from `origin/main` and restart execution flow as a new attempt.
5. For `Todo` tickets, do startup sequencing in this exact order:
   - `update_issue(..., state: "In Progress")`
   - find/create `## Codex Workpad` bootstrap comment
   - only then begin analysis/planning/implementation work.
6. Add a short comment if state and issue content are inconsistent, then proceed with the safest flow.

## Step 1: Start/continue execution (Todo or In Progress)

1. Find or create a single persistent scratchpad comment for the issue:
   - Search existing comments for a marker header: `## Codex Workpad`.
   - Ignore resolved comments while searching; only active/unresolved comments are eligible to be reused as the live workpad.
   - If found, reuse that comment; do not create a new workpad comment.
   - If not found, create one workpad comment and use it for all updates.
   - Persist the workpad comment ID and only write progress updates to that ID.
2. If arriving from `Todo`, do not delay on additional status transitions: the issue should already be `In Progress` before this step begins.
3. Immediately reconcile the workpad before new edits:
   - Check off items that are already done.
   - Expand/fix the plan so it is comprehensive for current scope.
   - Ensure `Acceptance Criteria` and `Validation` are current and still make sense for the task.
4. Start work by writing/updating a hierarchical plan in the workpad comment.
5. Ensure the workpad includes a compact environment stamp at the top as a code fence line:
   - Format: `<host>:<abs-workdir>@<short-sha>`
   - Example: `devbox-01:/home/dev-user/code/symphony-workspaces/MT-32@7bdde33bc`
   - Do not include metadata already inferable from Linear issue fields (`issue ID`, `status`, `branch`, `PR link`).
6. Add explicit acceptance criteria and TODOs in checklist form in the same comment.
   - If changes are user-facing, include a UI walkthrough acceptance criterion that describes the end-to-end user path to validate.
   - If changes touch app files or app behavior, add explicit app-specific flow checks to `Acceptance Criteria` in the workpad.
   - If the ticket description/comment context includes `Validation`, `Test Plan`, or `Testing` sections, copy those requirements into the workpad `Acceptance Criteria` and `Validation` sections as required checkboxes.
7. Run a principal-style self-review of the plan and refine it in the comment.
8. Before implementing, capture a concrete reproduction signal and record it in the workpad `Notes` section.
9. Run the `pull` skill to sync with latest `origin/main` before any code edits, then record the pull/sync result in the workpad `Notes`.
10. Compact context and proceed to execution.

## Branch and PR handoff requirements

Treat commit, push, and pull request creation as part of completing the issue. Do not claim the issue is ready for review unless reviewers can reach the work from Linear.

1. Before editing, sync from `origin/main` and create a dedicated branch for this issue.
   - Suggested branch shape: `symphony/{{ issue.identifier }}-short-title`.
   - Keep the branch based on `origin/main`.
2. Implement the change, then run the validation commands required by the issue and the repository guidance.
3. Commit the completed work with a focused commit message.
   - Include `{{ issue.identifier }}` in the commit subject or body.
   - Do not commit secrets, generated scratch files, or raw customer payloads.
4. Pull or merge latest `origin/main` into the branch, resolve conflicts if any, and rerun required validation.
5. Push the branch to the remote.
6. Create or update a GitHub PR for the branch.
   - Title format: `[{{ issue.identifier }}] {{ issue.title }}`.
   - PR body must include: Linear issue link, summary, validation run and result, and any known risk or blocker.
   - If a PR already exists for the issue, update the existing PR rather than creating a duplicate.
7. Link the PR in Linear.
   - Prefer a Linear attachment or related link if available.
   - If tooling only supports comments, include the PR URL in the final Linear status comment.
8. Before moving the issue to `Human Review`, run the PR feedback sweep protocol below.
9. If GitHub auth or push/PR creation is blocked, use the blocked-access escape hatch. Do not move the issue to `Human Review` for GitHub access/auth until all fallback strategies have been attempted and documented in the workpad.

## PR feedback sweep protocol (required)

When a ticket has an attached PR, run this protocol before moving to `Human Review`:

1. Identify the PR number from issue links/attachments.
2. Gather feedback from all channels:
   - Top-level PR comments (`gh pr view --comments`).
   - Inline review comments (`gh api repos/<owner>/<repo>/pulls/<pr>/comments`).
   - Review summaries/states (`gh pr view --json reviews`).
3. Treat every actionable reviewer comment (human or bot), including inline review comments, as blocking until one of these is true:
   - code/test/docs updated to address it, or
   - explicit, justified pushback reply is posted on that thread.
4. Update the workpad plan/checklist to include each feedback item and its resolution status.
5. Re-run validation after feedback-driven changes and push updates.
6. Repeat this sweep until there are no outstanding actionable comments.

## Blocked-access escape hatch (required behavior)

Use this only when completion is blocked by missing required tools or missing auth/permissions that cannot be resolved in-session.

- GitHub is not a valid blocker by default. Always try fallback strategies first (alternate remote/auth mode, then continue publish/review flow).
- Do not move to `Human Review` for GitHub access/auth until all fallback strategies have been attempted and documented in the workpad.
- If a non-GitHub required tool is missing, or required non-GitHub auth is unavailable, move the ticket to `Human Review` with a short blocker brief in the workpad that includes:
  - what is missing,
  - why it blocks required acceptance/validation,
  - exact human action needed to unblock.
- Keep the brief concise and action-oriented; do not add extra top-level comments outside the workpad.

## Step 2: Execution phase (Todo -> In Progress -> Human Review)

1. Determine current repo state (`branch`, `git status`, `HEAD`) and verify the kickoff `pull` sync result is already recorded in the workpad before implementation continues.
2. If current issue state is `Todo`, move it to `In Progress`; otherwise leave the current state unchanged.
3. Load the existing workpad comment and treat it as the active execution checklist.
4. Implement against the hierarchical TODOs and keep the comment current:
   - Check off completed items.
   - Add newly discovered items in the appropriate section.
   - Keep parent/child structure intact as scope evolves.
   - Update the workpad immediately after each meaningful milestone.
   - Never leave completed work unchecked in the plan.
   - For tickets that started as `Todo` with an attached PR, run the full PR feedback sweep protocol immediately after kickoff and before new feature work.
5. Run validation/tests required for the scope.
   - Execute all ticket-provided `Validation` / `Test Plan` / `Testing` requirements when present.
   - Prefer a targeted proof that directly demonstrates the behavior you changed.
   - Temporary local proof edits are allowed only when they increase confidence; revert them before commit/push and document them in the workpad.
6. Re-check all acceptance criteria and close any gaps.
7. Before every `git push` attempt, run required validation for the scope and confirm it passes.
8. Attach PR URL to the issue, preferably as an attachment/link; use the workpad only if attachment is unavailable.
   - Ensure the GitHub PR has label `symphony` when the label exists.
9. Merge latest `origin/main` into branch, resolve conflicts, and rerun checks.
10. Update the workpad comment with final checklist status and validation notes.
    - Mark completed plan/acceptance/validation checklist items as checked.
    - Add final handoff notes (commit + validation summary) in the same workpad comment.
    - Do not include PR URL in the workpad comment when issue attachment/link is available.
    - Add a short `### Confusions` section when any part of task execution was unclear.
    - Do not post any additional completion summary comment.
11. Before moving to `Human Review`, poll PR feedback and checks:
    - Run the full PR feedback sweep protocol.
    - Confirm PR checks are passing after latest changes.
    - Confirm every required ticket-provided validation/test-plan item is explicitly marked complete in the workpad.
    - Repeat this check-address-verify loop until no outstanding comments remain and checks are passing.
    - Re-open and refresh the workpad before state transition so `Plan`, `Acceptance Criteria`, and `Validation` exactly match completed work.
12. Only then move issue to `Human Review`.
13. For `Todo` tickets that already had a PR attached at kickoff, ensure all existing PR feedback was reviewed and resolved, branch was pushed, then move to `Human Review`.

## Step 3: Human Review and merge handling

1. When the issue is in `Human Review`, do not code or change ticket content.
2. Poll for updates as needed, including GitHub PR review comments from humans and bots.
3. If review feedback requires changes, move the issue to `Rework` and follow the rework flow.
4. If approved, human moves the issue to `Merging`.
5. When the issue is in `Merging`, open and follow `.codex/skills/land/SKILL.md`, then run the `land` skill in a loop until the PR is merged. Do not call `gh pr merge` directly.
6. After merge is complete, move the issue to `Done`.

## Step 4: Rework handling

1. Treat `Rework` as a full approach reset, not incremental patching.
2. Re-read the full issue body and all human comments; explicitly identify what will be done differently this attempt.
3. Close the existing PR tied to the issue.
4. Remove the existing `## Codex Workpad` comment from the issue.
5. Create a fresh branch from `origin/main`.
6. Start over from the normal kickoff flow:
   - If current issue state is `Todo`, move it to `In Progress`; otherwise keep the current state.
   - Create a new bootstrap `## Codex Workpad` comment.
   - Build a fresh plan/checklist and execute end-to-end.

## Completion bar before Human Review

- Step 1/2 checklist is fully complete and accurately reflected in the single workpad comment.
- Acceptance criteria and required ticket-provided validation items are complete.
- Validation/tests are green for the latest commit.
- PR feedback sweep is complete and no actionable comments remain.
- PR checks are green, branch is pushed, and PR is linked on the issue.
- Required PR metadata is present when applicable (`symphony` label).

## Guardrails

- If the branch PR is already closed/merged, do not reuse that branch or prior implementation state for continuation.
- For closed/merged branch PRs, create a new branch from `origin/main` and restart from reproduction/planning as if starting fresh.
- If issue state is `Backlog`, do not modify it; wait for human to move to `Todo`.
- Do not edit the issue body/description for planning or progress tracking.
- Use exactly one persistent workpad comment (`## Codex Workpad`) per issue.
- If comment editing is unavailable in-session, use available Linear tooling or scripts. Only report blocked if all comment editing routes are unavailable.
- Temporary proof edits are allowed only for local verification and must be reverted before commit.
- If out-of-scope improvements are found, create a separate Backlog issue rather than expanding current scope.
- Do not move to `Human Review` unless the `Completion bar before Human Review` is satisfied.
- In `Human Review`, do not make changes; wait and poll.
- If state is terminal (`Done`), do nothing and shut down.
- Keep issue text concise, specific, and reviewer-oriented.
- If blocked and no workpad exists yet, add one blocker comment describing blocker, impact, and next unblock action.

## Workpad template

Use this exact structure for the persistent workpad comment and keep it updated in place throughout execution:

````md
## Codex Workpad

```text
<hostname>:<abs-path>@<short-sha>
```

### Plan

- [ ] 1\. Parent task
  - [ ] 1.1 Child task
  - [ ] 1.2 Child task
- [ ] 2\. Parent task

### Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2

### Validation

- [ ] targeted tests: `<command>`

### Notes

- <short progress note with timestamp>

### Confusions

- <only include when something was confusing during execution>
````
'''


def run(cmd: list[str], cwd: Path) -> str:
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stdout, end="")
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        raise SystemExit(result.returncode)
    return result.stdout


def git_output(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def infer_required_paths(repo: Path) -> list[str]:
    candidates = [
        "AGENTS.md",
        "README.md",
        "package.json",
        "pyproject.toml",
        "frontend/package.json",
        "src",
        "app",
        "lib",
    ]
    found = [candidate for candidate in candidates if (repo / candidate).exists()]
    return found[:4] or ["README.md"]


def append_env_example(repo: Path) -> None:
    path = repo / ".env.example"
    text = path.read_text() if path.exists() else ""
    existing_keys = {
        line.split("=", 1)[0].strip()
        for line in text.splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }
    needed = {"LINEAR_API_KEY", "SYMPHONY_WORKSPACES_ROOT", "SYMPHONY_CODEX_HOME"}
    if needed.issubset(existing_keys):
        return

    home = Path.home()
    defaults = {
        "LINEAR_API_KEY": "your_linear_personal_api_key_here",
        "SYMPHONY_WORKSPACES_ROOT": str(home / "dev" / "symphony-workspaces"),
        "SYMPHONY_CODEX_HOME": str(home / ".codex"),
    }
    lines = ["", "# OpenAI Symphony + Linear orchestration"]
    for key in ["LINEAR_API_KEY", "SYMPHONY_WORKSPACES_ROOT", "SYMPHONY_CODEX_HOME"]:
        if key not in existing_keys:
            lines.append(f"{key}={defaults[key]}")
    path.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n")


def write_start_script(repo: Path, workflow_name: str) -> None:
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    path = scripts_dir / "start_symphony.sh"
    path.write_text(START_SCRIPT.replace("__WORKFLOW_NAME__", workflow_name))
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def update_package_json(repo: Path) -> None:
    path = repo / "package.json"
    if not path.exists():
        return
    data = json.loads(path.read_text())
    scripts = data.setdefault("scripts", {})
    scripts.setdefault("symphony:start", "bash scripts/start_symphony.sh")
    path.write_text(json.dumps(data, indent=2) + "\n")


def copy_upstream_skills(repo: Path) -> list[str]:
    copied = []
    if not UPSTREAM_SKILLS_DIR.exists():
        return copied

    target_root = repo / ".codex" / "skills"
    target_root.mkdir(parents=True, exist_ok=True)
    for skill_name in ["commit", "push", "pull", "land", "linear"]:
        source = UPSTREAM_SKILLS_DIR / skill_name
        if not source.exists():
            continue
        target = target_root / skill_name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
        copied.append(skill_name)
    return copied


def run_starter_bootstrap(args: argparse.Namespace, repo: Path, workflow_name: str) -> None:
    bootstrap = STARTER_DIR / "scripts" / "bootstrap.py"
    if not bootstrap.exists():
        raise SystemExit(f"Missing Symphony starter bootstrap script: {bootstrap}")

    branch = args.required_branch or git_output(repo, "rev-parse", "--abbrev-ref", "HEAD") or "main"
    clone_url = args.clone_url or git_output(repo, "remote", "get-url", "origin")
    if not clone_url:
        raise SystemExit("Could not infer clone URL. Pass --clone-url.")

    required_paths = args.required_path or infer_required_paths(repo)
    cmd = [
        sys.executable,
        str(bootstrap),
        "--target-repo",
        str(repo),
        "--workflow-name",
        workflow_name,
        "--clone-url",
        clone_url,
        "--linear-project-slug",
        args.linear_project_slug_id,
        "--lane",
        args.lane,
        "--max-concurrent-agents",
        str(args.max_concurrent_agents),
        "--required-branch",
        branch,
        "--write",
    ]
    if args.force:
        cmd.append("--force")
    for required_path in required_paths:
        cmd.extend(["--required-path", required_path])
    run(cmd, repo)


def normalize_active_states(text: str) -> str:
    pattern = re.compile(r"(active_states:\n)(?P<body>(?:[ \t]+- .+\n)+)")

    def replace(match: re.Match[str]) -> str:
        indent_match = re.search(r"^([ \t]+)- ", match.group("body"), re.MULTILINE)
        indent = indent_match.group(1) if indent_match else "    "
        states = ["Todo", "In Progress", "Merging", "Rework"]
        return match.group(1) + "".join(f"{indent}- {state}\n" for state in states)

    return pattern.sub(replace, text, count=1)


def normalize_agent_settings(text: str) -> str:
    text = re.sub(r"max_concurrent_agents:\s*\d+", "max_concurrent_agents: 3", text, count=1)
    command = (
        "command: 'CODEX_HOME=\"$SYMPHONY_CODEX_HOME\" codex --model gpt-5.5 "
        "--config shell_environment_policy.inherit=all "
        "--config model_reasoning_effort=medium app-server'"
    )
    text = re.sub(r"command:\s+['\"].*?codex .*?app-server['\"]", command, text, count=1)
    return text


def normalize_review_state_names(text: str) -> str:
    return text.replace("In Review", "Human Review")


def normalize_issue_context(text: str) -> str:
    if "Current status: {{ issue.state }}" in text:
        return text

    old = """You are working on Linear issue {{ issue.identifier }}.

Title: {{ issue.title }}

Body:
{{ issue.description }}
"""
    new = """You are working on Linear issue {{ issue.identifier }}.

Identifier: {{ issue.identifier }}
Title: {{ issue.title }}
Current status: {{ issue.state }}
Labels: {{ issue.labels }}
URL: {{ issue.url }}

Body:
{{ issue.description }}
"""
    return text.replace(old, new, 1)


def normalize_required_behavior(text: str) -> str:
    if "- Work only in the provided Symphony workspace checkout." not in text:
        text = text.replace(
            "- Keep changes bounded to the issue.\n",
            "- Keep changes bounded to the issue.\n"
            "- Work only in the provided Symphony workspace checkout.\n",
            1,
        )
    if "- If the issue is in `Todo`, move it to `In Progress` before starting implementation." not in text:
        text = text.replace(
            "- Work only in the provided Symphony workspace checkout.\n",
            "- Work only in the provided Symphony workspace checkout.\n"
            "- If the issue is in `Todo`, move it to `In Progress` before starting implementation.\n",
            1,
        )
    return text


def normalize_workflow_for_upstream_states(repo: Path, workflow_name: str) -> None:
    path = repo / ".orchestration" / f"{workflow_name}.WORKFLOW.md"
    if not path.exists():
        return

    text = path.read_text()
    text = normalize_agent_settings(text)
    text = normalize_active_states(text)
    text = normalize_review_state_names(text)
    text = normalize_issue_context(text)
    text = normalize_required_behavior(text)

    marker = "\nInstructions:\n"
    if marker in text:
        text = text.split(marker, 1)[0].rstrip() + "\n\n" + UPSTREAM_PROTOCOL_SECTION.lstrip()
    elif "\n## Required behavior\n" in text:
        text = text.split("\n## Required behavior\n", 1)[0].rstrip() + "\n\n" + UPSTREAM_PROTOCOL_SECTION.lstrip()
    elif "## Status map" in text:
        text = text.split("\n## Status map", 1)[0].rstrip() + "\n\n" + UPSTREAM_PROTOCOL_SECTION.lstrip()
    elif "## GitHub handoff requirements" in text:
        text = text.split("\n## GitHub handoff requirements", 1)[0].rstrip() + "\n\n" + UPSTREAM_PROTOCOL_SECTION.lstrip()
    else:
        text = text.rstrip() + "\n\n" + UPSTREAM_PROTOCOL_SECTION.lstrip()

    path.write_text(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enable OpenAI Symphony + Linear in a target repo.")
    parser.add_argument("--target-repo", default=".", help="Target repository path. Defaults to cwd.")
    parser.add_argument("--linear-project-slug-id", required=True, help="Linear GraphQL Project.slugId.")
    parser.add_argument("--workflow-name", help="Workflow file stem. Defaults to <repo>-medium.")
    parser.add_argument("--clone-url", help="Worker clone URL. Defaults to git remote origin.")
    parser.add_argument("--lane", choices=["small", "medium", "large", "content"], default="medium")
    parser.add_argument("--max-concurrent-agents", type=int, default=1)
    parser.add_argument("--required-branch", help="Required worker checkout branch. Defaults to current branch.")
    parser.add_argument("--required-path", action="append", default=[], help="Required repo anchor path.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing .orchestration files.")
    args = parser.parse_args()

    repo = Path(args.target_repo).expanduser().resolve()
    if not (repo / ".git").exists():
        raise SystemExit(f"Target is not a git repo: {repo}")

    workflow_name = args.workflow_name or f"{repo.name}-{args.lane}"
    run_starter_bootstrap(args, repo, workflow_name)
    normalize_workflow_for_upstream_states(repo, workflow_name)
    append_env_example(repo)
    write_start_script(repo, workflow_name)
    update_package_json(repo)
    copied_skills = copy_upstream_skills(repo)

    print(json.dumps({"ok": True, "repo": str(repo), "workflow_name": workflow_name, "copied_skills": copied_skills}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
