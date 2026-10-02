"""loom.guardrails：宣告式 guardrail 的執行器，以及 capability＋資料來源標記（taint）檢查（第 23、31、32 章）。

審查單位是 context：同一個 context 只要讀過不可信內容，模型之後產生的任何參數都視為受它影響。
政策結果三種：deny／ask／allow；ask 透過 ctx.state["ask"] 交給 loom.approval（兩個模組不互相 import）。
檢查順序：能力 → 機密性 → 完整性。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .core import Middleware, StopRun, ToolResult


@dataclass(frozen=True)
class Label:
    sources: frozenset[str] = frozenset()                 # 這個值受哪些來源影響（完整性）
    readers: frozenset[str] = frozenset({"*"})            # 誰可以看到這個值（機密性），"*" 代表不限

    @property
    def untrusted(self) -> bool:
        return any(s.startswith("untrusted:") for s in self.sources)

    def join(self, other: "Label") -> "Label":
        """兩個值混在一起：來源取聯集，讀者取交集（雙方都允許的人才能看）。"""
        if "*" in self.readers:
            readers = other.readers
        elif "*" in other.readers:
            readers = self.readers
        else:
            readers = self.readers & other.readers
        return Label(self.sources | other.sources, readers)


def lab(*sources: str, readers: tuple[str, ...] = ("*",)) -> Label:
    return Label(frozenset(sources), frozenset(readers))


@dataclass
class ToolSpec:
    capability: str                                       # 呼叫它需要的能力
    integrity_args: tuple[str, ...] = ()                  # 不能被不可信內容左右的參數
    recipient_arg: str | None = None                      # 對外通訊 tool：資料送給誰
    labels: Label | Callable[[dict], Label] = field(default_factory=Label)   # 結果的標記（可依 deps 決定讀者）
    inherits: bool = False                                # 結果是否繼承呼叫當下 context 的標記（text 回傳）


def check(spec: ToolSpec, grants: set[str], args: dict[str, tuple[Any, Label]]) -> tuple[str, str]:
    if spec.capability not in grants:
        return "deny", f"session 沒有 {spec.capability} 能力"
    if spec.recipient_arg:
        to = args[spec.recipient_arg][0]
        for name, (_, label) in args.items():
            if "*" not in label.readers and to not in label.readers:
                return "deny", f"{name} 含有 {to} 無權讀取的資料"
    for name in spec.integrity_args:
        if name in args and args[name][1].untrusted:
            src = sorted(s for s in args[name][1].sources if s.startswith("untrusted:"))
            return "ask", f"{name} 可能受不可信內容影響 {src}，轉人工確認"
    return "allow", "通過"


class TaintMiddleware(Middleware):
    def __init__(self, specs: dict[str, ToolSpec], grants: Callable[[Any], set[str]]):
        self.specs, self.grants = specs, grants

    def context_label(self, ctx) -> Label:
        """context 標記是 session log 的純函式：依序折疊每個 tool 結果的標記。"""
        label = lab("user")
        for e in ctx.session.load():
            if e.type == "tool_result" and (spec := self.specs.get(e.data["name"])) and not e.data["is_error"]:
                out = spec.labels(ctx.deps) if callable(spec.labels) else spec.labels
                label = label.join(out.join(label) if spec.inherits else out)
        return label

    async def wrap_tool(self, ctx, tc, nxt):
        spec = self.specs.get(tc.name)
        if spec is None:
            return await nxt(tc)
        here = self.context_label(ctx)                    # 保守：每個參數都可能受整個 context 影響
        verdict, reason = check(spec, self.grants(ctx), {k: (v, here) for k, v in tc.args.items()})
        if verdict != "allow":
            ctx.emit("guardrail_tripped", guardrail="taint", stage="tool", verdict=verdict, reason=reason)
        if verdict == "deny":
            return ToolResult("error", f"已被安全規則攔下：{reason}。請向使用者說明，不要改用其他工具繞過。")
        if verdict == "ask":
            ctx.state.setdefault("ask", {})[tc.id] = reason
        return await nxt(tc)


class GuardrailMiddleware(Middleware):
    """執行宣告在 Agent 上的 Guardrail：input 在落地前、tool 在執行前、output 在回覆前。"""

    def _trip(self, ctx, g, reason):
        ctx.emit("guardrail_tripped", guardrail=g.name, stage=g.stage, reason=reason)

    def before_run(self, ctx, user_input):
        if user_input is None:
            return                                        # resume：沒有新輸入
        for g in ctx.agent.guardrails:
            if g.stage == "input" and (reason := g.check(ctx.deps, user_input)):
                self._trip(ctx, g, reason)
                raise StopRun("blocked", "為了保護您的資料，這則訊息無法處理，請移除敏感資訊後再試。")

    async def wrap_tool(self, ctx, tc, nxt):
        for g in ctx.agent.guardrails:
            if g.stage == "tool" and (reason := g.check(ctx.deps, tc)):
                self._trip(ctx, g, reason)
                return ToolResult("error", f"已被安全規則攔下：{reason}。請向使用者說明，不要改用其他工具繞過。")
        return await nxt(tc)

    async def wrap_model(self, ctx, req, nxt):
        resp = await nxt(req)
        if not resp.tool_calls:
            for g in ctx.agent.guardrails:
                if g.stage == "output" and (reason := g.check(ctx.deps, resp.text)):
                    self._trip(ctx, g, reason)
                    raise StopRun("blocked", "這個回覆沒有通過檢查，已轉給真人同事。")
        return resp
