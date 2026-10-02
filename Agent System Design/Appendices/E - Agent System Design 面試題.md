# 附錄 E　Agent System Design 面試題

> [!abstract] 本附錄地圖
> **用途**：30 題 agent system design 面試題，分成兩類：E1–E10 是完整的 system design 題（45–60 分鐘），E11–E30 是概念與取捨題（5–15 分鐘的追問或獨立題）。每題都附上「考什麼」「答題框架」「參考答案要點」「常見陷阱與加分點」「對應章節」，答案要點寫成可以逐項打勾的形式，方便自我練習或當面試官時評分。
>
> **怎麼查**：E.1 節先說明答題流程，沿用第 35 章的七步驟框架；E.2 節是題目總表，可以依類型、難度與章節挑題；E.3 與 E.4 節是題目本體，答案收在摺疊區塊裡，先自己作答再展開對照；E.5 節是一段白板速算程式，驗證本附錄估算題用到的數字；E.6 節是評分 rubric 與練習方法。
>
> **前置知識**：讀過第 35 章（七步驟、需求釐清清單、容量與成本估算）最有幫助；每題的「對應章節」指出答不出來時該回去讀哪裡。

## E.1 答題流程：把第 35 章的七步驟搬進面試

agent system design 面試和傳統 system design 面試的骨架相同：需求釐清、估算、高階架構、深入元件、擴展與取捨、回答追問。差別在每一步的內容。第 35 章 35.2 節整理過，agent system 的成本隨步數近似平方成長、正確性是機率性的、副作用由模型提議而由 harness 核准、容量瓶頸在模型配額與核准人力。面試官要看的，正是你有沒有意識到這些差別，並把它們放進每一步，而不是在一般的服務架構圖上加一個「LLM」方塊。

所以答題的主線，是把第 35 章的七個步驟（任務與成功標準 → autonomy 與風險 → 架構選型 → context 與 tools → 評估 → 安全 → 營運）壓進一場有時間限制的對話。下面是 45 分鐘題目的建議時間分配；60 分鐘的題目把多出來的時間留給深入元件與追問。

```text
 分鐘  0────5────10───15───────25────────35───────42──45
       │需求 │估算 │動作 │ 架構選型 │ 深入元件 │評估／ │追問│
       │釐清 │     │清冊 │＋高階圖  │（context、│安全／ │總結│
       │     │     │     │          │ tools、    │營運   │    │
       │     │     │     │          │ 指定元件） │       │    │
 七步驟 (1)   估算  (2)    (3)        (4)        (5)(6)(7)
        └ 任務卡與成功標準寫在白板角落，之後每個決定都指回它 ┘
```

這張時間軸由左到右讀。前五分鐘是第 35 章的步驟一：問出使用者、互動形式、動作範圍與成功標準，並把三到五個數字與兩三條硬約束寫在白板角落（第 42 章 42.2 節的技巧）。接著五分鐘做量級估算，目的不是精確，而是找出哪個資源會先耗盡；對 agent 平台，答案幾乎總是 token 吞吐量、成本或核准人力。第三段是步驟二的動作清冊：列出每個 tool 的副作用分級與 autonomy 等級，這一步刻意放在畫架構之前，因為動作的風險會限制架構。然後才畫架構，並用第 35 章 35.6 節的決策樹說明「為什麼更簡單的結構不夠」。深入元件時，主動挑 context 版面與 tool 介面來講，也接受面試官指定的元件。最後七分鐘依序交代評估、安全與營運，留三分鐘回答追問與總結。

| 步驟 | 面試中要說出口的東西 | 面試官在找的訊號 | 最常見的扣分 |
|---|---|---|---|
| (1) 任務與成功標準 | 使用者、通路、範圍與非目標、三層成功指標（業務／品質／成本延遲） | 有沒有把「正確地轉真人」或「正確地拒絕」算成成功 | 只問流量，不問 agent 能做哪些動作 |
| 估算 | 每 session 的 k、P、d，尖峰 λ、並行數、TPM、每次成功任務成本 | 知道 input ≈ k×P ＋ d×k(k−1)/2，知道瓶頸是 token 不是 QPS | 只算 QPS；用全天平均而不是尖峰 |
| (2) autonomy 與風險 | 動作清冊：read／write／destructive、L0–L5、邊界、最大損失、idempotency 欄位 | 依動作而不是依系統決定 autonomy；不可回復的動作不完全自動 | 「我們是 L4 agent」；政策只寫在 prompt |
| (3) 架構選型 | 單次呼叫／workflow／單 agent／multi-agent 的選擇與被否決的替代方案 | 先證明單 agent 不夠，才拆 multi-agent | 一開口就畫五個專責 agent |
| (4) context 與 tools | context 三層版面與 token 預算、cache breakpoint、tool 粒度與回傳上限 | 把版面翻成成本參數；知道穩定層不能有會變的內容 | 「context window 有 1M，不用管」 |
| (5) 評估 | eval set 來源、grader、pass^k、上線門檻表、回歸與線上指標 | 以環境最終狀態評分；面向使用者的任務看 pass^k | 「我們會人工測一下」 |
| (6) 安全 | 信任邊界、lethal trifecta 檢查、有效權限交集、sandbox 與 egress | 回答「模型被完全誘導時最壞能做什麼」 | 「加一個 guardrail 過濾惡意輸入」 |
| (7) 營運 | SLO、release 綁定、canary、kill switch、降 autonomy、成本告警 | 把估算的假設變成儀表板；故障時先降級而不是全停 | 完全沒提上線後怎麼變更與止血 |

這張表的用法是：練習時每一列都要能說出至少一句具體的話，而且那句話要指向白板上的某個數字或約束。表的第三欄是加分的方向，第四欄是本書觀察到最常見的扣分。特別注意第 (2) 列：autonomy 是依「動作」決定的（第 1 章的定義），而且「路徑由誰決定」與「副作用由誰核准」是兩條獨立的軸，能清楚講出這兩點的候選人很少，所以它往往是區分度最高的一步。

```text
 面試官說「設計一個 X agent」
   │
   ├─► 先問會改變架構的問題：動作與風險 ＞ 互動形式與延遲 ＞ 流量與尖峰 ＞ 資料與權限 ＞ 合規
   │
   ├─► 複述假設：「我假設每天 N 個 session、尖峰一成、500 元以下退款自動……」
   │
   ├─► 每一個設計決定都附一句「因為……」，指回白板角落的數字或約束
   │
   ├─► 主動說出取捨：「這樣做的代價是……，如果條件變成……我會改成……」
   │
   └─► 被追問時先承認範圍：「這部分我會量 X 再決定」比編造數字好
```

這張流程圖是整場面試的說話習慣。第一個箭頭的提問順序來自第 35 章 35.11 節的需求釐清清單：動作與風險放最前面，因為它是 agent system 和一般聊天機器人最大的差別，也是面試官最想聽你主動問的。第二個箭頭的複述讓雙方對齊，之後的估算才有根據。第三、四個箭頭是評分的核心：沒有「因為」的決定只是偏好，沒有「代價」的設計只是推銷。最後一個箭頭處理不知道的事：說清楚你會量什麼、怎麼量，比背出某家廠商的價格或某個 benchmark 分數更有說服力。

> [!warning] 常見誤解
> 「agent 面試就是考你知不知道最新的框架與模型。」框架與模型的名字會在一年內換一輪，面試官要確認的是不容易過時的判斷：什麼時候不該用 agent、動作的風險怎麼分級、成本從哪裡來、怎麼知道它做對了、被注入時最壞能做什麼。提到具體產品時，說清楚「截至何時、依公開資料」，並把它當成例子而不是論據。

## E.2 題目總覽

| 題號 | 題目 | 類型 | 難度 | 主要對應章節 |
|---|---|---|---|---|
| E1 | 多租戶電商客服 agent 平台 | design | ★★★ | 35、36、41、42 |
| E2 | 背景 coding agent 平台（issue 到 PR） | design | ★★★ | 17、20、22、39、43 |
| E3 | 企業 research 與 analytics agent | design | ★★★ | 11、20、40、44 |
| E4 | 多租戶 agent 記憶服務 | design | ★★ | 12、33 |
| E5 | 多租戶 MCP gateway | design | ★★★ | 14、31、33、36 |
| E6 | agent eval 平台 | design | ★★ | 27、28、29 |
| E7 | 託管 code execution sandbox 服務 | design | ★★★ | 17、36 |
| E8 | 操作網頁後台的 browser agent | design | ★★ | 16、21、22 |
| E9 | 公司級 model gateway | design | ★★ | 25、36 |
| E10 | 跨 agent 共用的核准（HITL）服務 | design | ★★ | 21、22、33 |
| E11 | workflow 還是 agent | 概念 | ★ | 1、18、35 |
| E12 | 什麼時候值得用 multi-agent | 取捨 | ★★ | 20、40 |
| E13 | prompt injection 的防禦設計 | 概念 | ★★★ | 31、32 |
| E14 | compaction 怎麼設計、怎麼測 | 概念 | ★★ | 10 |
| E15 | pass@k 與 pass^k | 概念 | ★ | 27 |
| E16 | durable execution 的原理 | 概念 | ★★ | 22 |
| E17 | 好的 tool 長什麼樣 | 概念 | ★ | 5 |
| E18 | 退款逾時：idempotency 與「結果未知」 | 情境 | ★★ | 5、22 |
| E19 | cache 命中率突然掉到個位數 | 情境 | ★★ | 3、9、30 |
| E20 | 估算：IT helpdesk agent 的成本與容量 | 估算 | ★★ | 3、35 |
| E21 | 工具從 10 個長到 200 個 | 取捨 | ★★ | 13 |
| E22 | 傳統 RAG、agentic RAG 與權限 | 取捨 | ★★ | 11 |
| E23 | 把退款從 L3 放寬到 L4；approval fatigue | 情境 | ★★ | 1、21、38 |
| E24 | function calling、MCP、A2A、AG-UI 的分工 | 概念 | ★ | 14、15 |
| E25 | LLM-as-judge 能不能信 | 概念 | ★★ | 27 |
| E26 | 多租戶隔離與 noisy neighbor | 取捨 | ★★ | 33、36、42 |
| E27 | 全綠的儀表板與靜默失敗 | 情境 | ★★ | 29、34 |
| E28 | 換模型或換供應商 | 情境 | ★★ | 25、30、36 |
| E29 | 自建 framework、用 SDK 還是託管服務 | 取捨 | ★★ | 23、26 |
| E30 | agent 的 SLO 與事故止血 | 概念 | ★★ | 34、36 |

