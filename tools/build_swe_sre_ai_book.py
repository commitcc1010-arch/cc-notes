#!/usr/bin/env python3
"""Build the Software Engineering × SRE × AI handbook.

The canonical curriculum is structured Python data in ``swe_sre_ai_content``.
This builder validates the 48 chapter contract, emits readable Markdown source
notes, and builds a self-contained searchable HTML book.  ``build_epub.py``
then converts that HTML into an EPUB with every Q&A expanded.

Run:
    ./.venv-epub/bin/python tools/build_swe_sre_ai_book.py
    ./.venv-epub/bin/python tools/build_epub.py software-engineering-sre-ai.html
"""
from __future__ import annotations

import html
import json
import re
import sys
import unicodedata
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from swe_sre_ai_content import APPENDICES, CHAPTERS  # noqa: E402
from swe_sre_ai_model import PARTS, SOURCES, TERMS, Chapter  # noqa: E402

SOURCE_DIR = ROOT / "Software Engineering SRE AI"
OUTPUT = ROOT / "software-engineering-sre-ai.html"
AS_OF = "2026-09-30"
CHAPTER_BY_NUMBER = {chapter.number: chapter for chapter in CHAPTERS}


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"-+", "-", "".join(c if c.isalnum() else "-" for c in value)).strip("-")


def inline(value: str) -> str:
    escaped = html.escape(value)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def bullets(items: tuple[str, ...] | list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def numbered(items: tuple[str, ...] | list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, 1))


def part_for(number: int) -> dict:
    for part in PARTS:
        low, high = part["range"]
        if low <= number <= high:
            return part
    raise KeyError(number)


def journey_map(active: int) -> str:
    cards = []
    for part in PARTS:
        state = " active" if part["part"] == active else ""
        cards.append(
            f'<span class="journey-node{state}"><b>{part["part"]}</b>'
            f'{html.escape(part["title"])}</span>'
        )
    return '<div class="journey-map" aria-label="全書學習地圖">' + "".join(cards) + "</div>"


def chapter_position(chapter: Chapter) -> str:
    def card(label: str, other: Chapter | None, fallback: str) -> str:
        if other is None:
            return (
                f'<div class="position-card muted"><span>{label}</span>'
                f"<strong>{html.escape(fallback)}</strong></div>"
            )
        anchor = f"chapter-{other.number:02d}-{slugify(other.title)}"
        return (
            f'<a class="position-card" href="#{anchor}"><span>{label}</span>'
            f"<strong>{other.number:02d}. {html.escape(other.title)}</strong></a>"
        )

    return (
        '<div class="chapter-position">'
        + card("上一站", CHAPTER_BY_NUMBER.get(chapter.number - 1), "全書導讀")
        + (
            '<div class="position-card current"><span>你在這裡</span>'
            f"<strong>{chapter.number:02d}. {html.escape(chapter.title)}</strong></div>"
        )
        + card("下一站", CHAPTER_BY_NUMBER.get(chapter.number + 1), "完成全書")
        + "</div>"
    )


def term_cards(keys: tuple[str, ...]) -> str:
    cards = []
    for key in keys:
        term = TERMS[key]
        cards.append(
            '<section class="term-card">'
            f"<h3>{html.escape(term.title)}</h3>"
            '<div><span>白話定義</span>'
            f"<p>{inline(term.meaning)}</p></div>"
            '<div class="example"><span>具體例子</span>'
            f"<p>{inline(term.example)}</p></div>"
            '<div class="relevance"><span>本章位置</span>'
            f"<p>{inline(term.relevance)}</p></div>"
            "</section>"
        )
    return '<div class="term-grid">' + "".join(cards) + "</div>"


def flow(items: tuple[str, ...], css_class: str = "flow-grid") -> str:
    cards = "".join(
        f'<div class="flow-card"><span>{index}</span><p>{inline(item)}</p></div>'
        for index, item in enumerate(items, 1)
    )
    return f'<div class="{css_class}">{cards}</div>'


def comparison(left_title: str, left: tuple[str, ...], right_title: str, right: tuple[str, ...]) -> str:
    def side(title: str, items: tuple[str, ...], css: str) -> str:
        return (
            f'<section class="compare-card {css}"><h3>{html.escape(title)}</h3>'
            f"<ul>{''.join(f'<li>{inline(item)}</li>' for item in items)}</ul></section>"
        )

    return '<div class="comparison">' + side(left_title, left, "positive") + side(
        right_title, right, "guardrail"
    ) + "</div>"


