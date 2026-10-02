"""loom.runtime：async、串流、並行 tool、取消、逾時、重試與 loop guard（第 24 章，v1.0 版）。

Runner 繼承 loom.core 的參考 Runner，只覆寫「怎麼呼叫模型」「怎麼執行 tool」「怎麼收尾」；
所以同樣的 Agent、輸入與劇本，寫進 Session 的核心事件序列和參考版相同（契約測試在 tests/）。
"""
from __future__ import annotations

import asyncio
import json
import random
import selectors
from dataclasses import dataclass, make_dataclass
from typing import Any, ClassVar

from .core import ModelError, RunResult, ToolCall, ToolResult, invoke, pending_calls
from .core import Runner as ReferenceRunner


# ───────────── 串流事件：給 UI／呼叫端即時消費，不持久化 ─────────────
@dataclass
class StreamEvent:
    run_id: str
    n: int                                  # 串流內的序號：重連時用來去重與續傳
    t: float                                # run 開始後經過的秒數
    type: ClassVar[str] = "stream"


def stream_type(name: str, fields: str) -> type:
    return make_dataclass(name.title().replace("_", ""), [(f, Any) for f in fields.split()],
                          bases=(StreamEvent,), namespace={"type": name})


ModelDelta = stream_type("model_delta", "step text")
ModelRetry = stream_type("model_retry", "step attempt delay reason discard_partial")
ToolStarted = stream_type("tool_started", "call_id name")
ToolFinished = stream_type("tool_finished", "call_id name status content")
RunCancelling = stream_type("run_cancelling", "reason")
Committed = stream_type("committed", "event")       # 一個核心事件已寫進 Session
KINDS = {c.type: c for c in (ModelDelta, ModelRetry, ToolStarted, ToolFinished, RunCancelling, Committed)}


@dataclass
class RetryPolicy:
    max_attempts: int = 4
    base: float = 0.5
    cap: float = 8.0
    seed: int = 7

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)  # 固定 seed：jitter 也能重現

    def delay(self, attempt: int, retry_after: float = 0.0) -> float:
        backoff = self.rng.uniform(0, min(self.cap, self.base * 2 ** (attempt - 1)))   # full jitter
        return round(max(backoff, retry_after), 2)


class LoopGuard:
    """滑動視窗內的重複呼叫（含 A-B-A-B），以及連續幾步沒有新資訊（第 24.8 節）。"""

    def __init__(self, window: int = 6, max_repeats: int = 2, max_stale_steps: int = 3):
        self.window, self.max_repeats, self.max_stale_steps = window, max_repeats, max_stale_steps
        self.recent: list[str] = []
        self.seen: set[str] = set()
        self.stale = 0

    def inspect(self, tc: ToolCall) -> str:
        self.recent = (self.recent + [tc.name + json.dumps(tc.args, sort_keys=True)])[-self.window:]
        n = self.recent.count(self.recent[-1])
        return "stop" if n > self.max_repeats + 1 else "warn" if n > self.max_repeats else "ok"

    def no_progress(self, results: list[str]) -> bool:
        self.stale = self.stale + 1 if results and all(r in self.seen for r in results) else 0
        self.seen.update(results)
        return self.stale >= self.max_stale_steps

    def reason(self, verdicts: dict[str, str]) -> str:
        return "提醒後仍重複相同呼叫" if "stop" in verdicts.values() else f"連續 {self.stale} 步沒有新資訊"


class Run:
    """一次執行的把手：stream() 取串流事件、cancel() 取消、result 取結果。"""

    def __init__(self, runner: "Runner", agent, user_input, session, deps):
        self.loop = asyncio.get_running_loop()
        self.t0, self.n, self.detached = self.loop.time(), 0, False
        self.queue: asyncio.Queue = asyncio.Queue()
        self.ctx = runner.context(agent, session, deps, push=self._push)
        self.id = self.ctx.run_id
        self.task = self.loop.create_task(runner.arun(agent, user_input, session, deps, ctx=self.ctx))
        self.task.add_done_callback(lambda _: self.queue.put_nowait(None))   # 哨兵：沒有事件的結局（ignored）也能結束串流

    @property
    def result(self) -> RunResult | None:
        return self.task.result() if self.task.done() else None

    def cancel(self) -> None:
        self.task.cancel()

    def _push(self, kind: str, **data: Any) -> None:
        self.n += 1
        if not self.detached:
            self.queue.put_nowait(KINDS[kind](self.id, self.n, round(self.loop.time() - self.t0, 2), **data))

    async def stream(self):
        try:
            while True:
                item = await self.queue.get()
                if item is None:
                    return
                yield item
                if isinstance(item, Committed) and item.event.type == "run_finished":
                    return
        finally:
            if not self.task.done():        # 消費者離開（關掉視窗）＝取消這次 run
                self.detached = True
                self.cancel()


