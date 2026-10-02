---
chapter: 15
title: Agent 之間與 Agent 到前端：A2A 與 AG-UI
part: 3
---

# 第 15 章　Agent 之間與 Agent 到前端：A2A 與 AG-UI

> [!abstract] 本章地圖
> **核心問題**：當工作要交給另一家公司的 agent 處理、要花上幾小時甚至幾天，而使用者又在畫面前等著看進度時，agent 之間、agent 與前端之間應該用什麼樣的契約溝通？
>
> **你會學到**：
> - 分清楚 MCP、A2A、AG-UI 各自連接哪兩方，判斷一個整合需求該用哪一個協定
> - 讀懂並驗證 A2A 的 agent card，用它做能力探索與授權需求判斷
> - 實作含 input-required、auth-required 中斷態的 task 狀態機，並用合法轉移表擋下非法操作
> - 為長任務選擇 polling、streaming 或 push notification，並處理斷線與重新訂閱
> - 用 AG-UI 風格的事件串流把文字、tool call 與共享 state 推給前端，前端能驗證事件順序並重建畫面
> - 說明 agent payments 協定（AP2、ACP、x402 等）分別解決哪一層的信任問題
>
> **前置知識**：第 4 章（agent loop、streaming 的組裝）、第 5 章（tool 的副作用分級）、第 14 章（MCP 的 host／client／server 與授權）

## 15.1 故事：三天才會完成的 tool call

第 14 章之後，青鳥的客服 agent 已經透過 MCP 接上了 ERP 與物流商的查詢 API，查貨態、查庫存都很順。新的需求來自店家：包裹在運送途中壓壞了，店家希望直接在青鳥後台跟客服 agent 說一句「B-2077 外箱壓壞，幫我申請理賠」，不必再登入物流商的網站填表。合作的物流商「快航物流」剛好推出了自己的理賠 agent，願意讓合作夥伴從系統對接。阿哲很興奮：「對方都有 agent 了，兩個 agent 講話應該很快吧？」

Iris 的第一版很直覺：把快航的理賠 agent 包成一個 MCP tool `file_claim`，客服 agent 呼叫它、等它回傳。第一天就出了三個問題。第一，理賠不是一次呼叫能完成的事：快航的 agent 收到申請後，會要求補上外箱破損照片，審核要好幾個工作天，`file_claim` 在 30 秒逾時後只拿到一個錯誤，客服 agent 卻告訴店家「已幫您送出理賠」。第二，快航需要店家本人授權才能代為申請，Iris 一時找不到地方放這一步，只好把青鳥自己的服務帳號 token 塞進參數裡；Maya 看到後立刻擋下：「這等於用青鳥的身分替所有店家申請理賠，對方根本無從分辨是哪一家店授權的。」第三，店家在後台只看到一個轉圈圈，四十秒後才跳出一大段文字，中間 agent 查了什麼、卡在哪裡，畫面上完全沒有。

老陳看完事故紀錄，在白板上畫了三條線。「你遇到的是三種不同的邊。」老陳說，「agent 呼叫工具是一種邊，MCP 管；agent 把工作交給另一個不透明的 agent，是第二種邊，那是一個有生命週期的 task，不是一次函式呼叫；agent 把自己正在做的事推給畫面，是第三種邊，那是一條事件串流，不是最後一包回應。把三種邊混成一種，就會出現你今天的三個事故。」

這一章就沿著老陳的三條線展開。我們先用一張地圖分清 MCP、A2A、AG-UI 的分工，再深入 A2A 的 agent card、task 狀態機與長任務通知，接著談 AG-UI 的事件模型、共享 state 與 generative UI，最後概覽 agent 需要替人付錢時的 payments 協定與信任模型。「動手做」會實作一個含中斷態與合法轉移檢查的 A2A 風格 task 狀態機，以及一條給前端消費的 AG-UI 風格事件串流，把 Iris 的三個事故全部改寫成可測試的流程。

## 15.2 三個協定、三條邊：MCP、A2A、AG-UI 的分工

要理解這三個協定，最有效的方法是先問「它連接哪兩方」。**MCP**（第 14 章）連接 agent 與它的工具、資料：對 agent 來說，對方是一組可以列舉、可以呼叫的能力。**A2A**（Agent2Agent protocol，agent 對 agent 協定）連接兩個 agent：對呼叫方來說，對方是一個**不透明**（opaque）的服務，你看不到它的 prompt、工具與記憶，只能交給它一個任務、等它回報。**AG-UI**（Agent–User Interaction protocol，agent 與使用者互動協定）連接 agent 後端與前端畫面：它規定 agent 在執行過程中要送出哪些事件，前端才能即時顯示文字、工具進度與狀態。

```text
                     ┌──────────────────────────────┐
  店家的瀏覽器 ◄─────┤ AG-UI：事件串流（SSE）        │
  （青鳥後台）  ────►│ 文字片段、tool 進度、state    │
                     └──────────────┬───────────────┘
                                    │
                     ┌──────────────▼───────────────┐
                     │   青鳥客服 agent（loom）      │
                     │   loop、context、approval    │
                     └───────┬───────────────┬──────┘
                MCP：tool 呼叫 │               │ A2A：task 委派
                （同步、短）   │               │ （有生命週期、可能很長）
                     ┌────────▼─────┐   ┌─────▼──────────────────┐
                     │ ERP、物流查詢 │   │ 快航理賠 agent（黑盒子）│
                     │ MCP server    │   │ 自己的模型、工具、人員  │
                     └──────────────┘   └────────────────────────┘
```

這張圖從上往下看。最上面是 AG-UI 這條邊：店家的瀏覽器送出一則訊息，開始一次 **run**（一次 agent 執行），後端則持續送回事件，讓畫面一邊長出文字、一邊顯示「正在查理賠進度」的卡片。中間是青鳥自己的 agent，所有的決策與保證都在這裡。左下是 MCP：查詢 ERP、查物流貨態這類短而確定的動作，agent 把它們當成工具。右下是 A2A：快航的理賠 agent 有自己的模型、工具，甚至背後還有真人審核員，青鳥不需要也不應該知道它怎麼運作，只需要知道「我交出去的理賠 task 現在在哪個狀態、要我補什麼、最後產出什麼」。

為什麼不能全部用 MCP？技術上當然可以把任何遠端 agent 包成一個 tool，很多團隊一開始也這麼做。問題在於語意：tool 呼叫的心智模型是「送出參數、拿回結果」，它假設呼叫很短、結果一次到齊、中間不需要雙方再溝通。理賠這種工作恰好違反每一條假設：它會跑好幾天，中途要補件、要授權，結果是一份要長期保存的理賠單。MCP 近年也加入了長任務（Tasks extension）與「server 要求更多輸入」的機制，界線確實在靠近，但兩者的預設立場仍然不同：MCP 把對方當成能力，A2A 把對方當成同儕。

| 面向 | MCP | A2A | AG-UI |
|---|---|---|---|
| 連接的兩方 | agent ↔ 工具與資料 | agent ↔ 另一個不透明的 agent | agent 後端 ↔ 前端畫面 |
| 對方是什麼 | 一組可列舉的 tools、resources、prompts | 一個有技能清單的服務 | 一個要即時呈現進度的使用者介面 |
| 互動單位 | 一次 tool 呼叫 | 一個有生命週期的 task | 一次 run 內的一連串事件 |
| 典型時長 | 毫秒到數十秒 | 秒到數天 | 與一次 run 相同，通常數秒到數分鐘 |
| 中途溝通 | 少（server 可要求補輸入） | 核心能力：input-required、auth-required | 核心能力：interrupt、前端 tool、使用者輸入 |
| 結果 | tool 回傳值 | artifact（可長期保存的產出） | 前端畫面狀態（訊息、卡片、共享 state） |
| 青鳥的例子 | 查訂單、查貨態 | 向快航申請破損理賠 | 店家後台的對話視窗與理賠面板 |

這張表最重要的是「互動單位」那一列。tool 呼叫、task、run 事件三者的生命週期長短完全不同，選錯單位就會出現 Iris 的事故：把幾天的 task 當成幾秒的 tool 呼叫，逾時就只能報錯；把一連串事件壓成一包最後的回應，使用者就只能盯著轉圈圈。另一個常見誤解是把三者想成互相競爭的標準，實際上它們疊在一起用：一個 agent 可能同時是 AG-UI 的後端、A2A 的 client，以及好幾個 MCP server 的 client。

> [!warning] 常見誤解
> 「只要對方是 agent，就該用 A2A。」不一定。如果對方的行為短、確定、像一個函式（例如「把地址正規化」），即使背後是 LLM，包成 MCP tool 更簡單。判斷標準不是對方用不用模型，而是互動需不需要生命週期：會不會跑很久、會不會中途要求補件或授權、產出需不需要長期查詢。需要的話用 A2A；不需要的話，tool 就夠了。

## 15.3 Agent card：讓別人知道你是誰、會什麼、怎麼連

兩個公司的 agent 要合作，第一個問題是「怎麼知道對方能做什麼」。A2A 的答案是 **agent card**（agent 名片）：一份 JSON 文件，宣告這個 agent 的名稱、版本、提供者、支援的連線方式與協定版本、能力旗標（是否支援 streaming、push notification）、需要哪種身分驗證，以及一份 **skill**（技能）清單。例如快航的 agent card 會寫：「我是快航物流理賠 agent，有兩個技能：查詢貨態、申請破損理賠；申請理賠可以收文字與 JPEG 照片；呼叫我需要店家透過 OAuth 授權 `claims:write`。」

agent card 通常發布在對方網域下一個約定好的位置（**well-known URI**，例如 `/.well-known/agent-card.json`），就像網站用固定路徑放 `robots.txt` 一樣，client 只要知道對方的網域就能找到它。企業內部也常把 agent card 登錄在 registry（目錄服務），讓內部的 agent 可以依技能搜尋，概念上和第 13 章的 tool registry 類似。

```text
 青鳥客服 agent                                     快航物流
     │                                                  │
     │ (1) GET 對方網域 /.well-known/agent-card.json    │
     │─────────────────────────────────────────────────►│
     │◄──────────── agent card（公開版：技能、端點、     │
     │               支援的 binding、security 需求）    │
     │                                                  │
     │ (2) 本地驗證：欄位齊全？端點是 TLS？            │
     │     security 引用的 scheme 有定義？簽章可驗證？  │
     │                                                  │
     │ (3) 挑 skill：tag 含 claim，inputModes 收 JPEG   │
     │                                                  │
     │ (4) 依 security 需求取得憑證（店家 OAuth 同意）  │
     │                                                  │
     │ (5) 帶憑證取 extended card（需認證的完整版）     │
     │─────────────────────────────────────────────────►│
     │◄───────────── 進階技能、租戶專屬端點             │
     │                                                  │
     │ (6) SendMessage：開始第一個 task                 │
     │─────────────────────────────────────────────────►│
```

這張流程圖說明了 agent card 不是「讀了就用」。第 (1) 步取得的是公開版名片，任何人都能讀，所以只放可以公開的資訊。第 (2) 步是 client 的責任：名片是對方自己寫的，內容可能缺欄位、端點可能不是 TLS、security 區塊可能引用了沒定義的驗證方式；如果名片有簽章，還要驗證它確實出自宣稱的提供者，避免有人在中間替換名片、把你導到假的端點。第 (3) 步依技能的標籤與可接受的資料型態挑選技能。第 (4)、(5) 步處理授權：有些能力只在認證後才揭露，A2A 稱為 **extended agent card**（擴充名片），例如只對簽約夥伴開放的批次理賠。第 (6) 步才真正開始送任務。

下面的程式模擬 (1) 到 (3) 步：用一個 dict 假裝 HTTP 層，取得快航的名片、做最低限度的驗證，再挑出能收照片的理賠技能。

