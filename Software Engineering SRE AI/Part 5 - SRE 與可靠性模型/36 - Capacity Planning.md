---
chapter: 36
title: Capacity Planning、Performance 與 Provisioning
part: 5
---

# 第 36 章　Capacity Planning、Performance 與 Provisioning

> [!abstract] 本章地圖
> **核心問題**：在流量真正來臨之前，要怎麼算出「需要多少資源、什麼時候要到位」，讓服務在尖峰與故障同時發生時仍然守住 SLO？
>
> **你會學到**：
> - 區分 organic 與 inorganic demand，把業務預測轉換成每個服務的負載
> - 用 load test 找出單機的 safe capacity，而不是壓到崩潰的最大值
> - 用 Little's Law 與排隊理論解釋「CPU 才 60%，latency 卻爆了」
> - 用 N+1、N+2 與 failure domain 計算故障時仍夠用的容量，並分清 headroom 在保護什麼
> - 把 provisioning 的 lead time、quota、暖機時間排進時程，並判斷 autoscaling 什麼時候靠不住
> - 在成本與可靠性之間做出可以被檢討的取捨
>
> **前置知識**：第 25 章（load test）、第 32 章（SLO 與 latency SLI）、第 33 章（saturation 與 golden signals）
>
> **對應原書**：SRE 第 1 章（demand forecasting 與 provisioning 段落）、第 18 章〈Software Engineering in SRE〉（Auxon 與 intent-based capacity planning）、第 21 章〈Handling Overload〉；SRE Workbook 第 11 章〈Managing Load〉

## 36.1 故事：午夜十二點，CPU 只有 55%

Harbor 去年（第 3 年）第一次大規模參加雙十一。那時公司剛成立 4 人的 SRE 團隊，還沒有任何容量計畫：工程經理 Kevin 在活動前一週問 checkout 的 tech lead 美華「機器夠不夠」，美華看了一下平日的 CPU 圖，checkout 服務平常 24 台、只用到 25%，於是回答「把台數加倍到 48 台應該就夠了」。團隊另外打開了 autoscaling，心想萬一不夠，系統會自己補。

11 月 11 日 00:00，行銷推播同時送到兩百萬支手機。checkout 的請求量在 40 秒內從每秒約 800 跳到每秒約 5,000。值班的 SRE 志明看著儀表板：CPU 平均 55%，看起來還有一半空間；但 p99 latency 從 300 ms 飆到 9 秒，錯誤率超過 30%。Autoscaler 確實觸發了，新的機器在四分鐘後才開始接流量，那時使用者已經重試了好幾輪，重試又讓流量再翻一倍。更糟的是，新機器一上線就各自建立資料庫連線，把已經吃緊的資料庫連線數推到上限，結果連原本正常的機器也開始失敗。

事後 postmortem 找出好幾個問題，每一個都和「容量」有關，但沒有一個是「機器不夠多」那麼簡單：CPU 平均值掩蓋了排隊；真正的瓶頸是資料庫連線與外部金流商的每秒交易上限；autoscaling 的反應時間遠長於流量上升的時間；而沒有人知道一台 checkout 機器在 SLO 之內到底能處理多少請求。

今年（第 4 年）公司已經約 120 人，checkout 平時約 50 台、平日尖峰約 2,400 RPS。產品經理 Lisa 帶來行銷的計畫：預估雙十一（11 月 11 日 00:00）尖峰是平日的 6 倍，還會首次和三位網紅合作直播帶貨。Kevin 這次問的問題變了：「我們需要多少資源？什麼時候要準備好？如果活動當晚掉了一個機房，還撐得住嗎？」這一章要回答的就是這三個問題。

## 36.2 Capacity planning 要回答的問題

**Capacity**（容量）是「服務在滿足 SLO 的前提下，能處理的工作量」。注意這個定義的後半句：一台機器每秒能「處理」1,000 個請求，但如果其中一半要等 5 秒，對使用者來說它根本沒有處理好。容量永遠要和品質目標綁在一起講。

**Capacity planning**（容量規劃）是在需求到來之前，決定要準備多少、什麼樣的資源；**provisioning**（佈建）是真正把資源拿到手、設定好、驗證可用的過程。SRE 第 1 章把這件事拆成三個必要條件：要有一個時間跨度超過「取得資源所需時間」的 organic demand 預測；要把 inorganic demand（產品上線、行銷活動）正確納入；要定期做 load test，把「原始資源」（CPU、機器數）和「服務能力」（每秒能完成多少次結帳）對應起來。

把整個流程畫出來：

```text
 業務預測                 服務模型                      容量計算                     落地
┌────────────┐      ┌────────────────┐        ┌────────────────────┐     ┌──────────────────┐
│ 平日趨勢   │      │ 每筆訂單呼叫    │        │ 尖峰負載            │     │ quota／採購       │
│ 季節性     │ ───► │ 哪些服務、幾次  │ ─────► │ ÷ 單機 safe capacity│ ──► │ 部署、暖機        │
│ 活動倍數   │      │ （fan-out）     │        │ × (1 + headroom)    │     │ load test 驗證    │
└────────────┘      └────────────────┘        │ + failure domain    │     │ 監控 saturation   │
      ▲                     ▲                 └────────────────────┘     └────────┬─────────┘
      │                     │                          ▲                          │
      │              load test 量出單機能力 ────────────┘                          │
      └───────────────────── 實際流量回饋，修正下一次預測 ◄─────────────────────────┘
```

圖的左邊是**需求**：業務上會有多少人來、做什麼事。中間把業務單位（每分鐘訂單數）翻譯成服務單位（checkout 每秒請求、inventory 每秒查詢），再除以每台機器在 SLO 內能處理的量，加上不確定性與故障的保留。右邊是**供給**：資源從申請到能用，需要時間。最下面那條回饋線最容易被忽略：每次大活動結束後，要拿實際數字和預測比對，誤差就是下一次 headroom 的依據。

Google 在 SRE 第 18 章介紹過一個叫 Auxon 的內部工具，它代表一種思考方式的轉變，叫 **intent-based capacity planning**（以意圖為基礎的容量規劃）。最低層的需求描述是「我要在 X、Y、Z 三個叢集各要 50 個 CPU 核心」；往上一層是「我要在某個地區的任意三個叢集共 50 核」；再往上是「我要滿足這個服務在每個地區的需求，並且有 N+2 的冗餘」；最高層是「我要這個服務達到某個可靠性目標」。越往上，描述的是**為什麼**要這些資源，而不是**要哪些**資源，工具或人才能在條件改變時重新推導答案。Harbor 不需要自己寫 Auxon，但可以學它的做法：容量計畫裡的每一個數字，都要寫出它從哪個意圖推導而來。

## 36.3 Demand forecasting：預測要服務多少工作

### Organic 與 inorganic growth

**Organic growth**（自然成長）是使用者慢慢變多、使用習慣慢慢改變帶來的需求增加。它通常平滑、可以從歷史資料推估：Harbor 過去一年的平日尖峰流量大約每月成長 10%（一年約三倍），每週五晚上和每月 5 日發薪日前後特別高，農曆年前一週是年度第二高峰。

**Inorganic growth**（非自然成長）是某個特定事件造成的跳躍：雙十一、新功能上線、網紅直播、媒體報導、某個大賣家入駐。它的特徵是**歷史資料看不出來**，只能從事件本身推估，而且往往來得很突然。去年 Harbor 的事故就是用 organic 的直覺（「加倍應該夠」）去面對 inorganic 的需求。

Inorganic demand 還有一種常被忽略的來源：**系統自己的變更**。App 新版本把首頁的推薦從 1 次 API 呼叫改成 4 次、某個 client 加上了自動重試、把同步呼叫改成輪詢，這些都會讓後端負載跳一階，但從業務數字上完全看不出來。所以 launch review（第 46 章）要問「這個功能會讓哪些服務的負載增加多少」。

### 用尖峰規劃，不用平均

容量要對付的是**尖峰**，不是平均。Harbor 一天的流量曲線大致是凌晨極低、中午一個小峰、晚上九點到十一點最高，尖峰大約是全日平均的 2.5 倍。如果用每日平均算機器數，每天晚上都會不夠。

尖峰本身也要選對時間解析度。「每小時平均」會把十分鐘的高峰抹平，「每分鐘平均」會把十秒的推播衝擊抹平。雙十一午夜這類事件，真正要看的是**秒級**的尖峰：推播送出後的前一分鐘，流量可能是那個小時平均的好幾倍。規則是：**時間解析度要短於系統反應的時間**。如果你的 autoscaling 需要 4 分鐘生效，就至少要知道每分鐘的尖峰。

