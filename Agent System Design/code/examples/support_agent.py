"""青鳥客服 agent on loom v1.0：分流 → handoff → 退款專員；超過 500 元的退款要主管核准（interrupt／resume）。

執行：python3 examples/support_agent.py
"""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loom import Agent, Guardrail, Handoff, InMemorySession
from loom.approval import ApprovalDesk, ApprovalMiddleware, PolicyEngine, Rule
from loom.auth import AuthMiddleware, AuthServer
from loom.evals import Task, claim, report, run_suite
from loom.guardrails import GuardrailMiddleware
from loom.models import DEMO_PRICES, CostLedger, StreamingScriptedModel, call, say
from loom.runtime import Committed, ModelDelta, Runner, ToolFinished, run_virtual
from loom.tools import IdempotencyStore, tool
from loom.tracing import Tracer, TracingMiddleware

CARD = r"\b(?:\d[ -]?){16}\b"


# ───────── 青鳥的假後端：資料依租戶分開；金流閘道在「執行副作用的那一端」去重 ─────────
class Backend:
    def __init__(self) -> None:
        self.orders = {"shop-17": {"B-1042": {"owner": "u42", "status": "delivered", "paid": 1280},
                                   "B-1043": {"owner": "u42", "status": "delivered", "paid": 300}}}
        self.gateway = IdempotencyStore()
        self.refunds: list[dict] = []

    def tools(self):
        @tool("read", scope="orders:read")
        def get_order(deps, order_id: str) -> dict:
            """查詢訂單狀態與實付金額
            order_id: 訂單編號，例如 B-1042
            """
            o = self.orders[deps["tenant"]].get(order_id)
            if o is None or o["owner"] != deps["user_id"]:
                raise KeyError(f"找不到訂單 {order_id}，請向使用者確認編號")
            return {"order_id": order_id, "status": o["status"], "paid": o["paid"]}

        @tool("destructive", intent=("order_id", "amount"), scope="refunds:write")
        def issue_refund(deps, order_id: str, amount: int) -> dict:
            """對已送達的訂單退款（金額不可超過實付）
            order_id: 訂單編號
            amount: 退款金額（新台幣元）
            """
            def effect(order_id, amount):
                self.refunds.append({"tenant": deps["tenant"], "order_id": order_id, "amount": amount})
                return {"refund_id": f"RF-{len(self.refunds):03d}", "order_id": order_id, "amount": amount}
            result, replayed = self.gateway.run(deps["idempotency_key"], {"order_id": order_id, "amount": amount},
                                                0, effect)
            return {**result, "replayed": replayed}
        return get_order, issue_refund


def build(backend: Backend, script: list, clock: list[int]):
    get_order, issue_refund = backend.tools()
    no_card = Guardrail("no_card_number", "input",
                        lambda deps, text: "訊息中疑似有完整卡號" if re.search(CARD, text) else None)
    refund_agent = Agent("refund", "你負責退款。先查訂單，再依實付金額退款。", tools=(get_order, issue_refund))
    triage = Agent("triage", "你是青鳥客服的分流助理。", tools=(get_order,),
                   handoffs=(Handoff(refund_agent, "退款問題交給退款專員"),), guardrails=(no_card,))
    engine = PolicyEngine({"get_order": (4, "read"), "issue_refund": (4, "money")}, [
        Rule("refund-over-500", lambda r: r.kind == "money" and r.args["amount"] > 500, "approve", "退款超過 500 元", ("客服主管",)),
        Rule("refund-over-paid", lambda r: r.kind == "money" and r.args["amount"] > r.facts["paid"], "deny", "退款超過實付金額"),
    ], version="refund-policy@2026-10")
    desk = ApprovalDesk(clock=lambda: clock[0])

    def facts(ctx, tc):                    # 事實來自系統紀錄，不採信模型的說法
        o = backend.orders[ctx.deps["tenant"]].get(tc.args.get("order_id"), {})
        return {"paid": o.get("paid", 0)}

    auth = AuthServer("bluebird-idp", b"demo-key", clock=lambda: clock[0])
    tracer = Tracer(clock=lambda: int(asyncio.get_running_loop().time() * 1000))
    ledger = CostLedger(DEMO_PRICES)
    middleware = [TracingMiddleware(tracer, ledger.price, b"rotate-me"),
                  AuthMiddleware(auth, "loom-cs", {"triage": {"orders:read"}, "refund": {"orders:read", "refunds:write"}}),
                  GuardrailMiddleware(), ApprovalMiddleware(engine, desk, facts)]
    runner = Runner(StreamingScriptedModel(script, ttft=0.3, chunk=12), middleware)
    token = auth.issue("u42", "shop-17", "orders:read refunds:write", "loom-cs", ttl=3600)
    return runner, triage, desk, tracer, {"token": token}


