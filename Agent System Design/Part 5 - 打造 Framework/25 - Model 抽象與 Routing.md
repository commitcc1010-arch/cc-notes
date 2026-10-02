---
chapter: 25
title: Model 抽象、Provider Adapter 與 Routing
part: 5
---

# 第 25 章　Model 抽象、Provider Adapter 與 Routing

> [!abstract] 本章地圖
> **核心問題**：當 agent 要同時面對好幾家模型供應商、好幾種大小的模型，而且任何一家都可能在尖峰時段倒下時，model 層要怎麼設計，才能讓上層的 loop 完全不必知道背後是誰，又不會在換家時悄悄壞掉或燒錢？
>
> **你會學到**：
> - 列出各家模型 API 在訊息與 tool 格式、thinking／effort、cache 控制、usage 欄位、stop reason 與錯誤碼上的差異，並判斷哪些要統一、哪些要原樣保留
> - 設計 provider adapter 的介面，把不同形狀的回應正規化成全書統一的 `ModelResponse`，同時保留不透明欄位
> - 把模型 API 的錯誤分成「同一家重試」「換一家」「立刻停下」三類，並實作失敗率熔斷器
> - 設計 fallback chain，處理換家時的能力差異、資料落地限制、冷快取與歷史轉換
> - 依任務類別、難度、成本與延遲做 model routing，比較規則、分類器、cascade 與「主模型＋輔助模型」
> - 建立版本化價格表與成本帳本，算出每個租戶、每個 agent、每次成功任務的成本
>
> **前置知識**：第 3 章（token、reasoning 與 effort、三種 function calling 形態、prompt caching 計價）、第 4 章（`loom` v0.1 與統一的 `ModelResponse`）、第 18 章（routing 與 cascade 的 workflow 形式）、第 23、24 章（`loom` v0.5 的核心抽象與 runtime）

## 25.1 故事：雙 11 晚上的四十分鐘

雙 11 當晚九點，青鳥科技的客服 agent 正處在一年中流量最高的時刻。九點零七分，主力模型供應商的 API 開始大量回傳「服務過載」，接著連正常的請求也要等二十幾秒才回來。客服 agent 的 loop 照第 4 章的設計，對模型 API 的錯誤做了指數退避重試，但每一個 session 都在各自重試，數千個 session 同時退避、同時醒來、同時再打一次，原本只是過載的供應商被打得更慢。四十分鐘裡，使用者看到的不是答案，而是「處理中」的轉圈圈。

事後檢討時，Iris 發現問題不只一個。第一，青鳥其實已經和第二家供應商簽了約，第 3 章為了資料落地的租戶也寫過一個簡單的 adapter，但它只被那幾個租戶使用，沒有人把它接成主力供應商倒下時的備援。第二，Iris 在事故當下臨時加上「失敗就改呼叫第二家」的程式碼，結果第二家回了 400：歷史裡第一家模型的 thinking 區塊和簽章被原封不動地轉送過去，對方根本不認得。第三，第二天的成本報表顯示當晚的 token 用量比平常多了將近一倍，一查才知道，兩家的 usage 欄位語意不同，一家的 input tokens 包含快取命中的部分，另一家不包含，Iris 的報表把快取算了兩次。

阿哲則帶來另一個問題。營運 research agent 的月度帳單是客服 agent 的三倍，但 trace 顯示它有七成的模型呼叫只是在做「這段文字屬於哪一類」「把這頁摘要成三行」這種小工作，卻全部用前沿模型、高 effort 執行。「我們是不是該讓簡單的事用便宜的模型做？」阿哲問。Maya 補了一句：「換模型的時候，歐盟租戶的資料只能送到合約允許的區域，這條規則不能交給 prompt 去記。」

老陳把三個 agent 的程式碼攤開，指出它們各自用不同的方式呼叫模型：客服 agent 直接呼叫第一家的 SDK，coding agent 透過一個開源 gateway，research agent 則有一份自己寫的重試邏輯。「第 23 章我們把 `loom` 的核心抽象定下來，第 24 章把 runtime 改成能串流、並行與取消，」老陳說，「最後一塊是 model 層。三個 agent 都該透過同一個 `loom.models` 呼叫模型：adapter 負責翻譯，熔斷器負責別再敲壞掉的門，fallback 負責換家，router 負責選模型，帳本負責算錢。這五件事做完，`loom` 才算 v0.5。」

這一章依序拆解 model 層的位置、各家 API 的差異、adapter、錯誤分類、熔斷器、fallback、routing 與成本計量，最後在「動手做」用兩家假 provider 重演雙 11：熔斷器打開、流量切到第二家、冷卻後切回，每一筆錢都記在帳本上。

## 25.2 Model 抽象的邊界：loom.models 在架構中的位置

### 為什麼需要一層 model 抽象

在 agent loop 裡直接呼叫某一家的 SDK，在只有一個 agent、一家供應商時完全合理。問題出現在三個時刻：第二家供應商進來，loop 裡開始出現 `if provider == ...`；第二個模型尺寸進來，每個呼叫點都要自己選；第一次供應商事故發生，每個 agent 各自發明一套重試與備援。這些都和 agent 要做什麼無關，卻散落在每一個呼叫點。

**Model 抽象**（model abstraction）是在 agent loop 與供應商 API 之間的一層，對上只暴露一個穩定的介面，對下處理所有供應商相關的細節。軟體架構裡把這種設計叫 **ports and adapters**（埠與轉接器，也稱六角形架構）：上層定義自己需要的「埠」（這裡是 `complete(messages, tools, system) -> ModelResponse`），每家供應商各寫一個 **adapter**（轉接器）去實作它。舉例來說，客服 agent 的 loop 只說「用這些訊息與 tools 問模型」，至於這次是送到哪家、用什麼 JSON 格式、帶哪個 header，全部是 adapter 的事。

### 分層：五個元件各管一件事

```text
 Agent loop／Runner（第 4、23、24 章）
   │  complete(messages, tools, system, task=..., tenant=...)   ← 唯一的埠
   ▼
 ┌─ loom.models ───────────────────────────────────────────────────────┐
 │  (1) Router        依任務類別、租戶政策、預算，挑出一條候選鏈        │
 │        │                                                            │
 │  (2) FallbackChain 依序嘗試候選；錯誤可換家才往下走                 │
 │        │                                                            │
 │  (3) Breaker       每個 provider（或 provider＋模型＋區域）一個     │
 │        │           打開時直接跳過，不等逾時                         │
 │  (4) Adapter       統一格式 ⇄ provider JSON；錯誤 → ModelError      │
 │        │           不透明欄位（thinking、reasoning）原樣保留        │
 │  (5) CostLedger    每次成功回應，依版本化價格表記帳                 │
 └────────┼────────────────────────────────────────────────────────────┘
          ▼
 Transport：HTTP／SDK（逾時、連線池；SDK 內建重試關掉，由 runtime 統一管）
          ▼
 Provider A（messages 形態）     Provider B（items 形態）     ScriptedModel（測試）
```

這張圖由上往下是一次模型呼叫經過的路徑。最上面的 agent loop 只認得一個埠，它甚至不知道下面有 router。第 (1) 層 router 根據這次呼叫的任務類別（分類、回覆、退款審查）、租戶政策（資料只能留在某些區域）與預算，挑出一條候選模型的清單。第 (2) 層 fallback chain 照清單依序嘗試，只有當錯誤屬於「換一家有用」的類別才往下一個走。第 (3) 層熔斷器替每個 provider 記錄最近的健康狀況，壞掉時讓 chain 直接跳過，不必每次都等到逾時。第 (4) 層 adapter 做格式翻譯與錯誤分類。第 (5) 層帳本在每次成功回應後記帳。最底下是傳輸層，以及三種「模型」：兩家真實 provider，和第 4 章的 ScriptedModel。

最下面那一列值得注意：ScriptedModel 和兩家 provider 站在同一層。上層只認得 `complete()` 這個埠，所以測試時把 adapter 換成假的，router、fallback、熔斷器與帳本都能離線、可重現地測試；第 24 章的 runtime 呼叫的也是同一個埠，不需要為本章修改。

### 統一什麼、透傳什麼

設計 model 抽象最大的陷阱是**最小公分母**（lowest common denominator）：只保留所有供應商都有的功能，結果每一家最有價值的能力都被抽象層藏起來。反方向的陷阱是把每一家的參數都搬進統一介面，最後介面變成三家 API 的聯集，每個欄位都要附註「只有某某家支援」。比較穩健的做法是分三層：大家語意相同的部分統一；語意相近但細節不同的部分抽象成「意圖」，由 adapter 翻譯；只有某一家才有的功能，放進一個明確標示的 `provider_options` 透傳欄位。

| 項目 | 處理方式 | 為什麼 | 例子 |
|---|---|---|---|
| 訊息、tool 定義、tool call、tool 結果 | 統一 | 所有 agent loop 都依賴它，語意相同 | 第 4 章的 `ToolCall{id, name, args}` |
| stop reason | 統一成少數幾個值，不認得的值大聲失敗 | 上層依它決定停或繼續 | `end_turn`、`tool_use`、`max_tokens`、`refusal` |
| usage | 統一成「互斥」的幾個桶 | 成本與預算要能直接相加 | 未快取輸入、快取讀、快取寫、輸出 |
| 推理強度 | 抽象成意圖（`effort`），adapter 翻譯 | 各家旋鈕不同但目的相同 | low／medium／high 對應各家參數 |
| cache 斷點 | 抽象成「前綴穩定到這裡」的標記 | 有的要顯式標記，有的自動 | adapter 決定要不要插入 breakpoint |
| thinking 區塊、加密 reasoning、簽章 | 原樣保留在 `raw`，不解讀 | 下一輪要送回同一家，否則推理斷裂或報錯 | 換家時丟棄，只保留可重建的部分 |
| 某一家獨有的 server tool 或 beta 功能 | 透傳（`provider_options`） | 不值得為單一家擴充統一介面 | 只在指定該 provider 的路由上使用 |

這張表是 `loom.models` 的設計憲法。最上面三列是「統一」：上層程式直接依賴它們，所以必須在所有 adapter 上語意一致，usage 尤其要設計成可以直接相加的互斥桶，25.4 節會看到為什麼。中間兩列是「意圖」：上層說「這個步驟需要高推理強度」或「到這裡為止的前綴是穩定的」，由 adapter 翻成各家的參數。下面兩列是「保留與透傳」：抽象層不理解它們，但絕不能弄丟。常見的誤解是「抽象層要讓所有 provider 看起來一模一樣」；真正的目標是讓上層**不必知道**差異，同時讓差異**不會遺失**。

## 25.3 各家 API 差異地圖

第 3 章已經比較過三種 function calling 形態（messages、items、steps）。要寫出能上線的 adapter，還要再往下看五個維度：thinking 與 effort 怎麼控制、cache 怎麼標記、usage 怎麼回報、停止原因怎麼表示、錯誤怎麼分類。這些維度在 demo 時看不出差別，卻會在帳單、事故與換家時一次爆發。

### 訊息與 tool 格式

各家的差異首先在**歷史的容器**：第 3 章的 messages、items、steps 三種形態，加上 system 指令放在哪裡、是否每次都要重送。adapter 的第一個責任，就是把第 4 章的統一訊息格式（`user`、`assistant`、`tool` 三種角色）翻譯成各家的容器，並在回應時翻譯回來；其中最容易漏掉的細節是 messages 形態要求同一輪的多個 tool 結果放進同一則 user 訊息。

### Thinking、effort 與 cache

推理模型讓 adapter 多了兩件事。第一是旋鈕的翻譯：上層說 `effort="high"`，adapter 要知道這一家的參數叫什麼、放在哪一層、合法值有哪些，以及這個模型是否根本不能關掉 thinking。第二是**不透明欄位**（opaque fields）：thinking 區塊的簽章、加密的 reasoning 內容、thought signature，這些是供應商用來在多輪之間延續推理的資料，你看不懂也不該改，但下一輪必須原樣送回**同一家**。cache 控制則是第三個差異：有的供應商要你在請求中標記斷點並選 TTL，有的自動比對前綴，有的在某些介面上暫不支援顯式快取。對 adapter 來說，cache 最重要的事實是：**快取是依模型分開的**，換模型或換供應商，第一次呼叫一定是冷的。

### Usage 欄位：最容易算錯的地方

usage 是成本計量的原料，而各家對「input tokens」的定義並不一致。依各家公開文件，有的供應商把輸入拆成三個互斥的數字：未命中快取的輸入、寫入快取的輸入、從快取讀出的輸入，`input_tokens` 只代表第一個；另一種設計則讓 `input_tokens` 代表全部輸入，再用一個子欄位說明其中多少是快取命中。輸出也一樣：thinking 或 reasoning tokens 通常包含在輸出總數裡，再另外列出明細。如果 adapter 把兩種語意都當成「input_tokens 就是要付全價的部分」，其中一家的快取命中會被當成全價輸入，另一家的快取會被重複計算。Iris 雙 11 隔天的報表，就是這樣多算了一倍。

### Stop reason 與錯誤碼

停止原因的差異在第 3 章看過一部分：有的 API 直接回傳 `stop_reason`，有的只有 `status` 和輸出 item 的型別，要由 adapter 推導。值得補充的是「非典型」的停止原因：模型因安全理由拒答、伺服器端工具需要暫停後續、輸出撞到上限、context 超出視窗。這些值都會隨 API 版本增加，所以 adapter 對**不認得的停止原因要大聲失敗**，而不是默默當成 `end_turn`；後者會讓一個被截斷或被暫停的回應被當成完整答案交給使用者。錯誤碼也類似：同樣是 429，可能是「請求太快，等一下就好」，也可能是「額度用完，等多久都沒用」；同樣是 400，可能是「prompt 太長」，也可能是「tool 定義格式錯」。25.5 節會把這些整理成分類規則。

