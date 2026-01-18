# Beads workflow integration

If this file is linked from AGENTS.md, the project uses [beads]([text](https://github.com/steveyegge/beads)) for issue tracking. Issues are stored in `.beads/` and tracked in git.

### Key Concepts

- **Dependencies**: Issues can block other issues. `bd ready` shows only unblocked work.
- **Priority**: 0-4 or P0-P4, 0=highest (default "2")
- **Types**: bug|feature|task|epic|chore|merge-request|molecule|gate|agent|role|convoy|event (default "task")
- **Blocking**: `bd dep add <issue> <depends-on>` to add dependencies

### Essential commands

```bash
bd ready              # Find available work (no blockers)
bd list --status=open # All open issues
bd show <id>          # View issue details with dependencies
bd update <id> --claim # Claim work. MUST run before starting work. Must include --claim flag to prevent race conditions.
bd close <id> --reason="<reason>" --suggest-next # Complete work and see newly unblocked work
bd close <id1> <id2>  # Close multiple issues at once
bd sync               # Commit and push changes. MUST run after each bead close.
bd dep add <issue> <depends-on>` # Add dependencies
bd create             z # Create new bead (see below)
```

### Bead creation
```bash
bd create --title="..." -t=<type> -p=<priority> -d="<desc>"
```

When creating beads, plan thoroughly. Use descriptive titles and set appropriate priority/type. Create a comprehensive and granular set of beads with tasks, subtasks, and dependency structure overlaid, with detailed comments so that everything is self-contained and self-documenting, including relevant background, reasoning/justification, considerations, etc. anything we want our "future self" to know about project goals, intentions, thought process and how it serves the over-arching goals of the project.

### Workflow pattern (MUST follow)

1. **Start**: Run `bd ready` to find actionable work
2. **Claim**: Use `bd update <id> --claim`
3. **Work**: Implement the task
   **File issues for remaining work** - Create issues for anything that needs follow-up
4. **Run quality gates**: if code changed - Tests, linters, builds, ensure task is complete and verified
5. **Sync intermittently**: Run `bd sync` periodically to get latest changes and avoid conflicts
   **Update issue status** - Close finished work with `bd close`, update in-progress items
   
6. **Git/bd atomic commit & push**: - THIS IS MANDATORY AFTER EVERY BEAD CLOSE
    ```bash
    git status
    git pull --rebase
    git restore --staged :/  # Unstage everything to avoid accidental commits
    git add <files>         # Stage code changes
    git commit -m "<type(scope): message>" -- <files> # Only the files you changed
    bd sync # Commit any new beads changes
    git push
    git status  # MUST show "up to date with origin"
    ```
7. **Clean up** - Clear stashes, prune remote branches
8. **Verify** - All changes committed AND pushed
9. **Hand off/Iterate** - Provide context for next task, or iterate if more work remains

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds