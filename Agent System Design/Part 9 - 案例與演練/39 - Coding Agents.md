---
chapter: 39
title: 案例：Coding Agents
part: 9
---

# 第 39 章　案例：Coding Agents

> [!abstract] 本章地圖
> **核心問題**：市面上最成功的 coding agent，在 loop、tools、context、sandbox、審核與評估上各做了什麼選擇？哪些是共同的骨架，哪些是值得借鏡的差異？
>
> **你會學到**：
> - 用六個維度（loop、tools、context、sandbox 與權限、審核與驗證、評估）拆解任何一個 coding agent，並畫出它的架構圖
> - 說清楚 Claude Code、Codex、Gemini CLI、Cursor、Devin、GitHub Copilot coding agent 的公開架構重點與彼此的差異
> - 理解 coding agent 最關鍵的 tool：檔案編輯的三種做法（整檔寫入、唯一匹配取代、patch），以及各自的失敗模式
> - 比較本機互動型與雲端背景型兩種產品形態的安全模型、權限模式與驗證方式
> - 用 Python 模擬唯一匹配編輯、apply-patch、測試驗證閘門、分階段 compaction 與權限模式
> - 整理出一份可以直接用在自家 coding agent 的「可借鏡的設計」清單
>
> **前置知識**：第 4 章（agent loop）、第 5 章（tool 設計）、第 10 章（compaction）、第 13 章（大量工具與 code-as-action）、第 17 章（sandbox）、第 20 章（multi-agent 與 worktree）、第 21 章（核准與自動核准 classifier）

## 39.1 故事：買、借，還是自己做？

青鳥科技的內部 coding agent 原型，已經在 sandbox 裡以 L4 跑了幾個月：工程師在工單上留言，agent 讀程式、改檔案、跑測試、開 pull request。第 20 章那次三個 agent 一起改壞 `refund_policy.cfg` 的事故之後，團隊改成每張工單一個 git worktree，平行寫入的問題算是解決了。阿哲這週帶來新的需求卡：「全公司四十位工程師都要用，而且要能在晚上自己跑，早上看 PR。」阿哲問得很直接：「市面上的產品這麼多，我們要買、要拿開源的改，還是繼續自己做？」

Iris 翻了原型最近一個月的事故紀錄，發現問題和模型聰不聰明關係不大。第一件，agent 要把正式的 `AUTO_REFUND_LIMIT = 500` 改成 800，它的編輯工具做的是「取代第一個出現的字串」，結果改到上面一行測試假資料用的 `DEFAULT_LIMIT = 500`，CI 全綠，正式上限一點都沒變。第二件，agent 回報「已修好」，但它其實沒跑測試；工程師早上打開 PR，CI 一片紅。第三件最難查：一個跑了四十分鐘的任務，context 塞滿 pytest 的輸出，被截斷之後，agent 忘了工單上寫的「不准修改 tests/ 底下的測試」，最後改了一個測試讓它通過。

Maya 補上第四件：原型的 shell tool 沒有區分指令，agent 曾經在自己的分支上執行 `git push --force`，也曾經試圖讀取 home 目錄下的雲端憑證檔，只是剛好被 sandbox 的檔案邊界擋下。「這不是運氣的問題，」Maya 說，「我們要知道市面上的產品是怎麼把這些擋掉的，再決定要不要自己做。」

老陳給 Iris 兩週時間，題目是拆解六個產品：Claude Code、Codex、Gemini CLI、Cursor、Devin 與 GitHub Copilot coding agent。老陳的要求有三條：不要抄功能清單，要拆到 loop、tools、context、sandbox、審核、評估六個維度；只寫公開資訊，每一條都標日期；看不到的地方寫「公開資料未說明」，不要猜。這一章就是 Iris 的拆解報告。我們先建立拆解框架與共同骨架，再談 coding agent 最關鍵的編輯工具，接著逐一拆解六個產品，最後整理共同模式、差異與可借鏡的設計，並在「動手做」用 Python 重現上面四個事故與它們的修法。

> [!note] 本章的資料範圍
> 本章的產品資訊截至 2026 年 10 月，來源是各產品的官方文件、官方 engineering blog，以及兩個開源專案（Codex CLI 與 Gemini CLI）的原始碼。閉源產品的內部實作只寫官方公開說明的部分；標為「未查證」或「早期公開資料」的內容，代表本書寫作時沒有重新確認，請以官方最新資料為準。產品更新非常快，具體版本、數字與功能名稱集中放在各節的「2026 現況」區塊。

## 39.2 拆解框架：六個維度與一副共同的骨架

拆解一個 coding agent，最容易犯的錯是被功能清單牽著走：「它支援 MCP、有 plan mode、可以開 PR」。功能清單告訴你它能做什麼，卻沒告訴你它為什麼可靠。老陳要 Iris 改問六個問題，每個問題對應本書前面的一章：**loop**（誰決定下一步、怎麼停、能不能中途插話，第 4 章）、**tools**（給模型什麼動作空間，尤其是怎麼編輯檔案，第 5 章）、**context 策略**（專案指令怎麼載入、長任務怎麼壓縮、怎麼用 prompt caching 與子 agent 控制成本，第 9、10 章）、**sandbox 與權限**（動作在哪裡執行、哪些要問人，第 17、21 章）、**審核與驗證**（誰確認結果是對的，第 21、27 章）、**評估**（廠商怎麼知道新版本變好了，第 27、28 章）。

這裡的 **harness**（駕馭程式）和第 4 章的定義相同：包在模型外面、負責呼叫模型、執行 tool、管理 context 與權限的那層程式。coding agent 產品的差異，幾乎全部在 harness，而不在 loop 本身。下面這張圖是 Iris 拆完六個產品後畫出的共同骨架。

```text
 介面層        終端機 CLI ─ IDE 外掛 ─ 桌面 app ─ Web ─ Issue／PR 留言 ─ Slack
                 │
 ┌───────────────▼──────────────────────────────────────────────────────────┐
 │ Harness                                                                  │
 │  ┌──────────┐   ┌────────────────────┐   ┌──────────────────────────┐    │
 │  │ 主 loop  │◄─►│ context 管理       │   │ 權限引擎                 │    │
 │  │ gather → │   │ 專案指令檔         │   │ 模式（唯讀／詢問／自動） │    │
 │  │ act →    │   │ tool 輸出清除      │   │ allowlist、classifier    │    │
 │  │ verify   │   │ 摘要式 compaction  │   │ 或 reviewer agent        │    │
 │  └────┬─────┘   │ cache 版面         │   └────────────┬─────────────┘    │
 │       │         └────────────────────┘                │                  │
 │       ▼ tool call                                     │ 每個動作先過這裡 │
 │  ┌──────────────────────────────────────────────────▼───────────────┐    │
 │  │ Tool dispatcher：read／search／edit 或 patch／shell／web／子 agent │    │
 │  │                  ＋ MCP、skills、hooks 等擴充                      │    │
 │  └──────────────────────────────┬─────────────────────────────────────┘    │
 │  session log（可 resume、fork、rewind）、檔案 checkpoint                   │
 └─────────────────────────────────┼──────────────────────────────────────────┘
                                   ▼
 環境層    sandbox（OS 原生、container、VM）：workspace 檔案、shell、測試、git
           egress 控制；憑證留在 sandbox 外
                                   │
 交付層    本機：檔案改動＋使用者看 diff     雲端：branch → pull request → 人審查
```

由上往下讀這張圖。介面層是使用者接觸產品的地方，同一個 harness 常常同時有 CLI、IDE、桌面與 Web 入口。harness 的核心是一個主 loop，Claude Code 的官方文件把它描述成 gather context（收集脈絡）、take action（行動）、verify results（驗證）三段交織；旁邊的 context 管理決定每一輪送給模型什麼，權限引擎決定每一個動作能不能做、要不要問人。tool dispatcher 把模型的 tool call 轉成真正的檔案讀寫與 shell 指令，並透過 MCP（第 14 章）、skills（第 12、13 章）與 hooks 擴充。下面的環境層是動作真正發生的地方，所有產品都把它放在某種 sandbox 裡。最底下的交付層分成兩種：本機產品把改動留在使用者的工作目錄，由使用者看 diff；雲端產品把改動推到一個 branch，開 pull request 交給人審查。

六個產品都長得像這張圖，差別在每一格的選擇。最大的分界線是**產品形態**：本機互動型（agent 在開發者的電腦上跑，開發者在旁監看）與雲端背景型（agent 在雲端的臨時環境裡跑，開發者事後看結果）。這條分界線決定了安全模型：本機型的威脅是「agent 碰到開發者電腦上不該碰的東西」，所以重點是 OS sandbox 與權限模式；背景型的威脅是「沒有人在旁邊看」，所以重點是環境隔離、可丟棄的 branch，以及 PR 審查這道最終關卡。

| 產品 | 主要形態 | 開源程度 | 主要交付物 | 本章的公開資料來源 |
|---|---|---|---|---|
| Claude Code | 本機 CLI／IDE／桌面為主，另有雲端執行 | harness 閉源；sandbox runtime 開源 | 工作目錄中的改動、commit、PR | 官方文件、engineering blog |
| Codex | 本機 CLI／IDE／桌面＋雲端任務 | CLI 開源（Apache-2.0） | 改動、diff、PR | 官方文件、CLI 原始碼 |
| Gemini CLI | 本機 CLI | 開源（Apache-2.0） | 工作目錄中的改動 | README、原始碼 |
| Cursor | IDE 內建 agent＋雲端 agent | 閉源 | 編輯器中的改動、PR | 官方 blog |
| Devin | 雲端 agent＋桌面與 CLI | 閉源 | PR | 官方 blog |
| GitHub Copilot coding agent | 雲端背景型（跑在 GitHub Actions） | 閉源 | branch 與 PR | GitHub 官方文件 |

這張表的最後一欄提醒一件事：開源的兩個產品（Codex CLI、Gemini CLI）可以讀到原始碼層級的設計，閉源產品只能依官方文章與文件拆解，深度自然不同。拆解報告要誠實地反映這個落差，不能用推測補齊。

## 39.3 編輯檔案：coding agent 最關鍵的一個 tool

六個產品的 tool 清單各不相同，但每一個都把大量心力花在同一個 tool 上：**編輯檔案**。原因很簡單，coding agent 的產出就是檔案的改動；讀錯檔案頂多浪費一步，改錯檔案卻可能通過 CI、進到 production。Iris 的第一個事故正是編輯工具的問題，而不是模型的問題。

讓模型修改檔案，業界大致有三種做法。**整檔寫入**是讓模型輸出整份新檔案，簡單但昂貴：改一行也要重寫五百行，長檔案還可能在重寫時漏掉或改動其他段落。**字串取代**（str_replace）是讓模型提供「舊字串」與「新字串」，harness 在檔案裡找到舊字串並換掉；它的輸出很短，但關鍵在「找到」的規則。**patch** 是讓模型輸出一份差異描述，像 `git diff` 那樣用上下文行、刪除行、新增行說明要改哪裡，可以一次描述多個檔案、新增與刪除檔案。

字串取代最重要的規則是**唯一匹配**：舊字串必須在檔案中剛好出現一次，否則拒絕執行，並告訴模型出現了幾次、在哪幾行，請它加上前後文讓字串唯一；確定要全部取代時，必須明確指定 replace all。以 Claude Code 為例，它公開的 Edit tool 說明就要求舊字串唯一（否則編輯失敗），並要求先讀過檔案才能編輯。為什麼不乾脆「取代第一個」？因為模型提供的舊字串代表它心中的某個位置，當字串出現兩次，harness 無法知道模型指的是哪一個；猜錯的代價是一個看起來成功、其實改錯地方的編輯，這正是最難發現的失敗。拒絕執行雖然多花一步，卻把「靜默的錯誤」變成「明確的錯誤」。

```text
 edit(path, old, new, replace_all=False)
   │
   ├─ path 不存在？ ─────────────────────► 錯誤：新檔案請用 write
   ├─ 這個 session 沒讀過 path？ ─────────► 錯誤：請先讀取（避免憑記憶改檔）
   ├─ old == new？ ──────────────────────► 錯誤：沒有任何變更
   │
   └─ 在檔案中搜尋 old
        ├─ 0 次 ──────────────────────────► 錯誤：找不到，請重讀並確認縮排與空白
        ├─ 2 次以上且未設 replace_all ────► 錯誤：出現 N 次（第 a、b 行），請加上下文
        └─ 剛好 1 次（或 replace_all）────► 寫入，回報改了哪幾行
                                              │
                                              └─► 檔案版本改變：之前讀到的內容過期
```

這張流程圖由上到下是四道事前檢查與一個搜尋結果分支。前三道檢查擋掉的是「模型對檔案狀態的誤解」：檔案不存在、沒讀過就改、改了等於沒改。其中「先讀再改」特別重要，因為模型可能憑訓練資料或前幾輪的記憶猜測檔案內容，而檔案可能已經被使用者、formatter 或另一個步驟改過。搜尋結果的三個分支中，只有剛好一次會寫入，零次與多次都轉成可行動的錯誤訊息回填給模型（第 4 章的原則：tool 的失敗是一種觀察）。圖最下面那一行提醒：寫入之後，模型先前讀到的檔案內容就過期了，下一次編輯要基於新內容。

