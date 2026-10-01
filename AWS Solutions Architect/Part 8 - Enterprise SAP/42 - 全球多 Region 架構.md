---
chapter: 42
title: 全球多 Region 應用與資料架構
part: 8
---

# 第 42 章　全球多 Region 應用與資料架構：流量、寫入路由、一致性與切換

> [!abstract] 本章地圖
> **你會學到**：
> - 分辨「為了延遲」「為了災難復原」「為了資料主權」三種多 Region 需求，知道它們會把架構推往不同、甚至互相衝突的方向
> - 在 active-passive、read-local／write-global、write-local（多寫入）與 home Region 分區之間做選擇，並說清楚每一種的代價
> - 為每一類資料決定一致性等級，再對應到 Aurora Global Database、DynamoDB global tables、S3 CRR／Multi-Region Access Points、ElastiCache Global Datastore
> - 組合 Route 53、Global Accelerator、CloudFront 作為全球入口，並設計 Region 撤離與 failover 的順序
> - 讓另一個 Region「真的開得了機」：multi-Region KMS keys、Secrets Manager replica、設定同步、quota 與分波部署
>
> **前置知識**：第 9 章（Route 53 routing policy）、第 11 章（CloudFront、Global Accelerator）、第 23 章（S3 複寫）、第 26–28 章（Aurora、DynamoDB、ElastiCache）、第 34 章（DR 策略與 ARC）
> **考試比重**：SAA ★★☆（Domain 2 高可用、Domain 3 效能）｜SAP ★★★（Domain 1 可靠架構、Domain 2 業務持續與效能、Domain 3 改善可靠性）

## 42.1 故事：歐洲合作案與「兩邊都能下單」

第 34 章結束時，Wanderly 在新加坡建好了一套 warm standby：東京是唯一服務流量的 Region，新加坡平時只有縮小的運算與一直在接收複寫的資料庫。第 41 章的網路團隊也已經用 Transit Gateway peering 把兩個 Region 接起來。架構看起來很完整，直到業務部帶回一份合約。

一家德國旅遊集團要和 Wanderly 合作，把 Wanderly 的亞洲旅館庫存賣給歐洲客人，條件有三個。第一，歐洲會員的個人資料（姓名、護照號碼、聯絡方式）依合約與該集團的政策，**只能存放與處理在歐盟境內的 Region**。第二，歐洲使用者的搜尋與下單要和亞洲使用者一樣快；他們實測從法蘭克福連到東京，每次 API 往返就要兩百多毫秒，一個要呼叫五次後端的下單流程要等一秒以上。第三，合作夥伴要求任何一個 Region 故障時，服務仍要持續。

產品長在會議上的結論是：「那就每個 Region 都放一套，大家都能讀寫，誰壞了就切走。」技術主管小林在白板上寫下一個問題：「如果東京和法蘭克福同時有人改同一間旅館的剩餘房數，誰說了算？」會議室安靜了下來。

這一章要回答的就是這類問題。多開幾個 Region 的運算資源並不難，困難的是**資料**：哪些資料可以在每個 Region 各寫各的、哪些必須只有一個地方能寫、哪些根本不准離開某個地理範圍，以及當一個 Region 消失時，誰能接手寫入而不讓資料錯亂。

## 42.2 為什麼要多 Region：三個理由，三種不同的架構

多 Region 不是「更高級的高可用」。在同一個 Region 內跨三個 AZ 部署（第 34 章），已經能承受單一資料中心的故障，而且 AZ 之間的延遲通常只有個位數毫秒，資料庫可以同步複寫。一旦跨 Region，距離把延遲拉到數十到數百毫秒，同步複寫變得昂貴，所有設計都要重新考慮。所以第一步是問清楚：**你到底為了什麼需要第二個 Region？**

| 理由 | 真正的需求 | 另一個 Region 平時要做什麼 | 典型架構 |
|---|---|---|---|
| 延遲 | 遠方使用者的讀寫要快 | 服務當地使用者的讀取，甚至寫入 | Active-active，read-local |
| 災難復原 | Region 等級故障時，RTO／RPO 要達標 | 保持資料同步、能在時限內接手 | Active-passive（第 34 章的四種策略） |
| 資料主權 | 某些資料只能存在特定國家或地區 | 保存並處理「屬於當地」的資料，而且資料**不能**複寫出去 | 依地區分區（partition） |

這三種理由會互相拉扯：

- **延遲**希望資料「複製到每個地方」，讓每個 Region 都能就近讀取。
- **災難復原**希望資料「至少有兩份、在不同 Region」。
- **資料主權**卻要求某些資料「只能待在一個地區」，連 DR 副本都只能放在同一個地區內的另一個 Region。

以 Wanderly 的歐洲會員為例，他們的個資不能複寫到東京，所以東京不能是他們的 DR Region；歐盟境內的另一個 Region（例如愛爾蘭 `eu-west-1`）才可以。也就是說，資料主權直接決定了 DR 的拓撲。

### 先問：是不是根本不需要多 Region？

很多「歐洲使用者很慢」的問題，用 CloudFront（第 11 章）就能解決：圖片、前端程式、旅館介紹頁這些可以快取的內容，從法蘭克福的 edge location 提供，延遲就降到數十毫秒。動態 API 也能經 CloudFront 或 Global Accelerator 在最近的 edge 進入 AWS 骨幹網路，減少公共 Internet 的抖動。只有當「每次寫入都要等跨洲往返」本身成為瓶頸，或法規要求資料落地時，才真的需要在當地部署應用與資料。

多 Region 有實際的代價：每個 Region 都要有完整的運算、資料庫與網路；跨 Region 複寫每 GB 都要付資料傳輸費；部署、監控、演練的工作量至少加倍；而最貴的是**應用程式複雜度**，因為開發人員必須開始思考資料在哪裡被寫入、多久之後才會出現在其他地方。

> [!warning] 常見誤解
> 「多 Region 一定比單 Region 可靠。」若第二個 Region 從來沒演練過、設定與主 Region 漂移、或應用程式在寫入衝突時會產生錯誤資料，多 Region 反而增加了故障模式。可靠性來自**被驗證過的**切換能力，而不是 Region 的數量。

## 42.3 多 Region 的四種形狀

確定需要多 Region 之後，下一個決定是各 Region 平時扮演什麼角色。以「誰能讀」與「誰能寫」兩個問題，可以把架構分成四種形狀：

```text
① Active-passive（主備）
   使用者 ──► [Region A：讀＋寫] ══非同步複寫══► [Region B：待命，不接流量]

② Read-local / write-global（就近讀、集中寫）
   A 的使用者 ──讀──► [Region A：primary，讀＋寫]
   B 的使用者 ──讀──► [Region B：唯讀 replica]
                └─寫（跨 Region）─► Region A

③ Write-local（多寫入，multi-active）
   A 的使用者 ──讀寫──► [Region A] ◄══雙向非同步複寫══► [Region B] ◄──讀寫── B 的使用者
                                  （同一筆資料可能兩邊同時被改 → 衝突）

④ Home Region 分區（partitioned）
   亞洲會員 ──讀寫──► [東京：亞洲會員的 owner]
   歐洲會員 ──讀寫──► [法蘭克福：歐洲會員的 owner]
   每筆資料只有一個 owner Region；需要時才把允許的資料複寫出去
```

① **Active-passive**：一個 Region 服務全部流量，另一個 Region 只接收複寫、等待接手。這就是第 34 章的 pilot light 與 warm standby。它最簡單，資料只有一個寫入點，代價是遠方使用者沒有延遲改善，切換時需要一段 RTO。

② **Read-local／write-global**：所有 Region 都服務讀取，寫入集中到一個 primary Region。適合讀遠多於寫的系統，例如旅館目錄、價格查詢。Aurora Global Database 與 ElastiCache Global Datastore 天然就是這個形狀。遠方 Region 的寫入要多付一次跨 Region 往返。

③ **Write-local**：每個 Region 都能寫入任何資料，彼此非同步複寫。延遲最好，也最難：兩個 Region 可能同時修改同一筆資料，必須有衝突解決規則。DynamoDB global tables 的預設模式就是這個形狀。

④ **Home Region 分區**：每筆資料指定一個「擁有它的 Region」，只在那裡寫入。對使用者而言大多數操作都在本地完成（因為他的 home Region 就在附近），又不會有衝突。資料主權需求幾乎都會走到這個形狀。

### 這四種形狀可以混用

一個真實系統很少只用一種形狀。Wanderly 最後的設計是：旅館目錄用 ②，購物車用 ③，會員與訂單用 ④，付款相關的帳務資料用 ① 加上嚴格的單一寫入點。**形狀是依「資料類型」選的，而不是依「整個系統」選的**，42.6 節會把這件事做成一張表。

### Region 獨立性：每個 Region 都要能自己活下去

不論哪種形狀，都有一條共通原則：**一個 Region 在服務請求的路徑上，不應該同步依賴另一個 Region。** 如果法蘭克福每處理一個訂單都要同步呼叫東京的會員服務，那麼東京故障時法蘭克福也會跟著停擺，你等於花了兩倍的錢，換到「任何一邊壞掉都會全倒」的結果。

做法是讓跨 Region 的互動都變成**非同步**：資料以複寫或事件的方式在背景流動，請求路徑上只讀寫本地 Region 的資源。這和第 34 章的 static stability 是同一個精神，只是範圍從 AZ 放大到 Region。

> [!warning] 常見誤解
> 「兩個 Region 各有一組 ALB 與 Auto Scaling group，所以是 active-active。」如果寫入只能送到其中一個 Region、或第二個 Region 讀不到最新的 secret、或事件消費者的處理進度只存在第一個 Region，那它只是兩個 Region 都有機器而已。Active-active 的判斷標準是：**任何一個 Region 消失時，其他 Region 能不能在不做任何變更的情況下繼續服務該有的讀與寫。**

## 42.4 流量層：把使用者送到對的 Region

形狀決定之後，要讓每個請求到達正確的 Region。AWS 有三個全球入口服務，第 9 章與第 11 章分別介紹過它們本身的機制，這裡關心的是：**在多 Region 架構中，它們各自負責哪一段決策。**

### Route 53：用 DNS 決定 Region

Route 53 在 DNS 解析時決定回答哪個 Region 的位址：

- **Latency-based routing**：回答延遲最低的 Region，適合 read-local 的效能需求。
- **Geolocation routing**：依使用者所在國家或洲回答，適合「歐洲使用者連歐洲站」。
- **Failover routing**：primary 不健康時回答 secondary，適合 active-passive。
- 各種政策可以組成一棵記錄樹，每一層搭配 health check 或 evaluate target health（第 9 章）。

DNS 的限制是**快取**：使用者的 resolver 會記住答案直到 TTL 到期，有些用戶端甚至更久。所以 DNS 型的切換時間大約是「health check 偵測時間 + TTL + 用戶端行為」，通常是分鐘等級。

### Global Accelerator：用 anycast IP 決定 Region

Global Accelerator 提供兩個固定的 anycast IP，使用者從最近的 edge 進入 AWS 骨幹網路，再由 accelerator 依 endpoint group 的健康狀態與 **traffic dial**（每個 endpoint group 可設定 0–100% 的流量比例）送到某個 Region。切換發生在 AWS 網路內部，**不受用戶端 DNS 快取影響**，通常在一分鐘內完成。它特別適合：

