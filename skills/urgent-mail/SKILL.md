---
name: urgent-mail
description: Fetch and triage unarchived Outlook and Gmail messages Luke might want to know about, including urgent automated mail, mailing-list mail, security notices, deadlines, expiring accounts, payments due, tax deadlines, kid/family event notices, and Lydia messages, with since-last-pull state and Office 365/Gmail links.
---

# Urgent/FYI Mail

Use this skill when asked to fetch, pull, check, monitor, summarize, or triage Outlook or Gmail for red-alert mail or FYI mail Luke might want to know about.

This skill intentionally has broader intake than `direct-mail`: automated messages, mailing-list messages, alerts, and messages where Luke is not explicitly in `To` may qualify if they meet the priority bar.

Avoid duplicating `direct-mail`: if an item would normally be included by `direct-mail`, include it here only when it is red-hot: urgent, security-relevant, deadline-bearing, financially risky, irreversible, or clearly requiring immediate awareness/action.

## Identity

Luke's addresses:

- `luke.kyohere@onafriq.com`
- `luke@beyonic.com`
- `luke@kyohere.com`
- `luke.kyohere@gmail.com`

Family and priority names:

- Linden
- Leona
- Lydia McClure, `lydia.mcclure@gmail.com`

## Include Bar

Include unarchived mail that appears urgent, security-relevant, deadline-bearing, or personally important enough that Luke might want to know.

Strong include signals:

- Payments due, overdue, failed, declined, expiring cards, final notices, collections, or invoices with near-term deadlines.
- Tax deadlines, filing notices, government notices, compliance deadlines, legal deadlines, or penalty warnings.
- Events, school, medical, travel, or logistics involving Linden or Leona.
- Any email from Lydia McClure.
- Security issues: suspicious login, password reset not initiated by Luke, MFA/2FA changes, compromised account, account lockout, data breach, account access, domain/DNS/certificate problems, chargeback/fraud, or urgent vulnerability notices.
- Accounts, domains, subscriptions, storage, benefits, or services expiring, being deleted, disabled, suspended, downgraded, or requiring action.
- Anything with a concrete deadline that seems soon, missed, expensive, irreversible, or risky.
- Serious work-impacting outages, escalations, delivery failures, contract/customer issues, or executive/legal/finance matters that clearly need awareness.

Weak include signals:

- Automated, mailing-list, report, alert, receipt, confirmation, or notification mail may qualify only when it carries a strong include signal.
- Marketing urgency words alone do not qualify.
- Generic newsletters, product announcements, discounts, sales, cold outreach, PR, recruiting, and noisy SaaS alerts do not qualify unless the message itself creates a clear deadline, risk, or action for Luke.
- Direct messages that are simply useful, work-relevant, or addressed to Luke belong in `direct-mail`; keep them out of `urgent-mail` unless red-hot.

## Hard Filters

Include only unarchived mail.

Exclude:

- Read mail.
- Mail Luke has replied to, unless there is a newer inbound message after Luke's reply.
- Spam and likely phishing. Do not include suspicious mail as FYI/Urgent unless the security risk is specifically about one of Luke's real accounts or organizations and the message itself appears legitimate enough to inspect.
- Messages matching durable omit rules in the state file.

When Luke says a sender, subject, topic, biller, or email is not relevant to this task, add a durable omit rule and use it in future pulls.

## Time Window

Use `America/New_York` local time unless the user specifies another timezone.

- If the user gives a date or date range, use that exact local date window.
- If no date is given and a pull-state file is available, search only messages received after `last_pull_utc`.
- If no date is given and no state exists, search the current local day from `00:00`.

Default state file in the active workspace: `urgent-mail-state.json`.

After a successful pull, update:

- `last_pull_utc`
- `last_pull_local`
- `timezone`
- `default_scope`
- `omit_rules`
- `last_seen_provider_ids` when useful for dedupe

## Search Procedure

Use the Gmail connector for Gmail and Microsoft Outlook Email connector for Outlook. Prefer connector-native links in the final output.

1. Read `urgent-mail-state.json` if present.
2. Build the received window.
3. Search unread, unarchived Gmail and Outlook mail for the window. Use Inbox/non-Archive folder semantics where the connector exposes them.
4. Do not require Luke to be in `To`; include CC, BCC, list, forwarded, alias, automated, and notification mail if it meets the include bar.
5. Run targeted searches for strong signals if a broad unread inbox pull may miss items: Lydia, Linden, Leona, due/overdue/deadline, tax, security, suspicious login, password, MFA, account expiring/deleting/suspended, payment failed, final notice.
6. Suppress items that would be ordinary `direct-mail` matches unless they are red-hot by this skill's include bar.
7. Remove read items and messages already replied to by Luke unless the latest message is inbound after Luke's reply. When connector summaries are insufficient, fetch the message or thread.
8. Deduplicate by provider message/thread ID.
9. Apply spam, phishing, weak-signal, and omit filters.
10. Fetch full bodies or threads only for shortlisted items where context/action judgment needs more than the preview.
11. Sort newest first by local received time.
12. Update the state file only after the pull succeeds.

## Output

Return a concise list, newest first. For each kept email include:

- Local date/time.
- Subject linked to Office 365 or Gmail.
- Sender.
- Summary of the current email plus relevant preceding thread context.
- Recommended action if one is needed.

Also briefly state:

- Search window.
- Any important exclusions or connector limitations.
- If there are no matching messages.

Do not include a filtered-out item unless Luke asks for audit/debug details.
