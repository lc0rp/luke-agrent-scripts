---
name: safe-loop
description: Keep a coding agent in a safe autonomous execution loop for epics, multi-step tasks, and long repair sessions. Use when the user wants the agent to keep working through red/green/fix/verify cycles with concrete evidence, install any missing scaffolding required to finish the work, continue across tasks and subtasks without waiting for frequent replies, and stop early only if the next step would be destructive, dangerous, or a clear regression against functionality or company goals.
---

# Safe Loop

Use this skill when the user wants sustained autonomous execution and may not be available to respond between subtasks.

## Operating Rule

Continue through red/green/fix/verify with concrete evidence at each step. Do not stop at surface "test-targeting fixes". Complete the real implementation under the test, install or create the scaffolding needed to finish the task, and keep moving until the whole epic or task is done.

## Default Behavior

- Keep going across tasks and subtasks without waiting for routine confirmation.
- Send short progress updates so the user can interrupt or steer if needed.
- Verify with real evidence such as failing tests, passing tests, logs, screenshots, builds, traces, or equivalent outputs.
- Add or install missing harnesses, fixtures, dependencies, scripts, or validation scaffolding when they are required to complete the work properly.
- Prefer root-cause fixes over narrow edits that only make a specific test pass.
- Use subagents when the work splits cleanly and the expected speed, quality, or coverage gain is worth the coordination cost.

## Stop Early Only If

- the next step is destructive or hard to reverse
- the next step is dangerous from a security, data-loss, production, or compliance perspective
- the next step would reduce functionality or move the work backward relative to product or company goals
- the next step requires missing approvals, credentials, hardware, or external information that cannot be inferred safely

If you must stop, state the blocker, the risk, and the exact next step needed to resume.

## Completion Standard

Do not declare success from intent alone. Leave a concrete trail of what failed, what changed, and what now passes.
