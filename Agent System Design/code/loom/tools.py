"""loom.tools：從函式產生 Tool、副作用分級、idempotency（第 4、5、7 章）。

核心已經做了執行前驗證（validate_args）與 idempotency key 推導（intent_key）；
這裡提供宣告 tool 的便利層，以及「真正執行副作用的那一端」用的去重儲存。
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, get_type_hints

from .core import EFFECTS, Tool, digest

PY_TO_JSON = {str: "string", int: "integer", float: "number", bool: "boolean", dict: "object", list: "array"}


def schema_from(fn: Callable[..., Any]) -> tuple[str, dict]:
    """第一行 docstring 當描述，`名稱: 說明` 當參數說明；第一個參數 deps 不進 schema。"""
    hints = get_type_hints(fn)
    lines = (inspect.getdoc(fn) or "").splitlines()
    arg_docs = dict(l.strip().split(": ", 1) for l in lines[1:] if ": " in l)
    props, required = {}, []
    for i, (name, p) in enumerate(inspect.signature(fn).parameters.items()):
        if i == 0:
            continue                         # deps：由 harness 注入，模型看不到
        props[name] = {"type": PY_TO_JSON.get(hints.get(name, str), "string"), "description": arg_docs.get(name, "")}
        if p.default is inspect.Parameter.empty:
            required.append(name)
    return (lines[0] if lines else fn.__name__), {"type": "object", "properties": props, "required": required}


def tool(effect: str = "destructive", *, intent: tuple[str, ...] = (), code_callable: bool = False,
         timeout: float | None = None, scope: str = "", enums: dict[str, list] | None = None):
    """裝飾器：@tool("read") def get_order(deps, order_id: str) -> dict。不寫 effect 就當 destructive。"""
    if effect not in EFFECTS:
        raise ValueError(f"effect 必須是 {EFFECTS}")

    def wrap(fn: Callable[..., Any]) -> Tool:
        desc, params = schema_from(fn)
        for name, values in (enums or {}).items():
            params["properties"][name]["enum"] = list(values)
        return Tool(fn.__name__, desc, params, fn, effect, tuple(intent), code_callable, timeout, scope)
    return wrap


def lint(t: Tool) -> list[str]:
    """第 5 章的 tool 審查清單中，可以機器檢查的幾項。"""
    problems = []
    if len(t.description) < 8:
        problems.append(f"{t.name}: 描述太短，模型無從判斷何時使用")
    for name, spec in t.parameters.get("properties", {}).items():
        if not spec.get("description") and "enum" not in spec:
            problems.append(f"{t.name}.{name}: 參數沒有說明或合法值")
    if t.effect != "read" and not t.intent_fields:
        problems.append(f"{t.name}: 有副作用卻沒有 intent_fields，重試時無法穩定去重")
    return problems


class IdempotencyConflict(Exception):
    """同一把 key 配上不同的參數：多半是程式錯誤，絕不能默默執行。"""


@dataclass
class IdempotencyStore:
    """放在執行副作用的那一端（例如金流閘道）：key → (參數指紋, 結果)。"""

    ttl_seconds: float = 24 * 3600
    records: dict[str, tuple[str, Any, float]] = field(default_factory=dict)

    def run(self, key: str, args: dict, now: float, effect: Callable[..., Any]) -> tuple[Any, bool]:
        fp = digest(args)
        if key in self.records:
            old_fp, result, at = self.records[key]
            if now - at < self.ttl_seconds:
                if old_fp != fp:
                    raise IdempotencyConflict(f"key {key} 已用於不同參數")
                return result, True          # replay：回傳第一次的結果，不再執行
        result = effect(**args)
        self.records[key] = (fp, result, now)
        return result, False