難度的意思是：★ 題答對定義與一個例子就及格；★★ 題要講出取捨與至少一個失敗模式；★★★ 題要串起三個以上的章節，並能回答兩層以上的追問。練習時建議先做 E11、E15、E17 熱身，再做 E1 這種主線題，最後挑自己最弱的章節對應的題目。

## E.3 System design 題（E1–E10）

這十題每題都可以當成一場 45–60 分鐘的面試。答案要點依七步驟排列，但不必每一步都講到同樣深度：每題的「考什麼」指出面試官最在意的兩三步，時間要優先花在那裡。答案中的數字除非註明來自本書章節，否則都是示意假設，面試時要說清楚。

> [!question]- E1. 設計一個多租戶的電商客服 agent 平台：數千家網店共用，agent 可以查訂單、查物流、回答店家政策、建立退貨單、退款與轉真人。
> **考什麼**：需求釐清能不能問出「動作」與「租戶關係」；估算能不能指出瓶頸是 token 而不是 QPS；租戶隔離是否由程式強制；退款的核准邊界在哪裡執行。
>
> **答題框架**：需求釐清 → 估算（每日對話、尖峰 TPM、成本）→ 動作清冊 → 控制平面／資料平面架構 → 深入 tool gateway、context 分層、approval → eval 與安全 → 營運與擴展。
>
> **參考答案要點**：
> 1. 需求：租戶可能互為競爭對手，所以預設互不信任、跨租戶洩漏零容忍；同一位顧客可能是兩家店的顧客，memory 的 key 是（tenant, shopper）。同步互動，首字 p95 約 2 秒、完整回覆 p95 約 8 秒。明確列出非目標，例如第一期不做語音、不讓商家上傳程式碼當 tool。
> 2. 估算：店家數 × 每店對話數得到每日對話 S，乘尖峰占比換成 λ，再用 k×P ＋ d×k(k−1)/2 換成 TPM 與成本。第 35、42 章的算例（約 4,000 家店、每天 10 萬段對話、k＝8）中，大促尖峰每秒只有約 67 次模型呼叫，QPS 不是問題，但 input TPM 約 3,100 萬，將近假設配額的四倍，必須提前確認 cache 命中的 token 是否計入 rate limit、談保留容量、多區域或多供應商，並把簡單請求路由到小型模型。快取讓每段對話的模型成本從約 0.22 美元降到約 0.10 美元，所以 cache 命中率是一級指標。
> 3. 動作清冊：查詢類 read 為 L4 自動；建立退貨單是可回復的 write；退款是 destructive，500 元以下在 L4 邊界內自動（額度、每日累計上限、事後抽查），超過走核准；未標註的 tool 一律當 destructive。idempotency key 由 harness 依 `order_id`、金額等意圖欄位推導，不放進模型可見的 schema。
> 4. 架構：選單 agent 加依意圖載入的 tools 與 skills，而不是退款、物流、問答三個專責 agent，因為三類請求常出現在同一段對話、彼此相依，拆開會讓核准邊界分散。控制平面把商家設定驗證並編譯成不可變、有版本的 AgentSpec；資料平面是 edge gateway → session router → 無狀態 worker → model gateway 與 tool gateway。
> 5. 深入元件：tenant 只從 edge gateway 驗證過的 session 取得，tool 參數中不得有租戶欄位；所有快取（prompt、語意快取、檢索、tool 結果）的 key 都包含 tenant 與設定版本，否則就會把 A 店的政策回答給 B 店的顧客；tool gateway 集中做授權、憑證注入、approval policy、idempotency 與稽核，policy 不可用時寫入類 tool fail-closed。context 依變動頻率分平台穩定層、租戶半穩定層、對話動態層，店家設定有 token 上限，超過的改成按需檢索。檢索索引依租戶分片，權限過濾在排序之前。
> 6. 評估與安全：以資料庫最終狀態加 claim 檢查評分，看 pass^k 與錯誤退款率，eval 要分租戶看；店家可編輯的知識庫是 indirect injection 的入口，進 context 時標記為資料，而且即使模型被誘導，tool gateway 仍限制在該顧客、該租戶、L4 邊界內。
> 7. 營運：per-tenant token bucket 防 noisy neighbor；prompt、model、tool、policy、索引綁成 release，session 建立時固定；canary 推進、kill switch、供應商故障時降 autonomy 並切到通過 eval 的備援模型。大租戶或有資料區域要求的租戶可放進獨立 cell。
>
> **常見陷阱**：用一個共用向量索引、靠 prompt 叫模型「只看自己店的文件」；只算 QPS；退款上限只寫在 system prompt；把轉真人率壓到最低當目標，逼 agent 硬答。
>
> **加分點**：指出總成本最敏感的是轉真人率而不是 token（第 35 章的敏感度分析）；說明 silo、pool 與 cell 的取捨；提到「別家的資源與不存在的資源回傳相同錯誤」以防探測。
>
> **對應章節**：第 5、9、21、33、35、36、41、42 章。

> [!question]- E2. 設計一個背景 coding agent 平台：開發者在 issue 上指派任務，agent 在隔離環境中改程式、跑測試、開 pull request。
> **考什麼**：sandbox 的隔離與生命週期；長任務的 durable execution；「完成」由誰判定；平方項主導成本時的 context 策略；平行任務的寫入隔離。
>
> **答題框架**：需求（repo 規模、任務類型、可接受的等待時間、誰審 PR）→ 估算（每任務 token、sandbox 並行數）→ 動作清冊（sandbox 內 L4；合併不在 agent 的動作清冊裡）→ 架構（佇列、worker、sandbox pool、repo 快取）→ 深入 context 與驗證 → 安全 → 營運。
>
> **參考答案要點**：
> 1. 互動形式是 background：使用者不在場，所以需要任務佇列、狀態頁、通知，以及 input_required、needs_approval、cancelled 等中斷狀態（第 37 章）。
> 2. 估算：用第 35 章 Q3 的假設（每天 2,000 個任務集中在 10 小時、每任務 60 次呼叫、P＝12,000、d＝1,500、命中率 90%、持有 sandbox 25 分鐘），每任務 input 約 337.5 萬 tokens、平方項約占八成，每任務約 2.9 美元；sandbox 平均約 83 台同時在用（E.5 節的程式重算了這兩個數字）。第 43 章青鳥內部的規模小得多（每天約 300 張任務），但結構相同：token 成本是 sandbox 運算的二十多倍，尖峰 TPM 可能比 sandbox 更早撞到上限。結論：compaction 與把探索交給隔離 context 的 subagent 是成本設計，sandbox 是主要容量資源。
> 3. 動作清冊：sandbox 內讀寫檔案、跑測試是 L4；推送到 agent 專用的工作 branch 是可回復的 write，而且只由 PR 服務執行；合併到主分支、部署、改 CI 設定是不可回復或影響大的動作，根本不在 agent 的動作清冊裡，由人審 PR 後自己執行，並用 branch protection 在 git server 上強制。
> 4. 架構：issue webhook → job queue（lease、heartbeat、fencing）→ 無狀態 worker 跑 loop，每次 model call 與 tool call 都是 durable activity → sandbox pool（warm pool 放尚未使用的乾淨實例，用完即銷毀，不跨任務、不跨租戶）→ repo 快取加速 clone。等待 CI 或人回覆時釋放 worker。
> 5. 驗證：「完成」由 harness 依最新的測試結果判定，而不是模型說「我改好了」；這是第 39 章的 verification gate，沒有外部證據的完成記為 `unverified` 而不是 `succeeded`。驗證要在另一台乾淨的 sandbox 重放 diff，並以 diff 政策擋下刪改既有斷言（第 43 章）；可加一個唯讀的 review agent 做第二道檢查，最終關卡是 CI 與人工 PR 審查。測試檔要受保護，避免 agent 改測試讓它通過（reward hacking 的一種）。
> 6. context：專案指令檔與 repo 地圖放穩定層；檔案按需以 glob、grep、read 讀取；先清最大宗、可重讀的 tool 輸出，再做交接式摘要；進度與計畫寫進檔案。單次 tool 輸出在 tool 層就截斷或落地到檔案。
> 7. 安全：sandbox 選 gVisor 或 microVM 等級，egress 預設拒絕、只開套件來源等 allowlist；secrets 不進 sandbox，需要憑證的呼叫經 credential proxy；issue 內容與 repo 中的文字都是不可信資料。
>
> **常見陷阱**：讓多個 agent 平行改同一個 repo 而沒有 branch 或 worktree 隔離；sandbox 跨任務重用省開機時間；以模型自述判定完成；把 GitHub token 放進 sandbox 環境變數。
>
> **加分點**：用 Little's law 估 sandbox 並行數並依 p99 規劃 pool 與上限；說明子 agent 的主流用途是唯讀探索，平行寫入只在任務獨立且有隔離時使用；提出每任務 token 預算與超過時停止回報。
>
> **對應章節**：第 10、17、20、22、35、37、39、43 章。

