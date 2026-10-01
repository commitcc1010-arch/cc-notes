---
chapter: 19
title: Version Control、Branches 與 Small Batches
part: 3
---

# 第 19 章　Version Control、Branches 與 Small Batches

> [!abstract] 本章地圖
> **核心問題**：當幾十個人同時修改同一個系統，要怎麼讓每個人的變更盡早、安全地整合到同一份「真相」，並且出事時能精準地找出與撤回某一個變更？
>
> **你會學到**：
> - 說清楚 version control 解決的三件事（歷史、協作、回復），以及集中式與分散式 VCS 的實際差異
> - 定義組織的 source of truth，並讓 production 上的每個版本都能追溯到一個 commit
> - 估算長期分支的整合成本，理解為什麼衝突會隨分支壽命加速成長
> - 用 trunk-based development、feature flag 與 branch by abstraction 取代長期分支
> - 比較 monorepo 與 polyrepo，並解釋 One Version rule 為什麼比 repo 形狀更重要
> - 把變更切成可 review、可 bisect、可 revert 的 commit 與 PR，並理解 merge queue 在防止什麼
>
> **前置知識**：第 16 章（code review 與小型變更）、第 18 章（deprecation 與遷移）
>
> **對應原書**：SWE 第 16 章〈Version Control and Branch Management〉

## 19.1 故事：七週的分支與一個撤不回來的 merge

Harbor 已經有 40 位工程師，分成結帳、金流、搜尋、賣家後台與平台五個團隊，大部分程式碼仍然放在同一個主要的 monolith repository（另外還有十幾個小 repo，19.7 節會談）。年初，產品經理 Lisa 提出「新結帳流程」：把原本四個步驟的結帳頁縮成一頁，支援折價券疊加與分期付款。結帳團隊的 tech lead 美華估計要做七週。

為了「不要影響 main 的穩定」，團隊開了一條叫 `checkout-v2` 的分支。初階工程師阿凱負責折價券的部分，阿凱很認真，每天都在分支上 commit。前兩週一切順利；第三週，金流團隊把手續費計算從 `calc_fee` 改名成 `compute_fee`，並更新了 main 上所有的呼叫端，但 `checkout-v2` 上新寫的十幾個呼叫端當然沒有被改到。第五週，平台團隊把 web framework 升了一個 major version，路由寫法全部改變。

第七週是「整合週」。阿凱與美華花了四天解決 140 多個檔案的衝突，其中很多不是文字衝突，而是語意上的衝突：程式可以合併、可以編譯，但兩邊對同一個資料結構的假設已經不同。測試終於全綠之後，他們把整條分支用一個巨大的 merge commit 併進 main，週四晚上部署。

週五下午，客服發現有使用者疊了三張折價券後結帳金額變成負數。SRE 志明第一個反應是「revert 剛才那個變更」，但志明很快發現做不到：那個 merge commit 包含七週、兩百多個 commit 的工作，還有整合週裡為了解衝突而改寫的金流與平台程式碼。撤回它等於同時撤回其他團隊這兩個月的部分修正。最後團隊只能在壓力下 roll forward（往前修），一路修到晚上十點。

事後檢討時，工程經理 Kevin 問：「我們開分支是為了讓 main 穩定，結果為什麼反而造成了今年最不穩定的一天？」這一章要回答的就是這個問題：版本控制系統不只是存檔工具，分支、commit 與合併的方式，決定了團隊多早發現衝突、出事時能多精準地撤回。

## 19.2 Version control 在解決什麼問題

### 三件事：歷史、協作、回復

**Version control system**（VCS，版本控制系統）是記錄檔案隨時間變化的系統。它回答三類問題。第一是**歷史**：這行程式是誰、在什麼時候、為什麼改的？第二是**協作**：兩個人同時改同一個檔案，要怎麼合在一起而不互相覆蓋？第三是**回復**：新版本壞了，能不能精準回到某個已知良好的狀態？

一個人寫作業時，這三件事都可以靠「另存新檔」勉強應付。但只要有第二個人加入，或專案活超過幾個月，就會出現「`final_v3_真的最後.zip` 到底改了什麼」的問題。《Software Engineering at Google》把 version control 稱為工程師最核心的工具之一，原因正是第 3 章講的「軟體工程是隨時間積分的程式設計」：程式活得越久、參與的人越多，「理解過去的變更」與「安全地加入新變更」就越重要。

### Git 的心智模型：快照組成的圖

現在大多數團隊用 Git，所以先建立一個正確的心智模型。Git 的 **commit** 不是「一份 diff」，而是**整個專案在某一刻的快照**，加上作者、時間、說明，以及指向「上一個 commit」（parent）的指標。每個 commit 由內容計算出一個雜湊值（例如 `a1b2c3d`）當作 ID，所以內容只要改一個字元，ID 就不同，歷史無法被悄悄竄改而不留痕跡。

```text
                      main
                        │
  A ◀── B ◀── C ◀────── F          （F 是 merge commit，有兩個 parent）
              ▲        ╱
              └── D ◀─ E
                       │
                  checkout-v2

  每個字母是一個 commit（整個專案的快照）
  箭頭指向 parent；branch 只是一個「指向某個 commit 的名字」
```

讀這張圖時先看左邊：A、B、C 是 main 上依序產生的 commit。在 C 之後，有人開了 `checkout-v2` 分支，做出 D 與 E。**Branch**（分支）在 Git 裡只是一個會移動的標籤，指向某個 commit；新增 commit 時，標籤往前移。最後 F 是一個 **merge commit**，它有兩個 parent（C 與 E），代表「把兩條歷史合在一起」。Git 在合併時會找出兩邊的共同祖先（這裡是 C），比較兩邊各自改了什麼；如果兩邊改了同一段文字，就回報 **merge conflict**（合併衝突），要人決定保留哪一邊。

這個模型解釋了幾件後面會用到的事：開分支幾乎不花成本（只是建立一個標籤），所以「開分支很便宜」；但合併的成本取決於兩邊分開後各自累積了多少變更，所以「合併可能很貴」。分支的代價不在開，而在合。

### 集中式與分散式

VCS 大致分兩類。**集中式**（centralized）VCS，例如 Subversion（SVN）與 Perforce，只有一個中央伺服器保存完整歷史，開發者向它取出檔案、提交變更。**分散式**（distributed）VCS，例如 Git 與 Mercurial，每個開發者的電腦上都有完整的 repository 副本，可以離線 commit、開分支，之後再和別人交換。

| 面向 | 集中式（SVN、Perforce） | 分散式（Git、Mercurial） |
|---|---|---|
| 歷史存在哪裡 | 中央伺服器 | 每個 clone 都有完整歷史 |
| 離線工作 | 有限 | 可以 commit、開分支、看歷史 |
| 誰是「正式版本」 | 天生明確：伺服器上的 trunk | 技術上平等，靠組織約定（例如 GitHub 上的 main） |
| 超大型 repo | 只取出需要的部分，容易擴展 | 完整 clone 很大，需要 partial clone、sparse checkout 等技巧 |
| 權限控制 | 可以細到目錄 | 通常以 repo 為單位，細部靠 code owners 等機制 |

一個常見的誤解是「分散式 = 沒有中心」。原書特別指出：即使使用 Git，幾乎所有組織最後都會指定一個中央 repository 當作正式版本，因為團隊需要一個共同的答案來回答「現在的程式是什麼樣子」。分散式帶來的是工作方式的彈性（離線、本地實驗），而不是取消中心。Google 自己的主要 repository 跑在內部打造的集中式系統 Piper 上；原書的說法是，在 Google 的工作流程中，集中式、存放在雲端的 codebase 對擴展到那樣的規模是關鍵，早期嘗試改用 Git 這類工具也受限於 codebase 與使用者數量太大。

