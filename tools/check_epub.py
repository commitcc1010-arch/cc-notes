#!/usr/bin/env python3
"""Structural self-check for the generated EPUBs.

Not a substitute for epubcheck, but it catches the failures that actually break
readers: malformed XML, a mis-stored mimetype, manifest/spine gaps, dangling
internal links and oversized chapters.
"""
from __future__ import annotations

import glob
import os
import re
import sys
import zipfile
from xml.etree import ElementTree

NS = {"opf": "http://www.idpf.org/2007/opf",
      "x": "http://www.w3.org/1999/xhtml"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(path):
    problems, notes = [], []
    z = zipfile.ZipFile(path)
    names = z.namelist()

    first = z.infolist()[0]
    if first.filename != "mimetype":
        problems.append("mimetype 不是第一個項目")
    elif first.compress_type != zipfile.ZIP_STORED:
        problems.append("mimetype 被壓縮了（必須 STORED）")
    elif z.read("mimetype") != b"application/epub+zip":
        problems.append("mimetype 內容錯誤")

    for required in ("META-INF/container.xml", "OEBPS/content.opf",
                     "OEBPS/nav.xhtml", "OEBPS/toc.ncx", "OEBPS/style.css"):
        if required not in names:
            problems.append(f"缺少 {required}")

    # Every XML part must parse.
    for n in names:
        if n.endswith((".xhtml", ".opf", ".ncx", ".xml")):
            try:
                ElementTree.fromstring(z.read(n))
            except ElementTree.ParseError as exc:
                problems.append(f"{n} XML 不合法: {exc}")

    opf = ElementTree.fromstring(z.read("OEBPS/content.opf"))
    manifest = {i.get("href"): i.get("id")
                for i in opf.findall(".//opf:manifest/opf:item", NS)}
    ids = set(manifest.values())

    docs = [n[len("OEBPS/"):] for n in names
            if n.startswith("OEBPS/") and n.endswith(".xhtml")]
    for d in docs:
        if d not in manifest:
            problems.append(f"{d} 不在 manifest 中")
    for href in manifest:
        if f"OEBPS/{href}" not in names:
            problems.append(f"manifest 指向不存在的檔案 {href}")

    spine = [r.get("idref") for r in opf.findall(".//opf:spine/opf:itemref", NS)]
    if not spine:
        problems.append("spine 是空的")
    for ref in spine:
        if ref not in ids:
            problems.append(f"spine 參照不存在的 id {ref}")
    if "nav" not in [i.get("id") for i in opf.findall(".//opf:manifest/opf:item", NS)
                     if (i.get("properties") or "").find("nav") >= 0]:
        problems.append("manifest 沒有標記 nav 文件")

    # Internal links must resolve to a file that exists and an id that exists.
    id_map = {}
    for d in docs:
        body = z.read(f"OEBPS/{d}").decode("utf-8", "replace")
        id_map[d] = set(re.findall(r'\bid="([^"]+)"', body))
    dangling = 0
    for d in docs:
        body = z.read(f"OEBPS/{d}").decode("utf-8", "replace")
        for href in re.findall(r'<a[^>]+href="([^"]+)"', body):
            if href.startswith(("http:", "https:", "mailto:")):
                continue
            file, _, frag = href.partition("#")
            target = file or d
            if target not in id_map:
                dangling += 1
            elif frag and frag not in id_map[target]:
                dangling += 1
    if dangling:
        notes.append(f"{dangling} 個內部連結指向不存在的目標")

    # Chapter sizes: a single huge file makes readers stutter.
    sizes = sorted(((z.getinfo(f"OEBPS/{d}").file_size, d) for d in docs),
                   reverse=True)
    big = [(s, d) for s, d in sizes if s > 900_000]
    if big:
        notes.append("過大章節: " + ", ".join(f"{d} {s//1024}KB" for s, d in big[:3]))

    coloured = sum(len(re.findall(r'<span class="\w{1,3}"',
                                 z.read(f"OEBPS/{d}").decode("utf-8", "replace")))
                   for d in docs)
    return problems, notes, len(docs), sizes[0][0] if sizes else 0, coloured


def main():
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, "epub", "*.epub")))
    bad = 0
    print(f"{'epub':46} {'章':>3} {'最大章':>8} {'token':>7}  狀態")
    print("-" * 92)
    for p in files:
        problems, notes, n, biggest, coloured = check(p)
        name = os.path.basename(p)
        status = "✅ 通過" if not problems else f"❌ {len(problems)} 個問題"
        print(f"{name[:45]:46} {n:>3} {biggest//1024:>6}KB {coloured:>7}  {status}")
        for x in problems:
            print(f"      ✘ {x}")
            bad += 1
        for x in notes:
            print(f"      ⚠ {x}")
    print("-" * 92)
    print("全部通過 ✅" if not bad else f"共 {bad} 個必須修的問題")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
