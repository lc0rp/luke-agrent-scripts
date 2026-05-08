---
name: granola-call-logs
description: Search Luke's Onafriq Obsidian vault for Granola meeting notes and transcripts in daily notes. Use whenever the user asks for Granola meeting call logs, meeting notes/transcripts from Obsidian daily notes, meeting evidence after a date, or wants calendar/mail/Slack summaries sharpened with Granola logs. Handles exact-day and on-or-after date windows plus keywords, topics, titles, people, projects, and counterparties.
---

# Granola Call Logs

Search Granola meeting notes synced into Luke's private Onafriq Obsidian vault, then use the matching summaries and transcripts as evidence for the requested output.

## Source

- Vault root: `/Users/luke/Documents/Obsidian-Onafriq`
- Daily notes folder: `2-Areas/Journaling/Daily`
- qmd collection: `onafriq-notes`

Each Granola meeting usually has:

- a summary note with frontmatter `granola_id`, `type: note`, and a `transcript` wikilink
- a sibling transcript note ending in `-transcript.md` with `type: transcript`

## Triggered Output

Shape the final output to the user's context. Typical outputs include:

- meeting call log list
- brief source notes
- decisions/actions/open questions summary
- supporting evidence for calendar, mail, Slack, or vault synthesis

Use this source block when presenting the search scope:

```markdown
Granola Meeting Call Logs:
#### Filters
- Start date: <from context>
- Daily notes folder: `2-Areas/Journaling/Daily`
- Keywords, People, Topics: <from context>
- Titles: <from context>
#### Guidelines
- Search the daily notes folder by day on or after `<start-date>`
- Filter on both note title and note content using project, topic, people and counterparty keywords
- Use both the meeting transcript and the Granola summary sections when present
- Prioritize decisions, actions, owners, open questions, and committed next steps over general discussion
- Use Granola logs to sharpen summaries of meetings that also appear in calendar, mail, Slack sources, or other context sources
```

## Workflow

1. Parse the user request for:
   - exact day, start date, end date, or implicit window
   - keywords, topics, projects, counterparties, and people
   - title fragments or named meetings
   - desired output format
2. If the user gives a single day and the context does not require a range, search only that day.
3. If the user asks for "since", "after", "from", "latest", weekly brief support, or cross-source synthesis, search on or after the start date. Add an end date when the request provides one.
4. Run the helper first for deterministic candidate collection:

```bash
python3 /Users/luke/dev/luke-agent-scripts/skills/granola-call-logs/scripts/search_granola_logs.py \
  --start-date YYYY-MM-DD \
  --keywords "keyword or topic" \
  --people "Person Name" \
  --titles "Meeting title fragment" \
  --limit 20
```

5. If helper results look incomplete, run qmd keyword search against `onafriq-notes` and restrict accepted results back to `2-Areas/Journaling/Daily` and the requested date window:

```bash
qmd search "keyword person topic title" -c onafriq-notes -n 20 --json
```

6. Read the matched summary notes and their transcripts. Use the summary for structure; use the transcript to verify decisions, owners, deadlines, and nuanced wording.
7. Deduplicate summary/transcript pairs by `granola_id` or summary path.
8. Synthesize the requested output. Favor decisions, actions, owners, open questions, commitments, dates, blockers, risks, and explicit next steps.

## Search Rules

- Match date from the path or filename using `YYYY-MM-DD`.
- Match titles against frontmatter `title` and filename.
- Match keywords, topics, people, projects, and counterparties against both summary and transcript content.
- Treat title filters as strong filters: if titles are provided, a meeting should usually match at least one title fragment unless content evidence clearly proves it is the named meeting.
- Treat keyword/topic/person filters as additive evidence. Use judgement when a person appears in transcript filler but the meeting is plainly about another topic.
- Include transcript-only results only when no linked summary note exists or when the transcript contains the decisive evidence.

## Evidence Discipline

- Cite local sources as `[Granola] path/to/note.md` or `[Granola transcript] path/to/transcript.md`.
- When making a claim about a decision or commitment, prefer a source where the summary and transcript agree.
- If the transcript contradicts or weakens the summary, say so briefly.
- Do not expose large transcript excerpts. Quote only short phrases when they materially change interpretation.
- Respect vault privacy. Do not share vault contents outside Luke's 1:1 assistant context.

## Final Response Patterns

For call logs:

```markdown
Granola Meeting Call Logs
Window: YYYY-MM-DD to YYYY-MM-DD
Filters: <keywords/topics/people/titles>

- YYYY-MM-DD, <title>: <1 sentence outcome>. Source: [Granola] <path>
  Actions: <owner -> action, or "None explicit.">
  Open questions: <items, or "None explicit.">
```

For synthesis:

```markdown
Granola evidence checked: <N> meetings from <date window>.

Decisions:
- ...

Actions:
- ...

Open questions:
- ...

Source gaps: <missing dates, weak matches, or "None surfaced.">
```

Keep the final answer concise unless Luke asks for the full extraction.
