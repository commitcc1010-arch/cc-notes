---
chapter: 38
title: Queue、Backpressure、Overload 與 Load Shedding
part: 6
---

# 第 38 章　Queue、Backpressure、Overload 與 Load Shedding

> [!abstract] 本章地圖
> **核心問題**：當湧進來的工作超過系統能處理的量，要怎麼讓「一部分人得到好服務」，而不是「所有人都得到爛服務」？
>
> **你會學到**：
> - 分辨 offered load、throughput 與 goodput，看懂過載時 goodput 為什麼會崩塌
> - 判斷 queue 什麼時候在幫忙、什麼時候在傷害，並依 deadline 決定 queue 的上限
> - 設計端到端的 backpressure，讓壓力回到能夠減速的地方
> - 用 admission control、rate limit、concurrency limit 在昂貴工作開始前做決定
> - 依 criticality 做 load shedding，並用 adaptive throttling 讓 client 自己減量
> - 設計可測試、可觀測的 graceful degradation
>
> **前置知識**：第 33 章（four golden signals 中的 saturation）、第 36 章（Little's Law 與 utilization 對延遲的非線性影響）、第 37 章（load balancing 與 health check）
>
> **對應原書**：SRE 第 21 章〈Handling Overload〉、第 22 章〈Addressing Cascading Failures〉（queue 管理與 load shedding 的部分）

## 38.1 故事：開賣第一分鐘，CPU 滿載，訂單是零

雙十一前兩週，Harbor 和一個人氣品牌合作「預購搶先賣」：晚上八點整開放 3,000 組限量禮盒。Harbor 這時已經是約 120 人的公司，志明帶領的 SRE 團隊也擴充到約 6 人，第 36 章的雙十一容量計畫也已經完成；不過依計畫，「預先擴容到活動規模」要到雙十一前三天才進行，所以這場預購是用現有的機器撐：商品頁與 inventory 服務按「平常尖峰的三倍」準備。

七點五十九分，等待開賣的使用者已經在商品頁瘋狂按重新整理。八點整，流量衝到平常尖峰的五倍。最先出問題的是 inventory 服務：它每個 instance 有 64 個 worker thread，後面接一個沒有上限的請求 queue。湧進來的請求在 queue 裡越排越長，開賣才十幾秒，每個請求就要排八秒才輪得到；而 app 端的 timeout 是三秒，使用者看到「連線逾時」就再按一次。

值班的 SRE 志明看到的儀表板很矛盾：inventory 的 CPU 是 100%，每秒「處理完成」的請求數穩穩停在準備好的容量上限附近，但成功下單數幾乎是零。原因是 inventory 正在認真處理的，全是八秒前送來、使用者早就放棄的請求。機器很忙，但做的全是白工。更糟的是，queue 裡的請求越積越多，記憶體一路上升，八點四分開始有 instance 因為 out of memory 被重啟，剩下的 instance 分到更多流量，情況更快惡化。

最後志明在 load balancer 上把商品頁流量砍掉一半，inventory 才在幾分鐘內恢復。事後回顧時，checkout 的 tech lead 美華（inventory 也歸 checkout 團隊）算了一筆帳：inventory 在那段時間的真實容量大約是每秒 6,000 個請求（平常尖峰約每秒 2,000 個的三倍），送進來的是每秒 10,000 個（五倍）。每秒多出 4,000 個請求，十二秒就積了 48,000 個；以每秒 6,000 個的速度消化，新來的請求要等 48,000 / 6,000 = 8 秒，遠超過 app 的 3 秒 timeout。如果一開始就快速拒絕多出來的 4,000 個，每秒至少有 6,000 個請求能在一秒內得到回應；因為選擇「全部收下、慢慢排」，結果是每秒一萬個請求幾乎全部失敗。

這一章要回答的就是這個反直覺的結論：**系統做不完的時候，及早、便宜、有選擇地拒絕，比全部收下更可靠**。我們會從「過載」的定義開始，依序看 queue、backpressure、admission control、load shedding、client 端節流與 graceful degradation，最後把它們組成 Harbor 的分層防護。

## 38.2 過載是什麼：offered load、throughput 與 goodput

### 三個要分開的數字

**Offered load**（送入負載）是所有想要被處理的工作量，例如每秒 10,000 個請求。**Throughput**（吞吐量）是系統每秒實際處理完的工作量。**Goodput**（有效吞吐量）是其中「對使用者有用」的部分：在 deadline 內完成、結果正確、使用者還在等的請求。

正常時三者幾乎相等。過載時它們會分開，而且分開的方式很危險：offered load 繼續上升，throughput 維持在容量附近，goodput 卻往下掉，嚴重時掉到接近零。Harbor 開賣那一分鐘就是這樣：throughput 看起來正常，goodput 是零。

```text
 goodput（每秒在 deadline 內完成數）
   ▲
容量┤               ●━━━━━━━━━━━━━━━━━━━━━━━━  ① 理想：到容量後維持平頂
   │              ╱●─────────────────────────  ② 有 load shedding：略低但穩定
   │             ╱   ╲
   │            ╱      ╲
   │           ╱         ╲
   │          ╱             ╲_____________  ③ 沒有保護：goodput 崩塌
   │         ╱
   │        ╱
   └───────────────┼─────────────────────────▶ offered load
                 容量
```

這張圖的橫軸是送入的負載，縱軸是 goodput。在容量之前，三條線重疊：送多少、做多少。超過容量後，① 是理論上限：系統以最高速度工作，多出來的請求不被服務。② 是加了 load shedding 的真實系統：拒絕本身也要花一點資源，所以略低於平頂，但會穩定維持。③ 是沒有保護的系統：每多送一點，goodput 就少一點，這個現象在網路領域叫 **congestion collapse**（擁塞崩潰）。過載防護的目標就是把系統從 ③ 拉到 ②。

### 為什麼 goodput 會崩塌

崩塌通常有四個來源，它們往往同時出現：

1. **白工**：請求在 queue 裡等到超過 client 的 timeout，client 已經放棄，server 卻仍然把它做完。等待越久，白工的比例越高。
2. **重試**：使用者與 client library 看到 timeout 就重試，offered load 因此再乘上一個倍數（第 39 章會專門討論）。
3. **資源額外消耗**：queue 變長佔用記憶體，觸發更頻繁的 garbage collection；context switch、lock 競爭變多；每個請求的實際成本上升，等於容量下降。
4. **元件死亡**：記憶體耗盡、health check 逾時，instance 被重啟或被 load balancer 移除，剩下的 instance 分到更多負載。

第 1 與第 3 點會讓「每單位工作的成本」上升，第 2 與第 4 點會讓「負載」上升，兩者互相加強。這就是為什麼過載很少停在「慢一點」，而是一路惡化到全面失敗。

### 容量要用資源，不要用 QPS 衡量

很多團隊把容量寫成「每台每秒 800 個請求」。SRE 書特別指出這個做法的陷阱：不同請求的成本差很多，查一個商品 ID 和搜尋「紅色 洋裝 免運」可能差上百倍；請求組成一變，同樣的 QPS 就代表完全不同的負載。比較穩定的做法是用資源衡量容量，例如「CPU 使用時間」或「在途請求數」，並在 load test 時用接近真實比例的請求組合。

### 過載的徵兆

過載時最先變化的通常不是錯誤率，而是 saturation 類的訊號。值班時要特別注意：

| 訊號 | 正常時 | 過載前兆 | 為什麼重要 |
|---|---|---|---|
| Queue 長度與最老項目的等待時間（queue age） | 接近 0 | 持續上升 | 直接告訴你請求要等多久，最接近使用者體驗 |
| p99 latency | 穩定 | 上升速度比流量快 | 第 36 章提過：utilization 接近 100% 時延遲非線性暴增 |
| 在途請求數（in-flight） | 穩定 | 持續上升 | 依 Little's Law（L = λW），吞吐量停在容量上限時，延遲上升就代表在途數上升 |
| Thread／connection pool 使用率 | 有餘裕 | 持續滿載 | 滿了之後新請求只能排隊或失敗 |
| GC 時間、記憶體 | 平穩 | 鋸齒變密、基準線升高 | Queue 與在途請求佔用記憶體 |
| Timeout 與 client 重試數 | 很少 | 快速上升 | 代表白工與負載放大已經開始 |

