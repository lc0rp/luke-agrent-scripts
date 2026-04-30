---
name: frontend-web-design
description: Create world-class frontend web UI/UX inside Codex or GPT. Use this skill when building or redesigning websites, web apps, landing pages, dashboards, design systems, React components, HTML/CSS layouts, or any browser-based interface where generic AI aesthetics are a risk. It improves art direction, composition, image-led hierarchy, narrative page structure, design-system discipline, responsive behavior, accessibility, motion restraint, screenshot-driven iteration, and anti-template taste for non-designers who still want polished, memorable, product-appropriate interfaces.
---

# Frontend Web Design

Use this skill for browser-based UI work where taste, hierarchy, structure, imagery, and interaction quality matter.

This skill exists to stop generic AI UI and replace it with a tighter workflow:
- start with composition, not components
- pick an explicit visual direction
- freeze a small design system early
- use screenshots, mood boards, or generated visuals as guardrails
- structure the page or screen as a narrative
- verify visually in browser before handoff

## Scope

In scope:
- websites
- web apps
- landing pages
- dashboards
- settings screens
- design-system refreshes
- UI polish passes
- screenshot-to-implementation work

Out of scope:
- native iOS, Android, macOS design
- print or slide design
- logo or full brand identity creation unless it directly supports a web UI task

## GPT-5.5 Operating Mode

When model settings are available, start at `low` reasoning for straightforward UI work. Use `medium` when the task needs multi-step codebase navigation, browser verification, or several interacting states. Use `high` only for broad redesigns, unclear product constraints, or failures that need deeper investigation.

Use GPT-5.5 as an outcome-first design partner. State the destination and constraints, then let the model choose the efficient path unless the product or codebase requires a specific sequence.

Before coding, define:
1. Target outcome: what screen, page, flow, or component should exist.
2. Success criteria: what must be true in the rendered UI before handoff.
3. Constraints: stack, brand, content, accessibility, performance, and viewport requirements.
4. Visual evidence: screenshots, references, mood board, generated options, or a brief visual thesis.
5. Content source: real product context and real copy whenever possible.

Stop when the requested surface is implemented, visually verified after the final code change, and the final handoff can name the screens and viewports checked.

## Design Dials

When the request is open-ended, set these explicitly:
- `DESIGN_VARIANCE` 1-10: how experimental the layout should be
- `MOTION_INTENSITY` 1-10: how visible and frequent motion should be
- `VISUAL_DENSITY` 1-10: how much content should fit on screen

Defaults:
- marketing pages: `DESIGN_VARIANCE 6`, `MOTION_INTENSITY 5`, `VISUAL_DENSITY 4`
- product UI: `DESIGN_VARIANCE 3`, `MOTION_INTENSITY 3`, `VISUAL_DENSITY 7`

Raise these only with intent. More is not better.

## Working Model

Before building substantial UI, write three things:
- visual thesis: one sentence describing mood, material, energy, and level of restraint
- content plan: the section sequence or screen narrative
- interaction thesis: 2 or 3 motion ideas that change the feel of the work

Each section gets one job, one dominant visual idea, and one primary takeaway or action.

Use [references/style-system-template.md](references/style-system-template.md) when you need a quick artifact.

## Core Defaults

- Start with composition, not components.
- Treat the first viewport as a poster, not a document.
- Make the brand or product unmistakable in the first screen on branded pages.
- Prefer one strong visual anchor over many medium-strength elements.
- Use whitespace, scale, alignment, cropping, and contrast before adding chrome.
- Limit the system: two typefaces max, one accent color by default.
- Default to cardless layouts. Use sections, columns, dividers, media blocks, and tables before adding panels.
- Write in product language, not design commentary.

## Preferred Workflow

### 1. Lock the brief

Create or infer:
- product goal
- audience
- primary task
- tone
- constraints
- success criteria

If the request is underspecified, make the smallest reasonable assumption set and state it briefly.

### 2. Establish visual guardrails

When possible:
- use uploaded screenshots first
- otherwise generate a mood board or a few image directions
- otherwise ask the user for references

Default to uploaded or pre-generated images when they exist. If image generation is available and the task benefits from it, create visuals that match the intended style. Do not rely on random web images unless the user explicitly asks for them.

### 3. Freeze the system

Define:
- typography roles: display, headline, body, caption
- core tokens: background, surface, text, muted, accent, border, focus
- spacing scale
- radius scale
- border and shadow policy
- motion policy

Prefer CSS variables or design tokens.

### 4. Choose the layout mode

For landing pages:
- hero
- support
- detail
- proof when needed
- final CTA

For app surfaces:
- primary workspace
- navigation
- secondary context or inspector
- one clear accent for action or state

Read [references/prompt-recipes.md](references/prompt-recipes.md) for concrete patterns.

### 5. Build from real primitives

Prefer:
- existing project components first
- React plus Tailwind when a greenfield web stack is appropriate
- shadcn/ui or equivalent tokenized components next
- Radix primitives when interaction complexity matters
- AI Elements or Prompt Kit patterns for AI-native product surfaces

Do not invent a large component library from scratch unless the task explicitly requires it.

Implementation guardrails:
- check the dependency file before adding imports or new libraries
- prefer CSS Grid over fragile flexbox percentage math for multi-column layout
- use `min-height: 100dvh` or equivalent instead of naive `100vh` full-screen sections when mobile browser chrome matters
- use semantic HTML where it improves structure and accessibility
- use tabular figures or monospace numerals for dense numeric UI when scan speed matters

### 6. Verify visually

