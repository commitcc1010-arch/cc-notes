#!/usr/bin/env python3
"""Add a deterministic, idempotent deepening layer to the CS:APP book."""
from __future__ import annotations

import html
import re
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter

from csapp_supplement_appendices import (
    COVERAGE,
    EXTRA_GLOSSARY,
    FORMULAS,
    GUIDE,
    LABS,
    METHOD,
    WORK,
)
from csapp_practical_examples import EXAMPLES
from csapp_supplement_model import SOURCES, Supplement
from csapp_supplement_part01 import SUPPLEMENTS as PART01
from csapp_supplement_part02 import SUPPLEMENTS as PART02
from csapp_supplement_part03 import SUPPLEMENTS as PART03


ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "CSAPP_系統思維學習手冊.html"
SUPPLEMENTS: list[Supplement] = PART01 + PART02 + PART03
EXAMPLES_BY_ID = {item.section_id: item for item in EXAMPLES}

BLOCK_RE = re.compile(
    r"(?:[ \t]*\n)*<!-- CSAPP-ENRICHMENT START [^>]+ -->.*?"
    r"<!-- CSAPP-ENRICHMENT END [^>]+ -->(?:[ \t]*\n)*",
    re.S,
)
CSS_RE = re.compile(
    r"(?:[ \t]*\n)*/\* CSAPP ENRICHMENT CSS START \*/.*?"
    r"/\* CSAPP ENRICHMENT CSS END \*/(?:[ \t]*\n)*",
    re.S,
)


def md(value: str) -> str:
    return markdown.markdown(
        value.strip(),
        extensions=["extra", "sane_lists", "fenced_code", "codehilite"],
        extension_configs={
            "codehilite": {
                "guess_lang": False,
                "css_class": "highlight",
                "linenums": False,
            }
        },
        output_format="html5",
    )


def inline(value: str) -> str:
    rendered = markdown.markdown(value, extensions=["sane_lists"], output_format="html5")
    if rendered.startswith("<p>") and rendered.endswith("</p>"):
        return rendered[3:-4]
    return rendered


def render_terms(item: Supplement) -> str:
    cards = []
    for term in item.terms:
        cards.append(
            '<article class="deep-term">'
            f"<h4>{html.escape(term.name)}</h4>"
            f"<p>{html.escape(term.plain)}</p>"
            f'<p class="term-example"><strong>例：</strong>{html.escape(term.example)}</p>'
            "</article>"
        )
    return '<div class="deep-term-grid">' + "".join(cards) + "</div>"


def render_practical(section_id: str) -> str:
    item = EXAMPLES_BY_ID[section_id]
    steps = "".join(
        f'<div class="example-step"><span>{index}</span><p>{inline(step)}</p></div>'
        for index, step in enumerate(item.walkthrough, 1)
    )
    applications = "".join(f"<li>{inline(value)}</li>" for value in item.applications)
    transfers = "".join(
        '<article class="transfer-card">'
        f"<h4>{html.escape(name)}</h4><p>{inline(explanation)}</p></article>"
        for name, explanation in item.transfers
    )
    code = md(f"```python\n{item.code}\n```")
    return (
        '<section class="practical-layer">'
        '<div class="practical-heading"><span>WHY IT MATTERS</span>'
        f"<h3>具體實務案例：{html.escape(item.title)}</h3></div>"
        '<div class="practical-context">'
        f'<article><h4>真實問題</h4><p>{inline(item.situation)}</p></article>'
        f'<article><h4>為何需要本章</h4><p>{inline(item.why)}</p></article>'
        "</div>"
        "<h4>Python 概念模型（可直接執行）</h4>"
        '<p class="model-note">這段程式刻意只保留核心機制，方便先看懂因果；下方會再映射回'
        "真實 C／CPU／OS 邊界。</p>"
        f'<div class="python-example">{code}</div>'
        "<h4>逐步把 Python 映射回系統概念</h4>"
        f'<div class="example-steps">{steps}</div>'
        "<h4>實務上會用在哪裡？</h4>"
        f'<ul class="application-list">{applications}</ul>'
        "<h4>舉一反三：同一個設計模式還在哪裡？</h4>"
        f'<div class="transfer-grid">{transfers}</div>'
        "</section>"
    )


