---
name: direct-interactions
description: Fetch and synthesize high-signal interactions for Luke across Outlook, Gmail, Slack, and Granola/Obsidian notes, with per-source since-last-pull state, deep links, summaries, and recommended actions.
---

# Direct Interactions

Use this skill when asked to fetch, pull, monitor, summarize, or triage interactions meant for Luke across mail, Slack, and Granola notes.

This is the canonical definition for direct interaction monitoring. Any automation should do little more than check the allowed time window, invoke this skill, and update the skill state after successful source pulls.

Workspace folder: `/Users/luke/work/direct-interactions`

## Automation Window

Use `America/New_York` local time unless the user specifies otherwise.

For recurring heartbeats:

- If `current_time_iso` is outside 4:00 AM through 6:00 PM local time, do nothing: do not query any source, do not update state, and return a quiet no-op heartbeat response.
- If `current_time_iso` is inside the window, run the source workflow below and update state only for sources that were queried successfully.

## State

Default state file:

`/Users/luke/work/direct-interactions/direct-interactions-state.json`

Use one cursor per source so a failure in one source does not lose progress in another:

- `sources.gmail.last_pull_utc`
- `sources.gmail.last_pull_local`
- `sources.outlook.last_pull_utc`
- `sources.outlook.last_pull_local`
- `sources.slack.last_pull_utc`
- `sources.slack.last_pull_local`
- `sources.granola.last_pull_utc`
- `sources.granola.last_pull_local`

If a source cursor is missing and no date is provided, search the current local day from `00:00`.

When Luke says a sender, subject, topic, Slack source, meeting topic, or recurring item is not relevant, add a durable omit rule to the state file and use it in future pulls.

## Identity

Luke's addresses:

- `luke.kyohere@onafriq.com`
- `luke@beyonic.com`
- `luke@kyohere.com`
- `luke.kyohere@gmail.com`

Mention forms include `Luke`, `Luke Kyohere`, `@Luke`, and `luke.kyohere`.

## Priority Topics

Work:

- Internal topics important to a Group Chief Product and Innovation Officer.
- Stablecoin and adjacent topics.
- AI and adjacent topics.
- China JV and adjacent topics.

Life:

- Kids and family: Linden, Leona, Lydia.
- Health.

## Signal Bar

Keep the result set small. Include an interaction only when it is specifically for Luke and has a concrete reason Luke may need to know, decide, reply, follow up, unblock, or track.

High-signal examples:

- A direct ask, assignment, approval, decision, or escalation for Luke.
- A deadline, commitment, blocker, risk, customer issue, legal/compliance matter, or financial consequence involving Luke.
- A thread where Luke has participated and there is a new action, decision, disagreement, risk, or unanswered direct question.
- A meeting action where Luke is the owner, accountable approver, consulted decision-maker, informed stakeholder for a material topic, or expected follow-up owner.

Exclude low-signal items even when Luke is copied, mentioned, or present:

- FYIs, broad updates, routine chatter, reactions, thanks, greetings, ordinary status updates, passive channel noise, newsletters, digests, alerts, receipts, confirmations, calendar noise, and generic reports.
- Automated mail, mailing lists, system alerts, CI/Jira/GitHub/Bitbucket notifications, OTPs, bank authorization notices, subscriptions, and marketing outreach unless clearly urgent and specifically actionable for Luke.
- Spam and cold outreach. When sender domain is not `onafriq.com`, exclude likely cold email if it is not part of an existing thread, not initiated by Luke, not a referral, sounds generic, has unsubscribe/marketing tracking, or raises spam flags.
- Anything matching `omit_rules` in the state file.

## Mail Sources

Use the Gmail connector for Gmail and Microsoft Outlook Email connector for Outlook. Prefer connector-native links in the final output.

Include only unarchived mail that is directly meant for Luke:

- Direct `To` recipient matches for Luke's addresses.
- Body or subject mentions that explicitly ask for Luke, assign Luke, or materially concern Luke.
- CC-only items only when they meet the utmost-importance bar.

Exclude:

- Read mail.
- Mail Luke has replied to, unless there is a newer inbound message after Luke's reply.
- Broad distribution lists, review-only reports, FYIs, and informational CCs.

### Mail Search Procedure

