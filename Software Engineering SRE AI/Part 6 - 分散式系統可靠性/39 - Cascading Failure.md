---
chapter: 39
title: Cascading Failure：Deadline、Retry、Backoff 與 Circuit Breaker
part: 6
---

# 第 39 章　Cascading Failure：Deadline、Retry、Backoff 與 Circuit Breaker

> [!abstract] 本章地圖
> **核心問題**：一個依賴只是變慢一點，為什麼能在幾分鐘內拖垮整個系統，而且在依賴恢復之後還回不來？
>
> **你會學到**：
> - 看懂 cascading failure 的正回饋迴路，以及最常見的觸發條件
> - 區分 timeout 與 deadline，依延遲分佈設定 timeout，並把剩餘 deadline 傳遞到下游
> - 計算多層 retry 的放大倍數，決定在哪一層、用什麼條件重試
> - 實作 exponential backoff＋jitter 與 retry budget，並知道它們各自解決什麼
> - 設計 circuit breaker 與 bulkhead，把故障圈在小範圍內
> - 辨認 metastable failure，並用測試與演練提早發現 cascading failure
>
> **前置知識**：第 37 章（health check 與 lame duck）、第 38 章（queue、load shedding、adaptive throttling）
>
> **對應原書**：SRE 第 22 章〈Addressing Cascading Failures〉；SRE 第 21 章〈Handling Overload〉中關於 retry 的部分

## 39.1 故事：inventory 只慢了兩秒，整個網站倒了半個多小時

11 月 10 日晚上十點，距離雙十一午夜開賣還有兩小時，Harbor 的流量已經是平日的四倍（還不是第 36 章預估的午夜尖峰，那時會到平日的 6 倍；checkout 也已在三天前依計畫預先擴容到約 150 台），但一切都在第 38 章建立的防護之內：shedding 只丟了少量背景工作，商品頁的推薦區塊在 21:40 推薦服務變慢時就已經用 flag 關掉，checkout 的成功率 99.95%。十點零三分，inventory 的主資料庫（第 36 章的 1 主 2 replica，分佈在三個 zone）因為硬體問題，自動 failover 到另一個 zone 的 replica。這次 failover 本身很順利，只花了二十幾秒，但這段期間 inventory 的查詢延遲從 30 ms 升到 2 秒以上。

接下來的事情發生得很快。Checkout 呼叫 inventory 的 timeout 是 3 秒，失敗會重試 3 次；web 前端呼叫 checkout 的 timeout 是 10 秒，也會重試 3 次；手機 app 在逾時後還會自動再送一次。每一層的設定單獨看都合理，疊起來之後，一個使用者按下「結帳」，最壞會在 inventory 產生 4 × 4 × 2 = 32 次呼叫。更糟的是，checkout 對 inventory 的 4 次嘗試最多要花 4 × 3 = 12 秒，比 web 的 10 秒 timeout 還長：web 已經放棄並重送，前一輪 checkout 卻還在重試，新舊兩輪的重試疊在一起。Inventory 的請求量在一分鐘內變成原本的五倍。

Checkout 的 thread pool 有 200 條 thread，全部卡在等 inventory 回應。連不需要 inventory 的「查詢訂單」也排不到 thread，開始逾時。Checkout 的 health check 也跑在同一個 thread pool 上，於是 health check 開始失敗，load balancer 把 checkout instance 一台台移出服務。剩下的 instance 分到更多流量，倒得更快。十點零六分，Harbor 的首頁、購物車、訂單查詢全部無法使用。

最令人困惑的是十點零五分以後：資料庫 failover 已經完成，inventory 的單次查詢延遲回到 30 ms，系統卻沒有恢復。Inventory 的 queue 裡塞滿了早已被放棄的請求和不斷湧入的重試，每個新請求仍然要排好幾秒，於是繼續逾時、繼續重試。SRE 志明試了重啟 checkout，新的 instance 一上線就被重試流量淹沒。團隊最後在 edge 把結帳以外的流量全部擋掉、用 flag 關掉 app 的自動重試，等 queue 清空後再逐步放回流量，十點四十分才恢復服務。這起事故後來編號為 INC-1110。團隊沒有太多時間喘息：一個多小時後的午夜尖峰，另一起與這次無關的付款重複扣款事故 INC-1111 接著發生，第 44、45 章會從 incident command 與 postmortem 的角度回到那一晚。

事後 postmortem 中，美華指出一個關鍵：**觸發事故的資料庫問題只持續了二十幾秒，讓事故持續將近四十分鐘的是我們自己的 retry、timeout 與 health check 設計**。這一章要拆解的，就是一個局部問題如何透過這些「單獨看都合理」的機制擴散成全面故障，以及要怎麼切斷它。

## 39.2 Cascading failure 的機制：會自我加強的迴路

### 定義

**Cascading failure**（連鎖故障）是指一個元件的故障，透過正回饋迴路，造成其他元件接連故障，而且故障會隨時間擴大，而不是停留在原地。關鍵詞是**正回饋**（positive feedback）：結果會回頭加強原因。暖氣的恆溫器是負回饋（太熱就關掉，讓溫度回落）；麥克風靠近喇叭產生的尖嘯是正回饋（聲音被放大後又被收進去再放大）。Cascading failure 是分散式系統裡的尖嘯。

```text
             ┌──────────────────────────────────────────┐
             ▼                                          │
   下游變慢或失敗                                        │
             │                                          │
             ▼                                          │
   上游的 thread／連線被佔住更久 ──▶ 上游自己也變慢     │
             │                          │               │
             ▼                          ▼               │
   timeout 增加 ──▶ retry 增加 ──▶ 送到下游的負載上升 ─┘
             │
             ▼
   health check 失敗 ──▶ instance 被移除 ──▶ 剩下的 instance 負載更高 ─┐
             ▲                                                          │
             └──────────────────────────────────────────────────────────┘
```

圖裡有兩個迴路。上面的迴路是**負載放大**：下游變慢讓上游 timeout，timeout 觸發 retry，retry 讓下游負載更高、變得更慢。下面的迴路是**容量縮減**：資源被佔住讓 health check 失敗，instance 被移除，剩下的 instance 負載更高，更多 health check 失敗。兩個迴路同時運轉時，系統會在幾分鐘內從「有點慢」走到「全部掛掉」。

### SRE 書整理的成因

SRE 書把 cascading failure 的常見成因分成三大類：server overload、resource exhaustion、service unavailability，並在 resource exhaustion 底下特別討論「資源之間的依賴」。下面把這一點獨立出來講，因為 Harbor 的事故幾乎全部碰到了：

1. **Server overload**（伺服器過載）：最常見的起點。一部分 instance 過載後變慢或崩潰，負載轉移到其他 instance，使它們也過載。
2. **Resource exhaustion**（資源耗盡）：不同資源耗盡的症狀不同。CPU 不足讓所有請求變慢、queue 變長；記憶體不足造成更頻繁的 GC、cache 命中率下降，甚至 process 被系統殺掉；thread 耗盡讓新請求無法處理、health check 失敗；file descriptor 或連線耗盡讓服務無法開新連線。
3. **資源之間的依賴**：一種資源的問題會轉成另一種。Harbor 的例子是：inventory 變慢（延遲）→ checkout thread 被佔住（thread 耗盡）→ 在途請求佔用的記憶體上升（記憶體）→ GC 時間上升（CPU）。只看任何一個資源的儀表板，都看不出問題的全貌。
4. **Service unavailability**（服務不可用）：一個 instance 崩潰後，它的負載會轉到其他 instance。

### 為什麼「少一台」可能變成「全部倒」

容量縮減迴路可以用簡單的數字理解。為了讓每一步看得清楚，假設一個只有 10 台 instance 的服務（規模和第 37 章的 inventory 相當；雙十一的 checkout 有約 150 台，每移除一台跳得比較少，但 health check 失敗時機器往往是成批被移除的，結果一樣），每台在 85% 使用率下運作，總負載相當於 8.5 台滿載的量：

```text
10 台 → 每台 85%
 9 台 → 8.5 / 9 ≈ 94%       （第一台因 health check 失敗被移除）
 8 台 → 8.5 / 8 ≈ 106%      （超過 100%，開始排隊與逾時）
 7 台 → 8.5 / 7 ≈ 121%      （更多 health check 失敗）
 ...                        （若沒有 shedding，會一路倒到 0）
```

每移除一台，剩下每台的負載都會跳一大階，而且越後面跳得越多。如果過載的 instance 會因為 health check 失敗而被移除，這個過程就會自動進行到底。這也是第 38 章強調「過載不等於不健康」的原因：一個能用 shedding 保護自己、在過載時仍然回應 health check 的 instance，可以中斷這個迴路。

### 常見的觸發條件

Cascading failure 需要一個起點。SRE 書列出的典型觸發條件包括：process 崩潰或被殺、新版本上線（新程式碼更慢或有 bug）、設定變更、自然成長的流量終於越過臨界點、計畫性的維護（例如把一個資料中心排空，流量轉到其他地方）、請求組成的改變（例如新的 client 送出大量昂貴的查詢），以及資源限制的變化（例如叢集允許 CPU 超賣，鄰居的批次工作突然吃掉多餘的 CPU）。Harbor 的觸發條件是資料庫 failover，屬於依賴的短暫延遲上升。重點是：**觸發條件通常無法完全避免，能控制的是系統對觸發條件的反應**。

