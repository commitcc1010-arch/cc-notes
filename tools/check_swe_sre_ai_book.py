#!/usr/bin/env python3
"""Quality gate for《從 Commit 到可靠服務：Software Engineering × SRE × AI》.

Usage:
    PYTHONPATH=tools python3 tools/check_swe_sre_ai_book.py            # whole book
    PYTHONPATH=tools python3 tools/check_swe_sre_ai_book.py 32 33      # selected chapters
    PYTHONPATH=tools python3 tools/check_swe_sre_ai_book.py --partial  # skip missing files
    PYTHONPATH=tools python3 tools/check_swe_sre_ai_book.py --no-run   # parse Python, don't run it

Every ```python block is executed in a subprocess (10 s timeout) unless its
first line is ``# not-runnable``. Errors fail the run; warnings are printed.
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
from collections import defaultdict

from swe_sre_ai_book import (
    BOOK_DIR, FRONT, ROOT, load_outline, parse_frontmatter, parse_qas, python_blocks,
    strip_frontmatter,
)

BANNED = [
    "先沿箭頭讀一次", "背成口號", "本章位於 Part", "你現在位於哪裡", "開始前：四個一定要先懂的概念",
    "不是工具清單，而是判斷邊界", "交付能力", "問題壓力", "詳見原書", "請參考原書",
]
REQUIRED_SECTIONS = ["動手寫", "Trade-offs 與 Failure Modes", "AI 時代", "專家怎麼想", "動手練習"]
TAIL = ["本章重點整理", "延伸問答", "延伸閱讀"]
URLS = set((ROOT / "tools" / "swe_sre_reference_urls.txt").read_text().split())
URL_RE = re.compile(r"\((https?://[^)\s]+)\)")


def visible_len(text: str) -> int:
    text = re.sub(r"(?ms)^```.*?^```", "", text)
    return len(re.sub(r"\s+", "", text))


def run_python(source: str) -> str | None:
    """Return None on success, else a short error description."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
        fh.write(source)
        path = fh.name
    try:
        proc = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return "執行超過 10 秒"
    if proc.returncode != 0:
        tail = (proc.stderr.strip().splitlines() or ["(no stderr)"])[-1]
        return f"執行失敗：{tail}"
    return None


