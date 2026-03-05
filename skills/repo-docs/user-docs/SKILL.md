---
name: user-docs
description: 
  Guidelines for documenting a repository project for four primary audiences; builders, operators, testers, and users. Use when creating or updating documentation to ensure clear intent, audience alignment, and maintainability.
metadata:
    short-description: Document a repository project for builders, operators, testers, and users.
    type: Reference
    primary_audience: Documentation owners and contributors
    owner: Documentation program
    last_verified: 2026-02-06
    next_review_by: 2026-05-06
    source_of_truth: ./references/documentation_playbook.md
---

# User Docs Skill (Audience-First, Diataxis-Aligned)

## Purpose

This document describes a repeatable process for documenting a software project for four primary audiences:

- Builders (product and engineering)
- Testers (QA engineers and test automation engineers)
- Operators (content creators and maintainers, or system operators)
- Users (end users)

The goal is to help a reader find the right page for their goal, at the right time, without guessing.

This approach is project-agnostic. You can apply it to Proteus or any other project.

# User Docs (user-docs) vs Dev Docs (dev-docs)

- Dev-docs is designed for in-flight developer-facing documentation. 
- User-docs is designed for steady-state, user-facing documentation. 
- Dev-docs answers: what is being built and what has been built, for fellow developers. 
- User-docs answers: how do I use this and how does it work, for end users or future audiences, who may include builders/developers, but it's not a place/process for in-flight work documentation.

## Core ideas (method)

1. Every page must have one clear intent.
2. Every page must state one primary audience.
3. Documentation must match the user journey (lifecycle).
4. Hubs must route users. Hubs must not duplicate content.
5. Every page must have an owner and review cadence, so it stays correct.

## Terms and definitions

### Page intent (content types)

Use these content types. Do not mix them on one page.

1. Tutorial
This helps the reader learn by doing, with a guided path to first success.

2. How-to
This helps the reader do one specific task quickly.

3. Reference
This helps the reader look up facts (contracts, configuration, limits, fields, error meanings).

4. Concept
This helps the reader understand how something works and why it is designed that way.

### Primary audiences

Use four primary audiences. You can rename them for your project, but keep the meaning stable.

1. Builders
People who design and build the system. This includes product and engineering.

2. Testers
People who verify that the system behaves correctly. This includes QA engineers and test automation engineers. They need test plans, test levels, environments, and reproducible validation steps.

3. Operators
People who keep the system correct, up to date, and safe after it exists. This includes content maintainers, support, and operations.

4. Users
People who use the product to achieve outcomes. This may be internal or external.

### Lifecycle stages (user journey)

Use lifecycle stages to decide what must exist. A project may use a subset, but the list is stable:

- Discover
- Evaluate
- Implement
- Use
- Operate
- Change
- Troubleshoot
- Decommission

## Required metadata (every page)

Every page must include this metadata (frontmatter is preferred):

- `type`: Tutorial | How-to | Reference | Concept
- `primary_audience`: one audience (do not list many)
- `owner`: role or team (not only a person)
- `last_verified`: date or product version
- `next_review_by`: date
- `source_of_truth`: link to the canonical source (PRD, code, API spec, ticket, policy, runbook)

## The workflow (step by step)

### Step 1: Write down the scope and the product boundary

Write one paragraph that says:

- What the product is.
- What it is not.
- Where it sits in a larger system.

This paragraph becomes the anchor for your “About” Concept page.

Output:

- One Concept page: “About <Project>”.

### Step 1.1: Define the audience “start states”

For each audience, write two sentences:

- The problem they are trying to solve.
- The risks if they guess wrong.

This will determine what you must write first.

Example:

- Builders often risk shipping incorrect behavior.
- Testers often risk giving false confidence if tests do not match real behavior.
- Operators often risk corrupting data or content.
- Users often risk misunderstanding ownership or scope.

### Step 2: Identify your workstreams

Workstreams are ownership tracks. They exist because changes originate in different places.

For each workstream, define:

- Owner (team/role)
- Change triggers (what events require updates)
- Review cadence (how often to verify correctness)
- Release alignment (if relevant)

Typical workstreams map well to the four audiences:

