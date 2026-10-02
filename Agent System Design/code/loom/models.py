"""loom.models：ScriptedModel、provider adapter 介面、錯誤分類、熔斷、fallback、routing 與成本帳本（第 25 章）。

分工（canon）：重試與退避屬於 loom.runtime；錯誤分類、熔斷、fallback、routing、計費屬於這裡。
所有類別都實作同一個 Model 介面 complete(messages, tools, system)，所以 router 對 Runner 來說只是另一個 Model。
"""
from __future__ import annotations

import asyncio
import json
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

from .core import Middleware, ModelError, ModelResponse, StopRun, ToolCall


# ───────────── 劇本模型（全書統一介面）─────────────
class ScriptedModel:
    """依劇本回應的假模型。劇本的每一步是 ModelResponse，或「收到 messages 後回傳 ModelResponse」的函式。"""

    name = "scripted"

    def __init__(self, script: list[ModelResponse | Callable[[list[dict]], ModelResponse]]):
        self.script = list(script)
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict], tools: list[dict] | None = None, system: str = "") -> ModelResponse:
        self.calls.append(json.loads(json.dumps(messages)))
        if not self.script:
            raise RuntimeError("劇本已用完：agent 呼叫模型的次數比預期多")
        step = self.script.pop(0)
        return step(messages) if callable(step) else step


def call(name: str, call_id: str = "c1", **args: Any) -> ModelResponse:
    return ModelResponse(tool_calls=[ToolCall(call_id, name, args)], stop_reason="tool_use")


def calls(text: str, *specs: tuple[str, str, dict]) -> ModelResponse:
    """一則回應裡同時要求多個 tool（parallel tool calls）。"""
    return ModelResponse(text=text, tool_calls=[ToolCall(i, n, a) for i, n, a in specs], stop_reason="tool_use")


def say(text: str) -> ModelResponse:
    return ModelResponse(text=text)


def fail(err: ModelError) -> Callable[[list[dict]], ModelResponse]:
    def step(messages: list[dict]) -> ModelResponse:
        raise err                           # 劇本步驟：這一次模型呼叫直接失敗
    return step


class StreamingScriptedModel(ScriptedModel):
    """有 stream() 的劇本模型：先送 text_delta，最後送帶完整 ModelResponse 的 stop（canon 的串流介面）。"""

    def __init__(self, script, ttft: float = 0.4, chunk_delay: float = 0.05, chunk: int = 8):
        super().__init__(script)
        self.ttft, self.chunk_delay, self.chunk = ttft, chunk_delay, chunk

    async def stream(self, messages, tools=None, system=""):
        await asyncio.sleep(self.ttft)
        resp = self.complete(messages, tools, system)
        if not any(resp.usage.values()):    # 劇本沒給 usage：用字元數粗估，讓預算與成本有東西可量
            resp.usage = {"input_tokens": len(json.dumps([tools, messages], ensure_ascii=False)) // 2,
                          "output_tokens": max(1, len(resp.text)) + 20 * len(resp.tool_calls)}
        for i in range(0, len(resp.text), self.chunk):
            await asyncio.sleep(self.chunk_delay)
            yield "text_delta", resp.text[i:i + self.chunk]
        yield "stop", resp


# ───────────── provider adapter ─────────────
@dataclass
class ModelSpec:
    name: str
    provider: str
    tier: str                               # small｜frontier
    price: dict[str, float]                 # 每百萬 token 的美元（示意價格，不是任何供應商的報價）
    regions: tuple[str, ...] = ("tw",)


def classify(provider: str, status: int, body: dict) -> ModelError:
    """把 HTTP 狀態碼與錯誤內容翻成 loom 的錯誤種類；各家的 type 字串不同，規則集中在這裡。"""
    etype = body.get("error", {}).get("type", "")
    kind = (("quota" if etype == "insufficient_quota" else "rate_limit") if status == 429 else
            "overloaded" if status in (503, 529) else "server" if status >= 500 else
            "auth" if status in (401, 403) else
            "context_overflow" if "context" in etype else "invalid_request")
    return ModelError(kind, provider, status, float(body.get("retry_after", 0)))


class Adapter:
    """一個 provider 的翻譯層：統一格式 ⇄ provider JSON。子類只負責 build 與 parse；transport 可替換成假的。"""

    def __init__(self, spec: ModelSpec, transport: Callable[[dict], tuple[int, dict]]):
        self.spec, self.transport, self.name = spec, transport, spec.name

    def complete(self, messages, tools=None, system="") -> ModelResponse:
        status, body = self.transport(self.build(messages, tools or [], system))
        if status != 200:
            raise classify(self.spec.provider, status, body)
        resp = self.parse(body)
        resp.raw.update(model=self.spec.name, provider=self.spec.provider, body=body)   # raw 保留原始回應
        return resp

    def build(self, messages, tools, system) -> dict:
        raise NotImplementedError

    def parse(self, body: dict) -> ModelResponse:
        raise NotImplementedError