| 維度 | 差異在哪 | adapter 的責任 | 處理不好的後果 |
|---|---|---|---|
| 訊息容器 | 區塊、item、step；system 的位置 | 雙向翻譯；平行呼叫的結果合併 | 400 錯誤；模型學到「不要平行呼叫」 |
| tool 參數 | 物件或 JSON 字串 | 解析並處理解析失敗 | 半截參數被執行 |
| 推理控制 | 參數名稱、合法值、能否關閉 | 把 `effort` 意圖翻成各家參數 | 參數被拒；中途改設定讓 cache 失效 |
| 不透明欄位 | 簽章、加密 reasoning | 同一家原樣送回；跨家時丟棄 | 推理斷裂、400、跨家報錯 |
| cache 控制 | 顯式斷點或自動；TTL | 在穩定前綴尾端插入斷點 | 命中率掉到零，成本暴增 |
| usage | input 是否包含快取；reasoning 是否含在輸出 | 正規化成互斥的桶 | 成本報表重複計算或漏算 |
| 停止原因 | 欄位與值的集合不同 | 對應到統一值；不認得就失敗 | 截斷或拒答被當成完整答案 |
| 錯誤 | 狀態碼與 type 字串 | 分類成 `ModelError.kind` | 該換家的重試、該停的換家 |

這張表從上到下，大致也是 adapter 出錯的頻率排序。前兩列在第一次整合時就會被測試抓到，因為錯了 API 會直接拒絕；中間三列要到多輪 tool use、長 session 才會出現；最後三列最危險，因為錯了也不會報錯，只會讓成本報表、停止判斷或錯誤處理默默偏掉。所以 adapter 的測試重點應該放在後面幾列：用錄下來的真實回應（或依文件構造的假回應）做 **golden test**（黃金樣本測試，把已知正確的輸入輸出存起來比對），確認 usage 加總、停止原因與錯誤分類都對。

### 2026 現況：三家 API 的細節對照

截至 2026 年 10 月，依各家公開文件整理如下。標示「本書未經網路查證」的欄位，是依公開文件與 SDK 的一般用法撰寫，實作前請以官方 API reference 為準；Gemini 欄位中本書未查證的項目直接留白。

| 面向 | Anthropic Messages API | OpenAI Responses API | Gemini Interactions API |
|---|---|---|---|
| system 位置 | 頂層 `system` | `instructions`（本書未經網路查證） | `system_instruction`，每次請求都要重送 |
| 推理控制 | adaptive thinking＋`output_config.effort`（`low`／`medium`／`high`／`xhigh`／`max`）；手動 `budget_tokens` 已 deprecated | `reasoning.effort`（本書未經網路查證） | （本書未查證） |
| 不透明欄位 | thinking 區塊與簽章 | reasoning item，可帶 `encrypted_content`（本書未經網路查證） | thought signatures，stateless 模式要原樣回傳所有 model steps |
| cache 控制 | `cache_control` 斷點與頂層自動 caching；5 分鐘或 1 小時 TTL（斷點數量上限本書未經網路查證） | 自動前綴快取；部分新模型支援顯式 cache breakpoint（Cursor 2026-09 文章提到 GPT-5.6） | 尚未支援 explicit caching |
| usage | `input_tokens`（未快取部分）、`cache_creation_input_tokens`、`cache_read_input_tokens`、`output_tokens` | `input_tokens`（含快取）與 `input_tokens_details.cached_tokens`、`output_tokens` 與 `output_tokens_details.reasoning_tokens`（本書未經網路查證） | （本書未查證） |
| 停止表示 | `stop_reason`：`end_turn`、`tool_use`、`max_tokens`、`refusal` 等 | `status`；`incomplete` 時看 `incomplete_details.reason`；拒答為 `refusal` 類型輸出 | （本書未查證） |
| 常見錯誤 | 429 `rate_limit_error`、529 `overloaded_error`、400 `invalid_request_error`、401 `authentication_error` 等（本書未逐項網路查證） | 429 需區分速率限制與額度用盡（`insufficient_quota`）、5xx（本書未經網路查證） | （本書未查證） |
| 伺服器端狀態 | 無，client 送完整歷史 | `previous_response_id` 或 Conversations | `previous_interaction_id`；只有對話歷史延續，tools 與設定每次重傳 |

這張表要搭配兩個提醒閱讀。第一，Anthropic 在 2026 年的模型上，中途改 top-level effort 會讓 prompt cache 失效，官方另提供 beta 的 per-message effort 切換；Fable 5.1、Opus 5.5、Sonnet 5.5 不再接受強制 tool 的 `tool_choice`（本書未經網路查證）。第二，有伺服器端 web search 時，`cache_read_input_tokens` 會包含內部呼叫的累計值，直接拿來判斷 context 長度會高估。這類細節變化很快，所以本章的設計原則是：把每一家的規則集中寫在 adapter 裡，並用 golden test 鎖住，API 改版時只改一個地方。

## 25.4 Adapter 介面設計：把回應正規化成 ModelResponse

### 介面長什麼樣

`loom.models` 的 adapter 介面刻意和第 4 章的 ScriptedModel 一樣：`complete(messages, tools, system) -> ModelResponse`，再加上幾個關鍵字參數表達意圖，例如 `effort`。每個 adapter 內部拆成兩個純函式：**build** 把統一格式翻成 provider 的請求 JSON，**parse** 把 provider 的回應 JSON 翻回 `ModelResponse`。兩者都不碰網路，網路由注入的 **transport**（傳輸層，一個「送出請求、拿回狀態碼與 JSON」的函式）負責。這樣切的好處是 build 與 parse 都可以用 golden test 離線測試，transport 則可以在測試時換成假的。

```text
 統一格式                       Adapter（provider A）                     Provider A
 ─────────                      ─────────────────────                     ──────────
 messages[user, assistant,  ──► build()
   tool, ...]                     ├─ system 放到頂層
 tools[{name, parameters}]        ├─ tool 訊息合併成 user 的 tool_result
 effort="high"                    ├─ 同一家的 assistant：raw 原樣送回
                                  ├─ 別家的 assistant：只用 text＋tool_calls 重建
                                  └─ effort → 這一家的推理參數 ─────────► HTTP 請求
                                                                              │
 ModelResponse             ◄──── parse()                          ◄──── 200 JSON
   text、tool_calls               ├─ tool_use 區塊 → ToolCall
   stop_reason（統一值）           ├─ stop_reason 對應；不認得就丟例外
   usage（互斥的桶）               ├─ usage 正規化
   raw{provider, items}           └─ 整包內容區塊存進 raw
                           ◄──── classify()                       ◄──── 4xx／5xx
   ModelError(kind, ...)          狀態碼＋error type → kind
```

這張資料流圖左邊是統一格式，右邊是 provider，中間是 adapter 的三個函式。請求方向（上半部）有兩個關鍵分支：同一家產生的 assistant 訊息，直接用 `raw` 裡保存的原始區塊送回，thinking 與簽章一個位元組都不改；別家產生的 assistant 訊息，則只能用統一格式中的文字與 tool call 重建，對方的不透明欄位必須丟掉，因為它們對這一家沒有意義，甚至會讓請求被拒。回應方向（下半部）有兩條路：成功的 200 回應經過 parse 變成 `ModelResponse`，失敗的狀態碼經過 classify 變成 `ModelError`，上層永遠不會看到 provider 的原始例外。

### Usage 正規化成互斥的桶

`loom` v0.5 的 usage 統一成四個**互斥**的桶：`input_tokens`（未命中快取、付全價的輸入）、`cache_read_tokens`（從快取讀出）、`cache_write_tokens`（寫入快取）、`output_tokens`（所有輸出，含 thinking）。「互斥」的意思是同一個 token 只會出現在一個桶裡，所以總輸入就是前三者相加，成本就是每個桶乘上各自的單價再相加，不需要知道它來自哪一家。另外可以附帶資訊性的 `reasoning_tokens`，它是 `output_tokens` 的子集，只用於分析，不能再加進成本。第 4 章 v0.1 的預算只加總 `input_tokens` 和 `output_tokens`；v0.5 的預算改成加總四個桶，才不會在快取命中率高的時候嚴重低估實際處理的 token 量。第 23 章 core 的 `RunContext.usage` 與第 24 章 runtime 的用量累計都直接採用這四個欄位。

下面的程式用兩份假的 provider 回應（形狀依各家公開文件簡化），分別寫出兩家的 parse，並示範「第一輪由 items 形態的 provider 回答、之後 fallback 到 messages 形態的 provider」時，歷史要怎麼轉換。

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
    stop_reason: str = "end_turn"          # end_turn｜tool_use｜max_tokens｜refusal（v0.5 新增）
    usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    raw: dict[str, Any] = field(default_factory=dict)   # {"provider": ..., "items": [...]}：不透明欄位原樣保留


# ── 兩家假 provider 的回應（形狀依各家公開文件簡化；數字是假的）──
MESSAGES_STYLE = {   # Anthropic Messages 式：content blocks、stop_reason、cache 另列且不含在 input_tokens
    "stop_reason": "tool_use",
    "content": [{"type": "thinking", "thinking": "", "signature": "sig-77"},
                {"type": "tool_use", "id": "toolu_9", "name": "get_order", "input": {"order_id": "B-1042"}}],
    "usage": {"input_tokens": 220, "cache_read_input_tokens": 3000,
              "cache_creation_input_tokens": 0, "output_tokens": 140},
}
ITEMS_STYLE = {      # OpenAI Responses 式：output items、status、cached 與 reasoning 是「子集」
    "status": "completed",
    "output": [{"type": "reasoning", "encrypted_content": "enc-55"},
               {"type": "function_call", "call_id": "call_9", "name": "get_order",
                "arguments": "{\"order_id\": \"B-1042\"}"}],
    "usage": {"input_tokens": 3220, "input_tokens_details": {"cached_tokens": 3000},
              "output_tokens": 140, "output_tokens_details": {"reasoning_tokens": 95}},
}


STOP_MAP = {"end_turn": "end_turn", "tool_use": "tool_use", "max_tokens": "max_tokens", "refusal": "refusal"}


def parse_messages_style(r: dict) -> ModelResponse:
    calls = [ToolCall(b["id"], b["name"], b["input"]) for b in r["content"] if b["type"] == "tool_use"]
    text = "".join(b["text"] for b in r["content"] if b["type"] == "text")
    u = r["usage"]
    usage = {"input_tokens": u["input_tokens"],                       # 已經只是「未命中快取」的部分
             "cache_read_tokens": u.get("cache_read_input_tokens", 0),
             "cache_write_tokens": u.get("cache_creation_input_tokens", 0),
             "output_tokens": u["output_tokens"]}                     # 含 thinking
    stop = STOP_MAP.get(r["stop_reason"])
    if stop is None:                                                  # 不認得的值要大聲失敗，不能默默當成 end_turn
        raise ValueError(f"未知的 stop_reason：{r['stop_reason']}")
    return ModelResponse(text, calls, stop, usage, {"provider": "messages", "items": r["content"]})


def parse_items_style(r: dict) -> ModelResponse:
    out = r["output"]
    calls = []
    for i in out:
        if i["type"] == "function_call":
            calls.append(ToolCall(i["call_id"], i["name"], json.loads(i["arguments"])))  # 字串要自己解析
    text = "".join(c["text"] for i in out if i["type"] == "message" for c in i["content"])
    u = r["usage"]
    cached = u.get("input_tokens_details", {}).get("cached_tokens", 0)
    usage = {"input_tokens": u["input_tokens"] - cached,              # 扣掉子集，避免 cache 被算兩次
             "cache_read_tokens": cached, "cache_write_tokens": 0,
             "output_tokens": u["output_tokens"],
             "reasoning_tokens": u.get("output_tokens_details", {}).get("reasoning_tokens", 0)}
    if r["status"] == "incomplete":
        stop = "max_tokens"
    elif r["status"] == "completed":
        stop = "tool_use" if calls else "end_turn"                    # 沒有 stop_reason，要自己推導
    else:                                                             # 不認得的 status 同樣大聲失敗
        raise ValueError(f"未知的 status：{r['status']}")
    return ModelResponse(text, calls, stop, usage, {"provider": "items", "items": out})


def to_messages_style(history: list[dict]) -> list[dict]:
    """統一格式 → Messages 式。同一家的 assistant 訊息原樣送回 raw；別家的只能重建，不透明欄位丟掉。"""
    out: list[dict] = []
    for m in history:
        if m["role"] == "assistant":
            raw = m.get("raw", {})
            if raw.get("provider") == "messages":
                blocks = raw["items"]                                  # thinking 與簽章原樣送回
            else:
                blocks = ([{"type": "text", "text": m["content"]}] if m["content"] else []) + [
                    {"type": "tool_use", "id": c["id"], "name": c["name"], "input": c["args"]}
                    for c in m["tool_calls"]]
            out.append({"role": "assistant", "content": blocks})
        elif m["role"] == "tool":
            block = {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]}
            if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                out[-1]["content"].append(block)                       # 平行呼叫的結果併成同一則 user 訊息
            else:
                out.append({"role": "user", "content": [block]})
        else:
            out.append({"role": m["role"], "content": m["content"]})
    return out


a, b = parse_messages_style(MESSAGES_STYLE), parse_items_style(ITEMS_STYLE)
for name, r in (("messages 式", a), ("items 式", b)):
    print(f"{name:<10} stop={r.stop_reason} call={r.tool_calls[0].name}{r.tool_calls[0].args} usage={r.usage}")

# 一段對話：第一輪由 items 式 provider 回答，之後 fallback 到 messages 式 provider
history = [
    {"role": "user", "content": "B-1042 到哪了？"},
    {"role": "assistant", "content": "", "raw": b.raw,
     "tool_calls": [{"id": c.id, "name": c.name, "args": c.args} for c in b.tool_calls]},
    {"role": "tool", "tool_call_id": "call_9", "name": "get_order", "content": "{\"status\": \"shipped\"}"},
]
req = to_messages_style(history)
print(json.dumps(req[1:], ensure_ascii=False))
assert a.tool_calls[0].args == b.tool_calls[0].args
assert a.usage["input_tokens"] + a.usage["cache_read_tokens"] == b.usage["input_tokens"] + b.usage["cache_read_tokens"]
assert "encrypted_content" not in json.dumps(req)                     # 別家的不透明欄位不能跨 provider 送
assert req[2]["content"][0]["tool_use_id"] == "call_9"
try:
    parse_messages_style({**MESSAGES_STYLE, "stop_reason": "pause_turn"})
except ValueError as exc:
    print("新的 stop_reason：", exc)
