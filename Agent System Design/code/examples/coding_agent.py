"""內部 coding agent（簡化版）on loom v1.0：驗證閘門、durable session 與 crash 後的 resume、loop guard。

執行：python3 examples/coding_agent.py
注意：這裡的「測試」在同一個 process 裡執行，只是示範；真實的 coding agent 必須在 sandbox 裡跑（第 17 章）。
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loom import Agent, InMemorySession, Middleware, ToolCall
from loom.durable import FileSession, replay
from loom.models import ScriptedModel, call, say
from loom.runtime import Runner, run_virtual
from loom.tools import tool


class Crash(BaseException):
    """模擬 process 被殺：不是 Exception，runner 攔不到，事件日誌停在半路。"""


class Repo:
    def __init__(self) -> None:
        self.files = {"calc.py": "def add(a, b):\n    return a - b\n",
                      "test_calc.py": "assert add(2, 3) == 5\nassert add(-1, 1) == 0\n"}
        self.writes: dict[str, str] = {}               # idempotency key → path：同一個意圖只寫一次

    def tools(self):
        @tool("read", code_callable=True)
        def read_file(deps, path: str) -> str:
            """讀取 repo 中的檔案內容
            path: 檔案路徑，例如 calc.py
            """
            return self.files[path]

        @tool("write")
        def write_file(deps, path: str, content: str) -> str:
            """覆寫一個檔案（可回復：repo 有版本控制）
            path: 檔案路徑
            content: 新的完整內容
            """
            if deps["idempotency_key"] not in self.writes:
                self.writes[deps["idempotency_key"]] = path
                self.files[path] = content
            return f"已寫入 {path}（{len(content)} 字元）"

        @tool("read")
        def run_tests(deps) -> str:
            """執行測試，回傳 PASSED 或第一個失敗"""
            ns: dict = {}
            try:
                exec(self.files["calc.py"], ns)
                exec(self.files["test_calc.py"], ns)
            except AssertionError as exc:
                return f"FAILED: {exc or 'assertion failed'}"
            return "PASSED 2 tests"
        return read_file, write_file, run_tests


def tests_passed_after_last_write(ctx) -> str | None:
    """驗證閘門：證據必須來自 session log 裡的外部結果，而不是模型的宣稱。"""
    evidence = None
    for e in ctx.session.load():
        if e.type == "tool_result" and e.data["name"] == "write_file":
            evidence = None                             # 改過程式，之前的測試結果就不算數
        if e.type == "tool_result" and e.data["name"] == "run_tests" and e.data["content"].startswith("PASSED"):
            evidence = f"run_tests@seq{e.seq}: {e.data['content']}"
    return evidence


FIX = "def add(a, b):\n    return a + b\n"


def agent_for(repo: Repo) -> Agent:
    return Agent("coder", "你是青鳥的內部 coding agent。改完程式一定要跑測試。", tools=repo.tools(),
                 max_steps=10, verify=tests_passed_after_last_write)


class CrashAfter(Middleware):
    """在第一次 write_file 真的執行之後、結果寫進日誌之前讓 process 掛掉（最危險的窗口）。"""

    def __init__(self):
        self.armed = True

    async def wrap_tool(self, ctx, tc: ToolCall, nxt):
        r = await nxt(tc)
        if tc.name == "write_file" and self.armed:
            self.armed = False
            raise Crash("kill -9")
        return r


def main() -> None:
    print("── A 沒跑測試就宣告完成")
    repo = Repo()
    a = run_virtual(Runner(ScriptedModel([call("read_file", path="calc.py"),
                                          call("write_file", "c2", path="calc.py", content=FIX),
                                          say("修好了！")]), []).run(agent_for(repo), "修 add 的 bug", InMemorySession("a")))
    print(f"  status={a.status} evidence={a.evidence}")
    assert a.status == "unverified"

    print("── B 跑了測試：有外部證據才算完成")
    repo = Repo()
    b = run_virtual(Runner(ScriptedModel([call("write_file", path="calc.py", content=FIX),
                                          call("run_tests", "c2"), say("修好了，測試通過。")]), []).run(
        agent_for(repo), "修 add 的 bug", InMemorySession("b")))
    print(f"  status={b.status} evidence={b.evidence}")
    assert b.status == "done" and "PASSED" in b.evidence

    print("── C durable：寫檔後、記錄前 crash，換一個 worker 從日誌 resume")
    repo = Repo()
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "s-coding.jsonl"
        script = [call("write_file", path="calc.py", content=FIX), call("run_tests", "c2"), say("修好了。")]
        try:
            run_virtual(Runner(ScriptedModel(list(script)), [CrashAfter()]).run(
                agent_for(repo), "修 add 的 bug", FileSession(log)))
        except* Crash:                                  # TaskGroup 會把它包成 exception group
            pass
        state = replay(FileSession(log).load())
        print(f"  crash 後：上一個 run 結束狀態={state.last_status} 需要 resume={state.needs_resume} pending={state.pending}")
        # 新 worker、新的模型連線；已完成的模型回應在日誌裡，不再呼叫模型（劇本從第二步開始）
        c = run_virtual(Runner(ScriptedModel(script[1:]), []).resume(agent_for(repo), FileSession(log)))
        print(f"  resume 後：status={c.status} 實際寫檔次數={len(repo.writes)} 事件數={len(FileSession(log).load())}")
        assert c.status == "done" and len(repo.writes) == 1

    print("── D loop guard：一直重跑測試卻不改程式")
    repo = Repo()
    d = run_virtual(Runner(ScriptedModel([call("run_tests", f"c{i}") for i in range(8)]), []).run(
        agent_for(repo), "測試為什麼失敗？", InMemorySession("d")))
    print(f"  status={d.status}；" + "；".join(e.data["reason"] for e in d.events if e.type == "guardrail_tripped"))
    assert d.status == "loop"


if __name__ == "__main__":
    main()
