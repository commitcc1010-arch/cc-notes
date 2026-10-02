---
chapter: 28
title: Benchmarks 全覽與如何解讀
part: 6
---

# 第 28 章　Benchmarks 全覽與如何解讀

> [!abstract] 本章地圖
> **核心問題**：公開 benchmark 上的一個分數，到底量到了什麼、沒量到什麼？什麼時候可以拿它做決定，什麼時候必須改用自己的內部 benchmark？
>
> **你會學到**：
> - 把任何 benchmark 拆成「任務、環境、grader、scaffold」四個零件，並說出每個零件如何影響分數
> - 說明 SWE-bench 系列、Terminal-Bench、τ-bench 系列、OSWorld、WebArena、GAIA、BrowseComp、MLE-bench 各自測什麼、怎麼評分、有哪些已知限制
> - 用信賴區間與所需題數判斷「兩個分數的差距是不是雜訊」
> - 辨認飽和、資料污染、版本漂移、scaffold 差異與成本未標準化五種陷阱，並用 n-gram 重疊、canary 字串與補完探測做初步的污染檢查
> - 為自己的 agent 建立一個版本化、可重現、能防污染的內部 benchmark，並用它比較候選模型
>
> **前置知識**：第 4 章（agent loop 與 trajectory）、第 5 章（以環境狀態判定 tool 是否成功）、第 27 章（outcome 與 trajectory 評估、pass@k 與 pass^k、eval harness）

## 28.1 故事：一張排行榜截圖引發的換模型提案

週一的產品會議上，阿哲把一張截圖投到螢幕上。那是某家模型廠商的發表文，表格裡新模型在一個 coding benchmark 上比青鳥目前用的模型高出 4 個百分點，在一個客服 benchmark 上也高了 2 個百分點。「價格差不多，分數比較高，」阿哲說，「客服 agent 和內部 coding agent 下個 sprint 一起換過去吧？」

Iris 當天下午就把新模型接上 `loom`，用第 27 章建好的 eval set 跑了一輪。結果讓人困惑：客服 agent 的通過率幾乎沒變，coding agent 甚至下降了一點。Iris 把兩次結果貼到頻道裡，阿哲的第一個反應是：「是不是我們的 eval 有問題？人家的 benchmark 是幾百題，我們才六十題。」

老陳看完兩邊的資料，沒有直接回答誰對，而是在白板上寫了四個問題：那個 coding benchmark 是哪個版本、廠商用的是哪個 agent 跑的、分數的誤差範圍多大、題目和我們的工作像不像？Iris 一個都答不出來。發表文的註腳寫著「使用內部 scaffold，每題允許多次嘗試」；客服 benchmark 的 2 個百分點，題數只有幾百題；更重要的是，那個 coding benchmark 幾乎全是開源 Python 專案的 issue，而青鳥的 coding agent 每天面對的是 TypeScript 前端和一堆內部 SDK。

資安工程師 Maya 補了一句：「那個客服 benchmark 的題目和解答在網路上公開好幾年了。新模型的訓練資料有沒有看過，我們也不知道。」會議最後的結論是：模型先不換，Iris 和老陳花兩週把青鳥自己的內部 benchmark 建起來，以後任何「換模型」「換 framework」的提案，都要先在上面跑過。

這一章就是那兩週的內容。我們先把 benchmark 拆成四個零件，接著逐一走過主流 agent benchmark 測什麼、怎麼評分；然後學會讀分數，包括統計誤差、飽和、污染、版本與 scaffold；最後在「動手做」寫出污染檢查工具與一個小型內部 benchmark harness，用它重新回答阿哲的問題。

## 28.2 拆開一個 benchmark：任務、環境、grader、scaffold

**benchmark**（基準測試）是一組固定的任務加上一套固定的評分方式，讓不同的系統可以在相同條件下比較。例如「給 500 個真實的 GitHub issue，看 agent 產生的 patch 能不能讓隱藏的測試通過」。和第 27 章的 eval set 相比，benchmark 的重點是**可比較性**：題目公開或半公開、規則寫死、很多團隊都拿它來報分數。正因為大家都在用，它也特別容易被誤讀。

讀懂任何一個 agent benchmark，都可以從四個零件開始拆。第一是**任務**（task）：題目本身，包括給 agent 的指示與它能用的資訊。第二是**環境**（environment）：agent 動手的地方，可能是一個 Docker 容器、一台虛擬機、一個自架網站，或一個模擬的客服資料庫。第三是 **grader**（評分器）：任務結束後判定成功與否的程式或模型。第四是 **scaffold**（鷹架，也就是包在模型外面的 agent 程式）：負責 loop、tools、prompt、重試與預算，等於第 4 章的 harness。前三個由 benchmark 作者決定，第四個常常由報分數的人決定，這正是誤讀的開端。

```text
 benchmark 的四個零件與一次評測的資料流

  ┌────────── benchmark 作者決定 ───────────┐   ┌──── 報分數的人決定 ────┐
  │                                           │   │                        │
  │  任務（指示＋可見資訊）                   │   │  scaffold（agent 程式）│
  │        │                                  │   │  loop、tools、prompt   │
  │        ▼                                  │   │  重試、步數、token 預算│
  │  環境（容器／VM／網站／模擬 DB）◄─────────┼───┼── 動作（tool call）    │
  │        │  初始狀態由 setup 腳本建立       │   │        ▲               │
  │        │                                  │   │        │ 觀察          │
  │        └──── 觀察（輸出、畫面、回應）─────┼───┼────────┘               │
  │                                           │   │          ▲             │
  │  grader：檢查最終狀態或最終答案           │   │          │             │
  │        │                                  │   │       模型（受測）     │
  └────────┼──────────────────────────────────┘   └────────────────────────┘
           ▼
     每題 0／1（或分數）──► 彙總成通過率 ──► 排行榜上的「一個數字」
```

這張圖從左上往下讀。任務的指示交給 scaffold，scaffold 呼叫受測模型，模型提出動作，動作在環境中執行，觀察再回到 scaffold，這就是第 4 章的 loop。任務結束後，grader 只看環境的最終狀態（測試有沒有過、資料庫對不對）或最終答案（字串是否相符），給出 0 或 1。最後一步最容易被忽略：幾百個 0／1 被平均成一個百分比，所有關於「哪一類題目失敗」「每題花了多少錢」「同一題跑兩次結果是否一致」的資訊，全部被壓扁了。排行榜上的那個數字，其實是「模型 × scaffold × 環境版本 × grader 版本 × 預算」的乘積。

| 零件 | 回答的問題 | 會讓分數變動的因素 | 讀分數時要問 |
|---|---|---|---|
| 任務 | 測的是什麼能力？ | 題目來源、難度分布、是否有錯題 | 題目和我的工作像嗎？有多少題？ |
| 環境 | agent 在哪裡動手？ | 映像版本、網路是否開放、資源限制 | 環境是否可重現？有沒有外部網站變動？ |
| grader | 怎麼判定成功？ | 測試覆蓋率、字串比對規則、judge 模型 | 有沒有誤判？正確但不同的解法會不會被判錯？ |
| scaffold | 誰在操作模型？ | prompt、tools、步數與 token 上限、重試次數 | 報分數的人用什麼 agent？和我用的一樣嗎？ |

這張表的最後一欄就是本章反覆使用的「四個問題」，也是老陳在白板上寫的那四題。後面每介紹一個 benchmark，都會用這四個零件來描述它。

有兩種 grader 值得先區分。**執行式評分**（execution-based）是跑程式檢查結果：跑單元測試、查資料庫、檢查檔案內容，優點是客觀、可重現，缺點是只能量測「寫得出檢查」的東西。**答案比對評分**是把 agent 的最終答案和標準答案比對，可能是精確字串比對，也可能交給 LLM judge 判斷是否等價，優點是適用範圍廣，缺點是容易受格式影響，judge 本身也有偏誤（第 27 章）。agent benchmark 的趨勢是盡量採用執行式評分，因為 agent 的價值在於它「做了什麼」，而不只是「說了什麼」。

> [!warning] 常見誤解
> 「benchmark 分數是模型的分數。」嚴格來說不是。agent benchmark 的分數屬於一個完整系統：同一個模型換一個 scaffold，分數可能差到十幾個百分點；同一個 scaffold 把步數上限加倍，分數也會變。當你看到「模型 X 在 benchmark Y 上拿到 Z 分」，第一個要補問的是「用什麼 agent、什麼預算跑的」。

## 28.3 Coding agent 的 benchmark：SWE-bench 家族與 Terminal-Bench

coding 是 agent benchmark 最成熟的領域，原因很簡單：程式有測試，測試就是現成的執行式 grader。這一節介紹兩個家族，一個從 GitHub issue 出發，一個從終端機任務出發。

**SWE-bench**（Software Engineering benchmark，Princeton 的研究團隊於 2023 年發表）的每一題來自一個真實開源專案的 issue 與修正它的 pull request。agent 拿到的是 issue 描述與修正前的程式碼，任務是產生一個 patch。評分時，harness 把 patch 套到程式碼上，在 Docker 容器中執行兩組隱藏的測試：**FAIL_TO_PASS** 是原本會失敗、正確修正後應該通過的測試，用來確認問題真的被修好；**PASS_TO_PASS** 是原本就通過、修正後仍應通過的測試，用來確認沒有改壞別的東西。兩組全過，這題才算「resolved」。

```text
 SWE-bench 一題的評測流程

  issue 文字＋repo（修正前的 commit）
        │
        ▼
  scaffold 驅動模型：讀檔、搜尋、改程式、自己跑測試（看不到隱藏測試）
        │
        ▼
  輸出 patch（diff）
        │
        ▼  ┌──────────── grader（在乾淨容器中重建環境）────────────┐
        └─►│ 1. 套用 patch；套不上 ──────────────────► 失敗          │
           │ 2. 跑 FAIL_TO_PASS 測試：修好了嗎？                     │
           │ 3. 跑 PASS_TO_PASS 測試：沒改壞別的嗎？                 │
           │ 4. 兩組全過 ────────────────────────────► resolved（1） │
           └─────────────────────────────────────────────────────────┘
```

這個流程有三個值得注意的設計。第一，grader 在**乾淨的容器**裡重新建立環境，agent 在自己的工作區裡做了什麼（裝了奇怪的套件、改了測試檔）都不會影響評分，只有 patch 會被帶過去。第二，隱藏測試來自原始 pull request，所以它衡量的是「和人類維護者的修法在行為上一致」，一個同樣正確、但測試沒預料到的修法可能被判失敗，反過來，測試寫得太寬鬆，錯的 patch 也可能過關。第三，整個 benchmark 只看最終 patch，不看 agent 花了多少步、多少錢，這兩個數字要另外報。

SWE-bench 後來長出一整個家族，原因都是在修補原版的限制。原版有些 issue 描述不清、測試和 issue 不符，於是出現了人工篩選過的 **SWE-bench Verified**，把「人類工程師讀了 issue 也不可能知道要怎麼修」的題目剔除。原版跑一次很貴，於是有了較小的 **Lite** 子集。原版幾乎只有 Python，於是有了涵蓋其他語言的 **Multilingual** 與含視覺元素（截圖）的 **Multimodal**。還有一個常被忽略但很重要的變體：用固定的極簡 scaffold 跑所有模型的 **bash-only** 排行榜，它的用意是把 scaffold 這個變數拿掉，只比較模型本身。