```

```text
messages 式 stop=tool_use call=get_order{'order_id': 'B-1042'} usage={'input_tokens': 220, 'cache_read_tokens': 3000, 'cache_write_tokens': 0, 'output_tokens': 140}
items 式    stop=tool_use call=get_order{'order_id': 'B-1042'} usage={'input_tokens': 220, 'cache_read_tokens': 3000, 'cache_write_tokens': 0, 'output_tokens': 140, 'reasoning_tokens': 95}
[{"role": "assistant", "content": [{"type": "tool_use", "id": "call_9", "name": "get_order", "input": {"order_id": "B-1042"}}]}, {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "call_9", "content": "{\"status\": \"shipped\"}"}]}]
新的 stop_reason： 未知的 stop_reason：pause_turn
```

輸出第一、二行是兩家回應正規化後的結果。兩家的 tool call 完全相同，`usage` 的四個桶也相同：未快取輸入 220、快取讀 3,000、輸出 140。但回頭看原始 JSON，messages 形態的 `input_tokens` 是 220，items 形態卻是 3,220，因為後者的 `input_tokens` 包含快取命中的 3,000。`parse_items_style` 先把子集扣掉，兩家的帳才對得起來；第一個 assert 鎖住這件事；資訊性的 `reasoning_tokens=95` 已包含在 140 個輸出裡，不能再加一次。

第三行是轉換後送給 messages 形態 provider 的歷史。assistant 訊息只剩一個 `tool_use` 區塊，`id` 沿用原本的 `call_9`，對應的 `tool_result` 放在下一則 user 訊息裡；原本 items 形態的加密 reasoning（`enc-55`）沒有出現，第二個 assert 確認了這點。換句話說，換家之後，新模型看得到「之前呼叫過什麼、得到什麼結果」，但看不到前一個模型的推理過程，這是跨 provider fallback 必須接受的資訊損失。最後一行示範「不認得的停止原因」：假回應的 `stop_reason` 改成 `pause_turn`，parse 拒絕把它當成 `end_turn`，而是丟出例外，逼開發者明確決定這個新值該怎麼處理。

> [!warning] 常見誤解
> 「tool call 的 id 是 provider 產生的，換家時要重新編號。」通常不需要。id 只要在同一段歷史內唯一且前後一致即可，assistant 訊息與 tool 結果裡的 id 是 client 送出的內容。重新編號反而要同時改兩處，一處漏改就違反第 4 章的配對規則。唯一的例外是對方 API 對 id 的字元或長度有限制時，adapter 要做一個可逆的對應表，而不是隨手產生新 id。

### 能力宣告：ModelSpec

adapter 還要回答一個問題：這個模型**能做什麼**。router 與 fallback chain 在挑模型之前，必須知道它支不支援 tools、平行呼叫、structured outputs、圖片輸入，context window 多大、輸出上限多少、部署在哪些區域、價格多少。這些資訊放在一個 **ModelSpec**（模型規格）資料結構裡，由設定檔載入、版本化管理，而不是散落在程式碼的 if 判斷中。例如歐盟租戶的請求只能送到 `regions` 包含 `eu` 的模型，這條規則由 router 依 ModelSpec 過濾，而不是靠 prompt 提醒模型。ModelSpec 也是第 3 章「model card 怎麼讀」的落地：讀完 model card，把需要的欄位填進 ModelSpec，系統才真正用得上。

### 串流事件的正規化

第 4 章 4.8 節示範過把串流事件組裝成完整的 `ModelResponse`，第 24 章的 runtime 則把它推給前端。在 adapter 層，串流的工作是把各家不同名稱的事件，翻成 `loom` 的少數幾種統一事件。

```text
 provider A 的事件               provider B 的事件                   loom 統一事件
 ────────────────                ────────────────                    ────────────
 content_block_start(text)       output_item.added(message)    ──►   （開新文字段）
 content_block_delta(text)       output_text.delta             ──►   text_delta
 content_block_start(tool_use)   output_item.added(function)   ──►   tool_start{id, name}
 content_block_delta(json)       function_call_arguments.delta ──►   args_delta
 content_block_start(thinking)   reasoning 相關事件            ──►   （只累積到 raw，不顯示）
 message_delta(stop_reason)      response.completed／incomplete ──►  stop{stop_reason, usage}
 連線中斷、錯誤事件              連線中斷、錯誤事件            ──►   error（ModelError）
```

這張對照圖左兩欄是兩家的串流事件（名稱依公開文件簡寫，細節以官方文件為準），右欄是 `loom` 的統一事件。重點有三個。第一，thinking 或 reasoning 的串流內容只累積進 `raw`，不轉成 `text_delta`，否則使用者會看到模型的內部推理，也會在下一輪被當成一般文字重送。第二，usage 通常在串流的最後一個事件才完整，帳本必須等 `stop` 事件才記帳；串流中途斷線時，供應商可能已經計費，但你拿不到 usage，這種情況要記一筆「用量未知」並用請求大小估算，而不是當成零。第三，串流中途的錯誤也要經過 classify 變成 `ModelError`，fallback chain 才能用同一套規則判斷要不要換家；但如果已經有文字顯示在使用者面前，換家等於重新產生，UI 要明確標示（第 4 章 4.8 節）。

## 25.5 錯誤分類：該重試、該換家，還是該停下

### 三個獨立的問題

第 4 章把錯誤分成「模型能修」與「模型修不好」兩類，那是 tool 層的分類。模型 API 本身的錯誤要用另一組問題來分：**同一家重試有沒有用？換一家有沒有用？這次失敗代不代表 provider 壞了？**三個問題的答案彼此獨立。例如 429 速率限制，重試有用（等一下就好），換家也有用，但它不代表 provider 壞了，只代表我們送太快；400「tool 定義格式錯誤」則三個答案都是否：重試一百次結果一樣，換家很可能也錯（或更糟，把 bug 藏起來），也不是 provider 的問題。

```text
 模型 API 回傳錯誤
   │
   ├─ 429 ─┬─ 額度用完（quota）───────────► 重試✗  換家✓  熔斷✗   告警：帳務或配額
   │       └─ 速率限制（rate_limit）──────► 重試✓（照 retry-after） 換家✓  熔斷✗
   │
   ├─ 過載（503、529、overloaded）────────► 重試✓（退避＋jitter） 換家✓  熔斷✓
   ├─ 其他 5xx、逾時、連線中斷 ───────────► 重試✓  換家✓  熔斷✓
   │
   ├─ 401／403（金鑰、權限）──────────────► 重試✗  換家✓  熔斷✗   告警：設定錯誤
   │
   ├─ 400 ─┬─ context 太長 ───────────────► 重試✗  換家✗（除非對方視窗更大）
   │       │                                → 交給 compaction（第 10 章）
   │       └─ 其他格式錯誤 ───────────────► 重試✗  換家✗  熔斷✗   我們的 bug：快速失敗
   │
   └─ 不是錯誤：refusal（拒答）──────────► 不重試、不換家；照產品政策回覆或轉真人
```

這張決策樹由上往下讀，每個葉子都回答三個問題。429 要再分兩種：速率限制要照回應中的 `retry-after` 等待，等待期間這個 provider 也不該再收新請求；額度用完則重試毫無意義，只能換家並立刻通知負責帳務的人。過載與其他 5xx 是熔斷器要計數的對象，因為它們代表 provider 端出了問題。401／403 換家通常有用（只是這一家的金鑰壞了），但它是設定錯誤，要告警而不是默默地永遠走備援。400 的兩種情況都不該換家：context 太長是我們送太多，該交給 compaction；格式錯誤是我們的 bug，換家只會把 bug 藏起來，直到備援也撐不住。

最下面一列特別重要：**拒答不是錯誤**。模型因安全政策拒絕回答時，換到另一家「試試看會不會答」，等於用工程手段繞過安全機制；這不只是 Maya 會擋下的設計，也可能違反供應商的使用政策。正確做法是把 `refusal` 當成一種停止原因，交給產品層依政策處理：回覆使用者「這個問題我無法協助」，或轉給真人。

| kind | 典型來源 | 同一家重試 | 換下一個候選 | 計入熔斷 | 誰要被通知 |
|---|---|---|---|---|---|
| `rate_limit` | 429 速率限制 | 是，照 `retry-after` | 是 | 否（另設等待期） | 容量規劃（長期偏高時） |
| `quota` | 429 額度用盡 | 否 | 是 | 否 | 帳務、平台負責人 |
| `overloaded` | 503、529 | 是，退避＋jitter | 是 | 是 | on-call（持續時） |
| `server`／`network` | 其他 5xx、逾時、斷線 | 是，有限次數 | 是 | 是 | on-call（持續時） |
| `auth` | 401、403 | 否 | 是 | 否 | 立即告警 |
| `context_overflow` | 400 prompt 太長、413 | 否 | 只換到更大視窗的模型 | 否 | 開發者（compaction 門檻） |
| `invalid_request` | 400 其他 | 否 | 否 | 否 | 開發者（這是 bug） |

這張表就是 `ModelError` 的三個屬性 `retryable`、`fallback_ok`、`counts_for_breaker` 的規格。最右欄常被忽略：每一類錯誤都對應一個應該知道它發生的人。備援讓使用者感覺不到故障，這是好事，但也意味著沒有人會主動發現「我們已經在備援上跑了三天」。所以 fallback 發生時一定要留下指標與 trace 標記（第 29 章），持續偏高就告警。

### 重試放在哪一層

模型 API 的重試與退避是第 24 章 runtime 的責任，這裡只補充一個 model 層特有的陷阱：**多層重試相乘**。官方 SDK 通常內建自動重試，HTTP 客戶端可能也有，gateway 可能還有一層，再加上自己的 runtime。四層各自最多嘗試三次（一次加上兩次重試），最壞情況是一次請求變成 3 × 3 × 3 × 3 ＝ 81 次，正是雙 11 晚上把過載的供應商打得更慢的原因之一。原則是只留一層：把 SDK 的內建重試關掉，由 runtime 依 `ModelError` 的分類統一決定，並設定**重試預算**（retry budget，例如重試請求不得超過總請求的一成），讓整個系統在故障時的額外負載有上限。

下面是接真實 SDK 時 transport 的樣子。依 2026-10 的 SDK 介面撰寫，請以官方文件為準；`classify` 與 `ModelError` 是本節的分類函式與錯誤類別，`loom` 的 adapter 只看得到它們，看不到 SDK 的例外型別。

```python
# not-runnable
import anthropic
import openai


class AnthropicTransport:
    def __init__(self) -> None:
        # SDK 內建重試關掉：重試由 loom runtime 依 ModelError 統一決定，避免多層相乘
        self.client = anthropic.Anthropic(max_retries=0, timeout=60.0)

    def send(self, req: dict) -> dict:
        try:
            return self.client.messages.create(**req).model_dump()
        except anthropic.APIStatusError as exc:
            body = exc.body if isinstance(exc.body, dict) else {}
            raise classify("anthropic", exc.status_code, body, dict(exc.response.headers))
        except anthropic.APIConnectionError:          # 含逾時
            raise ModelError("network", "anthropic")


class OpenAITransport:
    def __init__(self) -> None:
        self.client = openai.OpenAI(max_retries=0, timeout=60.0)

    def send(self, req: dict) -> dict:
        try:
            return self.client.responses.create(**req).model_dump()
        except openai.APIStatusError as exc:
            body = exc.body if isinstance(exc.body, dict) else {}
            body = body if "error" in body else {"error": body}   # 兩種 body 形狀都接受
            raise classify("openai", exc.status_code, body, dict(exc.response.headers))
        except openai.APIConnectionError:
            raise ModelError("network", "openai")
```

這段程式的重點不在 SDK 的細節，而在邊界：transport 是整個 `loom` 唯一 import 供應商 SDK 的地方，所有例外在這裡就被翻成 `ModelError`。兩個 client 都設定 `max_retries=0`，把重試權收回到 runtime。錯誤 body 的形狀在不同 SDK 間可能不同，所以先做一次正規化再交給 `classify`；這種「防禦性正規化」正是 adapter 層該吸收的雜訊。

## 25.6 熔斷器：別再敲一扇壞掉的門

### 為什麼重試與 fallback 還不夠

假設主力 provider 已經完全過載，每個請求要等 30 秒逾時才失敗，再換到備援。fallback 確實讓使用者最後拿到了答案，但每個人都先白等了 30 秒；而且所有 session 仍然持續把請求送進那個已經過載的 provider，讓它更難恢復。**熔斷器**（circuit breaker）解決的就是這個問題：它記錄每個下游最近的成功與失敗，當失敗多到某個程度，就「跳脫」成打開狀態，接下來一段時間內的請求直接跳過這個下游，不送、不等；冷卻時間過後，放少量探測請求過去，成功了才恢復正常。這個模式來自分散式系統，Michael Nygard 在《Release It!》中把它整理成穩定性模式的經典之一。

```text
                    失敗率 ≥ 門檻（且樣本數 ≥ 最小值）
        ┌──────────┐ ─────────────────────────────────► ┌──────────┐
        │  closed  │                                    │   open   │
        │ 正常送出 │ ◄───────┐                          │ 直接跳過 │
        │ 記錄結果 │         │                          │ 不送不等 │
        └──────────┘         │                          └──────────┘
             ▲               │ 探測成功                      │ 冷卻時間到
             │               │                               ▼
             │           ┌───────────┐                       │
             └───────────│ half_open │ ◄─────────────────────┘
               清空紀錄  │ 只放一個  │
                         │ 探測請求  │ ── 探測失敗 ──► 回到 open，重新計時
                         └───────────┘

 只有 overloaded、server、network 計入失敗；429 另設「等到 retry-after」的封鎖期
