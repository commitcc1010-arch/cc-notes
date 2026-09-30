#!/usr/bin/env python3
"""Build the Coding Interview Patterns Obsidian notes into one HTML book.

The source remains the Markdown tree under ``Coding Interview Patterns/``.
This builder preserves the useful Obsidian conventions used by the book:

* wikilinks become in-book anchors;
* callouts become styled asides or collapsible details;
* YAML frontmatter is removed from rendered content;
* fenced Python blocks receive static Pygments highlighting;
* every source note and heading gets a stable, unique anchor.

Run with:
    ./.venv-epub/bin/python tools/build_coding_interview_patterns.py
"""
from __future__ import annotations

import html
import json
import re
import unicodedata
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter


ROOT = Path(__file__).resolve().parent.parent
BOOK_DIR = ROOT / "Coding Interview Patterns"
OUTPUT = ROOT / "coding-interview-patterns-160.html"

SOURCE_ORDER = [
    "00 - Book Index.md",
    "01 - How to Use This Book.md",
    "02 - Interview Operating System.md",
    "03 - Pattern Decision Tree.md",
    "Cheat Sheets/Python Interview Toolbox.md",
    "Cheat Sheets/Complexity and Constraints.md",
    "Study Plans/14-Day Sprint.md",
    "Study Plans/21-Day Complete.md",
    *[f"Patterns/{i:02d} - {name}.md" for i, name in enumerate([
        "Hashing and Counting",
        "Two Pointers",
        "Sliding Window",
        "Prefix Sum and Difference Array",
        "Binary Search",
        "Sorting Intervals and Sweep Line",
        "Stack and Monotonic Stack",
        "Linked List",
        "Binary Tree",
        "BST and Trie",
        "Heap Top-K and K-way Merge",
        "Graph DFS and BFS",
        "Graph DAG Union-Find and Shortest Path",
        "Backtracking",
        "Greedy",
        "DP 1D and State Machine",
        "DP 2D Sequence and Interval",
        "Bit Math and Geometry",
        "Data Structure Design",
        "Matrix Simulation and Parsing",
    ], start=1)],
    "Company Playbooks/Big Tech Last-Mile Playbook.md",
    "Modern Interview/AI-Assisted and Practical Coding.md",
    "Mock Interviews/6 Mixed Mock Interviews.md",
    "Sources and Survey Methodology.md",
]

GROUPS = [
    ("開始閱讀", SOURCE_ORDER[:4]),
    ("速查與讀書計畫", SOURCE_ORDER[4:8]),
    ("20 個核心 Patterns", SOURCE_ORDER[8:28]),
    ("公司攻略與模擬", SOURCE_ORDER[28:]),
]

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
WIKILINK_RE = re.compile(
    r"\[\["
    r"(?P<note>[^\]#|]*)"
    r"(?:#(?P<heading>[^\]|]+))?"
    r"(?:\|(?P<label>[^\]]+))?"
    r"\]\]"
)
CALLOUT_RE = re.compile(
    r"^>\s*\[!(?P<kind>[A-Za-z0-9_-]+)\]"
    r"(?P<fold>[+-])?"
    r"(?:\s+(?P<title>.*))?$"
)


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    return text[end + 5 :] if end >= 0 else text