## 39.3 Timeout 與 deadline：等待必須有上限

### 不設 timeout 的代價

每一次呼叫下游，都在佔用自己的資源：一條 thread、一個連線、一塊記憶體。如果下游永遠不回應，而呼叫端也永遠等下去，這些資源就永遠不會被釋放。**Timeout**（逾時）是單一次操作最多等待多久的上限，它的第一個目的不是讓使用者早點拿到錯誤，而是**保護呼叫端自己的資源**。很多 HTTP client library 的預設 timeout 非常長，甚至沒有上限，這是 cascading failure 最常見的溫床之一。

### Timeout 怎麼設

Timeout 太長，下游變慢時資源被佔住太久，cascading 更快發生；timeout 太短，正常的長尾請求被誤判為失敗，觸發不必要的 retry，反而增加下游負載。合理的設定方法是：

1. **從下游的延遲分佈出發**：看下游在正常負載下的 p99 或 p99.9，timeout 設在略高於它的位置。如果 inventory 的 p99.9 是 120 ms，timeout 設 300 ms 是合理的起點；設 3 秒則讓每次異常都佔住 thread 3 秒。
2. **不能超過呼叫端自己剩下的時間**：如果 checkout 收到請求時只剩 800 ms，對 inventory 的 timeout 就不能是 3 秒。
3. **分開設定 connect timeout 與 request timeout**：建立連線通常很快，connect timeout 可以很短（例如 100 ms 等級），讓「連不上」的情況快速失敗；request timeout 才依處理時間設定。
4. **把 queue 的等待也算進去**：如果請求在 client library 的連線池裡排隊等連線，這段時間也應該計入 timeout，否則實際等待會遠超過設定值。

### Deadline：整個操作的總時間預算

Timeout 是單一步驟的上限，**deadline**（截止時間）則是整個使用者操作最晚必須完成的時間點。兩者的差別在多層呼叫時特別明顯：

```text
沒有 deadline propagation：每層各自計時
  web ──(timeout 10s)──▶ checkout ──(timeout 3s)──▶ inventory
  使用者 5 秒後就放棄了，但 checkout 還在等 inventory，inventory 還在查資料庫

有 deadline propagation：剩餘時間一路往下傳
  使用者願意等 2.0 s
  web 收到：剩 2.0 s ── 自己花 0.1 s ──▶ checkout 收到：剩 1.9 s
  checkout 花 0.2 s ──▶ inventory 收到：剩 1.7 s（再扣掉預估的網路時間）
  inventory 在 queue 裡等了 1.8 s → 取出時發現已過期 → 直接丟棄，不查資料庫
```

**Deadline propagation**（deadline 傳遞）讓每一層都知道「這個請求還剩多少時間」。下游拿到請求時先檢查剩餘時間，不夠就立刻放棄，這就是第 38 章 deadline-aware dequeue 的資訊來源。SRE 書描述的模型是：deadline 在 stack 的最上層（例如 frontend）設定一次，整棵 RPC 樹共享同一個截止時間點；例如 A 設了 30 秒、自己處理了 7 秒，送給 B 的就只剩 23 秒。gRPC 內建這個機制：client 設定的 deadline 會透過 `grpc-timeout` header 傳給 server，server 用它建立 context，只要再呼叫下游時沿用這個 context，剩餘時間就會繼續往下傳。用 HTTP 的系統則需要自己定義 header，並由共用的 client library 自動處理。

傳遞時有兩個細節。第一，邏輯上大家共享同一個截止時間點，但在網路上傳的通常是**剩餘的時間長度**（例如「還有 1,700 ms」），而不是絕對時間點（例如「22:03:15.300 截止」），因為不同機器的時鐘可能有誤差；gRPC 的 `grpc-timeout` 就是這樣做的。第二，SRE 書建議送出時把 deadline 再縮短一點（例如幾百毫秒），預留網路傳輸與 client 收到回應後處理的時間，避免下游剛好在 deadline 那一刻才完成，回傳時已經來不及。

### Cancellation：放棄也要往下傳

Deadline 處理的是「時間到了」。另一種情況是使用者主動取消（關掉頁面）、或上游因為其他原因放棄（例如平行呼叫的另一個已經成功）。**Cancellation propagation**（取消傳遞）讓上游放棄時，下游也立刻停止工作，釋放資源。Go 的 `context`、gRPC 的 cancellation 都支援這個模式。沒有它，上游放棄的請求仍會在下游跑完，成為第 38 章說的白工。

### 雙峰延遲的陷阱

SRE 書提到一種容易忽略的情況，稱為 **bimodal latency**（雙峰延遲）：大部分請求很快，但一小部分請求因為某種原因卡到 deadline 才失敗。原書的例子是某段資料暫時無法存取，對應的請求全部等到 deadline；在 Harbor，可能是查詢一個超大賣家的請求。假設 95% 的請求 50 ms 完成、5% 卡 10 秒。以 thread 佔用時間來算，那 5% 的請求佔用的 thread 時間是 95% 的請求的十倍以上。只看 p50 或平均延遲會完全看不到這件事，但 thread pool 已經被那 5% 吃光。對策是監控延遲分佈而不只是平均值；讓註定無法完成的請求盡早回錯誤，而不是等滿 deadline；把 deadline 設在和正常延遲同一個量級，而不是大上好幾個數量級；並限制單一類請求或單一 client 能佔用的 thread（原書舉的例子是單一 client 最多佔 25%）。

## 39.4 Retry：救一個請求，可能害死整個系統

### Retry 什麼時候有用

**Retry**（重試）在一個條件下有幫助：失敗是**暫時的、隨機的**，而且下游**還有容量**。例如一次網路封包遺失、連到一台剛好在重啟的 instance、一次 leader 選舉期間的短暫錯誤。這時再試一次，很可能被送到另一台健康的 instance，或者問題已經消失。

反過來，當失敗的原因是**下游過載**時，retry 正好做了最糟的事：在下游最沒有能力的時候，送給它更多工作。Harbor 的事故中，inventory 變慢的原因是資料庫 failover，這時每一個 retry 都在增加 inventory 的負擔。

### 判斷可不可以重試

不是每種失敗都該重試。依錯誤類型區分：

| 錯誤類型 | 例子 | 是否重試 |
|---|---|---|
| 永久性錯誤 | 400 參數錯誤、404 不存在、403 權限不足 | 不重試，再試也一樣 |
| 暫時性錯誤 | 連線被重設、503 某台 instance 暫時不可用 | 可以重試，要退避並受 budget 限制 |
| 過載訊號 | 429、503 附 `Retry-After`、明確的「overloaded」錯誤 | 尊重 `Retry-After`；若下游明確表示過載，通常不在這一層重試 |
| 逾時 | 等不到回應 | 謹慎：下游可能已經執行，需要 idempotency；也可能代表下游過載 |
| 非 idempotent 操作失敗 | 扣款請求逾時 | 只有在有 idempotency key 時才能重試 |

最後一列特別重要。**Idempotent**（冪等）的操作執行一次或多次結果相同，例如「把訂單狀態設為已出貨」；非冪等的操作則每次執行都有新效果，例如「扣款 500 元」。逾時並不代表下游沒有執行：可能扣款已經成功，只是回應在路上遺失。如果直接重試，使用者可能被扣兩次錢。解法是帶上 idempotency key（冪等鍵，第 41 章詳談）：client 為每個邏輯操作產生唯一的 ID，下游記住已處理過的 ID，重複的請求直接回傳上次的結果。

### 多層 retry 的乘法

Retry 最危險的地方在於它會**相乘**。如果一個請求要經過三層，每一層都在失敗時最多嘗試 4 次（1 次原始加 3 次重試），最底層最壞會收到 4 × 4 × 4 = 64 次請求。

```text
使用者 1 次點擊
  └─ web 最多 4 次
       └─ 每次 checkout 最多 4 次  → 16
            └─ 每次 inventory 最多 4 次 → 64
```

這個放大只在下游失敗時發生，所以平常完全看不到；一旦下游開始失敗，送給它的流量會瞬間跳到數十倍，正好在它最脆弱的時候。Harbor 的事故中，app、web、checkout 三層各自的重試設定疊起來，讓 inventory 的負載在一分鐘內變成五倍。SRE 書〈Addressing Cascading Failures〉用的例子和這張圖一樣：資料庫過載時，backend、frontend、JavaScript 三層都重試 3 次（4 次嘗試），一個使用者動作最多會在資料庫產生 64 次嘗試。

SRE 書〈Handling Overload〉的建議是**只在一層重試**：緊接在拒絕請求的那一層之上的那一層。如果 inventory 過載，只有 checkout 對 inventory 的呼叫可以重試；checkout 重試仍失敗時，應該回傳一個明確表示「下游過載，不要重試」的錯誤，讓 web 前端直接把錯誤回給使用者，而不是再重試一輪。原書稱這種錯誤為「overloaded; don't retry」。這需要錯誤碼的設計配合：上游要能分辨「這個錯誤已經重試過了」。