Use Playwright, the in-app browser, or equivalent browser inspection when visual QA matters and tools are available. Relaunch the real surface after the final code change before calling the work complete.

Check:
- multiple viewports
- state transitions
- navigation flows
- visual similarity to screenshots or references
- overlap from fixed or floating elements
- optical alignment of icons, buttons, and mixed text blocks
- whether all requested deliverables are actually finished
- whether text, fixed elements, and interactive chrome overlap at any target breakpoint

Use [references/review-checklist.md](references/review-checklist.md).

## Landing Pages

Default sequence:
1. Hero: brand or product, promise, CTA, and one dominant visual
2. Support: one concrete feature, offer, or proof point
3. Detail: atmosphere, workflow, or product depth
4. Final CTA: convert, start, visit, or contact

Hero rules:
- One composition only.
- Prefer a full-bleed image or dominant visual plane by default.
- Keep the brand or product name at hero strength.
- Keep the text column narrow and anchored to a calm area.
- Keep headlines readable in one glance.
- Keep the first viewport small in scope: brand, one headline, one short supporting sentence, one CTA group, one dominant image.
- No hero cards, stat strips, logo clouds, pill soup, floating dashboards, or detached promo overlays by default.
- If the first viewport still works after removing the image, the image is too weak.
- If the brand disappears after hiding the nav, the hierarchy is too weak.

## App Surfaces

Default to restrained, calm product UI:
- strong typography and spacing
- few colors
- dense but readable information
- minimal chrome
- cards only when the card is the interaction

Avoid:
- dashboard-card mosaics
- thick borders around every region
- decorative gradients behind routine product UI
- multiple competing accent colors
- ornamental icons that do not improve scanning
- marketing hero copy inside utility screens unless explicitly requested

If a panel can become plain layout without losing meaning, remove the card treatment.

## Imagery

Imagery must do narrative work.

- Use at least one strong, real-looking image for brands, venues, editorial pages, and lifestyle products.
- Prefer in-situ photography over abstract gradients or fake 3D objects.
- Choose or crop images with a stable tonal area for text.
- Do not use images with embedded signage, logos, or typographic clutter that fights the UI.
- Do not use images with built-in UI frames, cards, or panels.
- If multiple moments are needed, use multiple images, not one collage.

The first viewport needs a real visual anchor. Decorative texture is not enough.

## Copy

- Write in product language, not design commentary.
- Let the headline carry the meaning.
- Supporting copy should usually be one short sentence.
- Cut repetition between sections.
- Give every section one responsibility: explain, prove, deepen, or convert.
- Use utility copy for dashboards, admin tools, and workspaces.
- If a sentence could appear in a homepage hero or ad, rewrite it until it sounds like product UI.
- If deleting 30 percent of the copy improves the page, keep deleting.
- Avoid stock AI wording and startup filler.

## Motion

Use motion to create presence and hierarchy, not noise.

For visually led work, ship 2 or 3 intentional motions:
- one entrance sequence
- one scroll-linked, sticky, or depth effect
- one hover, reveal, or layout transition that sharpens affordance

Prefer Framer Motion or Motion when available.

Motion rules:
- smooth on mobile
- fast and restrained
- consistent across the page
- removed if ornamental only

Keep fixed or floating UI elements from overlapping text, buttons, or key content across screen sizes. Place them in safe areas and verify them at multiple breakpoints.

## Hard Rules

- No cards by default.
- No hero cards by default.
- No boxed or center-column hero when the brief calls for full bleed.
- No more than one dominant idea per section.
- No more than two typefaces without a clear reason.
- No more than one accent color unless the product already has a strong system.
- No generic SaaS card grid as the first impression.
- No beautiful image with weak brand presence.
- No busy imagery behind text.
- No filler copy.
- No decorative copy that explains the UI instead of serving the product.
- No fake charts, fake metrics, or filler panels.
- No unfinished outputs, placeholder comments, or "same pattern continues" shortcuts when the task calls for real implementation.

## Codex / GPT Execution Rules

- Read the local codebase before introducing a new visual language.
- Preserve the product's existing identity when it is strong.
- If the current UI is weak or generic, improve it without breaking the information architecture.
- If screenshots exist, use them as primary visual truth.
- If screenshots do not exist, create a brief style system and visual direction artifact before large implementation work.
- Prefer complete, runnable UI over mock fragments.
- Always account for mobile web behavior, even when desktop is the main target.
- Ground the work in real content, real product context, and real interactions.
- Do not rewrite the stack for a redesign pass unless the user explicitly asks for it.

## Read When

- Source rationale or further reading needed:
  [references/sources.md](references/sources.md)
- Need a design-brief artifact:
  [references/style-system-template.md](references/style-system-template.md)
- Need concrete prompt patterns:
  [references/prompt-recipes.md](references/prompt-recipes.md)
- Need QA criteria:
  [references/review-checklist.md](references/review-checklist.md)
- Need stack and install guidance:
  [references/install-recipes.md](references/install-recipes.md)
- Need an audit-first workflow for an existing UI:
  [/Users/luke/Documents/dev/luke-agent-scripts/skills/frontend-redesign-audit/SKILL.md](/Users/luke/Documents/dev/luke-agent-scripts/skills/frontend-redesign-audit/SKILL.md)

## Output Expectations

For substantial UI work, leave behind:
- a visual thesis
- a content plan
- an interaction thesis
- explicit tokens or CSS variables
- realistic states
- responsive behavior
- accessibility-conscious interactions
- the rendered screens and viewports visually verified after the final code change
- whether the result matched the latest user reference, when a reference exists

Aim for deliberate, product-appropriate, non-generic UI that could survive real scrutiny.
