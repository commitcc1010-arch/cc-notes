---
chapter: 20
title: Multi-Agent 架構與取捨
part: 4
---

# 第 20 章　Multi-Agent 架構與取捨

> [!abstract] 本章地圖
> **核心問題**：什麼時候該把一個 agent 拆成好幾個？拆了之後，context 要怎麼分、決定由誰來做，才不會讓成本爆炸、結論互相矛盾、寫入彼此覆蓋？
>
> **你會學到**：
> - 用「控制拓撲」與「context 拓撲」兩條軸，分辨 orchestrator–subagent、supervisor、handoff、swarm、debate 五種架構，並畫出各自的資料流
> - 說清楚 multi-agent 的核心難題是 context 共享與決策一致性，並為每個邊界設計 brief 與回傳格式
> - 估算 multi-agent 的 token 成本倍數，知道前綴大小、tool 結果大小與 prompt caching 如何改變結論
> - 用 branch、worktree、lock 與三方合併隔離平行寫入，並理解文字合併抓不到的語意衝突
> - 依「廣度搜尋、可平行、需要隔離」與「緊耦合寫入」的判準，決定要不要用 multi-agent
> - 用 ScriptedModel 實作 orchestrator–subagent 與 handoff，實際量測 token 倍數，並重現與修好平行寫入的衝突
>
> **前置知識**：第 4 章（agent loop 與 messages）、第 9 章與第 10 章（context 預算、sub-agent 隔離 context）、第 18 章（orchestrator-workers 等 workflow patterns）、第 19 章（graph 與共享 state）

## 20.1 故事：五個 agent 一起寫錯的月報

青鳥科技的 Part 4 有兩個新專案：一個在 sandbox 裡修 bug、開 pull request 的內部 coding agent，一個每月自動產出營運分析的 research agent。阿哲希望月報 agent 在月初第一個工作天就交出「上個月退貨率為什麼變高」的分析，過去這份報告要兩個分析師花三天。Iris 讀了幾篇 multi-agent research system 的文章，覺得這正是平行化的好題目：物流、商品、行銷三個方向互不相干，交給三個 agent 同時查，最後再找一個 agent 寫報告。

Iris 的第一版很像一間會議室：資料 agent、物流 agent、商品 agent、行銷 agent、寫作 agent 共五個，全部放在同一個「群組對話」裡，每個 agent 發言前都讀過所有人說過的話與所有查詢結果。上線第一個月，月報準時產出，但出了兩個問題。第一是帳單：這份月報的 token 用量是單一 agent 試跑版本的好幾倍，Iris 拆帳後發現，每個 agent 每一輪都在重讀整個群組的查詢明細，五個 agent 等於把同一堆資料讀了五遍。第二個問題更麻煩：物流 agent 把退貨率定義成「退貨件數 ÷ 已出貨訂單」，商品 agent 用的是「退貨件數 ÷ 全部訂單」，兩個數字在報告裡相差將近兩個百分點，寫作 agent 把兩段都照抄進去，營運主管一眼就看出前後矛盾。

同一週，coding agent 也出了事。Iris 讓三個 coding agent 同時處理三張工單，三張都要改同一份退款設定檔 `refund_policy.cfg`：一張把自動退款上限從 500 元提高到 800 元，一張配合新金流把金額單位改成「分」，一張把退貨期改成 14 天。三個 agent 共用同一個工作目錄，各自讀檔、修改、整檔寫回。CI 全綠，合併也很順，直到客服發現小額退款的自動核准門檻根本沒變：前兩個 agent 的修改被第三個 agent 的整檔寫回蓋掉了，沒有任何人收到錯誤訊息。

老陳看完兩起事故，把問題歸成同一句話：「multi-agent 難的不是讓 agent 變多，是 context 怎麼分、決定由誰做。」月報的矛盾來自兩個 agent 各自做了「退貨率怎麼算」這個隱含決定，卻沒有共享；設定檔的覆蓋來自三個 agent 各自根據「自己讀到的版本」做決定，卻寫進同一個地方。資安的 Maya 則補上第三個問題：如果某個 subagent 讀到的網頁內容夾帶惡意指令，這段內容會不會一路傳給其他 agent，甚至被當成核准？阿哲只問了一句：「到底什麼時候值得用好幾個 agent？」

這一章就是回答這幾個問題。我們先用兩條軸把五種主流架構放進同一張地圖，再深入本章的核心論點：context 共享與決策一致性。接著逐一拆解 orchestrator–subagent、supervisor、handoff、swarm、debate 的運作與取捨，算清楚成本倍數，處理平行寫入的隔離，最後在「動手做」實際量測 token，並把設定檔被覆蓋的事故重現、用分支隔離修好。

## 20.2 從一個 loop 到多個 loop：multi-agent 的定義與兩條軸

先把名詞講清楚。**multi-agent system**（多代理系統）是指一個任務由兩個以上的 agent loop 共同完成，每個 loop 有自己的 system prompt、tools 與 messages，也就是有自己的 context。例如青鳥的月報 agent：lead 負責拆題與彙整，三個 subagent 各自查一個方向，每個 subagent 都是一個完整的第 4 章 loop。這和第 18 章的 orchestrator-workers workflow 有一條清楚的界線：workflow 的拆解與派工由程式碼決定，LLM 只是其中的步驟；multi-agent 的拆解、派工、何時再派、何時收尾，都由模型在 loop 裡決定。

為什麼會需要多個 loop？單一 agent 有三個天花板。第一是 **context 容量**：一個 loop 的 messages 只會越長，第 9 章講過 context rot（輸入越長，模型表現越差），研究類任務讀了幾十份文件之後，前面讀過的內容就開始被稀釋。第二是**延遲**：單一 loop 的 tool call 再怎麼平行，模型的推理仍是一步接一步，十個方向要查十輪。第三是**關注點分離**：一個 prompt 要同時處理退款規則、物流查詢與發票，條件分支多到 prompt 難以維護，tool 也多到模型開始選錯。multi-agent 用「多個乾淨的 context」解決這三件事，代價則是協調。

要比較各種架構，最有用的是兩條獨立的軸。第一條是**控制拓撲**：誰決定下一個做事的 agent？可以是中央的一個 agent（集中式），也可以是 agent 之間互相轉交或自己認領工作（分散式）。第二條是 **context 拓撲**：agent 之間看得到彼此多少東西？從「完全共享同一份對話」到「完全隔離、只交換精簡結果」是一條連續的光譜。

```text
                          context 拓撲
        完全共享（同一份對話） ◄──────────► 完全隔離（只交換精簡結果）

  集中式  ┌────────────────────────┐        ┌──────────────────────────┐
  （中央  │ supervisor             │        │ orchestrator–subagent    │
  決定）  │ 共享對話、輪流發言     │        │ lead 派 brief、收摘要    │
          └────────────────────────┘        └──────────────────────────┘

  控制                  ┌──────────────────────┐
  拓撲                  │ debate               │
                        │ 共享彼此的論點，     │
                        │ 由裁判或回合數收斂   │
                        └──────────────────────┘

  分散式  ┌────────────────────────┐        ┌──────────────────────────┐
  （agent │ handoff                │        │ swarm／team              │
  互相    │ 控制權連同歷史一起交出 │        │ 共享任務板，context 隔離 │
  轉交）  └────────────────────────┘        └──────────────────────────┘
```

這張圖由左上到右下讀。左上的 supervisor 由中央決定誰發言，所有人共享同一份對話，資訊完整但 context 會膨脹得很快，Iris 的五人會議室就是這一格。右上的 orchestrator–subagent 同樣由中央決定，但每個 subagent 從乾淨的 context 開始，只拿到 lead 寫的任務說明，只交回精簡結論。左下的 handoff 是分散式控制：目前的 agent 自己決定把控制權交給誰，交接時通常把對話歷史一起帶過去。右下的 swarm 也是分散式，agent 從共享任務板上自己認領工作，彼此透過檔案或訊息溝通，context 各自隔離。debate 放在中間，因為它刻意讓 agent 看見彼此的論點，再用裁判或固定回合數收斂。

| 架構 | 控制拓撲 | context 拓撲 | 誰做最終決定 | 典型用途 | 主要風險 |
|---|---|---|---|---|---|
| orchestrator–subagent | 集中：lead 派工 | 隔離：brief 進、摘要出 | lead | 廣度研究、平行調查、唯讀探索 | brief 寫不清楚、摘要遺漏關鍵事實 |
| supervisor | 集中：中央路由 | 多半共享對話 | supervisor 或最後發言者 | 多專長客服、多步驟審核 | context 膨脹、路由抖動 |
| handoff | 分散：agent 互相轉交 | 交接時帶走歷史（可過濾） | 目前持有控制權的 agent | 客服分流、專責流程 | 互踢皮球、交接遺失事實 |
| swarm／team | 分散：自行認領 | 隔離＋共享任務板與檔案 | 沒有單一決策者 | 大型平行工程、長時間任務 | 協調開銷、寫入衝突、品質不一 |
| debate | 集中或回合制 | 共享彼此的論點 | 裁判或共識規則 | 需要多角度檢驗的判斷 | 從眾收斂、成本倍增 |

這張表最重要的一欄是「誰做最終決定」。每一種架構的失敗模式，幾乎都可以追溯到這一欄沒有想清楚：月報的兩個退貨率定義，就是因為沒有人被指定為「定義指標的人」；設定檔被覆蓋，則是因為三個 agent 都以為自己是最後決定者。下一節就從這裡展開。

> [!warning] 常見誤解
> 「multi-agent 就是讓 agent 扮演不同角色，像一個團隊一樣合作。」角色扮演只是 prompt 的寫法，不是架構。兩個 agent 是否真的「不同」，看的是它們的 context、tools 與權限是否不同；如果五個 agent 共用同一份對話、同一組 tools，只換了一行「你是物流專家」，那更接近一個 agent 用五種語氣說話，卻要付五倍的錢。

## 20.3 核心問題：context 共享與決策一致性

agent 做的每一個動作，都隱含了一串決定。物流 agent 寫下「退貨率 14%」時，它同時決定了分母是什麼、時間範圍怎麼切、要不要排除測試訂單；coding agent 把 `AUTO_REFUND_LIMIT` 改成 800，同時假設了金額單位是「元」。Cognition 在〈Don't Build Multi-Agents〉一文中把這件事濃縮成兩條原則：第一，**共享 context**，而且要共享完整的 trace（每一步做了什麼、看到什麼），不能只共享片段訊息；第二，**動作帶著隱含的決定**，平行的 agent 看不到彼此的隱含決定，結果就會衝突。文中舉的例子是做一個 Flappy Bird 遊戲：一個 subagent 做出瑪利歐風格的背景，另一個做出風格完全不搭的鳥，兩個都各自「正確」，拼起來卻不能用。

這兩條原則和 20.2 節的 context 拓撲正好形成張力。context 越隔離，成本越低、越能平行、越不會互相污染；但隔離也代表 agent 越看不到彼此的決定，決策一致性越難保證。context 越共享，決策越一致，但每個 agent 都要讀所有東西，成本與 context rot 一起上升，最後就退化成「一個 agent 用好幾倍的價錢」。multi-agent 設計的本質，就是在這條光譜上為每一條邊界選一個位置，並且補上讓決策一致的機制。

```text
 lead 的 context（完整的使用者意圖、已做的決定、全域限制）
 ┌────────────────────────────────────────────────────────────┐
 │ 使用者：上個月退貨率為什麼從 6% 升到 9%？                  │
 │ 決定 D1：退貨率 = 退貨件數 ÷ 已出貨訂單（與財報一致）      │
 │ 決定 D2：時間範圍 9/1–9/30，排除測試店家                   │
 └───────┬─────────────────────────────────────────▲──────────┘
         │ brief（壓縮：意圖＋決定＋邊界）         │ 回傳（壓縮：結論＋證據＋假設）
         │ 「調查物流；用 D1、D2；                 │ 「物流延遲貢獻約 1.5 點；
         │   80 字內結論與貢獻百分點」             │   依據 D1；未涵蓋退款中訂單」
         ▼                                         │
 subagent 的 context（乾淨的起點）                 │
 ┌─────────────────────────────────────────────────┴──────────┐
 │ brief ＋ 自己的 search 結果（數千 tokens 的明細，不外流）  │
 │ 隱含決定：哪些物流商算延遲、延遲幾天才算                   │
 └────────────────────────────────────────────────────────────┘
   ✗ 邊界上遺失的東西：lead 沒寫進 brief 的決定，subagent 只能自己猜
   ✗ 回傳時遺失的東西：subagent 沒寫進摘要的假設，lead 永遠不知道
```

這張圖是本章的核心心智模型。上方是 lead 的 context，裡面有使用者的完整意圖與已經做出的決定；下方是 subagent 的 context，它從乾淨的起點開始，只看得到 brief。兩個方向的箭頭都是**壓縮**：往下的 brief 把意圖與決定壓成幾句話，往上的回傳把數千 tokens 的明細壓成一段結論。壓縮帶來成本與隔離的好處，也帶來兩種資訊遺失：lead 忘了寫進 brief 的決定，subagent 只能自己猜，月報的兩個退貨率定義就是這樣來的；subagent 沒寫進摘要的假設，lead 永遠不會知道，最後的報告就建立在看不見的前提上。

所以解決決策一致性有三個方向，可以組合使用。第一是**把決定往上收**：會影響全局的決定（指標定義、資料格式、介面）由 lead 先做好，寫進 brief，subagent 只做局部決定。第二是**把假設往上報**：回傳格式要求列出「我採用的假設」與「我沒涵蓋的範圍」，讓 lead 能檢查是否和其他 subagent 一致。第三是**把共享的事實放到外部**：決定寫進一份所有 agent 都會讀的檔案（例如 `decisions.md` 或任務板），而不是只存在某個 agent 的對話裡。下表比較四種常見的 context 共享策略。

| 共享策略 | 子 agent 看到什麼 | 成本 | 決策一致性 | 適合 |
|---|---|---|---|---|
| 完整對話共享 | 所有人的所有訊息與 tool 結果 | 最高，隨人數與輪數成長 | 最高，但會被雜訊稀釋 | 少數 agent、短任務、緊密協作 |
| 過濾後的歷史 | 使用者訊息＋部分 assistant 訊息 | 中 | 中，取決於過濾規則 | handoff 交接 |
| brief＋摘要 | 任務說明；只回傳精簡結論 | 低 | 依賴 brief 與回傳格式的品質 | 廣度研究、唯讀調查 |
| 外部共享狀態 | 任務板、決定紀錄、共用檔案 | 低到中，讀取按需 | 中到高，需要讀寫紀律 | swarm、長時間任務 |

表中沒有一種策略在每一欄都贏。實務上的組合通常是：lead 與 subagent 之間用 brief＋摘要，全局決定另外寫進外部檔案，subagent 在 brief 中被要求「開始前先讀決定紀錄」。這也解釋了為什麼 Cognition 的批評與 Anthropic 的 research system 並不矛盾：前者反對的是「讓看不到彼此決定的 agent 平行做緊耦合的事」，後者的 subagent 做的則是彼此獨立、只讀不寫的調查，把需要一致的決定留在 lead。

> [!warning] 常見誤解
> 「只要把所有 context 都分享給每個 agent，一致性問題就解決了。」完整共享確實讓每個 agent 看得到所有決定，但它同時讓每個 agent 的 context 塞滿與自己無關的細節，context rot 會讓它更容易忽略真正重要的那一條；成本也會隨 agent 數成倍增加。共享的重點是「決定」與「假設」，不是「所有原始資料」。

## 20.4 Orchestrator–subagent：把探索外包，把決策留下

**orchestrator–subagent**（也叫 lead–subagent 或 orchestrator–worker）是目前最常見、公開資料最多的 multi-agent 架構。一個 **lead agent**（主導 agent）負責理解任務、規劃、派工與彙整；**subagent**（子 agent）是 lead 透過一個 tool 呼叫產生的獨立 agent loop，有自己的 system prompt、tools 與全新的 messages，做完後只把精簡結果當成 tool 結果交回。從 lead 的角度看，subagent 就是一個「很貴、很聰明、會花幾分鐘」的 tool，所以這個模式也常被稱為 **agents-as-tools**。例如青鳥月報的 lead 會一次發出三個 `delegate` tool call，分別調查物流、尺寸與促銷。

```text
 使用者          lead agent                 subagent 物流   subagent 尺寸   subagent 促銷
   │── 問題 ───►│                                │               │               │
   │            │ 規劃：拆三個方向，寫進 plan 檔 │               │               │
   │            │── delegate(物流, brief) ──────►│               │               │
   │            │── delegate(尺寸, brief) ───────┼──────────────►│               │
   │            │── delegate(促銷, brief) ───────┼───────────────┼──────────────►│
   │            │   （三個 tool call 同一回應，  │ search ×N     │ search ×N     │ search ×N
   │            │     runtime 平行執行）         │ 自己的 loop   │ 自己的 loop   │ 自己的 loop
   │            │◄──────────── 摘要（數十字）────│               │               │
   │            │◄──────────── 摘要 ─────────────┼───────────────│               │
   │            │◄──────────── 摘要 ─────────────┼───────────────┼───────────────│
   │            │ 彙整：檢查假設是否一致；不足就再派一輪
   │◄─ 報告 ────│
```

時序圖從左到右是時間在走。lead 先規劃，並把計畫寫到外部（檔案或 memory），因為長任務中 lead 的 context 可能被 compaction 截斷，計畫不能只存在對話裡。接著 lead 在同一則回應中發出三個 `delegate` tool call，runtime 把它們平行執行；每個 subagent 在自己的 loop 裡做好幾次搜尋，這些搜尋結果全部留在 subagent 的 context，lead 一個字都看不到。三個摘要回來之後，lead 才在自己的 context 裡做彙整：比對三份結論的假設是否一致，資訊不足就再派一輪，足夠了才回答使用者。

這個架構的好處可以拆成三點。第一，**context 隔離像 garbage collection**：subagent 讀過的幾萬 tokens 明細在它結束時就丟掉了，lead 的 context 只增加幾段摘要，第 10 章把這稱為用 sub-agent 隔離 context。第二，**平行縮短關鍵路徑**：三個方向同時查，總時間取決於最慢的那個 subagent，而不是三者相加。第三，**每個 subagent 可以有不同的設定**：較小的快速模型、較少的 tools、更嚴格的權限（例如只能讀不能寫），這讓成本與風險都更容易控制。

真正決定品質的是 **brief**，也就是 lead 交給 subagent 的任務說明。subagent 沒有 lead 的 context，它對任務的全部理解都來自 brief，就像第 4 章的模型對 tool 的全部理解都來自 schema。好的 brief 要包含四件事：目標（要回答什麼問題）、邊界（不要做什麼、範圍到哪）、已做的全局決定（指標定義、時間範圍）、回傳格式（字數上限、必須列出的假設與證據）。公開的 research system 經驗也強調，要給 subagent 明確的目標、輸出格式、tool 使用指引與邊界，否則多個 subagent 容易重複搜尋或各自誤解任務；而且投入規模要和問題複雜度相稱，簡單的事實查詢一個 agent 就夠，不需要派一整隊。

```text
 brief 的版面（lead → subagent）               回傳的版面（subagent → lead）
 ┌──────────────────────────────────────┐      ┌──────────────────────────────────┐
 │ 目標：物流是否造成 9 月退貨率上升？  │      │ 結論：某物流商延遲 2 天，        │
 │ 全局決定：退貨率 = 退貨 ÷ 已出貨     │      │       約貢獻 1.5 個百分點        │
 │           期間 9/1–9/30，排除測試店  │      │ 證據：查詢 Q1、Q2 的彙總數字     │
 │ 邊界：只用 search；不改任何資料；    │      │ 採用的假設：延遲 ≥ 2 天才算延遲  │
 │       最多 8 次 tool call            │      │ 沒涵蓋：退款處理中的訂單         │
 │ 回傳：80 字內結論＋貢獻百分點＋假設  │      │ 信心：中（樣本只有兩家物流商）   │
 └──────────────────────────────────────┘      └──────────────────────────────────┘
```

左邊的 brief 對應 20.3 節的「把決定往上收」：退貨率定義與期間由 lead 決定並寫明，subagent 不必猜。邊界那一行同時限制成本與風險，「最多 8 次 tool call」讓 subagent 不會無限探索，「不改任何資料」讓它保持唯讀。右邊的回傳格式對應「把假設往上報」：除了結論，subagent 必須列出採用的假設、沒涵蓋的範圍與信心，lead 彙整時才能發現「物流 agent 把延遲定義成 2 天、另一個 agent 定義成 3 天」這種不一致。兩邊的格式都可以寫成固定的範本，甚至用第 7 章的 structured output 強制回傳欄位。

orchestrator–subagent 的取捨也很明確。lead 是單點：它的規劃錯了，所有 subagent 都在錯的方向上努力；它的彙整漏看了矛盾，報告就帶著矛盾出去。lead 若同步等待所有 subagent，最慢的那一個就決定總延遲，公開資料也把這點列為現行設計的瓶頸。最後，subagent 之間不能直接溝通，如果物流 agent 發現的線索對尺寸 agent 很重要，只能透過 lead 轉達，這對獨立的調查不是問題，對需要協作的任務就是限制。

> [!note] 2026 現況
> 截至 2026 年 10 月，公開資料中描述最完整的 orchestrator–subagent 系統是 Anthropic 的 multi-agent research system（Engineering Blog，2025-06-13）：LeadResearcher 規劃後把計畫存進 memory，以防 context 超過上限被截斷，再平行派出 subagent；複雜查詢時 lead 一次平行開 3–5 個 subagent，每個 subagent 再平行使用 3 個以上的 tool，文中報告複雜查詢的研究時間最多縮短 90%；最後由 CitationAgent 為主張補上出處。文中報告以 Claude Opus 4 為 lead、Claude Sonnet 4 為 subagent 的系統，在內部 research eval 上比單一 Claude Opus 4 agent 高 90.2%。Anthropic 的 context engineering 文章（2025-09-29）建議 subagent 在乾淨的視窗中探索，只回傳約 1,000–2,000 tokens 的濃縮摘要。Claude Code 的 subagent 預設從空白 context 開始，fork 模式則複製目前的對話；兩種模式下 subagent 的 tool call 都不進入主 context。OpenAI 的〈A practical guide to building agents〉把這個模式稱為 manager pattern（agents as tools），OpenAI Agents SDK 以 `agent.as_tool()` 提供。

## 20.5 Supervisor：中央路由與階層

**supervisor**（監督者）架構也是集中式控制，但和 orchestrator 的重點不同。orchestrator 把一個大任務拆成多個獨立子任務，派出去、收回來；supervisor 則是一個路由者，面對一段持續進行的對話或流程，每一輪決定「現在該由哪一位專家 agent 處理」，專家處理完把控制權交回 supervisor，再由 supervisor 決定下一位。例如青鳥客服若有退款、物流、發票三個專家 agent，supervisor 會在使用者說「退款之外，發票也要重開」時，先交給退款專家，退款完成後再交給發票專家，最後由自己整理回覆。

```text
                    ┌────────────────────┐
  使用者 ◄────────► │ supervisor（路由） │ ◄── 每一輪：讀對話，選下一位或結束
                    └───┬──────┬──────┬──┘
          控制權交出 ▼  │      │      │  ▲ 控制權交回（附結果）
              ┌─────────┴┐ ┌───┴──────┐ ┌┴────────────────┐
              │ 退款專家 │ │ 物流專家 │ │ 帳務 supervisor │  ◄── 第二層
              └──────────┘ └──────────┘ └──┬────────┬─────┘
                                           ▼        ▼
                                     ┌──────────┐ ┌──────────┐
                                     │ 發票專家 │ │ 對帳專家 │
                                     └──────────┘ └──────────┘
```

圖中最上方的 supervisor 與使用者對話，每一輪讀取目前的對話狀態，選出下一位專家，或決定結束。專家做完事後，控制權一定回到 supervisor，這是 supervisor 和 handoff 最大的差別：handoff 把控制權永久交出去，supervisor 則一直握有主導權。右下角是**階層式 supervisor**：當專家多到一個 supervisor 難以選對時，可以把相關的專家收成一組，由第二層 supervisor 管理，第一層只需要決定「這是帳務問題」。這和組織圖很像，也和組織圖有同樣的問題：層數越多，資訊在每一層轉述時遺失得越多，延遲也越長。

supervisor 最常被問的設計題是：專家看得到多少對話？如果每位專家都看到完整對話，決策一致但成本高，而且專家容易越界處理別人的事；如果只看到 supervisor 轉述的指令，就回到 20.3 節的 brief 問題。另一個常見問題是**路由抖動**：supervisor 在兩位專家之間反覆切換，因為兩邊都說「這不完全是我的範圍」。對策和第 4 章的重複偵測同理：限制每個專家的連續轉入次數，超過就交給真人或交回 supervisor 直接處理。

和 orchestrator–subagent 相比，supervisor 適合「同一段對話中依序需要不同專長」的情境，orchestrator 適合「一個大問題可以拆成平行的小問題」的情境。兩者在實作上很接近，都可以用「專家 agent 包成 tool」完成：差別在於 supervisor 的 tool 結果通常是專家對使用者說的話或做完的動作，而 orchestrator 的 tool 結果是給 lead 讀的摘要。第 19 章的 graph runtime 也很適合表達 supervisor：supervisor 是一個節點，專家是其他節點，條件邊由 supervisor 的路由決定。

> [!note] 2026 現況
> 截至 2026 年 10 月，多數主流框架都提供某種中央路由的 multi-agent 形式，但名稱與細節各異：LangGraph 生態中有 supervisor 形式的多 agent 編排（細節未經本書查證，請以官方文件為準）；Microsoft Agent Framework 列出 Sequential、Concurrent、Handoff、Group Chat 與源自 Magentic-One 的 Magentic 等內建編排（依 release 與文件整理，部分細節未經查證）；Google ADK 以 sub-agents、`AgentTool` 與 workflow agents 組合多 agent。第 26 章會比較各框架的抽象。

## 20.6 Handoff：把控制權交出去

**handoff**（交接）是分散式控制的代表：目前負責的 agent 判斷「這件事該由別人處理」，就把控制權連同對話交給另一個 agent，之後由新的 agent 直接面對使用者，原本的 agent 不再參與，除非再被交回來。最典型的例子是客服分流：分流 agent 先查清楚使用者要什麼，判斷是退款問題，就交給退款專責 agent；退款 agent 處理完，若使用者又問發票，可能再交給帳務 agent。這和真實客服中心的轉接一樣，差別只在每一位「專員」都是一個 agent loop。

實作上，handoff 通常被設計成一種**特殊的 tool call**。分流 agent 的 tool 清單中有 `transfer_to_refund`、`transfer_to_billing` 這類 tool，模型呼叫它，就等於說「交給退款專員」；runner 看到這個呼叫，不去執行任何外部動作，而是把「目前的 active agent」換成目標 agent，下一輪用目標 agent 的 system prompt 與 tools 呼叫模型。這個設計的好處是路由決定交給模型（它最懂使用者意圖），而執行交接的機制留在程式（保證交接一定合法、一定被記錄）。

```text
                        transfer_to_refund
   ┌──────────┐ ─────────────────────────► ┌──────────┐
   │  triage  │                            │  refund  │ ── 完成 ──► end_turn（回覆使用者）
   │ （分流） │ ◄───────────────────────── │ （退款） │
   └────┬─────┘     transfer_to_triage     └────┬─────┘
        │ transfer_to_billing                    │ 需要核准的退款
        ▼                                        ▼
   ┌──────────┐                            ┌──────────┐
   │  billing │ ── 完成 ──► end_turn       │  human   │（第 21 章的 escalation）
   │ （帳務） │                            │ （真人） │
   └──────────┘                            └──────────┘

   交接時決定：(1) 帶走哪些歷史  (2) 附上什麼交接筆記  (3) 這是第幾次交接
   不變式：任何時刻只有一個 active agent；交接次數超過上限就轉真人
```

把 handoff 看成狀態機最清楚：每個 agent 是一個狀態，`transfer_to_*` 是轉移，`end_turn` 是終止狀態，轉真人是第 21 章會詳談的 escalation。圖下方列出每一次交接都要做的三個決定。第一，帶走哪些歷史：完整歷史讓新 agent 看到前面所有 tool 結果，但也帶來前一個 agent 的 system 指令殘影與無關細節；過濾後的歷史比較乾淨，卻可能丟掉關鍵事實。第二，交接筆記：前一個 agent 在 `transfer_to_*` 的參數中寫下「B-1042 已出貨，金額 1,280 元，顧客要退款」，新 agent 就不必重查。第三，交接次數：triage 與 refund 互相踢皮球是 handoff 最典型的失敗，runner 必須計數並設上限。

handoff 和 agents-as-tools 是最常被拿來比較的一對，OpenAI 的實務指南也把兩者並列為 multi-agent 的兩種基本形態（manager pattern 與 decentralized handoffs）。判斷的關鍵是「使用者之後要跟誰對話」：如果專家只是幫忙算一件事，結果要回到原本的 agent 統整，用 agents-as-tools；如果專家要接手整段對話、直接面對使用者，用 handoff。handoff 讓每個 agent 的 prompt 與 tools 都很小，容易維護與測試；代價是沒有一個 agent 對整段對話負全責，跨多次交接的對話很難追蹤「誰答應了使用者什麼」，所以每次交接都要寫進 trace（第 29 章）。

> [!warning] 常見誤解
> 「handoff 時把完整歷史帶過去最安全。」完整歷史不一定是最好的選擇。前一個 agent 的 tool 結果可能包含新 agent 不該看到的資料（例如分流 agent 查到的其他訂單），前一個 agent 的思路也可能把新 agent 帶偏。比較穩健的做法是預設帶「使用者訊息＋結構化交接筆記」，需要時再讓新 agent 自己查；20.12 節的實驗會看到，筆記寫得好時，這種做法比完整歷史更省，也更不容易遺失事實。

> [!note] 2026 現況
> 截至 2026 年 10 月，依 OpenAI Agents SDK 的公開文件，`Agent` 可以設定 `handoffs` 清單，handoff 被設計成一種特殊的 tool call，由 runner 負責切換 agent；SDK 同時提供 agents-as-tools（`agent.as_tool()`）。這個 SDK 被描述為早期 Swarm 實驗專案的後繼。LlamaIndex 的 `AgentWorkflow` 與 Microsoft Agent Framework 也提供 handoff 形式的編排。各框架預設帶過去的歷史、交接時能否過濾，細節不同，請以官方文件為準。

## 20.7 Swarm 與 team：沒有中央的協作

**swarm**（群體）指的是沒有中央指揮、agent 透過共享狀態自我協調的架構。最常見的形式是一塊**共享任務板**：任務清單放在檔案或資料庫裡，每個 agent 自己認領一個未完成的任務、做完標記完成、再認領下一個，彼此透過檔案、訊息匣或版本控制溝通。例如青鳥若要把整個後台從舊的金流 SDK 遷移到新 SDK，可能有上百個獨立的模組要改，這時與其讓一個 lead 逐一派工，不如讓十個 agent 從任務板上自己拿。

```text
 ┌───────────────────────── 共享任務板（檔案或資料庫）────────────────────────┐
 │ T-01 遷移 orders 模組      [完成 by agent-3]                               │
 │ T-02 遷移 refunds 模組     [進行中 lock: agent-1，到期 10:42]              │
 │ T-03 遷移 invoices 模組    [進行中 lock: agent-2，到期 10:45]              │
 │ T-04 遷移 reports 模組     [待認領]                                        │
 └──────▲───────────────▲───────────────▲───────────────▲─────────────────────┘
        │ 認領／回報    │               │               │
   ┌────┴────┐     ┌────┴────┐     ┌────┴────┐     ┌────┴────┐
   │ agent-1 │     │ agent-2 │     │ agent-3 │     │ agent-4 │   每個 agent：
   │ 分支 a1 │     │ 分支 a2 │     │ 分支 a3 │     │ 分支 a4 │   自己的 context
   └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘   自己的工作分支
        └───────────────┴─── 合併到 main，跑測試 ───────┴──────── 失敗就開新任務
```

圖中上方的任務板是唯一的協調點。認領時要寫入 lock（誰持有、何時到期），避免兩個 agent 做同一件事；lock 要有到期時間，否則 agent 當掉就會永遠卡住那個任務，這和分散式系統的 lease 是同一個概念。下方每個 agent 有自己的 context 與自己的工作分支，做完合併回 main 並跑測試，失敗就在任務板上開一個新的修復任務。注意這裡沒有任何 agent 負責「全局決策」，一致性完全靠三樣東西：任務切得夠獨立、共享的規範文件（程式風格、介面約定）、以及合併時的測試。

swarm 的吸引力在於擴展性：要更快，就多開幾個 agent，不必讓 lead 成為瓶頸。但公開的實驗紀錄顯示它的協調成本很真實。Cursor 公開的長時間 multi-agent coding 實驗提到，最早用「共享狀態檔加 lock」協調時，大量 agent 的吞吐量只剩少數幾個 agent 的水準，因為大家都在等 lock；改成嚴格的 planner、executor、worker、judge 分工後，又被最慢的 worker 拖住、整體太僵硬；最後收斂到遞迴的 planner 加上只回傳一份交接結果的 worker。另一個教訓是**接受小而穩定的錯誤率**：大規模平行時不要求每個 worker 都完美，而是在最後安排一輪專門讓測試轉綠的修補。

**team** 是 swarm 與 orchestrator 的折衷：有一個 lead 負責建立任務與最後彙整，但 teammate 之間可以直接傳訊息、自行從共享任務清單認領工作。和 orchestrator–subagent 相比，team 的 teammate 能協作（物流 teammate 可以直接告訴尺寸 teammate「我發現這家物流商也負責服飾類」），代價是訊息流量與 token 都隨人數成長，而且需要額外的安全規則：一個 teammate 傳來的訊息，不能被另一個 teammate 當成使用者的核准。

> [!note] 2026 現況
> 截至 2026 年 10 月的公開資料：Anthropic 的 C compiler 專案（Engineering Blog，2026-02-05）以 16 個平行 agent 開發 C 編譯器，用 `current_tasks/` 目錄中的檔案作為任務 lock，並以 GCC 作為已知正確的 oracle；Cursor〈Towards self-driving codebases〉（2026-02-05）報告峰值數百個並行 agent、約每小時 1,000 個 commit，並記錄了上述從共享 lock 到遞迴 planner 的演化。Claude Code 的 agent teams 為實驗功能（需設定 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`），包含 lead、teammates、以 file lock 協調的共享任務清單與 mailbox；文件建議 3–5 個隊友、每人 5–6 個任務，指出 token 成本隨人數線性成長，適用於研究與 review、獨立的新模組、競爭假設除錯與跨層工作，不適用於循序任務、同檔編輯與高相依的工作；teammate 之間的訊息會被標記為來自另一個 session，隊友不能代替使用者核准權限。Strands Agents 也提供名為 Swarm 的多 agent 模式。

## 20.8 Debate 與 generator–evaluator：用分歧換品質

前面四種架構都在處理「分工」，**debate**（辯論）處理的是「檢驗」。多個 agent 對同一個問題各自提出答案，接著互相閱讀、反駁、修正，經過幾個回合後由裁判 agent 或共識規則決定結論。Du 等人 2023 年的 multi-agent debate 研究報告，這種做法在數學與事實性問題上能改善單一模型的答案。工程上更常見的變形是**競爭假設**：除錯時讓三個 agent 各自持有一個假設（是快取、是時區、是競態條件），各自找證據支持自己、反駁別人，最後留下證據最強的那個。

```text
 回合 0   agent A：主因是物流延遲      agent B：主因是新尺寸表      agent C：主因是促銷
            │                            │                            │
 回合 1   讀 B、C 的論點與證據 ──────── 讀 A、C ───────────────────── 讀 A、B
          補證據：延遲訂單退貨率 14%   反駁：延遲只影響 3 成訂單    修正：促銷影響小於 0.3 點
            │                            │                            │
 回合 2   ──────────────────────── 裁判 agent ────────────────────────
          只讀「論點＋證據」，不讀推理過程；依證據強度與一致性裁定
          結論：物流（約 1.5 點）＋尺寸（約 1 點），附上仍有爭議的部分
```

這張圖說明 debate 的三個關鍵設計。回合 0 要讓每個 agent 先**獨立**作答，如果一開始就看得到別人的答案，它們很容易直接附和第一個發言者，失去多樣性。回合 1 開始共享的是「論點與證據」，不是完整的推理過程，這是刻意的 context 選擇：證據可以被檢查，冗長的推理只會增加從眾的壓力。回合 2 的裁判最好和辯論者分開，而且只看結構化的論點；固定回合數或「連續一輪沒有人改變立場」是常見的停止條件，否則辯論可以無限進行下去。

debate 的近親是 **generator–evaluator**（產生者與評估者分離）：一個 agent 負責做，另一個調成懷疑態度的 agent 負責檢查，必要時退回重做。Anthropic 在長時間應用開發的 harness 文章中指出，agent 傾向過度稱讚自己的作品，一個獨立且調成懷疑態度的 evaluator，比讓 generator 自我批判容易做好；第 8 章的 reflection 與第 18 章的 evaluator-optimizer 都是這個想法的單 agent 或 workflow 版本。和 debate 相比，generator–evaluator 的分工更清楚，成本也更低，因為只有一個 agent 在產出。

這一類架構的價值取決於有沒有可靠的**驗證訊號**。如果答案可以被測試、編譯器或資料查詢客觀檢查，讓多個 agent 平行嘗試再用 verifier 挑選，往往比讓它們互相辯論更便宜也更可靠；debate 適合的是沒有客觀 verifier、但可以用證據比較強弱的判斷題。它的主要風險有兩個：一是從眾，同一個模型的多個副本常常有相同的盲點，三個 agent 一起錯得很有自信；二是成本，N 個辯論者跑 R 個回合，token 大約是單一 agent 的 N × R 倍以上，再加上每一輪都要讀別人的論點。

## 20.9 成本倍數：multi-agent 的 token 經濟學

阿哲的問題「什麼時候值得」，第一個要算的是錢。直覺上 multi-agent 一定比較貴，因為 agent 變多了；但第 4 章講過，單一 agent 每一步都要重讀整段歷史，累計 input tokens 接近步數的平方成長。subagent 把歷史切成好幾段短的，平方項變小了，卻多了每個 subagent 都要重讀一次的固定前綴（system prompt、tool 定義、brief）。所以成本倍數不是一個常數，而是取決於幾個量的相對大小。下表列出主要的成本來源。

| 成本來源 | 單一 agent | orchestrator–subagent | 什麼情況會放大 |
|---|---|---|---|
| 固定前綴（system＋tools） | 每次呼叫重讀一次 | 每個 agent 每次呼叫都重讀 | agent 多、system prompt 長、tool 多 |
| 歷史累積（平方項） | 所有 tool 結果都累積在同一個 context | 每個 subagent 只累積自己的結果 | tool 結果大、步數多 |
| 協調訊息 | 無 | brief、摘要、lead 的派工與彙整 | 摘要過長、多輪再派工 |
| 額外探索 | 受限於單一 context 的容量 | 每個 subagent 有自己的預算，常常探索更多 | brief 沒設上限、方向重疊 |
| prompt caching 效果 | 同一條前綴持續命中，重讀很便宜 | 每個新的 subagent 都是新的對話，前面的 cache 用不上 | cache 折扣大、subagent 數量多 |

表中最容易被忽略的是最後兩列。第一，multi-agent 的總成本往往不是因為「同樣的工作分給多人做」而變貴，而是因為每個 subagent 都有自己的探索預算，整個系統做了更多的工作；這也正是它在廣度研究上表現更好的原因。第二，prompt caching 會改變平方項的價格：單一 agent 的歷史是同一條不斷延長的前綴，重讀的部分大多命中快取，價格只有原價的一小部分；subagent 每一個都是新的對話，彼此的前綴雖然相似，卻不一定能共用快取。下面的小程式用公式把這兩個效果算出來。

```python
from __future__ import annotations


def bill(inputs: list[int], cached_price: float) -> float:
    """同一個 agent 連續呼叫：與上一次重疊的前綴以快取價計費（第一次呼叫全價）。"""
    cost, prev = 0.0, 0
    for size in inputs:
        cost += (size - prev) + prev * cached_price
        prev = size
    return cost


def single_agent(n: int, k: int, prefix: int, r: int, cached_price: float = 1.0) -> float:
    """一個 agent 依序做 n 個子任務、每個 k 步：第 j 次呼叫要重讀前面 j 份 tool 結果。"""
    return bill([prefix + j * r for j in range(n * k + 1)], cached_price)


def orchestrator(n: int, k: int, prefix: int, r: int, cached_price: float = 1.0,
                 brief: int = 150, summary: int = 300) -> float:
    """lead 兩次呼叫（派工、彙整）；每個 subagent 從「前綴＋brief」開始，只累積自己的 k 份結果。"""
    lead = bill([prefix, prefix + n * (brief + summary)], cached_price)
    sub = bill([prefix + brief + j * r for j in range(k + 1)], cached_price)
    return lead + n * sub


print("orchestrator ÷ 單一 agent（4 個子任務、各 5 步、前綴 8,000 tokens）")
for r in (200, 1_000, 3_000, 8_000):
    no_cache = orchestrator(4, 5, 8_000, r) / single_agent(4, 5, 8_000, r)
    cached = orchestrator(4, 5, 8_000, r, 0.1) / single_agent(4, 5, 8_000, r, 0.1)
    print(f"  每步 tool 結果 {r:>5,} tokens：無快取 {no_cache:.2f}　有快取（重讀 1 折）{cached:.2f}")
assert orchestrator(4, 5, 8_000, 200) > single_agent(4, 5, 8_000, 200)
assert orchestrator(4, 5, 8_000, 3_000, 0.1) > single_agent(4, 5, 8_000, 3_000, 0.1) * 0.9
```

```text
orchestrator ÷ 單一 agent（4 個子任務、各 5 步、前綴 8,000 tokens）
  每步 tool 結果   200 tokens：無快取 1.07　有快取（重讀 1 折）2.02
  每步 tool 結果 1,000 tokens：無快取 0.72　有快取（重讀 1 折）1.33
  每步 tool 結果 3,000 tokens：無快取 0.49　有快取（重讀 1 折）0.93
  每步 tool 結果 8,000 tokens：無快取 0.38　有快取（重讀 1 折）0.75
```

這段程式把「4 個子任務、每個 5 步、前綴 8,000 tokens」的任務，分別交給單一 agent 與 orchestrator 計算 input tokens，輸出是兩者的比值，大於 1 代表 orchestrator 比較貴。第一欄「無快取」顯示，只要每步的 tool 結果不太小，orchestrator 反而比較省：每步 1,000 tokens 時比值是 0.72，8,000 tokens 時只剩 0.38，因為單一 agent 的平方項太重。第二欄把「與上一次呼叫重疊的部分」以一折計價，模擬 prompt caching：同樣每步 1,000 tokens，比值變成 1.33，orchestrator 變貴了；即使每步 8,000 tokens，也只省到 0.75。結論是：在有 prompt caching 的現實世界，同樣的工作量下 multi-agent 多半更貴；只有在 tool 結果很大、單一 context 會被塞爆時，隔離 context 才同時省錢又提升品質。

這個模型刻意簡化了三件事，實務估算時要補回來。第一，它假設兩種架構做「同樣的工作」，實際上 subagent 會探索更多，倍數會再往上。第二，它沒有計算 output tokens 與推理模型的 thinking tokens，這些在 lead 的規劃與彙整中可能很可觀。第三，它沒有算延遲的價值：如果三個方向平行查能把研究時間從一小時縮成二十分鐘，對某些任務來說多付的錢是值得的。所以成本倍數不是拿來決定「用不用」的唯一依據，而是拿來回答「這個任務的價值是否撐得起這個倍數」。

> [!note] 2026 現況
> 截至 2026 年 10 月，Anthropic 的 multi-agent research system 文章（2025-06-13）報告：agent 的 token 用量約為一般 chat 互動的 4 倍，multi-agent 系統約為 15 倍；在 BrowseComp 評估中，三個因素解釋了 95% 的表現變異，其中 token 用量單獨就解釋了 80%，其餘是 tool call 數與模型選擇。文章因此把 multi-agent 定位為「在 context 限制下花更多 token 的方法」，適合價值高、可高度平行的任務。Claude Code 的 agent teams 文件指出 token 成本隨隊友數線性成長。Cognition 的 Devin Fusion（2026-06-29）則從成本面反向設計：以前沿模型為 main、便宜模型為 sidekick，各自持有快取的 context，並把切換點選在 compaction 時以避免額外的 cache 懲罰。

## 20.10 平行寫入的隔離：lock、branch、worktree 與 merge

到目前為止，大部分例子都是唯讀的：subagent 搜尋、閱讀、回報，不改任何東西。一旦 agent 要**寫入**，問題就變了。Iris 的三個 coding agent 共用同一個工作目錄，每個都「讀檔、修改、整檔寫回」，這是分散式系統裡經典的 **lost update**（更新遺失）：兩個寫入者都根據同一個舊版本做修改，後寫的蓋掉先寫的，而且沒有任何人收到錯誤。agent 讓這個問題更嚴重，因為 agent 寫入前不會主動檢查檔案在它讀取之後是否被改過，而且它會根據讀到的內容做隱含決定，例如「金額單位是元」。

處理平行寫入有幾種隔離層級，從最保守到最有彈性如下表。

| 隔離機制 | 怎麼運作 | 能防止 | 防不了 | 代價 | 公開的例子 |
|---|---|---|---|---|---|
| 序列化 | 有副作用的動作一次只讓一個 agent 做 | 所有寫入衝突 | 無（但失去平行） | 吞吐量 | 多數 coding agent 的 subagent 預設唯讀 |
| lock／lease | 寫入前取得資源的鎖，有到期時間 | 同時寫同一資源 | 根據過期資訊做的決定 | 等待、鎖競爭 | C compiler 專案的任務 lock 檔 |
| branch／worktree | 每個 agent 在自己的分支或工作目錄修改，完成後合併 | lost update、互相干擾 | 語意衝突（文字合併成功但意義錯） | 合併成本、衝突處理 | 每個 worker 一份 repo 副本、git worktree |
| 版本化文件＋合併 | 文件模型支援分支與合併，衝突交給 orchestrator | 同上，適用於非程式碼文件 | 同上 | 需要自建版本模型 | Harvey 的 versioned document model |
| 唯讀 subagent＋單一寫入者 | subagent 只回報建議，只有 lead 寫入 | 所有寫入衝突 | lead 的判斷錯誤 | lead 成為瓶頸 | Cognition 推薦的單執行緒寫入 |

表格由上往下，平行度越來越高，需要的合併能力也越來越強。序列化最安全，但等於放棄平行；lock 讓不同資源可以平行，但同一資源仍要排隊，而且大量 agent 搶同一把鎖時吞吐量會崩，這正是 20.7 節 Cursor 實驗的教訓。branch 與 worktree 是 coding agent 的主流解法：**git worktree** 讓同一個 repo 同時有多個工作目錄，每個目錄對應一個分支，agent 各自在自己的目錄裡改檔、跑測試，彼此完全看不到對方的半成品；做完再由 orchestrator 或 CI 合併。最後一列是另一個方向：乾脆不讓 subagent 寫，所有寫入集中在 lead，這也是 Cognition 認為 Claude Code subagent 設計得好的原因。

```text
 base（main 上的版本 v0）
   │
   ├──► 分支 A（worker A 的 worktree）：AUTO_REFUND_LIMIT 500 → 800
   ├──► 分支 B（worker B 的 worktree）：CURRENCY_UNIT TWD → CENTS，LIMIT 500 → 50000
   └──► 分支 C（worker C 的 worktree）：RETURN_WINDOW 7 → 14，新增 MAX_PARTIAL_REFUND = 300
                    │（三個 worker 都根據 v0 做決定，彼此看不到）
                    ▼
 orchestrator 依序合併到 main，每次合併後跑測試
   (1) 合併 A：只有 A 改 → 直接採用                       → 測試通過
   (2) 合併 B：LIMIT 兩邊都改且不同 → 文字衝突             → orchestrator 理解兩個意圖後裁決
   (3) 合併 C：沒有文字衝突 → 但測試失敗（300 分 = 3 元）  → 退回 C，在最新 main 上重做（rebase）
                    ▼
 main：LIMIT = 80000（800 元，以分表示）、CENTS、14 天、MAX_PARTIAL_REFUND = 30000
```

這張資料流圖就是 20.12 節第三個實驗的劇情，值得一步步看。三個分支都從同一個 base 長出來，三個 worker 各自根據 v0 做決定，彼此看不到，這正是 Cognition 說的「動作帶著隱含的決定」。合併 A 最簡單，只有一邊改。合併 B 出現**文字衝突**：A 把上限改成 800、B 把它改成 50000（500 元乘 100），兩個意圖都對，但不能同時成立，這時必須由一個看得到兩個意圖的角色裁決，正確答案是 80000（800 元以分表示），任何一邊直接覆蓋都是錯的。合併 C 最隱晦：文字上完全沒有衝突，C 新增的 `MAX_PARTIAL_REFUND = 300` 卻是根據「單位是元」這個已經過時的假設寫的，合併後代表 3 元。只有根據需求寫成的測試能抓到這種**語意衝突**，修法是把 C 退回去，讓它在最新的 main 上重做。

這張圖帶出三個設計原則。第一，**隔離解決的是互相干擾，不是一致性**：branch 讓每個 agent 的工作不會被別人蓋掉，但不會讓它們的決定變得一致，一致性要靠合併時的裁決與測試。第二，**衝突是訊號，不是錯誤**：文字衝突代表兩個 agent 對同一件事做了不同決定，正確的處理是交給看得到全局的 orchestrator 或真人，而不是自動選一邊。第三，**合併順序與 rebase 很重要**：每次合併後都要跑測試，失敗時讓 worker 在最新的 main 上重做，它就能看到別人已經做的決定。這和人類團隊用 pull request、code review 與 CI 協作是同一套紀律，只是 agent 的速度更快、數量更多，紀律更不能省。

非程式碼的寫入也適用同樣的原則。資料庫寫入可以用 optimistic concurrency（寫入時帶上讀取時的版本號，版本不符就拒絕），外部 API 的副作用要用第 5 章的 idempotency key，文件類產出可以像 Harvey 一樣為文件建立版本模型。真正無法隔離的副作用（寄信給顧客、真的退款）則不應該讓多個 agent 平行做，應該集中在單一寫入者，必要時加上第 21 章的人工核准。

## 20.11 什麼時候值得用 multi-agent

把前面幾節收斂成判準。multi-agent 值得的情況有三類。第一是**廣度搜尋**：問題可以拆成多個獨立的方向，每個方向都需要大量閱讀，例如月報的物流、尺寸、促銷三條線；單一 agent 的 context 裝不下所有原始資料，subagent 隔離 context 讓每個方向都能讀得夠深。第二是**可平行**：子任務之間沒有相依，平行執行能明顯縮短延遲，而延遲對使用者有價值。第三是**需要隔離**：子任務需要不同的權限或 tools（讀取不受信任網頁的 subagent 不該擁有寫入權限），或子任務的雜訊會污染主 context（讀一萬行 log 找錯誤）。

不值得的情況同樣清楚。最典型的是**緊耦合的寫入**：大多數 coding 任務都是這一類，改一個函式的簽名會牽動呼叫端、測試與文件，每一步的決定都依賴前一步，拆給平行的 agent 只會製造 20.10 節的衝突。Anthropic 的 research system 文章也明說，這種架構不適合高度相依的任務，例如大多數 coding。其他不值得的情況包括：任務本身很小（一個 agent 三步就能做完）、子任務需要頻繁交換中間結果（溝通成本超過平行的收益）、以及任務價值撐不起成本倍數。

```text
 任務進來
   │
   ├─ 單一 agent 做得到、品質夠嗎？ ── 是 ──► 用單一 agent（先把 tools 與 prompt 做好）
   │   否
   ├─ 能拆成彼此獨立的子任務嗎？ ── 否 ──► 單一 agent＋compaction（第 10 章）
   │   是                                   或唯讀 subagent 只做查詢
   ├─ 子任務要寫入共享資源嗎？
   │     是 ─► 能隔離嗎（branch、worktree、版本化文件）？
   │             否 ─► 序列化寫入：subagent 只建議，lead 單一寫入
   │             是 ─► 平行寫入＋合併時裁決衝突＋測試
   │     否 ─► 唯讀平行：orchestrator–subagent
   ├─ 使用者要和不同專長的 agent 對話？ ── 是 ──► handoff 或 supervisor
   └─ 沒有客觀 verifier、需要多角度檢驗？ ── 是 ──► generator–evaluator，必要時 debate
   最後一關：任務價值 ≥ 成本倍數 × 單一 agent 成本？ 否 ──► 退回單一 agent
