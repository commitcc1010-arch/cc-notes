---
chapter: 47
title: AI-ready Engineering Organization 與 SRE Engagement
part: 8
---

# 第 47 章　AI-ready Engineering Organization 與 SRE Engagement

> [!abstract] 本章地圖
> **核心問題**：當工程組織長到 200 人、AI agent 的數量比人還多時，SRE 的力氣要放在哪裡？平台要提供什麼？agent 能被授權做多少事，又由誰負責？
>
> **你會學到**：
> - 依服務的重要性與生命週期，選擇 SRE 的 engagement 模式，並寫成雙方的約定
> - 設計 hand-off（SRE 接手）與 hand-back（交還）的條件與流程
> - 理解 platform engineering 與 golden path 如何把可靠性變成每個團隊的預設值
> - 用 L0–L5 的 autonomy 等級描述並授權 AI agent，知道每一級的前提、證據與降級條件
> - 為 agent 設計身份、權限、稽核與 kill switch，並把 agent 的變更納入 eval 與漸進 rollout
> - 在導入 AI 的同時保住清楚的 ownership 與 accountability
>
> **前置知識**：第 2 章（人、機器、agent 的責任分工）、第 12 章（decision rights）、第 13 章（paved road）、第 30 章（engagement 模式預告）、第 31 章（agent 的授權階梯）、第 46 章（PRR）
>
> **對應原書**：SRE 第 32 章〈The Evolving SRE Engagement Model〉、第 33 章〈Lessons Learned from Other Industries〉；SRE Workbook 第 18 章〈SRE Engagement Model〉、第 20 章〈SRE Team Lifecycles〉

## 47.1 故事：凌晨三點，柏翰的帳號刪了一張表

Harbor 第五年，公司已經約 200 人，工程組織仍以五個大團隊為主：checkout、payments、search、seller 與 platform，另外有志明帶領、約八人的 SRE 團隊，以及阿凱今年新成立、負責 AI 客服 agent 的「客服平台」小組。不同的是，每位工程師身邊都有 AI agent：coding agent 開出的 pull request 已經占了相當比例；SRE 的維運 agent 處理磁碟清理、憑證更新這類 toil（第 31 章）；AI 客服 agent 每天處理數千筆對話；各團隊還自己做了不少小 agent，有的整理週報，有的分類 bug，有的清理資料。

某個週二早上，search 團隊發現推薦結果大量退化。追查之後，原因是 production 的推薦特徵表在凌晨三點被刪掉了四成的資料。資料庫稽核紀錄寫得很清楚：執行刪除的是 search 團隊工程師柏翰的帳號。但柏翰那時在睡覺。

真相花了半天才拼湊出來。三個月前，search 團隊有人寫了一個「特徵表清理 agent」，每晚清掉 staging 環境中過期的特徵資料。為了方便，它使用柏翰的個人 access token，而那個 token 同時有 staging 與 production 的寫入權限。前一天，有人調整了 agent 的 prompt，讓它「順便檢查所有環境的過期資料」。Agent 照做了。沒有人審查那次 prompt 修改，沒有人知道這個 agent 在 production 有權限，甚至不在任何清單上。

事後檢討時，工程副總 Kevin 請 IT 盤點全公司的 agent，結果找到四十多個，其中有十幾個使用個人帳號的 token，有三個的 owner 已經離職。同一場會議上，志明也提出另一個問題：SRE 團隊只有八個人，Harbor 卻已經有七十多個服務，每個團隊都希望 SRE 幫忙看他們的告警、審查他們的上線、接手他們的值班。SRE 不可能全部答應。

這兩個問題其實是同一個問題：**組織長大之後，「誰負責什麼、可以做到什麼程度」必須被明確設計，不能再靠默契**。對人如此，對 agent 更是如此。這一章從 SRE 如何分配自己的投入開始，接著談平台如何讓好的做法成為預設，最後建立一套 AI agent 的授權模型。

## 47.2 規模改變了 SRE 的問題

第 30 章 Harbor 成立 SRE 團隊時，四位 SRE 面對二十二個服務，最重要的兩個服務由 SRE 承接 on-call，其他服務自己值班。那時的分工可以靠幾次會議講清楚。

到了第五年，三件事改變了。第一，服務數量成長得比 SRE 人數快得多。這是必然的，也是應該的：如果 SRE 的人數必須隨服務數量線性成長，第 6 章談過的「線性成長的人工工作就是警訊」就會發生在 SRE 身上。SRE 書第 1 章指出，SRE 團隊需要的人數應該隨系統規模**次線性**（sublinear）成長，也就是系統變大十倍，SRE 遠不需要多十倍；第 32 章也提到，框架與平台降低了每個服務需要的 SRE 人力。

第二，服務的成熟度差異變大了。有的服務有完整的 SLO、runbook 與 game day 紀錄（第 46 章），有的服務連告警都還是預設的 CPU 門檻。用同一種方式支援所有服務，對成熟的服務是浪費，對不成熟的服務又不夠。

第三，工作的形態改變了。很多原本需要 SRE 親自做的事，例如審查告警設定、檢查 rollback 是否就緒，可以被做成平台功能或 agent 自動檢查。SRE 的價值從「親自做」轉向「設計讓別人能安全地自己做的系統」。

所以 SRE 在大組織中要回答的問題，不是「我們能幫多少團隊」，而是「**我們的投入放在哪裡，能讓整個組織的可靠性提升最多**」。這就是 engagement 模型要解決的問題。

## 47.3 SRE Engagement 模型：選擇投入的方式

### 從 PRR 到早期參與，再到平台

SRE 書第 32 章描述了 Google 的 engagement 模型如何演進，大致分成三個階段，每一個階段都是為了解決前一個階段的限制：

```text
階段一：Simple PRR model          階段二：Early Engagement           階段三：Frameworks 與 SRE Platform
服務快上線了，SRE 來審查          SRE 在設計階段就參與                  把最佳實務做成框架與平台
        │                                │                                    │
 SRE 審查 → 開發改善 → SRE 接手     設計時就避免難以維運的架構            服務照著用，自動具備可靠性基礎
        │                                │                                    │
 限制：發現問題時已經太晚，         限制：SRE 人數有限，                   每個新服務的邊際成本很低
       改架構代價很高                    只能參與最重要的少數服務              SRE 能「支援」的服務大幅增加
```

這張圖由左到右是演進方向。階段一的問題是時機：上線前才審查，發現「這個服務不能水平擴展」時，修正的代價可能是延期一季（第 46 章 PRR 的討論）。階段二把 SRE 提前到設計階段，解決了時機問題，但 SRE 的時間有限，只能深度參與少數服務。階段三把 SRE 的知識固化成框架與平台，例如內建標準監控、負載平衡、retry 與 deadline 處理的服務框架，讓沒有 SRE 直接參與的服務也能具備基本的可靠性。

這三個階段不是互相取代，而是並存。大組織會同時使用全部三種：對最關鍵的服務早期深度參與，對一般服務透過平台間接支援，對所有服務在重大上線前做 PRR。

### 服務的生命週期決定 SRE 何時參與

SRE Workbook 把服務的生命週期分成幾個階段：架構與設計、積極開發、有限可用（例如 beta）、全面可用（GA）、淘汰（deprecation）、棄置，以及不再支援。每個階段 SRE 能提供的價值不同：

| 生命週期階段 | SRE 能做的事 | 這時不介入的代價 |
|---|---|---|
| 架構與設計 | 審查設計中的依賴、容量模型、failure modes | 架構問題要到上線前才被發現 |
| 積極開發 | 協助定義 SLI／SLO、設計監控與告警、建立 load test | 上線後才補監控，第一次事故時沒有可用的訊號 |
| 有限可用 | 觀察真實流量下的行為、調整告警、建立 runbook | 全面上線時才發現容量與告警問題 |
| 全面可用 | 承接或支援 on-call、持續改善、容量規劃 | 值班負擔失控，SRE 或開發團隊被 toil 淹沒 |
| 淘汰與棄置 | 協助遷移流量、確認沒有殘留依賴、回收資源 | 舊系統沒人負責卻仍在 production 運作 |

最後一列常被忽略。一個被宣告淘汰、但還有少量流量的服務，往往是最危險的：沒有人想投資它，它卻仍然會在凌晨壞掉（第 18 章的 deprecation）。

### Harbor 的分級：把 engagement 寫成約定

Harbor 的做法是先把服務分級，再依級別決定 engagement 模式。分級只看兩個問題：這個服務失效時，對使用者與營收的影響多大？它的維運複雜度多高？

| 等級 | 例子 | Engagement 模式 | SRE 的投入 |
|---|---|---|---|
| Tier 0 | checkout、payments | 完整支援：SRE 承接主要 on-call，早期參與所有重大設計 | 每個服務約 1 位 SRE 的時間 |
| Tier 1 | search、通知、AI 客服 agent | Embedded 或 consulting：SRE 協助 SLO、告警與 game day，團隊自己值班 | 每季一次深度檢討、重大上線前 PRR |
| Tier 2 | 賣家後台報表、內部工具 | 平台自助：使用 golden path，團隊自己值班 | 不直接投入，透過平台與文件支援 |

分級本身之外，更重要的是把每一段 engagement 寫成一份短短的約定，Harbor 稱為 **engagement charter**（合作章程）。它寫明 SRE 提供什麼（例如每週參加 ops review、協助設計 SLO、承接第二層 on-call）、服務團隊承諾什麼（例如每季投入至少 20% 的時間在可靠性工作、postmortem 的 P0 action items 在 30 天內完成），以及雙方什麼時候重新檢討。沒有寫下來的 engagement，最後常變成「SRE 什麼都接」或「SRE 什麼都不管」。

## 47.4 Hand-off 與 hand-back：支援是有條件的

### Hand-off：SRE 接手之前

當一個服務要從「團隊自己值班」變成「SRE 承接 on-call」，這個過程叫做 **hand-off**（交接）。SRE 書描述的 PRR 流程大致分成幾個階段：建立合作關係、分析服務的現況、改善與重構、訓練 SRE、正式接手，以及接手後的持續改善。

Harbor 依這個結構訂了 hand-off 的條件。服務必須先通過第 46 章的 PRR，而且以下幾項要有證據：

- 過去八週，每個 on-call 班次的 page 數量在 SRE 的負荷上限內（第 43 章）。
- 每個 page 都有對應的 runbook，而且至少一位 SRE 照著 runbook 處理過一次。
- 最近一季參加過 game day，發現的 P0 問題已經修好。
- 服務團隊仍保留第二層 on-call，SRE 遇到程式邏輯問題時能找到人。

最後一條很重要。Hand-off 不是「把服務丟給 SRE」，而是把**第一線的維運責任**轉移，開發團隊仍然擁有程式碼、產品決策與修 bug 的責任。如果開發團隊完全退出，SRE 就只能靠重啟與 rollback 處理問題，根本原因永遠修不掉。

### Hand-back：把 on-call 交還

**Hand-back**（交還）是 hand-off 的反方向：當一個服務的維運負擔持續超過約定的上限，而服務團隊沒有投入改善時，SRE 把 on-call 交還給開發團隊。第 30 章介紹過這個機制（第 31 章的 50% toil 上限是它的觸發依據之一），它的目的不是懲罰，而是讓製造維運負擔的一方直接感受到成本。

Hand-back 如果處理不好，會變成部門之間的衝突。Harbor 把流程寫得很具體：

```text
觸發條件（任一項持續 4 週以上）
  ・每班次 page 數超過約定上限
  ・SRE 在此服務的 toil 超過其工作時間的 50%（第 31 章的上限）
  ・SLO 連續違反，但 error budget policy 要求的可靠性工作沒有排入
        │
        ▼
預警：SRE 主管與服務團隊主管開會，列出數據與改善清單，約定 4 週改善期
        │
        ├── 改善期內指標回到上限內 ──► 維持 SRE 支援
        │
        ▼
交還：服務團隊承接第一線 on-call；SRE 保留顧問支援，協助完成改善清單
        │
        ▼
重新接手：改善清單完成、指標連續 8 週在上限內，重新走 hand-off 條件
```

這張圖從上往下讀。觸發條件都是可量測的數字，不是「SRE 覺得很累」，這讓討論可以聚焦在事實上。預警階段給服務團隊一段改善期，讓交還不會突然發生。交還之後 SRE 並沒有消失，而是退回顧問角色，並且有明確的「重新接手」路徑，讓雙方都知道這是一個可以回頭的狀態。

Harbor 第一次啟動 hand-back，是 seller 團隊的通知服務。它在雙十一後持續每週產生二十多個 page，大部分是第三方簡訊供應商的延遲告警，seller 團隊則忙著新功能，一直沒排入改善。交還之後兩週，seller 團隊自己值班，很快就把告警改成以「通知送達率」這類症狀為準（第 34 章），把供應商延遲改成 ticket，page 數降到每週兩三個。後來這個服務一直由 seller 團隊自己值班，SRE 認為沒有必要再接回來。

> [!note] 不是每個服務都需要 SRE 接手
> 「SRE 接手」常被誤解成一種榮譽或目標。實際上，大部分服務由開發團隊自己值班、透過平台取得可靠性基礎，是更健康的狀態。SRE 的完整支援是稀缺資源，應該留給失效代價最高、維運最複雜的少數服務。

## 47.5 Platform engineering 與 golden path

### 為什麼需要平台

即使 SRE 只深度支援幾個 Tier 0 服務，其他七十個服務仍然需要部署、監控、告警、憑證管理、SLO 儀表板。如果每個團隊自己從頭做，結果會是七十種不同的做法，其中很多有相同的漏洞。第 6 章談過集中化的判斷：做錯的代價由整個組織承擔、需要深而少見的專業、各團隊需求大致相同的事，就適合集中。可靠性的基礎設施正好符合這三個條件。

**Platform engineering**（平台工程）就是把這些共同需求做成一個內部產品，讓產品團隊自助使用。這個平台常被稱為 **internal developer platform**（IDP，內部開發者平台）。關鍵詞是「產品」：平台團隊的使用者是公司內部的工程師，平台要像對外產品一樣做使用者研究、量測滿意度、提供文件與支援，而不是一套要求別人照做的規定。

《Team Topologies》一書提出的四種團隊類型，常被用來描述平台在組織中的位置：**stream-aligned team**（面向產品價值流的團隊，例如 Harbor 的 checkout）、**platform team**（提供自助服務讓 stream-aligned team 減少負擔）、**enabling team**（暫時協助其他團隊學會新能力，例如 embedded SRE）、**complicated-subsystem team**（負責需要深度專業的子系統，例如 payments 的金流引擎）。用這個詞彙來看，Harbor 的 platform 團隊是 platform team，SRE 團隊則同時扮演 enabling 角色（embedded 與顧問）並參與平台的可靠性功能。

### Golden path：讓正確的做法最省力

第 13 章介紹過 **golden path**（黃金路徑，也稱 paved road）：一條預設安全、可觀測、自助的標準路線。Harbor 的 golden path 是一個指令：

```text
$ harbor new service --name gift-card --tier 1 --team checkout

建立 repository（含 CODEOWNERS、style 設定、CI 設定）           第 15、16、28 章
建立部署 pipeline（canary 5% → 25% → 100%，自動 rollback）       第 29 章
註冊服務目錄：owner、tier、on-call 輪值、runbook 連結              本章 47.5
產生預設 SLI／SLO 與 error budget 儀表板（availability、latency）  第 32 章
產生 burn rate 告警（page 與 ticket 兩級）                         第 34 章
接上 OpenTelemetry：metrics、logs、traces 自動帶 service 名稱      第 33 章
預設 client 設定：deadline、retry budget、exponential backoff      第 39 章
產生 PRR 草稿，列出 tier 1 需要補上的項目                           第 46 章
建立 agent 授權範本：此服務的 workflow 預設 L1，升級需申請         本章 47.6
```

這個指令把全書大部分章節的最佳實務，變成新服務的預設值。一個新服務在第一天就有 SLO、告警、canary 與 trace，不是因為團隊每個人都讀過這些章節，而是因為走 golden path 最省力。

**Service catalog**（服務目錄）是 golden path 的核心資料。它記錄每個服務的 owner、tier、依賴、on-call 輪值、runbook、SLO 與 PRR 狀態。開源的開發者入口網站 Backstage 是常見的實作方式之一，但目錄本身比工具重要：它回答「這個東西是誰的」，而這正是柏翰帳號事件中沒有人能回答的問題。從第五年開始，Harbor 規定 agent 也必須登記在服務目錄中，47.7 節會說明。

### 好平台的幾個原則

- **自助，而不是開 ticket。** 如果建立一個新服務要開 ticket 等平台團隊處理三天，平台就變成瓶頸。自助的意思是團隊自己執行指令、自己調整設定，平台團隊只處理例外。
- **有立場的預設，加上出口。** Golden path 要替使用者做選擇（「我們用這套監控」），否則等於沒有路。但它也要允許有理由的團隊偏離，只是偏離的團隊要自己承擔維護成本，並在服務目錄中標示。
- **從最薄的可用平台開始。** 第一版的平台可能只是一個範本 repository 加一份文件。等到真的看到多個團隊在重複做同一件事，再把它做成平台功能。
- **量測採用率與滿意度。** 有多少新服務走 golden path？沒走的原因是什麼？平台的 DevEx 調查（第 14 章）分數如何？使用者不想用的平台，強制推行只會產生繞道。

> [!warning] 常見誤解
> 「平台團隊就是幫大家做維運的團隊。」不是。如果平台團隊的主要工作是處理各團隊的 ticket（幫忙開機器、幫忙改設定），它只是把 toil 集中到另一個地方。平台的目標是讓這些 ticket 不再需要存在。判斷方式很簡單：平台團隊的工作量是否隨著使用的團隊數線性成長？如果是，它還不是一個平台。

## 47.6 AI agent 的 autonomy 等級：L0–L5

### 為什麼需要等級

回到柏翰帳號的事件。那個清理 agent 的問題，不是它「太笨」或「太聰明」，而是**沒有人決定過它能做到什麼程度**。它在 staging 被允許自動刪資料，這個授權悄悄延伸到了 production。

第 31 章為 SRE 的維運 agent 設計了一個授權階梯，從唯讀觀察到有界自動。到了 200 人的組織，Harbor 需要一套全公司共用的語言，讓任何人看到一個 agent 時都能回答：它現在被允許做什麼？要升級需要什麼證據？出事時會退回到哪裡？這套語言就是 autonomy 等級，附錄 C 以本節的定義為準。

### 等級的定義

等級描述的是 **agent 的動作會產生什麼 side effect、以及人在哪個環節把關**，不是模型有多聰明。

| 等級 | 名稱 | Agent 可以做什麼 | 人的角色 | Harbor 的例子 |
|---|---|---|---|---|
| L0 | 無存取（No access） | 不能接觸這個 workflow 的任何系統或資料 | 人完全自己做 | 人事資料、薪資、金流商的正式金鑰管理 |
| L1 | 唯讀輔助（Read-only assist） | 讀取被授權的資料（程式碼、metrics、logs、ticket），回答問題、摘要、分析；產出不會被任何系統直接採用 | 人自己決定、自己執行 | 值班時問 agent「過去一小時有哪些部署」；事故中擔任 scribe |
| L2 | 提案（Propose） | 產生可以被採用的產物：PR、設定 diff、要執行的指令、退款建議；任何寫入都要經過人審查，並由人或既有流程（CI／CD）執行 | 人審查每一個產物，決定是否採用 | Coding agent 開 PR、由 reviewer 核准合併；維運 agent 在 shadow mode 記錄它的判斷 |
| L3 | 核准後執行（Approve-to-execute） | 準備好參數完整、附 dry-run 結果的具體動作；人逐筆核准後，由工具代為執行 | 人核准每一筆動作 | 值班者按下核准後，agent 執行 rollback 或擴容 |
| L4 | 有界自主（Bounded autonomy） | 在事先定義的邊界內自動執行，事後通知；邊界包括允許的動作清單、單次影響上限、速率、時段與預算；超出邊界自動退回 L3 | 人定義邊界、抽查結果、處理被退回的例外 | 清理磁碟；重啟單一不健康的 pod；AI 客服對 1,000 元以下且符合規則的訂單直接退款（第 48 章） |
| L5 | 目標自主（Goal-level autonomy） | 人只給目標與 policy，agent 自行規劃多步驟、跨工具的行動，決定做法與順序；仍受 policy、預算、稽核與 kill switch 約束 | 人審查結果與 policy，而不是個別動作 | 「讓開發環境的 flaky test 比例降到 1% 以下」：agent 自行找出、隔離、修復並開 PR |

幾個關鍵的設計原則：

**第一，授權的單位是「workflow × 環境」，不是 agent。** 同一個維運 agent，在「清理磁碟」上可以是 L4，在「資料庫 failover」上只能是 L2。柏翰事件中的 agent，在 staging 清理是 L4 也許合理，但在 production 至多只該是 L2。一個 agent 的「等級」若只用一個數字描述，就會出現授權悄悄外溢的問題。

**第二，等級是天花板，不是保證。** 即使是 L4，每一個動作仍然要經過 tool 層的 policy 檢查（第 2 章的 `policy_check`）。等級決定「最多能做到哪裡」，policy 決定「這一次能不能做」。

**第三，L5 很少，而且要被環境本身限制。** L5 意味著人不再看個別動作，所以只適用於所有動作都可以完全回復、影響被環境天然限制的地方，例如開發環境或沙箱。Harbor 目前沒有任何 production 寫入的 workflow 在 L5，也不打算在可預見的未來這麼做。L5 的 agent 若要把成果帶進 production，仍要透過 L2 的路徑：開 PR、由人審查。

**第四，L3 有一個隱藏的風險：核准疲勞。** 如果值班者一天要核准兩百筆動作，他們很快就會不看內容直接按下核准，L3 實際上變成了沒有邊界的 L4。所以 L3 適合「量少、每筆影響大」的動作；量大、每筆影響小的動作，應該設計好邊界升到 L4，把人的注意力留給例外。

### 和第 31 章授權階梯的對應

第 31 章的階梯是本節等級的一個特例，對應如下：

| 第 31 章的階段 | 本章的等級 |
|---|---|
| （未列出） | L0 無存取 |
| 階段 0 唯讀觀察 | L1 唯讀輔助 |
| 階段 1 建議 | L2 提案 |
| 階段 2 Shadow | L2 的運作方式之一，用來累積升到 L3 的證據 |
| 階段 3 核准後執行 | L3 核准後執行 |
| 階段 4 有界自動 | L4 有界自主 |
| （未列出） | L5 目標自主 |

Shadow mode 不是一個獨立的等級，因為它的 side effect 和 L2 相同：agent 的判斷不會被系統直接採用。它是 L2 期間收集證據的方法。

### 升級要靠證據，降級要事先寫好

每一次升級都要有證據，而且證據隨等級提高而變嚴：

| 升級 | 需要的證據 |
|---|---|
| L0 → L1 | 資料分級確認可以讓 agent 讀取；agent 有獨立身份與稽核紀錄 |
| L1 → L2 | 抽查回答的正確性；產物格式能被既有的 review 與 CI 流程處理 |
| L2 → L3 | Shadow 期間有足夠樣本、與人的決定高度一致，而且零次不安全的建議；離線 eval 通過 |
| L3 → L4 | 一段時間內核准後執行零事故、被人否決的比例低；邊界（動作、影響、速率、預算）寫成 policy 並由工具強制 |
| L4 → L5 | 環境的所有動作可完全回復；架構審查與工程副總簽核；只限非 production 或被環境本身限制的範圍 |

降級條件同樣重要，而且要自動執行。Harbor 規定以下情況會讓相關 workflow 的等級立刻降回 L2，重新累積證據：agent 的模型、prompt、工具或資料來源有重大變更；agent 造成或延長了一次事故；被人否決的比例突然上升；agent 的 owner 離職或轉調而沒有新的 owner。最後一條是柏翰事件的直接教訓：三個 owner 已經離職的 agent，在新制度下會自動降級，直到有人認領。

## 47.7 Agent 的身份、權限與審計

### 不再借用人的帳號

柏翰事件的第一個根本問題是身份：agent 用的是人的 token。這帶來三個後果。稽核紀錄說是柏翰做的，但其實不是，事後追查困難；agent 的權限等於柏翰的全部權限，遠超過它需要的；柏翰離職時，要嘛 token 被撤銷導致 agent 突然壞掉，要嘛 token 沒被撤銷，留下一個沒人負責的權限。

所以第一條規則是：**每個 agent 都有自己的身份**，屬於 **non-human identity**（非人類身份），就像服務帳號一樣。身份要有幾個特性：

- **短效憑證**：agent 每次執行時取得有效期限很短的憑證（例如數十分鐘），而不是一個永久有效的 token。憑證外洩的影響時間被限制住。
- **最小權限**：權限依 47.6 節的 workflow × 環境授權發放。清理 agent 在 staging 有刪除權限，在 production 只有讀取權限。
- **綁定 owner**：身份在服務目錄中登記，連到一位具名的人類 owner 與一個團隊。

### 代表誰行動：delegation