def plain_heading(value: str) -> str:
    value = re.sub(r"\s+\{#[^}]+\}\s*$", "", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = re.sub(r"\*([^*]+)\*", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = WIKILINK_RE.sub(
        lambda m: m.group("label") or m.group("heading") or m.group("note"),
        value,
    )
    return html.unescape(value).strip()


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKC", plain_heading(value)).lower()
    pieces = []
    for char in value:
        if char.isalnum():
            pieces.append(char)
        elif char in "-_":
            pieces.append("-")
        else:
            pieces.append("-")
    return re.sub(r"-+", "-", "".join(pieces)).strip("-") or "section"


def note_id(stem: str) -> str:
    return "note-" + slugify(stem)


def scan_headings(text: str, stem: str):
    """Return heading metadata with stable, note-scoped unique ids."""
    counts: dict[str, int] = {}
    headings = []
    in_fence = False
    for line_number, line in enumerate(text.splitlines()):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if not match:
            continue
        title = plain_heading(match.group(2))
        base = f"{note_id(stem)}--{slugify(title)}"
        counts[base] = counts.get(base, 0) + 1
        anchor = base if counts[base] == 1 else f"{base}-{counts[base]}"
        headings.append({
            "line": line_number,
            "level": len(match.group(1)),
            "title": title,
            "id": anchor,
        })
    return headings


def convert_callouts(text: str) -> str:
    lines = text.splitlines()
    output = []
    i = 0
    in_fence = False
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            output.append(line)
            i += 1
            continue
        match = None if in_fence else CALLOUT_RE.match(line)
        if not match:
            output.append(line)
            i += 1
            continue

        body = []
        i += 1
        while i < len(lines):
            continuation = re.match(r"^>\s?(.*)$", lines[i])
            if not continuation:
                break
            body.append(continuation.group(1))
            i += 1

        kind = slugify(match.group("kind"))
        title = match.group("title") or match.group("kind").replace("-", " ").title()
        title = html.escape(title)
        fold = match.group("fold")
        if fold:
            opened = " open" if fold == "+" else ""
            output.extend([
                "",
                f'<details class="callout callout-{kind}" markdown="1"{opened}>',
                f"<summary>{title}</summary>",
                "",
                *body,
                "",
                "</details>",
                "",
            ])
        else:
            output.extend([
                "",
                f'<aside class="callout callout-{kind}" markdown="1">',
                f'<div class="callout-title">{title}</div>',
                "",
                *body,
                "",
                "</aside>",
                "",
            ])
    return "\n".join(output)


def replace_outside_fences(text: str, replacer):
    output = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            output.append(line)
        elif in_fence:
            output.append(line)
        else:
            output.append(replacer(line))
    return "\n".join(output)


def make_search_text(markdown_text: str) -> str:
    text = re.sub(r"```.*?```", " ", markdown_text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = WIKILINK_RE.sub(
        lambda m: m.group("label") or m.group("heading") or m.group("note"),
        text,
    )
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[#>*_`|{}\[\]]", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def build():
    documents = {}
    heading_target = {}
    titles = {}

    for relative in SOURCE_ORDER:
        path = BOOK_DIR / relative
        if not path.exists():
            raise SystemExit(f"Missing source note: {path}")
        text = strip_frontmatter(path.read_text(encoding="utf-8"))
        stem = path.stem
        headings = scan_headings(text, stem)
        if not headings:
            raise SystemExit(f"No heading found in {path}")
        titles[relative] = headings[0]["title"]
        documents[relative] = {
            "path": path,
            "stem": stem,
            "text": text,
            "headings": headings,
        }
        for item in headings:
            heading_target[(stem, item["title"])] = item["id"]

    stem_to_note = {
        document["stem"]: note_id(document["stem"])
        for document in documents.values()
    }

    articles = []
    search_index = []
    for relative in SOURCE_ORDER:
        document = documents[relative]
        stem = document["stem"]
        current_note_id = stem_to_note[stem]
        text = convert_callouts(document["text"])
        heading_queue = iter(document["headings"])
        next_heading = next(heading_queue, None)

        def transform_line(line: str) -> str:
            nonlocal next_heading
            heading_match = HEADING_RE.match(line)
            if heading_match and next_heading:
                line = (
                    f'{heading_match.group(1)} {heading_match.group(2)} '
                    f'{{#{next_heading["id"]}}}'
                )
                next_heading = next(heading_queue, None)

            def wiki(match: re.Match) -> str:
                target_stem = match.group("note") or stem
                target_heading = match.group("heading")
                label = (
                    match.group("label")
                    or target_heading
                    or target_stem
                )
                if target_heading:
                    anchor = heading_target.get((target_stem, target_heading))
                else:
                    anchor = stem_to_note.get(target_stem)
                return (
                    f"[{label}](#{anchor})"
                    if anchor
                    else label
                )

            line = WIKILINK_RE.sub(wiki, line)
            line = re.sub(r"==(.+?)==", r"<mark>\1</mark>", line)
            line = re.sub(r"^(\s*[-*]\s+)\[ \]\s+", r"\1☐ ", line)
            line = re.sub(r"^(\s*[-*]\s+)\[[xX]\]\s+", r"\1☑ ", line)
            return line

        transformed = replace_outside_fences(text, transform_line)
        rendered = markdown.markdown(
            transformed,
            extensions=[
                "extra",
                "sane_lists",
                "codehilite",
                "md_in_html",
            ],
            extension_configs={
                "codehilite": {
                    "guess_lang": False,
                    "css_class": "highlight",
                    "linenums": False,
                },
            },
            output_format="html5",
        )
        articles.append(
            f'<article class="chapter" id="{current_note_id}" '
            f'data-title="{html.escape(titles[relative], quote=True)}">'
            f"{rendered}</article>"
        )

        heading_items = document["headings"]
        raw_lines = document["text"].splitlines()
        for index, item in enumerate(heading_items):
            start = item["line"] + 1
            end = (
                heading_items[index + 1]["line"]
                if index + 1 < len(heading_items)
                else len(raw_lines)
            )
            search_index.append({
                "title": item["title"],
                "id": item["id"],
                "chapter": titles[relative],
                "text": make_search_text("\n".join(raw_lines[start:end])),
            })

    nav_groups = []
    for label, relatives in GROUPS:
        links = "".join(
            f'<li><a href="#{stem_to_note[documents[relative]["stem"]]}">'
            f'{html.escape(titles[relative])}</a></li>'
            for relative in relatives
        )
        nav_groups.append(
            f'<section class="nav-group"><h2>{html.escape(label)}</h2>'
            f"<ul>{links}</ul></section>"
        )

    pygments_css = HtmlFormatter(style="friendly").get_style_defs(".highlight")
    search_json = json.dumps(search_index, ensure_ascii=False).replace("</", "<\\/")
    doc = TEMPLATE.format(
        pygments_css=pygments_css,
        nav="\n".join(nav_groups),
        articles="\n".join(articles),
        search_json=search_json,
    )
    OUTPUT.write_text(doc, encoding="utf-8")
    print(
        f"Built {OUTPUT.name}: "
        f"{len(SOURCE_ORDER)} notes, {len(search_index)} searchable headings, "
        f"{OUTPUT.stat().st_size / 1024:.0f} KB"
    )


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="20 個 coding interview patterns、160 題視覺化完整題解與 640 組 follow-ups。">
<title>Coding Interview Patterns — 20 Patterns, 160 Problems</title>
<script>
window.MathJax = {{
  tex: {{ inlineMath: [['$', '$'], ['\\(', '\\)']] }},
  options: {{ skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'] }}
}};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<style>
:root {{
  --bg: #f5f7fb;
  --panel: #ffffff;
  --panel-soft: #f0f4fa;
  --text: #172033;
  --muted: #5e6b80;
  --border: #d9e1ec;
  --accent: #2457d6;
  --accent-2: #0f8b8d;
  --accent-soft: #e8efff;
  --code: #f6f8fa;
  --shadow: 0 12px 35px rgba(28, 45, 78, .08);
  --sidebar: 19rem;
}}
html[data-theme="dark"] {{
  --bg: #0f1420;
  --panel: #171e2d;
  --panel-soft: #111827;
  --text: #e6edf7;
  --muted: #9eabc0;
  --border: #2a3549;
  --accent: #78a4ff;
  --accent-2: #5dd1c5;
  --accent-soft: #1c2b4a;
  --code: #0d1117;
  --shadow: 0 16px 40px rgba(0, 0, 0, .24);
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; scroll-padding-top: 1rem; }}
body {{
  margin: 0;
  color: var(--text);
  background: var(--bg);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans TC",
    "PingFang TC", "Microsoft JhengHei", sans-serif;
  line-height: 1.75;
  -webkit-font-smoothing: antialiased;
}}
a {{ color: var(--accent); }}
#progress {{
  position: fixed; z-index: 100; inset: 0 auto auto 0;
  width: 0; height: 3px; background: linear-gradient(90deg, var(--accent), var(--accent-2));
}}
.hero {{
  margin-left: var(--sidebar);
  padding: 3.2rem clamp(1.25rem, 5vw, 5rem) 2.4rem;
  color: white;
  background:
    radial-gradient(circle at 85% 15%, rgba(93, 209, 197, .28), transparent 28rem),
    linear-gradient(135deg, #14295e, #183d7a 55%, #0e6c72);
}}
.hero-inner {{ max-width: 70rem; margin: auto; }}
.eyebrow {{ margin: 0 0 .6rem; font-size: .78rem; letter-spacing: .16em; text-transform: uppercase; opacity: .78; }}
.hero h1 {{ margin: 0; font-size: clamp(2rem, 5vw, 3.6rem); line-height: 1.12; letter-spacing: -.035em; }}
.hero .subtitle {{ max-width: 53rem; margin: 1rem 0 1.4rem; color: #dbe8ff; font-size: 1.06rem; }}
.badges {{ display: flex; flex-wrap: wrap; gap: .55rem; }}
.badge {{ padding: .3rem .7rem; border: 1px solid rgba(255,255,255,.24); border-radius: 99px; background: rgba(255,255,255,.08); font-size: .78rem; }}
.hero-actions {{ display: flex; flex-wrap: wrap; gap: .65rem; margin-top: 1.35rem; }}
.button {{
  display: inline-flex; align-items: center; gap: .4rem; min-height: 2.5rem;
  border: 1px solid rgba(255,255,255,.28); border-radius: .65rem;
  padding: .45rem .8rem; color: white; background: rgba(255,255,255,.08);
  text-decoration: none; font: inherit; cursor: pointer;
}}
.button:hover {{ background: rgba(255,255,255,.16); }}
.sidebar {{
  position: fixed; z-index: 50; inset: 0 auto 0 0; width: var(--sidebar);
  padding: 1.1rem .9rem 2rem; overflow-y: auto;
  background: var(--panel); border-right: 1px solid var(--border);
}}
.brand {{ display: flex; align-items: center; justify-content: space-between; gap: .5rem; padding: .35rem .35rem 1rem; }}
.brand a {{ color: var(--text); font-weight: 800; text-decoration: none; }}
.icon-button {{
  border: 1px solid var(--border); background: var(--panel-soft); color: var(--text);
  border-radius: .55rem; min-width: 2.35rem; height: 2.35rem; cursor: pointer;
}}
.search-wrap {{ position: relative; margin-bottom: 1rem; }}
#search {{
  width: 100%; border: 1px solid var(--border); border-radius: .7rem;
  padding: .65rem .75rem .65rem 2.1rem; color: var(--text); background: var(--panel-soft);
  font: inherit; font-size: .88rem;
}}
.search-icon {{ position: absolute; left: .72rem; top: .65rem; color: var(--muted); }}
.nav-group {{ margin: 1.2rem 0; }}
.nav-group h2 {{ margin: 0 0 .4rem; padding: 0 .45rem; color: var(--muted); font-size: .72rem; letter-spacing: .09em; text-transform: uppercase; }}
.nav-group ul {{ margin: 0; padding: 0; list-style: none; }}
.nav-group a {{
  display: block; padding: .38rem .48rem; border-radius: .45rem;
  color: var(--muted); text-decoration: none; font-size: .83rem; line-height: 1.35;
}}
.nav-group a:hover, .nav-group a.active {{ color: var(--accent); background: var(--accent-soft); }}
.main {{
  margin-left: var(--sidebar);
  max-width: calc(78rem + var(--sidebar));
  padding: 2rem clamp(1rem, 4vw, 4rem) 7rem;
}}
.search-results {{
  display: none; margin: 0 auto 1.5rem; max-width: 70rem;
  padding: 1rem; border: 1px solid var(--border); border-radius: .8rem;
  background: var(--panel); box-shadow: var(--shadow);
}}
.search-results.show {{ display: block; }}
.search-results h2 {{ margin: 0 0 .6rem; border: 0; font-size: 1rem; }}
.search-results ul {{ margin: 0; padding: 0; list-style: none; }}
.search-results li + li {{ border-top: 1px solid var(--border); }}
.search-results a {{ display: block; padding: .55rem .2rem; text-decoration: none; }}
.search-results small {{ display: block; color: var(--muted); }}
.chapter {{
  max-width: 70rem; margin: 0 auto 2rem; padding: clamp(1.2rem, 3vw, 3rem);
  border: 1px solid var(--border); border-radius: 1rem; background: var(--panel);
  box-shadow: var(--shadow);
}}
.chapter > h1:first-child {{ margin-top: 0; }}
h1, h2, h3, h4 {{ line-height: 1.3; scroll-margin-top: 1rem; }}
h1 {{ margin: 2.8rem 0 1.2rem; font-size: clamp(1.75rem, 4vw, 2.4rem); letter-spacing: -.025em; }}
h2 {{ margin: 2.5rem 0 1rem; padding-bottom: .4rem; border-bottom: 1px solid var(--border); font-size: 1.48rem; }}
h3 {{ margin: 1.9rem 0 .65rem; font-size: 1.15rem; color: var(--accent-2); }}
h4 {{ margin: 1.4rem 0 .45rem; font-size: 1rem; }}
p, li {{ overflow-wrap: anywhere; }}
hr {{ margin: 2.5rem 0; border: 0; border-top: 1px solid var(--border); }}
code {{
  padding: .12em .35em; border-radius: .35rem; background: var(--code);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: .88em;
}}
pre {{
  margin: 1rem 0; padding: 1rem 1.1rem; overflow: auto;
  border: 1px solid var(--border); border-radius: .75rem; background: var(--code);
  line-height: 1.55; tab-size: 4;
}}
pre code {{ padding: 0; background: transparent; font-size: .86rem; }}
.highlight {{ margin: 1rem 0; border-radius: .75rem; overflow: auto; background: #f6f8fa; }}
.highlight pre {{ margin: 0; border: 0; background: transparent; }}
html[data-theme="dark"] .highlight {{ filter: invert(.88) hue-rotate(180deg); }}
table {{ width: 100%; margin: 1.2rem 0; border-collapse: collapse; font-size: .92rem; }}
th, td {{ padding: .6rem .7rem; border: 1px solid var(--border); text-align: left; vertical-align: top; }}
th {{ background: var(--accent-soft); }}
tbody tr:nth-child(even) {{ background: color-mix(in srgb, var(--panel-soft) 60%, transparent); }}
blockquote {{ margin: 1.2rem 0; padding: .65rem 1rem; border-left: 4px solid var(--accent); background: var(--panel-soft); }}
.callout {{
  margin: 1.15rem 0; padding: .9rem 1rem; border: 1px solid var(--border);
  border-left: 5px solid var(--accent); border-radius: .7rem; background: var(--panel-soft);
}}
.callout-title, .callout summary {{ color: var(--accent); font-weight: 800; cursor: pointer; }}
.callout-tip {{ border-left-color: #d49a16; }}
.callout-tip > summary, .callout-tip > .callout-title {{ color: #a66d00; }}
.callout-warning {{ border-left-color: #d05b42; }}
.callout-warning > .callout-title {{ color: #b9442d; }}
.callout-abstract {{ border-left-color: var(--accent-2); }}
.callout-success {{ border-left-color: #2f9e65; }}
.callout-success > summary, .callout-success > .callout-title {{ color: #23784d; }}
.callout-question {{ border-left-color: #7b61c9; }}
.callout-question > summary, .callout-question > .callout-title {{ color: #674bb7; }}
.callout p:last-child {{ margin-bottom: 0; }}
details.callout[open] > summary {{ margin-bottom: .7rem; }}
h3[id*="視覺化題解"] + .highlight,
h3[id*="視覺化題解"] + pre {{
  border: 1px solid color-mix(in srgb, var(--accent-2) 45%, var(--border));
  border-left: 6px solid var(--accent-2);
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--accent-soft) 65%, var(--panel)), var(--code));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.04);
}}
h3[id*="視覺化題解"] + .highlight pre,
h3[id*="視覺化題解"] + pre,
h3[id*="視覺化題解"] + pre code {{
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}}
mark {{ padding: .05em .2em; border-radius: .2em; background: #ffe58a; }}
.back-top {{
  position: fixed; z-index: 30; right: 1.2rem; bottom: 1.2rem;
  width: 2.8rem; height: 2.8rem; border: 1px solid var(--border); border-radius: 50%;
  color: var(--text); background: var(--panel); box-shadow: var(--shadow); cursor: pointer;
}}
.mobile-nav {{ display: none; }}
{pygments_css}
@media (max-width: 900px) {{
  .sidebar {{ transform: translateX(-102%); transition: transform .2s ease; box-shadow: var(--shadow); }}
  body.nav-open .sidebar {{ transform: translateX(0); }}
  .hero, .main {{ margin-left: 0; }}
  .mobile-nav {{ display: inline-flex; }}
  .chapter {{ border-radius: .75rem; }}
}}
@media print {{
  #progress, .sidebar, .hero-actions, .back-top, .search-results {{ display: none !important; }}
  .hero, .main {{ margin: 0; padding: 0; }}
  .hero {{ color: #111; background: white; border-bottom: 2px solid #111; }}
  .hero .subtitle {{ color: #333; }}
  .chapter {{ margin: 0; padding: 0; border: 0; box-shadow: none; content-visibility: visible; }}
  .chapter + .chapter {{ page-break-before: always; }}
  details.callout:not([open]) > * {{ display: block; }}
  a {{ color: inherit; text-decoration: none; }}
}}
</style>
</head>
<body>
<div id="progress"></div>
<aside class="sidebar" aria-label="書籍目錄">
  <div class="brand">
    <a href="index.html">← CC Notes 書架</a>
    <button class="icon-button" id="theme-toggle" aria-label="切換深色模式">◐</button>
  </div>
  <div class="search-wrap">
    <span class="search-icon" aria-hidden="true">⌕</span>
    <input id="search" type="search" placeholder="搜尋題目、pattern、關鍵字…" autocomplete="off">
  </div>
  <nav>{nav}</nav>
</aside>

<header class="hero">
  <div class="hero-inner">
    <p class="eyebrow">Coding Interview Field Guide · 2026 Edition</p>
    <h1>Coding Interview Patterns</h1>
    <p class="subtitle">20 個核心模型、160 題視覺化完整題解、640 組 follow-ups，以及每個 domain 的高難度上限與變形。</p>
    <div class="badges">
      <span class="badge">20 Patterns</span>
      <span class="badge">60 核心題</span>
      <span class="badge">100 上限題</span>
      <span class="badge">160 視覺題解</span>
      <span class="badge">640 Follow-ups</span>
      <span class="badge">Python 3</span>
      <span class="badge">14–21 天複習</span>
    </div>
    <div class="hero-actions">
      <button class="button mobile-nav" id="nav-toggle">☰ 目錄</button>
      <a class="button" href="#note-00-book-index">開始閱讀 ↓</a>
      <a class="button" href="epub/coding-interview-patterns-160.epub" download>下載 EPUB</a>
    </div>
  </div>
</header>

<main class="main">
  <section class="search-results" id="search-results" aria-live="polite"></section>
  {articles}
</main>

<button class="back-top" id="back-top" aria-label="回到頁首">↑</button>
<script>
const searchIndex = {search_json};
const root = document.documentElement;
const savedTheme = localStorage.getItem("cc-book-theme");
if (savedTheme) root.dataset.theme = savedTheme;
document.getElementById("theme-toggle").addEventListener("click", () => {{
  const next = root.dataset.theme === "dark" ? "light" : "dark";
  root.dataset.theme = next;
  localStorage.setItem("cc-book-theme", next);
}});
document.getElementById("nav-toggle").addEventListener("click", () => {{
  document.body.classList.toggle("nav-open");
}});
document.querySelectorAll(".sidebar a").forEach(link => link.addEventListener("click", () => {{
  document.body.classList.remove("nav-open");
}}));

const search = document.getElementById("search");
const results = document.getElementById("search-results");
function revealHashTarget() {{
  if (!location.hash) return;
  const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
  if (!target) return;
  target.scrollIntoView({{block: "start"}});
  setTimeout(() => target.scrollIntoView({{block: "start"}}), 0);
}}
addEventListener("hashchange", revealHashTarget);
revealHashTarget();
search.addEventListener("input", () => {{
  const query = search.value.trim().toLocaleLowerCase();
  if (!query) {{
    results.classList.remove("show");
    results.innerHTML = "";
    return;
  }}
  const matches = searchIndex.filter(item =>
    (item.title + " " + item.chapter + " " + item.text)
      .toLocaleLowerCase().includes(query)
  ).slice(0, 40);
  results.innerHTML = `<h2>${{matches.length}} 個搜尋結果</h2><ul>` +
    matches.map(item =>
      `<li><a href="#${{item.id}}"><strong>${{escapeHtml(item.title)}}</strong>` +
      `<small>${{escapeHtml(item.chapter)}}</small></a></li>`
    ).join("") + "</ul>";
  results.classList.add("show");
}});
results.addEventListener("click", () => {{
  results.classList.remove("show");
}});
function escapeHtml(value) {{
  return value.replace(/[&<>"']/g, char => ({{
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }})[char]);
}}
document.addEventListener("keydown", event => {{
  if (event.key === "/" && document.activeElement !== search) {{
    event.preventDefault();
    search.focus();
  }}
  if (event.key === "Escape") {{
    search.blur();
    results.classList.remove("show");
    document.body.classList.remove("nav-open");
  }}
}});

const progress = document.getElementById("progress");
function updateProgress() {{
  const max = document.documentElement.scrollHeight - innerHeight;
  progress.style.width = `${{max > 0 ? scrollY / max * 100 : 0}}%`;
}}
addEventListener("scroll", updateProgress, {{passive: true}});
addEventListener("resize", updateProgress);
updateProgress();

document.getElementById("back-top").addEventListener("click", () =>
  scrollTo({{top: 0, behavior: "smooth"}})
);

const navLinks = new Map(
  [...document.querySelectorAll(".nav-group a")]
    .map(link => [link.getAttribute("href").slice(1), link])
);
const observer = new IntersectionObserver(entries => {{
  const visible = entries
    .filter(entry => entry.isIntersecting)
    .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
  if (!visible) return;
  navLinks.forEach(link => link.classList.remove("active"));
  navLinks.get(visible.target.id)?.classList.add("active");
}}, {{rootMargin: "-10% 0px -75% 0px"}});
document.querySelectorAll("article.chapter").forEach(chapter => observer.observe(chapter));
</script>
</body>
</html>
"""


if __name__ == "__main__":
    build()