> [!warning] 常見誤解
> 「CPU 還沒到 100%，所以沒有過載。」過載的瓶頸可能是 thread pool、資料庫連線、下游配額或 lock，CPU 只是其中一種資源。Harbor 另一次事故中，checkout 的 CPU 只有 35%，但 50 條資料庫連線全被慢查詢佔住，新請求全部在等連線。看 saturation 要看「每一種會被耗盡的資源」。

## 38.3 Queue：吸收 burst，而不是創造容量

### Queue 為什麼存在

**Queue**（佇列）是讓工作排隊等待處理的地方。它存在的理由是流量本來就不平均：即使每秒平均 80 個請求，某一百毫秒可能來了 20 個，下一個一百毫秒只有 3 個。沒有 queue，同一瞬間湧進來的請求只能被拒絕；有了 queue，短暫的 **burst**（突發流量）可以先排著，等 worker 有空再處理。Queue 把「到達時間」和「處理時間」解耦，這對短期波動非常有用。

但 queue 只能搬移時間，不能創造容量。只要 **arrival rate**（到達速率，λ）長期大於 **service rate**（服務速率，μ），queue 就一定會一直變長：

```text
queue 每秒增加 = λ − μ
等了 t 秒後的 queue 長度 ≈ (λ − μ) × t
新到請求要等的時間 ≈ queue 長度 / μ

例：λ = 1,500/s，μ = 1,000/s
  10 秒後 queue ≈ 5,000 個 → 新請求要等約 5 秒
  60 秒後 queue ≈ 30,000 個 → 新請求要等約 30 秒
```

如果使用者只願意等 2 秒，第 4 秒之後到達的每一個請求都注定失敗，而且 server 還會繼續花資源處理它們。這就是 Harbor 開賣時 inventory 的狀態：queue 沒有吸收任何東西，只是把失敗延後，並把它變得更貴。

### Queue 的上限要從 deadline 推出來

既然 queue 會讓請求等待，它的上限就應該由「請求最多能等多久」決定，而不是由「記憶體夠放多少」決定。粗略的算法是：

```text
最大等待時間 ≈ queue 上限 × 每個請求的服務時間 / worker 數

若 deadline = 1 秒、服務時間 = 10 ms、1 個 worker：
  queue 上限 100 → 最壞要等 1 秒，剛好等於 deadline，排到的人幾乎都會逾時
  queue 上限 50  → 最壞約等 0.5 秒，留下另一半時間給處理與網路
```

本章 38.10 的模擬會直接看到這個差別：queue 上限 100 時仍有上千個請求「做完但逾時」，上限 50 時一個都沒有。SRE 書的經驗法則也類似：流量平穩的服務，queue 長度相對於 thread pool 大小應該很小（例如一半以下），讓 server 在跟不上時及早拒絕；流量本質上很 bursty 的服務，才需要依 burst 的大小與頻率設定較大的 queue。書中也提到 Gmail 常用不排隊（queueless）的 server，thread 滿了就讓請求 failover 到其他 task。

### 看 queue age，而不只是 queue 長度

**Queue depth**（隊伍長度）有個缺點：同樣 100 個請求，若都是便宜的查詢可能 0.1 秒就消化完，若都是昂貴的搜尋可能要 5 秒。**Queue age**（最老項目已等待的時間）直接回答「現在排進來要等多久」，和 deadline 可以直接比較，所以更適合拿來做告警與 shedding 判斷。

### 排隊順序也是一個決策

預設的 **FIFO**（先進先出）在正常時最公平。但過載時，FIFO 會讓 server 優先處理「等最久的」請求，而這些正是最可能已經被放棄的。有幾種替代做法：

- **Deadline-aware dequeue**：從 queue 取出請求時，先檢查它的 deadline 是否已經過了，或剩下的時間不夠完成。不夠就直接丟棄，不花任何處理成本。
- **LIFO**（後進先出）：塞車時先服務最新的請求，它們的使用者還在等。代價是舊請求可能永遠排不到，所以通常只在 queue 超過某個長度時才切換，叫 **adaptive LIFO**。
- **CoDel**（Controlled Delay）：原本是網路設備的佇列管理演算法，概念是觀察「最短等待時間」，如果一段時間內 queue 從來沒有清空過（代表形成了 **standing queue**，常駐隊伍），就縮短允許的等待時間，主動丟棄。Facebook 的 Ben Maurer 在 2015 年發表於 ACM Queue 的〈Fail at Scale〉中，分享過在服務端結合 CoDel 與 adaptive LIFO 的做法；SRE 書第 22 章也把 LIFO 與 CoDel 列為丟棄「不值得處理的請求」的方法。

這些做法的共同點是：**不要讓過載時的 queue 變成一個「保證每個人都等很久」的機器**。

### 隱藏的 queue

系統裡的 queue 遠比你畫在架構圖上的多。一個請求從使用者到資料庫，可能經過：作業系統的 TCP accept backlog、load balancer 的連線 queue、web server 的 request queue、應用程式的 thread pool queue、資料庫連線池的等待隊列、資料庫自己的 lock 等待。每一層都可能有一個不顯眼、預設很大的 queue。過載時延遲會在其中一層悄悄累積，而那一層往往沒有任何監控。設計過載防護的第一步，是把這些 queue 列出來，確認每一個都有上限，並且知道它滿了會發生什麼。

### 非同步 queue 是另一回事

Message queue（例如 Kafka、SQS、RabbitMQ）用來處理「使用者不需要立刻等結果」的工作，例如寄出貨通知、更新推薦模型。這種 queue 本來就預期會累積 backlog，長度大不一定是問題，只要 **consumer lag**（消費落後）在可接受範圍、最終能追上即可。判斷的方法是問：這些工作有沒有 deadline？「出貨通知晚 10 分鐘」可以接受，「晚 2 天」就不行。非同步 queue 一樣需要上限、lag 告警，以及對處理失敗訊息的 **dead letter queue**（死信佇列，存放重試多次仍失敗的訊息，讓人工檢查）。

> [!warning] 常見誤解
> 「Queue 越大，丟掉的請求越少，所以越可靠。」對同步請求來說剛好相反：queue 越大，過載時每個人等得越久，白工越多，最後連本來能成功的請求都逾時。Queue 大小是延遲的上限，不是可靠性的保險。

## 38.4 Backpressure：讓壓力回到能減速的地方

### 為什麼需要 backpressure

假設 Harbor 的訂單處理流程是「checkout 寫入訂單 → 訂單事件進入 queue → fulfillment 服務消化」。如果 fulfillment 變慢，而中間的 queue 沒有上限，checkout 會繼續快樂地寫入，直到 queue 塞爆儲存空間；等到發現時，可能已經累積了好幾個小時的 backlog。問題不在於 fulfillment 慢，而在於「它慢了」這個資訊沒有傳回上游。

**Backpressure**（背壓）就是下游把「我處理不了更多」的訊號傳回上游，讓上游減速、停下或改道的機制。名字來自水管：下游的閥門關小，壓力會沿著管線往回推。

### 傳遞壓力的四種方式

```text
 producer ──▶ [bounded buffer] ──▶ consumer
    ▲                │
    │   ①阻塞：buffer 滿了，producer 的 put() 卡住
    │   ②額度：consumer 告訴 producer「我還能收 n 個」
    │   ③拒絕：回 429／503 + Retry-After，由 producer 決定怎麼辦
    └── ④拉取：consumer 有空才去拿，producer 只負責放在原地
```

