---
chapter: 29
title: Observability：Tracing、成本與除錯
part: 6
---

# 第 29 章　Observability：Tracing、成本與除錯

> [!abstract] 本章地圖
> **核心問題**：agent 在 production 裡說錯話、繞圈子或花太多錢時，你要怎麼在幾分鐘內知道「是哪一次對話、走到哪一步、為什麼」，而且不必把客戶的個資一起存下來？
>
> **你會學到**：
> - 說明 agent 的 observability 和傳統服務差在哪裡，為什麼「HTTP 200」不等於「答對了」
> - 用 trace、span、session 的資料模型描述一次 agent 執行，並用 W3C traceparent 讓 trace 跨過 MCP 與 A2A 的邊界
> - 依 OpenTelemetry GenAI semantic conventions 為 agent、model、tool span 命名與加屬性，知道哪些名稱還在變動
> - 決定哪些資料一定記、哪些要 opt-in、哪些必須在離開 process 前遮蔽，並實作 PII 遮蔽與假名化
> - 在寫入時算好成本，做出依租戶、功能、prompt 版本切分的成本與 token 儀表板，並用「每次成功任務成本」做決策
> - 從 trace 查出失敗原因：寫出「說成功、其實失敗」等查詢，並把找到的案例變成回歸測試
> - 設計線上監控指標、tail sampling 與告警，並給 `loom` 加上 `loom.tracing` 模組
>
> **前置知識**：第 3 章（token、prompt caching 的計價）、第 4 章（agent loop、trajectory、`loom` v0.1）、第 9 章（context 版面與 cache 命中率）、第 27 章（outcome 與 trajectory 評估、error analysis）

## 29.1 故事：一句「已為您完成退款」

星期二下午，青鳥科技的客戶成功團隊轉來一張急件：晨光文具的店長說，有位顧客上週在聊天視窗要求退款，客服 agent 回覆「好的，已為您完成退款，款項 3–5 天入帳」，結果一週過去錢沒有進來，顧客在社群上留了一星評價。店長只記得訂單編號 B-2077 和大概的日期。阿哲把這張單丟進頻道：「今天能不能告訴對方發生了什麼事？」

Iris 打開 log 平台，搜尋 B-2077，跳出四十幾行。有的是 agent 服務印的 `calling tool refund`，有的是退款服務的 `ValueError: order shipped`，有的是閘道的 HTTP 存取紀錄，分散在三台機器、兩個時區格式的時間戳裡。最麻煩的是，看不出哪一行屬於哪一次對話：那一週 B-2077 被查過三次，其中一次是商家自己在後台查的。Iris 花了一個半小時，靠時間戳把幾行 log 拼起來，大致推論出：退款 tool 回了錯誤，但 agent 最後仍然告訴顧客「已退款」。可是模型那一輪看到了什麼、為什麼這樣說，log 裡沒有。

Maya 看了 Iris 貼在頻道的截圖，立刻私訊：「你截圖裡那行 log 有顧客的手機和 email，整串原文都印出來了。這個 log 平台全公司工程師都看得到，保存一年。」Iris 這才發現，當初為了除錯方便，在 loop 裡加了一行 `print(messages)`。同一天，阿哲又收到財務的問題：上個月模型帳單比前一個月高了三成多，哪個租戶、哪個功能造成的？沒有人答得出來，因為帳單只有一個總數。

老陳聽完這三件事，在白板上寫了三個問題：「這次對話走了哪幾步？每一步花了多少錢、多少時間？哪些資料不該被看到？」接著說：「你們有 log，但沒有 observability。log 是一行一行的句子，你要的是一棵樹：一次對話是一條 trace，每次模型呼叫、每次 tool 執行都是樹上的一個節點，節點上掛著 token、成本、錯誤和版本。有了這棵樹，今天的問題是一個查詢，不是一個半小時的考古。」

這一章就是 Iris 補上這棵樹的過程。我們先釐清 agent 的 observability 為什麼和傳統服務不同，再建立 trace、span、session 的資料模型，接著用 OpenTelemetry GenAI semantic conventions 決定名稱，處理 PII、成本、除錯查詢與線上監控，最後在「動手做」給 `loom` 加上 `loom.tracing`，把 B-2077 的事故重現出來，並用一個查詢把它找到。

## 29.2 Agent 的 observability 和傳統服務差在哪

**observability**（可觀測性）指的是：只靠系統對外輸出的資料，就能回答「系統現在為什麼是這個樣子」，包括你事先沒想到要問的問題。傳統上它由三種訊號組成：**log**（一行一行帶時間戳的事件紀錄）、**metric**（可以加總與畫成時間序列的數字，例如每分鐘請求數、p95 延遲）、**trace**（追蹤一個請求在系統中經過的每一段工作與它們的因果關係）。對一般的後端服務，這三種訊號大多能回答「哪裡慢、哪裡錯」。

agent 讓這套方法論遇到三個新問題。第一，**失敗多半是語意上的，不是技術上的**。B-2077 那次對話，每個 HTTP 呼叫都回 200，沒有任何例外往外丟，模型 API 也正常回應；錯的是「模型在 tool 失敗後仍然宣稱成功」。只看錯誤率與延遲的監控，對這種失敗完全沉默。第二，**路徑是動態的**。同一個「我要退款」，有時兩步就結束，有時走了九步還轉真人；你無法事先畫出呼叫圖，只能事後從資料重建。第三，**成本是每個請求不同的**。傳統服務的單次請求成本大致固定，agent 的單次成本可以相差上百倍，取決於步數、tool 結果大小與 cache 是否命中。

```text
 傳統服務的觀測重點              agent 系統還要多看的東西
 ─────────────────────           ────────────────────────────────────────
 請求 → handler → DB             請求 → loop ×N 輪 ─┬─ 模型呼叫（tokens、cache、成本）
   │                                                 ├─ tool 執行（參數、結果、錯誤）
   ├─ 延遲、錯誤率、吞吐量                           ├─ 子 agent（另一棵子樹）
   └─ 例外與 stack trace                             └─ guardrail／核准（判定與等待時間）

 「錯了」通常會丟例外              「錯了」常常是 200 OK 加上一句錯誤的回覆
 每個請求成本差不多                每個請求成本可以差上百倍
 呼叫圖事先知道                    呼叫圖由模型在執行時決定
```

這張圖左邊是傳統服務：路徑固定、錯誤會浮上來、成本平均。右邊是 agent：一個請求展開成 N 輪，每一輪裡面可能有模型呼叫、tool 執行、子 agent 與人工核准，每一種節點要記的東西都不同。最後三行對照了三個新問題：語意失敗不會丟例外、成本分布有長尾、呼叫圖是動態的。這三個問題決定了本章的三條主線：用 trace 重建動態路徑、在 span 上記成本、用查詢與線上 eval 找出語意失敗。

| 面向 | 傳統後端服務 | Agent 系統 | 對設計的影響 |
|---|---|---|---|
| 失敗訊號 | 例外、5xx、timeout | 錯誤回覆、繞圈、過早宣告完成、tool 失敗被忽略 | 需要結構化的業務訊號與線上 eval，不能只看錯誤率 |
| 呼叫路徑 | 部署時就知道 | 執行時由模型決定 | 必須記錄 parent-child 關係才能重建 |
| 單次成本 | 大致固定 | 依步數、tokens、cache 命中而變 | 成本要記在每個 span 上，能依任意維度加總 |
| 可重現性 | 同樣輸入大致同樣輸出 | 同樣輸入也可能走不同路徑 | 要存足夠的內容才能 replay，但內容涉及隱私 |
| 敏感資料 | 多半在 DB，log 少量 | prompt 與 tool 結果天然含有個資 | 內容擷取要 opt-in，遮蔽在離開 process 前完成 |
| 變更來源 | 程式碼部署 | 程式碼、prompt、模型版本、tool 描述、價目表 | 每個 span 要帶版本，才能對上變更時間點 |

這張表最後一列常被低估。傳統服務的行為改變幾乎都來自部署，agent 的行為改變卻可能來自 prompt 改版、模型供應商在同一個名稱下更新權重、tool 描述被產品經理改了一個字，或者價目表調整。trace 上沒有這些版本，你就只能看到「上週三開始變差」，卻不知道上週三改了什麼。

> [!warning] 常見誤解
> 「我們有 eval，所以不需要 observability。」第 27 章的 eval 回答「這個版本在測試集上好不好」，observability 回答「production 上這一次為什麼不好」。eval set 是你事先想到的題目，production 的失敗常常是你沒想到的；而好的 eval set 正是從 trace 裡撈出來的真實失敗。兩者是同一個迴圈的兩半，不是二選一。

## 29.3 Trace、span 與 session：資料模型

**trace**（追蹤）是一個邏輯工作單位從頭到尾的完整紀錄，例如「顧客送出一則訊息，到 agent 回覆為止」。trace 由很多 **span**（區段）組成，每個 span 代表一段有開始與結束時間的工作，例如「一次模型呼叫」或「一次 `refund` tool 執行」。每個 span 有一個 **span id**，並記錄它的 **parent span id**（父區段），因此所有 span 會連成一棵樹；樹根叫 **root span**，在 agent 系統中通常就是「這次 agent 執行」本身。所有 span 共享同一個 **trace id**，靠它把分散在不同機器上的片段收在一起。

每個 span 上可以掛三種資料。**attributes**（屬性）是鍵值對，描述這段工作是什麼，例如 `gen_ai.request.model=…`、`gen_ai.usage.input_tokens=467`；它們是查詢與加總的主要依據。**events**（事件）是 span 內某個時間點發生的事，例如「收到第一個 token」或「拋出例外」，帶有自己的時間戳與屬性。**status**（狀態）只有三種：UNSET、OK、ERROR，表示這段工作在技術上成功與否。另外，span 有 **kind**（種類）：呼叫外部服務的是 CLIENT，同一個 process 內的邏輯步驟是 INTERNAL，接收請求的是 SERVER。

```text
 一次 B-2077 退款對話的 trace（時間由左到右）

 trace_id = d18f2be3…   conversation = conv-002
 0ms                     600ms  690ms                    1290ms
 ├─────────────────────────────────────────────────────────┤ invoke_agent bluebird-support   (root, INTERNAL)
 ├────────────────────────┤                                    chat <model>                   (CLIENT)
 │  attrs: input_tokens=338, output_tokens=40, finish_reasons=[tool_use]
                          ├──┤                                 execute_tool refund            (INTERNAL)
                          │  status=ERROR  error.type=ValueError
                          │  event: exception "訂單已出貨，不能直接退款"
                             ├────────────────────────┤        chat <model>                   (CLIENT)
                             │  attrs: input_tokens=467, cache_read=338, finish_reasons=[end_turn]
```

這張瀑布圖就是老陳說的「那棵樹」，攤平在時間軸上。最上面的 root span 涵蓋整次執行，三個子 span 依時間排開：第一次模型呼叫決定呼叫 `refund`，`refund` 執行 90 毫秒後以 ERROR 結束，事件裡留著完整的錯誤訊息；第二次模型呼叫讀到錯誤後，卻以 end_turn 結束並回覆了「已退款」。只要看一眼這張圖，Iris 花一個半小時拼湊的結論就擺在眼前，而且多了 log 裡沒有的東西：每一步的 token、cache 命中量與先後因果。

注意 root span 的 status 是 OK。這不是 bug，而是一個重要的設計區分：span status 描述「這段程式有沒有技術性失敗」，而「任務有沒有真的完成」是業務結果，應該用另一個屬性記錄（本章用 `bluebird.run.status` 與 `bluebird.claims`）。如果把兩者混在一起，例如只要任何子 span 失敗就把 root 標成 ERROR，那麼「tool 失敗後模型正確改走退貨流程」的健康對話也會被算成錯誤，錯誤率就失去意義。

trace 之上還有一層：**session**（工作階段），在 OpenTelemetry 的 GenAI 慣例中稱為 conversation，用 `gen_ai.conversation.id` 表示。一個顧客的一段對話可能有很多輪，每一輪是一條 trace，同一個 conversation id 把它們串起來。為什麼不把整段對話做成一條巨大的 trace？因為 trace 通常有時間與大小的實務上限，而且「一輪」才是延遲與錯誤的自然單位；session 層級的問題（這段對話總共花多少錢、轉了幾次真人）則用 conversation id 聚合來回答。長時間的背景 agent 還要再記一個 run id，對上第 22 章 durable execution 的事件歷史。

