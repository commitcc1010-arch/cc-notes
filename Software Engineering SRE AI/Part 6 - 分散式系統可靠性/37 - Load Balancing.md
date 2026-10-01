---
chapter: 37
title: Load Balancing：從入口到 Backend 選擇
part: 6
---

# 第 37 章　Load Balancing：從入口到 Backend 選擇

> [!abstract] 本章地圖
> **核心問題**：一個請求從使用者手機出發，要經過哪幾層決策，才會落到某一台「健康、有空、夠近」的 backend？每一層做錯了會怎樣？
>
> **你會學到**：
> - 分辨 DNS、anycast、L4、L7 與 client-side load balancing 各自負責的層次與限制
> - 比較 round robin、weighted、least connections、power of two choices 與 consistent hashing，知道各自何時會失敗
> - 用 subsetting 控制連線數，並理解為什麼隨機 subset 會不平均
> - 設計 health check、lame duck 與 connection draining，讓部署與故障不掉請求
> - 判斷 sticky session 的代價，以及跨區域導流時要先確認的容量與資料條件
>
> **前置知識**：第 33 章（golden signals）、第 36 章（容量、failure domain 與排隊）
>
> **對應原書**：SRE 第 19 章〈Load Balancing at the Frontend〉、第 20 章〈Load Balancing in the Datacenter〉

## 37.1 故事：回得最快的機器，搶走一半的流量

Harbor 第四年的夏天，距離雙十一還有幾個月，流量穩定成長。checkout 平時跑在約 50 台機器上，它呼叫的 inventory 服務也已經擴展到 10 台機器，前面是一組 L7 proxy，選擇 backend 的演算法是「least connections」：哪一台目前正在處理的請求最少，就把新請求送給它。這是美華半年前調整的設定，理由很合理：比 round robin 更能避開忙碌的機器。

一個週二晚上九點，inventory 的錯誤率在五分鐘內從 0.1% 爬到 48%。值班的 SRE 志明第一個反應是「十台壞了一台也只該有 10% 錯誤」，但數字明明是將近一半。志明打開每台 backend 的流量圖，答案很快就出現了：第 3 台的本機磁碟故障，所有請求都在 2 ms 內回傳 503；正常的機器處理一個請求要 50 ms。因為第 3 台回得最快，它「正在處理的請求」永遠最少，least connections 就不斷把新請求送給它。它一台吃掉了一半的流量。

更讓人困惑的是健康檢查。Proxy 每 10 秒對每台 backend 做一次 TCP 連線檢查，第 3 台的 process 還活著、port 還開著，所以健康檢查一直是綠燈。從 load balancer 的角度看，這是一台非常健康、非常有效率的機器。

志明手動把第 3 台移出輪替，錯誤率立刻掉回正常。但志明還想到另一件事：Harbor 剛在東京建好第二個 region，計畫是台灣 region 出事時把流量切過去，切換方式是修改 DNS。上個月的演練中，DNS 記錄的 TTL 設 60 秒，但切換後二十分鐘，仍有一成的流量打到舊的 region。

這兩件事背後是同一個問題：**load balancing 不是「把流量平均分配」這麼簡單**。每一層的 load balancer 都只看得到它自己的訊號，訊號錯了，它就會非常有效率地把流量送到錯的地方。這一章從最外層的 DNS 開始，一路走到「選哪一台 backend」，看清楚每一層在做什麼、看什麼、會怎麼錯。

## 37.2 Load balancing 在解決什麼問題

**Load balancing**（負載平衡）是決定「這個請求要給誰處理」的機制。它同時要達成好幾個目標，而這些目標常常互相拉扯：

- **不讓任何一台過載**：第 36 章說過，utilization 越接近 100%，latency 越非線性地上升。分配不均時，平均 50% 的 fleet 裡可能有幾台已經 95%。
- **避開不健康的 backend**：壞掉的機器不應該收到請求，快壞掉的也盡量少收。
- **選擇夠近的位置**：台北的使用者連到台灣的資料中心，比繞到東京快幾十毫秒。
- **讓維護與部署不掉請求**：機器要能優雅地離開與加入。
- **控制成本**：跨區域傳輸要錢，連線本身也耗資源。

SRE 書把這件事分成兩個層次：**frontend**（第 19 章）決定「請求要去哪個資料中心或 region」，**datacenter 內部**（第 20 章）決定「要給哪一台 backend」。兩層要回答的問題不同，用的工具也不同。

```text
 使用者手機
     │ ① DNS：查 api.harbor.tw → 回答離你近、有容量的 region 的 IP
     ▼
 ┌───────────────────────── 台灣 region ─────────────────────────┐
 │ ② Anycast／VIP：同一個 IP 在多個入口點宣告，封包進到最近的入口 │
 │     │                                                         │
 │     ▼ ③ L4 load balancer：看 IP 與 port，決定這條 TCP 連線給   │
 │ ┌────────┐ ┌────────┐ ┌────────┐   哪一台 L7 proxy            │
 │ │ L7     │ │ L7     │ │ L7     │                              │
 │ │ proxy  │ │ proxy  │ │ proxy  │ ④ L7：終止 TLS、看 HTTP 路徑，│
 │ └───┬────┘ └───┬────┘ └───┬────┘   每個請求選一個 backend      │
 │     └──────────┼──────────┘                                   │
 │                ▼                                              │
 │   checkout backends ─⑤ client-side LB─► inventory backends    │
 │   （服務之間：呼叫端自己挑 backend，通常只連一個 subset）       │
 └───────────────────────────────────────────────────────────────┘
```

① **DNS** 是最粗的一層，決定使用者大致去哪個 region，但它的回答會被快取，改了不會立刻生效。② **Anycast** 讓同一個 IP 位址從多個地點對外宣告，網路路由會把封包送到最近的那個入口。③ **L4 load balancer** 處理的是連線層級：一條 TCP 連線建立時決定交給誰，之後這條連線的所有封包都去同一個地方。④ **L7 proxy** 看得懂 HTTP，能對每一個請求各自做決定，也能依路徑、header 做路由。⑤ 服務之間的呼叫通常不再經過中央的 proxy，而是由呼叫端（client）自己決定要打哪一台，稱為 **client-side load balancing**。

接下來由外而內，一層一層拆開。

## 37.3 DNS load balancing：最外層、最粗、最難收回

### 怎麼運作

使用者的 app 要連 `api.harbor.tw`，第一步是問 DNS「這個名字對應哪個 IP」。**DNS load balancing** 就是在這個回答裡動手腳：同一個名字可以回傳多個 IP，或依照查詢者的位置回傳不同的 IP。常見的策略有：

- **多筆記錄輪流**：回傳 A、B、C 三個 IP，順序每次不同，client 通常挑第一個。
- **Geo DNS**：依查詢來源的地理位置，台灣的查詢回台灣 region 的 IP，日本的查詢回東京 region。
- **Latency-based**：依過去量到的延遲，回傳最快的 region。
- **加權與 failover**：90% 的回答指向台灣、10% 指向東京；或台灣健康檢查失敗時全部指向東京。

DNS 的優點是簡單、不需要在資料路徑上放任何設備，幾乎所有雲端與 DNS 服務都支援，很適合做「大方向」的決策。

### 它的限制

DNS 最大的問題是**你控制不了回答之後發生的事**。

**快取。** DNS 回答帶有 **TTL**（time to live，存活時間），告訴快取「這個答案可以用多久」。但答案會被好幾層快取：使用者的作業系統、瀏覽器、ISP 的遞迴解析器（recursive resolver），有些執行環境或 app 會自己快取更久，甚至不理會 TTL。Harbor 演練時 TTL 是 60 秒，二十分鐘後仍有流量打到舊 region，就是這個原因。實務上要假設「改 DNS 之後，有一條很長的尾巴」。

**看到的是解析器，不是使用者。** DNS 伺服器收到的查詢通常來自 ISP 或公共 DNS 的遞迴解析器，而不是使用者本人。如果使用者用的是一個在國外的公共 DNS，Geo DNS 可能以為這位使用者在國外。有一個 DNS 擴充機制（EDNS Client Subnet，RFC 7871）讓解析器在查詢中附上使用者網段的部分資訊，可以改善這個問題，但不是每個解析器都支援。

