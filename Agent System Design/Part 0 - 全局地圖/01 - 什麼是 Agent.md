---
chapter: 1
title: 什麼是 Agent：從一次 LLM 呼叫到自主系統
part: 0
---

# 第 1 章　什麼是 Agent：從一次 LLM 呼叫到自主系統

> [!abstract] 本章地圖
> **核心問題**：「agent」到底是什麼？它和一次 LLM 呼叫、一條寫好的 workflow 差在哪裡？什麼時候該用、什麼時候不該用？
>
> **你會學到**：
> - 用一句可操作的定義判斷一個系統是不是 agent：模型在 loop 中自己決定下一步，也自己決定何時停止
> - 把「LLM 呼叫 → workflow → agent」看成一條光譜，並說出每一段的成本、可控性與失敗模式
> - 用 L0–L5 的 autonomy 等級，替每一個動作（而不是整個系統）決定要自動執行、要人核准，還是禁止
> - 用「開放、可驗證、可回復」三個問題判斷一個任務適不適合交給 agent
> - 用 Python 與 ScriptedModel 實際比較三種做法處理同一個客服請求的差異
> - 掌握全書 11 個 Part、46 章的地圖，依自己的角色選擇閱讀路線
>
> **前置知識**：會寫 Python、用過 ChatGPT 或任一家 LLM API。不需要任何 agent 經驗。

## 1.1 故事：一封「訂單沒到，可以退款嗎？」的客訴

青鳥科技（Bluebird）是一家做電商營運 SaaS 的公司，客戶是數千家中小型網店。網店老闆用青鳥的後台管理訂單、庫存與物流，而網店的消費者有問題時，會在網店頁面上的客服視窗留言。這些留言最後都落到青鳥的客服團隊：旺季時一天上萬則，其中大半是「我的貨到哪了」「可以退嗎」「為什麼扣兩次款」這類需要查系統才能回答的問題。

產品經理阿哲在季度規劃會上提出：「我們做一個 AI 客服 agent，讓它自己查訂單、自己處理退款。」剛從後端轉職成 AI 工程師的 Iris 接下這個專案。Iris 花了一個下午，把客服留言直接丟給 LLM API，加上一段「你是青鳥科技的客服」的 system prompt，做出第一個 demo。示範時阿哲輸入了一則真實留言：「我的訂單 BB-1024 一直沒到，可以直接退款嗎？另外 BB-1077 的衣服尺寸不合也想退。」模型很快回覆：「您好，BB-1024 正在配送中，已為您辦理退款，款項 3–5 天入帳。」

會議室安靜了幾秒。資安工程師 Maya 先開口：「它根本沒有連到訂單系統，怎麼知道 BB-1024 在配送中？而且它說已經退款了，那筆錢到底退了沒有？」答案是兩者都沒有發生。模型看不到任何資料，只是根據「客服回覆通常長這樣」寫出一段通順的文字；而「已為您辦理退款」是一句沒有對應任何實際動作的承諾。更糟的是，第二張訂單 BB-1077 完全被忽略了。

Iris 的 mentor、經歷過多次分散式系統上線的 staff engineer 老陳，在會後問了 Iris 三個問題：「你說的 agent，跟一次 API 呼叫差在哪裡？如果要查訂單，是你的程式決定去查，還是模型決定去查？它什麼時候知道自己做完了？」Iris 答不太出來。老陳說：「這三個問題就是整個專案的設計核心。答不出來的話，你會在兩個極端之間搖擺：要嘛做出一個只會講話、會亂承諾的聊天機器人，要嘛做出一個自己亂退款的系統。」

這一章就從 Iris 的困惑出發。我們會先拆解一次 LLM 呼叫能做什麼、不能做什麼；接著看「由程式碼決定路徑」的 workflow；再看「由模型決定下一步」的 agent；然後討論自主權該給多少、哪些任務根本不該用 agent。最後在動手做一節，用同一則客訴比較三種做法，並把整本書的地圖攤開，讓你知道接下來四十五章會怎麼一步步把這個客服 agent 做到能上線。

## 1.2 起點：一次 LLM 呼叫能做什麼

要理解 agent，得先看清楚它最小的零件。**LLM 呼叫**（LLM call）是把一段文字（以及圖片等輸入）送給大型語言模型，模型依機率逐字產生一段輸出文字的過程。例如把「把這段客訴分類成物流、退款、帳務或其他」加上客訴內容送出去，模型回「退款」。從程式設計師的角度，它很像一個函式：`text → text`，只是這個函式的行為是由訓練資料與提示決定的，而且每次呼叫的結果可能略有不同。

```text
 ┌──────────────┐    prompt（system＋user 訊息）    ┌──────────────┐
 │  你的程式      │ ───────────────────────────────► │     LLM       │
 │  (Python)     │ ◄─────────────────────────────── │ 只看得到 prompt │
 └──────────────┘          一段文字（回覆）           └──────────────┘
        │
        └─► 程式拿到文字後自己決定：顯示給使用者？存起來？丟掉？
```

這張圖要注意三件事。第一，箭頭只有一來一回：模型收到 prompt、吐出文字，然後這次呼叫就結束了，模型本身不保留任何狀態。下一次呼叫時它不記得上一次說過什麼，除非你的程式把上一次的對話再放進 prompt。第二，模型「只看得到 prompt」：訂單資料庫、物流 API、退款系統都不在它的視野裡。第三，輸出只是文字，要不要相信、要不要執行，全由外面的程式決定。

這三點直接解釋了 Iris 的 demo 為什麼會出錯。因為模型看不到訂單系統，所以它對 BB-1024 的狀態只能猜；因為它的輸出只是文字，所以「已為您辦理退款」不代表任何退款真的發生。這種「說得很像真的，但沒有事實依據」的輸出叫做 **hallucination**（幻覺），例如模型編出一個不存在的物流單號。在客服情境裡，hallucination 最危險的形式不是編錯事實，而是**承諾了一個沒有執行的動作**，因為客人會依此做決定。

一次 LLM 呼叫仍然非常有用，前提是任務只需要「把輸入轉換成輸出」，不需要額外資料或動作：分類、摘要、翻譯、改寫、從一段文字抽出欄位。青鳥的客服團隊其實已經在用這種能力：客服人員回覆前，按一個按鈕讓模型把留言摘要成一行。這是很好的起點，因為它便宜（一次呼叫）、快（一次往返的延遲）、容易測試（輸入輸出都是文字）。

要讓模型處理更多事情，業界的第一步通常是把它「加強」。Anthropic 在〈Building effective agents〉中把這種加強過的模型稱為 **augmented LLM**：模型可以搭配 retrieval（從知識庫找資料）、tools（呼叫外部功能）與 memory（記住先前的資訊）。這裡最關鍵的機制是 **tool calling**（也叫 function calling，工具呼叫）：你在呼叫時附上一份「可用工具清單」，每個工具有名稱、說明與參數格式；模型如果判斷需要，就不直接回答，而是輸出一段結構化的請求，例如「呼叫 `get_order`，參數 `order_id = "BB-1024"`」。

> [!warning] 常見誤解
> 「模型會呼叫工具」不代表模型自己去執行了工具。模型只是**輸出一個請求**；真正執行 `get_order` 的，是你的程式。你的程式可以選擇照做、拒絕、改參數或先問人。這個「模型提出、程式執行」的分工，是後面所有安全設計（第 21、32 章）的基礎。

有了 tool calling，下一個問題就出現了：模型提出「查訂單」之後，誰把查到的結果交回給模型？查完訂單後要不要再查物流？這些「下一步」由誰決定，正是 workflow 與 agent 的分水嶺。

## 1.3 Workflow：由程式碼決定路徑

**Workflow**（工作流程）是由程式碼預先定義好執行路徑，LLM 只負責其中某些步驟的系統。例如「先用 LLM 分類意圖，如果是退款就查訂單、查退款政策，最後用 LLM 寫回覆」。這裡每一步做什麼、按什麼順序、遇到什麼分支走哪條路，都寫在你的 Python 裡；模型只是在某幾個節點上做「判斷」或「寫作」。

```text
 客訴文字
    │
    ▼
 [LLM] 分類意圖 ──► "物流" ──► get_shipment ──► [LLM] 寫回覆 ──► 送出
    │
    ├──────────► "退款" ──► get_order ──► check_refund_policy ──► [LLM] 寫回覆 ──► 送出
    │
    └──────────► 其他 ──► 轉真人客服
```

這張圖的讀法是由上往下、由左往右。第一個節點用 LLM 做分類，輸出必須是事先定義好的幾個標籤之一；接著程式依標籤走固定的分支，每條分支裡要呼叫哪些 API 是寫死的；最後再用 LLM 把查到的資料寫成客人看得懂的回覆。路徑上的每個 `[LLM]` 節點都是一次獨立的 LLM 呼叫，彼此之間的資料傳遞由程式負責。

Workflow 的優點是**可預測**。因為路徑是程式碼，所以你可以畫出所有可能的執行路徑，替每條路徑寫測試，預估每個請求最多花幾次模型呼叫、多少錢、多少秒。當主管問「這個系統會不會自己退款」時，你可以指著程式碼說「退款分支裡沒有呼叫退款 API，所以不會」。這種可證明的性質，在處理金錢、個資或法規要求的場景特別珍貴。