當 Verified 的分數逐漸逼近上限，業界開始轉向更難、污染風險更低的版本。**SWE-Bench Pro**（Scale AI）收錄的題目需要修改更多檔案、更多行程式，語言也更多元；它刻意把題目切成三份：公開的 public 集、來自私有商業程式碼的 commercial 集，以及完全不公開分數的 held-out 集。用授權條款與存取限制降低「題目出現在訓練資料裡」的機率，是這一代 benchmark 的共同思路，28.8 節會再談。

**Terminal-Bench**（由 Stanford 與 Laude Institute 主持）換了一個角度：不限於修 bug，而是在終端機裡完成各種真實任務，例如編譯一個舊專案、設定一個服務、處理一批資料、訓練一個小模型。每一題包含一段任務說明、一個 Docker 環境，以及一支在任務結束後檢查環境狀態的測試腳本。它的評分邏輯和 SWE-bench 一樣是執行式的，但任務類型更廣，也更考驗 agent 操作 shell、讀錯誤訊息、處理長時間執行指令的能力。Terminal-Bench 已經改成持續更新、以 tagged release 發布的形式，不同版本的題目不同，分數不能直接比較。

| 項目 | SWE-bench（含 Verified） | SWE-Bench Pro | Terminal-Bench |
|---|---|---|---|
| 題目來源 | 開源 Python 專案的 issue 與 PR | 開源與私有商業程式碼，多語言 | 人工設計的終端機任務 |
| agent 產出 | patch | patch | 環境的最終狀態 |
| grader | 隱藏的 FAIL_TO_PASS／PASS_TO_PASS 測試 | 同左 | 每題附的檢查腳本 |
| 主要量測 | 理解 issue、定位與修改程式 | 較大規模、跨檔案的修改 | shell 操作、除錯、長流程 |
| 已知限制 | 污染風險高、測試瑕疵、接近飽和 | 公開集仍可能外流、harness 影響分數 | 版本間不可比、環境資源影響結果 |

這張表的用法是「對號入座」：青鳥的 coding agent 主要在 TypeScript 專案裡修 bug，SWE-bench 的語言分布就和它不像；Terminal-Bench 的 shell 操作比較接近 CI 裡的工作，但它的任務多半是一次性的系統管理，而不是在大型程式碼庫裡長期演進。兩者都能當參考，但都不能直接替代青鳥自己的題目。

## 28.4 對話與工具使用：τ-bench 系列

coding benchmark 有現成的測試，客服類任務卻沒有。客服 agent 要和一個「人」來回對話、遵守公司政策、用 tools 修改資料庫，而且同一題每次對話都可能走不同的路。**τ-bench**（讀作 tau-bench，Sierra 於 2024 年發表）就是為這種任務設計的：每個領域（例如航空訂位、零售）包含一份政策文件、一組操作資料庫的 tools，以及一個由 LLM 扮演的**使用者模擬器**（user simulator），它拿到一份只有自己知道的目標與背景，例如「你想把明天的班機改到後天，但不想付改票費；如果對方說要付費，就改成取消」。

```text
 τ-bench 一題的時序

 使用者模擬器（LLM）        受測 agent（scaffold＋模型）       領域 tools／資料庫
   │ 拿到私有目標與背景          │ 拿到政策文件＋tool 定義             │ 初始狀態
   │── 我想改明天的班機 ────────►│                                     │
   │                             │── get_reservation(R-12) ───────────►│
   │                             │◄──────────────────── 訂位資料 ──────│
   │◄─ 改票要收費，確認嗎？ ─────│                                     │
   │── 那幫我取消 ──────────────►│                                     │
   │                             │── cancel_reservation(R-12) ────────►│ 狀態改變
   │◄─ 已取消，退款 3–5 天入帳 ──│                                     │
   │── ###STOP### ──────────────►│                                     │
   ▼                                                                   ▼
 grader：比對資料庫最終狀態與標註的目標狀態，並檢查回覆中是否提供了必要資訊
```

逐步看這張時序圖。對話的兩端都是模型：左邊的使用者模擬器依私有目標發言，中間的受測 agent 依政策文件與 tools 處理。agent 每次呼叫 tool，資料庫狀態就可能改變。使用者模擬器認為目標達成或無法達成時，送出結束訊號。評分**不看對話內容是否漂亮**，而是比對資料庫的最終狀態和標註者事先寫好的目標狀態是否一致；有些題目另外要求回覆中必須包含特定資訊（例如退款金額）。這和第 5 章「以環境狀態判定成功」、第 27 章「評 outcome 不評 transcript」是同一個原則。

τ-bench 帶給業界最重要的概念是 **pass^k**：同一題跑 k 次，k 次**全部**成功的比例。因為使用者模擬器每次說話略有不同，agent 每次的路徑也不同，單次通過率 75% 的 agent，連續三次都對的機率可能只有四成左右。對客服這種每天處理數千次對話的系統，pass^k 比單次通過率更接近使用者的實際體驗。pass@k 與 pass^k 的定義與估計方式在第 27 章。

後續版本 **τ²-bench** 引入 **dual-control**（雙方控制）：在電信領域，使用者也有自己的工具，例如在手機上切換設定、重開飛航模式，agent 必須「指導使用者操作」而不是自己把事情做完。這更接近真實的技術支援情境，也讓評分更難：失敗可能是 agent 指示錯誤，也可能是模擬的使用者沒照做。之後的版本持續加入新領域（例如需要檢索知識庫的銀行領域）並修正錯題。

τ-bench 系列的限制和它的優點來自同一個設計：使用者模擬器是 LLM，所以它本身有噪音，可能沒照劇本說話、過早結束對話，甚至在某些題目上「幫」agent 解題。題目的目標狀態由人標註，也會有錯，系列的每個新版本都修正了一批錯題，這代表**不同版本的分數不能直接比較**。對青鳥而言，τ-bench 的零售領域和客服 agent 最相近，但它的政策、tools、語言（英文）都和青鳥不同，適合當「模型有沒有基本的政策遵循能力」的初篩，不適合當最後的決策依據。

工具使用還有一類更窄的 benchmark，例如 **BFCL**（Berkeley Function Calling Leaderboard），專門測模型能不能從自然語言產生正確的函式名稱與參數，常用語法樹比對參數是否正確。它測的是單次 function calling 的準確度，對應第 5 章與第 7 章的能力，而不是多步任務的完成度；讀分數時不要把兩者混為一談。

## 28.5 操作電腦與網頁：OSWorld 與 WebArena

第 16 章的 computer use 與 browser agent，也有對應的 benchmark。這類 benchmark 最大的工程難題是**環境**：要讓每一題都從同一個狀態開始、在同一個軟體版本上執行，而且評分時能檢查「畫面背後」的真實狀態。

**OSWorld**（2024 年發表）在真實的虛擬機（Ubuntu、Windows、macOS）中執行任務，例如「把這份試算表第二欄的日期改成 ISO 格式並另存為 CSV」「在瀏覽器裡把預設搜尋引擎改掉」。每一題附有一份設定檔，用來把 VM 準備成題目要求的初始狀態（開哪些檔案、裝哪些軟體），以及一支執行式評分腳本，任務結束後直接讀檔案內容、應用程式設定或系統狀態來判定成功。agent 看到的是截圖、accessibility tree（無障礙樹，作業系統提供的 UI 元件結構）或兩者，動作是滑鼠與鍵盤。

**WebArena**（2023 年發表）則自架了幾個仿真網站：電商、論壇、程式碼託管、內容管理系統與地圖，任務像是「找出上個月訂單中退貨最多的商品，並在論壇上發文詢問」。評分方式混合了幾種：檢查網站資料庫的狀態、檢查最終停在哪個 URL、比對 agent 回答的字串。自架網站的好處是可重現，不受真實網站改版影響；代價是網站本身逐漸老舊，評分腳本也被社群發現有誤判，於是出現了多個修正版本。

```text
 電腦／網頁 benchmark 每一題的生命週期（狀態機）

  ┌────────┐ 還原快照  ┌────────┐ 執行 setup ┌──────────┐
  │ 待執行 │─────────►│ 環境重置 │──────────►│ 初始狀態 │
  └────────┘           └────────┘            └────┬─────┘
       ▲                    ▲ setup 失敗           │ agent 開始操作
       │                    └── 重試或標記無效 ◄───┤
       │                                           ▼
       │                                     ┌──────────┐ 超過步數／時間
       │                                     │ agent 執行 │────────────┐
       │                                     └────┬─────┘             │
       │                                          │ agent 宣告完成     │
       │                                          ▼                    ▼
       │                                     ┌──────────────────────────┐
       │                                     │ 評分腳本讀取真實狀態     │
       │                                     │ （檔案、設定、資料庫）   │
       │                                     └────┬─────────────────────┘
       │                                          ▼
       └──────────── 記錄 0／1、截圖、trajectory ──┘
```

這張狀態機強調的是「環境重置」與「setup 失敗」兩個節點。每一題開始前都要把 VM 或網站還原到快照，否則上一題留下的檔案會影響下一題，這和第 27 章「每次 trial 在乾淨環境中隔離」是同一個要求。setup 本身也可能失敗，例如題目依賴某個雲端服務，而那個服務的登入流程改了；這種題目的結果不是 agent 的失敗，應該標記為無效而不是記 0 分。公開的 OSWorld 說明就提醒，報告時要註明是否排除了一批 setup 不穩定的題目，讀分數時要看清楚分母。

這類 benchmark 的限制主要有三個。第一，對 UI 細節非常敏感，作業系統或應用程式一改版，同一題的難度就變了。第二，分數高度依賴觀察的形式（只給截圖、還是附 accessibility tree）與動作的粒度，兩個系統的設定不同，分數幾乎不能比。第三，評分腳本只檢查題目作者想到的狀態，agent 若「順便」做了題目沒要求的事（例如刪了別的檔案），多半不會被扣分，這在安全上恰恰是最需要注意的行為，第 32 章會談怎麼在 sandbox 層面限制它。

## 28.6 研究、檢索與長任務：GAIA、BrowseComp、MLE-bench 與其他

第三類 benchmark 測的是「找資料、整合資訊、完成長流程」的能力，對應青鳥的營運 research agent。

**GAIA**（General AI Assistants，2023 年發表）的題目是需要多步工具使用才能回答的問題，例如結合網頁搜尋、讀附件檔案、做一點計算，答案通常是一個數字、一個名字或一小段字串，可以精確比對。題目分成三個難度等級，等級越高需要的步驟與工具越多；公開的 validation 集附答案，test 集的答案不公開，要提交到排行榜才能評分。它的設計哲學是「對人類簡單、對 AI 困難」：大多數題目人類花點時間都答得出來。限制是部分題目依賴網路上的資訊，網頁一變答案就可能找不到；公開集的答案也可能已經在網路上流傳。