```

這張決策圖的第一關最重要：先問單一 agent 是否做得到。OpenAI 的實務指南給的建議是先把單一 agent 的能力用到極限，只有在 prompt 的條件分支多到難以維護、或 tools 重疊到模型經常選錯時才拆。第二關問能不能拆成獨立子任務，不能就留在單一 agent，用 compaction 管理長任務，或只派唯讀的 subagent 做查詢。第三關是本章的重點：有寫入時，能隔離就平行寫入並在合併時裁決，不能隔離就序列化。後兩關處理對話型與檢驗型的需求。最後一關是阿哲的問題：把 20.9 節的成本倍數乘上去，任務價值撐不起就退回單一 agent。

multi-agent 還有一個常被低估的成本：**失敗模式變多**。研究者整理多個 multi-agent 框架的執行紀錄，提出 MAST 失敗分類，其中一整類是 agent 之間的錯位：對話被重置、沒有要求澄清、偏離任務、隱瞞資訊、忽略其他 agent 的輸入、推理和行動不一致；另一類是驗證問題：過早終止、驗證不完整或驗證錯誤。第 34 章會完整介紹這個分類。研究者的結論之一是，很多失敗靠更好的系統設計（清楚的角色、終止條件與驗證器）就能改善，不一定要換更強的模型。

最後是 Maya 的問題：安全。multi-agent 讓第 31 章的 prompt injection 多了傳播路徑：讀取網頁的 subagent 被惡意內容影響，它的摘要會被 lead 當成可信的工作成果，lead 再把它寫進其他 subagent 的 brief。第 31 章會把這件事說得更精確：審查的單位是 context，一個 context 只要讀過不可信內容就視為受污染，subagent 以自由文字回傳時，污染會跟著回到 lead 的 context；改用結構化、受驗證的 typed 回傳（例如只允許固定欄位與型別），才能在邊界上阻斷。對策是把 agent 之間傳遞的內容一律當成不可信輸入：subagent 的摘要只是資料，不是指令；一個 agent 轉述的「使用者已同意」不能取代真正的核准；權限依 subagent 的任務最小化，讀外部內容的 subagent 不給寫入工具。agent 是用自己的身分還是繼承使用者的權限，第 33 章會詳談；公開資料中，Anthropic 也把 multi-agent 之間的信任升級與 agent identity 列為仍待解決的問題。

> [!note] 2026 現況
> 截至 2026 年 10 月：Cognition 的〈Don't Build Multi-Agents〉（Walden Yan，2025-06-12）建議以單執行緒、線性的 agent 為預設，超長任務再加上專門壓縮歷史的模型，並認為 Claude Code 的 subagent 設計得好，是因為 subagent 不和主 agent 平行寫入、通常只回答界定清楚的問題；作者對 multi-agent 的長期發展仍表示樂觀。Cognition 之後推出的 Devin Fusion（2026-06-29）採 main＋sidekick 架構，關鍵決策仍留在主 agent，公開文章也記錄了它的失敗情境：當「判斷本身就是交付物」的困難功能被委派出去時，細微的意圖容易遺失。Harvey 重建 Playbook Review（2026-09-02）時比較了規則式 workflow、單一 agent 與 orchestrator＋subagents，最後選擇後者：子 agent 各在版本化文件模型的分支上工作，衝突交給 orchestrator；文中報告品質指標明顯提升，平均延遲則從 2.6 分鐘增加到 3.8 分鐘。MAST 失敗分類見 arXiv:2503.13657。

## 20.12 動手做：orchestrator–subagent、handoff 與分支隔離

這一節用三段可以獨立執行的程式，把本章的三個核心主張變成可以量測的結果。第一段實作 orchestrator–subagent，subagent 有獨立的 context，只回傳精簡結果，並量測它相對於單次呼叫與單一 agent 的 token 倍數。第二段實作 handoff，比較三種交接策略的 token 與行為差異，並示範互踢皮球的防護。第三段重現 Iris 的設定檔事故，再用分支隔離、三方合併與測試修好它。三段都用全書統一的 ScriptedModel，token 一律以「JSON 字元數 ÷ 2」粗估，數字本身只用來比較趨勢。這三段程式也是給 loom 加上 `loom.agents` 模組（multi-agent 編排）的雛形：第 23 章會把 handoff 升格成核心抽象，agents-as-tools、交接策略與分支合併則留在 `loom.agents`，建在 Runner 之上。

### 實驗一：orchestrator–subagent 與 token 成本倍數

程式中的 `Agent` 是第 4 章 loop 的精簡版，重點是每個 `Agent` 實例都有自己的 `messages`。`delegate` tool 在被呼叫時建立一個新的 `Agent`，把 brief 當成它的第一則使用者訊息，跑完後只回傳最後的結論，subagent 的完整 transcript 留在函式內部，不會流進 lead。`Metered` 在每次模型呼叫時記帳，最後依「誰呼叫的」分類加總。實驗跑兩組參數：情境 A 的 system prompt 很長、搜尋結果很短；情境 B 相反。

```python
from __future__ import annotations

import json
import unicodedata
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


# ───────── 計量：用「字元數 ÷ 2」粗估 token，每次呼叫記一筆帳 ─────────
def est(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False, default=vars)) // 2

class Metered(ScriptedModel):
    def __init__(self, who: str, script, ledger: list):
        super().__init__(script)
        self.who, self.ledger = who, ledger

    def complete(self, messages, tools=None, system=""):
        resp = super().complete(messages, tools, system)
        resp.usage = {"input_tokens": est([system, tools, messages]), "output_tokens": est([resp.text, resp.tool_calls])}
        self.ledger.append((self.who, resp.usage["input_tokens"], resp.usage["output_tokens"]))
        return resp


class Agent:
    """第 4 章 loop 的精簡版：每個 Agent 有自己的 messages，也就是自己的 context。"""

    def __init__(self, model, tools: dict[str, Callable[..., str]], system: str):
        self.model, self.tools, self.system = model, tools, system
        self.schemas = [{"name": n, "description": (f.__doc__ or n), "parameters": {}} for n, f in tools.items()]

    def run(self, task: str, max_steps: int = 10) -> tuple[str, list[dict]]:
        messages: list[dict] = [{"role": "user", "content": task}]
        for _ in range(max_steps):
            resp = self.model.complete(messages, tools=self.schemas, system=self.system)
            messages.append({"role": "assistant", "content": resp.text, "tool_calls": [vars(t) for t in resp.tool_calls]})
            if not resp.tool_calls:
                return resp.text, messages
            for tc in resp.tool_calls:          # 平行 tool call 在這裡逐一執行；真實 runtime 可並行
                out = self.tools[tc.name](**tc.args)
                messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": out})
        return "max_steps", messages


TOPICS = {"物流": ["物流延遲 退貨", "物流商 到貨天數"], "尺寸": ["尺寸不合 退貨", "尺寸表 版本"], "促銷": ["促銷檔期 退貨", "折扣 衝動購買"]}
FINDINGS = {"物流": "物流：某物流商 9 月第 3 週起延遲 2 天，延遲訂單退貨率 14%，約貢獻 1.5 個百分點。",
            "尺寸": "尺寸：新尺寸表上線後「尺寸不合」退貨增加 30%，約貢獻 1 個百分點。",
            "促銷": "促銷：9 月檔期退貨率與平時相近，貢獻小於 0.3 個百分點。"}
QUESTION = "上個月退貨率為什麼從 6% 升到 9%？請找出主要原因。"
FINAL = "主因是物流延遲（約 1.5 點）與新尺寸表（約 1 點），促銷影響很小。"


def experiment(prefix_chars: int, rows: int) -> dict[str, Any]:
    """prefix_chars：每個 agent 的 system prompt 長度；rows：每次 search 回傳幾列明細。"""
    ledger: list[tuple[str, int, int]] = []
    system = "你是青鳥科技的營運分析 agent。" + "規則與資料字典說明。" * (prefix_chars // 10)

    def search(query: str) -> str:
        """搜尋營運資料倉儲，回傳明細"""
        return "\n".join(f"{query}｜第{w}週｜店家 S-{100 + w * 7}｜退貨 {40 + w * 3} 件｜原因碼 R{w % 4}" for w in range(1, rows + 1))

    # (1) 單次呼叫：同樣的 system prompt，沒有 tools、沒有 loop
    Metered("chat", [say("可能與物流、尺寸或促銷有關，需要資料才能確認。")], ledger).complete(
        [{"role": "user", "content": QUESTION}], system=system)

    # (2) 單一 agent：一個 context 依序做完六次搜尋
    queries = [q for qs in TOPICS.values() for q in qs]
    script = [call("search", f"c{i}", query=q) for i, q in enumerate(queries)] + [say(FINAL)]
    Agent(Metered("single", script, ledger), {"search": search}, system).run(QUESTION)

    # (3) orchestrator–subagent：lead 一次發出三個 delegate，每個 subagent 有獨立 context
    def delegate(topic: str, brief: str) -> str:
        """派一個 subagent 調查單一方向，只回傳精簡結論"""
        qs = TOPICS[topic]
        sub_script = [call("search", "s1", query=qs[0]), call("search", "s2", query=qs[1]), say(FINDINGS[topic])]
        summary, _transcript = Agent(Metered(f"sub:{topic}", sub_script, ledger), {"search": search}, system).run(brief)
        return summary                          # 完整 transcript 留在 subagent 那邊，只有結論回到 lead

    plan = ModelResponse(stop_reason="tool_use", tool_calls=[
        ToolCall(f"d{i}", "delegate", {"topic": t, "brief": f"調查「{t}」是否造成 9 月退貨率上升；只用 search；回傳 80 字內結論與貢獻百分點。"})
        for i, t in enumerate(TOPICS)])
    _, lead_msgs = Agent(Metered("lead", [plan, say(FINAL)], ledger), {"delegate": delegate}, system).run(QUESTION)

    def tally(prefix: str) -> tuple[int, int, int]:
        rows_ = [r for r in ledger if r[0].startswith(prefix)]
        return sum(r[1] + r[2] for r in rows_), max(r[1] for r in rows_), len(rows_)

    return {"chat": tally("chat"), "single": tally("single"), "lead": tally("lead"), "sub": tally("sub:"),
            "returned": [m["content"] for m in lead_msgs if m["role"] == "tool"]}


def pad(s: str, width: int) -> str:
    """中文字占兩格，補空白讓表格對齊。"""
    return s + " " * (width - sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in s))


def report(title: str, r: dict[str, Any]) -> float:
    chat, multi = r["chat"][0], r["lead"][0] + r["sub"][0]
    rows = [("單次呼叫", chat, r["chat"][2], r["chat"][1]),
            ("單一 agent", r["single"][0], r["single"][2], r["single"][1]),
            ("orchestrator", multi, r["lead"][2] + r["sub"][2], max(r["lead"][1], r["sub"][1]))]
    print(f"── {title}")
    print("   " + pad("架構", 14) + pad("總 tokens", 11) + pad("倍數", 8) + pad("呼叫數", 8) + "最大單次 input")
    for name, total, n, peak in rows:
        print("   " + pad(name, 14) + pad(str(total), 11) + pad(f"{total / chat:.1f}x", 8) + pad(str(n), 8) + str(peak))
    print(f"   lead 的最大 context {r['lead'][1]}；subagent 回傳 {[len(x) for x in r['returned']]} 字元")
    return multi / r["single"][0]


a = experiment(prefix_chars=6000, rows=8)        # 長 system prompt、小 tool 結果
b = experiment(prefix_chars=600, rows=60)        # 短 system prompt、大 tool 結果
ratio_a = report("情境 A：前綴大、tool 結果小", a)
ratio_b = report("情境 B：前綴小、tool 結果大", b)
print(f"orchestrator ÷ 單一 agent：A = {ratio_a:.2f}、B = {ratio_b:.2f}")
print(f"關鍵路徑上的循序模型呼叫：單一 agent {a['single'][2]} 次；"
      f"orchestrator {a['lead'][2]} + {a['sub'][2] // len(TOPICS)} 次（三個 subagent 並行）")

for r in (a, b):
    assert all("第1週" not in x for x in r["returned"])     # 原始明細沒有流進 lead 的 context
    assert r["lead"][1] < r["single"][1]                    # lead 的 context 比單一 agent 小
assert ratio_a > 1.2 and ratio_b < 1.0                      # 成本倍數取決於「固定前綴」與「tool 結果」的比例
```

```text
── 情境 A：前綴大、tool 結果小
   架構          總 tokens  倍數    呼叫數  最大單次 input
   單次呼叫      3060       1.0x    1       3045
   單一 agent    26853      8.8x    7       4527
   orchestrator  36986      12.1x   11      3575
   lead 的最大 context 3462；subagent 回傳 [49, 36, 31] 字元
── 情境 B：前綴小、tool 結果大
   架構          總 tokens  倍數    呼叫數  最大單次 input
   單次呼叫      360        1.0x    1       345
   單一 agent    29173      81.0x   7       7875
   orchestrator  16358      45.4x   11      2917
   lead 的最大 context 762；subagent 回傳 [49, 36, 31] 字元
orchestrator ÷ 單一 agent：A = 1.38、B = 0.56
關鍵路徑上的循序模型呼叫：單一 agent 7 次；orchestrator 2 + 3 次（三個 subagent 並行）
```

先看情境 A。單次呼叫只花 3,060 tokens，幾乎全是那段很長的 system prompt。單一 agent 做 6 次搜尋加 1 次回答，共 7 次呼叫，總量是單次呼叫的 8.8 倍。orchestrator 有 11 次呼叫（lead 2 次、三個 subagent 各 3 次），總量是 12.1 倍，比單一 agent 多了約四成（最後一行的 A = 1.38）。原因正是 20.9 節表格的第一列：每個 subagent 的每次呼叫都要重讀那段很長的前綴，前綴越大，多出來的 agent 越貴。

情境 B 的結論完全相反。前綴變短、每次搜尋回傳 60 列明細後，單一 agent 的歷史累積很快，最後一次呼叫的 input 達到 7,875 tokens，總量是單次呼叫的 81 倍；orchestrator 只有 45.4 倍，比單一 agent 省了 44%（B = 0.56），因為每個 subagent 只累積自己的兩份結果。兩個情境有三件事是不變的：lead 收到的 subagent 結果只有 31 到 49 個字元，原始明細一列都沒有流進 lead（第一個 assert 驗證）；lead 的最大 context 都比單一 agent 小；關鍵路徑上的循序呼叫從 7 次降為 5 次，三個 subagent 若真的並行執行，延遲會跟著下降。

這個實驗的重點不是「哪種比較省」，而是**倍數由結構決定**：前綴與 tool 結果的比例、subagent 的數量與步數、以及 20.9 節提到的 prompt caching。實驗中兩種架構做的是同樣的工作；真實的 research system 會給每個 subagent 更多的探索預算，倍數會再往上，這也是公開報告中 multi-agent 約為 chat 十幾倍的主要原因。要估自己系統的倍數，最可靠的方法就是像這樣用 ScriptedModel 重播代表性的 trajectory，再換成真實的 usage 數字。

### 實驗二：handoff 與交接策略

`HandoffRunner` 一次只有一個 active agent。每個 agent 的 tool 清單會自動加上 `transfer_to_<目標>`；模型呼叫它時，runner 回填一則「已轉給 X」的 tool 訊息、換掉 active agent，並依 `history` 參數決定新 agent 看到什麼：`full` 是完整歷史，`filtered` 是只保留使用者訊息，再加一則交接筆記。退款專責 agent 的劇本是一個函式：它看得到「已出貨」這個事實就直接建立退貨單，看不到就自己再查一次訂單，這模擬了真實 agent 在資訊不足時的行為。

```python
from __future__ import annotations

