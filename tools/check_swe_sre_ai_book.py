#!/usr/bin/env python3
"""Quality gate for the Software Engineering × SRE × AI book.

This validates both the structured chapter data and the generated HTML.  It is
deliberately stricter than a generic HTML validator: a page can be valid HTML
while still missing the context, blueprint, example, AI guardrails, or answers
that make this book useful to a beginner.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from swe_sre_ai_content import APPENDICES, CHAPTERS
from swe_sre_ai_model import SOURCES, TERMS


ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "software-engineering-sre-ai.html"
SOURCE_DIR = ROOT / "Software Engineering SRE AI"

REQUIRED_HEADINGS = {
    "你現在位於哪裡？",
    "開始前：四個一定要先懂的概念",
    "為什麼需要這一章？",
    "Blueprint：先看完整 Flow",
    "從零建立心智模型",
    "Coding／實務例子",
    "Trade-offs 與 Failure Modes",
    "AI 時代：這一章發生了什麼變化？",
    "動手驗證",
    "Follow-up Questions & Answers",
    "本章官方來源與延伸閱讀",
}

PLACEHOLDERS = re.compile(
    r"(?:^|\n)\s*(?:TODO|TBD|PLACEHOLDER)(?:\s*:|\s*$)"
    r"|LOREM IPSUM|待補(?:充|寫|完成)(?:\s*:|\s*$)",
    re.IGNORECASE,
)


def classes(attrs: dict[str, str]) -> set[str]:
    return set(attrs.get("class", "").split())


class BookParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.external_srcs: list[str] = []
        self.chapter_stack: list[dict] = []
        self.chapters: list[dict] = []
        self.capture_heading: list[str] | None = None
        self.capture_summary: list[str] | None = None
        self.current_details = 0

    @property
    def chapter(self) -> dict | None:
        return self.chapter_stack[-1] if self.chapter_stack else None

    def handle_starttag(self, tag: str, raw_attrs: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in raw_attrs}
        css = classes(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        href = attrs.get("href")
        if href:
            self.hrefs.append(href)
        src = attrs.get("src")
        if src and src.startswith(("http://", "https://", "//")):
            self.external_srcs.append(src)

        if tag == "article" and "chapter" in css and "data-chapter" in attrs:
            chapter = {
                "number": int(attrs["data-chapter"]),
                "id": attrs.get("id", ""),
                "title": attrs.get("data-title", ""),
                "headings": set(),
                "term_cards": 0,
                "blueprints": 0,
                "comparisons": 0,
                "code_blocks": 0,
                "qas": 0,
                "answers": 0,
                "text": [],
            }
            self.chapter_stack.append(chapter)
            self.chapters.append(chapter)

        chapter = self.chapter
        if chapter is None:
            return
        if tag in {"h2", "h3"}:
            self.capture_heading = []
        if "term-card" in css:
            chapter["term_cards"] += 1
        if "ascii-diagram" in css:
            chapter["blueprints"] += 1
        if "comparison" in css:
            chapter["comparisons"] += 1
        if "highlight" in css:
            chapter["code_blocks"] += 1
        if tag == "details" and "qa" in css:
            chapter["qas"] += 1
            self.current_details += 1
        if tag == "summary" and self.current_details:
            self.capture_summary = []

    def handle_endtag(self, tag: str) -> None:
        chapter = self.chapter
        if chapter is not None and tag in {"h2", "h3"} and self.capture_heading is not None:
            heading = " ".join("".join(self.capture_heading).split())
            if heading:
                chapter["headings"].add(heading)
            self.capture_heading = None
        if chapter is not None and tag == "summary" and self.capture_summary is not None:
            if "".join(self.capture_summary).strip():
                chapter["answers"] += 1
            self.capture_summary = None
        if tag == "details" and self.current_details:
            self.current_details -= 1
        if tag == "article" and self.chapter_stack:
            self.chapter_stack.pop()

    def handle_data(self, data: str) -> None:
        if self.chapter is not None:
            self.chapter["text"].append(data)
        if self.capture_heading is not None:
            self.capture_heading.append(data)
        if self.capture_summary is not None:
            self.capture_summary.append(data)


def check_model(problems: list[str]) -> None:
    numbers = [chapter.number for chapter in CHAPTERS]
    if numbers != list(range(1, 49)):
        problems.append(f"章號應為 1..48，實際為 {numbers}")
    if len(APPENDICES) != 8:
        problems.append(f"預期 1 篇導讀與 7 篇附錄，實際為 {len(APPENDICES)}")

    for chapter in CHAPTERS:
        prefix = f"第 {chapter.number} 章"
        checks = [
            (len(chapter.terms) >= 4, "先備概念少於 4 個"),
            (len(chapter.mechanics) >= 4, "內部機制少於 4 步"),
            (len(chapter.walkthrough) >= 4, "例子解讀少於 4 步"),
            (len(chapter.tradeoffs) >= 3, "trade-offs 少於 3 個"),
            (len(chapter.ai_practices) >= 4, "AI practices 少於 4 個"),
            (len(chapter.ai_guardrails) >= 4, "AI guardrails 少於 4 個"),
            (len(chapter.lab) >= 4, "實作步驟少於 4 個"),
            (len(chapter.qa) >= 7, "Q&A 少於 7 組"),
            (len(chapter.sources) >= 2, "官方來源少於 2 個"),
            (len(chapter.mental_model) >= 240, "心智模型過短"),
            (len(chapter.ai_shift) >= 120, "AI Shift 過短"),
            (len(chapter.expert_view) >= 100, "Expert Lens 過短"),
            (len(chapter.code) >= 250, "coding／實務例子過短"),
            ("→" in chapter.blueprint or "↓" in chapter.blueprint, "blueprint 沒有 flow"),
        ]
        for ok, message in checks:
            if not ok:
                problems.append(f"{prefix}：{message}")
        for key in chapter.terms:
            if key not in TERMS:
                problems.append(f"{prefix}：未知術語 {key}")
        for key in chapter.sources:
            if key not in SOURCES:
                problems.append(f"{prefix}：未知來源 {key}")
        try:
            compile(chapter.code, f"chapter-{chapter.number:02d}.py", "exec")
        except SyntaxError as exc:
            problems.append(f"{prefix}：Python 例子無法解析（{exc.msg}，第 {exc.lineno} 行）")
        for question, answer in chapter.qa:
            if len(question.strip()) < 6 or len(answer.strip()) < 24:
                problems.append(f"{prefix}：Q&A 過短：{question}")
        joined = "\n".join(
            (
                chapter.title,
                chapter.promise,
                chapter.why,
                chapter.use_case,
                chapter.mental_model,
                chapter.code,
                chapter.ai_shift,
                chapter.expert_view,
            )
        )
        if PLACEHOLDERS.search(joined):
            problems.append(f"{prefix}：仍有 placeholder")


def check_html(problems: list[str], notes: list[str]) -> None:
    if not BOOK.exists():
        problems.append(f"找不到 {BOOK.name}")
        return

    source = BOOK.read_text(encoding="utf-8")
    parser = BookParser()
    parser.feed(source)

    if len(parser.chapters) != 48:
        problems.append(f"HTML 主章應有 48 篇，實際為 {len(parser.chapters)}")
    numbers = [chapter["number"] for chapter in parser.chapters]
    if numbers != list(range(1, 49)):
        problems.append(f"HTML 章號錯誤：{numbers}")

    duplicate_ids = [key for key, count in Counter(parser.ids).items() if count > 1]
    if duplicate_ids:
        problems.append("HTML 有重複 id：" + ", ".join(duplicate_ids[:8]))
    known_ids = set(parser.ids)
    dangling = sorted(
        {href for href in parser.hrefs if href.startswith("#") and href[1:] not in known_ids}
    )
    if dangling:
        problems.append("HTML 有懸空內部連結：" + ", ".join(dangling[:8]))
    if parser.external_srcs:
        problems.append("HTML 依賴外部資產：" + ", ".join(parser.external_srcs[:5]))

    for chapter in parser.chapters:
        prefix = f"第 {chapter['number']} 章"
        missing = REQUIRED_HEADINGS - chapter["headings"]
        if missing:
            problems.append(f"{prefix}：缺少區段 " + "、".join(sorted(missing)))
        for field, minimum, label in (
            ("term_cards", 4, "先備概念卡"),
            ("blueprints", 1, "blueprint"),
            ("comparisons", 1, "AI／guardrail 對照"),
            ("code_blocks", 1, "程式碼區塊"),
            ("qas", 7, "Q&A"),
        ):
            if chapter[field] < minimum:
                problems.append(f"{prefix}：{label} 僅 {chapter[field]} 個")
        visible = " ".join("".join(chapter["text"]).split())
        if len(visible) < 3_000:
            problems.append(f"{prefix}：可見正文過短（{len(visible)} 字元）")

    qas = sum(chapter["qas"] for chapter in parser.chapters)
    terms = sum(chapter["term_cards"] for chapter in parser.chapters)
    notes.extend(
        [
            f"48 章共 {qas} 組可折疊問答",
            f"共 {terms} 張章內先備概念卡",
            f"HTML {BOOK.stat().st_size / 1024 / 1024:.1f} MB，無外部資產依賴",
        ]
    )


def check_sources(problems: list[str], notes: list[str]) -> None:
    markdown_files = sorted(SOURCE_DIR.rglob("*.md"))
    if len(markdown_files) != 17:
        problems.append(f"Markdown 來源應有 17 份，實際為 {len(markdown_files)}")
    total_words = 0
    for path in markdown_files:
        body = path.read_text(encoding="utf-8")
        if PLACEHOLDERS.search(body):
            problems.append(f"{path.relative_to(ROOT)} 仍有 placeholder")
        total_words += len(re.findall(r"\S+", body))
    notes.append(f"Markdown 來源共 {total_words:,} 個空白分隔詞元")


def main() -> int:
    problems: list[str] = []
    notes: list[str] = []
    check_model(problems)
    check_html(problems, notes)
    check_sources(problems, notes)

    print("Software Engineering × SRE × AI book quality gate")
    print("-" * 64)
    for note in notes:
        print(f"  ✓ {note}")
    if problems:
        for problem in problems:
            print(f"  ✗ {problem}")
        print("-" * 64)
        print(f"FAIL: {len(problems)} 個問題")
        return 1
    print("-" * 64)
    print("PASS: 章節內容、HTML 結構、自包含性與來源檔全部通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
