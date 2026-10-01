---
chapter: 16
title: Code Review：正確性、理解與小型變更
part: 3
---

# 第 16 章　Code Review：正確性、理解與小型變更

> [!abstract] 本章地圖
> **核心問題**：Code review 要怎麼同時抓到錯誤、讓團隊理解彼此的程式、傳遞知識，又不變成每個變更都要排隊的瓶頸？
>
> **你會學到**：
> - 說明 code review 的四個目的，以及它「不是」什麼
> - 區分 LGTM、ownership approval 與 readability，並用 OWNERS／CODEOWNERS 設計 approval 規則
> - 把大變更拆成小而完整的 PR，並寫出讓 reviewer 能快速理解的 PR 描述
> - 寫出具體、分級、對事不對人的 review comment，並知道什麼時候該 approve
> - 理解 review 延遲如何放大 lead time，並設計回應時間與輪值的約定
> - Review AI 生成的變更，並把 AI reviewer 放在正確的位置
>
> **前置知識**：第 8 章（HRT 與給回饋）、第 10 章（readability）、第 15 章（style guide 與自動化）
>
> **對應原書**：SWE 第 9 章〈Code Review〉；SWE 第 3 章〈Knowledge Sharing〉（readability 部分）

## 16.1 故事：一個 1,800 行的 PR，和一個等了三天的 40 行 PR

第 15 章的 formatter 與 linter 上線後，Harbor 的 review 留言不再討論引號，但新的問題很快浮現。

seller 團隊的阿凱接到「賣家折價券 v2」的需求：讓賣家發行的多張折價券可以疊加、依商品類別限制使用範圍。折價計算在 checkout 的程式裡，阿凱花了兩週在自己的分支上開發，途中順手重構了 checkout 的價格計算模組、改了幾個函式名稱、補了一些 log。最後送出的 PR 有 1,800 行變更、42 個檔案，描述只有一行：「折價券 v2，詳見 ticket」。

美華是 checkout 的 tech lead（不久前才從 payments 轉任），因為 PR 改到 checkout 的程式，美華也是預設 reviewer。美華看了一眼行數，決定等週末有空再仔細看。三天後，產品經理 Lisa 在群組問上線進度，另一位同事看阿凱很著急，就花了十分鐘掃過，留下「LGTM」。PR 當天 merge、隔天上線。

上線第二天，財務發現退款金額異常：當一筆訂單用了兩張折價券、又部分退貨時，退款計算重複扣除了折價金額的四捨五入差額，有些訂單退得比實際付的還多。這段邏輯就藏在那 1,800 行裡、某個被重新命名的函式中。platform 團隊的志明協助止血後，大家在檢討時發現，給 LGTM 的同事其實只看了前三個檔案。

同一週，payments 團隊的小林送了一個 40 行的 PR，修正金流回呼的 timeout 設定。這個 PR 需要 checkout 團隊的 owner 同意，因為它改到了 checkout 的一個設定檔。它在美華的待辦清單裡躺了三天，因為美華一直在等「有空的時候」處理那個大 PR。

工程經理 Kevin 看完兩件事的時間線，在檢討會上說：「一個 PR 太大，所以沒人能真的看懂；另一個 PR 很小，卻因為排在大 PR 後面而等了三天。兩個問題的根源是同一件事：我們沒有把 review 當成一個需要設計的系統。」

這一章就要設計這個系統：review 到底為了什麼、誰有權批准什麼、作者與 reviewer 各自要負什麼責任、怎麼讓變更變小、怎麼讓 review 變快，以及當越來越多程式碼由 AI 產生時，review 要怎麼調整。

## 16.2 Code review 為了什麼

### 四個目的

**Code review**（程式碼審查）是指一個變更在進入主線之前，由作者以外的人閱讀並同意的過程。在 GitHub 上它叫 pull request（PR），在 Google 內部叫 changelist（CL），在 Gerrit 叫 change，概念相同。

很多人以為 review 的目的就是抓 bug。抓 bug 確實重要，但《Software Engineering at Google》第 9 章列出的好處遠不止於此：除了檢查正確性，還包括讓變更能被其他工程師理解、維持 codebase 的一致性、在心理上促進團隊共同擁有程式碼、促成知識分享，以及留下一份 review 的歷史紀錄。本章把它們整理成四個主要目的：

1. **正確性**（correctness）：在變更進入 production 前發現錯誤。越早發現的錯誤越便宜，review 是測試與 CI 之外的另一道防線。
2. **理解**（comprehension）：確保程式碼能被作者以外的人看懂。Reviewer 是這段程式的第一位「未來讀者」；如果 reviewer 看不懂，半年後的維護者、事故中的值班者也很可能看不懂。
3. **知識傳遞**：Reviewer 透過 review 了解系統的變化，作者透過 reviewer 的回饋學到更好的做法。一個團隊若每個 PR 都由不同的人 review，熟悉每塊程式的人就會變多，第 8 章談的 bus factor（關鍵知識只在少數人身上的風險）也會下降。
4. **一致性**：讓 codebase 在設計與寫法上保持一致，延續第 15 章的目標。能由工具處理的一致性交給工具，review 處理的是工具看不到的部分，例如抽象層次、錯誤處理方式、命名是否符合領域語言。

原書還提到一個常被忽略的心理效果：作者知道自己的程式會被別人讀，會更認真地寫、更主動地解釋。光是「有人會看」這件事，就改變了寫程式的方式。

### 研究怎麼說

Microsoft 研究人員 Bacchelli 與 Bird 在 2013 年發表於 ICSE 的研究〈Expectations, Outcomes, and Challenges of Modern Code Review〉中觀察到一個有趣的落差：開發者普遍認為 review 最主要的目的是找出缺陷，但實際的 review 留言中，直接與缺陷有關的只占一部分，更多是程式碼改善、替代方案的討論，以及讓團隊知道有哪些變化。這不代表 review 抓 bug 沒有用，而是提醒我們：如果只用「抓到多少 bug」評價 review，會低估它在理解與知識傳遞上的價值，也會讓人誤以為「測試夠完整就不需要 review」。

### Review 不是什麼

同樣重要的是說清楚 review 不是什麼：

- **不是測試的替代品**。人類讀程式很難發現所有邊界情況，尤其是並行、時間、大量資料的問題。Review 要確認測試存在且合理，而不是用眼睛代替測試執行。
- **不是 reviewer 按自己喜好重寫程式的機會**。如果作者的寫法正確、清楚、符合規範，只是和 reviewer 習慣的不同，那就不是問題。
- **不是權力或地位的展現**。資深工程師的 PR 一樣需要 review，初階工程師的意見一樣可能是對的。
- **不是責任轉移**。Reviewer 給了 approve，不代表作者可以不再對正確性負責。作者永遠是最了解這個變更的人。

## 16.3 三種批准：LGTM、ownership 與 readability

### Google 的三個問題

Google 把一次 code review 拆成三個獨立的問題，每個問題由合適的人回答：