**粒度太粗、反應太慢。** 一個大型 ISP 的解析器背後可能有幾十萬個使用者，DNS 只能把他們整批送到同一個地方。DNS 也不知道某個 region 此刻是否快滿了，除非你另外把容量資訊餵給它。

**Client 行為不一致。** 回傳三個 IP，有的 client 只用第一個、有的隨機挑、有的在連不上時才試下一個。

所以 DNS 適合做「把使用者大致導到哪個 region」與「災難時的最後手段」，不適合做精細、快速的流量控制。精細的部分交給下一層。

> [!warning] 常見誤解
> 「把 TTL 設成 5 秒，切換就會在 5 秒內完成。」不會。TTL 只是給快取的建議，很多快取會設下限或忽略它；而且 TTL 越短，DNS 查詢量越大，每個新連線前的查詢延遲也越常出現。DNS 切換要用「大部分流量在幾分鐘內移動、尾巴拖很久」來規劃，並同時監控舊 region 的殘餘流量。

## 37.4 Anycast 與 virtual IP：讓一個位址代表很多台機器

### Virtual IP

使用者拿到的 IP 不是某一台機器的 IP，而是一個 **VIP**（virtual IP，虛擬 IP）：這個位址背後是一整組 load balancer，任何一台都能接收送到這個位址的封包。這讓 load balancer 本身可以擴充、可以壞掉一台而不影響使用者。

VIP 背後的 **network load balancer** 要解決一個問題：同一條 TCP 連線的所有封包，必須送到同一台 backend，否則連線會斷。最直接的做法是記住每條連線（**connection tracking**），但 load balancer 自己也會壞或被替換，記憶就不見了；遇到 DoS 攻擊這類壓力時，連線表也可能被塞爆。SRE 第 19 章描述的做法是平常用 connection tracking，壓力大時退回 **consistent hashing**（一致性雜湊）：用連線的來源與目的 IP、port 算 hash 決定 backend。相較於 `hash % N` 在 backend 增減時幾乎打亂所有連線，consistent hashing 的對應關係相對穩定，而且任何一台 load balancer 算出來的結果都一樣，換了一台 load balancer，大部分既有連線仍會被送到原本的 backend。書中為這套設計引用的論文，就是 Google 在 2016 年公開的軟體網路 load balancer Maglev。

封包怎麼轉給 backend 也有講究。書中提到一種做法叫 **direct server response**（DSR，業界也常稱 direct server return）：load balancer 只改寫封包的第 2 層目的 MAC 位址就轉給 backend，backend 看到的仍是原始 IP，回應直接送回使用者、不必再經過 load balancer。因為請求通常很小、回應很大，這能大幅減輕 load balancer 的負擔；代價是 load balancer 與所有 backend 必須在同一個廣播網域內。書中說 Google 後來改用 GRE 封裝：把原封包包進另一個送往 backend 的 IP 封包，backend 拆封後照常處理，兩者就不必在同一個網段，代價是多出的標頭可能讓封包超過 MTU，需要在資料中心內使用較大的 MTU。

### Anycast

**Anycast** 是讓同一個 IP 位址從多個地點同時透過 BGP（網際網路的路由協定）對外宣告。網路上的路由器會把封包送往「路由上最近」的那個地點。CDN 與公共 DNS 服務大量使用 anycast：使用者連的都是同一個 IP，但台北的使用者會進台北的節點，東京的使用者進東京的節點。

Anycast 的好處是**不依賴 DNS 的快取**，路由改變時流量幾乎立刻移動；它也很適合吸收 DDoS 攻擊，因為攻擊流量會被分散到所有地點。代價是：「路由上最近」不一定是「延遲最低」或「最有空」；路由變動時，進行中的 TCP 連線可能被送到另一個地點而中斷。所以 anycast 常和前面說的 consistent hashing、connection tracking 搭配，或只用在入口層，進來之後再由內部的 load balancer 精細分配。

Harbor 自己不經營 anycast 網路，而是使用雲端與 CDN 提供的全球入口。了解它的原理是為了知道：入口層換了地點時，可能有短暫的連線重建，client 要能優雅地重試（第 39 章）。

## 37.5 L4 與 L7：看見連線，還是看見請求

### 兩種層次

**L4 load balancer** 工作在 OSI 模型的第 4 層（傳輸層），它看得到 IP 位址與 port，看不到 HTTP 的內容。它在 TCP 連線建立時決定 backend，之後只是轉送封包。**L7 load balancer**（通常是一個 reverse proxy，例如 Envoy、NGINX、HAProxy 或雲端的應用程式 load balancer）工作在第 7 層（應用層），它會終止使用者的連線、解開 TLS、讀懂 HTTP 請求，再對**每一個請求**各自選擇 backend。

| 比較 | L4 | L7 |
|---|---|---|
| 看得到什麼 | IP、port、TCP／UDP | HTTP 方法、路徑、header、cookie、gRPC 方法 |
| 決策單位 | 連線 | 請求 |
| 效能 | 很高，邏輯簡單 | 較低，要解析協定、常要處理 TLS |
| 能做的事 | 分散連線、健康檢查 | 依路徑路由、header 導流（canary）、重試、限流、改寫、觀測每個請求的狀態碼與延遲 |
| 常見位置 | 最外層入口、VIP 後面 | L4 後面、服務前面、service mesh 的 sidecar |
| 風險 | 長連線會造成不均 | proxy 本身是新的故障點與容量瓶頸 |

### 長連線的陷阱

L4 以連線為單位，在 HTTP/1.1 的短連線時代問題不大。但現代服務大量使用 **HTTP/2 與 gRPC**，它們會在一條長時間存在的連線上多工傳送成千上萬個請求。如果一個 checkout instance 對 inventory 只開一條 gRPC 連線，L4 load balancer 只會在連線建立時選一次 backend，之後這個 checkout 的所有請求都打到同一台 inventory。新加入的 inventory 機器拿不到任何既有連線，擴容後負載仍然不均。

解法有三種：在 L7 對每個請求做選擇；在 client 端做 load balancing，讓 client 對多台 backend 各自開連線（37.6）；或在 server 端設定連線的最長存活時間（gRPC 的 max connection age 就是這種設定），定期讓 client 重新連線，給新的 backend 機會分到流量。

### 常見的組合

Harbor 的入口是「雲端 L4 → 一組 L7 proxy → 各服務」。L4 負責把大量連線快速分散到 proxy 上，並讓 proxy 本身可以擴充；L7 負責 TLS、依路徑把 `/checkout` 與 `/search` 分到不同服務、做 canary 導流（第 29 章）、在入口記錄每個請求的狀態碼與延遲（這正是第 32 章 SLI 的量測點）。服務之間則用 client-side load balancing，避免每個內部呼叫都多繞一跳 proxy。

## 37.6 選哪一台 backend：演算法與它們的失敗方式

到了最內層，load balancer 面前有一組 backend，要為每個請求（或連線）挑一台。這是本章故事的核心。

### Round robin 與 random

**Round robin**（輪流）是依序把請求分給 1、2、3……號 backend，再從頭開始。**Random** 是每次隨機挑一台。兩者都不需要任何關於 backend 狀態的資訊，簡單、可預測。

它們的前提是：**每個請求的成本差不多，每台 backend 的能力也差不多**。現實中這兩個前提都常常不成立。SRE 第 20 章列舉了好幾個原因：請求成本差異很大（書中提到最貴的請求可能用掉最便宜請求一千倍以上的 CPU，例如一次查一個商品和一次查一千個商品）、機器規格不同（新舊硬體世代混用）、同一台實體機上的其他工作搶資源（書中稱 antagonistic neighbors，業界常說 noisy neighbor）、剛重啟的程式在頭幾分鐘還在暖機、需要更多資源。在這些情況下，round robin 會讓慢的 backend 排起長隊，因為它照樣分到相同比例的請求。

### Weighted round robin

