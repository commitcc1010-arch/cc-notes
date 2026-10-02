# loom v1.0：隨書程式碼

《Agent System 設計全書》第 45 章組裝的教學用 agentic framework。Python 3.11+，**只用標準函式庫**，不連網、不需要 API key：模型一律用 `ScriptedModel`（依劇本回應的假模型），時間用虛擬時鐘，所以每次執行的輸出都相同。

> 這是教學實作，不是 production framework。它的價值在於每個機制都短到讀得完、而且有測試鎖住語意；上線前要替換的部分，見第 45 章「下一步可以怎麼長」。

## 執行

```bash
cd "Agent System Design/code"
python3 -m unittest discover -s tests      # 全部測試（約 0.1 秒）
python3 examples/support_agent.py          # 青鳥客服：handoff、核准中斷與恢復、tracing、eval
python3 examples/coding_agent.py           # 內部 coding agent（簡化版）：驗證閘門、durable resume、loop guard
python3 examples/research_agent.py         # 營運 research agent：registry、MCP、平行查詢、taint、證據帳本
```

## 目錄結構

```text
code/
├── README.md
├── loom/
│   ├── __init__.py      版本號與核心型別的匯出
│   ├── core.py          八個核心抽象、七種持久化事件、middleware 四個擴充點、參考 Runner（第 4、23 章）
│   ├── runtime.py       async Runner：串流、並行 tool、取消、逾時、重試、loop guard、虛擬時鐘（第 24 章）
│   ├── models.py        ScriptedModel、adapter 介面、錯誤分類、熔斷、fallback、router、成本帳本、預算（第 25 章）
│   ├── tools.py         @tool 裝飾器、tool lint、IdempotencyStore（第 4、5、7 章）
│   ├── context.py       context 是 session log 的純函式；清除舊輸出（第 9、10 章）
│   ├── compaction.py    六段交接筆記、約束逐字保留（第 10 章）
│   ├── memory.py        檔案式長期記憶：使用者／組織範圍、路徑防護、TTL、刪除權（第 12 章）
│   ├── registry.py      tool search（BM25）與延遲載入，只往尾端追加（第 13 章）
│   ├── mcp.py           教學版 in-process MCP server／client 與橋接層（第 14 章）
│   ├── approval.py      policy engine、核准單狀態機、hash chain 稽核、interrupt／resume（第 21 章）
│   ├── durable.py       JSONL 事件日誌 Session（compare-and-set、fsync、事件升級）與 replay（第 22 章）
│   ├── guardrails.py    宣告式 guardrail 執行器、Label／ToolSpec、context 層級 taint（第 23、31、32 章）
│   ├── auth.py          短效 token、token exchange、租戶注入、有效權限交集（第 33、42 章）
│   ├── tracing.py       span 樹、遮蔽、HMAC 假名化、寫入時計價（第 29 章）
│   └── evals.py         任務集、outcome grader、宣稱檢查、pass@k／pass^k（第 27 章）
├── examples/            青鳥三個 agent 的端到端範例
└── tests/               unittest：核心契約、runtime、各模組、依賴規則、範例
```

## 依賴規則

`loom.core` 不 import 任何 loom 模組；其他每個模組都只 import `loom.core`（同層模組不互相 import，需要協作時透過 `RunContext.state` 或擴充事件）。`tests/test_architecture_and_examples.py` 會解析每個檔案的 import 來檢查這條規則，並確認沒有第三方套件。

## 擴充

- **新 tool**：用 `loom.tools.tool` 裝飾一個 `fn(deps, **args)`，標上副作用等級（不標就當 destructive）與 `intent_fields`。
- **新 model provider**：繼承 `loom.models.Adapter`，實作 `build()` 與 `parse()`，把回應正規化成 `ModelResponse`（四種 stop_reason、四個互斥的 usage 桶）；錯誤一律轉成 `ModelError`。
- **新 middleware**：繼承 `loom.core.Middleware`，只覆寫需要的擴充點（`before_run`、`wrap_model`、`wrap_tool`、`on_event`）。
- **新 memory／session backend**：實作同樣的方法（`MemoryStore.handle`、`Session.load／append`），保留路徑防護與 compare-and-set 的語意。

細節與取捨見第 45 章。