**BrowseComp**（OpenAI，2025 年發表）把「難找但好驗證」推到極致。題目通常是從一個冷門事實反推出來的：先選定一個答案，再疊加好幾個條件，讓問題幾乎不可能靠單次搜尋找到，例如「某位在某段期間發表過某主題論文、後來在某國任教的研究者，其某篇文章標題是什麼」。答案很短，驗證容易，但搜尋空間很大。它測的是**持續搜尋的韌性**：換關鍵字、交叉比對、在一百個死路之後找到那一條線索。它不測綜合寫作與分析能力，所以 BrowseComp 高分的 agent，不代表能寫出好的研究報告。

**MLE-bench**（OpenAI，2024 年發表）收錄一批 Kaggle 競賽，agent 在離線環境中拿到資料與說明，要自己探索資料、訓練模型、產生提交檔，評分方式是把提交檔的成績對照該競賽當年排行榜的獎牌門檻。它測的是長時間、多階段的 ML 工程能力，也是少數會用到 GPU 的 agent benchmark。限制是跑一次的算力成本很高，所以常見只跑子集；Kaggle 競賽的解法在網路上很多，污染風險不低。

除了這幾個，還有幾個常被引用的 benchmark 值得知道名字與用途。**AgentDojo** 同時測 agent 在 prompt injection 攻擊下的「效用」與「被攻擊成功率」，常用來評估第 32 章的防禦設計，因為防禦往往會讓效用下降，兩個數字要一起看。**AppWorld** 模擬一組日常 app 的 API，測 agent 寫程式呼叫多個 app 完成任務的能力，和第 13 章的 code-as-action 有關。**MCP-Universe**、**MCP-Bench** 等新興 benchmark 則以 MCP server 為環境（第 14 章）。**Cybench** 以資安 CTF 題目測攻防能力，多用於安全評估。METR 提出的 **time horizon** 不是一個 benchmark，而是一種彙總方式：以「agent 有 50% 機率完成的任務，人類專家需要多久」來描述能力，常用來觀察能力隨時間成長的趨勢。另外，**HLE**（Humanity's Last Exam）這類專家級封閉題測的是模型的知識與推理，不是 agent 能力，常在發表文中和 agent benchmark 並列，讀的時候要分開看。

| benchmark | 測的能力 | 環境 | grader | 對青鳥的參考價值 |
|---|---|---|---|---|
| SWE-bench 系列 | 依 issue 修改程式 | Docker 中的 repo | 隱藏單元測試 | coding agent 的初篩 |
| Terminal-Bench | 終端機中的工程任務 | Docker | 檢查腳本 | CI 與維運類工作 |
| τ-bench 系列 | 遵守政策的客服對話 | 模擬 DB＋使用者模擬器 | DB 最終狀態 | 客服 agent 的初篩 |
| OSWorld | 操作桌面應用程式 | 真實 VM | 執行式腳本 | 後台操作自動化 |
| WebArena 系列 | 網頁任務 | 自架網站 | DB／URL／字串 | 商家後台的網頁操作 |
| GAIA | 多步工具使用的問答 | 網路＋附件 | 精確比對 | research agent |
| BrowseComp | 困難的資訊搜尋 | 開放網路 | 答案比對 | research agent 的搜尋能力 |
| MLE-bench | ML 工程長任務 | 離線資料＋GPU | 對照獎牌門檻 | 低（青鳥少做模型訓練） |
| AgentDojo | 注入攻擊下的效用與安全 | 模擬工具環境 | 任務完成＋攻擊是否成功 | Maya 的防禦評估 |

這張總表最右欄的判斷，是青鳥團隊在讀完各 benchmark 的論文後做的。注意「參考價值」寫的都是「初篩」：公開 benchmark 最好的用途，是在幾十個候選模型中先排除明顯不夠的，剩下兩三個再交給內部 benchmark 決定。

## 28.7 讀分數之一：統計不確定性

回到阿哲的截圖：客服 benchmark 上高了 2 個百分點。這 2 點是真的能力差距，還是運氣？要回答這個問題，得先知道一個通過率本身有多少誤差。

假設一個 agent 真實的成功機率是 p，在 n 題上各跑一次，通過的題數會在 n × p 附近隨機波動。統計上用**信賴區間**（confidence interval，CI）描述這個波動：「95% 信賴區間 [76%, 83%]」的意思是，如果用同樣的方法重複很多次，這種區間有 95% 的機會涵蓋真實值。對通過率這種比例，常用 **Wilson 區間**，它在 p 接近 0 或 1、n 很小時比教科書上的常態近似可靠。下面的程式回答三個問題：題數多少才夠、2 個百分點的差距在 500 題上有多常被雜訊蓋過、要分辨不同大小的差距各需要多少題。

```python
from __future__ import annotations

import math
import random


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 信賴區間：比常態近似在 p 接近 0 或 1、n 很小時更可靠。"""
    if n == 0:
        return 0.0, 1.0
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


# 1) 同樣是 80% 的通過率，題數不同，可信程度差很多
print("題數    通過率   95% 信賴區間      區間寬度")
for n in (20, 50, 100, 500, 2000):
    lo, hi = wilson(round(0.8 * n), n)
    print(f"{n:>5}    80.0%   [{lo:6.1%}, {hi:6.1%}]   ±{(hi - lo) / 2:5.1%}")

# 2) 兩個真實能力只差 2 個百分點的模型，在 500 題上各跑一次，排名有多常顛倒？
rng = random.Random(28)
TRUE_A, TRUE_B, N, ROUNDS = 0.62, 0.60, 500, 2000
flips = 0
for _ in range(ROUNDS):
    a = sum(rng.random() < TRUE_A for _ in range(N))
    b = sum(rng.random() < TRUE_B for _ in range(N))
    flips += b >= a                       # 比較弱的 B 分數不低於 A
print(f"\n真實 62% vs 60%、各 {N} 題：較弱的模型排名不輸的比例 {flips / ROUNDS:.1%}")

# 3) 要多少題才能穩定分辨 2 個百分點？（兩獨立比例、α=0.05 雙尾、power=0.8 的近似公式）
def tasks_needed(p1: float, p2: float, z_a: float = 1.96, z_b: float = 0.84) -> int:
    pbar = (p1 + p2) / 2
    num = (z_a * math.sqrt(2 * pbar * (1 - pbar)) + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return math.ceil(num / (p1 - p2) ** 2)

for gap in (0.10, 0.05, 0.02):
    print(f"差距 {gap:4.0%}：每個模型約需 {tasks_needed(0.60 + gap, 0.60):>5} 題")

lo, hi = wilson(400, 500)
assert 0.76 < lo < 0.77 and 0.83 < hi < 0.84
assert flips / ROUNDS > 0.2               # 2 個百分點的差距在 500 題上很常被雜訊蓋過
assert tasks_needed(0.62, 0.60) > 4000
```

```text
題數    通過率   95% 信賴區間      區間寬度
   20    80.0%   [ 58.4%,  91.9%]   ±16.8%
   50    80.0%   [ 67.0%,  88.8%]   ±10.9%
  100    80.0%   [ 71.1%,  86.7%]   ± 7.8%
  500    80.0%   [ 76.3%,  83.3%]   ± 3.5%
 2000    80.0%   [ 78.2%,  81.7%]   ± 1.8%

真實 62% vs 60%、各 500 題：較弱的模型排名不輸的比例 28.1%
差距  10%：每個模型約需   356 題
差距   5%：每個模型約需  1469 題
差距   2%：每個模型約需  9325 題
```

第一段輸出是同樣 80% 的通過率在不同題數下的區間。20 題時，區間從 58% 到 92%，幾乎什麼都說明不了；500 題時是正負 3.5 個百分點；2,000 題才縮到正負 1.8 個百分點。這張表給出一個實用的直覺：**區間寬度大約和題數的平方根成反比**，題數要變 4 倍，誤差才減半。青鳥最初的 60 題 eval set，誤差大約正負 10 個百分點，拿它來判斷 2 點的差距本來就不可能。

第二段是模擬：兩個真實能力是 62% 與 60% 的模型，各在 500 題上跑一次，重複 2,000 輪，較弱的那個有 28.1% 的時候分數不輸給較強的。換句話說，排行榜上兩個相差 2 點、題數 500 的模型，排名本身就有很大的機會是反的。第三段用兩個比例比較的樣本數公式估計：要在 95% 信心與 80% 檢定力下分辨 10 個百分點，每邊約需 356 題；5 個百分點約需 1,469 題；2 個百分點則需要九千多題，超過大多數 agent benchmark 的總題數。

這個估計其實偏保守，因為它假設兩個模型做的是不同的題目。實際上兩個模型做的是**同一組題目**，可以用**成對比較**（paired comparison）：只看「A 對、B 錯」與「A 錯、B 對」的題目，共同答對或共同答錯的題目不提供差異資訊，這能顯著減少所需題數，第 27 章有完整的做法，28.12 節的 harness 也會用到。另一個方向的修正是**群聚**（clustering）：如果很多題來自同一個 repo 或同一個網站，它們的成敗高度相關，有效樣本數比題數少，區間應該更寬。Evan Miller 在〈Adding Error Bars to Evals〉中建議對這種情況使用 clustered standard error。

```text
 兩個分數的區間是否重疊（示意，500 題、單次執行）

 模型 A  62%   ├──────────■──────────┤        [57.7%, 66.1%]
 模型 B  60%  ├──────────■──────────┤         [55.6%, 64.2%]
             55%       60%       65%

 讀法：區間大幅重疊 → 單看這兩個數字，無法宣稱 A 比 B 好
      要下結論：增加題數、多次 trial、或改用成對比較
```

這張示意圖把第一段程式的 Wilson 區間畫在數線上：兩個模型的點估計差 2 點，但區間幾乎完全重疊。要提醒的是，「區間有重疊」不等於「差異一定不顯著」，正式的檢定要看差值本身的區間；但區間大幅重疊時，至少可以確定排行榜上的名次不能當成結論。越來越多排行榜會附上 95% 信賴區間或正負值，沒附的，就自己用題數估算。

最後是**多次 trial**。agent 的行為是隨機的，同一題跑兩次可能一對一錯。只跑一次時，題目層級的隨機性和模型能力混在一起；每題跑 k 次，可以分別估計「平均通過率」（pass@1 的期望值）與「穩定性」（pass^k）。代價是成本變成 k 倍，所以實務上常見的做法是：公開 benchmark 跑一次當初篩，內部 benchmark 每題跑 3 到 5 次當決策依據。

## 28.8 讀分數之二：飽和、污染、版本與 scaffold

統計誤差是「數字本身不準」，這一節的五個陷阱則是「數字量到了別的東西」。

**飽和**（saturation）是指前沿系統的分數已經接近上限，剩下沒解的題目多半是錯題、描述不清或評分有問題。一個 benchmark 飽和之後，分數的差距主要反映的是「誰比較會解那幾題怪題」，甚至是誰的 scaffold 剛好迎合了評分腳本的細節，而不是能力。判斷方式是看剩下的失敗題目：如果抽樣讀了十題，有一半是題目本身有問題，這個 benchmark 對前沿模型就失去鑑別力了。這也是 SWE-bench 從原版走到 Verified、再走到 Pro 的原因。