```python
from __future__ import annotations

import json


# 快航物流在自己的網域發布 agent card；這裡用 dict 模擬「網址 → 回應內容」的 HTTP 層
FAKE_WEB = {
    "https://kuaihang.example.com/.well-known/agent-card.json": json.dumps({
        "name": "快航物流理賠 agent",
        "description": "受理包裹破損、遺失的理賠申請，並回報審核進度",
        "version": "2.3.0",
        "provider": {"organization": "快航物流"},
        "supportedInterfaces": [{"url": "https://a2a.kuaihang.example.com/v1",
                                 "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}],
        "capabilities": {"streaming": True, "pushNotifications": True, "extendedAgentCard": True},
        "securitySchemes": {"merchant_oauth": {"type": "oauth2", "scopes": ["claims:read", "claims:write"]}},
        "security": [{"merchant_oauth": ["claims:write"]}],
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {"id": "track", "name": "查詢貨態", "tags": ["tracking"], "inputModes": ["text/plain"]},
            {"id": "file_claim", "name": "申請破損理賠", "tags": ["claim", "damage"],
             "inputModes": ["text/plain", "image/jpeg"], "examples": ["B-2077 外箱壓壞，申請理賠"]},
        ],
    }, ensure_ascii=False),
}
WELL_KNOWN = "/.well-known/agent-card.json"


def discover(host: str) -> dict:
    """依慣例到對方網域的 well-known 路徑取 agent card。"""
    return json.loads(FAKE_WEB[f"https://{host}{WELL_KNOWN}"])


def validate_card(card: dict) -> list[str]:
    """上線前的最低檢查：缺欄位、非 TLS 端點、引用了沒定義的 security scheme。"""
    problems = [f"缺少 {k}" for k in ("name", "version", "supportedInterfaces", "skills") if k not in card]
    for itf in card.get("supportedInterfaces", []):
        if not itf["url"].startswith("https://"):
            problems.append(f"端點不是 TLS（{itf['url'].split(':')[0]}）")
    for req in card.get("security", []):
        for scheme in req:
            if scheme not in card.get("securitySchemes", {}):
                problems.append(f"security 引用了未定義的 scheme：{scheme}")
    return problems


def pick_skill(card: dict, tag: str, need_mode: str) -> dict | None:
    """挑出「標籤符合、而且吃得下我要送的資料型態」的 skill。"""
    for skill in card["skills"]:
        modes = skill.get("inputModes", card["defaultInputModes"])
        if tag in skill["tags"] and need_mode in modes:
            return skill
    return None


card = discover("kuaihang.example.com")
print("agent    :", card["name"], card["version"])
print("端點     :", card["supportedInterfaces"][0]["protocolBinding"], "／ streaming =",
      card["capabilities"]["streaming"], "／ push =", card["capabilities"]["pushNotifications"])
print("卡片檢查 :", validate_card(card) or "通過")
skill = pick_skill(card, "claim", "image/jpeg")
print("選用 skill:", skill["id"], skill["name"])
print("需要授權 :", card["security"])

bad = dict(card, security=[{"api_key": []}])
bad["supportedInterfaces"] = [{"url": "http://a2a.kuaihang.example.com/v1", "protocolBinding": "JSONRPC"}]
print("壞卡片   :", validate_card(bad))
assert skill["id"] == "file_claim" and validate_card(card) == []
assert pick_skill(card, "tracking", "image/jpeg") is None      # 查貨態的 skill 不收照片
assert len(validate_card(bad)) == 2
```

```text
agent    : 快航物流理賠 agent 2.3.0
端點     : JSONRPC ／ streaming = True ／ push = True
卡片檢查 : 通過
選用 skill: file_claim 申請破損理賠
需要授權 : [{'merchant_oauth': ['claims:write']}]
壞卡片   : ['端點不是 TLS（http）', 'security 引用了未定義的 scheme：api_key']
```

輸出的前三行是名片的基本資訊與驗證結果：名片宣告支援 JSON-RPC binding、streaming 與 push，三項檢查都通過。第四行挑到 `file_claim`，因為它的標籤含 `claim`，而且 `inputModes` 裡有 `image/jpeg`；assert 也確認「查詢貨態」雖然存在，但不收照片，所以不會被選上。第五行列出 security 需求：呼叫時需要 `merchant_oauth` 這個 scheme 的 `claims:write` scope，這正是 Iris 事故二缺的那一步。最後一行是一張壞名片：端點是明文 HTTP，security 引用了沒定義的 `api_key`，兩個問題都被抓出來。

agent card 的設計有兩個常見誤解。第一，名片上的技能描述是給 client（常常是另一個模型）看的，寫法和第 5 章的 tool 描述一樣重要：例子、可接受的輸入、產出的格式都要寫清楚。第二，名片宣告的能力不等於授權：名片說「我會申請理賠」，不代表任何拿到名片的人都能替任何店家申請。授權永遠由 security 區塊與實際的 token 決定，伺服端每一次請求都要檢查，不能因為「對方讀過我的名片」就信任它。

## 15.4 Task 生命週期：狀態機與兩個中斷態

A2A 最核心的抽象是 **task**（任務）：client 送出第一則訊息時，server 建立一個 task，給它一個由 server 產生的 id，之後所有的進度、補件、產出都掛在這個 id 底下。task 有明確的狀態，任何時刻都只處在其中一個；狀態之間的轉移就是一台**狀態機**（state machine）。把遠端工作建模成狀態機，好處是雙方對「現在進行到哪」有共同語言：青鳥的 agent 不必解析快航寫的自由文字，只要讀狀態欄位，就知道該等待、該補件、該請店家授權，還是可以結案。

```text
                         ┌───────────┐
                         │ submitted │  server 收到、建立 task
                         └─────┬─────┘
              rejected ◄───────┤ 接受
                               ▼
              ┌──────────►┌─────────┐◄──────────┐
   補件送達   │           │ working │           │ 授權完成
              │           └────┬────┘           │
     ┌────────┴───────┐        │       ┌────────┴───────┐
     │ input-required │◄───────┼──────►│ auth-required  │
     │ 等 client 補資料│        │       │ 等 client 授權  │
     └────────┬───────┘        │       └────────┬───────┘
              │                ▼                │
              │   ┌──────────────────────────┐  │
              └──►│ 終態：completed／failed／ │◄─┘
       （canceled、│ canceled／rejected        │（canceled、failed）
         failed） │ 一旦進入就不可再變         │
                  └──────────────────────────┘
```

逐步看這張圖。task 從 `submitted` 開始，server 決定接受就進入 `working`，決定不接（例如超出服務範圍）就直接 `rejected`。`working` 是 agent 正在做事的狀態，它可以走向三類結果：正常完成（`completed`）、失敗（`failed`）、被取消（`canceled`）；也可以進入兩個**中斷態**（interrupted state）：`input-required` 表示 agent 需要 client 補充資料才能繼續，例如「請提供外箱破損照片」；`auth-required` 表示 agent 需要額外的授權，例如「需要店家授權 `claims:write`」。中斷態不是失敗，而是「球在你那邊」：client 補上需要的東西，task 回到 `working` 繼續。最下方的四個狀態是**終態**（terminal state），進入之後 task 就不再改變。

| 狀態 | 意義 | 球在誰手上 | 青鳥的例子 |
|---|---|---|---|
| submitted | server 已收到，尚未開始 | server | 理賠申請剛送達 |
| working | agent 正在處理 | server | 快航正在比對運送紀錄 |
| input-required | 需要 client 補充資料 | client（通常要轉給人） | 要求上傳破損照片 |
| auth-required | 需要額外授權才能繼續 | client（要求擁有者同意） | 要求店家授權申請理賠 |
| completed | 成功完成，結果在 artifact | 無（終態） | 理賠已立案，附理賠編號 |
| failed | 處理失敗 | 無（終態） | 運單查無此件 |
| canceled | 被 client 取消 | 無（終態） | 店家撤回申請 |
| rejected | server 拒絕接受 | 無（終態） | 超過申請期限，不受理 |

「球在誰手上」這一欄是設計 client 時最實用的視角。server 手上的狀態，client 只需要等；client 手上的兩個中斷態，client 必須主動處理，而且往往不是 agent 自己能決定的：照片要店家拍，授權要店家本人同意。這就是為什麼中斷態要和第 21 章的 human-in-the-loop 接起來：A2A 的 `input-required` 在青鳥這端，常常會變成一張給店家的待辦卡片。

為什麼終態不可再變？想像理賠已經 `completed`，店家又想補一張照片。如果允許 task 從 completed 回到 working，這張 task 的歷史就變得難以理解：它到底完成了沒？之前查過狀態、據此對帳的系統，看到的資料就作廢了。A2A 的做法是讓終態不可變（immutable），後續工作開一個新 task，並用 **contextId**（脈絡 id）把相關的 task 串成同一組，必要時在新訊息中引用舊 task 的 id。這和資料庫裡「已入帳的交易不修改，只用沖銷交易更正」是同一個思路。

spec 的重點是定義每個狀態的語意；實作時要把語意翻成一張明確的「哪個狀態可以轉到哪個狀態」的轉移表，每次轉移都檢查。下面是本書採用的規則，比 spec 的語意稍嚴格：中斷態只能回到 working 或結束（取消、失敗），不能直接跳到 completed，因為「收到補件」與「完成」之間一定要有 agent 處理的步驟。

```python
from __future__ import annotations

TERMINAL = {"completed", "failed", "canceled", "rejected"}
INTERRUPTED = {"input-required", "auth-required"}
# 本書的實作規則：spec 定義每個狀態的語意，這張表把語意翻成「哪些轉移合法」
ALLOWED: dict[str, set[str]] = {
    "submitted": {"working", "rejected", "canceled", "failed"},
    "working": {"input-required", "auth-required", "completed", "failed", "canceled"},
    "input-required": {"working", "canceled", "failed"},
    "auth-required": {"working", "canceled", "failed"},
}


class InvalidTransition(Exception):
    pass


def check(src: str, dst: str) -> None:
    if src in TERMINAL:
        raise InvalidTransition(f"{src} 是終態，task 不可再變；後續工作請在同一 contextId 開新 task")
    if dst not in ALLOWED[src]:
        hint = "中斷態要先回到 working（收到補件後繼續），不能直接跳到完成" if src in INTERRUPTED else "不在允許清單"
        raise InvalidTransition(f"{src} → {dst}：{hint}")


cases = [
    ("submitted", "working"), ("working", "input-required"), ("input-required", "working"),
    ("working", "auth-required"), ("auth-required", "working"), ("working", "completed"),
    ("completed", "working"), ("input-required", "completed"), ("working", "submitted"),
    ("canceled", "canceled"),
]
results = []
for src, dst in cases:
    try:
        check(src, dst)
        results.append(True)
        print(f"  ok    {src:>14} → {dst}")
    except InvalidTransition as exc:
        results.append(False)
        print(f"  拒絕  {src:>14} → {dst:<15} {exc}")
assert results == [True] * 6 + [False] * 4
```

```text
  ok         submitted → working
  ok           working → input-required
  ok    input-required → working
  ok           working → auth-required
  ok     auth-required → working
  ok           working → completed
  拒絕       completed → working         completed 是終態，task 不可再變；後續工作請在同一 contextId 開新 task
  拒絕  input-required → completed       input-required → completed：中斷態要先回到 working（收到補件後繼續），不能直接跳到完成
  拒絕         working → submitted       working → submitted：不在允許清單
  拒絕        canceled → canceled        canceled 是終態，task 不可再變；後續工作請在同一 contextId 開新 task
```

前六行是一條完整的合法路徑：接受、要求補件、補件後繼續、要求授權、授權後繼續、完成，這正是快航理賠 task 的標準生命週期。後四行是被拒絕的轉移，各自代表一種實務上會出現的 bug。`completed → working` 是「想在完成的 task 上補件」；`input-required → completed` 是「server 收到補件後沒有處理就宣告完成」，常見於有人把補件流程寫成捷徑；`working → submitted` 是狀態倒退，通常是重試邏輯把舊的狀態寫回去；`canceled → canceled` 則提醒我們，即使轉到同一個狀態，終態也不接受任何轉移，「重複取消」要在更上層以 idempotent 的方式處理，而不是讓狀態機放行。

> [!warning] 常見誤解
> 「把 task 狀態存成一個字串欄位就好，誰要改就改。」沒有轉移檢查的狀態欄位，遲早會出現「已完成的理賠又變成處理中」這種資料。轉移檢查要放在唯一的寫入入口（例如 `TaskStore.transition()`），並在資料庫層用條件更新（只有目前狀態等於預期值時才更新）防止兩個 worker 同時改同一張 task。狀態機的價值不在畫圖，而在每一次寫入都被它擋過。

## 15.5 Message、Artifact 與長任務的通知：streaming 與 push

task 裡流動的內容分成兩種。**message**（訊息）是雙方溝通用的：client 說「申請理賠」、agent 說「請補照片」，每則訊息標明角色（user 或 agent），由一個或多個 **part**（片段）組成，part 可以是文字、檔案或結構化資料。**artifact**（產出物）是任務的成果：理賠單、報表、翻譯好的文件，同樣由 part 組成。spec 特別強調結果要放在 artifact，不要只寫在 message 裡，因為 message 是溝通用的，不保證可靠送達；artifact 則掛在 task 上，任何時候用 task id 查都拿得到。青鳥的對帳系統要讀的是理賠單 artifact 裡的理賠編號，不是某則訊息裡的一句話。