- Builders: specs, architecture, delivery notes, test strategy.
- Testers: test strategy, test levels, test plans, test data, environment behavior, and release verification.
- Operators: operational docs, content governance, troubleshooting, runbooks.
- Users: tutorials, tasks, user help, FAQs.

Output:

- A short workstream list in the project hub.

### Step 3: Build a content matrix (Audience + Intent + Lifecycle)

Create a table or list that answers:

- For each audience, what are the top “jobs” they need to do?
- For each job, what lifecycle stage triggers the need?
- For each job, what content type is needed?

Rules:

- Do not start by writing many pages.
- Start by listing the minimum set that provides safe first success.

Output:

- A content matrix document (even if it is only 1 page).

### Step 3.1: Use a default matrix if you have no data yet

If you do not have support tickets or usage data yet, start with this default matrix. Then replace it over time with real “jobs” from your project.

Builders:

- Implement: Tutorial: “Run locally to first success”.
- Implement: Reference: “Environment configuration”.
- Operate: How-to: “Run tests and quality gates”.
- Change: How-to: “Deploy a preview and deploy production”.
- Troubleshoot: Reference: “Common failures and fixes”.

Testers:

- Implement: Reference: “Test levels and scope”.
- Implement: How-to: “Run the full test gate locally”.
- Use: How-to: “Add a new automated test (pattern and folder)”.
- Change: How-to: “Verify a release (smoke tests and critical paths)”.
- Troubleshoot: Reference: “Common test failures and fixes”.

Operators:

- Implement: Tutorial: “Publish a content change end to end”.
- Use: How-to: “Add a new item safely”.
- Change: How-to: “Rename or move an item safely”.
- Troubleshoot: Reference: “Parser warnings and fixes”.

Users:

- Use: Tutorial: “First time use”.
- Use: How-to: “Search and filter”.
- Use: How-to: “Export and share”.
- Troubleshoot: How-to: “No results”.

### Step 4: Create hubs (routing pages)

Hubs are “start here” pages. They should be stable and written in the reader’s language.

Rules:

- A hub should mostly be links.
- A hub should cover the main entry points for the audience.
- A hub should link to a small number of high-value pages for each lifecycle stage.

Minimum hubs for most projects:

- Builders hub
- Testers hub
- Operators hub
- Users hub

Optional extra hubs:

- Troubleshooting hub
- Change hub (release notes, migrations, deprecations)

Output:

- `docs/<project>/index.md` (project hub)
- One hub per primary audience

### Step 5: Write the pages in priority order

Write pages in this order:

1. Tutorials (first success).
2. How-tos (common tasks).
3. References (contracts, settings, error catalogs).
4. Concepts (explain the model and tradeoffs).

When in doubt:

- If the reader might do damage, write a How-to with prerequisites, steps, validation, and fallback.
- If the reader might guess, write a Reference page.

Output:

- A small set of pages that covers the top jobs per audience.

### Step 5.1: Keep language safe for ESL readers

Use these rules:

- Prefer short sentences.
- Prefer common words.
- Define acronyms the first time you use them.
- Avoid jokes and idioms.
- Prefer lists for steps and requirements.

### Step 6: Add review and verification steps

Each page should be easy to verify.

- Prefer linking to code, config, and scripts that enforce correctness.
- Add a “Validation” section for tutorials and how-tos.
- Add a “Troubleshooting” section for how-tos when failure modes exist.

Output:

- Pages that are testable and maintainable.

### Step 7: Apply quality checks (before publish)

Use this rubric:

- Correctness: does it match current behavior?
- Intent purity: is the page only one type?
- Findability: is the title clear and searchable?
- Actionability: are steps safe and complete?
- Maintainability: does it avoid duplication?
- Trust: does it explain security and data handling where needed?

Output:

- A short checklist in PR review, or a docs CI check.

## How to apply this to any project

If you are documenting a different project:

1. Replace “Proteus” with your project name.
2. Keep the same four primary hubs (Builders, Testers, Operators, Users).
3. Build the content matrix from your project’s real change triggers and support questions.
4. Ensure every page has metadata and an owner.
5. Keep hubs link-only and keep content pages intent-pure.

## Bundled references

See `./references/` for templates and checklists you can copy.
