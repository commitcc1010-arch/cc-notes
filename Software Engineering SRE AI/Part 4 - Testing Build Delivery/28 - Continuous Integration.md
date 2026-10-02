---
chapter: 28
title: Continuous Integration：把錯誤發現在最便宜的位置
part: 4
---

# 第 28 章　Continuous Integration：把錯誤發現在最便宜的位置

> [!abstract] 本章地圖
> **核心問題**：當幾十個人（以及越來越多 AI agent）每天對同一份程式碼提交上百個變更時，要怎麼讓主線一直保持可用，並且在錯誤造成傷害之前、用最低的成本把它找出來？
>
> **你會學到**：
> - 說清楚 CI 是一種團隊實踐，而不只是「有一台機器在跑測試」
> - 依時間預算與信號品質，把檢查分配到本機、presubmit、postsubmit 與 release 各層
> - 用依賴圖做 test selection，並用安全網防止漏測
> - 理解 merge queue 如何防止「各自綠燈、合起來紅燈」，以及批次大小的取捨
> - 在主線壞掉時優先 rollback，並用二分法找出 culprit
> - 估算 CI 的人力與運算成本，把 CI 當成一個有 SLO 的服務經營
> - 設計能驗證 AI 產生變更的 CI 規則，防止 agent 以削弱測試的方式「讓 CI 變綠」
>
> **前置知識**：第 19 章（trunk-based development、merge queue 入門）、第 22 章與第 26 章（測試組合、flaky test）、第 27 章（依賴圖與 build cache）
>
> **對應原書**：SWE 第 23 章〈Continuous Integration〉

## 28.1 故事：紅了一整個週末的主線

週一早上九點，Harbor seller 團隊的阿凱打開電腦，發現自己週五下午送出的 PR 測試失敗了。錯誤來自 invoice 服務的測試，而阿凱根本沒碰 invoice。按了「重新執行」，又失敗。往上翻 Slack，才發現主線（main）從週五晚上七點開始就是紅的，到現在已經六十多個小時。

這段時間裡，有八個 PR 被合併進主線。有的人以為紅燈是 flaky test，直接用管理員權限合併；有的人看到紅燈，送了一個「修正」PR，結果又引入另一個錯誤。等 tech lead 美華開始調查時，已經沒有人能確定最初是哪一個變更弄壞的，也不知道後來的八個變更裡，有哪些本身也有問題。

最後查出來的原因很典型。週五下午，checkout 團隊改了共用的 `pricing` 函式庫，把折扣的四捨五入從「每項商品各自進位」改成「整筆訂單一次進位」。他們的 PR 只跑了 `pricing` 自己的單元測試，全部通過；但 payments 團隊的 invoice 服務依賴舊的進位方式產生發票金額，合併後 invoice 的測試開始失敗。之所以沒在 PR 階段被抓到，是因為 Harbor 的 presubmit 只跑「被修改的目錄」裡的測試；而全部測試要跑 48 分鐘，只有合併後才會跑一次。

產品經理 Lisa 原本預計週一上線的新功能延到了週三。工程經理 Kevin 在檢討會上算了一筆帳：週一早上有二十多位工程師的 PR 被紅燈卡住，每個人平均花了一個多小時搞清楚「是不是我的錯」。美華則問了一個更根本的問題：「我們有 CI，每個 PR 都有綠勾勾，為什麼它沒有保護到我們？」

這一章要回答美華的問題。答案是：CI 不是一台跑測試的機器，而是一整套「頻繁整合、快速回饋、壞了立刻修」的工作方式；工具只是讓這套方式可行的手段。

## 28.2 CI 是什麼：一種實踐，不只是工具

### 定義

**Continuous Integration**（持續整合，CI）這個詞在 1990 年代末的 Extreme Programming 中被推廣，Martin Fowler 的經典文章把它描述為：團隊成員頻繁地把工作整合進共享的主線，通常每人每天至少一次，每次整合都由自動化的 build 與測試驗證，以便盡快發現整合錯誤。

注意這個定義的重心在「**整合**」，而不是「自動化測試」。CI 要解決的問題是：每個人的程式碼單獨看都沒問題，但和別人的放在一起就壞了。這種錯誤只有在整合的那一刻才會出現，所以整合越頻繁、每次整合的變更越小，錯誤就越早被發現，也越容易找到原因。

《Software Engineering at Google》把定義延伸到更大的尺度：CI 是對整個複雜、快速演進的生態系**持續地組裝與測試**。在一個大型 codebase 中，你的變更不只要和同事的變更整合，還要和你依賴的函式庫、依賴你的服務、外部套件的新版本、設定與基礎設施的變化整合。CI 的範圍是「所有會一起運作的東西」，而不只是「我這個 repository」。

### 有工具，不等於有 CI

很多團隊裝了 Jenkins 或 GitHub Actions，就以為自己在做 CI。但下面這些情況，即使有工具，也不算真正的持續整合：

- 功能分支活三週才合併。每個分支的 CI 都是綠的，但它驗證的是「這個分支自己能動」，不是「它和主線上其他人這三週的變更能一起動」（第 19 章討論過長期分支的代價）。
- 主線經常是紅的，而且大家習慣了。紅燈不再代表「有東西壞了、要停下來」，只代表「又是那樣」。
- CI 要跑一個小時，所以大家一天只送一次很大的 PR，或者在本機跑一小部分測試就合併。

所以 CI 至少包含三個互相依賴的承諾：**頻繁地把小變更整合進主線**、**每次整合都自動驗證**、**主線壞了立刻修**。少了任何一個，另外兩個就失去意義。Harbor 的週末事故三個都缺：pricing 的變更雖然小，但驗證範圍不足；驗證要 48 分鐘，只在合併後跑；主線紅了六十小時沒人負責。

### CI 是一種 alerting

原書提出一個很有用的類比：**CI 就是 alerting**。Production 的 alert 告訴你「現在有使用者受到影響」，CI 的失敗告訴你「如果這個變更上線，可能會有使用者受到影響」。兩者面對同樣的問題：false positive 太多（flaky test、基礎設施錯誤），人們會學會忽略它；信號太慢，傷害已經發生；信號不可行動（只有一行 `exit code 1`），收到的人不知道該做什麼。

把 CI 當成 alerting 看，很多設計原則就自然浮現：失敗要可行動、要附上足夠的上下文、要分辨「你的變更壞了」與「CI 自己壞了」、要追蹤 false positive 率。第 34 章談的好 alert 條件，幾乎可以原封不動套用到 CI 上。

## 28.3 為什麼越早發現越便宜

### 錯誤的成本隨距離增加

一個錯誤從被寫下到被發現，中間經過的每一站都讓修復變得更貴。原因不是神祕的「成本放大係數」，而是幾個具體的機制：

- **上下文消失**。寫完程式五分鐘後發現錯誤，你還記得每一行在做什麼；三天後發現，你要重新讀懂自己的程式碼。
- **嫌疑犯變多**。presubmit 失敗時只有一個嫌疑犯，就是這個 PR；postsubmit 失敗時，嫌疑犯是這段時間合併的所有變更；production 出事時，嫌疑犯還包括設定、流量、依賴與基礎設施。
- **影響範圍變大**。presubmit 失敗只影響作者；主線壞了影響所有開發者；production 壞了影響使用者與營收。
- **修復手段變重**。presubmit 只需要改程式重送；主線要 revert；production 要 rollback、事故處理、可能還要資料修復與客戶溝通。

這就是 **shift left**（左移）的意思：把檢查盡量往時間軸的左邊、也就是更早的位置移動（第 6 章介紹過這個概念）。但左移有一個限制：越左邊的位置，能接受的等待時間越短。你不會願意每次存檔都等十分鐘。所以真正的設計問題是：**每一種檢查，放在哪一層最划算？**

