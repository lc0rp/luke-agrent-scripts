# Prompt Recipes

Use these patterns when the model needs stronger structure.

## 1. Native Structure First

```text
Use ios-ux-design.
This is a native iOS task.
Before coding, choose the correct native structure for this feature and explain the choice briefly.
Consider list, form, tab, navigation stack, search, sheet, and confirmation dialog patterns.
Then freeze the system choices and implement it in a way that feels unmistakably iOS.
Avoid web-like mobile UI patterns.
```

## 2. Screenshot-Driven Native Polish

```text
Use ios-ux-design.
Treat the attached screenshot as visual truth for the feature intent and information density.
Improve hierarchy, touch ergonomics, typography, symbols, states, and native feel.
Keep the core task flow intact.
Then do a critique pass against the review checklist.
```

## 3. SwiftUI-First Prototype

```text
Use ios-ux-design.
Prototype this feature in SwiftUI first.
Prefer NavigationStack, List, Form, Section, searchable, sheet, confirmationDialog, and system toolbars where appropriate.
Use semantic colors, SF Symbols, Dynamic Type, and dark mode support.
```

## 4. Anti-Web Correction Pass

```text
Use ios-ux-design.
Review this screen for web-style composition mistakes.
Replace custom chrome, KPI-card habits, decorative copy, and weak touch targets with stronger native patterns.
Do not redesign the product logic; fix the platform feel.
```

## 5. Accessibility Review

```text
Use ios-ux-design.
Audit this feature for Dynamic Type, VoiceOver clarity, touch targets, contrast, reduced motion, and localization resilience.
Patch the highest-leverage issues and summarize the changes.
```
