# Frontend Web Design Skill

This skill is for browser-based UI work inside Codex or GPT.

It is designed to help a non-designer get much better frontend output by forcing a stronger workflow:

- pick a visual direction
- freeze a small design system early
- build on real primitives
- iterate from screenshots when possible
- review aggressively for hierarchy, responsiveness, and accessibility

## What It Is Good At

- web apps
- landing pages
- dashboards
- settings screens
- marketing pages
- component polish
- redesign passes on weak or generic UI
- turning screenshots or rough ideas into better web UI

## What It Is Not For

- native iOS design
- native Android design
- native macOS design
- logo systems or full brand identity work

## What To Ask For

Good requests:

- "Use `frontend-web-design` to redesign this dashboard so it feels editorial and data-dense."
- "Use `frontend-web-design` and give me 3 distinct directions before coding."
- "Use `frontend-web-design` and freeze a token system before implementation."
- "Use `frontend-web-design` and do a screenshot-driven polish pass."
- "Use `frontend-web-design` and make this stop looking like generic AI UI."

Useful additions:

- target audience
- product tone
- screenshots
- competitor references
- constraints on stack, fonts, brand colors, or performance

## Best Workflow For You

1. Give the model the page or feature goal.
2. Ask for 2 or 3 directions first if the visual language is still open.
3. Ask it to choose one direction and write a short style system artifact.
4. Ask for implementation with explicit tokens, states, and responsive behavior.
5. Ask for a final review pass against the checklist in `references/review-checklist.md`.

If you have screenshots, attach them. Screenshot-driven refinement is usually much better than text-only refinement.

## Recommended Ask Pattern

Use wording like:

```text
Use frontend-web-design.
Goal: redesign this web screen for [audience].
Tone: [tone].
Constraints: [stack / colors / existing components / performance limits].
First, name 3 distinct visual directions.
Then pick the strongest one, freeze a design system, and implement it.
Avoid generic AI UI.
Include realistic states, mobile behavior, and a final critique pass.
```

## What The Skill Synthesizes

The skill is built from a curated set of official docs, public skills, and design primers. The main sources are listed in [references/sources.md](references/sources.md).

Core ideas it borrows:

- explicit visual direction beats vague taste
- screenshots beat text-only prompting for visual polish
- design tokens and real component systems reduce drift
- stronger defaults matter more than more adjectives
- accessibility and responsiveness must be part of the design pass, not added later

## Further Reading

Start here:

- [references/sources.md](references/sources.md)
- [references/style-system-template.md](references/style-system-template.md)
- [references/prompt-recipes.md](references/prompt-recipes.md)
- [references/review-checklist.md](references/review-checklist.md)
- [references/install-recipes.md](references/install-recipes.md)

## Maintenance

If you want to improve the skill later, use [UPGRADING.md](UPGRADING.md).
