# Sources

Last reviewed: 2026-03-20

This skill synthesizes the sources below into one Android-native workflow for non-designers and developers.

## Top 10 Core Sources

1. [Android Developers: Mobile app design](https://developer.android.com/design/ui/mobile)
   Why it matters: the best top-level map for Android-native UI principles, Figma kits, theme builder entry points, and platform expectations.

2. [Android Developers: Material Design 3 in Compose](https://developer.android.com/develop/ui/compose/designsystems/material3)
   Why it matters: the clearest official bridge from Android theming concepts to real Compose implementation.

3. [Android Developers: Design systems in Compose](https://developer.android.com/develop/ui/compose/designsystems)
   Why it matters: explains how to structure theme, tokens, and design-system layers in Compose.

4. [Android Developers: Themes](https://developer.android.com/design/ui/mobile/guides/styles/themes)
   Why it matters: clarifies color, typography, shape, and role-based theming for Android surfaces.

5. [Material Theme Builder](https://material-foundation.github.io/material-theme-builder/)
   Why it matters: a practical non-designer tool for freezing a token system instead of hand-waving about taste.

6. [Android Developers: Compose previews](https://developer.android.com/develop/ui/compose/tooling/previews)
   Why it matters: preview-driven iteration is one of the fastest ways to improve Android UI quality.

7. [Android Developers: Accessibility API defaults in Compose](https://developer.android.com/develop/ui/compose/accessibility/api-defaults)
   Why it matters: keeps accessible behavior inside the implementation workflow instead of bolted on at the end.

8. [Android Developers: Build adaptive UIs](https://developer.android.com/develop/ui/compose/layouts/adaptive/build-adaptive-app)
   Why it matters: stops phone-only thinking and helps the skill produce better tablet and foldable layouts.

9. [Refactoring UI](https://refactoringui.com/)
   Why it matters: still one of the best practical design resources for developers and non-designers.

10. [Laws of UX](https://lawsofux.com/)
    Why it matters: converts cleanly into prompt constraints and design review heuristics.

## Supporting Sources

- [Android Developers: Adaptive navigation](https://developer.android.com/develop/ui/compose/layouts/adaptive/build-adaptive-navigation)
  Useful for deciding when bottom bars, rails, and drawers should change across device sizes.

- [Android Developers: System bars](https://developer.android.com/design/ui/mobile/guides/foundations/system-bars)
  Useful for edge-to-edge design, insets, and Android-specific screen polish.

- [Android Developers: Predictive back](https://developer.android.com/design/ui/mobile/guides/patterns/predictive-back)
  Useful for navigation behavior that feels modern and platform-correct.

- [Android Developers: UI kits](https://developer.android.com/design/ui/mobile/guides/get-started/ui-kit)
  Useful for non-designers who need a Figma starting point.

- [Android Compose samples](https://github.com/android/compose-samples)
  Useful for seeing how official samples structure Compose UI, screens, and patterns.

- [Now in Android](https://github.com/android/nowinandroid)
  Useful for large-scale Compose app structure, theming, and Android design choices in a real project.

- [Anthropic `frontend-design` skill](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md)
  Useful as a general anti-generic design discipline source, even though it is web-first.

- [OpenAI Cookbook: Frontend coding with GPT-5](https://cookbook.openai.com/examples/gpt-5/gpt-5_frontend)
  Useful for image-driven iteration and stronger multimodal critique loops.

- [OpenAI Developers Blog: Building frontend UIs with Codex and Figma](https://developers.openai.com/blog/building-frontend-uis-with-codex-and-figma)
  Useful for design-to-code workflows and visual-context iteration that transfer well to Android.

## Forum Signal

Forum and community discussion is weaker than the official Android material, but the recurring pattern is still useful:
- screenshots and previews improve results faster than text-only iteration
- a frozen theme system reduces generic-looking output
- phone-only layouts feel amateurish when a product clearly needs large-screen handling

## What The Skill Kept

From these sources, the skill keeps:
- explicit direction selection
- theme and token discipline
- preview and screenshot-driven refinement
- adaptive layout strategy
- Android-native navigation and system behavior
- anti-generic design safeguards

## What The Skill Excluded

The skill intentionally excludes:
- iOS-specific guidance
- generic cross-platform abstractions that erase Android behavior
- stale Views-only advice unless the target app clearly needs it
- broad listicle summaries
