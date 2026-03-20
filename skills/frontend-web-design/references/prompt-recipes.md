# Prompt Recipes

Use these patterns when the model needs stronger structure.

## 1. Direction First

```text
Use frontend-web-design.
This is a browser-based UI task.
Before coding, generate 3 clearly distinct visual directions for this screen.
Name each direction, describe its tone, information density, typography approach, and layout logic.
Pick the strongest one for the product and explain the choice in 4 bullets max.
Then freeze a token system and implement it.
Avoid generic AI UI patterns.
```

## 2. Screenshot-Driven Polish

```text
Use frontend-web-design.
Treat the attached screenshot as visual truth for layout intent and content density.
Improve hierarchy, spacing, alignment, typography, states, and responsiveness.
Keep the product structure intact.
Do not redesign for style alone.
Then do a critique pass against the review checklist.
```

## 3. Strong Redesign

```text
Use frontend-web-design.
Redesign this web interface so it feels deliberate and product-specific.
Pick one bold but credible direction.
Freeze colors, typography, spacing, radius, shadow, and motion before implementation.
Build with real components and realistic states.
No fake charts, no filler cards, no decorative copy, no generic AI SaaS look.
```

## 4. Existing Design System Respect

```text
Use frontend-web-design.
Read the existing codebase and preserve the current product language where it is strong.
Improve the weak parts without introducing a second design language.
Prefer extending existing tokens and components over replacing everything.
```

## 5. Final Critique Pass

```text
Use frontend-web-design.
Do not make large architectural changes.
Critique the current implementation for hierarchy, consistency, responsiveness, accessibility, states, realism, and generic AI patterns.
Patch the highest-leverage issues and summarize the changes.
```