缺點是**只能處理你預想到的情況**。回到那則客訴：客人同時問了兩張訂單，一張是物流延誤、一張是尺寸不合要退貨。分類器只能輸出一個標籤，於是 workflow 選了「退款」分支，只處理第一個單號，物流延誤的原因也沒查。要修正，你得加一個「多意圖」分支、一個「多單號」迴圈、一個「退款前先查物流」的前置步驟……每補一個情況，路徑就多一條，而真實世界的組合永遠比你寫得快。

Workflow 本身也有不少成熟的模式：把任務拆成連續步驟的 prompt chaining、依輸入分流的 routing、同時跑多個子任務的 parallelization、由一個 LLM 分派子任務的 orchestrator-workers、以及一個產生一個評分的 evaluator-optimizer。這五種模式會在第 18 章逐一實作。這裡只要記住：workflow 不是「比較笨的 agent」，它是另一種設計選擇，用彈性換取可預測性。

## 1.4 Agent：模型在 loop 中決定下一步與何時停止

本書採用一個可以操作的定義：**agent 是讓模型在一個 loop（迴圈）中，根據環境回饋自己決定下一步要做什麼、也自己決定何時停止的系統**。「下一步」可以是呼叫某個 tool、問使用者一個問題、或直接給出最終答案；「環境回饋」是 tool 執行後的結果，例如查訂單得到的 JSON。這個定義和 Anthropic 所說的「LLM 在 loop 中自主使用工具」、以及 OpenAI 實務指南中「由模型控制 workflow 執行、能辨識何時完成」的描述是一致的。

```text
            ┌───────────────────────────────────────────────┐
            │                  Harness（你的程式）              │
 使用者 ───►│  messages ──► Model：決定下一步                    │
            │                 │                               │
            │        ┌────────┴─────────┐                     │
            │   tool_use               end_turn               │
            │        │                   │                    │
            │        ▼                   ▼                    │
            │  執行 tool（查訂單、        回覆使用者 ──► 結束        │
            │  查物流、查政策）                                   │
            │        │                                        │
            │        └─► tool_result 加回 messages ──► 再問 Model │
            │                                                 │
            │  護欄：max_steps、token／金額預算、權限、人工核准       │
            └───────────────────────────────────────────────┘
```

圖中外框是 **harness**（駕馭程式，也常叫 agent runtime 或 runner）：圍繞模型、負責跑 loop 的那段程式碼。逐步看一次：使用者訊息放進 `messages`（對話紀錄串列）；harness 把 `messages` 與工具清單送給模型；模型回覆時會附一個 **stop reason**（停止原因），如果是 `tool_use`，代表模型想呼叫工具，harness 就去執行，把結果包成一則 `tool` 訊息加回 `messages`，再呼叫一次模型；如果是 `end_turn`，代表模型認為可以回答了，harness 把文字交給使用者並結束。最下方的護欄是 harness 加在模型判斷之外的硬限制，例如最多跑 8 步。

和 workflow 對照，差別只有一個，卻影響深遠：**下一步是誰決定的**。在 workflow 裡，程式碼寫死「查完訂單就查政策」；在 agent 裡，模型看完訂單資料，發現狀態是配送中、有物流單號，於是**自己決定**先去查物流，再分別查兩張訂單的退款政策。正因為路徑是在執行期間依實際資料長出來的，agent 能處理你沒預想到的組合，例如一則留言裡夾了兩張訂單。

「何時停止」同樣交給模型，這是第二個關鍵。模型輸出 `end_turn` 就代表它判斷任務完成了。但模型的判斷可能出錯：可能太早停（還沒查第二張訂單就回答），也可能永遠不停（同一個 tool 一直重試）。所以實務上的停止條件一定是雙層的：模型的判斷是第一層，harness 的硬限制（步數上限、預算上限、逾時）是第二層。第 4 章會從零寫出這個 loop，並逐一處理這些停止條件。

把定義拆開，一個 agent 至少要有四個部分：**model**（做決策的大型語言模型）、**tools**（讓它能讀取資料與改變世界的介面）、**loop／harness**（把決策、執行、回饋串起來的程式）、以及**停止條件**。第 2 章會把這四個擴充成十個元件，加上 context、memory、orchestration、runtime、interfaces、evaluation 與 guardrails，這是設計一個可上線 agent system 的完整拼圖。

下面用時序圖追蹤一次 agent 處理那則客訴的過程。**Trajectory**（軌跡）是指一次任務從頭到尾所有模型輸出與 tool 結果的完整序列，它是除錯與評估 agent 的主要材料（第 27、29 章）。

```text
 使用者        Harness                 Model                 Tools
   │  客訴       │                        │                      │
   │───────────►│  messages[1]           │                      │
   │            │───────────────────────►│                      │
   │            │  tool_use get_order(BB-1024)                  │
   │            │◄───────────────────────│                      │
   │            │──────────────────────────────────────────────►│
   │            │◄──────────── {status: in_transit, tracking: T-889}
   │            │───────────────────────►│ （看到物流單號）        │
   │            │  tool_use get_shipment(T-889)                 │
   │            │◄───────────────────────│                      │
   │            │──────────────────────────────────────────────►│
   │            │◄──────────── {last_event: 轉運中心延誤, eta: 2}  │
   │            │───────────────────────►│                      │
   │            │  tool_use ×2 check_refund_policy(BB-1024 / BB-1077)
   │            │◄───────────────────────│                      │
   │            │──────────────────────────────────────────────►│
   │            │◄──────────── {eligible: false} / {eligible: true}
   │            │───────────────────────►│                      │
   │            │  end_turn「BB-1024 延誤…BB-1077 可申請退貨…」    │
   │◄───────────│◄───────────────────────│                      │
```

讀這張時序圖時，注意兩個地方。其一，第二步「查物流」不是任何人寫死的，是模型看到第一次 tool 結果裡有 `tracking` 欄位後才決定的，這就是「依環境回饋決定下一步」。其二，第三次呼叫時模型一次提出兩個 tool call，這叫 **parallel tool calls**（平行工具呼叫），讓互不依賴的查詢可以同時執行，節省往返次數。整個過程模型被呼叫了四次，每次都要把越來越長的 `messages` 重新送一遍，這是 agent 比 workflow 貴的根本原因。

> [!warning] 常見誤解
> 「有接 tools 的聊天機器人就是 agent。」不一定。如果每次使用者訊息只觸發一次「模型選一個 tool → 程式執行 → 直接把結果貼給使用者」，模型並沒有在 loop 裡根據結果決定下一步，這比較接近 routing workflow。判斷的關鍵不在有沒有 tools，而在**模型能不能看到行動的結果，並據此決定要不要繼續**。

最後用一張表整理三種做法的差異。這張表會在全書反覆出現，因為很多設計爭論其實都是在問「這一段該放在哪一欄」。

| 面向 | 單次 LLM 呼叫 | Workflow | Agent |
|---|---|---|---|
| 誰決定下一步 | 沒有下一步 | 程式碼（事先寫死） | 模型（執行期間依回饋決定） |
| 誰決定何時停止 | 一次就停 | 程式碼走到終點 | 模型判斷＋harness 硬限制 |
| 能否取得外部資料 | 不能（除非程式先塞進 prompt） | 能，但只在寫好的節點 | 能，模型自己挑要查什麼 |
| 每個請求的模型呼叫數 | 1 | 固定，可事先算出 | 不固定，依任務而變 |
| 成本與延遲 | 最低 | 中，可預估 | 最高，變異也最大 |
| 可測試性 | 高 | 高，可列舉所有路徑 | 較低，要用 eval 統計成功率 |
| 典型失敗 | 幻覺、捏造動作 | 遇到沒預想的情況就走錯路 | 繞遠路、太早或太晚停、誤用 tool |
| 適合的任務 | 分類、摘要、改寫 | 步驟固定、要求可證明的流程 | 開放式、步驟無法事先列舉 |

## 1.5 從呼叫到自主：一條光譜，而不是二分法

實際系統很少是純 workflow 或純 agent。比較有用的看法是把它們放在一條光譜上：越往右，模型掌握的決策越多，系統的彈性越大，可預測性越低，成本也越高。

```text
 程式碼掌握決策 ◄──────────────────────────────────────────────► 模型掌握決策

  ①單次呼叫    ②Augmented LLM    ③Workflow       ④Agent          ⑤長時間／多 agent
  摘要、分類   ＋檢索、＋一次 tool   固定路徑串多次    模型在 loop 裡    數小時的任務、
              呼叫                LLM 節點         選 tool、決定停止   多個 agent 分工
     │             │                 │                │                 │
  成本 1x       1–2x              2–5x            3–20x            10–100x 以上
  （以下皆為示意的相對量級，實際依任務與模型而定）
```

①到⑤依序讀：①只是一次轉換；②讓那一次呼叫能拿到外部資料或執行一個動作；③把多次呼叫用程式碼串成固定路徑；④把「下一步」的決定權交給模型；⑤則是 agent 進一步延伸到長時間執行或多個 agent 協作，例如 coding agent 連續工作數小時、research agent 同時派出多個子 agent 搜尋。成本列的數字是示意用的相對量級，用意是提醒你：每往右一格，你都在用更多 token 與延遲換取彈性。

光譜觀點最大的價值是讓你**混合使用**。青鳥最後上線的客服系統就是混合體：入口是一個 routing workflow，把「查物流」這類高頻、路徑固定的問題交給便宜的固定流程處理；只有多意圖、需要多步查證的複雜留言才進入 agent loop；而 agent 裡面的「建立退貨單」步驟又被包成一個固定的子流程，必須經過人工核准。12-Factor Agents 一文的觀察與此一致：多數成功的生產系統是「大部分是確定性軟體，只在關鍵點使用 LLM」。