**Weighted round robin**（加權輪流）給每台 backend 一個權重，權重 2 的機器分到兩倍的請求。最簡單的權重是靜態的：新機型設 2、舊機型設 1。更好的做法是動態權重：SRE 第 20 章描述 Google 讓 backend 在每個回應（包括 health check 的回應）中附上自己的負載資訊：目前每秒處理的請求數與錯誤數，以及使用率（通常是 CPU），client 據此定期調整每台 backend 的權重，失敗的請求還會額外扣分。這樣能同時考慮機器能力與當下狀態，但需要 backend 回報可信的資訊。

### Least connections 與它的陷阱

**Least connections**（最少連線，或更精確地說「最少進行中請求」，least outstanding requests）每次都選目前 in-flight 請求最少的 backend。它不需要 backend 回報任何資訊，load balancer 自己就知道每台有幾個請求還沒回來。由第 36 章的 Little's Law（L = λW），慢的 backend 會累積較多 in-flight 請求，於是自然分到較少的新請求。這讓它能自動適應機器能力與請求成本的差異。

但 least connections 有一個致命的盲點，就是本章故事的事故：**快速失敗的 backend 看起來最空**。一台每個請求都在 2 ms 內回錯誤的機器，in-flight 永遠接近零，演算法會把越來越多流量送給它。SRE 第 20 章把這種情況稱為 sinkholing（像排水孔一樣把流量吸走），並提到一個對策：**把最近的錯誤也當成進行中的請求來計算**，讓一直出錯的 backend 看起來很忙。37.12 的模擬會顯示這個對策的效果。另一個對策是 **outlier detection**（離群偵測）：被動觀察每台 backend 的錯誤率，連續出錯的暫時踢出輪替（Envoy 這類 proxy 內建這個功能）。

Least connections 還有第二個問題：**當有很多台 load balancer 各自做決定時，它們會一起湧向同一台**。假設有 50 台 checkout 各自做 client-side load balancing，它們都看到 inventory 第 7 台最空，於是在同一瞬間都把請求送給它，第 7 台立刻從最空變成最忙。資訊越舊、決策者越多，這種「羊群效應」越嚴重。

### Power of two choices

**Power of two choices**（P2C，兩選一）是一個非常簡單、效果卻好得驚人的折衷：每次**隨機挑兩台**，再把請求送給這兩台中負載比較低的那一台。

為什麼有效？「隨機丟球進桶子」的經典分析指出：如果 n 顆球各自隨機丟進 n 個桶子，最滿的桶子大約有 log n / log log n 顆；但如果每顆球都隨機看兩個桶子、丟進比較空的那個，最滿的桶子降到大約 log log n / log 2 顆，差距是指數級的。直覺是：只要多看一個選項，就幾乎不會掉進最糟的那一台；但因為只看兩個隨機選項而不是全體的最小值，很多個 load balancer 同時決策時也不會全部擠向同一台。

P2C 已經是主流 proxy 的常見選項：Envoy 的「least request」演算法在各 backend 權重相同時，預設從隨機挑出的兩台中選 active request 較少者（候選數 choice_count 預設為 2，可調；權重不同時改用依進行中請求數動態調整的加權排程）；NGINX 的 `random two least_conn` 設定則是隨機挑兩台、再選 active connection 較少的那台。但要注意，單純的 P2C 仍然有 sinkholing 的問題（快速失敗的那台只要被抽中，就幾乎一定贏），只是程度比 least connections 輕，所以仍要搭配錯誤懲罰或 outlier detection。

### Consistent hashing：當你需要「同一個 key 去同一台」

前面的演算法都假設任何一台 backend 都能處理任何請求。有時候我們希望**同一個 key 總是去同一台**，例如 Harbor 的商品詳情快取服務：同一個商品 ID 若總是打到同一台，那台的本機快取命中率會高很多。

最直覺的做法是 `hash(key) % N`，但 N 一改變（加一台、壞一台），幾乎所有 key 都會換位置，快取瞬間全部失效。**Consistent hashing** 把 backend 與 key 都映射到一個環上，每個 key 去環上順時針遇到的第一台 backend；增減一台 backend 時，只有大約 1/N 的 key 需要移動。實務上每台 backend 會在環上放很多個虛擬節點，讓分佈更平均。另一個已知問題是熱門 key：一個爆紅商品的所有請求都去同一台，那台就會過載。「有上限的一致性雜湊」（consistent hashing with bounded loads）的做法是讓每台設負載上限，超過時把 key 溢出到環上的下一台。

### 誰來做選擇：proxy 還是 client

最後一個設計選擇是決策發生在哪裡。**Proxy 模式**是所有請求經過中央的 L7 proxy，由它選 backend；好處是 client 簡單、策略集中管理，壞處是多一跳延遲、proxy 本身要容量規劃。**Client-side 模式**是 client 自己取得 backend 清單（從服務發現系統）並選擇；少一跳、沒有中央瓶頸，但每個 client 只看得到自己送出的流量，資訊是局部的，而且每種語言的 client library 都要實作同一套邏輯。**Service mesh** 的 sidecar proxy 是兩者的混合：邏輯在每個 client 旁邊的 proxy 裡，但由中央控制平面統一下發設定。

| 演算法 | 需要什麼資訊 | 擅長 | 典型失敗 |
|---|---|---|---|
| Round robin／random | 無 | 同質 backend、同質請求 | 慢機器排長隊 |
| Weighted round robin | 權重（靜態或 backend 回報） | 新舊硬體混用 | 權重過時或回報錯誤 |
| Least connections | 每台 in-flight 數 | 請求成本差異大 | 快速失敗的 backend 吸走流量；多個決策者湧向同一台 |
| P2C | 兩台的 in-flight 數 | 分散式決策、大型 fleet | 仍需錯誤懲罰才能避開快速失敗 |
| Consistent hashing | key | 快取親和性 | 熱門 key 造成單台過載 |

## 37.7 Subsetting：不要每個 client 都連每個 backend

### 為什麼需要

Client-side load balancing 有一個規模問題。以 Harbor 雙十一尖峰的規模來算：checkout 擴到約 150 台機器、每台跑 2 個 instance，共 300 個 checkout instance；inventory 也從平時的 10 台擴到 30 台。每個 checkout 都對每台 inventory 開連線，就是 9,000 條連線。每條連線都要記憶體、要定期健康檢查、要 TLS 握手。當兩邊都成長到上千台時，連線數是百萬級，光是維持連線就會吃掉可觀的資源。

**Subsetting**（子集化）讓每個 client 只連 backend 的一部分：每個 checkout 只連 6 台 inventory。關鍵是：**要怎麼挑這 6 台，才能讓每台 inventory 被連的次數差不多？**

### 隨機 subset 為什麼不夠

最直覺的做法是每個 client 隨機挑 6 台。但隨機的結果並不平均：300 個 client、每個挑 6 台，平均每台 inventory 被 60 個 client 連，實際上有的被 46 個連、有的被 71 個（37.12 的模擬結果）。被 71 個 client 連的那台，承受的流量比平均多將近兩成，比最少的那台多五成。第 36 章說過，容量要依最忙的那台規劃，這個不均直接變成浪費或風險。

### Deterministic subsetting

SRE 第 20 章描述了一種 **deterministic subsetting**（確定性子集化）的演算法，思路是把 client 分「輪」：

```text
backend 數 30，subset 大小 6  →  每一輪可以切成 30 / 6 = 5 個 subset

client 0–4  是第 0 輪：用種子 0 洗牌 backend，切成 5 段，client 0 拿第 1 段 … client 4 拿第 5 段
client 5–9  是第 1 輪：用種子 1 重新洗牌，再切成 5 段
…
```

