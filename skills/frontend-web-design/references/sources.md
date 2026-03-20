# Sources

Last reviewed: 2026-03-20

This skill synthesizes the sources below into one web-only workflow.

## Top 10 Core Sources

1. [Anthropic `frontend-design` skill](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md)
   Why it matters: strong anti-generic aesthetic guidance; pushes explicit visual direction and intentional detail.

2. [OpenAI Cookbook: Frontend coding with GPT-5](https://cookbook.openai.com/examples/gpt-5/gpt-5_frontend)
   Why it matters: strong multimodal frontend workflow; encourages image-aware design iteration and practical implementation.

3. [OpenAI Developers Blog: Building frontend UIs with Codex and Figma](https://developers.openai.com/blog/building-frontend-uis-with-codex-and-figma)
   Why it matters: strong guidance for design-to-code, screenshot/visual context, and realistic frontend workflows inside Codex.

4. [v0 Docs](https://v0.dev/docs?trk=public_post-text)
   Why it matters: practical official workflow guidance for prompting, iteration, and product-oriented UI generation.

5. [v0 Docs: Screenshots](https://v0.dev/docs/screenshots)
   Why it matters: makes the screenshot-first workflow explicit; very useful for non-designers.

6. [v0 Docs: Design Mode](https://v0.dev/docs/design-mode)
   Why it matters: separates generation from visual refinement; useful pattern even outside v0.

7. [shadcn/ui Theming](https://ui.shadcn.com/docs/theming)
   Why it matters: token discipline and CSS-variable-based theming; lowers drift and improves consistency.

8. [Refactoring UI](https://refactoringui.com/)
   Why it matters: still one of the best design resources for developers and non-designers working on product UI.

9. [Laws of UX](https://lawsofux.com/)
   Why it matters: fast, practical UX heuristics that convert well into prompt constraints and review criteria.

10. [web.dev: Design and UX for accessibility](https://web.dev/learn/accessibility/design-ux/)
    Why it matters: brings accessibility, contrast, state clarity, and usable interaction design into the design pass.

## Supporting Sources

- [OpenAI Cookbook: Build a coding agent with GPT-5.1](https://cookbook.openai.com/examples/build_a_coding_agent_with_gpt-5.1)
  Useful for the scaffold-patch-run-verify loop that keeps frontend work grounded in real code and validation.

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
- explicit visual-direction selection
- anti-generic safeguards
- screenshot-first refinement
- token and component-system discipline
- responsive and accessibility review
- agentic iteration instead of one-shot prompting

## What The Skill Excluded

The skill intentionally excludes:
- mobile-native platform rules
- deep brand-identity theory
- broad SEO-style prompt collections
- weak listicle summaries