- 需要快速、可預期的 Region failover。
- 合作夥伴的防火牆只允許固定 IP。
- 要以 traffic dial 逐步把一個 Region 的流量移走（Region 撤離），或把新 Region 從 10% 慢慢加到 100%。

### CloudFront：在 edge 吸收讀取，並選擇 origin

CloudFront 讓可快取的內容根本不必到達任何 Region。對動態請求，它在 edge 終止 TLS，再把請求送到 origin。多 Region 時有兩種常見用法：

- **Origin group（origin failover）**：主要 origin 回應特定錯誤碼或逾時時，改向次要 origin 重試。它只對 GET、HEAD、OPTIONS 生效，適合讀取型內容的 DR，不能保護寫入 API。
- **讓 origin 網域本身指向多個 Region**：把 origin 設為一個 Route 53 latency 記錄的網域，CloudFront 從 edge 解析時會得到離該 edge 最近的 Region；或用 Lambda@Edge 依請求內容（例如 header 或 cookie）改寫 origin（第 11 章）。

### 三者怎麼分工

| 需求 | Route 53 | Global Accelerator | CloudFront |
|---|---|---|---|
| 協定 | 任何（只回答 DNS） | TCP、UDP | HTTP、HTTPS、WebSocket |
| 選 Region 的依據 | 延遲、地理、權重、健康 | 最近的健康 endpoint group、traffic dial | Origin 設定、origin group、Lambda@Edge |
| 切換速度 | 受 TTL 與用戶端快取影響（分鐘級） | 不受 DNS 快取影響（通常一分鐘內） | 每個請求即時重試（僅限 GET／HEAD／OPTIONS） |
| 快取 | 無 | 無 | 有 |
| 固定 IP | 無 | 2 個 anycast IP | 一般情況無 |
| 依使用者屬性路由 | 地理位置、來源 IP 網段 | 無（只看網路位置） | 可依 header、cookie（Lambda@Edge） |

### 資料主權不能只靠流量層

一個很常見的錯誤設計是：「用 Route 53 geolocation 把歐洲使用者導到法蘭克福，所以歐洲資料就留在歐洲了。」geolocation 依的是**查詢來源的位置**，不是使用者的身份：一位歐洲會員出差到東京，他的請求會被送到東京；使用 VPN 或公司代理的使用者，位置判斷也可能失準。

真正可靠的做法是讓**應用層依使用者身份決定 home Region**：會員註冊時就決定他的 home Region，並把它寫進登入權杖（例如 JWT 的一個 claim）。任何 Region 的 API 收到請求時，先看這個 claim；如果請求落在錯的 Region，就把請求轉送到 home Region 的 API，或回應一個重新導向。流量層負責「大多數人進到最近的入口」，應用層負責「資料只在該在的地方被讀寫」。

```text
歐洲會員在東京出差，打開 App 下單
   │ ① DNS（latency）或 Global Accelerator 把他送到最近的入口：東京
   ▼
[東京 API]
   │ ② 讀取 JWT：home_region = eu-central-1
   │ ③ 這筆寫入不屬於東京 → 轉送（或回應 307 重新導向）
   ▼
[法蘭克福 API] ── ④ 在歐盟境內寫入會員與訂單資料
   │
   └─► ⑤ 只把「允許跨區」的資料（例如去識別化的訂單統計、
         旅館庫存扣減事件）非同步送到其他 Region
```

① 入口選擇只追求延遲。② 身份決定資料的歸屬，這個判斷不依賴使用者在哪裡。③ 東京不保存這位會員的個資，只是轉送。④ 個資只在 home Region 寫入。⑤ 跨區流動的資料經過分類，只有允許的部分會離開歐盟。轉送多了一次跨洲往返，但只發生在少數「人在外地」的請求上，這是用延遲換合規的取捨。

## 42.5 寫入路由：write-global、write-local 與 home Region

使用者到達某個 Region 之後，讀取通常在本地完成。真正需要設計的是**寫入要送到哪裡**。這一節把 42.3 節的形狀變成具體的寫入策略。

### Write-global：所有寫入送到一個 primary Region

**Write-global** 指所有寫入都由同一個 primary Region 處理。好處是一致性最單純：只有一個地方在決定「誰先誰後」，資料庫可以使用一般的交易、唯一索引與外鍵。代價有兩個：

1. 遠方 Region 的寫入要多一次跨 Region 往返。從法蘭克福寫到東京，單次寫入就多兩百多毫秒；一個流程有多次寫入時，延遲會累加。
2. Primary Region 故障時，**所有 Region 的寫入都會中斷**，直到完成資料庫提升（Aurora Global Database 的 failover 通常在一分鐘級）。讀取仍可在各 Region 繼續。

實作上有三種送法：

- **應用程式自己送**：每個 Region 的應用程式設定兩組連線，讀用本地 reader endpoint，寫用 primary 的 writer endpoint（Aurora 的 global writer endpoint 會在切換後自動指向新的 primary，第 26 章）。
- **Aurora write forwarding**：應用程式把寫入送到本地 secondary cluster，由 Aurora 轉送到 primary 執行（42.7 節）。
- **API 層轉送**：本地 API 收到寫入請求後，呼叫 primary Region 的寫入 API。

### Write-local：每個 Region 都寫自己的副本

**Write-local** 讓每個 Region 都直接寫入本地副本，再非同步複寫給其他 Region。延遲最低，任何一個 Region 故障，其他 Region 的寫入完全不受影響。代價是**衝突**：同一筆資料在複寫完成前被兩個 Region 修改，兩邊都以為自己成功了，最後必須有規則決定留下哪一個。

DynamoDB global tables 的預設模式（MREC）用 **last writer wins** 解決：時間較晚的寫入覆蓋較早的寫入，被覆蓋的那一次修改就消失了。這對「使用者在兩支手機上同時改購物車」也許可以接受，對「兩個 Region 同時扣同一間房的庫存」就會造成超賣。

### Home Region：每筆資料只有一個寫入點

**Home Region 路由**為每筆資料指定一個 owner Region，所有寫入都送到那裡。它結合了前兩者的優點：

- 對大多數使用者，home Region 就在附近，寫入是本地的。
- 每筆資料同時只有一個寫入點，不會有衝突。
- 資料主權自然被滿足：歐洲會員的 owner 就是歐盟的 Region。

它的難處在於「切換 owner」。當法蘭克福故障，歐洲會員的資料要改由誰來寫？如果法規允許，可以預先讓愛爾蘭成為歐洲會員的備援 owner，並把資料複寫到愛爾蘭；切換時，透過一個集中而高可用的設定（例如 ARC routing control 的狀態，或每個 Region 都有一份的路由表）宣告「歐洲分區的 owner 改為 eu-west-1」。這個宣告必須確保**舊 owner 不再接受寫入**，否則就會出現兩個 owner 同時寫入的**腦裂（split brain）**。

### 跨 Region 重試要有冪等性

不論哪種策略，跨 Region 的網路比 Region 內更容易逾時。用戶端在法蘭克福送出付款請求，轉送到東京時逾時，用戶端重試，結果東京其實已經處理成功，第二次請求又扣了一次款。解法是第 33 章的**冪等鍵（idempotency key）**：每個寫入請求帶一個由用戶端產生的唯一 ID，服務端在處理前先檢查這個 ID 是否已處理過。在多 Region 架構中，這張冪等紀錄表必須和資料本身在同一個 owner Region，才能保證檢查與寫入一致。

> [!tip] 考試提示
> 題目寫「多個 Region 都要低延遲寫入，且同一筆資料不能有衝突」，最常見的正解是「依使用者或租戶指定 home Region，寫入只送到該 Region」，而不是「開啟多寫入再處理衝突」。題目寫「資料只能留在某地區」時，也要想到 home Region 分區。

## 42.6 一致性取捨：你能接受多舊的資料

寫入送到哪裡，決定了「誰說了算」；複寫有多快，決定了「其他 Region 多久之後才知道」。後者就是一致性的問題。

### 為什麼跨 Region 很難同時又快又一致

光在光纖中傳播，從東京到法蘭克福的往返就要上百毫秒，再加上路由與處理，實際往返常在兩百毫秒以上。如果要求「寫入在兩個 Region 都確認後才回應」（同步複寫），每次寫入都要付出這個往返；如果只在本地確認就回應（非同步複寫），寫入很快，但其他 Region 會有一段時間讀到舊資料，而且本地 Region 若在複寫完成前故障，這段資料就遺失了。

這就是分散式系統的基本取捨：**延遲、一致性、在 Region 故障時仍可用，無法同時取到最好。** 大多數 AWS 跨 Region 服務選擇非同步複寫，提供低延遲與高可用，代價是一段很短（通常一秒左右）但不保證為零的不一致期間。少數服務提供跨 Region 強一致的選項（DynamoDB global tables 的 MRSC、Aurora DSQL），代價是寫入延遲較高、功能與 Region 組合有限制。

### 把資料分類，而不是整個系統選一種

小林和各團隊一起把 Wanderly 的資料列成一張表，每一列回答三個問題：讀到幾秒前的資料會怎樣？兩個 Region 同時寫入會怎樣？法規允許它離開哪些地區？

| 資料 | 讀到舊資料的後果 | 同時寫入的後果 | 跨區限制 | 選擇的形狀 | 服務 |
|---|---|---|---|---|---|
| 旅館目錄、照片、介紹 | 幾秒內看到舊介紹，無妨 | 只有後台會寫 | 無 | Read-local／write-global | Aurora Global Database、S3 CRR、CloudFront |
| 搜尋索引 | 可以晚數十秒 | 由事件重建，不直接寫 | 無 | 每個 Region 由本地資料重建 | OpenSearch（各 Region 各一份） |
| 購物車 | 使用者重新整理即可 | 少量覆蓋可接受 | 不含個資時無 | Write-local | DynamoDB global tables（MREC） |
| 會員個資 | 本人看到舊資料會困惑 | 不可遺失修改 | 歐洲會員只能在歐盟 | Home Region 分區 | 各地區各自的 DynamoDB table |
| 訂單 | 本人必須讀到自己剛下的單 | 不可衝突 | 隨會員的 home Region | Home Region 分區 | 同上 |
| 庫存（剩餘房數） | 顯示可以略舊，扣減必須準確 | 絕對不可超賣 | 無 | 單一寫入點 | Aurora Global Database 的 primary |
| Session | 只在本地使用 | 不會跨區寫 | 隨會員 | 每個 Region 本地 | ElastiCache（各 Region 各一份） |

這張表最重要的觀察是：**真正需要「全球單一寫入點」的資料其實很少**（庫存扣減），大多數資料可以就近讀寫或依會員分區。把一致性需求最嚴格的那一小部分隔離出來，其他部分才能享受多 Region 的延遲優勢。

### Read-your-writes：使用者自己的寫入要讀得到

非同步複寫最常見的使用者抱怨是：「我剛改了暱稱，重新整理後又變回舊的。」原因是寫入送到 primary，下一個讀取卻落在還沒收到複寫的 replica。這個需求稱為 **read-your-writes（讀到自己的寫入）**。常見解法：

