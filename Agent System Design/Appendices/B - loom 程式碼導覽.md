# 附錄 B　loom 程式碼導覽

> [!abstract] 本附錄地圖
> **用途**：全書的程式碼分成兩種。第一種是各章「動手做」中可以單獨執行的 Python 段落，第二種是第 45 章組裝出來的隨書套件 `Agent System Design/code/`（`loom` v1.0）。本附錄是這兩者的索引：怎麼執行、套件裡有哪些模組、每個模組的公開介面與對應測試、每章的程式後來變成了什麼、`loom` 怎麼從 v0.1 長到 v1.0、要擴充時照什麼步驟做，以及教學版刻意沒做的事。
>
> **怎麼查**：
> - 第一次拿到套件、想先跑起來：看 B.1。
> - 想知道某個類別在哪個檔案、建構子要傳什麼：先看 B.2 的目錄與依賴圖，再到 B.3 查該模組的介面。B.3 的簽名直接從 `code/loom/` 的原始碼整理出來。
> - 讀到某一章的「動手做」，想知道它在 v1.0 裡變成哪個模組，或根本沒有收錄：查 B.4。
> - 要寫遷移文件或向同事解釋版本差異：查 B.5。
> - 要加新的 tool、model provider、middleware 或 memory／session backend：照 B.6 的步驟做，再對照第 45 章 45.11 節。
> - 要評估「能不能直接拿去上線」：先讀 B.7。
>
> **前置知識**：第 4 章（`loom` v0.1）、第 23–25 章（`loom` v0.5）、第 45 章（`loom` v1.0）。

## B.1 怎麼執行

全書的程式有一個共同前提：**只用 Python 3.11 以上版本的標準函式庫，不連網，也不需要 API key**。需要模型的地方都用 `ScriptedModel`（依劇本回應的假模型），需要時間的地方用模擬時鐘或虛擬時間 event loop，所以每次執行的輸出都一樣。示範怎麼接真實 API 或第三方框架的段落，第一行都標了 `# not-runnable`，這些段落只示範介面形狀，不會被執行。

### B.1.1 環境需求

| 項目 | 需求 | 說明 |
|---|---|---|
| Python | 3.11 以上 | 套件用到 `asyncio.timeout`、`asyncio.TaskGroup`、`Task.uncancel()`，範例用到 `except*`，這些都是 3.11 才有的語法與 API |
| 第三方套件 | 不需要 | `tests/test_architecture_and_examples.py` 會檢查每個 import 都來自標準函式庫 |
| 網路、API key | 不需要 | MCP 走 in-process transport；模型是 `ScriptedModel`／`StreamingScriptedModel` |
| 作業系統 | macOS 或 Linux | 第 17 章的 `run_untrusted()` 用到 `resource` 模組（rlimit），在不支援的平台上會回報「限制沒有生效」；隨書套件本身不依賴作業系統功能 |
| 執行時間 | 不到 1 秒 | 套件的 56 個測試約 0.1 秒；虛擬時間讓「等 45 秒核准」「退避 8 秒」都不必真的等 |

> [!warning] 常見誤解
> 「`python3` 就是夠新的 Python。」不一定。macOS 內建的 `/usr/bin/python3` 可能是 3.9：在這台機器上用它跑套件測試，會出現 `SyntaxError` 與一連串失敗。執行前先跑 `python3 --version` 確認版本是 3.11 以上；如果不是，就改用明確的 `python3.11`、`python3.12` 等指令。

### B.1.2 執行各章的「動手做」程式

各章的每一段 ````python```` 都是自給自足的：需要的 `ToolCall`、`ModelResponse`、`ScriptedModel` 以及該段用到的類別都定義在同一段裡，最後用 `assert` 驗證行為並印出結果。執行方式有兩種：

| 方式 | 指令（在 repo 根目錄） | 用途 |
|---|---|---|
| 單獨執行一段 | 把該段程式存成 `demo.py`，執行 `python3 demo.py` | 邊讀邊改、觀察輸出；輸出應該和書中緊接的 ````text```` 區塊一致 |
| 一次執行某幾章的全部段落 | `python3 tools/check_agent_system_book.py 4 45` | 每段單獨執行（10 秒逾時），同時檢查格式；`--no-run` 只解析不執行 |
| 檢查全書 | `python3 tools/check_agent_system_book.py` | 全部章節，適合改完共用介面之後跑一次 |

本書撰寫時（2026 年 10 月）在這台機器上執行 `python3 tools/check_agent_system_book.py 4 45`，結果是「檢查 2 章、16 組問答：0 errors、0 warnings」；檢查全書時 46 章的所有可執行段落都通過，回報的錯誤只有當時尚未完成的附錄檔案。

### B.1.3 執行隨書套件

隨書套件的所有指令都在 `Agent System Design/code` 目錄下執行，因為測試與範例都以這個目錄為根來 import `loom`。

```text
$ cd "Agent System Design/code"
$ python3 -m unittest discover -s tests            # 全部 56 個測試
$ python3 -m unittest discover -s tests -v         # 列出每個測試的名稱與結果
$ python3 -m unittest tests.test_core              # 只跑一個測試檔
$ python3 -m unittest tests.test_core.CoreTest.test_validate_args   # 只跑一個測試
$ python3 examples/support_agent.py                # 客服：handoff、核准中斷與恢復、tracing、eval
$ python3 examples/coding_agent.py                 # coding（簡化版）：驗證閘門、crash 後 resume、loop guard
$ python3 examples/research_agent.py               # research：memory、registry、MCP、平行查詢、taint、證據帳本
```

下面是撰寫本附錄時在 `Agent System Design/code` 下實際執行 `python3 -m unittest discover -s tests` 的結果（Python 3.14.6）：

```text
$ python3 -m unittest discover -s tests
........................................................
----------------------------------------------------------------------
Ran 56 tests in 0.098s

OK
```

撰寫時另外用 Python 3.11.14 與 3.12.12 各跑了一次，測試全部通過；三個範例在 3.11 下的結束碼都是 0。耗時每次略有不同（0.07 到 0.1 秒之間），這是正常的，測試結果本身不受影響。56 個測試分布在五個檔案：

| 測試檔 | 測試類別 | 測試數 | 鎖住的語意 |
|---|---|---|---|
| `tests/test_core.py` | `CoreTest` | 13 | 七種核心事件、handoff 與權限、input guardrail 擋在落地前、max_tokens 不執行半截 tool call、未知 stop_reason 報錯、副作用 tool 不可 `code_callable`、參數驗證、idempotency key 不在 schema 裡、`StopRun` 時補齊配對、預算在呼叫模型前檢查、Session compare-and-set、`Agent.version` 是內容 hash、參考 Runner 與 async runtime 的契約測試 |
| `tests/test_runtime.py` | `RuntimeTest` | 9 | 唯讀 tool 平行執行但依 call 順序落地、唯讀逾時是部分失敗、副作用逾時記為 unknown 且不重試、取消時保持配對並 shield 副作用、只重試 retryable 錯誤、refusal 不重試、串流先 delta 後 committed、loop guard、run 逾時 |
| `tests/test_modules.py` | `ToolsTest`、`ContextTest`、`MemoryTest`、`RegistryTest`、`MCPTest`、`ApprovalTest`、`DurableTest`、`GuardrailsTest`、`AuthTest`、`TracingTest`、`EvalsTest` | 18 | 各模組的單元語意，見 B.3 每個模組的「測試」欄 |
| `tests/test_models.py` | `ClassifyTest`、`AdapterTest`、`BreakerTest`、`FallbackTest`、`RouterAndLedgerTest` | 12 | 錯誤分類與 retryable／fallback_ok 的差別、usage 正規化成四個桶、未知 stop_reason 報錯、熔斷器 closed → open → half_open → closed、client 錯誤不觸發熔斷、fallback 換家與不可換家的錯誤、整條鏈失敗時丟出 retryable 錯誤、router 遵守區域與等級、成本帳本依快取分桶計價 |
| `tests/test_architecture_and_examples.py` | `ArchitectureTest`、`ExamplesTest` | 4 | 依賴規則（核心不 import 其他模組、其他模組只 import 核心、只用標準函式庫），以及三個範例跑完後的關鍵輸出 |

`ExamplesTest` 會把三個範例當成模組載入並擷取輸出，斷言其中幾行關鍵字（例如客服範例的「第二次 resume → ignored；實際退款筆數 1」、coding 範例的「實際寫檔次數=1」）。所以只要測試通過，範例也一定跑得完；但範例的完整輸出（第 45 章 45.13 節）要直接執行才看得到。

## B.2 隨書套件的目錄結構與模組依賴圖

### B.2.1 目錄結構

下圖是 `Agent System Design/code/` 的實際結構，行數是 `wc -l` 的結果（包含空行與註解），括號裡是模組誕生的章節。`loom/` 合計約 2,360 行，和第 45 章所說的「約 2,400 行」一致；`examples/` 約 450 行，`tests/` 約 740 行。

```text
 Agent System Design/code/
 ├── README.md                        執行方式、目錄、依賴規則、擴充摘要
 ├── loom/
 │   ├── __init__.py          12 行   __version__ = "1.0.0"；從 core 匯出 22 個公開名稱
 │   ├── core.py             512 行   宣告、事件、Session、RunContext、Middleware、參考 Runner（第 4、23 章）
 │   ├── runtime.py          269 行   async Runner、Run 把手、串流事件、RetryPolicy、LoopGuard、虛擬時間（第 24 章）
 │   ├── models.py           241 行   劇本模型、Adapter、classify、熔斷、fallback、router、成本帳本、預算（第 25 章）
 │   ├── tools.py             80 行   @tool、schema_from、lint、IdempotencyStore（第 4、5、7 章）
 │   ├── context.py           87 行   build_view、ContextPolicy、ContextMiddleware（第 9、10 章）
 │   ├── compaction.py        54 行   六段交接筆記、check_handoff、Compactor（第 10 章）
 │   ├── memory.py           122 行   MemoryStore：/memories 虛擬路徑、組織唯讀、TTL、刪除權（第 12 章）
 │   ├── registry.py          79 行   ToolRegistry（BM25）、RegistryMiddleware（第 13 章）
 │   ├── mcp.py              170 行   MiniMCPServer／Client、InProcessTransport、mcp_tools、fingerprint（第 14 章）
 │   ├── approval.py         204 行   PolicyEngine、ApprovalDesk、AuditLog、ApprovalMiddleware（第 21 章）
 │   ├── durable.py           88 行   FileSession（JSONL、compare-and-set、fsync、upcaster）、replay（第 22 章）
 │   ├── guardrails.py       119 行   GuardrailMiddleware、Label、ToolSpec、check、TaintMiddleware（第 23、31、32 章）
 │   ├── auth.py              88 行   AuthServer（issue／verify／exchange）、AuthMiddleware（第 33、42 章）
 │   ├── tracing.py          158 行   Span、Tracer、redact、pseudonym、TracingMiddleware（第 29 章）
 │   └── evals.py             77 行   Task、Trial、run_suite、claim、pass@k／pass^k、report（第 27 章）
 ├── examples/
 │   ├── support_agent.py    165 行   客服：分流 → handoff → 退款專員；1,280 元退款走核准；trace；eval
 │   ├── coding_agent.py     139 行   coding（簡化版）：驗證閘門、寫檔後 crash 再 resume、loop guard
 │   └── research_agent.py   144 行   research：memory、registry、MCP、平行查詢、證據帳本、taint → 核准
 └── tests/
     ├── test_core.py        122 行
     ├── test_models.py      123 行
     ├── test_runtime.py     120 行
     ├── test_modules.py     307 行
     └── test_architecture_and_examples.py   64 行
```

