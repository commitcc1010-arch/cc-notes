---
chapter: 14
title: Model Context Protocol 深入
part: 3
---

# 第 14 章　Model Context Protocol 深入

> [!abstract] 本章地圖
> **核心問題**：同一套內部系統要接給好幾個 agent、IDE 與聊天產品使用時，怎麼用一個標準協定只整合一次，又不犧牲水平擴展與安全？
>
> **你會學到**：
> - 說清楚 MCP 解決的 N×M 整合問題，以及它和 function calling、OpenAPI、A2A 的分工
> - 畫出 host／client／server 架構，分辨 tools、resources、prompts 各由誰控制
> - 讀懂 JSON-RPC 2.0 訊息，分辨「協定錯誤」與「tool 執行錯誤」該由誰來修
> - 解釋 MCP 為什麼從 initialize handshake 與 session 走向 stateless，以及 multi round-trip requests 怎麼取代 server 主動發問
> - 為遠端 MCP server 設計 OAuth 授權：resource indicator、audience 驗證、禁止 token passthrough
> - 用純 Python 寫一個教學版 MCP server 與 client，接上 `loom` 的 tool dispatcher
>
> **前置知識**：第 4 章（`loom` v0.1 的 loop 與 dispatch）、第 5 章（tool 設計與副作用分級）、第 13 章（大量工具、tool search 與 code-as-action）

## 14.1 故事：三個 agent、三份 ERP 包裝程式

客服 agent v1 以 L3 上線三個月後，阿哲帶來了 Part 3 的第一張需求卡：「客服要能直接查 ERP 的庫存與退貨單，還要接三家物流商的貨態。」這件事聽起來和第 4 章的 `get_order` 沒什麼不同，只是多寫幾個 tool。麻煩的是，同一時間內部 coding agent 團隊想讓 agent 讀 ERP 的訂單 schema 來寫報表程式，營運 research agent 也要每月拉退貨資料做分析；營運同事甚至問，能不能在自己的 IDE 和桌面聊天 app 裡直接問「B-1042 現在在哪」。

兩週後，青鳥科技裡有了三份 ERP 包裝程式。客服 agent 的叫 `get_order`，research agent 的叫 `fetch_order_detail`，coding agent 乾脆直接連資料庫的唯讀副本。某個週二，ERP 團隊把訂單狀態的 enum 從小寫改成大寫，三個 agent 以三種不同方式壞掉：客服 agent 開始把每張訂單都說成「狀態不明」，research agent 的退貨率算成零，coding agent 產生的報表程式在 CI 裡全部失敗。Iris 花了兩天才把三個地方都找齊。

資安的 Maya 在事後檢討時把另一張投影片放上來：三份包裝程式各自持有一把 ERP 服務帳號金鑰，其中 research agent 那把因為「之後可能要寫回資料」而開了寫入權限。「你們三個團隊，各自發明了一次 ERP 的權限模型，」Maya 說，「而 ERP 團隊完全不知道誰在用、用來做什麼。」老陳在白板上畫了一個 3×4 的格子：三個 agent 加一個 IDE 是一邊，ERP、三家物流商是另一邊，每一格都是一份要維護的整合。「這是 N×M 問題。讓 ERP 團隊發布一個 MCP server，所有 agent 都當 client，格子就變成一條線。」

Iris 照做了。第一版在筆電上用 stdio 跑得很順，但部署到 Kubernetes、在 load balancer 後面開三個副本之後，客服 agent 開始隨機出現「session 不存在」的錯誤；退貨單需要使用者確認的那一步，server 要在呼叫中途回頭問 client，結果連線被 proxy 的逾時切斷。接著 Maya 又問：「ERP MCP server 收到客服 agent 傳來的使用者 token，是直接拿去打 ERP API 嗎？」Iris 愣住了，因為那正是 Iris 的寫法。

這三個問題剛好對應本章的三條主線：MCP 的架構與協定細節（14.2–14.5）、從有狀態連線走向 stateless 的演進（14.6–14.7）、授權與安全（14.8–14.10）。很多團隊都撞過同一面牆，這也是 MCP 規格最新一版改成 stateless 的原因。最後在「動手做」，我們把青鳥的 ERP 與物流 server 用純 Python 寫成教學版，接進 `loom`。

## 14.2 為什麼需要 MCP：把 N×M 變成 N＋M

第 3 章與第 4 章講的 **function calling**（函式呼叫）標準化的是「模型與 harness 之間」的格式：模型怎麼說「我要呼叫 `get_order`」，harness 怎麼把結果回填。它沒有標準化「harness 與外部系統之間」：`get_order` 這個 tool 的程式碼要寫在哪、誰維護、怎麼發現有哪些 tool、怎麼認證。結果就是每一個 host 都要自己為每一個外部系統寫一次整合。**MCP**（Model Context Protocol，模型情境協定）是一個開放協定，它把這一層也標準化：外部系統以 **MCP server** 的形式提供能力，任何支援 MCP 的應用都能以 client 身分連上去使用。例如 ERP 團隊寫一個 ERP MCP server，客服 agent、research agent、IDE 與桌面聊天 app 都能直接接上。

```text
 沒有共同協定：N 個 host × M 個系統 = N×M 份整合

   客服 agent ──┬──► ERP 包裝 #1        coding agent ──┬──► ERP 直連 DB
                ├──► 黑貓包裝 #1                       └──► GitHub 包裝
                └──► 新竹包裝 #1        research agent ─┬──► ERP 包裝 #2
   IDE ─────────┬──► ERP 包裝 #3                        └──► 報表 API 包裝
                └──► GitHub 包裝 #2     （每條線：各自的 schema、認證、錯誤處理）

 有 MCP：N 個 client 實作 + M 個 server 實作 = N＋M

   客服 agent ─────┐                       ┌──► ERP MCP server（ERP 團隊維護）
   coding agent ───┤                       ├──► 物流 MCP server（平台團隊維護）
   research agent ─┼──── MCP（同一協定）───┼──► GitHub MCP server（廠商維護）
   IDE、聊天 app ──┘                       └──► 報表 MCP server（資料團隊維護）
```

上半部是青鳥的現況：每條線都是一份獨立的程式，有自己的欄位名稱、錯誤格式與金鑰，ERP 改一個 enum，要改的是所有連到 ERP 的線。下半部是 MCP 的做法：每個 host 只要實作一次「MCP client」，每個系統只要實作一次「MCP server」，中間用同一個協定。更重要的是**所有權的移動**：ERP 的整合由最懂 ERP 的 ERP 團隊維護，enum 改了，他們在 server 裡處理一次，所有 client 同時受益；權限也集中在一個地方設計與稽核。這和 **LSP**（Language Server Protocol，語言伺服器協定）解決的問題同構：在 LSP 之前，每個編輯器要為每種語言各寫一次自動完成；之後，每種語言只要一個 language server。MCP 的規格文件也明說借鏡了 LSP 的設計。

MCP 標準化了五件事：**發現**（server 有哪些能力，例如 `tools/list`）、**呼叫**（怎麼帶參數執行，例如 `tools/call`）、**資料形狀**（結果以 content block 表示，可以是文字、圖片或資源連結）、**傳輸**（stdio 與 HTTP）、以及遠端情境下的**授權**。它刻意不標準化的事情同樣重要：tool 該怎麼設計（第 5 章）、模型怎麼挑 tool（第 8 章、第 13 章）、agent loop 怎麼寫（第 4 章），以及 host 要採取什麼安全政策（第 32 章）。MCP 是插座規格，插座本身不會讓電器變聰明。

| 技術 | 標準化的介面 | 典型使用者 | 解決的問題 | 不解決的問題 |
|---|---|---|---|---|
| function calling | 模型 ↔ harness | 每個 agent 自己 | 模型如何提出結構化呼叫 | tool 程式碼在哪、誰維護、怎麼發現 |
| OpenAPI | 程式 ↔ HTTP API | 一般後端整合 | 描述 REST API 的路徑與參數 | 給模型看的描述品質、context 型資料、互動式確認 |
| MCP | harness ↔ 外部能力 | host 與 tool 提供者 | 一次實作、到處可用的工具與資料 | agent 之間的協作、tool 的設計品質 |
| A2A（第 15 章） | agent ↔ agent | 跨團隊、跨公司的 agent | 把遠端 agent 當成不透明的服務委派任務 | 細粒度的工具呼叫 |

這張表最容易混淆的是最後兩列。MCP 的對象是「能力」：一個 tool、一份資料，呼叫端完全掌控流程；A2A 的對象是「另一個 agent」：你交出任務，對方用自己的工具與推理完成，你只看得到任務狀態與結果。如果青鳥要讓合作物流商的 agent 自己處理理賠，那是 A2A；如果只是查貨態，那是 MCP。

> [!warning] 常見誤解
> 「每個內部 API 都應該包成 MCP server。」MCP 的價值來自**重用與所有權邊界**。如果某個 tool 只有一個 agent 用、由同一個團隊維護，直接寫成 harness 內的 tool 更簡單，少一層 process、少一次序列化、除錯也直接。當同一個能力要給多個 host 使用，或者能力的擁有者是另一個團隊，MCP 的成本才划算。

## 14.3 架構：host、client、server 與三種 primitives

MCP 的架構有三個角色。**host**（宿主）是使用者實際面對的應用程式，它擁有模型、對話紀錄與安全政策，例如桌面聊天 app、IDE，或青鳥用 `loom` 寫的客服 runner。**client**（客戶端）是 host 內部的一個連線元件，**一個 client 只對應一個 server**；host 連三個 server，就有三個 client。**server**（伺服器）是提供能力的程式，可以是使用者電腦上的一個 subprocess，也可以是遠端的 HTTP 服務，例如 ERP 團隊部署的 ERP MCP server。

```text
 ┌──────────────────────── Host（loom 客服 runner）────────────────────────┐
 │  Model ◄──► Agent loop ◄──► 安全政策（allowlist、核准、預算）           │
 │                 │                                                       │
 │      ┌──────────┼───────────────┐                                       │
 │      ▼          ▼               ▼                                       │
 │  Client #1   Client #2       Client #3       （每個 client              │
 │      │          │               │              只連一個 server）        │
 └──────┼──────────┼───────────────┼───────────────────────────────────────┘
        │ stdio    │ Streamable HTTP│ Streamable HTTP
        ▼          ▼               ▼
  本機檔案 server  ERP MCP server  物流 MCP server ──► 三家物流商 API
  （subprocess）  （ERP 團隊）     （平台團隊）
                       │
                       └──► ERP 資料庫與 API（server 自己的憑證）
```

這張圖要注意三件事。第一，**host 是唯一看得到全貌的角色**：它知道對話內容、知道連了哪些 server、決定把哪些 tool 交給模型。server 彼此看不到對方，也看不到完整對話，只看到發給自己的 request。這是刻意的隔離：物流 server 不該知道使用者剛剛查了哪張 ERP 訂單。第二，client 與 server 一對一，所以每條連線可以有不同的 transport 與憑證：本機檔案 server 用 stdio，ERP server 用 HTTP 加 OAuth。第三，server 後面的系統（ERP 資料庫、物流商 API）用的是 server 自己的憑證，不是 client 傳過來的那一張，14.8 節會說明為什麼這條線不能偷懶。

server 能提供三種 **primitives**（基本能力），差別在於**由誰決定使用它**：

| primitive | 由誰控制 | 是什麼 | 青鳥的例子 | 設計重點 |
|---|---|---|---|---|
| tools | 模型（model-controlled） | 可執行的動作，可能有副作用 | `get_order`、`create_return` | 模型自己挑，所以寫入類要有核准政策 |
| resources | 應用程式（application-controlled） | 以 URI 定址的唯讀資料 | `bluebird://policy/returns`（退貨政策） | host 決定何時放進 context，可快取 |
| prompts | 使用者（user-controlled） | 帶參數的訊息模板 | 斜線指令「/退貨分析 B-1042」 | 使用者明確觸發，不由模型自行呼叫 |

這個三分法直接決定風險與成本。tool 是模型自己挑的，所以一個有副作用的 tool 只要出現在清單上，模型就可能在你沒預期的時候呼叫它，host 必須搭配第 21 章的核准政策。resource 由 host 或使用者決定是否載入，例如客服 runner 在每次 session 開始時讀一次退貨政策放進 system prompt；因為載入時機可控，它可以放在穩定前綴、命中 prompt cache（第 9 章）。prompt 則由使用者在介面上挑選，host 向 server 取得填好參數的訊息放進對話。

除了 server 提供給 client 的三種能力，早期規格也定義了反方向、由 client 提供給 server 的能力：**elicitation**（向使用者索取資訊，例如請使用者確認退貨）、**sampling**（server 借用 host 的模型產生文字）、**roots**（host 告訴 server 可以存取哪些檔案目錄）。這三者在最新一版有大幅調整：sampling 與 roots 已被標為 deprecated，elicitation 改用 14.7 節的 multi round-trip 機制運作，細節放在 14.11 節。

> [!warning] 常見誤解
> 「resource 只是唯讀的 tool。」功能上看起來像，但控制權不同。把退貨政策做成 tool，模型要先「想到」去查，每次查都多一輪呼叫，結果還落在對話尾端、無法快取；做成 resource，host 可以在開頭就放進穩定前綴。反過來，資料量大、只有少數問題用得到的資料（例如某張訂單的完整歷程），做成 tool 讓模型按需取用比較省 context。判斷標準是「誰最清楚什麼時候需要它」。

## 14.4 協定底層：JSON-RPC 2.0 訊息