接下來是長任務最實際的問題：client 怎麼知道 task 變了？A2A 提供三種方式。最簡單的是 **polling**（輪詢）：client 定期用 task id 查詢狀態。第二種是 **streaming**（串流）：client 送出訊息時改用串流版的操作，server 在同一條 HTTP 連線上用 SSE（server-sent events，伺服器推送事件）持續送回狀態更新與 artifact 更新。第三種是 **push notification**（推送通知）：client 事先登記一個 webhook，server 在 task 有變化時主動呼叫它，client 不必維持連線。

```text
 青鳥 agent                       快航 A2A server                 青鳥 webhook
    │── SendStreamingMessage ─────────►│                               │
    │◄── status: working ──────────────│                               │
    │◄── status: input-required ───────│   （串流在中斷態結束）        │
    │                                  │                               │
    │   ……店家兩小時後才上傳照片……     │                               │
    │── SendMessage（補件，帶 taskId）─►│                               │
    │◄── status: working ──────────────│                               │
    │── 登記 push config（webhook）────►│                               │
    │   （青鳥的 worker 被重新部署，連線中斷）                          │
    │                                  │── POST：status auth-required ─►│
    │                                  │   （帶驗證 token）             │ 驗證來源
    │                                  │                               │ 轉成店家待辦
    │── GetTask 或 SubscribeToTask ────►│   （重新上線後補齊狀態）      │
    │◄── 目前完整 task 快照 ───────────│                               │
```

這張時序圖把三種通知方式放在同一個理賠流程裡。一開始青鳥用 streaming：狀態更新即時送達，進入 `input-required` 時串流結束，因為接下來要等的是人，不是機器。兩小時後店家上傳照片，青鳥用 task id 補件，task 回到 working。這時青鳥知道接下來的審核可能要好幾天，維持連線不划算，所以登記了 push config。後來青鳥的 worker 重新部署、連線中斷，快航仍然能把 `auth-required` 推到 webhook；webhook 驗證這個通知確實來自快航（驗證 token 或簽章），再把它轉成店家的待辦。最後一步是重新上線的補償：不論推送有沒有漏，client 都可以用 `GetTask` 取得完整快照，或用 `SubscribeToTask` 重新訂閱。

| 通知方式 | 運作 | 適合 | 代價與風險 |
|---|---|---|---|
| polling | client 定期查詢 task | 低頻、簡單整合、防火牆內的 client | 延遲取決於輪詢間隔；太頻繁浪費資源 |
| streaming | 同一連線上持續收 SSE 事件 | 秒到分鐘級、使用者正在等 | 要維持連線；斷線後要重新訂閱並補齊狀態 |
| push notification | server 呼叫 client 登記的 webhook | 小時到天級、client 不常駐 | webhook 要公開可達、驗證來源；server 端要防 SSRF |

三種方式不是互斥的，成熟的 client 通常組合使用：使用者在等時用 streaming，進入長時間等待時登記 push，任何時候都能用查詢補齊。push 的安全問題要特別注意兩邊。對 client 來說，webhook 是一個任何人都能打的公開端點，必須驗證通知來自真正的 server，並且只把通知當成「去查一下」的提示，真正的狀態以 `GetTask` 查到的為準。對 server 來說，webhook 網址是 client 給的，如果不檢查就照著打，攻擊者可以登記一個指向 server 內網的網址，讓 server 替它打內部服務，這叫 **SSRF**（server-side request forgery，伺服端請求偽造）；server 應該驗證網址的擁有權、限制可呼叫的網段。

還有一個設計原則值得記住：**task 的狀態以 server 為準，事件只是通知**。串流可能斷、push 可能重送或亂序，client 端的畫面與資料庫要能容忍重複事件（用 task id 與狀態做冪等更新），也要能在任何時候用一次完整查詢覆蓋本地狀態。這和 15.7 節 AG-UI 的 snapshot 加 delta 是同一個想法：增量事件讓體驗即時，完整快照讓系統正確。

> [!note] 2026 現況
> 截至 2026 年 10 月，A2A 最新版本是 v1.0.1（2026-05-26），v1.0.0 於 2026-03-12 發布。v1.0 把 spec 拆成三層：以 Protocol Buffers 定義的 canonical data model（`a2a.proto` 是唯一的 normative 來源）、抽象操作，以及 JSON-RPC、gRPC、HTTP+JSON 三種 binding。操作包含 `SendMessage`（預設會等到 task 進入終態或中斷態才回傳，可設定立即回傳）、`SendStreamingMessage`、`GetTask`、`ListTasks`（v1.0 新增，cursor 分頁）、`CancelTask`、`SubscribeToTask`、push notification config 的增刪查，以及需要認證的 `GetExtendedAgentCard`。v1.0 的 breaking changes 包括：OAuth 移除 implicit 與 password flow、新增 device code 與 PKCE；拼法統一為 `canceled`；移除 `TaskStatusUpdateEvent` 的 `final` 欄位；擴充名片的能力旗標移到 `AgentCapabilities.extendedAgentCard`。v0.3 起 well-known 路徑改為 `/.well-known/agent-card.json`，並加入名片簽章。版本以 `A2A-Version` header 協商，extension 以 `A2A-Extensions` header 宣告。spec 也規定 server 不得區分「task 不存在」與「沒有權限」。早期 0.x 版本的 JSON 以小寫連字號表示狀態（如 `input-required`），v1.0 的 proto 以 enum 定義（如 `INPUT_REQUIRED`、`AUTH_REQUIRED`），本章程式沿用前者以便閱讀，正式欄位名稱與序列化方式以 spec 為準。治理上，公開資料指出 A2A 已移交 Linux Foundation（移交時間以官方公告為準），spec 頁面也標示將加入 Agentic AI Foundation。框架方面，Google ADK、Microsoft Agent Framework、Strands Agents、AG2 都有 A2A 支援，Amazon Bedrock AgentCore Runtime 與 Google 的 agent 託管平台也能部署 A2A agent。

## 15.6 AG-UI：把 agent 的一舉一動變成前端事件

回到 Iris 的事故三：店家盯著轉圈圈四十秒，最後才看到一大段文字。第 4 章談過 streaming 能改善第一個字出現的時間，但那一章的串流只發生在模型與 harness 之間；harness 收完片段、組裝成完整回應後，前端仍然什麼都不知道。前端真正需要的資訊比模型的文字片段多得多：agent 開始呼叫哪個 tool、參數是什麼、tool 跑完了沒、共享的狀態（例如理賠面板）改變了什麼、agent 是否在等使用者核准。每個框架各自發明一套串流格式，前端元件就只能綁死在某一個框架上。

**AG-UI** 的做法是定義一組與框架無關的**事件**（event）：前端用一次 HTTP 請求開始一個 run，請求裡帶著 thread id（對話串的 id）、run id、目前的訊息、前端提供的 tools 與共享 state；後端在回應中用 SSE 持續送出事件，直到 run 結束。事件是單向、有順序的串流，不是一來一回的 RPC，所以前端的工作很單純：依序把每個事件套用到畫面狀態上。這和前端常見的 reducer 模式完全一樣：畫面是事件序列 fold（依序累積）出來的結果。

```text
 agent loop 內部（第 4 章）              AG-UI 事件（送往前端）        前端畫面
 ───────────────────────────            ─────────────────────────     ──────────────────
 run 開始                          ──►  RUN_STARTED                   顯示「處理中」
 送出目前共享 state                ──►  STATE_SNAPSHOT                畫出理賠面板
 模型吐出文字片段                  ──►  TEXT_MESSAGE_START            新增一個對話泡泡
                                        TEXT_MESSAGE_CONTENT × n      泡泡裡的字逐段長出
                                        TEXT_MESSAGE_END              泡泡完成
 模型要求 tool（參數串流）         ──►  TOOL_CALL_START               新增「查理賠進度」卡片
                                        TOOL_CALL_ARGS × n            卡片顯示準備中的參數
                                        TOOL_CALL_END                 參數完整，卡片轉為執行中
 harness 執行 tool、回填結果       ──►  TOOL_CALL_RESULT              卡片標示完成
 tool 改變了共享 state             ──►  STATE_DELTA（JSON Patch）     面板上的狀態更新
 需要人核准或前端執行的 tool       ──►  RUN_FINISHED（等待外部輸入） 顯示上傳元件或核准按鈕
 run 失敗                          ──►  RUN_ERROR                     顯示錯誤與重試
```

這張資料流圖的左欄是第 4 章已經寫過的 loop 步驟，中欄是對應的事件，右欄是前端拿到事件後的反應。重點有三個。第一，文字與 tool call 都用「開始、內容、結束」三段式：開始事件帶 id，內容事件用同一個 id 追加片段，結束事件宣告完整。這讓前端能同時處理多則訊息與多個 tool call，也讓前端知道何時可以安全地解析 tool 參數（第 4 章講過，參數在結束前不是合法 JSON）。第二，tool 的執行結果與 state 變化是 harness 才有的資訊，模型的串流裡沒有，所以 AG-UI 是 harness 對外的串流，不是把模型串流原封不動轉發。第三，run 的結束要有明確的事件，前端才能區分「結束了」「失敗了」與「在等我」。

| 事件家族 | 代表事件 | 前端用來做什麼 | 設計重點 |
|---|---|---|---|
| 生命週期 | RUN_STARTED、RUN_FINISHED、RUN_ERROR、STEP_STARTED／FINISHED | 進度條、處理中狀態、錯誤提示 | 每個 run 一定以結束或錯誤事件收尾 |
| 文字訊息 | TEXT_MESSAGE_START／CONTENT／END | 對話泡泡逐字顯示 | 同一 messageId 的片段依序追加 |
| Tool call | TOOL_CALL_START／ARGS／END／RESULT | tool 進度卡片、前端執行的 tool | 參數到 END 才解析；RESULT 可能很晚才到 |
| 共享 state | STATE_SNAPSHOT、STATE_DELTA、MESSAGES_SNAPSHOT | 側邊面板、表單、清單同步 | snapshot 覆蓋，delta 用 JSON Patch 增量更新 |
| 推理與擴充 | reasoning 事件、RAW、CUSTOM | 顯示思考摘要、承載框架特有資料 | CUSTOM 讓協定不必為每個需求加新事件 |

這張表的最後一列提醒一件事：協定不可能涵蓋所有產品需求，所以留了 CUSTOM 與 RAW 事件作為逃生口。逃生口好用，但用多了就會回到「前端綁死特定後端」的老問題。原則是：能用標準事件表達的就用標準事件，例如理賠進度應該放在共享 state 裡用 STATE_DELTA 更新，而不是自創一個 `CLAIM_UPDATED` 事件。

AG-UI 有兩個機制特別值得在設計時用上。第一是**前端 tool**（frontend tool）：由前端宣告、由前端執行的 tool。例如 `request_photo_upload`：agent 決定要請店家上傳照片時，就呼叫這個 tool，後端不執行它，而是把 tool call 事件送到前端，前端顯示上傳元件；店家上傳完，前端把結果當成 tool 結果，開始下一個 run 帶回後端。這讓 agent 可以「操作畫面」，而不必讓後端知道畫面怎麼長。要注意的是，前端 tool 的結果來自瀏覽器，等同使用者輸入，後端必須當成不可信的資料驗證，不能因為它的格式是 tool 結果就信任它。

第二是 **interrupt**（中斷）：run 需要人的決定才能繼續時，例如退款前需要客服按下核准，後端以中斷的形式結束目前的 run，前端顯示核准介面，使用者決定後再恢復。這和 A2A 的 input-required、auth-required 是同一類概念，只是發生在不同的邊上：A2A 的中斷是「遠端 agent 在等我」，AG-UI 的中斷是「我的 agent 在等使用者」。在青鳥的系統裡，兩者常常串在一起：快航的 task 進入 input-required，青鳥的 agent 把它翻成一個前端 tool 呼叫或 interrupt，請店家上傳照片。第 21 章會把核准流程做成完整的 approval policy engine；本章關心的是這些中斷怎麼在協定上表達。

> [!tip] 斷線重連
> AG-UI 的事件流是單向的，網路一斷，前端就漏掉事件。比較穩健的設計是：後端把每個 run 的事件寫進 durable log（第 22 章），前端重連時先拿一次 snapshot（state 與 messages 的完整快照），再從斷點之後接續 delta。只靠「重新整理就重跑一次 run」是危險的，因為 run 可能已經執行了有副作用的 tool。