> [!question]- E3. 設計一個企業內部的 research 與 analytics agent：營運人員用自然語言問開放的分析問題，agent 跨文件庫、資料倉儲與內部系統查資料，產出附引用的報告。
> **考什麼**：是否真的需要 multi-agent 以及成本倍數；權限感知檢索；SQL 與 code execution 的安全；引用與可信度驗證；L5 預算內自主的邊界。
>
> **答題框架**：需求（問題類型、可等待時間、資料源與權限差異）→ 估算（含 multi-agent 倍數）→ 動作清冊（幾乎全唯讀）→ 架構（lead 加 subagent 或單 agent）→ 深入檢索、SQL、引用 → 評估 → 安全 → 營運。
>
> **參考答案要點**：
> 1. 先分級：簡單事實題用單 agent 加檢索即可；開放、多面向、可平行的問題才啟用 orchestrator–subagent。投入規模的規則寫在指令裡，上限（subagent 數、搜尋次數、token 預算）寫在 harness 裡。
> 2. 成本：Anthropic 公開其 research system 時提到，agent 的 token 用量約為一般聊天的 4 倍，multi-agent 約 15 倍。design doc 要用「每份報告的價值」論證這個倍數值得付，並指出 fan-out 的覆蓋率有天花板、成本沒有。
> 3. 架構：lead 澄清問題並把計畫寫進外部紀錄，平行派出 subagent，每個 subagent 有隔離的 context、只回傳結構化摘要與出處；lead 判斷缺口再補查；最後由獨立的引用步驟把主張對齊原文。
> 4. 權限：有效權限＝發問者權限 ∩ agent 權限 ∩ 任務範圍；檢索的權限過濾在排序之前；subagent 繼承發問者的權限，而不是用一個能讀全部資料的服務帳號。
> 5. SQL 與計算：只給唯讀、限定 schema 的資料庫角色，範圍由 row-level security 或安全視圖在引擎層保證，執行前用查詢計畫估計成本、執行中有 statement timeout，結果有列數上限並明說截斷（第 44 章）；計算放進無對外網路、無 secrets 的 sandbox；大量結果落地成檔案，只把摘要放回 context。
> 6. 安全：同時具備私有資料、不可信內容（外部網頁或使用者上傳文件）與對外通訊時就是 lethal trifecta；切掉對外通訊（報告只回給本人、不渲染外部圖片連結），或讓讀不可信內容的 subagent 以 typed 回傳阻斷污染。
> 7. 評估：rubric 包含事實、引用、完整性、來源品質與 tool 效率，事實與引用是必過項，不能被平均掉；citation precision 與 recall 一起看；定期人工閱讀 trace。
> 8. 數字可追溯：報告中每個數字都要對應證據帳本中的查詢結果（Q 編號）或由程式計算的衍生值（D 編號），沒有證據編號的數字由核對器擋下；報告記錄證據權限下限，分享前檢查讀者權限是否涵蓋（第 44 章）。
>
> **常見陷阱**：所有問題都開最大規模的 fan-out；subagent 用自由文字回傳，把外部內容的注入帶回 lead；「查不到」被寫成「沒問題」；引用只到文件層級。
>
> **加分點**：說明 research agent 是 L5（預算內自主），但任何寫入或對外發送仍要核准；提出主張層級的引用驗證先做便宜的程式檢查、再做語意判斷。
>
> **對應章節**：第 11、17、20、31、33、40、44 章。

> [!question]- E4. 設計一個供公司內多個 agent 共用的記憶服務：能記住使用者偏好與過去事件、支援多租戶，並符合刪除權。
> **考什麼**：記什麼與不記什麼的寫入政策；範圍與隔離；衝突、遺忘與 TTL；刪除權如何 fan-out；memory poisoning。
>
> **答題框架**：釐清使用者與範圍 → 資料模型（episodic／semantic／procedural、範圍、來源、期限）→ 寫入路徑 → 讀取路徑 → 隔離與權限 → 刪除與隱私 → 評估與營運。
>
> **參考答案要點**：
> 1. 三種記憶形狀不同：episodic 記事件、semantic 記事實與偏好、procedural 記做事方法（Skills 是它的產品化，影響所有使用者，寫入門檻最高）。可以隨時查的狀態（訂單狀態）不記，憑證與高敏感個資不進長期記憶。
> 2. 每筆記憶帶範圍（使用者、組織、專案）、來源（使用者明說、客服註記、模型推論）、建立時間與 TTL；推論來的記憶 TTL 最短。agent 對組織記憶預設唯讀，組織記憶只能經審核寫入。
> 3. 寫入政策由 harness 確定性地執行：路徑與範圍檢查、敏感資料過濾、價值判斷、去重與衝突處理；衝突依權威與新近解決，被取代的舊值保留為歷史。讀取衝突的優先順序是產品規則 > 組織規則 > 使用者偏好 > 模型推論。
> 4. 讀取分預載（有上限，截斷時明說）、按需讀取與檢索三層。
> 5. 隔離：harness 依 session 身分把虛擬路徑對應到實體位置，模型的參數中不出現使用者 id；路徑做字串層與 resolve 後的兩層檢查。
> 6. 刪除權：追蹤每份衍生資料的 subject，刪除要 fan-out 到索引、摘要、trace、eval 資料與備份，並用 tombstone 防止被寫回。
> 7. 安全：記憶是資料不是指令，也不能用來授權；memory poisoning 讓一次注入變成持續影響，所以寫入要標來源，來自不可信內容的推論不寫入或需確認。
>
> **常見陷阱**：把整段 session log 當記憶塞回 context；用 email 當 key 導致跨租戶合併；只刪主資料表，忘了向量索引與摘要裡的副本。
>
> **加分點**：提出記憶品質的評估方式（事實保留探針、錯誤記憶率、使用者修正率）；說明選型時要逐一檢查寫入政策、衝突處理、TTL、範圍隔離與刪除介面，而不只是「有沒有 memory」。
>
> **對應章節**：第 10、12、33 章。

> [!question]- E5. 設計一個多租戶的 MCP gateway：公司內外的 agent 透過它存取數百個 MCP server（自建與第三方），需要授權、稽核與防護。
> **考什麼**：MCP 的授權模型（resource server、audience、禁止 token passthrough）；tool poisoning 與供應鏈；集中政策的位置；stateless 協定下的狀態處理。
>
> **答題框架**：釐清使用情境（誰呼叫、哪些 server、內部或第三方）→ 信任模型 → 架構（registry、授權、政策、轉送、稽核）→ 深入授權與定義審核 → 擴展與營運。
>
> **參考答案要點**：
> 1. gateway 對 agent 而言是一個 OAuth resource server：發布 Protected Resource Metadata，client 用 resource indicator 取得 audience 綁定 gateway 的 token，gateway 驗證 audience。
> 2. 禁止 token passthrough：gateway 存取下游 server 時用自己的身分或經 token exchange 取得只對該下游有效、範圍更小、期限更短、記錄行動者（`act`）的 token；不能把 agent 拿來的 token 原封轉送。
> 3. 有效權限＝使用者權限 ∩ agent 權限 ∩ 任務範圍；租戶只來自已認證的身分，不來自 tool 參數。
> 4. server registry 與定義審核：每個 server 要登記擁有者與版本，tool 定義做雜湊 pin，定義變更本身觸發停用與重新審核（防 rug pull）；對外暴露的 tool 名稱加 server 前綴避免衝突；annotations 只是提示，不能拿來做安全決策。
> 5. 政策點：每次 tool call 前做確定性的政策檢查（副作用分級、deny-overrides、未登記動作預設拒絕），寫入類動作可串接核准服務；policy 不可用時寫入 fail-closed。
> 6. 回應處理：tool 輸出是不可信內容，gateway 可以做大小上限、secret 掃描與遮蔽，並標記來源讓上層 harness 判斷污染。
> 7. 狀態：依 2026-07-28 版的 stateless 設計，每個 request 自帶版本與能力，狀態放在有 id、有擁有者、有過期時間的 handle 與共享儲存，所以 gateway 可以水平擴展而不需要 sticky session。
> 8. 稽核：append-only、hash chain、記錄被拒絕的嘗試；trace 以 W3C traceparent 串接，但它可被偽造，不是安全邊界。
>
> **常見陷阱**：把 gateway 當成單純的反向代理；只精簡 tool 清單、背後仍用全權限的服務帳號；相信第三方 server 自己宣告的 annotations。
>
> **加分點**：區分協定錯誤與 tool 執行錯誤（`isError` 回填給模型當觀察）；說明 deferred loading 是 context 管理而不是權限控制，權限永遠在 dispatch 時檢查；為不支援某 extension 的 host 準備退路。
>
> **對應章節**：第 13、14、31、32、33、36 章。

> [!note] 2026 現況
> 截至 2026 年 10 月，MCP 的目前版本是 2026-07-28 版：拿掉 initialize handshake 與 session 標頭改成 stateless、新增 `server/discover`、以 multi round-trip requests 取代 server 主動向 client 發問、Tasks 移到官方 extension；授權規格要求 server 實作 Protected Resource Metadata、client 帶 resource indicator，並禁止 token passthrough。託管平台也提供 MCP gateway 類服務，例如 Amazon Bedrock AgentCore 的 Gateway 能把既有 API 轉成 MCP tools，並在每次 tool call 前做政策攔截。各服務的細節與限制以官方文件為準，面試中當例子即可。

> [!question]- E6. 設計一個 agent eval 平台：讓公司內多個 agent 團隊定義任務、跑評估、比較版本，並當成發布閘門。
> **考什麼**：task、trial、grader、harness 的資料模型；環境可重建；非決定性與統計；grader 的校準；和 CI／發布流程的整合。
>
> **答題框架**：釐清使用者與用途（開發中迭代、發布閘門、線上監控）→ 資料模型 → 執行架構 → grader 體系 → 統計與報表 → 治理與營運。
>
> **參考答案要點**：
> 1. task 不只是 prompt，而是 prompt、初始環境與成功條件的組合；每個 trial 從乾淨、可重建的環境開始（資料庫快照、假的外部服務、使用者模擬器）。
> 2. grader 選擇順序：能用程式判斷就用程式（查環境最終狀態、claim 檢查），不行才用 LLM-as-judge，人負責校準與發現新問題；trajectory 斷言只描述不變式（例如「寫入前必須查訂單」），不逐步比對參考路徑。
> 3. 非決定性：每題跑多次，面向使用者的任務報告 pass^k，有驗證器、可多試再挑的任務報告 pass@k；以題目為抽樣單位做配對比較，報告 bootstrap 信賴區間。
> 4. 題目生命週期：從真實失敗與 error analysis 建立；capability 題穩定通過後畢業進 regression suite；dev 與 held-out 分開，避免自己污染自己。
> 5. 發布閘門同時看整體差距、regression 題逐題結果、安全違規次數與成本，任何一項退步都擋下。
> 6. 執行：大量 trial 平行跑，要有自己的模型配額與成本帳，不能和 production 搶配額；結果連回 trace，失敗可以一鍵重現成 ScriptedModel 劇本。
> 7. judge 要版本化並和人工標註校準，看 kappa 與抓錯率；換 judge 模型或改 rubric 後重新校準。
>
> **常見陷阱**：只看平均成功率；只評主模型不評 fallback 模型；用「和標準 trajectory 一模一樣」當成功；幾十題就宣稱 2 個百分點的進步。
>
> **加分點**：說明信賴區間大約和題數的平方根成反比；提出 eval 成本也要編進預算（pass^k 讓每次改版的 eval 成本變成 k 倍）；線上抽樣 eval 與離線 eval 共用 grader。
>
> **對應章節**：第 27、28、29、30、34 章。