### 從業務單位翻譯成服務單位

行銷給的數字是「雙十一尖峰每分鐘 10,800 筆訂單」，但 checkout 團隊需要的是「checkout 每秒多少請求」，負責 inventory 資料庫的人需要的是「每秒多少寫入」。中間的橋樑是 **fan-out ratio**（扇出比）：一個業務動作會在每個服務上產生多少請求。

第一步是找對業務單位。不是每個進入結帳頁的人都會成交：有人在比價、有人在湊免運、有人付款失敗後放棄。Harbor 的歷史資料顯示，大活動時每成交一筆訂單，大約對應 10 次「結帳 session」（使用者進入結帳流程一次）。所以每分鐘 10,800 筆訂單，等於每秒 180 筆訂單、每秒 1,800 個結帳 session。第二步才是每個 session 或每筆訂單對各服務的請求：

| 業務單位 | 對各服務的請求 | 換算成 P90 尖峰 | 備註 |
|---|---|---|---|
| 每個結帳 session | checkout 約 8 次（購物車、優惠計算、地址、確認頁、送出…） | 14,400 RPS | 包含 app 輪詢付款結果 |
| 每個結帳 session | inventory 3 次讀、0.8 次寫 | 5,400 讀／s、約 1,440 寫／s | 寫入是預扣庫存，放棄結帳時再釋放 |
| 每筆訂單 | payments 1.3 次 | 約 230 TPS | 包含使用者換卡重試 |
| 每筆訂單 | notification 2 次 | 360 msg/s | 訂單成立與付款成功 |

這張表必須從真實的 tracing 或日誌量出來（第 33 章），不能用架構圖推測。Harbor 第一次量時發現 checkout 的 fan-out 是 8 而不是設計文件寫的 3，多出來的是 app 每秒輪詢付款狀態的請求。也要注意，checkout 的 14,400 RPS 正好是平日尖峰 2,400 RPS 的 6 倍，和行銷估計的倍數吻合；兩條獨立的推估路線互相印證，比只有一條可靠得多。

### 預測要有範圍

任何預測都有誤差，inorganic 事件的誤差特別大。比較好的做法是給出幾個情境，而不是一個數字：

| 情境 | 每分鐘訂單 | checkout 尖峰 RPS | 用途 |
|---|---|---|---|
| 保守（P50） | 7,000 | 約 9,300 | 成本估算 |
| 預期（P90） | 10,800 | 約 14,400 | **容量規劃的基準** |
| 極端（網紅效應超出預期） | 16,000 | 約 21,000 | 準備降級與 load shedding 方案 |

**P90 情境**的意思是「我們估計實際尖峰有 90% 的機率不會超過這個數字」。容量照 P90 準備，極端情境不靠買機器解決，而是靠第 38 章的 load shedding 與降級：先關掉推薦、延後寄信、讓排隊頁面接住超出的流量。把這三件事分開，才能避免「為了極端情境買三倍機器」或「完全沒想過極端情境」兩種錯誤。

> [!warning] 常見誤解
> 「QPS 就是容量的單位。」不一定。SRE 第 21 章特別提醒，不同請求的成本可能差很多倍：一次「查看購物車」只讀快取，一次「送出訂單」要寫三個資料庫。若雙十一的請求組成（mix）和平日不同，例如送出訂單的比例變高，同樣的 QPS 會吃掉更多資源。比較穩健的做法是直接用資源（CPU 秒、資料庫寫入數）來描述容量，或至少分開規劃讀與寫兩種請求。

## 36.4 Load test：找出 safe capacity

有了需求，下一步是知道一台機器（或一個 instance、一個 pod）能處理多少。答案只能量出來。

### 量的是曲線，不是一個點

**Load test**（負載測試，第 25 章介紹過測試類型）在這裡的目的，是畫出「負載 vs 品質」的曲線。做法是逐步加壓：每秒 50、100、150、200……個請求，每一階維持數分鐘讓系統穩定，記錄 throughput、p50／p99 latency、錯誤率，以及 CPU、記憶體、連線數、thread pool、GC 等資源指標。

```text
 p99 latency
   (ms)
  3000 ┤                                          ●
       │                                         ╱
  2000 ┤                                        ╱
       │                                      ●
  1000 ┤                                    ╱
       │                                 ●╱      ← 過了 knee，越來越陡
   500 ┼ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ●─ ─ ─ ─ ─ ─ ─ SLO 門檻
   300 ┤  ●───●───●───●───●───●───●
       └──┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───► 每台 RPS
         25  50  75 100 125 150 175 200 225 250
                                  ▲   ▲
                                  │   └─ SLO 失守點（約 200）
                                  └───── safe capacity（180）
```

曲線前半段幾乎是平的：負載加倍，latency 不變，因為機器有空閒，請求不用等。過了某個點（**knee**，膝點），latency 開始往上彎，而且越來越陡。Throughput 往往還在上升，看起來機器「還能多吃一點」，但使用者已經在等了。再往後，錯誤率開始升高，throughput 甚至反過來下降，那是第 38 章要談的過載。

**Safe capacity**（安全容量）是「在 SLO 門檻以下、而且離 knee 還有一點距離」的負載。Harbor 的 checkout 每台在約 200 RPS 時 p99 碰到 500 ms 的門檻，團隊把 safe capacity 訂在 180 RPS。這裡的 500 ms 和第 32 章 checkout SLO 的「2 秒內完成」量的不是同一件事：2 秒是使用者一次完整結帳（含呼叫 inventory、金流商與 app 輪詢）的端到端目標，500 ms 則是單一 checkout API 請求在一個 pod 上的內部門檻。一次結帳會打到 checkout 約 8 次（36.3 的 fan-out），每一跳都要遠低於 2 秒，端到端才守得住，所以容量測試用更嚴的單請求門檻。保留的 10% 是為了吸收單機差異：雲端上同型號的機器，效能也會因為硬體世代、鄰居負載（noisy neighbor）而不同。

### 找出真正的瓶頸

Load test 的第二個目的，是找出**最先耗盡的資源**。去年 Harbor 的 checkout 在 CPU 55% 時就失守，原因是每台機器的資料庫連線池只有 20 條，而每個請求平均佔用一條連線 100 ms。下一節的 Little's Law 會說明為什麼這代表每台大約只能撐 200 RPS，和 CPU 完全無關。

常見的瓶頸順序沒有固定答案，常見的候選包括：CPU、記憶體與 GC、thread 或 worker 數、連線池、檔案描述符、網路頻寬、下游服務的 quota、資料庫的鎖與寫入吞吐量。Load test 時每加一階，就要看哪個指標最先接近上限；找到之後，要決定是調大它（例如加大連線池，但要同時確認資料庫撐得住），還是接受它就是容量的上限。

### 讓 load test 像真的

Load test 最常見的問題是測得太樂觀：

- **流量組成不對**。只打「查詢商品」一個 API，忽略了昂貴的寫入。比較好的做法是從 production 日誌取樣，依真實比例重播。
- **快取太熱**。測試反覆查同一批商品，快取命中率 99%；雙十一大家搶的商品不同，命中率可能只有 80%。未命中的比例從 1% 變成 20%，打到資料庫的讀取是原來的 20 倍。
- **只測單一服務**。單台 checkout 沒問題，但 150 台一起上線，資料庫、金流商、內部 auth 服務同時被放大。單機測試量 safe capacity，系統層級的測試量整條路徑的上限。
- **Load generator 自己成了瓶頸**，或使用 **closed-loop**（收到回應才送下一個）模式。Closed-loop 產生器在系統變慢時會自動送得更少，正好掩蓋了排隊造成的延遲，這個現象叫 **coordinated omission**。要模擬「使用者不會因為你變慢就少來」，應該用 **open-loop** 模式：照固定的到達速率送請求，不管前一個回來了沒。
- **忽略依賴的限制**。Harbor 串接的外部金流商，原本的合約規定每秒最多 300 筆授權交易。這個數字不會出現在任何 CPU 圖上，卻是整個雙十一的硬上限。

> [!example] 例子
> Harbor 今年的 load test 分三層：單台 checkout 用 open-loop 產生器、依 production 流量比例重播，量出 safe capacity 180 RPS；整條 checkout 路徑在 staging 用 40 台模擬，發現 inventory 資料庫主節點的寫入在每秒 1,800 次時開始延遲；最後在活動前兩週的凌晨，對 production 送出標記為測試的合成訂單，驗證金流商調整後的 600 TPS 上限與 Harbor 自己的限流設定一致。