## 15.7 共享 state 與 generative UI

很多 agent 介面不只是對話泡泡。青鳥的店家後台在對話旁邊有一個理賠面板，列出每張理賠的狀態與缺件；客服人員的 copilot 旁邊有一份回覆草稿，agent 會邊想邊改，客服也可以直接修改。這些資料是 agent 與前端共同擁有的，AG-UI 稱為**共享 state**（shared state）。同步它的方式有兩種事件：**STATE_SNAPSHOT** 送出完整狀態，前端直接覆蓋；**STATE_DELTA** 只送變化，格式是 **JSON Patch**（RFC 6902 定義的 JSON 差異格式，每個操作是「對某個路徑 add、replace 或 remove」），例如 `{"op": "replace", "path": "/claims/B-2077/state", "value": "input-required"}`。

為什麼需要兩種？只用 snapshot，每次小改動都要重送整份狀態，狀態一大就浪費頻寬，前端也很難做平滑的局部更新。只用 delta，一旦漏收一個 delta，之後的每一個 delta 都可能套在錯的基礎上，畫面就會默默地錯下去。正確的組合是：run 開始時送一次 snapshot，之後送 delta；前端套用 delta 失敗時不要硬套，而是要求重新同步。下面用最小版的 JSON Patch 示範正常套用與漏收後的失敗。

```python
from __future__ import annotations

import copy
import json


class PatchError(Exception):
    pass


def _walk(doc, path: str):
    """把 JSON Pointer（如 /claims/B-2077/state）拆成「父節點＋最後一段 key」。"""
    parts = [p.replace("~1", "/").replace("~0", "~") for p in path.lstrip("/").split("/")]
    for p in parts[:-1]:
        if isinstance(doc, dict) and p not in doc:
            raise PatchError(f"路徑不存在：{path}")
        doc = doc[int(p)] if isinstance(doc, list) else doc[p]
    return doc, parts[-1]


def apply_patch(state: dict, ops: list[dict]) -> dict:
    """最小版 JSON Patch（RFC 6902 的 add／replace／remove）；任何一步失敗就整批作廢。"""
    new = copy.deepcopy(state)                    # 先在副本上套用：失敗時前端畫面不會停在半套狀態
    for op in ops:
        parent, key = _walk(new, op["path"])
        if op["op"] == "add":
            parent[key] = op["value"]
        elif op["op"] == "replace":
            if key not in parent:
                raise PatchError(f"replace 的目標不存在：{op['path']}")
            parent[key] = op["value"]
        elif op["op"] == "remove":
            del parent[key]
    return new


# 前端先收到一次完整 snapshot，之後只收 delta
state = {"claims": {}, "draft_reply": ""}
deltas = [
    [{"op": "add", "path": "/claims/B-2077", "value": {"state": "working", "carrier": "快航"}}],
    [{"op": "replace", "path": "/claims/B-2077/state", "value": "input-required"},
     {"op": "add", "path": "/claims/B-2077/need", "value": "破損照片"}],
    [{"op": "replace", "path": "/draft_reply", "value": "請上傳外箱照片"}],
]
for i, ops in enumerate(deltas, 1):
    state = apply_patch(state, ops)
    print(f"delta {i}: {json.dumps(state, ensure_ascii=False)}")

# 漏收一個 delta（例如斷線重連），下一個 delta 的路徑對不上：不能硬套，要重新要 snapshot
try:
    apply_patch({"claims": {}, "draft_reply": ""}, deltas[1])
except PatchError as exc:
    print("套用失敗:", exc, "→ 向後端要求 STATE_SNAPSHOT 重新同步")
assert state["claims"]["B-2077"] == {"state": "input-required", "carrier": "快航", "need": "破損照片"}
```

```text
delta 1: {"claims": {"B-2077": {"state": "working", "carrier": "快航"}}, "draft_reply": ""}
delta 2: {"claims": {"B-2077": {"state": "input-required", "carrier": "快航", "need": "破損照片"}}, "draft_reply": ""}
delta 3: {"claims": {"B-2077": {"state": "input-required", "carrier": "快航", "need": "破損照片"}}, "draft_reply": "請上傳外箱照片"}
套用失敗: 路徑不存在：/claims/B-2077/state → 向後端要求 STATE_SNAPSHOT 重新同步
```

前三行是三個 delta 依序套用後的狀態：第一個新增 B-2077 的理賠，第二個把狀態改成 input-required 並加上缺件說明，第三個更新回覆草稿。注意第二個 delta 有兩個操作，`apply_patch` 先在副本上套用，全部成功才換掉原狀態，所以前端畫面不會停在「狀態改了、缺件說明還沒加」的半套狀態。最後一行模擬漏收：前端只拿到初始狀態，就直接套用第二個 delta，`/claims/B-2077/state` 的父節點不存在，套用失敗。這時正確的反應是要一次 snapshot，而不是忽略錯誤或自己猜一個值補上。

共享 state 是雙向的：店家在面板上修改回覆草稿，前端在下一個 run 的輸入中帶著新的 state，agent 就看到修改後的版本。雙向帶來衝突問題：agent 正在改草稿的同時，客服也在改同一段。常見的做法是把 state 依擁有者分區（agent 只寫建議區、人只寫定稿區），或在 state 上加版本號，衝突時以人的修改為準。不要讓兩方同時無條件覆寫同一個欄位。

更進一步，agent 不只更新資料，還決定「顯示什麼介面」，這叫 **generative UI**（生成式介面）。例如店家問「這個月哪些理賠還卡著？」，agent 不是回一段文字，而是讓畫面出現一張可以排序的表格，每列有「補件」按鈕。依「agent 能決定多少」可以分成三種做法：

| 類型 | agent 決定什麼 | 例子 | 優點 | 風險與代價 |
|---|---|---|---|---|
| 靜態元件 | 呼叫哪個預先寫好的元件、填什麼 props | tool call `show_claim_table` 對應前端的理賠表格元件 | 最安全、品牌一致、容易測試 | 每種介面都要先寫好，彈性最低 |
| 宣告式 UI | 用 JSON 描述版面，從允許的元件目錄中組合 | agent 輸出「卡片＋表格＋按鈕」的結構描述，前端渲染 | 彈性與安全的平衡，跨平台可渲染 | 元件目錄要維護；props 要驗證 |
| 開放式 UI | 由 agent 或工具 server 產生 HTML 等完整介面 | 工具 server 提供一個互動式地圖，在 sandboxed iframe 中顯示 | 彈性最高，第三方可以提供介面 | 必須隔離執行；外觀不一致；最難審查 |

這張表從上到下，agent 的自由度遞增，安全邊界也越來越難守。靜態元件是多數產品的起點：tool call 的名稱就是元件名稱，參數就是 props，前端用 15.6 節的 tool call 事件就能渲染。宣告式 UI 讓 agent 能組合新的版面，但元件只能從 allowlist 的目錄裡挑，props 要用 schema 驗證，前端不執行任何 agent 產生的程式碼。開放式 UI 讓第三方（例如第 14 章提到的 MCP Apps）提供完整介面，前提是放進隔離的 iframe，限制它能呼叫的 API，並且所有從介面發出的動作都要回到後端重新授權。

> [!warning] 常見誤解
> 「generative UI 就是讓模型產生 HTML 然後顯示出來。」直接把模型輸出的 HTML 放進主頁面，等同讓任何能影響模型輸入的人（例如在訂單備註裡藏指令的攻擊者，第 31 章的 indirect prompt injection）在你的網站上執行腳本、偽造按鈕。生成的介面要嘛只從允許的元件目錄組合，要嘛放在隔離的 iframe 裡；而且介面上的任何按鈕，觸發的都只是「請後端做某件事」的請求，後端照樣要檢查權限與核准規則。

> [!note] 2026 現況
> 截至 2026 年 10 月，AG-UI 由 CopilotKit 發起並以開源社群方式維護，1.0.0 於 2026-09-17 同步發布 TypeScript、Python、.NET 三種實作，1.0.1（2026-09-29）讓 client 能重新連上帶有未完成 interrupt 的 thread。1.0 的 run 終態事件帶有 usage 與 outcome 資訊，0.x 的名稱保留為 deprecated alias；除了 SSE，也支援 protobuf 編碼。公開資料顯示的整合包括 LangGraph、CrewAI、Mastra、Strands Agents、Google ADK、Microsoft Agent Framework、Claude Agent SDK、Spring AI、LlamaIndex 等，另有 MCP Apps、A2UI 與 A2A 的 middleware。A2UI 是 Google 提出的宣告式介面格式，AG-UI 以 middleware 方式承載。本章使用的事件名稱依 AG-UI 公開文件整理，部分事件的確切欄位（例如 step 與 reasoning 事件、`outcome` 的取值）請以官方 schema 為準；程式中 `outcome` 的取值為本書簡化。

## 15.8 Agent payments：當 agent 要替人付錢

阿哲接著提出下一個需求：店家同意理賠後，快航要收一筆加急取件費；店家也希望 agent 能直接替店家購買退貨的物流單。一旦 agent 要付錢，前面所有的信任問題都被放大。商家會問：這個 agent 代表誰？使用者真的同意了這筆金額嗎？使用者交代的是「買一張退貨單」，agent 卻結帳了三張，責任在誰？付款憑證會不會在 agent 的 context 裡被偷走？傳統線上付款假設「按下付款鈕的是本人」，agent 讓這個假設失效了。

這一節只做概念與信任模型的概覽：付款流程、金流法規與卡組織規則牽涉很廣，實作時要以各協定的正式規格與支付服務商的要求為準。核心觀念是，現有的 agent payments 協定大致分在三個層次，各自回答不同的信任問題。

```text
 使用者（店家）
   │ (1) 意圖與授權：「退貨單可自動購買，每張上限 120 元，本月最多 30 張」
   │     → 以可驗證、可稽核的方式簽署（授權證明層，例如 AP2 的 mandate）
   ▼
 青鳥 agent ──(2) 商務流程：建立 checkout、確認品項與總價 ──► 快航（商家）
   │            （商務流程層，例如 ACP、UCP 的 checkout）          │
   │                                                              │
   │ (3) 付款：送出受限的付款憑證（token 化、限額、限商家）       │
   │     （或對付費 API 走 HTTP 402 挑戰與回應，例如 x402、MPP）  │
   ▼                                                              ▼
 支付服務商／憑證提供者 ◄──── 驗證授權鏈：金額、商家、期限 ────► 清算、收據
   │
   └─► 每一層留下稽核紀錄：誰授權、授權了什麼、實際付了什麼
```

這張圖由上往下是一筆 agent 付款的信任鏈。第 (1) 層是**授權證明**：使用者事先或當下表達意圖與限制，而且要以商家與支付方都能驗證的方式記錄下來，不能只是 agent 自己說「使用者同意了」。AP2 用**可驗證數位憑證**（verifiable digital credential，經過簽章、第三方可以驗證真偽的數位文件）組成授權鏈，稱為 **mandate**（授權書）。第 (2) 層是**商務流程**：agent 與商家之間怎麼建立購物車、確認價格、結帳、追蹤訂單，ACP 與 UCP 主要定義這一層。第 (3) 層是**付款傳輸**：真正把錢付出去的機制。對一般商品，常見做法是傳遞一個受限的付款 token（只能用在特定商家、特定金額內），agent 本身從不經手卡號；對按次計費的 API，x402 與 MPP 利用 HTTP 的 402（Payment Required）狀態碼：server 回應「要付多少、怎麼付」，client 附上付款證明重送請求。

| 協定 | 主要層次 | 解決的問題 | 一句話理解 |
|---|---|---|---|
| AP2（Agent Payments Protocol） | 授權證明 | 商家與支付方如何驗證「使用者真的授權了這筆」 | 用可驗證的 mandate 串起從意圖到付款的授權鏈 |
| ACP（Agentic Commerce Protocol） | 商務流程 | agent 如何與商家完成 checkout，並安全地傳遞付款 token | 商家仍是交易的賣方，agent 不經手金流 |
| UCP（Universal Commerce Protocol） | 商務流程 | 商家如何宣告可被 agent 使用的商務能力 | 能力加擴充的標準，與傳輸方式無關 |
| x402、MPP | 付款傳輸 | 機器對機器、按次或按量付費 | 用 HTTP 402 挑戰與回應完成小額付款 |

