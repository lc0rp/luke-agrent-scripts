# Upgrading The Skill

This guide is for both humans and LLMs.

Use it when the skill starts feeling stale, too verbose, too generic, or misaligned with current web UI practice.

## Upgrade Goals

Preserve:

- concise trigger metadata
- strong anti-generic guidance
- web-only scope
- practical, implementation-friendly advice

Improve:

- current source quality
- stack recommendations
- prompt recipes
- accessibility and responsive guidance
- visual QA workflow

## When To Upgrade

Upgrade when:

- official OpenAI, v0, or shadcn guidance changes
- better public frontend design skills appear
- the skill starts producing repetitive aesthetics
- the recommended stack is outdated
- the reference pack grows noisy or redundant

## Upgrade Procedure

1. Re-read `SKILL.md` and keep it lean.
2. Re-verify the source list in `references/sources.md`.
3. Prefer official and primary sources over summaries.
4. Add only sources that materially improve outcomes.
5. Fold repeated advice into one stronger rule.
6. Move detail into `references/` instead of bloating `SKILL.md`.
7. Re-run a sanity check on a few realistic prompts.

## Research Standard

Favor this order:

1. official docs
2. primary-source public skills or repos
3. strong design primers for non-designers
4. forum threads only as supporting evidence

Avoid adding weak listicles, SEO filler, or untested prompt libraries.

## Source Selection Rules

Keep the "top 10" curated, not exhaustive.

A source should stay only if it meaningfully strengthens at least one of:

- visual direction
- design-system discipline
- screenshot-driven iteration
- accessibility and responsive rigor
- anti-generic taste
- implementation realism

Remove sources that duplicate stronger ones.

## File Responsibilities

- `SKILL.md`: operating instructions for Codex/GPT; keep concise
- `README.md`: user-facing usage guidance
- `UPGRADING.md`: maintenance and research workflow
- `references/sources.md`: curated source map
- `references/style-system-template.md`: reusable artifact template
- `references/prompt-recipes.md`: practical prompt patterns
- `references/review-checklist.md`: QA checklist
- `references/install-recipes.md`: install and stack notes

## Quality Bar For Changes

The upgraded skill should make these more likely:

- clearer design direction
- less generic layout and styling
- fewer fake dashboard patterns
- better responsive behavior
- better focus and keyboard states
- more believable real-product UI

## Validation Prompts

Test the skill on prompts like:

- redesign a cluttered B2B dashboard
- build a polished settings page from scratch
- convert a rough screenshot into a real web screen
- create a landing page without drifting into generic startup visuals

Check whether the output:

- names a direction
- freezes tokens early
- avoids template AI tropes
- handles mobile and states
- feels product-specific

## Editing Rules

- Keep `SKILL.md` under control; do not turn it into a book.
- Prefer sharper rules over more rules.
- Keep references one level deep.
- Replace stale links.
- Date major updates at the top of `references/sources.md`.

## Optional Future Additions

Only add these if they prove useful:

- a browser screenshot critique script
- a small token scaffolder
- stack-specific sub-references for Next.js, plain HTML/CSS, and React
- example before/after screenshots if licensing is clean
