---
chapter: 5
title: Tool 設計：Agent-Computer Interface
part: 1
---

# 第 5 章　Tool 設計：Agent-Computer Interface

> [!abstract] 本章地圖
> **核心問題**：同一個模型、同一個 loop，為什麼換一組 tools 就能從「常常答錯又重複退款」變成「少一半步數、每題都對」？tool 到底要怎麼設計，才是一個好的「給模型用的 API」？
>
> **你會學到**：
> - 用 ACI（agent-computer interface）的角度審視 tool：名稱、描述、參數、回傳、錯誤五個面，各自要回答模型的什麼問題
> - 依任務而不是依 endpoint 決定 tool 的粒度，判斷什麼時候該合併成 workflow 級 tool、什麼時候該拆開
> - 設計對 context 友善的回傳：精簡欄位、人類可讀的值、截斷提示與 cursor 分頁
> - 把每個 tool 標上副作用等級（read、write、destructive），並讓 harness 依等級決定核准、重試與平行
> - 實作 idempotency key：由 harness 依業務意圖推導、交給真正執行副作用的那一端去重，讓逾時重試不會變成重複退款
> - 用固定任務集比較兩組 tools 的成功率、步數與 token，並知道這種比較的限制
>
> **前置知識**：第 2 章（tools 元件與副作用的初步概念）、第 3 章（token 與成本、function calling 的形態）、第 4 章（`loom` v0.1 的 dispatch、錯誤回填與停止條件）

## 5.1 故事：八個 tool 與一筆重複退款

第 4 章的 `loom` v0.1 修好了 demo 上的三個事故之後，青鳥的客服團隊開始內部試用。依照第 1 章定下的 autonomy 等級，v1 是 L3：查詢由 agent 自主完成，任何寫入動作都要客服按下「核准」才會執行。為了趕進度，Iris 用第 4 章的 schema 產生器，把 ERP 的 OpenAPI 文件一對一轉成了八個 tool：`get_order`、`fetch_order`、`get_shipment`、`get_customer`、`list_orders`、`get_order_items`、`get_refund_policy`、`create_refund`。每個 tool 都對應一個已經在線上跑了好幾年的 endpoint，Iris 覺得這是最不會出錯的做法。

試用第一週，客服主管整理了一份「機器人迷惑行為」清單。顧客問「B-1042 到哪了」，agent 呼叫了四次模型，最後回答「最後一筆紀錄是 TXG-03 的 AR 事件」，因為物流 endpoint 回傳的是內部事件代碼，模型看不懂，只能照抄。一位顧客把訂單編號的 0 打成英文字母 O，tool 回了 `ERR_4041`，模型把它當成系統故障，回覆「系統暫時查不到，請稍後再試」，顧客等了一個下午又回來投訴。還有一題「上個月買的藍色外套能退嗎」，因為訂單清單裡沒有品名，模型只好把每張訂單的品項逐一打開，再把一千八百字的退貨條款整份讀進 context，這一題的 token 是平均值的四倍多。

真正讓會議室安靜下來的是第四件事。一筆 1,280 元的退款，金流閘道其實已經扣款成功，但回應在網路上遺失，`create_refund` 回了 `ERR_TIMEOUT`。模型合理地判斷「再試一次」，客服看到第二張一模一樣的核准卡片，也合理地按下核准。財務對帳時發現同一張訂單退了兩次。第 4 章說過有副作用的 tool 不在 harness 層自動重試，`loom` 也確實沒有自動重試；可是這次重試是模型自己提出、人自己核准的，harness 的那條規則完全攔不住。

檢討會上，資安工程師 Maya 問了一個沒人答得出來的問題：「這八個 tool 裡，哪幾個會動到錢？清單在哪裡？」產品經理阿哲關心的是另一件事：同樣的問題，為什麼有時兩步、有時六步，帳單要怎麼估？老陳聽完，在白板上寫了一句話：「你把 ERP 的 API 給了模型，但沒有給它一個介面。」意思是：這八個 endpoint 原本是寫給讀過文件、會除錯、會問同事的工程師用的；現在使用者換成了一個每次只能讀描述、看不到程式碼、會照字面猜的模型，介面就必須重新設計。

這一章就是 Iris 重構 tools 的過程。我們會先建立「tool 是給模型用的 API」這個心智模型，再依序處理命名與描述、粒度、回傳與分頁、錯誤訊息、副作用分級與 idempotency，最後談怎麼評估 tool 的好壞。「動手做」會給 `loom` 加上 `loom.tools` 模組，用 ScriptedModel 讓「設計差」與「設計好」兩組 tools 跑同一組四個任務，量出成功率、步數與 token 的差異，並重現、修好那筆重複退款。

## 5.2 Tool 是給模型用的 API：ACI 的心智模型

**ACI**（agent-computer interface，agent 與電腦之間的介面）是借用 HCI（human-computer interaction，人機互動）的說法：設計給人用的介面時，我們會研究使用者看得到什麼、會怎麼誤解、犯錯時怎麼引導；設計給 agent 用的 tool，也要用同樣的心力。這個詞因 Princeton 團隊的 SWE-agent 論文（2024）而廣為人知，論文發現只要改變 agent 看檔案、搜尋與編輯程式碼的介面，同一個模型解決軟體問題的成功率就有明顯差異。Anthropic 的〈Building effective agents〉也把「精心設計 ACI」列為打造 agent 的三個核心原則之一，建議投入在 ACI 的心力要和投入在人機介面上的一樣多；文中還提到，他們打造 SWE-bench 的 agent 時，花在優化 tools 的時間比優化整體 prompt 還多。

為什麼不能直接沿用給工程師的 API？因為兩種使用者的條件差太多了。下表把差異攤開來看，每一列都對應本章後面的一個設計原則。

| 面向 | 傳統 API 的使用者（工程師） | tool 的使用者（模型） | 設計上的後果 |
|---|---|---|---|
| 怎麼學會用 | 讀文件、看範例、問同事，學一次記很久 | 每次呼叫都重讀名稱與描述，沒有其他資訊來源 | 描述就是全部的文件，要寫清楚何時用、何時不用 |
| 看得到什麼 | 原始碼、log、除錯器 | 只有 tool 回傳的文字 | 回傳與錯誤訊息要自帶下一步的線索 |
| 閱讀成本 | 幾乎免費 | 每個字都是 token，佔用有限的注意力 | 回傳要精簡；工具定義本身也要計成本 |
| 犯錯時 | 看錯誤碼查文件 | 照字面猜，可能把 `ERR_4041` 當成系統故障 | 錯誤要用自然語言說明原因與修法 |
| 組合多個呼叫 | 寫程式一次串好，執行很便宜 | 每多一個呼叫就多一輪推論與延遲 | 常見的連鎖步驟要合併成一個 tool |
| 重試 | 由程式碼控制，次數固定 | 模型隨時可能「再試一次」，而且參數可能稍有不同 | 寫入要有 idempotency，key 不能交給模型產生 |

表中最容易被低估的是第三列與第五列。對工程師來說，呼叫三個 endpoint 再自己拼起來是理所當然的事；對模型來說，那是三輪推論、三次重送整段歷史、三次出錯的機會。第 4 章 4.5 節已經量過，每多一步，該步的 input tokens 就多一截，累計成本接近平方成長。所以好的 tool 設計同時改善三件事：正確率（模型比較不會選錯、填錯）、成本（步數與 token 變少）、延遲（串行的模型呼叫變少）。

```text
                       模型看得到的（每次呼叫都送進 context）
 ┌──────────────────────────────────────────────────────────────────┐
 │ ① 名稱   orders_get_overview                                     │
 │ ② 描述   做什麼／何時用／何時改用別的 tool／回傳什麼             │
 │ ③ 參數   order_id: string，格式 B- 加四位數字，例如 B-1042       │
 └──────────────────────────────┬───────────────────────────────────┘
                                │ tool call（模型提議）
 ┌──────────────────────────────▼───────────────────────────────────┐
 │ harness：驗證參數 → 副作用政策（核准、idempotency key）          │ 模型
 │          → 執行實作（ERP、物流、金流）→ 整形結果（欄位、截斷）   │ 看不到
 └──────────────────────────────┬───────────────────────────────────┘
                                │ tool result（觀察）
 ┌──────────────────────────────▼───────────────────────────────────┐
 │ ④ 回傳   精簡、人類可讀、只含下一個決定需要的欄位，標示是否截斷  │ 模型
 │ ⑤ 錯誤   發生什麼、為什麼、下一步怎麼做、能不能重試              │ 看得到
 └──────────────────────────────────────────────────────────────────┘
```

這張圖是本章的地圖，把一個 tool 拆成五個「模型看得到的面」和一段「模型看不到的中間層」。上半部的名稱、描述、參數，決定模型**會不會選對 tool、填對參數**；它們每次呼叫都會送進 context，所以既是說明書，也是固定成本。中間層是 harness 與 tool 實作，負責驗證、權限、副作用政策與真正的執行；這一層的規則必須由程式保證，不能寫在描述裡指望模型遵守。下半部的回傳與錯誤，決定模型**看到結果後能不能做出正確的下一步**。本章 5.3 到 5.6 節依序處理這五個面，5.7 與 5.8 節處理中間層的副作用政策。

一個實用的檢驗方法是「新人測試」：把 tool 的名稱、描述與參數印出來，交給一位剛到職、沒看過程式碼的客服同仁，問對方「顧客說 B-1042 到哪了，你會用哪一個？填什麼？」如果對方猶豫，模型也會猶豫。Anthropic 在 context engineering 的文章裡說過類似的話：如果人類工程師都說不出某個情況該用哪個 tool，就不能期待 agent 做得更好。

> [!warning] 常見誤解
> 「模型越來越強，tool 隨便包一包它也會想辦法用。」更強的模型確實更會從爛介面裡挖出答案，但代價是更多步數與 token，而且它無法從回傳裡得到不存在的資訊：物流 endpoint 沒有給預計送達日，再強的模型也只能照抄事件代碼或自己編一個。tool 設計決定的是「資訊與動作的上限」，模型能力決定的是「在這個上限內做得多好」。

## 5.3 命名、描述與參數：寫給新人的說明書

模型選 tool 的過程，很像人在一排沒有圖示的按鈕前面找對的那一個：只能靠上面的字。所以第一個要處理的是**名稱**。好的名稱有三個特徵：用一致的格式（例如「資源_動作」或「服務_資源_動作」）、動詞精確（`search` 表示依條件找、`get` 表示用 id 取一筆、`create` 表示新增），以及彼此之間沒有同義詞。青鳥原本的 `get_order` 與 `fetch_order` 就是反例：兩個名稱意思一樣，模型只能猜，猜錯就多花一步。依服務或資源加前綴的做法叫 **namespacing**（命名空間），例如 `orders_search`、`refunds_create`；當 agent 同時接上多個系統（第 14 章的 MCP server），前綴能避免兩個系統都有一個叫 `search` 的 tool。

第二個是**描述**。描述要回答四個問題：這個 tool 做什麼、什麼情況該用、什麼情況改用別的、回傳什麼。最常被省略的是第三個，偏偏它最能減少選錯：`orders_get_overview` 的描述寫「只有 email 時改用 orders_search」，等於在兩個 tool 之間畫了一條清楚的界線。把描述當成給新人的交接說明來寫，寫出你腦中那些「大家都知道」的慣例：訂單編號的格式、金額的單位是元還是分、日期用哪個時區。描述中的限制如果很重要（例如「不可逆，需客服核准」），就要同時由 harness 強制執行，描述只是讓模型提早知道，不是安全機制。

第三個是**參數**。參數名稱不能有歧義：`id` 是誰的 id？`user` 是 email、帳號還是 UUID？改成 `order_id`、`customer_email` 就不會填錯。有限集合要用 **enum**（列舉，限定參數只能是幾個值之一），例如訂單狀態只能是 `pending`、`shipped`、`delivered`。格式慣例用描述加例子說明：「格式 B- 加四位數字，例如 B-1042」。Anthropic 在〈Building effective agents〉的附錄裡把這件事稱為 tool 的 **poka-yoke**（防呆，源自製造業「讓錯誤不可能發生」的設計）：與其在描述裡叮嚀模型，不如改變參數讓它很難犯錯；文中的例子是，他們的 coding agent 在切換目錄後常把相對路徑弄錯，改成只接受絕對路徑之後，這類錯誤就消失了。

| 元素 | 設計差的寫法 | 設計好的寫法 | 解決的問題 |
|---|---|---|---|
| 名稱 | `get_order`、`fetch_order` 並存 | 只留 `orders_get_overview` | 同義 tool 讓模型猜 |
| 描述：做什麼 | 「取得訂單」 | 「一次取得狀態、品項、物流進度與退款資格」 | 模型不知道回傳裡有沒有它要的東西 |
| 描述：何時用／何時不用 | 沒寫 | 「有訂單編號時用；只有 email 改用 orders_search」 | 相近 tool 的邊界 |
| 參數名稱 | `id`、`user`、`ref` | `order_id`、`customer_email` | 填錯欄位、填錯種類的 id |
| 參數值域 | 任意字串 | enum、格式說明、例子 | 填出系統不認得的值 |
| 風險標示 | 沒寫 | 「【不可逆】需客服核准」，且 harness 強制 | 模型輕率呼叫；人看不出風險 |