1. **讓使用者固定讀寫同一個 Region**（home Region 分區天然滿足）。
2. **寫入後的短時間內從 primary 讀取**：應用程式在寫入後的幾秒內，針對該使用者的讀取直接查 primary。
3. **使用資料庫提供的 session 一致性**：例如 Aurora write forwarding 的 `SESSION` 一致性等級，讓同一個連線在 secondary 上一定讀得到自己剛轉送的寫入（42.7 節）。

### 衝突解決的三個方向

當你確實需要 write-local 時，有三種處理衝突的方式，由簡單到困難：

1. **避免衝突**：把「修改同一筆」改成「新增不同筆」。例如會員點數不存「目前餘額」，而是每次增減各寫一筆事件，餘額由彙總計算。不同 Region 新增的是不同 item，不會互相覆蓋。
2. **接受 last writer wins**：只用在覆蓋無害的資料，例如「最後瀏覽的旅館」「偏好語言」。
3. **自訂合併邏輯**：例如購物車的合併取聯集。這需要應用程式自己記錄版本與合併規則，複雜度最高，考試中很少是正確答案。

> [!warning] 常見誤解
> 「DynamoDB 的 strongly consistent read 可以解決 global tables 的衝突。」在 MREC 模式下，strongly consistent read 只保證讀到**本 Region** 最新的寫入，看不到另一個 Region 還在複寫途中的修改，更不能阻止兩邊同時寫入。需要跨 Region 強一致時，要用 MRSC 或單一寫入點。

## 42.7 資料層：每個服務的多 Region 能力

有了資料分類，接著逐一看 AWS 資料服務能提供什麼。第 26–28 章介紹過各服務的基本功能，這裡聚焦在多 Region 設計時要做的決定。

### Aurora Global Database：單一寫入點的全球關聯式資料庫

Aurora Global Database 由一個可寫的 primary Region 與最多 10 個唯讀的 secondary Region 組成，在儲存層非同步複寫，延遲通常不到一秒。設計時要決定四件事：

**一、secondary 要不要有 instance。** Secondary Region 可以只有儲存、沒有 DB instance（headless），平時最省錢，適合純 DR；若要讓當地使用者 read-local，就要在 secondary 放 reader instance。

**二、遠方的寫入怎麼送。** **Write forwarding** 讓 secondary cluster 接受寫入 SQL，由 Aurora 轉送到 primary 執行。它解決了「應用程式要維護兩組連線」的麻煩，並提供可選的讀取一致性等級（以 Aurora MySQL 的 `aurora_replica_read_consistency` 參數為例）：

| 一致性等級 | 意思 | 代價 |
|---|---|---|
| `EVENTUAL` | 寫入轉送後立即回應；接下來的讀取可能還看不到這筆寫入 | 最快 |
| `SESSION` | 同一個 session 的讀取一定看得到自己轉送過的寫入（read-your-writes） | 讀取可能要等待複寫追上 |
| `GLOBAL` | 讀取會等到 secondary 追上 primary 在讀取當下的所有已提交變更 | 最慢 |

Write forwarding 的寫入延遲仍然包含跨 Region 往返，也會占用 primary 的資源，適合「偶爾寫入、主要讀取」的場景，例如會員在 secondary Region 更新偏好設定，不適合大量寫入。

**三、RPO 要不要有硬上限。** 非同步複寫的 RPO 等於當下的複寫延遲，平時一秒以內，但網路異常時可能變長。Aurora PostgreSQL 的 Global Database 可以設定 managed RPO（`rds.global_db_rpo` 參數）：當所有 secondary 的延遲都超過設定秒數時，primary 會暫停接受交易提交，直到至少一個 secondary 追上。這是用「暫時犧牲寫入可用性」換取「保證資料遺失不超過 N 秒」，適合帳務類系統。不論哪種引擎，都應以 CloudWatch 的複寫延遲指標（例如 `AuroraGlobalDBReplicationLag`）設定告警。

**四、怎麼切換。** 計畫內用 **switchover**（不遺失資料、保留全球拓撲），災難時用 **failover**（可能遺失尚未複寫的資料）。兩者都可以用 CLI 執行：

```bash
# 計畫內：把 primary 從東京換到新加坡，等待完全同步，RPO = 0
aws rds switchover-global-cluster \
  --global-cluster-identifier wanderly-catalog-global \
  --target-db-cluster-identifier arn:aws:rds:ap-southeast-1:111122223333:cluster:catalog-sin

# 東京已不可用：接受可能遺失最後幾秒的資料，提升新加坡
aws rds failover-global-cluster \
  --global-cluster-identifier wanderly-catalog-global \
  --target-db-cluster-identifier arn:aws:rds:ap-southeast-1:111122223333:cluster:catalog-sin \
  --allow-data-loss
```

`--allow-data-loss` 這個參數本身就是提醒：failover 是在明知可能遺失資料的情況下做出的決定，應該由 runbook 清楚規定誰有權執行。

> [!note] 需要多 Region 同時寫入的關聯式資料庫
> Aurora Global Database 只有一個寫入 Region。AWS 另外提供 **Aurora DSQL**：一個 serverless、相容 PostgreSQL 的分散式 SQL 資料庫，multi-Region cluster 讓兩個 Region 都能讀寫並維持強一致（另需一個 witness Region），以 optimistic concurrency control 處理並行交易。它不支援完整的 PostgreSQL 功能，遷移既有應用前要確認相容性。對考試而言，「關聯式＋單一寫入 Region＋秒級 RPO」仍以 Aurora Global Database 為標準答案。

### DynamoDB global tables：多寫入的 key-value 資料

Global tables 讓每個 replica 都可讀寫。多 Region 設計時的關鍵決定：

- **MREC 還是 MRSC**：MREC（預設）寫入在本地確認，非同步複寫，衝突以 last writer wins 解決，可以部署在任意數量的支援 Region。MRSC 寫入要同步確認後才回應，RPO 為零、任何 Region 的 strongly consistent read 都讀得到最新資料，但必須**剛好三個 Region**（三個 replica，或兩個 replica 加一個 witness；witness 由 DynamoDB 管理，不能讀寫），只能選擇支援 MRSC 的 Region，且**不支援 transactions**、TTL 與 LSI。MRSC 只能在建立時（從空的 table）設定，之後不能加入更多 replica；兩個 Region 同時修改同一個 item 時，其中一方會收到 `ReplicatedWriteConflictException`，重試即可。
- **交易的範圍**：即使在 MREC 模式，`TransactWriteItems` 也只在發起它的 Region 內具有 ACID 保證；另一個 Region 會以一般的複寫看到結果，可能看到交易的部分 item 先到。需要跨 Region 交易語意的流程，應該讓該流程只在一個 Region 執行。
- **整張 table 都會複寫**：global tables 沒有「只複寫部分 item」的過濾機制。Wanderly 若把歐洲會員和亞洲會員放在同一張 global table，再加一個東京 replica，歐洲個資就會被複寫到東京。所以資料主權的分區必須體現在**table 層級**：歐洲會員一張 table（replica 只在 `eu-central-1` 與 `eu-west-1`），亞洲會員另一張 table（replica 在東京與新加坡）。
- **備份與誤刪**：global tables 會把錯誤的寫入與刪除同樣複製到所有 Region，仍要開 PITR 或使用 AWS Backup（第 34 章）。
- **Streams 是每個 Region 各自的**：每個 replica 都有自己的 stream，如果每個 Region 都掛同一個 Lambda 處理「訂單建立」事件，同一筆訂單可能在每個 Region 都被處理一次。常見做法是只讓 owner Region 的消費者處理業務事件，或在消費者中檢查該 item 的 owner Region。

### S3：CRR 與 Multi-Region Access Points

第 23 章介紹過 S3 Replication 的規則與限制。多 Region 應用要再多考慮兩件事。

**雙向複寫。** Active-active 時，兩個 Region 的應用程式都會寫入自己附近的 bucket，所以要設定兩個方向的複寫規則，並開啟 **replica modification sync**，讓副本上的 metadata 變更（例如 tag、Object Lock 設定）也能同步回去。S3 物件的「衝突」也是以較新的寫入為準，所以同一個 key 最好只有一個 Region 會寫，例如在 key 中加入 Region 前綴或使用唯一 ID。

**單一全球入口。** **S3 Multi-Region Access Points（MRAP）** 提供一個全球的 endpoint，背後連到多個 Region 的 bucket：

- 請求經由 Global Accelerator 的網路，被送到延遲最低、且狀態為 active 的 bucket。
- **Failover controls**：每個 bucket 可以設為 active 或 passive。Active-passive 時，平時只有 active bucket 接收請求；把 active 改為 passive、passive 改為 active，就能在幾分鐘內把所有請求移到另一個 Region，應用程式不需要改任何設定。
- MRAP **本身不複製資料**，必須另外設定 bucket 之間的複寫規則；複寫是非同步的，切換到另一個 Region 時，最近寫入的物件可能還沒複寫過去（需要可預期的延遲時，開啟 RTC，第 23 章）。
- 用戶端必須用 **SigV4A**（支援多 Region 的簽章演算法）簽署請求，目前的 AWS SDK 與 CLI 都支援。
- 除了一般的 S3 費用，經 MRAP 的請求另有資料路由費，跨 Region 存取還有傳輸費。

適合的場景是「應用程式在多個 Region，要用同一個名稱存取物件，並在 Region 故障時切換」。如果只是 DR 副本、平時沒有應用程式讀取，一般的 CRR 就夠了。

### ElastiCache Global Datastore：就近讀取的快取

Global Datastore 讓一個 node-based 的 Valkey 或 Redis OSS primary cluster 把資料非同步複寫到其他 Region 的 secondary cluster（最多兩個 secondary Region），secondary 只能讀，primary Region 故障時可以提升某個 secondary。它是 read-local／write-global 的快取版本，適合「全球都要讀的熱門資料」，例如熱門旅館排行榜。

另一個選擇是**每個 Region 各自的獨立快取**，各自從本地資料庫副本載入（第 28 章）。對 session 這類只在本地使用的資料，或對「切換時希望 Region 之間沒有任何依賴」的系統，獨立快取比 Global Datastore 更簡單。

### 其他元件

| 元件 | 跨 Region 能力 | 多 Region 設計要點 |
|---|---|---|
| SQS、SNS | 沒有內建跨 Region 複寫 | 每個 Region 各自的 queue；producer 寫本地 queue。Region 故障時，未處理的訊息會留在該 Region，要靠冪等與補償處理 |
| EventBridge | Global endpoints（主備 Region，依 Route 53 health check 切換）、跨 Region 事件轉送 | 讓事件發布不因單一 Region 故障而中斷（第 32 章） |
| Kinesis Data Streams | 沒有內建跨 Region 複寫 | 用消費者轉寫到另一個 Region，或 producer 雙寫；MSK 可用 MSK Replicator（第 31 章） |
| OpenSearch | Cross-cluster replication | 常見做法是在每個 Region 由本地資料重建索引，減少跨 Region 依賴 |
| DocumentDB、Neptune | Global clusters／global database，一個寫入 Region | 與 Aurora Global Database 同樣是單一寫入點（第 29 章） |

