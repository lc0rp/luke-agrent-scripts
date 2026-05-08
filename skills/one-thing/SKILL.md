---
name: one-thing
description: Find the single highest-leverage action Luke should take right now for Onafriq. Use whenever Luke asks for "one thing", "highest leverage", "what should I do now", "big hairy audacious action", "big hairy odacious action", "biggest bang for the buck", "turn the dial", "cut through the noise", or asks for a decisive intervention using Slack, work mail, Granola, Obsidian projects, OKRs, weekly CEO briefs, current company context, role context, and web/industry signals.
---

# One Thing

Choose one specific, immediate, high-leverage intervention for Luke as Group CPIO at Onafriq.

This skill is an orchestration skill. It does not replace `brief`, `direct-interactions`, `urgent-interactions`, or `granola-call-logs`; use those source workflows when they are the best way to collect evidence, then synthesize across them.

## Outcome

Return exactly one action Luke can take now that plausibly has the highest expected impact across Onafriq and Luke's role.

The action should be concrete enough to execute in the next 15-90 minutes: a named person, a message, a meeting to force, a decision to make, an artifact to create, a partner/customer intervention, a metric owner to pin down, or an escalation to trigger.

## Source Map

Use the strongest available sources. Do not wait for perfect coverage if enough evidence exists to decide.

1. Time context:
   - Current date, local time, day of week, week/month/quarter/year timing.
   - Interpret timing in `America/New_York` unless the user specifies otherwise.
   - Consider business rhythm: start/end of day, Monday planning, Friday closure, month-end, quarter-end, board/exco cadence, budget cycles, OKR cycles.
2. Role and priority context:
   - Read `/Users/luke/Documents/Obsidian-Onafriq/AGENTS.md`.
   - Read `/Users/luke/Documents/Obsidian-Onafriq/2-Areas/Onafriq/Onafriq.md`.
   - When needed, read role notes under:
     - `/Users/luke/Documents/Obsidian-Onafriq/2-Areas/Chief Product Officer/`
     - `/Users/luke/Documents/Obsidian-Onafriq/2-Areas/Chief Innovation Officer/`
3. Obsidian projects and goals:
   - Search `/Users/luke/Documents/Obsidian-Onafriq/1-Projects/` and `2-Areas/` for active projects, priorities, goals, OKRs, status, blockers, and dated notes.
   - Search local Onafriq planning files when available, especially `/Users/luke/Library/CloudStorage/OneDrive-SharedLibraries-OnafriqLimited/06 - Product - Documents/03 - Planning/2026/OKRs`.
   - Prefer `qmd` when it has an indexed collection; otherwise use `rg` and direct file reads.
   - Pay special attention to P1 projects, Dare/CEO-linked work, board technology committee work, product org work, and items where Luke is default responsible.
4. Weekly CEO brief signals:
   - Use `briefs` to list latest generated briefs when useful.
   - Read the latest generated briefs and the relevant `*weekly CEO brief.md` specs for AI, Stablecoin, Cards, Agency, Network, Platform, and FX/FinOps when they are relevant.
   - Treat unresolved questions, stale metrics, missing owners, and repeated recommendations as leverage signals.
5. Mail and Slack:
   - Use Outlook/Gmail/Slack connectors when available.
   - Prefer direct asks, escalations, executive threads, customer/partner blockers, owner ambiguity, risk, deadlines, and repeated unresolved themes.
   - Borrow the signal bar from `direct-interactions`; do not advance its state file unless Luke explicitly asked for that skill's pull.
6. Granola:
   - Use `granola-call-logs` against `/Users/luke/Documents/Obsidian-Onafriq` for recent meetings, decisions, owner language, commitments, open questions, blockers, and risks.
   - Use transcripts to verify owners, decisions, and nuance when the summary is thin.
7. External landscape:
   - Browse current web sources for unstable industry facts, competitor/partner news, regulatory shifts, payments/stablecoin/AI changes, and macro or market context.
   - Cite sources with links. Use current sources for any claim that may have changed.
