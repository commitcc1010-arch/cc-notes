---
chapter: 31
title: Streaming 與即時資料管線
part: 5
---

# 第 31 章　Streaming 與即時資料管線：Kinesis、MSK 與 Flink

> [!abstract] 本章地圖
> **你會學到**：
> - 說清楚 batch 與 stream 處理的差別，以及什麼時候「每小時跑一次」已經不夠
> - 理解 Kinesis Data Streams 的 shard、partition key、順序保證、retention 與兩種 capacity mode，能算出需要幾個 shard
> - 分辨 shared throughput 與 enhanced fan-out、KCL 與 Lambda 兩種 consumer，並處理重複與失敗的紀錄
> - 用 Data Firehose 以最少程式把串流寫進 S3、Redshift、OpenSearch，知道 buffer 怎麼影響延遲
> - 用 Managed Service for Apache Flink 做即時視窗彙總，用 MSK 承接既有 Kafka 生態系
> - 在 Kinesis、SQS、MSK 之間做出正確選擇，並設計一條完整的 clickstream 管線
>
> **前置知識**：第 19 章（Lambda）、第 30 章（data lake 與 Parquet）；第 32 章會再談 SQS 與 SNS 的細節
> **考試比重**：SAA ★★☆（Domain 3.5 資料擷取與轉換、Domain 2.1 鬆耦合）｜SAP ★★☆（Domain 2.4–2.5 可靠性與效能、Domain 4 現代化）

## 31.1 故事：「每小時一次」來不及了

第 30 章的分析平台上線後，Wanderly 的點擊紀錄每小時由 Glue job 整理一次，行銷團隊很滿意。直到某個週五晚上，一家合作旅館的房價被設定錯誤，原本一晚 6,000 元的房間顯示成 600 元。四十分鐘內湧進三百筆訂單，等到第二天早上報表出來，損失已經造成。

營運主管問了一個簡單的問題：「如果某家旅館的訂房量在五分鐘內突然暴增十倍，我們能不能**當下**就知道？」同一週，產品團隊也提出需求：搜尋結果的「熱門旅館」排序希望反映最近十分鐘的點擊，而不是昨天的資料；資料科學家則希望使用者的每次點擊都能即時更新推薦模型的特徵。

這三個需求有一個共同點：資料的價值隨時間快速下降。一小時後才知道房價錯誤，等於沒有知道。這就是 **streaming（串流處理）** 要解決的問題：資料一產生就被處理，延遲從小時縮短到秒。

這一章要幫 Wanderly 建立即時資料管線：用 Kinesis Data Streams 接收每秒上萬筆點擊事件，用 Data Firehose 把事件持續寫進第 30 章的 data lake，用 Managed Service for Apache Flink 每分鐘計算每家旅館的訂房速率並在異常時告警，並了解為什麼併購來的旅行社會選擇 Amazon MSK。

## 31.2 Batch vs stream：兩種處理資料的思維

### Batch：先累積，再一起處理

**Batch processing（批次處理）** 是把一段時間內的資料累積起來，定時一次處理。第 30 章每小時執行的 Glue job 就是 batch。它的優點是簡單、便宜、容易重跑：處理失敗就整批再跑一次；缺點是延遲至少等於批次間隔。

### Stream：資料一到就處理

**Stream processing（串流處理）** 把資料看成一條沒有終點的事件流，每個 **event（事件）**，例如「使用者 A 在 21:03:15 點擊了旅館 B」，一產生就被送進管線、在秒級內被處理。

| 比較 | Batch | Stream |
|---|---|---|
| 延遲 | 分鐘到小時（等於批次間隔） | 毫秒到秒 |
| 資料邊界 | 有明確的開始與結束（「昨天的資料」） | 無止盡，需要用 **window（時間視窗）** 切出範圍 |
| 失敗重跑 | 整批重跑 | 從某個位置（checkpoint）繼續 |
| 典型工具 | Glue、EMR、Redshift COPY | Kinesis、MSK、Flink、Lambda |
| 適合 | 月報、模型訓練、歷史分析 | 異常偵測、即時儀表板、即時推薦、IoT 監控 |

兩者不是互斥的。實務上最常見的設計是：同一份事件流**同時**餵給即時處理（秒級告警）與 data lake（之後做 batch 分析）。本章最後組出的 Wanderly 管線就是這種架構。

### 串流系統要回答的四個問題

不論用哪個服務，設計串流系統都要回答這四個問題，後面的每一節都會回到它們：

1. **吞吐量**：每秒有多少筆、多少 MB？尖峰是平時的幾倍？
2. **順序**：哪些事件必須依序處理？（同一筆訂單的「建立 → 付款 → 取消」不能顛倒）
3. **重播（replay）**：處理程式有 bug 時，能不能回頭重新讀過去的資料？能回頭多久？
4. **多個消費者**：同一份資料要給幾個不同的程式使用？它們會不會互相影響？

> [!note] Stream 和 queue 有什麼不同？
> 第 32 章的 SQS 是 **queue（佇列）**：訊息被一個 consumer 處理並刪除後就消失，多個 consumer 是「搶工作」。Stream 則像一本**只能往後寫的日誌（log）**：資料寫入後保留一段時間，每個 consumer 各自記住自己讀到哪裡，多個 consumer 可以各自從頭讀同一份資料，讀了也不會刪除。這個差別是 31.9 節選型的核心。

## 31.3 Kinesis Data Streams：shard、partition key 與順序

### 基本模型

**Amazon Kinesis Data Streams（KDS）** 是 AWS 受管的即時資料串流服務。它的組成是：

- **Stream（串流）**：一個具名的資料流，例如 `wanderly-clickstream`。
- **Shard（分片）**：stream 的容量單位與平行單位。一個 stream 由一個或多個 shard 組成，每個 shard 是一條有序的紀錄序列。
- **Record（紀錄）**：寫入的資料單位，包含 **partition key（分區鍵）**、**sequence number（序號）** 與資料本體（data blob）。
- **Producer（生產者）**：寫入資料的程式，例如 Wanderly 的網站後端。
- **Consumer（消費者）**：讀取資料的程式，例如 Lambda、Flink 應用程式、Firehose。

### Partition key 決定資料進哪個 shard

Producer 寫入每筆紀錄時必須指定 partition key。Kinesis 對 partition key 做 MD5 hash，得到一個 128 位元的數字；每個 shard 負責一段 **hash key range**，數字落在哪一段，紀錄就進哪個 shard。

```text
 Producer: PutRecord(partitionKey="hotel-1088", data={...click...})
        │
        │ ① MD5("hotel-1088") → 0x7A3F...（128-bit 數字）
        ▼
 ┌─────────────────────── Stream: wanderly-clickstream ───────────────────────┐
 │ shard-000  hash 0x0000... ~ 0x3FFF...  │ seq 101 │ seq 102 │ seq 103 │ ...  │
 │ shard-001  hash 0x4000... ~ 0x7FFF...  │ seq 201 │ seq 202 │ seq 203 │ ◄─② │
 │ shard-002  hash 0x8000... ~ 0xBFFF...  │ seq 301 │ seq 302 │ ...            │
 │ shard-003  hash 0xC000... ~ 0xFFFF...  │ seq 401 │ ...                      │
 └────────────────────────────────────────────────────────────────────────────┘
        │ ③ 每個 consumer 記住「每個 shard 讀到哪個 sequence number」
        ▼
 Consumer A（Lambda 異常偵測）   Consumer B（Firehose → S3）
```

① 相同的 partition key 永遠得到相同的 hash，所以**同一家旅館的事件永遠進同一個 shard**。② 紀錄在 shard 內依寫入順序取得遞增的 sequence number。③ 每個 consumer 獨立追蹤自己的讀取位置，A 讀到哪裡不影響 B。

這帶出 Kinesis 最重要的順序保證：

> **順序只在單一 shard 內保證。** 同一個 partition key 的紀錄會依序被讀到；不同 shard 之間沒有全域順序。

所以要保證「同一筆訂單的事件依序處理」，就用 `order_id` 當 partition key；要保證「同一位使用者的點擊依序處理」，就用 `user_id`。

### Hot shard：partition key 選錯的代價

Partition key 同時決定順序與負載分布。如果 Wanderly 用 `country` 當 partition key，九成流量來自台灣，那麼台灣的 hash 落在哪個 shard，那個 shard 就承擔九成流量，這稱為 **hot shard（熱分片）**。其他 shard 閒置，而熱分片超過寫入上限後開始拒絕寫入。

選 partition key 的原則：

- **高基數**：值的種類要遠多於 shard 數（user_id、session_id、order_id 都很好）。
- **符合順序需求的最小範圍**：只需要「同一訂單內」有序，就不要用「同一國家」。
- 若某個 key 天生特別熱（例如一家超大型連鎖旅館），可以在 key 後面加上隨機後綴把它打散，代價是失去該 key 的跨後綴順序。

### Shard 的容量與 capacity mode

每個 shard 的容量（provisioned mode）：

| 方向 | 每 shard 上限 |
|---|---|
| 寫入 | **1 MB／秒或 1,000 筆／秒**（先達到哪個就是哪個） |
| 讀取（shared throughput） | **2 MB／秒**，由所有共用模式的 consumer 一起分；每 shard 每秒最多 5 次 GetRecords 呼叫 |
| 讀取（enhanced fan-out） | **每個註冊的 consumer 各自 2 MB／秒** |