1. **阻塞**（blocking）：最簡單的形式。程式裡有上限的 channel 或 queue，滿了之後寫入方會被暫停。適合同一個 process 內的 pipeline。
2. **Credit-based flow control**（額度制流量控制）：接收方明確告訴傳送方還能收多少。TCP 的 receive window、HTTP/2 與 gRPC 的 stream flow control、Reactive Streams 的 `request(n)` 都是這個模式。
3. **明確拒絕**：跨服務的同步呼叫最常見的形式。HTTP 用 **429 Too Many Requests**（通常表示 client 超過配額）或 **503 Service Unavailable**（server 暫時無法服務），可以附上 `Retry-After` header 告訴 client 多久後再試；gRPC 有對應的 `RESOURCE_EXHAUSTED` 與 `UNAVAILABLE` 狀態碼。
4. **Pull-based**（拉取式）：consumer 主動拉工作，自然不會拿超過自己能處理的量。Kafka consumer 就是這種模式，壓力會表現為 lag，而不是把 consumer 壓垮。

### 壓力最後要停在哪裡

Backpressure 必須是**端到端**的。如果中間有任何一層「先收下再說」，壓力就會被那一層吞掉，上游完全感覺不到。常見的錯誤是在兩個服務之間加一個沒有上限的 buffer 或 queue，表面上「解耦」了，實際上只是把爆炸地點從 fulfillment 搬到 queue 本身。

壓力最終要停在一個能夠合理處理它的地方：

- 對**使用者**：顯示「目前人數眾多，請稍後再試」或排隊頁，比讓使用者等 30 秒後失敗好得多。Harbor 之後的搶購都改用虛擬排隊頁。
- 對**批次或非同步 producer**：減速、暫停，或把資料暫存在有上限、有告警的地方。
- 對**內部 client 服務**：收到拒絕後走 fallback 或把錯誤往上傳，而不是重試到天荒地老（第 39 章）。

> [!tip] 實務做法
> 盤點一條關鍵路徑時，對每一個邊界問三個問題：下游忙的時候，上游怎麼知道？上游知道後會做什麼？如果上游什麼都不做，壓力會累積在哪裡？答不出來的地方，就是下一次事故的位置。

## 38.5 Admission control：在門口就決定

### 越早拒絕越便宜

一個請求被拒絕的成本，取決於它被拒絕之前做了多少事。在 edge 被 rate limit 擋下，只花了解析 header 的成本；在 inventory 服務查完三次資料庫後才因為逾時失敗，已經花掉了完整的處理成本，還佔住了資料庫連線。**Admission control**（准入控制）就是在昂貴的工作開始之前，判斷「這個請求我做得完嗎？值得做嗎？」，做不完就立刻拒絕。

### 常見的准入機制

**Rate limiting**（速率限制）限制單位時間內的請求數。最常見的實作是 **token bucket**（權杖桶）：桶子以固定速率 r 補充 token，最多存 b 個；每個請求要拿走一個 token 才能進來，拿不到就拒絕。

```text
token bucket：r = 100 token/秒，b = 200
  平常流量 80/s → 桶子常常是滿的，偶爾的 burst 可以一次用掉最多 200 個
  持續流量 150/s → 先用完存量，之後每秒只放行 100 個，其餘拒絕
  長期平均放行率 ≤ r；短期 burst ≤ b
```

Token bucket 同時處理了「長期平均」與「短期突發」，所以被廣泛用在 API gateway、雲端服務的 API 配額，以及 Linux 的流量控制。

**Concurrency limit**（並行數上限）限制同時在處理中的請求數，而不是每秒的數量。它的好處是自動適應請求成本：如果每個請求突然變慢，同樣的並行上限會讓每秒放行的數量自然下降。依 Little's Law（第 36 章），並行數 = 吞吐量 × 延遲，所以若一個 instance 在 p99 達標時最多能維持每秒 400 個請求、每個平均 50 ms，合理的並行上限大約是 400 × 0.05 = 20，再加上一些餘裕。

**Adaptive concurrency limit**（自適應並行上限）更進一步：持續觀察延遲，延遲開始上升時就調低上限，延遲回穩時慢慢調高。這個想法借自 TCP 的擁塞控制（例如「加法增、乘法減」的 AIMD），好處是不需要事先精準知道容量，也能隨著部署、硬體或請求組合改變而調整；代價是參數更難理解，調不好會震盪。

**Per-customer quota**（每個客戶的配額）防止單一 client 吃掉所有容量。SRE 書描述的做法是：依容量規劃，給每個客戶一個資源配額；一個客戶超量時，只拒絕這個客戶的超額請求，其他人不受影響。Harbor 的開放 API 給大賣家串接上架系統，每個賣家都有獨立配額，否則一個寫錯迴圈的賣家程式就能拖垮全站的上架功能。

### 在哪一層做

| 位置 | 擅長 | 不擅長 |
|---|---|---|
| CDN／edge | 擋掉惡意流量、爬蟲、超大量 burst，成本最低 | 不知道後端的即時狀態與請求的業務價值 |
| Load balancer／API gateway | 每個 client 或租戶的配額、全域 rate limit | 不知道單一 instance 的資源狀況 |
| 服務 instance 自己 | 依自身 CPU、記憶體、queue age 即時判斷 | 拒絕已經需要花一點成本 |
| 下游依賴之前 | 依依賴的健康狀況限制呼叫量 | 只能保護那一個依賴 |

實務上這些位置要一起用：edge 擋明顯不該進來的，gateway 做公平分配，instance 做最後的自我保護。**每個服務都必須能保護自己**，不能假設上游一定會幫它擋住，因為上游的設定可能錯、可能被繞過，也可能有新的 client 直接連進來。

> [!warning] 常見誤解
> 「有 autoscaling 就不需要 admission control。」Autoscaling 需要時間：偵測到負載、啟動新機器、載入程式與 cache、通過 health check，通常要好幾分鐘（第 36 章）。開賣第一分鐘的 burst 遠比這快。而且有些瓶頸根本無法擴展，例如資料庫的寫入能力或外部金流商的配額。Autoscaling 是長期調整容量，admission control 是當下保護自己，兩者都需要。

## 38.6 Load shedding：依 criticality 丟掉對的工作

### Shedding 和 rate limit 的差別

Rate limit 通常依「誰送的、送了多少」做決定，是一種事先約定的配額。**Load shedding**（負載卸除）則是 server 依自己**當下**的狀態，主動丟掉一部分工作來保護其餘的工作。即使每個 client 都沒超過配額，總量仍然可能超過容量，例如三台 instance 剛好掛了一台，這時就要靠 shedding。

Shedding 最簡單的形式是「超過某個 utilization 就拒絕新請求」。但這樣有個問題：被拒絕的可能是結帳，留下來的可能是推薦清單的背景刷新。更好的做法是**依重要程度決定丟什麼**。

### Criticality：讓每個請求帶著自己的重要程度

SRE 書描述 Google 內部把請求分成四個 **criticality**（關鍵程度）等級，Harbor 也照這個概念定義了自己的版本：

| 等級 | 意義 | Harbor 的例子 | 過載時 |
|---|---|---|---|
| CRITICAL_PLUS | 最重要，失敗會直接造成嚴重的使用者或金錢損失 | 付款確認、扣庫存 | 最後才丟 |
| CRITICAL | 使用者正在等、會直接看到結果的請求，production 流量的預設值 | 商品頁、加入購物車、搜尋 | 容量不足時才丟 |
| SHEDDABLE_PLUS | 可以接受偶爾失敗、可以稍後重試 | 批次對帳、商品圖片轉檔 | 早期就開始丟 |
| SHEDDABLE | 經常失敗也沒關係 | 推薦模型的特徵預先計算、分析報表 | 最早丟 |

Criticality 有兩個關鍵設計。第一，它要**跟著請求往下傳**：使用者付款請求在 checkout 是 CRITICAL_PLUS，checkout 因此呼叫 inventory 時，這個呼叫也要繼承同樣的等級，否則 inventory 可能先丟掉了付款流程中的扣庫存。實作上通常放在 RPC metadata 或 HTTP header 裡，由共用的 client library 自動傳遞。第二，它需要**治理**：如果每個團隊都把自己的請求標成最高級，等級就失去意義。Harbor 規定 CRITICAL_PLUS 只能用在 checkout 與 payments 的少數 API，新增要經過 SRE review。

### 依什麼訊號決定要不要丟

