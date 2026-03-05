# IA Skill Tightening Plan — Personas + Intent Alignment

## Summary
- Keep top-level IA lifecycle folders unchanged.
- Add audience and intent metadata, templates, hub guidance, and continuity mapping.
- Update IA skill to enforce these rules and checks.

## Goals / Success Criteria
- Every doc declares: `Type`, `Primary audience`, `Owner`, `Last verified`, `Next review by`, `Source of truth`.
- Diataxis purity enforced by templates and lint rules.
- Persona coverage is visible via indexes and hubs without new top-level folders.
- Agent continuity docs map to Diataxis types (no fifth category).

## Non-Goals
- No change to top-level folder list or order.
- No repo-wide content rewrite in this pass.

## Key Decisions
- Keep lifecycle folders as structural backbone.
- Add metadata + audience tagging to make intent/persona explicit.
- Hubs are routing pages only, not sources of truth.

## Changes to IA Skill
- Require intent + audience metadata on every doc (frontmatter or standard header).
- Allow section-level `For: ...` tags only when audiences are mixed.
- Add templates for the 4 Diataxis types.
- Define continuity docs as `How-to` or `Concept` (mapped, not new type).
- Require indexes to include audience + intent tags for each linked page.
- Extend validation to check required metadata and allowed values.

## Doc IA Updates
- Update indexes to include audience + intent tags.
- Add hub pages for user journey entry points (routing only).
- Apply metadata blocks to new or touched pages.

## Testing / Validation
- `pnpm run lint:links`
- `pnpm run lint:ia`
- New: `pnpm run lint:docmeta` (metadata presence + allowed values)
- Spot-check 2–3 exemplar docs across personas.

## Risks / Tradeoffs
- Higher authoring overhead; mitigated by templates.
- Confusion between lifecycle folders and persona intent; mitigated by metadata + hubs.

## Open Questions
- Audience tag format: frontmatter only vs inline `For:` blocks.
- Hub page placement: likely `01-product` and `09-user-docs`, internal analogs as needed.

## Rollout
- Update IA skill + templates + validators.
- Pilot on 2–3 docs.
- Expand via normal doc-touch workflow.