單筆紀錄的大小上限，考試與舊教材常用的數字是 1 MB；AWS 已把上限提高到 10 MiB，1–10 MiB 的大紀錄靠 shard 的突發容量處理，只適合偶爾出現。持續的寫入量仍以每 shard 1 MB／秒計算，設計時仍以小紀錄為佳；更大的資料（例如圖片）應放 S3，stream 裡只放物件位置。寫入超過上限時，API 回傳 `ProvisionedThroughputExceededException`，producer 必須重試。

**容量計算範例**：Wanderly 尖峰每秒 6,000 筆點擊，每筆平均 0.5 KB。

- 依筆數：6,000 ÷ 1,000 = 6 個 shard。
- 依大小：6,000 × 0.5 KB ≈ 3 MB／秒 → 3 個 shard。
- 取較大者：至少 **6 個 shard**，再為尖峰與不均勻分布預留空間，例如 8 個。

KDS 有兩種 **capacity mode（容量模式）**：

| 模式 | 怎麼運作 | 計費 | 適合 |
|---|---|---|---|
| **Provisioned** | 你決定 shard 數量；用 **resharding**（split 拆分熱 shard、merge 合併冷 shard）或 UpdateShardCount 調整 | 每 shard 小時 + PUT 單位 | 流量可預測、想精準控制成本 |
| **On-demand** | 不用管 shard 數量，AWS 依過去一段時間的流量峰值自動調整容量 | 依寫入與讀取的資料量（及 stream 小時） | 流量難以預測、新產品、不想做容量規劃 |

On-demand 會自動擴充，但它是依據「最近的流量峰值」調整，若流量在極短時間內跳到過去峰值的數倍以上，仍可能短暫被限流。兩種模式之間可以切換（每 24 小時有切換次數限制）。

> [!tip] 考試提示
> 「流量難以預測、團隊不想管理 shard」→ on-demand mode。「Producer 收到 ProvisionedThroughputExceededException，但整體流量遠低於總容量」→ hot shard，改用更分散的 partition key（或 split 熱 shard），而不是只增加 shard 數。

### Retention：資料能保留多久

Kinesis 的資料不會在被讀取後刪除，而是保留一段時間：

- **預設 24 小時**。
- 可以延長到 **最長 365 天**（超過 24 小時開始收取延長保留費用，超過 7 天另有長期保留費率）。

Retention 決定了 **replay（重播）** 的能力。如果 Wanderly 的異常偵測程式在週六凌晨部署了一個 bug、週一才發現，24 小時的 retention 意味著週六的資料已經不在 stream 裡了；若設為 7 天，修好程式後就可以讓 consumer 從週六的位置重新讀取。在資料寫入 S3 的 data lake 之後，長期歷史通常改從 S3 重新處理，不必把 stream retention 設得非常長。

## 31.4 寫入與讀取：producer、consumer 與錯誤處理

### Producer 端：PutRecords 與部分失敗

Producer 寫入的方式：

- **AWS SDK**：`PutRecord`（單筆）或 `PutRecords`（一次最多 500 筆）。
- **KPL（Kinesis Producer Library）**：高吞吐的 producer 函式庫，自動批次（batching）、聚合（aggregation，把多筆小紀錄打包成一筆）與重試。
- **Kinesis Agent**：安裝在伺服器上，監看 log 檔並傳送。
- 其他 AWS 服務：例如 CloudWatch Logs subscription filter、IoT Core rules、DynamoDB 的 Kinesis Data Streams 整合。

`PutRecords` 有一個常被忽略的行為：**整批呼叫成功不代表每一筆都成功**。回應中的 `FailedRecordCount` 與每筆的 `ErrorCode` 會指出哪些紀錄被拒絕（通常是因為限流）。Producer 必須只重試失敗的那些，並使用 exponential backoff（指數退避，第 33 章）。

重試也帶來副作用：如果網路逾時、producer 不確定上一次寫入是否成功而重試，同一事件可能被寫入兩次。所以 **Kinesis 是 at-least-once（至少一次）傳遞**，consumer 必須能處理重複紀錄。

### Consumer 端：shared throughput vs enhanced fan-out

Consumer 有兩種讀取方式：

| 比較 | Shared throughput（標準） | Enhanced fan-out（EFO） |
|---|---|---|
| 讀取方式 | Consumer 主動 `GetRecords` 輪詢（pull） | Kinesis 透過 HTTP/2 `SubscribeToShard` 主動推送（push） |
| 頻寬 | 每 shard 2 MB／秒，**所有標準 consumer 共用** | **每個 consumer** 每 shard 專屬 2 MB／秒 |
| 延遲 | 平均約 200 ms；consumer 越多越慢 | 平均約 70 ms，不受其他 consumer 影響 |
| 成本 | 不另外收費 | 依 consumer-shard 小時與讀取量另計費用 |
| 適合 | 1–2 個 consumer、延遲要求不高 | 多個 consumer、需要低延遲或互不干擾（每個 stream 預設最多註冊 20 個 EFO consumer） |

Wanderly 的 stream 一開始只有 Firehose 一個 consumer，標準模式就夠了。後來加了異常偵測 Lambda、推薦特徵 Flink、搜尋排序服務、風控服務共五個 consumer，五個程式每秒輪詢、共用 2 MB／秒，開始互相搶頻寬、延遲上升。改成讓延遲敏感的 consumer 註冊為 EFO 後，每個都有自己的 2 MB／秒管道。

### KCL：自建 consumer 的標準函式庫

**KCL（Kinesis Client Library）** 是撰寫 consumer 應用程式的函式庫，處理分散式讀取最麻煩的部分：

- **Lease（租約）**：每個 shard 由一個 worker 處理。KCL 用一張 **DynamoDB 表**（lease table）記錄「哪個 worker 擁有哪個 shard 的 lease」。Worker 增加或當機時，lease 會自動重新分配。
- **Checkpoint（檢查點）**：worker 定期把「這個 shard 已處理到哪個 sequence number」寫入 lease table。Worker 重啟後從 checkpoint 繼續，而不是從頭讀。
- **Resharding 處理**：shard 被拆分或合併時，KCL 確保先讀完 parent shard 再讀 child shard，維持順序。

兩個重要推論：(1) 一個 shard 同時只被一個 KCL worker 處理，所以 **worker 數量超過 shard 數量沒有幫助**；要提升平行度，要增加 shard。(2) Checkpoint 是「處理完一批之後」才寫的，若 worker 在處理後、checkpoint 前當機，新 worker 會重新處理那一批，這是另一個重複來源。

lease table 是 DynamoDB 表，若它的容量不足，consumer 也會變慢；KCL 的 IAM role 也需要 DynamoDB 與 CloudWatch 權限。

### Lambda 作為 consumer

不想自己管理 consumer 程式時，最常見的選擇是 **Lambda event source mapping（事件來源對應）**：Lambda 服務代你輪詢 shard、把紀錄打包成批次呼叫你的函數。重要設定：

| 設定 | 作用 |
|---|---|
| Batch size／batching window | 每次呼叫最多帶多少筆、最多等多久湊一批 |
| **Parallelization factor** | 每個 shard 同時執行的 Lambda 數量，最多 10；同一 partition key 仍維持順序 |
| Starting position | `LATEST`、`TRIM_HORIZON`（最舊）或 `AT_TIMESTAMP` |
| **Bisect batch on function error** | 批次失敗時把批次對半拆開重試，找出造成失敗的那一筆 |
| **Maximum retry attempts／maximum record age** | 限制重試次數與紀錄年齡，避免一筆壞資料無限重試 |
| **On-failure destination** | 放棄重試的批次資訊送到 SQS、SNS 或 S3，之後再處理（SQS／SNS 只收到 shard 與 sequence number 等 metadata，要在 retention 內回 stream 取資料；S3 會連同完整紀錄一起保存） |
| Tumbling window | 在 Lambda 中做簡單的時間視窗彙總 |
| Enhanced fan-out | 也可以讓 Lambda 以 EFO consumer 身份讀取 |

這裡有個與 SQS 不同的關鍵行為：**stream 是有序的，所以一個批次失敗時，Lambda 會不斷重試同一批，該 shard 後面的紀錄全部卡住**（預設會一直重試到紀錄過期）。一筆格式錯誤的紀錄就能讓整個 shard 停擺，這稱為 **poison record（毒藥紀錄）**。正確設定是：開啟 bisect batch、設定最大重試次數或最大紀錄年齡、並設定 on-failure destination。

### 監控：IteratorAge 告訴你 consumer 跟不跟得上

最重要的 consumer 指標是 **`GetRecords.IteratorAgeMilliseconds`**（Lambda 則看 `IteratorAge`）：consumer 剛讀到的紀錄距離現在多久。數值穩定接近零代表跟得上；持續上升代表 consumer 處理速度低於寫入速度，資料越積越多。如果它接近 retention 時間，資料會在被處理前過期。

IteratorAge 上升時的排查順序：

1. Consumer 本身是否變慢（下游資料庫變慢、程式錯誤一直重試）？
2. 是否有 poison record 卡住某個 shard？
3. 平行度是否不足：增加 shard 數，或提高 Lambda 的 parallelization factor。
4. 多個標準 consumer 是否在搶 2 MB／秒的共享頻寬：改用 EFO。

寫入端則看 `WriteProvisionedThroughputExceeded` 與 `PutRecords.FailedRecords`，判斷是否限流或 hot shard。

### 安全