Shedding 需要一個代表「我有多忙」的訊號。SRE 書提到 Google 使用 **executor load average**：計算 process 中「正在執行或已就緒、在等 CPU」的 thread 數，再用指數衰減平滑；當它超過這個 task 分配到的處理器數量時，就開始拒絕請求。它比單看 CPU 使用率更能反映「有沒有在排隊」。其他常用訊號包括 queue age、在途請求數、記憶體使用量，以及 adaptive concurrency limit 本身。

不同 criticality 用不同門檻，可以做到「逐級丟棄」（下圖的門檻數字是 Harbor 的示意設定，不是 SRE 書的建議值）：

```text
utilization  0%────────70%────────85%────────95%──────100%
SHEDDABLE    放行      │ 開始拒絕
SHEDDABLE_PLUS 放行────────────────│ 開始拒絕
CRITICAL     放行───────────────────────────│ 開始拒絕
CRITICAL_PLUS 放行──────────────────────────────────────│ 只在完全無法服務時拒絕
```

這張圖從左往右是 instance 的忙碌程度。負載升高時，最不重要的工作最先被拒絕，騰出的資源留給較重要的工作；只有在連 CRITICAL 都要拒絕的時候，才代表真的容量不足，需要人或自動擴展介入。這樣的設計讓「負載上升」從全面劣化變成可預測的逐級退讓。

### 做好 shedding 的幾個細節

- **拒絕要便宜**：拒絕的判斷要放在請求處理的最前面，在解析 body、查資料庫、呼叫下游之前。
- **拒絕要明確**：回傳清楚的狀態碼（例如 503 或 `UNAVAILABLE`），並附上 `Retry-After`，讓 client 知道這是過載而不是 bug。
- **不要讓 shedding 害死 health check**：如果過載的 instance 連 health check 都回不來，load balancer 會把它移除，負載轉到其他 instance，引發連鎖反應（第 37 章的 lame duck 與第 39 章的 cascading failure）。Health check 應該走獨立、輕量的路徑，並且「忙碌」不等於「不健康」。
- **公平**：同一個 criticality 內，要避免某個大租戶的流量擠掉所有小租戶，常見做法是在 shedding 時依租戶的配額比例分配。
- **可觀測**：每一次 shed 都要記錄 metric，依 criticality、原因、client 分組。Shed rate 是過載的直接證據，也是事後檢討容量是否足夠的依據。

## 38.7 Client-side throttling：讓 client 自己減量

### 拒絕也有成本

Server 端的 shedding 再便宜，也不是免費的。每個被拒絕的請求仍然要經過網路、TLS、解析、認證，才能被判斷要不要拒絕。當 offered load 是容量的好幾倍時，光是「說不」就可能耗掉 server 一大部分資源，留給真正工作的部分反而變少。SRE 書描述的正是這種情況：即使 backend 絕大部分的 CPU 都花在拒絕請求上，它仍然可能過載。

解法是讓 client 在把請求送出去之前，就先自己判斷「這個 backend 現在很可能會拒絕我」，直接在本地失敗。這就是 **client-side throttling**（client 端節流）。

### Adaptive throttling 公式

SRE 書描述的 **adaptive throttling**（自適應節流）讓每個 client 自己記錄最近一段時間（書中的例子是兩分鐘）的兩個數字：

- **requests**：應用層想要送出的請求數（包含被自己本地擋下的）
- **accepts**：backend 實際接受（沒有因過載而拒絕）的請求數

接著，每一個新請求以下面的機率在本地直接拒絕：

```text
client 端拒絕機率 = max(0, (requests − K × accepts) / (requests + 1))
```

正常時 backend 幾乎都接受，accepts ≈ requests，分子是負的，機率是 0，完全不影響流量。Backend 開始拒絕時，accepts 下降，一旦 requests 超過 K 倍的 accepts，client 就開始在本地丟棄多出來的部分。

```text
算例：K = 2，最近兩分鐘 requests = 1,000，accepts = 400
  拒絕機率 = (1,000 − 2 × 400) / 1,001 ≈ 0.20
  → client 只送出約 800 個，約是 backend 能接受量的 2 倍

若 backend 恢復，accepts 上升到 500 以上
  → 1,000 − 2 × 500 = 0 → 拒絕機率回到 0
```

**K** 是一個乘數，決定 client 願意讓多少「可能被拒絕」的請求繼續送到 backend。K = 2 代表 client 送到 backend 的量大約是 backend 實際接受量的兩倍，也就是 backend 會浪費一些資源在拒絕上，但 client 對 backend 狀態的估計會比較快更新（如果完全不送，client 就無法知道 backend 恢復了沒）。K 越小越積極，backend 收到的多餘請求越少，但 client 對恢復的反應也越慢；K 越大越保守。SRE 書的例子是：把 K 降到 1.1，代表 backend 每接受 10 個請求，只會拒絕大約 1 個；書中也說 Google 一般偏好 K = 2。

### 它為什麼有效

Adaptive throttling 的優點是**每個 client 只用自己看得到的資訊**，不需要和其他 client 或中央協調器溝通，也不需要 backend 告訴它容量是多少。只要每個 client 都採用同樣的規則，整體送到 backend 的量就會自動收斂到 backend 接受量的 K 倍左右。它特別適合「很多 client 呼叫同一個 backend」的情況。

它的限制是需要足夠的請求量才能有穩定的統計；只送很少請求的 client，兩分鐘的視窗裡可能只有幾個樣本。另外它保護的是「backend 因過載而拒絕」的情況，所以 backend 要用明確、可辨識的錯誤碼表示過載，client library 才能把它和其他錯誤（例如參數錯誤）區分開來計算。

## 38.8 Graceful degradation：少一點，但還能用

### 降級是什麼

Shedding 是「不做」，**graceful degradation**（優雅降級）是「做少一點」：在過載或依賴失效時，用較便宜的方式提供部分功能，而不是完全失敗。使用者拿到的結果比平常差，但仍然能完成主要目的。

Harbor 為雙十一定義了幾個降級模式：

| 功能 | 正常 | 降級後 | 省下什麼 |
|---|---|---|---|
| 搜尋 | 即時查詢全部商品，個人化排序 | 只查熱門商品索引，排序用預先算好的結果；頁面標示「顯示部分結果」 | 大部分的搜尋 CPU 與記憶體 |
| 商品頁 | 即時庫存數字、個人化推薦 | 庫存只顯示「有貨／少量／售完」並使用 30 秒內的 cache；不顯示推薦 | 對 inventory 與推薦服務的大量呼叫 |
| 購物車 | 每次變更都重算運費與優惠 | 運費與優惠在進入結帳時才算 | 優惠計算服務的負載 |
| 訂單通知 | 立刻寄送 | 延後到流量下降再寄 | 通知服務與外部簡訊商的額度 |
| AI 客服 | 完整的多輪對話與工具呼叫 | 只回答常見問題範本，退款轉為建立工單 | 模型推論成本與後端工具呼叫 |

### 降級要能被信任

降級模式最大的風險是**它平常沒有在跑**。一段一年只在大促時啟用一次的程式碼，很可能早就因為其他變更而壞掉，在最需要的時候才發現。SRE 書也提醒，降級機制應該保持簡單、容易理解，並且要定期演練。Harbor 的做法是：

1. **用 feature flag 控制**，每個降級模式都能獨立開關，也有一個「全部降級」的總開關。
2. **觸發條件要簡單**：由明確的訊號（例如 queue age 超過 500 ms）或值班者手動觸發，不依賴複雜的推論邏輯。
3. **定期演練**：每月在低峰時段對一小部分流量啟用降級模式，確認它真的比正常模式便宜，而且結果正確。
4. **結果要標示**：降級的回應帶有標記（例如 response header 或欄位），下游與監控都知道這是降級結果，不會把 30 秒前的庫存當成精確數字使用。
5. **監控降級比例**：降級的請求數也是 SLI 的一部分；如果某個降級模式長期開著，代表容量規劃出了問題。

> [!example] 例子
> 11 月 10 日晚上 21:40，雙十一午夜尖峰前，推薦服務的延遲上升。值班者依 runbook 打開「商品頁不顯示推薦」的 flag，商品頁的 p99 從 1.8 秒回到 400 ms，負責推薦的 search 團隊則在不受流量壓力的情況下排查問題。使用者看到的是少了一個區塊的商品頁，而不是轉圈圈的白畫面。

