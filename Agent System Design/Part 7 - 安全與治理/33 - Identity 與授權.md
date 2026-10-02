---
chapter: 33
title: Identity、授權與稽核
part: 7
---

# 第 33 章　Identity、授權與稽核

> [!abstract] 本章地圖
> **核心問題**：agent 替人做事時，系統要怎麼回答「這是誰、代表誰、憑什麼、做了什麼」，而且在事後拿得出別人無法竄改的證據？
>
> **你會學到**：
> - 把 agent 當成獨立的 principal 管理，說清楚「agent 自己的身分」與「代表使用者行動」的差別，並算出一次動作的有效權限
> - 用 delegation、on-behalf-of 與 token exchange 的概念，設計一條每一跳都縮小權限、都留下代理鏈的 token 路徑
> - 設計 scope 與 step-up：預設最小權限，高風險動作才升級，而且升級只對單筆交易有效
> - 依 MCP 授權模型實作 resource server 端的檢查：resource metadata、resource indicator、audience 檢查與禁止 token passthrough
> - 讓 secrets 不進 prompt、不進 sandbox，並讓租戶隔離由 harness 強制執行，不靠模型自律
> - 實作授權 middleware 與 hash-chained 稽核日誌，並寫出能抓到修改、刪除、重算與截斷的驗證程式
>
> **前置知識**：第 4 章（agent loop 與 dispatch）、第 14 章（MCP 的 OAuth 流程與 token passthrough）、第 21 章（approval gate）、第 31 章（威脅模型與 excessive agency）、第 32 章（least privilege 與 capability-based 權限）

## 33.1 故事：一筆說不清楚的 3,200 元退款

九月底，青鳥科技準備把客服 agent 開放給所有店家，同時把 500 元以下的退款從「每筆都要客服確認」（L3）移到「邊界內自動」（L4）。上線前一週，小森選物（komori）的店長打電話來：後台報表顯示訂單 B-1042 被退了 3,200 元，「我們店裡沒有任何人核准過這筆」。阿哲把電話轉給 Iris，Iris 以為查 log 十分鐘就能回覆，結果查了兩天，最後的結論是「說不清楚」。

第一個卡關的地方在 ERP。ERP 的操作紀錄上，這筆退款的操作者是 `bluebird-integration`，那是青鳥所有 agent 共用的一把長效 API key，權限是整個 ERP 的管理者，放在每個 tool 都讀得到的環境變數裡。ERP 只知道「青鳥做了這件事」，不知道是哪個 agent、替哪位店員、在哪一次對話裡做的。第二個卡關的地方在青鳥自己的紀錄：debug trace 只保留七天，已經被清掉了；approval 資料表裡這筆退款的核准者欄位寫著 `amy`，可是 Amy 堅持自己沒按過核准，而客服後台的管理員剛好有權限改這個欄位。沒有人能證明這個值是當時寫的，還是事後補的。

查的過程中 Maya 又挖出第三個問題。營運 research agent 的 `query_orders` tool 有一個 `tenant_id` 參數，由模型根據對話內容填寫；有一次店員貼了一段含有「海港家居」字樣的對話紀錄進來，模型就把 `tenant_id` 填成了 harbor，報表裡混進了另一家店的訂單。資料庫照單全收，因為那把共用 key 本來就能讀所有店家的資料。

週五的檢討會上，老陳在白板寫了四個詞：**是誰、代表誰、憑什麼、做了什麼**。「安全審查問的不只是會不會出錯，」老陳說，「而是出錯之後，你能不能用別人改不了的證據，把這四件事說清楚。我們現在一件都說不清。」Maya 接著列出要求：每個 agent 有自己的身分；agent 代表店員行動時，權限不能超過店員本人；每一跳的 token 都要短效、只給特定的下游；租戶由登入身分決定；稽核紀錄要能證明沒被改過。

這一章就是青鳥把這些要求做出來的過程。我們會從身分的基本概念講起，依序處理 agent identity、delegation 與 token exchange、scope 與 step-up、MCP 的授權模型、secrets 管理、多租戶隔離與稽核日誌，最後在「動手做」給 `loom` 加上 `loom.auth` 模組：一個授權 middleware，加上一份能偵測竄改的 hash-chained 稽核日誌。

## 33.2 三個問題：認證、授權與可歸責

身分與權限的討論常常混在一起，先把三個詞分開。**authentication**（認證）回答「你是誰」：使用者用密碼加 MFA 登入、服務用憑證證明自己，結果是一個可信的身分，例如「user:amy，屬於 komori」。**authorization**（授權）回答「你能不能做這件事」：Amy 能不能查 B-1042、能不能退 3,200 元。**accountability**（可歸責）回答「事後能不能證明是誰做的」：靠的是完整、可信、不可竄改的紀錄。三者是依序建立的：沒有可信的認證，授權只是在猜；沒有可信的紀錄，授權做得再好，出事時也拿不出證據。

傳統 web 應用裡，這三件事的主角只有一個：使用者按下按鈕，伺服器就以使用者的身分執行。agent 讓這條路徑變長了。Amy 在客服後台打一句話，客服 agent 決定呼叫 `refund`，tool gateway 把呼叫轉給 ERP 的 MCP server，MCP server 再呼叫 ERP API。每一跳都有一個「行動者」，而真正的意圖來源只有最前面那位使用者。

```text
 意圖來源                       行動者（每一跳都要能被識別）                      資源
 ┌─────────┐   對話    ┌──────────────┐ tool call ┌────────────┐  MCP   ┌────────────┐  API  ┌─────────┐
 │ Amy     │ ────────► │ 客服 agent   │ ────────► │ tool       │ ─────► │ ERP MCP    │ ────► │ ERP API │
 │ (komori)│           │ cs-agent@3.2 │           │ gateway    │        │ server     │       │ 訂單/退款│
 └─────────┘           └──────────────┘           └────────────┘        └────────────┘       └─────────┘
      │                       │                         │                     │                  │
  認證：登入＋MFA        認證：workload 身分       驗 token、scope       驗 aud、scope      驗 aud、租戶
      │                       │                         │                     │                  │
      └──────── 每一跳的紀錄都要寫：sub=amy（代表誰）、act=當下的行動者（誰在做）────────────────┘

 v0 的現況：五個方框共用一把 bluebird-integration 管理者 key，ERP 只看得到最後一個名字
```

這張圖從左到右讀。最左邊的 Amy 是 **principal**（主體，可以被認證、被授權、被追責的實體）；Amy 的身分來自登入。第二個方框是客服 agent，它也是一個 principal，只是它的身分不是靠密碼，而是靠部署時配發的 **workload identity**（工作負載身分，用來識別「哪一份程式、哪個版本、跑在哪裡」的身分）。後面三個方框是資源端，每一個都要自己驗證收到的 token，不能因為「請求來自內部」就放行。圖底下那一行是本章最重要的要求：每一跳的紀錄都同時寫下「代表誰」與「誰在做」。青鳥 v0 的問題，就是五個方框共用一把 key，資訊在第一跳之後就全部遺失了。

| 面向 | 傳統 web 應用 | Agent 系統 |
|---|---|---|
| 誰決定要做什麼 | 使用者按按鈕，程式碼決定呼叫哪個 API | 模型依對話決定呼叫哪個 tool、帶什麼參數 |
| 行動者 | 使用者本人（經由前端） | 使用者 → agent → gateway → MCP server，一條鏈 |
| 參數從哪來 | 表單欄位，有固定格式 | 模型產生，可能被 prompt injection 影響（第 31 章） |
| 權限的典型錯誤 | 越權存取（IDOR）、缺少檢查 | 共用高權限 key、agent 權限大於使用者、模型填身分參數 |
| 使用者在不在場 | 通常在 | 背景 agent 可能跑好幾個小時，使用者早就離開 |
| 事後追查 | 存取紀錄＋使用者 id | 還要知道 agent 版本、model 與 prompt 版本、核准者、trace |

表中最後兩列是 agent 特有的難題。背景 agent（第 22 章）在使用者離線時仍然代表使用者行動，傳統「登入 session 過期就失效」的模型不夠用；而追查一次錯誤時，除了「誰」，還要知道「哪個版本的 agent 用哪個 prompt 做了這個決定」，因為同一個使用者、同一句話，在不同版本的 agent 上可能產生完全不同的動作。OWASP 的 agentic 應用風險清單把「身分與權限濫用」列為獨立一項，第 31 章的 excessive agency 也是同一件事的另一面：agent 能做的事，超過它這一刻該做的事。

> [!warning] 常見誤解
> 「agent 是我們自己的程式，跑在我們的機房，所以它呼叫內部 API 不需要授權。」這正是 confused deputy 的溫床。agent 的行為由模型決定，而模型的輸入包含使用者訊息、網頁、文件與其他 tool 的結果，任何一段都可能夾帶指令。把 agent 當成「可信的內部服務」，等於把這些外部內容都升格成可信的。正確的假設是：agent 是一個能力受限、行為不完全可預測的 principal，每一跳都要重新授權。

## 33.3 Agent identity：agent 也是一個 principal

**agent identity**（agent 身分）是讓系統能分辨「這是哪個 agent、哪個版本、誰負責」的身分。為什麼 agent 需要自己的身分，而不是直接用使用者的？有三個理由。第一是歸責：同一位店員可能同時用客服 agent 與 research agent，事故發生時要能分辨是哪一個做的。第二是限權：客服 agent 不需要讀財務報表，即使使用者本人有這個權限，agent 也不該有。第三是撤銷：發現某個版本的 agent 行為異常，要能一次停掉這個 agent 的所有權限，而不必停掉使用者的帳號。

agent 身分的具體形態通常是三層。最外層是**註冊資料**：agent id、擁有團隊、用途、允許使用的 tool 清單、autonomy 等級，像是一張員工識別證背後的人事資料。中間是**workload 憑證**：部署時由平台配發、短效、自動輪替的憑證，證明「這個 process 確實是 cs-agent 的 3.2 版」。業界常見的做法是 SPIFFE 這類標準：每個 workload 拿到一個形如 `spiffe://bluebird.example/agent/cs-agent` 的 id，以及由平台簽發、幾分鐘到幾小時就過期的 X.509 或 JWT 憑證。最內層是**執行情境**：這一次 run 的 session id、trace id、model 與 prompt 版本，它們不是身分本身，但要和身分一起寫進每一筆紀錄。

有了 agent 身分之後，下一個問題是：一次動作的權限到底由誰決定？答案是交集。

```text
 一次 tool call 的有效權限 ＝ 使用者的權限 ∩ agent 的權限 ∩ 這次任務的權限

   使用者 Amy（店員）          客服 agent（註冊時核定）       這次任務（session 授權）
 ┌──────────────────────┐   ┌──────────────────────┐     ┌──────────────────────┐
 │ orders:read          │   │ orders:read          │     │ orders:read          │
 │ refunds:write        │   │ refunds:write        │     │ refunds:write ≤ 500  │
 │ reports:read         │   │ returns:write        │     │                      │
 │ staff:manage         │   │                      │     │                      │
 └──────────────────────┘   └──────────────────────┘     └──────────────────────┘
              └──────────────────────┬──────────────────────────┘
                                     ▼
                     有效權限：orders:read、refunds:write（≤ 500）
           reports:read：agent 沒有 → 不給      returns:write：Amy 沒有 → 不給
```

逐欄看。第一欄是 Amy 在店家系統裡的角色權限，包括管理店員帳號這種和客服無關的權限。第二欄是客服 agent 註冊時核定的能力上限，它能建立退貨單，但不能讀報表。第三欄是這一次任務實際需要、使用者在 session 中同意的範圍，退款還帶著金額上限。有效權限是三者的交集：`reports:read` 因為 agent 沒有而不給，`returns:write` 因為 Amy 本人沒有而不給，即使 agent 有這個能力。這個交集規則有一個直接的推論：**agent 永遠不能讓使用者做到本人做不到的事**，這是防止 agent 變成提權工具的底線。

| 身分模式 | 意思 | 典型技術 | 適用情境 | 主要風險 |
|---|---|---|---|---|
| agent 自身身分 | agent 以自己的名義行動，沒有特定使用者 | client credentials、workload identity | 夜間對帳、系統監控、L5 的月度分析（資料範圍事先核定） | 權限容易越給越大；看不出是替誰做的 |
| 代表使用者（delegation） | agent 以「代表 Amy」的名義行動，權限是交集 | authorization code＋token exchange、`act` claim | 客服、個人助理、coding agent 操作使用者的 repo | 使用者權限很大時，agent 也可能很大 |
| 冒充使用者（impersonation） | 下游看到的就是 Amy 本人，看不出 agent | 直接轉送使用者 token | 不建議 | 稽核看不出 agent；token passthrough |