讀這張表時要記得，這些協定彼此不是競爭關係，而是可以疊在一起：授權證明可以作為 A2A、MCP 或商務協定的 extension，商務流程可以跑在 REST、MCP 或 A2A 上，付款傳輸則可以是卡片 token 或 HTTP 402。對 framework 設計者來說，這張表也指出一件事：**tool 層不需要懂每一種付款協定，只需要把「需要付款」抽象成一個中斷**。agent 走到要付錢的步驟時，進入類似 A2A `auth-required` 的狀態；由獨立的付款元件檢查授權範圍（金額、商家、次數、期限）、在範圍外時找人核准、在範圍內時取得受限憑證，再讓 task 繼續。

付款情境還要區分 **human-present**（使用者在場，當下確認）與 **human-not-present**（使用者事先授權，agent 之後自行執行）。前者的信任來源是當下的確認，風險在於 approval fatigue（第 21 章）；後者的信任來源是事先簽署的限制，風險在於限制寫得太寬。依第 1 章的 autonomy 分級，「每張 120 元以內的退貨單自動購買」是有邊界的自主（L4），超出邊界就要回到 L3 由人核准；而付款本身是不容易回復的動作，所以每一筆都要有 idempotency key（同一張退貨單不論重試幾次只付一次）與完整的稽核紀錄。

> [!warning] 常見誤解
> 「把信用卡號或支付 API key 放進 agent 能用的 tool 參數，限制模型只在必要時使用。」這讓付款能力的邊界完全依賴模型的判斷，而且憑證會出現在 context、trace 與 log 裡。正確的做法是 agent 永遠只拿到受限、可撤銷、綁定商家與金額的 token，真正的憑證留在支付服務商或獨立的付款元件；限額檢查用確定性程式做，不靠 prompt。

> [!note] 2026 現況
> 截至 2026 年 10 月，依各協定公開的規格與 repository：AP2 由 Google 發起（2025-09 宣布），目前為 v0.2，已捐給 FIDO Alliance 標準化；v0.2 官網以 Checkout Mandate 與 Payment Mandate、各分 Open／Closed 兩階段描述授權，與早期常見的 Intent／Cart／Payment mandate 說法不同，實作請以最新 spec 為準，並支援 human-present 與 human-not-present 兩種模式。ACP 由 OpenAI 與 Stripe 維護，仍為 beta，最新穩定版為 2026-04-17，規格分為 agentic checkout 與 delegated payment 兩部分。UCP 有 draft 與版本化文件，定義 checkout、identity linking、order、payment token exchange 等能力。x402 由 Coinbase 發起、已移交 x402 Foundation，以 `PAYMENT-REQUIRED`、`PAYMENT-SIGNATURE`、`PAYMENT-RESPONSE` header 完成流程；MPP（Machine Payments Protocol）提供 charge、session（可按量計費）、subscription 等模式，並可與 x402 互通。Amazon Bedrock AgentCore 的 Payments 功能支援 x402 與 MPP，並可設定支出上限。另外要注意縮寫衝突：ACP 也被用來指 Zed 發起的 Agent Client Protocol（編輯器與 coding agent 之間的協定），以及 IBM 的 Agent Communication Protocol（公開報導指出已宣布併入 A2A），閱讀資料時要確認指的是哪一個。

## 15.9 動手做：A2A task 狀態機與 AG-UI 事件串流

這一節把 15.3 到 15.7 節的概念組成兩段可以單獨執行的程式。第一段是快航理賠 agent 的 A2A 風格 server：task 由 server 產生 id，所有狀態變化都經過合法轉移檢查，兩個中斷態分別處理補件與授權，並示範五種必須被擋下的違規操作。第二段是青鳥客服 agent 的 AG-UI 風格後端：用 ScriptedModel 驅動 agent loop，把每個動作翻成事件，用 SSE 格式送出；前端解析事件、驗證順序，把事件 fold 成畫面。兩段程式合起來，就是 Iris 三個事故的正確版本。

### 第一段：含中斷態的 A2A task 狀態機

程式的結構分三塊。`TaskStore` 是唯一能改 task 狀態的地方，`transition()` 依 15.4 節的轉移表檢查每次轉移，並把狀態變化記成事件（真實系統中這些事件會推給串流訂閱者或 webhook）。`ClaimAgentServer` 模擬快航的理賠 agent：它的內部邏輯對青鳥是黑盒子，青鳥只看得到 task 狀態、狀態訊息與 artifact。最後是青鳥這一端的 `resolve_interrupt()`，把兩種中斷態翻成「該去找誰」。注意授權的處理方式：憑證透過 `credentials` 參數傳遞，代表 HTTP 層的 Authorization header，而不是塞進訊息的 parts 裡。

```python
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

# ───────── A2A 風格的 task 狀態機（伺服端）─────────
TERMINAL = {"completed", "failed", "canceled", "rejected"}
INTERRUPTED = {"input-required", "auth-required"}
ALLOWED = {
    "submitted": {"working", "rejected", "canceled", "failed"},
    "working": {"input-required", "auth-required", "completed", "failed", "canceled"},
    "input-required": {"working", "canceled", "failed"},
    "auth-required": {"working", "canceled", "failed"},
}


class A2AError(Exception):
    code = "error"


class InvalidTransition(A2AError):
    code = "invalid_transition"


class TaskNotFound(A2AError):
    code = "task_not_found"


class TaskNotCancelable(A2AError):
    code = "task_not_cancelable"


@dataclass
class Task:
    id: str
    context_id: str
    owner: str                                   # 哪個租戶建立的；查詢時用來做存取控制
    state: str = "submitted"
    status_message: str = ""
    history: list[dict] = field(default_factory=list)
    artifacts: list[dict] = field(default_factory=list)


class TaskStore:
    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}
        self.events: list[dict] = []             # 推給 streaming 訂閱者的 status／artifact 事件
        self._ids = itertools.count(1)

    def create(self, owner: str, context_id: str | None) -> Task:
        n = next(self._ids)
        task = Task(id=f"t-{n}", context_id=context_id or f"ctx-{n}", owner=owner)   # id 一律由 server 產生
        self.tasks[task.id] = task
        self.events.append({"kind": "status", "task": task.id, "state": "submitted"})
        return task

    def get(self, task_id: str, caller: str) -> Task:
        task = self.tasks.get(task_id)
        if task is None or task.owner != caller:  # 不存在與沒權限回同一個錯，避免被拿來探測 task id
            raise TaskNotFound(f"找不到 task {task_id}")
        return task

    def transition(self, task: Task, dst: str, note: str = "") -> None:
        if task.state in TERMINAL:
            raise InvalidTransition(f"{task.id} 已是 {task.state}，終態不可再變")
        if dst not in ALLOWED[task.state]:
            raise InvalidTransition(f"{task.id}：{task.state} → {dst} 不合法")
        task.state, task.status_message = dst, note
        self.events.append({"kind": "status", "task": task.id, "state": dst, "note": note})

    def add_artifact(self, task: Task, name: str, data: dict) -> None:
        task.artifacts.append({"name": name, "parts": [{"data": data}]})
        self.events.append({"kind": "artifact", "task": task.id, "name": name})


# ───────── 快航物流的理賠 agent（對青鳥而言是黑盒子）─────────
class ClaimAgentServer:
    REQUIRED_SCOPE = "claims:write"

    def __init__(self) -> None:
        self.store = TaskStore()

    def send_message(self, caller: str, parts: list[dict], task_id: str | None = None,
                     context_id: str | None = None, credentials: dict | None = None) -> Task:
        """對應 SendMessage：沒帶 task_id 就開新 task；帶了就是對既有 task 補件。"""
        if task_id is None:
            task = self.store.create(caller, context_id)
            self.store.transition(task, "working", "已受理")
        else:
            task = self.store.get(task_id, caller)
            if task.state in TERMINAL:
                raise InvalidTransition(f"{task.id} 已是 {task.state}；請在 {task.context_id} 開新 task")
            if task.state in INTERRUPTED:
                self.store.transition(task, "working", "收到補件，繼續處理")
        task.history.append({"role": "user", "parts": parts})
        self._advance(task, credentials or {})
        return task                              # 預設 block 到終態或中斷態才回傳

    def _advance(self, task: Task, credentials: dict) -> None:
        got = [p for m in task.history for p in m["parts"]]
        if not any(p.get("mime") == "image/jpeg" for p in got):
            self.store.transition(task, "input-required", "請提供外箱破損照片（image/jpeg）")
            return
        if self.REQUIRED_SCOPE not in credentials.get("scopes", []):
            # 授權不放在訊息內容裡：要求 client 走 OAuth 拿到帶 scope 的 token，再從傳輸層帶過來
            self.store.transition(task, "auth-required", f"需要店家授權 scope {self.REQUIRED_SCOPE}")
            return
        self.store.add_artifact(task, "claim-receipt", {"claim_id": "KH-CL-5521", "amount_cap": 1500})
        self.store.transition(task, "completed", "理賠已立案，3 個工作天內審核")

    def cancel_task(self, caller: str, task_id: str) -> Task:
        task = self.store.get(task_id, caller)
        if task.state == "canceled":
            return task                          # 重複取消是 idempotent：不報錯也不重複產生事件
        if task.state in TERMINAL:
            raise TaskNotCancelable(f"{task.id} 已是 {task.state}，不能取消")
        self.store.transition(task, "canceled", "client 取消")
        return task


# ───────── 青鳥客服 agent 這一端：把中斷態翻成「該去找誰」─────────
def resolve_interrupt(task: Task) -> tuple[dict, list[dict]]:
    if task.state == "input-required":
        print(f"   → 青鳥：轉給店家補件「{task.status_message}」")
        return {}, [{"mime": "image/jpeg", "file": "box-B2077.jpg"}]
    if task.state == "auth-required":
        print(f"   → 青鳥：請店家在快航的授權頁同意 {ClaimAgentServer.REQUIRED_SCOPE}")
        return {"scopes": ["claims:read", "claims:write"]}, [{"text": "已完成授權"}]
    raise ValueError(task.state)


server = ClaimAgentServer()
creds: dict = {}
task = server.send_message("bluebird", [{"text": "訂單 B-2077 外箱壓壞，申請理賠"}])
while task.state in INTERRUPTED:
    print(f"[{task.id}] 停在 {task.state}")
    creds, parts = resolve_interrupt(task)
    task = server.send_message("bluebird", parts, task_id=task.id, credentials=creds)
print(f"[{task.id}] 結束於 {task.state}：{task.status_message}")
print("artifact :", task.artifacts[0]["parts"][0]["data"])
print("事件串流 :", " → ".join(e["state"] if e["kind"] == "status" else "artifact" for e in server.store.events))
assert task.state == "completed" and len(task.history) == 3

# 違規操作：每一個都要被拒絕，而且錯誤碼要能讓 client 判斷下一步
attempts = {
    "對已完成的 task 補件": lambda: server.send_message("bluebird", [{"text": "再補一張"}], task_id="t-1"),
    "直接把終態改回 working": lambda: server.store.transition(task, "working"),
    "別的租戶查 t-1": lambda: server.store.get("t-1", "other-shop"),
    "查不存在的 t-99": lambda: server.store.get("t-99", "bluebird"),
    "取消已完成的 task": lambda: server.cancel_task("bluebird", "t-1"),
}
for label, attempt in attempts.items():
    try:
        attempt()
        print(f"  沒擋住！{label}")
    except A2AError as exc:
        print(f"  {exc.code:<19} {label}｜{exc}")

# 同一個 contextId 開第二張 task，然後取消兩次
t2 = server.send_message("bluebird", [{"text": "B-2077 另一箱也壞了"}], context_id=task.context_id)
first, second = server.cancel_task("bluebird", t2.id), server.cancel_task("bluebird", t2.id)
print(f"[{t2.id}] context={t2.context_id} 取消兩次後：{second.state}，事件數 "
      f"{sum(1 for e in server.store.events if e['task'] == t2.id)}")
assert t2.context_id == task.context_id and second.state == "canceled"
assert sum(1 for e in server.store.events if e["task"] == t2.id and e["state"] == "canceled") == 1
```

```text
[t-1] 停在 input-required
   → 青鳥：轉給店家補件「請提供外箱破損照片（image/jpeg）」
[t-1] 停在 auth-required
   → 青鳥：請店家在快航的授權頁同意 claims:write
[t-1] 結束於 completed：理賠已立案，3 個工作天內審核
artifact : {'claim_id': 'KH-CL-5521', 'amount_cap': 1500}
事件串流 : submitted → working → input-required → working → auth-required → working → artifact → completed
  invalid_transition  對已完成的 task 補件｜t-1 已是 completed；請在 ctx-1 開新 task
  invalid_transition  直接把終態改回 working｜t-1 已是 completed，終態不可再變
  task_not_found      別的租戶查 t-1｜找不到 task t-1
  task_not_found      查不存在的 t-99｜找不到 task t-99
  task_not_cancelable 取消已完成的 task｜t-1 已是 completed，不能取消
[t-2] context=ctx-1 取消兩次後：canceled，事件數 4
```

