---
chapter: 27
title: DynamoDB：Serverless NoSQL
part: 5
---

# 第 27 章　DynamoDB：Serverless NoSQL

> [!abstract] 本章地圖
> **你會學到**：
> - 用 partition key、sort key 與 item collection 描述 DynamoDB 的資料模型，並說明為什麼「先列存取模式、再設計 key」
> - 判斷一個 key 設計會不會造成熱分割，並用 write sharding 等手法修正
> - 手算 RCU 與 WCU（含 strongly／eventually consistent、transactional、Query 合併計算、GSI 寫入放大），選擇 on-demand 或 provisioned
> - 分辨 LSI 與 GSI，正確使用 TTL、Streams、transactions、DAX 與 global tables
> - 為 DynamoDB 規劃備份、匯出、加密與 fine-grained access control
>
> **前置知識**：第 4 章（NoSQL、strong 與 eventual consistency）、第 12 章（IAM policy）、第 26 章（與關聯式資料庫對照）
> **考試比重**：SAA ★★★（Domain 2 鬆耦合、Domain 3 資料庫效能、Domain 4 資料庫成本）｜SAP ★★☆（Domain 2 效能與可靠性、Domain 3 改善效能）

## 27.1 故事：購物車撐不住限時搶購

Wanderly 每季會舉辦「一元住宿」限時搶購。活動開始的第一分鐘，數十萬名使用者同時把房間加入購物車、查看自己的購物車、反覆刷新。購物車原本放在第 26 章的 Aurora MySQL 裡，一張 `cart_items` 表加上 `user_id` 索引。

前兩次活動，資料庫的連線數與 CPU 在一分鐘內衝到頂，結帳也跟著變慢。團隊檢查流量後發現一件事：購物車幾乎只有三種操作，「把一個房間加入某人的購物車」、「讀出某人的整個購物車」、「刪除某人購物車裡的一項」。沒有 JOIN、沒有跨使用者的統計，每個請求都只碰一個使用者的資料。

這種「存取方式固定、每次只碰一小塊資料、流量可能瞬間放大百倍」的工作負載，正是 **Amazon DynamoDB** 擅長的。這一章跟著 Wanderly 把購物車、會員點數與行程資料搬上 DynamoDB，過程中你會發現：DynamoDB 不用調資料庫參數、不用管連線，但**資料要怎麼分布、讀寫要花多少容量，全部取決於你怎麼設計 key**。

## 27.2 DynamoDB 是什麼：沒有伺服器的 key-value 資料庫

**Amazon DynamoDB** 是全受管、serverless 的 NoSQL 資料庫，支援 **key-value（鍵值）** 與 **document（文件）** 兩種資料形態。它的幾個基本特性決定了它適合什麼、不適合什麼：

- **沒有伺服器與連線要管**：你建立的是 table，不是 instance。應用程式透過 HTTPS API（`GetItem`、`PutItem`、`Query`…）存取，每個請求都用 IAM 簽章驗證，所以沒有「連線池耗盡」的問題，非常適合 Lambda。
- **Regional 且自動跨 AZ**：每個 table 屬於一個 Region，資料自動同步複寫到該 Region 的多個 AZ，你不用設定 Multi-AZ。
- **效能可預測**：只要 key 設計得當，無論 table 有 1 GB 還是 100 TB，單筆讀寫延遲都維持在個位數毫秒。
- **按容量或請求計費**：不用付 instance 費用，費用由讀寫量與儲存量決定（27.7 節）。

代價是：**DynamoDB 不支援 JOIN，也不適合臨時的複雜查詢**。你只能有效率地依 key 查資料，想用任意欄位篩選，就得掃描整個 table（`Scan`），既慢又貴。所以 DynamoDB 的設計思路和關聯式資料庫相反：

| 關聯式資料庫（第 26 章） | DynamoDB |
|---|---|
| 先依實體正規化設計 table，查詢時再 JOIN | 先列出所有存取模式，再設計 key 讓每個模式都是一次 key 查詢 |
| 任意欄位都能 `WHERE`，靠 index 加速 | 只有 key 與 index 上的屬性能有效率地查詢 |
| 垂直擴展為主（換大機器）、讀取靠 replica | 水平擴展：資料自動分散到多個 partition |
| 連線數有上限 | 無連線概念，請求數可以極高 |

> [!warning] 常見誤解
> 「NoSQL 就是沒有 schema，所以不用設計。」DynamoDB 的 item 屬性確實可以不一致，但 key 的設計一旦上線就無法修改（要改只能建新 table 搬資料）。DynamoDB 需要的設計功夫不比關聯式資料庫少，只是設計的對象從「正規化」變成「存取模式」。

## 27.3 資料模型：table、item 與 primary key

### 基本名詞

- **Table（資料表）**：資料的容器，例如 `WanderlyCart`。
- **Item（項目）**：一筆資料，相當於關聯式資料庫的一列。**單一 item 最大 400 KB**（含屬性名稱與值）。
- **Attribute（屬性）**：item 裡的一個欄位。型別包括字串（S）、數字（N）、二進位（B）、布林、null，document 型別的 map（M）與 list（L），以及字串／數字／二進位的 set。
- **Primary key（主鍵）**：每個 item 唯一的識別，建立 table 時決定，之後不能修改。除了主鍵，其他屬性每個 item 都可以不同。

### 兩種主鍵

1. **Simple primary key**：只有 **partition key（分割鍵，也叫 hash key）**。每個 partition key 值只能對應一個 item。例如會員資料表以 `member_id` 為 partition key。
2. **Composite primary key**：**partition key + sort key（排序鍵，也叫 range key）**。同一個 partition key 下可以有很多 item，以 sort key 區分並排序。partition key 與 sort key 的組合必須唯一。

在 composite key 的 table 中，**相同 partition key 的所有 item 稱為一個 item collection（項目集合）**。它們實體上存放在一起，並依 sort key 排序，所以能用一次 `Query` 取出整個集合，或取出 sort key 落在某個範圍的部分。

### Wanderly 購物車的 key

購物車的三個存取模式都以「某個使用者」為中心，所以：

| 屬性 | 角色 | 範例 |
|---|---|---|
| `user_id` | Partition key | `U#81723` |
| `item_key` | Sort key | `ROOM#tpe-0193#2026-12-24` |
| `price`、`qty`、`added_at` | 一般屬性 | `1`、`1`、`2026-11-01T12:00:03Z` |

- 「加入購物車」→ `PutItem`，key 為 `(U#81723, ROOM#…)`。
- 「讀出整個購物車」→ `Query user_id = U#81723`，一次取回整個 item collection。
- 「刪除一項」→ `DeleteItem`，key 為完整的 `(user_id, item_key)`。

三個操作都直接命中 key，不需要任何掃描。這就是「先列存取模式、再設計 key」的意思。

## 27.4 Partition 與熱分割

### DynamoDB 怎麼分散資料

DynamoDB 把 table 的資料存放在許多 **partition（分割區）** 上。Partition 是 DynamoDB 內部的儲存與運算單位，你看不到也不能直接管理，但它決定了效能上限：

```text
   PutItem(user_id = "U#81723", item_key = "ROOM#tpe-0193#…")
                         │
              ① 對 partition key 做雜湊（hash）
                         ▼
               hash("U#81723") = 0x7A3F…
                         │ ② 依雜湊值落在的範圍決定 partition
      ┌──────────────────┼──────────────────────────┐
      ▼                  ▼                          ▼
 ┌──────────┐      ┌──────────┐               ┌──────────┐
 │Partition1│      │Partition2│      …        │PartitionN│
 │hash 0–3F │      │hash 40–7F│               │hash C0–FF│
 └──────────┘      └──────────┘               └──────────┘
   ③ 每個 partition：最多約 10 GB 資料、
      每秒最多 3,000 RCU 與 1,000 WCU
   ④ 同一個 item collection 內的 item 依 sort key 排序存放
```

① DynamoDB 用 partition key 的雜湊值決定資料去哪裡，sort key 不參與這個決定。② 雜湊值把 key 均勻打散，不同使用者的資料自然分散到不同 partition。③ 單一 partition 有固定的上限：約 10 GB 資料、每秒 3,000 RCU 讀取與 1,000 WCU 寫入（RCU／WCU 的定義見 27.6 節）。資料變多或流量變大時，DynamoDB 會自動把 partition 分裂成更多個。④ Sort key 只決定 item 在 partition 內的排序。

### 熱分割：總容量夠，卻還是被 throttle

由第 ③ 點可以推出一個非常重要的結論：**單一 partition key 值的流量，最多只能用到一個 partition 的上限**。假設 Wanderly 的點擊事件表用「日期」當 partition key，今天所有寫入都打到 `2026-11-01` 這一個值，不管 table 總共配置了多少容量，這個 key 每秒最多約 1,000 WCU，超過的請求會被拒絕，回傳 `ProvisionedThroughputExceededException`，這叫 **throttling（節流）**。

這種流量集中在少數 key 的情況叫 **hot partition（熱分割）** 或 **hot key**。DynamoDB 有兩個機制緩和它：

- **Burst capacity**：provisioned 模式下，table 會保留最近一段時間（約 5 分鐘）沒用完的容量，供短暫的尖峰使用。
- **Adaptive capacity**：DynamoDB 自動把更多容量分給流量較高的 partition，必要時把熱 item 分到獨立的 partition。

但這兩個機制都只是緩和：流量集中在單一 key（尤其是單一 item）時，仍然受單一 partition 每秒約 3,000 RCU、1,000 WCU 的上限限制。根本解法還是 key 設計：