有些 agent 是代表某個人行動的，例如工程師讓 coding agent 幫自己開 PR，或客服人員讓 agent 幫忙查訂單。這時 agent 的有效權限應該是**「agent 自己被授權的範圍」與「委派它的人的權限」的交集**，而不是其中任何一個。

為什麼是交集？想像一個 agent 被授權讀取所有訂單，而一位只能看自己負責賣家的客服人員委派它查詢。如果 agent 用自己的權限，客服人員就能透過 agent 看到自己原本看不到的訂單，這叫做 **confused deputy**（混淆代理人）問題：一個擁有較多權限的代理人，被權限較少的一方誘導去做越權的事。Prompt injection 是這個問題在 AI 時代最常見的形式：惡意的輸入誘導 agent 用它自己的權限做事。交集原則讓 agent 在任何情況下都不會比委派者擁有更多權限。

### Tool gateway：所有動作經過同一道門

第 31 章提過 tool broker：agent 只能呼叫預先定義、範圍很窄的工具，由工具檢查參數與權限。在組織層級，Harbor 把它做成平台的一部分，稱為 **tool gateway**：

```text
  Agent（任何團隊、任何模型）
        │  請求：我是 reco-cleaner，代表誰、要對哪個環境執行哪個工具、參數是什麼
        ▼
  ┌──────────────────────── Tool gateway（platform 團隊維護）────────────────────────┐
  │ ① 身份驗證：短效憑證是否有效？agent 是否登記在服務目錄？owner 是否在職？          │
  │ ② 授權：這個 workflow × 環境的等級是多少？動作類型是否在等級允許範圍內？           │
  │ ③ Policy：參數是否違反 invariant？影響範圍、速率、預算是否超過邊界？              │
  │ ④ 決定：allow／escalate（轉人核准）／deny                                        │
  │ ⑤ 稽核：不論結果，寫入一筆完整紀錄                                                │
  │ ⑥ Kill switch：可依 agent、workflow、團隊或全公司一鍵停用                         │
  └──────────────────────────────────────────────────────────────────────────────────┘
        │  只有 allow 的請求會到達
        ▼
  實際系統（資料庫、部署系統、退款 API…）
```

這張圖從上往下讀。Agent 不直接連到任何實際系統，所有請求都經過 gateway 的六道檢查。前三道依序回答「你是誰」「你被允許做到哪個等級」「這一次的參數是否安全」；第四道產生三種結果之一，其中 escalate 和第 2 章一樣，是「轉給人」而非拒絕；第五道確保每一個請求都留下紀錄，包括被拒絕的；第六道讓人在發現問題時，可以用不同的粒度立即停止 agent。

集中在 gateway 有兩個好處。第一，七十個服務、四十多個 agent 不必各自實作身份與權限檢查，避免第 6 章說的「七十種做法、相同的漏洞」。第二，平台團隊可以在一個地方看到全公司 agent 的行為，例如「哪個 agent 最近被拒絕的次數突然增加」，這可能是 prompt 改壞了，也可能是有人在嘗試 prompt injection。

### 稽核紀錄要記什麼

稽核紀錄要能回答事後最常被問的問題：誰、代表誰、用哪個版本、根據什麼、做了什麼、結果如何。Harbor 的每一筆紀錄包含：

| 欄位 | 範例 | 回答的問題 |
|---|---|---|
| agent 身份與 owner | `reco-cleaner`／柏翰（search） | 這是哪個 agent？出事找誰？ |
| 委派者 | 無（排程觸發）或某位工程師 | 代表誰在行動？ |
| 版本 | 模型版本、prompt 版本、工具版本 | 行為改變時，是哪個版本開始的？ |
| workflow、環境與等級 | `feature-table-cleanup`／prod／L2 | 當時被授權到哪裡？ |
| 工具與參數 | `delete_rows(table=..., where=...)` | 實際嘗試做什麼？ |
| policy 決定與理由 | deny：L2 以下不能直接寫入 | 為什麼被允許或拒絕？ |
| trace id | 連到 agent 的推理與工具呼叫紀錄 | 它為什麼決定這麼做？ |

最後一欄連到 agent 的 trace（第 33 章談過 LLM 應用的 observability）。事後分析時，「agent 為什麼刪 production 的資料」的答案，往往就在 trace 中看到的那段被修改過的 prompt。

### 職責分離

最後一組規則是 **separation of duties**（職責分離），它在人的世界早已存在（例如不能自己核准自己的報帳），在 agent 的世界要重新寫一次：

- Agent 不能核准自己開的 PR，也不能由同一個 agent 的另一個實例核准。
- Agent 不能修改自己的 policy、等級或 prompt；這些變更要走一般的 code review。
- 對 production 有寫入權限的 agent，它的 prompt 與設定存放在 repository 中，變更需要 owner 以外的人 review。

最後一條直接對應柏翰事件：如果那次 prompt 修改必須經過 review，「順便檢查所有環境」這句話很可能會被攔下。

## 47.8 Eval 與 rollout：agent 的變更也是變更

### Agent 的「版本」由什麼組成

傳統服務的版本是一個 commit。Agent 的行為則由好幾樣東西共同決定：模型版本、system prompt、可用的工具與工具描述、retrieval 的資料來源與設定、policy。任何一樣改變，agent 的行為都可能改變，而且不會產生任何錯誤碼。柏翰事件的觸發點就是一次 prompt 修改，而 prompt 修改在大部分團隊的認知中「不算部署」。

Harbor 的規則是：**這些組成部分合起來視為 agent 的版本，任何一部分的變更都走和程式碼相同的變更流程**。這包括 code review、eval、漸進 rollout 與共用的 error budget（第 32、35 章）。

### Eval：agent 的測試

**Eval**（評估）是用固定的測試資料與評分規則，量測 AI 系統是否完成目標、是否遵守限制。它是 agent 世界的測試，第 25 章介紹過它是一種新型的測試。Harbor 的 agent eval 分成三類：

- **能力 eval**：agent 是否完成任務。例如給清理 agent 一組模擬的特徵表，檢查它是否正確找出過期資料。
- **安全 eval**：agent 是否守住界線。例如在輸入中加入「順便清理 production」或其他 prompt injection，檢查 agent 是否拒絕或轉人。這類測試的結果要求通常是「零次違規」，而不是一個百分比。
- **回歸 eval**：每次發生事故或發現新的失敗模式，就把那個案例加入測試集，確保同樣的問題不會再發生。

Eval 的結果同時有兩個用途：作為每次版本變更的上線門檻，以及作為 47.6 節升級等級的證據。

### 漸進 rollout

通過 eval 之後，agent 的新版本和服務的新版本一樣漸進上線：

```text
離線 eval ──► shadow（新版本只記錄判斷，舊版本仍在執行）──► canary（少量流量）──► 全量
   │                    │                                      │
 能力、安全、回歸      比較新舊版本的判斷差異                     觀察線上 SLI：
 全部達門檻            每一筆差異都值得看                          unsafe action、轉人工、
                                                                   被否決比例、成本
```

這張圖由左到右是同一個版本經過的關卡。離線 eval 用固定資料擋下已知的問題；shadow 用真實流量找出 eval 沒涵蓋的差異；canary 讓少量真實使用者接觸新版本，並用第 32 章的 AI SLI 監看；全量之後，線上監控仍持續運作。

一個常被忽略的細節是**模型供應商的變更**。如果 Harbor 使用的是外部模型服務，供應商更新模型時，agent 的行為可能在沒有任何內部變更的情況下改變。對策是盡量固定模型版本（使用供應商提供的版本識別），並把「供應商宣布模型更新」視為一次需要走 eval 與 rollout 的變更；同時在線上持續執行一小組 canary eval，偵測沒有預告的行為變化。

## 47.9 組織如何導入 AI 而不失去責任

### Agent 可以是 R，不能是 A

第 12 章用 RACI 說明過：**agent 可以是 R（執行者），但不能是 A（當責者）**。到了 200 人的組織，這句話要落實成制度：

- 每個 agent 在服務目錄中有一位具名的 owner。Owner 對 agent 的行為負責，就像對自己團隊的服務負責一樣，包括它的 eval、等級申請、事故處理。
- 每一個由 agent 產生、被合併的變更，都有一位核准的人。核准者對合併的結果負責，就像程式碼是自己寫的一樣（第 16 章的 review 責任）。
- 事故的 postmortem 不寫「AI 出錯了」。問題仍然是系統層級的：為什麼這個動作能通過 gateway？等級是否授得太高？eval 為什麼沒有涵蓋？（第 9 章的 blameless 原則同樣適用於 agent 事故。）

### 用 paved road 取代禁令