最後一個基礎概念是 **context propagation**（上下文傳遞）：當 agent 透過 MCP 呼叫 ERP，或透過 A2A 委派給另一個 agent，對方建立的 span 要能接回同一條 trace。業界標準是 W3C Trace Context 規格定義的 `traceparent` 標頭，格式是「版本-trace id-parent span id-旗標」。HTTP 呼叫放在 header；MCP 社群也定義了在請求的 `_meta` 欄位中傳遞 `traceparent` 的慣例（第 14 章）。下面的程式示範 client 端怎麼放、server 端怎麼讀。

```python
from __future__ import annotations

import re
from dataclasses import dataclass

# W3C Trace Context 的 traceparent：版本-trace_id(32 hex)-parent_id(16 hex)-flags(2 hex)
TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


@dataclass
class SpanContext:
    trace_id: str
    span_id: str
    sampled: bool


def inject(ctx: SpanContext) -> dict[str, str]:
    """client 端：把目前 span 的身分放進要送出的請求（HTTP header 或 MCP 的 _meta）。"""
    return {"traceparent": f"00-{ctx.trace_id}-{ctx.span_id}-{'01' if ctx.sampled else '00'}"}


def extract(carrier: dict[str, str]) -> SpanContext | None:
    """server 端：讀回上游的身分；格式不對就當成沒有，開一條新 trace，而不是讓請求失敗。"""
    m = TRACEPARENT.match(carrier.get("traceparent", ""))
    if not m or set(m.group(1)) == {"0"} or set(m.group(2)) == {"0"}:
        return None
    return SpanContext(m.group(1), m.group(2), int(m.group(3), 16) & 1 == 1)


# 青鳥的客服 agent（loom）呼叫 ERP 的 MCP server
agent_tool_span = SpanContext("4bf92f3577b34da6a3ce929d0e0e4736", "00f067aa0ba902b7", True)
request = {"method": "tools/call", "params": {"name": "erp_get_invoice",
           "_meta": inject(agent_tool_span)}}

upstream = extract(request["params"]["_meta"])
server_span = SpanContext(upstream.trace_id, "b7ad6b7169203331", upstream.sampled)
print("client 送出:", request["params"]["_meta"]["traceparent"])
print("server span: trace_id 相同 =", server_span.trace_id == agent_tool_span.trace_id,
      "／parent =", upstream.span_id)
print("壞掉的 header →", extract({"traceparent": "00-xyz-123-01"}))
assert server_span.trace_id == agent_tool_span.trace_id and upstream.span_id == agent_tool_span.span_id
assert extract({"traceparent": "00-" + "0" * 32 + "-00f067aa0ba902b7-01"}) is None
```

```text
client 送出: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
server span: trace_id 相同 = True ／parent = 00f067aa0ba902b7
壞掉的 header → None
```

第一行是 client 送出的 `traceparent`：`00` 是版本，接著是 32 個十六進位字元的 trace id、16 個字元的 span id（也就是 client 端 tool span 自己的 id），最後的 `01` 表示「這條 trace 有被取樣」。第二行顯示 server 端建立的 span 沿用了同一個 trace id，並把 client 的 span id 當成 parent，於是 ERP 裡的工作會出現在客服 agent 那棵樹的 `execute_tool` 節點底下。第三行是防禦性設計：header 格式不對時回傳 None，server 開一條新的 trace 繼續服務，而不是因為觀測資料壞掉就讓業務請求失敗。observability 永遠不能成為可用性的單點故障。

> [!tip] trace id 不是安全邊界
> `traceparent` 是對方送來的資料，可以被偽造。不要用 trace id 做授權判斷，也不要把它當成租戶隔離的依據；跨越信任邊界時（例如接收外部 A2A agent 的請求），可以選擇只記錄對方的 trace id 作為連結屬性，而不是直接接成 parent，以免外部系統把垃圾 span 灌進你的 trace。

## 29.4 OpenTelemetry GenAI semantic conventions：agent、model、tool span 怎麼命名

有了 span 這個容器，下一個問題是「裡面的東西叫什麼名字」。如果 Iris 把 token 數記成 `tokens_in`、另一個團隊記成 `prompt_tokens`、第三方框架又記成 `input_token_count`，任何跨團隊的儀表板都做不出來，換觀測平台時也要全部重寫。**semantic conventions**（語意慣例）就是用來解決這件事的共同命名規範：同一個概念在所有系統裡用同一個屬性名稱、同一種值。**OpenTelemetry**（簡稱 OTel）是 CNCF 旗下的開源觀測標準，提供 API、SDK、傳輸協定（OTLP）與 semantic conventions；其中針對生成式 AI 的部分稱為 **GenAI semantic conventions**，涵蓋模型呼叫、agent、tool，以及 MCP 等協定。

GenAI 慣例的核心是 `gen_ai.operation.name` 這個屬性，它說明這個 span 在做哪一類操作，並決定 span 的名稱格式。對 agent 系統最重要的幾種如下表。表中的屬性名稱依 2026 年 10 月的公開規格整理；這份規格幾乎全部仍處於 Development（開發中）穩定度，名稱可能變動，實作時以官方最新版本為準。

| 操作（`gen_ai.operation.name`） | span 名稱格式 | span kind | 代表什麼 | 常用屬性 |
|---|---|---|---|---|
| `invoke_workflow` | `invoke_workflow {gen_ai.workflow.name}` | INTERNAL | 多 agent 或 graph 的整體協調 | workflow 名稱 |
| `invoke_agent` | `invoke_agent {gen_ai.agent.name}` | 同 process 為 INTERNAL，遠端 agent 為 CLIENT | 一次 agent 執行 | `gen_ai.agent.name`、`gen_ai.agent.id`、`gen_ai.agent.version`、`gen_ai.conversation.id` |
| `plan` | `plan {gen_ai.agent.name}` | INTERNAL | 產生計畫的步驟，規劃用的模型呼叫是它的子 span | agent 名稱 |
| `chat` | `chat {gen_ai.request.model}` | CLIENT | 一次模型呼叫 | `gen_ai.provider.name`、`gen_ai.request.model`、`gen_ai.response.model`、`gen_ai.usage.input_tokens`、`gen_ai.usage.output_tokens`、`gen_ai.response.finish_reasons` |
| `execute_tool` | `execute_tool {gen_ai.tool.name}` | INTERNAL | 一次 tool 執行 | `gen_ai.tool.name`、`gen_ai.tool.call.id`、`gen_ai.tool.type` |
| `retrieval`、`embeddings` | 依操作與資料源命名 | CLIENT | 檢索與向量化 | `gen_ai.data_source.id` 等 |
| `search_memory` 等 memory 操作 | 依操作命名 | 依情況 | 第 12 章的 memory 讀寫 | 依規格 |

這張表有幾個值得細看的地方。第一，span 名稱刻意只放「低基數」的值：操作類型加 agent 名稱、模型名稱或 tool 名稱，而不是訂單編號或使用者 id。**cardinality**（基數）是某個欄位可能出現的不同值的數量；觀測後端常以 span 名稱分組與建立索引，名稱裡放了高基數的值，就會產生數百萬個「不同的操作」，查詢變慢、費用暴增。高基數的資料放屬性，不放名稱。第二，`invoke_agent` 的 kind 依 agent 在哪裡而不同：同一個 process 裡的子 agent 是 INTERNAL，透過網路呼叫的遠端 agent 是 CLIENT，這讓後端能分辨「時間花在我們自己的程式」還是「花在等別人」。第三，`execute_tool` 的屬性中，tool 參數與結果（`gen_ai.tool.call.arguments`、`gen_ai.tool.call.result`）屬於 opt-in 的內容欄位；這兩個名稱在 survey 時未能逐字核對規格頁面，請以官方為準。

```text
 營運 research agent（multi-agent）的 span 階層

 invoke_workflow monthly-ops-report                    INTERNAL
 └─ invoke_agent ops-lead                              INTERNAL
    ├─ plan ops-lead                                   INTERNAL
    │  └─ chat <frontier-model>                        CLIENT   ← 規劃用的模型呼叫掛在 plan 底下
    ├─ invoke_agent refund-analyst                     INTERNAL ← 同 process 的子 agent
    │  ├─ chat <small-model>                           CLIENT
    │  └─ execute_tool run_sql                         INTERNAL
    │     └─ (sandbox 內的程式呼叫 get_refunds ×40)    INTERNAL ← 第 13 章 code-as-action 的內部呼叫
    ├─ invoke_agent logistics-partner                  CLIENT   ← 透過 A2A 委派給物流商的遠端 agent
    │  └─ ……對方系統的 span（traceparent 傳遞）       SERVER
    └─ chat <frontier-model>                           CLIENT   ← 綜合所有子結果
```

這張圖把第 20 章的 orchestrator–subagent 架構對應到 span 階層。最外層的 `invoke_workflow` 只在多 agent 或 graph 協調時才需要，單一 agent 直接以 `invoke_agent` 當 root 即可。`plan` 是一個邏輯分組，它底下的 `chat` 是真正的模型呼叫，這樣你能分別看到「規劃花了多少」和「執行花了多少」。`refund-analyst` 子 agent 的 `run_sql` 底下，還有程式在 sandbox 內部呼叫的 40 次 `get_refunds`：第 13 章提到 code-as-action 會讓這些呼叫在 trace 上消失，解法就是在 sandbox 提供的 tool 介面裡同樣建立 `execute_tool` span，並透過 `traceparent` 接回來。最後，委派給物流商的遠端 agent 是 CLIENT span，對方若也支援 trace context，它的 SERVER span 就會出現在這棵樹裡。

為什麼要遵循一個還在 Development 狀態的規格，而不是自己定名字？因為成本不對稱。照規格命名，大多數觀測平台能直接辨識 span 類型、算出 token 與成本、畫出 agent 的樹狀視圖；未來規格改名時，通常只需要在匯出端做一層名稱對應。自己發明名字，每接一個平台都要寫一次轉換，團隊之間也無法共用儀表板。本章的做法是：GenAI 慣例有定義的概念一律用 `gen_ai.*`；慣例沒有涵蓋的業務屬性放在自家命名空間 `bluebird.*`（例如租戶 id、prompt 版本、成本），不要把自訂屬性塞進 `gen_ai.*`，以免日後和官方新增的名稱衝突。

規格中另有幾個對 agent 很實用的設計原則。用來做 **head sampling**（請求開始時就決定是否記錄）的屬性，例如 agent 名稱、操作、provider、模型，應該在 span 建立時就設定，而不是在結束時才補；prompt、回應、system instructions、tool 定義等內容欄位一律是 opt-in，預設不擷取；錯誤用 Stable 的 `error.type` 屬性記錄類別（例如 `ValueError`、`timeout`），細節放在 exception 事件。規格也定義了 metrics，例如 client 端的 token 用量與操作耗時分布，讓你不必從 span 反推就能畫時間序列。

> [!note] 2026 現況
> 截至 2026 年 10 月，GenAI semantic conventions 已從 OpenTelemetry 主要的 semantic-conventions repo 搬到獨立的 `semantic-conventions-genai` repo 維護，範圍包含 GenAI client、agent、MCP 與部分供應商專屬慣例；舊頁面標示不再維護。穩定度方面，幾乎所有 GenAI 屬性仍為 Development，只有 `error.type` 與 `server.*` 等通用屬性為 Stable，尚未看到正式 release。`gen_ai.operation.name` 的已知值包括 `chat`、`text_completion`（舊）、`generate_content`、`embeddings`、`retrieval`、`execute_tool`、`create_agent`、`invoke_agent`、`invoke_workflow`、`plan`、`fetch_response`，以及一系列 memory 操作（如 `create_memory`、`search_memory`）。usage 屬性除了 input／output tokens，還有 cache 讀取、寫入與不同 modality 的細分，確切名稱請查規格。過去 OTel 的 instrumentation 曾以環境變數（如 `OTEL_SEMCONV_STABILITY_OPT_IN`）切換新舊屬性格式、以 `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` 控制是否擷取內容；這類開關的名稱依各語言 instrumentation 而異。

如果你要把本章的 tracer 換成官方 OpenTelemetry SDK，對應關係很直接：`tracer.span(...)` 換成 `start_as_current_span`，屬性用 `set_attribute`，例外用 `record_exception` 加 `set_status`。下面依 2026-10 的 OpenTelemetry Python API 撰寫，匯出器的套件與參數請以官方文件為準。

```python
# not-runnable：需要 opentelemetry-api、opentelemetry-sdk 與 OTLP exporter 套件
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))   # 背景批次匯出，不阻塞 agent
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("loom.tracing")


def traced_tool(name: str, call_id: str, fn, **args):
    with tracer.start_as_current_span(f"execute_tool {name}", kind=SpanKind.INTERNAL) as span:
        span.set_attribute("gen_ai.operation.name", "execute_tool")
        span.set_attribute("gen_ai.tool.name", name)
        span.set_attribute("gen_ai.tool.call.id", call_id)
        try:
            return fn(**args)
        except Exception as exc:
            span.record_exception(exc)
            span.set_attribute("error.type", type(exc).__name__)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
```