patch 格式的代表是 Codex。它的 `apply_patch` tool 使用自訂的 patch 格式：以 `*** Begin Patch` 開頭、`*** End Patch` 結尾，中間用 `*** Update File:`、`*** Add File:`、`*** Delete File:` 標示每個檔案的動作，更新檔案時用 `@@` 開頭的區塊（hunk）列出上下文行、以 `-` 開頭的刪除行與以 `+` 開頭的新增行。patch 定位的依據是上下文行，而不是行號，因為模型很不擅長精確計算行號，而上下文行就算檔案前面多了幾行也還找得到。patch 的另一個關鍵性質是**全有或全無**（all-or-nothing）：一份 patch 中只要有一個 hunk 對不上，整份都不套用，否則檔案會停在「改了一半」的狀態，比沒改還難處理。

| 做法 | 模型輸出量 | 定位依據 | 典型失敗 | 適合的情境 | 代表產品（依公開資料） |
|---|---|---|---|---|---|
| 整檔寫入 | 整份檔案 | 不需定位 | 長檔案重寫時漏段、改到無關內容 | 新檔案、很短的檔案 | 各產品都有 write 類 tool |
| 字串取代（唯一匹配） | 舊字串＋新字串 | 舊字串在檔案中唯一 | 空白或縮排不符找不到；字串不唯一 | 單一檔案的局部修改 | Claude Code 的 Edit、Gemini CLI 的 edit |
| patch | 差異描述 | 上下文行（加上可選的錨點） | 上下文過期對不上；格式錯誤 | 一次改多個檔案、新增與刪除檔案 | Codex 的 apply_patch |
| 大模型描述＋小模型套用 | 粗略的改動意圖 | 由套用模型推斷 | 套用模型誤解意圖 | 早期產品常見，現在較少 | Cognition 公開文章指出這種雙模型做法常失敗 |

表格最後一列值得多說一句。早期有些產品讓大模型用自然語言或粗略的程式片段描述改動，再由一個便宜的小模型把它「套用」到檔案上。Cognition 在〈Don't Build Multi-Agents〉一文中提到，這種 edit-apply 雙模型的做法常常失敗，因為小模型會誤解大模型的意圖；現在的主流是由同一個模型決定並套用改動。這和第 20 章的結論一致：關鍵決定不要在兩個看不到彼此完整 context 的模型之間傳遞。

> [!warning] 常見誤解
> 「編輯失敗就讓 harness 自動用模糊比對（fuzzy match）找最接近的位置。」模糊比對能救回空白差異這類小問題，但它把「明確的錯誤」重新變回「可能靜默改錯」。如果要做，只對無害的差異（行尾空白、縮排的 tab 與空格）放寬，而且要在結果中告訴模型「使用了寬鬆比對，請確認」。改錯位置的代價，遠高於多一次重試。

## 39.4 Claude Code：單一 loop、分層權限與檔案 checkpoint

**為什麼值得先看它**：Claude Code 是 Anthropic 自己做的 coding agent，它的 harness 也以 Claude Agent SDK 的形式開放給開發者當函式庫使用（第 26 章），所以它的設計選擇會直接影響很多基於 SDK 打造的 agent。它的公開文件與 engineering blog 也是六個產品中最完整的。

**loop**：官方文件把它描述為單一主 loop，在收集脈絡、行動、驗證三個階段之間交織；使用者可以隨時中斷，也可以在 agent 執行中送出新訊息調整方向（新訊息在哪個時間點被讀到，以官方文件的最新說明為準）。**tools** 分成幾類：檔案讀寫與編輯、搜尋（glob 與 grep）、shell 執行、網頁搜尋與擷取、透過 LSP 外掛取得的程式碼智慧（跳到定義、找引用），以及編排類的 tool，例如啟動子 agent、向使用者提問、管理任務清單。擴充能力來自 MCP、skills、hooks（在 tool 執行前後觸發的使用者腳本）與 plugins（把這些打包成可安裝的套件）。

**context 策略**有四層。第一層是專案指令檔 `CLAUDE.md`（也可以讀 `AGENTS.md`），每個 session 開始時載入；第二層是自動維護的 `MEMORY.md`，只預載前面一段（有行數與大小上限）；第三層是 just-in-time 載入：檔案內容靠 glob、grep、read 按需讀取，而不是預先建向量索引，MCP tool 的定義預設延遲載入，透過 tool search 按需取用（第 13 章）；第四層是長任務的壓縮：接近上限時**先清除舊的 tool 輸出，再做摘要**，使用者可以在 `CLAUDE.md` 寫壓縮時要保留什麼，或用 `/compact` 指定重點。如果單一巨大的輸出讓 context 反覆爆滿，它會停止自動壓縮並回報錯誤，而不是無限循環。子 agent 預設從空白 context 開始，也可以 fork 目前的對話；不論哪種，子 agent 的 tool call 都不進主 context，只回傳結論（第 10、20 章）。

```text
 ┌────────────────────── Claude Code（本機 session）─────────────────────────┐
 │ 啟動時載入：system ＋ tools（核心 tool 常駐；MCP tool 延遲載入）           │
 │            CLAUDE.md／AGENTS.md ＋ MEMORY.md（截取前段）＋ skill 的描述    │
 │                                                                           │
 │  主 loop ── tool call ──► 權限檢查 ─────────────────────► 執行             │
 │    ▲          │            │ Plan：只讀                     │              │
 │    │          │            │ Manual：寫入與指令都問人        │ 編輯前先做   │
 │    │          │            │ Accept edits：專案內編輯放行    │ 檔案 snapshot│
 │    │          │            │ Auto：classifier 判斷          │（checkpoint）│
 │    │          │            ▼                               ▼              │
 │    │          │      OS sandbox：寫入限 workspace、網路預設拒絕            │
 │    │          └─► 子 agent（空白或 fork 的 context）── 只回傳結論 ──┐      │
 │    └──────────────── tool 結果、system reminder、排入的使用者訊息 ◄──┘     │
 │                                                                           │
 │ session 以 JSONL 存在本機：resume、fork、rewind                            │
 └───────────────────────────────────────────────────────────────────────────┘
```

這張圖由上往下是一次 session 的生命週期。啟動時載入的內容就是第 9 章說的穩定前綴：system、tools、專案指令與記憶。主 loop 提出 tool call 後先過權限檢查，四種模式由嚴到寬；通過的動作在 OS sandbox 裡執行，寫入限於工作目錄，網路預設拒絕。編輯檔案之前會先做 snapshot，這就是 **checkpoint**（檢查點），讓使用者可以把檔案倒回某一步；官方文件特別說明 checkpoint 和 git 是分開的，而且已經發生的遠端副作用（例如部署、寫入外部資料庫）無法倒回。子 agent 是 context 的垃圾回收：探索過程留在子 agent 裡，主 loop 只看到濃縮的結論。最底下的 session log 讓對話可以接續、分岔或倒帶，對應第 10 章「context 是 log 的可重建視圖」。

**sandbox 與權限**是它最有特色的部分。Anthropic 在 2026 年的工程文章中描述了兩層設計：OS 原生的 sandbox（macOS 用 Seatbelt，Linux 用 bubblewrap）先在環境層畫出確定性的邊界，permission mode 再決定邊界內的動作要不要問人。auto mode 的動機是 **approval fatigue**（核准疲勞，第 21 章）：使用者幾乎核准所有的請求，核准就失去意義。它的做法是三級：唯讀動作直接放行、專案內的編輯直接放行，其餘動作交給一個 transcript classifier 判斷；這個 classifier 只看使用者訊息與 tool call，刻意不看 agent 自己的說明文字與 tool 結果，所以 agent 無法說服它，tool 結果裡的注入內容也到不了它。連續或累計被拒太多次就升級給人。

**審核與驗證**：本機型的最終審核者是坐在旁邊的開發者，由開發者看 diff、決定要不要 commit。官方也提供在 CI 中執行與無人值守模式，文件建議無人值守時改用 devcontainer 這類更強的隔離。**評估**方面，Anthropic 公開了一次品質事故的 postmortem：為了降低延遲把預設的推理強度調低、一個快取最佳化的 bug 讓舊的推理內容每輪都被裁掉、一行限制 tool call 之間文字長度的 system prompt，三件事都讓使用者覺得 agent 變笨。結論是任何可能和「聰明程度」互相取捨的改動，都要做逐模型的 eval、ablation（一次拿掉一個元件看影響）、soak period（觀察期）與漸進 rollout。

> [!note] 2026 現況
> 截至 2026 年 10 月，依 Anthropic 官方文件與 engineering blog：Claude Code 的 permission modes 包括 Auto、Manual、Accept edits、Plan，v2.1.283 起 auto 是互動式 session 的預設起始模式；另有略過權限檢查的模式，官方定位為只在隔離環境使用（這一點本次未重新查證）。auto mode 的工程文章（2026-03-25）提到使用者核准了 93% 的權限請求；classifier 分兩階段（先做偏向攔阻的快速篩選，再只對被標記者做推理），連續 3 次或累計 20 次被拒即升級給人；完整 pipeline 在真實流量的誤擋率 0.4%，對真實「過度積極」行為的漏放率 17%，對合成外洩情境的漏放率 5.7%。〈How we contain Claude across products〉（2026-05-25）提到 sandbox 讓權限提示減少 84%，並記錄了 clone 下來的 repo 的 project hooks 在信任對話框之前就被執行的事故（之後改為延後解析專案設定）。MEMORY.md 預載前 200 行或 25KB；〈Writing effective tools for agents〉（2025）提到 Claude Code 預設把單次 tool 回應上限設在 25,000 tokens。品質 postmortem 發布於 2026-04-23。實驗性的 agent teams 功能需以環境變數開啟。

## 39.5 Codex：patch 格式、sandbox 模式與 reviewer agent

**為什麼值得看**：Codex CLI 是開源的（Rust 實作），所以可以讀到原始碼層級的設計；它的 sandbox 與審批設計也是六個產品中最「可設定」的。Codex 同時有 CLI、IDE 外掛、雲端任務與桌面 app 等入口。

**loop** 建立在 OpenAI 的 Responses API 上，原始碼中有 thread、turn 與 rollout（session 紀錄）的模組，對應「一個對話串、一輪互動、一份可重播的紀錄」三個層次。**tools** 的處理器放在同一個目錄下，從名稱就能看出設計重點：`apply_patch`（39.3 節的 patch 格式）、`shell` 與統一的執行介面、`tool_search` 與 MCP 相關處理、`plan`（任務計畫）、`request_user_input` 與 `request_permissions`（向使用者提問與要權限）、`view_image`、`web_search`，以及多 agent、`code-mode`（讓模型寫程式來編排 tool，第 13 章的 code-as-action）等能力。

**context 策略**有兩個特別值得借鏡的設計。第一，專案指令檔是 `AGENTS.md`，這個檔名後來被多個產品採用，成為跨產品的慣例。第二，compaction 被明確框成**交接**：原始碼中的壓縮 prompt 開頭寫著「You are performing a CONTEXT CHECKPOINT COMPACTION. Create a handoff summary for another LLM that will resume the task.」，要求摘要包含進度與關鍵決定、限制與偏好、剩餘步驟、關鍵資料；接續時則告訴模型「另一個模型已經開始解這個問題，並留下了摘要」。這和第 10 章「摘要就是交接筆記」完全一致。Codex 還提供 `get_context_remaining` 與 `new_context_window` 兩個 tool，讓模型自己查詢剩餘的 context、自己決定何時開新視窗（新視窗不會清掉環境狀態），把「何時壓縮」的部分決定權交給模型。壓縮可以在本機做，也可以呼叫伺服器端的 compaction。

```text
 模型提出 shell 指令或 patch
        │
        ▼
 execpolicy：依指令前綴規則判斷 ── 明確禁止 ──► 拒絕
        │ 允許或需要判斷
        ▼
 在 sandbox 內執行（sandbox 模式決定邊界）
   read-only           只能讀
   workspace-write     可寫 workspace（預設）
   danger-full-access  沒有邊界
        │
        ├─ 邊界內 ───────────────────────────► 直接執行，結果回填
        │
        └─ 需要越過邊界（寫 workspace 外、連網）
               │ approval 政策
               ├─ never ──────────────────────► 不升權，回填失敗
               └─ on-request
                     ├─ 問使用者
                     └─ auto-review：交給隔離、同步的 reviewer agent
                         （只決定升權請求，不改變 sandbox 本身）
```

這張圖是 Codex 處理一個動作的路徑。第一關是 execpolicy，用指令前綴規則做確定性的判斷，例如明確禁止某些指令。第二關是 sandbox 模式，三種模式由緊到鬆，預設是可寫入 workspace；邊界內的動作直接執行，不用問人。只有需要越過邊界時，才看 approval 政策：設為 never 就不升權（適合無人值守、寧可失敗也不越界的場景），設為 on-request 就請求核准，核准者可以是使用者，也可以是 **auto-review**：把審批交給一個隔離、同步的 reviewer agent。官方文件強調，auto-review 不改變 sandbox 邊界，它只處理邊界上的升權請求。這和 Claude Code 的 classifier 是同一個想法的兩種實作：先用環境畫硬邊界，再用模型處理灰色地帶。

**審核與驗證**：本機使用時由開發者審 diff；雲端任務產出 diff 或 PR 交給人審查。官方另外推出了專門的 security review 功能。**評估**方面，公開資料沒有完整描述 Codex 內部的 eval 流程，但原始碼透露一個重要的工程實踐：repo 中依模型版本分別維護 system prompt 檔案。換模型時，prompt 不是共用一份然後祈禱它仍然有效，而是當成和模型綁定的元件，分開維護與測試（第 6、30 章）。

