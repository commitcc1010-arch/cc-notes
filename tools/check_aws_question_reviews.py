#!/usr/bin/env python3
"""Publication gate for independent AWS question-bank reviews."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BANK_DIR = ROOT / "tools" / "aws_question_banks"
REVIEW_DIR = ROOT / "tools" / "aws_question_reviews"


def final_verdict(raw: str) -> str | None:
    for line in reversed(raw.splitlines()):
        token = re.sub(r"[^A-Z]", "", line.upper())
        if token in {"PASS", "VERIFIED", "REVISE"}:
            return token
    return None


def main() -> int:
    problems: list[str] = []
    all_bank_ids: set[str] = set()
    for bank_path in sorted(BANK_DIR.glob("part_*.json")):
        try:
            bank = json.loads(bank_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        all_bank_ids.update(
            question["id"]
            for chapter in bank.get("chapters", ())
            for question in chapter.get("questions", ())
            if "id" in question
        )

    for part in range(12):
        bank_path = BANK_DIR / f"part_{part:02d}.json"
        review_path = REVIEW_DIR / f"part_{part:02d}.md"
        if not bank_path.exists():
            problems.append(f"part_{part:02d}: missing bank")
            continue
        if not review_path.exists():
            problems.append(f"part_{part:02d}: missing independent review")
            continue
        bank = json.loads(bank_path.read_text(encoding="utf-8"))
        raw = review_path.read_text(encoding="utf-8")
        verdict = final_verdict(raw)
        if verdict not in {"PASS", "VERIFIED"}:
            problems.append(f"part_{part:02d}: final verdict is {verdict or 'missing'}")
        author = bank.get("author_agent", "")
        if author and author in raw and re.search(
            rf"(?:Reviewer|reviewer|審查者)\s*[:：]\s*`?{re.escape(author)}`?",
            raw,
        ):
            problems.append(f"part_{part:02d}: reviewer appears to be the author")
        expected_questions = sum(len(chapter["questions"]) for chapter in bank["chapters"])
        if expected_questions not in {60, 70, 80, 90, 100, 110, 120}:
            problems.append(f"part_{part:02d}: unexpected question count")
        unknown = {
            match
            for match in re.findall(r"ch\d{3}-q\d{2}", raw)
            if match not in all_bank_ids
        }
        if unknown:
            problems.append(
                f"part_{part:02d}: review mentions unknown IDs {sorted(unknown)[:5]}"
            )
    if problems:
        print(f"❌ {len(problems)} review-gate problem(s)")
        for problem in problems:
            print("  -", problem)
        return 1
    print("✅ All 12 AWS question-bank parts independently reviewed and verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
