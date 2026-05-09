#!/usr/bin/env python3
import argparse
import json
import os
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
    append_env_example(repo)
    write_start_script(repo, workflow_name)
    update_package_json(repo)

    print(json.dumps({"ok": True, "repo": str(repo), "workflow_name": workflow_name}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