def sources_block(keys: tuple[str, ...]) -> str:
    rows = []
    for key in keys:
        title, url = SOURCES[key]
        rows.append(f"- [{title}]({url})")
    return "\n".join(rows)


def qa_blocks(chapter: Chapter) -> list[str]:
    blocks = []
    for index, (question, answer) in enumerate(chapter.qa, 1):
        blocks.extend([
            f'<details class="qa"><summary>Q{index}. {html.escape(question)}</summary>',
            "",
            answer,
            "",
            "</details>",
            "",
        ])
    return blocks


def chapter_markdown(chapter: Chapter) -> str:
    part = part_for(chapter.number)
    return "\n".join([
        f"# 第 {chapter.number} 章　{chapter.title}",
        "",
        f'<p class="chapter-question">{html.escape(chapter.question)}</p>',
        "",
        f'<div class="chapter-meta"><span>難度：{html.escape(chapter.level)}</span>'
        f'<span>Part {part["part"]} · {html.escape(part["title"])}</span>'
        '<span>Software Engineering × SRE × AI</span></div>',
        "",
        '<aside class="callout promise" markdown="1">',
        '<div class="callout-title">本章完成後</div>',
        "",
        chapter.promise,
        "",
        "</aside>",
        "",
        "## 你現在位於哪裡？",
        "",
        journey_map(part["part"]),
        "",
        chapter_position(chapter),
        "",
        f"本章位於 **Part {part['part']}：{part['title']}**。先理解這個 component "
        "接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。",
        "",
        "## 開始前：四個一定要先懂的概念",
        "",
        '<aside class="callout prerequisite" markdown="1">',
        '<div class="callout-title">不需要先跳出去查資料</div>',
        "",
        "以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。",
        "",
        "</aside>",
        "",
        term_cards(chapter.terms),
        "",
        "## 為什麼需要這一章？",
        "",
        chapter.why,
        "",
        "### 真實 Use Case",
        "",
        chapter.use_case,
        "",
        '<div class="context-grid">',
        f'<section><span>問題壓力</span><p>{inline(chapter.why)}</p></section>',
        f'<section><span>交付能力</span><p>{inline(chapter.promise)}</p></section>',
        f'<section><span>真實場景</span><p>{inline(chapter.use_case)}</p></section>',
        "</div>",
        "",
        "## Blueprint：先看完整 Flow",
        "",
        f'<pre class="ascii-diagram"><code>{html.escape(chapter.blueprint)}</code></pre>',
        "",
        "先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、"
        "失敗後如何返回上一層。這張圖是本章所有細節的索引。",
        "",
        "## 從零建立心智模型",
        "",
        chapter.mental_model,
        "",
        "### 內部機制：一步一步拆開",
        "",
        flow(chapter.mechanics),
        "",
        "## Coding／實務例子",
        "",
        chapter.example_intro,
        "",
        f"```{chapter.code_lang}",
        chapter.code,
        "```",
        "",
        "### 如何讀這個例子",
        "",
        flow(chapter.walkthrough, "walkthrough-grid"),
        "",
        "## Trade-offs 與 Failure Modes",
        "",
        bullets(chapter.tradeoffs),
        "",
        "不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，"
        "原本的選擇會不再合理，以及要用哪個 signal 看見它。",
        "",
        "## AI 時代：這一章發生了什麼變化？",
        "",
        '<aside class="callout ai-shift" markdown="1">',
        '<div class="callout-title">AI Shift</div>',
        "",
        chapter.ai_shift,
        "",
        "</aside>",
        "",
        comparison("適合交給 AI 的工作", chapter.ai_practices, "必須建立的 Guardrails", chapter.ai_guardrails),
        "",
        "### Domain Expert Lens",
        "",
        '<aside class="callout expert" markdown="1">',
        '<div class="callout-title">不是工具清單，而是判斷邊界</div>',
        "",
        chapter.expert_view,
        "",
        "</aside>",
        "",
        "## 動手驗證",
        "",
        numbered(chapter.lab),
        "",
        "## Follow-up Questions & Answers",
        "",
        *qa_blocks(chapter),
        "## 本章官方來源與延伸閱讀",
        "",
        sources_block(chapter.sources),
        "",
        "---",
        "",
    ])


def appendix_markdown(item: dict) -> str:
    return f'# {item["title"]}\n\n{item["body"].strip()}\n'