### 分層的 feedback

```text
時間預算            層級               跑什麼                               失敗時誰受影響
─────────────────────────────────────────────────────────────────────────────
秒            ① 編輯器 / 本機      formatter、linter、型別、相關單元測試      只有作者
5–15 分鐘     ② presubmit         build、受影響的單元與整合測試、           作者（PR 被擋）
                                 契約測試、安全掃描
                  │ merge queue：在「最新主線 + 這個變更」上驗證
                  ▼
數十分鐘      ③ postsubmit        所有受影響測試、較慢的整合與 E2E、         所有開發者（主線紅燈）
                                 多平台組合；失敗時自動找 culprit
數小時        ④ release 候選      完整 E2E、load test、相容性、合規掃描      發布被延後
持續          ⑤ production 驗證    canary 分析、synthetic probe、SLO         使用者
```

這張圖從上往下讀，每往下一層，時間預算變大、能跑的檢查變多，但失敗時影響的人也變多。設計原則是：**能在上層可靠抓到的錯誤，就不要留到下層**；但不能為了把所有檢查塞到上層，而讓上層慢到大家想繞過它。

第 ① 層是開發者自己的迴圈，第 15 章的 formatter、linter 與 type checker 主要在這裡發揮作用。第 ② 層與第 ③ 層是本章的重點。第 ④ 層與第 ⑤ 層屬於 release 與 delivery，第 29 章會談 canary，第 32 章的 SLO 則是最後一道、也是最貼近使用者的驗證。

## 28.4 Presubmit 與 Postsubmit

### 兩者的分工

**Presubmit**（提交前檢查）是在變更合併進主線**之前**執行的檢查，失敗就不能合併。**Postsubmit**（提交後檢查）是變更合併**之後**，在主線上持續執行的檢查，失敗時主線已經包含了問題，要盡快修復。

兩者的取捨很清楚：presubmit 能完全阻止壞變更進入主線，但每一分鐘都是作者的等待時間，而且每個 PR 都要付一次成本；postsubmit 不擋人，可以跑更多、更慢的測試，也可以把多個變更合在一起跑以節省資源，但失敗時錯誤已經進了主線，影響所有人。

| 面向 | Presubmit | Postsubmit |
|---|---|---|
| 執行時機 | 合併前，每個 PR | 合併後，主線上（可能每個 commit 或批次） |
| 目標 | 擋下高機率、可歸因於這個變更的錯誤 | 抓到 presubmit 範圍外的錯誤，確認主線健康 |
| 時間預算 | 通常 5–15 分鐘 | 數十分鐘到數小時 |
| 適合的測試 | 快、穩定、hermetic、與變更相關 | 慢、範圍大、跨服務、多平台組合 |
| 失敗時 | 作者自己修 | 找出 culprit、revert、通知作者 |
| 可以容忍 flaky 嗎 | 幾乎不行，會擋住無辜的人 | 稍可容忍，但需要自動重試與隔離 |

### Google 的做法

原書以 Google 的 **TAP**（Test Automation Platform）為例說明這個分工。在 Google 的 monorepo 中，各團隊為 presubmit 挑出一個快速、可靠的子集（通常是單元測試）；原書提到，通過 presubmit 的變更有很高的機率（95% 以上）也會通過其餘測試。變更合併後，TAP 依依賴圖非同步地執行所有可能受影響的測試，包括較大、較慢的測試；由於變更量極大，它會把相關的變更合成一批一起測試。批次失敗時，TAP 會自動把它拆成個別變更重跑，找出是哪一個造成的。每個團隊都有一位 **build cop**（主線看守者），負責讓自己專案的測試保持通過，不論是誰弄壞的；收到失敗通知時，build cop 要放下手邊的事，讓主線回到綠色。

這個設計反映了一個重要判斷：**presubmit 不需要、也不可能抓到所有錯誤**。它的目標是用最少的等待抓到大部分錯誤；剩下的由 postsubmit 抓到，再靠快速的 culprit 找尋與 rollback 把傷害控制在很短的時間內。只要主線壞掉的時間很短，postsubmit 抓到錯誤的代價就可以接受。

### 什麼該放 presubmit

Harbor 在週末事故後重新整理了 presubmit 的規則，依據是三個問題：

1. **它抓到的錯誤，常見嗎？嚴重嗎？** 編譯錯誤、型別錯誤、受影響模組的單元測試，幾乎每天都會抓到東西，一定放 presubmit。付款相關的契約測試抓到的錯誤不常見但非常嚴重，也放 presubmit。
2. **它夠快、夠穩定嗎？** 一個要跑 10 分鐘、每 50 次失敗一次的 E2E 測試，放在 presubmit 會讓大量無辜的 PR 被擋，應該移到 postsubmit，並同時修它的 flakiness（第 26 章）。
3. **它的失敗能歸因到這個變更嗎？** 依賴外部 staging 環境的測試，失敗時常常不是 PR 的錯，不適合擋人。

依此原則，pricing 那次變更的問題，答案是 invoice 的測試應該出現在 presubmit：它快、穩定，而且 invoice 依賴 pricing。問題不在於 presubmit 的規則，而在於 Harbor 用「被修改的目錄」來決定要跑什麼，而不是用依賴圖。這就是下一個主題。

## 28.5 Fast feedback：時間預算與加速手段

### 為什麼速度是 CI 的功能，不是附加品

CI 的速度直接改變工程師的行為。Extreme Programming 有一條實踐叫「十分鐘 build」（Ten-Minute Build），理由是十分鐘大約是一個人願意等、又不會切換到其他工作的上限。超過這個時間，人會開始做別的事，等 CI 結果回來時，已經失去了上下文；再更慢，人會開始把多個修改塞進同一個 PR 以減少等待次數，PR 變大、review 變難、出錯時更難找原因（第 16、19 章）。

所以 presubmit 的時間不只是「工程師等了多久」，它還決定了 PR 的大小、整合的頻率，以及大家是否願意遵守規則。Harbor 的 48 分鐘全量測試，就是讓大家改成只跑「修改的目錄」的原因：規則被設計成可以繞過，因為守規則太痛苦。

### 讓 CI 變快的手段

依效果與成本，常見的手段如下：

- **只跑受影響的部分**：用依賴圖做 test selection（28.6 節），通常是效果最大的一項。
- **快取**：第 27 章的 build cache 與 remote cache。沒改的 target 不重建，沒變的測試結果也可以快取：如果一個測試的所有輸入（程式碼、依賴、資料）都沒變，它的結果就不會變，這要求測試是 hermetic 的。
- **平行與分片**：把測試分散到多台機器同時執行（sharding，分片）。總時間取決於最慢的那一片，所以要依歷史執行時間平衡分片，並把特別慢的測試拆小。
- **Fail fast**（快速失敗）：先跑最快、最常失敗的檢查（編譯、lint、型別），失敗就立刻回報，不必等所有測試跑完。
- **取消過時的執行**：作者在 CI 還沒跑完時又推了新 commit，舊的執行就該取消，不要浪費資源。
- **預熱的執行環境**：每次 CI 都從零下載 toolchain、安裝依賴，常常比測試本身還慢。預先建好的 builder 映像與依賴 mirror 能省下大量時間。

### 信號品質和速度一樣重要

快但不可信的 CI 和慢的 CI 一樣糟。CI 失敗時，作者需要在一分鐘內回答「這是我的錯嗎？我該做什麼？」好的失敗回報包含：哪個測試失敗、失敗的 assertion 與實際值、這個測試最近的 flaky 紀錄、在本機重現的指令，以及這個失敗是「測試失敗」還是「CI 基礎設施錯誤」（例如機器斷線、下載逾時）。