這些規則大多可以機器檢查。下面這段程式是一個最小的 **tool lint**（靜態檢查器）：它不需要模型，只讀 tool 定義，就能抓出名稱格式、描述缺項、參數歧義、缺少 enum 與 tool 之間的同義重疊。把它放進 CI，任何人新增或修改 tool 時都會先過一遍，成本幾乎是零。

```python
from __future__ import annotations

import re
from typing import Any

AMBIGUOUS = {"id", "user", "data", "query", "type", "value", "info"}   # 單獨出現時意思不明的參數名


def lint_tool(t: dict[str, Any]) -> list[str]:
    """對單一 tool 定義做靜態檢查。回傳問題清單；規則都是「模型讀不懂」的常見原因。"""
    issues: list[str] = []
    name, desc = t["name"], t.get("description", "")
    props = t.get("parameters", {}).get("properties", {})
    if not re.fullmatch(r"[a-z]+(_[a-z]+)+", name):
        issues.append(f"名稱 {name!r} 不是 小寫_動詞 或 服務_動詞 形式")
    if len(desc) < 30:
        issues.append(f"描述只有 {len(desc)} 字，說不清楚做什麼、何時用")
    if "何時" not in desc and "當" not in desc:
        issues.append("描述沒有說明何時該用（或不該用）")
    if "回傳" not in desc:
        issues.append("描述沒有說明回傳什麼")
    for p, spec in props.items():
        if p in AMBIGUOUS:
            issues.append(f"參數 {p!r} 名稱有歧義，應寫成 order_id、customer_email 這類")
        if not spec.get("description"):
            issues.append(f"參數 {p!r} 沒有描述")
        if spec.get("type") == "string" and p.endswith("status") and "enum" not in spec:
            issues.append(f"參數 {p!r} 是有限集合卻沒有 enum")
    return issues


def lint_toolset(tools: list[dict[str, Any]]) -> list[str]:
    """跨 tool 的檢查：名稱只差在同義動詞的 tool，模型（和人）都分不清。"""
    synonyms = {"get": "read", "fetch": "read", "query": "read", "lookup": "read"}
    seen: dict[str, str] = {}
    issues = []
    for t in tools:
        verb, _, noun = t["name"].partition("_")
        key = synonyms.get(verb, verb) + "_" + noun
        if key in seen:
            issues.append(f"{seen[key]} 與 {t['name']} 功能重疊，模型難以選擇")
        seen[key] = t["name"]
    return issues


bad = [
    {"name": "get_order", "description": "取得訂單",
     "parameters": {"properties": {"id": {"type": "string"}}}},
    {"name": "fetch_order", "description": "訂單資料（舊版）",
     "parameters": {"properties": {"id": {"type": "string"}}}},
    {"name": "listOrders", "description": "列出訂單",
     "parameters": {"properties": {"user": {"type": "string"}, "status": {"type": "string"}}}},
]
good = [
    {"name": "orders_get_overview",
     "description": "用訂單編號查詢一張訂單的狀態、物流進度與退款資格。當使用者提到具體訂單編號時使用；"
                    "只有 email 時改用 orders_search。回傳精簡摘要，需要品項明細時設 response_format=detailed。",
     "parameters": {"properties": {
         "order_id": {"type": "string", "description": "訂單編號，格式 B- 加四位數字，例如 B-1042"},
         "response_format": {"type": "string", "enum": ["concise", "detailed"], "description": "預設 concise"}}}},
    {"name": "orders_search",
     "description": "依顧客 email 與關鍵字搜尋訂單。當使用者沒有給訂單編號時使用。回傳最多 limit 筆摘要與 next_cursor。",
     "parameters": {"properties": {
         "customer_email": {"type": "string", "description": "顧客 email，例如 amy@example.com"},
         "order_status": {"type": "string", "enum": ["any", "pending", "shipped", "delivered"],
                          "description": "只看某個狀態，預設 any"}}}},
]

for label, tools in (("設計差", bad), ("設計好", good)):
    report = {t["name"]: lint_tool(t) for t in tools}
    overlap = lint_toolset(tools)
    total = sum(map(len, report.values())) + len(overlap)
    print(f"── {label}：{total} 個問題")
    for name, issues in report.items():
        for i in issues:
            print(f"  {name:<20} {i}")
    for i in overlap:
        print(f"  {'(跨 tool)':<20} {i}")

assert sum(len(lint_tool(t)) for t in good) == 0 and not lint_toolset(good)
assert any("重疊" in i for i in lint_toolset(bad))
```

```text
── 設計差：19 個問題
  get_order            描述只有 4 字，說不清楚做什麼、何時用
  get_order            描述沒有說明何時該用（或不該用）
  get_order            描述沒有說明回傳什麼
  get_order            參數 'id' 名稱有歧義，應寫成 order_id、customer_email 這類
  get_order            參數 'id' 沒有描述
  fetch_order          描述只有 8 字，說不清楚做什麼、何時用
  fetch_order          描述沒有說明何時該用（或不該用）
  fetch_order          描述沒有說明回傳什麼
  fetch_order          參數 'id' 名稱有歧義，應寫成 order_id、customer_email 這類
  fetch_order          參數 'id' 沒有描述
  listOrders           名稱 'listOrders' 不是 小寫_動詞 或 服務_動詞 形式
  listOrders           描述只有 4 字，說不清楚做什麼、何時用
  listOrders           描述沒有說明何時該用（或不該用）
  listOrders           描述沒有說明回傳什麼
  listOrders           參數 'user' 名稱有歧義，應寫成 order_id、customer_email 這類
  listOrders           參數 'user' 沒有描述
  listOrders           參數 'status' 沒有描述
  listOrders           參數 'status' 是有限集合卻沒有 enum
  (跨 tool)             get_order 與 fetch_order 功能重疊，模型難以選擇
── 設計好：0 個問題
```

輸出的前五組是三個設計差的 tool 各自的問題。`get_order` 與 `fetch_order` 的描述只有幾個字，沒說何時用、回傳什麼，參數還叫 `id`；`listOrders` 用了駝峰命名，`user` 參數有歧義，`status` 明明只有幾個合法值卻沒有 enum。倒數第二行是跨 tool 的檢查：`get` 與 `fetch` 被視為同義動詞，於是 `get_order` 與 `fetch_order` 被標成功能重疊，這正是 5.1 節模型第一步選錯的原因。設計好的兩個 tool 是 0 個問題，最後的 assert 鎖住這個結果。

lint 能抓的是「明顯寫壞」，抓不到「寫得通順但誤導」：一段描述可以通過所有規則，卻把退款資格的條件寫錯。所以 lint 是第一道門檻，真正的判斷仍然要靠 5.9 節的任務評估與閱讀 transcript。另外要注意，lint 規則本身也要隨團隊慣例調整，例如有的團隊偏好 `search_orders`（動詞在前）而不是 `orders_search`；重點不是哪一種格式，而是整組 tools 一致。

> [!note] 2026 現況：讓參數「保證」符合 schema
> 截至 2026 年 10 月，三家主要 API 都提供在模型產生 tool 參數時就強制符合 JSON Schema 的模式（依各家公開文件，參數名稱以官方文件為準）：OpenAI 的 function tool 可設 `strict: true`，Anthropic 的 tool 定義也有 `strict: true`，Gemini 則以 `validated` 模式保證呼叫符合 schema。這類 **constrained decoding**（受限解碼：產生 token 時直接排除不合 schema 的選項）能消除「缺欄位、型別錯」這類語法錯誤，但消除不了語意錯誤，例如把別人的訂單編號填進去；第 7 章會深入。另外，Anthropic 在 2025 年 11 月推出 beta 的 `input_examples` 欄位，讓 tool 定義附上 1 到 5 個真實的參數範例，用來表達 JSON Schema 說不清楚的慣例（日期格式、何時填選填欄位）；該公司公開的內部測試中，複雜參數的處理正確率從 72% 提升到 90%。

## 5.4 粒度：依任務設計，而不是依 endpoint

**粒度**（granularity）是一個 tool 做多少事。光譜的一端是 **CRUD 級** tool：每個 tool 對應一個資料表的新增、讀取、更新、刪除，例如 `get_customer`、`list_orders`、`get_order_items`；另一端是 **workflow 級** tool：一個 tool 完成使用者心中的一件事，例如「查這張訂單現在怎樣、能不能退」的 `orders_get_overview`。ERP 的 API 天生是 CRUD 級的，因為它是寫給要自由組合資料的工程師；而客服 agent 面對的是任務，任務往往需要好幾個 CRUD 呼叫串起來。

```text
 任務：「我是 amy@example.com，上個月買的藍色外套還能退嗎？」

 CRUD 級（8 個 tool）                              workflow 級（4 個 tool）
 ─────────────────────────────────────            ─────────────────────────────────
 model ─► get_customer(email)                      model ─► orders_search(
            └► customer_uuid                                  customer_email, keyword=外套)
 model ─► list_orders(customer_uuid)                          └► B-1033 藍色連帽外套
            └► 4 筆：只有 uuid、狀態、日期                       已送達，可退貨，期限 09-22
 model ─► get_order_items(uuid #1) ─► 帆布托特包    model ─► 回答
 model ─► get_order_items(uuid #2) ─► 藍色連帽外套
 model ─► get_refund_policy() ─► 1,800 字條款
 model ─► 自己算到貨日＋7 天，回答

 6 次模型呼叫、5 次 tool、約 7,200 tokens          2 次模型呼叫、1 次 tool、約 1,600 tokens
 中間每一步都可能選錯 uuid、算錯日期                 日期與資格由確定性程式計算
```

左右兩欄是同一個任務的兩條 trajectory，數字來自 5.10 節的實際執行。左邊的每一個箭頭都是一輪推論：模型要先用 email 換 UUID，再用 UUID 列訂單，因為清單裡沒有品名，只好逐張打開品項，最後讀完整份退貨條款，自己計算到貨日加七天。這裡有三個風險：模型可能把 UUID 抄錯一個字元（hallucinated tool call 最常見的形態）、可能漏看某張訂單、可能把日期算錯。右邊把「搜尋＋品項＋退款資格」合成一個 tool，日期與資格由程式計算，模型只需要讀結果、組織回答。第 2 章提過的 `get_order_overview`，就是這個想法。

合併的原則可以濃縮成一句：**把「模型每次都會照同樣順序做」的連鎖步驟收進 tool 裡，把「需要判斷」的分岔留給模型**。查訂單之後幾乎一定要看物流與退款資格，所以合併；「要退款還是改建退貨單」取決於訂單狀態與顧客意願，所以留給模型，並用兩個 tool 表達。Anthropic 的〈Writing effective tools for agents〉舉過同樣的例子：與其提供 `list_contacts` 讓 agent 把整份通訊錄讀進 context，不如提供 `search_contacts`；與其讓 agent 自己串 `list_users`、`list_events`、`create_event`，不如提供一個 `schedule_event`。

但合併也有極限。第一，不要把讀和寫合在同一個 tool：`check_and_refund` 看起來省了一步，卻讓「只是想查一下」的呼叫也有機會動到錢，副作用分級（5.7 節）也無從標示。第二，不要做出萬用 tool：一個 `erp_call(endpoint, payload)` 雖然只有一個 tool，實際上是把整份 API 文件的負擔丟回給模型，而且權限無法控管。第三，workflow 級 tool 會把「業務規則」寫死在程式裡，例如七天鑑賞期；這是優點（確定、可測試），也代表規則改了要改程式，而不是改 prompt。

| 情況 | 建議粒度 | 例子 | 理由 |
|---|---|---|---|
| 幾乎每次都依同樣順序串接的讀取 | 合併成 workflow 級 | `orders_get_overview` | 少步數、少出錯、少 token |
| 結果需要確定性計算（日期、金額、資格） | 在 tool 內計算後回傳結論 | 「可退貨，期限 09-22」 | 模型算數與日期容易錯 |
| 依情況走不同分支的動作 | 拆成多個 tool，界線寫進描述 | `refunds_create` vs `returns_create` | 判斷留給模型，風險分開標示 |
| 讀取與寫入 | 一定分開 | `orders_search` 與 `refunds_create` | 唯讀可平行、可重試；寫入要核准 |
| 探索性任務、步驟無法預期 | 保留較細的 tool，或改用 code execution | 營運分析的任意查詢 | 合併會限制彈性；大量組合用第 13 章的 code-as-action |
| 很少使用的進階操作 | 不放進常駐 tool 清單 | 修改發票抬頭 | 降低選擇負擔；需要時用第 13 章的 tool search 載入 |

這張表的最後兩列提醒，粒度不是越粗越好。客服任務的種類有限、路徑相對固定，適合偏粗的 workflow 級 tool；營運分析或 coding 任務的組合方式無法事先列舉，硬做成 workflow 級 tool 只會不斷加參數。另外，tool 數量本身也是成本：OpenAI 的〈A practical guide to building agents〉指出，問題不只在 tool 的數量，更在於 tool 之間的相似與重疊，有的團隊能把十五個以上界線清楚的 tool 管理得很好，有的團隊不到十個彼此重疊的 tool 就出問題。

> [!warning] 常見誤解
> 「tool 越少越好，最好只有一個。」少的是「模型需要做的選擇」，不是 tool 的總數。把八個 CRUD tool 合成四個任務 tool，是減少了模型要組合的步驟；把四個合成一個帶 `action` 參數的萬用 tool，則只是把選擇從「選 tool」搬到「填參數」，還失去了按 tool 設定權限與副作用等級的能力。

## 5.5 回傳格式、截斷與分頁