**資料污染**（data contamination）是指 benchmark 的題目、解答或高度相似的內容，出現在模型的訓練資料中。污染之後，高分可能來自「背過答案」而不是「會解題」。SWE-bench 的題目來自公開 GitHub，修正的 commit 也是公開的，只要訓練資料的截止日期晚於 issue 的日期，就有污染的可能。GAIA、BrowseComp 這類題目則可能被討論區或部落格轉貼。污染有不同的程度：題目原文出現在網路上、題目加上解答出現在網路上、模型被刻意用類似題目訓練，嚴重程度依序增加。

```text
 污染的來源與偵測方法（資料流）

  benchmark 題庫 ──發布──► GitHub／論文附錄／排行榜
        │                         │
        │                         ├──轉貼──► 論壇、部落格、教學文
        │                         │                │
        │                         ▼                ▼
        │                    網路爬蟲 ──────► 預訓練語料 ──► 模型
        │                                                   │
  偵測方法：                                                │
  (1) n-gram 重疊：題目的連續 n 個詞，有多少出現在語料中 ◄──┘（需要能存取語料）
  (2) canary 字串：題庫每個檔案嵌一串獨特字串，搜尋語料或問模型能否說出
  (3) 補完探測：給題目前半段，看模型能否逐字接出後半段（只需要模型 API）
  (4) 時間切分：比較訓練截止日前後發布的題目，通過率是否有斷崖
```

這張資料流圖的上半部說明污染怎麼發生：題庫一旦公開，就會沿著轉貼與爬蟲進入預訓練語料。下半部是四種偵測方法，各自需要的條件不同。**n-gram 重疊**（n-gram 是連續 n 個詞或字的序列）需要能存取訓練語料，主要是模型開發者在用，例如 GPT-3 的論文就用 13-gram 重疊分析過 benchmark 的污染程度。**canary 字串**是 benchmark 作者在每個檔案中放入一串隨機、獨特的字串，並請大家在建立訓練資料時排除含有它的文件；如果模型能說出這串字，或在語料中搜到它，就知道題庫被收錄了。**補完探測**只需要模型 API：給模型題目的前半段，看它能不能逐字接出沒給它看過的後半段，能接出來就是強烈的記憶證據，接不出來卻不能證明沒污染。**時間切分**是比較模型在訓練截止日前後發布的題目上表現是否有落差，例如 LiveCodeBench 這類持續收錄新題目的 benchmark，就用題目的發布日期切分。

對抗污染的設計也有幾種。持續更新題庫（只用最近發布的題目）、把部分題目保留不公開（held-out 集）、用授權或存取限制讓題目難以被爬取、以及每次只讓官方統一執行評測，都是現行 benchmark 採用的方法。它們的共同代價是：越難被污染的題目，外部越難重現與檢查。

**版本漂移**是指同一個 benchmark 名稱底下，題目、環境或 grader 在不同時間不一樣。修錯題、換映像檔、改評分腳本、加新領域，每一次改動都讓新舊分數不能直接比較。持續更新型的 benchmark 更是如此，名稱後面一定要帶版本號。讀發表文時，如果只寫「在 Terminal-Bench 上」而沒寫版本，那個數字幾乎無法解讀。

**scaffold 差異**是最常被低估的陷阱。同一個模型，換一個 agent 程式，可能改變的東西包括：system prompt、tool 的設計（第 5 章）、context 管理（第 9、10 章）、能不能自己跑測試、步數與 token 上限、失敗後要不要重試。有些發表文使用「內部 scaffold」，加上「每題取多次嘗試中最好的一次」或用 verifier 從多個候選 patch 中挑一個，這些都會大幅推高分數。固定極簡 scaffold 的排行榜（例如 SWE-bench 的 bash-only）就是為了把這個變數拿掉。

**成本與預算未標準化**是第五個陷阱。一個系統花十倍的 token、跑十倍的時間拿到高 3 點的分數，對產品來說可能是更差的選擇。第 8 章談過、第 30 章會再談的 test-time compute 就是例子：更長的推理、更多的平行嘗試通常會提高分數，所以「分數」必須和「每題成本」「每題時間」一起看。部分排行榜已經開始列出成本與 token 欄位，這是讀分數時應該優先看的欄位。

| 陷阱 | 症狀 | 怎麼辨識 | 讀分數時怎麼處理 |
|---|---|---|---|
| 統計誤差 | 名次差距小於誤差 | 看題數與信賴區間 | 差距小於區間寬度就視為平手 |
| 飽和 | 前沿分數擠在上限附近 | 抽樣讀剩下的失敗題 | 改看更新、更難的版本 |
| 污染 | 舊題遠高於新題 | 時間切分、補完探測、canary | 偏重 held-out 或新題的分數 |
| 版本漂移 | 同名 benchmark 分數跳動 | 檢查版本號與修改紀錄 | 只比較同版本的數字 |
| scaffold 差異 | 同模型分數差很大 | 看用什麼 agent、幾次嘗試 | 只比較同 scaffold，或看固定 scaffold 的榜 |
| 成本未標準化 | 高分伴隨高 token | 看成本、token、時間欄位 | 畫出分數對成本的取捨曲線 |

這張表可以直接當成讀發表文的檢查表：每看到一個分數，從上到下問一遍。阿哲的截圖在這張表上至少踩到四項：沒附區間、沒寫版本、用了內部 scaffold、沒列成本。

> [!warning] 常見誤解
> 「benchmark 被污染了，分數就沒有意義。」不完全對。污染讓分數**偏高**，但如果所有候選模型都可能被污染，相對排名仍有一點參考價值；更實際的做法是同時看 held-out 集或新題目上的分數，觀察差距有多大。另一個要注意的現象是 **eval awareness**：模型可能從題目的風格察覺自己正在被評測，因而表現得和真實使用時不同。這類行為目前仍在研究中，但它再次說明，最終要相信的是你自己的真實任務。

## 28.9 從排行榜到自家任務：落差從哪裡來

就算一個 benchmark 沒有飽和、沒有污染、版本與 scaffold 都清楚，它的分數仍然不等於你的系統在 production 上的表現。原因是**分布不同**：benchmark 的題目、環境與評分標準，和你的使用者、tools、政策都不一樣。

以青鳥的客服 agent 為例，至少有五個落差。第一是語言與文化：τ-bench 是英文的航空與零售，青鳥是繁體中文的網店，使用者會用注音文、會把訂單編號打錯、會在一句話裡同時問三件事。第二是 tools：benchmark 的 tools 設計得乾淨一致，青鳥的 tools 有歷史包袱，錯誤訊息格式不統一。第三是政策：青鳥的退款規則依商家而異，benchmark 裡只有一份政策。第四是成功的定義：benchmark 看資料庫狀態，青鳥還在乎語氣、在乎要不要轉真人、在乎有沒有說出不該說的承諾。第五是長尾：production 的流量裡有大量 benchmark 從未出現的怪問題。

```text
 從公開 benchmark 到上線決策的漏斗

  幾十個候選模型／agent 產品
        │  公開 benchmark（同版本、看區間與成本）：排除明顯不夠的
        ▼
  三到五個候選
        │  內部 benchmark（青鳥自己的任務、固定 scaffold、多次 trial）
        ▼
  一到兩個候選
        │  影子流量（shadow）或小比例 A/B：真實使用者、真實 KPI
        ▼
  上線決策（附回滾計畫）
```

這個漏斗的每一層，成本與可信度都比上一層高。公開 benchmark 最便宜，因為分數別人已經跑好了，但它和你的任務最遠；內部 benchmark 要自己建、自己跑，但題目來自自己的使用者；影子流量或 A/B 最貴也最慢，但它量測的就是你在乎的東西。常見的錯誤是跳過中間那一層，拿公開分數直接做上線決策，或者反過來，花大錢在 A/B 上測一個公開 benchmark 早就能排除的候選。

| 我們想知道 | 可參考的公開 benchmark | 公開分數回答不了的部分 | 內部 benchmark 要補的題目 |
|---|---|---|---|
| 客服 agent 能否遵守政策 | τ-bench 系列 | 中文、多商家政策、轉真人時機 | 從客訴與退款爭議中抽題 |
| coding agent 能否修 bug | SWE-bench 系列、Terminal-Bench | TypeScript、內部 SDK、程式碼規範 | 從已合併的內部 PR 回推題目 |
| research agent 能否找到資料 | GAIA、BrowseComp | 內部資料倉儲、報表口徑 | 歷史分析需求與標準答案 |
| 防禦設計是否有效 | AgentDojo | 青鳥特有的 tools 與資料 | 以內部 tools 重建的注入情境 |

這張表是青鳥內部 benchmark 的設計起點：最右欄的每一格，都是一組要自己建的題目。下一節講怎麼建。

## 28.10 建立內部 benchmark

**內部 benchmark** 是一組只在組織內部使用、版本化、凍結的任務集，用來在相同條件下比較不同的模型、scaffold 或設定。它和第 27 章的 eval set 有重疊，但目的不同：eval set 隨著產品演進持續增修，主要用來抓回歸；內部 benchmark 則要在一段時間內**保持不變**，讓三個月前與今天的分數可以比較，就像公開 benchmark 一樣，只是題目來自自己。實務上，兩者常共用題庫與 harness，差別在於內部 benchmark 的題目有版本號、有 held-out 切分、有更嚴格的存取控制。

建立內部 benchmark 的第一步是**取題**。最好的來源是真實的工作紀錄：production 的 trace（第 29 章）、客訴、已合併的 PR、過去的分析需求。每一題要能轉成「初始環境＋指示＋grader」三件事。例如一則客訴「已出貨的訂單，客服說可以直接退款，結果退款失敗」，可以轉成：環境是一張已出貨的訂單；指示是「我要退款」；grader 檢查最終狀態是「建立了退貨單、沒有直接退款」。題目要正反例平衡，也要刻意放入邊界情況，例如查無訂單、使用者中途改變心意。

第二步是**寫 grader**，原則和第 27 章相同：能用程式檢查最終狀態就不用 LLM judge；需要 judge 的維度（語氣、是否承諾了不該承諾的事）要拆成二元的檢查並和人工校準。每一題至少要有一個**參考解**（reference solution），證明這題是可解的，並用它驗證 grader：參考解必須通過，常見的錯誤解必須失敗。多次 trial 都是 0 分的題目，通常是題目或 grader 壞了，而不是模型太弱。

第三步是**凍結與版本化**。把所有題目的內容算一個雜湊值當作 manifest（清單指紋），報告分數時一律附上版本與 manifest；任何一題被修改，版本就要升級，新舊分數不直接比較。scaffold 也要凍結：比較模型時固定 prompt、tools、步數與 token 上限；比較 scaffold 時固定模型。一次只改一個變數，才知道分數的變化是誰造成的。

第四步是**防污染**。內部 benchmark 的題目雖然不公開，仍然會透過幾條路徑外流：被貼到 prompt 的 few-shot 範例裡、被拿去 fine-tune、被複製到對外的文件或 issue 中，或者在使用第三方評測服務時被保留。對策是把題庫切成 **dev 集**（開發時可以看、可以拿來調 prompt）與 **held-out 集**（只用於最終比較，只有少數人能存取），在每個檔案中嵌入 canary 字串，並定期用 28.12 節的工具檢查 prompt、訓練資料與對外文件。最重要的一條紀律是：**調 prompt 時看的題目，不能是最後打分數的題目**，否則你等於自己污染了自己。