MCP 的訊息建立在 **JSON-RPC 2.0** 上，這是一個極簡的遠端程序呼叫規格：用 JSON 表示「呼叫哪個方法、帶什麼參數、結果是什麼」。它只有三種訊息。**request** 有 `id`、`method` 與 `params`，期待一個回應；**response** 帶著同一個 `id`，裡面有 `result` 或 `error` 二擇一；**notification** 沒有 `id`，是不需要回應的單向通知，例如進度更新。選 JSON-RPC 的理由很實際：它和傳輸方式無關、夠小、任何語言都容易實作，LSP 也用它。

MCP 在 JSON-RPC 上定義了一組方法名稱，用斜線分組：`tools/list` 列出 tools、`tools/call` 執行 tool、`resources/list` 與 `resources/read` 列出與讀取資料、`prompts/list` 與 `prompts/get` 取得模板。清單類的方法支援 **cursor 分頁**：server 回傳一頁結果加上不透明的 `nextCursor`，client 帶著它再要下一頁，直到沒有 `nextCursor`。`tools/call` 的結果是一個 **content** 陣列，每個元素有 `type`（例如 `text`、`image`），讓 tool 可以回傳文字、圖片或指向某個 resource 的連結；需要讓程式而不是模型讀取的結果，則可以另外放在 `structuredContent`，並由 tool 定義中的 `outputSchema` 描述形狀。

這一層最值得花時間理解的，是**失敗分成兩層**。第一層是**協定錯誤**：方法不存在、tool 名稱不存在、request 格式不合法，用 JSON-RPC 的 `error` 物件回應；這代表「呼叫端的程式寫錯了」，應該由 host 或工程師處理。第二層是 **tool 執行錯誤**：協定層成功，tool 也跑了，但業務上失敗，例如查無訂單、已出貨不能退款；這用正常的 `result` 回應，並把 `isError` 設為 true。第二層正是第 4 章說的「模型能修的錯誤」，要回填給模型當觀察。下面這段程式把一次 `tools/call` 可能在 wire 上看到的訊息分類：

```python
from __future__ import annotations

import json

# 一次 tools/call 在 wire 上可能出現的四種訊息（JSON-RPC 2.0）
WIRE = [
    '{"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "get_order", "arguments": {"order_id": "B-1042"}}}',
    '{"jsonrpc": "2.0", "method": "notifications/progress", "params": {"progressToken": "p7", "progress": 0.5}}',
    '{"jsonrpc": "2.0", "id": 7, "result": {"content": [{"type": "text", "text": "找不到訂單 B-1042"}], "isError": true}}',
    '{"jsonrpc": "2.0", "id": 8, "error": {"code": -32602, "message": "Unknown tool: cancel_order"}}',
    '{"jsonrpc": "2.0", "id": 9, "result": {"content": [{"type": "text", "text": "{\\"status\\": \\"shipped\\"}"}]}}',
]

STANDARD_ERRORS = {-32700: "Parse error", -32600: "Invalid Request", -32601: "Method not found",
                   -32602: "Invalid params", -32603: "Internal error"}


def classify(raw: str) -> str:
    """回答兩個問題：這是哪一種 JSON-RPC 訊息？如果是失敗，該由誰來修？"""
    msg = json.loads(raw)
    if "method" in msg:
        return "request（要回應）" if "id" in msg else "notification（沒有 id，不回應）"
    if "error" in msg:                      # 協定層失敗：呼叫端的程式或設定有問題
        code = msg["error"]["code"]
        return f"協定錯誤 {code} {STANDARD_ERRORS.get(code, '自訂')} → host／工程師修"
    if msg["result"].get("isError"):        # 協定成功、tool 執行失敗：模型可以讀了再改
        return "tool 執行錯誤 → 回填給模型當觀察"
    return "成功結果 → 回填給模型"


for raw in WIRE:
    msg = json.loads(raw)
    print(f"id={str(msg.get('id', '-')):<2} {classify(raw)}")

kinds = [classify(r) for r in WIRE]
assert kinds[1].startswith("notification") and kinds[3].startswith("協定錯誤 -32602")
assert kinds[2].startswith("tool 執行錯誤")
```

```text
id=7  request（要回應）
id=-  notification（沒有 id，不回應）
id=7  tool 執行錯誤 → 回填給模型當觀察
id=8  協定錯誤 -32602 Invalid params → host／工程師修
id=9  成功結果 → 回填給模型
```

第一行是 request，帶著 `id=7`；第二行是 notification，沒有 id，所以 server 送出、client 不回應，這裡是長任務的進度回報。第三行同樣是 `id=7` 的回應，代表它回答的是第一行那個 request；它是一個成功的 JSON-RPC 回應，但 `isError` 為 true，意思是「tool 跑了，找不到訂單」，host 應該把這段文字回填給模型，讓模型去向使用者確認編號。第四行是 `id=8` 的協定錯誤：`-32602` 代表參數不合法，這裡是 tool 名稱不存在，這不該交給模型「再試試看」，而是 host 的 tool 清單和 server 不同步，要修的是程式。第五行是一般的成功結果。

| 錯誤碼 | 名稱 | MCP 中的典型原因 | 誰處理 |
|---|---|---|---|
| -32700 | Parse error | 傳來的不是合法 JSON（transport 切壞了訊息） | transport 與 client 實作 |
| -32600 | Invalid Request | 缺少 `jsonrpc` 或 `method` | client 實作 |
| -32601 | Method not found | server 不支援這個方法（版本或 capability 不符） | host：先查詢 server 支援什麼 |
| -32602 | Invalid params | tool 名稱不存在、resource 不存在、參數格式錯誤 | host：同步 tool 清單或修正呼叫 |
| -32603 | Internal error | server 內部例外未被處理 | server 維護者 |
| `isError: true`（不是錯誤碼） | tool 執行錯誤 | 查無資料、業務規則拒絕 | 回填給模型 |

表的最後一列刻意放在這裡，因為它是最常被搞錯的地方。如果 server 把「查無訂單」當成 `-32603` 丟出，host 的 client 程式會把它當成例外，模型就看不到可行動的訊息；反過來，如果 server 把「tool 不存在」包成 `isError` 的文字，模型會開始猜別的 tool 名稱，掩蓋了 host 與 server 版本不同步的真正問題。參數驗證失敗屬於哪一層，不同版本的規格與 SDK 有不同的處理；本章的教學版把它當成 tool 執行錯誤回給模型，因為依第 4 章的原則，參數寫錯是模型修得好的錯誤。

## 14.5 Transport：stdio 與 Streamable HTTP

**transport**（傳輸層）只回答一個問題：JSON-RPC 的字串怎麼從 client 搬到 server、再搬回來。協定本身與 transport 無關，這是 14.4 節選擇 JSON-RPC 的直接收益。MCP 定義了兩種標準 transport。

**stdio**：host 把 server 當成 subprocess 啟動，client 寫 JSON 到 server 的標準輸入，server 把回應寫到標準輸出，一行一則訊息；標準錯誤輸出留給 server 寫 log。它沒有網路、沒有 port、沒有 TLS，啟動快、除錯容易，憑證通常從環境變數取得。代價是一個 server process 通常只服務一個 host，而且它跑在使用者的機器上、用使用者的權限，這也是本機 server 的供應鏈風險來源：一行 `npx` 或 `uvx` 指令就能下載並執行一個未經審核的套件。

**Streamable HTTP**：server 是一個 HTTP 服務，提供單一 endpoint。client 把每則 JSON-RPC 訊息用 HTTP POST 送出；server 可以直接回一個 JSON，也可以把回應改成 **SSE**（server-sent events，伺服器推送事件）串流，在最終結果之前先送進度通知。它適合遠端、多使用者、需要集中部署與 OAuth 授權的情境，例如 ERP 團隊的 server。早期規格有另一種「HTTP＋SSE」transport，需要兩個 endpoint 與一條長連線，已被 Streamable HTTP 取代。

```text
 stdio（本機 subprocess）                    Streamable HTTP（遠端服務）

 Host ── spawn ──► server process            Host ── POST /mcp（一則 JSON-RPC）──► LB
  │                                            │                                    │
  │ stdin  ─► {"id":1,"method":...}\n          │                     ┌──────────────┼──────┐
  │ stdout ◄─ {"id":1,"result":...}\n          │                     ▼              ▼      ▼
  │ stderr ◄─ log（不能混進 stdout）          │                  replica A     replica B  C
  │                                            │◄── 200 application/json（一次回完）
  │ 憑證：環境變數                             │◄── 200 text/event-stream（進度…最終結果）
  │ 生命週期：跟著 host 啟動與結束             │ 憑證：Authorization: Bearer（OAuth）
```

左半邊的 stdio 有一個常見陷阱：標準輸出是協定通道，server 程式裡任何一個除錯用的 `print` 都會把一段非 JSON 的文字混進去，client 收到 parse error 後連線就壞了；log 一律寫到標準錯誤輸出。右半邊的 HTTP 版本，每個 POST 都是一次獨立的 HTTP 交換，前面可以放 load balancer 與多個副本。注意圖中的 LB：14.6 節會看到，早期規格在 HTTP 上維持 session 的做法，正是和這個 LB 起衝突。

| 面向 | stdio | Streamable HTTP | in-process（本章動手做） |
|---|---|---|---|
| server 在哪 | 使用者機器上的 subprocess | 遠端服務，可多副本 | 同一個 process 內的物件 |
| 典型用途 | 檔案系統、本機工具、開發者工具 | 企業 SaaS、共享的內部系統 | 測試、SDK 內建工具、framework 內部 |
| 憑證 | 環境變數 | OAuth access token | 不需要 |
| 擴展性 | 一個 host 一個 process | 水平擴展（需 stateless） | 不適用 |
| 主要風險 | 執行未審核的套件、權限等同使用者 | token 處理、SSRF、多租戶隔離 | 幾乎沒有，但也測不到網路問題 |
| 除錯方式 | 看 stderr、錄製 stdin／stdout | HTTP log、trace | 直接看 wire 紀錄 |

最後一欄是本章動手做採用的方式：client 與 server 在同一個 Python process，transport 只是把 JSON 字串交給 server 的處理函式。它仍然保留序列化，所以 wire 上的每一個位元組都和真實 transport 一樣，但不需要網路。主流 SDK 也提供類似的 in-process server。

> [!warning] 常見誤解
> 「stdio server 在本機，所以比較安全。」本機 server 以使用者的身分執行，能讀使用者的檔案、用使用者的網路，它的風險比遠端 server 更直接。遠端 server 至少有一道 OAuth 與網路邊界；本機 server 要靠套件來源審核、版本鎖定與 sandbox（第 17 章）來控制。

## 14.6 生命週期的演進：從 initialize handshake 到 stateless

早期的 MCP 是一個**有狀態的連線協定**。client 連上 server 之後，第一件事是送出 `initialize` request，帶上自己支援的協定版本、自己的能力（capabilities，例如「我支援 sampling」）與身分；server 回覆它選定的版本、自己的能力（例如「我的 tool 清單會變動，會發通知」）、身分與給模型的使用說明；client 再送一個 `notifications/initialized` 通知，握手才算完成，之後才能呼叫 tools。這個借自 LSP 的設計有兩個好處：版本與能力只協商一次，之後的訊息不必重複攜帶；連線建立後是雙向的，server 也能在同一條連線上主動送 request 給 client。

```text
 早期：有狀態的連線生命週期

 Client                                     Server（某一個 process）
   │── initialize（版本、capabilities、clientInfo）──►│
   │◄── 選定版本、capabilities、serverInfo ───────────│  ← server 記住這個 session
   │── notifications/initialized ────────────────────►│
   │                                                   │
   │── tools/list ───────────────────────────────────►│  ← 依 session 決定回什麼
   │── tools/call ───────────────────────────────────►│
   │◄── （呼叫中途）elicitation/create ───────────────│  ← server 反向發問，
   │── 使用者的回答 ─────────────────────────────────►│     需要同一條連線還活著
   │◄── tools/call 結果 ──────────────────────────────│
   │                                                   │
   │   HTTP 上：每個 request 帶 Mcp-Session-Id header，server 依它找回 session
```

圖中三個箭頭旁的註解，是有狀態設計在 production 會出問題的地方。在 stdio 上這一切很自然：一個 host 對一個 process，連線就是 process 的生命週期。但搬到 HTTP 上，每個 POST 都是獨立的請求，規格於是用一個 `Mcp-Session-Id` header 把它們串成 session，server 把 session 存在記憶體裡。只要 server 有多個副本、前面有一個 load balancer，問題就來了。下面的程式模擬 Iris 在 Kubernetes 上看到的現象：