## 42.8 金鑰、機密與設定：讓另一個 Region 真的開得了機

資料複寫過去了，不代表另一個 Region 能用它。Region 演練最常見的失敗不是資料庫，而是「應用程式啟動後打不開資料、讀不到密碼、拉不到 image」。這一節處理這些「讓 Region 能開機」的依賴。

### Multi-Region KMS keys：什麼時候需要、什麼時候不需要

KMS key 預設只存在一個 Region。第 15 章說明過 **multi-Region key** 是一組在不同 Region 擁有相同 key ID 與金鑰材料的 key。判斷是否需要它，只要問一句：**密文是由誰解密的？**

- **由 AWS 服務在目的 Region 重新加密**：S3 CRR、Aurora Global Database、DynamoDB global tables 的伺服器端加密、AWS Backup 的跨 Region copy，服務會用目的 Region 的 key 處理，**一般的單 Region key 就夠了**。
- **由你的應用程式解密**：例如應用程式先用 KMS 對護照號碼做欄位層級加密，再寫進 DynamoDB global table。密文原封不動地被複寫到新加坡，新加坡的應用程式要解密，就需要同一份金鑰材料。這時用 multi-Region key，新加坡可以呼叫本地的 replica key 解密，不必跨 Region 呼叫東京。

建立方式是在 primary Region 建立 multi-Region key，再複製到其他 Region：

```bash
aws kms create-key --multi-region \
  --description "wanderly member PII field encryption (APAC)" \
  --region ap-northeast-1

aws kms replicate-key \
  --key-id mrk-1234abcd12ab34cd56ef1234567890ab \
  --replica-region ap-southeast-1 \
  --region ap-northeast-1
```

要記得：key policy、alias、grant、啟用狀態**不會**在 primary 與 replica 之間同步，每個 Region 要分別管理；primary 所在的 Region 故障時，可以把某個 replica 更新為新的 primary（`UpdatePrimaryRegion`）。資料主權也適用在這裡：歐洲會員的欄位加密 key，replica 只能建立在歐盟的 Region。

### Secrets Manager replica：密碼在每個 Region 都要有

應用程式啟動時要讀資料庫密碼、第三方 API key。如果 secret 只在東京，東京故障時新加坡就讀不到。**Replica secret** 讓 secret 自動同步到其他 Region：

```bash
aws secretsmanager replicate-secret-to-regions \
  --secret-id prod/booking/db \
  --add-replica-regions Region=ap-southeast-1,KmsKeyId=alias/booking-secrets \
  --region ap-northeast-1
```

輪替只在 primary secret 上執行，完成後 replica 會自動更新；replica 本身是唯讀的。東京長期不可用時，可以把新加坡的 replica **提升為獨立的 secret**，之後在新加坡設定輪替。要注意，Aurora Global Database failover 後，新 primary 的連線位址與原本不同；若應用程式使用 global writer endpoint，就不必改 secret 中的主機名稱。另外，RDS 的「由 Secrets Manager 管理 master user 密碼」整合功能不支援 Aurora Global Database（加入 secondary Region 前必須先關閉），所以 global database 的密碼要以一般 secret 自行管理、輪替並複寫。

### 其他每個 Region 都要準備的東西

| 依賴 | 為什麼會出問題 | 做法 |
|---|---|---|
| Parameter Store | 沒有內建跨 Region 複寫 | 由 IaC 或部署 pipeline 在每個 Region 寫入相同參數；變動頻繁的設定改用每個 Region 各自的 AppConfig |
| AMI、container image | 是 Regional 資源 | AMI copy、ECR replication（第 34 章） |
| ACM 憑證 | 是 Regional 資源 | 在每個 Region 為 ALB 申請憑證；CloudFront 用的憑證在 `us-east-1` |
| Service quotas | 每個 Region、每個帳號分開計算 | 事先把 DR／active Region 的 quota 提高到能承受全部流量；新帳號可用 Service Quotas 的 quota request template 自動申請 |
| STS | SDK 與 CLI 預設可能使用全域端點 `sts.amazonaws.com`，它依賴 `us-east-1` | 應用程式設定為使用 Regional STS endpoint（MRAP 的 SigV4A 也需要 Regional endpoint 取得的臨時憑證） |
| 第三方允許清單 | 金流商只允許東京 NAT Gateway 的 EIP | 事先把每個 Region 的出口 IP 都登記 |
| IAM | 全域服務，變更由單一 Region 的 control plane 處理 | 在平時就建立好所有 Region 需要的 role，不在事故中修改 IAM |
| Cognito user pool | 是 Regional 資源，會員登入與發 token 都依賴它 | 啟用 multi-Region replication，在另一個 Region 建立 secondary replica user pool；前提是 Essentials 或 Plus 方案、以 KMS multi-Region key 加密、且 user pool 符合啟用條件。只能有一個 secondary，secondary 不能註冊新使用者、重設密碼或修改個人資料，使用 TOTP MFA 的使用者也無法在 secondary 登入，DR runbook 要寫明切換期間暫停這些功能（第 53 章） |

> [!tip] 考試提示
> 「failover 演練時，資料庫已經切過去，但應用程式無法解密資料／讀不到 secret／無法擴充」是 SAP 的經典題型。答案通常是一組「事先在目的 Region 準備好」的動作：multi-Region key（只在應用層加密時需要）、Secrets Manager replica、ECR replication、提高 quota，而不是在事故時才去建立。

## 42.9 部署與設定同步：同一份版本，分批到每個 Region

多 Region 最隱蔽的風險是**漂移（drift）**：東京上週改了 security group，新加坡忘了改；東京的應用是 v2.3，法蘭克福還停在 v2.1。平時沒人發現，切換那天才爆發。解法是讓每個 Region 的環境都由同一份 IaC 與 pipeline 產生，而且**有順序地**部署。

### 用 IaC 產生每個 Region 的環境

- **CloudFormation StackSets** 可以把同一份 template 部署到多個帳號與多個 Region，並以 operation preferences 控制順序：`RegionOrder` 決定先後、`MaxConcurrentCount` 控制同時部署幾個目標、`FailureToleranceCount` 決定失敗幾個就停止（第 37 章）。
- **CDK** 或 Terraform 以「每個 Region 一個 stack／一組 provider」的方式描述，Region 差異（CIDR、Region 代號、容量）放在參數檔中，而不是複製一份程式碼再修改。
- Region 專屬的位址由 IPAM 的 Regional pool 分配（第 5 章），保證不同 Region 的 VPC 不重疊，TGW peering 的路由才能彙總。依第 5 章的位址規劃，東京是 `10.16.0.0/12`、新加坡是 `10.32.0.0/12`，法蘭克福與愛爾蘭則從 `10.48.0.0/12` 起各分配一個 `/12`；每個 Region 一個 `/12`，跨 Region 的路由表只需要一條彙總路由。

### 分波部署：不要一次更新所有 Region

如果一個有 bug 的版本同時部署到三個 Region，多 Region 帶來的保護就消失了：三個 Region 會同時故障。正確的做法是**分波（waves）**：

```text
 build ──► ① 測試帳號（單一 Region）
            │  整合測試、合成測試通過
            ▼
          ② 第一個 production Region（流量最小的，例如新加坡）
            │  bake time 1 小時：alarm、錯誤率、延遲都正常
            ▼
          ③ 第二個 production Region（法蘭克福）
            │  bake time 1 小時
            ▼
          ④ 最大的 Region（東京）
   任何一波的 alarm 觸發 → 自動停止 pipeline 並回滾該波
```

① 先在非 production 驗證。② 第一個 production Region 選流量最小的，讓壞版本的影響最小。每一波之間的 **bake time（烘烤時間）** 讓問題有時間浮現。③④ 確認後再擴大。CodePipeline 支援 cross-Region actions，可以在同一條 pipeline 中依序部署到各 Region，每一波搭配 CloudWatch alarm 作為自動回滾條件。

### 設定與功能旗標也要分波

程式碼以外的變更同樣危險：調整逾時參數、打開一個新功能旗標，都可能讓所有 Region 同時出錯。**AWS AppConfig** 是 Regional 服務，每個 Region 各有一份設定，搭配部署策略（逐步推出並在 alarm 觸發時自動回滾），就能讓設定變更也遵守分波原則。

### 每個 Region 都要看得見

多 Region 的監控要回答兩個問題：「每個 Region 自己健不健康？」以及「整體使用者體驗如何？」做法是在每個 Region 部署 **CloudWatch Synthetics canary**，從使用者角度定期執行登入、搜尋、下單；並用 CloudWatch 的跨帳號、跨 Region 觀測功能建立一個總覽儀表板。注意監控本身也不能只放在一個 Region：如果所有 alarm 都在東京，東京故障時你連「東京故障了」都收不到。

## 42.10 切換：Region 撤離與 failover 的順序

第 34 章介紹了 ARC 的 routing control、safety rules 與 Region switch。這一節從 active-active 與 home Region 架構的角度，看切換時要依序做什麼。

### 容量：存活的 Region 能不能吃下全部流量

Active-active 最常被忽略的問題是容量。假設 Wanderly 在兩個 Region 各服務一半流量，每個 Region 的使用率是 70%；當其中一個 Region 撤離，另一個 Region 要承受 140%，結果是兩個 Region 都倒下。

計算方式和第 34 章的 AZ 容量規劃一樣，只是單位從 AZ 換成 Region：有 N 個 Region、要能承受失去 1 個時，每個 Region 平時的使用率上限約為 (N−1)／N。

| Region 數 | 失去一個後剩下 | 每個 Region 平時使用率上限 |
|---|---|---|
| 2 | 1 | 50% |
| 3 | 2 | 約 66% |
| 4 | 3 | 75% |

這也是為什麼很多企業的 active-active 最後選擇三個 Region：比兩個 Region 浪費的閒置容量少。若靠 Auto Scaling 在切換當下擴充，則要確認擴充速度、quota 與下游資料庫的承受能力，並把「擴充所需時間」算進 RTO。

### Active-active 的 Region 撤離

在 active-active 中，「切換」其實是**撤離（evacuation）**：停止把流量送往有問題的 Region。

1. **決定撤離**：依 synthetics、錯誤率等指標，由值班人員判斷（或依預先定義的條件自動觸發）。
2. **移走流量**：ARC routing control 把該 Region 的開關關掉，讓 Route 53 不再回答它；這是 data plane 操作，不需要修改 DNS 記錄，適合在事故中使用。Global Accelerator 的 traffic dial 也能把該 Region 調為 0%，但調整 traffic dial 是對 Global Accelerator control plane（位於 `us-west-2`）的設定變更，AWS 建議事故中的復原路徑不要依賴它；traffic dial 最適合計畫內的維護與逐步移轉。至於 endpoint 不健康時由 health check 觸發的自動移轉，則屬於 data plane，不需要任何設定變更。
3. **處理該 Region 擁有的資料**：若該 Region 是某些資料的唯一寫入點（例如 Aurora primary、某個分區的 home Region），就要進入下一小節的 failover 流程；若只有 write-local 的資料（global tables MREC），其他 Region 本來就能寫，撤離到此完成。
4. **確認存活 Region 的容量**，必要時擴充。