1. Read the Gmail and Outlook cursors from the state file.
2. Build each source's UTC received window from the requested date range or that source cursor.
3. Search direct recipients for Luke's addresses.
4. Search mention forms in subject/body.
5. Separately search CC matches, then keep only utmost-importance items.
6. Remove read items and messages already replied to by Luke unless the latest message is inbound after Luke's reply. When connector summaries are insufficient, fetch the message or thread.
7. Deduplicate by provider message/thread ID.
8. Apply hard filters, the signal bar, and omit rules.
9. Fetch full bodies or threads only for shortlisted items where context/action judgment needs more than the preview.
10. Sort newest first by local received time.

## Slack Source

Use the Slack connector and the Slack skill as the source workflow. Focus only on direct interactions with Luke.

Include Slack messages or threads in the time window when they clear the signal bar and any of these are true:

- A DM with Luke has new relevant activity.
- Luke is directly mentioned in a message or thread.
- Luke is mentioned in a chat, channel, or thread in a way that asks for Luke, assigns Luke, escalates to Luke, or materially concerns Luke.
- A thread that Luke is part of has new relevant activity.
- A channel where Luke is active has new activity that directly affects Luke, asks for Luke, assigns Luke, or contains a material decision/risk Luke is expected to know.

Do not include ambient channel activity just because Luke has access to the channel. If it is not important, omit it.

### Slack Search Procedure

1. Read the Slack cursor from the state file.
2. Resolve Luke's Slack user identity where possible, then prefer user IDs for searches and links.
3. Search DMs, mentions, threads involving Luke, and active channels available to Luke for direct asks, assignments, decisions, blockers, risks, deadlines, and material follow-ups.
4. Pull thread context for shortlisted messages where the action, decision, owner, or recipient is unclear.
5. Deduplicate by Slack message URL or `channel_id` + `ts`.
6. Keep deep links to messages or threads whenever the connector returns them.
7. Sort newest first by local message time.

## Granola Source

Use the `granola-call-logs` skill.

Granola source:

- Vault root: `/Users/luke/Documents/Obsidian-Onafriq`
- Daily notes folder: `2-Areas/Journaling/Daily`
- qmd collection: `onafriq-notes`

Include Granola meetings in the time window only when there is a high-signal action, decision, or responsibility for Luke:

- An action Luke needs to do.
- An action Luke needs to follow up on.
- A commitment, open question, blocker, risk, decision, or deadline assigned to Luke.
- A RACI-style responsibility where Luke is Responsible, Accountable, Consulted, or Informed for a material topic and there is a concrete next step or decision context.

Do not include a meeting just because Luke attended, was mentioned, or the topic is generally interesting.

### Granola Search Procedure

1. Read the Granola cursor from the state file.
2. Use the `granola-call-logs` helper first for deterministic candidate collection.
3. Search by Luke mention forms, action language, owner language, follow-up language, and RACI terms: responsible, accountable, consulted, informed, owner, action, follow up, decide, approve, blocker, risk, deadline, next step.
4. If helper results look incomplete, use `qmd search` against `onafriq-notes` and restrict results back to the daily notes folder and the requested date window.
5. Read matched summary notes and transcripts when needed.
6. Deduplicate by `granola_id` or summary path.
7. Keep local Obsidian paths or Obsidian links where available.
8. Prioritize decisions, actions, owners, open questions, commitments, dates, blockers, and risks over general discussion.

## Cross-Source Synthesis

After collecting source results:

1. Deduplicate near-identical events across sources by time, people, and topic.
2. Correlate Slack and Granola evidence with mail threads when they clearly refer to the same topic.
3. Recommend the best course of action based on all available evidence.
4. If evidence is weak or a source failed, say so briefly.
5. Do not invent missing context. Label inferences as inferences.

## Output

Return only new matching items, newest first within each section.

Use this section order:

1. **Mail**
2. **Slack Interactions**
3. **Granola Interactions**

For mail:

- Local date/time.
- Subject as an Office 365 or Gmail link.
- Sender or recipient match.
- Summary of the current email plus relevant preceding messages.
- Recommended action if one is needed.

For Slack interactions:

- Local date/time.
- Message or thread title/context as a Slack deep link.
- Why this is specifically for Luke.
- Summary of the discussion and relevant thread context.
- Recommended action if one is needed.

For Granola interactions:

- Local date/time or meeting date.
- Meeting title linked to the Granola/Obsidian note path where possible.
- Luke's role or responsibility.
- Summary of decisions, actions, blockers, risks, and open questions.
- Recommended action if one is needed.

If there are no new matches in any source, say so and include the searched source windows. For heartbeat no-op responses, use the heartbeat XML format requested by the automation.