> [!warning] 常見誤解
> 「用了 Git，所以每個人的 clone 都是備份，不需要另外管理中央 repository。」本地 clone 可能過時、可能只有部分分支，也沒有 code review、權限與 CI 紀錄。中央 repository 的可用性、備份與存取控制仍然要當成正式的 production 系統來管理。

## 19.3 Source of truth：哪一份才算數

**Source of truth**（真相來源）是組織同意「以它為準」的那一份資料。對程式碼而言，通常就是中央 repository 的 main 分支（有些團隊叫 trunk，較舊的專案可能沿用 Git 早期的預設分支名稱；本書一律用 main）。這不是技術上的必然，而是組織的約定：當兩份程式碼不一致時，以 main 為準；要進入 production，必須先進入 main。

為什麼需要明確約定？想像 Harbor 沒有約定時的情況：阿凱的筆電上有一份修過 bug 的版本、某台 staging 機器上有人直接改過的設定、`checkout-v2` 分支上有七週的新功能。如果 production 出事，志明問「現在 production 跑的是什麼」，沒有人能給出唯一的答案。Source of truth 的價值在於，任何人在任何時候都能回答兩個問題：「現在的正式程式碼是什麼？」與「production 上跑的是哪一份？」

實務上，要讓 source of truth 真的成立，Harbor 採用了幾條規則：

- **所有會影響 production 的東西都進 VCS**：程式碼、設定檔、資料庫 schema migration、基礎設施定義（infrastructure as code）、alert 規則、runbook。直接登入機器改設定的變更，在 VCS 裡不存在，下一次部署就會被覆蓋，也沒有人能 review。
- **Production 能追溯到一個 commit**：每個部署出去的 artifact（例如 container image）都記錄它是從哪個 commit 建置的。Git tag（例如 `v2026.03.14`）只是一個可移動的名字，真正證明「這些 bytes 從哪裡來」的是 commit SHA、artifact 的內容雜湊與建置紀錄，第 27 章會講 provenance 的完整做法。
- **Main 隨時可以建置、可以測試**：如果 main 常常是壞的，大家就會改以「某個自己知道能跑的分支」為準，source of truth 就名存實亡。這也是第 28 章「broken build 優先 rollback」的理由。

> [!example] 例子
> Harbor 在 checkout 服務的 `/version` endpoint 回傳 commit SHA 與建置時間。週五事故時，志明第一步就是比對 production 的 SHA 與 main 的歷史，確認問題版本包含哪些 commit。這個小小的 endpoint，讓「現在跑的是什麼」從猜測變成查詢。

## 19.4 分支的真實成本

### 整合距離

既然開分支很便宜，為什麼 `checkout-v2` 會這麼痛？關鍵概念是**整合距離**（integration distance）：一條分支和 main 分開後，兩邊各自累積了多少尚未互相看見的變更。分支每多活一天，距離就多一點；合併時，所有累積的距離一次結清。

衝突的成長不是線性的。粗略地想：分支改了 a 個檔案，main 同期被別人改了 b 個檔案，兩邊撞到同一個檔案的數量大約和 a × b 成正比。分支活兩倍久，a 和 b 都變兩倍，單次合併的衝突就接近四倍：

```text
單次合併衝突 ≈ (分支每天改的檔案 × 天數) × (main 每天被改的檔案 × 天數) ÷ 總檔案數
              ∝ 天數²

算例：每天各改 6 與 25 個檔案、共 400 個檔案
  分開 2 天：(6×2) × (25×2) ÷ 400 ≈ 1.5 個衝突檔
  分開 10 天：(6×10) × (25×10) ÷ 400 ≈ 37.5 個衝突檔（實際會少一些，因為同一檔案被重複修改只算一次）
```

如果每兩天就整合一次，35 天的專案會遇到很多次小衝突，但總數遠少於最後一次結清。19.11 的程式會用模擬驗證這個直覺。更重要的是，小衝突發生時，改動的人記憶猶新，三分鐘就能解；大衝突發生時，很多變更是好幾週前寫的，作者可能已經不記得當初的假設。

### 文字衝突與語意衝突

Git 只能偵測**文字衝突**（textual conflict）：兩邊改了同一段文字。更危險的是**語意衝突**（semantic conflict）：兩邊改的是不同的檔案或不同的行，Git 順利合併，但合起來的程式邏輯是錯的。Harbor 故事中的 `calc_fee` 改名就是典型：金流團隊改名並更新了所有既有呼叫端，阿凱在分支上新增了呼叫端；兩邊沒有碰到同一行，Git 不會抱怨，但合併後的程式找不到 `calc_fee`。

語意衝突只能靠編譯、型別檢查與測試抓到，而且只有在「兩邊的變更真的放在一起」時才抓得到。長期分支的根本問題就在這裡：它延後了兩邊相遇的時間，也就延後了所有語意衝突被發現的時間。

### 三種分支，三種代價

不是所有分支都一樣有害。原書區分了幾種用途，代價差很多：

| 分支類型 | 用途 | 代價 | 原書與業界的建議 |
|---|---|---|---|
| 短命的 feature branch | 一個 PR 的工作區，幾小時到一兩天 | 很低：整合距離短，review 後即刪除 | 鼓勵 |
| 長期的 **dev branch**（開發分支） | 一個團隊或大功能在上面開發數週、數月 | 高：延後整合，最後一次性合併 | 原書明確反對，認為它把風險往後推並集中爆發 |
| **Release branch**（發行分支） | 從 main 切出一個要發布的版本，只接受修補 | 中：需要 cherry-pick 修補到多個分支 | 原書認為相對無害，問題不在分支技術而在用法：cherry-pick 越少越好，也不打算再合回 main；修補先進 main，再 cherry-pick 到 release branch |

Dev branch 的誘因很容易理解：「功能還沒做完，不想弄壞 main」。但它實際上是把「弄壞 main」的風險從每天一點點，換成最後一次全部。原書引用 DORA 的研究指出，trunk-based development、沒有長期 dev branch，和良好的技術成果之間有很強的正相關；這不代表開分支本身有罪，而是代表「整合得越晚，代價越高」這件事在大量團隊中都觀察得到。

Release branch 則是另一回事。行動 app 需要送審、企業客戶需要固定版本，這些情況下從 main 切出一個穩定點是合理的。紀律在於：release branch 上不開發新功能；修 bug 先修在 main，再 **cherry-pick**（把某個 commit 的變更複製到另一條分支）到 release branch。反過來（先修在 release branch 再補回 main）很容易忘記，下一個版本就會「復活」同一個 bug。

## 19.5 Trunk-based development

### 定義與做法

**Trunk-based development**（主幹開發）是一種讓所有開發者頻繁地把小變更整合進同一條主幹（main）的做法。它有兩種常見形式：小團隊直接 commit 到 main；較大的團隊使用很短命的 feature branch（通常不超過一兩天），經過 code review 與 CI 後合進 main。重點不是「完全沒有分支」，而是**沒有長期存在、與 main 分歧的分支**。

DORA 對這個能力的描述包含幾個可檢查的特徵：同時活躍的分支很少、分支在合併前的壽命很短（例如不到一天）、團隊很少或從不出現「程式碼凍結期」。Harbor 用這些特徵當作檢查表，而不是爭論名詞。

### 為什麼它能運作

Trunk-based development 不是單獨存在的習慣，它依賴幾個前提，缺一個就會失敗：