```python
from __future__ import annotations

import itertools

SHARED_STORE: dict[str, dict] = {}            # 模擬 Redis／資料庫：所有 instance 都看得到


class StatefulInstance:
    """舊式：initialize 之後，session 存在這台 instance 的記憶體裡。"""

    def __init__(self, name: str):
        self.name, self.sessions = name, {}

    def handle(self, method: str, headers: dict, params: dict) -> tuple[int, dict]:
        if method == "initialize":
            sid = f"{self.name}-s{len(self.sessions) + 1}"
            self.sessions[sid] = {"version": params["protocolVersion"]}
            return 200, {"Mcp-Session-Id": sid}
        if headers.get("Mcp-Session-Id") not in self.sessions:
            return 404, {"error": "unknown session，client 必須重新 initialize"}
        return 200, {"served_by": self.name}

    def restart(self) -> None:                # deploy 或 crash：記憶體裡的 session 全部消失
        self.sessions.clear()


class StatelessInstance:
    """新式：每個 request 自帶版本與能力；跨 call 的狀態用 server 發的 handle，存在共享儲存。"""

    def __init__(self, name: str):
        self.name = name

    def handle(self, method: str, headers: dict, params: dict) -> tuple[int, dict]:
        if params.get("_meta", {}).get("protocolVersion") != "v2":
            return 400, {"error": "unsupported version"}
        if method == "start_report":
            handle = f"rpt-{len(SHARED_STORE) + 1}"
            SHARED_STORE[handle] = {"month": params["month"], "rows": 0}
            return 200, {"handle": handle, "served_by": self.name}
        if method == "append_rows":
            SHARED_STORE[params["handle"]]["rows"] += params["n"]
            return 200, {"rows": SHARED_STORE[params["handle"]]["rows"], "served_by": self.name}
        return 200, {"served_by": self.name}


def round_robin(instances):
    return itertools.cycle(instances).__next__


# ── 舊式：三個 instance 在 round-robin load balancer 後面 ──
pick = round_robin([StatefulInstance("A"), StatefulInstance("B"), StatefulInstance("C")])
_, h = pick().handle("initialize", {}, {"protocolVersion": "v1"})
for i in range(3):
    code, body = pick().handle("tools/call", h, {})
    print(f"stateful  call {i + 1} → {code} {body}")

# 就算加 sticky session，deploy 一重啟也一樣斷
a = StatefulInstance("A")
_, h = a.handle("initialize", {}, {"protocolVersion": "v1"})
a.restart()
print("sticky＋重啟 →", a.handle("tools/call", h, {}))

# ── 新式：任何 instance 都能接任何 request ──
pick = round_robin([StatelessInstance("A"), StatelessInstance("B"), StatelessInstance("C")])
meta = {"_meta": {"protocolVersion": "v2"}}
_, r = pick().handle("start_report", {}, {**meta, "month": "2026-09"})
print("stateless start  →", r)
for n in (120, 80):
    print("stateless append →", pick().handle("append_rows", {}, {**meta, "handle": r["handle"], "n": n})[1])

assert SHARED_STORE["rpt-1"]["rows"] == 200
```

```text
stateful  call 1 → 404 {'error': 'unknown session，client 必須重新 initialize'}
stateful  call 2 → 404 {'error': 'unknown session，client 必須重新 initialize'}
stateful  call 3 → 200 {'served_by': 'A'}
sticky＋重啟 → (404, {'error': 'unknown session，client 必須重新 initialize'})
stateless start  → {'handle': 'rpt-1', 'served_by': 'A'}
stateless append → {'rows': 120, 'served_by': 'B'}
stateless append → {'rows': 200, 'served_by': 'C'}
```

前三行是舊式 server 在 round-robin load balancer 後面的樣子。`initialize` 落在 A，session 存在 A 的記憶體；第一次呼叫被分到 B，B 不認識這個 session，回 404；第二次到 C，同樣 404；第三次輪回 A 才成功。這就是 Iris 看到的「隨機」錯誤，其實成功率剛好是副本數分之一。常見的補救是 **sticky session**（黏著連線：LB 讓同一個 session 永遠打到同一台），但第四行說明了它的極限：A 一重啟，記憶體裡的 session 全部消失。serverless 平台更糟，兩次呼叫之間 process 可能根本不存在。

後三行是 stateless 的做法。每個 request 都自己帶著協定版本（程式中的 `_meta`），所以任何副本都能處理；三次呼叫分別落在 A、B、C，全部成功。跨呼叫需要的狀態（這裡是一份正在累積的月報）不存在連線上，而是由 server 發一個 **handle**（控制代碼，例如 `rpt-1`），client 把它當成普通的 tool 參數傳回來，server 從共享儲存讀出狀態。狀態沒有消失，只是從「隱含在連線裡」搬到「明確、可定址的資料」。

MCP 最新一版的規格正是走這條路，核心變化有四項（具體欄位名稱放在 14.11 節）。第一，**拿掉 initialize handshake 與 protocol-level session**：版本、client 能力與 client 身分改由每個 request 的 metadata 自己攜帶。第二，新增一個必須實作的 **`server/discover`** 方法，client 任何時候都能問「你支援哪些版本、有什麼能力、你是誰」，不需要先建立連線狀態。第三，需要跨呼叫的狀態，由 server 發 handle、當成 tool 參數傳遞。第四，server 不再在呼叫中途反向發 request 給 client，改用下一節的 multi round-trip requests。附帶的效果是 tool 清單不再因連線而不同，並以固定順序回傳、附上快取存活時間，對 client 端快取與 prompt cache 都友善。

```text
 最新：stateless，每個 request 自給自足

 Client                         LB              Server 副本 A / B / C（任何一台都行）
   │── server/discover ────────►│──► A ── 版本、capabilities、serverInfo
   │                            │
   │── tools/list ─────────────►│──► B ── tools（固定順序、ttlMs、cacheScope）
   │   _meta：版本、client 能力、clientInfo
   │                            │
   │── tools/call start_report ►│──► C ── {handle: rpt-1}  ──► 共享儲存
   │── tools/call append_rows ─►│──► A ── 讀 rpt-1 的狀態 ◄── 共享儲存
   │   arguments：{handle: rpt-1, ...}
   │
   │   沒有 session、沒有 Mcp-Session-Id；需要狀態就用 handle，需要使用者輸入就用 MRTR
```

對照前一張圖，這張圖少了握手，也少了 server 反向發問的箭頭；每一列都可以落在任何副本。代價也要看清楚。每個 request 多帶的 metadata 可以忽略；真正的成本是 handle 變成一種要保護的資源：它必須綁定擁有者，server 收到 `rpt-1` 時要檢查呼叫者是不是建立它的使用者，否則一個猜得到的 handle 就是越權讀取的入口。最後，原本「握手時一次協商好」的能力，現在每次都要檢查，client 也要準備好處理「這個 server 不支援某方法」的錯誤。

| 面向 | 有狀態連線（早期） | stateless（最新） |
|---|---|---|
| 版本與能力協商 | initialize 時一次 | 每個 request 的 metadata 攜帶；`server/discover` 隨時查詢 |
| 跨呼叫狀態 | 隱含在 session 裡 | server 發 handle，當成 tool 參數 |
| server 向 client 要資料 | 呼叫中途反向發 request | 回傳「需要輸入」的結果，client 補上後重送 |
| 水平擴展 | 需要 sticky session，重啟就斷 | 任意副本、serverless 皆可 |
| 斷線恢復 | 依 event id 續傳串流 | 用新的 request id 重送 |
| tool 清單 | 可能因連線而不同 | 對所有 client 一致、固定順序、可快取 |

這張表的每一列都在呼應同一個設計原則：**狀態要嘛放在 request 裡，要嘛放在明確可定址的儲存裡，不要放在連線上**。這也是 HTTP 與 REST 走過的路。對寫 framework 的人，這還有一個啟示：`loom` 的 session（第 10 章的 session log）應該和協定層解耦，不要假設底下的 MCP 連線會一直活著。

> [!warning] 常見誤解
> 「stateless 代表 server 不能有狀態。」server 當然可以有狀態，購物車、草稿、長任務都需要。stateless 指的是**協定層不依賴連線狀態**：任何一個 request 都可以被任何一個副本正確處理。狀態從「連線的隱含屬性」變成「有 id、有擁有者、有存活時間的資料」，反而更容易備份、稽核與跨副本共享。

## 14.7 Server 需要問 client 的時候：從反向 request 到 multi round-trip

有些 tool 執行到一半，server 才發現自己缺一樣東西。青鳥的 `create_return` 要建立退貨單並觸發退款，ERP 團隊要求每一筆都要使用者本人確認金額；報表 server 想請模型把一段資料摘要成一句話；檔案 server 需要知道使用者允許它碰哪些目錄。早期規格的做法是讓 server 在 `tools/call` 進行到一半時，反向送一個 request 給 client：`elicitation/create` 請使用者確認、`sampling/createMessage` 借用 host 的模型、`roots/list` 詢問目錄。client 回答之後，server 那個暫停中的呼叫才繼續。

這個設計在 stdio 上很優雅，在 stateless 的世界卻不可能成立：「暫停中的呼叫」活在某一台副本的記憶體裡，使用者的回答必須送回同一台、同一條連線，而這條連線在使用者思考的三十秒裡，很可能已經被 proxy 的逾時切斷。這正是 Iris 遇到的第二個問題。最新規格的解法叫 **Multi Round-Trip Requests**（MRTR，多次往返請求）：server 不再反向發問，而是**直接回傳一個「需要輸入」的結果**，說明缺什麼；client 取得答案後，把答案附在原本的 request 上**重送一次**。

```text
 Client（host）                                      Server（任意副本）
   │── tools/call create_return {order_id: B-1042} ───►│
   │                                                    │ 缺使用者確認：不執行副作用
   │◄── resultType: input_required ─────────────────────│
   │      inputRequests: {confirm: elicitation 表單}    │
   │      requestState: <server 封好的狀態>             │
   │                                                    │
   │  host 在 UI 問使用者「確定退款 1280 元？」→ 同意   │（這段時間沒有任何連線掛著）
   │                                                    │
   │── tools/call create_return {order_id: B-1042} ───►│ 可能落在另一台副本
   │      inputResponses: {confirm: accept, approve}    │
   │      requestState: <原樣送回>                      │ 驗證 requestState、執行副作用
   │◄── resultType: complete，content：已建立 R-7781 ───│
```

逐步看這張時序圖。第一次呼叫時，server 檢查到缺少確認，**不執行任何副作用**，回傳 `input_required`，裡面有兩樣東西：`inputRequests` 說明需要什麼輸入（這裡是一份 elicitation 表單），`requestState` 是 server 想在下一輪拿回來的狀態，例如它算好的退款金額。client 把表單交給 host 的 UI，這段時間 server 端沒有任何東西在等，連線可以斷、副本可以重啟。使用者同意後，client 把原 request 加上 `inputResponses` 與原樣的 `requestState` 重送；這次可能落在另一台副本，但需要的狀態全在 request 裡，所以照樣能處理。概念上，這很像 HTTP 的「401 之後帶著憑證重試」。

`requestState` 有一個容易忽略的性質：它在兩輪之間由 client 保管，所以**對 server 來說是不可信的輸入**。如果 server 把「退款金額」放在裡面，惡意或有 bug 的 client 就可能改掉它。下面的程式用標準函式庫的 `hmac` 為 requestState 加上簽章，示範完整的兩輪流程與竄改偵測（欄位形狀是教學用的簡化，確切 schema 以規格為準）：

```python
from __future__ import annotations

import hashlib
import hmac
import json

SERVER_KEY = b"only-servers-know-this"     # 所有 server instance 共用；client 拿不到


def seal(state: dict) -> str:
    """requestState 由 client 保管、原樣送回；server 要能發現它被改過。"""
    payload = json.dumps(state, sort_keys=True, ensure_ascii=False)
    mac = hmac.new(SERVER_KEY, payload.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{payload}|{mac}"


def unseal(token: str) -> dict:
    payload, mac = token.rsplit("|", 1)
    good = hmac.new(SERVER_KEY, payload.encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(mac, good):
        raise PermissionError("requestState 遭竄改")
    return json.loads(payload)


def server_create_return(params: dict) -> dict:
    """任何一台 instance 都能處理：需要的狀態全在 request 裡。"""
    answers = params.get("inputResponses", {})
    if "confirm" not in answers:              # 缺使用者確認：不建立退貨單，而是告訴 client 缺什麼
        order = params["arguments"]["order_id"]
        return {"resultType": "input_required",
                "inputRequests": {"confirm": {"method": "elicitation/create", "params": {
                    "message": f"確定為 {order} 建立退貨單？將退款 1280 元",
                    "requestedSchema": {"type": "object", "properties": {"approve": {"type": "boolean"}}}}}},
                "requestState": seal({"order_id": order, "refund": 1280})}
    state = unseal(params["requestState"])
    reply = answers["confirm"]
    if reply["action"] != "accept" or not reply["content"]["approve"]:
        return {"resultType": "complete", "content": [{"type": "text", "text": "使用者取消"}]}
    return {"resultType": "complete",
            "content": [{"type": "text", "text": f"已建立 R-7781，退款 {state['refund']} 元"}]}


def client_call(params: dict, ask_user, max_rounds: int = 3) -> tuple[dict, int]:
    """client 的 MRTR 迴圈：收到 input_required 就補上答案、帶著 requestState 重送原 request。"""
    for rounds in range(1, max_rounds + 1):
        result = server_create_return(params)
        print(f"  round {rounds} ← resultType={result['resultType']}")
        if result["resultType"] == "complete":
            return result, rounds
        answers = {k: ask_user(req["params"]["message"]) for k, req in result["inputRequests"].items()}
        params = {**params, "inputResponses": answers, "requestState": result["requestState"]}
    raise RuntimeError("超過允許的往返次數")


def user_says_yes(message: str) -> dict:
    print(f"  UI 詢問使用者：{message} → 同意")
    return {"action": "accept", "content": {"approve": True}}


print("正常流程：")
result, rounds = client_call({"name": "create_return", "arguments": {"order_id": "B-1042"}}, user_says_yes)
print("  結果：", result["content"][0]["text"])

print("竄改 requestState：")
first = server_create_return({"name": "create_return", "arguments": {"order_id": "B-1042"}})
forged = first["requestState"].replace("1280", "9999")
try:
    server_create_return({"arguments": {"order_id": "B-1042"}, "requestState": forged,
                          "inputResponses": {"confirm": {"action": "accept", "content": {"approve": True}}}})
except PermissionError as exc:
    print("  server 拒絕：", exc)

assert rounds == 2 and "1280" in result["content"][0]["text"]
```

```text
正常流程：
  round 1 ← resultType=input_required
  UI 詢問使用者：確定為 B-1042 建立退貨單？將退款 1280 元 → 同意
  round 2 ← resultType=complete
  結果： 已建立 R-7781，退款 1280 元
竄改 requestState：
  server 拒絕： requestState 遭竄改
```