這個結構是扁平的：每個模組一個檔案，沒有子套件，`loom/` 一眼看得完。每個模組檔案開頭都有一段 docstring，寫明它來自哪一章、遵守哪些不變式；讀程式時建議先讀 docstring，再讀該模組在 B.3 的介面表。`tests/` 沒有 `__init__.py`，但從 `code/` 目錄執行 `python3 -m unittest tests.test_core` 時，Python 會把它當成命名空間套件處理，所以兩種寫法（`discover -s tests` 與指定模組）都能用。

### B.2.2 模組依賴圖

依賴圖規定「誰可以 import 誰」。下圖依實際的 import 敘述畫出：每個箭頭旁邊列出該模組從 `loom.core` 匯入的名稱。

```text
                                         loom.core
                                    （只 import 標準函式庫）
   ▲            ▲            ▲            ▲            ▲            ▲            ▲
   │            │            │            │            │            │            │
 runtime      models       tools        context      memory       registry      mcp
 ModelError   Middleware   EFFECTS      Event        Tool         Middleware    Tool
 RunResult    ModelError   Tool         Middleware                Tool          digest
 ToolCall     ModelResponse digest      to_messages               ToolResult
 ToolResult   StopRun
 invoke       ToolCall
 pending_calls
 Runner（改名為 ReferenceRunner 後繼承）

   ▲            ▲            ▲            ▲            ▲            ▲
   │            │            │            │            │            │
 approval     durable      guardrails   auth         tracing      evals
 Interrupt    ConcurrencyError Middleware Middleware  Interrupt    RunResult
 Middleware   Event        StopRun      StopRun      Middleware
 ToolResult   needs_resume ToolResult   ToolResult
 digest       pending_calls
 intent_key

 compaction：不 import 任何 loom 模組（純函式＋Compactor），由應用層注入 ContextMiddleware

 examples/*.py ──► 可以 import 任何 loom 模組（組裝發生在應用層）
```

這張圖由上往下讀。最上面的 `loom.core` 沒有任何往外的箭頭：它只 import `asyncio`、`contextlib`、`hashlib`、`inspect`、`json`、`dataclasses`、`typing`。下面兩排是其他十四個模組，每一個都只從核心匯入它需要的名稱，彼此之間沒有任何 import。`loom.compaction` 是唯一完全不 import 核心的模組：它只處理文字（交接筆記的格式與驗證）和一個「有 `complete()` 方法的模型」，所以 `ContextMiddleware(policy, compactor)` 的 `compactor` 參數由應用層傳入，這是第 45 章所說的依賴反轉。

| 規則 | 內容 | 由誰保護 |
|---|---|---|
| 規則一 | `loom.core` 不 import 任何 loom 模組 | `ArchitectureTest.test_modules_only_depend_on_core`：core 出現相對 import 就失敗 |
| 規則二 | 其他模組只 import `loom.core`；同層模組不互相 import | 同一個測試：相對 import 的目標必須是 `core`（`__init__.py` 除外） |
| 規則三 | 只用標準函式庫；第三方 SDK 只能出現在最外圈的 adapter（隨書套件沒有） | 同一個測試：絕對 import 的模組，來源路徑不能在 `site-packages` |
| 協作方式 | 透過 `RunContext.state`、擴充事件，或由應用層把 A 的方法當參數傳給 B | 寫在各模組 docstring；例如 tracing 接受 `price` 函式、guardrails 寫 `ctx.state["ask"]` |

模組之間需要協作的地方，v1.0 一共用了三種方式，下表列出套件中實際出現的每一處：

| 協作 | 寫入方 | 讀取方 | 媒介 |
|---|---|---|---|
| taint 判定為 ask，要改走核准 | `TaintMiddleware.wrap_tool` | `ApprovalMiddleware.wrap_tool` | `ctx.state["ask"][tool_call_id]` |
| 寫入時計價 | 應用層把 `CostLedger.price` 傳入 | `TracingMiddleware` | 建構子參數 `price(model, usage)` |
| 摘要模型 | 應用層建立 `Compactor(model)` | `ContextMiddleware` | 建構子參數 `compactor` |
| 根 span、累計成本 | `TracingMiddleware.on_event` | `TracingMiddleware.wrap_model`／`wrap_tool` | `ctx.state["span"]`、`ctx.state["cost"]` |
| 使用者與任務 scope | `AuthMiddleware.before_run` | `AuthMiddleware.effective()` | `ctx.state["user_scopes"]`、`ctx.state["task_scopes"]` |
| 租戶與使用者 | `AuthMiddleware.before_run` | 所有 tool、`MemoryStore`、tracing | `ctx.deps["tenant"]`、`ctx.deps["user_id"]` |
| 重試次數 | `runtime.Runner._call_model` | 核心 `_loop` 寫進 `model_response.attempts` | `ctx.state["attempts"]` |
| 已載入的 tool | `RegistryMiddleware` | 核心 `RunContext.tool_schemas()`／`find_tool()` | `ctx.loaded_tools`＋擴充事件 `tools_loaded` |
| 被取消的 tool call | 核心 `_settle()` 寫 `tool_result(status=cancelled)` | `ApprovalMiddleware.on_event` 取消對應核准單 | 核心事件 |

### B.2.3 三個範例用到的模組與 middleware 順序

| 範例 | 用到的 loom 模組 | middleware 清單（由外到內） | 應用層自己寫的部分 |
|---|---|---|---|
| `support_agent.py` | core、runtime、models、tools、approval、auth、guardrails、tracing、evals | `TracingMiddleware` → `AuthMiddleware` → `GuardrailMiddleware` → `ApprovalMiddleware` | `Backend`（訂單、金流閘道以 `IdempotencyStore` 去重）、`build()`、`stream_once()`、`evaluate()` |
| `coding_agent.py` | core、runtime、models、tools、durable | 情境 A、B、D 沒有 middleware；情境 C 只有應用層的 `CrashAfter` | `Repo`、驗證閘門函式 `tests_passed_after_last_write()`、`Crash`、`CrashAfter` |
| `research_agent.py` | core、runtime、models、memory、registry、mcp、guardrails、approval | `BudgetMiddleware` → `RegistryMiddleware` → `GuardrailMiddleware` → `EvidenceLedger`（應用層） → `TaintMiddleware` → `ApprovalMiddleware` | `EvidenceLedger`（證據帳本，第 44 章）、物流商的 MCP server、`build()` |

這張表也說明了第 45 章的收錄原則：證據帳本只有 research agent 需要，所以留在範例裡，以一個普通的 middleware 掛上去，沒有收進 `loom`。

## B.3 每個模組的職責、公開介面與對應測試

本節的簽名直接從 `code/loom/` 的原始碼整理，型別提示照抄；dataclass 列出欄位與預設值，一般類別列出建構子與公開方法。底線開頭的名稱（例如 `Runner._execute`）依第 23 章的規則是內部實作，不列入。每個模組的表格中，「接法」指它用哪種方式接上核心（實作介面、掛擴充點、產生 Tool，或從外部呼叫 Runner）。

### B.3.1 `loom.core`

| 項目 | 內容 |
|---|---|
| 誕生章 | 第 4 章（v0.1 的 loop、dispatch、配對不變式）、第 23 章（v0.5 的八個核心抽象與四個擴充點） |
| 職責 | 不可變宣告（Agent、Tool、Handoff、Guardrail）、事件與 Session、`to_messages` 投影、配對不變式、intent key 推導、參數驗證、middleware 擴充點、同步參考 Runner |
| 接法 | 核心本身 |
| 測試 | `test_core.CoreTest`（13 個）；依賴規則由 `ArchitectureTest` 保護 |

```text
常數
  STOP_REASONS  = ("end_turn", "tool_use", "max_tokens", "refusal")
  USAGE_KEYS    = ("input_tokens", "cache_read_tokens", "cache_write_tokens", "output_tokens")
  EFFECTS       = ("read", "write", "destructive")
  TOOL_STATUSES = ("ok", "error", "timeout", "cancelled", "unknown")
  CORE_EVENTS   = ("run_started", "user_message", "model_response", "tool_result",
                   "handoff", "guardrail_tripped", "run_finished")

模型介面的資料型別
  @dataclass ToolCall(id: str, name: str, args: dict[str, Any])
  @dataclass ModelResponse(text: str = "", tool_calls: list[ToolCall] = [], stop_reason: str = "end_turn",
                           usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}, raw: dict = {})
             # __post_init__：stop_reason 不在 STOP_REASONS 就丟 ValueError
  class ModelError(Exception)(kind: str, provider: str = "", status: int = 0, retry_after: float = 0.0)
        .retryable -> bool            # kind ∈ {rate_limit, overloaded, server, network}
        .fallback_ok -> bool          # retryable 的種類 ∪ {quota, auth}
        .counts_for_breaker -> bool   # kind ∈ {overloaded, server, network}
  class Model(Protocol)
        complete(messages: list[dict], tools: list[dict] | None = None, system: str = "") -> ModelResponse

四個不可變宣告
  @dataclass(frozen) Tool(name: str, description: str, parameters: dict, fn: Callable,
                          effect: str = "destructive", intent_fields: tuple[str, ...] = (),
                          code_callable: bool = False, timeout: float | None = None, scope: str = "")
        schema() -> dict              # 只有 name、description、parameters
  @dataclass(frozen) Guardrail(name: str, stage: str, check: Callable[..., str | None])   # stage：input｜tool｜output
  @dataclass(frozen) Handoff(target: Agent, description: str)
        .tool_name -> str             # "transfer_to_<target.name>"
        schema() -> dict              # 帶一個必填的 note 參數
  @dataclass(frozen) Agent(name: str, instructions: str, tools: tuple[Tool, ...] = (),
                           handoffs: tuple[Handoff, ...] = (), guardrails: tuple[Guardrail, ...] = (),
                           max_steps: int = 8, verify: Callable[[RunContext], str | None] | None = None)
        .version -> str               # "spec-" + 內容 hash（第 42 章的 AgentSpec 版本）

事件與 Session
  @dataclass(frozen) Event(seq: int, type: str, agent: str, data: dict[str, Any], v: int = 1)
  class ConcurrencyError(Exception)
  class Session(Protocol):  id: str;  load() -> list[Event];  append(event: Event) -> None
  class InMemorySession(session_id: str)
        load() -> list[Event]
        append(event: Event) -> None  # seq 不等於目前長度就丟 ConcurrencyError
  def to_messages(events: list[Event]) -> list[dict]          # 不認得的事件類型略過
  def pending_calls(events: list[Event]) -> list[ToolCall]    # 有 tool call、沒有 tool_result
  def needs_resume(events: list[Event]) -> bool               # 有 pending，或最後一個 run 沒有 run_finished
  def digest(obj: Any, n: int = 12) -> str
  def intent_key(scope_id: str, tool: str, args: dict, fields: tuple[str, ...] = ()) -> str
  def validate_args(schema: dict, args: dict) -> str | None   # 必填、未知參數、基本型別、enum
  async def invoke(tool: Tool, deps: dict, args: dict) -> Any # fn 可以是同步或 async

middleware 擴充點
  @dataclass ModelRequest(system: str, messages: list[dict], tools: list[dict], step: int = 0)
  @dataclass ToolResult(status: str = "ok", content: str = "")
        .is_error -> bool             # status != "ok"
  class StopRun(Exception)(status: str, output: str)
  class Interrupt(Exception)(ticket: str, reason: str = "")
  @dataclass RunContext(run_id: str, agent: Agent, session: Session, deps: dict[str, Any],
                        middleware: list[Middleware] = [], usage: dict[str, int] = USAGE_KEYS 各為 0,
                        loaded_tools: list[Tool] = [], state: dict[str, Any] = {},
                        push: Callable[..., None] = 空函式, hook_errors: list[str] = [])
        emit(type_: str, **data) -> Event   # 先落地 → 通知 on_event（例外記進 hook_errors）→ push("committed")
        find_tool(name: str) -> Tool | None
        find_handoff(name: str) -> Handoff | None
        tool_schemas() -> list[dict]        # 固定 tools → handoffs → 延遲載入（只追加）
  class Middleware
        before_run(ctx: RunContext, user_input: str | None) -> None      # 可同步或 async；resume 時 user_input 為 None
        on_event(ctx: RunContext, event: Event) -> None                  # 同步
        async wrap_model(ctx: RunContext, req: ModelRequest, nxt) -> ModelResponse
        async wrap_tool(ctx: RunContext, tc: ToolCall, nxt) -> ToolResult

執行
  @dataclass RunResult(status: str, output: str, last_agent: Agent, usage: dict[str, int],
                       events: list[Event], tickets: list[str] = [], evidence: str | None = None)
  class Runner(model: Model, middleware: list[Middleware] | tuple = (), *, max_result_chars: int = 4_000)
        run(agent: Agent, user_input: str, session: Session, deps: dict | None = None) -> RunResult    # 同步
        resume(agent: Agent, session: Session, deps: dict | None = None) -> RunResult                  # 同步
        context(agent: Agent, session: Session, deps: dict | None, push=None) -> RunContext
        async arun(agent, user_input, session, deps=None, ctx: RunContext | None = None) -> RunResult
```

