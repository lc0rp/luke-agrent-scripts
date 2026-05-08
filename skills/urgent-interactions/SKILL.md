# urgent-interactions

Use this skill to find unread, unarchived, high-signal interactions Luke should know about now across mail, Slack, and meeting context.

This is the interaction-oriented successor to `urgent-mail`. Do not extend `urgent-mail`; keep this skill independent so the automation can include automated mail, mailing lists, Slack activity, Granola transcripts, and meeting notes in one pass.

## Inputs

- Gmail inbox messages.
- Outlook inbox messages.
- Slack messages, mentions, DMs, channel messages, threads, and canvases available through the Slack connector.
- Granola transcripts and meeting notes via the `granola-call-logs` skill; use the Granola connector too when it is available.
- The state file at `/Users/luke/work/urgent-interactions/urgent-interactions-state.json`.

## Time Window

1. Check America/New_York local time first.
2. If the current local time is outside 4:00 AM through 6:00 PM, do not query any source and do not update state.
3. If a date or time window is explicitly provided, use it.
4. Otherwise, read `last_pull_utc` from the state file and query only items newer than that.
5. If there is no state file or no `last_pull_utc`, default to the current local day.
6. After a successful in-window run, update `last_pull_utc` and `last_pull_local` to the heartbeat/run timestamp.

## Include Criteria

Include only unread or newly available interactions that are red-alert or strong FYI signals:

- Payments due, overdue, failed, declined, at risk, or needing approval unless covered by omit rules.
- Tax, government, compliance, audit, legal, or regulatory deadlines.
- Events, school, medical, travel, pickup/dropoff, or logistics involving Linden or Leona.
- Any email or interaction from Lydia McClure, especially `lydia.mcclure@gmail.com`.
- Security issues: suspicious login, MFA, password reset, account lockout, breach, fraud, abuse, phishing risk from a real account, compromised credentials, certificate/domain/security alert.
- Accounts, domains, services, cards, subscriptions, storage, or access that are expiring, being deleted, suspended, downgraded, blocked, or requiring action.
- Concrete near-term or missed deadlines, especially where inaction creates cost, loss, access loss, customer impact, compliance risk, or relationship risk.
- Slack or meeting content where Luke is assigned, blocked, explicitly asked to decide, or needs to know about an urgent risk.
- Granola notes/transcripts where a decision, action item, risk, deadline, or commitment matching this scope appears, even if it was not emailed.

## Exclude Criteria

Suppress noise aggressively:

- Read mail, read Slack items, or previously reported meeting items unless there is a newer inbound/update.
- Mail Luke has replied to unless there is a newer inbound message.
- Spam, likely phishing, cold outreach, sales nurture, newsletters, weak marketing urgency, ordinary product launches, routine shipment tracking, digests without a concrete action, ordinary cron output, and normal operational chatter.
- Ordinary direct-mail/direct-message items that would belong in `direct-mail` or `mail-for-me`, unless red-hot: urgent, security-relevant, deadline-bearing, financially risky, irreversible, or clearly requiring immediate awareness/action.
- Anything matching `omit_rules` in the state file.

## Durable Omit Rules

The state file owns durable omit rules. Preserve and apply these unless Luke changes them:

- Standard Bank pending authorizations: sender `bph_za@standardbank.co.za`, subject contains `Pending Authorisation`. Luke is only cc/indirectly copied on that account.
- SVB payments awaiting approval: sender `onlinebanking@svb.com`, subject contains `SVB Payment Reminder: Payments Awaiting Approval`.

## Source Guidance

For Gmail:

- Search unread inbox mail newer than the state timestamp.
- Use Gmail links in the output.
- Read full messages only for candidates that look like they may match.

For Outlook:

- List unread messages with `receivedDateTime ge <last_pull_utc>`.
- Prefer list results for previews; fetch full messages only for candidates that need details.
- Use Office 365 web links in the output.

For Slack:

- Search recent Slack activity since `last_pull_utc` using available Slack search/read tools.
- Favor DMs, mentions, threads where Luke is directly addressed, and channels likely to carry incidents, customer escalations, payments, security, legal, compliance, or executive actions.
- Include a Slack item only when it has a concrete urgent signal, action, deadline, risk, or decision for Luke.
- Include channel/thread context in the summary and link to the Slack item when available.

For Granola:

- Use the `granola-call-logs` skill to search meeting notes and transcripts since `last_pull_utc`. That skill searches synced Granola notes and transcripts in Luke's Onafriq Obsidian vault.
- Also use a Granola connector when it is available, but do not treat missing connector tools as missing Granola access until `granola-call-logs` has been tried.
- Include only notes with concrete decisions, commitments, action items, urgent risks, or deadlines matching this skill.
- Summarize the relevant discussion and cite the meeting title/time/link when available.
- If both the `granola-call-logs` skill and connector tools are unavailable in the current session, continue with mail and Slack and mention the source limitation only in the final status when it affects confidence.

## Output

Return newest first. For each matching item include:

- America/New_York local date and time.
- Source label: Gmail, Outlook, Slack, or Granola.
- Subject/title as a link that opens Gmail, Office 365, Slack, or Granola where possible.
- Sender/author/meeting owner.
- Thread-aware summary, including relevant preceding messages or meeting context.
- Recommended action if any.

If no new matching items exist, say so and include the searched window.

For heartbeat runs, use the heartbeat XML decision:

- `NOTIFY` when there are one or more new matching items.
- `DONT_NOTIFY` when there are none, or when the run is outside the active time window.

## State File Shape

Keep the state JSON simple and durable:

```json
{
  "last_pull_utc": "2026-05-08T18:00:21Z",
  "last_pull_local": "2026-05-08 14:00:21 EDT",
  "timezone": "America/New_York",
  "active_window_local": {
    "start": "04:00",
    "end": "18:00"
  },
  "sources": ["gmail", "outlook", "slack", "granola"],
  "omit_rules": []
}
```

Append or edit `omit_rules` when Luke says a sender, subject, Slack source, meeting topic, or recurring item is not relevant in the future.