### 降級與 correctness

降級不能犧牲不該犧牲的東西。顯示稍舊的庫存「有貨」可以接受，但扣庫存時一定要用準確的數字，否則會超賣。決定一個功能能不能降級，要先問：降級後的結果如果錯了，最壞的後果是什麼？可以補救嗎？金流、權限、庫存扣減這類**不變量**（invariant，任何時候都必須成立的條件）通常不能降級，只能拒絕。

## 38.9 把它們組起來：Harbor 的分層過載防護

前面的機制各自解決一部分問題，真正的防護來自把它們放在正確的位置。開賣事故之後，Harbor 的 SRE 團隊和各服務團隊一起畫出了這張圖：

```text
使用者
  │
  ▼
[CDN／edge]          擋爬蟲與惡意流量；全域 rate limit；搶購時啟用虛擬排隊頁
  │
  ▼
[API gateway]        每個 client／賣家的 token bucket 配額；帶上 deadline 與 criticality
  │
  ▼
[服務 instance]      ① 檢查 deadline 是否還夠 → 不夠就拒絕
  │                  ② 依 criticality 與 utilization 決定是否 shed
  │                  ③ 並行數上限（adaptive concurrency limit）
  │                  ④ 有上限的 queue，deadline-aware dequeue
  │                  ⑤ 依 flag 進入降級模式
  ▼
[client library]     adaptive throttling；尊重 Retry-After；有限的 retry（第 39 章）
  │
  ▼
[下游依賴]           每個依賴自己也有同樣的防護
```

由上往下讀：越外層的防護越便宜、越粗略，負責擋掉「明顯不該進來」的流量；越內層越精確，知道每個請求的價值與自己當下的狀態。Deadline 與 criticality 在 gateway 加上，之後跟著請求一路傳遞，讓每一層都能做出一致的決定。Client library 是很多人忽略的一層：同一份共用的 library 決定了全公司所有服務怎麼對待「被拒絕」，它的預設值比任何單一服務的設定都重要。

### 驗證：找到容量的「膝蓋」

防護設計得再好，也要用 load test 驗證（第 25 章）。Harbor 每次大促前都會做一次 **overload test**：不是測「能撐住預期流量」，而是刻意把流量推到預期容量的 1.5 倍、2 倍、3 倍，觀察三件事：

1. **膝蓋在哪裡**：goodput 停止上升的那個點，就是真實容量。它通常比根據 CPU 估算的容量低。
2. **超過膝蓋後 goodput 是否維持**：好的系統在 2 倍、3 倍負載下，goodput 仍接近容量；壞的系統會崩塌。
3. **流量退去後能否自己恢復**：有些系統在負載下降後仍然卡在壞狀態，這是第 39 章要談的 metastable failure。

### 要放上儀表板的訊號

| 類別 | 訊號 |
|---|---|
| 負載 | offered load（含被拒絕的）、各 criticality 的流量比例 |
| 結果 | goodput（deadline 內成功的比例）、各原因的拒絕數（配額、shed、deadline 不足） |
| 等待 | queue age、queue depth、在途請求數、並行上限的當前值 |
| 資源 | CPU、記憶體、thread／connection pool 使用率、GC 時間 |
| 降級 | 每個降級模式的啟用狀態與受影響的請求比例 |

## 38.10 動手寫：queue 策略與 adaptive throttling 模擬

### 模擬一：四種 queue 策略

下面的程式模擬一個容量每秒 100 個請求的 inventory instance（所有參數都是為了說明而假設的數字，到達時間用 Poisson 過程、服務時間固定 10 ms）。平常每秒有 80 個請求，第 10～30 秒開賣時湧進每秒 150 個。使用者最多等 1 秒，超過就放棄。我們比較幾種 queue 策略在同一份流量下的結果。

```python
import random
from collections import deque

SERVICE_MS = 10          # 每個請求佔用 worker 10 ms → 容量 100 req/s
DEADLINE_MS = 1000       # 使用者最多等 1 秒
SIM_MS = 60_000          # 模擬 60 秒


def arrivals(seed=7):
    """平常 80 req/s；第 10～30 秒開賣，湧進 150 req/s。"""
    rng = random.Random(seed)
    t, out = 0.0, []
    while t < SIM_MS:
        rate = 150 if 10_000 <= t < 30_000 else 80
        t += rng.expovariate(rate / 1000)
        out.append(int(t))
    return out


def simulate(policy, max_queue=None):
    arr = deque(arrivals())
    queue = deque()
    busy_until, current = 0, None
    good = late = rejected = dropped = 0
    latencies, max_len = [], 0
    for now in range(SIM_MS + 30_000):          # 多跑 30 秒讓 queue 排空
        while arr and arr[0] <= now:
            t = arr.popleft()
            if max_queue is not None and len(queue) >= max_queue:
                rejected += 1                    # 立刻回 503：便宜、使用者馬上知道
            else:
                queue.append(t)
        if current is not None and now >= busy_until:
            wait = now - current
            if wait <= DEADLINE_MS:
                good += 1
                latencies.append(wait)
            else:
                late += 1                        # 做完了，但使用者早就走了
            current = None
        while current is None and queue:
            if policy == "lifo" and len(queue) > 20:
                t = queue.pop()                  # 塞車時先服務最新的請求
            else:
                t = queue.popleft()
            if policy in ("deadline", "lifo") and now - t > DEADLINE_MS - SERVICE_MS:
                dropped += 1                     # 已經來不及，丟掉不做
                continue
            current, busy_until = t, now + SERVICE_MS
        max_len = max(max_len, len(queue))
    latencies.sort()
    p = lambda q: latencies[int(q * (len(latencies) - 1))] if latencies else 0
    total = good + late + rejected + dropped
    return total, good, late, rejected, dropped, p(0.5), p(0.99), max_len


print("  總數  準時  白做  拒絕  丟棄  p50  p99  隊長  策略")
cases = [("無上限 FIFO", "fifo", None),
         ("有上限 FIFO(100)", "fifo", 100),
         ("有上限 FIFO(50)", "fifo", 50),
         ("有上限＋丟過期(100)", "deadline", 100),
         ("無上限＋丟過期＋LIFO", "lifo", None)]
for name, policy, mq in cases:
    total, good, late, rej, drop, p50, p99, mlen = simulate(policy, mq)
    print(f"{total:>6}{good:>6}{late:>6}{rej:>6}{drop:>6}{p50:>5}{p99:>5}{mlen:>6}  {name}")
```

執行結果：

```text
  總數  準時  白做  拒絕  丟棄  p50  p99  隊長  策略
  6278  1096  5182     0     0   37  953  1064  無上限 FIFO
  6278  4268  1046   964     0   44 1000   100  有上限 FIFO(100)
  6278  5264     0  1014     0   54  509    50  有上限 FIFO(50)
  6278  5313     0   947    18   73  999   100  有上限＋丟過期(100)
  6278  5228     0     0  1050   18  117  1064  無上限＋丟過期＋LIFO
```

欄位依序是：總請求數、在 1 秒內完成的（goodput）、做完但已逾時的（白工）、進門就被拒絕的、從 queue 取出時發現來不及而丟棄的、成功請求的 p50 與 p99 延遲（ms）、queue 的最大長度。逐列解讀：