```

這張狀態機有三個狀態。**closed**（閉合，電路接通）是正常狀態：請求照常送出，每次結果記進一個滑動視窗。當視窗內的失敗率超過門檻，而且樣本數夠多（避免第一次失敗就跳脫），轉成 **open**（打開，電路斷開）：所有請求直接被拒絕，fallback chain 會立刻改走下一個候選，不必等逾時。冷卻時間到了，轉成 **half_open**（半開）：只放一個探測請求過去，成功就回到 closed 並清空紀錄，失敗就回到 open 重新計時。圖底下那行說明哪些錯誤算數：只有代表「provider 壞了」的錯誤才計入，400 與 401 是我們自己的問題，計入的話會讓一個 bug 把健康的 provider 熔斷掉。

### 設計熔斷器時的幾個選擇

第一是**鍵的粒度**：一個熔斷器保護的是一整家 provider、一個模型，還是一個「provider＋模型＋區域」？粒度太粗，某個小模型過載會連帶把同一家的大模型也跳過；粒度太細，每個熔斷器樣本數太少，判斷不穩。常見的折衷是以「provider＋區域」為主，對流量大的模型再單獨設一個。第二是**失敗的定義**：除了錯誤，**慢**也是一種失敗。如果主力 provider 沒有報錯，但 p95 延遲從 3 秒變成 25 秒，同步客服一樣無法使用，所以可以把超過延遲門檻的呼叫也記為失敗。第三是**分散式狀態**：多個 worker 各自維護熔斷器，每台都要自己踩幾次失敗才會跳脫；共享狀態（例如放在 Redis）反應較快，但多了一個依賴。對多數團隊來說，每個 process 一個熔斷器已經能擋掉大部分的傷害。

下面的程式實作 25.5 節的錯誤分類與失敗率熔斷器，並用模擬時鐘重演雙 11：provider A 在第 10 到 60 秒之間過載，請求每 2 秒一個。

```python
from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class ModelError(Exception):
    kind: str            # rate_limit｜quota｜overloaded｜server｜network｜auth｜context_overflow｜invalid_request
    provider: str
    status: int = 0
    retry_after: float = 0.0

    # 三個獨立的問題：同一家重試有沒有用？換一家有沒有用？要不要算進熔斷？
    @property
    def retryable(self) -> bool:
        return self.kind in {"rate_limit", "overloaded", "server", "network"}

    @property
    def fallback_ok(self) -> bool:
        return self.kind in {"rate_limit", "quota", "overloaded", "server", "network", "auth"}

    @property
    def counts_for_breaker(self) -> bool:
        return self.kind in {"overloaded", "server", "network"}


def classify(provider: str, status: int, body: dict, headers: dict) -> ModelError:
    """把 HTTP 狀態碼與錯誤內容翻成 loom 的錯誤種類。各家的 type 字串不同，規則集中在這裡。"""
    etype = body.get("error", {}).get("type", "")
    msg = body.get("error", {}).get("message", "")
    if status == 429:
        kind = "quota" if etype == "insufficient_quota" else "rate_limit"   # 額度用完：重試沒用
    elif status in (529, 503) or etype == "overloaded_error":
        kind = "overloaded"
    elif status >= 500:
        kind = "server"
    elif status in (401, 403):
        kind = "auth"
    elif status in (400, 413) and ("context" in msg or "too long" in msg or status == 413):
        kind = "context_overflow"
    else:
        kind = "invalid_request"                                            # 多半是我們自己的 bug
    return ModelError(kind, provider, status, float(headers.get("retry-after", 0)))


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0


class CircuitBreaker:
    """失敗率熔斷：最近 window 次呼叫中，失敗比例 >= threshold 就打開 cooldown 秒。"""

    def __init__(self, clock: FakeClock, window: int = 8, min_calls: int = 4,
                 threshold: float = 0.5, cooldown: float = 30.0) -> None:
        self.clock, self.window, self.min_calls = clock, window, min_calls
        self.threshold, self.cooldown = threshold, cooldown
        self.state, self.opened_at, self.blocked_until = "closed", 0.0, 0.0
        self.results: deque[bool] = deque(maxlen=window)
        self.log: list[str] = []

    def allow(self) -> bool:
        now = self.clock.now
        if now < self.blocked_until:                     # 429 的 retry-after：不算故障，但這段時間不送
            return False
        if self.state == "open" and now - self.opened_at >= self.cooldown:
            self._move("half_open")                      # 冷卻結束：放一個探測請求過去
            return True
        return self.state != "open"

    def record(self, ok: bool, err: ModelError | None = None) -> None:
        if err is not None and err.kind == "rate_limit":
            self.blocked_until = self.clock.now + err.retry_after
            return
        if err is not None and not err.counts_for_breaker:
            return                                       # 400、401 這類錯誤不代表 provider 壞了
        if self.state == "half_open":
            self._move("closed" if ok else "open")
            return
        self.results.append(ok)
        fails = self.results.count(False)
        if len(self.results) >= self.min_calls and fails / len(self.results) >= self.threshold:
            self._move("open")

    def _move(self, state: str) -> None:
        self.log.append(f"t={self.clock.now:>4.0f}s  {self.state:>9} → {state}")
        self.state = state
        if state == "open":
            self.opened_at = self.clock.now
        if state == "closed":
            self.results.clear()


# 1) 錯誤分類
cases = [(429, {"error": {"type": "rate_limit_error"}}, {"retry-after": "12"}),
         (429, {"error": {"type": "insufficient_quota"}}, {}),
         (529, {"error": {"type": "overloaded_error"}}, {}),
         (400, {"error": {"type": "invalid_request_error", "message": "prompt is too long"}}, {}),
         (400, {"error": {"type": "invalid_request_error", "message": "tools.0.name: invalid"}}, {}),
         (401, {"error": {"type": "authentication_error"}}, {})]
for status, body, headers in cases:
    e = classify("A", status, body, headers)
    print(f"{status} {e.kind:<16} 重試={e.retryable!s:<5} 換家={e.fallback_ok!s:<5} 熔斷={e.counts_for_breaker}")

# 2) 熔斷器：provider A 從 t=10s 開始過載，t=60s 恢復
clock = FakeClock()
cb = CircuitBreaker(clock)
sent = skipped = 0
for t in range(0, 100, 2):
    clock.now = float(t)
    if not cb.allow():
        skipped += 1
        continue
    sent += 1
    if 10 <= t < 60:
        cb.record(False, classify("A", 529, {}, {}))
    else:
        cb.record(True)
print("\n".join(cb.log))
print(f"送出 {sent} 次，熔斷期間直接跳過 {skipped} 次")
assert [line.split("→ ")[1] for line in cb.log] == ["open", "half_open", "open", "half_open", "closed"]
assert cb.state == "closed"
```

```text
429 rate_limit       重試=True  換家=True  熔斷=False
429 quota            重試=False 換家=True  熔斷=False
529 overloaded       重試=True  換家=True  熔斷=True
400 context_overflow 重試=False 換家=False 熔斷=False
400 invalid_request  重試=False 換家=False 熔斷=False
401 auth             重試=False 換家=True  熔斷=False
t=  16s     closed → open
t=  46s       open → half_open
t=  46s  half_open → open
t=  76s       open → half_open
t=  76s  half_open → closed
送出 22 次，熔斷期間直接跳過 28 次
```

前六行是錯誤分類的結果，和 25.5 節的表一一對應：兩種 429 分別變成 `rate_limit` 與 `quota`，前者可以重試，後者不行；529 是唯一「計入熔斷」的；兩種 400 依錯誤訊息分成 `context_overflow` 與 `invalid_request`，都既不重試也不換家；401 可以換家，但不計入熔斷。

接下來五行是熔斷器的狀態變化。t=10 秒開始失敗，到 t=16 秒，視窗內 8 次呼叫有 4 次失敗，失敗率達到 50%，熔斷器打開。t=46 秒冷卻 30 秒結束，轉成半開並放一個探測請求，但 provider 還在過載，探測失敗，立刻回到 open。t=76 秒第二次探測時 provider 已經恢復，探測成功，熔斷器閉合。最後一行是效果：100 秒內本來要送 50 次，熔斷器讓其中 28 次直接跳過，那 28 次在真實系統中會立刻走 fallback，而不是先等一次逾時；provider A 也少收了 28 次請求，恢復得更快。注意 t=60 到 76 秒之間 provider 其實已經恢復，但熔斷器還在冷卻，這段時間的流量會繼續走備援。冷卻時間越長，越能保護下游，但「已經恢復卻沒用上」的時間也越長，這是熔斷器最基本的取捨。

## 25.7 Fallback chain：換模型不是換一個字串

### 換家時會壞掉的五件事

fallback chain（備援鏈）是一個依序嘗試的候選模型清單：第一個失敗而且錯誤屬於「換家有用」時，就換下一個。概念很簡單，Iris 在雙 11 當下也只花了十分鐘就寫出來，然後立刻撞上 400。原因是換模型從來不只是換一個模型名稱字串，至少有五件事要同時處理。

第一是**歷史轉換**：前面的回合是另一家模型產生的，不透明欄位要丟掉、格式要重建，25.4 節的 `to_messages_style` 就是在做這件事。第二是**能力相容**：備援模型要支援這個請求用到的所有能力，例如 tools、structured outputs、圖片輸入，而且 context window 要放得下目前的歷史；不相容的候選要在挑選時就排除，而不是送出去等它報錯。第三是**政策限制**：資料落地、合約與租戶設定決定了哪些 provider 可以收到這個租戶的資料，這是硬條件，fallback 絕不能為了可用性越過它。第四是**prompt 適配**：同一份 system prompt 在不同模型上的表現可能差很多，備援路徑可能需要自己的 prompt 變體。第五是**成本與延遲的跳升**：備援模型的快取是冷的，第一次呼叫要付全價甚至寫入溢價，TTFT 也較長；如果備援是更貴的模型，整個故障期間的單位成本都會上升。

```text
 Runner          Router            Chain           Breaker A    Adapter A    Adapter B     Ledger
   │ complete(task=reply, tenant=t-tw)│                │            │            │            │
   │───────────────►│                 │                │            │            │            │
   │                │ 過濾：區域、能力、視窗              │            │            │            │
   │                │ 候選 = [a-large, b-large]          │            │            │            │
   │                │────────────────►│ allow?         │            │            │            │
   │                │                 │───────────────►│ closed     │            │            │
   │                │                 │──────────── complete ──────►│            │            │
   │                │                 │◄─────────── ModelError(overloaded) ──────│            │
   │                │                 │ record(✗) ────►│ 失敗率 50% → open       │            │
   │                │                 │ fallback_ok → 下一個候選     │            │            │
   │                │                 │──────────────────────── complete（歷史轉換）──►│      │
   │                │                 │◄─────────────────────── ModelResponse（冷快取）│      │
   │                │                 │ 記錄 fallback 指標 ─────────────────────────────────►│
   │◄───────────────────────────────── ModelResponse（raw 標記 model=b-large）              │
```

這張時序圖追蹤一次發生 fallback 的呼叫。router 先依硬條件過濾，產生兩個候選；chain 問熔斷器 A 能不能送，此時還是 closed，於是送出，得到過載錯誤。chain 把失敗記給熔斷器，這次記錄讓失敗率達到門檻，熔斷器打開；因為錯誤的 `fallback_ok` 為真，chain 改用 adapter B，並在送出前完成歷史轉換。B 成功回應，但快取是冷的；帳本記下這筆較貴的呼叫，並標記為 fallback。最後 runner 拿到的 `ModelResponse` 在 `raw` 中記著實際使用的模型，下一輪要用它決定歷史怎麼送，trace 也要用它追蹤是哪個模型做了這個決定。

### Session 黏著與切換時機

fallback 發生在一個多輪 session 的中途時，下一輪該回到主力模型，還是留在備援模型？每切一次就丟一次快取、丟一次推理連續性，所以多數情況下應該讓 session **黏著**（sticky）在備援上，直到這個 session 結束或遇到自然的切換點；新的 session 才依熔斷器狀態回到主力。最好的切換點是 **compaction**（第 10 章）：compaction 本來就會重寫 context、讓快取失效，在那個時間點換模型幾乎不需要額外代價。Cognition 公開描述的 Devin Fusion 正是把模型切換點選在 compaction 時，以避開額外的快取懲罰。

| 備援策略 | 適用的故障 | 優點 | 代價與風險 |
|---|---|---|---|
| 同模型、另一個區域或端點 | 單一區域過載或中斷 | 行為幾乎相同，prompt 不用改 | 資料落地限制可能不允許；快取仍是冷的 |
| 同一家、較小或較舊的模型 | 某個模型過載 | 格式相同，不透明欄位常可沿用 | 品質下降；provider 整體故障時一起倒 |
| 另一家的同級模型 | provider 整體故障 | 真正的獨立性 | 歷史轉換、prompt 適配、需要獨立 eval |
| 降級模式：排隊、非同步回覆 | 所有候選都不可用 | 不會給出錯誤答案 | 使用者要等；需要通知機制 |
| 轉真人或固定回覆 | 高風險動作、長時間故障 | 最安全 | 人力成本；只適合部分流量 |

這張表由上到下，獨立性越來越高，與原本行為的落差也越來越大。實務上 fallback chain 往往是幾種策略的組合：先換區域，再換同一家的另一個模型，再換另一家，最後進入降級模式。降級模式值得特別設計：對青鳥客服來說，「目前查詢量較大，我們會在 10 分鐘內以訊息回覆您」比一個勉強擠出來的錯誤答案好得多，而且退款這類 destructive 動作在備援路徑上可以直接改成需要人工確認（第 21 章）。

> [!warning] 常見誤解
> 「有 fallback，可用性就是兩家可用性相乘的互補。」這只在兩條路徑真正獨立、而且備援路徑真的能用時成立。很多團隊的備援平常沒有流量，等到故障那天才發現 prompt 不相容、配額太低、金鑰過期。備援路徑要有平時的小流量（例如 1% 的請求固定走備援）、自己的 eval 與配額，否則它只是一個從未測試過的假設。

## 25.8 Model routing：依難度、成本與延遲選模型

### 為什麼要 routing

阿哲的問題直指 routing 的核心：一個 agent 系統裡的模型呼叫，難度分布非常不平均。分類意圖、抽取訂單編號、把長頁面摘要成三行、判斷 tool 結果是否為空，這些步驟的難度和「判斷這筆跨訂單的退款爭議是否符合政策」完全不在同一個量級。全部用前沿模型與高 effort，品質不會比較好，只會比較貴、比較慢。**Model routing**（模型路由）就是在每次呼叫前決定「這一步用哪個模型、哪個 effort」。第 18 章介紹過 routing 作為 workflow pattern 的形式；這一節談它在 model 層的實作，以及它特有的風險：**路由錯了不會報錯，只會讓品質默默下降**。

### 四種路由策略

最簡單也最可靠的是**依任務類別的規則路由**：呼叫端在請求上標記任務類別（`triage`、`reply`、`refund_review`），router 依一張表選模型等級與 effort。它的前提是呼叫端知道自己在做什麼，在 agent 系統中通常成立，因為分類、摘要這類步驟本來就是 harness 程式碼發起的，而不是模型自己決定的。第二種是**分類器路由**：用一個小模型或規則模型先判斷這個請求的難度，再決定送哪裡，適合「同一個入口、難度差異大」的情境，例如使用者訊息直接進來的第一輪。第三種是 **cascade**（串聯升級）：先用便宜的模型做，再用某種訊號判斷結果可不可信，不可信才升級到貴的模型重做。第四種是**主模型＋輔助模型**：一個前沿模型負責主要推理與決策，一個小型快速模型負責大量的輔助工作，例如摘要 tool 輸出、壓縮歷史、跑平行的子任務，兩者各自維持自己的 context。

```text
 請求進來（task、tenant、預估輸入長度、延遲預算）
   │
   ▼
 (1) 硬條件過濾 ─── 區域／合約不允許、能力不足、視窗放不下 ───► 從候選中移除
   │
   ▼
 (2) 任務類別有對應規則？ ── 有 ──► 依規則選等級與 effort（triage → small/low）
   │ 沒有
   ▼
 (3) 分類器估難度 ──► 簡單 → small；困難 → frontier；不確定 → 走 cascade
   │
   ▼
 (4) cascade：small 先做 ──► 驗證通過？ ── 是 ──► 回傳（記錄 route=small）
   │                              │ 否
   │                              ▼
   │                         升級 frontier 重做（記錄 route=escalated，兩次都記帳）
   ▼
 (5) 依熔斷器狀態，把同等級的候選排成 fallback chain ──► 25.7 節
