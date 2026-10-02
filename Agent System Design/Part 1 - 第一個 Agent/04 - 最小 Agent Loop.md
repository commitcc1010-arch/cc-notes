---
chapter: 4
title: 100 行的最小 Agent Loop
part: 1
---

# 第 4 章　100 行的最小 Agent Loop

> [!abstract] 本章地圖
> **核心問題**：一個「模型在迴圈中自己決定下一步」的程式，最少需要哪些零件，才不會在第一次 demo 就崩潰、失控或燒錢？
>
> **你會學到**：
> - 畫出 agent loop 的完整流程，說清楚哪些決定交給模型、哪些一定要留在程式裡
> - 設計 message 格式與 tool schema，讓每一次 tool 呼叫都能用 id 對回結果
> - 把 tool 的例外、參數錯誤、不存在的 tool 轉成模型讀得懂的觀察，而不是讓 loop 崩潰
> - 為 loop 設計多重停止條件：end_turn、步數上限、token 預算、重複呼叫偵測、輸出截斷
> - 理解 streaming 對 loop 的影響：文字可以邊收邊顯示，tool 參數要等完整才執行
> - 從 30 行的裸 loop 一路寫到約 100 行、可離線測試的 `loom` v0.1
>
> **前置知識**：第 1 章（agent 的定義：模型在 loop 中決定下一步與何時停止）、第 2 章（Model／Harness／Environment 三層）、第 3 章（token、context window、function calling 的基本形態）

## 4.1 故事：一個 while True 搞垮的 demo

週一早上，阿哲把一張需求卡片貼到 Iris 的螢幕旁邊：「讓客服機器人自己查訂單、查物流，能退款的就直接退。週五給業務看 demo。」青鳥科技的客服每天要處理上萬則「我的貨到哪了」「我要退款」的訊息，八成都只需要查兩三個系統就能回答。Iris 有後端背景，第 3 章講過的 function calling 也試過，心想這應該是一個下午的事。

Iris 的第一版只有十幾行：把使用者的問題和 tool 定義送給模型，模型回傳「我要呼叫 `get_order`」，程式就呼叫，結果塞回去，再問一次模型，外面包一個 `while True`。在自己的筆電上，「B-1042 到哪了？」跑得漂漂亮亮。週五的 demo 卻接連出了三次狀況，而且每一次都和模型聰不聰明無關。

第一次，業務問「B-1042 幫我退款」。退款 API 因為訂單已出貨而丟出 `ValueError`，例外一路往外炸，整個 process 結束，畫面只剩 stack trace。第二次，物流商的查詢回「查詢中」，模型覺得再查一次也許就有了，於是用一模一樣的參數連查了四十幾次，直到 Iris 手動按下 Ctrl+C；事後看帳單，這一題花掉的 token 比整週的測試加起來還多。第三次最隱晦：Iris 修掉第一個問題時，在例外處理裡直接 `continue`，結果對話紀錄裡留下一個「有呼叫、沒結果」的 tool call，下一輪送給 API 時直接被拒絕。

demo 結束後，staff engineer 老陳把 Iris 的程式印出來，在 `while True` 那一行畫了個圈。「agent 的核心真的就只是一個 loop，」老陳說，「但這個 loop 的每一條邊都要想清楚：訊息怎麼記、tool 怎麼派、錯誤怎麼回、什麼時候停。你今天的三個事故，剛好是三條沒想清楚的邊。」老陳建議 Iris 把 loop 抽成獨立的小模組，取名 `loom`（織布機）：梭子一來一回織出布，agent 也是模型與工具一來一回完成任務。

這一章就是 Iris 重寫的過程。我們會先把 loop 的骨架講清楚，再逐一處理 message、tool dispatch、錯誤回填、停止條件與 streaming，最後在「動手做」把 30 行的裸 loop 長成約 100 行的 `loom` v0.1，並用 ScriptedModel 把週五的三個事故全部重現、全部修好。後面的章節會不斷回到這 100 行：第 5 章重構 tools，第 9 章與第 10 章處理 context，第 24 章把它改成支援串流、並行與取消的 runtime，第 45 章則把它組成完整的 framework。

## 4.2 Agent loop 的骨架：模型提議，程式執行

先建立最重要的一個心智模型：**模型從來不執行任何東西**。模型只會輸出文字，其中一種特別格式的文字叫 **tool call**（工具呼叫請求），意思是「我想用這些參數呼叫這個工具」。例如模型輸出 `get_order(order_id="B-1042")`，它並沒有查到任何訂單，只是提出一個請求。真正去查資料庫的，是包在模型外面的那段程式，業界叫它 **harness**（駕馭程式、外殼）：負責呼叫模型、執行 tool、把結果送回、決定何時停止。第 2 章的 Model／Harness／Environment 三層，在這一章就落實成一個具體的 Python 類別。

```text
 使用者問題「B-1042 到哪了？」
     │
     ▼
 messages = [user]
     │
     ▼
 (1) 呼叫模型 complete(messages, tools) ──────────────────► Model
     │                                                        │
     │◄───────────────── 回應：text、tool_calls、stop_reason ─┘
     ▼
 (2) 停止條件成立？ ── 是 ──► 回傳 RunResult（status、output）給使用者
     │ 否：有 tool_calls 要執行
     ▼
 (3) dispatch：逐一執行 tool ─────────────────────────────► Environment
     │                                                        │（訂單 DB、物流 API）
     │◄──────────────────────────────────────── 結果，或例外 ─┘
     ▼
 (4) 每個 tool 結果包成一則 tool 訊息，用 tool_call_id 對回
     │
     └──► 回到 (1)：模型帶著新的觀察，決定下一步
```

這張圖是全書最常出現的一張圖，值得一步一步看。第 (1) 步，harness 把目前累積的所有 messages 和可用的 tool 定義一起送給模型；模型是**無狀態**的，它不記得上一輪說過什麼，所以每一輪都要把完整歷史重送一次。第 (2) 步，harness 根據回應判斷要不要停：模型沒有要求任何 tool（代表它認為可以回答了），或者撞到步數、預算等上限，就把結果整理成 `RunResult` 回傳。第 (3) 步，如果模型要求呼叫 tool，harness 才真的去碰外部世界：查資料庫、打物流 API、建立退貨單。第 (4) 步，把每個 tool 的結果包成一則訊息附加到 messages 尾端，然後回到第 (1) 步，讓模型看到新的資訊再決定下一步。

這個「想一步、做一步、看結果、再想一步」的節奏，由 ReAct（Reasoning + Acting，Yao 等人在 2022 年發表的論文）系統化地提出：模型交錯產生推理與動作，並根據動作的觀察結果修正推理。今天的主流 API 已經把「動作」做成結構化的 tool call，不必再從自由文字裡解析，但節奏是同一個。第 8 章會比較 ReAct、plan-and-execute 等推理 pattern；本章只需要記住：**loop 每轉一圈，模型就多看到一個 observation**（觀察，也就是 tool 執行後回填的結果），它的下一個決定就建立在這些觀察之上。

為什麼不乾脆讓程式寫死流程：先查訂單、再查物流、再回答？因為使用者的問題是開放的。「B-1042 到哪了」需要兩步；「我上個月買的藍色外套能退嗎」要先用 email 找訂單、再查退貨政策、再判斷是否出貨；「幫我把兩張訂單合併出貨」可能根本不在能力範圍，應該轉真人。步驟數量與順序事先無法列舉，才是讓模型決定下一步的理由。反過來說，如果你的任務每次都是固定三步，第 18 章的 workflow 會比 agent 更便宜、更可預測。

| 決定 | 交給模型 | 留在 harness（程式） | 為什麼這樣分 |
|---|---|---|---|
| 下一步呼叫哪個 tool、帶什麼參數 | 是 | 驗證參數是否符合 schema | 模型擅長理解意圖，但會猜錯參數名稱 |
| tool 實際怎麼執行 | 否 | 是 | 執行涉及權限、交易與副作用，必須是確定性程式 |
| tool 失敗後怎麼辦 | 是（讀錯誤訊息後改做法） | 把例外轉成可讀的錯誤訊息 | 模型能從「已出貨，請改用退貨單」學到改法 |
| 什麼時候算完成 | 提議（不再呼叫 tool） | 最終裁決（上限、預算、迴圈偵測） | 模型可能過早宣告完成，也可能永遠不宣告 |
| 花多少錢、跑多久 | 否 | 是 | 成本與延遲是營運責任，不能交給被計費的那一方決定 |

這張表是本章所有設計決定的根據。左欄的事情需要「理解」，交給模型；右欄的事情需要「保證」，留在程式。常見的誤解是把 harness 想成可有可無的膠水，只要模型夠強就不需要；事實正好相反，模型越強、能做的事越多，harness 負責的保證就越重要。另一個誤解是「框架會幫我處理這些」：主流框架確實內建了 loop，但它們的預設上限、錯誤處理方式各不相同，你仍然需要知道每一條邊在做什麼，才能判斷預設值適不適合自己的產品。

## 4.3 Message：agent 唯一的記憶

既然模型是無狀態的，agent 在一次任務中「記得」的一切，就是那串 messages。**message** 是一則有角色的訊息；把它們依序排成清單，就是送給模型的對話歷史。本書統一使用四種角色：`user`（使用者說的話）、`assistant`（模型的回應，可能帶著 tool_calls）、`tool`（某個 tool 的執行結果），以及放在 messages 之外、每次呼叫都會帶上的 `system`（系統指令，第 6 章詳談）。

```text
 每次呼叫模型時實際送出的內容（context 版面）

 ┌─ system ───────────────────────────────────────────────┐ 穩定前綴：每一輪都相同
 │ 你是青鳥科技的客服助理，只處理訂單、物流與退款。       │
 ├─ tools ────────────────────────────────────────────────┤
 │ get_order(order_id)  get_shipment(tracking)            │ （prompt caching 的重點）
 │ refund(order_id)    create_return(order_id)            │
 ├─ messages ─────────────────────────────────────────────┤ 只會在尾端追加
 │ [0] user       「我的訂單 B-1042 到哪了？」            │
 │ [1] assistant  tool_calls=[{id: c1, name: get_order,   │
 │                             args: {order_id: B-1042}}] │
 │ [2] tool       tool_call_id=c1   ◄── 用 id 對回 c1     │
 │                content={status: shipped,               │
 │                         tracking: TC-88301}            │
 │ [3] assistant  tool_calls=[{id: c2, get_shipment}]     │
 │ [4] tool       tool_call_id=c2   content={eta: 明天}   │
 │ [5] assistant  text=「已出貨，預計明天送達」           │
 │                tool_calls=[]     ◄── 沒有呼叫：end_turn│
 └────────────────────────────────────────────────────────┘
```

這張圖有三個重點。第一，system 與 tools 放在最前面，每一輪都一樣；messages 則只在尾端追加。這個「穩定前綴、尾端追加」的版面不只是整齊，它直接決定成本：主流模型供應商都提供 **prompt caching**（提示快取），當請求的開頭和前一次完全相同時，那一段可以用便宜很多的價格重用。如果你在 loop 中途改寫歷史或調換 tool 順序，快取就失效。第 9 章會把這件事當成一級架構約束來談。