第一段輸出是正常流程。round 1，server 回 `input_required`，host 在 UI 顯示 server 提供的訊息並取得同意；round 2，client 帶著答案與 requestState 重送，server 驗證簽章、讀出金額 1280，建立退貨單，回 `complete`。注意副作用只發生在最後一輪，第一輪什麼都沒寫入，所以就算使用者關掉視窗、永遠不回答，系統也沒有半成品。第二段輸出是竄改測試：有人把 requestState 裡的 1280 改成 9999，server 重新計算 HMAC 不符，直接拒絕。實務上還有另一種做法：requestState 只放一個隨機 id，真正的狀態存在 server 端的共享儲存，並設定過期時間；兩種做法都比「相信 client 送回來的內容」安全。

MRTR 也讓 client 端的責任變清楚了：限制往返次數（程式中的 `max_rounds`），避免 server 無止境地要求輸入；把每一輪都記進 trace（第 29 章）；以及確保重送的是**同一個邏輯操作**，server 端仍應以 idempotency key 防止重複建立（第 5 章）。這個「暫停、索取外部輸入、帶著狀態恢復」的模式在 agent 系統裡到處都是：第 15 章 A2A 的 input-required 狀態、第 21 章 human-in-the-loop 的 interrupt、第 22 章 durable execution 的等待，本質上是同一件事。

至於 sampling 與 roots 為什麼被標為 deprecated：sampling 的原意是讓 server 借用 host 的模型，但實務上需要 LLM 的 server 多半直接呼叫模型供應商的 API，成本與資料政策更好控制，host 也不必說明自己的模型被拿去做什麼。roots 告訴 server 可以碰哪些目錄，現在建議直接用 tool 參數或 resource URI 傳路徑，讓每一次存取都明確出現在 request 裡。elicitation 則保留下來，因為「向使用者確認」是 agent 系統真正需要的能力；它還有一種 URL 模式，讓使用者到瀏覽器完成敏感操作（例如第三方授權），敏感資料完全不經過模型與 client。

## 14.8 授權：遠端 MCP server 是 OAuth resource server

stdio server 跟著使用者的 process 跑，憑證從環境變數拿，誰在用很清楚。遠端 server 不一樣：ERP MCP server 同時服務客服 agent、IDE 與聊天 app 上的上百位使用者，每個 request 都必須回答「這是誰、代表誰、能做什麼」。MCP 選擇不發明新的授權機制，而是直接採用 **OAuth 2.1**。先用青鳥的場景把 OAuth 的四個角色對上：**resource owner** 是使用者（客服人員 Amy）；**client** 是 MCP client 所在的 host；**authorization server**（授權伺服器）是公司的身分系統，負責登入與發 token；**resource server** 是被保護的服務，也就是 ERP MCP server。**access token** 是授權伺服器發給 client 的通行證，上面寫著它給誰用（**audience**，受眾）、能做什麼（**scope**，範圍）、何時過期。

```text
 Host / MCP client          ERP MCP server             公司身分系統（AS）
   │── POST /mcp（沒帶 token）────►│                           │
   │◄── 401 WWW-Authenticate：     │                           │
   │     resource_metadata=<PRM 位置>                          │
   │── GET Protected Resource Metadata ──►│                    │
   │◄── authorization_servers=[公司 AS]、scopes_supported ─────│
   │                                                           │
   │── 授權請求：PKCE、scope=orders:read、resource=<ERP MCP server 的 URI> ─►│
   │        （使用者在瀏覽器登入並同意）                       │
   │◄──────── access token（aud = ERP MCP server，scope = orders:read）──────│
   │                                                           │
   │── POST /mcp  Authorization: Bearer <token> ──►│           │
   │                       驗證：簽章、過期、aud 是不是我、scope 夠不夠
   │◄── tools/call 結果 ───────────────│
```

逐步看這個流程。client 第一次沒帶 token 打過來，server 回 401，並在 `WWW-Authenticate` header 指出自己的 **Protected Resource Metadata**（受保護資源中繼資料，RFC 9728）在哪裡；client 讀這份 metadata，得知「我的 token 要去哪個授權伺服器拿、支援哪些 scope」。接著 client 走標準的 OAuth 授權碼流程，必須使用 **PKCE**（一種防止授權碼被攔截後冒用的機制），並在請求中帶上 **resource indicator**（RFC 8707）：明確寫出「這張 token 是要拿去用在 ERP MCP server 的」。授權伺服器於是把 token 的 audience 設成 ERP MCP server。最後 client 以 `Authorization: Bearer` header 帶 token 呼叫，server 驗證簽章、期限、scope，以及最關鍵的一項：**audience 是不是自己**。

resource indicator 與 audience 驗證要一起看才懂它在防什麼。假設沒有這兩樣，客服 host 拿一張通用 token 同時打 ERP 與物流 server；物流 server 一旦被入侵，就拿到一張能直接打 ERP 的 token。有了 audience 綁定，每張 token 只在一個 server 有效，外洩的影響被限制在那裡。

接著回答 Maya 的問題。Iris 原本的寫法是：ERP MCP server 收到 client 的 token，原封不動地轉送給後面的 ERP API。這叫 **token passthrough**（token 直通），MCP 規格明文禁止：server 不得接受不是發給自己的 token，也不得把收到的 token 轉送給下游。禁止的理由有三個。第一，下游 API 看到的是「使用者直接來呼叫」，MCP server 該做的限流、稽核與權限檢查都被繞過。第二，稽核紀錄上看不出這個操作經過了 MCP server，事故時無法追溯。第三，如果 ERP API 接受這種 token，代表它接受 audience 不是自己的 token，等於把 audience 綁定整個作廢。

```text
 錯誤：token passthrough
   client ── token(aud=ERP MCP) ──► ERP MCP server ── 同一張 token ──► ERP API
                                     （只是轉手）                     （接受了不是給它的 token）

 正確：每一段都有自己的 token
   client ── token(aud=ERP MCP, scope=orders:read) ──► ERP MCP server
                                                         │ 驗 aud、scope；記錄「Amy 經由客服 host」
                                                         │ 以自己的身分向 AS 換 token
                                                         ▼ （或用服務憑證＋使用者情境）
                                                       token(aud=ERP API, scope 最小) ──► ERP API
```

圖中下半部是正確的做法：ERP MCP server 驗完 client 的 token 之後，用**自己的身分**取得一張專門給 ERP API 的 token，常見方式是 OAuth token exchange，或用 server 自己的服務憑證並附帶使用者情境；scope 只開這次需要的最小範圍。這樣每一段的權限、稽核與撤銷都是獨立的。這也是 **confused deputy**（混淆代理人）問題的解法：一個有權限的中介者（MCP server），被誘導用自己的權限替不該有權限的請求者辦事；防禦的關鍵是中介者每次都依「原始請求者」的身分做授權判斷，而不是依自己的權限。

還有兩個機制值得認識。第一是 **client 註冊**：授權伺服器要知道 client 是誰。早期規格推薦 **Dynamic Client Registration**（動態註冊，client 自己向授權伺服器註冊），但在開放生態裡，這讓任何程式都能註冊成 client，難以管理；最新規格改推 **Client ID Metadata Documents**：client 的 id 就是一個 URL，指向 client 自己發布的 metadata 文件，授權伺服器讀取後決定是否信任。第二是 **scope 最小化與 step-up**：client 一開始只要最少的 scope（例如只讀訂單）；當它呼叫需要更高權限的 tool，server 回 403 並指出缺少的 scope，client 再請使用者授權更高的範圍，而且要限制重試次數。

| 威脅 | 情境 | 防禦 |
|---|---|---|
| token 外洩被重用 | 某個 server 被入侵，拿到的 token 被拿去打別的 server | resource indicator＋audience 驗證；短效 token |
| token passthrough | MCP server 把 client 的 token 轉送下游 | 禁止；server 以自己的身分取得下游 token |
| confused deputy | MCP proxy 用自己的高權限替使用者執行 | 依原始使用者身分授權；每個使用者各自同意 |
| mix-up attack | client 被騙把授權碼送到錯的授權伺服器 | 驗證授權回應中的 issuer |
| SSRF | metadata 探索時被導向內網位址 | 限制可連線的位址與 scheme |
| token 洩漏在 log | token 放在 URL query string | 只能放在 `Authorization` header |

表中的防禦大多已由授權伺服器與 client SDK 實作，你要做的是**不要繞過它們**。授權在規格中是選用的，但只要 server 走 HTTP、服務多個使用者，就應該照規格實作；更完整的 delegation 與稽核設計在第 33 章。

## 14.9 Extensions：在精簡的 core 之外長出新能力

協定一旦被廣泛採用，每個新需求都想擠進 core，全部塞進去，每個實作者都要追著實作一堆用不到的功能。MCP 的解法是 **extensions**（擴充）：core 保持精簡，選用能力以擴充的形式定義，每個擴充有帶命名空間的識別字（例如 `io.modelcontextprotocol/ui`），由 client 與 server 在 capabilities 中協商，**預設停用**，雙方都宣告支援才啟用。

```text
 Core（每個實作都要支援）              Extensions（雙方都宣告才啟用）
 ┌───────────────────────────┐        ┌───────────────────────────────────────────┐
 │ JSON-RPC、transport         │        │ MCP Apps：server 提供互動式 UI             │
 │ server/discover             │  協商  │ Tasks：長時間非同步工作（handle＋polling） │
 │ tools / resources / prompts │◄──────►│ Skills over MCP：用 resources 發布 Skills  │
 │ elicitation（MRTR）         │        │ ext-auth：M2M、企業管理的授權              │
 │ 授權（OAuth）               │        │ 實驗性擴充（需掛在工作小組之下）           │
 └───────────────────────────┘        └───────────────────────────────────────────┘
   client 不支援某個 extension 時：server 必須退回 core 也能運作的行為
```

左邊是所有實作都要支援的 core，右邊是選用的擴充；中間的「協商」是關鍵。圖下方那一行是設計擴充時最重要的責任：server 不能假設 client 一定支援某個擴充。例如 ERP server 提供了一個互動式退貨表單，但使用者用的是只有文字介面的 CLI host，server 就要退回「用 elicitation 問兩個問題」的做法。

**MCP Apps** 讓 server 回傳一段在 host 內嵌顯示的互動式 UI，例如讓使用者在一張訂單明細上勾選要退的品項，比用文字一來一回快得多。它的安全問題和瀏覽器嵌入第三方網頁一樣：host 必須把 UI 放在隔離環境執行，不能讓它讀取對話或 host 的資料。第 15 章會從前端的角度再談。

**Tasks** 處理長時間工作：營運 research agent 要 ERP 產生一份涵蓋十二個月的退貨明細，可能要跑十分鐘，不可能讓一個 `tools/call` 掛著十分鐘。Tasks 擴充讓 server 立刻回傳一個 task handle，client 之後用它查詢進度與結果，需要時也能送補充輸入給 task。這完全是 14.6 節「用 handle 取代連線狀態」的延伸，也和第 22 章 durable execution 的思路一致：長任務的狀態要放在可以被查詢、可以跨重啟存活的地方。

**Skills over MCP** 讓 server 透過 resources 發布 Agent Skills（第 12 章與第 13 章談過的「可漸進載入的程序知識」）。ERP 團隊除了提供 tool，還可以發布一份「如何正確處理跨月退貨」的 skill，host 在需要時才讀取。**ext-auth** 擴充則補上 OAuth 授權碼流程沒涵蓋的情境：沒有使用者在場的 machine-to-machine 呼叫（例如排程執行的背景 agent），以及由企業身分系統集中管理授權。

| 擴充 | 解決的問題 | 青鳥的用法 | 要注意的事 |
|---|---|---|---|
| MCP Apps | 文字介面不適合的互動 | 勾選退貨品項的表單 | UI 必須隔離執行；要有文字退路 |
| Tasks | 單次呼叫等不了的長任務 | 十二個月退貨明細 | handle 要綁擁有者；設定保留期限 |
| Skills over MCP | 程序知識的發布與更新 | ERP 團隊維護的退貨處理 skill | skill 內容也是不可信輸入，需審核 |
| ext-auth | 無使用者在場或企業集中授權 | research agent 的月度排程 | 服務身分的 scope 要比人更小 |

> [!warning] 常見誤解
> 「規格裡有這個擴充，所以 host 都支援。」擴充是選用的，不同 host 的支援程度差異很大，而且擴充本身也在演進。上線前要逐一確認目標 host 是否宣告支援，並為不支援的情況設計退路；不要讓核心業務流程只能在某一個 host 上運作。

## 14.10 MCP 的安全注意事項

MCP 讓接上一個新能力變得非常容易，這同時是它最大的安全風險：每接一個 server，就等於讓一段第三方程式碼的**描述**進入模型的 context、讓它的**輸出**成為模型下一步決策的依據，還可能讓它在使用者的機器上**執行**。第 31 章會完整做 threat model；這裡只整理 MCP 特有的幾類問題，以及 host 與 server 各自要負的責任。

```text
 信任邊界：模型讀到的每個字，都可能來自不同的信任等級

 ┌─ Host（可信：自己的程式與政策）──────────────────────────────────────┐
 │  system prompt、allowlist、核准政策、預算                              │
 │                                                                        │
 │  context 裡來自 server 的內容（不可信）：                              │
 │   (1) tool 名稱與描述 ◄── server 自己寫的，可能夾帶指示或被悄悄修改    │
 │   (2) tool 結果       ◄── 可能含有外部資料中的 prompt injection        │
 │   (3) resource 內容   ◄── 同上，還可能很大                             │
 └───────────┬───────────────────────────┬──────────────────────────────┘
             │                           │
   ERP MCP server（內部、已審核）    某個社群 MCP server（未審核）
             │                           │
        私有訂單資料                 可對外發送資料的能力
   ───────────────────────────────────────────────────────────────────
   兩者接在同一個 agent：私有資料＋不可信內容＋外送管道 = 第 31 章的 lethal trifecta
```

