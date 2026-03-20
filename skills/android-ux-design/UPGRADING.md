# Upgrading The Skill

This guide is for both humans and LLMs.

Use it when the skill feels stale, too verbose, too generic, or behind current Android UI practice.

## Upgrade Goals

Preserve:
- concise trigger metadata
- Android-native platform fit
- strong anti-generic guidance
- non-designer friendliness
- Compose-first practical advice

Improve:
- source freshness
- adaptive and large-screen guidance
- theme and token guidance
- prompt recipes
- accessibility and system-behavior coverage

## When To Upgrade

Upgrade when:
- Android or Material guidance shifts
- Compose UI patterns materially change
- better public Android UI/UX skills appear
- the skill starts generating web-shaped Android screens
- the recommended stack or APIs get stale

## Upgrade Procedure

1. Re-read `SKILL.md` and keep it lean.
2. Re-verify the source list in `references/sources.md`.
3. Prefer official Android, Material, and primary-source repos.
4. Add only sources that materially improve results.
5. Move detail into `references/` rather than bloating `SKILL.md`.
6. Re-test the skill on realistic Android prompts.

## Research Standard

Favor this order:
1. official Android Developers docs
2. official Material docs and tools
3. official Android or Google sample repos
4. strong public skills and prompt packs
5. forums only as supporting signal

Avoid stale XML-era advice unless the target app is Views-based.

## Source Selection Rules

Keep the "top 10" curated, not exhaustive.

A source should stay only if it materially improves:
- Android platform fit
- Compose theming and tokens
- adaptive layouts
- accessibility and touch ergonomics
- screenshot and preview-driven iteration
- anti-generic taste

Remove sources that duplicate stronger ones.

## File Responsibilities

- `SKILL.md`: operating instructions for Codex/GPT
- `README.md`: user-facing usage guidance
- `UPGRADING.md`: maintenance workflow
- `references/sources.md`: curated source map
- `references/style-system-template.md`: reusable Android theme artifact
- `references/prompt-recipes.md`: structured prompt patterns
- `references/review-checklist.md`: QA checklist
- `references/install-recipes.md`: stack notes

## Quality Bar For Changes

The upgraded skill should make these more likely:
- stronger Android-native navigation and hierarchy
- less web-shaped mobile UI
- better adaptive behavior on larger screens
- better theming discipline
- better focus, touch, and accessibility handling
- more believable real-product Android surfaces

## Validation Prompts

Test the skill on prompts like:
- redesign a cluttered Android settings flow
- build a polished Compose dashboard for phone and tablet
- convert a rough mock or screenshot into a native Android screen
- create an onboarding flow that feels Android-native instead of generic mobile UI

Check whether the output:
- names a direction
- freezes theme roles early
- respects Android navigation and back behavior
- handles adaptive layouts and accessibility
- feels like a real Android product

## Editing Rules

- Keep `SKILL.md` concise.
- Prefer sharper rules over more rules.
- Replace stale links.
- Date major source refreshes in `references/sources.md`.

## Optional Future Additions

Only add these if they prove useful:
- a preview screenshot critique helper
- stack-specific references for Compose-only, hybrid, and Views-based apps
- example before/after screenshot sets with clean licensing