tool 的回傳就是模型的下一個觀察，它會原封不動地進入 messages，在之後的每一輪被重讀。所以回傳要以「模型的下一個決定需要什麼」為準，而不是「資料庫裡有什麼」。5.1 節的 `get_order` 回傳了付款閘道代碼、詐騙分數、同步旗標，模型一個都用不到，卻每一輪都要為它們付錢；更糟的是，最關鍵的預計送達日根本不在裡面。

回傳設計有四條原則。第一，**用人類可讀的值取代內部代碼**：「已抵達台中轉運中心，預計明天送達」而不是 `{"code": "AR", "hub": "TXG-03"}`；UUID 這類長串識別碼也盡量換成短的業務編號，因為模型在複製長 UUID 時容易出錯，Anthropic 的工具設計文章也觀察到，把不透明的 UUID 換成有語意的名稱能減少幻覺。第二，**只放下一步需要的欄位**，並提供一個 `response_format` 參數（concise 或 detailed）讓模型在需要時拿完整資料。第三，**結果過大時截斷並給出路**：說清楚總共幾筆、顯示了哪幾筆、怎麼取下一頁或縮小範圍。第四，**格式穩定**：同一個 tool 每次回傳的欄位名稱與順序一致，模型才能可靠地讀取。

**分頁**（pagination）是處理大量結果的標準做法。對 agent 來說，比起用頁碼或 offset，更建議用 **cursor**（游標：一個不透明字串，代表「下一頁從哪裡開始」）。原因是模型不需要、也不應該自己計算 offset：它只要把上一頁回傳的 `next_cursor` 原樣傳回即可，少了一個算錯的機會；而且資料在兩次呼叫之間有新增時，cursor 的實作可以避免重複或遺漏。

```text
 model                          orders_search                           訂單資料庫
   │── customer_email, limit=5 ──►│                                        │
   │                              │── 查詢（offset 0，取 5 筆）───────────►│
   │                              │◄───────────────────────── 23 筆中的 5 ─│
   │◄─ total_matches=23           │                                        │
   │   showing=1-5、orders[5]     │  只留 order_id、status、total、item    │
   │   next_cursor="eyJvIjogNX0="  │  拿掉 UUID、倉庫代碼、更新時間         │
   │   hint=「帶 next_cursor 取下一頁，或加 order_status 縮小範圍」         │
   │                              │                                        │
   ├─ 選擇 A：cursor=上一頁的 next_cursor ──► 回傳 6-10                    │
   └─ 選擇 B：order_status=shipped, limit=10 ──► total=8、next_cursor=null │
                                                 （沒有更多，不再翻頁）
```

這張資料流圖從模型的第一次呼叫開始。tool 只取 5 筆，並在回傳中附上三樣東西：總筆數（讓模型知道自己沒看到全部）、`next_cursor`（取下一頁的憑證），以及一句 hint（下一步的兩種選擇）。模型接著有兩條路：選擇 A 原樣帶回 cursor 取得第 6 到 10 筆；選擇 B 改用篩選條件縮小範圍，這通常比一頁頁翻更好。最後一頁的 `next_cursor` 是 null，而且沒有 hint，明確告訴模型「已經看完了」，避免它為了確認而多翻一次。

```python
from __future__ import annotations

import base64
import json

# 假資料：一位大客戶有 23 張訂單（批發網店常見）
ORDERS = [{"order_id": f"B-{2000 + i}", "uuid": f"9f1c{i:04d}-77aa-4e0b-b2f1-{i:012d}",
           "status": ["pending", "shipped", "delivered"][i % 3], "total": 300 + 45 * i,
           "items": [{"sku_uuid": f"sku-{i}-a", "name": "棉質T恤", "qty": 2}],
           "warehouse_code": "TC-W03", "updated_at": f"2026-09-{1 + i % 28:02d}T10:00:00Z"}
          for i in range(23)]


def encode_cursor(offset: int) -> str:
    # cursor 對模型是不透明字串：模型只要原樣傳回，不需要（也不應該）自己算 offset
    return base64.urlsafe_b64encode(json.dumps({"o": offset}).encode()).decode()


def decode_cursor(cursor: str) -> int:
    return json.loads(base64.urlsafe_b64decode(cursor))["o"]


def orders_search(customer_email: str, order_status: str = "any", limit: int = 5,
                  cursor: str | None = None, response_format: str = "concise") -> str:
    rows = [o for o in ORDERS if order_status in ("any", o["status"])]
    start = decode_cursor(cursor) if cursor else 0
    page = rows[start:start + limit]
    if response_format == "concise":       # 只留下「下一個決定」需要的欄位，拿掉 UUID 與內部代碼
        page = [{"order_id": o["order_id"], "status": o["status"], "total": o["total"],
                 "item": o["items"][0]["name"]} for o in page]
    more = start + limit < len(rows)
    result = {"total_matches": len(rows), "showing": f"{start + 1}-{start + len(page)}",
              "orders": page, "next_cursor": encode_cursor(start + limit) if more else None}
    if more:
        result["hint"] = "還有更多結果：帶 next_cursor 取下一頁，或加上 order_status 縮小範圍"
    return json.dumps(result, ensure_ascii=False)


def list_orders_raw(customer_email: str) -> str:
    """設計差的版本：把資料庫整包倒給模型。"""
    return json.dumps(ORDERS, ensure_ascii=False)


raw = list_orders_raw("wholesale@example.com")
first = orders_search("wholesale@example.com")
p1 = json.loads(first)
second = json.loads(orders_search("wholesale@example.com", cursor=p1["next_cursor"]))
shipped = json.loads(orders_search("wholesale@example.com", order_status="shipped", limit=10))
detailed = orders_search("wholesale@example.com", limit=5, response_format="detailed")

print(f"整包傾倒        {len(raw):>5} 字元，23 筆，含 UUID 與內部代碼")
print(f"concise 第一頁  {len(first):>5} 字元，{p1['showing']}／{p1['total_matches']}，hint={p1['hint'][:12]}…")
print(f"detailed 第一頁 {len(detailed):>5} 字元")
print(f"第二頁          showing={second['showing']}  第一筆={second['orders'][0]['order_id']}")
print(f"篩選 shipped    total_matches={shipped['total_matches']}  next_cursor={shipped['next_cursor']}")
assert second["orders"][0]["order_id"] == "B-2005"            # 第二頁接續第一頁，不重複、不遺漏
assert shipped["next_cursor"] is None and "hint" not in shipped  # 最後一頁明說沒有更多
assert len(first) * 5 < len(raw)
```

```text
整包傾倒         5439 字元，23 筆，含 UUID 與內部代碼
concise 第一頁    518 字元，1-5／23，hint=還有更多結果：帶 nex…
detailed 第一頁  1318 字元
第二頁          showing=6-10  第一筆=B-2005
篩選 shipped    total_matches=8  next_cursor=None
```

第一行是設計差的做法：23 筆訂單整包倒出來，5,439 個字元，裡面大半是 UUID 與內部代碼。第二行是 concise 格式的第一頁，只有 518 個字元，並附上「1-5／23」與 hint；同樣是 5 筆，detailed 格式（第三行）是 1,318 個字元，差了兩倍多，這就是 `response_format` 的價值：模型只有在真的需要品項明細時才付這個錢。第四行驗證 cursor 分頁接續正確，第二頁從 B-2005 開始，不重複也不遺漏。第五行是改用篩選條件：shipped 只有 8 筆，一頁就裝得下，`next_cursor` 是 None。最後的 assert 鎖住「concise 第一頁不到整包傾倒的五分之一」。

截斷要放在哪一層，也是設計決定。第 4 章的 `loom` v0.1 在 harness 層用字元數做通用截斷，這是最後一道防線，它不懂資料的結構，只能從中間切斷。tool 層的分頁與篩選才是主要手段，因為 tool 知道「一筆」是什麼、總數是多少、該建議什麼篩選條件。兩層都要有：tool 層讓結果有意義地變小，harness 層保證任何 tool（包括第 14 章接進來、不是自己寫的 MCP tool）都不會一次塞爆 context。

> [!note] 2026 現況：回傳大小與結構化回傳
> 截至 2026 年 10 月，Anthropic 的工具設計文章提到 Claude Code 預設把單次 tool 回傳限制在 25,000 tokens；同文的範例中，同一份資料以 detailed 格式回傳約 206 tokens、concise 格式約 72 tokens。MCP 規格（第 14 章）允許 tool 宣告 `outputSchema` 並以 `structuredContent` 回傳結構化結果，讓 client 程式能直接驗證與使用回傳，同時仍可提供給模型閱讀的文字內容；2026-07-28 版規格允許 `outputSchema` 使用任意 JSON Schema 2020-12 關鍵字。

## 5.6 錯誤訊息：告訴模型下一步

第 4 章 4.6 節建立了 harness 層的原則：tool 的失敗是一種觀察，要回填給模型；模型修不好的錯誤（設定、權限）要快速中止。那一節處理的是「錯誤怎麼送回去」，這一節處理的是「錯誤裡要寫什麼」，而這是 tool 設計者的責任，因為只有 tool 知道錯誤的業務意義。`ERR_4041` 對寫 ERP 的工程師來說是「查無訂單」，對模型來說只是一串看起來像系統故障的字元。

一則**可行動的錯誤訊息**包含三個部分：發生了什麼（「找不到訂單 B-1O42」）、可能的原因（「編號格式是 B- 加四位數字，英文字母 O 可能是數字 0 的誤植」）、下一步怎麼做（「請向使用者確認編號，不要自行猜測」）。第三部分最重要，它把錯誤從「死路」變成「指路」。注意這個例子刻意叫模型**不要猜**：tool 其實可以算出 B-1042 是最接近的編號，但替使用者決定「你指的應該是 B-1042」可能查到別人的訂單，所以讓模型把選擇交還給使用者，這是安全與正確性的考量，不只是措辭。

另一個常被混淆的是「錯誤」與「空結果」。搜尋 amy 的訂單、關鍵字「外套」而沒有找到，這不是錯誤，是一個合法的答案，應該回傳 `total_matches: 0` 並附上建議（「沒有符合的訂單；可以放寬關鍵字或確認 email」），而不是丟例外。把空結果當錯誤，模型會以為工具壞了而反覆重試；把錯誤當空結果（例如資料庫逾時卻回傳空清單），模型會告訴顧客「您沒有任何訂單」，這更糟。

| 錯誤類別 | 例子 | 訊息要包含 | 是否可重試 | 誰採取下一步 |
|---|---|---|---|---|
| 參數格式錯誤 | `B-1O42` | 正確格式與例子 | 修正後可以 | 模型（或向使用者確認） |
| 查無資料 | 訂單不存在 | 已確認不存在、可能原因、不要猜 | 不可（同參數） | 使用者確認 |
| 業務規則拒絕 | 已出貨不能直接退款 | 規則、替代 tool | 不可（同參數） | 模型改走別條路 |
| 暫時性失敗 | 物流 API 逾時（唯讀） | 已在 tool 內重試幾次、建議稍後再查 | 唯讀可以 | tool 內部先重試，再交給模型 |
| 結果未知 | 金流逾時，可能已扣款 | 「結果未知，可能已成功」、重試是否安全 | 只有在有 idempotency 時 | 模型用相同意圖重試，或轉真人 |
| 權限不足 | 查詢別的商家的訂單 | 不需細節，明說不可繞過 | 不可 | harness 中止或轉真人 |

表中的「結果未知」是最危險、也最常被忽略的一類。對唯讀 tool 來說，逾時就是失敗，重查一次無害；對有副作用的 tool 來說，逾時代表「不知道成功了沒」，這時錯誤訊息怎麼寫，直接決定模型會不會重複執行。設計差的 `ERR_TIMEOUT` 只說了失敗，模型自然會重試；設計好的訊息說「結果未知，可能已成功；可以用相同參數重試，系統會以 idempotency key 確認，不會重複退款」，同時暗示了重試的安全條件。但要記得，訊息只是讓模型做出合理決定，真正保證不重複的是 5.8 節的機制，不是這段文字。反過來說，如果 destructive tool 沒有一路傳到執行端的 idempotency key，「結果未知」就絕對不能直接重試：tool 應該回報「結果未知，請勿重試」，由 harness 先向執行端查詢狀態，或轉給真人確認。有 key 的「重試」本質上是向執行端確認結果，而不是再做一次。

> [!tip] 錯誤訊息也要考慮誰會看到
> 模型常常會把錯誤訊息的內容轉述給使用者。所以訊息不要夾帶內部主機名稱、SQL、stack trace 或其他客戶的資料；這些既浪費 token，也可能洩漏內部資訊。需要給工程師除錯的細節，寫進 trace（第 29 章），回填給模型的只留它和使用者需要知道的部分。

## 5.7 副作用分級：read、write、destructive

回到 Maya 的問題：「哪幾個 tool 會動到錢？」答案不應該靠讀程式碼，而應該是 tool 定義上的一個欄位。**副作用分級**（effect level）就是替每個 tool 標上它對外部世界的影響程度。本書使用三級，延續第 2 章的說法：

- **read**（唯讀）：不改變任何狀態，重複呼叫一百次結果也只有「查了一百次」。例如 `orders_get_overview`、`orders_search`。
- **write**（可回復的寫入）：改變狀態，但可以撤銷或補償，影響範圍在系統內部。例如 `returns_create`（建立退貨單，物流取件前可以取消）、在工單上加註記。
- **destructive**（不可逆或對外的動作）：一旦執行就無法乾淨地撤銷，或已經影響到系統外的人與錢。例如 `refunds_create`（錢退出去了）、寄 email 給顧客、取消已交給物流商的訂單。