## 36.5 Little's Law 與排隊：為什麼 80% 已經很滿

上一節的曲線為什麼會彎？答案在排隊理論。這一節只需要兩個公式，但它們能解釋大部分「看起來還有空，卻已經很慢」的現象。

### Little's Law

**Little's Law** 說：在一個穩定的系統中，

```text
L = λ × W

L：系統中平均同時存在的工作數（in-flight 請求數、佔用中的連線數）
λ：平均到達速率（每秒請求數）
W：每個工作在系統中平均停留的時間（秒）
```

這個公式幾乎不需要任何假設，不管到達是否隨機、處理時間是否固定都成立，所以非常實用。

算例一：Harbor 的 checkout 每台承受 180 RPS，每個請求平均停留 0.15 秒，那麼任何時刻平均有 180 × 0.15 = 27 個請求正在處理。如果每個請求佔用一個 worker thread，至少需要 27 個 thread，加上波動，設 64 個比較安全。

算例二（去年的事故）：每個請求平均佔用資料庫連線 0.1 秒，連線池 20 條。20 = λ × 0.1，所以每台最多約 200 RPS。雙十一時資料庫變慢，每次查詢從 0.1 秒變成 0.4 秒，同一個連線池只撐得住 50 RPS，請求開始在連線池前面排隊，latency 爆炸，而 CPU 因為大家都在等連線，反而只有 55%。

算例三反過來用：如果觀察到某個 queue 平均有 600 個請求、每秒進來 200 個，那每個請求平均在裡面待 3 秒。Little's Law 讓你從容易量的兩個數字，推出難量的第三個。

### Utilization 與 latency 的非線性

**Utilization**（使用率，ρ）是到達速率除以處理能力：ρ = λ / μ。一台每秒能處理 50 個請求的機器，每秒進來 40 個，ρ = 80%。

最簡單的排隊模型 M/M/1（隨機到達、隨機處理時間、單一 worker）有一個漂亮的結果：

```text
平均停留時間 W = S / (1 − ρ)        S：單一請求的平均處理時間

ρ = 50%  → W = 2 S
ρ = 80%  → W = 5 S
ρ = 90%  → W = 10 S
ρ = 95%  → W = 20 S
```

假設 S = 20 ms。使用率 50% 時平均 40 ms，80% 時 100 ms，90% 時 200 ms，95% 時 400 ms。從 50% 到 80%，使用率只增加了六成，latency 卻變成 2.5 倍；從 90% 到 95%，使用率只多了 5 個百分點，latency 又翻倍。這就是曲線會「彎」的原因：**使用率越接近 100%，每多一點負載造成的等待越大**，在 100% 時理論上是無限大。

直覺可以這樣想：請求是隨機到達的，有時候一秒內來 30 個，有時候來 60 個。使用率 50% 時，偶爾的高峰很快就被空閒時間消化；使用率 95% 時幾乎沒有空閒時間，一個小高峰造成的隊伍要很久才排得完，而在排完之前下一個高峰又來了。

更一般的近似公式（Kingman's formula）告訴我們等待時間大約和兩件事成正比：ρ / (1 − ρ)，以及到達與處理時間的**變異程度**。這帶出兩個實務結論。第一，請求成本差異越大（有的 5 ms、有的 2 秒），越不能把使用率拉高；把慢的請求分到另一個 pool，常常比加機器更有效。第二，流量越突發（推播、整點搶購），同樣的平均使用率下排隊越嚴重。

### 為什麼大 pool 可以跑得比較熱

M/M/1 很悲觀，因為只有一個 worker。真實服務有很多 worker 共用一條 queue（一台機器有多個 thread、一個服務有多台機器），排隊情況會好很多：某個 worker 在處理慢請求時，其他 worker 可以接手。36.12 的模擬會顯示，在 90% 使用率下，8 個 worker 共用一條 queue 的 p99 只有單一 worker 的大約六分之一。這是「大型服務可以安全地跑在比較高的使用率」的原因之一，也是 load balancing 要盡量把請求平均分配、避免某些 worker 忙死某些閒著的原因（第 37 章）。

> [!warning] 常見誤解
> 「CPU 平均 55%，所以還有將近一半的容量。」錯在三個地方。第一，一分鐘的平均值會掩蓋秒級的尖峰。第二，平均是所有機器的平均，負載不均時某些機器早就 95%。第三，CPU 可能根本不是瓶頸，連線池、thread、資料庫鎖都可能先滿。判斷容量要看 saturation 指標（queue 長度、等待時間、連線池使用率），而不是只看 CPU（第 33 章的 USE 方法）。

## 36.6 Redundancy：N+1、N+2 與 failure domain

到目前為止算的都是「一切正常」時需要多少。但機器會壞、會被拿去升級、整個 zone 會斷電。容量規劃必須回答「壞掉一部分之後還夠不夠」。

### N+1 與 N+2

假設尖峰需要 N 台才能守住 SLO。**N+1** 代表多準備一台，任何一台壞掉或被拿去維護時仍然夠用。**N+2** 代表多準備兩台，能同時承受一次**計畫中的停機**（例如滾動升級時一台正在重啟）和一次**非計畫的故障**。N+2 比 N+1 多的那一台，就是為了「維護時剛好又壞一台」這種常見的組合。

這裡的「台」不一定是機器，而是**一起失敗的單位**，稱為 **failure domain**（故障域）：同一台實體主機上的 VM、同一個機架、同一個 zone（雲端的可用區，是一個或一組獨立供電、供網的資料中心）、同一個 region。容量的冗餘要以你打算承受的 failure domain 為單位計算。

### 以 zone 為單位計算

Harbor 的 checkout 部署在同一個 region 的 3 個 zone。如果要求「失去任何一個 zone 仍能守住 SLO」，剩下的 2 個 zone 必須能承擔全部尖峰：

```text
需要的總容量 = 尖峰需求 × zone 數 / (zone 數 − 1)

3 個 zone：尖峰 × 3/2 = 150%
4 個 zone：尖峰 × 4/3 ≈ 133%
2 個 zone：尖峰 × 2/1 = 200%
```

這說明了為什麼很多系統偏好 3 個以上的 zone：2 個 zone 時，為了承受一個 zone 的失效，平常只能用到一半；zone 越多，冗餘的比例越低。代價是部署與資料同步變得更複雜。

```text
 正常時（3 zone，各 50 台，每台約 96 RPS）
 ┌──────────┐ ┌──────────┐ ┌──────────┐
 │ zone A   │ │ zone B   │ │ zone C   │      總需求 14,400 RPS
 │ ████░░░░ │ │ ████░░░░ │ │ ████░░░░ │      每台負載 ≈ safe capacity 的 53%
 └──────────┘ └──────────┘ └──────────┘

 zone C 失效後（剩 100 台，每台 144 RPS）
 ┌──────────┐ ┌──────────┐ ┌──────────┐
 │ zone A   │ │ zone B   │ │  ✕ ✕ ✕   │      總需求不變
 │ ██████░░ │ │ ██████░░ │ │          │      每台負載 ≈ safe capacity 的 80%
 └──────────┘ └──────────┘ └──────────┘
```

zone 失效時，原本那三分之一的流量會被 load balancer 轉到剩下的機器上（第 37 章）。圖中每台的負載從 safe capacity 的 53% 上升到 80%，仍然在 SLO 之內。這裡還有一個容易漏掉的前提：**流量轉移需要時間**，健康檢查要先發現失效、client 要重新連線，這段時間的錯誤也要算進 error budget。

### 不只是 stateless 服務

冗餘最容易做的是 stateless 的服務（不保存狀態，任何一台都能處理任何請求），加機器就好。真正難的是有狀態的部分：資料庫主節點失效時，replica 升級需要時間，而且升級後的新主節點是否有足夠的容量？快取叢集失去一個 zone，命中率下降，打到資料庫的請求可能突然變成兩倍。容量計畫要逐一列出這些「失效之後的二次效應」，不能只算 web tier 的台數。

## 36.7 Headroom：把不確定性換算成機器

**Headroom**（餘裕）是在預測尖峰之上額外保留的容量。它和 N+k 冗餘保護的是不同的東西，分清楚才不會重複計算，也不會漏算：

