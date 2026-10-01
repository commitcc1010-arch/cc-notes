"""Load the independently authored AWS chapter question banks.

The generated book switches from the legacy five-question fallback only when
all twelve parts are present and structurally complete.  This prevents a
half-written agent artifact from leaking into the published HTML or EPUB.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
BANK_DIR = ROOT / "tools" / "aws_question_banks"
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


class QuestionBankError(ValueError):
    """Raised when a complete-looking bank violates the publication schema."""


def _load_part(part: int) -> dict[str, Any]:
    path = BANK_DIR / f"part_{part:02d}.json"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _validate_part(part: int, payload: dict[str, Any]) -> None:
    if payload.get("part") != part:
        raise QuestionBankError(f"part_{part:02d}: wrong part number")
    chapters = payload.get("chapters")
    sources = payload.get("sources")
    if not isinstance(chapters, list) or not isinstance(sources, list):
        raise QuestionBankError(f"part_{part:02d}: chapters/sources must be lists")
    expected = list(PART_RANGES[part])
    actual = [chapter.get("chapter") for chapter in chapters]
    if actual != expected:
        raise QuestionBankError(
            f"part_{part:02d}: chapters {actual} do not match {expected}"
        )
    source_ids = {source.get("id") for source in sources}
    if None in source_ids or len(source_ids) != len(sources):
        raise QuestionBankError(f"part_{part:02d}: duplicate or missing source id")
    for chapter in chapters:
        number = chapter["chapter"]
        questions = chapter.get("questions")
        if not isinstance(questions, list) or len(questions) != 10:
            raise QuestionBankError(f"chapter {number}: expected exactly 10 questions")
        if [question.get("intent") for question in questions] != list(range(1, 11)):
            raise QuestionBankError(f"chapter {number}: intents must be 1..10 in order")
        for index, question in enumerate(questions, 1):
            expected_id = f"ch{number:03d}-q{index:02d}"
            if question.get("id") != expected_id:
                raise QuestionBankError(
                    f"chapter {number}: expected id {expected_id}, got {question.get('id')}"
                )
            choices = question.get("choices")
            answers = question.get("answers")
            explanations = question.get("explanations")
            kind = question.get("kind")
            expected_choices = 4 if kind == "single" else 5 if kind == "multi" else 0
            expected_answers = 1 if kind == "single" else 2 if kind == "multi" else 0
            if (
                not isinstance(choices, list)
                or len(choices) != expected_choices
                or not isinstance(answers, list)
                or len(answers) != expected_answers
                or not isinstance(explanations, list)
                or len(explanations) != expected_choices
            ):
                raise QuestionBankError(f"{expected_id}: invalid choices/answers schema")
            if any(
                not isinstance(answer, int) or not 0 <= answer < expected_choices
                for answer in answers
            ):
                raise QuestionBankError(f"{expected_id}: invalid answer index")
            if not question.get("source_ids"):
                raise QuestionBankError(f"{expected_id}: missing official source")
            missing = set(question["source_ids"]) - source_ids
            if missing:
                raise QuestionBankError(
                    f"{expected_id}: unknown source ids {sorted(missing)}"
                )


@lru_cache(maxsize=1)
def complete_bank() -> dict[int, tuple[dict[str, Any], ...]] | None:
    """Return chapter-indexed questions only when every part is publishable."""

    paths = [BANK_DIR / f"part_{part:02d}.json" for part in PART_RANGES]
    if not all(path.exists() for path in paths):
        return None
    by_chapter: dict[int, tuple[dict[str, Any], ...]] = {}
    for part in PART_RANGES:
        payload = _load_part(part)
        _validate_part(part, payload)
        source_map = {source["id"]: source for source in payload["sources"]}
        author = payload.get("author_agent", f"P{part:02d}-A")
        for chapter in payload["chapters"]:
            enriched = []
            for question in chapter["questions"]:
                row = dict(question)
                row["author_agent"] = author
                row["resolved_sources"] = tuple(
                    source_map[source_id] for source_id in question["source_ids"]
                )
                row["resolved_inspirations"] = tuple(
                    source_map[source_id]
                    for source_id in question.get("inspiration_ids", ())
                    if source_id in source_map
                )
                enriched.append(row)
            by_chapter[chapter["chapter"]] = tuple(enriched)
    if set(by_chapter) != set(range(1, 117)):
        raise QuestionBankError("complete bank does not cover chapters 1..116")
    return by_chapter


def questions_for_chapter(chapter: int) -> tuple[dict[str, Any], ...] | None:
    bank = complete_bank()
    return None if bank is None else bank[chapter]