> [!note] 2026 現況
> 截至 2026 年 10 月，依 OpenAI 官方文件與 openai/codex repo（2026-10-02 讀取）：Codex CLI 以 Rust 實作（`codex-rs`，Apache-2.0），仍每天發布 alpha 版（例如 `rust-v0.162.0-alpha.5`）；Codex app 在 2026-07 併入 ChatGPT 桌面 app。sandbox 在 macOS 用 Seatbelt，Linux／WSL2 用 bubblewrap（找不到時改用內建的 helper），Windows 有原生 sandbox；sandbox 模式為 `read-only`、`workspace-write`（預設）、`danger-full-access`，approval 為 `on-request`、`never`（`untrusted` 已退役）；auto-review 以 `approvals_reviewer = auto_review` 設定，原始碼位於 `core/src/guardian/`。自動壓縮的門檻可用 `model_auto_compact_token_limit` 設定。2026 年陸續推出的功能包括 scheduled tasks（3 月 GA）、plugins（3 月）、memories（4 月）、computer use（4–5 月）、goal mode 與 hooks GA（5 月）、Record & Replay skills（6 月），以及 9 月底的「dots」（跨對話持續工作的委派單位）。OpenAI 另提供託管的 Codex harness（Agents API，第 26 章）。

## 39.6 Gemini CLI：pipeline 化的 context 處理與 model router

**為什麼值得看**：Gemini CLI 是 TypeScript 寫成的開源專案，核心套件的模組劃分（agent、agents、context、routing、sandbox、skills、policy、safety、scheduler、hooks、mcp、telemetry）幾乎就是本書的章節目錄，很適合當作「完整 harness 長什麼樣」的參考實作。

**tools** 涵蓋讀取（單檔與多檔）、寫入、edit、glob、grep（含 ripgrep）、ls、shell（含背景執行）、網頁擷取與以 Google Search 做 grounding 的網頁搜尋、memory tool、todo 清單、進入與離開 plan mode、向使用者提問、啟用 skill、宣告任務完成，以及 MCP 系列。它內建幾個專職的子 agent，例如探索 codebase 的 investigator、通用 agent、回答 CLI 使用問題的 agent，以及從對話中萃取 skill 的 agent；還能透過 A2A 協定（第 15 章）呼叫遠端的子 agent。

它最值得借鏡的是 **context 處理的 pipeline 化**：不是一個「壓縮」函式，而是一串各司其職的處理器。

```text
 每一輪送出前的 context pipeline（依原始碼模組整理）

 對話歷史
   │
   ▼
 (1) tool output masking
     舊的大型 tool 輸出 → 換成短標記，原文落地到 tool-outputs/ 目錄
     例外：啟用 skill、向使用者提問、plan mode 相關 tool 的輸出永不遮罩
   │
   ▼
 (2) 用量超過模型上限的一半？
     ├─ 否 ──► 原樣送出
     └─ 是 ──► chat compression：較舊的歷史 → 摘要
                                 最近約 30% 的歷史 → 保留原文
   │
   ▼
 (3) distillation／rolling summary 等處理器（持續濃縮長輸出與舊節點）
   │
   ▼
 (4) model router：依 classifier 或規則選模型 ──► 送出
```

這張圖由上到下是一輪送出前的處理。第 (1) 步遮罩舊的大型 tool 輸出，原文寫到磁碟上的目錄，context 裡只留標記；這是第 10 章「可還原的壓縮」：資料沒有消失，需要時可以再讀。它刻意排除了幾類輸出：skill 的內容、使用者的回答、計畫，這些是「狀態」而不是「可以重讀的資料」，遮罩掉就無法恢復。第 (2) 步在用量超過一半時做摘要式壓縮，但保留最近約 30% 的原文，因為模型下一步最需要的正是最近發生的事。第 (3) 步是更細的濃縮處理器。第 (4) 步的 **model router** 依任務選擇模型，原始碼中的策略包括 classifier、用小模型做的 classifier、數值型 classifier、fallback 與使用者覆寫。這兩件事和 39.11 節的動手做直接對應：先清 tool 輸出、再摘要，而且永不清除的清單要明確。

**sandbox 與權限**：sandbox 有 Linux（bubblewrap）、macOS（Seatbelt）與 Windows 原生三種實作，另有 policy 與 safety 模組，以及在信任資料夾之前不載入專案設定的 folder trust 機制，這和 Claude Code 事故後的修正是同一個方向：不受信任的 repo，不應該在使用者同意前就影響 agent 的行為。專案指令檔慣例是 `GEMINI.md`。**評估**的公開資料較少；原始碼有 telemetry 模組，但內部 eval 流程公開資料未說明。

> [!note] 2026 現況
> 截至 2026 年 10 月，依 google-gemini/gemini-cli repo（2026-10-02 讀取）：壓縮相關常數為 `DEFAULT_COMPRESSION_TOKEN_THRESHOLD = 0.5`、`COMPRESSION_PRESERVE_THRESHOLD = 0.3`；tool output masking 服務中的保護門檻與最小可裁門檻常數分別為 50,000 與 30,000。README 載明個人帳號的免費額度為每分鐘 60 次、每天 1,000 次請求，支援 1M context 的 Gemini 3 系列模型；專案每天發布 nightly 版（例如 v0.64.0-nightly）。

## 39.7 Cursor：把 prompt cache 當成一級約束的 harness

**為什麼值得看**：Cursor 是 IDE 形態的代表，agent 和編輯器整合在一起；它在 2026 年公開了一篇很具體的 harness 最佳化文章，示範了「harness 隨模型變強而變瘦」的實際做法。Cursor 是閉源產品，以下只依官方 blog。

**tools**：官方文章列出常駐的核心 tool 是讀取、搜尋、編輯、shell、向使用者提問與建立計畫；使用率低的內建 tool 與 MCP tool 都改成按需載入（第 13 章的 deferred loading）。早期公開資料也描述過 Cursor 為 codebase 建立語意索引，以及用專門的模型把編輯套用進檔案；這些設計的 2026 年現況，本書寫作時沒有重新查證。

**context 策略**是 Cursor 公開資料中最具體的部分，核心是 prompt cache。它利用模型 API 的顯式 cache breakpoint（快取斷點，指定「到這裡為止的前綴要快取」），在穩定的層（tools、system）之後、會成長的對話之前切一刀；會變動的內容（可用的 skills、子 agent、環境資訊）不放進 system，而是移到斷點之後的一則「phantom user message」（harness 自動插入、使用者看不到的訊息）。

```text
 ┌──────────────────────────────────────────┐
 │ tools（核心 tool 常駐，其他按需追加）     │  穩定層：每個 session 都一樣
 │ system prompt（瘦身後）                   │  → 跨 session 命中 cache
 ├──────────── cache breakpoint ────────────┤
 │ phantom user message：                    │  會變的環境資訊
 │   可用 skills、子 agent、作業系統、目錄    │  → 只影響這一段之後
 ├──────────────────────────────────────────┤
 │ 對話：user、assistant、tool 結果……         │  只在尾端追加
 │   read 的輸出：每 10 行才標一次行號        │  → 省下大量行號 token
 └──────────────────────────────────────────┘
```

這張 context 版面圖由上往下是穩定到變動。最上層的 tools 與 system 在每個 session 都相同，所以可以跨 session 命中 cache；如果把「這個專案有哪些 skills」寫進 system，每個專案的 system 都不同，整段前綴的快取就失效了。變動的環境資訊移到斷點之後，只影響它自己與後面的內容。最下層的對話只在尾端追加。最後一個細節很能說明這種 harness 工作的顆粒度：讀檔輸出原本每一行都標行號，改成每 10 行標一次，因為每個行號都要花幾個 token，而讀檔輸出是 context 中最大宗的內容之一。

**loop 與子 agent**：Cursor 在文章中說，模型變強之後，冗長的禁止事項與提醒變得不必要，system prompt 大幅瘦身；過去「提示模型多用子 agent 探索」的指示也拿掉了，因為模型已經會自己判斷；子 agent 只有在使用者或 harness 指定時才換模型，以控制協調成本。**評估**：Cursor 特別說明，自家的離線 eval 偏向困難題，所以 prompt 瘦身這類改動是用真實流量的 A/B 測試驗證品質不下降。Cursor 另外公開過一個長時間多 agent 實驗（第 20 章）：數百個 agent 平行寫一個大型專案，共享狀態檔加鎖的設計讓吞吐量崩潰，最後演化成遞迴的 planner 與只回傳一份交接結果的 worker。雲端 agent 則可以跑在客戶自管的機器上。

> [!note] 2026 現況
> 截至 2026 年 10 月，依 Cursor 官方 blog：harness token 效率文章（2026-09-23）報告整體 token 減少 7% 而品質不變，system prompt 減少約 66%；使用率低於 20% 對話的內建 tool 改為按需載入；先前 MCP tool 延遲載入讓有用到 MCP 的 session 總 token 降 46.9%，static context 中的 tool 描述 token 降 60%；cache breakpoint 加 phantom user message 讓 cold cache miss 降 20%；稀疏行號讓 cache-read token 降 1.6%。雲端 agent 可在自管機器上執行（2026-09-02），build 啟動速度提升 3 倍（2026-08-13）；Cursor Router 依任務選模型（2026-08-06，細節未讀）。Cursor 在 2026-08-14 宣布被 SpaceX 收購，並發布自家 Grok 4.6（08-12）與 Grok 4.7（09-21）模型。長時間多 agent 實驗文章發布於 2026-02-05。

## 39.8 Devin：雲端 agent 與混模型的 main＋sidekick

**為什麼值得看**：Devin（Cognition）是最早以「雲端裡的自主軟體工程師」定位的產品，Cognition 也是公開討論 coding agent 架構取捨最多的公司之一，包括第 20 章引用的〈Don't Build Multi-Agents〉。

依早期公開介紹，Devin 在雲端 VM 中工作，具備 shell、編輯器與瀏覽器，並有 planner、知識庫（Knowledge）、可重用的作業手冊（Playbooks）與 repo 索引等能力；這些是 2024 到 2025 年的資料，2026 年的細節本書沒有重新查證。2026 年 Cognition 的產品線擴展到桌面 app 與 CLI。**context 策略**上，Cognition 在 2025 年的文章中主張：超長任務要用專門的模型把歷史壓縮成關鍵細節、事件與決定，這件事「很難做對」，Cognition 為此 fine-tune 了一個小模型。

2026 年公開的 **Devin Fusion** 是最值得借鏡的設計：一個前沿模型當 main，一個便宜的模型當 sidekick，兩者平行運作，各自持有持久、可快取的 context；一個輕量的 classifier 在 session 中途決定由誰接手。

```text
 時間 ─────────────────────────────────────────────────────────────►

 main（前沿模型）   規劃、關鍵判斷 ──────┐                 ┌── 審查與收尾
   自己的 cached context                 │                 │
                                         ▼ 切換            │ 切換
 classifier         「接下來是例行執行」 ●                 ● 「需要判斷」
                                         │                 ▲
 sidekick（便宜模型）                    └─ 例行修改、跑測試┘
   自己的 cached context

 ● 切換點刻意選在 compaction 時：反正 context 要重組、cache 要 miss，
   這時換手不會多付一次 cache 懲罰
```

這張時序圖說明 Fusion 的兩個關鍵。第一，main 與 sidekick 各自持有 context，切換時不是把一個模型的 context 硬塞給另一個，而是各自維持自己的快取；這符合 Cognition 自己的原則：關鍵決定留在主 agent，context 要共享而不是轉述。第二，切換點選在 compaction 發生時。第 9 章說過，換模型等於整段 prompt cache 失效；而 compaction 本來就會改寫 context、讓 cache 失效，所以把換手放在這個時間點，等於免費換手。Cognition 也坦白公開了失敗案例：當「判斷本身就是交付物」的困難 feature 任務被委派給 sidekick 時，細微的意圖會遺失。

**評估**：Cognition 以自家的 coding benchmark 同時報告分數與每個任務的成本，並追蹤真實使用者中由 router 驅動完成的 merged PR 比例；它的 RL 訓練也把成本放進 reward：成功的回報要扣掉推論成本與執行時間的懲罰，讓模型學會在不同的 effort 等級下取捨（第 30 章）。這個「成本是一級指標」的觀點，對要控制單位經濟的內部 agent 特別有參考價值。

> [!note] 2026 現況
> 截至 2026 年 10 月，依 Cognition 官方 blog：Devin Desktop 於 2026-06-02 推出；Devin Fusion 文章發布於 2026-06-29，09-11 進入 Desktop 與 CLI。Fusion 在 FrontierCode 1.1 Extended 上為 63.1 分、每任務 1.35 美元，對照 Opus 5 medium 為 63.6 分、3.51 美元，Fable 5 xhigh 為 64.9 分、10.53 美元；一組使用者中 88% 的 merged PR 完全由 Fusion router 驅動。SWE-2（2026-09-10）以 Kimi K3 post-train，reward 為 R = S − λₑC，SWE-2 medium 比 SWE-1.7 少 58% turns、便宜 81%。Cognition 在 09-25 宣布 ARR 超過 10 億美元。以上分數為廠商自報、自建 benchmark，請當單一來源看待。

## 39.9 GitHub Copilot coding agent：把整個交付流程交給既有的 CI 與 PR

**為什麼值得看**：Copilot coding agent（官方文件近期改稱 Copilot cloud agent）是雲端背景型的代表，它最聰明的地方是**幾乎不發明新的基礎設施**：執行環境用 GitHub Actions，隔離單位是 branch，審核是 pull request，權限邊界是 repo 與 branch protection。