class MessagesAdapter(Adapter):
    """Messages 式 API（content block 中有 text 與 tool_use）的教學版；欄位以官方文件為準。"""

    STOP = {"end_turn": "end_turn", "tool_use": "tool_use", "max_tokens": "max_tokens", "refusal": "refusal"}

    def build(self, messages, tools, system):
        return {"model": self.spec.name, "system": system, "messages": messages,
                "tools": [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
                          for t in tools]}

    def parse(self, r):
        u = r["usage"]                      # 四個互斥的桶：未命中快取的 input 不含 cache 部分
        usage = {"input_tokens": u["input_tokens"], "cache_read_tokens": u.get("cache_read_input_tokens", 0),
                 "cache_write_tokens": u.get("cache_creation_input_tokens", 0), "output_tokens": u["output_tokens"]}
        text = "".join(b["text"] for b in r["content"] if b["type"] == "text")
        tcs = [ToolCall(b["id"], b["name"], b["input"]) for b in r["content"] if b["type"] == "tool_use"]
        if r["stop_reason"] not in self.STOP:
            raise ModelError("invalid_response", self.spec.provider)   # 不認得的值：大聲失敗
        return ModelResponse(text, tcs, self.STOP[r["stop_reason"]], usage)


class CircuitBreaker:
    def __init__(self, clock: Callable[[], float], window: int = 6, min_calls: int = 3,
                 threshold: float = 0.5, cooldown: float = 20.0):
        self.clock, self.min_calls, self.threshold, self.cooldown = clock, min_calls, threshold, cooldown
        self.state, self.opened_at, self.results = "closed", 0.0, deque(maxlen=window)

    def allow(self) -> bool:
        if self.state == "open" and self.clock() - self.opened_at >= self.cooldown:
            self.state = "half_open"        # 冷卻後放一個探測請求
        return self.state != "open"

    def record(self, ok: bool, err: ModelError | None = None) -> None:
        if err is not None and not err.counts_for_breaker:
            return                          # 400、quota 這類錯誤不代表對方壞了
        if self.state == "half_open":
            self.state, self.opened_at = ("closed", 0.0) if ok else ("open", self.clock())
            self.results.clear()
            return
        self.results.append(ok)
        if len(self.results) >= self.min_calls and self.results.count(False) / len(self.results) >= self.threshold:
            self.state, self.opened_at = "open", self.clock()


class FallbackChain:
    """依序嘗試候選模型；跳過熔斷中的，遇到可換家的錯誤就往下一個。介面和 ScriptedModel 相同。"""

    def __init__(self, models: list, breakers: dict[str, CircuitBreaker]):
        self.models, self.breakers, self.attempts = models, breakers, []

    def complete(self, messages, tools=None, system="") -> ModelResponse:
        self.attempts, last = [], None
        for m in self.models:
            br = self.breakers.get(getattr(m, "name", ""))
            if br and not br.allow():
                self.attempts.append(f"{m.name} 熔斷中")
                continue
            try:
                resp = m.complete(messages, tools, system)
            except ModelError as err:
                if br:
                    br.record(False, err)
                self.attempts.append(f"{m.name} ✗{err.kind}")
                if not err.fallback_ok:
                    raise                   # 換家也沒用的錯誤，直接往外丟
                last = err
                continue
            if br:
                br.record(True)
            self.attempts.append(f"{m.name} ✓")
            return resp
        # 整條鏈都失敗：丟出最後一個錯誤（全部熔斷中則視同 overloaded），讓 loom.runtime 依 retryable 決定要不要等一下再試（第 24、25 章）
        raise last if last is not None else ModelError("overloaded", "chain")


class Router:
    """先用硬條件（租戶允許的區域）過濾，再依任務類別選等級；同等級依偏好排成 fallback chain。"""

    def __init__(self, adapters: list[Adapter], breakers: dict[str, CircuitBreaker], routes: dict[str, str]):
        self.adapters, self.breakers, self.routes = adapters, breakers, routes

    def for_task(self, task: str, region: str) -> FallbackChain:
        tier = self.routes.get(task, "frontier")
        ok = [a for a in self.adapters if a.spec.tier == tier and region in a.spec.regions]
        if not ok:
            raise ModelError("no_route", "router")
        return FallbackChain(ok, self.breakers)


@dataclass
class CostLedger:
    """成本在寫入時依有版本的價目表計算；改價只影響之後的紀錄。"""

    prices: dict[str, dict[str, float]]
    price_version: str = "demo-2026-10"
    rows: list[dict] = field(default_factory=list)

    def price(self, model: str, usage: dict[str, int]) -> float:
        p = self.prices[model]
        return (usage.get("input_tokens", 0) * p["input"] + usage.get("cache_read_tokens", 0) * p["cache_read"]
                + usage.get("cache_write_tokens", 0) * p["cache_write"]
                + usage.get("output_tokens", 0) * p["output"]) / 1_000_000

    def record(self, tenant: str, model: str, usage: dict[str, int], **tags: Any) -> float:
        cost = self.price(model, usage)
        self.rows.append({"tenant": tenant, "model": model, "cost": cost, "price_version": self.price_version,
                          **usage, **tags})
        return cost

    def total(self, tenant: str | None = None) -> float:
        return sum(r["cost"] for r in self.rows if tenant in (None, r["tenant"]))


DEMO_PRICES = {   # 示意價格（USD／百萬 tokens）
    "scripted": {"input": 3.0, "cache_read": 0.3, "cache_write": 3.75, "output": 15.0},
    "sim-small": {"input": 0.5, "cache_read": 0.05, "cache_write": 0.6, "output": 2.0},
    "sim-large": {"input": 3.0, "cache_read": 0.3, "cache_write": 3.75, "output": 15.0},
}


class BudgetMiddleware(Middleware):
    """呼叫模型前檢查累計 token（呼叫模型就是花錢的動作）。軟上限：最多超出一輪。"""

    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens

    async def wrap_model(self, ctx, req, nxt):
        if sum(ctx.usage.values()) >= self.max_tokens:
            raise StopRun("budget", "這個問題處理得比預期久，我先轉給真人同事協助。")
        return await nxt(req)
