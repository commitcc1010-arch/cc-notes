---
chapter: 29
title: Continuous Delivery、Canary 與 Rollback
part: 4
---

# 第 29 章　Continuous Delivery、Canary 與 Rollback

> [!abstract] 本章地圖
> **核心問題**：通過 CI 的程式碼，要怎麼送進 production，才不會把整間公司的命運押在一次大部署上？
>
> **你會學到**：
> - 分清 continuous integration、continuous delivery、continuous deployment，以及「deploy」和「release」為什麼要拆開
> - 設計一條 build once、promote many 的 delivery pipeline，並選擇 rolling、blue/green、canary 等部署策略
> - 用 feature flag 與 dark launch 把「程式上線」和「功能開放」分開，同時避免 flag 債
> - 設計 canary 分析：選指標、設對照組、判斷樣本夠不夠、用統計比較而不是用眼睛看圖
> - 判斷該 rollback 還是 roll forward，並用 expand／contract 讓資料庫 schema 變更可以回退
> - 用 DORA 指標檢查 delivery 流程是否真的變好
>
> **前置知識**：第 19 章（trunk-based development 與 feature flag）、第 27 章（artifact 與 provenance）、第 28 章（continuous integration）
>
> **對應原書**：SWE 第 24 章〈Continuous Delivery〉；SRE 第 8 章〈Release Engineering〉；SRE Workbook 第 16 章〈Canarying Releases〉

## 29.1 故事：雙週四晚上十點的「大部署」

Harbor 成長到四十位工程師時，發布方式還停留在八人新創的年代：每隔一週的週四晚上十點，全體後端工程師留在辦公室，由 tech lead 美華依照一份共享文件逐行執行部署步驟。這兩週累積下來的所有 commit 會被打包成一個版本，一次推到所有機器上。大家把那天晚上叫做「release night」，訂便當、開直播、一直待到凌晨。

四月的那一次，版本裡有 63 個 commit。其中一個是阿凱重寫的購物車折價券邏輯，另一個是一支資料庫 migration：把 `orders` 表裡舊的 `coupon_code` 欄位改成新的 `coupon_id`，並刪掉舊欄位。部署在十點二十分完成，十點三十五分客服開始回報「結帳時折價券無效」。原來新邏輯在某種「滿額再折」的組合下會算錯金額，於是系統拒絕結帳。

美華決定 rollback，把機器換回上一版。但舊版程式還在讀 `coupon_code`，而那個欄位已經被 migration 刪掉了，舊版一啟動就噴出大量錯誤。回不去，也走不下去。團隊只好從前一晚的備份還原欄位資料、再手動補寫這幾十分鐘內成立的訂單，一路弄到凌晨兩點。事後估計約有三個小時，大部分使用者無法完成結帳。

Postmortem 會議上，工程經理 Kevin 問了三個問題：「為什麼一個折價券的 bug 會讓所有使用者都受影響？為什麼兩週的變更要一起上？為什麼 rollback 的時候才發現回不去？」第 28 章的 CI 已經讓 Harbor 每個 commit 都會跑測試，但這次的 bug 只在真實訂單的特定組合下出現，測試沒有涵蓋到。CI 能證明「我們想得到的情況是對的」，卻無法證明「production 裡所有情況都是對的」。

這一章要建立的，就是 CI 之後的那一段：讓每個變更以小批次、可觀察、可停止、可回退的方式進入 production。Harbor 後來的做法有四個部分：小批次的 continuous delivery、用 feature flag 把部署和開放分開、用 canary 讓新版本先只碰到一小部分流量，以及讓每一次資料庫變更都能回退。

## 29.2 CI、CD 與 continuous deployment：三個常被混用的詞

### 三個詞各自承諾什麼

**Continuous integration**（持續整合，第 28 章）承諾的是：每個變更都盡快合進主線，並且自動驗證，主線隨時是綠的。它回答的問題是「程式碼現在是不是好的」。

**Continuous delivery**（持續交付，簡稱 CD）承諾的是：主線上的每個版本隨時都**可以**安全地發布到 production，發布只需要一個決定，不需要一個專案。Harbor 的 release night 正好是反例：每次發布都需要一份逐行執行的文件、一整個晚上與一群人。CD 的目標是把發布變成無聊的例行事。

**Continuous deployment**（持續部署）則再進一步：每個通過 pipeline 所有關卡的變更都**自動**部署到 production，中間沒有人按按鈕。

三者是一層一層往上疊的。可以做 continuous delivery 但不做 continuous deployment，例如受監管的金融系統要求每次發布都由指定的人核准，或者手機 app 必須經過商店審核。《Software Engineering at Google》第 24 章特別指出，CD 大部分的價值來自「隨時可以發布」的那套結構，就算你沒有真的每次都發布，那套結構仍然讓你能在需要時快速、安全地出貨。

### Deploy 與 release 是兩件事

**Deploy**（部署）是把新的程式放到機器上執行；**release**（發布、開放）是讓使用者真正接觸到新的行為。Harbor 以前把兩者綁在一起：程式一上機器，新功能就對所有人開放。之後整章的工具，feature flag、dark launch、canary，本質上都是在拆開這兩件事，讓「程式在不在 production」和「誰看得到新行為」可以分別控制。

> [!example] 例子
> Harbor 的新折價券引擎可以在週一就部署到所有機器上，但被 flag 關著，沒有任何使用者走到新程式碼。週三先對公司內部員工開放，週四開放 1% 使用者，下週再逐步擴大。程式碼只部署了一次，release 卻分成了五步。

### 為什麼小批次比較安全

直覺上，部署越少次越安全，因為每次部署都有風險。《Software Engineering at Google》的核心主張卻是「**faster is safer**」：部署越頻繁、每次越小，整體反而越安全。原因可以用一個簡單的算例說明。

```text
假設每個 commit 有 2% 的機率帶進一個 production 才會出現的 bug。

雙週發布一次、每次 60 個 commit：
  這次發布至少有一個 bug 的機率 = 1 − 0.98^60 ≈ 70%
  出事時要從 60 個變更裡找兇手

每天發布數次、每次 1–3 個 commit：
  單次發布出事的機率 ≈ 2%–6%
  出事時只要看 1–3 個變更，回退也只回退這幾個
```

總 bug 數沒有變，變的是三件事。第一是**定位成本**：從 60 個變更裡找出元兇，比從 2 個變更裡找難得多。第二是**回退的連坐範圍**：大版本 rollback 時，另外 59 個沒問題的變更也一起被撤回，等於拖慢了所有人。第三是**記憶的新鮮度**：一個 commit 若在兩週後才上線，作者早已轉去做別的事，出事時要重新回憶當時的想法。

SRE 書第 8 章描述 Google 的 release engineering 時也強調同樣的觀念：發布頻率高，代表兩個版本之間的變更少，測試和排除問題都更容易。有的團隊每小時建置一次再挑一個版本出貨，也有團隊採用「push on green」，只要 build 通過所有測試就部署。

> [!warning] 常見誤解
> 「CD 就是部署得更快。」速度是結果，不是目標。CD 的重點是讓每次部署的風險小到可以接受、出事時能快速停下並回退。一個每天部署十次卻沒有 canary、沒有 rollback 的團隊，只是更頻繁地冒大風險。

## 29.3 Delivery pipeline：同一個 artifact 一路晉升

### Build once, promote many

Harbor 舊流程的另一個問題，是每個環境各自 build：staging 從原始碼 build 一次，production 再從原始碼 build 一次。兩次 build 之間，某個依賴套件可能剛好發布了新版本，於是 staging 測過的東西和 production 跑的東西其實不是同一份 bytes。

正確的做法是 **build once, promote many**：只 build 一次，產生一個不可變的 **artifact**（建置產物，例如容器映像），用它的內容雜湊值（**digest**，例如 `sha256:3f9a…`）當身分證，然後讓同一個 digest 依序**晉升**（promote）到各個環境。第 27 章談過的 hermetic build 與 provenance 在這裡發揮作用：你能證明 production 執行的，正是當初通過所有測試的那一份產物。

環境之間真正不同的東西，例如資料庫位址、外部金流商的端點、機器數量，放在**版本化的設定**中，於部署時注入，而不是改變 artifact 本身。

```text
 commit ──► CI（第 28 章）──► build 一次 ──► artifact  sha256:3f9a…
                                              │
        ┌─────────────────────────────────────┘
        ▼
   ┌─────────┐   自動    ┌─────────┐   自動    ┌──────────────────────────┐
   │ staging │ ───────► │ canary  │ ───────► │ production（逐步擴大）    │
   │ 整合測試 │  gate     │ 1%→5%   │  gate     │ 25% → 50% → 100%         │
   └─────────┘          └─────────┘          └──────────────────────────┘
        │                    │                         │
        └──── 任一 gate 失敗：停止晉升，自動回到上一個 digest ──┘

   設定（DB 位址、外部端點、副本數）：每個環境各自一份，版本化，部署時注入
   Feature flag：獨立於部署，控制「誰看得到新行為」
```

這張圖由左往右讀。CI 產生唯一的 artifact 之後，它經過三個環境，每個箭頭上都有一個 **gate**（關卡），也就是自動判斷「能不能往下走」的檢查。Staging 的 gate 看整合測試；canary 的 gate 比較新舊版本在真實流量下的表現（29.6 節）；production 內部又分成數個擴大階段。最下面的回退箭頭很重要：任何一個 gate 失敗，pipeline 不是停在半路等人來救，而是自動退回上一個已知良好的 digest。圖的最下方提醒兩件事：設定與 artifact 分開管理，flag 又與部署分開管理。

### Pipeline 本身也是 production 系統

當發布變成全自動，pipeline 就成了能改變 production 的最大權限持有者。Harbor 把 pipeline 當成一個需要被保護的系統：只有 pipeline 的身分能部署到 production，工程師個人帳號不能直接改線上機器；每次部署都留下紀錄（哪個 digest、誰合併的、經過哪些 gate、結果如何）；緊急情況下的手動部署有一條明確的「破窗」流程，事後必須補上檢討。SRE 書第 8 章把這叫做**政策與流程的強制執行**：誰能核准程式碼變更、建立 release、部署、修改 build 設定，都由權限控制，每次 release 都會產生一份它包含哪些變更的報告。

### Release train：為不能連續部署的東西設定節奏

並不是所有東西都能隨時部署。Harbor 的 iOS 與 Android app 要經過商店審核，使用者也不一定會更新。這種情況適合 **release train**（發布列車）：固定時間發車，例如每週二切出 release 分支，當時主線上已完成的東西搭上車，沒完成的等下一班。

Release train 的關鍵紀律是**列車不等人**。《Software Engineering at Google》引用的說法是：如果你趕不上列車，它會丟下你直接開走。只要班次夠密，錯過一班的代價只是晚幾天，大家就不會為了「一定要搭上這班」而塞進沒準備好的東西。Release 分支上需要修 bug 時，SRE 書描述的做法是先修在主線，再 **cherry-pick**（挑選單一 commit 套用）到 release 分支，分支本身永遠不合併回主線，這樣才能精確知道每個版本裡有什麼。

App 的 release train 還帶來一個伺服器端的長期責任：舊版本的 app 會在使用者手機上活很多個月。Harbor 的 API 因此必須同時相容好幾個 app 版本，新功能則盡量由伺服器端的 flag 控制開關，不必等使用者更新 app。

## 29.4 部署策略：rolling、blue/green 與 canary

把新版本放上機器有好幾種方式，差別在於**同一時間有多少使用者暴露在新版本下**，以及**出事時回退有多快**。

| 策略 | 怎麼運作 | 回退速度 | 額外成本 | 適合 |
|---|---|---|---|---|
| **一次全部替換**（big bang） | 所有機器同時換版 | 慢，要重新部署 | 無 | 幾乎不適合有使用者的服務 |
| **Rolling update**（滾動更新） | 一批一批替換，例如每次 10% 的機器 | 中，要反向滾動 | 低 | 一般無狀態服務的預設 |
| **Blue/green** | 準備一整套新環境（green），測好後把 router 從 blue 切到 green | 快，切回 blue 即可 | 高，同時有兩套環境 | 需要快速切換、能負擔雙倍資源 |
| **Canary** | 先讓一小部分流量走新版本，與舊版本比較後才擴大 | 快，把小部分流量切回 | 中，需要分析能力 | 使用者多、風險高的服務 |

**Rolling update** 是 Kubernetes Deployment 的預設策略：逐批建立新 Pod、等它們通過 readiness 檢查後，再移除舊 Pod，透過 `maxSurge`、`maxUnavailable` 控制速度。它的問題是「逐批」不等於「逐批驗證」：如果沒有人在每一批之間比較指標，rolling update 只是比較慢的 big bang。

**Blue/green** 的優點是切換瞬間完成，回退也只是把 router 切回去。但它有兩個陷阱。第一，兩套環境通常共用同一個資料庫，所以 blue 與 green 必須能同時讀寫同一份 schema（29.8 節）。第二，切換是全有或全無的，若問題只在大流量時出現，切過去的瞬間所有人都會碰到。

**Canary** 這個名字來自礦工帶金絲雀下礦坑：金絲雀對有毒氣體比人敏感，牠出事就代表該撤退。SRE Workbook 第 16 章的定義是：對一個服務做**局部且有時間限制的部署，並加以評估**，評估結果決定是否繼續 rollout。拿到新版本的那一小群叫 canary，其餘叫 **control**（對照組）。Canary 的本質是一個 A/B 實驗：差別只在版本，其他條件都盡量相同。

實務上這幾種策略常組合使用。**Progressive delivery**（漸進式交付）這個詞，用來概括「依證據逐步擴大曝光」的整套做法：先 canary，通過後以 rolling 方式逐步擴大，每一步都有自動 gate，同時用 feature flag 控制功能開放的對象。Argo Rollouts、Flagger 這類工具把它實作在 Kubernetes 上；Spinnaker 搭配 Kayenta 則提供自動化的 canary 分析。

Harbor 部署在多個 **availability zone**（可用區，雲端供應商內電力與網路彼此獨立的機房）上，所以還加上一層 **wave**（波次）：canary 通過後，先擴大到一個可用區，觀察一段時間，再到下一個。SRE 書描述 Google 大型面向使用者的服務會以「指數式」的方式跨叢集擴大 rollout，原理相同：信心少的時候影響範圍小，證據累積了才擴大。

## 29.5 Feature flag 與 dark launch：把開放的權力交給執行期

### Flag 怎麼運作

**Feature flag**（功能旗標）是程式中的一個條件判斷，判斷依據來自執行期可修改的設定，而不是寫死在程式碼裡：

```python
# not-runnable
def calculate_discount(cart, user):
    if flags.is_enabled("coupon_engine_v2", user=user):   # 由設定服務決定
        return coupon_engine_v2.calculate(cart)
    return legacy_coupon.calculate(cart)
```

設定服務可以依照使用者 ID、地區、員工身分、百分比等條件決定 flag 的值，修改後幾秒內生效，不需要重新部署。《Software Engineering at Google》第 24 章主張所有變更都用 flag 保護（flag guard），讓新程式碼和舊程式路徑並存；它同時提醒，一次對 100% 使用者打開 flag 並不是好主意，flag 的設定變更本身也是 production 變更，同樣需要逐步 rollout。

Flag 依用途大致可以分成四類。業界常引用的這個分類，來自 Pete Hodgson 在 Martin Fowler 網站上發表的〈Feature Toggles〉一文：

| 類型 | 用途 | 壽命 | Harbor 例子 |
|---|---|---|---|
| **Release toggle** | 未完成或未驗證的功能先關著 | 幾天到幾週，開完就刪 | `coupon_engine_v2` |
| **Experiment toggle** | A/B 實驗分流 | 實驗期間 | 推薦區塊兩種排序 |
| **Ops toggle**（kill switch） | 出事時關掉昂貴或危險的功能 | 長期 | 雙十一時關閉個人化推薦 |
| **Permission toggle** | 只對特定使用者開放 | 長期 | 企業賣家專屬報表 |

### Dark launch：讓新程式碼在暗處吃真實流量

**Dark launch**（暗中上線）是讓新程式碼處理真實流量，但結果不給使用者看。Harbor 在折價券引擎 v2 上線前做了兩週的 dark launch：每次結帳時，舊引擎的結果照常回給使用者，同時把同一份購物車送給新引擎計算，再比較兩者的金額。不一致的案例寫進日誌，工程師每天檢查。

這兩週抓出了七種金額不一致的組合，其中一種正是四月事故的「滿額再折」。這種做法也叫 **shadow traffic**（影子流量）。它的限制是只適合沒有副作用的計算：如果新程式碼會扣款、寄信或寫入資料庫，影子流量就必須把這些副作用接到假的實作，否則使用者會收到兩封信或被扣兩次款。

### Flag 的代價：flag 債與組合爆炸

Flag 讓部署和發布分開，但每個 flag 都讓程式多一條路徑。十個彼此獨立的布林 flag，理論上有 2 的 10 次方，也就是 1,024 種組合，沒有團隊會全部測試。更危險的是早已沒人記得的舊 flag。

2012 年 8 月，美國券商 Knight Capital 在新版交易程式中重新使用了一個舊 flag，這個 flag 原本用來啟動一段多年前就停用、卻一直沒刪除的舊交易邏輯。手動部署時，八台伺服器中有一台沒有更新到新程式。當 flag 被打開，那台機器跑起了舊邏輯，在大約 45 分鐘內送出大量錯誤訂單，依美國證管會（SEC）事後的調查，損失超過 4.6 億美元。這個事故集合了本章的幾個主題：手動部署而且沒有驗證每台機器都換了版、重用舊 flag、死碼沒有清掉，以及出事時沒有能快速停下來的機制。

Harbor 因此訂了 flag 的管理規則：每個 flag 建立時必須填 owner 與預計移除日期；release toggle 在全面開放後兩週內要刪除程式碼與設定；CI 會列出超過期限的 flag 並開 ticket 給 owner；flag 名稱不准重用。若要在多個服務間共用 flag 的評估方式，可以考慮 CNCF 的 OpenFeature 這類開放標準，避免綁定單一供應商的 SDK。

> [!warning] 常見誤解
> 「有 flag 就不需要 rollback。」Flag 只能關掉被它包住的程式碼。如果新版本在啟動時就 crash、拖垮了記憶體，或者 bug 出在 flag 外面的共用路徑，關 flag 救不了你。Flag 和 rollback 是兩個互補的工具。

## 29.6 Canary 分析：讓資料而不是感覺決定要不要繼續

### 為什麼不能「部署完看一下圖表」

很多團隊的 canary 是這樣做的：把新版本推到一台機器，工程師盯著 dashboard 十分鐘，「看起來沒事」就繼續。這有三個問題。

第一是**訊號被稀釋**。SRE Workbook 舉過一個例子：如果 canary 只拿到 5% 流量，而新版本有 20% 的請求失敗，整體錯誤率只會上升約 1%，混在平常的波動裡很難被看出來。所以指標一定要**分開看 canary 與 control**，不能只看整體。

第二是 **before/after 比較的陷阱**。拿「部署後的錯誤率」和「部署前的錯誤率」比，看似合理，但時間本身會影響指標：晚上八點的流量和下午三點不同，週末和平日不同，外部金流商也可能剛好在那時候變慢。正確的做法是讓 canary 和 control **在同一段時間內並排比較**，兩者唯一的差別是版本。

第三是**人眼不是統計工具**。Control 組的錯誤率是 0.3%，canary 是 0.5%，這是新版本的問題，還是隨機波動？答案取決於樣本有多少。1,000 個請求裡多兩個錯誤可能只是運氣；100,000 個請求裡多出兩百個錯誤，幾乎可以確定是真的。

### 怎麼設計一次 canary

```text
                    ┌──────────────── 所有流量 100% ────────────────┐
                    │                                               │
                    ▼                                               ▼
   ┌──────────────────────────┐                     ┌──────────────────────────┐
   │ canary：新版本 v43        │                     │ 其餘：舊版本 v42           │
   │ 1% 流量                   │                     │ 98% 流量（不列入比較）      │
   └──────────────────────────┘                     └──────────────────────────┘
                    │                    ┌──────────────────────────┐
                    │                    │ control：舊版本 v42        │
                    │                    │ 1% 流量（大小與 canary 相同）│
                    │                    └──────────────────────────┘
                    │                                  │
                    └────────────► 比較 ◄──────────────┘
                     同時段、同大小、同類流量；只差版本
                     錯誤率（統計檢定）、p99 延遲、資源、業務指標
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
                  PASS             WAIT              FAIL
               擴大到下一階段     樣本不足，延長觀察   自動回退 canary
```

這張圖的重點在中間那一塊：control 是從舊版本中特別劃出的一群，**大小與 canary 相同**。SRE Workbook 的例子是拿 canary 和其餘流量比較，這在指標已經分開統計時也可行；但許多自動化 canary 分析的實務（例如 Spinnaker 搭配 Kayenta 的做法）會另外啟動一組和 canary 同大小的舊版本 baseline。原因是拿 1% 的 canary 去和 99% 的其他機器比，看似樣本更多，其實會引入偏差：小群機器有自己的快取暖機狀態、自己的負載平衡分配，與一大片舊機器的平均表現天生就不一樣。讓兩邊同樣大小、同樣剛啟動，比較才公平。底下三個結果中，「WAIT」最常被忽略：樣本不夠時，正確的反應是延長觀察，而不是假設沒事。

設計 canary 時要決定幾件事：

**一、選什麼指標。** SRE Workbook 提出三個條件：指標要能**反映問題**（最好從 SLI 開始，第 32 章），要具有**代表性**（門檻太嚴會一直誤判、太鬆會放過壞版本；像原始 CPU 使用率這種很吵的指標，會讓大家開始忽略 canary），以及要**可歸因**（指標的變化要能歸因於這次變更，而不是同一台機器上的其他程式或共用的基礎設施）。它建議指標不要太多，大約一打以內。Harbor 的 checkout canary 看的是：HTTP 5xx 比例、p99 延遲、process 重啟次數、記憶體成長斜率，以及一個業務指標「結帳成功率」。業務指標常被忘記，但四月事故的錯誤正是「系統沒有報錯，只是拒絕結帳」。

**二、canary 多大、跑多久。** Canary 要大到能在合理時間內累積足夠樣本，又小到出事時傷害有限。它也要跑得夠久，最好涵蓋一次流量高峰，因為很多效能問題只在高負載下出現。對每天部署多次的團隊，canary 不能拖太久；對每週部署一次的團隊，可以放得比較久。SRE Workbook 也建議一次只跑一個 canary，同時跑多個時，指標的變化就難以歸因。

**三、分階段擴大。** 前幾個小階段只能依賴最明顯的訊號，例如 crash 與請求失敗；到了較大的階段，樣本多了，才能看出細微的延遲退化或業務指標變化。這是 **gradual canary**（漸進式 canary）的意義。

**四、與 SLO 的關係。** Canary 消耗的 error budget 受限於它的流量比例與時間，這正是它便宜的原因。但 canary 和 control 共用依賴，可能互相影響（例如新版本把共用的資料庫拖慢，control 也一起變慢，兩邊比起來「沒差」）。所以除了相對比較，也要同時看絕對的 SLO 指標。

### 統計比較的直覺

錯誤率是比例，可以用**雙比例 z 檢定**判斷「canary 比 control 高」是否可能只是隨機波動：

```text
p_c = canary 錯誤數 / canary 請求數        p_b = control 錯誤數 / control 請求數
p   = (兩邊錯誤數總和) / (兩邊請求數總和)   ← 假設兩邊其實一樣時的共同錯誤率
SE  = √( p(1−p) × (1/n_c + 1/n_b) )         ← 這麼多樣本下，差距的自然波動有多大
z   = (p_c − p_b) / SE

例：n_c = n_b = 3,000，canary 22 個錯誤（0.73%），control 4 個錯誤（0.13%）
    p = 26 / 6,000 ≈ 0.0043，SE ≈ √(0.0043 × 0.9957 × 2/3,000) ≈ 0.0017
    z ≈ (0.0073 − 0.0013) / 0.0017 ≈ 3.5
    單尾 p-value ≈ 0.0002：如果兩版本真的一樣，看到這麼大差距的機率約萬分之二
```

p-value 很小，代表差距不太可能只是運氣。但「統計上顯著」不等於「值得在意」：樣本極大時，0.001% 的差距也會顯著。所以實務上的判斷要同時滿足兩個條件：差距**顯著**，而且差距**大到有業務意義**（例如超過 0.1 個百分點）。延遲則通常比較百分位數，或用不假設分佈形狀的 Mann-Whitney U 檢定比較兩組延遲。Kayenta 這類工具做的事情本質上就是這樣：對每個指標做統計比較，再把結果彙總成一個分數。

> [!warning] 常見誤解
> 「Canary 沒有錯誤，所以新版本是好的。」低流量時，canary 很可能在觀察期間一個錯誤都沒碰到。零錯誤加上一百個請求，什麼都證明不了。Gate 必須有**最小樣本數**，樣本不夠就延長觀察，或改用 synthetic 流量補足。

## 29.7 Rollback 與 roll forward

### Rollback 優先

出事時有兩個選擇：**rollback**（回退到上一個已知良好的版本），或 **roll forward**（往前修，部署一個包含修正的新版本）。Harbor 的預設規則是：**先 rollback，再 debug**。理由是 rollback 的結果是已知的，上一個版本昨天還在正常服務；roll forward 的修正是剛寫的，沒有經過 canary，可能修好也可能帶來新問題，而且在壓力下寫程式最容易出錯。

Rollback 要能用，必須事先準備好三件事：上一版的 artifact 還在、pipeline 能用一個指令完成回退（而且平常就練習過），以及新舊版本能**互相相容**。最後一點最容易被忽略。Harbor 四月的事故就是因為新版本做了一個舊版本無法接受的改變：刪掉一個舊版仍在讀取的欄位。

### 什麼時候 roll forward 才是對的

有些情況 rollback 救不了，甚至會讓事情更糟：

- **資料已經被新格式寫入**。新版本把訂單以新格式寫進資料庫或訊息佇列，舊版本讀不懂。回退後，舊版本面對這些新資料會出錯。
- **外部副作用已經發生**。新版本寄出了錯誤的通知、向金流商送出了請求，回退程式不會把信收回來或把款退回去，需要的是補償動作。
- **修正非常小、pipeline 夠快**。如果問題是一個明顯的設定錯字，而 pipeline 從 commit 到 canary 只需要十分鐘，roll forward 可能比 rollback 更乾淨。但這必須是團隊事先同意的例外，不是值班者在凌晨兩點的直覺。
- **安全漏洞修補**。回退會重新打開剛修補的漏洞。

判斷原則是：**rollback 是預設，roll forward 要有理由**。這也是為什麼每次變更都應該在設計時就問「如果要回退，會發生什麼事？」，而不是等到出事才發現回不去。

### 設定變更也是變更

Harbor 的事故中，有不少起因根本不是程式碼，而是設定：timeout 從 2 秒改成 200 毫秒、連線池上限少打一個零、一個 flag 對 100% 使用者打開。設定變更應該和程式碼走一樣的路：版本控制、code review、逐步 rollout、可以一鍵回退。SRE 書第 1 章提到，Google 的經驗是約 70% 的 outage 來自對線上系統的變更；設定與 flag 也屬於變更，不能因為「只是改一個值」就跳過流程。

## 29.8 Schema migration：expand／contract 讓資料庫也能回退

### 為什麼資料庫是 rollback 的最大障礙

程式可以換回上一版，資料不行。部署新版本的時候，舊版本與新版本會**同時存在一段時間**：rolling update 期間有一半機器跑舊版、一半跑新版；canary 期間 1% 跑新版；rollback 之後又全部回到舊版。在這整段時間裡，兩個版本讀寫的是同一個資料庫。所以任何 schema 變更都必須滿足：**新舊兩個版本的程式都能在新 schema 上正常運作**。

Harbor 四月的 migration 違反了這個條件：它在同一次部署中新增 `coupon_id`、搬資料、刪除 `coupon_code`，舊程式一碰到新 schema 就壞掉。

### Expand／contract 的步驟

**Expand／contract**（擴張／收縮，也叫 parallel change）把一個破壞性的 schema 變更，拆成好幾個各自可以安全部署、各自可以回退的小步驟。以把 `coupon_code`（字串）換成 `coupon_id`（外鍵）為例：

```text
步驟  資料庫 schema                 程式行為                            可以回退到上一步嗎
───  ───────────────────────────  ───────────────────────────────────  ──────────────────
 1   新增 coupon_id（可為 NULL）      程式不變                             可以（新欄位沒人用）
     ← expand
 2   兩個欄位並存                    寫入時同時寫 code 與 id；讀取仍用 code   可以（舊版只讀 code）
 3   兩個欄位並存                    背景工作把歷史訂單補上 coupon_id       可以（只是多了資料）
     （backfill）                    並驗證兩欄一致
 4   兩個欄位並存                    讀取改用 id（用 flag 逐步切換）          可以（關 flag 改回讀 code）
 5   兩個欄位並存                    停止寫入 code                        可以，但要先恢復雙寫
 6   刪除 coupon_code               ← contract                           不行，所以最後才做，
                                                                      並等觀察期結束
```

這張表從上往下讀，每一列都是一次獨立的部署，中間可以隔幾天。前五步都可以回退，因為在任何一個時間點，資料庫裡都同時保存著新舊兩種格式，正在運作的任何一個版本都找得到自己需要的欄位。真正不可逆的只有第 6 步，而它被刻意放到最後：等所有程式都已經不讀 `coupon_code`、觀察期內沒有問題、相關報表與資料管線也確認改用新欄位之後才做。

這個流程看起來慢，但每一步都很小、很無聊，任何一步出事的影響都有限。對比之下，四月那次「一步到位」的 migration 讓 Harbor 停擺了三個小時。

### 大表變更的實務問題

即使是第 1 步的「新增欄位」，在大型資料表上也可能出事。有些資料庫在某些 `ALTER TABLE` 操作時會鎖住整張表，幾千萬筆訂單的表一鎖就是幾分鐘，所有寫入都會卡住。實務上的對策包括：先確認你的資料庫版本對該操作是否支援線上變更、使用 gh-ost 或 pt-online-schema-change 這類線上 schema 變更工具、在離峰時段執行，以及 backfill 時分批處理並限制速度，避免把資料庫的 I/O 吃滿。Migration 也應該像程式碼一樣經過 review，review 時的第一個問題是：「這一步部署到一半時，舊版本還能跑嗎？」

## 29.9 用 DORA 指標檢查 delivery 是否真的變好

Harbor 花了一季改造 delivery 流程，Kevin 需要知道這些投資有沒有效果。第 14 章介紹過 **DORA** 指標，它們來自 DevOps Research and Assessment 多年的研究，正好量測本章的主題：

| 指標 | 量什麼 | 本章哪個做法影響它 |
|---|---|---|
| **Deployment frequency** | 多常部署到 production | 小批次、自動化 pipeline |
| **Lead time for changes** | 從 commit 到 production 要多久 | 移除 release night、自動 gate |
| **Change failure rate** | 部署後需要補救（rollback、hotfix）的比例 | Canary、dark launch、expand／contract |
| **Failed deployment recovery time** | 部署造成的失敗要多久恢復 | 一鍵 rollback、flag kill switch |

傳統上前兩個被歸為速度（throughput），後兩個被歸為穩定性（stability）。DORA 研究的一個重要結論是：這兩組指標**不是此消彼長**，表現好的團隊通常在兩方面都好。這和「faster is safer」是同一件事：小批次讓部署更頻繁，也讓每次失敗更小、更容易恢復。DORA 2024 年的報告另外加入了 **rework rate**（重工率），衡量有多少部署是因為 production 出了問題而做的計畫外部署，可以補足 change failure rate 只看「部署後立即需要介入」的盲點。DORA 目前的五指標模型也調整了分組：把 failed deployment recovery time 歸到 throughput，把 change failure rate 與 rework rate 歸為 instability。分組怎麼畫不影響本章的重點：五個數字要一起看。

這些指標是用來觀察趨勢、找出瓶頸的，不是用來比較個人或團隊排名的。第 14 章談過 Goodhart's law：一旦把 deployment frequency 當成 KPI 考核，團隊就會開始把一個變更拆成十次沒有意義的部署。

下面的程式以 checkout 單一服務的部署紀錄為例，算出四個指標（整個 Harbor 有二十多個服務，全公司的部署次數是各服務相加）。

```python
from datetime import datetime, timedelta
from statistics import median

# (commit 時間, 部署到 production 時間, 是否造成需要補救的失敗, 恢復所花分鐘)
T = datetime.fromisoformat
before = [  # 雙週大版本：每次打包幾十個 commit
    (T("2025-03-03 10:00"), T("2025-03-13 22:00"), True, 190),
    (T("2025-03-17 15:00"), T("2025-03-27 22:00"), False, 0),
    (T("2025-03-31 11:00"), T("2025-04-10 22:00"), True, 240),
    (T("2025-04-14 09:00"), T("2025-04-24 22:00"), False, 0),
]
after = []  # 導入 CD 與 canary 後：每天多次小部署
start = T("2025-09-01 09:00")
for i in range(40):
    commit = start + timedelta(hours=i * 7)
    failed = i in (6, 23, 31)
    after.append((commit, commit + timedelta(hours=3, minutes=10 * (i % 4)), failed, 12 if failed else 0))


def dora(name, deploys, days):
    lead = median((d - c).total_seconds() / 3600 for c, d, _, _ in deploys)
    failures = [m for _, _, f, m in deploys if f]
    print(f"{name}")
    print(f"  deployment frequency : {len(deploys) / days * 7:5.1f} 次／週")
    print(f"  lead time (median)   : {lead:5.1f} 小時")
    print(f"  change failure rate  : {len(failures) / len(deploys):5.0%}")
    print(f"  recovery time (median): {median(failures):5.0f} 分鐘")


dora("導入前：雙週大版本", before, days=56)
dora("導入後：CD + canary", after, days=12)
```

執行結果：

```text
導入前：雙週大版本
  deployment frequency :   0.5 次／週
  lead time (median)   : 251.5 小時
  change failure rate  :   50%
  recovery time (median):   215 分鐘
導入後：CD + canary
  deployment frequency :  23.3 次／週
  lead time (median)   :   3.2 小時
  change failure rate  :    8%
  recovery time (median):    12 分鐘
```

資料是示意用的，但形狀很典型。導入前每次發布都包含兩週的變更，lead time 是以「這批變更裡第一個 commit」為起點算的，所以長達十天；四次發布中有兩次需要補救，每次恢復都要三、四個小時，因為要從幾十個變更裡找兇手，rollback 還可能碰到 schema 問題。導入後，lead time 降到幾小時；失敗率下降，因為 canary 在 1% 流量時就攔下了大部分問題；恢復時間只剩十幾分鐘，因為回退只是把 canary 的流量切回去。真實計算時，lead time 應該對**每個 commit** 計算後取中位數，而不是每次部署取一個值；失敗的判定也要有一致的定義，例如「部署後 24 小時內發生 rollback、hotfix 或觸發事故」。

## 29.10 動手寫：一條會自己踩煞車的漸進式 rollout

下面的程式模擬 29.6 節的 canary 分析：新版本依序拿到 1%、5%、25%、50% 的流量，每個階段都與大小相同的 control 並排比較。判斷規則有三個：樣本不足就延長觀察；錯誤率要顯著較高，而且差距超過 0.1 個百分點才判失敗；p99 延遲比 control 高 15% 以上也判失敗。

```python
import math
import random
from dataclasses import dataclass

random.seed(29)


@dataclass
class Version:
    name: str
    error_rate: float        # 模擬用的「真實」錯誤率；現實中你看不到這個數字
    median_ms: float         # 模擬用的延遲中位數


def serve(v: Version, n: int):
    """模擬某版本處理 n 個請求，回傳 (錯誤數, 延遲列表)。"""
    errors = sum(random.random() < v.error_rate for _ in range(n))
    lat = [random.lognormvariate(math.log(v.median_ms), 0.6) for _ in range(n)]
    return errors, lat


def p99(xs):
    s = sorted(xs)
    return s[int(0.99 * (len(s) - 1))]


def canary_worse_p_value(e_c, n_c, e_b, n_b):
    """單尾雙比例 z 檢定：canary 錯誤率是否顯著高於 baseline。"""
    pooled = (e_c + e_b) / (n_c + n_b)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n_c + 1 / n_b))
    if se == 0:
        return 1.0
    z = (e_c / n_c - e_b / n_b) / se
    return 0.5 * math.erfc(z / math.sqrt(2))


def judge(e_c, lat_c, e_b, lat_b, min_n=3000):
    n_c, n_b = len(lat_c), len(lat_b)
    if n_c < min_n:
        return "WAIT", f"樣本 {n_c} < {min_n}，延長觀察"
    reasons = []
    p = canary_worse_p_value(e_c, n_c, e_b, n_b)
    gap = e_c / n_c - e_b / n_b
    if p < 0.01 and gap > 0.001:          # 顯著，而且差距大到值得在意
        reasons.append(f"錯誤率 {e_c / n_c:.2%} vs {e_b / n_b:.2%}（p={p:.1e}）")
    if p99(lat_c) > p99(lat_b) * 1.15:
        reasons.append(f"p99 {p99(lat_c):.0f}ms vs {p99(lat_b):.0f}ms")
    return ("FAIL", "；".join(reasons)) if reasons else ("PASS", f"錯誤率差 {gap:+.2%}，p={p:.2f}")


def rollout(new: Version, old: Version, per_window=100_000):
    print(f"== 發布 {new.name} ==")
    for frac in (0.01, 0.05, 0.25, 0.50):
        e_c = e_b = 0
        lat_c, lat_b = [], []
        for window in range(1, 5):                     # 每階段最多觀察 4 個時間窗
            n = int(per_window * frac)                 # canary 拿到的流量
            ec, lc = serve(new, n)
            eb, lb = serve(old, n)                     # baseline：同樣大小的舊版本
            e_c, e_b = e_c + ec, e_b + eb
            lat_c += lc
            lat_b += lb
            verdict, why = judge(e_c, lat_c, e_b, lat_b)
            print(f"  {frac:>4.0%} 第{window}窗  {verdict:4}  {why}")
            if verdict != "WAIT":
                break
        if verdict == "FAIL":
            print(f"  → 自動 rollback，影響範圍只有 {frac:.0%} 流量\n")
            return
        if verdict == "WAIT":
            print("  → 觀察時間用完仍無結論，停下來交給人判斷\n")
            return
    print("  → 100% 上線\n")


stable = Version("v41（線上版本）", 0.003, 120)
rollout(Version("v42 正常版", 0.003, 122), stable)
rollout(Version("v43 錯誤率升高", 0.009, 120), stable)
rollout(Version("v44 長尾變慢", 0.003, 150), stable)
```