1. **選高基數（high cardinality）的 partition key**：值的種類多、流量平均分布。`user_id`、`order_id`、`device_id` 通常是好選擇；`status`（只有幾種值）、`date`、`country` 通常是壞選擇。
2. **Write sharding（寫入分片）**：在 key 後面加上後綴，把一個邏輯 key 拆成多個實體 key。例如把 `2026-11-01` 寫成 `2026-11-01#0` 到 `2026-11-01#9` 之一（隨機或依 hash 決定）。寫入分散到 10 個 key；讀取時要對 10 個 key 各做一次 `Query` 再合併。這是用讀取的複雜度換寫入的擴展性。
3. **用快取吸收熱讀取**：同一個熱門 item 被大量讀取時，用 DAX（27.11 節）或 ElastiCache（第 28 章）接住。

要找出是哪些 key 太熱，可以開啟 **CloudWatch Contributor Insights for DynamoDB**，它會列出存取最頻繁與最常被 throttle 的 key。

## 27.5 讀取方式與一致性

### 三種讀取 API

| 操作 | 做什麼 | 效率 |
|---|---|---|
| `GetItem` | 用完整主鍵讀一個 item | 最高 |
| `Query` | 指定一個 partition key 值，可加 sort key 條件（`=`、`<`、`BETWEEN`、`begins_with`），取回該 item collection 的部分或全部 | 高，只讀符合條件的 item |
| `Scan` | 讀整個 table（或 index）的每一個 item | 低，table 越大越慢越貴 |

每次 `Query` 或 `Scan` 最多回傳 1 MB 資料，超過要用回傳的 `LastEvaluatedKey` 分頁繼續讀。`BatchGetItem` 一次最多取 100 個 item，可以減少網路往返，但容量是逐個 item 計算的。

### FilterExpression 不省容量

`Query` 與 `Scan` 都可以加 **FilterExpression**（過濾條件），但要特別注意：**過濾發生在 DynamoDB 讀完資料之後**。DynamoDB 先依 key 條件讀出 item、計算消耗的容量，再把不符合 filter 的 item 丟掉才回傳。所以 filter 只減少網路傳輸量，**不減少消耗的 RCU**。一個需要「讀 10,000 筆、filter 掉 9,990 筆」的查詢，代表 key 設計沒有支援這個存取模式，應該改用 index（27.8 節）。

同理，**ProjectionExpression**（只回傳指定屬性）也不減少 RCU，因為容量依整個 item 的大小計算。

### 一致性：eventually、strongly 與 transactional

DynamoDB 的每筆寫入會複寫到多個 AZ 的儲存節點。寫入成功後，所有副本通常在一秒內一致，但讀取剛好打到還沒更新的副本時，可能讀到舊資料。所以讀取有三種一致性選項：

- **Eventually consistent read（最終一致讀取）**：預設值。可能讀到稍舊的資料，但容量只要 strongly consistent 的一半。
- **Strongly consistent read（強一致讀取）**：在請求中設定 `ConsistentRead=true`，保證讀到讀取前所有成功寫入的最新值。容量是兩倍，延遲可能稍高。**GSI 不支援 strongly consistent read**；global tables 也只在同一個 Region 內提供強一致（MRSC 模式例外，見 27.12 節）。
- **Transactional read**：`TransactGetItems`，多個 item 以一致的快照一起讀，容量再加倍（27.9 節）。

購物車在使用者按下「加入」後立刻顯示，適合用 strongly consistent read；首頁的「熱門旅館」列表晚一秒更新無所謂，用 eventually consistent 省一半容量。

## 27.6 Capacity 計算：RCU 與 WCU

### 定義

DynamoDB 用兩種單位衡量讀寫量：

- **1 RCU（Read Capacity Unit）** = 每秒 1 次 **strongly consistent** 讀取，item 大小**最多 4 KB**。
  - Eventually consistent：1 RCU 可以做每秒 2 次（也就是每次 0.5 RCU）。
  - Transactional：每次 4 KB 需要 2 RCU。
- **1 WCU（Write Capacity Unit）** = 每秒 1 次寫入，item 大小**最多 1 KB**。
  - Transactional：每次 1 KB 需要 2 WCU。

**大小一律向上取整**：讀取以 4 KB 為單位、寫入以 1 KB 為單位。一個 4.1 KB 的 item，strongly consistent 讀取要 2 RCU；一個 1.1 KB 的 item 寫入要 2 WCU。寫入的大小以「寫入後的 item 大小」與「寫入前大小」中較大者計算，所以只更新一個小欄位，也要依整個 item 大小付費。

On-demand 模式（27.7 節）用的 **read request unit** 與 **write request unit** 換算方式完全相同，差別只在計費方式。

### 計算公式

```text
RCU = 每秒讀取次數 × ceil(item 大小 ÷ 4 KB) × 一致性係數
        一致性係數：eventually = 0.5、strongly = 1、transactional = 2

WCU = 每秒寫入次數 × ceil(item 大小 ÷ 1 KB) × 交易係數
        交易係數：一般寫入 = 1、transactional = 2
```

### 算例一：單筆讀取

Wanderly 的旅館詳細資料 item 平均 **6.5 KB**，旺季每秒被讀取 **100 次**。

- 每次讀取的單位數：ceil(6.5 ÷ 4) = ceil(1.625) = **2** 個 4 KB 單位。
- Strongly consistent：100 × 2 × 1 = **200 RCU**。
- Eventually consistent：100 × 2 × 0.5 = **100 RCU**。
- Transactional：100 × 2 × 2 = **400 RCU**。

一致性的選擇讓容量差了四倍。旅館資料不需要即時一致，所以用 eventually consistent，只要 100 RCU。

### 算例二：單筆寫入

購物車 item 平均 **1.5 KB**，搶購尖峰每秒寫入 **800 次**。

- 每次寫入的單位數：ceil(1.5 ÷ 1) = **2**。
- 一般寫入：800 × 2 = **1,600 WCU**。
- 若改用 transactional 寫入：800 × 2 × 2 = **3,200 WCU**。

另一個觀察：如果能把 item 精簡到 1 KB 以內（例如縮短屬性名稱、把很少用的大欄位移到別的 item），每次寫入只要 1 WCU，容量直接減半。**屬性名稱也計入大小**，在大量寫入的 table 上，`added_at_timestamp_utc` 這種長名稱是會花錢的。

### 算例三：Query 是「合併後」再取整

會員的行程列表用 `Query` 讀取，一次回傳 **25 個 item、每個 0.8 KB**，每秒 **40 次** Query，使用 strongly consistent。

- `Query` 與 `Scan` 的容量是把**所有回傳 item 的大小加總後**再以 4 KB 取整：25 × 0.8 = 20 KB → 20 ÷ 4 = **5** 個單位。
- 每秒容量：40 × 5 × 1 = **200 RCU**；若改用 eventually consistent 只要 **100 RCU**。

對比：如果應用程式改成用 25 次 `GetItem`（或一次 `BatchGetItem`）逐筆讀取，每個 0.8 KB 的 item 都要向上取整成 1 個單位：40 × 25 × 1 = **1,000 RCU**，是 Query 的五倍。**把相關的小 item 放在同一個 item collection、用 Query 一次讀出，是 DynamoDB 最重要的省容量技巧之一。**

### 算例四：Scan 的代價

一個 50 GB 的 table，用 eventually consistent `Scan` 全表掃描一次：50 GB ≈ 51,200 MB，每 1 MB 頁面消耗 1,024 KB ÷ 4 KB × 0.5 = 128 RCU，總共約 51,200 × 128 ≈ **655 萬 RCU**。即使分攤在一小時內，每秒也要約 1,800 RCU，會和線上流量搶容量。這就是為什麼分析型需求應該用「匯出到 S3」（27.13 節）而不是 Scan。

### 算例五：GSI 的寫入放大

會員資料表有兩個 GSI（27.8 節），兩個都投影全部屬性（`ALL`）。寫入一個 0.9 KB 的新 item：

- Base table：1 WCU。
- 每個 GSI 也要寫入一份：各 1 WCU。
- 合計 **3 WCU**。若一次更新改變了某個 GSI 的 key 屬性值，該 index 要「刪舊項目＋寫新項目」，那個 index 會消耗 2 次寫入。

所以每多一個 GSI、投影越多屬性，寫入成本越高。只投影查詢需要的屬性（`KEYS_ONLY` 或 `INCLUDE`）能降低 index 的寫入量與儲存量。

### 算例六：為搶購活動估算 provisioned 容量

把購物車在搶購尖峰的需求加起來：

| 操作 | 每秒次數 | Item 大小 | 一致性 | 容量 |
|---|---|---|---|---|
| 讀整個購物車（Query，平均 3 個 item 共 4.5 KB） | 3,000 | 4.5 KB → 2 單位 | strongly | 6,000 RCU |
| 加入購物車（PutItem） | 800 | 1.5 KB → 2 單位 | — | 1,600 WCU |
| 刪除一項（DeleteItem，以被刪 item 大小計） | 200 | 1.5 KB → 2 單位 | — | 400 WCU |

合計 **6,000 RCU 與 2,000 WCU**。若使用 provisioned 模式搭配 auto scaling、目標使用率 70%，尖峰時配置量約為 6,000 ÷ 0.7 ≈ 8,600 RCU 與 2,000 ÷ 0.7 ≈ 2,900 WCU。這個數字遠超過單一 partition 的上限，所以 key 必須讓流量分散到許多 partition；`user_id` 有數十萬個不同值，正好滿足。

## 27.7 Capacity modes：on-demand 與 provisioned

### On-demand

**On-demand（隨需）模式**不用預先指定容量，DynamoDB 依實際請求數計費（每百萬個 read／write request unit 計價），自動因應流量。

- 適合：新應用流量未知、流量難以預測、尖離峰差異極大、很長時間幾乎沒流量的 table。
- 它也不是無上限：on-demand 能立即承受**先前尖峰的兩倍**；若在 **30 分鐘內**衝到超過先前尖峰的兩倍，仍可能被 throttle。新建的 on-demand table 一開始約可承受每秒 4,000 次寫入與 12,000 次讀取，之後隨流量自動擴大。若已知某個時間點會有大流量，可以事先為 table 設定 **warm throughput**（預熱）。你也可以設定 on-demand 的最大吞吐量，防止失控的程式造成意外帳單。
- 熱分割的限制同樣存在：單一 partition key 的上限不因 on-demand 而改變。