這段程式的重點是 `BatchSpanProcessor`：span 結束時只是放進記憶體佇列，由背景執行緒批次送出。這是 tracing 不能拖慢 agent 的基本要求，也意味著 process 被強制終止時，佇列裡最後幾個 span 可能遺失，所以要在關機流程中呼叫 provider 的 shutdown 讓佇列清空。遮蔽 PII 的 processor 要排在匯出之前，下一節就談它。

## 29.5 記錄什麼、遮蔽什麼：內容擷取與 PII

Maya 指出的問題，是 agent observability 最根本的張力：要除錯，你需要看到模型看到的東西；但模型看到的東西，天然包含顧客的姓名、電話、地址、訂單內容，甚至信用卡號。**PII**（personally identifiable information，個人可識別資訊）是能直接或間接識別某個人的資料，例如 email、手機號碼、身分證字號，或者「台中市某路某號的王小姐」這種組合。傳統服務的 log 裡偶爾漏一點 PII，agent 的 trace 如果全文擷取，幾乎每一筆都是 PII。

解法不是「全記」或「全不記」，而是把資料分層，每一層有不同的預設、保存期限與存取權限。

| 資料層級 | 例子 | 預設 | 保存與權限建議 | 為什麼 |
|---|---|---|---|---|
| 結構與耗時 | span 名稱、parent、開始結束時間、status、`error.type` | 一律記錄 | 一般工程師可讀，保存數十天 | 不含內容，是重建路徑與延遲分析的骨架 |
| 用量與成本 | tokens、cache 讀寫、成本、步數 | 一律記錄 | 同上，聚合結果可長期保存 | 成本歸因與容量規劃的依據 |
| 版本與設定 | prompt 版本、模型、tool 版本、價目表版本、feature flag | 一律記錄 | 同上 | 對上變更時間點 |
| 業務識別碼 | 訂單編號、租戶 id、假名化的使用者 id | 記錄（使用者 id 先假名化） | 依租戶隔離存取 | 除錯時要能 join 回業務系統 |
| 衍生訊號 | 「回覆宣稱已退款」「偵測到 2 個 PII」「guardrail 判定」 | 記錄 | 同上 | 不存原文也能查語意失敗 |
| 內容 | prompt、回應、tool 參數與結果 | opt-in，遮蔽後才記錄 | 少數人可讀、短期保存、存取留稽核 | 價值最高，風險也最高 |

這張表從上到下，資訊量與風險同時增加。前三層沒有內容，可以放心地廣泛使用；第四層的關鍵是「可以 join，但不能直接識別」；第五層是本章最推薦的技巧：**在寫入時萃取結構化訊號**。與其存下整句回覆再用全文搜尋找「已退款」，不如在 agent 結束時用規則或小模型判斷「這句回覆是否宣稱某個副作用已完成」，把結果記成一個屬性。查詢只需要這個布林值，原文可以不存，或只存在權限更嚴的地方。第六層的內容，則依環境決定：開發與測試環境全開，production 預設關閉，只在特定租戶同意、特定事件調查時短期開啟，並且一定先遮蔽。

**遮蔽**（redaction）是把敏感片段替換成標記，例如把 `0912-345-678` 換成 `<PHONE>`；**假名化**（pseudonymization）是用一個穩定但不可逆的代號取代識別碼，例如把 `user-512` 換成 `u_0a369f5ea4`，同一個人永遠得到同一個代號，因此仍能統計「這位使用者這週問了幾次」，卻無法從代號反推身分。假名化要用 **keyed hash**（帶金鑰的雜湊，例如 HMAC）而不是單純的 SHA-256：使用者 id、手機號碼的可能值空間很小，沒有金鑰的雜湊可以被窮舉還原。

```text
 span 從產生到落地的資料流（遮蔽一定在離開 process 之前）

 loom（agent process）                                    觀測後端
 ┌───────────────────────────────────────────┐            ┌────────────────────────┐
 │ instrumentation                           │            │ collector              │
 │  ├─ 結構、用量、版本 ────────────┐         │            │  ├─ tail sampling      │
 │  ├─ 內容（capture_content=on?）──┤         │   OTLP     │  ├─ 第二道遮蔽（保險）  │
 │  └─ 衍生訊號（claims、pii_count）┤         │  ───────►  │  └─ 依租戶路由          │
 │                                  ▼         │            ├────────────────────────┤
 │ processors： ① 屬性 allowlist             │            │ 儲存：骨架長期保留      │
 │              ② PII 遮蔽、假名化            │            │       內容短期、加密    │
 │              ③ 截斷過長的值                │            │ 存取：依角色與租戶授權  │
 │ exporter（背景批次）─────────────────────────────────►  │       讀取內容要留稽核  │
 └───────────────────────────────────────────┘            └────────────────────────┘
```

這張資料流圖有三個重點。第一，第一道遮蔽在 agent process 裡、匯出之前執行，因為資料一旦離開 process，就會經過網路、collector、佇列與儲存，每一站都可能留下副本；在來源處遮蔽是唯一能保證「後端從來沒見過原文」的位置。第二，processor 的順序是 allowlist → 遮蔽 → 截斷：先用 **allowlist**（允許清單）決定哪些屬性可以出門，新加的欄位預設不出門，比 denylist 更安全；再對允許的內容做遮蔽；最後截斷過長的值，避免一個 50 KB 的 tool 結果塞爆後端。第三，collector 端可以再做一次遮蔽當保險，並負責取樣（29.8 節）與依租戶路由，但它不能取代來源端的遮蔽。

下面的程式實作 allowlist、遮蔽與假名化，並刻意放進幾個容易誤判的資料：物流單號是一長串數字但不是卡號，訂單編號是除錯必需的業務 id，不應遮蔽。

```python
from __future__ import annotations

import hashlib
import hmac
import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# 台灣手機：0912-345-678、0912345678、+886 912 345 678 都要抓到
TW_MOBILE = re.compile(r"(?:\+886[\s-]?|0)9\d{2}[\s-]?\d{3}[\s-]?\d{3}")
CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def luhn_ok(digits: str) -> bool:
    """信用卡號的檢查碼。只遮蔽通過 Luhn 的數字串，避免把物流單號、金額誤殺。"""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def redact(text: str) -> tuple[str, list[str]]:
    hits: list[str] = []

    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if luhn_ok(digits):
            hits.append("CARD")
            return "<CARD>"
        return m.group(0)

    text = CARD.sub(card, text)
    for label, pattern in (("EMAIL", EMAIL), ("PHONE", TW_MOBILE)):
        text, n = pattern.subn(f"<{label}>", text)
        hits += [label] * n
    return text, hits


KEY = b"demo-key"                                   # 示意；實務由 secrets manager 提供並定期輪替

def pseudonym(value: str) -> str:
    return hmac.new(KEY, value.encode(), hashlib.sha256).hexdigest()[:12]


# 只匯出 allowlist 中的屬性：新加的欄位預設不出門，比 denylist 安全
EXPORT_ALLOWLIST = {"gen_ai.operation.name", "gen_ai.tool.name", "gen_ai.usage.input_tokens",
                    "gen_ai.tool.call.arguments", "bluebird.user.pseudonym", "error.type"}

raw = {
    "gen_ai.operation.name": "execute_tool",
    "gen_ai.tool.name": "update_address",
    "gen_ai.tool.call.arguments": "訂單 B-1042 改寄 amy.lin@example.com 與 +886 912 345 678，"
                                  "卡號 4111 1111 1111 1111，物流單 7712 3456 7890 12",
    "bluebird.user.email": "amy.lin@example.com",   # 工程師順手加的欄位，不在 allowlist
    "bluebird.user.pseudonym": pseudonym("user-512"),
}
exported = {}
for k, v in raw.items():
    if k not in EXPORT_ALLOWLIST:
        continue
    exported[k], hits = redact(v) if isinstance(v, str) else (v, [])
    if hits:
        exported["bluebird.redactions"] = sorted(set(hits))
for k, v in exported.items():
    print(f"{k:<28} {v}")
assert "bluebird.user.email" not in exported
assert "4111" not in exported["gen_ai.tool.call.arguments"]
assert "7712 3456 7890 12" in exported["gen_ai.tool.call.arguments"]   # 不是卡號，保留
assert "B-1042" in exported["gen_ai.tool.call.arguments"]               # 業務 id 保留，除錯要用
assert pseudonym("user-512") == exported["bluebird.user.pseudonym"]      # 同一人可 join
```

```text
gen_ai.operation.name        execute_tool
gen_ai.tool.name             update_address
gen_ai.tool.call.arguments   訂單 B-1042 改寄 <EMAIL> 與 <PHONE>，卡號 <CARD>，物流單 7712 3456 7890 12
bluebird.redactions          ['CARD', 'EMAIL', 'PHONE']
bluebird.user.pseudonym      277a70657bb7
```

逐行看輸出。`bluebird.user.email` 沒有出現在結果裡：它是工程師順手加的欄位，不在 allowlist，所以根本沒有被匯出，這就是 allowlist 的價值，你不必預先猜到每個人會加什麼欄位。`gen_ai.tool.call.arguments` 中，email、帶國碼的手機號碼與卡號都被換成標記，但 `B-1042` 與物流單號完整保留：卡號的判斷不只看「13 到 19 位數字」，還要通過 Luhn 檢查碼，否則物流單號、金額、時間戳都會被誤殺，trace 就失去除錯價值。`bluebird.redactions` 記錄了這個 span 遮蔽了哪些類型，它本身就是有用的衍生訊號：如果某個 tool 的參數經常出現卡號，代表上游流程讓顧客在聊天中輸入卡號，這是產品與合規問題，不只是 observability 問題。最後一行的假名在不同 span、不同 trace 之間保持一致，所以能 join。

規則式遮蔽有極限。它抓得到格式固定的資料（email、電話、卡號、身分證字號），抓不到自由文字中的姓名與地址，例如「寄給住在西屯區的林小姐」。實務上的做法是分層：規則式遮蔽一律開啟；需要更高召回率時，加上命名實體辨識模型或雲端的 DLP 服務；最重要的是減少內容擷取本身，能用衍生訊號回答的問題就不要存原文。另外，遮蔽也要套用在 events 與巢狀結構上（例如 messages 陣列中每一則的 content），只遮頂層字串是常見的漏洞。

> [!warning] 常見誤解
> 「trace 只有工程師看得到，所以不算外洩。」個資保護法規關心的是資料被誰處理、保存多久、能否刪除，而不只是有沒有公開。如果顧客行使刪除權，你必須能刪掉這位顧客在 trace 裡的內容；全文擷取又散落在各處的 trace，幾乎不可能做到。第 33 章會談稽核日誌：它和 debug trace 用 trace id 關聯，但保存期限、存取權限與防竄改要求都不同，必須分開治理。

## 29.6 成本與 token：從 span 算到儀表板

阿哲的問題「哪個租戶、哪個功能讓帳單漲了三成」，在 span 上記好用量之後，就變成一個 group by。但要讓這個 group by 的答案可信，有三個設計決定要先做對。

第一，**分開記錄每一種 token**。第 3 章談過，同樣是輸入 token，一般輸入、cache 讀取與 cache 寫入的價格差很多；推理模型的 thinking tokens 通常以輸出價格計費；多模態輸入還可能另計。只記一個「total_tokens」，你就無法區分「流量變大了」和「cache 命中率掉了」這兩種完全不同的漲價原因。第二，**成本在寫入時就算好**，並記下用的是哪一版價目表。模型價格會調整，事後用新價格回推舊用量，會讓歷史曲線出現假的斷層；把 `bluebird.cost.usd` 與 `bluebird.price.version` 一起寫在 span 上，歷史就是當時的真相。第三，**tool 也有成本**。網路搜尋 API 按次計費、sandbox 按秒計費、OCR 按頁計費，這些都要記在對應的 `execute_tool` span 上，否則「模型成本下降」可能只是成本轉移到了 tool。

單次模型呼叫的成本可以寫成：

```text
 cost = （input − cache_read − cache_write）× 輸入單價
      ＋ cache_read  × 快取讀取單價
      ＋ cache_write × 快取寫入單價
      ＋ output × 輸出單價（reasoning tokens 通常已含在 output 中）
 一次任務的成本 = Σ 模型呼叫成本 ＋ Σ tool 外部成本
```

