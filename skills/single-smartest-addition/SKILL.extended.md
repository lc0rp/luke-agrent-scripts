---
name: single-smartest-addition
description: Find and deliver the single highest-leverage next addition to a project. Use when the user asks what the smartest, most innovative, most accretive, most useful, or most compelling addition would be at this point, including prompts like "What's the single smartest and most radically innovative and accretive and useful and compelling addition you could make to the project at this point?"
---

# Single Smartest Addition

## Goal

Identify the one addition that creates the most upside for the project right now, then either ship the thinnest real version of it or hand back a tight implementation spec if execution is blocked.

This is a singular prompt. Do not return a backlog, top 10 list, or a brainstorm dump unless the user explicitly asks for alternatives.

## Default posture

- Build enough context to understand the product, current maturity, and biggest missing compounding loop.
- Prefer additions that increase future velocity, adoption, retention, insight, or defensibility.
- Innovation must still cash out into usefulness. Do not propose novelty for its own sake.
- Ground the choice in repo evidence, not generic startup advice.
- Default to making the addition, not just naming it, unless the user clearly wants analysis only.

## What counts as a strong answer

Strong candidates usually do one or more of these:

- Unlock a new user loop or tighten a weak one
- Turn manual work into a reusable system
- Add observability or feedback where the team is currently flying blind
- Remove a bottleneck that is suppressing product iteration
- Create a platform capability that future features can cheaply build on
- Add a wedge that meaningfully improves distribution, activation, or retention

Weak candidates usually look like this:

- Cosmetic polish with no strategic leverage
- Refactors that do not unlock user or developer value
- Dependency churn for its own sake
- Vague "AI features" with no obvious fit to the product
- Large rewrites when a thin vertical slice would prove the value faster

## Workflow

### 1) Build context fast

Read the project map first:

- `AGENTS.md`
- `README.md`, `docs/`, `ARCHITECTURE.md`, `dev-docs/README.md`
- app entrypoints, package manifests, test setup, deploy config
- any nearby specs, TODOs, issues, or analytics/telemetry docs

Then inspect the code for:

- unfinished or missing product loops
- repeated manual/operator pain
- places where data is captured poorly or not at all
- obvious quality cliffs blocking adoption
- primitives already present that could support a bigger capability

### 2) Generate a short candidate set

Generate 3-5 serious candidates across different leverage types:

- user-facing product capability
- developer/operator leverage
- measurement/insight
- growth/activation/retention
- trust/reliability, but only if it is clearly a gating bottleneck

Do not show this list to the user unless it helps explain the choice.

### 3) Score for upside, not busyness

Use a lightweight rubric:

- user value now
- compounding value later
- fit with the actual repo and product direction
- novelty delta versus what already exists
- feasibility in the current session
- confidence based on concrete evidence

Pick the candidate with the highest expected value, not the easiest one.

### 4) Make a thesis and commit to it

State the answer in one sentence:

`The single smartest addition is <X> because <Y>.`

Then defend it with repo-specific evidence:

- what is missing today
- why this beats the next-best alternatives
- why now is the right time

### 5) Execute

If the request is action-oriented, implement the thinnest real version that proves the thesis:

- prefer an end-to-end vertical slice
- wire it into the existing UX and architecture
- add tests or validation where it matters
- update docs if behavior changes

If execution is blocked, provide a concrete spec:

- scope
- touched files/systems
- acceptance criteria
- risks
- validation plan

## Output shape

When answering, keep it crisp and decisive:

1. Thesis: the single addition
2. Why this wins: 2-5 repo-specific reasons
3. Execution: what was shipped, or the concrete spec if not shipped
4. Validation: how it was checked

## Heuristics

- If the project is very early, the best addition is often a force multiplier: onboarding, evals, instrumentation, content pipeline, internal platforming, or a first sticky user loop.
- If the project already has users, bias toward retention, insight, reliability, or a feature that deepens the core job-to-be-done.
- If the repo is messy, only choose cleanup when that cleanup clearly unlocks the next product step.
- If several ideas are attractive, choose the one that creates the most future options per unit of effort.

## Anti-patterns

- Do not answer with "it depends" and stop there.
- Do not give ten equal-weight options.
- Do not hide behind strategy language without touching the code when code changes are feasible.
- Do not confuse "ambitious" with "massive".
