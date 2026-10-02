"""loom.evals：任務集、outcome grader 與 pass@k／pass^k（第 27 章）。

grader 看「環境的最終狀態」與「回覆中的宣稱是否和狀態相符」，不看 agent 自己說完成了沒有。
每題跑多次：pass@k 問「k 次裡至少一次成功」，pass^k 問「k 次全部成功」，後者才是可靠性。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from math import comb
from typing import Any, Callable

from .core import RunResult


@dataclass
class Task:
    id: str
    prompt: str
    script: Callable[[random.Random], list]               # 劇本：可依 rng 模擬模型的不穩定
    check: Callable[[Any, RunResult], list[str]]          # 回傳失敗理由；空清單代表通過
    setup: Callable[[], Any] = lambda: None               # 每次試驗都建立全新的環境
    tags: tuple[str, ...] = ()


@dataclass
class Trial:
    task: str
    n: int
    ok: bool
    failures: list[str]
    status: str
    usage: dict[str, int] = field(default_factory=dict)


def claim(text: str, keywords: tuple[str, ...], fact: bool, what: str) -> list[str]:
    """回覆宣稱了某件事（例如「已退款」），環境裡卻沒有發生：這是最傷信任的失敗。"""
    return [f"宣稱{what}，但環境狀態不符"] if any(k in text for k in keywords) and not fact else []


def run_suite(tasks: list[Task], harness: Callable[[Any, list], Callable[[str], RunResult]],
              trials: int = 4, seed: int = 27) -> list[Trial]:
    """harness(env, script) 回傳 execute(prompt)；evals 不知道 runner 是同步還是 async、用哪個模型。"""
    out = []
    for task in tasks:
        for i in range(trials):
            rng = random.Random(f"{seed}:{task.id}:{i}")
            env = task.setup()
            result = harness(env, task.script(rng))(task.prompt)
            failures = task.check(env, result)
            if result.status not in ("done", "interrupted"):
                failures = failures + [f"run status={result.status}"]
            out.append(Trial(task.id, i, not failures, failures, result.status, result.usage))
    return out


def pass_at_k(n: int, c: int, k: int) -> float:
    """n 次試驗成功 c 次，估計「抽 k 次至少一次成功」（Chen et al. 2021 的無偏估計）。"""
    return 1.0 if n - c < k else 1 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """估計「抽 k 次全部成功」；E[C(c,k)/C(n,k)] = p^k。"""
    return comb(c, k) / comb(n, k)


def report(results: list[Trial], k: int) -> dict[str, dict[str, float]]:
    by_task: dict[str, list[Trial]] = {}
    for r in results:
        by_task.setdefault(r.task, []).append(r)
    rows = {}
    for task, rs in by_task.items():
        n, c = len(rs), sum(r.ok for r in rs)
        rows[task] = {"n": n, "c": c, "pass@k": pass_at_k(n, c, k), "pass^k": pass_hat_k(n, c, k)}
    if rows:
        rows["_mean"] = {m: sum(r[m] for r in rows.values()) / len(rows) for m in ("pass@k", "pass^k")}
    return rows