## 39.5 Exponential backoff 與 jitter：重試要錯開

### 為什麼不能立刻重試

立刻重試有兩個問題。第一，如果失敗原因是下游短暫過載，立刻重試等於在它還沒恢復時再打一次。第二，如果很多 client 同時遇到同一個失敗，它們會在同一時間一起重試，形成 **thundering herd**（驚群效應），讓下游在每個重試時間點都承受尖峰。

**Exponential backoff**（指數退避）讓每次重試前的等待時間成倍增加：

```text
等待時間 = min(上限, 基準 × 2^attempt)

基準 100 ms、上限 10 s：
  第 1 次重試前等 200 ms，第 2 次 400 ms，第 3 次 800 ms ……
```

等待時間成倍增加，代表下游的問題持續越久，client 送出重試的頻率就越低，給下游留下恢復的空間。

### Jitter：把同步的 client 打散

只有指數退避還不夠。假設 1,000 個 client 在同一秒遇到錯誤，它們會在完全相同的時間點重試：

```text
沒有 jitter（所有 client 同步）
  時間 →  0.0s      0.2s      0.6s            1.4s
  請求數  ████████  ████████  ████████        ████████
          尖峰       尖峰       尖峰             尖峰

有 full jitter（每個 client 在區間內隨機挑時間）
  時間 →  0.0s ──────────────────────────────── 1.4s
  請求數  ███▆▅▅▄▄▄▃▃▃▃▃▃▃▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂
          尖峰被攤平成一段較低的負載
```

**Jitter**（抖動）在等待時間中加入隨機性。常見的變形有：

- **Full jitter**：等待時間 = random(0, min(上限, 基準 × 2^attempt))，完全隨機。
- **Equal jitter**：一半固定、一半隨機，保證至少等一段時間。
- **Decorrelated jitter**：下次的等待時間依上次的等待時間隨機決定。

AWS Architecture Blog 的〈Exponential Backoff And Jitter〉（Marc Brooker，2015）用模擬比較過這幾種做法：沒有 jitter 的指數退避明顯最差；有 jitter 的版本中 equal jitter 較差，full jitter 與 decorrelated jitter 差距不大，full jitter 讓 client 做的總工作最少、完成時間略長。SRE 書也直接引用這篇文章，要求重試一律使用隨機化的指數退避。實務上，選哪一種不如「一定要有 jitter」重要。

### 尊重 Retry-After

如果下游回傳了 `Retry-After`，它比 client 自己算的退避更有資訊：下游知道自己需要多久恢復。Client library 應該以 `Retry-After` 為準（必要時再加上 jitter），而不是無視它繼續用自己的節奏重試。

> [!warning] 常見誤解
> 「有了 exponential backoff＋jitter，就不會有 retry storm。」Backoff 與 jitter 只改變重試**什麼時候**發生，沒有改變重試**總共**發生幾次。如果每個請求最終仍會嘗試 4 次，在持續性的失敗下，下游收到的總量仍然是原本的 4 倍，只是比較平滑。39.11 的模擬會直接看到這件事：只加 backoff 的系統和立刻重試的系統一樣回不來。限制總量需要下一節的 retry budget。

## 39.6 Retry budget：限制重試的總量

### 兩種限制

**Per-request retry limit**（每個請求的重試上限）限制一個請求最多試幾次。SRE 書〈Handling Overload〉描述 Google 的做法是每個請求最多 3 次嘗試，三次都失敗就把失敗往上傳。它防止單一請求無限重試，但無法限制整體：原書估算，當幾乎所有請求都被拒絕時，總請求量仍會接近原本的 3 倍。

**Retry budget**（重試預算）則限制整個 client（或整個服務）的重試比例。同一章描述的 per-client retry budget 是：每個 client 追蹤重試請求佔所有請求的比例，只有在比例低於 10% 時才允許重試。原書的估算是，疊上這個 budget 後，同樣的最壞情況在一般狀況下只會讓請求量增加到約 1.1 倍。

```text
沒有 retry budget：
  下游正常時 → 重試很少，總量 ≈ 1.0x
  下游全壞時 → 每個請求試 4 次，總量 ≈ 4.0x ← 在最脆弱時放大最多

retry budget 10%：
  下游正常時 → 偶發的錯誤都能重試，總量 ≈ 1.0x
  下游全壞時 → 重試被 budget 擋住，總量 ≤ 1.1x
```

Retry budget 的巧妙之處在於它**自動區分了兩種情況**。偶發的隨機錯誤只佔很小比例，budget 足夠讓每一個都被重試，retry 發揮了它該有的效果；大規模的失敗會迅速用完 budget，多出來的重試被直接放棄，避免在下游最脆弱時放大負載。一個常見的實作方式是 token bucket（不是原書的寫法，而是 RPC 框架常見的做法，39.11 的模擬也用它）：每個新請求存入 0.1 個 token，每次重試花掉 1 個 token，token 不夠就不重試。

SRE 書在〈Addressing Cascading Failures〉一章另外建議考慮 server-wide 的 retry budget，例如一個 process 每分鐘最多重試 60 次，超過就不再重試、直接讓請求失敗。兩種 budget 可以並用。

### Hedged requests 也要算在 budget 裡

另一種「多送請求」的技巧是 **hedged request**（對沖請求）：送出請求後，若一段時間（例如 p95 延遲）內沒有回應，就向另一個 replica 再送一份，誰先回來用誰。Google 的 Jeffrey Dean 與 Luiz André Barroso 在〈The Tail at Scale〉（Communications of the ACM，2013）一文中討論過這種降低尾端延遲的方法；SRE 書也提醒，一旦有一份回應回來，就要把其他份取消，而且取消要一路傳到下游。它在正常時能有效改善 p99，但本質上也是在增加負載，所以必須受到同樣的 budget 限制，並且只用在 idempotent 的讀取操作上。

## 39.7 Circuit breaker：持續失敗時就別再打了

### 為什麼需要

Retry budget 限制了重試，但每個請求仍然會嘗試第一次。如果下游已經完全壞掉，每一次呼叫都要等到 timeout 才失敗，呼叫端的 thread 仍然被佔住。**Circuit breaker**（斷路器）解決的是這個問題：當它偵測到對某個下游的呼叫持續失敗，就暫時停止呼叫，讓請求**立刻失敗**（或走 fallback），不再浪費資源等待，也讓下游有喘息的時間。這個模式因 Michael Nygard 的《Release It!》（2007 年初版）而廣為人知，名字來自電路中的斷路器：電流過大時跳開，保護整條線路。

### 三個狀態

```text
              失敗率超過門檻
   ┌────────┐ ─────────────────▶ ┌────────┐
   │ CLOSED │                    │  OPEN  │  所有呼叫立刻失敗／走 fallback
   │ 正常呼叫│ ◀───┐              └────────┘
   └────────┘     │                  │ 等待一段時間
                  │                  ▼
                  │  探測成功    ┌───────────┐
                  └───────────── │ HALF-OPEN │  只放少量探測請求
                                 └───────────┘
                                     │ 探測失敗
                                     └──────▶ 回到 OPEN
```

- **Closed**（閉合，正常狀態）：呼叫照常進行，breaker 記錄最近一段時間或最近 N 次呼叫的結果。失敗率超過門檻，而且呼叫數夠多（避免少量樣本誤判），就跳到 open。
- **Open**（斷開）：所有呼叫不送到下游，直接失敗或走 fallback。等待一段設定的時間後，進入 half-open。
- **Half-open**（半開）：只放行少量探測請求。如果探測成功，代表下游恢復，回到 closed；如果失敗，回到 open，再等一輪。

Half-open 的設計很重要：它讓系統能**自動恢復**，同時避免所有 client 在下游剛恢復時一起湧入。這呼應 SRE 書提到的恢復原則：下游剛恢復時通常比較脆弱（例如 cache 是冷的），流量要慢慢放回去。

### 設計細節

- **什麼算失敗**：除了錯誤回應，**慢回應也應該算失敗**。一個每次都要 5 秒才成功的下游，對呼叫端的傷害可能比立刻回錯誤更大。
- **範圍**：breaker 的範圍要和故障的範圍對齊。對整個 payments 服務設一個 breaker，可能因為某一種付款方式（例如某家銀行）壞掉，就把所有付款方式都擋掉。比較好的做法是依下游的 endpoint、依外部供應商，甚至依租戶分開。
- **Fallback**：breaker 跳開時要有明確的行為。Harbor 的 checkout 在外部金流商的 breaker 開啟時，把訂單標記為「付款處理中」並在背景重試確認，而不是讓使用者看到錯誤頁；但它**不會**假裝付款成功，因為那會破壞金流的不變量。
- **可觀測**：breaker 的狀態變化必須是 metric 與事件，開啟時通常值得通知值班者。breaker 隱藏了錯誤，如果沒有人知道它開著，問題可能被掩蓋好幾天。

### 和 retry budget、load shedding 的關係

這三個機制常被混淆，其實分工不同：retry budget 在**呼叫端**限制「額外」送出的量；circuit breaker 在**呼叫端**判斷「要不要送出第一次」；load shedding（第 38 章）在**被呼叫端**決定「要不要接受」。完整的防護三者都需要：breaker 讓呼叫端在下游全壞時快速失敗，budget 防止部分失敗時放大負載，shedding 讓下游在呼叫端都沒做好時仍能保護自己。