分級的目的是讓 harness 能「依等級而不是依名稱」套用政策。這和第 1 章的 autonomy 等級是兩件事但緊密相關：autonomy 是依「動作」決定的，而副作用等級正是描述動作風險的那個屬性。依第 1 章的定義，青鳥客服 v1 是 L3，寫入都要客服確認；之後小額退款移到 L4，500 元以下自動。這些規則寫成程式，就是一個以副作用等級為輸入的政策函式。

| 政策 | read | write | destructive |
|---|---|---|---|
| L3 是否要人核准 | 否 | 是 | 是 |
| L4 是否要人核准 | 否 | 否（事後稽核） | 邊界內否（例如 500 元以下），超出是 |
| harness 可否自動重試 | 可（有限次數） | 否，除非有 idempotency | 否，除非有 idempotency |
| 是否需要 idempotency key | 不需要 | 需要 | 必須 |
| 可否平行執行 | 可 | 同一資源上要序列化 | 序列化 |
| shadow／dry-run 模式 | 照常執行 | 不執行，記錄「將會做什麼」 | 不執行，記錄「將會做什麼」 |
| 稽核紀錄 | 可抽樣 | 全部 | 全部，含核准者 |

逐列看這張表。核准政策隨 autonomy 等級改變，但 read 永遠不需要核准，destructive 永遠有邊界。重試政策是 5.1 節事故的關鍵：read 可以由 harness 自動重試，寫入類只有在有 idempotency 時才能重試，而且這條規則要同時套用在「harness 自動重試」與「模型自己提出的重試」上。平行執行是第 24 章 runtime 的主題，這裡先記住唯讀才能自由平行。shadow 模式（第 36 章）是新版 agent 上線前跑真實流量但不產生副作用的做法，只有 tool 有分級，harness 才知道哪些呼叫要換成 dry-run。

分級要由誰來標？原則是**由 tool 的擁有者在定義時標註，由 harness 強制執行，並由審查流程把關**。不能從名稱推斷（`sync_inventory` 聽起來無害，實際上會覆寫庫存），也不能只寫在描述裡讓模型自律。一個實用的預設是「沒標就當 destructive」：新接進來、沒人審過的 tool，先以最嚴格的政策對待。有疑慮時往嚴格那邊標，例如寄出「退貨單已建立」的通知信，因為對外而且收不回，應該是 destructive，而不是 write。

```text
 refunds_create 的生命週期（加上 loom.tools 的 harness 與金流閘道一起實現）

   ┌──────────┐ 模型提出  ┌──────────────┐ 客服核准  ┌──────────┐
   │ proposed │──────────►│ pending      │──────────►│ approved │
   └──────────┘ 參數驗證  │ _approval    │           └────┬─────┘
                通過      └──────┬───────┘                │ 帶 idempotency key
                                 │ 客服拒絕               ▼ 呼叫金流
                                 ▼                  ┌───────────┐
                          ┌──────────┐              │ executing │
                          │ rejected │              └─────┬─────┘
                          └──────────┘    成功回應 ┌──────┼───────┐ 明確失敗
                                                   ▼      │       ▼
                                           ┌───────────┐  │  ┌────────┐
                                           │ succeeded │  │  │ failed │
                                           └───────────┘  │  └────────┘
                                                 ▲        │ 逾時
                                                 │        ▼
                                                 │  ┌─────────┐
                                                 └──│ unknown │ 用同一把 key 重試：
                                       閘道回傳     └─────────┘ 已扣款就回傳原結果，
                                       第一次的結果             不會扣第二次
```

這張狀態機把一筆退款從提議到結束的所有狀態畫出來。模型的 tool call 只是 `proposed`，參數驗證通過後進入 `pending_approval` 等客服；被拒絕就結束在 `rejected`，回填給模型的訊息要明說「不要改用其他工具繞過」。核准後帶著 idempotency key 呼叫金流，進入 `executing`。有三種結果：成功、明確失敗（例如卡片已註銷），以及最麻煩的 `unknown`（逾時）。設計差的系統沒有 `unknown` 這個狀態，只把它當失敗，於是重試就變成第二筆退款；設計好的系統把 `unknown` 當成一個需要「確認」的狀態，用同一把 key 重試，閘道若已扣款就回傳第一次的結果，狀態收斂到 `succeeded`。

另一個值得一提的模式是**兩段式 tool**：把 destructive 動作拆成 `prepare` 與 `commit`。例如 `refunds_prepare` 回傳退款金額、退回方式、預計到帳時間與一個短效的確認 token，客服或使用者看過之後，`refunds_commit` 只接受這個 token。好處是核准的對象是一份具體、不可竄改的「報價單」，而不是模型可能在核准後又改掉的參數；確認 token 本身也可以兼作 idempotency key。代價是多一個 tool 與一次往返，適合金額大或不可逆程度高的動作。

> [!note] 2026 現況：tool 的副作用標註
> 截至 2026 年 10 月，MCP 規格允許 server 為 tool 附上 annotations，例如 `readOnlyHint`、`destructiveHint`、`idempotentHint`、`openWorldHint`（是否與外部世界互動）等提示；規格明確把它們定位為提示，client 不應該在不信任 server 的情況下依賴它們做安全決策，確切欄位以規格為準。框架方面，依公開文件，OpenAI Agents SDK 的 tool 可設定 `needs_approval`，觸發時 run 會產生 interruption，核准或拒絕後再恢復；Mastra 等框架也提供 tool approval。這些機制提供了「要人核准」的掛鉤，但哪些 tool 屬於哪一級、在哪個 autonomy 等級要核准，仍然是你自己的政策。

## 5.8 Idempotency：讓重試不會變成重複退款

**idempotency**（冪等性）是指同一個操作執行一次和執行多次，結果相同。查詢天生是冪等的；「把訂單狀態設為已取消」也是冪等的，執行兩次結果一樣；但「退款 1,280 元」不是，執行兩次就是 2,560 元。**idempotency key**（冪等鍵）是讓非冪等操作變得可安全重試的標準做法：呼叫端為每一個「業務意圖」產生一把 key，隨請求送出；執行端記錄每把 key 的處理結果，同一把 key 第二次出現時直接回傳第一次的結果，不再執行。支付業界早已普遍採用，例如 Stripe 的 API 就以 `Idempotency-Key` header 實作，並在同一把 key 配上不同參數時回傳錯誤。

agent 讓這件事變得更重要，因為重試的來源變多了。傳統服務的重試只來自程式碼（網路重試、佇列重送）；agent 的重試還可能來自模型（看到逾時就再呼叫一次，而且參數的措辭可能稍有不同）、來自人（客服對第二張核准卡片按下核准）、來自 durable execution 的 replay（第 22 章：程式崩潰後從事件紀錄重跑）。這些重試對 harness 來說都是「新的 tool call」，有不同的 tool_call_id，所以不能靠 call id 去重。

```text
 harness（loom.tools）          refunds_create（tool）            金流閘道
   │ 模型提出 refunds_create(B-1077, 1280, 理由 A)                  │
   │ key = run-1 ＋ hash(refunds_create, order_id, amount)          │
   │ 客服核准（核准綁在 key 上）                                    │
   │── kwargs＋idempotency_key=K ──►│── refund(B-1077, 1280, K) ───►│
   │                                │                               │ 記錄 K → RF-0001
   │                                │                               │ 扣款成功
   │                                │      ✕ 回應在網路上遺失 ◄─────│
   │◄── 錯誤：結果未知，可能已成功；│                               │
   │    可用相同參數重試，不會重複  │                               │
   │                                                                │
   │ 模型重試 refunds_create(B-1077, 1280, 理由 B)                  │
   │ 推導出同一把 K → 已核准過，不再請客服核准                      │
   │── kwargs＋idempotency_key=K ──►│── refund(B-1077, 1280, K) ───►│
   │                                │                               │ K 已存在：不扣款
   │◄── RF-0001（replayed）─────────│◄── 回傳第一次的結果 ──────────│
```

這張時序圖是 5.1 節事故的修正版，有三個關鍵設計。第一，**key 由 harness 推導，不由模型產生**：harness 用「run id＋tool 名稱＋定義意圖的參數（訂單與金額）」算出 key，所以模型第二次呼叫時就算把理由從 A 改成 B，推導出的仍是同一把 K。如果讓模型自己填 key，它很可能每次產生新的隨機字串，保護就完全失效；所以 idempotency key 不放進 tool 的 schema，模型看不到也填不了。第二，**去重發生在真正執行副作用的那一端**：只在 harness 記錄「呼叫過了」不夠，因為逾時時 harness 根本不知道金流有沒有扣款；必須把 key 一路傳到閘道，由閘道在扣款的同一個交易裡記錄。第三，**核准綁在意圖上**：同一把 key 核准過一次，重試就不再產生第二張核准卡片，客服不會被迫在兩張一模一樣的卡片之間猜哪一張是重複的。

key 的範圍要想清楚。「run id＋意圖」代表同一次對話中，同一張訂單、同一個金額只會退一次；如果顧客真的要求分兩次各退 640 元，因為金額不同，key 就不同，可以正常執行。但如果同一次對話裡顧客真的要對同一張訂單退兩次 640 元（例如兩件同價商品分開退），就需要把品項也放進意圖欄位。key 的保存期限也要設定：太短，晚到的重試會被當成新請求；太長，儲存成本上升，也可能擋住隔天合法的新請求。

下面的程式把執行端的 idempotency store 單獨拿出來，示範三件事：意圖相同但措辭不同的重試會 replay、讓模型自產 key 會失效，以及同一把 key 配上不同參數會被拒絕。

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


class IdempotencyConflict(Exception):
    """同一把 key 配上不同的參數：多半是程式錯誤，絕不能默默執行。"""


@dataclass
class IdempotencyStore:
    """key → (參數指紋, 結果)。真實系統放在和業務資料同一個交易能寫入的資料庫，並設保存期限。"""
    ttl_seconds: int = 24 * 3600
    records: dict[str, tuple[str, dict, float]] = field(default_factory=dict)

    def run(self, key: str, args: dict, now: float, effect) -> tuple[dict, bool]:
        fingerprint = hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()[:12]
        if key in self.records:
            fp, result, at = self.records[key]
            if now - at < self.ttl_seconds:
                if fp != fingerprint:
                    raise IdempotencyConflict(f"key {key} 已用於不同參數（{fp} ≠ {fingerprint}）")
                return result, True                      # replay：回傳第一次的結果，不再執行
        result = effect(**args)                          # 只有第一次真的動到外部世界
        self.records[key] = (fingerprint, result, now)
        return result, False


def intent_key(run_id: str, tool: str, args: dict, fields: tuple[str, ...]) -> str:
    """由 harness 依「業務意圖」推導 key：同一次 run、同一個動作、同一張訂單與金額 → 同一把 key。"""
    intent = [tool, {f: args[f] for f in fields}]
    return f"{run_id}:{tool}:" + hashlib.sha256(json.dumps(intent, sort_keys=True).encode()).hexdigest()[:10]


ledger: list[dict] = []        # 金流端真正發生的退款

def refund(order_id: str, amount: int, reason: str = "") -> dict:
    ledger.append({"order_id": order_id, "amount": amount})
    return {"refund_id": f"RF-{len(ledger):04d}", "order_id": order_id, "amount": amount}


store = IdempotencyStore()
fields = ("order_id", "amount")
a1 = {"order_id": "B-1077", "amount": 1280, "reason": "尺寸不合"}
a2 = {"order_id": "B-1077", "amount": 1280, "reason": "尺寸不合，顧客再次確認"}   # 模型重試時改了措辭

# 1) 模型重試：reason 措辭不同，但業務意圖相同 → 同一把 key → replay
k1, k2 = intent_key("run-42", "refunds_create", a1, fields), intent_key("run-42", "refunds_create", a2, fields)
r1, replay1 = store.run(k1, {f: a1[f] for f in fields}, now=0, effect=refund)
r2, replay2 = store.run(k2, {f: a2[f] for f in fields}, now=30, effect=refund)
print("第一次  ", r1, "replay" if replay1 else "executed")
print("重試    ", r2, "replay" if replay2 else "executed", "| 同一把 key：", k1 == k2)

# 2) 如果讓模型自己產生 key：每次呼叫都是新 key，保護完全失效
for i, model_key in enumerate(["k-7f3a", "k-91bd"]):
    store.run(model_key, {f: a1[f] for f in fields}, now=60 + i, effect=refund)
print("模型自產 key 後的金流紀錄：", len(ledger), "筆")

# 3) 上游程式重用了同一把 key、卻換了金額：拒絕，而不是執行或 replay
try:
    store.run(k1, {"order_id": "B-1077", "amount": 999}, now=90, effect=refund)
except IdempotencyConflict as exc:
    print("衝突    ", exc)