### Provisioned

**Provisioned（預置）模式**由你指定每秒的 RCU 與 WCU，按配置量每小時計費，用不到也要付費；超過配置量的請求會被 throttle（短時間內可以用到 burst capacity）。

- **Auto scaling**：透過 Application Auto Scaling 設定最小值、最大值與目標使用率（例如 70%），DynamoDB 依 CloudWatch 指標自動調整配置。它的反應需要幾分鐘，所以**接不住「一秒內暴增十倍」的流量**，適合逐步變化的流量曲線。
- **Reserved capacity**：對 provisioned 的基礎用量承諾 1 年或 3 年，取得大幅折扣。
- 適合：流量穩定可預測、能透過容量規劃把使用率維持在高水準的工作負載。

### 怎麼選

| 情境 | 建議 |
|---|---|
| 新產品，不知道流量 | On-demand |
| 流量尖峰在秒級暴增、無法預測 | On-demand（必要時預熱） |
| 每天的流量曲線平滑、可預測 | Provisioned + auto scaling |
| 長期穩定的大量基礎流量 | Provisioned + reserved capacity |
| 開發測試、偶爾才使用 | On-demand |

兩種模式可以切換：從 provisioned 切到 on-demand 在任意 24 小時內最多 4 次，從 on-demand 切回 provisioned 則不限次數。這個限制讓 capacity mode 不適合當作每小時調整的手段。

### Table class：Standard 與 Standard-IA

除了 capacity mode，table 還有 **table class**：**DynamoDB Standard** 與 **DynamoDB Standard-Infrequent Access（Standard-IA）**。Standard-IA 的儲存單價明顯較低，讀寫單價較高，適合「資料量很大、但很少被讀寫」的 table，例如保存多年的歷史訂單或稽核紀錄。當儲存費用是 table 費用的主要部分時，改用 Standard-IA 通常更省。

## 27.8 Secondary indexes：為新的存取模式開一條路

### 為什麼需要

購物車以 `user_id` 為 partition key，三個存取模式都很順。但會員中心又提出新需求：「依 email 找會員」、「列出某間旅館最近的所有訂單」。這些查詢用的屬性不是 primary key，若沒有 index 只能 Scan。**Secondary index（次要索引）** 讓你用另一組 key 查詢同一份資料。

### LSI 與 GSI

**LSI（Local Secondary Index，本地次要索引）**：

- **Partition key 必須和 base table 相同**，只換 sort key。例如 base table 是 `(user_id, item_key)`，LSI 是 `(user_id, added_at)`，讓同一個使用者的購物車可以依加入時間排序。
- **只能在建立 table 時一起建立**，之後無法新增或刪除。每個 table 最多 5 個 LSI。
- 與 base table **共用容量**。
- **支援 strongly consistent read**。
- 有 LSI 的 table，每個 partition key 值的 item collection（base table 加所有 LSI 的資料）最多 10 GB。

**GSI（Global Secondary Index，全域次要索引）**：

- **Partition key 與 sort key 都可以和 base table 不同**。例如訂單表以 `order_id` 為 key，建立 GSI `(hotel_id, order_date)`，就能查某間旅館的訂單。
- **可以隨時新增或刪除**。每個 table 預設最多 20 個（預設 quota，可申請提高）。
- **有自己的容量**（provisioned 模式下要另外設定 RCU／WCU；on-demand 模式則按請求計費）。
- **只支援 eventually consistent read**。Base table 寫入後，GSI 以非同步方式更新，通常很快但不保證即時。
- GSI 的 key 值不需要唯一，多個 item 可以有相同的 GSI key。

| 比較 | LSI | GSI |
|---|---|---|
| Partition key | 與 base table 相同 | 可不同 |
| 建立時機 | 只能建表時 | 隨時 |
| 數量上限 | 5 | 預設 20（可申請提高） |
| 容量 | 與 base table 共用 | 獨立 |
| 一致性 | 支援 strongly consistent | 只有 eventually consistent |
| Item collection 10 GB 限制 | 有 | 無 |

### Projection 與 sparse index

建立 index 時要選擇 **projection（投影）**：哪些屬性要複製到 index。

- `KEYS_ONLY`：只有 table 與 index 的 key。最省，但查詢後若需要其他屬性要再回 base table 讀。
- `INCLUDE`：key 加上你指定的屬性。
- `ALL`：全部屬性。查詢最方便，但寫入與儲存成本最高。

**Sparse index（稀疏索引）** 是一個很實用的技巧：只有「具有 GSI key 屬性」的 item 才會出現在 GSI 裡。例如只在「待付款」訂單上設定 `pending_since` 屬性，付款完成就移除它；以 `pending_since` 為 key 的 GSI 就只包含待付款訂單，查詢它比掃描全部訂單便宜得多。

> [!warning] 常見誤解：GSI 會反過來拖慢 base table
> 在 provisioned 模式下，如果 GSI 的 WCU 不夠，GSI 被 throttle，**base table 的寫入也會被 throttle**，因為 DynamoDB 必須能把變更寫進 index。發現 base table 容量充足卻寫入失敗時，要檢查 GSI 的容量與指標。

## 27.9 寫入正確性：條件寫入與交易

### Condition expression 與 optimistic locking

搶購時，兩個使用者可能同時搶最後一間房。若兩個請求都「讀出剩餘 1 間 → 寫入剩餘 0 間」，就會超賣。DynamoDB 的 **condition expression（條件運算式）** 讓寫入只在條件成立時才執行，判斷與寫入是原子的：

```python
table.update_item(
    Key={"PK": "HOTEL#tpe-0193", "SK": "INVENTORY#2026-12-24"},
    UpdateExpression="SET remaining = remaining - :one",
    ConditionExpression="remaining >= :one",
    ExpressionAttributeValues={":one": 1},
)
```

條件不成立時，DynamoDB 拋出 `ConditionalCheckFailedException`，應用程式就知道房間已售完，不會超賣。這段程式同時示範了 **atomic counter（原子計數器）**：`SET remaining = remaining - :one` 在伺服器端執行，不需要先讀再寫。

更一般的模式是 **optimistic locking（樂觀鎖）**：每個 item 帶一個 `version` 屬性，更新時加上條件 `version = :expected`，並把 version 加 1。若別人已經先改過，條件失敗，應用程式重新讀取後再試。

### Transactions

有些操作必須同時成功或同時失敗。例如「用 500 點會員點數兌換一晚住宿」要同時做三件事：扣點數（點數不足就失敗）、建立兌換紀錄、扣旅館庫存。**DynamoDB transactions** 提供跨多個 item、甚至跨多個 table（同一 Region、同一帳號）的 ACID 交易：

- `TransactWriteItems`：最多 100 個動作（Put、Update、Delete、ConditionCheck），合計最多 4 MB，全部成功或全部不執行。
- `TransactGetItems`：最多 100 個 item 的一致讀取。
- **容量加倍**：transactional 寫入每 1 KB 需要 2 WCU，讀取每 4 KB 需要 2 RCU（因為 DynamoDB 內部要做準備與提交兩個階段）。
- **ClientRequestToken**：為交易提供冪等性（idempotency），同一個 token 在 10 分鐘內重送，不會重複執行。網路逾時後重試時特別重要。

```python
client.transact_write_items(
    ClientRequestToken="redeem-U81723-20261101-0001",
    TransactItems=[
        {"Update": {
            "TableName": "Wanderly",
            "Key": {"PK": {"S": "MEMBER#81723"}, "SK": {"S": "PROFILE"}},
            "UpdateExpression": "SET points = points - :p",
            "ConditionExpression": "points >= :p",
            "ExpressionAttributeValues": {":p": {"N": "500"}}}},
        {"Put": {
            "TableName": "Wanderly",
            "Item": {"PK": {"S": "MEMBER#81723"}, "SK": {"S": "REDEEM#20261101-0001"},
                     "points": {"N": "500"}},
            "ConditionExpression": "attribute_not_exists(PK)"}},
        {"Update": {
            "TableName": "Wanderly",
            "Key": {"PK": {"S": "HOTEL#tpe-0193"}, "SK": {"S": "INVENTORY#2026-12-24"}},
            "UpdateExpression": "SET remaining = remaining - :one",
            "ConditionExpression": "remaining >= :one",
            "ExpressionAttributeValues": {":one": {"N": "1"}}}},
    ],
)
```

任何一個條件失敗，整個交易都不會生效。交易適合「少數 item 必須一起改」的業務規則，不適合大量資料的批次處理；批次寫入用 `BatchWriteItem`（每次最多 25 個 item），但它**不是交易**，部分成功時要處理回傳的 `UnprocessedItems`。

## 27.10 TTL 與 Streams：讓資料自己過期、讓變更觸發事件

### TTL

購物車放了 30 天沒結帳就該清掉，session 資料 24 小時後就沒用了。自己寫排程去 Scan 再刪除，既耗容量又麻煩。**TTL（Time to Live，存活時間）** 讓 DynamoDB 自動刪除過期的 item：

- 在 table 上指定一個屬性名稱（例如 `expires_at`），值為 **Unix epoch 秒數**的 Number。
- 過了這個時間，DynamoDB 會在背景刪除該 item，**不消耗 WCU、不收費**。
- 刪除不是即時的，通常在到期後**數天內**完成。到期但尚未刪除的 item 仍會被讀到，所以需要精確過期的應用程式要在查詢時加 filter（例如 `expires_at > :now`）。
- TTL 刪除會出現在 DynamoDB Streams 中，並標示為系統刪除，可以據此把過期資料封存到 S3。