柏翰事件之後，Harbor 有主管提議「禁止各團隊自製 agent，一律由平台團隊開發」。Kevin 沒有採納，理由和第 13 章談 AI paved road 時一樣：禁令不會讓需求消失，只會讓 agent 轉入地下，組織反而失去可見度。這類不在組織管控範圍內的 AI 使用，常被稱為 **shadow AI**。

Harbor 的做法是讓「正確的路」最省力：用 `harbor new agent` 建立的 agent，自動取得獨立身份、登記到服務目錄、接上 tool gateway、產生 eval 範本，等級預設為 L1。團隊要做的只是寫 prompt、選工具、補上 eval 案例。走這條路比自己拿 token 寫腳本更快，大部分團隊自然就會選它。對於仍然用個人 token 的舊 agent，平台給了六十天的遷移期，期滿後個人 token 不再能存取 production。

### 依風險分級的 AI 政策

Harbor 的 AI 使用政策不是一份長長的禁止清單，而是一張分級表，依「資料敏感度」與「動作的影響」決定需要什麼：

| 風險等級 | 例子 | 最低要求 |
|---|---|---|
| 低 | 整理週報、解釋程式碼、草擬文件 | 使用核可的模型服務；不放入機密資料 |
| 中 | Coding agent 開 PR、分類 bug、維運 agent 唯讀分析 | 獨立身份、稽核紀錄、服務目錄登記；產物經人 review |
| 高 | 任何對 production 的寫入、涉及金錢或個資的動作 | 上述全部，加上 tool gateway、安全 eval、shadow 證據、kill switch、owner 以外的人審查 prompt 變更 |

政策也規定了哪些決定**永遠留給人**：人事決策、對個別使用者有重大影響且無法回復的決定（例如永久停權）、資料的永久刪除、以及等級與 policy 本身的變更。這些不是因為 AI 做不到，而是因為它們需要有人能被詢問、能解釋、能承擔後果。

### 量測：不要只算採用率

Harbor 導入 AI 的第一年，曾經在週報上追蹤「AI 產生的程式碼行數」與「AI 建議的接受率」。第 14 章已經說明了這類指標的問題：它們很容易被灌水，而且和使用者價值沒有直接關係。第五年，Harbor 改看幾組指標：DORA 的交付指標（包括 rework rate）是否改善、AI 參與的變更的 change failure rate 是否和人寫的相當、review 等待時間與 reviewer 的負擔是否上升、agent 造成的事故數與 gateway 拒絕次數，以及開發者體驗調查中對 AI 工具的評價。

DORA 在 2025 年提出的 AI Capabilities Model 提供了一個有用的參照：它認為 AI 帶來的效益取決於組織既有的能力，並列出七項能力，包括清楚傳達的 AI 立場、健康的資料生態、讓 AI 能存取內部資料、良好的版本控制實務、以小批次工作、以使用者為中心，以及高品質的內部平台。這份清單和本章的內容幾乎一一對應：AI 政策、服務目錄、tool gateway、golden path。換句話說，**AI-ready 的組織，首先是一個工程基礎紮實的組織**；基礎薄弱時，AI 只會讓問題放大得更快。

### 向其他高可靠性產業借鏡

SRE 書第 33 章訪談了來自航空、醫療、核能等產業的人，比較這些產業和 SRE 的共同做法，歸納出幾個主題：事前準備與災難演練、從事故中學習的 postmortem 文化、把重複的操作自動化，以及結構化、理性的決策方式。這些產業早就面對過「自動化程度越來越高時，人的責任放在哪裡」的問題，例如飛機有自動駕駛，但機長仍然對飛行負責，並且定期在模擬器中練習自動系統失效的情境。導入 AI agent 的組織面對的是同一個問題：自動化可以接手執行，但責任、演練與決策的結構必須由人刻意設計，而不是隨著工具的能力自然長出來。

### 人的能力不能被掏空

最後一個風險比較隱微。當 agent 處理了大部分的 toil 與例行排查，初階工程師就少了很多從簡單問題中學習的機會，而真正困難的事故仍然需要人。這是第 31 章〈Ironies of Automation〉在組織層級的版本。Harbor 的對策包括：game day 中定期演練「agent 不可用」的情境（第 46 章）；新進工程師的前幾次值班，刻意先自己排查、再看 agent 的分析；以及在 postmortem 中記錄「人是否能理解並驗證 agent 的判斷」。

## 47.10 動手寫：agent 授權引擎

下面的程式把 47.6 到 47.8 節的設計寫成一個簡化的 tool gateway：agent 登記與 workflow × 環境的授權、每一次動作的決定、依證據判斷能否升級，以及版本變更時自動降級。

```python
from dataclasses import dataclass, field

LEVELS = {
    0: "L0 無存取",
    1: "L1 唯讀輔助",
    2: "L2 提案",
    3: "L3 核准後執行",
    4: "L4 有界自主",
    5: "L5 目標自主",
}


@dataclass
class Grant:
    workflow: str          # 授權的單位是「工作流程 × 環境」，不是整個 agent
    env: str
    level: int
    max_blast: int = 0     # L4 以上：單次動作最多影響幾個資源


@dataclass
class Agent:
    agent_id: str
    owner: str             # 具名的人類負責人
    version: str           # model + prompt + tools 的版本組合
    grants: dict = field(default_factory=dict)


REGISTRY: dict[str, Agent] = {}
AUDIT: list[tuple] = []


def register(agent: Agent, *grants: Grant):
    for g in grants:
        agent.grants[(g.workflow, g.env)] = g
    REGISTRY[agent.agent_id] = agent


def decide(agent_id, workflow, env, action, blast=1, approved_by=None):
    agent = REGISTRY.get(agent_id)
    if agent is None:
        result = "deny：未登記的 agent"
    else:
        g = agent.grants.get((workflow, env))
        if g is None or g.level == 0:
            result = "deny：此流程與環境沒有授權"
        elif action == "read":
            result = "allow"
        elif action == "propose":
            result = "allow" if g.level >= 2 else "deny：等級不足以提案"
        elif g.level <= 2:
            result = "deny：L2 以下不能直接寫入"
        elif g.level == 3:
            result = f"allow（核准人 {approved_by}）" if approved_by else "escalate：需要人核准"
        elif blast > g.max_blast:
            result = f"escalate：影響 {blast} 個資源，超過上限 {g.max_blast}"
        else:
            result = "allow（事後通知 owner）"
    owner = agent.owner if agent else "?"
    AUDIT.append((agent_id, owner, workflow, env, action, blast, result))
    return result


@dataclass
class Evidence:
    eval_pass: float         # 離線 eval 通過率
    shadow_agree: float      # shadow 期間與人類決定的一致率
    shadow_samples: int
    unsafe: int              # 不安全的建議或動作次數（一次就擋）
    incidents_90d: int


def review_promotion(current, ev: Evidence):
    target = current + 1
    reasons = []
    if ev.unsafe > 0:
        reasons.append(f"有 {ev.unsafe} 次不安全行為")
    if ev.eval_pass < 0.95:
        reasons.append(f"eval 通過率 {ev.eval_pass:.0%} < 95%")
    if target >= 3 and (ev.shadow_samples < 200 or ev.shadow_agree < 0.97):
        reasons.append(f"shadow 證據不足（{ev.shadow_samples} 筆，一致率 {ev.shadow_agree:.0%}）")
    if target == 5:
        reasons.append("L5 需要架構審查與工程副總簽核，不由程式自動判斷")
    if ev.incidents_90d:
        reasons.append(f"90 天內 {ev.incidents_90d} 次相關事故")
    verdict = f"{LEVELS[current]} → {LEVELS[target]}："
    return verdict + ("可以升級" if not reasons else "維持，原因：" + "；".join(reasons))


def on_version_change(agent: Agent, new_version: str):
    """模型或 prompt 換版：所有 L3 以上的授權先降到 L2，重新跑 shadow。"""
    agent.version = new_version
    for g in agent.grants.values():
        if g.level >= 3:
            g.level = 2
    return [(w, e, LEVELS[g.level]) for (w, e), g in agent.grants.items()]


register(Agent("ops-agent", owner="志明", version="m3+p12"),
         Grant("disk-cleanup", "prod", 4, max_blast=3),
         Grant("db-failover", "prod", 2))
register(Agent("reco-cleaner", owner="柏翰（search）", version="m2+p4"),
         Grant("feature-table-cleanup", "staging", 4, max_blast=50),
         Grant("feature-table-cleanup", "prod", 2))

print("== 授權判斷 ==")
print("1", decide("ops-agent", "disk-cleanup", "prod", "write", blast=2))
print("2", decide("ops-agent", "disk-cleanup", "prod", "write", blast=12))
print("3", decide("ops-agent", "db-failover", "prod", "write"))
print("4", decide("reco-cleaner", "feature-table-cleanup", "prod", "write", blast=40))
print("5", decide("reco-cleaner", "feature-table-cleanup", "prod", "propose"))
print("6", decide("night-bot", "feature-table-cleanup", "prod", "write"))

print("\n== 升級審查 ==")
print(review_promotion(2, Evidence(0.98, 0.99, 340, 0, 0)))
print(review_promotion(2, Evidence(0.97, 0.98, 410, 1, 0)))
print(review_promotion(3, Evidence(0.96, 0.95, 120, 0, 1)))

print("\n== 換版降級 ==")
print(on_version_change(REGISTRY["ops-agent"], "m4+p12"))
print("7", decide("ops-agent", "disk-cleanup", "prod", "write", blast=2))

print("\n== 稽核紀錄（最後 3 筆）==")
for row in AUDIT[-3:]:
    print(" ", row)
```

