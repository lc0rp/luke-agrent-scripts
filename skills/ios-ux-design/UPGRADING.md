# Upgrading The Skill

This guide is for both humans and LLMs.

Use it when the skill starts feeling stale, too generic, too web-like, or behind current iOS guidance.

## Upgrade Goals

Preserve:
- concise trigger metadata
- hard native guardrails
- iOS-first scope
- practical implementation guidance

Improve:
- current Apple source quality
- SwiftUI and simulator workflow guidance
- accessibility and localization coverage
- prompt recipes
- review discipline

## When To Upgrade

Upgrade when:
- Apple HIG or design resources materially change
- SwiftUI patterns shift
- the skill starts producing web-like mobile UI
- newer public iOS agent skills expose better guardrails
- deployment targets or platform conventions change

## Upgrade Procedure

1. Re-read `SKILL.md` and keep it lean.
2. Re-verify the source map in `references/sources.md`.
3. Prefer Apple primary sources over summaries.
4. Add public skills only if they materially improve native results.
5. Push detail into `references/` rather than bloating `SKILL.md`.
6. Re-test on realistic iOS prompts and screenshot-driven tasks.

## Research Standard

Favor this order:
1. Apple primary sources
2. official SwiftUI and accessibility docs
3. strong public iOS agent skills
4. forums only as supporting signal
5. transferable cross-platform sources only when they improve the iOS workflow

Avoid adding weak prompt dumps, SEO listicles, or web-first advice that breaks native feel.

## File Responsibilities

- `SKILL.md`: operating instructions for Codex/GPT
- `README.md`: user-facing usage guidance
- `UPGRADING.md`: maintenance workflow
- `references/sources.md`: curated source map
- `references/native-patterns.md`: structural guidance
- `references/ios-design-brief-template.md`: reusable artifact template
- `references/prompt-recipes.md`: practical prompt patterns
- `references/review-checklist.md`: QA checklist
- `references/install-recipes.md`: tooling and install notes

## Quality Bar For Changes

The upgraded skill should make these more likely:
- clearer native structure
- less web-like composition
- better touch ergonomics
- better Dynamic Type and VoiceOver outcomes
- more believable SwiftUI output
- stronger dark-mode and state coverage

## Validation Prompts

Test the skill on prompts like:
- redesign a cluttered SwiftUI settings flow
- convert a web-like mobile screen into a native iPhone flow
- build a polished list-driven feature from scratch
- refine an onboarding flow from screenshots
- review a screen for Dynamic Type, VoiceOver, and native affordances

Check whether the output:
- chooses the right container
- uses system components appropriately
- avoids web dashboard habits
- handles states and accessibility
- feels like iOS at first glance

## Optional Future Additions

Only add these if they prove useful:
- simulator screenshot critique scripts
- stack-specific notes for SwiftUI vs UIKit
- richer localization and content-sizing examples
- before/after assets if licensing is clean