## 39.8 Bulkhead：把故障關在小隔間裡

### 共用資源是故障的傳播路徑

Harbor 事故中，「查詢訂單」根本不需要 inventory，卻也跟著失敗，原因是它和結帳共用同一個 thread pool。Inventory 一變慢，結帳請求佔滿了 thread，查詢訂單也排不到。**共用的資源池就是故障擴散的管道**。

**Bulkhead**（艙壁）的名字來自船艙的隔間設計：船身破一個洞，只有那一個隔間進水，船不會沉。在軟體中，bulkhead 是把資源分成彼此隔離的池子，讓一個依賴或一類工作出問題時，只能耗盡自己那一份。

```text
沒有 bulkhead：
  checkout thread pool（200）
  ├─ 呼叫 inventory 的請求 ████████████████████  ← inventory 變慢，佔滿全部
  ├─ 呼叫 payments 的請求  （排不到）
  └─ 查詢訂單             （排不到）

有 bulkhead：
  inventory 專用池（80）  ████████████  ← 滿了，只有這類請求失敗
  payments 專用池（60）   ███           ← 不受影響
  查詢訂單專用池（40）     ██            ← 不受影響
  health check（獨立）     ✓
```

### 怎麼切、切多大

Bulkhead 可以依很多維度切：依下游依賴（每個依賴一個連線池）、依請求類型（讀與寫分開）、依 criticality（關鍵與背景工作分開）、依租戶（大客戶有專屬容量）。更大規模的版本是 **cell-based architecture**（單元化架構）：把整個服務堆疊複製成多個獨立的 cell，每個 cell 只服務一部分使用者，一個 cell 壞掉只影響那部分使用者。

池子的大小可以用 Little's Law 估算：所需的並行數 = 每秒請求數 × 每個請求的平均佔用時間。如果 checkout 每秒呼叫 inventory 400 次、正常延遲 50 ms，平均需要 400 × 0.05 = 20 條 thread；考慮尖峰與延遲變異，給 40 到 60 條是合理的範圍。給得太大，失去隔離的意義（inventory 變慢時仍然能吃掉大量資源）；給得太小，正常的尖峰就會被擋。

Bulkhead 的代價是資源利用率下降：每個池子都要預留餘裕，加總起來比一個共用池更浪費。這是用效率換隔離的取捨，對關鍵路徑通常值得。

### 讓 health check 不被拖下水

Bulkhead 最重要的應用之一是 health check。Health check 如果和一般請求共用 thread pool，過載時就會失敗，讓 load balancer 把仍然能工作的 instance 移除，啟動 39.2 的容量縮減迴路。Health check 應該有獨立的處理路徑，並且只檢查「這個 process 是否還能運作」，而不是「所有依賴是否健康」。如果 health check 會因為依賴變慢而失敗，一個依賴的問題就會讓所有呼叫它的服務被 load balancer 移除，這正是一種 cascading failure。

## 39.9 Metastable failure：觸發消失了，系統卻回不來

### 什麼是 metastable failure

Harbor 事故最讓人困惑的部分，是資料庫恢復之後系統仍然壞著。這類現象有一個名字：**metastable failure**（亞穩態故障）。Nathan Bronson、Aleksey Charapko、Abutalib Aghayev 與 Timothy Zhu 在 HotOS 2021 研討會的論文〈Metastable Failures in Distributed Systems〉中系統化地描述了它。直覺的說法是：在同樣的負載下，系統可能停在健康的狀態，也可能停在壞掉的狀態；一個短暫的**觸發**（trigger）把系統推進壞狀態後，某個**維持效應**（sustaining effect）讓它停留在那裡，即使觸發已經消失。論文把系統分成 stable、vulnerable、metastable 三種狀態，下圖用中文對應。

```text
   ┌─────────┐   負載上升     ┌────────────┐   觸發事件      ┌──────────────┐
   │ 穩定狀態 │ ────────────▶ │  脆弱狀態   │ ─────────────▶ │  亞穩態故障   │
   │（有餘裕） │ ◀──────────── │（正常但沒餘裕）│                │（維持效應運轉）│
   └─────────┘   負載下降     └────────────┘                └──────────────┘
                                    ▲                              │
                                    └──────────────────────────────┘
                                     只有大幅降低負載、切斷維持效應才回得去
```

這張圖的重點是中間的「脆弱狀態」。系統在這個狀態下看起來完全正常，所有指標都是綠的，但它已經沒有足夠的餘裕承受一次衝擊。Harbor 雙十一的流量是平常的四倍，就是處在脆弱狀態。一旦觸發事件發生，系統跌進右邊的故障狀態，而回去的路不是原路：觸發消失（資料庫恢復）不夠，必須主動把負載壓到遠低於平常的程度，才能讓維持效應停下來。

### 常見的維持效應

- **Retry**：最常見的一種。故障讓請求逾時，逾時產生重試，重試讓負載維持在容量以上，於是請求繼續逾時。Harbor 的事故就是這種。
- **冷 cache**：服務重啟或 cache 被清空後，命中率下降，大量請求直接打到資料庫，資料庫變慢，cache 因為請求逾時而無法被填滿。SRE 書在討論 slow startup 與 cold caching 時描述過這個問題：剛啟動的服務能力比穩態低，需要逐步放入流量。
- **GC 與記憶體**：queue 變長讓記憶體上升，GC 變頻繁，處理變慢，queue 更長。
- **失敗的副作用**：例如失敗會觸發額外的記錄、告警或補償工作，這些工作本身又消耗資源。

### 怎麼脫離與預防

脫離 metastable failure 的共同方法是**讓負載降到維持效應無法運轉的程度**，而且通常要低於正常負載：在 edge 擋掉大量流量、關閉 client 的自動重試、暫停批次工作，等系統清空 queue、cache 回溫後，再逐步放回流量。只是重啟服務通常沒有用，因為新的 instance 一上線就會面對同樣的負載。

預防則要從兩方面著手：一是**削弱維持效應**，例如 retry budget 讓重試無法把負載放大到容量以上、deadline-aware dequeue 讓 queue 裡的過期請求不消耗資源、cache 的預熱與逐步放流量；二是**保留足夠的餘裕**，讓系統不要長時間停留在脆弱狀態。容量規劃（第 36 章）時，除了問「能不能撐住預期尖峰」，還要問「在預期尖峰時，如果一個依賴慢了 30 秒，系統能不能自己恢復」。

## 39.10 測試與演練：在事故之前看見 cascade

### 測到故障為止，然後繼續

SRE 書建議的測試方法是：**對服務施加負載直到它故障，然後再繼續加**。目的是回答幾個問題：在什麼負載下開始劣化？劣化時是逐步退讓還是突然崩潰？負載移除後，它能不能自己恢復？如果需要人工介入，要做什麼？第 38 章的 overload test 已經涵蓋前三個問題（膝蓋在哪裡、超過膝蓋後是否崩塌、流量退去後能否自己恢復），但它只是單純加大流量。Cascading failure 的測試要再往前一步：在**觸發事件**（依賴變慢、instance 被移除）發生時測試**恢復**，並回答第四個問題：自己恢復不了時，人工介入的步驟是什麼、要多久。

### 注入延遲，不只注入錯誤

很多團隊的 chaos experiment（第 25 章）只注入錯誤，例如讓依賴回傳 500。但 cascading failure 最常見的起點是**變慢**，而不是失敗：立刻失敗的依賴很容易處理，慢吞吞的依賴才會佔住資源、觸發 timeout 與 retry。Harbor 的演練現在固定包括：

1. 讓 inventory 的延遲增加 1 秒、持續 60 秒，觀察 checkout 的 thread 使用率、retry 比例與 breaker 狀態，並確認延遲恢復後 60 秒內系統回到正常。
2. 讓一個非關鍵依賴（例如推薦服務）完全不回應，確認商品頁走降級路徑，而不是被拖慢。
3. 在模擬雙十一的負載下重複上述實驗，因為同樣的觸發在脆弱狀態下的後果完全不同。
4. 一次移除多台 instance，確認剩下的 instance 會 shed 而不是一台接一台倒下。

### 稽核 client 設定

事故前沒有人知道 Harbor 的三層重試會疊成 32 倍，因為設定分散在四個 repo、三種語言的 client library 裡。事後 Harbor 做了兩件事：把所有 RPC 呼叫統一到一個共用 client library，預設值是「只重試 idempotent 呼叫、最多 3 次嘗試、full jitter、retry budget 10%、傳遞 deadline 與 criticality」；並在 CI 中加入檢查，任何自訂 timeout 或 retry 設定的變更都要附上理由並經過 SRE review。

### 要觀測的訊號

| 訊號 | 為什麼重要 |
|---|---|
| 每個使用者請求平均產生的下游呼叫數 | 直接反映 retry 放大，平常應接近固定值 |
| Retry 比例（retry ÷ 所有請求），依下游分 | 突然上升代表下游有問題，也代表放大正在發生 |
| Circuit breaker 狀態 | 開啟代表某個依賴已被隔離，值班者應該知道 |
| 每個 bulkhead 的使用率 | 哪個依賴正在吃掉資源 |
| 因 deadline 不足而被丟棄的請求數 | Deadline propagation 正在發揮作用的證據，也是上游等太久的訊號 |
| Health check 失敗數與被移除的 instance 數 | 容量縮減迴路是否正在啟動 |

