#!/usr/bin/env bash
set -euo pipefail

# macOS helper: sync Codex OAuth creds to agent, then optionally rotate and clear.
# Usage: ./sync_codex_to_agent_macos.sh <agent-id> [--rotate-codex-auth]

usage() {
  cat <<'USAGE'
Usage: ./sync_codex_to_agent_macos.sh <agent-id> [--rotate-codex-auth]

Options:
  --rotate-codex-auth  Backup and clear Keychain + auth.json after sync.
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

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This helper is macOS-only. Use sync_codex_to_agent.sh on Linux."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/sync_codex_to_agent.sh" "$AGENT_ID"

CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
ACCOUNT_HASH="$(python3 - <<'PY'
import hashlib, os
home=os.environ.get('CODEX_HOME') or os.path.expanduser('~/.codex')
print(hashlib.sha256(home.encode()).hexdigest()[:16])
PY
)"
ACCOUNT="cli|${ACCOUNT_HASH}"

if [[ "$ROTATE_CODEX_AUTH" -eq 1 ]]; then
  ts="$(date +%Y%m%d-%H%M%S)"
  keychain_backup="$CODEX_HOME_DIR/codex-keychain.bak.$ts.json"
  if secret="$(security find-generic-password -s "Codex Auth" -a "$ACCOUNT" -w 2>/dev/null)"; then
    printf '%s\n' "$secret" > "$keychain_backup"
    echo "Backed up Keychain entry to $keychain_backup"
  else
    echo "No Keychain entry found for Codex Auth ($ACCOUNT)"
  fi

  CODEX_AUTH_FILE="$CODEX_HOME_DIR/auth.json"
  if [[ -f "$CODEX_AUTH_FILE" ]]; then
    mv "$CODEX_AUTH_FILE" "$CODEX_AUTH_FILE.bak.$ts"
    echo "Moved $CODEX_AUTH_FILE to $CODEX_AUTH_FILE.bak.$ts"
  else
    echo "No Codex auth file found at $CODEX_AUTH_FILE"
  fi

  security delete-generic-password -s "Codex Auth" -a "$ACCOUNT" >/dev/null 2>&1 || true
  echo "Cleared Keychain entry: service=Codex Auth account=$ACCOUNT"
fi
