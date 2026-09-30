"""HTML -> XHTML normalisation and lightweight tree building.

The books are single-file HTML with their own <style> blocks. EPUB needs
well-formed XHTML, so we reparse and re-serialise rather than string-patching.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}

# Dropped entirely: EPUB readers do not run scripts, and external CSS/CDN links
# cannot be resolved offline.
DROP_TREE = {"script", "noscript"}
DROP_SELF = {"link", "meta", "base"}

# EPUB 3 content is validated against XHTML5, which rejects legacy presentational
# attributes (cellpadding, align, bgcolor, …) and anything non-standard. Rather
# than denylisting, allow known-good names and drop the rest.
KEEP_PREFIX = ("aria-", "data-", "xml:", "epub:", "xmlns")
GLOBAL_ATTR = {
    "id", "class", "style", "title", "lang", "dir", "hidden", "tabindex", "role",
    "translate", "slot", "is", "itemprop", "itemscope", "itemtype", "itemid",
    "itemref", "inputmode", "enterkeyhint", "spellcheck", "autocapitalize",
}
ELEMENT_ATTR = {
    "a": {"href", "download", "rel", "type", "hreflang"},
    "area": {"href", "alt", "coords", "shape", "rel"},
    "audio": {"src", "controls", "loop", "muted", "preload"},
    "blockquote": {"cite"},
    "button": {"type", "value", "disabled", "name"},
    "canvas": {"width", "height"},
    "col": {"span"},
    "colgroup": {"span"},
    "del": {"cite", "datetime"},
    "details": {"open"},
    "embed": {"src", "type", "width", "height"},
    "iframe": {"src", "width", "height", "allow"},
    "img": {"src", "alt", "width", "height", "usemap", "ismap", "decoding"},
    "ins": {"cite", "datetime"},
    "input": {"type", "value", "name", "checked", "disabled", "readonly",
              "placeholder", "min", "max", "step"},
    "label": {"for"},
    "li": {"value"},
    "ol": {"start", "reversed", "type"},
    "q": {"cite"},
    "source": {"src", "type", "media"},
    "svg": {"width", "height", "viewBox", "viewbox", "xmlns", "fill", "stroke",
            "preserveAspectRatio"},
    "path": {"d", "fill", "stroke", "stroke-width", "fill-rule", "clip-rule"},
    "g": {"fill", "stroke", "transform"},
    "td": {"colspan", "rowspan", "headers"},
    "th": {"colspan", "rowspan", "headers", "scope", "abbr"},
    "textarea": {"rows", "cols", "name", "readonly", "disabled"},
    "time": {"datetime"},
    "video": {"src", "controls", "poster", "width", "height", "loop", "muted",
              "preload"},
}

# Boolean attributes need a value in XML.
BOOL_ATTR = {"open", "checked", "selected", "disabled", "readonly", "multiple",
             "required", "autofocus", "hidden", "novalidate", "reversed"}


class Node:
    __slots__ = ("tag", "attrs", "kids", "text")

    def __init__(self, tag, attrs=None):
        self.tag = tag                 # None => text node
        self.attrs = attrs or []
        self.kids = []
        self.text = ""

    # -- queries -----------------------------------------------------------
    def cls(self):
        for k, v in self.attrs:
            if k == "class":
                return (v or "").split()
        return []

    def get(self, name):
        for k, v in self.attrs:
            if k == name:
                return v
        return None

    def elements(self):
        return [k for k in self.kids if k.tag]

    def iter(self):
        yield self
        for k in self.kids:
            yield from k.iter()

    def inner_text(self):
        if not self.tag:
            return self.text
        return "".join(k.inner_text() for k in self.kids)

    # -- serialisation -----------------------------------------------------
    def xhtml(self, out):
        if not self.tag:
            out.append(esc_text(self.text))
            return
        if self.tag in DROP_TREE or self.tag in DROP_SELF:
            return
        a = "".join(f' {k}="{esc_attr(v)}"' for k, v in self.attrs)
        if self.tag in VOID:
            out.append(f"<{self.tag}{a}/>")
            return
        out.append(f"<{self.tag}{a}>")
        for k in self.kids:
            k.xhtml(out)
        out.append(f"</{self.tag}>")

    def to_xhtml(self):
        out = []
        self.xhtml(out)
        return "".join(out)

    def children_xhtml(self):
        out = []
        for k in self.kids:
            k.xhtml(out)
        return "".join(out)


def esc_text(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def esc_attr(s):
    s = "" if s is None else s
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


class Builder(HTMLParser):
    """Parse HTML into a Node tree, normalising as we go."""

    def __init__(self):
        # convert_charrefs=True turns &amp;/&nbsp; into real characters, which we
        # then re-escape on output -- that is what makes the result valid XML.
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.stack = [self.root]
        self.styles = []
        self.in_style = False
        self.skip_depth = 0
        self.title = None
        self.in_title = False

    # -- helpers -----------------------------------------------------------
    def _attrs(self, tag, attrs):
        out = []
        seen = set()
        allowed = GLOBAL_ATTR | ELEMENT_ATTR.get(tag, set())
        for k, v in attrs:
            k = k.lower()
            if k in seen:
                continue
            if not re.match(r"^[A-Za-z_:][\w.:-]*$", k):
                continue          # not a legal XML attribute name
            if k not in allowed and not k.startswith(KEEP_PREFIX):
                continue          # legacy/presentational/unknown -> drop
            seen.add(k)
            if v is None:
                v = k if k in BOOL_ATTR else ""
            out.append((k, v))
        return out

    # -- parser callbacks --------------------------------------------------
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self.skip_depth:
            if tag in DROP_TREE:
                self.skip_depth += 1
            return
        if tag in DROP_TREE:
            self.skip_depth = 1
            return
        if tag in DROP_SELF:
            return
        if tag == "style":
            self.in_style = True
            return
        if tag == "title":
            self.in_title = True
            return
        if not re.match(r"^[A-Za-z][\w-]*$", tag):
            return
        node = Node(tag, self._attrs(tag, attrs))
        self.stack[-1].kids.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if self.skip_depth or tag in DROP_TREE or tag in DROP_SELF:
            return
        node = Node(tag, self._attrs(tag, attrs))
        self.stack[-1].kids.append(node)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in DROP_TREE:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        if tag == "style":
            self.in_style = False
            return
        if tag == "title":
            self.in_title = False
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]          # auto-closes anything left open
                return

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.in_style:
            self.styles.append(data)
            return
        if self.in_title:
            self.title = (self.title or "") + data
            return
        n = Node(None)
        n.text = data
        self.stack[-1].kids.append(n)


def parse(html):
    b = Builder()
    b.feed(html)
    b.close()
    body = None
    for n in b.root.iter():
        if n.tag == "body":
            body = n
            break
    if body is None:                        # no <body> tag: treat root as body
        body = b.root
    return body, "\n".join(b.styles), (b.title or "").strip()


def chapter_container(body):
    """Find the container whose direct children represent book chapters."""
    for candidate in body.iter():
        if candidate.get("data-epub-chapters") is not None:
            return candidate

    node = body
    while True:
        els = node.elements()
        if len(els) == 1 and els[0].tag in ("div", "main", "section", "article"):
            node = els[0]
            continue
        return node


def split_sections(container, level):
    """Group top-level children into sections starting at each `level` heading."""
    tag = f"h{level}"

    def has_heading(n):
        return any(x.tag == tag for x in n.iter())

    groups, cur = [], []
    for kid in container.kids:
        if kid.tag and has_heading(kid) and cur and any(k.tag for k in cur):
            groups.append(cur)
            cur = [kid]
        else:
            cur.append(kid)
    if cur:
        groups.append(cur)
    return [g for g in groups if any(k.tag or k.text.strip() for k in g)]


def section_title(group, level):
    for kid in group:
        if not kid.tag:
            continue
        for n in kid.iter():
            if n.tag == f"h{level}":
                t = re.sub(r"\s+", " ", n.inner_text()).strip()
                if t:
                    return t
    for kid in group:
        if kid.tag:
            t = re.sub(r"\s+", " ", kid.inner_text()).strip()
            if t:
                return t[:60]
    return "（無標題）"