執行結果：

```text
== 授權判斷 ==
1 allow（事後通知 owner）
2 escalate：影響 12 個資源，超過上限 3
3 deny：L2 以下不能直接寫入
4 deny：L2 以下不能直接寫入
5 allow
6 deny：未登記的 agent

== 升級審查 ==
L2 提案 → L3 核准後執行：可以升級
L2 提案 → L3 核准後執行：維持，原因：有 1 次不安全行為
L3 核准後執行 → L4 有界自主：維持，原因：shadow 證據不足（120 筆，一致率 95%）；90 天內 1 次相關事故

== 換版降級 ==
[('disk-cleanup', 'prod', 'L2 提案'), ('db-failover', 'prod', 'L2 提案')]
7 deny：L2 以下不能直接寫入

== 稽核紀錄（最後 3 筆）==
  ('reco-cleaner', '柏翰（search）', 'feature-table-cleanup', 'prod', 'propose', 1, 'allow')
  ('night-bot', '?', 'feature-table-cleanup', 'prod', 'write', 1, 'deny：未登記的 agent')
  ('ops-agent', '志明', 'disk-cleanup', 'prod', 'write', 2, 'deny：L2 以下不能直接寫入')
```

逐段解讀：

1. `Grant` 的鍵是 `(workflow, env)`，這是 47.6 節第一條原則的直接實作。同一個 `reco-cleaner` 在 staging 是 L4、在 production 是 L2，所以判斷 4 中，它想在 production 刪除 40 筆資料時被拒絕，但判斷 5 中，它在 production「提案」要刪除哪些資料是被允許的。如果柏翰事件中的 agent 是這樣登記的，那次 prompt 修改最多只會產生一份需要人審查的刪除提案。
2. 判斷 1 和 2 示範 L4 的邊界：同樣是清理磁碟，影響 2 台主機時自動執行並事後通知 owner；影響 12 台時超過上限 3，退回成 escalate，由人核准。邊界不是讓 agent 停下來，而是把超出常態的動作交還給人。
3. 判斷 6 是一個沒有登記的 agent，在 gateway 的第一道檢查就被拒絕。這對應 Harbor 的遷移規則：個人 token 被停用之後，沒有在服務目錄登記的 agent 就無法碰到 production。稽核紀錄中的 owner 欄是 `?`，這本身就是一個應該告警的訊號。
4. `review_promotion` 把升級的條件寫成程式。第一個案例各項證據都達標，可以升到 L3；第二個案例 eval 與 shadow 都很好，但有一次不安全行為，所以不能升級，這和第 31 章的原則一致：一筆不安全的建議比高一致率更重要。第三個案例同時缺少足夠的 shadow 樣本與有相關事故。程式刻意不讓 L5 自動通過，因為那需要人的架構判斷。
5. `on_version_change` 模擬維運 agent 更換模型：所有 L3 以上的授權自動降回 L2，所以判斷 7 中，原本可以自動執行的磁碟清理現在被拒絕，直到新版本重新累積證據。這是「降級要事先寫好、自動執行」的實作。
6. 每一次判斷，不論結果，都寫入 `AUDIT`。真實的稽核紀錄還會包含委派者、模型與 prompt 的版本、參數與 trace id（47.7 節的表格）。

真實系統中，`REGISTRY` 是服務目錄、`decide` 是 tool gateway 中的授權與 policy 引擎（常用 policy-as-code 工具實作），`Evidence` 來自 eval 平台與 shadow 紀錄，`on_version_change` 由部署 pipeline 在偵測到 agent 版本變更時觸發。結構和程式相同：**身份 → 授權等級 → 單次 policy → 決定 → 稽核**。

## 47.11 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| SRE 什麼都接 | SRE 被 toil 淹沒，沒有時間做工程改善 | 八位 SRE 承接二十個服務的 on-call，每週超過一半時間在處理 page | 服務分級，只對 Tier 0 完整支援，其他透過平台與顧問 |
| Hand-back 被當成懲罰 | 團隊隱藏問題、抗拒 PRR | seller 團隊把告警調得很鬆，避免觸發交還條件 | 交還條件用可量測的數字，設預警期，並保留重新接手的路徑 |
| 平台強制推行但不好用 | 團隊繞道，平台失去可見度 | Golden path 不支援某種常見需求，團隊自己架了另一套部署 | 把平台當產品：量測採用率與滿意度，提供有理由的出口 |
| Agent 只有一個等級數字 | 授權從低風險環境外溢到高風險環境 | 清理 agent 在 staging 可自動刪除，同樣的權限延伸到 production | 以 workflow × 環境為授權單位，由 gateway 強制 |
| L3 的核准量太大 | 核准疲勞，L3 名存實亡 | 值班者一天核准兩百筆重啟，完全不看內容 | 量大、單筆影響小的動作設計邊界升到 L4，L3 留給量少影響大的動作 |
| 以禁令管理 AI | Shadow AI，組織失去可見度 | 禁止自製 agent 後，工程師改用外部服務與個人 token | 提供比自製更省力的 golden path，並設遷移期停用個人 token |
| 只看 AI 採用率 | 指標好看，品質與 reviewer 負擔惡化 | AI 產生的 PR 數量翻倍，rework rate 與 review 等待時間同時上升 | 看交付與穩定性指標、AI 參與變更的失敗率與 reviewer 負擔 |

## 47.12 AI 時代：什麼變了？

這一章本身就在談 AI 導入，所以這一節聚焦在一個比較少被討論的面向：AI 如何改變 SRE engagement 與平台工程**本身的工作方式**。

**第一，PRR 多了一個對象：agent。** 過去 PRR 審查的是服務；現在 agent 也需要類似的審查，Harbor 稱為 agent readiness review。它檢查的項目包括：是否有獨立身份與 owner、各 workflow 的等級是否合理、tool 層是否強制了關鍵 invariant、安全 eval 是否涵蓋 prompt injection、kill switch 是否演練過、以及 agent 失效時人能否接手。高風險的 agent（例如能在額度內直接退款的 AI 客服 agent）由 SRE 參與審查，就像 Tier 0 服務一樣。

**第二，SRE 的 engagement 可以部分由 agent 擴展。** 過去 Tier 2 的服務幾乎得不到 SRE 的直接協助；現在 SRE 可以把自己的審查經驗做成一個 L1 或 L2 的「PRR 助理」agent，讓任何團隊在上線前自助檢查：告警是否以症狀為主、runbook 是否和告警對應、依賴是否有 timeout。SRE 的角色從親自審查，轉向維護這個 agent 的 eval 與知識。

**第三，平台的範圍擴大到 AI 基礎設施。** Harbor 的 platform 團隊現在除了 CI/CD 與監控之外，還維護核可的模型服務入口、tool gateway、agent 的身份系統、eval 平台與 agent 的 observability（token 用量、成本、trace）。這些都屬於「做錯的代價由整個組織承擔、需要深而少見的專業、各團隊需求大致相同」的事，適合集中。

