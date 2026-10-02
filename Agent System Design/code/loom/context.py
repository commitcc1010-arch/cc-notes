"""loom.context：context 是 session log 的純函式（第 9、10 章）。

清除舊 tool 輸出與摘要都「記成事件」（context_cleared、context_compacted），不改寫歷史：
log 只追加，任何時候都能重建、倒帶、取回原文。這兩個是擴充事件，to_messages 會略過它們。
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from .core import Event, Middleware, to_messages


def estimate_tokens(obj) -> int:
    """粗估：字元數 ÷ 2。真實系統用 provider 的 token 計數 API。"""
    return len(json.dumps(obj, ensure_ascii=False)) // 2


def build_view(events: list[Event]) -> list[dict]:
    """重播核心事件與 context 事件，得到這一輪要送給模型的 messages。"""
    msgs: list[tuple[int, dict]] = []
    cleared: dict[str, str] = {}
    note = None
    for e in events:
        if e.type == "context_cleared":
            cleared.update(e.data["placeholders"])
        elif e.type == "context_compacted":
            msgs = [(s, m) for s, m in msgs if s > e.data["upto"]]
            note = e.data["note"]
        else:
            msgs += [(e.seq, m) for m in to_messages([e])]
    view = [{"role": "user", "content": note}] if note else []
    for _, m in msgs:
        if m["role"] == "tool" and m["tool_call_id"] in cleared:
            m = {**m, "content": cleared[m["tool_call_id"]]}   # 只換內容、不刪訊息：配對原封不動
        view.append(m)
    return view


@dataclass
class ContextPolicy:
    clear_at: int = 3_000          # 第一道：超過就清舊 tool 輸出
    clear_at_least: int = 500      # 一次至少省這麼多才清：少清幾次，少破壞幾次 prompt cache
    compact_at: int = 6_000        # 第二道：清完仍超過就摘要
    keep_tool_results: int = 2     # 最近幾則 tool 結果保留原文
    keep_turns: int = 2            # 摘要時保留最近幾輪 assistant（含其 tool 結果）
    never_clear: tuple[str, ...] = ("update_progress",)


class ContextMiddleware(Middleware):
    """掛在 wrap_model：送出前依預算組裝 context，必要時先清、再摘要（compactor 來自 loom.compaction）。"""

    def __init__(self, policy: ContextPolicy | None = None, compactor=None):
        self.p, self.compactor = policy or ContextPolicy(), compactor

    async def wrap_model(self, ctx, req, nxt):
        view = build_view(ctx.session.load())
        if estimate_tokens(view) > self.p.clear_at:
            self._clear(ctx, view)
            view = build_view(ctx.session.load())
        if self.compactor and estimate_tokens(view) > self.p.compact_at:
            self._compact(ctx)
            view = build_view(ctx.session.load())
        req.messages = view
        return await nxt(req)

    def _clear(self, ctx, view: list[dict]) -> None:
        results = [m for m in view if m["role"] == "tool" and m["name"] not in self.p.never_clear
                   and not m["content"].startswith("[已清除")]
        old = results[: max(0, len(results) - self.p.keep_tool_results)]
        if sum(estimate_tokens(m["content"]) for m in old) < self.p.clear_at_least:
            return
        seq = {e.data["id"]: e.seq for e in ctx.session.load() if e.type == "tool_result"}
        ctx.emit("context_cleared", placeholders={
            m["tool_call_id"]: f"[已清除 {m['name']} 的輸出，原文在 session seq={seq[m['tool_call_id']]}]" for m in old})

    def _compact(self, ctx) -> None:
        events = ctx.session.load()
        last = max([e.data["upto"] for e in events if e.type == "context_compacted"], default=-1)
        turns = [e.seq for e in events if e.type == "model_response" and e.seq > last]
        if len(turns) <= self.p.keep_turns:
            return
        upto = turns[-self.p.keep_turns] - 1    # 切在 assistant 之前：前面的 tool_call 都已配對完成
        # 摘要器讀原文（不套用 clear），才看得到已被清掉的單號等細節
        old = build_view([e for e in events if e.seq <= upto and e.type != "context_cleared"])
        note = self.compactor.summarize(old, ctx.deps.get("constraints", []), ctx.deps.get("progress"))
        ctx.emit("context_compacted", upto=upto, note=note)
