---
name: exco-mail
description: Fetch and summarize unarchived Outlook mail from Onafriq executive senders or to exco@onafriq.com, excluding BI report senders, with since-last-pull state and Office 365 links.
---

# Exco Mail

Use this skill when asked to fetch, pull, summarize, monitor, or triage Outlook mail involving:

- From: `dare.okoudjou@onafriq.com`
- From: `sumayah.kader@onafriq.com`
- From: `rashi.gupta@onafriq.com`
- From: `patrick.gutmann@onafriq.com`
- From: `christian.bwakira@onafriq.com`
- From: `tayo.ogunlade@onafriq.com`
- To: `exco@onafriq.com`

## Filters

Always exclude these senders:

- `reports@onafriq.com`
- `onafriq.com@reports.onafriq.com`

Only include unarchived mail. Prefer explicit non-Archive folders or folder metadata when available. If the available connector does not expose archive state, use the default Outlook message search/listing and state the limitation briefly.

## Time Window

Use `America/New_York` local time unless the user specifies another timezone.

- If the user gives a date or date range, use that exact date window.
- If no date is given and a pull-state file is available, search only messages received after `last_pull_utc`.
- If no date is given and no state is available, search the current local day from `00:00`.

Default state file: `outlook-pull-state.json` in the active workspace. Update it after each successful run with:

- `last_pull_utc`
- `last_pull_local`
- `default_timezone`
- `filters.from`
- `filters.to`
- `filters.exclude_from`

## Search Procedure

Prefer the Microsoft Outlook Email connector when available because it returns Office 365 links.

1. Read the state file if present.
2. Build the UTC received window from the requested/local date or `last_pull_utc`.
3. Query the listed `from` addresses and `to:exco@onafriq.com`.
4. Filter out excluded senders and duplicates by Outlook message ID.
5. Fetch full messages only for matched items where thread context or action judgment needs more than the preview.
6. Sort newest first by received time.
7. Update the state file after the pull succeeds.

If connector filter syntax fails for `toRecipients`, search for `exco@onafriq.com`, fetch candidate messages, and keep only messages where the actual `toRecipients` includes `exco@onafriq.com`.

## Output

Return a concise list. For each email include:

- Local date/time, newest first.
- Subject as an Office 365 link.
- Sender or recipient match.
- Summary of the current email plus preceding messages in the thread.
- Recommended action when the email needs one.

If there are no new matches, say so with the searched time window.