第二，每個 tool call 都有一個 **id**，對應的 tool 結果必須帶著同一個 id（`tool_call_id`）。這不是形式主義。模型一次可以要求好幾個 tool（**parallel tool calls**，平行工具呼叫），例如同時查兩張訂單；harness 可能平行執行、結果回來的順序也不一定，只有靠 id 才能對回。主流 API 對這個配對規則很嚴格：assistant 提出的每個 tool call，都必須在下一則非 tool 訊息之前收到結果，否則整個請求會被拒絕。Iris 週五的第三個事故，就是違反了這條規則。

第三，最後一則 assistant 訊息沒有 tool_calls，代表模型認為任務完成，API 會用 **stop_reason**（停止原因）標示出來；本書的統一格式沿用 Anthropic 的命名，稱為 `end_turn`。如果模型要求呼叫 tool，stop_reason 是 `tool_use`；如果輸出長度撞到上限被截斷，則是 `max_tokens`。stop_reason 是 harness 判斷下一步的第一個訊號，4.7 節會看到它不是唯一的訊號。

因為配對規則這麼重要，值得寫一個小檢查器。下面的程式重現 Iris 的事故：tool 丟例外後，程式跳過了回填，使用者又追問一句，歷史就壞了。

```python
from __future__ import annotations


def check_history(messages: list[dict]) -> list[str]:
    """檢查 messages 是否符合 tool use 的配對規則；回傳問題清單，空清單代表合法。"""
    problems: list[str] = []
    pending: list[str] = []                       # 還沒收到結果的 tool_call id
    for i, m in enumerate(messages):
        role = m["role"]
        if role == "tool":
            if m["tool_call_id"] in pending:
                pending.remove(m["tool_call_id"])   # 平行呼叫的結果靠 id 對回，順序可以不同
            else:
                problems.append(f"#{i} tool 結果 {m['tool_call_id']} 找不到對應的 tool_call")
            continue
        if pending:                               # 下一則非 tool 訊息出現前，所有 call 都要有結果
            problems.append(f"#{i} 之前有 tool_call 沒有結果：{pending}")
            pending = []
        if role == "assistant":
            pending = [tc["id"] for tc in m.get("tool_calls", [])]
    if pending:
        problems.append(f"結尾有 tool_call 沒有結果：{pending}")
    return problems


ok = [
    {"role": "user", "content": "B-1042 到哪了？"},
    {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "name": "get_order", "args": {"order_id": "B-1042"}}]},
    {"role": "tool", "tool_call_id": "c1", "name": "get_order", "content": '{"status": "shipped"}'},
    {"role": "assistant", "content": "已出貨。", "tool_calls": []},
]
# Iris 的裸 loop 在 tool 丟例外後，把半截歷史存進資料庫；使用者再問一句時就變成這樣
broken = ok[:2] + [{"role": "user", "content": "所以呢？"}]
orphan = ok[:1] + [{"role": "tool", "tool_call_id": "c9", "name": "refund", "content": "已退款"}]

print("ok     →", check_history(ok) or "合法")
print("broken →", check_history(broken))
print("orphan →", check_history(orphan))
assert check_history(ok) == []
assert check_history(broken) == ["#2 之前有 tool_call 沒有結果：['c1']"]
assert len(check_history(orphan)) == 1
```

```text
ok     → 合法
broken → ["#2 之前有 tool_call 沒有結果：['c1']"]
orphan → ['#1 tool 結果 c9 找不到對應的 tool_call']
```

`ok` 是一段合法的歷史：c1 被呼叫、c1 有結果、最後一則 assistant 沒有 tool_calls。`broken` 是 Iris 的事故現場：第 1 則訊息提出了 c1，但第 2 則直接是使用者的追問，c1 的結果永遠不會來了。`orphan` 則是反方向的錯誤：一個不知道從哪來的 tool 結果，常見於有人「手動修補」歷史時刪掉了 assistant 訊息。實務上，這個檢查應該放在兩個地方：每次把 messages 寫進資料庫之前，以及每次從資料庫讀出來要續跑之前。檢查不到成本，卻能把「API 回 400」這種在凌晨才會出現的錯誤，提前變成單元測試裡的一行 assert。

> [!warning] 常見誤解
> 「messages 只是 log，壞了頂多少一點上下文。」不對。messages 是 agent 唯一的工作記憶，也是下一次呼叫模型的輸入。少一則 tool 結果，API 會拒絕；多塞一則不相干的內容，模型會被干擾；在中間改一個字，prompt cache 就失效。把 messages 當成有 schema、有不變式（invariant）的資料結構來對待，而不是隨手 append 的字串清單。

### 2026 現況：三家 API 的 tool use 欄位對照

截至 2026 年 10 月，三家主要模型 API 的 tool use 形態如下（依各家公開文件整理，欄位名稱以官方文件為準）。本書的統一格式刻意取三家的最大公約數，第 25 章會為每一家寫 adapter。

| 概念 | 本書統一格式 | Anthropic Messages API | OpenAI Responses API | Gemini Interactions API |
|---|---|---|---|---|
| tool 定義 | `name`、`description`、`parameters` | `name`、`description`、`input_schema` | `type: "function"`、`name`、`description`、`parameters` | `type: "function"`、`name`、`description`、`parameters` |
| 模型要求呼叫 | assistant 的 `tool_calls`（`id`、`name`、`args`） | assistant 內容中的 `tool_use` block（`id`、`name`、`input`） | `function_call` item（`call_id`，`arguments` 為 JSON 字串） | `function_call` step |
| 回填結果 | `role: "tool"`、`tool_call_id`、`content` | user 訊息中的 `tool_result` block（`tool_use_id`，可帶 `is_error`） | `function_call_output` item（`call_id`） | `function_result` step |
| 要求呼叫時的停止訊號 | `stop_reason: "tool_use"` | `stop_reason: "tool_use"` | 輸出中出現 `function_call` item | 輸出中出現 `function_call` step |

表中最值得注意的是兩個差異。一是 OpenAI 的 `arguments` 是 JSON 字串而不是物件，adapter 必須自己解析，也必須處理解析失敗。二是三家都在往「有狀態、item／step 化」的介面走（server 端保存歷史，用 id 串接），但底層概念仍然是同一串配對好的 messages。另外，部分推理模型會在回應中附上不透明的推理欄位（例如加密的 reasoning 內容或 thought signature），多輪 tool use 時必須原樣送回，adapter 不能把它們丟掉。

## 4.4 Tool schema 與 dispatch：把函式變成模型看得懂的能力

模型要能提出 tool call，前提是它知道有哪些 tool、每個 tool 吃什麼參數。**tool schema** 就是寫給模型看的函式說明書：名稱、一句話描述，以及用 **JSON Schema**（描述 JSON 資料長相的標準格式）寫成的參數規格。例如 `get_order` 的 schema 會說：「查詢訂單狀態與物流單號；參數 `order_id` 是字串、必填，例如 B-1042」。模型看不到你的 Python 程式碼，它對 tool 的全部理解都來自這份說明書，所以描述寫得含糊，模型就會用錯。

手寫 JSON Schema 很囉嗦，也容易和函式本體不同步。常見的做法是從函式簽名自動產生：型別提示決定參數型別，沒有預設值的參數就是必填，docstring 當描述。主流框架大多提供這種裝飾器。下面用標準函式庫的 `inspect` 寫一個最小版本，讓你看清楚它沒有魔法。

```python
from __future__ import annotations

import inspect
from typing import Any, Callable, get_type_hints

JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean"}


def tool_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    """從函式簽名與 docstring 產生 tool schema。第一行 docstring 當描述，`名稱: 說明` 當參數說明。"""
    hints = get_type_hints(fn)
    doc = inspect.getdoc(fn) or ""
    lines = doc.splitlines()
    arg_docs = dict(l.strip().split(": ", 1) for l in lines[1:] if ": " in l)
    props, required = {}, []
    for name, p in inspect.signature(fn).parameters.items():
        props[name] = {"type": JSON_TYPES[hints[name]], "description": arg_docs.get(name, "")}
        if p.default is inspect.Parameter.empty:
            required.append(name)            # 沒有預設值的參數才是必填
    return {"name": fn.__name__, "description": lines[0] if lines else "",
            "parameters": {"type": "object", "properties": props, "required": required}}


def search_orders(customer_email: str, status: str = "any", limit: int = 5) -> list[dict]:
    """依顧客 email 搜尋最近的訂單，回傳訂單編號、狀態與金額。
    customer_email: 顧客的 email，例如 amy@example.com
    status: 只看某個狀態：any、pending、shipped、delivered
    limit: 最多回傳幾筆，預設 5
    """
    return []


schema = tool_schema(search_orders)
print(schema["description"])
for name, spec in schema["parameters"]["properties"].items():
    flag = "必填" if name in schema["parameters"]["required"] else "選填"
    print(f"  {name:<15} {spec['type']:<8} {flag}  {spec['description']}")
assert schema["parameters"]["required"] == ["customer_email"]
assert schema["parameters"]["properties"]["limit"]["type"] == "integer"
```

```text
依顧客 email 搜尋最近的訂單，回傳訂單編號、狀態與金額。
  customer_email  string   必填  顧客的 email，例如 amy@example.com
  status          string   選填  只看某個狀態：any、pending、shipped、delivered
  limit           integer  選填  最多回傳幾筆，預設 5
```

輸出的第一行是 tool 的描述，下面三行是參數。`customer_email` 沒有預設值，所以是必填；`status` 與 `limit` 有預設值，是選填；`limit: int` 被翻成 JSON Schema 的 `integer`。注意描述裡的例子（`amy@example.com`、狀態的四個合法值），這些對模型的幫助往往比型別本身更大，因為模型會照著例子的格式填參數。第 5 章會專門談怎麼寫好 tool 的名稱、描述、粒度與回傳格式；`loom` v0.1 為了讓每個欄位都看得見，選擇讓使用者直接傳入 schema。

有了 schema，**dispatch**（派送）就是把模型提出的 tool call 對應到真正的函式並執行。它看起來只是一行 `TOOLS[name](**args)`，實際上要依序處理四種情況：名稱不存在（模型幻想出一個 tool，例如 `cancel_order`）、參數不合 schema（模型把 `order_id` 寫成 `id`）、函式執行時丟例外（業務規則拒絕、下游逾時）、執行成功但結果太長（一次回傳五百筆訂單）。前三種是錯誤，第四種是成功但需要處理。每一種都不應該讓 loop 崩潰，這是下一節的主題。

dispatch 還有一個常被忽略的責任：**把結果轉成文字**。模型只讀得懂文字，所以 dict 要序列化成 JSON，而且最好用 `ensure_ascii=False` 保留中文，否則「台中轉運中心」會變成一串 `台` 編碼，既浪費 token 又讓模型難以閱讀。過長的結果要截斷並明確標示「已截斷，原長 N 字元」，讓模型知道自己沒看到全部，必要時改用更精確的查詢。主流 coding agent 也都對單次 tool 回傳設有上限，超過就截斷或改存到檔案；`loom` v0.1 用字元數做簡化版的上限。

## 4.5 逐步追蹤一次完整的 trajectory