讀這份介面時有三個重點。第一，`Runner.run()` 與 `resume()` 在核心是**同步**方法，內部呼叫 `asyncio.run(self.arun(...))`；`loom.runtime.Runner` 把它們改成 coroutine（見 B.3.2），所以兩者的呼叫方式不同，事件序列卻相同。第二，`RunResult.status` 的值是全書統一的 done、unverified、max_steps、max_tokens、budget、loop、blocked、cancelled、timeout、error、refusal，另有兩個非結束狀態 interrupted 與 ignored。第三，`Agent.verify` 是驗證閘門（第 39 章）：Agent 宣告了它，模型說完成時 Runner 會呼叫它取得證據，拿不到證據就記為 unverified。

`loom/__init__.py` 從核心匯出 22 個名稱：`CORE_EVENTS`、`Agent`、`ConcurrencyError`、`Event`、`Guardrail`、`Handoff`、`InMemorySession`、`Interrupt`、`Middleware`、`ModelError`、`ModelRequest`、`ModelResponse`、`RunContext`、`Runner`、`RunResult`、`StopRun`、`Tool`、`ToolCall`、`ToolResult`、`intent_key`、`pending_calls`、`to_messages`。注意 `from loom import Runner` 拿到的是同步的參考 Runner；要用 async runtime 必須寫 `from loom.runtime import Runner`，三個範例都是這樣寫的。

### B.3.2 `loom.runtime`

| 項目 | 內容 |
|---|---|
| 誕生章 | 第 24 章 |
| 職責 | async 執行、兩層事件（核心事件持久化、串流事件不持久化）、唯讀 tool 平行、副作用 shield、取消與逾時、依 `ModelError.retryable` 退避重試、loop guard、虛擬時間 event loop |
| 接法 | 繼承核心 Runner，只覆寫呼叫模型、執行 tool、收尾等內部方法 |
| 測試 | `test_runtime.RuntimeTest`（9 個）；`CoreTest.test_contract_reference_and_async_runner_write_same_events` |

```text
串流事件（dataclass，基底 StreamEvent(run_id, n, t)；type 是類別屬性）
  ModelDelta(step, text)                         type = "model_delta"
  ModelRetry(step, attempt, delay, reason, discard_partial)   type = "model_retry"
  ToolStarted(call_id, name)                     type = "tool_started"
  ToolFinished(call_id, name, status, content)   type = "tool_finished"
  RunCancelling(reason)                          type = "run_cancelling"
  Committed(event)                               type = "committed"   # 一個核心事件已寫進 Session
  def stream_type(name: str, fields: str) -> type
  KINDS: dict[str, type]                         # type 名稱 → 類別

  @dataclass RetryPolicy(max_attempts: int = 4, base: float = 0.5, cap: float = 8.0, seed: int = 7)
        delay(attempt: int, retry_after: float = 0.0) -> float     # full jitter，固定 seed 可重現
  class LoopGuard(window: int = 6, max_repeats: int = 2, max_stale_steps: int = 3)
        inspect(tc: ToolCall) -> str             # ok｜warn｜stop
        no_progress(results: list[str]) -> bool
        reason(verdicts: dict[str, str]) -> str
  class Run(runner, agent, user_input, session, deps)      # 由 Runner.start() 建立
        .result -> RunResult | None
        cancel() -> None
        async stream()                           # 逐一 yield 串流事件；消費者提早離開＝取消 run
  class Runner(core.Runner)(model, middleware=(), *, max_parallel: int = 4, tool_timeout: float = 2.0,
                            model_timeout: float = 10.0, run_timeout: float = 60.0, cancel_grace: float = 2.0,
                            retry: RetryPolicy | None = None, loop_guard: bool = True,
                            max_result_chars: int = 4_000)
        start(agent, user_input, session, deps=None) -> Run        # user_input 為 None 代表 resume；需在 event loop 中呼叫
        async run(agent, user_input, session, deps=None) -> RunResult
        async resume(agent, session, deps=None) -> RunResult
  class VirtualTimeLoop(asyncio.SelectorEventLoop)()
        time() -> float                          # 沒事可做時直接把時鐘撥到下一個計時器
  def run_virtual(coro)                          # 用 VirtualTimeLoop 執行 coroutine，結束時收掉剩下的 task
```

runtime 的契約是「只能改變多快與外面看到什麼，不能改變事實」：同一份劇本在參考 Runner 與 runtime 上寫進 Session 的核心事件序列必須相同，`test_core` 裡的契約測試就是在檢查這件事。模型如果有 `stream()` 方法，runtime 會逐段推 `model_delta`；沒有就退回呼叫 `complete()`。重試只看 `ModelError.retryable`，錯誤怎麼分類屬於 `loom.models`，所以 runtime 不 import models。

### B.3.3 `loom.models`

| 項目 | 內容 |
|---|---|
| 誕生章 | 第 25 章（`StreamingScriptedModel` 與 `fail()` 最早出現在第 24 章的動手做） |
| 職責 | 全書統一的劇本模型、provider adapter 介面、HTTP 錯誤分類、熔斷、fallback、routing、寫入時計價、token 預算 |
| 接法 | 實作 Model 介面（`complete()`，串流版另有 `stream()`）；預算掛 `wrap_model` |
| 測試 | 劇本模型與 `fail()`／`calls()` 由 `test_runtime` 使用；`BudgetMiddleware` 由 `CoreTest.test_budget_is_checked_before_calling_model` 測試；`classify`、`MessagesAdapter`、`CircuitBreaker`、`FallbackChain`、`Router`、`CostLedger` 由 `tests/test_models.py` 測試（整條 fallback 鏈失敗時丟出最後一個 `ModelError`，讓 runtime 依 `retryable` 決定是否稍後重試，和第 24、25 章一致） |

```text
劇本模型
  class ScriptedModel(script: list[ModelResponse | Callable[[list[dict]], ModelResponse]])
        name = "scripted";  calls: list[list[dict]]
        complete(messages: list[dict], tools: list[dict] | None = None, system: str = "") -> ModelResponse
  def call(name: str, call_id: str = "c1", **args) -> ModelResponse          # 一個 tool call
  def calls(text: str, *specs: tuple[str, str, dict]) -> ModelResponse        # 一則回應多個 tool call：(id, name, args)
  def say(text: str) -> ModelResponse
  def fail(err: ModelError) -> Callable[[list[dict]], ModelResponse]           # 劇本步驟：這次呼叫直接失敗
  class StreamingScriptedModel(ScriptedModel)(script, ttft: float = 0.4, chunk_delay: float = 0.05, chunk: int = 8)
        async stream(messages, tools=None, system="")   # yield ("text_delta", str) …，最後 ("stop", ModelResponse)

provider adapter
  @dataclass ModelSpec(name: str, provider: str, tier: str, price: dict[str, float], regions: tuple[str, ...] = ("tw",))
  def classify(provider: str, status: int, body: dict) -> ModelError
        # 429 → rate_limit（insufficient_quota → quota）；503／529 → overloaded；其他 5xx → server；
        # 401／403 → auth；錯誤 type 含 context → context_overflow；其餘 → invalid_request
  class Adapter(spec: ModelSpec, transport: Callable[[dict], tuple[int, dict]])
        complete(messages, tools=None, system="") -> ModelResponse   # build → transport → classify／parse → raw
        build(messages, tools, system) -> dict          # 子類實作
        parse(body: dict) -> ModelResponse              # 子類實作
  class MessagesAdapter(Adapter)                        # 教學版：Messages 式 content block（text、tool_use）

可靠性與路由
  class CircuitBreaker(clock: Callable[[], float], window: int = 6, min_calls: int = 3,
                       threshold: float = 0.5, cooldown: float = 20.0)
        allow() -> bool;  record(ok: bool, err: ModelError | None = None) -> None   # closed／open／half_open
  class FallbackChain(models: list, breakers: dict[str, CircuitBreaker])
        complete(messages, tools=None, system="") -> ModelResponse;  attempts: list[str]
  class Router(adapters: list[Adapter], breakers: dict[str, CircuitBreaker], routes: dict[str, str])
        for_task(task: str, region: str) -> FallbackChain     # 先過濾區域，再依任務選等級

成本與預算
  @dataclass CostLedger(prices: dict[str, dict[str, float]], price_version: str = "demo-2026-10", rows: list[dict] = [])
        price(model: str, usage: dict[str, int]) -> float
        record(tenant: str, model: str, usage: dict[str, int], **tags) -> float
        total(tenant: str | None = None) -> float
  DEMO_PRICES: dict    # scripted、sim-small、sim-large 的示意價格（USD／百萬 tokens），不是任何供應商的報價
  class BudgetMiddleware(Middleware)(max_tokens: int)
        async wrap_model(ctx, req, nxt)        # 累計 usage ≥ max_tokens 就 StopRun("budget", …)；軟上限
```

### B.3.4 `loom.tools`

| 項目 | 內容 |
|---|---|
| 誕生章 | 第 4 章（schema 與 dispatch）、第 5 章（副作用分級、intent_fields、idempotency）、第 7 章（參數型別與 enum） |
| 職責 | 從函式宣告 Tool、tool lint、執行副作用那一端的去重儲存 |
| 接法 | 產生 Tool；執行前驗證（`validate_args`）與 key 推導（`intent_key`）在核心 |
| 測試 | `ToolsTest`（2 個）：裝飾器產生的 schema 與 destructive 預設；`IdempotencyStore` 的 replay 與衝突 |

```text
  PY_TO_JSON: dict[type, str]       # str→string、int→integer、float→number、bool→boolean、dict→object、list→array
  def schema_from(fn: Callable) -> tuple[str, dict]     # docstring 第一行是描述，「名稱: 說明」是參數說明；第一個參數 deps 不進 schema
  def tool(effect: str = "destructive", *, intent: tuple[str, ...] = (), code_callable: bool = False,
           timeout: float | None = None, scope: str = "", enums: dict[str, list] | None = None)
        # 用法：@tool("read") def get_order(deps, order_id: str) -> dict；回傳 Tool
  def lint(t: Tool) -> list[str]    # 描述太短、參數沒有說明或合法值、有副作用卻沒有 intent_fields
  class IdempotencyConflict(Exception)
  @dataclass IdempotencyStore(ttl_seconds: float = 86_400, records: dict = {})
        run(key: str, args: dict, now: float, effect: Callable) -> tuple[Any, bool]   # (結果, 是否為重播)
```

### B.3.5 `loom.context` 與 `loom.compaction`

