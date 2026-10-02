---
chapter: 26
title: Hermeticity、Flakiness 與 Coverage 陷阱
part: 4
---

# 第 26 章　Hermeticity、Flakiness 與 Coverage 陷阱

> [!abstract] 本章地圖
> **核心問題**：測試要能讓人信任，紅燈必須代表「程式有問題」、綠燈必須代表「這些行為被檢查過」；什麼會破壞這兩件事，又要怎麼把信任找回來？
>
> **你會學到**：
> - 說出 hermetic test 的定義，並把時間、亂數、網路、檔案、共享狀態等隱藏輸入一一變成顯式輸入
> - 辨認 flaky test 的常見成因，並用重跑與統計量化 flaky 率
> - 算出小小的 flaky 率如何在大型 suite 中放大，以及自動重試如何掩蓋真正的 race condition
> - 設計一套 quarantine 與修復流程，讓 flaky test 有 owner、有期限、不會永遠離開閘門
> - 正確使用 coverage：知道它能說明什麼、不能說明什麼，並用 mutation score 補上它的盲點
> - 管理測試資料：fixture、builder、隔離、清理與個資保護
>
> **前置知識**：第 22 章（test size）、第 23 章（unit test 與 mutation testing 簡介）、第 25 章（larger tests 與 SUT）
>
> **對應原書**：SWE 第 11 章〈Testing Overview〉、第 14 章〈Larger Testing〉

## 26.1 故事：重跑三次就綠了

Harbor 成立第二年的耶誕節前，seller 團隊和幾位台灣職人合辦了一場「職人聯名」限時快閃，其中一檔限量商品是一款手作陶杯，只有 100 個。開賣後三分鐘就賣完了，系統顯示售出 107 個。倉庫只有 100 個杯子，七位客人收到了道歉信與退款，社群上出現了「Harbor 超賣」的貼文。

負責 inventory 的 checkout 團隊很快找到原因：扣庫存的程式先讀取剩餘數量、判斷足夠後再寫回，兩個請求同時進來時，可能都讀到「剩 1 個」並都扣成功。這是典型的 race condition（競態條件：結果取決於多個執行緒或請求的先後順序）。讓人在意的是後續的發現：三週前修改這段程式的 PR，CI 上的 `test_inventory_reserve_concurrent` 失敗過一次。作者阿哲按了重跑，第二次通過，PR 就被 merge 了。

阿哲沒有做錯什麼特別的事，只是做了團隊裡每個人都在做的事。Harbor 的 CI 那時有一份「大家都知道」的清單：`test_checkout_e2e` 大概每二十次失敗一次、`test_coupon_expiry` 在午夜前後會壞、`test_search_rank` 偶爾因為順序不同而失敗。遇到這些測試失敗，標準動作就是重跑。CI 甚至設定了「失敗自動重試兩次」。`test_inventory_reserve_concurrent` 在那次 PR 上第一次失敗時，所有人的反應都和面對其他 flaky test 一樣。

同一個月，工程經理 Kevin 把 coverage 設成團隊目標：每個服務 line coverage 至少 85%。數字很快達標了。tech lead 美華在 review 時發現，有些新增的測試只是呼叫函式、不檢查任何結果。coverage 儀表板一片綠色，但這些測試什麼都不保護。

這兩件事是同一個問題的兩面：**測試信號失去了可信度**。紅燈不再代表「有問題」，因為大家知道它常常亂紅；綠燈也不再代表「有檢查」，因為 coverage 可以在沒有任何斷言的情況下達標。本章要處理的，就是如何讓測試的紅燈與綠燈重新有意義。

## 26.2 測試的價值在於信號可信

在談具體技術之前，先把問題說清楚。測試是一個**偵測器**：它的輸出（通過或失敗）應該反映程式是否正確。偵測器可能犯兩種錯：

```text
                    程式其實正確          程式其實有 bug
                 ┌──────────────────┬──────────────────┐
  測試通過（綠）  │  正確              │  漏報（false     │ ← coverage 陷阱：
                 │                   │  negative）       │   執行了但沒檢查
                 ├──────────────────┼──────────────────┤
  測試失敗（紅）  │  誤報（false      │  正確              │
                 │  positive）       │                   │
                 └──────────────────┴──────────────────┘
                          ↑
                   flaky test：同樣的程式，有時落在這一格
```

讀這張表時，看兩個錯誤的格子。左下是誤報：程式正確，測試卻失敗。flaky test 就是會隨機落進這一格的測試。右上是漏報：程式有 bug，測試卻通過。沒有斷言、只追求 coverage 的測試，以及被自動重試洗白的失敗，都會讓 bug 落進這一格。

這兩種錯會互相強化。誤報一多，工程師就學會忽略紅燈或直接重跑；重跑又把真正的 bug 變成漏報。SWE 一書第 11 章把這描述為信任的流失：當測試經常無故失敗，工程師對測試的信心下降，開始把失敗當成噪音，而這正是讓真正的 regression 溜過的時刻。

所以本章的目標可以用一句話表達：**讓每一次紅燈都值得調查，讓每一次綠燈都代表某些行為真的被檢查過**。前半部（hermeticity、flakiness、quarantine）處理誤報，後半部（coverage、mutation score、測試資料）處理漏報。

## 26.3 Hermetic test：把所有輸入都變成顯式的

### 什麼是 hermetic

**Hermetic test**（封閉測試）是指：測試的結果只取決於它明確宣告的輸入，也就是受測的程式碼、測試程式碼、固定版本的依賴與測試資料。它不依賴外部網路、不依賴執行的機器、不依賴執行的時間、不依賴其他測試是否先執行過。同一份輸入，在任何時候、任何機器上執行，都得到同樣的結果。

「Hermetic」原意是「密封的」，像一個密封的容器：外面的東西進不來，裡面的東西也不會漏出去影響別人。SWE 一書第 11 章的觀點是，所有測試都應該努力做到 hermetic：測試本身要帶著建立、執行與拆除自己環境所需的全部資訊，盡量不對外部環境做假設，例如不假設測試的執行順序、不依賴共用的資料庫。原書第 14 章討論 larger tests 時，則用 hermeticity 描述 SUT（system under test，受測系統）與外界隔離的程度：越 hermetic 的 SUT，越少暴露在並行與基礎設施造成的 flakiness 之下。

### 隱藏輸入：測試真正依賴的東西

大部分非 hermetic 的測試，不是作者故意的，而是測試依賴了一些作者沒意識到的**隱藏輸入**（hidden input）：

```text
        顯式輸入（寫在測試裡、版本控制中）
        ┌──────────────────────────────────┐
        │ 受測程式碼、測試程式碼、           │
        │ 固定版本的依賴、測試資料           │──┐
        └──────────────────────────────────┘  │
                                              ▼
        隱藏輸入（沒有宣告，卻影響結果）     ┌──────────┐
        ┌──────────────────────────────────┐ │          │
        │ 現在的時間、時區、locale            │─►│   測試   │──► 通過／失敗
        │ 亂數種子                           │ │          │
        │ 網路與外部服務                     │ └──────────┘
        │ 檔案系統上的既有檔案、固定 port     │      ▲
        │ 其他測試留下的狀態、執行順序        │──────┘
        │ 執行緒排程、機器負載                │
        │ 環境變數、已安裝的工具版本          │
        └──────────────────────────────────┘
```

上方的顯式輸入是你控制、也看得見的；下方的隱藏輸入同樣會進入測試，但你沒有宣告它們。只要任何一個隱藏輸入在兩次執行之間改變，同樣的程式碼就可能得到不同的結果。讓測試 hermetic 的過程，就是把下方的每一項，或者移除，或者搬到上方變成顯式輸入。

### 怎麼把隱藏輸入變成顯式

| 隱藏輸入 | 問題範例 | 讓它顯式的方法 |
|---|---|---|
| 時間 | 測試「優惠券今天到期」，跨過午夜就失敗 | 程式從注入的 clock 取得時間，測試用 fake clock 設定在固定時刻 |
| 時區與 locale | 開發者筆電是 Asia/Taipei，CI 是 UTC，日期差一天 | 測試明確設定時區；程式內部一律用 UTC，只在顯示時轉換 |
| 亂數 | 測試用全域亂數產生資料，失敗後無法重現 | 使用自己的 `random.Random(seed)`，失敗時印出 seed |
| 網路與外部服務 | 測試呼叫真實的匯率 API，對方維修時測試失敗 | 用 fake 或錄製的回應（第 24 章）；在沙盒中禁止對外連線 |
| 檔案系統 | 測試寫入 `/tmp/report.csv`，並行時互相覆蓋 | 每個測試使用自己的暫存目錄，結束後刪除 |
| 固定 port | 兩個測試都要開 8080，並行時其中一個失敗 | 讓作業系統分配空閒 port（綁定 port 0），再把實際 port 傳給 client |
| 共享狀態 | 測試 A 改了全域設定沒還原，測試 B 才會通過或失敗 | 每個測試建立自己的物件與資料；不要用可變的全域狀態 |
| 工具版本 | CI 機器升級了資料庫版本，查詢結果排序改變 | 依賴與工具版本鎖定在設定中，用容器固定執行環境（第 27 章） |

