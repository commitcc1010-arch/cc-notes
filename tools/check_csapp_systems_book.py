#!/usr/bin/env python3
"""Content and structure quality gate for the enriched CS:APP book."""
from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from csapp_practical_examples import EXAMPLES
from csapp_supplement_part01 import SUPPLEMENTS as PART01
from csapp_supplement_part02 import SUPPLEMENTS as PART02
from csapp_supplement_part03 import SUPPLEMENTS as PART03


ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "CSAPP_系統思維學習手冊.html"
SUPPLEMENTS = PART01 + PART02 + PART03
CHAPTER_IDS = [item.section_id for item in SUPPLEMENTS]


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.external_assets: list[str] = []
        self.all_text: list[str] = []
        self.section_stack: list[dict] = []
        self.section_markers: list[bool] = []
        self.sections: dict[str, dict] = {}
        self.details_stack: list[dict] = []
        self.details: list[dict] = []

    @property
    def section(self) -> dict | None:
        return self.section_stack[-1] if self.section_stack else None

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_list}
        classes = set(attrs.get("class", "").split())
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if attrs.get("href"):
            self.hrefs.append(attrs["href"])
        if attrs.get("src", "").startswith(("http://", "https://", "//")):
            self.external_assets.append(attrs["src"])

        if tag == "section":
            has_id = bool(attrs.get("id"))
            self.section_markers.append(has_id)
            if has_id:
                data = {
                    "id": attrs["id"],
                    "text": [],
                    "details": 0,
                    "deep_qas": 0,
                    "terms": 0,
                    "diagrams": 0,
                    "contracts": 0,
                    "practical": 0,
                    "python_examples": 0,
                    "transfers": 0,
                }
                self.section_stack.append(data)
                self.sections[attrs["id"]] = data

        if self.section is not None:
            if tag == "details":
                self.section["details"] += 1
                if "deep-qa" in classes:
                    self.section["deep_qas"] += 1
                detail = {"section": self.section["id"], "text": []}
                self.details_stack.append(detail)
                self.details.append(detail)
            if "deep-term" in classes:
                self.section["terms"] += 1
            if "diagram" in classes:
                self.section["diagrams"] += 1
            if "chapter-contract" in classes:
                self.section["contracts"] += 1
            if "practical-layer" in classes:
                self.section["practical"] += 1
            if "python-example" in classes:
                self.section["python_examples"] += 1
            if "transfer-card" in classes:
                self.section["transfers"] += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "details" and self.details_stack:
            self.details_stack.pop()
        if tag == "section" and self.section_markers:
            had_id = self.section_markers.pop()
            if had_id and self.section_stack:
                self.section_stack.pop()

    def handle_data(self, data: str) -> None:
        self.all_text.append(data)
        if self.section is not None:
            self.section["text"].append(data)
        if self.details_stack:
            self.details_stack[-1]["text"].append(data)