> [!question]- E7. 設計一個託管的 code execution sandbox 服務，供多個租戶的 agent 執行模型產生的程式。
> **考什麼**：隔離層級的選擇與理由；資源限制；egress 與 secrets；生命週期與 warm pool 容量；多租戶的 noisy neighbor。
>
> **答題框架**：威脅模型（誰寫的程式、誰會受害）→ 隔離層級 → 資源與檔案系統 → 網路與憑證 → 生命週期與 pool → 容量估算 → API 與營運。
>
> **參考答案要點**：
> 1. 前提：模型產生的程式一律當不可信程式，因為它會被 context 中的任何內容影響。多租戶執行不可信程式，不應停在共用 host kernel 的 process 或 container 層，選 gVisor 或 microVM。
> 2. sandbox 要提供六個獨立保證：保護服務、host 與其他租戶、憑證、資料、外部世界與下一個任務。
> 3. 資源：CPU 時間與 wall clock 兩種上限都要有，用 cgroup 或 VM 限制整組資源；執行器要回報每項限制是否真的生效，平台不支援時明確警告。
> 4. 檔案系統：只放這次任務需要的輸入並唯讀掛載，寫入只落在可整個丟棄的地方；匯出檔案經過大小與類型檢查。
> 5. 網路：egress 在網路層預設拒絕，sandbox 唯一能到達的是 proxy；allowlist 等同授權，要細到 host、方法與路徑。secrets 不進 sandbox，由 credential proxy 在邊界外注入，sandbox 只拿短效 session token。
> 6. 生命週期：用完即銷毀，不跨任務、不跨租戶重用；warm pool 裡是尚未使用的乾淨實例；長任務用 snapshot、閒置 TTL 與租期上限。
> 7. 容量：並行數用 Little's law（到達率 × 持有時間）估平均，用 Poisson 分位數估 p99；warm pool 大小約為到達率 × 開機時間，再加尖峰緩衝；每租戶有並行上限與排隊。
>
> **常見陷阱**：在 agent 服務的 process 裡 `exec`；以為限制 builtins 就安全；只依平均並行數配置；為了省開機時間重用 sandbox。
>
> **加分點**：區分「受限執行器只讓行為可預期，不是安全邊界」；提出 sandbox 回應中回顯的 secret 也要遮蔽；說明 build vs buy 時要比較隔離層級、冷啟動、snapshot 與資料駐留。
>
> **對應章節**：第 13、17、32、33、36 章。

> [!question]- E8. 設計一個 browser agent：替客服人員在沒有 API 的物流商網頁後台查件、改派送地址。
> **考什麼**：什麼時候才該操作畫面；觀察與動作的選擇；等待、驗證與重試；不可逆動作的「結果不明」；登入與 CAPTCHA 的原則；人工接手。
>
> **答題框架**：先問能不能往上走（API、結構化工具）→ 觀察與動作空間 → loop 與驗證 → 動作清冊 → checkpoint 與接手 → 安全 → 成本與延遲。
>
> **參考答案要點**：
> 1. 同一個意圖可以在 API、網站結構化工具、accessibility tree、截圖座標四個層級完成，越往下越通用也越貴、越脆弱；能往上走就不要往下走，先確認物流商真的沒有 API。
> 2. 觀察以 accessibility tree 為主，必要時才截圖；用晚綁定讓模型指名元素、由 harness 在動作當下重新定位，抵抗頁面跳版；必須用座標時點擊前做 hit-test。
> 3. 等待以條件為準並有逾時上限；每個動作宣告預期結果並由 harness 在環境中驗證，模型說「我點了」不算完成。
> 4. 動作清冊：查件是 read，L4；改派送地址是對外、可能不可逆的動作，L3，由客服在確認畫面看到 harness 讀回的真實參數後核准。
> 5. 不可逆動作驗證失敗時進入「結果不明」：先查證（重新讀取該筆貨件），查不到才交給人，不直接重試。
> 6. 憑證不進 context，由 harness 注入登入狀態；遇到 CAPTCHA 交給人，不嘗試解或繞過；網頁內容是不可信資料。
> 7. checkpoint 記錄已驗證步驟與副作用帳本，續跑時先對帳、再重新觀察、再前進。探索穩定後把常用路徑固化成腳本，降低步數與成本。
>
> **常見陷阱**：用固定 sleep 等頁面；把物流商帳密放進 prompt；把每一步的截圖都留在 context 裡。
>
> **加分點**：說明 perception–action loop 和一般 agent loop 的差異是環境自己會變；把頁面改版當成主要營運風險，用合成監測定期跑標準任務。
>
> **對應章節**：第 16、21、22、37 章。

> [!question]- E9. 設計一個公司級的 model gateway：所有 agent 的模型呼叫都經過它，要支援多家供應商、routing、配額、fallback 與成本計量。
> **考什麼**：抽象的邊界與正規化；錯誤分類、重試只留一層、熔斷；fallback 的前提；以 token 為單位的限流；計量的正確性。
>
> **答題框架**：需求（供應商、團隊數、資料駐留）→ 介面與正規化 → 請求管線 → 錯誤與韌性 → routing → 配額 → 計量與觀測。
>
> **參考答案要點**：
> 1. 上層只依賴一個 `complete()` 埠；adapter 把回應正規化成統一的 ModelResponse：`stop_reason` 四種（end_turn、tool_use、max_tokens、refusal），未知值直接報錯；usage 分成未命中快取輸入、cache 讀、cache 寫、輸出四個互斥欄位，reasoning tokens 只做參考不重複計費；原始回應保留在 `raw`。
> 2. 管線依序是配額、快取、routing、熔斷、adapter、計量；整條鏈只能有一層重試，關掉 SDK 與 HTTP 客戶端的內建重試，並設重試預算。
> 3. 錯誤分類回答三個問題：同一家重試有沒有用、換一家有沒有用、是否代表 provider 壞了；拒答不是錯誤，不能用 fallback 繞過。熔斷只計 provider 端錯誤與過慢的呼叫。
> 4. fallback 只能指向在該 release 上通過 eval、且符合租戶資料駐留限制的模型；換模型時要處理歷史轉換、能力相容與冷快取成本，備援路徑平時就要有流量。
> 5. routing：硬條件最先過濾，規則路由優先於分類器；session 內主線黏著同一模型，模型切換只發生在 compaction 這類快取本來就失效的時間點。
> 6. 限流單位是 token：月配額、租戶 token bucket、全域 bucket 三層，預留估計值、結算實際值；rate_limited（稍後再試）與 quota_exceeded（重試無用）語意不同。
> 7. 計量：在每次成功回應的當下用版本化價目表算好成本，寫進 append-only 帳本，附模型、租戶、任務、路由與 trace id，並能回填任務結果以算出每次成功任務成本。
>
> **常見陷阱**：最小公分母介面藏掉各家能力；把未知 stop reason 當 end_turn；SDK、gateway、agent 三層都重試，故障時流量相乘。
>
> **加分點**：主動提出供應商故障時除了切換，還要降 autonomy 並暫停可延後的任務；說明 cache 命中的 token 是否計入 rate limit 要向供應商確認。
>
> **對應章節**：第 3、24、25、30、36 章。

> [!question]- E10. 設計一個跨 agent 共用的核准服務：客服、coding、research 三個 agent 的高風險動作都要送到這裡等人核准。
> **考什麼**：政策引擎的輸入輸出；核准單的狀態機與逾時；綁定參數 hash；interrupt／resume 與 durable 等待；信任 UX 與 approval fatigue；稽核。
>
> **答題框架**：釐清動作種類與核准者 → 政策引擎 → 核准單生命週期 → 與 agent runtime 的整合 → UX → 稽核與營運。
>
> **參考答案要點**：
> 1. 政策引擎輸入結構化的動作與來自系統紀錄的事實（不採信模型的說法），輸出 auto／approve／deny，以及核准鏈、逾時、逾時預設、理由與政策版本；規則以 deny-overrides 合併，未登記的動作預設拒絕，destructive 至少要核准且這條寫在引擎程式碼裡。
> 2. 核准單狀態：PENDING → APPROVED／REJECTED／EXPIRED／CANCELLED；APPROVED 執行後 → EXECUTED／FAILED。依 SLA 升級，逾時預設選做錯時代價較低的一邊，不可逆的 destructive 動作不得因逾時自動執行。
> 3. 核准綁定參數 hash，執行時參數不符即拒絕；核准綁在意圖上，重試不產生第二張卡片；以核准單 id 作為 idempotency key。
> 4. 職責分離：agent 不能核准自己、轉述的核准不算數、大額動作需要兩個不同的人；step-up token 綁定單筆交易、短效、只能用一次。
> 5. 與 runtime 整合：agent 在 interrupt 時存下 messages 與 pending 的 tool call 並釋放 worker；resume 時驗證 hash、有效期與前提，把核准、拒絕或修改的結果回填成模型讀得懂的觀察。等待用 durable timer 與 signal。
> 6. UX：核准卡片的關鍵參數由程式渲染並和參照值並排，agent 的說明放在次要位置並標示為 AI 產生。
> 7. 稽核：append-only、hash chain，能回答誰提出、核准了什麼、誰以什麼權限核准、依哪一版政策、執行後發生什麼。
>
> **常見陷阱**：讓模型呼叫一個 `ask_human` tool 就當成核准閘門（閘門必須由 harness 在 dispatch 前強制）；等待期間佔著 worker；只看核准率判斷政策好壞。
>
> **加分點**：用核准率搭配修改率與事後抽查錯誤率判斷 approval fatigue；說明自動核准 classifier 只處理灰色地帶、故障時 fail-closed，不是安全邊界。
>
> **對應章節**：第 19、21、22、33、37 章。

## E.4 概念與取捨題（E11–E30）

這二十題適合當 system design 題的追問，也可以單獨成題。好的答案通常有三段：先給定義或結論，再講判斷依據與取捨，最後給一個本書中的具體例子或失敗模式。只背結論的答案在第一層追問就會露餡。

> [!question]- E11. 同一個需求，什麼時候用 workflow、什麼時候用 agent？請舉例說明你的判斷依據。
> **考什麼**：本書的定義（workflow 由程式碼決定步驟，agent 由模型在 loop 中決定下一步與何時停止）與任務適合度三問。
>
> **答題框架**：定義 → 決策樹 → 例子 → 混合設計。
>
> **參考答案要點**：依第 35 章的決策樹依序問：需要 LLM 嗎（查表或範本能解決就用 L0）；步驟能事先列舉嗎（能就用單次呼叫或 workflow，有分支與等人就用 graph）；任務是否開放、可驗證、可回復（開放決定要不要用 agent，可驗證決定能否讓它自己完成，可回復決定能給多少 autonomy）。物流查詢這種固定兩步的任務用 workflow，便宜、可預測、好測試；「我的貨到哪了？不喜歡可以退嗎？」這種步驟相依、事先列舉不完的對話才需要 agent。實際系統多半是混合：workflow 包 agent、agent 呼叫 workflow，或 agent 提議而 workflow 執行，邊界畫在副作用發生之前。
>
> **常見陷阱**：用「有沒有 tools」判斷是不是 agent；忘了延遲嚴格、量大單價低、錯誤無法驗證又代價高的任務通常不該用 agent。
>
> **加分點**：指出 trajectory 每次都走同樣幾步時那段該降級成 workflow，workflow 的分支不斷長出例外時那段該交給 agent。
>
> **對應章節**：第 1、18、19、35 章。

