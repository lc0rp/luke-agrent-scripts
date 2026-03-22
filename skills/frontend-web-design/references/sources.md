# Sources

Last reviewed: 2026-03-21

This skill synthesizes the sources below into one web-only workflow.

## Top 10 Core Sources

1. [OpenAI: Designing delightful frontends with GPT-5.4](https://developers.openai.com/blog/designing-delightful-frontends-with-gpt-5-4)
   Why it matters: the strongest current OpenAI source for web UI generation; adds composition-first rules, low-reasoning guidance, mood-board workflows, narrative page structure, image-led hierarchy, and verification practices tailored to GPT-5.4.

2. [OpenAI `frontend-skill`](https://github.com/openai/skills/blob/main/skills/.curated/frontend-skill/SKILL.md)
   Why it matters: a concise official skill with stronger hard rules for landing pages, app restraint, hero composition, imagery, copy, and motion.

3. [Anthropic `frontend-design` skill](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md)
   Why it matters: strong anti-generic aesthetic guidance; pushes explicit visual direction and intentional detail.

4. [OpenAI Cookbook: Frontend coding with GPT-5](https://cookbook.openai.com/examples/gpt-5/gpt-5_frontend)
   Why it matters: strong multimodal frontend workflow; encourages image-aware design iteration and practical implementation.

5. [OpenAI Developers Blog: Building frontend UIs with Codex and Figma](https://developers.openai.com/blog/building-frontend-uis-with-codex-and-figma)
   Why it matters: strong guidance for design-to-code, screenshot or visual context, and realistic frontend workflows inside Codex.

6. [v0 Docs: Screenshots](https://v0.dev/docs/screenshots)
   Why it matters: makes the screenshot-first workflow explicit; very useful for non-designers.

7. [v0 Docs: Design Mode](https://v0.dev/docs/design-mode)
   Why it matters: separates generation from visual refinement; useful pattern even outside v0.

8. [shadcn/ui Theming](https://ui.shadcn.com/docs/theming)
   Why it matters: token discipline and CSS-variable-based theming; lowers drift and improves consistency.

9. [Refactoring UI](https://refactoringui.com/)
   Why it matters: still one of the best design resources for developers and non-designers working on product UI.

10. [Laws of UX](https://lawsofux.com/)
   Why it matters: fast, practical UX heuristics that convert well into prompt constraints and review criteria.

## Supporting Sources

- [web.dev: Design and UX for accessibility](https://web.dev/learn/accessibility/design-ux/)
  Useful for accessible spacing, contrast, focus, state clarity, and usable interaction design.

- [Leonxlnx `taste-skill`](https://github.com/Leonxlnx/taste-skill)
  Useful as a secondary source for audit heuristics, design tuning dials, and redesign-first workflows. Incorporated selectively, not adopted wholesale.

- [Leonxlnx `redesign-skill`](https://raw.githubusercontent.com/Leonxlnx/taste-skill/main/skills/redesign-skill/SKILL.md)
  Useful for targeted upgrade checklists and "improve without rewriting" discipline.

- [Vercel AI Elements](https://github.com/vercel/ai-elements)
  Useful when the UI includes chat, message streams, and AI-native interface patterns.

- [Prompt Kit](https://github.com/ibelick/prompt-kit)
  Useful for borrowing believable AI product patterns instead of inventing them badly.

- [UI Guides: Writing AI design prompts](https://www.uiguides.com/guides/design-prompts)
  Simple prompt structure for non-designers.

## Forum Signal

Forum posts are not primary sources, but the recurring pattern is useful:

- users get better results when they freeze a style system early
- screenshot-driven refinement beats text-only refinement
- implementation models should build from real components and tokens, not freehand large UI systems

## What The Skill Kept

From these sources, the skill keeps:

- composition-first planning
- explicit visual-direction selection
- visual thesis, content plan, and interaction thesis
- anti-generic safeguards
- image-led first-view composition
- screenshot-first refinement
- token and component-system discipline
- narrative page structure
- responsive and accessibility review
- agentic iteration instead of one-shot prompting

## What The Skill Excluded

The skill intentionally excludes:

- mobile-native platform rules
- deep brand-identity theory
- broad SEO-style prompt collections
- weak listicle summaries
