# Project overview

See [README.md](../README.md) for overall project context.

## Project documentation structure

This project uses a standard documentation structure. It works for people and LLMs (large language models). Use the index below to find docs.

Rules:
- Use markdown links only (no wikilinks). Run `pnpm run lint:links`.
- Every page lists doc type and primary audience in frontmatter or the header block.
- One doc type per page.

Order (by project stage):

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

Each index lists the owner and update schedule. The scrum master keeps this page updated each sprint. Run `pnpm run lint:links` and `pnpm run lint:ia` before merging.