這些方法有一個共同的設計前提：**程式本身要讓隱藏輸入可以被替換**。如果程式直接呼叫 `datetime.now()`、直接連到寫死的 URL，測試就只能用 monkeypatch 等手段硬改，又脆弱又難懂。第 24 章的 dependency injection 在這裡再次出現：把時鐘、亂數來源、外部 client 當成參數傳進來，測試才能自然地控制它們。

### Hermetic 的代價與界線

完全 hermetic 不是免費的，而且不是所有測試都應該追求。第 25 章談過，larger tests 的價值來自保真度，而保真度常常意味著碰真實的東西。一個 100% hermetic、所有依賴都是 fake 的測試，可能因此錯過 fake 與真實系統之間的差異。

實務上的平衡是分層：small 與 medium test 應該盡量 hermetic，它們是開發者每天依賴的快速信號，必須穩定；需要真實依賴的 larger tests 則接受一部分不確定性，但要把它們和 hermetic 的測試分開、分開統計失敗率、不要讓它們阻擋每一次提交。真實的外部依賴留給 contract test、staging 與 production probe 去驗證。

> [!warning] 常見誤解
> 「用了容器就是 hermetic。」容器能固定執行環境與依賴版本，但測試仍可能依賴時間、亂數、網路或其他測試留下的資料。一個在容器裡呼叫 `datetime.now()` 的測試，在午夜一樣會失敗。Hermeticity 是關於「所有輸入都被控制」，不是關於使用哪一種技術。

## 26.4 Flaky test 的成因

**Flaky test**（不穩定測試）是指：在程式碼與測試都沒有改變的情況下，有時通過、有時失敗的測試。注意定義中的「沒有改變」：如果失敗是因為程式碼確實有 bug，那是一個正確的失敗；只有「同樣的輸入、不同的結果」才是 flaky。

Flaky 的根源永遠是某種**不確定性**（nondeterminism），也就是 26.3 節的某個隱藏輸入在變動。常見的成因可以分成幾類：

**時間相依**。測試的結果取決於執行的時刻。Harbor 的 `test_coupon_expiry` 建立一張「明天到期」的優惠券，然後檢查它「今天還有效」；在 23:59:59 建立、00:00:01 檢查時，「今天」已經變成明天。同類問題還有月底、閏年、夏令時間切換，以及用 `sleep(1)` 假設「一秒後某件事一定已經發生」。

**順序相依**。測試的結果取決於其他測試是否先執行。例如測試 A 把一個全域的設定改成「免運門檻 500 元」，沒有還原；測試 B 剛好依賴這個值才通過。單獨跑 B 會失敗，跟著 A 一起跑才通過。測試框架改成並行或隨機順序時，這類問題就會浮現。這也叫 **test pollution**（測試污染）。

**共享狀態**。多個測試使用同一個資料庫、同一個檔案、同一個測試帳號。第 25 章提到 staging 上兩個團隊搶同一件測試商品的庫存，就是這一類。在 CI 中並行執行時尤其常見。

**非同步等待**。測試觸發一個非同步動作（寄信、寫入 queue、背景任務），然後用固定時間等待結果。CI 機器負載高時，背景任務沒在預期時間內完成，測試就失敗。正確做法是等待一個條件（輪詢直到狀態改變，並設上限），而不是等待一段時間。SWE 第 14 章也指出，固定時間的 sleep 會讓 timeout 變成需要持續維護的數字，建議改成對事件做出反應的等待方式。

**並行與 race condition**。這一類最需要小心，因為它可能是測試的問題，也可能是**產品的問題**。Harbor 的 `test_inventory_reserve_concurrent` 失敗，正是因為產品程式真的有 race condition。測試本身沒有錯，它忠實地反映了「有時候會超賣」這個事實。把這種失敗歸類為 flaky 並重跑，等於把產品 bug 藏起來。

**資源與逾時**。測試設定了過緊的 timeout，在負載高的 CI 機器上偶爾超過；或測試耗盡記憶體、檔案描述符。

**未定義的順序**。測試依賴 hash table、set 的迭代順序，或資料庫查詢沒有 `ORDER BY` 時的回傳順序。這是第 5 章 Hyrum's Law 的典型例子：順序本來就沒有承諾，卻被測試依賴了。

**外部依賴與基礎設施**。測試呼叫真實的外部 API、從網路下載套件，或 CI 機器本身的網路、磁碟出問題。

> [!example] 例子：同一個症狀，三種不同的原因
> Harbor 的 `test_checkout_e2e` 每二十次失敗一次，失敗訊息都是「等待訂單狀態變成 paid 逾時」。調查後發現三種原因混在一起：有時是 staging 的 payments sandbox 短暫不可用（基礎設施）；有時是另一個團隊的測試同時搶走了測試商品的庫存（共享狀態）；還有少數是 checkout 在高負載下真的有一個處理 callback 的 bug（產品問題）。如果團隊只看症狀、把它整體標成「flaky」，第三種原因就永遠不會被找到。

## 26.5 量化 flakiness：小機率如何變成大問題

### 為什麼要量化

「這個測試有點不穩」不是一個可以行動的描述。要決定該修哪一個、要不要 quarantine、修好了沒有，都需要數字。更重要的是，flaky 的影響在大型 suite 中是乘法放大的，直覺很容易低估。

### Suite 層級的放大

假設每個測試都是獨立的，每個的 flaky 率是 p（在正確的程式碼上隨機失敗的機率），suite 有 N 個測試。那麼一次正確的提交，整個 suite 全部通過的機率是：

```text
P(全綠) = (1 − p)^N

例：p = 0.1%、N = 500
P(全綠) = 0.999^500 ≈ 0.606
→ 每 5 次正確的提交，大約有 2 次會看到至少一個紅燈
```

0.1% 聽起來很小，相當於一個測試跑一千次只失敗一次，單獨看幾乎感覺不到。但 suite 有 500 個這樣的測試時，約四成的正確提交會看到紅燈。當工程師的經驗變成「紅燈常常不是我的錯」，他們就會停止調查紅燈。這就是為什麼大型組織對 flakiness 的容忍度很低：suite 越大，每個測試的 flaky 率就必須越低。

SWE 第 11 章給了一個經驗值：flaky 的比例接近 1% 時，測試就開始失去價值（第 22 章 22.9 節也引用了這個說法）；Google 自己的 flaky 率大約在 0.15% 上下，而以 Google 的測試量，這仍然代表每天有數千次 flaky 失敗。原書強調，測試的價值來自工程師對它的信任；只要調查過幾次無故的失敗，團隊就會開始不理會紅燈，整套測試的價值也就跟著消失。

### 重試如何掩蓋真正的 bug

很多 CI 的第一反應是「失敗就自動重試」。它確實能讓 suite 變綠，但代價是把真正的間歇性 bug 也洗掉了。假設一個真正的 race condition 在 CI 上只有 20% 的機率重現：

```text
不重試：    bug 通過 CI 的機率 = 1 − 0.2           = 80%
重試 1 次：  bug 通過 CI 的機率 = 1 − 0.2²          = 96%
重試 2 次：  bug 通過 CI 的機率 = 1 − 0.2³          = 99.2%
```

因為只要有任何一次「剛好沒重現」，測試就被判定通過。重試次數越多，間歇性 bug 越難被發現。Harbor 的超賣 bug 就是這樣通過的：那次 PR 的 CI 確實失敗過，系統把它當成雜訊吞掉了。

這不代表重試完全不能用，而是重試的結果必須被**記錄並區別對待**。一個「重試後通過」的測試，不應該被當成「通過」，而應該被標記為「這次 flaky」，寫進資料庫、算進 flaky 率、通知 owner。重試可以避免一個 flaky test 阻擋所有人，但不能讓它的失敗消失。SWE 第 11 章對重跑的評價也很直接：它是用 CPU 時間換工程師的時間，只是把處理根因的時刻往後延。

### 怎麼偵測與估計 flaky 率

偵測 flaky test 有兩種主要資料來源：