### 事故當下的應對

SRE 書列出了處理 cascading failure 的即時手段，Harbor 把它們寫進了 runbook，依序考慮：

1. **增加資源**：如果系統還在劣化初期，擴容可能有幫助；但如果已經進入 metastable 狀態，新資源會被立刻淹沒。
2. **停止 health check 造成的死亡**：暫時放寬或停用會因過載而失敗的 health check，避免 load balancer 繼續移除 instance。
3. **重啟 server**：只在 server 卡死、沒有進展時才有用，例如 GC death spiral、沒有 deadline 的請求佔住 thread、deadlock。重啟前要先確認原因，否則就像 Harbor 當晚一樣，新 instance 一上線就被淹沒；如果問題其實是冷 cache，重啟還會讓情況更糟。
4. **降低負載**：在 edge 大幅限流，必要時只放行關鍵流量，讓系統清空 queue；穩定後再逐步放回流量，觀察是否再次惡化。
5. **進入降級模式**：啟用第 38 章的降級 flag。
6. **停止批次與背景工作**：把資源讓給線上流量。
7. **消除不良流量**：如果某個 client 或某類請求（例如會讓 process 崩潰的 query of death）是負載來源，直接擋掉。

## 39.11 動手寫：retry storm 與 circuit breaker 模擬

### 模擬一：metastable retry storm

下面的程式模擬 Harbor 事故的簡化版：inventory 有一個 worker，每個請求 10 ms（容量每秒 100 個），使用者每秒送 80 個請求（80% 使用率）。Checkout 呼叫 inventory 的 timeout 是 1 秒，逾時最多再試 3 次。第 20～25 秒資料庫 failover，每個請求變成 40 ms，之後恢復正常。我們比較三種 retry 策略。這些數字（10 ms、80 req/s、1 秒 timeout、5 秒的變慢）都是為了讓現象在 90 秒內清楚出現而選的假設值，不是 Harbor 的實際設定；模型也刻意簡化成單一 worker、只有 checkout 一層重試。

```python
import heapq
import random
from collections import deque

SERVICE_MS = 10            # inventory 每個請求 10 ms → 單一 worker 容量 100 req/s
TIMEOUT_MS = 1000          # checkout 等 inventory 最多 1 秒
USER_RATE = 80             # 使用者每秒 80 個請求（平常 80% 使用率）
SIM_S = 90


def simulate(policy, seed=42):
    rng = random.Random(seed)
    events = []                                   # (時間, 序號, 種類, 資料)
    seq = 0

    def push(t, kind, data):
        nonlocal seq
        seq += 1
        heapq.heappush(events, (t, seq, kind, data))

    t = 0.0
    while t < SIM_S * 1000:                       # 先排好所有使用者請求
        t += rng.expovariate(USER_RATE / 1000)
        push(t, "user", None)

    queue = deque()
    busy_until = 0.0
    tokens = 10.0                                 # retry budget：每個新請求存 0.1 個 token
    sent = [0] * SIM_S                            # 每秒送到 inventory 的 attempt 數
    ok = [0] * SIM_S
    users = [0] * SIM_S
    req_id = 0
    done = set()          # 已經結束（成功或被放棄）的 attempt
    succeeded = set()     # 已經成功的使用者請求

    def send(now, rid, attempt, start):
        sec = int(now // 1000)
        if sec < SIM_S:
            sent[sec] += 1
        queue.append((now, rid, attempt, start))
        push(now + TIMEOUT_MS, "timeout", (rid, attempt, start))

    while events:
        now, _, kind, data = heapq.heappop(events)
        if now > SIM_S * 1000:
            break
        if kind == "user":
            req_id += 1
            users[int(now // 1000)] += 1
            tokens = min(10.0, tokens + 0.1)
            send(now, req_id, 1, now)
        elif kind == "timeout":
            rid, attempt, start = data
            if (rid, attempt) in done or rid in succeeded:
                continue
            done.add((rid, attempt))              # 這個 attempt 被 client 放棄了
            if attempt >= 4:                      # 最多 1 次原始 + 3 次 retry
                continue
            if policy == "naive":
                send(now, rid, attempt + 1, start)
            elif policy == "backoff":
                delay = rng.uniform(0, 100 * 2 ** attempt)   # full jitter
                push(now + delay, "retry", (rid, attempt + 1, start))
            elif policy == "budget" and tokens >= 1:
                tokens -= 1
                delay = rng.uniform(0, 100 * 2 ** attempt)
                push(now + delay, "retry", (rid, attempt + 1, start))
        elif kind == "retry":
            rid, attempt, start = data
            send(now, rid, attempt, start)
        # 推進 inventory：把「現在之前就能開始」的工作依序做掉
        while queue and busy_until <= now:
            arrived, rid, attempt, start = queue.popleft()
            begin = max(busy_until, arrived)
            if policy == "budget" and begin - arrived >= TIMEOUT_MS:
                continue                          # deadline 已過：丟掉，不浪費 worker
            # 第 20～25 秒：inventory 的資料庫 failover，每個請求變成 40 ms
            service = 40 if 20_000 <= begin < 25_000 else SERVICE_MS
            busy_until = begin + service
            if busy_until - arrived < TIMEOUT_MS and rid not in succeeded:
                succeeded.add(rid)
                done.add((rid, attempt))
                ok[int(start // 1000)] += 1
    return users, sent, ok


print("每 10 秒一格：使用者請求 → 送到 inventory 的 attempt（放大倍數）→ 成功")
for policy, label in [("naive", "立刻重試 3 次"), ("backoff", "指數退避＋jitter"),
                      ("budget", "退避＋retry budget 10%＋丟過期")]:
    users, sent, ok = simulate(policy)
    print(f"--- {label}")
    for s in range(0, SIM_S, 10):
        u, a, g = sum(users[s:s+10]), sum(sent[s:s+10]), sum(ok[s:s+10])
        print(f"  {s:>2}–{s+9:>2} 秒  使用者 {u:>4}  attempts {a:>5} ({a/u:4.1f}x)  成功 {g/u:6.1%}")
```

執行結果：

```text
每 10 秒一格：使用者請求 → 送到 inventory 的 attempt（放大倍數）→ 成功
--- 立刻重試 3 次
   0– 9 秒  使用者  776  attempts   776 ( 1.0x)  成功 100.0%
  10–19 秒  使用者  794  attempts   794 ( 1.0x)  成功 100.0%
  20–29 秒  使用者  781  attempts  2534 ( 3.2x)  成功   4.6%
  30–39 秒  使用者  781  attempts  3157 ( 4.0x)  成功   0.0%
  40–49 秒  使用者  803  attempts  3187 ( 4.0x)  成功   0.0%
  50–59 秒  使用者  859  attempts  3403 ( 4.0x)  成功   0.0%
  60–69 秒  使用者  797  attempts  3229 ( 4.1x)  成功   0.0%
  70–79 秒  使用者  814  attempts  3239 ( 4.0x)  成功   0.0%
  80–89 秒  使用者  800  attempts  3156 ( 3.9x)  成功   0.0%
--- 指數退避＋jitter
   0– 9 秒  使用者  776  attempts   776 ( 1.0x)  成功 100.0%
  10–19 秒  使用者  794  attempts   794 ( 1.0x)  成功 100.0%
  20–29 秒  使用者  781  attempts  2459 ( 3.1x)  成功   4.6%
  30–39 秒  使用者  781  attempts  3166 ( 4.1x)  成功   0.0%
  40–49 秒  使用者  803  attempts  3164 ( 3.9x)  成功   0.0%
  50–59 秒  使用者  859  attempts  3391 ( 3.9x)  成功   0.0%
  60–69 秒  使用者  797  attempts  3247 ( 4.1x)  成功   0.0%
  70–79 秒  使用者  814  attempts  3228 ( 4.0x)  成功   0.0%
  80–89 秒  使用者  800  attempts  3160 ( 4.0x)  成功   0.0%
--- 退避＋retry budget 10%＋丟過期
   0– 9 秒  使用者  776  attempts   776 ( 1.0x)  成功 100.0%
  10–19 秒  使用者  794  attempts   794 ( 1.0x)  成功 100.0%
  20–29 秒  使用者  781  attempts   823 ( 1.1x)  成功  63.1%
  30–39 秒  使用者  781  attempts   781 ( 1.0x)  成功 100.0%
  40–49 秒  使用者  803  attempts   803 ( 1.0x)  成功 100.0%
  50–59 秒  使用者  859  attempts   859 ( 1.0x)  成功 100.0%
  60–69 秒  使用者  797  attempts   797 ( 1.0x)  成功 100.0%
  70–79 秒  使用者  814  attempts   814 ( 1.0x)  成功 100.0%
  80–89 秒  使用者  800  attempts   800 ( 1.0x)  成功  99.6%
```

逐段解讀：