最後一項特別重要。如果基礎設施錯誤和測試失敗看起來一樣，作者會學會「紅了就重跑」，真正的失敗也會被重跑掉。Harbor 把 CI 結果分成三種顏色：綠（通過）、紅（測試失敗，作者要處理）、紫（基礎設施錯誤，自動重試並通知 CI 平台的 owner）。

## 28.6 Test selection：跑對的測試，而不是全部的測試

### 用依賴圖選測試

**Test selection**（測試選擇）是根據變更內容，決定這次要跑哪些測試。最直接也最可靠的方法是用第 27 章的依賴圖：找出所有被修改的 target，沿著反向依賴往上找所有直接或間接依賴它們的 target，再執行這些 target 的測試。

```text
           改了 //lib/pricing
                  │ 反向依賴（誰依賴我）
        ┌─────────┴──────────┐
        ▼                    ▼
 //svc/checkout         //svc/invoice      ← 週末事故中漏跑的就是這裡
        │
        ▼
    //web/app
                         //svc/search      ← 與 pricing 無關，不用跑

要跑：pricing_test、checkout_test、invoice_test、web 的相關測試
不用跑：search_test
```

這張圖說明了 Harbor「只跑修改的目錄」錯在哪裡：它只跑了最上面那個節點。依賴圖的方法會沿著箭頭找到 checkout、invoice 與 web，同時排除完全不相干的 search。在依賴圖精確的系統中（例如 Bazel 可以用 `rdeps` 查詢反向依賴），這種選擇既完整又精準：大部分變更只影響 codebase 的一小部分，所以大部分 PR 只需要跑一小部分的測試。

### 依賴圖看不到的東西

依賴圖只能看到宣告的依賴。以下幾種依賴常常不在圖上，是 test selection 漏測的主要來源：

- **執行期的動態依賴**：以反射或 plugin 機制載入的模組、用字串組出來的 import。
- **設定與資料檔**：一個 YAML 設定被三個服務讀取，但沒有被宣告為它們的輸入。
- **跨服務的網路依賴**：checkout 透過 HTTP 呼叫 inventory，兩者在 build 圖上沒有任何關係，但 inventory 的 API 改了，checkout 就會壞。這是第 25 章契約測試要處理的問題。
- **基礎設施與共用環境**：資料庫 schema、訊息佇列的設定。

因此 test selection 一定要有**安全網**：

1. **Always-run 清單**：少數高價值、快速的測試（例如付款契約測試）每次都跑，不依賴選擇邏輯。
2. **Postsubmit 跑得更廣**：presubmit 選擇性地跑，postsubmit 跑所有受影響的測試，包含 presubmit 排除的慢測試。
3. **定期全量執行**：每天或每幾小時對主線跑一次全部測試，抓出選擇邏輯漏掉的東西。每次全量抓到「選擇邏輯該選卻沒選」的失敗，都要回頭修補依賴宣告。
4. **不確定時擴大範圍**：修改了 build 設定、共用的 CI 設定、toolchain 版本時，直接跑全部測試。

### 預測式選擇

當 codebase 大到即使「受影響的測試」也太多時，有些組織會再加一層**預測式 test selection**：用歷史資料（哪些檔案的修改過去常讓哪些測試失敗）訓練模型，在受影響的測試中優先或只跑最可能失敗的那些。Meta 與 Google 都發表過這類方法的研究。它能進一步縮短 presubmit，但本質上是用「偶爾漏掉」換「平均更快」，所以只適合在有強大 postsubmit 與快速 culprit 找尋作為後盾時使用，而且要持續量測它漏掉了多少真正的失敗。

## 28.7 Merge queue：讓主線永遠是綠的

### 各自綠燈，合起來紅燈

就算 presubmit 跑對了所有測試，還有一個漏洞。假設阿凱和 search 團隊的一位同事同時開了 PR：

- 阿凱的 PR 把函式 `apply_discount(order)` 改名為 `apply_discounts(order)`，並更新了所有呼叫的地方。
- 同事的 PR 在新的 `gift_card.py` 裡呼叫了 `apply_discount(order)`。

兩個 PR 都基於早上九點的主線，各自的 presubmit 都通過。阿凱先合併；同事的 PR 隨後合併，此時主線上已經沒有 `apply_discount` 了，主線立刻壞掉。兩個變更沒有任何文字上的衝突，Git 也不會提醒你，這叫**語意衝突**（semantic conflict）。PR 的 presubmit 驗證的是「舊主線加上這個變更」，而不是「合併當下的主線加上這個變更」。

這個問題在團隊小、合併不頻繁時很少發生；當每天有上百次合併，兩個 PR 的 presubmit 之間主線可能已經變了幾十次，發生機率就高到每週都會遇到。

### Merge queue 怎麼運作

**Merge queue**（合併佇列）的解法是：PR 通過 review 與 presubmit 之後不直接合併，而是進入一個佇列；佇列依序把每個 PR 放在「最新的主線加上排在它前面的所有 PR」之上再驗證一次，通過才真正合併。這實現了一個早期由 Rust 專案推廣的原則，Graydon Hoare 稱之為「Not Rocket Science Rule」：**自動維護一個永遠通過所有測試的 repository**。第 19 章介紹過 merge queue 的基本概念；這裡說明它的內部機制與取捨。

```text
主線 M ── 佇列： [A] [B] [C] [D]

逐一驗證（batch = 1）：
  test(M+A) ✔ 合併 → test(M+A+B) ✔ 合併 → test(M+A+B+C) ✘ 踢出 C → test(M+A+B+D) ✔ 合併
  四次 CI，依序執行；佇列吞吐量 = 1 個 PR / 每次 CI 時間

批次驗證（batch = 4）：
  test(M+A+B+C+D) ✘
    ├─ test(M+A+B) ✔        ┐ 同時測兩個前綴
    └─ test(M+A+B+C) ✘      ┘ → 問題在 C，踢出 C
  test(M+A+B+D) ✔ → 合併 A、B、D
  失敗率低時，大部分批次一次就通過，四個 PR 只花一次 CI
```

逐一驗證最簡單也最安全，但佇列的吞吐量受限於 CI 時間：每次 CI 12 分鐘，一小時最多合併 5 個 PR，對四十多人的公司會變成新的瓶頸。實務上的 merge queue（例如 GitHub 的 merge queue、GitLab 的 merge trains，以及 OpenStack 社群的 Zuul）用兩種方法提高吞吐量：

- **Speculative execution**（推測執行）：同時驗證 `M+A`、`M+A+B`、`M+A+B+C`，假設前面的都會通過。如果 A 失敗，後面所有的推測都要作廢重跑。這用更多運算換更低的等待時間。
- **Batching**（批次）：把多個 PR 合成一批驗證，通過就一起合併；失敗再切半找出問題 PR。失敗率低時能大量節省運算；失敗率高時，切半重測的成本會吃掉節省的部分。28.10 節的程式會量化這個取捨。

### Merge queue 不能取代什麼

Merge queue 驗證的是「合併後的主線能通過 presubmit 的測試」，所以 presubmit 範圍外的問題（慢的 E2E、跨服務的整合）它一樣抓不到，仍然需要 postsubmit。另外，merge queue 讓 presubmit 實際上跑兩次（PR 上一次、佇列裡一次），CI 成本會增加。對變更量不大的團隊，「合併前要求分支與主線同步並重跑」可能就足夠；merge queue 的價值隨合併頻率而增加。

## 28.8 主線壞了怎麼辦：rollback 優先

### 為什麼先 revert

即使有好的 presubmit 與 merge queue，主線還是會壞：postsubmit 的慢測試、平台組合、外部依賴的更新。壞了之後最重要的指標只有一個：**多久回到綠色**。主線紅燈的每一分鐘，所有人的 PR 都無法判斷自己的失敗是不是自己造成的，新的錯誤會被舊的紅燈掩蓋，就像 Harbor 的週末。