- **加密**：KDS 支援以 KMS 做 server-side encryption（第 15 章），傳輸使用 TLS。
- **存取控制**：用 IAM policy 限制誰能 `PutRecord` 或讀取哪個 stream；KDS 也支援 resource-based policy，讓其他帳號的 producer 或 consumer 存取。
- **私有連線**：透過 interface VPC endpoint（第 6 章）讓 VPC 內的 producer 不經 Internet 寫入。

## 31.5 Amazon Data Firehose：不寫 consumer 也能把資料送到目的地

### 為什麼需要 Firehose

Wanderly 的第一個串流需求，其實只是「把點擊事件持續送進 S3 的 data lake」。用 KDS 做的話，要寫一個 consumer：讀資料、累積成檔案、轉 Parquet、按日期分區寫入 S3、處理失敗重試、管理 checkpoint。這些都是重複的苦工。

**Amazon Data Firehose**（舊名 Kinesis Data Firehose）是全受管的「串流投遞」服務：它接收串流資料，**累積（buffer）、選擇性轉換後，自動寫到目的地**。不需要管 shard、不需要寫 consumer、自動擴展，按處理的資料量計費。

### 來源與目的地

| 來源 | 目的地 |
|---|---|
| Direct PUT（應用程式直接用 API 寫入） | Amazon S3 |
| Kinesis Data Streams | Amazon Redshift（Firehose 先寫到 S3，再自動執行 COPY） |
| Amazon MSK | Amazon OpenSearch Service／OpenSearch Serverless |
| CloudWatch Logs、EventBridge、IoT Core 等 AWS 服務 | Splunk、Snowflake 等第三方服務 |
| | 自訂 HTTP endpoint（以及 Datadog、New Relic 等合作夥伴） |
| | Apache Iceberg 表（含 S3 Tables） |

### Buffer：為什麼 Firehose 是「near real-time」

Firehose 不會每收到一筆就寫一個 S3 物件，那樣會產生數十億個小檔案。它會先把資料累積起來，直到滿足以下任一條件才寫出：

- **Buffer size**：累積到指定大小（以 MB 計，例如 S3 目的地可設 1–128 MB）。
- **Buffer interval**：距離上次寫出已過指定時間（以秒計，最長 900 秒）。

這就是 Firehose 被稱為 **near real-time（近即時）** 而非 real-time 的原因：資料延遲取決於 buffer 設定，通常是數十秒到數分鐘。把 buffer interval 調小（Firehose 也支援非常小甚至零緩衝的設定）可以降低延遲，但會產生更多小檔案。若需求是「毫秒級、每筆都要立即處理」，Firehose 不是正確答案，應該用 KDS 搭配 Lambda 或 Flink。

### 轉換、格式轉換與動態分區

Firehose 在投遞前可以做三種處理：

1. **Lambda transformation**：Firehose 把一批紀錄交給你的 Lambda 函數，函數回傳轉換後的紀錄並標記每筆的結果（`Ok`、`Dropped`、`ProcessingFailed`）。可以用來解析 log、遮罩個資、補欄位。
2. **Record format conversion**：把 JSON 轉成 **Parquet 或 ORC**，schema 取自 Glue Data Catalog 的表定義。這讓寫進 S3 的資料直接就是第 30 章 Athena 喜歡的格式。
3. **Dynamic partitioning（動態分區）**：依紀錄內容（例如 `event_date`、`region` 欄位）決定寫到哪個 S3 prefix，直接產生 `event_date=2026-09-28/region=apac/` 的分區結構。

### 錯誤與備份

- 轉換失敗或格式轉換失敗的紀錄會寫到 S3 的 **error output prefix**，不會靜默消失。
- 目的地暫時無法寫入時，Firehose 會在一段時間內重試；對 OpenSearch、Splunk、HTTP endpoint、Redshift 等目的地，超過重試時間的資料會備份到 S3。
- 可以啟用 **source record backup**，把轉換前的原始資料另外存一份到 S3，方便日後重新處理。

> [!warning] 常見誤解
> 「Firehose 也能讓多個程式讀取、重播資料。」不行。Firehose 是投遞管線，**不是**可以被多個 consumer 讀取的儲存：它沒有 retention、沒有 replay、也沒有可以讓其他程式訂閱的介面。需要多個 consumer 或重播時，在 Firehose 前面放 KDS（KDS 當來源，Firehose 只是其中一個 consumer）。

## 31.6 Managed Service for Apache Flink：在串流上做運算

### 為什麼 Lambda 不夠

營運主管的需求是「每家旅館的訂房量在 5 分鐘內暴增十倍就告警」。這需要：

- 為每家旅館維護計數器（**state，狀態**），跨越許多筆事件。
- 把事件依**時間視窗**分組，例如每 1 分鐘一個視窗，並與過去一小時的平均比較。
- 處理**遲到的事件**：手機網路不穩，21:03 的點擊可能 21:05 才送到，應該算進 21:03 的視窗。
- 程式重啟時不能遺失計數器，也不能重複計算。

Lambda 每次呼叫都是無狀態的，要做這些就得自己把狀態存到 DynamoDB，處理視窗邊界與重複，很快就變得複雜且容易出錯。

### Flink 是什麼

**Apache Flink** 是開源的分散式串流處理引擎，專門處理有狀態（stateful）的串流運算。**Amazon Managed Service for Apache Flink**（舊名 Kinesis Data Analytics for Apache Flink）是它的受管版本：你提供 Flink 應用程式（Java、Scala、Python，或用 SQL），AWS 負責佈建運算資源、自動擴展、執行 **checkpoint** 與 **snapshot**。

Flink 的核心能力：

| 能力 | 說明 |
|---|---|
| **Windowing** | **Tumbling window**（固定、不重疊，例如每 1 分鐘）、**sliding window**（固定長度、會重疊，例如每 1 分鐘計算過去 5 分鐘）、**session window**（依使用者活動間隔切分） |
| **Event time 與 watermark** | 依事件「實際發生的時間」而非「到達的時間」分組，watermark 決定要等遲到事件多久 |
| **Managed state** | 計數器、彙總結果等狀態由 Flink 管理並定期 checkpoint 到耐久儲存 |
| **Exactly-once state** | 從 checkpoint 恢復時，狀態的計算結果如同每筆事件只處理一次（端到端是否 exactly-once 還取決於目的地是否支援） |
| **連接器** | 來源與目的地可以是 KDS、MSK、S3、Firehose、DynamoDB、OpenSearch 等 |

計費以 **KPU（Kinesis Processing Unit）** 計算，每個 KPU 代表一組運算與記憶體資源，應用程式依負載自動擴展。另有 **Studio notebook**，可以在 notebook 中用 SQL 或 Python 互動式探索串流資料。

> [!note] Kinesis Data Analytics for SQL 已停止
> 舊的 Kinesis Data Analytics for **SQL** applications 已終止：自 2025 年 10 月 15 日起不能新建應用程式，2026 年 1 月 27 日起 AWS 開始刪除既有應用程式並停止支援。新的串流 SQL 需求應使用 Managed Service for Apache Flink（Flink SQL 或 Studio notebook）。看到舊教材的「Kinesis Data Analytics」時，請對應到 Flink。

### Wanderly 的異常偵測

Flink 應用程式從 `wanderly-bookings` stream 讀取訂房事件，以 `hotel_id` 分組，用 1 分鐘的 tumbling window 計算每家旅館的訂房數，再與該旅館過去 60 分鐘的滑動平均比較，超過十倍就輸出一筆告警事件到另一個 KDS stream，由 Lambda 讀取後通知營運人員並自動暫停該旅館的房價。從錯誤房價上線到告警，延遲約一到兩分鐘。

## 31.7 Amazon MSK：受管的 Apache Kafka

### Kafka 的基本模型

**Apache Kafka** 是業界最普及的開源串流平台，概念與 KDS 很像，但用詞不同：

| Kafka | Kinesis Data Streams |
|---|---|
| Topic | Stream |
| Partition | Shard |
| Offset | Sequence number |
| Broker（伺服器節點） | 由 AWS 隱藏 |
| Consumer group | 各個 consumer application（KCL application name） |
| Message key | Partition key |

Kafka 的 **consumer group** 讓一組 consumer 分擔一個 topic 的 partition：每個 partition 在同一個 group 內只由一個 consumer 讀取（因此 consumer 數超過 partition 數也沒有幫助，和 KCL 相同）；不同 group 各自獨立讀取完整資料。每個 partition 在多個 broker 上有副本（**replication factor**，通常為 3，分散在 3 個 AZ）。

### MSK 的部署選項

**Amazon MSK（Managed Streaming for Apache Kafka）** 是 AWS 受管的 Kafka：

- **MSK Provisioned**：你選擇 broker 的 instance type 與數量、每個 broker 的儲存空間，AWS 負責佈建、修補、替換故障 broker、跨 AZ 部署。可以調整 Kafka 的設定（retention、訊息大小上限等），也可以啟用 **tiered storage**，把舊資料移到低成本儲存，以較低費用保留很長時間。
- **MSK Serverless**：不用管 broker 與儲存容量，自動擴展，按使用量計費；用戶端驗證使用 IAM access control。適合流量不穩定、不想做容量規劃，又需要 Kafka API 相容的情境。部分進階 Kafka 設定與某些整合在 Serverless 上有限制。
- **MSK Connect**：受管的 Kafka Connect，執行 connector 把資料在 Kafka 與資料庫、S3 等系統之間搬移（例如 Debezium CDC connector 擷取資料庫異動）。
- **MSK Replicator**：在不同 MSK cluster 之間（可跨 Region）複寫 topic，用於 DR 或跨 Region 資料共享。

