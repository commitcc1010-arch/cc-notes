#!/usr/bin/env python3
"""Quality gate for《Coding Interview Pattern Playbook》Markdown sources.

Usage:
    python3 tools/check_coding_interview_book.py            # whole book
    python3 tools/check_coding_interview_book.py 8 9        # selected chapters
    python3 tools/check_coding_interview_book.py --partial  # skip missing files
    python3 tools/check_coding_interview_book.py --no-run   # parse code, don't run it

Every ```python block is executed (10 s timeout) unless its first line is
``# not-runnable``.
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
from swe_sre_ai_book import load_outline, parse_frontmatter, strip_frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BOOK_DIR = ROOT / "Coding Interview Pattern Playbook"
OUTLINE = ROOT / "tools" / "coding_interview_outline.md"

BANNED = ["視覺化題解：從暴力到最佳模型", "五步推導", "原題直接變形", "正確性證明骨架", "這題真正考什麼",
          "production API", "一句話記憶", "deep-learning:start", "deep-followups"]
CORE_H3 = ["題目", "思路", "解法", "複雜度與邊界", "Follow-up"]
HARD_H3 = ["題目", "提示", "詳解", "解法", "複雜度與邊界", "Follow-up", "心得"]
PROB_RE = re.compile(r"^## (核心題|難題) (\d)｜(\d+)\. (.+)｜(Easy|Medium|Hard)$")
FU_RE = re.compile(r"^> \[!question\]- (F\d+|Q\d+)\. (.+)$")
TIP_RE = re.compile(r"^> \[!tip\]- 提示 \d")
CJK = r"[一-鿿]"
GLUE_RE = re.compile(rf"{CJK}[A-Za-z]|[A-Za-z]{CJK}")


def visible_len(text: str) -> int:
    text = re.sub(r"(?ms)^```.*?^```", "", text)
    return len(re.sub(r"\s+", "", text))


def outline_meta() -> dict[int, tuple[str, list[int], list[int]]]:
    meta = {}
    for line in OUTLINE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| (\d+) \| .+?\.md \| .+? \| (guide|pattern) \| \d+ \| (.*) \|$", line)
        if not m:
            continue
        body = m.group(3)
        core = hard = []
        if m.group(2) == "pattern":
            core_txt = body.split("核心：", 1)[1].split("。難題：", 1)[0]
            hard_txt = body.split("難題：", 1)[1]
            core = [int(x) for x in re.findall(r"(?:^|、)(\d+)", core_txt)]
            hard = [int(x) for x in re.findall(r"(?:^|、)(\d+)", hard_txt)]
        meta[int(m.group(1))] = (m.group(2), core, hard)
    return meta


def run_py(source: str) -> str | None:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
        fh.write(source)
    try:
        proc = subprocess.run([sys.executable, fh.name], capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return "執行超過 10 秒"
    if proc.returncode != 0:
        return "執行失敗：" + ((proc.stderr.strip().splitlines() or ["?"])[-1])
    return None


def callouts(section: str, pattern: re.Pattern) -> list[str]:
    """Return the body text of each callout whose first line matches pattern."""
    out, lines, i = [], section.splitlines(), 0
    while i < len(lines):
        if pattern.match(lines[i]):
            body = []
            i += 1
            while i < len(lines) and lines[i].startswith(">"):
                body.append(lines[i][1:].strip())
                i += 1
            out.append("\n".join(body))
        else:
            i += 1
    return out


def check_code(text: str, rel: str, do_run: bool, errors: list[str]) -> int:
    runnable = 0
    for m in re.finditer(r"(?ms)^```python\n(.*?)^```", text):
        src = m.group(1)
        try:
            ast.parse(src)
        except SyntaxError as exc:
            errors.append(f"{rel}: Python 語法錯誤：{exc.msg}")
            continue
        if src.lstrip().startswith("# not-runnable"):
            continue
        runnable += 1
        if do_run and (p := run_py(src)):
            first = src.strip().splitlines()[0][:40]
            errors.append(f"{rel}: 程式 {p}（{first}…）")
    return runnable


def check_common(body: str, rel: str, errors: list[str]) -> None:
    for phrase in BANNED:
        if phrase in body:
            errors.append(f"{rel}: 出現禁用語「{phrase}」")
    prose = re.sub(r"(?ms)^```.*?^```", "", body)
    prose = re.sub(r"`[^`]*`", "", prose)
    glue = GLUE_RE.findall(prose)
    if len(glue) > 8:
        errors.append(f"{rel}: 中英文之間缺少空格 {len(glue)} 處（例如「{glue[0]}」）")
    if re.search(r"https?://", body):
        errors.append(f"{rel}: 不應放 URL")


def check_pattern(spec, core, hard, body, rel, do_run, errors, warnings):
    nofence = re.sub(r"(?ms)^```.*?^```", "", body)
    h2 = re.findall(r"(?m)^## (.+)$", nofence)
    intro = [h for h in h2 if re.match(rf"{spec.number}\.\d+ ", h)]
    if len(intro) < 4:
        errors.append(f"{rel}: 開頭編號小節少於 4 節")
    for need in ("辨識訊號", "模板", "常見錯誤"):
        if not any(need in h for h in intro):
            errors.append(f"{rel}: 缺少「{need}」小節")
    if h2[-2:] != ["Pattern 歸納", "本章重點整理"]:
        errors.append(f"{rel}: 最後兩個 H2 必須是 Pattern 歸納、本章重點整理")
    if "**辨識訊號**" not in body[:1500]:
        errors.append(f"{rel}: 本章地圖缺少 **辨識訊號**")
    probs = [(m, i) for i, line in enumerate(body.splitlines()) if (m := PROB_RE.match(line))]
    got_core = [int(m.group(3)) for m, _ in probs if m.group(1) == "核心題"]
    got_hard = [int(m.group(3)) for m, _ in probs if m.group(1) == "難題"]
    if got_core != core:
        errors.append(f"{rel}: 核心題題號 {got_core}，大綱為 {core}")
    if got_hard != hard:
        errors.append(f"{rel}: 難題題號 {got_hard}，大綱為 {hard}")
    for kind in ("核心題", "難題"):
        nums = [int(m.group(2)) for m, _ in probs if m.group(1) == kind]
        if nums != list(range(1, len(nums) + 1)):
            errors.append(f"{rel}: {kind}編號不連續 {nums}")
    lines = body.splitlines()
    starts = [i for _, i in probs] + [next((i for i, l in enumerate(lines) if l == "## Pattern 歸納"), len(lines))]
    for (m, start), end in zip(probs, starts[1:]):
        label = f"{m.group(1)} {m.group(2)}（{m.group(3)}）"
        section = "\n".join(lines[start + 1:end])
        sec_nofence = re.sub(r"(?ms)^```.*?^```", "", section)
        h3 = re.findall(r"(?m)^### (.+)$", sec_nofence)
        want = CORE_H3 if m.group(1) == "核心題" else HARD_H3
        if h3 != want:
            errors.append(f"{rel}: {label} 的 H3 應為 {want}，實際 {h3}")
        if "```text" not in section:
            errors.append(f"{rel}: {label} 沒有 ```text 視覺化")
        if check_code(section, f"{rel} {label}", do_run, errors) == 0:
            errors.append(f"{rel}: {label} 沒有可執行的解法")
        fus = callouts(section.split("### Follow-up", 1)[-1], FU_RE)
        if len(fus) < 3:
            errors.append(f"{rel}: {label} Follow-up 只有 {len(fus)} 個")
        for k, ans in enumerate(fus, 1):
            if visible_len(ans) < 80:
                errors.append(f"{rel}: {label} F{k} 答案過短")
        if m.group(1) == "難題":
            tips = callouts(section, TIP_RE)
            if len(tips) < 3:
                errors.append(f"{rel}: {label} 提示少於 3 段")
            insight = section.split("### 心得", 1)[-1]
            if visible_len(insight) < 80:
                errors.append(f"{rel}: {label} 心得過短")
        if visible_len(section) < 1500:
            warnings.append(f"{rel}: {label} 內容偏短（{visible_len(section)} 字元）")
    tail = body.split("## 本章重點整理", 1)[-1]
    if len(re.findall(r"(?m)^- ", tail)) < 8:
        errors.append(f"{rel}: 本章重點整理少於 8 條")
    return len(probs)


def check_guide(spec, body, rel, do_run, errors):
    nofence = re.sub(r"(?ms)^```.*?^```", "", body)
    h2 = re.findall(r"(?m)^## (.+)$", nofence)
    if h2[-2:] != ["本章重點整理", "延伸問答"]:
        errors.append(f"{rel}: 最後兩個 H2 必須是 本章重點整理、延伸問答")
    if len([h for h in h2 if re.match(rf"{spec.number}\.\d+ ", h)]) < 4:
        errors.append(f"{rel}: 編號小節少於 4 節")
    qas = callouts(body.split("## 延伸問答", 1)[-1], FU_RE)
    if len(qas) != 8:
        errors.append(f"{rel}: 延伸問答 {len(qas)} 題（應為 8）")
    for k, ans in enumerate(qas, 1):
        if visible_len(ans) < 120:
            errors.append(f"{rel}: Q{k} 答案過短")
    if visible_len(body) < 8000:
        errors.append(f"{rel}: 正文過短（{visible_len(body)}）")
    check_code(body, rel, do_run, errors)


def main(argv):
    chapters, appendices, _ = load_outline(OUTLINE)
    meta = outline_meta()
    partial = "--partial" in argv
    do_run = "--no-run" not in argv
    nums = {int(a) for a in argv if a.isdigit()}
    errors, warnings = [], []
    checked = problems = 0
    for spec in chapters:
        if nums and spec.number not in nums:
            continue
        path = BOOK_DIR / spec.path
        if not path.exists():
            if nums or not partial:
                errors.append(f"缺少章節檔案：{spec.path}")
            continue
        text = path.read_text(encoding="utf-8")
        body = strip_frontmatter(text)
        rel = spec.path
        if parse_frontmatter(text).get("chapter") != str(spec.number):
            errors.append(f"{rel}: frontmatter chapter 應為 {spec.number}")
        h1 = re.findall(r"(?m)^# (.+)$", re.sub(r"(?ms)^```.*?^```", "", body))
        if len(h1) != 1 or not h1[0].startswith(f"第 {spec.number} 章　"):
            errors.append(f"{rel}: 必須恰好一個 H1「# 第 {spec.number} 章　標題」")
        if "> [!abstract] 本章地圖" not in body[:800]:
            errors.append(f"{rel}: 開頭缺少本章地圖")
        check_common(body, rel, errors)
        kind, core, hard = meta[spec.number]
        if kind == "pattern":
            problems += check_pattern(spec, core, hard, body, rel, do_run, errors, warnings)
        else:
            check_guide(spec, body, rel, do_run, errors)
        checked += 1
    if not nums and not partial:
        for rel, _ in appendices:
            if not (BOOK_DIR / rel).exists():
                errors.append(f"缺少附錄：{rel}")
        if not (BOOK_DIR / "00 - 導讀.md").exists():
            errors.append("缺少導讀：00 - 導讀.md")
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"\n檢查 {checked} 章、{problems} 題：{len(errors)} errors、{len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
