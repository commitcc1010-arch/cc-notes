#!/usr/bin/env python3
"""Build《Agent System 設計全書》into one HTML book.

The hand-written Markdown under ``Agent System Design/`` is the source
of truth and ``tools/agent_system_outline.md`` defines order. This builder only
assembles: anchors, part dividers, chapter cross-links, callout styling and a
search index. ``build_epub.py`` then expands every Q&A for EPUB readers.

Run:
    PYTHONPATH=tools ./.venv-epub/bin/python tools/build_agent_system_book.py
    ./.venv-epub/bin/python tools/build_epub.py agent-system-design.html
"""
from __future__ import annotations

import html
import json
import re
import sys

from pygments.formatters import HtmlFormatter

from build_aws_architect_book import EXTRA_CSS, render
from book_template import TEMPLATE as BASE_TEMPLATE, make_search_text
from swe_sre_ai_book import ROOT, load_outline, parse_qas, strip_frontmatter

BOOK_DIR = ROOT / "Agent System Design"
OUTLINE = ROOT / "tools" / "agent_system_outline.md"
FRONT = "00 - 導讀.md"

OUTPUT = ROOT / "agent-system-design.html"
EPUB = "epub/agent-system-design.epub"
PARTIAL = "--partial" in sys.argv

BOOK_CSS = EXTRA_CSS + """
.callout-question {{ border-left-color: #7b61c9; }}
.callout-question > summary {{ color: #674bb7; }}
.callout-ai {{ border-left-color: #0f8b8d; }}
.callout-ai > .callout-title {{ color: #0b6f71; }}
"""


def build() -> None:
    chapters, appendices, parts = load_outline(OUTLINE)
    ids = {f"ch{c.number}": f"ch{c.number:02d}" for c in chapters}
    articles: list[str] = []
    search: list[dict] = []
    nav: dict[str, list[tuple[str, str]]] = {}
    qa_total = 0
    built = 0

    def add(rel: str, base: str, group: str, own: int | None = None, title: str | None = None) -> str:
        path = BOOK_DIR / rel
        if not path.exists():
            if PARTIAL:
                return ""
            raise SystemExit(f"Missing source: {path}")
        raw = strip_frontmatter(path.read_text(encoding="utf-8"))
        body, heads = render(raw, dict(ids, base=base), own)
        first = title or next((t for lvl, t, _ in heads if lvl == 1), rel)
        articles.append(f'<article class="chapter" id="{base}" data-title="{html.escape(first, quote=True)}">{body}</article>')
        nav.setdefault(group, []).append((first, base))
        h2 = [(t, hid) for lvl, t, hid in heads if lvl <= 2]
        chunks = re.split(r"(?m)^#{1,2} .+$", raw)[1:]
        for (t, hid), chunk in zip(h2, chunks):
            search.append({"title": t, "id": hid, "chapter": first, "text": make_search_text(chunk)[:4000]})
        return raw

    add(FRONT, "preface", "開始閱讀", title="導讀")
    by_part: dict[int, list] = {}
    for c in chapters:
        by_part.setdefault(c.part, []).append(c)
    for part, specs in sorted(by_part.items()):
        title, _folder = parts[part]
        group = f"Part {part}　{title}"
        items = "".join(f'<li><a href="#{ids[f"ch{c.number}"]}">第 {c.number} 章　{html.escape(c.title)}</a></li>' for c in specs)
        articles.append(f'<article class="chapter part-divider" id="part{part:02d}" data-title="{html.escape(group)}">'
                        f'<h1>{html.escape(group)}</h1><ol>{items}</ol></article>')
        for c in specs:
            raw = add(c.path, ids[f"ch{c.number}"], group, own=c.number)
            if raw:
                built += 1
                qa_total += len(parse_qas(raw.split("## 延伸問答", 1)[-1]))
    for rel, _desc in appendices:
        add(rel, "appx-" + rel.split("/")[1][0].lower(), "附錄")

    nav_html = "\n".join(
        f'<section class="nav-group"><h2>{html.escape(g)}</h2><ul>'
        + "".join(f'<li><a href="#{i}">{html.escape(t)}</a></li>' for t, i in items)
        + "</ul></section>"
        for g, items in nav.items()
    )
    template = BASE_TEMPLATE
    swaps = {
        "<title>Coding Interview Patterns — 20 Patterns, 160 Problems</title>":
            "<title>Agent System 設計全書：從 0 到 1 打造 Agent 與 Agentic Framework</title>",
        "Coding Interview Field Guide · 2026 Edition": "Agent System Design · 2026 Edition",
        "<h1>Coding Interview Patterns</h1>": "<h1>Agent System 設計全書</h1>",
        "搜尋題目、pattern、關鍵字…": "搜尋概念、架構、問答…",
        "#note-00-book-index": "#preface",
        "epub/coding-interview-patterns-160.epub": EPUB,
    }
    for old, new in swaps.items():
        if old not in template:
            raise SystemExit(f"Template anchor missing: {old}")
        template = template.replace(old, new)
    template = re.sub(r'<p class="subtitle">.*?</p>',
                      '<p class="subtitle">從一個 100 行的 agent loop 出發，跟著青鳥科技打造客服、coding 與 research 三個 agent，'
                      '再把共用的部分抽成自己的 agentic framework。涵蓋 tool 設計、context 與 memory、MCP 與 A2A、'
                      'orchestration、評估、安全與治理，以及從 0 到 1 的 agent system design。</p>', template, count=1, flags=re.S)
    badges = [f"{built} 章", "11 個 Part", f"{qa_total} 組延伸問答", "可離線執行的 Python 範例",
              "自建 framework：loom", "3 場設計演練", "6 份附錄"]
    template = re.sub(r'<div class="badges">.*?</div>',
                      '<div class="badges">' + "".join(f'<span class="badge">{b}</span>' for b in badges) + "</div>",
                      template, count=1, flags=re.S)
    template = template.replace("</style>", BOOK_CSS + "</style>", 1)
    doc = template.format(
        pygments_css=HtmlFormatter(style="friendly").get_style_defs(".highlight"),
        nav=nav_html,
        articles="\n".join(articles),
        search_json=json.dumps(search, ensure_ascii=False).replace("</", "<\\/"),
    )
    OUTPUT.write_text(doc, encoding="utf-8")
    print(f"Built {OUTPUT.name}: {built} chapters, {qa_total} Q&A, {OUTPUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    build()
