# iOS UX Design Skill

This skill is for native iOS product UI inside Codex or GPT.

It is designed to help a non-designer get much better iPhone UI output by forcing a stronger workflow:
- choose the right native pattern before styling
- freeze a small system early
- build from SwiftUI and system components
- iterate with screenshots and simulator output
- review hard for accessibility, touch ergonomics, and anti-web mistakes

## What It Is Good At

- iPhone-first app screens
- onboarding
- settings
- forms and lists
- navigation and search flows
- redesign passes on weak or web-like iOS UI
- screenshot-to-native polish
- SwiftUI-first prototyping

## What It Is Not For

- Android UI
- macOS UI
- mobile web
- brand identity outside the app

## What To Ask For

Good requests:
- "Use `ios-ux-design` to redesign this onboarding flow so it feels unmistakably native."
- "Use `ios-ux-design` and decide whether this should be a list, form, or sheet flow before coding."
- "Use `ios-ux-design` and do a screenshot-driven native polish pass."
- "Use `ios-ux-design` and fix the web-like patterns in this SwiftUI screen."
- "Use `ios-ux-design` and review this feature for Dynamic Type, VoiceOver, and touch targets."

Useful additions:
- target user
- screenshots
- target iOS version
- SwiftUI vs UIKit constraints
- existing brand constraints
- whether iPad support matters

## Best Workflow For You

1. Give the model the feature goal and user context.
2. Ask it to choose the native pattern before styling.
3. Ask for a short iOS design brief.
4. Ask for implementation using system components and realistic states.
5. Ask for a final review against `references/review-checklist.md`.

If you have screenshots, attach them. Screenshot-driven refinement is much better than text-only refinement for native feel.

## Recommended Ask Pattern

Use wording like:

```text
Use ios-ux-design.
Goal: design or refine this iOS feature for [audience].
Context: [where/when the feature is used].
Constraints: [SwiftUI/UIKit, existing patterns, deployment target, brand].
First, choose the correct native structure and explain it briefly.
Then freeze the system choices, implement it, and keep it unmistakably iOS.
Avoid web-like UI patterns.
Include Dynamic Type, dark mode, states, and a final critique pass.
```

## What The Skill Synthesizes

The skill combines Apple-native guidance, public SwiftUI agent skills, and cross-platform prompting lessons that transfer well to iOS. The source map is in [references/sources.md](references/sources.md).

Core ideas it keeps:
- structure first
- screenshots and simulator loops beat text-only guessing
- system components and semantic tokens reduce drift
- accessibility must be part of the design pass
- stronger native guardrails matter more than more adjectives

## Further Reading

Start here:
- [references/sources.md](references/sources.md)
- [references/native-patterns.md](references/native-patterns.md)
- [references/ios-design-brief-template.md](references/ios-design-brief-template.md)
- [references/prompt-recipes.md](references/prompt-recipes.md)
- [references/review-checklist.md](references/review-checklist.md)
- [references/install-recipes.md](references/install-recipes.md)

## Maintenance

If you want to improve the skill later, use [UPGRADING.md](UPGRADING.md).
