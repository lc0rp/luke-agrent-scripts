# Android UX Design Skill

This skill is for native Android UI/UX work inside Codex or GPT.

It is meant to help a non-designer get much better Android output by enforcing a stronger workflow:
- choose a direction
- freeze a small Android theme early
- build from Compose and Material 3 primitives
- review on real rendered screens
- verify adaptive layout, accessibility, and Android-native behavior

## What It Is Good At

- Android screens in Jetpack Compose
- Material 3 theme work
- settings, forms, feeds, dashboards, onboarding
- adaptive phone and tablet layouts
- redesign passes on generic or web-shaped Android UI
- screenshot-driven Android polish

## What It Is Not For

- mobile web
- iOS
- macOS
- pure brand identity work

## What To Ask For

Good requests:
- "Use `android-ux-design` to redesign this Compose dashboard so it feels native and data-dense."
- "Use `android-ux-design` and give me 3 Android-native directions before coding."
- "Use `android-ux-design` and freeze a Material 3 theme system before implementation."
- "Use `android-ux-design` and make this stop looking like a web app in an Android wrapper."
- "Use `android-ux-design` and do a screenshot-driven polish pass for phone and tablet."

Useful additions:
- screenshots
- target audience
- device scope
- brand constraints
- Compose vs Views constraints
- any navigation or architecture constraints

## Best Workflow For You

1. Give the model the Android feature or screen goal.
2. Ask for 2 or 3 directions first if the visual language is still open.
3. Ask it to pick one direction and freeze a small theme artifact.
4. Ask for implementation with realistic states and adaptive behavior.
5. Ask for a final critique pass against `references/review-checklist.md`.

If you have emulator screenshots, design mocks, or existing app screens, attach them. Screenshot-driven refinement is much better than abstract prompting.

## Recommended Ask Pattern

Use wording like:

```text
Use android-ux-design.
Goal: redesign this native Android screen for [audience].
Devices: [phone / tablet / foldable].
Tone: [tone].
Constraints: [Compose / Views / brand / performance / accessibility].
First, name 3 distinct Android-native design directions.
Then pick the strongest one, freeze a theme system, and implement it.
Avoid generic mobile UI and avoid web-shaped design.
Include realistic states, adaptive behavior, and a final critique pass.
```

## What The Skill Synthesizes

The skill combines official Android and Material guidance with a few high-signal general design resources and public workflow patterns. The main source map is in [references/sources.md](references/sources.md).

Core ideas it keeps:
- explicit direction beats vague taste
- Compose previews and screenshots beat text-only critique
- theme roles and tokens reduce visual drift
- Android navigation and adaptive layout are part of design, not cleanup
- accessibility, touch targets, and back behavior must be designed deliberately

## Further Reading

Start here:
- [references/sources.md](references/sources.md)
- [references/style-system-template.md](references/style-system-template.md)
- [references/prompt-recipes.md](references/prompt-recipes.md)
- [references/review-checklist.md](references/review-checklist.md)
- [references/install-recipes.md](references/install-recipes.md)

## Maintenance

If you want to improve the skill later, use [UPGRADING.md](UPGRADING.md).