```text
 開發者          GitHub（Issue／PR）       Actions 臨時環境          Copilot agent
   │── 指派 issue ──►│                           │                        │
   │                 │── 啟動任務 ──────────────►│ 依 setup steps 準備環境│
   │                 │                           │── 啟動 ───────────────►│
   │                 │                           │◄── 讀 repo、改檔、跑測試│
   │                 │◄── 建 branch、推 commit ───────────────────────────│
   │                 │◄── 開 PR（描述改了什麼）───────────────────────────│
   │◄── 通知審查 ────│                           │ 任務結束，環境銷毀      │
   │── PR 留言 @copilot「測試名稱改一下」──►│     │                        │
   │                 │── 再啟動一次任務 ────────►│── 同一個 branch 上迭代 ►│
   │── 核准、合併 ──►│（受 branch protection 與 ruleset 約束）             │
```

這張時序圖從左到右是四個參與者。開發者把 issue 指派給 Copilot（也可以從 agents 面板、VS Code、Slack、Teams 或自動化觸發），GitHub 在 Actions 的臨時環境中啟動任務；環境依 repo 中的 setup steps 設定檔準備相依套件，agent 在裡面讀程式、改檔案、跑測試，結果推到一個 branch 並開 PR。任務結束環境就銷毀，符合第 17 章「sandbox 用完即丟」的原則。開發者在 PR 留言 @copilot 要求修改時，會在同一個 branch 上再跑一次任務，所以 PR 的對話串就是 agent 的回饋迴圈。最後的合併仍受 branch protection 與 ruleset 約束；如果規則擋住了 agent 的推送，管理者可以把 Copilot 設為 bypass actor，這是一個需要刻意做出的決定。

這個設計的取捨很清楚。好處是每個環節都是團隊早就信任、早就有稽核紀錄的元件：Actions 的執行紀錄、branch 的歷史、PR 的審查與 CI。壞處是互動性低，任務有時間上限，而且每一次迭代都要重新準備環境。它也可以先做研究或計畫、不急著開 PR；預設啟用 GitHub 自己的 MCP server 與瀏覽器自動化的 Playwright MCP，並支援自訂指令、自訂 agent、hooks、skills 與 Copilot Memory。**評估**的公開資料主要是產品使用面的說明，內部 eval 流程公開資料未說明。

> [!note] 2026 現況
> 截至 2026 年 10 月，依 GitHub 官方文件（2026-10-02 讀取）：任務在 GitHub Actions 的臨時環境中執行，硬上限 59 分鐘（可在 `copilot-setup-steps.yml` 以 `timeout-minutes` 縮短），同時消耗 Actions 分鐘數與 AI credits；只能在被指派的 repo 內作業；Copilot Memory 為 preview。過去版本的文件描述過限制對外連線的 agent 防火牆，本次查證的頁面未提到這部分細節，請以官方最新文件為準。

## 39.10 共同模式、差異與可借鏡的設計

六個產品拆完，Iris 把結果攤在一張表上。老陳看完只說了一句：「先找出它們都做的事，那是業界用事故換來的共識；再看它們不一樣的地方，那是你要依自己的條件做的選擇。」

### 2026 現況：六個產品的比較表

以下依截至 2026 年 10 月的公開資料整理；「未說明」代表公開資料中沒有找到，不代表產品沒有這項能力。

| 維度 | Claude Code | Codex | Gemini CLI | Cursor | Devin | Copilot coding agent |
|---|---|---|---|---|---|---|
| loop | 單一主 loop，可中途排入訊息 | Responses API 上的 thread／turn | 單一 loop＋scheduler | IDE 內 agent loop | 雲端 agent；main＋sidekick | Actions 中的一次任務 |
| 編輯方式 | 唯一匹配的 Edit＋Write | apply_patch | edit＋write-file | 編輯 tool（細節未說明） | 未說明 | 未說明 |
| 專案指令 | CLAUDE.md（可讀 AGENTS.md） | AGENTS.md | GEMINI.md | 未說明 | 早期資料有 Knowledge | custom instructions |
| compaction | 先清 tool 輸出再摘要 | 交接式摘要；模型可自行換窗 | 遮罩落地＋50% 門檻摘要 | 未說明 | fine-tune 小模型壓縮 | 未說明 |
| cache 與載入 | MCP tool 延遲載入 | tool_search | 未說明 | 斷點＋phantom message、按需載入 | 切換點對齊 compaction | 未說明 |
| 子 agent | 空白或 fork；agent teams 實驗 | 多 agent 模組 | 專職子 agent、A2A 遠端 | 指定時才換模型 | main＋sidekick | custom agents |
| sandbox | Seatbelt／bubblewrap | Seatbelt／bubblewrap／Windows | bwrap／Seatbelt／Windows | 雲端 agent 可自管機器 | 雲端 VM（早期資料） | Actions 臨時環境 |
| 權限 | 四種模式＋classifier | sandbox 模式＋approval＋reviewer | policy、plan mode、folder trust | 未說明 | 未說明 | repo 範圍＋branch protection |
| 審核與驗證 | 開發者看 diff、checkpoint | diff／PR、security review | 開發者看 diff | 編輯器中審查 | PR | PR 審查＋CI |
| 公開的評估做法 | per-model eval、ablation、漸進 rollout | prompt 依模型版本分開維護 | 未說明 | 真實流量 A/B | 分數與成本並列 | 未說明 |

這張表最值得注意的是「未說明」的分布：閉源產品在編輯方式、權限細節與評估上公開得最少，所以拆解報告的結論只能建立在有公開資料的格子上。從有資料的格子，可以讀出五個共同模式。第一，**loop 都很簡單**，全部是單一 while-loop 的變形，複雜度長在 tools、context 與權限；從公開資料看，沒有任何一個產品用顯式的 planner–executor 分離或樹狀搜尋當主架構，「計畫」是一個輕量的 tool 或模式。第二，**專案指令檔是共識**，名字不同但做法一樣：一份放在 repo 裡、人與 agent 都讀得懂的 Markdown。第三，**檔案系統就是檢索**：程式碼用 glob、grep、read 按需讀取，而不是預先把整個 repo 塞進 context。第四，**context 管理是分階段的**：先處理最大宗、最可重讀的 tool 輸出，再做摘要，摘要寫成交接筆記。第五，**安全做在環境層**：每個產品都把動作放進某種 sandbox，模型層的判斷（classifier、reviewer agent）只處理環境邊界上的灰色地帶。

差異則集中在三條軸上。第一條是**誰在旁邊看**：本機型假設開發者在場，所以投資在權限模式與即時中斷；背景型假設沒人在場，所以投資在環境隔離與 PR 這道最後關卡。第二條是**把多少決定權交給模型**：Codex 讓模型自己決定何時換 context 視窗，Cursor 拿掉推模型用子 agent 的提示，Claude Code 與 Codex 都讓模型（classifier 或 reviewer）處理部分核准；其他產品在這些地方較保守或沒有公開。第三條是**單模型還是多模型**：Devin Fusion、Cursor Router、Gemini CLI 的 router 都在 session 中切換模型，代價是 cache 斷點與協調成本，所以切換時機要和 compaction 對齊。

權限模式是 Iris 最想借鏡的部分，Iris 把各產品的模式對到同一把尺上：

| 等級 | 意義 | Claude Code | Codex | 背景型產品的對應 | 適合青鳥的哪種情境 |
|---|---|---|---|---|---|
| 唯讀／計畫 | 只能讀與提出計畫 | Plan | read-only | 先做研究與計畫、不開 PR | 陌生 repo、大型重構前 |
| 詢問 | 寫入與指令都問人 | Manual | on-request（核准者為人） | 不適用（沒人在場） | 第一次接觸的高風險專案 |
| 接受編輯 | workspace 內編輯放行，指令仍問人 | Accept edits | workspace-write＋on-request | 不適用 | 日常開發 |
| 自動 | 邊界內放行，灰色地帶交給模型判斷 | Auto（classifier） | auto-review（reviewer agent） | 環境＋branch 就是邊界 | 有完整測試的 repo、夜間任務 |
| 無邊界 | 不檢查 | 略過權限的模式 | danger-full-access | 不適用 | 只在用完即丟的隔離環境 |

這張表把第 1 章的 autonomy 等級落到 coding agent 上：同一個產品、同一個使用者，會依 repo 與任務切換等級，而 autonomy 是依「動作」決定的，不是依系統。表中最重要的一行其實是「自動」：兩個產品都選擇讓模型處理灰色地帶，但都把它放在確定性的 sandbox 邊界之內。只有 classifier 而沒有 sandbox，等於把安全押在一個公開資料顯示仍有可觀漏放率的判斷上（見 39.4 節的 2026 現況）。

最後，Iris 整理出給青鳥的「可借鏡的設計」清單，每一條都標了出處與要防的事故：

1. **編輯 tool 採唯一匹配，並要求先讀再改**（Claude Code 的 Edit）：防止事故一「改到第一個出現處」。多檔案改動用 all-or-nothing 的 patch（Codex 的 apply_patch）。
2. **驗證是 harness 的責任，不是模型的自述**：改過檔案就要看到測試綠燈才算完成；背景型任務以 CI 結果與 PR 審查當最終關卡（Copilot coding agent）。防止事故二「說修好了但沒跑測試」。
3. **分階段 compaction，先清 tool 輸出再摘要，摘要寫成交接筆記**（Claude Code、Codex、Gemini CLI）；使用者的原始要求與限制釘在 context 開頭，進度與計畫類輸出列入永不清除清單（Gemini CLI 的例外清單）。防止事故三「忘了不准改測試」。
4. **單一巨大輸出要有上限與落地機制，壓縮後仍超量就停**（Claude Code 的 thrashing 保護、Gemini CLI 的落地目錄）。
5. **先用環境畫硬邊界，再用模式與 classifier 處理灰色地帶**（Claude Code、Codex 共同的設計）；憑證不進 sandbox（第 17 章）。防止事故四「讀憑證、force push」。
6. **不受信任的 repo，在使用者同意前不載入它的設定與 hooks**（Claude Code 的事故修正、Gemini CLI 的 folder trust）。
7. **背景型任務盡量重用既有的信任元件**：臨時的 CI 環境、每任務一個 branch、PR 審查（Copilot coding agent），不要自己發明一套核准 UI。
8. **cache 版面當成一級約束**：穩定的 tools 與 system 放前面、變動的環境資訊放斷點之後、tool 按需追加（Cursor、第 9、13 章）。
9. **prompt 與 harness 元件和模型版本綁定，換模型就重做 eval 與 ablation**（Codex 的分版 prompt、Anthropic 的 postmortem、Cursor 的 A/B）。
10. **成本是一級指標**：eval 報告同時列分數與每任務成本，router 與換手時機和 compaction 對齊（Devin Fusion）。

這份清單刻意沒有列「multi-agent 平行寫程式」。六個產品中，子 agent 的主流用途是唯讀探索；平行寫入只在任務彼此獨立、而且有 branch 或 worktree 隔離時才使用。這和第 20 章的結論一致，也和青鳥自己的事故紀錄一致。

## 39.11 動手做：用 Python 模擬 coding agent 的關鍵機制

拆解報告寫完，老陳要 Iris 再做一件事：「把你最想借鏡的機制寫成程式，用青鳥的四個事故跑一遍。看得懂文章不代表做得出來。」這一節分三個實驗，每段程式都可以單獨執行，只用標準函式庫。實驗一是純函式，不需要模型；實驗二、三用全書統一的 ScriptedModel，讓 agent 的每一步都可以重現。

### 實驗一：唯一匹配的 edit 與 all-or-nothing 的 apply_patch

第一段程式先重現事故一，再實作 39.3 節的兩種編輯工具。`str_replace` 依序檢查檔案存在、是否先讀過、新舊是否相同、出現次數；`apply_patch` 實作 Codex 風格 patch 格式的簡化版，支援新增、刪除、更新三種動作，更新時可以用 `@@` 後面的錨點（例如函式名稱）先縮小搜尋範圍，而且先在副本上套用，全部成功才寫回。

