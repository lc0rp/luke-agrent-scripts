---
name: exco-interactions
description: Fetch and synthesize Luke's ExCo interactions across Outlook, Slack, and Granola/Obsidian notes, with per-source since-last-pull state, deep links, summaries, and recommended actions.
---

# ExCo Interactions

Use this skill when asked to fetch, pull, monitor, summarize, or triage ExCo interactions across Outlook, Slack, and Granola notes.

This is the canonical definition for ExCo monitoring. Any automation should do little more than check the allowed time window, invoke this skill, and update the skill state after successful source pulls.

Workspace folder: `/Users/luke/work/exco-interactions`

## Automation Window

Use `America/New_York` local time unless the user specifies otherwise.

For recurring heartbeats:

- If `current_time_iso` is outside 4:00 AM through 6:00 PM local time, do nothing: do not query any source, do not update state, and return a quiet no-op heartbeat response.
- If `current_time_iso` is inside the window, run the source workflow below and update state only for sources that were queried successfully.

## State

Default state file:

`/Users/luke/work/exco-interactions/exco-interactions-state.json`

Use one cursor per source so a failure in one source does not lose progress in another:

- `sources.outlook.last_pull_utc`
- `sources.outlook.last_pull_local`
- `sources.slack.last_pull_utc`
- `sources.slack.last_pull_local`
- `sources.granola.last_pull_utc`
- `sources.granola.last_pull_local`

If a source cursor is missing and no date is provided, search the current local day from `00:00`.

## ExCo Roster

Track each person by email, Slack handle/name, title variants, and common name variants.

| Person | Title | Email | Slack | Names and aliases |
| --- | --- | --- | --- | --- |
| Dare Okoudjou | CEO / Founder | `dare.okoudjou@onafriq.com` | `@Dare` | Dare, Dare Okoudjou, Dare Okoudjuo |
| Sumayah Kader | Group Chief of People & Culture | `sumayah.kader@onafriq.com` | `@Sumayah Kader` | Sumayah, Sumayah Kader, Head of PepOps, Head of People Operations, Head of HR |
| Rashi Gupta | Chief Strategy Officer | `rashi.gupta@onafriq.com` | `@Rashi` | Rashi, Rashi Gupta |
| Patrick Gutmann | President and Group Chief Financial Officer | `patrick.gutmann@onafriq.com` | `@Patrick` | Patrick, Patrick Gutmann, CFO, Group CFO |
| Christian Bwakira | Group Chief Commercial Officer | `christian.bwakira@onafriq.com` | `@Christian Bwakira` | Christian, Christian Bwakira, GCCO, Chief Commercial Officer |
| Omotayo Ogunlade | Group Chief Technology Officer | `tayo.ogunlade@onafriq.com` | `@Tayo Ogunlade` | Tayo, Omotayo, Omotayo Ogunlade, CTO, Group CTO |
| Funmi Dele-Giwa | General Counsel & Chief Risk Officer | `funmi.delegiwa@onafriq.com` | `@Funmi` | Funmi, Funmi Dele-Giwa, General Counsel, Chief Risk Officer, GC, CRO |

ExCo group aliases for Slack and Granola:

- `exco`
- `Exco`
- `EXCO`
- `ExCo`

Luke identity:

- Email: `luke.kyohere@onafriq.com`
- Slack/name variants: Luke, Luke Kyohere, `@Luke`

## Outlook Source

Use the Microsoft Outlook Email connector. Keep the current ExCo mail behavior.

Include unarchived Outlook mail:

- From any ExCo email in the roster, or
- To `exco@onafriq.com`

Always exclude messages from:

- `reports@onafriq.com`
- `onafriq.com@reports.onafriq.com`

If the connector does not expose archive state, use the default Outlook list/search behavior and state the limitation only when it materially affects confidence.

### Outlook Search Procedure

1. Read the Outlook cursor from the state file.
2. Build the UTC received window from the requested date range or `sources.outlook.last_pull_utc`.
3. Query messages from ExCo emails.
4. Query messages to `exco@onafriq.com`.
5. If `toRecipients` filter syntax fails, search for `exco@onafriq.com`, fetch candidate messages when needed, and keep only messages whose actual recipients include `exco@onafriq.com`.
6. Remove excluded senders and duplicate Outlook message IDs.
7. Fetch full messages only where thread context or action judgment needs more than the preview.
8. Sort newest first by local received time.

## Slack Source

Use the Slack connector and the Slack skill as the source workflow. Include DMs, mentions, public channels, and private channels available to Luke.

Cast a wide net for now. Include Slack messages or threads in the time window when any of these are true:

- An ExCo person sent the message.
- The message is addressed to, replies to, or directly mentions an ExCo person.
- The message mentions any ExCo name, alias, title, email, Slack handle, or ExCo group alias.
- There is a direct interaction between Luke and an ExCo person.
- There is an ExCo-to-ExCo interaction visible to Luke.

### Slack Search Procedure

1. Read the Slack cursor from the state file.
2. Resolve Slack users from the roster handles/names where possible, then prefer user IDs for searches and links.
3. Search direct messages and channels available to Luke for roster names, Slack mentions, email addresses, title aliases, and ExCo group aliases.
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

Include Granola meetings in the time window when any of these are true:

- An ExCo person attended or appears to have attended.
- The meeting title mentions an ExCo person, alias, title, email, or ExCo group alias.
- The summary or transcript mentions an ExCo person, alias, title, email, or ExCo group alias.
- The meeting has decisions, actions, blockers, risks, or open questions relevant to an ExCo person or ExCo as a group.

### Granola Search Procedure

1. Read the Granola cursor from the state file.
2. Use the `granola-call-logs` helper first for deterministic candidate collection.
3. Search by ExCo names, common names, title aliases, email addresses, and ExCo group aliases.
4. If helper results look incomplete, use `qmd search` against `onafriq-notes` and restrict results back to the daily notes folder and the requested date window.
5. Read matched summary notes and transcripts when needed.
6. Deduplicate by `granola_id` or summary path.
7. Keep local Obsidian paths or Obsidian links where available.
8. Prioritize decisions, actions, owners, open questions, commitments, dates, blockers, and risks over general discussion.

## Cross-Source Synthesis

After collecting source results:

1. Deduplicate near-identical events across sources by time, people, and topic.
2. Correlate Slack and Granola evidence with Outlook threads when they clearly refer to the same topic.
3. Recommend the best course of action based on all available evidence.
4. If evidence is weak or a source failed, say so briefly.
5. Do not invent missing context. Label inferences as inferences.

## Output

Return only new matching items, newest first within each section.

Use this section order:

1. **Mail**
2. **Slack Interactions**
3. **Granola Interactions**

For Outlook mail, preserve the current concise mail format:

- Local date/time.
- Subject as an Office 365 link.
- Sender or recipient match.
- Summary of the current email plus relevant preceding messages.
- Recommended action if one is needed.

For Slack interactions:

- Local date/time.
- Message or thread title/context as a Slack deep link.
- Person or alias matched.
- Summary of the discussion and relevant thread context.
- Recommended action if one is needed.

For Granola interactions:

- Local date/time or meeting date.
- Meeting title linked to the Granola/Obsidian note path where possible.
- Person or alias matched.
- Summary of decisions, actions, blockers, risks, and open questions.
- Recommended action if one is needed.

If there are no new matches in any source, say so and include the searched source windows. For heartbeat no-op responses, use the heartbeat XML format requested by the automation.