1. **無上限 FIFO** 是 Harbor 開賣時的設定。總共 6,278 個請求中只有 1,096 個準時完成，而且全是開賣前（817 個）與開賣最初幾秒（279 個）的請求；之後 queue 一直到模擬結束都沒有縮回 1 秒以內，連開賣結束後才到的人也全部逾時。開賣期間 server 一秒都沒閒著，做了 5,182 個白工。注意成功請求的 p50 只有 37 ms，看起來很健康，這是**倖存者偏差**：只統計成功請求的延遲，會完全看不到失敗的那些人。這也是為什麼第 32 章把 latency SLI 定義成「門檻內完成的請求數 / 所有有效請求數」：逾時與失敗的請求要留在分母裡，算成壞事件。
2. **有上限 FIFO(100)** 把準時完成提高到 4,268 個，但仍有 1,046 個白工。原因是 38.3 算過的：100 個 × 10 ms = 1 秒，排到隊尾的人剛好等到 deadline。
3. **有上限 FIFO(50)** 依 deadline 縮小 queue 後，白工歸零，準時完成 5,264 個，p99 降到 509 ms。被拒絕的人數只多了 50 個，換來的是所有被接受的人都在時間內得到回應。
4. **有上限＋丟過期** 換一種方式達到類似效果：queue 仍是 100，但取出時檢查 deadline，來不及的直接丟掉（成本是零），goodput 最高。
5. **LIFO＋丟過期** 讓成功請求的 p99 只有 117 ms，因為塞車時永遠先服務剛到的人。但 queue 沒有上限，最長仍然排到 1,064 個，在真實系統中這代表記憶體壓力。被丟掉的 1,050 個請求是 LIFO 的代價：它們被新請求一直插隊，在 queue 裡待了 1 到 20 秒（中位數約 11 秒）才被取出丟棄；使用者早在 1 秒時就自己逾時放棄，從頭到尾沒有收到明確的回應，不像「拒絕」那樣讓使用者立刻知道。

開賣期間的請求總量超過容量，所以任何策略都無法讓每個人成功；差別在於「失敗的人怎麼失敗」與「成功的人有多少」。在真實系統中，`max_queue` 對應 thread pool 或 server framework 的 queue 設定，`DEADLINE_MS` 對應從請求 header 讀到的剩餘 deadline，`rejected` 則是回給 client 的 503。

### 模擬二：adaptive throttling

第二段程式模擬 38.7 的情況（同樣是假設的參數）：拒絕一個請求要花處理成本的 20%，client 每秒想送 300 個請求給一個每秒只有 120 單位資源的 backend。

```python
import random
from collections import deque

BACKEND_BUDGET = 120.0   # backend 每秒能花的「工作單位」
SERVE_COST = 1.0         # 處理一個請求花 1 單位
REJECT_COST = 0.2        # 拒絕一個請求也要花 0.2 單位（解析、認證、回錯誤）
OFFERED = 300            # client 每秒想送 300 個請求
WINDOW_S = 10            # 統計最近 10 秒（SRE 書中的例子用 2 分鐘）


def backend(n_requests):
    """回傳這一秒 backend 實際接受（並處理完）的請求數。"""
    # accepts * SERVE_COST + (n - accepts) * REJECT_COST <= BUDGET
    if n_requests * SERVE_COST <= BACKEND_BUDGET:
        return n_requests
    accepts = (BACKEND_BUDGET - n_requests * REJECT_COST) / (SERVE_COST - REJECT_COST)
    return max(0, int(accepts))


def run(k=None, seconds=30, seed=1):
    rng = random.Random(seed)
    history = deque(maxlen=WINDOW_S)      # 每格是 (requests, accepts)
    rows = []
    for sec in range(seconds):
        reqs = sum(r for r, _ in history)
        accs = sum(a for _, a in history)
        p_reject = 0.0 if k is None else max(0.0, (reqs - k * accs) / (reqs + 1))
        sent = sum(1 for _ in range(OFFERED) if rng.random() >= p_reject)
        accepted = backend(sent)
        history.append((OFFERED, accepted))   # requests 計的是「應用層想送的」數量
        rows.append((sec, p_reject, sent, accepted))
    return rows


for label, k in [("不節流", None), ("adaptive throttling K=2", 2), ("K=1.1（更積極）", 1.1)]:
    rows = run(k)
    print(f"--- {label}")
    for sec, p, sent, acc in rows:
        if sec in (0, 1, 2, 5, 10, 29):
            print(f"第 {sec:>2} 秒  本地拒絕率 {p:4.0%}  送到 backend {sent:>3}  被接受 {acc:>3}")
```

執行結果：

```text
--- 不節流
第  0 秒  本地拒絕率   0%  送到 backend 300  被接受  75
第  1 秒  本地拒絕率   0%  送到 backend 300  被接受  75
第  2 秒  本地拒絕率   0%  送到 backend 300  被接受  75
第  5 秒  本地拒絕率   0%  送到 backend 300  被接受  75
第 10 秒  本地拒絕率   0%  送到 backend 300  被接受  75
第 29 秒  本地拒絕率   0%  送到 backend 300  被接受  75
--- adaptive throttling K=2
第  0 秒  本地拒絕率   0%  送到 backend 300  被接受  75
第  1 秒  本地拒絕率  50%  送到 backend 162  被接受 109
第  2 秒  本地拒絕率  39%  送到 backend 193  被接受 101
第  5 秒  本地拒絕率  35%  送到 backend 184  被接受 103
第 10 秒  本地拒絕率  34%  送到 backend 186  被接受 103
第 29 秒  本地拒絕率  33%  送到 backend 213  被接受  96
--- K=1.1（更積極）
第  0 秒  本地拒絕率   0%  送到 backend 300  被接受  75
第  1 秒  本地拒絕率  72%  送到 backend  87  被接受  87
第  2 秒  本地拒絕率  70%  送到 backend 105  被接受 105
第  5 秒  本地拒絕率  66%  送到 backend  94  被接受  94
第 10 秒  本地拒絕率  65%  送到 backend 104  被接受 104
第 29 秒  本地拒絕率  57%  送到 backend 136  被接受 115
```

逐段解讀：

1. **不節流**時，backend 每秒收到 300 個請求，光是拒絕其中的 225 個就花掉 45 單位，只剩 75 單位處理真正的工作。如果拒絕不用成本，它每秒能完成 120 個；「努力拒絕」讓它少做了 37.5%。
2. **K = 2** 時，client 從第 1 秒開始在本地丟掉約三到五成的請求，送到 backend 的量收斂到接受量的兩倍左右（約 200 對 100），backend 每秒接受的請求從 75 提高到約 100。這正是公式的設計：本地拒絕率會停在讓「實際送出的量 ≈ K × accepts」的位置。可以驗算平衡點：送出 S 個時 backend 接受 (120 − 0.2S) / 0.8 個，令 S = 2 × 接受數，解得 S = 200、接受 100。
3. **K = 1.1** 更積極，送到 backend 的量非常接近它能接受的量，浪費更少，第 29 秒接受了 115 個。代價是 client 本地拒絕率很高，而且當 backend 恢復時，client 需要更久才會察覺並放更多流量進去。這就是 K 的取捨。

這個模型刻意簡化：真實系統的拒絕成本不是固定比例、client 很多個、視窗通常是兩分鐘。但機制相同：**每個 client 只看自己的 requests 與 accepts，就能讓整體流量自動退到 backend 能負荷的附近**。在真實系統中，這段邏輯通常放在共用的 RPC client library 裡，應用程式開發者不需要自己實作。

## 38.11 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| 大 queue「避免丟請求」 | 過載時每個人都等到逾時，白工佔滿資源 | Harbor 開賣時 inventory 的無上限 queue | 依 deadline 推出 queue 上限，取出時檢查 deadline |
| 在處理後段才 shed | 拒絕前已花掉大部分成本，shed 沒有保護效果 | 查完資料庫、呼叫完推薦服務，才因為逾時回錯 | 准入判斷放在最前面，在任何昂貴操作之前 |
| Criticality 沒有治理 | 所有團隊都標最高級，shedding 退化成隨機丟棄 | 一年後 70% 的流量都是 CRITICAL_PLUS | 最高等級需要 review；定期稽核各等級流量比例 |
| 只靠 autoscaling | Burst 比擴展速度快，或瓶頸無法擴展 | 開賣第一分鐘就過載，新機器五分鐘後才就緒；資料庫寫入是瓶頸 | Admission control 與 shedding 先保護，autoscaling 補長期容量；大促前預先擴容 |
| 降級模式平常沒跑 | 需要時才發現它壞了或更貴 | 「只查熱門索引」的程式碼半年前被重構弄壞，到大促當天打開 flag 才發現 | 定期在部分流量上演練，有自動化測試 |
| 過載讓 health check 失敗 | Load balancer 移除忙碌的 instance，負載集中到剩下的機器 | inventory 忙到 health check 逾時，十台被移除三台，其餘七台更快倒下 | Health check 走獨立輕量路徑，過載不等於不健康（第 37、39 章） |
| Rate limit 用固定 QPS | 請求成本改變時，限制不再對應真實容量 | 新的搜尋功能讓每個請求貴三倍，QPS 限制沒變，搜尋叢集仍然過載 | 以資源或並行數為基礎設定限制，並在請求組合改變時重新 load test |
| 全域單一配額 | 一個租戶吃光所有人的配額 | 一個賣家的同步程式寫錯迴圈，所有賣家的 API 都被限流 | Per-tenant 配額與公平排程 |

