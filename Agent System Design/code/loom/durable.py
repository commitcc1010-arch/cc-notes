"""loom.durable：以 append-only 事件日誌實作 Session，並從日誌重播狀態（第 22 章）。

事件日誌就是 checkpoint：已完成的模型回應與 tool 結果都在 log 裡，resume 時直接重播、不重做；
只有 pending 的 tool call 會被補做，而有副作用的那些帶著同一把 idempotency key，下游只會生效一次。
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .core import ConcurrencyError, Event, needs_resume, pending_calls

UPCASTERS = {}   # (type, 舊版本) → 升級函式；讀舊事件時就地升級，不改寫檔案


def upcaster(type_: str, from_v: int):
    def register(fn):
        UPCASTERS[(type_, from_v)] = fn
        return fn
    return register


@upcaster("tool_result", 1)
def _tool_result_v1(data: dict) -> dict:
    """v0.5 之前的 tool_result 沒有 status 欄位：由 is_error 推回來（只增不改）。"""
    return {"status": "error" if data.get("is_error") else "ok", **data}


class FileSession:
    """一行一個事件的 JSONL 檔。append 時做 compare-and-set，並在回傳前 fsync：回傳了就代表寫進磁碟。"""

    def __init__(self, path: Path, session_id: str | None = None):
        self.path = Path(path)
        self.id = session_id or self.path.stem
        self._events: list[Event] = []
        self._size = -1

    def load(self) -> list[Event]:
        size = self.path.stat().st_size if self.path.exists() else 0
        if size != self._size:              # 別的 worker 寫過：重新讀
            text = self.path.read_text(encoding="utf-8") if size else ""
            self._events = [self._decode(json.loads(line)) for line in text.splitlines() if line]
            self._size = size
        return list(self._events)

    @staticmethod
    def _decode(row: dict) -> Event:
        data, v = row["data"], row.get("v", 1)
        while (row["type"], v) in UPCASTERS:
            data, v = UPCASTERS[(row["type"], v)](data), v + 1
        return Event(row["seq"], row["type"], row["agent"], data, v)

    def append(self, event: Event) -> None:
        current = len(self.load())
        if event.seq != current:
            raise ConcurrencyError(f"seq {event.seq} 已被寫過（目前長度 {current}）")
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self.load()


@dataclass
class RunState:
    last_status: str | None
    needs_resume: bool
    pending: list[str]
    open_tickets: list[str]
    usage: dict[str, int] = field(default_factory=dict)
    runs: int = 0


def replay(events: list[Event]) -> RunState:
    """只讀日誌就能回答：上一個 run 怎麼結束、有沒有要補做的、還有哪些核准單在等。"""
    finished = [e for e in events if e.type == "run_finished"]
    asked = {e.data["call_id"]: e.data["ticket"] for e in events if e.type == "approval_requested"}
    pending = [tc.id for tc in pending_calls(events)]
    usage: dict[str, int] = {}
    for e in events:
        if e.type == "model_response":
            for k, n in e.data["usage"].items():
                usage[k] = usage.get(k, 0) + n
    return RunState(finished[-1].data["status"] if finished else None, needs_resume(events), pending,
                    [asked[c] for c in pending if c in asked], usage,
                    sum(1 for e in events if e.type == "run_started"))