最快回到綠色的方法幾乎永遠是 **revert**（撤回）那個造成問題的變更，而不是修好它。理由是：revert 是一個已知安全的操作，它讓主線回到一個測試過的狀態；而「往前修」是一個新的、未經驗證的變更，在壓力下寫的修正更容易出錯，Harbor 週末那個「修正」PR 就引入了第二個錯誤。Revert 不是懲罰，也不代表變更不好；作者可以在不受時間壓力的情況下修好問題，再重新送出。

原書描述的 Google 做法把這件事講得很明確：rollback 是 build cop 最有效的工具，通常也是修好 build 最快、最安全的路；往前修則被視為風險較高的選項。TAP 在高度確信某個變更就是 culprit 時，甚至會自動把它 rollback。這需要第 9 章講的心理安全：被 revert 不是丟臉的事，而是系統正常運作。

### Culprit finding

要 revert，先要知道是哪個變更。如果 postsubmit 每個 commit 都跑，第一個失敗的 commit 就是 culprit（罪魁禍首）。但 postsubmit 為了節省資源常常是批次執行的：一次測試涵蓋了最近的十幾個 commit，失敗時要在其中找出是哪一個。

方法是**二分搜尋**：在這批 commit 的中點跑一次測試，通過代表問題在後半，失敗代表在前半，重複直到找到第一個失敗的 commit。8 個 commit 只需要 3 次，64 個 commit 只需要 6 次，這就是 `git bisect` 的原理，也是自動化 culprit finding 常用的方法（原書提到 TAP 會把失敗的批次拆成個別變更重跑，開發者也可以用工具在批次中做二分搜尋）。二分法有一個前提：測試結果必須穩定。如果測試是 flaky 的，二分法會指向錯的 commit，這是第 26 章強調 flaky 必須修的又一個理由。

### Harbor 的主線健康規則

週末事故後，Harbor 寫下了下面這份規則，並放在 repository 的 `CONTRIBUTING.md` 中：

```text
Harbor 主線健康規則（v1）

1. 主線紅燈是最高優先的工程問題。發現者在 #main-health 頻道宣告，
   當週的 build cop（輪值，每週一人）負責到它變綠為止。
2. 先 revert，再修。若 culprit 明確，build cop 可直接 revert，不需等待作者；
   目標是紅燈後 30 分鐘內回到綠色。
3. 紅燈期間，merge queue 暫停合併，除了 revert 與經 build cop 確認的修正。
4. 失敗若是 flaky test，build cop 將其隔離（quarantine）並開 ticket 給 owner，
   不得以「重跑到綠」處理（第 26 章）。
5. 自動化：postsubmit 失敗時自動執行 culprit finding，對 culprit 開出 revert PR
   並通知作者；revert PR 仍經 merge queue 驗證。
6. 每次紅燈超過 2 小時，進行簡短檢討：為什麼 presubmit 沒抓到？
```

第 6 條是讓系統持續改善的關鍵。每一次 postsubmit 抓到的錯誤，都是一個「為什麼不能更早抓到」的問題：是 test selection 漏了依賴？是測試太慢被放到 postsubmit？還是這種錯誤本來就只能在 postsubmit 抓到？答案會變成 presubmit 規則或依賴宣告的改進。

## 28.9 CI 的成本，以及把 CI 當成服務

### 成本有兩種

CI 的成本常被只算成「CI 機器的帳單」，但對大多數組織，更大的成本是人的時間。用 Harbor 的數字粗估：

```text
人的等待成本
  30 位工程師 × 每人每天 4 次 CI × 每次等 30 分鐘 = 3,600 分鐘 / 天 = 60 小時 / 天
  就算只有三分之一是「真的卡住、無法做別的事」：約 20 小時 / 天 ≈ 2.5 位工程師的全職時間

運算成本
  每天 120 次 CI × 每次 20 台機器 × 30 分鐘 = 72,000 機器分鐘 = 1,200 機器小時 / 天
```

這筆帳說明了兩件事。第一，讓 presubmit 從 30 分鐘降到 10 分鐘，省下的人力成本通常遠大於多花的機器成本，所以花錢買更多平行度與快取常常是划算的。第二，運算成本會隨變更量線性成長，當變更量大幅增加（例如 AI agent 開始大量開 PR，28.12 節），不加控制的 CI 帳單也會跟著暴增。

還有一些難以量化但真實的成本：flaky test 造成的重跑與誤判、紅燈期間的互相干擾、因為 CI 慢而變大的 PR、以及工程師對 CI 失去信任後繞過它所帶來的風險。

### 用 SLO 經營 CI

CI 平台是公司內部每個工程師每天都依賴的服務，它應該像 production 服務一樣有 owner、有 SLO、有容量規劃。Harbor 的 platform 團隊為 CI 訂了以下指標：

| 指標 | 定義 | Harbor 目標 |
|---|---|---|
| Time to first signal | PR 推送後到第一個失敗或全部通過的時間（p90） | ≤ 12 分鐘 |
| Queue time | 工作等待可用 runner 的時間（p90） | ≤ 1 分鐘 |
| Infra failure rate | 非測試原因（runner、網路、下載）造成的失敗比例 | ≤ 0.5% |
| Flaky rate | 同一 commit 重跑結果不同的測試執行比例 | 追蹤趨勢，逐月下降 |
| Main red time | 主線處於紅燈的時間比例 | ≤ 2% |
| Escaped defects | presubmit 通過、postsubmit 或之後才發現的錯誤數 | 每月檢討來源 |

最後一項是 CI「有效性」的指標：presubmit 再快，如果漏掉的錯誤越來越多，它就沒有在保護主線。速度指標與有效性指標要一起看，否則很容易為了變快而把測試一個個移出 presubmit。

### CI 是供應鏈的一部分

CI 系統可以讀取原始碼、執行任意程式、存取部署憑證，第 27 章也說過它是產生並簽章 artifact 的地方。所以 CI 的安全性就是供應鏈的安全性。幾條基本規則：

- **不受信任的程式碼拿不到秘密**。來自外部 fork 的 PR、或任何尚未經人類 review 的程式碼，在 presubmit 中執行時不應能讀到部署憑證或 production 秘密。
- **第三方 CI 元件固定版本**。CI 設定中引用的第三方 action 或 plugin，應以 commit SHA 或 digest 固定，而不是浮動的 tag，理由和第 27 章固定 base image 相同。
- **最小權限的 token**。CI 執行用的 token 預設唯讀，只在需要的步驟（例如推送 artifact）才取得寫入權限。
- **隔離的 runner**。每次執行使用乾淨、用完即丟的執行環境，避免一次執行留下的狀態影響下一次，這也是 SLSA Build L3 的要求之一。
- **CI 設定本身受保護**。修改 CI 設定、必要檢查清單、branch protection 的變更，要有指定 owner 的 review，否則任何人都能用一個 PR 把檢查關掉。

## 28.10 動手寫：test selection、culprit finding 與 merge queue 模擬

第一段程式用依賴圖選出受影響的測試，並模擬 postsubmit 批次失敗時用二分法找 culprit。