另一個常被混為一談的概念是 **multi-agent**（多 agent 系統）：由多個 agent 分工合作完成任務，例如一個負責規劃、多個負責搜尋。Multi-agent 位在光譜最右邊，但它不是「更高級的 agent」，而是一種有明確代價的架構：每個 agent 都有自己的 context，彼此之間要傳遞資訊，成本常是單一 agent 的數倍。第 20 章會說明什麼情況值得（可平行的廣度搜尋），什麼情況不值得（需要緊密協調的寫入任務）。

> [!note] 2026 現況
> 截至 2026 年 10 月，主流框架幾乎都同時提供「模型自主的 agent」與「確定性的 graph／workflow」兩種模式並允許互相嵌套，例如 Microsoft Agent Framework、Google ADK 2.x、CrewAI 的 Crews 與 Flows、Mastra、LangGraph。另一個明顯趨勢是託管式 agent harness：Claude Managed Agents（beta）、OpenAI 的 Agents API、Amazon Bedrock AgentCore 的 Harness、Gemini Interactions API 中的 agents，都把「agent loop＋sandbox＋session＋compaction」做成雲端服務。OpenAI 也宣布視覺化的 Agent Builder 預計在 2026-11-30 關閉，code-first 的開發方式仍是主線。框架與託管服務的比較見第 26 章。

## 1.6 Autonomy 等級：L0 到 L5

光譜回答的是「誰決定路徑」，但阿哲與 Maya 真正擔心的是另一件事：**這個系統可以在沒有人點頭的情況下做多少事？**這就是 **autonomy**（自主程度）。例如同樣是 agent，一個查完資料後只能「建議」客服人員退款，另一個能直接把錢退出去，兩者的風險天差地遠。

為了讓團隊有共同語言，本書借用自動駕駛分級（SAE J3016 的 L0–L5）的精神，定義一套 agent 的 autonomy 等級。要先說明：這是本書為了設計討論而整理的分級，業界並沒有一套公認的標準，不同公司與論文的切法各有差異。重點不是背下名稱，而是用它逼自己回答「每一類動作由誰核准」。

| 等級 | 名稱 | 誰決定下一步 | 有副作用的動作由誰核准 | 人的角色 | 青鳥的例子 |
|---|---|---|---|---|---|
| L0 | 無 LLM 決策 | 規則或人 | 人 | 全部自己做 | 客服按 FAQ 範本回覆 |
| L1 | 建議 | 人 | 人 | 採納或修改模型草稿 | 模型摘要客訴、擬回覆草稿 |
| L2 | 流程內的 LLM 步驟 | 程式碼 | 程式碼（只開放事先寫好的動作） | 設計流程、處理例外 | 物流查詢的固定 workflow |
| L3 | 監督式 agent | 模型 | 每個寫入動作都要人核准 | 逐一核准 | 客服 agent v1：查詢自主，退貨單要客服按確認 |
| L4 | 有邊界的自主 | 模型 | 邊界內自動，超出邊界才找人 | 設定邊界、抽查、處理升級 | 500 元以下退款自動，超過轉真人 |
| L5 | 目標導向的長時間自主 | 模型（含拆解子目標） | 預算內自主；不可逆或超出預算的動作找人 | 給目標與預算、驗收結果 | 內部 research agent 自行跑完一份月度分析 |

逐列讀這張表，會發現兩個欄位在不同等級的變化方式不同。「誰決定下一步」在 L2 到 L3 之間發生跳躍：從程式碼變成模型，這正是 workflow 與 agent 的分界。「誰核准副作用」則是從 L3 開始逐步放寬：從每步核准、到邊界內自動、到只在不可逆動作時找人。**副作用**（side effect）指會改變外部世界狀態的動作，例如建立退貨單、退款、寄信；相對的，查訂單只是讀取，沒有副作用。

這帶出一個重要的設計觀念：**autonomy 是依動作決定的，不是依系統決定的。**同一個客服 agent，查訂單可以是 L4（自動），建立退貨單是 L3（要確認），刪除帳號則永遠不開放給它。把整個系統標成「L4」是一種危險的簡化，因為它暗示所有動作都同樣可以自動執行。

```text
                       副作用由誰核准
                 人逐一核准 ◄────────────► 系統自動（邊界內）
                    ┌────────────────────┬────────────────────┐
  路徑由模型決定      │ L3 監督式 agent      │ L4／L5 自主 agent    │
  （agent）         │ 客服 agent v1        │ 小額退款自動、        │
                    │                     │ coding agent 在 sandbox│
                    ├────────────────────┼────────────────────┤
  路徑由程式碼決定    │ L1 建議              │ L2 自動化 workflow   │
  （workflow）      │ 擬草稿給客服           │ 每晚同步訂單到 ERP     │
                    └────────────────────┴────────────────────┘
```

這張二維圖把 L1–L5 拆成兩個獨立的軸。縱軸是「路徑由誰決定」（光譜），橫軸是「副作用由誰核准」（autonomy）。左下是傳統的人機協作：程式碼固定流程、人做決定；右下是傳統自動化：路徑上沒有模型決策（模型最多是流程中的一個步驟），但動作自動執行，例如每晚的批次同步；左上是 agent 自己規劃、人逐步核准；右上才是一般人想像中的「自主 agent」。拆成兩軸的好處是可以獨立調整：你可以先在左上把 agent 的決策品質驗證夠了，再一個動作一個動作地往右移。

要把這個觀念落實成程式，最直接的做法是一張「風險等級 × autonomy 等級」的決策表。下面這段程式把青鳥的四種動作分成讀取、寫入、金錢、破壞性四級風險，依系統所在的等級決定自動、核准或禁止。

```python
# 每個動作依「風險等級」與「系統目前的 autonomy 等級」決定：自動執行、要人核准，或禁止
RISK = {"get_order": "read", "create_return": "write", "issue_refund": "money", "close_account": "destructive"}

POLICY: dict[int, dict[str, str]] = {
    1: {"read": "deny", "write": "deny", "money": "deny", "destructive": "deny"},       # 只產生建議
    2: {"read": "auto", "write": "deny", "money": "deny", "destructive": "deny"},       # 程式碼替它查資料
    3: {"read": "auto", "write": "approve", "money": "approve", "destructive": "deny"},
    4: {"read": "auto", "write": "auto", "money": "limit", "destructive": "approve"},
    5: {"read": "auto", "write": "auto", "money": "budget", "destructive": "approve"},
}


def decide(level: int, tool: str, amount: int = 0, limit: int = 500, budget_left: int = 3000) -> str:
    rule = POLICY[level][RISK[tool]]
    if rule == "limit":                    # L4：小額自動，超過門檻才找人
        return "auto" if amount <= limit else "approve"
    if rule == "budget":                   # L5：在整體預算內自主
        return "auto" if amount <= budget_left else "approve"
    return rule


print("level | get_order | create_return | refund 300 | refund 1280 | close_account")
for level in range(1, 6):
    row = [decide(level, "get_order"), decide(level, "create_return"),
           decide(level, "issue_refund", 300), decide(level, "issue_refund", 1280),
           decide(level, "close_account")]
    print(f"  L{level}  | " + " | ".join(f"{r:<7}" for r in row).rstrip())

assert decide(3, "issue_refund", 100) == "approve"      # L3：任何花錢的動作都要人點頭
assert decide(4, "issue_refund", 300) == "auto"
assert decide(4, "issue_refund", 1280) == "approve"
assert all(decide(lv, "close_account") != "auto" for lv in range(1, 6))  # 不可回復的動作永遠不自動
```

```text
level | get_order | create_return | refund 300 | refund 1280 | close_account
  L1  | deny    | deny    | deny    | deny    | deny
  L2  | auto    | deny    | deny    | deny    | deny
  L3  | auto    | approve | approve | approve | deny
  L4  | auto    | auto    | auto    | approve | approve
  L5  | auto    | auto    | auto    | auto    | approve
```

輸出逐列看：L1 什麼都不能做，因為模型只產生建議；L2 只開放讀取，而且實際上是程式碼替模型去查；L3 開始可以寫入，但每一筆都要人核准，破壞性動作仍然禁止；L4 讓 300 元退款自動通過、1280 元轉人工，這就是「有邊界的自主」；L5 在預算內連 1280 元也能自動處理。最後一欄 `close_account` 在每一級都不是 `auto`，對應最後一個 assert：**不可回復的動作永遠不應該完全自動**。第 21 章會把這張表擴充成完整的 approval policy engine，第 32 章再加上 capability 式的權限設計。

這裡為了讓「金錢」的特殊性一目了然，暫時把風險分成四級。第 5 章會把它收斂成全書統一的三級副作用分級：**read**（唯讀）、**write**（可回復的寫入，例如建立退貨單）、**destructive**（不可逆或對外的動作，例如退款、寄信、刪除帳號），本節的「金錢」與「破壞性」都歸入 destructive，而且未標註等級的 tool 一律當成 destructive。分級變少，但上表的精神不變：L4 的小額退款之所以能自動，是因為金額邊界把它限制在可承受的損失內，而不是因為退款變得可回復。