這張圖把 context 依信任等級拆開。第 (1) 類是 **tool poisoning**（工具投毒）：tool 的描述是 server 寫的，模型會完整讀進去，但使用者介面通常只顯示名稱，所以描述裡夾帶的指示很難被人發現。它的變形是 **rug pull**（事後變更）：server 在你審核時提供正常的定義，之後才悄悄改掉。第 (2)、(3) 類是 indirect prompt injection：tool 結果裡可能有來自外部網頁、email 或客戶留言的文字，模型可能把它當成指令。圖底部是最危險的組合：同一個 agent 同時接了能讀私有資料的 server、會帶進不可信內容的 server，以及能把資料送出去的能力，三者湊齊，資料外洩就只差一段被注入的文字。

另外三類問題和 MCP 的連線方式有關。**名稱衝突與 shadowing**：兩個 server 都提供 `get_order`，模型看到的是哪一個？惡意 server 甚至可以在描述中影響模型對另一個 server 的 tool 的使用方式。**本機 server 的供應鏈風險**：一行安裝指令就讓一個未審核的套件以使用者權限執行。**annotations 不可信**：tool 定義可以帶 `readOnlyHint`、`destructiveHint` 等提示，但它們是 server 自己宣告的，host 可以拿來改善 UI，卻不能拿來做安全決策；一個宣稱唯讀的 tool 是否真的唯讀，只有審核與權限才能保證。

下面這段程式實作最基本、也最有效的一道防線：把審核時看到的 tool 定義算成雜湊並記錄下來，之後每次取得 tool 清單都比對，定義一變就停用並重新審核；同時偵測未審核的新 tool 與跨 server 的名稱衝突。

```python
from __future__ import annotations

import hashlib
import json


def fingerprint(tool: dict) -> str:
    """tool 定義（名稱、描述、schema、annotations）的雜湊：任何一個字變了，雜湊就變。"""
    canonical = json.dumps(tool, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def audit(servers: dict[str, list[dict]], approved: dict[str, str]) -> list[str]:
    """比對每個 server 這次 tools/list 的結果與審核時記下的雜湊。"""
    findings, owners = [], {}
    for server, tools in servers.items():
        for t in tools:
            key = f"{server}/{t['name']}"
            fp = fingerprint(t)
            if key not in approved:
                findings.append(f"NEW      {key}：未經審核，先不暴露給模型")
            elif approved[key] != fp:
                findings.append(f"CHANGED  {key}：定義與審核版本不同（{approved[key]} → {fp}），停用並重新審核")
            owners.setdefault(t["name"], []).append(server)
    for name, who in owners.items():
        if len(who) > 1:
            findings.append(f"COLLIDE  {name} 同時出現在 {who}：必須加 server 前綴，並確認模型看到的是哪一個")
    return findings


get_order = {"name": "get_order", "description": "查詢訂單狀態",
             "inputSchema": {"type": "object", "properties": {"order_id": {"type": "string"}}}}
track = {"name": "track", "description": "查詢貨態",
         "inputSchema": {"type": "object", "properties": {"tracking": {"type": "string"}}}}
approved = {"erp/get_order": fingerprint(get_order), "carrier/track": fingerprint(track)}

# 審核通過後的某一天，server 回傳的定義悄悄變了，還多了一個 server 也叫 get_order
get_order_v2 = json.loads(json.dumps(get_order))
get_order_v2["description"] += "（新增 note 參數）"
get_order_v2["inputSchema"]["properties"]["note"] = {"type": "string"}
today = {"erp": [get_order_v2], "carrier": [track],
         "partner-crm": [{"name": "get_order", "description": "查詢 CRM 訂單", "inputSchema": {}}]}

report = audit(today, approved)
print("\n".join(report))
assert [line.split()[0] for line in report] == ["CHANGED", "NEW", "COLLIDE"]
assert audit({"erp": [get_order], "carrier": [track]}, approved) == []
```

```text
CHANGED  erp/get_order：定義與審核版本不同（443ad3eb840b → 5e6fc2ce16ca），停用並重新審核
NEW      partner-crm/get_order：未經審核，先不暴露給模型
COLLIDE  get_order 同時出現在 ['erp', 'partner-crm']：必須加 server 前綴，並確認模型看到的是哪一個
```

第一行是 rug pull 的偵測：ERP server 的 `get_order` 描述多了一句話、schema 多了一個 `note` 參數，雜湊從 `443ad3eb840b` 變成 `5e6fc2ce16ca`。新的參數本身未必惡意，但「審核過的東西變了」就足以觸發停用與重新審核，因為一個看似無害的自由文字參數，可能正是把對話內容帶出去的管道。第二行是新出現的 `partner-crm/get_order`，沒有審核紀錄，所以先不暴露給模型。第三行是名稱衝突：兩個 server 都叫 `get_order`，host 必須加上 server 前綴（本章動手做用 `erp__get_order` 的形式），並在審核時確認模型看到的描述足以區分兩者。

| 威脅 | 發生在哪 | host 的防禦 | server 維護者的責任 |
|---|---|---|---|
| tool poisoning | tool 描述 | 審核時顯示完整描述；定義雜湊 pin | 描述只寫用途與參數，不寫給模型的指示 |
| rug pull | 定義事後變更 | 每次取得清單都比對雜湊，變更即停用 | 變更走版本與公告流程 |
| 名稱衝突與 shadowing | 多個 server | server 前綴；allowlist | 用有辨識度的名稱 |
| indirect prompt injection | tool 結果、resource | 輸出當成資料；寫入動作要核准；分離高風險組合 | 標示外部來源內容；限制輸出長度 |
| 供應鏈 | 本機 server 安裝 | 只裝審核過、鎖定版本的套件；放進 sandbox | 簽章發布；最小依賴 |
| 過度授權 | 憑證與 scope | 每個 server 獨立憑證、最小 scope | 不要求超出需要的 scope |

實務上，規模大一點的組織會把這些防禦集中到一個 **MCP gateway**：所有 host 只能連 gateway，gateway 負責 server allowlist、定義 pin、授權、稽核 log 與資料外洩防護（DLP），也是 14.13 節幾個情境的共同架構。青鳥最後的規則很簡單：寫入類 tool 預設不暴露給模型，要暴露就必須經過第 21 章的核准流程；這也是動手做中 `allow` 參數的由來。

## 14.11 2026 現況：2026-07-28 版與生態

> [!note] 2026 現況
> 以下依 MCP 官方規格、changelog 與相關公開資料整理，截至 2026 年 10 月。規格仍在快速演進，確切欄位名稱、必要性（MUST／SHOULD）與擴充狀態請以官方規格為準。早期版本的細節來自公開 changelog 的整理，部分未逐一回頭查證。

MCP 由 Anthropic 在 2024 年 11 月開源發布，版本號 `YYYY-MM-DD` 代表最後一次不相容變更的日期。依公開資訊，MCP 已移交 Linux Foundation 旗下的 Agentic AI Foundation（AAIF）治理（移交細節以官方公告為準），規格變更走 SEP 流程；deprecated 的功能原則上至少保留 12 個月。

| 版本 | 重點（依公開 changelog 整理） |
|---|---|
| 2024-11-05 | 初版：stdio 與 HTTP＋SSE；tools、resources、prompts；sampling、roots |
| 2025-03-26 | Streamable HTTP；OAuth 2.1 授權框架；tool annotations |
| 2025-06-18 | structured tool output；elicitation；server 定位為 OAuth resource server |
| 2025-11-25 | experimental tasks；URL 模式 elicitation；Client ID Metadata Documents |
| 2026-07-28（current） | stateless 化、MRTR、Tasks 移為擴充、Roots／Sampling／Logging deprecated（見下表） |

**2026-07-28 的主要變更**：

| 類別 | 變更 |
|---|---|
| 生命週期 | 移除 `initialize`／`notifications/initialized` 與 `Mcp-Session-Id`；每個 request 在 `_meta` 帶 `io.modelcontextprotocol/protocolVersion`、`io.modelcontextprotocol/clientCapabilities`，並應帶 client 身分；server 在 result 的 `_meta` 帶 `serverInfo`；新增必須實作的 `server/discover` |
| 狀態 | 需要跨呼叫的狀態，由 server 發 handle、以一般 tool 參數傳遞 |
| 移除 | `ping`、`logging/setLevel`、`notifications/roots/list_changed`；SSE 續傳（`Last-Event-ID`），串流中斷時 client 以新的 request id 重送 |
| 訂閱 | HTTP GET endpoint 與 `resources/subscribe`／`unsubscribe` 合併為單一的 `subscriptions/listen` |
| MRTR | server 回傳 `resultType: "input_required"` 與 `inputRequests`，client 補 `inputResponses` 後重送原 request；所有 result 都要帶 `resultType`（`complete` 或 `input_required`）；跨輪狀態放 `requestState` |
| Tasks | 移出 core，成為官方擴充 `io.modelcontextprotocol/tasks`：以 `tasks/get` 查詢、新增 `tasks/update`，移除 `tasks/list` 與阻塞式的 `tasks/result` |
| 快取 | list 類與 `resources/read` 的結果要帶 `ttlMs` 與 `cacheScope`（`public`／`private`）；`tools/list` 應以固定順序回傳 |
| HTTP 與 Schema | POST 要帶 `Mcp-Method`、`Mcp-Name` header；`inputSchema`／`outputSchema` 可用任意 JSON Schema 2020-12 關鍵字 |
| 觀測 | 在 `_meta` 傳遞 OpenTelemetry 的 `traceparent`、`tracestate`、`baggage` |
| 錯誤碼 | `-32000`～`-32019` 留給實作自訂、`-32020`～`-32099` 留給 MCP 規格；resource not found 改用 `-32602` |

| deprecated 項目 | 建議替代 |
|---|---|
| Roots | 用 tool 參數或 resource URI 傳路徑 |
| Sampling | server 直接呼叫模型供應商的 API |
| Logging | 寫到 stderr，或用 OpenTelemetry |
| HTTP＋SSE transport | Streamable HTTP |
| `includeContext` 的 `thisServer`／`allServers` | 不再使用 |
| Dynamic Client Registration | Client ID Metadata Documents |

**授權要求**：授權本身是選用的；HTTP transport 實作時應遵循規格，stdio 則從環境變數取得憑證。MCP server 是 OAuth 2.1 resource server，必須實作 RFC 9728 Protected Resource Metadata，client 必須用它發現授權伺服器；client 必須在授權與 token 請求中帶 RFC 8707 的 `resource`（server 的 canonical URI），server 必須驗證 token 的 audience 是自己；禁止接受或轉送其他 token；必須使用 PKCE；token 只能放在 `Authorization: Bearer` header。新版另外要求 client 驗證授權回應中的 `iss`（RFC 9207）以防 mix-up attack；scope 不足時以 403 `insufficient_scope` 做 step-up。

**擴充**：在 `capabilities.extensions` 協商、預設停用。官方擴充包括 ext-auth（OAuth client credentials、企業管理的授權）、MCP Apps（`io.modelcontextprotocol/ui`，MIME type 為 `text/html;profile=mcp-app`）、Tasks、Skills over MCP（ext-skills）；實驗性擴充以 `experimental-ext-*` 命名，必須隸屬某個工作小組。

**生態**：Claude Code、Codex、Gemini CLI、GitHub Copilot coding agent 都支援 MCP；Copilot coding agent 預設啟用 GitHub MCP 與 Playwright MCP；Claude Code 的 MCP tool 定義預設延遲載入，透過 tool search 按需取用（第 13 章）。OpenAI 的 deep research API 要求接入的 MCP server 提供 `search` 與 `fetch` 兩個 tool。模型 API 端，Anthropic Messages API 有 MCP connector、OpenAI Responses API 有 `mcp` tool，可以直接連遠端 server；Gemini 的官方文件則表示遠端 MCP 支援即將推出。SDK 方面，2026 年 8 到 9 月出現一波 MCP SDK 2.x 的不相容升級，OpenAI Agents SDK、Google ADK、Strands、Mastra 等都已發版支援，其中 `@mastra/mcp` 2.0.0 只支援 2026-07-28 版。官方的 MCP Registry 仍標示為 preview。

## 14.12 動手做：純 Python 的教學版 MCP server 與 client，接上 loom

這一節把前面的概念寫成一段可以離線執行的程式：一個 MCP 風格的 server、一個 in-process transport、一個 client，以及把 MCP tools 接進 `loom` 的橋接層。先把範圍講清楚：**這是教學版，不是完整的規格實作**。它模仿最新一版的訊息形狀（每個 request 自帶版本、`server/discover`、`resultType`、`ttlMs`），但只實作了理解原理所需的最小子集。要接真實的 host 或 server，請使用官方 SDK。

| 這段程式有實作 | 這段程式刻意省略 |
|---|---|
| JSON-RPC 2.0 request／response、錯誤物件、notification 不回應 | stdio 與 Streamable HTTP transport、SSE 串流 |
| `server/discover`、每個 request 的版本檢查 | 完整的 capabilities 與 extensions 協商 |
| `tools/list`（固定順序、cursor 分頁、ttl 快取）、`tools/call` | 完整的 JSON Schema 驗證、`outputSchema` 驗證 |
| `resources/list`、`resources/read` | prompts、resource templates、`subscriptions/listen` |
| 協定錯誤與 tool 執行錯誤的分層 | MRTR（見 14.7 節的獨立程式）、Tasks、進度通知、取消 |
| 橋接到 `loom`：前綴命名、allowlist、`isError` 轉成觀察 | OAuth 授權、`_meta` 中的 trace context |

