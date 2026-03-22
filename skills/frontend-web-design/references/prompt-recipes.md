# Prompt Recipes

Use these patterns when the model needs stronger structure.

## 1. Direction First

```text
Use frontend-web-design.
This is a browser-based UI task.
Start at low reasoning unless complexity clearly requires medium.
Before coding, generate 3 clearly distinct visual directions or a quick mood board for this screen.
Name each direction, describe its tone, information density, typography approach, layout logic, and imagery style.
Pick the strongest one for the product and explain the choice in 4 bullets max.
Then write a visual thesis, content plan, and interaction thesis.
Then freeze a token system and implement it.
Avoid generic AI UI patterns.
```

## 2. Screenshot Or Mood-Board Polish

```text
Use frontend-web-design.
Treat the attached screenshot as visual truth for layout intent and content density.
Improve hierarchy, spacing, alignment, typography, states, and responsiveness.
Keep the product structure intact.
Do not redesign for style alone.
Check that the first viewport reads as one composition.
Then do a critique pass against the review checklist.
```

## 3. Existing UI Redesign Audit

```text
Use frontend-web-design.
This is an upgrade of an existing interface, not a rewrite.
Work with the existing stack.
Audit the UI first for generic patterns, weak hierarchy, bad spacing, placeholder states, accessibility gaps, and unfinished details.
Then fix the highest-leverage issues in priority order.
Do not migrate frameworks or add libraries unless there is a clear need.
```

## 4. Landing Page Narrative

```text
Use frontend-web-design.
This is a branded landing page.
Treat the first viewport as a poster, not a document.
Keep the brand or product name at hero strength.
Use one dominant full-bleed visual plane.
Structure the page as: hero, support, detail, proof if needed, final CTA.
No hero cards, stat strips, logo clouds, pill soup, or promo overlays by default.
Freeze colors, typography, spacing, shadow, and motion before implementation.
```

## 5. App Surface Restraint

```text
Use frontend-web-design.
This is a product UI, not a marketing page.
Default to restrained, calm layout with strong typography, few colors, dense but readable information, and minimal chrome.
Organize around the primary workspace, navigation, and secondary context.
Cards only when the card itself is the interaction.
Avoid dashboard-card mosaics, decorative gradients, and marketing copy inside utility screens.
```

## 6. Existing Design System Respect

```text
Use frontend-web-design.
Read the existing codebase and preserve the current product language where it is strong.
Improve the weak parts without introducing a second design language.
Prefer extending existing tokens and components over replacing everything.
```

## 7. Final Critique Pass

```text
Use frontend-web-design.
Do not make large architectural changes.
Critique the current implementation for composition, first-screen hierarchy, branding strength, consistency, responsiveness, accessibility, states, realism, and generic AI patterns.
Patch the highest-leverage issues and summarize the changes.
```
