---
name: ios-simulator-screenshot
description: Capture viewport and stitched full-page screenshots from a booted iOS Simulator. Use when the user asks to show the current simulator screen, capture a specific iPhone UI, export a scrollable screen, or produce a stitched screenshot from multiple simulator viewports.
---

# iOS Simulator Screenshot

Use this skill when the task is about producing screenshots from the local iOS Simulator.

## Scope

In scope:
- capture the current visible simulator viewport
- save a screenshot artifact from the booted simulator
- create a stitched long screenshot from a vertically scrollable screen
- verify that the simulator is booted and the target app is frontmost enough for capture

Out of scope:
- design critique or UI redesign by itself; pair with `$ios-ux-design` when needed
- arbitrary swipe automation inside any iOS app; generic simulator scrolling is still manual
- physical iPhone screenshots

## Quick Start

### Current viewport

```bash
TS=$(date +%Y%m%d-%H%M%S)
OUT="output/ios-sim-${TS}.png"
xcrun simctl io booted screenshot "$OUT"
```

Use this first for "show me the current simulator screen" or when only the visible region matters.

### Full-page stitched screenshot

Run the bundled helper:

```bash
python3 scripts/fullpage_screenshot.py
```

Workflow:
1. Put the target scroll view on screen in the booted simulator.
2. Press Enter to capture the current viewport.
3. Scroll manually in the Simulator.
4. Press Enter again for the next segment.
5. Type `s` to stitch.

Outputs:
- raw frames under `output/ios-sim-fullpage/<timestamp>/raw/`
- stitched result as `stitched-fullpage.png`
- overlap report as `capture-metadata.json`

## Health Check

Before capturing, confirm the simulator is usable:

```bash
xcrun simctl list devices | rg Booted
open -a Simulator
```

If no device is booted, boot or launch one first.

## Decision Guide

- User wants the visible screen only: use `simctl io ... screenshot`.
- User wants "the whole page" or content below the fold: use `scripts/fullpage_screenshot.py`.
- User needs a shareable artifact after UI work: save into repo-local `output/` or another task-local artifact directory.
- User asks why the screenshot is incomplete: explain that Simulator only captures the current viewport natively.

## Long Screenshot Rules

- Keep the same device orientation and scale for every frame.
- Scroll vertically only; horizontal drift weakens overlap matching.
- Capture with small overlaps between frames; do not skip large sections.
- If the stitch leaves a visible seam, recapture that segment with more overlap.
- If the screen changes while scrolling, state that the result is stitched and may contain seams.

## Dependencies

The stitched workflow expects:
- `xcrun`
- `magick` from ImageMagick

Quick check:

```bash
command -v xcrun
command -v magick
```

If `magick` is missing, you can still take viewport screenshots, but you cannot stitch them with the bundled helper.

## Script

Use the bundled helper instead of rewriting the overlap-detection logic:

- [scripts/fullpage_screenshot.py](scripts/fullpage_screenshot.py)

It supports:
- interactive capture from the booted simulator
- stitching from an existing raw directory via `--from-dir`
- custom output directories and filenames

## Output Expectations

When you use this skill:
- leave behind the screenshot file path
- say whether it is a viewport capture or a stitched long screenshot
- mention any visible seam or limitation
- keep the artifact in a predictable local directory