這張表的第三列要特別說明。**impersonation**（冒充）和 **delegation**（委派）在 token exchange 的規格裡是兩種不同的語意：冒充時，新 token 上只有使用者，下游以為是使用者本人在操作；委派時，新 token 同時寫著「主體是 Amy」與「行動者是 cs-agent」。對 agent 系統而言，委派幾乎總是對的選擇，因為事故調查與權限設計都需要知道「這是 agent 做的」。一個實用的判斷方法是：如果 ERP 想對 agent 發出的退款套用比人工退款更嚴的規則（例如更低的金額上限），它就必須能分辨兩者，這只有委派做得到。

> [!warning] 常見誤解
> 「agent 繼承使用者的全部權限最簡單，反正使用者本來就能做這些事。」問題在於使用者不會被一段網頁文字說服去刪掉所有訂單，但 agent 可能會。繼承全部權限讓 prompt injection 的影響範圍等於使用者的全部權限。正確做法是讓 agent 的註冊權限只包含它的任務需要的能力，再和使用者權限取交集。

> [!note] 2026 現況
> 截至 2026 年 10 月，依公開文件：Amazon Bedrock AgentCore 提供 Identity 服務，負責 agent 身分與 OAuth credential 管理，支援 Cognito、Okta、Entra、Auth0 等身分提供者；Google 的 Gemini Enterprise Agent Platform（原 Vertex AI Agent Engine 頁面）在 Agent Runtime 中列出 agent identity，Sessions 以 IAM Conditions 控管存取。Microsoft Entra、Okta、Auth0 等身分廠商也都推出了以 agent 身分為主題的方案，但名稱與功能狀態變動很快，採用前請查當時的官方文件。標準面，NIST 在 2026 年啟動 AI Agent Standards Initiative，其中 NCCoE 發表了以軟體與 AI agent 的身分與授權為題的 concept paper；Agentic AI Foundation 也設有 Identity & Trust 工作小組。Anthropic 在 2026 年的公開文章中，仍把「agent 該有自己的 principal 還是繼承使用者權限」與 multi-agent 之間的信任升級列為開放問題。

## 33.4 代表使用者行動：delegation、on-behalf-of 與 token exchange

知道要用委派之後，接著要解決「怎麼做」。起點是 **OAuth**：一套讓使用者授權某個應用程式、在限定範圍內代表自己存取資源的標準。使用者在授權伺服器登入並同意之後，應用程式拿到一張 **access token**（存取權杖），上面寫著主體（`sub`）、受眾（`aud`，這張 token 是給哪個服務用的）、範圍（`scope`，能做什麼）與期限（`exp`）。第 14 章已經用 MCP 的場景走過一次完整的授權碼流程，這一節關心的是下一步：拿到使用者的 token 之後，agent 要怎麼往下游傳遞授權，才不會變成冒充，也不會越傳越大。

答案是 **token exchange**（權杖交換，RFC 8693）。它的意思是：拿著一張既有的 token（`subject_token`，代表「替誰做」）去找授權伺服器，加上自己的身分證明（`actor_token`，代表「誰在做」），換一張新的 token。新 token 的受眾是下一跳的服務、範圍不超過原本、期限更短，並用 **`act` claim**（行動者聲明）記下行動者。當鏈條更長時，`act` 會巢狀嵌套：最外層是現在的行動者，裡面一層是上一個行動者，一路記到最早的那一個。這種模式在不同廠商的文件裡也被稱為 **on-behalf-of**（OBO，代表某人）流程，概念相同。

```text
 Amy 的瀏覽器      客服後台/agent       授權伺服器（AS）        tool gateway        ERP MCP server      ERP API
     │ 登入＋同意 ─────►│                     │                     │                    │                  │
     │                  │◄── t0：sub=amy, aud=console, scope=orders:read refunds:write, 1 小時
     │                  │                     │                     │                    │                  │
     │                  │── exchange(t0, actor=cs-agent 憑證, aud=tool-gateway) ────────►│                  │
     │                  │◄── t1：sub=amy, act={cs-agent}, aud=tool-gateway, 5 分鐘 ──────│                  │
     │                  │── tools/call refund ＋ t1 ──────────────►│                    │                  │
     │                  │                     │       驗 t1 的 aud、scope、租戶          │                  │
     │                  │                     │◄─ exchange(t1, actor=gateway, aud=erp-mcp) │                │
     │                  │                     │── t2：act={gateway,{cs-agent}}, 60 秒 ─►│                  │
     │                  │                     │                     │── 轉呼叫＋t2 ─────►│                  │
     │                  │                     │◄─────────── exchange(t2, aud=erp-api, scope=最小) ─────────│
     │                  │                     │── t3：act={erp-mcp,{gateway,{cs-agent}}}, 60 秒 ──────────►│── refund ＋ t3 ─►│
     │                  │                     │                     │                    │   驗 aud=erp-api │
```

這張時序圖展示了一張 token 怎麼一跳一跳地被「換」而不是被「轉」。t0 是 Amy 登入後客服後台拿到的 token，受眾是後台本身，期限一小時。agent 要呼叫 tool 時，以自己的 workload 憑證當 `actor_token` 換到 t1：主體仍是 Amy，`act` 是 cs-agent，受眾只有 tool gateway，期限五分鐘。gateway 驗證 t1 之後，同樣用自己的身分換出受眾是 ERP MCP server 的 t2；MCP server 再換出受眾是 ERP API、scope 只剩這次需要的最小範圍的 t3。每一跳的 token 只在下一跳有效，被偷了也拿不去別的地方用；每一跳都要經過授權伺服器，授權伺服器可以集中套用政策（例如「cs-agent 只能換到 ERP 的訂單與退款 scope」）並留下紀錄。

實務上不一定每一跳都要找授權伺服器換 token。tool gateway 與 MCP server 如果在同一個信任邊界內，也可以由 gateway 驗證後，以內部簽發的短效情境 token 傳遞使用者與 agent 資訊；關鍵不在於用哪一種技術，而在於三條不變式：**範圍只能縮小、期限只能縮短、行動者必須被記下**。授權伺服器還可以用 `may_act` 一類的設定事先聲明「哪些行動者可以代表這個主體」，例如只有註冊過的 cs-agent 能代表店員換 token，其他程式拿著 Amy 的 token 來換會被拒絕。

下面的小程式把這三條不變式寫成一個函式，示範兩跳交換之後的 token 長什麼樣子。

```python
from __future__ import annotations


def exchange(subject: dict, actor: str, audience: str, scope: set[str], now: int, ttl: int = 60) -> dict:
    """RFC 8693 的概念版：用「使用者的 token」加上「行動者的身分」換一張更窄、更短、指定受眾的新 token。"""
    granted = set(subject["scope"].split())
    if not scope <= granted:                       # 只能縮小，不能放大
        raise PermissionError(f"要求的 {sorted(scope - granted)} 超出原授權")
    act = {"sub": actor}
    if "act" in subject:                           # 舊的行動者往內層巢狀，最外層永遠是「現在的行動者」
        act["act"] = subject["act"]
    return {"iss": subject["iss"], "sub": subject["sub"], "tenant": subject["tenant"],
            "aud": audience, "scope": " ".join(sorted(scope)), "act": act,
            "exp": min(subject["exp"], now + ttl)}  # 新 token 不能比原 token 活得久


def chain(claims: dict) -> str:
    """把 act 巢狀結構攤平成「誰經由誰」的可讀字串，稽核與除錯都靠它。"""
    hops, act = [], claims.get("act")
    while act:
        hops.append(act["sub"])
        act = act.get("act")
    return " ← ".join(hops + [f"{claims['sub']}（使用者）"])


now = 1_000
amy = {"iss": "https://id.bluebird.example", "sub": "user:amy", "tenant": "komori",
       "aud": "bluebird-console", "scope": "orders:read refunds:write", "exp": now + 3600}
t1 = exchange(amy, "agent:cs-agent@3.2", "tool-gateway", {"orders:read", "refunds:write"}, now, ttl=300)
t2 = exchange(t1, "mcp:erp-server", "erp-api", {"orders:read"}, now)

for name, t in (("t1 給 tool gateway", t1), ("t2 給 ERP API", t2)):
    print(f"{name:<16} aud={t['aud']:<13} scope={t['scope']:<26} 剩 {t['exp'] - now:>4} 秒")
    print(f"{'':<16} 代理鏈：{chain(t)}")
try:
    exchange(t2, "mcp:erp-server", "erp-api", {"refunds:write"}, now)
except PermissionError as exc:
    print("想從 t2 換回寫入權限 →", exc)

assert t2["act"] == {"sub": "mcp:erp-server", "act": {"sub": "agent:cs-agent@3.2"}}
assert t2["exp"] - now == 60 and t1["exp"] - now == 300
```

```text
t1 給 tool gateway aud=tool-gateway  scope=orders:read refunds:write  剩  300 秒
                 代理鏈：agent:cs-agent@3.2 ← user:amy（使用者）
t2 給 ERP API     aud=erp-api       scope=orders:read                剩   60 秒
                 代理鏈：mcp:erp-server ← agent:cs-agent@3.2 ← user:amy（使用者）
想從 t2 換回寫入權限 → 要求的 ['refunds:write'] 超出原授權
```

前四行是兩張 token 的摘要。t1 的受眾是 tool gateway，保留了讀訂單與寫退款兩個 scope，壽命 300 秒；代理鏈顯示 cs-agent 代表 Amy。t2 的受眾是 ERP API，scope 被縮到只剩 `orders:read`，壽命被壓到 60 秒，代理鏈多了一跳：ERP MCP server 經由 cs-agent 代表 Amy。最後一行是反向測試：拿著只剩讀取權限的 t2 想換回寫入權限，被拒絕。assert 鎖住了兩件事：`act` 的巢狀順序（最外層是最近的行動者），以及新 token 的期限不會比原 token 長。

**refresh token**（更新權杖）是另一個要小心的元件。access token 短效，所以應用程式通常也拿到一張長效的 refresh token，用來在不打擾使用者的情況下換新的 access token。對 agent 而言，refresh token 是最值錢的 secret：拿到它的人可以在幾週內持續代表使用者。因此它只能存在後端的 credential vault，不能進入 agent 的 context、不能進 sandbox、不能出現在 log，而且使用者撤銷授權時要能立即失效。背景 agent 的長時間授權，33.5 節與延伸問答會再談。

## 33.5 Scope 設計與 step-up：權限要小、要短、要能升級

**scope** 是 token 上「能做什麼」的清單。scope 設計得太粗，最小權限就只是口號：如果只有一個 `erp:all`，任何拿到 token 的 agent 都能做所有事。設計 scope 的經驗法則是讀寫分開、依資源類型分開、高風險動作獨立成一個 scope，並且讓 scope 名稱對應到第 5 章的 tool 副作用分級（read、write、destructive）。下表是青鳥重新設計後的 scope。

| scope | 對應的 tool | 副作用等級 | 預設給誰 | 自動核准的邊界 |
|---|---|---|---|---|
| `orders:read` | `get_order`、`search_orders` | read | 客服 agent、research agent | 只限本租戶 |
| `shipments:read` | `get_shipment` | read | 客服 agent | 只限本租戶 |
| `returns:write` | `create_return` | write（可撤銷） | 客服 agent（店員有權限時） | 自動 |
| `refunds:write` | `refund` | write（不可逆） | 客服 agent（店員有權限時） | 500 元以下自動（L4） |
| `refunds:approved` | `refund`（大額） | write（不可逆） | 沒有人預設持有 | 只能經 step-up 取得，綁定單筆交易 |
| `reports:read` | `query_orders`（彙總） | read | research agent | 只限本租戶，敏感欄位遮罩 |

表中最後一欄把第 1 章的 autonomy 等級落實成授權規則：500 元以下的退款在 `refunds:write` 的範圍內自動執行，超過就需要額外的授權。scope 也不必只是字串。金額上限、訂單 id、有效時間這些「這一筆交易的細節」，可以用結構化的授權資料表達，業界稱為 **rich authorization request**（RFC 9396，用 `authorization_details` 描述「授權做哪一筆具體的事」），比在 scope 字串裡塞 `refunds:write:max500` 這種約定更清楚，也更容易驗證。

當 agent 要做超出目前權限的事，正確的反應不是失敗，也不是讓 agent 自己想辦法，而是 **step-up authorization**（升級授權）：暫停動作，向有權限的人取得額外授權，拿到一張權限更高、期限很短、只對這一筆動作有效的 token，再繼續。