執行結果：

```text
== 發布 v42 正常版 ==
    1% 第1窗  WAIT  樣本 1000 < 3000，延長觀察
    1% 第2窗  WAIT  樣本 2000 < 3000，延長觀察
    1% 第3窗  PASS  錯誤率差 -0.13%，p=0.83
    5% 第1窗  PASS  錯誤率差 -0.18%，p=0.96
   25% 第1窗  PASS  錯誤率差 -0.06%，p=0.92
   50% 第1窗  PASS  錯誤率差 -0.08%，p=0.99
  → 100% 上線

== 發布 v43 錯誤率升高 ==
    1% 第1窗  WAIT  樣本 1000 < 3000，延長觀察
    1% 第2窗  WAIT  樣本 2000 < 3000，延長觀察
    1% 第3窗  FAIL  錯誤率 0.73% vs 0.13%（p=2.0e-04）
  → 自動 rollback，影響範圍只有 1% 流量

== 發布 v44 長尾變慢 ==
    1% 第1窗  WAIT  樣本 1000 < 3000，延長觀察
    1% 第2窗  WAIT  樣本 2000 < 3000，延長觀察
    1% 第3窗  FAIL  p99 669ms vs 494ms
  → 自動 rollback，影響範圍只有 1% 流量
```

逐段解讀：

1. **`serve` 是假的 production。** 每個版本有一個「真實」錯誤率與延遲分佈，這是模擬才看得到的上帝視角。真實世界裡你只看得到觀測值，所以才需要統計。延遲用 lognormal 分佈產生，因為真實延遲通常是右偏的：大部分請求很快，少數很慢。
2. **每一階段都有同樣大小的 control。** `serve(old, n)` 和 `serve(new, n)` 使用同樣的 `n`，對應 29.6 節「control 與 canary 同大小、同時段」的原則。真實系統中，這通常是由負載平衡器或 service mesh 把等量流量分給兩組新啟動的機器。
3. **`WAIT` 是最重要的一行。** 1% 階段每個時間窗只有 1,000 個請求，以 0.3% 的錯誤率來算，平均只有 3 個錯誤，任何比較都沒有意義。程式選擇延長觀察，累積到 3,000 個請求才判斷。真實系統中，最小樣本數取決於你想偵測多小的退化：想偵測的差距越小，需要的樣本越多。
4. **v43 在第一個階段就被攔下。** 錯誤率 0.73% 對 0.13%，p-value 約萬分之二，差距也超過 0.1 個百分點。注意 control 那一段實際觀察到的錯誤率（0.13%）比它的真實值（0.3%）低，這就是樣本不大時的隨機波動；但兩者的差距大到不可能用運氣解釋。整個事件只影響了 1% 的流量，對照四月 release night 的 100%。
5. **v44 沒有任何錯誤，卻被延遲攔下。** 它的中位數只從 120 ms 變成 150 ms，用平均值看圖時很容易忽略，但 p99 從約 490 ms 升到約 670 ms。第 32 章說過延遲要看尾端，canary 也一樣。
6. **v42 的錯誤率差是負的，p-value 接近 1。** 這代表 canary 沒有比較差，可以前進。到了 5% 之後的階段，每個時間窗的樣本已經足夠，所以第一個時間窗就能做出判斷，rollout 會自然加速。

這個程式刻意簡化了幾件事：沒有處理多個指標同時比較時誤判機率會增加的問題（multiple comparisons），沒有考慮流量的時段變化，也沒有在 FAIL 之後做真正的回退動作。真實的 canary 分析系統會在這些地方做更多處理，但判斷的骨架相同：**同時段同大小的比較、足夠的樣本、顯著且有意義的差距、失敗就自動停**。

## 29.11 Trade-offs 與 Failure Modes

| 做法 | 什麼情況下會失敗 | 具體情境 | 對策 |
|---|---|---|---|
| Canary 只看整體指標 | 局部問題被平均掉 | 新版本只在 Android 舊版 app 送來的請求格式上出錯，占 canary 流量的 3%，整體錯誤率幾乎不動 | 依平台、地區、重要客群切分指標；關鍵使用者旅程（critical user journey，CUJ，例如「搜尋→加入購物車→結帳」）單獨看 |
| Canary 流量不具代表性 | 樣本裡沒有會出事的那種請求 | Canary 被分配在流量最低的可用區，從來沒有碰到企業賣家的批次上架 | 按使用者隨機分流，canary 涵蓋流量高峰，必要時補上 synthetic 流量 |
| 自動 rollback 太敏感 | 部署反覆被回退，團隊開始關掉 gate | 用原始 CPU 使用率當指標，每次快取暖機就超標 | 只挑能反映使用者問題的指標，用統計檢定與最小差距門檻 |
| 把 rollback 當萬靈丹 | 回退後資料或外部副作用不相容 | 新版本已向物流商送出新格式的出貨單，回退後物流商回呼的資料舊版讀不懂 | 協定與 schema 走 expand／contract；設計補償動作；變更前就寫好回退計畫 |
| Feature flag 永遠不刪 | 組合爆炸、重用舊名稱造成意外 | 三年累積 200 個 flag，某個測試環境的 flag 組合與 production 不同，bug 只在 production 出現 | Flag 有 owner 與到期日，CI 追蹤過期 flag，名稱禁止重用 |
| Blue/green 忽略共用資料庫 | 切換瞬間資料不相容 | Green 環境的 migration 改了欄位，blue 環境還在寫舊格式 | 兩個環境必須能同時運作在同一份 schema 上 |
| 只追 deployment frequency | 數字好看，風險沒變 | 團隊為了達成目標把一個變更拆成十次部署，每次都沒有 canary | 四個 DORA 指標一起看，並搭配 rework rate 與事故檢討 |

## 29.12 AI 時代：什麼變了？

AI 從三個方向改變 delivery 的工作。

**第一，變更的數量與速度上升了。** AI coding agent 讓一個工程師一天能產出的 PR 數量明顯增加，第 21 章談過的大規模變更也更容易發動。這讓本章的機制變得更重要而不是更不重要：每個變更仍然要小、要經過 canary、要能回退。Harbor 對 agent 產生的 PR 採用和人類一樣的 pipeline，沒有捷徑；另外要求 agent 在 PR 描述中寫出「這個變更的回退方式」與「上線後該觀察哪些指標」，reviewer 會檢查這兩段是否合理。

**第二，AI 可以讓 canary 分析與 rollout 更聰明，但不能取代確定性的 gate。** Canary 失敗時，值班者最花時間的是找原因：哪個指標退化、哪類請求出錯、和這次變更的哪段程式碼有關。AI 適合做這種跨 log、trace、diff 的關聯分析，並用自然語言整理成摘要。但「要不要擴大 rollout」的判斷，Harbor 仍然交給版本化、可重現、可稽核的規則（像 29.10 節的程式）。AI 的判斷是機率性的，同樣的輸入可能給出不同的結論，而且很難事後解釋為什麼放行了一個壞版本。