8. Open loops and traction:
   - Look for the last 7 days by default unless the user gives another window.
   - Also scan 30-90 days when strategic trajectory matters.
   - Track where there was movement, where movement stalled, and where a small Luke intervention can unlock a much larger system.

## Search Prompts

Use these as starting points, adapted to the date window:

```bash
rg -n "Dare|Simon|board|BTC|P1|priority|OKR|Objective|Key Result|goal|blocked|blocker|risk|decision|owner|follow up|next step|stale|metric|scorecard|TPV|revenue|pipeline|stablecoin|AI|China|Pass|Network|Platform|Cards|FX|FinOps" \
  /Users/luke/Documents/Obsidian-Onafriq/1-Projects \
  /Users/luke/Documents/Obsidian-Onafriq/2-Areas \
  -g '*.md'
```

```bash
qmd search "Dare board OKR blocker decision owner stablecoin AI China network platform cards FX FinOps" -c onafriq-notes -n 40 --json
```

## Candidate Generation

Generate 5-9 candidate interventions before choosing one. Include at least one candidate from each applicable class:

- unblock a P1 initiative
- force a decision or owner assignment
- create an artifact that makes ambiguity impossible
- intervene with a high-priority person
- convert weak traction into measurable traction
- reduce existential, regulatory, customer, or board risk
- exploit a time-sensitive external landscape shift
- make a counterintuitive or outside-the-box move that Luke can uniquely do

Reject candidates that are merely good hygiene, generic planning, passive reading, broad "follow up", or too diffuse to execute today.

## Scoring

Score each candidate 1-5 on:

- **Company impact**: revenue, strategic position, risk reduction, operating leverage, board/CEO importance.
- **Role leverage**: uniquely suited to Group CPIO; crosses product, innovation, tech, commercial, and executive boundaries.
- **Timing**: why now matters given time of day/week/month/quarter and live signals.
- **Neglectedness**: under-owned, stuck, ambiguous, or repeatedly deferred.
- **Execution clarity**: Luke can take the first move in 15-90 minutes.
- **Evidence strength**: supported by multiple sources or one decisive source.

Prefer the candidate with the best expected value, even if confidence is imperfect. Penalize actions that depend on many unavailable facts before Luke can start.

Use this internal formula as a guide:

`leverage = company_impact + role_leverage + timing + neglectedness + execution_clarity + evidence_strength`

Then apply judgment. A single decisive P1 signal can beat a higher numeric score if the downside of delay is large.

## Decision Discipline

- Return one action, not a menu.
- Name the people and channel when possible.
- Write the first message or artifact outline when useful.
- Make uncertainty explicit without hedging the recommendation into mush.
- If evidence is thin because a source failed, say which source was missing and how it affects confidence.
- Do not expose long private source excerpts. Summarize and cite local paths or connector links.
- Do not use source access to update another skill's state unless the user explicitly requested that source skill.

## Output Format

Use this shape:

```markdown
**One Thing**
<one sentence action, with named target and channel>

**Why This**
<3-5 bullets, each tied to evidence or timing>

**Do This Now**
1. <first concrete step, usually message/call/artifact>
2. <second step>
3. <third step>

**Draft**
<ready-to-send message or artifact skeleton, when applicable>

**Evidence**
- <source label/path/link>: <short relevance>
- <source label/path/link>: <short relevance>

**Confidence**
<High/Medium/Low> because <one sentence>. Source gaps: <none or list>.
```

If the user asked for a terse answer, compress to:

```markdown
One thing: <action>.

Why: <one tight paragraph>.

Draft: <message>.
```

## Final Check

Before answering, ask:

- Is this a specific interaction Luke can initiate now?
- Does it use Luke's actual role rather than generic productivity advice?
- Would this plausibly matter to Dare, the board, revenue, product execution, risk, or a P1 initiative?
- Is there a named owner, counterparty, or artifact?
- Did I cite enough evidence for Luke to trust the call?