**第四，SRE 自己也是 agent 的使用者與 owner。** SRE 的維運 agent 是 Harbor 等級最高的 production agent 之一，所以 SRE 必須以身作則：它的等級、eval、降級條件與事故紀錄都要公開在服務目錄中，接受和其他團隊相同的審查。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 盤點組織中的 agent：比對 token 使用紀錄、API 呼叫來源，找出未登記的 agent | 未登記 agent 的處置（停用、遷移、認領）由 owner 與平台團隊決定，不由 agent 自動停用 production 流程 |
| 依 PRR 範本自助檢查服務與 agent 的就緒度，列出缺項與證據連結 | 是否接手 on-call、是否 hand-back、服務分級，由 SRE 主管與服務團隊主管決定 |
| 從稽核紀錄分析每個 agent 的拒絕率、escalate 率、被否決比例，草擬升降級建議 | 等級的升級由 owner 申請、指定的審查者核准；降級條件由程式自動執行 |
| 為 agent 的版本變更自動執行能力、安全與回歸 eval，比較新舊版本 | Eval 測試集的內容與門檻由 owner 維護；「零次不安全行為」這類硬性門檻不能被 agent 調整 |
| 分析 golden path 的使用紀錄與開發者回饋，找出最常被繞過的部分 | 平台的 roadmap 與「什麼應該被集中」的決定由平台團隊與工程主管做出 |
| 草擬 AI 政策的更新與各團隊的遷移指南 | 哪些決定永遠留給人（人事、不可回復的使用者決定、永久刪除資料、等級與 policy 變更）由組織領導者訂定並簽核 |

> [!ai] AI 提醒
> 讓 agent 管理 agent 是一個誘人但危險的方向，例如讓一個「治理 agent」自動調整其他 agent 的等級。這會讓授權模型本身變成一個機率性的系統，而它正是整套架構中最需要確定性的部分。Agent 可以分析與建議，但等級的變更、policy 的修改與 kill switch 的觸發條件，應該由人決定、由確定性的程式執行。

## 47.13 專家怎麼想

- **「這個服務如果沒有 SRE，會怎樣？」** 資深 SRE 主管在決定 engagement 時，不是問「這個服務重不重要」，而是問 SRE 的參與能帶來多少邊際改善。一個重要但已經很成熟的服務，可能透過平台支援就夠了；一個中等重要但正在快速成長的服務，可能更需要一位 embedded SRE。
- **把 SRE 的知識變成預設值。** 每當 SRE 在第三個服務上給出相同的建議，專家就會問：這能不能變成 golden path 的預設、框架的行為或一個自助檢查？SRE 的影響力來自它能改變多少服務的預設，而不是它能親自看多少服務。
- **授權要能被一句話說清楚。** 專家看到一個 agent，會要求 owner 用一句話回答：「它在哪些流程、哪些環境、被允許做到哪一步，超出時會發生什麼。」答不出來，代表授權沒有被設計，只是被累積出來的。
- **先問誰負責，再問能不能做。** 在討論一個 agent 能不能升級之前，專家會先確認：owner 是誰？owner 是否理解 agent 的行為並願意為它值班？沒有 owner 的能力，就是沒有人負責的風險。
- **AI 會放大組織原本的樣子。** 專家不會把 AI 導入當成獨立的專案。如果一個團隊的 review、測試與 SLO 本來就薄弱，給它更多 agent 只會讓問題更快出現。所以 AI 的 roadmap 往往同時是改善工程基礎的 roadmap。
- **量測人的負擔，而不只是機器的產出。** AI 產出越多，人的審查與判斷就越稀缺。專家會追蹤 reviewer 的負擔、核准的速度是否快到不合理，以及值班者是否還能理解 agent 的判斷。

## 47.14 動手練習

1. 為 Harbor 的五個團隊各挑一個服務，依「失效影響」與「維運複雜度」分級，並為每個服務選擇 engagement 模式，寫出一份一頁的 engagement charter：SRE 提供什麼、服務團隊承諾什麼、何時重新檢討。
2. 設計一份 hand-back 的觸發條件與流程，至少包含三個可量測的觸發條件、預警期、交還後 SRE 的角色與重新接手的條件。說明你會如何避免團隊為了不觸發條件而隱藏問題。
3. 為 Harbor 的 golden path 新增一個 `harbor new agent` 指令：列出它應該自動建立的所有東西（身份、目錄登記、gateway 設定、eval 範本、預設等級等），並說明每一項對應本章哪一節。
4. 擴充 47.10 的程式：加入 delegation，讓 `decide` 接受一個 `on_behalf_of` 參數，有效權限為 agent 授權與委派者權限的交集；寫一個測試案例，證明權限較少的人無法透過 agent 做越權的事。
5. 再擴充 47.10 的程式：當 agent 的 owner 被標記為離職時，所有授權自動降到 L1，並在稽核紀錄中記錄原因；再加入一個 kill switch，可以依 agent、workflow 或全公司停用。
6. 挑一個你使用過或設計過的 AI agent，用 L0–L5 描述它在每個 workflow × 環境中的等級，列出升到下一級需要的證據，以及你會設定的降級條件。

## 本章重點整理

- 組織長大後，SRE 的人數必須次線性成長於服務數量，所以 SRE 要回答的問題是「投入放在哪裡，能讓整體可靠性提升最多」。
- SRE engagement 從上線前的 PRR，演進到設計階段的早期參與，再到框架與平台；大組織會同時使用三種方式。
- 服務的生命週期決定 SRE 何時參與最有價值，越早參與，修正架構問題的成本越低；淘汰中的服務同樣需要明確的負責人。
- 依失效影響與維運複雜度把服務分級，並把每一段 engagement 寫成 charter，明確 SRE 提供什麼、服務團隊承諾什麼。
- Hand-off 前服務要通過 PRR 並有證據；交接的是第一線維運責任，開發團隊仍擁有程式碼與修 bug 的責任。
- Hand-back 的觸發條件應該可量測、有預警期，並保留重新接手的路徑，讓它成為改善的機制而不是懲罰。
- Platform engineering 把共同需求做成內部產品；golden path 讓正確的做法成為最省力的做法，平台工作量若隨使用團隊數線性成長，就還不是平台。
- AI agent 的 autonomy 分為六級：L0 無存取、L1 唯讀輔助、L2 提案、L3 核准後執行、L4 有界自主、L5 目標自主；等級描述的是 side effect 與人的把關位置，不是模型的聰明程度。
- 授權的單位是 workflow × 環境；等級是天花板，每一次動作仍要經過 policy 檢查；L5 只適用於可完全回復、被環境本身限制的範圍。
- 升級要有隨等級變嚴的證據，降級條件要事先寫好並自動執行，包括模型或 prompt 變更、相關事故與 owner 離職。
- 每個 agent 要有獨立的非人類身份、短效憑證與最小權限；代表人行動時，有效權限是 agent 授權與委派者權限的交集，以避免 confused deputy。
- 所有 agent 的動作經過集中的 tool gateway，依序檢查身份、等級、policy，產生 allow、escalate 或 deny，並寫入完整稽核紀錄與支援多粒度的 kill switch。
- Agent 的版本由模型、prompt、工具、retrieval 與 policy 共同組成，任何一部分的變更都要走 review、eval 與漸進 rollout。
- Agent 可以是 R，不能是 A；每個 agent 要有具名的 owner，組織應以比自製更省力的 paved road 取代禁令，避免 shadow AI。
- 評估 AI 導入要看交付與穩定性、AI 參與變更的失敗率與人的負擔，而不是採用率；AI 會放大組織原有的工程能力與弱點。

## 延伸問答

> [!question]- Q1. 為什麼 SRE 的人數不應該隨服務數量線性成長？這和「SRE 要接手最重要的服務」矛盾嗎？
> 如果每多一個服務就要多一位 SRE，SRE 本身就變成第 6 章說的「線性成長的人工工作」：組織每擴張一次，SRE 的招募就成為瓶頸，而且大部分 SRE 的時間會花在重複的維運上，沒有餘力做工程改善。SRE 的價值在於把可靠性的知識變成工具、框架與平台，讓沒有 SRE 直接參與的服務也能具備基本的可靠性，這樣 SRE 能影響的服務數量才能遠大於 SRE 的人數。
>
> 這和「接手最重要的服務」不矛盾，而是同一個策略的兩面。最關鍵的少數服務失效代價最高、維運最複雜，值得 SRE 深度投入；其他大部分服務則透過平台、自助檢查與顧問支援。重點在於深度支援是稀缺資源，必須有意識地分配，而不是誰先開口就給誰。