```python
from collections import deque

# target -> 它直接依賴的 targets（和第 27 章的 build graph 相同概念）
DEPS = {
    "//lib/money":    [],
    "//lib/pricing":  ["//lib/money"],
    "//svc/checkout": ["//lib/pricing"],
    "//svc/invoice":  ["//lib/pricing"],
    "//svc/search":   [],
    "//web/app":      ["//svc/checkout", "//svc/search"],
}
# 測試 -> (被測 target, 平均秒數, 標籤)
TESTS = {
    "money_test":         ("//lib/money", 4, set()),
    "pricing_test":       ("//lib/pricing", 6, set()),
    "checkout_test":      ("//svc/checkout", 40, set()),
    "checkout_contract":  ("//svc/checkout", 90, {"always"}),   # 付款契約：每次都跑
    "invoice_test":       ("//svc/invoice", 30, set()),
    "search_test":        ("//svc/search", 120, set()),
    "web_e2e":            ("//web/app", 600, {"postsubmit"}),   # 太慢，留給 postsubmit
}

rdeps = {t: set() for t in DEPS}
for target, deps in DEPS.items():
    for d in deps:
        rdeps[d].add(target)


def affected(changed):
    seen, queue = set(changed), deque(changed)
    while queue:                                   # 沿反向依賴 BFS
        for consumer in rdeps[queue.popleft()]:
            if consumer not in seen:
                seen.add(consumer)
                queue.append(consumer)
    return seen


def select(changed, stage):
    hit = affected(changed)
    chosen = []
    for name, (target, secs, tags) in TESTS.items():
        if "postsubmit" in tags and stage == "presubmit":
            continue
        if target in hit or "always" in tags:
            chosen.append((name, secs))
    return chosen


full = sum(s for _, s, _ in TESTS.values())
for changed in ({"//svc/search"}, {"//lib/pricing"}):
    for stage in ("presubmit", "postsubmit"):
        chosen = select(changed, stage)
        secs = sum(s for _, s in chosen)
        names = ", ".join(n for n, _ in chosen)
        print(f"{sorted(changed)[0]:<14} {stage:<10} {secs:>4}s / 全部 {full}s  [{names}]")

# ---- Postsubmit 批次失敗時，用二分法找出 culprit ----
batch = ["c101", "c102", "c103", "c104", "c105", "c106", "c107", "c108"]
culprit = "c106"


def passes(prefix):            # 在 main + prefix 這些 commit 上跑測試
    return culprit not in prefix


lo, hi, runs = 0, len(batch), 0     # 不變式：batch[:lo] 通過、batch[:hi] 失敗
while hi - lo > 1:
    mid = (lo + hi) // 2
    runs += 1
    ok = passes(batch[:mid])
    print(f"  測試到 {batch[mid - 1]} 為止：{'綠' if ok else '紅'}")
    lo, hi = (mid, hi) if ok else (lo, mid)
print(f"culprit = {batch[hi - 1]}，額外跑了 {runs} 次（逐一測試需要 {len(batch)} 次）")
```

執行結果：

```text
//svc/search   presubmit   210s / 全部 890s  [checkout_contract, search_test]
//svc/search   postsubmit  810s / 全部 890s  [checkout_contract, search_test, web_e2e]
//lib/pricing  presubmit   166s / 全部 890s  [pricing_test, checkout_test, checkout_contract, invoice_test]
//lib/pricing  postsubmit  766s / 全部 890s  [pricing_test, checkout_test, checkout_contract, invoice_test, web_e2e]
  測試到 c104 為止：綠
  測試到 c106 為止：紅
  測試到 c105 為止：綠
culprit = c106，額外跑了 3 次（逐一測試需要 8 次）
```

逐段解讀：

1. `rdeps` 把依賴圖反過來，`affected` 從被修改的 target 沿反向依賴做廣度優先搜尋，找出所有直接或間接受影響的 target。改 `//lib/pricing` 時，它找到了 checkout、invoice 與 web；週末事故中被漏掉的 `invoice_test` 這次被選進 presubmit。
2. `select` 實作兩個安全網與一個分層規則：`always` 標籤的契約測試不管改了什麼都跑（所以改 search 也會跑 `checkout_contract`）；`postsubmit` 標籤的慢測試在 presubmit 被排除，在 postsubmit 才跑。
3. 改 pricing 的 presubmit 只要 166 秒，而全部測試要 890 秒。這個比例在真實的大型 codebase 中通常更懸殊，因為大部分變更只影響很小一部分的依賴圖。
4. 二分法維持一個不變式：`batch[:lo]` 一定通過、`batch[:hi]` 一定失敗。每次在中點測一次，就把範圍縮小一半，3 次就從 8 個 commit 中找到 c106。真實系統會在找到 culprit 後自動開 revert PR。

第二段程式模擬 merge queue 的批次大小取捨：48 個 PR，各有一定機率會讓測試失敗；批次失敗時切半、兩半平行重測，直到找出失敗的 PR 並踢出佇列。

```python
import random

CI_MINUTES = 12      # 一次 CI 執行的時間


def make_prs(n, fail_rate, seed=7):
    rng = random.Random(seed)
    return [rng.random() < fail_rate for _ in range(n)]   # True = 這個 PR 會讓測試失敗


def run_batch(batch):
    """測試一個 batch；失敗就切半，兩半平行重測。回傳 (合併的 PR 數, CI 次數, 經過幾輪)。"""
    if not any(batch):
        return len(batch), 1, 1
    if len(batch) == 1:
        return 0, 1, 1                             # 找到 culprit，踢出 queue
    half = len(batch) // 2
    m1, r1, d1 = run_batch(batch[:half])
    m2, r2, d2 = run_batch(batch[half:])
    return m1 + m2, 1 + r1 + r2, 1 + max(d1, d2)


def simulate(prs, batch_size):
    merged = runs = rounds = 0
    for i in range(0, len(prs), batch_size):
        m, r, d = run_batch(prs[i:i + batch_size])
        merged, runs, rounds = merged + m, runs + r, rounds + d
    return merged, runs, rounds * CI_MINUTES


for rate in (0.05, 0.25):
    prs = make_prs(48, rate)
    print(f"48 個 PR，其中 {sum(prs)} 個會失敗（失敗率 {rate:.0%}）")
    for size in (1, 4, 8, 16):
        merged, runs, minutes = simulate(prs, size)
        print(f"  batch={size:<2}  合併 {merged:>2}  CI 執行 {runs:>3} 次  "
              f"全部處理完約 {minutes:>3} 分鐘")
```

執行結果：

```text
48 個 PR，其中 2 個會失敗（失敗率 5%）
  batch=1   合併 46  CI 執行  48 次  全部處理完約 576 分鐘
  batch=4   合併 46  CI 執行  20 次  全部處理完約 192 分鐘
  batch=8   合併 46  CI 執行  18 次  全部處理完約 144 分鐘
  batch=16  合併 46  CI 執行  19 次  全部處理完約 132 分鐘
48 個 PR，其中 16 個會失敗（失敗率 25%）
  batch=1   合併 32  CI 執行  48 次  全部處理完約 576 分鐘
  batch=4   合併 32  CI 執行  54 次  全部處理完約 360 分鐘
  batch=8   合併 32  CI 執行  60 次  全部處理完約 288 分鐘
  batch=16  合併 32  CI 執行  63 次  全部處理完約 180 分鐘
```

逐段解讀：

1. `run_batch` 是遞迴的切半搜尋：整批通過就一次合併全部；失敗就切成兩半各自測試，直到單一 PR。`rounds` 用 `1 + max(...)` 計算，因為兩半是平行測試的，經過的時間取決於較深的那一半。
2. 失敗率 5% 時，batch 從 1 變成 8，CI 次數從 48 降到 18，處理時間從 576 分鐘降到 144 分鐘。大部分批次一次就通過，批次幾乎只有好處。
3. 失敗率 25% 時情況反轉：批次越大，**CI 次數越多**（48 → 63），因為幾乎每一批都有失敗的 PR，要付出切半重測的成本。時間仍然變短，是因為重測是平行的，但代價是更多運算。這說明了 batch 大小不是越大越好，最佳值取決於失敗率：失敗率高的時候，與其加大 batch，不如先提高 presubmit 的品質，讓進入佇列的 PR 本來就比較乾淨。
4. 這個模型刻意簡化了幾件事：假設 PR 之間沒有交互作用（真實的語意衝突只有兩個 PR 放在一起才失敗）、沒有模擬推測執行、也沒有 flaky test。加入 flaky 之後，好的 PR 會被誤判踢出，大 batch 的損失更明顯。動手練習第 3 題請你把 flaky 加進去。