1. **同一個 commit 上的不同結果**。CI 在同一個 commit 上重跑某個測試，一次失敗、一次通過，就是最直接的 flaky 證據。很多組織會定期在主線最新的 commit 上把整個 suite 重跑很多次，專門用來找 flaky test。
2. **歷史中的翻轉**。一個測試在主線上「通過 → 失敗 → 通過」，而中間的 commit 和它無關，也是 flaky 的強烈訊號。

估計 flaky 率時要注意樣本數。重跑 200 次都沒失敗，不代表 flaky 率是 0，只代表它可能很低。一個好用的經驗法則是 **rule of three**：在 n 次獨立試驗中觀察到 0 次失敗，真實失敗率的 95% 信賴上限約為 3/n。重跑 200 次沒失敗，只能說「flaky 率大概低於 1.5%」。對一個要求 0.1% 以下的大型 suite，這遠遠不夠。

這個 3 從哪裡來？如果真實失敗率是 p，n 次都沒失敗的機率是 (1 − p)^n。所謂 95% 信賴上限，就是讓「n 次都沒失敗」這件事的機率剛好降到 5% 的那個 p：

```text
(1 − p)^n = 0.05
n · ln(1 − p) = ln 0.05 ≈ −3.0
p 很小時 ln(1 − p) ≈ −p，所以 p ≈ 3 / n

例：n = 200 → p ≈ 3 / 200 = 1.5%
    精確解 1 − 0.05^(1/200) ≈ 1.49%
反過來：想說「flaky 率低於 0.1%」，至少要連續 3 / 0.001 = 3,000 次沒失敗
```

最後一行也是 26.6 節「修好後要重跑幾次才能放回閘門」的算法：先決定要證明的上限，再用 3 除以它。

也要注意某些 flaky 用重跑抓不到：`test_coupon_expiry` 只在午夜前後失敗，在下午連續重跑一千次也全部通過。時間相依、順序相依的問題，需要刻意改變那個隱藏輸入（把 fake clock 設在 23:59:59、隨機化測試順序）才會現形。

## 26.6 Quarantine 與修復流程

### 為什麼需要一套流程

偵測到 flaky test 之後，有三種常見但錯誤的反應：一直重跑（26.5 節說明了代價）；直接刪掉（失去了它原本保護的行為）；放著不管（大家繼續習慣性忽略紅燈）。**Quarantine**（隔離）是介於中間的做法：把 flaky test 從阻擋提交的閘門中暫時移出，但繼續執行與追蹤，直到修好為止。它的目的是保護主線上其他人的信號，同時不讓問題被遺忘。

### 一個 flaky test 的生命週期

```text
  ┌──────────┐   偵測到 flaky   ┌────────────────┐   指定 owner    ┌───────────────┐
  │ 正常閘門  │────────────────►│ 分類：是產品   │────────────────►│ Quarantine    │
  │（阻擋提交）│                │ bug 還是測試／ │  （測試或環境   │ 仍然執行、記錄 │
  └──────────┘                 │ 環境問題？     │    問題時）      │ 不阻擋提交     │
       ▲                       └───────┬────────┘                 │ ticket＋期限   │
       │                               │ 產品 bug                  └──────┬────────┘
       │                               ▼                                 │
       │                       ┌────────────────┐                        │ 重現 → 修根因
       │                       │ 當成真正的 bug  │                        ▼
       │                       │ 處理，測試留在  │                 ┌───────────────┐
       │                       │ 閘門中          │                 │ 驗證：重跑 N 次│
       │                       └────────────────┘                 │ 沒有失敗       │
       │   通過驗證                                                 └──────┬────────┘
       └──────────────────────────────────────────────────────────────────┤
                                             超過期限且無人修 → 由 owner 決定刪除
                                             或改寫，並記錄失去的保護
```

從左上開始讀：一個在正常閘門中的測試被偵測為 flaky 後，第一步不是 quarantine，而是**分類**。如果失敗反映的是產品 bug（例如 race condition），它就不是 flaky test，而是一個抓到 bug 的好測試，應該留在閘門中，當成 bug 處理。只有確認是測試本身或環境的問題，才進入 quarantine。

Quarantine 中的測試仍然在 CI 中執行並記錄結果，只是不再阻擋提交。它必須有一個 owner、一張 ticket 與修復期限。修復後，在同一個 commit 上重跑足夠多次（依 26.5 節的 rule of three 決定次數）確認沒有失敗，才放回閘門。超過期限仍無人處理的測試，由 owner 決定刪除或改寫，並明確記錄「我們失去了對哪個行為的保護」。

### 重現技巧

修 flaky test 最難的一步是重現。實用的技巧包括：

- **大量重跑**：在本機或 CI 上把同一個測試跑幾百次，並平行執行以增加資源競爭。
- **隨機化順序**：用固定 seed 打亂測試順序，找出順序相依；失敗時記錄 seed 以便重現。
- **單獨執行 vs 一起執行**：單獨跑會失敗、一起跑會通過（或相反），就是 test pollution 的線索。
- **控制時間**：把 fake clock 設在邊界時刻，例如午夜、月底、夏令時間切換。
- **製造壓力**：限制 CPU 或同時執行其他負載，讓時序問題更容易出現。
- **保存證據**：每次失敗都保存 seed、執行順序、機器資訊、log 與 trace。「它在 CI 上失敗了，但我在本機跑不出來」通常是因為缺少這些資訊。

### 組織層級的做法

Quarantine 的危險是它變成垃圾場：測試被丟進去，永遠沒有出來。避免的方法是把它當成一個要被量測與管理的佇列：追蹤 quarantine 中的測試數量、平均待了多久、每個團隊各有多少；把它們放進團隊的週會或儀表板；對超過期限的測試自動提醒。一個健康的組織中，quarantine 的大小應該是穩定或下降的。

另一個重要的原則是：**flakiness 由測試的 owner 負責，而不是由 CI 平台團隊負責**。平台團隊提供偵測、quarantine 與統計的工具（第 28 章），但修復一個測試需要理解它在測什麼，只有 owner 能做。

> [!warning] 常見誤解
> 「這個測試很 flaky，加長 timeout 就好。」加長 timeout 有時是正確的修法，例如它原本設得不合理地短；但如果測試是在等待一個非同步事件，加長 timeout 只是降低失敗機率，並讓測試變慢。真正的修法通常是改成等待條件，或讓非同步工作在測試中可以被同步觸發。修 flaky 之前，先回答「是哪一個隱藏輸入在變動」。

## 26.7 Coverage：它能說明什麼，不能說明什麼

### 什麼是 coverage

前面處理的是誤報（紅燈不可信），接下來處理漏報（綠燈不可信）。最常被拿來衡量「測試夠不夠」的數字是 **code coverage**（程式碼覆蓋率）：測試執行時，有多少比例的程式碼被執行到。常見的幾種：

- **Line coverage**（行覆蓋率）：被執行到的行數 ÷ 總行數。
- **Branch coverage**（分支覆蓋率）：每個 `if`、`else` 等分支方向是否都被走過。`if a and b:` 這一行被執行到，line coverage 就算覆蓋了，但「a 為真、b 為假」這條路徑可能從沒被走過。
- **Condition coverage**（條件覆蓋率）與 **path coverage**（路徑覆蓋率）：更細的版本，前者看複合條件中每個子條件，後者看所有可能的執行路徑組合。path coverage 的數量隨分支數指數成長，實務上很少完整追求。

### Coverage 真正告訴你的事

Coverage 能可靠地告訴你一件事：**哪些程式碼完全沒有被任何測試執行過**。這是有用的資訊。一段沒被執行過的錯誤處理程式，你可以確定測試對它一無所知。

但 coverage 不能告訴你被執行的程式碼是否被**檢查**過。一個呼叫函式但不檢查任何結果的測試，能讓 coverage 增加，卻不能抓到任何 bug。Harbor 的 coverage 目標帶來的正是這類測試。換句話說，coverage 是測試品質的**必要條件**的近似，不是充分條件：低 coverage 幾乎一定代表測試不足；高 coverage 不代表測試足夠。

### Coverage 當成目標時會發生什麼

這是第 14 章 Goodhart's Law 的典型案例：當一個量測變成目標，它就不再是好的量測。把 coverage 設成硬性門檻或個人考核指標，常見的結果有：

- 寫沒有斷言、只為了執行程式碼的測試。
- 優先測試容易測的程式碼（getter、簡單的轉換函式），而不是風險最高的程式碼（錯誤處理、並行、邊界）。
- 把難以測試的程式碼排除在 coverage 統計之外。
- 為了覆蓋某一行而寫出綁定實作細節的測試，讓第 23 章談的 brittle test 增加。

SWE 第 11 章還觀察到一個更微妙的效果：門檻會從地板變成天花板。把目標訂在 80%，新的變更很快就開始剛好停在 80% 左右，沒有人有動機多測一點。原書因此建議只用 small test 來量 coverage（避免 larger tests 執行大量程式碼卻沒有檢查而灌高數字），並且不要試圖用單一數字回答「測試夠不夠」。