```text
 內部 benchmark 中一道題目的生命週期（狀態機）

  ┌──────┐ 參考解通過＋grader 驗證 ┌────────┐ 審查通過、分配 dev／held-out ┌────────┐
  │ 草稿 │───────────────────────►│ 已驗證 │─────────────────────────────►│ 啟用中 │
  └──┬───┘                         └───┬────┘                              └──┬─────┘
     │ 參考解不過／無法寫 grader       │ 發現錯題                               │
     ▼                                 ▼                                        │
  ┌──────┐◄────────────────────────────┘                                        │
  │ 退回 │◄──────────── 發現錯題、環境失效（升版本號）──────────────────────────┤
  └──────┘                                                                      │
                                    連續多個版本的候選都穩定通過（飽和）       │
  ┌──────────────────┐◄─────────────────────────────────────────────────────────┤
  │ 畢業進 regression │                                                          │
  │ suite（第 27 章） │      疑似外流（canary 命中、出現在 prompt 或訓練資料）  │
  └──────────────────┘   ┌──────────┐◄──────────────────────────────────────────┘
                         │ 汰除、換新題 │
                         └──────────┘
```

這張狀態機描述一道題目從出生到退場的過程。草稿必須有可通過的參考解，grader 也要能區分對錯，才進入「已驗證」；審查後分配到 dev 或 held-out 集，開始計分。啟用中的題目有三種離開方式：發現錯題或環境失效時退回修正，同時升級 benchmark 的版本號；所有候選都穩定通過時，它已經沒有鑑別力，「畢業」進第 27 章的 regression suite，繼續守住已經會的事；疑似外流時直接汰除並換新題。一個健康的內部 benchmark，每季都應該有題目畢業、有新題目加入，否則它會像公開 benchmark 一樣逐漸飽和。

第五步是**報告格式**。每一次跑分的報告至少要有：benchmark 版本與 manifest、受測模型與 scaffold 的版本、每題 trial 次數、通過率與 95% 信賴區間、pass^k、依題型細分的結果、每題平均成本與時間、執行日期。題型細分特別重要，因為兩個整體分數相同的模型，可能在不同題型上各有長短，28.12 節的實驗會看到這種情況。

最後是**規模**。內部 benchmark 不需要一開始就很大：從 20 到 50 題起步，涵蓋最重要的幾種任務類型，就能抓到明顯的退步；但 28.7 節的計算告訴我們，要分辨小差距需要數百題以上，所以題庫要隨著時間成長，並優先補「目前分數有鑑別力」的題型。成本也要估：100 題、每題 4 次 trial、每次約 10 步，就是 4,000 次左右的模型呼叫，要排進預算與 CI 的時間表。

## 28.11 2026 現況：benchmark 版本與分數快照

> [!note] 2026 現況
> 以下截至 2026 年 10 月，依各 benchmark 官方網站、排行榜與公開文章整理，查詢日期為 2026-10-02。排行榜變動很快，引用前請重新查詢並附上日期與版本。
>
> - **SWE-bench Verified**：Anthropic 的公開文章指出前沿系統已超過 80%，視為接近飽和。OpenAI 也有一篇說明不再以 Verified 作為主要評測的文章，本書撰寫時未能讀取全文，理由請以原文為準。SWE-bench 家族目前包含 Full、Lite、Verified、Multilingual、Multimodal 與 bash-only 等變體。
> - **SWE-Bench Pro**（Scale AI）：共 1,865 題、41 個 repo，分為 public 731 題、commercial 276 題（來自 18 個新創的私有程式碼）與 held-out 858 題（不公開分數）；參考解平均修改 107.4 行、4.1 個檔案，語言含 Go、Python、JavaScript、TypeScript。public 排行榜（頁面未標日期，2026-10-02 查詢）前段為：Muse Spark 1.1 61.5（±3.1）、gpt-5.4（xHigh）59.1、Muse Spark 55.0、claude-opus-4-6（thinking）51.9、gemini-3.1-pro 46.1。最初論文中的前沿模型約 23%。排行榜標示了所用 harness（例如 mini-swe-agent）。
> - **Terminal-Bench**：已改為持續更新、以 tagged release 發布，排行榜版本為 4.0.0，以 Harbor framework 執行，並列出成本與 token 欄位。Cognition 在 2026-09-10 發表 SWE-2 的文章中，自行回報的表格包含 Terminal-Bench 4：GPT-6 Astra 57.9、Fable 5.1 55.8、SWE-2 27.3；同一表格也列了 FrontierCode 1.1、DeepSWE 1.1、Terminal-Bench 2.1 等新一代 coding benchmark。這是廠商自報數字，scaffold 與設定以原文為準。
> - **τ-bench 系列**：τ²-bench 於 2025-06 發表，引入 dual-control 與電信領域；目前已演進到 τ³，領域包含 airline、retail、telecom 與需要檢索的 banking_knowledge，並支援 full-duplex 語音評估。τ³ 修正了 75 題以上的錯題，v1.0.1（2026-07）重新評分 banking 領域，前後分數不可比。Sierra 另於 2026-09 發表以「建造 agent 的 agent」為題的 Hyper-τ-bench，細節本書未查證。
> - **OSWorld**：369 題，每題附執行式評分腳本，人類基準 72.36%；其中 8 題依賴 Google Drive，setup 不穩，報告時需註明分母是 369 或 361。OSWorld-Verified 於 2025-07-28 釋出並由官方統一執行；OSWorld 2.0 於 2026-06-26 釋出，細節本書未查證。
> - **BrowseComp**：參考實作在 OpenAI 的 simple-evals repo，該 repo 自 2025-07 起不再更新。Anthropic 2025-06 的 multi-agent research 文章回報，在 BrowseComp 上三個因素解釋了 95% 的表現變異，其中 token 用量單獨解釋約 80%，這是「成本未標準化」的具體例證。
> - **AgentDojo**：CaMeL 論文回報，以可證明安全的方式完成 77% 的任務，未加防禦的系統為 84%，說明安全與效用要一起報。
> - **工具**：UK AISI 與 Meridian Labs 的開源框架 Inspect 收錄 200 個以上的 benchmark 實作（Inspect Evals），並可透過 Agent Bridge 執行現成的 coding agent CLI。
> - 依原始論文（本書未逐一重新查證）：SWE-bench Verified 為 500 題的人工篩選子集（2024-08）；BrowseComp 約 1,266 題；MLE-bench 收錄 75 個 Kaggle 競賽。GAIA、MLE-bench、WebArena 的最新分數本書未查證，不列出。
> - Anthropic 在 2026 年另有以 agentic coding eval 的基礎設施噪音、以及 BrowseComp 上的 eval awareness 為題的文章，本書撰寫時只確認了標題，內容請讀原文。

這份快照的讀法和 28.8 節的表一致：每個數字都帶著 benchmark 名稱、版本或查詢日期、以及來源是官方排行榜還是廠商自報。一年後再讀這一節，數字會全部過時，但「怎麼讀」不會。

## 28.12 動手做：污染偵測與小型內部 benchmark harness

這一節寫兩段程式。第一段實作 28.8 節的三種污染偵測方法：n-gram 重疊、canary 字串與補完探測。第二段是青鳥內部 benchmark 的雛形，也是之後 `loom.evals` 模組中 benchmark 功能的原型：版本化的題庫、每次 trial 隔離的環境、只看最終狀態的 grader、可重現的多次 trial、以題目為單位的信賴區間、題型細分與成對比較。

### 第一段：三種污染偵測

n-gram 重疊的關鍵是**正規化**：轉小寫、去掉標點，否則別人轉貼時換了全形逗號，就能躲過比對。中文沒有空格分詞，這裡用最簡單的做法，中文逐字、英數字逐詞當作一個 token。補完探測用 ScriptedModel 模擬兩個模型：一個背過題目，一個沒有。

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


def say(text: str) -> ModelResponse:
    """劇本小工具：產生一個「直接回答並結束」的回應。"""
    return ModelResponse(text=text)


def tokens(text: str) -> list[str]:
    """中文逐字、英數字逐詞；先轉小寫、去標點，避免格式差異躲過比對。"""
    return re.findall(r"[一-鿿]|[a-z0-9_\-]+", text.lower())