1. **快速、可信的 CI**（第 28 章）：每個變更合進 main 前都要跑過測試。如果 CI 要跑兩小時、而且常常 flaky，大家就會累積變更、減少合併次數。
2. **快速的 code review**（第 16 章）：PR 等三天才有人看，就不可能「每天合併」。
3. **小變更的能力**：會把工作切小，並且知道怎麼讓未完成的功能安全地存在於 main 上，也就是下一節的 feature flag 與 branch by abstraction。
4. **壞了先撤回**：main 被弄壞時，第一個動作是 revert 那個變更，而不是在 main 上慢慢修。小 commit 讓 revert 便宜。

### 常見分支模型比較

| 模型 | 長期分支 | 適合 | 主要風險 |
|---|---|---|---|
| **GitFlow**（develop、feature、release、hotfix 多條長期分支） | 有：main 與 develop 長期並存，feature 分支常活數週 | 有固定發行版本、多版本並存維護的產品（例如可安裝軟體） | 整合延後；hotfix 要同步到多條分支；流程複雜 |
| **GitHub flow**（main ＋短命 feature branch ＋ PR） | 無 | 持續部署的 web 服務 | 若 feature branch 實際上活很久，就退化成 dev branch |
| **Trunk-based development** | 無；release branch 可選且短命 | 高頻整合、需要快速回饋的團隊 | 需要 CI、flag、review 速度到位，否則 main 常壞 |

Harbor 之前名義上用 GitHub flow，但 `checkout-v2` 活了七週，實際上就是一條 dev branch。檢討後，Harbor 訂了一條簡單的規則：**任何分支超過三個工作天未合併，CI 機器人會在 PR 上提醒作者與 tech lead，並要求說明原因或拆分**。規則本身不是重點，重點是讓「分支壽命」這個看不見的成本變得看得見。

> [!warning] 常見誤解
> 「Trunk-based development 就是大家直接 push 到 main、不做 code review。」不是。大多數規模化的團隊仍然透過短命分支與 PR 做 review，只是分支在一兩天內就合併。真正的差別在整合頻率，而不是有沒有 PR。

## 19.6 用 feature flag 與 branch by abstraction 取代長期分支

### 把「整合」與「發布」拆開

開長期分支最常見的理由是：「功能還沒完成，不能讓使用者看到。」這句話混淆了兩件事。**整合**（integration）是讓程式碼進入 main、和別人的程式碼放在一起測試；**發布**（release）是讓使用者真的用到這個功能。長期分支把兩者綁在一起：功能做完才整合，整合了就發布。Trunk-based development 的關鍵技巧，是把它們拆開：程式碼每天整合，使用者在準備好之後才看到。

拆開的工具有三種，依情境選擇。

**Feature flag**（功能旗標，也叫 feature toggle）是一個在執行期決定「要不要走新程式路徑」的開關：

```python
# not-runnable
if flags.enabled("checkout_v2", user=current_user):
    return render_single_page_checkout(cart)
return render_legacy_checkout(cart)
```

新結帳流程的程式碼每天都合進 main、跟著每次部署一起上線，但 flag 預設關閉，使用者完全看不到。開發中可以只對內部員工開啟；完成後先開給 1% 使用者，再逐步擴大（第 29 章會講漸進發布與 canary）。這也是 **dark launch**（暗中上線）的基礎：程式已經在 production，但還沒有對使用者曝光。

**Branch by abstraction**（以抽象層取代分支）適合要替換一個深層元件、無法用單一 if 包住的情況，例如把整個折扣計算引擎換掉。做法分成五步：

```text
 步驟 1：找出所有直接呼叫舊實作的地方
         caller ──▶ OldDiscountEngine

 步驟 2：加入抽象層，讓 caller 只依賴介面（行為不變，可直接合進 main）
         caller ──▶ DiscountEngine 介面 ──▶ OldDiscountEngine

 步驟 3：在 main 上逐步寫新實作，用 flag 決定走哪一個
         caller ──▶ DiscountEngine 介面 ─┬▶ OldDiscountEngine
                                         └▶ NewDiscountEngine（flag 控制）

 步驟 4：逐步把流量切到新實作，觀察指標
 步驟 5：刪除舊實作與 flag，必要時移除抽象層
```

這張圖的重點在於：每一步都是一個可以獨立合進 main、獨立 review、獨立 revert 的小變更，而且每一步之後 main 都能正常運作。步驟 2 是純重構，不改行為；步驟 3 新增程式但預設不走；步驟 4 只改設定；步驟 5 是清理。這和第 18 章的 deprecation 流程是同一種思路：先建立新舊並存的狀態，再逐步遷移，最後移除舊世界。

第三種是**未接線的新程式**：新的 API endpoint 或新頁面先合進 main，但沒有任何路由或選單連到它。這最簡單，但只適用於「全新、不替換任何東西」的功能。

### Flag 的生命週期與債務

Feature flag 不是免費的。每個 flag 都讓程式多一條路徑，n 個彼此獨立的 boolean flag 理論上有 2ⁿ 種組合；沒有人會測試全部組合。Flag 也會被遺忘：功能已經百分之百開啟一年，舊路徑的程式碼還在，下一個工程師不敢刪。

最著名的反面案例之一是 2012 年的 Knight Capital 事件。這家證券交易公司在部署新交易程式時，重新使用了一個多年前用於舊功能的 flag；而八台伺服器中有一台沒有部署到新程式碼，那台機器上的 flag 一打開，就啟動了早已不該執行的舊邏輯。公司在大約 45 分鐘內損失超過四億美元。這個事故同時包含了部署不一致與 flag 重用兩個問題，教訓是：**舊的 flag 與舊程式碼要盡快刪除，flag 名稱永遠不要重複使用**。

業界常把 flag 依用途分類，生命週期差很多：

| 類型 | 用途 | 預期壽命 | Harbor 的例子 |
|---|---|---|---|
| Release flag | 讓未完成的功能安全地留在 main | 數天到數週，功能全開後立即刪除 | `checkout_v2` |
| Experiment flag | A/B 測試 | 實驗期間 | 推薦區塊的兩種排序 |
| Ops flag（kill switch） | 事故時關閉昂貴或有風險的功能 | 長期，但要定期演練 | 關閉 AI 客服 agent 的退款能力 |
| Permission flag | 依客群開放功能 | 長期，本質上是產品設定 | 企業賣家專屬報表 |

Harbor 的規則是：每個 release flag 建立時必須填 owner 與預計刪除日期；過期的 flag 會在每週的平台報表中列出，並自動開一張清理工單給 owner。

## 19.7 Monorepo 與 polyrepo

### 兩種形狀

**Monorepo**（單一倉庫）是把組織內許多專案、服務、函式庫放在同一個 repository；**polyrepo**（多倉庫）是每個服務或函式庫一個 repository。Google、Meta 等公司以大型 monorepo 聞名；也有很多成功的組織使用 polyrepo。

| 面向 | Monorepo | Polyrepo |
|---|---|---|
| 跨專案變更 | 一個 commit 就能同時改函式庫與所有使用者，原子性完成 | 要在多個 repo 各發一次 PR，協調發布順序 |
| 依賴版本 | 天然傾向「大家都用 HEAD」，容易做到 One Version | 每個 repo 自己釘版本，容易出現多版本並存 |
| 可見性 | 容易搜尋所有使用者（第 21 章的 code search） | 需要額外工具跨 repo 搜尋 |
| 權限與隔離 | 需要 code owners、目錄權限等機制 | repo 邊界就是天然的權限邊界 |
| 工具需求 | 需要能處理大規模的 build（第 27 章）、CI 只跑受影響的部分、sparse checkout | 標準工具即可，但跨 repo 協調要自己做 |
| 失敗模式 | 一個壞的共用變更影響所有人；CI 若不做 test selection 會越來越慢 | 共用函式庫的版本分裂，升級時要逐一追 |

### 真正重要的不是形狀