### 實務上怎麼用

比較健康的用法是把 coverage 當成**提問的工具**，而不是評分的工具：

1. **在 code review 中看變更的 coverage**。與其看整個專案的百分比，不如看這次 PR 新增或修改的程式碼中，哪幾行沒有被測試執行到。reviewer 可以針對那幾行問：「這段錯誤處理怎麼驗證？」作者可能有好理由（例如這是只在 production 才會發生的分支，由 integration test 覆蓋），也可能真的漏了。
2. **找出完全未覆蓋的高風險區域**。依風險排序看未覆蓋的程式碼：付款、權限、資料刪除的未覆蓋分支，比 log 格式化的未覆蓋分支重要得多。
3. **不要追求 100%**。最後幾個百分點常常是防禦性的程式碼或極難觸發的分支，為它們寫測試的成本可能高於價值。
4. **用 branch coverage 而不是只看 line coverage**，它更能反映條件邏輯是否被完整走過。

Google Testing Blog 在 2020 年 8 月由 Carlos Arguelles、Marko Ivanković 與 Adam Bender 撰寫的〈Code Coverage Best Practices〉一文中，提供了一組粗略的參考：60% 可接受（acceptable）、75% 值得稱讚（commendable）、90% 堪為典範（exemplary）。文章同時說明，Google 不喜歡由上而下的全面強制，而是讓每個團隊依業務需要選擇自己的數字；整個專案追求 90% 以上多半不值得，但針對每次 commit 的變更，99% 是合理的目標、90% 是不錯的下限。文章也強調，未覆蓋的部分比已覆蓋的部分更有意義，在 code review 中針對具體未覆蓋行的務實討論，比執著於任意的目標數字更有價值；並指出要評估被覆蓋的程式碼有沒有被好好檢查，mutation testing 是更好的方法。這組數字可以作為起點，但更重要的是文章的精神：coverage 的價值在於引發對話。

## 26.8 Mutation score：測試能不能分辨對錯

### 為什麼需要

既然 coverage 只告訴你程式碼有沒有被執行，那要怎麼量測「測試能不能抓到 bug」？最直接的方法是：**故意放進 bug，看測試會不會發現**。這就是第 23 章介紹過的 **mutation testing**（突變測試）。這裡從「量測」的角度更深入看它。

### 怎麼運作：回顧與公式

第 23 章（23.9 節）已經用圖說明了基本機制：工具用突變運算子（例如 `>=` 改成 `>`）產生 mutant，有測試失敗就是 killed、全部通過就是 survived，存活的 mutant 再分成「測試缺口」「equivalent mutant」「不重要的行為」三類判讀。這裡只補上把它當成**量測**時需要的部分。第一件事是分數的算法：

```text
mutation score = 被殺死的 mutant 數 / （所有 mutant 數 − equivalent mutant 數）

例：23.10 節的程式產生 8 個 mutant，殺死 7 個，
    存活的那個（x * 90 // 100 → x * 9 // 10）對整數完全等價。
    未扣除時：7 / 8 ≈ 88%
    扣除後：  7 / (8 − 1) = 7 / 7 = 100%
```

扣掉 equivalent mutant 的理由是：它們不可能被任何測試殺死，留在分母裡只會讓「完美的測試」也到不了 100%，分數就無法比較。代價是有人得判斷哪些 mutant 等價，這一般無法完全自動化，是 mutation testing 主要的人力成本之一。也因為這一步需要人工判斷，分母本身就帶有主觀成分，這是 mutation score 不適合拿來跨團隊比較的原因之一。

### 存活的 mutant 是一個具體的問題

Mutation score 比 coverage 有用的地方，不只是那個百分比，而是**每一個存活的 mutant 都是一個具體、可行動的問題**。「coverage 82%」不告訴你該做什麼；「把 `subtotal >= 1000` 改成 `subtotal > 1000` 時沒有任何測試失敗」直接告訴你：免運門檻的邊界值沒有被測試。修法很明確：加一個 `subtotal == 1000` 的測試案例。

### 成本與實務做法

Mutation testing 的主要成本是運算量：每個 mutant 都要跑一次相關的測試，大型程式碼庫可能有數十萬個 mutant。實務上常見的降低成本方法：

- **只對變更的程式碼做突變**。Google 的 Goran Petrović 與 Marko Ivanković 在 ICSE 2018（軟體工程實務 SEIP track）發表的論文〈State of Mutation Testing at Google〉描述了這種做法：以 diff 為基礎、機率性地挑選 mutant，只對這次修改、而且有被測試執行到的程式行產生少量 mutant；論文稱為 **arid**（貧瘠）的程式行，也就是突變了也不太可能帶來有用資訊的程式碼（例如 log 語句），會被刻意略過，判斷規則依語言而不同。存活的 mutant 以 review 意見的形式呈現給作者與 reviewer，而不是一個阻擋合併的分數。論文特別在意開發者的注意力：mutant 少而精，結果才容易解讀、才會被認真處理。
- **只跑覆蓋該行的測試**。用 coverage 資料找出哪些測試會執行到被突變的程式碼，只跑那些。
- **定期而非每次執行**。對核心模組每週跑一次完整的 mutation 分析，追蹤分數趨勢。

各語言都有成熟的工具，例如 Java 的 PIT（pitest）、JavaScript 與 .NET 的 Stryker、Python 的 mutmut。導入時建議從一個高風險的核心模組開始，例如 Harbor 的價格計算或庫存扣減，而不是對全部程式碼一次執行。

### 為什麼不該當 KPI

Mutation score 一旦變成考核指標，投機的方式和 coverage 不同，但一樣存在：把難殺的存活 mutant 標成「equivalent」讓分母變小；寫出逐行對照實作、什麼 mutant 都殺得死卻不描述任何行為的測試（23.10 節結尾提到的另一種極端）；或把運算子設定成只產生容易殺死的 mutant。分數會變好看，測試卻沒有更能保護行為。比較健康的追蹤方式是看「review 中被提出的存活 mutant，有多少比例被處理（補了測試或有理由地標記）」，而不是看分數本身。

> [!warning] 常見誤解
> 「mutation score 應該取代 coverage 成為新的目標。」它同樣會受 Goodhart's Law 影響，只是比較難被投機。Mutation score 最好的用法和 coverage 一樣：把存活的 mutant 當成 review 中的具體問題，而不是當成要達到的百分比。

## 26.9 測試資料管理

### 為什麼測試資料是一個獨立的問題

測試資料既影響 flakiness（共享資料造成干擾），也影響漏報（資料不夠真實就抓不到真實的 bug）。隨著測試數量增加，資料的管理方式往往決定了整個 suite 是否可維護。

### 小型測試：資料寫在測試裡

Small test 的資料應該盡量直接寫在測試中，讓讀者不需要跳到別的檔案就能理解。第 23 章談過 DAMP（Descriptive And Meaningful Phrases）：測試裡寧可有一點重複，也要讓每個測試自己說清楚它的前提。

當資料物件很複雜（例如一筆訂單有買家、賣家、多個商品、優惠券、配送地址），常用 **test data builder**（測試資料建構器）：提供合理的預設值，讓測試只寫出和它有關的欄位。

```python
# not-runnable
order = an_order().with_coupon("FREESHIP").with_subtotal(999).build()
# 讀者一眼就知道這個測試在意的是「優惠券」與「999 元」，其他欄位都是預設值
```

這比一個共用的巨大 fixture 檔案好得多。共用 fixture 的問題是：每個測試都依賴它的某些部分，但沒人知道是哪些部分；有人為了一個新測試修改 fixture，十個舊測試就壞了。

### 較大測試：隔離與清理

使用真實資料庫的 integration test 與 E2E，需要額外處理隔離：

- **每個測試使用唯一的資料**。測試建立自己的使用者、商品，使用唯一的 ID 或前綴（例如 `test-<隨機字串>`），不依賴資料庫中「應該已經存在」的資料。
- **清理策略**。常見三種：每個測試包在一個交易中，結束時 rollback（最快，但無法測試跨交易的行為）；測試結束後刪除自己建立的資料；或每個 suite 使用一個全新的資料庫實例，結束後整個丟棄（最乾淨，第 25 章的 ephemeral environment）。
- **不要依賴清理一定成功**。測試可能在中途失敗或被中止。比較穩健的做法是測試開始時就不假設環境是乾淨的，並使用自己專屬的資料。

### 真實性與個資