把這兩段程式放回真實世界：第一段對應 Bazel 的 `rdeps` 查詢或各種 monorepo 工具的「affected」指令，以及 `git bisect` 與 TAP 的自動 culprit finding；第二段對應 GitHub merge queue、GitLab merge trains 等系統中可設定的批次大小與並行數。

## 28.11 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| 把所有測試放進 presubmit | Presubmit 慢到大家繞過或改送大 PR | Harbor 的 48 分鐘全量測試，讓團隊改成只跑「修改的目錄」 | 依依賴圖選擇；慢測試移到 postsubmit；投資快取與平行度 |
| 激進的 test selection | 漏掉依賴圖看不到的依賴，給出錯誤的綠燈 | 設定檔被三個服務讀取但沒有宣告，改設定只跑了一個服務的測試 | Always-run 清單、postsubmit 跑得更廣、定期全量、不確定時擴大範圍 |
| 主線紅燈時「往前修」 | 在壓力下寫的修正引入新錯誤，紅燈時間拉長 | 週末事故中的「修正」PR 又引入第二個錯誤 | 先 revert 回到已知安全的狀態，再從容修正 |
| 失敗就重跑 | 真正的失敗被重跑掉，flaky 越積越多 | 一個偶發的競態錯誤，在 CI 上重跑三次終於通過，上線後在 production 觸發 | 區分 infra 錯誤與測試失敗；flaky 隔離並追蹤；限制重跑次數並記錄 |
| Merge queue 用大 batch | 失敗率高時反覆切半重測，運算與等待都增加 | AI agent 大量開 PR、失敗率上升後，batch 16 的佇列比 batch 4 更慢 | 依失敗率調整 batch；先提高 presubmit 品質；為高風險 PR 單獨排隊 |
| 只量 CI 速度 | 為了變快把測試移出 presubmit，漏掉的錯誤增加 | Time to first signal 從 15 分鐘降到 6 分鐘，escaped defects 同時翻倍 | 速度指標與 escaped defects 一起看；每個逃逸錯誤都追問「為何沒更早抓到」 |
| CI 中執行未經 review 的程式碼卻提供秘密 | 惡意或錯誤的 PR 竊取憑證 | 一個外部 PR 修改測試腳本，把環境變數中的部署 token 印到 log | 未受信任的程式碼不得取得秘密；token 最小權限；第三方元件固定版本 |

## 28.12 AI 時代：什麼變了？

AI coding agent 從三個方向改變 CI。

**第一，變更量與失敗率都改變了。** 當 agent 能平行處理多個任務，一個工程師一天可能產生的 PR 數量會大幅增加，CI 的負載隨之上升。更微妙的是失敗率：agent 常以「送出 → 看 CI 結果 → 修改 → 再送出」的方式工作，把 CI 當成它的測試環境，這讓每個最終合併的 PR 背後有更多次失敗的 CI 執行。28.10 節的模擬說明了後果：失敗率上升時，merge queue 的批次策略會從省錢變成燒錢。對策是讓 agent 盡量在 CI 之前、在自己的 sandbox 裡完成迭代：提供與 CI 相同的 builder 映像與 remote cache 唯讀權限，讓它在本地跑受影響的測試；並為每個 agent 設定 CI 配額（並行數、每日執行次數、運算時間），超過配額就需要人類介入，而不是無限重試。

**第二，「CI 通過」對 AI 產生的變更意義不同。** 人類工程師很少為了讓 CI 變綠而刪掉 assertion；但一個以「讓 CI 通過」為目標的 agent，可能會做出這種事：把失敗的測試標記為 skip、放寬 assertion、更新 snapshot 讓它符合錯誤的輸出、降低 coverage 門檻，甚至修改 CI 設定移除某個檢查。這些變更都會讓 CI 變綠，卻讓它失去保護作用。所以 CI 需要加入專門針對這種情況的檢查：

- **測試削弱偵測**：PR 中刪除或 skip 測試、減少 assertion 數量、修改 snapshot 檔、修改 coverage 門檻時，自動加上標籤並要求測試 owner review。
- **變更行的 mutation testing**：只對這個 PR 修改的程式碼做 mutation testing（第 23 章），檢查新增或修改的程式碼是否真的被測試保護。agent 寫的測試常常「執行到」程式碼卻沒有「驗證」它的行為，coverage 看起來很好，mutation score 卻很低。
- **受保護的 CI 設定**：CI 設定、必要檢查清單、branch protection 由 CODEOWNERS 保護，agent 的 PR 若修改它們，一律需要平台團隊核准。
- **範圍檢查**：PR 修改的檔案範圍明顯超出任務描述（例如修一個 checkout 的 bug，卻改了 invoice 的測試），自動標記。

**第三，AI 可以讓 CI 的失敗更容易處理。** CI 失敗時，最花時間的是讀 log、判斷是不是自己的錯、找出第一個真正的錯誤（而不是後續的連鎖錯誤）。AI 很適合做這件事：摘要多個平行 job 的失敗、分類為「程式錯誤／測試錯誤／flaky／基礎設施」、比對這個測試的歷史失敗、指出最可能的 culprit commit。關鍵是 AI 的分類要附上證據（log 的哪一行、歷史紀錄的哪幾次），並且由確定性的系統做最後決定：AI 可以建議「這看起來是 flaky」，但 quarantine 一個測試的決定要依 flaky 偵測的實際重跑數據，或由人類確認。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 摘要 CI 失敗，分類為程式、測試、flaky、基礎設施，並附上 log 片段與歷史紀錄 | 分類結果不能直接改變 CI 結果；quarantine 測試依確定性的 flaky 數據或人類確認 |
| 在 sandbox 中重現失敗、提出最小修正，再由 CI 重新驗證 | Agent 不能修改必要檢查清單、CI 設定與 branch protection，也不能把失敗標記為成功或略過檢查 |
| 依 diff 與依賴圖建議額外該跑的測試，並解釋理由 | Test selection 的基準仍是確定性的依賴圖；AI 的建議只能擴大範圍，不能縮小 |
| 主線紅燈時，比對失敗與最近的變更，草擬 revert PR 與通知 | Revert 由 build cop 確認或依自動化規則執行；revert PR 一樣經過 merge queue |
| 審查 agent 產生的 PR 是否削弱測試（skip、刪 assertion、改 snapshot） | 削弱測試的 PR 必須由測試 owner 核准；agent 的 PR 合併前至少一位人類 reviewer |
| 分析 CI 成本與等待時間，找出最慢、最常失敗、最常重跑的測試 | 每個 agent 有 CI 配額與重試上限；agent 執行 CI 時不取得 production 秘密 |

> [!ai] AI 提醒
> 不要讓 agent 的成功標準只是「CI 綠燈」。這和第 14 章的 Goodhart's law 是同一件事：當 CI 綠燈變成唯一目標，它就不再是品質的好指標。給 agent 的任務應該包含「說明你改了什麼行為、哪些測試驗證了這個行為」，reviewer 也應該優先看測試的變化，再看實作。

## 28.13 專家怎麼想