原書對這個題目的立場很值得注意：作者明確表示，他們描述的 monorepo 做法並不是適合每個組織的完美答案；重要的不是要不要用 monorepo，而是遵守 One Version 原則（下一節）。從工具面來看也是如此：Monorepo 的好處（原子性跨專案變更、單一版本）需要 build 系統、code search、CI test selection 的支撐；沒有這些，monorepo 只會變成一個很大、很慢、誰都能改壞的 repo。

Harbor 的情況是：主要 monolith 在一個 repo，另外有 12 個小 repo（行動 app、幾個獨立服務、`harbor-common` 共用函式庫）。問題出現在 `harbor-common`：搜尋服務釘在 1.8 版，賣家後台釘在 2.3 版，結帳服務用 2.6 版。每次修一個安全問題，要在三條版本線上各修一次。美華在 ADR（第 7 章）中的結論是：短期內不做全面的 monorepo 遷移，而是先對 `harbor-common` 落實「單一版本」政策，並讓 CI 在 `harbor-common` 每次發布時，自動對所有使用者發升級 PR。Repo 形狀可以之後再討論，版本分裂必須先處理。

## 19.8 One Version rule

### 定義

原書提出的 **One Version rule**（單一版本規則）可以這樣理解：**對組織內的任何一個元件，開發者永遠不應該面臨「我要依賴哪一個版本」的選擇**。函式庫只有一個正式版本（通常就是 main 上的那一份），所有使用者都用它。

這條規則看起來很嚴格，但它解決的是一個隨規模惡化的問題。如果允許多版本並存：

- 每個版本都要維護，安全修補要做好幾次；
- 兩個使用不同版本的元件放進同一個程式時，可能出現 **diamond dependency**（菱形依賴）衝突，第 20 章會詳細解釋；
- 函式庫作者無法知道「改了這個行為會影響誰」，因為舊版本的使用者看不到新變更，問題要等到他們某天升級時才爆發，而那時距離變更已經很久了。

### 它和分支的關係

One Version rule 其實就是「不要有長期分支」在依賴關係上的延伸。一條長期存在的 dev branch、一個被 fork 出來自己改的函式庫副本、一個釘死在舊版本的依賴，本質上都是「同一個元件有兩個版本」。原書特別警告不要讓「選擇」出現：一旦有人可以選舊版本，就會有人留在舊版本，而留在舊版本的人越多，未來的升級就越貴（第 4 章的升級成本曲線）。

實務上，One Version 需要配套才能維持：函式庫作者改了行為，要能找到所有使用者並一起修（第 21 章的 large-scale change），或提供遷移期的相容層（第 18 章）；CI 要能在函式庫變更時跑所有使用者的測試，這就是第 20 章「live at head」的基礎。

> [!tip] 怎麼判斷你是否違反 One Version
> 問一個簡單的問題：「如果明天發現這個共用函式庫有安全漏洞，我們要修幾個地方？」答案若大於一，就有多版本問題。

## 19.9 Commit 與 PR 的大小：讓變更可以被理解與撤回

### 好 commit 的條件

小批次（small batches）不只是「分支要短」，也包含「每一個變更要小而完整」。一個好的 commit（或 PR，視團隊是否 squash 而定）有幾個特徵：

1. **一件事**：只做一件可以用一句話描述的事。「把 `calc_fee` 改名為 `compute_fee`」是一件事；「改名、順便修折價券 bug、順便升級 lint 規則」是三件事。
2. **自成一體**：合進去之後 main 仍然可以建置、測試通過。中間狀態壞掉的 commit 會讓之後的 bisect 失效。
3. **機械變更與語意變更分開**：格式化、改名、搬檔案這類機械變更，和改變行為的語意變更，放在不同 commit。Reviewer 可以快速掃過前者，專心看後者。
4. **Message 說明為什麼**：diff 已經告訴讀者「改了什麼」，message 要補上「為什麼要改」與「考慮過什麼」。

一個對比：

```text
不好的 message：
  fix bug

好的 message：
  折價券疊加時先套用百分比折扣，再套用固定金額折扣

  原本依加入順序套用，使用者先加固定金額券、再加 9 折券時，
  會得到比預期更低的金額，三張券疊加時甚至出現負數（事故 #2026-031）。
  改為固定順序並在最後檢查金額下限為 0。

  考慮過：禁止疊加。產品確認疊加是新結帳流程的核心需求，不採用。
```

半年後有人用 `git blame` 看到這行程式，第二個 message 能告訴對方當初的情境與被否決的選項，這和第 7 章 ADR 記錄被否決選項是同一個道理。

### 為什麼小變更讓 bisect 與 revert 有效

**`git bisect`** 是用二分搜尋找出「哪個 commit 引入了問題」的工具：給它一個已知好的版本和一個已知壞的版本，它每次挑中間的 commit 讓你測試，n 個 commit 只需要大約 log₂ n 步。從好到壞之間有 256 個 commit，只要測 8 次就能找到。但前提是每個 commit 都能獨立建置與測試，而且每個 commit 只做一件事；如果找到的 commit 是一個混合了七週工作的 merge，bisect 就只能告訴你「問題在那一大包裡」。

**Revert** 也一樣。`git revert` 會產生一個新的 commit，內容是某個舊 commit 的反向變更。對一個只做一件事的小 commit，revert 幾乎沒有副作用；對一個混合多件事的大 commit，revert 會連帶撤掉無辜的修改。Harbor 週五事故的根本困境就是這樣：問題只在折價券疊加的十幾行，但能撤回的最小單位是兩百個 commit 的合併。

### 歷史要不要改寫：merge、squash、rebase

合併 PR 時，常見三種方式：

| 方式 | 結果 | 優點 | 注意事項 |
|---|---|---|---|
| Merge commit | 保留分支上的所有 commit，加一個 merge commit | 完整保留歷史 | 分支上「wip」「fix typo」之類的 commit 也全部進入 main |
| Squash merge | 把整個 PR 壓成 main 上的一個 commit | main 歷史乾淨，一個 PR 一個 commit，revert 單位清楚 | PR 必須本身就小而單一，否則壓出來是一個大 commit |
| Rebase merge | 把分支上的 commit 逐一接到 main 最新的位置 | 線性歷史，保留細節 | 分支上每個 commit 都要能獨立通過測試，否則傷害 bisect |

選哪一種是團隊約定，沒有絕對答案；Harbor 選 squash merge，並因此要求「一個 PR 只做一件事」。不管選哪一種，有一條規則幾乎沒有例外：**不要改寫別人正在使用的共享分支歷史**。在自己的分支上 `rebase`、整理 commit 都沒問題；但對 main 或別人已經拉下來的分支做 `git push --force`，會讓其他人的歷史和中央 repository 對不上，甚至讓已經 review 過的變更消失。

### 大變更怎麼切

把大功能切小，有幾個常用的模式：

- **先重構，後改行為**：先送一個不改行為的 PR 讓程式更容易修改（例如步驟 2 的抽象層），再送真正的功能 PR。
- **由下往上**：先加資料結構與函式（還沒有人呼叫），再加呼叫端，最後接上 UI。
- **Expand / contract**：先新增新欄位或新 API、兩者並存，遷移使用者，最後刪除舊的（第 29 章會用在 schema migration）。
- **Stacked PR**（堆疊 PR）：把一連串互相依賴的小 PR 疊在一起，第二個建立在第一個之上，可以平行 review，再依序合併。有些 code review 工具原生支援，有些團隊用輔助工具管理。

> [!warning] 常見誤解
> 「小 PR 就是行數少。」行數只是代理指標。一個 30 行但同時改了金流邏輯與權限檢查的 PR，比一個 500 行、純粹由工具自動改名的 PR 更難 review。判斷標準是「reviewer 能不能在合理時間內完整理解它的影響」，以及「撤回它會不會連帶撤回別的事」。