| 項目 | `loom.context` | `loom.compaction` |
|---|---|---|
| 誕生章 | 第 9 章（依預算組裝）、第 10 章（context 是 log 的純函式） | 第 10 章 |
| 職責 | 從 Session 重播出這一輪的 messages；超過門檻先清舊 tool 輸出、再摘要，兩者都記成擴充事件 | 六段交接筆記的格式、驗收與補強 |
| 接法 | `wrap_model` | 不接核心；`Compactor` 由應用層傳給 `ContextMiddleware` |
| 寫入的擴充事件 | `context_cleared`（placeholders）、`context_compacted`（upto、note） | 無 |
| 測試 | `ContextTest.test_clear_and_compact_are_events_and_view_stays_paired` | `ContextTest.test_check_handoff` |

```text
loom.context
  def estimate_tokens(obj) -> int                  # 粗估：JSON 字元數 ÷ 2
  def build_view(events: list[Event]) -> list[dict]
  @dataclass ContextPolicy(clear_at: int = 3_000, clear_at_least: int = 500, compact_at: int = 6_000,
                           keep_tool_results: int = 2, keep_turns: int = 2,
                           never_clear: tuple[str, ...] = ("update_progress",))
  class ContextMiddleware(Middleware)(policy: ContextPolicy | None = None, compactor=None)
        async wrap_model(ctx, req, nxt)           # 把 req.messages 換成 build_view 的結果

loom.compaction
  SECTIONS = ("目標", "使用者約束", "已完成", "進行中", "下一步", "未解問題")
  SUMMARY_PROMPT: str
  def format_note(sections: dict[str, str]) -> str
  def parse_note(note: str) -> dict[str, str]
  def check_handoff(note: str, must_keep: list[str], max_chars: int = 1_200) -> list[str]
  class Compactor(model, max_chars: int = 1_200)
        summarize(messages: list[dict], constraints: list[str], progress: dict | None = None) -> str
        warnings: list[str]
```

`ContextMiddleware` 摘要時從 `ctx.deps` 讀兩個鍵：`constraints`（必須逐字保留的使用者約束）與 `progress`（程式記帳的進度檔，原文附在筆記後面）。清除只換掉 tool 結果的內容、不刪訊息，所以投影出來的 messages 仍然一一配對。

### B.3.6 `loom.memory`

| 項目 | 內容 |
|---|---|
| 誕生章 | 第 12 章 |
| 職責 | 檔案式長期記憶：模型看到虛擬路徑 `/memories`，harness 依 `deps` 的租戶與使用者對應到實體目錄；`/memories/org` 唯讀；單檔上限與秘密檢查；TTL；刪除權；稽核只記路徑 |
| 接法 | 產生 Tool（`as_tool()`，effect 為 write，intent_fields 為 command 與 path） |
| 測試 | `MemoryTest.test_paths_scopes_and_secrets` |

```text
  VERBS = {"create": "建立", "str_replace": "更新", "delete": "刪除"}
  SECRET: re.Pattern               # 疑似卡號、「密碼」、password
  class MemoryToolError(Exception)
  class MemoryStore(root: Path, max_chars: int = 1_000, ttl_days: dict[str, int] | None = None)   # 預設 {"episodes": 30}
        handle(deps: dict, command: str, path: str, file_text: str = "", old_str: str = "", new_str: str = "") -> str
              # command：view｜create｜str_replace｜delete；deps 必須有 tenant 與 user_id，today 選填
        forget_user(tenant: str, user: str) -> int    # 回傳刪除的檔案數
        as_tool() -> Tool                             # 名稱 "memory"
        audit: list[str]
```

### B.3.7 `loom.registry`

| 項目 | 內容 |
|---|---|
| 誕生章 | 第 13 章 |
| 職責 | 能力目錄與 BM25 tool search；命中的 tool 延遲載入，只往清單尾端追加；載入紀錄寫成 `tools_loaded` 事件，resume 時重建 |
| 接法 | 產生 Tool（`search_tools` meta tool）＋`before_run`（從 log 重建）＋`wrap_tool`（攔下 `search_tools`） |
| 測試 | `RegistryTest.test_search_appends_and_rebuilds_on_resume` |

```text
  def terms(text: str) -> list[str]        # 英數取整字（底線拆開），中文取相鄰兩字
  class ToolRegistry(tools: list[Tool], tags: dict[str, list[str]] | None = None)
        search(query: str, k: int = 3) -> list[str]
        code_callable() -> list[Tool]       # 唯讀且標了 code_callable 的 tool
        search_tool() -> Tool               # 放進 Agent.tools 的 "search_tools"
  class RegistryMiddleware(Middleware)(registry: ToolRegistry, k: int = 3)
        before_run(ctx, user_input)
        async wrap_tool(ctx, tc, nxt)
```

### B.3.8 `loom.mcp`

| 項目 | 內容 |
|---|---|
| 誕生章 | 第 14 章 |
| 職責 | 教學版 MCP：in-process transport 但保留 JSON-RPC 序列化；只實作 `server/discover`、`tools/list`（cursor 分頁）、`tools/call`；每個 request 自帶協定版本。橋接層把遠端 tool 變成 loom Tool：allowlist、名稱前綴、定義 pin，副作用等級由 loom 端決定（不採信 annotations） |
| 接法 | 產生 Tool |
| 測試 | `MCPTest`（2 個）：allowlist、effect、isError 轉成錯誤觀察；pin 偵測定義被改寫 |

```text
  PROTOCOL_VERSION = "2026-07-28"
  META_VERSION = "io.modelcontextprotocol/protocolVersion"
  class RPCError(Exception)(code: int, message: str)
  @dataclass ServerTool(name: str, description: str, input_schema: dict, fn: Callable, annotations: dict[str, bool] = {})
  class MiniMCPServer(name: str, page_size: int = 50)
        tool(name: str, description: str, input_schema: dict, **annotations: bool)   # 註冊用裝飾器
        handle(raw: str) -> str | None      # notification 回傳 None
  class InProcessTransport(server: MiniMCPServer)
        send(raw: str) -> str | None;  wire: list[tuple[str, str | None]]
  class MCPError(Exception)
  class MiniMCPClient(transport: InProcessTransport)
        request(method: str, params: dict | None = None) -> dict
        list_tools() -> list[dict]
        call_tool(name: str, arguments: dict) -> dict
  class ToolExecutionError(Exception)
  def fingerprint(t: dict) -> str
  def mcp_tools(client: MiniMCPClient, prefix: str, allow: dict[str, str],
                pins: dict[str, str] | None = None) -> list[Tool]       # 產生的名稱是 "<prefix>__<遠端名稱>"
```

### B.3.9 `loom.approval`

| 項目 | 內容 |
|---|---|
| 誕生章 | 第 21 章 |
| 職責 | 依 autonomy 等級與風險類別決定 auto／approve／deny（deny-overrides；破壞性類別的硬底線寫在程式裡）；核准單狀態機；hash chain 稽核；以 `Interrupt` 暫停、resume 時依單據狀態執行或回填 |
| 接法 | `wrap_tool`（決策、開單、Interrupt）＋`on_event`（tool call 被取消時取消核准單） |
| 寫入的擴充事件 | `approval_requested`（ticket、call_id、tool、hash、rule、approvers） |
| 測試 | `ApprovalTest`（3 個）：引擎決策；核准台狀態機、職責分離與稽核鏈；interrupt／resume 只執行一次 |

```text
常數
  STRICT     = {"auto": 0, "approve": 1, "deny": 2}
  BASELINE   = {0: "deny", 1: "deny", 2: "deny", 3: "approve", 4: "auto", 5: "auto"}   # autonomy 等級 → 預設效果
  KINDS      = ("read", "write", "money", "destructive")
  TRANSITIONS = {"PENDING": {"APPROVED", "REJECTED", "EXPIRED", "CANCELLED"}, "APPROVED": {"EXECUTED", "FAILED"}}

  @dataclass(frozen) ActionRequest(tool: str, args: dict, kind: str, facts: dict)
  @dataclass(frozen) Rule(id: str, when: Callable[[ActionRequest], bool], effect: str, reason: str,
                          approvers: tuple[str, ...] = ("客服",), timeout_s: int = 14_400, on_timeout: str = "deny")
  @dataclass(frozen) Decision(effect: str, rule: str, reasons: tuple[str, ...], approvers: tuple[str, ...] = (),
                              timeout_s: int = 0, on_timeout: str = "deny", policy_version: str = "")
  class PolicyEngine(actions: dict[str, tuple[int, str]], rules: list[Rule] = (), version: str = "v1")
        decide(tool: str, args: dict, facts: dict | None = None) -> Decision     # 未登記的動作 → default-deny
  def args_hash(tool: str, args: dict) -> str
  class AuditLog()
        append(ts: int, event: str, ticket: str, actor: str, **detail) -> None
        verify() -> int | None              # 第一筆對不上的 seq；None 代表鏈完好
  @dataclass Ticket(id: str, tool: str, args: dict, hash: str, kind: str, decision: Decision, opened: int,
                    requester: str, state: str = "PENDING", by: str = "")
  class ApprovalDesk(clock: Callable[[], int], audit: AuditLog | None = None)
        open(tid: str, tool: str, args: dict, kind: str, d: Decision, requester: str) -> Ticket
        tick() -> None                      # 逾時處理；破壞性類別絕不因逾時自動核准
        respond(tid: str, actor: str, role: str, verdict: str, seen_hash: str) -> str
              # verdict 為 "approved" 才核准；發起者與 agent 不能核准、角色要在關卡內、hash 要相符
        finish(tid: str, ok: bool) -> None
        cancel(tid: str) -> None
  class ApprovalMiddleware(Middleware)(engine: PolicyEngine, desk: ApprovalDesk,
                                       facts: Callable[[ctx, tc], dict] = lambda ctx, tc: {},
                                       ask_approvers: tuple[str, ...] = ("客服",))
        async wrap_tool(ctx, tc, nxt)
        on_event(ctx, event)
```

核准單 id 就是 `intent_key(session.id, tool, args, tool.intent_fields)`，和核心推導的 idempotency key 同源，所以重試或重啟都不會開第二張單，下游也以同一把 key 去重。`ApprovalMiddleware` 讀 `ctx.state["ask"]`：taint 判定為 ask 而政策原本是 auto 時，升級成 approve（規則名稱 `guardrails-ask`）。

### B.3.10 `loom.durable`

| 項目 | 內容 |
|---|---|
| 誕生章 | 第 22 章 |
| 職責 | 以 append-only 的 JSONL 檔實作 Session（compare-and-set、回傳前 fsync、別的 worker 寫過就重讀）；讀取時以 upcaster 就地升級舊版事件；從日誌重播出 run 的狀態 |
| 接法 | 實作 Session 介面；resume 本身由 Runner 負責 |
| 測試 | `DurableTest.test_file_session_cas_upcast_and_replay` |

```text
  UPCASTERS: dict[tuple[str, int], Callable[[dict], dict]]
  def upcaster(type_: str, from_v: int)      # 註冊用裝飾器；內建 ("tool_result", 1)：由 is_error 推出 status
  class FileSession(path: Path, session_id: str | None = None)   # id 預設為檔名主幹
        load() -> list[Event]
        append(event: Event) -> None
  @dataclass RunState(last_status: str | None, needs_resume: bool, pending: list[str], open_tickets: list[str],
                      usage: dict[str, int] = {}, runs: int = 0)
  def replay(events: list[Event]) -> RunState
```

### B.3.11 `loom.guardrails`

| 項目 | 內容 |
|---|---|
| 誕生章 | 第 23 章（宣告式 guardrail 的執行器）、第 31 章（lethal trifecta 與 context 層級污染）、第 32 章（capability、Label、ToolSpec） |
| 職責 | 執行 Agent 上宣告的 input／tool／output guardrail；依序做能力、機密性、完整性三項檢查，結果是 deny／ask／allow |
| 接法 | `GuardrailMiddleware`：`before_run`＋`wrap_tool`＋`wrap_model`；`TaintMiddleware`：`wrap_tool` |
| 測試 | `GuardrailsTest`（2 個）：檢查順序與標記合併；從 log 算出 context 污染。`GuardrailMiddleware` 由 `CoreTest.test_input_guardrail_blocks_before_persisting` 測試 |

