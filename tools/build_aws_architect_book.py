#!/usr/bin/env python3
"""Build《AWS Solutions Architect 雙證全攻略》into one offline HTML book.

The hand-written Markdown under ``AWS Solutions Architect/`` is the source of
truth; ``tools/aws_architect_outline.md`` defines order. This builder only
assembles: it adds anchors, part dividers, chapter cross-links, callout
styling and a search index. It never generates book content.

Run with:
    PYTHONPATH=tools ./.venv-epub/bin/python tools/build_aws_architect_book.py
"""
from __future__ import annotations

import html
import json
import re
import sys
from collections import Counter

import markdown
from pygments.formatters import HtmlFormatter

from aws_architect_book import (
    BOOK_DIR, FRONT, MOCKS, ROOT, load_outline, parse_questions, strip_frontmatter,
)
from build_coding_interview_patterns import (
    TEMPLATE as BASE_TEMPLATE, convert_callouts, make_search_text, replace_outside_fences,
)

OUTPUT = ROOT / "aws-solutions-architect-saa-sap.html"
PARTIAL = "--partial" in sys.argv
EPUB = "epub/aws-solutions-architect-saa-sap.epub"
HEADING_RE = re.compile(r"^(#{1,3}) (.+?)\s*$")
CHAPTER_REF_RE = re.compile(r"第 (\d{1,2}) 章")

EXTRA_CSS = """
.callout-note {{ border-left-color: #5e6b80; }}
.callout-sap {{ border-left-color: #7b61c9; }}
.callout-sap > .callout-title {{ color: #674bb7; }}
.callout-example {{ border-left-color: #0f8b8d; }}
.callout-example > .callout-title {{ color: #0b6f71; }}
.callout-answer {{ border-left-color: #2f9e65; }}
.callout-answer > summary {{ color: #23784d; }}
.part-divider {{ text-align: left; }}
.part-divider h1 {{ font-size: 2.2rem; }}
.part-divider ol {{ columns: 2; }}
.chapter h3 + p {{ margin-top: .4rem; }}
a.xref {{ text-decoration: underline dotted; }}
"""


def slug_id(prefix: str, n: int) -> str:
    return f"{prefix}-{n}"


def normalize_blocks(text: str) -> str:
    """Insert the blank lines Python-Markdown needs before lists, tables and
    bold lead-ins that authors often write directly under a line of text."""
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.lstrip("> ").rstrip() if line.startswith(">") else line
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        prev = out[-1] if out else ""
        prev_body = prev.lstrip(">").strip()
        quote = ">" if line.startswith(">") else ""
        if not in_fence and prev_body and not prev.lstrip().startswith("```"):
            is_list = re.match(r"^(\s*)([-*]|\d+\.) ", stripped)
            prev_list = re.match(r"^(\s*)([-*]|\d+\.) ", prev_body) or prev.startswith(("  ", "\t"))
            is_table = stripped.startswith("|")
            prev_table = prev_body.startswith("|")
            lead = re.match(r"^\*\*[^*]+\*\*：", stripped)
            if (is_list and not prev_list) or (is_table and not prev_table) or (lead and not prev_list):
                if not prev_body.startswith("[!"):
                    out.append(quote)
        out.append(line)
    return "\n".join(out)


def render(text: str, ids: dict[str, str], own: int | None) -> tuple[str, list[tuple[int, str, str]]]:
    """Return HTML and the list of (level, title, id) headings."""
    headings: list[tuple[int, str, str]] = []
    counter = Counter()
    base = ids["base"]

    def line_fn(line: str) -> str:
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2)
            counter[level] += 1
            hid = f"{base}-title" if level == 1 else f"{base}-h{level}-{counter[level]}"
            headings.append((level, title, hid))
            return f"{m.group(1)} {title} {{#{hid}}}"

        def xref(match: re.Match) -> str:
            n = int(match.group(1))
            if n == own or f"ch{n}" not in ids:
                return match.group(0)
            return f'<a class="xref" href="#{ids[f"ch{n}"]}">{match.group(0)}</a>'

        if "](" in line or line.lstrip().startswith(("|", "<")):
            return line
        return CHAPTER_REF_RE.sub(xref, line)

    text = normalize_blocks(text)
    text = convert_callouts(text)
    text = replace_outside_fences(text, line_fn)
    rendered = markdown.markdown(
        text,
        extensions=["extra", "sane_lists", "codehilite", "md_in_html"],
        extension_configs={"codehilite": {"guess_lang": False, "css_class": "highlight", "linenums": False}},
        output_format="html5",
    )
    return rendered, headings


