#!/usr/bin/env python3
"""Build the problem-driven NGINX source-code book.

The canonical curriculum lives in ``nginx_source_journey_content.py``.  This
builder emits both readable Markdown notes and a single-file HTML book.  The
repository's generic EPUB builder then turns the HTML into an EPUB where every
``<details>`` block is flattened and therefore always visible.

Run:
    ./.venv-epub/bin/python tools/build_nginx_source_journey.py
    ./.venv-epub/bin/python tools/build_epub.py nginx-source-code-journey.html
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nginx_source_journey_content import APPENDICES, BOOK_PARTS  # noqa: E402
from nginx_source_journey_beginner_guides import (  # noqa: E402
    BEGINNER_GUIDES,
    PROLOGUE,
    STAGE_LABELS,
)
from nginx_source_journey_examples import EXAMPLES, SOURCE_WINDOWS  # noqa: E402
from nginx_source_journey_foundations import (  # noqa: E402
    CHAPTER_FOUNDATIONS,
    DEEP_PRIMERS,
    TERMS,
)


SOURCE_DIR = ROOT / "NGINX Source Code Journey"
OUTPUT = ROOT / "nginx-source-code-journey.html"
SOURCE_BASE = "https://github.com/nginx/nginx/blob/release-1.31.5/"
SOURCE_RAW_BASE = "https://raw.githubusercontent.com/nginx/nginx/release-1.31.5/"
ALL_CHAPTERS = [
    chapter
    for part in BOOK_PARTS
    for chapter in part["chapters"]
]
PART_FOR_CHAPTER = {
    chapter["number"]: part["part"]
    for part in BOOK_PARTS
    for chapter in part["chapters"]
}
CHAPTER_BY_NUMBER = {chapter["number"]: chapter for chapter in ALL_CHAPTERS}
_SOURCE_FILE_CACHE: dict[str, list[str]] = {}


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    chars = []
    for char in value:
        chars.append(char if char.isalnum() else "-")
    return re.sub(r"-+", "-", "".join(chars)).strip("-") or "section"


def source_link(path: str) -> str:
    label = path.replace(":", "#L")
    href = SOURCE_BASE + path.replace(":", "#L")
    return f"[`{label}`]({href})"


def source_checkout_root() -> Path | None:
    configured = os.environ.get("NGINX_SOURCE_ROOT")
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.extend(sorted(Path("/tmp").glob("nginx-source-1.31.5.*")))
    for candidate in candidates:
        if (candidate / "src" / "core" / "nginx.c").is_file():
            return candidate
    return None


def source_file_lines(relative_path: str) -> list[str]:
    cached = _SOURCE_FILE_CACHE.get(relative_path)
    if cached is not None:
        return cached

    checkout = source_checkout_root()
    if checkout is not None:
        text = (checkout / relative_path).read_text(encoding="utf-8", errors="replace")
    else:
        request = urllib.request.Request(
            SOURCE_RAW_BASE + relative_path,
            headers={"User-Agent": "cc-notes-nginx-book-builder/1.0"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            text = response.read().decode("utf-8", errors="replace")

    lines = text.splitlines()
    _SOURCE_FILE_CACHE[relative_path] = lines
    return lines


def actual_source_window(number: int) -> tuple[str, str]:
    relative_path, start, count = SOURCE_WINDOWS[number]
    lines = source_file_lines(relative_path)
    end = min(len(lines), start + count - 1)
    if start < 1 or start > len(lines):
        raise ValueError(f"invalid source window for chapter {number}: {relative_path}:{start}")
    excerpt = "\n".join(lines[start - 1 : end])
    caption = f"`{relative_path}`，官方 `release-1.31.5` 第 {start}–{end} 行"
    return caption, excerpt


def prose_blocks(value: str) -> str:
    return "\n\n".join(part.strip() for part in value.strip().split("\n\n") if part.strip())


def bullet_block(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def numbered_block(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, 1))


def inline_markup(value: str) -> str:
    """Escape trusted prose while preserving short inline-code spans."""
    escaped = html.escape(value)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def journey_map(active_part: int) -> str:
    nodes = []
    for part, label in STAGE_LABELS:
        state = " active" if part == active_part else ""
        nodes.append(
            f'<span class="journey-node{state}">'
            f'<b>{part}</b>{html.escape(label)}</span>'
        )
    return '<div class="journey-map" aria-label="全書八階段地圖">' + "".join(nodes) + "</div>"


def chapter_position(number: int) -> str:
    previous = CHAPTER_BY_NUMBER.get(number - 1)
    following = CHAPTER_BY_NUMBER.get(number + 1)

    def card(kind: str, chapter: dict | None, fallback: str) -> str:
        if chapter is None:
            return (
                f'<div class="position-card muted"><span>{kind}</span>'
                f"<strong>{html.escape(fallback)}</strong></div>"
            )
        anchor = f'chapter-{chapter["number"]:02d}-{slugify(chapter["title"])}'
        return (
            f'<a class="position-card" href="#{anchor}"><span>{kind}</span>'
            f'<strong>{chapter["number"]:02d}. '
            f'{html.escape(chapter["title"])}</strong></a>'
        )

    current = CHAPTER_BY_NUMBER[number]
    return (
        '<div class="chapter-position">'
        + card("上一站", previous, "全書導讀")
        + (
            '<div class="position-card current"><span>你在這裡</span>'
            f'<strong>{number:02d}. {html.escape(current["title"])}</strong></div>'
        )
        + card("下一站", following, "完成全書，進入實作")
        + "</div>"
    )


def contract_grid(contract: tuple[str, str, str, str, str]) -> str:
    labels = ["本章元件", "接收什麼", "產生什麼", "狀態由誰保存", "主要失敗出口"]
    cards = "".join(
        '<div class="contract-card">'
        f'<span>{html.escape(label)}</span><p>{inline_markup(value)}</p></div>'
        for label, value in zip(labels, contract, strict=True)
    )
    return f'<div class="contract-grid">{cards}</div>'


def flow_visual(items: list[str]) -> str:
    cards = "".join(
        '<div class="flow-step">'
        f'<span>{index}</span><p>{inline_markup(item)}</p></div>'
        for index, item in enumerate(items, 1)
    )
    return f'<div class="flow-visual">{cards}</div>'


def source_walkthrough(items: list[str]) -> str:
    cards = "".join(
        '<div class="source-step">'
        f'<span>{index}</span><p>{inline_markup(item)}</p></div>'
        for index, item in enumerate(items, 1)
    )
    return f'<div class="source-walkthrough">{cards}</div>'


def pattern_grid(items: list[tuple[str, str]]) -> str:
    cards = "".join(
        '<div class="pattern-card">'
        f'<h3>{html.escape(name)}</h3><p>{inline_markup(explanation)}</p></div>'
        for name, explanation in items
    )
    return f'<div class="pattern-grid">{cards}</div>'


def mapping_table(items: list[tuple[str, str]]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{inline_markup(example)}</td>"
        f"<td>{inline_markup(nginx)}</td>"
        "</tr>"
        for example, nginx in items
    )
    return (
        '<div class="mapping-table-wrap"><table class="mapping-table">'
        "<thead><tr><th>Python 小模型</th><th>對應的 NGINX C 概念</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def microscope_grid(items: list[str]) -> str:
    cards = "".join(
        '<div class="microscope-card">'
        f'<span>{index}</span><p>{inline_markup(item)}</p></div>'
        for index, item in enumerate(items, 1)
    )
    return f'<div class="microscope-grid">{cards}</div>'


def foundation_grid(keys: list[str]) -> str:
    cards = []
    for key in keys:
        term = TERMS[key]
        cards.append(
            '<section class="foundation-card">'
            f'<h3>{html.escape(term["title"])}</h3>'
            '<div class="foundation-block">'
            '<span>白話定義</span>'
            f'<p>{inline_markup(term["meaning"])}</p></div>'
            '<div class="foundation-block foundation-example">'
            '<span>具體例子</span>'
            f'<p>{inline_markup(term["example"])}</p></div>'
            '<div class="foundation-block foundation-role">'
            '<span>在 NGINX 中</span>'
            f'<p>{inline_markup(term["nginx_role"])}</p></div>'
            '</section>'
        )
    return (
        '<div class="foundation-grid" '
        'aria-label="本章開始前需要理解的技術名詞">'
        + "".join(cards)
        + "</div>"
    )


def design_decision_grid(guide: dict) -> str:
    why_parts = [
        part.strip()
        for part in guide["why"].strip().split("\n\n")
        if part.strip()
    ]
    pressure = why_parts[0]
    use_case = " ".join(why_parts[1:]) if len(why_parts) > 1 else why_parts[0]
    component, receives, produces, owner, failures = guide["contract"]
    cards = [
        ("外部壓力", pressure),
        ("真實 use case", use_case),
        (
            "NGINX 的設計選擇",
            f"建立「{component}」這個責任邊界；接收 {receives}，交付 {produces}。",
        ),
        (
            "為什麼 state 放在這裡",
            f"跨函式或跨事件仍要存活的資料由 {owner} 保存，而不是依賴會消失的 local stack。",
        ),
        (
            "這個設計付出的代價",
            f"必須明確處理 {failures}。抽象不是免費的：callback、state 與 cleanup contract 都要保持一致。",
        ),
    ]
    return (
        '<div class="design-decision-grid">'
        + "".join(
            '<section class="design-decision-card">'
            f'<span>{html.escape(label)}</span><p>{inline_markup(text)}</p>'
            '</section>'
            for label, text in cards
        )
        + "</div>"
    )


def foundation_glossary_table() -> str:
    rows = "".join(
        "<tr>"
        f'<th scope="row">{html.escape(term["title"])}</th>'
        f'<td>{inline_markup(term["meaning"])}</td>'
        f'<td>{inline_markup(term["example"])}</td>'
        f'<td>{inline_markup(term["nginx_role"])}</td>'
        "</tr>"
        for term in TERMS.values()
    )
    return (
        "## 完整零背景術語表\n\n"
        "這一節收錄每章先備概念卡的全部內容。忘記任何名詞時，不必離開本書；"
        "可直接使用 HTML／EPUB 閱讀器的搜尋功能。\n\n"
        '<div class="foundation-glossary-wrap"><table class="foundation-glossary">'
        "<thead><tr><th>名詞</th><th>白話定義</th><th>具體例子</th>"
        "<th>在 NGINX 中</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>\n"
    )


def chapter_markdown(chapter: dict) -> str:
    number = chapter["number"]
    title = chapter["title"]
    sources = " · ".join(source_link(path) for path in chapter["sources"])
    concepts = " · ".join(chapter["concepts"])
    code_lang = chapter.get("code_lang", "c")
    guide = BEGINNER_GUIDES[number]
    example = EXAMPLES[number]
    primer = DEEP_PRIMERS.get(number, "").strip()
    part_number = PART_FOR_CHAPTER[number]
    source_caption, source_excerpt = actual_source_window(number)

    qa = []
    for index, item in enumerate(chapter["qa"], 1):
        qa.extend([
            f'<details class="qa" markdown="1">',
            f"<summary>Q{index}. {item[0]}</summary>",
            "",
            prose_blocks(item[1]),
            "",
            "</details>",
            "",
        ])

    return "\n".join([
        f'# 第 {number} 章　{title}',
        "",
        "## 本章先備概念：先把名詞講成人話",
        "",
        '<aside class="admonition prerequisite-note" markdown="1">',
        '<div class="admonition-title">不需要先去查另一本文獻</div>',
        "",
        "先讀完下面的白話定義、具體例子與 NGINX 對應，就具備閱讀本章的最低背景。"
        "後文再次出現這些名詞時，請把它們放回卡片中的情境，不要只背英文。",
        "",
        "</aside>",
        "",
        foundation_grid(CHAPTER_FOUNDATIONS[number]),
        "",
        primer,
        "",
        f'<p class="chapter-question">{chapter["question"]}</p>',
        "",
        f'<div class="chapter-meta"><span>難度：{chapter["level"]}</span>'
        f'<span>{concepts}</span></div>',
        "",
        '<aside class="admonition" markdown="1">',
        '<div class="admonition-title">本章先得到什麼</div>',
        "",
        chapter["promise"],
        "",
        "</aside>",
        "",
        "## 先建立 Context：你現在位於整張地圖的哪裡？",
        "",
        journey_map(part_number),
        "",
        chapter_position(number),
        "",
        f"本章位於 **Part {part_number}：{BOOK_PARTS[part_number - 1]['title']}**。"
        "先看清楚前一站交付了什麼、本章負責什麼、下一站為什麼會自然出現；"
        "不要把下面的函式當成孤立知識點。",
        "",
        "## 為什麼系統需要這個 Component？",
        "",
        prose_blocks(guide["why"]),
        "",
        "### Design Decision：從問題推導到實作邊界",
        "",
        design_decision_grid(guide),
        "",
        "### Component Contract",
        "",
        contract_grid(guide["contract"]),
        "",
        "## 完整 Flow：從觸發到交付",
        "",
        flow_visual(guide["flow"]),
        "",
        "上面的每一步都可能在真實程式中分散於不同 callback。先記住事件順序與"
        "狀態 owner，再讀函式名稱；這樣即使 source code 跳到另一個檔案，也不會失去主線。",
        "",
        "## 大框架圖：這個 Component 如何接入系統",
        "",
        "```text",
        chapter["diagram"].strip("\n"),
        "```",
        "",
        "## 從零建立心智模型",
        "",
        prose_blocks(chapter["mental_model"]),
        "",
        "## 先用 Python 跑一次同樣的設計",
        "",
        "### 最直覺的寫法為什麼不夠？",
        "",
        prose_blocks(example["naive"]),
        "",
        '<aside class="admonition python-bridge" markdown="1">',
        '<div class="admonition-title">Python 是概念顯微鏡，不是說 NGINX 應改寫成 Python</div>',
        "",
        "這個例子刻意拿掉作業系統相容層、memory pool 與 production error handling，"
        "只保留本章最重要的 state、callback 或 ownership。程式可單獨執行，"
        "先預測輸出再往下讀。",
        "",
        "</aside>",
        "",
        "```python",
        example["python"],
        "```",
        "",
        "### Python 與 NGINX C 怎麼一一對回去？",
        "",
        mapping_table(example["mapping"]),
        "",
        "這張表是閱讀 source 的翻譯層：左邊先建立直覺，右邊才是你在 NGINX"
        " 會真正看到的 struct、field、callback 或 return code。",
        "",
        "### 真實 NGINX C：不用跳出本書",
        "",
        source_caption,
        "",
        "```c",
        source_excerpt,
        "```",
        "",
        "第一次閱讀時，不必理解這段裡的每個型別與 macro。先圈出輸入 object、"
        "被修改的 state、會提前 return 的 branch，以及被安裝或呼叫的 callback；"
        "下面的 Source Microscope 會告訴你應該依什麼順序看。",
        "",
        "## 源碼導覽：不跳出去也能理解",
        "",
        '<aside class="admonition" markdown="1">',
        '<div class="admonition-title">先在書內讀懂，再把連結當成選讀</div>',
        "",
        "下面先把真正 source path 壓縮成可讀的 execution story。"
        "你不需要離開本書，也能知道每一步由誰觸發、改了哪個狀態，以及下一個 callback 在哪裡。",
        "",
        "</aside>",
        "",
        source_walkthrough(chapter["trace"]),
        "",
        "### Source Microscope：打開檔案時依序找這四件事",
        "",
        microscope_grid(example["microscope"]),
        "",
        "### 讀真實 Source 時要盯住什麼？",
        "",
        bullet_block(guide["attention"]),
        "",
        "### 把真實程式壓縮成最小可理解版本",
        "",
        '<aside class="admonition" markdown="1">',
        '<div class="admonition-title">這段不是要求背誦</div>',
        "",
        "以下程式只保留本章要理解的控制流；它不是從 NGINX 逐字複製，"
        "因此先用它建立 state、branch 與 callback 模型。之後即使選擇不打開外部連結，"
        "本章的核心設計仍然完整。",
        "",
        "</aside>",
        "",
        f"```{code_lang}",
        chapter["code"].strip("\n"),
        "```",
        "",
        "### 選讀：核對官方 Source",
        "",
        f"**固定版本：** `release-1.31.5`（commit `231a60ee3e90a43b829b9ca0a3013a8359b98d7e`）",
        "",
        f"**閱讀座標：** {sources}",
        "",
        "這些連結用來核對細節與繼續深挖，不是理解本章的必要條件。",
        "",
        "## 關鍵機制拆解",
        "",
        prose_blocks(chapter["deep_dive"]),
        "",
        "## Design Patterns 與 Implementation 巧思",
        "",
        pattern_grid(guide["patterns"]),
        "",
        "Pattern 名稱不是背誦目標。重點是看見：它解決哪個 constraint、把哪種變化隔離，"
        "以及為此付出了哪些 state、indirection 或維護成本。",
        "",
        "## 動手驗證",
        "",
        numbered_block(chapter["lab"]),
        "",
        "## 常見誤解與失敗模式",
        "",
        bullet_block(chapter["pitfalls"]),
        "",
        "## 可以帶走的 Coding／CS 能力",
        "",
        bullet_block(chapter["transfer"]),
        "",
        "## 本章收束：為什麼下一章會出現？",
        "",
        '<aside class="admonition chapter-bridge" markdown="1">',
        '<div class="admonition-title">把知識接回主線</div>',
        "",
        guide["bridge"],
        "",
        "</aside>",
        "",
        "## Follow-up Questions & Answers",
        "",
        *qa,
        "---",
        "",
    ])


def appendix_markdown(item: dict) -> str:
    body = item["body"].strip()
    if item["slug"] == "Glossary":
        body += "\n\n" + foundation_glossary_table()
    return f'# {item["title"]}\n\n{body}\n'


def write_sources() -> list[tuple[dict, Path, str]]:
    SOURCE_DIR.mkdir(exist_ok=True)
    prologue_path = SOURCE_DIR / "00 - Start Here.md"
    prologue_text = PROLOGUE.strip() + "\n"
    prologue_path.write_text(prologue_text, encoding="utf-8")
    emitted = [({"title": "導讀"}, prologue_path, prologue_text)]

    for part in BOOK_PARTS:
        chunks = [
            "---",
            f'title: "{part["title"]}"',
            f'part: {part["part"]}',
            "source_baseline: release-1.31.5",
            "---",
            "",
            f'# Part {part["part"]}　{part["title"]}',
            "",
            part["intro"].strip(),
            "",
        ]
        for chapter in part["chapters"]:
            chunks.append(chapter_markdown(chapter))
        text = "\n".join(chunks).rstrip() + "\n"
        path = SOURCE_DIR / f'{part["part"]:02d} - {part["slug"]}.md'
        path.write_text(text, encoding="utf-8")
        emitted.append((part, path, text))

    appendix_dir = SOURCE_DIR / "Appendices"
    appendix_dir.mkdir(exist_ok=True)
    for index, item in enumerate(APPENDICES, 1):
        text = appendix_markdown(item)
        path = appendix_dir / f'{index:02d} - {item["slug"]}.md'
        path.write_text(text, encoding="utf-8")
        emitted.append((item, path, text))
    return emitted


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    marker = text.find("\n---\n", 4)
    return text[marker + 5 :] if marker >= 0 else text


def render_markdown(text: str) -> str:
    return markdown.markdown(
        strip_frontmatter(text),
        extensions=["extra", "sane_lists", "codehilite", "md_in_html", "toc"],
        extension_configs={
            "codehilite": {
                "guess_lang": False,
                "css_class": "highlight",
                "linenums": False,
            },
            "toc": {"permalink": False},
        },
        output_format="html5",
    )


def scope_fragment_ids(fragment: str, scope: str) -> str:
    """Make Markdown-generated heading ids unique across rendered chapters."""
    ids = re.findall(r'\bid="([^"]+)"', fragment)
    mapping = {item: f"{scope}--{item}" for item in ids}
    for old, new in mapping.items():
        fragment = fragment.replace(f'id="{old}"', f'id="{new}"')
        fragment = fragment.replace(f'href="#{old}"', f'href="#{new}"')
    return fragment


def plain_text(text: str) -> str:
    value = re.sub(r"```.*?```", " ", text, flags=re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"[#>*_`|{}\[\]]", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def build() -> None:
    emitted = write_sources()
    prologue_anchor = "start-here"
    prologue_rendered = scope_fragment_ids(render_markdown(PROLOGUE), prologue_anchor)
    articles = [
        f'<article class="chapter prologue" id="{prologue_anchor}" '
        'data-title="如果你連 NGINX 是什麼都不知道，從這裡開始">'
        '<div class="part-kicker">Start Here · 零背景導讀</div>'
        f"{prologue_rendered}</article>"
    ]
    nav_parts = [
        '<section class="nav-group start-here-nav"><h2>開始之前</h2><ul>'
        '<li><a href="#start-here"><span>00</span>NGINX 是什麼？</a></li>'
        "</ul></section>"
    ]
    search_items = [{
        "id": prologue_anchor,
        "title": "導讀：NGINX 是什麼？",
        "part": "開始之前",
        "text": plain_text(PROLOGUE),
    }]

    for part in BOOK_PARTS:
        links = []
        for chapter in part["chapters"]:
            anchor = f'chapter-{chapter["number"]:02d}-{slugify(chapter["title"])}'
            links.append(
                f'<li><a href="#{anchor}"><span>{chapter["number"]:02d}</span>'
                f'{html.escape(chapter["title"])}</a></li>'
            )
            md = chapter_markdown(chapter)
            rendered = scope_fragment_ids(render_markdown(md), anchor)
            articles.append(
                f'<article class="chapter" id="{anchor}" '
                f'data-title="{html.escape(chapter["title"], quote=True)}">'
                f'<div class="part-kicker">Part {part["part"]} · '
                f'{html.escape(part["title"])}</div>{rendered}</article>'
            )
            search_items.append({
                "id": anchor,
                "title": f'第 {chapter["number"]} 章 {chapter["title"]}',
                "part": part["title"],
                "text": plain_text(md),
            })
        nav_parts.append(
            f'<section class="nav-group"><h2>Part {part["part"]} · '
            f'{html.escape(part["title"])}</h2><ul>{"".join(links)}</ul></section>'
        )

    appendix_articles = []
    appendix_links = []
    for index, appendix in enumerate(APPENDICES, 1):
        anchor = f'appendix-{index:02d}-{slugify(appendix["title"])}'
        rendered = scope_fragment_ids(
            render_markdown(appendix_markdown(appendix)),
            anchor,
        )
        appendix_articles.append(
            f'<article class="chapter appendix" id="{anchor}" '
            f'data-title="{html.escape(appendix["title"], quote=True)}">'
            f'<div class="part-kicker">Appendix {index}</div>{rendered}</article>'
        )
        appendix_links.append(
            f'<li><a href="#{anchor}"><span>A{index}</span>'
            f'{html.escape(appendix["title"])}</a></li>'
        )
        search_items.append({
            "id": anchor,
            "title": appendix["title"],
            "part": "附錄",
            "text": plain_text(appendix["body"]),
        })
    nav_parts.append(
        f'<section class="nav-group"><h2>附錄</h2><ul>'
        f'{"".join(appendix_links)}</ul></section>'
    )

    chapter_count = sum(len(part["chapters"]) for part in BOOK_PARTS)
    qa_count = sum(len(ch["qa"]) for part in BOOK_PARTS for ch in part["chapters"])
    lab_count = sum(len(ch["lab"]) for part in BOOK_PARTS for ch in part["chapters"])
    source_count = sum(len(ch["sources"]) for part in BOOK_PARTS for ch in part["chapters"])
    pygments_css = HtmlFormatter(style="friendly").get_style_defs(".highlight")
    search_json = json.dumps(search_items, ensure_ascii=False).replace("</", "<\\/")
    document = TEMPLATE.format(
        nav="\n".join(nav_parts),
        articles="\n".join(articles + appendix_articles),
        search_json=search_json,
        pygments_css=pygments_css,
        chapter_count=chapter_count,
        qa_count=qa_count,
        lab_count=lab_count,
        source_count=source_count,
    )
    OUTPUT.write_text(document, encoding="utf-8")
    print(
        f"Built {OUTPUT.name}: {chapter_count} chapters, {qa_count} Q&A, "
        f"{lab_count} lab steps, {source_count} source coordinates, "
        f"{len(emitted)} Markdown notes, {OUTPUT.stat().st_size / 1024:.0f} KB"
    )


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="從一次 HTTP 請求出發，循序漸進讀懂 NGINX 源碼、Linux epoll、HTTP、upstream、記憶體池與模組架構。">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%23176b57'/%3E%3Ctext x='32' y='43' text-anchor='middle' font-size='36' fill='white'%3EN%3C/text%3E%3C/svg%3E">
<title>從一次請求出發：NGINX 源碼、Linux 網路與系統設計</title>
<style>
:root {{
  --bg:#f3f1ea; --paper:#fffdf7; --paper-2:#f8f4e9; --ink:#202520;
  --muted:#667066; --line:#dcd6c6; --green:#176b57; --green-2:#0e8b74;
  --blue:#285a83; --amber:#b56a18; --red:#a94734; --code:#f1efe8;
  --shadow:0 16px 42px rgba(54,48,34,.10); --sidebar:20.5rem;
}}
html[data-theme="dark"] {{
  --bg:#101714; --paper:#17201c; --paper-2:#1d2923; --ink:#edf3ee;
  --muted:#a7b6ac; --line:#31433a; --green:#67d6b5; --green-2:#79dfc2;
  --blue:#8dc7f1; --amber:#f0b86d; --red:#ef9b89; --code:#101713;
  --shadow:0 18px 48px rgba(0,0,0,.28);
}}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; scroll-padding-top:1rem; }}
body {{
  margin:0; color:var(--ink); background:var(--bg);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",
    "PingFang TC","Microsoft JhengHei",sans-serif;
  line-height:1.78; -webkit-font-smoothing:antialiased;
}}
a {{ color:var(--blue); }}
#progress {{
  position:fixed; z-index:100; inset:0 auto auto 0; width:0; height:3px;
  background:linear-gradient(90deg,var(--green-2),#f0b04d);
}}
.sidebar {{
  position:fixed; z-index:60; inset:0 auto 0 0; width:var(--sidebar);
  padding:1rem .85rem 2rem; overflow:auto; background:var(--paper);
  border-right:1px solid var(--line);
}}
.brand {{ display:flex; align-items:center; justify-content:space-between; gap:.5rem; padding:.25rem .35rem 1rem; }}
.brand a {{ color:var(--ink); text-decoration:none; font-weight:850; }}
.icon-button {{
  width:2.35rem; height:2.35rem; border:1px solid var(--line); border-radius:.65rem;
  color:var(--ink); background:var(--paper-2); cursor:pointer;
}}
.search-wrap {{ position:relative; margin-bottom:1rem; }}
#search {{
  width:100%; padding:.68rem .75rem .68rem 2.15rem; border:1px solid var(--line);
  border-radius:.72rem; color:var(--ink); background:var(--paper-2); font:inherit;
  font-size:.88rem;
}}
.search-icon {{ position:absolute; left:.75rem; top:.68rem; color:var(--muted); }}
.nav-group {{ margin:1.1rem 0; }}
.nav-group h2 {{ margin:0 0 .35rem; padding:0 .45rem; color:var(--muted); border:0; font-size:.69rem; letter-spacing:.06em; text-transform:uppercase; }}
.nav-group ul {{ margin:0; padding:0; list-style:none; }}
.nav-group a {{
  display:flex; gap:.5rem; padding:.35rem .45rem; border-radius:.45rem;
  color:var(--muted); text-decoration:none; font-size:.79rem; line-height:1.35;
}}
.nav-group a span {{ flex:0 0 1.8rem; color:var(--green); font-variant-numeric:tabular-nums; }}
.nav-group a:hover,.nav-group a.active {{ color:var(--green); background:color-mix(in srgb,var(--green) 10%,transparent); }}
.hero {{
  margin-left:var(--sidebar); padding:4rem clamp(1.2rem,5vw,5.5rem) 3.1rem;
  color:#f8fff9; background:
    radial-gradient(circle at 82% 22%,rgba(240,176,77,.24),transparent 24rem),
    radial-gradient(circle at 10% 100%,rgba(88,196,165,.24),transparent 28rem),
    linear-gradient(135deg,#102e27,#174b3e 55%,#17334b);
}}
.hero-inner {{ max-width:72rem; margin:auto; }}
.eyebrow {{ margin:0 0 .7rem; font-size:.76rem; letter-spacing:.16em; text-transform:uppercase; color:#aee5d3; }}
.hero h1 {{ max-width:62rem; margin:0; font-size:clamp(2.15rem,5vw,4.1rem); line-height:1.08; letter-spacing:-.045em; }}
.subtitle {{ max-width:58rem; margin:1.15rem 0 1.4rem; color:#d9ece5; font-size:1.08rem; }}
.golden-path {{
  max-width:64rem; margin:1.5rem 0; padding:1rem 1.15rem; border:1px solid rgba(255,255,255,.18);
  border-radius:.85rem; background:rgba(7,19,16,.28); font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:.84rem; line-height:1.65; overflow:auto; white-space:pre;
}}
.badges,.hero-actions {{ display:flex; flex-wrap:wrap; gap:.55rem; }}
.badge {{ padding:.3rem .7rem; border:1px solid rgba(255,255,255,.22); border-radius:99px; background:rgba(255,255,255,.07); font-size:.77rem; }}
.hero-actions {{ margin-top:1.35rem; }}
.button {{
  display:inline-flex; align-items:center; min-height:2.55rem; padding:.48rem .82rem;
  border:1px solid rgba(255,255,255,.25); border-radius:.65rem; color:white;
  background:rgba(255,255,255,.08); text-decoration:none; font:inherit; cursor:pointer;
}}
.button:hover {{ background:rgba(255,255,255,.16); }}
.main {{ margin-left:var(--sidebar); padding:2rem clamp(1rem,4vw,4.5rem) 7rem; }}
.chapter {{
  max-width:72rem; margin:0 auto 2rem; padding:clamp(1.25rem,3.8vw,3.4rem);
  border:1px solid var(--line); border-radius:1rem; background:var(--paper); box-shadow:var(--shadow);
}}
.prologue {{ border-top:7px solid var(--green); }}
.part-kicker {{ margin-bottom:.5rem; color:var(--green); font-size:.75rem; font-weight:800; letter-spacing:.11em; text-transform:uppercase; }}
.chapter > h1:first-of-type {{ margin-top:.2rem; }}
h1,h2,h3,h4 {{ line-height:1.3; scroll-margin-top:1rem; }}
h1 {{ margin:2.8rem 0 1rem; font-size:clamp(1.75rem,4vw,2.5rem); letter-spacing:-.025em; }}
h2 {{ margin:2.35rem 0 .9rem; padding-bottom:.42rem; border-bottom:1px solid var(--line); font-size:1.42rem; }}
h3 {{ margin:1.7rem 0 .55rem; color:var(--green); font-size:1.12rem; }}
p,li {{ overflow-wrap:anywhere; }}
.chapter-question {{ margin:.7rem 0 1rem; color:var(--muted); font-size:1.12rem; font-weight:650; }}
.chapter-meta {{ display:flex; flex-wrap:wrap; gap:.5rem; margin:0 0 1.3rem; }}
.chapter-meta span {{ padding:.22rem .62rem; border-radius:99px; color:var(--green); background:color-mix(in srgb,var(--green) 10%,transparent); font-size:.76rem; }}
.prerequisite-note {{ border-left-color:var(--amber); }}
.foundation-grid {{
  display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.8rem;
  margin:1rem 0 1.65rem;
}}
.foundation-card {{
  min-width:0; padding:1rem; border:1px solid var(--line); border-top:5px solid var(--amber);
  border-radius:.82rem; background:var(--paper-2);
}}
.foundation-card h3 {{
  margin:0 0 .8rem; color:var(--ink); font-size:1.08rem;
}}
.foundation-block {{
  padding:.68rem .75rem; border-radius:.62rem; background:var(--paper);
}}
.foundation-block + .foundation-block {{ margin-top:.55rem; }}
.foundation-block span {{
  display:block; margin-bottom:.18rem; color:var(--green); font-size:.68rem;
  font-weight:850; letter-spacing:.08em; text-transform:uppercase;
}}
.foundation-block p {{ margin:0; font-size:.9rem; line-height:1.62; }}
.foundation-example {{ border-left:3px solid var(--blue); }}
.foundation-role {{ border-left:3px solid var(--green); }}
.foundation-glossary-wrap {{
  max-width:100%; overflow:auto; margin:1rem 0 1.5rem; border:1px solid var(--line);
  border-radius:.8rem;
}}
.foundation-glossary {{ min-width:68rem; margin:0; }}
.foundation-glossary th[scope="row"] {{ width:13rem; color:var(--green); background:var(--paper-2); }}
.design-decision-grid {{
  display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem;
  margin:1rem 0 1.5rem;
}}
.design-decision-card {{
  padding:.88rem .95rem; border:1px solid var(--line); border-radius:.72rem;
  background:var(--paper-2);
}}
.design-decision-card:nth-child(3) {{
  grid-column:1/-1; border-left:5px solid var(--green);
}}
.design-decision-card span {{
  display:block; color:var(--green); font-size:.7rem; font-weight:850;
  letter-spacing:.07em; text-transform:uppercase;
}}
.design-decision-card p {{ margin:.3rem 0 0; line-height:1.62; }}
.journey-map {{
  display:grid; grid-template-columns:repeat(8,minmax(0,1fr)); gap:.45rem;
  margin:1.15rem 0; padding:1rem; border:1px solid var(--line); border-radius:.9rem;
  background:color-mix(in srgb,var(--green) 4%,var(--paper-2));
}}
.journey-node {{
  min-height:4.4rem; padding:.65rem .45rem; border:1px solid var(--line);
  border-radius:.65rem; color:var(--muted); background:var(--paper); text-align:center;
  font-size:.74rem; line-height:1.35;
}}
.journey-node b {{
  display:grid; place-items:center; width:1.65rem; height:1.65rem; margin:0 auto .35rem;
  border-radius:50%; color:var(--green); background:color-mix(in srgb,var(--green) 12%,var(--paper));
}}
.journey-node.active {{
  color:white; border-color:var(--green); background:linear-gradient(145deg,var(--green),#15516c);
  box-shadow:0 8px 22px color-mix(in srgb,var(--green) 25%,transparent); transform:translateY(-2px);
}}
.journey-node.active b {{ color:var(--green); background:white; }}
.chapter-position {{
  display:grid; grid-template-columns:1fr 1.12fr 1fr; gap:.65rem; margin:1rem 0 1.25rem;
}}
.position-card {{
  display:flex; flex-direction:column; min-width:0; padding:.75rem .85rem;
  border:1px solid var(--line); border-radius:.7rem; color:var(--ink); background:var(--paper-2);
  text-decoration:none; line-height:1.4;
}}
.position-card span {{ color:var(--muted); font-size:.7rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }}
.position-card strong {{ margin-top:.25rem; font-size:.85rem; }}
.position-card.current {{ border-color:var(--green); background:color-mix(in srgb,var(--green) 10%,var(--paper)); }}
.position-card.muted {{ opacity:.7; }}
.contract-grid {{
  display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem; margin:1rem 0 1.4rem;
}}
.contract-card {{
  padding:.85rem .95rem; border:1px solid var(--line); border-radius:.72rem; background:var(--paper-2);
}}
.contract-card:first-child {{ grid-column:1/-1; border-left:5px solid var(--green); }}
.contract-card span {{ display:block; color:var(--green); font-size:.72rem; font-weight:850; letter-spacing:.07em; text-transform:uppercase; }}
.contract-card p {{ margin:.28rem 0 0; line-height:1.55; }}
.flow-visual,.source-walkthrough {{ display:grid; gap:.62rem; margin:1rem 0 1.35rem; }}
.flow-step,.source-step {{
  display:grid; grid-template-columns:2.2rem 1fr; align-items:start; gap:.72rem;
  padding:.75rem .9rem; border:1px solid var(--line); border-radius:.72rem; background:var(--paper-2);
}}
.flow-step > span,.source-step > span {{
  display:grid; place-items:center; width:2rem; height:2rem; border-radius:50%;
  color:white; background:var(--green); font-size:.78rem; font-weight:850;
}}
.flow-step p,.source-step p {{ margin:.08rem 0; line-height:1.58; }}
.source-walkthrough {{ padding-left:.75rem; border-left:3px solid color-mix(in srgb,var(--blue) 60%,var(--line)); }}
.source-step > span {{ background:var(--blue); }}
.pattern-grid {{
  display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.7rem; margin:1rem 0 1.4rem;
}}
.pattern-card {{
  padding:.9rem; border:1px solid var(--line); border-top:4px solid var(--green);
  border-radius:.72rem; background:var(--paper-2);
}}
.pattern-card h3 {{ margin:0 0 .4rem; font-size:.98rem; }}
.pattern-card p {{ margin:0; color:var(--muted); font-size:.9rem; line-height:1.55; }}
.python-bridge {{ border-left-color:var(--blue); }}
.mapping-table-wrap {{ overflow:auto; margin:1rem 0 1.35rem; border-radius:.72rem; }}
.mapping-table {{ margin:0; min-width:36rem; }}
.mapping-table td:first-child {{ width:42%; }}
.microscope-grid {{
  display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem; margin:1rem 0 1.4rem;
}}
.microscope-card {{
  display:grid; grid-template-columns:2rem 1fr; align-items:start; gap:.65rem;
  padding:.85rem; border:1px solid var(--line); border-radius:.72rem; background:var(--paper-2);
}}
.microscope-card span {{
  display:grid; place-items:center; width:1.8rem; height:1.8rem; border-radius:.5rem;
  color:white; background:var(--amber); font-size:.76rem; font-weight:850;
}}
.microscope-card p {{ margin:0; line-height:1.58; }}
.chapter-bridge {{ border-left-color:var(--amber); }}
pre {{
  margin:1rem 0; padding:1rem 1.1rem; overflow:auto; border:1px solid var(--line);
  border-radius:.78rem; background:var(--code); line-height:1.52; tab-size:4;
}}
pre code {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:.84rem; }}
h2:nth-of-type(1) + .highlight,h2:nth-of-type(1) + pre {{
  border-left:6px solid var(--green-2); background:linear-gradient(135deg,color-mix(in srgb,var(--green) 8%,var(--code)),var(--code));
}}
.highlight {{ margin:1rem 0; border:1px solid var(--line); border-radius:.78rem; overflow:auto; background:#f6f8fa; }}
.highlight pre {{ margin:0; border:0; background:transparent; }}
html[data-theme="dark"] .highlight {{ filter:invert(.88) hue-rotate(180deg); }}
code {{ padding:.12em .32em; border-radius:.32rem; background:var(--code); font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.88em; }}
table {{ width:100%; margin:1.2rem 0; border-collapse:collapse; font-size:.91rem; }}
th,td {{ padding:.58rem .68rem; border:1px solid var(--line); text-align:left; vertical-align:top; }}
th {{ background:color-mix(in srgb,var(--green) 9%,var(--paper)); }}
blockquote,.admonition {{
  margin:1.1rem 0; padding:.78rem 1rem; border:1px solid var(--line);
  border-left:5px solid var(--green); border-radius:.72rem; background:var(--paper-2);
}}
.admonition-title {{ margin:0 0 .3rem; color:var(--green); font-weight:850; }}
details.qa {{
  margin:.72rem 0; padding:.78rem .95rem; border:1px solid var(--line);
  border-radius:.72rem; background:var(--paper-2);
}}
details.qa summary {{ color:var(--blue); font-weight:760; cursor:pointer; }}
details.qa[open] summary {{ margin-bottom:.65rem; }}
.search-results {{
  display:none; max-width:72rem; margin:0 auto 1.5rem; padding:1rem;
  border:1px solid var(--line); border-radius:.8rem; background:var(--paper); box-shadow:var(--shadow);
}}
.search-results.show {{ display:block; }}
.search-results h2 {{ margin:0; border:0; font-size:1rem; }}
.search-results ul {{ margin:.5rem 0 0; padding:0; list-style:none; }}
.search-results li + li {{ border-top:1px solid var(--line); }}
.search-results a {{ display:block; padding:.55rem .2rem; text-decoration:none; }}
.search-results small {{ display:block; color:var(--muted); }}
.back-top {{ position:fixed; z-index:30; right:1.1rem; bottom:1.1rem; width:2.8rem; height:2.8rem; border:1px solid var(--line); border-radius:50%; color:var(--ink); background:var(--paper); box-shadow:var(--shadow); cursor:pointer; }}
.mobile-nav {{ display:none; }}
{pygments_css}
@media(max-width:920px) {{
  .sidebar {{ transform:translateX(-103%); transition:transform .2s ease; box-shadow:var(--shadow); }}
  body.nav-open .sidebar {{ transform:translateX(0); }}
  .hero,.main {{ margin-left:0; }}
  .mobile-nav {{ display:inline-flex; }}
  .journey-map {{ grid-template-columns:repeat(4,minmax(0,1fr)); }}
  .pattern-grid {{ grid-template-columns:1fr; }}
  .microscope-grid {{ grid-template-columns:1fr; }}
  .foundation-grid {{ grid-template-columns:1fr; }}
  .design-decision-grid {{ grid-template-columns:1fr; }}
  .design-decision-card:nth-child(3) {{ grid-column:auto; }}
}}
@media(max-width:560px) {{
  .hero {{ padding-top:3rem; }}
  .chapter {{ padding:1.15rem; border-radius:.75rem; }}
  .golden-path {{ font-size:.72rem; }}
  .journey-map {{ grid-template-columns:repeat(2,minmax(0,1fr)); padding:.7rem; }}
  .chapter-position,.contract-grid {{ grid-template-columns:1fr; }}
  .contract-card:first-child {{ grid-column:auto; }}
}}
@media print {{
  #progress,.sidebar,.hero-actions,.back-top,.search-results {{ display:none!important; }}
  .hero,.main {{ margin:0; padding:0; }}
  .hero {{ color:#111; background:white; border-bottom:2px solid #111; }}
  .hero .subtitle {{ color:#333; }}
  .chapter {{ margin:0; padding:0; border:0; box-shadow:none; page-break-before:always; }}
  details.qa:not([open]) > * {{ display:block; }}
}}
</style>
</head>
<body>
<div id="progress"></div>
<aside class="sidebar" aria-label="書籍目錄">
  <div class="brand"><a href="index.html">← CC Notes 書架</a>
    <button class="icon-button" id="theme-toggle" aria-label="切換深色模式">◐</button></div>
  <div class="search-wrap"><span class="search-icon" aria-hidden="true">⌕</span>
    <input id="search" type="search" placeholder="搜尋函式、概念、問題…" autocomplete="off"></div>
  <nav>{nav}</nav>
</aside>
<header class="hero">
  <div class="hero-inner">
    <p class="eyebrow">Problem-driven source reading · NGINX release-1.31.5</p>
    <h1>從一次請求出發：NGINX 源碼、Linux 網路與系統設計</h1>
    <p class="subtitle">從「NGINX 是什麼」開始，沿著一個請求切入。每章先交代 context、use case 與完整 flow，再在書內拆解源碼、設計 pattern、implementation 巧思與 failure path。</p>
    <pre class="golden-path">Client → accept → connection/event → epoll → HTTP parser
       → location/phase engine → proxy/upstream → load balancer
       → backend → response filters → keep-alive / release pool</pre>
    <div class="badges">
      <span class="badge">{chapter_count} 章</span>
      <span class="badge">{qa_count} 組理解驗收</span>
      <span class="badge">{lab_count} 個實驗步驟</span>
      <span class="badge">{source_count} 個源碼座標</span>
      <span class="badge">{chapter_count} 組 Python ↔ C 對照</span>
      <span class="badge">零背景導讀</span>
      <span class="badge">零背景友善</span>
      <span class="badge">Linux · C · HTTP · System Design</span>
    </div>
    <div class="hero-actions">
      <button class="button mobile-nav" id="nav-toggle">☰ 目錄</button>
      <a class="button" href="#start-here">從零開始 ↓</a>
      <a class="button" href="epub/nginx-source-code-journey.epub" download>下載 EPUB</a>
      <button class="button" id="expand-all">展開所有 Q&amp;A</button>
    </div>
  </div>
</header>
<main class="main" data-epub-chapters>
  <section class="search-results" id="search-results" aria-live="polite"></section>
  {articles}
</main>
<button class="back-top" id="back-top" aria-label="回到頁首">↑</button>
<script>
const searchIndex={search_json};
const root=document.documentElement;
const saved=localStorage.getItem("nginx-book-theme");
if(saved) root.dataset.theme=saved;
document.getElementById("theme-toggle").addEventListener("click",()=>{{
  const next=root.dataset.theme==="dark"?"light":"dark";
  root.dataset.theme=next; localStorage.setItem("nginx-book-theme",next);
}});
document.getElementById("nav-toggle").addEventListener("click",()=>document.body.classList.toggle("nav-open"));
document.querySelectorAll(".sidebar a").forEach(a=>a.addEventListener("click",()=>document.body.classList.remove("nav-open")));
document.getElementById("expand-all").addEventListener("click",event=>{{
  const details=[...document.querySelectorAll("details.qa")];
  const open=details.some(item=>!item.open);
  details.forEach(item=>item.open=open);
  event.currentTarget.textContent=open?"收合所有 Q&A":"展開所有 Q&A";
}});
const search=document.getElementById("search");
const results=document.getElementById("search-results");
const escapeHtml=value=>value.replace(/[&<>"']/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}})[c]);
search.addEventListener("input",()=>{{
  const q=search.value.trim().toLocaleLowerCase();
  if(!q){{results.classList.remove("show");results.innerHTML="";return;}}
  const hits=searchIndex.filter(x=>(x.title+" "+x.part+" "+x.text).toLocaleLowerCase().includes(q)).slice(0,50);
  results.innerHTML=`<h2>${{hits.length}} 個搜尋結果</h2><ul>`+
    hits.map(x=>`<li><a href="#${{x.id}}"><strong>${{escapeHtml(x.title)}}</strong><small>${{escapeHtml(x.part)}}</small></a></li>`).join("")+"</ul>";
  results.classList.add("show");
}});
results.addEventListener("click",()=>results.classList.remove("show"));
document.addEventListener("keydown",event=>{{
  if(event.key==="/"&&document.activeElement!==search){{event.preventDefault();search.focus();}}
  if(event.key==="Escape"){{search.blur();results.classList.remove("show");document.body.classList.remove("nav-open");}}
}});
const progress=document.getElementById("progress");
const updateProgress=()=>{{
  const max=document.documentElement.scrollHeight-innerHeight;
  progress.style.width=`${{max>0?scrollY/max*100:0}}%`;
}};
addEventListener("scroll",updateProgress,{{passive:true}});addEventListener("resize",updateProgress);updateProgress();
document.getElementById("back-top").addEventListener("click",()=>scrollTo({{top:0,behavior:"smooth"}}));
const navLinks=new Map([...document.querySelectorAll(".nav-group a")].map(a=>[a.getAttribute("href").slice(1),a]));
const observer=new IntersectionObserver(entries=>{{
  const visible=entries.filter(e=>e.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top)[0];
  if(!visible)return;navLinks.forEach(a=>a.classList.remove("active"));navLinks.get(visible.target.id)?.classList.add("active");
}},{{rootMargin:"-10% 0px -75% 0px"}});
document.querySelectorAll("article.chapter").forEach(ch=>observer.observe(ch));
const restoreInitialHash=()=>{{
  if(!location.hash)return;
  let id;
  try{{id=decodeURIComponent(location.hash.slice(1));}}catch{{id=location.hash.slice(1);}}
  const target=document.getElementById(id);
  if(!target)return;
  const previous=root.style.scrollBehavior;
  root.style.scrollBehavior="auto";
  target.scrollIntoView({{block:"start"}});
  root.style.scrollBehavior=previous;
}};
requestAnimationFrame(restoreInitialHash);
addEventListener("load",restoreInitialHash,{{once:true}});
if(document.fonts?.ready)document.fonts.ready.then(restoreInitialHash);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    build()