### DynamoDB Streams

**DynamoDB Streams** 是 table 的變更紀錄：每一次 item 的新增、修改、刪除都會產生一筆 stream record，**同一個 item 的變更依發生順序排列**，保留 **24 小時**。你可以選擇每筆 record 包含什麼：

| StreamViewType | 內容 |
|---|---|
| `KEYS_ONLY` | 只有被修改 item 的 key |
| `NEW_IMAGE` | 修改後的完整 item |
| `OLD_IMAGE` | 修改前的完整 item |
| `NEW_AND_OLD_IMAGES` | 修改前後都有 |

最常見的用法是搭配 Lambda 的 event source mapping（第 19 章），形成事件驅動架構：

```text
 ① 使用者付款完成
        ▼
 [Order API] ── UpdateItem status = PAID ──► [DynamoDB: Orders]
                                                  │ ② 產生 stream record
                                                  ▼
                                         [DynamoDB Streams]（保留 24 小時）
                                                  │ ③ Lambda 輪詢、批次取得
                                                  ▼
                                         [Lambda: order-events]
                                ┌─────────────────┼──────────────────┐
                                ▼                 ▼                  ▼
                    ④ 寄確認信（SES）   更新搜尋索引（OpenSearch）  發事件到 EventBridge
```

① 訂單 API 只負責寫入資料庫。② 寫入成功後，DynamoDB 自動產生 stream record，API 不需要另外發訊息，也不會出現「資料寫入了但訊息沒送出」的不一致。③ Lambda 依 shard 依序批次讀取；處理失敗時會重試，可設定 bisect batch、最大重試次數與失敗目的地，避免一筆壞資料卡住整個 shard。④ 後續工作與寫入路徑解耦，任何一個下游變慢都不影響使用者。

同一個 stream shard 建議最多兩個消費者同時讀取。需要更多消費者、更長保留期或使用 Kinesis 生態系工具時，改用 **Kinesis Data Streams for DynamoDB**：把變更送到你指定的 Kinesis data stream（第 31 章），保留期可延長、支援 enhanced fan-out，但 record 順序與去重要自己處理。

## 27.11 DAX：微秒級的讀取快取

搶購頁面上，同一批熱門旅館的資料每秒被讀取上萬次。DynamoDB 的毫秒級延遲已經很快，但頁面要組合上百個 item 時，每個幾毫秒累積起來就很可觀，熱門 item 也可能形成熱分割。

**DAX（DynamoDB Accelerator）** 是專為 DynamoDB 設計的受管記憶體快取：

- **API 相容**：應用程式改用 DAX client，呼叫方式和 DynamoDB 一樣（`GetItem`、`Query`…），幾乎不用改程式。
- 快取命中時延遲降到**微秒級**，並把大量重複讀取從 DynamoDB 移走，降低 RCU 消耗。
- 有兩種快取：**item cache**（`GetItem`／`BatchGetItem` 的結果）與 **query cache**（`Query`／`Scan` 的結果），各有 TTL（預設 5 分鐘）。
- **Write-through**：透過 DAX 寫入時，DAX 先寫 DynamoDB、成功後更新 item cache。
- **只快取 eventually consistent read**。Strongly consistent read 會直接穿透到 DynamoDB，不經過快取。
- DAX cluster 部署在你的 VPC 裡，由多個 node 組成（建議至少 3 個 node 分散在多個 AZ）。

DAX 不適合的情況：寫入為主的工作負載、需要 strongly consistent 的讀取、每次讀取的 key 都不同（命中率低）。需要快取 DynamoDB 以外的資料、或需要 Redis 資料結構（排行榜、計數器）時，改用 ElastiCache（第 28 章）。

## 27.12 Global tables：多 Region 都能讀寫

Wanderly 的會員遍布台灣、日本與美國。會員資料若只放在東京 Region，美國使用者每次讀寫都要跨太平洋；東京 Region 出事時也無法服務。

**DynamoDB global tables** 讓同一個 table 在多個 Region 各有一份 **replica（副本）**，每個 replica 都**可以讀也可以寫**（multi-active）：

- **MREC（multi-Region eventual consistency）**：預設模式。寫入在本地 Region 完成後立即回應，再非同步複寫到其他 Region，通常在一秒左右完成。若兩個 Region 幾乎同時修改同一個 item，以 **last writer wins（最後寫入者勝）** 解決衝突：時間較晚的寫入覆蓋較早的。Strongly consistent read 只保證讀到「本 Region」的最新寫入。
- **MRSC（multi-Region strong consistency）**：較新的模式，寫入會同步確認到其他 Region 後才回應，任何 Region 的 strongly consistent read 都能讀到最新資料，RPO 為零。代價是寫入延遲較高，且有不少限制：必須剛好部署在三個 Region（三個 replica，或兩個 replica 加一個不能讀寫、由 DynamoDB 管理的 **witness**），只能使用支援 MRSC 的 Region，只能從空 table 轉換，建立後不能再增加 replica；**不支援 transactions、TTL 與 LSI**。兩個 Region 同時修改同一個 item 時，其中一個寫入會收到 `ReplicatedWriteConflictException`，可以重試。
- 每個 replica 是完整的 table。Capacity mode 與寫入容量（含 write auto scaling）會在所有 replica 間同步，讀取容量則可以依 Region 個別覆寫。
- 複寫寫入也會消耗目的 Region 的寫入容量，並有跨 Region 資料傳輸費。

> [!tip] 考試提示：global tables 與衝突
> 題目寫「多個 Region 都要低延遲讀寫、Region 故障時其他 Region 繼續服務」→ global tables。若同一個 item 會在多個 Region 被同時修改，MREC 會以 last writer wins 丟掉其中一個寫入；常見的設計是讓每筆資料有一個「主要 Region」（例如依會員所在地路由寫入），或在 MRSC 適用時使用 MRSC。

## 27.13 備份、還原與匯出

### 兩種備份

- **On-demand backup（隨需備份）**：手動或排程建立的完整備份，不消耗 table 容量、不影響效能，保留到你刪除為止。適合長期保存與法規需求。也可以透過 **AWS Backup** 管理，取得跨帳號、跨 Region 複製與集中政策（第 34 章）。
- **PITR（Point-in-time recovery）**：開啟後持續備份，可還原到保留期間（最多 35 天，可設定較短）內的任意一秒。用來處理「程式 bug 寫壞了資料」這類人為錯誤。

兩種還原都**建立一個新的 table**，不會覆蓋原 table。這點和第 26 章的 RDS 一樣。還原時還要注意：新 table 不會自動帶上原本的 **auto scaling 設定、IAM policy、CloudWatch alarm、tag、Streams 與 TTL 設定**，這些都要在還原後重新設定（用 IaC 管理會輕鬆很多，第 37 章）。

### Export to S3 與 import

分析團隊想每天分析訂單資料。直接 Scan 會消耗大量 RCU（27.6 節算例四），還會影響線上流量。**Export to S3** 從 PITR 的備份資料匯出，**完全不消耗 table 的讀取容量**：

- 前提是 table 已開啟 PITR。
- 支援完整匯出（某個時間點的整份資料）與增量匯出（某段時間內的變更）。
- 格式為 DynamoDB JSON 或 Amazon Ion，匯出後可用 Athena 查詢或交給 Glue 轉成 Parquet（第 30 章）。
- 可以匯出到其他帳號的 S3 bucket。

反方向的 **import from S3** 可以把 S3 上的 CSV、DynamoDB JSON 或 Ion 檔案匯入成一個新的 table，同樣不消耗寫入容量，適合初次載入大量資料。此外，DynamoDB 也提供到 Redshift、OpenSearch 等服務的 zero-ETL integration，可以免自建管線把資料同步過去。

## 27.14 安全：加密與 fine-grained access control

### 加密

- **靜態加密一律開啟，無法關閉**。可選的 key 有三種：AWS owned key（預設，不收費、看不到）、AWS managed key（`aws/dynamodb`，在 CloudTrail 可看到使用紀錄）、customer managed key（你控制 key policy 與輪替，第 15 章）。
- 傳輸加密：DynamoDB API 一律走 HTTPS。
- 網路：private subnet 的應用程式透過 **gateway VPC endpoint** 存取 DynamoDB，流量不經過 NAT Gateway 也不走 Internet（第 6 章）；endpoint policy 可以限制能存取哪些 table。

### Fine-grained access control

Wanderly 的 App 讓使用者直接從手機讀寫自己的行程（透過 Cognito 取得臨時 AWS 憑證，第 13 章）。要保證每個使用者**只能存取 partition key 等於自己 ID 的 item**，可以在 IAM policy 使用條件鍵 `dynamodb:LeadingKeys`：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:ap-northeast-1:111122223333:table/WanderlyTrips",
      "Condition": {
        "ForAllValues:StringEquals": {
          "dynamodb:LeadingKeys": ["${cognito-identity.amazonaws.com:sub}"]
        }
      }
    }
  ]
}
```

`${cognito-identity.amazonaws.com:sub}` 是 policy variable，會被替換成呼叫者的 Cognito identity ID。所以每個使用者拿到的雖然是同一個 IAM role，實際能碰到的只有自己的 item collection。如果要隔離的單位是「租戶」而不是個別使用者，可以讓 Cognito identity pool 把使用者的租戶屬性對應成 session 的 principal tag，條件改寫成 `${aws:PrincipalTag/tenant_id}`，這就是第 12 章介紹的 ABAC。`StringEquals` 要求 partition key 完全等於該值；若 partition key 的格式是 `tenant_id#entity_id` 這種「租戶 ID 加後綴」，要改用 `ForAllValues:StringLike` 搭配 `${aws:PrincipalTag/tenant_id}#*` 做前綴比對。另外要注意 `LeadingKeys` 只對指定 key 的操作（`GetItem`、`Query` 等）有效，不要把 `Scan` 授權給這類 role。另一個條件鍵 `dynamodb:Attributes` 可以限制能讀寫哪些屬性，例如禁止使用者修改 `points` 欄位。多租戶 SaaS 也常用同樣的手法，以 tenant ID 作為 partition key 前綴並用 `LeadingKeys` 隔離租戶（第 49 章）。

