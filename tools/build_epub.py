#!/usr/bin/env python3
"""Build an EPUB 3 for every book HTML file in the repository root.

Design notes
------------
* The books are self-contained HTML with their own <style> blocks, so we keep
  that CSS verbatim -- that is what preserves each book's look.
* EPUB readers do not run JavaScript, so any code block that relied on
  highlight.js at runtime is tokenised here with Pygments instead. Blocks that
  already carry server-side Pygments spans are left untouched.
* Each chapter becomes its own XHTML file, which is what gives readers a real
  table of contents and sane pagination.

Usage:  tools/build_epub.py [book.html ...]      (default: all books)
"""
from __future__ import annotations

import html
import os
import re
import sys
import unicodedata
import uuid
import zipfile
from datetime import datetime, timezone
from xml.etree import ElementTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import epub_lib as E  # noqa: E402

from pygments import highlight as pyg_highlight  # noqa: E402
from pygments.formatters import HtmlFormatter  # noqa: E402
from pygments.lexers import get_lexer_by_name  # noqa: E402
from pygments.util import ClassNotFound  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "epub")
BOX = set("─│┌┐└┘├┤┬┴┼━┃╔╗╚╝║═")

FORMATTER = HtmlFormatter(nowrap=True)

# ---------------------------------------------------------------- highlighting

LANG_ALIASES = {
    "c": "c", "cpp": "cpp", "c++": "cpp", "python": "python", "py": "python",
    "bash": "bash", "sh": "bash", "shell": "bash", "zsh": "bash",
    "java": "java", "go": "go", "golang": "go", "rust": "rust",
    "javascript": "javascript", "js": "javascript", "typescript": "typescript",
    "json": "json", "yaml": "yaml", "yml": "yaml", "sql": "sql",
    "html": "html", "xml": "xml", "css": "css", "diff": "diff",
    "protobuf": "protobuf", "proto": "protobuf", "cuda": "cuda", "make": "make",
    "dockerfile": "docker", "ini": "ini", "toml": "toml", "text": None,
    "plaintext": None, "none": None,
}

# Two independent markers required, so prose, output dumps and ASCII art are
# left alone rather than mis-highlighted.
GUESS = [
    ("python", [r"^\s*def\s+\w+\s*\(", r"^\s*import\s+\w", r"^\s*from\s+\w+\s+import",
                r"\bself\.", r"^\s*class\s+\w+.*:", r"^\s*elif\b", r'f"', r"print\("]),
    ("java", [r"\bpublic\s+(?:static\s+)?(?:class|void|int)", r"System\.out\.print",
              r"^\s*private\s+\w", r"\bnew\s+[A-Z]\w*\(", r"@Override"]),
    ("cpp", [r"^\s*#include\s*[<\"]", r"\bstd::", r"\bint\s+main\s*\(",
             r"\bprintf\s*\(", r"\bmalloc\s*\(", r"->\w+\("]),
    ("go", [r"^\s*func\s+\w", r"^\s*package\s+\w", r":=", r"\bgoroutine\b",
            r"\bchan\s+\w"]),
    ("bash", [r"^\s*#!/bin/(?:ba)?sh", r"^\s*\$\s+\w", r"\bsudo\s+\w",
              r"\b(?:apt-get|yum|brew)\s+install", r"^\s*(?:grep|awk|sed|curl|ls|cat)\s+-"]),
    ("sql", [r"\bSELECT\b.*\bFROM\b", r"\bWHERE\b", r"\bJOIN\b", r"\bGROUP\s+BY\b"]),
    ("yaml", [r"^\s*apiVersion:", r"^\s*kind:", r"^\s*metadata:", r"^\s*spec:"]),
]


def lang_from_classes(classes):
    for c in classes:
        key = c[9:] if c.startswith("language-") else c
        if key in LANG_ALIASES:
            return LANG_ALIASES[key]
    return None


def guess_lang(text):
    if BOX & set(text):                       # an ASCII diagram, not code
        return None
    if len(text.strip()) < 24:
        return None
    for lang, pats in GUESS:
        hits = sum(1 for p in pats if re.search(p, text, re.M))
        if hits >= 2:
            return lang
    return None


def highlight_block(text, lang):
    try:
        lexer = get_lexer_by_name(lang, stripnl=False, ensurenl=False)
    except ClassNotFound:
        return None
    try:
        return pyg_highlight(text, lexer, FORMATTER)
    except Exception:
        return None