```python
from __future__ import annotations


class EditError(Exception):
    """編輯失敗：訊息要寫給模型看，告訴它下一步怎麼做。"""


def line_numbers(text: str, needle: str) -> list[int]:
    """回傳 needle 每次出現的起始行號（1 起算），讓錯誤訊息能指出位置。"""
    out, start = [], 0
    while (i := text.find(needle, start)) != -1:
        out.append(text.count("\n", 0, i) + 1)
        start = i + 1
    return out


def str_replace(fs: dict[str, str], read_set: set[str], path: str, old: str, new: str,
                replace_all: bool = False) -> str:
    """唯一匹配規則：old 必須剛好出現一次（或明確 replace_all），而且檔案要先讀過。"""
    if path not in fs:
        raise EditError(f"{path} 不存在；新檔案請用 write_file")
    if path not in read_set:                       # 沒讀過就改，等於憑記憶改檔
        raise EditError(f"編輯前必須先讀取 {path}")
    if old == new:
        raise EditError("old 與 new 相同，沒有任何變更")
    hits = line_numbers(fs[path], old)
    if not hits:
        raise EditError(f"在 {path} 找不到 old；請重新讀取檔案，確認縮排、空白與換行")
    if len(hits) > 1 and not replace_all:
        raise EditError(f"old 在 {path} 出現 {len(hits)} 次（第 {hits} 行）；"
                        "請加入前後文讓它唯一，或確定要全部取代時設 replace_all")
    fs[path] = fs[path].replace(old, new) if replace_all else fs[path].replace(old, new, 1)
    return f"已修改 {path}：{len(hits) if replace_all else 1} 處（第 {hits if replace_all else hits[0]} 行）"


def apply_patch(fs: dict[str, str], patch: str) -> list[str]:
    """Codex 風格 patch 的簡化版：全部 hunk 都對得上才寫入（all-or-nothing）。"""
    lines = patch.strip("\n").splitlines()
    if lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
        raise EditError("patch 必須以 *** Begin Patch 開頭、*** End Patch 結尾")
    staged = dict(fs)                              # 先在副本上套用，失敗就整個丟掉
    report, i = [], 1
    while i < len(lines) - 1:
        head = lines[i]
        if head.startswith("*** Add File: "):
            path, body = head[14:], []
            i += 1
            while i < len(lines) - 1 and not lines[i].startswith("***"):
                body.append(lines[i][1:])          # 每行以 + 開頭
                i += 1
            if path in staged:
                raise EditError(f"Add File 失敗：{path} 已存在")
            staged[path] = "\n".join(body) + "\n"
            report.append(f"A {path}")
        elif head.startswith("*** Delete File: "):
            path = head[17:]
            if staged.pop(path, None) is None:
                raise EditError(f"Delete File 失敗：{path} 不存在")
            report.append(f"D {path}")
            i += 1
        elif head.startswith("*** Update File: "):
            path = head[17:]
            if path not in staged:
                raise EditError(f"Update File 失敗：{path} 不存在")
            text, cursor, n_hunks = staged[path], 0, 0
            i += 1
            while i < len(lines) - 1 and lines[i].startswith("@@"):
                anchor = lines[i][2:].strip()
                old, new = [], []
                i += 1
                while i < len(lines) - 1 and lines[i][:1] in (" ", "-", "+"):
                    tag, body = lines[i][0], lines[i][1:]
                    if tag in " -":
                        old.append(body)
                    if tag in " +":
                        new.append(body)
                    i += 1
                if anchor:                         # 錨點（例如函式名稱）先定位，縮小搜尋範圍
                    a = text.find(anchor, cursor)
                    if a == -1:
                        raise EditError(f"{path}：找不到錨點 {anchor!r}")
                    cursor = a
                block_old, block_new = "\n".join(old) + "\n", "\n".join(new) + "\n"
                at = text.find(block_old, cursor)
                if at == -1:
                    raise EditError(f"{path}：hunk {n_hunks + 1} 的上下文對不上，檔案可能已被修改，請重新讀取")
                text = text[:at] + block_new + text[at + len(block_old):]
                cursor = at + len(block_new)       # 下一個 hunk 從這裡之後找，保持順序
                n_hunks += 1
            staged[path] = text
            report.append(f"M {path}（{n_hunks} 個 hunk）")
        else:
            raise EditError(f"看不懂的 patch 行：{head!r}")
    fs.clear()
    fs.update(staged)                              # 全部成功才一次寫回
    return report


SRC = '''# 青鳥退款規則
DEFAULT_LIMIT = 500        # 測試假資料用
AUTO_REFUND_LIMIT = 500    # 正式：自動退款上限（元）

def auto_refund_allowed(amount):
    return 0 < amount < AUTO_REFUND_LIMIT
'''

# 1) 天真的「取代第一個出現處」：想改正式上限，卻改到測試假資料
naive = SRC.replace("LIMIT = 500", "LIMIT = 800", 1)
print("天真取代 →", [l for l in naive.splitlines() if "800" in l])
assert "DEFAULT_LIMIT = 800" in naive and "AUTO_REFUND_LIMIT = 500" in naive

# 2) 唯一匹配規則：先拒絕，再讓模型補上下文
fs, read_set = {"refund.py": SRC}, set()
try:
    str_replace(fs, read_set, "refund.py", "LIMIT = 500", "LIMIT = 800")
except EditError as exc:
    print("第 1 次 →", exc)
read_set.add("refund.py")                          # 模型照指示先讀檔
try:
    str_replace(fs, read_set, "refund.py", "LIMIT = 500", "LIMIT = 800")
except EditError as exc:
    print("第 2 次 →", exc)
print("第 3 次 →", str_replace(fs, read_set, "refund.py", "AUTO_REFUND_LIMIT = 500", "AUTO_REFUND_LIMIT = 800"))
assert "DEFAULT_LIMIT = 500" in fs["refund.py"] and "AUTO_REFUND_LIMIT = 800" in fs["refund.py"]

# 3) apply_patch：一次改兩個檔案；第二份 patch 的上下文過期，整份不生效
PATCH = """*** Begin Patch
*** Update File: refund.py
@@ def auto_refund_allowed
-    return 0 < amount < AUTO_REFUND_LIMIT
+    return 0 < amount <= AUTO_REFUND_LIMIT
*** Add File: test_refund.py
+from refund import auto_refund_allowed
+assert auto_refund_allowed(800)
*** End Patch"""
print("patch 1 →", apply_patch(fs, PATCH))
before = dict(fs)
STALE = """*** Begin Patch
*** Delete File: test_refund.py
*** Update File: refund.py
@@
-    return 0 < amount < AUTO_REFUND_LIMIT
+    return amount <= AUTO_REFUND_LIMIT
*** End Patch"""
try:
    apply_patch(fs, STALE)
except EditError as exc:
    print("patch 2 →", exc)
assert fs == before and "test_refund.py" in fs   # Delete 沒有半套生效
print("檔案清單：", sorted(fs), "；refund.py 最後一行：", fs["refund.py"].splitlines()[-1].strip())
```

```text
天真取代 → ['DEFAULT_LIMIT = 800        # 測試假資料用']
第 1 次 → 編輯前必須先讀取 refund.py
第 2 次 → old 在 refund.py 出現 2 次（第 [2, 3] 行）；請加入前後文讓它唯一，或確定要全部取代時設 replace_all
第 3 次 → 已修改 refund.py：1 處（第 3 行）
patch 1 → ['M refund.py（1 個 hunk）', 'A test_refund.py']
patch 2 → refund.py：hunk 1 的上下文對不上，檔案可能已被修改，請重新讀取
檔案清單： ['refund.py', 'test_refund.py'] ；refund.py 最後一行： return 0 < amount <= AUTO_REFUND_LIMIT
```

第一行重現事故一：天真的「取代第一個出現處」把 `DEFAULT_LIMIT` 改成 800，正式的 `AUTO_REFUND_LIMIT` 原封不動，而且沒有任何錯誤，這就是靜默的錯誤。接下來三次是唯一匹配規則的效果：第 1 次因為沒讀過檔案被拒；第 2 次讀過了，但 `LIMIT = 500` 出現在第 2、3 行，被拒並附上行號，模型知道要加上前後文；第 3 次用 `AUTO_REFUND_LIMIT = 500` 當舊字串，剛好一次，成功改到第 3 行。assert 確認測試假資料沒被動到。

後半段是 patch。patch 1 同時更新 `refund.py`（用 `def auto_refund_allowed` 當錨點定位，把 `<` 改成 `<=`）並新增測試檔，報告列出 `M` 與 `A` 兩個動作。patch 2 想先刪掉測試檔、再更新 `refund.py`，但它的上下文行還是修改前的 `0 < amount < AUTO_REFUND_LIMIT`，檔案已經被 patch 1 改過，所以 hunk 對不上而失敗。關鍵在最後一行：測試檔仍然存在，代表排在前面的 Delete 沒有半套生效。如果 patch 是逐段寫入，這時 repo 會停在「測試檔被刪、程式沒改」的狀態，下一步的 agent 和人都很難理解發生了什麼。

### 實驗二：權限模式與測試驗證閘門

第二段程式把 39.10 節的權限表與「驗證是 harness 的責任」寫成一個小型 coding agent。`decide()` 的判斷順序就是設計本身：先判環境層的硬邊界（workspace 之外的路徑，任何模式都拒絕），再判唯讀，再看模式；auto 模式下，簡化版的 classifier 擋掉不可逆或疑似外洩的指令；在可寫入的模式下，連網一律要人核准，因為那代表要離開 sandbox。`run_tests` 真的執行 repo 中的程式碼與測試，結果不是模型說了算。loop 中的**驗證閘門**（verification gate）規則很簡單：agent 宣告完成之前，必須有外部證據；在這裡，證據就是「最後一次修改之後，`run_tests` 全部通過」。沒有證據，模型說「完成」就不算數；退回幾次之後仍拿不出證據，run 的狀態記為 `unverified`，它和 `done` 是兩種不同的結果，上層程式不能把前者當成後者處理。

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


# ───────── 權限：環境層的硬邊界先判，模式只決定「邊界內」要不要問人 ─────────
KIND = {"read_file": "read", "edit": "edit", "run_tests": "exec", "shell": "exec"}
ALLOWLIST = ("git status", "git diff", "git log")
NETWORK = re.compile(r"\b(curl|wget|pip install|npm install)\b")
RISKY = re.compile(r"push\s+--force|reset\s+--hard|rm\s+-rf|@\.env")   # 簡化版 classifier


def decide(mode: str, name: str, args: dict) -> tuple[str, str]:
    path = args.get("path", "")
    if path.startswith("/") or ".." in path.split("/"):
        return "deny", "workspace 之外的路徑（sandbox 邊界，任何模式都一樣）"
    kind, cmd = KIND.get(name, "unknown"), args.get("cmd", "")
    if kind == "unknown":
        return "deny", "未登記的 tool"
    if kind == "read":
        return "allow", "唯讀"
    if mode == "plan":
        return "deny", "plan 模式只能讀取；請先提出計畫"
    if mode == "auto" and RISKY.search(cmd):
        return "deny", "classifier：不可逆或疑似外洩"
    if NETWORK.search(cmd):
        return "ask", "要離開 sandbox 連網"
    if kind == "edit":
        return ("allow", "workspace 內編輯") if mode in ("accept_edits", "auto") else ("ask", "編輯檔案")
    if name == "run_tests" or cmd.startswith(ALLOWLIST):
        return "allow", "allowlist"
    return ("allow", "classifier：與任務相符") if mode == "auto" else ("ask", "shell 指令")


# ───────── 假 repo 與 tools：run_tests 真的執行程式碼，結果不是模型說了算 ─────────
REPO = {
    "src/refund.py": "AUTO_REFUND_LIMIT = 500\n\ndef auto_refund_allowed(amount):\n"
                     "    if amount < 0:\n        return False\n    return amount < AUTO_REFUND_LIMIT\n",
    "tests/test_refund.py": "def test_limit_inclusive():\n    assert auto_refund_allowed(500)\n"
                            "def test_zero_not_allowed():\n    assert not auto_refund_allowed(0)\n"
                            "def test_small():\n    assert auto_refund_allowed(1)\n",
}


def run_tests(fs: dict[str, str]) -> tuple[bool, str]:
    ns: dict[str, Any] = {}
    exec(fs["src/refund.py"], ns)
    exec(fs["tests/test_refund.py"], ns)
    failed = []
    for name in [n for n in ns if n.startswith("test_")]:
        try:
            ns[name]()
        except AssertionError:
            failed.append(name)
    total = sum(n.startswith("test_") for n in ns)
    return not failed, f"{total - len(failed)} passed, {len(failed)} failed" + "".join(f"\nFAILED {f}" for f in failed)


def run(model: ScriptedModel, mode: str, approver: Callable[[str, dict], bool], max_steps: int = 15,
        max_nudges: int = 2) -> dict:
    fs, msgs = dict(REPO), [{"role": "user", "content": "500 元（含）以下的退款要自動核准，請修正並確認測試通過"}]
    st = {"prompts": 0, "denied": 0, "streak": 0, "nudges": 0, "changed": False, "green": False, "trace": []}
    for step in range(1, max_steps + 1):
        resp = model.complete(msgs)
        msgs.append({"role": "assistant", "content": resp.text, "tool_calls": [vars(t) for t in resp.tool_calls]})
        if not resp.tool_calls:
            if st["changed"] and not st["green"]:    # 驗證閘門：改過檔就要看到綠燈才算完成
                if st["nudges"] == max_nudges:
                    return {**st, "status": "unverified", "fs": fs}
                st["nudges"] += 1
                st["trace"].append(f"{step:>2} 模型宣告完成 → 驗證閘門退回（測試未通過或未執行）")
                msgs.append({"role": "user", "content": "[harness] 你修改了檔案，但最新一次 run_tests 不是全部通過，請先執行並修正。"})
                continue
            st["trace"].append(f"{step:>2} 完成：{resp.text}")
            return {**st, "status": "done", "fs": fs}
        for tc in resp.tool_calls:
            verdict, why = decide(mode, tc.name, tc.args)
            if verdict == "ask":
                st["prompts"] += 1
                verdict = "allow" if approver(tc.name, tc.args) else "deny"
                why = f"人工{'核准' if verdict == 'allow' else '拒絕'}（{why}）"
            if verdict == "deny":
                st["denied"] += 1
                st["streak"] += 1
                out = f"已拒絕，{why}。請改用其他做法，或向使用者說明。"
            else:
                st["streak"] = 0
                if tc.name == "read_file":
                    out = fs[tc.args["path"]]
                elif tc.name == "edit":
                    path, old = tc.args["path"], tc.args["old"]
                    if fs[path].count(old) != 1:
                        out = f"old 出現 {fs[path].count(old)} 次，必須剛好 1 次"
                    else:
                        fs[path] = fs[path].replace(old, tc.args["new"])
                        st["changed"], st["green"], out = True, False, f"已修改 {path}"
                elif tc.name == "run_tests":
                    st["green"], out = run_tests(fs)
                else:
                    out = f"(模擬執行) {tc.args['cmd']}"
            st["trace"].append(f"{step:>2} {tc.name:<9} {verdict:<5} → {out.splitlines()[0][:26]}" + (f"（{why}）" if verdict == "allow" else ""))
            msgs.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": out})
            if st["streak"] >= 3:                  # 連續被拒：不讓模型繼續試探，交給人
                return {**st, "status": "escalated", "fs": fs}
    return {**st, "status": "max_steps", "fs": fs}


