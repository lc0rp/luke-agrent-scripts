# Install Recipes

Use these on the fly when the project needs stronger iOS-native design and review tooling.

## Core Tools

Install or confirm:
- Xcode
- iOS Simulator
- SF Symbols app

Official downloads:
- [Xcode](https://developer.apple.com/xcode/)
- [SF Symbols](https://developer.apple.com/sf-symbols/)

## Optional Agent Skills

These are useful complements to `ios-ux-design`:

- [twostraws/SwiftUI-Agent-Skill](https://github.com/twostraws/SwiftUI-Agent-Skill)
- [AvdLee/SwiftUI-Agent-Skill](https://github.com/AvdLee/SwiftUI-Agent-Skill)
- [PasqualeVittoriosi/swift-accessibility-skill](https://github.com/PasqualeVittoriosi/swift-accessibility-skill)
- [conorluddy/ios-simulator-skill](https://github.com/conorluddy/ios-simulator-skill)

Typical install shape from those repos:

```bash
npx skills add https://github.com/OWNER/REPO --skill SKILL_NAME
```

Always read the current repo instructions before running install commands.

## Recommended Validation Loop

1. Build the screen in SwiftUI or the existing native stack.
2. Use previews for quick iteration.
3. Run in Simulator for actual interaction checks.
4. Capture screenshots.
5. Run a critique pass against `review-checklist.md`.

## When Not To Add More Tooling

Do not add extra packages or skills just to polish a small screen if the project already has:
- stable native components
- a working design system
- simulator access
- accessibility checks in place

In that case, use the current app structure and keep the change local.
