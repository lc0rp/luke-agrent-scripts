---
name: ios-ux-design
description: Create world-class native iOS UI/UX inside Codex or GPT. Use this skill when designing, reviewing, or refining iPhone and iOS interfaces, SwiftUI screens, onboarding, forms, lists, tab/navigation architecture, search, modal flows, settings, accessibility, and visual polish. It improves Apple-native structure, touch ergonomics, Dynamic Type, semantic colors, SF Symbols, screenshot and simulator iteration, and anti-web guardrails for non-designers who want polished native results.
---

# iOS UX Design

Use this skill for native iOS interface work.

This skill exists to prevent two common failures:
- generic AI mobile UI
- web UI patterns pasted into iPhone screens

## Scope

In scope:
- iPhone-first product UI
- SwiftUI screen design
- iOS onboarding, settings, forms, lists, and flows
- tab, navigation stack, search, and sheet decisions
- accessibility and touch ergonomics
- screenshot-to-native redesign work
- native polish passes

Out of scope:
- Android
- macOS desktop UI
- mobile web
- full brand-identity creation outside app UI

## Default Operating Mode

Assume the user wants strong native design, not a small website in a phone frame.

Before coding:
1. Identify the primary user task and context.
2. Choose the native structure before styling.
3. Prefer system components and patterns unless the product has a clear reason not to.
4. Freeze a small native design system: text styles, semantic colors, symbols, spacing, motion.
5. Decide what should feel unmistakably iOS on first use.

Then build:
1. Prototype the flow in SwiftUI or within the existing native stack.
2. Make touch targets, focus, and readability real.
3. Cover empty, loading, error, disabled, confirmation, and permission states.
4. Validate with previews, simulator, and screenshots when feasible.
5. Review against HIG, accessibility, and anti-web checks before handoff.

## Non-Negotiables

- Do not turn iPhone screens into mini web dashboards.
- Do not invent custom navigation chrome without a strong product reason.
- Do not ship tiny touch targets. Use 44x44pt minimum.
- Do not hard-code colors when semantic or dynamic colors should be used.
- Do not ignore Dynamic Type, VoiceOver, reduced motion, or contrast.
- Do not over-card everything.
- Do not hide primary tasks inside decorative layouts.
- Do not force Liquid Glass or heavy translucency everywhere.
- Do not use generic startup copy inside utility screens.
- Do not treat iOS like a canvas for random novelty. Native trust matters.

## Preferred Workflow

### 1. Lock the task and context

Create or infer:
- user goal
- task frequency
- device context
- information density
- trust and risk level
- constraints

Use [references/ios-design-brief-template.md](references/ios-design-brief-template.md) when you need a quick artifact.

### 2. Choose the right native pattern first

Decide early between:
- list
- form
- tab bar
- navigation stack
- search
- sheet
- confirmation dialog
- full-screen cover

Read [references/native-patterns.md](references/native-patterns.md) when the structure is unclear.

### 3. Freeze the native system

Define:
- text styles
- semantic colors
- SF Symbols strategy
- spacing rhythm
- corner treatment
- motion and haptics policy

Prefer system defaults where possible. Native coherence beats unnecessary originality.

### 4. Prototype in SwiftUI first

When the codebase allows it:
- use `NavigationStack`
- use `List`, `Form`, `Section`, `Toolbar`, `sheet`, `confirmationDialog`, `searchable`
- prefer system materials, symbols, and text styles

If the app already uses UIKit or mixed architecture, respect the existing stack.

### 5. Iterate visually

When possible:
- ask for or capture screenshots
- use SwiftUI previews
- run the simulator
- critique from visuals, not only from code

For explicit simulator screenshot capture or stitched full-page export requests, use `$ios-simulator-screenshot`.

Screenshot and simulator loops are much better than text-only guessing for spacing, affordance, and density.

### 6. Review with a hard checklist

Before handoff, audit:
- task clarity
- container choice
- touch ergonomics
- readability
- accessibility
- state coverage
- localization resilience
- native feel

Use [references/review-checklist.md](references/review-checklist.md).

## Native Heuristics

### Structure

- Start from the task, not the decoration.
- Use lists and forms aggressively; they are first-class iOS patterns.
- Keep top-level navigation shallow and obvious.
- Use sheets for focused tasks, not as a default dumping ground.

### Typography and Iconography

- Use San Francisco text styles semantically.
- Use SF Symbols when system meaning exists.
- Let hierarchy come from size, weight, placement, and spacing before color.

### Color and Materials

- Prefer semantic colors and dynamic materials.
- Let content lead; chrome should support it.
- Accent color should guide action, not flood the screen.

### Motion and Feedback

- Motion should explain hierarchy or state change.
- Haptics should reinforce important actions, not decorate every tap.
- Respect reduced motion.

### Touch and Reachability

- Make primary actions easy to reach.
- Avoid fragile gestures near system edges.
- Keep destructive actions explicit and recoverable where possible.

### Accessibility

- Design for Dynamic Type early.
- Preserve contrast in light and dark appearances.
- Ensure VoiceOver labels and reading order make sense.
- Expect longer localized strings and larger accessibility sizes.

## Codex / GPT Execution Rules

- Read the local app structure before introducing new patterns.
- Preserve the app's identity where it is strong, but normalize weak custom UI back toward native behavior.
- If the user gives screenshots, use them as visual truth while correcting anti-native patterns.
- If no screenshots exist, create a short design brief before wide implementation.
- Prefer complete, runnable SwiftUI or native code over sketch fragments.
- Always account for light and dark mode.
- Default to system components first; customize second.
- Gate newer visual treatments by deployment target and API availability.

## Read When

- Need source rationale or further reading:
  [references/sources.md](references/sources.md)
- Need a design brief:
  [references/ios-design-brief-template.md](references/ios-design-brief-template.md)
- Need structural guidance:
  [references/native-patterns.md](references/native-patterns.md)
- Need prompt patterns:
  [references/prompt-recipes.md](references/prompt-recipes.md)
- Need QA criteria:
  [references/review-checklist.md](references/review-checklist.md)
- Need tooling or install help:
  [references/install-recipes.md](references/install-recipes.md)

## Output Expectations

For substantial iOS design work, leave behind:
- a named native direction
- explicit system choices
- realistic states
- accessible interactions
- deployment-aware visual decisions
- a brief note on what changed and why

Aim for deliberate, trustworthy, product-appropriate iOS UI that feels native at first touch.