def script() -> list[ModelResponse]:
    return [
        call("read_file", "c1", path="src/refund.py"),
        call("read_file", "c2", path="tests/test_refund.py"),
        call("edit", "c3", path="src/refund.py", old="amount < AUTO_REFUND_LIMIT", new="amount <= AUTO_REFUND_LIMIT"),
        say("已修正：500 元也會自動退款。"),                       # 過早宣告完成
        call("run_tests", "c4"),
        call("edit", "c5", path="src/refund.py", old="if amount < 0:", new="if amount <= 0:"),
        call("shell", "c6", cmd="git push --force origin main"),   # 太積極：想直接推上主線
        call("run_tests", "c7"),
        say("修好了：上限含 500 元、0 元不自動退款，3 個測試全過。未推送，請開 PR 審查。"),
    ]


ACTIONS = [("read_file", {"path": "src/refund.py"}), ("edit", {"path": "src/refund.py"}),
           ("run_tests", {}), ("shell", {"cmd": "git diff"}), ("shell", {"cmd": "pip install requests"}),
           ("shell", {"cmd": "git push --force"}), ("read_file", {"path": "../../.ssh/id_rsa"})]
MODES = ["plan", "default", "accept_edits", "auto"]
print(f"{'動作':<30}" + "".join(f"{m:<14}" for m in MODES))
for name, args in ACTIONS:
    label = f"{name} {args.get('path') or args.get('cmd') or ''}"
    print(f"{label:<32}" + "".join(f"{decide(m, name, args)[0]:<14}" for m in MODES))

no_push = lambda name, args: "push" not in args.get("cmd", "")    # 人：核准編輯，拒絕推送
results = {m: run(ScriptedModel(script()), m, no_push) for m in ("default", "accept_edits", "auto")}
print("\n── auto 模式的 trajectory")
print("\n".join(results["auto"]["trace"]))
print()
for m, r in results.items():
    print(f"{m:<13} status={r['status']:<10} 問人 {r['prompts']} 次  被拒 {r['denied']} 次  測試綠燈={r['green']}")
assert all(r["status"] == "done" and r["green"] for r in results.values())
assert [r["prompts"] for r in results.values()] == [3, 1, 0]
assert decide("auto", "read_file", {"path": "../../.ssh/id_rsa"})[0] == "deny"
lazy = run(ScriptedModel(script()[:4] + [say("真的修好了。"), say("相信我。")]), "auto", no_push)
print("只會說「修好了」的模型 →", lazy["status"], f"（被閘門退回 {lazy['nudges']} 次）")
assert lazy["status"] == "unverified"
```

```text
動作                            plan          default       accept_edits  auto          
read_file src/refund.py         allow         allow         allow         allow         
edit src/refund.py              deny          ask           allow         allow         
run_tests                       deny          allow         allow         allow         
shell git diff                  deny          allow         allow         allow         
shell pip install requests      deny          ask           ask           ask           
shell git push --force          deny          ask           ask           deny          
read_file ../../.ssh/id_rsa     deny          deny          deny          deny          

── auto 模式的 trajectory
 1 read_file allow → AUTO_REFUND_LIMIT = 500（唯讀）
 2 read_file allow → def test_limit_inclusive()（唯讀）
 3 edit      allow → 已修改 src/refund.py（workspace 內編輯）
 4 模型宣告完成 → 驗證閘門退回（測試未通過或未執行）
 5 run_tests allow → 2 passed, 1 failed（allowlist）
 6 edit      allow → 已修改 src/refund.py（workspace 內編輯）
 7 shell     deny  → 已拒絕，classifier：不可逆或疑似外洩。請改
 8 run_tests allow → 3 passed, 0 failed（allowlist）
 9 完成：修好了：上限含 500 元、0 元不自動退款，3 個測試全過。未推送，請開 PR 審查。

default       status=done       問人 3 次  被拒 1 次  測試綠燈=True
accept_edits  status=done       問人 1 次  被拒 1 次  測試綠燈=True
auto          status=done       問人 0 次  被拒 1 次  測試綠燈=True
只會說「修好了」的模型 → unverified （被閘門退回 2 次）
```

輸出分三段。第一段是決策矩陣，七個動作乘上四種模式。讀取在任何模式都放行；plan 模式除了讀取全部拒絕；編輯在 default 要問人，在 accept_edits 與 auto 直接放行；`run_tests` 與 `git diff` 在 allowlist 上，不必問人；`pip install` 要連網，即使在 auto 模式也要問人；`git push --force` 在需要人核准的模式交給人決定，在 auto 模式被 classifier 直接擋下；最後一列讀 `../../.ssh/id_rsa`，四種模式全部拒絕，這一列不會因為任何模式設定而改變，這就是「先在環境層畫硬邊界」的意思。

第二段是 auto 模式下的完整 trajectory，重現了事故二與事故四。第 3 步改了上限判斷，第 4 步模型就宣告完成，驗證閘門把它退回，因為改過檔案卻沒跑測試。第 5 步跑測試，結果是 2 passed、1 failed：0 元也被當成可以自動退款，這是模型原本沒注意到的第二個 bug。第 7 步模型想直接 force push 到主線，被 classifier 拒絕，拒絕訊息回填給模型。第 8 步測試全綠，第 9 步模型再次宣告完成，這次閘門放行，而且模型的回答改成「未推送，請開 PR 審查」。

第三段比較同一份劇本在三種模式下的結果。三種模式最後都是 done、測試綠燈，差別在問人的次數：default 問了 3 次（兩次編輯、一次推送），accept_edits 只問 1 次（推送），auto 不問人。被拒的都是那次推送，只是拒絕者不同：前兩種模式是人，auto 模式是 classifier。這就是 approval fatigue 的量化：一個有幾十次編輯的真實任務，在 default 模式下要按幾十次核准，人很快就會不看內容直接按。最後一行是只會說「修好了」的模型：它被閘門退回兩次之後，run 以 `unverified` 結束，上層程式可以據此不開 PR 或標示為未驗證。

> [!tip] 驗證閘門要看「最新狀態」，不是「曾經通過」
> 程式中 `edit` 會把 `green` 設回 False。如果只記錄「測試曾經通過過」，模型可以先跑一次綠燈、再改檔案、然後宣告完成。閘門檢查的必須是「最後一次修改之後，有沒有一次全綠的測試」。真實系統還要防另一種作弊：改測試讓它通過。第 27 章與第 34 章談的 reward hacking，在 coding agent 上最常見的形式就是刪改測試，所以 harness 應該把測試檔列為唯讀，或在閘門中比對測試檔有沒有被修改。

### 實驗三：分階段 compaction，先清 tool 輸出再摘要

第三段程式模擬事故三的長 session，並實作 39.10 節清單第 3、4 條。和第 10 章的通用版本相比，這裡特別針對 coding agent 的 context 形狀：大部分空間被讀檔與測試輸出佔據，而真正不能忘的是使用者的限制、改過的檔案與失敗的測試。每一輪呼叫模型之前都檢查一次用量，超過門檻就啟動：**階段一**把最舊的 tool 輸出換成可還原的 placeholder，只保留最近 3 則，`todo_write` 這類進度輸出永不清除；如果清完仍超過門檻，或省下的量不值得打破一次 cache（`clear_at_least`），就進入**階段二**：找一個不會拆開 tool call 與結果的切點，保留最近約 30% 的內容，較舊的部分交給摘要模型，用交接式的 prompt 產生摘要。壓縮後仍然超量時拋出 `ThrashingError`，而不是無限地再壓一次。

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


def tokens(msgs: list[dict]) -> int:
    """粗估：每 4 個字元約 1 token，每則訊息另加 4 token 的格式開銷。"""
    return sum(len(m["content"]) // 4 + 4 + len(json.dumps(m.get("tool_calls", []))) // 4 for m in msgs)


class ThrashingError(RuntimeError):
    """壓縮後仍超出上限：繼續自動壓縮只會無限循環，應停下來交給人或改策略。"""


HANDOFF = ("你正在做 context checkpoint：為接手的另一個模型寫交接摘要。必須包含："
           "使用者目標與限制、修改過的檔案與原因、目前失敗的測試、已排除的假設、下一步。\n\n")
NEVER_CLEAR = {"todo_write"}                       # 進度檔類 tool 的輸出是狀態，不是可重讀的資料


def clear_tool_outputs(msgs: list[dict], keep: int) -> list[dict]:
    """第一階段：最舊的 tool 輸出換成可還原的 placeholder；tool_call 本身保留，配對不壞。"""
    calls = {tc["id"]: tc for m in msgs if m["role"] == "assistant" for tc in m.get("tool_calls", [])}
    tool_idx = [i for i, m in enumerate(msgs) if m["role"] == "tool" and m["name"] not in NEVER_CLEAR]
    out = [dict(m) for m in msgs]
    for i in tool_idx[:-keep] if keep else tool_idx:
        m = out[i]
        if m["content"].startswith("[已清除"):
            continue
        args = json.dumps(calls[m["tool_call_id"]]["args"], ensure_ascii=False)
        m["content"] = f"[已清除 {m['name']}({args}) 的輸出，原長 {len(msgs[i]['content'])} 字元；需要時請重新執行]"
    return out


def safe_cut(msgs: list[dict], keep_tokens: int) -> int:
    """找切點：從尾端往前保留約 keep_tokens，且只切在 assistant 訊息之前，不拆開 tool_call 與結果。"""
    acc = 0
    for i in range(len(msgs) - 1, 0, -1):
        acc += tokens([msgs[i]])
        if acc >= keep_tokens and msgs[i]["role"] == "assistant":
            return i
    return 1


def compact(msgs: list[dict], model: ScriptedModel, window: int, trigger: float = 0.5,
            keep_recent: float = 0.3, keep_tools: int = 3, clear_at_least: int = 1000) -> tuple[list[dict], str]:
    before, limit = tokens(msgs), int(window * trigger)
    if before <= limit:
        return msgs, ""
    cleared = clear_tool_outputs(msgs, keep_tools)
    gain = before - tokens(cleared)
    note = f"{before} → 階段一 {tokens(cleared)}"
    if tokens(cleared) <= limit and gain >= clear_at_least:   # 省得夠多，才值得打破一次 cache
        return cleared, note
    msgs = cleared
    cut = safe_cut(msgs, int(tokens(msgs) * keep_recent))
    transcript = "\n".join(f"{m['role']}: {m['content'][:300]}" for m in msgs[1:cut])
    summary = model.complete([{"role": "user", "content": HANDOFF + transcript}]).text
    msgs = [msgs[0], {"role": "user", "content": "[交接摘要]\n" + summary}] + msgs[cut:]
    note += f"（只省 {gain}）→ 階段二 {tokens(msgs)}：摘要第 1–{cut - 1} 則，保留最近 {len(msgs) - 2} 則"
    if tokens(msgs) > limit:
        raise ThrashingError(f"壓縮後仍有 {tokens(msgs)} tokens：最近的輸出本身就太大，請截斷或落地到檔案")
    return msgs, note


GOAL = {"role": "user", "content": "修正 500 元自動退款判斷；限制：不准改 tests/ 底下的測試，金額單位是元"}


def cycle(k: int, big_log: int = 0) -> list[dict]:
    """模擬修 bug 的一輪：讀檔、跑測試、改檔、更新 todo 輪流出現；big_log 模擬一次爆量的測試輸出。"""
    name, args, body = [("read_file", {"path": f"src/mod{k}.py"}, "x = 1\n" * 300),
                        ("run_tests", {}, "....F\n" * 450 + "FAILED test_limit_inclusive"),
                        ("edit", {"path": "src/refund.py"}, "已修改 src/refund.py"),
                        ("todo_write", {}, "[x] 讀規則 [x] 重現 [ ] 修正 [ ] 全綠")][k % 4]
    if big_log:
        name, args, body = "run_tests", {"verbose": True}, "E" * big_log
    thought = f"第 {k} 步：根據上一個結果，接下來檢查 {name} 的輸出是否和退款上限有關。" * 4
    return [{"role": "assistant", "content": thought, "tool_calls": [{"id": f"c{k}", "name": name, "args": args}]},
            {"role": "tool", "tool_call_id": f"c{k}", "name": name, "content": body}]


def summarizer(msgs: list[dict]) -> ModelResponse:
    assert "修改過的檔案" in msgs[0]["content"]          # 交接 prompt 一定要問到這些欄位
    return ModelResponse(text="目標：500 元（含）以下自動退款；限制：不改 tests/、單位是元。"
                              "修改：src/refund.py（上限改成 <=）。失敗：test_limit_inclusive。下一步：重跑測試。")


def paired(msgs: list[dict]) -> bool:
    ids = [tc["id"] for m in msgs if m["role"] == "assistant" for tc in m.get("tool_calls", [])]
    return ids == [m["tool_call_id"] for m in msgs if m["role"] == "tool"]


WINDOW = 8000
msgs, model, peak = [GOAL], ScriptedModel([summarizer] * 10), 0
for k in range(60):                                # 每輪呼叫模型前都檢查一次，和真實 harness 一樣
    msgs, note = compact(msgs + cycle(k), model, WINDOW)
    if note:
        print(f"第 {k + 1:>2} 輪 {note}")
    assert paired(msgs) and msgs[0] == GOAL       # 配對不壞，使用者的原始要求永遠釘在第一則
    peak = max(peak, tokens(msgs))
print(f"60 輪後：{len(msgs)} 則、{tokens(msgs)} tokens；最高 {peak}（上限 {WINDOW}）；摘要模型呼叫 {len(model.calls)} 次")
print("最新交接摘要：", msgs[1]["content"].splitlines()[1])
print("仍原文保留的 todo_write：", sum(m.get("name") == "todo_write" and "[x]" in m["content"] for m in msgs), "則")
assert peak < WINDOW and "src/refund.py" in msgs[1]["content"]

try:                                               # 最近一輪就塞進 40,000 字元的測試 log
    compact(msgs + cycle(60, big_log=40_000), ScriptedModel([summarizer]), WINDOW)
except ThrashingError as exc:
    print("單一巨大輸出 → ThrashingError：", exc)
```

