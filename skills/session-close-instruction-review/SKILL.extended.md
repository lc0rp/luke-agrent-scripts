---
name: session-close-instruction-review
description: Review the current session before closing and identify anything that should be turned into durable instructions in AGENTS.md or packaged as a reusable skill. Use when the user asks questions like "Review the session before we close. Anything we can/should turn into instructions in AGENTS.md or into reusable skills?"
---

# Session Close Instruction Review

Answer this prompt:

Review the session before we close. Anything we can/should turn into instructions in AGENTS.md or into reusable skills?

## Goal

Before ending a session, scan the work for reusable patterns worth codifying.

Prefer durable, repeatable guidance. Ignore one-off facts, temporary hacks, and project noise.

## Review sources

Check the highest-signal artifacts from the current session:

- the user request and any corrections
- files changed
- commands run and exact errors seen
- decisions that unblocked progress
- repeated patterns that would help in future sessions

## Decision rule

Only recommend codifying something if it is likely to help again.

Use this split:

- `AGENTS.md`: stable behavioral rules, repo conventions, workflow defaults, validation expectations, tool preferences
- reusable skill: multi-step workflows, domain procedures, tool-specific playbooks, repeatable prompting patterns
- neither: one-off implementation details, temporary environment issues, or facts already covered elsewhere

## Output shape

Keep the answer short and decisive.

For each candidate, include:

1. what to capture
2. where it belongs: `AGENTS.md`, a new skill, or nowhere
3. why it will pay off again

If nothing is worth codifying, say so plainly.

## Quality bar

- Prefer 0-3 strong suggestions over a long list
- Be concrete enough that the instruction or skill could actually be written next
- Do not suggest a skill when a short `AGENTS.md` rule would do
- Do not suggest `AGENTS.md` for content that is really a procedure
