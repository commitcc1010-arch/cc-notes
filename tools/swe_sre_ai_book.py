"""Shared parsing for《從 Commit 到可靠服務》Markdown sources.

The hand-written Markdown under ``Software Engineering SRE AI/`` is the single
source of truth. ``tools/swe_sre_ai_outline.md`` defines chapter order, file
names and Q&A targets; the builder and the checker both read it from here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK_DIR = ROOT / "Software Engineering SRE AI"
OUTLINE = Path(__file__).resolve().parent / "swe_sre_ai_outline.md"
FRONT = "00 - 導讀.md"


@dataclass
class ChapterSpec:
    number: int
    part: int
    part_title: str
    path: str
    title: str
    qas: int


PART_RE = re.compile(r"^## (Part \d+)　(.+?)（`(.+?)/`）")
ROW_RE = re.compile(r"^\| (\d+) \| (.+?\.md) \| (.+?) \| .*? \| (\d+) \|")
APPX_RE = re.compile(r"^\| ([A-G] - .+?\.md) \| (.+) \|$")
QA_RE = re.compile(r"^> \[!question\]- Q(\d+)\. (.+)$")


def load_outline() -> tuple[list[ChapterSpec], list[tuple[str, str]], dict[int, tuple[str, str]]]:
    chapters: list[ChapterSpec] = []
    appendices: list[tuple[str, str]] = []
    parts: dict[int, tuple[str, str]] = {}
    part_no, part_title, folder, in_appx = -1, "", "", False
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
        m = ROW_RE.match(line)
        if m and not in_appx:
            chapters.append(ChapterSpec(int(m.group(1)), part_no, part_title,
                                        f"{folder}/{m.group(2)}", m.group(3), int(m.group(4))))
            continue
        m = APPX_RE.match(line)
        if m and in_appx:
            appendices.append((f"Appendices/{m.group(1)}", m.group(2)))
    return chapters, appendices, parts


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


def parse_qas(section: str) -> list[tuple[int, str, str]]:
    """Return (number, question, answer) for every Q&A callout in a section."""
    out: list[tuple[int, str, str]] = []
    lines = section.splitlines()
    i = 0
    while i < len(lines):
        m = QA_RE.match(lines[i])
        if not m:
            i += 1
            continue
        body = []
        i += 1
        while i < len(lines) and lines[i].startswith(">"):
            body.append(lines[i][1:].lstrip())
            i += 1
        out.append((int(m.group(1)), m.group(2).strip(), "\n".join(body).strip()))
    return out


def python_blocks(text: str) -> list[tuple[int, str]]:
    """Return (line number, source) for every ```python fenced block."""
    blocks: list[tuple[int, str]] = []
    for m in re.finditer(r"(?m)^```python\n(.*?)^```", text, flags=re.S):
        blocks.append((text[:m.start()].count("\n") + 1, m.group(1)))
    return blocks
