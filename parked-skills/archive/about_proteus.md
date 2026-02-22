---
type: Concept
primary_audience: Product managers
owner: Product (Proteus) + Engineering
last_verified: 2026-02-06
next_review_by: 2026-05-06
source_of_truth: /data/projects/onafriq-proteus/docs/01-product/specs/high-level-spec.md
---

# About Proteus

## Read when

You are new to Proteus and want a shared understanding of what it is, who it is for, what V1 does (and does not) do, and where to go next for implementation and operations details.

## What Proteus is

Proteus is an internal product and technology map for Onafriq, presented as a dynamic org-chart/mind-map.

Each node represents a product (or product area) and can display metadata like ownership and team details. The map supports hierarchical parent/child relationships, collapsing/expanding, search, and filtering.

## Who it is for

Primary: product managers (portfolio visibility, ownership clarity, discoverability of product context).

Also useful for: engineers and technical staff (architecture and integration context, operational guardrails, content pipeline behavior).

## V1 scope (today)

V1 is a read-only experience:

- Content is seeded from Markdown files stored in Bitbucket.
- A build step parses Markdown into a normalized JSON graph.
- The client loads JSON and renders the map using ELK (layout) with SVG edges and HTML nodes.
- Search and filtering are supported (search index is built ahead of time; client applies filters/search and syncs state to URL params for shareable links).
- Exports: PNG, PDF, CSV.

## Roles and permissions (current + planned)

V1 roles (implemented intent):

- Authenticated Viewer (Office 365 `@onafriq.com`): view map, search/filter, pan/zoom.

Planned for V2 (not in V1):

- Product Admin: edit assigned nodes and their descendants; add/edit highlights.
- Global Admin: full edit access; manage attributes schema and governance workflow.
- Suggestion workflow: non-admin suggestions go to a queue for review/approve/reject.

## Authentication and access

- SSO is handled by Onafriq Home (`home.onafriq.com`).
- Proteus receives a redirect with an authentication token and validates it against the configured SSO validation service.
- Access is restricted to Office 365 users with `@onafriq.com` emails.

## Where the truth lives (content + behavior)

V1 uses Markdown as the content source of truth (git history is used for audit/history in the V1 model).

Important behavior to understand early:

- “Map” detection depends on repository structure (single-map vs multi-map).
- Nodes can be represented as a file note or a folder note (`index.md` conventions).
- Ordering can be controlled by numeric prefixes in file/folder names (prefix-first, then alpha).
- Map `index.md` frontmatter can define display settings (owner tag precedence, tech lead tag precedence, tag ordering, and icon selection).

## Non-goals (V1)

- In-app editing or multi-admin concurrency.
- Runtime Markdown parsing.
- Deep governance workflows (comment threads, SLAs, etc.).

## Hosting and monitoring

- Hosting: Vercel.
- Monitoring: Vercel error logs and analytics (plus any app-level logging adopted by the engineering team).

## Key docs (next steps)

If you want to go deeper, start here:

- Product overview and scope: `/data/projects/onafriq-proteus/docs/01-product/specs/high-level-spec.md`
- Architecture and content pipeline: `/data/projects/onafriq-proteus/docs/04-architecture/v1-architecture.md`
- Delivery/implementation notes: `/data/projects/onafriq-proteus/docs/06-delivery/index.md`
- Test strategy and commands: `/data/projects/onafriq-proteus/docs/07-quality/tests/test-levels.md`
- Operations entrypoint (runbooks live here): `/data/projects/onafriq-proteus/docs/08-operations/index.md`