def render_sources(item: Supplement) -> str:
    links = []
    for key in item.sources:
        title, url = SOURCES[key]
        links.append(
            f'<a href="{html.escape(url, quote=True)}">{html.escape(title)}</a>'
        )
    return '<div class="deep-sources"><strong>本章校準來源：</strong>' + " · ".join(links) + "</div>"


def render_prelude(item: Supplement) -> str:
    input_, process, output = item.contract
    return (
        f"<!-- CSAPP-ENRICHMENT START prelude-{item.section_id} -->\n"
        '<div class="deepening-layer">'
        '<div class="deepening-banner"><span>CORE COMPLETION LAYER</span>'
        f"<strong>第 {item.number} 章深化導覽</strong>"
        f"<p>{html.escape(item.question)}</p></div>"
        '<div class="chapter-contract">'
        f'<article><span>輸入與壓力</span><p>{html.escape(input_)}</p></article>'
        f'<article><span>內部責任</span><p>{html.escape(process)}</p></article>'
        f'<article><span>讀完輸出</span><p>{html.escape(output)}</p></article>'
        "</div>"
        "<h3>開始前先補齊的概念</h3>"
        '<p class="bridge-copy">以下名詞只給本章需要的最低背景；先把定義、例子與完整 flow '
        "連起來，再進入細節，不需要跳出本書查詢。</p>"
        f"{render_terms(item)}"
        "<h3>Big Picture：本章完整資料流</h3>"
        f'<pre class="diagram deep-map"><code>{html.escape(item.blueprint)}</code></pre>'
        f'<div class="deep-narrative">{md(item.narrative)}</div>'
        f"{render_practical(item.section_id)}"
        "<h3>可執行的證據實驗</h3>"
        f'<div class="deep-experiment">{md(item.experiment)}</div>'
        "<h3>常見錯誤模型</h3>"
        '<ul class="pitfall-list">'
        + "".join(f"<li>{html.escape(value)}</li>" for value in item.pitfalls)
        + "</ul>"
        + render_sources(item)
        + "</div>\n"
        f"<!-- CSAPP-ENRICHMENT END prelude-{item.section_id} -->"
    )


def render_questions(item: Supplement) -> str:
    rows = [
        f"<!-- CSAPP-ENRICHMENT START qa-{item.section_id} -->",
        '<div class="deepening-questions">',
        "<h3>本章深化 Follow-up Questions &amp; Detailed Answers</h3>",
        '<p class="bridge-copy">先遮住答案口述；答案除了結論，也要包含機制、邊界與實務影響。</p>',
    ]
    for index, (question, answer) in enumerate(item.qa, 1):
        rows.append(
            f'<details class="deep-qa"><summary>深化 Q{index}. '
            f"{html.escape(question)}</summary><div>{md(answer)}</div></details>"
        )
    rows.extend(
        [
            "</div>",
            f"<!-- CSAPP-ENRICHMENT END qa-{item.section_id} -->",
        ]
    )
    return "\n".join(rows)


def marker(name: str, body: str) -> str:
    return (
        f"<!-- CSAPP-ENRICHMENT START {name} -->\n"
        f"{body}\n"
        f"<!-- CSAPP-ENRICHMENT END {name} -->"
    )


def inject_section(source: str, section_id: str, prelude: str, ending: str) -> str:
    opener = f'<section id="{section_id}">'
    start = source.find(opener)
    if start < 0:
        raise ValueError(f"missing section #{section_id}")
    end = source.find("</section>", start)
    if end < 0:
        raise ValueError(f"unterminated section #{section_id}")
    first_h3 = source.find("<h3", start, end)
    if first_h3 < 0:
        first_h3 = end
    source = source[:first_h3] + prelude + "\n" + source[first_h3:]
    end = source.find("</section>", first_h3 + len(prelude))
    suffix = ending + "\n" if ending else ""
    return source[:end] + suffix + source[end:]


