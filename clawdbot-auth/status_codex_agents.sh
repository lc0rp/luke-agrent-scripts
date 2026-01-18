#!/usr/bin/env bash
set -euo pipefail

# Status for Codex OAuth profile across all agents.

STATE_DIR="${CLAWDBOT_STATE_DIR:-$HOME/.clawdbot}"
PROFILE="openai-codex:codex-cli"
CONFIG_PATH="${CLAWDBOT_CONFIG_PATH:-$STATE_DIR/clawdbot.json}"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 1
fi

printf '%-16s %-12s %-18s %-24s %-10s\n' "agent" "codex" "label" "expires" "authfile"

resolve_label_from_config() {
  local profile_id="$1"
  if [ ! -f "$CONFIG_PATH" ]; then
    return 0
  fi
  if command -v node >/dev/null 2>&1; then
    node - <<'NODE' "$CONFIG_PATH" "$profile_id" 2>/dev/null || true
const fs = require("fs");
const path = process.argv[1];
const profileId = process.argv[2];
let raw;
try {
  raw = fs.readFileSync(path, "utf8");
} catch {
  process.exit(0);
}
let data = null;
try {
  data = JSON.parse(raw);
} catch {
  try {
    const JSON5 = require("json5");
    data = JSON5.parse(raw);
  } catch {
    process.exit(0);
  }
}
const entry = data?.auth?.profiles?.[profileId];
const label = entry?.email || entry?.label || entry?.name || "";
if (label) console.log(label);
NODE
  fi
}

for agent_dir in "$STATE_DIR"/agents/*/agent; do
  if [ ! -d "$agent_dir" ]; then
    continue
  fi
  agent_id="$(basename "$(dirname "$agent_dir")")"
  auth_file="$agent_dir/auth-profiles.json"
  if [ ! -f "$auth_file" ]; then
    printf '%-16s %-12s %-18s %-24s %-10s\n' "$agent_id" "missing" "-" "-" "absent"
    continue
  fi

  profile_json="$(jq -c --arg p "$PROFILE" '.profiles[$p] // empty' "$auth_file")"
  if [ -z "$profile_json" ]; then
    printf '%-16s %-12s %-18s %-24s %-10s\n' "$agent_id" "absent" "-" "-" "present"
    continue
  fi

  label_from_config="$(resolve_label_from_config "$PROFILE")"
  label_from_profile="$(jq -r '(.email // .accountId // empty)' <<<"$profile_json")"
  label="${label_from_config:-$label_from_profile}"
  if [ -z "$label" ]; then
    label="-"
  fi

  expires_ms="$(jq -r 'try .expires // empty' <<<"$profile_json")"
  if [ -n "$expires_ms" ] && [ "$expires_ms" != "null" ]; then
    expires_iso="$(python3 - <<'PY' "$expires_ms"
import sys, time, datetime
try:
    ms = int(sys.argv[1])
except Exception:
    print("unknown")
    raise SystemExit(0)
now = int(time.time())
exp = int(ms / 1000)
dt = datetime.datetime.fromtimestamp(exp, datetime.UTC)
iso = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
delta = exp - now
if delta == 0:
    print(f"{iso} (now)")
    raise SystemExit(0)
absd = abs(delta)
days, rem = divmod(absd, 86400)
hours, rem = divmod(rem, 3600)
mins, _ = divmod(rem, 60)
if days > 0:
    rel = f"{days}d{hours}h"
elif hours > 0:
    rel = f"{hours}h{mins}m"
else:
    rel = f"{max(1, mins)}m"
if delta > 0:
    print(f"{iso} (in {rel})")
else:
    print(f"{iso} ({rel} ago)")
PY
)"
  else
    expires_iso="unknown"
  fi

  printf '%-16s %-12s %-18s %-24s %-10s\n' "$agent_id" "present" "$label" "$expires_iso" "present"

done