同一輪的 5 個 client 拿到的 subset 互不重疊、合起來剛好涵蓋全部 30 台，所以每一輪每台 backend 恰好被連 1 次。300 個 client 共 60 輪，每台 backend 恰好被 60 個 client 連。洗牌有兩個目的。第一，如果不洗牌、直接按編號切段，client 會拿到編號連續的 backend，而部署常常是依編號順序逐批更新，同一個 client 的 subset 可能整段同時在重啟。第二，每一輪用不同的種子，讓不同輪的 client 拿到不同的組合；這樣某台 backend 壞掉時，它的負載會分散到其餘許多 backend 上，而不是集中到固定幾台。Backend 數不能被 subset 大小整除時，有些 subset 會多一台，但每台 backend 被連的次數最多只差 1。

### Subset 要多大

Subset 太小，每個 client 的流量只能分散到少數幾台，任一台壞掉或變慢時，影響就很大；而且 client 數量少、流量不均時，backend 之間的負載差異會放大。Subset 太大，又回到連線數過多的問題。SRE 第 20 章提到 Google 常見的 subset 大小是 20 到 100 個 backend，但沒有通用的正確值；client 數遠少於 backend 數（否則有些 backend 會分不到流量），或 client 之間的流量很不平均時，就需要較大的 subset。其他判斷依據還有：可以容忍同時有幾台 backend 失效，以及 backend 每台能承受多少連線。本章例子用 6 是為了讓數字好算。Backend 數量改變時，subset 會重新計算，要注意這會造成一波連線重建。

## 37.8 Health check 與 lame duck：怎麼知道誰可以接請求

### 主動與被動

**Health check**（健康檢查）是 load balancer 判斷 backend 能否接流量的方法。**主動檢查**是定期對 backend 送探測：TCP 能否連上、HTTP `/healthz` 是否回 200。**被動檢查**是觀察真實流量的結果：最近 10 個請求有 5 個失敗，就把它暫時移出（也就是前面的 outlier detection）。兩者互補：主動檢查能在沒有流量時發現問題，被動檢查能發現「探測正常但真實請求失敗」的情況，例如本章故事的磁碟故障。

### 檢查要多深

這是 health check 最難的設計問題。

**太淺**的檢查，例如只確認 TCP port 有開，會漏掉大量真實故障：程式卡死、磁碟壞了、設定載入失敗，port 都還開著。Harbor 的 inventory 就是這樣。

**太深**的檢查，例如在 `/healthz` 裡順便確認資料庫、快取、三個下游服務都可用，看起來很周全，卻有一個危險的副作用：**共同依賴一出問題，所有 backend 同時被判定為不健康**。資料庫短暫抖動 5 秒，30 台 inventory 的健康檢查同時失敗，load balancer 把它們全部移出輪替，於是一個局部、短暫的問題變成全面中斷。而且移出之後，原本或許還能用快取服務一部分請求的能力也一併消失。

實務的折衷是：**health check 只檢查「這個 instance 本身」能否服務**（程式能回應、必要的本機資源正常、設定已載入、暖機已完成），依賴的狀態用 metrics 與告警觀察，而不是用來把自己移出輪替。另外，很多 load balancer 有「fail open」的保護：當不健康的 backend 比例超過某個門檻時，乾脆忽略健康檢查、把流量送給全部 backend，因為「大家都不健康」更可能是健康檢查本身或共同依賴出了問題。Envoy 的 panic threshold（預設 50%）就是這種設計。

Kubernetes 把這件事拆成兩種探測：**liveness probe**（失敗時重啟 container）與 **readiness probe**（失敗時從 Service 的 endpoints 移除，不再收流量但不重啟）。把依賴檢查放進 liveness probe 特別危險：資料庫一抖，所有 pod 被同時重啟，重啟後一起暖機、一起重建連線，反而把資料庫壓得更慘。

### Lame duck

SRE 第 20 章描述 backend 從 client 角度看有三種狀態：**healthy**（正常服務）、**refusing connections**（沒有回應，通常是正在啟動或關閉，或處於異常狀態）、**lame duck**（跛腳鴨）。Lame duck 是一個刻意設計的中間狀態：backend 還在監聽、還能服務，但明確告訴 client「請不要再送新請求給我」。

為什麼需要這個狀態？因為 backend 要停機時（部署、縮容、維護），如果直接關掉 process，正在處理的請求會失敗，client 也要等連線失敗才知道。有了 lame duck，關機的流程變成：

```text
 收到 SIGTERM
     │
     ▼
 進入 lame duck：health／readiness 開始回報「不接新請求」
     │              （或在回應中告知 client 自己即將離開）
     ▼
 等待 load balancer 與 client 看到這個狀態，停止送新請求
     │
     ▼
 繼續處理已經在手上的請求，直到完成或達到上限時間
     │
     ▼
 關閉連線、結束 process
```

這個流程把「停止接新工作」和「結束舊工作」分開。它和下一節的 connection draining 是同一件事的兩面：lame duck 是 backend 這邊的行為，draining 是 load balancer 那邊的行為。

## 37.9 Connection draining 與長連線

**Connection draining**（連線排空）是 load balancer 把某台 backend 移出輪替時，不立刻切斷它，而是停止分配新的請求，等已經在進行中的請求完成，超過上限時間才強制關閉。雲端 load balancer 通常把這個上限稱為 deregistration delay 或 draining timeout，預設值可能長達數分鐘（例如 AWS target group 的 deregistration delay 預設是 300 秒），要依服務最長的請求時間調整。

Draining 最常出錯的地方是**時序**。以 Kubernetes 為例，pod 要被刪除時，「送 SIGTERM 給 container」和「把 pod 從 Service 的 endpoints 移除、再讓各個 proxy 更新設定」是平行發生的。如果程式收到 SIGTERM 就立刻停止接受連線，而某些 proxy 還沒更新，它們會繼續送請求過來，結果就是每次部署都有一小段錯誤。常見做法是在 container 加一個 preStop 的短暫等待（例如 5–15 秒），讓移除的消息先傳遍，再開始 lame duck 流程；同時要注意 terminationGracePeriodSeconds（預設 30 秒）是從刪除開始算的總時限，preStop 的等待也包含在內，所以它要大於「preStop 等待＋最長請求時間」，否則時間一到，剩下的請求會隨 SIGKILL 一起中斷。

**長連線**讓 draining 更困難。WebSocket、gRPC streaming、HTTP keep-alive 連線可能持續好幾個小時，load balancer 不能永遠等下去。HTTP/2 提供了 GOAWAY 訊框，讓 server 通知 client「這條連線不再接受新的串流，請另開新連線」，client 就能平順地轉移；HTTP/1.1 可以在回應中加上 `Connection: close`。WebSocket 這類應用層的長連線，則需要 server 主動送出重新連線的訊號，而且 client 必須實作帶有隨機延遲的重連（第 39 章），否則一次部署會讓幾萬條連線在同一秒一起重連，形成 thundering herd（驚群效應）。

Harbor 在 inventory 事故後，把部署流程寫成一張檢查表：readiness 只檢查本機；preStop 先等 10 秒再進入 lame duck；lame duck 期間 HTTP/2 送 GOAWAY；手上的請求最多再等 25 秒；terminationGracePeriodSeconds 從預設的 30 秒調高到 45 秒（10＋25，再留 10 秒餘裕）；load balancer 的 draining timeout 設 35 秒。每次部署的錯誤數從平均數百個降到接近零。

## 37.10 Sticky session 的代價

**Sticky session**（黏性會話，也叫 session affinity）是讓同一個使用者的請求總是去同一台 backend。實作方式通常是 load balancer 發一個 cookie 記住 backend，或用使用者的 IP 做 hash。

團隊會想用它，通常是因為狀態放在 backend 的記憶體裡：購物車暫存在本機、登入 session 只存在某台機器上、或者本機快取了這位使用者的資料。黏住之後，這些東西就能用。

代價卻不小：

