# Subagent Playbook

Read this file when subagent use is allowed and you expect delegation to help.

## Principle

Keep control of the critical path in the main rollout. Delegate expensive, bounded work. Do not delegate the integration loop unless the artifact contract is extremely clear and the worker can validate its own output without ambiguity.

## When To Delegate End-To-End

Delegate one whole file end-to-end only when all of the following are true:

- the file is an independent job with its own output directory
- success is easy to define from artifacts on disk
- the worker can build and QA the result without blocking the next main-thread step
- recovery is cheap if the worker drifts or times out

Good fit:

- short documents
- clearly digital documents
- one output PDF plus one QA directory

## When To Keep Local Control

Keep orchestration local when any of the following are true:

- the file is long enough that translation will need multiple request batches
- the main work is merging partial outputs, applying responses, building, and QA
- acceptance depends on visual review or override judgment in the main thread
- the document is scan-heavy, mixed, signature-heavy, or legally dense
- the next main-thread step is blocked on the result

For large files, prefer:

1. extract locally
2. prepare translation requests locally
3. delegate only translation-batch generation
4. merge responses locally
5. apply responses, build, compare, and override locally

## Page Count Is A Warning Signal, Not The Rule

Page count is only a proxy for coordination risk.

- `<= 5` pages: end-to-end delegation is usually fine
- `6-15` pages: decide from density, scan quality, and document class
- `20+` pages: default to local orchestration plus bounded translation workers unless the structure is highly repetitive

Use the real decision factors:

- coupling across batches
- glossary consistency pressure
- merge complexity
- QA ambiguity
- cost of worker drift

## Main-Agent Rules

- Treat each source file as its own job.
- Do not mix artifacts, glossary assumptions, or QA conclusions across files.
- Read the filesystem before trusting worker summaries.
- Prefer deterministic artifact checks over narrative progress updates.
- Close completed workers quickly to preserve thread budget.
- If a worker has not produced the promised file within a reasonable window, interrupt or replace it.
- If a worker writes a nearly usable artifact in the wrong shape, normalize it locally instead of redoing finished translation work.

## Delegation Grain

Use the smallest unit that still preserves terminology and context.

- extraction: usually local
- fragment merge: bounded batches
- translation for short docs: one worker may own the whole file
- translation for long docs: one worker per bounded request range or per request
- apply-responses: local unless the artifact contract is trivial
- build + compare + override: local by default

## Worker Contract Design

Every worker prompt should specify all of the following:

- exact read scope
- exact write scope
- exact output path
- exact output schema
- exact assigned request IDs or page range
- explicit non-goals
- exact completion string

Preferred completion pattern:

- write the artifact first
- then reply with only the path written and the exact IDs covered

Do not ask workers for broad summaries when what you need is a file on disk.

## Recommended Timeout Behavior

If a worker does not produce its required file after one meaningful wait:

1. inspect the output directory
2. decide whether the job is stalled, drifting, or partially complete
3. if partially complete, keep the usable artifact and reshard the missing work
4. if stalled, interrupt or replace the worker

## Recommended Local Ownership

The main rollout should usually own:

- run-manifest integrity
- final `translation-responses.json` assembly
- final `translated_blocks.json`
- final PDF build
- final compare-rendered-pages pass
- final override decisions
- final statement of checked pages and residual risks

## Suggested Worker Types

- `agents/translate-batch-worker.md`
- `agents/apply-responses-worker.md`
- `agents/build-and-qa-worker.md`
- `agents/qa-review-worker.md`

Use them as templates and fill in the actual file paths, request IDs, and output locations in the spawn prompt.