> [!question]- E12. 什麼時候值得用 multi-agent？面試官說「我們想把客服拆成退款、物流、問答三個 agent」，你怎麼回應？
> **考什麼**：multi-agent 的核心問題是 context 共享與決策一致性；值得的三類情況；成本倍數。
>
> **答題框架**：判準 → 套用到題目 → 替代方案 → 若真要拆該怎麼拆。
>
> **參考答案要點**：值得用 multi-agent 的是廣度搜尋、可平行、需要隔離的任務，例如研究類的 fan-out；緊耦合的寫入（多數 coding、同一段對話中相依的客服請求）應該用單一 agent，必要時加唯讀 subagent。三個專責客服 agent 的問題是：三類請求常在同一段對話出現，每次轉手都要壓縮 context、可能遺失細節，退款核准邊界也分散到多處；tool 總數只有十幾個，單 agent 完全裝得下。替代方案是單 agent 加依意圖載入的 tools 與 skills。成本上，multi-agent 的倍數由固定前綴、tool 結果大小、探索預算與 prompt caching 共同決定，要用代表性 trajectory 實測。若真的要拆（例如不同團隊擁有、使用者之後要和不同角色對話），用 handoff 並以結構化交接筆記取代完整歷史，限制交接次數，全域政策放在 Runner 層 middleware，因為掛在 Agent 上的 guardrail 在 handoff 後會失效。
>
> **常見陷阱**：「拆開比較好擴展」；忽略 agent 之間傳遞的內容也是不可信資料，轉述的核准不能取代使用者的核准。
>
> **加分點**：引用 Cognition〈Don't Build Multi-Agents〉與 Anthropic research system 兩種觀點，說明它們並不矛盾：一個講緊耦合寫入，一個講可平行的讀取。
>
> **對應章節**：第 20、23、35、40 章。

> [!question]- E13. prompt injection 怎麼防？為什麼「加一個分類器把惡意輸入擋掉」不夠？
> **考什麼**：成因、機率型與確定性防禦的區別、lethal trifecta、架構層的設計模式。只談防禦，不談攻擊手法。
>
> **答題框架**：成因 → 防禦立場 → 分層防禦 → 具體設計 → 偵測。
>
> **參考答案要點**：根本原因是模型無法依來源可靠地區分指令與資料，沒有像 parameterized query 那樣的第二個通道，所以沒有根治解法。分類器與 prompt 規則是機率型防禦，只能降低被說服的機率；對會重試的攻擊者，任何非零的漏判率最終都會被找到，「擋下 95%」在安全上不及格。所以防禦立場是假設模型會被說服，問「被說服後最多能做什麼」，並用確定性防禦限制損害：least privilege（tool、scope、憑證三層都要小）、檢查 lethal trifecta（私有資料、不可信內容、對外通訊在同一個 context 同時成立）並切掉一條腿、plan-then-execute 或 dual-LLM 讓不可信內容無法新增動作、CaMeL 式的來源與讀者標籤在 tool 呼叫前做完整性與機密性檢查、sandbox 與 egress 預設拒絕、受不可信內容影響的動作升級確認。分類器的正確位置是分流、告警與減少確認，是第二道防線。
>
> **常見陷阱**：只防使用者輸入，忘了檢索文件、tool 輸出、MCP tool 描述與 memory 都是入口；忘了 markdown 圖片渲染也是外洩管道。
>
> **加分點**：說明審查單位是 context：sub-agent 的 text 回傳會把污染帶回主 context，typed 回傳可以阻斷；提出把 trifecta 審查寫成程式放進 CI。
>
> **對應章節**：第 31、32 章。

> [!question]- E14. 長任務的 context 一定會滿。compaction 要怎麼設計，又要怎麼測？
> **考什麼**：session log 與 context 的分離、分階段 compaction、交接筆記的結構、不能交給摘要器的事實、失敗模式。
>
> **答題框架**：不變式 → 分階段手段 → 摘要格式 → 必保事實 → 測試。
>
> **參考答案要點**：不變式是 context 是 session log 的純函式：log 只追加，清除與摘要也記成事件，所以可以重建、倒帶、取回原文。第一道防線是 tool output clearing，只替換內容、不刪訊息，tool call 配對自動成立，placeholder 指出原文在哪裡；清除要批次化，因為每次清除都打斷 prompt cache。第二道防線是摘要式 compaction，切點落在 user 或 assistant 訊息之前，摘要器讀 log 原文，寫成六段固定的交接筆記：目標、使用者約束、已完成、進行中、下一步、未解問題；使用者約束逐字保留。副作用由程式記帳（進度檔），不靠摘要記住「退款做過了沒」。全部手段失效時以 thrashing 明確停止。測試分層：不變式測試、事實保留探針、端到端劇本測試、線上監控。
>
> **常見陷阱**：用更大的 context window 取代 compaction；讓摘要決定副作用狀態，導致重複退款；摘要摘要的摘要，約束一路流失。
>
> **加分點**：提出 sub-agent 是另一種 context 管理：用一個用完即丟的 context 換一份濃縮結論；把換模型的時機對齊 compaction，因為快取本來就要重算。
>
> **對應章節**：第 9、10、20、39 章。

> [!question]- E15. pass@k 和 pass^k 差在哪？客服 agent 和 coding agent 各該看哪一個？每題要跑幾次？
> **考什麼**：定義、方向、和產品體驗的對應、估計方法。
>
> **答題框架**：定義與公式 → 對應產品 → 例子 → 試驗次數。
>
> **參考答案要點**：同一題跑 k 次，pass@k 是至少一次成功的機率，pass^k 是全部成功的機率。單次成功率 p 且獨立時，pass@k ＝ 1 −（1 − p）^k 隨 k 上升，pass^k ＝ p^k 隨 k 下降。從 n 次試驗成功 c 次估計時，用組合數：pass@k ≈ 1 − C(n−c, k)／C(n, k)，pass^k ≈ C(c, k)／C(n, k)。coding agent 有測試套件，失敗的 patch 會被擋下、使用者只看到通過的那個，所以 pass@k 描述使用者體驗；客服每次對話都是真實顧客，失敗那次就是一位被誤導的顧客，所以看 pass^k。單次 75% 的客服 agent，pass^3 只有約 42%。兩個平均成功率相同的 agent，pass^k 可能差很多，因為它對失敗集中或分散很敏感。每題 3 到 5 次看穩不穩，報告 pass^3 要跑 5 到 8 次；但比每題次數更重要的是題數。
>
> **常見陷阱**：把 c/n 直接代入 p^k；以為 temperature=0 就不需要多次試驗。
>
> **加分點**：指出一題跑很多次都是 0% 時先懷疑題目壞了，每題要附參考解；說明 τ-bench 系列推廣了 pass^k。
>
> **對應章節**：第 27、28、38 章。

> [!question]- E16. 什麼是 durable execution？為什麼長時間 agent 需要它？replay 的前提是什麼？
> **考什麼**：workflow／activity 的切分、event history、determinism、至少一次與效果只發生一次。
>
> **答題框架**：失敗情境 → 原理 → 前提 → 副作用 → 等待。
>
> **參考答案要點**：長時間 agent 的第一條假設是執行它的 process 一定會在任務結束前死掉（部署、擴縮、OOM、rate limit）。durable execution 把程式切成確定性的 workflow 與不確定的 activity：對 agent 而言，loop 是 workflow，每次 model call 與 tool call 都是 activity。event history 是只追加的日誌，記錄每個 activity 的結果；恢復時重新執行 workflow 程式碼，已記錄的呼叫直接讀紀錄，不重做。前提是 workflow 的確定性：時間、亂數、外部狀態與模型回答都必須經由 activity 進入，重播時比對簽章，不一致就明確失敗；prompt 與程式碼改版是最常見的不確定來源，要事先決定版本綁定策略。activity 的保證是至少一次，因為「做完」與「記錄」之間的縫隙無法消除，所以效果只發生一次要靠冪等的 activity 與下游：idempotency key 在意圖產生時就固定（例如 `run_id:seq`），每次執行才產生的 UUID 等於沒有 key。等人核准用 durable timer 與 signal，等待期間釋放 worker。
>
> **常見陷阱**：以為 durable execution 保證恰好一次；在 workflow 裡直接讀時間或呼叫模型。
>
> **加分點**：比較三種恢復策略（重跑、快照、事件重播）的粒度；說明長任務日誌變大時的分段續跑，分段時的精簡狀態正好就是 compaction 摘要。
>
> **對應章節**：第 19、22、36 章。

> [!question]- E17. 好的 tool 長什麼樣？請用「訂單查詢」與「退款」兩個 tool 說明你的設計。
> **考什麼**：tool 是給模型用的 API（ACI）；命名、描述、參數、回傳、錯誤五個面；粒度；副作用分級。
>
> **答題框架**：心智模型 → 五個面 → 粒度 → 副作用與 harness 中間層 → 怎麼評估。
>
> **參考答案要點**：模型看不到程式碼，只讀名稱、描述與回傳，每多一次呼叫就多一輪推論與成本，所以介面要重新設計而不是沿用給工程師的 endpoint。描述寫做什麼、何時用、何時改用別的、回傳什麼；參數用 enum 與例子表達值域。粒度依任務：模型每次都照同樣順序做的讀取串接收進一個 tool（例如 `get_order` 直接附上物流狀態，少兩步），需要判斷的分岔留給模型，讀寫永遠分開。回傳以下一個決定需要什麼為準：精簡欄位、人類可讀的值、附總筆數與 cursor 的分頁。錯誤訊息可行動：發生什麼、可能原因、下一步；空結果不是錯誤。退款 tool 標為 destructive，由 harness 依等級決定核准、重試與 dry-run；idempotency key 由 harness 依意圖推導，不在 schema 裡。評估 tool 要看成功率、步數、tokens、錯誤率與副作用正確性，並讀 transcript。
>
> **常見陷阱**：把後端 API 一對一包成數十個 CRUD tool；回傳整包 JSON；錯誤只回 500。
>
> **加分點**：說明 tool 描述也是 prompt，修改要走同樣的審查與回歸流程；指出 tool 回傳大小直接放大成本公式中的 d。
>
> **對應章節**：第 5、6、13、35 章。

