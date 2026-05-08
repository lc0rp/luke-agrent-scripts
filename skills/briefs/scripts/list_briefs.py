#!/usr/bin/env python3
import argparse
import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_VAULT = Path("/Users/luke/Documents/Obsidian-Onafriq")
DATED_BRIEF_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(.+?)\s+CEO brief\.md$", re.IGNORECASE)


@dataclass(frozen=True)
class Brief:
    date: str
    topic: str
    path: Path


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def find_briefs(vault: Path) -> list[Brief]:
    briefs: list[Brief] = []
    for path in vault.rglob("*.md"):
        match = DATED_BRIEF_RE.match(path.name)
        if not match:
            continue
        date, topic = match.groups()
        briefs.append(Brief(date=date, topic=topic, path=path))
    return sorted(briefs, key=lambda brief: (brief.date, brief.topic.lower()), reverse=True)


def latest_per_topic(briefs: list[Brief]) -> list[Brief]:
    latest: dict[str, Brief] = {}
    for brief in briefs:
        key = normalize(brief.topic)
        if key not in latest:
            latest[key] = brief
    return sorted(latest.values(), key=lambda brief: (brief.date, brief.topic.lower()), reverse=True)


def markdown_link(brief: Brief) -> str:
    label = brief.path.name
    target = str(brief.path)
    if " " in target:
        return f"[{label}](<{target}>)"
    return f"[{label}]({target})"


def main() -> int:
    parser = argparse.ArgumentParser(description="List generated CEO briefs.")
    parser.add_argument("--vault", default=str(DEFAULT_VAULT), help="Vault root.")
    parser.add_argument("--topic", help="Filter by topic.")
    parser.add_argument("--all", action="store_true", help="List all dated briefs, not just the latest per topic.")
    args = parser.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    briefs = find_briefs(vault)
    if args.topic:
        topic_norm = normalize(args.topic)
        briefs = [brief for brief in briefs if topic_norm in normalize(brief.topic)]
    if not args.all:
        briefs = latest_per_topic(briefs)

    if not briefs:
        print(f"No generated CEO briefs found in {vault}")
        return 1

    for brief in briefs:
        print(f"- {brief.date} | {brief.topic} | {markdown_link(brief)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