import json
import unicodedata
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


def est(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False, default=vars)) // 2


@dataclass
class HandoffAgent:
    name: str
    system: str
    tools: dict[str, Callable[..., str]]
    handoffs: list[str]                     # 可以把控制權交給誰
    model: ScriptedModel


class HandoffRunner:
    """同一時間只有一個 active agent；handoff 是一個特殊的 tool call，runner 看到它就換人。"""

    def __init__(self, agents: list[HandoffAgent], history: str = "full", max_handoffs: int = 3):
        self.agents = {a.name: a for a in agents}
        self.history, self.max_handoffs = history, max_handoffs
        self.tokens: dict[str, int] = {a.name: 0 for a in agents}

    def view(self, messages: list[dict], note: str) -> list[dict]:
        """新 agent 看到什麼：full＝整段歷史；filtered＝只有使用者的話＋交接筆記。"""
        if self.history == "full":
            return list(messages)
        users = [m for m in messages if m["role"] == "user"]
        return users + [{"role": "user", "content": f"[交接筆記] {note}"}]

    def run(self, user_input: str, start: str, max_steps: int = 12) -> tuple[str, str, list[str]]:
        active, path, handoffs = self.agents[start], [start], 0
        messages: list[dict] = [{"role": "user", "content": user_input}]
        for _ in range(max_steps):
            tools = list(active.tools) + [f"transfer_to_{h}" for h in active.handoffs]
            resp = active.model.complete(messages, tools=[{"name": t} for t in tools], system=active.system)
            self.tokens[active.name] += est([active.system, tools, messages]) + est([resp.text, resp.tool_calls])
            messages.append({"role": "assistant", "content": resp.text, "tool_calls": [vars(t) for t in resp.tool_calls]})
            if not resp.tool_calls:
                return "done", resp.text, path
            for tc in resp.tool_calls:
                if tc.name.startswith("transfer_to_"):
                    target = tc.name.removeprefix("transfer_to_")
                    handoffs += 1
                    messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": f"已轉給 {target}"})
                    if handoffs > self.max_handoffs:           # 防止兩個 agent 互踢皮球
                        return "handoff_loop", "已轉給真人客服。", path
                    active = self.agents[target]
                    path.append(target)
                    messages = self.view(messages, tc.args.get("note", ""))
                    break                                      # 換人之後，同一回應裡剩下的 call 不再執行
                out = active.tools[tc.name](**tc.args)
                messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": out})
        return "max_steps", "", path


def get_order(order_id: str) -> str:
    return json.dumps({"order_id": order_id, "status": "shipped", "amount": 1280, "items": ["羽絨外套"] * 3}, ensure_ascii=False)

def create_return(order_id: str) -> str:
    return json.dumps({"return_id": "R-7781", "order_id": order_id})

TRIAGE = "你是青鳥客服的分流 agent。先查訂單，再轉給對的專責 agent。" * 20
REFUND = "你是退款專責 agent。已出貨訂單要建退貨單，未出貨才退款。" * 20


def scenario(history: str) -> HandoffRunner:
    def refund_policy(msgs: list[dict]) -> ModelResponse:
        # 專責 agent 需要「訂單已出貨」這個事實；看不到就只好自己再查一次
        if any(m.get("name") == "create_return" for m in msgs):
            return say("已建立退貨單 R-7781，物流後天取件。")
        if any("shipped" in str(m.get("content", "")) for m in msgs):
            return call("create_return", "r2", order_id="B-1042")
        return call("get_order", "r1", order_id="B-1042")

    triage = HandoffAgent("triage", TRIAGE, {"get_order": get_order}, ["refund"], ScriptedModel([
        call("get_order", "t1", order_id="B-1042"),
        call("transfer_to_refund", "t2", note="B-1042 要退款")]))
    refund = HandoffAgent("refund", REFUND, {"get_order": get_order, "create_return": create_return}, ["triage"],
                       ScriptedModel([refund_policy] * 4))
    runner = HandoffRunner([triage, refund], history=history)
    status, answer, path = runner.run("B-1042 我不要了，幫我退款", start="triage")
    calls = len(refund.model.calls)
    print(f"{history:<9} status={status} path={'→'.join(path)} refund 呼叫模型 {calls} 次 tokens={runner.tokens}")
    assert status == "done" and "R-7781" in answer
    return runner


full, filtered = scenario("full"), scenario("filtered")
assert len(filtered.agents["refund"].model.calls) == 3 and len(full.agents["refund"].model.calls) == 2
assert filtered.tokens["refund"] > full.tokens["refund"]          # 交接時丟掉事實，專責 agent 只好重查

# 好的交接筆記：把關鍵事實寫進 note，filtered 也不必重查
good = HandoffRunner([
    HandoffAgent("triage", TRIAGE, {"get_order": get_order}, ["refund"], ScriptedModel([
        call("get_order", "t1", order_id="B-1042"),
        call("transfer_to_refund", "t2", note="B-1042 status=shipped 金額 1280，顧客要退款")])),
    HandoffAgent("refund", REFUND, {"create_return": create_return}, ["triage"], ScriptedModel([
        call("create_return", "r2", order_id="B-1042"), say("已建立退貨單 R-7781。")]))], history="filtered")
print(f"{'note':<9} status={good.run('B-1042 我不要了，幫我退款', start='triage')[0]} tokens={good.tokens}")

# 基準：一個 agent 擁有全部 tools 與兩份指令，不做 handoff
solo = HandoffRunner([HandoffAgent("solo", TRIAGE + REFUND, {"get_order": get_order, "create_return": create_return}, [],
                                ScriptedModel([call("get_order", "c1", order_id="B-1042"),
                                               call("create_return", "c2", order_id="B-1042"), say("已建立退貨單 R-7781。")]))])
solo.run("B-1042 我不要了，幫我退款", start="solo")
base = solo.tokens["solo"]
for name, r in [("solo", solo), ("full", full), ("filtered", filtered), ("note", good)]:
    print(f"  {name:<8} 總 tokens {sum(r.tokens.values()):>5}  ＝ {sum(r.tokens.values()) / base:.2f} 倍（相對 solo）")
assert sum(good.tokens.values()) < sum(full.tokens.values()) < sum(filtered.tokens.values())

# 互踢皮球：兩個 agent 都覺得不是自己的事
bounce = HandoffRunner([
    HandoffAgent("triage", TRIAGE, {}, ["refund"], ScriptedModel([call("transfer_to_refund", f"a{i}") for i in range(5)])),
    HandoffAgent("refund", REFUND, {}, ["triage"], ScriptedModel([call("transfer_to_triage", f"b{i}") for i in range(5)]))])
status, answer, path = bounce.run("我的發票開錯了", start="triage")
print("互踢皮球", status, "→".join(path), answer)
assert status == "handoff_loop" and len(path) == 4
```

```text
full      status=done path=triage→refund refund 呼叫模型 2 次 tokens={'triage': 1023, 'refund': 1443}
filtered  status=done path=triage→refund refund 呼叫模型 3 次 tokens={'triage': 1023, 'refund': 1694}
note      status=done tokens={'triage': 1035, 'refund': 968}
  solo     總 tokens  2633  ＝ 1.00 倍（相對 solo）
  full     總 tokens  2466  ＝ 0.94 倍（相對 solo）
  filtered 總 tokens  2717  ＝ 1.03 倍（相對 solo）
  note     總 tokens  2003  ＝ 0.76 倍（相對 solo）
互踢皮球 handoff_loop triage→refund→triage→refund 已轉給真人客服。
```

前三行是三種交接策略。`full`：退款 agent 看到分流 agent 查到的訂單資料，2 次呼叫就完成，但它的每次呼叫都要讀分流 agent 的整段歷史，花了 1,443 tokens。`filtered`：交接筆記只寫了「B-1042 要退款」，退款 agent 不知道訂單已出貨，只好再查一次，多一次呼叫，反而花了 1,694 tokens，這就是 20.3 節說的「brief 遺失決定」。`note`：同樣是過濾歷史，但分流 agent 把「status=shipped、金額 1,280」寫進交接筆記，退款 agent 不必重查，只花 968 tokens，是三者中最省的。

中間四行把總量和 `solo`（一個 agent 擁有全部 tools 與兩份指令）比較。完整歷史的 handoff 是 solo 的 0.94 倍，好的交接筆記只有 0.76 倍，因為每個專責 agent 的 system prompt 與 tools 都比 solo 小；但遺失事實的 filtered 交接是 1.03 倍，比單一 agent 還貴。這說明 handoff 的成本倍數主要不是由「agent 數量」決定，而是由交接品質決定。最後一行是互踢皮球：兩個 agent 都覺得發票問題不是自己的事，runner 在第 4 次交接時停下並轉真人，path 顯示 `triage→refund→triage→refund`。沒有這個上限，兩個 agent 可以一直互踢到步數用完。

### 實驗三：平行寫入的衝突與分支隔離

第三段重現 20.1 節的事故。三個 coding worker 各自執行「先讀檔、依讀到的內容決定怎麼改、再整檔寫回」的流程；`run_parallel` 用輪流執行的方式模擬並行：A、B、C 依序讀檔，再依序寫回。worker 的修改函式刻意依賴讀到的內容，例如 C 會根據 `CURRENCY_UNIT` 決定 300 元要寫成 300 還是 30000，這就是「隱含決定」。做法一讓三個 worker 共用同一個 `shared` 字典；做法二給每個 worker 一份自己的分支，再由 orchestrator 用 `merge3` 逐一三方合併，每次合併後跑 `finance_test`。

```python
from __future__ import annotations

import json
import unicodedata
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


BASE = "AUTO_REFUND_LIMIT = 500\nCURRENCY_UNIT = TWD\nRETURN_WINDOW_DAYS = 7\n"
PATH = "refund_policy.cfg"

def parse(text: str) -> dict[str, str]:
    return dict(line.split(" = ", 1) for line in text.strip().splitlines())

def render(cfg: dict[str, str]) -> str:
    return "".join(f"{k} = {v}\n" for k, v in cfg.items())


def worker(edit: Callable[[dict[str, str]], dict[str, str]]) -> ScriptedModel:
    """一個 coding subagent：先讀檔，依讀到的內容決定怎麼改，再整檔寫回。"""
    def policy(msgs: list[dict]) -> ModelResponse:
        tool_msgs = [m for m in msgs if m["role"] == "tool"]
        if not tool_msgs:
            return call("read_file", "r1", path=PATH)
        if len(tool_msgs) == 1:                       # 隱含決策：依「讀到的版本」做判斷
            return call("write_file", "w1", path=PATH, content=render(edit(parse(tool_msgs[0]["content"]))))
        return say("完成")
    return ScriptedModel([policy] * 3)


def edit_a(cfg):                                       # 任務 A：自動退款上限提高到 800 元
    return {**cfg, "AUTO_REFUND_LIMIT": "800"}

def edit_b(cfg):                                       # 任務 B：新金流要求金額改用「分」
    return {**cfg, "CURRENCY_UNIT": "CENTS", "AUTO_REFUND_LIMIT": str(int(cfg["AUTO_REFUND_LIMIT"]) * 100)}

def edit_c(cfg):                                       # 任務 C：退貨期改 14 天、新增部分退款上限 300 元
    amount = 300 * (100 if cfg["CURRENCY_UNIT"] == "CENTS" else 1)
    return {**cfg, "RETURN_WINDOW_DAYS": "14", "MAX_PARTIAL_REFUND": str(amount)}


def run_parallel(models: dict[str, ScriptedModel], fs_for: Callable[[str], dict[str, str]]) -> None:
    """模擬並行：每個 worker 輪流走一步（A 讀、B 讀、C 讀、A 寫、B 寫、C 寫）。"""
    msgs = {n: [{"role": "user", "content": f"任務 {n}"}] for n in models}
    for _ in range(3):
        for name, model in models.items():
            resp = model.complete(msgs[name])
            msgs[name].append({"role": "assistant", "content": resp.text, "tool_calls": [vars(t) for t in resp.tool_calls]})
            for tc in resp.tool_calls:
                fs = fs_for(name)
                if tc.name == "read_file":
                    out = fs[tc.args["path"]]
                else:
                    fs[tc.args["path"]], out = tc.args["content"], "ok"
                msgs[name].append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": out})


def merge3(base: dict, ours: dict, theirs: dict) -> tuple[dict, list[str]]:
    """以設定鍵為單位的三方合併：只有一邊改就採用；兩邊改得不同就是衝突。"""
    merged, conflicts = dict(ours), []
    for k in base.keys() | ours.keys() | theirs.keys():
        b, o, t = base.get(k), ours.get(k), theirs.get(k)
        if t == b or t == o:
            continue
        if o == b:
            merged[k] = t
        else:
            conflicts.append(f"{k}: base={b} main={o} branch={t}")
    return merged, sorted(conflicts)


def finance_test(cfg: dict[str, str]) -> list[str]:
    """由需求寫成的測試：金額換算回「元」後必須符合規格。"""
    unit = 100 if cfg["CURRENCY_UNIT"] == "CENTS" else 1
    want = {"AUTO_REFUND_LIMIT": 800, "MAX_PARTIAL_REFUND": 300}
    return [f"{k} 換算為 {int(cfg[k]) / unit:g} 元，需求是 {v} 元" for k, v in want.items() if k in cfg and int(cfg[k]) / unit != v]


EDITS = {"A": edit_a, "B": edit_b, "C": edit_c}