**trajectory**（軌跡）是一次任務從使用者輸入到最終結果之間，所有模型回應與 tool 結果的完整序列。它是除錯、評估（第 27 章）與觀測（第 29 章）的基本單位：當使用者說「機器人亂回答」，你要看的不是最後那句話，而是整條 trajectory，找出它在哪一步走錯。下面用時序圖追蹤「B-1042 到哪了？」這一題。

```text
 使用者                 loom（harness）                   Model               訂單／物流系統
    │── B-1042 到哪了？ ───►│                               │                       │
    │                       │ messages=[user]               │                       │
    │                       │── step 1：送出 1 則 ─────────►│                       │
    │                       │◄───────── tool_use get_order ─│                       │
    │                       │ append assistant（c1）        │                       │
    │                       │── get_order(B-1042) ─────────────────────────────────►│
    │                       │◄────────────────────────────────── shipped, TC-88301 ─│
    │                       │ append tool（c1）             │                       │
    │                       │── step 2：送出 3 則 ─────────►│                       │
    │                       │◄────── tool_use get_shipment ─│                       │
    │                       │ append assistant（c2）        │                       │
    │                       │── get_shipment(TC-88301) ────────────────────────────►│
    │                       │◄───────────────────────────────── 台中轉運中心、明天 ─│
    │                       │ append tool（c2）             │                       │
    │                       │── step 3：送出 5 則 ─────────►│                       │
    │                       │◄─────────── end_turn：已出貨 ─│                       │
    │                       │ status=done                   │                       │
    │◄─────── 預計明天送達 ─│                               │                       │
```

逐步看這條 trajectory。step 1，模型只看到一則使用者訊息，它判斷要先查訂單，於是提出 `get_order`；注意模型不知道物流單號，它必須先拿到訂單資料。harness 執行後把結果回填，messages 變成 3 則。step 2，模型看到 `tracking: TC-88301`，這是它從觀察中得到的新資訊，於是提出 `get_shipment`；這一步的參數完全來自上一步的結果，如果模型在 step 1 就「猜」一個物流單號，那就是 hallucinated tool call（幻覺工具呼叫），第 34 章會談怎麼防範。step 3，模型看到貨態，不再需要任何 tool，回傳 end_turn，harness 結束 loop。

這條 trajectory 也揭露了 agent 的成本結構。每一步都要重送完整歷史，所以第 N 步的 input tokens 大約是「固定前綴＋前面所有步驟累積的內容」。下表是 4.9 節程式實際量到的數字（用字元數粗估 token，數值本身不重要，趨勢才重要）：

| 步驟 | 送給模型的 messages 數 | 這一步的 input tokens | 累計 input tokens | 這一步新增的內容 |
|---|---|---|---|---|
| 1 | 1 | 405 | 405 | 使用者問題 |
| 2 | 3 | 563 | 968 | get_order 的呼叫與結果 |
| 3 | 5 | 710 | 1,678 | get_shipment 的呼叫與結果 |

每一步的 input 是線性成長，累計值則接近平方成長：一個 30 步的任務，最後幾步每一次呼叫都要重讀前面二十幾步的內容。這就是為什麼長任務一定要談 compaction（第 10 章）、為什麼 prompt caching 的命中率直接決定帳單（第 9 章），也是為什麼 `loom` 需要 token 預算，而不只是步數上限。步數上限限制的是「轉幾圈」，預算限制的是「花多少錢」，兩者在 tool 回傳很大的任務上會差很多。

## 4.6 錯誤處理：把例外變成觀察

回到 Iris 的第一個事故：退款 API 丟出 `ValueError("訂單已出貨，不能直接退款")`，例外炸穿 loop，整個任務失敗。但仔細想，這個錯誤訊息本身是很有用的資訊。如果把它交給模型，模型很可能會說：「那我改建立退貨單。」這就是本節的核心原則：**tool 層的失敗是一種觀察，應該回填給模型，而不是往外丟**。12-Factor Agents 把這條原則稱為「Compact Errors into Context Window」：把錯誤整理成精簡的文字放進 context，讓模型自我修正。

但不是所有錯誤都該交給模型。判斷標準是：**模型能不能靠改變行為來修正它**。參數寫錯、tool 不存在、業務規則拒絕，模型都能修；模型 API 本身回 429（請求太多）或 503（服務過載），模型根本看不到這個錯誤（因為呼叫它的就是這次失敗的請求），只能由 harness 退避重試；資料庫連線字串錯誤這種設定問題，模型再怎麼重試都沒用，應該立刻中止並告警。

```text
 tool call 進入 dispatch
   │
   ├─ (a) tool 名稱不存在 ───────────────────► 回填「沒有這個 tool，可用的有 ...」
   │
   ├─ (b) 參數不合 schema ───────────────────► 回填「缺少 X、不認得 Y，正確參數是 ...」
   │
   └─ (c) 執行 tool
          │
          ├─ 成功 ─┬─ 結果不長 ──────────────► 回填結果（序列化成 JSON 文字）
          │        │
          │        └─ 結果過長 ──────────────► 截斷並標示原長後回填
          │
          └─ 例外 ─┬─ 模型能修 ──────────────► 回填 is_error＋可行動的訊息
                   │   （參數、業務規則、查無資料）
                   └─ 模型修不好 ────────────► 往外丟：中止 run 並告警
                       （設定錯誤、權限被撤銷）

 不變式：只要 loop 繼續，每個 tool call 都產生一則 tool 訊息（tool_call_id 對回）
 不在這裡：模型 API 本身的 429／5xx，由呼叫模型的那一層退避重試（第 24 章）
```

這張決策圖由上到下對應 dispatch 的關卡。(a) 與 (b) 是「事前驗證」：在碰外部世界之前，先確認名稱存在、參數合法，失敗就回填一則說明「正確的長相」的錯誤，例如列出可用的 tool 或正確的參數名稱。(c) 是「執行」：成功就序列化並視需要截斷；失敗時再問一次「模型能不能修」，能修就回填，不能修的少數類別（設定錯誤、權限被撤銷、資料損毀）才往外丟。圖底下的「不變式」是整張圖最重要的一行：只要決定繼續 loop，每個 tool call 都一定產生一則帶著對應 id 的 tool 訊息，這正是 4.3 節的配對規則。

| 錯誤類型 | 例子 | 誰處理 | 回填給模型的內容 | 是否重試 |
|---|---|---|---|---|
| tool 不存在 | 模型呼叫 `cancel_order` | harness 回填 | 「沒有這個工具，可用的有 get_order、refund…」 | 模型自行改用正確 tool |
| 參數不合 schema | `refund(id=...)` | harness 回填 | 「缺少 order_id，不認得 id」 | 模型自行修正參數 |
| 業務規則拒絕 | 已出貨不能退款 | tool 丟例外，harness 回填 | 「已出貨，請改用 create_return」 | 模型改走另一條路 |
| 下游暫時失敗 | 物流 API 逾時 | tool 內部先重試，仍失敗再回填 | 「物流系統逾時，已重試 2 次，可稍後再查或告知使用者」 | tool 內有限次數重試 |
| 模型 API 失敗 | 429、503、連線中斷 | 呼叫模型的那一層 | 不回填（模型看不到） | 指數退避＋jitter，設上限 |
| 設定或權限錯誤 | API key 失效 | harness 中止 | 不回填，回傳失敗狀態並告警 | 不重試 |

這張表有兩個容易混淆的地方。第一是「下游暫時失敗」該不該交給模型重試：讓模型重試，每次重試都要多付一輪 LLM 呼叫，還可能觸發下一節的重複呼叫偵測；所以短暫的網路錯誤應該在 tool 內部用確定性程式重試，只有重試用盡才把狀況告訴模型。第二是有副作用的 tool：如果 `refund` 在扣款成功、回傳結果之前逾時，盲目重試可能重複退款。這類 tool 需要 **idempotency key**（冪等鍵，同一個 key 重複送出只會生效一次），第 5 章與第 22 章會詳談；`loom` v0.1 先把原則記下來：有副作用的 tool 不在 harness 層自動重試。

錯誤訊息怎麼寫，決定了模型能不能修正。使用者把 B-1042 的 0 打成英文字母 O，tool 丟出 `KeyError: 'B-1O42'`，這對模型幾乎沒有幫助；「找不到訂單 B-1O42，請向使用者確認訂單編號（格式為 B-加四位數字）」則直接告訴它下一步該做什麼。這叫**可行動的錯誤訊息**：說清楚發生什麼事、為什麼、可以怎麼做。另外，主流 API 允許在 tool 結果上標記 `is_error`，讓模型明確知道這是失敗而不是一般資料；`loom` 的 tool 訊息也帶著這個欄位，之後轉換成各家格式時才不會遺失。

> [!warning] 常見誤解
> 「把所有例外都 catch 起來回填，agent 就很穩健了。」只對一半。一律回填會讓設定錯誤、權限被撤銷這類「模型永遠修不好」的問題，變成模型反覆嘗試、直到步數用完的慢性失敗，帳單和延遲都更難看。回填的前提是模型有機會修正；沒有機會的，就讓它快速、明確地失敗。

## 4.7 停止條件：什麼時候停、誰說了算

Iris 的第二個事故，模型用相同參數查了四十幾次物流，暴露了裸 loop 唯一的停止條件有多脆弱：「模型不再呼叫 tool」。這個條件把「何時停止」完全交給模型，但模型可能永遠覺得「再查一次也許就有了」，也可能在任務其實沒完成時就宣告完成。第 1 章說 agent 是「模型自己決定何時停止」的系統，這句話的完整版是：**模型提議何時停止，harness 保證一定會停止**。

```text
 每一輪的檢查順序
 ┌────────────────────────────────────────────────────┐
 │ (1) 呼叫模型之前：累計 tokens >= 預算？            │ ── 是 ──► status=budget
 └───────────┬────────────────────────────────────────┘
             │ 否：呼叫模型
 ┌───────────▼────────────────────────────────────────┐
 │ (2) stop_reason == max_tokens？                    │ ── 是 ──► status=max_tokens
 │     輸出被截斷，tool 參數可能是半截 JSON，不執行   │
 └───────────┬────────────────────────────────────────┘
             │ 否
 ┌───────────▼────────────────────────────────────────┐
 │ (3) 回應中沒有 tool_calls？                        │ ── 是 ──► status=done（模型的提議）
 └───────────┬────────────────────────────────────────┘
             │ 否：逐一處理 tool call
 ┌───────────▼────────────────────────────────────────┐
 │ (4) 相同 (name, args) 出現次數 > max_repeats？     │ ── 仍重複 ──► status=loop
 │     第一次超過：不執行，回填「請換做法」           │
 │     提醒後仍重複：回填「已停止」                   │
 └───────────┬────────────────────────────────────────┘
             │ 都沒觸發：執行 tool、回填結果
 ┌───────────▼────────────────────────────────────────┐
 │ (5) 已經轉了 max_steps 圈？                        │ ── 是 ──► status=max_steps
 └───────────┬────────────────────────────────────────┘
             └──► 否：回到 (1)
```