```text
            tool call：refund(B-1042, 3200)
                        │
                        ▼
              ┌───────────────────┐   scope 足夠且未超過邊界
              │ 授權 middleware   │ ───────────────────────────────► [執行]
              └─────────┬─────────┘
                        │ 超過 500 元的自動邊界（或 403 insufficient_scope）
                        ▼
              ┌───────────────────┐
              │ step_up_required  │  run 暫停（interrupt），保存待執行的 tool call
              └─────────┬─────────┘
                        │ 通知有權限的人：主管、店長，或要求使用者重新驗證（MFA）
            ┌───────────┼───────────────────┐
         核准           拒絕               逾時（例如 24 小時）
            │           │                   │
            ▼           ▼                   ▼
   AS 簽發 approval token   回填「已拒絕」給模型   回填「逾時未核准」，通知使用者
   scope=refunds:approved   run 繼續，讓模型      不自動重試
   綁定 {refund, B-1042, 3200}  向使用者說明
   120 秒、只能用一次
            │
            ▼
   resume：重送被暫停的那一個 tool call ──► middleware 比對參數完全相同、未使用過 ──► [執行]
```

這個狀態機有三個重點。第一，step-up 是一個 **interrupt**，run 要能停在原地並保存待執行的動作，這需要第 21 章的 approval 機制與第 22 章的 durable execution；同步對話中可以讓使用者當場完成 MFA，背景任務則要用推播或工單通知核准者。第二，核准得到的不是「從此可以大額退款」的泛用權限，而是一張**綁定單筆交易**的 token：工具名稱、訂單、金額都寫在 token 裡，期限只有兩分鐘，而且只能用一次。如果 resume 時參數被改了（3,200 變成 3,100），或同一張 token 被重送，middleware 都要再次要求 step-up。第三，拒絕與逾時都要回填給模型，讓它向使用者說明，但**不能讓模型自動重試或換一個 tool 繞過**；這和第 4 章「權限錯誤不回填給模型繞過」的原則一致。

step-up 和第 21 章的 approval 是同一件事的兩面。approval 是**人的決定**：主管看了參數與影響後按下核准；step-up 是**憑證的變化**：這個決定被轉成一張可驗證的 token，讓下游不必相信「harness 說主管核准過」，而是自己驗證核准的簽章。兩者分開做最常見的漏洞，是 approval 只存在 harness 的資料庫欄位裡，下游 API 看不到，於是任何能改那個欄位的人（或被誘導的 agent）都能偽造核准，青鳥的故事就是這樣。

另一個常被問到的情境是使用者不在場。背景 agent 在凌晨要做一筆需要 step-up 的動作時，沒有人能當場按 MFA。可行的做法有三種：事先在任務建立時就取得涵蓋這類動作的授權（範圍與期限都要寫清楚）；用 **backchannel 認證**（例如 OpenID 的 CIBA 這類「由服務端發起、使用者在自己的手機上核准」的流程）把核准請求推給使用者；或乾脆把動作排進待辦，等使用者上線再處理。第三種最保守，也最常是對的答案。

## 33.6 MCP 的授權模型：每一跳都是獨立的 resource server

第 14 章從 client 的角度走過一次 MCP 的授權流程：client 第一次呼叫被 401 拒絕，從 `WWW-Authenticate` 找到 server 的 **Protected Resource Metadata**（受保護資源中繼資料，RFC 9728），得知該去哪個授權伺服器拿 token；授權請求必須用 PKCE，並帶上 **resource indicator**（RFC 8707），明確說明 token 要用在哪一個 MCP server；拿到的 token 只能放在 `Authorization: Bearer` header。這一節換到 server 的角度：青鳥自己要寫 ERP MCP server 時，每收到一個 request 要做哪些檢查，以及它要怎麼呼叫自己的下游。

```text
 ERP MCP server 收到 POST /mcp
   │
   ├─ (1) 有沒有 Authorization: Bearer？ ──── 沒有 ──► 401 ＋ WWW-Authenticate: resource_metadata=<PRM>
   │                                                  （token 在 query string 一律拒絕）
   ├─ (2) 簽章、issuer、期限 ─────────────── 不通過 ─► 401 invalid_token
   │
   ├─ (3) aud 是不是「我」的 canonical URI？ ─ 不是 ──► 401：這張 token 不是給我的
   │       （就算簽章有效、scope 夠，也拒絕）
   ├─ (4) scope 夠不夠這個 tool？ ─────────── 不夠 ──► 403 insufficient_scope ＋ 所需 scope
   │                                                  （client 據此做 step-up，次數有上限）
   ├─ (5) 租戶與資源歸屬：這張訂單屬於 token 上的租戶嗎？ ── 否 ─► 與「不存在」相同的回應
   │
   └─ (6) 執行 tool：呼叫 ERP API 時
           ├─ ✗ 把收到的 token 原樣轉送（token passthrough，規格明文禁止）
           └─ ✓ 用自己的身分換一張 aud=ERP API、scope 最小的新 token，並記錄代理鏈
```

逐步看這六道檢查。(1) 確認 token 放在正確的位置；放在 URL query string 的 token 會出現在 proxy 與存取紀錄裡，所以不接受。(2) 是任何 JWT 驗證都有的基本項目。(3) 是 MCP 授權模型的核心：**audience 檢查**。簽章有效只代表「這張 token 是授權伺服器發的」，不代表「這張 token 是發給我的」；不檢查 audience，任何一個 MCP server 收到的 token 都能被拿去打另一個 MCP server。(4) scope 不夠時回 403 並在 `WWW-Authenticate` 指出需要的 scope，讓 client 走上一節的 step-up；規格也要求 client 限制重試次數，避免無限循環地要求使用者授權。(5) 是 MCP 規格之外、但每個多租戶 server 都要做的資源歸屬檢查。(6) 是 server 呼叫下游的方式，和上一節的 token exchange 是同一件事。

為什麼 **token passthrough**（token 直通）要被明文禁止？如果 ERP MCP server 把 client 的 token 原樣轉給 ERP API，代表 ERP API 接受了 audience 不是自己的 token，audience 綁定就整個失效；ERP API 看到的是「Amy 直接來呼叫」，MCP server 應該做的限流、稽核與權限判斷都被繞過；而事故調查時，紀錄上看不出這個操作經過了哪個 MCP server。換句話說，passthrough 同時破壞了授權與可歸責。這也是 **confused deputy**（混淆代理人）問題的典型形態：一個有權限的中介者被請求者利用，替請求者做了它本人不該能做的事。防禦的原則是中介者每次都以「原始請求者的權限」加上「自己的能力上限」做判斷，並用自己的身分向下游取得專屬 token。

| 要求 | 誰負責 | 防的是什麼 | 青鳥 v0 的狀況 |
|---|---|---|---|
| 發布 Protected Resource Metadata | MCP server | client 不知道該去哪拿 token，只好用寫死的共用 key | 沒有，用共用 key |
| 授權與 token 請求帶 resource indicator | MCP client | 一張 token 被多個 server 通用 | 沒有 |
| 驗證 audience 是自己 | MCP server（與每個下游） | 偷來的 token 被拿去打別的 server | 沒有驗 |
| 禁止 token passthrough | MCP server | 下游繞過 server 的檢查；稽核斷鏈 | ERP MCP server 直接轉送 |
| PKCE、token 只放 header | client 與 server | 授權碼被攔截；token 出現在 log | token 曾出現在除錯 URL |
| 驗證授權回應的 issuer | MCP client | mix-up：被騙把授權碼送到錯的授權伺服器 | 只有一個 AS，未處理 |
| scope 最小化與 step-up | 兩端 | 一開始就要求所有權限 | 只有管理者 scope |

這張表右欄是青鳥 v0 的體檢結果，幾乎每一項都不合格，但修法並不神祕：表中多數防禦已由授權伺服器與成熟的 client SDK 實作，工程上最重要的是**不要繞過它們**。stdio 型的本機 MCP server 是例外：它跟著使用者的 process 跑，規格允許從環境變數取得憑證，但 33.7 節的 secrets 原則仍然適用。

### 2026 現況：MCP 2026-07-28 版的授權重點

截至 2026 年 10 月，MCP 的最新規格版本是 2026-07-28。依官方規格與 changelog，授權部分的重點如下：授權本身是選用的，HTTP transport 實作授權時應遵循規格，stdio transport 從環境取得憑證；MCP server 是 OAuth 2.1 的 resource server，**必須**實作 RFC 9728 Protected Resource Metadata，client 必須透過它發現授權伺服器；client **必須**在授權與 token 請求中帶 RFC 8707 的 `resource` 參數（MCP server 的 canonical URI），server **必須**驗證 token 的 audience 是自己；server 不得接受或轉送其他 token（禁止 token passthrough）；必須使用 PKCE，token 只能放在 `Authorization: Bearer` header。這一版也新增了 RFC 9207 的 `iss` 驗證以防 mix-up attack，credential 要以 issuer 為 key 保存、不得跨授權伺服器重用；client 註冊優先使用 Client ID Metadata Documents，Dynamic Client Registration（RFC 7591）被標為 deprecated，只為相容而保留；scope 不足時以 403 `insufficient_scope` 做 step-up，並要限制重試次數。另外，官方的 `ext-auth` extension 涵蓋 OAuth client credentials（機器對機器）與企業管理的授權（Enterprise-Managed Authorization）。細節以官方規格為準。

## 33.7 Secrets 管理：憑證不進 context、不進 sandbox

**secret**（機密）是任何能證明身分或授予權限的字串：API key、OAuth 的 access 與 refresh token、資料庫密碼、簽章金鑰、webhook 的共享密鑰。傳統服務的 secrets 原則是「放在 secret manager、不寫進程式碼、定期輪替」。agent 系統要再加一條更嚴的原則：**secrets 不能出現在模型看得到的任何地方**。理由很直接：模型會把 context 裡的內容寫進回答、寫進 tool 參數、寫進程式碼，而 context 裡也可能有 prompt injection 在要求它這麼做。只要 secret 進了 context，它被外洩就只是機率問題。

```text
 錯誤：secret 跟著資料流走
   環境變數 ERP_KEY ──► tool 回傳的 debug 資訊 ──► context ──► 模型 ──► 回答／參數／程式碼 ──► 外洩

 正確：secret 只存在 credential broker 與下游之間
 ┌──────────────── agent 能看到的世界 ────────────────┐
 │ context：「refund(B-1042, 300)」                   │
 │ sandbox：程式碼、暫存檔（沒有任何長效憑證）       │
 └───────────────┬────────────────────────────────────┘
                 │ tool call（只有參數，沒有憑證）
                 ▼
 ┌──────────────────────────┐   以 session 身分取得短效憑證   ┌─────────────────┐
 │ tool gateway / broker    │ ◄─────────────────────────────► │ credential vault│
 │ 注入 Authorization header│      （token exchange、輪替）   │ refresh token   │
 └───────────────┬──────────┘                                 │ 簽章金鑰        │
                 │ 帶短效 token 的請求                        └─────────────────┘
                 ▼
          ERP API / 物流 API / MCP server
 回程：broker 剝除回應中的憑證與敏感 header，DLP 掃描後才交回 context
```

這張圖的上半部是青鳥 v0 的實際事故路徑：某個 tool 為了方便除錯，把請求 header 一起回傳，於是共用 key 進了 context；之後只要有一段夾帶指令的文字要求模型「把設定印出來」，key 就可能出現在回答裡。下半部是修正後的架構。agent 看得到的世界只有 context 與 sandbox，兩者都沒有長效憑證；tool call 只帶業務參數，由 tool gateway 扮演 **credential broker**（憑證代理）：依 session 的身分從 vault 取得或交換一張短效 token，注入到對下游的請求 header 裡。回程時 broker 剝除回應中的憑證與敏感 header，再經過 DLP（資料外洩防護）掃描，才把結果交回 context。

sandbox 尤其要注意。第 17 章的 code execution sandbox 裡跑的是模型寫的程式，任何放進去的憑證都等於交給模型。常見的錯誤是為了讓 agent 能 `git push`，把一把有寫入權限的 token 放進 sandbox 的環境變數。比較安全的做法是讓 sandbox 經過一個 egress proxy 對外連線，由 proxy 依目的地注入短效憑證；或只在 sandbox 初始化（例如 clone repo）時使用憑證，執行模型程式碼之前就移除。