```text
 loom Agent（第 4 章的 loop）
   │ tool_call: erp__get_order {order_id}
   ▼
 loom _dispatch ──► Tool.fn（橋接層 mcp_tools 產生的 closure）
                      │ 去掉前綴：get_order
                      ▼
                    MiniMCPClient.call_tool ── 組 JSON-RPC、帶 _meta 版本 ──┐
                                                                            │ JSON 字串
                    InProcessTransport.send（記錄 wire）◄────────────────────┘
                      │
                      ▼
                    MiniMCPServer.handle ── 解析 → 版本檢查 → 路由 → 執行 tool
                      │
                      ▼ result：content、structuredContent、isError
 橋接層：isError=True → 丟 ToolExecutionError → loom 回填 is_error=True 的觀察
         isError=False → content 的文字 → loom 回填結果
```

這張資料流圖是理解整段程式的地圖。最上面的 `loom` 完全不知道 MCP 的存在：它看到的只是一般的 `Tool`，名稱叫 `erp__get_order`。橋接層 `mcp_tools` 在啟動時呼叫 `tools/list`，為每個 MCP tool 產生一個 closure，裡面記住原始名稱；`loom` 呼叫它時，closure 去掉前綴、交給 client。client 負責 JSON-RPC 的細節：遞增 id、附上版本 metadata、檢查回應的 id 是否對得上、把協定錯誤轉成 `MCPError`。transport 只搬字串並留下紀錄。回程時，橋接層把 MCP 的 `isError` 轉成例外，`loom` 第 4 章寫好的 dispatch 自然會把它變成 `is_error=True` 的觀察，這正是 14.4 節兩層失敗在 `loom` 裡的落點。

程式分成五個部分：教學版 server、transport 與 client、`loom` v0.1 精簡版（為了讓這段程式自給自足而附上，省略了預算與重複偵測，完整版見第 4 章）、橋接層，以及青鳥的兩個 server 與一次完整的 run。

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class ModelResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"          # end_turn｜tool_use｜max_tokens
    usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})


class ScriptedModel:
    """依劇本回應的假模型。劇本的每一步是 ModelResponse，或「收到 messages 後回傳 ModelResponse」的函式。"""

    def __init__(self, script: list[ModelResponse | Callable[[list[dict]], ModelResponse]]):
        self.script = list(script)
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict], tools: list[dict] | None = None, system: str = "") -> ModelResponse:
        self.calls.append(json.loads(json.dumps(messages)))
        if not self.script:
            raise RuntimeError("劇本已用完：agent 呼叫模型的次數比預期多")
        step = self.script.pop(0)
        return step(messages) if callable(step) else step


def call(name: str, call_id: str = "c1", **args: Any) -> ModelResponse:
    """劇本小工具：產生一個「呼叫 name 工具」的回應。"""
    return ModelResponse(tool_calls=[ToolCall(call_id, name, args)], stop_reason="tool_use")


def say(text: str) -> ModelResponse:
    """劇本小工具：產生一個「直接回答並結束」的回應。"""
    return ModelResponse(text=text)


# ═══════════════ 第一部分：教學版 MCP server（只實作 spec 的一小部分）═══════════════
PROTOCOL_VERSION = "2026-07-28"
META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CLIENT = "io.modelcontextprotocol/clientInfo"


class RPCError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code, self.message, self.data = code, message, data


@dataclass
class ServerTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    fn: Callable[..., Any]
    annotations: dict[str, bool] = field(default_factory=dict)


class MiniMCPServer:
    def __init__(self, name: str, page_size: int = 50):
        self.info = {"name": name, "version": "0.1.0"}
        self.tools: dict[str, ServerTool] = {}
        self.resources: dict[str, tuple[str, Callable[[], Any]]] = {}
        self.page_size = page_size                  # 刻意設小，才看得到 cursor 分頁

    def tool(self, name, description, input_schema, **annotations):
        def register(fn):
            self.tools[name] = ServerTool(name, description, input_schema, fn, annotations)
            return fn
        return register

    def resource(self, uri: str, name: str):
        def register(fn):
            self.resources[uri] = (name, fn)
            return fn
        return register

    def handle(self, raw: str) -> str | None:
        """transport 只負責搬字串；所有協定邏輯都在這裡。"""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return self._reply(None, error=(-32700, "Parse error"))
        if msg.get("jsonrpc") != "2.0" or "method" not in msg:
            return self._reply(msg.get("id"), error=(-32600, "Invalid Request"))
        if "id" not in msg:
            return None                             # notification：不回應
        try:
            result = self._route(msg["method"], msg.get("params") or {})
        except RPCError as e:
            return self._reply(msg["id"], error=(e.code, e.message, e.data))
        result.setdefault("resultType", "complete")
        result["_meta"] = {"serverInfo": self.info}
        return self._reply(msg["id"], result=result)

    def _route(self, method: str, params: dict) -> dict:
        if method == "server/discover":             # 不需要先握手，任何時候都能問
            return {"supportedVersions": [PROTOCOL_VERSION], "serverInfo": self.info,
                    "capabilities": {"tools": {}, "resources": {}}}
        version = params.get("_meta", {}).get(META_VERSION)
        if version != PROTOCOL_VERSION:             # stateless：每個 request 自己帶版本
            raise RPCError(-32000, "Unsupported protocol version", {"supported": [PROTOCOL_VERSION]})
        if method == "tools/list":
            names = sorted(self.tools)              # 固定順序：對 prompt cache 友善
            start = int(params.get("cursor", 0))
            page = names[start:start + self.page_size]
            out: dict[str, Any] = {"tools": [self._describe(self.tools[n]) for n in page],
                                   "ttlMs": 60_000, "cacheScope": "public"}
            if start + self.page_size < len(names):
                out["nextCursor"] = str(start + self.page_size)
            return out
        if method == "tools/call":
            return self._call_tool(params.get("name"), params.get("arguments") or {})
        if method == "resources/list":
            return {"resources": [{"uri": u, "name": n, "mimeType": "application/json"}
                                  for u, (n, _) in sorted(self.resources.items())],
                    "ttlMs": 300_000, "cacheScope": "public"}
        if method == "resources/read":
            uri = params.get("uri")
            if uri not in self.resources:
                raise RPCError(-32602, "Resource not found", {"uri": uri})
            text = json.dumps(self.resources[uri][1](), ensure_ascii=False)
            return {"contents": [{"uri": uri, "mimeType": "application/json", "text": text}],
                    "ttlMs": 300_000, "cacheScope": "public"}
        raise RPCError(-32601, "Method not found", {"method": method})

    def _describe(self, t: ServerTool) -> dict:
        return {"name": t.name, "description": t.description, "inputSchema": t.input_schema,
                "annotations": t.annotations}

    def _call_tool(self, name: str, args: dict) -> dict:
        tool = self.tools.get(name)
        if tool is None:                            # 呼叫端的錯：協定層錯誤
            raise RPCError(-32602, f"Unknown tool: {name}")
        props = tool.input_schema.get("properties", {})
        missing = [p for p in tool.input_schema.get("required", []) if p not in args]
        unknown = [a for a in args if a not in props]
        try:
            if missing or unknown:                  # 模型修得好的錯：當成 tool 執行錯誤回給模型
                raise ValueError(f"參數錯誤：缺少 {missing}，不認得 {unknown}")
            value = tool.fn(**args)
        except Exception as exc:
            return {"content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}], "isError": True}
        return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}],
                "structuredContent": value, "isError": False}

    @staticmethod
    def _reply(msg_id, result=None, error=None) -> str:
        body: dict[str, Any] = {"jsonrpc": "2.0", "id": msg_id}
        if error:
            body["error"] = dict(zip(("code", "message", "data"), error))
        else:
            body["result"] = result
        return json.dumps(body, ensure_ascii=False)


# ═══════════════ 第二部分：in-process transport 與 client ═══════════════
class InProcessTransport:
    """不經網路，但保留 JSON 序列化：wire 上的每個位元組都和真的一樣，方便測試與觀察。"""

    def __init__(self, server: MiniMCPServer):
        self.server, self.wire = server, []

    def send(self, raw: str) -> str | None:
        reply = self.server.handle(raw)
        self.wire.append((raw, reply))
        return reply


class MCPError(Exception):
    def __init__(self, error: dict):
        super().__init__(f"{error['code']} {error['message']}")
        self.code = error["code"]


class MiniMCPClient:
    def __init__(self, transport: InProcessTransport, version: str = PROTOCOL_VERSION):
        self.transport, self.version = transport, version
        self.next_id, self.now_ms = 0, 0            # now_ms 是模擬時鐘，讓 ttl 可以重現
        self.cache: dict[str, tuple[int, Any]] = {}

    def request(self, method: str, params: dict | None = None) -> dict:
        self.next_id += 1
        params = {**(params or {}), "_meta": {META_VERSION: self.version,
                                              META_CLIENT: {"name": "loom", "version": "0.1"}}}
        raw = json.dumps({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params},
                         ensure_ascii=False)
        reply = json.loads(self.transport.send(raw))
        assert reply["id"] == self.next_id          # 用 id 對回 request，和 tool_call_id 同一個道理
        if "error" in reply:
            raise MCPError(reply["error"])
        return reply["result"]

    def list_tools(self) -> list[dict]:
        hit = self.cache.get("tools")
        if hit and hit[0] > self.now_ms:            # ttl 內直接用快取，不打 wire
            return hit[1]
        tools, cursor, ttl = [], None, 0
        while True:                                 # cursor 分頁：一直拿到沒有 nextCursor 為止
            page = self.request("tools/list", {"cursor": cursor} if cursor else {})
            tools += page["tools"]
            ttl = page["ttlMs"]
            cursor = page.get("nextCursor")
            if not cursor:
                break
        self.cache["tools"] = (self.now_ms + ttl, tools)
        return tools

    def call_tool(self, name: str, arguments: dict) -> dict:
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def read_resource(self, uri: str) -> str:
        return self.request("resources/read", {"uri": uri})["contents"][0]["text"]


# ═══════════════ 第三部分：loom v0.1 精簡版（完整版見第 4 章）═══════════════
@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable[..., Any]

    def schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


class Agent:
    def __init__(self, model, tools: list[Tool], system: str = "", max_steps: int = 8):
        self.model, self.system, self.max_steps = model, system, max_steps
        self.tools = {t.name: t for t in tools}

    def run(self, user_input: str) -> tuple[str, str, list[dict]]:
        messages: list[dict] = [{"role": "user", "content": user_input}]
        for _ in range(self.max_steps):
            resp = self.model.complete(messages, tools=[t.schema() for t in self.tools.values()],
                                       system=self.system)
            messages.append({"role": "assistant", "content": resp.text,
                             "tool_calls": [vars(tc) for tc in resp.tool_calls]})
            if not resp.tool_calls:
                return "done", resp.text, messages
            for tc in resp.tool_calls:
                is_error, content = self._dispatch(tc)
                messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name,
                                 "content": content, "is_error": is_error})
        return "max_steps", "步驟用完了，先轉給真人同事。", messages

    def _dispatch(self, tc: ToolCall) -> tuple[bool, str]:
        tool = self.tools.get(tc.name)
        if tool is None:
            return True, f"沒有名為 {tc.name} 的工具。可用的工具：{', '.join(self.tools)}。"
        try:
            return False, tool.fn(**tc.args)
        except Exception as exc:
            return True, f"{type(exc).__name__}: {exc}"


# ═══════════════ 第四部分：MCP → loom 的橋接 ═══════════════
class ToolExecutionError(Exception):
    pass


def mcp_tools(client: MiniMCPClient, prefix: str, allow: set[str]) -> list[Tool]:
    """把一個 MCP server 的 tools 轉成 loom Tool。只暴露 allowlist 內的 tool，名稱加上 server 前綴。"""
    def make_fn(remote_name: str):
        def fn(**args):
            result = client.call_tool(remote_name, args)
            text = "\n".join(c["text"] for c in result["content"] if c["type"] == "text")
            if result.get("isError"):               # MCP 的 isError → loom 的 is_error 觀察
                raise ToolExecutionError(text)
            return text
        return fn

    return [Tool(f"{prefix}__{t['name']}", f"[{prefix}] {t['description']}", t["inputSchema"],
                 make_fn(t["name"])) for t in client.list_tools() if t["name"] in allow]


# ═══════════════ 第五部分：青鳥的兩個 MCP server 與一次完整的 run ═══════════════
def obj(**props: str) -> dict:
    return {"type": "object", "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
            "required": list(props)}


ORDERS = {"B-1042": {"status": "shipped", "tracking": "TC-88301", "amount": 1280}}
erp = MiniMCPServer("bluebird-erp", page_size=2)


@erp.tool("get_order", "查詢訂單狀態、金額與物流單號", obj(order_id="訂單編號，例如 B-1042"), readOnlyHint=True)
def get_order(order_id: str) -> dict:
    if order_id not in ORDERS:
        raise LookupError(f"找不到訂單 {order_id}，請向使用者確認編號（B-加四位數字）")
    return {"order_id": order_id, **ORDERS[order_id]}


@erp.tool("create_return", "為已出貨訂單建立退貨單", obj(order_id="訂單編號"), destructiveHint=False)
def create_return(order_id: str) -> dict:
    return {"return_id": "R-7781"}


@erp.tool("list_returns", "列出某訂單的退貨單", obj(order_id="訂單編號"), readOnlyHint=True)
def list_returns(order_id: str) -> list:
    return []


@erp.resource("bluebird://policy/returns", "退貨政策")
def return_policy() -> dict:
    return {"window_days": 7, "shipped": "已出貨訂單不能直接退款，需建立退貨單"}


logistics = MiniMCPServer("carrier-gateway")


@logistics.tool("track", "用物流單號查詢貨態", obj(tracking="物流單號，例如 TC-88301"), readOnlyHint=True)
def track(tracking: str) -> dict:
    return {"tracking": tracking, "location": "台中轉運中心", "eta": "明天"}