- **LGTM**（Looks Good To Me）：這個變更正確嗎？看得懂嗎？由任何一位熟悉相關程式的同事回答，通常是同團隊的工程師。
- **Owner approval**（擁有者批准）：這個變更適合放在這裡嗎？符合這塊程式的長期方向嗎？由該目錄的 owner 回答。Google 用每個目錄中的 OWNERS 檔案列出有權批准的人；這些檔案是階層式疊加的，一個檔案的 owner 是它上方所有目錄 OWNERS 名單的聯集，所以上層目錄的 owner 對下層也有批准權。如果作者本身就是 owner，這一項自動滿足。
- **Readability approval**：這個變更符合該語言的寫法與慣例嗎？由通過該語言 readability 認證的人回答（第 10 章）。

一個人可以同時滿足三個條件，例如 owner 本身有 readability，又熟悉這段程式，那麼一次 review 就夠了。拆開的意義在於：**「這段程式對不對」和「這段程式該不該這樣改」是兩個不同的問題**，需要的知識不同，也不一定由同一個人回答最好。

```text
            作者送出 PR
                 │
                 ▼
     ┌───────── 自動檢查 ─────────┐   formatter、linter、type check、
     │  （第 15 章、第 28 章）     │   測試、安全掃描
     └─────────────┬──────────────┘
                   │ 全部通過才請人看
                   ▼
  ┌────────────────┼────────────────┐
  ▼                ▼                ▼
 LGTM          Owner approval    Readability
 正確嗎？       該這樣改嗎？       寫法符合慣例嗎？
 同事           OWNERS 檔案中的人  有語言認證的人
  │                │                │
  └────────────────┼────────────────┘
                   ▼
      三者都滿足（可以是同一個人）
                   │
                   ▼
           merge（或進入 merge queue）
```

這張圖從上往下讀：自動檢查是第一關，沒有通過就不該占用人的時間；接著是三個平行的問題，由不同角色回答；三者都滿足才能 merge。實務上大多數 PR 只需要一到兩個人，因為同一位 reviewer 往往同時具備多種身份。

### 在 GitHub 上的對應

大多數公司沒有 Google 的 readability 制度，但前兩者很容易落地。GitHub 的 **CODEOWNERS** 檔案可以為路徑指定 owner，搭配 branch protection 的「需要 code owner review」設定，就能要求修改某個目錄的 PR 必須有該目錄 owner 的 approve。GitLab 與其他平台也有類似機制。

Harbor 的 CODEOWNERS 大致長這樣：

```text
# 路徑                     擁有者
*                          @harbor/checkout-team      # 預設
/payments/                 @harbor/payments-team
/deploy/                   @harbor/platform-team
/tools/lint/               @harbor/platform-team      # 第 15 章：linter 設定受保護
/.github/workflows/        @harbor/platform-team
```

GitHub 的 CODEOWNERS 規則是後面的規則優先，所以 `/payments/` 下的檔案由 payments 團隊擁有，而不是預設的 checkout 團隊。小林那個 40 行的 PR 改到 checkout 的設定檔，就自動要求 checkout 團隊的 approve。

這裡有兩個常見的設計錯誤。第一是 **owner 名單只有一個人**，那個人休假時，整個目錄的變更都會卡住。owner 應該是一個團隊，或至少兩到三個人。第二是 **要求太多 approve**。原書提到 Google 大多數的 code review 恰好只有一位 reviewer，預設也只需要一個 LGTM，並指出多加 reviewer 的成本很快就會超過他們帶來的價值。當一個 PR 需要三個人同意，每個人都可能假設「其他人會仔細看」，結果反而沒有人仔細看。這種現象叫 **diffusion of responsibility**（責任分散）。要求的 approve 數量應該和風險相稱，而不是越多越安全。

### Approval 之後的變更

另一個設定細節是：作者在得到 approve 之後又推了新的 commit，approve 還算數嗎？GitHub 的 branch protection 可以設定「有新 commit 時撤銷舊的 approve」。對高風險的目錄（payments、deploy）應該開啟，避免「先拿到 approve，再偷偷改大」。對一般目錄，另一種常見做法是 reviewer 給「LGTM with comments」：同意整體方向，信任作者會處理剩下的小建議，不必再看一次。兩者的選擇取決於風險與團隊間的信任程度。

## 16.4 小變更：review 品質的第一個決定因素

### 為什麼要小

如果只能改善 code review 的一件事，幾乎所有資深工程師都會選：**讓變更變小**。Harbor 的折價券事故，根本原因不是 reviewer 不認真，而是 1,800 行的變更超出了任何人一次能理解的範圍。

小變更的好處是互相加乘的：

- **Review 品質更高**。Reviewer 能在腦中建立整個變更的模型，看出邏輯錯誤與邊界情況。變更越大，reviewer 越容易只看表面。
- **Review 更快**。一個 50 行的 PR，reviewer 可以在兩次會議之間看完；一個 1,800 行的 PR，reviewer 會等「有一整段空檔」，而那段空檔可能永遠不會來。
- **出問題時更容易定位與回復**。如果小 PR 造成問題，可以直接 revert 它，不會連帶撤掉其他無關的修改；用 `git bisect`（二分搜尋找出引入問題的 commit）時，定位也更精確。
- **衝突更少**。在分支上待兩週的變更，會和其他人的修改大量衝突（第 19 章）。

一個常被引用的經驗法則來自 Google 公開的 code review 指南：大約 100 行的變更通常合理，1,000 行通常太大，但最終仍由 reviewer 判斷；檔案數也有影響，同樣 200 行，集中在一個檔案可能沒問題，散在 50 個檔案通常就太大。原書第 9 章則說「小」的變更一般應限制在約 200 行左右。這些都不是硬性規定，刪除整個檔案、由完全信任的自動化工具產生的變更可以很大；但對人類需要理解的邏輯變更，這個數量級是個好參考。

### 怎麼拆

「拆小」最常見的反對理由是：「我的功能就是這麼大，拆開後每一塊都不完整。」關鍵在於拆的方式。每個小 PR 都要滿足兩個條件：**本身是完整的一件事**，以及 **merge 之後主線仍然可以運作**。

阿凱的折價券 v2，可以這樣拆：

| 順序 | PR | 大約行數 | 為什麼可以獨立 |
|---|---|---|---|
| 1 | 重構價格計算模組，行為不變 | 300 | 純重構；現有測試全部通過就代表行為沒變 |
| 2 | 新增 `CouponStack` 資料結構與單元測試，尚未被呼叫 | 200 | 新程式碼沒有被使用，不影響 production |
| 3 | 在 checkout 中使用 `CouponStack`，以 feature flag 關閉 | 150 | Flag 預設關閉，上線後行為不變 |
| 4 | 退款流程支援多張折價券，同樣在 flag 後 | 180 | 可以單獨測試退款的邊界情況 |
| 5 | 補充 log 與 metrics | 80 | 純觀測性變更 |
| 6 | 移除舊的單張折價券程式碼（flag 全開穩定後） | −400 | 清理 |

幾個常用的拆法：