## 38.12 AI 時代：什麼變了？

**第一，AI 請求的成本差異極大，而且事前很難知道。** 傳統 API 請求之間的成本差幾倍；Harbor AI 客服的一次對話，可能是一個簡短問答，也可能是讀了二十筆訂單、呼叫十次工具、產生上千 token 的多步驟任務，差距可以到數百倍。這讓「每秒請求數」幾乎完全失去作為容量單位的意義。實務上要改用 token 數（輸入與輸出分開）、並行的推論數、GPU 使用時間，或每個任務的「步驟預算」作為准入與配額的單位。Harbor 的做法是在 AI gateway 對每個請求先估算輸入 token，超過上限的直接拒絕或要求先摘要，並對每個租戶分別設定每分鐘 token 配額與同時進行的 agent 任務數。

**第二，模型服務本身就是一個有嚴格容量限制的下游。** 不管是自建推論叢集還是使用外部模型 API，它都有速率限制、配額，以及在高負載下明顯變慢的延遲。對它的呼叫需要和其他下游一樣的保護：有上限的 queue、依 deadline 的准入、尊重 429 與 `Retry-After`、adaptive throttling。過載時的降級選項也更多元：改用較小、較便宜的模型，限制回應長度，關閉需要多次工具呼叫的流程，或改成範本回答。

**第三，criticality 的概念要延伸到 agent 的工作。** 一個 AI coding agent 在背景跑大量測試、一個 AI 維運 agent 在事故中查詢 metrics、AI 客服幫使用者送出退款申請，它們對共用基礎設施的重要程度完全不同。如果不標示，一個在背景大量掃描 log 的 agent 可能在事故當下擠掉值班者的查詢。Harbor 規定所有 agent 發出的請求都要帶 criticality 與 agent 身份，背景 agent 一律是 SHEDDABLE。

**第四，AI 可以幫忙分析過載，但准入與降級的判斷要由確定性的機制執行。**

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 從架構與設定檔盤點一條請求路徑上的所有 queue、timeout、pool 大小，標出沒有上限的地方 | 盤點結果要對照實際設定與 load test 驗證；AI 可能漏掉框架預設值 |
| 分析過載事故的 metrics，找出最先飽和的資源與流量組成的變化 | 容量數字與 queue 上限的最終決定由服務 owner 根據 load test 決定 |
| 依 runbook 草擬降級決策建議，例如「queue age 超過門檻，建議開啟推薦降級」 | 降級 flag 的開關要有明確授權；高影響的降級（例如關閉結帳功能）只能由人執行 |
| 產生 overload test 的流量腳本與報告 | Criticality 等級的分配是業務決策，由產品與工程共同決定並 review |
| 估算 AI 請求的 token 與步驟成本，協助設定配額 | Token、步驟、並行數、花費的硬上限必須在 gateway 或 harness 中強制，不能依賴模型自己遵守 |

> [!ai] AI 提醒
> 不要讓 AI agent 自己決定自己的優先級或配額。一個被要求「盡快完成任務」的 agent，如果能修改自己請求的 criticality 或重試設定，它會傾向把自己標成最高等級。所有優先級與配額都應該由 agent 執行環境（harness）依 agent 身份強制附加，agent 本身無法改寫。

## 38.13 專家怎麼想

- **先問「我們要犧牲什麼」，而不是「怎麼不犧牲」。** 容量有限是事實，過載一定會發生。資深 SRE 設計過載防護時，第一個問題是：容量不足時，哪些使用者旅程必須保住、哪些可以變差、哪些可以直接關掉？這個答案要在事故之前和產品一起決定。
- **看 goodput，不看 throughput。** 「每秒處理了多少」沒有意義，「每秒有多少使用者在時間內拿到正確結果」才有意義。專家看過載的儀表板，第一張圖永遠是 deadline 內成功的比例。
- **把每一個 queue 都當成延遲上限。** 看到一個 queue 時，專家會問：它滿的時候，最後一個人要等多久？這比 deadline 長嗎？如果答案是「不知道」或「比 deadline 長」，這個 queue 就該縮小或加上 deadline 檢查。
- **每個服務都要能保護自己。** 上游的 rate limit 會設錯，新的 client 會繞過 gateway，重試會在你不知道的地方發生。只有服務自己知道自己現在有多忙，所以最後一道防線一定在服務內部。
- **過載測試要測到超過容量。** 只測「能撐住預期流量」的 load test，無法回答「超過時會怎樣」。真正有用的是推到 2 倍、3 倍，看 goodput 是否維持，再看流量退去後能不能自己恢復。

## 38.14 動手練習

1. 修改 38.10 的模擬一，加入「queue age 超過 300 ms 就拒絕新請求」的策略，和其他策略比較 goodput 與 p99。再把服務時間改成隨機（例如平均 10 ms 的指數分佈），觀察 queue 上限 50 是否仍然足夠。
2. 盤點你熟悉的一個服務（或 Harbor 的 checkout）從使用者到資料庫的所有 queue：TCP backlog、load balancer、web server、thread pool、connection pool。寫下每個的預設上限與滿了之後的行為，標出沒有上限或不知道上限的地方。
3. 為 Harbor 的五個服務（搜尋、商品頁、購物車、checkout、通知）的主要 API 指定 criticality，並寫下判斷理由。哪些呼叫在不同情境下應該有不同等級？
4. 修改模擬二，讓 backend 在第 15 秒恢復成每秒 300 單位的容量，比較 K = 1.1、2、4 時 client 需要幾秒才讓送出量回到 300。
5. 為 Harbor 的 AI 客服設計一份降級計畫：列出至少三個降級等級，每個等級的觸發條件、使用者看到的行為、省下的資源，以及哪些動作（例如退款）在降級時必須禁止。
6. 設計一個 overload test 計畫：流量組合、要推到幾倍容量、要觀察哪些訊號、怎麼判斷系統「超過容量後仍然穩定」。

## 本章重點整理

- 過載時 offered load、throughput 與 goodput 會分開；沒有保護的系統 goodput 會崩塌，而 throughput 看起來仍然正常。
- Goodput 崩塌的主要來源是白工、重試、每個請求成本上升與元件死亡，它們互相加強，所以過載很少停在「慢一點」。
- 容量要用資源（CPU 時間、並行數）衡量，不要只用 QPS，因為不同請求的成本可能差上百倍。
- Queue 只能吸收短期 burst，不能創造容量；只要 λ 長期大於 μ，任何 queue 最終都會滿。
- 同步請求的 queue 上限要從 deadline 推出來，並優先觀察 queue age；過載時可以用 deadline-aware dequeue、adaptive LIFO 或 CoDel 避免處理已被放棄的請求。
- 系統中有許多隱藏的 queue（TCP backlog、thread pool、connection pool），每一個都需要上限與監控。
- Backpressure 必須端到端，任何一層「先收下再說」的無上限 buffer 都會吞掉壓力訊號。
- Admission control 在昂貴工作之前決定是否接受；token bucket、concurrency limit 與 per-customer quota 各自處理不同的問題。
- Load shedding 依 server 當下的狀態丟棄工作，應依 criticality 逐級進行，並讓 criticality 隨請求往下傳、受到治理。
- 拒絕本身也有成本；adaptive throttling 讓 client 依 max(0, (requests − K × accepts)/(requests + 1)) 在本地拒絕，K 通常為 2。
- Graceful degradation 用較便宜的方式提供部分功能，但必須簡單、定期演練、標示結果，並且不能破壞金流與庫存等不變量。
- Autoscaling 太慢，無法應付秒級的 burst；admission control 與 shedding 負責當下保護，autoscaling 負責長期容量。
- 過載測試要推到超過容量，確認 goodput 能維持，並確認流量退去後系統能自己恢復。
- AI 請求的成本差異極大，准入與配額要改用 token、步驟、並行數等單位，並由 harness 強制執行，不能讓 agent 決定自己的優先級。