> [!tip] 自主權要「賺」來
> 合理的路徑是從低等級上線，用 eval 與線上資料證明可靠後再逐步放權，而不是一開始就給高等級、出事再收回。青鳥的客服 agent 以 L3 上線，累積了足夠的核准紀錄、確認模型建議的退貨單幾乎都被客服接受後，才把小額退款移到 L4。這個過程需要的評估方法在第 27 章，上線階段的退出條件在第 38 章。

## 1.7 什麼時候不該用 agent

看完 agent 的彈性，很容易覺得所有事情都該交給它。老陳給 Iris 的第一個規則恰好相反：**能用更簡單的方法解決，就不要用 agent**。因為 agent 的每一個優點都有對應的代價：彈性換來不可預測，多步驟換來更高的成本與延遲，自主換來更大的風險面。

具體來說，以下幾種情況應該優先考慮更簡單的做法。第一，**路徑可以事先列舉**：例如「每晚把新訂單同步到 ERP」，步驟永遠一樣，寫成程式或 workflow 更便宜、更可靠，也更容易除錯。第二，**延遲要求很嚴格**：例如結帳頁面上的即時地址驗證，使用者等不了一個多步驟的 loop。第三，**錯誤成本極高又無法驗證**：例如自動調整數千個商品的售價，一旦出錯損失立即發生，又沒有可靠的自動檢查。第四，**量大而單價低**：例如每天數百萬筆的商品評論情緒分類，單次呼叫的成本乘上數量已經可觀，agent 的倍數成本完全不划算。

```text
 新任務
   │
   ▼
 步驟能事先列舉嗎？ ── 能 ──► 寫成程式或 workflow（L2）
   │ 不能
   ▼
 結果能被客觀檢查嗎？ ── 不能 ──► 讓模型給建議，由人判斷（L1）
   │ 能
   ▼
 延遲與成本預算容得下多步 loop 嗎？ ── 不能 ──► 縮小範圍，或用 routing 把簡單情況分流
   │ 能
   ▼
 錯誤能便宜地撤銷嗎？ ── 不能 ──► agent＋不可逆步驟前人工核准（L3）
   │ 能
   ▼
 agent，在權限與預算邊界內自主（L4）
```

這個決策流程由上往下問四個問題，每個「否」的分支都把你導向一個更保守的選項。注意它並不是要你避開 agent，而是要你**把 agent 用在它真正有優勢的地方**，並且在不可逆的地方加上人工核准。很多團隊的失敗不是因為 agent 做不到，而是因為把一個固定流程硬做成 agent，結果成本高了五倍、行為還更難預測。

> [!warning] 常見誤解
> 「用 agent 才顯得有技術含量，workflow 太土了。」這是最昂貴的誤解之一。Anthropic 的〈Building effective agents〉給出的建議是先從最簡單的方案開始，只在確實需要時才增加複雜度；OpenAI 的實務指南也建議在規則容易維護的情況下優先使用確定性方案。使用者在意的是問題有沒有被解決，不在意背後是不是 agent。

## 1.8 Agent 適合的任務：開放、可驗證、可回復

反過來說，什麼樣的任務最適合 agent？本書用三個特徵來判斷，對應上一節決策流程中最關鍵的三個問題。

**開放**（open-ended）：完成任務需要的步驟數與路徑事先無法列舉，必須邊做邊看。例如「這則客訴到底發生了什麼事」：可能要查一張訂單，也可能要查三張訂單、兩筆物流、一筆付款紀錄，取決於查到什麼。修 bug 也是典型的開放任務，因為在讀完程式碼之前，你不知道問題在哪裡。開放性是 agent 存在的理由；如果任務不開放，workflow 幾乎總是更好的選擇。

**可驗證**（verifiable）：存在客觀的方法檢查結果是否正確，而且最好能在執行過程中檢查。例如 coding agent 可以跑測試，客服 agent 可以比對它的回覆是否和訂單資料一致。可驗證性同時影響兩件事：一是 agent 在 loop 裡能不能自我修正，因為測試失敗的訊息會成為下一步的依據；二是你能不能評估它，因為沒有判準就無法知道它做得好不好。Anthropic 在描述 agent 的適用場景時也強調，agent 要能在每一步從環境取得 **ground truth**（真實狀態的回饋，例如 tool 結果或測試結果）來判斷進度。

**可回復**（reversible）：做錯了能以低成本撤銷。在 git branch 上改程式碼可以丟掉重來；草擬的退貨單在送出前可以修改；但已經退出去的錢、已經寄出的信、已經刪除的資料則很難撤回。可回復性決定了 autonomy 能給到多高：可回復的動作可以讓 agent 自主嘗試，不可回復的動作則必須在執行前加入核准或其他防護。

| 任務 | 開放 | 可驗證 | 可回復 | 建議做法 |
|---|---|---|---|---|
| 每晚同步新訂單到 ERP | 否 | 是 | 是 | 一般程式或 workflow |
| 回覆訂單與退貨相關客訴 | 是 | 是（比對訂單資料） | 部分（退款不可逆） | agent，退款前人工核准（L3） |
| 修 CI 上失敗的測試並開 PR | 是 | 是（跑測試） | 是（PR 要人合併） | agent，在 sandbox 內自主（L4） |
| 每月營運分析報告 | 是 | 部分（數字可核對，結論要人判斷） | 是（只讀資料） | research agent，人驗收結論 |
| 決定下一季品牌定位 | 是 | 否 | 否 | 模型提供素材與草稿，人決定（L1） |

這張表把青鳥實際考慮過的五個候選任務放在一起比較。最上面的 ERP 同步因為不開放，直接排除；最下面的品牌定位因為無法驗證，只適合讓模型當助手。中間三個是 agent 的甜蜜點：它們都開放、大致可驗證，差別在可回復的程度，而這正好決定了各自的 autonomy 等級。值得注意的是 coding 任務：它在三個特徵上都很適合 agent，這也是為什麼 coding agent 是目前最成熟的 agent 產品類型（第 39 章）。

把這三個問題寫成程式，就是一個很小的判斷器。它刻意保持簡單，用意是讓團隊在立項時被迫逐一回答這三題。

```python
from dataclasses import dataclass


@dataclass
class Task:
    name: str
    open_ended: bool    # 步驟數與路徑事先無法列舉
    verifiable: bool    # 有客觀方法檢查結果對不對
    reversible: bool    # 做錯了能便宜地撤銷


def recommend(t: Task) -> str:
    if not t.open_ended:
        return "workflow（路徑可列舉，寫死更便宜可靠）"
    if not t.verifiable:
        return "assist（L1：模型給草稿，人判斷）"
    if not t.reversible:
        return "agent＋不可逆步驟前人工核准（L3）"
    return "agent（可在邊界內自主，L4）"


tasks = [
    Task("每晚把新訂單同步到 ERP", open_ended=False, verifiable=True, reversible=True),
    Task("回覆客人關於訂單與退貨的問題", open_ended=True, verifiable=True, reversible=False),
    Task("修 CI 上失敗的測試並開 PR", open_ended=True, verifiable=True, reversible=True),
    Task("決定下一季的品牌定位", open_ended=True, verifiable=False, reversible=False),
]
for t in tasks:
    print(f"{t.name} → {recommend(t)}")

assert recommend(tasks[0]).startswith("workflow")
assert "L3" in recommend(tasks[1])
assert recommend(tasks[2]).startswith("agent（")
assert recommend(tasks[3]).startswith("assist")
```

```text
每晚把新訂單同步到 ERP → workflow（路徑可列舉，寫死更便宜可靠）
回覆客人關於訂單與退貨的問題 → agent＋不可逆步驟前人工核准（L3）
修 CI 上失敗的測試並開 PR → agent（可在邊界內自主，L4）
決定下一季的品牌定位 → assist（L1：模型給草稿，人判斷）
```

輸出的四行對應四種結論。判斷的順序很重要：先問開放性，因為不開放的任務根本不需要 agent；再問可驗證性，因為無法驗證的任務即使開放，也不該讓模型自己做完；最後才問可回復性，用來決定 autonomy 等級。真實的立項評估當然還要加上量、價值、延遲與成本，第 35 章的設計方法論會把它擴充成完整的需求釐清清單。

## 1.9 青鳥科技：本書的貫穿案例

接下來的 45 章都圍繞同一家公司展開，因為 agent 的設計決策只有放在具體情境裡才看得出取捨。青鳥科技的業務很適合當案例：它有大量重複但多變的客服請求（適合 agent），有內部工程與營運需求（適合 coding 與 research agent），也有金錢、個資、多租戶這些讓設計變困難的約束。

```text
 Part 0–1  客服 agent v1：查訂單、查物流、退款（單一 agent、少量 tools）
    │
 Part 2    ＋知識庫檢索、長對話 compaction、使用者 memory
    │
 Part 3    ＋透過 MCP 接上 ERP 與物流商；code execution 做報表
    │
 Part 4    ＋內部 coding agent、營運 research agent；multi-agent 與人工審核
    │
 Part 5    把三個 agent 共用的部分抽成自家 framework「loom」
    │
 Part 6–7  建立 eval、tracing、安全審查與治理流程
    │
 Part 8–10 平台化、多租戶上線、設計演練與 capstone
```

這條時間線由上往下就是全書的推進順序。前兩個 Part 只做一件事：把客服 agent 從「會講話」做到「會正確查資料、會正確地不做它不該做的事」。Part 2 與 Part 3 讓它能處理更長的對話、更多的知識與更多的外部系統。Part 4 出現第二、第三個 agent，青鳥的團隊開始發現三個 agent 有大量重複的程式碼，於是在 Part 5 把共用部分抽成自己的 framework，取名 **loom**（織布機，取「把模型、工具與 context 織在一起」之意）。loom 從第 4 章的 100 行 loop 起步，一路長成第 45 章的完整 framework。