DynamoDB 也支援 **resource-based policy**，直接附加在 table 或 stream 上（table 的 policy 同時涵蓋它的 index），方便跨帳號授權存取。

## 27.15 設計模式：大物件與 single-table design

### 大物件放 S3

Wanderly 想把旅館的房型照片和 PDF 行程單也存起來。照片動輒數 MB，超過 item 400 KB 的上限；就算沒超過，大 item 也會讓每次讀寫消耗大量 RCU／WCU。標準做法是：

- **大物件放 S3**（第 22 章），DynamoDB item 只存 S3 的 bucket 與 key（以及大小、content type 等中繼資料）。
- 應用程式先查 DynamoDB 拿到物件位置，再用 presigned URL 讓使用者直接從 S3 或 CloudFront 下載。
- 中等大小但很少讀的屬性（例如長篇旅館介紹），可以拆成另一個 item，避免每次讀取基本資料都付它的容量。

### Single-table design

關聯式資料庫的習慣是一個實體一張表。DynamoDB 不能 JOIN，若「會員」「訂單」「訂單明細」各一張表，顯示一張訂單就要對三張表發三次請求。**Single-table design（單表設計）** 把多種實體放進同一張 table，用**泛用的 key 名稱**（`PK`、`SK`）和**有前綴的 key 值**區分實體，讓相關的資料落在同一個 item collection：

| PK | SK | 實體 | 其他屬性 |
|---|---|---|---|
| `MEMBER#81723` | `PROFILE` | 會員資料 | `name`、`email`、`points` |
| `MEMBER#81723` | `ORDER#2026-11-01#A913` | 訂單摘要 | `hotel_id`、`total`、`status` |
| `MEMBER#81723` | `ORDER#2026-12-20#B220` | 訂單摘要 | … |
| `ORDER#A913` | `ITEM#1` | 訂單明細 | `room_type`、`nights` |
| `ORDER#A913` | `ITEM#2` | 訂單明細 | … |

- 「會員中心首頁」：`Query PK = MEMBER#81723`，一次拿到會員資料與所有訂單摘要。
- 「最近的訂單」：`Query PK = MEMBER#81723 AND begins_with(SK, "ORDER#2026-")`，因為 sort key 以日期開頭，自然依時間排序。
- 「依旅館查訂單」：建立 GSI，以 `hotel_id` 為 partition key、`SK` 為 sort key。不同實體共用同一個 GSI 的做法稱為 **GSI overloading**。

Single-table design 讓讀取效率最高，但代價是 schema 較難理解、新增存取模式時可能要調整 key 或加 GSI。考試不會考你設計完整的單表，但會考它背後的觀念：**依存取模式設計 key、把一起讀的資料放在同一個 partition key 下**。

## 27.16 比較與選型

### DynamoDB 還是關聯式資料庫？

| 需求 | DynamoDB | RDS／Aurora（第 26 章） |
|---|---|---|
| 存取模式固定、以 key 查詢 | 非常適合 | 可以 |
| 臨時查詢、複雜 JOIN、報表 | 不適合 | 適合 |
| 流量可能瞬間放大百倍 | 適合（on-demand） | 需要預先擴容、連線受限 |
| Lambda 大量並行 | 無連線問題 | 需要 RDS Proxy |
| 多 Region 都要寫入 | Global tables | Global Database 只有一個寫入 Region |
| 單筆資料大於 400 KB | 不行，大物件放 S3 | 可以（但大物件也建議放 S3） |
| 複雜交易、外鍵約束 | 有限的 transactions（100 個動作） | 完整 ACID |
| 營運負擔 | 最低（無 instance、無修補） | 低（仍有 instance、維護時間） |

### DynamoDB 功能選擇

```text
DynamoDB 需求是什麼？
├─ 讀取延遲要微秒、重複讀取很多 → DAX
├─ 依非 key 屬性查詢
│   ├─ 要 strongly consistent、partition key 相同、建表前就知道 → LSI
│   └─ 其他情況（可事後新增、key 完全不同）→ GSI
├─ 資料自動過期 → TTL
├─ 資料變更要觸發處理 → Streams + Lambda（需要更多消費者或更長保留 → Kinesis Data Streams for DynamoDB）
├─ 多個 item 要一起成功或失敗 → Transactions（+ ClientRequestToken）
├─ 防止併發覆寫 → Condition expression／optimistic locking
├─ 多 Region 讀寫 → Global tables（MREC；需要跨 Region 強一致評估 MRSC）
├─ 誤寫資料要回復 → PITR（還原成新 table）
├─ 長期保存或跨帳號備份 → On-demand backup／AWS Backup
└─ 分析大量資料、不影響線上 → Export to S3 + Athena
```

## 27.17 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 計算 RCU：item X KB、每秒 N 次 strongly／eventually | ceil(X÷4) × N（eventually 再 ÷2，transactional ×2） |
| 計算 WCU | ceil(X÷1) × N（transactional ×2） |
| 總容量充足但仍被 throttle | 熱分割：改用高基數 partition key 或 write sharding |
| 流量無法預測、新應用、尖峰暴增 | On-demand capacity |
| 穩定可預測的流量、降低成本 | Provisioned + auto scaling（+ reserved capacity） |
| 依另一個屬性查詢、table 已上線 | GSI |
| 同 partition key 不同排序、需要 strongly consistent | LSI（只能建表時建立） |
| 微秒級讀取延遲、最少程式修改 | DAX |
| 自動刪除過期資料且不耗 WCU | TTL |
| 資料變更時觸發 Lambda | DynamoDB Streams |
| 多個 item 全有或全無 | TransactWriteItems |
| 多 Region active-active、低延遲 | Global tables |
| 誤刪或錯誤寫入要回到某個時間點 | PITR |
| 分析 DynamoDB 資料、不影響線上容量 | Export to S3（需 PITR）+ Athena |
| 使用者只能存取自己的資料 | IAM 條件 `dynamodb:LeadingKeys` |
| 物件大於 400 KB | 存 S3，DynamoDB 存指標 |
| 大量資料很少存取，儲存費用高 | Standard-IA table class |

**常見陷阱**：

1. 以為 FilterExpression 或 ProjectionExpression 會減少 RCU。容量依讀取的資料量計算，filter 在讀取後才套用。
2. 對 GSI 要求 strongly consistent read。GSI 只支援 eventually consistent。
3. 以為 LSI 可以在 table 建立後新增。只有 GSI 可以。
4. 以為 on-demand 永遠不會 throttle。熱分割與超過先前尖峰兩倍的瞬間流量仍可能被 throttle。
5. 以為 TTL 會在到期那一秒刪除。刪除通常在數天內才完成，查詢時要自己過濾。
6. 以為 DAX 能加速寫入或 strongly consistent read。DAX 只快取 eventually consistent 讀取。
7. 以為 PITR 會原地還原。它建立新 table，而且不帶 auto scaling、alarm、Streams 等設定。
8. 計算 Query 容量時逐筆取整。Query 與 Scan 是把回傳 item 的大小加總後再以 4 KB 取整。

## 27.18 SAP 加深：多 Region、遷移與大規模營運

### 多 Region 架構的衝突策略

SAP 題目的 global tables 常附帶「同一筆資料可能在兩個 Region 被修改」。可選的策略：

1. **Home Region 路由**：每筆資料指定一個寫入 Region（例如會員註冊地），用 Route 53 或應用程式邏輯把寫入導到該 Region；其他 Region 只讀。衝突幾乎不會發生，Region 故障時再改變路由。
2. **設計成不衝突的寫入**：把「修改同一個 item」改成「新增不同 item」，例如點數異動以事件的形式各自寫成一筆，餘額再由彙總產生。
3. **MRSC**：需要跨 Region 強一致且 Region 組合符合限制時使用，接受較高的寫入延遲。
4. **回到單一寫入 Region**：業務規則必須強一致且 MRSC 不適用時，選第 26 章的 Aurora Global Database（單一寫入 Region）或 Aurora DSQL。

### 從關聯式資料庫遷移到 DynamoDB

把 Oracle 或 MySQL 的某個功能改用 DynamoDB，不是「把 table 原樣搬過去」。正確的順序是：列出所有存取模式與其頻率 → 設計 key 與 GSI → 用 AWS DMS（以 DynamoDB 為 target）或 import from S3 搬資料 → 用雙寫或 Streams 驗證一致性後切換。若存取模式大量依賴臨時 JOIN 與報表，應保留關聯式資料庫，只把高流量、key-value 型的部分（購物車、session、庫存計數）拆出來。

### 多帳號與大規模營運

- **成本可視化**：為 table 加上成本分配 tag；用 CloudWatch 的 `ConsumedReadCapacityUnits`、`ThrottledRequests` 找出過度配置與容量不足的 table。
- **治理**：以 AWS Config rule 檢查 PITR 是否開啟、是否使用 customer managed key；以 SCP 禁止刪除 production table 或關閉 PITR（第 14 章）。
- **跨帳號備份隔離**：用 AWS Backup 把 DynamoDB 備份複製到獨立的備份帳號與 Region。
- **大量讀取的分析**：把 Export to S3 排程化，或使用 zero-ETL integration，讓分析流量完全離開線上 table。

> [!sap] SAP 加深：on-demand 與 provisioned 的成本交叉點
> On-demand 的單位請求價格高於 provisioned 的單位容量價格，但 provisioned 要為「配置但沒用到」的容量付費。若 provisioned 的平均使用率很低（例如流量只有尖峰的一小部分且尖峰短暫），on-demand 通常更便宜；若流量穩定且能以 auto scaling 把使用率維持在高水準，再加上 reserved capacity，provisioned 明顯更省。SAP 題目常要你根據流量曲線在兩者間取捨。