def write_sources() -> list[Path]:
    SOURCE_DIR.mkdir(exist_ok=True)
    emitted = []
    prologue = SOURCE_DIR / "00 - Start Here.md"
    prologue.write_text(APPENDICES[0]["body"].strip() + "\n", encoding="utf-8")
    emitted.append(prologue)
    for part in PARTS:
        low, high = part["range"]
        chunks = [
            "---",
            f'title: "{part["title"]}"',
            f'part: {part["part"]}',
            f'as_of: {AS_OF}',
            "---",
            "",
            f'# Part {part["part"]}　{part["title"]}',
            "",
            part["intro"],
            "",
        ]
        for chapter in CHAPTERS:
            if low <= chapter.number <= high:
                chunks.append(chapter_markdown(chapter))
        path = SOURCE_DIR / f'{part["part"] + 1:02d} - {part["slug"]}.md'
        path.write_text("\n".join(chunks).rstrip() + "\n", encoding="utf-8")
        emitted.append(path)

    appendix_dir = SOURCE_DIR / "Appendices"
    appendix_dir.mkdir(exist_ok=True)
    for index, item in enumerate(APPENDICES[1:], 1):
        path = appendix_dir / f'{index:02d} - {item["slug"]}.md'
        path.write_text(appendix_markdown(item), encoding="utf-8")
        emitted.append(path)
    return emitted


def strip_frontmatter(value: str) -> str:
    if not value.startswith("---\n"):
        return value
    marker = value.find("\n---\n", 4)
    return value[marker + 5 :] if marker >= 0 else value


def render_markdown(value: str) -> str:
    return markdown.markdown(
        strip_frontmatter(value),
        extensions=["extra", "sane_lists", "codehilite", "md_in_html", "toc"],
        extension_configs={
            "codehilite": {"guess_lang": False, "css_class": "highlight", "linenums": False},
            "toc": {"permalink": False},
        },
        output_format="html5",
    )


def scope_ids(fragment: str, scope: str) -> str:
    ids = re.findall(r'\bid="([^"]+)"', fragment)
    for old in ids:
        new = f"{scope}--{old}"
        fragment = fragment.replace(f'id="{old}"', f'id="{new}"')
        fragment = fragment.replace(f'href="#{old}"', f'href="#{new}"')
    return fragment