- **負載不均**。使用者的活躍程度差很多，一個正在大量下單的企業賣家會讓自己黏住的那台特別忙，而 load balancer 不能把這位賣家移走。
- **故障時狀態消失**。黏住的那台壞了，使用者被分到另一台，記憶體裡的購物車就不見了。Sticky session 讓「機器壞掉」從一個使用者無感的事件，變成使用者看得到的資料遺失。
- **擴容沒有立即效果**。新加入的機器只會分到新來的使用者，既有使用者都黏在舊機器上。如果 Harbor 用 sticky session，雙十一前把機器加倍時，已經在線上的使用者仍黏在舊機器，舊機器的負載會幾乎不降，直到這些 session 過期。
- **Draining 拖很久**。要移除一台機器，得等所有黏在它上面的 session 過期，部署因此變慢。
- **IP hash 的特殊問題**。行動網路與企業網路常讓大量使用者共用同一個出口 IP（carrier-grade NAT），這些人會全部被 hash 到同一台。

比較好的做法是**把狀態移出 backend**：session 放到共享的儲存（例如 Redis 或資料庫），或用帶簽章的 token 讓每個請求自帶必要資訊，backend 就變成 stateless，任何一台都能處理任何請求。若真的需要親和性（例如為了本機快取命中率），就用 37.6 的 consistent hashing，並把它當成**效能最佳化而不是正確性的前提**：請求被送到別台時，應該只是變慢，而不是出錯。Harbor 的購物車在 inventory 事故後的一次 ADR（第 7 章）中，正式從 checkout 的記憶體搬到了共享儲存。

## 37.11 跨區域流量管理

回到故事的第二件事。Harbor 現在有台灣與東京兩個 region，跨區域流量管理要回答三個問題：平常怎麼分、出事時怎麼切、切了之後撐不撐得住。

### 平常怎麼分

最常見的是**就近服務**：台灣使用者去台灣、日本使用者去東京，用 Geo DNS 或全球入口的 anycast 加上就近路由達成。比較成熟的 global load balancer 會同時考慮**容量**：SRE 第 19 章提到，好的全域負載平衡要考慮使用者到各資料中心的距離、各資料中心當下的負載與容量，而不是只看地理位置。當台灣 region 接近滿載時，部分流量**溢出**（spillover）到東京，多花幾十毫秒延遲，總比在台灣排隊或被拒絕好。

### 出事時怎麼切

**Active-passive** 是平常只用台灣，東京只在災難時接手；**active-active** 是兩邊平常都在服務，出事時把流量集中到健康的一邊。Active-passive 簡單，但「平常沒在用的東西，需要時往往不能用」：東京的快取是冷的、設定可能過時、容量可能沒跟著台灣成長。Active-active 讓兩邊都持續被真實流量驗證，代價是更複雜的資料同步。

切換的手段由快到慢大致是：全球 L7 入口或 anycast 層的權重調整（秒到分鐘），DNS 修改（分鐘，加上很長的尾巴），以及 client 端內建的備援位址（取決於 app 版本）。Harbor 演練後的改進是：主要的切換改用全球入口的權重，DNS 只當最後手段；並且**漸進地**移動流量，例如每兩分鐘移 20%，同時觀察東京的 latency 與錯誤率，而不是一次把 100% 倒過去。

### 切了之後撐不撐得住

這是最常被忽略的一步，而它完全是第 36 章的問題。如果台灣 region 平常承擔 80% 的流量，東京只準備了自己 20% 的容量，切換的那一刻東京會被壓垮，兩個 region 一起掛。跨區域的 failover 是一種 N+1，**以 region 為 failure domain** 計算：兩個 region 各自都要能承擔失去另一邊後的總流量，或者事先決定在 failover 時要犧牲哪些功能（第 38 章的 load shedding 與降級）。

另外有兩個常見的陷阱。**冷快取**：東京的快取裡沒有台灣使用者常看的商品，切換後命中率驟降，資料庫負載突然上升。**資料位置與一致性**：如果訂單資料的主節點在台灣，東京的 backend 寫入時仍要跨區域打回台灣，台灣整個 region 掛掉時，東京根本無法寫入；這牽涉到資料複製與一致性的選擇，第 40 章會討論。

```text
 平常：                                   台灣 region 失效後（漸進切換）：
 台灣使用者 ──► 台灣 region（80%）         台灣使用者 ──╳─► 台灣 region
 日本使用者 ──► 東京 region（20%）              │
                  │ 接近滿載時                  └──────► 東京 region（100%）
                  └─ spillover ─► 東京              需要：容量 ≥ 總流量
                                                    快取預熱、資料主節點可用
```

圖的左邊是平常：各自就近，滿載時才溢出。右邊是 failover 後：所有流量去東京，而圖下方的三個條件，任何一個不成立，切換就只是把事故從一個 region 搬到另一個。這也是為什麼跨區域 failover 必須定期演練（第 46 章），而且要在真實流量下驗證。

## 37.12 動手寫：backend 選擇演算法與 subsetting 模擬

下面的程式用離散事件模擬比較五種 backend 選擇策略，重現本章故事的 sinkholing，再比較隨機與確定性的 subsetting。模擬參數都是為了說明而設的假設，不是 Harbor 的實測值：10 台 backend、每台 4 個 worker、平均處理時間 50 ms（指數分布）、壞機器固定 2 ms 回 503、舊機器慢 1.5 倍、錯誤懲罰的視窗是 1 秒，以及固定的亂數種子。

```python
import heapq
import random
from collections import deque

BACKENDS, WORKERS, SERVICE_MS = 10, 4, 50.0
POLICIES = ("round robin", "random", "least outstanding", "P2C", "P2C + 錯誤懲罰")


def simulate(policy, load, bad=None, slow=(), n=60_000, seed=11):
    """bad：快速回 503 的 backend；slow：處理時間是 1.5 倍的舊機器。"""
    rng = random.Random(seed)
    rate = load * BACKENDS * WORKERS / SERVICE_MS          # 每 ms 到達的請求數
    free_at = [[0.0] * WORKERS for _ in range(BACKENDS)]   # 每個 worker 何時有空
    outstanding = [0] * BACKENDS                           # 每個 backend 的 in-flight 數
    recent_errors = [deque() for _ in range(BACKENDS)]     # 最近 1 秒內的錯誤時間
    done_events, sent = [], [0] * BACKENDS
    rr, t, errors, latency = 0, 0.0, 0, []

    def score(b):                                          # 把最近的錯誤也算成負載
        while recent_errors[b] and recent_errors[b][0] < t - 1000:
            recent_errors[b].popleft()
        return outstanding[b] + len(recent_errors[b])

    for _ in range(n):
        t += rng.expovariate(rate)
        while done_events and done_events[0][0] <= t:      # 先結算已完成的請求
            when, b, failed = heapq.heappop(done_events)
            outstanding[b] -= 1
            if failed:
                recent_errors[b].append(when)
        if policy == "round robin":
            b, rr = rr, (rr + 1) % BACKENDS
        elif policy == "random":
            b = rng.randrange(BACKENDS)
        elif policy == "least outstanding":
            low = min(outstanding)
            b = rng.choice([i for i in range(BACKENDS) if outstanding[i] == low])
        else:                                              # power of two choices
            x, y = rng.sample(range(BACKENDS), 2)
            cost = score if policy.endswith("懲罰") else outstanding.__getitem__
            b = x if cost(x) <= cost(y) else y
        sent[b] += 1
        outstanding[b] += 1
        if b == bad:
            heapq.heappush(done_events, (t + 2.0, b, True))
            errors += 1
            continue
        mean = SERVICE_MS * (1.5 if b in slow else 1.0)
        start = max(t, heapq.heappop(free_at[b]))
        finish = start + rng.expovariate(1 / mean)
        heapq.heappush(free_at[b], finish)
        heapq.heappush(done_events, (finish, b, False))
        latency.append(finish - t)
    latency.sort()
    return sent, errors / n, latency[int(len(latency) * 0.99)]


def pad(text, width):                                      # 中文字佔兩格
    return text + " " * (width - sum(2 if ord(c) > 0x2E80 else 1 for c in text))


print("情境 A：backend 3 磁碟壞了，2 ms 內回 503（負載 70%）")
print("policy              壞 backend 分到   錯誤率   成功請求 p99")
for p in POLICIES:
    sent, err, p99 = simulate(p, load=0.7, bad=3)
    print(f"{pad(p, 20)}{sent[3] / sum(sent):>10.1%}   {err:>8.1%}   {p99:>8.0f} ms")

print()
print("情境 B：backend 0、1 是舊機器，慢 1.5 倍（負載 60%）")
print("policy              舊機器分到   成功請求 p99")
for p in POLICIES:
    sent, _, p99 = simulate(p, load=0.6, slow=(0, 1))
    print(f"{pad(p, 20)}{(sent[0] + sent[1]) / sum(sent):>8.1%}   {p99:>9.0f} ms")


# ── Subsetting：300 個 client、30 個 backend，每個 client 只連 6 個 ────────
def deterministic_subset(backends, client_id, subset_size):
    subset_count = len(backends) // subset_size            # 每一輪可分成幾個 subset
    round_id = client_id // subset_count
    shuffled = list(backends)
    random.Random(round_id).shuffle(shuffled)              # 同一輪的 client 用同一種洗牌
    sid = client_id % subset_count
    return shuffled[sid * subset_size:(sid + 1) * subset_size]


def connection_spread(choose):
    count = [0] * 30
    for client in range(300):
        for b in choose(client):
            count[b] += 1
    return min(count), max(count)


rng = random.Random(5)
print()
print("每個 backend 被多少 client 連線（理想值 60）")
print("隨機 subset      最少 %d、最多 %d" % connection_spread(lambda c: rng.sample(range(30), 6)))
print("deterministic    最少 %d、最多 %d" %
      connection_spread(lambda c: deterministic_subset(range(30), c, 6)))
```