def highlight_tree(body):
    """Tokenise code blocks that carry no markup yet. Returns (done, guessed)."""
    done = guessed = 0
    for pre in [n for n in body.iter() if n.tag == "pre"]:
        if any(x.tag == "span" and x.cls() for x in pre.iter()):
            continue                          # already tokenised (Pygments)
        codes = [n for n in pre.iter() if n.tag == "code"]
        target = codes[0] if codes else pre
        text = target.inner_text()
        if not text.strip():
            continue
        lang = lang_from_classes(target.cls() + pre.cls())
        was_guess = False
        if not lang:
            lang = guess_lang(text)
            was_guess = bool(lang)
        if not lang:
            continue
        out = highlight_block(text, lang)
        if not out:
            continue
        frag, _, _ = E.parse(f"<body>{out}</body>")
        target.kids = frag.kids
        done += 1
        guessed += 1 if was_guess else 0
    return done, guessed


def expand_details(body):
    """Flatten interactive details into always-visible EPUB content.

    EPUB readers vary widely in their support for <details>. Converting the
    element to a normal <div> is stronger than merely adding ``open``: the
    explanation remains visible even in readers that ignore disclosure
    widgets entirely.
    """
    expanded = 0

    def add_class(node, name):
        classes = node.cls()
        if name not in classes:
            classes.append(name)
        node.attrs = [(k, v) for k, v in node.attrs if k != "class"]
        node.attrs.append(("class", " ".join(classes)))

    for node in [n for n in body.iter() if n.tag == "details"]:
        node.tag = "div"
        node.attrs = [(k, v) for k, v in node.attrs if k != "open"]
        add_class(node, "epub-expanded")
        for child in node.elements():
            if child.tag == "summary":
                child.tag = "div"
                add_class(child, "callout-title")
                add_class(child, "epub-summary")
        expanded += 1
    return expanded


# ------------------------------------------------------------------------ CSS

def pygments_css():
    """Token colours, scoped to <pre> so short class names cannot collide."""
    raw = HtmlFormatter(style="friendly").get_style_defs(".__T")
    out = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith(".__T"):
            continue
        out.append(line.replace(".__T .", "pre .").replace(".__T", "pre"))
    return "\n".join(out)


EPUB_CSS = """
/* --- EPUB overrides: the reader owns the page, not the document --- */
html, body { max-width: none !important; margin: 0 !important;
             padding: 0 1em !important; font-size: 1em !important;
             line-height: 1.7 !important; }
body { background: #fff !important; color: #1a1a1a !important; }
img, svg { max-width: 100%; height: auto; }
table { display: table; width: 100%; border-collapse: collapse;
        font-size: 0.85em; table-layout: fixed; }
td, th { word-wrap: break-word; overflow-wrap: break-word; }
/* Keep long code and ASCII diagrams readable instead of clipped. */
pre { white-space: pre-wrap !important; word-wrap: break-word;
      overflow-wrap: break-word; font-size: 0.8em; padding: 0.8em;
      border-radius: 4px; }
pre code { white-space: inherit; }
/* ASCII diagrams must keep their own spacing. */
.diagram, .ascii-diagram { white-space: pre-wrap !important;
      font-family: monospace; font-size: 0.78em; }
h1 { page-break-before: always; break-before: page; }
h1, h2, h3, h4 { page-break-after: avoid; break-after: avoid; }
.epub-expanded { display: block !important; }
.epub-expanded > * { display: block !important; }
.epub-summary { margin-bottom: 0.7em; font-weight: bold; }
/* Anything sticky/fixed breaks paginated readers. */
* { position: static !important; }
"""

TITLE_CSS = """
.cc-title { text-align: center; margin-top: 25%; }
.cc-title h1 { page-break-before: avoid; border: none; font-size: 1.8em; }
.cc-title .sub { color: #555; font-size: 0.95em; margin-top: 0.8em; }
.cc-title .meta { color: #777; font-size: 0.8em; margin-top: 2.5em; }
"""

# -------------------------------------------------------------------- helpers

XHTML_DOC = ('<?xml version="1.0" encoding="utf-8"?>\n'
             '<!DOCTYPE html>\n'
             '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-Hant" lang="zh-Hant">\n'
             '<head><meta charset="utf-8"/><title>{title}</title>'
             '<link rel="stylesheet" type="text/css" href="style.css"/></head>\n'
             '<body>\n{body}\n</body>\n</html>\n')


