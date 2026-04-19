#!/usr/bin/env python3
"""List and replace text in PPTX slides without third-party dependencies.

This script is intentionally narrow:
- inspect slide text so the operator can see exact placeholder strings
- replace text in slide text bodies by exact or contains matching

It edits slide XML directly inside the PPTX zip so it can run on a minimal host.
It is safe for template-copy workflows where the deck has already been duplicated.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "xml": "http://www.w3.org/XML/1998/namespace",
}

for prefix, uri in NS.items():
    if prefix != "xml":
        ET.register_namespace(prefix, uri)


def qname(prefix: str, tag: str) -> str:
    return f"{{{NS[prefix]}}}{tag}"


def slide_members(zf: ZipFile) -> list[str]:
    return sorted(
        [
            name
            for name in zf.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        ],
        key=lambda name: int(Path(name).stem.replace("slide", "")),
    )


def paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []
    for child in list(paragraph):
        if child.tag == qname("a", "r"):
            text_node = child.find("a:t", NS)
            if text_node is not None and text_node.text:
                parts.append(text_node.text)
        elif child.tag == qname("a", "br"):
            parts.append("\n")
        elif child.tag == qname("a", "fld"):
            text_node = child.find("a:t", NS)
            if text_node is not None and text_node.text:
                parts.append(text_node.text)
    return "".join(parts)


def text_body_text(text_body: ET.Element) -> str:
    lines = [paragraph_text(paragraph) for paragraph in text_body.findall("a:p", NS)]
    return "\n".join(line for line in lines if line != "")


@dataclass
class TextContainer:
    slide_number: int
    kind: str
    name: str
    element: ET.Element
    text_body: ET.Element
    text: str


def iter_text_containers(slide_root: ET.Element, slide_number: int) -> Iterable[TextContainer]:
    shape_index = 0
    for shape in slide_root.findall(".//p:sp", NS):
        text_body = shape.find("p:txBody", NS)
        if text_body is None:
            continue
        text = text_body_text(text_body).strip()
        if not text:
            continue
        c_nv_pr = shape.find("p:nvSpPr/p:cNvPr", NS)
        shape_index += 1
        name = (
            c_nv_pr.get("name")
            if c_nv_pr is not None and c_nv_pr.get("name")
            else f"shape-{shape_index}"
        )
        yield TextContainer(
            slide_number=slide_number,
            kind="shape",
            name=name,
            element=shape,
            text_body=text_body,
            text=text,
        )

    table_index = 0
    for cell in slide_root.findall(".//a:tc", NS):
        text_body = cell.find("a:txBody", NS)
        if text_body is None:
            continue
        text = text_body_text(text_body).strip()
        if not text:
            continue
        table_index += 1
        yield TextContainer(
            slide_number=slide_number,
            kind="table-cell",
            name=f"table-cell-{table_index}",
            element=cell,
            text_body=text_body,
            text=text,
        )


def rewrite_text_body(text_body: ET.Element, replacement: str) -> None:
    paragraphs = text_body.findall("a:p", NS)
    first_paragraph = paragraphs[0] if paragraphs else None
    first_p_pr = first_paragraph.find("a:pPr", NS) if first_paragraph is not None else None
    first_end_para = (
        first_paragraph.find("a:endParaRPr", NS) if first_paragraph is not None else None
    )
    first_run_pr = None
    if first_paragraph is not None:
        first_run = first_paragraph.find("a:r", NS)
        if first_run is not None:
            first_run_pr = first_run.find("a:rPr", NS)

    for paragraph in list(text_body.findall("a:p", NS)):
        text_body.remove(paragraph)

    for line in replacement.split("\n"):
        paragraph = ET.SubElement(text_body, qname("a", "p"))
        if first_p_pr is not None:
            paragraph.append(copy.deepcopy(first_p_pr))
        run = ET.SubElement(paragraph, qname("a", "r"))
        if first_run_pr is not None:
            run.append(copy.deepcopy(first_run_pr))
        text_node = ET.SubElement(run, qname("a", "t"))
        if line[:1].isspace() or line[-1:].isspace():
            text_node.set(f"{{{NS['xml']}}}space", "preserve")
        text_node.text = line
        if first_end_para is not None:
            paragraph.append(copy.deepcopy(first_end_para))


def list_command(args: argparse.Namespace) -> int:
    deck = Path(args.deck).expanduser().resolve()
    with ZipFile(deck, "r") as zf:
        for member in slide_members(zf):
            slide_number = int(Path(member).stem.replace("slide", ""))
            root = ET.fromstring(zf.read(member))
            containers = list(iter_text_containers(root, slide_number))
            if not containers:
                continue
            if args.json:
                payload = [
                    {
                        "slide": container.slide_number,
                        "kind": container.kind,
                        "name": container.name,
                        "text": container.text,
                    }
                    for container in containers
                ]
                print(json.dumps(payload, ensure_ascii=False))
            else:
                print(f"--- slide {slide_number} ---")
                for container in containers:
                    print(f"[{container.kind}] {container.name}")
                    print(container.text)
                    print()
    return 0


def load_rules(spec_path: Path) -> list[dict]:
    payload = json.loads(spec_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("rules"), list):
        return payload["rules"]
    raise ValueError("Replacement spec must be a JSON array or an object with a 'rules' array.")


def container_matches(container: TextContainer, rule: dict) -> bool:
    if int(rule["slide"]) != container.slide_number:
        return False
    if "kind" in rule and rule["kind"] != container.kind:
        return False
    if "name" in rule and rule["name"] != container.name:
        return False
    match_mode = rule.get("mode", "exact")
    target = rule["match"]
    if match_mode == "exact":
        return container.text == target
    if match_mode == "contains":
        return target in container.text
    raise ValueError(f"Unsupported rule mode: {match_mode}")


def apply_command(args: argparse.Namespace) -> int:
    input_deck = Path(args.input_deck).expanduser().resolve()
    output_deck = Path(args.output_deck).expanduser().resolve()
    spec_path = Path(args.spec).expanduser().resolve()
    rules = load_rules(spec_path)
    if not rules:
        raise ValueError("Replacement spec has no rules.")

    slide_xml: dict[str, ET.Element] = {}
    matched_rules = [0 for _ in rules]

    with ZipFile(input_deck, "r") as source_zip:
        slide_names = slide_members(source_zip)
        for member in slide_names:
            root = ET.fromstring(source_zip.read(member))
            slide_number = int(Path(member).stem.replace("slide", ""))
            containers = list(iter_text_containers(root, slide_number))
            for index, rule in enumerate(rules):
                hits = [container for container in containers if container_matches(container, rule)]
                if len(hits) > 1:
                    raise ValueError(
                        f"Rule {index} matched multiple containers on slide {slide_number}; "
                        "add a more specific 'name' field."
                    )
                if len(hits) == 1:
                    rewrite_text_body(hits[0].text_body, rule["replace"])
                    matched_rules[index] += 1
            slide_xml[member] = root

        for index, count in enumerate(matched_rules):
            if count == 0:
                raise ValueError(f"Rule {index} did not match anything: {rules[index]}")
            if count > 1:
                raise ValueError(f"Rule {index} matched more than once: {rules[index]}")

        with ZipFile(output_deck, "w", compression=ZIP_DEFLATED) as output_zip:
            for info in source_zip.infolist():
                data = source_zip.read(info.filename)
                if info.filename in slide_xml:
                    data = ET.tostring(slide_xml[info.filename], encoding="utf-8", xml_declaration=False)
                output_zip.writestr(info, data)

    print(f"Wrote {output_deck}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List visible text by slide.")
    list_parser.add_argument("deck", help="Path to the source PPTX.")
    list_parser.add_argument("--json", action="store_true", help="Emit JSON lines instead of plain text.")
    list_parser.set_defaults(func=list_command)

    apply_parser = subparsers.add_parser("apply", help="Apply replacements from a JSON spec.")
    apply_parser.add_argument("input_deck", help="Path to the input PPTX.")
    apply_parser.add_argument("spec", help="Path to the JSON replacement spec.")
    apply_parser.add_argument("output_deck", help="Path to the output PPTX.")
    apply_parser.set_defaults(func=apply_command)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except Exception as exc:  # pragma: no cover - CLI guard
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