- **重構與行為變更分開**。純重構的 PR，reviewer 只需要確認「行為沒變」；行為變更的 PR，reviewer 只需要專注新邏輯。混在一起，reviewer 就必須在每一行判斷「這是搬移還是修改」，折價券事故中被重新命名的函式就是這樣藏住 bug 的。
- **先加後用**。先新增新的函式、類別或資料表，但不使用；下一個 PR 再接上。
- **用 feature flag 讓未完成的功能進主線**。功能在 flag 後面逐步完成，不必在長期分支上累積（第 19 章、第 29 章）。
- **資料庫變更用 expand／contract**：先加新欄位、雙寫、切換讀取、最後移除舊欄位，每一步都可以獨立上線與回復（第 29 章）。
- **Stacked changes**（堆疊式變更）：PR 2 建立在 PR 1 之上，兩者可以同時送出 review，reviewer 依序看。Gerrit 等工具原生支援這種工作流，GitHub 上也有輔助工具。

拆小也有下限。如果某個不變條件（invariant，例如「訂單總額等於各項金額加總」）需要兩處同時修改才能成立，就不能把它們拆到兩個 PR，否則中間那段時間主線是壞的。拆分的目標是「每一步都安全」，不是「行數越少越好」。

## 16.5 作者的責任

### 讓 reviewer 的工作變簡單

作者是對變更最了解的人，也是最能降低 review 成本的人。原書與 Google 的指南都強調：好的 review 從作者開始。作者的責任包括：

**寫一份好的 PR 描述。** 描述的第一行是摘要，要能在列表中單獨讀懂，例如「修正多張折價券部分退款時重複扣除捨入差額」，而不是「fix bug」或「update」。內文要回答 reviewer 最需要知道的問題。Harbor 事故後採用的 PR 範本：

```text
## 為什麼
多張折價券疊加後部分退款，退款金額會重複扣除四捨五入差額（INC-2024-031）。

## 做了什麼
- 退款計算改為依原始付款明細按比例分攤，不再重新計算折價
- 新增 6 個邊界情況測試（單張／多張、全退／部分退、含運費）

## 沒有做什麼
- 未修改折價券疊加規則本身（另開 PR #1482）

## 風險與驗證
- 影響範圍：refund_amount()，所有退款路徑
- 已用過去 30 天的 1,200 筆退款資料重算，新舊結果差異僅出現在多張折價券的 37 筆，皆為修正方向
- Rollback：直接 revert，無資料遷移

## 請特別看
- refund.py 第 88–120 行的分攤邏輯
```

「沒有做什麼」與「請特別看」是最常被省略、卻最能幫 reviewer 節省時間的兩段。前者避免 reviewer 浪費時間質疑不在範圍內的事；後者告訴 reviewer 作者自己最不確定的地方。

**送出前先自己 review 一次。** 在 PR 介面上以 reviewer 的角度讀一遍自己的 diff，常常會發現忘記刪除的除錯程式碼、不小心 commit 的檔案，或描述與實作不符的地方。

**先讓自動檢查通過。** CI 還是紅的就請人 review，等於請 reviewer 幫忙做機器的工作。

**選對 reviewer，而且數量要少。** 一位熟悉這段程式的 reviewer，加上必要的 owner，通常就夠了。把五個人都加進來，反而沒有人覺得自己負責。

### 回應 review 意見

收到意見時，作者的工作是**回應每一則留言**：修改了就說「已修改」並附上 commit；不同意就說明理由；不確定就提問。不要靜默地修改某些、忽略另一些，reviewer 會不知道哪些已經處理。

當作者和 reviewer 意見不同，第 8 章的 HRT（謙遜、尊重、信任）是基礎：先假設對方有道理，試著理解對方的顧慮。如果來回兩輪仍然無法達成共識，就不要在留言串裡繼續爭論，改成直接對話，或請 tech lead、owner 做決定，並把結論記錄在 PR 中。

第 8 章談過，作者不要把 reviewer 的意見視為對自己的評價。程式碼不是作者的一部分，對程式碼的批評也不是對人的批評。反過來，reviewer 也有責任讓留言只針對程式碼，這是下一節的主題。

## 16.6 Reviewer 的責任與好的 review comment

### 看什麼、依什麼順序看

Reviewer 的注意力是有限的資源，要花在最重要的地方。一個實用的閱讀順序，是從大到小：

1. **目的與設計**：讀 PR 描述，確認這個變更要解決的問題是真實的，做法是合理的。如果設計方向就有問題，後面的細節都不用看，應該先回到設計討論。大型新功能的設計應該在寫程式之前就經過 design doc review（第 17 章），而不是在 PR 階段才第一次討論。
2. **正確性與邊界情況**：主要邏輯對嗎？錯誤處理、空值、並行、時區、金額精度、重試這些容易出錯的地方，有沒有處理？
3. **測試**：測試是否覆蓋了變更的行為與邊界情況？測試失敗時能看出原因嗎？測試是否只是重複實作，而沒有真正驗證行為（第 23 章）？
4. **可理解性**：命名是否反映領域意義？結構是否讓讀者容易追蹤？需要註解解釋「為什麼」的地方有沒有註解？
5. **營運面**：上線後出問題能被看見嗎？有 log 與 metrics 嗎？能安全 rollback 嗎？會不會影響其他服務的負載？

格式與排版不在清單上，因為第 15 章已經把它們交給工具了。

### 什麼時候該 approve

Reviewer 最常犯的錯誤之一，是把「這不是我會寫的樣子」當成不 approve 的理由。Google 公開的 code review 指南提出一個很好的標準：**當一個變更確實改善了整體的程式碼健康程度，即使它不完美，reviewer 也應該傾向 approve**。追求完美會讓每個 PR 來回五輪，作者精疲力盡，整個團隊的速度變慢；而「比現在更好」是一個可以持續累積的方向。

這不代表可以放過真正的問題。正確性、安全性、會讓程式更難維護的設計問題，都應該要求修改。可以放過的是偏好：另一種一樣好的寫法、作者沒採用但不影響品質的小建議。

### 留言要分級

為了讓作者知道每則留言的份量，Harbor 採用明確的前綴：

| 前綴 | 意思 | 作者要怎麼做 | 例子 |
|---|---|---|---|
| （無前綴） | 必須處理才能 merge | 修改，或說服 reviewer | 「部分退款時這裡會重複扣除捨入差額，見下方算例」 |
| **Nit:** | 小問題，建議修但不阻擋 | 自行決定 | 「Nit: `amt` 改成 `refund_amount` 會更清楚」 |
| **Optional:** | 可以考慮的替代做法 | 自行決定，可以之後再做 | 「Optional: 這段之後可以抽成共用函式」 |
| **Question:** | Reviewer 不理解，需要解釋 | 回答；若需要解釋，考慮補註解 | 「Question: 為什麼這裡要先排序？」 |
| **FYI:** | 分享資訊，不需要動作 | 閱讀即可 | 「FYI: platform 團隊下個月會提供共用的 retry helper」 |

Google 公開的 code review 指南也建議用 Nit:、Optional:（或 Consider:）、FYI: 這類前綴標示留言的份量，現在很多團隊都採用類似的慣例；Question: 是 Harbor 自己加的。分級最大的好處是讓作者分得出輕重：沒有分級時，作者常常會把 reviewer 隨口的建議當成命令，或反過來把真正的問題當成偏好忽略。

