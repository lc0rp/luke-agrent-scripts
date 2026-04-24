#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


ALIASES = {
    "cards": ["card issuing"],
    "card": ["card issuing"],
    "card issuing": ["card issuing"],
    "agency": ["agency and offline", "agency"],
    "offline": ["agency and offline", "offline"],
    "fx": ["fx finops", "fx"],
    "finops": ["fx finops", "finops"],
    "fx finops": ["fx finops"],
}


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def topic_variants(topic: str) -> list[str]:
    topic_norm = normalize(topic)
    variants = [topic_norm]
    variants.extend(ALIASES.get(topic_norm, []))
    return list(dict.fromkeys(variant for variant in variants if variant))


def spec_project_name(text: str) -> str | None:
    match = re.search(r"-\s*`<project-name>`:\s*`([^`]+)`", text)
    return match.group(1).strip() if match else None


def discover_specs(vault: Path) -> list[Path]:
    return sorted(
        path
        for path in vault.rglob("*.md")
        if normalize(path.stem).endswith("weekly ceo brief")
    )


def score_spec(path: Path, topic: str) -> tuple[int, dict[str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    project = spec_project_name(text) or ""
    haystacks = {
        "project": normalize(project),
        "filename": normalize(path.stem),
        "parent": normalize(" ".join(part for part in path.parts[-5:-1])),
    }
    score = 0
    for topic_norm in topic_variants(topic):
        for key, value in haystacks.items():
            if value == topic_norm:
                score += 100
            elif topic_norm and topic_norm in value:
                score += 40
            elif any(token in value.split() for token in topic_norm.split()):
                score += 10
    return score, {"project": project}


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve a CEO brief topic to a spec note.")
    parser.add_argument("topic", nargs="?")
    parser.add_argument("--vault", default=".", help="Vault root. Defaults to current directory.")
    parser.add_argument("--list", action="store_true", help="List available brief topics.")
    parser.add_argument("--help-command", action="store_true", help="Print brief command help.")
    args = parser.parse_args()

    if args.help_command:
        print("Usage: brief <topic> [days|last]")
        print("Examples: brief AI 7, brief Cards 1, brief Stablecoin last, brief list topics")
        print("Default duration: 7 days")
        return 0

    vault = Path(args.vault).expanduser().resolve()
    specs = discover_specs(vault)

    if args.list:
        for spec in specs:
            text = spec.read_text(encoding="utf-8", errors="replace")
            project = spec_project_name(text) or spec.stem.replace(" Weekly CEO brief", "")
            rel = spec.relative_to(vault)
            print(f"{project}\t{rel}")
        return 0

    if not args.topic:
        parser.error("topic is required unless --list or --help-command is used")

    matches = []
    for spec in specs:
        score, metadata = score_spec(spec, args.topic)
        if score > 0:
            matches.append((score, spec, metadata))

    matches.sort(key=lambda item: (-item[0], str(item[1])))
    for score, spec, metadata in matches:
        rel = spec.relative_to(vault)
        project = metadata.get("project") or ""
        print(f"{score}\t{project}\t{rel}")

    return 0 if matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