| 保留項目 | 保護什麼 | Harbor 的量化方式 |
|---|---|---|
| Safe capacity 的折扣 | 單機效能差異、量測誤差 | 失守點 200 RPS → 規劃用 180 RPS |
| Headroom | 預測誤差、秒級突發、負載不均、擴容延遲 | 過去三次大活動，實際尖峰比預測高 8%–22%，取 25% |
| N+k／failure domain | 機器、zone 故障與維護 | 失去 1 個 zone 仍可服務 |
| Load shedding 與降級 | 超出 P90 的極端情境 | 不買機器，靠第 38 章的機制 |

Headroom 的大小應該來自資料，而不是感覺。最好的來源是**過去預測與實際的差距**：如果團隊每次大活動都低估 20%，headroom 至少要 20%，而且要同時改進預測。其次是**秒級尖峰與分鐘平均的比值**，以及**負載不均的程度**：如果 load balancer 讓最忙的機器比平均高 15%，規劃就要以最忙的那台為準。

把三層疊起來就是 Harbor checkout 的計算：

```text
P90 尖峰需求          14,400 RPS
× (1 + 25% headroom) = 18,000 RPS
÷ safe capacity 180   = 100 台（在全部 zone 都健康時就需要）
× 3/2（可失去 1 zone）= 150 台，每個 zone 50 台
```

一個常見的疑問是：這樣疊下去，正常時每台只跑到 safe capacity 的 53%，是不是太浪費？答案取決於你在付什麼保險。如果 Harbor 只想在「預測準確、所有 zone 健康」時撐住，14,400 ÷ 180 = 80 台就夠；要再吸收 25% 的預測誤差，需要 100 台；如果還要在「預測低估 25% 而且同時掉一個 zone」時撐住，就需要 150 台。這個決定應該由產品、工程與財務一起做，並寫進容量計畫，而不是由某個工程師默默多開或少開。另一個常見做法是承認兩個壞事件同時發生的機率較低，例如只在「預測尖峰、失去一個 zone」（80 × 3/2 = 120 台）與「預測加 headroom、所有 zone 健康」（100 台）兩個情境中取較大值，也就是 120 台。重點是**每一層保留都要能說出它在保護哪一種風險**。

## 36.8 Provisioning：lead time、quota 與暖機

算出要 150 台之後，下一個問題是：它們什麼時候能真正接流量？

### 每種資源的 lead time 不同

**Lead time**（前置時間）是從決定要某個資源，到它能用的時間。不同資源差了好幾個數量級：

| 資源 | 典型 lead time | Harbor 的例子 |
|---|---|---|
| 在已有節點上多開 container | 秒到分鐘 | checkout pod 擴容 |
| 新的 VM 或節點 | 分鐘 | Kubernetes 叢集加節點 |
| 雲端帳號的 quota 調高 | 數天到數週，需要申請 | 某種機型在該 region 的上限 |
| 預留或承諾用量的採購 | 數週，涉及財務流程 | 年度 reserved capacity |
| 資料庫重新分片、換大機型 | 數週，需要演練與遷移 | inventory 主節點升級 |
| 外部供應商的上限 | 數週到數月，需要談合約 | 金流商 300 TPS 提高到 600 TPS |
| 自建機房的硬體 | 數月 | Harbor 沒有，但大公司常見 |

**容量計畫的時程必須以最長的 lead time 為起點倒推**。去年 Harbor 在活動前一週才開始準備，那時唯一還來得及做的事就是加 container，而真正的瓶頸（資料庫與金流商）都需要數週以上。

雲端也不是無限的。帳號有 **quota**（配額上限），某個 region 的某種機型在需求高峰時可能暫時沒有庫存，這時申請新機器會直接失敗。所以大活動前除了確認 quota，常見的做法是提前幾天把機器開好，或使用雲端提供的容量預留機制，而不是期待當晚隨時都能拿到。

### 開好不等於能用

一台新機器從開機到能穩定服務，中間還有好幾步：拉取 container image、啟動程式、JIT 編譯與 class loading（Java 這類語言前幾分鐘特別慢）、建立資料庫與下游的連線池、本地快取暖機、通過 load balancer 的健康檢查並被加入輪替。SRE 第 1 章也強調，新增容量通常牽涉設定檔、load balancer、網路的修改，因此**provisioning 本身就是一種變更**，要和其他變更一樣漸進、可觀測、可回復（第 35 章），而且要驗證新容量真的能正確處理請求。

Harbor 量過：checkout 的新 pod 從建立到能以 safe capacity 服務，需要大約 4 分鐘，前 90 秒只能以一半效能運作。這 4 分鐘就是下一節 autoscaling 的關鍵限制。

### 雙十一的時程

Harbor 今年的時程是從活動日往回推：

```text
T−90 天  行銷給初版預測 → SRE 轉成各服務需求，找出 lead time 最長的項目
T−75 天  向金流商提出 TPS 上限調整；開始 inventory 資料庫升級的演練
T−60 天  申請雲端 quota；確認各 region 機型供應
T−30 天  系統層級 load test（staging）；根據結果修正容量計畫
T−14 天  production 合成訂單測試；容量計畫凍結；非必要變更開始收斂
T−3 天   預先擴容到活動規模，觀察穩定性與成本
T−0      war room；即時監控 saturation；load shedding 開關待命
T+3 天   縮回平日規模
T+14 天  預測 vs 實際的檢討，更新 headroom 與 fan-out 數據
```

這張時程的重點不是每個日期，而是兩個原則：**最慢的資源最先動**，**活動前留一段只觀察不改動的時間**。

## 36.9 Autoscaling 的能與不能

### 它怎麼運作

**Autoscaling**（自動擴縮）是一個控制迴路（第 2 章）：定期量一個指標、和目標比較、調整台數。最常見的是 **target tracking**（目標追蹤）。Kubernetes 的 Horizontal Pod Autoscaler 用的公式是：

```text
期望台數 = ceil( 目前台數 × 目前指標值 / 目標指標值 )

例：目前 40 台，平均 CPU 90%，目標 60%
    期望台數 = ceil(40 × 90 / 60) = 60 台
```

對於平滑、可預期的 organic 流量變化（白天變多、半夜變少），autoscaling 非常好用：它省下了半夜閒置的成本，也省下了人工調整的 toil（第 31 章）。

### 它的限制

Autoscaling 在以下情況靠不住，而這些情況正好是大活動最常遇到的：

**反應時間長於流量上升時間。** 從流量上升到新容量可用，要經過：指標收集與聚合（常見 15 秒到 1 分鐘）、autoscaler 的判斷週期、建立新機器、暖機。Harbor 加起來約 4–5 分鐘。午夜推播讓流量在 40 秒內從每秒 2,000 變成 11,000，超過五倍，autoscaling 只能在事故中途趕到。36.12 的模擬會量化這段落差。

**看錯指標。** 只看 CPU 的 autoscaler，在瓶頸是連線池或下游時完全沒反應；更糟的是，請求都卡在等待時 CPU 反而下降，autoscaler 可能判斷「負載很低」而**縮減**台數。比較好的指標是接近使用者體驗或真正瓶頸的那一個：in-flight 請求數、queue 長度、每台 RPS。

**把壓力推給下游。** Stateless 的 checkout 可以擴容，但它依賴的資料庫、金流商不能自動變大。每多一台 checkout，就多 20 條資料庫連線。去年 Harbor 的 autoscaler 正是把資料庫推到連線上限的推手。所以 autoscaling 一定要設**上限**，而上限要根據下游的容量來算。

**不健康的機器扭曲訊號。** 一台卡住的機器 CPU 很低、一台在無窮重試的機器 CPU 很高，兩者都會讓平均值失真。SRE Workbook 第 11 章提醒，若把還在啟動或已經不服務的 instance 也算進平均，autoscaling 可能該擴不擴；比較好的做法是用 load balancer 看到的容量指標，並等新 instance 健康後才納入計算。對有狀態系統也要小心：如果 session 綁定在特定 backend，加機器不一定能分擔已經過載的那幾台。

**震盪。** 擴容後指標下降、立刻縮容、指標又上升，台數來回擺盪。對策是不對稱的設定：擴容要快、縮容要慢。Kubernetes 預設在縮容時有 5 分鐘的 stabilization window（在這段時間內取最大的建議值），就是為了避免這種情況。

### 正確的組合

可靠的做法是把三種機制疊在一起，各自負責不同時間尺度：

| 機制 | 時間尺度 | 負責什麼 |
|---|---|---|
| 容量規劃與預先擴容 | 天到月 | 已知的大事件、底線容量、下游與外部上限 |
| Autoscaling（有上下限） | 分鐘到小時 | 日常的平滑變化、預測的小誤差 |
| Load shedding 與降級（第 38 章） | 毫秒到秒 | 擴容還沒趕到、或超出所有規劃的瞬間 |