def glossary() -> str:
    entries: dict[str, str] = {}
    for item in SUPPLEMENTS:
        for term in item.terms:
            entries.setdefault(term.name, term.plain)
    entries.update(EXTRA_GLOSSARY)
    cards = "".join(
        f'<article><h3>{html.escape(name)}</h3><p>{html.escape(definition)}</p></article>'
        for name, definition in sorted(entries.items(), key=lambda row: row[0].lower())
    )
    return (
        '<section id="glossary"><span class="chapter-tag">Appendix D</span>'
        "<h2>完整核心術語表</h2>"
        "<p>本表是複習索引。第一次遇到術語時，仍應回到對應章節的需求、flow、例子與"
        "failure mode；定義脫離場景很容易變成背誦。</p>"
        f'<div class="glossary-grid">{cards}</div></section>'
    )


CSS = r"""
/* CSAPP ENRICHMENT CSS START */
.deepening-layer {
  margin: 1.6rem 0 2rem;
  padding: 1.15rem;
  border: 1px solid #b9cfc9;
  border-radius: 16px;
  background: linear-gradient(145deg, #f8fcfa, #eef7f4);
  box-shadow: 0 12px 30px rgba(23, 93, 75, .08);
}
.deepening-banner {
  margin: -1.15rem -1.15rem 1.1rem;
  padding: 1rem 1.15rem;
  color: #eefbf7;
  background: linear-gradient(120deg, #174f43, #23745f);
  border-radius: 15px 15px 0 0;
}
.deepening-banner span {
  display: block; font: 700 .68rem/1.2 ui-monospace, monospace;
  letter-spacing: .13em; color: #a9e0d0; margin-bottom: .35rem;
}
.deepening-banner strong { display:block; font-size:1.18rem; }
.deepening-banner p { margin:.35rem 0 0; color:#d9f0e9; }
.chapter-contract {
  display:grid; grid-template-columns:repeat(3,1fr); gap:.7rem; margin:1rem 0 1.35rem;
}
.chapter-contract article, .deep-term, .formula-grid article, .glossary-grid article {
  border:1px solid #cbd9d5; border-radius:10px; background:#fff; padding:.8rem;
}
.chapter-contract span, .deep-term h4 {
  color:#176b57; font-weight:750; font-size:.82rem; letter-spacing:.03em;
}
.chapter-contract p { margin:.35rem 0 0; font-size:.9rem; }
.deep-term-grid {
  display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem; margin:.8rem 0 1.35rem;
}
.deep-term h4 { margin:0 0 .35rem; font-size:.95rem; }
.deep-term p { margin:.2rem 0; font-size:.88rem; }
.deep-term .term-example { color:#4f625d; padding-top:.35rem; border-top:1px dashed #d7e2df; }
.deep-map {
  border-left:5px solid #2f8d74 !important;
  background:#edf7f3 !important;
  color:#163d36 !important;
  font-weight:600;
}
.deep-map code {
  color:#163d36 !important;
  opacity:1 !important;
  text-shadow:none !important;
}
.deep-narrative h3 { margin-top:1.65rem; padding-top:.3rem; border-top:1px solid #cfddd9; }
.deep-narrative h4 { color:#176b57; }
.deep-narrative p, .deep-experiment p { text-align:justify; }
.practical-layer {
  margin:1.8rem 0;
  padding:1rem;
  border:1px solid #d7c89f;
  border-radius:13px;
  background:linear-gradient(145deg,#fffdf7,#f8f2e3);
}
.practical-heading { margin-bottom:.8rem; }
.practical-heading span {
  display:block; color:#8a6225; font:750 .68rem/1.2 ui-monospace,monospace;
  letter-spacing:.12em;
}
.practical-heading h3 { margin:.25rem 0 0; color:#593f18; border:0; }
.practical-context {
  display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem; margin:.8rem 0 1rem;
}
.practical-context article {
  padding:.75rem; border:1px solid #e1d4b5; border-radius:9px; background:#fff;
}
.practical-context h4, .practical-layer > h4 { color:#72501d; }
.practical-context h4 { margin:0 0 .35rem; }
.practical-context p { margin:0; }
.model-note { color:#675f50; font-size:.88rem; }
.python-example .highlight { border:1px solid #c9d7d3; background:#f7faf9; }
.example-steps { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.6rem; }
.example-step {
  display:grid; grid-template-columns:1.8rem 1fr; gap:.5rem; align-items:start;
  padding:.65rem; border-radius:8px; background:#fff; border:1px solid #e3d9c1;
}
.example-step span {
  display:grid; place-items:center; width:1.65rem; height:1.65rem;
  border-radius:50%; color:#fff; background:#8a6225; font-weight:750;
}
.example-step p { margin:0; font-size:.88rem; }
.application-list { columns:2; column-gap:2rem; }
.application-list li { break-inside:avoid; margin-bottom:.45rem; }
.transfer-grid {
  display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.6rem;
}
.transfer-card { padding:.7rem; border-radius:9px; background:#fff; border:1px solid #d8cba9; }
.transfer-card h4 { margin:0 0 .3rem; color:#72501d; }
.transfer-card p { margin:0; font-size:.86rem; }
.deep-experiment {
  background:#fff; border:1px solid #a9c8bf; border-left:5px solid #4f9fd8;
  border-radius:9px; padding:.25rem .9rem; margin:.75rem 0 1.2rem;
}
.pitfall-list { display:grid; gap:.38rem; padding-left:1.4rem; }
.pitfall-list li::marker { color:#b44f45; }
.deep-sources {
  margin-top:1.2rem; padding:.75rem .85rem; background:#e2f0eb; border-radius:8px;
  font-size:.8rem; line-height:1.7;
}
.deep-sources a { color:#176b57; text-decoration:underline; text-underline-offset:2px; }
.deepening-questions { margin:2rem 0; padding-top:.5rem; border-top:3px double #8fb8ac; }
.deep-qa { border-left-color:#2f8d74; }
.deep-qa summary { color:#174f43; }
.bridge-copy { color:#52655f; }
.formula-grid, .glossary-grid {
  display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem; margin:1rem 0;
}
.formula-grid article h3, .glossary-grid article h3 {
  margin:0 0 .35rem; color:#176b57; font-size:.95rem;
}
.formula-grid article p, .glossary-grid article p { margin:.25rem 0; font-size:.88rem; }
.book-progress {
  position:fixed; left:0; top:0; height:4px; width:0; z-index:9999;
  background:linear-gradient(90deg,#4fb39a,#e0a45c); transition:width .08s linear;
}
.nav-search {
  width:100%; margin:.7rem 0; padding:.52rem .62rem; border:1px solid #c9d4d0;
  border-radius:8px; font:inherit; background:#fff;
}
.nav-search-count { display:block; min-height:1.2em; color:#687a74; font-size:.72rem; }
nav a.search-hidden { display:none; }
.highlight { overflow:auto; border-radius:8px; }
.highlight pre { margin:0; }
@media (max-width: 800px) {
  .chapter-contract, .deep-term-grid, .formula-grid, .glossary-grid,
  .practical-context, .example-steps, .transfer-grid { grid-template-columns:1fr; }
  .application-list { columns:1; }
  .deepening-layer { padding:.85rem; }
  .deepening-banner { margin:-.85rem -.85rem 1rem; }
}
@media print {
  .book-progress, .nav-search, .nav-search-count { display:none; }
  .deepening-layer { box-shadow:none; break-inside:auto; }
  .deep-qa > div { display:block; }
}
/* CSAPP ENRICHMENT CSS END */
"""


