#!/usr/bin/env python3
"""Validate independently authored AWS chapter practice-question banks."""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from aws_architect_model import TASKS
from aws_architect_question_bank import BANK_DIR, PART_RANGES, QuestionBankError, _validate_part


BLOCKED_SOURCE_MARKERS = (
    "examtopics",
    "braindump",
    "brain dump",
    "actual exam questions",
    "real exam questions",
    "recalled questions",
)
OFFICIAL_HOST_SUFFIXES = (
    "aws.amazon.com",
    "docs.aws.amazon.com",
    "d1.awsstatic.com",
    "skillbuilder.aws",
    "powertools.aws.dev",
)


def normalized(value: str) -> str:
    return re.sub(r"\W+", "", value, flags=re.UNICODE).lower()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", type=int, choices=tuple(PART_RANGES))
    args = parser.parse_args()
    problems: list[str] = []
    prompts: list[tuple[str, str]] = []
    ids: list[str] = []
    total = 0
    selected_parts = (
        {args.part: PART_RANGES[args.part]} if args.part is not None else PART_RANGES
    )
    for part, chapter_range in selected_parts.items():
        path = BANK_DIR / f"part_{part:02d}.json"
        if not path.exists():
            problems.append(f"missing {path.name}")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            _validate_part(part, payload)
        except (json.JSONDecodeError, QuestionBankError) as exc:
            problems.append(f"{path.name}: {exc}")
            continue
        source_map = {source["id"]: source for source in payload["sources"]}
        for source in payload["sources"]:
            url = source.get("url", "")
            blob = " ".join(str(value) for value in source.values()).lower()
            host = urlparse(url).hostname or ""
            if not url.startswith("https://"):
                problems.append(f"{path.name}: non-HTTPS source {url!r}")
            if any(marker in blob for marker in BLOCKED_SOURCE_MARKERS):
                problems.append(f"{path.name}: prohibited source {url!r}")
            if source.get("kind") == "official" and not any(
                host == suffix or host.endswith("." + suffix)
                for suffix in OFFICIAL_HOST_SUFFIXES
            ):
                problems.append(f"{path.name}: official source has non-AWS host {host}")
        for chapter in payload["chapters"]:
            questions = chapter["questions"]
            kinds = Counter(question["kind"] for question in questions)
            if kinds["single"] < 7 or kinds["multi"] < 2:
                problems.append(
                    f"chapter {chapter['chapter']}: requires >=7 single and >=2 multi"
                )
            answer_positions = Counter(
                answer for question in questions for answer in question["answers"]
            )
            if answer_positions and max(answer_positions.values()) > 7:
                problems.append(
                    f"chapter {chapter['chapter']}: answer position too concentrated "
                    f"{dict(answer_positions)}"
                )
            for question in questions:
                qid = question["id"]
                ids.append(qid)
                total += 1
                prompt = question.get("prompt", "").strip()
                tested = question.get("tested", "").strip()
                if len(prompt) < 35 or len(tested) < 3:
                    problems.append(f"{qid}: prompt/tested label is too thin")
                choice_keys = [normalized(choice) for choice in question["choices"]]
                if len(choice_keys) != len(set(choice_keys)):
                    problems.append(f"{qid}: duplicate choices")
                if any(len(item.strip()) < 32 for item in question["explanations"]):
                    problems.append(f"{qid}: option explanation is too thin")
                if not any(
                    source_map[source_id].get("kind") == "official"
                    for source_id in question["source_ids"]
                ):
                    problems.append(f"{qid}: no official AWS fact source")
                unknown_tasks = set(question.get("task_keys", ())) - (
                    set(TASKS) | {"BOOK-META"}
                )
                if unknown_tasks:
                    problems.append(f"{qid}: unknown task keys {sorted(unknown_tasks)}")
                if "BOOK-META" in question.get("task_keys", ()) and chapter["chapter"] != 1:
                    problems.append(f"{qid}: BOOK-META is only valid in chapter 1")
                prompts.append((qid, normalized(prompt)))

    if len(ids) != len(set(ids)):
        problems.append(f"duplicate question IDs: {len(ids) - len(set(ids))}")
    for index, (left_id, left) in enumerate(prompts):
        for right_id, right in prompts[index + 1 :]:
            if left == right:
                problems.append(f"duplicate prompts: {left_id} and {right_id}")
                continue
            if min(len(left), len(right)) >= 80:
                ratio = difflib.SequenceMatcher(None, left, right).ratio()
                if ratio >= 0.92:
                    problems.append(
                        f"near-duplicate prompts ({ratio:.2f}): {left_id}, {right_id}"
                    )
    expected_total = sum(len(list(chapters)) * 10 for chapters in selected_parts.values())
    if total != expected_total:
        problems.append(f"expected {expected_total} questions, found {total}")
    if problems:
        print(f"❌ {len(problems)} question-bank problem(s)")
        for problem in problems[:200]:
            print("  -", problem)
        return 1
    chapter_count = sum(len(list(chapters)) for chapters in selected_parts.values())
    print(f"✅ AWS question banks passed: {total} questions across {chapter_count} chapters")
    return 0


if __name__ == "__main__":
    sys.exit(main())