Autoscaling 不是容量規劃的替代品，而是它的一部分：你仍然要規劃上限、quota、下游能力，以及 autoscaler 失效時（例如它依賴的 metrics 系統在尖峰時也掛了）要怎麼手動操作。WB 第 11 章也建議保留**手動覆寫與關閉 autoscaling 的開關**。

## 36.10 成本與容量

容量直接等於錢。150 台 checkout 跑一個月，和平時的 50 台跑一個月、只在活動前後幾天開到 150 台，成本差了好幾倍。容量規劃的另一半責任，是讓這筆錢花得有道理。

**用單位成本溝通。** 「checkout 每月雲端費用 X 元」很難判斷好壞；「每一千筆訂單的基礎設施成本」可以跨月比較，也可以和每筆訂單的毛利比較。單位成本上升，代表效率變差（可能是某次變更讓每個請求變慢了），值得調查。

**Headroom 是保險費。** 判斷保險值不值得買，要比較保費和損失。假設 Harbor 雙十一尖峰每分鐘成交金額很高，一次 20 分鐘的 checkout 中斷，損失的不只是那 20 分鐘的訂單，還有使用者對平台的信任。相比之下，多開三天的機器費用通常小得多。反過來，一個內部報表服務沒有必要準備 N+2 和 25% headroom。不同服務的 SLO 不同（第 32 章），容量的保險程度也應該不同。

**分開「底線」與「尖峰」。** 長期穩定需要的容量，適合用預留或長期承諾的方式取得，單價較低；活動期間的短期尖峰，用按需（on-demand）的資源；可以被中斷的批次工作，用便宜但可能被收回的資源（spot／preemptible）。注意最後一類**不能**用來承擔 SLO 關鍵的尖峰，因為在大家都需要機器的時候，它最可能被收回。

**效率改善也是容量。** 把一個熱門 API 的資料庫查詢從 3 次減少到 1 次，等於免費多出一大塊容量。每次容量檢討都應該問：最貴的 5 個請求類型是哪些？有沒有便宜的優化？Profiling（第 33 章）在這裡比加機器更有槓桿。

**定期檢討閒置。** 活動結束後沒人縮回去的機器、早就沒流量卻還開著的服務，是雲端成本最常見的浪費。Harbor 在容量計畫裡寫明每項預先擴容的「縮回日期」與負責人。

## 36.11 Harbor 雙十一容量計畫

把前面的方法整理成一份文件，就是 Harbor 今年的雙十一容量計畫。它和第 32 章的 SLO 文件一樣放在 repository 裡，經過 review，活動後再更新。節錄如下：

| 服務／資源 | 意圖（為什麼） | P90 尖峰需求 | 單位 safe capacity | 規劃量 | 最長 lead time | 超出時的動作 | Owner |
|---|---|---|---|---|---|---|---|
| checkout pods | 守住 checkout SLO，可失去 1 zone | 14,400 RPS | 180 RPS／pod | 150 pods（3 × 50） | 4 分鐘暖機 | 排隊頁面、關閉推薦 | 美華 |
| inventory DB 主節點 | 寫入延遲 < 50 ms | 約 1,440 writes/s | 升級後約 2,600 writes/s | 1 主 2 replica，換大機型 | 6 週（演練＋遷移） | 庫存預扣改非同步 | checkout 團隊（阿哲）＋platform |
| 金流商授權 | 合約上限 | 約 230 TPS（P90）；極端約 350 TPS | 合約 300 TPS → 調整為 600 TPS | 調整合約 | 10 週 | 付款排隊、限制單一使用者重試 | Lisa＋志明 |
| notification 寄送 | 訂單通知 5 分鐘內送達 | 360 msg/s | queue 消化 600 msg/s | 現有規模 | — | 延後非交易類通知 | seller 團隊（思妤） |
| AI 客服 agent | 客服對話 SLO，成本上限 | 平日 4 倍 | 受模型 API 速率與預算限制 | 模型 API 速率上限調高、每日成本上限 | 4 週 | 轉人工排隊、只保留查訂單功能 | Lisa＋客服主管 |

這張表有幾個值得注意的地方。第一欄之後緊接著是「意圖」，讓每個數字都能追溯到一個 SLO 或合約；之後若需求改變，可以重新推導。金流商一列在原合約下，P90 需求已經用掉上限的近八成，極端情境更會直接超過；它是整條路徑**唯一無法臨時調整**的資源，所以提早十週去談。每一列都有「超出時的動作」，因為容量計畫一定會在某個地方被現實超越，團隊需要事先知道那時要犧牲什麼。最後一列的 AI 客服是新面孔，36.14 會說明它的容量為什麼要用不同的單位來算。

## 36.12 動手寫：排隊、容量與 autoscaling 模擬

下面的程式做三件事：用模擬驗證 utilization 與 latency 的非線性；把 36.7 的容量計算寫成函式；模擬午夜流量跳升時，只靠 autoscaling 和預先擴容的差別。

```python
import heapq
import math
import random


# ── 1. 排隊模擬：utilization 與 latency 的非線性 ─────────────────────
def simulate_queue(utilization, servers=1, service_ms=20.0, n=200_000, seed=7):
    """M/M/c 佇列：Poisson 到達、指數分佈服務時間、c 個 worker 共用一條 queue。"""
    rng = random.Random(seed)
    arrival_rate = utilization * servers / service_ms      # 每 ms 到達幾個請求
    free_at = [0.0] * servers                              # 每個 worker 何時有空
    heapq.heapify(free_at)
    t, latencies = 0.0, []
    for _ in range(n):
        t += rng.expovariate(arrival_rate)                 # 下一個請求抵達
        start = max(t, heapq.heappop(free_at))             # 等到有 worker 空出來
        done = start + rng.expovariate(1 / service_ms)
        heapq.heappush(free_at, done)
        latencies.append(done - t)                         # 排隊 + 處理
    latencies.sort()
    return sum(latencies) / n, latencies[int(n * 0.99)]


def averaged(utilization, servers, seeds=5):
    """高使用率時單次模擬的 p99 雜訊很大，取 5 個 seed 的平均。"""
    runs = [simulate_queue(utilization, servers, seed=s) for s in range(seeds)]
    return sum(m for m, _ in runs) / seeds, sum(p for _, p in runs) / seeds


def theory_p99(utilization, servers, service_ms=20.0):
    """M/M/c 停留時間的理論 p99：Erlang C 算出要排隊的機率，再用二分搜尋解尾端機率 = 1%。"""
    mu = 1 / service_ms
    a = utilization * servers                              # offered load（Erlang）
    top = a ** servers / math.factorial(servers) / (1 - utilization)
    wait_prob = top / (sum(a ** k / math.factorial(k) for k in range(servers)) + top)
    drain = servers * mu * (1 - utilization)               # 排隊時間的指數分佈速率

    def tail(t):                                           # P(停留時間 > t)
        if abs(drain - mu) < 1e-12:
            queued = (1 + mu * t) * math.exp(-mu * t)
        else:
            queued = (drain * math.exp(-mu * t) - mu * math.exp(-drain * t)) / (drain - mu)
        return (1 - wait_prob) * math.exp(-mu * t) + wait_prob * queued

    lo, hi = 0.0, 1e6
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if tail(mid) > 0.01 else (lo, mid)
    return lo


print("            ── 單一 worker（c=1）──────────────    ── 8 個 worker（c=8）──")
print("utilization  理論平均  模擬平均  理論p99  模擬p99    理論p99  模擬p99")
for rho in (0.5, 0.7, 0.8, 0.9, 0.95):
    mean1, p99_1 = averaged(rho, servers=1)
    _, p99_8 = averaged(rho, servers=8)
    print(f"   {rho:4.0%}    {20.0 / (1 - rho):6.0f} ms {mean1:6.0f} ms "
          f"{theory_p99(rho, 1):6.0f} ms {p99_1:6.0f} ms  "
          f"{theory_p99(rho, 8):6.0f} ms {p99_8:6.0f} ms")


# ── 2. 容量規劃：從需求到要開幾台 ─────────────────────────────────
def plan(peak_rps, safe_rps_per_instance, headroom, zones, lose_zones=1):
    with_headroom = peak_rps * (1 + headroom)
    needed = math.ceil(with_headroom / safe_rps_per_instance)
    surviving = zones - lose_zones
    per_zone = math.ceil(needed / surviving)               # 剩下的 zone 要扛全部
    return needed, per_zone, per_zone * zones


print()
peak = 2_400 * 6            # 平日尖峰 2,400 RPS × 雙十一倍數 6
needed, per_zone, total = plan(peak, safe_rps_per_instance=180, headroom=0.25, zones=3)
print(f"雙十一預測尖峰 {peak:,} RPS，加 25% headroom 需 {needed} 台（以 safe capacity 180 RPS 計）")
print(f"三個 zone、要能失去一個：每 zone {per_zone} 台，共 {total} 台")
print(f"正常時每台負載 {peak / total:.0f} RPS，約 safe capacity 的 {peak / total / 180:.0%}")


# ── 3. Autoscaling 追不上午夜的階梯式流量 ───────────────────────────
def midnight(start_instances, lag_s=240, step_s=30, verbose=False):
    """模擬 23:55–00:10。午夜（t=300 s）流量從 4,000 跳到 14,400 RPS。"""
    instances, pending, overflow = start_instances, [], 0
    for t in range(0, 900, step_s):
        demand = 4_000 if t < 300 else 14_400
        instances += sum(n for when, n in pending if when == t)   # 新機器開始接流量
        pending = [(w, n) for w, n in pending if w != t]
        capacity = instances * 180                                # safe capacity
        overflow += max(0, demand - capacity) * step_s
        utilization = demand / capacity
        if verbose and t % 120 == 0:
            print(f"  t={t:>3}s  需求 {demand:>6,}  台數 {instances:>3}  使用率 {utilization:5.0%}")
        if utilization > 0.6 and not pending:                     # target tracking：目標 60%
            want = math.ceil(instances * utilization / 0.6)
            pending.append((t + lag_s, want - instances))
    return overflow


print()
print("只靠 autoscaling（從平時的 50 台開始，擴容要 4 分鐘才生效）：")
reactive = midnight(50, verbose=True)
print(f"  超出 safe capacity 的請求約 {reactive:,} 個")
print(f"預先擴容到 150 台：超出 safe capacity 的請求 {midnight(150):,} 個")
```