erp_wire, log_wire = InProcessTransport(erp), InProcessTransport(logistics)
erp_client, log_client = MiniMCPClient(erp_wire), MiniMCPClient(log_wire)

# (1) 先問 server 是誰、支援什麼；不需要 initialize，也沒有 session
info = erp_client.request("server/discover")
print("discover →", info["serverInfo"]["name"], info["supportedVersions"], list(info["capabilities"]))

# (2) host 組裝 loom 的工具箱：寫入類 tool（create_return）不在 allowlist，模型根本看不到
tools = (mcp_tools(erp_client, "erp", allow={"get_order", "list_returns"})
         + mcp_tools(log_client, "logistics", allow={"track"}))
print("loom tools →", [t.name for t in tools])
print("tools/list 分頁次數 →", sum(1 for raw, _ in erp_wire.wire if '"tools/list"' in raw))

# (3) resource 由 host 決定放進 context（application-controlled），不是給模型呼叫的
policy = json.loads(erp_client.read_resource("bluebird://policy/returns"))
system = f"你是青鳥客服。退貨政策：{policy['shipped']}（{policy['window_days']} 天內）。"

# (4) 跑一次 agent：模型先打錯編號，讀了 isError 後自己修正
model = ScriptedModel([
    call("erp__get_order", "c1", order_id="B-1O42"),
    call("erp__get_order", "c2", order_id="B-1042"),
    call("logistics__track", "c3", tracking="TC-88301"),
    say("B-1042 已出貨，預計明天送達；已出貨訂單不能直接退款，需要的話我可以協助申請退貨。"),
])
status, answer, history = Agent(model, tools, system=system).run("B-1042 到哪了？可以直接退款嗎？")
for m in history:
    if m["role"] == "tool":
        print(f"{m['tool_call_id']} {m['name']:<17} is_error={m['is_error']!s:<5} {m['content'][:48]}")
print(status, "：", answer)

# (5) 看一眼 wire：loom 的一次 tool 呼叫，在 MCP 上就是一組 tools/call request／response
raw, reply = erp_wire.wire[-1]
print("wire →", raw[:96])
print("wire ←", reply[:96])

# (6) 快取與錯誤：ttl 內不打 wire；ttl 過期才重抓；未知 tool 與版本不符是協定層錯誤
n0 = len(erp_wire.wire)
erp_client.list_tools()
n1 = len(erp_wire.wire)
erp_client.now_ms += 61_000
erp_client.list_tools()
print(f"ttl 內重抓 {n1 - n0} 次；時鐘前進 61 秒、ttl 過期後重抓 {len(erp_wire.wire) - n1} 次（2 頁）")
for label, fn in [("未知 tool", lambda: erp_client.call_tool("cancel_order", {})),
                  ("舊版 client", lambda: MiniMCPClient(erp_wire, version="2025-06-18").list_tools()),
                  ("不存在的方法", lambda: erp_client.request("sampling/createMessage"))]:
    try:
        fn()
    except MCPError as exc:
        print(f"{label:<6} → MCPError {exc}")