這組公式的第一行要特別注意「扣掉」：多數供應商的回報方式是把 cache 讀寫的 token 和一般輸入分開列，但也有 API 把它們包含在總輸入裡再另外列出細項，你的計算要配合實際的 usage 欄位語意，否則會重複計算。reasoning tokens 也一樣：多數 API 把它算在 output tokens 之內、另列細項只供參考，再加一次就會重複計費。第 25 章的 model adapter 會把 usage 正規化成四個互不重疊的欄位（`input_tokens` 只代表未命中快取的部分），經過 adapter 之後就不必再做這裡的扣除；本章的程式直接處理「總輸入含快取」的原始語意，所以保留扣除這一步。第 4 章說過 agent 每一輪都重送完整歷史，所以一次任務的輸入 token 總量接近步數的平方成長；cache 命中與否，決定這個平方項是用一般價格還是用快取價格計費。

**成本歸因**（cost attribution）是把每一筆成本歸到可以負責的維度上：租戶、功能（客服、research、coding）、agent 名稱、prompt 版本、模型、tool。只要這些維度都是 root span 或 chat span 上的屬性，任何組合都能即時加總。實務上要注意兩點：維度要在 root span 建立時就決定，並由子 span 繼承或在查詢時 join，不要在每個子 span 上各自猜；共用成本（例如背景的 memory 整理、離線 eval 執行）要有自己的 agent 名稱或功能標籤，不能混進客服的成本裡。

```text
 青鳥 agent 成本儀表板的版面

 ┌─ 今日總覽 ────────────────────────────────────────────────────────────┐
 │ 任務數  成功率  每任務成本  每次成功任務成本  cache 命中率  p95 步數   │
 ├─ 依租戶 ──────────────────────┬─ 依功能／agent ──────────────────────┤
 │ 前 10 名租戶的成本與成功率      │ 客服、research、coding 的成本趨勢     │
 │ （找出異常的單一租戶）          │ （對上部署與 prompt 版本的時間點）     │
 ├─ 成本結構 ────────────────────┼─ 長尾 ───────────────────────────────┤
 │ 一般輸入／cache 讀／cache 寫／  │ 成本最高的 20 條 trace（可點進 span 樹）│
 │ 輸出／reasoning／tool 外部成本  │ 步數分布、單次 input tokens 的 p99     │
 └───────────────────────────────┴───────────────────────────────────────┘
```

這個版面的設計邏輯是「從總數往下鑽到單一 trace」。最上面一列回答「今天健不健康」，其中「每次成功任務成本」是最重要的一格：它等於總成本除以成功任務數，把品質與成本放在同一個數字裡。某個 prompt 改版讓單次成本降了 20%，但成功率從 90% 掉到 70%，每次成功任務成本反而上升，這正是只看單次成本會做錯決策的情況。中間兩格把成本切成租戶與功能兩個方向，用來找「是誰」；左下的成本結構用來找「是哪一種 token」，cache 讀取比例突然下降，通常就是第 9 章說的前綴被打斷；右下的長尾是除錯入口，成本最高的 trace 幾乎總是藏著繞圈、超大 tool 結果或錯誤的重試。

成功率從哪來？agent 的「成功」很少有直接的訊號，實務上用幾個代理指標組合：run status 為 done 且沒有可疑的衍生訊號、對話後沒有轉真人、使用者沒有在短時間內重問同一件事、使用者回饋與線上 eval 的分數（29.8 節）。這些都不完美，但只要定義固定、長期追蹤，趨勢就有意義。成功率的定義要寫進儀表板的說明裡，避免不同人用不同定義吵架。

> [!tip] 估算而不是猜
> 上線前就可以用 trace 的資料估算規模化後的成本：從內部試用的 trace 取出每任務的平均成本與 p95 成本，乘上預估任務量，再乘上一個長尾係數。第 35 章的容量估算會用到這組數字；第 25 章的 model router 則可以直接讀 span 上的成本與成功率，決定哪類任務該交給小型快速模型。

## 29.7 從 trace 找失敗原因

有了 span 樹、衍生訊號與成本，除錯就從「讀 log」變成「問問題」。老陳給 Iris 的除錯流程是一個固定的狀態機，不論症狀是什麼都照著走。

```text
 從症狀到修正的除錯流程

 [症狀] 客訴／告警／儀表板異常
    │  用 conversation id、訂單編號、租戶與時間範圍定位
    ▼
 [找到 trace] ──找不到──► 檢查取樣與傳遞：是否被丟棄？trace id 是否斷掉？
    │
    ▼
 [沿著 span 樹走] 找「第一個偏離預期的 span」，不是最後一個
    │
    ▼
 [分類] ─┬─ tool 錯誤被忽略／宣稱成功   ─┬─ 參數錯誤、選錯 tool
         ├─ 繞圈、步數或預算耗盡          ├─ context 過長、關鍵資訊被截斷
         └─ 外部依賴慢或失敗              └─ guardrail 誤擋或漏擋
    │
    ▼
 [重現] 把該 trace 的模型回應轉成 ScriptedModel 劇本，在本機 replay
    │
    ▼
 [修正與鎖住] 改 tool／prompt／harness → 加入 eval set（第 27 章）→ CI 回歸
    │
    ▼
 [擴大搜尋] 把這個失敗寫成查詢，找出同類 trace，估計影響範圍
```

這張流程圖最重要的是第三步：找**第一個**偏離預期的 span。agent 的錯誤會累積，最後那句錯誤的回覆只是結果；B-2077 的根因是 `refund` 失敗之後的那次模型呼叫沒有正確處理錯誤，再往前追，是錯誤訊息裡沒有明說「退款未執行，請不要告訴使用者已退款」。第四步的分類讓修正有方向：「tool 錯誤被忽略」通常改 harness 或錯誤訊息，「選錯 tool」通常改 tool 描述（第 5 章），「繞圈」改停止條件與 tool 回傳（第 4 章），「context 過長」改 compaction（第 10 章）。第五步的 replay 是 trace 最被低估的用途：只要 trace 存了每一次模型回應（至少是 tool calls 與 stop reason），就能把它變成第 4 章的 ScriptedModel 劇本，在本機一字不差地重跑 harness，驗證修正。最後一步把個案變成查詢，回答阿哲一定會問的「還有多少人遇到」。

| 失敗類型 | 在 trace 上的特徵 | 查詢條件（概念） | 常見根因 |
|---|---|---|---|
| 說成功、其實失敗 | 回覆宣稱副作用完成，但對應 tool span 為 ERROR 或不存在 | `claims 含 refund_done` 且沒有 status=OK 的 `execute_tool refund` | 錯誤訊息不夠明確；沒有結果驗證 |
| 繞圈 | 相同 `gen_ai.tool.name` 與參數的 span 連續出現 | 同一 trace 中相同 tool＋參數雜湊的次數 ≥ 3 | tool 回傳沒有新資訊；缺少重複偵測 |
| 選錯 tool | 該用 A 的情境呼叫了 B，或呼叫後立刻改呼叫另一個 | 「呼叫後下一步換 tool」的比例，依 tool 對分組 | tool 名稱或描述相近 |
| 參數錯誤 | `execute_tool` 的 `error.type` 為驗證錯誤 | 依 tool 統計驗證錯誤率 | schema 缺例子、enum 不清楚 |
| context 爆量 | 某一步 `input_tokens` 突然暴增 | 單次 input 超過 p99，或相鄰兩步差異過大 | 未截斷的大 tool 結果 |
| cache 失效 | `cache_read` 在 session 中途歸零 | 第 k 步 cache_read 遠小於第 k−1 步的 input | 中途改了 system 或 tool 清單（第 9 章） |
| 外部依賴慢 | 某個 `execute_tool` 或 CLIENT span 佔了大部分時間 | 依 tool 的 p95 耗時，及其在 trace 總時長的佔比 | 下游服務、沒有 timeout |

這張表是除錯的「症狀字典」。每一列都能寫成一個固定的查詢，存成儀表板上的一格或一條告警。第一列的查詢依賴 29.5 節的衍生訊號：沒有 `claims` 屬性，你只能對原文做全文搜尋，而 production 的原文多半沒有存。「說成功、其實失敗」是客服 agent 最傷信任的一類失敗，值得在 harness 層加上結構性的防線，例如把「宣稱已退款」與「有成功的 refund 結果」做一致性檢查，不一致就攔下回覆，第 32 章會談輸出 guardrail 的設計。

查詢語言依平台而異：有的平台提供類 SQL 查詢 span 表，有的用自己的查詢語法或 UI 篩選器。原理都一樣：span 是一張表，欄位是 trace id、span id、parent id、名稱、時間、status 與屬性；trace 層級的條件（「這條 trace 裡有 A 卻沒有 B」）用 group by trace id 表達。只要屬性命名一致，這些查詢就能在平台之間搬移。

從 trace 找到的失敗，最終要回到第 27 章的 **error analysis**：抽樣一批失敗 trace，逐條讀、寫下第一個出錯的地方，再把相似的歸成類別，數一數每類佔多少。這個步驟沒辦法完全自動化，但 trace 讓它變得可行：讀一條結構化的 span 樹，比讀一份 messages JSON 快得多。分類結果決定接下來的投資：佔 40% 的類別先修，佔 2% 的先記下來。

## 29.8 線上監控指標、取樣與告警

除錯是事後的，監控是持續的。**線上監控**要回答兩個問題：「現在有沒有出事」與「這個版本比上個版本好還是壞」。agent 的監控指標可以分成四組：品質、可靠性、成本、安全。

| 組別 | 指標 | 怎麼算 | 告警或檢視方式 |
|---|---|---|---|
| 品質 | 任務成功率（代理指標） | done 且無可疑訊號、未轉真人、未短時間重問 | 依功能與租戶，對上一週同時段比較 |
| 品質 | 線上 eval 分數 | 抽樣 trace 交給 LLM judge 或規則評分（第 27 章） | 版本切換後的分數差異 |
| 品質 | 使用者負評率、轉真人率 | 回饋事件與 handoff span | 突然上升即調查 |
| 可靠性 | 非正常結束比例 | run status 為 max_steps、budget、loop、max_tokens 的比例 | 任一類別超過基準的數倍 |
| 可靠性 | 各 tool 錯誤率與 p95 耗時 | `execute_tool` 依 tool 名稱分組 | 單一 tool 異常時通知該 tool 的 owner |
| 可靠性 | 端到端延遲、首字延遲 | root span 耗時；串流時第一個輸出事件的時間 | 依互動類型設 SLO（第 34 章） |
| 成本 | 每任務成本、每次成功任務成本 | span 上的成本加總 | 日成本超出預測區間、單一 trace 超過上限 |
| 成本 | cache 命中率、p95 步數、單次 input 的 p99 | chat span 的 usage | 部署後明顯變化 |
| 安全 | guardrail 觸發率、PII 偵測數、核准被拒率 | guardrail 與 approval span、衍生訊號 | 觸發率驟升可能是攻擊或誤擋 |

這張表刻意把「品質」放在第一組，因為它最難量、也最容易被省略。可靠性與成本指標全部能從 span 機械地算出來；品質需要額外的判斷，來源是三種：規則（回覆是否包含必要的政策說明）、使用者行為（轉真人、重問、負評）、以及抽樣的線上 eval。線上 eval 不必每條 trace 都跑，抽樣 1% 到 5% 交給 judge 模型評分就足以看出趨勢；被評為低分的 trace 自動進入人工標註佇列，標註後成為 eval set 的新題目。這就是 production trace → 標註 → dataset → 回歸測試 → 部署的飛輪。

監控資料量是另一個現實問題。青鳥每天數萬次對話，每次十幾個 span，全部保存的儲存與查詢成本很高，而 99% 的正常 trace 很少被讀。**sampling**（取樣）就是決定哪些 trace 要留。**head sampling** 在請求開始時就決定（例如固定留 10%），簡單、便宜，但它無法知道這條 trace 最後會不會出錯，於是寶貴的失敗案例也會被丟掉 90%。**tail sampling** 在整條 trace 結束後才決定，能依結果保留：有錯誤的全留、成本或延遲異常的全留、被負評的全留，其餘正常 trace 只留一小部分當基準。代價是 collector 要暫存整條 trace 直到結束，記憶體與架構都更複雜。