```text
  @dataclass(frozen) Label(sources: frozenset[str] = frozenset(), readers: frozenset[str] = frozenset({"*"}))
        .untrusted -> bool                  # 任一來源以 "untrusted:" 開頭
        join(other: Label) -> Label         # 來源取聯集、讀者取交集（"*" 代表不限）
  def lab(*sources: str, readers: tuple[str, ...] = ("*",)) -> Label
  @dataclass ToolSpec(capability: str, integrity_args: tuple[str, ...] = (), recipient_arg: str | None = None,
                      labels: Label | Callable[[dict], Label] = Label(), inherits: bool = False)
  def check(spec: ToolSpec, grants: set[str], args: dict[str, tuple[Any, Label]]) -> tuple[str, str]
  class TaintMiddleware(Middleware)(specs: dict[str, ToolSpec], grants: Callable[[ctx], set[str]])
        context_label(ctx) -> Label         # 依序折疊 Session 中每個成功 tool 結果的標記
        async wrap_tool(ctx, tc, nxt)       # deny 回填錯誤；ask 寫 ctx.state["ask"][tc.id]
  class GuardrailMiddleware(Middleware)()
        before_run(ctx, user_input)         # input：攔下就 StopRun("blocked")，user_message 不落地
        async wrap_tool(ctx, tc, nxt)       # tool：回填錯誤，不中斷 run
        async wrap_model(ctx, req, nxt)     # output：沒有 tool call 的最終回覆才檢查
```

Guardrail 的 `check` 呼叫慣例是 `check(deps, 內容)`：input 階段傳使用者輸入、tool 階段傳 `ToolCall`、output 階段傳回覆文字；回傳 None 代表通過，回傳字串就是攔下的理由。

### B.3.12 `loom.auth`

| 項目 | 內容 |
|---|---|
| 誕生章 | 第 33 章（token、exchange、有效權限）、第 42 章（租戶只從驗證過的 session 注入） |
| 職責 | 簽發與驗證短效 token（HMAC，教學用）；token exchange 只能縮小 scope；把租戶與使用者注入 `deps`；每次 tool call 依目前的 agent 計算有效權限；擋下模型填寫的身分參數 |
| 接法 | `before_run`＋`wrap_tool` |
| 測試 | `AuthTest`（2 個）：簽章、期限、audience、exchange；租戶注入與身分參數阻擋 |

```text
  FORBIDDEN_ARGS = frozenset({"tenant", "tenant_id", "user_id", "as_user", "org_id"})
  class TokenError(Exception)
  class AuthServer(issuer: str, key: bytes, clock: Callable[[], int])
        issue(sub: str, tenant: str, scope: str, aud: str, ttl: int = 300, **extra) -> str
        verify(token: str, audience: str, leeway: int = 30) -> dict      # 簽章、issuer、期限、audience
        exchange(subject_token: str, its_aud: str, actor: str, audience: str, scope: str) -> str
              # 壽命取 min(60 秒, 原 token 剩餘時間)，claims 中以 act 記下行動者
  class AuthMiddleware(Middleware)(auth: AuthServer, audience: str, agent_scopes: dict[str, set[str]])
        before_run(ctx, user_input)          # 驗 ctx.deps["token"]；失敗 StopRun("blocked")
        effective(ctx) -> set[str]           # 使用者 scope ∩ 目前 agent 的 scope ∩ 任務範圍
        async wrap_tool(ctx, tc, nxt)        # 身分參數或 insufficient_scope 都回填錯誤
```

任務範圍來自 `ctx.deps["task_scope"]`；沒有提供時等於 token 的 scope。

### B.3.13 `loom.tracing`

| 項目 | 內容 |
|---|---|
| 誕生章 | 第 29 章 |
| 職責 | span 樹（`invoke_agent` → `chat`／`execute_tool`）；span status 只記技術成敗，業務結果放 `bluebird.*` 屬性；匯出前遮蔽 PII；使用者 id 以 HMAC 假名化；寫入時計價並記下價目表版本；內容擷取預設關閉 |
| 接法 | `on_event`（根 span 的開與關、span event）＋`wrap_model`＋`wrap_tool` |
| 測試 | `TracingTest.test_span_tree_status_and_redaction` |

```text
  EMAIL、TW_MOBILE、CARD: re.Pattern
  def redact(value: Any) -> Any            # 遞迴處理 str／list／dict
  def pseudonym(user_id: str, key: bytes) -> str     # "u_" + HMAC 前 10 碼
  @dataclass Span(name: str, trace_id: str, span_id: str, parent_id: str | None, start: int, end: int = 0,
                  attributes: dict = {}, events: list[dict] = [], status: str = "UNSET")   # UNSET｜OK｜ERROR
  class Tracer(clock: Callable[[], int], processors: list[Callable[[Span], Span]] | None = None)   # 預設 [redaction]
        start(name: str, parent: Span | None = None, **attrs) -> Span
        end(sp: Span, error: str | None = None) -> None
        static redaction(sp: Span) -> Span
        tree(trace_id: str | None = None) -> list[str]
        finished: list[Span]
  class TracingMiddleware(Middleware)(tracer: Tracer, price: Callable[[str, dict], float], pseudonym_key: bytes,
                                      model_name: str = "scripted", price_version: str = "demo-2026-10",
                                      capture_content: bool = False)
        on_event(ctx, event);  async wrap_model(ctx, req, nxt);  async wrap_tool(ctx, tc, nxt)
```

根 span 的 `bluebird.tenant.id`、`bluebird.user.pseudonym`、`bluebird.cost.usd` 在 `run_finished` 時才寫入，因為租戶是在 `before_run` 才由 auth 注入的（第 45 章 45.7 節）。`execute_tool` 收到 `Interrupt` 時記 `bluebird.tool.status=interrupted`，span status 仍是 OK。

### B.3.14 `loom.evals`

| 項目 | 內容 |
|---|---|
| 誕生章 | 第 27 章（第 28 章的 benchmark harness 是它的原型延伸） |
| 職責 | 任務集、每次試驗建立全新環境、outcome grader 與宣稱檢查、pass@k 與 pass^k |
| 接法 | 從外部呼叫 Runner，只依賴核心的 `RunResult` |
| 測試 | `EvalsTest.test_pass_hat_k_and_suite` |

```text
  @dataclass Task(id: str, prompt: str, script: Callable[[random.Random], list],
                  check: Callable[[env, RunResult], list[str]], setup: Callable[[], Any] = lambda: None,
                  tags: tuple[str, ...] = ())
  @dataclass Trial(task: str, n: int, ok: bool, failures: list[str], status: str, usage: dict[str, int] = {})
  def claim(text: str, keywords: tuple[str, ...], fact: bool, what: str) -> list[str]
  def run_suite(tasks: list[Task], harness: Callable[[env, list], Callable[[str], RunResult]],
                trials: int = 4, seed: int = 27) -> list[Trial]
        # status 不是 done 或 interrupted 也算失敗
  def pass_at_k(n: int, c: int, k: int) -> float
  def pass_hat_k(n: int, c: int, k: int) -> float
  def report(results: list[Trial], k: int) -> dict[str, dict[str, float]]   # 每題一列，另加 "_mean"
```

`run_suite` 不知道 Runner 是同步還是 async、用哪個模型，它只呼叫 `harness(env, script)` 得到 `execute(prompt) -> RunResult`。客服範例的 `evaluate()` 就是在 `harness` 裡用 `run_virtual` 包住 async runtime。

### B.3.15 模組總表

| 模組 | 誕生章 | 接法 | 寫入的事件 | 測試（數量） |
|---|---|---|---|---|
| `loom.core` | 4、23 | 核心 | 七種核心事件 | `test_core`（13） |
| `loom.runtime` | 24 | 繼承 Runner | 同核心；另推串流事件 | `test_runtime`（9）＋契約測試 |
| `loom.models` | 24、25 | 實作 Model；預算掛 `wrap_model` | 無（`BudgetMiddleware` 以 `StopRun` 結束） | 間接（見 B.3.3） |
| `loom.tools` | 4、5、7 | 產生 Tool | 無 | `ToolsTest`（2） |
| `loom.context` | 9、10 | `wrap_model` | `context_cleared`、`context_compacted` | `ContextTest`（1） |
| `loom.compaction` | 10 | 由應用層注入 | 無 | `ContextTest`（1） |
| `loom.memory` | 12 | 產生 Tool | 無（稽核在 `MemoryStore.audit`） | `MemoryTest`（1） |
| `loom.registry` | 13 | 產生 Tool＋`before_run`＋`wrap_tool` | `tools_loaded` | `RegistryTest`（1） |
| `loom.mcp` | 14 | 產生 Tool | 無 | `MCPTest`（2） |
| `loom.approval` | 21 | `wrap_tool`＋`on_event` | `approval_requested` | `ApprovalTest`（3） |
| `loom.durable` | 22 | 實作 Session | 無（升級讀到的舊事件） | `DurableTest`（1） |
| `loom.guardrails` | 23、31、32 | `before_run`＋`wrap_tool`＋`wrap_model` | `guardrail_tripped` | `GuardrailsTest`（2）＋`CoreTest`（1） |
| `loom.auth` | 33、42 | `before_run`＋`wrap_tool` | 無 | `AuthTest`（2） |
| `loom.tracing` | 29 | `on_event`＋`wrap_model`＋`wrap_tool` | 無（產生 span） | `TracingTest`（1） |
| `loom.evals` | 27 | 從外部呼叫 Runner | 無 | `EvalsTest`（1） |

`guardrail_tripped` 還有兩個寫入者：runtime 的 loop guard（`guardrail="loop_guard"`）與 `TaintMiddleware`（`guardrail="taint"`）。

## B.4 全書各章「動手做」程式索引

下表列出第 1 到 46 章「動手做」中的每一組程式。「主要類別與函式」只列該章新定義的重點名稱，省略每段開頭共用的 `ToolCall`、`ModelResponse`、`ScriptedModel`、`call`、`say`。「v1.0 收錄」欄的意思：**是**＝該章的機制以同名或改寫後的形式收進隨書套件；**部分**＝只收了其中一部分，括號註明收了什麼；**否**＝沒有收錄，B.7 說明原因與掛接點。所有段落都可以單獨執行，B.1.2 說明執行方式。