執行結果：

```text
情境 A：backend 3 磁碟壞了，2 ms 內回 503（負載 70%）
policy              壞 backend 分到   錯誤率   成功請求 p99
round robin              10.0%      10.0%        242 ms
random                   10.0%      10.0%        287 ms
least outstanding        51.5%      51.5%        231 ms
P2C                      19.2%      19.2%        230 ms
P2C + 錯誤懲罰            1.1%       1.1%        235 ms

情境 B：backend 0、1 是舊機器，慢 1.5 倍（負載 60%）
policy              舊機器分到   成功請求 p99
round robin            20.0%         379 ms
random                 19.8%         527 ms
least outstanding      15.0%         257 ms
P2C                    16.2%         257 ms
P2C + 錯誤懲罰         16.2%         257 ms

每個 backend 被多少 client 連線（理想值 60）
隨機 subset      最少 46、最多 71
deterministic    最少 60、最多 60
```

逐段解讀：

1. **模擬的結構**。每台 backend 有 4 個 worker 共用一條 queue（第 36 章的 M/M/c）。每個請求抵達前，先把已經完成的請求結算掉，更新每台的 in-flight 數；再依策略挑 backend。這和真實的 load balancer 一樣：它只知道「我送出去、還沒回來」的請求有幾個。
2. **情境 A 重現了故事**。Round robin 與 random 不看狀態，壞掉的那台分到它應得的 10%，錯誤率 10%。Least outstanding 讓壞掉的那台吃掉 51.5% 的流量，錯誤率暴增五倍，和 Harbor 當晚看到的 48% 非常接近。單純的 P2C 也被拖累到 19%，因為壞機器只要被抽中就幾乎必勝。把最近 1 秒的錯誤也算成負載之後，壞機器的分數高到幾乎不會被選，錯誤率降到 1.1%。
3. **為什麼不乾脆用 round robin**？看情境 B。兩台舊機器處理一個請求要 75 ms，round robin 照樣分給它們 20% 的流量，它們的使用率接近 90%，排出長隊，整體 p99 變成 379 ms；random 因為還會隨機地讓某幾台短暫過載，更糟。Least outstanding 與 P2C 自動把舊機器的份額降到 15%–16%，p99 只有 257 ms。所以「看負載」的演算法在正常時更好，只是需要錯誤懲罰補上它的盲點。
4. **Subsetting**。隨機 subset 讓被連最多的 backend 比最少的多五成，deterministic subsetting 則每台恰好 60 個。這個差距會直接反映在每台 backend 的負載上。
5. **真實系統的差異**。模擬裡的 least outstanding 是一個全知的中央 load balancer，看得到精確、即時的數字，所以沒有出現 37.6 說的羊群效應；在很多 client 各自決策、資訊有延遲的真實環境中，least outstanding 的表現會更差，而 P2C 的優勢更明顯。真實系統也還會有主動 health check 與 outlier detection，在幾秒到幾十秒內把壞機器踢出去；錯誤懲罰的價值是在那之前就把傷害壓低。

## 37.13 Trade-offs 與 Failure Modes

| 做法 | 什麼時候會出問題 | 具體情境 | 對策 |
|---|---|---|---|
| Least connections | 快速失敗的 backend 吸走流量 | Inventory 一台磁碟壞，回 503 只要 2 ms，吃掉一半流量 | 錯誤計入負載、outlier detection、health check 涵蓋本機資源 |
| 只做 TCP health check | 程式卡住或依賴本機資源失效，但 port 仍開 | 健康檢查全綠，錯誤率 48% | 應用層 health check 加被動錯誤偵測 |
| Health check 檢查共同依賴 | 依賴抖動時全部 backend 同時被移除 | 資料庫抖 5 秒，30 台 inventory 全部離線 | 只檢查本機；設定 fail open／panic threshold；依賴狀態用告警處理 |
| 用 DNS 做快速切換 | 快取讓切換拖出長尾 | TTL 60 秒，二十分鐘後仍有一成流量打舊 region | 用全球入口權重做主要切換，DNS 當最後手段，監控殘餘流量 |
| L4 搭配 HTTP/2／gRPC 長連線 | 擴容後新 backend 分不到流量 | 加了 10 台 inventory，負載仍集中在舊的 10 台 | L7 或 client-side 逐請求平衡；設定 max connection age |
| Sticky session | 負載不均、故障時遺失狀態、擴容無效 | 若用 sticky session，雙十一前擴容後舊機器負載幾乎不降；機器壞了購物車消失 | 狀態外移；需要親和性時用 consistent hashing 並容許錯位 |
| 隨機 subsetting | Backend 連線數與負載不均 | 最忙的 backend 比最閒的多五成 client | Deterministic subsetting，並依 client 流量選 subset 大小 |
| Failover 到容量不足的 region | 切換把事故搬到另一個 region | 東京只有 20% 容量，承接 100% 流量後全面過載 | 以 region 為 failure domain 規劃容量；漸進切換；事先決定降級範圍 |

## 37.14 AI 時代：什麼變了？

**第一，AI 推論服務需要不同的平衡訊號。** Harbor 的 AI 客服 agent 背後有模型推論服務。這類服務的請求成本變異極大：一個請求可能只產生 20 個 token，也可能產生 2,000 個；長對話的 prompt 越來越長，處理時間跟著變長；串流回應讓一個請求佔用連線好幾秒到幾十秒。以「請求數」或「連線數」平衡會嚴重失準。比較有意義的訊號是 backend 的佇列中等待處理的 token 數、正在生成的序列數、加速器記憶體的使用量（例如存放對話中間狀態的快取用了多少）。很多推論服務也會利用「相同前綴的 prompt 送到同一台，可以重用已計算的中間結果」的特性做親和性路由，這正是 37.6 consistent hashing 的取捨在新場景的重演：命中率提高了，熱門前綴卻可能讓單台過載，必須有溢出機制。

如果推論是呼叫外部模型供應商，load balancing 的對象就變成**多個供應商或多個模型層級**：依延遲、錯誤率、每分鐘的 token 配額與成本，把請求分配給不同的端點，配額用盡時切換到備援。這和跨區域流量管理是同一套思考：平常怎麼分、出事時怎麼切、切了之後撐不撐得住（備援模型的品質與配額是否足夠，是否需要先通過第 32 章提到的 eval）。

**第二，AI 維運 agent 可以協助調查與調整，但流量控制是高風險操作。** 調整 load balancer 的權重、把一台 backend 移出輪替、切換 region，都是一個動作就影響大量使用者的變更。