執行結果：

```text
            ── 單一 worker（c=1）──────────────    ── 8 個 worker（c=8）──
utilization  理論平均  模擬平均  理論p99  模擬p99    理論p99  模擬p99
    50%        40 ms     40 ms    184 ms    184 ms      92 ms     92 ms
    70%        67 ms     66 ms    307 ms    305 ms      96 ms     95 ms
    80%       100 ms     99 ms    461 ms    453 ms     103 ms    103 ms
    90%       200 ms    197 ms    921 ms    909 ms     142 ms    141 ms
    95%       400 ms    399 ms   1842 ms   1836 ms     247 ms    249 ms

雙十一預測尖峰 14,400 RPS，加 25% headroom 需 100 台（以 safe capacity 180 RPS 計）
三個 zone、要能失去一個：每 zone 50 台，共 150 台
正常時每台負載 96 RPS，約 safe capacity 的 53%

只靠 autoscaling（從平時的 50 台開始，擴容要 4 分鐘才生效）：
  t=  0s  需求  4,000  台數  50  使用率   44%
  t=120s  需求  4,000  台數  50  使用率   44%
  t=240s  需求  4,000  台數  50  使用率   44%
  t=360s  需求 14,400  台數  50  使用率  160%
  t=480s  需求 14,400  台數  50  使用率  160%
  t=600s  需求 14,400  台數 134  使用率   60%
  t=720s  需求 14,400  台數 134  使用率   60%
  t=840s  需求 14,400  台數 134  使用率   60%
  超出 safe capacity 的請求約 1,296,000 個
預先擴容到 150 台：超出 safe capacity 的請求 0 個
```

逐段解讀：

1. **排隊模擬**。`simulate_queue` 是一個極簡的離散事件模擬：請求以隨機間隔抵達，找最早有空的 worker，處理時間也是隨機的。單一 worker 的模擬平均值和公式 S / (1 − ρ) 幾乎一致，證明 36.5 的表格不是紙上談兵。高使用率時單次模擬的 p99 雜訊很大（同樣 20 萬筆，換一個 seed，95% 的 p99 可以差到幾百 ms），所以程式取 5 個 seed 的平均，並把理論值並列：M/M/1 的停留時間是指數分佈，p99 恰好是平均的 ln 100 ≈ 4.6 倍，模擬與理論相差不到 2%。這也說明了 p99 那一欄真正的教訓：在 M/M/1 下，平均與 p99 **一起**按 1 / (1 − ρ) 放大，從 80% 到 90% 兩者都翻倍（p99 從約 460 ms 到約 920 ms），到 95% 再翻倍，p99 來到約 1.8 秒。尾端並沒有比平均惡化得「更快」，但它的絕對值大得多：SLO 通常訂在 p99 或門檻比例上（第 32 章），平均只有 200 ms 時，p99 已經接近 1 秒，這才是「80% 已經很滿」的真正原因。真實服務的處理時間變異往往比指數分佈更大，尾端會更差（Kingman 公式中的變異項）。
2. **Pooling 的效果**。最後兩欄是 8 個 worker 共用一條 queue。在 90% 使用率下，p99 理論值約 142 ms（模擬 141 ms），大約是單一 worker（約 920 ms）的六分之一；而且使用率從 80% 升到 90%，p99 只從約 103 ms 增加到約 142 ms，遠比單一 worker 平緩。這對應真實系統的兩個設計：一台機器用多個 worker 共用 queue；以及 load balancer 盡量讓請求去有空的機器（第 37 章），讓整個 fleet 的行為接近「一條大 queue」。
3. **容量計算**。`plan` 依序套用 headroom、safe capacity、failure domain，結果和 36.7 手算的 150 台一致。最後一行提醒：正常情況下每台只用 safe capacity 的一半左右，這是刻意買的保險，不是浪費，前提是每一層保留都說得出理由。
4. **Autoscaling 的落差**。`midnight` 用 30 秒一步模擬 target tracking：使用率超過 60% 就算出期望台數，4 分鐘後生效。從平時的 50 台出發，午夜後的 4 分鐘裡，需求是 safe capacity 的 1.6 倍，累積約 130 萬個請求落在 safe capacity 之外，它們不一定全部失敗，但會排隊、變慢，並誘發重試（第 39 章）。注意 autoscaler 最後停在 134 台，少於容量計畫的 150 台，因為它只看當下的使用率，不知道「要能失去一個 zone」這個意圖。
5. **模擬參數是假設**。服務時間 20 ms、午夜前 4,000 RPS、4 分鐘生效、60% 目標使用率、流量瞬間跳升且沒有縮容，都是為了說明機制而選的假設值，不是 Harbor 的量測數據；換成你自己的數字，結論的方向不變，但量級會不同。實際的雙十一當晚，11/10 22:00 流量就已經是平日的 4 倍（約 9,600 RPS，第 39 章）；若用這個數字起跳，50 台（safe capacity 約 9,000 RPS）在午夜之前就已超載，「只靠 autoscaling」的結論只會更糟。
6. **與真實系統的對應**。真實的 autoscaler 有更多細節：指標有延遲與平滑、有最小與最大台數、有縮容冷卻時間、新機器有暖機期。但結構相同：**偵測 → 決策 → 等待資源 → 生效**，任何長於流量變化的迴路都追不上。這也是為什麼已知的大事件要靠預先擴容，而不是靠反應。

## 36.13 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| 用 CPU 平均判斷容量 | 瓶頸不是 CPU，或平均值掩蓋了尖峰與不均 | Harbor 去年 CPU 55% 時資料庫連線池已滿 | Load test 找出最先耗盡的資源；看 saturation 與 queue 指標 |
| 用平均流量或每小時尖峰規劃 | 秒級突發超過容量 | 推播造成 40 秒內五倍以上的流量 | 規劃的時間解析度要短於擴容反應時間 |
| 只依賴 autoscaling | 反應時間長於流量上升；把壓力推給下游 | 新 pod 四分鐘後才上線，又打爆資料庫連線 | 已知事件預先擴容；autoscaler 設上限並以下游容量計算 |
| Load test 不像 production | 高估容量 | 快取全熱、只測讀取、closed-loop 產生器 | 依真實比例重播、測冷快取、用 open-loop；系統層級驗證 |
| 只替 stateless tier 規劃冗餘 | 有狀態元件失效時二次效應壓垮系統 | 快取失去一個 zone，資料庫讀取變兩倍 | 逐一列出失效情境與二次效應，納入 load test |
| 容量計畫只有數字沒有意圖 | 條件改變時沒人知道怎麼重算 | 金流商換約，沒人知道 600 TPS 是從哪個需求推來的 | 每個數字寫出它對應的 SLO、合約或 failure domain |
| 為極端情境買足機器 | 成本長期過高，且仍可能被更極端的情況超過 | 照網紅爆紅情境準備三倍機器，平日閒置 | 容量照 P90，極端情境用 load shedding 與降級 |
| 活動後不縮回 | 成本浪費、單位成本上升 | 雙十一的 150 台在一月還開著 | 計畫中寫明縮回日期與負責人，追蹤單位成本 |