SCRIPT = r"""
<!-- CSAPP-ENRICHMENT START script -->
<div class="book-progress" id="book-progress" aria-hidden="true"></div>
<script>
(() => {
  const progress = document.getElementById('book-progress');
  const updateProgress = () => {
    const max = document.documentElement.scrollHeight - innerHeight;
    progress.style.width = `${max > 0 ? (scrollY / max) * 100 : 0}%`;
  };
  addEventListener('scroll', updateProgress, {passive:true});
  addEventListener('resize', updateProgress);
  updateProgress();

  const input = document.getElementById('nav-search');
  const count = document.getElementById('nav-search-count');
  const links = [...document.querySelectorAll('nav a[href^="#"]')];
  const searchable = links.map(link => {
    const target = document.querySelector(link.getAttribute('href'));
    return {link, text: `${link.textContent} ${target?.textContent || ''}`.toLowerCase()};
  });
  const filter = () => {
    const query = input.value.trim().toLowerCase();
    let visible = 0;
    for (const item of searchable) {
      const show = !query || item.text.includes(query);
      item.link.classList.toggle('search-hidden', !show);
      if (show) visible++;
    }
    count.textContent = query ? `${visible} 個章節含有「${input.value.trim()}」` : '';
  };
  input.addEventListener('input', filter);
  addEventListener('keydown', event => {
    if (event.key === '/' && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) {
      event.preventDefault(); input.focus();
    }
  });
})();
</script>
<!-- CSAPP-ENRICHMENT END script -->
"""