| 適合交給 AI 的工作 | 必須保留的人類判斷與 guardrails |
|---|---|
| 比對每台 backend 的流量、錯誤率、latency 分佈，找出吸走流量或負載不均的機器 | 結論要附上可重現的查詢；是否把 backend 移出輪替，在預先核准的範圍內（例如一次最多一台、總數不低於 N+1）才可自動執行 |
| 審查 load balancer 與 health check 設定，指出「檢查共同依賴」「只做 TCP 檢查」等風險 | 設定變更走 code review 與漸進發布（第 29、35 章），不由 agent 直接改 production |
| 演練時依 runbook 執行漸進的區域切換，並即時回報目標 region 的容量與錯誤率 | 是否在真實事故中切換 region、切多少比例，由 incident commander 決定（第 44 章）；agent 不能自行觸發全域切換 |
| 為 AI 推論服務分析 token 分佈，建議平衡訊號與親和性策略 | 新的平衡策略先在部分流量上驗證；保留一鍵回到簡單策略的開關 |
| 草擬 subsetting 大小、draining timeout 等參數的計算與理由 | 參數的取捨（連線成本 vs 容錯）由服務 owner 決定並記錄於 ADR |

> [!ai] AI 提醒
> AI coding agent 在產生服務程式碼時，常會順手寫一個「完整」的 health check：連資料庫、打下游、檢查快取，全部通過才回 200。這正是 37.8 說的危險設計。審查 agent 產生的 health check 與 readiness probe 時，要特別問：這個檢查失敗時，load balancer 會做什麼？如果所有 instance 同時失敗，會發生什麼？

## 37.15 專家怎麼想

- **「這個 load balancer 看的是什麼訊號？訊號錯了會怎樣？」** 每一層 load balancer 都會非常有效率地執行它的演算法。專家先問它依據什麼做決定，再想像那個訊號說謊的情況：快速失敗、health check 太淺、資訊過時。
- **健康檢查是一種自動化的「移除」權力，要像對待自動化一樣謹慎。** 會同時移除所有 backend 的檢查，比沒有檢查更危險。資深 SRE 會確認有 fail open 的保護，並且只讓檢查反映 instance 自身的狀態。
- **偏好簡單、可預測、對局部資訊穩健的演算法。** 在分散式決策的環境中，P2C 加錯誤懲罰常常比複雜的全域最佳化更好，因為它在資訊不完整時也不會一起犯錯。
- **把「離開」設計得和「加入」一樣仔細。** 大部分部署時的錯誤，來自 instance 離開時的時序：SIGTERM、endpoint 移除、draining 的順序。專家會實際量一次部署期間的錯誤數，而不是假設它是零。
- **Failover 是容量問題，不只是路由問題。** 看到跨區域切換的設計，第一個問題是：目標 region 有沒有容量、快取是不是冷的、資料寫得進去嗎？
- **狀態放在哪裡，決定了 load balancing 能多自由。** 想移除 sticky session，真正的工作通常是搬移狀態，而不是改 load balancer 設定。

## 37.16 動手練習

1. 修改 37.12 的模擬，加入「主動 health check」：每 10 秒（模擬時間）檢查一次，若某台 backend 最近 10 秒的錯誤率超過 50%，就把它移出 30 秒。比較 least outstanding 在有與沒有這個機制時的錯誤率，再思考錯誤懲罰與 health check 各自保護的是哪段時間。
2. 在模擬中加入「多個 load balancer 各自決策、資訊延遲 50 ms」：每個 load balancer 看到的 in-flight 數是 50 ms 前的快照。比較 least outstanding 與 P2C 的 p99，觀察羊群效應。
3. 用 `deterministic_subset` 計算：backend 從 30 台增加到 36 台時，有多少比例的 client 的 subset 改變了？這對連線重建有什麼影響？
4. 為 Harbor 的 checkout 寫一份 health check 與關機流程設計：liveness 與 readiness 各檢查什麼、不檢查什麼，SIGTERM 之後每一步的時間，以及 load balancer 的 draining timeout。說明每個數字的理由。
5. 為 Harbor 台灣與東京兩個 region 設計一份 failover runbook 的大綱：切換的觸發條件、切換手段的優先順序、每一步移動多少流量、要觀察哪些指標、什麼情況下要停止或回退，以及事前要確認的容量與資料條件。
6. 找一個你用過的 load balancer 或 proxy（雲端 LB、NGINX、Envoy、Kubernetes Service），查它的預設演算法、health check 方式、是否 fail open，以及 draining 的預設時間，寫成一張表。

## 本章重點整理

- Load balancing 分兩層：frontend 決定請求去哪個 region 或資料中心，datacenter 內部決定給哪一台 backend；每一層看的訊號與限制都不同。
- DNS load balancing 簡單、適合粗粒度的地理分配與最後手段的切換，但快取與遞迴解析器讓它的變更有很長的尾巴，不適合快速精細的控制。
- VIP 讓一組 load balancer 共用一個位址，consistent hashing 與 connection tracking 讓同一條連線落在同一台 backend；anycast 讓同一個 IP 從多地點宣告，流量進到路由上最近的入口。
- L4 以連線為單位、速度快；L7 以請求為單位、能依內容路由與觀測。HTTP/2、gRPC 長連線搭配 L4 會造成不均，需要逐請求平衡或限制連線存活時間。
- Round robin 假設請求與 backend 同質；weighted round robin 用權重反映能力；least connections 能適應成本差異，但會被快速失敗的 backend 吸走流量，也會在多個決策者之間造成羊群效應。
- Power of two choices 只看兩個隨機選項，就能大幅降低最忙 backend 的負載，並且在分散式決策下保持穩健；仍需搭配錯誤懲罰或 outlier detection。
- Consistent hashing 讓同一個 key 去同一台，增減 backend 時只移動約 1/N 的 key，適合快取親和性，但要處理熱門 key。
- Subsetting 控制連線數；隨機 subset 會不平均，deterministic subsetting 讓每台 backend 被連的次數一致。
- Health check 只應反映 instance 自身能否服務；檢查共同依賴會讓局部問題變成全面中斷，要搭配 fail open 的保護。
- Lame duck 讓 backend 先停止接新請求、再完成舊請求；connection draining 是 load balancer 端的對應行為，部署錯誤多半來自兩者的時序沒有對齊。
- Sticky session 讓負載不均、故障時遺失狀態、擴容與 draining 變慢；優先把狀態移出 backend，需要親和性時當成效能最佳化而非正確性前提。
- 跨區域 failover 是以 region 為 failure domain 的容量問題，要確認目標 region 的容量、快取與資料寫入能力，並漸進切換、定期演練。
- AI 推論服務需要用 token、佇列與加速器記憶體等訊號做平衡；AI 維運 agent 可以分析與在核准範圍內操作，但大範圍的流量切換由人決定。

## 延伸問答

> [!question]- Q1. 你是值班者。Inventory 有 10 台 backend，一台壞了，但錯誤率是 48% 而不是 10%。你會怎麼推理？
> 錯誤率遠高於「壞掉的比例」，代表那台壞機器分到的流量遠超過十分之一，問題在 load balancing 的分配，而不只是單台故障。我會先看每台 backend 的請求數與錯誤率分佈，確認是否有一台吸走了大量流量；接著看它的回應時間，如果它的錯誤回得特別快，再加上演算法是 least connections 或類似「選最空的」策略，就幾乎可以確定是 sinkholing。
>
> 止血的動作是把那台手動移出輪替，錯誤率應該立刻回落。之後的修正有三個層次：讓 health check 能偵測到這類故障（例如檢查本機磁碟），啟用 outlier detection 自動踢出連續出錯的 backend，以及讓演算法把最近的錯誤也計入負載。Postmortem 也要記錄「health check 全綠但服務在失敗」，這代表檢查的深度需要重新設計。