這張圖的順序是刻意安排的。預算檢查放在呼叫模型**之前**，因為呼叫模型就是花錢的動作；放在之後，你永遠會多付一輪。max_tokens 檢查放在處理 tool call 之前，因為被截斷的回應裡，tool 參數可能是 `{"order_id": "B-10` 這樣的半截 JSON，絕對不能執行，尤其是退款這類有副作用的 tool。「沒有 tool_calls」才輪到模型的提議。重複偵測在 tool 層，採取兩段式：先提醒、再硬停。步數上限是最後的保險，保證不管其他條件有沒有寫對，loop 都會在有限步內結束。

每一個停止條件都在回答不同的問題，所以不能互相取代：

| 停止條件 | 回答的問題 | 典型觸發情境 | 回傳給使用者的內容 | 建議的初始值 |
|---|---|---|---|---|
| end_turn（無 tool_calls） | 模型認為完成了嗎？ | 正常回答 | 模型的回答 | 不需設定 |
| max_steps | 轉了太多圈嗎？ | 模型反覆嘗試不同做法 | 目前進度＋轉真人 | 依任務：客服 8–15，coding 數十到數百 |
| token 預算 | 花太多錢了嗎？ | tool 回傳很大、歷史很長 | 目前進度＋轉真人 | 依單題可接受成本反推 |
| 重複呼叫 | 在原地打轉嗎？ | 相同參數查同一個狀態 | 提醒後仍重複才停 | 相同呼叫 2–3 次 |
| max_tokens（輸出截斷） | 回應完整嗎？ | 回答太長、上限設太小 | 截斷的文字，或重試 | 視輸出長度調整 |
| 時間上限（wall clock） | 跑太久了嗎？ | 下游很慢、同步互動等不了 | 稍後通知 | 同步客服數十秒 |

表格最後一欄的數字只是起點，不是標準答案；真正的值要從自己的 trajectory 分布來定，例如先觀察 99% 的正常任務在幾步內完成，再把上限設在略高於那裡。時間上限在本章的同步 loop 裡沒有實作，因為它需要能取消進行中的模型呼叫與 tool，第 24 章會用 asyncio 處理。另外要注意 **status 的設計**：`loom` 的 `RunResult` 不只回傳文字，還回傳 `status`（done、max_steps、budget、loop、max_tokens）。上層程式要靠 status 決定怎麼做：done 直接顯示，budget 與 loop 轉給真人並記錄，max_tokens 可能要提高上限重試。只回傳一段文字的 agent，上層永遠分不清「答完了」和「放棄了」。

重複偵測值得多談一點。`loom` 用 `(tool 名稱, 參數排序後的 JSON)` 當 key 計數，參數要排序，否則 `{"a":1,"b":2}` 和 `{"b":2,"a":1}` 會被當成不同的呼叫。為什麼第一次超過時不直接停？因為重複有時是合理的：使用者說「等一下再幫我查一次」，模型重查是對的。先回填一則提醒，模型多半會改變做法（例如回覆使用者「目前貨態未更新，建議明天再查」）；提醒後仍然重複，才代表真的卡住了。v0.1 在整個 run 內計數，比較進階的做法是只看最近幾步的滑動視窗，或偵測「沒有進展」（連續幾步都沒有新資訊），第 24 章與第 34 章會再深入。

預算檢查有一個取捨要知道：因為檢查在呼叫之前、而 token 數在呼叫之後才知道，最後一次呼叫可能讓總量略超過預算，超出的幅度最多是一輪的用量。這是**軟上限**。若需要硬上限，可以在呼叫前先估算這次的 input tokens（部分 API 提供 token 計數功能），並把這次的輸出上限設為「剩餘預算」。另外也要決定預算算什麼：只算 input＋output tokens，還是換算成金額（cache 命中的 tokens 比較便宜、推理模型的 thinking tokens 要另外計），第 29 章會談成本計量。

> [!warning] 常見誤解
> 「只要 max_steps 設好就夠了。」步數上限限制的是圈數，不是成本也不是正確性。一個 tool 一次回傳兩萬字，五步就可能比別人五十步還貴；模型在第三步就錯誤地宣告完成，步數上限也幫不上忙。後者要靠第 27 章的 outcome 評估，以及在 harness 裡加入驗證（例如退款前確認訂單狀態），不能只相信 end_turn。

## 4.8 Streaming：同一個 loop，換一種收訊方式

到目前為止，`complete()` 都是等模型整段回應產生完才回傳。使用者因此要盯著空白畫面等好幾秒。**streaming**（串流）是讓模型邊產生、邊把片段送回來：文字一個片段一個片段到達，畫面可以立刻顯示「好的，我幫您查一下……」。它改善的是 **TTFT**（time to first token，第一個 token 出現的時間），也就是使用者的體感延遲；總時間並沒有變短。

streaming 對 loop 的結構影響比想像中小，但有一個關鍵限制：**文字可以邊收邊顯示，tool call 的參數必須等完整才能執行**。tool 參數是 JSON，串流時會被切成好幾段送來，例如 `{"order_` 和 `id": "B-10` 和 `42"}`；在最後一段到達之前，它不是合法的 JSON，更不能拿去呼叫退款 API。

```text
 時間 ──────────────────────────────────────────────────────────────►

 模型串流   text_delta     text_delta     tool_start     args_delta x3    stop
            好的，我幫您   查一下 B-1042  get_order      JSON 片段        tool_use
              │              │              │              │                │
 harness    顯示到 UI      顯示到 UI      開參數緩衝區   累積到緩衝區     組裝完整的
                                                         尚非合法 JSON    ModelResponse
              │              │                                              │
              ▼              ▼                                              ▼
 使用者     立刻看到字     字繼續出現                               進入停止檢查與 dispatch
```

圖中前兩個事件是文字片段，harness 直接轉給 UI，使用者在模型還在「想」下一步時就看到回應。第三個事件宣告一個 tool call 開始，harness 為它開一個參數緩衝區；接下來的參數片段只能累積、不能解析。直到 stop 事件到達，harness 才把文字與所有 tool call 組裝成一個完整的 `ModelResponse`，從這裡開始，後面的流程和非串流版本完全一樣。換句話說，streaming 只改變了 loop 的第 (1) 步「怎麼收回應」，沒有改變第 (2) 到 (4) 步。

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


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


# 一次模型回應被拆成一連串事件；真實 API 的事件名稱各家不同，但都是這幾類
EVENTS = [
    ("text_delta", "好的，我幫您"),
    ("text_delta", "查一下 B-1042。"),
    ("tool_start", {"id": "c1", "name": "get_order"}),
    ("args_delta", '{"order_'),
    ("args_delta", 'id": "B-10'),
    ("args_delta", '42"}'),
    ("stop", "tool_use"),
]


def assemble(events, on_text) -> ModelResponse:
    """邊收事件邊組裝：文字立刻交給 UI，tool 參數要等 JSON 完整才能解析與執行。"""
    text, calls, buffers = "", [], {}
    for kind, data in events:
        if kind == "text_delta":
            text += data
            on_text(data)                                # 使用者馬上看到字
        elif kind == "tool_start":
            calls.append(data)
            buffers[data["id"]] = ""
        elif kind == "args_delta":
            buffers[calls[-1]["id"]] += data
            try:
                json.loads(buffers[calls[-1]["id"]])
                state = "完整"
            except json.JSONDecodeError:
                state = "不完整，還不能執行"
            print(f"  args 緩衝區 {buffers[calls[-1]['id']]!r:<28} {state}")
        elif kind == "stop":
            tool_calls = [ToolCall(c["id"], c["name"], json.loads(buffers[c["id"]])) for c in calls]
            return ModelResponse(text=text, tool_calls=tool_calls, stop_reason=data)
    raise ConnectionError("串流在 stop 事件前中斷：這次回應必須整個作廢重來")


shown: list[str] = []
resp = assemble(EVENTS, on_text=lambda d: shown.append(d) or print(f"  UI 顯示 +{d!r}"))
print("組裝結果：", resp.stop_reason, resp.tool_calls)
assert resp.tool_calls[0].args == {"order_id": "B-1042"} and "".join(shown) == resp.text

try:
    assemble(EVENTS[:4], on_text=lambda d: None)         # 模擬網路在參數傳到一半時斷線
except ConnectionError as exc:
    print("斷線：", exc)
```

```text
  UI 顯示 +'好的，我幫您'
  UI 顯示 +'查一下 B-1042。'
  args 緩衝區 '{"order_'                   不完整，還不能執行
  args 緩衝區 '{"order_id": "B-10'         不完整，還不能執行
  args 緩衝區 '{"order_id": "B-1042"}'     完整
組裝結果： tool_use [ToolCall(id='c1', name='get_order', args={'order_id': 'B-1042'})]
  args 緩衝區 '{"order_'                   不完整，還不能執行
斷線： 串流在 stop 事件前中斷：這次回應必須整個作廢重來
```

前兩行是 UI 收到的文字片段，在 tool 參數還沒到之前就已經顯示。接著三行是參數緩衝區的狀態：前兩段都「不完整，還不能執行」，第三段到達後才成為合法 JSON。`組裝結果` 那一行顯示最終的 `ModelResponse` 和非串流版本完全相同，所以後面的 dispatch 可以共用。最後兩行是斷線模擬：只送出前四個事件，倒數第二行是斷線前收到的半段參數，接著拋出 `ConnectionError`。這很重要：串流在 stop 之前中斷時，這次回應必須整個作廢重來，因為你無法知道模型原本還要說什麼、還要呼叫什麼。已經顯示在畫面上的文字也要處理，例如標示「重新產生中」，否則使用者會看到兩段重複的開頭。

> [!note] 2026 現況
> 截至 2026 年 10 月，主流 API 的串流都採用 server-sent events，但事件名稱不同。依公開文件，Anthropic Messages API 以 `content_block_start`、`content_block_delta`（文字為 text delta，tool 參數為 input JSON delta）與 `message_delta`（帶 stop_reason）等事件組成；OpenAI Responses API 則有輸出文字的 delta 事件與 function call 參數的 delta 事件，最後以完成事件結束。部分框架與平台會在單一 tool 的參數完整時就立刻開始執行（各框架的支援情況本書未逐一查證），不等整則回應結束，以進一步降低延遲；這需要確定該 tool 沒有副作用或可以安全取消。確切事件名稱與行為請以各家官方文件為準。

streaming 帶來的進階問題，例如把「模型正在呼叫 get_order」這類進度事件推給前端、在串流中途取消、平行執行多個 tool，都放在第 24 章的 runtime；前端事件協定則在第 15 章談 AG-UI。`loom` v0.1 維持非串流的 `complete()`，因為本章的重點是 loop 的正確性，而 streaming 只是在 loop 的入口加一個組裝器。

## 4.9 動手做：從 30 行長到 100 行的 loom v0.1

這一節把前面所有概念寫成程式，分三個版本逐步長大。每一段程式都可以單獨執行，開頭複製了全書統一的 ScriptedModel：它不連網、不需要 API key，依照我們寫好的「劇本」逐步回應。用劇本模型測試 harness 的好處是**可重現**：週五 demo 的三個事故，我們可以一字不差地重演，修好之後用 assert 鎖住，以後任何人改壞都會立刻知道。真實模型的行為是機率性的，同樣的事故可能一百次才出現一次，用它來測試 harness 的錯誤處理既慢又不可靠。

### 第一版：30 行的裸 loop（重現週五的事故）

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


# ───────── 第一版：約 30 行的裸 loop，能跑，但沒有任何防護 ─────────
ORDERS = {"B-1042": {"status": "shipped", "tracking": "TC-88301"}}

def get_order(order_id: str) -> dict:
    return {"order_id": order_id, **ORDERS[order_id]}          # 找不到就丟 KeyError

def refund(order_id: str) -> str:
    if ORDERS[order_id]["status"] == "shipped":
        raise ValueError("訂單已出貨，不能直接退款")
    return "已退款"

TOOLS = {"get_order": get_order, "refund": refund}
SCHEMAS = [{"name": n, "description": f.__name__, "parameters": {}} for n, f in TOOLS.items()]

def run(model, user_input: str) -> tuple[str, list[dict]]:
    messages: list[dict] = [{"role": "user", "content": user_input}]
    while True:                                               # 沒有步數上限
        resp = model.complete(messages, tools=SCHEMAS)
        messages.append({"role": "assistant", "content": resp.text,
                         "tool_calls": [vars(tc) for tc in resp.tool_calls]})
        if not resp.tool_calls:                               # 唯一的停止條件：模型不再呼叫 tool
            return resp.text, messages
        for tc in resp.tool_calls:
            result = TOOLS[tc.name](**tc.args)                # 例外會直接炸穿整個 loop
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name,
                             "content": json.dumps(result, ensure_ascii=False)})


# 1) 正常路徑：兩步完成
model = ScriptedModel([call("get_order", order_id="B-1042"), say("B-1042 已出貨，物流單號 TC-88301。")])
answer, history = run(model, "B-1042 到哪了？")
print("正常：", answer, f"（呼叫模型 {len(model.calls)} 次，messages {len(history)} 則）")
assert len(history) == 4 and history[2]["tool_call_id"] == "c1"

# 2) tool 丟例外：整個 run 崩潰，前面累積的 messages 也一起消失
try:
    run(ScriptedModel([call("refund", order_id="B-1042"), say("（不會走到這裡）")]), "幫我退款")
except ValueError as exc:
    print("崩潰：", type(exc).__name__, exc)

# 3) 模型一直呼叫 tool：while True 不會自己停，這裡只是因為劇本用完才被打斷
runaway = ScriptedModel([call("get_order", f"c{i}", order_id="B-1042") for i in range(50)])
try:
    run(runaway, "B-1042？")
except RuntimeError as exc:
    print("失控：", exc, f"（已呼叫模型 {len(runaway.calls)} 次）")
assert len(runaway.calls) == 51
```