第 25 章提到，測試資料要夠真實才能抓到真實的 bug。最直接的想法是複製一份 production 資料庫，但這會帶來嚴重的問題：個資、付款資訊與商業機密會流到權限較寬的測試環境，違反隱私法規與公司政策。實務上的做法：

- **合成資料**：依照 production 的統計分佈產生假資料，例如商品名稱的長度分佈、包含 emoji 與多語言的比例、購物車大小的分佈。
- **去識別化**：如果必須使用真實資料的結構，就做遮罩、替換與聚合，並經過安全與隱私審查。
- **刻意加入邊界案例**：真實資料中罕見但會出問題的情況（超長字串、特殊字元、金額為 0、時區邊界）要明確寫進測試資料集。
- **Golden file**（黃金檔案：預先保存的預期輸出，測試比對實際輸出與它是否一致）要納入版本控制，更新時要經過 review，不能「跑一下就自動覆蓋」。

## 26.10 動手寫：flaky 的數學與 mutation score

第一段程式把 26.5 節的三個量化概念放在一起：suite 層級的放大、重試對真正 bug 的掩蓋，以及在同一個 commit 上重跑來偵測 flaky 並決定是否 quarantine。

```python
import random

# ── 1. 單一測試的小 flaky 率，放大成整個 suite 的紅燈 ──
print("每個測試 flaky 率 p、suite 有 N 個測試時，同一個正確 commit 全綠的機率")
for n in [100, 500, 2000]:
    row = "  ".join(f"p={p:.2%}: {(1 - p) ** n:6.1%}" for p in [0.0005, 0.001, 0.005])
    print(f"  N={n:>4}  {row}")

# ── 2. 自動重試把真的 race condition 也洗成綠燈 ──
print("\n真 bug 在 CI 上只有 20% 的機率重現時，被 merge 的機率")
for retries in [0, 1, 2, 3]:
    pass_prob = 1 - 0.20 ** (retries + 1)               # 至少一次「沒重現」就會通過
    print(f"  失敗後自動重試 {retries} 次：bug 通過 CI 的機率 {pass_prob:.1%}")

# ── 3. 在同一個 commit 上重跑，偵測 flaky 並決定 quarantine ──
TRUE_RATES = {                       # 真實（但未知）的失敗機率
    "test_cart_total": 0.0,
    "test_search_rank": 0.002,
    "test_checkout_e2e": 0.06,
    "test_coupon_expiry": 0.03,      # 跨午夜時才失敗的時間相依測試
    "test_inventory_reserve": 0.0,
}
rng = random.Random(42)
RUNS = 200
print(f"\n同一個 commit 重跑 {RUNS} 次")
for name, rate in TRUE_RATES.items():
    fails = sum(rng.random() < rate for _ in range(RUNS))
    observed = fails / RUNS
    if fails == 0:
        verdict = f"沒看到失敗（95% 信心上限約 {3 / RUNS:.1%}）"
    elif fails == RUNS:
        verdict = "穩定地壞（不是 flaky，是 bug）"
    elif observed >= 0.01:
        verdict = "flaky → quarantine、開 ticket、指定 owner"
    else:
        verdict = "flaky（低）→ 開 ticket 追蹤"
    print(f"  {name:<24} 失敗 {fails:>3}/{RUNS}  估計 {observed:5.1%}  {verdict}")
```

執行結果：

```text
每個測試 flaky 率 p、suite 有 N 個測試時，同一個正確 commit 全綠的機率
  N= 100  p=0.05%:  95.1%  p=0.10%:  90.5%  p=0.50%:  60.6%
  N= 500  p=0.05%:  77.9%  p=0.10%:  60.6%  p=0.50%:   8.2%
  N=2000  p=0.05%:  36.8%  p=0.10%:  13.5%  p=0.50%:   0.0%

真 bug 在 CI 上只有 20% 的機率重現時，被 merge 的機率
  失敗後自動重試 0 次：bug 通過 CI 的機率 80.0%
  失敗後自動重試 1 次：bug 通過 CI 的機率 96.0%
  失敗後自動重試 2 次：bug 通過 CI 的機率 99.2%
  失敗後自動重試 3 次：bug 通過 CI 的機率 99.8%

同一個 commit 重跑 200 次
  test_cart_total          失敗   0/200  估計  0.0%  沒看到失敗（95% 信心上限約 1.5%）
  test_search_rank         失敗   2/200  估計  1.0%  flaky → quarantine、開 ticket、指定 owner
  test_checkout_e2e        失敗  13/200  估計  6.5%  flaky → quarantine、開 ticket、指定 owner
  test_coupon_expiry       失敗   2/200  估計  1.0%  flaky → quarantine、開 ticket、指定 owner
  test_inventory_reserve   失敗   0/200  估計  0.0%  沒看到失敗（95% 信心上限約 1.5%）
```

逐段解讀：

1. 第一張表把 26.5 節的公式 (1 − p)^N 展開。看中間那一欄：p = 0.1% 時，100 個測試的 suite 還有 90% 的全綠率，到了 2,000 個測試只剩 13.5%。suite 從小團隊長到大組織時，同樣的 flaky 率會從「偶爾煩人」變成「幾乎每次都紅」。這也說明為什麼 SWE 一書強調大型組織必須積極處理 flakiness。
2. 第二段的重點是起點：一個 20% 重現率的 bug，即使**不重試**，也有 80% 的機率通過一次 CI。間歇性 bug 本來就難抓，自動重試讓它變得幾乎抓不到。這就是 Harbor 超賣 bug 的路徑。
3. 第三段模擬偵測流程。注意估計的雜訊：`test_search_rank` 的真實 flaky 率是 0.2%，200 次重跑中剛好失敗 2 次，被估成 1.0%；`test_coupon_expiry` 真實是 3%，卻只被估成 1.0%。樣本數有限時，估計值會偏離真實值，所以決策門檻不能訂得太細。
4. 「沒看到失敗」的測試印出 rule of three 的上限：重跑 200 次只能說明 flaky 率大概低於 1.5%。程式中的 `test_inventory_reserve` 真實失敗率設為 0，但現實中，它的 race condition 只在高並行時出現；在這種低並行的重跑中，它就會落在「沒看到失敗」。這提醒我們：重跑只能抓到「在這個條件下會變動」的隱藏輸入。
5. 程式中的 `test_coupon_expiry` 用一個固定機率代表它，但真實世界的時間相依測試不是隨機的：它只在特定時刻失敗。在下午重跑一千次也找不到它，必須把 fake clock 設在午夜才會現形。

真實系統中，這些資料來自 CI 的測試結果資料庫：每次執行的 commit、測試名稱、結果、是否為重試、機器與時間。flaky 偵測服務定期計算每個測試的翻轉率與同 commit 的不一致次數，超過門檻就自動開 ticket 給 owner 並提議 quarantine（第 28 章）。

第二段程式比較兩組測試：它們的 line coverage 都是 100%，mutation score 卻天差地遠。mutation testing 的基本機制（用字串替換產生 mutant、逐一跑測試判斷 killed 或 survived）第 23 章（23.10 節）已經示範過；這段程式要看的是本章的量測角度：把 coverage 與 mutation score 放在一起量，看兩個數字在什麼地方分道揚鑣。

```python
import sys

SOURCE = '''
def shipping_fee(subtotal, is_member):
    if subtotal >= 1000:
        return 0
    if is_member and subtotal >= 500:
        return 30
    return 60
'''

MUTATIONS = [                         # (原始片段, 突變後片段)：模擬常見的 off-by-one 與邏輯錯誤
    (">= 1000", "> 1000"),
    (">= 500", "> 500"),
    ("is_member and", "is_member or"),
    ("return 30", "return 60"),
    ("return 0", "return 1"),
    ("return 60", "return 0"),
]


def load(src):
    ns = {}
    exec(compile(src, "<shipping>", "exec"), ns)
    return ns["shipping_fee"]


def weak_suite(fee):                  # 每一行都跑到，但幾乎沒有檢查
    fee(1500, False)
    fee(600, True)
    assert fee(100, False) > 0


def strong_suite(fee):                # 斷言精確值，並測邊界
    assert fee(1000, False) == 0
    assert fee(999, False) == 60
    assert fee(500, True) == 30
    assert fee(499, True) == 60
    assert fee(600, False) == 60


def line_coverage(suite):
    hit = set()

    def tracer(frame, event, arg):
        if frame.f_code.co_filename == "<shipping>" and event == "line":
            hit.add(frame.f_lineno)
        return tracer

    sys.settrace(tracer)
    suite(load(SOURCE))
    sys.settrace(None)
    body = [i for i, line in enumerate(SOURCE.splitlines(), 1)
            if line.strip() and not line.startswith("def")]
    return len(hit & set(body)) / len(body)


def mutation_score(suite):
    killed, survivors = 0, []
    for old, new in MUTATIONS:
        mutant = load(SOURCE.replace(old, new, 1))
        try:
            suite(mutant)
            survivors.append(f"{old!r} → {new!r}")
        except AssertionError:
            killed += 1
    return killed / len(MUTATIONS), survivors


for name, suite in [("弱測試", weak_suite), ("強測試", strong_suite)]:
    cov = line_coverage(suite)
    score, survivors = mutation_score(suite)
    print(f"{name}：line coverage {cov:.0%}，mutation score {score:.0%}")
    for s in survivors:
        print(f"    存活的突變：{s}")
```