> [!question]- Q2. 為什麼 power of two choices 只多看一個選項，效果就比隨機好那麼多？為什麼不乾脆看全部、選最小的？
> 隨機分配的問題是會「運氣不好」地把很多請求丟到同一台。只要每次多看一台、選比較空的那台，掉進最糟那台的機率就大幅下降：兩台都恰好很忙的機率，遠低於一台很忙的機率。經典的分析顯示，最忙 backend 的負載從隨機時的 log n / log log n 降到大約 log log n，對大型 fleet 來說差距非常明顯。
>
> 不看全部選最小，有兩個理由。第一是成本：每次都要知道所有 backend 的即時狀態，在大型系統中代價很高。第二、也是更重要的理由：當很多個 load balancer 各自決策、資訊又有延遲時，大家會在同一瞬間湧向同一台「最空」的 backend，讓它立刻過載，這就是羊群效應。P2C 每次的兩個候選是隨機的，不同決策者通常會挑到不同的組合，因此在資訊不完整時依然穩健。

> [!question]- Q3. 新來的同事寫了一個 health check：確認資料庫、Redis 與兩個下游服務都正常才回 200，並把它設成 Kubernetes 的 liveness probe。你會給什麼 review 意見？
> 我會指出兩個問題。第一，health check 檢查了共同依賴：資料庫或 Redis 只要短暫抖動，所有 pod 的檢查會同時失敗，load balancer 或 Kubernetes 會同時把它們全部移除，一個局部、短暫的問題就變成全面中斷，連原本能用快取或降級回應的能力都一起失去。第二，它被設成 liveness probe：失敗時 pod 會被重啟，所有 pod 同時重啟、同時暖機、同時重建連線，反而會在依賴最脆弱的時候加重它的負擔。
>
> 建議改成：liveness 只確認程式本身還活著、沒有卡死；readiness 確認 instance 已完成啟動與暖機、必要的本機資源正常，可以接流量；依賴的狀態用 metrics 與告警觀察，並在程式中對依賴失敗做降級處理。同時確認 load balancer 有 fail open 的保護。

> [!question]- Q4. Harbor 的 checkout 改用 gRPC 呼叫 inventory，前面是一個 L4 load balancer。擴容了 10 台 inventory 之後，新機器幾乎沒有流量。為什麼？怎麼修？
> gRPC 建立在 HTTP/2 上，會在一條長時間存在的連線上多工傳送大量請求。L4 load balancer 只在連線建立時選擇 backend，之後這條連線的所有請求都去同一台。既有的 checkout 早就和舊的 10 台 inventory 建好了連線，除非連線斷掉重建，否則永遠不會用到新機器。
>
> 修法有三種，可以組合使用。一是改用 L7 load balancer 或 service mesh 的 sidecar，對每個請求各自選擇 backend。二是改用 client-side load balancing：checkout 從服務發現取得 inventory 清單，對多台各自開連線並在請求層級選擇。三是在 inventory 端設定 max connection age，定期讓連線結束、client 重新連線，讓新的 backend 有機會分到連線；結束時要用 GOAWAY 讓 client 平順轉移，並加上隨機的時間差，避免所有連線同時重建。

> [!question]- Q5. 計算題：假設 Harbor 再成長一年，有 400 個 checkout instance 與 40 台 inventory。不做 subsetting 時有多少條連線？如果每個 checkout 只連 8 台，用 deterministic subsetting，每台 inventory 會被多少個 checkout 連？如果改用隨機挑 8 台，會有什麼差別？
> 不做 subsetting 時，每個 checkout 都連每台 inventory，共 400 × 40 = 16,000 條連線。Subset 大小 8 時，總連線數降到 400 × 8 = 3,200 條。Deterministic subsetting 中，每一輪可切成 40 / 8 = 5 個不重疊的 subset，5 個 client 為一輪，400 個 client 共 80 輪，每輪每台 inventory 恰好被連一次，所以每台恰好被 80 個 checkout 連。
>
> 隨機挑 8 台時，平均也是每台 80 個，但會有明顯的隨機波動：有的 inventory 可能被六十多個 client 連、有的接近一百個。因為每個 client 會把自己的流量分散在它的 subset 上，被連得多的 inventory 就會承受明顯更多的流量，容量必須依最忙的那台規劃，等於浪費了平均與最大值之間的差距。

> [!question]- Q6. 產品團隊說：「購物車存在 checkout 的記憶體裡，所以我們需要 sticky session。」你會怎麼評估？
> 我會先列出 sticky session 的代價給團隊看：活躍的使用者會讓某些機器特別忙而無法移走；機器壞掉時，使用者的購物車就消失，這是使用者看得到的資料遺失；雙十一擴容時，既有使用者都黏在舊機器上，新機器分不到負載；每次部署要等 session 過期才能移除機器，部署變慢；如果用 IP hash，共用出口 IP 的大量行動網路使用者會擠在同一台。
>
> 根本的解法是把購物車移出 checkout 的記憶體，放到共享的儲存，讓 checkout 變成 stateless。這通常是一個值得寫 ADR 的決策，因為它牽涉到延遲、儲存成本與遷移工作。如果短期內做不到，至少要讓 sticky session 失效時只是降級（例如購物車從持久化的備份重建），並規劃好部署與擴容時的處理方式。

> [!question]- Q7. 台灣 region 出事了，主管要求「立刻把 100% 流量切到東京」。你身為 SRE，在執行之前會確認什麼？
> 我會快速確認三件事。第一，容量：東京平常承擔多少流量、目前準備了多少容量，能否承擔全部流量；如果不行，要事先決定降級範圍，例如關閉推薦、限制非關鍵功能，否則切換只會讓兩個 region 一起倒。第二，資料：訂單、庫存等需要寫入的資料，主節點在哪裡？如果在台灣而台灣整個不可用，東京能不能寫入、會不會有資料不一致；這決定了能切哪些功能。第三，快取與依賴：東京的快取是冷的，切換後資料庫負載會上升；外部金流商等依賴從東京連是否已經設定好。
>
> 執行上我會建議漸進切換，例如每兩分鐘移 20%，同時觀察東京的 latency、錯誤率與 saturation，出現惡化就暫停；切換手段優先用全球入口的權重，DNS 作為輔助並監控殘餘流量。是否切、切多少的決策屬於 incident commander，我的責任是把這些條件與風險清楚地提供給決策者。

> [!question]- Q8. Harbor 想讓 AI 維運 agent 在偵測到某台 backend 異常時，自動把它移出 load balancer。你會怎麼設計 guardrails？
> 移出單台 backend 是相對低風險、而且常常需要快速執行的動作，適合在嚴格的範圍內自動化。我會設的限制包括：一次最多移出一台，且在一段時間內的總數有上限；任何時候保留的健康 backend 不能低於容量計畫要求的 N+1；如果同時有大量 backend 看起來異常，agent 不能逐一移除，而要停止並呼叫人類，因為這更可能是共同依賴或監控本身的問題（和 fail open 是同一個道理）。
>
> 另外，每次動作都要記錄判斷依據（哪些指標、哪些查詢）與預期效果，事後可以審計；移出的 backend 要有自動或人工的恢復流程，避免越移越少；要有一鍵停用 agent 自動操作的開關。導入時先讓 agent 只提出建議、由值班者確認執行，累積一段時間的準確率紀錄後，再逐步放寬到自動執行。

## 延伸閱讀

- [Site Reliability Engineering — Load Balancing at the Frontend](https://sre.google/sre-book/load-balancing-frontend/)：DNS 負載平衡的限制、VIP 背後的網路 load balancer、connection tracking 與 consistent hashing、DSR 與 GRE 封裝。本章 37.6–37.8 依據的第 20 章〈Load Balancing in the Datacenter〉（lame duck、sinkholing、deterministic subsetting 的原始程式）是同一本書的下一章，可從這頁往後讀。
- [Site Reliability Engineering — Handling Overload](https://sre.google/sre-book/handling-overload/)：Load balancing 無法解決的容量不足問題，以及 backend 如何保護自己，銜接第 38 章。
- [Site Reliability Engineering — Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/)：Health check、重試與 load balancing 如何在故障時互相放大，銜接第 39 章。
- [The Site Reliability Workbook — Table of Contents](https://sre.google/workbook/table-of-contents/)：從目錄進入第 11 章〈Managing Load〉，閱讀全球負載平衡、autoscaling 與 load shedding 如何搭配運作的案例。