| 洩漏路徑 | 例子 | 防禦 | 怎麼偵測 |
|---|---|---|---|
| system prompt 或 tool 描述 | 把 API key 寫進 prompt「方便模型呼叫」 | secret 永不進 prompt；由 broker 注入 | 對 prompt 版本做 secret 掃描 |
| tool 回傳內容 | 回應帶著請求 header、連線字串 | broker 剝除；tool 回傳 schema 化 | 對 tool result 做 DLP 掃描 |
| sandbox 環境變數或檔案 | `GITHUB_TOKEN` 在環境變數裡 | egress proxy 注入；用完即移除 | 掃描 sandbox 映像與環境 |
| log 與 trace | token 被記進 debug log 或 span 屬性 | 記錄前遮蔽 `Authorization` 等欄位 | log pipeline 的 secret 偵測規則 |
| URL query string | `?access_token=...` 出現在存取紀錄 | 只接受 header | 存取紀錄掃描 |
| 長效共用 key | 所有 agent 共用一把管理者 key | 每個 agent、每個租戶、每次 session 各自的短效憑證 | 盤點憑證的壽命與使用者數 |

這張表的最後一列是根本解法：**讓 secret 本身變得不值錢**。一張只對 ERP API 有效、只能讀單一租戶訂單、六十秒後過期的 token，就算外洩，攻擊者能做的事也非常有限；一把永不過期、管理者權限、所有 agent 共用的 key，外洩一次就是全平台事故。輪替也要自動化：長效憑證（例如簽章金鑰、第三方服務的 client secret）要有輪替排程，並在新舊金鑰重疊的期間同時接受兩者，避免輪替本身造成停機。

> [!tip] 從 log 開始盤點
> 想知道系統裡有多少 secret 曾經進過 context，最快的方法是對過去一段時間的 trace 與 tool result 跑一次 secret 掃描（常見格式的 API key、JWT、私鑰標頭）。青鳥第一次掃描就找到三種來源：tool 回傳的 debug header、店員貼進對話的第三方 API key、以及 research agent 寫進報表的資料庫連線字串。

## 33.8 多租戶隔離：租戶來自 session，不來自模型

青鳥是多租戶 SaaS：數千家店家共用同一套 agent、同一組資料庫與向量索引。**多租戶隔離**的目標是：任何一個租戶的使用者，經由任何路徑，都不能讀到或影響另一個租戶的資料。傳統 SaaS 已經有成熟的做法（每個查詢都帶租戶條件、資料庫的 row-level security），agent 加入了一個新變數：查詢參數由模型產生，而模型的輸入包含外部內容。Maya 在故事中挖出的 `tenant_id` 事故，就是這個變數造成的。

```text
 登入 ──► session：{tenant: komori, user: amy, agent: cs-agent@3.2}   ← 唯一的租戶來源
             │
             ▼ harness 建立 tool 實例時就綁定租戶（模型的參數裡沒有這個欄位）
 ┌──────────────────────────────────────────────────────────────────────┐
 │ tool 參數（模型產生）：{order_id: "B-2077"}                          │
 │   └─ 若出現 tenant / tenant_id / user_id ──► 拒絕並記錄（不是忽略） │
 └───────────────┬──────────────────────────────────────────────────────┘
                 ▼ 每一層都用 session 的租戶，不信任上一層「已經檢查過」
   資料庫        WHERE tenant = :session_tenant（加上 row-level security 雙保險）
   向量索引      依租戶分 namespace，在召回前過濾（pre-filter）
   memory        路徑由 harness 依租戶與使用者決定（第 12 章）
   cache         key 包含租戶與權限範圍
   sandbox       每個任務或租戶一個用完即丟的環境
   配額          每個租戶各自的 rate limit 與 token 預算
                 ▼
 回應：別家的 B-2077 與不存在的 B-9999，回傳一模一樣的「找不到訂單」
```

這張圖由上往下讀。第一行是整個設計的根：**租戶只有一個來源，就是已認證的 session**。harness 建立 tool 實例時就把租戶綁進去，tool 的參數 schema 裡根本沒有租戶欄位，所以模型無從填寫。如果模型的參數裡還是出現了 `tenant_id` 之類的欄位，middleware 應該拒絕並記錄，而不是默默忽略；因為這通常代表有內容在試圖影響模型，值得被告警。中間是縱深防禦：資料庫、向量索引、memory、cache、sandbox、配額，每一層都獨立地以 session 的租戶做隔離，不依賴上一層的檢查。最後一行是一個容易被忽略的細節：別家的訂單和不存在的訂單要回傳完全相同的錯誤，否則攻擊者可以用「查不到」與「無權限」的差別探測出別家有哪些訂單編號。A2A 規格也明文要求 server 不得區分「不存在」與「未授權」，就是這個理由。

| 隔離層 | 共用的東西 | 隔離做法 | 常見漏洞 |
|---|---|---|---|
| 身分與租戶情境 | 同一個 agent 服務 | 租戶只來自 session；tool 參數沒有租戶欄位 | 模型填 `tenant_id`；從 prompt 讀店名推斷租戶 |
| 交易資料庫 | 同一組資料表 | 每個查詢帶租戶條件＋row-level security | 少數報表查詢忘了加條件 |
| 向量索引與檢索 | 同一個索引 | 依租戶分 namespace 或 pre-filter（第 11 章） | 先取前 k 名再過濾（post-filter） |
| memory 與 workspace | 同一個儲存系統 | harness 依身分決定路徑（第 12 章） | 路徑穿越；模型提供路徑 |
| 應用層 cache | 同一個 cache | key 包含租戶與權限範圍 | semantic cache 跨租戶命中 |
| sandbox | 同一組機器 | 每個任務或租戶獨立、用完即丟 | 重複使用含有前一個任務檔案的環境 |
| 配額與成本 | 同一個模型 API 額度 | 每租戶的 rate limit 與預算 | 一家店的批次任務拖垮所有人（noisy neighbor） |
| 稽核與 trace | 同一個 log 系統 | 依租戶分鏈、依租戶授權查詢 | 店家支援人員能查所有店家的 trace |

表中最後一列提醒我們，稽核資料本身也是租戶資料：一筆稽核紀錄裡有訂單編號、金額、店員帳號，店家 A 的管理員不能查到店家 B 的紀錄。青鳥的做法是每個租戶一條獨立的稽核鏈（下一節），既方便隔離與匯出，也讓一個租戶的資料保存與刪除政策不會影響其他租戶。配額那一列看起來和安全無關，但它是可用性的隔離：一家店跑了一個失控的 research 任務，不應該讓所有店家的客服 agent 都被 rate limit 擋住。

> [!warning] 常見誤解
> 「system prompt 裡已經寫了『只能查本店資料』，模型很聽話。」system prompt 是對模型的指示，不是對資料的保證。模型會被對話內容、檢索結果與 tool 輸出影響，第 31 章已經說明 prompt injection 沒有可靠的模型層解法。隔離必須是確定性的程式：租戶來自 session、查詢條件由 harness 加上、資料庫再做一次 row-level 檢查。

## 33.9 稽核日誌與不可否認性

回到故事的最後一個問題：核准者欄位寫著 `amy`，但沒有人能證明這個值不是事後改的。**audit log**（稽核日誌）是專門用來回答「是誰、代表誰、憑什麼、做了什麼」的紀錄，它和第 29 章的 trace 看起來相似，用途卻不同。trace 是給工程師除錯用的：內容詳盡、保存期限短、可以取樣、隨時可以調整格式；稽核日誌是給事後追責用的：內容固定、保存期限依法規與合約、不能取樣、不能被修改。兩者用 trace id 互相關聯，但要分開儲存、分開授權。

| 欄位 | 例子 | 為什麼要記 |
|---|---|---|
| 時間與序號 | `ts=160`、`seq=2` | 排序與偵測缺漏 |
| 租戶 | `komori` | 隔離與依租戶匯出 |
| 主體（代表誰） | `user:amy` | 意圖來源 |
| 行動者與代理鏈 | `agent:cs-agent@3.2` | 是哪個 agent、哪個版本做的 |
| model 與 prompt 版本 | `cs-system@v41` | 同一句話在不同版本可能有不同行為 |
| tool 與參數（敏感欄位遮罩） | `refund {B-1042, 3200}` | 實際做了什麼 |
| 授權決定與理由 | `allow`、`step_up`、`deny` | 被擋下的嘗試同樣重要 |
| 核准者與核准 id | `user:chen`、`AP-551` | 高風險動作的責任歸屬 |
| 結果 | `RF-1042` 或錯誤 | 動作是否真的生效 |
| trace id | `tr-9f2` | 連到詳細的 trace 做除錯 |

這張表有兩個容易被省略的欄位。一是**被拒絕的嘗試**：deny 與 step_up 也要記，因為「agent 試圖用 `tenant_id` 查別家訂單」這種事件，是發現 prompt injection 或設計缺陷的最佳訊號。二是**敏感欄位的處理**：稽核日誌要長期保存，所以不能存放不必要的個資明文。一個實用的做法是對敏感欄位存「帶金鑰的雜湊」（例如以每個租戶的金鑰計算 HMAC）：事後可以驗證「當時通知的是不是這個 email」，但無法從紀錄反推出 email 本身。

有了正確的內容，接著要讓它不能被竄改。第一層是 **append-only**（只能追加）：應用程式只有新增權限，沒有修改與刪除權限。但這只防得了應用程式，防不了資料庫管理員或拿到管理權限的攻擊者。第二層是 **hash chain**（雜湊鏈）：每一筆紀錄都包含前一筆紀錄的雜湊值，自己的雜湊則涵蓋全部內容加上前一筆的雜湊。改動任何一筆，它的雜湊就變了，下一筆的 `prev` 就對不上，一路對不上到最後。

```text
  #0                     #1                     #2                         #3
 ┌────────────────┐     ┌────────────────┐     ┌────────────────────┐     ┌────────────────┐
 │ get_order allow│     │ refund step_up │     │ refund allow       │     │ notify allow   │
 │ prev = 000…    │  ┌─►│ prev = d2c8…   │  ┌─►│ prev = 6e7f…       │  ┌─►│ prev = 5b05…   │
 │ hash = d2c8… ──┼──┘  │ hash = 6e7f… ──┼──┘  │ approver=user:chen │  │  │ hash = bbfd…   │
 └────────────────┘     └────────────────┘     │ hash = 5b05… ──────┼──┘  └───────┬────────┘
                                               └────────────────────┘             │
   hash = SHA-256(正規化後的「本筆內容＋prev」)                                  │ 定期
                                                                                  ▼
                               另一個信任域：checkpoint {seq: 3, hash: bbfd…, 簽章}
                               （WORM 儲存、不同帳號、外部時間戳服務）

 改 #2 的 approver ──► #2 的 hash 重算後不符 ──► 抓得到
 改完把 #2、#3 重算 ──► 鏈本身自洽 ──► 只有 checkpoint 抓得到
 刪掉 #3 ──► 鏈本身自洽 ──► 只有 checkpoint（記著 seq 3）抓得到
```

這張圖的上半部是鏈本身：#0 的 `prev` 是固定的起點，之後每一筆的 `prev` 都是前一筆的 `hash`。雜湊的輸入要先**正規化**（欄位排序、固定格式），否則同樣的內容可能算出不同的值。下半部是 hash chain 最常被誤解的地方：**鏈本身只能證明「內部一致」，不能證明「沒有被整條重寫」**。一個有資料庫寫入權限的人，可以修改 #2 之後把 #2、#3 的雜湊全部重算，整條鏈依然自洽；也可以直接刪掉最後幾筆，剩下的鏈同樣自洽。要抓到這兩種竄改，必須定期把最新的序號與雜湊（稱為 **checkpoint** 或 anchor）簽章後送到另一個信任域：例如有 WORM（write once, read many，寫入後在保存期限內不能修改或刪除）保護的儲存、由另一個團隊管理的帳號，或外部的時間戳服務。攻擊者必須同時控制兩個信任域，才能不留痕跡地竄改。

**non-repudiation**（不可否認性）又比防竄改更進一步：它要讓行動者事後無法否認「這是我做的」。hash chain 證明紀錄沒被改，但不能證明核准真的是陳主管按的；要做到這點，核准動作本身要帶著只有核准者能產生的證明，例如核准時的強認證（MFA 或硬體金鑰）加上授權伺服器簽發、寫著核准者身分的 approval token。33.5 節的 step-up token 正好扮演這個角色：稽核紀錄裡存的不只是「approver=user:chen」這個字串，而是一張可以被獨立驗證的簽章憑證的 id。

最後是保存與刪除的張力。稽核日誌要求不可刪除，隱私法規卻可能要求在特定情況下刪除個人資料。常見的解法是不在稽核紀錄裡存個資明文（前面說的金鑰雜湊），或把個資用每個資料主體各自的金鑰加密，需要刪除時銷毀該金鑰（稱為 crypto-shredding），紀錄本身與雜湊鏈則保持完整。哪一種做法符合特定法規的要求，需要和法務一起確認，第 34 章會談治理流程。

## 33.10 動手做：loom.auth 授權 middleware 與 hash-chained 稽核日誌