## 延伸問答

> [!question]- Q1. Throughput 和 goodput 有什麼不同？為什麼過載時只看 throughput 會誤判？
> Throughput 是系統每秒處理完的工作量，goodput 是其中真正對使用者有用的部分：在 deadline 內完成、結果正確、使用者還在等。正常時兩者幾乎一樣，所以很多團隊只看 throughput。
>
> 過載時，server 可能以滿速處理一堆已經逾時、使用者早就放棄的請求。這時 throughput 維持在容量附近，儀表板看起來「處理量正常」，goodput 卻接近零。Harbor 開賣事故就是如此：inventory 每秒處理數停在容量上限附近，成功下單數卻幾乎是零。所以過載相關的儀表板與告警應該以「deadline 內成功的比例」為主，throughput 只能當成輔助訊號。

> [!question]- Q2. 一個服務每個請求處理 20 ms，有 8 個 worker，client 的 deadline 是 800 ms。Queue 上限大概該設多少？
> 先算每秒容量：8 個 worker × (1000 / 20) = 每秒 400 個請求。排在 queue 第 n 位的請求，大約要等 n / 400 秒才開始處理。若要讓它在 deadline 內完成，等待時間加上處理時間要小於 800 ms，還要預留網路與上游的時間。
>
> 假設只讓 queue 等待佔用 deadline 的一半（400 ms），queue 上限約為 400 × 0.4 = 160。實務上還要考慮處理時間的變異：若某些請求比 20 ms 慢很多，實際等待會更久，所以通常再打個折，並且在取出時檢查剩餘 deadline 作為第二道保護。最後要用 load test 驗證，而不是只靠計算。

> [!question]- Q3. 為什麼「把 queue 調大」在過載時通常會讓情況更糟？
> 對同步請求來說，queue 的大小就是延遲的上限。Queue 調大之後，過載時新請求要等更久才輪到，等待時間一旦超過 client 的 timeout，server 處理這個請求就是白工。Queue 越大，白工比例越高，真正準時完成的反而越少。
>
> 大 queue 還有副作用：佔用更多記憶體、增加 GC 壓力、讓過載持續更久（流量退去後還要花很長時間消化 backlog），而且讓使用者在等很久之後才知道失敗，他們通常會重試，進一步增加負載。調大 queue 只在流量是短暫 burst、平均負載低於容量時有幫助。

> [!question]- Q4. Rate limiting 和 load shedding 有什麼不同？兩者都需要嗎？
> Rate limiting 通常依「誰送的、送了多少」做決定，是事先約定的配額，例如每個賣家每分鐘 600 次 API 呼叫。它保護的是公平性：防止單一 client 吃掉所有容量。它不知道 server 當下的狀態，即使 server 很閒也會擋，即使 server 快倒了只要沒超配額也會放行。
>
> Load shedding 是 server 依自己當下的負載（CPU、queue age、在途請求數）主動丟棄工作，保護的是 server 本身。即使每個 client 都在配額內，總量仍可能超過容量，例如一部分 instance 掛掉的時候。兩者處理不同的問題，所以都需要：rate limit 放在 gateway 處理公平與濫用，shedding 放在服務內部做最後的自我保護。

> [!question]- Q5. 你是 Harbor 的值班者，雙十一當晚 inventory 的 queue age 從 50 ms 升到 900 ms，CPU 95%，shed rate 開始上升。你會依序做什麼？
> 第一步是確認影響：goodput（deadline 內成功的比例）和 checkout 的 SLI 是否已經下降，以及 shed 的是哪些 criticality 的請求。如果被丟掉的只有 SHEDDABLE 流量，代表防護正在照設計運作，結帳仍然安全，可以爭取時間調查；如果 CRITICAL 甚至 CRITICAL_PLUS 也開始被丟，就要立刻止血。
>
> 止血的選項依影響由小到大：依 runbook 啟用降級模式（例如商品頁改用 cache 的庫存狀態，大幅減少對 inventory 的呼叫）、暫停批次與背景工作、在 edge 對非關鍵頁面加強限流或啟用排隊頁，同時擴容。要避免的動作是調大 queue 或 timeout，這只會讓白工更多。穩定之後，再查流量組成是否改變、是否有某個 client 在大量重試，以及容量規劃與實際的差距。

> [!question]- Q6. Adaptive throttling 公式中的 K 代表什麼？K 設成 1 會怎樣？
> K 決定 client 願意送到 backend 的請求量是 backend 接受量的幾倍。當 requests 超過 K × accepts 時，client 開始在本地拒絕多出來的部分，最後送出的量大約穩定在 K × accepts。K = 2 代表 backend 會收到大約兩倍於它能接受的請求，其中一半會被拒絕，backend 浪費一些資源，但 client 能較快觀察到 backend 的恢復。
>
> 若 K 接近 1，client 幾乎只送 backend 會接受的量，浪費最少。但這有一個問題：client 是靠被接受的請求數判斷 backend 狀態的，如果它幾乎不送出「可能被拒絕」的請求，當 backend 恢復時，accepts 只會很慢地上升，client 需要很長時間才會放回流量。K 越小越積極、恢復越慢；K 越大越保守、浪費越多。SRE 書提到 Google 一般用 K = 2。

> [!question]- Q7. 反例題：有人說「我們的服務都有 autoscaling，而且上游 gateway 有 rate limit，所以服務內部不需要 load shedding。」你怎麼回應？
> 這個論點有三個漏洞。第一，autoscaling 需要時間偵測負載、啟動機器、載入 cache、通過 health check，通常是分鐘級，而開賣或事故造成的 burst 是秒級；在這幾分鐘內，服務只能靠自己撐住。第二，有些瓶頸根本不會隨 autoscaling 改善，例如資料庫寫入、外部金流商的配額、單一熱門商品的 lock。第三，gateway 的 rate limit 是依預先設定的配額，不知道服務當下的真實容量；如果一部分 instance 掛掉、或請求組合變貴，即使流量都在配額內，服務仍然會過載。
>
> 此外，不是所有流量都經過 gateway：內部服務之間的呼叫、批次工作、重試，都可能直接打到服務。所以每個服務都要能依自己的狀態保護自己，上游的保護是額外的防線，不是替代品。

> [!question]- Q8. AI 情境：Harbor 的 AI 客服使用外部模型 API，雙十一當晚模型供應商開始大量回傳 429。AI 客服應該怎麼處理？
> 首先，429 是明確的 backpressure 訊號，client 必須尊重它：讀取 `Retry-After`、停止立即重試，並用 adaptive throttling 讓送出的量降到供應商願意接受的範圍。如果每個對話都各自重試，只會讓 429 更多，同時讓使用者等更久。
>
> 其次要依 criticality 分配有限的模型額度：正在進行退款確認的對話比「推薦商品」的閒聊重要，背景的對話摘要工作應該最先暫停。接著啟用降級模式：常見問題改用範本回答，需要多步驟推理的流程改為建立工單由人工後續處理，必要時切換到配額較寬鬆的較小模型。最後，這些決策要由 AI gateway 依確定性的規則執行，而不是讓每個 agent 自己判斷要不要重試；事後也要檢討配額規劃，例如大促前是否應該向供應商申請更高額度，或準備備援的模型供應來源。

## 延伸閱讀

- [Site Reliability Engineering — Handling Overload](https://sre.google/sre-book/handling-overload/)：本章 criticality、per-customer limit、adaptive throttling 與 utilization 訊號的原始來源。
- [Site Reliability Engineering — Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/)：queue 管理、load shedding 與 graceful degradation 的詳細討論，也是第 39 章的主要來源。
- [Site Reliability Engineering — Load Balancing at the Frontend](https://sre.google/sre-book/load-balancing-frontend/)：與第 37 章相關，說明使用者流量如何進入資料中心，是理解過載從何而來的背景。
