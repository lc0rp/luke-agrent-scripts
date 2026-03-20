# Install Recipes

Use these on the fly when the Android project needs a stronger modern UI foundation.

Verify the existing Gradle setup and version catalog before adding dependencies.

## Modern Compose UI Stack

Strong default building blocks:
- Compose BOM
- Material 3
- Navigation Compose
- UI tooling previews
- Window size / adaptive helpers

Typical dependency shape:

```kotlin
implementation(platform(libs.androidx.compose.bom))
implementation("androidx.compose.material3:material3")
implementation("androidx.navigation:navigation-compose")
implementation("androidx.compose.ui:ui-tooling-preview")
debugImplementation("androidx.compose.ui:ui-tooling")
```

For adaptive navigation and larger devices:

```kotlin
implementation("androidx.compose.material3:material3-adaptive-navigation-suite")
```

For window-aware behavior:

```kotlin
implementation("androidx.window:window")
```

Use the current stable versions already adopted by the project when possible.

## Theme Work

If the team has no clear token system yet:
- start with [Material Theme Builder](https://material-foundation.github.io/material-theme-builder/)
- export a minimal token set
- map it into the app theme before heavy screen work

## Preview-Driven Design

Enable Compose previews and use them aggressively.

Good practice:
- one default preview
- one dark theme preview
- one font-scale or accessibility preview
- one large-screen preview when relevant

## Emulator Screenshot Review

When visual polish matters:
- run the screen in an emulator
- capture screenshots
- critique spacing, density, touch targets, and system-bar fit from the rendered UI

## When Not To Install More

Do not add a new UI stack if the project already has:
- stable theme roles
- reusable components
- acceptable navigation scaffolding

In that case, extend the current system instead of replacing it.