assert k1 == k2 and replay2 and r1 == r2
assert len(ledger) == 3          # 1 筆正確退款 + 2 筆因為模型自產 key 而重複
```

```text
第一次   {'refund_id': 'RF-0001', 'order_id': 'B-1077', 'amount': 1280} executed
重試     {'refund_id': 'RF-0001', 'order_id': 'B-1077', 'amount': 1280} replay | 同一把 key： True
模型自產 key 後的金流紀錄： 3 筆
衝突     key run-42:refunds_create:5fa056c8a9 已用於不同參數（55ca21136a4d ≠ 5d6d8c43a2eb）
```

第一行是第一次退款，真的執行了（executed），金流紀錄多一筆 RF-0001。第二行是模型的重試：理由的措辭變了，但 `intent_key` 只看訂單與金額，推導出同一把 key，所以 store 回傳第一次的結果並標示 replay，金流沒有第二筆。第三行示範反例：如果 key 交給模型產生，兩次呼叫各帶一把隨機的新 key，store 認不出它們是同一件事，金流紀錄變成 3 筆（1 筆正確、2 筆重複）。第四行是另一種錯誤：上游程式重用了一把已經用過的 key，卻換了金額，store 比對參數指紋不同，直接拋出 `IdempotencyConflict`，而不是默默 replay 舊結果或執行新的退款，因為兩種做法都會讓帳對不起來。

實務上還有兩個細節。其一，能設計成天生冪等的操作，就不要依賴 key：「把退貨單狀態設為已取消」比「切換退貨單狀態」安全，「設定庫存為 12」比「庫存加 3」安全，宣告式（declarative）的寫入在重試時天然正確。其二，下游系統不支援 idempotency key 時，tool 可以在執行前先查詢「這個意圖是否已經完成」（例如查詢該訂單是否已有相同金額的退款），這叫 check-then-act；它在並行時有競爭條件，只能當成退而求其次的做法，並要搭配鎖或唯一約束。

## 5.9 評估 tool 好壞的方法

前面每一節都在說「這樣設計比較好」，但「比較好」必須可以量測，否則 tool 的修改就只是品味之爭。評估 tool 有三個層次，成本由低到高：靜態檢查（5.3 節的 lint）、固定任務集上的端到端評估，以及閱讀 transcript（完整的對話與 tool 呼叫紀錄）找出失敗的原因。Anthropic 的〈Writing effective tools for agents〉描述了一個以評估驅動的流程，下圖是它的骨架。

```text
 ┌─────────────┐   ┌──────────────────┐   ┌───────────────┐   ┌───────────────────┐
 │ 1. 原型     │──►│ 2. 建立任務集    │──►│ 3. 用簡單的   │──►│ 4. 收集指標       │
 │ tools 先能用│   │ 真實、多步、     │   │ loop 執行     │   │ 成功率、步數、    │
 └─────────────┘   │ 結果可驗證       │   │ （loom）      │   │ tokens、錯誤率    │
        ▲          └──────────────────┘   └───────────────┘   └─────────┬─────────┘
        │                                                               │
 ┌──────┴────────────────┐   ┌─────────────────────┐   ┌────────────────▼──────────┐
 │ 7. 用保留集（held-out）│◄──│ 6. 修改 tool        │◄──│ 5. 讀 transcript          │
 │ 確認沒有過度擬合      │   │ 名稱、描述、粒度、  │   │ 選錯哪個 tool？哪個參數？ │
 │ 通過才上線            │   │ 回傳、錯誤訊息      │   │ 哪則回傳讓它卡住？        │
 └───────────────────────┘   └─────────────────────┘   └───────────────────────────┘
```

這個迴圈的第 2 步最花心力，也最重要。任務要來自真實情境（試用期的客服紀錄是最好的來源），而且要多步、有可驗證的結果：「B-1077 退款」的驗證不是看 agent 說了「已退款」，而是檢查金流紀錄裡恰好有一筆 1,280 元。第 4 步的指標不只看成功率，因為兩組 tools 可能都答對，但一組要多花三倍 token。第 5 步讀 transcript 是找出「為什麼」的唯一方法：指標告訴你 T2 很貴，transcript 告訴你是因為清單裡沒有品名。第 7 步的保留集防止你為了少數任務過度調整描述，例如在描述裡寫死「藍色外套請搜尋外套」。

| 指標 | 怎麼算 | 它揭露的 tool 問題 |
|---|---|---|
| 任務成功率 | 以環境狀態或答案檢查判定，不信 agent 自述 | 資訊不足、粒度錯誤、錯誤訊息無法引導 |
| 每題模型呼叫數（步數） | trajectory 中的模型呼叫次數 | CRUD 級粒度、名稱相近導致選錯 |
| 每題 tokens | input＋output 加總 | 回傳過大、tool 定義過長、步數過多 |
| 各 tool 的錯誤率 | 回填 is_error 的比例 | 參數歧義、缺少格式說明 |
| 選錯 tool 率 | 呼叫後立刻改用另一個 tool 的比例 | 功能重疊、描述沒寫界線 |
| 重複呼叫率 | 相同 (name, args) 重複次數 | 回傳沒說清楚「狀態未更新」 |
| 副作用正確性 | 金流、退貨單等外部狀態是否符合預期 | 缺少 idempotency、讀寫混在一起 |
| 人工核准次數 | 每題觸發的核准卡片數 | 核准沒有綁在意圖上、重試產生重複卡片 |

最後要誠實地說明評估工具的限制。本章的「動手做」用 ScriptedModel 跑兩組 tools，劇本是人寫的，它代表「一個合理的模型面對這些回傳會怎麼做」的假設，而不是真實模型的行為。它能可靠量測的是在這個假設下，tool 設計對步數、token、副作用與錯誤處理的機械性影響，並且能把事故（重複退款）一字不差地重現、用 assert 鎖住。它不能回答「真實模型讀了這段描述會不會選對」，那需要用真實模型在任務集上重複多次執行，並用第 27 章的統計方法比較；兩者互補，前者是單元測試，後者是實驗。

## 5.10 動手做：重構青鳥 tools，量化成功率、步數與 token

這一節把本章的設計原則寫成程式，並讓兩組 tools 在同一組任務上比賽。程式分成四塊。第一塊是 `loom.tools` 模組：沿用第 4 章 `loom` v0.1 的 loop 與 dispatch（參數驗證、錯誤回填、重複偵測、步數上限），新增三樣東西：`Tool` 多了 `effect`（副作用等級）與 `intent_fields`（哪些參數定義同一個業務意圖）；`needs_approval()` 依副作用等級與 autonomy 等級決定要不要核准；`_dispatch()` 在執行前推導 idempotency key 注入 tool，並把核准綁在 key 上。為了篇幅，這段程式省略了 v0.1 的 token 預算、max_tokens 檢查、結果截斷與 trace，它們不影響這組任務的結果；完整版就是 v0.1 加上本章的 `loom.tools`。

第二塊是青鳥的假後端 `Shop`，其中的金流閘道支援 idempotency key，並且被設定成「第一次退款扣款成功、但回應逾時」，重現 5.1 節的事故。第三塊是兩組 tools：`bad_tools` 是 ERP endpoint 的一對一包裝（8 個 tool、原始欄位、UUID、`ERR_4041` 這類錯誤碼、退款不帶 key），`good_tools` 依本章原則重新設計（4 個任務級 tool、人類可讀摘要、可行動的錯誤、副作用分級與 idempotency）。第四塊是四個任務，每個任務包含使用者輸入、兩套劇本，以及一個檢查結果的 grader；grader 檢查的是答案內容或金流紀錄，不是 agent 說了什麼。

劇本是本實驗最需要誠實看待的部分。每一步都模擬「一個合理的模型看到這則回傳會怎麼做」：設計差的劇本會先選錯名稱相近的 `fetch_order`、會因為看不懂 `ERR_4041` 而以為系統故障、會在 `ERR_TIMEOUT` 之後再試一次；部分步驟是函式，真的從上一則 tool 回傳中讀出 UUID 或判斷錯誤內容再決定下一步。你可以不同意某一步的假設，直接改劇本重跑；數字會變，但量測方法不變。

```python
from __future__ import annotations

import hashlib
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


class MeteredModel(ScriptedModel):
    """用「(tool 定義 + messages) 的字元數 ÷ 2」粗估 input tokens；真實 API 會在 usage 直接回傳。"""

    def complete(self, messages, tools=None, system=""):
        resp = super().complete(messages, tools, system)
        resp.usage = {"input_tokens": len(json.dumps([tools, messages], ensure_ascii=False)) // 2,
                      "output_tokens": 40}
        return resp


# ─────────────── loom.tools：在 v0.1 的 dispatch 上加副作用分級與 idempotency ───────────────
@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable[..., Any]
    effect: str = "read"                          # read｜write｜destructive
    intent_fields: tuple[str, ...] = ()           # 哪些參數定義「同一個業務意圖」；非空就會注入 idempotency key

    def schema(self) -> dict[str, Any]:           # 注意：idempotency_key 不在 schema 裡，模型看不到也填不了
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


def needs_approval(tool: Tool, args: dict, autonomy: str) -> bool:
    if tool.effect == "read":
        return False
    if autonomy == "L3":                          # 客服 agent v1：每個寫入都要客服確認
        return True
    return tool.effect == "destructive" and args.get("amount", 0) > 500   # L4：500 元以下退款自動


class Agent:
    def __init__(self, model, tools: list[Tool], approver: Callable[[str, dict], bool],
                 autonomy: str = "L3", run_id: str = "run-1", max_steps: int = 10, max_repeats: int = 2):
        self.model, self.tools, self.approver = model, {t.name: t for t in tools}, approver
        self.autonomy, self.run_id, self.max_steps, self.max_repeats = autonomy, run_id, max_steps, max_repeats
        self.approved: set[str] = set()           # 核准綁在「意圖」上，不是綁在每一次呼叫上
        self.stats = Counter()

    def run(self, user_input: str) -> tuple[str, str, list[dict]]:
        messages: list[dict] = [{"role": "user", "content": user_input}]
        seen: Counter[str] = Counter()
        for _ in range(self.max_steps):
            resp = self.model.complete(messages, tools=[t.schema() for t in self.tools.values()])
            self.stats["model_calls"] += 1
            self.stats["tokens"] += sum(resp.usage.values())
            messages.append({"role": "assistant", "content": resp.text,
                             "tool_calls": [vars(tc) for tc in resp.tool_calls]})
            if not resp.tool_calls:
                return "done", resp.text, messages
            for tc in resp.tool_calls:
                key = tc.name + json.dumps(tc.args, sort_keys=True, ensure_ascii=False)
                seen[key] += 1
                if seen[key] > self.max_repeats:
                    is_error, content = True, "相同呼叫已重複多次，結果不會改變；請換做法或回覆使用者。"
                else:
                    is_error, content = self._dispatch(tc)
                self.stats["tool_calls"] += 1
                self.stats["tool_errors"] += is_error
                messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name,
                                 "content": content, "is_error": is_error})
        return "max_steps", "步驟用完了，轉給真人同事。", messages

    def _dispatch(self, tc: ToolCall) -> tuple[bool, str]:
        tool = self.tools.get(tc.name)
        if tool is None:
            return True, f"沒有名為 {tc.name} 的工具。可用的工具：{', '.join(self.tools)}。"
        props = tool.parameters.get("properties", {})
        missing = [p for p in tool.parameters.get("required", []) if p not in tc.args]
        unknown = [a for a in tc.args if a not in props]
        if missing or unknown:
            return True, f"參數錯誤：缺少 {missing}，不認得 {unknown}。正確參數：{list(props)}。"
        kwargs = dict(tc.args)
        intent = None
        if tool.intent_fields:                    # key 由 harness 依業務意圖推導，不讓模型自己產生
            body = json.dumps([tool.name, {f: tc.args.get(f) for f in tool.intent_fields}], sort_keys=True)
            intent = f"{self.run_id}:{hashlib.sha256(body.encode()).hexdigest()[:10]}"
            kwargs["idempotency_key"] = intent
        if needs_approval(tool, tc.args, self.autonomy):
            if intent is None or intent not in self.approved:
                self.stats["approvals"] += 1
                if not self.approver(tool.name, tc.args):
                    return True, f"客服未核准 {tool.name}。請向使用者說明需要人工處理，不要改用其他工具繞過。"
                if intent:
                    self.approved.add(intent)
        try:
            result = tool.fn(**kwargs)
        except Exception as exc:                  # tool 的例外是觀察；訊息品質由 tool 自己負責
            return True, str(exc)
        return False, result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
# ─────────────────────────────── loom.tools 結束 ───────────────────────────────


class Shop:
    """青鳥的假後端。金流閘道支援 idempotency key；第一次退款會「扣款成功但回應逾時」。"""

    def __init__(self):
        self.orders = {
            "B-1009": dict(uuid="5d0e-1009", email="amy@example.com", status="delivered", day="2026-07-30",
                           total=390, items=[("sku-77a1", "帆布托特包")], tracking="TC-80112"),
            "B-1033": dict(uuid="5d0e-1033", email="amy@example.com", status="delivered", day="2026-09-15",
                           total=1680, items=[("sku-31c9", "藍色連帽外套")], tracking="TC-87730"),
            "B-1042": dict(uuid="5d0e-1042", email="amy@example.com", status="shipped", day="2026-09-18",
                           total=590, items=[("sku-52f0", "棉質T恤")], tracking="TC-88301"),
            "B-1077": dict(uuid="5d0e-1077", email="amy@example.com", status="pending", day="2026-09-19",
                           total=1280, items=[("sku-90de", "黑色寬褲")], tracking=None),
        }
        self.ledger: list[dict] = []              # 金流端真正發生的退款
        self.gateway_keys: dict[str, dict] = {}
        self.timeout_once = True

    def gateway_refund(self, order_id: str, amount: int, key: str | None = None) -> dict:
        if key and key in self.gateway_keys:      # 同一把 key：回傳第一次的結果，不再扣款
            return {**self.gateway_keys[key], "replayed": True}
        result = {"refund_id": f"RF-{len(self.ledger) + 1:04d}", "order_id": order_id, "amount": amount}
        self.ledger.append(result)
        if key:
            self.gateway_keys[key] = result
        if self.timeout_once:                     # 扣款已完成，但回應在路上遺失：呼叫端無從得知結果
            self.timeout_once = False
            raise TimeoutError("gateway timeout")
        return result