## 19.10 Merge queue：兩個綠燈加起來可能是紅燈

### 問題：測試的是哪一個版本

在一般的 PR 流程中，CI 測試的是「PR 分支 ＋ 開分支時的 main」，或「PR 分支 ＋ 某個時間點的 main」。如果兩個 PR 都在同一段時間通過 CI，然後依序合併，沒有任何人測試過「main ＋ PR A ＋ PR B」這個組合。19.4 的語意衝突就是在這個空隙中溜進 main 的。

小團隊可以要求「合併前必須先 rebase 到最新 main 並重跑 CI」，但當每天有幾十個 PR 時，大家會不停地 rebase、重跑、再被別人搶先，形成一場賽跑。

### Merge queue 怎麼運作

**Merge queue**（合併佇列）把「合併」變成一個由系統執行的排隊流程：

```text
  PR 通過 review 與自己的 CI
          │
          ▼
  ┌──────────────── merge queue ────────────────┐
  │  [PR A] → 測試 main + A                      │
  │  [PR B] → 測試 main + A + B   （假設 A 會進） │
  │  [PR C] → 測試 main + A + B + C               │
  └──────────────────────────────────────────────┘
          │
   全部通過 → 依序合進 main
   B 失敗   → 退回 B，C 改測 main + A + C 後再決定
```

圖中的關鍵是第二列：PR B 不是對「現在的 main」測試，而是對「main 加上排在它前面的 PR A」測試。這樣合進 main 的每一個狀態都真的被測試過。為了不讓佇列變成瓶頸，系統通常會**推測性地平行測試**（同時跑 A、A+B、A+B+C 三組），或把幾個 PR **批次**一起測，失敗時再用二分法找出是哪一個造成的。GitHub、GitLab（稱為 merge train）等平台都提供這類功能，大型組織也常自建。

Merge queue 是 trunk-based development 在團隊變大後的必要配件，它保護的是 19.3 講的那條規則：main 隨時可以建置、可以測試。第 28 章會從 CI 的角度再談它的成本與 test selection。

## 19.11 動手寫：整合頻率與 merge queue 的模擬

### 模擬一：分支活越久，衝突越多

第一段程式模擬 Harbor 的新結帳流程：35 個工作天中，結帳團隊每天改 6 個檔案，其他團隊每天在 main 上改 25 個檔案，repo 共 400 個檔案。我們比較「每 1、2、5、10 天和 main 整合一次」與「35 天後才合併」的差別。

```python
import random

FILES = 400            # Harbor monolith 裡可能被改到的檔案數
PROJECT_DAYS = 35      # 新結帳流程預計開發 7 週（35 個工作天）
FEATURE_PER_DAY = 6    # 結帳團隊每天改到的檔案數
MAIN_PER_DAY = 25      # 其他團隊每天合進 main、改到的檔案數
RUNS = 200             # 重複模擬次數，取平均


def simulate(sync_every: int, rng: random.Random) -> tuple[int, int, int]:
    """回傳 (整合次數, 累計衝突檔案數, 單次最大衝突檔案數)。"""
    mine: set[int] = set()     # 上次整合後，分支改過的檔案
    theirs: set[int] = set()   # 上次整合後，main 改過的檔案
    syncs = total = worst = 0
    for day in range(1, PROJECT_DAYS + 1):
        mine.update(rng.sample(range(FILES), FEATURE_PER_DAY))
        theirs.update(rng.sample(range(FILES), MAIN_PER_DAY))
        if day % sync_every == 0 or day == PROJECT_DAYS:
            conflicts = len(mine & theirs)   # 兩邊都改過的檔案，要人工解衝突
            syncs += 1
            total += conflicts
            worst = max(worst, conflicts)
            mine.clear()
            theirs.clear()
    return syncs, total, worst


rng = random.Random(2026)
print("整合間隔 | 整合次數 | 平均累計衝突檔 | 平均單次最大衝突")
for every in (1, 2, 5, 10, 35):
    results = [simulate(every, rng) for _ in range(RUNS)]
    syncs = results[0][0]
    total = sum(r[1] for r in results) / RUNS
    worst = sum(r[2] for r in results) / RUNS
    print(f"{every:>4} 天  | {syncs:>6}   | {total:>12.1f}   | {worst:>12.1f}")
```

執行結果：

```text
整合間隔 | 整合次數 | 平均累計衝突檔 | 平均單次最大衝突
   1 天  |     35   |         12.9   |          1.9
   2 天  |     18   |         24.7   |          3.6
   5 天  |      7   |         55.8   |         11.2
  10 天  |      4   |         88.0   |         29.8
  35 天  |      1   |        146.7   |        146.7
```

逐步解讀：

1. `mine` 與 `theirs` 兩個集合記錄「上次整合之後」兩邊各改了哪些檔案。整合時，兩個集合的交集就是需要人工處理的衝突檔，處理完兩邊重新對齊，所以清空集合。
2. 「累計衝突檔」隨整合間隔變長而增加：每天整合，35 天總共約 13 個衝突檔；等到最後才合併，約 147 個，是十倍以上。原因就是 19.4 的 a × b：每次整合的衝突大約隨間隔的平方成長，而整合次數只隨間隔成反比減少，兩者相乘，總量仍隨間隔變長而增加。增加幅度沒有到 35 倍，是因為同一個檔案在一段時間內被改好幾次也只算一個衝突檔，400 個檔案的 repo 最後會「飽和」。
3. 「單次最大衝突」更能說明痛苦程度。每天整合時，一次最多兩個檔案，作者記憶猶新；35 天才合併，就是 Harbor 那個花了四天的整合週。
4. 這個模型刻意簡化：它只算文字衝突，假設每個檔案被改到的機率相同。真實系統的熱點檔案（例如路由表、設定）衝突更集中，而語意衝突根本不會出現在這張表上，它們要到合併後跑測試，甚至上了 production 才現形。所以真實的差距通常比模擬更大。

### 模擬二：兩個綠燈的 PR，合起來是紅燈

第二段程式重現 `calc_fee` 改名的語意衝突，並比較「兩個都綠燈就依序合併」與「經過 merge queue」的差別。

```python
import re

# 用「檔案名稱 → 內容」的 dict 代表一個 repo 快照
main = {
    "fees.py": "def calc_fee(amount):\n    return round(amount * 0.02)\n",
    "checkout.py": "from fees import calc_fee\nfee = calc_fee(1000)\n",
}

# PR A：把 calc_fee 改名為 compute_fee，並更新所有既有呼叫端
pr_a = {
    "fees.py": "def compute_fee(amount):\n    return round(amount * 0.02)\n",
    "checkout.py": "from fees import compute_fee\nfee = compute_fee(1000)\n",
}
# PR B：新增退款模組，呼叫舊名稱 calc_fee（作者開分支時它還存在）
pr_b = {
    "refund.py": "from fees import calc_fee\nback = -calc_fee(500)\n",
}


def apply(base: dict, change: dict) -> dict:
    """套用變更。兩個 PR 沒有改到同一個檔案，所以 Git 不會回報任何衝突。"""
    merged = dict(base)
    for path, content in change.items():
        merged[path] = content
    return merged


def ci(snapshot: dict) -> list[str]:
    """極簡 CI：每個 import 的名稱都必須在 fees.py 中有定義。"""
    defined = set(re.findall(r"def (\w+)\(", snapshot["fees.py"]))
    errors = []
    for path, src in snapshot.items():
        for name in re.findall(r"from fees import (\w+)", src):
            if name not in defined:
                errors.append(f"{path}: 找不到 {name}")
    return errors


print("PR A 對舊 main 測試：", ci(apply(main, pr_a)) or "通過")
print("PR B 對舊 main 測試：", ci(apply(main, pr_b)) or "通過")

# 沒有 merge queue：兩個都綠燈就依序合併
naive = apply(apply(main, pr_a), pr_b)
print("依序直接合併後的 main：", ci(naive) or "通過")

# 有 merge queue：每個 PR 都要對「main + 排在它前面的 PR」重新測試
queue_main = main
for name, pr in (("PR A", pr_a), ("PR B", pr_b)):
    candidate = apply(queue_main, pr)
    errors = ci(candidate)
    if errors:
        print(f"merge queue 退回 {name}：{errors}")
    else:
        queue_main = candidate
        print(f"merge queue 合併 {name}")
print("merge queue 後的 main：", ci(queue_main) or "通過")
```

