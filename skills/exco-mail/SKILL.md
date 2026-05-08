---
name: exco-mail
description: Compatibility wrapper for ExCo Outlook mail monitoring. The canonical ExCo monitoring definition now lives in the exco-interactions skill.
---

# Exco Mail

This skill is a compatibility wrapper. For new work, use `exco-interactions`.

When the user specifically asks for ExCo mail only, use the Outlook source workflow in:

`/Users/luke/dev/luke-agent-scripts/skills/exco-interactions/SKILL.md`

Legacy ExCo mail scope:

- From: `dare.okoudjou@onafriq.com`
- From: `sumayah.kader@onafriq.com`
- From: `rashi.gupta@onafriq.com`
- From: `patrick.gutmann@onafriq.com`
- From: `christian.bwakira@onafriq.com`
- From: `tayo.ogunlade@onafriq.com`
- To: `exco@onafriq.com`

Legacy excluded senders:

- `reports@onafriq.com`
- `onafriq.com@reports.onafriq.com`

Use the state file and output rules from `exco-interactions` unless the user explicitly asks to use the old mail-only state file.