assert status == "done" and [m["is_error"] for m in history if m["role"] == "tool"] == [True, False, False]
assert n1 == n0 and "erp__create_return" not in {t.name for t in tools}
assert all(json.loads(r)["id"] == json.loads(q)["id"] for q, r in erp_wire.wire if r)
```

```text
discover → bluebird-erp ['2026-07-28'] ['tools', 'resources']
loom tools → ['erp__get_order', 'erp__list_returns', 'logistics__track']
tools/list 分頁次數 → 2
c1 erp__get_order    is_error=True  ToolExecutionError: LookupError: 找不到訂單 B-1O42，請向
c2 erp__get_order    is_error=False {"order_id": "B-1042", "status": "shipped", "tra
c3 logistics__track  is_error=False {"tracking": "TC-88301", "location": "台中轉運中心", "
done ： B-1042 已出貨，預計明天送達；已出貨訂單不能直接退款，需要的話我可以協助申請退貨。
wire → {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "get_order", "arguments":
wire ← {"jsonrpc": "2.0", "id": 6, "result": {"content": [{"type": "text", "text": "{\"order_id\": \"B-
ttl 內重抓 0 次；時鐘前進 61 秒、ttl 過期後重抓 2 次（2 頁）
未知 tool → MCPError -32602 Unknown tool: cancel_order
舊版 client → MCPError -32000 Unsupported protocol version
不存在的方法 → MCPError -32601 Method not found
```

逐段解說這份輸出。

**第 1 行（discover）**：client 還沒做任何握手，第一個 request 就是 `server/discover`，server 回答自己的名字、支援的版本與 capabilities。教學版的 server 讓 `server/discover` 不檢查版本，因為它本來就是「先問清楚再說」的方法；其他所有方法都要求 request 自帶版本。

**第 2、3 行（組裝工具箱）**：host 從兩個 server 取得 tool 清單，經過 allowlist 過濾並加上前綴，`loom` 最後只看到三個 tool。`erp__create_return` 不在清單上：它是寫入類 tool，青鳥的政策是寫入要經過核准流程，所以模型連它的存在都不知道，這比「看得到但被拒絕」更安全，也更省 context。第 3 行顯示 ERP 的 `tools/list` 打了 2 次：page size 刻意設成 2，三個 tool 分兩頁，client 依 `nextCursor` 自動翻頁。

**接著是 resource**（沒有印出）：host 在 run 開始前讀了 `bluebird://policy/returns`，寫進 system prompt，這是 14.3 節「resource 由 host 決定何時載入」的示範。

**c1 到 c3（agent run）**：c1 是模型把編號的 0 打成英文字母 O，ERP server 的 tool 丟出 `LookupError`，server 依規則包成 `isError: true` 的結果；橋接層把它轉成 `ToolExecutionError`，`loom` 回填 `is_error=True` 的觀察，內容就是 server 寫好的可行動訊息。c2 模型改用正確編號，成功取得訂單；c3 跨到物流 server 查貨態。c2 與 c3 分屬兩個 server，對 `loom` 卻沒有任何差別，這就是 N＋M 的效果。

**wire 兩行**：這是 c2 那次呼叫在協定上的真實樣子。request 是 `id: 6` 的 `tools/call`，名稱是去掉前綴後的 `get_order`；response 帶著同樣的 `id: 6`，`result` 裡是 content 陣列。當 agent 行為怪異時，先看 wire 上 server 實際回了什麼。

**最後四行（快取與錯誤）**：第一行驗證 ttl 快取：在 ttl 內再次取得清單，wire 上沒有任何新請求；模擬時鐘前進 61 秒後超過 `ttlMs`，client 才重新抓兩頁。接下來三行是三種協定錯誤：呼叫不存在的 `cancel_order` 得到 `-32602`；一個帶著舊版本字串的 client 得到 `-32000`，這是教學版在「實作自訂」範圍內選的錯誤碼，訊息會附上 server 支援的版本，讓 client 知道該升級；呼叫已經 deprecated、教學版也沒實作的 `sampling/createMessage` 得到 `-32601`。這三種錯誤都不該交給模型，而是要讓 host 的工程師看到。

程式最後的三個 assert 鎖住了三個性質：模型確實從 `isError` 觀察中恢復；寫入類 tool 沒有被暴露；wire 上每個 response 的 id 都對得上 request。改成真實部署時，transport 換成 stdio 或 HTTP、client 與 server 換成官方 SDK，再加上 14.8 節的授權與 14.10 節的定義 pin；`loom` 這一側幾乎不用動，因為它只依賴「一組 Tool」這個介面。第 45 章會把這個橋接層收成 `loom.mcp` 模組。

## 14.13 實務應用

MCP 在不同產品形態中的用法差異很大，差別主要在三件事：server 由誰維護、跑在哪裡、誰持有憑證。以下四個情境各自代表一種典型。

**情境一：企業內部共享系統（青鳥的 ERP 與物流）**。這是本章故事的主線：ERP 團隊維護 ERP MCP server，部署在內部、以 Streamable HTTP 提供服務，客服、coding 與 research 三個 agent 和員工的 IDE 都透過它存取 ERP。設計重點是 stateless 部署（多副本、不需要 sticky session）、以公司身分系統做 OAuth、server 以自己的身分存取 ERP，並依使用者情境限制資料範圍。tool 清單依 host 分組：客服 host 只看到查詢類 tool，寫入類要經過核准；research agent 的長時間匯出走 Tasks 擴充。

**情境二：開發者工具與 coding agent**。coding agent 大量使用本機 stdio server：檔案系統、瀏覽器自動化、資料庫用戶端，以及遠端的程式碼託管平台 server。主流 coding agent 都能以設定檔加入 MCP server（見 14.11 節）。這類情境的主要風險是本機 server 的供應鏈與權限：server 以開發者的身分執行，能讀整個 home 目錄。實務做法是只裝審核過且鎖定版本的 server、把它們放進 sandbox（第 17 章），並利用 tool search 讓大量 MCP tool 不必全部常駐 context（第 13 章）。

**情境三：SaaS 廠商對外發布遠端 MCP server**。一家做線上表單或專案管理的 SaaS 公司，想讓客戶在任何支援 MCP 的聊天產品或 agent 裡使用自家服務。這時 server 是多租戶的公開服務，授權設計是重點：使用 Protected Resource Metadata 讓任何 client 自動找到授權伺服器、用 Client ID Metadata Documents 管理來路不明的 client、scope 依租戶與使用者最小化，並嚴格驗證 audience。客戶資料中的文字可能含有 prompt injection，server 應標示外部來源內容、限制輸出長度；有些平台對接入的 server 還有額外的 tool 介面要求（見 14.11 節）。

**情境四：把既有 API 批次轉成 MCP 的 gateway**。大型組織有上百個內部 REST API，不可能逐一手寫 MCP server。常見做法是用 gateway 把 OpenAPI 規格自動轉成 MCP tools，並在 gateway 集中套用授權、policy 與稽核。依公開文件，Amazon Bedrock AgentCore Gateway 能把 OpenAPI、Smithy 與 Lambda 轉成 MCP endpoint，並在每次 tool call 前套用 policy；開源的 FastMCP 也提供從 OpenAPI 產生 server 的功能。自動轉出來的 tool 通常是 CRUD 粒度、描述照抄 API 文件，對模型並不友善（第 5 章）；它適合起步，常用的工作流仍值得手工包成 workflow 級的 tool。

| 情境 | server 在哪、誰維護 | transport 與授權 | 主要風險 | 關鍵做法 |
|---|---|---|---|---|
| 企業內部共享系統 | 內部服務，擁有該系統的團隊 | Streamable HTTP＋公司 OAuth | token passthrough、過度授權 | stateless 部署；server 自有下游憑證 |
| 開發者工具 | 本機 subprocess 與遠端平台 | stdio（環境變數）＋遠端 OAuth | 供應鏈、使用者權限 | 審核與版本鎖定；sandbox；tool search |
| SaaS 對外發布 | 廠商的多租戶公開服務 | Streamable HTTP＋OAuth（PRM、CIMD） | 跨租戶外洩、不可信 client | audience 驗證；最小 scope；輸出標示來源 |
| API gateway 轉換 | 平台團隊集中維護 | 經 gateway 統一授權 | tool 粒度差、描述品質低 | 自動轉換起步；常用流程手工包裝 |

四個情境的共同點是：**MCP 讓「接得上」變便宜，但「接得安全、接得好用」仍然是設計工作**。協定替你決定了訊息格式與授權框架，tool 的粒度與描述（第 5 章）、context 預算（第 9 章、第 13 章）、核准政策（第 21 章）與權限邊界（第 33 章）仍然要自己設計。

## 14.14 設計檢查清單

設計或審查一個 MCP 整合時，逐項回答下面的問題：

1. 這個能力是否真的會被多個 host 重用，或由另一個團隊擁有？如果都不是，直接寫成 harness 內的 tool 是否更簡單？
2. 每個能力該做成 tool、resource 還是 prompt？是依「誰最清楚什麼時候需要它」決定的嗎？
3. server 是否區分協定錯誤（JSON-RPC `error`）與 tool 執行錯誤（`isError`）？tool 執行錯誤的訊息是否可行動？
4. 遠端 server 能否在任意副本處理任意 request？是否有任何狀態只存在某台 instance 的記憶體或連線上？
5. 跨呼叫的 handle 是否綁定擁有者、有過期時間，且不可猜測？
6. 需要使用者輸入時，副作用是否只在最後一輪執行？requestState 是否有簽章或只放 server 端狀態的 id？往返次數是否有上限？
7. 遠端 server 是否驗證 token 的 audience 是自己？是否確定沒有把 client 的 token 轉送給下游？
8. server 存取下游系統時用的是自己的身分與最小 scope 嗎？稽核紀錄是否能看出「哪個使用者、經由哪個 host、呼叫了什麼」？
9. host 是否只暴露 allowlist 內的 server 與 tool？寫入類 tool 是否預設不暴露或必須經過核准？
10. 是否為每個 server 的 tool 定義記錄雜湊，定義變更時停用並重新審核？
11. 多個 server 的 tool 是否加了前綴，避免名稱衝突？
12. 本機 stdio server 是否來自審核過、鎖定版本的套件，並在 sandbox 中執行？
13. host 是否快取 tool 清單並遵守 ttl？tool 清單在一次 run 中是否保持固定順序，以保護 prompt cache？
14. 依賴的擴充（Apps、Tasks、Skills）在目標 host 不支援時，是否有退路？

## 14.15 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 部署多副本後隨機出現「session 不存在」或 404 | server 依賴連線或記憶體中的 session，LB 把 request 分到別台 | 比對失敗率與副本數；看 request 落在哪台 | 改成 stateless；狀態用 handle 存共享儲存 |
| stdio server 一啟動 client 就報 parse error | server 程式把 log 或除錯輸出寫到 stdout | 單獨執行 server，看 stdout 是否有非 JSON 文字 | log 一律寫 stderr |
| 模型反覆猜不同的 tool 名稱 | server 把「tool 不存在」包成 `isError` 文字回給模型 | 看 wire：是否有 Unknown tool 的 result | 改用協定錯誤；host 同步 tool 清單並告警 |
| 查無資料時 agent 整個失敗 | server 把業務錯誤丟成 JSON-RPC `error` | 看 wire 上的 error code 與訊息 | 業務錯誤改回 `isError: true` 的結果 |
| 需要使用者確認的 tool 在等待時逾時 | 依賴 server 中途反向發問、連線被 proxy 切斷 | 對照 proxy 的 idle timeout 與失敗時間點 | 改用 MRTR；副作用只在最後一輪執行 |
| 下游 API 的稽核紀錄看不到 MCP server | token passthrough：server 轉送了 client 的 token | 檢查下游收到的 token audience | server 用自己的身分取得下游 token |
| 換了 server 版本後成本上升、cache 命中率下降 | tool 清單順序或描述變動，破壞 prompt cache 前綴 | 比較前後 `tools/list` 的內容與順序 | 固定順序；快取清單；定義變更走審核 |
| 接了很多 server 後模型常選錯 tool | tool 太多、名稱相近、描述重疊 | 統計錯誤 tool 呼叫；看 context 中的 tool 數量 | 加前綴與 allowlist；用 tool search 延遲載入（第 13 章） |

## 本章重點整理

- function calling 標準化了模型與 harness 之間的格式，MCP 則標準化 harness 與外部能力之間的介面，把 N×M 份整合變成 N＋M 份實作，並讓整合的所有權回到擁有該系統的團隊。
- host 擁有模型、對話與安全政策；一個 client 只連一個 server；server 彼此隔離，也看不到完整對話。
- tools 由模型控制、resources 由應用程式控制、prompts 由使用者控制；這個控制權的差異決定了核准政策、快取方式與 context 成本。
- MCP 建立在 JSON-RPC 2.0 上：request 與 response 用 id 配對，notification 沒有 id 也不回應。
- 失敗分成兩層：協定錯誤由 host 與工程師處理，tool 執行錯誤以 `isError` 回填給模型當觀察；兩者混用會讓問題被藏起來或讓模型白忙。
- stdio 適合本機工具，但以使用者權限執行；Streamable HTTP 適合遠端、多使用者、需要 OAuth 的服務。
- 早期的 initialize handshake 與 session 讓 HTTP 部署需要 sticky session、怕重啟、難以 serverless；最新規格改成每個 request 自帶版本與能力，並以 `server/discover` 隨時查詢。
- stateless 不代表沒有狀態，而是把狀態從連線搬到有 id、有擁有者、有過期時間的 handle 與共享儲存。
- multi round-trip requests 讓 server 以「需要輸入」的結果取代中途反向發問；副作用只在最後一輪執行，requestState 必須當成不可信輸入保護。
- 遠端 MCP server 是 OAuth resource server：client 用 Protected Resource Metadata 找到授權伺服器、以 resource indicator 取得綁定 audience 的 token，server 必須驗證 audience。
- 禁止 token passthrough：server 存取下游時要用自己的身分與最小 scope，才能保住限流、稽核與 audience 綁定。
- extensions 讓 core 保持精簡；MCP Apps、Tasks、Skills over MCP、ext-auth 都要經過協商，並為不支援的 host 準備退路。
- tool 描述、tool 輸出與 resource 都是不可信內容；allowlist、定義雜湊 pin、server 前綴與寫入核准是 host 的基本防線，annotations 只是提示，不能拿來做安全決策。
- 教學版的 MCP server／client 只要一百多行就能說明協定的骨架，但要上線請使用官方 SDK，並補上 transport、授權與定義審核。

## 延伸問答

> [!question]- Q1. MCP 和 function calling 是什麼關係？有了 MCP 還需要 function calling 嗎？
> 兩者在不同的層。function calling 是模型 API 的能力：模型輸出結構化的「我要呼叫某 tool」，harness 執行後回填，這是第 4 章的 loop 賴以運作的基礎。MCP 是 harness 與外部能力之間的協定：tool 由誰提供、怎麼發現、怎麼呼叫與授權。一個 host 從 MCP server 取得 tool 清單後，仍然要把它們轉成模型 API 的 tool 定義，模型仍然用 function calling 提出呼叫，host 再透過 MCP 轉給 server 執行。
>
> 所以 MCP 不取代 function calling，而是讓 function calling 背後的 tool 可以來自任何人、被任何 host 使用。本章動手做的橋接層正是這個轉換點：`loom` 看到的是一般的 Tool，模型看到的是一般的 tool 定義，只有橋接層知道背後是 MCP。有些模型 API 提供遠端 MCP connector，讓供應商的伺服器直接連 MCP server，這只是把 host 的角色搬到雲端，分層關係不變。

> [!question]- Q2. 某個資料該做成 MCP 的 tool 還是 resource？請用青鳥的例子說明判斷依據。
> 判斷依據是「誰最清楚什麼時候需要它」，以及載入時機對成本的影響。退貨政策是每一段客服對話都可能用到、內容穩定、篇幅不大的資料，host 最清楚它該在對話開頭載入，所以做成 resource，host 讀一次放進 system prompt 的穩定前綴，還能命中 prompt cache。如果做成 tool，模型要先「想到」去查，多花一輪呼叫，結果也落在對話尾端，無法快取。
>
> 相反地，某張訂單的完整異動歷程只有少數問題用得到、內容可能很長，host 無法事先知道哪張訂單會被問到，只有模型在推理過程中才知道，所以做成 tool 讓模型按需取用比較合理。有副作用的動作（建立退貨單）一定是 tool，而且要搭配核准政策。介於中間的情況，例如使用者想在 IDE 裡把某份報表明確加進對話，可以做成 resource，讓使用者透過介面選取，同樣是由人而不是模型決定載入時機。

> [!question]- Q3. 為什麼 MCP 要把 initialize handshake 拿掉？handshake 原本有什麼好處，拿掉後失去了什麼？
> handshake 的好處是只協商一次：版本、雙方能力、身分在連線開頭確定，之後的訊息不必重複攜帶；連線建立後是雙向的，server 可以在呼叫中途反向發問。問題在於這些好處都綁在「連線」上。HTTP 部署時，連線被表示成記憶體裡的 session，於是多副本需要 sticky session、部署重啟會讓所有 session 失效、serverless 平台無法保留狀態，server 中途反向發問則需要一條長時間掛著、容易被 proxy 切斷的串流。
>
> 拿掉之後，每個 request 自帶版本與能力，任何副本都能處理，需要時用 `server/discover` 查詢。失去的東西有三項：每個 request 多一小段 metadata；能力不再「一次確定」，client 要處理任何時候都可能出現的「不支援」錯誤；server 不能再隱含地記住連線狀態，跨呼叫的狀態必須設計成 handle，並處理擁有者綁定與過期。以 production 的擴展性與可靠性來說，這些代價是值得的，這也和 HTTP 與 REST 選擇無狀態的理由相同。

> [!question]- Q4. 情境判斷：你在 production 看到 ERP MCP server 擴充到 3 個副本後，客服 agent 的 tool 呼叫失敗率剛好接近 67%。你會怎麼排查？
> 失敗率接近「1 − 1/副本數」是很強的訊號：只有落在某一台的 request 成功，其餘都失敗，幾乎可以確定是狀態綁在單一 instance 上。第一步看失敗的錯誤內容：如果是 404 或「session 不存在」，就是舊式 session 存在記憶體裡；如果是「handle 不存在」，則是 server 雖然用了 handle，卻把它存在本機記憶體而不是共享儲存。第二步確認 load balancer 的分流方式，並在 trace 中標出每個 request 落在哪個副本，對照成功與失敗的分布。
>
> 短期止血可以開 sticky session，但要知道部署或 crash 重啟時仍然會斷。根本解法是讓 server 真正 stateless：協定版本與能力由每個 request 攜帶，跨呼叫的狀態放到共享儲存，handle 綁定擁有者並設定過期。修完之後，用類似 14.6 節的 round-robin 模擬寫成測試，在 CI 中以多個 instance 跑同一組呼叫，避免回歸。

> [!question]- Q5. MRTR 的 requestState 由 client 保管，為什麼這會是安全問題？有哪些設計方式？
> requestState 在兩輪之間存在 client 手上，client 重送時原樣帶回，所以 server 收到的 requestState 和其他 request 參數一樣，是不可信的輸入。如果 server 把「退款金額」「訂單擁有者」這類影響授權或金額的資訊直接放進 requestState，又在第二輪直接採信，惡意或有 bug 的 client 就能改掉它，等於繞過了 server 自己的計算。
>
> 常見的設計有兩種。第一種是簽章或加密：server 用只有自己知道的金鑰對 requestState 做 HMAC（14.7 節的程式），第二輪先驗證再使用，所有副本共用金鑰即可 stateless；需要隱藏內容時改用加密。第二種是只放一個隨機 id，真正的狀態存在 server 端共享儲存並設定過期，這樣 client 看不到也改不了內容，代價是需要儲存。不論哪一種，第二輪都要重新檢查授權（這個使用者還能做這件事嗎），副作用只在最後一輪執行，並以 idempotency key 防止重送造成重複。

> [!question]- Q6. 什麼是 token passthrough？為什麼 MCP 規格明文禁止？正確的替代做法是什麼？
> token passthrough 是指 MCP server 把 client 傳來的 access token 原封不動地轉送給下游 API，或者接受不是發給自己的 token。它看起來很方便：使用者的權限直接延伸到下游，不必另外管理憑證。問題是它破壞了三件事：下游看到的是「使用者直接呼叫」，MCP server 應有的限流、權限檢查與資料過濾被繞過；稽核紀錄上看不出中間經過了 MCP server；而下游若接受這種 token，代表它不驗證 audience，一張外洩的 token 可以在多個系統間通用。
>
> 正確的做法是每一段都有自己的 token：client 以 resource indicator 取得 audience 是 MCP server 的 token；MCP server 驗證後，以自己的身分取得給下游 API 的 token，常見方式是 OAuth token exchange，或用服務憑證並附帶使用者情境，scope 只開這次需要的範圍。這樣每一段的權限可以獨立撤銷，稽核紀錄也能完整重建「哪個使用者、經由哪個 host 與 server、做了什麼」。這也是 confused deputy 問題的標準解法。

> [!question]- Q7. 程式找錯：下面是某個 host 把 MCP tool 接進 agent 的程式，有哪些會在 production 出事的問題？
> ```python
> tools = []
> for server in servers:
>     for t in server.list_tools():
>         tools.append(Tool(t["name"], t["description"], t["inputSchema"],
>                           lambda **a: server.call_tool(t["name"], a)["content"][0]["text"]))
> ```
> 第一個問題是 Python closure 的晚綁定：lambda 引用的 `server` 與 `t` 是迴圈變數，迴圈結束後所有 lambda 都指向最後一個 server 的最後一個 tool，模型呼叫任何 tool 實際上都會打到同一個。14.12 節的程式用 `make_fn(remote_name)` 工廠函式，在建立時就把名稱綁定，正是為了避免這個問題。
>
> 第二，沒有前綴也沒有 allowlist：兩個 server 的同名 tool 會互相覆蓋，寫入類 tool 也全部暴露給模型。第三，忽略了 `isError`：tool 執行失敗時，錯誤文字被當成成功結果回填，模型分不清「查無訂單」與正常資料；而且只取 `content[0]`，多個 content block 時會丟資訊，content 為空時直接 IndexError。第四，沒有定義雜湊比對與快取：每次啟動都盲目信任 server 當下回傳的描述，rug pull 不會被發現。

> [!question]- Q8. 估算題：青鳥的客服 host 接了 6 個 MCP server，共 90 個 tool，每個 tool 定義平均 350 tokens。每天 20 萬次模型呼叫。tool 定義的 token 量有多大？你會怎麼處理？
> 90 × 350 ＝ 31,500 tokens，每次呼叫光是 tool 定義就有約三萬多 tokens；20 萬次呼叫就是每天約 63 億 tokens 的 input，而且這還沒算對話內容。就算 tool 定義放在穩定前綴、大多能命中 prompt cache 的折扣價，它仍然佔用 context window、拉長延遲；更重要的是，第 13 章提到 tool 一多，模型選錯 tool 的機率會上升，這是正確率問題，不只是成本問題。
>
> 處理方式分三層。第一層是 allowlist：客服 host 真的需要 90 個 tool 嗎？依 trace 統計實際使用率，多數 host 只需要其中一小部分，寫入類還應該預設不暴露。第二層是延遲載入：常用的少數 tool 常駐，其餘以 tool search 按需載入（第 13 章），追加定義而不改動前綴，保護 prompt cache。第三層是改善 tool 本身：把多個 CRUD 級 tool 合併成 workflow 級 tool（第 5 章），縮短描述中的冗詞。實際折扣與上限依供應商而異，但估算的方向不變：先量出 tool 定義佔 input 的比例，再決定要在哪一層下手。

## 延伸閱讀

- Model Context Protocol 官方規格（Specification，2026-07-28 版）與 changelog
- Model Context Protocol 官方規格〈Authorization〉與〈Security Best Practices〉章節
- Anthropic〈Introducing the Model Context Protocol〉（2024）
- Anthropic Engineering Blog〈Code execution with MCP〉（2025）
- JSON-RPC Working Group〈JSON-RPC 2.0 Specification〉
- IETF RFC 9728〈OAuth 2.0 Protected Resource Metadata〉與 RFC 8707〈Resource Indicators for OAuth 2.0〉
- OWASP〈Top 10 for Agentic Applications〉（2026 版，2025 年 12 月發布）