## 本章重點整理

- DynamoDB 是 serverless、Regional、自動跨 AZ 複寫的 key-value／document 資料庫，透過 HTTPS API 存取，沒有連線數問題，適合存取模式固定、流量可能暴增的工作負載。
- 設計順序是「先列存取模式，再設計 key」；primary key 是 partition key 或 partition key + sort key，建表後不能修改；單一 item 最大 400 KB。
- Partition key 的雜湊值決定資料在哪個 partition；每個 partition 約 10 GB、每秒最多 3,000 RCU 與 1,000 WCU，單一 key 的流量無法超過這個上限。
- 熱分割的解法是高基數 partition key、write sharding 與快取；adaptive capacity 與 burst capacity 只能緩和。
- 1 RCU = 每秒一次 4 KB 的 strongly consistent 讀取，eventually consistent 減半、transactional 加倍；1 WCU = 每秒一次 1 KB 寫入，transactional 加倍；大小向上取整。
- Query 與 Scan 依回傳 item 的合計大小取整，FilterExpression 與 ProjectionExpression 都不減少 RCU；分析需求用 Export to S3 而非 Scan。
- On-demand 適合未知或劇烈波動的流量；provisioned 搭配 auto scaling 與 reserved capacity 適合可預測流量；auto scaling 接不住秒級暴增。
- LSI 與 base table 同 partition key、只能建表時建立、最多 5 個、支援 strongly consistent；GSI 可用任意 key、隨時新增、容量獨立、只有 eventually consistent，且 GSI 容量不足會 throttle base table 寫入。
- Condition expression 與 optimistic locking 防止併發覆寫；TransactWriteItems 最多 100 個動作、容量加倍，ClientRequestToken 提供冪等性。
- TTL 以 epoch 秒數自動刪除過期 item、不耗 WCU，但刪除可能延後數天；Streams 依 item 順序保留 24 小時的變更，常搭配 Lambda。
- DAX 是 API 相容的記憶體快取，提供微秒級讀取，只快取 eventually consistent 讀取、採 write-through。
- Global tables 讓多個 Region 都能讀寫：MREC 非同步複寫、last writer wins；MRSC 提供跨 Region 強一致但有 Region 組合與功能限制。
- PITR（最多 35 天）與 on-demand backup 都還原成新 table，auto scaling、alarm、Streams、TTL 等設定要重新設定；Export to S3 需要 PITR 且不耗讀取容量。
- 靜態加密一律開啟；`dynamodb:LeadingKeys` 條件讓每個使用者或租戶只能存取自己的 partition key。
- 大物件放 S3、DynamoDB 存指標；single-table design 把一起讀的資料放在同一個 item collection，用 Query 一次取回。

## 本章練習題

### 練習 27-1｜SAA｜單選｜RCU 計算

Wanderly 的旅館資料表中，每個 item 平均 7 KB。旅館詳細頁面每秒讀取 150 次，因為頁面上顯示即時剩餘房數，產品要求每次都讀到最新資料。這個 table 使用 provisioned 模式。

至少需要配置多少 RCU？

- A. 150 RCU
- B. 263 RCU
- C. 300 RCU
- D. 600 RCU

> [!answer]- 答案：C
> **A ✗** 這是把每次讀取都當成 1 RCU 的結果，忽略了 7 KB 超過 4 KB 的單位大小。
>
> **B ✗** 這是用 7 ÷ 4 = 1.75 直接乘以 150 的結果。容量計算要先把 item 大小向上取整到 4 KB 的倍數，不能用小數。
>
> **C ✓** 「每次都讀到最新資料」代表 strongly consistent read。ceil(7 ÷ 4) = 2 個單位，150 × 2 × 1 = 300 RCU。
>
> **D ✗** 這是 transactional read 的容量（再乘 2）。題目沒有要求多個 item 的交易讀取，一般的 strongly consistent read 就足夠。
>
> **考點**：SAA-3.3｜RCU 計算：4 KB 向上取整、strongly consistent

### 練習 27-2｜SAA｜單選｜WCU 計算

Wanderly 的會員點數兌換使用 `TransactWriteItems`，每次交易寫入兩個 item：會員資料（2.5 KB）與兌換紀錄（0.5 KB）。尖峰時每秒有 40 次兌換交易。

這些交易每秒會消耗多少 WCU？

- A. 80 WCU
- B. 120 WCU
- C. 160 WCU
- D. 320 WCU

> [!answer]- 答案：D
> **A ✗** 這是把每個 item 都當 1 WCU、也沒有乘上交易係數的結果：40 × 2 = 80。
>
> **B ✗** 這是 2.5 KB 取整為 3、0.5 KB 為 0（錯誤地省略），且未乘交易係數的結果。小於 1 KB 的寫入仍要 1 個單位。
>
> **C ✗** 這是正確算出單位數（3 + 1 = 4）但沒有乘上交易係數 2 的結果：40 × 4 = 160。
>
> **D ✓** 會員資料 ceil(2.5) = 3 個單位、兌換紀錄 ceil(0.5) = 1 個單位，每次交易共 4 個單位；transactional 寫入加倍為 8 WCU；40 × 8 = 320 WCU。
>
> **考點**：SAA-3.3、SAA-4.3｜WCU 計算：1 KB 向上取整、transactional 加倍

### 練習 27-3｜SAA｜單選｜Query 的容量計算

Wanderly 的行程頁面用 `Query` 讀取某位會員的所有行程項目，每次平均回傳 30 個 item，每個 item 0.5 KB，使用 eventually consistent read，尖峰每秒 100 次 Query。

這些 Query 每秒大約消耗多少 RCU？

- A. 200 RCU
- B. 400 RCU
- C. 1,500 RCU
- D. 3,000 RCU

> [!answer]- 答案：A
> **A ✓** Query 依回傳 item 的合計大小計算：30 × 0.5 KB = 15 KB，向上取整到 16 KB，即 4 個 4 KB 單位。Eventually consistent 減半為 2 RCU，100 次 × 2 = 200 RCU。
>
> **B ✗** 這是 strongly consistent 的結果（每次 4 RCU）。題目使用 eventually consistent。
>
> **C ✗** 這是把 30 個 item 逐筆取整（每個 1 單位 × 0.5 = 0.5 RCU，共 15 RCU）的結果，那是 30 次 GetItem 的算法，不是 Query。
>
> **D ✗** 這是逐筆取整又使用 strongly consistent 的結果。
>
> **考點**：SAA-3.3｜Query 合計大小後再以 4 KB 取整

### 練習 27-4｜SAA｜單選｜熱分割

Wanderly 建立了一個點擊事件 table，以 `event_date`（例如 `2026-11-01`）為 partition key、`event_time` 為 sort key，使用 provisioned 模式並配置了 20,000 WCU。實際寫入量約每秒 5,000 WCU，但 CloudWatch 顯示大量寫入被 throttle。

最可能的原因與修正方式是什麼？

- A. 配置的 WCU 不足，應把 provisioned WCU 提高到 40,000
- B. 當天所有寫入都集中在同一個 partition key 值，超過單一 partition 的寫入上限；應改用高基數的 key，或在日期後加上分片後綴分散寫入
- C. Sort key 的值重複造成衝突，應把 `event_time` 改為更精細的時間戳記
- D. Provisioned 模式不支援每秒超過 1,000 次寫入，應改用 DAX 緩衝寫入

> [!answer]- 答案：B
> **A ✗** Table 總容量（20,000 WCU）遠高於實際使用量，加更多容量也無法讓單一 partition key 突破每個 partition 每秒約 1,000 WCU 的上限。
>
> **B ✓** Partition key 決定資料落在哪個 partition，同一天的事件全部共用一個 key 值，形成熱分割。改用高基數 key，或用 write sharding（例如 `2026-11-01#0`～`#9`）讓寫入分散到多個 partition，是根本解法。
>
> **C ✗** Sort key 不參與 partition 的決定，讓它更精細無法分散流量。
>
> **D ✗** Provisioned 模式的 table 可以支援遠超過 1,000 WCU，限制是在單一 partition。DAX 是讀取快取，不會緩衝或加速寫入。
>
> **考點**：SAA-3.3｜partition key 設計與熱分割

### 練習 27-5｜SAA｜單選｜選擇 capacity mode

Wanderly 即將推出新的「旅遊直播」功能，聊天訊息存放在 DynamoDB。團隊完全無法預測上線後的流量：可能幾乎沒人用，也可能在網紅直播時瞬間暴增。團隊希望不需要做容量規劃，並且只為實際使用的量付費。

應如何設定 table？

- A. 使用 on-demand capacity mode
- B. 使用 provisioned 模式並配置預估尖峰的兩倍容量
- C. 使用 provisioned 模式搭配 auto scaling，最小值設為 1
- D. 使用 provisioned 模式並購買一年的 reserved capacity

> [!answer]- 答案：A
> **A ✓** On-demand 不需要預先指定容量，依實際請求計費，會自動依流量調整，最適合無法預測的新應用。若事前知道某場直播會有大流量，還可以預熱 table。
>
> **B ✗** 在流量未知時配置兩倍尖峰，平時大部分容量閒置也要付費，違反「只為實際使用付費」。
>
> **C ✗** Auto scaling 需要幾分鐘才會反應，瞬間暴增的流量會在擴展完成前被 throttle；最小值 1 更讓尖峰初期幾乎無法承受。
>
> **D ✗** Reserved capacity 需要對穩定的基礎流量做長期承諾，不適合流量未知的新功能。
>
> **考點**：SAA-4.3、SAA-3.3｜on-demand 與 provisioned 的選擇