這一節給 `loom` 加上 `loom.auth` 模組，分成兩段程式。第一段是授權 middleware：授權伺服器簽發短效 token、tool 呼叫下游時做 token exchange、middleware 在每次 dispatch 前檢查簽章、期限、audience、scope 與租戶，並對大額退款要求 step-up。第二段是 hash-chained 稽核日誌與它的驗證程式，示範它抓得到哪些竄改、哪些只有 checkpoint 抓得到。為了只用標準函式庫，token 用 HMAC 簽章；真實系統通常用非對稱簽章的 JWT，resource server 只持有授權伺服器的公鑰（經由 JWKS 取得），不必共享任何密鑰，這是教學版與正式版最大的差別。

### 第一段：授權 middleware、token exchange 與 step-up

程式的結構依序是：全書統一的 ScriptedModel；`loom.auth` 本體（`AuthServer`、`AuthMiddleware` 與一個只保留授權邏輯的最小 loop）；扮演下游 resource server 的假 ERP API；最後是五個情境。注意 tool 函式拿到的 `ctx` 由 harness 注入，裡面有使用者的 token 與 agent 的身分，模型的參數碰不到它。為了精簡，Amy 的 token 直接以 tool gateway 為受眾簽發，相當於 33.4 節時序圖中的 t1；tool 呼叫 ERP 前再換一次，相當於圖中最後一跳。

```python
from __future__ import annotations

import base64
import hashlib
import hmac
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


# ───────────────────────── loom.auth（教學版）─────────────────────────
class Clock:
    """模擬時鐘：讓「token 過期」可以在測試裡重現，而不用真的等。"""
    def __init__(self, now: int = 1_000_000):
        self.now = now


class TokenError(Exception):
    pass


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


class AuthServer:
    """簽發短效 token 與做 token exchange。真實系統用非對稱簽章（JWT＋JWKS），這裡用 HMAC 只為了只靠標準函式庫。"""

    def __init__(self, issuer: str, key: bytes, clock: Clock):
        self.issuer, self.key, self.clock = issuer, key, clock

    def issue(self, sub: str, tenant: str, scope: str, aud: str, ttl: int, **extra: Any) -> str:
        claims = {"iss": self.issuer, "sub": sub, "tenant": tenant, "scope": scope, "aud": aud,
                  "iat": self.clock.now, "exp": self.clock.now + ttl, **extra}
        body = _b64(json.dumps(claims, sort_keys=True).encode())
        return body + "." + _b64(hmac.new(self.key, body.encode(), hashlib.sha256).digest())

    def verify(self, token: str, audience: str, leeway: int = 30) -> dict:
        """resource server 每次都要做的四項檢查：簽章、issuer、期限、audience。"""
        body, _, sig = token.partition(".")
        good = _b64(hmac.new(self.key, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, good):
            raise TokenError("簽章不符")
        claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if claims["iss"] != self.issuer:
            raise TokenError("issuer 不符")
        if self.clock.now > claims["exp"] + leeway:
            raise TokenError("token 已過期，需要重新登入")
        if claims["aud"] != audience:
            raise TokenError(f"這張 token 的 audience 是 {claims['aud']}，不是 {audience}")
        return claims

    def exchange(self, subject_token: str, its_aud: str, actor: str, audience: str, scope: str) -> str:
        """token exchange：只能縮小 scope、換成指定受眾、壽命不超過原 token，並在 act 記下行動者。"""
        c = self.verify(subject_token, its_aud)
        if not set(scope.split()) <= set(c["scope"].split()):
            raise TokenError(f"不能換到原 token 沒有的 scope：{scope}")
        act = {"sub": actor, **({"act": c["act"]} if "act" in c else {})}
        ttl = min(60, c["exp"] - self.clock.now)
        return self.issue(c["sub"], c["tenant"], scope, audience, ttl, act=act)


@dataclass
class ToolSpec:
    name: str
    scope: str                                            # 呼叫這個 tool 需要的 scope
    fn: Callable[[dict, dict], Any]                       # fn(ctx, args)；ctx 由 harness 注入，模型碰不到
    needs_step_up: Callable[[dict], bool] = lambda args: False


@dataclass
class Decision:
    effect: str                                           # allow｜deny｜step_up
    reason: str


class AuthMiddleware:
    """在 dispatch 之前做授權。身分與租戶一律來自 token，不來自模型產生的參數。"""
    FORBIDDEN_ARGS = {"tenant", "tenant_id", "user_id", "as_user"}

    def __init__(self, auth: AuthServer, tools: dict[str, ToolSpec], audience: str):
        self.auth, self.tools, self.audience = auth, tools, audience
        self.used_grants: set[str] = set()

    def check(self, token: str, tc: ToolCall) -> tuple[Decision, dict | None]:
        try:
            claims = self.auth.verify(token, self.audience)
        except TokenError as exc:
            return Decision("deny", f"驗證失敗：{exc}"), None
        spec = self.tools[tc.name]
        if self.FORBIDDEN_ARGS & tc.args.keys():
            return Decision("deny", f"參數 {sorted(self.FORBIDDEN_ARGS & tc.args.keys())} 不允許：身分由 session 決定"), claims
        if spec.scope not in claims["scope"].split():
            return Decision("deny", f"insufficient_scope：需要 {spec.scope}"), claims
        if spec.needs_step_up(tc.args):
            grant = claims.get("approved")                # 綁定單筆交易的核准，不是泛用的高權限
            if grant is None or grant["call"] != {"tool": tc.name, **tc.args}:
                return Decision("step_up", f"金額 {tc.args.get('amount')} 超過自動核准門檻 500，需要主管核准"), claims
            if grant["id"] in self.used_grants:           # 核准只能用一次，防止重送同一張 token
                return Decision("step_up", f"核准 {grant['id']} 已使用過"), claims
            self.used_grants.add(grant["id"])
        return Decision("allow", "ok"), claims


def run(model, mw: AuthMiddleware, token: str, ctx: dict, user_input: str, audit: list, max_steps: int = 6):
    """把第 4 章的 loop 縮到最小，只保留和授權有關的部分。回傳 (status, output)。"""
    messages: list[dict] = [{"role": "user", "content": user_input}]
    for _ in range(max_steps):
        resp = model.complete(messages)
        messages.append({"role": "assistant", "content": resp.text, "tool_calls": [vars(t) for t in resp.tool_calls]})
        if not resp.tool_calls:
            return "done", resp.text
        for tc in resp.tool_calls:
            decision, claims = mw.check(token, tc)
            who = claims["sub"] if claims else "?"
            audit.append({"who": who, "agent": ctx["agent_id"], "tool": tc.name, "args": tc.args,
                          "effect": decision.effect, "approver": (claims or {}).get("approver")})
            print(f"  {tc.name}({json.dumps(tc.args, ensure_ascii=False)}) → {decision.effect}  {decision.reason}")
            if decision.effect != "allow":                # 權限問題不回填讓模型「想辦法」，直接中斷
                messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name,
                                 "content": decision.reason, "is_error": True})
                return ("step_up" if decision.effect == "step_up" else "denied"), decision.reason
            try:
                out, is_error = json.dumps(mw.tools[tc.name].fn({**ctx, "token": token}, tc.args), ensure_ascii=False), False
            except LookupError as exc:
                out, is_error = str(exc), True
            print(f"      ⤷ {out}")
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": out, "is_error": is_error})
    return "max_steps", ""
# ─────────────────────── loom.auth 結束 ───────────────────────


# 下游的 ERP API：它是另一個 resource server，只收 audience 是自己的 token
class ErpApi:
    ORDERS = {"B-1042": {"tenant": "komori", "amount": 3200, "status": "delivered"},
              "B-2077": {"tenant": "harbor", "amount": 980, "status": "delivered"}}

    def __init__(self, auth: AuthServer):
        self.auth, self.calls = auth, []

    def get_order(self, token: str, order_id: str) -> dict:
        c = self.auth.verify(token, "erp-api")
        self.calls.append(c)
        order = self.ORDERS.get(order_id)
        if order is None or order["tenant"] != c["tenant"]:   # 別家的訂單和不存在的訂單，回應一模一樣
            raise LookupError(f"找不到訂單 {order_id}")
        return {"order_id": order_id, "amount": order["amount"], "status": order["status"]}

    def refund(self, token: str, order_id: str, amount: int) -> dict:
        c = self.auth.verify(token, "erp-api")
        if "refunds:write" not in c["scope"].split():
            raise TokenError("ERP：scope 不足")
        self.get_order(token, order_id)
        return {"refund_id": "RF-" + order_id[2:], "amount": amount, "by": c["act"]["sub"]}


clock = Clock()
auth = AuthServer("https://id.bluebird.example", b"demo-signing-key", clock)
erp = ErpApi(auth)
AGENT = "agent:cs-agent@3.2"


def downstream(ctx: dict, scope: str) -> str:
    """tool 不轉送使用者的 token，而是換一張 aud=erp-api、scope 最小、60 秒的新 token。"""
    return ctx["auth"].exchange(ctx["token"], "tool-gateway", ctx["agent_id"], "erp-api", scope)


TOOLS = {
    "get_order": ToolSpec("get_order", "orders:read",
                          lambda ctx, a: erp.get_order(downstream(ctx, "orders:read"), a["order_id"])),
    "refund": ToolSpec("refund", "refunds:write",
                       lambda ctx, a: erp.refund(downstream(ctx, "orders:read refunds:write"), a["order_id"], a["amount"]),
                       needs_step_up=lambda a: a["amount"] > 500),       # 第 1 章：500 元以下才在 L4 自動
}
mw = AuthMiddleware(auth, TOOLS, audience="tool-gateway")
ctx = {"auth": auth, "agent_id": AGENT}
audit: list[dict] = []
amy = auth.issue("user:amy", "komori", "orders:read refunds:write", "tool-gateway", ttl=300)

print("── A 小額退款：自動放行，下游 token 帶著代理鏈")
s, out = run(ScriptedModel([call("get_order", order_id="B-1042"),
                            call("refund", "c2", order_id="B-1042", amount=300), say("已退 300 元。")]),
             mw, amy, ctx, "B-1042 少寄一件，退 300", audit)
print(f"  status={s}；ERP 最後看到 aud={erp.calls[-1]['aud']} scope={erp.calls[-1]['scope']!r} act={erp.calls[-1]['act']}")
assert s == "done" and erp.calls[-1]["act"] == {"sub": AGENT}

print("── B 跨租戶：別家的訂單查不到；想用參數指定租戶，直接拒絕")
s, out = run(ScriptedModel([call("get_order", order_id="B-2077"),
                            call("get_order", "c2", order_id="B-2077", tenant_id="harbor")]),
             mw, amy, ctx, "幫我看 B-2077", audit)
print(f"  status={s}")
assert s == "denied"

print("── C 大額退款：step-up，主管核准後拿到只對這一筆有效的 token")
script = [call("refund", order_id="B-1042", amount=3200)]
s, out = run(ScriptedModel(script), mw, amy, ctx, "B-1042 全額退款", audit)
print(f"  status={s}")
approved = auth.issue("user:amy", "komori", "orders:read refunds:write", "tool-gateway", ttl=120,
                      approved={"id": "AP-551", "call": {"tool": "refund", "order_id": "B-1042", "amount": 3200}},
                      approver="user:chen")
s, out = run(ScriptedModel([call("refund", order_id="B-1042", amount=3200), say("已全額退款。")]),
             mw, approved, ctx, "（核准後重送）", audit)
s2, _ = run(ScriptedModel([call("refund", order_id="B-1042", amount=3100)]), mw, approved, ctx, "改成 3100", audit)
s3, _ = run(ScriptedModel([call("refund", order_id="B-1042", amount=3200)]), mw, approved, ctx, "再退一次", audit)
print(f"  status={s}；拿同一張核准改金額 → {s2}；原封不動重送 → {s3}")
assert s == "done" and s2 == s3 == "step_up"

print("── D token passthrough：把使用者的 token 直接轉給 ERP")
try:
    erp.get_order(amy, "B-1042")
except TokenError as exc:
    print("  ERP 拒絕：", exc)

print("── E 過期：時鐘前進 331 秒")
clock.now += 331
s, out = run(ScriptedModel([call("get_order", order_id="B-1042")]), mw, amy, ctx, "再查一次", audit)
print(f"  status={s}")
assert s == "denied" and "過期" in out

effects = [a["effect"] for a in audit]
print(f"稽核事件 {len(audit)} 筆：", {e: effects.count(e) for e in ("allow", "deny", "step_up")})
assert effects.count("step_up") == 3 and effects.count("deny") == 2
assert [a["approver"] for a in audit if a["tool"] == "refund" and a["effect"] == "allow"] == [None, "user:chen"]
```

