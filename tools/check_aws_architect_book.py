#!/usr/bin/env python3
"""Quality gate for the AWS Solutions Architect book sources.

Usage:
    PYTHONPATH=tools python3 tools/check_aws_architect_book.py            # whole book
    PYTHONPATH=tools python3 tools/check_aws_architect_book.py 5 6 7      # selected chapters
    PYTHONPATH=tools python3 tools/check_aws_architect_book.py --mocks    # mock exams only
    PYTHONPATH=tools python3 tools/check_aws_architect_book.py --partial  # skip missing files

Errors fail the run; warnings are printed for human review.
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict

from aws_architect_book import (
    BOOK_DIR, FRONT, MOCK_DOMAINS, MOCKS, TASKS, load_outline, parse_frontmatter,
    parse_questions, strip_frontmatter,
)

BANNED = [
    "證明完成", "四個閱讀支點", "Portable pattern", "故事真的有好結局", "需要時再查",
    "跟著一個封包走：先從故事開始", "本章其他角色", "第一個交接", "答案翻轉點",
    "詳見官方文件", "請參考官方文件",
]
REQUIRED_H2_TAIL = ["本章重點整理", "本章練習題"]
URLS = set((BOOK_DIR.parent / "tools" / "aws_architect_reference_urls.txt").read_text().split())
URL_RE = re.compile(r"\((https?://[^)\s]+)\)")


def prose_of(body: str) -> str:
    idx = body.find("\n## 本章練習題")
    return body if idx == -1 else body[:idx]


def visible_len(text: str) -> int:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return len(re.sub(r"\s+", "", text))


def check_chapter(spec, errors, warnings, all_questions, paragraphs):
    path = BOOK_DIR / spec.path
    rel = spec.path
    text = path.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    body = strip_frontmatter(text)
    if meta.get("chapter") != str(spec.number):
        errors.append(f"{rel}: frontmatter chapter 應為 {spec.number}")
    nofence = re.sub(r"(?ms)^```.*?^```", "", body)
    h1 = re.findall(r"(?m)^# (.+)$", nofence)
    if len(h1) != 1 or not h1[0].startswith(f"第 {spec.number} 章　"):
        errors.append(f"{rel}: 必須恰好一個 H1，格式「# 第 {spec.number} 章　標題」")
    if "> [!abstract] 本章地圖" not in body[:600]:
        errors.append(f"{rel}: 開頭缺少 `> [!abstract] 本章地圖`")
    h2 = re.findall(r"(?m)^## (.+)$", nofence)
    if h2[-2:] != REQUIRED_H2_TAIL:
        errors.append(f"{rel}: 最後兩個 H2 必須是 {REQUIRED_H2_TAIL}，實際 {h2[-2:]}")
    if not any("考試這樣考" in h for h in h2):
        errors.append(f"{rel}: 缺少「考試這樣考」小節")
    for h in h2[:-2]:
        if not re.match(rf"{spec.number}\.\d+ ", h):
            errors.append(f"{rel}: H2「{h}」缺少節號（應為 {spec.number}.x）")
    for phrase in BANNED:
        if phrase in body:
            errors.append(f"{rel}: 出現禁用語「{phrase}」")
    prose = prose_of(body)
    size = visible_len(prose)
    minimum = 9000 if spec.part in (0, 10, 11) else 13000
    if size < minimum:
        errors.append(f"{rel}: 正文可見字元 {size} 低於 {minimum}")
    takeaways = body.split("## 本章重點整理", 1)[-1].split("## 本章練習題", 1)[0]
    n_take = len(re.findall(r"(?m)^- ", takeaways))
    if n_take < 8:
        errors.append(f"{rel}: 本章重點整理只有 {n_take} 條（至少 8）")
    if body.count("```text") < 1:
        warnings.append(f"{rel}: 沒有任何 ASCII 圖")
    for url in URL_RE.findall(body):
        if url not in URLS:
            warnings.append(f"{rel}: 連結不在已查證清單：{url}")
    qs = parse_questions(body.split("## 本章練習題", 1)[-1], rel)
    if len(qs) != spec.questions:
        errors.append(f"{rel}: 題數 {len(qs)}，大綱要求 {spec.questions}")
    for n, q in enumerate(qs, 1):
        if q.qid != f"{spec.number}-{n}":
            errors.append(f"{rel}:{q.line}: 題號應為 {spec.number}-{n}，實際 {q.qid}")
        for e in q.errors:
            errors.append(f"{rel}:{q.line} 練習 {q.qid}: {e}")
        if q.level == "SAA" and any(t.startswith("SAP") for t in q.tasks) and not any(t.startswith("SAA") for t in q.tasks):
            warnings.append(f"{rel}:{q.line}: SAA 題只標了 SAP task")
    first = Counter(q.answers[0] for q in qs if q.answers and q.kind == "單選")
    if len(qs) >= 8:
        for letter in "ABCD":
            if first[letter] == 0:
                errors.append(f"{rel}: 單選題答案從未出現 {letter}，分布 {dict(first)}")
        if first and max(first.values()) > 0.45 * sum(first.values()):
            warnings.append(f"{rel}: 單選答案分布偏斜 {dict(first)}")
    all_questions.extend(qs)
    for para in re.split(r"\n\s*\n", prose):
        para = para.strip()
        if len(para) >= 60 and not para.startswith(("|", "```", "#")):
            paragraphs[para].append(rel)


def check_mock(rel, level, count, errors, warnings, all_questions):
    path = BOOK_DIR / rel
    body = strip_frontmatter(path.read_text(encoding="utf-8"))
    qs = parse_questions(body, rel)
    if len(qs) != count:
        errors.append(f"{rel}: 題數 {len(qs)}，應為 {count}")
    domains = Counter()
    for n, q in enumerate(qs, 1):
        if q.qid != str(n):
            errors.append(f"{rel}:{q.line}: 題號應為 {n}，實際 {q.qid}")
        if q.level != level:
            errors.append(f"{rel}:{q.line}: 等級應為 {level}")
        m = re.match(r"D([1-4]) ", q.topic)
        if not m:
            errors.append(f"{rel}:{q.line}: 主題需以 D1–D4 開頭")
        else:
            domains[int(m.group(1))] += 1
        for e in q.errors:
            errors.append(f"{rel}:{q.line} 第 {q.qid} 題: {e}")
        if not all(t.startswith(level) for t in q.tasks):
            errors.append(f"{rel}:{q.line}: 模擬考 task 必須全是 {level}")
    for d, want in MOCK_DOMAINS[level].items():
        if abs(domains[d] - want) > 1:
            errors.append(f"{rel}: Domain {d} 題數 {domains[d]}，應約為 {want}")
    first = Counter(q.answers[0] for q in qs if q.answers and q.kind == "單選")
    total = sum(first.values()) or 1
    for letter in "ABCD":
        if not 0.15 <= first[letter] / total <= 0.35:
            warnings.append(f"{rel}: 單選答案 {letter} 比例 {first[letter]}/{total}")
    multi = sum(q.kind != "單選" for q in qs)
    if not 0.1 * count <= multi <= 0.3 * count:
        warnings.append(f"{rel}: 多選題 {multi} 題，建議 10–30%")
    covered = {t for q in qs for t in q.tasks}
    missing = sorted(t for t in TASKS if t.startswith(level) and t not in covered)
    if missing:
        errors.append(f"{rel}: 未涵蓋 task {missing}")
    all_questions.extend(qs)


def main(argv):
    chapters, appendices, _ = load_outline()
    partial = "--partial" in argv
    nums = {int(a) for a in argv if a.isdigit()}
    only_mocks = "--mocks" in argv
    errors: list[str] = []
    warnings: list[str] = []
    questions = []
    paragraphs: dict[str, list[str]] = defaultdict(list)
    checked = 0
    if not only_mocks:
        for spec in chapters:
            if nums and spec.number not in nums:
                continue
            if not (BOOK_DIR / spec.path).exists():
                if not partial and not nums:
                    errors.append(f"缺少章節檔案：{spec.path}")
                elif nums:
                    errors.append(f"缺少章節檔案：{spec.path}")
                continue
            check_chapter(spec, errors, warnings, questions, paragraphs)
            checked += 1
    if not nums:
        for rel, level, count in MOCKS:
            if (BOOK_DIR / rel).exists():
                check_mock(rel, level, count, errors, warnings, questions)
                checked += 1
            elif not partial:
                errors.append(f"缺少模擬考：{rel}")
        if not only_mocks:
            for rel, _ in appendices:
                if not (BOOK_DIR / rel).exists() and not partial:
                    errors.append(f"缺少附錄：{rel}")
            if not (BOOK_DIR / FRONT).exists() and not partial:
                errors.append(f"缺少前言：{FRONT}")
    for para, files in paragraphs.items():
        if len(files) >= 2:
            warnings.append(f"重複段落（{len(files)} 次，{sorted(set(files))}）：{para[:50]}…")
    stems = defaultdict(list)
    for q in questions:
        key = re.sub(r"\s+", "", q.stem)[:80]
        if key:
            stems[key].append(f"{q.file} {q.qid}")
    for key, where in stems.items():
        if len(where) > 1:
            errors.append(f"重複題幹：{where}")
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    kinds = Counter(q.kind for q in questions)
    print(f"\n檢查 {checked} 個檔案、{len(questions)} 題（{dict(kinds)}）："
          f"{len(errors)} errors、{len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