> [!question]- E18. 退款 tool 呼叫逾時了，agent 想再試一次。你的系統怎麼處理？
> **考什麼**：重試的來源、idempotency key 的推導與去重位置、「結果未知」的錯誤類別。
>
> **答題框架**：為什麼不能直接重試 → key 怎麼來 → 去重在哪 → 結果未知的處理 → 核准與重試的關係。
>
> **參考答案要點**：逾時代表「結果未知」，錢可能已經撥出，所以它是獨立的錯誤類別，不可直接重試 destructive 動作。agent 的重試來源包括程式、模型、人與 replay，它們都是新的 tool call，所以不能靠 call id 去重。正確做法是 harness 依業務意圖（`intent_fields`，例如訂單編號與金額）推導 idempotency key，不放進模型可見的 schema，並一路傳到真正執行副作用的那一端（金流閘道）去重；同一把 key 配不同參數要拒絕。遇到結果未知，先用同一把 key 查詢狀態或做對帳，確認沒有成功才重送；查不到就升級給人。核准綁在意圖上，重試不會產生第二張核准卡片。不支援 key 的下游，用先查再做、去重表或 outbox 補救；不可逆又無法去重的動作應經過人工核准。
>
> **常見陷阱**：每次呼叫產生新的 UUID 當 key；把 key 放進 schema 讓模型填；在 harness 層自動重試有副作用的 tool。
>
> **加分點**：連到第 22 章的事故：部署砍掉執行中的 process，排程系統從第 1 步重跑，補償優惠券發了兩輪；根因是 runner 沒有事件日誌，而且發券沒有在意圖產生時就固定的 idempotency key（例如 `run_id:seq`）。
>
> **對應章節**：第 4、5、21、22 章。

> [!question]- E19. 上線一週後，cache 命中率從 80% 掉到個位數，帳單翻倍。你怎麼排查與預防？
> **考什麼**：prompt caching 依前綴逐位元組比對的原理；cache 友善的版面；量測方法。
>
> **答題框架**：原理 → 排查步驟 → 常見根因 → 預防。
>
> **參考答案要點**：prompt caching 依前綴逐位元組比對，第一個不同的位置之後全部失效。排查時比對兩次相鄰請求的序列化前綴，找第一個不同的位置；在 trace 中記錄每一層的累積指紋，就能直接定位是哪一層變了。常見根因：有人在 system prompt 開頭放了時間戳或其他動態值（第 35 章的實驗中命中率從 85% 掉到 1%）、tool 清單順序或內容在 session 中途改變、JSON 序列化沒有排序、TTL 短於使用者回覆間隔。預防：context 依變動頻率分穩定、半穩定、動態三層，cache breakpoint 放在邊界；每次都會變的值放進 user 訊息；歷史 append-only；新 tool 只追加到清單尾端，不重排、不刪除（前綴不變式）；必須改寫前綴時批次化，集中在 compaction；CI 中加前綴一致性測試，儀表板監控命中率並告警。
>
> **常見陷阱**：用 token 總量判斷有沒有問題（總量幾乎不變，成本卻翻倍）；只看功能測試。
>
> **加分點**：說明 cache 命中率同時影響成本與 TTFT；算出命中率從 90% 掉到 50% 時青鳥的 AI 成本翻倍以上（第 35 章敏感度分析）。
>
> **對應章節**：第 3、9、13、30、35 章。

> [!question]- E20. 估算題：一個內部 IT helpdesk agent，每天 2 萬個 session，尖峰小時占一成五，每個 session 停留約 5 分鐘、平均 10 次模型呼叫，P＝5,000、d＝800、每次輸出 300 tokens，cache 命中率 80%。用示意價格（輸入每百萬 3 美元、輸出 15 美元、cache 讀 0.1 倍、寫 1.25 倍）估算每 session 成本、每日成本、並行 session 與尖峰 TPM。
> **考什麼**：成本公式的平方項、cache 的有效倍數、Little's law、尖峰而不是平均。
>
> **答題框架**：每 session token → 每 session 成本 → 每日成本 → 尖峰到達率 → 並行數 → TPM → 敏感度與結論。
>
> **參考答案要點**：
> 1. input ＝ 10 × 5,000 ＋ 800 × 10 × 9 ÷ 2 ＝ 50,000 ＋ 36,000 ＝ 86,000 tokens，平方項約占 42%；output ＝ 3,000 tokens。
> 2. 輸入有效倍數 ＝ 0.8 × 0.1 ＋ 0.2 × 1.25 ＝ 0.33；輸入成本 ＝ 86,000 × 0.33 × 3 ÷ 10⁶ ≈ 0.085 美元，輸出 ＝ 3,000 × 15 ÷ 10⁶ ＝ 0.045 美元，每 session 約 0.13 美元（無 cache 約 0.30 美元），每日約 2,600 美元。
> 3. 尖峰到達率 ＝ 20,000 × 0.15 ÷ 3,600 ≈ 0.83 個／秒；並行 session ＝ 0.83 × 300 秒 ≈ 250（Little's law，p99 再往上加）。
> 4. 尖峰主模型 QPS ≈ 8.3，平均每次呼叫 input 8,600 tokens，input TPM ≈ 4.3M，其中未命中 cache 約 0.86M；要確認供應商是否把 cache 命中的 token 計入 rate limit。
> 5. 敏感度：k 從 10 變成 14，input 變成 70,000 ＋ 72,800 ＝ 142,800，成長約 66%，比流量成長 40% 的影響更大；所以優先控制步數（合併 workflow 級 tool）與守住命中率。
>
> **常見陷阱**：用全天平均到達率（20,000 ÷ 86,400）算並行；秒與分鐘混用；只算 k × P 忘了平方項；把每次呼叫的 input 當成固定值。
>
> **加分點**：主動說「量級與敏感度排序比小數點重要」，並列出估算刻意沒算的東西（重試、eval 與 shadow 流量、compaction 呼叫、長尾 session）。E.5 節的程式重算了這些數字。
>
> **對應章節**：第 3、4、35 章。

> [!question]- E21. agent 的工具從 10 個長到 200 個，正確率下降、成本上升。你有哪些做法，怎麼選？
> **考什麼**：tool registry、tool search 與 deferred loading、Skills 漸進揭露、code-as-action 的取捨與安全限制。
>
> **答題框架**：問題成因 → 三個機制 → 選擇依據 → 安全邊界。
>
> **參考答案要點**：tool 定義放在每一輪都送出的前綴，數量的成本是每一輪、每個 session 都付，而且稀釋模型選擇 tool 的注意力。第一個機制是 tool registry 加 deferred loading：把「系統有哪些能力」和「這一輪看得到哪些能力」分開，大多數 tool 只登記不載入，模型透過常駐的 tool search 找到後才把完整定義追加到清單尾端；tool search 的召回率就是能力上限，要用評估集量 recall。第二是 Skills：程序知識用索引常駐、本體按需、附加檔案更需要時才讀的三層漸進揭露。第三是 code-as-action：讓模型寫程式在執行環境中呼叫 tools、跑迴圈與彙總，中間結果留在變數裡，在大量項目的任務上累計 input 幾乎和項目數無關；代價是需要安全的執行環境、模型看不到中間結果、副作用難以逐筆核准，所以有副作用的 tool 一律 `code_callable=False`。選擇時同時量 token、步數與正確率。
>
> **常見陷阱**：把 deferred loading 當成權限控制（權限一律在 dispatcher 依身分與副作用等級檢查）；載入新 tool 時重排清單打斷 cache；以為語言層的受限執行器是安全 sandbox。
>
> **加分點**：說明分工原則：每次都適用的規則放 system prompt，某類任務的做法放 skill，可執行的動作做成 tool，從互動學到的事實放 memory。
>
> **對應章節**：第 9、13、17 章。

> [!question]- E22. 傳統 RAG 和 agentic RAG 怎麼選？多租戶、權限不同的文件庫要注意什麼？
> **考什麼**：檢索管線、hybrid 與 rerank、agent 主導檢索的代價、citation 驗證、權限過濾的位置。
>
> **答題框架**：定義差異 → 選擇依據 → 管線品質 → 權限 → 量測。
>
> **參考答案要點**：傳統 RAG 由程式先檢索一次再生成，延遲與成本可預測；agentic RAG 把檢索變成 agent 可反覆呼叫的 tool，模型能拆解問題、改寫查詢、依結果決定下一步，代價是延遲與成本，所以 harness 要設搜尋次數上限。單一事實型問題用傳統 RAG，需要多輪拼湊、比較或追查的問題用 agentic RAG。品質上限由 chunking 決定（依文件結構切、保留標題路徑、每個 chunk 帶 id、tenant、來源與版本）；BM25 擅長代碼與專有名詞，embedding 擅長同義改寫，用 hybrid 加 RRF 融合、cross-encoder rerank。權限過濾必須在排序之前，否則 top-k 會被看不到的文件佔滿或洩漏；租戶與受眾由 harness 填入。citation 由 harness 驗證：只能引用本次檢索結果，關鍵數字要找得到出處。檢索與生成分開量：recall@k、nDCG、MRR。
>
> **常見陷阱**：「context window 夠大就不用檢索」；檢索後才過濾權限；把檢索內容當指令。
>
> **加分點**：search tool 的結果帶 id、標題、日期與截斷標示，沒有結果時給可行動的改寫建議；說明查詢與文件必須用同一個 embedding 模型版本。
>
> **對應章節**：第 9、11、31、44 章。

> [!question]- E23. 客服 agent 的退款目前是 L3（每筆都要客服核准），核准佇列塞爆、客服開始無腦按「全部核准」。你會怎麼處理？要不要直接放到 L4？
> **考什麼**：autonomy 依動作決定、證據式放寬、approval fatigue 的量測、自動核准 classifier 的定位。
>
> **答題框架**：診斷 → 放寬的證據 → 邊界設計 → 上線與回退 → 不變式。
>
> **參考答案要點**：「全部核准」代表人已經只是在按按鈕，核准形同虛設，這比沒有核准更危險，因為大家以為有人把關。先用資料診斷：核准率要搭配修改率與事後抽查錯誤率看；高核准率、低修改率、低抽查錯誤率的區間（例如小額、老顧客、非高風險商品）是放寬的候選。放寬是一個動作、一個區間地做：把 500 元以下移到 L4，同時加每日累計上限、事後抽查與風險分數（模型產生的訊號只能加分不能減分），邊界寫在授權規則與 harness 裡，不只寫在 prompt。上線分階段，依樣本與指標推進，晉升線比降級線嚴格，嚴重事故立即降級。剩下仍需核准的單據，改善信任 UX（程式渲染的關鍵參數與參照值並排）並排班。自動核准 classifier 可以處理灰色地帶、減少人的負擔，但故障時 fail-closed，不是安全邊界。不變式：不可回復且損失無法界定的動作永遠不完全自動。
>
> **常見陷阱**：全部放到 L4 以解決人力問題；用「核准率 99%」證明政策很好；把系統整體標成某個等級。
>
> **加分點**：分清兩條軸：L3 到 L4 改的是「副作用由誰核准」，不是「路徑由誰決定」；提出零事件時只能用 rule of three 推上限，不能說錯誤率是 0。
>
> **對應章節**：第 1、21、35、38 章。