執行結果：

```text
弱測試：line coverage 100%，mutation score 17%
    存活的突變：'>= 1000' → '> 1000'
    存活的突變：'>= 500' → '> 500'
    存活的突變：'is_member and' → 'is_member or'
    存活的突變：'return 30' → 'return 60'
    存活的突變：'return 0' → 'return 1'
強測試：line coverage 100%，mutation score 100%
```

逐段解讀：

1. `shipping_fee` 是 Harbor 的運費規則：滿 1,000 元免運，會員滿 500 元運費 30 元，其他 60 元。它很短，但有兩個邊界與一個複合條件，正是 bug 最常藏的地方。
2. `MUTATIONS` 是手動列出的突變運算子，產生 mutant 的方式和 23.10 節相同。真實工具會自動在 AST（抽象語法樹）上找出所有可以突變的位置，例如每個比較運算子、每個布林運算子、每個回傳值。這 6 個 mutant 都會改變行為，沒有 equivalent mutant，所以程式直接用 6 當分母；若有等價的 mutant，就要依 26.8 節的公式從分母扣掉。
3. `line_coverage` 用 Python 的 `sys.settrace` 記錄哪些行被執行，這也是 coverage.py 這類工具的基本原理。兩組測試都讓每一行至少被執行一次，所以都是 100%。
4. `weak_suite` 呼叫了三次函式，卻只檢查一個「運費大於 0」，五個突變都存活。每一個存活的突變都是一個具體的盲點：例如 `'>= 1000' → '> 1000'` 存活，表示沒有任何測試檢查「剛好 1,000 元」的情況，如果有人把邊界寫錯，這組測試不會發現。
5. `strong_suite` 的差別在於斷言精確值，並且測試了邊界兩側（1,000 與 999、500 與 499）。它的 coverage 和弱測試一樣，mutation score 卻是 100%。這就是 26.7 節的結論：**coverage 衡量執行，mutation score 衡量檢查**。兩組測試在 coverage 儀表板上完全看不出差別，只有 mutation score 與存活清單揭露了弱測試的五個盲點；Kevin 的 85% coverage 目標之所以會被沒有斷言的測試達成，原因也在這裡。

## 26.11 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| CI 自動重試失敗的測試 | 間歇性的產品 bug 被當成 flaky 洗掉 | Harbor 的 inventory race condition 在 CI 失敗一次，重試後通過，上線後超賣 | 重試結果要記錄為「flaky」並通知 owner；涉及並行的測試失敗先當成產品 bug 調查 |
| Quarantine 沒有 owner 與期限 | 測試永久離開閘門，保護悄悄消失 | 半年後發現 quarantine 中有 60 個測試，其中 12 個保護的是付款流程 | 每個 quarantine 都要有 owner、ticket 與期限；追蹤 quarantine 的數量與年齡；超期由 owner 決定刪除或改寫 |
| 把 coverage 設為硬性目標或考核指標 | 出現沒有斷言的測試，高風險程式反而沒人測 | 團隊達成 85% coverage，新增的測試大多是 getter 與沒有斷言的呼叫 | 在 review 中討論變更中未覆蓋的行；依風險看未覆蓋區域；搭配 mutation 分析 |
| 過度追求 hermetic | 所有依賴都是 fake，測試和真實系統脫節 | 所有測試都用 in-memory fake 資料庫，PostgreSQL 的鎖行為從沒被測過 | Small／medium test 追求 hermetic；保留少量使用真實依賴的 integration 與 contract test |
| 全公司對 mutation testing 一次開跑 | 運算成本爆炸、結果噪音太多，團隊放棄 | 對整個 monorepo 跑完整 mutation 分析，需要好幾天，產生上萬個存活 mutant | 從高風險模組或只對變更的程式碼開始；過濾掉 log 等低價值的突變；把結果以 review 意見呈現 |
| 用 production 資料副本當測試資料 | 個資與付款資訊外流到權限較寬的環境 | 為了「真實」把 production 訂單資料庫複製到 staging，staging 的存取控制比 production 寬鬆 | 使用合成資料與去識別化資料；把邊界案例明確寫進測試資料集；資料流程經過隱私審查 |
| 共用的巨大 fixture | 修改一處，不相關的測試大量失敗 | 為了新測試在共用 fixture 加了一個優惠券，二十個計算總金額的舊測試全部失敗 | 使用 test data builder，每個測試只寫出和它相關的欄位 |

## 26.12 AI 時代：什麼變了？

AI coding agent 讓這一章的問題變得更急迫，也提供了新的處理工具。AI 生成測試的一般品質陷阱（鏡像測試、弱斷言、過度 mock、放錯層）第 22 章（22.12 節）已經談過；這裡聚焦本章的兩個角度：flaky 與重跑，以及 coverage 被灌水。

### 新的壓力：agent 驅動的重跑與被灌水的 coverage

**Agent 會比人類更有效率地把紅燈洗成綠燈**。一個在 CI 上反覆「修改、跑測試、看結果」的 coding agent，遇到隨機失敗時，最容易的路徑是重跑直到通過、加長 timeout、或加上重試。人類按重跑至少會猶豫一下，agent 可以在幾分鐘內重跑十次而不留下任何紀錄。26.5 節的數學在這裡同樣成立：重跑次數越多，像 Harbor 超賣那樣的間歇性 bug 越確定會溜過去。更麻煩的是 agent 也會從噪音中「學習」：在一個常常亂紅的 suite 裡，agent 很快就會把紅燈當成正常現象，連真正由它自己引入的失敗也一起重跑掉。

**Coverage 可以在一個下午被灌滿**。請 agent「把 coverage 提高到 90%」，它可以很快產生大量測試，每一個都執行了更多程式碼。26.7 節的 Goodhart's Law 問題在 AI 時代被放大了：指標更容易被最佳化，而最佳化的速度遠超過人類 review 的速度。對這種一次湧入的大量新測試，coverage 數字本身完全無法分辨好壞，26.10 節的弱測試與強測試就是例子；能分辨的是只對這批變更跑的 mutation 分析。

**Agent 寫的測試可能本身就不 hermetic，於是成為新的 flaky 來源**。Agent 寫的測試可能直接呼叫 `datetime.now()`、使用全域亂數、寫入固定路徑或對外部服務送請求，因為這些在範例程式碼中很常見。它們在產生的當下跑一次會通過，要等到午夜、並行或網路不穩時才會失敗，那時已經很難追回是誰、為什麼加的。

### 新的工具：AI 擅長的分析工作

另一方面，flaky 與測試品質的分析中有大量 AI 擅長的工作：

- **分類 flaky 的原因**。給 agent 一個 flaky test 的原始碼、歷史失敗的 log 與執行環境資訊，它可以提出可能的隱藏輸入（「這個測試用了 `datetime.now()`，失敗都發生在 UTC 16:00 前後，也就是台北的午夜」）並建議重現方法。
- **處理存活的 mutant**。Agent 可以讀取 mutation 分析的結果，判斷哪些可能是等價 mutant、哪些代表真正的測試缺口，並為後者草擬測試案例。
- **審查新測試的 hermeticity**。在 review 中標出直接讀取系統時間、使用全域亂數、固定 port 或路徑、依賴未定義順序的比較，以及用固定 sleep 等待非同步結果的寫法。
- **產生測試資料**。依據 schema 與統計分佈產生合成資料，並刻意加入邊界案例。

### 具體做法

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 分析 flaky test 的失敗 log 與原始碼，提出可能的隱藏輸入與重現步驟 | 「這是 flaky 還是產品 bug」的分類由 owner 確認，特別是涉及並行與金流的測試；不能讓 agent 直接 quarantine 測試 |
| 依 mutation 分析結果，為存活的 mutant 草擬測試案例並標出疑似等價 mutant | 「這個 mutant 等價」的標記由人確認並寫下理由，否則分母會被悄悄縮小（26.8 節） |
| 在 review 中標出非 hermetic 的寫法（系統時間、全域亂數、固定 port、固定 sleep） | Coverage 與 mutation score 不能作為 AI 的唯一目標；coverage 的上升要搭配針對變更的 mutation 分析才算數 |
| 產生合成測試資料與邊界案例，依 schema 檢查資料一致性 | 不得把 production 資料交給 agent 作為範例；資料產生規則經過隱私審查 |
| 將 flaky 測試的修正改寫為 fake clock、固定 seed、條件式等待等確定性寫法 | 禁止 agent 以加長 timeout、加上重試或刪除斷言的方式「修好」flaky test，除非 owner 明確核准 |