執行結果：

```text
PR A 對舊 main 測試： 通過
PR B 對舊 main 測試： 通過
依序直接合併後的 main： ['refund.py: 找不到 calc_fee']
merge queue 合併 PR A
merge queue 退回 PR B：['refund.py: 找不到 calc_fee']
merge queue 後的 main： 通過
```

逐步解讀：

1. 每個 repo 狀態用一個 dict 表示，`apply` 就是「把 PR 的檔案蓋上去」。PR A 改了 `fees.py` 與 `checkout.py`，PR B 只新增 `refund.py`，兩者沒有碰到同一個檔案，所以在真實的 Git 裡也不會出現文字衝突。
2. `ci` 是一個只檢查「import 的函式是否存在」的極簡測試，對應真實世界的編譯、型別檢查與單元測試。兩個 PR 各自對舊 main 測試都通過。
3. 依序直接合併後，main 壞了：`refund.py` 呼叫了已經不存在的 `calc_fee`。這就是語意衝突，Git 完全看不出來。在 Harbor，這代表下一個從 main 開分支的工程師會拿到一個壞掉的起點。
4. Merge queue 讓 PR B 對「main ＋ PR A」重新測試，發現問題就退回給作者，main 始終保持可用。代價是 PR B 的作者要多等一輪並修改程式，但這個代價是在一個人的 PR 上付，而不是在所有人的 main 上付。

## 19.12 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| 長期 dev branch 保護 main | 整合延後，衝突與語意錯誤在最後集中爆發 | `checkout-v2` 活七週，整合週四天，上線後無法 revert | 每天整合；用 flag 或 branch by abstraction 隔離未完成功能；分支壽命超過門檻就提醒 |
| Trunk-based development | CI 慢、flaky 或 review 慢時，main 常壞或大家偷偷累積變更 | CI 要 90 分鐘，工程師一天只敢合一次，PR 變大 | 先投資 CI 速度與穩定性（第 26、28 章）；壞了先 revert |
| 大量 feature flag | 組合爆炸、舊路徑沒人敢刪、flag 被重用 | 一年前全開的 flag 仍在，新人改到舊路徑，或有人重用舊 flag 名稱 | 每個 release flag 有 owner 與到期日；過期自動開清理工單；禁止重用名稱 |
| Monorepo | 沒有對應的 build、CI 與權限工具 | 任何人都能改共用模組；每個 PR 跑全部測試，CI 變成一小時 | 先導入 code owners、test selection、遠端 build cache，再擴大 monorepo |
| Polyrepo | 共用函式庫版本分裂，跨 repo 變更難以協調 | `harbor-common` 三條版本線，安全修補做三次 | 對共用元件落實 One Version；自動化升級 PR；跨 repo 搜尋工具 |
| Squash merge | PR 本身太大時，壓出一個無法精準 revert 的 commit | 一個 PR 混合重構與功能，squash 後只能整包撤回 | 規定一個 PR 一件事；機械變更與語意變更分開送 |
| Merge queue | 佇列成為瓶頸，或 flaky 測試讓無辜的 PR 被退回 | 尖峰時段佇列排了二十個 PR，每個要跑 30 分鐘 | 推測性平行測試、批次測試、修復 flaky test、只跑受影響的測試 |
| 過度追求極小 commit | 中間狀態無法建置，破壞 bisect；reviewer 被大量瑣碎 PR 淹沒 | 一個功能拆成 40 個 PR，其中幾個單獨合進去會讓 main 壞掉 | 以「可獨立理解、可獨立通過測試」為切分標準，而不是行數 |

## 19.13 AI 時代：什麼變了？

AI coding agent 改變了這一章的兩個基本假設：產生變更的速度，以及「誰」在操作 repository。

**第一，變更產生得太快，小批次的紀律更重要。** 人類寫一個 2,000 行的 PR 要好幾天，自然會在中途停下來 commit、push、找人看。Agent 可能在幾分鐘內產生同樣大小的 diff，而且常常「順便」改了格式、重構了不相關的函式、更新了依賴。Harbor 在導入 agent 的第一個月就收到一個 2,800 行的 PR，同時包含折價券邏輯修正、測試重寫與 lint 修正。Reviewer 的注意力不會因為程式是 AI 寫的而變多，所以 review 品質反而下降。Harbor 的做法是在 agent 的任務說明中寫明「一個任務一個 PR、機械變更與行為變更分開、單一 PR 超過 400 行要先停下來提出切分計畫」，並在 CI 中檢查 PR 是否同時改動多個 code owner 範圍。

**第二，agent 是另一個在操作 Git 的「人」，需要權限邊界。** Agent 可能執行 `git reset --hard`、`git push --force`、刪除它認為「沒用」的檔案，或把測試失敗的檔案直接移除。這些動作在人類手上已經很危險，交給一個不完全理解上下文的 agent 更危險。Harbor 的 guardrails 包括：agent 一律在獨立的分支或 **worktree**（Git 的一個功能，讓同一個 repository 同時有多個工作目錄）中工作；開始前檢查工作目錄是否有未提交的修改，有就停止並回報，而不是覆蓋；中央 repository 對 main 開啟分支保護，任何身份（包括 agent 的服務帳號）都不能 force push 或略過 merge queue。

**第三，AI 讓 commit history 的價值上升。** Agent 在理解一段程式時，會讀 commit message、PR 描述與 blame 歷史。寫著「fix」的 commit 對人和 agent 都沒有幫助；說明「為什麼」與「考慮過什麼」的 commit message，是之後 agent 能否做出正確修改的關鍵上下文。反過來，agent 也可以幫忙寫出更好的 message，前提是人類確認它描述的「為什麼」是真的，而不是從 diff 猜出來的。

**第四，agent 讓 trunk-based development 更可行，也更需要 merge queue。** Agent 擅長把一個大變更拆成一系列小步驟（例如 branch by abstraction 的五步），並為每一步補上測試。但當很多 agent 同時送出很多小 PR，語意衝突的機會也增加，merge queue 從「大團隊才需要」變成「有 agent 就需要」。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 把一個功能拆成一系列可獨立合併的 commit 計畫（重構、抽象層、新實作、切換、清理） | 切分是否合理、每一步是否真的不改行為，由作者與 reviewer 確認；計畫要先被人核准再執行 |
| 草擬 commit message 與 PR 描述，列出改了哪些檔案、可能影響哪些模組 | 「為什麼要改」與被否決的選項必須由人確認；不接受 agent 憑 diff 推測動機 |
| 協助 `git bisect`：自動在每個候選 commit 上執行重現腳本，回報第一個壞掉的 commit | 是否 revert、revert 會連帶影響什麼，由值班者與 code owner 決定 |
| 掃描過期的 feature flag，產生刪除 flag 與舊路徑的 PR | Flag 是否真的可刪（是否仍有客群依賴、是否是 kill switch）由 owner 決定 |
| 在 merge queue 失敗時分析是哪兩個 PR 的組合造成衝突，提出修正建議 | 修正要經過一般的 review 與 CI，不能因為是「修 main」就略過 |
| 在獨立 worktree 中完成任務並提交 PR | 禁止 agent 對共享分支 force push、`reset --hard`、刪除未追蹤檔案；分支保護對 agent 身份一樣生效；以刪除或跳過測試讓 CI 變綠一律退回 |