## 36.14 AI 時代：什麼變了？

**第一，AI 功能本身是新的、很難預測的容量負載。** Harbor 的 AI 客服 agent 和一般 API 不一樣。一次對話可能呼叫模型好幾次，每次的成本取決於 prompt 與回應的 token 數；agent 若決定查三張訂單、讀兩份退款規則，就會多出五次 tool call。結果是**請求成本的變異極大**：一次「查物流」的對話和一次「多筆訂單退款爭議」的對話，資源消耗可能差十倍以上。36.5 的 Kingman 公式告訴我們，變異越大，越不能把使用率拉高。

所以 AI 功能的容量要用不同的單位規劃：每秒 token 數（輸入與輸出分開）、同時進行中的對話數（Little's Law：每秒新對話 × 平均對話時長）、每次對話的 tool call 分佈、首個 token 的延遲（time to first token）、以及模型 API 的速率上限（不論是外部供應商給的 quota，還是自建 GPU 叢集的吞吐量）。GPU 這類資源的 lead time 往往比一般 CPU 長得多，更需要提早規劃。

**第二，成本也是容量的一個維度。** 傳統服務被大量請求打到時，最糟是變慢或失敗；AI 服務被打到時，還可能燒掉大量預算。惡意或異常的使用（例如某個爬蟲反覆送超長的訊息）會變成 **denial of wallet**：服務沒有掛，但帳單爆了。容量計畫要包含每個使用者、每個租戶、每次對話的 token 與步數上限，以及每日的成本上限，而且這些限制要由確定性的程式碼執行，不能交給模型自己判斷。

**第三，AI 能幫忙做容量分析，但不能取代驗證。**

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 從歷史流量與活動紀錄產生多個預測情境，並標出季節性與異常點 | 預測必須附上資料區間與不確定性；選哪個情境作為規劃基準（例如 P90）由服務 owner 與產品決定 |
| 從 tracing 資料計算各服務的 fan-out ratio，找出和設計文件不一致的地方 | Fan-out 數字要能用可重現的查詢驗證，不能只採信摘要 |
| 讀 load test 結果，指出 knee 的位置與最先耗盡的資源 | Safe capacity 的最終數字由人根據 SLO 與風險決定，並在 production 驗證 |
| 草擬容量計畫文件、時程與「超出時的動作」清單 | 外部合約、quota 申請、採購承諾需要人簽核 |
| AI 維運 agent 在預先核准的範圍內調整 autoscaling 參數或執行預先擴容 | Agent 只能在 min／max 範圍內動作，所有變更留審計紀錄，並保留人工覆寫與停用開關 |

> [!ai] AI 提醒
> 讓 AI agent 直接決定「現在要開幾台」很誘人，但它和 autoscaler 有同樣的根本限制：資源有 lead time，而且下游有上限。一個沒有上限的 agent 可能為了壓低 latency 不斷擴容，把資料庫連線打滿，或在幾小時內花掉一個月的預算。給 agent 的權限要比給 autoscaler 更窄，而不是更寬：明確的上下限、單次變更幅度、成本上限，以及超出範圍時必須找人。

## 36.15 專家怎麼想

- **「瓶頸是什麼？」比「要幾台？」先問。** 資深 SRE 看到容量問題，第一件事是找出最先耗盡的資源。如果瓶頸是資料庫或外部 quota，加多少 web 機器都沒用，甚至會更糟。
- **用 SLO 定義容量，而不是用崩潰點。** 「這台機器每秒能處理多少」沒有意義，「在 p99 低於 500 ms 時能處理多少」才有。容量數字若沒有附帶品質條件，專家會直接退回。
- **從最長的 lead time 倒推。** 時程表的第一行是最慢的那件事：外部合約、資料庫遷移、quota。等到一週前才開始的容量計畫，只剩「多開 container」這一個選項。
- **每一層保留都要說得出在保護什麼。** Safe capacity 的折扣、headroom、N+k、load shedding 分別對應不同風險。說不出理由的保留會被當成浪費砍掉，重複計算的保留則真的是浪費。
- **事後一定比對預測與實際。** 預測誤差是下一次 headroom 最好的依據。沒有回饋的容量計畫，每年都在重新猜。
- **不要相信沒有在 production 驗證過的容量。** Staging 的 load test 告訴你機器的能力，production 的合成流量或活動前的預演才告訴你整條路徑的能力。

## 36.16 動手練習

1. 修改 36.12 的 `simulate_queue`，讓服務時間不是指數分佈，而是「95% 的請求 10 ms、5% 的請求 400 ms」（平均約 29.5 ms）。在相同使用率下比較 p99，驗證「請求成本變異越大，越不能把使用率拉高」。再試著把慢請求分到另一組 worker，觀察快請求的 p99 有什麼變化。
2. 修改 `midnight`：加入 autoscaler 的最大台數限制（例如 120 台），並在午夜前 5 分鐘改用「排程擴容」先加到 100 台。比較三種設定下超出 safe capacity 的請求數。
3. 用 Little's Law 計算：Harbor 的 checkout 每台 180 RPS，每個請求佔用資料庫連線 30 ms，連線池需要多大？若資料庫變慢到 150 ms，同一個連線池能撐多少 RPS？150 台 checkout 一共會開多少條資料庫連線，資料庫能接受嗎？
4. 為你熟悉的一個服務（或 Harbor 的 search）寫一列容量計畫：意圖、尖峰需求、單位 safe capacity、規劃量、最長 lead time、超出時的動作、owner。
5. 列出 Harbor 的 checkout 在「失去一個 zone」時會發生的所有二次效應（至少 5 項，包含快取、資料庫、連線重建、重試），並說明每一項要怎麼在活動前驗證。
6. 為 AI 客服 agent 設計容量指標：寫出要追蹤的 5 個指標、每個指標的單位，以及當模型 API 達到速率上限時的降級方案。

## 本章重點整理

- 容量是「在滿足 SLO 的前提下能處理的工作量」，沒有附帶品質條件的容量數字沒有意義。
- Capacity planning 需要三樣東西：涵蓋 lead time 的 organic 預測、對 inorganic 事件的估計，以及把原始資源對應到服務能力的 load test。
- Organic growth 可以從歷史推估；inorganic growth（活動、上線、client 變更）只能從事件本身推估，誤差也大得多。
- 規劃用尖峰而不是平均，時間解析度要短於系統擴容的反應時間。
- 業務預測要透過實測的 fan-out ratio 轉換成每個服務的負載；預測要給範圍，常以 P90 作為規劃基準，極端情境交給 load shedding 與降級。
- Load test 要畫出負載與 latency 的曲線，找出 knee 與最先耗盡的資源；open-loop、真實流量組成與冷快取能避免高估。
- Little's Law（L = λW）能從到達速率與停留時間推出需要的 thread、連線數，也能解釋依賴變慢時為何容量驟降。
- 排隊讓 latency 隨 utilization 非線性上升（M/M/1：W = S / (1 − ρ)），平均與 p99 一起按 1 / (1 − ρ) 放大，而 p99 的絕對值約是平均的 4.6 倍；請求成本變異越大、流量越突發，越不能把使用率拉高。
- N+1 承受單一故障或維護，N+2 承受一次維護加一次故障；以 failure domain 計算，3 個 zone 要能失去一個時需要 150% 的容量。
- Safe capacity 折扣、headroom、N+k 冗餘與 load shedding 保護不同的風險，每一層都要說得出理由。
- Provisioning 有從秒到月的 lead time，開好機器不等於能用；容量計畫要從最長的 lead time 倒推，並把 provisioning 當作需要驗證的變更。
- Autoscaling 適合平滑的日常變化，但對步階式流量反應太慢、可能看錯指標並把壓力推給下游；要設上限、搭配預先擴容與 load shedding。
- 容量是成本：用單位成本溝通，headroom 是保險費，底線與尖峰用不同方式取得，活動後要縮回。
- AI 功能的請求成本變異大，要用 token、同時對話數、tool call 與成本上限規劃，並防範 denial of wallet；AI 可以協助分析，但上下限與承諾要由人決定。

## 延伸問答

