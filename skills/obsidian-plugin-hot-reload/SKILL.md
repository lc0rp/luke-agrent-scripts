---
name: obsidian-plugin-hot-reload
description: Start or manage a local hot-reload loop for Obsidian plugin development. Use when the user wants live rebuilds, symlinked plugin artifacts, local-vault testing, or automatic plugin reload after bundle changes.
---

# Obsidian Plugin Hot Reload

Use this for Luke-style local Obsidian plugin development loops.

## Prefer repo-local helpers

Before assembling commands by hand, look for a repo-local helper such as:

- `start-local-hot-reload.sh`
- a private docs/scripts helper under `*/plugin/scripts/`
- local-development docs that define a supported hot-reload command

If such a helper exists, prefer it over ad hoc commands.

## KeepSidian

For KeepSidian, use the private helper:

```bash
/Users/luke/Documents/dev/KeepSidianProj/KeepSidianDev/plugin/scripts/start-local-hot-reload.sh
```

Reference docs:

- `/Users/luke/Documents/dev/KeepSidianProj/KeepSidianDev/plugin/docs/06-delivery/local-development.md`

What that helper already handles:

- ensures the local server is listening on `:8080`
- injects `KEEPSIDIAN_SERVER_URL=http://localhost:8080` into the watch build
- ensures the local vault plugin uses symlinks for `main.js`, `manifest.json`, and `styles.css`
- runs `npm run dev`
- watches bundle outputs with `fswatch`
- reloads the `keepsidian` plugin in the `Obsidian-Notes` vault

## If no helper exists

Assemble the hot-reload loop with this shape:

1. Ensure the local backend/server is running.
2. Ensure the plugin build uses the local server URL.
3. Symlink only the bundle artifacts into the vault plugin dir:
   - `main.js`
   - `manifest.json`
   - `styles.css`
4. Preserve plugin state files such as `data.json` and logs; do not replace the whole plugin folder with a symlink unless the repo explicitly wants that.
5. Start the watch build, usually `npm run dev`.
6. Watch the built bundle files with `fswatch` and reload the plugin through the Obsidian CLI.

## Obsidian CLI

On Luke's Mac, default to:

```bash
/Applications/Obsidian.app/Contents/MacOS/obsidian
```

Typical reload command:

```bash
/Applications/Obsidian.app/Contents/MacOS/obsidian plugin:reload id=<plugin-id> vault="<vault-name>"
```

## Validation

After starting the loop:

- verify the watch build is running
- verify the vault plugin artifacts are symlinks to the repo outputs
- verify the plugin is enabled in Obsidian
- if possible, make a small bundle change and confirm the plugin reloads