「Question」也值得一提。Reviewer 看不懂某段程式時，問題常常不在 reviewer，而在程式本身不夠清楚。作者回答之後，應該想想：「下一個讀者也會有同樣的問題嗎？」如果會，答案應該寫進程式碼或註解，而不是只留在 PR 的留言裡，因為 PR 留言之後幾乎沒人會再看。

### 好的留言長什麼樣子

好的 review comment 有三個特徵：**針對程式碼而非人、說明理由、盡量給出具體建議**。比較下面幾組：

| 不好的留言 | 好的留言 | 差別 |
|---|---|---|
| 「你為什麼要這樣寫？」 | 「這裡每次迴圈都查一次資料庫，訂單有 200 項時會發 200 次查詢。可以先批次讀進來嗎？」 | 說出具體的問題與後果，給出方向 |
| 「錯了。」 | 「當 `coupons` 為空時，第 42 行會除以零。可以加一個測試案例覆蓋這個情況嗎？」 | 指出條件、位置與驗證方式 |
| 「這樣很難讀。」 | 「Nit: 三層巢狀的 if 不太好追蹤，用 early return 會比較平，例如……」 | 標示份量、提供替代寫法 |
| 「我們這裡不這樣做。」 | 「我們的錯誤處理慣例是往上拋出 `PaymentError`，由 handler 統一轉成回應，見 docs/errors.md。」 | 說明慣例與出處，讓作者下次知道 |

也別忘了稱讚。看到寫得好的測試、清楚的抽象、細心的邊界處理，說一句「這個測試設計得很好」。這不只是禮貌，也是在告訴作者和其他讀者「這是值得模仿的做法」，是知識傳遞的一部分。

> [!warning] 常見誤解
> 「留言越多，代表 review 越認真。」留言數量和 review 品質沒有直接關係。一個 reviewer 留了 30 則 nit，卻沒注意到退款邏輯的錯誤，比只留一則「這裡會重複扣款」的 reviewer 糟糕得多。好的 reviewer 會把注意力放在影響最大的地方。

## 16.7 Review 延遲的成本

### 等待會被放大

小林那個 40 行的 PR，美華只需要十分鐘就能看完，但它等了三天。這三天的成本遠不只三天：

- **Context switch**（脈絡切換）：小林在等待期間開始做別的事，收到意見時要重新回想當初的細節。
- **變更越積越大**：作者不想等，就在同一個分支上繼續加東西，PR 變大，review 更慢，形成惡性循環。
- **衝突**：等待期間主線一直在前進，PR 越晚 merge，衝突越多。
- **激勵效應**：如果每個 PR 都要等三天，工程師就會傾向把工作累積成更大的 PR 一次送出，因為「反正都要等」。這正好和 16.4 節的目標相反。

Review 延遲也直接影響第 14 章與第 29 章的 DORA 指標 **lead time for changes**（從 commit 到上線的時間）。在很多團隊中，等待 review 是 lead time 裡相當大的一段，常常比跑 CI 還久；第 14 章會談怎麼量測它，而不是憑感覺猜。

### 回應快不等於 approve 快

Google 公開的 code review 指南建議：如果你不在專注工作的中途，收到 review 請求後應盡快處理；如果正在專注，就等到自然的中斷點（完成手上的工作、午餐或會議回來）再處理，而**回應的上限是一個工作天**。原書第 9 章也描述 Google 期待在 24 個工作小時內得到 review 回饋。注意它講的是「回應」，不是「approve」。一個快速的回應可以是：「我看完了設計，有兩個問題」，或「這個 PR 太大，我建議拆成三個」，甚至是「我今天沒空，建議改找另一位 owner」。作者最怕的不是被要求修改，而是不知道什麼時候會有回應。

Harbor 在檢討後訂了幾條約定：

- **一個工作天內第一次回應**；高優先的修正（例如事故修復）在一小時內。
- **每天固定兩個時段處理 review**，例如上午開始工作前與午餐後，讓 review 不會一直打斷專注工作，也不會無限期延後。
- **Reviewer 輪值**：每個團隊每天有一位「review 值班」，負責處理沒有指定 reviewer 的 PR，避免所有 PR 都湧向 tech lead。
- **大 PR 可以直接退回**：reviewer 有權要求拆分，而不必硬著頭皮看完。

16.9 節的程式會用一個簡單模型顯示：當每一輪等待時間很長時，把大 PR 拆成小 PR 未必能縮短總時間；只有當 review 回應夠快時，小變更的好處才會完全發揮。**小變更與快速 review 是一組的**，只做其中一個，效果有限。

### 量測 review 的健康程度

Kevin 開始追蹤幾個數字：第一次回應的時間、從送出到 merge 的時間、PR 大小的分布、每個 PR 的來回輪數，以及每位 reviewer 的負載。這些數字的用途是找出瓶頸，例如發現 70% 的 checkout PR 都在等美華，進而擴大 owner 名單。

但它們不該變成個人績效指標。第 14 章的 Goodhart's law 在這裡特別明顯：如果「review 回應時間」變成考核目標，reviewer 會學會快速丟下一則「LGTM」，數字變漂亮，品質卻下降。折價券事故中那個十分鐘的 LGTM，正是這種壓力的產物。

## 16.8 自動化先行與不同類型的變更

### 讓人只看機器看不到的東西

Review 的人力很貴，所以要確保 reviewer 拿到 PR 時，所有機器能檢查的事都已經檢查過了。Harbor 的 PR 在請人看之前，會先經過：

- Formatter、linter、type checker（第 15 章）
- 單元測試與受影響的整合測試（第 22 章、第 28 章）
- 安全掃描與依賴檢查（第 20 章）
- 自動標記：PR 大小標籤、是否修改了 CODEOWNERS 保護的檔案、是否新增了 suppression、是否修改了資料庫 schema

最後一類「自動標記」很值得投資。它不判斷對錯，而是把 reviewer 該特別注意的事情放到最顯眼的位置。例如一個 PR 修改了 schema，就自動加上「需要 migration review」的標籤，並提醒 reviewer 確認 rollback 方式。

### 不同類型的變更，review 重點不同

原書指出，不同類型的變更需要不同的 review 方式：

- **全新的功能或專案**（greenfield）：最大的風險是設計錯誤。原書強調程式碼本身是一種負債（code is a liability），需要維護、需要被理解，所以新程式碼要有充分的理由。設計應該在寫程式之前就由 design doc 討論過（第 17 章），PR 階段主要確認實作是否符合設計，以及測試是否完整。
- **行為變更、改進與最佳化**：重點是「改了什麼行為」以及「誰會受影響」。效能最佳化需要附上量測數據，不能只說「應該會比較快」。
- **Bug 修正**：應該附上能重現 bug 的測試，修正前失敗、修正後通過。修正的範圍要小，不要順手重構，否則 reviewer 無法判斷修正是否完整。
- **Rollback**：Revert 一個造成問題的變更，應該是最快通過 review 的類型。Harbor 允許 revert PR 由任何一位 owner 快速 approve，因為 rollback 是止血手段，延遲 rollback 的代價通常比 rollback 本身的風險高得多（第 29 章）。
- **重構與大規模變更**：大多由工具產生，reviewer 重點是確認變更確實是機械性的、測試通過。大規模變更通常會拆成許多小 PR，並由特定的全域 approver 處理，避免每個團隊都要重新 review 同樣的模式（第 21 章）。
- **緊急修正**：事故中可能需要在沒有完整 review 的情況下上線修正。這種例外要有明確規則：誰可以授權、事後多久內補 review、在 postmortem 中記錄（第 44 章、第 45 章）。