**第三，AI 產品本身的變更也是變更。** Harbor 的 AI 客服 agent 有自己的 delivery 問題：換模型版本、改 system prompt、更新知識庫、調整 agent 可以呼叫的工具，都可能改變行為，而且不會出現任何錯誤碼。這類變更應該走同一套流程：先跑離線 eval（第 25 章），再以 flag 小範圍開放，canary 階段除了看錯誤率與延遲，也要看品質類指標，例如轉人工比例、抽樣品質分數、退款金額分佈是否異常。退款這類有真實金錢後果的工具，新版本在 canary 期間應該有更低的單筆上限。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 依 diff 與 ownership 產生 release 風險摘要：影響哪些服務、哪些 CUJ、該看哪些指標 | 摘要只是輸入；高風險變更（付款、權限、schema）仍需指定 owner 核准 |
| Canary 失敗時，關聯 log、trace、指標與 diff，提出可能原因與對應的程式碼位置 | 結論必須附上可重現的查詢；不能只採信文字描述 |
| 草擬 expand／contract 的 migration 步驟與每一步的回退方式 | Migration 的 review 必須由熟悉資料的人確認「部署到一半時舊版本還能跑嗎」 |
| 掃描過期 feature flag，自動開 PR 刪除已全面開放的 flag 程式碼 | 刪除 flag 的 PR 經過一般的 canary 流程；ops toggle 與 kill switch 不在自動刪除範圍 |
| 在 shadow 模式下模擬 rollout 判斷，和實際的 gate 結果比較 | Promotion 與 rollback 的門檻由版本化 policy 執行，模型不能修改門檻 |
| 依已核准的 runbook 執行 rollback | Agent 使用專用身分與最小權限，動作有次數與時間上限，全程留下稽核紀錄 |

> [!ai] AI 提醒
> 不要讓 AI agent 擁有「修改 canary 門檻」或「跳過 gate」的權限。當 agent 的目標是「讓部署成功」時，最省力的路徑可能是放寬條件，而不是修好程式。Gate 的定義應該和程式碼一樣經過 review，agent 只能讀，不能改。

## 29.13 專家怎麼想

- **「這個變更要怎麼回退？」是第一個問題，不是最後一個。** 資深工程師在設計階段就問這個問題。如果答案是「回不去」，這個變更就需要被拆開，或者需要事先寫好補償計畫。
- **證據與曝光範圍要一起成長。** 1% 的 canary 只能證明「沒有大問題」；細微的退化要在更大的流量下才看得出來。所以 rollout 的每個階段看的指標應該不同，越後面看得越細。
- **讓 rollback 變成平凡的動作。** 如果 rollback 很少做，真正需要時就不會做，或做錯。一些團隊會定期在正常時段練習 rollback，確保流程、權限與 artifact 都還在。值班者按下 rollback 不應該需要任何人批准。
- **設定與 flag 也是程式碼。** 很多事故的觸發點是一個設定值，而不是一行程式。專家會檢查設定變更是否也有 review、canary 與回退。
- **Pipeline 的權限比任何個人都大，要當成 production 系統保護。** 問誰能改 pipeline 的定義、誰能跳過 gate、跳過時會留下什麼紀錄。
- **衡量流程，不衡量人。** DORA 指標拿來找瓶頸（是 review 太慢、測試太慢，還是 canary 太久），不是拿來排名團隊。

## 29.14 動手練習

1. 為 Harbor 的 checkout 服務寫一份 rollout 計畫：列出 1%、5%、25%、50%、100% 每個階段要看的指標、最少觀察時間、最小樣本數，以及哪些條件會觸發自動回退。
2. 修改 29.10 節的程式，加入一個「只在某類請求出錯」的版本（例如 5% 的請求屬於「舊版 app」，只有這類請求錯誤率上升到 10%）。觀察整體比較是否抓得到，再修改程式依請求類型分開比較。
3. 在同一支程式中，把 control 改成「其餘 99% 流量」而不是同大小的 1%，並讓新啟動的機器有 5 分鐘的暖機期延遲較高。比較兩種 control 設計的誤判情況。
4. 為「把 `users.phone` 欄位拆成 `country_code` 與 `phone_number`」設計 expand／contract 步驟，寫出每一步的 schema、程式行為，以及能否回退。
5. 從你手邊的專案（或公開的開源專案）找出最近十次部署，估算四個 DORA 指標。寫下你在定義「失敗」與「lead time 起點」時做了哪些選擇。
6. 盤點一個專案中的 feature flag，依 29.5 節的四類分類，找出應該刪除但還沒刪的 flag，並寫一個簡單的腳本列出超過 90 天沒有變更的 flag。

## 本章重點整理

- Continuous integration 讓主線隨時是綠的；continuous delivery 讓主線隨時可以發布；continuous deployment 讓通過所有 gate 的變更自動上線。三者是逐層疊加的承諾。
- Deploy（程式上機器）與 release（使用者看到新行為）是兩件事，feature flag、dark launch、canary 都是在拆開兩者。
- 「Faster is safer」：小批次讓每次部署的出錯機率、定位成本與回退範圍都變小，總體風險更低。
- Build once, promote many：同一個 artifact digest 依序晉升到各環境，環境差異用版本化設定注入。
- Release train 適合無法連續部署的產品（例如手機 app），關鍵紀律是列車不等人。
- Rolling update、blue/green、canary 的差別在於同時有多少使用者暴露在新版本下，以及回退有多快；progressive delivery 把它們與自動 gate 組合起來。
- Feature flag 需要 owner、到期日與清理機制；永久累積的 flag 會造成組合爆炸，重用舊 flag 可能釀成災難。
- Canary 要和同時段、同大小的 control 比較，指標要能反映問題、具代表性、可歸因，並分開看 canary 與 control。
- Canary 的判斷要有最小樣本數，錯誤率差距要統計上顯著且大到有業務意義；低流量時零錯誤什麼都證明不了。
- 出事時 rollback 是預設，roll forward 要有理由；資料格式、外部副作用與安全修補是 rollback 無法處理的典型情況。
- 新舊版本會同時存在，所以 schema 變更必須讓兩個版本都能運作；expand／contract 把破壞性變更拆成可回退的小步驟，不可逆的刪除放在最後。
- 設定與 flag 的變更也是 production 變更，應該走同樣的 review、rollout 與回退流程。
- DORA 的速度指標與穩定性指標不是此消彼長；它們用來找出流程瓶頸，不用來評比個人。
- AI 讓變更變多、分析變快，但 promotion 與 rollback 的門檻要由確定性的、版本化的規則執行；AI 產品的模型與 prompt 變更也要走同一套 rollout。
- 本章讓變更能安全地「進入」production；但版本上線之後，憑證會過期、磁碟會滿、依賴會變慢，這些都不是 pipeline 能攔下的。誰負責讓服務在 production 裡持續可靠，以及這份工作怎麼不把人淹沒，是第 30 章 SRE 要回答的問題。

## 延伸問答

> [!question]- Q1. Continuous delivery 和 continuous deployment 差在哪裡？一個團隊有可能需要前者但不需要後者嗎？
> Continuous delivery 保證主線上每個版本隨時可以安全發布，發布與否只需要一個決定；continuous deployment 則是通過所有 gate 的變更會自動部署，沒有人工按鈕。前者是能力，後者是在這個能力上選擇的一種政策。
>
> 很多團隊只需要前者。手機 app 必須經過商店審核，無法每個 commit 都上線；受監管的產業可能要求每次發布有指定人員簽核；有些 B2B 產品的客戶要求固定的維護時段。這些團隊仍然應該讓主線隨時可發布，因為這代表緊急修補可以在幾小時內出貨，而不是要等下一個大版本。《Software Engineering at Google》也提到，大部分價值來自「能夠持續部署」的那套結構，而不是實際部署的頻率。

