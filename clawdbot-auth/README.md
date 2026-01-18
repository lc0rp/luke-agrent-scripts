# clawdbot-auth (OpenAI Codex OAuth)

Scripts to manage **OpenAI Codex OAuth** credentials per Clawdbot agent. This uses
`openai-codex:codex-cli` profiles (OAuth from Codex CLI), **not** API keys.

## Prereqs
- Codex CLI already logged into the desired OpenAI account on this host
- `jq` installed
- Clawdbot CLI available (`clawdbot` in PATH)

## 1) Force sync Codex OAuth -> agent

Log into Codex CLI for the account you want, then:

```bash
./sync_codex_to_agent.sh <agent-id>
```

Optional: rotate Codex auth after sync:

```bash
./sync_codex_to_agent.sh <agent-id> --rotate-codex-auth
```

What it does:
- Deletes the agent's existing `openai-codex:codex-cli` entry + usage stats
- Loads the auth store (which re-syncs from Codex CLI)
- Prints the stored profile as a sanity check
 - When `--rotate-codex-auth` is used: moves `auth.json` to a timestamped `.bak`

## 2) Swap Codex OAuth between agents

```bash
./swap_codex_between_agents.sh <agent-a> <agent-b>
```

What it does:
- Swaps the `openai-codex:codex-cli` profile between the two agents
- Clears usage stats for that profile (avoids cooldown carryover)

## 3) Status across agents

```bash
./status_codex_agents.sh
```

Shows each agent and whether `openai-codex:codex-cli` is present + expiry.

Example output:

```
agent            codex        label             expires                  authfile
main             present      acct_123          2026-01-16T12:34:56Z (in 3h12m)  present
work             present      work@company.com  2026-01-15T08:00:00Z (2h ago)    present
personal         absent       -                 -                       present
```

## macOS helper (Keychain + file rotation)

On macOS, Codex CLI uses Keychain. This helper syncs the agent and can rotate
credentials (Keychain + file) when `--rotate-codex-auth` is passed:

```bash
./sync_codex_to_agent_macos.sh <agent-id> --rotate-codex-auth
```

## Notes
- Codex CLI credentials are read from:
  - macOS: Keychain ("Codex Auth")
  - Linux: `~/.codex/auth.json`
- Clearing `~/.codex/auth.json` on macOS may not clear Keychain creds.
- This is **one-way** sync (Codex CLI -> Clawdbot). Clawdbot does not write back.
- API keys are not touched. If `OPENAI_API_KEY` is set, it can still be used by provider `openai`.

## Files
- `sync_codex_to_agent.sh`
- `swap_codex_between_agents.sh`