def main() -> int:
    problems: list[str] = []
    notes: list[str] = []
    if not BOOK.exists():
        print(f"FAIL: missing {BOOK}")
        return 1
    source = BOOK.read_text(encoding="utf-8")
    parser = Parser()
    parser.feed(source)

    duplicate_ids = [key for key, count in Counter(parser.ids).items() if count > 1]
    if duplicate_ids:
        problems.append("duplicate ids: " + ", ".join(duplicate_ids[:10]))
    ids = set(parser.ids)
    dangling = sorted(
        href for href in set(parser.hrefs)
        if href.startswith("#") and href[1:] not in ids
    )
    if dangling:
        problems.append("dangling anchors: " + ", ".join(dangling[:10]))
    if parser.external_assets:
        problems.append("external assets: " + ", ".join(parser.external_assets[:5]))

    for item in SUPPLEMENTS:
        section = parser.sections.get(item.section_id)
        if section is None:
            problems.append(f"missing section #{item.section_id}")
            continue
        text = " ".join("".join(section["text"]).split())
        if len(text) < 6_000:
            problems.append(
                f"chapter {item.number} visible text too short: {len(text)} chars"
            )
        if section["deep_qas"] < 7:
            problems.append(f"chapter {item.number} has only {section['deep_qas']} deep Q&A")
        if section["details"] < 5:
            problems.append(f"chapter {item.number} has only {section['details']} total Q&A")
        if section["terms"] < 4:
            problems.append(f"chapter {item.number} has only {section['terms']} term cards")
        if section["diagrams"] < 1:
            problems.append(f"chapter {item.number} has no diagram")
        if section["contracts"] != 1:
            problems.append(f"chapter {item.number} has {section['contracts']} contracts")
        if section["practical"] != 1:
            problems.append(
                f"chapter {item.number} has {section['practical']} practical sections"
            )
        if section["python_examples"] != 1:
            problems.append(
                f"chapter {item.number} has {section['python_examples']} Python examples"
            )
        if section["transfers"] < 3:
            problems.append(
                f"chapter {item.number} has only {section['transfers']} transfer patterns"
            )

    for required in (
        "guide",
        "labs",
        "work",
        "coverage",
        "formula-cards",
        "research-method",
        "glossary",
        "sources",
    ):
        if required not in parser.sections:
            problems.append(f"missing book section #{required}")

    short_answers = []
    for detail in parser.details:
        text = " ".join("".join(detail["text"]).split())
        if len(text) < 90:
            short_answers.append((detail["section"], len(text), text[:50]))
    if short_answers:
        problems.append(
            f"{len(short_answers)} folded answers shorter than 90 chars; "
            f"first={short_answers[0]}"
        )

    if source.count("CSAPP-ENRICHMENT START") != source.count("CSAPP-ENRICHMENT END"):
        problems.append("unbalanced enrichment markers")
    if "color:#163d36 !important;" not in source:
        problems.append("deep-map high-contrast foreground color is missing")
    encoded_size = len(source.encode("utf-8"))
    visible_chars = len(" ".join("".join(parser.all_text).split()))
    if encoded_size < 300_000:
        problems.append(f"book unexpectedly small: {encoded_size} UTF-8 bytes")
    if visible_chars < 150_000:
        problems.append(f"book visible content unexpectedly short: {visible_chars} chars")
    if re.search(r"(?:^|\n)\s*(?:TODO|TBD|PLACEHOLDER)(?:\s*:|\s*$)", source, re.I):
        problems.append("placeholder remains")

    runnable = 0
    for example in EXAMPLES:
        try:
            result = subprocess.run(
                [sys.executable, "-c", example.code],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except subprocess.TimeoutExpired:
            problems.append(f"chapter {example.number} Python example timed out")
            continue
        if result.returncode != 0:
            problems.append(
                f"chapter {example.number} Python example failed: "
                f"{result.stderr.strip()[:160]}"
            )
        else:
            runnable += 1

    notes.extend(
        [
            f"{len(SUPPLEMENTS)} guided chapters",
            f"{runnable}/{len(EXAMPLES)} runnable Python examples",
            f"{sum(s['deep_qas'] for s in parser.sections.values())} deep Q&A",
            f"{len(parser.details)} total folded answers",
            f"{sum(s['terms'] for s in parser.sections.values())} prerequisite cards",
            f"{sum(s['diagrams'] for s in parser.sections.values())} diagrams",
            f"{encoded_size / 1024:.0f} KB self-contained HTML",
            f"{visible_chars:,} visible characters",
        ]
    )

    print("CS:APP systems book quality gate")
    print("-" * 64)
    for note in notes:
        print(f"  ✓ {note}")
    if problems:
        for problem in problems:
            print(f"  ✗ {problem}")
        print("-" * 64)
        print(f"FAIL: {len(problems)} problems")
        return 1
    print("-" * 64)
    print("PASS: coverage, continuity, diagrams, Q&A, links, and offline assets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