> [!question]- Q2. 為什麼 canary 的對照組應該和 canary 同樣大小，而不是拿全部舊機器當對照？
> 直覺上對照組越大、樣本越多，比較越準確，但真正的問題是偏差，不是樣本數。Canary 的機器通常剛啟動，快取是冷的、JIT 還沒暖好、連線池剛建立；一大片已經跑了好幾天的舊機器沒有這些狀態。拿兩者比較，你量到的差距有一部分來自「新啟動」而不是「新版本」。
>
> 讓 control 和 canary 同樣大小、同時啟動、接收同類型的流量，兩組之間唯一的差別就是版本，比較的結果才能歸因於這次變更。SRE Workbook 強調指標要可歸因，就是這個意思。另外，兩組同大小也讓統計檢定更簡單、更好解釋。

> [!question]- Q3. 你是 Harbor 的值班者。凌晨一點，新版本的 canary 在 5% 階段失敗，但開發者在群組說「我知道是哪一行，十分鐘就能 roll forward 修好」。你會怎麼做？
> 預設應該先 rollback。Canary 的回退通常只是把 5% 的流量切回舊版本，結果已知、速度很快；roll forward 的修正是剛在凌晨寫好的，沒有經過 review 與 canary，可能修好，也可能帶進新問題。先止血，再修復，是事故處理的基本順序（第 44 章）。
>
> 回退之後，開發者可以在不受時間壓力的情況下修正，讓修正版本照正常流程重新走一次 canary。只有在 rollback 本身不可行時才考慮 roll forward，例如新版本已經寫入舊版本讀不懂的資料，或者回退會重新打開一個安全漏洞。如果團隊經常想在凌晨 roll forward，這是一個訊號：可能 canary 抓問題太晚，或者變更的設計讓回退很痛苦，值得在 postmortem 中討論。

> [!question]- Q4. 計算題：canary 與 control 各有 2,000 個請求，canary 有 9 個錯誤，control 有 4 個。這足以判斷新版本比較差嗎？
> Canary 錯誤率 0.45%，control 0.2%，看起來 canary 是兩倍多。共同錯誤率 p = 13 / 4,000 = 0.00325；標準誤 SE = √(0.00325 × 0.99675 × (1/2,000 + 1/2,000)) ≈ √(0.00324 × 0.001) ≈ 0.0018；z = (0.0045 − 0.002) / 0.0018 ≈ 1.39，單尾 p-value 約 0.08。
>
> 也就是說，如果兩個版本其實一樣，看到這麼大差距的機率約 8%，以常用的 1% 或 5% 門檻都不足以下結論。正確的反應是延長觀察、累積更多樣本，而不是直接放行或直接回退。這個例子也說明為什麼人眼看「兩倍」很容易被誤導：錯誤數太少時，比例的波動非常大。

> [!question]- Q5. 有人說「我們有 feature flag，所以不需要 canary」。這句話哪裡有問題？
> Feature flag 控制的是被它包住的那段程式碼，canary 驗證的是整個新版本。新版本除了新功能，還包含依賴套件的升級、編譯器或執行環境的變化、共用程式碼的重構、設定的改動。這些都不在 flag 的保護範圍內。如果新版本在啟動時就 crash、記憶體洩漏，或者共用的序列化邏輯出錯，關掉 flag 毫無幫助。
>
> 反過來，canary 也不能取代 flag：canary 通過後，新版本跑在所有機器上，但新功能可能需要依使用者群體逐步開放、做 A/B 實驗，或在高峰時段能立即關閉。兩者回答的是不同的問題：canary 問「這個 binary 安全嗎」，flag 問「這個行為該讓誰看到」。成熟的團隊兩者都用，而且 flag 的變更本身也逐步 rollout。

> [!question]- Q6. 為什麼「刪除舊欄位」要放在 expand／contract 的最後一步，而且要等一段觀察期？
> 因為它是整個流程中唯一不可逆的步驟。在刪除之前，資料庫同時保存新舊兩種格式，任何一步出問題都可以回退到上一步：關掉讀新欄位的 flag、恢復雙寫，資料都還在。一旦刪除，舊欄位的資料就消失了，任何還依賴它的東西都會壞掉，而且只能從備份還原。
>
> 觀察期的目的是找出你不知道的依賴者。除了主程式，舊欄位可能還被報表查詢、資料管線、客服後台、另一個團隊的批次工作讀取，這是第 5 章 Hyrum's Law 在資料庫上的版本。實務上可以在刪除前先把欄位改名或撤銷讀取權限一段時間，觀察有沒有東西因此報錯，再真正刪除。

> [!question]- Q7. Harbor 想讓 AI agent 負責「看 canary 結果並決定要不要擴大 rollout」。你會怎麼設計這件事？
> 我會把「判斷」與「解釋」分開。擴大或回退的決定由確定性的規則做出：版本化的指標清單、最小樣本數、統計檢定與門檻，同樣的輸入永遠得到同樣的結果，事後可以重現與稽核。Agent 負責的是規則之外的工作：canary 失敗時關聯 log、trace 與 diff，找出可能的原因；canary 結果邊界模糊（例如判為 WAIT 太久）時，整理資訊給人判斷。
>
> 導入時可以先讓 agent 以 shadow 模式運作：它對每次 rollout 給出建議，但不執行，事後和實際結果比較，量測它的建議準確度與誤判類型。即使之後授權 agent 執行 rollback，它也應該使用專用身分、只能執行已核准的 runbook 動作、不能修改門檻或跳過 gate，所有動作留下紀錄。擴大 rollout 的權限比回退的權限風險更高，應該更晚才考慮授權。

> [!question]- Q8. 面試題：DORA 的四個指標中，你認為哪一個最容易被誤用？為什麼？
> 很多人會說 deployment frequency，因為它最容易灌水：把一個變更拆成很多次無意義的部署，數字就變好看，但風險與使用者價值都沒有變。一旦它成為考核目標，Goodhart's law 就會發生作用。
>
> Change failure rate 也很容易被誤用，因為「失敗」的定義有彈性。如果團隊被要求降低失敗率，最簡單的方法是把 rollback 重新命名為「計畫內的調整」，或者乾脆不 rollback、默默 roll forward。DORA 2024 年加入的 rework rate 可以補上這個盲點：它計算因為 production 出問題而做的計畫外部署，默默 roll forward 的 hotfix 也會被算進去。好的回答會強調：四個指標要一起看，它們描述的是系統與流程，不是個人績效；定義要事先寫清楚並保持一致；最重要的用途是找出瓶頸，例如發現 lead time 主要卡在 code review 等待，而不是用來比較團隊排名。

## 延伸閱讀

- [Software Engineering at Google — Continuous Delivery](https://abseil.io/resources/swe-book/html/ch24.html)：Google 的 CD 慣用法：flag 保護、release train、「faster is safer」與「ship only what gets used」。
- [Site Reliability Engineering — Release Engineering](https://sre.google/sre-book/release-engineering/)：hermetic build、release 分支與 cherry-pick、設定管理的幾種做法。
- [Site Reliability Engineering — Reliable Product Launches](https://sre.google/sre-book/reliable-product-launches/)：漸進式 rollout 與 launch checklist，第 46 章會再展開。
- [The Site Reliability Workbook — Canarying Releases](https://sre.google/workbook/canarying-releases/)：canary 的定義、指標選擇的條件、before/after 比較的陷阱與 canary 流量比例的取捨。
- [DORA](https://dora.dev/)：DORA 指標的定義、研究報告與自我評估工具。