# ── 做法一：三個 worker 共用同一個工作目錄
shared = {PATH: BASE}
run_parallel({n: worker(e) for n, e in EDITS.items()}, lambda _n: shared)
final = parse(shared[PATH])
print("共用目錄 最終檔案：", final)
lost = [n for n, e in EDITS.items() if any(final.get(k) != v for k, v in e(parse(BASE)).items())]
print("  被覆蓋而遺失的修改：", lost)
assert lost == ["A", "B"]

# ── 做法二：每個 worker 一個分支，orchestrator 逐一合併並跑測試
branches = {n: {PATH: BASE} for n in "ABC"}
run_parallel({n: worker(e) for n, e in EDITS.items()}, lambda n: branches[n])
main = parse(BASE)
for name in "ABC":
    merged, conflicts = merge3(parse(BASE), main, parse(branches[name][PATH]))
    if conflicts:
        print(f"  合併 {name}：衝突 {conflicts} → 交給 orchestrator 裁決")
        merged["AUTO_REFUND_LIMIT"] = "80000"       # orchestrator 理解兩個意圖：800 元，以分表示
    problems = finance_test(merged)
    if problems:
        print(f"  合併 {name}：文字上沒有衝突，但測試失敗 {problems}")
        rebased = {PATH: render(main)}             # 退回給 worker：在最新 main 上重做
        run_parallel({name: worker(EDITS[name])}, lambda _n: rebased)
        merged, conflicts = merge3(main, main, parse(rebased[PATH]))
        print(f"  {name} rebase 後重做 → 測試問題 {finance_test(merged)}")
    else:
        print(f"  合併 {name}：成功，測試通過")
    main = merged
print("分支合併 最終檔案：", main)
assert finance_test(main) == [] and main["RETURN_WINDOW_DAYS"] == "14" and main["CURRENCY_UNIT"] == "CENTS"
```

```text
共用目錄 最終檔案： {'AUTO_REFUND_LIMIT': '500', 'CURRENCY_UNIT': 'TWD', 'RETURN_WINDOW_DAYS': '14', 'MAX_PARTIAL_REFUND': '300'}
  被覆蓋而遺失的修改： ['A', 'B']
  合併 A：成功，測試通過
  合併 B：衝突 ['AUTO_REFUND_LIMIT: base=500 main=800 branch=50000'] → 交給 orchestrator 裁決
  合併 B：成功，測試通過
  合併 C：文字上沒有衝突，但測試失敗 ['MAX_PARTIAL_REFUND 換算為 3 元，需求是 300 元']
  C rebase 後重做 → 測試問題 []