```text
正常： B-1042 已出貨，物流單號 TC-88301。 （呼叫模型 2 次，messages 4 則）
崩潰： ValueError 訂單已出貨，不能直接退款
失控： 劇本已用完：agent 呼叫模型的次數比預期多 （已呼叫模型 51 次）
```

這一版的 schema 只是空殼（`parameters` 是空的），目的是讓程式最短。輸出的第一行證明這個 loop 在正常路徑上是對的：模型被呼叫 2 次，messages 有 4 則（user、assistant 呼叫、tool 結果、assistant 回答），而且 tool 結果的 `tool_call_id` 正確對回 c1。第二行重現事故一：`refund` 丟出的 `ValueError` 直接穿出 `run()`，呼叫端拿到的是例外而不是回答，前面累積的 messages 也隨著函式結束而消失，連事後除錯都沒有材料。第三行重現事故二：劇本準備了 50 次 tool 呼叫，loop 就乖乖呼叫了 51 次模型，最後是因為劇本用完才停；換成真實模型，它不會用完，只會一直燒錢。

### 第二版：加上步數上限與錯誤回填

第二版只改兩件事：`while True` 換成 `for _ in range(max_steps)`，以及把 tool 的執行包進 `dispatch()`，任何失敗都轉成 `(is_error, content)` 回填。回傳值也多了 status，讓呼叫端知道是怎麼結束的。

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


# ───────── 第二版：加上步數上限與錯誤回填（約 50 行）─────────
ORDERS = {"B-1042": {"status": "shipped", "tracking": "TC-88301"}}

def get_order(order_id: str) -> dict:
    return {"order_id": order_id, **ORDERS[order_id]}

def refund(order_id: str) -> str:
    if ORDERS[order_id]["status"] == "shipped":
        raise ValueError("訂單已出貨，不能直接退款；請改用 create_return 建立退貨單")
    return "已退款"

def create_return(order_id: str) -> dict:
    return {"return_id": "R-7781", "order_id": order_id}

TOOLS = {"get_order": get_order, "refund": refund, "create_return": create_return}
SCHEMAS = [{"name": n, "description": f.__name__, "parameters": {}} for n, f in TOOLS.items()]

def dispatch(tc: ToolCall) -> tuple[bool, str]:
    """回傳 (is_error, content)。任何失敗都變成模型讀得懂的文字，而不是往外丟。"""
    if tc.name not in TOOLS:
        return True, f"沒有名為 {tc.name} 的工具。可用的工具：{', '.join(TOOLS)}。"
    try:
        result = TOOLS[tc.name](**tc.args)
    except Exception as exc:
        return True, f"{type(exc).__name__}: {exc}"
    return False, json.dumps(result, ensure_ascii=False)

def run(model, user_input: str, max_steps: int = 6) -> tuple[str, str, list[dict]]:
    messages: list[dict] = [{"role": "user", "content": user_input}]
    for _ in range(max_steps):
        resp = model.complete(messages, tools=SCHEMAS)
        messages.append({"role": "assistant", "content": resp.text,
                         "tool_calls": [vars(tc) for tc in resp.tool_calls]})
        if not resp.tool_calls:
            return "done", resp.text, messages
        for tc in resp.tool_calls:
            is_error, content = dispatch(tc)
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name,
                             "content": content, "is_error": is_error})
    return "max_steps", "步驟用完了，先轉給真人同事。", messages


# 1) 模型先猜錯 tool 名稱，再撞上業務規則，最後讀錯誤訊息自行修正
model = ScriptedModel([
    call("cancel_order", "c1", order_id="B-1042"),
    call("refund", "c2", order_id="B-1042"),
    call("create_return", "c3", order_id="B-1042"),
    say("B-1042 已出貨，已幫您建立退貨單 R-7781。"),
])
status, answer, history = run(model, "B-1042 幫我退款")
for m in history:
    if m["role"] == "tool":
        print(f"{m['tool_call_id']} {m['name']:<14} is_error={m['is_error']!s:<5} {m['content'][:34]}")
print(status, "：", answer)
assert status == "done" and [m["is_error"] for m in history if m["role"] == "tool"] == [True, True, False]

# 2) 同一個失控劇本，現在會在第 6 步停下，而且 messages 還在
runaway = ScriptedModel([call("get_order", f"c{i}", order_id="B-1042") for i in range(50)])
status, answer, history = run(runaway, "B-1042？")
print(status, "：", answer, f"（呼叫模型 {len(runaway.calls)} 次，messages {len(history)} 則）")
assert status == "max_steps" and len(runaway.calls) == 6 and len(history) == 13
```

```text
c1 cancel_order   is_error=True  沒有名為 cancel_order 的工具。可用的工具：get_or
c2 refund         is_error=True  ValueError: 訂單已出貨，不能直接退款；請改用 creat
c3 create_return  is_error=False {"return_id": "R-7781", "order_id"
done ： B-1042 已出貨，已幫您建立退貨單 R-7781。
max_steps ： 步驟用完了，先轉給真人同事。 （呼叫模型 6 次，messages 13 則）
```

前三行是三則 tool 訊息。c1：模型呼叫了不存在的 `cancel_order`，dispatch 回填「沒有這個工具」並列出可用的工具；c2：模型改呼叫 `refund`，業務規則拒絕，例外被轉成 `ValueError: 訂單已出貨……請改用 create_return` 回填；c3：模型照著錯誤訊息的指示呼叫 `create_return`，成功。第四行 status 是 done，代表 agent 從兩個錯誤中自行恢復，這正是 4.6 節「把例外變成觀察」的效果。最後一行是同一個失控劇本，現在在第 6 步就停下，status 是 max_steps，13 則 messages 都還在（1 則 user＋6 組呼叫與結果），可以交給真人接手或事後分析。

第二版還有三個洞：參數錯誤只能靠 Python 的 `TypeError` 間接發現，訊息對模型不友善；同樣參數重複呼叫要等到步數用完才停，中間白白多花好幾輪；完全不知道花了多少 token。第三版補上這些。

### 第三版：loom v0.1

`loom` v0.1 把 loop 包成 `Agent` 類別，tool 包成帶 schema 的 `Tool`，結果包成 `RunResult`。標記之間的框架本體連空行約 90 行，加上 tool 定義正好約 100 行；依序實作 4.7 節的五個檢查：預算、max_tokens、end_turn、重複呼叫、步數上限；`_dispatch` 則實作 4.6 節決策圖的 (a)、(b)、(c) 三道關卡與結果截斷。後半段是青鳥的假後端與五個情境的測試。`MeteredModel` 是 ScriptedModel 的子類別，用字元數粗估 token 填進 usage，讓預算機制有東西可量；真實 API 會在每次回應中直接回傳 usage。

```python
from __future__ import annotations

import json
from collections import Counter
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


# ───────────────────────── loom v0.1 ─────────────────────────
@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]              # JSON Schema：type=object、properties、required
    fn: Callable[..., Any]

    def schema(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


@dataclass
class RunResult:
    status: str                             # done｜max_steps｜budget｜loop｜max_tokens
    output: str
    steps: int
    usage: dict[str, int]
    messages: list[dict]
    trace: list[str]


class Agent:
    def __init__(self, model, tools: list[Tool], system: str = "", max_steps: int = 8,
                 token_budget: int = 50_000, max_repeats: int = 2, max_result_chars: int = 2_000):
        self.model, self.system = model, system
        self.tools = {t.name: t for t in tools}
        self.max_steps, self.token_budget = max_steps, token_budget
        self.max_repeats, self.max_result_chars = max_repeats, max_result_chars

    def run(self, user_input: str) -> RunResult:
        messages: list[dict] = [{"role": "user", "content": user_input}]
        usage = {"input_tokens": 0, "output_tokens": 0}
        seen: Counter[str] = Counter()
        trace: list[str] = []

        def finish(status: str, output: str, steps: int) -> RunResult:
            trace.append(f"stop  status={status}")
            return RunResult(status, output, steps, usage, messages, trace)

        for step in range(1, self.max_steps + 1):
            if usage["input_tokens"] + usage["output_tokens"] >= self.token_budget:
                return finish("budget", "這個問題處理得比預期久，我先轉給真人同事協助。", step - 1)
            resp = self.model.complete(messages, tools=[t.schema() for t in self.tools.values()],
                                       system=self.system)
            for k in usage:
                usage[k] += resp.usage.get(k, 0)
            if resp.stop_reason == "max_tokens":    # 被截斷的 tool call 參數可能不完整，不執行
                messages.append({"role": "assistant", "content": resp.text, "tool_calls": []})
                return finish("max_tokens", resp.text, step)
            messages.append({"role": "assistant", "content": resp.text,
                             "tool_calls": [vars(tc) for tc in resp.tool_calls]})
            if not resp.tool_calls:
                trace.append(f"step {step}  answer  {resp.text[:30]}")
                return finish("done", resp.text, step)
            looping = False
            for tc in resp.tool_calls:
                key = tc.name + json.dumps(tc.args, sort_keys=True, ensure_ascii=False)
                seen[key] += 1
                if seen[key] > self.max_repeats + 1:   # 提醒過還在重複：硬停
                    looping = True
                    is_error, content = True, "已停止：重複呼叫。"
                elif seen[key] > self.max_repeats:     # 第一次超過：不執行，提醒模型換做法
                    is_error, content = True, (f"你已經用相同參數呼叫 {tc.name} {seen[key] - 1} 次，"
                                               "結果不會改變。請改用其他做法，或直接回覆使用者目前的狀況。")
                else:
                    is_error, content = self._dispatch(tc)
                trace.append(f"step {step}  {tc.name}({json.dumps(tc.args, ensure_ascii=False)})"
                             f"  →  {'ERROR ' if is_error else ''}{content[:30]}")
                messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name,
                                 "content": content, "is_error": is_error})
            if looping:
                return finish("loop", "我卡在同一個步驟，已轉給真人同事。", step)
        return finish("max_steps", "步驟用完了，我先整理目前進度並轉給真人同事。", self.max_steps)

    def _dispatch(self, tc: ToolCall) -> tuple[bool, str]:
        tool = self.tools.get(tc.name)
        if tool is None:
            return True, f"沒有名為 {tc.name} 的工具。可用的工具：{', '.join(self.tools)}。"
        props = tool.parameters.get("properties", {})
        missing = [p for p in tool.parameters.get("required", []) if p not in tc.args]
        unknown = [a for a in tc.args if a not in props]
        if missing or unknown:
            return True, f"參數錯誤：缺少 {missing}，不認得 {unknown}。正確參數：{list(props)}。"
        try:
            result = tool.fn(**tc.args)
        except Exception as exc:                 # tool 的例外是「觀察」，回填給模型而不是讓 loop 崩潰
            return True, f"{type(exc).__name__}: {exc}"
        text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        if len(text) > self.max_result_chars:
            text = text[: self.max_result_chars] + f"…（已截斷，原長 {len(text)} 字元）"
        return False, text