| 人物 | 角色 | 在書中關心的事 |
|---|---|---|
| Iris | 剛轉職的 AI 工程師，後端背景 | 第一次負責 agent 專案；代表讀者提問、寫程式、踩坑 |
| 老陳 | staff engineer，Iris 的 mentor | 可靠性、失敗模式、上線經驗；常問「出事時怎麼辦」 |
| 阿哲 | 產品經理 | 使用者體驗、成本、上線時程；常問「值不值得」 |
| Maya | 資安工程師 | threat modeling、權限、稽核；常問「誰能讓它做什麼」 |

四個人物代表設計 agent system 時必須同時回答的四類問題。Iris 的問題是「怎麼做出來」，老陳的問題是「怎麼讓它可靠」，阿哲的問題是「怎麼讓它值得」，Maya 的問題是「怎麼讓它安全」。一個只滿足 Iris 的 demo，在會議室裡就會被另外三個人攔下來，就像本章開頭那樣。你在自己的專案裡，也可以用這四個角色當作設計審查的四個視角。

## 1.10 全書地圖與讀法

本書共 11 個 Part、46 章，外加 6 個附錄。整體的順序是先建立心智模型，再從零做出第一個 agent，接著依序補上 context、協定與環境、orchestration，然後把共用的部分抽成 framework，最後處理評估、安全與 system design。每一章都建立在前面章節之上，但多數 Part 也能在讀完 Part 0 與 Part 1 後單獨閱讀。

```text
                ┌──────────────────────────────┐
                │ Part 0 全局地圖（1–3）           │
                └──────────────┬───────────────┘
                               ▼
                ┌──────────────────────────────┐
                │ Part 1 第一個 Agent（4–8）       │  ◄── 所有後續 Part 的基礎
                └───┬──────────┬──────────┬────┘
                    ▼          ▼          ▼
     ┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
     │ Part 2 Context 與 │ │ Part 3 協定與  │ │ Part 4           │
     │ Memory（9–13）    │ │ 環境（14–17）  │ │ Orchestration    │
     └────────┬─────────┘ └──────┬───────┘ │ （18–22）          │
              │                  │         └────────┬─────────┘
              └──────────┬───────┴──────────────────┘
                         ▼
                ┌──────────────────────────────┐
                │ Part 5 打造 Framework（23–26） │
                └──────────────┬───────────────┘
                               ▼
     ┌──────────────────────┐     ┌──────────────────────┐
     │ Part 6 評估與優化（27–30）│ ◄─► │ Part 7 安全與治理（31–34）│
     └───────────┬──────────┘     └──────────┬───────────┘
                 └──────────────┬────────────┘
                                ▼
       Part 8 System Design（35–38）─► Part 9 案例與演練（39–44）─► Part 10 Capstone（45–46）
```

這張依賴圖說明章節之間的先後關係。Part 0 與 Part 1 是所有人都該讀的基礎；Part 2、3、4 是三條可以平行閱讀的支線，分別處理「模型看到什麼」「agent 能碰到什麼」「多個步驟或多個 agent 怎麼組織」；三條支線在 Part 5 匯合成 framework。Part 6 與 Part 7 互相引用，因為安全防禦需要評估，評估也要涵蓋安全；最後 Part 8 到 10 把所有元件組合成完整的系統設計。

| Part | 章 | 主題 | 讀完你能做到 |
|---|---|---|---|
| 0 全局地圖 | 1–3 | agent 的定義、十個元件、LLM 基礎 | 判斷何時該用 agent，看懂各家 API 與成本模型 |
| 1 第一個 Agent | 4–8 | loop、tool 設計、system prompt、structured output、推理 patterns | 從零寫出可運作的單一 agent（loom v0.1） |
| 2 Context 與 Memory | 9–13 | context engineering、compaction、RAG、memory、大量工具 | 讓 agent 處理長任務、大知識庫與上百個工具 |
| 3 協定與環境 | 14–17 | MCP、A2A／AG-UI、computer use、sandbox | 讓 agent 安全地接上外部系統與執行環境 |
| 4 Orchestration | 18–22 | workflow patterns、graph、multi-agent、human-in-the-loop、durable execution | 組織多步驟與多 agent 系統，加入人工審核與故障恢復 |
| 5 打造 Framework | 23–26 | 核心抽象、runtime、model routing、框架選型 | 設計自己的 framework，或理性地選用現成框架 |
| 6 評估與優化 | 27–30 | eval、benchmarks、observability、優化 | 證明 agent 變好了，並找出失敗原因與成本熱點 |
| 7 安全與治理 | 31–34 | 威脅模型、防禦設計、identity 與授權、可靠性治理 | 做 threat modeling，設計多層防禦與稽核 |
| 8 System Design | 35–38 | 設計方法論、production 架構、產品化、上線路線圖 | 寫出完整的 agent system design doc |
| 9 案例與演練 | 39–44 | coding／research／客服 agent 案例，三個設計演練 | 拆解成功產品，完成 system design interview 題 |
| 10 Capstone | 45–46 | 組裝完整的 loom、趨勢與持續學習 | 擁有一套可擴充的 framework，並能持續跟上變化 |

附錄 A 到 F 依序是術語表、loom 程式碼導覽、框架與協定速查、設計與上線 checklists、30 題 agent system design 面試題、延伸閱讀。遇到不熟的術語可以隨時翻附錄 A；想知道某段程式在 loom 的哪個模組，翻附錄 B。

不同角色的讀者，可以依目標選擇路線。以下的路線都假設你已讀完 Part 0；如果時間有限，第 4 章是唯一不建議跳過的章節，因為後面所有程式都從它長出來。

| 讀者與目標 | 建議路線 | 可以先略讀 |
|---|---|---|
| 第一次做 agent、目標是上線一個產品 | Part 1 → 第 9、10、12 章 → 第 14、17 章 → 第 21 章 → 第 27、29 章 → 第 31、32 章 → 第 38 章 | 第 26、28 章 |
| 要打造自家 agentic framework | Part 1 → Part 2 → 第 19、22 章 → Part 5 → 第 29 章 → 第 45 章 | 第 37、41 章 |
| 技術主管或架構師，要做技術決策 | 第 2 章 → 第 18、20 章 → 第 26 章 → Part 6 → Part 7 → Part 8 | 動手做的程式細節 |
| 準備 agent system design 面試 | 第 2、3 章 → 第 18、20 章 → 第 35、36 章 → 第 42–44 章 → 附錄 E | 第 24、25 章的實作細節 |
| 產品經理，要評估價值與風險 | 第 21 章 → 第 34 章 → 第 37、38 章 → 第 41 章 | Part 3、Part 5 |

每一章的結構固定：故事開場、核心概念、動手做、實務應用、設計檢查清單、常見錯誤與除錯、重點整理、延伸問答、延伸閱讀。建議的讀法是先讀故事與核心概念，再把動手做的程式實際跑一次並試著改動劇本；設計檢查清單可以在你自己的專案設計審查時直接拿來用。所有程式只用 Python 標準函式庫，用 ScriptedModel（依劇本回應的假模型）取代真實 LLM，所以不需要 API key、不需要網路，跑出來的結果每次都一樣。需要接真實 API 的程式會明確標註，並說明依據的 SDK 版本。

## 1.11 動手做：同一個客服請求的三種做法

現在把本章的概念變成可以執行的程式。我們用那則讓 Iris 出糗的客訴，分別用「單次呼叫」「固定 workflow」「agent loop」三種做法處理，然後用同一套評分規則比較結果。

先說明 **ScriptedModel**。真實的 LLM 每次輸出可能不同，也需要網路與 API key，不適合拿來教學與測試。ScriptedModel 是一個依「劇本」回應的假模型：劇本是一串事先寫好的回應，每呼叫一次 `complete()` 就取出下一步。劇本的某一步也可以是一個函式，接收當下的 `messages`，依內容產生回應，用來模擬「模型讀了 tool 結果之後才決定怎麼回答」。全書都用同一份 ScriptedModel 介面，第 4 章會再詳細說明它的設計。

程式裡的三個 tool 都是唯讀的：`get_order` 查訂單、`get_shipment` 查物流、`check_refund_policy` 依「配送中不能退款、送達 7 天內可退貨」的規則判斷。評分規則檢查回覆是否涵蓋四個關鍵事實（兩個單號、延誤原因、BB-1077 可申請退貨），以及是否捏造了「已為您辦理退款」這種沒有發生的動作。

