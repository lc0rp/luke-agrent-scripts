---
name: skill-harvester
description: Review the current Codex session for repeated workflows, missing guardrails, or stale skill coverage; recommend whether to create a new skill or update an existing one; then use the skill-creator workflow to implement and validate the chosen skill work. Use when the user asks to harvest reusable skills from the current session, wants recommendations grounded in the live thread, or wants Codex to turn session learnings into new or updated skills.
---

# Skill Harvester

Harvest reusable skill work from the active session. Start from the current thread, compare the observed workflow against existing skills, show a compact audit, then use `skill-creator` to implement and validate the highest-value recommendation.

## Default Target

- Default skill root: `/Users/luke/Documents/dev/luke-agent-scripts/skills`
- If the user names a different destination, use that instead.
- Treat the target root as the primary coverage surface.
- Check global skills only after scanning the target root, to avoid proposing duplicates that are already solved locally.

## What Counts As Skill Material

Promote work into a skill when the current session shows one or more of these patterns:

- the same workflow needs to be rediscovered or restated
- the same validation sequence or failure shield keeps recurring
- success depends on remembering specific paths, scripts, tools, or conventions
- the work naturally breaks into a repeatable procedure another Codex instance should follow
- an existing skill is close, but its triggers, defaults, guardrails, or validation steps are no longer sufficient

Do not recommend skill work for:

- one-off bugs or isolated implementation details
- generic know-how already covered well by current shared skills
- tiny command aliases or trivial reminders that do not justify maintenance

## Workflow

### 1. Review the Current Session First

Use the live thread as the primary evidence source.

Extract:

- repeated tasks or repeated reframing from the user
- steps that had to be rediscovered
- validation or review patterns that should become defaults
- recurring failure modes, confusion points, or decision criteria
- places where an existing skill was used but was incomplete

Prefer concrete evidence from this session over generic brainstorming.

### 2. Scan Existing Skill Coverage

Inspect the target root before recommending anything new.

Check:

- sibling skill folders under the target root
- each candidate skill's `SKILL.md`
- `agents/openai.yaml` when present

Capture:

- which current skills already cover the observed workflow
- where the coverage is partial, stale, too generic, or missing key guardrails
- whether the right action is `update existing skill` or `create new skill`

Prefer updating an existing skill when it already owns the workflow.

### 3. Decide Update Versus New Skill

Recommend an update when:

- the workflow already belongs to an existing skill
- the trigger description is too weak to fire reliably
- the body is missing critical steps, defaults, or validation guidance
- `agents/openai.yaml` drifted from the actual skill behavior

Recommend a new skill when:

- the workflow is meaningfully distinct from current skills
- stretching an existing skill would make it vague
- the session shows a repeatable procedure with durable value

### 4. Display the Audit Before Editing

Present a compact audit to the user in this shape:

1. `Existing coverage`
2. `Suggested updates`
3. `Suggested new skills`
4. `Priority order`

For each recommendation, include:

- skill name
- `update` or `new`
- why it is needed
- what should trigger it
- the smallest valuable scope

If the user asked only for recommendations, stop after the audit.

Otherwise, continue immediately with the top recommendation unless the user asked for a broader batch.

Default to implementing one recommendation at a time. Only batch multiple skills when the scopes are clearly separate and the session evidence is strong.

### 5. Hand Off Implementation to Skill Creator

Use [`$skill-creator`](/Users/luke/.codex/skills/.system/skill-creator/SKILL.md) for the actual create or update work.

For a new skill:

- normalize the skill name to hyphen-case
- scaffold it with `init_skill.py`
- create only the resource directories that are actually needed
- write a concise, trigger-rich frontmatter description
- keep the body procedural and lean
- add or sync `agents/openai.yaml`

Use this initializer unless the user explicitly asked for a different setup:

```bash
python3 /Users/luke/.codex/skills/.system/skill-creator/scripts/init_skill.py <skill-name> --path <target-root> --interface display_name='<Display Name>' --interface short_description='<Short Description>' --interface default_prompt='Use $<skill-name> to ...'
```

For an existing skill:

- update `SKILL.md` in place
- update `agents/openai.yaml` if the UI metadata is stale
- keep ownership with the existing skill instead of cloning it into a new folder

### 6. Validate and Evaluate

After each create or update:

- run `quick_validate.py` on the skill folder
- fix any reported issues and re-run validation
- forward-test non-trivial skills with a fresh subagent when practical

Use:

```bash
python3 /Users/luke/.codex/skills/.system/skill-creator/scripts/quick_validate.py <path/to/skill-folder>
```

Forward-test with a user-like prompt that uses the skill directly. Do not frame the task as a skill review. Ask before forward-testing only if the evaluation is likely to be slow, risky, approval-heavy, or live-system affecting.

### 7. Close With Outcome And Next Recommendations

Report:

- what was recommended
- what was created or updated
- where it was written
- whether validation passed
- whether forward-testing ran
- which remaining recommendations were intentionally left for later

## Failure Shields

- Do not invent recurring patterns without thread evidence.
- Do not create duplicate skills when an update is enough.
- Do not create many speculative skills in one pass.
- Do not leave templated TODO text in the final skill.
- Do not add extra documentation files unless the skill truly needs bundled references, scripts, or assets.
- Do not skip validation after editing a skill.