```python
from __future__ import annotations

import hashlib
import random
from collections import Counter

random.seed(29)


def keep_reason(t: dict, baseline_rate: float = 0.05) -> str | None:
    """tail sampling：整條 trace 結束後才決定要不要留，所以能看到結果再決定。"""
    if t["error_spans"]:
        return "有錯誤 span"
    if t["status"] != "done":
        return f"非正常結束（{t['status']}）"
    if t["flagged"]:
        return "使用者負評或線上 eval 標記"
    if t["usd"] > 0.05:
        return "高成本"
    if t["ms"] > 15_000:
        return "高延遲"
    # 其餘正常 trace 依 trace_id 雜湊取樣：同一條 trace 在每台 collector 上的決定一致
    bucket = int(hashlib.sha256(t["trace_id"].encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "基準取樣" if bucket < baseline_rate else None


traces = []
for i in range(10_000):                               # 模擬一天中的一萬條客服 trace
    r = random.random()
    traces.append({
        "trace_id": f"{i:032x}",
        "error_spans": 1 if r < 0.04 else 0,
        "status": "max_steps" if 0.04 <= r < 0.05 else "done",
        "flagged": 0.05 <= r < 0.06,
        "usd": 0.08 if 0.06 <= r < 0.07 else 0.01,
        "ms": random.choice([2_000, 4_000, 6_000, 20_000 if r > 0.99 else 3_000]),
    })

reasons = Counter(keep_reason(t) for t in traces)
kept = sum(n for k, n in reasons.items() if k)
for reason, n in reasons.most_common():
    print(f"{n:>5}  {reason or '丟棄'}")
print(f"保留 {kept} / {len(traces)} 條（{kept / len(traces):.1%}），所有異常 trace 都在裡面")
assert all(keep_reason(t) for t in traces if t["error_spans"] or t["status"] != "done")
assert 0.1 < kept / len(traces) < 0.25
```

```text
 8769  丟棄
  480  基準取樣
  405  有錯誤 span
  120  使用者負評或線上 eval 標記
  105  高成本
   93  非正常結束（max_steps）
   28  高延遲
保留 1231 / 10000 條（12.3%），所有異常 trace 都在裡面
```

這份輸出模擬一天一萬條 trace 的取樣結果。有錯誤 span、非正常結束、被標記、高成本、高延遲的 trace 全部保留，加起來約 750 條；其餘正常 trace 依 trace id 的雜湊保留 5%，約 480 條，當作「正常長什麼樣子」的基準。總共保留 12.3%，卻包含了 100% 的異常案例；如果改用 head sampling 留 12.3%，異常案例也只會留下 12.3%。用 trace id 的雜湊而不是隨機數決定基準取樣，是因為一條 trace 的 span 可能經過多個 collector，每個 collector 用同一個雜湊規則會做出一致的決定，不會出現「這條 trace 只留了一半」。

有兩個細節要注意。第一，**成本與用量的 metrics 不能從取樣後的 trace 算**：丟掉 88% 的 trace 之後再加總成本，數字就錯了。成本、token、錯誤率等聚合指標要在取樣之前、由 metrics 管線或 collector 在全量資料上計算，trace 只負責「讓你看到個案」。第二，告警要設在比率與趨勢上，而不是單一事件：單條 trace 出錯在 agent 系統裡是常態，「tool 錯誤率比過去七天同時段高三倍」才值得半夜叫醒人。第 34 章會把這些指標接到 SLO 與 error budget 上。

## 29.9 動手做：給 loom 加上 loom.tracing

這一節把本章的概念組成 `loom.tracing` 模組，並包住一個沿用第 4 章形狀的最小 loop。程式分成五個部分。`Clock` 是模擬時鐘，讓每個 span 的耗時可以重現。`Span` 與 `Tracer` 是 tracer 本體：`tracer.span()` 是一個 context manager，用 `contextvars` 記住「目前的 span」，所以巢狀呼叫時 parent-child 關係自動建立，不必把 span 當參數一路傳下去；span 結束時依序執行 processors，再放進 `finished` 清單（相當於匯出）。接著是匯出前的遮蔽 processor 與 HMAC 假名化，以及依版本化價目表計算成本的 `cost_usd()`。

`TracedAgent` 在三個位置建立 span：整次執行是 `invoke_agent`，每次模型呼叫是 `chat`，每次 tool 執行是 `execute_tool`，屬性名稱依 29.4 節的 GenAI 慣例，業務屬性放在 `bluebird.*`。內容擷取由 `capture_content` 控制，預設關閉。tool 丟出例外時，span 標為 ERROR 並記下 exception 事件，但例外不往外丟，而是照第 4 章的做法轉成錯誤訊息回填給模型。程式中 cache 讀寫的屬性名稱（`gen_ai.usage.cache_read.input_tokens`、`gen_ai.usage.cache_creation.input_tokens`）是依規格草案的寫法，撰寫時未能逐字核對，請以官方最新版本為準。模型的 usage 用字元數粗估，並假設前綴完全不變，所以每一輪的 cache 讀取量等於上一輪的輸入量；價格是示意值，不是任何供應商的報價。

最後跑三個 session：conv-001 是正常查詢；conv-002 重現 B-2077 事故，使用者訊息中含有手機與 email，`refund` 失敗後劇本讓模型回覆「已為您完成退款」；conv-003 沒有開啟內容擷取，模型連續查了四次物流，最後以步數用完結束。輸出包括兩棵 span 樹與三個查詢。

