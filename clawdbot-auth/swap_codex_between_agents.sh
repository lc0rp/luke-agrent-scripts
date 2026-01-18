#!/usr/bin/env bash
set -euo pipefail

# Swap Codex OAuth creds between two agents.
# Usage: ./swap_codex_between_agents.sh <agent-a> <agent-b>

A="${1:?agent A}"
B="${2:?agent B}"

STATE_DIR="${CLAWDBOT_STATE_DIR:-$HOME/.clawdbot}"
AUTH_A="$STATE_DIR/agents/$A/agent/auth-profiles.json"
AUTH_B="$STATE_DIR/agents/$B/agent/auth-profiles.json"
PROFILE="openai-codex:codex-cli"

[ -f "$AUTH_A" ] || { echo "missing $AUTH_A"; exit 1; }
[ -f "$AUTH_B" ] || { echo "missing $AUTH_B"; exit 1; }

P1="$(jq -c --arg p "$PROFILE" '.profiles[$p] // empty' "$AUTH_A")"
P2="$(jq -c --arg p "$PROFILE" '.profiles[$p] // empty' "$AUTH_B")"

[ -n "$P1" ] || { echo "no $PROFILE in $A"; exit 1; }
[ -n "$P2" ] || { echo "no $PROFILE in $B"; exit 1; }

tmpA="$(mktemp)"
tmpB="$(mktemp)"

jq --arg p "$PROFILE" --argjson new "$P2" '
  .profiles = (.profiles // {} | .[$p] = $new) |
  .usageStats = (if .usageStats then (.usageStats | del(.[$p])) else .usageStats end)
' "$AUTH_A" > "$tmpA"

jq --arg p "$PROFILE" --argjson new "$P1" '
  .profiles = (.profiles // {} | .[$p] = $new) |
  .usageStats = (if .usageStats then (.usageStats | del(.[$p])) else .usageStats end)
' "$AUTH_B" > "$tmpB"

mv "$tmpA" "$AUTH_A"
mv "$tmpB" "$AUTH_B"