存取控制可以使用 **IAM access control**、**SASL/SCRAM**（帳號密碼，存在 Secrets Manager）或 **mutual TLS**；MSK cluster 部署在你的 VPC subnet 中，broker 有 ENI，用 security group 控制連線。

### 什麼時候選 MSK 而不是 Kinesis

Kinesis 是 AWS 原生、整合度高、營運最簡單；MSK 的優勢在於 **Kafka 相容性**：

- 公司**已經在用 Kafka**，有大量 producer／consumer 程式、Kafka Streams、Kafka Connect connector，想遷移到 AWS 而**不改程式碼**。
- 需要 Kafka 生態系的特定工具或可調整的 Kafka 設定。
- 需要避免綁定特定雲端的 API，或與地端 Kafka 做雙向複寫。

Wanderly 併購的旅行社（Part 8）在資料中心有一套 Kafka cluster，數十個微服務都用 Kafka client 溝通。遷移時把 Kafka 搬到 MSK，應用程式只需要改 bootstrap broker 位址與驗證設定，是典型的 replatform（第 44 章）。

## 31.8 IoT Core 與其他串流來源

### AWS IoT Core

當資料來源是成千上萬台**裝置**（例如合作旅館房間裡的智慧門鎖、溫控器）時，裝置通常無法直接呼叫 Kinesis API：它們運算能力小、網路不穩、需要裝置級的身份驗證。**AWS IoT Core** 是讓裝置安全連上 AWS 的受管服務：

- **Device gateway**：支援 **MQTT**（一種輕量的發布／訂閱協定，專為不穩定網路設計）、MQTT over WebSocket 與 HTTPS。
- **身份驗證**：每台裝置使用 X.509 憑證，搭配 IoT policy 控制它能發布或訂閱哪些 topic。
- **Device Shadow**：在雲端保存每台裝置的「期望狀態」與「回報狀態」，裝置離線時也能讀寫。
- **Rules engine**：用類 SQL 語法篩選 MQTT 訊息，再把資料路由到 Kinesis Data Streams、Data Firehose、Lambda、S3、DynamoDB、SNS、SQS 等服務。

典型設計是：裝置 → IoT Core（MQTT）→ rule → Firehose → S3（存檔分析），或 → KDS → Flink（即時監控）。考試看到「數百萬台裝置、MQTT、裝置憑證」→ IoT Core；不要選讓裝置直接寫 Kinesis 的方案。

### 其他常見來源

- **DynamoDB**：除了 DynamoDB Streams（第 27 章，保留 24 小時），也可以把 table 的變更直接送到 Kinesis Data Streams，獲得更長的 retention 與更多 consumer。
- **資料庫 CDC**：DMS 可以把資料庫的變更持續送到 KDS 或 MSK（第 45 章）。
- **CloudWatch Logs**：subscription filter 把 log 即時送到 KDS、Firehose 或 Lambda，例如集中到資安帳號（第 36 章）。
- **Kinesis Video Streams**：串流的是影像與音訊而非資料紀錄，用於攝影機畫面的儲存、播放與分析，和 KDS 是不同的服務。

## 31.9 組起來：Wanderly 的即時 clickstream 管線

```text
 使用者瀏覽器/App
      │ ① 點擊事件（JSON）
      ▼
 [API Gateway / ALB → 事件收集服務]
      │ ② PutRecords(partitionKey = session_id)
      ▼
 [Kinesis Data Streams: wanderly-clickstream]（on-demand mode，retention 7 天）
      │
      ├─③ Data Firehose ──► Lambda 遮罩 IP ──► 轉 Parquet + 動態分區 ──► S3 data lake raw/curated（第 30 章）
      │                                                                    └─ 失敗紀錄 → S3 error prefix
      │
      ├─④ Managed Service for Apache Flink（EFO consumer）
      │       └─ 1 分鐘視窗：每家旅館點擊與訂房速率
      │            ├─► DynamoDB（熱門旅館排名，搜尋服務讀取）
      │            └─► 告警 stream ──► Lambda ──► SNS 通知營運 / 暫停房價
      │
      └─⑤ Lambda（EFO consumer，推薦特徵即時更新）
              └─ 失敗批次：bisect + 最多重試 3 次 + on-failure destination → SQS
```

① 前端把點擊事件送到後端的事件收集服務（也可以讓前端透過 Cognito 取得暫時憑證直接寫 Kinesis，第 13 章）。② 以 `session_id` 當 partition key：基數高、負載平均，又能保證同一次瀏覽的事件有序。Stream 用 on-demand mode，因為旅遊旺季與促銷活動的流量難以預測；retention 設 7 天，讓 consumer 出錯時有一週時間修正與重播。③ Firehose 負責把資料送進 data lake，不需要任何自寫 consumer；Lambda 只做個資遮罩，格式轉換與分區由 Firehose 內建功能完成。④ Flink 做需要狀態與時間視窗的運算，結果寫到 DynamoDB 供搜尋服務以毫秒讀取，異常則觸發告警。⑤ 推薦特徵更新用 Lambda，因為每筆事件的處理是無狀態的；poison record 的保護設定確保一筆壞資料不會卡住整個 shard。

Flink 與 Lambda 都註冊為 enhanced fan-out consumer，Firehose 使用標準讀取，三者互不搶頻寬。

這個設計有幾個值得注意的取捨：

- **為什麼不讓前端直接寫 Firehose？** 因為我們需要多個 consumer 與重播能力，Firehose 都不提供。
- **為什麼不用 SQS？** SQS 的訊息被處理後就刪除，無法讓三個不同的程式各自讀完整資料，也無法重播；標準 queue 也不保證順序。
- **重複怎麼辦？** Producer 重試與 consumer 重新處理都可能產生重複。每個事件帶有唯一的 `event_id`，寫入 DynamoDB 時用 conditional write（第 27 章）或在下游以 `event_id` 去重，讓處理具備 **idempotency（冪等性）**（第 33 章）。

## 31.10 比較與選型

### Kinesis vs SQS vs MSK

| 比較 | Kinesis Data Streams | SQS（第 32 章） | Amazon MSK |
|---|---|---|---|
| 模型 | 有序日誌（stream） | 佇列（queue） | 有序日誌（Kafka topic） |
| 讀取後 | 保留到 retention 到期 | 處理完刪除 | 保留到 retention 到期 |
| 多個獨立 consumer | 可以（標準或 EFO） | 不行（要搭配 SNS fan-out） | 可以（consumer groups） |
| Replay | 可以，retention 最長 365 天 | 不行 | 可以，retention 可依設定與 tiered storage 拉長 |
| 順序 | 每 shard 內有序 | Standard 無；FIFO 依 message group 有序 | 每 partition 內有序 |
| 擴展單位 | Shard（或 on-demand） | 完全自動 | Partition 與 broker（或 Serverless） |
| 營運負擔 | 低 | 最低 | 中（Provisioned）／低（Serverless） |
| 選它的理由 | AWS 原生即時串流、多 consumer、重播 | 解耦工作、每則訊息處理一次 | 既有 Kafka、需要 Kafka API 與生態系 |

### KDS vs Firehose vs Flink

| 需求 | 選擇 |
|---|---|
| 毫秒到秒級延遲、多個自訂 consumer、需要重播 | Kinesis Data Streams |
| 把串流資料以最少程式送進 S3／Redshift／OpenSearch／Splunk，可接受數十秒以上延遲 | Data Firehose |
| JSON 轉 Parquet 並分區寫入 S3 | Firehose 的 format conversion + dynamic partitioning |
| 時間視窗彙總、有狀態運算、遲到事件處理、串流 SQL | Managed Service for Apache Flink |
| 每筆事件的簡單無狀態處理 | Lambda（event source mapping） |
| 數百萬台裝置以 MQTT 連線 | IoT Core（rules 再轉送到 KDS／Firehose） |

### 選型決策流程

```text
資料需要「每則只處理一次、處理完就刪」的工作分派嗎？
├─ 是 → SQS（第 32 章）
└─ 否，這是一條事件流
     ├─ 已有 Kafka 程式與工具、要求 Kafka API 相容？ → MSK（流量不定 → MSK Serverless）
     └─ 用 AWS 原生服務
          ├─ 只需要送進 S3/Redshift/OpenSearch，近即時即可 → Data Firehose
          └─ 需要即時處理、多個 consumer 或重播 → Kinesis Data Streams
                ├─ 有狀態、視窗運算 → Flink 當 consumer
                ├─ 無狀態逐筆處理 → Lambda 當 consumer
                └─ 同時要進 data lake → 再加一個 Firehose consumer
```