```python
from __future__ import annotations

import contextvars
import hashlib
import hmac
import json
import re
from contextlib import contextmanager
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
    return ModelResponse(tool_calls=[ToolCall(call_id, name, args)], stop_reason="tool_use")


def say(text: str) -> ModelResponse:
    return ModelResponse(text=text)


# ───────────────────────── loom.tracing ─────────────────────────
class Clock:
    """模擬時鐘（毫秒）：讓 duration 可重現，不必真的 sleep。"""
    def __init__(self) -> None:
        self.ms = 0

    def advance(self, ms: int) -> None:
        self.ms += ms


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_id: str | None
    kind: str                                   # INTERNAL｜CLIENT
    start: int
    end: int = 0
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    status: str = "UNSET"                       # UNSET｜OK｜ERROR

    def set(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def event(self, name: str, at: int, **attrs: Any) -> None:
        self.events.append({"name": name, "time": at, "attributes": attrs})

    def fail(self, error_type: str, at: int, message: str) -> None:
        self.status = "ERROR"
        self.attributes["error.type"] = error_type
        self.event("exception", at, **{"exception.type": error_type, "exception.message": message})


class Tracer:
    def __init__(self, clock: Clock, processors: list[Callable[[Span], Span]] | None = None):
        self.clock, self.processors = clock, processors or []
        self.finished: list[Span] = []
        self._current: contextvars.ContextVar[Span | None] = contextvars.ContextVar("span", default=None)
        self._n = 0

    def _id(self, hex_len: int) -> str:
        self._n += 1                           # 確定性 id：讓輸出可重現；production 用隨機 id
        return hashlib.sha256(f"loom-{self._n}".encode()).hexdigest()[:hex_len]

    @contextmanager
    def span(self, name: str, kind: str = "INTERNAL", attributes: dict[str, Any] | None = None):
        parent = self._current.get()           # parent 由 context 決定，不必手動傳遞
        sp = Span(name, parent.trace_id if parent else self._id(32), self._id(16),
                  parent.span_id if parent else None, kind, self.clock.ms, attributes=dict(attributes or {}))
        token = self._current.set(sp)
        try:
            yield sp
            if sp.status == "UNSET":
                sp.status = "OK"
        except Exception as exc:               # 未處理的例外：記下來再往外丟
            sp.fail(type(exc).__name__, self.clock.ms, str(exc))
            raise
        finally:
            sp.end = self.clock.ms
            self._current.reset(token)
            for process in self.processors:    # 匯出前處理：遮蔽一定在離開 process 之前
                sp = process(sp)
            self.finished.append(sp)


# ── 匯出前的遮蔽 processor ──
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
TW_MOBILE = re.compile(r"09\d{2}-?\d{3}-?\d{3}")

def redact_text(s: str) -> str:
    return TW_MOBILE.sub("<PHONE>", EMAIL.sub("<EMAIL>", s))

def redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    return value

def redaction_processor(sp: Span) -> Span:
    sp.attributes = {k: redact(v) for k, v in sp.attributes.items()}
    for ev in sp.events:
        ev["attributes"] = redact(ev["attributes"])
    return sp

PSEUDONYM_KEY = b"rotate-me-quarterly"        # 示意；實務放 secrets manager

def pseudonym(user_id: str) -> str:
    """keyed hash：同一使用者得到同一代號（可 join），但沒有 key 就無法反推。"""
    return "u_" + hmac.new(PSEUDONYM_KEY, user_id.encode(), hashlib.sha256).hexdigest()[:10]


# ── 成本：寫入時就算好，並記下價目表版本 ──
PRICES = {"version": "price-demo-2026-10",   # 示意價格（USD／百萬 tokens），不是任何供應商的報價
          "sim-large": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75}}

def cost_usd(model: str, u: dict[str, int]) -> float:
    p = PRICES[model]
    fresh = u["input_tokens"] - u["cache_read"] - u["cache_write"]
    return (fresh * p["input"] + u["cache_read"] * p["cache_read"] + u["cache_write"] * p["cache_write"]
            + u["output_tokens"] * p["output"]) / 1_000_000


# ───────────── 被 instrument 的最小 loop（沿用第 4 章的形狀）─────────────
class TracedAgent:
    def __init__(self, name: str, model: ScriptedModel, tools: dict[str, Callable[..., Any]],
                 tracer: Tracer, clock: Clock, capture_content: bool = False, max_steps: int = 4):
        self.name, self.model, self.tools = name, model, tools
        self.tracer, self.clock = tracer, clock
        self.capture_content, self.max_steps = capture_content, max_steps   # 內容擷取預設關閉

    def run(self, text: str, conversation_id: str, tenant: str, user_id: str) -> str:
        attrs = {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": self.name,
                 "gen_ai.conversation.id": conversation_id, "bluebird.tenant.id": tenant,
                 "bluebird.user.pseudonym": pseudonym(user_id), "bluebird.prompt.version": "support-v14"}
        with self.tracer.span(f"invoke_agent {self.name}", "INTERNAL", attrs) as root:
            messages: list[dict] = [{"role": "user", "content": text}]
            prev_input, status, out = 0, "max_steps", "步驟用完了，已轉給真人同事。"
            for _ in range(self.max_steps):
                resp = self._chat(messages, prev_input)
                prev_input = resp.usage["input_tokens"]
                messages.append({"role": "assistant", "content": resp.text,
                                 "tool_calls": [vars(tc) for tc in resp.tool_calls]})
                if not resp.tool_calls:
                    status, out = "done", resp.text
                    break
                for tc in resp.tool_calls:
                    messages.append(self._execute_tool(tc))
            root.set("bluebird.run.status", status)
            # 不存原文也能查詢：寫入時萃取結構化訊號
            root.set("bluebird.claims", ["refund_done"] if re.search(r"已.{0,4}退款", out) else [])
            if self.capture_content:
                root.set("gen_ai.output.messages", [{"role": "assistant", "content": out}])
            return out

    def _chat(self, messages: list[dict], prev_input: int) -> ModelResponse:
        model = "sim-large"
        with self.tracer.span(f"chat {model}", "CLIENT", {
                "gen_ai.operation.name": "chat", "gen_ai.provider.name": "scripted",
                "gen_ai.request.model": model}) as sp:
            if self.capture_content:
                sp.set("gen_ai.input.messages", json.loads(json.dumps(messages)))
            resp = self.model.complete(messages)
            self.clock.advance(600)
            inp = len(json.dumps(messages, ensure_ascii=False)) // 2 + 300   # 300 ≈ system＋tools
            u = {"input_tokens": inp, "output_tokens": 40,
                 "cache_read": prev_input, "cache_write": inp - prev_input}  # 前綴不變：上一輪全部命中
            resp.usage = u
            sp.set("gen_ai.usage.input_tokens", u["input_tokens"])
            sp.set("gen_ai.usage.output_tokens", u["output_tokens"])
            sp.set("gen_ai.usage.cache_read.input_tokens", u["cache_read"])
            sp.set("gen_ai.usage.cache_creation.input_tokens", u["cache_write"])
            sp.set("gen_ai.response.finish_reasons", [resp.stop_reason])
            sp.set("bluebird.cost.usd", round(cost_usd(model, u), 6))
            sp.set("bluebird.price.version", PRICES["version"])
            return resp

    def _execute_tool(self, tc: ToolCall) -> dict:
        attrs = {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": tc.name,
                 "gen_ai.tool.call.id": tc.id, "gen_ai.tool.type": "function"}
        with self.tracer.span(f"execute_tool {tc.name}", "INTERNAL", attrs) as sp:
            if self.capture_content:
                sp.set("gen_ai.tool.call.arguments", tc.args)
            self.clock.advance(TOOL_LATENCY_MS.get(tc.name, 50))
            try:
                content, is_error = json.dumps(self.tools[tc.name](**tc.args), ensure_ascii=False), False
            except Exception as exc:          # 回填給模型的是觀察；trace 裡記的是完整錯誤
                sp.fail(type(exc).__name__, self.clock.ms, str(exc))
                content, is_error = f"{type(exc).__name__}: {exc}", True
            if self.capture_content:
                sp.set("gen_ai.tool.call.result", content)
            return {"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": content, "is_error": is_error}


# ───────────────────────── 青鳥的假後端與三個 session ─────────────────────────
TOOL_LATENCY_MS = {"get_order": 40, "get_shipment": 1800, "refund": 90}
ORDERS = {"B-1042": "shipped", "B-2077": "shipped"}

def get_order(order_id: str) -> dict:
    return {"order_id": order_id, "status": ORDERS[order_id], "tracking": "TC-88301"}

def get_shipment(tracking: str) -> dict:
    return {"tracking": tracking, "location": "台中轉運中心", "eta": "查詢中"}

def refund(order_id: str) -> str:
    if ORDERS[order_id] == "shipped":
        raise ValueError(f"訂單 {order_id} 已出貨，不能直接退款；請改用 create_return")
    return "已退款"

TOOLS = {"get_order": get_order, "get_shipment": get_shipment, "refund": refund}
clock = Clock()
tracer = Tracer(clock, processors=[redaction_processor])

runs = [
    ("conv-001", "t-小森選物", "user-881", "B-1042 到哪了？", True,
     [call("get_order", order_id="B-1042"), call("get_shipment", "c2", tracking="TC-88301"),
      say("B-1042 已出貨，目前在台中轉運中心。")]),
    ("conv-002", "t-晨光文具", "user-512", "B-2077 幫我退款，電話 0912-345-678，amy@example.com", True,
     [call("refund", order_id="B-2077"), say("好的，已為您完成退款，款項 3–5 天入帳。")]),   # 幻覺式成功
    ("conv-003", "t-小森選物", "user-881", "TC-88301 為什麼還沒到", False,
     [call("get_shipment", f"c{i}", tracking="TC-88301") for i in range(4)]),
]
for conv, tenant, user, text, capture, script in runs:
    TracedAgent("bluebird-support", ScriptedModel(script), TOOLS, tracer, clock,
                capture_content=capture).run(text, conv, tenant, user)


# ───────────────────────── 輸出：span 樹 ─────────────────────────
def children(spans: list[Span], parent_id: str | None) -> list[Span]:
    return sorted((s for s in spans if s.parent_id == parent_id), key=lambda s: s.start)

def summary(s: Span) -> str:
    a = s.attributes
    if a["gen_ai.operation.name"] == "chat":
        return (f"in={a['gen_ai.usage.input_tokens']} cache_read={a['gen_ai.usage.cache_read.input_tokens']}"
                f" out={a['gen_ai.usage.output_tokens']} ${a['bluebird.cost.usd']:.5f}")
    if s.status == "ERROR":
        return f"error.type={a['error.type']}"
    return ""

def print_tree(spans: list[Span], parent_id: str | None = None, prefix: str = "") -> None:
    kids = children(spans, parent_id)
    for i, s in enumerate(kids):
        last = i == len(kids) - 1
        branch = "" if parent_id is None else ("└─ " if last else "├─ ")
        line = f"{prefix}{branch}{s.name:<26} {s.end - s.start:>5}ms {s.status:<5} {summary(s)}"
        print(line.rstrip())
        print_tree(spans, s.span_id, prefix + ("" if parent_id is None else ("   " if last else "│  ")))

def traces() -> dict[str, list[Span]]:
    out: dict[str, list[Span]] = {}
    for s in tracer.finished:
        out.setdefault(s.trace_id, []).append(s)
    return out

def root_of(spans: list[Span]) -> Span:
    return next(s for s in spans if s.parent_id is None)

T = traces()
by_conv = {root_of(sp).attributes["gen_ai.conversation.id"]: sp for sp in T.values()}
t2 = by_conv["conv-002"]
r2 = root_of(t2)
print(f"── span 樹  trace={r2.trace_id[:8]}…  conversation=conv-002  user={r2.attributes['bluebird.user.pseudonym']}")
print_tree(t2)
tool_span = next(s for s in t2 if s.name == "execute_tool refund")
print("   使用者訊息（已遮蔽）:", next(s for s in t2 if s.name.startswith("chat"))
      .attributes["gen_ai.input.messages"][0]["content"])
print("   refund 例外事件:", tool_span.events[0]["attributes"]["exception.message"])
print("\n── span 樹  conversation=conv-003（未開內容擷取）")
print_tree(by_conv["conv-003"])

# ───────────────────────── 查詢一：說成功、其實失敗 ─────────────────────────
print("\n── 查詢一：回覆宣稱已退款，但沒有任何成功的 refund span")
suspicious = []
for spans in T.values():
    root = root_of(spans)
    ok_refund = any(s.attributes.get("gen_ai.tool.name") == "refund" and s.status == "OK" for s in spans)
    if "refund_done" in root.attributes["bluebird.claims"] and not ok_refund:
        suspicious.append(root.attributes["gen_ai.conversation.id"])
        failed = [s for s in spans if s.status == "ERROR"]
        print(f"   {root.attributes['gen_ai.conversation.id']}  首個錯誤 span：{failed[0].name}"
              f"（{failed[0].attributes['error.type']}），之後模型仍回覆成功")

# ───────────────────────── 查詢二：tool 的錯誤率與延遲 ─────────────────────────
print("\n── 查詢二：各 tool 的呼叫數、錯誤數、最大延遲")
stats: dict[str, list[int]] = {}
for s in tracer.finished:
    if s.attributes.get("gen_ai.operation.name") == "execute_tool":
        st = stats.setdefault(s.attributes["gen_ai.tool.name"], [0, 0, 0])
        st[0] += 1
        st[1] += s.status == "ERROR"
        st[2] = max(st[2], s.end - s.start)
for name, (n, err, mx) in sorted(stats.items()):
    print(f"   {name:<13} calls={n}  errors={err}  max={mx}ms")

# ───────────────────────── 查詢三：成本儀表板 ─────────────────────────
print("\n── 查詢三：依租戶彙總成本與「每次成功任務成本」")
board: dict[str, dict[str, float]] = {}
for spans in T.values():
    root = root_of(spans)
    row = board.setdefault(root.attributes["bluebird.tenant.id"], {"runs": 0, "done": 0, "usd": 0.0, "steps": 0})
    row["runs"] += 1
    conv = root.attributes["gen_ai.conversation.id"]
    row["done"] += root.attributes["bluebird.run.status"] == "done" and conv not in suspicious
    row["usd"] += sum(s.attributes.get("bluebird.cost.usd", 0) for s in spans)
    row["steps"] += sum(s.attributes["gen_ai.operation.name"] == "chat" for s in spans)
for tenant, row in board.items():
    per_success = f"${row['usd'] / row['done']:.5f}" if row["done"] else "無成功任務"
    print(f"   {tenant}  runs={row['runs']:.0f} 成功={row['done']:.0f} 模型呼叫={row['steps']:.0f}"
          f"  總成本=${row['usd']:.5f}  每次成功={per_success}")

# ───────────────────────── 驗證 ─────────────────────────
dump = json.dumps([vars(s) for s in tracer.finished], ensure_ascii=False)
assert "0912-345-678" not in dump and "amy@example.com" not in dump and "user-512" not in dump
assert suspicious == ["conv-002"]
assert root_of(by_conv["conv-003"]).attributes["bluebird.run.status"] == "max_steps"
assert "gen_ai.input.messages" not in json.dumps([vars(s) for s in by_conv["conv-003"]])  # 沒開擷取就沒有內容
assert all(s.parent_id in {x.span_id for x in tracer.finished} for s in tracer.finished if s.parent_id)
print("\n驗證通過：PII 已遮蔽、可疑 session 已找出、每個 span 都接得回 parent")
```

```text
── span 樹  trace=d18f2be3…  conversation=conv-002  user=u_0a369f5ea4
invoke_agent bluebird-support  1290ms OK
├─ chat sim-large               600ms OK    in=338 cache_read=0 out=40 $0.00187
├─ execute_tool refund           90ms ERROR error.type=ValueError
└─ chat sim-large               600ms OK    in=467 cache_read=338 out=40 $0.00119
   使用者訊息（已遮蔽）: B-2077 幫我退款，電話 <PHONE>，<EMAIL>
   refund 例外事件: 訂單 B-2077 已出貨，不能直接退款；請改用 create_return

── span 樹  conversation=conv-003（未開內容擷取）
invoke_agent bluebird-support  9600ms OK
├─ chat sim-large               600ms OK    in=324 cache_read=0 out=40 $0.00181
├─ execute_tool get_shipment   1800ms OK
├─ chat sim-large               600ms OK    in=472 cache_read=324 out=40 $0.00125
├─ execute_tool get_shipment   1800ms OK
├─ chat sim-large               600ms OK    in=620 cache_read=472 out=40 $0.00130
├─ execute_tool get_shipment   1800ms OK
├─ chat sim-large               600ms OK    in=768 cache_read=620 out=40 $0.00134
└─ execute_tool get_shipment   1800ms OK

── 查詢一：回覆宣稱已退款，但沒有任何成功的 refund span
   conv-002  首個錯誤 span：execute_tool refund（ValueError），之後模型仍回覆成功

── 查詢二：各 tool 的呼叫數、錯誤數、最大延遲
   get_order     calls=1  errors=0  max=40ms
   get_shipment  calls=5  errors=0  max=1800ms
   refund        calls=1  errors=1  max=90ms

── 查詢三：依租戶彙總成本與「每次成功任務成本」
   t-小森選物  runs=2 成功=1 模型呼叫=7  總成本=$0.01006  每次成功=$0.01006
   t-晨光文具  runs=1 成功=0 模型呼叫=2  總成本=$0.00305  每次成功=無成功任務

驗證通過：PII 已遮蔽、可疑 session 已找出、每個 span 都接得回 parent
```

逐段解說這份輸出。

**第一棵 span 樹（conv-002）**就是 29.3 節瀑布圖的實際版本。root 是 `invoke_agent bluebird-support`，總耗時 1,290 毫秒，底下依時間排著三個子 span。第一次 `chat` 的 `cache_read=0`，因為這是 session 的第一次呼叫，338 個輸入 token 全部是 cache 寫入，成本 0.00187 美元；第二次 `chat` 的 `cache_read=338`，正好等於上一輪的輸入量，所以雖然輸入變多（467），成本反而降到 0.00119 美元，這就是第 9 章說的「前綴不變、尾端追加」在帳單上的樣子。中間的 `execute_tool refund` 是 ERROR，`error.type=ValueError`。標題列的 `user=u_0a369f5ea4` 是假名，原本的 `user-512` 從未進入 trace。接下來兩行顯示內容擷取有開啟時，使用者訊息中的手機與 email 已在匯出前被換成 `<PHONE>` 與 `<EMAIL>`，而 exception 事件保留了完整的業務錯誤訊息，給工程師除錯用。

**第二棵 span 樹（conv-003）**呈現另一種失敗。四次 `chat` 與四次 `get_shipment` 交錯，每次物流查詢都花 1,800 毫秒，root 總耗時 9.6 秒，其中 7.2 秒在等物流商；每次 `chat` 的 `cache_read` 都等於上一次的 `in`，代表前綴健康，成本隨步數緩慢上升。root 的 status 是 OK，因為沒有任何技術錯誤；但它的 `bluebird.run.status` 是 max_steps（assert 驗證了這一點），顧客其實沒有得到答案。這正是 29.3 節強調的區分：span status 與業務結果是兩回事。這個 session 沒有開啟內容擷取，assert 也驗證了它的 span 上完全沒有 `gen_ai.input.messages`，但我們仍然能看出它在繞圈、時間花在哪裡、花了多少錢。

**查詢一**找出「回覆宣稱已退款，但沒有任何成功的 refund span」的 session。它只用了兩個欄位：root 上的衍生訊號 `bluebird.claims`，以及 `execute_tool refund` span 的 status，完全不需要讀原文。結果只有 conv-002，並且指出第一個錯誤 span 是 `execute_tool refund`。在 production 上，這個查詢會回傳所有同類的 session，回答「還有多少顧客被告知已退款但其實沒有」。

**查詢二**依 tool 統計呼叫數、錯誤數與最大延遲：`get_shipment` 被呼叫 5 次（conv-001 一次、conv-003 四次），最大延遲 1,800 毫秒，是延遲的主要來源；`refund` 一次呼叫一次錯誤。真實系統會用 p95 而不是最大值，並依時間序列畫出來。

