# Prompt Recipes

Use these patterns when the model needs stronger structure.

## 1. Direction First

```text
Use android-ux-design.
This is a native Android task.
Before coding, generate 3 clearly distinct Android-native design directions for this screen.
Name each direction, describe its tone, hierarchy, Material 3 treatment, navigation logic, and density.
Pick the strongest one for the product and explain the choice in 4 bullets max.
Then freeze a theme system and implement it.
Avoid generic mobile UI and avoid web-shaped design.
```

## 2. Screenshot-Driven Polish

```text
Use android-ux-design.
Treat the attached screenshot as visual truth for layout intent, content density, and task structure.
Improve hierarchy, spacing, touch affordance, typography, states, Android navigation patterns, and adaptive behavior.
Keep the product structure intact.
Then do a critique pass against the review checklist.
```

## 3. Strong Android Redesign

```text
Use android-ux-design.
Redesign this Android screen so it feels deliberate, Android-native, and product-specific.
Pick one strong direction.
Freeze theme roles, typography, spacing, shape, navigation model, and motion before implementation.
Build with real Compose and Material 3 primitives and realistic states.
No web-shaped layouts, no filler cards, no fake metrics, and no generic Material-by-numbers UI.
```

## 4. Existing App Respect

```text
Use android-ux-design.
Read the existing Android codebase and preserve the product language where it is strong.
Improve the weak or generic areas without introducing a second design language.
Prefer extending existing theme roles and components over replacing everything.
```

## 5. Final Critique Pass

```text
Use android-ux-design.
Do not make large architectural changes.
Critique the current implementation for hierarchy, Android platform fit, navigation, back behavior, adaptive layout, accessibility, realism, and generic mobile patterns.
Patch the highest-leverage issues and summarize the changes.
```
