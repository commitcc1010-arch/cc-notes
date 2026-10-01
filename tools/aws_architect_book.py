"""Shared parsing for the AWS Solutions Architect book sources.

The Markdown files under ``AWS Solutions Architect/`` are the single source of
truth. The outline (``tools/aws_architect_outline.md``) defines chapter order,
file names and question targets; this module parses both so the builder and
the checker agree on structure.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK_DIR = ROOT / "AWS Solutions Architect"
OUTLINE = Path(__file__).resolve().parent / "aws_architect_outline.md"

SAA_TASKS = {f"SAA-{d}.{t}" for d, n in ((1, 3), (2, 2), (3, 5), (4, 4)) for t in range(1, n + 1)}
SAP_TASKS = {f"SAP-{d}.{t}" for d, n in ((1, 5), (2, 6), (3, 5), (4, 4)) for t in range(1, n + 1)}
TASKS = SAA_TASKS | SAP_TASKS

KIND_OPTIONS = {"單選": 4, "選兩項": 5, "選三項": 6}
KIND_ANSWERS = {"單選": 1, "選兩項": 2, "選三項": 3}

FRONT = "00 - 前言.md"
MOCKS = [
    ("Mock Exams/SAA 模擬考 1.md", "SAA", 65),
    ("Mock Exams/SAA 模擬考 2.md", "SAA", 65),
    ("Mock Exams/SAA 模擬考 3.md", "SAA", 65),
    ("Mock Exams/SAP 模擬考 1.md", "SAP", 75),
    ("Mock Exams/SAP 模擬考 2.md", "SAP", 75),
]
MOCK_DOMAINS = {
    "SAA": {1: 20, 2: 17, 3: 15, 4: 13},
    "SAP": {1: 20, 2: 22, 3: 19, 4: 14},
}


@dataclass
class ChapterSpec:
    number: int
    part: int
    part_title: str
    path: str
    title: str
    questions: int


@dataclass
class Question:
    file: str
    line: int
    qid: str
    level: str
    kind: str
    topic: str
    stem: str
    options: list[str]
    answers: list[str]
    explanations: dict[str, tuple[bool, str]]
    tasks: list[str]
    point: str
    errors: list[str] = field(default_factory=list)


PART_RE = re.compile(r"^## (Part \d+)　(.+?)（`(.+?)/`）")
ROW_RE = re.compile(r"^\| (\d+) \| (.+?\.md) \| (.+?) \| .*? \| (\d+) \|")
APPX_RE = re.compile(r"^\| ([A-E] - .+?\.md) \| (.+) \|$")


def load_outline() -> tuple[list[ChapterSpec], list[tuple[str, str]], dict[int, tuple[str, str]]]:
    chapters: list[ChapterSpec] = []
    appendices: list[tuple[str, str]] = []
    parts: dict[int, tuple[str, str]] = {}
    part_no, part_title, folder = -1, "", ""
    in_appx = False
    for line in OUTLINE.read_text(encoding="utf-8").splitlines():
        m = PART_RE.match(line)
        if m:
            part_no = int(m.group(1).split()[1])
            part_title, folder = m.group(2), m.group(3)
            parts[part_no] = (part_title, folder)
            in_appx = False
            continue
        if line.startswith("## 附錄"):
            in_appx = True
            continue
        if line.startswith("## 模擬考"):
            in_appx = False
            continue
        m = ROW_RE.match(line)
        if m and not in_appx:
            chapters.append(ChapterSpec(int(m.group(1)), part_no, part_title,
                                        f"{folder}/{m.group(2)}", m.group(3), int(m.group(4))))
            continue
        m = APPX_RE.match(line)
        if m and in_appx:
            appendices.append((f"Appendices/{m.group(1)}", m.group(2)))
    return chapters, appendices, parts


Q_HEAD_RE = re.compile(
    r"^### (?:練習 (?P<cid>\d+-\d+)|第 (?P<mid>\d+) 題)｜(?P<level>SAA|SAP)｜(?P<kind>單選|選兩項|選三項)｜(?P<topic>.+)$"
)
OPT_RE = re.compile(r"^- ([A-F])\. (.+)$")
ANS_RE = re.compile(r"^> \[!answer\]- 答案：([A-F](?:、[A-F])*)\s*$")
EXP_RE = re.compile(r"^> \*\*([A-F]) (✓|✗)\*\* ?(.*)$")
POINT_RE = re.compile(r"^> \*\*考點\*\*：(.+)$")
TASK_RE = re.compile(r"\b(SA[AP]-\d\.\d)\b")


def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:]
    return text


def parse_frontmatter(text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        for line in text[4:end].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
    return meta


def parse_questions(text: str, file: str) -> list[Question]:
    lines = text.splitlines()
    out: list[Question] = []
    i = 0
    while i < len(lines):
        m = Q_HEAD_RE.match(lines[i])
        if not m:
            if lines[i].startswith("### 練習") or lines[i].startswith("### 第 ") and "題" in lines[i][:12]:
                q = Question(file, i + 1, lines[i], "", "", "", "", [], [], {}, [], "")
                q.errors.append(f"題目標題格式錯誤：{lines[i]}")
                out.append(q)
            i += 1
            continue
        start = i
        j = i + 1
        while j < len(lines) and not lines[j].startswith("### ") and not lines[j].startswith("## "):
            j += 1
        block = lines[i + 1:j]
        q = Question(file, start + 1, m.group("cid") or m.group("mid"), m.group("level"), m.group("kind"),
                     m.group("topic").strip(), "", [], [], {}, [], "")
        stem: list[str] = []
        k = 0
        while k < len(block) and not OPT_RE.match(block[k]):
            stem.append(block[k])
            k += 1
        q.stem = "\n".join(stem).strip()
        while k < len(block) and (OPT_RE.match(block[k]) or not block[k].strip()):
            om = OPT_RE.match(block[k])
            if om:
                expected = "ABCDEF"[len(q.options)]
                if om.group(1) != expected:
                    q.errors.append(f"選項順序錯誤：預期 {expected} 實際 {om.group(1)}")
                q.options.append(om.group(2).strip())
            k += 1
        ans_line = next((b for b in block[k:] if b.startswith("> [!answer]")), None)
        am = ANS_RE.match(ans_line or "")
        if not am:
            q.errors.append("缺少或格式錯誤的 `> [!answer]- 答案：X` 行")
        else:
            q.answers = am.group(1).split("、")
        for b in block[k:]:
            em = EXP_RE.match(b)
            if em:
                if em.group(1) in q.explanations:
                    q.errors.append(f"選項 {em.group(1)} 解析重複")
                q.explanations[em.group(1)] = (em.group(2) == "✓", em.group(3).strip())
            pm = POINT_RE.match(b)
            if pm:
                q.point = pm.group(1)
                q.tasks = TASK_RE.findall(pm.group(1))
        validate_question(q)
        out.append(q)
        i = j
    return out


def validate_question(q: Question) -> None:
    n = KIND_OPTIONS[q.kind]
    if len(q.options) != n:
        q.errors.append(f"{q.kind}需要 {n} 個選項，實際 {len(q.options)}")
    if len(q.answers) != KIND_ANSWERS[q.kind]:
        q.errors.append(f"{q.kind}需要 {KIND_ANSWERS[q.kind]} 個答案，實際 {len(q.answers)}")
    letters = "ABCDEF"[:len(q.options)]
    for a in q.answers:
        if a not in letters:
            q.errors.append(f"答案 {a} 不在選項中")
    for letter in letters:
        if letter not in q.explanations:
            q.errors.append(f"選項 {letter} 缺少解析")
        elif len(q.explanations[letter][1]) < 15:
            q.errors.append(f"選項 {letter} 解析過短")
    correct = sorted(k for k, (ok, _) in q.explanations.items() if ok)
    if q.answers and correct != sorted(q.answers):
        q.errors.append(f"✓ 標記 {correct} 與答案 {q.answers} 不一致")
    if not q.tasks:
        q.errors.append("考點缺少 task ID")
    for t in q.tasks:
        if t not in TASKS:
            q.errors.append(f"未知 task ID {t}")
    if len(q.stem) < 40:
        q.errors.append("題幹過短")