> [!question]- E24. function calling、MCP、A2A、AG-UI 各解決什麼問題？為什麼說它們不是互相競爭的標準？
> **考什麼**：每個介面連接的兩端；判斷什麼時候需要 A2A 的生命週期。
>
> **答題框架**：四條邊 → 各自的核心抽象 → 選擇判準 → 安全注意。
>
> **參考答案要點**：function calling 標準化模型與 harness 之間的格式：模型只提出呼叫請求，執行與權限都在 harness。MCP 標準化 harness 與外部能力之間的介面，把 N 個 agent × M 個系統的整合變成 N＋M 份實作；host 擁有模型與安全政策，一個 client 只連一個 server；tools 由模型控制、resources 由應用程式控制、prompts 由使用者控制。A2A 連接 agent 與另一個不透明的 agent，核心是 agent card 與 task 狀態機（含 input-required 與 auth-required 兩個中斷態）；判斷要不要用它的標準不是對方用不用模型，而是互動需不需要生命週期：會不會跑很久、會不會中途要求補件或授權、產出需不需要長期查詢。AG-UI 是 agent 後端到前端的事件串流，文字與 tool call 用開始、內容、結束三段式。四者疊在一起用：前端經 AG-UI 看到進度，agent 用 function calling 決定動作，透過 MCP 存取 ERP，再用 A2A 委託物流商的 agent 處理三天才會完成的申訴。
>
> **常見陷阱**：把 MCP 當成 agent 之間的通訊協定；相信 agent card 上的能力宣告等於授權。
>
> **加分點**：指出前端 tool 的結果等同使用者輸入，後端要以不可信資料驗證；A2A 中 task 不存在與沒有權限要回傳相同錯誤。
>
> **對應章節**：第 3、14、15 章。

> [!question]- E25. LLM-as-judge 能不能信？你會怎麼把它放進 eval 與上線閘門？
> **考什麼**：grader 的選擇順序、judge 的系統性偏誤、校準方法與指標。
>
> **答題框架**：何時用 → 偏誤 → 校準 → 營運。
>
> **參考答案要點**：能用程式判斷的就用程式（查資料庫狀態、claim 檢查），程式判斷不了的軟性維度（語氣、是否給出下一步、報告是否完整）才用 LLM-as-judge，人負責校準與發現新問題。judge 有位置偏誤、冗長偏誤、自我偏好等系統性偏誤，要用交換順序、對照樣本實際量出來，而不是假設不存在。上線前和人工標註校準，看 Cohen's kappa 與抓錯率，而不是一致率，因為正例多時一致率會虛高。rubric 要具體、可判定，必過項（事實、引用、安全）不能被平均分數掩蓋。judge 的模型與 rubric 都要版本化，換模型或改 rubric 就重新校準；judge 和被評的模型最好不同，降低自我偏好。線上抽樣 eval 可以共用同一個 judge，但每週抽樣人工複核。
>
> **常見陷阱**：讓 judge 評 agent 的自述而不是環境狀態；只報告 judge 的平均分；用同一份資料調 rubric 又計分。
>
> **加分點**：說明 judge 也可能被受評內容中的指令影響，評分輸入要當成不可信資料處理；提出把 judge 的分歧案例變成 rubric 修訂的來源。
>
> **對應章節**：第 27、29、40 章。

> [!question]- E26. 多租戶 agent 平台的隔離要做到哪些層？大租戶的大促會不會拖垮小租戶？
> **考什麼**：租戶身分的來源、逐資源的隔離決策、以 token 為單位的限流、cell 架構。
>
> **答題框架**：身分 → 資料 → 執行 → 容量 → 部署形態。
>
> **參考答案要點**：租戶只來自已認證的 session（伺服器端身分），tool 參數中不得有租戶欄位，出現時拒絕並告警，模型不能填寫租戶。隔離逐資源決定：運算可以共用，資料與身分要分開（檢索索引依租戶分片、memory key 含 tenant、租戶級加密金鑰、每租戶的 connector 憑證），執行程式碼的 sandbox 永遠不共用。別家的資源與不存在的資源回傳相同錯誤，避免探測。容量上，agent 平台的限流單位是 token 不是請求數：月配額、租戶 token bucket、全域 bucket 三層，預留估計值、結算實際值；非即時任務排隊，尖峰把簡單請求導到 workflow 或小型模型。非功能需求要寫成數字，例如單一租戶的流量不能讓其他租戶的 p95 惡化超過一定比例。部署形態上，pool 最便宜但隔離全靠程式正確，silo 對長尾小店太貴，折衷是預設 pool、大租戶或有資料區域要求的租戶放進獨立 cell。
>
> **常見陷阱**：靠 prompt 叫模型「只處理這家店」；共用一個向量索引再事後過濾；只用請求數限流。
>
> **加分點**：說明 eval 與監控都要能分租戶看，全平台平均會掩蓋某些租戶的退步；提出 trace 中帶 tenant 屬性以便事故時評估影響範圍。
>
> **對應章節**：第 12、17、33、36、42 章。

> [!question]- E27. 儀表板全綠：可用性 99.9%、錯誤率接近 0、延遲正常，但客訴說「agent 說已退款，其實沒有」。你的觀測設計哪裡出了問題，怎麼補？
> **考什麼**：靜默失敗；span status 與業務結果分開；衍生訊號；過早宣告完成的防線。
>
> **答題框架**：為什麼看不到 → trace 設計 → 偵測 → 根本修正 → 回饋到 eval。
>
> **參考答案要點**：agent 最危險的失敗是語意上的：每個 API 呼叫都回 200，回覆卻是錯的，所以只看錯誤率與延遲的監控對它沉默。trace 的 span status 只記技術成敗，業務結果另外記在自家命名空間的屬性（例如本書的 `bluebird.run.status`、`bluebird.claims`）。在寫入時萃取衍生訊號，例如「回覆中宣稱已退款」，再和退款表的實際狀態對帳，不讀原文也能查到這類失敗。線上監控分品質、可靠性、成本、安全四組，品質靠代理指標與抽樣的線上 eval，告警設在比率與趨勢上。根本修正在 harness：完成宣稱必須有終態成功或讀回確認的證據，prompt 中的「請確認」只能提高機率。除錯時沿 span 樹找第一個偏離預期的 span，把 trace 轉成 ScriptedModel 劇本重現，修正後加入 eval set，再把失敗寫成查詢估計影響範圍並主動通知受影響的顧客。
>
> **常見陷阱**：為了除錯把所有 prompt 與 tool 內容都記下（內容擷取預設關閉、PII 在匯出前遮蔽）；用 tail sampling 後的資料算錯誤率。
>
> **加分點**：說明 SLI 至少包含可信完成率、升級率區間、延遲與成本；升級率太高與太低都要告警。
>
> **對應章節**：第 29、34、37 章。

> [!question]- E28. 供應商推出新一代模型，阿哲想下週全面切換。你會怎麼做？
> **考什麼**：release 綁定、eval 閘門、harness ablation、shadow 與 canary、成本與快取的影響。
>
> **答題框架**：版本化 → 離線比較 → harness 調整 → 漸進發布 → 回滾。
>
> **參考答案要點**：prompt、model snapshot、tool 版本、policy、檢索索引與 harness 設定綁成一個不可變的 release，session 建立時綁定並在整個 session 內不變，所以切換的單位是 release 而不是一個字串。先在內部 eval 上做配對比較：整體差距、regression 題逐題結果、pass^k、安全違規次數、每次成功任務成本與延遲都要看，任何一項退步都擋下；公開 benchmark 只能當初篩。新模型常讓部分 harness 結構變得多餘，用 ablation 一次拿掉一個模組、以非劣性門檻判斷，但權限、sandbox、loop guard 與人工核准是對環境負責的元件，不參加品質 ablation。發布依序是 offline eval、shadow、canary（依品質信賴區間推進，安全指標用硬門檻立即回滾），必要時 A/B。fallback 模型也要在新 release 上重跑 eval。注意換模型會讓快取冷啟動、成本短期上升，而且 thinking 與 tokenizer 的差異會改變估算假設。
>
> **常見陷阱**：用排行榜分數做決定；只測主模型；在 session 中途切換模型。
>
> **加分點**：提出小比例 canary 統計力低，細微差異需要大量樣本或序貫檢定；說明 prompt 中補模型弱點的段落要隨升級刪減，但刪除前要確認它原本的目的有測試涵蓋。
>
> **對應章節**：第 6、25、28、30、36 章。

> [!question]- E29. 你的團隊要做第三個 agent 了，要不要自己做 framework？還是用現成 SDK 或託管 agent 服務？
> **考什麼**：先決定外包哪一層；自建的好理由；lock-in 的類型；POC 要測什麼。
>
> **答題框架**：技術堆疊分層 → 硬性限制淘汰 → harness 是否為差異化 → TCO 與 lock-in → 遷移策略。
>
> **參考答案要點**：選型的第一個問題是「哪一層要外包」：harness、編排、runtime、平台服務可以分開決定；tools 與 prompts 是業務本身，無論選什麼都要以不依賴框架的形式自己擁有。自建 framework 的好理由是多個 agent 的一致性需求（同一套 guardrail、核准、tracing），加上現成 SDK 擴充點撐不住的限制；只有一個 agent 時，抽象沒有第二個使用者可以驗證。若自建，遵守最少抽象原則：每個核心抽象保護一個不變式、有兩種以上的用法、概念在主流 SDK 間穩定（本書 `loom` 的八個核心抽象就是這樣選出來的）。託管服務分成託管 harness 與託管平台積木，只轉移基礎設施的責任，approval 政策、成功標準、資料能否送進模型仍是你的責任。POC 一定要包含不愉快的路徑：核准等待、在有副作用的 tool 前後殺 process。lock-in 分 API、狀態、行為、營運、模型五類，行為 lock-in 最隱蔽，只能靠契約測試發現；adapter 保持薄，遷移用 strangler fig 分階段。
>
> **常見陷阱**：先選框架再讓框架的範例決定架構；用 demo 的上手速度做決定。
>
> **加分點**：把決策寫成可定期重新檢視的紀錄，用加權決策矩陣攤開權重並做敏感度分析。
>
> **對應章節**：第 23、26、35 章。

