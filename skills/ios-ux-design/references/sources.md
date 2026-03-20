# Sources

Last reviewed: 2026-03-20

This skill synthesizes Apple-native guidance, public iOS agent skills, and a few transferable cross-platform workflow lessons.

## Top 10 Core Sources

1. [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
   Why it matters: canonical source for native structure, behavior, controls, and visual expectations.

2. [Apple Design Resources](https://developer.apple.com/design/resources/)
   Why it matters: practical system assets, templates, and platform-aligned visual resources.

3. [Apple SF Symbols](https://developer.apple.com/sf-symbols/)
   Why it matters: native iconography, semantic meaning, and visual consistency.

4. [Apple SwiftUI Documentation](https://developer.apple.com/documentation/swiftui)
   Why it matters: official surface area for native implementation patterns and modern UI APIs.

5. [Apple Accessibility](https://developer.apple.com/accessibility/)
   Why it matters: accessibility needs to be designed in from the start, not retrofitted.

6. [Apple Design Awards](https://developer.apple.com/design/awards/)
   Why it matters: useful inspiration for what polished, product-specific native quality looks like.

7. [twostraws/SwiftUI-Agent-Skill](https://github.com/twostraws/SwiftUI-Agent-Skill)
   Why it matters: strong public agent-skill guidance targeting common LLM SwiftUI mistakes, including design, performance, and accessibility.

8. [AvdLee/SwiftUI-Agent-Skill](https://github.com/AvdLee/SwiftUI-Agent-Skill)
   Why it matters: practical SwiftUI best-practice guardrails for AI coding tools.

9. [PasqualeVittoriosi/swift-accessibility-skill](https://github.com/PasqualeVittoriosi/swift-accessibility-skill)
   Why it matters: strong accessibility-specific checks across SwiftUI, UIKit, and AppKit.

10. [conorluddy/ios-simulator-skill](https://github.com/conorluddy/ios-simulator-skill)
    Why it matters: pushes models toward simulator and screenshot loops instead of blind code-only iteration.

## Transferable Sources Kept From The Web Research

- [OpenAI Cookbook: Frontend coding with GPT-5](https://cookbook.openai.com/examples/gpt-5/gpt-5_frontend)
  Useful because the screenshot and multimodal workflow transfers cleanly to iOS UI iteration.

- [OpenAI Developers Blog: Building frontend UIs with Codex and Figma](https://developers.openai.com/blog/building-frontend-uis-with-codex-and-figma)
  Useful for design-to-code workflows inside Codex.

- [Refactoring UI](https://refactoringui.com/)
  Useful for hierarchy, spacing, and visual discipline, as long as its web bias does not override native iOS patterns.

- [Laws of UX](https://lawsofux.com/)
  Useful for prompt constraints and review heuristics.

## Forum Signal

Forum and community signal was consistent on three points:
- models do better when you lock the native structure before styling
- screenshot and simulator feedback loops beat text-only prompting
- public SwiftUI agent skills are increasingly used as guardrails for Codex, Claude, Gemini, and related tools

Useful community references:
- [r/iOSProgramming: Those of you using AI to assist with development, what is your current setup?](https://www.reddit.com/r/iOSProgramming/comments/1rrvq9k/those_of_you_using_ai_to_assist_with_development/)
- [r/SwiftUI: 23 agent skills for iOS 26 development](https://www.reddit.com/r/SwiftUI/comments/1rnf25c/23_agent_skills_for_ios_26_development_swiftui/)

## What The Skill Kept

From these sources, the skill keeps:
- native structure-first thinking
- system components over invented chrome
- screenshot and simulator iteration
- accessibility and Dynamic Type as first-class design inputs
- explicit anti-web guardrails

## What The Skill Excluded

The skill intentionally excludes:
- Android rules
- desktop macOS patterns
- generic mobile-web advice
- prompt dumps without strong platform knowledge