| 章 | 節 | 程式在做什麼 | 主要類別與函式 | 對應模組 | v1.0 收錄 |
|---|---|---|---|---|---|
| 1 | 1.11 | 同一則退款客訴，用單次呼叫、固定 workflow、agent loop 三種做法處理，用同一套規則評分 | `single_call`、`fixed_workflow`、`agent_loop`、`grade` | 無（概念示範） | 否 |
| 2 | 2.12 | 十個元件各用幾行實作，一次請求依序流經它們並寫追蹤 | `route`、`build_context`、`check_action`、`execute`、`run_agent`、`handle_request` | 對應全書架構，無單一模組 | 否 |
| 3 | 3.12 | token、成本、延遲估算器，模擬 prefix cache 命中與 TTL，比較四種情境 | `estimate_tokens`、`Pricing`、`Latency`、`PrefixCache`、`run_session` | `loom.context`、`loom.models` | 部分（`estimate_tokens` 的粗估規則、`CostLedger` 的計價） |
| 4 | 4.9 | 從 30 行裸 loop 長到約 100 行的 `loom` v0.1，重現並修好三個事故 | `Tool`、`Agent`、`RunResult`、`dispatch`、`MeteredModel` | `loom.core` | 是（改寫成 v0.5／v1.0 的 Runner） |
| 5 | 5.10 | 重構青鳥 tools，比較設計差與設計好的 tool 在成功率、步數、token 上的差異 | `Tool`（effect、intent_fields）、`needs_approval`、`bad_tools`、`good_tools` | `loom.tools`、`loom.core` | 是（`needs_approval` 的角色由 `loom.approval` 承接） |
| 6 | 6.12 | prompt 模組與組裝器、店家設定驗證、lint、行為檢查與上線閘門、ablation | `Module`、`assemble`、`PromptBuild`、`lint`、`regress`、`gate` | 無（v1.0 的 `Agent.instructions` 是單一字串） | 否 |
| 7 | 7.10 | 小型 JSON Schema 驗證器與 validate-and-repair 迴圈；串流的部分 JSON 解析 | `validate`、`validate_one_of`、`extract_json`、`structured_call`、`parse_partial` | `loom.schema` | 部分（核心 `validate_args` 只涵蓋必填、未知參數、基本型別與 enum；修復迴圈與部分解析未收錄） |
| 8 | 8.8 | 同一題跑七種推理與規劃設定（ReAct、critic、plan-execute、tree search 等），各 300 次 | `react`、`critic`、`plan_execute`、`tree_search`、`trial` | 無 | 否 |
| 9 | 9.9 | 依預算分層組裝 context，在層邊界放 breakpoint，模擬 prefix cache | `ContextBuilder`、`Segment`、`BudgetExceeded`、`PrefixCache` | `loom.context` | 部分（依預算組裝改為 `ContextMiddleware`；breakpoint 與 workspace handle 未收錄） |
| 10 | 10.10 | append-only session log、重播成 context 的純函式、兩道防線的清除與摘要 | `SessionLog`、`build_view`、`ContextPolicy`、`ContextManager` | `loom.context`、`loom.compaction`、`loom.core`（Session） | 是 |
| 11 | 11.10 | BM25、雜湊向量、RRF 融合的 hybrid 檢索與評估；包成 `search_kb` 的 agentic RAG | `BM25`、`VectorIndex`、`rrf`、`recall_at_k`、`ndcg_at_k`、`search_kb` | `loom.retrieval` | 否 |
| 12 | 12.11 | 檔案式 memory tool，跨六個 session 記住使用者偏好，含刪除權 | `MemoryTool`、`MemoryToolError`、`forget_user` | `loom.memory` | 是（改名為 `MemoryStore`） |
| 13 | 13.9 | tool registry 與 BM25 搜尋、延遲載入；skills 三層揭露；受限的 code-as-action | `ToolRegistry`、`terms`、`SkillLibrary`、`run_restricted` | `loom.registry` | 部分（registry、搜尋與延遲載入；skills 與受限執行器未收錄） |
| 14 | 14.12 | 教學版 MCP server、in-process transport、client，以及接上 loom 的橋接層 | `MiniMCPServer`、`InProcessTransport`、`MiniMCPClient`、`mcp_tools` | `loom.mcp` | 是（v1.0 只保留 tools 相關方法） |
| 15 | 15.9 | A2A 風格 task 狀態機（含兩種中斷態）；AG-UI 風格事件串流與前端 fold | `TaskStore`、`ClaimAgentServer`、`resolve_interrupt`、`to_sse`、`from_sse`、`FrontendView` | `loom.a2a` | 否 |
| 16 | 16.10 | 模擬物流商後台，比較 accessibility tree 與截圖座標兩種觀察方式 | `Portal`、`BrowserAgent`、`policy` | `loom.browser` | 否 |
| 17 | 17.8 | 概念版受限執行器：暫存目錄、乾淨環境變數、rlimit、wall clock 逾時，並回報哪些限制生效 | `Limits`、`ExecResult`、`run_untrusted` | `loom.sandbox` | 否 |
| 18 | 18.11 | 青鳥客服 v2 的混合 pipeline：guardrail 與 router 平行、物流 chain、需核准的退款 agent | `shipping_workflow`、`refund_agent`、`complaint_draft`、`route`、`handle` | `loom.workflows` | 否 |
| 19 | 19.10 | 約 130 行的 graph runtime：super-step、checkpoint、動態 interrupt、time travel | `Graph`、`Runtime`、`Saver`、`NodeContext`、`build_refund_graph` | `loom.graph` | 否 |
| 20 | 20.12 | orchestrator–subagent 的 token 倍數；三種 handoff 策略；分支隔離與三方合併 | `Metered`、`AgentSpec`、`HandoffRunner`、`run_parallel`、`merge3` | `loom.agents`、`loom.core`（Handoff） | 部分（handoff 升格為核心的 `Handoff`；其餘未收錄） |
| 21 | 21.11 | policy engine、核准台與 hash chain 稽核；把核准接進 loop 的 interrupt／resume | `PolicyEngine`、`Rule`、`Decision`、`AuditLog`、`ApprovalDesk`、`decide` | `loom.approval` | 是（改寫成 `wrap_tool` middleware） |
| 22 | 22.10 | 事件日誌 runner：crash 後重播、idempotency key、429 退避；佇列、lease 與排程器 | `EventLog`、`DurableRunner`、`NonDeterminismError`、`TaskQueue`、`Scheduler` | `loom.durable`、`loom.runtime` | 部分（事件日誌改為 `FileSession`＋`replay`，resume 由 Runner 負責；佇列與排程器未收錄） |
| 23 | 23.12 | `loom` v0.5 核心：四個宣告、Event 與 Session、middleware 鏈；分流、handoff、攔截情境 | `Agent`、`Tool`、`Handoff`、`Guardrail`、`InMemorySession`、`RunContext`、`Runner`、`LoggingMiddleware`、`BudgetMiddleware`、`GuardrailMiddleware` | `loom.core`、`loom.models`、`loom.guardrails` | 是（`LoggingMiddleware` 由 `loom.tracing` 取代） |
| 24 | 24.10 | `loom.runtime`：虛擬時間、串流、平行 tool、取消、重試、loop guard，重演雙 11 | `VirtualTimeLoop`、`StreamingScriptedModel`、`Cut`、`fail`、`RetryPolicy`、`LoopGuard`、`Runner`、`Run` | `loom.runtime`、`loom.models` | 是（`Cut` 斷線劇本未收錄） |
| 25 | 25.10 | `loom.models`：錯誤分類、熔斷、兩種 adapter、fallback、router、成本帳本，重演 provider 過載 | `classify`、`ModelSpec`、`Breaker`、`Adapter`、`MessagesAdapter`、`ItemsAdapter`、`FallbackChain`、`Router`、`CostLedger` | `loom.models` | 是（`Breaker` 改名為 `CircuitBreaker`；只保留 `MessagesAdapter`） |
| 26 | 26.11 | 加權決策矩陣與敏感度；中立 tool 定義匯出成各家格式；跨框架契約測試 | `score`、`rank`、`flips`、`strictify`、`to_openai_responses`、`to_anthropic`、`to_gemini`、`to_mcp`、`VendorAgent` | `loom.tools`（exporter） | 否（契約測試的作法沿用在 `test_core` 的契約測試） |
| 27 | 27.9 | eval harness 與 pass^3；LLM-as-judge 的位置偏誤與 kappa；配對 bootstrap；error analysis | `Env`、`Task`、`run_suite`、`grade`、`pass_hat_k`、`judge_pair`、`kappa`、`paired_bootstrap`、`detect` | `loom.evals` | 部分（任務、run_suite、pass@k／pass^k、宣稱檢查；judge 與統計檢定未收錄） |
| 28 | 28.12 | 三種污染偵測；版本化題庫、隔離環境、信賴區間的小型 benchmark harness | `ngrams`、`overlap`、`completion_probe`、`make_tasks`、`manifest_hash`、`bootstrap_ci` | `loom.evals` | 否 |
| 29 | 29.9 | `loom.tracing`：contextvars 管理的 span 樹、遮蔽、HMAC 假名化、寫入時計價 | `Clock`、`Span`、`Tracer`、`redact`、`pseudonym`、`cost_usd`、`TracedAgent` | `loom.tracing` | 是（改為 middleware、明確的 `start`／`end`，計價改由注入的 `price` 函式負責） |
| 30 | 30.10 | 依 eval 回饋搜尋 prompt；新舊模型的 harness ablation；成本與延遲的帕雷托前緣 | `build_prompt`、`reflect`、`run_trial`、`run_config`、`dominates`、`choose` | 無 | 否 |
| 31 | 31.14 | lethal trifecta 靜態檢查器；執行期追蹤 context 污染的守門員 | `analyze`、`walk`、`TaintGuard` | `loom.guardrails` | 部分（執行期檢查演進為 `TaintMiddleware`；靜態檢查器未收錄） |
| 32 | 32.12 | capability 權限與 taint tracking：能力、機密性、完整性三項檢查 | `Label`、`lab`、`ToolSpec`、`check`、`GuardedAgent` | `loom.guardrails` | 是（`GuardedAgent` 改為 `TaintMiddleware`） |
| 33 | 33.10 | 授權 middleware：短效 token、exchange、scope、租戶、step-up；hash-chained 稽核日誌 | `AuthServer`、`AuthMiddleware`、`TokenError`、`AuditLog`、`rechain` | `loom.auth`、`loom.approval`（稽核鏈） | 部分（token、exchange、租戶注入、有效權限；step-up 未收錄；hash chain 在 `approval.AuditLog`） |
| 34 | 34.10 | 只讀 trace 的 failure 偵測器（重複、未驗證完成、不存在的 tool）；burn rate 監控 | `detect_repeats`、`detect_unknown_tool`、`detect_unverified_done`、`BurnRateMonitor` | 無（重複偵測的線上版是 runtime 的 `LoopGuard`） | 否 |
| 35 | 35.14 | 從 trace 量 workload profile；容量與成本估算器與敏感度分析 | `MeteredModel`、`run_session`、`Assumptions`、`Prices`、`poisson_quantile`、`estimate` | 無 | 否 |
| 36 | 36.13 | 租戶限流、model gateway 的 fallback、canary 發布控制 | `TokenBucket`、`Limiter`、`ModelGateway`、`CanaryController`、`rollout` | `loom.models`、`loom.evals` 往平台層的延伸 | 否 |
| 37 | 37.11 | 回饋事件經同意與遮蔽後變成 eval 案例；單位經濟試算 | `redact`、`EvalCase`、`build_cases`、`Workload`、`cost_per_conversation` | 無 | 否 |
| 38 | 38.12 | 資料化的 stage gate 評估器：最小樣本、Wilson 區間、未量測視為未達標 | `Criterion`、`Obs`、`wilson`、`pass_hat_k`、`evaluate` | 無 | 否 |
| 39 | 39.11 | 唯一匹配的 edit 與 all-or-nothing patch；權限模式與測試驗證閘門；coding agent 的分階段 compaction | `str_replace`、`apply_patch`、`decide`、`run_tests`、`clear_tool_outputs`、`safe_cut`、`ThrashingError` | `loom.core`（驗證閘門）、`examples/coding_agent.py` | 部分（驗證閘門成為 `Agent.verify` 與 unverified 狀態；編輯工具與權限模式未收錄） |
| 40 | 40.12 | 完整 research 流水線：subagent fan-out、去重、引用支持檢查，量測 fan-out 與覆蓋率 | `search`、`run_subagent`、`canonical`、`supports`、`research` | `loom.retrieval`、`loom.agents`、`examples/research_agent.py` | 否 |
| 41 | 41.11 | 退款 SOP 狀態機與 τ-bench 風格的 pass^k，比較三種 guard 模式 | `Env`、`PolicyGuard`、`agent_brain`、`user_brain`、`episode`、`pass_hat_k` | `loom.guardrails`、`loom.evals` 的應用 | 否 |
| 42 | 42.17 | 平台容量估算；租戶隔離的 tool gateway；加權公平配額 | `Tier`、`peak`、`AgentSpec`、`compile_spec`、`ToolGateway`、`simulate` | `loom.core`（`Agent.version`）、`loom.auth` | 部分（AgentSpec 的內容 hash 成為 `Agent.version`；租戶只從 token 注入；gateway 與配額未收錄） |
| 43 | 43.16 | sandbox pool 的離散事件模擬；background coding 任務的生命週期狀態機 | `Config`、`Stats`、`simulate`、`Task`、`guard`、`harness`、`drive` | 無 | 否 |
| 44 | 44.15 | 以 sqlite3 實作唯讀守門、權限改寫與查詢計畫檢查；證據帳本與數字追溯 | `build_db`、`Principal`、`SafeSQL`、`QueryRejected`、`Ledger`、`verify` | `examples/research_agent.py`（`EvidenceLedger`） | 部分（證據帳本以應用層 middleware 出現在 research 範例；`SafeSQL` 未收錄） |
| 45 | 45.13 | 約 300 行的縮小版整合：核心、auth、approval、tracing、eval 跑完 1,280 元退款；以及隨書套件的執行輸出 | `Tool`、`Agent`、`Session`、`Ctx`、`Middleware`、`Runner`、`Auth`、`Desk`、`Approval`、`Tracing`、`Gateway` | 整個隨書套件 | 是（縮小版是套件的教學摘要） |
| 46 | 46.13 | 技術雷達分類；harness 元件的 ablation 排程與承重判定 | `Candidate`、`paired_ci`、`classify`、`Component`、`evaluate`、`due` | 無 | 否 |