def obj(required: list[str], **props: dict) -> dict:
    return {"type": "object", "properties": props, "required": required}


S = {"type": "string"}


def bad_tools(shop: Shop) -> list[Tool]:
    """把 ERP 的 endpoint 一對一包成 tool：原始欄位、UUID、不透明錯誤碼、沒有 idempotency。"""
    def find(order_id):
        if order_id not in shop.orders:
            raise KeyError("ERR_4041")
        return shop.orders[order_id]

    def get_order(id):
        o = find(id)
        return {"id": id, "uuid": o["uuid"], "customer_uuid": "c-88f2-0a1b", "state": o["status"].upper(),
                "created": o["day"] + "T08:12:44Z", "shipment_ref": f"shp-{o['tracking']}", "amount": o["total"],
                "currency": "TWD", "payment": {"gw": "PGX", "txn": "tx-" + o["uuid"], "captured": True},
                "flags": {"vip": False, "fraud_score": 0.02, "legacy_sync": True}}

    def fetch_order(id):                          # 舊版 endpoint：和 get_order 名稱相近、內容更少
        return {"id": id, "st": "S" + str(len(find(id)["status"]))}

    def get_shipment(ref):
        return {"ref": ref, "events": [{"ts": f"2026-09-{d}T0{h}:00Z", "code": c, "hub": "TXG-03"}
                                       for d, h, c in [(18, 9, "PU"), (18, 11, "AR"), (19, 2, "DP"), (19, 6, "AR")]]}

    def get_customer(email):
        return {"customer_uuid": "c-88f2-0a1b", "email": email, "tier": "T2"}

    def list_orders(customer_uuid):
        return [{"uuid": o["uuid"], "state": o["status"].upper(), "created": o["day"]} for o in shop.orders.values()]

    def get_order_items(order_uuid):
        o = next(o for o in shop.orders.values() if o["uuid"] == order_uuid)
        return [{"sku_uuid": s, "title": n, "qty": 1} for s, n in o["items"]]

    def get_refund_policy():
        return "退貨政策：商品於到貨日起七日內得申請退貨……（以下共 1,800 字的完整條款）" + "條款內容" * 120

    def create_refund(order_uuid, amount):
        order_id = next(k for k, o in shop.orders.items() if o["uuid"] == order_uuid)
        try:
            return shop.gateway_refund(order_id, amount)          # 沒有傳 idempotency key
        except TimeoutError:
            raise RuntimeError("ERR_TIMEOUT") from None

    return [
        Tool("get_order", "取得訂單", obj(["id"], id=S), get_order),
        Tool("fetch_order", "訂單資料", obj(["id"], id=S), fetch_order),
        Tool("get_shipment", "取得物流", obj(["ref"], ref=S), get_shipment),
        Tool("get_customer", "取得顧客", obj(["email"], email=S), get_customer),
        Tool("list_orders", "列出訂單", obj(["customer_uuid"], customer_uuid=S), list_orders),
        Tool("get_order_items", "訂單品項", obj(["order_uuid"], order_uuid=S), get_order_items),
        Tool("get_refund_policy", "退款政策", obj([]), get_refund_policy),
        Tool("create_refund", "建立退款", obj(["order_uuid", "amount"], order_uuid=S, amount={"type": "integer"}),
             create_refund, effect="destructive"),
    ]


def good_tools(shop: Shop) -> list[Tool]:
    """依任務設計：workflow 級查詢、人類可讀欄位、可行動的錯誤、副作用分級與 idempotency。"""
    TODAY, LABEL = "2026-09-20", {"pending": "未出貨", "shipped": "運送中", "delivered": "已送達"}

    def overview(o_id, o):
        deadline = f"2026-09-{int(o['day'][-2:]) + 7:02d}" if o["status"] == "delivered" else None
        refund = ("未出貨，可直接退款" if o["status"] == "pending" else "運送中，送達後可申請退貨" if
                  o["status"] == "shipped" else f"可退貨，期限 {deadline}" if deadline and deadline >= TODAY
                  else "已超過七天鑑賞期，無法退貨")
        out = {"order_id": o_id, "status": LABEL[o["status"]], "placed": o["day"], "total": o["total"],
               "items": [n for _, n in o["items"]], "refund": refund}
        if o["status"] == "shipped":
            out["shipment"] = "黑貓 TC-88301：已抵達台中轉運中心，預計明天送達"
        return out

    def orders_get_overview(order_id):
        if order_id not in shop.orders:
            raise LookupError(f"找不到訂單 {order_id}。編號格式是 B- 加四位數字，英文字母 O 可能是數字 0 的誤植；"
                           "請向使用者確認編號，不要自行猜測。")
        return overview(order_id, shop.orders[order_id])

    def orders_search(customer_email, keyword=""):
        hits = [overview(k, o) for k, o in shop.orders.items()
                if o["email"] == customer_email and keyword in "".join(n for _, n in o["items"])]
        return {"total_matches": len(hits), "orders": hits[:5]}

    def refunds_create(order_id, amount, reason, idempotency_key):
        o = shop.orders.get(order_id)
        if o is None or o["status"] != "pending":
            raise ValueError(f"{order_id} 不是未出貨訂單，不能直接退款；已出貨或已送達請改用 returns_create。")
        if amount > o["total"]:
            raise ValueError(f"退款金額 {amount} 超過訂單金額 {o['total']}。")
        try:
            return shop.gateway_refund(order_id, amount, key=idempotency_key)
        except TimeoutError:
            raise TimeoutError("金流回應逾時，退款結果未知（可能已成功）。請用相同的 order_id 與 amount 重試："
                               "系統會以 idempotency key 確認，不會重複退款。") from None

    def returns_create(order_id, reason, idempotency_key):
        return {"return_id": "R-7781", "order_id": order_id, "pickup": "後天"}

    order_id = {"type": "string", "description": "訂單編號，格式 B- 加四位數字，例如 B-1042"}
    return [
        Tool("orders_get_overview", "用訂單編號一次取得訂單狀態、品項、物流進度與退款資格。使用者提到具體訂單編號時使用；"
             "只有 email 時改用 orders_search。回傳人類可讀的摘要。", obj(["order_id"], order_id=order_id),
             orders_get_overview),
        Tool("orders_search", "依顧客 email 與品名關鍵字搜尋訂單，回傳每張訂單的摘要（同 orders_get_overview）與總筆數。"
             "使用者沒有給訂單編號時使用。", obj(["customer_email"], customer_email={"type": "string",
             "description": "顧客 email"}, keyword={"type": "string", "description": "品名關鍵字，例如 外套"}),
             orders_search),
        Tool("refunds_create", "【不可逆】未出貨訂單直接退款到原付款方式。需客服核准。已出貨請改用 returns_create。",
             obj(["order_id", "amount", "reason"], order_id=order_id, amount={"type": "integer"},
                 reason={"type": "string"}), refunds_create, effect="destructive", intent_fields=("order_id", "amount")),
        Tool("returns_create", "已出貨或已送達的訂單建立退貨單（可取消）。需客服核准。",
             obj(["order_id", "reason"], order_id=order_id, reason={"type": "string"}),
             returns_create, effect="write", intent_fields=("order_id",)),
    ]


# ─────────── 同一組四個任務：每個任務 = 使用者輸入 + 兩套劇本 + outcome 檢查 ───────────
def last(msgs: list[dict]) -> str:
    return msgs[-1]["content"]


def field_of(name: str) -> Callable[[list[dict]], str]:
    return lambda msgs: json.loads(last(msgs))[name]


TASKS = [
    ("T1 查貨態", "B-1042 到哪了？",
     [call("fetch_order", id="B-1042"),                                   # 名稱相近，先選錯
      call("get_order", id="B-1042"),
      lambda m: call("get_shipment", ref=field_of("shipment_ref")(m)),
      say("B-1042 已出貨，最後一筆紀錄是 TXG-03 的 AR 事件。")],          # 看不懂代碼，只能照抄
     [call("orders_get_overview", order_id="B-1042"),
      say("B-1042 運送中，已抵達台中轉運中心，預計明天送達。")],
     lambda out, shop: "明天" in out),
    ("T2 找訂單", "我是 amy@example.com，上個月買的藍色外套還能退嗎？",
     [call("get_customer", email="amy@example.com"),
      lambda m: call("list_orders", customer_uuid=field_of("customer_uuid")(m)),
      call("get_order_items", "c3", order_uuid="5d0e-1009"),             # 沒有品名，只能逐張打開看
      call("get_order_items", "c4", order_uuid="5d0e-1033"),
      call("get_refund_policy"),
      say("您的藍色連帽外套（B-1033）9/15 到貨，七天內可退，期限 9/22。")],
     [call("orders_search", customer_email="amy@example.com", keyword="外套"),
      say("您的藍色連帽外套（B-1033）可以退貨，期限 2026-09-22。")],
     lambda out, shop: "B-1033" in out and "22" in out),
    ("T3 編號打錯", "B-1O42 怎麼還沒到？",
     [call("get_order", id="B-1O42"),
      lambda m: call("fetch_order", id="B-1O42") if last(m) == "'ERR_4041'" else say("?"),
      say("系統暫時查不到您的訂單，請稍後再試。")],                       # 不透明錯誤碼：模型以為是系統故障
     [call("orders_get_overview", order_id="B-1O42"),
      lambda m: say("查不到 B-1O42，請問是 B-1042 嗎？麻煩幫我確認編號。") if "確認" in last(m) else say("?")],
     lambda out, shop: "確認" in out),
    ("T4 退款逾時", "B-1077 還沒出貨，我不要了，幫我退 1280 元",
     [call("get_order", id="B-1077"),
      lambda m: call("create_refund", order_uuid=field_of("uuid")(m), amount=1280),
      call("create_refund", "c3", order_uuid="5d0e-1077", amount=1280),   # ERR_TIMEOUT：模型只能再試一次
      say("已為您退款 1280 元。")],
     [call("refunds_create", order_id="B-1077", amount=1280, reason="顧客取消"),
      call("refunds_create", "c2", order_id="B-1077", amount=1280, reason="顧客取消（重試）"),
      say("已退款 1280 元（RF-0001），3–5 個工作天退回原付款方式。")],
     lambda out, shop: len(shop.ledger) == 1),
]

report = {}
for label, make_tools, idx in (("設計差（8 個 CRUD tool）", bad_tools, 2), ("設計好（4 個任務 tool）", good_tools, 3)):
    total = Counter()
    for name, user, *scripts, grade in TASKS:
        shop = Shop()
        agent = Agent(MeteredModel(scripts[idx - 2]), make_tools(shop), approver=lambda tool, args: True)
        status, out, _ = agent.run(user)
        ok = status == "done" and grade(out, shop)
        total.update(agent.stats)
        total["success"] += ok
        print(f"{label[:3]} {name:<7} {'PASS' if ok else 'FAIL'}  model={agent.stats['model_calls']} "
              f"tools={agent.stats['tool_calls']} err={agent.stats['tool_errors']} "
              f"approvals={agent.stats['approvals']} tokens={agent.stats['tokens']:>5} refunds={len(shop.ledger)}")
    report[label] = total

print()
for label, t in report.items():
    print(f"{label}：成功 {t['success']}/4｜模型呼叫 {t['model_calls']}｜tool 呼叫 {t['tool_calls']}"
          f"｜tool 錯誤 {t['tool_errors']}｜客服核准 {t['approvals']}｜tokens {t['tokens']}")
for label, make_tools in (("設計差", bad_tools), ("設計好", good_tools)):
    defs = [t.schema() for t in make_tools(Shop())]
    print(f"{label}的 tool 定義本身約 {len(json.dumps(defs, ensure_ascii=False)) // 2} tokens（每次呼叫都要送）")

bad, good = report.values()
assert good["success"] == 4 and bad["success"] == 1
assert good["tokens"] < bad["tokens"] and good["model_calls"] < bad["model_calls"]
small = Tool("refunds_create", "", obj([]), lambda **k: None, effect="destructive")
assert not needs_approval(small, {"amount": 300}, "L4") and needs_approval(small, {"amount": 1280}, "L4")
```

```text
設計差 T1 查貨態  FAIL  model=4 tools=3 err=0 approvals=0 tokens= 3968 refunds=0
設計差 T2 找訂單  PASS  model=6 tools=5 err=0 approvals=0 tokens= 7168 refunds=0
設計差 T3 編號打錯 FAIL  model=3 tools=2 err=2 approvals=0 tokens= 2383 refunds=0
設計差 T4 退款逾時 FAIL  model=4 tools=3 err=1 approvals=2 tokens= 4050 refunds=2
設計好 T1 查貨態  PASS  model=2 tools=1 err=0 approvals=0 tokens= 1548 refunds=0
設計好 T2 找訂單  PASS  model=2 tools=1 err=0 approvals=0 tokens= 1579 refunds=0
設計好 T3 編號打錯 PASS  model=2 tools=1 err=1 approvals=0 tokens= 1486 refunds=0
設計好 T4 退款逾時 PASS  model=3 tools=2 err=1 approvals=1 tokens= 2541 refunds=1

