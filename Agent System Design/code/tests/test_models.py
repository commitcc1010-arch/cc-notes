"""loom.models 的錯誤分類、adapter、熔斷、fallback、routing 與成本帳本（第 25 章）。"""
import unittest

from loom.core import ModelError
from loom.models import (CircuitBreaker, CostLedger, FallbackChain, MessagesAdapter, ModelSpec, Router,
                         ScriptedModel, classify, say)


def spec(name, tier="frontier", regions=("tw",)):
    return ModelSpec(name, "acme", tier, {"input": 3.0, "cache_read": 0.3, "cache_write": 3.75, "output": 15.0},
                     regions)


def ok_body(text="好的", stop="end_turn"):
    return {"content": [{"type": "text", "text": text}], "stop_reason": stop,
            "usage": {"input_tokens": 100, "cache_read_input_tokens": 900, "output_tokens": 20}}


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class ClassifyTest(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(classify("acme", 429, {}).kind, "rate_limit")
        self.assertEqual(classify("acme", 429, {"error": {"type": "insufficient_quota"}}).kind, "quota")
        self.assertEqual(classify("acme", 529, {}).kind, "overloaded")
        self.assertEqual(classify("acme", 500, {}).kind, "server")
        self.assertEqual(classify("acme", 401, {}).kind, "auth")
        self.assertEqual(classify("acme", 400, {}).kind, "invalid_request")

    def test_retryable_vs_fallback(self):
        self.assertTrue(ModelError("rate_limit").retryable)
        self.assertFalse(ModelError("quota").retryable)          # 同一家重試沒用
        self.assertTrue(ModelError("quota").fallback_ok)         # 換家有用
        self.assertFalse(ModelError("invalid_request").fallback_ok)


class AdapterTest(unittest.TestCase):
    def test_usage_is_normalized_into_four_buckets(self):
        r = MessagesAdapter(spec("m1"), lambda req: (200, ok_body())).complete([{"role": "user", "content": "hi"}])
        self.assertEqual(r.usage, {"input_tokens": 100, "cache_read_tokens": 900, "cache_write_tokens": 0,
                                   "output_tokens": 20})
        self.assertEqual(r.raw["model"], "m1")

    def test_unknown_stop_reason_fails_loudly(self):
        a = MessagesAdapter(spec("m1"), lambda req: (200, ok_body(stop="pause_turn_v9")))
        with self.assertRaises(ModelError):
            a.complete([{"role": "user", "content": "hi"}])

    def test_http_error_is_classified(self):
        a = MessagesAdapter(spec("m1"), lambda req: (529, {}))
        with self.assertRaises(ModelError) as cm:
            a.complete([{"role": "user", "content": "hi"}])
        self.assertEqual(cm.exception.kind, "overloaded")


class BreakerTest(unittest.TestCase):
    def test_open_half_open_close(self):
        clock = Clock()
        br = CircuitBreaker(clock, min_calls=3, threshold=0.5, cooldown=20)
        for _ in range(3):
            br.record(False, ModelError("overloaded"))
        self.assertFalse(br.allow())
        clock.t = 21
        self.assertTrue(br.allow())                 # half_open：放一個探測請求
        br.record(True)
        self.assertEqual(br.state, "closed")

    def test_client_errors_do_not_trip(self):
        br = CircuitBreaker(Clock(), min_calls=3)
        for _ in range(5):
            br.record(False, ModelError("invalid_request"))
        self.assertEqual(br.state, "closed")


class FallbackTest(unittest.TestCase):
    def test_falls_back_to_next_model(self):
        bad = MessagesAdapter(spec("primary"), lambda req: (529, {}))
        good = MessagesAdapter(spec("backup"), lambda req: (200, ok_body("備援回答")))
        chain = FallbackChain([bad, good], {})
        self.assertEqual(chain.complete([{"role": "user", "content": "hi"}]).text, "備援回答")
        self.assertEqual(chain.attempts, ["primary ✗overloaded", "backup ✓"])

    def test_whole_chain_failure_raises_retryable_error(self):
        a = MessagesAdapter(spec("a"), lambda req: (529, {}))
        b = MessagesAdapter(spec("b"), lambda req: (503, {}))
        with self.assertRaises(ModelError) as cm:
            FallbackChain([a, b], {}).complete([{"role": "user", "content": "hi"}])
        self.assertTrue(cm.exception.retryable)     # runtime 可以等一下再試

    def test_non_fallback_error_is_not_retried_elsewhere(self):
        a = MessagesAdapter(spec("a"), lambda req: (400, {}))
        b = ScriptedModel([say("不該被呼叫")])
        b.name = "b"
        with self.assertRaises(ModelError):
            FallbackChain([a, b], {}).complete([{"role": "user", "content": "hi"}])
        self.assertEqual(b.calls, [])


class RouterAndLedgerTest(unittest.TestCase):
    def test_router_respects_region_and_tier(self):
        small = MessagesAdapter(spec("small-tw", tier="small"), lambda req: (200, ok_body()))
        big_us = MessagesAdapter(spec("big-us", regions=("us",)), lambda req: (200, ok_body()))
        router = Router([small, big_us], {}, {"faq": "small"})
        self.assertEqual([m.name for m in router.for_task("faq", "tw").models], ["small-tw"])
        with self.assertRaises(ModelError):
            router.for_task("refund", "tw")         # frontier 只有 us 區域：不能違反資料駐留

    def test_ledger_prices_cache_buckets(self):
        ledger = CostLedger({"m1": spec("m1").price})
        cost = ledger.record("shop-a", "m1", {"input_tokens": 1_000_000, "cache_read_tokens": 1_000_000,
                                              "cache_write_tokens": 0, "output_tokens": 0})
        self.assertAlmostEqual(cost, 3.3)
        self.assertAlmostEqual(ledger.total("shop-a"), 3.3)


if __name__ == "__main__":
    unittest.main()
