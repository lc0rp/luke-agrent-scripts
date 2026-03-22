---
name: frontend-redesign-audit
description: Audit and upgrade an existing web UI without rewriting the stack. Use this skill for redesign passes on websites, dashboards, web apps, settings screens, or landing pages that already exist but feel generic, unfinished, inconsistent, or weak. It emphasizes scan-first diagnosis, preserving the current tech stack, fixing the highest-leverage visual and UX issues first, and shipping focused improvements without breaking functionality.
---

# Frontend Redesign Audit

Use this skill when the task is to improve an existing browser-based UI rather than invent a new one.

Goal:
- diagnose what feels generic, weak, inconsistent, or unfinished
- improve the UI using the existing stack
- keep changes focused and reviewable

## Sequence

1. Scan
- identify the framework and styling system
- identify the existing design language
- identify the page type: landing page, app surface, dashboard, settings, marketing section

2. Diagnose
- list the highest-leverage problems first
- focus on hierarchy, spacing, typography, surfaces, states, responsiveness, and omissions
- separate visual problems from structural or content problems

3. Fix
- preserve functionality
- work with the existing stack
- patch the most valuable issues first
- avoid broad rewrites unless explicitly requested

## Audit Priorities

Check these in order:

1. Typography
- generic or weak font choice
- poor headline presence
- over-wide body copy
- weak weight hierarchy
- numbers not optimized for data scan speed

2. Color and surfaces
- too many accent colors
- purple-blue AI gradient fingerprints
- generic shadows
- flat, textureless sections when the product needs more presence
- inconsistent light or surface treatment

3. Layout
- generic three-card grids
- everything centered and symmetrical without purpose
- missing max-width or poor containment
- awkward spacing rhythm
- overuse of card treatment
- mobile viewport issues from naive `100vh`

4. States and interaction
- missing hover, active, focus, loading, empty, or error states
- dead links and fake buttons
- no current-page indication in nav
- abrupt or ornamental animation

5. Content realism
- fake round numbers
- filler copy
- generic AI wording
- placeholder names or brands

6. Strategic omissions
- missing legal links when needed
- missing back path where flows dead-end
- missing form validation
- missing skip link when page structure warrants it

## Fix Rules

- Do not migrate frameworks or styling libraries unless explicitly requested.
- Check the dependency file before importing anything new.
- Prefer CSS Grid over fragile percentage-based flex layouts.
- Use semantic HTML where it improves structure and accessibility.
- Use `100dvh`-style viewport handling where mobile browser chrome matters.
- Keep changes reviewable and focused.

## Upgrade Techniques

Use selectively:
- stronger type hierarchy
- cleaner container logic
- fewer accent colors
- better hover and active states
- better empty and loading states
- card removal where plain layout works better
- subtle noise, texture, or imagery where the design feels sterile
- optical alignment improvements for icons, labels, and buttons

## Output

Leave behind:
- a short diagnosis
- the prioritized fixes you applied
- any remaining high-value issues not yet addressed

The redesign should feel intentional and stronger without looking like a rewrite from another product.