### 單一寫入點的 failover：順序決定會不會腦裂

當故障的 Region 擁有寫入權，切換順序非常重要：

```text
 ① 圍欄（fence）：讓舊 primary 停止接受寫入
    （ARC routing control 關閉、應用程式讀到「本分區唯讀」的旗標）
        │
        ▼
 ② 確認資料狀態：看複寫延遲，決定用 switchover（可等同步）或 failover（接受遺失）
        │
        ▼
 ③ 提升資料庫：Aurora failover／switchover、ElastiCache 提升 secondary
        │
        ▼
 ④ 擴充新 primary Region 的運算，確認 secret、key、quota 就緒
        │
        ▼
 ⑤ 移動寫入流量：更新分區 owner、ARC routing control 打開新 Region
        │
        ▼
 ⑥ 驗證業務：以合成交易確認可以下單、付款，再對外宣告恢復
```

① 圍欄是避免腦裂的關鍵：如果舊 primary 其實只是網路暫時不通，恢復後又開始接受寫入，兩邊就同時成為 primary。② 依 RPO 要求選擇切換方式。③ 先提升資料庫，④ 再準備運算，⑤ 最後才移動流量：順序反過來的話，使用者會在資料庫還是唯讀時被送過去，看到的只有錯誤。⑥ 以業務指標而不是基礎設施指標判斷完成。ARC 的 **Region switch** 可以把這些步驟寫成一個計畫並依序執行；ARC 的 readiness check 已不再開放給新客戶，新環境改用 Region switch 的 plan evaluation 定期檢查計畫是否可執行。

**Failback** 是反向的同一套流程，而且通常更難：故障期間新寫入的資料都在新 Region，要先讓原 Region 重新加入複寫、完全追上，再用計畫內的 switchover 搬回去。

## 42.11 組起來：Wanderly 的全球架構

把前面的決定組合起來，Wanderly 的全球架構如下：

```text
                      亞洲使用者                    歐洲使用者
                          │                             │
              ┌───────────┴────────── ① ────────────────┴───────────┐
              │  CloudFront（靜態內容、edge 快取、WAF）                 │
              │  Global Accelerator（API，2 個 anycast IP，traffic dial）│
              └──────┬──────────────────┬──────────────────┬────────┘
                     ▼                  ▼                  ▼
          ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
          │ 東京 ap-northeast-1│ │新加坡 ap-southeast-1│ │法蘭克福 eu-central-1│
          │ ② API（讀 JWT     │ │ API              │ │ API              │
          │   home_region）  │ │                  │ │                  │
          │ ③ Aurora primary │ │ Aurora secondary │ │ Aurora secondary │
          │   （目錄、庫存）   │◄┼═ 儲存層複寫 ═══►│ │（目錄唯讀）        │
          │ ④ DDB 亞洲會員/訂單 │◄┼═ global table ═►│ │ ④ DDB 歐洲會員/訂單 │
          │                  │ │                  │ │   ══► eu-west-1   │
          │ ⑤ DDB 購物車 ◄═══╪═╪═ global table ══╪═╪═══► DDB 購物車     │
          │ ⑥ 本地 ElastiCache │ │ 本地 ElastiCache │ │ 本地 ElastiCache   │
          │ ⑦ S3 照片（CRR）   │ │ S3 照片（CRR）    │ │ S3 照片（CRR）     │
          └─────────────────┘ └─────────────────┘ └─────────────────┘
           ⑧ ARC routing control／Region switch：撤離與 failover 計畫
```

① 入口層：CloudFront 吸收所有可快取的讀取並套用 WAF；API 走 Global Accelerator，三個 Region 各一個 endpoint group，平時依網路位置就近分配。② 每個 Region 的 API 先讀登入權杖中的 home Region，個資相關的請求只在 home Region 處理，落在錯誤 Region 時轉送。③ 旅館目錄與庫存是 read-local／write-global：Aurora Global Database 的 primary 在東京，新加坡與法蘭克福有 reader 服務當地查詢；扣庫存一律送到 primary，接受跨洲寫入延遲，換取不超賣。旅館目錄與庫存不含個資，複寫到法蘭克福沒有主權問題。④ 會員與訂單依 home Region 分區：亞洲會員的 global table 只有東京與新加坡兩個 replica，歐洲會員的 global table 只有法蘭克福與愛爾蘭兩個 replica。⑤ 購物車只存旅館與日期（不含個資），用一張三個 Region 的 MREC global table，接受 last writer wins。⑥ 快取每個 Region 各自獨立，切換時沒有跨 Region 依賴。⑦ 旅館照片以 CRR 複寫到各 Region，主要由 CloudFront 提供。⑧ 撤離與 failover 由 ARC 管理，順序依 42.10 節。

這個架構裡，「東京故障」的影響是：亞洲會員改由新加坡服務（global table 本來就可寫）；庫存扣減要等 Aurora 提升新加坡為 primary（約一分鐘級，期間只能瀏覽不能下單）；歐洲會員幾乎不受影響，只有扣庫存會短暫中斷。「法蘭克福故障」時，歐洲會員的分區 owner 切到愛爾蘭，資料始終留在歐盟。

## 42.12 比較與選型

### 多 Region 形狀選擇

| 形狀 | 寫入延遲（遠方 Region） | 衝突 | Region 故障時的寫入 | 資料主權 | 典型服務 |
|---|---|---|---|---|---|
| Active-passive | 不適用（只服務一地） | 無 | 要 failover，RTO 分鐘級以上 | 備援要在允許的地區 | 第 34 章各策略 |
| Read-local／write-global | 跨 Region 往返 | 無 | 要提升 secondary | 所有副本都在各 Region | Aurora Global Database、Global Datastore |
| Write-local | 本地 | 有，要設計解決 | 其他 Region 不受影響 | 整份資料都會複寫 | DynamoDB global tables MREC、S3 雙向 CRR |
| Write-local 強一致 | 同步確認，較高 | 由服務處理（寫入可能失敗重試） | 其他 Region 不受影響 | 整份資料都會複寫 | DynamoDB MRSC、Aurora DSQL |
| Home Region 分區 | 大多本地 | 無 | 該分區要切換 owner | 天然滿足 | 各分區各自的資料庫 |

### 選型流程

```text
這份資料可以離開它的地區嗎？
├─ 不行 → 依地區分區（home Region），DR 副本只放在同地區的另一個 Region
└─ 可以 → 兩個 Region 同時修改同一筆時，覆蓋可以接受嗎？
           ├─ 可以（購物車、偏好設定）→ Write-local：DynamoDB global tables（MREC）
           └─ 不行 → 需要多個 Region 都能低延遲寫入嗎？
                      ├─ 是 → 能依使用者或租戶分區嗎？
                      │        ├─ 能 → Home Region 分區
                      │        └─ 不能 → 跨 Region 強一致：MRSC（三個 Region、無交易）
                      │                   或 Aurora DSQL，接受較高的寫入延遲
                      └─ 否（讀多寫少）→ Read-local／write-global：
                                         Aurora Global Database（關聯式）、
                                         Global Datastore（快取）
```

### 流量入口選擇

| 題目需求 | 選擇 |
|---|---|
| 可快取內容、全球使用者、WAF | CloudFront |
| 多 Region 依延遲分流、active-active、成本最低 | Route 53 latency + health check |
| 依國家顯示不同內容或導到不同站 | Route 53 geolocation（不能單獨作為資料主權的保證） |
| 固定 IP、TCP/UDP、不受 DNS 快取影響的快速切換 | Global Accelerator |
| 逐步把流量移入或移出某個 Region | Global Accelerator traffic dial；或 Route 53 weighted |
| 人工決定、不依賴 control plane 的 Region 切換 | ARC routing control（加 safety rules） |
| 多步驟的 Region 切換計畫 | ARC Region switch |

## 42.13 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 遠方使用者載入慢，內容大多是靜態圖片與頁面 | 先用 CloudFront，不一定需要多 Region |
| 多 Region 都要低延遲讀寫、Region 故障不影響其他 Region | DynamoDB global tables |
| 同一筆資料可能被兩個 Region 同時修改，不能遺失 | Home Region 路由、改成 append 事件，或 MRSC |
| 跨 Region 強一致、RPO 為零的 key-value 資料 | DynamoDB MRSC（剛好三個 Region、不支援 transactions） |
| 關聯式、讀多寫少、遠方 Region 秒級延遲讀取 | Aurora Global Database + secondary reader |
| secondary Region 的應用程式偶爾要寫入，不想管兩組連線 | Aurora write forwarding（需要 read-your-writes 時用 `SESSION`） |
| 計畫內 Region 輪替且不能遺失資料 | Aurora switchover；災難時才用 failover |
| 多 Region 用同一個名稱存取 S3、可切換 | S3 Multi-Region Access Points + 複寫規則 + failover controls |
| 全球熱門資料的低延遲讀取快取 | ElastiCache Global Datastore（只有 primary 可寫） |
| 應用層加密的資料要在 DR Region 解密 | KMS multi-Region key |
| DR Region 讀不到資料庫密碼 | Secrets Manager replica secret |
| 固定 IP、快速 failover、不受 DNS 快取影響 | Global Accelerator |
| 歐洲個資只能在歐盟 | 依地區分區的 table／資料庫，應用層依身份路由；不是只靠 geolocation |
| 新版本不能同時讓所有 Region 故障 | 分波部署 + bake time + alarm 自動回滾 |

**常見陷阱**：

1. 以為 Aurora write forwarding 讓每個 Region 都成為寫入點：寫入仍在 primary 執行，primary Region 故障時寫入照樣中斷。
2. 以為 global tables 可以只複寫部分資料：它複寫整張 table，資料主權要靠拆 table。
3. 以為 MREC 的 strongly consistent read 能防止衝突：它只保證本 Region 的最新資料。
4. 以為 S3 Multi-Region Access Points 會自動複製資料：複寫規則要另外設定。
5. 以為所有跨 Region 複寫都需要 multi-Region KMS key：只有應用程式自己解密跨 Region 的密文時才需要。
6. Active-active 卻讓每個 Region 平時跑到 70% 以上：失去一個 Region 時剩下的 Region 承受不住。
7. 先切流量再提升資料庫：使用者會被送到仍是唯讀的 Region。