1. **立刻重試 3 次**：前 20 秒一切正常，每個使用者請求只產生 1 個 attempt。第 20 秒觸發後，queue 開始變長，請求逾時，重試湧入。關鍵在第 30 秒之後：觸發早已消失，inventory 每個請求又只需要 10 ms，系統卻**再也沒有恢復**，成功率維持在 0%，每個使用者請求產生 4 個 attempt。原因是 4 × 80 = 320 個 attempt／秒，遠超過容量 100，queue 永遠排不完，每個 attempt 都等到逾時，然後再產生下一個重試。這就是 metastable failure：觸發是 5 秒的變慢，維持效應是 retry。
2. **指數退避＋jitter**：結果幾乎一樣糟。Backoff 把重試在時間上打散，但每個請求仍然嘗試 4 次，總量仍是 4 倍。這驗證了 39.5 的警告：backoff 和 jitter 改變重試的時機，不改變重試的總量。
3. **退避＋retry budget＋丟過期**：包含觸發的第 20–29 秒這一格，成功率掉到 63%，但放大倍數只有 1.1 倍，第 30 秒之後立刻回到 100%。Budget 讓重試最多增加 10% 的負載，總量不會超過容量；server 端丟棄已經過期的請求，queue 中的白工不消耗 worker，積壓很快清空。最後一格的 99.6% 是模擬在第 90 秒結束，最後幾個請求還沒完成造成的邊界效應。

如果把第三種策略拆開執行（只要修改 `simulate` 裡兩處 `policy` 判斷），可以看到兩個機制各自的角色。只開 retry budget、不丟過期，系統也會恢復，但要到第 40 秒左右才回到正常，因為 queue 中累積的過期請求仍要一個個被處理完；只丟過期、不限制重試，放大倍數仍維持在 4 倍左右，成功率只剩個位數百分比，幾乎和第一種一樣卡住，因為 queue 一直是滿的，worker 處理到的請求都已經等了接近 1 秒，回應回到 client 時大多已經逾時。兩個機制都需要，而 retry budget 是切斷維持效應的關鍵。

在真實系統中，`TIMEOUT_MS` 對應 client library 的 timeout 設定，`tokens` 對應 client 端的 retry budget，`begin - arrived >= TIMEOUT_MS` 的判斷對應 server 從 deadline propagation 讀到的剩餘時間。

### 模擬二：retry 放大與 circuit breaker

第二段程式先算出多層 retry 的放大倍數，再模擬一個呼叫外部金流商的 circuit breaker：金流商在第 10～21 秒全面失敗。

```python
from collections import deque


def amplification(attempts_per_layer, layers):
    return attempts_per_layer ** layers


print("每層最多嘗試次數 × 層數 → 最底層最壞收到的請求數")
for attempts in (2, 3, 4):
    row = "  ".join(f"{layers} 層：{amplification(attempts, layers):>3}" for layers in (1, 2, 3, 4))
    print(f"  每層 {attempts} 次  {row}")
print()


class CircuitBreaker:
    """最近 window 次呼叫中失敗率 ≥ threshold 就跳開；open 一段時間後放少量探測。"""

    def __init__(self, window=20, min_calls=10, threshold=0.5, open_seconds=5, probes=3):
        self.results = deque(maxlen=window)
        self.min_calls, self.threshold = min_calls, threshold
        self.open_seconds, self.probes = open_seconds, probes
        self.state, self.opened_at, self.probe_ok = "closed", 0, 0

    def allow(self, now):
        if self.state == "open" and now - self.opened_at >= self.open_seconds:
            self.state, self.probe_ok = "half-open", 0
        return self.state != "open"

    def record(self, now, ok):
        if self.state == "half-open":
            if not ok:
                self.state, self.opened_at = "open", now      # 探測失敗：再等一輪
            else:
                self.probe_ok += 1
                if self.probe_ok >= self.probes:
                    self.state = "closed"
                    self.results.clear()
            return
        self.results.append(ok)
        failures = self.results.count(False)
        if len(self.results) >= self.min_calls and failures / len(self.results) >= self.threshold:
            self.state, self.opened_at = "open", now


def payments_ok(second):
    return not (10 <= second < 22)          # 外部金流商在第 10～21 秒全面失敗


breaker = CircuitBreaker()
last_state = None
called = fast_failed = 0


def report(second):
    global last_state
    if breaker.state != last_state:
        print(f"第 {second:>2} 秒  breaker → {breaker.state}")
        last_state = breaker.state


for second in range(35):
    for _ in range(4):                       # 每秒 4 筆付款
        allowed = breaker.allow(second)
        report(second)
        if allowed:
            called += 1
            breaker.record(second, payments_ok(second))
            report(second)
        else:
            fast_failed += 1                 # 直接走 fallback：「付款稍後確認」
print(f"實際呼叫金流商 {called} 次，快速失敗（不打下游）{fast_failed} 次")
```

執行結果：

```text
每層最多嘗試次數 × 層數 → 最底層最壞收到的請求數
  每層 2 次  1 層：  2  2 層：  4  3 層：  8  4 層： 16
  每層 3 次  1 層：  3  2 層：  9  3 層： 27  4 層： 81
  每層 4 次  1 層：  4  2 層： 16  3 層： 64  4 層：256

第  0 秒  breaker → closed
第 12 秒  breaker → open
第 17 秒  breaker → half-open
第 17 秒  breaker → open
第 22 秒  breaker → half-open
第 22 秒  breaker → closed
實際呼叫金流商 103 次，快速失敗（不打下游）37 次
```

逐段解讀：

1. **放大表**：每層最多嘗試 4 次、經過 3 層，最底層最壞收到 64 次請求，這就是 39.4 的乘法。即使每層只試 2 次，4 層也會放大 16 倍。這張表是說服團隊「只在一層重試」最直接的證據。
2. **第 12 秒跳開**：金流商從第 10 秒開始失敗，breaker 要等最近 20 次呼叫中失敗達到一半才跳開，所以在第 12 秒才開啟。`min_calls` 與 `threshold` 的取捨是：設得越敏感，越早保護，但也越容易被偶發錯誤誤觸。
3. **第 17 秒的 half-open 探測失敗**：open 5 秒後放出一個探測請求，金流商仍然壞著，breaker 立刻回到 open，再等 5 秒。這一來一回只送出 1 個請求，而不是讓 4 個請求都去撞牆。
4. **第 22 秒恢復**：探測連續成功 3 次，breaker 回到 closed，恢復正常呼叫。
5. **總計**：故障期間 37 個請求快速失敗、走 fallback，沒有佔用 thread 去等一個註定失敗的呼叫。在真實系統中，fallback 對應 39.7 說的「付款處理中、背景確認」，而 breaker 通常由 Resilience4j 這類函式庫提供，不需要自己寫；但理解它的參數，才能把它設對。另外，這個簡化版的 half-open 沒有限制同時放行的探測數，因為每秒的呼叫是依序發生的，第一個探測失敗就會立刻回到 open；真實的實作會明確限制 half-open 時的並行探測數。Service mesh 也有類似的機制，但名稱容易混淆：以 Envoy 為例，它的「circuit breaking」設定其實是連線數與並行請求數的上限，更接近 39.8 的 bulkhead；比較像本節 breaker 的是 outlier detection，它把連續回錯誤的單一 host 暫時移出 load balancing，範圍是一台 host 而不是整個下游服務。

## 39.12 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| 每層都重試 | 下游失敗時負載相乘 | Harbor 三層重試疊成 32 倍，inventory 被重試淹沒 | 只在緊接失敗元件的那一層重試；向上回傳「不要重試」的錯誤 |
| Timeout 設得比正常 p99 還短 | 正常的長尾被當成失敗，製造不必要的重試 | 搜尋的 p99 是 800 ms，timeout 設 500 ms，平常就有 1% 的請求被重試 | 依下游延遲分佈設定，並定期隨下游變化檢視 |
| Timeout 設得過長或沒有 timeout | 下游變慢時資源被長時間佔住 | HTTP client 預設沒有 read timeout，一個卡住的下游讓所有 thread 都在等 | 所有呼叫都要有 timeout，並以剩餘 deadline 為上限 |
| Circuit breaker 範圍太大 | 局部問題被擴大成全面拒絕 | 一家銀行的付款通道壞掉，整個 payments breaker 跳開，所有付款方式都無法使用 | 依 endpoint、供應商或租戶分開設定 breaker |
| Breaker 跳開沒人知道 | 錯誤被 fallback 掩蓋，問題持續數天 | 匯率服務 breaker 一直開著，價格都用 cache 的舊匯率，兩天後才被發現 | Breaker 狀態要有 metric 與告警，fallback 結果要標示 |
| 對非 idempotent 操作重試 | 重複的副作用 | 扣款逾時後重試，使用者被扣兩次 | Idempotency key；沒有 key 的寫入操作不重試（第 41 章） |
| Health check 檢查依賴 | 一個依賴變慢，所有呼叫它的服務都被 load balancer 移除 | inventory 慢，checkout 的 health check 因為查 inventory 失敗，checkout 全部下線 | Health check 只檢查 process 自身，走獨立的資源池 |
| 只靠 backoff 沒有 budget | 持續故障時總量仍然被放大 | 39.11 模擬中，backoff 版本和立刻重試一樣無法恢復 | Backoff＋jitter 搭配 retry budget |
| Bulkhead 切得太細 | 資源利用率低，正常尖峰就被擋 | 每個依賴只分到 5 條 thread，促銷時正常流量也被拒 | 用 Little's Law 估算並保留尖峰餘裕，定期依實際用量調整 |