```text
── A 小額退款：自動放行，下游 token 帶著代理鏈
  get_order({"order_id": "B-1042"}) → allow  ok
      ⤷ {"order_id": "B-1042", "amount": 3200, "status": "delivered"}
  refund({"order_id": "B-1042", "amount": 300}) → allow  ok
      ⤷ {"refund_id": "RF-1042", "amount": 300, "by": "agent:cs-agent@3.2"}
  status=done；ERP 最後看到 aud=erp-api scope='orders:read refunds:write' act={'sub': 'agent:cs-agent@3.2'}
── B 跨租戶：別家的訂單查不到；想用參數指定租戶，直接拒絕
  get_order({"order_id": "B-2077"}) → allow  ok
      ⤷ 找不到訂單 B-2077
  get_order({"order_id": "B-2077", "tenant_id": "harbor"}) → deny  參數 ['tenant_id'] 不允許：身分由 session 決定
  status=denied
── C 大額退款：step-up，主管核准後拿到只對這一筆有效的 token
  refund({"order_id": "B-1042", "amount": 3200}) → step_up  金額 3200 超過自動核准門檻 500，需要主管核准
  status=step_up
  refund({"order_id": "B-1042", "amount": 3200}) → allow  ok
      ⤷ {"refund_id": "RF-1042", "amount": 3200, "by": "agent:cs-agent@3.2"}
  refund({"order_id": "B-1042", "amount": 3100}) → step_up  金額 3100 超過自動核准門檻 500，需要主管核准
  refund({"order_id": "B-1042", "amount": 3200}) → step_up  核准 AP-551 已使用過
  status=done；拿同一張核准改金額 → step_up；原封不動重送 → step_up
── D token passthrough：把使用者的 token 直接轉給 ERP
  ERP 拒絕： 這張 token 的 audience 是 tool-gateway，不是 erp-api
── E 過期：時鐘前進 331 秒
  get_order({"order_id": "B-1042"}) → deny  驗證失敗：token 已過期，需要重新登入
  status=denied
稽核事件 9 筆： {'allow': 4, 'deny': 2, 'step_up': 3}
```

逐段解說這份輸出。

**情境 A（小額退款）**是正常路徑。兩次 tool call 都通過 middleware；`refund` 的金額 300 低於 500 元的自動邊界，所以直接放行。關鍵在最後一行：ERP 收到的 token，受眾是 `erp-api`，`act` 寫著 cs-agent 的身分。也就是說，tool 並沒有把 Amy 的 token 轉送下去，而是用 `downstream()` 換了一張新的；ERP 的紀錄上終於看得出「這是 cs-agent 代表 Amy 做的」，而不是 `bluebird-integration`。

**情境 B（跨租戶）**示範兩種不同的防線。第一次呼叫查別家的 B-2077，middleware 放行（Amy 有 `orders:read`），但 ERP 依 token 上的租戶判斷這張訂單不屬於 komori，回傳和不存在時一模一樣的「找不到訂單」，模型無從得知 B-2077 是別家的訂單還是根本不存在。第二次模型試圖在參數裡加上 `tenant_id`，middleware 直接拒絕，run 以 `denied` 結束。這裡刻意不把錯誤回填讓模型「再想想」：試圖指定租戶本身就是異常訊號，應該中止並告警。

**情境 C（大額退款與 step-up）**分成四步。第一次呼叫金額 3,200，超過自動邊界，middleware 回傳 `step_up`，run 暫停。接著模擬主管 `user:chen` 核准：授權伺服器簽發一張 120 秒的 token，裡面的 `approved` 綁定了核准 id、tool、訂單與金額。resume 時重送同一個 tool call，middleware 比對參數完全相同且核准未使用過，放行並執行。後兩行是反向測試：拿同一張核准 token 把金額改成 3,100，或原封不動再送一次，都會被要求重新 step-up。核准是「對這一筆、這一次」的授權，不是一張通行證。

**情境 D（token passthrough）**直接把 Amy 給 tool gateway 的 token 拿去打 ERP，ERP 以「這張 token 的 audience 是 tool-gateway，不是 erp-api」拒絕。這正是 audience 檢查的價值：就算某個 tool 的實作偷懶想轉送 token，下游也不會接受。**情境 E（過期）**把模擬時鐘往前推 331 秒，超過 300 秒的壽命加上 30 秒的時鐘誤差容許值，middleware 以「token 已過期」拒絕。最後一行統計了 9 筆授權事件，其中 allow 4 筆、deny 2 筆、step_up 3 筆；assert 也驗證了 B-1042 的兩次成功退款中，小額那筆沒有核准者、大額那筆的核准者是 `user:chen`。這些事件就是下一段稽核日誌的輸入。

### 第二段：hash-chained 稽核日誌與驗證

第二段實作 `AuditLog`：每筆紀錄包含前一筆的雜湊，敏感欄位以租戶金鑰做 HMAC 後才寫入，並可以產生簽章過的 checkpoint。`verify()` 檢查序號連續、`prev` 相連、內容與雜湊相符，有 checkpoint 時再比對尾端。最後模擬四種竄改：改內容、刪中間、改完整條重算、截掉尾端。

```python
from __future__ import annotations

import copy
import hashlib
import hmac
import json

GENESIS = "0" * 64
SENSITIVE = {"email", "phone", "card_last4"}


def canonical(obj: dict) -> bytes:
    """雜湊前先正規化：key 排序、固定分隔符號。少了這一步，同樣的內容會算出不同的 hash。"""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


class AuditLog:
    """append-only＋hash chain：每筆紀錄都包含前一筆的 hash，改任何一筆，後面全部對不上。"""

    def __init__(self, tenant: str, pii_key: bytes):
        self.tenant, self.pii_key = tenant, pii_key
        self.records: list[dict] = []

    def _redact(self, args: dict) -> dict:
        # 敏感欄位不存明文，存「帶金鑰的雜湊」：日後能證明「是不是這個值」，但無法從紀錄反推
        return {k: ("hmac:" + hmac.new(self.pii_key, str(v).encode(), hashlib.sha256).hexdigest()[:16]
                    if k in SENSITIVE else v) for k, v in args.items()}

    def append(self, ts: int, event: dict) -> dict:
        rec = {"seq": len(self.records), "ts": ts, "tenant": self.tenant,
               **event, "args": self._redact(event.get("args", {})),
               "prev": self.records[-1]["hash"] if self.records else GENESIS}
        rec["hash"] = hashlib.sha256(canonical(rec)).hexdigest()
        self.records.append(rec)
        return rec

    def checkpoint(self, signing_key: bytes) -> dict:
        """定期把「最新 seq＋hash」簽章後送到另一個信任域（WORM 儲存、另一個帳號、外部時間戳服務）。"""
        head = {"tenant": self.tenant, "seq": self.records[-1]["seq"], "hash": self.records[-1]["hash"]}
        return {**head, "sig": hmac.new(signing_key, canonical(head), hashlib.sha256).hexdigest()}


def verify(records: list[dict], checkpoint: dict | None = None, signing_key: bytes = b"") -> list[str]:
    problems, prev = [], GENESIS
    for i, rec in enumerate(records):
        body = {k: v for k, v in rec.items() if k != "hash"}
        if rec["seq"] != i:
            problems.append(f"#{i} seq 應為 {i}，實際 {rec['seq']}（中間有紀錄被刪除或插入）")
        if rec["prev"] != prev:
            problems.append(f"#{i} prev 對不上前一筆的 hash")
        if hashlib.sha256(canonical(body)).hexdigest() != rec["hash"]:
            problems.append(f"#{i} 內容與 hash 不符（紀錄被修改）")
        prev = rec["hash"]
    if checkpoint:
        head = {k: checkpoint[k] for k in ("tenant", "seq", "hash")}
        if not hmac.compare_digest(checkpoint["sig"], hmac.new(signing_key, canonical(head), hashlib.sha256).hexdigest()):
            problems.append("checkpoint 簽章無效")
        at = [r for r in records if r["seq"] == checkpoint["seq"]]
        if not at:
            problems.append(f"checkpoint 記到 seq {checkpoint['seq']}，紀錄只到 {len(records) - 1}（尾端被截斷）")
        elif at[0]["hash"] != checkpoint["hash"]:
            problems.append(f"seq {checkpoint['seq']} 的 hash 和 checkpoint 不同（整條鏈被重算過）")
    return problems


def rechain(records: list[dict]) -> list[dict]:
    """模擬有資料庫寫入權限的內部人員：改完內容後把整條鏈重新計算一遍。"""
    prev = GENESIS
    for rec in records:
        rec["prev"] = prev
        rec["hash"] = hashlib.sha256(canonical({k: v for k, v in rec.items() if k != "hash"})).hexdigest()
        prev = rec["hash"]
    return records


log = AuditLog("komori", pii_key=b"tenant-komori-pii-key")
base = {"actor": "agent:cs-agent@3.2", "on_behalf_of": "user:amy", "trace_id": "tr-9f2"}
log.append(100, {**base, "tool": "get_order", "args": {"order_id": "B-1042"}, "effect": "allow"})
log.append(101, {**base, "tool": "refund", "args": {"order_id": "B-1042", "amount": 3200}, "effect": "step_up"})
log.append(160, {**base, "tool": "refund", "args": {"order_id": "B-1042", "amount": 3200}, "effect": "allow",
                 "approver": "user:chen", "model": "frontier-model@2026-09", "prompt": "cs-system@v41"})
log.append(162, {**base, "tool": "notify", "args": {"email": "kao@example.com"}, "effect": "allow"})
log.append(170, {**base, "tool": "get_order", "args": {"order_id": "B-1042"}, "effect": "allow"})
KEY = b"audit-checkpoint-key"
cp = log.checkpoint(KEY)

for r in log.records:
    print(f"#{r['seq']} {r['tool']:<9} {r['effect']:<7} prev={r['prev'][:8]} hash={r['hash'][:8]} args={r['args']}")
print("checkpoint：", {k: (v[:8] if k in ("hash", "sig") else v) for k, v in cp.items()})

cases = {"原始紀錄": copy.deepcopy(log.records)}
t = copy.deepcopy(log.records); t[2]["approver"] = "user:amy"; cases["改掉核准者"] = t
t = copy.deepcopy(log.records); del t[1]; cases["刪掉中間一筆"] = t
t = copy.deepcopy(log.records); t[2]["args"]["amount"] = 320; cases["改金額後重算整條鏈"] = rechain(t)
cases["截掉尾端兩筆"] = copy.deepcopy(log.records)[:3]

results = {}
for name, recs in cases.items():
    chain_only = verify(recs)
    with_cp = verify(recs, cp, KEY)
    results[name] = (chain_only, with_cp)
    print(f"{name:<10} 只驗鏈：{'通過' if not chain_only else chain_only[0]}")
    print(f"{'':<10} 加 checkpoint：{'通過' if not with_cp else with_cp[-1]}")

assert results["原始紀錄"] == ([], [])
assert results["改掉核准者"][0] and results["刪掉中間一筆"][0]
assert results["改金額後重算整條鏈"][0] == [] and results["改金額後重算整條鏈"][1]   # 只有外部 checkpoint 抓得到
assert results["截掉尾端兩筆"][0] == [] and "截斷" in results["截掉尾端兩筆"][1][-1]
assert log.records[3]["args"]["email"].startswith("hmac:")
```

```text
#0 get_order allow   prev=00000000 hash=d2c83b76 args={'order_id': 'B-1042'}
#1 refund    step_up prev=d2c83b76 hash=6e7fc4e0 args={'order_id': 'B-1042', 'amount': 3200}
#2 refund    allow   prev=6e7fc4e0 hash=5b0562a6 args={'order_id': 'B-1042', 'amount': 3200}
#3 notify    allow   prev=5b0562a6 hash=bbfde36e args={'email': 'hmac:a43015018daf95d7'}
#4 get_order allow   prev=bbfde36e hash=8ffe925c args={'order_id': 'B-1042'}
checkpoint： {'tenant': 'komori', 'seq': 4, 'hash': '8ffe925c', 'sig': 'bc31cc28'}
原始紀錄       只驗鏈：通過
           加 checkpoint：通過
改掉核准者      只驗鏈：#2 內容與 hash 不符（紀錄被修改）
           加 checkpoint：#2 內容與 hash 不符（紀錄被修改）
刪掉中間一筆     只驗鏈：#1 seq 應為 1，實際 2（中間有紀錄被刪除或插入）
           加 checkpoint：#3 seq 應為 3，實際 4（中間有紀錄被刪除或插入）
改金額後重算整條鏈  只驗鏈：通過
           加 checkpoint：seq 4 的 hash 和 checkpoint 不同（整條鏈被重算過）
截掉尾端兩筆     只驗鏈：通過
           加 checkpoint：checkpoint 記到 seq 4，紀錄只到 2（尾端被截斷）
```