## 31.11 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| 即時（real-time）、多個應用程式讀取同一份資料、可重播 | Kinesis Data Streams |
| 近即時（near real-time）把串流存進 S3／Redshift／OpenSearch，最少營運 | Data Firehose |
| 串流資料轉 Parquet 存 S3 | Firehose record format conversion（schema 來自 Glue Data Catalog） |
| 同一個使用者／訂單的事件要依序處理 | 以該 ID 當 partition key（KDS）或 message group ID（SQS FIFO） |
| 部分 shard 被限流、總流量並不高 | Hot shard，改用高基數 partition key 或 split shard |
| 流量無法預測、不想管理 shard | KDS on-demand mode |
| 多個 consumer 延遲升高、互相搶讀取頻寬 | Enhanced fan-out |
| Consumer 需要重新處理過去幾天的資料 | 延長 retention（最長 365 天） |
| IteratorAge 持續上升 | Consumer 跟不上：增加 shard、提高 Lambda parallelization factor、檢查 poison record |
| 一筆壞資料讓 Lambda 卡住整個 shard | Bisect batch、maximum retry attempts、on-failure destination |
| 滑動視窗、即時彙總、有狀態串流運算 | Managed Service for Apache Flink |
| 既有 Kafka 遷移、不改程式碼 | Amazon MSK |
| Kafka 相容但不想管 broker | MSK Serverless |
| 大量 IoT 裝置、MQTT | AWS IoT Core + rules engine |

**常見陷阱**：

1. 把 Firehose 當作可以多方讀取或重播的 stream：它只負責投遞，沒有 retention。
2. 把需要毫秒級回應的需求交給 Firehose：buffer 讓它是 near real-time。
3. 增加 KCL worker 或 Kafka consumer 數量來提高平行度：超過 shard／partition 數的 consumer 會閒置，要增加 shard 或 partition。
4. 以為 Kinesis 保證全域順序：順序只在單一 shard 內。
5. 以為 Kinesis 是 exactly-once：producer 重試與 consumer 重新處理都會造成重複，下游要 idempotent。
6. 以為 `PutRecords` 呼叫成功代表所有紀錄都寫入了：要檢查 `FailedRecordCount` 並重試失敗的紀錄。
7. 把 SQS 當作多 consumer 的事件流：SQS 的訊息被一個 consumer 處理後就刪除，需要多個獨立 consumer 時要用 SNS fan-out 或改用 stream。

## 31.12 SAP 加深：大規模串流平台的可靠性與遷移

### 多帳號的串流平台

企業常見的設計是由資料平台帳號擁有 stream，其他帳號的服務寫入或讀取：

- **跨帳號寫入／讀取**：KDS 的 resource-based policy 可以直接允許其他帳號的 role 存取，或讓對方 assume 平台帳號中的 role（第 13 章）。若 stream 使用 customer managed KMS key 加密，key policy 也要允許對方。
- **集中 log 管線**：各帳號的 CloudWatch Logs 透過 subscription filter 送到集中帳號的 Firehose 或 KDS（經由 CloudWatch Logs destination），再進入資安帳號的 S3 與 OpenSearch（第 40、43 章）。
- **MSK 跨 VPC 存取**：MSK 支援 multi-VPC private connectivity（以 PrivateLink 為基礎），讓其他帳號的 VPC 不必和 MSK 所在 VPC 互連路由。

### 可靠性設計

- **Producer 端緩衝**：當 stream 被限流或短暫不可用時，producer 需要本地緩衝與退避重試，不要無限重試把自己拖垮（第 35 章的 backpressure）。
- **Consumer 重播策略**：retention 要大於「發現錯誤＋修正＋重播」的最長時間。長期歷史則從 S3 data lake 重新處理，形成「stream 管短期重播、S3 管長期重建」的分工。
- **Exactly-once 的現實**：串流系統通常只能保證 at-least-once 傳遞；「效果上只處理一次」要靠下游的 idempotent 寫入（唯一鍵、conditional write、upsert）。Flink 的 exactly-once 只涵蓋它自己的狀態，寫到外部系統時仍需目的地配合。
- **跨 Region**：KDS 本身不提供跨 Region 複寫，需要自己用 consumer（例如 Lambda 或 Flink）把資料寫到另一個 Region 的 stream，或在 producer 端雙寫；MSK 則可以用 MSK Replicator 在 Region 之間複寫 topic（第 42 章）。

### 從自建平台遷移

| 現況 | 建議方向 |
|---|---|
| 地端 Kafka，大量 Kafka client 程式 | MSK（Provisioned 或 Serverless），用 MSK Replicator 或 MirrorMaker 2 在切換期間同步資料 |
| EC2 上自管的 Kafka，團隊不想再管 broker | MSK Serverless 或 MSK Provisioned |
| 自寫 consumer 只為了把資料寫進 S3 | 用 Firehose 取代，降低程式維護 |
| 舊的 Kinesis Data Analytics for SQL 應用程式 | 改寫為 Managed Service for Apache Flink（Flink SQL） |
| Cron 每小時批次處理，業務要求分鐘級延遲 | 在既有資料來源前加 KDS，批次與串流並存，逐步把需要低延遲的邏輯搬到 Flink |

## 本章重點整理

- Batch 處理累積後定時執行，延遲等於批次間隔；stream 處理在資料產生後秒級處理，用時間視窗切出範圍，兩者常並存。
- Stream 是保留一段時間的有序日誌，多個 consumer 各自追蹤讀取位置並可重播；queue 的訊息處理後刪除，consumer 之間是分工。
- Kinesis Data Streams 用 partition key 的 hash 決定 shard；順序只在單一 shard 內保證；partition key 要高基數以避免 hot shard。
- 每個 shard 寫入上限 1 MB／秒或 1,000 筆／秒，標準讀取每 shard 2 MB／秒由所有 consumer 共用；shard 數取筆數與大小兩種算法的較大值。
- Provisioned mode 自己管 shard 數並用 resharding 調整；on-demand mode 自動擴展，適合流量難以預測的情境。
- KDS retention 預設 24 小時，最長 365 天；retention 決定 consumer 出錯後能重播多久。
- Enhanced fan-out 讓每個 consumer 每 shard 獨享 2 MB／秒並以推送方式降低延遲，適合多個低延遲 consumer。
- KCL 用 DynamoDB lease table 分配 shard 並記錄 checkpoint；consumer 數超過 shard 數沒有幫助。
- Kinesis 是 at-least-once；`PutRecords` 可能部分失敗，producer 要只重試失敗紀錄，下游處理要 idempotent。
- Lambda 讀 stream 時一個失敗批次會卡住該 shard；要設定 bisect batch、最大重試次數或紀錄年齡、on-failure destination，並用 parallelization factor 提高每 shard 平行度。
- IteratorAge 持續上升表示 consumer 跟不上寫入速度，接近 retention 時資料會在處理前過期。
- Data Firehose 以 buffer size 與 interval 批次投遞，是 near real-time；可用 Lambda 轉換、轉成 Parquet、動態分區，但沒有 retention 與 replay。
- Managed Service for Apache Flink 處理有狀態的視窗運算、event time 與遲到事件；舊的 Kinesis Data Analytics for SQL 已停止，新需求改用 Flink。
- MSK 提供受管 Kafka，適合既有 Kafka 生態系遷移；MSK Serverless 免管 broker；MSK Connect 與 MSK Replicator 分別處理資料整合與跨 cluster 複寫。
- 大量 IoT 裝置以 MQTT 透過 IoT Core 連線，再用 rules engine 轉送到 Kinesis、Firehose、Lambda 等服務。

## 本章練習題

### 練習 31-1｜SAA｜單選｜Stream 與 queue 的選擇

Wanderly 的網站每秒產生約 3,000 筆點擊事件。同一份事件要同時提供給三個團隊：資料平台團隊要存進 S3、搜尋團隊要即時更新熱門排名、風控團隊要偵測異常。三個團隊的程式各自部署、處理速度不同，而且任何團隊的程式出錯時，都需要能重新處理過去 3 天的事件。

哪個設計最合適？

- A. 把事件寫入 Kinesis Data Streams 並把 retention 設為 3 天以上，三個團隊各自作為獨立 consumer 讀取
- B. 把事件寫入一個 SQS standard queue，三個團隊的程式都從這個 queue 讀取
- C. 把事件寫入 Data Firehose，三個團隊的程式都向 Firehose 訂閱資料
- D. 把事件寫入一個 SQS FIFO queue，並把訊息保留期間設為 3 天

> [!answer]- 答案：A
> **A ✓** Kinesis Data Streams 是保留一段時間的日誌，每個 consumer 獨立追蹤讀取位置，三個團隊都能讀到完整資料、互不影響；retention 延長到 3 天以上，任何 consumer 出錯時都能從過去的位置重播。
>
> **B ✗** SQS 的訊息被某個 consumer 處理並刪除後就消失，三個程式會互相搶訊息，每個團隊只拿到部分事件；也無法重播已處理的訊息。若改用 SNS 對三個 queue fan-out 能解決多 consumer，但仍無法重播。
>
> **C ✗** Firehose 是投遞服務，只能把資料送到設定好的目的地，沒有讓其他程式訂閱的介面，也沒有 retention 與 replay。
>
> **D ✗** FIFO queue 同樣是處理後刪除的模型，保留期間只影響「尚未被處理」的訊息能留多久，無法讓多個 consumer 各自讀完整資料。
>
> **考點**：SAA-2.1、SAA-3.5｜stream 與 queue 的差異、多 consumer 與 replay

### 練習 31-2｜SAA｜單選｜Hot shard

Wanderly 的訂房事件寫入一個有 10 個 shard 的 Kinesis Data Streams，partition key 是 `country_code`。約 85% 的訂房來自台灣。監控顯示整體寫入量只有 stream 總容量的 30%，但 producer 經常收到 `ProvisionedThroughputExceededException`。業務只要求同一筆訂單的事件依序處理。

哪個做法最能解決問題？

- A. 把 shard 數量增加到 40 個
- B. 改用 enhanced fan-out，提高每個 shard 的寫入上限
- C. 改用 `order_id` 作為 partition key
- D. 把 retention 從 24 小時延長到 7 天