> [!note] 延伸閱讀
> - [Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)
> - [Aurora Global Database 的 write forwarding](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-write-forwarding.html)
> - [DynamoDB global tables](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html)
> - [KMS multi-Region keys](https://docs.aws.amazon.com/kms/latest/developerguide/multi-region-keys-overview.html)
> - [Secrets Manager 跨 Region 複寫](https://docs.aws.amazon.com/secretsmanager/latest/userguide/replicate-secrets.html)
> - [Global Accelerator traffic dial](https://docs.aws.amazon.com/global-accelerator/latest/dg/about-endpoint-groups-traffic-dial.html)
> - [ARC routing control](https://docs.aws.amazon.com/r53recovery/latest/dg/routing-control.html)

## 本章重點整理

- 多 Region 有三種理由：延遲、災難復原、資料主權；三者會互相拉扯，資料主權甚至會決定 DR 副本能放在哪裡。
- 在決定多 Region 之前，先確認 CloudFront 或 Global Accelerator 能否以單 Region 解決延遲問題，因為多 Region 會讓成本與應用複雜度大幅上升。
- 多 Region 有四種形狀：active-passive、read-local／write-global、write-local、home Region 分區；形狀應依「資料類型」選擇，一個系統常常混用。
- Region 在服務請求時不應同步依賴另一個 Region，跨 Region 的互動應該是非同步的複寫或事件。
- Write-global 一致性最簡單，但遠方寫入多一次跨 Region 往返，primary Region 故障時所有寫入都會中斷。
- Write-local 延遲最低但會有衝突；DynamoDB global tables 的 MREC 以 last writer wins 解決，不適合庫存、餘額這類不能遺失修改的資料。
- Home Region 分區讓每筆資料只有一個寫入點，同時滿足低延遲、無衝突與資料主權；切換 owner 時必須先圍欄舊 owner，避免腦裂。
- 資料主權不能只靠 Route 53 geolocation，應由應用層依使用者身份決定 home Region。
- Aurora Global Database 最多 10 個 secondary Region、只有一個寫入 Region；write forwarding 提供 EVENTUAL、SESSION、GLOBAL 三種讀取一致性，計畫內用 switchover，災難時用 failover。
- DynamoDB global tables 會複寫整張 table；MRSC 提供跨 Region 強一致，但必須剛好三個 Region，且不支援 transactions、TTL 與 LSI。
- S3 Multi-Region Access Points 提供單一全球入口與 active／passive failover controls，但資料要靠另外設定的複寫規則同步。
- Multi-Region KMS key 只在應用程式自己解密跨 Region 複寫的密文時需要；Secrets Manager replica、ECR replication、quota、憑證也都要在目的 Region 事先準備。
- 多 Region 部署要分波進行，每一波之間有 bake time 與 alarm 回滾；設定與功能旗標也要分波。
- Active-active 要能承受失去一個 Region，N 個 Region 時每個 Region 平時使用率上限約為 (N−1)／N。
- 單一寫入點的 failover 順序是：圍欄舊 primary → 確認資料狀態 → 提升資料庫 → 擴充運算 → 移動流量 → 以業務指標驗證。

## 本章練習題

### 練習 42-1｜SAA｜單選｜遠方使用者的延遲

Wanderly 的網站全部部署在東京 Region。歐洲使用者抱怨首頁與旅館介紹頁載入很慢，分析後發現 85% 的回應時間花在下載旅館照片、前端程式與很少變動的介紹頁 HTML。下單 API 的延遲目前可以接受。公司希望以最低的成本與營運負擔改善歐洲使用者的體驗。

最合適的做法是什麼？

- A. 在法蘭克福 Region 部署完整的應用程式與 Aurora Global Database 的 secondary cluster，並用 Route 53 latency routing 分流
- B. 在既有架構前面加上 CloudFront，讓照片、前端檔案與介紹頁從 edge location 快取提供
- C. 把 S3 照片以 Cross-Region Replication 複寫到法蘭克福，讓歐洲使用者直接從法蘭克福的 bucket 下載
- D. 為 API 建立 Global Accelerator，讓歐洲使用者從最近的 edge 進入 AWS 骨幹網路

> [!answer]- 答案：B
> **A ✗** 部署第二個 Region 能改善延遲，但成本與營運負擔都很高，而題目的瓶頸是可快取的靜態內容，下單 API 延遲本來就可以接受。當題目要求寫入也要在當地低延遲，或有資料落地要求時，這才會是合理選項。
>
> **B ✓** 瓶頸是可快取的內容。CloudFront 從靠近使用者的 edge location 提供照片、前端與很少變動的 HTML，不需要新增任何 Region，成本與營運負擔最低。
>
> **C ✗** CRR 只解決照片，而且使用者仍要連到法蘭克福的 bucket，沒有 edge 快取，也沒有處理前端與 HTML；還要多付一份儲存與複寫費用。
>
> **D ✗** Global Accelerator 改善 TCP 連線品質，但不快取任何內容，每次下載照片仍要回到東京。
>
> **考點**：SAA-3.4、SAA-4.4｜先用 CloudFront 解決可快取內容的全球延遲

### 練習 42-2｜SAP｜單選｜多 Region 寫入且無衝突

Wanderly 在東京、新加坡、法蘭克福三個 Region 提供訂單服務。每位會員的訂單都可能被修改（變更日期、取消），同一筆訂單絕對不能因為兩個 Region 同時修改而遺失變更。產品要求絕大多數會員的下單與修改都能在本地 Region 完成，Region 故障時其他 Region 的會員不受影響。訂單資料目前存在 DynamoDB。

哪個設計最能滿足需求？

- A. 把訂單 table 改為三個 Region 的 global table（MREC），並讓應用程式改用 strongly consistent read 避免衝突
- B. 把訂單 table 留在東京，其他 Region 的應用程式以 VPC 跨 Region 連線存取東京的 table
- C. 依會員註冊地決定 home Region，並寫入登入權杖；所有訂單寫入只送到該會員的 home Region，其他 Region 收到時轉送
- D. 使用 global table，並讓每個 Region 的 Lambda 透過 DynamoDB Streams 比較兩個版本，以較大的金額為準合併衝突

> [!answer]- 答案：C
> **A ✗** MREC 以 last writer wins 解決衝突，被覆蓋的修改就消失了。Strongly consistent read 只保證讀到本 Region 的最新寫入，無法阻止另一個 Region 同時寫入同一筆訂單。
>
> **B ✗** 所有 Region 的寫入都跨 Region 到東京，不符合「本地完成」；東京故障時所有 Region 都無法寫入。
>
> **C ✓** Home Region 分區讓每筆訂單只有一個寫入點，不會有衝突；會員通常在自己 home Region 附近，大多數寫入都是本地的；某個 Region 故障只影響以它為 home 的會員，其他 Region 不受影響。
>
> **D ✗** 事後以 Streams 合併衝突既複雜又容易出錯，「取較大金額」也不是正確的業務規則；衝突在合併前已經被使用者看到。
>
> **考點**：SAP-1.3、SAP-2.4｜home Region 寫入路由避免多 Region 衝突

### 練習 42-3｜SAP｜選兩項｜會員點數的衝突

Wanderly 的會員點數存在一張橫跨東京與新加坡的 DynamoDB global table（MREC），每個會員一個 item，其中有 `balance` 屬性。會員在東京訂房時加點、同時在新加坡兌換點數，事後發現餘額有時會少算一次異動。團隊希望修正問題，並保留兩個 Region 都能接受點數異動的能力。

哪兩個做法能解決問題？（選兩項）

- A. 把每次點數異動寫成獨立的 item（例如以異動 ID 為 sort key），餘額由彙總所有異動計算，不再直接覆寫同一個 `balance`
- B. 在兩個 Region 都改用 `TransactWriteItems` 更新 `balance`，讓交易保證跨 Region 的原子性
- C. 把寫入容量改為 provisioned 並提高 WCU，讓複寫更快完成
- D. 開啟 DynamoDB Streams，讓每個 Region 的 Lambda 把對方的異動再寫一次 `balance`
- E. 讓每位會員的點數異動只在該會員的 home Region 寫入，另一個 Region 收到兌換請求時轉送到 home Region

> [!answer]- 答案：A、E
> **A ✓** 問題來自兩個 Region 同時覆寫同一個 item，last writer wins 丟掉了其中一次。改成每次異動新增一筆不同的 item，兩個 Region 寫的是不同 key，不會互相覆蓋，餘額由彙總得出。
>
> **B ✗** DynamoDB 的交易只在發起交易的 Region 內具有 ACID 保證，無法阻止另一個 Region 同時寫入同一個 item。
>
> **C ✗** 衝突來自複寫的非同步本質，提高容量不能消除「複寫完成前的並行寫入」。
>
> **D ✗** 由 Lambda 重放對方的異動會造成重複加減，而且 Lambda 自己的寫入也會被複寫回去，形成更多衝突。
>
> **E ✓** 讓同一位會員的點數只有一個寫入點，就不存在並行覆寫；另一個 Region 轉送請求，多一次跨 Region 往返，但保證正確。
>
> **考點**：SAP-2.4、SAP-3.4｜避免 last writer wins 造成的遺失更新

### 練習 42-4｜SAP｜單選｜歐洲個資與 global tables

Wanderly 的會員資料存在一張名為 `members` 的 DynamoDB global table，replica 在東京與新加坡，同時包含亞洲與少量歐洲會員。新合約要求歐洲會員的個資只能存放與處理在歐盟境內，並要求歐洲會員在歐盟內有跨 Region 的備援。團隊原本打算在 `members` 加上法蘭克福的 replica，讓歐洲使用者就近讀寫。

應如何調整設計？

- A. 為歐洲會員建立另一張 global table，replica 只放在法蘭克福與愛爾蘭；把歐洲會員從 `members` 搬過去，應用程式依會員的 home Region 存取對應的 table
- B. 在 `members` 加上法蘭克福 replica，並用 Route 53 geolocation 把歐洲使用者導到法蘭克福
- C. 在 `members` 加上法蘭克福 replica，並以 KMS multi-Region key 對歐洲會員的欄位做應用層加密
- D. 在 `members` 加上法蘭克福 replica，並在東京與新加坡的 table 上設定 IAM policy，拒絕讀取歐洲會員的 item

> [!answer]- 答案：A
> **A ✓** Global tables 會複寫整張 table，沒有依 item 過濾的機制，資料主權必須在 table 層級分開。歐洲會員的 table 只在歐盟的兩個 Region 有 replica，同時滿足落地與歐盟內備援；亞洲會員的 table 維持原狀。
>
> **B ✗** 法蘭克福 replica 會讓整張 table 同步，但歐洲會員資料仍存在東京與新加坡，違反合約；geolocation 只影響入口，不影響資料存放位置。
>
> **C ✗** 加密保護的是機密性，不改變資料存放的位置；加密後的歐洲個資仍然存在東京與新加坡。
>
> **D ✗** IAM 只限制誰能讀取，資料本身仍被複寫並存放在歐盟以外的 Region。
>
> **考點**：SAP-1.2、SAP-2.3｜global tables 整表複寫與資料主權分區

### 練習 42-5｜SAP｜單選｜Region 維護時的流量移轉

Wanderly 的 API 以 Global Accelerator 對外提供服務，東京、新加坡、法蘭克福各有一個 endpoint group，後端是 ALB，三個 Region 都能處理所有 API。東京下週要進行一次可能影響服務的資料庫參數調整，團隊希望事先把東京的流量平順地移到其他 Region，調整完成後再逐步移回；全程不能要求合作夥伴更改防火牆允許的 IP，也不能受用戶端 DNS 快取影響。

最合適的做法是什麼？

- A. 在 Route 53 把 API 網域改成 failover 記錄，primary 指向新加坡，維護完成後再改回
- B. 從 accelerator 刪除東京的 endpoint group，維護完成後重新建立
- C. 把東京 endpoint group 中 ALB 的 endpoint weight 調為 255，其他 Region 調為 0
- D. 把東京 endpoint group 的 traffic dial 逐步調降到 0%，維護完成後再逐步調回 100%

> [!answer]- 答案：D
> **A ✗** 修改 DNS 記錄受用戶端與 resolver 快取影響，切換時間不可預期，也違反「不能受 DNS 快取影響」。
>
> **B ✗** 刪除 endpoint group 會立即移走流量，不夠平順，而且重新建立時要重新設定 endpoint 與健康檢查，回切時也無法逐步進行。
>
> **C ✗** Endpoint weight 控制的是同一個 endpoint group（同一個 Region）內各 endpoint 的比例，不能把流量從一個 Region 移到另一個 Region；調整方向也和需求相反。
>
> **D ✓** Traffic dial 控制送往某個 Region 的流量比例，逐步調到 0% 就能平順撤離東京，之後再逐步調回。Anycast IP 不變，切換發生在 AWS 網路內，不受 DNS 快取影響。
>
> **考點**：SAP-2.1、SAP-3.4｜Global Accelerator traffic dial 做 Region 撤離

### 練習 42-6｜SAP｜單選｜Secondary Region 的讀到自己的寫入

Wanderly 的會員偏好設定存在 Aurora MySQL Global Database，primary 在東京，新加坡有 secondary cluster 與 reader instance。新加坡的應用程式已改用 write forwarding，讓少量偏好設定的更新透過本地 cluster 轉送到東京。使用者反映：在新加坡更新偏好後，頁面重新載入時有時仍顯示舊設定。團隊希望修正這個問題，同時不影響其他使用者的讀取效能。

應如何調整？

- A. 把 write forwarding 的讀取一致性設為 `GLOBAL`，讓所有讀取都等待 secondary 追上 primary
- B. 把更新偏好的連線 session 的讀取一致性設為 `SESSION`，讓同一個 session 一定讀得到自己轉送過的寫入
- C. 改用 Aurora switchover，把 primary 移到新加坡
- D. 在新加坡增加更多 reader instance，降低複寫延遲

> [!answer]- 答案：B
> **A ✗** `GLOBAL` 也能讓使用者看到自己的寫入，但它讓讀取等待 secondary 追上 primary 的所有變更，延遲最高；只需要 read-your-writes 時是過度的代價。
>
> **B ✓** `SESSION` 一致性正是為 read-your-writes 設計：同一個 session 的讀取會看到自己先前轉送的寫入，其他不需要這個保證的連線可以維持 `EVENTUAL`，不影響整體讀取效能。
>
> **C ✗** 把 primary 移到新加坡會讓東京的使用者遇到同樣的問題，也改變了整體的寫入延遲分布，沒有解決根本原因。
>
> **D ✗** 複寫延遲來自跨 Region 的儲存層複寫，增加 reader 不會讓複寫變快，問題仍會發生。
>
> **考點**：SAP-2.4、SAP-3.3｜Aurora write forwarding 的一致性等級

### 練習 42-7｜SAP｜單選｜計畫內的 Region 輪替

Wanderly 的庫存資料庫是 Aurora PostgreSQL Global Database，primary 在東京、secondary 在新加坡。稽核要求每半年做一次 Region 輪替演練：把 primary 移到新加坡運作一週再移回。演練期間不能遺失任何已提交的交易，演練後兩個 Region 都要維持在同一個 global database 中，應用程式也不想在每次切換後修改連線字串。

哪個做法最合適？

- A. 應用程式連線改用 global writer endpoint；演練時執行 global database 的 switchover，把新加坡 cluster 設為新的 primary
- B. 執行 `failover-global-cluster` 並加上 `--allow-data-loss`，再手動把東京重新加入
- C. 把新加坡 cluster 從 global database 分離（detach）並提升為獨立 cluster，應用程式改連新加坡
- D. 從東京的最新 snapshot 在新加坡還原一個新 cluster，演練結束後再刪除

> [!answer]- 答案：A
> **A ✓** Switchover 會先等 secondary 完全同步再交換角色，不遺失資料，並保留全球拓撲；global writer endpoint 在切換後自動指向新的 primary，應用程式不必修改連線設定。
>
> **B ✗** Failover 是給 primary Region 真的不可用時使用的，可能遺失尚未複寫的交易；計畫內的演練應使用 switchover。
>
> **C ✗** Detach 會讓新加坡變成獨立 cluster，global database 的拓撲被拆開，演練後要重新建立複寫。
>
> **D ✗** 從 snapshot 還原會遺失 snapshot 之後的交易，也不是在原 global database 中切換角色。
>
> **考點**：SAP-2.2、SAP-3.4｜Aurora Global Database switchover 與 global writer endpoint

### 練習 42-8｜SAP｜單選｜S3 的單一全球入口

Wanderly 的行程文件服務在東京與新加坡都有應用程式執行，兩個 Region 各有一個 S3 bucket。目前應用程式依所在 Region 寫死 bucket 名稱，DR 演練時要修改設定並重新部署，花了一個多小時。團隊希望：兩地的應用程式用同一個名稱存取文件；平時所有請求都由東京的 bucket 處理；東京有問題時，能在幾分鐘內把所有請求移到新加坡，且不必重新部署應用程式。

最合適的做法是什麼？

- A. 建立 CloudFront distribution，以東京 bucket 為主要 origin、新加坡 bucket 為次要 origin 組成 origin group，應用程式改以 CloudFront 網域讀寫文件
- B. 在 Route 53 建立指向兩個 bucket 的 failover 記錄，應用程式改用這個網域存取 S3
- C. 建立 S3 Multi-Region Access Point 包含兩個 bucket，設定雙向複寫；以 failover controls 把東京設為 active、新加坡設為 passive，應用程式改用 MRAP 並以 SigV4A 簽署請求
- D. 在兩個 bucket 之間設定雙向 Cross-Region Replication，並以 S3 Replication Time Control 保證 15 分鐘內完成複寫

> [!answer]- 答案：C
> **A ✗** Origin group 的 failover 只對 GET、HEAD、OPTIONS 生效，應用程式的寫入（PUT）無法自動切換；用 CloudFront 寫入 S3 也不是這類內部應用的常見做法。
>
> **B ✗** S3 的請求需要與 bucket 對應的端點與簽章，單純以 DNS 記錄指向兩個 bucket 無法正確運作，而且切換仍受 DNS 快取影響。
>
> **C ✓** MRAP 提供一個全球名稱，failover controls 讓平時只有 active bucket 接收請求，切換時把 active／passive 對調即可在幾分鐘內生效，應用程式不需改設定。MRAP 本身不複製資料，所以要另外設定雙向複寫；用戶端需使用 SigV4A。
>
> **D ✗** 雙向 CRR 只同步資料，應用程式仍寫死各自的 bucket 名稱，切換時還是要改設定與重新部署。
>
> **考點**：SAP-2.2、SAP-1.3｜S3 Multi-Region Access Points 與 failover controls

### 練習 42-9｜SAA｜單選｜跨 Region 的熱門資料快取

Wanderly 在東京以 ElastiCache for Valkey（node-based）快取熱門旅館排行榜，資料由東京的後台每分鐘更新。新加坡 Region 的應用程式也要讀取這份排行榜，目前每次都跨 Region 連回東京的快取，延遲很高。排行榜可以接受一秒左右的延遲，只有東京的後台會寫入。團隊希望以最少的應用程式變更改善新加坡的讀取延遲，並在東京故障時能讓新加坡接手。

最合適的做法是什麼？

- A. 在新加坡另外建立一個 ElastiCache cluster，並讓東京的後台同時寫入兩個 cluster
- B. 把排行榜改存到 DynamoDB global table，新加坡改讀本地 replica
- C. 在新加坡的 cluster 上啟用 cluster mode，並增加 shard 數量
- D. 建立 ElastiCache Global Datastore，以東京為 primary cluster、新加坡為 secondary cluster，新加坡應用程式讀取本地 secondary

> [!answer]- 答案：D
> **A ✗** 雙寫能運作，但後台要自行處理其中一邊寫入失敗的情況，增加應用程式複雜度，也不是最少變更。
>
> **B ✗** 改用 DynamoDB 需要改寫資料存取邏輯，變更大；排行榜這類資料本來就適合放在快取。
>
> **C ✗** 增加 shard 只提升單一 Region 的容量，新加坡的讀取仍要跨 Region。
>
> **D ✓** Global Datastore 把 primary cluster 的資料非同步複寫到其他 Region 的 secondary（延遲通常在一秒以內），secondary 提供本地讀取；東京故障時可以把新加坡提升為 primary。只有東京寫入、可容忍短暫延遲，正好符合它的設計。
>
> **考點**：SAA-3.3、SAA-2.2｜ElastiCache Global Datastore 的就近讀取

### 練習 42-10｜SAP｜單選｜應用層加密與 DR Region

Wanderly 以 KMS 對會員護照號碼做欄位層級加密：應用程式在東京呼叫 KMS 產生 data key、加密欄位後寫入一張 DynamoDB global table，replica 在東京與新加坡。DR 演練時，新加坡的應用程式讀得到 item，卻無法解密護照欄位，因為加密用的 key 只存在東京。公司要求東京完全不可用時，新加坡仍能解密，而且希望不必重新加密每個欄位的內容。

最合適的做法是什麼？

- A. 在新加坡建立一把新的 KMS key，之後的寫入改用這把 key 加密
- B. 趁東京仍正常時，在東京建立新的 multi-Region primary key 並複製 replica 到新加坡，以新 key 重新包裝（re-encrypt）既有資料的 data key，之後新加坡以本地 replica 解密
- C. 讓新加坡的應用程式跨 Region 呼叫東京的 KMS endpoint 解密
- D. 改用 DynamoDB 的伺服器端加密，並在 table 上指定新加坡的 customer managed key

> [!answer]- 答案：B
> **A ✗** 新 key 只對之後的寫入有效，既有資料仍然只能用東京的 key 解密，東京故障時這些資料打不開。
>
> **B ✓** 密文由應用程式自己解密，所以新加坡需要擁有相同金鑰材料的 key，也就是 multi-Region key。既有的單 Region key 無法轉換成 multi-Region key，因此要建立 multi-Region key，並重新包裝（re-encrypt）既有資料的 data key；被保護的欄位內容本身不必重新加密，之後新加坡就能在本地解密。這是本題四個選項中唯一能在東京不可用時仍解密既有資料的做法。
>
> **C ✗** 跨 Region 呼叫東京的 KMS，在東京完全不可用時一樣失敗，不符合需求。
>
> **D ✗** 伺服器端加密保護的是 table 的儲存，應用層已經加密的欄位仍是密文，新加坡依然需要原本的 key 解密。
>
> **考點**：SAP-2.3、SAP-2.2｜multi-Region KMS key 用於應用層加密的跨 Region 解密

### 練習 42-11｜SAP｜選兩項｜Region 演練中的啟動失敗

Wanderly 進行新加坡 Region 的接手演練。Aurora Global Database 已成功提升，但應用程式 container 啟動後立刻失敗，日誌顯示：讀不到 Secrets Manager 中的資料庫密碼（secret 只存在東京）；讀不到 Parameter Store 中的功能設定（參數也只存在東京）。公司希望下次演練時，即使東京完全不可用，新加坡也能在不修改程式碼的情況下啟動。

哪兩個做法最合適？（選兩項）

- A. 讓新加坡的應用程式在啟動時跨 Region 讀取東京的 secret 與參數
- B. 為資料庫 secret 設定 replica secret 到新加坡，讓輪替後的新值自動同步，新加坡應用程式讀取本地 replica
- C. 把資料庫密碼直接寫進 container image 的環境變數，避免依賴 Secrets Manager
- D. 由部署 pipeline 在每個 Region 以 IaC 寫入相同的 Parameter Store 參數，並把參數納入分波部署
- E. 在 Parameter Store 中開啟跨 Region 複寫選項

> [!answer]- 答案：B、D
> **A ✗** 跨 Region 讀取在東京完全不可用時一樣失敗，違反 Region 獨立性。
>
> **B ✓** Replica secret 讓 secret 在新加坡有自動同步的副本，primary 輪替後 replica 也會更新；應用程式讀取本地 Region 的 secret 即可，不依賴東京。
>
> **C ✗** 把密碼寫進 image 會讓密碼外洩到 image registry 與所有能拉 image 的人，也失去輪替能力。
>
> **D ✓** Parameter Store 沒有內建跨 Region 複寫，所以要由 IaC 或 pipeline 在每個 Region 建立相同參數，並和程式碼一樣分波部署，避免 Region 之間的設定漂移。
>
> **E ✗** Parameter Store 沒有這個選項；它是 Regional 服務。
>
> **考點**：SAP-2.2、SAP-3.4｜Secrets Manager replica 與每個 Region 的設定同步

### 練習 42-12｜SAP｜單選｜多 Region 的安全部署

Wanderly 的基礎設施以一份 CloudFormation template 描述，透過 StackSets 部署到 3 個 production Region 的 20 個帳號。上個月一次錯誤的 security group 變更被同時推到所有 Region，造成三個 Region 同時中斷。平台團隊希望之後任何錯誤的變更最多只影響一個 Region，並在發現錯誤後停止繼續推出。

最合適的做法是什麼？

- A. 改為每個 Region 各自維護一份 template，由各 Region 的團隊分別手動部署
- B. 在 StackSets 部署前執行 change set 檢視，確認無誤後再同時部署到所有 Region
- C. 設定 StackSets 的 operation preferences：以 `RegionOrder` 先部署到流量最小的 Region，`RegionConcurrencyType` 設為 sequential、`FailureToleranceCount` 設為 0，並在每個 Region 之間加入 bake time 與 alarm 檢查的 pipeline 階段
- D. 啟用 StackSets 的自動部署，讓新帳號加入 OU 時自動套用最新版本

> [!answer]- 答案：C
> **A ✗** 每個 Region 各自維護 template 會造成設定漂移，切換時才發現 Region 之間不一致，也增加營運負擔。
>
> **B ✗** Change set 有助於檢查變更內容，但它看不出「變更上線後是否造成中斷」；同時部署到所有 Region 仍會讓一個錯誤影響全部。
>
> **C ✓** 依序部署 Region、失敗時立即停止，並在每一波之間以 bake time 與 alarm 確認健康，能讓錯誤的變更最多影響第一個 Region，這就是分波部署。要注意，錯誤的 security group 規則通常會讓 stack「部署成功」卻造成服務中斷，`FailureToleranceCount` 擋不住這種情況；真正攔下它的是每一波之後的 bake time 與 alarm 檢查，所以兩者要一起使用。
>
> **D ✗** 自動部署解決的是新帳號的 baseline，不控制變更推出的順序與範圍。
>
> **考點**：SAP-2.1、SAP-3.1｜多 Region 分波部署與 StackSets operation preferences

### 練習 42-13｜SAP｜單選｜Active-active 的容量規劃

Wanderly 的搜尋服務以 active-active 部署在三個 Region，平時流量平均分配。尖峰時全站需要相當於 600 個 vCPU 的運算量。需求是任何一個 Region 整個失效時，剩下的兩個 Region 必須在不依賴緊急擴充的情況下承受全部尖峰流量。團隊希望在滿足需求的前提下預先配置最少的容量。

每個 Region 應預先配置多少容量？

- A. 每個 Region 300 vCPU
- B. 每個 Region 200 vCPU
- C. 每個 Region 400 vCPU
- D. 每個 Region 600 vCPU

> [!answer]- 答案：A
> **A ✓** 失去一個 Region 後剩兩個 Region，必須共同承受 600 vCPU，所以每個 Region 至少 300 vCPU。平時每個 Region 只承受 200 vCPU，使用率約 66%，正是 (N−1)／N 的上限。
>
> **B ✗** 200 vCPU 剛好是平時每個 Region 的負載，失去一個 Region 時剩下的兩個 Region 只有 400 vCPU，無法承受 600 vCPU 的尖峰。
>
> **C ✗** 400 vCPU 能滿足需求，但比必要的多配置了三分之一，不是最少的容量。
>
> **D ✗** 每個 Region 都能單獨承受全部流量，這是「能失去兩個 Region」的設計，遠超過需求。
>
> **考點**：SAP-1.3、SAP-2.4｜多 Region 靜態穩定的容量計算

### 練習 42-14｜SAP｜單選｜單一寫入點的切換順序

Wanderly 的庫存 Aurora Global Database primary 在東京。東京出現網路異常，部分請求仍能到達東京的資料庫，但大多數失敗。值班人員決定把庫存服務切到新加坡。過去一次演練中，因為東京的資料庫在網路恢復後又開始接受寫入，造成兩邊資料不一致。

哪個 runbook 順序最能避免資料不一致並讓服務最快恢復？

- A. 先用 ARC routing control 把流量導向新加坡，再提升新加坡的資料庫，最後讓東京停止接受寫入
- B. 先提升新加坡的資料庫並移動流量，等東京恢復後再把東京的寫入合併到新加坡
- C. 先在新加坡擴充運算並移動流量，等使用者回報錯誤消失後再處理資料庫
- D. 先讓東京停止接受寫入（圍欄），確認複寫狀態後提升新加坡的資料庫，接著確認新加坡的運算與 secret 就緒，再移動流量並以合成交易驗證

> [!answer]- 答案：D
> **A ✗** 先移動流量會讓使用者被送到資料庫仍是唯讀的新加坡，只看到錯誤；最後才圍欄東京，中間仍可能有寫入進到舊 primary。
>
> **B ✗** 沒有先圍欄東京，網路恢復後東京仍會接受寫入，事後合併兩邊的庫存扣減既困難又可能超賣。
>
> **C ✗** 資料庫仍是唯讀時移動流量，所有寫入都會失敗；也完全沒有處理舊 primary。
>
> **D ✓** 圍欄舊 primary 避免腦裂；依複寫狀態選擇切換方式；先提升資料庫再準備運算、最後移動流量，確保使用者到達時新 Region 已可寫；以業務交易驗證後才宣告恢復。
>
> **考點**：SAP-2.2、SAP-1.3｜Region failover 的圍欄與步驟順序

### 練習 42-15｜SAA｜單選｜多 Region 讀寫的 key-value 資料

一個旅遊 App 的使用者分布在亞洲與美國，購物車資料存在單一 Region 的 DynamoDB table。美國使用者的加入購物車操作延遲很高。團隊希望兩地使用者都能在本地 Region 讀寫購物車，Region 故障時另一個 Region 繼續服務；購物車偶爾因兩地同時修改而以較晚的寫入為準是可以接受的。團隊希望營運負擔最低。

最合適的做法是什麼？

- A. 在美國 Region 建立另一張 table，應用程式自行把每次寫入同步到兩張 table
- B. 在美國 Region 建立 DynamoDB Accelerator（DAX）cluster，快取亞洲 table 的資料
- C. 把 table 轉為 DynamoDB global table，在美國 Region 新增 replica，各地應用程式讀寫本地 replica
- D. 用 DynamoDB Streams 加 Lambda 把亞洲 table 的變更複製到美國 Region 的唯讀 table

> [!answer]- 答案：C
> **A ✗** 應用程式自行雙寫要處理部分失敗與重試，營運負擔高，也容易讓兩張 table 不一致。
>
> **B ✗** DAX 是同一 Region 內的讀取快取，不能跨 Region 快取，也不能讓寫入在美國本地完成。
>
> **C ✓** Global tables 讓每個 Region 的 replica 都能讀寫，變更自動非同步複寫，Region 故障時其他 replica 繼續服務；衝突以 last writer wins 解決，對購物車可以接受。
>
> **D ✗** 自建複寫只產生唯讀副本，美國的寫入仍要跨 Region 回到亞洲，且要自行維護 Lambda。
>
> **考點**：SAA-2.2、SAA-3.3｜DynamoDB global tables 的多 Region 讀寫

### 練習 42-16｜SAP｜選兩項｜跨 Region 強一致的庫存計數

Wanderly 的亞太限時搶購活動要在三個亞太 Region 同時開賣，庫存計數存在 DynamoDB。需求是：任何一個 Region 扣減庫存後，其他 Region 立刻讀得到最新數字；任何一個 Region 故障都不能遺失已確認的扣減（RPO 為零）；三個 Region 都要能接受扣減。現有程式以 `TransactWriteItems` 同時扣減庫存並寫入一筆預訂紀錄。

哪兩個做法是設計時必須採用的？（選兩項）

- A. 把庫存 table 建立為 MRSC 模式的 global table，部署在三個支援的亞太 Region（或兩個 replica 加一個 witness）
- B. 把庫存 table 建立為 MREC 模式的 global table，並把所有讀取改為 strongly consistent read
- C. 保留 `TransactWriteItems`，並在每個 Region 加上 DynamoDB Streams 確認交易已複寫
- D. 把扣減改成單一 item 的條件更新（例如 `ConditionExpression` 檢查剩餘數量大於 0），預訂紀錄改由後續的冪等流程寫入
- E. 在三個 Region 前面加上 DAX，讓所有 Region 讀取同一份快取

> [!answer]- 答案：A、D
> **A ✓** MRSC 在寫入同步確認到其他 Region 後才回應，任何 Region 的 strongly consistent read 都讀得到最新資料，RPO 為零，且三個 Region 都能寫入。它要求剛好三個 Region（三個 replica 或兩個 replica 加 witness），亞太 Region 的組合要在支援範圍內。
>
> **B ✗** MREC 是非同步複寫，strongly consistent read 只保證本 Region 的最新資料，其他 Region 會短暫讀到舊數字，Region 故障時也可能遺失尚未複寫的扣減。
>
> **C ✗** MRSC 不支援 transactions，原本的 `TransactWriteItems` 必須改寫；Streams 也無法提供交易的跨 Region 保證。
>
> **D ✓** 以單一 item 的條件更新扣減庫存，就能在 MRSC 下保證不超賣；兩個 Region 同時更新同一個 item 時，其中一方會收到衝突例外並重試。預訂紀錄改由帶冪等鍵的後續流程寫入。
>
> **E ✗** DAX 是單一 Region 的快取，而且快取本身就會讓讀取變成最終一致，與需求相反。
>
> **考點**：SAP-2.4、SAP-4.4｜DynamoDB MRSC 的限制與改寫交易