## 39.13 AI 時代：什麼變了？

**第一，AI agent 本身就是一個會重試的分散式工作流。** Harbor 的 AI 客服處理一件退款客訴，可能要查訂單、查物流、檢查退款政策、送出退款申請（由客服人員核准），每一步都是一次工具呼叫。工具呼叫失敗時，模型會「想辦法」：換個參數再試、改呼叫另一個工具、或乾脆重新開始整個流程。從下游的角度看，這就是沒有上限的 retry，而且比傳統 client 更難預測。更危險的是多個 agent 互相呼叫的架構：一個 agent 的重試會觸發另一個 agent 的多個步驟，形成和 39.4 一樣的乘法放大。

實務上，agent 的執行環境（harness）必須提供本章所有的機制，而且是在模型之外強制執行：

- **整體 deadline 與步驟上限**：一個任務最多跑多久、最多呼叫幾次工具、最多花多少 token，時間或額度用完就停止並交給人。
- **每個工具的 retry 政策**：由 harness 依錯誤類型決定是否重試，而不是讓模型自己決定。權限錯誤、政策阻擋這類錯誤絕對不重試，也不能讓模型「改寫指令繞過去」。
- 帶上 idempotency key（第 41 章）：所有會產生副作用的工具（送出退款申請、寄信、改訂單）都要帶 idempotency key。模型在逾時後「再送一次退款申請」時，下游必須能辨識這是同一個操作。
- **Circuit breaker**：某個工具持續失敗時，harness 要讓 agent 知道「這個工具目前不可用」，引導它走替代流程或轉人工，而不是讓每個對話都去撞同一面牆。

**第二，AI 能協助找出 cascade 的風險，這類分析很適合交給 coding agent。** 例如讓 agent 掃描所有 repo 的 client 設定，畫出每條呼叫鏈的 timeout 與 retry，計算最壞的放大倍數，標出 timeout 比上游 deadline 還長的地方。這種跨 repo、跨語言的盤點正是人很難做完整、AI 很擅長的工作，但結論必須用實際設定與演練驗證。

**第三，事故中 AI 可以幫忙建立時間線，但止血決策要由人做。** AI 維運 agent 可以快速關聯 retry 比例、breaker 狀態、部署紀錄與依賴延遲，指出「inventory 延遲上升 30 秒後，checkout 的 retry 比例從 1% 升到 300%」這類線索。但「關掉 app 的自動重試」「在 edge 擋掉非結帳流量」這些決策影響大量使用者，必須由 incident commander 判斷（第 44 章）。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 跨 repo 盤點 timeout、retry、breaker 設定，計算每條呼叫鏈的最壞放大倍數 | 盤點結果要用實際部署的設定與演練驗證，不能只信靜態分析 |
| 依延遲分佈建議 timeout 值，產生設定變更的 PR | Timeout 與 retry 政策的變更要經過服務 owner 與 SRE review，並先在 canary 驗證 |
| 產生延遲注入、依賴失效的 chaos 實驗腳本與預期結果 | 實驗的範圍、時段與中止條件由人核准，production 實驗要有明確的 blast radius 限制 |
| 事故中關聯 retry 比例、breaker 狀態、部署與依賴延遲，草擬時間線 | 限流、關閉重試、降級等止血決策由 incident commander 決定 |
| 在 agent harness 中依錯誤類型分類工具錯誤（暫時、永久、政策） | Agent 的 deadline、步驟上限、retry 政策與花費上限由 harness 強制，agent 無法自行調整 |

> [!ai] AI 提醒
> 一個沒有整體預算的「聰明」agent loop，本質上就是一個更難觀察的 retry storm。它不會像 HTTP client 一樣在 log 中留下整齊的「retry attempt 3」，而是表現為「模型決定再查一次」「模型換了一個工具」。觀測 agent 時，要計算的不只是請求數，還有每個任務的工具呼叫次數、重複呼叫同一工具的次數，以及每個任務的總花費，並對這些數字設定告警。

## 39.14 專家怎麼想

- **先畫放大圖。** 看到一個新服務的設計，資深 SRE 第一件事是畫出呼叫鏈，標上每一層的 timeout、retry 次數與 deadline，算出「一個使用者請求在最壞情況下會在最底層產生多少呼叫」。這個數字超過個位數，就值得停下來討論。
- **Retry 是用負載換成功率，只在有餘裕時划算。** Retry 在下游有容量時是好交易，在下游過載時是壞交易。專家會問：這個 retry 在下游壞掉的時候會發生什麼事？如果答案是「放大負載」，就需要 budget。
- **最怕的不是失敗，是變慢。** 立刻失敗的依賴很好處理，慢吞吞的依賴才會佔住資源、觸發 timeout 與 retry。演練與監控都要特別針對延遲上升，而不只是錯誤率。
- **問「觸發消失後能不能自己恢復」。** 很多系統在負載測試中撐得住尖峰，卻在短暫故障後回不來。資深工程師會要求演練不只看故障期間，也看故障結束後的恢復時間。
- **把防護放在共用的 library 和平台。** 讓每個團隊自己設定 timeout 和 retry，一定會有人設錯。最有效的投資是一個預設值正確的共用 client library 或 service mesh，讓「做對」是預設，「做錯」需要額外理由。
- **Fallback 不能說謊。** Breaker 跳開時的 fallback 要誠實：可以說「付款處理中」，不能說「付款成功」。專家會檢查每個 fallback 是否破壞了業務不變量。

## 39.15 動手練習

1. 修改 39.11 的模擬一，把 retry budget 從 10% 改成 30%、50%，找出系統開始無法恢復的門檻。再把使用者流量從 80 改成 60 與 90，觀察「脆弱狀態」的餘裕如何影響恢復能力。
2. 在模擬一中加入 circuit breaker：當最近 50 次 attempt 中逾時超過一半，就停止送新請求 2 秒。比較它和 retry budget 的效果，以及兩者並用的結果。
3. 為你熟悉的一條呼叫鏈（或 Harbor 的 web → checkout → inventory → 資料庫）畫出每一層的 timeout、retry 次數與 deadline，計算最壞的放大倍數，並提出只在一層重試的修改方案。
4. 寫一個 deadline propagation 的小程式：三個函式模擬三層服務，每層接收「剩餘毫秒數」、扣掉自己的處理時間後傳給下一層，剩餘時間不足時直接回傳錯誤。測試使用者 deadline 是 500 ms 與 100 ms 時的行為。
5. 為 Harbor AI 客服的五個工具（查訂單、查物流、查政策、送出退款申請、寄信）設計工具呼叫政策：哪些錯誤可以重試、最多幾次、是否需要 idempotency key、breaker 開啟時 agent 該怎麼做。
6. 設計一個 game day 劇本：讓 inventory 延遲增加 2 秒、持續 60 秒。寫下預期的觀測結果、中止條件，以及「系統在故障結束後 2 分鐘內恢復」的驗證方式。

## 本章重點整理

- Cascading failure 是透過正回饋迴路擴大的故障；最常見的兩個迴路是「變慢 → 逾時 → 重試 → 更慢」與「過載 → health check 失敗 → instance 被移除 → 更過載」。
- 不同資源的耗盡會互相轉換（延遲 → thread → 記憶體 → CPU），只看單一資源的儀表板看不出全貌。
- 觸發條件（failover、部署、流量成長）通常無法完全避免，能控制的是系統對觸發的反應。
- 每個呼叫都要有 timeout，依下游延遲分佈設定，並以呼叫端剩餘的 deadline 為上限。
- Deadline propagation 讓每一層知道請求還剩多少時間，應傳遞剩餘時間長度而非絕對時間點；cancellation 也要往下傳。
- Retry 只對暫時、隨機的失敗且下游有餘裕時有幫助；對過載的下游重試等於火上加油。
- 多層 retry 的放大是相乘的：每層 4 次嘗試、3 層就是 64 倍；應只在緊接失敗元件的一層重試。
- 非 idempotent 的操作只有在有 idempotency key 時才能重試，因為逾時不代表下游沒有執行。
- Exponential backoff＋jitter 打散重試的時間、避免驚群，但不減少重試的總量。
- Retry budget（例如重試佔請求比例 ≤ 10%）限制重試總量，能自動區分偶發錯誤與大規模故障。
- Circuit breaker 在持續失敗時讓呼叫立刻失敗，透過 half-open 探測自動恢復；範圍要和故障範圍對齊，狀態要可觀測，fallback 不能破壞不變量。
- Bulkhead 把資源分成隔離的池子，防止一個依賴的問題經由共用資源擴散；health check 應有獨立路徑且不檢查依賴。
- Metastable failure 是觸發消失後仍因維持效應（retry、冷 cache、GC）停留在故障狀態；脫離需要把負載壓到遠低於正常，預防需要削弱維持效應並保留餘裕。
- 測試 cascading failure 要注入延遲而不只是錯誤，要測到故障之後，並驗證觸發消失後系統能自行恢復。
- AI agent 是會自行重試的工作流，harness 必須在模型之外強制 deadline、步驟上限、retry 政策、idempotency 與 circuit breaker。

