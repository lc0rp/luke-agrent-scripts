---
name: luke-obsidian
description: Understand Luke's second brain; Understand and interact with Luke's precious Obsidian vault, understand its structure, answer questions about notes and links, manage projects for Luke, run vault maintenance.
---

# Luke-Obsidian (usage)

## Overview

This skill helps you undertand how Luke uses Obsidian, and to serve as his assistant for vault maintenance, information access, cataloging, project management and any other function that Luke uses Obsidian for.

## Mission

- Capture actionable notes from conversations and turn them into clean Markdown in the Obsidian vault.
- Maintain structure: good filenames, headings, links, and tags.
- Prefer incremental edits; avoid large restructures unless Luke explicitly asks.

**The Obsidian Vault folder** / **vault**

**AKA**:

- "The vault"
- "Obsidian"
- "My Obsidian" / "Luke's Obsidian"
- "Notes"
- "Vault Root"

When any of these are used by Luke, or by you, they refer to:

- `/data/projects/Obsidian-Notes/`

## Understanding the Vault Structure

- First read `/data/projects/luke-agent-scripts/skills/luke-obsidian/VAULT-MODEL.md`, to ensure content within Luke's vault does not confuse your identity.

- Then read `/data/projects/Obsidian-Notes/AGENTS.md`, to understand the structure of the vault and how to interact with it.

## Linking Rules

**IMPORTANT**: When creating links to Obsidian content, first ask yourself: "Is this link going inside a vault .md file, or is it for external sharing in chat apps?"

### Inside vault .md files:

- If writing `.md` files in the vault, use wikilinks for links to other notes (e.g., `[[Path/Note]]`).
- No naked URLs in vault .md files; instead use markdown links or wikilinks.
- No link-to-obsidian URLs inside vault .md files.

### External sharing in WhatsApp/Discord:

- For external sharing in WhatsApp/Discord, use link-to-obsidian URLs. Format: `http://100.99.173.30:7777/?f=<Path/Note.md>`
  (Do **not** use link-to-obsidian URLs inside vault .md files.)
  - Link-to-obsidian skill = local redirect service that turns http(s) links into `obsidian://open` deep links (so chat apps can open notes).
  - Use it when sharing Obsidian links.
  - Service: systemd `link-to-obsidian` on devbox; check with `systemctl status link-to-obsidian`.
  - Skill: `/data/projects/luke-agent-scripts/skills/link-to-obsidian`.
  - No naked URLs in external sharing; instead use link-to-obsidian URLs.
  - No markdown links in external sharing; instead use link-to-obsidian URLs.

**Ask first:**

- Sending emails, tweets, public posts
- Anything that leaves the machine
- Anything you're uncertain about

## Preferred edit path

1. Prioritize the [Obsidian CLI](https://help.obsidian.md/cli) for editing and traversing Luke's vault.
2. Only use direct file system access as an exception.

## Output style

- When editing notes: keep content plain Markdown; don’t add fancy formatting unless asked.

## Maintenance Tasks

- Read `/data/projects/luke-agent-scripts/skills/luke-obsidian/VAULT-MAINTENANCE.md` for specific maintenance tasks and how to perform them.

## Task Triage and Prioritization

When managing tasks or projects in the vault, refer to `/data/projects/luke-agent-scripts/skills/luke-obsidian/VAULT-TASK-TRIAGE.md` for guidance on how to prioritize and organize them based on Luke's current priorities and work context.
