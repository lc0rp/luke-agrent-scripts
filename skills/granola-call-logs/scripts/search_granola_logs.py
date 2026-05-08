#!/usr/bin/env python3
"""Search Granola meeting summaries and transcripts in Luke's Onafriq daily notes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


DEFAULT_VAULT = Path("/Users/luke/Documents/Obsidian-Onafriq")
DAILY_FOLDER = Path("2-Areas/Journaling/Daily")
DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


@dataclass
class Meeting:
    date: date
    title: str
    summary_path: Path | None
    transcript_path: Path | None
    summary_text: str = ""
    transcript_text: str = ""
    granola_id: str | None = None
    matched_terms: list[str] = field(default_factory=list)
    matched_title_terms: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--start-date", required=True, help="Inclusive YYYY-MM-DD start date.")
    parser.add_argument("--end-date", help="Inclusive YYYY-MM-DD end date.")
    parser.add_argument("--keywords", action="append", default=[], help="Keyword/topic filter. Repeatable; comma-separated accepted.")
    parser.add_argument("--people", action="append", default=[], help="People filter. Repeatable; comma-separated accepted.")
    parser.add_argument("--topics", action="append", default=[], help="Topic/project filter. Repeatable; comma-separated accepted.")
    parser.add_argument("--titles", action="append", default=[], help="Meeting title filter. Repeatable; comma-separated accepted.")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    return parser.parse_args()


def split_terms(values: list[str]) -> list[str]:
    terms: list[str] = []
    for value in values:
        for part in value.split(","):
            term = part.strip()
            if term:
                terms.append(term)
    return terms


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid date {value!r}; expected YYYY-MM-DD.") from exc


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def date_from_path(path: Path) -> date | None:
    match = DATE_RE.search(str(path))
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def resolve_wikilink(vault: Path, raw_link: str | None) -> Path | None:
    if not raw_link:
        return None
    match = re.search(r"\[\[(.*?)\]\]", raw_link)
    if not match:
        return None
    target = match.group(1).split("|", 1)[0]
    if not target.endswith(".md"):
        target = f"{target}.md"
    path = vault / target
    return path if path.exists() else None


def normalize(value: str) -> str:
    return value.casefold()


def term_matches(term: str, haystack: str) -> bool:
    return normalize(term) in normalize(haystack)


def find_meetings(vault: Path, start: date, end: date | None, terms: list[str], title_terms: list[str]) -> list[Meeting]:
    root = vault / DAILY_FOLDER
    if not root.exists():
        raise SystemExit(f"Daily notes folder not found: {root}")

    meetings: list[Meeting] = []
    seen: set[Path] = set()
    seen_transcripts: set[Path] = set()
    for path in sorted(root.rglob("*.md")):
        if path.name.endswith("-transcript.md"):
            continue
        text = read_text(path)
        meta = frontmatter(text)
        if "granola_id" not in meta and "notes.granola.ai" not in text:
            continue
        meeting_date = date_from_path(path)
        if meeting_date is None or meeting_date < start or (end and meeting_date > end):
            continue

        title = meta.get("title") or path.stem
        transcript_path = resolve_wikilink(vault, meta.get("transcript"))
        if transcript_path is None:
            sibling = path.with_name(f"{path.stem}-transcript.md")
            transcript_path = sibling if sibling.exists() else None
        transcript_text = read_text(transcript_path) if transcript_path else ""
        if transcript_path:
            seen_transcripts.add(transcript_path)
        search_text = "\n".join([title, path.name, text, transcript_text])

        matched_title_terms = [term for term in title_terms if term_matches(term, f"{title} {path.name}")]
        matched_terms = [term for term in terms if term_matches(term, search_text)]
        if title_terms and not matched_title_terms:
            continue
        if terms and not matched_terms:
            continue

        seen.add(path)
        meetings.append(
            Meeting(
                date=meeting_date,
                title=title,
                summary_path=path.relative_to(vault),
                transcript_path=transcript_path.relative_to(vault) if transcript_path else None,
                summary_text=text,
                transcript_text=transcript_text,
                granola_id=meta.get("granola_id"),
                matched_terms=matched_terms,
                matched_title_terms=matched_title_terms,
            )
        )

    for path in sorted(root.rglob("*-transcript.md")):
        if path in seen or path in seen_transcripts:
            continue
        text = read_text(path)
        meta = frontmatter(text)
        if "granola_id" not in meta:
            continue
        meeting_date = date_from_path(path)
        if meeting_date is None or meeting_date < start or (end and meeting_date > end):
            continue
        title = meta.get("title") or path.stem
        search_text = "\n".join([title, path.name, text])
        matched_title_terms = [term for term in title_terms if term_matches(term, f"{title} {path.name}")]
        matched_terms = [term for term in terms if term_matches(term, search_text)]
        if title_terms and not matched_title_terms:
            continue
        if terms and not matched_terms:
            continue
        meetings.append(
            Meeting(
                date=meeting_date,
                title=title,
                summary_path=None,
                transcript_path=path.relative_to(vault),
                transcript_text=text,
                granola_id=meta.get("granola_id"),
                matched_terms=matched_terms,
                matched_title_terms=matched_title_terms,
            )
        )
    return meetings


def excerpt(text: str) -> str:
    for heading in ("### Action Items", "### Next Steps", "### Decisions", "### Open Questions"):
        index = text.find(heading)
        if index >= 0:
            chunk = text[index : index + 700]
            return " ".join(chunk.split())
    body = FRONTMATTER_RE.sub("", text).strip()
    return " ".join(body.split()[:70])


def as_json(meetings: list[Meeting], vault: Path) -> str:
    payload = []
    for meeting in meetings:
        payload.append(
            {
                "date": meeting.date.isoformat(),
                "title": meeting.title,
                "granola_id": meeting.granola_id,
                "summary_path": str(meeting.summary_path) if meeting.summary_path else None,
                "transcript_path": str(meeting.transcript_path) if meeting.transcript_path else None,
                "matched_terms": meeting.matched_terms,
                "matched_title_terms": meeting.matched_title_terms,
                "excerpt": excerpt(meeting.summary_text or meeting.transcript_text),
            }
        )
    return json.dumps(payload, indent=2, ensure_ascii=False)


def as_markdown(meetings: list[Meeting], vault: Path) -> str:
    lines = [f"Found {len(meetings)} Granola meeting(s)."]
    for meeting in meetings:
        source = meeting.summary_path or meeting.transcript_path
        transcript = f"; transcript: `{meeting.transcript_path}`" if meeting.transcript_path else ""
        terms = ", ".join(meeting.matched_title_terms + meeting.matched_terms) or "date match"
        lines.append("")
        lines.append(f"- {meeting.date.isoformat()} | {meeting.title}")
        lines.append(f"  Source: `{source}`{transcript}")
        lines.append(f"  Matched: {terms}")
        ex = excerpt(meeting.summary_text or meeting.transcript_text)
        if ex:
            lines.append(f"  Excerpt: {ex}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    start = parse_date(args.start_date)
    end = parse_date(args.end_date) if args.end_date else None
    if end and end < start:
        raise SystemExit("--end-date must be on or after --start-date.")

    terms = split_terms(args.keywords + args.people + args.topics)
    title_terms = split_terms(args.titles)
    meetings = find_meetings(args.vault, start, end, terms, title_terms)
    meetings = meetings[: args.limit]
    print(as_json(meetings, args.vault) if args.json else as_markdown(meetings, args.vault))
    return 0


if __name__ == "__main__":
    sys.exit(main())