## 16.9 動手寫：merge gate 與 review 延遲模型

下面的程式分成兩部分。第一部分是一個簡化的 **merge gate**（合併關卡）：依照 OWNERS 規則判斷一個 PR 是否滿足 LGTM、owner approval 與 CI 的要求，並對大變更與 AI 生成的變更加上額外規則。第二部分用一個簡單的模型，比較「一個大 PR」與「四個小 PR」在不同 review 等待時間下的 lead time。

```python
from dataclasses import dataclass, field

TEAMS = {
    "checkout-team": {"小芸", "美華"},
    "payments-team": {"小林", "美華"},   # 美華從 payments 轉任，仍保留 owner 身分
    "seller-team": {"阿凱", "思妤"},
    "platform-team": {"志明"},
}
# 類似 OWNERS／CODEOWNERS：最長的路徑前綴勝出，沒有符合就往上繼承根目錄
OWNERS = {
    "": "checkout-team",
    "payments/": "payments-team",
    "deploy/": "platform-team",
}
SIZE_WARN = 400


@dataclass
class Change:
    title: str
    author: str
    files: dict                       # 路徑 → 變更行數
    lgtm: set = field(default_factory=set)
    ci_green: bool = True
    ai_generated: bool = False
    has_tests: bool = False
    author_explained: bool = False    # 作者是否在描述中說明設計與驗證方式


def owner_team(path):
    prefix = max((p for p in OWNERS if path.startswith(p)), key=len)
    return OWNERS[prefix]


def evaluate(c: Change):
    blockers, warnings = [], []
    reviewers = c.lgtm - {c.author}
    if not reviewers:
        blockers.append("缺少作者以外的 LGTM")
    for team in sorted({owner_team(p) for p in c.files}):
        members = TEAMS[team]
        if c.author not in members and not (reviewers & members):
            blockers.append(f"缺少 {team} 的 owner approval")
    if not c.ci_green:
        blockers.append("CI 未通過")
    size = sum(c.files.values())
    if size > SIZE_WARN:
        warnings.append(f"變更 {size} 行，超過 {SIZE_WARN} 行，建議拆分")
    if c.ai_generated and not (c.has_tests and c.author_explained):
        blockers.append("AI 生成的變更需附測試，且作者要說明設計與驗證")
    return blockers, warnings


changes = [
    Change("折價券計算", "阿凱", {"checkout/coupon.py": 120, "checkout/test_coupon.py": 90},
           lgtm={"美華"}, has_tests=True),
    Change("退款四捨五入修正", "小芸", {"payments/refund.py": 30, "checkout/api.py": 8},
           lgtm={"志明"}),
    Change("agent：重構訂單查詢", "阿凱", {"checkout/orders.py": 520, "deploy/canary.yaml": 12},
           lgtm={"美華", "志明"}, ai_generated=True, has_tests=True),
]

for c in changes:
    blockers, warnings = evaluate(c)
    status = "可以 merge" if not blockers else "擋下"
    print(f"[{status}] {c.title}")
    for b in blockers:
        print(f"   ✗ {b}")
    for w in warnings:
        print(f"   ! {w}")

print()
print("lead time 粗估（假設值，用來比較形狀，不是實測數據）")


def lead_time(prs, wait):
    # 每個 PR：rounds × (等待 reviewer + 閱讀 + 作者修改)，PR 之間依序進行
    total = 0.0
    for lines, rounds in prs:
        read = lines / 300            # 假設每小時仔細讀 300 行
        fix = 1 + lines / 400         # 假設修改時間隨變更大小成長
        total += rounds * (wait + read + fix)
    return total


big = [(1600, 3)]                     # 一個大 PR，留言多、來回三輪
small = [(400, 1)] * 4                # 拆成四個 PR，各一輪
for wait in (24, 4, 1):
    print(f"  每輪等待 {wait:>2} 小時：大 PR {lead_time(big, wait):6.1f} h｜四個小 PR {lead_time(small, wait):6.1f} h")
```

執行結果：

```text
[可以 merge] 折價券計算
[擋下] 退款四捨五入修正
   ✗ 缺少 payments-team 的 owner approval
[擋下] agent：重構訂單查詢
   ✗ AI 生成的變更需附測試，且作者要說明設計與驗證
   ! 變更 532 行，超過 400 行，建議拆分

lead time 粗估（假設值，用來比較形狀，不是實測數據）
  每輪等待 24 小時：大 PR  103.0 h｜四個小 PR  109.3 h
  每輪等待  4 小時：大 PR   43.0 h｜四個小 PR   29.3 h
  每輪等待  1 小時：大 PR   34.0 h｜四個小 PR   17.3 h
```

逐段解讀：

1. `OWNERS` 用 CODEOWNERS 的思路簡化：每個路徑前綴對應一個團隊，最長（最具體）的前綴勝出，沒有符合的就落到根目錄的 owner。`owner_team` 就是這個查找邏輯。真實的 CODEOWNERS 支援萬用字元，並以「最後一條符合的規則」為準；Google 的 OWNERS 則是把上層各目錄的名單取聯集，所以根目錄的 owner 也能批准 `payments/` 下的檔案。這個程式刻意只取一個團隊，讓「誰負責這個目錄」更清楚。
2. `evaluate` 把 16.3 節的三個問題中的兩個寫成程式：至少一位**作者以外**的 LGTM，以及每個被修改的目錄都有其 owner 團隊的成員同意。注意 owner 檢查允許「作者本身就是 owner」，這和 Google 的做法一致：owner 自己的變更仍需要另一個人的 LGTM，但不需要再找另一位 owner。
3. 第二個 PR「退款四捨五入修正」被擋下，因為它修改了 `payments/refund.py`，而給 LGTM 的志明不是 payments 團隊的成員。LGTM 說的是「我看過、覺得正確」，owner approval 說的是「這塊程式的負責人同意這樣改」，兩者不能互相取代。
4. 第三個 PR 由 AI agent 產生，雖然有兩位 reviewer 同意、也有測試，但作者沒有在描述中說明設計與驗證方式，因此被擋下；它同時超過 400 行，收到拆分建議。這對應到 16.11 節的原則：AI 生成的變更，作者仍要能解釋它。
5. 延遲模型中的參數（每小時讀 300 行、修改時間、來回輪數）都是**假設值**，用來觀察形狀，不是實測數據。結果顯示：當每輪等待 24 小時，四個小 PR 依序送出的總時間甚至比一個大 PR 還長，因為每個 PR 都要付一次等待成本；當等待縮短到 4 小時或 1 小時，小 PR 的優勢就非常明顯。這就是 16.7 節說的「小變更與快速 review 是一組的」。

