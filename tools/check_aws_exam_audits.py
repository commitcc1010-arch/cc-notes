#!/usr/bin/env python3
"""Validate the per-chapter AWS exam coverage audits.

The audit files describe coverage requirements. They intentionally do not
contain copied exam questions or exam dumps.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "tools" / "aws_exam_audits"

PART_RANGES = {
    0: range(1, 11),
    1: range(11, 21),
    2: range(21, 32),
    3: range(32, 41),
    4: range(41, 52),
    5: range(52, 61),
    6: range(61, 72),
    7: range(72, 79),
    8: range(79, 91),
    9: range(91, 97),
    10: range(97, 105),
    11: range(105, 117),
}

CHAPTER_HEADING = re.compile(
    r"^##\s+(?:Chapter\s+|第\s*)(?P<number>\d+)(?:\s*章|\s+—|:|：)"
)
TABLE_INTENT = re.compile(r"^\|\s*(?:\d+|\d+\.\d+)\s*\|")
LIST_INTENT = re.compile(r"^\d+\.\s+\*\*")


def chapter_sections(text: str) -> dict[int, str]:
    lines = text.splitlines()
    headings: list[tuple[int, int]] = []
    level_two_headings = [
        index for index, line in enumerate(lines) if line.startswith("## ")
    ]
    for index, line in enumerate(lines):
        match = CHAPTER_HEADING.match(line)
        if match:
            headings.append((index, int(match.group("number"))))

    sections: dict[int, str] = {}
    for start, chapter in headings:
        end = next(
            (index for index in level_two_headings if index > start),
            len(lines),
        )
        if chapter in sections:
            raise ValueError(f"duplicate chapter heading: {chapter}")
        sections[chapter] = "\n".join(lines[start:end])
    return sections


def count_intents(section: str) -> int:
    count = 0
    for line in section.splitlines():
        if TABLE_INTENT.match(line) or LIST_INTENT.match(line):
            count += 1
    return count


def validate_part(part: int) -> list[str]:
    path = AUDIT_DIR / f"part_{part:02d}.md"
    if not path.exists():
        return [f"Part {part:02d}: missing {path.relative_to(ROOT)}"]

    text = path.read_text(encoding="utf-8")
    sections = chapter_sections(text)
    expected = set(PART_RANGES[part])
    actual = set(sections)
    errors: list[str] = []

    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing:
        errors.append(f"Part {part:02d}: missing chapters {missing}")
    if unexpected:
        errors.append(f"Part {part:02d}: unexpected chapters {unexpected}")

    for chapter in sorted(expected & actual):
        intent_count = count_intents(sections[chapter])
        if intent_count != 10:
            errors.append(
                f"Part {part:02d}, chapter {chapter}: "
                f"expected 10 intents, found {intent_count}"
            )

    return errors


def main() -> int:
    errors = [
        error
        for part in PART_RANGES
        for error in validate_part(part)
    ]
    if errors:
        print("AWS exam audit validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("AWS exam audit validation passed: 116 chapters × 10 intents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