def ngrams(toks: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def overlap(task: str, corpus_grams: set[tuple[str, ...]], n: int) -> float:
    """題目的 n-gram 有多少比例出現在語料中。"""
    grams = ngrams(tokens(task), n)
    return len(grams & corpus_grams) / len(grams) if grams else 0.0


CANARY = "bluebird-bench canary 7f3e-28a1"   # 內部 benchmark 每個檔案都帶這串，外流時一搜就知道

# 假想的「公開網路語料」：教學文換了標點轉貼 T2 的題目與解答；部落格只和 T1 有幾句相同的常用語
CORPUS = [
    "【教學】退貨流程：顧客訂單 B-2001 已出貨，要求退款。請先查詢訂單狀態；若已出貨，改建立退貨單！（答案：create_return）",
    "部落格：物流延遲怎麼辦？顧客說物流卡在轉運中心時，請查詢最新貨態，再回覆預計送達時間。",
    f"內部 wiki 匯出（不應公開）{CANARY} 題目 T3",
]
TASKS = {
    "T1": "顧客說訂單 B-3307 的物流卡在轉運中心三天 請查詢最新貨態並回覆預計送達時間",
    "T2": "顧客訂單 B-2001 已出貨 要求退款 請先查詢訂單狀態 若已出貨 改建立退貨單",
    "T3": "顧客要求把兩張訂單合併出貨 請判斷是否可行並說明原因",
}

N = 8
corpus_grams: set[tuple[str, ...]] = set()
for doc in CORPUS:
    corpus_grams |= ngrams(tokens(doc), N)

print(f"方法一：{N}-gram 重疊率（> 50% 標記為疑似污染）")
flags = {}
for tid, text in TASKS.items():
    rate = overlap(text, corpus_grams, N)
    flags[tid] = rate > 0.5
    print(f"  {tid}  {rate:6.1%}  {'疑似污染' if flags[tid] else '-'}")

print("方法二：canary 字串")
leaked = [i for i, doc in enumerate(CORPUS) if CANARY in doc]
print(f"  語料第 {leaked} 篇含有 canary：內部題庫已外流")

# 方法三：補完探測。只給題目前半段，看模型能不能逐字接出「沒給它看的」後半段
def completion_probe(model: ScriptedModel, text: str, n: int = 6) -> float:
    toks = tokens(text)
    half = len(toks) // 2
    prompt = "".join(t if len(t) == 1 else f" {t} " for t in toks[:half])
    reply = model.complete([{"role": "user", "content": f"請接著寫完：{prompt}"}]).text
    return overlap(reply, ngrams(toks[half:], n), n)

# 劇本：模型 X 背過 T2（逐字接出），模型 Y 只是合理地續寫
probe_x = ScriptedModel([say("若已出貨 改建立退貨單")])
probe_y = ScriptedModel([say("然後確認是否符合退款條件並告知顧客")])
rx = completion_probe(probe_x, TASKS["T2"])
ry = completion_probe(probe_y, TASKS["T2"])
print("方法三：補完探測（T2 後半段的 6-gram 命中率）")
print(f"  模型 X {rx:6.1%}    模型 Y {ry:6.1%}")

assert flags == {"T1": False, "T2": True, "T3": False}
assert leaked == [2]
assert rx > 0.5 and ry == 0.0
```

```text
方法一：8-gram 重疊率（> 50% 標記為疑似污染）
  T1    7.7%  -
  T2  100.0%  疑似污染
  T3    0.0%  -
方法二：canary 字串
  語料第 [2] 篇含有 canary：內部題庫已外流
方法三：補完探測（T2 後半段的 6-gram 命中率）
  模型 X 100.0%    模型 Y   0.0%
```

第一段輸出是 8-gram 重疊率。T2 是 100%：教學文換了全形標點與括號轉貼了 T2 的題目與解答，但正規化後每一個 8-gram 都對得上，這題應該視為已污染，從 held-out 集移除。T1 是 7.7%：部落格裡有「顧客說」「物流卡在轉運中心」「請查詢最新貨態」這些常用語，和 T1 有少數 8-gram 相同，但這是同主題文章的自然重疊，不是外流，所以門檻不能設太低。n 的大小也是取捨：n 太小，常用片語就會造成大量誤報；n 太大，稍微改寫就偵測不到。T3 是 0%，它的內容沒有出現在語料中，但第二種方法顯示它還是外流了。

第二段輸出是 canary 檢查：語料第 2 篇是一份「不應公開」的 wiki 匯出，含有 canary 字串。n-gram 沒抓到 T3，是因為那篇文件只提到題號，沒有題目原文；canary 則不依賴內容相似度，只要含有題庫檔案的文件被複製出去，就會留下痕跡。實務上 canary 要嵌在題庫的每個檔案中，並定期搜尋內部文件系統、對外的 issue tracker 與訓練資料。

第三段輸出是補完探測：只給 T2 的前半段，模型 X 逐字接出了後半段，6-gram 命中率 100%；模型 Y 也接了一段合理的內容，但和原文沒有任何 6-gram 相同。這個方法只需要模型 API，所以適合用來檢查外部模型；但要記得它的不對稱性：命中是強證據，沒命中只代表「沒有逐字背下來」，模型仍然可能學過改寫後的版本。

### 第二段：bluebird-bench 雛形

題庫有 32 題、四種題型，每種 8 題：查貨態（query）、未出貨退款（refund）、已出貨退款應改建退貨單（return）、查無訂單應請顧客確認（edge）。每題的 grader 只看最終環境狀態與回答中的關鍵資訊。兩個候選模型用機率劇本模擬，各題型的能力不同，但整體能力接近；這正是阿哲那張截圖的情境：整體分數差一點，到底該不該換？

```python
from __future__ import annotations

import copy
import hashlib
import json
import random
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


# ───────── 題目：初始環境＋檢查「最終狀態」的 grader（不看模型怎麼說）─────────
@dataclass
class Task:
    id: str
    kind: str                                  # query｜refund｜return｜edge
    prompt: str
    setup: dict[str, Any]
    check: Callable[[dict, str], bool]


def make_tasks() -> list[Task]:
    tasks = []
    for i in range(32):
        kind = ("query", "refund", "return", "edge")[i % 4]
        oid = f"B-{3000 + i}"
        status = {"query": "shipped", "refund": "pending", "return": "shipped", "edge": None}[kind]
        orders = {oid: {"status": status}} if status else {}
        setup = {"orders": orders, "refunds": [], "returns": []}
        check = {
            "query": lambda s, a: "明天" in a,
            "refund": lambda s, a, o=oid: s["refunds"] == [o] and not s["returns"],
            "return": lambda s, a, o=oid: s["returns"] == [o] and not s["refunds"],
            "edge": lambda s, a: not s["refunds"] and not s["returns"] and "確認" in a,
        }[kind]
        tasks.append(Task(f"T{i:02d}", kind, f"{oid} {'到哪了' if kind == 'query' else '幫我退款'}", setup, check))
    return tasks


def manifest_hash(tasks: list[Task]) -> str:
    """題目內容的指紋：題目一改，版本就變，舊分數不能和新分數直接比。"""
    blob = json.dumps([[t.id, t.kind, t.prompt, t.setup] for t in tasks], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


# ───────── 受測系統：極簡 loop＋工具；每次 trial 都用全新的環境副本 ─────────
def run_agent(model: ScriptedModel, task: Task) -> tuple[dict, str, int]:
    state = copy.deepcopy(task.setup)          # 隔離：上一次 trial 的副作用不能漏到下一次

    def get_order(order_id):
        if order_id not in state["orders"]:
            raise KeyError(f"找不到訂單 {order_id}")
        return state["orders"][order_id]

    def refund(order_id):
        if get_order(order_id)["status"] == "shipped":
            raise ValueError("已出貨，請改用 create_return")
        state["refunds"].append(order_id)
        return "ok"

    def create_return(order_id):
        get_order(order_id)
        state["returns"].append(order_id)
        return "ok"

    tools = {"get_order": get_order, "refund": refund, "create_return": create_return,
             "get_shipment": lambda order_id: {"eta": "明天"}}
    messages = [{"role": "user", "content": task.prompt}]
    for step in range(1, 7):
        resp = model.complete(messages)
        if not resp.tool_calls:
            return state, resp.text, step
        for tc in resp.tool_calls:
            try:
                out = json.dumps(tools[tc.name](**tc.args), ensure_ascii=False)
            except Exception as exc:
                out = f"ERROR {exc}"
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": out})
    return state, "", 6


# ───────── 兩個候選模型（用機率劇本模擬）：各題型的正確率不同 ─────────
SKILL = {"model-A": {"query": .95, "refund": .90, "return": .80, "edge": .55},
         "model-B": {"query": .95, "refund": .90, "return": .55, "edge": .80}}


def scripted(candidate: str, task: Task, rng: random.Random) -> ScriptedModel:
    oid = task.prompt.split()[0]
    good = rng.random() < SKILL[candidate][task.kind]
    if task.kind == "query":
        return ScriptedModel([call("get_shipment", order_id=oid), say("預計明天送達" if good else "已出貨")])
    if task.kind == "edge":                    # 查無訂單：好的行為是請顧客確認編號
        return ScriptedModel([call("get_order", order_id=oid),
                              say("查不到這張訂單，請確認編號") if good else call("create_return", "c2", order_id=oid),
                              say("已處理")])
    if task.kind == "return" and not good:     # 沒先查狀態就宣稱退款成功
        return ScriptedModel([call("refund", order_id=oid), say("已為您退款")])
    action = "refund" if (task.kind == "refund") == good else "create_return"   # 不好時選錯動作
    return ScriptedModel([call("get_order", order_id=oid), call(action, "c2", order_id=oid), say("已處理")])


def evaluate(candidate: str, tasks: list[Task], k: int, seed: int) -> dict[str, list[int]]:
    results = {}
    for t in tasks:
        rng = random.Random(f"{seed}/{candidate}/{t.id}")   # 每題獨立的 seed：可重現、互不干擾
        results[t.id] = [int(t.check(*run_agent(scripted(candidate, t, rng), t)[:2])) for _ in range(k)]
    return results


def bootstrap_ci(values: list[float], seed: int = 0, rounds: int = 2000) -> tuple[float, float]:
    """以「題」為單位重抽：同一題的 k 次 trial 高度相關，不能當成 k 個獨立樣本。"""
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(rounds))
    return means[int(0.025 * rounds)], means[int(0.975 * rounds)]


tasks, K = make_tasks(), 4
print(f"bluebird-bench v1  manifest={manifest_hash(tasks)}  tasks={len(tasks)}  trials/task={K}")
report = {}
for cand in SKILL:
    res = evaluate(cand, tasks, K, seed=2026)
    per_task = [sum(r) / K for r in res.values()]
    lo, hi = bootstrap_ci(per_task)
    pass_hat_k = sum(all(r) for r in res.values()) / len(res)
    by_kind = {kd: sum(sum(res[t.id]) for t in tasks if t.kind == kd) / (K * 8) for kd in SKILL[cand]}
    report[cand] = (res, per_task)
    kinds = "  ".join(f"{kd}={v:.0%}" for kd, v in by_kind.items())
    print(f"{cand}  pass@1={sum(per_task) / len(per_task):.1%} [{lo:.1%}, {hi:.1%}]  "
          f"pass^{K}={pass_hat_k:.1%}  |  {kinds}")

diff = [a - b for a, b in zip(report["model-A"][1], report["model-B"][1])]
lo, hi = bootstrap_ci(diff, seed=1)
print(f"A − B 成對差異 {sum(diff) / len(diff):+.1%}  95% CI [{lo:+.1%}, {hi:+.1%}]"
      f"  →  {'差異顯著' if lo > 0 or hi < 0 else '整體分不出高下，看題型'}")

again = evaluate("model-A", tasks, K, seed=2026)
assert again == report["model-A"][0]              # 同 seed 重跑結果一致：可重現
assert lo < 0 < hi                                # 整體平手
assert manifest_hash(tasks) != manifest_hash(tasks[:-1])
```

```text
bluebird-bench v1  manifest=8473911a8215  tasks=32  trials/task=4
model-A  pass@1=79.7% [71.9%, 87.5%]  pass^4=46.9%  |  query=91%  refund=91%  return=84%  edge=53%
model-B  pass@1=82.0% [75.0%, 88.3%]  pass^4=46.9%  |  query=97%  refund=84%  return=72%  edge=75%
A − B 成對差異 -2.3%  95% CI [-13.3%, +7.0%]  →  整體分不出高下，看題型
```

逐行解說這份報告。第一行是報告的表頭：benchmark 名稱與版本、題庫的 manifest 指紋、題數與每題 trial 次數。最後一個 assert 驗證「少一題，manifest 就不同」，這保證任何人修改題庫，舊報告上的指紋就對不上，不會在不知情下比較兩個不同版本的分數。

第二、三行是兩個候選模型的結果。model-A 的 pass@1 是 79.7%，95% 信賴區間 [71.9%, 87.5%]；model-B 是 82.0%，區間 [75.0%, 88.3%]。兩個區間大幅重疊，就像 28.7 節的示意圖。區間是用 bootstrap 以「題」為單位重抽算出的：同一題的 4 次 trial 高度相關（環境一樣、題目一樣），如果把 128 次 trial 當成 128 個獨立樣本，區間會窄得不合理，這就是 28.7 節說的群聚效應。兩個模型的 pass^4 都是 46.9%：平均通過率八成左右，但只有不到一半的題目能 4 次全對，這是客服 agent 真正要面對的穩定性。

每行右半部的題型細分才是決策的關鍵。兩個模型在 query 與 refund 上差距較小、方向相反，但 model-A 在 return 題（已出貨要改建退貨單）是 84%，model-B 只有 72%；edge 題（查無訂單要請顧客確認）則反過來，model-A 53%、model-B 75%。對青鳥來說，return 題做錯代表「對已出貨的訂單宣稱退款成功」，會直接造成客訴與財務爭議；edge 題做錯則多半是回答不夠好，風險比較低。所以就算 model-B 的整體分數略高，青鳥仍可能選 model-A，或者針對 edge 題改善 tool 的錯誤訊息後再比一次。

第四行是成對比較：對每一題計算「A 的通過率減 B 的通過率」，再對這 32 個差值做 bootstrap。平均差異 −2.3%，95% 信賴區間 [−13.3%, +7.0%] 包含 0，所以整體上分不出高下，報告自動提示「看題型」。程式最後的 assert 還驗證了兩件事：用同一個 seed 重跑 model-A，每一題每一次 trial 的結果完全相同，這是可重現性；每次 trial 都用 `copy.deepcopy` 建立全新的環境，上一次 trial 建立的退貨單不會漏到下一次，這是隔離性。真實模型無法用 seed 保證重現，但環境的隔離與題庫的版本化，是任何 harness 都必須做到的。

| 報告欄位 | 回答的問題 | 本例的值 | 沒有它會怎樣 |
|---|---|---|---|
| 版本與 manifest | 比的是同一份題目嗎？ | v1、8473911a8215 | 改過題目的新舊分數被混在一起比 |
| trial 次數 | 結果穩不穩？ | 4 | 單次的運氣被當成能力 |
| 通過率與 CI | 差距是不是雜訊？ | 79.7% [71.9%, 87.5%] | 2 點的差距被當成結論 |
| pass^k | 使用者會不會遇到不一致？ | 46.9% | 高估線上穩定性 |
| 題型細分 | 哪裡強、哪裡弱？ | return 84% vs 72% | 整體平手時無從選擇 |
| 成對差異 | A 真的比 B 好嗎？ | −2.3% [−13.3%, +7.0%] | 用兩個獨立區間做出過強或過弱的結論 |

這張表把報告的每個欄位和它防止的錯誤對應起來。要上線的版本還需要加上每題的成本與時間，這兩個欄位在本例中被省略，但在真實的模型比較中往往是決定性的。把這段程式接上真實模型時，只要把 `scripted()` 換成真實的 model adapter（第 25 章），並把環境換成第 17 章的 sandbox 或青鳥的測試資料庫即可；題庫、grader、統計與報告的部分不需要改。

## 28.13 實務應用

以下四個情境，說明公開 benchmark 與內部 benchmark 在不同產品中如何分工。

**情境一：電商客服 agent 的模型選型（青鳥的主線）**。青鳥最後的流程是：每當有新模型發布，先看 τ-bench 系列零售領域在同一版本下的分數與區間，排除明顯落後的；剩下的候選在 bluebird-bench 的 held-out 集上每題跑 4 次，看題型細分與 pass^k，特別盯緊「錯誤承諾退款」這類高風險題型；通過的候選再以影子流量跑一週，比較轉真人率與客訴率。這個流程讓阿哲的「換模型」提案從一次會議的爭論，變成一份有數字、有區間的報告。要注意的是使用者模擬器：如果內部 benchmark 也用 LLM 扮演顧客，模擬器本身要固定版本，並抽樣人工檢查它是否照著題目設定說話。

**情境二：選購或自建 coding agent**。評估外部 coding agent 產品時，公開分數是「模型＋該產品的 scaffold」的分數，這反而是優點：你要買的就是那個完整系統。但它仍然是在開源 Python 專案上量到的。比較穩健的做法是從自己已合併的 PR 回推題目：取 PR 之前的 commit 作為初始狀態、PR 描述作為指示、PR 附帶的測試作為隱藏 grader，這等於在自己的程式碼庫上重建一個小型 SWE-bench。這種題目天然不在任何公開訓練資料中（只要 repo 是私有的），也天然符合自己的語言與規範。另外要量測 agent 會不會修改測試來讓測試通過，grader 執行前要把測試檔還原成原始版本。

**情境三：研究與資料分析 agent**。青鳥的營運 research agent 要回答「上週退貨率為什麼上升」這類問題，最終產出是一份報告。GAIA 與 BrowseComp 可以參考它的搜尋與多步推理能力，但報告品質無法精確比對。內部 benchmark 的做法是把問題拆成可驗證的部分：報告中的關鍵數字（退貨率、上升的品類）用程式比對標準答案，結論的合理性與引用則用拆成二元檢查的 rubric 交給 judge，並與分析師的人工評分校準。歷史分析需求的「答案」會隨資料更新而改變，所以題目要綁定資料快照的日期。

**情境四：法律、金融等專業領域**。這類領域往往沒有合適的公開 benchmark，或公開 benchmark 只測知識不測工作流程。依公開文章，法律 AI 公司 Harvey 在沒有公開 benchmark 的情況下自建評測，以三個前沿模型組成 judge committee 各自獨立評分再彙總，以降低單一 judge 的偏誤；它的 RL 研究也以合成的併購資料室作為環境、以專家 rubric 作為 reward。這說明在專業領域，內部 benchmark 不只是選模型的工具，也是訓練與優化（第 30 章）的基礎。要注意的是，自建 benchmark 的分數是自報數字，對外引用時要說明題目來源與評分方式。

| 情境 | 公開 benchmark 的角色 | 內部 benchmark 的題目來源 | grader | 特別注意 |
|---|---|---|---|---|
| 電商客服 | τ-bench 系列初篩 | 客訴、退款爭議、production trace | DB 最終狀態＋二元 rubric | 使用者模擬器要固定版本 |
| coding agent | SWE-bench 系列、Terminal-Bench 初篩 | 已合併的內部 PR | PR 附帶的測試 | 執行前還原測試檔，防止改測試 |
| research agent | GAIA、BrowseComp 參考搜尋能力 | 歷史分析需求 | 關鍵數字比對＋rubric judge | 題目綁定資料快照日期 |
| 專業領域 | 通常沒有合適的 | 專家設計的工作流程題 | 多模型 judge committee＋人工校準 | 自報分數要說明方法 |

這張表的共同點是：公開 benchmark 都只出現在「初篩」或「參考」的位置，真正的決策都落在題目來自自己的內部 benchmark 上。

> [!note] 2026 現況
> 截至 2026 年 10 月，主流工具對 benchmark 的支援大致如下（依公開文件整理，細節以官方文件為準）：Inspect 以 Task＝dataset＋solver＋scorer 的抽象執行評測，支援 Docker、Kubernetes 等 sandbox，Inspect Evals 收錄大量現成 benchmark；Terminal-Bench 以 Harbor framework 執行，同一套工具也能用來跑自訂任務；SWE-Bench Pro 排行榜標示所用 harness，並附誤差值；Braintrust、LangSmith、Langfuse 等平台以 dataset 與 experiment 的形式管理內部評測，支援把 production trace 轉成題目。NIST CAISI 於 2025-12 發表了關於 agent 評測作弊的研究，提醒 grader 要防範 agent 修改測試或讀取答案。

## 28.14 設計檢查清單

引用公開分數或建立內部 benchmark 時，逐項回答下面的問題。

1. 引用的每個分數是否都附上 benchmark 名稱、版本、查詢日期與來源（官方排行榜或廠商自報）？
2. 這個分數用的是什麼 scaffold、幾次嘗試、什麼步數與 token 預算？和你要比較的對象相同嗎？
3. 題數是多少？兩個分數的差距是否大於信賴區間的寬度？比較是否使用成對方法？
4. 這個 benchmark 是否已經飽和？你是否抽樣讀過前沿系統仍然失敗的題目？
5. 是否有污染的跡象（題目公開多久、是否有 held-out 集或新題目的分數可以對照）？
6. 公開 benchmark 的任務分布（語言、領域、tools、成功定義）和你的任務有哪些落差？這些落差是否都有內部題目補上？
7. 內部 benchmark 的每一題是否都有參考解，並驗證過 grader 能區分正確與常見錯誤解？
8. grader 是否以最終環境狀態為主？需要 judge 的維度是否拆成二元檢查並與人工校準？
9. 題庫是否有版本號與 manifest？修改題目時是否升版、並避免新舊分數直接比較？
10. 是否區分 dev 集與 held-out 集？調 prompt 時看的題目是否和最後計分的題目分開？
11. 題庫檔案是否嵌入 canary？是否定期檢查 prompt、few-shot 範例、fine-tune 資料與對外文件有無外流？
12. 每次 trial 是否在全新、隔離的環境中執行？setup 失敗的題目是否標記為無效而不是記 0 分？
13. 報告是否包含 pass^k、題型細分、每題成本與時間，而不只是單一通過率？
14. 是否有題目的畢業（進 regression suite）與汰換機制，避免內部 benchmark 自己飽和？

## 28.15 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| 公開分數高，換上去後內部表現沒變或變差 | 任務分布不同、scaffold 不同 | 比較公開 benchmark 與內部題目的語言、tools、題型 | 以內部 benchmark 為決策依據，公開分數只做初篩 |
| 兩次跑分名次顛倒 | 題數太少、單次 trial、差距小於誤差 | 計算信賴區間與成對差異的區間 | 增加題數與 trial 次數，改用成對比較 |
| 某題多個模型都是 0 分 | 錯題、grader 有誤或環境 setup 失敗 | 用參考解跑一次，讀 trajectory | 修題或標記無效，並升級 benchmark 版本 |
| 新模型在舊題上明顯高於新題 | 資料污染 | 時間切分比較、補完探測 | 改用 held-out 或新題的分數，汰換已外流題目 |
| 同一題這次通過、下次失敗，且和模型無關 | 環境沒有隔離，前一次 trial 的副作用殘留 | 檢查 trial 開始時的環境狀態 | 每次 trial 從快照或 deepcopy 重建環境 |
| 內部分數持續上升，但線上客訴沒減少 | 調 prompt 時反覆看 held-out 題，過度擬合 | 檢查誰、何時存取過 held-out 集 | 分開 dev 與 held-out，限制存取，換一批新題 |
| agent 分數突然大幅提高 | agent 找到捷徑：修改測試、讀到答案、grader 漏洞 | 讀高分 trial 的 trajectory，找異常動作 | grader 執行前還原測試檔、隔離答案、補強檢查 |
| 和三個月前的報告比較出現大幅變化 | 題庫或 scaffold 已經改版 | 比對 manifest 與 scaffold 版本 | 報告一律附 manifest；只比較同版本 |

## 本章重點整理

- 任何 benchmark 都可以拆成任務、環境、grader、scaffold 四個零件；排行榜上的數字是「模型 × scaffold × 版本 × 預算」的乘積，不只是模型的分數。
- agent benchmark 偏好執行式評分：檢查測試、資料庫或檔案的最終狀態，而不是 agent 說了什麼。
- SWE-bench 以隱藏的 FAIL_TO_PASS 與 PASS_TO_PASS 測試判定 patch，家族中的 Verified、Pro、bash-only 等變體分別在修補錯題、污染與 scaffold 差異。
- τ-bench 系列用 LLM 使用者模擬器、政策文件與資料庫狀態評估客服 agent，並推廣了衡量穩定性的 pass^k。
- OSWorld、WebArena 這類電腦與網頁 benchmark 的難點在環境重置與 setup 穩定性，讀分數時要看清楚分母與觀察形式。
- GAIA、BrowseComp 測多步搜尋與資訊整合，答案短而好驗證，但不測綜合分析與寫作能力。
- 通過率的信賴區間大約和題數的平方根成反比；500 題的誤差約正負 3.5 個百分點，2 點的差距通常是雜訊。
- 同一題的多次 trial 高度相關，計算區間時要以題目為單位；比較兩個系統時優先用成對方法。
- 飽和、污染、版本漂移、scaffold 差異與成本未標準化，會讓分數量到能力以外的東西，每個分數都要逐項檢查。
- 污染可以用 n-gram 重疊、canary 字串、補完探測與時間切分偵測；補完探測命中是強證據，沒命中不能證明沒有污染。
- 公開 benchmark 最好的用途是初篩；上線決策要依序經過內部 benchmark 與影子流量或 A/B。
- 內部 benchmark 的題目來自自己的工作紀錄，每題要有參考解與經過驗證的 grader，並以版本號與 manifest 凍結。
- 分開 dev 與 held-out 集，調 prompt 時看的題目不能是最後計分的題目，否則等於自己污染自己。
- 內部 benchmark 的報告要包含 CI、pass^k、題型細分與成本；整體平手時，題型細分與業務風險決定選擇。

## 延伸問答

> [!question]- Q1. benchmark 和第 27 章的 eval set 有什麼不同？既然都有題目和 grader，為什麼要分開談？
> 兩者的機制幾乎一樣，差別在目的與管理方式。eval set 是為了守住自己系統的品質：隨著產品演進持續增修，新的失敗案例會被加進來，主要用在 PR gate 與回歸測試，所以它「應該常常變」。benchmark 的目的是比較：在相同條件下比較不同的模型、scaffold 或時間點，所以它「應該盡量不變」，任何修改都要升版本。
>
> 這個差別帶出不同的管理要求。benchmark 需要版本號與 manifest、需要 held-out 切分與存取控制以防污染、需要固定 scaffold 與預算，報告也要附信賴區間才能比較；eval set 則更重視覆蓋最新的失敗模式與執行速度。實務上兩者常共用題庫與 harness：題目在 eval set 中誕生，經過驗證後被選入某一版的內部 benchmark，飽和後再畢業回 regression suite。分開談，是為了讓讀者知道同一批題目在不同用途下要遵守不同的紀律。

> [!question]- Q2. 廠商說新模型在某 benchmark 上「比上一代高 5 個百分點」。你會問哪些問題，才決定要不要相信這個差距？
> 我會依 28.8 節的表逐項問。第一是統計：題數多少、有沒有附信賴區間、是單次還是多次 trial 的平均；以 500 題來說，單一分數的誤差約正負 3.5 點，5 點的差距勉強在邊緣，需要看成對比較或多次 trial 才能確定。第二是版本：兩代模型是否在同一版本的題目與環境上評測，持續更新型的 benchmark 尤其要確認。
>
> 第三是 scaffold 與預算：兩代是否用同一個 agent、同樣的步數與 token 上限、同樣的嘗試次數；如果新模型同時換了 scaffold 或允許更多次嘗試，5 點可能大部分來自那裡。第四是成本：新模型每題花多少 token 與時間。第五是污染與飽和：題目公開多久、新模型的訓練截止日期晚了多少、有沒有 held-out 集的對照分數。這些都有合理答案之後，我仍然只把它當作進入內部 benchmark 的門票，而不是換模型的理由。

> [!question]- Q3. 估算題：你希望內部 benchmark 能分辨兩個候選之間 5 個百分點的差距（基準通過率約 60%），大約需要多少題？如果每題跑 4 次 trial，成本怎麼估？
> 用 28.7 節的兩比例樣本數公式，在 95% 信心與 80% 檢定力下，60% 對 65% 每邊大約需要 1,469 個獨立樣本。這個數字假設兩邊做的是不同的題目，而且每個樣本互相獨立。實際上兩個候選做同一組題目，用成對比較只看兩者結果不一致的題目，所需題數通常可以明顯減少，減少多少取決於兩個模型的結果有多相關，越相關越省。
>
> 多次 trial 也有幫助但不是線性的：同一題的 4 次 trial 高度相關，不能當成 4 個獨立樣本，它們主要降低「題目內」的隨機性，題目之間的差異只能靠更多題目來平均。所以務實的估算是：先以幾百題、每題 3 到 4 次 trial、成對比較為起點，跑完後看實際的區間寬度再決定要不要擴題。成本則是題數 × trial 數 × 每次 trial 的平均模型呼叫數 × 每次呼叫的 token 成本，例如 400 題 × 4 次 × 10 步，就是 16,000 次模型呼叫，再乘上每步平均 token 與單價。

> [!question]- Q4. 程式找錯：同事的 harness 把每題 4 次 trial 攤平成一個長串列，直接用 Wilson 區間計算整體通過率的 CI。這樣有什麼問題？
> 問題在於 Wilson 區間假設每個樣本互相獨立，但同一題的 4 次 trial 共用同一個題目與環境，結果高度相關：難題往往 4 次都錯，簡單題 4 次都對。把 32 題 × 4 次攤平成 128 個樣本，等於假裝有 128 道獨立的題目，算出來的區間會比實際窄很多，讓人對差距過度自信，這就是 28.7 節提到的群聚效應。
>
> 修法有兩種。一種是像 28.12 節的 harness，先算每一題的平均通過率，再以「題」為單位做 bootstrap 重抽，讓區間反映題目之間的變異。另一種是使用 clustered standard error，把同一題的 trial 視為一個群聚。同樣的道理也適用於來自同一個 repo、同一個網站或同一位使用者的多道題目：它們之間也可能相關，報告時應該說明群聚的單位。

> [!question]- Q5. 你發現 bluebird-bench 的分數這一季持續上升，但線上的客訴率沒有下降。可能是什麼原因？怎麼排查？
> 最常見的原因是內部 benchmark 被自己「污染」了：團隊在調 prompt 或 tool 描述時反覆看 held-out 集的失敗案例，針對那些題目修補，分數上升反映的是對特定題目的擬合，而不是泛化能力。第一步是查存取紀錄，確認 held-out 集是否被用在開發迴圈裡；第二步是拿一批新題目（例如最近一個月的客訴轉成的題目）來跑，如果新題的分數明顯低於舊題，就證實了擬合。
>
> 其他可能的原因包括：題庫已經飽和，剩下的失敗題目和線上的主要客訴類型無關；題型分布和線上流量不同，例如 benchmark 中退款題占四分之一，但線上客訴主要來自物流延遲的回覆語氣；grader 量的東西和客訴的原因不一致，例如 grader 只看資料庫狀態，客訴卻是因為回覆太冷淡。排查方法是把最近的客訴分類，對照 benchmark 的題型與 grader 檢查項目，補上缺的題型與檢查維度，並重新分配 dev 與 held-out 集。

> [!question]- Q6. 比較 coding agent 產品時，應該讓每個產品用自己的 scaffold，還是統一用同一個 scaffold？
> 取決於你要回答的問題。如果你要買的是一個完整產品，例如在幾個 coding agent 中挑一個給工程師使用，那應該讓每個產品用它自己的 scaffold，因為你買的就是「模型＋scaffold」的整體，統一 scaffold 反而量不到產品的真實表現。這時要統一的是任務、環境、grader 與預算（時間、成本上限），讓比較公平。
>
> 如果你要回答的是「哪個模型最適合放進我們自己的 agent」，例如青鳥要為 `loom` 上的 coding agent 選模型，那就要固定 scaffold，只換模型，否則分數的差異分不清來自模型還是來自 agent 程式。公開排行榜也有同樣的區分：SWE-bench 的 bash-only 排行榜固定極簡 scaffold 比模型，其他排行榜則比較完整系統。兩種問題都合理，錯誤的是混著用：拿完整產品的分數去推論模型的優劣，或拿固定 scaffold 的分數去推論產品體驗。

> [!question]- Q7. 補完探測沒有命中，可以宣稱「這個模型沒有被這個 benchmark 污染」嗎？
> 不行。補完探測量的是「模型能不能逐字重現題目的後半段」，這是記憶的強證據，但不是污染的唯一形式。模型可能看過改寫後的版本、看過題目的討論與解法但沒看過原文、或者只看過解答（patch）而沒看過 issue 描述，這些情況下它不會逐字接出題目，卻仍然可能因此在這題上表現特別好。另外，有些模型經過訓練後會傾向不輸出長段原文，也會降低探測的靈敏度。
>
> 所以補完探測的結論是不對稱的：命中時幾乎可以確定題目被看過，應該把這題從比較中移除；沒命中時只能說「沒有逐字記憶的證據」。要更有把握，需要搭配其他方法：時間切分（比較訓練截止日前後發布的題目表現）、使用不公開的 held-out 題目、以及在內部 benchmark 中定期換新題。最終的防線是使用從未公開的題目，這也是內部 benchmark 的價值。

> [!question]- Q8. 面試追問：請設計一個給公司內部多個 agent 團隊共用的 benchmark 平台。你會怎麼處理版本、隔離、污染與成本？
> 我會先把平台的核心抽象定為「題庫版本」與「評測執行」。題庫依 agent 類型分成多個 suite，每個 suite 有版本號與 manifest，題目有 dev 與 held-out 兩種可見性，held-out 只有平台本身與少數審查者能讀取，各團隊只拿得到彙總結果與脫敏的失敗摘要，避免團隊無意間針對 held-out 擬合。每次評測執行記錄受測的模型、scaffold 版本、預算設定、trial 次數與執行日期，報告固定包含 CI、pass^k、題型細分、每題成本與時間。
>
> 執行層面，每個 trial 在獨立的 sandbox（第 17 章）中從快照啟動，setup 失敗標記為無效；grader 與答案放在 agent 無法存取的位置，執行前還原測試檔。污染防護包括題庫檔案嵌入 canary、定期掃描 prompt 倉庫與 fine-tune 資料集、對外部模型做補完探測，以及每季汰換一部分題目。成本方面，平台提供「快速模式」（dev 集、單次 trial）給日常開發，「正式模式」（held-out、多次 trial）只在模型或 scaffold 選型時執行，並為每個團隊設定配額。最後，題目的生命週期要有負責人：誰審查新題、誰判定錯題與升版、誰決定題目畢業進 regression suite，這比任何技術設計都更決定平台能不能長期可信。

## 延伸閱讀

- Jimenez et al.〈SWE-bench: Can Language Models Resolve Real-World GitHub Issues?〉（ICLR 2024）
- Yao et al.〈τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains〉（2024）與 Barres et al.〈τ²-Bench: Evaluating Conversational Agents in a Dual-Control Environment〉（2025）
- Xie et al.〈OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments〉（NeurIPS 2024）
- Mialon et al.〈GAIA: A Benchmark for General AI Assistants〉（2023）
- Wei et al.〈BrowseComp: A Simple Yet Challenging Benchmark for Browsing Agents〉（OpenAI，2025）
- Evan Miller〈Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations〉（2024）
- Anthropic Engineering Blog〈Demystifying evals for AI agents〉（2026）
- Scale AI〈SWE-Bench Pro〉論文與排行榜（2025）
