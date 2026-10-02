import unittest

from loom import (Agent, Guardrail, Handoff, InMemorySession, Middleware, ModelResponse, Runner, StopRun, Tool,
                  ToolCall, pending_calls)
from loom.core import ConcurrencyError, Event, intent_key, validate_args
from loom.models import BudgetMiddleware, ScriptedModel, call, say
from loom import runtime


def obj(*names):
    return {"type": "object", "properties": {n: {"type": "string"} for n in names}, "required": list(names)}


GET = Tool("get_order", "查詢訂單狀態", obj("order_id"), lambda deps, order_id: {"order_id": order_id}, effect="read")
SEEN_KEYS = []
RET = Tool("create_return", "建立退貨單", obj("order_id"),
           lambda deps, order_id: SEEN_KEYS.append(deps["idempotency_key"]) or "R-1", effect="write",
           intent_fields=("order_id",))


def paired(events):
    asked = sorted(c["id"] for e in events if e.type == "model_response" for c in e.data["tool_calls"])
    return asked == sorted(e.data["id"] for e in events if e.type == "tool_result")


class CoreTest(unittest.TestCase):
    def test_happy_path_and_seven_core_events(self):
        s = InMemorySession("s1")
        r = Runner(ScriptedModel([call("get_order", order_id="B-1"), say("已出貨")])).run(
            Agent("cs", "客服", tools=(GET,)), "B-1？", s)
        self.assertEqual(r.status, "done")
        self.assertEqual([e.type for e in r.events], ["run_started", "user_message", "model_response", "tool_result",
                                                      "model_response", "run_finished"])
        self.assertTrue(paired(r.events))

    def test_handoff_switches_agent_and_permissions_follow(self):
        refund = Agent("refund", "退款", tools=(GET, RET))
        triage = Agent("triage", "分流", tools=(GET,), handoffs=(Handoff(refund, "退款"),))
        r = Runner(ScriptedModel([call("transfer_to_refund", note="退 B-1"), call("create_return", "c2", order_id="B-1"),
                                  say("好了")])).run(triage, "退貨", InMemorySession("s"))
        self.assertEqual((r.status, r.last_agent.name), ("done", "refund"))
        self.assertIn("handoff", [e.type for e in r.events])

    def test_input_guardrail_blocks_before_persisting(self):
        g = Guardrail("no_card", "input", lambda deps, text: "卡號" if "4111" in text else None)
        from loom.guardrails import GuardrailMiddleware
        model = ScriptedModel([])
        r = Runner(model, [GuardrailMiddleware()]).run(Agent("a", "", guardrails=(g,)), "卡號 4111", InMemorySession("s"))
        self.assertEqual(r.status, "blocked")
        self.assertNotIn("user_message", [e.type for e in r.events])
        self.assertEqual(model.calls, [])

    def test_max_tokens_never_executes_half_tool_call(self):
        cut = ModelResponse("您的", [ToolCall("c1", "create_return", {})], "max_tokens")
        r = Runner(ScriptedModel([cut])).run(Agent("a", "", tools=(RET,)), "退", InMemorySession("s"))
        self.assertEqual(r.status, "max_tokens")
        self.assertFalse([e for e in r.events if e.type == "tool_result"])

    def test_unknown_stop_reason_fails_loudly(self):
        with self.assertRaises(ValueError):
            ModelResponse(stop_reason="stop")

    def test_side_effect_tools_cannot_be_code_callable(self):
        with self.assertRaises(ValueError):
            Tool("refund", "退款", obj("order_id"), lambda deps, order_id: None, effect="destructive", code_callable=True)

    def test_validate_args(self):
        schema = {"type": "object", "properties": {"n": {"type": "integer"}, "s": {"type": "string", "enum": ["a"]}},
                  "required": ["n"]}
        self.assertIsNone(validate_args(schema, {"n": 1, "s": "a"}))
        self.assertIn("缺少", validate_args(schema, {}))
        self.assertIn("integer", validate_args(schema, {"n": True}))
        self.assertIn("只能是", validate_args(schema, {"n": 1, "s": "b"}))

    def test_idempotency_key_derived_from_intent_not_visible_to_model(self):
        SEEN_KEYS.clear()
        s = InMemorySession("s-key")
        Runner(ScriptedModel([call("create_return", order_id="B-1"), say("ok")])).run(
            Agent("a", "", tools=(RET,)), "退", s)
        self.assertEqual(SEEN_KEYS, [intent_key("s-key", "create_return", {"order_id": "B-1"}, ("order_id",))])
        self.assertNotIn("idempotency_key", RET.schema()["parameters"]["properties"])

    def test_stop_run_fills_pending_results(self):
        class StopOnTool(Middleware):
            async def wrap_tool(self, ctx, tc, nxt):
                raise StopRun("blocked", "停")
        r = Runner(ScriptedModel([call("get_order", order_id="B-1")]), [StopOnTool()]).run(
            Agent("a", "", tools=(GET,)), "?", InMemorySession("s"))
        self.assertEqual(r.status, "blocked")
        self.assertTrue(paired(r.events))
        self.assertEqual(pending_calls(r.events), [])

    def test_budget_is_checked_before_calling_model(self):
        priced = lambda: ModelResponse(tool_calls=[ToolCall("c", "get_order", {"order_id": "B-1"})],
                                       stop_reason="tool_use", usage={"input_tokens": 900, "output_tokens": 100})
        model = ScriptedModel([priced() for _ in range(5)])
        r = Runner(model, [BudgetMiddleware(2_500)]).run(Agent("a", "", tools=(GET,)), "?", InMemorySession("s"))
        self.assertEqual((r.status, len(model.calls)), ("budget", 3))

    def test_session_compare_and_set(self):
        s = InMemorySession("s")
        s.append(Event(0, "run_started", "a", {}))
        with self.assertRaises(ConcurrencyError):
            s.append(Event(0, "run_started", "a", {}))

    def test_agent_version_is_content_hash(self):
        a, b = Agent("a", "x", tools=(GET,)), Agent("a", "y", tools=(GET,))
        self.assertNotEqual(a.version, b.version)
        self.assertEqual(a.version, Agent("a", "x", tools=(GET,)).version)

    def test_contract_reference_and_async_runner_write_same_events(self):
        script = lambda: [call("get_order", order_id="B-1"), call("create_return", "c2", order_id="B-1"), say("好")]
        agent = Agent("cs", "客服", tools=(GET, RET))
        ref = Runner(ScriptedModel(script())).run(agent, "退", InMemorySession("s"))
        rt = runtime.run_virtual(runtime.Runner(ScriptedModel(script()), loop_guard=False).run(
            agent, "退", InMemorySession("s")))
        strip = lambda evs: [(e.type, {k: v for k, v in e.data.items() if k != "spec"}) for e in evs]
        self.assertEqual(strip(ref.events), strip(rt.events))


if __name__ == "__main__":
    unittest.main()