# ─────────────────────── loom v0.1 結束 ───────────────────────


# 青鳥客服的假後端
ORDERS = {"B-1042": {"status": "shipped", "carrier": "黑貓", "tracking": "TC-88301"}}

def get_order(order_id: str) -> dict:
    if order_id not in ORDERS:
        raise KeyError(f"找不到訂單 {order_id}，請向使用者確認訂單編號")
    return {"order_id": order_id, **ORDERS[order_id]}

def get_shipment(tracking: str) -> dict:
    return {"tracking": tracking, "location": "台中轉運中心", "eta": "明天"}

def refund(order_id: str) -> str:
    if ORDERS[order_id]["status"] == "shipped":
        raise ValueError(f"訂單 {order_id} 已出貨，不能直接退款；請改用 create_return 建立退貨單")
    return "已退款"

def create_return(order_id: str) -> dict:
    return {"return_id": "R-7781", "order_id": order_id, "pickup": "後天"}

def obj(**props: str) -> dict:
    return {"type": "object", "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
            "required": list(props)}

TOOLS = [
    Tool("get_order", "查詢訂單狀態與物流單號", obj(order_id="訂單編號，例如 B-1042"), get_order),
    Tool("get_shipment", "用物流單號查詢貨態", obj(tracking="物流單號，例如 TC-88301"), get_shipment),
    Tool("refund", "未出貨訂單直接退款", obj(order_id="訂單編號"), refund),
    Tool("create_return", "已出貨訂單建立退貨單", obj(order_id="訂單編號"), create_return),
]


class MeteredModel(ScriptedModel):
    """真實 API 會回傳 usage；這裡用「字元數 ÷ 2」粗估，讓預算機制有東西可量。"""

    log: list[int]

    def __init__(self, script):
        super().__init__(script)
        self.log = []

    def complete(self, messages, tools=None, system=""):
        resp = super().complete(messages, tools, system)
        resp.usage = {"input_tokens": len(json.dumps([tools, messages], ensure_ascii=False)) // 2,
                      "output_tokens": 40}
        self.log.append(resp.usage["input_tokens"])
        return resp


def show(title: str, agent: Agent, r: RunResult) -> None:
    print(f"── {title}")
    print("\n".join(r.trace))
    print(f"   steps={r.steps} messages={len(r.messages)} 每次呼叫的 input tokens={agent.model.log}\n")


# 情境 A：正常路徑
agent = Agent(MeteredModel([
    call("get_order", order_id="B-1042"),
    call("get_shipment", tracking="TC-88301"),
    say("您的訂單 B-1042 已出貨，目前在台中轉運中心，預計明天送達。"),
]), TOOLS)
a = agent.run("我的訂單 B-1042 到哪了？")
show("A 正常查詢", agent, a)
assert a.status == "done" and a.steps == 3 and "明天" in a.output

# 情境 B：參數寫錯、業務規則拒絕，模型讀了錯誤訊息後自行修正
agent = Agent(MeteredModel([
    call("refund", id="B-1042"),
    call("refund", order_id="B-1042"),
    lambda msgs: call("create_return", order_id="B-1042") if "create_return" in msgs[-1]["content"] else say("?"),
    say("B-1042 已出貨，無法直接退款；已為您建立退貨單 R-7781，物流後天到府取件。"),
]), TOOLS)
b = agent.run("B-1042 我不要了，幫我退款")
show("B 錯誤回填與修正", agent, b)
assert b.status == "done" and [m["is_error"] for m in b.messages if m["role"] == "tool"] == [True, True, False]

# 情境 C：模型一直用相同參數查貨態
agent = Agent(MeteredModel([call("get_shipment", f"c{i}", tracking="TC-88301") for i in range(6)]),
              TOOLS, max_repeats=2)
c = agent.run("TC-88301 怎麼還沒到？")
show("C 重複呼叫偵測", agent, c)
assert c.status == "loop" and c.steps == 4

# 情境 D：每一步都合理，但累積的 token 超過預算
agent = Agent(MeteredModel([call("get_order", f"c{i}", order_id="B-1042") if i % 2 == 0
                            else call("get_shipment", f"c{i}", tracking="TC-88301") for i in range(8)]),
              TOOLS, token_budget=2_500, max_repeats=5)
d = agent.run("幫我一直追蹤 B-1042")
show("D 預算上限", agent, d)
assert d.status == "budget" and sum(d.usage.values()) >= 2_500

# 情境 E：輸出被截斷（max_tokens），半截的 tool call 不執行
e = Agent(ScriptedModel([ModelResponse(text="您的訂單", tool_calls=[ToolCall("c1", "refund", {})],
                                       stop_reason="max_tokens")]), TOOLS).run("退款")
assert e.status == "max_tokens" and not [m for m in e.messages if m["role"] == "tool"]

# 不論哪種停法，每個 tool_call 都有對應的 tool 結果：messages 可以安全地續跑或重放
for r in (a, b, c, d, e):
    ids = [tc["id"] for m in r.messages if m["role"] == "assistant" for tc in m["tool_calls"]]
    assert ids == [m["tool_call_id"] for m in r.messages if m["role"] == "tool"]