class Runner(ReferenceRunner):
    def __init__(self, model, middleware=(), *, max_parallel: int = 4, tool_timeout: float = 2.0,
                 model_timeout: float = 10.0, run_timeout: float = 60.0, cancel_grace: float = 2.0,
                 retry: RetryPolicy | None = None, loop_guard: bool = True, max_result_chars: int = 4_000):
        super().__init__(model, middleware, max_result_chars=max_result_chars)
        self.max_parallel, self.tool_timeout, self.model_timeout = max_parallel, tool_timeout, model_timeout
        self.run_timeout, self.cancel_grace, self.loop_guard = run_timeout, cancel_grace, loop_guard
        self.retry = retry or RetryPolicy()

    def start(self, agent, user_input, session, deps=None) -> Run:
        """user_input 為 None 代表 resume。必須在 event loop 裡呼叫。"""
        return Run(self, agent, user_input, session, dict(deps or {}))

    async def run(self, agent, user_input, session, deps=None) -> RunResult:   # 第 24 章：coroutine
        run = self.start(agent, user_input, session, deps)
        async for _ in run.stream():
            pass
        return await run.task

    async def resume(self, agent, session, deps=None) -> RunResult:
        return await self.run(agent, None, session, deps)

    def _deadline(self):
        return asyncio.timeout(self.run_timeout)

    def _guard(self):
        return LoopGuard() if self.loop_guard else None

    async def _call_model(self, ctx, req):
        policy = self.retry
        for attempt in range(1, policy.max_attempts + 1):
            streamed = False
            try:
                async with asyncio.timeout(self.model_timeout):
                    if hasattr(self.model, "stream"):
                        resp = None
                        async for kind, data in self.model.stream(req.messages, req.tools, req.system):
                            if kind == "text_delta":
                                streamed = True
                                ctx.push("model_delta", step=req.step, text=data)
                            elif kind == "stop":
                                resp = data
                        if resp is None:
                            raise ModelError("network")             # 串流在 stop 前中斷
                    else:
                        resp = await super()._call_model(ctx, req)
            except (ModelError, TimeoutError) as exc:
                err = exc if isinstance(exc, ModelError) else ModelError("network")
                if not err.retryable or attempt == policy.max_attempts:   # 重試只看 retryable；refusal 不是錯誤
                    raise err
                delay = policy.delay(attempt, err.retry_after)
                ctx.push("model_retry", step=req.step, attempt=attempt, delay=delay, reason=err.kind,
                         discard_partial=streamed)          # UI 要清掉已顯示的半段文字
                await asyncio.sleep(delay)
                continue
            ctx.state["attempts"] = attempt
            return resp
        raise AssertionError("unreachable")

    async def _run_tools(self, ctx, calls, verdicts, call_tool, persist) -> None:
        # 連續的唯讀 tool 併成一組平行執行；有副作用的 tool 與 handoff 自成一組，依模型給的順序
        sem = ctx.state.setdefault("sem", asyncio.Semaphore(self.max_parallel))
        is_read = lambda tc: (t := ctx.find_tool(tc.name)) is not None and t.effect == "read"
        groups: list[list[ToolCall]] = []
        for tc in calls:
            if is_read(tc) and groups and is_read(groups[-1][0]):
                groups[-1].append(tc)
            else:
                groups.append([tc])
        for group in groups:
            done: dict[str, Any] = {}

            async def one(tc: ToolCall) -> None:
                async with sem:             # 平行上限：保護下游與 rate limit
                    done[tc.id] = await self._one(ctx, tc, verdicts[tc.id], call_tool)

            async with asyncio.TaskGroup() as tg:
                for tc in group:
                    tg.create_task(one(tc))
            for tc in group:                # 依 call 順序落地，不依完成順序
                persist(tc, done[tc.id])

    async def _invoke(self, ctx, tool, tc, deps):
        timeout = tool.timeout or self.tool_timeout
        if tool.effect == "read":
            async with asyncio.timeout(timeout):
                return await invoke(tool, deps, tc.args)
        # 有副作用的 tool 用 shield 包住：取消 run 不會把扣款砍到一半；逾時則回報「結果未知」
        effect = asyncio.ensure_future(invoke(tool, deps, tc.args))
        inflight = ctx.state.setdefault("inflight", {})
        inflight[tc.id] = effect
        try:
            return await asyncio.wait_for(asyncio.shield(effect), timeout)
        finally:
            if effect.done():
                inflight.pop(tc.id, None)

    async def _settle(self, ctx, status, extra=None) -> None:
        extra = dict(extra or {})
        results = ctx.state.get("results", {})
        for tc in pending_calls(ctx.session.load()):
            effect = ctx.state.get("inflight", {}).pop(tc.id, None)
            if effect is None or isinstance(results.get(tc.id), ToolResult):
                continue
            finished, _ = await asyncio.wait({effect}, timeout=self.cancel_grace)   # 副作用進行中：給寬限期
            if finished and not effect.cancelled() and effect.exception() is None:
                out = effect.result()
                text = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
                extra[tc.id] = ToolResult("ok", text + "（run 結束前已完成）")
            else:
                extra[tc.id] = ToolResult("unknown", f"結果未知：{tc.name} 在 run 結束時仍未完成。不要重試，請轉真人查證。")
        await super()._settle(ctx, status, extra)


# ───────────── 測試基礎設施：虛擬時間 event loop（第 24.9 節）─────────────
class _VirtualSelector(selectors.DefaultSelector):
    def __init__(self, loop: "VirtualTimeLoop"):
        super().__init__()
        self._loop = loop

    def select(self, timeout=None):
        ready = super().select(0)
        if not ready and timeout is None:
            raise RuntimeError("死結：沒有任何計時器或 I/O 能喚醒程式")
        if not ready:
            self._loop.now += timeout      # 沒事可做：直接把時鐘撥到下一個計時器
        return ready


class VirtualTimeLoop(asyncio.SelectorEventLoop):
    """asyncio.sleep、timeout 照常運作，但時間是假的：一秒不用等，結果完全可重現。"""

    def __init__(self) -> None:
        self.now = 0.0
        super().__init__(selector=_VirtualSelector(self))

    def time(self) -> float:
        return self.now


def run_virtual(coro):
    loop = VirtualTimeLoop()
    try:
        return loop.run_until_complete(coro)
    finally:                                # 和 asyncio.run 一樣：收掉還在跑的 task（例如逾時後仍在進行的副作用）
        rest = [t for t in asyncio.all_tasks(loop) if not t.done()]
        for t in rest:
            t.cancel()
        if rest:
            loop.run_until_complete(asyncio.gather(*rest, return_exceptions=True))
        loop.close()