在 CI 中落實這些規則，可以從幾條具體政策開始：agent 不能觸發超過一次的重跑，而且那一次重跑的結果照 26.5 節的規則記錄為 flaky；第二次失敗時必須回報分析而不是繼續重試。agent 不能把測試移進 quarantine，只能提出建議，由 owner 依 26.6 節的流程先分類。agent 新增的測試在合併前先在同一個 commit 上重跑數十次、並打亂順序執行，擋下新的 flaky 來源；再跑一次針對變更的 mutation 分析，存活的 mutant 必須在 PR 描述中說明。若 PR 修改了 timeout、新增重試或刪除斷言，自動要求測試 owner 額外 review。

> [!ai] AI 提醒
> 第 25 章談到 AI agent 的 eval 本身是機率性的，同一個案例多次執行結果不同。這和 flaky test 是同一個數學問題：判斷「新版本是否變差」時，要用 26.5 節的方法估計雜訊，用足夠的重複次數，並區分「隨機波動」與「穩定的退步」。不同的是，eval 的不確定性是 AI 系統的本質，不能也不應該被完全消除，只能被量測。

## 26.13 專家怎麼想

- **把每一個 flaky 失敗都先當成真的。** 資深工程師看到一個「偶爾失敗」的測試，第一個問題是「產品有沒有可能真的偶爾壞？」特別是涉及並行、快取、重試與時間的程式。Harbor 的超賣事故說明了，最危險的 flaky test 是那些其實不 flaky 的。
- **問「哪一個隱藏輸入在變動」。** 修 flaky test 不是試各種方法直到它通過，而是找出那個沒有被控制的輸入：時間、順序、共享狀態、網路還是排程。找到了，修法通常很明確；沒找到，任何修法都只是降低機率。
- **Suite 越大，容忍度越低。** 專家會用 (1 − p)^N 思考：當 suite 從幾百個測試長到幾萬個時，每個測試能接受的 flaky 率要跟著下降好幾個數量級，否則紅燈就會失去意義。
- **Coverage 是用來發問的，不是用來打分數的。** 看到一個 90% coverage 的報告，有經驗的 reviewer 會直接去看那 10% 是什麼，以及覆蓋的那 90% 有沒有真的檢查結果，而不是對數字本身感到滿意。
- **存活的 mutant 比 mutation score 重要。** 一個百分比無法告訴你該做什麼；一個「把 `>=` 改成 `>` 時沒有測試失敗」的具體發現，可以直接變成一個測試案例。

## 26.14 動手練習

1. 找出你專案中（或 Harbor 的情境中）三個依賴隱藏輸入的測試，分別寫出依賴的是哪一個隱藏輸入，以及如何讓它變成顯式輸入。
2. 延伸 26.10 的第一段程式：讓 `test_coupon_expiry` 的失敗不再是固定機率，而是「只在模擬的時刻落在 23:59 到 00:01 之間時失敗」。比較「在固定時刻重跑 1,000 次」與「把模擬時刻隨機分佈在一天中」兩種偵測方式的結果。
3. 延伸 26.10 的第二段程式：加入兩個新的突變運算子（例如把 `return 0` 改成 `return -1`，或刪除第一個 `if`），檢查強測試是否仍能殺死它們；再寫一個你認為是等價 mutant 的突變，解釋為什麼。
4. 為 Harbor 寫一份 flaky test 政策（一頁以內）：如何偵測、誰分類、quarantine 的條件與期限、重試的規則、修好後如何驗證，以及 AI agent 在其中可以與不可以做什麼。
5. 寫一個 Python 測試，刻意讓它依賴 set 的迭代順序或全域狀態，並觀察它在不同執行方式（例如改變 `PYTHONHASHSEED` 環境變數、改變測試順序）下的行為；然後把它改成 hermetic。
6. 為 Harbor 的訂單設計一個 test data builder：列出預設值，並寫三個測試示範它如何讓每個測試只表達自己在意的欄位。

## 本章重點整理

- 測試是一個偵測器：flaky test 造成誤報（程式正確卻紅燈），沒有檢查的測試與被重試洗掉的失敗造成漏報（程式有 bug 卻綠燈），兩者會互相強化。
- Hermetic test 的結果只取決於明確宣告的輸入；讓測試 hermetic 的方法是找出時間、時區、亂數、網路、檔案、port、共享狀態、工具版本等隱藏輸入，並把它們移除或變成顯式輸入。
- 程式本身要讓隱藏輸入可以被替換，例如透過 dependency injection 傳入時鐘與外部 client，測試才能自然地控制它們。
- Small 與 medium test 應盡量 hermetic；需要真實依賴的 larger tests 要與它們分開執行與統計，而不是放棄保真度。
- Flaky 的成因包括時間、順序、共享狀態、非同步等待、並行、資源、未定義順序與外部依賴；涉及並行的「flaky」失敗，可能是真正的產品 bug。
- Suite 全綠的機率是 (1 − p)^N；0.1% 的 flaky 率在 500 個測試的 suite 中就會讓約四成的正確提交看到紅燈。
- 自動重試會把間歇性的真 bug 洗成綠燈；重試結果必須被記錄為 flaky 並通知 owner，而不是當成通過。
- 估計 flaky 率要注意樣本數：n 次重跑都沒失敗，只能說失敗率大約低於 3/n；時間與順序相依的問題需要刻意改變那個輸入才能重現。
- Quarantine 是在保護主線信號與不遺忘問題之間的平衡：先分類、有 owner、有期限、持續執行並追蹤，修好後經過重跑驗證才放回閘門。
- Coverage 能可靠地指出哪些程式碼完全沒被執行，但不能說明被執行的程式碼是否被檢查；把它當成目標會引發 Goodhart's Law。
- Coverage 最好的用法是在 code review 中討論變更中未覆蓋的高風險程式碼，並優先看 branch coverage。
- Mutation score 衡量測試能否分辨對錯；每一個存活的 mutant 都是一個具體可行動的測試缺口，實務上常只對變更的程式碼做突變以控制成本。
- 測試資料應盡量寫在測試中或用 test data builder 表達；larger tests 要使用專屬資料與可靠的清理策略，並以合成或去識別化資料取代 production 副本。
- AI 讓產生測試與重跑都變得便宜，所以要用政策限制 agent 修改預期值、加長 timeout 與無限重試，並要求每個新測試說明它保護的行為。

## 延伸問答

> [!question]- Q1. Hermetic 和 deterministic 有什麼不同？一個測試可以 hermetic 卻不 deterministic 嗎？
> Deterministic（確定性）描述的是結果：同樣的輸入，每次都得到同樣的結果。Hermetic 描述的是輸入的範圍：測試只依賴它明確宣告與控制的輸入，不受外部環境影響。Hermeticity 是達成 determinism 最主要的手段，因為大部分的不確定性來自沒有被控制的外部輸入。
>
> 但兩者不完全相同。一個測試可以完全 hermetic（所有依賴都在測試自己的容器中、沒有網路、沒有共享資料），卻仍然不 deterministic，例如它啟動多個執行緒，結果取決於作業系統的執行緒排程。執行緒排程在概念上也是一個隱藏輸入，但它通常無法透過隔離環境來控制，需要另外的方法：把並行邏輯設計成可以用確定性的排程器測試、用 invariant 檢查所有可能的交錯，或用大量重跑與壓力測試提高發現問題的機率。

> [!question]- Q2. 你是 Harbor 的值班工程師。一個 PR 的 CI 中，`test_inventory_reserve_concurrent` 失敗了一次，作者說「這個測試本來就 flaky，重跑就好」。你會怎麼做？
> 我會先不同意直接重跑，至少不是在了解原因之前。這個測試的名稱就說明它在測並行行為，而並行測試的偶發失敗，很可能反映的是產品真的有 race condition，只是不是每次都會觸發。如果真是如此，重跑通過只代表這次運氣好，bug 仍然存在。
>
> 具體做法是：先看失敗的訊息與 log，判斷失敗的內容是什麼（例如庫存數字少扣了，還是只是逾時）；查這個測試在主線上的歷史，是否在這個 PR 之前就有相同的失敗；在本機或 CI 上對這個 PR 的程式碼大量重跑並增加並行度，看能否穩定重現。如果失敗的內容是「庫存不一致」，而且這個 PR 修改了扣庫存的程式，就應該把它當成產品 bug 處理，而不是 flaky。如果確認是測試本身的問題，也要開 ticket 交給 owner，而不是默默重跑。