def plain_text(value: str) -> str:
    value = re.sub(r"```.*?```", " ", value, flags=re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"[#>*_`|{}\[\]]", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def validate_book() -> None:
    numbers = [chapter.number for chapter in CHAPTERS]
    assert numbers == list(range(1, 49)), f"expected chapters 1..48, got {numbers}"
    for chapter in CHAPTERS:
        for term in chapter.terms:
            assert term in TERMS, f"chapter {chapter.number}: unknown term {term}"
        for source in chapter.sources:
            assert source in SOURCES, f"chapter {chapter.number}: unknown source {source}"


def build() -> None:
    validate_book()
    emitted = write_sources()
    nav = []
    articles = []
    search_items = []

    prologue = APPENDICES[0]
    prologue_anchor = "start-here"
    articles.append(
        f'<article class="chapter prologue" id="{prologue_anchor}" data-title="全書導讀">'
        '<div class="part-kicker">Start Here · 使用說明</div>'
        f'{scope_ids(render_markdown(prologue["body"]), prologue_anchor)}</article>'
    )
    nav.append(
        '<section class="nav-group"><h2>開始之前</h2><ul>'
        '<li><a href="#start-here"><span>00</span>全書導讀</a></li></ul></section>'
    )
    search_items.append({
        "id": prologue_anchor,
        "title": "全書導讀",
        "part": "開始之前",
        "text": plain_text(prologue["body"]),
    })

    for part in PARTS:
        low, high = part["range"]
        links = []
        for chapter in CHAPTERS:
            if not low <= chapter.number <= high:
                continue
            anchor = f"chapter-{chapter.number:02d}-{slugify(chapter.title)}"
            md = chapter_markdown(chapter)
            rendered = scope_ids(render_markdown(md), anchor)
            articles.append(
                f'<article class="chapter" id="{anchor}" '
                f'data-chapter="{chapter.number}" '
                f'data-title="{html.escape(chapter.title, quote=True)}">'
                f'<div class="part-kicker">Part {part["part"]} · '
                f'{html.escape(part["title"])}</div>{rendered}</article>'
            )
            links.append(
                f'<li><a href="#{anchor}"><span>{chapter.number:02d}</span>'
                f'{html.escape(chapter.title)}</a></li>'
            )
            search_items.append({
                "id": anchor,
                "title": f"第 {chapter.number} 章 {chapter.title}",
                "part": part["title"],
                "text": plain_text(md),
            })
        nav.append(
            f'<section class="nav-group"><h2>Part {part["part"]} · '
            f'{html.escape(part["title"])}</h2><ul>{"".join(links)}</ul></section>'
        )

    appendix_links = []
    for index, appendix in enumerate(APPENDICES[1:], 1):
        anchor = f"appendix-{index:02d}-{slugify(appendix['title'])}"
        md = appendix_markdown(appendix)
        articles.append(
            f'<article class="chapter appendix" id="{anchor}" '
            f'data-title="{html.escape(appendix["title"], quote=True)}">'
            f'<div class="part-kicker">Appendix {index}</div>'
            f'{scope_ids(render_markdown(md), anchor)}</article>'
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
    nav.append(
        f'<section class="nav-group"><h2>附錄</h2><ul>{"".join(appendix_links)}</ul></section>'
    )

    qa_count = sum(len(chapter.qa) for chapter in CHAPTERS)
    lab_count = sum(len(chapter.lab) for chapter in CHAPTERS)
    source_count = sum(len(chapter.sources) for chapter in CHAPTERS)
    term_count = sum(len(chapter.terms) for chapter in CHAPTERS)
    search_json = json.dumps(search_items, ensure_ascii=False).replace("</", "<\\/")
    pygments_css = HtmlFormatter(style="friendly").get_style_defs(".highlight")
    doc = TEMPLATE.format(
        nav="\n".join(nav),
        articles="\n".join(articles),
        search_json=search_json,
        pygments_css=pygments_css,
        qa_count=qa_count,
        lab_count=lab_count,
        source_count=source_count,
        term_count=term_count,
    )
    OUTPUT.write_text(doc, encoding="utf-8")
    print(
        f"Built {OUTPUT.name}: 48 chapters, {qa_count} Q&A, {lab_count} lab steps, "
        f"{term_count} prerequisite cards, {source_count} source references, "
        f"{len(emitted)} Markdown notes, {OUTPUT.stat().st_size / 1024:.0f} KB"
    )


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="從 Commit 到可靠服務：整合 Software Engineering at Google、Site Reliability Engineering 與 AI 時代工程實務的自包含指南。">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%231d4f68'/%3E%3Ctext x='32' y='43' text-anchor='middle' font-size='34' fill='white'%3ER%3C/text%3E%3C/svg%3E">
<title>從 Commit 到可靠服務 — Software Engineering × SRE × AI</title>
<style>
:root {{
  --bg:#edf2f3; --paper:#fffefa; --paper-2:#f4f7f6; --ink:#182428;
  --muted:#5e6e72; --line:#d6e0e1; --navy:#1d4f68; --teal:#147d79;
  --ai:#7157a8; --amber:#ad681d; --red:#a74646; --green:#287552;
  --code:#eef2f1; --shadow:0 16px 44px rgba(34,55,60,.11); --sidebar:21rem;
}}
html[data-theme="dark"] {{
  --bg:#0f171a; --paper:#172226; --paper-2:#1d2a2e; --ink:#edf5f4;
  --muted:#a6b9ba; --line:#324448; --navy:#7ec4e5; --teal:#71d7ce;
  --ai:#c3a9ff; --amber:#efb267; --red:#f09393; --green:#78d3a2;
  --code:#10191c; --shadow:0 18px 48px rgba(0,0,0,.3);
}}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; scroll-padding-top:1rem; }}
body {{
  margin:0; color:var(--ink); background:var(--bg);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",
    "PingFang TC","Microsoft JhengHei",sans-serif;
  line-height:1.78; -webkit-font-smoothing:antialiased;
}}
a {{ color:var(--navy); }}
#progress {{ position:fixed; z-index:100; inset:0 auto auto 0; width:0; height:3px;
  background:linear-gradient(90deg,var(--teal),var(--ai),#e5a13c); }}
.sidebar {{
  position:fixed; z-index:60; inset:0 auto 0 0; width:var(--sidebar);
  padding:1rem .85rem 2rem; overflow:auto; background:var(--paper);
  border-right:1px solid var(--line);
}}
.brand {{ display:flex; align-items:center; justify-content:space-between; gap:.5rem; padding:.25rem .35rem 1rem; }}
.brand a {{ color:var(--ink); text-decoration:none; font-weight:850; }}
.icon-button {{ width:2.35rem; height:2.35rem; border:1px solid var(--line); border-radius:.65rem;
  color:var(--ink); background:var(--paper-2); cursor:pointer; }}
.search-wrap {{ position:relative; margin-bottom:1rem; }}
#search {{ width:100%; padding:.68rem .75rem .68rem 2.15rem; border:1px solid var(--line);
  border-radius:.72rem; color:var(--ink); background:var(--paper-2); font:inherit; font-size:.88rem; }}
