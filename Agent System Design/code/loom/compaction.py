"""loom.compaction：交接筆記（第 10 章）。

六個固定段落：目標、使用者約束、已完成、進行中、下一步、未解問題。
使用者約束逐字保留：摘要漏掉的由程式補上；副作用由程式記帳（進度檔原文附在筆記後），不靠摘要。
"""
from __future__ import annotations

import json
import re

SECTIONS = ("目標", "使用者約束", "已完成", "進行中", "下一步", "未解問題")
SUMMARY_PROMPT = ("把以上對話整理成交接筆記，依序寫六段，每段以「## 段名」開頭："
                  + "、".join(SECTIONS) + "。使用者約束必須逐字照抄。")


def format_note(sections: dict[str, str]) -> str:
    return "\n".join(f"## {name}\n{sections.get(name, '（無）')}" for name in SECTIONS)


def parse_note(note: str) -> dict[str, str]:
    parts = re.split(r"(?m)^## ", note)
    return {p.split("\n", 1)[0].strip(): (p.split("\n", 1) + [""])[1].strip() for p in parts if p.strip()}


def check_handoff(note: str, must_keep: list[str], max_chars: int = 1_200) -> list[str]:
    sections = parse_note(note)
    problems = [f"缺少段落「{s}」" for s in SECTIONS if s not in sections]
    problems += [f"漏掉使用者約束「{c}」" for c in must_keep if c not in note]
    if len(note) > max_chars:
        problems.append(f"筆記 {len(note)} 字元，超過 {max_chars}")
    return problems


class Compactor:
    """用一個（通常較小的）模型寫摘要，再由程式驗證與補強；warnings 給觀測系統當訊號。"""

    def __init__(self, model, max_chars: int = 1_200):
        self.model, self.max_chars = model, max_chars
        self.warnings: list[str] = []

    def summarize(self, messages: list[dict], constraints: list[str], progress: dict | None = None) -> str:
        note = self.model.complete(messages, system=SUMMARY_PROMPT).text
        problems = check_handoff(note, constraints, self.max_chars)
        self.warnings += problems
        sections = parse_note(note)
        if any(p.startswith("缺少段落") for p in problems):
            sections = {s: sections.get(s, "（摘要缺漏，請查 session log）") for s in SECTIONS}
        missing = [c for c in constraints if c not in note]
        if missing:                         # 不靠摘要：約束原文一定會出現在筆記裡
            sections["使用者約束"] = "\n".join(filter(None, [sections.get("使用者約束", ""), *missing]))
        out = "【交接筆記】\n" + format_note(sections)
        if progress is not None:
            out += "\n【進度檔原文】\n" + json.dumps(progress, ensure_ascii=False, sort_keys=True)
        return out