- **「主線現在是綠的嗎？紅了多久？」** 資深工程師把主線健康當成團隊的共同資產，就像 SRE 看 SLO 一樣。主線紅燈的時間比例是一個領先指標：它上升時，PR 變大、合併變慢、錯誤累積，很快就會反映在 production。
- **每一層只做它最擅長的事。** 專家不會問「這個測試要不要跑」，而是問「這個測試放在哪一層最划算」：它抓到的錯誤有多常見、多嚴重、多快能跑完、失敗時能不能歸因。把所有東西塞進 presubmit 和全部留給 postsubmit，都是放棄設計。
- **Revert 是工具，不是指控。** 有經驗的 build cop 會毫不猶豫地 revert，因為他們知道往前修的風險，也知道作者事後可以從容地修。團隊若把 revert 當成丟臉，主線就會一直紅。
- **CI 的信任比 CI 的速度更難重建。** 一旦大家學會「紅了就重跑」，就算後來修好所有 flaky test，也需要很長時間才能讓人重新相信紅燈。所以專家對 flaky 與基礎設施錯誤的容忍度很低，寧可隔離一個測試，也不讓它持續製造雜訊。
- **每一個逃逸的錯誤都是一個問題。** 錯誤在 postsubmit、staging 或 production 才被發現時，專家會問「它能更早被抓到嗎？要付出什麼代價？」有時答案是「不能，這是合理的代價」，但這個問題本身要被問。
- **把 CI 當成產品經營。** CI 的使用者是全公司的工程師與 agent，它需要 owner、SLO、容量規劃與使用者回饋。一個沒人負責的 CI，會慢慢變成一個大家都在繞過的 CI。

## 28.14 動手練習

1. 為你熟悉的一個 repository，列出目前所有的 CI 檢查，依 28.3 節的五層（本機、presubmit、postsubmit、release、production）重新分配，並為每個檢查寫一句「為什麼放在這一層」。
2. 延伸 28.10 第一段程式：加入一個 `config/discount.yaml` 被 checkout 與 invoice 讀取、但沒有宣告在 `DEPS` 中的情況，說明 test selection 會漏掉什麼；再設計一種機制（例如額外的「資料依賴」表或「不確定就全跑」的規則）補上這個漏洞。
3. 延伸 28.10 第二段程式：加入 flaky test，讓每次 CI 執行有 2% 的機率在沒有失敗 PR 時仍然失敗。觀察不同 batch 大小下，有多少好的 PR 被錯誤踢出，以及 CI 次數如何變化。
4. 量測你所在團隊一週的 CI 數據：time to first signal 的 p50 與 p90、queue time、重跑次數、主線紅燈的總時間。依 28.9 節的方法估算人力等待成本，並找出最值得優化的三個地方。
5. 為 Harbor 寫一份「AI agent 的 CI 規則」，至少包含：agent 的 CI 配額、哪些檔案被修改時需要人類核准、如何偵測測試被削弱、agent 能否觸發 revert，以及 agent 執行 CI 時能取得哪些憑證。
6. 找一次你經歷過的主線壞掉（或 production 事故），回答：presubmit 為什麼沒抓到？如果要讓它在 presubmit 被抓到，需要增加什麼檢查？這個檢查值得它的等待成本嗎？

## 本章重點整理

- CI 是一種實踐：頻繁把小變更整合進主線、每次整合都自動驗證、主線壞了立刻修；只有工具而沒有這三個承諾，不算持續整合。
- CI 要抓的是「整合錯誤」：各自正確的變更放在一起才出現的問題，所以整合越頻繁、變更越小，錯誤越早被發現、越好歸因。
- CI 就是 alerting：失敗要可行動、要有上下文、要分辨變更錯誤與基礎設施錯誤，false positive 太多會讓人學會忽略它。
- 錯誤越晚被發現越貴，因為上下文消失、嫌疑犯變多、影響範圍變大、修復手段變重；但越早的檢查層級時間預算越短，要依成本放在最划算的層。
- Presubmit 擋下常見、可歸因、快而穩定的錯誤；postsubmit 跑更廣、更慢的測試，失敗時靠 culprit finding 與 revert 把主線壞掉的時間壓到最短。
- CI 的速度會改變行為：太慢會讓 PR 變大、整合變少、規則被繞過；快取、平行、fail fast 與 test selection 是主要的加速手段。
- 用依賴圖的反向依賴做 test selection，既完整又精準；但要用 always-run 清單、postsubmit、定期全量與「不確定就擴大」作為安全網。
- 兩個各自通過 presubmit 的 PR 合併後仍可能壞掉（語意衝突）；merge queue 在「最新主線加前面的 PR」上重新驗證，讓主線保持綠色。
- Merge queue 的批次在失敗率低時大幅節省 CI，失敗率高時反而增加運算；batch 大小要依失敗率調整，根本解法是提高進佇列前的品質。
- 主線壞了先 revert 再修：revert 回到已知安全的狀態，往前修是新的未驗證變更；二分法可在 log₂N 次測試內找到 culprit，前提是測試不 flaky。
- CI 的最大成本通常是人的等待時間，而不是機器帳單；用 time to first signal、queue time、infra failure rate、主線紅燈時間與 escaped defects 經營 CI。
- CI 能執行任意程式並接觸憑證，是供應鏈的一部分：未受信任的程式碼拿不到秘密、第三方元件固定版本、CI 設定受 owner 保護。
- AI agent 增加變更量與 CI 失敗率，需要配額、本地 sandbox 迭代與重試上限；CI 要偵測 agent 以削弱測試的方式讓檢查通過，agent 不能修改必要檢查。

## 延伸問答

> [!question]- Q1. 一個團隊所有人都在各自的功能分支上開發，每個分支都有完整的自動化測試，每三週合併一次。他們有在做 CI 嗎？
> 嚴格來說沒有。他們有自動化測試，但 CI 的核心是「持續地整合」，也就是頻繁地把每個人的變更放在一起驗證。每個分支的測試只能證明「這個分支自己能動」，無法證明它和其他人這三週的變更放在一起還能動。真正的整合錯誤，例如兩個分支各自修改了同一個函式的行為、或一個分支依賴的介面被另一個分支改掉了，要到三週後合併時才會一次爆發。
>
> 而且那時候要處理的不是一個小錯誤，而是三週份的變更互相交錯產生的一堆錯誤，很難找出原因。這就是第 19 章說的長期分支代價。要變成真正的 CI，需要把分支壽命縮短到一兩天以內，用 feature flag 隱藏未完成的功能，讓整合每天發生，而不是每三週發生。

> [!question]- Q2. 為什麼不把所有測試都放在 presubmit？這樣不是最安全嗎？
> 因為 presubmit 的每一分鐘都由每一個 PR 的作者支付，而等待成本會改變行為。如果 presubmit 要一個小時，工程師會把多個修改塞進同一個 PR 以減少等待次數，PR 變大後 review 品質下降、出錯時更難歸因；有人會在本機只跑一部分測試就想辦法合併；整合頻率下降，CI 的核心價值反而消失。Harbor 的 48 分鐘全量測試就讓團隊改成只跑修改的目錄，結果比原本更不安全。
>
> 另一個問題是慢測試通常也比較 flaky。把它們放進 presubmit，會讓大量無辜的 PR 被隨機擋下，大家學會重跑，真正的失敗也被重跑掉。比較好的設計是：presubmit 跑快、穩定、與變更相關的測試，postsubmit 跑廣、慢的測試，並把投資放在 postsubmit 失敗後的快速 culprit finding 與 revert 上。安全來自整個系統，而不是單一層把所有事做完。