def check_chapter(spec, run, errors, warnings, paragraphs):
    rel = spec.path
    text = (BOOK_DIR / rel).read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    body = strip_frontmatter(text)
    nofence = re.sub(r"(?ms)^```.*?^```", "", body)
    if meta.get("chapter") != str(spec.number):
        errors.append(f"{rel}: frontmatter chapter 應為 {spec.number}")
    h1 = re.findall(r"(?m)^# (.+)$", nofence)
    if len(h1) != 1 or not h1[0].startswith(f"第 {spec.number} 章　"):
        errors.append(f"{rel}: 必須恰好一個 H1「# 第 {spec.number} 章　標題」")
    head = body[:1500]
    if "> [!abstract] 本章地圖" not in head:
        errors.append(f"{rel}: 開頭缺少 `> [!abstract] 本章地圖`")
    for label in ("**核心問題**", "**你會學到**", "**對應原書**"):
        if label not in head:
            errors.append(f"{rel}: 本章地圖缺少 {label}")
    h2 = re.findall(r"(?m)^## (.+)$", nofence)
    if h2[-3:] != TAIL:
        errors.append(f"{rel}: 最後三個 H2 必須是 {TAIL}，實際 {h2[-3:]}")
    numbered = h2[:-3]
    for h in numbered:
        if not re.match(rf"{spec.number}\.\d+ ", h):
            errors.append(f"{rel}: H2「{h}」缺少節號（{spec.number}.x）")
    nums = [int(m.group(1)) for h in numbered if (m := re.match(rf"{spec.number}\.(\d+) ", h))]
    if nums != list(range(1, len(nums) + 1)):
        errors.append(f"{rel}: 節號不連續 {nums}")
    titles = [re.sub(r"^\d+\.\d+ ", "", h) for h in numbered]
    for req in REQUIRED_SECTIONS:
        if not any(t.startswith(req) for t in titles):
            errors.append(f"{rel}: 缺少「{req}」小節")
    if numbered and "故事" not in numbered[0]:
        warnings.append(f"{rel}: 第一節不是「故事」開場")
    for phrase in BANNED:
        if phrase in body:
            errors.append(f"{rel}: 出現禁用語「{phrase}」")
    prose = body.split("\n## 延伸問答", 1)[0]
    size = visible_len(prose)
    if size < 12000:
        errors.append(f"{rel}: 正文可見字元 {size} 低於 12000")
    if "```text" not in prose:
        errors.append(f"{rel}: 沒有 ASCII 圖（```text）")
    takeaways = body.split("## 本章重點整理", 1)[-1].split("## 延伸問答", 1)[0]
    n_take = len(re.findall(r"(?m)^- ", takeaways))
    if n_take < 8:
        errors.append(f"{rel}: 本章重點整理只有 {n_take} 條（至少 8）")
    qa_section = body.split("## 延伸問答", 1)[-1].split("## 延伸閱讀", 1)[0]
    qas = parse_qas(qa_section)
    if len(qas) != spec.qas:
        errors.append(f"{rel}: 延伸問答 {len(qas)} 題，大綱要求 {spec.qas}")
    for n, (num, question, answer) in enumerate(qas, 1):
        if num != n:
            errors.append(f"{rel}: 問答編號應為 Q{n}，實際 Q{num}")
        if visible_len(answer) < 120:
            errors.append(f"{rel}: Q{num} 答案過短（{visible_len(answer)} 字元）")
    blocks = python_blocks(prose)
    runnable = [(ln, src) for ln, src in blocks if not src.lstrip().startswith("# not-runnable")]
    if not runnable:
        errors.append(f"{rel}: 「動手寫」需要至少一段可執行的 Python")
    for ln, src in blocks:
        try:
            ast.parse(src)
        except SyntaxError as exc:
            errors.append(f"{rel}:{ln}: Python 語法錯誤：{exc.msg}（第 {exc.lineno} 行）")
            continue
        if run and not src.lstrip().startswith("# not-runnable"):
            problem = run_python(src)
            if problem:
                errors.append(f"{rel}:{ln}: Python {problem}")
    for url in URL_RE.findall(body):
        if url not in URLS:
            warnings.append(f"{rel}: 連結不在已查證清單：{url}")
    for para in re.split(r"\n\s*\n", prose):
        para = para.strip()
        if len(para) >= 60 and not para.startswith(("|", "```", "#", ">")):
            paragraphs[para].append(rel)
    return len(qas)


def main(argv):
    chapters, appendices, _ = load_outline()
    partial = "--partial" in argv
    run = "--no-run" not in argv
    nums = {int(a) for a in argv if a.isdigit()}
    errors: list[str] = []
    warnings: list[str] = []
    paragraphs: dict[str, list[str]] = defaultdict(list)
    checked = qa_total = 0
    for spec in chapters:
        if nums and spec.number not in nums:
            continue
        if not (BOOK_DIR / spec.path).exists():
            if nums or not partial:
                errors.append(f"缺少章節檔案：{spec.path}")
            continue
        qa_total += check_chapter(spec, run, errors, warnings, paragraphs)
        checked += 1
    if not nums:
        for rel, _ in appendices:
            if not (BOOK_DIR / rel).exists() and not partial:
                errors.append(f"缺少附錄：{rel}")
        if not (BOOK_DIR / FRONT).exists() and not partial:
            errors.append(f"缺少導讀：{FRONT}")
    for para, files in paragraphs.items():
        if len(files) >= 2:
            warnings.append(f"重複段落（{sorted(set(files))}）：{para[:50]}…")
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"\n檢查 {checked} 章、{qa_total} 組問答：{len(errors)} errors、{len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