**查詢三**是成本儀表板的最小版本。小森選物有兩個 session、一個成功，總成本 0.01006 美元，其中 conv-003 這個失敗的 session 就佔了大半（四次模型呼叫），所以「每次成功任務成本」等於總成本，是單次平均成本的兩倍。晨光文具唯一的 session 被查詢一判定為可疑，不算成功，因此顯示「無成功任務」。如果只看「每任務成本」，晨光文具看起來比小森選物便宜，但它付的錢買到的是一句錯誤的回覆。

最後的 assert 鎖住了四個性質：匯出的所有 span 裡找不到手機、email 與原始使用者 id；查詢一只找到 conv-002；conv-003 的業務狀態是 max_steps 且沒有任何內容欄位；每個非 root span 的 parent 都存在，整棵樹沒有斷枝。

| 本章機制 | 在程式中的位置 | 對應小節 | production 版本要補的 |
|---|---|---|---|
| parent-child 自動建立 | `Tracer.span()` 的 `contextvars` | 29.3 | 跨執行緒與 asyncio task 的 context 複製 |
| GenAI 慣例命名 | `TracedAgent` 的三種 span | 29.4 | 依規格版本做名稱對應；metrics 一併輸出 |
| 內容 opt-in | `capture_content` 參數 | 29.5 | 依租戶與環境設定，開啟要留稽核 |
| 遮蔽與假名化 | `redaction_processor`、`pseudonym()` | 29.5 | allowlist、更多 PII 類型、金鑰輪替 |
| 寫入時算成本 | `cost_usd()` 與 `bluebird.price.version` | 29.6 | 每家供應商的 usage 語意、tool 外部成本 |
| 衍生訊號 | root 的 `bluebird.claims` | 29.5、29.7 | 用規則加小模型萃取多種副作用宣稱 |
| 從 trace 查失敗 | 查詢一、二、三 | 29.7 | 存成儀表板與告警；接上 tail sampling |

`loom.tracing` 刻意沒有做的事也要列出來：匯出是同步放進清單，沒有背景批次與失敗重送；id 是確定性的，production 必須用密碼學安全的隨機 id；沒有 tail sampling 與 metrics；沒有處理 parallel tool calls 時多個 span 同時開啟的情況（`contextvars` 在 asyncio 中會自動依 task 複製，thread pool 則要手動傳遞 context）。第 24 章的 runtime 已經透過 `on_event` 擴充點把核心事件交給 tracer，正式版的 `loom.tracing` 就從那裡接入；第 45 章組裝完整 `loom` 時，會讓這個 tracer 可以替換成官方 OpenTelemetry SDK，而 instrumentation 的程式碼不變。

## 29.10 實務應用

同一套 trace、span 與遮蔽的原理，在不同類型的 agent 產品中，重點完全不同。

**情境一：多租戶客服 agent（青鳥的主線）**。客服的 trace 短（通常十幾個 span）但量大，最重要的是三件事。一是**租戶隔離**：每個 span 帶租戶 id，觀測後端依租戶控管存取，商家的客戶成功經理只能看自己租戶的 trace，而且只能看遮蔽後的版本。二是**語意失敗的偵測**：「說成功、其實失敗」「承諾了政策不允許的補償」這類失敗要有衍生訊號與固定查詢，並接上輸出 guardrail。三是**成本歸因到租戶**：青鳥的定價若是按對話數收費，依租戶的「每次成功任務成本」直接決定哪些方案在賠錢，這是第 37 章單位經濟的資料來源。阿哲的「帳單漲了三成」，在這套儀表板上最後追到一個大型租戶上線了新的商品目錄，使得知識庫檢索結果變長、單次 input tokens 上升，而不是流量增加。

**情境二：coding agent（內部或 CI 中的背景 agent）**。coding agent 的一次任務可能有數百個 span，執行數十分鐘，trace 的形狀和客服完全不同：大部分時間花在 sandbox 裡的指令（安裝依賴、跑測試），模型呼叫反而是少數。這裡要特別記錄每個 shell 指令的耗時與 exit code、檔案修改的摘要（不存完整檔案內容，存 diff 的統計與路徑）、以及測試結果；除錯時最常問的是「它為什麼改了這個檔案」與「這一個小時花在哪」。因為任務長，要能把 trace 對上第 22 章的 durable run id，在 worker 重啟後接續同一條 trace，或用 link 把前後兩段關聯起來。程式碼本身可能是機密，內容擷取的預設要更保守。公開資料中，Claude Code 的文件描述可以透過 OpenTelemetry 匯出使用量指標與事件，讓組織追蹤 token 用量與成本；本書未逐項查證，細節以官方文件為準。

**情境三：multi-agent 的營運 research agent**。research agent 的 trace 是一棵很寬的樹：lead agent 同時派出多個 subagent，每個 subagent 又有自己的搜尋與閱讀步驟。觀測的重點是**成本倍數與平行效率**：每個 subagent 子樹花了多少 token、有多少子樹的結果最後根本沒被引用、lead agent 等待最慢的 subagent 等了多久。Anthropic 在公開的工程文章中描述他們的 multi-agent research 系統時提到，加上完整的 production tracing 之後才能診斷 agent 為什麼失敗，並且是在不監控個別對話內容的前提下，觀察 agent 的決策模式與互動結構；這和 29.5 節「用結構與衍生訊號回答問題、少存原文」的方向一致。對青鳥的月度分析 agent 來說，最有用的單一指標是「每份報告的成本」與「每份報告被營運人員修改的比例」。

**情境四：受監管產業的企業 agent（金融、醫療、法律）**。這類 agent 的 trace 同時是除錯工具與合規證據的入口，兩者的要求互相拉扯：合規要求保存「誰在何時根據什麼做了什麼決定」，隱私要求盡量少存個資。常見做法是把三種資料分開：debug trace（短期、遮蔽、工程師可讀）、稽核日誌（長期、append-only、防竄改，第 33 章）、以及內容保管庫（加密、存取需要審批）。三者用 trace id 關聯，刪除權請求時只需要處理內容保管庫與假名對照表。部分組織會選擇自架觀測平台，讓 trace 不離開自己的雲端帳號。

| 情境 | trace 形狀 | 最重要的指標 | 內容擷取預設 | 特別注意 |
|---|---|---|---|---|
| 多租戶客服 | 短、量大 | 每次成功任務成本、語意失敗率 | 關閉，個案調查時短期開啟 | 租戶隔離、衍生訊號 |
| coding agent | 長、深、以 sandbox 為主 | 任務耗時分布、測試通過率 | 保守，存 diff 統計 | durable run id 與 trace 的對應 |
| multi-agent research | 寬、平行 | 子樹成本、未被引用的子樹比例 | 依資料敏感度 | 跨 agent 的 context 傳遞 |
| 受監管企業 agent | 中等，帶核准節點 | 核准耗時、政策違規率 | 分離到內容保管庫 | debug trace 與稽核日誌分開治理 |

這張表的共同點是：instrumentation 的程式碼幾乎相同，差別在取樣政策、內容擷取政策、保存期限與存取控制。所以 `loom.tracing` 把這些做成設定，而不是寫死在 tracer 裡。

> [!note] 2026 現況
> 截至 2026 年 10 月，主流框架與觀測平台大多以 OpenTelemetry 為共同語言（以下依各家公開文件整理，功能細節會變動，請以官方為準）。OpenAI Agents SDK 內建 tracing，可透過 trace processor 把資料送到其他平台；Google ADK、Microsoft Agent Framework、Strands Agents、Pydantic AI（搭配 Logfire）與 CrewAI 等都輸出 OTel 或提供整合；LangGraph 的觀測主要搭配 LangSmith，LangSmith 也接受 OTel 資料。觀測與評估平台方面，Langfuse 是開源、可自架的 tracing 與 eval 平台，2026 年 1 月由 ClickHouse 收購並承諾維持開源；Arize Phoenix 以 OTel 與 OpenInference 慣例為基礎；Logfire 支援以 SQL 查詢 trace；Datadog、Honeycomb、Grafana 等通用觀測平台也提供 LLM 相關功能；雲端託管 agent 服務（如 Amazon Bedrock AgentCore、Google 的 agent 平台）提供各自的原生觀測整合。MCP 社群則定義了在 `_meta` 中傳遞 `traceparent`、`tracestate` 與 `baggage` 的慣例，讓 trace 能跨過 MCP server。

## 29.11 設計檢查清單

設計或審查一個 agent 的 observability 時，逐項回答下面的問題。

1. 每一次 agent 執行是否都有一條 trace，root span 帶著 conversation id、租戶、agent 名稱與版本？背景任務是否能對上 durable run id？
2. 模型呼叫、tool 執行、子 agent、檢索、核准等待是否各有自己的 span，並且 parent-child 關係正確？code-as-action 內部的 tool 呼叫是否也有 span？
3. span 名稱與屬性是否依 OpenTelemetry GenAI semantic conventions 命名？自訂屬性是否放在自家命名空間，而不是 `gen_ai.*`？
4. span 名稱是否只含低基數的值？訂單編號、使用者 id 等高基數資料是否只放在屬性？
5. 跨 MCP、A2A、HTTP 的呼叫是否傳遞 `traceparent`？接收外部請求時，是否決定了要接成 parent 還是只記成 link？
6. 內容擷取（prompt、回應、tool 參數與結果）在 production 是否預設關閉？開啟的條件、範圍與期限是否明確，開啟時是否留稽核？
7. 遮蔽是否在資料離開 process 之前完成？是否採用屬性 allowlist、處理巢狀結構與 events、並以 keyed hash 做假名化？
8. 是否在寫入時萃取衍生訊號（例如「宣稱已退款」「PII 數量」「guardrail 判定」），讓常見的語意失敗不讀原文也能查到？
9. 每次模型呼叫是否分開記錄一般輸入、cache 讀取、cache 寫入、輸出與 reasoning tokens？成本是否在寫入時依版本化的價目表算好？
10. tool 的外部成本（搜尋 API、sandbox 秒數）是否記在對應的 span 上？
11. 儀表板是否有「每次成功任務成本」，且成功的定義寫清楚？
12. 取樣策略是 head 還是 tail？是否保證所有錯誤、非正常結束與高成本的 trace 都被保留？成本與錯誤率的聚合指標是否在取樣之前計算？
13. 「說成功、其實失敗」「繞圈」「cache 失效」等失敗是否有固定查詢或告警，並且找到的案例會進入 eval set？
14. trace 匯出是否非同步、有界限的佇列，觀測後端故障時 agent 仍能正常服務？
15. debug trace 與稽核日誌的保存期限、存取權限是否分開設定？刪除權請求時，能否找到並刪除某位使用者的內容？

## 29.12 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 一次對話的 span 散成好幾條 trace | 跨執行緒或 asyncio task 時 context 沒有傳遞；跨服務沒有帶 `traceparent` | 比對同一 conversation id 下的 trace 數與 root 數 | 在 thread pool 提交時複製 context；所有外呼帶 `traceparent` |
| 儀表板的成本和供應商帳單對不上 | cache token 重複計算；reasoning tokens 漏算或重複計算；用新價格回推舊用量；從取樣後的 trace 加總 | 抽一天的 span 用帳單價格重算，逐項比較 | 依各家 usage 語意計算；寫入時存成本與價目表版本；成本由全量 metrics 計算 |
| trace 平台出現顧客的手機、email | `print(messages)` 或內容擷取未遮蔽；遮蔽只處理頂層字串 | 對匯出資料跑 PII 掃描，找出來源 span 與屬性 | 來源端 allowlist＋遮蔽；遮蔽遞迴處理巢狀結構與 events；清除已外洩資料 |
| 觀測後端的費用暴增、查詢變慢 | span 名稱含訂單編號等高基數值；大 tool 結果整包寫進屬性 | 依 span 名稱計數，看不同名稱的數量 | 名稱只放操作與 tool 名稱；屬性值截斷；內容改存外部並放引用 |
| 客訴的那次對話找不到 trace | head sampling 把它丟了；trace id 沒有和 conversation id 關聯 | 查取樣設定；確認 root span 上有 conversation id | 改用 tail sampling 並保留異常；root 一律記 conversation id |
| 錯誤率很低，但客訴不斷 | 只看 span status，語意失敗不會產生 ERROR | 抽樣低分或負評的 trace，看 status 分布 | 加衍生訊號與線上 eval；把業務結果記在獨立屬性 |
| 觀測後端故障時 agent 變慢或失敗 | 同步匯出；佇列無界限 | 壓測時關掉後端，觀察 agent 延遲 | 背景批次匯出、有界佇列、滿了就丟棄並計數 |
| 部署後指標變了卻找不到原因 | span 上沒有 prompt、模型、tool 版本 | 查 span 屬性是否有版本欄位 | root 與 chat span 帶完整版本；儀表板標出部署時間點 |