讀這張表時有一個規律：第 4、5、9–14、21–25、27、29、32、33 章的程式是「給 loom 加上 X 模組」的原型，大多收進了 v1.0；第 15–20 章的協定與 orchestration、第 30、34–38 章的營運工具，以及第 39–44 章的案例模擬，都建在 Runner 之上或屬於平台層，留在章節裡當作設計參考。章節中的版本和 v1.0 的同名類別不一定完全相同：章節版為了單獨執行，常常內嵌一份縮小的 loop，欄位也可能較少；要用的時候以 B.3 的介面為準。

## B.5 版本演進：v0.1 → v0.5 → v1.0

依全書的版本規則，`loom` 只有三個版本號：第 4 章的 v0.1、第 23–25 章的 v0.5、第 45 章的 v1.0。其他章節不給版本號，而是寫成「給 loom 加上 X 模組」。

```text
 第 4 章            第 5–22 章（給 loom 加上模組）            第 23–25 章             第 26–44 章            第 45 章
 v0.1 ─────────────► tools、schema、context、compaction ──► v0.5 ───────────────► evals、tracing、 ──────► v1.0
 約 100 行          retrieval、memory、registry、mcp、        core＋runtime＋models   guardrails、auth        15 個模組
 一個 Agent 類別    a2a、browser、sandbox、workflows、        loom.compat 相容層     等模組陸續接上          56 個測試
                    graph、agents、approval、durable          四個擴充點             v0.5 核心               移除 loom.compat
```

這張圖由左往右讀。v0.1 是一個持有模型與 messages 的 `Agent` 類別，loop 的所有保證都寫在一個方法裡。第 5 到 22 章各自為 loom 加上一個模組，但那時還沒有擴充點，每個模組都是直接改 loop 或包住 loop。v0.5 把共用部分抽成核心抽象與四個擴充點，並保留 `loom.compat` 讓舊程式繼續跑。v0.5 之後的模組（evals、tracing、guardrails、auth）一開始就照擴充點設計。v1.0 把所有模組都改成只透過擴充點或介面接上核心，並移除相容層。

| 面向 | v0.1（第 4 章） | v0.5（第 23–25 章） | v1.0（第 45 章） |
|---|---|---|---|
| 程式規模 | 約 100 行，一個類別 | 核心約 220 行，加上 runtime 與 models | 15 個模組約 2,400 行，56 個測試 |
| 核心形狀 | `Agent` 同時持有 model 與 messages，有 `run()` 方法 | Agent 是不可變設定，由 Runner 執行，狀態在 Session | 同 v0.5；`Agent` 多了 `verify` 與內容 hash 的 `version` |
| 事實來源 | 記憶體裡的 messages | Session 事件（但核准、durable 各有一份狀態） | 只有 Session 事件；擴充事件也寫進同一份 log |
| 執行契約 | `Agent.run()` | 同步參考 Runner＋async runtime，事件序列相同 | 同上，async runtime 直接繼承參考 Runner |
| 擴充方式 | 改 loop 本身 | 四個擴充點，但部分模組仍自帶 loop | 所有模組只走四個擴充點，或實作 Session／Model 介面 |
| 停止原因 | end_turn、max steps、budget、max_tokens、重複呼叫 | 加上 refusal；狀態名稱全書統一 | 加上 unverified（驗證閘門）、interrupted 與 ignored 進入核心 |
| 相容層 | 無 | `loom.compat` 轉換舊名稱與舊呼叫方式 | 移除；改用事件升級（upcaster）處理舊資料 |
| 驗證 | 五個情境的 assert | 各章的情境測試 | 契約測試、依賴規則測試、三個端到端範例 |

### B.5.1 各版本新增了什麼

**v0.1（第 4 章）** 在 30 行的裸 loop 上依序加上：schema 參數驗證（必填與未知參數）、例外回填成觀察、結果截斷、token 預算、max_tokens 不執行半截的 tool call、兩段式重複偵測（先提醒、再停止）、步數上限、`RunResult`，以及最重要的保證：不論怎麼停止，每個 tool call 都有對應的結果。它刻意沒做的事也很明確：沒有平行與取消、沒有模型重試、messages 只在記憶體裡、沒有權限控制。

**v0.5（第 23–25 章）** 是一次不相容的重構：

| 章 | 新增 | 留到 v1.0 的形狀 |
|---|---|---|
| 23 | 八個核心抽象（Agent、Tool、Handoff、Guardrail＋Runner、Session、Event，外加 middleware）；四個擴充點；七種核心事件；`deps` 依賴注入；handoff 是特殊 tool call；Tool 的 `effect`、`intent_fields`、`code_callable` 成為正式欄位；公開介面規則；`loom.compat` | `loom.core`；`BudgetMiddleware` 移到 `loom.models`、`GuardrailMiddleware` 移到 `loom.guardrails` |
| 24 | async Runner、兩層事件、唯讀平行與副作用依序、shield、單次與整體逾時、取消收尾、`tool_result.status`、`model_response.attempts`、退避重試、滑動視窗 loop guard、虛擬時間測試 | `loom.runtime` |
| 25 | 正規化的 `ModelResponse`（四種 stop_reason、四個互斥的 usage 桶、`raw`）、`ModelError` 分類、熔斷、adapter、fallback chain、router、成本帳本 | `loom.models`；`ModelError` 的型別移到核心 |

**v1.0（第 45 章）** 沒有增加核心事件，主要的改變是「收斂」：

| v0.5 的寫法 | v1.0 的寫法 | 原因 |
|---|---|---|
| `wrap_model`／`wrap_tool` 是同步函式 | 一律是 coroutine；`before_run` 可同步可 async | 參考 Runner 與 runtime 共用同一組 middleware |
| 核准狀態存在獨立的 checkpoint 表 | 只存在 Session：pending tool call＋`approval_requested` | 一個事實來源 |
| `DurableRunner` 自帶一份 loop | `FileSession` 實作 Session，resume 由 Runner 負責 | 一個執行契約 |
| 驗證寫在應用程式裡 | `Agent.verify` 回傳證據；沒有證據記為 unverified | 驗證閘門成為框架語意 |
| `ModelError` 定義在 runtime | 型別在 core，分類規則在 models | runtime 與 models 不互相 import |
| 狀態別名經 `loom.compat` 轉換 | 移除相容層，全書統一的狀態名稱 | 只有一套名稱 |
| auth 在 run 開始時算一次權限 | 每次 tool call 依目前的 agent 計算 | handoff 後權限跟著換人 |
| 延遲載入的 tool 只存在 agent 物件裡 | 寫成 `tools_loaded` 擴充事件，`before_run` 從 log 重建 | resume 或換 worker 後清單相同 |
| 依賴規則只寫在文件裡 | 寫成 `ArchitectureTest` | 違規的 import 由 CI 擋下 |

v1.0 新增的四個擴充事件是 `approval_requested`、`tools_loaded`、`context_cleared`、`context_compacted`。它們和核心事件寫進同一份 Session、同樣有 seq 與版本號，但 `to_messages()` 不認得就略過，所以舊的讀取端不會壞。

## B.6 如何擴充

v1.0 的擴充原則是「加東西不必改核心」。下面四種擴充的步驟與第 45 章 45.11 節一致；每一種最後都列出要跑哪些測試來確認語意沒有走樣。

### B.6.1 加一個新 tool

| 步驟 | 做什麼 | 要遵守的規則 |
|---|---|---|
| 1 | 寫一個 `fn(deps, **args)` 函式，用 `@loom.tools.tool(...)` 裝飾 | 第一個參數 `deps` 由 harness 注入，不進 schema；其他參數要有型別提示 |
| 2 | 在 docstring 第一行寫描述，下面每行寫「參數名: 說明」 | `schema_from()` 依此產生 JSON Schema；有固定合法值的參數用 `enums=` |
| 3 | 決定副作用等級 `effect` | 不寫就是 destructive，這是刻意的保守預設（第 5 章） |
| 4 | 有副作用的 tool 設定 `intent=(...)` | 決定 idempotency key 與核准單 id；業務意圖相同就應該得到同一把 key |
| 5 | 下游用 `deps["idempotency_key"]` 去重 | 只在 harness 推導 key、下游不認，等於沒有 |
| 6 | 需要授權時設定 `scope=` | `AuthMiddleware` 會用它比對有效權限 |
| 7 | 在 `PolicyEngine` 的動作清冊登記 `(autonomy 等級, 風險類別)` | 未登記的動作會被 `ApprovalMiddleware` 以 default-deny 擋下 |
| 8 | 唯讀、想讓 code-as-action 呼叫時才設 `code_callable=True` | 有副作用的 tool 設了會在建構時丟 `ValueError` |
| 9 | 執行 `lint(tool)`，結果要是空清單 | 描述、參數說明、intent_fields 都齊全 |

驗證：`ToolsTest` 的兩個測試，以及 `CoreTest.test_idempotency_key_derived_from_intent_not_visible_to_model`。tool 的參數中不能出現 `tenant`、`user_id` 等身分欄位，`AuthMiddleware` 會直接擋下；身分只能從 `deps` 讀。

### B.6.2 加一個新 model provider

| 步驟 | 做什麼 | 要遵守的規則 |
|---|---|---|
| 1 | 繼承 `loom.models.Adapter`，建構子沿用 `(spec: ModelSpec, transport)` | transport 是 `Callable[[dict], tuple[int, dict]]`，測試時換成假的 |
| 2 | 實作 `build(messages, tools, system) -> dict` | 把統一格式翻成 provider 的請求；tools 的 `parameters` 對應到該家的 schema 欄位 |
| 3 | 實作 `parse(body) -> ModelResponse` | stop_reason 只能是四種之一，不認得的值丟 `ModelError("invalid_response", ...)` |
| 4 | usage 正規化成四個互斥的桶 | 有些 API 回報的 input 已包含快取命中的部分，要先減掉，否則成本重複計算 |
| 5 | 非 200 的回應交給 `Adapter.complete()` 內建的 `classify()` | 該家的錯誤 type 字串若有差異，在 `classify()` 增加規則，不要在 runtime 判斷 |
| 6 | 在 `ModelSpec` 填 `tier`、`regions` 與示意價格 | `Router` 依 regions 過濾（資料不出境）、依 tier 選等級 |
| 7 | 支援 prompt cache 自訂 key 時，把租戶與 `Agent.version` 放進 key | 第 42 章的多租戶不變式 |