> [!question]- Q2. 你是 SRE 主管，seller 團隊的通知服務每週產生二十多個 page，seller 團隊說他們忙著新功能。你會直接 hand-back 嗎？
> 不會直接交還，而是先啟動事先約定好的流程。第一步是拿出數據：過去幾週的 page 數、每個 page 的類型、有多少是可行動的、SRE 在這個服務上花了多少時間。和 seller 團隊主管一起看這些數據，通常會發現大部分 page 集中在少數幾種原因，例如第三方供應商的延遲告警，這些往往可以透過改成症狀告警或改成 ticket 快速消除。
>
> 接著約定一段改善期，例如四週，列出具體的改善清單與 owner。如果改善期內指標回到上限內，就維持 SRE 支援；如果沒有，才正式交還，並明確說明 SRE 退回顧問角色、會協助完成改善清單，以及重新接手的條件。這樣做的目的是讓交還成為一個雙方都理解的機制，而不是突然的懲罰。Harbor 的經驗也顯示，交還之後由 seller 團隊自己承受 page，反而讓他們很快排入了改善工作，這正是 hand-back 設計的用意。

> [!question]- Q3. Golden path 和「強制所有團隊使用同一套工具」有什麼不同？
> Golden path 的核心是「讓正確的做法最省力」，而不是「禁止其他做法」。它提供有立場的預設，例如統一的部署 pipeline、監控與 SLO 範本，讓團隊在第一天就具備可靠性的基礎；走這條路比自己從頭做更快，所以大部分團隊會自然選擇它。它同時允許有理由的團隊偏離，但偏離的團隊要自己承擔維護成本，並在服務目錄中標示，讓組織保有可見度。
>
> 強制推行的問題在於，當平台不支援某種合理的需求時，團隊只能選擇放棄需求或偷偷繞道，後者會讓組織失去可見度，這和 shadow AI 是同一個現象。判斷一個平台健康與否，可以看它的採用率是來自「好用」還是「被規定」，以及偏離的團隊是否願意說明原因。好的平台團隊會把偏離的原因當成產品回饋，決定是否把那個需求納入 golden path。

> [!question]- Q4. 為什麼 autonomy 等級要以「workflow × 環境」為單位，而不是給每個 agent 一個等級？
> 因為同一個 agent 在不同流程與環境中的風險完全不同。Harbor 的維運 agent 清理磁碟時，每個動作影響小、可以回復、量又很大，適合 L4；同一個 agent 執行資料庫 failover 時，動作罕見、影響巨大、很難回復，應該只到 L2，由人決定是否執行。如果只給 agent 一個等級，要嘛為了 failover 的安全把它壓到 L2，讓清理磁碟這類 toil 無法自動化；要嘛為了清理磁碟把它升到 L4，讓 failover 也能自動執行。
>
> 更危險的是授權外溢，也就是柏翰事件的情況：清理 agent 在 staging 被允許自動刪除，這個授權因為只有一個數字，就悄悄延伸到了 production。以 workflow × 環境為單位，並由 tool gateway 在每一次動作時檢查，就能讓「staging 的 L4」和「production 的 L2」同時成立，而且一次 prompt 修改無法讓 agent 越過環境的邊界。

> [!question]- Q5. L3（核准後執行）聽起來比 L4 安全，為什麼有時候把動作升到 L4 反而更安全？
> L3 的安全性建立在一個假設上：人會認真看每一筆核准。當核准的數量很大、每一筆又很相似時，這個假設很快就會失效。值班者一天要核准兩百筆重啟，很自然會在幾天後開始不看內容直接按下核准，這時 L3 實際上變成了「沒有邊界的自動執行」，比 L4 還危險，因為 L4 至少有由工具強制的動作清單、影響上限、速率與預算。
>
> 所以對量大、單筆影響小、可以回復的動作，更安全的做法是把邊界想清楚、寫成 policy 並由 gateway 強制，然後升到 L4，讓超出邊界的情況自動退回給人。這樣人的注意力被保留給真正需要判斷的例外，而不是被大量例行核准消耗掉。L3 適合的是量少、每一筆影響大、值得人花幾分鐘思考的動作，例如 production 的 rollback 或擴容。

> [!question]- Q6. 一位客服人員只能查看自己負責的賣家的訂單，但這位客服人員使用的 AI 助理 agent 被授權讀取所有訂單。這樣有什麼問題？該怎麼設計？
> 這是典型的 confused deputy 問題。Agent 擁有比客服人員更大的權限，如果它用自己的權限回應請求，客服人員就能透過 agent 查到原本看不到的訂單，不論是刻意的（例如在問題中要求「也幫我查一下另一個賣家的訂單」），還是透過 prompt injection 被誘導的（例如某筆訂單備註中寫了指令）。稽核紀錄上看起來是 agent 在做合法的查詢，實際上發生了越權存取。
>
> 正確的設計是讓 agent 代表人行動時，有效權限為「agent 被授權的範圍」與「委派者權限」的交集。客服人員委派 agent 查詢時，agent 只能看到這位客服人員本來就能看到的訂單；排程觸發、沒有委派者的工作，則只用 agent 自己的授權。這個交集要在 tool gateway 中由確定性的程式計算與強制，而不是在 prompt 中要求 agent「只查詢使用者有權看的資料」，因為後者正是 prompt injection 能繞過的地方。稽核紀錄也要同時記錄 agent 身份與委派者，事後才能追溯。

> [!question]- Q7. Harbor 的維運 agent 已經在 L4 穩定運作半年，模型供應商宣布要更新模型版本。你會怎麼處理？
> 把它當成一次 agent 的版本變更，而不是一次單純的供應商升級。Agent 的行為由模型、prompt、工具、retrieval 與 policy 共同決定，模型改變就可能讓同樣的 prompt 產生不同的判斷，而且不會出現錯誤碼。依照 Harbor 的規則，相關 workflow 的等級先降回 L2，新版本要重新通過能力、安全與回歸 eval，再以 shadow mode 和舊版本比較判斷的差異。
>
> Shadow 期間要特別檢查每一筆不一致，以及有沒有任何不安全的建議。證據足夠之後，依 L2 到 L3、L3 到 L4 的條件逐步升回，而不是一次恢復到 L4。實務上還有兩個細節：一是盡量固定模型版本，讓更新發生在自己選擇的時間，而不是供應商預設切換的那一天；二是在線上持續執行一小組 canary eval，偵測供應商沒有預告的行為變化。這個過程會讓自動化暫時倒退，但它換到的是「我們知道新版本在哪些情況下表現不同」。

> [!question]- Q8. 面試題：如果你負責讓一個 200 人的工程組織導入 AI agent，前三個月你會做什麼？
> 一個好的回答會先處理可見度與責任，再處理能力。第一個月盤點現況：組織中有哪些 agent、誰在用、用什麼身份、能碰到哪些系統、owner 是誰。這一步幾乎一定會發現使用個人 token、沒有 owner 或權限過大的 agent。同時訂出一份依風險分級的 AI 政策，說清楚哪些用法只需核可的模型服務、哪些需要獨立身份與稽核、哪些需要完整的 gateway 與 eval，以及哪些決定永遠留給人。
>
> 第二個月建立最薄的可用平台：agent 的獨立身份、服務目錄登記、一個集中的 tool gateway 與稽核紀錄，並提供 `new agent` 這類比自製更省力的建立方式，同時設定個人 token 的停用期限。第三個月挑一兩個有清楚驗證方式、影響範圍小、重複成本高的 workflow，例如磁碟清理或依賴更新，依 L0–L5 的升級條件走一次完整流程，讓組織看到授權是如何靠證據取得的。整個過程的指標不是採用率，而是交付與穩定性是否改善、reviewer 的負擔是否可控，以及 agent 相關的事故是否能被快速追溯與停止。回答時可以補充：如果組織的 review、測試與 SLO 本身很薄弱，這三個月同時也要投資這些基礎，因為 AI 會放大既有的弱點。

## 延伸閱讀

- [Site Reliability Engineering — The Evolving SRE Engagement Model](https://sre.google/sre-book/evolving-sre-engagement-model/)：PRR 模型、早期參與與框架平台三個階段的演進。
- [The Site Reliability Workbook — Table of Contents](https://sre.google/workbook/table-of-contents/)：從目錄找到〈SRE Engagement Model〉與〈SRE Team Lifecycles〉，有服務生命週期與 SRE 組織成長的實務建議。
- [DORA — Introducing DORA's inaugural AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)：哪些組織能力決定了 AI 導入能否帶來效益。
- [Google Cloud — How Google SRE is using agentic AI to improve operations](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)：SRE 組織如何把 agent 引入維運工作。
- [OWASP — Top 10 for Large Language Model Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)：設計 agent 權限、tool gateway 與安全 eval 時，可以對照的常見風險，例如過度授權與 prompt injection。
- [NIST — AI Risk Management Framework: Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)：組織層級管理生成式 AI 風險的框架，可作為撰寫 AI 政策的參考。