> [!ai] AI 提醒
> 不要用「agent 產生的 PR 數量」或「合併的行數」衡量 agent 的效益。這會鼓勵大 PR 與不必要的變更。比較好的觀察是：agent 的 PR 被 revert 的比例、review 花費的時間、以及合併後一週內是否需要後續修正（第 14 章）。

## 19.14 專家怎麼想

- **「這個變更出事時，最小的撤回單位是什麼？」** 資深工程師在送出 PR 前會先想 revert。如果答案是「要連同別人的工作一起撤」，就代表切得不夠好。能精準撤回，是 production 可靠性在 version control 層的第一道保護。
- **把分支壽命當成風險指標。** 專家看到一條活了兩週的分支，不會問「快做完了嗎」，而會問「為什麼還沒整合、要怎麼切成今天就能合併的一塊」。分支越老，每天的利息越高。
- **先問 One Version，再問 repo 形狀。** 被問到「要不要遷移到 monorepo」時，有經驗的人會先問「我們現在有多少個共用元件存在多版本」與「我們有沒有能力在一天內找到並更新所有使用者」。前者是問題，後者是能力，repo 形狀只是手段。
- **Flag 是有到期日的負債。** 新增 flag 時就決定誰負責、何時刪除。專家對「暫時先加一個 flag」的反應是：「好，刪除它的工單在哪裡？」
- **Main 壞掉時，先 revert 再討論。** 修好壞掉的 main 不是作者的面子問題，而是所有人的生產力問題。能在幾分鐘內 revert 的組織，才敢讓大家頻繁合併。
- **歷史是寫給未來讀者的文件。** Commit message、PR 描述與 ADR 一起構成「為什麼系統長這樣」的證據。事故調查、新人 onboarding、AI agent 理解程式碼，都依賴它。

## 19.15 動手練習

1. 打開你手上的一個 repository，找出目前所有未合併的分支，列出每條分支和 main 分開了幾天、領先與落後 main 各幾個 commit（`git rev-list --left-right --count main...分支名`）。哪幾條已經是事實上的 dev branch？
2. 修改 19.11 的模擬一，加入「熱點檔案」：讓 5% 的檔案被修改的機率是其他檔案的十倍（提示：用 `rng.choices` 搭配權重）。觀察每天整合與 35 天才合併的差距是變大還是變小，並解釋原因。
3. 延伸模擬二，加入第三個 PR C（與 A、B 都不衝突），並實作「批次測試」：先一次測試 main ＋ A ＋ B ＋ C，失敗時再逐一找出造成失敗的 PR。比較批次與逐一測試各要跑幾次 CI。
4. 把 Harbor「把折扣計算引擎換成新實作」的需求，依 branch by abstraction 寫成 5 個 PR 的計畫。每個 PR 寫出標題、改了什麼、合併後 main 的行為是否改變，以及如何 revert。
5. 找一個你最近寫的 commit，依 19.9 的格式重寫它的 message：一行摘要、為什麼要改、考慮過什麼。再請一位同事（或 AI）只讀 message 不看 diff，說出這個變更的目的，看是否和你的意圖一致。
6. 為你的團隊設計一份給 AI coding agent 的 Git 操作規則：列出允許的指令、禁止的指令、遇到 dirty worktree 或 merge conflict 時應該怎麼停下來回報，以及 PR 大小的上限與例外。

## 本章重點整理

- Version control 解決歷史、協作與回復三件事；它的價值隨程式壽命與參與人數增加而增加。
- Git 的 commit 是整個專案的快照加上 parent 指標，branch 只是可移動的標籤；開分支很便宜，合併的成本取決於兩邊分開後累積的變更。
- 分散式 VCS 不代表沒有中心；組織仍需要一個中央的 source of truth，並讓 production 上的每個版本能追溯到一個 commit。
- 所有會影響 production 的東西（程式碼、設定、schema、基礎設施、alert）都應該進 VCS 並經過 review。
- 整合距離越長，單次合併的衝突大約以分支壽命的平方成長；語意衝突更只有在變更真的放在一起時才會被測試抓到。
- 長期 dev branch 把風險往後推並集中爆發；release branch 可以接受，但要短命，且修補先進 main 再 cherry-pick。
- Trunk-based development 的核心是高頻整合，依賴快速 CI、快速 review、小變更能力與「壞了先 revert」的文化。
- Feature flag、branch by abstraction 與未接線的新程式，讓團隊可以每天整合、等準備好再發布。
- Feature flag 是有到期日的負債：要有 owner、刪除日期，名稱絕不重用。
- Monorepo 與 polyrepo 各有代價；原書認為 One Version rule 比 repo 形狀更重要。
- One Version rule 要求開發者不需要選擇依賴哪個版本，避免多版本維護與 diamond dependency。
- 好的 commit 只做一件事、自成一體、機械與語意變更分開、message 說明為什麼；這讓 bisect 與 revert 精準有效。
- 不要改寫共享分支的歷史；merge、squash、rebase 的選擇是團隊約定，但都要求 PR 本身小而單一。
- Merge queue 確保合進 main 的每個狀態都真的被測試過，防止兩個各自綠燈的 PR 合起來變紅燈。
- AI agent 讓變更產生得更快，因此更需要小批次、權限邊界（獨立 worktree、禁止 force push）與 merge queue。

## 延伸問答

> [!question]- Q1. 開分支在 Git 裡幾乎不花成本，為什麼還說長期分支很貴？
> 因為成本不在「開」，而在「合」。Git 的 branch 只是一個指向 commit 的標籤，建立它只需要寫入幾十個位元組；但分支存在的每一天，它和 main 都在各自累積對方看不見的變更。合併時，這些差異要一次被比較、被解決。
>
> 衝突數量大約和「分支改了多少」乘上「main 同期改了多少」成正比，兩者都隨時間增加，所以單次合併的衝突大致隨分支壽命的平方成長。更麻煩的是語意衝突：Git 只能看到同一段文字被兩邊修改，看不到「一邊改名、另一邊新增舊名稱的呼叫」這種邏輯錯誤，它們只有在變更合在一起後跑測試才會出現。分支活越久，這些問題被發現得越晚，也越難追溯到原因。

> [!question]- Q2. 產品經理說：「這個功能還要三週才能給使用者看，所以一定要開長期分支。」你會怎麼回應？
> 我會先把「整合」和「發布」分開來談。使用者三週後才能看到，是發布的需求；程式碼三週後才進 main，是整合的選擇，兩者不必綁在一起。我們可以把新功能放在預設關閉的 feature flag 後面，每天把小變更合進 main，讓它和其他團隊的變更持續一起測試，三週後再打開 flag，甚至先對內部員工或 1% 使用者開放。
>
> 如果功能是替換一個深層元件，就用 branch by abstraction：先加抽象層、再在 main 上逐步寫新實作、最後切換。我也會說明這樣做對產品的好處：三週後的上線只是一個設定變更，出問題可以在幾秒內關閉 flag，而不是像長期分支那樣，上線即是一次大合併，出事時很難撤回。代價是要管理 flag 的生命週期，功能全開後要立即刪除舊路徑。

