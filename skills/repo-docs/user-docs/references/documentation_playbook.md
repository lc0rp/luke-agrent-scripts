---
type: Concept
primary_audience: Documentation owners and contributors
owner: Luke, author
last_verified: 2026-02-06
next_review_by: 2026-05-06
source_of_truth: ./documentation_playbook.md
created: 2026-01-01T04:15:31-05:00
updated: 2026-02-05T15:34:53-05:00
---
This is an overview of our documentation guidelines, for documentation owners and contributors: mainly product managers and workstream owners, as well as stakeholders in Engineering, Support, Marketing, and Compliance departments.

Documentation is part of the product experience. It is important to our users because it helps them discover, buy, implement, operate, troubleshoot, and trust what we build. It is also important to us. Our goal is simple: to have the right documentation for the right person at the right time, and to keep it up to date with minimal effort.

## What does “good” documentation look like?

Documentation is successful when:

- A new reader can quickly find what they need.
- A user, administrator, or operator can complete a task safely every time.
- A technical user or engineer can find out the exact behavior without guessing.
- Decision-makers can understand what the product is, why it is important, and how it works at a high level.
- Auditors and risk officers can check controls, data handling, and compliance claims with clear evidence, such as control mappings, attestations, test summaries, and policy excerpts.

### Non Goal

We want to avoid creating a single, large “User Guide” that tries to please everyone but ends up satisfying no one.

### Here are some examples of "good" documentation:

