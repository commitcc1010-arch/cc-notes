#!/usr/bin/env python3
"""Quality gate for《CS:APP 系統思維學習手冊》Markdown sources.

Usage:
    python3 tools/check_csapp_systems_book.py            # whole book
    python3 tools/check_csapp_systems_book.py 23 24      # selected chapters
    python3 tools/check_csapp_systems_book.py --partial  # skip missing files
    python3 tools/check_csapp_systems_book.py --no-run   # parse code, don't run it

Every ```c block containing ``int main`` is compiled and run, and every
```python block is run (10 s timeout), unless its first line is
``// not-runnable`` / ``// linux-only`` / ``# not-runnable``.
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
BOOK_DIR = ROOT / "CSAPP 系統思維學習手冊"
OUTLINE = ROOT / "tools" / "csapp_outline.md"
FRONT = "00 - 導讀.md"
URLS = set((ROOT / "tools" / "csapp_reference_urls.txt").read_text().split())

BANNED = [
    "CORE COMPLETION LAYER", "DSA → SYSTEMS BRIDGE", "進入細節前的三個定位點", "輸入與壓力",
    "內部責任", "讀完輸出", "術語卡住？回到零背景", "WHY IT MATTERS", "詳見原書", "請參考原書",
]
REQUIRED_SECTIONS = ["動手做", "在工作上怎麼用", "常見錯誤與除錯", "動手練習"]
TAIL = ["本章重點整理", "延伸問答", "延伸閱讀"]
URL_RE = re.compile(r"\((https?://[^)\s]+)\)")
CODE_RE = re.compile(r"(?ms)^```(\w*)\n(.*?)^```")
CJK = r"[一-鿿]"
GLUE_RE = re.compile(rf"{CJK}[A-Za-z]|[A-Za-z]{CJK}")
SKIP_MARKS = ("// not-runnable", "// linux-only", "# not-runnable")


def visible_len(text: str) -> int:
    text = re.sub(r"(?ms)^```.*?^```", "", text)
    return len(re.sub(r"\s+", "", text))


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=20, **kw)


def run_c(source: str) -> str | None:
    with tempfile.TemporaryDirectory() as tmp:
        src, exe = Path(tmp) / "x.c", Path(tmp) / "x"
        src.write_text(source)
        proc = run(["cc", "-std=c17", "-O1", "-Wall", "-Wextra", "-o", str(exe), str(src), "-lpthread", "-lm"])
        if proc.returncode != 0:
            first = next((l for l in proc.stderr.splitlines() if "error" in l), proc.stderr.strip()[:200])
            return f"C 編譯失敗：{first}"
        try:
            proc = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10, cwd=tmp)
        except subprocess.TimeoutExpired:
            return "C 執行超過 10 秒"
        if proc.returncode != 0:
            return f"C 執行回傳 {proc.returncode}"
    return None


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
    for label in ("**核心問題**", "**你會學到**", "**對應 CS:APP 3e**"):
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
        warnings.append(f"{rel}: 第一節不是「故事」開場")
    for phrase in BANNED:
        if phrase in body:
            errors.append(f"{rel}: 出現禁用語「{phrase}」")
    prose = body.split("\n## 延伸問答", 1)[0]
    size = visible_len(prose)
    if size < 12000:
        errors.append(f"{rel}: 正文可見字元 {size} 低於 12000")
    n_diagrams = prose.count("```text")
    n_tables = len(re.findall(r"(?m)^\|[ :]*-{3,}", prose))
    if n_diagrams < 3:
        errors.append(f"{rel}: ```text 圖只有 {n_diagrams} 個（至少 3）")
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
        if visible_len(answer) < 120:
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
            if not skipped:
                runnable += 1
                if do_run and (problem := run_py(src)):
                    errors.append(f"{rel}:{line}: {problem}")
        elif lang == "c" and "int main" in src and not skipped:
            runnable += 1
            if do_run and (problem := run_c(src)):
                errors.append(f"{rel}:{line}: {problem}")
    if not runnable:
        errors.append(f"{rel}: 「動手做」需要至少一段可執行的 C 或 Python")
    for url in URL_RE.findall(body):
        if url not in URLS:
            warnings.append(f"{rel}: 連結不在已查證清單：{url}")
    for para in re.split(r"\n\s*\n", prose):
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
