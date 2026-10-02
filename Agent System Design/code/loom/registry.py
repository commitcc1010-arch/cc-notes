"""loom.registry：大量 tool 的目錄與 tool search（第 13 章）。

能力目錄和「這一輪送給模型的 tool 清單」分開：模型先呼叫 search_tools，命中的 tool 才載入。
前綴不變式：載入只往清單尾端追加，不重排、不刪除；載入紀錄寫成 tools_loaded 事件，resume 後可重建。
"""
from __future__ import annotations

import math
import re
from collections import Counter

from .core import Middleware, Tool, ToolResult


def terms(text: str) -> list[str]:
    """英數字取整個字（底線拆開），中文取相鄰兩字（bigram）；不需要斷詞字典。"""
    out = re.findall(r"[a-z0-9]+", text.lower().replace("_", " "))
    for run in re.findall(r"[一-鿿]+", text):
        out += [run[i:i + 2] for i in range(len(run) - 1)] or [run]
    return out


class ToolRegistry:
    def __init__(self, tools: list[Tool], tags: dict[str, list[str]] | None = None):
        tags = tags or {}
        self.tools = {t.name: t for t in tools}
        self.docs = {t.name: terms(f"{t.name} {t.description} {' '.join(tags.get(t.name, []))}") for t in tools}
        self.df = Counter(w for d in self.docs.values() for w in set(d))
        self.avg_len = sum(map(len, self.docs.values())) / max(1, len(self.docs))

    def search(self, query: str, k: int = 3) -> list[str]:
        """BM25：詞越少見、在文件中出現越多次，分數越高；文件太長會被懲罰。"""
        n, scores = len(self.docs), {}
        for name, doc in self.docs.items():
            tf, s = Counter(doc), 0.0
            for w in set(terms(query)):
                if tf[w]:
                    idf = math.log(1 + (n - self.df[w] + 0.5) / (self.df[w] + 0.5))
                    s += idf * tf[w] * 2.2 / (tf[w] + 1.2 * (0.25 + 0.75 * len(doc) / self.avg_len))
            if s > 0:
                scores[name] = s
        return sorted(scores, key=lambda x: (-scores[x], x))[:k]

    def code_callable(self) -> list[Tool]:
        """code-as-action 只能用這些：唯讀且明確標成 code_callable（canon）。"""
        return [t for t in self.tools.values() if t.code_callable and t.effect == "read"]

    def search_tool(self) -> Tool:
        """放進 Agent.tools 的 meta tool；實際執行由 RegistryMiddleware 攔下處理。"""
        return Tool("search_tools", "用關鍵字搜尋可用的工具；命中的工具會在下一步出現在工具清單",
                    {"type": "object", "properties": {"query": {"type": "string", "description": "要做的事，例如 查詢發票"}},
                     "required": ["query"]}, lambda deps, query: "", effect="read")


class RegistryMiddleware(Middleware):
    def __init__(self, registry: ToolRegistry, k: int = 3):
        self.registry, self.k = registry, k

    def before_run(self, ctx, user_input):
        # context 是 log 的純函式：從事件重建已載入的 tool，resume 或換 worker 後清單完全相同
        for e in ctx.session.load():
            if e.type == "tools_loaded":
                self._append(ctx, e.data["names"])

    def _append(self, ctx, names: list[str]) -> list[str]:
        have = {t.name for t in (*ctx.agent.tools, *ctx.loaded_tools)}
        new = [n for n in names if n not in have and n in self.registry.tools]
        ctx.loaded_tools.extend(self.registry.tools[n] for n in new)   # 只追加：保護 prompt cache 前綴
        return new

    async def wrap_tool(self, ctx, tc, nxt):
        if tc.name != "search_tools":
            return await nxt(tc)
        hits = self.registry.search(tc.args.get("query", ""), self.k)
        new = self._append(ctx, hits)
        if new:
            ctx.emit("tools_loaded", names=new)
        lines = [f"{n}：{self.registry.tools[n].description}" for n in hits]
        return ToolResult("ok", "已載入：\n" + "\n".join(lines) if lines else "沒有找到相關工具，請換關鍵字。")