逐段解說這份輸出。

**前五行是正常的理賠流程。** 青鳥送出第一則訊息，server 建立 `t-1` 並立刻接受；因為訊息裡沒有照片，task 停在 input-required，`SendMessage` 在中斷態就回傳，不會一直 block。青鳥的 agent 把狀態訊息轉給店家，拿到照片後用同一個 task id 補件，task 回到 working，接著因為缺少 `claims:write` 授權停在 auth-required。店家完成 OAuth 同意後，青鳥帶著新的憑證再送一次，task 產出理賠單 artifact 並進入 completed。第六行的 artifact 是對帳系統真正要讀的資料。

**第七行是事件串流。** 從 submitted 到 completed，每一次轉移都留下一個事件，artifact 事件出現在 completed 之前。這個順序很重要：client 收到 completed 時，必須已經拿得到 artifact，否則會出現「任務完成、卻查不到結果」的空窗。這串事件也是第 29 章 tracing 的材料：兩個中斷態各停了多久，就是這張理賠單在等誰、等多久。

**接下來五行是被擋下的違規操作**，每一個都帶著機器可讀的錯誤碼。對已完成的 task 補件得到 `invalid_transition`，錯誤訊息直接指出該在 `ctx-1` 開新 task；直接把終態改回 working 同樣被擋。兩個 `task_not_found` 值得對照：別的租戶查 `t-1`，與任何人查不存在的 `t-99`，得到的錯誤完全相同，攻擊者無法藉此判斷某個 task id 是否存在。取消已完成的 task 得到 `task_not_cancelable`，因為完成的理賠不能被「取消」成另一個終態。

**最後一行是 contextId 與 idempotent 取消。** 店家發現另一箱也壞了，青鳥在同一個 `ctx-1` 開了 `t-2`，它和 `t-1` 是兩張獨立的理賠，但屬於同一組脈絡。`t-2` 被連續取消兩次，第二次直接回傳已取消的 task，不報錯也不產生新事件；`t-2` 的四個事件是 submitted、working、input-required、canceled，assert 也確認 canceled 事件只有一個。重複取消在真實世界很常見：使用者連點兩下、client 逾時重試，如果第二次報錯，client 就會誤以為取消失敗。

### 第二段：AG-UI 風格的事件串流與前端

這段程式的後端 `run_agent()` 就是第 4 章的 loop，多了一個 `emit` 參數：loop 的每個動作都送出對應的事件。tools 分成兩類：`check_claim` 是後端 tool，代表去查快航的 A2A task；`request_photo_upload` 是前端在 run 輸入中宣告的前端 tool，後端不執行，只把 tool call 送給前端。事件先編碼成 SSE 的 `data:` 行，再由前端解析，模擬真實的網路邊界。前端的 `FrontendView` 一邊驗證事件順序，一邊維護三種畫面狀態：對話泡泡、tool 卡片與共享 state 面板。

```python
from __future__ import annotations

import copy
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


def say(text: str) -> ModelResponse:
    """劇本小工具：產生一個「直接回答並結束」的回應。"""
    return ModelResponse(text=text)


def chunks(s: str, n: int) -> list[str]:
    return [s[i:i + n] for i in range(0, len(s), n)]


# ───────── 後端：把 agent loop 的每個動作翻成 AG-UI 風格事件 ─────────
def check_claim(order_id: str) -> dict:
    """後端 tool：實際上是去 GetTask 查快航的 A2A task（這裡直接回傳快照）。"""
    return {"order_id": order_id, "task": "t-1", "state": "input-required", "need": "外箱破損照片"}


BACKEND_TOOLS = {"check_claim": check_claim}


def run_agent(model: ScriptedModel, run_input: dict, emit: Callable[[dict], None]) -> list[dict]:
    thread, run = run_input["threadId"], run_input["runId"]
    messages = list(run_input["messages"])
    frontend_tools = {t["name"] for t in run_input["tools"]}       # 前端宣告、由前端執行的 tools
    state = copy.deepcopy(run_input["state"])
    emit({"type": "RUN_STARTED", "threadId": thread, "runId": run})
    emit({"type": "STATE_SNAPSHOT", "snapshot": state})
    for step in range(1, 6):
        resp = model.complete(messages, tools=run_input["tools"])
        mid = f"{run}-m{step}"
        if resp.text:
            emit({"type": "TEXT_MESSAGE_START", "messageId": mid, "role": "assistant"})
            for piece in chunks(resp.text, 8):                      # 模擬模型一小段一小段吐字
                emit({"type": "TEXT_MESSAGE_CONTENT", "messageId": mid, "delta": piece})
            emit({"type": "TEXT_MESSAGE_END", "messageId": mid})
        messages.append({"role": "assistant", "content": resp.text, "tool_calls": [vars(tc) for tc in resp.tool_calls]})
        if not resp.tool_calls:
            emit({"type": "RUN_FINISHED", "threadId": thread, "runId": run, "outcome": "success"})
            return messages
        pending = []
        for tc in resp.tool_calls:
            emit({"type": "TOOL_CALL_START", "toolCallId": tc.id, "toolCallName": tc.name, "parentMessageId": mid})
            for piece in chunks(json.dumps(tc.args, ensure_ascii=False), 12):
                emit({"type": "TOOL_CALL_ARGS", "toolCallId": tc.id, "delta": piece})
            emit({"type": "TOOL_CALL_END", "toolCallId": tc.id})
            if tc.name in frontend_tools:
                pending.append(tc.id)                               # 後端不執行，交給前端
                continue
            result = BACKEND_TOOLS[tc.name](**tc.args)
            content = json.dumps(result, ensure_ascii=False)
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": content})
            emit({"type": "TOOL_CALL_RESULT", "toolCallId": tc.id, "content": content})
            ops = [{"op": "add", "path": f"/claims/{result['order_id']}",
                    "value": {"state": result["state"], "need": result["need"]}}]
            emit({"type": "STATE_DELTA", "delta": ops})
        if pending:                                                 # 等前端執行完，下一個 run 帶結果回來
            emit({"type": "RUN_FINISHED", "threadId": thread, "runId": run, "outcome": "awaiting_frontend_tool"})
            return messages
    emit({"type": "RUN_ERROR", "message": "步數用完"})
    return messages


def to_sse(event: dict) -> str:
    return "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"


def from_sse(stream: str) -> list[dict]:
    return [json.loads(block[len("data: "):]) for block in stream.split("\n\n") if block.startswith("data: ")]


# ───────── 前端：驗證事件順序，並把事件 fold 成畫面狀態 ─────────
class ProtocolError(Exception):
    pass


class FrontendView:
    def __init__(self) -> None:
        self.bubbles: dict[str, str] = {}
        self.cards: dict[str, dict] = {}
        self.state: dict = {}
        self.open_msgs: set[str] = set()
        self.open_calls: set[str] = set()
        self.phase = "idle"

    def apply(self, ev: dict) -> None:
        t = ev["type"]
        if self.phase != "running" and t != "RUN_STARTED":
            raise ProtocolError(f"{t} 出現在 run 之外")
        if t == "RUN_STARTED":
            self.phase = "running"
        elif t == "TEXT_MESSAGE_START":
            self.open_msgs.add(ev["messageId"])
            self.bubbles[ev["messageId"]] = ""
        elif t == "TEXT_MESSAGE_CONTENT":
            if ev["messageId"] not in self.open_msgs:
                raise ProtocolError(f"訊息 {ev['messageId']} 沒有 START 就收到內容")
            self.bubbles[ev["messageId"]] += ev["delta"]          # 使用者看到字一段段長出來
        elif t == "TEXT_MESSAGE_END":
            self.open_msgs.discard(ev["messageId"])
        elif t == "TOOL_CALL_START":
            self.open_calls.add(ev["toolCallId"])
            self.cards[ev["toolCallId"]] = {"name": ev["toolCallName"], "args": "", "status": "準備參數"}
        elif t == "TOOL_CALL_ARGS":
            if ev["toolCallId"] not in self.open_calls:
                raise ProtocolError(f"tool call {ev['toolCallId']} 已結束或不存在")
            self.cards[ev["toolCallId"]]["args"] += ev["delta"]
        elif t == "TOOL_CALL_END":
            self.open_calls.discard(ev["toolCallId"])
            card = self.cards[ev["toolCallId"]]
            card["args"], card["status"] = json.loads(card["args"]), "執行中"   # 參數到齊才解析
        elif t == "TOOL_CALL_RESULT":
            self.cards[ev["toolCallId"]]["status"] = "完成"
        elif t == "STATE_SNAPSHOT":
            self.state = copy.deepcopy(ev["snapshot"])
        elif t == "STATE_DELTA":
            for op in ev["delta"]:                                  # 這裡只需要 add；完整版見 15.7 節
                *parents, key = op["path"].lstrip("/").split("/")
                node = self.state
                for p in parents:
                    node = node[p]
                node[key] = op["value"]
        elif t in ("RUN_FINISHED", "RUN_ERROR"):
            if self.open_msgs or self.open_calls:
                raise ProtocolError("run 結束時還有沒關閉的訊息或 tool call")
            self.phase = "idle"
            for card in self.cards.values():
                if card["status"] == "執行中" and ev.get("outcome") == "awaiting_frontend_tool":
                    card["status"] = "等使用者操作"


FRONTEND_TOOLS = [{"name": "request_photo_upload", "description": "在畫面上顯示上傳元件，請店家上傳照片",
                   "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}}}]

model = ScriptedModel([
    ModelResponse(text="我幫您查一下 B-2077 的理賠進度。",
                  tool_calls=[ToolCall("c1", "check_claim", {"order_id": "B-2077"})], stop_reason="tool_use"),
    ModelResponse(text="快航需要外箱破損照片才能繼續審核，請在下方上傳。",
                  tool_calls=[ToolCall("c2", "request_photo_upload", {"order_id": "B-2077"})], stop_reason="tool_use"),
    say("收到照片，已轉交快航，審核進度會顯示在右側面板。"),
])

wire: list[str] = []
run1 = {"threadId": "th-88", "runId": "r1", "state": {"claims": {}}, "tools": FRONTEND_TOOLS,
        "messages": [{"role": "user", "content": "B-2077 的破損理賠到哪了？"}]}
history = run_agent(model, run1, emit=lambda ev: wire.append(to_sse(ev)))
events = from_sse("".join(wire))
view = FrontendView()
for ev in events:
    view.apply(ev)

# 把連續相同的事件壓成「名稱×次數」，方便看順序
runs = [[e["type"], 1] for e in events[:1]]
for e in events[1:]:
    if e["type"] == runs[-1][0]:
        runs[-1][1] += 1
    else:
        runs.append([e["type"], 1])
print(f"run r1 共 {len(events)} 個事件：")
items = [f"{t}×{n}" if n > 1 else t for t, n in runs]
for i in range(0, len(items), 5):
    print("  " + " → ".join(items[i:i + 5]))
for mid, text in view.bubbles.items():
    print(f"  [對話] {mid}: {text}")
for cid, card in view.cards.items():
    print(f"  [卡片] {cid} {card['name']}({card['args']}) → {card['status']}")
print("  [面板]", json.dumps(view.state, ensure_ascii=False))

# 前端執行完自己的 tool（店家上傳照片），開新的 run 把結果帶回去
view.cards["c2"]["status"] = "完成"
run2 = dict(run1, runId="r2", state=view.state, messages=history + [
    {"role": "tool", "tool_call_id": "c2", "name": "request_photo_upload", "content": '{"uploaded": "box-B2077.jpg"}'}])
wire2: list[str] = []
run_agent(model, run2, emit=lambda ev: wire2.append(to_sse(ev)))
for ev in from_sse("".join(wire2)):
    view.apply(ev)
print("run r2:", view.bubbles["r2-m1"])

# 壞掉的串流：沒有 START 就送內容；前端要拒絕，而不是默默顯示
broken = [{"type": "RUN_STARTED", "threadId": "th-88", "runId": "r3"},
          {"type": "TEXT_MESSAGE_CONTENT", "messageId": "x", "delta": "哈囉"}]
try:
    v = FrontendView()
    for ev in broken:
        v.apply(ev)
except ProtocolError as exc:
    print("壞串流被拒絕:", exc)

assert view.cards["c2"]["status"] == "完成" and len(events) == 23
assert view.state["claims"]["B-2077"]["state"] == "input-required"
assert len(model.calls) == 3 and model.calls[2][-1]["role"] == "tool"
assert wire[0].startswith("data: {\"type\": \"RUN_STARTED\"")
```