這個模型還沒有反映另外兩個現實：大 PR 的 review 品質較差（更多 bug 漏到 production），以及小 PR 可以用 stacked changes 平行送出、不必完全依序等待。把這兩點加進去，小變更的優勢會更大；練習 3 會請你實作。

在真實系統中，merge gate 由程式碼託管平台的 branch protection、CODEOWNERS 與必要的 CI 檢查共同組成，額外的組織規則（例如 AI 生成變更的要求）常以自訂的 CI 檢查或 bot 實作。結構不變：**機器先檢查 → 依路徑找到負責人 → 正確性與 ownership 分開批准 → 依風險加上額外條件**。

## 16.10 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| 大型 PR 一次送出 | Reviewer 無法建立完整理解，只看表面 | 折價券 v2 的 1,800 行 PR，reviewer 只看了前三個檔案就 LGTM | 重構與行為變更分開；feature flag 讓未完成功能進主線；reviewer 有權要求拆分 |
| Rubber stamp（橡皮圖章式 approve） | 流程上有 review，實際上沒有獨立檢查 | 上線壓力下，同事十分鐘掃過就 LGTM | 高風險路徑要求 owner approve；PR 描述標出「請特別看」；不把回應時間當 KPI |
| 要求太多 reviewer | 責任分散，每個人都以為別人會仔細看，latency 也變長 | 一個 PR 加了五位 reviewer，三天後只有兩人看過，都只看了自己熟的部分 | 一位主要 reviewer 加必要 owner；明確指定誰負責哪個面向 |
| Owner 只有一個人 | 單點瓶頸，休假或忙碌時整個目錄停擺 | 小林的 40 行 PR 等了三天，因為只有美華能 approve | Owner 設為團隊；review 輪值；追蹤 reviewer 負載 |
| 追求完美才 approve | 來回輪數過多，作者疲憊，團隊變慢 | 一個 bug 修正因為 reviewer 堅持改變數命名來回五輪 | 以「改善整體程式碼健康」為標準；用 Nit／Optional 標示偏好 |
| Review 只看程式碼，不看營運面 | 上線後才發現無法觀測、無法回復 | 新的 migration 沒有 rollback 方式，上線失敗後只能手動修資料 | Review checklist 包含 log、metrics、rollback；schema 變更自動標記 |
| Approve 後又推大量修改 | Reviewer 同意的版本和 merge 的版本不同 | 作者拿到 approve 後又加了 200 行「小調整」 | 高風險目錄開啟「新 commit 撤銷 approve」 |

## 16.11 AI 時代：什麼變了？

AI 同時改變了 code review 的兩端：越來越多的變更由 AI 產生，越來越多的 review 意見也由 AI 提供。

### Review AI 生成的變更

**第一，產量的瓶頸從寫轉移到審。** 一個 coding agent 可以在二十分鐘內產生幾百行看起來合理的程式碼，但 reviewer 的閱讀速度沒有變。如果團隊不調整，review 會成為新的瓶頸，或者更糟：review 品質下降，大家開始對 AI 產生的程式碼 rubber stamp。Harbor 的對策是把 16.4 節的規則同樣套用在 agent 身上：一個 agent 任務只做一件事，產生的 PR 同樣要小；超過一定大小的 agent PR 要先拆分才能請人 review。

**第二，送出 PR 的人就是作者，不管程式碼是誰打的。** 阿凱用 agent 產生了一個 PR，阿凱就是這個 PR 的作者，要能回答 reviewer 的每一個問題：為什麼這樣設計、考慮過哪些邊界情況、怎麼驗證的。「這是 AI 寫的」不是答案。Harbor 的 PR 範本加了一欄「AI 參與」，作者要說明哪些部分由 AI 產生、自己如何驗證；16.9 節的 merge gate 就是這條規則的自動化版本。

**第三，AI 生成程式碼有特定的錯誤型態。** Reviewer 應該特別注意：

- **不存在或過時的 API**：模型可能呼叫一個看起來合理、但實際不存在的函式或參數，或使用已經 deprecated 的寫法。型別檢查與測試能抓到一部分。
- **看似完整、其實錯誤的邊界處理**：程式碼結構完整、有錯誤處理，但處理的方式不符合業務需求，例如退款失敗時靜默回傳零。
- **範圍蔓延**：要求修一個 bug，agent 順手改了十個檔案的命名或結構。這會讓 reviewer 難以分辨哪些是必要修改。
- **削弱測試**：為了讓測試通過，修改測試的預期值、刪除失敗的測試，或把 assertion 改得更寬鬆。Reviewer 要特別檢查測試檔案的 diff，問「這個測試被改，是因為行為該變，還是因為實作錯了？」
- **繞過檢查**：新增 suppression、修改 linter 或 CI 設定（第 15 章）。

GitHub 也公開了審查 AI 生成程式碼的指南（見延伸閱讀），可以作為團隊建立自己 checklist 的起點。

### 使用 AI reviewer

**AI reviewer 適合做「第一位讀者」，不適合做「最後一位決策者」。** AI reviewer 可以在人類看之前，先指出可能遺漏的測試、未處理的錯誤路徑、與既有慣例不一致的地方，或為大型 diff 整理一份「變更地圖」：入口在哪、哪些狀態被修改、哪些依賴受影響。這能讓人類 reviewer 更快建立理解，把注意力放在最關鍵的地方。

但它有幾個限制要清楚：

- **它不知道沒有寫下來的脈絡**：業務規則、過去事故的教訓、團隊的長期方向，如果沒有出現在它能讀到的資料中，它就無從判斷。
- **它會產生雜訊**：大量看似合理但不重要的建議，會讓作者疲於回應，也可能淹沒真正重要的那一則。要像第 15 章對待 linter 誤報一樣，追蹤 AI 意見中有多少真的被採納。
- **同源的盲點**：如果產生程式碼與審查程式碼的是同一個模型、同一份 context，它很可能對同樣的錯誤視而不見。用不同的 context（例如只給 reviewer 需求與 diff，不給生成時的對話）能減少這種情況，但不能完全消除。
- **它不能承擔責任**：AI 的意見不能取代 LGTM 或 owner approval。Approve 代表一個人願意對這個變更負責，這個角色不能交給模型。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 為大型 diff 產生變更地圖：入口、狀態變化、受影響的依賴與測試 | 變更地圖只是導覽，reviewer 仍要閱讀關鍵路徑的實際程式碼 |
| 在人類 review 前先檢查遺漏的測試、錯誤處理、timeout、與慣例不符之處 | AI 意見不能算作 LGTM 或 owner approval；高風險路徑（payments、auth、deploy）必須有人類 owner approve |
| 比對 diff 與 API／schema 定義，列出可能不相容的變更 | 是否接受不相容變更、如何遷移，由 owner 決定（第 17 章、第 18 章） |
| 依需求拆分大型任務，讓 agent 產生多個小 PR | Agent PR 要遵守同樣的大小限制；作者必須在「AI 參與」欄說明範圍與驗證方式 |
| 整理 review 留言，區分必須修改、需要決策與可選建議 | 作者與 reviewer 之間的意見分歧，由人討論與決定，並記錄結論 |
| 標記測試檔案中被刪除或放寬的 assertion、新增的 suppression | 任何測試被削弱或檢查被繞過，都需要人類明確同意並說明理由 |