前五行是鏈本身：#0 的 `prev` 是全零的起點，之後每一筆的 `prev` 都等於前一筆的 `hash`。#3 的 `email` 已經變成 `hmac:` 開頭的雜湊值，日誌裡沒有 email 明文。第六行是 checkpoint：記著「komori 這條鏈目前到 seq 4，最後一筆的雜湊是 8ffe925c」，並附上簽章；正式系統會把它定期寫到另一個信任域。

接下來是四種竄改的結果，每種印兩行：只驗鏈的結果，以及加上 checkpoint 之後的結果（印出最後一個問題）。**改掉核准者**：把 #2 的 approver 從 chen 改成 amy，#2 的內容和雜湊立刻對不上，只驗鏈就抓得到。**刪掉中間一筆**：刪掉 #1 後，序號出現跳號、`prev` 也斷了，同樣只驗鏈就抓得到；加上 checkpoint 那一行印的是最後一個問題（原本的 #4 落在 index 3），代表從刪除點之後每一筆都被標出來。真正的重點是後兩種。**改金額後重算整條鏈**：內部人員把 3,200 改成 320 後重算所有雜湊，只驗鏈的結果是「通過」，鏈本身完全自洽；只有和外部 checkpoint 比對時，才發現 seq 4 的雜湊和當時記下的不同。**截掉尾端兩筆**：刪掉最後兩筆，剩下的鏈同樣「通過」，只有 checkpoint 記著「應該到 seq 4」才抓得到。assert 把這四個結論全部鎖住。

這兩段程式合起來回答了故事裡的四個問題：是誰（token 的 `sub` 與 `act`）、代表誰（`on_behalf_of`）、憑什麼（scope 與綁定單筆交易的核准 token）、做了什麼（帶雜湊鏈與 checkpoint 的稽核紀錄）。

| 能力 | 青鳥 v0 | 加上 `loom.auth` 之後 | 對應小節 |
|---|---|---|---|
| 下游看得到的身分 | 共用的 `bluebird-integration` | 使用者＋代理鏈（`sub`、`act`） | 33.3、33.4 |
| 憑證 | 長效管理者 key | 每跳 60–300 秒、受眾綁定、只縮不放 | 33.4、33.7 |
| 大額退款 | 核准存在可改的資料表欄位 | step-up token 綁定單筆交易、只能用一次 | 33.5 |
| 下游驗證 | 不驗 audience，接受轉送的 token | 每一跳驗 audience，拒絕 passthrough | 33.6 |
| 租戶 | 模型填 `tenant_id` | 只來自 token；出現租戶參數即拒絕 | 33.8 |
| 稽核 | 七天的 debug trace | 每租戶一條 hash chain＋外部 checkpoint | 33.9 |

教學版刻意沒有做的事也要列出來：token 用共享密鑰的 HMAC 而不是非對稱簽章；沒有 token 撤銷清單與 refresh token；step-up 的暫停與恢復只用兩次 `run()` 模擬，沒有持久化（第 22 章）；checkpoint 沒有真的寫到另一個信任域；稽核日誌只在記憶體裡，也沒有處理並行寫入時的排序。正式上線時，這些都應該交給成熟的身分平台、資料庫與儲存服務，`loom.auth` 只負責把它們接起來，並保證 agent 這一側的不變式。

## 33.11 實務應用

身分、授權與稽核的原則在不同產品中都一樣，但重點會隨著「誰是使用者、誰在場、出錯的代價」而改變。以下四個情境說明本章的設計在其中怎麼落地。

**情境一：多租戶客服 agent 平台（青鳥的主線）**。使用者是店家的客服人員，意圖來源清楚、通常在場，風險集中在退款與跨租戶存取。設計重點是：租戶與使用者只來自登入 session；每個 tool 對應細粒度 scope；500 元以下的退款在 scope 內自動，超過就 step-up 給店長；每個店家一條稽核鏈，店家管理員能查自己店的紀錄，青鳥的支援人員查詢時也要留下紀錄。終端顧客透過聊天視窗直接使用 agent 時，顧客的身分驗證更弱（可能只有訂單編號加手機號碼），能做的動作就要更少，例如只能查自己的訂單、退款一律轉真人。第 42 章的設計演練會把這個平台完整走一遍。

**情境二：企業內部的 coding agent**。青鳥的 coding agent 代表工程師操作 repo、跑測試、開 pull request。這裡最常見的錯誤是把工程師的個人 token 放進 sandbox，讓 agent 擁有工程師在所有 repo 的全部權限。比較好的做法是讓 agent 以自己的 app 身分安裝在特定 repo 上，取得只對這些 repo 有效、一小時內過期的 installation token，並在 pull request 上同時標示「由 agent 建立、代表哪位工程師」；push 到受保護的分支、修改 CI 設定這類動作，仍需人工 review。公開資料中，GitHub App 的 installation access token 預設在一小時後過期，權限可以限縮到特定 repo 與特定操作，是這類設計的常見基礎。

**情境三：金融或醫療的 research 與分析 agent**。使用者是分析師，資料敏感、法規要求可追溯，而 agent 常常在背景跑很久。設計重點有三個。第一是權限感知的檢索：agent 只能檢索分析師本人有權限看的文件，過濾在召回之前完成（第 11 章、第 44 章）。第二是長時間授權：任務建立時取得明確範圍與期限的委派授權，每個步驟再換成短效 token，使用者撤銷授權時任務要能立即停止。第三是稽核的保存期限與不可竄改性要符合產業法規，稽核紀錄要能證明「這份報告引用的每一筆資料，當時這位分析師都有權限讀」。

**情境四：跨組織的 agent 互動與 MCP 生態**。青鳥的客服 agent 透過 MCP 接物流商的 server，或透過 A2A 委派任務給合作夥伴的 agent（第 15 章）。跨組織時，雙方的身分系統不同，信任不能靠「都在同一個機房」。設計重點是：每個外部 server 有獨立的憑證與最小 scope，credential 以 issuer 為 key 保存、不跨授權伺服器重用；絕不把青鳥內部的 token 轉送給外部 server；外部 agent 回傳的內容一律當成不可信資料，它轉述的「使用者已同意」不能取代真正的核准。

| 情境 | 主要身分模式 | 最關鍵的授權控制 | 稽核重點 |
|---|---|---|---|
| 多租戶客服 | 代表店員（delegation） | 租戶來自 session；退款 step-up | 每租戶一條鏈；核准者可驗證 |
| 內部 coding agent | agent app 身分＋代表工程師 | repo 範圍、短效 installation token | PR 標示代理鏈；受保護分支人工 review |
| 金融／醫療分析 | 長時間委派 | 權限感知檢索；可撤銷的委派 | 法規保存期限；引用資料的存取證明 |
| 跨組織協作 | 每個外部 server 獨立憑證 | audience 綁定、禁止 passthrough | 對外呼叫與回應都記錄 |

這張表的共同點是：模型從不參與身分與權限的判斷。模型決定「想做什麼」，身分系統與 middleware 決定「能不能做」，稽核日誌記下「實際做了什麼」。

> [!note] 2026 現況
> 截至 2026 年 10 月，依各家公開文件：Anthropic 的 Managed Agents 在架構上讓憑證無法從 sandbox 取得，git token 只在初始化 clone 時使用，MCP 的 OAuth token 存放在 vault，由 proxy 以 session token 換取；Claude Code 的 agent teams 中，隊友之間的訊息會被標記來源，隊友不能代替使用者核准權限，被拒絕的動作也不能轉給另一個隊友繞過。Amazon Bedrock AgentCore 的 Policy 服務在 Gateway 層攔截每一次 tool call，規則可以用 Cedar 相容的 policy language 撰寫，與模型推理分離。A2A 在 2026 年 3 月的 v1.0 移除了 OAuth 的 implicit 與 password flow，新增 device code 與 PKCE。稽核儲存方面，AWS CloudTrail 提供以雜湊與簽章的 digest 檔驗證 log 完整性的功能，S3 Object Lock 提供 WORM 保存。OWASP 在 2025 年 12 月發布的 Top 10 for Agentic Applications for 2026 中，ASI03 即為 Identity & Privilege Abuse。產品功能變動快，採用前請查當時的官方文件。

## 33.12 設計檢查清單

設計或審查一個 agent 系統的身分、授權與稽核時，逐項回答下面的問題。

1. 每個 agent 是否有自己的註冊身分（id、版本、擁有團隊、允許的 tool）與自動輪替的 workload 憑證？
2. agent 代表使用者時，下游看到的是委派（同時有 `sub` 與 `act`），還是冒充（只有使用者）？
3. 一次 tool call 的有效權限是否為「使用者 ∩ agent ∩ 這次任務」的交集？有沒有任何路徑能讓 agent 做到使用者本人做不到的事？
4. 每一跳的 token 是否只對下一跳有效（audience 綁定），而且範圍只縮不放、期限只縮不延？
5. 是否有任何元件把收到的 token 原樣轉送給下游（token passthrough）？
6. scope 是否讀寫分開、高風險動作獨立？自動核准的邊界（例如 500 元）是寫在授權規則裡，還是只寫在 prompt 裡？
7. step-up 得到的授權是否綁定單筆交易（tool、參數、金額）、短效且只能使用一次？拒絕與逾時時，模型能不能換條路繞過？
8. 自己寫的 MCP server 是否發布 Protected Resource Metadata、驗證 audience、只接受 header 中的 token，並在 scope 不足時回 403 `insufficient_scope`？
9. secrets 是否完全不出現在 prompt、tool 描述、tool 回傳、sandbox 與 log？refresh token 存在哪裡、誰能讀？
10. 租戶是否只來自已認證的 session？tool 參數 schema 中是否還有任何租戶或使用者欄位？出現時是拒絕並告警，還是默默忽略？
11. 資料庫、向量索引、memory、cache、sandbox、配額、稽核，每一層是否都獨立以租戶隔離？別家資源與不存在的資源是否回傳相同錯誤？
12. 稽核紀錄是否包含主體、行動者與版本、model 與 prompt 版本、參數（敏感欄位遮罩）、授權決定、核准者與 trace id，並且也記錄被拒絕的嘗試？
13. 稽核日誌是否 append-only、以 hash chain 串接，並定期把簽章過的 checkpoint 寫到另一個信任域？有沒有定期執行驗證？
14. 稽核日誌的保存期限、存取權限與個資處理（雜湊或 crypto-shredding）是否和 debug trace 分開治理，並經過法務確認？

## 33.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 下游紀錄的操作者永遠是同一個服務帳號 | 所有 agent 共用一把長效 key，或做了冒充而不是委派 | 查下游存取紀錄中的身分分布；盤點憑證的壽命與使用者數 | 每跳做 token exchange，下游 token 帶 `sub` 與 `act` |
| 報表或回答混入別家租戶的資料 | 租戶由模型參數決定，或某層查詢漏了租戶條件 | 在稽核中搜尋帶租戶參數的 tool call；對每個查詢路徑做跨租戶測試 | 租戶只來自 session；移除參數中的租戶欄位；加上 row-level security |
| 偷來的 token 能打多個服務 | 沒用 resource indicator，或下游不驗 audience | 拿 A 服務的 token 打 B 服務的測試 | 每個 token 綁定單一 audience；所有 resource server 驗 audience |
| MCP server 被要求「轉送」使用者 token 才能運作 | 下游 API 只接受使用者 token，於是做了 passthrough | 檢查 server 對下游的請求 header 是否與收到的相同 | server 以自己的身分做 token exchange，或改用服務憑證加使用者情境 |
| secret 出現在模型回答或 trace 裡 | tool 回傳 debug header、secret 放在 prompt 或 sandbox | 對 trace 與 tool result 跑 secret 掃描 | credential broker 注入與剝除；記錄前遮蔽；輪替已外洩的 secret |
| 核准紀錄被質疑是事後補的 | 核准只是資料表裡的可改欄位 | 檢查誰有該欄位的寫入權限；稽核是否有 hash chain | 核准轉成可驗證的 step-up token；稽核用 hash chain 與外部 checkpoint |
| 一張核准被用了很多次 | step-up token 沒有綁定參數，或沒有一次性檢查 | 在稽核中找同一核准 id 對應的多筆執行 | 核准綁定 tool 與參數，記錄已使用的核准 id |
| 稽核驗證「通過」但懷疑紀錄被動過 | 只驗鏈的內部一致性，沒有外部 checkpoint | 比對外部保存的 checkpoint 與目前的鏈尾 | 定期簽章 checkpoint 並寫入 WORM 或另一個帳號 |
| step-up 不斷跳出，使用者一直被要求授權 | client 對 403 無限重試，或 scope 設計太細碎 | 統計每個 session 的 step-up 次數 | 限制重試次數；合併常一起使用的 scope；調整自動邊界 |