> [!answer]- 答案：C
> **A ✗** 相同的 partition key 永遠落到同一個 shard。即使有 40 個 shard，所有台灣的事件仍集中在其中一個，熱點依舊存在，只是多付了 shard 費用。
>
> **B ✗** Enhanced fan-out 提升的是 consumer 的讀取頻寬，與寫入上限無關。
>
> **C ✓** 整體容量足夠但仍被限流，代表是 hot shard。`order_id` 基數高，能把寫入平均分散到所有 shard；需求只要求同一筆訂單有序，以 `order_id` 為 key 正好滿足這個順序範圍。
>
> **D ✗** Retention 決定資料保留多久，與寫入吞吐無關。
>
> **考點**：SAA-3.5｜partition key 選擇與 hot shard

### 練習 31-3｜SAA｜選兩項｜Shard 容量規劃

Wanderly 預估點擊 stream 尖峰時每秒寫入 4,500 筆紀錄，每筆平均 2 KB。Stream 使用 provisioned mode 與標準（shared throughput）讀取，有兩個 consumer 各自需要讀取全部資料。團隊要決定最少需要幾個 shard 才不會被限流。

關於這個計算，哪兩個敘述正確？（選兩項）

- A. 只需要看寫入的筆數：4,500 ÷ 1,000，所以 5 個 shard 一定足夠
- B. 依寫入大小計算，4,500 × 2 KB ≈ 9 MB／秒，至少需要 9 個 shard
- C. 增加 consumer 數量不會影響讀取容量，因為每個 consumer 都有自己的 2 MB／秒
- D. 兩個標準 consumer 每秒共讀取約 18 MB，而每個 shard 的共享讀取上限是 2 MB／秒，因此 9 個 shard 剛好能滿足讀取，沒有餘裕；若再增加 consumer 應考慮 enhanced fan-out
- E. 讀取容量是每 shard 1 MB／秒，因此讀取端至少需要 18 個 shard

> [!answer]- 答案：B、D
> **A ✗** 每個 shard 的寫入上限是「1 MB／秒或 1,000 筆／秒」先達到者。以筆數算只需 5 個，但以大小算需要 9 個，必須取較大值。
>
> **B ✓** 4,500 × 2 KB 約 9 MB／秒，每個 shard 寫入上限 1 MB／秒，因此至少 9 個 shard；實務上還要為尖峰與分布不均預留空間。
>
> **C ✗** 這是 enhanced fan-out 的行為。標準讀取模式下，每 shard 2 MB／秒由所有 consumer 共用。
>
> **D ✓** 9 個 shard 的共享讀取容量是 18 MB／秒，兩個 consumer 各讀 9 MB／秒剛好用滿。再多一個標準 consumer 就會超過，這時應讓 consumer 改用 enhanced fan-out，或增加 shard。
>
> **E ✗** 標準讀取上限是每 shard 2 MB／秒，不是 1 MB／秒；1 MB／秒是寫入上限。
>
> **考點**：SAA-3.5｜shard 寫入與讀取上限計算

### 練習 31-4｜SAA｜單選｜流量難以預測的 stream

Wanderly 即將推出一個與網紅合作的限時促銷活動，事件流量可能從平時每秒數百筆跳到數萬筆，也可能毫無起色，團隊無法事先預估。新的 Kinesis Data Streams 要能承接流量變化，團隊沒有人力監控並手動調整 shard 數量。

最合適的設定是什麼？

- A. 以 provisioned mode 建立 200 個 shard，確保尖峰時容量足夠
- B. 以 provisioned mode 建立少量 shard，並寫一個 Lambda 每分鐘依 CloudWatch 指標執行 split 與 merge
- C. 改用 SQS standard queue，因為它可以自動擴展
- D. 以 on-demand capacity mode 建立 stream

> [!answer]- 答案：D
> **A ✗** 200 個 shard 在流量低時大部分閒置，每個 shard 都按小時計費，成本很高；若流量真的超過預估，仍需手動調整。
>
> **B ✗** 自建自動擴縮可以運作，但需要開發、測試與維護，違反「沒有人力管理 shard」；resharding 也有速率限制，自寫邏輯容易出錯。
>
> **C ✗** SQS 確實會自動擴展，但它是處理後刪除的 queue，若應用程式依賴 stream 的多 consumer 或重播特性，就不能直接替代。
>
> **D ✓** On-demand mode 不需要規劃 shard 數，AWS 依流量自動調整容量，按實際寫入與讀取量計費，適合流量無法預測、不想做容量管理的情境。
>
> **考點**：SAA-3.5、SAA-2.1｜KDS on-demand 與 provisioned capacity mode

### 練習 31-5｜SAA｜單選｜多個 consumer 的延遲

Wanderly 的點擊 stream 有 6 個 shard，原本只有 Firehose 一個 consumer。最近又加入了四個以 KCL 撰寫的 consumer，包括需要在 200 毫秒內反應的即時推薦服務。之後所有 consumer 的延遲都明顯上升，並出現讀取被限流的錯誤。寫入量沒有變化。

最合適的改善方式是什麼？

- A. 把 retention 延長到 7 天，讓 consumer 有更多時間讀取
- B. 把延遲敏感的 consumer 註冊為 enhanced fan-out consumer
- C. 為每個 KCL consumer 增加更多 worker instance
- D. 把 stream 拆成五個獨立 stream，讓 producer 同時寫入五份

> [!answer]- 答案：B
> **A ✗** Retention 只影響資料保留時間，不會提升讀取頻寬或降低延遲。
>
> **B ✓** 標準模式下每個 shard 的 2 MB／秒讀取頻寬與每秒 5 次 GetRecords 由所有 consumer 共用，consumer 越多越互相干擾。Enhanced fan-out 讓每個註冊的 consumer 每 shard 獨享 2 MB／秒，並以 HTTP/2 推送降低延遲。
>
> **C ✗** 每個 shard 同時只會被一個 KCL worker 處理，增加 worker 不會增加讀取頻寬，反而讓多出的 worker 閒置。
>
> **D ✗** 拆成五個 stream 並讓 producer 寫五份，會增加 producer 複雜度、成本與資料不一致風險，是 EFO 出現前的變通做法。
>
> **考點**：SAA-3.5｜enhanced fan-out 與 shared throughput

### 練習 31-6｜SAA｜單選｜串流資料進 data lake

Wanderly 想把行動 App 的事件持續寫入 S3 data lake，供 Athena 查詢。需求是：以 Parquet 格式存放、依事件日期分區、在寫入前遮罩使用者 IP 位址，資料延遲在 5 分鐘內即可。團隊希望撰寫與維護的程式碼越少越好，也不需要其他程式讀取這份事件流。

最合適的做法是什麼？

- A. 使用 Data Firehose，以 Lambda transformation 遮罩 IP，啟用 record format conversion 轉成 Parquet（schema 取自 Glue Data Catalog），並以 dynamic partitioning 依日期寫入 S3
- B. 使用 Kinesis Data Streams，撰寫 KCL consumer 累積資料、轉換格式並寫入 S3
- C. 讓 App 直接把每個事件以獨立物件 PutObject 到 S3，再每小時執行 Glue job 轉換為 Parquet
- D. 使用 Managed Service for Apache Flink，撰寫應用程式把事件轉成 Parquet 寫入 S3

> [!answer]- 答案：A
> **A ✓** Firehose 是受管的投遞服務，內建 buffer、Lambda 轉換、轉 Parquet 與動態分區，只需撰寫一個簡單的遮罩函數。5 分鐘延遲在 buffer 設定可達成的範圍內，也不需要多 consumer 或重播。
>
> **B ✗** KDS 加上自寫 consumer 可以做到，若同時需要多個 consumer 或重播時會是合適的設計；但這裡要自行處理 buffer、格式轉換、分區、重試與 checkpoint，程式碼最多。
>
> **C ✗** 每個事件一個物件會產生大量小檔案並增加 PUT 請求費用，也讓 App 必須持有 S3 寫入權限；每小時的 Glue job 也無法保證 5 分鐘內可查詢。
>
> **D ✗** Flink 適合有狀態的串流運算。單純的轉換與投遞用 Flink 需要撰寫並維護應用程式，營運負擔比 Firehose 高。
>
> **考點**：SAA-3.5｜Data Firehose 轉換、格式轉換與動態分區

### 練習 31-7｜SAA｜單選｜Near real-time 與 real-time

Wanderly 的支付團隊要即時偵測盜刷：每筆刷卡事件必須在 1 秒內完成規則檢查，命中規則時立刻凍結交易。目前的設計是 App 把事件寫入 Data Firehose，Firehose 把資料投遞到 S3，再由 S3 事件通知觸發 Lambda 檢查。測試發現事件到檢查完成常常需要一分鐘以上。

最合適的改善方式是什麼？

- A. 把 Firehose 的 buffer size 調到最大，讓每次投遞包含更多事件
- B. 把 Firehose 的目的地改成 Amazon Redshift，並在 Redshift 中以排程查詢執行規則檢查
- C. 改把事件寫入 Kinesis Data Streams，由 Lambda event source mapping 直接讀取並檢查
- D. 在 S3 bucket 啟用 Transfer Acceleration，加快 Firehose 寫入 S3 的速度