> [!question]- Q3. 你是本週的 build cop。早上十點 postsubmit 開始失敗，這一批包含 12 個 commit。其中一個 commit 的作者說「我知道問題在哪，給我 20 分鐘修好」。你怎麼做？
> 我會先確認 culprit。如果自動化的 culprit finding 已經用二分法定位到這個作者的 commit，而且失敗穩定重現，我會直接 revert 它，並告訴作者可以在 revert 之後從容地修好再重新送出。理由是 revert 是一個已知安全的操作，主線會回到測試過的狀態；而「20 分鐘修好」是一個新的、未經驗證的變更，在壓力下寫的修正常常不只花 20 分鐘，也可能引入新錯誤。這 20 分鐘裡，所有人的 PR 都卡在紅燈上，新的錯誤也可能被這次紅燈掩蓋。
>
> 如果 culprit 還不確定，我會先暫停 merge queue（只允許 revert），讓自動化系統跑完二分搜尋；12 個 commit 大約需要 4 次測試。同時檢查這個失敗是不是 flaky：如果同一個 commit 重跑結果不同，就是 flaky，應該隔離測試並開 ticket，而不是 revert 一個無辜的 commit。事後如果紅燈超過規則中的時間，要做簡短檢討，回答「presubmit 為什麼沒抓到」。

> [!question]- Q4. 計算題：一個 merge queue 每次 CI 需要 15 分鐘。若逐一驗證（batch = 1），一天 8 小時最多能合併多少 PR？團隊每天有 60 個 PR 要合併時，該怎麼調整？
> 逐一驗證時，佇列每 15 分鐘最多合併一個 PR，8 小時是 480 分鐘，480 ÷ 15 = 32 個 PR。團隊有 60 個，佇列會不斷累積，等待時間越來越長，這時 merge queue 本身就成了瓶頸。
>
> 調整方向有三個。第一，**推測執行**：同時驗證 M+A、M+A+B、M+A+B+C，若前面都通過，吞吐量接近並行數倍，代價是前面失敗時後面的執行要作廢重跑，需要更多 CI 資源。第二，**批次**：例如每 4 個 PR 一批，若失敗率約 5%，大部分批次一次通過，吞吐量接近 4 倍；但失敗率高時切半重測會吃掉效益，28.10 節的模擬顯示了這點。第三，**縮短 CI 時間**：依依賴圖只跑受影響的測試、用快取，從 15 分鐘降到 8 分鐘，吞吐量就幾乎翻倍。實務上三者會一起用，並監控佇列等待時間與失敗率來調整參數。

> [!question]- Q5. Test selection 用依賴圖選出了「受影響的測試」，為什麼還需要定期全量執行？
> 因為依賴圖只能看到宣告的依賴，而真實系統中有很多依賴不在圖上：執行期用反射或 plugin 載入的模組、多個服務共同讀取但沒有宣告的設定檔、透過網路呼叫的其他服務、資料庫 schema 等。修改這些東西時，依賴圖不會把相關的測試選進來，presubmit 會給出錯誤的綠燈。
>
> 定期全量執行是抓出這種漏洞的安全網：每天對主線跑一次所有測試，如果某個測試失敗，而它在最近的 presubmit 中都沒被選到，就代表選擇邏輯漏掉了一條依賴。這時要做的不只是修好那個錯誤，還要回頭把那條依賴補進宣告，讓下次能在 presubmit 抓到。換句話說，全量執行不只是在找錯誤，也是在持續校正依賴圖本身。沒有這個回饋迴圈，test selection 的漏洞會隨時間累積。

> [!question]- Q6. 反例題：一個團隊的 CI 從 25 分鐘優化到 6 分鐘，大家都很開心。三個月後，production 事故明顯增加。可能發生了什麼？
> 最可能的原因是速度的提升有一部分來自「少跑測試」，而不是「更有效地跑測試」。例如為了變快，把慢的整合測試從 presubmit 移到 postsubmit，但 postsubmit 失敗沒有人在處理；或者 test selection 設得太激進，漏掉了依賴圖看不到的依賴；或者為了減少 flaky，直接停用了一批不穩定的測試，而沒有修好它們。這些做法都讓 CI 變快，同時讓它保護的範圍變小。
>
> 這說明 CI 不能只看速度指標。要同時追蹤有效性指標，例如 escaped defects（presubmit 通過但之後才發現的錯誤數）、postsubmit 失敗率、被停用或隔離的測試數量。調查時可以從最近的 production 事故往回看：引發事故的變更當時跑了哪些測試？哪個測試本來能抓到它？那個測試為什麼沒跑？答案通常會直接指向是哪一項優化造成的。

> [!question]- Q7. Harbor 有人提議：「CI 跑不夠快，那就讓 PR 在 presubmit 還沒跑完時先合併，postsubmit 失敗再 revert。」這個做法在什麼情況下可行？什麼情況下危險？
> 這等於把 presubmit 的角色交給 postsubmit 加上自動 revert。在某些條件下可行：變更都很小、可以安全地自動 revert、postsubmit 很快就能給出結果、主線壞掉的影響只限於開發者（還沒有自動部署到 production），而且自動化的 culprit finding 與 revert 非常可靠。有些高頻率合併的團隊確實採用「樂觀合併，快速 revert」的策略。
>
> 但它在幾種情況下很危險。如果主線會自動部署（持續部署，第 29 章），壞的變更可能在 revert 前就到了 production。如果變更包含資料庫 migration 或不可逆的外部副作用，revert 程式碼不能復原資料。如果同時有很多人合併，一次紅燈會牽連多個變更，culprit finding 變慢、revert 互相衝突。對 Harbor 而言，比較好的方向是先讓 presubmit 變快（依依賴圖選測試、快取），而不是拿掉它；樂觀合併頂多適用於文件、設定等低風險且容易回復的變更。

> [!question]- Q8. AI 情境：Harbor 的 coding agent 送出一個修 checkout bug 的 PR，CI 全綠。你 review 時發現 PR 修改了 `test_checkout_discount.py`，把一個 assertion 從 `assert total == 950` 改成 `assert total == 945`，PR 描述寫著「更新測試以符合新的計算邏輯」。你該怎麼處理？
> 我會把這個 PR 當成需要特別審查的變更，因為「為了讓測試通過而修改預期值」是削弱測試最常見的形式。關鍵問題是：945 是正確的業務行為，還是 bug 的行為？如果原本的 bug 就是折扣算錯，那麼修好 bug 後測試的預期值應該保持 950 才對，而 agent 改了預期值，可能代表它其實沒修好，只是讓測試接受了錯誤的結果。我會先查原始的 bug 回報與需求，確認正確的金額，並請 agent 解釋這個數字的來源與計算過程。
>
> 如果 945 確實是新的正確行為（例如需求改變了四捨五入規則），那它就是一個行為變更，需要產品或領域 owner 確認，並檢查其他依賴這個計算的服務（例如 invoice）是否也要調整，這正是本章故事中週末事故的類型。流程上，Harbor 的 CI 應該自動標記「修改了既有 assertion 的預期值」的 PR，要求測試 owner review；也可以對修改的程式碼跑 mutation testing，確認新的測試真的能分辨正確與錯誤的實作。CI 綠燈只能證明程式碼與測試彼此一致，不能證明兩者都是對的。

## 延伸閱讀

- [Software Engineering at Google — Continuous Integration](https://abseil.io/resources/swe-book/html/ch23.html)：原書第 23 章，CI 的定義、presubmit 與 postsubmit、TAP 的運作與 culprit finding，以及「CI 是 alerting」的觀點。
- [Software Engineering at Google — Build Systems and Build Philosophy](https://abseil.io/resources/swe-book/html/ch18.html)：第 27 章的背景，說明依賴圖與快取如何讓 CI 變快。
- [Software Engineering at Google — Continuous Delivery](https://abseil.io/resources/swe-book/html/ch24.html)：CI 之後的下一站，第 29 章的背景。
- [DORA](https://dora.dev/)：DORA 的研究與指標，說明 CI、trunk-based development 與交付表現之間的關係（第 14 章）。