def validate() -> None:
    assert [item.number for item in SUPPLEMENTS] == list(range(13))
    assert [item.section_id for item in SUPPLEMENTS] == [
        "prereq",
        *[f"ch{number}" for number in range(1, 13)],
    ]
    assert [item.number for item in EXAMPLES] == list(range(13))
    assert set(EXAMPLES_BY_ID) == {item.section_id for item in SUPPLEMENTS}


def build() -> None:
    validate()
    source = BOOK.read_text(encoding="utf-8")
    source = BLOCK_RE.sub("\n", source)
    source = CSS_RE.sub("\n", source)

    source = source.replace("</style>", CSS + "\n</style>", 1)

    guide_block = marker("guide", md(GUIDE))
    source = inject_section(source, "guide", guide_block, "")

    for item in SUPPLEMENTS:
        source = inject_section(
            source,
            item.section_id,
            render_prelude(item),
            render_questions(item),
        )

    source = inject_section(source, "labs", marker("labs", md(LABS)), "")
    source = inject_section(source, "work", marker("work", md(WORK)), "")

    appendices = marker(
        "appendices",
        COVERAGE + "\n" + FORMULAS + "\n" + METHOD + "\n" + glossary(),
    )
    source = source.replace('<section id="sources">', appendices + '\n<section id="sources">', 1)

    nav = marker(
        "nav",
        '<input class="nav-search" id="nav-search" type="search" '
        'placeholder="搜尋全書（按 /）" aria-label="搜尋全書">'
        '<span class="nav-search-count" id="nav-search-count" aria-live="polite"></span>'
        '<a href="#coverage">附錄 A：完整覆蓋表</a>'
        '<a href="#formula-cards">附錄 B：公式與工具</a>'
        '<a href="#research-method">附錄 C：研究方法</a>'
        '<a href="#glossary">附錄 D：核心術語</a>',
    )
    source = source.replace('<a href="#sources">資料來源</a>', nav + '\n<a href="#sources">資料來源</a>', 1)

    source = source.replace(
        '<div class="stat"><strong>80+</strong>深化練習</div>',
        '<div class="stat"><strong>150+</strong>章內問答</div>',
    )
    source = source.replace(
        '<div class="stat"><strong>完整</strong>解題思路</div>',
        '<div class="stat"><strong>30+</strong>架構與流程圖</div>',
    )
    source = source.replace(
        "每章都用同一條學習路徑：先建立直覺，再看機制，最後落到工作中的診斷與設計。",
        "每章先補齊脈絡與先備概念，再沿完整流程拆機制、做可執行實驗，最後落到工作診斷、設計取捨與詳細問答。",
    )
    source = re.sub(
        r"CS:APP 系統思維學習手冊 · 單一 HTML、可離線閱讀 · 最後整理：\d{4}-\d{2}",
        "CS:APP 系統思維學習手冊 · 單一 HTML、可離線閱讀 · 深化版：2026-10",
        source,
    )
    source = source.replace("</body>", SCRIPT + "\n</body>", 1)

    pygments_css = HtmlFormatter(style="friendly").get_style_defs(".highlight")
    if pygments_css not in source:
        source = source.replace("</style>", pygments_css + "\n</style>", 1)

    source = re.sub(r"[ \t]+\n", "\n", source)
    source = re.sub(r"\n{3,}(</section>)", r"\n\n\1", source)
    BOOK.write_text(source, encoding="utf-8")
    details = source.count("<details")
    diagrams = source.count('class="diagram')
    print(
        f"Enriched {BOOK.name}: {len(SUPPLEMENTS)} guided chapters, "
        f"{sum(len(item.qa) for item in SUPPLEMENTS)} new chapter Q&A, "
        f"{details} total folded sections, {diagrams} diagrams, "
        f"{len(source) / 1024:.0f} KB"
    )


if __name__ == "__main__":
    build()