```python
from __future__ import annotations

import json
import re
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


# ---- 青鳥科技的假資料與三個唯讀 tools ----
ORDERS = {
    "BB-1024": {"status": "in_transit", "tracking": "T-889", "paid": 1280},
    "BB-1077": {"status": "delivered", "delivered_days_ago": 3, "paid": 650},
}
SHIPMENTS = {"T-889": {"last_event": "轉運中心延誤", "eta_days": 2}}


def get_order(order_id: str) -> dict:
    return ORDERS.get(order_id, {"error": f"找不到訂單 {order_id}"})


def get_shipment(tracking: str) -> dict:
    return SHIPMENTS.get(tracking, {"error": f"找不到物流單 {tracking}"})


def check_refund_policy(order_id: str) -> dict:
    order = ORDERS[order_id]
    if order["status"] == "in_transit":
        return {"eligible": False, "reason": "配送中，可先申請攔截或等待送達"}
    if order["delivered_days_ago"] <= 7:
        return {"eligible": True, "reason": "送達 7 天內，可申請退貨"}
    return {"eligible": False, "reason": "超過 7 天鑑賞期"}


TOOLS: dict[str, Callable[..., dict]] = {
    "get_order": get_order, "get_shipment": get_shipment, "check_refund_policy": check_refund_policy,
}
REQUEST = "我的訂單 BB-1024 一直沒到，可以直接退款嗎？另外 BB-1077 的衣服尺寸不合也想退。"


# ---- 做法一：單次呼叫。模型看不到任何資料，只能「猜」 ----
def single_call(model: ScriptedModel, request: str) -> tuple[str, int]:
    reply = model.complete([{"role": "user", "content": request}])
    return reply.text, 0


# ---- 做法二：固定 workflow。路徑由程式碼寫死：抽單號 → 查訂單 → 查政策 → 寫回覆 ----
def fixed_workflow(model: ScriptedModel, request: str) -> tuple[str, int]:
    intent = model.complete([{"role": "user", "content": f"分類意圖：{request}"}]).text
    order_id = re.search(r"BB-\d+", request).group(0)   # 只抓第一個單號：這就是寫死路徑的代價
    facts = {"intent": intent, "order": get_order(order_id), "policy": check_refund_policy(order_id)}
    reply = model.complete([{"role": "user", "content": f"依資料回覆客人：{json.dumps(facts, ensure_ascii=False)}"}])
    return reply.text, 2


# ---- 做法三：agent loop。模型每一步決定要呼叫哪個 tool、何時停止 ----
def agent_loop(model: ScriptedModel, request: str, max_steps: int = 8) -> tuple[str, int]:
    messages: list[dict] = [{"role": "user", "content": request}]
    tool_count = 0
    for _ in range(max_steps):
        reply = model.complete(messages, tools=list(TOOLS))
        messages.append({"role": "assistant", "content": reply.text,
                         "tool_calls": [{"id": c.id, "name": c.name, "args": c.args} for c in reply.tool_calls]})
        if reply.stop_reason != "tool_use":
            return reply.text, tool_count
        for c in reply.tool_calls:                       # 執行 tool，結果回填給模型看
            result = TOOLS[c.name](**c.args)
            tool_count += 1
            messages.append({"role": "tool", "tool_call_id": c.id, "name": c.name,
                             "content": json.dumps(result, ensure_ascii=False)})
    raise RuntimeError("超過 max_steps，agent 沒有停下來")


def answer_from_results(messages: list[dict]) -> ModelResponse:
    """模擬模型讀完 tool 結果後寫回覆：內容完全來自 messages 裡的 tool 結果。"""
    results = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
    ship = next(r for r in results if "last_event" in r)
    p1024, p1077 = [r for r in results if "eligible" in r]
    return say(f"BB-1024 目前{ship['last_event']}，預計 {ship['eta_days']} 天內送達，"
               f"{p1024['reason']}。BB-1077 {p1077['reason']}，確認後我會幫您建立退貨單。")


# ---- 評分：回覆是否涵蓋關鍵事實、有沒有捏造已完成的動作 ----
MUST_HAVE = ["BB-1024", "延誤", "BB-1077", "可申請退貨"]
FORBIDDEN = ["已為您辦理退款"]


def grade(answer: str) -> tuple[int, bool]:
    covered = sum(f in answer for f in MUST_HAVE)
    fabricated = any(f in answer for f in FORBIDDEN)
    return covered, fabricated


models = {
    "單次呼叫": ScriptedModel([say("您好，BB-1024 正在配送中，已為您辦理退款，款項 3–5 天入帳。")]),
    "固定 workflow": ScriptedModel([
        say("refund"),
        say("BB-1024 尚未送達，暫時無法退款，可先申請攔截或等待送達。"),
    ]),
    "agent loop": ScriptedModel([
        call("get_order", "c1", order_id="BB-1024"),
        call("get_shipment", "c2", tracking="T-889"),
        ModelResponse(tool_calls=[ToolCall("c3", "check_refund_policy", {"order_id": "BB-1024"}),
                                  ToolCall("c4", "check_refund_policy", {"order_id": "BB-1077"})],
                      stop_reason="tool_use"),
        answer_from_results,
    ]),
}
runners = {"單次呼叫": single_call, "固定 workflow": fixed_workflow, "agent loop": agent_loop}

print(f"請求：{REQUEST}\n")
report = {}
sent_chars = {}
for name, model in models.items():
    answer, tools_used = runners[name](model, REQUEST)
    covered, fabricated = grade(answer)
    # 每次呼叫都要把整段 messages 重送一次，所以 agent 的 context 成本會累加
    sent = sum(len(json.dumps(c, ensure_ascii=False)) for c in model.calls)
    sent_chars[name] = sent
    report[name] = (len(model.calls), tools_used, covered, fabricated)
    print(f"[{name}] 模型呼叫 {len(model.calls)} 次、tool 呼叫 {tools_used} 次、送進模型 {sent} 字元")
    print(f"  事實 {covered}/{len(MUST_HAVE)}、捏造動作：{'是' if fabricated else '否'}")
    print(f"  回覆：{answer}\n")

assert report["單次呼叫"] == (1, 0, 1, True)        # 便宜，但會捏造「已退款」
assert report["固定 workflow"] == (2, 2, 1, False)  # 不捏造，但漏掉第二張訂單與物流原因
assert report["agent loop"] == (4, 4, 4, False)     # 最完整，代價是 4 次模型呼叫
assert sent_chars["agent loop"] > sent_chars["固定 workflow"] > sent_chars["單次呼叫"]
print("三種做法的取捨驗證通過")
```

```text
請求：我的訂單 BB-1024 一直沒到，可以直接退款嗎？另外 BB-1077 的衣服尺寸不合也想退。

[單次呼叫] 模型呼叫 1 次、tool 呼叫 0 次、送進模型 81 字元
  事實 1/4、捏造動作：是
  回覆：您好，BB-1024 正在配送中，已為您辦理退款，款項 3–5 天入帳。

[固定 workflow] 模型呼叫 2 次、tool 呼叫 2 次、送進模型 301 字元
  事實 1/4、捏造動作：否
  回覆：BB-1024 尚未送達，暫時無法退款，可先申請攔截或等待送達。

[agent loop] 模型呼叫 4 次、tool 呼叫 4 次、送進模型 2106 字元
  事實 4/4、捏造動作：否
  回覆：BB-1024 目前轉運中心延誤，預計 2 天內送達，配送中，可先申請攔截或等待送達。BB-1077 送達 7 天內，可申請退貨，確認後我會幫您建立退貨單。

三種做法的取捨驗證通過
```

逐段解讀這份輸出。**單次呼叫**只花了 1 次模型呼叫、送進模型的內容最少，但它只答對了「提到 BB-1024」這一項，而且捏造了「已為您辦理退款」。這正是開場 demo 的翻版：模型沒有任何資料，只能寫出「像客服回覆」的文字。這個結果也提醒我們，劇本雖然是寫好的，但它模擬的是真實模型在缺乏資料時的典型行為。

**固定 workflow** 沒有捏造任何東西，因為回覆是依查到的資料寫的，而程式也沒有開放退款動作。但它仍然只得到 1 分：程式碼用正規表示式只抓了第一個單號，路徑裡也沒有「查物流」這一步，所以 BB-1077 被忽略，延誤原因也沒有說明。注意這不是 workflow 寫得不好，而是它忠實地執行了設計者預想的路徑；要修正，就得替「多單號」「退款前先查物流」各加一條分支。

**agent loop** 四項事實全部涵蓋，也沒有捏造動作，而且最後一句「確認後我會幫您建立退貨單」把有副作用的動作留給人確認，這就是 L3 的行為。它的代價清楚寫在第一行：4 次模型呼叫，送進模型的字元數是 workflow 的七倍左右。原因是 agent 每一步都要把**完整的** `messages`（包含先前所有 tool 結果）重新送給模型，所以每次呼叫的 context 都比上一次更長，總成本隨步數快速累加。這個成本結構是第 3 章（token 與成本模型）、第 9 章（context engineering）與第 10 章（compaction）要處理的核心問題。

再看程式裡幾個值得注意的設計。第一，`agent_loop` 有 `max_steps=8`，超過就丟出例外，這是 harness 層的硬停止條件，不依賴模型自己說「完成了」。第二，tool 的執行發生在 harness 裡，模型只提出 `ToolCall`；如果劇本裡模型要求一個不存在的 tool，`TOOLS[c.name]` 會直接失敗，第 4 章會改成把錯誤回填給模型讓它修正。第三，`answer_from_results` 只從 `messages` 中的 tool 結果組出答案，模擬「有根據的回答」，這種讓回覆可以追溯到資料來源的性質叫 **grounding**（第 11 章）。

建議你動手改幾個地方，感受三種做法的差異：把 `REQUEST` 改成只問 BB-1024，看看 workflow 是否就足夠了（是的，而且更便宜）；把 agent 劇本的第二步刪掉，模擬模型「忘了查物流」，看評分怎麼變化；把 `max_steps` 改成 2，觀察硬停止條件如何攔下沒做完的 agent。這三個實驗分別對應「什麼時候不需要 agent」「agent 的決策品質」「harness 的護欄」，是後面章節的三條主線。

## 1.12 實務應用