## 延伸問答

> [!question]- Q1. Timeout 和 deadline 有什麼不同？為什麼有了 timeout 還需要 deadline propagation？
> Timeout 是單一步驟最多等多久，由呼叫端自己決定；deadline 是整個使用者操作最晚完成的時間點，屬於整條請求鏈。只有 timeout 時，每一層各自計時，下游不知道上游已經等了多久，也不知道使用者是否早就放棄了。
>
> 例如使用者願意等 2 秒，web 呼叫 checkout 的 timeout 是 10 秒，checkout 呼叫 inventory 的 timeout 是 3 秒。使用者在 2 秒時放棄後，checkout 和 inventory 仍會繼續工作好幾秒，全部是白工。Deadline propagation 讓每一層都知道「還剩多少時間」：下游可以在剩餘時間不夠時直接放棄、不做任何昂貴操作，也可以用剩餘時間作為自己呼叫下游的 timeout 上限。兩者是互補的：deadline 決定總預算，timeout 在每一步執行這個預算。

> [!question]- Q2. 計算題：一個請求經過 app → web → checkout → payments，app 呼叫 web 最多嘗試 2 次，web 呼叫 checkout 最多 3 次，checkout 呼叫 payments 最多 3 次。payments 完全失敗時，一個使用者點擊最壞會在 payments 產生幾次呼叫？你會怎麼改？
> 放大是相乘的。題目的呼叫鏈中，app 呼叫 web 最多 2 次，每次 web 呼叫 checkout 最多 3 次，每次 checkout 呼叫 payments 最多 3 次，所以 payments 最壞收到 2 × 3 × 3 = 18 次呼叫。如果中間再多一層同樣會重試 3 次的服務，就會變成 54 次。
>
> 修改方向是只在一層重試：讓 checkout 對 payments 的呼叫保留有限的重試（例如最多 3 次嘗試、full jitter、受 retry budget 限制），並在重試仍失敗時回傳明確的「下游失敗，不要重試」錯誤；web 與 app 收到這個錯誤時直接顯示給使用者，不再重試。另外，扣款是非 idempotent 操作，checkout 的重試必須帶 idempotency key，否則逾時後的重試可能造成重複扣款。

> [!question]- Q3. 為什麼說 exponential backoff＋jitter 不足以防止 retry storm？
> Backoff 和 jitter 處理的是重試的「時機」：backoff 讓重試間隔越來越長，jitter 讓不同 client 的重試錯開，避免所有 client 同時重試造成週期性尖峰。這兩者都非常重要，但它們都沒有改變一件事：每個失敗的請求最終仍然會嘗試設定的次數。
>
> 在持續性的故障下，如果每個請求最多試 4 次，下游收到的總量仍然是原本的 4 倍，只是分佈得比較平均。如果這個 4 倍超過下游的容量，系統就會像 39.11 的模擬一樣卡在故障狀態。要限制總量，需要 retry budget（例如重試比例不超過 10%）或 circuit breaker，讓大規模故障時多數的重試直接被放棄。

> [!question]- Q4. 你是 Harbor 的值班者，資料庫 failover 已經完成，單次查詢延遲恢復正常，但 checkout 的成功率仍然是 0%，retry 比例是 300%。你會怎麼做？
> 這是 metastable failure 的典型徵兆：觸發已經消失，但重試讓負載維持在容量以上。重啟服務或等待通常沒有用，因為新 instance 一上線就會面對同樣的負載。目標是把負載壓到維持效應無法運轉的程度。
>
> 具體做法依序是：關閉或大幅降低重試來源（例如透過 flag 關掉 app 的自動重試、調低 client library 的 retry 設定）；在 edge 大幅限流，只放行結帳等關鍵流量，甚至暫時只放行一部分使用者；暫停批次與背景工作；如果 health check 正在讓 instance 被移除，暫時放寬它。等 queue 清空、成功率回升後，再逐步放回流量並觀察是否再度惡化。事後的 postmortem 要處理的不是資料庫 failover 本身，而是為什麼二十幾秒的觸發會變成將近 40 分鐘的事故：retry 設定、缺少 retry budget、health check 設計。

> [!question]- Q5. Circuit breaker 和 retry budget 都是在限制送往下游的請求，兩者有什麼不同？只用其中一個可以嗎？
> Retry budget 限制的是「額外」的請求：它不影響每個請求的第一次嘗試，只限制重試佔總量的比例。所以在下游完全壞掉時，每個請求仍然會送出第一次，等到 timeout 才失敗，呼叫端的 thread 仍然被佔住。Circuit breaker 則在偵測到持續失敗後連第一次都不送，讓請求立刻失敗或走 fallback，釋放呼叫端的資源，並透過 half-open 探測自動恢復。
>
> 只用 retry budget，下游全壞時呼叫端會被 timeout 拖慢；只用 breaker，在部分失敗（例如 30% 錯誤率，未達跳開門檻）時，每個失敗的請求仍會重試多次，放大負載。兩者處理不同的失敗型態，所以通常一起使用，再加上下游自己的 load shedding 作為最後一道防線。

> [!question]- Q6. 反例題：有人提議「為了讓 load balancer 更快移除壞掉的 instance，checkout 的 health check 應該檢查 inventory、payments、資料庫是否都正常」。這有什麼問題？
> 這會把依賴的問題變成整個 checkout 服務的下線。如果 inventory 變慢，所有 checkout instance 的 health check 都會同時失敗，load balancer 會把它們全部移除，即使 checkout 本身完全正常、很多請求（例如查詢訂單）根本不需要 inventory。一個依賴的局部問題，被 health check 放大成了 checkout 的全面故障，這正是 cascading failure。
>
> Health check 應該只回答「這個 process 能不能處理請求」，例如能否回應、是否已完成初始化，並且走獨立的資源路徑，不受一般請求的 thread pool 影響。依賴的健康狀況應該由 circuit breaker、降級邏輯與監控處理：依賴壞掉時，checkout 繼續運作並走 fallback，同時發出告警，而不是把自己下線。

> [!question]- Q7. 面試題：請設計一個呼叫外部金流商的 client，要考慮哪些可靠性機制？
> 首先是 timeout：connect timeout 短（例如數百毫秒），request timeout 依金流商的延遲分佈與上游剩餘 deadline 設定，取兩者中較小的值。其次是 idempotency：每筆付款產生唯一的 idempotency key 並傳給金流商，讓逾時後的重試不會重複扣款；若金流商不支援，就不能自動重試，只能改為查詢交易狀態。
>
> 重試方面，只對明確的暫時性錯誤重試，最多 2 到 3 次嘗試，使用 exponential backoff＋full jitter，尊重 `Retry-After`，並受 retry budget 限制。Circuit breaker 依金流商或付款通道分開，失敗與過慢都計入，開啟時 fallback 為「付款處理中」並在背景確認，絕不假裝成功。最後是 bulkhead：金流商呼叫用獨立的連線池，避免它變慢時拖垮 checkout 的其他功能；並且監控 retry 比例、breaker 狀態與每筆交易的嘗試次數。回答時能說明「為什麼逾時不代表失敗」，通常是面試官最在意的部分。

> [!question]- Q8. AI 情境：Harbor 的 AI 客服在呼叫「送出退款申請」工具時遇到逾時，模型決定再呼叫一次。harness 應該怎麼設計才能安全？
> 第一，「送出退款申請」是有副作用的非 idempotent 操作，harness 必須在第一次呼叫時就自動產生 idempotency key，並在模型再次呼叫時沿用同一個 key（例如依對話 ID 與退款的訂單 ID 產生）。這樣即使第一次其實已經成功，下游也會辨識出重複請求並回傳原本的結果，而不是建立兩筆退款申請（客服人員若兩筆都核准，就是退兩次款）。更好的做法是 harness 在重試前先查詢該訂單的退款申請狀態。
>
> 第二，重試的決定不應該交給模型。harness 依錯誤類型決定：逾時可以在 budget 內重試一次，權限或政策錯誤絕不重試；整個任務有 deadline 與工具呼叫上限，用完就轉人工。第三，如果退款服務持續失敗，harness 的 circuit breaker 應該讓 agent 收到「退款工具暫時不可用」的結構化訊息，引導它告訴使用者「已轉交專人處理退款」，而不是讓模型反覆嘗試。最後，所有的重試與工具呼叫都要被記錄與監控，讓「agent 重複呼叫同一個工具」的比例成為可告警的指標。

## 延伸閱讀

- [Site Reliability Engineering — Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/)：本章的主要來源，涵蓋成因、觸發條件、retry、deadline、slow startup、測試與即時應對手段。
- [Site Reliability Engineering — Handling Overload](https://sre.google/sre-book/handling-overload/)：per-request 與 per-client retry budget、只在一層重試，以及「overloaded; don't retry」錯誤的設計。
- [Site Reliability Engineering — Testing for Reliability](https://sre.google/sre-book/testing-reliability/)：如何設計測試與演練，延伸本章 39.10 的內容。