> [!ai] AI 提醒
> 不要讓同一個 agent 寫程式、修改測試、再自己 review 並宣告通過。這三件事如果由同一個系統完成，等於沒有獨立的檢查。至少要讓測試與 CI 是確定性的、不可被該 agent 修改，並由一位人類對結果負責。

## 16.12 專家怎麼想

- **「這個 PR 想解決什麼問題？」** 資深 reviewer 的第一步永遠是讀描述、理解目的。如果描述看不懂，會先請作者補充，而不是直接讀程式碼猜意圖。目的不清楚的變更，再漂亮的實作也無法判斷對錯。
- **「如果這個 PR 明天造成事故，我們怎麼發現、怎麼回復？」** 專家會把一部分注意力放在營運面：有沒有 metrics、能不能 revert、會不會需要資料修復。這個問題常常能暴露出作者沒想到的風險。
- **「太大就退回，而不是硬看。」** 專家知道自己的注意力有限，變更超過幾百行後很難再逐行仔細閱讀。與其勉強看完一個 1,800 行的 PR 並給出虛假的信心，不如請作者拆分，這對雙方都更好。
- **「回應要快，approve 不一定要快。」** 資深工程師會盡快給出第一個回應，即使只是「我明天下午看」或「先拆小再說」。讓作者知道狀態，比讓作者猜測更重要。
- **「這則意見是品質問題，還是我的偏好？」** 專家在留言前會問自己這個問題，並誠實地用 Nit 或 Optional 標示偏好。他們也會在寫得好的地方留下稱讚。
- **「重複出現的意見就是自動化的候選。」** 如果同一類意見在三個 PR 中都出現，專家會把它變成 linter 規則、PR 範本的檢查項或文件，而不是繼續一次一次地留言（第 15 章）。

## 16.13 動手練習

1. 找一個你寫過的大型 PR（或一個開源專案中超過 500 行的 PR），把它重新規劃成 4–6 個可以依序 merge、每一步主線都能運作的小 PR，並說明每一步為什麼是安全的。
2. 為 16.9 節的 merge gate 加入兩條規則：修改 `payments/` 的 PR 若在 approve 後有新 commit，approve 失效；以及標記為 `revert` 的 PR 只需要任一位 owner 的 approve，不需要額外 LGTM。
3. 擴充 16.9 節的延遲模型：加入 stacked changes（多個小 PR 可以同時送出 review，等待時間部分重疊），以及「PR 越大、漏到 production 的 bug 越多」的假設，觀察小 PR 的優勢如何變化。記得清楚標示你的假設。
4. 挑一個最近的 PR，依 16.6 節的順序（目的、正確性、測試、可理解性、營運面）重新 review 一次，並為每則留言加上分級前綴。
5. 把一則你收過（或寫過）的不好的 review comment，改寫成「針對程式碼、說明理由、給出建議」的版本。
6. 請一個 AI coding agent 完成一個小功能，再分別用兩種方式請 AI review：一次在同一個對話中，一次在只提供需求與 diff 的新對話中。比較兩者找出的問題有何不同，並記錄哪些問題兩者都沒發現。

## 本章重點整理

- Code review 的目的不只是抓 bug，還包括確保程式能被理解、傳遞知識、維持一致性；只用抓到的 bug 數量評價 review 會低估它的價值。
- Review 不是測試的替代品，不是 reviewer 按個人偏好重寫的機會，也不是作者的責任轉移。
- 「這段程式對不對」（LGTM）和「這段程式該不該這樣改」（owner approval）是兩個不同的問題，可以由不同的人回答；Google 另外用 readability 確保語言慣例。
- OWNERS／CODEOWNERS 讓 approval 依路徑自動找到負責人；owner 應該是團隊而不是單一個人，要求的 approve 數量要和風險相稱。
- 小變更是 review 品質的第一個決定因素：理解更完整、回應更快、更容易回復與定位問題。
- 拆分的原則是每個 PR 本身完整、merge 後主線仍能運作；重構與行為變更分開，用 feature flag 與 expand／contract 讓未完成的工作安全進入主線。
- 作者負責降低 review 成本：清楚的 PR 描述（為什麼、做了什麼、沒做什麼、風險與驗證、請特別看）、先自我 review、先讓 CI 通過、回應每一則留言。
- Reviewer 從目的與設計看起，再看正確性、測試、可理解性與營運面；格式交給工具。
- 當變更確實改善整體程式碼健康時，即使不完美也應傾向 approve；偏好要用 Nit 或 Optional 標示。
- 好的 review comment 針對程式碼而非人、說明理由、給出具體建議，也包括對好做法的稱讚。
- Review 延遲會被 context switch、變更累積與衝突放大；第一次回應應在一個工作天內，回應快不等於 approve 快。
- 小變更與快速 review 必須一起做；只拆小而 review 仍然很慢，總時間未必縮短。
- AI 生成的變更，送出 PR 的人就是作者，必須能解釋與驗證；reviewer 要特別注意不存在的 API、範圍蔓延、被削弱的測試與被繞過的檢查。
- AI reviewer 適合當第一位讀者，不能取代人類的 LGTM 與 owner approval，也不應和產生程式碼的 agent 共用同一份 context。

## 延伸問答

> [!question]- Q1. LGTM 和 owner approval 有什麼不同？為什麼不讓一個人全包？
> LGTM 回答的是「這個變更正確嗎、看得懂嗎」，任何熟悉相關程式的同事都能回答；owner approval 回答的是「這個變更適合放在這裡嗎、符合這塊程式的長期方向嗎」，需要對該模組負長期責任的人回答。前者重在細節，後者重在方向與後果。
>
> 實務上兩者常常由同一個人完成，例如 owner 本身就在 review 程式碼。拆開的價值在於讓更多人可以參與 review：初階工程師可以給 LGTM、在過程中學習，而不必每個 PR 都等少數幾位 owner 從頭看到尾；owner 則可以把注意力集中在方向與風險上。在 16.9 節的例子中，志明的 LGTM 不能取代 payments 團隊的 owner approval，因為退款邏輯的長期責任在 payments 團隊身上。

> [!question]- Q2. 作者說：「這個功能就是這麼大，拆開之後每個 PR 都不完整，沒辦法 review。」你會怎麼回應？
> 先同意對方的顧慮是合理的：拆分不能讓主線處於壞掉的狀態，也不能拆到 reviewer 看不出整體方向。但「不完整」通常指的是「功能還不能給使用者用」，而不是「程式碼不能獨立驗證」，這兩者可以分開處理。
>
> 具體做法是：先把純重構拆出來，讓 reviewer 只需確認行為不變；新的資料結構與邏輯可以先加入但不被呼叫；接上 production 路徑的部分放在預設關閉的 feature flag 後面；資料庫變更用 expand／contract。為了讓 reviewer 看見全貌，第一個 PR 的描述可以附上整體計畫與後續 PR 的清單，或先用一份簡短的 design doc 對齊方向。如果某兩處修改確實必須同時成立才能維持不變條件，就讓它們留在同一個 PR，拆分的目標是每一步都安全，不是行數最少。