`Adapter.complete()` 會把原始回應放進 `ModelResponse.raw`，部分推理模型需要在多輪中原樣送回的不透明欄位就存在這裡。驗證：套件中沒有現成的 adapter 單元測試（B.3.3），新 provider 應該自己寫契約測試：用假的 transport 回放錄好的回應，斷言 stop_reason、usage 四個桶與錯誤分類的結果；再用 `CoreTest.test_contract_reference_and_async_runner_write_same_events` 的寫法，確認換了模型之後核心事件序列不變。接真實 SDK 的程式依全書規則標 `# not-runnable`，而且只能放在最外圈的 adapter。

### B.6.3 加一個新 middleware

| 步驟 | 做什麼 | 要遵守的規則 |
|---|---|---|
| 1 | 繼承 `loom.core.Middleware`，只覆寫需要的擴充點 | `wrap_model`／`wrap_tool` 是 `async def`，簽名 `(self, ctx, req 或 tc, nxt)`，放行就 `return await nxt(...)` |
| 2 | 決定它在洋蔥的哪一層，理由寫在 docstring | 清單第一個在最外層；tracing 最外、approval 緊貼 dispatch（第 45 章 45.8 節） |
| 3 | 能回填錯誤就不要丟例外 | 回傳 `ToolResult("error", ...)` 讓模型改口；`StopRun(status, output)` 只在繼續沒有意義時用 |
| 4 | 需要留下紀錄就用 `ctx.emit(...)` | 新的事件類型就是擴充事件；需要被觀察的攔截用 `guardrail_tripped` |
| 5 | 有狀態就想清楚 resume 時怎麼辦 | 影響決策的狀態要能從 Session 重建（像 registry），或寫成擴充事件 |
| 6 | 不 import 其他 loom 模組 | 協作只透過 `ctx.state` 約定的鍵或建構子注入的函式，並在 docstring 寫明鍵名與讀不到時的預設 |
| 7 | `on_event` 保持輕量、不丟例外 | 例外會被記進 `ctx.hook_errors`，不會中斷 run，但代表觀察資料缺了一段 |

驗證：`ArchitectureTest` 確認沒有違規的 import；用 `ScriptedModel` 寫一個情境測試，斷言事件序列與配對不變式（每個 tool call 都有 tool_result）；如果它會在中途結束 run，再仿照 `CoreTest.test_stop_run_fills_pending_results` 確認收尾正確。第 45 章 45.11 節的 `TenantRateLimit` 是一個完整例子：它要放在 Auth 之內（需要租戶）、Approval 之外（被限流的呼叫不該開核准單）。

### B.6.4 加一個新 memory 或 session backend

| 項目 | memory backend（取代 `MemoryStore`） | session backend（取代 `InMemorySession`／`FileSession`） |
|---|---|---|
| 要實作的介面 | `handle(deps, command, path, file_text="", old_str="", new_str="") -> str`、`forget_user(tenant, user) -> int`、`as_tool() -> Tool` | `id: str`、`load() -> list[Event]`、`append(event: Event) -> None` |
| 必須保留的語意 | 虛擬路徑 `/memories` 對應到這位使用者的範圍；`/memories/org` 唯讀；擋 `..` 與編碼字元；身分只來自 `deps`；單檔上限與秘密檢查；TTL；刪除權；稽核只記路徑 | 只追加；compare-and-set（seq 必須等於目前長度，否則丟 `ConcurrencyError`）；寫入成功才回傳；`load()` 要看得到別的 worker 剛寫的事件 |
| 舊資料 | 搬遷時保留 `created`、`expires` 中繼資料 | 舊版事件用 `@upcaster(type, from_v)` 在讀取時升級，不改寫原始資料 |
| 驗證 | `MemoryTest` 的斷言（越界路徑、組織唯讀、秘密、TTL、刪除數量） | `DurableTest` 的斷言（兩個實例搶寫同一個 seq、舊版事件升級、`replay` 算出正確狀態），以及 `CoreTest.test_session_compare_and_set` |

第 45 章 45.11 節有一份以標準函式庫 `sqlite3` 實作 Session 的骨架：以 `(sid, seq)` 主鍵實作 compare-and-set，交易提交後才回傳，`load()` 每次都從資料庫讀。資料庫版的 memory 與 session 要多考慮交易、備份、保存期限與刪除 fan-out（第 12、22、36 章），但介面與上表的語意不變。

### B.6.5 擴充前的自我檢查

| 問題 | 期待的答案 |
|---|---|
| 這個功能是否至少有兩個 agent 需要？ | 是；只有一個 agent 需要就留在應用層，像證據帳本留在 research 範例 |
| 它能不能只靠四個擴充點或 Session／Model 介面接上？ | 能；需要改 `loom.core` 代表設計要重新討論 |
| 它的狀態能不能從 session log 重建？ | 能，或已寫成擴充事件 |
| 它在 middleware 清單的位置與理由是否寫進 docstring？ | 是 |
| 加進來之後 `python3 -m unittest discover -s tests` 是否仍然全部通過？ | 是，而且新功能有自己的測試 |

## B.7 已知限制與未收錄的模組

隨書套件是教學版：每個機制都短到讀得完、有測試鎖住語意，但它不是 production framework。本節依第 45 章 45.2 與 45.12 節整理它刻意沒做的事。

### B.7.1 未收錄的模組

全書出現過、但沒有收進隨書套件的模組如下。它們沒有收錄的原因分兩類：需要作業系統層級的隔離才有意義，或建在 `Runner.run()` 之上、不影響核心的組裝方式。

| 模組 | 誕生章 | 未收錄的原因 | 接上 v1.0 的位置 |
|---|---|---|---|
| `loom.sandbox` | 第 17 章 | 真正的隔離需要容器或 microVM；process 內的 `exec` 不是安全邊界 | 產生 Tool（例如 `run_tests`）；用完即銷毀、secrets 不進 sandbox、egress 預設拒絕（第 17、43 章） |
| `loom.browser` | 第 16 章 | 需要真正的瀏覽器與隔離環境 | 產生 Tool；每個動作照常經過 `wrap_tool` 的 guardrail 與 approval |
| `loom.a2a` | 第 15 章 | 對外暴露 agent 屬於平台層 | 在 `Runner.run()` 之外包一層協定；AG-UI 把 runtime 的串流事件對應成前端協定 |
| `loom.workflows` | 第 18 章 | orchestration 層，建在 Runner 之上 | 只透過 `Runner.run()` 使用核心 |
| `loom.graph` | 第 19 章 | 同上 | graph 中的 agent 節點就是在節點裡呼叫一次 Runner |
| `loom.agents` | 第 20 章 | 同上；handoff 已升格為核心的 `Handoff` | agents-as-tools 與分支合併建在 Runner 之上；sub-agent 的 typed 結果對應 `ToolSpec.inherits=False` |
| `loom.retrieval` | 第 11 章 | 檢索品質依賴真實的 embedding 與索引，教學版的雜湊向量沒有代表性 | 一個 Tool（`search_kb`）＋必要時的 context provider |

另外，第 7 章的 `loom.schema` 也沒有以獨立模組出現：v1.0 的核心 `validate_args()` 只涵蓋必填、未知參數、基本型別與 enum，巢狀結構、`oneOf` 與修復迴圈留在第 7 章的程式中。第 23 章 v0.5 的相容層 `loom.compat` 依計畫在 v1.0 移除。

### B.7.2 教學版的簡化與上線前要換的零件

| 面向 | 隨書套件的做法 | 上線前要做的事 | 相關章節 |
|---|---|---|---|
| tracing 匯出 | 教學版 `Tracer`，span 存在記憶體的 `finished` 清單，id 是確定性的 | 換成官方 OpenTelemetry SDK；`TracingMiddleware` 的 span 名稱與屬性不變 | 29 |
| Session 儲存 | `InMemorySession`；`FileSession` 是單機 JSONL 檔 | 資料庫版 Session：交易、唯一鍵、備份、保存期限 | 22、36 |
| memory 儲存 | 本機目錄；中繼資料存在 `.meta.json` | 資料庫或物件儲存；刪除權要 fan-out 到所有衍生儲存 | 12 |
| sandbox | coding 範例在同一個 process 裡執行「測試」 | 真正的 sandbox；這是上線前最容易被低估的一項 | 17、43 |
| provider adapter | 只有教學版 `MessagesAdapter`，欄位以官方文件為準；沒有直接的單元測試 | 每家一個 adapter，依官方 SDK 撰寫，契約測試鎖住正規化 | 25 |
| 身分驗證 | HMAC 共享金鑰的 token | 非對稱簽章（JWT＋JWKS），resource server 只持有公鑰 | 33 |
| step-up 驗證 | 未實作 | 大額或高風險動作要求重新驗證 | 33 |
| token 計數 | `estimate_tokens()` 以字元數 ÷ 2 粗估 | 使用 provider 的 token 計數 API 或回應中的 usage | 3、9 |
| 串流 | runtime 的佇列沒有上限 | 有界佇列、依 `n` 去重與續傳、慢速消費者處理 | 24、37 |
| resume 的觸發 | 由呼叫端呼叫 `resume()` | 任務佇列、lease，定期掃描最後一個 run 沒有 `run_finished` 的 session | 22、36 |
| spec 版本不符 | `run_started` 只記錄 `spec`，resume 時不阻擋 | 版本不符時拒絕自動恢復、轉人工判斷 | 22 |
| 核准台 | `ApprovalDesk` 是記憶體物件，`tick()` 在 resume 時才被呼叫 | 持久化的核准單、UI、逾時排程、通知 | 21 |
| 平台元件 | 沒有限流、配額、canary、gateway | 第 36、42 章的平台層 | 36、42 |
| MCP | 只有 in-process transport 與 tools 三個方法 | 官方 SDK、遠端 transport、授權、gateway | 14 |

> [!note] 2026 現況
> 截至 2026 年 10 月：`loom.mcp` 的 `PROTOCOL_VERSION = "2026-07-28"` 對應第 14 章「2026 現況」所述的當時最新規格版本（survey 標為已查證）。它只是教學版的常數，套件只模仿了「每個 request 自帶協定版本、`server/discover`」等訊息形狀的一小部分，不代表符合該版規格；接真實的 host 或 server 請使用官方 SDK，規格細節以官方文件為準。`DEMO_PRICES` 與 `price_version="demo-2026-10"` 是示意價格，不是任何供應商的報價。

### B.7.3 測試涵蓋的缺口

56 個測試鎖住了核心契約與各模組的主要語意，但並不完整。讀者擴充或拿去改寫時，最該先補的是下面幾項：

| 缺口 | 目前的狀態 | 建議補的測試 |
|---|---|---|
| `loom.models` 的串流 adapter 與 `StreamingScriptedModel` | `tests/test_models.py` 只測非串流路徑 | 串流中途斷線、`stop` 事件帶完整 `ModelResponse` |
| `ContextMiddleware` 與 registry 在 async runtime 上的組合 | 單元測試用參考 Runner | 用 `loom.runtime.Runner` 跑同一份劇本，比對事件序列 |
| 跨 process 的 `FileSession` 並行 | 測試用兩個實例模擬 | 兩個 process 同時 append，確認只有一方成功 |
| middleware 順序 | 順序寫在範例與第 45 章 | 把「tracing 在最外層、approval 在最內層」寫成測試，防止有人重排 |

這些缺口不影響本書的論點，因為每個機制的語意都已經在對應章節的動手做中用 `assert` 驗證過；它們影響的是「把套件當成起點繼續開發」時的安全網。第 45 章的檢查清單第 2、3 題（依賴規則與契約測試是否寫進 CI）在這裡同樣適用。