> [!question]- Q1. Safe capacity 和 maximum throughput 有什麼不同？為什麼規劃要用前者？
> Maximum throughput 是把機器壓到極限時每秒能完成的請求數，通常出現在 latency 已經很高、甚至開始出錯的時候。Safe capacity 則是在 SLO 門檻以下、而且離 latency 曲線的 knee 還有一點距離的負載。兩者的差距可能很大：Harbor 的 checkout 在 250 RPS 時還有 throughput，但 p99 已經是好幾秒。
>
> 規劃要用 safe capacity，因為使用者在意的是品質，不是機器的忙碌程度。用 maximum throughput 規劃，等於假設尖峰時所有使用者都願意等好幾秒；而一旦接近極限，小小的流量波動就會讓排隊急劇惡化，重試又會讓負載更高。Safe capacity 也要保留一點折扣，吸收單機效能差異與量測誤差。

> [!question]- Q2. 用 Little's Law 計算：Harbor 的 search 服務每秒 3,000 個請求，平均回應時間 80 ms。系統中平均有多少個請求在處理？如果某次變更讓回應時間變成 400 ms，會發生什麼事？
> L = λ × W = 3,000 × 0.08 = 240，平均有 240 個請求同時在處理。如果整個 fleet 有 30 台、每台 worker 上限 16 個，總共 480 個 worker，使用率約 50%，還算舒適。
>
> 回應時間變成 400 ms 後，L = 3,000 × 0.4 = 1,200，超過 480 個 worker 的上限。這代表系統無法維持穩定：多出來的請求會開始排隊，排隊又讓 W 變得更長，形成惡性循環，直到 timeout 或 load shedding 介入。這個算例說明，依賴變慢對容量的影響和流量增加是等價的：W 變成五倍，相當於流量變成五倍。所以容量規劃也要考慮「依賴變慢」的情境，而不只是「流量變多」。

> [!question]- Q3. 你是值班者。雙十一晚上 checkout 的 p99 開始上升，但平均 CPU 只有 50%。你會先看哪些東西？
> 平均 CPU 50% 不代表有空，我會依序排除三種可能。第一，負載不均：看每台機器的 CPU 與 RPS 分佈，而不是平均，若有一部分機器已經接近飽和，問題可能在 load balancing 或某些 zone。第二，瓶頸不在 CPU：看連線池使用率與等待時間、thread pool 的 queue 長度、下游服務（資料庫、金流商、inventory）的 latency 與錯誤率。依 Little's Law，依賴變慢會讓 in-flight 請求暴增，而 CPU 因為大家都在等反而下降。第三，時間解析度：看秒級的流量與 latency，確認是否有推播造成的突發。
>
> 在找原因的同時，要依容量計畫中「超出時的動作」先止血，例如關閉推薦、啟動排隊頁面，而不是等找到根因才行動（第 44 章）。如果是下游瓶頸，不要擴容 checkout，那只會把下游壓得更慘。

> [!question]- Q4. 為什麼 N+2 而不只是 N+1？什麼時候 N+1 就夠了？
> N+1 能承受一個單位失效，但現實中「計畫中的停機」非常頻繁：滾動部署時總有機器在重啟、作業系統更新時要逐台重開、某台機器被拿去除錯。如果剛好在維護期間又有一個單位故障，N+1 就不夠了。N+2 的設計就是為了同時承受一次計畫內停機和一次計畫外故障。
>
> N+1 適合的情況是：維護可以安排在離峰時段、單位數很多（例如 200 台中少 2 台影響很小，此時 N+k 的 k 可以用比例思考）、或服務的 SLO 較寬鬆。反過來，當「單位」是 zone 或 region 這種大的 failure domain，或服務對營收非常關鍵時，N+2 甚至更多才合理。關鍵是先定義你的 failure domain，再決定要承受幾個同時失效。

> [!question]- Q5. 產品經理問：「我們已經有 autoscaling，為什麼還要花時間做雙十一容量計畫？」你會怎麼回答？
> 我會用三個具體理由回答。第一，反應時間：autoscaling 從偵測到新機器可用要好幾分鐘，而午夜推播讓流量在一分鐘內翻好幾倍，這段時間只能靠事先準備好的容量或 load shedding。第二，下游與外部上限：autoscaling 只能擴容 stateless 服務，資料庫、金流商的上限需要數週到數月準備，autoscaling 甚至會把更多壓力推到它們身上。第三，資源不保證拿得到：雲端的 quota 與某些機型在尖峰時可能不足，申請失敗時 autoscaling 也無能為力。
>
> 我也會補充：autoscaling 本身就是容量計畫的一部分，它的上下限、看的指標、失效時的手動備案，都需要事先規劃。去年的事故就是「有 autoscaling、沒有計畫」的結果。

> [!question]- Q6. Harbor 的 checkout 部署在 2 個 zone。如果要能承受一個 zone 失效，需要多少冗餘？改成 3 個 zone 會有什麼變化？
> 2 個 zone 時，任何一個失效，另一個必須承擔 100% 的尖峰，所以每個 zone 都要能單獨扛全部流量，總容量是尖峰需求的 200%，正常時最多只能用到一半。改成 3 個 zone，失去一個後剩下 2 個要扛全部，每個 zone 需要 50% 的尖峰容量，總容量是 150%。4 個 zone 則是約 133%。
>
> 所以 zone 越多，冗餘比例越低，成本越省。但增加 zone 也有代價：跨 zone 的網路延遲與傳輸費用、資料庫 replica 的同步、部署與監控的複雜度，以及每個 zone 的規模變小後，單一 zone 內的機器失效影響比例變大。實務上 3 個 zone 是常見的平衡點。

> [!question]- Q7. 面試題：你要為一個從未上線過的新功能做容量規劃，沒有任何歷史資料，你會怎麼做？
> 沒有歷史資料時，我會從三個方向建立估計。第一，從業務假設推估需求：預計多少使用者會用、每人每天用幾次、尖峰集中在什麼時段，並用相似的既有功能作為參考（例如新的直播購物可以參考既有的限時搶購）。第二，從設計推估 fan-out：每次使用會呼叫哪些服務、各幾次，並在 staging 實際量測，而不是只看架構圖。第三，用 load test 量出單位 safe capacity 與瓶頸。
>
> 因為不確定性很高，我會給出區間（保守、預期、極端），用預期情境加上較大的 headroom 準備，極端情境準備降級與 load shedding。上線時用 feature flag 漸進開放（第 29 章），每一階段比對實際與預測，修正後再擴大。這個回答的重點是：沒有資料時，用可驗證的假設和漸進上線取代猜測。

> [!question]- Q8. 公司想讓 AI 維運 agent 負責「根據即時指標自動決定容量」，你會怎麼設計它的權限？
> 我會把 agent 的權限限制在 autoscaler 已有的框架內，而不是給它更大的自由。具體來說：它只能在預先核准的最小與最大台數之間調整，最大值依下游容量與成本上限計算；單次變更的幅度有上限（例如一次最多加 30%）；它不能修改 quota、採購或外部合約，這些需要人簽核；每一次動作都要記錄原因、依據的指標與預期效果，供事後審計。
>
> 另外要設計失效模式：agent 依賴的 metrics 異常時要停止動作而不是猜測；有人工覆寫與停用的開關；當 agent 判斷需要的容量超出核准範圍時，應該通知人並建議啟動 load shedding，而不是繞過限制。漸進授權的方式是先讓 agent 只提出建議、由人執行一段時間，比對它的建議和人的決定，再逐步讓它在低風險服務上自動執行（第 31 章的漸進授權）。

## 延伸閱讀

- [Site Reliability Engineering — Introduction](https://sre.google/sre-book/introduction/)：SRE 職責中「demand forecasting and capacity planning」與「provisioning」兩段，說明容量規劃的三個必要條件。
- [Site Reliability Engineering — Handling Overload](https://sre.google/sre-book/handling-overload/)：為什麼 QPS 不是好的容量單位，以及容量不足時的保護機制，是第 38 章的基礎。
- [Site Reliability Engineering — Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/)：容量不足如何透過排隊、重試演變成連鎖故障，以及 load test 的建議。
- [Site Reliability Engineering — Reliable Product Launches at Scale](https://sre.google/sre-book/reliable-product-launches/)：上線前的容量與負載檢查，對應 inorganic demand 的處理。
- [The Site Reliability Workbook — Table of Contents](https://sre.google/workbook/table-of-contents/)：從目錄進入第 11 章〈Managing Load〉，閱讀 autoscaling 的注意事項與負載管理的案例。