```

這張決策流程圖的順序是刻意的。硬條件永遠在最前面：資料落地、能力與視窗是不能妥協的約束，任何成本或品質的考量都不能越過它。第 (2) 步的規則路由排在分類器之前，因為規則是確定性的、可以審查、不會出錯；只有規則沒涵蓋的請求才交給分類器。第 (3) 步的分類器本身也是一個模型呼叫，它的成本與延遲要算進來，所以分類器必須比它省下的錢便宜很多。第 (4) 步 cascade 的關鍵在「驗證」：升級時前一次的錢已經花掉，所以升級率太高的 cascade 比直接用前沿模型還貴。最後一步把選中的等級交給 fallback chain，路由和備援從此是兩個獨立的關注點：routing 決定「該用多強的模型」，fallback 決定「這個等級裡誰現在能用」。

### Cascade 的關鍵：用什麼判斷要不要升級

cascade 最常見的錯誤，是讓小模型自己說「我有沒有把握」。模型的自我信心和正確率之間的關聯並不可靠，尤其在它能力邊界附近的題目上，答錯時往往同樣自信。比較可靠的升級訊號是**外部驗證**：輸出是否通過 schema 與業務規則檢查、引用的訂單編號是否真的存在、計算出的退款金額是否和訂單資料一致、程式碼是否通過測試。下面用 20 張難度不同的工單模擬四種策略：

```python
from __future__ import annotations

# 20 張客服工單的難度（1 = 查物流，5 = 跨訂單的退款爭議）。分布刻意偏向簡單題，貼近真實流量
DIFFICULTY = [1, 1, 2, 1, 3, 2, 1, 4, 1, 2, 3, 1, 5, 2, 1, 3, 4, 1, 2, 3]
COST = {"small": 1.0, "frontier": 8.0}          # 相對成本：前沿模型一次約等於小模型 8 次


def small(i: int, d: int) -> tuple[bool, float]:
    """回傳 (答對嗎, 模型自稱的信心)。難度 3 的題目有一半答錯，但它照樣很有信心。"""
    correct = d <= 2 or (d == 3 and i % 2 == 0)
    confidence = 0.9 if d <= 3 else 0.4
    return correct, confidence


def frontier(i: int, d: int) -> bool:
    return not (d == 5 and i % 3 == 0)


def verifier(i: int, correct: bool) -> bool:
    """確定性檢查（政策規則、schema、和訂單資料比對）。抓得到大多數錯，但不是全部。"""
    return correct or i % 5 == 0                 # i 為 5 的倍數時漏抓


def run(strategy: str) -> tuple[float, float, float]:
    right = cost = escalated = 0
    for i, d in enumerate(DIFFICULTY):
        if strategy == "全用前沿":
            ok, cost = frontier(i, d), cost + COST["frontier"]
        elif strategy == "全用小模型":
            (ok, _), cost = small(i, d), cost + COST["small"]
        else:
            ok, conf = small(i, d)
            cost += COST["small"]
            need_up = conf < 0.7 if strategy == "cascade：看自信" else not verifier(i, ok)
            if need_up:                           # 升級：前面那次小模型的錢已經花掉了
                escalated += 1
                ok, cost = frontier(i, d), cost + COST["frontier"]
        right += ok
    n = len(DIFFICULTY)
    return right / n, cost / n, escalated / n


results = {}
for s in ("全用前沿", "全用小模型", "cascade：看自信", "cascade：看驗證"):
    results[s] = run(s)
    acc, c, up = results[s]
    print(f"{s}｜正確率 {acc:.0%}｜每題成本 {c:.2f}｜升級率 {up:.0%}")

assert results["cascade：看驗證"][0] > results["cascade：看自信"][0]        # 自信不等於正確
assert results["cascade：看驗證"][1] < results["全用前沿"][1] / 2           # 成本不到一半
```

```text
全用前沿｜正確率 95%｜每題成本 8.00｜升級率 0%
全用小模型｜正確率 75%｜每題成本 1.00｜升級率 0%
cascade：看自信｜正確率 85%｜每題成本 2.20｜升級率 15%
cascade：看驗證｜正確率 90%｜每題成本 2.60｜升級率 20%
```

第一行是基準：全部用前沿模型，正確率 95%，每題成本 8。第二行全部用小模型，成本降到八分之一，但正確率掉到 75%，因為難度 3 以上的題目有一半以上答錯。第三行是「看自信」的 cascade：小模型對難度 4、5 的題目信心低，這些被升級，成本 2.2、正確率 85%；但難度 3 的題目它答錯了也一樣有信心，這兩題完全沒有被升級，品質就這樣默默流失。第四行是「看驗證」的 cascade：確定性的驗證抓到了大部分錯誤（只漏掉一題），升級率 20%，成本 2.6，正確率 90%，用不到三分之一的成本拿到接近前沿模型的品質。

這組數字是刻意構造的，真正要記住的是三個結構性結論。第一，cascade 的品質上限由驗證器決定，驗證器漏抓的錯誤會直接流到使用者面前。第二，升級時要付兩次錢，第四行的成本 2.6 中有 0.4 是「小模型白做」的部分；升級率越高，cascade 越不划算，超過某個比例就應該直接走前沿模型。第三，這張表只有在有 eval 的情況下才算得出來：沒有標註好的工單集合，你根本不會知道「看自信」的策略漏掉了哪些題目。第 27 章的 eval harness 是 router 的前提，不是事後的補充。

### 主模型＋輔助模型，以及路由與快取的衝突

「主模型＋輔助模型」是 coding 與 research agent 最常見的配置：主模型保有完整的 session 與長 context，把明確、可驗證的小工作交給輔助模型，例如第 20 章的唯讀子任務、第 10 章的 compaction 摘要、第 9 章的 tool 輸出摘要。它的好處是主模型的 context 與快取保持穩定，輔助模型的呼叫雖多但便宜且互相獨立。反過來的變體是「小模型主導、遇到難題時諮詢大模型」：執行者是快速模型，只在需要判斷時把問題交給前沿模型給建議，適合大部分步驟都是例行操作的任務。

路由最容易被忽略的成本是**快取**。在同一個 session 裡逐步依難度換模型，每換一次就丟掉一次快取；第 3 章算過，50 步的任務靠快取可以把輸入成本降到約八分之一，頻繁切換會把這個優勢吃光。所以要套用 25.7 節的黏著原則：主線維持同一個模型，輔助工作在獨立 context 裡進行，主模型的切換只發生在 compaction 時。

| 策略 | 決定依據 | 優點 | 風險 | 適用 |
|---|---|---|---|---|
| 規則路由（依任務類別） | 呼叫端標記的 task | 確定、可審查、零額外成本 | 需要呼叫端分類；新任務要記得加規則 | harness 發起的分類、摘要、抽取 |
| 分類器路由 | 小模型或規則估的難度 | 同一入口也能分流 | 分類器本身會錯，且有成本 | 使用者訊息直接進來的第一輪 |
| cascade | 便宜模型的結果是否通過驗證 | 大部分流量用便宜模型 | 升級付兩次錢；驗證器漏抓 | 有確定性驗證的任務 |
| 主模型＋輔助模型 | 工作性質（主線 vs 輔助） | 主線 context 與快取穩定 | 交接的資訊損失 | coding、research 長任務 |
| 依延遲預算 | 剩餘的時間預算 | 保住同步互動的 SLO | 趕時間時品質下降 | 同步客服、語音 |

這張表的最後一列補上了延遲這個維度：同步客服的延遲預算是秒級，如果某一輪前面的 tool 已經花掉大半預算，router 可以為最後的回覆選較快的模型或較低的 effort。不管用哪一種策略，router 的決定都要寫進 trace（route、模型、effort、是否升級），並定期抽樣比較「被路由到小模型的請求」與「如果用前沿模型」的結果，這種 **shadow 比較**（同一請求在背景也跑一次另一條路徑，只比較不回覆）是發現路由品質默默下降的主要手段。

> [!note] 2026 現況
> 截至 2026 年 10 月，多模型路由已是主流 agent 產品的常態（依各家公開文章與原始碼）：Cognition 的 Devin Fusion（2026-06-29）讓前沿主模型與便宜的 sidekick 模型平行運作、各自有持久且快取的 context，由輕量 classifier 在 session 中途決定切換，切換點選在 compaction；公開數據為 FrontierCode 1.1 Extended 上 Fusion 63.1 分、每任務 $1.35，對照 Opus 5 medium 63.6 分、$3.51，Fable 5 xhigh 64.9 分、$10.53。Harvey 自建的 cloud agent runtime 讓「選模型只是一個 routing 決策」，相對只用前沿模型省 3–5 倍。Gemini CLI 的原始碼中有 `routing` 模組，策略包括 classifier、Gemma classifier、numerical classifier、fallback、override 等。Cursor 於 2026-08-06 發表 Cursor Router（本書未讀細節）。Anthropic 的 advisor tool 讓較快的 executor 模型在生成中途諮詢較強的 advisor 模型。框架方面，Google ADK 2.x 提供 `FallbackModel`，OpenAI Agents SDK 可透過 LiteLLM 或自訂 model provider 接其他供應商；LangChain 的 middleware 中有 model fallback（本書未經網路查證）。

## 25.9 成本計量：每一個 token 都要記到帳上

### 為什麼成本要在 model 層記

第 3 章給了成本公式，第 29 章會把成本做成儀表板；這一節談中間那一段：**誰、在什麼時候、用什麼價格把一次呼叫換算成錢**。答案是 model 層，在每次成功回應的當下。理由有三個。第一，只有 model 層同時知道實際使用的模型（可能是 fallback 後的那個）、正規化後的 usage、以及這次呼叫屬於哪個租戶、哪個 agent、哪個任務。第二，價格會變，供應商調價、你換了合約、新模型上線，事後拿月底的價格回推上個月的成本一定會錯，所以成本要在寫入時就用當時的價格算好存下。第三，預算控制需要即時的數字：第 4 章的 token 預算、租戶的每月額度、research agent 的單次任務上限，都要在下一次呼叫前知道已經花了多少。

```text
 ModelResponse.usage（互斥的桶）        ModelSpec + 價格表（版本化）
   input_tokens        220               price_version = demo-2026-10
   cache_read_tokens   3000              input  4.00 /MTok   output 20.00 /MTok
   cache_write_tokens  0                 read_mult 0.1       write_mult 1.25
   output_tokens       140                         │
          │                                        │
          └───────────────► CostLedger.record() ◄──┘
                              │  cost = Σ 桶 × 單價 × 倍數
                              │  附上：tenant、agent、task、route、model、
                              │        fallback?、price_version、trace_id
                              ▼
                       帳本（append-only）
                              │
          ┌───────────────────┼─────────────────────┬──────────────────────┐
          ▼                   ▼                     ▼                      ▼
   即時預算檢查          租戶月額度            每次成功任務成本        對帳（和供應商帳單）
   （第 4、24 章）       （第 36 章）          （第 27、30 章）        （差異 > 門檻就告警）