> [!question]- Q3. 計算題：從已知良好的版本到已知壞掉的版本之間有 500 個 commit，用 git bisect 大約要測試幾次？如果這 500 個 commit 中有 50 個無法單獨建置，會發生什麼事？
> Bisect 是二分搜尋，每次測試把候選範圍減半，所需次數大約是 log₂ 500，約 9 次（2⁹ = 512）。這是理想情況：每個被挑中的 commit 都能建置、能執行重現腳本，並且能明確判斷好或壞。
>
> 如果有 50 個 commit 無法單獨建置，被挑到時你只能用 `git bisect skip` 跳過，bisect 要改挑附近的 commit，步數會增加；更糟的是，如果問題恰好在一串無法建置的 commit 之間，bisect 最後只能告訴你「問題在這幾個 commit 中的某一個」，你得手動分析。這說明了為什麼「每個 commit 都要自成一體、能通過測試」不只是美觀要求，而是讓除錯工具有效的前提。如果團隊使用 squash merge，main 上的每個 commit 對應一個通過 CI 的 PR，這個問題會小很多。

> [!question]- Q4. Monorepo 和 polyrepo，哪一個比較好？
> 這題沒有通用答案，比較好的回答是先說清楚各自的代價，再說選擇依據。Monorepo 讓跨專案變更可以在一個 commit 中原子性完成，天然傾向所有人使用同一個版本，也容易搜尋所有使用者；代價是需要能處理大規模的 build 系統、只跑受影響測試的 CI、細緻的 code owners 與權限機制。沒有這些工具，monorepo 會變成一個又慢又容易被改壞的 repo。
>
> Polyrepo 的 repo 邊界就是天然的權限與發布邊界，標準工具就能用；代價是共用函式庫容易出現多版本並存，跨 repo 的變更要協調多次 PR 與發布順序。原書的立場是 One Version rule 比 repo 形狀更重要：如果在 polyrepo 中能做到共用元件只有一個版本、更新能自動推送到所有使用者，就拿到了 monorepo 最主要的好處。所以我會先評估組織的多版本問題有多嚴重、工具投資的能力有多少，再決定。

> [!question]- Q5. 兩個 PR 都通過了 CI，合併後 main 卻壞了，這是怎麼發生的？要怎麼預防？
> 這是語意衝突加上「測試的版本不是合併後的版本」。每個 PR 的 CI 測試的是「該 PR ＋ 某個時間點的 main」，兩個 PR 平行開發、平行測試，沒有人測過「main ＋ A ＋ B」。如果 A 把一個函式改名並更新了既有呼叫端，B 新增了對舊名稱的呼叫，兩者沒有改到同一行，Git 會順利合併，但合併結果無法運作。
>
> 預防的方法有幾層。小團隊可以要求合併前先 rebase 到最新的 main 並重跑 CI，但 PR 一多就會變成賽跑。較完整的做法是 merge queue：每個 PR 都對「main ＋ 排在它前面的所有 PR」重新測試，通過才合併。另外，函式改名這類變更本身也可以更安全，例如先新增新名稱、保留舊名稱作為轉接一段時間，等所有呼叫端遷移完再刪除（expand / contract），這樣即使有人新增舊名稱的呼叫，也不會立刻壞掉。

> [!question]- Q6. 你是 Harbor 的 SRE 志明。週五下午發現 production 的折價券金額錯誤，最近一次部署包含一個巨大的 merge commit。你會怎麼處理？之後要推動什麼改變？
> 當下的第一優先是止血，而不是找到完美的修法。我會先看有沒有不需要 revert 程式碼的止血手段：例如有沒有 flag 可以關閉折價券疊加、能不能把 checkout 部署回上一個版本的 artifact（如果上一版沒有相依的資料庫變更）。如果這個功能沒有 flag，而 merge commit 又混合了其他團隊的修正，直接 revert 可能會帶來新的問題，這時要和美華、相關 code owner 一起評估：是部署回舊 artifact、revert 整個 merge，還是針對折價券的十幾行做最小的 roll forward 修正。這個判斷要考慮資料庫 schema 是否已經改變，以及其他團隊的修正是否已經被使用者依賴。
>
> 事後在 postmortem 中，我會把「無法精準撤回」列為重要的 contributing factor，而不只是那個計算 bug。行動項目包括：新功能必須放在 release flag 後面；分支超過三天未合併要提醒並說明；採用 squash merge 與一個 PR 一件事的規則；部署系統能一鍵回到上一個 artifact。目標是讓下一次事故的止血手段是「關掉 flag」或「回到上一版」，而不是在壓力下修到晚上十點。

> [!question]- Q7. 為什麼原書說 One Version rule 很重要？允許團隊自己選版本不是比較有彈性嗎？
> 允許選版本在短期內確實有彈性：一個團隊不想升級，就可以留在舊版本，不會被別人的變更打擾。但這個彈性的成本會隨時間和規模累積，而且由別人承擔。每多一個版本，安全修補就要多做一次；函式庫作者無法知道一個行為改變會影響誰，因為舊版本的使用者暫時看不到；等到舊版本的使用者某天必須升級時，他們要一次跨越很多變更，這就是第 4 章講的「越晚升級越貴」。
>
> 多版本還會造成 diamond dependency：兩個元件分別依賴同一個函式庫的不同版本，放進同一個程式時無法共存（第 20 章）。One Version rule 把這些成本變成每天一點點的小成本：函式庫一改，所有使用者立刻知道是否受影響，問題在變更剛發生、作者還記得時就被處理。它需要配套才能運作，例如能在函式庫變更時跑所有使用者的測試、能自動化地更新所有呼叫端；沒有這些配套，硬推 One Version 會讓函式庫作者寸步難行。

> [!question]- Q8. AI 情境：你的團隊讓 coding agent 處理一張「修正折價券計算錯誤」的工單，agent 送出了一個 2,500 行的 PR，CI 全綠。你會直接核准嗎？要怎麼調整流程？
> 不會直接核准。CI 全綠只代表現有測試沒有失敗，不代表變更的範圍合理，也不代表 reviewer 有能力在合理時間內理解 2,500 行。我會先看 diff 的組成：通常這種 PR 會混合真正的 bug 修正、順手的重構、格式化，甚至依賴更新或測試的刪改。我會要求把它拆開：一個只包含 bug 修正與對應測試的小 PR，其他的重構與格式化另外送，或者乾脆不要。特別要檢查有沒有測試被刪除、被跳過或被放寬，因為那是讓 CI 變綠最便宜的方式。
>
> 流程上，我會在 agent 的任務說明中加入明確的範圍限制：一張工單一個 PR、只改與工單相關的檔案、行為變更與機械變更分開、超過一定行數要先停下來提出切分計畫。CI 也可以加上自動檢查，例如 PR 同時觸及多個 code owner 範圍或改動測試檔案的斷言時，要求額外的人工 review。最後，評估 agent 的指標應該是 revert 率與後續修正次數，而不是 PR 數量或行數，避免鼓勵大而雜的變更。

## 延伸閱讀

- [Software Engineering at Google](https://abseil.io/resources/swe-book)：第 16 章〈Version Control and Branch Management〉討論 source of truth、dev branch 的問題、monorepo 與 One Version rule。
- [Software Engineering at Google — Continuous Integration](https://abseil.io/resources/swe-book/html/ch23.html)：從 CI 的角度看 presubmit、主幹的可建置性，以及為什麼要讓變更盡早相遇。
- [DORA](https://dora.dev/)：DORA 研究中關於 trunk-based development 等技術能力，以及它們和軟體交付表現的關係。
- [GitHub — Review AI-generated code](https://docs.github.com/copilot/tutorials/review-ai-generated-code)：審查 AI 產生的變更時要注意的事項，可搭配 19.13 的 guardrails 閱讀。
