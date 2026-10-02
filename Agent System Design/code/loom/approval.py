"""loom.approval：policy engine、核准單狀態機、hash chain 稽核與 interrupt／resume（第 21 章）。

風險類別（讀取／寫入／金錢／破壞性）決定要不要找人；副作用等級（第 5 章）決定重試與平行。
硬底線只套用在「破壞性」類別，寫在引擎程式碼中，不是可改的規則。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable

from .core import Interrupt, Middleware, ToolResult, digest, intent_key

STRICT = {"auto": 0, "approve": 1, "deny": 2}
BASELINE = {0: "deny", 1: "deny", 2: "deny", 3: "approve", 4: "auto", 5: "auto"}
KINDS = ("read", "write", "money", "destructive")
TRANSITIONS = {"PENDING": {"APPROVED", "REJECTED", "EXPIRED", "CANCELLED"}, "APPROVED": {"EXECUTED", "FAILED"}}


@dataclass(frozen=True)
class ActionRequest:
    tool: str
    args: dict[str, Any]
    kind: str                               # 風險類別
    facts: dict[str, Any]                   # 來自系統紀錄的事實（帳齡、當日累計），不採信模型的說法


@dataclass(frozen=True)
class Rule:
    id: str
    when: Callable[[ActionRequest], bool]
    effect: str                             # auto｜approve｜deny
    reason: str
    approvers: tuple[str, ...] = ("客服",)
    timeout_s: int = 4 * 3600
    on_timeout: str = "deny"                # 逾時預設：選做錯時代價較低的一邊


@dataclass(frozen=True)
class Decision:
    effect: str
    rule: str
    reasons: tuple[str, ...]
    approvers: tuple[str, ...] = ()
    timeout_s: int = 0
    on_timeout: str = "deny"
    policy_version: str = ""


class PolicyEngine:
    def __init__(self, actions: dict[str, tuple[int, str]], rules: list[Rule] = (), version: str = "v1"):
        self.actions, self.rules, self.version = actions, list(rules), version   # 動作 → (autonomy 等級, 風險類別)

    def decide(self, tool: str, args: dict, facts: dict | None = None) -> Decision:
        if tool not in self.actions:
            return Decision("deny", "default-deny", ("未登記的動作一律拒絕",), policy_version=self.version)
        level, kind = self.actions[tool]
        req = ActionRequest(tool, args, kind, facts or {})
        base = Rule(f"baseline-L{level}", lambda r: True, BASELINE[level], f"{tool} 的 autonomy 等級是 L{level}")
        matched = [base] + [r for r in self.rules if r.when(req)]
        win = max(matched, key=lambda r: (STRICT[r.effect], len(r.approvers)))   # deny-overrides
        effect = win.effect
        if kind == "destructive" and effect == "auto":
            effect = "approve"              # 硬底線：破壞性動作永遠不完全自動
        return Decision(effect, win.id, tuple(r.reason for r in matched), win.approvers,
                        win.timeout_s, win.on_timeout, self.version)


def args_hash(tool: str, args: dict) -> str:
    return digest([tool, args], 12)


class AuditLog:
    """append-only 且以 hash 串起來：改掉任何一筆，後面的 hash 全部對不上。"""

    def __init__(self) -> None:
        self.entries: list[dict] = []

    @staticmethod
    def _hash(body: dict) -> str:
        return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]

    def append(self, ts: int, event: str, ticket: str, actor: str, **detail: Any) -> None:
        body = {"seq": len(self.entries), "ts": ts, "event": event, "ticket": ticket, "actor": actor,
                "detail": detail, "prev": self.entries[-1]["hash"] if self.entries else "0" * 12}
        self.entries.append({**body, "hash": self._hash(body)})

    def verify(self) -> int | None:
        """回傳第一筆對不上的位置；None 代表整條鏈完好。"""
        prev = "0" * 12
        for e in self.entries:
            body = {k: v for k, v in e.items() if k != "hash"}
            if e["prev"] != prev or e["hash"] != self._hash(body):
                return e["seq"]
            prev = e["hash"]
        return None


@dataclass
class Ticket:
    id: str                                 # = intent key：核准綁在意圖上，重試不會開第二張
    tool: str
    args: dict
    hash: str
    kind: str
    decision: Decision
    opened: int
    requester: str
    state: str = "PENDING"
    by: str = ""


class ApprovalDesk:
    def __init__(self, clock: Callable[[], int], audit: AuditLog | None = None):
        self.clock, self.audit, self.tickets = clock, audit or AuditLog(), {}

    def _move(self, t: Ticket, state: str, actor: str, **detail: Any) -> None:
        if state not in TRANSITIONS.get(t.state, set()):
            raise ValueError(f"核准單 {t.id} 不能從 {t.state} 變成 {state}")
        t.state = state
        self.audit.append(self.clock(), state.lower(), t.id, actor, **detail)

    def open(self, tid: str, tool: str, args: dict, kind: str, d: Decision, requester: str) -> Ticket:
        t = self.tickets[tid] = Ticket(tid, tool, args, args_hash(tool, args), kind, d, self.clock(), requester)
        self.audit.append(t.opened, "opened", tid, requester, rule=d.rule, hash=t.hash, policy=d.policy_version)
        return t

    def tick(self) -> None:
        for t in self.tickets.values():
            if t.state == "PENDING" and self.clock() - t.opened >= t.decision.timeout_s:
                # 不可逆的破壞性動作不得因逾時自動執行：on_timeout 寫 approve 也一律當過期
                ok = t.decision.on_timeout == "approve" and t.kind != "destructive"
                self._move(t, "APPROVED" if ok else "EXPIRED", "system", reason="timeout")

    def respond(self, tid: str, actor: str, role: str, verdict: str, seen_hash: str) -> str:
        t = self.tickets[tid]
        if t.state != "PENDING":
            return f"拒收：單據已是 {t.state}"
        if actor == t.requester or actor.startswith("agent:"):
            return "拒收：發起者與 agent 不能核准自己的請求"   # 職責分離
        if role not in t.decision.approvers:
            return f"拒收：{role} 不在核准關卡 {t.decision.approvers}"
        if seen_hash != t.hash:
            return "拒收：核准時看到的參數和待執行的參數不同"
        t.by = actor
        self._move(t, "APPROVED" if verdict == "approved" else "REJECTED", actor, role=role)
        return t.state

    def finish(self, tid: str, ok: bool) -> None:
        self._move(self.tickets[tid], "EXECUTED" if ok else "FAILED", "system")

    def cancel(self, tid: str) -> None:
        if self.tickets[tid].state == "PENDING":
            self._move(self.tickets[tid], "CANCELLED", "system")


class ApprovalMiddleware(Middleware):
    """掛在 wrap_tool：auto 放行、deny 回填錯誤、approve 開單並 Interrupt；resume 時依單據狀態執行或回填。"""

    def __init__(self, engine: PolicyEngine, desk: ApprovalDesk,
                 facts: Callable[[Any, Any], dict] = lambda ctx, tc: {}, ask_approvers: tuple[str, ...] = ("客服",)):
        self.engine, self.desk, self.facts, self.ask_approvers = engine, desk, facts, ask_approvers

    def _ticket_id(self, ctx, tc) -> str:
        tool = ctx.find_tool(tc.name)
        return intent_key(ctx.session.id, tc.name, tc.args, tool.intent_fields if tool else ())

    async def wrap_tool(self, ctx, tc, nxt):
        if ctx.find_tool(tc.name) is None:
            return await nxt(tc)            # 不存在的 tool 交給核心回填「沒有這個工具」
        d = self.engine.decide(tc.name, tc.args, self.facts(ctx, tc))
        ask = ctx.state.get("ask", {}).get(tc.id)       # loom.guardrails 的 ask：至少要核准
        if d.effect == "auto" and ask:
            d = Decision("approve", "guardrails-ask", (ask,), self.ask_approvers, 4 * 3600, "deny", d.policy_version)
        if d.effect == "deny":
            return ToolResult("error", f"政策不允許 agent 執行 {tc.name}（{d.rule}），請轉真人處理。")
        if d.effect == "auto":
            return await nxt(tc)
        tid = self._ticket_id(ctx, tc)
        t = self.desk.tickets.get(tid)
        if t is None:
            kind = self.engine.actions[tc.name][1]
            t = self.desk.open(tid, tc.name, tc.args, kind, d, f"agent:{ctx.agent.name}")
            ctx.emit("approval_requested", ticket=tid, call_id=tc.id, tool=tc.name, hash=t.hash,
                     rule=d.rule, approvers=list(d.approvers))
            raise Interrupt(tid, d.rule)
        self.desk.tick()
        if t.state == "PENDING":
            raise Interrupt(tid, "仍在等待核准")
        if t.state in ("REJECTED", "EXPIRED", "CANCELLED"):
            return ToolResult("error", f"核准單 {t.state}，{tc.name} 沒有執行。不要用相同參數再次申請，請告知使用者。")
        if t.state != "APPROVED" or args_hash(tc.name, tc.args) != t.hash:
            return ToolResult("error", "核准單與待執行的參數不符（或已執行過），未執行。")
        r = await nxt(tc)                   # idempotency key 與 ticket id 同源：重送也只扣一次
        self.desk.finish(tid, ok=not r.is_error)
        return ToolResult(r.status, f"已由 {t.by or 'system'} 核准；{r.content}")

    def on_event(self, ctx, event):
        # 被取消的 tool call（例如 run 被取消或逾時）：對應的待核准單一起取消
        if event.type == "tool_result" and event.data.get("status") == "cancelled":
            for t in self.desk.tickets.values():
                if t.tool == event.data["name"] and t.state == "PENDING" and t.id.startswith(ctx.session.id + ":"):
                    self.desk.cancel(t.id)