本章的概念在不同產業會落到不同的設計選擇上。以下四個情境都依「光譜位置、autonomy 等級、三個任務特徵」來分析，並說明市面上公開的做法。

**情境一：電商與 SaaS 客服。**這是青鳥的主戰場，也是 agent 最早大規模商用的領域之一。客服請求高度開放（同一句「我要退款」背後可能有十種情況），結果大致可驗證（回覆要和訂單資料一致），但退款、補償等動作不可逆。所以常見的架構是：用 workflow 處理高頻的簡單查詢，agent 處理複雜個案，所有金錢動作都設門檻與人工核准，並且一定要有「轉真人」的出口。公開資訊中，客服 agent 公司 Sierra 發表了 τ-bench 系列 benchmark，用模擬顧客與政策文件測試 agent 是否遵守規則，並提出 pass^k（同一題連續 k 次都成功的機率）來衡量一致性；Intercom 的研究部落格有一篇以〈The Agency, Control, Reliability (ACR) Tradeoff〉為題的文章，從標題就看得出它關注的正是自主程度、可控性與可靠性三者之間的取捨，和本章的光譜觀點相呼應。要注意的是：客服場景裡「一致性」比「平均表現」更重要，因為同一位客人問兩次得到不同答案，傷害的是信任。

**情境二：軟體開發的 coding agent。**修 bug、加功能、寫測試是三個特徵都很符合的任務：步驟無法事先列舉，測試與編譯提供強力的自動驗證，而在 branch 上的修改可以丟棄。因此 coding agent 通常能給到較高的 autonomy：在隔離的 sandbox 裡自主讀檔、改檔、跑指令，但「合併到主幹」這個不可逆的動作留給人。公開文件中，Claude Code 把它的 loop 描述為交錯進行的三個階段：蒐集 context、採取行動、驗證結果；GitHub 的 Copilot coding agent 在 GitHub Actions 的臨時環境中執行，每個任務對應一個 branch 與一個 pull request，由人審查後合併。這兩個例子都體現了「可回復性決定 autonomy」：sandbox 與 branch 讓錯誤變得便宜。

**情境三：研究與營運分析。**「整理競品這季的定價變化」「分析上個月退款率上升的原因」這類任務開放且只需要讀取，風險主要在結論錯誤而不是破壞系統。常見的設計是讓 agent 大量搜尋與閱讀，必要時平行派出多個子 agent，最後由人驗收結論與引用。公開資訊中，Anthropic 的 Research 功能採用一個主 agent 協調多個平行搜尋子 agent 的架構；ChatGPT 的 deep research 在研究前會先釐清需求、改寫問題；Google 的 Gemini Deep Research agent 提供「協作規劃」，讓使用者先確認研究計畫再執行。這些設計的共同點是：在不可驗證的部分（「這個結論對不對」）把人放回 loop，在可驗證的部分（引用是否存在）用程式檢查。

**情境四：企業內部的 IT 與 HR 工單。**「重設密碼」「申請筆電」「查詢假別」這類請求量大但路徑固定，多數應該是 workflow 甚至一般表單，只在「描述模糊、需要判斷屬於哪一類」的入口使用 LLM 分類（routing）。真正適合 agent 的只有少數複雜工單，例如「新人到職要開哪些系統權限」，因為它需要查詢多個系統、依部門規則組合。這個情境是「什麼時候不該用 agent」最常見的反例：團隊先做了一個全能 agent，後來發現 80% 的請求用 workflow 就能處理得更快更便宜。OpenAI 的〈A practical guide to building agents〉也列出 agent 最有價值的三類場景：需要複雜判斷（例如退款核准）、規則多到難以維護、需要處理大量非結構化資料，其他情況建議優先考慮確定性方案。

| 情境 | 光譜位置 | 典型 autonomy | 最關鍵的驗證方式 | 不可回復的動作與對策 |
|---|---|---|---|---|
| 電商客服 | workflow 入口＋agent 處理複雜個案 | 查詢 L4、退款 L3 | 回覆和訂單資料比對、政策遵循 eval | 退款、補償：門檻＋人工核准 |
| Coding agent | agent（單一主 loop） | sandbox 內 L4 | 測試、編譯、code review | 合併、部署：留給人 |
| 研究分析 | agent＋平行子 agent | 唯讀，接近 L5 | 引用檢查、人驗收結論 | 少；主要風險是錯誤結論被採用 |
| 內部工單 | 以 workflow 為主 | L2，少數 L3 | 表單欄位驗證 | 權限開通：審批流程 |

這張表把四個情境並排。你會發現沒有一個成功的應用是「純 agent、全自動」：每一個都在光譜上選了混合的位置，並且依動作的可回復性分配 autonomy。這也是本書反覆強調的設計態度：agent 是工具箱裡的一把工具，不是整個工具箱。

## 1.13 設計檢查清單

在決定要不要做 agent、以及做成什麼樣子時，逐項回答下列問題。

1. 這個任務的步驟能事先列舉嗎？如果能，為什麼不用 workflow？
2. 系統中「下一步由誰決定」的每一段，是程式碼還是模型？有沒有畫出光譜位置？
3. 任務結果有客觀的驗證方法嗎？agent 在執行過程中能取得哪些 ground truth？
4. 每一個 tool 都標了風險等級（讀取／寫入／金錢／破壞性，第 5 章收斂為 read／write／destructive）嗎？沒有標註的是否預設當成最高風險？
5. 每一類動作的 autonomy 等級是什麼（自動、核准、禁止）？是依動作決定，而不是整個系統一個等級嗎？
6. 不可回復的動作是否都有執行前的核准或其他防護？
7. Harness 有沒有模型判斷之外的硬停止條件：步數上限、token 或金額預算、逾時？
8. 每個請求預期的模型呼叫數與 context 長度是多少？乘上流量後的成本與延遲可以接受嗎？
9. 高頻且路徑固定的請求，是否已經用 workflow 分流，而不是全部進 agent loop？
10. 有沒有「轉真人」或「交回使用者」的出口？什麼情況會觸發？
11. 從低 autonomy 等級升到高等級的條件（eval 分數、核准接受率、事故數）有沒有事先寫下？
12. 是否能記錄完整的 trajectory，讓出錯時可以重現每一步的決策？

## 1.14 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 回覆說「已幫您退款」，但系統沒有任何退款紀錄 | 模型沒有 tool 或沒有呼叫 tool，只是寫出「像客服的話」 | 對照 trajectory：該回合沒有任何 tool call，或 tool 結果與回覆內容不符 | 讓動作只能透過 tool 發生；用評分規則攔下「宣稱完成但沒有對應 tool 結果」的回覆 |
| 簡單查詢也花了五、六次模型呼叫，成本暴增 | 把路徑固定的任務整個交給 agent | 統計各意圖的平均步數，看高頻意圖是否步數也高 | 用 routing workflow 把高頻簡單請求分流；agent 只處理複雜個案 |
| Agent 在同一個 tool 上反覆重試，直到逾時 | 只依賴模型判斷停止，沒有硬限制；或 tool 錯誤訊息無法引導修正 | 看 trajectory 是否有重複的相同 tool call | 加上 max_steps 與預算上限；讓 tool 錯誤訊息說明如何修正（第 5 章） |
| 多問題的請求只回答了第一個 | workflow 寫死只處理單一意圖或單一實體，或 agent 太早停止 | 用含多個單號的測試案例重跑，檢查哪些實體被處理 | workflow 加入多實體處理；agent 在 system prompt 與 eval 中涵蓋多問題情境 |
| 團隊爭論「這是不是 agent」卻得不出結論 | 混淆了「有沒有 tools」「路徑由誰決定」「副作用由誰核准」三件事 | 把系統的每一段標上光譜位置與 autonomy 等級 | 用本章的二維圖分開討論決策權與核准權 |
| 上線後才發現某個寫入動作被自動執行了 | autonomy 是以系統為單位設定，沒有依動作分級 | 列出所有 tool，檢查每一個的風險等級與核准規則 | 建立「風險 × 等級」決策表，預設拒絕，逐一開放 |
| Demo 很成功，上線後成功率明顯下降 | demo 用的是精心挑選的請求；沒有可驗證的成功標準 | 收集真實請求做 error analysis，計算成功率與失敗類型 | 建立 eval set 並在每次修改後回歸測試（第 27 章） |

## 本章重點整理

- 一次 LLM 呼叫是 `text → text` 的轉換：模型不保留狀態、只看得到 prompt、輸出只是文字，要不要相信與執行由外部程式決定。
- Tool calling 讓模型能「提出」呼叫外部功能的請求，但真正執行的永遠是你的程式，這個分工是所有安全設計的基礎。
- Workflow 由程式碼事先決定路徑，LLM 只負責其中的判斷或寫作節點；它用彈性換取可預測性與可測試性。
- 本書對 agent 的定義是：模型在 loop 中根據環境回饋自己決定下一步，也自己決定何時停止。
- 判斷是不是 agent 的關鍵不在有沒有 tools，而在模型能不能看到行動結果並據此決定是否繼續。
- 停止條件必須是雙層的：模型的判斷之外，harness 還要有步數、預算與逾時等硬限制。
- 單次呼叫、workflow、agent 是一條光譜；越往右彈性越大，但成本、延遲與不可預測性也越高，實際系統通常是混合體。
- Autonomy 回答「副作用由誰核准」，和「路徑由誰決定」是兩個獨立的軸；本書用 L0–L5 描述，但這不是業界統一標準。
- Autonomy 應該依動作決定而不是依系統決定，不可回復的動作永遠不應完全自動執行。
- 路徑可列舉、延遲嚴格、錯誤無法驗證又代價高、量大單價低的任務，通常不該用 agent。
- 適合 agent 的任務是開放、可驗證、可回復的；開放決定要不要用 agent，可驗證決定能否讓它自己完成，可回復決定能給多少 autonomy。
- Agent 每一步都要重送完整的 messages，所以 context 成本隨步數累加，這是後面 context engineering 與 compaction 的出發點。
- 自主權應該從低等級上線，用 eval 與線上資料證明可靠後，再一個動作一個動作地放寬。