.search-icon {{ position:absolute; left:.75rem; top:.68rem; color:var(--muted); }}
.nav-group {{ margin:1.05rem 0; }}
.nav-group h2 {{ margin:0 0 .35rem; padding:0 .45rem; color:var(--muted); border:0;
  font-size:.68rem; letter-spacing:.055em; text-transform:uppercase; }}
.nav-group ul {{ margin:0; padding:0; list-style:none; }}
.nav-group a {{ display:flex; gap:.5rem; padding:.33rem .45rem; border-radius:.45rem;
  color:var(--muted); text-decoration:none; font-size:.78rem; line-height:1.35; }}
.nav-group a span {{ flex:0 0 1.8rem; color:var(--teal); font-variant-numeric:tabular-nums; }}
.nav-group a:hover,.nav-group a.active {{ color:var(--navy); background:color-mix(in srgb,var(--teal) 10%,transparent); }}
.hero {{
  margin-left:var(--sidebar); padding:4.2rem clamp(1.2rem,5vw,5.5rem) 3.2rem; color:white;
  background:radial-gradient(circle at 86% 22%,rgba(183,143,255,.25),transparent 24rem),
    radial-gradient(circle at 10% 100%,rgba(78,207,190,.24),transparent 28rem),
    linear-gradient(135deg,#102c36,#174e58 52%,#302d55);
}}
.hero-inner {{ max-width:74rem; margin:auto; }}
.eyebrow {{ margin:0 0 .7rem; color:#a9e3df; font-size:.75rem; letter-spacing:.15em; text-transform:uppercase; }}
.hero h1 {{ max-width:66rem; margin:0; font-size:clamp(2.2rem,5vw,4.2rem); line-height:1.07; letter-spacing:-.045em; }}
.subtitle {{ max-width:62rem; margin:1.15rem 0 1.4rem; color:#dcedee; font-size:1.08rem; }}
.golden-path {{ max-width:68rem; margin:1.5rem 0; padding:1rem 1.15rem;
  border:1px solid rgba(255,255,255,.18); border-radius:.85rem; background:rgba(3,19,22,.3);
  color:#f5ffff; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.82rem;
  line-height:1.65; overflow:auto; white-space:pre; }}
.badges,.hero-actions {{ display:flex; flex-wrap:wrap; gap:.55rem; }}
.badge {{ padding:.3rem .7rem; border:1px solid rgba(255,255,255,.22); border-radius:99px;
  background:rgba(255,255,255,.07); font-size:.77rem; }}
.hero-actions {{ margin-top:1.35rem; }}
.button {{ display:inline-flex; align-items:center; min-height:2.55rem; padding:.48rem .82rem;
  border:1px solid rgba(255,255,255,.25); border-radius:.65rem; color:white;
  background:rgba(255,255,255,.08); text-decoration:none; font:inherit; cursor:pointer; }}
.button:hover {{ background:rgba(255,255,255,.16); }}
.main {{ margin-left:var(--sidebar); padding:2rem clamp(1rem,4vw,4.5rem) 7rem; }}
.chapter {{ max-width:74rem; margin:0 auto 2rem; padding:clamp(1.25rem,3.8vw,3.4rem);
  border:1px solid var(--line); border-radius:1rem; background:var(--paper); box-shadow:var(--shadow); }}
.prologue {{ border-top:7px solid var(--teal); }}
.part-kicker {{ margin-bottom:.5rem; color:var(--teal); font-size:.75rem; font-weight:850;
  letter-spacing:.11em; text-transform:uppercase; }}
h1,h2,h3,h4 {{ line-height:1.3; scroll-margin-top:1rem; }}
h1 {{ margin:2.8rem 0 1rem; font-size:clamp(1.75rem,4vw,2.55rem); letter-spacing:-.025em; }}
h2 {{ margin:2.35rem 0 .9rem; padding-bottom:.42rem; border-bottom:1px solid var(--line); font-size:1.42rem; }}
h3 {{ margin:1.7rem 0 .55rem; color:var(--navy); font-size:1.1rem; }}
p,li {{ overflow-wrap:anywhere; }}
.chapter-question {{ margin:.7rem 0 1rem; color:var(--muted); font-size:1.12rem; font-weight:680; }}
.chapter-meta {{ display:flex; flex-wrap:wrap; gap:.5rem; margin:0 0 1.3rem; }}
.chapter-meta span {{ padding:.22rem .62rem; border-radius:99px; color:var(--teal);
  background:color-mix(in srgb,var(--teal) 10%,transparent); font-size:.76rem; }}
.callout {{ margin:1.1rem 0; padding:.82rem 1rem; border:1px solid var(--line);
  border-left:5px solid var(--teal); border-radius:.72rem; background:var(--paper-2); }}
.callout-title {{ margin:0 0 .3rem; color:var(--teal); font-weight:850; }}
.promise {{ border-left-color:var(--green); }}
.prerequisite {{ border-left-color:var(--amber); }}
.ai-shift {{ border-left-color:var(--ai); background:color-mix(in srgb,var(--ai) 8%,var(--paper-2)); }}
.ai-shift .callout-title {{ color:var(--ai); }}
.expert {{ border-left-color:var(--amber); }}
.journey-map {{ display:grid; grid-template-columns:repeat(9,minmax(0,1fr)); gap:.4rem;
  margin:1.15rem 0; padding:1rem; border:1px solid var(--line); border-radius:.9rem; background:var(--paper-2); }}
.journey-node {{ min-height:4.5rem; padding:.58rem .4rem; border:1px solid var(--line); border-radius:.62rem;
  color:var(--muted); background:var(--paper); text-align:center; font-size:.7rem; line-height:1.35; }}
.journey-node b {{ display:grid; place-items:center; width:1.55rem; height:1.55rem; margin:0 auto .32rem;
  border-radius:50%; color:var(--teal); background:color-mix(in srgb,var(--teal) 12%,var(--paper)); }}
.journey-node.active {{ color:white; border-color:var(--teal); background:linear-gradient(145deg,var(--teal),var(--navy));
  box-shadow:0 8px 22px color-mix(in srgb,var(--teal) 25%,transparent); transform:translateY(-2px); }}
.journey-node.active b {{ color:var(--teal); background:white; }}
.chapter-position {{ display:grid; grid-template-columns:1fr 1.12fr 1fr; gap:.65rem; margin:1rem 0 1.25rem; }}
.position-card {{ display:flex; flex-direction:column; min-width:0; padding:.75rem .85rem;
  border:1px solid var(--line); border-radius:.7rem; color:var(--ink); background:var(--paper-2);
  text-decoration:none; line-height:1.4; }}
.position-card span {{ color:var(--muted); font-size:.68rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }}
.position-card strong {{ margin-top:.25rem; font-size:.84rem; }}
.position-card.current {{ border-color:var(--teal); background:color-mix(in srgb,var(--teal) 10%,var(--paper)); }}
.position-card.muted {{ opacity:.7; }}
.term-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.8rem; margin:1rem 0 1.6rem; }}
.term-card {{ min-width:0; padding:1rem; border:1px solid var(--line); border-top:5px solid var(--amber);
  border-radius:.82rem; background:var(--paper-2); }}
.term-card h3 {{ margin:0 0 .75rem; color:var(--ink); }}
.term-card div {{ padding:.63rem .72rem; border-radius:.6rem; background:var(--paper); }}
.term-card div + div {{ margin-top:.5rem; }}
.term-card span,.context-grid span {{ display:block; margin-bottom:.15rem; color:var(--teal);
  font-size:.67rem; font-weight:850; letter-spacing:.075em; text-transform:uppercase; }}
.term-card p,.context-grid p {{ margin:0; font-size:.9rem; line-height:1.6; }}
.term-card .example {{ border-left:3px solid var(--navy); }}
.term-card .relevance {{ border-left:3px solid var(--teal); }}
.context-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.7rem; margin:1rem 0 1.5rem; }}
.context-grid section {{ padding:.88rem; border:1px solid var(--line); border-radius:.72rem; background:var(--paper-2); }}
.ascii-diagram {{ border-left:6px solid var(--teal); white-space:pre; }}
.flow-grid,.walkthrough-grid {{ display:grid; gap:.62rem; margin:1rem 0 1.35rem; }}
.flow-card {{ display:grid; grid-template-columns:2.2rem 1fr; align-items:start; gap:.72rem;
  padding:.75rem .9rem; border:1px solid var(--line); border-radius:.72rem; background:var(--paper-2); }}
.flow-card > span {{ display:grid; place-items:center; width:2rem; height:2rem; border-radius:50%;
  color:white; background:var(--teal); font-size:.78rem; font-weight:850; }}
.walkthrough-grid .flow-card > span {{ background:var(--navy); }}
.flow-card p {{ margin:.08rem 0; line-height:1.58; }}
.comparison {{ display:grid; grid-template-columns:1fr 1fr; gap:.8rem; margin:1rem 0 1.4rem; }}
.compare-card {{ padding:1rem; border:1px solid var(--line); border-radius:.78rem; background:var(--paper-2); }}
.compare-card h3 {{ margin:0 0 .5rem; }}
.compare-card ul {{ margin:.4rem 0 0; padding-left:1.25rem; }}
.positive {{ border-top:5px solid var(--ai); }}
.positive h3 {{ color:var(--ai); }}
.guardrail {{ border-top:5px solid var(--red); }}
.guardrail h3 {{ color:var(--red); }}
pre {{ margin:1rem 0; padding:1rem 1.1rem; overflow:auto; border:1px solid var(--line);
  border-radius:.78rem; background:var(--code); line-height:1.52; tab-size:4; }}
pre code {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:.84rem; }}
.highlight {{ margin:1rem 0; border:1px solid var(--line); border-radius:.78rem; overflow:auto; background:#f6f8fa; }}
.highlight pre {{ margin:0; border:0; background:transparent; }}
html[data-theme="dark"] .highlight {{ filter:invert(.88) hue-rotate(180deg); }}
code {{ padding:.12em .32em; border-radius:.32rem; background:var(--code);
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.88em; }}
table {{ width:100%; margin:1.2rem 0; border-collapse:collapse; font-size:.91rem; }}
th,td {{ padding:.58rem .68rem; border:1px solid var(--line); text-align:left; vertical-align:top; }}
th {{ background:color-mix(in srgb,var(--teal) 9%,var(--paper)); }}
blockquote {{ margin:1.1rem 0; padding:.78rem 1rem; border-left:5px solid var(--teal); background:var(--paper-2); }}
details.qa {{ margin:.72rem 0; padding:.78rem .95rem; border:1px solid var(--line);
  border-radius:.72rem; background:var(--paper-2); }}
details.qa summary {{ color:var(--navy); font-weight:760; cursor:pointer; }}
details.qa[open] summary {{ margin-bottom:.65rem; }}
.search-results {{ display:none; max-width:74rem; margin:0 auto 1.5rem; padding:1rem;
  border:1px solid var(--line); border-radius:.8rem; background:var(--paper); box-shadow:var(--shadow); }}
.search-results.show {{ display:block; }}
.search-results h2 {{ margin:0; border:0; font-size:1rem; }}
.search-results ul {{ margin:.5rem 0 0; padding:0; list-style:none; }}
.search-results li + li {{ border-top:1px solid var(--line); }}
.search-results a {{ display:block; padding:.55rem .2rem; text-decoration:none; }}
.search-results small {{ display:block; color:var(--muted); }}
.back-top {{ position:fixed; z-index:30; right:1.1rem; bottom:1.1rem; width:2.8rem; height:2.8rem;
  border:1px solid var(--line); border-radius:50%; color:var(--ink); background:var(--paper);
  box-shadow:var(--shadow); cursor:pointer; }}
.mobile-nav {{ display:none; }}
{pygments_css}
@media(max-width:980px) {{
  .sidebar {{ transform:translateX(-103%); transition:transform .2s ease; box-shadow:var(--shadow); }}
  body.nav-open .sidebar {{ transform:translateX(0); }}
  .hero,.main {{ margin-left:0; }}
  .mobile-nav {{ display:inline-flex; }}
  .journey-map {{ grid-template-columns:repeat(3,minmax(0,1fr)); }}
  .context-grid,.comparison {{ grid-template-columns:1fr; }}
}}
@media(max-width:620px) {{
  .hero {{ padding-top:3rem; }}
  .chapter {{ padding:1.15rem; border-radius:.75rem; }}
  .golden-path {{ font-size:.7rem; }}
  .journey-map,.term-grid,.chapter-position {{ grid-template-columns:1fr; }}
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
    <input id="search" type="search" placeholder="搜尋 SLO、review、agent…" autocomplete="off"></div>
  <nav>{nav}</nav>
</aside>
<header class="hero">
  <div class="hero-inner">
    <p class="eyebrow">Software Engineering · Site Reliability Engineering · AI, as of 2026-09-30</p>
    <h1>從 Commit 到可靠服務</h1>
    <p class="subtitle">整合《Software Engineering at Google》與《Site Reliability Engineering》，從零建立 codebase、delivery、production、incident 與 AI-assisted engineering 的完整心智模型。</p>
    <pre class="golden-path">Intent → Design → Code → Review → Test / Build → CI → Release → Production
  ↑                                                                  ↓
  └──── Docs / Rules / Platform ← Postmortem ← Incident ← SLO / Telemetry

AI Agent: 取得 bounded context → 在 sandbox 行動 → deterministic gates
          → independent review → canary → eval / audit → earned autonomy</pre>
    <div class="badges">
      <span class="badge">48 章</span>
      <span class="badge">{term_count} 張先備概念卡</span>
      <span class="badge">{qa_count} 組 Follow-up Q&amp;A</span>
      <span class="badge">{lab_count} 個實作步驟</span>
      <span class="badge">{source_count} 個官方來源</span>
      <span class="badge">每章 AI Shift + Guardrails</span>
      <span class="badge">Python · YAML · Production cases</span>
      <span class="badge">零背景、自包含</span>
    </div>
    <div class="hero-actions">
      <button class="button mobile-nav" id="nav-toggle">☰ 目錄</button>
      <a class="button" href="#start-here">從零開始 ↓</a>
      <a class="button" href="epub/software-engineering-sre-ai.epub" download>下載 EPUB</a>
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
const saved=localStorage.getItem("swe-sre-ai-theme");
if(saved) root.dataset.theme=saved;
document.getElementById("theme-toggle").addEventListener("click",()=>{{
  const next=root.dataset.theme==="dark"?"light":"dark";
  root.dataset.theme=next;localStorage.setItem("swe-sre-ai-theme",next);
}});
document.getElementById("nav-toggle").addEventListener("click",()=>document.body.classList.toggle("nav-open"));
document.querySelectorAll(".sidebar a").forEach(a=>a.addEventListener("click",()=>document.body.classList.remove("nav-open")));
document.getElementById("expand-all").addEventListener("click",event=>{{
  const details=[...document.querySelectorAll("details.qa")];
  const open=details.some(item=>!item.open);details.forEach(item=>item.open=open);
  event.currentTarget.textContent=open?"收合所有 Q&A":"展開所有 Q&A";
}});
const search=document.getElementById("search");const results=document.getElementById("search-results");
const escapeHtml=value=>value.replace(/[&<>"']/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}})[c]);
search.addEventListener("input",()=>{{
  const q=search.value.trim().toLocaleLowerCase();
  if(!q){{results.classList.remove("show");results.innerHTML="";return;}}
  const hits=searchIndex.filter(x=>(x.title+" "+x.part+" "+x.text).toLocaleLowerCase().includes(q)).slice(0,60);
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
const updateProgress=()=>{{const max=document.documentElement.scrollHeight-innerHeight;
  progress.style.width=`${{max>0?scrollY/max*100:0}}%`;}}
addEventListener("scroll",updateProgress,{{passive:true}});addEventListener("resize",updateProgress);updateProgress();
document.getElementById("back-top").addEventListener("click",()=>scrollTo({{top:0,behavior:"smooth"}}));
const navLinks=new Map([...document.querySelectorAll(".nav-group a")].map(a=>[a.getAttribute("href").slice(1),a]));
const observer=new IntersectionObserver(entries=>{{
  const visible=entries.filter(e=>e.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top)[0];
  if(!visible)return;navLinks.forEach(a=>a.classList.remove("active"));navLinks.get(visible.target.id)?.classList.add("active");
}},{{rootMargin:"-10% 0px -75% 0px"}});
document.querySelectorAll("article.chapter").forEach(ch=>observer.observe(ch));
</script>
</body>
</html>
"""


if __name__ == "__main__":
    build()