> [!question]- Q3. 計算題：Harbor 的 CI suite 有 1,200 個測試，平均每個測試的 flaky 率是 0.05%。一個正確的提交看到紅燈的機率是多少？如果要讓這個機率降到 5% 以下，平均 flaky 率要多低？
> 全綠的機率是 (1 − 0.0005)^1200。用近似 (1 − p)^N ≈ e^(−pN)，pN = 0.6，e^(−0.6) ≈ 0.549，所以正確提交看到至少一個紅燈的機率約為 45%。也就是說，將近一半的正確提交會遇到與自己無關的失敗。
>
> 要讓這個機率低於 5%，需要 (1 − p)^1200 ≥ 0.95，也就是 pN ≤ −ln(0.95) ≈ 0.0513，p ≤ 0.0513 / 1200 ≈ 0.0043%，大約每 23,000 次執行才允許失敗一次。這個數字說明了兩件事：一是 suite 越大，對單一測試穩定性的要求就越嚴苛；二是實務上很難讓所有測試都達到這個水準，所以需要 quarantine 把最不穩定的那幾個移出閘門，並把非 hermetic 的 larger tests 和每次提交都要跑的 suite 分開。

> [!question]- Q4. 為什麼「重試後通過」不應該被當成「通過」？難道 CI 不該重試嗎？
> 重試本身不是錯的，錯的是把重試的結果和第一次就通過混為一談。一個測試第一次失敗、重試後通過，提供了兩個資訊：它在這段程式碼上有時會失敗。這可能是測試或環境的問題，也可能是產品真的有間歇性 bug。如果 CI 只回報「通過」，這個資訊就消失了，沒有人會知道這個測試正在變得不穩定，更不會有人去調查產品是否有問題。
>
> 比較好的設計是：允許有限的重試（例如一次），避免一個偶發失敗阻擋所有人；但重試後通過的結果要被標記為「flaky」，寫進測試結果資料庫，算入這個測試的 flaky 率，超過門檻時自動通知 owner。對於涉及金流、庫存、權限等高風險區域的測試，或明顯在測並行行為的測試，甚至可以設定為不重試，第一次失敗就要人看。這樣重試是一個降低摩擦的工具，而不是一個隱藏問題的工具。

> [!question]- Q5. Kevin 想把 coverage 門檻從 85% 提高到 95%，理由是「事故還是很多，表示測試不夠」。你會怎麼回應？
> 我會先同意「測試可能不夠」這個方向，但提出 coverage 門檻可能不是對的手段。首先，事故多不一定是 unit test 的 coverage 問題。需要先看最近幾次事故的 postmortem：它們的原因是被執行過但沒被檢查的邏輯、完全沒被執行的程式碼，還是設定、跨服務互動、負載這類 unit test 本來就抓不到的問題（第 25 章）？如果是後者，把 coverage 從 85% 提高到 95% 幾乎不會減少事故。
>
> 其次，從 85% 到 95% 的最後十個百分點，通常是最難測、最低價值的程式碼，強制要求會產生大量沒有斷言、綁定實作的測試，增加維護成本卻不增加保護。比較有效的做法是：從事故倒推，看哪些行為應該被測試卻沒有；在 code review 中要求說明變更中未覆蓋的高風險程式碼；對核心模組（例如價格、庫存、付款）導入 mutation 分析，處理存活的 mutant。如果仍想要一個數字，可以追蹤「事故中有多少比例本可以被某一層測試抓到」，這比 coverage 更接近 Kevin 真正關心的事。

> [!question]- Q6. 什麼是 equivalent mutant？它為什麼讓 mutation testing 變得困難？
> Equivalent mutant（23.9 節介紹過的三類存活 mutant 之一）是指程式被突變後，對所有可能的輸入，行為都和原版完全一樣的 mutant。例如在一個函式開頭已經檢查過 `if x < 0: return`，後面再把 `x >= 0` 改成 `x > -1`，對整數來說兩者等價。因為行為沒有改變，任何測試都不可能殺死它。
>
> 它帶來兩個困難。第一，它會讓 mutation score 看起來比真實低：如果把等價 mutant 算進分母，即使測試完美也到不了 100%。第二，判斷一個存活的 mutant 是否等價，一般而言無法完全自動化，常常需要人去閱讀程式碼思考，這是 mutation testing 最主要的人力成本之一。實務上的處理方式包括：讓工具使用已知會產生較少等價 mutant 的突變運算子、避開不太可能有意義的程式碼（例如 log 語句），以及在 review 中允許作者把某個 mutant 標記為等價並說明理由。AI 可以協助初步判斷，但最後的標記應該由人確認。

> [!question]- Q7. AI 情境：一個 coding agent 被要求「修好 `test_checkout_e2e` 的 flakiness」。它提交的 PR 把等待時間從 5 秒改成 30 秒，並加上失敗時重試 3 次。你會核准嗎？
> 不會直接核准。這個修改沒有回答「哪一個隱藏輸入在變動」，只是讓失敗變得不容易被看見。加長等待時間會讓測試變慢，而且如果原因是共享資料或產品 bug，它仍然會失敗，只是頻率降低；加上 3 次重試則會把可能存在的產品 bug 也一起洗掉，這正是 26.5 節的問題。
>
> 我會要求 agent（或作者）先做分析：列出過去失敗的 log 與時間分佈，判斷失敗的原因是 payments sandbox 不可用、測試資料被其他測試搶走、還是 checkout 在處理 callback 時真的有問題；針對找到的原因提出確定性的修法，例如把固定等待改成輪詢訂單狀態、讓測試使用專屬的測試商品、或修正產品 bug。這也說明了為什麼 CI 政策應該讓「修改 timeout 或新增重試」的變更需要測試 owner 額外核准，以及為什麼要求 agent 在 PR 中說明根因，而不只是說明改了什麼。

> [!question]- Q8. 面試題：你加入一個團隊，CI 有 300 個測試，大家都說「CI 很不穩，常常要重跑」。你的前 30 天會怎麼做？
> 第一步是把「很不穩」變成數據。從 CI 的歷史結果中找出每個測試的失敗率、同一個 commit 上結果不一致的次數，以及重跑的頻率。通常會發現 flakiness 高度集中：少數幾個測試貢獻了大部分的失敗。同時估計它的成本，例如每週浪費多少 CI 時間、多少次 merge 被延誤，讓團隊與主管看到這是值得投資的問題。
>
> 第二步是止血與分類。對最不穩定的前幾個測試逐一分類：是產品 bug、測試問題還是環境問題。產品 bug 優先修；測試與環境問題指定 owner、開 ticket，必要時 quarantine，但要有期限。同時檢查 CI 的重試設定：如果有自動重試，改成記錄並回報 flaky，而不是靜默通過。第三步是防止新的 flaky 進來：在 review 中注意時間、亂數、共享狀態與固定等待的使用，提供 fake clock、test data builder 等工具讓正確的寫法變簡單，並建立一個每週檢視 flaky 數量與 quarantine 年齡的節奏。回答時強調「先量測、再分類、最後建立機制」，並提到要先懷疑產品本身，會讓面試官看到你理解 flaky test 最危險的地方。

## 延伸閱讀

- [Software Engineering at Google — Testing Overview](https://abseil.io/resources/swe-book/html/ch11.html)：flaky test 對信任的傷害、test size 與 hermeticity 的關係，以及 Google 對 code coverage 的看法。
- [Software Engineering at Google — Unit Testing](https://abseil.io/resources/swe-book/html/ch12.html)：可維護測試與清晰斷言的原則，是理解「為什麼 coverage 不等於檢查」的基礎。
- [Software Engineering at Google — Larger Testing](https://abseil.io/resources/swe-book/html/ch14.html)：hermetic SUT、測試資料與 larger tests 中的 flakiness 管理。
- [Site Reliability Engineering — Testing for Reliability](https://sre.google/sre-book/testing-reliability/)：從可靠性角度看測試，包括測試環境與 production 的差異。
- [Google Testing Blog — Code Coverage Best Practices](https://testing.googleblog.com/2020/08/code-coverage-best-practices.html)：26.7 節 60%／75%／90% 參考值與「在 code review 中討論未覆蓋程式碼」的原文出處。
- [State of Mutation Testing at Google](https://research.google/pubs/state-of-mutation-testing-at-google/)：Petrović 與 Ivanković 的 ICSE SEIP 2018 論文，說明以 diff 為基礎、略過 arid 程式行、在 code review 中呈現存活 mutant 的做法。
