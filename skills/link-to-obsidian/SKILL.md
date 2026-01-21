---
name: link-to-obsidian
description: Generate or explain link-to-obsidian HTTP links and verify/manage the link-to-obsidian redirect service on the devbox (systemd service: link-to-obsidian). Use when you need shareable http(s) links that open Obsidian notes, or when checking/restarting the redirect service.
---

# Link-to-Obsidian

## Overview

Use the link-to-obsidian service to turn shareable http(s) links into `obsidian://open` deep links. This is useful for chats/apps that only allow http(s) URLs (Discord/WhatsApp).

## Quick start (generate a link)

Format:

```
http://<host>:<port>/open?vault=<VaultName>&file=<Path/Note.md>
```

Example:

```
http://dev.quail-mercat.ts.net:7777/open?vault=Obsidian-Notes&file=0-Inbox/Tasks.md
```

Notes:
- Preserve the **entire** query string; only the scheme/host/port change from `obsidian://open`.
- Percent-encode the `file=` path the same way Obsidian expects.

## Check service status / logs

```bash
systemctl status link-to-obsidian --no-pager
journalctl -u link-to-obsidian -f
```

## Config

- Env file: `/etc/link-to-obsidian/link-to-obsidian.env` (override with `LTO_CONFIG`)
- Common keys: `LTO_TAILSCALE_IP`, `LTO_TAILSCALE_DNS`, `LTO_VAULT_NAME`, `LTO_SAMPLE_FILE`, `PORT` (default 7777)

## Restart

```bash
sudo systemctl restart link-to-obsidian
```

## Source / docs

- Repo: `/data/projects/link-to-obsidian`
- See: `README.md`, `spec.md`
