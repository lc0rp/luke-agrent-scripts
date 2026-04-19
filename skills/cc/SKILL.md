---
name: cc
description: Analyze the current git worktree, infer the real intent of the change, craft a conventional commit message, stage the right files, and create the commit. Use when the user says cc, commit this, make a conventional commit, or asks Codex to inspect the current work and commit it.
---

# CC

Use this skill when the user wants Codex to turn the current local changes into a conventional commit.

## Workflow

1. Inspect the worktree before committing.
2. Read enough diff context to understand what changed and why.
3. Decide whether the modified files form one coherent commit.
4. Write a conventional commit message that matches the actual change.
5. Stage the intended files.
6. Create the commit.

## Inspect First

Start with git state, not assumptions.

- Run `git status --short`.
- Run `git diff --stat` and `git diff --cached --stat`.
- Read the relevant diffs before writing the message.

If there are both staged and unstaged changes, or multiple unrelated themes in the worktree, do not blindly sweep everything into one commit. Summarize the split and ask the user which slice to commit.

If there is nothing to commit, say so plainly and stop.

## Commit Message Rules

Write a conventional commit message in this shape:

`type(scope): summary`

Guidelines:

- Pick the type from the actual intent: `feat`, `fix`, `refactor`, `style`, `docs`, `test`, `build`, `ci`, `chore`, `perf`, or another conventional type only when justified.
- Use a scope when it adds clarity.
- Keep the summary short, imperative, and specific.
- Base the message on the source change, not on noisy generated output.
- If generated artifacts changed only because source files were rebuilt, reflect the source intent in the message.

## Staging Rule

Stage only the files that belong in the inferred commit.

- If all changes clearly belong together, stage them together.
- If the worktree is mixed, stop and ask instead of guessing.
- Do not revert unrelated user changes.

## Commit

After staging, create the commit with the conventional message.

Use non-interactive git commands. After committing, report:

- the final commit message
- the new commit SHA
- whether any local changes remain uncommitted