We have based the principles in these guidelines on industry best practices and successful models like [Diátaxis](https://diataxis.fr), [arc42,](https://arc42.org) and the [C4 model](https://c4model.com). These frameworks are used effectively by well-known B2B companies recognized for their quality documentation, such as the ones below:

- [**Stripe Docs**](https://stripe.com/docs) – API-first documentation with clear examples.

- [**Twilio Docs**](https://www.twilio.com/docs) – practical guides, SDKs, and a focus on developer experience.

- [**AWS Documentation**](https://docs.aws.amazon.com/) – comprehensive reference material and how-to guides for enterprise needs.

- [**Kubernetes Docs**](https://kubernetes.io/docs/) –  well-organized sections, split between: Concepts, Tasks, Tutorials, and Reference.

- [**Django Docs**](https://docs.djangoproject.com/) – known for consistently strong documentation.

## Topics covered below

To create a framework for our documentation, we shall cover three areas:

- **Content Matrix (Intent/Audience/Lifecycle)** = what documentation to create
- **Documentation Hubs** = how users find it without thinking too hard
- **Workstreams** = who keeps it accurate as reality changes

In other words, we will cover: content, access, and accountability

## A. Content Matrix - What content to create

How do we determine what documentation we should create? How do we evaluate our documentation? How do we identify documentation gaps?

### A.1. Intent: Our content types should match user intent

According to  [Diátaxis](https://diataxis.fr), users want to do one of four things. Each page should show which of these things it helps the user accomplish, and each page should follow a matching template based on that intent. We should not mix or combine more than one intent on each page:

1. **Tutorials (User intent: to Learn)**
   - **Purpose:** a practical, guided path to first success.
   
   - **Structure:** Overview → Prerequisites → Steps → Validation → Next steps.
   
   - **Other terms:** Quick start guides, get started
   
2. **How-tos / Tasks (User intent: to 'Do' something specific)**

   - **Purpose:** achieve a specific outcome quickly.

   - **Structure:** Overview → Prerequisites → Steps → Troubleshooting notes → Next steps.

3. **References (User intent: Look up something specific)**

   - **Purpose:** accurate, complete, searchable facts (APIs, parameters, limits, error codes, pricing tables where needed).

   - **Structure:** Summary → Details (structured) → Examples → Edge cases → Version notes.

4. **Concepts / Overview (User intent: Understand why, how it works)**

   - **Purpose:** explain how it works, mental models, key ideas, tradeoffs.

   - **Structure:** Overview → Core concepts → Flows/diagrams → Common misconceptions → Links to tasks/reference.

   - **Other terms:** Explainers, architecture, how-it-works, design notes

#### Master list of document artifacts by content type

Use this as a menu of "document types” we can create. The same artifact name can be used for different audiences, but each page should focus on, and clearly state only one intent.

##### 1) Tutorials (Learn)

- Getting started / Quick start / First transaction
- End-to-end walkthrough (common scenario)
- “Build your first …” (partner/dev)
- Sandbox tutorial (test credentials, test data)
- Sample app tutorial (reference implementation)
- Onboarding tutorial (admins/operators)
- Migration tutorial (guided upgrade path)
- Interactive labs (if we have the platform)
- Training modules (internal enablement)

##### 2) How-tos / Tasks (Do)

- How to onboard (customer, merchant, partner)
- How to configure (settings, roles, permissions)
- How to integrate (API + callbacks/webhooks)
- How to reconcile/settle (operational workflows)
- How to handle failures (retries, reversals, disputes)
- How to monitor (dashboards, alerts)
- How to run common ops procedures (operational playbooks)
- How to troubleshoot a specific symptom (“if X then Y”)
- Checklists (go-live checklist, rollout checklist)
- Playbooks (incident response steps, escalation)

##### 3) References (Look up)

- API reference (OpenAPI/Swagger, endpoints, schemas)
- SDK reference (methods, types, examples)
- Webhook/callback reference (events, payloads, signatures)
- Error code catalog (codes, meanings, remediation)
- Limits & constraints (rate limits, size limits, timeouts)
- Configuration reference (env vars, feature flags, settings)
- Data dictionary (fields, definitions, formats)
- Permissions/roles matrix (who can do what)
- Pricing & fees tables (where appropriate, versioned)
- SLA/SLO definitions + service boundaries
- Glossary (terms and definitions)
- Compliance/control reference (control IDs, scope, evidence links)

##### 4) Concepts / Overviews (Understand)

- Product overview (what it is, who it’s for, value)
- Conceptual model (key entities and relationships)
- How it works (flows, lifecycle, state machines)
- Architecture overview (C4 L1–L2) and deeper dives (L3–L4)
- Security model (threat model summary, trust boundaries)
- Data handling model (PII, retention, residency, logging)
- Design rationale / tradeoffs / “why it is this way”
- Integration patterns (recommended approaches)
- Operational concepts (idempotency, retries, reconciliation)
- Internal: Architecture Decision Records (ADRs), design notes

#### Rule:

We do not mix types on one page. If you feel the urge, you probably need two pages.

### A.2. Audience: We should know who we write for

Each page should clearly state its main audience and any assumptions it makes. The intended audience will help us decide what topics the page should include.

### External audiences:

- **Non-users or buyers**: Expect information about what it is, results, prices, how hard it is to set up, security, and more.

- **Admins or operators**: Expect details about setting up, permissions, monitoring, responding to problems, and more.

- **End users**: Want to learn how to do their work and common tasks.

- **Developers or partners**: Need guides for APIs, how to connect, SDKs, and practice environments.

### Internal audiences:

- **Sales and marketing**: Want to understand our positioning, use cases, competitors, FAQs, and more.

- **Support and operations**: Need information about procedures, troubleshooting, known issues, and how to escalate problems.

- **Engineers**: Want product requirement documents, technical details, system design, decision records, internal APIs, and operational guides.

- **Leadership**: Expect explanations of strategy, plans, key numbers, and risks.

- **Risk, compliance, and audit teams**: Want to understand controls, proof, how data is handled, changes, and more.

### A.3. Lifecycle, or user journey: When docs are needed&#x20;

Different information is needed at different parts of a user’s journey with the product. In addition to audience and intent, we need to consider a user's stage when creating documentation, from discovering the product to stopping use. **Audience + Intent + Lifecycle** ensures we have the right content.

#### **Example**:

- **Audience**: Partner engineer
- **Intent**: Integrate API
- **Lifecycle**: Pre-production/build phase
   → We can predict we need this content: auth guide, sandbox setup, error handling, webhook retries, test vectors, etc.

#### **Lifecycle stages include**:

- **Discover**: what it is, who it’s for, and outcomes. 
- **Evaluate**: pricing, security, compliance, architecture overview, FAQs.
- **Implement**: onboarding, prerequisites, integration tutorials, checklists.
- **Use**: role-based tasks and workflows.
- **Operate**: monitoring, SLAs/SLOs, operational playbooks, incident playbooks.
- **Change**: release notes, migration guides, deprecations.
- **Troubleshoot**: error catalog, known issues, “if X then Y” guides.
- **Decommission**: offboarding steps, data retention, and export.

#### Lifecycle examples

A number of large B2B doc sites consider the “customer journey” even if they don’t explicitly call it that. Here are some examples:

- **Okta: “journey” framing.** Okta’s docs [home page](https://developer.okta.com) and [Okta’s guides](https://developer.okta.com/docs/guides/) are framed around the customer journey including planning, designing, building, deploying and troubleshooting.
- **Auth0: explicit lifecycle, especially for change/deprecation.** They have [Get Started](https://auth0.com/docs/get-started), a dedicated [Troubleshoot](https://auth0.com/docs/troubleshoot) area, and a “[Product Lifecycle](https://auth0.com/docs/troubleshoot/product-lifecycle)” section with deprecations/migrations and release stages.
- **Stripe: clean “Implement + Change” entry points.** [Get started](https://docs.stripe.com/get-started) and [quickstarts](https://docs.stripe.com/quickstarts) for implementation, [API reference](https://docs.stripe.com/api) for lookup, and a [changelog](https://docs.stripe.com/changelog) for ongoing change management.
- **Cloudflare: Top level “get started / troubleshoot / changelog”.** Their docs landing page prominently features “[Get started](https://developers.cloudflare.com/)” and “[Troubleshoot errors](https://developers.cloudflare.com/fundamentals/reference/troubleshooting/),” and they keep a central [changelog](https://developers.cloudflare.com/changelog/). 
- **Datadog (B2B): strong “Implement / Operate / Troubleshoot.”** Dedicated Getting Started, API reference, and troubleshooting sections (Agent, RUM, etc.). [Datadog+2Datadog+2](https://docs.datadoghq.com/getting_started/?utm_source=chatgpt.com)
- **GitHub Enterprise Server (B2B): “Change + Decommission.”** They publish admin release notes and “all releases” pages that include discontinuation dates (an explicit decommission/offboarding signal). [GitHub Docs+1](https://docs.github.com/en/enterprise-server@3.14/admin/release-notes?utm_source=chatgpt.com)

## B. Hubs, entrypoints, or “routing” pages - How users find & navigate our content

If audience, intent, and lifecycle ensure we have the right content, hubs are where that content lives and how we route users through them. They are the means by which users find and navigate it. We need to create entry points for the most important stages, from discovery to decommissioning, so people can find the right help when they need it the most.

These entry points are found on our content hubs, such as websites, developer docs, Zendesk, product portal help pages, release notes emails, Confluence, SharePoint, and others.

Users visit these hubs at different times during their journey. Because of this, choosing the right hubs is important, and product documentation "entry points" should be available across these hubs based on where users are in their journey.

### Hubs are not content types

Hubs are often confused with content types (intent) discussed in section A above. 

Hubs should not try to replace content. They should be short, focused, and mainly contain links to actual content pages above. Examples include:

- FAQs (answer briefly, then link to authoritative content)

- Landing pages/entry points (like “Start here”, “Onboarding”, “Troubleshooting”)

- Customer journey hubs (Discover, Evaluate, Implement, Use, Operate, Change, Troubleshoot, Decommission)

- Indexes (API index, error index, integration patterns index)

The first two lifecycle stages are repeated below to showcase hub examples.

- **Discover**: what it is, who it’s for, and outcomes. 
  - Hub example: our main website should lead non-users and potential buyers to the overview pages. 
  - Also, sales and marketing executives should receive a product overview packet.
- **Evaluate**: pricing, security, compliance, architecture overview, FAQs.
  - Hub example: the sales executive packet should include pricing.
  - Internal audit will want an overview that covers security and compliance.
  - Something to think about: Where should the FAQ sections be placed? In Zendesk, or somewhere else? 
- And so forth.

A single documentation page can be connected to many customer journey/lifecycle hubs. The page type (tutorial, task, reference, or concept) should remain clear and unchanged.

### Rule:

Maintain a single source of truth. It is better to link content across hubs rather than copy it into each hub. Keeping documentation up to date is difficult. Duplicating it makes this even more challenging.

### How to choose hubs

Pick 5-9 hubs based on **user entry points**. For example:

1. **List top user “jobs”** from support tickets, sales/SE questions, onboarding checklists, and API integration patterns
   - E.g "Build & Integrate" hub for API developers
2. **Cluster them** (card-sort style) into 5–9 groups
3. Name clusters in the **user language** (not internal product names), e.g., "Build & integrate", not "Dev-lab 2.0"
4. Make sure hubs are:
   - **stable** (won’t change every quarter),
   - **distinct** (minimal overlap at the top level),
   - **complete enough** (most docs have an obvious “home”),
   - **small** (too many hubs = nobody remembers them)

#### **Using the previous example**:

- **Audience + Intent + Lifecycle** ensures we have the right content. Hubs are how users find and navigate that content
- **Audience**: Partner engineer
- **Intent**: Integrate API
- **Lifecycle**: Pre-production/build phase
   → We can predict we need this content: auth guide, sandbox setup, error handling, webhook retries, test vectors, etc.
- **<u>Hub</u>**: We might then decide to create a "Build & Integrate" page on our website with links to all these articles.

## C. Workstreams - Who owns & updates the documentation

Finally, workstreams are how we manage all of this.

In many companies, documentation often becomes outdated, and efforts to keep it current tend to fail. This isn’t because of a poor system, but because:

- "everyone assumed someone else did it.”
- updates miss scheduled release periods,
- there is no single agreed-upon completion criteria,
- content becomes stale because nobody is responsible for maintaining its accuracy.

Workstreams should be based on **where changes originate** and **who can authoritatively verify correctness**. A workstream should exist when there’s a distinct **source of truth** and a distinct **change trigger.**

Common examples of change triggers include:

- API updates
- new product/feature launches
- pricing/commercial changes
- operational runbook changes
- compliance/regulatory updates
- incident learnings / known-issues updates
- partner onboarding patterns

Each workstream should have an owner, a review cadence, and a release alignment.

Example workstreams:

- **Buyer documents (Commercial team) and Trust documents (Security/Compliance team)** (co-owned): 
  - Overview, pricing, implementation summary, 
  - Plus a compliance pack (security & compliance claims backed by evidence: certifications, available controls, pen test summary, policies, and audit artifacts).

- **User Help** (owned by Product): 
  - Tutorials, tasks, UI reference, FAQs.

- **Developer** **documents** (owned by Engineering + Product): 
  - API reference, integration guides, SDK docs, samples.

- **Operations documents** (owned by SRE/Operations + Support):
  -  Operational playbooks, incident guides, monitoring, support playbooks.

- **Internal Product/Engineering** **documents** (owned by PM + Eng): 
  - PRDs/RFCs, ADRs, architecture docs, operational decisions.

- **Change documents** (Owned by Release Manager + PM):
  - Release notes, changelog, migrations, deprecations.


**Rule**:

Every page should belong to exactly one workstream for ownership purposes. Cross-links are encouraged.

## Required metadata on every page

Putting this all together, every doc page must include:

- **Type**: Tutorial | How-to | Reference | Concept
- **Primary audience**: one of the tiers above
- **Owner**: role or team (not just a person)
- **Last verified**: product version/date
- **Next review by**: date (based on workstream cadence)
- **Source of truth**: link to system or repo (PRD, API spec, ticket, policy)

## How documentation work happens

Documentation is part of delivery, not an afterthought. Definition of Done (DoD) - or in our parlance, the sign-off and launch checklists, for any change that affects users, partners, ops, pricing, or controls, must include:

- Appropriate docs updated (or explicitly marked “no doc change”).
- Release notes entry created when user-visible behavior changes.
- Reference updated from source where possible (OpenAPI, schema, config).
- Support notes/operational playbook updated for new failure modes.
- Links validated and examples verified.

Workflow:

- Draft in the workstream’s home.
- Review includes at least: a domain reviewer (PM/Eng) and a clarity reviewer (someone not on the project).
- Publish, then link into relevant customer journey hubs.

## Quality bar and checks

We use a lightweight rubric:

- **Correctness**: matches current behavior.
- **Intent purity**: page type matches content.
- **Findability**: searchable title, consistent terms, tagged audience and customer journey links (Discover/Evaluate/Implement/Use/Operate/Change/Troubleshoot/Decommission).
- **Actionability**: tasks have prerequisites, steps, validation, and fallback.
- **Maintainability**: avoids duplication and links to the canonical reference.
- **Trust**: where relevant, includes security, data handling, and pricing clarity.

## Governance

- Each workstream runs a monthly “docs triage” to identify stale pages, top support issues, top search misses, etcetera.
- Quarterly: review customer journey hubs for gaps and broken paths.
- Measure: doc freshness (pages verified on time), search success, ticket deflection, and top “confusion themes.”

## Summary

If you’re unsure where something belongs, pick the reader’s goal: Learn, Do, Look up, or Understand. Then use the matching template and link to the rest.