> [!answer]- 答案：C
> **A ✗** 加大 buffer 會讓 Firehose 等待更久才投遞，延遲只會增加。
>
> **B ✗** Firehose 寫入 Redshift 是先寫 S3 再執行 COPY，排程查詢又多一層延遲，離 1 秒的要求更遠。
>
> **C ✓** Firehose 的 buffer 讓它是 near real-time，加上 S3 寫入與事件通知，延遲通常是數十秒到數分鐘。KDS 搭配 Lambda event source mapping 時，紀錄寫入後可在約一秒內被讀取處理，符合即時檢查的需求。
>
> **D ✗** Transfer Acceleration 是透過 edge location 加速遠距離上傳到 S3，與 Firehose 的 buffer 延遲無關。
>
> **考點**：SAA-3.5、SAA-2.1｜Firehose 是 near real-time，即時處理用 KDS

### 練習 31-8｜SAA｜選兩項｜Poison record 卡住 shard

Wanderly 的推薦服務以 Lambda event source mapping 讀取 Kinesis Data Streams。某天一筆格式錯誤的事件讓函數持續拋出例外，監控顯示其中一個 shard 的 IteratorAge 不斷上升、該 shard 後續的紀錄完全沒有被處理，其他 shard 正常。團隊希望未來單一壞資料不會阻塞整個 shard，且被放棄的紀錄要能事後調查。

哪兩個設定最合適？（選兩項）

- A. 把 Lambda 的 reserved concurrency 設為 0，暫停處理直到人工介入
- B. 啟用 bisect batch on function error，並設定 maximum retry attempts（或 maximum record age）
- C. 把 stream 的 retention 延長到 365 天，讓壞紀錄自然過期
- D. 把 batch size 調大，讓壞紀錄混在更多正常紀錄中一起處理
- E. 設定 on-failure destination，把放棄重試的紀錄資訊送到 SQS queue 或 SNS topic

> [!answer]- 答案：B、E
> **A ✗** 把 concurrency 設為 0 會停止所有 shard 的處理，讓問題擴大，也沒有讓壞紀錄被跳過。
>
> **B ✓** Stream 是有序的，失敗批次預設會一直重試，阻塞該 shard。Bisect 把失敗的批次對半拆開重試，找出真正的壞紀錄；限制重試次數或紀錄年齡後，Lambda 會放棄這筆並繼續處理後面的紀錄。
>
> **C ✗** 延長 retention 只會讓壞紀錄存在更久、shard 被阻塞更久。
>
> **D ✗** 批次越大，一筆壞紀錄造成整批失敗時牽連的正常紀錄越多，問題更嚴重。
>
> **E ✓** On-failure destination 會收到被放棄批次的 metadata（shard、sequence number 範圍等），團隊可以據此回頭從 stream 取出並調查那些紀錄，滿足「事後調查」。
>
> **考點**：SAA-2.1、SAA-3.5｜Lambda 讀 stream 的錯誤處理

### 練習 31-9｜SAA｜單選｜Consumer 錯誤後重播

Wanderly 的會員積點服務以 KCL 讀取訂房 stream。上週五晚上部署的新版本有計算錯誤，直到週一早上才被發現，期間計算的積點都不正確。Stream 目前使用預設的 retention 設定。團隊希望未來類似的錯誤能在修正程式後，直接從 stream 重新處理最多一週內的事件。

最合適的做法是什麼？

- A. 把 consumer 的 checkpoint 頻率提高為每筆紀錄一次
- B. 為 stream 啟用 enhanced fan-out，讓 consumer 可以讀取歷史資料
- C. 在 producer 端把所有事件同時寫入第二個 stream 作為備份
- D. 把 stream 的 retention 延長到 7 天以上，修正後讓 consumer 從錯誤發生時間點（AT_TIMESTAMP）重新讀取

> [!answer]- 答案：D
> **A ✗** Checkpoint 頻率影響當機重啟時需要重新處理的範圍，與能回頭多久無關；資料過了 retention 就已不存在。
>
> **B ✗** Enhanced fan-out 提升讀取頻寬與延遲，不會延長資料保留時間。
>
> **C ✗** 第二個 stream 若也是預設 retention，同樣只保留 24 小時；雙寫還增加成本與一致性問題。
>
> **D ✓** 預設 retention 只有 24 小時，週五的資料在週一已經過期。延長到 7 天以上後，修正程式可以讓 consumer 從指定時間點重新讀取並重新計算。下游寫入要設計成 idempotent，重播才不會重複累加積點。
>
> **考點**：SAA-2.2、SAA-3.5｜KDS retention 與 replay

### 練習 31-10｜SAA｜單選｜大量裝置的資料擷取

Wanderly 與連鎖旅館合作，在 5 萬間客房安裝智慧溫控器，每台裝置每 30 秒回報一次溫度與用電量。裝置使用低功耗晶片與不穩定的 Wi-Fi，原生支援 MQTT。每台裝置必須有獨立的身份驗證，並只能發布到自己的 topic。資料要存進 S3 供分析。

最合適的設計是什麼？

- A. 讓裝置透過 MQTT 連線到 AWS IoT Core，每台裝置使用 X.509 憑證與 IoT policy，再以 IoT rule 把訊息送到 Data Firehose 寫入 S3
- B. 在每台裝置嵌入同一組 IAM access key，直接呼叫 Kinesis Data Streams 的 PutRecord API
- C. 讓裝置透過 HTTPS 呼叫 API Gateway，再由 Lambda 逐筆寫入 S3
- D. 在 EC2 上自建 MQTT broker，並撰寫程式把訊息轉寫到 S3

> [!answer]- 答案：A
> **A ✓** IoT Core 是為大量裝置設計的受管服務：支援 MQTT、每台裝置用 X.509 憑證驗證，IoT policy 可限制每台裝置只能發布到自己的 topic；rules engine 再把資料路由到 Firehose，由 Firehose 批次寫入 S3。
>
> **B ✗** 所有裝置共用一組長期 IAM key，任何一台被破解就會外洩整組憑證，也無法做到裝置級權限；裝置也未必能有效呼叫 Kinesis API。
>
> **C ✗** API Gateway 與 Lambda 能接收 HTTPS，但不支援 MQTT，裝置級憑證驗證與 topic 權限要自己實作；逐筆寫 S3 也會產生大量小檔案。
>
> **D ✗** 自建 MQTT broker 需要自行處理高可用、擴展、憑證管理與修補，營運負擔最高。
>
> **考點**：SAA-3.5、SAA-1.2｜AWS IoT Core 與 rules engine

### 練習 31-11｜SAP｜單選｜既有 Kafka 平台遷移

Wanderly 併購的旅行社在資料中心運行一套 Kafka cluster，有 40 個微服務使用 Kafka client 程式庫、Kafka Streams 應用程式，以及數個 Kafka Connect connector。公司計畫在 6 個月內把這些系統遷移到 AWS，要求應用程式改動最少、不再自行管理 Kafka 伺服器的修補與故障替換，並在切換期間讓地端與雲端的 topic 資料保持同步。

最合適的做法是什麼？

- A. 把所有微服務改寫為使用 Kinesis Data Streams API，並以 KCL 取代 Kafka Streams
- B. 在 EC2 上自建 Kafka cluster，用 Auto Scaling group 管理 broker
- C. 建立 Amazon MSK cluster，以 MirrorMaker 2 在切換期間把地端 topic 複寫到 MSK，再逐步把應用程式改連 MSK，connector 改用 MSK Connect
- D. 改用 SQS FIFO queue 取代 Kafka topic，並用 message group ID 維持順序

> [!answer]- 答案：C
> **A ✗** 改寫 40 個微服務與 Kafka Streams 應用程式，工作量與風險都很高，違反「改動最少」。若是新系統、沒有 Kafka 包袱，KDS 才是營運最簡單的選擇。
>
> **B ✗** 自建 Kafka 仍要自己處理 broker 的修補、故障替換與儲存擴充，違反「不自行管理 Kafka 伺服器」。
>
> **C ✓** MSK 與開源 Kafka API 相容，應用程式主要只需更新 broker 位址與驗證設定；AWS 負責 broker 的佈建、修補與故障替換。MirrorMaker 2 在切換期間同步 topic，讓服務可以分批切換；Kafka Connect connector 可以移到 MSK Connect 執行。
>
> **D ✗** SQS 不是 Kafka 相容的服務，也不支援多個 consumer group 各自重播；所有程式都要改寫。
>
> **考點**：SAP-4.2、SAP-4.3｜既有 Kafka 遷移到 Amazon MSK

### 練習 31-12｜SAP｜單選｜MSK Serverless 選型

Wanderly 的資料平台團隊要為十多個新的內部專案提供 Kafka 相容的串流服務。每個專案的流量從每天幾 MB 到偶爾每秒數十 MB 不等，難以預測；團隊只有兩位工程師，不想規劃 broker 數量、instance type 與儲存容量。所有用戶端都能使用 IAM 驗證。

最合適的做法是什麼？

- A. 為每個專案建立一個 MSK Provisioned cluster，選擇最大的 broker instance type 預留尖峰容量
- B. 建立 MSK Serverless cluster，為各專案建立 topic，用 IAM access control 管理各專案的存取權限
- C. 建立一個大型 MSK Provisioned cluster 並啟用 tiered storage，由兩位工程師定期依監控結果調整 broker 數量
- D. 改用 Kinesis Data Streams on-demand，並要求各專案改用 Kinesis API