## 本章重點整理

- 身分與權限要分三件事看：認證回答「是誰」，授權回答「能不能做」，可歸責回答「事後能不能用不可竄改的證據證明」。
- agent 是一個獨立的 principal，需要自己的註冊身分與短效的 workload 憑證，才能被限權、被追責、被單獨撤銷。
- 一次 tool call 的有效權限是使用者、agent 與這次任務三者的交集；agent 永遠不能讓使用者做到本人做不到的事。
- agent 代表使用者時要用委派而不是冒充：下游 token 同時寫著主體（`sub`）與行動者（`act`），代理鏈可以一路巢狀記錄。
- token exchange 的三條不變式是範圍只能縮小、期限只能縮短、行動者必須被記下；每一跳的 token 只對下一跳有效。
- scope 要讀寫分開、高風險動作獨立；自動核准的邊界要寫在授權規則裡，而不是只寫在 prompt 裡。
- step-up 讓超出權限的動作暫停並取得額外授權；得到的 token 要綁定單筆交易、短效且只能使用一次。
- MCP server 是 OAuth resource server：發布 Protected Resource Metadata、要求 resource indicator、驗證 audience 是自己，並禁止 token passthrough。
- secrets 不能出現在模型看得到的任何地方；由 credential broker 在 tool 層注入短效憑證，並在回程剝除與掃描。
- 讓 secret 變得不值錢是根本解法：短效、單一受眾、最小範圍的 token，外洩的影響很有限。
- 租戶只來自已認證的 session；tool 參數中不該有租戶欄位，出現時要拒絕並告警，每一層儲存都要獨立隔離。
- 別家的資源與不存在的資源要回傳相同的錯誤，避免透過錯誤訊息探測其他租戶的資料。
- 稽核日誌與 debug trace 用途不同：稽核內容固定、不取樣、長期保存、不可修改，也要記錄被拒絕的嘗試。
- hash chain 能偵測單筆修改與中間刪除，但偵測不到整條重算與尾端截斷；必須定期把簽章過的 checkpoint 存到另一個信任域。
- 不可否認性需要行動者本人產生的證明，例如強認證後由授權伺服器簽發、寫著核准者身分的 approval token。

## 延伸問答

> [!question]- Q1. 使用者已經登入了，為什麼 agent 呼叫每個 tool 時還要再做授權檢查？登入不就證明了身分嗎？
> 登入只完成了認證，回答「這是 Amy」；它沒有回答「Amy 經由這個 agent、在這次任務裡，能不能退這一筆 3,200 元」。agent 系統的特殊之處在於，使用者登入之後，實際提出動作的是模型，而模型的決定受到對話、檢索結果與 tool 輸出影響。如果只在登入時檢查一次，之後模型提出的任何 tool call 都會以 Amy 的完整權限執行，prompt injection 的影響範圍就等於 Amy 的全部權限。
>
> 所以授權要在每次 dispatch 前做，而且要用「使用者 ∩ agent ∩ 這次任務」的交集判斷，再加上金額、租戶這類參數層級的規則。下游的每個 resource server 也要再驗一次自己收到的 token，因為它們無法確認上游真的做了檢查。這種「每一跳都重新驗證」的做法，就是零信任架構在 agent 系統中的落實。

> [!question]- Q2. 營運 research agent 每月自動產出跨店家的彙總報表，沒有特定使用者在場。它應該用自己的身分，還是代表某位使用者？
> 這是 agent 自身身分的典型情境。報表的意圖來源是一個排程，而不是某位使用者的即時要求，硬找一位使用者讓 agent 代表，反而會讓權限邊界變模糊：那位使用者離職或權限改變時，報表就壞了；更糟的是 agent 可能繼承了那位使用者其他無關的權限。比較好的做法是讓 research agent 以自己的 workload 身分執行，註冊時核定它只能讀彙總層級的資料，敏感欄位在資料層就遮罩。
>
> 但要注意兩點。第一，誰建立或修改這個排程，本身要被授權與稽核，因為排程的建立者實際上決定了 agent 會做什麼。第二，如果報表要寄給特定店家，寄出的內容要依收件店家的權限重新過濾，不能因為 agent 有跨店家的讀取權限，就把彙總中的別家資料寄出去。換句話說，「用什麼身分讀」和「結果可以給誰看」是兩個獨立的授權判斷。

> [!question]- Q3. 你接手的系統裡，ERP 的操作紀錄全部顯示同一個服務帳號。你會怎麼分階段改造，而不讓服務中斷？
> 第一階段先補可見性，不改權限：在 tool gateway 對下游的每個請求加上帶簽章的情境 header（使用者、租戶、agent 與版本、trace id），並寫進青鳥自己的稽核日誌。這一步不需要 ERP 配合，就能先回答「是誰代表誰」的問題，也能統計每個 agent 實際用到哪些操作，作為下一步設計 scope 的依據。
>
> 第二階段縮權限：依統計結果為每個 agent 建立獨立的憑證與最小 scope，先在讀取類 tool 上切換，觀察錯誤率，再切換寫入類 tool；舊的共用 key 保留一段時間但加上告警，任何仍在使用它的路徑都會浮現。第三階段做委派：和 ERP 團隊一起支援 token exchange 與 audience 驗證，讓 ERP 自己看得到 `sub` 與 `act`，並能對 agent 發出的動作套用不同的規則。最後撤銷共用 key。每個階段都可以獨立回退，這比一次全面換掉安全得多。

> [!question]- Q4. 如果在 system prompt 裡明確寫「tenant_id 一律填目前店家」，並且在 tool 裡檢查 tenant_id 和 session 相同，這樣把 tenant_id 留在參數裡可以嗎？
> 第二道檢查確實能擋下越權，所以這個設計不會直接外洩資料，但它仍然比「參數裡根本沒有這個欄位」差。第一，它把一個本來不需要模型決定的值交給模型，增加出錯的機會；模型填錯時，使用者看到的是莫名其妙的錯誤，而不是正確的結果。第二，它讓安全依賴於每一個 tool 都記得做那道檢查；只要新加的一個 tool 忘了，漏洞就出現了，而「參數裡沒有租戶」是結構上的保證，不依賴每個人都記得。
>
> 第三，它模糊了訊號。如果參數裡根本沒有租戶欄位，那麼模型試圖指定租戶這件事本身就是異常，可以直接拒絕並告警；如果參數裡本來就有這個欄位，你就分不出模型是「照常填寫」還是「被內容誘導去填別家」。好的授權設計會讓不該出現的東西在結構上就不可能出現，於是任何出現都值得調查。

> [!question]- Q5. 程式找錯：下面這段 middleware 有四個安全問題，請指出並說明後果。
> ```python
> def check(token, tc):
>     body, sig = token.split(".")
>     if sig != sign(body):
>         raise Deny("bad sig")
>     claims = decode(body)
>     if "refunds" in claims["scope"] and tc.name == "refund":
>         tenant = tc.args.get("tenant_id", claims["tenant"])
>         return erp.refund(token, tenant, tc.args["order_id"])
> ```
> 第一，簽章比對用 `!=`，一般字串比較會在第一個不同的字元就返回，理論上可以被用來做時序攻擊，應改用 `hmac.compare_digest`。更嚴重的是它完全沒有檢查 `exp`、`iss` 與 `aud`：過期的 token、別的授權伺服器發的 token、發給其他服務的 token 都會被接受。
>
> 第二，scope 用子字串比對，`"refunds" in claims["scope"]` 會讓 `refunds:read` 或 `norefunds` 這類 scope 也通過，應該把 scope 切成集合後做精確比對。第三，租戶以模型參數優先，`tenant_id` 一出現就覆蓋 token 上的租戶，等於讓模型決定要退哪一家店的錢。第四，它把收到的 token 原樣傳給 ERP，這是 token passthrough；正確做法是以 agent 的身分換一張 audience 為 ERP、scope 最小的新 token。另外它也沒有金額邊界與 step-up，也沒有寫稽核紀錄。

> [!question]- Q6. 估算題：青鳥每天約 20 萬個客服 session，平均每個 session 6 次 tool call，每筆稽核紀錄約 1 KB。法規要求保存 7 年。儲存量大約多少？checkpoint 要多久做一次？
> 每天的紀錄數是 20 萬 × 6 ＝ 120 萬筆，每筆 1 KB，約 1.2 GB／天；一年約 438 GB，7 年約 3 TB，再加上索引與副本，估計在 5 到 10 TB 的量級。這個量對物件儲存而言不大，成本主要在於查詢需求：如果要支援「查某位店員過去一年的所有退款」，就需要依租戶與主體建立索引，或把舊資料轉成可查詢的欄式格式。依租戶分鏈也讓匯出與保存政策更容易管理。
>
> checkpoint 的頻率決定了「最多有多長一段紀錄可能被不留痕跡地竄改或截斷」。每小時一次，代表最壞情況下最近一小時內的紀錄只受鏈本身保護；每分鐘一次則要寫 1,440 次／天／鏈，若有數千個租戶各自一條鏈，可以把所有鏈的最新雜湊再組成一棵 Merkle tree，只對樹根做一次 checkpoint。實務上常見的取捨是數分鐘到一小時一次，並在高風險事件（例如大額退款核准）發生後立即補做一次。

> [!question]- Q7. hash chain、WORM 儲存與數位簽章都被說成「防竄改」，它們各自保證什麼？只選一種夠不夠？
> hash chain 保證「內部一致」：鏈中任何一筆被修改或從中間刪除，驗證時都會被發現；但擁有寫入權限的人可以整條重算，或截掉尾端，鏈依然自洽。WORM 儲存保證「寫入後在保存期限內不能修改或刪除」，由儲存系統強制執行，但它只保護已經寫進去的東西，寫入之前在應用程式裡被竄改，它無從得知；它也不提供方便的方式證明紀錄之間的順序與完整性。
>
> 數位簽章保證「這段內容是持有某把私鑰的人產生的」：對 checkpoint 簽章，證明這個鏈尾是稽核服務在當時承認的；由核准者的強認證產生的簽章憑證，則提供不可否認性。三者保護的是不同的攻擊者與不同的時間點，所以實務上會組合使用：應用程式寫入 hash chain，定期把簽章過的 checkpoint 寫進另一個信任域的 WORM 儲存，高風險動作的核准再帶著可獨立驗證的簽章憑證。只選一種，總會留下一類無法偵測的竄改。

> [!question]- Q8. 面試追問：設計一個可以在使用者離線時跑好幾個小時的背景 agent，它要代表使用者修改雲端資源。授權要怎麼設計？
> 先拆成「任務授權」與「步驟憑證」兩層。任務建立時，使用者在場，明確同意一份任務授權：能動哪些資源、能做哪些操作、金額或數量上限、有效期限（例如 8 小時）。這份授權由授權伺服器保存並簽發 id，agent 只持有這個 id，不持有使用者的 refresh token。每個步驟要呼叫下游時，broker 以「任務授權 id＋agent 的 workload 憑證」換一張幾分鐘內有效、只對該下游有效的 token，所以就算某一步的 token 外洩，影響也只有幾分鐘、一個服務。
>
> 接著處理三種邊界情況。第一，撤銷：使用者或管理員撤銷任務授權後，下一次換 token 就會失敗，agent 必須在下一個步驟停止，並把進度存好以便日後人工接手（第 22 章）。第二，超出範圍：遇到授權範圍外的動作，不讓 agent 自行擴權，而是暫停並透過 backchannel 推播請使用者核准，或排進待辦等使用者上線；不可逆的動作預設走後者。第三，可歸責：每一步的稽核紀錄都寫著任務授權 id、使用者、agent 版本與當時的 token 代理鏈，事後能回答「這個修改是在哪份授權下、由哪個版本的 agent 做的」。面試時能主動提到撤銷與「範圍外動作的處理」，通常是區分答案深度的關鍵。

## 延伸閱讀

- IETF RFC 8693〈OAuth 2.0 Token Exchange〉（2020）
- IETF RFC 8707〈Resource Indicators for OAuth 2.0〉（2020）
- IETF RFC 9728〈OAuth 2.0 Protected Resource Metadata〉（2025）
- IETF RFC 9396〈OAuth 2.0 Rich Authorization Requests〉（2023）
- Model Context Protocol Specification〈Authorization〉（2026-07-28 版）
- OWASP〈Top 10 for Agentic Applications for 2026〉（2025）
- NIST NCCoE〈Accelerating the Adoption of Software and AI Agent Identity and Authorization〉concept paper（2026）
- Crosby & Wallach〈Efficient Data Structures for Tamper-Evident Logging〉（USENIX Security 2009）