```

這張資料流圖左上是 25.4 節正規化後的 usage，右上是版本化的價格表。兩者在 `CostLedger.record()` 相遇，算出這次呼叫的成本，並附上所有後續分析需要的維度：租戶、agent、任務類別、路由結果、實際模型、是否發生 fallback、價格表版本與 trace id。帳本是 append-only 的，一筆寫進去就不改；如果價格表事後被更正，就寫一筆調整紀錄，而不是改寫歷史。下方四個消費者各有不同的時間尺度：預算檢查是每次呼叫前，租戶額度是每天或每月，每次成功任務成本是每週的評估與優化，對帳則是每月和供應商的實際帳單比對，差異過大代表 usage 正規化或價格表有錯。

### 帳本要記哪些欄位

| 帳本欄位 | 來源 | 用途 | 常見錯誤 |
|---|---|---|---|
| `input_tokens`、`cache_read_tokens`、`cache_write_tokens`、`output_tokens` | adapter 正規化的 usage | 依各自單價計費 | 把含快取的 input 當未快取，重複計算 |
| `reasoning_tokens`（資訊性） | 部分 provider 的明細 | 分析 effort 的效果 | 再加進成本，算了兩次 |
| `model`、`provider`、`region` | chain 實際使用的 adapter | 依模型分攤、比較 fallback 成本 | 記成「請求的模型」而不是實際模型 |
| `price_version` | 價格表 | 事後重算與稽核 | 只存 token，月底用新價格回推 |
| `tenant`、`agent`、`task`、`route` | 呼叫端與 router | 租戶計費、路由效益分析 | 缺租戶維度，無法做多租戶分攤 |
| `fallback`、`escalated` | chain 與 cascade | 算出故障與升級的額外成本 | 升級時只記第二次，低估 cascade 成本 |
| `ok`（任務是否成功） | 任務結束時由 eval 或結果回填 | 每次成功任務成本 | 用「呼叫成功」代替「任務成功」 |
| `trace_id` | runtime | 從帳本跳到 trace 除錯 | 帳本與 trace 對不起來 |

這張表的最後兩列最常被做錯。`ok` 指的是**任務**是否成功，不是 API 呼叫是否回 200；它通常在任務結束時才知道（使用者是否滿意、退款是否正確完成、eval 是否通過），所以帳本要能在事後把同一個任務的所有呼叫標上結果。第 3 章說過，真正該拿來做決策的是「每次成功任務成本」：一個單次便宜三成、但成功率從九成掉到六成的路由，換算後反而更貴。`trace_id` 則讓「這個租戶這週的成本為什麼翻倍」這種問題，可以從帳本一路追到具體的 trajectory（第 29 章）。

### 預算控制：事前估算與事後記帳

帳本記的是已經發生的成本；預算控制還需要**事前估算**：送出前用輸入長度乘上單價，加上輸出上限乘上輸出單價，就是這次呼叫的最大可能成本。「已花費＋最大可能成本」超過預算時，就拒絕這次呼叫，或改用較便宜的模型、較低的 effort、較小的輸出上限，這就是第 4 章所說的硬上限。搜尋 API、sandbox 秒數、embedding 這些 model 層之外的成本，也要用同一個帳本與維度記錄。

> [!note] 2026 現況
> 截至 2026 年 10 月，Anthropic API 價格（每百萬 token 的 input／output）為 Fable 5.1 $10／$50、Opus 5.5 $4／$20、Sonnet 5.5 $2／$10、Haiku 4.5 $1／$5；cache read 一般為 base input 的 0.1 倍，但 Opus 5.5 為 0.05 倍、Fable 5.1 為 0.025 倍；cache write 的倍數（常見說法是 5 分鐘 TTL 為 1.25 倍、1 小時 TTL 為 2 倍）與 fast mode 的計價，本書未經網路查證，請以官方價目表為準。Anthropic 另有「Task budgets」，可以給整個 agentic loop 一個建議性的 token 預算讓模型自我調節（本書未讀細節）。OpenTelemetry GenAI semantic conventions 定義了 `gen_ai.usage.input_tokens`、`gen_ai.usage.output_tokens` 以及 cache read／write 等屬性，帳本欄位可以對齊這些名稱，方便和 tracing 平台整合（第 29 章）。價格變動頻繁，以上只作為填寫價格表時的參照。

## 25.10 動手做：loom.models

這一節把本章的五個元件組成 `loom.models`，並用兩家假 provider 重演雙 11。程式分成兩半：上半是 `loom.models` 本體，包括 `ModelError` 與分類、`ModelSpec`、熔斷器、兩個 adapter、`FallbackChain`、`Router` 與 `CostLedger`；下半是假的 provider 後端與情境。假後端用模擬時鐘控制時間，每次呼叫花 2 秒；provider A 在第 8 到 30 秒之間回傳 529 過載；兩家各自維護 prompt cache，同一個模型第一次被呼叫時是冷的，之後才命中。

情境設定如下：青鳥有四個模型，A、B 兩家各有一個前沿模型與一個小模型，A 只部署在台灣區域，B 在台灣與歐盟都有。任務有三類：`triage`（意圖分類，小模型、低 effort）、`reply`（客服回覆，前沿模型、中 effort）、`refund_review`（退款審查，前沿模型、高 effort）。每 4 秒進來一個任務，其中一個來自歐盟租戶 `t-eu`，它的資料只能送到歐盟區域。為了把焦點放在 model 層，假 provider 一律回覆一段短文字，不呼叫 tool。

```python
from __future__ import annotations

import json
from collections import defaultdict, deque
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
    stop_reason: str = "end_turn"          # end_turn｜tool_use｜max_tokens｜refusal
    usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    raw: dict[str, Any] = field(default_factory=dict)


# ───────────────────────── loom.models（v0.5 的模型層）─────────────────────────
@dataclass
class ModelError(Exception):
    kind: str
    provider: str
    status: int = 0
    retry_after: float = 0.0

    @property
    def retryable(self) -> bool:                # 給第 24 章的 runtime 讀：要不要等一下再試
        return self.kind in {"rate_limit", "overloaded", "server", "network"}

    @property
    def fallback_ok(self) -> bool:
        return self.kind in {"rate_limit", "quota", "overloaded", "server", "network", "auth"}

    @property
    def counts_for_breaker(self) -> bool:
        return self.kind in {"overloaded", "server", "network"}


def classify(provider: str, status: int, body: dict) -> ModelError:
    etype = body.get("error", {}).get("type", "")
    kind = ("quota" if etype == "insufficient_quota" else "rate_limit") if status == 429 else \
           "overloaded" if status in (503, 529) else "server" if status >= 500 else \
           "auth" if status in (401, 403) else "invalid_request"
    return ModelError(kind, provider, status)


@dataclass
class ModelSpec:
    name: str
    provider: str
    tier: str                               # small｜frontier
    price: dict[str, float]                 # 每百萬 token 的美元（示意價格）
    regions: tuple[str, ...] = ("tw", "eu")


class Clock:
    now = 0.0


class Breaker:
    def __init__(self, clock: Clock, window=6, min_calls=3, threshold=0.5, cooldown=20.0):
        self.clock, self.min_calls, self.threshold, self.cooldown = clock, min_calls, threshold, cooldown
        self.state, self.opened_at, self.results, self.log = "closed", 0.0, deque(maxlen=window), []

    def allow(self) -> bool:
        if self.state == "open" and self.clock.now - self.opened_at >= self.cooldown:
            self._move("half_open")
        return self.state != "open"

    def record(self, ok: bool, err: ModelError | None = None) -> None:
        if err is not None and not err.counts_for_breaker:
            return
        if self.state == "half_open":
            return self._move("closed" if ok else "open")
        self.results.append(ok)
        if len(self.results) >= self.min_calls and self.results.count(False) / len(self.results) >= self.threshold:
            self._move("open")

    def _move(self, state: str) -> None:
        self.log.append(f"t={self.clock.now:>3.0f}s {self.state} → {state}")
        self.state, self.opened_at = state, self.clock.now
        if state == "closed":
            self.results.clear()


class Adapter:
    """一個 provider 的翻譯層：統一格式 ⇄ provider JSON。子類只負責 build 與 parse。"""

    def __init__(self, spec: ModelSpec, transport: Callable[[dict], tuple[int, dict]]):
        self.spec, self.transport = spec, transport

    def complete(self, messages, tools=None, system="", effort="medium") -> ModelResponse:
        status, body = self.transport(self.build(messages, tools or [], system, effort))
        if status != 200:
            raise classify(self.spec.provider, status, body)
        return self.parse(body)


class MessagesAdapter(Adapter):           # Anthropic Messages 式
    def build(self, messages, tools, system, effort):
        return {"model": self.spec.name, "system": system, "messages": messages,
                "tools": [{"name": t["name"], "input_schema": t["parameters"]} for t in tools],
                "output_config": {"effort": effort}}

    def parse(self, r):
        u = r["usage"]
        usage = {"input_tokens": u["input_tokens"], "cache_read_tokens": u["cache_read_input_tokens"],
                 "cache_write_tokens": u["cache_creation_input_tokens"], "output_tokens": u["output_tokens"]}
        text = "".join(b["text"] for b in r["content"] if b["type"] == "text")
        stop = {"end_turn": "end_turn", "tool_use": "tool_use", "max_tokens": "max_tokens",
                "refusal": "refusal"}[r["stop_reason"]]          # 不認得的值 → KeyError，大聲失敗
        return ModelResponse(text, [], stop, usage, {"provider": "A", "items": r["content"]})


class ItemsAdapter(Adapter):              # OpenAI Responses 式
    def build(self, messages, tools, system, effort):
        return {"model": self.spec.name, "instructions": system, "input": messages,
                "tools": [{"type": "function", **t} for t in tools], "reasoning": {"effort": effort}}

    def parse(self, r):
        u, cached = r["usage"], r["usage"]["input_tokens_details"]["cached_tokens"]
        usage = {"input_tokens": u["input_tokens"] - cached, "cache_read_tokens": cached,
                 "cache_write_tokens": 0, "output_tokens": u["output_tokens"]}
        if r["status"] != "completed":                                # 簡化：本節只處理完成的回應，其他一律大聲失敗
            raise ValueError(f"未處理的 status：{r['status']}")
        text = "".join(c["text"] for i in r["output"] if i["type"] == "message" for c in i["content"])
        return ModelResponse(text, [], "end_turn", usage, {"provider": "B", "items": r["output"]})


class FallbackChain:
    """依序嘗試候選模型；跳過熔斷中的，遇到可換家的錯誤就往下一個。介面和 ScriptedModel 相同。"""

    def __init__(self, adapters: list[Adapter], breakers: dict[str, Breaker]):
        self.adapters, self.breakers, self.attempts = adapters, breakers, []

    def complete(self, messages, tools=None, system="", effort="medium") -> ModelResponse:
        self.attempts, last = [], None
        for ad in self.adapters:
            br = self.breakers[ad.spec.provider]
            if not br.allow():
                self.attempts.append(f"{ad.spec.name} 熔斷中")
                continue
            try:
                resp = ad.complete(messages, tools, system, effort)
            except ModelError as err:
                br.record(False, err)
                self.attempts.append(f"{ad.spec.name} ✗{err.kind}")
                last = err
                if not err.fallback_ok:
                    raise                                  # 400 這類錯誤換家也沒用，直接往外丟
                continue
            br.record(True)
            self.attempts.append(f"{ad.spec.name} ✓")
            resp.raw["model"] = ad.spec.name
            return resp
        # 整條 chain 都不可用：丟出最後一個錯誤（全部熔斷中視同 overloaded），
        # 讓外層的 runtime 依 retryable 決定要不要等一下再試（第 24 章），而不是在這裡自己重試
        raise last or ModelError("overloaded", "chain")


ROUTES = {"triage": "small", "reply": "frontier", "refund_review": "frontier"}
EFFORT = {"triage": "low", "reply": "medium", "refund_review": "high"}


class Router:
    """先用硬條件（租戶允許的區域）過濾，再依任務類別選等級；同等級的模型照偏好順序排成 fallback chain。"""

    def __init__(self, adapters: list[Adapter], breakers: dict[str, Breaker]):
        self.adapters, self.breakers = adapters, breakers

    def chain_for(self, task: str, region: str) -> FallbackChain:
        tier = ROUTES[task]
        ok = [a for a in self.adapters if a.spec.tier == tier and region in a.spec.regions]
        return FallbackChain(ok, self.breakers)


class CostLedger:
    PRICE_VERSION = "demo-2026-10"

    def __init__(self, specs: dict[str, ModelSpec]):
        self.specs, self.rows = specs, []

    def record(self, tenant: str, task: str, model: str, usage: dict[str, int], ok: bool) -> float:
        p = self.specs[model].price
        cost = (usage["input_tokens"] * p["input"] + usage["cache_read_tokens"] * p["input"] * p["read_mult"]
                + usage["cache_write_tokens"] * p["input"] * p["write_mult"]
                + usage["output_tokens"] * p["output"]) / 1_000_000
        self.rows.append({"tenant": tenant, "task": task, "model": model, "cost": cost, "ok": ok,
                          "price_version": self.PRICE_VERSION, **usage})
        return cost
# ───────────────────────── loom.models 結束 ─────────────────────────


# 假的 provider 後端：A 在 t∈[8, 30) 過載；每家各自的 prompt cache，換家就是冷啟動
clock = Clock()
warm: set[str] = set()

def fake_backend(provider: str):
    def transport(req: dict) -> tuple[int, dict]:
        clock.now += 2.0                                          # 每次呼叫花 2 秒（模擬時鐘）
        if provider == "A" and 8 <= clock.now < 30:
            return 529, {"error": {"type": "overloaded_error"}}
        size = len(json.dumps(req, ensure_ascii=False)) // 2
        prefix, hit = 3000, req["model"] in warm
        warm.add(req["model"])
        out = {"low": 60, "medium": 180, "high": 420}[req.get("output_config", req.get("reasoning"))["effort"]]
        if provider == "A":
            return 200, {"stop_reason": "end_turn", "content": [{"type": "text", "text": "好的"}],
                         "usage": {"input_tokens": size, "cache_read_input_tokens": prefix if hit else 0,
                                   "cache_creation_input_tokens": 0 if hit else prefix, "output_tokens": out}}
        return 200, {"status": "completed",
                     "output": [{"type": "message", "content": [{"type": "output_text", "text": "好的"}]}],
                     "usage": {"input_tokens": size + prefix, "output_tokens": out,
                               "input_tokens_details": {"cached_tokens": prefix if hit else 0}}}
    return transport


price = lambda i, o: {"input": i, "output": o, "read_mult": 0.1, "write_mult": 1.25}
SPECS = {s.name: s for s in [
    ModelSpec("a-large", "A", "frontier", price(4, 20), regions=("tw",)),
    ModelSpec("b-large", "B", "frontier", price(3, 15)),
    ModelSpec("a-small", "A", "small", price(1, 5), regions=("tw",)),
    ModelSpec("b-small", "B", "small", price(0.5, 2)),
]}
adapters = [(MessagesAdapter if s.provider == "A" else ItemsAdapter)(s, fake_backend(s.provider))
            for s in SPECS.values()]
breakers = {"A": Breaker(clock), "B": Breaker(clock)}
router, ledger = Router(adapters, breakers), CostLedger(SPECS)

TASKS = [("t-tw", "triage"), ("t-tw", "reply"), ("t-tw", "refund_review"), ("t-tw", "reply"),
         ("t-tw", "triage"), ("t-eu", "reply"), ("t-tw", "reply"), ("t-tw", "reply"),
         ("t-tw", "triage"), ("t-tw", "reply"), ("t-tw", "refund_review"), ("t-tw", "reply"),
         ("t-tw", "triage"), ("t-tw", "reply")]