```text
run r1 共 23 個事件：
  RUN_STARTED → STATE_SNAPSHOT → TEXT_MESSAGE_START → TEXT_MESSAGE_CONTENT×3 → TEXT_MESSAGE_END
  TOOL_CALL_START → TOOL_CALL_ARGS×2 → TOOL_CALL_END → TOOL_CALL_RESULT → STATE_DELTA
  TEXT_MESSAGE_START → TEXT_MESSAGE_CONTENT×3 → TEXT_MESSAGE_END → TOOL_CALL_START → TOOL_CALL_ARGS×2
  TOOL_CALL_END → RUN_FINISHED
  [對話] r1-m1: 我幫您查一下 B-2077 的理賠進度。
  [對話] r1-m2: 快航需要外箱破損照片才能繼續審核，請在下方上傳。
  [卡片] c1 check_claim({'order_id': 'B-2077'}) → 完成
  [卡片] c2 request_photo_upload({'order_id': 'B-2077'}) → 等使用者操作
  [面板] {"claims": {"B-2077": {"state": "input-required", "need": "外箱破損照片"}}}
run r2: 收到照片，已轉交快航，審核進度會顯示在右側面板。
壞串流被拒絕: 訊息 x 沒有 START 就收到內容
```

逐段解說這份輸出。

**前五行是 run r1 的 23 個事件**：第一行是標題，後四行把連續的相同事件壓成「×次數」。順序完全對應 15.6 節的資料流圖：run 開始、送出 state snapshot；第一則文字訊息以 START、三段 CONTENT、END 送出；接著 `check_claim` 的 tool call 以 START、兩段 ARGS、END 送出，後端執行後送出 RESULT，並用一個 STATE_DELTA 把理賠狀態寫進共享 state；第二則文字訊息之後是前端 tool `request_photo_upload` 的 tool call，沒有 RESULT，因為後端不執行它；最後是 RUN_FINISHED。

**中間五行是前端 fold 出來的畫面。** 兩個對話泡泡是從片段拼回來的完整文字；兩張 tool 卡片中，`check_claim` 已完成，`request_photo_upload` 的狀態是「等使用者操作」，因為 RUN_FINISHED 的 outcome 告訴前端這個 run 在等前端 tool。面板上的 B-2077 是 input-required、缺外箱破損照片，這份資料來自後端查到的 A2A task 狀態，透過 STATE_DELTA 送到畫面：第一段程式的中斷態，在這裡變成了店家眼前的一個待辦。

**倒數第二行是 run r2。** 店家上傳照片後，前端把上傳結果當成 `c2` 的 tool 結果，開始新的 run，並帶上目前的 state；後端的模型看到 tool 結果，回覆「收到照片，已轉交快航」。assert 確認模型第三次被呼叫時，最後一則訊息正是這個 tool 結果，第 4 章的配對不變式跨越兩個 run 仍然成立。**最後一行**是壞掉的串流：沒有 START 就送 CONTENT，前端以 `ProtocolError` 拒絕，而不是默默顯示一段來路不明的文字。真實的前端遇到這種錯誤，應該丟棄這個 run 的增量狀態，向後端要求 snapshot 重新同步。

| 事故（15.1 節） | 錯誤的做法 | 本章的做法 | 程式中的位置 |
|---|---|---|---|
| 逾時後誤報「已送出」 | 把多天的工作包成同步 tool 呼叫 | A2A task：中斷態即回傳，狀態以 server 為準 | `send_message`、`resolve_interrupt` |
| 用青鳥的身分替所有店家申請 | 把服務帳號 token 塞進參數 | auth-required：店家本人 OAuth 授權，憑證走傳輸層 | `credentials`、`REQUIRED_SCOPE` |
| 店家盯著轉圈圈四十秒 | 等整個 run 結束才回一包文字 | AG-UI 事件串流：文字、tool 進度、state 即時推送 | `run_agent`、`FrontendView` |

這張表把三個事故與修法對齊。三個修法有一個共同點：都把「隱含在程式流程裡的狀態」變成「協定上看得見的狀態」。task 狀態讓雙方知道球在誰手上，scope 讓授權可以被驗證，事件讓畫面知道 agent 正在做什麼。這兩段程式刻意沒有做的事也要列出來：task 狀態只存在記憶體，沒有持久化與並行寫入保護；webhook 推送、名片簽章驗證、斷線重連都只在文字中說明；AG-UI 的 interrupt 用 outcome 欄位簡化表達。這些分別在第 22 章（durable execution）、第 33 章（identity 與授權）與第 24 章（runtime 的事件串流）補上。

## 15.10 實務應用

本章的三個協定都還在快速演進，但它們要解決的問題很穩定：跨組織的長任務委派、即時的前端呈現、可驗證的代理付款。以下四個情境說明這些技術在不同產品中怎麼落地。

**情境一：電商 SaaS 與物流夥伴的跨公司協作（青鳥的主線）**。青鳥與快航是兩家公司，彼此不分享 prompt、工具與資料庫，A2A 的不透明 agent 模型正好合適。落地時的重點是：用 agent card 宣告技能與授權需求；每張理賠是一個 task，用 contextId 把同一筆訂單的多次申請串起來；中斷態轉成店家後台的待辦，並設定逾時（店家三天沒補件，task 由快航轉為 failed 或由青鳥取消）；結果以 artifact 讀取，寫進青鳥的對帳系統。授權永遠是店家本人透過 OAuth 給的 scope，青鳥的服務帳號只代表「青鳥這個平台」，不能代替店家同意。

**情境二：企業內部的多 agent 平台**。大型企業常有好幾個團隊各自用不同框架做 agent：IT 的帳號 agent、HR 的請假 agent、財務的報銷 agent。內部平台用 A2A 作為共同介面，各 agent 在內部 registry 登錄 agent card，入口的助理 agent 依技能挑選並委派。和跨公司情境相比，內部情境的身分可以統一用企業的身分系統，但要注意兩件事：委派時要把「原始使用者是誰」一路傳下去（第 33 章的 delegation），否則財務 agent 只會看到「入口 agent 要求報銷」；而且每個 agent 仍然要自己做授權檢查，不能因為請求來自內部 agent 就放行。公開資料中，Google ADK 有原生的 A2A task 模式，Gemini CLI 的原始碼內建 A2A client，用來呼叫遠端 subagent。

**情境三：SaaS 產品內嵌的 copilot**。專案管理、CRM、設計工具在畫面側邊放一個 agent，它要能讀寫畫面上的資料（共享 state）、在畫面上開啟元件（前端 tool）、在執行有副作用的動作前請使用者確認（interrupt）。這是 AG-UI 的典型場景：後端可以換框架，前端元件不用重寫。設計重點是 state 的分區（哪些欄位 agent 可以寫）、前端 tool 結果的驗證，以及斷線重連後用 snapshot 重建畫面。AG-UI 由 CopilotKit 發起，公開資料顯示 LangGraph、Mastra、Microsoft Agent Framework、Claude Agent SDK 等都有整合，常見的做法是框架負責產生事件、CopilotKit 這類前端套件負責渲染。

**情境四：代理購物與付費 API**。購物助理替使用者比價、加入購物車、結帳；研究 agent 呼叫按次計費的資料 API。前者的關鍵是 checkout 流程與授權證明：商家要確認購物車內容、價格與使用者授權一致，agent 只傳遞受限的付款 token；ACP 的公開規格就把商家定位為交易的賣方（merchant of record），agent 不經手金流。後者的關鍵是小額、高頻、機器對機器：x402 這類協定讓 API 直接以 HTTP 402 要求付款，搭配錢包層級的支出上限。兩者的共同原則是：付款的邊界用確定性程式檢查，超出邊界一律找人，而且每一筆都可以稽核。

| 情境 | 主要協定 | 關鍵設計 | 最容易出錯的地方 |
|---|---|---|---|
| 跨公司物流協作 | A2A（＋MCP 查詢） | task 狀態機、中斷轉待辦、artifact 對帳 | 用平台帳號替使用者授權 |
| 企業內部多 agent | A2A＋內部 registry | 技能探索、身分一路傳遞、各自授權 | 信任「來自內部 agent」的請求 |
| SaaS 內嵌 copilot | AG-UI | 共享 state 分區、前端 tool、interrupt | 把前端 tool 結果當成可信資料 |
| 代理購物與付費 API | ACP／UCP、AP2、x402／MPP | 授權鏈、受限 token、支出上限 | 把真實憑證交給 agent |

這張表的最後一欄都是信任邊界的錯誤，而不是協定格式的錯誤。協定讓雙方說同一種語言，但「誰可以代表誰、做什麼、做到多少」仍然要由你的系統決定與檢查。

## 15.11 設計檢查清單

設計或審查一個跨 agent 或 agent 到前端的整合時，逐項回答下面的問題。

1. 這個整合連接的是哪兩方？應該用 MCP（工具）、A2A（不透明 agent 的長任務），還是 AG-UI（前端事件）？選擇的理由是否寫在 design doc 裡？
2. 遠端 agent 的 agent card 是否經過驗證（必要欄位、TLS 端點、security scheme、簽章）？名片更新時是否會重新驗證？
3. task 狀態的所有寫入是否都經過唯一的轉移檢查入口？資料庫層是否用條件更新防止並行覆寫？
4. 終態是否不可變？後續工作是否以新 task 加上同一個 contextId 處理？
5. input-required 與 auth-required 各自轉給誰處理？是否設定了等待逾時，以及逾時後的狀態？
6. 授權是否由資源擁有者本人給予，憑證是否走傳輸層而不是訊息內容？平台帳號是否永遠不代替使用者同意？
7. task 不存在與沒有權限是否回傳相同的錯誤？
8. 長任務選擇了哪種通知方式（polling、streaming、push）？斷線或漏收時，是否能用一次完整查詢補齊？
9. 如果使用 push notification，client 是否驗證通知來源？server 是否驗證 webhook 網址、防止 SSRF？
10. 結果是否放在 artifact，而不是只寫在 message 裡？
11. AG-UI 的每個 run 是否保證以結束或錯誤事件收尾？前端是否驗證事件順序，遇到違規就重新同步？
12. 共享 state 是否以 snapshot 加 delta 同步？哪些欄位由 agent 寫、哪些由人寫，衝突時以誰為準？
13. 前端 tool 的結果是否在後端以不可信輸入的標準驗證？
14. generative UI 是否只從允許的元件目錄組合，或在隔離的 iframe 中執行？介面上的動作是否回到後端重新授權？
15. 如果涉及付款，agent 是否只拿到受限、可撤銷的 token？限額是否由確定性程式檢查？每筆付款是否有 idempotency key 與稽核紀錄？

## 15.12 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 客服告訴使用者「已送出」，對方其實還在等補件 | 把長任務包成同步 tool，逾時或中斷態被當成成功 | 比對 agent 回覆與遠端 task 的實際狀態 | 改用 task；只有讀到 completed 與 artifact 才宣告完成 |
| 已完成的 task 又出現處理中 | 狀態欄位可被任意改寫，或重試邏輯寫回舊狀態 | 查 task 的狀態事件序列是否有終態之後的轉移 | 唯一寫入入口加轉移檢查；資料庫用條件更新 |
| 遠端 agent 無法分辨是哪個使用者授權 | 用平台服務帳號呼叫，或把 token 放進訊息內容 | 檢查請求的 Authorization 與 scope 屬於誰 | auth-required 時讓擁有者本人授權；憑證走傳輸層 |
| 長任務的狀態在 client 端卡住不動 | 串流斷線後沒有重新訂閱，或 push 被漏收 | 對照 client 本地狀態與 GetTask 的結果 | 重連時先查完整快照；push 只當提示，以查詢為準 |
| 前端畫面出現錯誤或重複的內容 | 漏收 delta 後硬套後續 delta，或重複事件未去重 | 比對前端 state 與後端 snapshot | delta 失敗即要求 snapshot；事件用 id 冪等處理 |
| 前端卡在「處理中」 | 後端例外時沒有送出 RUN_ERROR，串流就此中斷 | 看事件流的最後一個事件是否為結束或錯誤 | 用 try／finally 保證每個 run 都送出終態事件 |
| webhook 收到偽造的狀態通知 | 沒有驗證通知來源，直接相信通知內容 | 檢查通知的 token 或簽章驗證邏輯 | 驗證來源；收到通知後以 GetTask 查詢真正狀態 |
| agent 重試後重複付款 | 付款步驟沒有 idempotency key | 看同一張訂單是否有多筆相同金額的付款紀錄 | 每筆付款帶 idempotency key；付款狀態以支付方為準 |

