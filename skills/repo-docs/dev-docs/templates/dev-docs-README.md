# Project overview

See [README.md](../README.md) for overall project context.

## Project documentation structure

This project uses a standard dev-docs IA docs structure designed to be scalable and LLM-friendly. This file acts as a single navigation point for the dev-docs IA structure.

'Dev-docs' documents in-flight development work. The target user is a fellow developer working on the project, or a hand-off to another team. It answers: what is being built and what has been built. For user-facing documentation or future audiences, readers should be advised to see the `docs/` or `user-docs/` folders.

Linking: standardize on markdown links (no wikilinks); run `pnpm run lint:links` to catch strays.

Flow (ordered by lifecycle):

- [00-foundation](./00-foundation/index.md)
- [01-product](./01-product/index.md)
- [02-research](./02-research/index.md)
- [03-design](./03-design/index.md)
- [04-architecture](./04-architecture/index.md)
- [05-planning](./05-planning/index.md)
- [06-delivery](./06-delivery/index.md)
- [07-quality](./07-quality/index.md)
- [08-operations](./08-operations/index.md)
- [09-user-docs](./09-user-docs/index.md)
- [99-archive](./99-archive/index.md)

Caretakers: each index lists primary roles and update cadence; scrum master keeps this top index in sync at sprint
start/end. Run `pnpm run lint:links` and `pnpm run lint:ia` before merging.