分支合併 最終檔案： {'AUTO_REFUND_LIMIT': '80000', 'CURRENCY_UNIT': 'CENTS', 'RETURN_WINDOW_DAYS': '14', 'MAX_PARTIAL_REFUND': '30000'}
```

第一行是共用目錄的結果：最終檔案只有 C 的修改（退貨期 14 天、部分退款上限 300），A 把上限改成 800、B 把單位改成分的修改都不見了，第二行確認被覆蓋的是 A 與 B。這個結果沒有任何錯誤訊息，三個 worker 都回報「完成」，和 Iris 的 CI 全綠一模一樣。

接下來是分支隔離。合併 A 成功，因為只有 A 改了上限。合併 B 時，`merge3` 發現 `AUTO_REFUND_LIMIT` 兩邊都改了而且不同（main 上已經是 A 的 800，B 的分支是 50000），回報衝突並交給 orchestrator；orchestrator 理解兩個意圖後裁決為 80000，也就是 800 元以分表示，測試通過。合併 C 時文字上沒有任何衝突，但 `finance_test` 發現部分退款上限換算後只有 3 元，因為 C 在分支裡讀到的單位還是元。程式把 C 退回去，在最新的 main 上重做，這次 C 讀到 `CENTS`，寫出 30000，測試問題清單變成空的。最後一行是正確的最終檔案：四個修改都在，而且單位一致。

這個實驗把 20.10 節的三個原則都具體化了：分支解決了 lost update，但 B 的衝突需要一個看得到兩個意圖的裁決者，C 的語意衝突只有根據需求寫成的測試才抓得到，修法是讓 worker 在最新版本上重做。如果把 orchestrator 的裁決換成「後合併的覆蓋先合併的」，或把測試拿掉，事故就會原封不動地回來。

| 實驗 | 驗證的主張 | 關鍵數字 | 對應小節 |
|---|---|---|---|
| 一：orchestrator–subagent | 隔離 context 讓 lead 只看到摘要；倍數由前綴與 tool 結果的比例決定 | A：1.38 倍；B：0.56 倍；lead 只收到數十字 | 20.4、20.9 |
| 二：handoff | 交接品質決定成本與正確性；必須限制交接次數 | note 0.76 倍、filtered 1.03 倍；第 4 次交接停下 | 20.6 |
| 三：分支隔離 | 共用目錄會 lost update；分支要配上裁決與測試 | 共用目錄遺失 2 個修改；分支版本 4 個修改全保留 | 20.10 |

## 20.13 實務應用

**情境一：營運 research agent（青鳥的主線）**。月報屬於第 1 章的 L5 任務：在預算內自主完成，不可逆的動作（例如寄給主管）才找人。Iris 的第二版改成 orchestrator–subagent：lead 先把指標定義、期間與排除條件寫進 `decisions.md`，再依問題複雜度派 2 到 5 個 subagent；brief 用 20.4 節的範本，回傳必須列出假設與沒涵蓋的範圍；subagent 只有唯讀的資料倉儲查詢 tool，每個有 tool call 上限；lead 彙整時逐一比對假設，不一致就再派一輪澄清。成本上，每份月報設總 token 預算，並在 trace 中分別記錄 lead 與各 subagent 的用量（第 29 章），每月檢查倍數是否穩定。公開資料中，Anthropic 的 Research 功能採用同樣的 orchestrator-worker 架構，並在最後由專門的 citation agent 補上出處；第 40 章會拆解各家 deep research 系統。

**情境二：內部 coding agent**。coding 是緊耦合寫入的典型，青鳥的 coding agent 預設是單一 agent，只把「讀程式找呼叫端」「讀 log 找錯誤」這類唯讀探索交給 subagent，subagent 回傳檔案路徑與摘要，不回傳整份檔案。只有在工單彼此獨立（例如遷移上百個互不相依的模組）時才開平行 worker，每個 worker 一個 git worktree 與分支，合併時跑完整測試，衝突一律交給 lead 或真人。公開資料中，GitHub 的 Copilot coding agent 讓每個任務對應一個 branch 與一個 pull request；Claude Code 的 agent teams 文件明列同檔編輯與高相依工作不適合平行；Cursor 的大規模實驗則讓每個 worker 有自己的 repo 副本。第 43 章的設計演練會把這套做法擴展成平台。

**情境三：多專長客服**。青鳥客服的退款、物流、發票三條流程，政策與 tools 差異很大，放在同一個 prompt 裡條件分支越來越多，於是 Iris 用 handoff：分流 agent 查清楚意圖後交給專責 agent，交接只帶使用者訊息與結構化交接筆記（訂單編號、狀態、金額、顧客訴求），每段對話最多交接 3 次，超過就轉真人。退款專責 agent 的寫入動作沿用 L3 與 L4 的核准規則，handoff 不改變權限：分流 agent 沒有退款權限，交接後退款 agent 才有，而且仍受金額上限約束。客服分流（triage 加上 handoff）是 OpenAI Agents SDK 這類以 handoff 為原語的框架最典型的用法；公開的客服 agent 產品細節與做法，第 41 章會整理。

**情境四：法律與合規審閱**。合約審閱要對照一份長長的公司政策清單，每一條都要讀合約的相關段落並提出修改建議。Harvey 公開描述的 Playbook Review 改版採用 orchestrator＋subagents：每個 subagent 負責一部分條款，在版本化文件模型的分支上提出修改，衝突交給 orchestrator 合併。這個情境同時具備廣度（很多條款）、可平行（條款大多獨立）與寫入（修改建議）三個特徵，所以需要 20.10 節的分支與合併，而不只是唯讀的摘要回傳。

**情境五：事故除錯的競爭假設**。線上出現間歇性的退款失敗，可能原因有三個：金流商逾時、資料庫鎖競爭、快取過期。與其讓一個 agent 依序排查，不如讓三個 agent 各持一個假設、各自找證據，最後由 lead 比較證據強度。每個 agent 都是唯讀的（查 log、查 metric、查設定），沒有寫入衝突；debate 的回合數固定為一輪反駁，避免無限辯論。這正是 Claude Code agent teams 文件列出的適用情境之一。

| 情境 | 架構 | context 策略 | 寫入隔離 | 主要風險控制 |
|---|---|---|---|---|
| 營運月報 | orchestrator–subagent | brief＋摘要＋決定紀錄檔 | 無寫入 | 假設比對、tool call 上限、總預算 |
| coding agent | 單一 agent＋唯讀 subagent；獨立工單才平行 | 摘要回傳路徑與結論 | worktree＋分支＋測試 | 衝突交給 lead 或真人 |
| 多專長客服 | handoff | 使用者訊息＋結構化交接筆記 | 寫入只在專責 agent | 交接次數上限、權限不隨交接擴大 |
| 合約審閱 | orchestrator–subagent | 條款範圍的 brief | 版本化文件分支 | orchestrator 裁決衝突 |
| 事故除錯 | debate／競爭假設 | 共享論點與證據 | 唯讀 | 固定回合數、lead 裁定 |

這張表的共同點是：架構選擇跟著任務的「耦合程度」與「寫入需求」走，而不是跟著「需要幾種專長」走。同樣是多專長，客服用 handoff、月報用 orchestrator，差別在使用者要不要和專家直接對話、子任務是否彼此獨立。

> [!note] 2026 現況
> 截至 2026 年 10 月，主流框架的 multi-agent 原語大致收斂為兩類：agents-as-tools（OpenAI Agents SDK 的 `agent.as_tool()`、Google ADK 的 `AgentTool`、Strands 的 agents-as-tools）與 handoff（OpenAI Agents SDK 的 handoffs、LlamaIndex `AgentWorkflow`、Microsoft Agent Framework 的 Handoff 編排）；Claude Agent SDK 直接沿用 Claude Code 的 subagents，包含背景執行的 subagent。graph 型框架（LangGraph、Microsoft Agent Framework Workflows、ADK 2.x 的 graph Workflow）則用節點與條件邊表達 supervisor、平行 fan-out 與 fan-in。OpenAI 的 Agents API 把 multi-agent orchestration 列為託管 harness 的內建能力。各框架的版本與 API 變動頻繁，請以官方文件為準，第 26 章有完整比較。

## 20.14 設計檢查清單

1. 是否先證明單一 agent（好的 tools、prompt 與 compaction）做不到或品質不夠，才決定拆成 multi-agent？
2. 每個 agent 的 context、tools 與權限是否真的不同？如果只差一行角色描述，是否應該合併？
3. 每一條 agent 之間的邊界，是否明確選了 context 策略（完整共享、過濾歷史、brief＋摘要、外部共享狀態）？
4. 會影響全局的決定（指標定義、格式、介面）是否由單一角色先做好，並寫進 brief 或外部決定紀錄？
5. subagent 的回傳格式是否強制列出結論、證據、採用的假設與沒涵蓋的範圍？是否有字數或 token 上限？
6. 每個 subagent 是否有獨立的 tool call 上限、token 預算與時間上限？整個系統是否有總預算？
7. 是否用代表性的 trajectory 量過成本倍數（相對於單一 agent），並確認任務價值撐得起它？量測是否考慮了 prompt caching？
8. 子任務是否需要寫入共享資源？若需要，選了哪一種隔離（序列化、lock、branch／worktree、版本化文件、單一寫入者）？
9. 合併時的文字衝突由誰裁決？是否禁止「後寫入的自動覆蓋」？
10. 合併後是否跑根據需求寫成的測試，能抓到文字合併成功但語意錯誤的情況？失敗時是否讓 worker 在最新版本上重做？
11. handoff 與 supervisor 路由是否有次數上限與轉真人的出口？
12. agent 之間傳遞的內容是否一律視為不可信資料？一個 agent 轉述的核准是否不能取代真正的核准？
13. 讀取外部不受信任內容的 subagent，是否沒有寫入或對外發送的 tools？
14. trace 是否記錄每個 agent 的 context、brief、回傳與 token，能在事後重建「誰在什麼依據下做了什麼決定」？

## 20.15 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 最終結論前後矛盾（例如兩個退貨率） | 全局決定沒有寫進 brief，subagent 各自做了不同的隱含決定 | 比對各 subagent 回傳中的假設欄位 | 全局決定由 lead 先做並寫進 brief 或決定紀錄；回傳強制列出假設 |
| multi-agent 版本的帳單是單一 agent 的好幾倍，品質卻差不多 | 所有 agent 共享完整對話；或前綴大、tool 結果小，subagent 只是重複付前綴 | 依 agent 拆帳，看每次呼叫的 input 組成 | 改成 brief＋摘要；合併不必要的 agent；任務不值得就退回單一 agent |
| 多個 subagent 回報幾乎相同的內容 | brief 太模糊，方向重疊 | 比對 brief 的目標與邊界是否互斥 | brief 寫明範圍與「不要做什麼」；lead 規劃時明確切分 |
| 修改無聲消失，CI 卻全綠 | 多個 agent 在同一工作目錄整檔寫回，發生 lost update | 比對各 agent 的寫入紀錄與最終檔案 | 每個 agent 一個 worktree 或分支；寫入前檢查版本 |
| 合併沒有衝突，上線後行為錯誤 | 語意衝突：某個 worker 根據過時的假設做決定 | 用需求寫成的測試重跑合併結果 | 每次合併後跑測試；失敗就讓 worker 在最新 main 上重做 |
| 對話在兩個 agent 之間來回轉手 | handoff 條件重疊，兩邊都認為不是自己的範圍 | 在 trace 中統計交接路徑與次數 | 設交接次數上限並轉真人；釐清各 agent 的職責描述 |
| 專責 agent 接手後重複詢問使用者已經回答過的資訊 | 交接時過濾掉了關鍵事實，筆記不完整 | 比較交接前後 agent 看到的 messages | 交接筆記改成結構化欄位；必要事實由 runner 強制帶過去 |
| lead 等待時間過長，整體延遲由最慢的 subagent 決定 | lead 同步等待所有 subagent；某個 subagent 卡在無效探索 | 看各 subagent 的步數與耗時分布 | 為 subagent 設時間與步數上限；允許部分結果先彙整 |
| 一個 subagent 讀到的外部內容影響了其他 agent 的行為 | agent 之間傳遞的內容被當成指令 | 追蹤可疑指令在 trace 中的來源 | 摘要只當資料；讀外部內容的 subagent 不給寫入工具；核准只能來自使用者 |

## 本章重點整理

- multi-agent system 是由多個各自擁有 context、tools 與 messages 的 agent loop 共同完成任務；和 workflow 的差別在於拆解與派工由模型決定。
- 比較架構最有用的兩條軸是控制拓撲（集中或分散）與 context 拓撲（共享或隔離），每種架構的失敗模式都可追溯到「誰做最終決定」。
- multi-agent 的核心難題是 context 共享與決策一致性：動作帶著隱含決定，看不到彼此決定的平行 agent 會產生衝突。
- brief 與回傳都是壓縮；全局決定要往上收並寫進 brief，假設要往上報，共享的事實要放在所有 agent 都會讀的外部紀錄。
- orchestrator–subagent 用隔離 context 把探索外包、把決策留在 lead，適合廣度研究與唯讀調查；品質取決於 brief 與回傳格式。
- supervisor 是一直握有主導權的中央路由者，handoff 則把控制權交出去；判斷依據是使用者之後要和誰對話。
- handoff 的成本與正確性主要由交接品質決定，結構化交接筆記比完整歷史更省也更穩，而且必須限制交接次數。
- swarm 與 team 用共享任務板與 lock 擴展到大量 agent，但協調開銷真實存在，鎖競爭與僵硬的分工都會拖垮吞吐量。
- debate 與 generator–evaluator 用分歧換品質，前提是回合 0 獨立作答、共享證據而非推理，並有固定的停止條件；有客觀 verifier 時，平行嘗試再挑選通常更划算。
- multi-agent 的成本倍數由固定前綴、tool 結果大小、探索預算與 prompt caching 共同決定，必須用代表性的 trajectory 實際量測。
- 平行寫入要隔離：序列化、lock、branch／worktree、版本化文件或單一寫入者；隔離解決互相干擾，不解決一致性。
- 文字衝突要交給看得到全局的角色裁決，語意衝突只有根據需求寫成的測試抓得到，失敗時讓 worker 在最新版本上重做。
- 值得用 multi-agent 的三類情況是廣度搜尋、可平行、需要隔離；緊耦合的寫入（多數 coding）應該用單一 agent 加唯讀 subagent。
- agent 之間傳遞的內容一律是不可信資料，轉述的核准不能取代使用者的核准，讀外部內容的 subagent 不該有寫入權限。

## 延伸問答

> [!question]- Q1. Cognition 說「Don't Build Multi-Agents」，Anthropic 卻公開了一套 multi-agent research system，兩者矛盾嗎？
> 不矛盾，兩者在處理不同耦合程度的任務。Cognition 反對的是讓看不到彼此決定的 agent 平行做緊耦合的事，例如把一個遊戲拆給兩個 agent 分別做背景與角色，結果風格不合；它的兩條原則（共享完整 context、動作帶著隱含決定）講的是決策一致性。文中也明說 Claude Code 的 subagent 設計得好，因為 subagent 不平行寫入、只回答界定清楚的問題。
>
> Anthropic 的 research system 正好落在這個安全區：subagent 做的是彼此獨立的唯讀調查，需要一致的決定與最後的綜合留在 lead；文章本身也說這種架構不適合高度相依的任務，例如多數 coding。所以兩者其實給出同一個判準：可平行、低耦合、讀多寫少的任務適合 multi-agent；緊耦合寫入用單一 agent，必要時加唯讀 subagent。
>
> 有趣的是 Cognition 後來的 Devin Fusion 也是多模型、多 context 的架構，但關鍵決策仍留在主 agent，這說明爭論的重點從來不是 agent 的數量，而是決定在哪裡做。

> [!question]- Q2. 估算題：lead 一次派 4 個 subagent，每個 subagent 跑 6 步，每步新增 1,500 tokens 的 tool 結果，所有 agent 的固定前綴都是 5,000 tokens，brief 200 tokens。不考慮快取，subagent 部分的 input tokens 大約多少？
> 每個 subagent 有 7 次呼叫（6 次 tool call 加 1 次回答），第 j 次（j 從 0 算起）的 input 是 5,000 ＋ 200 ＋ 1,500 × j。7 次加總是 7 × 5,200 ＋ 1,500 ×（0 ＋ 1 ＋ … ＋ 6）＝ 36,400 ＋ 1,500 × 21 ＝ 67,900 tokens。4 個 subagent 合計約 271,600 tokens，lead 的兩次呼叫另外約一萬多 tokens。
>
> 對照單一 agent 依序做完 24 步：25 次呼叫的 input 是 25 × 5,000 ＋ 1,500 ×（0 ＋ … ＋ 24）＝ 125,000 ＋ 450,000 ＝ 575,000 tokens，約是 orchestrator 的兩倍。但這是不考慮快取的情況；加入 prompt caching 後，單一 agent 重讀的部分大多以折扣價計費，差距會大幅縮小甚至反轉，20.9 節的程式就是在算這件事。而且真實的 subagent 常常會探索得比單一 agent 多，所以估算之後還要用實際 trajectory 校正。

> [!question]- Q3. orchestrator–subagent 和 handoff 怎麼選？青鳥客服要支援退款、物流、發票三種流程，該用哪一個？
> 判斷的關鍵是「專家做完事之後，使用者要跟誰對話」以及「子任務是否彼此獨立」。如果專家只是替主 agent 算一件事，結果要回到主 agent 統整後再回覆，用 agents-as-tools（orchestrator–subagent）；如果專家要接手整段對話、直接面對使用者，用 handoff。另一個角度是 context：orchestrator 的 subagent 從 brief 開始、只回傳摘要；handoff 的新 agent 通常要繼承對話歷史。
>
> 青鳥客服的三種流程，使用者在每一段都在和負責的專家來回對話（確認退貨原因、提供發票抬頭），而且每段的政策與 tools 差異很大，所以用 handoff 比較自然：每個專責 agent 的 prompt 小、容易測試。但要補上三件事：結構化交接筆記讓事實不遺失、交接次數上限防止互踢皮球、權限跟著專責 agent 而不是跟著對話。如果流程很少、單一 agent 的 prompt 還管得住，最好的答案其實是先不拆。

> [!question]- Q4. 你在 production 看到月報 agent 的 token 用量一個月內成長了三倍，但報告品質沒有明顯改善，怎麼排查？
> 第一步是依 agent 拆帳：成長來自 lead 還是 subagent？是 subagent 的數量變多、每個 subagent 的步數變多，還是每步的 input 變大？trace 裡若有每次呼叫的 input 組成（前綴、brief、歷史、tool 結果），很快就能定位。常見的原因有三個：lead 的規劃開始對簡單問題也派很多 subagent（投入規模沒有和複雜度相稱）、brief 太模糊導致 subagent 方向重疊而重複搜尋、或某個 tool 改版後回傳變大。
>
> 第二步是檢查變更時間點：是否和 prompt 改版、模型版本切換、tool 描述修改同時發生。第三步是比對品質指標：如果品質沒變而成本變三倍，代表多花的 token 沒有換到價值，應該在 lead 的 prompt 裡寫明「依複雜度決定 subagent 數量」的規則、為每個 subagent 設 tool call 上限，並設整份報告的總預算。修完後用幾條代表性的 trajectory 寫成 ScriptedModel 測試，把成本倍數當成回歸指標鎖住。

> [!question]- Q5. 程式找錯：下面的 delegate tool 有兩個會讓 multi-agent 失去意義或出事的問題，請指出。
> ```python
> def delegate(topic: str) -> str:
>     sub = Agent(model, ALL_TOOLS, system=LEAD_SYSTEM)
>     _, transcript = sub.run(f"調查 {topic}")
>     return json.dumps(transcript, ensure_ascii=False)
> ```
> 第一個問題是回傳整份 transcript。subagent 的所有搜尋結果會原封不動地變成 lead 的 tool 結果，lead 的 context 和單一 agent 一樣膨脹，還多付了 subagent 自己的成本；隔離 context 的好處完全消失。應該只回傳結論與假設，並設長度上限，必要時把明細寫到檔案、只回傳路徑。
>
> 第二個問題是 subagent 拿到 `ALL_TOOLS` 與 lead 的 system prompt。調查型的 subagent 應該只有唯讀的 tools，否則讀到惡意網頁內容時可能觸發寫入或對外發送；沿用 lead 的 system prompt 也讓它以為自己要負責彙整與回覆。此外 brief 只有「調查 {topic}」，沒有全局決定、邊界與回傳格式，多個 subagent 會各自做隱含決定。修法是為 subagent 準備專用的 system prompt、最小權限的 tools、結構化的 brief 與回傳格式。

> [!question]- Q6. 用 git worktree 讓每個 coding agent 在自己的分支上工作之後，還會有哪些衝突？要怎麼處理？
> worktree 解決的是「互相干擾」：每個 agent 的半成品不會被別人看到或覆蓋，lost update 不會再發生。但還有兩種衝突。第一種是文字衝突：兩個分支改了同一段程式，合併時 git 會報出來；這代表兩個 agent 對同一件事做了不同決定，正確做法是交給看得到兩個意圖的 lead 或真人裁決，而不是自動選一邊，20.12 節的上限 800 元與單位改成分就是例子。
>
> 第二種更危險：語意衝突。兩個分支改的是不同地方，文字合併完全成功，但組合起來意義錯了，例如一個分支改了函式的單位，另一個分支新增的呼叫端仍用舊單位。只有根據需求寫成的測試、型別檢查或整合測試能抓到。處理方式是每次合併後都跑測試，失敗時讓該 worker 在最新的 main 上 rebase 重做，讓它看到別人已經做的決定。最根本的預防仍是任務切分：讓平行的工單真的彼此獨立，共用的介面變更先由單一 agent 做完再平行。

> [!question]- Q7. System design 面試追問：設計一個能同時處理上百個獨立模組遷移的 multi-agent coding 系統，如何避免協調本身變成瓶頸？
> 先避開兩個已知的坑。一是所有 agent 搶同一個共享狀態檔或同一把鎖，agent 一多吞吐量就崩，因為大家都在等鎖；二是過度僵硬的流水線分工（planner、executor、worker、judge 一層等一層），整體被最慢的環節拖住。比較可行的結構是遞迴的 planner：頂層 planner 把工作切成大塊，子 planner 再切成可以獨立完成的任務，worker 各自在自己的 repo 副本或 worktree 裡完成一個任務，只回傳一份交接結果（分支名稱、變更摘要、測試結果）。
>
> 任務板用有到期時間的 lease 認領，避免 worker 當掉時卡住任務；合併交給 CI 與一個合併佇列，測試失敗就自動開修復任務。品質方面，接受小而穩定的錯誤率，在最後安排一輪專門讓測試轉綠的修補，而不是要求每個 worker 都完美。成本方面，每個 worker 有步數與 token 上限，系統有總預算與並行數上限。最後，共用介面或規範的變更不要平行做，先由單一 agent 完成並合併，再讓其他 worker 在新的基礎上工作。

> [!question]- Q8. 讓三個 agent 辯論同一個問題，結果三個都很有自信地同意一個錯誤答案。可能的原因是什麼？怎麼改進？
> 最常見的原因是缺乏真正的多樣性。三個 agent 若用同一個模型、相似的 prompt，常常有相同的盲點，辯論只是把同一個錯誤講三遍；如果它們在回合 0 就看得到彼此的答案，還會附和第一個發言者，形成從眾。另一個原因是共享的是推理過程而不是證據，冗長的推理讀起來很有說服力，卻無法被檢查。
>
> 改進方向有四個。第一，回合 0 強制獨立作答，之後才交換論點。第二，要求每個論點附上可檢查的證據（查詢結果、log 片段、引用），裁判只依證據裁定。第三，增加真正的多樣性：不同的模型、不同的資料來源、或指定不同的立場（例如一個專門找反例）。第四，如果問題其實有客觀的驗證方式（跑測試、查資料庫），就不要用辯論，改成平行嘗試再用 verifier 挑選，這通常更便宜也更可靠。辯論的價值在於沒有客觀 verifier 的判斷題，而且要接受它的成本大約是辯論者數乘以回合數。

## 延伸閱讀

- Anthropic Engineering Blog〈How we built our multi-agent research system〉（2025）
- Cognition Blog，Walden Yan〈Don't Build Multi-Agents〉（2025）
- OpenAI〈A practical guide to building agents〉（2025）
- Anthropic Engineering Blog〈Effective context engineering for AI agents〉（2025）
- Cursor Blog〈Towards self-driving codebases〉（2026）
- Cemri et al.〈Why Do Multi-Agent LLM Systems Fail?〉（MAST，arXiv:2503.13657，2025）
- Du et al.〈Improving Factuality and Reasoning in Language Models through Multiagent Debate〉（2023）
- Claude Code 文件〈Subagents〉與〈Agent teams〉