設計差（8 個 CRUD tool）：成功 1/4｜模型呼叫 17｜tool 呼叫 13｜tool 錯誤 3｜客服核准 2｜tokens 17569
設計好（4 個任務 tool）：成功 4/4｜模型呼叫 9｜tool 呼叫 5｜tool 錯誤 2｜客服核准 1｜tokens 7154
設計差的 tool 定義本身約 619 tokens（每次呼叫都要送）
設計好的 tool 定義本身約 603 tokens（每次呼叫都要送）
```

先看前四行，設計差的 tools。**T1 查貨態**失敗：模型先選了名稱相近的 `fetch_order`，拿到一個沒有物流資訊的舊格式；改用 `get_order` 後再用 `shipment_ref` 查物流，回傳只有事件代碼，沒有預計送達日，於是答案只能照抄「TXG-03 的 AR 事件」，grader 要求答案提到送達時間，判定失敗。這不是模型笨，而是資訊根本不在回傳裡。**T2 找訂單**成功了，但花了 6 次模型呼叫、5 次 tool、7,168 tokens，是設計好版本的 4.5 倍，原因就是 5.4 節那張圖的左半邊。**T3 編號打錯**失敗：兩次 `ERR_4041` 之後，模型回答「系統暫時查不到，請稍後再試」，沒有請使用者確認編號。**T4 退款逾時**失敗：`approvals=2` 表示客服被要求核准了兩次，`refunds=2` 表示金流真的退了兩筆，5.1 節的事故原樣重現。

接著四行是設計好的 tools，四題全部通過。T1 與 T2 都只用 1 次 tool、2 次模型呼叫，因為 workflow 級的 `orders_get_overview` 與 `orders_search` 直接回傳了狀態、物流進度與退款資格。T3 的 `err=1` 是預期中的錯誤：tool 回傳可行動的訊息「請向使用者確認編號，不要自行猜測」，劇本的函式讀到「確認」才請使用者確認，這模擬了模型依錯誤訊息修正行為。T4 也有 1 次錯誤，就是那次逾時；模型用相同的訂單與金額重試，雖然理由改成「顧客取消（重試）」，harness 推導出同一把 key，`approvals=1` 表示沒有產生第二張核准卡片，閘道回傳第一次的結果，`refunds=1`。

彙總的兩行是本章要的數字，整理成下表：

| 指標 | 設計差（8 個 CRUD tool） | 設計好（4 個任務 tool） | 差異的來源 |
|---|---|---|---|
| 任務成功率 | 1/4 | 4/4 | 回傳缺資訊、錯誤碼不可行動、沒有 idempotency |
| 模型呼叫（4 題合計） | 17 | 9 | 選錯同義 tool、CRUD 級需要串接 |
| tool 呼叫 | 13 | 5 | workflow 級合併了連鎖讀取 |
| tool 錯誤 | 3 | 2 | 兩邊都有逾時；好的版本把錯誤變成指路 |
| 客服核准次數 | 2 | 1 | 核准綁在意圖（key）上 |
| tokens | 17,569 | 7,154 | 步數減半、回傳精簡，累計成本約降六成 |
| tool 定義本身 | 約 619 tokens | 約 603 tokens | 4 個寫得完整的 tool ≈ 8 個寫得簡陋的 tool |

最後一列值得多看一眼。設計好的 tools 描述長很多，但因為數量減半，定義的總長度和 8 個簡陋的 tool 差不多。換句話說，好的描述不一定更貴；真正讓 token 差了 2.5 倍的，是步數與回傳大小。最後的 assert 鎖住四件事：設計好的版本四題全過、設計差的只過一題、設計好的 tokens 與模型呼叫數都比較少，以及政策函式在 L4 下對 300 元退款不要求核准、對 1,280 元要求核准。

| 版本 | 新增的行為 | 修掉的事故或風險 | 對應小節 |
|---|---|---|---|
| v0.1（第 4 章） | loop、dispatch、錯誤回填、停止條件 | 例外炸穿、無限迴圈、半截 tool call | 第 4 章 |
| `loom.tools` 模組（本章） | `effect`、`intent_fields`、`needs_approval()`、harness 推導 idempotency key、核准綁意圖 | 重複退款、重複核准、寫入沒有統一政策 | 5.7、5.8 |
| tools 重構（本章） | 任務級粒度、可讀回傳、可行動錯誤、namespacing | 選錯 tool、照抄代碼、把錯誤當故障、步數與 token 過高 | 5.3–5.6 |

`loom.tools` 目前仍然刻意沒做的事：核准是同步的 callback，真實系統的客服可能五分鐘後才按，需要第 21 章的 interrupt／resume 與第 22 章的 durable execution；`approved` 集合與 idempotency 紀錄都在記憶體中，process 重啟就消失；write 與 destructive 在 L3 下的處理相同，尚未實作 shadow 模式的 dry-run。這些會在後面的章節補上，但介面已經定下來了：tool 自己宣告等級與意圖欄位，政策由 harness 統一執行。

## 5.11 實務應用

本章的原則放在不同產品裡，重點會不一樣。以下四個情境說明同一套 ACI 思路在不同領域要調整什麼。

**情境一：電商客服 agent（青鳥的主線）**。客服任務的種類有限、路徑相對固定，所以偏向 workflow 級的讀取 tool，把「訂單＋物流＋退款資格」這類固定串接收進 tool，日期與資格由程式計算。寫入 tool 依風險拆開（退款 vs 退貨單），每個都標副作用等級並帶 idempotency key。錯誤訊息要同時讓模型知道下一步、讓模型能安全地轉述給顧客。公開的客服 benchmark τ-bench 系列正是以這種情境建模：每個領域包含一份政策文件、一組 tools 與一個模擬使用者，評估 agent 是否在遵守政策的前提下把資料庫改成正確的狀態，這和 5.9 節「以環境狀態判定成功」的做法一致，第 28 章會詳談。

**情境二：coding agent 的檔案與搜尋 tools**。SWE-agent 論文是 ACI 這個概念的原點，它為 agent 設計的介面有幾個值得借鏡的特點：檔案檢視器一次只顯示一段固定行數並附行號，而不是把整個檔案倒進 context；搜尋指令回傳精簡的結果並限制數量；編輯指令會先做語法檢查，有語法錯誤就拒絕套用並說明原因。這三點分別對應本章的回傳截斷、分頁與可行動錯誤。主流 coding agent 的編輯 tool 多半採用局部替換（舊字串換成新字串）或 patch 的形式，而不是重寫整個檔案，部分 tool 也要求絕對路徑；Anthropic 提供的 text editor tool 也以 `view`、`str_replace` 等指令操作檔案。這類 tool 大多是 write 等級，但因為在 sandbox 與版本控制之下（第 17 章），它們實際上是可回復的；真正 destructive 的是 `git push`、部署與對外的網路呼叫。

**情境三：金融與支付後台的營運 agent**。這是 idempotency 與兩段式 tool 最不可妥協的地方。退款、轉帳、調整額度都是 destructive，建議做成 prepare／commit 兩段：prepare 回傳金額、手續費、到帳時間與確認 token，人核准的是這份不可竄改的內容，commit 只接受 token，token 同時是 idempotency key。支付業界的 API 普遍支援 idempotency key（例如 Stripe），agent 的 tool 應該把 harness 推導出的 key 一路傳下去，而不是在 tool 層自己再產生一把。稽核紀錄要記下意圖、核准者與 key，讓對帳能從金流紀錄反查到是哪一次對話、哪一個核准。

**情境四：透過 MCP 接上企業 SaaS 的整合 agent**。當 tool 來自第三方 MCP server（第 14 章），你無法改寫它的名稱與描述，但可以在 client 端做三件事：用 namespacing 避免多個 server 的同名 tool 衝突；把 server 宣告的 annotations 當成提示，而在自己的政策表中重新標註副作用等級（沒審過的一律當 destructive）；在 harness 層統一做結果截斷。也有平台反過來規定 tool 介面：依 OpenAI 公開文件，要讓 Deep Research 使用的 MCP server 必須提供 `search` 與 `fetch` 兩個 tool，這是「少數、職責清楚的 tool」原則在平台層的體現。Manus 公開分享的經驗則提醒另一件事：任務進行中不要增刪 tool 定義（會破壞 prompt cache，歷史中引用的 tool 也可能消失），並用一致的前綴（例如 `browser_`、`shell_`）讓同類 tool 容易被辨識與遮罩。

| 產品類型 | 主要粒度 | 副作用重點 | 回傳與錯誤重點 | 主流做法參考 |
|---|---|---|---|---|
| 電商客服 | workflow 級讀取＋依風險拆開的寫入 | 退款 destructive、退貨單 write | 人類可讀、可轉述給顧客 | τ-bench 以政策＋tools＋環境狀態評估 |
| coding agent | 細粒度的檢視、搜尋、編輯 | sandbox 內可回復；push 與部署才是 destructive | 分段檢視、搜尋限量、編輯前語法檢查 | SWE-agent 的 ACI、str_replace 式編輯 |
| 金融營運 | 兩段式 prepare／commit | 幾乎全是 destructive | 報價單式回傳、結果未知要明說 | 支付 API 的 idempotency key |
| MCP 企業整合 | 由第三方決定，client 端補強 | 自行重新標註，預設 destructive | harness 統一截斷 | search／fetch 雙 tool、固定前綴 |

這張表的共同點是：不管 tool 是自己寫的還是別人給的，副作用政策都必須落在你能控制的 harness 層，而介面品質（名稱、描述、回傳、錯誤）則盡量在 tool 的源頭解決。

> [!note] 2026 現況：框架中的 tool 定義
> 截至 2026 年 10 月，主流框架都提供從函式產生 tool schema 的捷徑（依各框架公開文件）：OpenAI Agents SDK 的 `@function_tool` 會從型別提示與 docstring 產生 schema 並驗證參數；Claude Agent SDK 以 `@tool` 搭配 in-process 的 SDK MCP server 定義自訂 tool；Strands Agents、smolagents 等也都提供 `@tool` 裝飾器。這些捷徑解決的是「schema 與程式同步」，不會替你決定粒度、回傳格式與副作用等級；把 ERP 的函式加上裝飾器，就得到 5.1 節那八個 tool。

## 5.12 設計檢查清單

設計或審查一組 tools 時，逐項回答下面的問題。

1. 每個 tool 的名稱是否遵循一致的格式（例如「資源_動作」），且整組沒有同義動詞的重疊（`get` 與 `fetch` 並存）？
2. 每段描述是否寫明做什麼、何時用、何時改用哪個 tool、回傳什麼？一位沒看過程式碼的新人能不能只靠描述選對 tool？
3. 參數名稱是否沒有歧義（`order_id` 而不是 `id`）？有限集合是否用 enum？格式慣例是否附上例子？
4. 粒度是否依任務設計：模型每次都照同樣順序串接的讀取，是否已經合併成一個 tool？讀取與寫入是否分開？
5. 回傳是否只含下一個決定需要的欄位、用人類可讀的值取代內部代碼與長 UUID？是否提供 concise／detailed 的選擇？
6. 大量結果是否有 cursor 分頁、總筆數與縮小範圍的建議？最後一頁是否明確表示沒有更多？
7. 每種錯誤是否說明發生什麼、可能原因與下一步？空結果是否與錯誤區分開來？「結果未知」是否被明確標示？
8. 每個 tool 是否標註了副作用等級（read、write、destructive）？沒有標註的 tool 是否預設為 destructive？
9. 核准、重試、平行、dry-run 政策是否依副作用等級由 harness 統一執行，而不是寫在描述裡請模型遵守？
10. 所有寫入 tool 是否帶 idempotency key？key 是否由 harness 依業務意圖推導、不出現在模型可見的 schema 中？
11. idempotency 的去重是否發生在真正執行副作用的那一端（金流、ERP），並與副作用在同一個交易中記錄？同一把 key 配不同參數時是否拒絕？
12. 核准是否綁在意圖上，讓重試不會產生第二張核准卡片？
13. 是否有固定任務集與 grader，能比較 tool 修改前後的成功率、步數、tokens 與副作用正確性？是否保留了 held-out 任務？

## 5.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 模型第一步常選錯 tool，第二步才改正 | 名稱相近或功能重疊、描述沒寫界線 | 統計「呼叫後立刻改用另一個 tool」的比例；跑 tool lint | 刪除或合併重疊的 tool；描述寫「何時改用 X」 |
| 簡單問題也要五、六步 | CRUD 級粒度，固定串接交給模型 | 看 trajectory 中是否總是同一串 tool 依序出現 | 合併成 workflow 級 tool，由程式完成串接與計算 |
| 答案出現內部代碼或錯誤的日期 | 回傳是原始欄位，關鍵資訊缺漏或需要模型自行計算 | 比對 tool 回傳與答案，看模型是照抄還是自行推算 | 回傳人類可讀的結論；日期、金額、資格在 tool 內計算 |
| 單題 token 異常高 | 回傳整包傾倒、沒有分頁、讀入長篇條款 | 看 trace 中每則 tool 回傳的長度 | concise 預設、cursor 分頁、條款改成「結論＋可查詢的條目」 |
| 模型把查無資料當系統故障，叫使用者稍後再試 | 錯誤碼不透明，或空結果被當成例外 | 搜尋 transcript 中錯誤碼後的模型回答 | 可行動的錯誤訊息；空結果回傳 `total_matches: 0` 加建議 |
| 同一筆退款執行兩次 | 逾時後模型重試，沒有 idempotency 或 key 每次不同 | 對帳時以訂單反查金流紀錄與 trace 中的 key | harness 依意圖推導 key 並傳到金流端；逾時標示「結果未知」 |
| 客服看到兩張一模一樣的核准卡片 | 核准綁在 tool call 上，而不是綁在意圖上 | 比對兩張卡片的參數與推導出的 key | 核准紀錄以 key 為索引，相同意圖不重複請求 |
| 新接的 MCP tool 默默改了資料 | 副作用等級依名稱或 server 自報判斷 | 檢查政策表中該 tool 的等級來源 | 未審查的 tool 預設 destructive；annotations 只當提示 |

## 本章重點整理

- tool 是給模型用的 API：模型每次只能讀名稱、描述與回傳，看不到程式碼，每多一次呼叫就多一輪推論與成本，所以介面要重新設計，而不是沿用給工程師的 endpoint。
- 一個 tool 有五個模型看得到的面（名稱、描述、參數、回傳、錯誤），以及一段模型看不到、由 harness 保證的中間層（驗證、副作用政策、執行）。
- 名稱要一致且沒有同義重疊；描述要寫做什麼、何時用、何時改用別的、回傳什麼；參數要無歧義、用 enum 與例子表達值域。
- 粒度依任務而不是依 endpoint：把模型每次都照同樣順序做的讀取串接收進 tool，把需要判斷的分岔留給模型，讀寫永遠分開。
- 回傳要以下一個決定需要什麼為準：人類可讀的值、精簡欄位、concise／detailed 選擇，以及附總筆數與建議的 cursor 分頁。
- 可行動的錯誤訊息包含發生什麼、可能原因與下一步；空結果不是錯誤，「結果未知」是需要特別標示的錯誤類別。
- 每個 tool 都要標註副作用等級（read、write、destructive），由 harness 依等級統一決定核准、重試、平行與 dry-run；沒標註的預設為 destructive。
- 副作用等級描述動作的風險，和 autonomy 等級一起決定核准政策：L3 寫入都要核准，L4 只有超出邊界的 destructive 動作要核准。
- agent 的重試來源包括程式、模型、人與 replay，它們都是新的 tool call，所以不能靠 call id 去重。
- idempotency key 要由 harness 依業務意圖推導、不放進模型可見的 schema，並一路傳到真正執行副作用的那一端去重；同一把 key 配不同參數要拒絕。
- 核准應該綁在意圖上，讓同一個意圖的重試不會產生第二張核准卡片。
- 評估 tool 要同時看成功率、步數、tokens、錯誤率與副作用正確性，並讀 transcript 找原因、用 held-out 任務防止過度擬合。
- ScriptedModel 的比較量測的是「在明確的行為假設下」tool 設計的機械性影響，適合重現事故與鎖住修正；真實模型的選擇行為仍需用真實模型反覆評估。

## 延伸問答

> [!question]- Q1. 公司已經有一套文件完整、跑了好幾年的 REST API，為什麼不能直接一對一包成 tool？
> 因為那套 API 的設計前提是「使用者是工程師」：工程師讀一次文件就記住、能看原始碼與 log、呼叫三個 endpoint 再自己組合幾乎不花成本。模型的條件正好相反：每次呼叫都重讀描述、只看得到回傳的文字、每多一個呼叫就多一輪推論與整段歷史的重送。一對一包裝會把 API 的組合負擔全部丟給模型，於是步數、token 與出錯機會一起上升，就像 5.10 節設計差的 tools 在 T2 用了 6 次模型呼叫。
>
> 更深一層的問題是資訊與語意。內部 API 常回傳代碼（`AR`、`TXG-03`）、長 UUID 與大量無關欄位，模型看不懂就只能照抄或猜；錯誤碼如 `ERR_4041` 對模型沒有指引作用。正確的做法是把既有 API 當成 tool 的「實作」，在上面設計一層給模型的介面：依任務合併、整形回傳、改寫錯誤訊息、標註副作用。API 本身不必改，改的是你暴露給模型的那一層。

> [!question]- Q2. workflow 級 tool 能減少步數，那為什麼不乾脆把整個客服流程做成一個 `handle_customer_request` tool？
> 因為那樣就不是 agent 了，而且會失去 tool 粒度帶來的所有控制點。workflow 級 tool 合併的應該是「模型每次都會照同樣順序做」的確定性串接，例如查訂單後一定要看物流與退款資格。客服流程中真正需要判斷的部分，例如顧客到底要退款還是換貨、要不要先安撫情緒、資訊不足時要問什麼，正是要交給模型的；把它們包進一個 tool，等於把判斷寫死成程式，那應該用第 18 章的 workflow 實作，而不是假裝成 agent。
>
> 另一個代價是控制與觀測。一個萬用 tool 無法標示單一的副作用等級（它有時只讀、有時退款），harness 就無法依等級套用核准與重試政策；trace 中也只看得到一次呼叫，看不出 agent 在哪一步做了什麼決定。實務上的判準是：合併後的 tool 是否仍然只有一種副作用等級、一個清楚的職責，以及模型是否仍然需要在它之外做有意義的選擇。

> [!question]- Q3. 程式找錯：下面的退款 tool 宣稱支援 idempotency，請指出問題並說明後果。
> ```python
> REFUND_SCHEMA = {"name": "refunds_create", "parameters": {"type": "object",
>     "properties": {"order_id": {"type": "string"}, "amount": {"type": "integer"},
>                    "idempotency_key": {"type": "string", "description": "隨機產生的唯一字串"}},
>     "required": ["order_id", "amount", "idempotency_key"]}}
>
> SEEN = {}
> def refunds_create(order_id, amount, idempotency_key):
>     if idempotency_key in SEEN:
>         return SEEN[idempotency_key]
>     result = gateway.refund(order_id, amount)        # 沒有把 key 傳給閘道
>     SEEN[idempotency_key] = result
>     return result
> ```
> 第一個問題是 key 由模型產生。schema 要求模型填「隨機產生的唯一字串」，模型每次重試都會照做，產生一把新的 key，於是去重永遠不會命中，保護形同虛設，正如 5.8 節程式中「模型自產 key」那兩筆重複的金流紀錄。key 應該由 harness 依業務意圖（run、tool、訂單、金額）推導，並從模型可見的 schema 中移除。
>
> 第二個問題是去重發生在錯誤的地方。`SEEN` 只在閘道成功回應後才寫入；如果閘道扣款成功但回應逾時，`gateway.refund` 拋出例外，`SEEN` 沒有紀錄，下一次重試會再扣一次款。key 必須傳給閘道，由執行副作用的那一端在同一個交易中記錄。另外 `SEEN` 是記憶體中的 dict，process 重啟或多台機器時就失效，也沒有比對「同一把 key 是否配上不同參數」，應該在不一致時拒絕。

> [!question]- Q4. 你在 production 的 trace 中發現，`orders_search` 之後有七成的機率緊接著呼叫 `orders_get_overview`，這代表什麼？你會怎麼處理？
> 這是典型的「固定串接」訊號：模型搜尋到訂單之後，幾乎總是還需要那張訂單的詳細資訊，代表 `orders_search` 的回傳少了模型下一步需要的欄位。第一步是讀幾條 transcript，確認模型在 `orders_get_overview` 的結果中用到了什麼，例如退款資格或物流進度；如果是這樣，就把這些欄位加進搜尋結果的摘要，或讓搜尋在只有一筆結果時直接回傳完整概覽。
>
> 處理前要權衡兩件事。一是回傳大小：搜尋結果若有很多筆，每筆都附完整概覽會讓 token 暴增，所以可以只在 concise 摘要中加入最常用的一兩個欄位，或依結果筆數調整。二是不要誤判：如果那三成沒有接續呼叫的情況，正是因為使用者只想確認「有沒有這張訂單」，那現在的設計可能已經合理。修改後要在任務集上比較步數與 token，並觀察上線後這個比例是否下降，而不是只憑直覺改。

> [!question]- Q5. 估算題：一個客服 agent 掛了 30 個 tool，平均每個定義 250 tokens，每次對話平均 10 次模型呼叫，每天 10 萬次對話。光是 tool 定義每天要送多少 tokens？若重構成 8 個、每個 300 tokens 呢？
> 30 個 tool 的定義約 30 × 250 ＝ 7,500 tokens，每次模型呼叫都要送一次，所以每次對話是 7,500 × 10 ＝ 75,000 tokens，每天 75,000 × 100,000 ＝ 75 億 tokens。重構成 8 個、每個描述寫得更完整（300 tokens）之後，定義是 2,400 tokens，每次對話 24,000 tokens，每天 24 億 tokens，大約只剩三分之一。而且這還沒算步數下降的效果：如果重構讓平均呼叫數從 10 次降到 6 次，每天就是 2,400 × 6 × 100,000 ＝ 14.4 億 tokens。
>
> prompt caching 會大幅降低這部分的實際費用，因為 tool 定義位於穩定前綴，命中快取時以較低的價格計費；但快取不是免費的，寫入快取有成本、快取有存活時間，而且只要在對話中途改變 tool 清單或順序就會失效。另外，tool 定義的成本不只是錢：它佔用 context，也佔用模型的注意力，tool 越多、越相似，選錯的機率越高。所以估算的結論不只是「快取能省錢」，而是「tool 數量與描述長度都是要管理的預算」，當 tool 真的多到上百個時，就要用第 13 章的 tool search 與延遲載入。

> [!question]- Q6. 面試追問：請設計一個退款 tool，保證在網路逾時、模型重試、服務重啟的情況下都不會重複退款。
> 我會從意圖、key、執行端三層回答。意圖層：把退款的業務意圖定義為（對話或任務 id、訂單、金額，必要時加品項），harness 從這些欄位推導 idempotency key，key 不出現在模型可見的 schema 中，所以模型怎麼重試、措辭怎麼改，同一個意圖都得到同一把 key。核准也綁在這把 key 上，避免重試產生第二張核准卡片。
>
> 執行端：key 一路傳到金流閘道或退款服務，由它在扣款的同一個資料庫交易中寫入「key → 參數指紋 → 結果」；同一把 key 再來就回傳原結果，參數不同就拒絕。紀錄要持久化並設保存期限，這樣服務重啟或換機器後仍然有效。若下游不支援 key，就在自家退款服務中加一張帶唯一約束的意圖表，先寫意圖再呼叫下游，並用定期對帳處理「寫了意圖但不知道下游結果」的情況。
>
> 介面層：逾時時 tool 回傳「結果未知，可能已成功；可以相同參數重試」，而不是單純的失敗；大額退款改成 prepare／commit 兩段式，核准的對象是 prepare 產生的報價單，commit 的確認 token 兼作 key。最後補上觀測：trace 與稽核紀錄都記下 key，對帳時能從每一筆金流反查到對話與核准者。若有 durable execution（第 22 章），replay 時同樣沿用原本的 key。

> [!question]- Q7. MCP server 已經在 tool 上標了 `readOnlyHint: true`，為什麼 harness 還要自己維護一份副作用等級？
> 因為 annotations 是 server 的自我宣告，而 server 不一定可信、也不一定正確。MCP 規格本身就把 annotations 定位為提示，要求 client 不應在不信任 server 時依賴它們。實際風險有三種：第三方 server 的作者標錯（例如 `sync_contacts` 實際上會覆寫資料）；server 在你核准後更新了 tool 的行為與標註（第 31 章的 rug pull）；惡意 server 刻意把有副作用的 tool 標成唯讀，以避開核准。
>
> 所以合理的分工是：annotations 是審查時的輸入，幫你快速分類；最終的副作用等級寫在你自己的政策表中，經過人工審查，並和 tool 定義的版本（或定義內容的 hash）綁在一起，定義一變就重新審查。沒有審查過的 tool 一律當 destructive。這和「描述裡寫了需要核准，harness 仍要強制核准」是同一個原則：安全相關的決定，必須落在你能控制的那一層。

> [!question]- Q8. 阿哲看到 5.10 節的表格，想拿「成功率從 1/4 提升到 4/4」去跟主管報告，你會怎麼回應？
> 我會說這個數字證明的是機制，不是成效。ScriptedModel 的劇本是我們寫的，它把「模型看到 `ERR_4041` 會以為系統故障」「看到逾時會重試」這些行為當成假設寫死了，所以成功率的差異是在這些假設下必然得到的結果。它能可靠證明的是：好的 tools 在相同行為下需要更少步數與 token、能讓可行動的錯誤被利用、能讓重試不會重複退款；這些是確定性的機械效果，而且已經用 assert 鎖成回歸測試。
>
> 要對主管報告成效，需要用真實模型在更大的任務集上評估：從試用期的客服紀錄挑出數十到數百個有可驗證結果的任務，兩組 tools 各跑多次，比較成功率、平均步數、token 與副作用正確性，並用第 27 章的方法看差異是否顯著、pass^k 這類一致性指標是否改善。在那之前，可以誠實地報告兩件已經確定的事：重複退款的根因已被修正並有測試保護，以及在相同行為假設下單題成本約降六成，真實的成功率提升待評估確認。

## 延伸閱讀

- Anthropic Engineering Blog〈Writing effective tools for agents — with agents〉（2025）
- Anthropic Engineering Blog〈Building effective agents〉（2024），附錄〈Prompt engineering your tools〉
- Yang et al.〈SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering〉（NeurIPS 2024）
- OpenAI〈A practical guide to building agents〉（2025）
- Model Context Protocol 規格，Tools 章節（2026-07-28 版）
- Stripe API Reference〈Idempotent requests〉
- Anthropic Engineering Blog〈Effective context engineering for AI agents〉（2025）
