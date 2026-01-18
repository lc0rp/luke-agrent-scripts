#!/usr/bin/env bash
set -euo pipefail

# Force-sync current Codex CLI OAuth creds into a specific agent.
# Usage: ./sync_codex_to_agent.sh <agent-id> [--rotate-codex-auth]

usage() {
  cat <<'USAGE'
Usage: ./sync_codex_to_agent.sh <agent-id> [--rotate-codex-auth]

Options:
  --rotate-codex-auth  Move ~/.codex/auth.json (or $CODEX_HOME/auth.json) to a
                       timestamped .bak file after sync.
  -h, --help           Show this help.
USAGE
}

ROTATE_CODEX_AUTH=0
AGENT_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rotate-codex-auth)
      ROTATE_CODEX_AUTH=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -z "$AGENT_ID" ]]; then
        AGENT_ID="$1"
        shift
      else
        echo "Unknown argument: $1"
        usage
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$AGENT_ID" ]]; then
  usage
  exit 1
fi

STATE_DIR="${CLAWDBOT_STATE_DIR:-$HOME/.clawdbot}"
AGENT_DIR="$STATE_DIR/agents/$AGENT_ID/agent"
AUTH="$AGENT_DIR/auth-profiles.json"
PROFILE="openai-codex:codex-cli"

mkdir -p "$AGENT_DIR"

if [ ! -f "$AUTH" ]; then
  printf '{"version":1,"profiles":{}}\n' > "$AUTH"
fi

# Remove existing codex-cli profile + usage stats so sync will repopulate.
tmp="$(mktemp)"
jq --arg p "$PROFILE" '
  .profiles = (.profiles // {} | del(.[$p])) |
  .usageStats = (if .usageStats then (.usageStats | del(.[$p])) else .usageStats end)
' "$AUTH" > "$tmp"
mv "$tmp" "$AUTH"

# Trigger auth store load + external CLI sync for this agent.
CLAWDBOT_AGENT_DIR="$AGENT_DIR" clawdbot models status --plain >/dev/null

# Print the stored profile for sanity.
jq -r --arg p "$PROFILE" '.profiles[$p] // empty' "$AUTH"

if [[ "$ROTATE_CODEX_AUTH" -eq 1 ]]; then
  CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
  CODEX_AUTH_FILE="$CODEX_HOME_DIR/auth.json"
  if [[ -f "$CODEX_AUTH_FILE" ]]; then
    ts="$(date +%Y%m%d-%H%M%S)"
    mv "$CODEX_AUTH_FILE" "$CODEX_AUTH_FILE.bak.$ts"
    echo "Moved $CODEX_AUTH_FILE to $CODEX_AUTH_FILE.bak.$ts"
  else
    echo "No Codex auth file found at $CODEX_AUTH_FILE"
  fi
fi