def build() -> None:
    chapters, appendices, parts = load_outline()
    ids = {f"ch{c.number}": f"ch{c.number:02d}" for c in chapters}
    articles: list[str] = []
    search: list[dict] = []
    nav: dict[str, list[tuple[str, str]]] = {}
    totals = Counter()

    def add(rel: str, base: str, group: str, own: int | None = None, title: str | None = None):
        path = BOOK_DIR / rel
        if not path.exists():
            if PARTIAL:
                return ""
            raise SystemExit(f"Missing source: {path}")
        raw = strip_frontmatter(path.read_text(encoding="utf-8"))
        local = dict(ids, base=base)
        body, heads = render(raw, local, own)
        first = title or next((t for lvl, t, _ in heads if lvl == 1), rel)
        articles.append(f'<article class="chapter" id="{base}" data-title="{html.escape(first, quote=True)}">{body}</article>')
        nav.setdefault(group, []).append((first, base))
        lines = raw.splitlines()
        h2 = [(t, hid) for lvl, t, hid in heads if lvl <= 2]
        chunks = re.split(r"(?m)^#{1,2} .+$", raw)[1:]
        for (t, hid), chunk in zip(h2, chunks):
            search.append({"title": t, "id": hid, "chapter": first, "text": make_search_text(chunk)[:4000]})
        return raw

    add(FRONT, "preface", "開始閱讀", title="前言")
    by_part: dict[int, list] = {}
    for c in chapters:
        by_part.setdefault(c.part, []).append(c)
    for part, specs in sorted(by_part.items()):
        title, _folder = parts[part]
        group = f"Part {part}　{title}"
        items = "".join(f'<li><a href="#{ids[f"ch{c.number}"]}">第 {c.number} 章　{html.escape(c.title)}</a></li>' for c in specs)
        pid = f"part{part:02d}"
        articles.append(f'<article class="chapter part-divider" id="{pid}" data-title="{html.escape(group)}">'
                        f'<h1>{html.escape(group)}</h1><ol>{items}</ol></article>')
        for c in specs:
            raw = add(c.path, ids[f"ch{c.number}"], group, own=c.number)
            totals["chapter_q"] += len(parse_questions(raw.split("## 本章練習題", 1)[-1], c.path))
            totals["chapters"] += 1
    for rel, _desc in appendices:
        add(rel, "appx-" + rel.split("/")[1][0].lower(), "附錄")
    for n, (rel, _lvl, _count) in enumerate(MOCKS, 1):
        raw = add(rel, f"mock-{n}", "模擬考")
        totals["mock_q"] += len(parse_questions(raw, rel))

    nav_html = "\n".join(
        f'<section class="nav-group"><h2>{html.escape(g)}</h2><ul>'
        + "".join(f'<li><a href="#{i}">{html.escape(t)}</a></li>' for t, i in items)
        + "</ul></section>"
        for g, items in nav.items()
    )
    template = BASE_TEMPLATE
    swaps = {
        "<title>Coding Interview Patterns — 20 Patterns, 160 Problems</title>":
            "<title>AWS Solutions Architect 雙證全攻略 — SAA-C03 × SAP-C02</title>",
        "Coding Interview Field Guide · 2026 Edition": "AWS Certification Guide · 2026-10 Edition",
        "<h1>Coding Interview Patterns</h1>": "<h1>AWS Solutions Architect 雙證全攻略</h1>",
        "搜尋題目、pattern、關鍵字…": "搜尋服務、概念、題目關鍵字…",
        "#note-00-book-index": "#preface",
        "epub/coding-interview-patterns-160.epub": EPUB,
    }
    for old, new in swaps.items():
        if old not in template:
            raise SystemExit(f"Template anchor missing: {old}")
        template = template.replace(old, new)
    template = re.sub(r'<p class="subtitle">.*?</p>',
                      '<p class="subtitle">從零背景到 Professional：用一家公司的成長故事，循序漸進讀懂 AWS 架構設計，'
                      '並以原創情境題準備 SAA-C03 與 SAP-C02。</p>', template, count=1, flags=re.S)
    badges = [f"{totals['chapters']} 章", "12 個 Part", f"{totals['chapter_q']} 題章內練習",
              f"{totals['mock_q']} 題模擬考", "SAA 3 回 × 65 題", "SAP 2 回 × 75 題", "5 份附錄"]
    template = re.sub(r'<div class="badges">.*?</div>',
                      '<div class="badges">' + "".join(f'<span class="badge">{b}</span>' for b in badges) + "</div>",
                      template, count=1, flags=re.S)
    template = template.replace("</style>", EXTRA_CSS + "</style>", 1)
    doc = template.format(
        pygments_css=HtmlFormatter(style="friendly").get_style_defs(".highlight"),
        nav=nav_html,
        articles="\n".join(articles),
        search_json=json.dumps(search, ensure_ascii=False).replace("</", "<\\/"),
    )
    OUTPUT.write_text(doc, encoding="utf-8")
    print(f"Built {OUTPUT.name}: {totals['chapters']} chapters, {totals['chapter_q']} chapter questions, "
          f"{totals['mock_q']} mock questions, {OUTPUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    build()