print("五個情境全部通過；messages 中的 tool_call 與 tool 結果一一配對")
```

```text
── A 正常查詢
step 1  get_order({"order_id": "B-1042"})  →  {"order_id": "B-1042", "status
step 2  get_shipment({"tracking": "TC-88301"})  →  {"tracking": "TC-88301", "loca
step 3  answer  您的訂單 B-1042 已出貨，目前在台中轉運中心，預計明天
stop  status=done
   steps=3 messages=6 每次呼叫的 input tokens=[405, 563, 710]

── B 錯誤回填與修正
step 1  refund({"id": "B-1042"})  →  ERROR 參數錯誤：缺少 ['order_id']，不認得 ['id'
step 2  refund({"order_id": "B-1042"})  →  ERROR ValueError: 訂單 B-1042 已出貨，不能直接
step 3  create_return({"order_id": "B-1042"})  →  {"return_id": "R-7781", "order
step 4  answer  B-1042 已出貨，無法直接退款；已為您建立退貨單 R-7
stop  status=done
   steps=4 messages=8 每次呼叫的 input tokens=[405, 531, 664, 812]

── C 重複呼叫偵測
step 1  get_shipment({"tracking": "TC-88301"})  →  {"tracking": "TC-88301", "loca
step 2  get_shipment({"tracking": "TC-88301"})  →  {"tracking": "TC-88301", "loca
step 3  get_shipment({"tracking": "TC-88301"})  →  ERROR 你已經用相同參數呼叫 get_shipment 2 次，結果
step 4  get_shipment({"tracking": "TC-88301"})  →  ERROR 已停止：重複呼叫。
stop  status=loop
   steps=4 messages=9 每次呼叫的 input tokens=[404, 552, 699, 839]

── D 預算上限
step 1  get_order({"order_id": "B-1042"})  →  {"order_id": "B-1042", "status
step 2  get_shipment({"tracking": "TC-88301"})  →  {"tracking": "TC-88301", "loca
step 3  get_order({"order_id": "B-1042"})  →  {"order_id": "B-1042", "status
step 4  get_shipment({"tracking": "TC-88301"})  →  {"tracking": "TC-88301", "loca
stop  status=budget
   steps=4 messages=9 每次呼叫的 input tokens=[403, 561, 709, 867]

五個情境全部通過；messages 中的 tool_call 與 tool 結果一一配對
```

逐段解說這份輸出。

**情境 A（正常查詢）**和 4.5 節的時序圖一模一樣：step 1 查訂單、step 2 用訂單裡的物流單號查貨態、step 3 回答，status 是 done。最後一行的 `每次呼叫的 input tokens=[405, 563, 710]` 就是 4.5 節表格的資料來源：每多一步，模型要重讀的內容就多一截。

**情境 B（錯誤回填與修正）**示範了兩種不同層級的錯誤。step 1 的 `參數錯誤：缺少 ['order_id']，不認得 ['id']` 是 dispatch 在執行前用 schema 抓到的，tool 本體根本沒被呼叫；這比第二版靠 `TypeError` 間接發現更安全，因為有副作用的 tool 不會在參數錯誤時執行一半。step 2 的 `ValueError` 是業務規則拒絕。step 3 的劇本是一個函式：它先檢查最後一則訊息裡有沒有 `create_return` 這個提示，有才走對的路，這模擬了「模型讀錯誤訊息後修正」的行為。assert 驗證三則 tool 訊息的 `is_error` 依序是 True、True、False。

**情境 C（重複呼叫偵測）**重現事故二。`max_repeats=2` 代表相同呼叫允許執行 2 次；step 3 第三次出現時，loom 不執行 tool，而是回填「你已經用相同參數呼叫 2 次，結果不會改變」；劇本裡的模型不聽勸，step 4 又呼叫一次，loom 回填「已停止」後以 status=loop 結束。共 9 則 messages：1 則 user 加 4 組呼叫與結果。和第二版相比，它在第 4 步就停了，而不是等到第 6 步或第 8 步。

**情境 D（預算上限）**是最容易被忽略的情境：每一步都是合理的不同呼叫，重複偵測不會觸發（`max_repeats=5`），步數也遠低於 8，但四步累積的 input tokens（403＋561＋709＋867）加上 output，已經超過 2,500 的預算，所以在第 5 次呼叫模型之前停下，status=budget。注意實際用量略超過預算，這就是 4.7 節說的軟上限。**情境 E** 沒有印出輸出，它用 assert 驗證 max_tokens 時半截的 `refund` 呼叫不會被執行。

最後一段 assert 是整個 v0.1 最重要的保證：不論五個情境以哪種方式停止，messages 中每個 tool_call 都有對應的 tool 結果。這代表任何一次 run 留下的歷史都可以安全地續跑（使用者追問）、重放（除錯）或交給真人接手，不會出現 Iris 的第三個事故。

| 版本 | 新增的行為 | 修掉的事故或風險 | 對應小節 |
|---|---|---|---|
| 第一版：裸 loop（約 30 行） | 基本 loop：呼叫、執行、回填 | 無（能跑正常路徑） | 4.2、4.3 |
| 第二版（約 50 行） | max_steps、dispatch 錯誤回填、status | 例外炸穿 loop、無限迴圈 | 4.6、4.7 |
| 第三版：`loom` v0.1（約 100 行） | schema 參數驗證、結果截斷、token 預算、兩段式重複偵測、max_tokens 處理、trace、RunResult | 參數錯誤時執行一半、原地打轉、成本失控、半截 tool call | 4.4、4.6、4.7 |

`loom` v0.1 刻意沒有做的事，也值得列出來，免得你以為它已經能上線：tool 是逐一序列執行的，沒有平行；沒有時間上限與取消；模型 API 失敗時沒有重試；messages 只在記憶體裡，process 一掛就沒了；沒有 system prompt 的版本管理，也沒有權限控制。這些分別在第 24 章（runtime）、第 22 章（durable execution）、第 6 章（system prompt）與第 32 章（防禦設計）補上。保持 v0.1 小，是為了讓你能把 loop 的每一行都讀懂；複雜度應該長在 tools 與 context，而不是 loop 本身。

## 4.10 實務應用

本章的 loop 看起來簡單，但幾乎所有成功的 agent 產品，核心都是同一個 while-loop；它們的差異在於每條邊的設定。以下四個情境說明同一份 100 行程式在不同產品中要怎麼調整。

**情境一：電商客服 agent（青鳥的主線）**。客服是同步互動，使用者在聊天視窗前等，所以最重要的停止條件是時間與步數：多數問題應該在 3 到 6 步內完成，上限設在 10 步左右，超過就轉真人，而且轉交時要附上 trajectory 摘要，讓真人不必從頭問起。tool 分成唯讀（查訂單、查物流）與有副作用（退款、建立退貨單）兩類；唯讀 tool 失敗可以在 tool 內部重試，有副作用的不行。錯誤訊息要同時對模型與使用者友善，例如「已出貨不能直接退款」既能引導模型改建退貨單，也能讓模型向使用者解釋原因。status=budget 或 loop 的案例要記錄下來，每週檢查，它們通常指向 tool 設計的問題（第 5 章）。

**情境二：在 CI 裡跑的 coding agent**。開發者在 pull request 上留言「幫我修這個測試」，agent 在隔離環境裡讀程式、改檔案、跑測試。和客服相反，這類任務常常需要數十到上百步，步數上限要放寬很多，主要靠 token 預算與 wall-clock 時間限制成本；公開文件中，GitHub 的 Copilot coding agent 在 GitHub Actions 的臨時環境裡執行，並有工作時間的硬上限。這裡的 tool 錯誤（編譯失敗、測試失敗）正是 agent 最重要的觀察，一定要完整回填，必要時截斷但保留錯誤所在的行。重複偵測要小心：反覆執行同一個測試指令是合理的（改完程式再測），所以 key 不能只看參數，要搭配「程式碼有沒有改變」來判斷。Claude Code 公開描述的 loop 是 gather context → take action → verify results 三段交織，並允許使用者在執行中排入訊息，這些都是在本章的基本 loop 上加的能力。

**情境三：企業內部 IT helpdesk 與營運 runbook agent**。員工問「我的 VPN 連不上」，agent 依照 runbook 查帳號狀態、查裝置憑證、必要時重設。這類 agent 的 tool 常常會碰到權限問題：查詢員工 A 的帳號，可能因為 agent 的服務帳號沒有權限而失敗。依 4.6 節的判斷，權限錯誤是「模型修不好」的錯誤，不應該讓模型反覆嘗試，而是立刻中止並開工單給 IT 人員；如果把它當成一般錯誤回填，模型可能會嘗試別的 tool 繞過權限，這在安全上是更糟的結果（第 31 章的 excessive agency）。高風險動作（重設 MFA、停用帳號）要在 dispatch 前插入人工核准，第 21 章會把它做成 loop 中的 interrupt。

**情境四：營運數據分析 agent**。營運人員問「上週退貨率為什麼上升」，agent 要查好幾張報表、比較不同維度。這類 tool 的結果往往很大（一次查詢回傳上千列），所以結果截斷與 token 預算是主要防線：截斷時要告訴模型「共 1,284 列，只顯示前 50 列，可以加上篩選條件」，讓它改用更精確的查詢，而不是在被截斷的資料上下結論。這也是第 13 章 code-as-action 的動機：與其把上千列塞進 context，不如讓 agent 寫一段程式在 sandbox 裡算完，只把結果帶回來。

| 產品類型 | 主要停止條件 | 錯誤回填重點 | 特別注意 |
|---|---|---|---|
| 電商客服 | 步數（約 10）、時間、轉真人 | 業務規則錯誤要可行動 | 有副作用的 tool 不自動重試 |
| CI coding agent | token 預算、wall clock | 編譯與測試輸出完整回填 | 重複偵測要考慮狀態是否改變 |
| IT helpdesk | 步數、權限錯誤即中止 | 權限錯誤不回填給模型繞過 | 高風險動作插入人工核准 |
| 數據分析 | token 預算、結果截斷 | 截斷要附總筆數與改查建議 | 大結果改用 code execution |

這張表的共同點是：loop 的程式碼幾乎不用改，改的是設定值與 dispatch 的政策。這也是為什麼 `loom` 把上限都做成建構子參數，而不是寫死在 loop 裡。

> [!note] 2026 現況
> 截至 2026 年 10 月，主流框架都內建了本章的 loop，並以不同名稱暴露停止條件（以下依各框架公開文件與 release 紀錄整理，預設值會隨版本調整，請以官方文件為準）：OpenAI Agents SDK 的 `Runner.run()` 有 `max_turns` 參數，超過時拋出專用例外；Claude Agent SDK 的選項中有 `max_turns`，其 loop 直接沿用 Claude Code 的 harness；LangGraph 以 `recursion_limit` 限制 graph 執行的步數；Vercel AI SDK 以 `stopWhen` 設定多步停止條件；Anthropic 的 client SDK 另有 beta 階段的 Tool Runner，可以自動跑完 tool loop。OpenAI 的〈A practical guide to building agents〉把 run 定義為「loop until exit condition」，列出的結束條件包括呼叫特定的 final-output tool、模型回應不含 tool call、發生錯誤，以及達到最大輪數。託管型服務（Claude Managed Agents、OpenAI Agents API、Amazon Bedrock AgentCore 等）則把 loop、session 與 sandbox 一起放到雲端，第 26 章會比較。

## 4.11 設計檢查清單

設計或審查一個 agent loop 時，逐項回答下面的問題。任何一題答不出來，就是上線前要補的洞。

1. 每個 tool call 是否都有唯一 id，且 tool 結果用同一個 id 對回？是否有測試保證「不論以哪種方式停止，所有 tool call 都有結果」？
2. messages 是否只在尾端追加？system 與 tool 定義在一次 run 中是否保持不變（保護 prompt cache）？
3. tool 不存在、參數不合 schema、執行時例外，這三種情況是否都轉成可行動的錯誤訊息回填，而不是讓 loop 崩潰？
4. 哪些錯誤類別不回填、直接中止（設定錯誤、權限被撤銷）？清單是否明確寫在程式裡？
5. 有副作用的 tool 是否禁止在 harness 層自動重試？是否規劃了 idempotency key？
6. 是否同時設定了步數上限與 token 預算？兩者的數值是否來自實際 trajectory 的分布，而不是隨手填？
7. 預算是軟上限還是硬上限？可接受的最大超支是多少？
8. 重複呼叫偵測的 key 是否把參數排序後再比較？合理的重複（例如改完程式再跑測試）會不會被誤判？
9. stop_reason 為 max_tokens 時，是否保證不執行半截的 tool call？
10. `RunResult` 是否區分 done、max_steps、budget、loop、max_tokens，讓上層能採取不同動作？
11. tool 結果是否有長度上限？截斷時是否告訴模型原始長度與改查建議？
12. 若採用 streaming，是否只在收到完整的 tool 參數後才執行？串流中斷時，UI 是否能處理已顯示的半段文字？
13. 每次 run 的 trace（每一步的 tool、參數、結果摘要、token）是否被保存，足以在使用者投訴時重建整條 trajectory？

## 4.12 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| API 回 400，訊息提到 tool_use 沒有對應結果 | 某個 tool call 沒有回填結果（例外時 `continue`、提前 return） | 對歷史跑 4.3 節的 `check_history` | 所有路徑都產生 tool 訊息；停止前補上「已取消」結果 |
| 同一題帳單異常高 | 沒有 token 預算，或 tool 回傳過大內容 | 看 trace 中每一步的 input tokens 與 tool 結果長度 | 加 token 預算、結果截斷；大結果改用分頁或 code execution |
| 模型反覆呼叫相同 tool | 結果沒有新資訊，模型以為再試會不同 | 在 trace 中統計相同 (name, args) 次數 | 兩段式重複偵測；tool 結果明說「狀態未更新，建議稍後再查」 |
| 模型呼叫不存在的 tool 或參數名稱錯誤 | 描述含糊、tool 名稱相近、schema 沒有例子 | 看錯誤回填後模型是否修正；統計錯誤率 | 回填列出正確名稱與參數；改善描述與命名（第 5 章） |
| 參數錯誤時有副作用的 tool 執行到一半 | 沒有事前驗證，靠 tool 內部的例外發現錯誤 | 檢查 dispatch 是否在呼叫前比對 schema | 執行前驗證必填與未知參數；有副作用的 tool 用 strict schema |
| 回答突然中斷，或執行了奇怪的參數 | 輸出撞到 max_tokens，半截 JSON 被解析 | 看 stop_reason 是否為 max_tokens | max_tokens 時不執行 tool；調高輸出上限或縮短回答 |
| 模型在權限錯誤後嘗試其他 tool 繞過 | 把不可修正的錯誤當成一般錯誤回填 | 在 trace 中找權限錯誤之後的 tool 呼叫 | 權限錯誤直接中止並告警，不回填給模型 |
| 換了 tool 順序後成本上升 | 每輪重組 tool 清單，破壞 prompt cache 前綴 | 比較變更前後的 cache 命中率 | tool 定義在 run 內固定順序；動態能力改用第 13 章的 deferred 載入 |

## 本章重點整理

- agent loop 的四個動作是呼叫模型、檢查停止條件、執行 tool、回填結果；模型只提議，harness 負責執行與保證。
- 模型是無狀態的，messages 是 agent 在一次任務中唯一的記憶；每一輪都要把完整歷史重送一次。
- messages 有不變式：每個 tool call 的 id 都必須在下一則非 tool 訊息之前收到對應結果，否則主流 API 會拒絕請求。
- system 與 tool 定義放在穩定前綴、messages 只在尾端追加，這個版面同時服務正確性與 prompt caching 的成本。
- tool schema 是寫給模型看的說明書；描述中的例子與合法值，往往比型別本身更能減少參數錯誤。
- dispatch 要處理四種情況：tool 不存在、參數不合 schema、執行例外、結果過長，每一種都不應讓 loop 崩潰。
- 模型能靠改變行為修正的錯誤要回填成可行動的訊息；模型修不好的錯誤（設定、權限）要快速中止並告警。
- 模型 API 本身的 429 與 5xx 由呼叫模型的那一層退避重試，有副作用的 tool 不在 harness 層自動重試。
- 停止條件要多重並行：end_turn 是模型的提議，步數上限、token 預算、重複偵測與 max_tokens 處理是 harness 的保證。
- 每一步的 input tokens 線性成長、累計成本接近平方成長，所以步數上限不能取代 token 預算。
- `RunResult` 要回傳 status，讓上層分得清「答完了」與「放棄了」，並據此轉真人、重試或記錄。
- streaming 只改變 loop 收回應的方式：文字可以邊收邊顯示，tool 參數必須完整後才執行，串流中斷就整則重來。
- 用 ScriptedModel 測試 harness，可以一字不差地重現事故並用 assert 鎖住修正，這是真實模型做不到的。
- loop 本身要保持小；能力與複雜度應該長在 tools、context 與 runtime，後續章節會逐步加上去。

## 延伸問答

> [!question]- Q1. 為什麼停止條件不能只靠模型說「完成了」（end_turn）？
> end_turn 只代表模型這一輪沒有再要求 tool，它是模型的提議，不是任務完成的證明。模型可能過早宣告完成：例如退款 API 其實回傳了錯誤，模型卻告訴使用者「已幫您退款」；也可能永遠不宣告完成：例如在貨態「查詢中」時一直重查。前者是正確性問題，後者是成本與可用性問題。
>
> 所以 harness 需要兩類補強。一類是「保證會停」：步數上限、token 預算、重複偵測、時間上限，不管模型怎麼想，loop 都會在有限的資源內結束。另一類是「保證停得對」：對重要動作做結果驗證（例如退款後再查一次訂單狀態），以及第 27 章的 outcome 評估。兩類缺一不可，只有前者，agent 會穩定地給出錯誤答案；只有後者，agent 偶爾會燒掉一整天的預算。

> [!question]- Q2. tool 丟出例外時，什麼情況應該回填給模型，什麼情況應該讓整個 run 失敗？
> 判斷標準是「模型能不能靠改變行為修正它」。參數錯誤、tool 名稱錯誤、業務規則拒絕（已出貨不能退款）、查無資料，模型讀了錯誤訊息之後都有合理的下一步：修正參數、換一個 tool、改走退貨流程、向使用者確認編號，這些要回填，而且訊息要可行動。
>
> 設定錯誤（API key 失效、連線字串錯誤）、權限被撤銷、資料損毀，模型再怎麼嘗試都不會成功，回填只會讓它繞圈直到步數用完，甚至嘗試用其他 tool 繞過權限。這類錯誤應該讓 run 以失敗狀態快速結束並告警。實作上可以定義一個例外類別（例如 `FatalToolError`），dispatch 遇到它就往外丟，其餘例外才轉成 `is_error` 回填。下游的暫時性錯誤則是第三種：先在 tool 內部有限次重試，用盡後才回填給模型。

> [!question]- Q3. 步數上限和 token 預算都能讓 loop 停下來，為什麼兩個都要？只留一個不行嗎？
> 它們限制的是不同的東西。步數上限限制「轉幾圈」，主要防的是模型反覆嘗試、原地打轉；token 預算限制「花多少錢」，防的是單步就很貴的情況。兩者在 tool 回傳很大的任務上會差非常多：一個報表 tool 一次回傳兩萬字，五步的成本可能超過一般任務五十步，步數上限完全攔不住。
>
> 反過來，只留 token 預算也不好：每步都很便宜的原地打轉，可能要轉上百圈才觸發預算，使用者早就等不及了。而且因為每一步都重送完整歷史，累計 input tokens 接近步數的平方成長，兩者的關係不是線性換算。實務上兩個都設，再加上同步互動需要的時間上限，三者各自取能涵蓋 99% 正常 trajectory 的值，觸發時回傳不同的 status，事後才能分辨是哪一種失控。

> [!question]- Q4. 估算題：一個客服任務平均 12 步，system 加 tool 定義約 3,000 tokens，每一步平均新增 600 tokens 的呼叫與結果。整個任務的 input tokens 大約多少？prompt caching 能省多少？
> 第 k 步（k 從 1 算起）送出的 input 約為 3,000 ＋ 600 ×（k − 1）。12 步加總是 12 × 3,000 ＋ 600 ×（0 ＋ 1 ＋ … ＋ 11）＝ 36,000 ＋ 600 × 66 ＝ 75,600 tokens。對照一下：最後一步單次只有 3,000 ＋ 6,600 ＝ 9,600 tokens，總量是它的將近 8 倍，這就是「累計接近平方成長」的意思。
>
> prompt caching 的效果取決於前綴有多少能重用。因為 messages 只在尾端追加，第 k 步的內容中，除了最新那 600 tokens，其餘都和第 k − 1 步完全相同，理論上可以命中快取。粗略地說，75,600 tokens 中只有約 3,000 ＋ 11 × 600 ＝ 9,600 tokens 是「第一次出現」，其餘約 66,000 tokens 可以用快取價格計費。實際折扣比例、快取存活時間與寫入成本依供應商而異，要查當時的價目表；但結論不變：一旦在中途改寫歷史或調換 tool 順序，這些節省就全部消失。

> [!question]- Q5. 程式找錯：下面這段 loop 有兩個會在 production 出事的錯誤，請指出並說明後果。
> ```python
> for tc in resp.tool_calls:
>     try:
>         out = TOOLS[tc.name](**tc.args)
>     except Exception:
>         continue
>     messages.append({"role": "tool", "tool_call_id": tc.id, "content": out})
> messages.append({"role": "assistant", "content": resp.text, "tool_calls": resp.tool_calls})
> ```
> 第一個錯誤是例外時直接 `continue`：失敗的 tool call 沒有對應的 tool 訊息，違反配對規則，下一次呼叫模型時 API 會拒絕整個請求；就算某個 API 不檢查，模型也看不到失敗原因，無法修正。正確做法是把例外轉成 `is_error` 的 tool 訊息回填。
>
> 第二個錯誤是順序：assistant 訊息被 append 在 tool 結果之後。tool 結果必須跟在提出它的 assistant 訊息後面，順序顛倒同樣會被拒絕，或讓模型誤解誰先誰後。另外還有一個較小的問題：`out` 沒有序列化成字串，dict 直接塞進 content 會在轉成 API 格式時出錯，也沒有長度上限。修法就是 4.9 節 v0.1 的寫法：先 append assistant，再對每個 tool call 呼叫一定會回傳 `(is_error, content)` 的 dispatch。

> [!question]- Q6. 你在 production 看到某一類問題的 status=loop 比例突然從 0.5% 升到 8%，你會怎麼排查？
> 先別急著調高 `max_repeats`，它只會把症狀藏起來。第一步是抽樣 status=loop 的 trajectory，看是哪個 tool、哪種參數在重複。重複呼叫通常代表模型認為「再試一次結果會不同」，所以第二步是看那個 tool 最近回了什麼：如果物流 API 改版後開始回傳空結果或「處理中」，模型自然會一直查，這時要修的是 tool 的回傳訊息，明說「狀態尚未更新，建議 X 小時後再查」。
>
> 第三步是比對時間點：比例上升是否和 prompt 改版、模型版本切換、tool 描述修改同時發生。換模型後行為改變很常見，不同模型對相同錯誤訊息的反應不同。最後要確認偵測本身沒有誤判：例如新上線的功能讓使用者常說「再幫我查一次」，合理的重複被當成迴圈。修完後把幾條代表性的 trajectory 寫成 ScriptedModel 測試，避免回歸。

> [!question]- Q7. 為什麼 loom v0.1 把參數驗證放在 dispatch 裡，而不是讓 tool 函式自己丟 TypeError？
> 有三個理由。第一是副作用安全：如果靠 tool 內部發現參數錯誤，有副作用的 tool 可能在發現錯誤前已經做了一半，例如先寫了一筆退款紀錄才發現缺少金額。事前驗證保證參數錯誤時 tool 本體完全不會執行。
>
> 第二是錯誤訊息的品質：Python 的 `TypeError: refund() got an unexpected keyword argument 'id'` 對模型尚可理解，但不會告訴它正確的參數有哪些；dispatch 有 schema，可以直接回填「缺少 order_id，不認得 id，正確參數是 [order_id]」，模型一次就能修好。第三是一致性：TypeError 也可能來自 tool 內部的程式錯誤，和模型填錯參數混在一起，事後統計會分不清是模型的問題還是程式的 bug。v0.1 只驗證必填與未知參數，第 7 章會加上型別、enum 與巢狀結構的驗證；主流 API 的 strict schema 模式則能在模型產生參數時就保證符合格式。

> [!question]- Q8. 面試追問：如果要讓這個 loop 支援 parallel tool calls，你會改哪些地方？要注意什麼？
> 結構上改動不大，因為 messages 已經用 id 配對：模型一次回傳多個 tool call，harness 平行執行，結果依 tool_call_id 回填即可，回填順序不影響語意。要改的是 dispatch 的呼叫方式（用 thread pool 或 asyncio 同時執行），以及重複偵測與預算的計算要在整批呼叫之前做，不能讓一批十個相同呼叫全部執行完才發現。
>
> 真正要注意的是副作用與一致性。唯讀 tool（查訂單、查物流）可以安全平行；有副作用的 tool 要序列化，或確認彼此不衝突，例如同一張訂單的退款與取消絕不能同時執行。還要決定部分失敗的處理：三個呼叫中一個逾時，其他兩個的結果照常回填，逾時的那個回填錯誤，而不是整批作廢。最後是取消：使用者中途離開時，進行中的呼叫要能取消，並為被取消的呼叫補上「已取消」的結果，維持配對不變式。這些都是第 24 章 runtime 的主題。

## 延伸閱讀

- Anthropic Engineering Blog〈Building effective agents〉（2024）
- Anthropic Engineering Blog〈Writing effective tools for agents — with agents〉（2025）
- OpenAI〈A practical guide to building agents〉（2025）
- HumanLayer，Dex Horthy〈12-Factor Agents〉（2025，GitHub）
- Yao et al.〈ReAct: Synergizing Reasoning and Acting in Language Models〉（ICLR 2023）
- Anthropic Claude Code 文件〈How Claude Code works〉