## 本章重點整理

- MCP、A2A、AG-UI 分別連接 agent 與工具、agent 與另一個不透明的 agent、agent 後端與前端，三者是疊在一起用的，不是互相競爭的標準。
- 判斷要不要用 A2A 的標準不是對方用不用模型，而是互動需不需要生命週期：會不會跑很久、會不會中途要求補件或授權、產出需不需要長期查詢。
- agent card 宣告身分、技能、端點與授權需求；client 要驗證名片，而名片上的能力宣告永遠不等於授權。
- A2A 的 task 是一台狀態機：working 可以進入 input-required 與 auth-required 兩個中斷態，中斷態代表「球在 client 手上」，補件或授權後回到 working。
- 終態不可變，後續工作開新 task 並用 contextId 串起來；所有狀態寫入都要經過唯一的合法轉移檢查。
- 結果放在 artifact，message 只用於溝通；task 不存在與沒有權限要回傳相同錯誤，避免資源探測。
- 長任務的通知要組合 polling、streaming 與 push，並以 server 的完整快照為準，事件只是讓體驗即時的通知。
- 授權由資源擁有者本人給予，憑證走傳輸層；push 通知要驗證來源，server 要防 SSRF。
- AG-UI 是 harness 對外的事件串流：文字與 tool call 用「開始、內容、結束」三段式，run 一定以結束或錯誤事件收尾。
- 共享 state 用 snapshot 加 JSON Patch delta 同步，delta 套用失敗時要重新要 snapshot，而不是硬套。
- 前端 tool 讓 agent 操作畫面，但它的結果等同使用者輸入，後端要以不可信資料驗證。
- generative UI 依 agent 的自由度分成靜態元件、宣告式 UI、開放式 UI，自由度越高越需要元件 allowlist 或隔離執行。
- agent payments 協定分成授權證明、商務流程、付款傳輸三層；framework 只需要把付款抽象成中斷，由獨立元件用確定性規則檢查限額。
- agent 永遠只拿到受限、可撤銷的付款 token，每筆付款都要有 idempotency key 與稽核紀錄。

## 延伸問答

> [!question]- Q1. 快航的理賠 agent 背後也是 LLM，為什麼不把它包成 MCP tool 就好？什麼情況下包成 tool 反而比較對？
> 關鍵在互動的形狀，而不是對方用了什麼技術。理賠會跑好幾天、中途要補照片、要店家本人授權，結果是一份要長期查詢的理賠單；把它包成 tool，等於假設「送出參數、一次拿回結果」，逾時、補件、授權都沒有地方表達，Iris 的事故一就是這樣發生的。A2A 的 task 讓這些狀態成為協定的一部分，雙方都看得懂。
>
> 反過來，如果對方的行為短而確定，例如「把地址正規化」「把商品描述翻成英文」，即使背後是 LLM，包成 MCP tool 更簡單：不需要 task id、不需要狀態查詢，失敗就重試。另一個判斷點是控制權：tool 是呼叫方 agent 的一部分能力，呼叫方要對結果負責；A2A 的對方是獨立的服務，有自己的政策與責任範圍。對方會不會拒絕你、會不會要求你補資料，也是選 A2A 的訊號。

> [!question]- Q2. 為什麼 A2A 的 task 進入終態後不可再變？店家想在已完成的理賠上補一張照片，該怎麼設計？
> 終態不可變有兩個理由。第一是讓所有讀者看到一致的歷史：對帳系統讀到 completed 與理賠編號後就入帳了，如果 task 之後可以回到 working，對帳系統讀到的資料就作廢，而且它無從得知。第二是讓狀態機簡單到可以驗證：只要終態沒有出邊，「task 最後怎麼了」就只有一個答案，稽核與 tracing 都依賴這一點。這和會計上「已入帳的交易不修改，用沖銷更正」是同一個原則。
>
> 店家想補照片時，client 應該在同一個 contextId 開一個新 task，訊息中引用原本的 task id，讓快航知道這是同一筆理賠的補充。快航可以決定把它當成「補件申請」處理，產出一份新的 artifact（例如更新後的理賠單），舊 task 的歷史則原封不動。動手做的程式就是這樣處理：對已完成的 `t-1` 補件得到 `invalid_transition`，錯誤訊息直接告訴 client 要在 `ctx-1` 開新 task。

> [!question]- Q3. input-required 與 auth-required 都是「等 client」，為什麼要分成兩個狀態？用一個 waiting 加上說明文字不行嗎？
> 因為兩者的處理者、處理方式與安全要求都不同，client 必須能用程式分辨，而不是解析自由文字。input-required 要的是資料，例如照片、訂單編號，通常可以由 agent 自己補，或轉給使用者在對話中回答；這些資料走訊息的 parts。auth-required 要的是授權，必須由資源擁有者本人在授權頁同意，產生的憑證要走傳輸層的 Authorization，不能放進訊息內容，否則憑證會進入對方的 context、log 與 trace。
>
> 如果只有一個 waiting 狀態，client 就得從說明文字猜測對方要什麼，猜錯的代價很高：把授權需求當成資料需求，agent 可能會試著自己「補」一個 token，例如拿平台的服務帳號頂替，這正是 Iris 的事故二。分成兩個狀態，client 可以為它們寫不同的處理路徑：input-required 轉成對話或待辦，auth-required 一律轉成擁有者的 OAuth 同意流程，而且 agent 本身完全碰不到憑證。

> [!question]- Q4. 你在 production 看到 15% 的理賠 task 停在 input-required 超過七天，你會怎麼排查與改善？
> 先分清楚是「該補的沒人補」還是「不該停的停住了」。第一步是抽樣這些 task 的狀態訊息與歷史：如果多數是「請提供照片」，問題在青鳥這端的轉交流程，可能是待辦沒有送到店家、通知被埋在其他訊息裡，或者店家根本不知道要去哪裡上傳。這時要看 AG-UI 端的資料：中斷態有沒有變成前端的待辦卡片、店家有沒有看到、看到後有沒有操作。
>
> 如果狀態訊息含糊或重複要求同一份資料，問題可能在快航那端，例如照片格式不符卻沒有說清楚。這時要把具體 task 給對方，並要求狀態訊息可行動（要什麼、什麼格式、為什麼）。改善上有三件事：為中斷態設定逾時與提醒（例如三天提醒、七天自動取消並通知店家）；在 client 端記錄每次中斷的開始與結束時間，做成 dashboard；把「中斷態停留時間」列為和合作夥伴共同追蹤的指標，因為它直接決定理賠的處理天數。

> [!question]- Q5. AG-UI 的 STATE_DELTA 很省頻寬，為什麼還需要 STATE_SNAPSHOT？什麼時候應該送 snapshot？
> delta 的正確性依賴「前端目前的狀態與後端預期的基礎一致」。只要漏收一個 delta（網路斷線、分頁在背景被暫停、前端重新整理），之後的每一個 delta 都可能套在錯的基礎上；有時會像 15.7 節的程式一樣直接失敗，更糟的是有時會「成功」套用卻產生錯誤的畫面，而且不會有人發現。snapshot 是校正點：它不依賴任何先前的狀態，前端收到後直接覆蓋。
>
> 應該送 snapshot 的時機有四個：run 開始時、前端重新連線時、前端回報 delta 套用失敗時，以及狀態結構大幅改變、用 delta 表達反而更大時。實務上可以替 state 加上版本號，每個 delta 帶著它所基於的版本，前端發現版本對不上就主動要求 snapshot。這和 A2A 的「事件只是通知、以 GetTask 為準」是同一個原則：增量讓體驗即時，快照讓系統正確。

> [!question]- Q6. 程式找錯：下面這段前端程式處理 AG-UI 事件，有哪些會在 production 出事的問題？
> ```python
> def on_event(ev, ui):
>     if ev["type"] == "TEXT_MESSAGE_CONTENT":
>         ui.bubble += ev["delta"]
>     elif ev["type"] == "TOOL_CALL_ARGS":
>         ui.card_args = json.loads(ev["delta"])
>     elif ev["type"] == "CUSTOM" and ev["name"] == "render_html":
>         ui.panel.inner_html = ev["value"]
> ```
> 第一個問題是文字沒有依 messageId 分開：所有片段都追加到同一個 `ui.bubble`，兩則訊息或交錯的訊息會混在一起，也沒有檢查 START 是否出現過。第二個問題是在 TOOL_CALL_ARGS 就解析 JSON：參數是分段送達的，單一片段通常不是合法 JSON，這一行會丟例外，就算剛好成功，也只是參數的一部分；正確做法是依 toolCallId 累積，到 TOOL_CALL_END 才解析。
>
> 第三個問題最嚴重：把 CUSTOM 事件帶來的 HTML 直接塞進主頁面。只要攻擊者能影響模型的輸入（例如在訂單備註裡藏指令），就可能讓 agent 產生惡意 HTML，在店家後台執行腳本或偽造按鈕。generative UI 應該只從允許的元件目錄組合，或放進隔離的 iframe。另外這段程式也沒有處理 RUN_FINISHED、RUN_ERROR 與未知事件，前端無法知道 run 結束了沒，斷線時也不會要求 snapshot。

> [!question]- Q7. 面試追問：設計一個讓 agent 能替使用者購買退貨物流單的功能，你會怎麼處理付款的信任與風險？
> 先從授權範圍開始：使用者事先設定「退貨單可自動購買，每張上限 120 元，每月最多 30 張，只限快航」，這份授權要以可驗證、可稽核的形式保存，而不是只存在 prompt 裡；超出範圍的購買一律變成 human-present 的確認。依 autonomy 分級，範圍內是 L4，範圍外回到 L3。執行時，agent 走到付款步驟就進入類似 auth-required 的中斷，由獨立的付款元件用確定性程式檢查金額、商家、次數與期限，通過才向支付服務商取得受限的 token。
>
> 接著是失敗與重試：每筆購買都帶 idempotency key（例如由訂單編號與退貨單類型組成），agent 或 worker 重試幾次都只付一次；付款狀態以支付服務商的回應為準。最後是可觀測與可回復：每一筆付款留下「誰授權、授權了什麼、實際付了什麼」的稽核紀錄，並提供使用者撤銷授權與申請退款的路徑。如果面試官追問協定，可以說明 AP2 這類 mandate 解決授權證明、ACP 或 UCP 解決 checkout 流程、x402 解決 API 按次付費，但系統的信任邊界不會因為採用哪個協定而消失。

> [!question]- Q8. 估算題：青鳥每天約有 2,000 張理賠 task，平均每張經歷 6 次狀態變化，審核期平均 3 天。用 streaming 一直維持連線，和改用 push notification，資源需求差多少？
> 如果每張 task 從建立到結束都維持一條串流連線，同時存在的連線數約等於「每天新增數乘以平均存活天數」，也就是 2,000 × 3 ＝ 6,000 條長連線，而且這些連線絕大多數時間沒有任何事件：每張 task 三天只有 6 次狀態變化。每條連線都要佔用 server 與 client 的連線資源、要處理 load balancer 的閒置逾時，部署時全部斷線還要重新訂閱，成本和可靠性都不划算。
>
> 改用 push 之後，傳輸量只剩事件本身：每天約 2,000 × 6 ＝ 12,000 次 webhook 呼叫，平均每秒不到一次，就算尖峰是平均的十倍也很輕。實務上的組合是：店家正在畫面前等的那幾十秒用 streaming，讓第一個狀態即時出現；進入中斷態或長時間審核後改用 push；每天再用一次 ListTasks 或 GetTask 對帳，補上任何漏收的通知。這個估算也說明了為什麼 push 的可靠性設計（驗證、重送、去重）值得投資。

## 延伸閱讀

- A2A Project〈Agent2Agent (A2A) Protocol Specification〉v1.0（Linux Foundation，2026）
- AG-UI Protocol 文件〈Agent User Interaction Protocol〉與 1.0 release notes（CopilotKit 與社群，2026）
- Model Context Protocol〈Specification 2026-07-28〉（第 14 章的延伸，含 Tasks 與 MCP Apps extensions）
- Google〈AP2: Agent Payments Protocol〉規格文件（v0.2，FIDO Alliance）
- OpenAI 與 Stripe〈Agentic Commerce Protocol〉規格（GitHub）
- x402 Foundation〈x402〉規格與 SDK 文件（GitHub）
- IETF RFC 6902〈JavaScript Object Notation (JSON) Patch〉