## 延伸問答

> [!question]- Q1. 一個聊天機器人接了查訂單、查物流兩個 tool，它算 agent 嗎？
> 要看它怎麼使用 tool，而不是有沒有 tool。如果每次使用者發問，系統只做「模型挑一個 tool → 程式執行 → 把結果直接格式化給使用者」，模型從來沒有看到 tool 的結果、也沒有據此決定下一步，那它比較接近 routing workflow：模型只做了一次分類，路徑的其餘部分是固定的。
>
> 如果 tool 結果會回填給模型，模型可以依結果決定再查物流、改查另一張訂單，或判斷資料已經足夠而回答，那它就具備 agent 的兩個核心性質：依環境回饋決定下一步、自己決定何時停止。實務上這個區分很重要，因為它決定了你要怎麼測試：前者可以列舉路徑寫單元測試，後者必須用 eval 統計成功率。

> [!question]- Q2. 青鳥的退款流程應該做成 workflow 還是 agent？怎麼決定？
> 先拆解退款流程裡的決策。「這筆訂單符不符合退款政策」是規則判斷，可以寫成程式；「客人到底想要什麼、牽涉幾張訂單、要不要先查物流」是開放的理解與調查；「把錢退出去」是不可逆的動作。三者的性質不同，不必用同一種做法。
>
> 合理的設計是混合：讓 agent 負責理解與調查（開放、可用訂單資料驗證），政策判斷做成一個確定性的 tool（`check_refund_policy`），而真正的退款動作做成需要核准的 tool，金額門檻以下才可能自動。這樣模型的彈性用在它擅長的地方，規則與金錢則留在可證明、可稽核的程式碼裡。如果分析後發現九成退款請求都是「單一訂單、已送達、7 天內」，那麼入口再加一個 routing，把這類請求直接走 workflow，會更便宜也更穩定。

> [!question]- Q3. 你在 production 看到客服 agent 對「我的貨到哪了」這種簡單問題平均也要呼叫模型五次，成本是預期的三倍。你會怎麼處理？
> 第一步是從 trajectory 找出多出來的步驟是什麼。常見原因有三種：模型習慣性地多查（例如每次都查退款政策）、tool 回傳的資訊不完整迫使它再查一次（例如 `get_order` 沒附物流狀態）、或 system prompt 沒有說明何時可以直接回答。這三種的修法完全不同，所以要先確認再動手。
>
> 第二步是重新檢視光譜位置。「貨到哪了」是路徑幾乎固定的高頻請求，本來就適合用 routing 分流到固定 workflow：查訂單、查物流、寫回覆，兩次模型呼叫就夠。agent 只保留給多意圖或異常的個案。最後，把「各意圖的平均步數與成本」做成監控指標，下次有類似退化時能及早發現。這個問題的本質是「把不開放的任務交給了 agent」，而不是模型不夠好。

> [!question]- Q4. System design 面試中被問：「你設計的客服 agent 要給它多少自主權？」該怎麼回答？
> 好的回答不是給一個等級，而是說明「依動作分級」的方法。先列出 agent 會用到的動作並分風險：查訂單與物流是讀取，建立退貨單是可撤銷的寫入，退款是不可逆的金錢動作，修改帳號資料涉及個資。接著說明每一類的初始策略：讀取自動，寫入要客服確認，金錢設門檻並人工核准，個資相關一律轉真人。
>
> 然後說明自主權如何演進：上線初期採保守設定，蒐集核准紀錄與 eval 結果；當某類動作的建議被人接受的比例長期很高、事故率在 error budget 內，再把它的門檻放寬。也要提到 harness 層的硬限制（步數、預算、逾時）與稽核紀錄，說明出事時如何追溯。面試官要聽的是你能把「自主權」轉成可執行的政策與可量測的升級條件，而不是一個抽象的等級。

> [!question]- Q5. 下面這個 loop 有什麼問題？`while True:` 呼叫模型，若 `stop_reason == "tool_use"` 就執行 tool 並把結果 append 進 messages，否則 return 回覆。
> 第一個問題是沒有硬停止條件。整個 loop 只依賴模型輸出 `end_turn` 才會結束；只要模型陷入重複呼叫同一個 tool 的狀態，或 tool 一直回傳讓模型想重試的錯誤，這個 loop 就會一直跑，直到 context 爆掉或帳單爆掉。至少要加上 `max_steps`，實務上還要加 token 或金額預算與逾時，並在觸發時回傳明確的失敗狀態而不是假裝成功。
>
> 第二個要檢查的是 `stop_reason` 的其他值。例如 `max_tokens` 代表模型的輸出被截斷，此時回傳的文字可能是半句話，直接交給使用者並不妥當；第三個是 tool 執行失敗時的處理，如果例外直接往外丟，整個 session 就中斷，更好的做法是把錯誤包成 tool 結果回填，讓模型有機會修正。這些細節都會在第 4 章的最小 loop 中逐一處理。

> [!question]- Q6. 估算：青鳥每天有 2 萬則客訴。若全部用 agent 處理，平均每則 4 次模型呼叫、每次送進模型平均 6,000 個 token；若用 workflow，平均 2 次呼叫、每次 2,000 token。兩者每天的 input token 差多少？
> Agent：20,000 × 4 × 6,000 = 4.8 億 token／天。Workflow：20,000 × 2 × 2,000 = 8,000 萬 token／天。差距是 6 倍，每天多出 4 億個 input token。注意 agent 的每次呼叫平均 token 數比較高，是因為後面的呼叫要重送前面所有的 tool 結果；步數越多，平均值越高，所以步數與單次 context 長度是相乘關係。
>
> 換算成金額時要用你實際使用的模型單價，並考慮 prompt caching：agent 每次重送的前綴大多相同，快取命中時這部分的計價會大幅降低（第 3、9 章）。這個估算也指出最有效的優化方向：如果 70% 的客訴是簡單查詢，把它們分流到 workflow，agent 的流量只剩 6,000 則，總量就降到約 1.44 億＋5,600 萬，大約是全 agent 方案的四成。估算的價值不在精確，而在找出哪個變數影響最大。

> [!question]- Q7. 為什麼本書把「可回復」當成判斷 agent 任務的核心特徵之一？模型越來越聰明，這個條件還重要嗎？
> 因為再好的模型也有非零的錯誤率，而錯誤的代價取決於能不能撤銷。一個 99% 正確的 agent，處理 1 萬筆可回復的任務，100 筆錯誤可以被發現並撤回，成本是重做；但如果是 1 萬筆不可逆的退款，100 筆錯誤就是實際的金錢損失與客訴。可回復性把「模型的錯誤率」轉換成「系統的損失」，所以它是架構問題，不是模型能力問題。
>
> 模型變強會降低錯誤率，讓你可以在可回復的動作上給更多自主，但不可逆動作的風險結構不會改變。而且 agent 還面臨模型之外的風險，例如 prompt injection（第 31 章）讓模型被外部內容誘導做出錯誤動作，這和模型多聰明關係不大。實務上，與其等待更聰明的模型，不如把動作設計得更可回復：先建立草稿再送出、先在 sandbox 驗證再套用、把退款拆成「建立申請」與「核准執行」兩步。

> [!question]- Q8. L5 的完全自主是不是 agent 發展的終極目標？團隊應該以達到 L5 為里程碑嗎？
> 不應該。Autonomy 等級是依任務風險選擇的設定，不是品質分數。研究型的唯讀任務可能適合接近 L5，因為錯誤主要表現為報告品質，人驗收即可；但處理客戶金錢的客服 agent，即使模型非常可靠，在退款這類動作上維持門檻與抽查也是合理的商業與法規選擇。把 L5 當目標，會誘導團隊放寬不該放寬的核准。
>
> 比較好的里程碑是可量測的：某類動作的成功率與一致性（例如 pass^k）、核准建議被接受的比例、事故率是否在 error budget 內、每次成功任務的成本。當這些指標支持放寬時，才針對那一類動作提高 autonomy。這也意味著 autonomy 可能下降：換了模型或改了 prompt 後 eval 退步，就應該暫時收回權限。把 autonomy 當成隨證據調整的旋鈕，而不是單向的升級路線。

## 延伸閱讀

- Anthropic Engineering Blog〈Building effective agents〉（2024）
- OpenAI〈A practical guide to building agents〉（2025）
- Google〈Agents〉whitepaper（Wiesinger et al.，2024）
- HumanLayer〈12-Factor Agents〉（Dex Horthy，2025）
- Yao et al.〈ReAct: Synergizing Reasoning and Acting in Language Models〉（ICLR 2023）
- Anthropic Engineering Blog〈Effective context engineering for AI agents〉（2025）
- Sierra〈τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains〉（2024）
- SAE International〈J3016：Taxonomy and Definitions for Terms Related to Driving Automation Systems〉
