# Native Patterns

Use this when the right iOS structure is unclear.

## Choose The Shell First

Use:
- `TabView` for 2-5 top-level destinations of similar importance
- `NavigationStack` for drill-down flows
- `List` for browseable or dense collections
- `Form` for settings, preferences, and grouped inputs
- `sheet` for focused, dismissible tasks
- `fullScreenCover` for immersive or clearly separate flows
- `searchable` when search is a real product action, not decoration

Avoid custom shells unless the product truly needs them.

## Lists Beat Card Mazes

On iPhone, lists are often better than:
- card grids
- multi-column dashboards
- floating panels
- over-segmented screens

If the task is scan, compare, choose, or manage, start with a list.

## Forms Should Feel Native

For settings or structured inputs:
- use `Form`
- group related controls into `Section`
- keep labels literal
- use inline help sparingly
- put destructive actions in clear, separate positions

## Navigation

- Keep top-level navigation shallow.
- Avoid hiding important destinations behind multiple taps.
- Use large titles when they improve orientation, not everywhere.
- Toolbars should contain real actions, not decorative clutter.

## Sheets And Confirmation

Use sheets for:
- focused subtasks
- creation flows
- edits that can be dismissed cleanly

Use confirmation dialogs for:
- destructive actions
- branching decisions
- choices that should stay lightweight

Do not replace every second screen with a sheet.

## Search

Use search when:
- users genuinely need to find items fast
- list size or complexity justifies it
- it can replace excessive navigation depth

Do not add search solely because it looks advanced.

## Visual System

- Prefer semantic colors.
- Use San Francisco text styles.
- Use SF Symbols when meaning exists.
- Keep radius, shadow, and materials restrained.
- Let content lead; chrome should support it.

## Touch And Reachability

- Keep primary actions easy to reach.
- Respect 44x44pt minimum touch targets.
- Be careful near system gesture edges.
- Swipe actions are useful, but discoverability still matters.

## Anti-Web Guardrails

Avoid:
- dashboard KPI tiles as the default composition
- decorative hero sections in app screens
- custom segmented nav bars that mimic websites
- floating card stacks everywhere
- marketing copy inside functional flows
- tiny dense controls with weak touch targets

## When In Doubt

Choose the simpler native pattern:
- list over card maze
- form over custom settings layout
- sheet over complex overlay invention
- system toolbar over bespoke chrome