msgs = [{"role": "user", "content": "B-1042 我不要了，可以退款嗎？"}]
for i, (tenant, task) in enumerate(TASKS):
    clock.now = start = max(clock.now, i * 4.0)                  # 每 4 秒進來一個任務
    chain = router.chain_for(task, region=tenant[2:])
    resp = chain.complete(msgs, system="你是青鳥科技的客服助理。", effort=EFFORT[task])
    cost = ledger.record(tenant, task, resp.raw["model"], resp.usage, ok=True)
    print(f"t={start:>2.0f}s {tenant} {task:<13} ${cost:.4f}  {' → '.join(chain.attempts)}")

print("\n熔斷器 A：", "；".join(breakers["A"].log))
by_model: dict[str, list[float]] = defaultdict(list)
for row in ledger.rows:
    by_model[row["model"]].append(row["cost"])
for m, costs in sorted(by_model.items()):
    print(f"{m:<8} {len(costs):>2} 次  ${sum(costs):.4f}")
total = sum(r["cost"] for r in ledger.rows)
print(f"合計 ${total:.4f}；每次成功任務 ${total / sum(r['ok'] for r in ledger.rows):.4f}")

assert breakers["A"].state == "closed" and "open" in breakers["A"].log[0]
assert all(r["model"].startswith("b-") for r in ledger.rows if r["tenant"] == "t-eu")   # 資料落地：只能用 B
assert {r["model"] for r in ledger.rows if r["task"] == "triage"} <= {"a-small", "b-small"}
first_b_large = next(r for r in ledger.rows if r["model"] == "b-large")
assert first_b_large["cache_read_tokens"] == 0                                         # 換家第一次一定是冷的
```

```text
t= 0s t-tw triage        $0.0041  a-small ✓
t= 4s t-tw reply         $0.0189  a-large ✓
t= 8s t-tw refund_review $0.0155  a-large ✗overloaded → b-large ✓
t=12s t-tw reply         $0.0038  a-large ✗overloaded → b-large ✓
t=16s t-tw triage        $0.0017  a-small 熔斷中 → b-small ✓
t=20s t-eu reply         $0.0038  b-large ✓
t=24s t-tw reply         $0.0038  a-large 熔斷中 → b-large ✓
t=28s t-tw reply         $0.0038  a-large 熔斷中 → b-large ✓
t=32s t-tw triage        $0.0003  a-small 熔斷中 → b-small ✓
t=36s t-tw reply         $0.0051  a-large ✓
t=40s t-tw refund_review $0.0099  a-large ✓
t=44s t-tw reply         $0.0051  a-large ✓
t=48s t-tw triage        $0.0007  a-small ✓
t=52s t-tw reply         $0.0051  a-large ✓

