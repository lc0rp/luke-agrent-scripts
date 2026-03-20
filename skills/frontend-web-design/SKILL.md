---
name: frontend-web-design
description: Create world-class frontend web UI/UX inside Codex or GPT. Use this skill when building or redesigning websites, web apps, landing pages, dashboards, design systems, React components, HTML/CSS layouts, or any browser-based interface where generic AI aesthetics are a risk. It improves visual direction, information hierarchy, design-system discipline, responsive behavior, accessibility, motion restraint, screenshot-driven iteration, and anti-template taste. It is optimized for non-designers who still want polished, memorable, product-appropriate interfaces.
---

# Frontend Web Design

Use this skill for browser-based UI work.

This skill exists to stop generic AI UI and replace it with a tighter workflow:
- choose an explicit visual direction
- freeze a small design system early
- build on real components and tokens
- iterate with screenshots, not only text
- review hierarchy, responsiveness, and accessibility before handoff

## Scope

In scope:
- websites
- web apps
- marketing pages
- dashboards
- settings screens
- design-system refreshes
- UI polish passes
- screenshot-to-implementation work

Out of scope:
- native iOS, Android, macOS design
- print or slide design
- logo/brand identity creation from scratch unless it directly supports a web UI task

## Default Operating Mode

Assume the user wants strong design with clear intention.

Before coding:
1. Identify product type, audience, primary task, and tone.
2. Pick one design direction with a short name.
3. Freeze a minimal system: type, color, spacing, radius, shadows, motion.
4. Prefer an existing component system or app style over invention.
5. Decide what should feel memorable on first load.

Then build:
1. Establish layout and hierarchy before decoration.
2. Use tokens and CSS variables early.
3. Make every screen state believable: empty, loading, error, hover, focus, active, disabled.
4. Make desktop and mobile both real.
5. Validate with screenshots or browser review when feasible.

## Non-Negotiables

- No vague aesthetic. Name the direction.
- No default AI SaaS look.
- No purple-on-white fallback.
- No decorative hero blocks inside product UI unless the product genuinely needs them.
- No fake charts, fake metrics, or filler panels.
- No over-rounded everything.
- No excessive glassmorphism, blur haze, or gradient fog as the default visual language.
- No decorative copy that explains the UI instead of letting the UI explain itself.
- No typography-by-default. Pick a real point of view.
- No component soup. The interface should feel like one product.

## Preferred Workflow

### 1. Lock the design brief

Create or infer:
- product goal
- target user
- key jobs-to-be-done
- tone
- constraints
- success criteria

If the request is underspecified, make the smallest reasonable assumption set and state it briefly.

Use [references/style-system-template.md](references/style-system-template.md) when you need a quick artifact.

### 2. Explore direction before polishing

Generate 2 or 3 distinct directions internally or briefly in chat:
- conservative and credible
- expressive and memorable
- dense and utilitarian

Then choose one. Do not average them together.

### 3. Freeze the system early

Define:
- typography pair or font strategy
- color tokens
- spacing scale
- radius scale
- border treatment
- shadow policy
- motion policy

Prefer CSS variables or design tokens.

Read [references/install-recipes.md](references/install-recipes.md) if you need a practical base stack.

### 4. Build from real primitives

Prefer:
- existing project components first
- shadcn/ui or equivalent tokenized components next
- Radix primitives when interaction complexity matters
- AI Elements or Prompt Kit patterns for AI-native product surfaces

Do not ask the model to invent a large component library from scratch unless the task explicitly requires it.

### 5. Use image-first iteration

When possible:
- ask for or capture screenshots
- compare generated UI against screenshots
- perform critique passes from visuals, not just code

Image-guided refinement usually beats text-only prompting for spacing, balance, and visual hierarchy.

### 6. Review with a hard checklist

Before handoff, audit against:
- hierarchy
- information density
- responsiveness
- keyboard and focus states
- contrast
- loading/empty/error states
- content realism
- motion restraint

Use [references/review-checklist.md](references/review-checklist.md).

## Design Heuristics

### Hierarchy

- Make the primary action obvious in under 3 seconds.
- Use fewer emphasis levels, not more.
- Group related controls tightly.
- Keep labels literal and short.
- Remove sections that only repeat page context.

### Layout

- Prefer stable structure over novelty for app screens.
- Use asymmetry only when it improves scanning or brand character.
- Keep edge alignment clean.
- Density is allowed when the product benefits from it.

### Typography

- Choose a type system on purpose.
- Use contrast through size, weight, and rhythm before using color.
- Avoid ornamental micro-labels and fake sophistication.

### Color

- Start from a restrained palette.
- Use accent color for action or meaning, not everywhere.
- Make neutrals do most of the structural work.

### Motion

- One meaningful entrance sequence is better than many random animations.
- Favor opacity, filter, and small position changes over exaggerated transforms.
- Respect reduced-motion preferences.

### Components

- Buttons should look tappable and trustworthy.
- Inputs should be plain, readable, and stateful.
- Tables and lists should prioritize scan speed.
- Cards are optional, not mandatory.

### Copy

- Prefer product language over generic startup language.
- Use concrete nouns and verbs.
- Do not add filler marketing lines inside utility screens.

## Codex / GPT Execution Rules

- Read the local codebase before introducing a new visual language.
- Preserve the product's existing identity when one exists.
- If the current UI is weak or generic, improve it without breaking the product's information architecture.
- Use `Playwright` or equivalent browser inspection when visual QA matters and tools are available.
- If the user gives screenshots, use them as primary visual truth.
- If no screenshots exist, create a brief system artifact before large implementation work.
- Prefer complete, runnable UI over mock fragments.
- Always account for mobile web behavior, even when desktop is the main target.

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

## Output Expectations

For substantial UI work, leave behind:
- a named visual direction
- explicit tokens or CSS variables
- realistic states
- responsive behavior
- accessibility-conscious interactions
- a brief note on what changed and why

Aim for deliberate, product-appropriate, non-generic UI that could survive real scrutiny.