> [!answer]- 答案：B
> **A ✗** 每個專案一個大型 cluster，在流量低時大量閒置，成本很高，也增加十多套 cluster 的管理工作。
>
> **B ✓** MSK Serverless 提供 Kafka API 相容的服務，自動擴展容量，按使用量計費，不需要規劃 broker 與儲存。用戶端使用 IAM access control，可以用 IAM policy 依 topic 控制各專案的權限。
>
> **C ✗** Tiered storage 降低長期保留的儲存成本，但 broker 數量仍需人工規劃與調整，不符合兩人團隊不想做容量規劃的需求。若需要調整 Kafka 進階設定或有穩定的大流量，Provisioned 會是較好的選擇。
>
> **D ✗** KDS on-demand 同樣免容量規劃，但需求是 Kafka 相容；要求各專案改用 Kinesis API 違反這個條件。
>
> **考點**：SAP-2.5、SAP-2.6｜MSK Serverless 與 Provisioned 的選擇

### 練習 31-13｜SAP｜單選｜有狀態的即時異常偵測

Wanderly 要偵測房價設定錯誤：當某家旅館過去 5 分鐘的訂房數超過其過去 1 小時平均值的 10 倍時，在 2 分鐘內發出告警。行動網路造成部分事件會延遲最多 3 分鐘才到達，這些事件必須依實際發生時間計入正確的時間區間。應用程式重啟時不能遺失計數也不能重複計數。團隊希望使用受管服務，不想自建 cluster。

最合適的做法是什麼？

- A. 由 Lambda event source mapping 讀取 stream，在每次呼叫中把計數累加到 DynamoDB，以到達時間判斷屬於哪個區間
- B. 由 Data Firehose 每 5 分鐘把事件寫入 S3，再以 Athena 排程查詢計算比率
- C. 在 EMR cluster 上以 Spark Structured Streaming 執行，並自行管理 checkpoint 與 cluster 容量
- D. 使用 Managed Service for Apache Flink 讀取訂房 stream，以 event time 與 watermark 處理遲到事件，用 sliding window 計算各旅館的訂房數並與歷史平均比較，依賴 Flink 的 checkpoint 保存狀態

> [!answer]- 答案：D
> **A ✗** Lambda 是無狀態的，以到達時間分組會把遲到事件算錯區間；重試時累加 DynamoDB 也可能重複計數，要自己實作視窗與去重邏輯。
>
> **B ✗** Firehose 的 buffer 加上排程查詢，延遲與粒度都難以保證 2 分鐘內告警，也沒有處理遲到事件的機制。
>
> **C ✗** Spark Structured Streaming 在功能上可行，但需要自建並管理 EMR cluster 與容量，違反「使用受管服務、不想自建 cluster」。
>
> **D ✓** Flink 原生支援 event time、watermark（決定要等待遲到事件多久）、sliding window 與由 checkpoint 保護的 managed state；重啟時從 checkpoint 恢復，狀態不遺失也不重複計算。Managed Service for Apache Flink 負責佈建與擴展。
>
> **考點**：SAP-2.5、SAP-2.4｜Managed Service for Apache Flink 的視窗與狀態

### 練習 31-14｜SAP｜選兩項｜Consumer 跟不上寫入

Wanderly 的搜尋排名服務以 Lambda event source mapping 讀取一個 8 shard 的 provisioned Kinesis stream。促銷活動期間寫入量成長三倍，但仍低於 stream 的寫入容量。監控顯示 Lambda 沒有錯誤，每次呼叫的執行時間穩定，但 IteratorAge 持續上升，已接近 retention 時間。同一個 partition key 的事件必須依序處理。

哪兩個做法能最直接地解決問題？（選兩項）

- A. 提高 event source mapping 的 parallelization factor，讓每個 shard 同時有多個 Lambda 執行，並仍依 partition key 維持順序
- B. 把 stream 改為 on-demand mode，自動提升 Lambda 的處理速度
- C. 增加 stream 的 shard 數量，提高整體平行處理的單位數
- D. 把 retention 延長，讓 IteratorAge 不再上升
- E. 把 Lambda 的 reserved concurrency 設為 8，確保每個 shard 有一個執行環境

> [!answer]- 答案：A、C
> **A ✓** Lambda 沒有錯誤、執行時間穩定，但處理速度跟不上寫入，代表平行度不足。Parallelization factor 最多可讓每個 shard 同時有 10 個批次在處理，Lambda 會確保相同 partition key 的紀錄仍依序處理。
>
> **B ✗** 寫入量仍低於容量，問題不在 stream 寫入端。On-demand 依寫入流量決定容量，不會因為 consumer 跟不上而增加 shard，也不會讓 Lambda 處理得更快。
>
> **C ✓** 預設每個 shard 同時只有一個 Lambda 批次在處理，增加 shard 就增加平行處理的單位，也提高讀取容量。
>
> **D ✗** 延長 retention 只能讓資料晚一點過期，consumer 仍跟不上，IteratorAge 會繼續上升。
>
> **E ✗** 把並行數限制在 8，等於維持目前每 shard 一個執行環境的狀態，甚至可能在提高 parallelization factor 後變成瓶頸。
>
> **考點**：SAP-3.3、SAP-3.4｜IteratorAge 與 consumer 平行度

### 練習 31-15｜SAP｜單選｜重複事件與 idempotency

Wanderly 的積點服務從 Kinesis Data Streams 讀取「訂房完成」事件，每個事件為會員加上積點並寫入 DynamoDB。稽核發現少數會員收到兩倍積點。調查顯示：producer 在網路逾時時會重試 PutRecords，consumer 偶爾在處理後、checkpoint 前被替換。財務要求同一筆訂房絕不能重複發放積點，並以最少的架構改動達成。

最合適的做法是什麼？

- A. 把 stream 改成 SQS FIFO queue，以內容去重保證每則訊息只傳遞一次
- B. 讓 producer 為每個事件產生唯一的 `event_id`，consumer 以 DynamoDB conditional write 記錄已處理的 `event_id`，只有第一次寫入成功時才發放積點
- C. 提高 KCL 的 checkpoint 頻率為每筆紀錄一次，並關閉 producer 的重試
- D. 改用 enhanced fan-out，讓每筆紀錄只被推送一次

> [!answer]- 答案：B
> **A ✗** FIFO queue 的去重只在 5 分鐘的去重視窗內有效，consumer 端處理後失敗重試仍可能重複處理；而且這是替換整個傳輸元件，改動大，也失去 stream 的多 consumer 與重播能力。
>
> **B ✓** Kinesis 是 at-least-once 傳遞，重複無法在傳輸層完全消除，正確做法是讓處理具有 idempotency。以唯一的 `event_id` 搭配 conditional write（例如 `attribute_not_exists`），同一事件第二次到達時寫入失敗，就不會再發放積點。
>
> **C ✗** 每筆 checkpoint 縮小了重複範圍，但處理與 checkpoint 之間仍有空窗；關閉 producer 重試則會在限流或逾時時遺失事件。
>
> **D ✗** Enhanced fan-out 改變的是讀取頻寬與推送方式，不改變 at-least-once 的語意，重試與重新處理仍會造成重複。
>
> **考點**：SAP-2.4、SAP-3.4｜at-least-once 與 idempotent consumer

### 練習 31-16｜SAP｜單選｜全域 clickstream 平台設計

Wanderly 要重新設計 clickstream 平台：尖峰每秒 5 萬筆事件、流量隨行銷活動劇烈變化；事件要在 10 分鐘內以 Parquet 進入 S3 data lake；一個即時排名服務需要 1 秒內的延遲；風控團隊每次部署新規則時，需要用過去 3 天的資料重新驗證。平台團隊希望盡量使用受管服務，並讓各 consumer 互不影響。

哪個設計最合適？

- A. 前端直接寫入 Data Firehose，Firehose 轉 Parquet 寫入 S3；即時排名服務與風控團隊都從 S3 讀取最新檔案
- B. 寫入 SQS standard queue，由 Lambda 讀取後同時寫 S3、更新排名並交給風控；風控從 S3 重新驗證
- C. 在 EC2 上自建 Kafka cluster，讓所有團隊各自撰寫 consumer，並自行開發寫入 S3 的程式
- D. 寫入 on-demand 模式的 Kinesis Data Streams 並把 retention 設為 3 天以上；Data Firehose 作為一個 consumer 轉 Parquet 寫入 S3；即時排名服務與風控以 enhanced fan-out consumer 讀取，風控需要時從指定時間點重播

> [!answer]- 答案：D
> **A ✗** Firehose 符合「10 分鐘內進 S3」，但它的 buffer 讓從 S3 讀最新檔案的延遲遠超過 1 秒，也沒有 stream 層級的重播能力。
>
> **B ✗** SQS 訊息處理後即刪除，單一 Lambda 承擔三種工作讓 consumer 互相影響，任何一個下游失敗都會影響其他兩者；也無法從 queue 重播。
>
> **C ✗** 自建 Kafka 技術上可行，但需要管理 broker、容量與修補，還要自寫 S3 投遞程式，違反「盡量使用受管服務」。
>
> **D ✓** On-demand KDS 承接劇烈變化的流量；3 天以上的 retention 讓風控可以重播；Firehose 作為 consumer 以最少程式完成 Parquet 投遞；enhanced fan-out 讓延遲敏感的排名服務與風控各自擁有專屬讀取頻寬，互不影響。
>
> **考點**：SAP-2.5、SAP-2.4｜整合 KDS、Firehose 與 EFO 的串流平台設計