熔斷器 A： t= 14s closed → open；t= 36s open → half_open；t= 38s half_open → closed
a-large   5 次  $0.0442
a-small   2 次  $0.0048
b-large   5 次  $0.0309
b-small   2 次  $0.0020
合計 $0.0819；每次成功任務 $0.0059
```

逐段解說這份輸出。

**前兩行（t=0、4 秒）**是正常狀態：分類走 `a-small`，回覆走 `a-large`。注意這兩筆的成本比後面同類任務高（$0.0041、$0.0189），因為這是兩個模型第一次被呼叫，3,000 tokens 的穩定前綴要付 1.25 倍的寫入價格。

**t=8 到 12 秒**，provider A 開始過載。退款審查先送到 `a-large`，得到 `overloaded`，因為這類錯誤可以換家，chain 立刻改送 `b-large`。這筆 $0.0155 是之後 `b-large` 一般回覆（$0.0038）的四倍：`b-large` 的快取是冷的，再加上高 effort 產生較多輸出。t=12 秒的回覆再次在 A 失敗，這是熔斷器視窗中的第二次失敗，失敗率達到 50%，熔斷器在 t=14 秒打開（熔斷器紀錄的第一筆）。

**t=16 到 32 秒**是熔斷期間。每一筆都顯示「`a-small 熔斷中`」或「`a-large 熔斷中`」，chain 不再送請求給 A，而是直接走 B，使用者不必先等一次失敗。熔斷器是以 provider 為鍵，所以 `a-small` 雖然沒有親自失敗過，也一起被跳過，這就是 25.6 節說的「粒度太粗」的取捨；在這個情境中 A 是整家過載，所以以 provider 為鍵剛好正確。t=20 秒的歐盟租戶請求只有 `b-large` 一個候選，`a-large` 連出現在 chain 裡的機會都沒有，因為 router 在第一步就依區域把它過濾掉了，這和熔斷器無關。

**t=36 秒以後**，冷卻 20 秒結束，熔斷器轉成半開，放一個探測請求給 `a-large`；provider A 已經在 t=30 秒恢復，探測成功，熔斷器在 t=38 秒閉合，之後的流量全部回到 A。注意 t=36 秒的 `a-large` 成本是 $0.0051，比 t=4 秒的第一次便宜，因為假後端仍保有它的快取（真實系統中要看 TTL 是否已過期）。

**帳本摘要**依模型列出呼叫次數與成本。14 個任務中有 7 個由 B 承接，總成本 $0.0819，每次成功任務 $0.0059。這個情境中所有任務都標為成功，真實系統的 `ok` 要由任務結果回填。最後幾個 assert 鎖住四個保證：熔斷器先打開、最後閉合；歐盟租戶的請求只用了 B 的模型；分類任務只用了小模型；換家後第一次呼叫的快取讀取量為零，也就是冷啟動的成本確實被記到帳上。

| 元件 | 本章對應小節 | 在程式中的類別 | 測試鎖住的保證 |
|---|---|---|---|
| 錯誤分類 | 25.5 | `ModelError`、`classify` | 400 不換家；只有 provider 端錯誤計入熔斷 |
| 能力與政策 | 25.4、25.7 | `ModelSpec` | 資料落地：不允許的區域連候選都不是 |
| 熔斷器 | 25.6 | `Breaker` | closed → open → half_open → closed |
| adapter | 25.3、25.4 | `MessagesAdapter`、`ItemsAdapter` | usage 正規化成互斥的桶 |
| fallback chain | 25.7 | `FallbackChain` | 熔斷中直接跳過；可換家的錯誤才往下走 |
| router | 25.8 | `Router` | 任務類別決定等級；同等級依偏好排序 |
| 成本帳本 | 25.9 | `CostLedger` | 每筆記錄實際模型、價格版本與冷快取成本 |

這張表是 `loom.models` 的導覽。要特別說明的是它和 `loom` 其他部分的接法：`FallbackChain.complete()` 的簽名和第 4 章的 ScriptedModel 相同，所以 v0.1 的 `Agent` 可以直接把 chain 當成模型使用，loop 一行都不用改；第 24 章的 runtime 則在 chain 的外面做重試與退避：整條 chain 都失敗時，chain 丟出最後一個 `ModelError`（全部熔斷中則視同 overloaded），runtime 只讀它的 `retryable` 決定要不要等一下再試；`effort` 與任務類別則由 agent 的設定傳下來。刻意省略的部分：同模型重試（第 24 章）、延遲型熔斷、跨 process 共享熔斷狀態、adapter 的 tool call 與串流（25.4 節示範過）、從版本化設定載入價格表，這些是上 production 前要補的洞。

## 25.11 實務應用

**情境一：多租戶電商客服（青鳥的主線）**。客服是同步互動，最重要的是故障時的延遲與資料落地。router 的第一步一定是租戶政策過濾：有資料落地要求的租戶，候選清單裡只能有合約允許的區域與供應商，這個清單在租戶設定中明確列出，並由 Maya 的團隊審查。fallback chain 依序是同模型的另一個區域、另一家的同級模型、最後是降級模式（「我們會在 10 分鐘內回覆您」）。分類與意圖辨識走小模型、低 effort；退款審查走前沿模型、高 effort，而且在備援路徑上改成一律需要客服確認，因為備援模型沒有經過和主力模型一樣多的退款 eval。帳本以租戶為第一維度，讓業務可以看到每個租戶的單位成本，也讓「某個租戶的對話特別長」這類問題能被發現。

**情境二：background coding agent**。內部 coding agent 的任務動輒數十步、context 很長，快取命中率是成本的決定因素，所以主線 session 黏著在同一個前沿模型上，不做逐步路由；輔助工作（讀大檔案後的摘要、搜尋結果的過濾、平行的唯讀調查）在獨立 context 裡交給小模型。fallback 的設計重點是「不要在任務中途換模型」：provider 故障時，進行中的任務暫停並等待熔斷器恢復（搭配第 22 章的 durable execution 從 checkpoint 繼續），新任務才改走備援；如果一定要中途換，就在下一次 compaction 時換。公開資料中，Devin Fusion 採用主模型加 sidekick 的配置並在 compaction 時切換；Claude Code 等 coding agent 的 subagent 機制也讓輔助工作有獨立的 context。

**情境三：營運 research 與批次報表**。research agent 是阿哲那張帳單的來源。它的工作天然分層：規劃與最後的綜合需要前沿模型，大量的「讀一頁、抽出相關段落、摘要」可以交給小模型，而且這些子任務彼此獨立，很適合平行（第 20 章）。cascade 在這裡很好用，因為很多子任務有確定性的驗證：抽出的數字是否出現在原文、引用是否指向真實存在的段落。夜間的批次報表沒有延遲壓力，可以選更便宜的模型與供應商的批次介面。帳本要同時記錄搜尋 API 與 sandbox 的成本，因為 research agent 的 tool 成本常常和模型成本同一個量級。

**情境四：受監管產業的內部助理（例如金融或醫療機構）**。這類情境的路由決策首先是法遵決策：哪些資料類別可以送到哪些供應商、是否需要零資料保留、是否只能用自架的開源模型。常見的設計是把 router 的第一層做成資料分類器：含有個資或敏感資料的請求只能走自架模型或特定合約的端點，其他請求才可以使用外部的前沿模型。fallback 永遠不能跨越資料分類的邊界，寧可降級成「目前無法處理，請稍後再試」。Amazon Bedrock、Google Vertex 這類雲端平台提供多家模型與區域部署，常被用來滿足資料落地要求；企業也常在內部放一個 model gateway，集中管理金鑰、配額、稽核與成本分攤，`loom.models` 的 router 與帳本就相當於這個 gateway 的應用層版本。

| 情境 | 路由重點 | fallback 重點 | 帳本重點 |
|---|---|---|---|
| 多租戶客服 | 租戶政策過濾；分類走小模型 | 換區域 → 換家 → 降級模式；備援路徑收緊權限 | 租戶維度、每次成功對話成本 |
| background coding | 主線黏著前沿模型；輔助走小模型 | 進行中的任務暫停等恢復；只在 compaction 換 | 每個任務的總成本與快取命中率 |
| research／批次 | 規劃與綜合用前沿；子任務 cascade | 批次可延後，不必即時換家 | 模型與 tool 成本合併記錄 |
| 受監管產業 | 資料分類決定可用模型 | 不得跨越資料分類邊界 | 稽核需要的完整維度與保留期 |

這張表顯示同一套 `loom.models` 在不同產品上的差異幾乎都落在設定與政策：規則表、chain 順序、熔斷門檻、帳本維度。這正是把它做成 framework 模組的理由：政策可以集中審查，事故時的行為可以預測。

> [!note] 2026 現況
> 截至 2026 年 10 月，主流框架大多內建多 provider 支援（依各框架公開文件與 release 紀錄）：Strands Agents 支援 Bedrock、Anthropic、OpenAI、Gemini、LiteLLM、Ollama 等；Pydantic AI 近期版本有 `ConcurrencyLimitedModel` 等模型包裝；DSPy 3.4.0（2026-09-25）內建原生 LM 引擎與 `register_provider(...)`。選型時要確認框架的模型抽象是否保留不透明欄位、usage 是否正規化、錯誤是否分類，第 26 章會比較。

## 25.12 設計檢查清單

1. 整個系統中，是否只有 transport 層 import 供應商 SDK？其他程式是否只依賴 `complete()` 這個埠與 `ModelError`？
2. 每個 adapter 是否有 golden test，鎖住訊息轉換、tool call 解析、停止原因對應與 usage 正規化？
3. usage 是否正規化成互斥的桶（未快取輸入、快取讀、快取寫、輸出）？資訊性的 reasoning tokens 是否確定沒有再加進成本？
4. 遇到不認得的 stop reason 時，adapter 是大聲失敗，還是默默當成 `end_turn`？
5. 不透明欄位（thinking 簽章、加密 reasoning）是否原樣保存在 `raw`，同一家原樣送回、跨家時丟棄？
6. 每一類 API 錯誤是否都明確定義了「同一家重試、換下一個、計入熔斷、通知誰」四件事？
7. SDK 與 HTTP 客戶端的內建重試是否已關閉，只保留 runtime 一層？是否設定了重試預算？
8. 熔斷器的鍵是 provider、模型，還是 provider＋模型＋區域？是否把「過慢」也算成失敗？
9. 拒答（refusal）是否被當成停止原因交給產品政策處理，而不是觸發 fallback？
10. fallback 的候選是否先經過資料落地、能力與 context window 的硬條件過濾？
11. 備援路徑平時是否有小流量、獨立的 eval 與足夠的配額？fallback 發生時是否有指標與告警？
12. session 內是否黏著在同一個模型，只在 compaction 這類快取本來就失效的時間點切換？
13. 每個路由規則是否有 eval 支撐？cascade 的升級訊號是外部驗證，還是模型的自我信心？
14. 帳本是否記錄實際模型、價格表版本、租戶、任務、路由、是否 fallback 或升級，以及 trace id？
15. 「每次成功任務成本」能不能從帳本算出來？任務成功與否是否會回填到帳本？

## 25.13 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 成本報表比供應商帳單高很多或低很多 | usage 語意不同（input 是否含快取）未正規化；reasoning 重複計算 | 拿同一請求的原始 usage 與帳本紀錄比對；按 provider 分開對帳 | adapter 正規化成互斥的桶；golden test 鎖住；每月對帳告警 |
| 換到備援 provider 後立刻回 400 | 前一家的不透明欄位被轉送過去；tool 結果格式未轉換 | 印出送給備援的請求 JSON，找 thinking、reasoning 欄位 | 跨家時只用統一格式重建 assistant 訊息，丟棄別家的 `raw` |
| provider 故障時延遲飆高、故障拖得更久 | 多層重試相乘；沒有熔斷器，每個請求都等到逾時 | 看 trace 中單一請求的嘗試次數與每次等待時間 | 關掉 SDK 內建重試；加熔斷器與重試預算；退避加 jitter |
| 一個程式 bug 讓健康的 provider 被熔斷 | 400 也計入熔斷器的失敗 | 熔斷時段的錯誤種類分布是否以 `invalid_request` 為主 | 只讓 overloaded、server、network 計入熔斷 |
| 平常一切正常，故障那天備援也失敗 | 備援路徑平時沒有流量，配額、金鑰或 prompt 早已失效 | 檢查備援路徑最近一次成功呼叫的時間 | 固定小比例流量走備援；備援也跑 eval；配額預留 |
| 用了 routing 之後，抱怨變多但沒有任何錯誤 | 路由把困難的請求送到小模型；cascade 依自我信心升級 | 抽樣小模型路由的請求做 shadow 比較；看各 route 的成功率 | 改用外部驗證當升級訊號；調整規則；router 納入 eval |
| 加了逐步路由後成本反而上升 | 每換一次模型就丟一次快取 | 看帳本中各呼叫的 `cache_read_tokens` 是否經常歸零 | session 內黏著同一模型；輔助工作放獨立 context；只在 compaction 切換 |
| 截斷或拒答的回應被當成完整答案給使用者 | adapter 把未知或非典型的停止原因對應成 `end_turn` | 搜尋 `raw` 中原始停止原因與統一值不一致的紀錄 | 明確對應 `max_tokens`、`refusal`；不認得的值丟例外 |
| 歐盟租戶的資料出現在不允許的區域 | fallback 為了可用性越過資料落地限制 | 依帳本的 `tenant` 與 `region` 交叉查詢 | 硬條件在 router 第一步過濾；寫成測試；降級優先於越界 |

## 本章重點整理

- model 抽象是 agent loop 與供應商 API 之間的一層 ports and adapters：上層只依賴 `complete()` 一個埠，供應商細節全部收在 adapter 與 transport 裡。
- 抽象層要避開兩個陷阱：最小公分母會藏起每家的能力，聯集式介面會讓每個欄位都附帶例外；正確做法是統一語意相同的部分、把相近的部分抽象成意圖、把獨有的部分明確透傳。
- 各家 API 的差異不只在訊息與 tool 格式，還在推理控制、cache 標記、usage 語意、停止原因與錯誤碼；後三者錯了不會報錯，只會讓成本、停止判斷與錯誤處理默默偏掉。
- adapter 把 usage 正規化成互斥的桶（未快取輸入、快取讀、快取寫、輸出），成本與預算才能直接相加；資訊性的 reasoning tokens 不能再計入成本。
- 不透明欄位要原樣保存在 `raw`：同一家原樣送回，跨家時丟棄並用統一格式重建，這是跨 provider fallback 必須接受的資訊損失。
- 不認得的停止原因要大聲失敗，不能默默當成 `end_turn`，否則截斷或暫停的回應會被當成完整答案。
- 模型 API 的錯誤要回答三個獨立問題：同一家重試有沒有用、換一家有沒有用、是否代表 provider 壞了；拒答不是錯誤，不能用 fallback 繞過。
- 重試只留一層：關掉 SDK 與 HTTP 客戶端的內建重試，由 runtime 依錯誤分類決定，並設定重試預算，避免故障時多層重試相乘。
- 熔斷器讓請求在 provider 壞掉時直接跳過、不必等逾時，也讓 provider 有機會恢復；只有 provider 端的錯誤與過慢的呼叫該計入。
- 換模型不是換字串：fallback 要處理歷史轉換、能力相容、資料落地、prompt 適配與冷快取成本，而且備援路徑平時就要有流量與 eval。
- model routing 依任務類別、難度、成本與延遲選模型；硬條件永遠最先過濾，規則路由優先於分類器，cascade 的品質上限由驗證器決定。
- session 內的路由要黏著，主線維持同一個模型、輔助工作放獨立 context，模型切換只發生在 compaction 這類快取本來就失效的時間點。
- 成本要在 model 層、每次成功回應的當下，用版本化的價格表算好寫進 append-only 的帳本，並附上實際模型、租戶、任務、路由與 trace id。
- 決策要看每次成功任務成本，而不是單次呼叫成本；帳本必須能回填任務結果，才算得出這個數字。

## 延伸問答

> [!question]- Q1. model 抽象層應該做到「讓所有 provider 看起來一模一樣」嗎？
> 不應該。「一模一樣」只有兩種做法：只保留大家都有的功能（最小公分母），或把每一家的參數都塞進統一介面（聯集）。前者會讓你用不到某家最有價值的能力，例如伺服器端工具、特殊的快取控制或推理模式；後者會讓統一介面變成一份「某參數只在某家有效」的例外清單，上層程式反而要知道每一家的差異，抽象就失去意義。
>
> 比較好的目標是「上層不必知道差異，同時差異不會遺失」。語意相同的部分（訊息、tool call、停止原因、usage）統一；語意相近但細節不同的部分（推理強度、cache 斷點）抽象成意圖，由 adapter 翻譯；某一家獨有的功能放在明確標示的透傳欄位，只在指定該 provider 的路由上使用。判斷標準是：如果一個功能要讓上層程式寫 `if provider == ...`，它就應該被抽象成意圖或明確透傳，而不是假裝不存在。

> [!question]- Q2. 為什麼 usage 一定要正規化成「互斥的桶」？直接存各家的原始數字不行嗎？
> 原始數字一定要存（放在 `raw`，對帳與除錯用），但不能直接拿來算錢或做預算。各家對 input tokens 的定義不同：有的只代表未命中快取的部分，快取讀寫另外列；有的代表全部輸入，再用子欄位說明其中多少命中快取。輸出也類似，reasoning tokens 常常是輸出總數的子集。如果上層直接相加，同一個 token 會在某家被算兩次、在另一家被算成錯誤的價格。
>
> 互斥的桶讓每個 token 只出現在一個地方，成本就是「每個桶 × 單價」的簡單加總，預算檢查也是簡單加總，完全不需要知道它來自哪一家。這把「語意差異」的複雜度集中在 adapter 的 parse 函式裡，用 golden test 鎖住；其他所有地方（帳本、預算、儀表板）都只面對一種語意。Iris 雙 11 隔天的報表多算一倍，就是把這個複雜度散落到報表程式裡的結果。

> [!question]- Q3. 程式找錯：下面這段 fallback 程式有三個會在 production 出事的問題，請指出來。
> ```python
> def complete(messages, tools):
>     for model in ["a-large", "b-large", "b-small"]:
>         try:
>             return clients[model].create(model=model, messages=messages, tools=tools)
>         except Exception:
>             continue
>     raise RuntimeError("all failed")
> ```
> 第一，`except Exception` 不分青紅皂白地換家。400 格式錯誤是我們的 bug，換家只會把 bug 藏起來；context 太長換到視窗更小的模型只會再失敗一次；拒答如果以例外形式出現，換家等於繞過安全機制。正確做法是先把錯誤分類成 `ModelError`，只有 `fallback_ok` 為真才往下走。
>
> 第二，歷史沒有轉換。`messages` 原封不動送給另一家，前一家的 thinking 簽章或加密 reasoning 會讓請求被拒，tool 結果的格式也可能不對；這正是 Iris 在雙 11 撞到的 400。第三，沒有熔斷器也沒有記錄：每個請求都要先在壞掉的 `a-large` 上等到逾時，provider 也持續被打；而且呼叫端完全不知道這次實際用了哪個模型，帳本會用錯價格，trace 也追不到。另外 `b-small` 和前兩個不是同一等級，品質降級應該是明確的決策，不該默默發生在備援鏈的尾端。

> [!question]- Q4. 熔斷器的冷卻時間要設多長？設太短或太長分別會發生什麼事？
> 冷卻時間是「保護下游」與「恢復後多快用上」之間的取捨。設太短，熔斷器頻繁地在 open 與 half_open 之間切換，每次探測都打到還沒恢復的 provider，而且多個 worker 的探測可能同時發生，形成週期性的小尖峰；設太長，provider 早就恢復了，流量卻還在備援上跑，付著冷快取與可能更貴的單價，品質也可能較差。25.6 節的模擬中，provider 在 t=60 秒恢復，熔斷器到 t=76 秒才閉合，這 16 秒就是冷卻太長的代價。
>
> 實務上的起點是參考 provider 過去事故的典型持續時間與自己的延遲預算，例如數十秒到幾分鐘，再加上幾個改進：冷卻時間指數成長（連續探測失敗就加倍，有上限）、探測請求加 jitter 避免多個 worker 同步、half_open 時只放少量請求而不是一個就決定。最重要的是把熔斷器的狀態變化當成指標輸出，事後用真實事故的資料回頭調整，而不是憑感覺設一個數字。

> [!question]- Q5. 情境題：你在 production 看到備援 provider 的流量比例從平常的 1% 慢慢升到 15%，但沒有任何告警，你會怎麼查？
> 先確認這是「主力 provider 在失敗」還是「router 或熔斷器的行為變了」。第一步看熔斷器的狀態變化紀錄與主力 provider 的錯誤種類分布：如果是大量 overloaded 或 5xx，代表主力真的不穩定，要和供應商確認並評估是否要調整容量；如果熔斷器頻繁打開但錯誤種類是 `invalid_request`，代表有 400 被錯誤地計入熔斷，很可能是某個新版本的 prompt 或 tool 定義觸發了格式錯誤。
>
> 第二步看是不是 429 速率限制或額度問題：流量成長讓主力的 TPM 不夠，請求被限速後轉到備援，這是容量規劃問題，不是故障。第三步確認延遲型熔斷：如果把「過慢」也算失敗，主力 provider 延遲小幅上升就可能把流量推走。最後要補上這次缺失的東西：fallback 比例本身就該是一個有告警門檻的指標，而且帳本要能按 `fallback` 欄位算出這段期間多花了多少錢、備援路徑的任務成功率是否較低。

> [!question]- Q6. 設計取捨：規則路由、分類器路由和 cascade 要怎麼選？可以混用嗎？
> 先問「呼叫端知不知道這一步在做什麼」。agent 系統中很多模型呼叫是 harness 程式碼自己發起的：意圖分類、摘要 tool 輸出、compaction、抽取訂單編號，呼叫端完全知道任務類別，規則路由最便宜、最確定、也最好審查，應該是預設選擇。分類器路由適合「同一個入口、難度差異很大、呼叫端無法事先知道」的情境，例如使用者的第一則訊息；它的代價是分類器本身的成本、延遲與錯誤率，所以分類器必須比它省下的錢便宜很多，而且要和 router 一起評估。
>
> cascade 適合「有便宜而可靠的驗證」的任務：輸出能被 schema、業務規則、測試或資料比對檢查。沒有驗證器的 cascade 只能依賴模型的自我信心，而 25.8 節的模擬顯示自信與正確率並不可靠。三者可以而且通常應該混用：硬條件過濾之後，有規則的走規則，沒有規則的交給分類器，分類器不確定的走 cascade。關鍵是每一層的決定都要寫進 trace，並且有 eval 量測各 route 的成功率與成本。

> [!question]- Q7. 估算題：客服 agent 每天 20 萬次模型呼叫，其中 60% 是意圖分類與摘要。假設前沿模型每次呼叫平均成本 1.0 元、小模型 0.1 元，把這 60% 改走小模型可以省多少？還要考慮什麼？
> 改之前每天成本是 20 萬 × 1.0 ＝ 20 萬元。改之後，12 萬次分類與摘要走小模型 ＝ 1.2 萬元，8 萬次其他呼叫仍走前沿 ＝ 8 萬元，合計 9.2 萬元，每天省 10.8 萬元，約 54%。如果其中一部分改用 cascade，例如分類有 10% 需要升級，升級的那 1.2 萬次要多付 1.2 萬元，總成本約 10.4 萬元，仍省約 48%。
>
> 但這個估算漏了幾件事。第一，快取：分類與摘要如果原本和主線共用前沿模型的快取前綴，改走小模型後兩邊各自的快取命中率都要重新量，每次呼叫的平均成本可能不是 1.0 與 0.1。第二，品質：分類錯誤會讓後面整條 trajectory 走錯，成本與滿意度都會受影響，要看的是每次成功任務成本，而不是每次呼叫成本。第三，延遲通常會改善，這是額外的好處。所以正確的流程是先在 eval 上量測小模型的分類正確率與下游影響，再用 shadow 流量確認，最後才全面切換。

> [!question]- Q8. 面試追問：如果要把 `loom.models` 做成全公司共用的 model gateway，你會怎麼調整設計？
> 第一個改變是部署形態：從 library 變成一個獨立的服務（或 sidecar），各團隊的 agent 透過內部 API 呼叫它。好處是金鑰、配額、資料落地政策、稽核與成本分攤集中管理，供應商合約也只要接一次；代價是多一個網路跳點與一個必須高可用的依賴，所以 gateway 本身要多區域部署，而且串流要能端到端穿透。熔斷器狀態在服務內共享，反應比每個 process 各自判斷快。
>
> 第二個改變是多租戶治理：每個團隊、每個 agent 都要有配額與預算（RPM、TPM、每月金額），超過時依政策限流或降級；帳本變成公司層級的成本分攤系統，維度要包含團隊與產品。第三是政策即設定：路由規則、fallback 順序、資料分類對應的允許模型，都以版本化設定管理並經過審查，變更要能 canary。最後是保持「埠」不變：各團隊程式碼依賴的仍然是 `complete()` 這個介面與 `ModelError` 分類，從 library 切換到 gateway 只需要換一個 transport，這正是 ports and adapters 在組織層級的價值。

## 延伸閱讀

- Michael T. Nygard《Release It! Design and Deploy Production-Ready Software》（第 2 版，2018，Pragmatic Bookshelf）：Circuit Breaker 與穩定性模式
- Alistair Cockburn〈Hexagonal Architecture（Ports and Adapters）〉（2005）
- Anthropic 文件〈Errors〉與〈Prompt caching〉（Claude Developer Platform）
- OpenAI 文件〈Responses API reference〉與〈Error codes〉（OpenAI Platform）
- Cognition Blog〈Devin Fusion〉（2026）
- Chen, Zaharia, Zou〈FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance〉（2023，arXiv）
- Ong et al.〈RouteLLM: Learning to Route LLMs with Preference Data〉（2024，arXiv）
- OpenTelemetry〈Semantic Conventions for Generative AI〉