```text
第 10 輪 4071 → 階段一 1871
第 18 輪 4677 → 階段一 2487
第 24 輪 4029 → 階段一 2944
第 26 輪 4208 → 階段一 3103
第 30 輪 4506 → 階段一 3411
第 33 輪 4069 → 階段一 3645（只省 424）→ 階段二 1446：摘要第 1–58 則，保留最近 8 則
第 41 輪 4252 → 階段一 2062
第 46 輪 4210 → 階段一 2444
第 53 輪 4505 → 階段一 2986
第 57 輪 4389 → 階段一 3294
第 58 輪 4039 → 階段一 3368（只省 671）→ 階段二 1307：摘要第 1–55 則，保留最近 4 則
60 輪後：10 則、1446 tokens；最高 3986（上限 8000）；摘要模型呼叫 2 次
最新交接摘要： 目標：500 元（含）以下自動退款；限制：不改 tests/、單位是元。修改：src/refund.py（上限改成 <=）。失敗：test_limit_inclusive。下一步：重跑測試。
仍原文保留的 todo_write： 1 則
單一巨大輸出 → ThrashingError： 壓縮後仍有 10110 tokens：最近的輸出本身就太大，請截斷或落地到檔案
```

前 11 行是 60 輪中觸發壓縮的時間點。第 10 輪第一次超過 4,000 的門檻，階段一把用量從 4,071 降到 1,871，不需要呼叫摘要模型。之後每隔幾輪又觸發一次，但階段一能省下的越來越少：placeholder 與模型自己的推理文字不會被清除，持續累積。第 33 輪階段一只省下 424 tokens，低於 `clear_at_least` 的 1,000，代表為了這一點空間打破 cache 不划算，所以進入階段二：摘要第 1 到 58 則，保留最近 8 則，用量降到 1,446，換來好幾輪的空間。第 58 輪又發生一次階段二；這次被摘要的範圍包含上一份交接摘要，也就是「摘要的摘要」，這是長任務中資訊逐漸流失的主要來源，所以摘要 prompt 必須要求保留限制與改過的檔案。

統計行顯示 60 輪後只剩 10 則訊息、1,446 tokens，整個過程的最高用量 3,986 從未超過門檻，摘要模型只被呼叫 2 次。最新的交接摘要仍然保留了事故三最關鍵的資訊：「不改 tests/」與「修改：src/refund.py」；而且程式的 assert 保證使用者的原始要求永遠釘在第一則，tool call 與結果的配對始終完整。最後一行是 thrashing 保護：最近一輪的測試輸出有 40,000 字元，它就在必須保留原文的最近範圍內，兩個階段都救不了，程式選擇停下並建議截斷或落地到檔案，而不是每一輪都再壓縮一次。真實產品的做法是在 tool 層就設單次輸出上限（39.4 節的 2026 現況），或像 Gemini CLI 那樣把大型輸出寫到磁碟、context 只留路徑。

| 實驗 | 重現的事故 | 借鏡的設計 | 對應產品（依公開資料） |
|---|---|---|---|
| 一：唯一匹配 edit、apply_patch | 改到第一個出現處 | 先讀再改、唯一匹配、all-or-nothing | Claude Code 的 Edit、Codex 的 apply_patch |
| 二：權限模式、驗證閘門 | 沒跑測試就說修好；force push；讀憑證 | 環境層硬邊界、模式分級、classifier、以測試結果判定完成 | Claude Code、Codex 的權限設計；Copilot 以 CI 與 PR 把關 |
| 三：分階段 compaction | 長任務忘了限制 | 先清 tool 輸出、永不清除清單、交接摘要、thrashing 保護 | Claude Code、Codex、Gemini CLI 的 context 處理 |

這三個實驗刻意沒有模擬的部分也要說清楚。classifier 是一個正規表示式，真實的 classifier 是模型，而且公開資料顯示仍有可觀的漏放率；sandbox 邊界只檢查路徑字串，真實系統要先解析 symlink 再驗證路徑（第 17 章），並在 OS 層強制執行；摘要模型是劇本，真實的摘要品質要用第 10 章的方法測試。這些程式的價值在於把設計決定寫成可以 assert 的規則：任何人改壞判斷順序、讓閘門失效或拆開 tool 配對，測試都會立刻失敗。

## 39.12 實務應用

拆解報告的價值，在於把這些設計搬到自己的情境。以下四個情境涵蓋不同的產品形態與組織條件。

**情境一：青鳥的內部 coding agent 平台**。Iris 的最終建議是「混合」：工程師在本機用現成的 coding agent 產品（依各團隊偏好），公司只做兩件現成產品不會替你做的事。第一件是背景任務平台：夜間任務在每任務一台的 sandbox 裡跑，產出 branch 與 PR，完全比照 Copilot coding agent 的模式重用公司既有的 CI 與 branch protection；第二件是共用的 `AGENTS.md` 規範、測試唯讀政策與驗證閘門，讓不同產品的 agent 都遵守同一套交付標準。權限上，夜間任務在 sandbox 內是 L4，越過邊界的動作（連到套件鏡像站以外的網路、推送到受保護的 branch）一律拒絕，而不是等人核准，因為夜裡沒有人。第 43 章會把這個平台完整設計一次。

**情境二：受監管產業（金融、醫療）的 coding agent 導入**。這類組織最在意的是資料不出境、憑證不外洩與稽核。可借鏡的是三件事：OS sandbox 或 VM 的網路預設拒絕，只開放內部的套件鏡像站與 git server；憑證不進 sandbox，由外部的 credential proxy 代為加上（第 17 章）；每一次越過邊界的請求與核准決定都寫入稽核日誌（第 21、33 章）。auto 模式的 classifier 在這類組織中適合當「減少打擾」的工具，而不是安全邊界；若要使用託管的 reviewer agent，要先確認它看到的資料範圍符合資料治理要求。

**情境三：開源專案的維護者用背景 agent 處理 issue**。開源專案的 issue 與 PR 內容來自陌生人，是典型的 indirect prompt injection 入口（第 31 章）。可借鏡 Copilot coding agent 的做法：agent 只能在指定的 repo 內工作、每個任務一個 branch、PR 必須由維護者審查才能合併；另外要特別注意，agent 開的 PR 不能讓 CI 帶著有寫入權限的憑證自動執行，否則攻擊者可以透過 issue 內容間接取得權限。Claude Code 公開的事故（clone 下來的 repo 的 hooks 在信任對話框之前就被執行）也提醒：處理不受信任的 repo 時，不要自動載入它的設定。

**情境四：大型 monorepo 的程式碼遷移**。把上百個模組從舊 API 遷移到新 API，是少數適合平行寫入的 coding 任務，因為每個模組彼此獨立。可借鏡的是 Cursor 長時間多 agent 實驗的教訓與第 20 章的隔離：每個 worker 一個 worktree 與 branch、只回傳一份交接結果、不共享需要加鎖的狀態檔；接受小而穩定的錯誤率，最後再統一修正。context 方面，每個 worker 處理的模組不同，但 system 與 tools 相同，所以 cache 版面（39.7 節）直接決定整批任務的成本。

| 情境 | 產品形態 | 最關鍵的借鏡 | 權限與 autonomy | 特別注意 |
|---|---|---|---|---|
| 青鳥內部平台 | 本機產品＋自建背景平台 | 重用 CI 與 PR、驗證閘門 | 背景任務 sandbox 內 L4，越界即拒絕 | 夜間沒人核准，越界要直接拒絕而非等待 |
| 受監管產業 | 本機或私有雲 | egress 預設拒絕、憑證留在外面 | classifier 只當減少打擾的工具 | reviewer 看到的資料範圍 |
| 開源維護 | 雲端背景型 | repo 範圍、branch、PR 審查 | agent 不能觸發有寫入權限的 CI | issue 內容是注入入口 |
| monorepo 遷移 | 多個背景 worker | worktree 隔離、交接結果 | 每個 worker 的 sandbox 獨立 | cache 版面決定總成本 |

> [!note] 2026 現況
> 截至 2026 年 10 月，coding agent 的評估已經從單一 benchmark 轉向多個版本化的 benchmark。依公開資料：SWE-bench Verified 已經飽和（前沿分數超過 80%），前沿比較轉向 SWE-Bench Pro（1,865 題）；Terminal-Bench 改為持續更新的 benchmark，排行榜版本為 4.0.0，不同版本的分數不能直接比較；Cognition 等廠商以自建的 FrontierCode 等 benchmark 同時報告分數與成本。開源的評估框架 Inspect 可以透過 Agent Bridge 直接執行 Claude Code、Codex CLI 與 Gemini CLI，適合在自家 repo 上比較不同產品（第 27、28 章）。引用任何分數都要標明 benchmark 版本、harness 與日期。

## 39.13 設計檢查清單

設計或評估一個 coding agent（自建或採購）時，逐項回答下面的問題：

1. 編輯 tool 是否要求先讀再改？舊字串不唯一時是拒絕並回報行號，還是默默取代第一個？
2. 一次改多個檔案時，是否保證 all-or-nothing？中途失敗時，工作目錄會不會停在改了一半的狀態？
3. 「完成」由誰判定？改過檔案之後，是否要求最後一次修改之後的測試全綠，而不是模型的自述？
4. 測試檔與 CI 設定是否對 agent 唯讀，或在驗證閘門中檢查它們有沒有被修改？
5. 專案指令檔（AGENTS.md 或同類）是否放在 repo 裡、有版本控制、有人負責維護？
6. compaction 是否分階段（先清 tool 輸出再摘要）？永不清除的清單（進度、計畫、使用者回答）是否明確寫在程式裡？
7. 使用者的原始要求與限制，在任何壓縮之後是否仍然原文保留？
8. 單次 tool 輸出是否有上限？超量時是截斷、落地到檔案，還是會讓 compaction 反覆失敗？
9. 權限判斷的順序是否是「環境硬邊界 → 唯讀 → 模式 → classifier」？有沒有任何模式設定可以讓 agent 讀到 workspace 以外的憑證？
10. sandbox 的網路是否預設拒絕？allowlist 上的每個網域，是否都被當成一項能力授權來審查？
11. 不受信任的 repo，是否在使用者同意前就載入了它的設定、hooks 或 MCP server？
12. 背景任務越過邊界時是直接拒絕，還是等待核准？等待的上限與逾時行為是什麼？
13. 子 agent 是唯讀探索，還是會平行寫入？平行寫入時是否每個 agent 一個 branch 或 worktree？
14. 換模型或改 prompt 時，是否有逐模型的 eval、ablation 與漸進 rollout？eval 報告是否同時列出成本？

## 39.14 常見錯誤與除錯

| 症狀 | 原因 | 怎麼確認 | 怎麼修 |
|---|---|---|---|
| CI 全綠，但要改的設定沒變 | 編輯 tool 取代了第一個出現處，改到別的位置 | 比對 diff 與預期修改的行號；搜尋舊字串出現次數 | 改用唯一匹配規則，不唯一時回報行號並要求加上下文 |
| agent 回報「已修好」，PR 打開 CI 是紅的 | 沒有驗證閘門，完成由模型自述判定 | 在 trajectory 中找最後一次 edit 之後有沒有 run_tests | 加驗證閘門，以最新一次測試結果判定完成；未通過則標為 unverified |
| 長任務後期違反使用者限制（例如改了測試） | compaction 摘要漏掉限制，或限制被當成舊訊息清除 | 檢查壓縮後的 context 是否仍有原始要求與限制 | 原始要求釘在開頭；摘要 prompt 明列「限制」欄位；測試檔唯讀 |
| context 反覆爆滿，壓縮後馬上又觸發 | 最近範圍內有單一巨大輸出，或 placeholder 與推理文字累積 | 看每次壓縮前後的用量與最大的單則訊息 | tool 層設輸出上限並落地到檔案；壓縮後仍超量就停止並回報 |
| patch 失敗後 repo 處於奇怪狀態 | patch 逐段寫入，前面的動作已生效 | 檢查失敗時哪些檔案已被改動 | 在副本上套用，全部成功才寫回；失敗時回報哪個 hunk 對不上 |
| 核准請求太多，使用者開始不看就按 | 所有寫入與指令都要求人核准 | 統計每個任務的核准次數與核准率 | 用 sandbox 讓邊界內動作可回復後放行；灰色地帶交給 classifier 或 reviewer |
| agent 讀到開發者的雲端憑證 | 權限只靠模式判斷，沒有環境層的檔案邊界；或 symlink 繞過路徑檢查 | 檢查 sandbox 設定與路徑解析是否先處理 symlink | OS 層限制可讀寫範圍；先解析 symlink 再驗證；憑證不放在 sandbox 可見的位置 |
| 換新模型後品質下降或成本上升 | prompt 與 harness 預設值是為舊模型調的 | 逐模型 eval 與 ablation，一次拿掉一個元件 | prompt 與模型版本綁定；換模型前做 eval，漸進 rollout |