def slugify(name):
    base = os.path.splitext(os.path.basename(name))[0]
    base = unicodedata.normalize("NFKC", base)
    out = []
    for ch in base:
        if ch.isalnum() and ord(ch) < 128:
            out.append(ch.lower())
        elif ch.isalnum():
            out.append(ch)          # keep CJK so titles stay recognisable
        else:
            out.append("-")
    s = re.sub(r"-+", "-", "".join(out)).strip("-")
    return s or "book"


def pick_level(body):
    h1 = sum(1 for n in body.iter() if n.tag == "h1")
    h2 = sum(1 for n in body.iter() if n.tag == "h2")
    # A book whose chapters are h2 typically has 1-2 h1s (title / part banners).
    return 1 if h1 >= 5 else (2 if h2 >= 3 else 1)


def validate(xhtml, label):
    try:
        ElementTree.fromstring(xhtml)
    except ElementTree.ParseError as exc:
        raise SystemExit(f"  ✘ {label}: 產生的 XHTML 不合法 -> {exc}")


def rewrite_anchors(sections, id_home):
    """Retarget in-book '#id' links, and neutralise links that cannot resolve.

    A dangling href is a hard epubcheck error, so any link we cannot point at
    real content loses its href and stays as plain text.
    """
    fixed = dropped = 0
    for nodes in sections:
        for root in nodes:
            if not root.tag:
                continue
            for n in root.iter():
                if n.tag != "a":
                    continue
                href = n.get("href")
                if href is None:
                    continue
                keep = True
                if href.startswith("#"):
                    home = id_home.get(href[1:])
                    if home:
                        n.attrs = [(k, f"{home}{href}") if k == "href" else (k, v)
                                   for k, v in n.attrs]
                        fixed += 1
                    else:
                        keep = False        # target id does not exist anywhere
                elif not re.match(r"^(?:https?:|mailto:|tel:)", href):
                    keep = False            # relative link to something absent
                if not keep:
                    n.attrs = [(k, v) for k, v in n.attrs if k != "href"]
                    dropped += 1
    return fixed, dropped


# --------------------------------------------------------------------- build

