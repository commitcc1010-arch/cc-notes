"""loom.core：八個核心抽象、七種持久化事件與四個 middleware 擴充點（第 23 章，v1.0 版）。

依賴規則：核心只用標準函式庫，不 import loom 的任何其他模組；其他模組都只依賴這裡。
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import inspect
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

STOP_REASONS = ("end_turn", "tool_use", "max_tokens", "refusal")
USAGE_KEYS = ("input_tokens", "cache_read_tokens", "cache_write_tokens", "output_tokens")
EFFECTS = ("read", "write", "destructive")
TOOL_STATUSES = ("ok", "error", "timeout", "cancelled", "unknown")
CORE_EVENTS = ("run_started", "user_message", "model_response", "tool_result",
               "handoff", "guardrail_tripped", "run_finished")


# ───────────────────────── 模型介面的資料型別（第 4、25 章）─────────────────────────
@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class ModelResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"          # end_turn｜tool_use｜max_tokens｜refusal
    usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.stop_reason not in STOP_REASONS:   # 未知值大聲失敗，不默默當成 end_turn（第 25 章）
            raise ValueError(f"未知的 stop_reason：{self.stop_reason!r}")


class ModelError(Exception):
    """型別屬於 Model 介面（所以放在核心）；如何從 HTTP 錯誤分類成 kind 屬於 loom.models。"""

    RETRYABLE = frozenset({"rate_limit", "overloaded", "server", "network"})
    FALLBACK = RETRYABLE | {"quota", "auth"}
    BREAKER = frozenset({"overloaded", "server", "network"})

    def __init__(self, kind: str, provider: str = "", status: int = 0, retry_after: float = 0.0):
        super().__init__(f"{provider or 'model'}:{kind}" + (f"（HTTP {status}）" if status else ""))
        self.kind, self.provider, self.status, self.retry_after = kind, provider, status, retry_after

    @property
    def retryable(self) -> bool:          # 同一家重試有沒有用（loom.runtime 只看這個）
        return self.kind in self.RETRYABLE

    @property
    def fallback_ok(self) -> bool:        # 換一家有沒有用（loom.models 的 FallbackChain）
        return self.kind in self.FALLBACK

    @property
    def counts_for_breaker(self) -> bool:
        return self.kind in self.BREAKER


class Model(Protocol):
    def complete(self, messages: list[dict], tools: list[dict] | None = None, system: str = "") -> ModelResponse: ...


# ───────────────────────── 四個不可變的宣告 ─────────────────────────
@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable[..., Any]                  # fn(deps, **args)；可以是 async def
    effect: str = "destructive"             # 未標註的 tool 一律當 destructive（第 5 章）
    intent_fields: tuple[str, ...] = ()     # idempotency key 依這些欄位推導；空的代表全部參數
    code_callable: bool = False             # 有副作用的 tool 一律不可從程式呼叫（第 13 章）
    timeout: float | None = None
    scope: str = ""                         # loom.auth：呼叫它需要的 scope

    def __post_init__(self) -> None:
        if self.effect not in EFFECTS:
            raise ValueError(f"{self.name}: effect 必須是 {EFFECTS}")
        if self.code_callable and self.effect != "read":
            raise ValueError(f"{self.name}: 有副作用的 tool 不可設為 code_callable")

    def schema(self) -> dict[str, Any]:     # 模型只看得到這三個欄位；idempotency key 不在裡面
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


@dataclass(frozen=True)
class Guardrail:
    name: str
    stage: str                              # input｜tool｜output
    check: Callable[..., str | None]        # 回傳 None 代表通過；字串是攔下的理由


@dataclass(frozen=True)
class Handoff:
    target: "Agent"
    description: str

    @property
    def tool_name(self) -> str:
        return f"transfer_to_{self.target.name}"

    def schema(self) -> dict[str, Any]:
        return {"name": self.tool_name, "description": self.description,
                "parameters": {"type": "object", "properties": {"note": {"type": "string"}}, "required": ["note"]}}


@dataclass(frozen=True)
class Agent:                                # 純設定：不持有模型連線、不持有對話狀態
    name: str
    instructions: str
    tools: tuple[Tool, ...] = ()
    handoffs: tuple[Handoff, ...] = ()
    guardrails: tuple[Guardrail, ...] = ()
    max_steps: int = 8
    verify: Callable[["RunContext"], str | None] | None = None   # 驗證閘門（第 39 章）：回傳證據或 None

    @property
    def version(self) -> str:
        """以內容 hash 當版本號（第 42 章的 AgentSpec）：每段對話 pin 住它，trace 也帶著它。"""
        spec = {"name": self.name, "instructions": self.instructions, "max_steps": self.max_steps,
                "tools": [{**t.schema(), "effect": t.effect, "intent": list(t.intent_fields)} for t in self.tools],
                "handoffs": [h.target.name for h in self.handoffs], "guardrails": [g.name for g in self.guardrails]}
        return "spec-" + digest(spec, 10)


# ───────────────────────── Event 與 Session：唯一的事實來源 ─────────────────────────
@dataclass(frozen=True)
class Event:
    seq: int
    type: str
    agent: str
    data: dict[str, Any]
    v: int = 1                              # 事件 schema 版本：持久化的東西一定要能升級


class ConcurrencyError(Exception):
    """append 時發現 seq 已被別人寫過：兩個 worker 同時續跑同一個 session，只有一個能贏。"""


class Session(Protocol):
    id: str

    def load(self) -> list[Event]: ...
    def append(self, event: Event) -> None: ...


class InMemorySession:
    def __init__(self, session_id: str):
        self.id, self._events = session_id, []

    def load(self) -> list[Event]:
        return list(self._events)

    def append(self, event: Event) -> None:
        if event.seq != len(self._events):  # compare-and-set：和 loom.durable 的檔案版語意相同
            raise ConcurrencyError(f"seq {event.seq} 已被寫過（目前長度 {len(self._events)}）")
        self._events.append(event)


def to_messages(events: list[Event]) -> list[dict]:
    """核心事件投影成 messages；不認得的事件類型一律略過（新增事件類型因此向後相容）。"""
    out: list[dict] = []
    for e in events:
        if e.type == "user_message":
            out.append({"role": "user", "content": e.data["text"]})
        elif e.type == "model_response":
            out.append({"role": "assistant", "content": e.data["text"], "tool_calls": e.data["tool_calls"]})
        elif e.type == "tool_result":
            out.append({"role": "tool", "tool_call_id": e.data["id"], "name": e.data["name"],
                        "content": e.data["content"], "is_error": e.data["is_error"]})
    return out


def pending_calls(events: list[Event]) -> list[ToolCall]:
    """模型提出、但還沒有 tool_result 的 tool call（等待核准，或 crash 前沒做完）。"""
    done = {e.data["id"] for e in events if e.type == "tool_result"}
    return [ToolCall(**c) for e in events if e.type == "model_response"
            for c in e.data["tool_calls"] if c["id"] not in done]


def needs_resume(events: list[Event]) -> bool:
    """有 pending 的 tool call，或最後一個 run 沒有 run_finished（crash 在半路）。"""
    starts = [e.seq for e in events if e.type == "run_started"]
    ends = [e.seq for e in events if e.type == "run_finished"]
    return bool(pending_calls(events)) or bool(starts and (not ends or ends[-1] < starts[-1]))


def digest(obj: Any, n: int = 12) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:n]


def intent_key(scope_id: str, tool: str, args: dict, fields: tuple[str, ...] = ()) -> str:
    """由 harness 依業務意圖推導 idempotency key（第 5 章）；用 session id 而非 run id，resume 後仍是同一把。"""
    intent = {f: args.get(f) for f in fields} if fields else args
    return f"{scope_id}:{tool}:{digest([tool, intent], 10)}"


JSON_TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "object": dict, "array": list}


def validate_args(schema: dict, args: dict) -> str | None:
    """執行前的參數驗證（第 4、7 章）：必填、未知參數、基本型別與 enum。回傳 None 代表通過。"""
    props = schema.get("properties", {})
    missing = [p for p in schema.get("required", []) if p not in args]
    unknown = [a for a in args if a not in props]
    if missing or unknown:
        return f"參數錯誤：缺少 {missing}，不認得 {unknown}。正確參數：{list(props)}。"
    for name, value in args.items():
        spec = props[name]
        want = JSON_TYPES.get(spec.get("type", ""))
        if want and (not isinstance(value, want) or (spec.get("type") == "integer" and isinstance(value, bool))):
            return f"參數錯誤：{name} 應為 {spec['type']}，收到 {type(value).__name__}。"
        if "enum" in spec and value not in spec["enum"]:
            return f"參數錯誤：{name} 只能是 {spec['enum']}。"
    return None


async def invoke(tool: Tool, deps: dict, args: dict) -> Any:
    out = tool.fn(deps, **args)
    return await out if inspect.isawaitable(out) else out


# ───────────────────────── middleware 擴充點 ─────────────────────────
@dataclass
class ModelRequest:
    system: str
    messages: list[dict]
    tools: list[dict]
    step: int = 0


@dataclass
class ToolResult:
    status: str = "ok"                      # ok｜error｜timeout｜cancelled｜unknown
    content: str = ""

    @property
    def is_error(self) -> bool:
        return self.status != "ok"


class StopRun(Exception):
    """middleware 用來結束整個 run（預算用完、輸入被攔下）。Runner 保證 tool 配對不變式。"""

    def __init__(self, status: str, output: str):
        super().__init__(status)
        self.status, self.output = status, output


class Interrupt(Exception):
    """wrap_tool 用來暫停這個 tool call（等待核准）：不執行、不回填，run 以 interrupted 結束。"""

    def __init__(self, ticket: str, reason: str = ""):
        super().__init__(ticket)
        self.ticket, self.reason = ticket, reason


@dataclass
class RunContext:
    run_id: str
    agent: Agent
    session: Session
    deps: dict[str, Any]                    # 依賴注入：身分、租戶、client；模型看不到也改不了
    middleware: list["Middleware"] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=lambda: dict.fromkeys(USAGE_KEYS, 0))
    loaded_tools: list[Tool] = field(default_factory=list)   # loom.registry 延遲載入的 tool（只往尾端追加）
    state: dict[str, Any] = field(default_factory=dict)      # middleware 之間透過這裡溝通，不互相 import
    push: Callable[..., None] = lambda kind, **data: None    # 串流事件出口（loom.runtime 接上）
    hook_errors: list[str] = field(default_factory=list)

    def emit(self, type_: str, **data: Any) -> Event:
        """先落地、再通知 on_event、最後推串流：紀錄不會因 hook 失敗而遺失。"""
        ev = Event(len(self.session.load()), type_, self.agent.name, json.loads(json.dumps(data, ensure_ascii=False)))
        self.session.append(ev)
        for mw in self.middleware:
            try:
                mw.on_event(self, ev)
            except Exception as exc:        # 觀察者壞掉不能拖垮 run，但要留下訊號
                self.hook_errors.append(f"{type(mw).__name__}: {exc}")
        self.push("committed", event=ev)
        return ev

    def find_tool(self, name: str) -> Tool | None:
        return next((t for t in (*self.agent.tools, *self.loaded_tools) if t.name == name), None)

    def find_handoff(self, name: str) -> Handoff | None:
        return next((h for h in self.agent.handoffs if h.tool_name == name), None)

    def tool_schemas(self) -> list[dict]:   # 前綴不變式：固定 tools → handoffs → 延遲載入（只追加）
        return ([t.schema() for t in self.agent.tools] + [h.schema() for h in self.agent.handoffs]
                + [t.schema() for t in self.loaded_tools])


class Middleware:
    """四個擴充點；預設全部放行。before_run／on_event 是同步（before_run 也可以是 async），wrap_* 是 coroutine。"""

    def before_run(self, ctx: RunContext, user_input: str | None) -> None: ...   # resume 時 user_input 為 None
    def on_event(self, ctx: RunContext, event: Event) -> None: ...

    async def wrap_model(self, ctx: RunContext, req: ModelRequest, nxt) -> ModelResponse:
        return await nxt(req)

    async def wrap_tool(self, ctx: RunContext, tc: ToolCall, nxt) -> ToolResult:
        return await nxt(tc)


@dataclass
class RunResult:
    status: str        # done｜unverified｜max_steps｜max_tokens｜budget｜loop｜blocked｜cancelled｜timeout｜error｜refusal
    output: str        # 另有兩個非結束狀態：interrupted（等待核准）、ignored（重複的 resume 被忽略）
    last_agent: Agent
    usage: dict[str, int]
    events: list[Event]
    tickets: list[str] = field(default_factory=list)   # interrupted 時：等待中的核准單
    evidence: str | None = None


# ───────────────────────── 參考 Runner（同步介面，第 23 章的契約）─────────────────────────
class Runner:
    """參考實作：序列執行、沒有串流與重試。loom.runtime.Runner 繼承它，事件序列必須相同。"""

    def __init__(self, model: Model, middleware: list[Middleware] | tuple = (), *, max_result_chars: int = 4_000):
        self.model, self.middleware, self.max_result_chars = model, list(middleware), max_result_chars

    def run(self, agent: Agent, user_input: str, session: Session, deps: dict | None = None) -> RunResult:
        return asyncio.run(self.arun(agent, user_input, session, deps))

    def resume(self, agent: Agent, session: Session, deps: dict | None = None) -> RunResult:
        """核准有結果之後、或 crash 之後：從 session 讀回狀態，補做 pending 的 tool call 再繼續。"""
        return asyncio.run(self.arun(agent, None, session, deps))

    def context(self, agent: Agent, session: Session, deps: dict | None, push=None) -> RunContext:
        ctx = RunContext(f"{session.id}#{len(session.load())}", agent, session, dict(deps or {}), self.middleware)
        if push:
            ctx.push = push
        return ctx

    async def arun(self, agent, user_input, session, deps=None, ctx: RunContext | None = None) -> RunResult:
        ctx = ctx or self.context(agent, session, deps)
        start = len(session.load())
        resuming = user_input is None
        if resuming and not needs_resume(session.load()):   # 重複的 resume 回呼：什麼都不寫
            return RunResult("ignored", "沒有等待中的動作", agent, dict(ctx.usage), [])
        ctx.emit("run_started", agent=agent.name, spec=agent.version, resumed=resuming)
        try:
            async with self._deadline():
                for mw in self.middleware:      # 先過 before_run 再落地：被攔下的輸入不進 session
                    out = mw.before_run(ctx, user_input)
                    if inspect.isawaitable(out):
                        await out
                if not resuming and pending_calls(session.load()):
                    raise StopRun("interrupted", "還有等待核准的動作，新訊息請在核准後再送出。")
                if not resuming:
                    ctx.emit("user_message", text=user_input)
                status, output = await self._loop(ctx, resuming)
        except StopRun as stop:
            status, output = stop.status, stop.output
        except TimeoutError:
            status, output = "timeout", "處理時間超過上限，已轉給真人同事。"
            ctx.push("run_cancelling", reason="run_timeout")
        except asyncio.CancelledError:
            if (task := asyncio.current_task()) is not None:
                task.uncancel()                 # 取消是預期中的結局：收尾後正常結束
            status, output = "cancelled", ""
            ctx.push("run_cancelling", reason="使用者取消")
        except Exception as exc:                # 例如重試用盡的 ModelError
            status, output = "error", f"{type(exc).__name__}: {exc}"
        if status != "interrupted":
            await self._settle(ctx, status)
        ctx.emit("run_finished", status=status, output=output, tickets=ctx.state.get("tickets", []))
        return RunResult(status, output, ctx.agent, dict(ctx.usage), session.load()[start:],
                         list(ctx.state.get("tickets", [])), ctx.state.get("evidence"))

    async def _loop(self, ctx: RunContext, resuming: bool) -> tuple[str, str]:
        call_model = self._chain("wrap_model", ctx, lambda req: self._call_model(ctx, req))
        call_tool = self._chain("wrap_tool", ctx, lambda tc: self._execute(ctx, tc))
        guard = self._guard()
        if resuming and (pending := pending_calls(ctx.session.load())):
            if outcome := await self._batch(ctx, pending, call_tool, None):
                return outcome
        for step in range(1, ctx.agent.max_steps + 1):
            req = ModelRequest(ctx.agent.instructions, to_messages(ctx.session.load()), ctx.tool_schemas(), step)
            resp = await call_model(req)
            attempts = ctx.state.pop("attempts", 1)     # 重試次數由 runtime 記下（middleware 只看到 ModelResponse）
            for k in USAGE_KEYS:
                ctx.usage[k] += resp.usage.get(k, 0)
            cut = resp.stop_reason in ("max_tokens", "refusal")    # 半截的 tool call 不執行
            calls = [] if cut else resp.tool_calls
            ctx.emit("model_response", text=resp.text, tool_calls=[vars(tc) for tc in calls],
                     stop_reason=resp.stop_reason, usage=resp.usage, attempts=attempts)
            if cut:
                return resp.stop_reason, resp.text
            if not calls:
                return self._verify(ctx, resp.text)
            if outcome := await self._batch(ctx, calls, call_tool, guard):
                return outcome
        return "max_steps", "步驟用完了，我先整理目前進度並轉給真人同事。"

    def _verify(self, ctx: RunContext, text: str) -> tuple[str, str]:
        if ctx.agent.verify is None:
            return "done", text
        evidence = ctx.agent.verify(ctx)        # 沒有外部證據的「完成」不等於成功（第 39 章）
        ctx.state["evidence"] = evidence
        return ("done" if evidence else "unverified"), text

    async def _batch(self, ctx, calls: list[ToolCall], call_tool, guard) -> tuple[str, str] | None:
        verdicts = {tc.id: guard.inspect(tc) if guard else "ok" for tc in calls}
        tickets: list[str] = []

        def persist(tc: ToolCall, r: ToolResult | Interrupt) -> None:
            if isinstance(r, Interrupt):        # 等待核准：不回填，配對在 resume 時補齊
                tickets.append(r.ticket)
                return
            ctx.emit("tool_result", id=tc.id, name=tc.name, is_error=r.is_error, content=r.content, status=r.status)
            if (h := ctx.find_handoff(tc.name)) and not r.is_error:
                ctx.emit("handoff", source=ctx.agent.name, target=h.target.name, note=tc.args.get("note", ""))
                ctx.agent = h.target

        await self._run_tools(ctx, calls, verdicts, call_tool, persist)
        if tickets:
            ctx.state["tickets"] = tickets
            return "interrupted", "已送出核准申請，核准後會繼續處理。"
        executed = [ctx.state["results"][tc.id].content for tc in calls if verdicts[tc.id] == "ok"]
        if guard and ("stop" in verdicts.values() or guard.no_progress(executed)):
            ctx.emit("guardrail_tripped", guardrail="loop_guard", stage="tool", reason=guard.reason(verdicts))
            return "loop", "我卡在同一個步驟，已轉給真人同事。"
        return None

    async def _run_tools(self, ctx, calls, verdicts, call_tool, persist) -> None:
        for tc in calls:                        # 參考版：依模型給的順序逐一執行
            persist(tc, await self._one(ctx, tc, verdicts[tc.id], call_tool))

    async def _one(self, ctx, tc: ToolCall, verdict: str, call_tool) -> ToolResult | Interrupt:
        if (h := ctx.find_handoff(tc.name)):    # handoff 不碰外部世界，只換 active agent
            r: ToolResult | Interrupt = ToolResult("ok", f"已轉給 {h.target.name}")
        elif verdict != "ok":
            r = ToolResult("error", "已停止：重複呼叫。" if verdict == "stop" else
                           f"你最近已用相同參數呼叫 {tc.name} 多次，結果不會改變；請換做法或回覆使用者。")
        else:
            ctx.push("tool_started", call_id=tc.id, name=tc.name)
            try:
                r = await call_tool(tc)
            except Interrupt as it:
                r = it
        ctx.state.setdefault("results", {})[tc.id] = r
        status, content = ("interrupted", r.ticket) if isinstance(r, Interrupt) else (r.status, r.content)
        ctx.push("tool_finished", call_id=tc.id, name=tc.name, status=status, content=content)
        return r

    async def _execute(self, ctx: RunContext, tc: ToolCall) -> ToolResult:
        """洋蔥最內層：第 4 章的 dispatch（名稱、參數驗證、例外回填、截斷）＋ idempotency key。"""
        tool = ctx.find_tool(tc.name)
        if tool is None:
            return ToolResult("error", f"沒有名為 {tc.name} 的工具。可用的工具：{[t['name'] for t in ctx.tool_schemas()]}。")
        if problem := validate_args(tool.parameters, tc.args):
            return ToolResult("error", problem)
        deps = ctx.deps
        if tool.effect != "read":               # key 由 harness 推導、不在 schema 裡；去重在執行副作用的那一端
            deps = {**deps, "idempotency_key": intent_key(ctx.session.id, tool.name, tc.args, tool.intent_fields)}
        try:
            out = await self._invoke(ctx, tool, tc, deps)
        except TimeoutError:
            if tool.effect == "read":
                return ToolResult("timeout", f"{tc.name} 沒有在時限內回應，可稍後再查或告知使用者。")
            return ToolResult("unknown", f"結果未知：{tc.name} 逾時，可能已生效。不要重試，請轉真人查證。")
        except (StopRun, Interrupt):
            raise
        except Exception as exc:                # tool 的例外是觀察，回填給模型
            return ToolResult("error", f"{type(exc).__name__}: {exc}")
        text = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
        if len(text) > self.max_result_chars:
            text = text[: self.max_result_chars] + f"…（已截斷，原長 {len(text)} 字元）"
        return ToolResult("ok", text)

    async def _invoke(self, ctx, tool: Tool, tc: ToolCall, deps: dict) -> Any:
        return await invoke(tool, deps, tc.args)

    async def _call_model(self, ctx, req: ModelRequest) -> ModelResponse:
        resp = self.model.complete(req.messages, tools=req.tools, system=req.system)
        return await resp if inspect.isawaitable(resp) else resp

    async def _settle(self, ctx: RunContext, status: str, extra: dict | None = None) -> None:
        """不論 run 怎麼結束，每個 tool call 都要有 tool_result，Session 才能續跑。"""
        results, extra = ctx.state.get("results", {}), extra or {}
        for tc in pending_calls(ctx.session.load()):
            r = extra.get(tc.id) or results.get(tc.id)
            if not isinstance(r, ToolResult):
                r = extra[tc.id] = ToolResult("cancelled", f"{'已取消' if status == 'cancelled' else '已中止'}：{tc.name} 沒有執行。")
            if tc.id in extra:
                ctx.push("tool_finished", call_id=tc.id, name=tc.name, status=r.status, content=r.content)
            ctx.emit("tool_result", id=tc.id, name=tc.name, is_error=r.is_error, content=r.content, status=r.status)

    def _chain(self, method: str, ctx: RunContext, terminal):
        fn = terminal                           # 由內往外包：清單第一個 middleware 在最外層
        for mw in reversed(self.middleware):
            fn = (lambda m, nxt: lambda x: getattr(m, method)(ctx, x, nxt))(mw, fn)
        return fn

    def _deadline(self):
        return contextlib.nullcontext()

    def _guard(self):
        return None
