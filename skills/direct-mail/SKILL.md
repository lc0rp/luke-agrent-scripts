---
name: direct-mail
description: Compatibility wrapper for direct mail monitoring. The canonical direct monitoring definition now lives in the direct-interactions skill.
---

# Direct Mail

This skill is a compatibility wrapper. For new work, use `direct-interactions`.

When the user specifically asks for mail only, use the Gmail and Outlook source workflow in:

`/Users/luke/dev/luke-agent-scripts/skills/direct-interactions/SKILL.md`

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

## Hard Filters

Include only unarchived mail.

Exclude:

- Read mail.
- Mail Luke has replied to, unless there is a newer inbound message after Luke's reply.
- Automated mail: mailing lists, system alerts, receipts, confirmations, digests, newsletters, subscriptions, alerts, CI/Jira/GitHub/Bitbucket notifications, OTPs, bank authorization notices, generic reports, and calendar noise unless clearly urgent.
- Spam and cold outreach. In particular, when sender domain is not `onafriq.com`, exclude likely cold email if it is not part of an existing thread, not initiated by Luke, not a referral, sounds generic, has unsubscribe/marketing tracking, or raises spam flags.
- Any sender, subject, or topic listed in the local omit rules.

CC handling:

- If Luke is explicitly in `cc`, include only if it appears of utmost importance.
- Broad distribution lists, review-only reports, FYIs, and informational CCs do not meet the bar.

## Time Window

Use `America/New_York` local time unless the user specifies another timezone.

- If the user gives a date or date range, use that exact local date window.
- If no date is given and a pull-state file is available, search Gmail and Outlook messages received after the relevant source cursor.
- If no date is given and no state exists, search the current local day from `00:00`.

Default canonical state file:

`/Users/luke/work/direct-interactions/direct-interactions-state.json`

After a successful pull, update:

- `sources.gmail.last_pull_utc`
- `sources.gmail.last_pull_local`
- `sources.outlook.last_pull_utc`
- `sources.outlook.last_pull_local`
- `omit_rules`

When Luke says a sender, subject, topic, or email is not relevant, add a durable omit rule to the state file and use it in future pulls.

## Search Procedure

Use the Gmail connector for Gmail and Microsoft Outlook Email connector for Outlook. Prefer connector-native links in the final output.

1. Read `/Users/luke/work/direct-interactions/direct-interactions-state.json` if present.
2. Build each source's received window from `sources.gmail.last_pull_utc` and `sources.outlook.last_pull_utc`.
3. Search direct recipients for Luke's addresses.
4. Search mention forms in subject/body.
5. Separately search CC matches, then keep only utmost-importance items.
6. Remove read items and messages already replied to by Luke unless the latest message is inbound after Luke's reply. When connector summaries are insufficient, fetch the message or thread.
7. Deduplicate by provider message/thread ID.
8. Apply hard filters and omit rules.
9. Fetch full bodies or threads only for shortlisted items where context/action judgment needs more than the preview.
10. Sort newest first by local received time.
11. Update the state file only after the pull succeeds.

## Output

Return a concise list, newest first. For each kept email include:

- Local date/time.
- Subject linked to Office 365 or Gmail.
- Summary of the current email plus relevant preceding thread context.
- Recommended action if one is needed.

Also briefly state:

- Search window.
- Any important exclusions or connector limitations.
- If there are no matching messages.

Do not include a filtered-out item unless Luke asks for audit/debug details.