### 練習 27-6｜SAA｜單選｜為既有 table 新增查詢方式

Wanderly 的會員 table 以 `member_id` 為 partition key，已經上線兩年。客服系統現在需要依 email 快速找到會員，目前只能用 Scan 搭配 FilterExpression，每次都耗費大量 RCU 且速度很慢。客服系統可以接受資料有一秒左右的延遲。

最合適的做法是什麼？

- A. 建立以 `email` 為 sort key 的 LSI
- B. 保留 Scan，但加上 ProjectionExpression 只回傳需要的屬性以降低 RCU
- C. 把 FilterExpression 改為 KeyConditionExpression
- D. 建立以 `email` 為 partition key 的 GSI，並只投影客服需要的屬性

> [!answer]- 答案：D
> **A ✗** LSI 只能在建立 table 時一起建立，而且 partition key 必須和 base table 相同，無法以 email 作為查詢入口。
>
> **B ✗** ProjectionExpression 只減少回傳的資料量，DynamoDB 仍然讀取整個 item 並依其大小計算 RCU，Scan 的成本不變。
>
> **C ✗** KeyConditionExpression 只能使用 table 或 index 的 key 屬性。`email` 不是 base table 的 key，不能直接用來 Query。
>
> **D ✓** GSI 可以在 table 上線後新增，以 `email` 為 partition key 就能用 Query 直接找到會員。GSI 是 eventually consistent，符合「可接受一秒延遲」；只投影需要的屬性能降低 index 的寫入與儲存成本。
>
> **考點**：SAA-3.3｜GSI 支援新的存取模式

### 練習 27-7｜SAA｜單選｜需要強一致的替代排序

Wanderly 正在設計一個新的行程 table，以 `trip_id` 為 partition key、`item_seq` 為 sort key。產品另外需要「在同一個行程內，依出發時間排序列出項目」，而且使用者修改後必須立即看到正確的排序（需要 strongly consistent read）。Table 尚未建立。

最合適的設計是什麼？

- A. 之後再建立一個以 `trip_id` 為 partition key、`depart_at` 為 sort key 的 GSI
- B. 用 Query 讀出整個行程，再在應用程式端依 `depart_at` 排序，並對 Query 使用 eventually consistent read
- C. 建立 table 時一起建立 LSI，partition key 為 `trip_id`、sort key 為 `depart_at`
- D. 把 `depart_at` 加入 partition key，改成 `trip_id#depart_at`

> [!answer]- 答案：C
> **A ✗** GSI 只支援 eventually consistent read，不符合強一致的要求。
>
> **B ✗** 在應用程式排序在項目很少時可行，但題目同時要求 strongly consistent，這個選項卻使用 eventually consistent；而且行程項目多時，每次都要讀出整個 collection。
>
> **C ✓** LSI 與 base table 使用相同的 partition key、提供替代的 sort key，並支援 strongly consistent read。LSI 只能在建立 table 時定義，題目說 table 尚未建立，正好可以這麼做。需注意每個 `trip_id` 的 item collection 不能超過 10 GB。
>
> **D ✗** 把時間放進 partition key 會讓同一個行程的項目分散到不同 item collection，無法再用一次 Query 取出整個行程。
>
> **考點**：SAA-3.3｜LSI 的特性與建立時機

### 練習 27-8｜SAA｜選兩項｜過期資料與變更通知

Wanderly 的購物車 table 有兩個需求：第一，超過 30 天未結帳的購物車項目要自動刪除，而且不想為刪除付出寫入容量；第二，每當訂單 table 中的訂單狀態變成 `PAID`，要寄出確認信，寄信失敗不能影響下單 API 的回應。

哪兩個做法能滿足需求？（選兩項）

- A. 在購物車 item 寫入 Unix epoch 秒數的 `expires_at` 屬性，並在 table 上啟用 TTL
- B. 每天用 EventBridge Scheduler 觸發 Lambda，Scan 購物車 table 並刪除過期項目
- C. 在訂單 table 啟用 DynamoDB Streams（`NEW_AND_OLD_IMAGES`），由 Lambda 讀取 stream，在狀態從其他值變成 `PAID` 時寄信
- D. 在下單 API 中，於寫入 DynamoDB 之後同步呼叫寄信服務，寄信成功才回應使用者
- E. 把購物車 table 改為 Standard-IA table class，讓過期資料自動移除

> [!answer]- 答案：A、C
> **A ✓** TTL 依 epoch 秒數屬性在背景刪除過期 item，不消耗 WCU。刪除可能延後數天，若畫面要精確隱藏過期項目，查詢時再加條件過濾。
>
> **B ✗** Scan 會消耗大量 RCU，每筆刪除也要消耗 WCU，正是 TTL 要避免的做法。
>
> **C ✓** Streams 依序記錄每次變更，`NEW_AND_OLD_IMAGES` 讓 Lambda 能判斷狀態是否「剛變成」PAID，避免重複寄信。寄信在非同步路徑執行，失敗時重試也不影響 API。
>
> **D ✗** 同步呼叫讓寄信的延遲與失敗直接影響下單 API，違反需求。
>
> **E ✗** Table class 只影響儲存與讀寫的計價，不會刪除任何資料。
>
> **考點**：SAA-2.1、SAA-3.3｜TTL 與 DynamoDB Streams

### 練習 27-9｜SAA｜單選｜讀取延遲降到微秒

Wanderly 的首頁每秒讀取數萬次相同的熱門旅館資料（存放在 DynamoDB），使用 eventually consistent 的 `GetItem` 與 `Query`。現在每次讀取約 5 毫秒，產品希望降到微秒級，並降低 RCU 費用。開發團隊希望程式修改越少越好。

最合適的做法是什麼？

- A. 把 table 改為 on-demand 模式
- B. 部署 DAX cluster，讓應用程式改用 DAX client 存取 table
- C. 建立一個 GSI 專門給首頁使用
- D. 把讀取改為 strongly consistent，讓 DynamoDB 直接從 leader 副本回傳

> [!answer]- 答案：B
> **A ✗** Capacity mode 影響計費與擴展方式，不會降低單次讀取延遲。
>
> **B ✓** DAX 與 DynamoDB API 相容，只需改用 DAX client；它快取 eventually consistent 讀取，命中時延遲降到微秒級，重複讀取不再消耗 table 的 RCU。
>
> **C ✗** GSI 提供新的查詢入口，延遲仍是毫秒級，而且會增加寫入成本。
>
> **D ✗** Strongly consistent read 消耗兩倍 RCU，延遲不會降低，也不會被 DAX 快取。
>
> **考點**：SAA-3.3｜DAX 的適用情境

### 練習 27-10｜SAA｜單選｜存放大型檔案

Wanderly 想讓旅館業者上傳房型照片（每張 1–5 MB）與 PDF 簡介，並在 App 中與房型資料一起顯示。房型資料已存放在 DynamoDB。團隊希望架構簡單、讀取房型資料時不要消耗大量容量。

最合適的做法是什麼？

- A. 把檔案存放在 S3，在 DynamoDB 的房型 item 中保存物件的 bucket、key 與中繼資料
- B. 把檔案以 Base64 編碼後存入 DynamoDB item 的 Binary 屬性
- C. 把每個檔案切成 400 KB 的區塊，分別存成多個 DynamoDB item
- D. 開啟 DynamoDB 的壓縮功能，讓大於 400 KB 的 item 自動壓縮後存入

> [!answer]- 答案：A
> **A ✓** DynamoDB 單一 item 最大 400 KB。大物件放在 S3、DynamoDB 存指標是標準做法；讀取房型資料時只讀小 item，檔案再透過 presigned URL 或 CloudFront 直接下載。
>
> **B ✗** 1–5 MB 的檔案超過 400 KB 上限，Base64 編碼還會讓資料再變大約三分之一。
>
> **C ✗** 技術上可行，但每次讀取都要消耗大量 RCU 並在應用程式組裝，複雜度與成本都很高。
>
> **D ✗** DynamoDB 沒有讓 item 突破 400 KB 上限的壓縮功能；應用程式可以自行壓縮屬性，但無法讓數 MB 的檔案放進一個 item。
>
> **考點**：SAA-3.1、SAA-4.3｜item 400 KB 上限與 S3 搭配

### 練習 27-11｜SAP｜單選｜多租戶資料隔離

Wanderly 推出給旅行社使用的 SaaS 平台，所有租戶的資料放在同一個 DynamoDB table，partition key 為 `tenant_id#entity_id`。每個租戶的使用者登入後，會透過 Cognito identity pool 取得同一個 IAM role 的臨時憑證，直接存取 DynamoDB。安全審查要求：即使應用程式有 bug，租戶也不可能讀寫其他租戶的資料。

最合適的做法是什麼？

- A. 為每個租戶建立獨立的 table，並在應用程式中依租戶切換 table 名稱
- B. 在應用程式的每一個查詢中加上 FilterExpression，過濾掉不屬於該租戶的 item
- C. 在 IAM policy 中使用 `dynamodb:LeadingKeys` 條件，限制只能存取 partition key 以該租戶 ID 開頭的 item，租戶 ID 來自身份 token 的 principal tag 或 policy variable
- D. 在 DynamoDB table 上啟用 customer managed key，為每個租戶使用不同的 KMS key

> [!answer]- 答案：C
> **A ✗** 每租戶一個 table 可以隔離，但若 IAM 權限仍允許存取所有 table，應用程式 bug 依然可能讀錯 table；而且大量租戶時 table 數量與營運負擔會快速增加。
>
> **B ✗** FilterExpression 由應用程式自己加，bug 正好可能漏掉它；它也不減少讀取容量，不是安全邊界。
>
> **C ✓** `dynamodb:LeadingKeys` 在 IAM 層強制檢查請求的 partition key（本題的 key 是「租戶 ID 加後綴」，所以用 `StringLike` 與 `<租戶 ID>#*` 做前綴比對），租戶身份來自驗證後的 token（principal tag 或 policy variable），應用程式無法偽造。即使程式有 bug，跨租戶的請求也會被 IAM 拒絕。
>
> **D ✗** DynamoDB 的 KMS key 以 table 為單位設定，不能依 item 使用不同的 key；靜態加密也不控制「誰能透過 API 讀取」。
>
> **考點**：SAP-2.3、SAP-1.2｜fine-grained access control 與多租戶隔離