## 本章重點整理

- agent 的失敗多半是語意上的：每個呼叫都回 200，回覆卻是錯的，所以只看錯誤率與延遲的監控對它沉默。
- trace 是一次工作的完整紀錄，span 是其中一段有起訖時間的工作，parent-child 關係把它們連成一棵樹；session（conversation）把多條 trace 串成一段對話。
- span status 描述技術上的成敗，任務是否完成是業務結果，要記在獨立的屬性，不能混為一談。
- W3C `traceparent` 讓 trace 跨過 HTTP、MCP 與 A2A 的邊界；它是可被偽造的資料，不能當作安全邊界。
- OpenTelemetry GenAI semantic conventions 以 `gen_ai.operation.name` 區分 `invoke_agent`、`chat`、`execute_tool` 等操作；規格仍多為 Development，名稱以官方最新版本為準，自訂屬性放在自家命名空間。
- span 名稱只放低基數的值，訂單編號與使用者 id 放在屬性，否則觀測後端的索引與費用會失控。
- 資料依風險分層：結構、用量、版本、衍生訊號一律記錄；prompt 與 tool 內容在 production 預設關閉，開啟時先遮蔽。
- 遮蔽必須在資料離開 process 之前完成，用屬性 allowlist、遞迴處理巢狀結構，並用 keyed hash 做可 join 的假名化。
- 在寫入時萃取衍生訊號（例如「宣稱已退款」），讓最傷信任的語意失敗不讀原文也能查到。
- 成本要分開記錄各類 token 與 tool 外部成本，在寫入時依版本化的價目表算好；「每次成功任務成本」比單次成本更能支撐決策。
- 除錯時沿著 span 樹找第一個偏離預期的 span，把 trace 轉成 ScriptedModel 劇本重現，修正後加入 eval set，再把失敗寫成查詢估計影響範圍。
- tail sampling 能保留所有異常 trace，但成本與錯誤率等聚合指標必須在取樣之前由全量資料計算。
- 線上監控分品質、可靠性、成本、安全四組，品質靠代理指標與抽樣的線上 eval，告警設在比率與趨勢上。
- tracing 本身不能成為可用性的單點故障：匯出要非同步、佇列有界，觀測資料壞掉時業務照常服務。

## 延伸問答

> [!question]- Q1. log、metric、trace 三者在 agent 系統中各自負責什麼？只留一種行不行？
> metric 是可加總的數字，負責回答「整體健不健康」：今天的成功率、每任務成本、tool 錯誤率、p95 延遲，它便宜、可長期保存、適合告警，但看不到個案。trace 負責回答「這一次發生了什麼」：一次對話走了哪幾步、哪一步錯、每一步花多少，它是除錯與 error analysis 的單位。log 則是不屬於任何特定請求的事件，例如服務啟動、設定載入、背景任務的狀態，或者 span 裡放不下的細節。
>
> 只留一種會出問題。只有 metric，你知道成本漲了卻找不到是哪些對話；只有 trace，你必須掃描大量 span 才能畫出趨勢，而且取樣之後的加總會失真；只有 log，就是 Iris 在故事中的處境。實務上三者用同一組識別碼關聯：metric 的異常點連到該時段的範例 trace，trace 中的 span 連到同一 trace id 的 log。對 agent 來說，trace 的地位比傳統服務更核心，因為路徑是動態的，只有 trace 能重建它。

> [!question]- Q2. 為什麼 B-2077 那次對話的 root span status 是 OK？如果把它改成 ERROR，會有什麼後果？
> 因為 span status 的語意是「這段程式在技術上有沒有失敗」。那次執行沒有任何未處理的例外，模型 API 正常回應，loop 也正常結束；`refund` 失敗被當成觀察回填給模型，這是第 4 章設計好的正常路徑。真正的問題是業務結果：模型在 tool 失敗後錯誤地宣稱成功。這要由 `bluebird.run.status`、`bluebird.claims` 這類業務屬性記錄。
>
> 如果規則是「任何子 span 失敗就把 root 標成 ERROR」，那麼所有「tool 失敗後模型正確地改走退貨流程」的健康對話也會變成 ERROR，錯誤率會被這些正常的恢復行為灌水，失去告警價值；反過來，真正的語意失敗（tool 根本沒被呼叫，模型就說已退款）仍然不會被標成 ERROR。把技術狀態與業務結果分開記錄，兩種查詢才都準確：技術錯誤率用 status，任務成功率用業務屬性。

> [!question]- Q3. 設計取捨：production 要不要開啟 prompt 與回應的內容擷取？
> 先列出兩邊的成本。開啟的好處是除錯與 replay 最完整，error analysis 可以直接讀模型看到的內容；壞處是 trace 變成大量個資的集中地，帶來外洩風險、法規上的保存與刪除義務、更高的儲存成本，以及「誰能讀」的權限管理負擔。關閉的好處是風險最小，壞處是遇到語意失敗時只能看到骨架，無法確認模型為什麼這樣回答。
>
> 多數團隊的答案是「預設關閉，用三種手段補回價值」。第一，衍生訊號：在寫入時萃取最常用的語意判斷，讓多數查詢不需要原文。第二，分級開啟：依租戶同意、特定 agent 或事件調查期間短期開啟，而且一律先遮蔽、短期保存、讀取留稽核。第三，結構化的最小內容：例如只存模型回應中的 tool calls 與 stop reason（不含自由文字），它們足以 replay harness，個資風險也低得多。開發與測試環境則全開，因為那裡用的是合成資料。

> [!question]- Q4. 你在 production 看到每任務成本在週三之後上升了 40%，但任務數沒變。你會怎麼排查？
> 第一步是看成本結構：把成本拆成一般輸入、cache 讀取、cache 寫入、輸出、reasoning 與 tool 外部成本，看是哪一項在漲。如果 cache 讀取比例在週三驟降、一般輸入上升，幾乎可以確定是前綴被打斷，例如有人在 system prompt 加了時間戳或改了 tool 順序（第 9 章），對照 chat span 上的 prompt 版本與部署時間就能找到。如果輸出或 reasoning tokens 上升，可能是模型版本變了或 effort 設定被調高。
>
> 第二步是看分布：是所有任務都貴了，還是長尾變長了？若 p95 步數或單次 input 的 p99 上升，去看成本最高的 20 條 trace，常見的是繞圈或某個 tool 開始回傳超大結果。第三步是依維度切：是不是集中在某個租戶或功能，例如某個大租戶匯入了新的商品目錄。最後確認不是計量本身的問題：價目表版本是否換了、usage 語意是否因 adapter 改版而重複計算 cache token。修完後把「cache 命中率」與「每任務成本」設成部署後的自動比較，下次在 canary 階段就攔下來。

> [!question]- Q5. 程式找錯：下面這個 instrumentation 有三個會在 production 出事的問題，請指出來。
> ```python
> with tracer.span(f"execute_tool {tc.name} {tc.args['order_id']}") as sp:
>     sp.set("bluebird.user.email", user.email)
>     sp.set("gen_ai.tool.call.result", json.dumps(result))
> ```
> 第一，span 名稱放了訂單編號，這是高基數的值。觀測後端通常依名稱分組與建索引，每張訂單都變成一個「不同的操作」，查詢與費用都會失控；訂單編號應該放在屬性，名稱只留 `execute_tool {tool 名稱}`。另外 `tc.args['order_id']` 在參數缺失時會丟 KeyError，讓 tracing 本身弄壞了 tool 呼叫。
>
> 第二，直接把 email 寫進屬性，等於把 PII 送進 trace；如果需要識別使用者，應該用 keyed hash 的假名。第三，tool 結果無條件寫進內容屬性：它沒有經過 opt-in 開關、沒有遮蔽，也沒有長度上限，一個大的查詢結果就可能塞進數十 KB。修法是：名稱只用低基數的值，使用者以假名記錄，內容欄位受 `capture_content` 控制並經過 allowlist、遮蔽與截斷的 processor。

> [!question]- Q6. head sampling 和 tail sampling 怎麼選？各自的代價是什麼？
> head sampling 在 trace 開始時就決定留不留，通常依 trace id 的雜湊取固定比例。它的優點是簡單、便宜：不被留下的 trace 在 agent 端就不必產生與傳送，collector 不需要暫存。缺點是它在不知道結果的情況下做決定，所以失敗的 trace 和正常的 trace 被丟掉的比例相同；在失敗率只有幾個百分點的系統裡，你會丟掉大部分最想看的案例。
>
> tail sampling 等整條 trace 結束後才決定，能依結果保留所有錯誤、異常結束、高成本與被負評的 trace，再加一小部分正常 trace 當基準。代價是 collector 要在記憶體中暫存每條 trace 直到結束，並且同一條 trace 的所有 span 要送到同一個 collector，架構更複雜；長時間的 agent 任務還要設定暫存的等待上限。agent 系統通常值得付這個代價，因為失敗的語意多樣、案例珍貴。不論選哪種，成本與錯誤率的聚合指標都要在取樣之前從全量資料計算。

> [!question]- Q7. 估算題：青鳥每天 5 萬次客服對話，平均每次 12 個 span，每個 span 平均 1.5 KB（不含內容）；若對 5% 的對話開啟內容擷取，內容平均每次對話 40 KB。全量保存 30 天需要多少儲存？用 tail sampling 保留 12% 的骨架又是多少？
> 骨架的每日資料量是 50,000 × 12 × 1.5 KB ＝ 900,000 KB，約 900 MB；內容是 50,000 × 5% × 40 KB ＝ 100,000 KB，約 100 MB。每天約 1 GB，30 天約 30 GB（未計壓縮、索引與副本，實際儲存通常是原始量的數倍）。用 tail sampling 保留 12% 的骨架，骨架降到每天約 108 MB，30 天約 3.2 GB；內容擷取通常只對被保留的 trace 有意義，若內容也只保留在這 12% 中，就再降一個量級。
>
> 這個數字本身不大，所以對中型系統而言，取樣的主要理由往往不是儲存，而是觀測平台按 span 數或資料量計價的費用，以及查詢效能。估算的價值在於看出比例：內容只佔 5% 的對話，卻佔了一成的資料量與絕大部分的隱私風險；把內容擷取比例從 5% 降到 1%，風險下降的幅度遠大於儲存的節省。實際規劃時要換成你的平台計價方式與保存政策。

> [!question]- Q8. 面試追問：如果要你為一個多租戶 agent 平台設計 tracing 架構，你會怎麼畫？
> 從資料流講起。agent runtime 內建 instrumentation，依 GenAI 慣例產生 span，在 process 內依序經過屬性 allowlist、PII 遮蔽與假名化、截斷，再由背景批次匯出器以 OTLP 送到 collector 叢集。所有外呼帶 `traceparent`，MCP 與 A2A 走同樣的傳遞慣例；接收外部 agent 的請求時只記 link，不直接接成 parent。collector 負責第二道遮蔽、tail sampling（同一 trace 依 trace id 路由到同一台）、依租戶路由，並在取樣之前輸出成本、token 與錯誤率的 metrics。
>
> 儲存分三類：骨架 trace（依租戶分區、保存數十天）、內容保管庫（加密、短期、讀取需審批並留稽核）、稽核日誌（append-only、長期，第 33 章）。存取控制依租戶與角色：商家只能看自己租戶的遮蔽版本，平台工程師看骨架，內容需要額外授權。接著談取捨：自架 collector 與儲存讓資料留在自己的帳號、成本可控，但營運負擔重；用託管平台上手快，要確認資料駐留與租戶隔離能力。最後補上營運面：觀測管線本身要有 SLO 與背壓策略，滿載時丟棄並計數而不是拖慢 agent；價目表與語意慣例的版本變更要有遷移計畫。

## 延伸閱讀

- OpenTelemetry〈Semantic Conventions for Generative AI Systems〉（semantic-conventions-genai repo，含 agent spans 與 MCP conventions）
- W3C〈Trace Context〉Recommendation
- Sigelman et al.〈Dapper, a Large-Scale Distributed Systems Tracing Infrastructure〉（Google Technical Report，2010）
- Charity Majors、Liz Fong-Jones、George Miranda《Observability Engineering》（O'Reilly，2022）
- Anthropic Engineering Blog〈How we built our multi-agent research system〉（2025）
- Hamel Husain〈Your AI Product Needs Evals〉（2024，個人部落格）
- Google《Site Reliability Engineering》〈Monitoring Distributed Systems〉（O'Reilly，2016）