def build(src):
    name = os.path.basename(src)
    raw = open(src, encoding="utf-8", errors="replace").read()
    body, css, doc_title = E.parse(raw)
    title = doc_title or os.path.splitext(name)[0]
    title = re.sub(r"^[\W_]+", "", title).strip() or os.path.splitext(name)[0]

    n_expanded = expand_details(body)
    n_hl, n_guess = highlight_tree(body)

    container = E.chapter_container(body)
    level = pick_level(body)
    marked_chapters = [
        n for n in body.iter()
        if n.tag == "article" and "chapter" in n.cls()
    ]
    groups = (
        [[chapter] for chapter in marked_chapters]
        if len(marked_chapters) >= 2
        else E.split_sections(container, level)
    )

    # Map every id to the file it will live in, then fix cross-file anchors.
    id_home = {}
    for i, group in enumerate(groups, start=1):
        fname = f"ch{i:03d}.xhtml"
        for root in group:
            if not root.tag:
                continue
            for n in root.iter():
                nid = n.get("id")
                if nid:
                    id_home.setdefault(nid, fname)
    n_anchor, n_dropped = rewrite_anchors(groups, id_home)

    slug = slugify(name)
    out_path = os.path.join(OUT_DIR, slug + ".epub")
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Derived from the slug so rebuilds keep a stable identifier.
    book_id = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, "cc-notes/" + slug))

    chapters = []
    for i, group in enumerate(groups, start=1):
        fname = f"ch{i:03d}.xhtml"
        ctitle = E.section_title(group, level)
        inner = "".join(n.to_xhtml() if n.tag else E.esc_text(n.text) for n in group)
        doc = XHTML_DOC.format(title=html.escape(ctitle), body=inner)
        validate(doc, f"{name} / {fname}")
        chapters.append((fname, ctitle, doc))

    # Title page
    tp_body = (f'<div class="cc-title"><h1>{html.escape(title)}</h1>'
               f'<p class="sub">CC Notes 電子書</p>'
               f'<p class="meta">共 {len(chapters)} 章 · 由 {html.escape(name)} 轉換</p></div>')
    tp = XHTML_DOC.format(title=html.escape(title), body=tp_body)
    validate(tp, f"{name} / title")

    style = "\n".join([css, pygments_css(), EPUB_CSS, TITLE_CSS])

    nav_items = "".join(
        f'<li><a href="{f}">{html.escape(t)}</a></li>' for f, t, _ in chapters)
    nav = (
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
        'xml:lang="zh-Hant" lang="zh-Hant">\n<head><meta charset="utf-8"/>'
        f'<title>目錄</title></head>\n<body>\n<nav epub:type="toc" id="toc">\n<h1>目錄</h1>\n'
        f'<ol><li><a href="title.xhtml">封面</a></li>{nav_items}</ol>\n</nav>\n</body>\n</html>\n')
    validate(nav, f"{name} / nav")

    ncx_items = "".join(
        f'<navPoint id="n{i}" playOrder="{i}"><navLabel><text>{html.escape(t)}</text>'
        f'</navLabel><content src="{f}"/></navPoint>'
        for i, (f, t, _) in enumerate(chapters, start=2))
    ncx = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
           f'<head><meta name="dtb:uid" content="{book_id}"/></head>\n'
           f'<docTitle><text>{html.escape(title)}</text></docTitle>\n<navMap>'
           '<navPoint id="n1" playOrder="1"><navLabel><text>封面</text></navLabel>'
           '<content src="title.xhtml"/></navPoint>'
           f'{ncx_items}</navMap>\n</ncx>\n')
    validate(ncx, f"{name} / ncx")

    manifest = "".join(f'<item id="c{i}" href="{f}" media-type="application/xhtml+xml"/>'
                       for i, (f, _, _) in enumerate(chapters, start=1))
    spine = "".join(f'<itemref idref="c{i}"/>' for i in range(1, len(chapters) + 1))
    opf = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">\n'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
           f'<dc:identifier id="bookid">{book_id}</dc:identifier>\n'
           f'<dc:title>{html.escape(title)}</dc:title>\n'
           '<dc:language>zh-Hant</dc:language>\n'
           '<dc:creator>CC Notes</dc:creator>\n'
           f'<meta property="dcterms:modified">{stamp}</meta>\n</metadata>\n'
           '<manifest>\n<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
           '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
           '<item id="css" href="style.css" media-type="text/css"/>'
           '<item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>'
           f'{manifest}\n</manifest>\n'
           f'<spine toc="ncx"><itemref idref="title"/>{spine}</spine>\n</package>\n')
    validate(opf, f"{name} / opf")

    container_xml = ('<?xml version="1.0" encoding="utf-8"?>\n'
                     '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
                     '<rootfiles><rootfile full-path="OEBPS/content.opf" '
                     'media-type="application/oebps-package+xml"/></rootfiles>\n</container>\n')

    with zipfile.ZipFile(out_path, "w") as z:
        # The mimetype entry must come first and be stored uncompressed.
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip",
                   compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container_xml, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/nav.xhtml", nav, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/toc.ncx", ncx, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/style.css", style, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/title.xhtml", tp, zipfile.ZIP_DEFLATED)
        for f, _, doc in chapters:
            z.writestr(f"OEBPS/{f}", doc, zipfile.ZIP_DEFLATED)

    size = os.path.getsize(out_path)
    print(f"  ✔ {name[:42]:44} -> {slug}.epub  "
          f"{len(chapters):>3} 章  h{level}  上色 {n_hl:>3}(推測 {n_guess})  "
          f"展開 {n_expanded:>3}  錨點 {n_anchor:>4} 移除 {n_dropped:>3}  "
          f"{size/1048576:.1f}MB")
    return slug, title, len(chapters), size


def main():
    args = sys.argv[1:]
    if args:
        books = [os.path.join(ROOT, a) if not os.path.isabs(a) else a for a in args]
    else:
        books = sorted(
            os.path.join(ROOT, f) for f in os.listdir(ROOT)
            if f.endswith(".html") and f != "index.html")
    print(f"產生 EPUB（輸出至 {os.path.relpath(OUT_DIR, ROOT)}/）")
    rows = [build(b) for b in books]
    total = sum(r[3] for r in rows)
    print(f"\n完成 {len(rows)} 本，合計 {total/1048576:.1f}MB")


if __name__ == "__main__":
    main()
