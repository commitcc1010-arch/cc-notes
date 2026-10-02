"""loom.tracing：span 樹、遮蔽、假名化與寫入時計價（第 29 章）。

- span 名稱依 OTel GenAI 慣例：invoke_agent → chat／execute_tool；屬性名稱以官方為準。
- span status 只記技術成敗；業務結果記在 bluebird.* 屬性（例如 bluebird.run.status）。
- 內容擷取預設關閉；PII 在匯出前遮蔽；使用者 id 以 HMAC 假名化；每個 span 帶租戶與 spec 版本。
這是教學版 tracer：介面刻意貼近 OTel SDK，換成官方 SDK 時只需替換 Tracer，instrumentation 不動。
"""
from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from .core import Interrupt, Middleware

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
TW_MOBILE = re.compile(r"09\d{2}-?\d{3}-?\d{3}")
CARD = re.compile(r"\b(?:\d[ -]?){13,16}\b")


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return CARD.sub("<CARD>", TW_MOBILE.sub("<PHONE>", EMAIL.sub("<EMAIL>", value)))
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    return value


def pseudonym(user_id: str, key: bytes) -> str:
    """keyed hash：同一使用者得到同一代號（可 join），沒有 key 就無法反推。"""
    return "u_" + hmac.new(key, user_id.encode(), hashlib.sha256).hexdigest()[:10]


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_id: str | None
    start: int
    end: int = 0
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    status: str = "UNSET"                   # UNSET｜OK｜ERROR


class Tracer:
    def __init__(self, clock: Callable[[], int], processors: list[Callable[[Span], Span]] | None = None):
        self.clock, self.processors = clock, processors if processors is not None else [self.redaction]
        self.finished: list[Span] = []
        self._n = 0

    def _id(self, n: int) -> str:
        self._n += 1                        # 確定性 id：輸出可重現；production 用隨機 id
        return hashlib.sha256(f"loom-{self._n}".encode()).hexdigest()[:n]

    def start(self, name: str, parent: Span | None = None, **attrs: Any) -> Span:
        return Span(name, parent.trace_id if parent else self._id(32), self._id(16),
                    parent.span_id if parent else None, self.clock(), attributes=dict(attrs))

    def end(self, sp: Span, error: str | None = None) -> None:
        sp.end = self.clock()
        if error:
            sp.status, sp.attributes["error.type"] = "ERROR", error
        elif sp.status == "UNSET":
            sp.status = "OK"
        for process in self.processors:     # 匯出前處理：遮蔽一定在離開 process 之前
            sp = process(sp)
        self.finished.append(sp)

    @staticmethod
    def redaction(sp: Span) -> Span:
        sp.attributes = {k: redact(v) for k, v in sp.attributes.items()}
        for ev in sp.events:
            ev["attributes"] = redact(ev["attributes"])
        return sp

    def tree(self, trace_id: str | None = None) -> list[str]:
        spans = [s for s in self.finished if trace_id in (None, s.trace_id)]
        out: list[str] = []

        def walk(parent: str | None, depth: int) -> None:
            for s in sorted((s for s in spans if s.parent_id == parent), key=lambda s: (s.start, s.span_id)):
                what = s.attributes.get("gen_ai.tool.name") or s.attributes.get("gen_ai.agent.name") or ""
                out.append(f"{'  ' * depth}{s.name} {what} [{s.status}] {s.end - s.start}ms".replace("  [", " ["))
                walk(s.span_id, depth + 1)
        walk(None, 0)
        return out


class TracingMiddleware(Middleware):
    """invoke_agent 由 on_event 開關（run_started／run_finished）；chat、execute_tool 由 wrap_* 量測。"""

    def __init__(self, tracer: Tracer, price: Callable[[str, dict], float], pseudonym_key: bytes,
                 model_name: str = "scripted", price_version: str = "demo-2026-10", capture_content: bool = False):
        self.t, self.price, self.key, self.model_name = tracer, price, pseudonym_key, model_name
        self.price_version, self.capture = price_version, capture_content

    def on_event(self, ctx, event):
        if event.type == "run_started":
            ctx.state["span"] = self.t.start("invoke_agent", **{
                "gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": ctx.agent.name,
                "gen_ai.conversation.id": ctx.session.id, "bluebird.spec.version": ctx.agent.version})
            ctx.state["cost"] = 0.0
        elif event.type in ("handoff", "guardrail_tripped", "approval_requested") and "span" in ctx.state:
            ctx.state["span"].events.append({"name": f"bluebird.{event.type}", "time": self.t.clock(),
                                             "attributes": {k: v for k, v in event.data.items() if k != "note"}})
        elif event.type == "run_finished" and "span" in ctx.state:
            root = ctx.state.pop("span")
            root.attributes.update({"bluebird.run.status": event.data["status"],   # 業務結果：不影響 span status
                                    # 租戶與身分在 before_run 才由 loom.auth 注入，所以收尾時才寫
                                    "bluebird.tenant.id": ctx.deps.get("tenant", ""),
                                    "bluebird.user.pseudonym": pseudonym(str(ctx.deps.get("user_id", "")), self.key),
                                    "bluebird.cost.usd": round(ctx.state["cost"], 6),
                                    "bluebird.price.version": self.price_version})
            self.t.end(root, "run_error" if event.data["status"] == "error" else None)

    async def wrap_model(self, ctx, req, nxt):
        sp = self.t.start("chat", ctx.state.get("span"), **{"gen_ai.operation.name": "chat",
                                                            "gen_ai.request.model": self.model_name})
        if self.capture:
            sp.attributes["gen_ai.input.messages"] = req.messages
        try:
            resp = await nxt(req)
        except Exception as exc:
            self.t.end(sp, type(exc).__name__)
            raise
        u = resp.usage
        cost = self.price(self.model_name, u)           # 寫入時就算好成本，並記下價目表版本
        ctx.state["cost"] = ctx.state.get("cost", 0.0) + cost
        sp.attributes.update({"gen_ai.usage.input_tokens": u.get("input_tokens", 0),
                              "gen_ai.usage.output_tokens": u.get("output_tokens", 0),
                              "gen_ai.usage.cache_read.input_tokens": u.get("cache_read_tokens", 0),
                              "gen_ai.response.finish_reasons": [resp.stop_reason], "bluebird.cost.usd": cost})
        self.t.end(sp)
        return resp

    async def wrap_tool(self, ctx, tc, nxt):
        sp = self.t.start("execute_tool", ctx.state.get("span"), **{
            "gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": tc.name, "gen_ai.tool.call.id": tc.id})
        if self.capture:
            sp.attributes["gen_ai.tool.call.arguments"] = tc.args
        try:
            r = await nxt(tc)
        except Interrupt:                                # 等待核准不是技術失敗
            sp.attributes["bluebird.tool.status"] = "interrupted"
            self.t.end(sp)
            raise
        except BaseException as exc:
            self.t.end(sp, type(exc).__name__)
            raise
        sp.attributes["bluebird.tool.status"] = r.status
        self.t.end(sp, r.status if r.status in ("error", "timeout", "unknown") else None)
        return r