### 練習 27-12｜SAP｜單選｜多 Region 低延遲讀寫

Wanderly 的會員資料（偏好設定、收藏清單）放在東京 Region 的 DynamoDB。美國與歐洲的使用者抱怨每次修改設定都要等很久。公司要求三個地區的使用者都能在本地 Region 低延遲讀寫，且任一 Region 故障時其他 Region 能繼續服務。同一位會員的資料幾乎只會在其所在地區被修改，可以接受跨 Region 一秒左右的複寫延遲。

最合適的方案是什麼？

- A. 在美國與歐洲 Region 部署 DAX cluster，快取東京 table 的資料
- B. 用 DynamoDB Streams 觸發 Lambda，把變更寫入另外兩個 Region 的獨立 table
- C. 每小時把東京 table 匯出到 S3，再匯入另外兩個 Region
- D. 把 table 轉換為 global table，在美國與歐洲 Region 新增 replica，使用預設的 multi-Region eventual consistency 模式

> [!answer]- 答案：D
> **A ✗** DAX 只能加速 eventually consistent 讀取，而且 DAX cluster 只能存取同一個 Region 的 table，無法在美國替東京的 table 做快取；寫入仍要跨 Region 回東京，東京故障時也無法寫入。
>
> **B ✗** 自建跨 Region 複寫要自己處理衝突、重試與順序，雙向複寫還可能形成迴圈，營運負擔高。
>
> **C ✗** 每小時同步的延遲遠超過一秒，匯入也只能建立新 table，無法維持持續更新的副本。
>
> **D ✓** Global tables 讓每個 Region 的 replica 都能讀寫，通常一秒左右完成跨 Region 複寫，任一 Region 故障時其他 Region 繼續服務。會員資料幾乎只在所在地區修改，last writer wins 的衝突風險很低，MREC 模式正好適用。
>
> **考點**：SAP-2.5、SAP-1.3｜DynamoDB global tables（MREC）

### 練習 27-13｜SAP｜單選｜分析資料不影響線上

Wanderly 的訂單 table 有 2 TB 資料，使用 provisioned 模式，平時讀取使用率約 70%。資料團隊需要每天用 SQL 分析前一天的訂單變化，並保存歷史資料供機器學習使用。之前有人用 Scan 匯出資料，導致線上 API 大量 throttle。

哪個做法最合適？

- A. 為分析建立一個投影全部屬性的 GSI，讓資料團隊 Scan 這個 GSI
- B. 啟用 PITR，每天使用 DynamoDB 的增量 export to S3，並用 Athena 或 Glue 查詢與轉換資料
- C. 在凌晨把 table 的 RCU 提高三倍，Scan 完成後再調回原值
- D. 部署 DAX cluster，讓資料團隊透過 DAX 執行 Scan

> [!answer]- 答案：B
> **A ✗** Scan GSI 一樣消耗 RCU（GSI 的容量），投影全部屬性還會讓每次寫入都多一份成本。
>
> **B ✓** Export to S3 從 PITR 的備份資料匯出，不消耗 table 的讀取容量，不影響線上流量；增量匯出只匯出指定期間的變更，正好用於每日分析。匯出到 S3 後可用 Athena 以 SQL 查詢，或用 Glue 轉成 Parquet 長期保存。
>
> **C ✗** 暫時加容量可以減少 throttle，但每天都要付出大量 RCU 費用，而且 provisioned 模式的調整次數與生效時間都有限制，操作也容易出錯。
>
> **D ✗** DAX 適合重複讀取相同資料的線上流量；Scan 全表的命中率極低，大部分請求仍會落到 DynamoDB。
>
> **考點**：SAP-3.3、SAP-2.6｜Export to S3 與分析解耦

### 練習 27-14｜SAP｜選兩項｜可重試的點數兌換交易

Wanderly 的點數兌換服務要同時做三件事：扣除會員點數（點數不足要失敗）、建立兌換紀錄、扣除旅館庫存（庫存為 0 要失敗）。三件事必須全部成功或全部不發生。服務部署在 Lambda 上，網路逾時時會自動重試，不能因為重試而重複扣點。

哪兩個做法能滿足需求？（選兩項）

- A. 用 `TransactWriteItems` 把三個寫入放進同一個交易，並在扣點與扣庫存的 Update 上加 ConditionExpression
- B. 用 `BatchWriteItem` 一次送出三個寫入，失敗時重送 `UnprocessedItems`
- C. 依序執行三次 `UpdateItem`，任何一步失敗就由程式反向補回前面的修改
- D. 為每次兌換產生唯一的 `ClientRequestToken` 傳給 `TransactWriteItems`，重試時使用相同的 token
- E. 對三個 item 改用 strongly consistent read 先檢查餘額與庫存，再分別寫入

> [!answer]- 答案：A、D
> **A ✓** TransactWriteItems 提供跨 item 的 ACID 交易，ConditionExpression 確保點數或庫存不足時整個交易被取消，三個寫入全部成功或全部不執行。
>
> **B ✗** BatchWriteItem 不是交易，可能部分成功；而且它只支援 Put 與 Delete，不能附加條件檢查。
>
> **C ✗** 自己做補償可行但複雜，中途失敗或 Lambda 中斷時可能留下不一致的狀態；DynamoDB 已提供原生交易。
>
> **D ✓** ClientRequestToken 讓交易具有冪等性：同一個 token 在 10 分鐘內重送，DynamoDB 不會重複執行，避免逾時重試造成重複扣點。
>
> **E ✗** 先讀再寫存在競態：讀取與寫入之間其他請求可能已經修改資料，無法保證不超賣或不扣成負數。
>
> **考點**：SAP-2.4、SAP-3.4｜DynamoDB transactions 與冪等性

### 練習 27-15｜SAP｜單選｜錯誤部署寫壞資料

Wanderly 在 10:00 部署了一個有 bug 的版本，它在 10:00 到 10:40 之間錯誤地覆寫了會員 table 中數萬筆 item 的折扣欄位。這個 table 已開啟 PITR，使用 provisioned 模式搭配 auto scaling，並啟用了 Streams 供下游 Lambda 使用。團隊希望把資料回復到 09:59 的狀態。

最合適的復原方式是什麼？

- A. 在原 table 上執行 PITR，讓 table 原地回到 09:59 的狀態
- B. 用 DynamoDB Streams 的紀錄，把 10:00 以後的變更反向套用回去
- C. 用 PITR 把 table 還原到 09:59 成為一個新 table，在新 table 上重新設定 auto scaling、Streams、alarm 等設定，驗證後切換應用程式或把需要的資料寫回原 table
- D. 從上週的 on-demand backup 還原，因為 PITR 無法還原單一欄位

> [!answer]- 答案：C
> **A ✗** DynamoDB 的 PITR 一律還原成新 table，不能原地覆蓋。
>
> **B ✗** Streams 只保留 24 小時，雖然在本例時間內，但用它反向套用需要自行撰寫並驗證大量邏輯，還可能與 10:40 之後的合法寫入衝突，風險高且費時。
>
> **C ✓** PITR 能還原到保留期間內的任意一秒，並建立新 table。還原的 table 不會帶上 auto scaling、Streams、alarm、TTL 等設定，必須重新設定；之後可以切換應用程式，或只把受影響的資料寫回原 table。
>
> **D ✗** 上週的備份會遺失一週的合法資料。PITR 可以精確還原到 09:59，從還原的 table 取出所需欄位即可。
>
> **考點**：SAP-2.2、SAP-3.4｜PITR 還原成新 table 與需重設的設定

### 練習 27-16｜SAP｜選兩項｜DynamoDB 成本最佳化

Wanderly 有兩個 DynamoDB table 的費用偏高。第一個是房價 table，使用 on-demand 模式，過去一年的流量曲線非常穩定，每天的尖峰與離峰變化不到 30%。第二個是歷史訂單 table，存放 8 年的資料共 30 TB，99% 的資料一年內都不會被讀取，帳單顯示它的費用主要來自儲存。

哪兩個做法最能降低成本？（選兩項）

- A. 把房價 table 改為 provisioned 模式並設定 auto scaling，為穩定的基礎用量購買 reserved capacity
- B. 為房價 table 部署 DAX，以降低 on-demand 的寫入費用
- C. 把歷史訂單 table 的 table class 改為 DynamoDB Standard-IA
- D. 為歷史訂單 table 新增 GSI，只投影最常查詢的屬性
- E. 為歷史訂單 table 啟用 Streams，把資料同步到另一個 Region

> [!answer]- 答案：A、C
> **A ✓** 穩定、可預測的流量是 provisioned 模式最划算的情境：auto scaling 能維持高使用率，reserved capacity 再為基礎用量提供折扣，通常比 on-demand 便宜許多。
>
> **B ✗** DAX 只能減少讀取，寫入仍要寫到 DynamoDB，而且 DAX cluster 本身有費用。
>
> **C ✓** Standard-IA 的儲存單價明顯較低，讀寫單價較高；資料量大、很少存取、費用以儲存為主的 table 正是它的適用情境。
>
> **D ✗** 新增 GSI 會增加儲存與寫入成本，不會降低費用。
>
> **E ✗** Streams 與跨 Region 同步會增加費用，與降低儲存成本無關。
>
> **考點**：SAP-3.5、SAP-1.5｜capacity mode 與 table class 的成本最佳化
