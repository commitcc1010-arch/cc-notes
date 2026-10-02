import asyncio
import unittest

from loom import Agent, InMemorySession, ModelError, ModelResponse, Tool
from loom.models import ScriptedModel, StreamingScriptedModel, call, calls, fail, say
from loom.runtime import ModelDelta, ModelRetry, Runner, ToolFinished, run_virtual


def obj(*names):
    return {"type": "object", "properties": {n: {"type": "string"} for n in names}, "required": list(names)}


def slow(seconds, effect="read", log=None):
    async def fn(deps, order_id):
        await asyncio.sleep(seconds)
        if log is not None:
            log.append(order_id)
        return {"order_id": order_id}
    return fn


def paired(events):
    asked = sorted(c["id"] for e in events if e.type == "model_response" for c in e.data["tool_calls"])
    return asked == sorted(e.data["id"] for e in events if e.type == "tool_result")


TWO = lambda: [calls("", ("c1", "get_order", {"order_id": "A"}), ("c2", "get_order", {"order_id": "B"})), say("好")]


class RuntimeTest(unittest.TestCase):
    def test_parallel_reads_and_call_order_persisted(self):
        agent = Agent("a", "", tools=(Tool("get_order", "查單", obj("order_id"), slow(1.0), effect="read"),))

        async def go(parallel):
            loop = asyncio.get_running_loop()
            t0 = loop.time()
            r = await Runner(ScriptedModel(TWO()), max_parallel=parallel).run(agent, "?", InMemorySession("s"))
            return r, loop.time() - t0
        (r4, t4), (r1, t1) = run_virtual(go(4)), run_virtual(go(1))
        self.assertAlmostEqual(t4, 1.0, places=2)
        self.assertAlmostEqual(t1, 2.0, places=2)
        self.assertEqual([e.data["id"] for e in r4.events if e.type == "tool_result"], ["c1", "c2"])

    def test_read_timeout_is_partial_failure(self):
        agent = Agent("a", "", tools=(Tool("get_order", "查單", obj("order_id"), slow(30), effect="read"),))
        r = run_virtual(Runner(ScriptedModel(TWO()), tool_timeout=2.0).run(agent, "?", InMemorySession("s")))
        self.assertEqual([e.data["status"] for e in r.events if e.type == "tool_result"], ["timeout", "timeout"])
        self.assertEqual(r.status, "done")

    def test_side_effect_timeout_is_unknown_not_retried(self):
        log = []
        agent = Agent("a", "", tools=(Tool("refund", "退款", obj("order_id"), slow(5, log=log), effect="destructive"),))
        r = run_virtual(Runner(ScriptedModel([call("refund", order_id="B-1"), say("轉真人")]), tool_timeout=2.0).run(
            agent, "退", InMemorySession("s")))
        self.assertEqual([e.data["status"] for e in r.events if e.type == "tool_result"], ["unknown"])

    def test_cancel_mid_tool_keeps_pairing_and_shields_effect(self):
        log = []
        agent = Agent("a", "", tools=(Tool("refund", "退款", obj("order_id"), slow(1.5, log=log), effect="destructive"),))

        async def go():
            run = Runner(ScriptedModel([call("refund", order_id="B-1"), say("x")]), tool_timeout=5, cancel_grace=2.0).start(
                agent, "退", InMemorySession("s"))
            asyncio.get_running_loop().call_later(0.5, run.cancel)
            items = [i async for i in run.stream()]
            return run.result, items
        r, items = run_virtual(go())
        self.assertEqual(r.status, "cancelled")
        self.assertTrue(paired(r.events))
        self.assertEqual(log, ["B-1"])                         # 扣款沒有被砍到一半
        self.assertIn("run 結束前已完成", [e for e in r.events if e.type == "tool_result"][0].data["content"])
        self.assertEqual(sum(isinstance(i, ToolFinished) for i in items), 1)

    def test_retry_only_retryable_errors(self):
        model = ScriptedModel([fail(ModelError("overloaded", "A", 529)), say("好")])
        agent = Agent("a", "")

        async def go(m):
            run = Runner(m).start(agent, "?", InMemorySession("s"))
            return [i async for i in run.stream()], run
        items, run = run_virtual(go(model))
        self.assertEqual(run.result.status, "done")
        self.assertEqual(sum(isinstance(i, ModelRetry) for i in items), 1)
        self.assertEqual([e.data["attempts"] for e in run.result.events if e.type == "model_response"], [2])
        items, run = run_virtual(go(ScriptedModel([fail(ModelError("invalid_request", "A", 400))])))
        self.assertEqual(run.result.status, "error")

    def test_refusal_is_a_status_not_retried(self):
        model = ScriptedModel([ModelResponse("無法協助", stop_reason="refusal")])
        r = run_virtual(Runner(model).run(Agent("a", ""), "?", InMemorySession("s")))
        self.assertEqual((r.status, len(model.calls)), ("refusal", 1))

    def test_streaming_deltas_then_committed(self):
        async def go():
            run = Runner(StreamingScriptedModel([say("您的訂單已出貨，預計明天到。")], chunk=6)).start(
                Agent("a", ""), "?", InMemorySession("s"))
            return [i async for i in run.stream()]
        items = run_virtual(go())
        text = "".join(i.text for i in items if isinstance(i, ModelDelta))
        self.assertEqual(text, "您的訂單已出貨，預計明天到。")
        self.assertEqual(items[-1].event.type, "run_finished")
        self.assertEqual([i.n for i in items], list(range(1, len(items) + 1)))

    def test_loop_guard(self):
        agent = Agent("a", "", tools=(Tool("get_order", "查單", obj("order_id"), lambda d, order_id: "同樣", effect="read"),))
        r = run_virtual(Runner(ScriptedModel([call("get_order", f"c{i}", order_id="B") for i in range(8)])).run(
            agent, "?", InMemorySession("s")))
        self.assertEqual(r.status, "loop")
        self.assertEqual([e.data["guardrail"] for e in r.events if e.type == "guardrail_tripped"], ["loop_guard"])

    def test_run_timeout(self):
        agent = Agent("a", "", tools=(Tool("get_order", "查單", obj("order_id"), slow(5), effect="read"),))
        r = run_virtual(Runner(ScriptedModel([call("get_order", f"c{i}", order_id=str(i)) for i in range(8)]),
                               tool_timeout=10, run_timeout=12, loop_guard=False).run(agent, "?", InMemorySession("s")))
        self.assertEqual(r.status, "timeout")
        self.assertTrue(paired(r.events))


if __name__ == "__main__":
    unittest.main()