> [!question]- Q3. 你是 reviewer，看到一個 PR 寫法和你習慣的不同，但你找不出任何錯誤。該怎麼做？
> 應該 approve。Code review 的標準是「這個變更是否改善了整體程式碼健康」，而不是「這是否是我會寫的樣子」。如果作者的寫法正確、清楚、符合團隊規範與慣例，只是風格和你不同，堅持修改只會增加來回輪數、讓作者覺得被找麻煩，對 codebase 沒有實質改善。
>
> 如果你真的認為另一種寫法更好，可以用「Optional:」或「Nit:」前綴提出，並說明理由，讓作者自行決定。如果你發現團隊中反覆出現同樣的分歧，例如錯誤處理有兩種常見做法，那就是該在 style guide 或設計文件中統一的訊號，而不是在每個 PR 裡各自爭論。

> [!question]- Q4. 為什麼要求越多人 approve，不一定越安全？
> 因為責任會被分散。當一個 PR 需要三位 reviewer，每個人都可能只看自己熟悉的部分，並假設其他人會仔細看其他部分，最後可能沒有人完整理解整個變更。這就是 diffusion of responsibility。同時，每多一個必要的 approver，等待時間就會增加，因為要等最慢的那一位。
>
> 比較好的設計是：一位主要 reviewer 負責整體正確性，必要時加上特定路徑的 owner，並明確指定每個人負責看什麼，例如「志明請看 deploy 設定的 rollback 方式」。對真正高風險的變更，增加的應該是檢查的深度與自動化的保護，例如更完整的測試、canary 與 rollback 計畫，而不只是 approve 的數量。

> [!question]- Q5. 計算題：一個團隊每輪 review 平均要等 24 小時。一個 1,600 行的 PR 需要 3 輪，四個 400 行的 PR 各需 1 輪。照 16.9 節的模型，為什麼拆小之後總時間反而稍微變長？要怎麼改善？
> 依模型，大 PR 每輪的成本是等待 24 小時、閱讀約 5.3 小時、修改 5 小時，三輪共約 103 小時；四個小 PR 每個是等待 24 小時、閱讀約 1.3 小時、修改 2 小時，四個依序進行共約 109 小時。等待時間是最大的成本，而小 PR 每一個都要付一次等待，所以總等待次數從 3 次變成 4 次，抵消了閱讀與修改時間的節省。
>
> 改善有兩個方向。第一是縮短等待：當每輪等待降到 4 小時，小 PR 總共約 29 小時，大 PR 約 43 小時，差距立刻出現；這就是為什麼小變更必須搭配快速回應的 review 文化。第二是讓等待重疊：用 stacked changes 同時送出多個 PR，reviewer 可以一次依序看完。這個模型還沒算入大 PR 漏掉更多 bug 的成本，真實情況下小 PR 的優勢通常更大，但前提是 review 不能慢。

> [!question]- Q6. 情境題：你在 review 一個 AI agent 產生的 PR，發現它為了修一個 bug，同時修改了實作和三個測試的預期值。你會怎麼判斷？
> 關鍵問題是：這些測試的預期值被改，是因為「正確的行為本來就該改變」，還是因為「實作錯了，所以把測試改成符合錯誤的實作」？前者是合理的修改，後者是削弱測試，會讓 bug 被永久寫進測試裡。AI agent 在被要求「讓測試通過」時，後者是一條很常見的捷徑。
>
> 具體做法是逐一檢查被修改的測試：原本的預期值代表什麼業務規則？新的預期值有沒有需求或規格支持？然後請 PR 的作者（送出 PR 的人，不是 agent）在描述中說明每一個測試修改的理由。如果作者說不出來，就不應該 merge。長期來看，可以讓工具自動標記「同時修改實作與既有測試預期值」的 PR，提醒 reviewer 特別注意。

> [!question]- Q7. 團隊想導入 AI reviewer，有人提議「AI 沒意見就自動 merge」。你怎麼看？
> 不建議。AI reviewer 沒有提出意見，只代表它沒有發現它能發現的問題，不代表變更是正確的。它不知道沒有寫下來的業務規則與過去的事故教訓，也可能和產生程式碼的模型有相同的盲點。更根本的是，approve 代表有人願意對這個變更負責，這個角色不能交給模型。
>
> 比較好的定位是讓 AI reviewer 當「第一位讀者」：在人類看之前先指出可能的問題、整理變更地圖，讓人類 reviewer 更快進入重點。對低風險的變更，例如文件修正或自動產生的依賴更新，可以搭配嚴格的確定性檢查來簡化人類 review，但仍應有人類 approve。導入後要追蹤 AI 意見的採納率與誤報率，太吵的 AI reviewer 會像高誤報的 linter 一樣，讓所有人學會忽略它。

> [!question]- Q8. 面試題：你加入一個團隊，發現 PR 平均要等三天才有人 review。你會怎麼改善？
> 先量測，找出瓶頸在哪裡：是所有 PR 都慢，還是集中在某幾位 reviewer 或某些目錄？PR 的大小分布如何？等待發生在第一次回應之前，還是在來回修改之間？常見的發現是少數 owner 負擔過重，或 PR 普遍太大讓人一直延後處理。
>
> 接著依原因處理：擴大 owner 名單、設定 review 輪值；約定一個工作天內第一次回應，並強調回應不等於 approve；在 PR 範本與 CI 中加入大小提醒，鼓勵拆分；把格式與常見問題交給工具，減少每次 review 的負擔；讓 revert 與緊急修正有快速通道。最後持續追蹤第一次回應時間與 PR 大小，但不要把它們變成個人績效指標，否則會換來快速而空洞的 LGTM。回答時能同時講到「量測、流程、工具、文化」四個面向，並提醒 Goodhart's law，會很有說服力。

## 延伸閱讀

- [Software Engineering at Google — Code Review](https://abseil.io/resources/swe-book/html/ch09.html)：本章的原始章節，Google 的 LGTM、ownership、readability 三種批准與 review 最佳實務。
- [Software Engineering at Google — Knowledge Sharing](https://abseil.io/resources/swe-book/html/ch03.html)：readability 制度的由來，說明 review 如何成為知識傳遞的管道。
- [Software Engineering at Google — Continuous Integration](https://abseil.io/resources/swe-book/html/ch23.html)：自動化檢查如何在人類 review 之前攔下問題。
- [GitHub Docs — Review AI-generated code](https://docs.github.com/copilot/tutorials/review-ai-generated-code)：審查 AI 生成程式碼時的檢查重點。
- [OpenAI — Codex best practices](https://learn.chatgpt.com/guides/best-practices)：使用 coding agent 時如何設定任務範圍與驗證方式，可搭配本章的 AI 小節閱讀。