SCRIPT = [
    call("transfer_to_refund", note="u42 要退 B-1042"),
    call("get_order", "c2", order_id="B-1042"),
    call("issue_refund", "c3", order_id="B-1042", amount=1280),
    say("已為您退款 1,280 元（RF-001），約 3–5 個工作天入帳。"),
]


async def stream_once(runner, agent, text, session, deps):
    run = runner.start(agent, text, session, deps)
    async for item in run.stream():
        if isinstance(item, ModelDelta):
            print(f"  {item.t:5.2f}s ▸ {item.text}")
        elif isinstance(item, ToolFinished):
            print(f"  {item.t:5.2f}s ⚙ {item.name} [{item.status}] {item.content[:40]}")
        elif isinstance(item, Committed) and item.event.type in ("handoff", "approval_requested", "run_finished"):
            d = item.event.data
            print(f"  {item.t:5.2f}s ● {item.event.type} {d.get('target') or d.get('ticket') or d.get('status')}")
    return run.result


async def main() -> None:
    clock = [0]
    backend = Backend()
    runner, triage, desk, tracer, deps = build(backend, list(SCRIPT), clock)
    session = InMemorySession("s-u42")

    print("── 1. 顧客要求退款 1,280 元（超過 L4 自動門檻）")
    r1 = await stream_once(runner, triage, "B-1042 我不要了，幫我全額退款", session, deps)
    assert r1.status == "interrupted" and backend.refunds == [], r1.output
    ticket = desk.tickets[r1.tickets[0]]

    print("\n── 2. 45 秒後客服主管在核准台處理（看到的參數 hash 必須和待執行的一致）")
    clock[0] += 45
    print("  agent 自己核准 →", desk.respond(ticket.id, "agent:refund", "客服主管", "approved", ticket.hash))
    print("  主管核准       →", desk.respond(ticket.id, "lead-chen", "客服主管", "approved", ticket.hash))

    print("\n── 3. resume：任何一個 worker 都能從 session 接手")
    r2 = await stream_once(runner, r1.last_agent, None, session, deps)
    r3 = await runner.resume(r1.last_agent, session, deps)          # 核准台的 webhook 重送
    print(f"  第二次 resume → {r3.status}；實際退款筆數 {len(backend.refunds)}；稽核鏈完好：{desk.audit.verify() is None}")
    assert r2.status == "done" and r3.status == "ignored" and len(backend.refunds) == 1

    print("\n── 4. trace（span 樹；業務結果在 bluebird.* 屬性）")
    for line in tracer.tree():
        print("  " + line)
    roots = [s for s in tracer.finished if s.name == "invoke_agent"]
    print("  ", {k: v for k, v in roots[-1].attributes.items() if k.startswith("bluebird.") and "pseudonym" not in k})



def evaluate() -> None:
    print("\n── 5. eval：每題跑 4 次，看 pass^k")
    tasks = [
        Task("refund-300-auto", "B-1043 退款", lambda rng: [
            call("transfer_to_refund", note="退 B-1043"), call("get_order", "c2", order_id="B-1043"),
            call("issue_refund", "c3", order_id="B-1043", amount=300),
            say("已退款 300 元。") if rng.random() > 0.3 else say("已退款 300 元，另補償 100 元購物金。")],
             check=lambda env, r: claim(r.output, ("購物金",), False, "補償購物金")
             + ([] if len(env.refunds) == 1 else ["退款筆數不對"]), setup=Backend),
        Task("refund-1280-needs-approval", "B-1042 全額退款", lambda rng: list(SCRIPT),
             check=lambda env, r: ([] if r.status == "interrupted" and not env.refunds else ["未經核准就退款"])
             + claim(r.output, ("已為您退款",), bool(env.refunds), "已退款"), setup=Backend),
    ]

    def harness(env, script):
        rnr, agent, _, _, d = build(env, script, [0])
        return lambda prompt: run_virtual(rnr.run(agent, prompt, InMemorySession("eval"), d))

    rows = report(run_suite(tasks, harness, trials=4), k=4)
    for name, row in rows.items():
        print(f"  {name:<28} " + "  ".join(f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}" for k, v in row.items()))


if __name__ == "__main__":
    run_virtual(main())
    evaluate()