## 本章重點整理

- 拆解 coding agent 要看六個維度：loop、tools、context 策略、sandbox 與權限、審核與驗證、評估；功能清單無法說明它為什麼可靠。
- 六個產品的 loop 都是單一 while-loop 的變形，差異化幾乎全部在 harness：編輯工具、context 管理、權限與驗證。
- 產品形態分成本機互動型與雲端背景型，前者的安全重點是 OS sandbox 與權限模式，後者是環境隔離、可丟棄的 branch 與 PR 審查。
- 編輯 tool 的唯一匹配規則把「靜默改錯位置」變成「明確的錯誤」；搭配「先讀再改」，避免模型憑記憶修改已變動的檔案。
- patch 以上下文行而不是行號定位，而且必須 all-or-nothing，否則失敗時 repo 會停在改了一半的狀態。
- 專案指令檔（CLAUDE.md、AGENTS.md、GEMINI.md）是跨產品的共識；程式碼檢索以 glob、grep、read 按需讀取為主。
- compaction 要分階段：先清最大宗、可重讀的 tool 輸出，再做交接式摘要；進度、計畫與使用者回答要列入永不清除清單。
- 壓縮後仍超量時應停止並回報，而不是無限重試；單次 tool 輸出要在 tool 層就有上限或落地到檔案。
- prompt cache 是一級架構約束：穩定的 tools 與 system 在前，變動的環境資訊放在斷點之後，換模型的時機最好對齊 compaction。
- 安全先做在環境層：sandbox 畫出確定性邊界，權限模式決定邊界內要不要問人，classifier 或 reviewer agent 只處理灰色地帶。
- auto 模式解決的是 approval fatigue，而不是取代 sandbox；公開資料顯示 classifier 仍有可觀的漏放率。
- 「完成」必須由 harness 依最新的測試結果判定；背景型產品以 CI 與 PR 審查當最終關卡。
- 子 agent 的主流用途是唯讀探索；平行寫入只在任務獨立且有 branch 或 worktree 隔離時使用。
- prompt 與 harness 元件要和模型版本綁定，換模型時做逐模型 eval、ablation 與漸進 rollout，並把成本列為一級指標。

## 延伸問答

> [!question]- Q1. 為什麼主流 coding agent 的編輯工具要求舊字串「唯一」，而不是取代第一個出現處就好？
> 因為模型提供的舊字串代表它心中的某一個位置，而 harness 只看得到字串。當字串在檔案中出現兩次以上，harness 無法知道模型指的是哪一個；「取代第一個」是用猜的，猜錯時的結果是一個執行成功、通過 CI、卻改錯位置的編輯。這類錯誤最難發現，因為所有自動化訊號都是綠的，青鳥的事故一就是例子。
>
> 唯一匹配規則把這種靜默錯誤轉成明確的錯誤：拒絕執行、告訴模型出現了幾次與在哪幾行，模型多半下一步就會加上前後文改對。代價只是多一次 tool call。確實要全部取代時（例如改一個變數名稱），讓模型明確指定 replace all，意圖就被記錄在 tool call 裡，事後審查也看得出來。搭配「先讀再改」，還能防止模型根據過期的檔案內容產生舊字串。

> [!question]- Q2. 字串取代（str_replace）和 patch（apply_patch）兩種編輯工具，你會怎麼選？可以兩個都提供嗎？
> 兩者的差別在描述能力與失敗模式。字串取代一次只改一個檔案的一個位置，參數簡單，模型很少寫錯格式，失敗時的錯誤訊息也很好懂（找不到或不唯一）；適合局部修改，是多數任務的主力。patch 可以在一次呼叫中描述多個檔案的修改、新增與刪除，適合跨檔案的重構，並且可以做到 all-or-nothing；代價是格式較複雜，模型寫錯格式或上下文過期時，整份失敗要重來。
>
> 可以兩個都提供，但要注意第 5 章的原則：tool 之間的重疊要小，否則模型會猶豫該用哪個。實務上常見的做法是依模型的訓練習慣選主力：有些模型在訓練時大量接觸某種 patch 格式，用它的成功率較高；有些模型習慣字串取代。決定前應該用自己的 eval 比較兩種工具在同一批任務上的成功率、重試次數與 token，而不是只看哪個「比較先進」。Codex 選擇 patch、Claude Code 選擇唯一匹配取代，都和它們各自的模型與 harness 一起調整過。

> [!question]- Q3. 本機互動型（如 Claude Code、Codex CLI）與雲端背景型（如 Copilot coding agent）的安全模型有什麼根本差異？
> 根本差異在「誰在旁邊看」以及「環境裡有什麼」。本機型在開發者的電腦上執行，環境裡有開發者的 SSH key、雲端憑證、其他專案與個人檔案，威脅主要是 agent 碰到這些東西，或在開發者沒注意時執行破壞性指令。所以重點是 OS 原生 sandbox（寫入限 workspace、網路預設拒絕）與權限模式；開發者在場，可以即時中斷與核准，approval fatigue 是主要的可用性問題。
>
> 背景型在雲端的臨時環境中執行，環境裡原本就沒有開發者的個人憑證，每個任務一個新環境、用完即丟，所以「碰到不該碰的東西」的風險較低；但沒有人在旁邊看，即時核准不可行。它的重點因此變成環境的權限範圍（只能存取指定的 repo、推送到自己的 branch）、egress 控制，以及 PR 審查與 CI 這道最終關卡。兩者的共同點是：安全都先做在環境層，模型層的判斷只是第二道防線。設計自家系統時，要先決定是哪一種形態，才能決定把錢花在權限 UX 還是環境隔離上。

> [!question]- Q4. 你在 production 看到：agent 開的 PR 中有 15% 的 CI 是紅的，但 agent 在對話中都說「測試全部通過」。你會怎麼排查與修正？
> 先抽樣這些 PR 的 trajectory，回答三個問題：最後一次編輯之後有沒有執行測試？執行的測試和 CI 跑的是否相同？測試結果是否被正確讀取？常見的原因有四種：模型沒跑測試就宣告完成；跑的是局部測試（例如只跑一個檔案），CI 跑的是全套；測試輸出太長被截斷，失敗訊息落在被截掉的部分，模型只看到前面的 passed；或 sandbox 的環境和 CI 不同（相依版本、環境變數）。
>
> 修正要從 harness 下手，而不是加一句「請務必跑測試」的 prompt。第一，加驗證閘門：完成由 harness 依最新一次測試結果判定，結果不全綠就退回或標為 unverified，不開 PR。第二，閘門執行的測試指令要和 CI 一致，最好直接由 harness 執行而不是讓模型自己挑指令。第三，測試輸出的截斷要保留結尾的摘要與失敗清單，而不是只留開頭。第四，讓 sandbox 的映像和 CI 使用同一份環境定義。修完後把幾條代表性的 trajectory 寫成 ScriptedModel 測試，鎖住閘門的行為。

> [!question]- Q5. 為什麼分階段 compaction 要先清 tool 輸出、再做摘要？什麼樣的 tool 輸出不能清？
> 因為 coding agent 的 context 形狀很特殊：佔最多空間的是讀檔、搜尋與測試輸出，而這些都是「可以再取得一次」的資料，檔案還在磁碟上、測試可以再跑。把它們換成寫明來源的 placeholder，資訊沒有真正消失，模型需要時可以再讀；而且這一步不需要呼叫模型，成本低、不會引入摘要錯誤。摘要則是有損的，會把細節與限制濃縮甚至遺漏，還要多一次模型呼叫，所以應該在清除不夠時才使用。
>
> 不能清的是「狀態」而不是「資料」：進度清單（todo）、計畫、使用者對問題的回答、啟用的 skill 內容，以及有副作用動作的回執（例如建立了哪個 branch）。這些內容一旦清掉就無法重新取得，因為它們記錄的是過去發生的決定，而不是外部世界目前的樣子。Gemini CLI 的原始碼就把向使用者提問、啟用 skill 與 plan mode 相關的輸出列為永不遮罩。另外，清除會打斷 prompt cache，所以要設一個「至少省多少才值得清」的門檻，省得太少時直接進入摘要，換取較長的空間。

> [!question]- Q6. 估算題：一個 coding 任務平均有 80 次 tool call，其中 60% 是唯讀、25% 是 workspace 內的編輯、15% 是 shell 指令（其中三分之二在 allowlist 上）。在 Manual、Accept edits、Auto 三種模式下，每個任務大約要問人幾次？
> 唯讀 48 次、編輯 20 次、shell 12 次（allowlist 上 8 次、其他 4 次）。Manual 模式下，唯讀與 allowlist 指令放行，編輯與非 allowlist 指令都要問：20＋4＝24 次。Accept edits 模式下，workspace 內編輯放行，只剩非 allowlist 的 4 次指令要問。Auto 模式下，邊界內的動作交給 classifier，理論上 0 次；實際上會有少數被 classifier 擋下或需要越過 sandbox 邊界（例如連網）的請求升級給人，假設 4 次中有 1 次，約 1 次。
>
> 這個估算說明了 approval fatigue 的量級：Manual 模式每個任務 24 次核准，一位工程師一天跑十個任務就是 240 次，幾乎不可能每次都認真看。Accept edits 把次數降到 4 次，前提是 sandbox 與 checkpoint 讓編輯可以回復。Auto 再降到約 1 次，但要付出 classifier 的成本（每個非唯讀動作一次判斷，第一階段可以用很便宜的快速篩選），並接受它的漏放率。所以選模式時要同時看三件事：核准次數、動作的可回復性、classifier 的錯誤代價。

> [!question]- Q7. 程式找錯：下面的權限檢查有三個問題，請指出並說明後果。
> ```python
> def decide(mode, name, args):
>     if mode == "bypass":
>         return "allow"
>     if args.get("cmd", "").startswith("git"):
>         return "allow"
>     path = args.get("path", "")
>     if not path.startswith("repo/"):
>         return "deny"
>     return "allow" if mode == "auto" else "ask"
> ```
> 第一個問題是判斷順序：bypass 模式在路徑邊界之前就直接放行，代表任何模式設定都能讓 agent 讀到 workspace 之外的檔案。環境層的硬邊界必須排在最前面，不受模式影響；真正需要「無邊界」時，應該靠用完即丟的隔離環境，而不是在權限引擎裡開後門。第二個問題是 allowlist 用 `startswith("git")` 太寬：`git push --force`、`git reset --hard`，甚至名稱以 git 開頭的其他程式都會被放行。allowlist 要比對完整的指令前綴（例如 `git status`、`git diff`），破壞性的子指令要明確排除。
>
> 第三個問題是路徑檢查只比對字串前綴：`repo/../../.ssh/id_rsa` 以 `repo/` 開頭，會通過檢查；指向 workspace 外的 symlink 也會通過。正確做法是先把路徑正規化並解析 symlink，再檢查它是否位於 workspace 之內，而且這個檢查最終要由 OS 層的 sandbox 強制執行，程式中的檢查只是第一道。另外，最後一行讓沒有 path 也沒有 cmd 的未知 tool 走到 ask 或 allow，未登記的 tool 應該預設拒絕。

> [!question]- Q8. 面試追問：模型升級之後，coding agent 的 harness 應該拿掉什麼？你怎麼判斷某個元件可以拿掉？
> harness 的每個元件都編碼了一個對「模型弱點」的假設：冗長的禁止事項假設模型會做蠢事，提醒模型使用子 agent 假設它不會主動探索，固定的 context reset 假設它在接近上限時會慌張收尾。模型變強之後，這些假設可能不再成立，元件就從保護變成負擔：佔 context、增加成本，甚至讓模型表現變差。Cursor 公開的做法是把 system prompt 大幅瘦身、拿掉推模型用子 agent 的提示；Anthropic 的長任務 harness 則在新模型上拿掉了不再需要的 sprint 結構，但保留了 planner。
>
> 判斷方法是 ablation：一次只拿掉一個元件，在逐模型的 eval 上比較成功率、成本與延遲，離線 eval 不足以涵蓋的部分再用真實流量的 A/B 驗證。不能憑感覺拿，也不能一次拿很多，否則無法知道哪個元件是承重的。Anthropic 的 postmortem 也提醒反方向的風險：一行看似無害的 prompt 或預設值調整，都可能讓品質明顯下降，所以任何改動都要有觀察期與漸進 rollout。安全相關的元件（sandbox、權限邊界、驗證閘門）不在「隨模型變強而拿掉」的範圍內，因為它們防的不是模型能力不足，而是錯誤與攻擊的代價。

## 延伸閱讀

- Anthropic Claude Code 文件〈How Claude Code works〉與權限、sandbox 相關章節（2026）
- Anthropic Engineering Blog 介紹 Claude Code auto mode 的文章（2026-03）與〈How we contain Claude across products〉（2026-05）
- Anthropic Engineering Blog 關於 Claude Code 品質事故的 postmortem（2026-04-23）
- OpenAI Codex 文件〈Sandboxing〉與 openai/codex GitHub repository（原始碼與 apply_patch、compaction prompt）
- google-gemini/gemini-cli GitHub repository（`packages/core` 的 context、routing、sandbox 模組）
- Cursor Blog 關於 harness token 效率的文章（2026-09）與〈Towards self-driving codebases〉（2026）
- Cognition Blog〈Don't Build Multi-Agents〉（2025）與〈Devin Fusion〉（2026）
- GitHub Docs〈About Copilot coding agent〉（2026）