> [!question]- E30. agent 的 SLO 要怎麼定？凌晨發現 agent 正在大量錯誤退款，on-call 的第一步做什麼？
> **考什麼**：agent 特有的 SLI、error budget 政策、止血手段的優先順序、事後追溯。
>
> **答題框架**：SLI → SLO 與 error budget → 止血 → 溯源與影響範圍 → postmortem。
>
> **參考答案要點**：SLI 除了可用性與延遲，至少要有可信完成率（有證據的完成，不是模型自述）、升級率區間與成本；依任務長度分桶，才看得出 context rot。告警用多視窗、多燒率：長視窗確認嚴重性、短視窗確認仍在發生。error budget 政策要事先約定：消耗到什麼程度凍結變更、降 autonomy，事故當下不需要爭論。止血優先靠降 autonomy 與回滾 release：kill switch 先把退款從 L4 降回 L3（或暫停該動作），而不是把整個 agent 關掉；再回滾到上一個 release。溯源依賴 trace 中的版本 lockfile（哪個 prompt、模型、tool、policy 版本）。影響範圍要主動對帳：用衍生訊號與退款表找出所有受影響的交易，啟動補償流程。postmortem 把失敗加進 failure taxonomy 與 regression suite，並檢查哪一層（model、harness、環境、流程）缺了確定性控制。
>
> **常見陷阱**：只有可用性 SLO；事故時第一步是改 prompt；只修觸發案例，不找其他受影響的交易。
>
> **加分點**：提到 prompt、model snapshot、tool schema、guardrail 與 autonomy 的變更都是程式變更，要依風險分級審查並保留緊急回滾的快速通道；概念層級連到 NIST AI RMF 的 Govern、Map、Measure、Manage。
>
> **對應章節**：第 29、34、36、38 章。

## E.5 白板速算：驗證估算題的數字

面試中的估算靠手算，但練習時值得用程式確認自己的公式沒寫錯。下面這段程式把第 35 章 35.12 節的公式收成一個函式，重算 E20 的 IT helpdesk agent，以及 E2 引用的背景 coding agent（第 35 章 Q3 的假設）。只用標準函式庫，可以直接執行。

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Workload:
    """白板上的假設。每一個數字在面試中都要說得出來源（trace、產品預估或猜測）。"""
    sessions_per_day: float
    peak_hour_share: float      # 尖峰時段佔全天的比例
    session_seconds: float      # 一個 session（或 task）的牆鐘停留時間
    k: float                    # 每個 session 的主模型呼叫次數
    P: float                    # 固定前綴 tokens
    d: float                    # 每次呼叫新增的歷史 tokens
    out: float                  # 每次呼叫的輸出 tokens
    hit: float                  # cache 命中率


IN_PRICE, OUT_PRICE, READ, WRITE = 3.0, 15.0, 0.10, 1.25   # 示意價格（美元／百萬 tokens 與倍數）


def whiteboard(w: Workload, peak_seconds: float = 3600) -> dict[str, float]:
    tokens_in = w.k * w.P + w.d * w.k * (w.k - 1) / 2         # 前綴重送 k 次＋歷史累積（平方項）
    mult = w.hit * READ + (1 - w.hit) * WRITE                 # 沒命中的部分寫進 cache 供下一步讀
    cost = (tokens_in * mult * IN_PRICE + w.k * w.out * OUT_PRICE) / 1e6
    no_cache = (tokens_in * IN_PRICE + w.k * w.out * OUT_PRICE) / 1e6
    lam = w.sessions_per_day * w.peak_hour_share / peak_seconds   # 尖峰每秒到達
    qps = lam * w.k
    return {
        "tokens_in": tokens_in, "square_share": (tokens_in - w.k * w.P) / tokens_in,
        "cost": cost, "no_cache": no_cache, "per_day": cost * w.sessions_per_day,
        "lam": lam, "concurrent": lam * w.session_seconds,    # Little's law：L = λW
        "qps": qps, "itpm": qps * 60 * tokens_in / w.k,
        "itpm_uncached": qps * 60 * tokens_in / w.k * (1 - w.hit),
    }


def show(name: str, r: dict[str, float]) -> None:
    print(f"── {name}")
    print(f"  每 session input {r['tokens_in']:,.0f} tokens（平方項占 {r['square_share']:.0%}）")
    print(f"  每 session 成本 ${r['cost']:.3f}（無 cache ${r['no_cache']:.3f}），每天 ${r['per_day']:,.0f}")
    print(f"  尖峰到達 {r['lam']:.3f}/s、並行 {r['concurrent']:,.0f}、主模型 QPS {r['qps']:.2f}")
    print(f"  尖峰 input TPM {r['itpm'] / 1e6:.2f}M（未命中 {r['itpm_uncached'] / 1e6:.2f}M）")


# E20：內部 IT helpdesk agent
helpdesk = whiteboard(Workload(20_000, 0.15, 300, 10, 5_000, 800, 300, 0.80))
show("E20 IT helpdesk agent", helpdesk)

# E2：背景 coding agent（第 35 章 Q3 的假設；任務集中在 10 個工作小時，所以尖峰占比 1、尖峰長度 36,000 秒）
coding = whiteboard(Workload(2_000, 1.0, 1_500, 60, 12_000, 1_500, 800, 0.90), peak_seconds=36_000)
show("E2 背景 coding agent（每個 session 是一個 task）", coding)

assert helpdesk["tokens_in"] == 86_000 and abs(helpdesk["cost"] - 0.13014) < 1e-5
assert round(helpdesk["concurrent"]) == 250
assert abs(coding["cost"] - 2.897) < 0.01 and round(coding["concurrent"]) == 83
assert coding["square_share"] > 0.75 > helpdesk["square_share"]
```

```text
── E20 IT helpdesk agent
  每 session input 86,000 tokens（平方項占 42%）
  每 session 成本 $0.130（無 cache $0.303），每天 $2,603
  尖峰到達 0.833/s、並行 250、主模型 QPS 8.33
  尖峰 input TPM 4.30M（未命中 0.86M）
── E2 背景 coding agent（每個 session 是一個 task）
  每 session input 3,375,000 tokens（平方項占 79%）
  每 session 成本 $2.897（無 cache $10.845），每天 $5,794
  尖峰到達 0.056/s、並行 83、主模型 QPS 3.33
  尖峰 input TPM 11.25M（未命中 1.12M）
```

逐段看輸出。E20 的每 session 約 0.13 美元、並行 250、input TPM 4.3M，和 E20 參考答案的手算一致；平方項占 42%，代表步數再多幾步，歷史累積就會超過前綴。E2 的平方項占 79%，這是 coding agent 和客服最大的結構差異：成本幾乎全由歷史累積決定，所以 compaction 與 subagent 隔離 context 直接砍在最大的成本來源上。另一個值得注意的數字是 E2 的無 cache 成本約 10.8 美元，是有 cache 時的 3.7 倍，長任務對 cache 命中率比客服更敏感。最後，E2 的 input TPM 是 11.25M，雖然每天只有 2,000 個任務，卻比每天 2 萬個 session 的 helpdesk 高出一倍以上，這正是面試中「容量單位是 token，不是請求數」的具體例子。

## E.6 評分 rubric 與練習方法

當面試官或自我練習時，可以用下面這張 rubric 評分。每個維度給 0–2 分，總分 16 分；本書建議資深職位以 12 分為及格線，但任何一個維度拿 0 分都值得單獨討論，因為 agent system 的事故往往就出在被跳過的那一步。

| 維度 | 0 分 | 1 分 | 2 分 |
|---|---|---|---|
| 需求釐清 | 直接畫架構 | 問了流量與延遲 | 主動問動作、風險、租戶關係與成功標準，並複述假設 |
| 量化 | 沒有數字 | 算了 QPS 或成本其中之一 | 算出 token、並行、TPM、每次成功任務成本，指出最敏感的假設 |
| autonomy 與風險 | 整個系統一個等級 | 有提到核准 | 動作清冊、副作用分級、邊界、idempotency，政策在 harness 執行 |
| 架構取捨 | 一開始就 multi-agent | 有選型但沒有替代方案 | 說明為什麼更簡單的不夠，寫出被否決的方案與代價 |
| context 與 tools | 沒提 | 提到 RAG 或 memory | context 分層與預算、cache 版面、tool 粒度與回傳上限 |
| 評估 | 「人工測一下」 | 有 eval set | 以最終狀態評分、pass^k、上線門檻、fallback 也要 eval |
| 安全 | 「加 guardrail」 | 提到 prompt injection | trifecta 檢查、有效權限交集、sandbox 與 egress、被完全誘導時的最壞情況 |
| 營運 | 沒提 | 有監控 | release 綁定、canary、降 autonomy、假設變成儀表板、成本告警 |

這張表的每一列對應 E.1 節的一個步驟。使用時有兩個提醒：第一，2 分的條件是「主動說出」，被面試官提示後才補上的只算 1 分；第二，量化與 autonomy 兩列最能區分有沒有實際上線過 agent 的經驗，評分時要特別嚴格。

```text
 第 1 週  概念題熱身：E11、E15、E17、E24（每題限時 5 分鐘口述，錄音回放）
 第 2 週  主線題：E1 完整走一次（45 分鐘），再用 E.6 rubric 自評，補讀 0 分維度的章節
 第 3 週  延伸題：E2、E3 各一次；概念題 E12、E13、E14、E16、E18
 第 4 週  平台題：E5、E6、E9、E10 擇二；情境題 E19、E23、E27、E28、E30
 之後     找人扮演面試官，對每題至少追問兩層；把答不出的追問寫進自己的題庫
```

這份練習計畫由淺入深：先用概念題建立詞彙，再用 E1 把七步驟走熟，接著換到 coding 與 research 這兩種成本結構完全不同的系統，最後練平台型與情境型題目。每一題練完都回到「對應章節」補洞，而不是只記住參考答案；參考答案要點是評分用的檢核表，面試中真正被評分的是你從需求一路推到設計的因果鏈。
