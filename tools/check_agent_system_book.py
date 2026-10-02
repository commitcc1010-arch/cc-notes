#!/usr/bin/env python3
"""Quality gate for《Agent System 設計全書》Markdown sources.

Usage:
    python3 tools/check_agent_system_book.py            # whole book
    python3 tools/check_agent_system_book.py 23 24      # selected chapters
    python3 tools/check_agent_system_book.py --partial  # skip missing files
    python3 tools/check_agent_system_book.py --no-run   # parse code, don't run it

Every ```python block is run on its own (10 s timeout) unless its first
line is ``# not-runnable``. Code must use the standard library only.
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from swe_sre_ai_book import load_outline, parse_frontmatter, parse_qas, strip_frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BOOK_DIR = ROOT / "Agent System Design"
OUTLINE = ROOT / "tools" / "agent_system_outline.md"
FRONT = "00 - 導讀.md"

BANNED = ["在這個快速變化的時代", "請參考官方文件", "詳見官方文件", "總而言之，agent 非常強大"]
NONINCLUSIVE = re.compile(r"\b(master|slave|whitelist|blacklist)\b|白名單|黑名單|主從式", re.I)
GENDERED = re.compile(r"她|(?<![其利吉排])他(?![們人])")
THIRD_PARTY = re.compile(r"(?m)^\s*(?:from|import)\s+(openai|anthropic|langchain|langgraph|google|crewai|pydantic|requests|httpx|numpy|pandas|autogen|llama_index|mcp|dspy)\b")
REQUIRED_SECTIONS = ["動手做", "實務應用", "設計檢查清單", "常見錯誤與除錯"]
TAIL = ["本章重點整理", "延伸問答", "延伸閱讀"]
URL_RE = re.compile(r"https?://")
CODE_RE = re.compile(r"(?ms)^```(\w*)\n(.*?)^```")
CJK = r"[一-鿿]"
GLUE_RE = re.compile(rf"{CJK}[A-Za-z]|[A-Za-z]{CJK}")
SKIP_MARKS = ("# not-runnable",)


def visible_len(text: str) -> int:
    text = re.sub(r"(?ms)^```.*?^```", "", text)
    return len(re.sub(r"\s+", "", text))


def run_py(source: str) -> str | None:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
        fh.write(source)
    try:
        proc = subprocess.run([sys.executable, fh.name], capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return "Python 執行超過 10 秒"
    if proc.returncode != 0:
        tail = (proc.stderr.strip().splitlines() or ["(no stderr)"])[-1]
        return f"Python 執行失敗：{tail}"
    return None


def prose_without_code(text: str) -> str:
    text = re.sub(r"(?ms)^```.*?^```", "", text)
    text = re.sub(r"`[^`]*`", "", text)
    return re.sub(r"\]\([^)]*\)", "]", text)


def check_chapter(spec, do_run, errors, warnings, paragraphs):
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
    for label in ("**核心問題**", "**你會學到**", "**前置知識**"):
        if label not in head:
            errors.append(f"{rel}: 本章地圖缺少 {label}")
    h2 = re.findall(r"(?m)^## (.+)$", nofence)
    if h2[-3:] != TAIL:
        errors.append(f"{rel}: 最後三個 H2 必須是 {TAIL}，實際 {h2[-3:]}")
    numbered = h2[:-3]
    nums = [int(m.group(1)) for h in numbered if (m := re.match(rf"{spec.number}\.(\d+) ", h))]
    if len(nums) != len(numbered) or nums != list(range(1, len(nums) + 1)):
        errors.append(f"{rel}: 節號必須是連續的 {spec.number}.1、{spec.number}.2…")
    titles = [re.sub(r"^\d+\.\d+ ", "", h) for h in numbered]
    for req in REQUIRED_SECTIONS:
        if not any(t.startswith(req) for t in titles):
            errors.append(f"{rel}: 缺少「{req}」小節")
    if numbered and "故事" not in numbered[0]:
        errors.append(f"{rel}: 第一節必須是「故事」開場")
    for phrase in BANNED:
        if phrase in body:
            errors.append(f"{rel}: 出現禁用語「{phrase}」")
    if (m := GENDERED.search(prose_without_code(body))):
        errors.append(f"{rel}: 人物不用性別代名詞（「{prose_without_code(body)[max(0, m.start()-10):m.end()+5]}」），改用名字或「對方」")
    if (m := NONINCLUSIVE.search(prose_without_code(body))):
        errors.append(f"{rel}: 非包容性用語「{m.group(0)}」")
    prose = body.split("\n## 延伸問答", 1)[0]
    size = visible_len(prose)
    if size < 14000:
        errors.append(f"{rel}: 正文可見字元 {size} 低於 14000")
    n_diagrams = prose.count("```text")
    n_tables = len(re.findall(r"(?m)^\|[ :]*-{3,}", prose))
    if n_diagrams < 5:
        errors.append(f"{rel}: ```text 區塊只有 {n_diagrams} 個（至少 4 張圖＋1 段執行輸出）")
    if n_tables < 3:
        errors.append(f"{rel}: 表格只有 {n_tables} 張（至少 3）")
    glue = GLUE_RE.findall(prose_without_code(body))
    if len(glue) > 5:
        errors.append(f"{rel}: 中英文之間缺少空格 {len(glue)} 處（例如「{glue[0]}」）")
    takeaways = body.split("## 本章重點整理", 1)[-1].split("## 延伸問答", 1)[0]
    if len(re.findall(r"(?m)^- ", takeaways)) < 8:
        errors.append(f"{rel}: 本章重點整理少於 8 條")
    qas = parse_qas(body.split("## 延伸問答", 1)[-1].split("## 延伸閱讀", 1)[0])
    if len(qas) != spec.qas:
        errors.append(f"{rel}: 延伸問答 {len(qas)} 題，大綱要求 {spec.qas}")
    for n, (num, _q, answer) in enumerate(qas, 1):
        if num != n:
            errors.append(f"{rel}: 問答編號應為 Q{n}，實際 Q{num}")
        if visible_len(answer) < 150:
            errors.append(f"{rel}: Q{num} 答案過短")
    runnable = 0
    for m in CODE_RE.finditer(prose):
        lang, src = m.group(1), m.group(2)
        line = prose[:m.start()].count("\n") + 1
        skipped = src.lstrip().startswith(SKIP_MARKS)
        if lang == "python":
            try:
                ast.parse(src)
            except SyntaxError as exc:
                errors.append(f"{rel}:{line}: Python 語法錯誤：{exc.msg}")
                continue
            if THIRD_PARTY.search(src) and not skipped:
                errors.append(f"{rel}:{line}: 可執行的程式只能用標準函式庫")
            if not skipped:
                runnable += 1
                if do_run and (problem := run_py(src)):
                    errors.append(f"{rel}:{line}: {problem}")
    if not runnable:
        errors.append(f"{rel}: 「動手做」需要至少一段可執行的 Python")
    if URL_RE.search(re.sub(r"(?ms)^```.*?^```", "", body)):
        errors.append(f"{rel}: 不應放 URL")
    for para in re.split(r"\n\s*\n", re.sub(r"(?ms)^```.*?^```", "", prose)):
        para = para.strip()
        if len(para) >= 60 and not para.startswith(("|", "```", "#", ">")):
            paragraphs[para].append(rel)
    return len(qas)


def main(argv):
    chapters, appendices, _ = load_outline(OUTLINE)
    partial = "--partial" in argv
    do_run = "--no-run" not in argv
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
        qa_total += check_chapter(spec, do_run, errors, warnings, paragraphs)
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
