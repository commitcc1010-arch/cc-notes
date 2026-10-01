---
chapter: 29
title: Purpose-built 資料庫
part: 5
---

# 第 29 章　Purpose-built 資料庫：DocumentDB、OpenSearch、Neptune、Keyspaces、Timestream 與選型方法

> [!abstract] 本章地圖
> **你會學到**：
> - 用「資料模型」與「存取模式」解釋為什麼一個關聯式資料庫不適合承擔所有工作
> - 說出 DocumentDB、OpenSearch Service、Neptune、Keyspaces、Timestream、MemoryDB 與 Redshift 各自解決什麼問題、不適合什麼
> - 知道 QLDB 已終止支援、Timestream for LiveAnalytics 不再開放新客戶等服務現況，以及替代做法
> - 設計「一個真相來源、多個衍生視圖」的 polyglot 架構，避免資料同步失控
> - 依「存取模式 → 一致性 → 規模 → 營運」四步驟為新系統或從 Oracle／SQL Server 遷移的系統選資料庫，並考慮授權成本
>
> **前置知識**：第 4 章（資料庫類型與一致性）、第 26 章（RDS 與 Aurora）、第 27 章（DynamoDB）、第 28 章（ElastiCache 與 MemoryDB）
> **考試比重**：SAA ★★☆（Domain 3 高效能資料庫、Domain 4 資料庫成本）｜SAP ★★★（Domain 2 新方案設計、Domain 4 遷移與現代化）

## 29.1 故事：一個 Aurora，五種需求

Wanderly 的核心訂房系統一直跑在 Aurora MySQL 上，表現穩定。但到了成長期，產品團隊一口氣提出五個新需求，每一個都讓資料庫團隊的阿哲皺眉：

1. **旅館搜尋**：使用者打「沖繩 親子 海景 泳池」，要依相關度排序，打錯字（「沖蠅」）也要找得到，還要即時顯示「有泳池的 132 間、有停車場的 87 間」這種分面統計。
2. **旅館內容**：每間旅館的介紹、設施、房型、政策欄位都不一樣，日本溫泉旅館有「入浴時間」，歐洲民宿有「城市稅」；每個月都有新欄位，資料表 schema 改到大家都不敢動。
3. **推薦**：「和你有相似旅遊紀錄的人，也訂了這些旅館」，需要沿著「使用者→訂單→旅館→其他訂單→其他使用者」走好幾層關係。
4. **智慧客房**：合作旅館裝了溫度、用電感測器，每間房每 10 秒回報一次，要能畫出過去 30 天的趨勢。
5. **併購的旅行社**：他們的行程系統跑在自建的 Apache Cassandra 叢集上，還有一套 Oracle 與一套 SQL Server，維運人員下個月就要離職。

阿哲先試著全部用 Aurora 做：搜尋用 `LIKE '%海景%'`，查詢一次全表掃描要 4 秒；推薦用五層 self-join，查詢計畫長到看不完；感測器資料一天新增 2,500 萬列，三個月後索引大到寫入變慢。

他在白板上寫下一句話：「**不是 Aurora 不夠好，是我們在用一把螺絲起子做所有事。**」AWS 把這個想法稱為 **purpose-built 資料庫**：每一種資料模型與存取模式，都有專門為它設計的資料庫。這一章就逐一看這些資料庫解決了什麼，以及更重要的：怎麼避免因為資料庫太多而讓系統失控。

## 29.2 為什麼需要 purpose-built：資料模型決定了什麼查詢便宜

每個資料庫在設計時都做了取捨：它把資料以某種結構存放，讓「某些查詢」非常便宜，代價是「另一些查詢」變貴。

- 關聯式資料庫把資料存成正規化的表格，透過 join 組合，擅長**任意條件的查詢、跨表交易與強一致**；但資料量與寫入量極大時，單一 writer 會成為瓶頸。
- Key-value 資料庫（DynamoDB）用 key 直接定位資料，擅長**已知 key 的超大規模讀寫**；但不能有效率地做任意 join 或臨時查詢。
- 搜尋引擎建立**倒排索引（inverted index）**：預先記錄「每個詞出現在哪些文件」，所以全文搜尋很快；但它不擅長交易與即時一致。

所以選資料庫的第一步不是比較功能清單，而是問：**這個系統最常執行的是什麼查詢？** 這就是 **存取模式（access pattern）**。

| 資料模型 | 資料長什麼樣 | 擅長的查詢 | AWS 服務 |
|---|---|---|---|
| Relational | 固定 schema 的表格與關聯 | 任意 SQL、join、ACID 交易 | RDS、Aurora（第 26 章） |
| Key-value | key → item | 依 key 的大規模低延遲讀寫 | DynamoDB（第 27 章） |
| In-memory | key → 資料結構 | 微秒級讀取、計數、排行榜 | ElastiCache、MemoryDB（第 28 章） |
| Document | 巢狀 JSON 文件 | 依文件內任意欄位查詢、schema 常變 | DocumentDB |
| Wide-column | 分區鍵 + 叢集鍵的寬表 | 巨量寫入、依分區查詢 | Keyspaces |
| Graph | 節點與邊 | 多層關係走訪 | Neptune |
| Time series | 時間戳 + 維度 + 量測值 | 時間範圍聚合、降採樣 | Timestream |
| Search | 倒排索引的文件 | 全文搜尋、相關度排序、日誌分析 | OpenSearch Service |
| Data warehouse | 欄式儲存（columnar） | 大量資料的分析與彙總 | Redshift（第 30 章） |

> [!warning] 常見誤解
> 「資料是 JSON，所以要用 DocumentDB。」JSON 只是表示格式。Aurora PostgreSQL 與 MySQL 都有 JSON 欄位型別，DynamoDB 也能存巢狀文件。真正的判斷依據是存取模式：需要依文件內各種欄位做複雜查詢、聚合，且應用程式已經使用 MongoDB API，DocumentDB 才是自然的答案。

## 29.3 Amazon DocumentDB：MongoDB 相容的文件資料庫

Wanderly 的旅館內容非常適合 **document 模型**：一間旅館是一份 JSON 文件，房型、設施、政策是文件內的巢狀陣列與物件。新增「入浴時間」只是在文件裡多一個欄位，不需要 `ALTER TABLE`。

```json
{
  "_id": "hotel-1234",
  "name": "海風飯店",
  "city": "Okinawa",
  "facilities": ["pool", "parking", "kids_club"],
  "rooms": [
    { "type": "ocean-twin", "max_guests": 3, "base_price": 5200 },
    { "type": "family-suite", "max_guests": 5, "base_price": 9800 }
  ],
  "onsen": { "open": "15:00", "close": "24:00" }
}
```

**Amazon DocumentDB（with MongoDB compatibility）** 是 AWS 受管的文件資料庫，**相容 MongoDB 的 API**：應用程式可以繼續使用 MongoDB driver 與查詢語法，例如 `db.hotels.find({ facilities: "pool", "rooms.max_guests": { $gte: 4 } })`。

### 架構：和 Aurora 很像

DocumentDB 的架構與 Aurora（第 26 章）同一個思路，計算與儲存分離：

- 一個 **cluster** 有一個 **primary instance**（負責寫入）與最多 15 個 **replica instance**（分擔讀取，也是 failover 的候選）。
- 所有 instance 共用一個**分散式 cluster storage**，資料在 3 個 AZ 各保存兩份，共 6 份副本；儲存空間依資料量自動成長。
- 提供 **cluster endpoint**（永遠指向 primary）、**reader endpoint**（分散到 replica）與各 instance 的 endpoint。
- primary 故障時，自動把一個 replica 提升為新的 primary；因為儲存是共用的，replica 不需要「追資料」。
- **備份**：連續備份到 S3，可在保留期內（1–35 天）做 **point-in-time restore**；也能建立手動 snapshot。誤刪 collection 這種邏輯錯誤會立刻同步到所有 replica，只能靠 PITR 或 snapshot 復原。
- 支援 **change streams**，讓下游系統依文件變更觸發處理。

需要更大規模時，有兩個延伸選項：**Global Clusters** 把資料非同步複寫到其他 Region，提供跨 Region 的低延遲讀取與災難復原；**Elastic Clusters** 則以分片（sharding）把資料與寫入分散到多個節點，用在單一 writer 撐不住的超大規模文件工作負載。

### 相容，不等於完全相同

DocumentDB 不是執行 MongoDB 的原始程式，而是 AWS 自己實作、**相容特定版本 MongoDB API** 的服務。大部分常用的 CRUD、索引、聚合與交易都支援，但部分運算子、索引類型與管理指令不支援或行為不同。遷移前必須依目標版本查核相容性清單，並用真實的查詢與 driver 測試。若應用程式重度依賴 DocumentDB 不支援的 MongoDB 功能，替代方案是在 AWS 上使用 MongoDB 官方的受管服務（透過 AWS Marketplace），或在 EC2 自行維運 MongoDB。

> [!tip] 考試提示
> 題目出現「既有 MongoDB 應用程式、遷移到受管服務、最少程式改動」→ DocumentDB。搬資料可用 `mongodump`／`mongorestore` 做離線遷移，或用 AWS DMS（Database Migration Service）做全量載入加持續複寫（CDC，change data capture：持續擷取來源的每一筆變更）以縮短停機時間（第 45 章）。

## 29.4 Amazon OpenSearch Service：搜尋與日誌分析

回到使用者輸入「沖蠅 親子 海景」的搜尋框。關聯式資料庫的 B-tree 索引擅長「等於」與「範圍」，但 `LIKE '%海景%'` 這種前後都有萬用字元的查詢無法使用索引，只能掃描整張表；它也不懂「相關度」，更不會把「沖蠅」糾正成「沖繩」。

### 倒排索引：全文搜尋為什麼快

搜尋引擎在寫入文件時，先把文字切成詞（**analyzer**，中文需要斷詞器），再建立「詞 → 出現在哪些文件」的對照表：

```text
文件 1：「沖繩 海景 飯店，親子 泳池」
文件 2：「大阪 市區 飯店，近 地鐵」
文件 3：「沖繩 親子 民宿」

倒排索引：
  沖繩 → [1, 3]      海景 → [1]      親子 → [1, 3]
  飯店 → [1, 2]      泳池 → [1]      大阪 → [2]
```

查詢「沖繩 親子 海景」時，只要取出三個詞的文件清單、合併、依出現次數與詞的稀有程度計算**相關度分數**，就能在毫秒內回傳排序好的結果，不需要逐一掃描文件。模糊比對（fuzzy match）能容忍拼錯的字，**aggregation** 能同時算出「有泳池的有幾間」這種分面統計。

### OpenSearch Service 的組成

**OpenSearch** 是從 Elasticsearch 7.10 分支出來的開源搜尋與分析引擎，**Amazon OpenSearch Service** 是 AWS 的受管版本（也支援舊版 Elasticsearch 到 7.10）。核心概念：

- **Domain**：一個 OpenSearch 叢集。
- **Index**：一組文件，類似資料庫的一張表；index 被切成多個 **shard**，每個 primary shard 可以有 **replica shard**，放在不同節點上提供讀取擴充與容錯。
- **Data node**：存放 shard、執行查詢。
- **Dedicated master node（cluster manager node）**：專門管理叢集狀態，不存資料。正式環境建議使用 **3 個** dedicated master node，避免叢集管理工作被查詢負載拖垮，也讓多數決在一個節點故障時仍能運作。
- **Multi-AZ**：把節點分散到多個 AZ（zone awareness），replica shard 會放在與 primary shard 不同的 AZ。**Multi-AZ with Standby** 進一步在 3 個 AZ 中保留一個待命 AZ，AZ 故障時快速切換，是正式環境推薦的部署方式。
- **OpenSearch Dashboards**：視覺化與查詢介面。

### 儲存分層與日誌分析

OpenSearch 另一個大用途是**日誌分析**：把應用程式日誌、CloudTrail、VPC Flow Logs 匯入，用全文搜尋與聚合快速排查問題。日誌的特性是「新資料常被查、舊資料很少看但要保存」，所以 OpenSearch Service 提供儲存分層：

| 層級 | 底層 | 特性 | 適合 |
|---|---|---|---|
| Hot | data node 的 EBS 或 instance store | 最快，可讀寫 | 最近幾天、頻繁查詢的資料 |
| UltraWarm | S3 加上節點快取 | 唯讀、成本低很多 | 數週到數月、偶爾查詢 |
| Cold | S3，需要時再掛載 | 最便宜，查詢前要先 attach | 稽核或法規保存 |

**Index State Management（ISM）** 讓你用政策自動化 index 的生命週期，例如「index 大小超過 50 GB 就 rollover 產生新 index → 7 天後移到 UltraWarm → 90 天後移到 cold → 365 天後刪除」。

### OpenSearch Serverless

不想管理節點時，可以使用 **OpenSearch Serverless**：建立 **collection**（依用途分為 search、time series、vector search 三種類型），服務依負載自動擴縮運算能力，以 **OCU（OpenSearch Compute Unit）** 計費。它適合流量變化大或不想做容量規劃的情境；需要細緻控制節點、外掛或特定版本時仍用 domain。

### 安全

OpenSearch domain 可以部署在 **VPC 內**（透過 security group 控制連線）或使用 public endpoint 加上存取政策；正式環境建議 VPC。授權分三層：**domain access policy**（resource-based policy，決定哪些 IAM principal 能呼叫 domain）、**fine-grained access control**（以角色控制到 index、文件甚至欄位層級）、以及 Dashboards 的登入（可整合 SAML 或 Cognito）。加密包括靜態加密、節點間加密與 HTTPS。

### OpenSearch 不是 source of truth

這是最重要的設計原則。OpenSearch 的資料是**從主要資料庫衍生出來的搜尋視圖**：

- 寫入後要經過 refresh（預設約 1 秒）才搜尋得到，屬於 near real-time，不是交易式的即時一致。
- 調整 mapping（欄位型別、斷詞器）常常需要**重建 index（reindex）**，所以必須能從來源重新匯入全部資料。
- 它沒有關聯式資料庫那樣的跨文件交易與約束。

Wanderly 的做法是：旅館資料的真相在 DocumentDB 與 Aurora，變更透過 change streams 或 CDC 送到 OpenSearch。常見的同步管道包括：**OpenSearch Ingestion**（受管的資料管線）、DynamoDB 到 OpenSearch 的 **zero-ETL 整合**、Data Firehose（第 31 章），或 DynamoDB Streams 觸發 Lambda 寫入。

> [!note] 向量搜尋
> OpenSearch 也支援 **向量搜尋（k-NN）**：把文字或圖片轉成向量（embedding），找出「意思最接近」的內容，是 AI 助理以 RAG（檢索增強生成）查資料的常見基礎。其他支援向量搜尋的 AWS 資料庫包括 Aurora PostgreSQL（pgvector 擴充）、MemoryDB、DocumentDB 與 Neptune Analytics。已經使用 Aurora PostgreSQL 且向量數量適中時，直接啟用 pgvector 通常是新增元件最少的做法；這部分在 Part 9 會再展開。

## 29.5 Amazon Neptune：關係本身就是資料

推薦功能的查詢是：「找出和使用者 A 訂過同一間旅館的人，他們還訂了哪些 A 沒去過的旅館，依人數排序」。在關聯式資料庫裡，每多走一層關係就多一次 join，資料量大時成本呈爆炸性成長，而且查詢層數是寫死在 SQL 裡的。

**Graph（圖）資料庫**把資料存成 **vertex（節點）** 與 **edge（邊）**。每個節點直接記錄它連到哪些節點，所以「沿著關係走下一步」的成本只和走過的邊數有關，不需要掃描整張表：

```text
(使用者 A)──訂了──►(海風飯店)◄──訂了──(使用者 B)──訂了──►(琉球民宿)
     │                                     │
     └──追蹤──►(使用者 C)──訂了──►(那霸商旅) └──評論──►(琉球民宿)
```

從使用者 A 出發，走「訂了 → 被誰訂了 → 他們訂了什麼」三步，就得到推薦候選。

**Amazon Neptune** 是 AWS 受管的圖資料庫，支援兩種圖模型與三種查詢語言：

| 模型 | 查詢語言 | 適合 |
|---|---|---|
| Property graph（節點與邊都可以有屬性） | Apache TinkerPop **Gremlin**、**openCypher** | 社群關係、推薦、詐欺偵測、權限關係 |
| RDF（主詞-述詞-受詞三元組） | **SPARQL** | 知識圖譜、語意網、需要標準本體論的資料 |

例如用 openCypher 寫推薦查詢：

```text
MATCH (a:User {id: 'A'})-[:BOOKED]->(:Hotel)<-[:BOOKED]-(other:User)-[:BOOKED]->(h:Hotel)
WHERE NOT (a)-[:BOOKED]->(h)
RETURN h.name, count(other) AS score
ORDER BY score DESC LIMIT 10
```

Neptune 的架構也和 Aurora 類似：一個 primary 加最多 15 個 read replica、共用跨 3 AZ 保存 6 份副本的儲存、cluster endpoint 與 reader endpoint、自動 failover、PITR。延伸能力包括 **Neptune Serverless**（依負載自動擴縮容量）、**Neptune Global Database**（跨 Region 複寫，提供就近讀取與災難復原）、**Neptune Analytics**（把大型圖載入記憶體做圖演算法分析與向量搜尋），以及 **Neptune ML**（用圖神經網路預測關係）。資料可以用 bulk loader 從 S3 大量匯入。

典型使用情境：**詐欺偵測**（同一裝置、同一信用卡、同一地址串起的帳號群）、**推薦**、**社群網路**、**知識圖譜**、**身份圖譜**（把同一個人在不同裝置上的身份連起來）、**IT 網路拓撲與依賴分析**。

> [!warning] 常見誤解
> 「有關聯就用 Neptune。」幾乎所有資料都有關聯。只有在查詢的核心是**多層、層數不固定的關係走訪**（朋友的朋友的朋友、找出環狀資金流）時，圖資料庫才有明顯優勢；一般的「訂單屬於會員」一層關係，關聯式資料庫做得很好。

## 29.6 Amazon Keyspaces：受管的 Cassandra

併購的旅行社把行程事件存在自建的 **Apache Cassandra** 叢集。Cassandra 是一種 **wide-column（寬欄）** 資料庫：資料以 **partition key** 分散到很多節點，同一個 partition 內依 **clustering column** 排序，擅長每秒大量寫入與「給我某個 partition 在某段範圍內的資料」這種查詢。它的查詢語言是 **CQL（Cassandra Query Language）**，語法像 SQL，但沒有 join，資料表要依查詢事先設計。

自建 Cassandra 的維運很辛苦：要調整 compaction、修復節點、擴充叢集、升級版本。**Amazon Keyspaces（for Apache Cassandra）** 是 AWS 的 **serverless、相容 Cassandra** 的資料庫：

- **相容 CQL 與 Cassandra driver**，既有應用程式通常只需要改連線設定（例如啟用 TLS 與驗證方式）。
- **Serverless**：沒有節點與叢集要管理，表格依流量自動擴縮。
- **容量模式**：on-demand（按請求計費，適合難預測流量）或 provisioned（設定讀寫容量並可搭配 auto scaling，適合穩定流量），概念與 DynamoDB 相同（第 27 章）。
- 資料自動在多個 AZ 保存 3 份副本；支援 PITR、靜態加密、IAM 驗證。
- 支援 **multi-Region replication**，在多個 Region 提供可讀寫的表格。

和 DynamoDB 比較：兩者都是 serverless 的大規模 NoSQL。**Keyspaces 的價值在於相容 Cassandra**，讓既有 Cassandra 應用程式與團隊技能可以直接沿用；全新的系統若沒有 Cassandra 包袱，DynamoDB 通常是更常見、整合更多的選擇。遷移時要注意，Keyspaces 並非支援所有 Cassandra 功能（例如部分管理操作與特定功能），同樣需要先比對相容性。

> [!tip] 考試提示
> 「既有 Cassandra 叢集、維運負擔重、想改用受管或 serverless、最少程式改動」→ Amazon Keyspaces。看到 Cassandra 卻選 DynamoDB，通常需要改寫資料存取層，不是「最少改動」。

## 29.7 時間序列：Amazon Timestream 與它的現況

智慧客房感測器資料的特性非常鮮明：

- **幾乎只有新增**，很少修改或刪除。
- 每筆資料都帶著**時間戳**、描述來源的**維度**（旅館、房號、感測器類型）與**量測值**（溫度 24.5、用電 1.2 kWh）。
- 查詢幾乎都是**時間範圍的聚合**：「過去 24 小時每 5 分鐘的平均溫度」「上個月每天的用電總量」。
- **新資料查詢頻繁、舊資料很少查**，而且常常要降採樣（把每 10 秒一筆壓縮成每小時一筆）後長期保存。

這種資料稱為 **time series（時間序列）**。通用資料庫可以存，但每天幾千萬筆的寫入會讓索引越來越大，時間範圍聚合也越來越慢。時間序列資料庫會依時間分區、壓縮相鄰的資料、內建時間聚合函式。

AWS 的時間序列服務是 **Amazon Timestream**，目前有兩個產品，現況不同，寫架構時要特別注意：

- **Timestream for LiveAnalytics**：原本的 serverless 時間序列資料庫，資料先寫進 **memory store**（處理最近的資料、快速寫入與查詢），依保留期限自動移到成本較低的 **magnetic store**（長期保存與分析），以 SQL 查詢。**自 2025 年 6 月 20 日起，LiveAnalytics 不再開放新客戶使用**；已在使用的客戶（其 payer account 下）可以繼續使用並新增帳號，AWS 也持續維護服務，但新的設計不應以它為基礎，AWS 建議新客戶評估 Timestream for InfluxDB。
- **Timestream for InfluxDB**：受管的 **InfluxDB**（廣泛使用的開源時間序列資料庫），以 instance 方式部署，可選 Multi-AZ，使用 InfluxDB 的 API 與查詢語言，可以搭配 Grafana 等常見工具。新的時間序列工作負載，特別是已經使用 InfluxDB 生態系的團隊，通常選擇它。

時間序列也不一定要用專門的資料庫。量不大時，DynamoDB 以「感測器 ID」為 partition key、「時間」為 sort key，再搭配 TTL 自動刪除舊資料，就是一個簡單的方案；長期的歷史資料則可以匯出到 S3，以 Parquet 格式用 Athena 分析（第 30 章）。IoT 裝置的資料收集與串流處理在第 31 章介紹。

> [!note] 時效說明
> 考試題目可能仍以 Timestream（LiveAnalytics）作為「時間序列資料、serverless」的答案，因為題庫更新有時間差。理解它的設計（memory store 與 magnetic store 分層）仍然有價值；但在實際新專案中，請以服務的最新可用性為準。

## 29.8 MemoryDB 與 Ledger 需求：QLDB 之後怎麼辦

### MemoryDB 的定位複習

第 28 章介紹過 **Amazon MemoryDB**：相容 Valkey 與 Redis OSS、以跨多個 AZ 的交易日誌保證寫入耐久的 **in-memory 主要資料庫**。在 purpose-built 選型中，它對應的存取模式是「需要微秒級讀取、Redis 資料結構，而且資料不能遺失、不想另外維護一個資料庫」，例如即時庫存、遊戲狀態、高速計數。如果只是要加速另一個資料庫，用 ElastiCache 就夠了。

### Ledger 資料庫與 QLDB 的現況

有些系統需要**可驗證、不可竄改的完整變更歷史**：例如會員點數、金流對帳、合約版本，稽核人員要確認「沒有人偷偷改過歷史紀錄」。**Ledger（帳本）資料庫**用密碼學的雜湊鏈（每筆紀錄包含前一筆紀錄的雜湊值）讓任何竄改都會被發現。

AWS 過去提供 **Amazon QLDB（Quantum Ledger Database）** 做這件事，但 **AWS 已終止 QLDB（於 2025 年 7 月 31 日停止支援）**，不能再作為新架構的選項，既有使用者需要遷移。AWS 建議的遷移目標是 **Aurora PostgreSQL**。在關聯式資料庫上實現類似的保證，常見做法包括：

- 使用**只允許新增（append-only）的歷史表**：以資料庫權限撤銷應用程式帳號對歷史表的 `UPDATE` 與 `DELETE`，每次變更都新增一筆紀錄。
- 在每筆紀錄中保存**前一筆紀錄的雜湊值**，形成應用程式層的雜湊鏈，稽核時重新計算驗證。
- 定期把歷史紀錄匯出到啟用 **S3 Object Lock**（compliance mode）的 bucket，讓保存期間內任何人（包括 root）都無法刪除或修改（第 16、23 章）。
- 以資料庫稽核日誌（例如 PostgreSQL 的 pgAudit）記錄誰做了什麼操作。

> [!warning] 常見誤解
> 「要防竄改就用 Amazon Managed Blockchain。」區塊鏈解決的是**多個互不信任的組織**共同維護帳本的問題。如果只有 Wanderly 一家公司是資料擁有者、只是要讓稽核能驗證歷史沒被改過，一個 append-only 的資料庫加上 Object Lock 就足夠，而且簡單得多。

## 29.9 Redshift 的定位：OLTP 與 OLAP 是兩件事

財務團隊想知道「過去三年各城市、各季、各旅館等級的營收與取消率」，阿哲在 Aurora 的 read replica 上跑這個查詢，花了 40 分鐘。這不是 Aurora 設計不好，而是**交易型（OLTP）**與**分析型（OLAP）**的工作負載本質不同：

| 比較 | OLTP（線上交易處理） | OLAP（線上分析處理） |
|---|---|---|
| 典型查詢 | 「訂單 #8812 的狀態」「扣一間房」 | 「三年內各城市營收」 |
| 每次觸及的資料 | 少數幾列、所有欄位 | 數億列、少數幾個欄位 |
| 並行量 | 每秒數千到數萬個小交易 | 少量但非常重的查詢 |
| 儲存方式 | 列式（row-oriented） | 欄式（columnar） |
| AWS 服務 | RDS、Aurora、DynamoDB | Redshift、Athena |

**Amazon Redshift** 是 AWS 的 **資料倉儲（data warehouse）**：資料以**欄式儲存**（同一欄的值存在一起，壓縮率高、只讀需要的欄位），並以 **MPP（massively parallel processing，大規模平行處理）** 把查詢分散到多個節點同時執行。它擅長大量歷史資料的彙總分析，但不適合作為處理單筆訂單的交易資料庫。

把資料從 Aurora 送進 Redshift，傳統上需要 ETL 管線；AWS 也提供 Aurora、RDS 與 DynamoDB 到 Redshift 的 **zero-ETL 整合**，自動把交易資料近即時複製到 Redshift 供分析。Redshift 的架構（RA3、Serverless、Spectrum、data sharing）與資料湖在第 30 章詳述。

## 29.10 Polyglot persistence：一個真相，多個視圖

到這裡，Wanderly 的架構裡多了好幾個資料庫。阿哲最擔心的不是「每個資料庫怎麼用」，而是「**同一份資料存在好幾個地方，誰說了算？**」使用多種資料庫的做法稱為 **polyglot persistence（多語言持久化）**，它的成敗取決於資料流設計。

### 原則：每一類資料只有一個 owner

```text
                        [應用程式／API]
                 ① 寫入只到 owner（各自的 source of truth）
        ┌───────────────┬──────────────┬────────────────┐
        ▼               ▼              ▼                ▼
   [Aurora MySQL]   [DocumentDB]   [Keyspaces]    [Timestream for
    訂單、付款        旅館內容        行程事件        InfluxDB] 感測器
        │               │
        │ ② CDC／       │ ② change streams
        │   outbox      │
        ▼               ▼
   ┌──────────────────────────────┐
   │  事件管道（EventBridge／      │
   │  Kinesis／OpenSearch Ingestion）│ ③ 冪等寫入、可重放
   └──────┬──────────────┬────────┘
          ▼              ▼              ④ zero-ETL
   [OpenSearch]      [Neptune]     [Aurora] ──────► [Redshift]
    搜尋視圖          推薦關係圖                       分析視圖
          ▲              ▲
          └── ⑤ 可從 owner 重建（reindex／重新載入）
```

① **寫入只進入 owner**：訂單只寫 Aurora、旅館內容只寫 DocumentDB。應用程式不同時寫入多個資料庫，避免「一邊成功一邊失敗」的 dual write 問題。② owner 的變更以 **CDC（change data capture，擷取資料變更）** 或 **transactional outbox**（在同一筆交易中把事件寫進 outbox 表，再由另一程序送出，第 33 章）發布。③ 事件管道把變更送到衍生視圖；寫入要設計成**冪等（idempotent）**，同一事件處理兩次結果也一樣，因為事件可能重送。④ 分析用途透過 zero-ETL 或 ETL 進入 Redshift。⑤ 所有衍生視圖都必須能**從 owner 重建**：OpenSearch mapping 改了就 reindex，Neptune 圖模型改了就重新載入。

### 每多一個資料庫，就多一份成本

Purpose-built 不是「越多越好」。每增加一種資料庫，團隊就要多學一套查詢語言、多一套備份與還原流程、多一種監控指標、多一條同步管道、多一個值班時要懂的系統。好的架構師會問：**現有的資料庫能不能用合理的成本滿足這個需求？**

- 搜尋需求很簡單（只依名稱前綴查詢）？Aurora 的索引就夠了，不必上 OpenSearch。
- 只需要一層關係？用 join，不必上 Neptune。
- 文件資料量不大、團隊熟悉 PostgreSQL？Aurora PostgreSQL 的 JSONB 欄位就能處理。
- 向量數量適中？Aurora PostgreSQL 的 pgvector 可能比新增一個向量資料庫更划算。

只有當「專用資料庫帶來的效能、成本或開發效率提升」明顯大於「多一個系統的營運成本」時，才值得引入。

## 29.11 從 Oracle 與 SQL Server 選型：授權是隱藏的架構限制

併購來的旅行社還有一套 Oracle Enterprise Edition 與一套 SQL Server。商用資料庫的遷移決策，常常不是由技術、而是由**授權（license）**決定。這是 SAP 考試的重點題型。

### 選項光譜：從原封不動到完全重構

| 選項 | 說明 | 授權 | 營運負擔 | 適合 |
|---|---|---|---|---|
| EC2 自行安裝 | 完全掌控 OS 與資料庫 | BYOL（自帶授權）；依 socket／core 計價的授權可能需要 **Dedicated Hosts**（第 17 章） | 最高 | 需要 RDS 不支援的功能或設定 |
| **RDS Custom**（Oracle、SQL Server） | 受管資料庫，但可以登入 OS、安裝第三方代理程式、做特殊設定 | Oracle 只能 BYOL（自備安裝媒體與授權）；SQL Server 可用 License Included 或自備媒體與授權（BYOM） | 中 | 需要 OS 或特權存取的舊應用程式 |
| **RDS for Oracle** | 完全受管 | **License Included 只提供 Standard Edition 2**；Enterprise Edition 需 BYOL | 低 | 不需要 OS 存取的 Oracle 工作負載 |
| **RDS for SQL Server** | 完全受管 | License Included（授權費含在每小時價格中） | 低 | 一般 SQL Server 工作負載 |
| **Babelfish for Aurora PostgreSQL** | Aurora PostgreSQL 能理解 SQL Server 的 T-SQL 語法與 TDS（Tabular Data Stream，SQL Server 用戶端使用的網路協定） | 不需要 SQL Server 授權 | 低 | 想擺脫 SQL Server 授權、又想減少程式改寫 |
| 轉換到 Aurora PostgreSQL／MySQL | 用 SCT（AWS Schema Conversion Tool）或 DMS Schema Conversion 轉換 schema 與程式碼，DMS 搬資料（第 45 章） | 不需要商用授權 | 低 | 長期現代化、降低授權成本 |

幾個需要記住的細節：

- **RDS 不支援 Oracle RAC**（Real Application Clusters）。依賴 RAC 或 Exadata 特性的系統，傳統上只能考慮 EC2 自建或保留在地端；AWS 與 Oracle 近年另外推出 **Oracle Database@AWS**（在 AWS 資料中心內執行、由 Oracle 管理的 Exadata 服務），屬於較新的選項，可用 Region 有限，導入前要確認現況。
- **大量使用 PL/SQL 預存程序**的 Oracle 系統，轉換到 PostgreSQL 的工作量大；SCT 的評估報告會列出可自動轉換與需要人工處理的比例，是決定「先搬過去（rehost／replatform）還是重構（refactor）」的依據（第 44 章）。
- **Babelfish** 並非支援所有 T-SQL 功能，遷移前要先用評估工具確認相容程度。
- License Included 的好處是不用管授權稽核、隨用隨付；BYOL 的好處是已經買的授權不浪費。題目若說「公司已有大量 Oracle Enterprise Edition 授權且有軟體保證」，BYOL 通常比較划算；若說「要降低長期授權成本」，答案往往是轉到 Aurora PostgreSQL。

## 29.12 比較與選型

### 四步驟選型流程

選資料庫時依序回答四個問題，每一步都會縮小候選範圍：

```text
① 存取模式：最常見的查詢是什麼？
   ├─ 任意 SQL、join、跨表交易 ──────────────► RDS／Aurora
   ├─ 已知 key 的大規模讀寫 ─────────────────► DynamoDB
   ├─ 巢狀文件、依多欄位查詢、MongoDB API ───► DocumentDB
   ├─ 多層關係走訪 ───────────────────────────► Neptune
   ├─ Cassandra／CQL、巨量寫入 ──────────────► Keyspaces
   ├─ 時間範圍聚合 ───────────────────────────► Timestream for InfluxDB
   ├─ 全文搜尋、相關度、日誌分析 ─────────────► OpenSearch（衍生視圖）
   ├─ 微秒級、Redis 資料結構、需耐久 ─────────► MemoryDB
   └─ 大量歷史資料分析 ───────────────────────► Redshift／Athena
② 一致性與交易：需要強一致、多筆資料的 ACID 交易嗎？
   └─ 需要跨多實體的複雜交易 → 偏向關聯式；衍生視圖只能最終一致
③ 規模：資料量、每秒讀寫量、是否需要多 Region 寫入？
   └─ 單一 writer 不夠 → DynamoDB、Keyspaces、DocumentDB Elastic Clusters；
      多 Region → global tables、Global Database／Global Clusters
④ 營運：團隊技能、既有程式、授權、是否要 serverless？
   └─ 既有 MongoDB → DocumentDB；既有 Cassandra → Keyspaces；
      不想管容量 → serverless 版本；商用授權 → 29.11 節
```

### 服務總覽

| 服務 | 資料模型 | 相容性／介面 | 部署型態 | 最典型的題目關鍵字 | 不適合 |
|---|---|---|---|---|---|
| DocumentDB | Document | MongoDB API | instance-based cluster（另有 Elastic Clusters） | MongoDB 遷移、JSON 文件、schema 彈性 | 需要完整 MongoDB 功能、強交易的帳務 |
| OpenSearch Service | 搜尋索引 | OpenSearch／Elasticsearch API | domain 或 Serverless | 全文搜尋、模糊比對、日誌分析、向量搜尋 | 作為唯一資料來源 |
| Neptune | Graph | Gremlin、openCypher、SPARQL | cluster 或 Serverless | 社群關係、推薦、詐欺環、知識圖譜 | 一般 CRUD 與報表 |
| Keyspaces | Wide-column | Cassandra CQL | serverless | 既有 Cassandra、serverless | 需要 join 或臨時查詢 |
| Timestream for InfluxDB | Time series | InfluxDB API | instance-based | IoT、指標、時間範圍聚合 | 交易資料 |
| MemoryDB | In-memory | Valkey／Redis OSS API | cluster | 微秒讀取＋耐久 | 只需要快取（用 ElastiCache） |
| Redshift | Columnar warehouse | SQL（PostgreSQL 方言） | provisioned 或 Serverless | OLAP、BI、PB 級分析 | 高並行的單筆交易 |
| QLDB | Ledger | — | **已終止支援** | 舊題目的「不可竄改帳本」 | 新架構（改用 Aurora PostgreSQL 等） |

## 29.13 考試這樣考

| 題目出現的關鍵字 | 優先想到 |
|---|---|
| MongoDB 相容、JSON 文件、遷移既有 MongoDB | DocumentDB |
| 全文搜尋、模糊比對、相關度排序、分面統計 | OpenSearch Service |
| 日誌集中搜尋與視覺化、Kibana／Dashboards | OpenSearch Service（搭配 UltraWarm／cold 與 ISM） |
| 社群網路、朋友的朋友、推薦、詐欺環、知識圖譜 | Neptune |
| Gremlin、openCypher、SPARQL | Neptune |
| Apache Cassandra、CQL、serverless | Keyspaces |
| IoT 感測器、時間序列、指標 | Timestream（新工作負載注意 LiveAnalytics 已不開放新客戶，改用 Timestream for InfluxDB） |
| Redis 相容、耐久、主要資料庫 | MemoryDB |
| 不可竄改的變更歷史、可驗證 | 舊題答案是 QLDB；新架構用 Aurora PostgreSQL append-only 設計 + S3 Object Lock |
| 數年資料的複雜分析、BI | Redshift（第 30 章） |
| Oracle EE 已有授權、要受管 | RDS for Oracle BYOL；需要 OS 存取 → RDS Custom for Oracle |
| SQL Server 應用程式、去除授權、少改程式 | Babelfish for Aurora PostgreSQL |
| 異質資料庫轉換 | SCT／DMS Schema Conversion + DMS（第 45 章） |

**常見陷阱**：

1. 把 OpenSearch 當成交易資料的唯一存放處：它是 near real-time 的衍生視圖，mapping 變更需要 reindex，必須能從 owner 重建。
2. 以為 DocumentDB 完全等同 MongoDB：它相容特定版本 API，部分功能不支援，遷移前要驗證。
3. 只要資料有「關聯」就選 Neptune：一兩層的固定關係用關聯式資料庫的 join 就夠了。
4. 選 QLDB 作為新設計：QLDB 已終止支援。
5. 把 Redshift 當 OLTP：它為大型分析查詢設計，不適合大量的單筆讀寫交易。
6. 以為 RDS for Oracle 的 License Included 包含 Enterprise Edition：License Included 只有 Standard Edition 2。
7. 為每個新需求都加一個新資料庫：每多一個資料庫就多一份同步、備份、監控與技能成本。

## 29.14 SAP 加深：遷移、整併與跨 Region 的資料庫組合

### 併購後的資料庫整併策略

Wanderly 併購旅行社後，面對的是 Cassandra、Oracle、SQL Server 三套系統與一個即將離職的 DBA。SAP 題目常把這類情境包裝成「在 6 個月內遷移、降低營運負擔、控制授權成本」。典型的分階段策略：

1. **先降低營運風險**：把維運最重、人員最缺的系統先搬到受管服務，例如 Cassandra → Keyspaces、SQL Server → RDS for SQL Server（replatform），程式幾乎不改。
2. **再處理授權成本**：Oracle 依 SCT 評估結果，PL/SQL 少的系統轉到 Aurora PostgreSQL；PL/SQL 多、時程緊的系統先以 BYOL 上 RDS for Oracle，列入下一波現代化。
3. **最後才重構資料模型**：例如把行程事件從 Keyspaces 整合到 Wanderly 既有的 DynamoDB，或把旅行社的商品資料併入 DocumentDB。這一步需要改寫應用程式，風險最高，應放在穩定之後。

7Rs 與 wave planning 的完整方法在第 44 章，遷移工具與切換步驟在第 45 章。

### 跨 Region 的資料庫組合

當 Wanderly 走向多 Region（第 42 章）時，每一種 purpose-built 資料庫的跨 Region 能力不同，架構師要逐一確認：

| 服務 | 跨 Region 能力 |
|---|---|
| Aurora | Global Database（第 26 章） |
| DynamoDB | Global tables，多 Region 可寫入（第 27 章） |
| DocumentDB | Global Clusters，一個 primary Region 可寫入，其他 Region 唯讀 |
| Neptune | Global Database，一個 primary Region 可寫入 |
| Keyspaces | Multi-Region replication，多 Region 可寫入 |
| ElastiCache | Global Datastore（第 28 章） |
| OpenSearch | 跨叢集複寫（cross-cluster replication）或在各 Region 從 owner 各自建立索引 |

「只有一個 Region 可寫入」的服務，在 primary Region 故障時需要提升 secondary 並把寫入流量導過去；「多 Region 可寫入」的服務則要處理同一筆資料在兩地同時被修改的衝突。衍生視圖（OpenSearch、Neptune 推薦圖）通常不必跨 Region 複寫，可以在每個 Region 從本地的 owner 副本各自重建，減少跨 Region 依賴。

### 治理：不讓 purpose-built 變成 purpose-sprawl

大型組織常見的問題是每個團隊自己挑資料庫，最後公司裡有十幾種資料庫、每一種都只有一兩個人懂。SAP 層級的做法是建立「核准的資料庫清單與選型準則」、用 Service Catalog 或 IaC 範本提供預先設定好備份、加密與監控的資料庫（第 37 章），並用 AWS Config 規則檢查加密與備份是否啟用（第 16 章）。這樣團隊仍能選對工具，但每個工具都有一致的營運基線。

## 本章重點整理

- Purpose-built 的核心是「資料模型決定哪些查詢便宜」：先找出最常見的存取模式，再選資料庫。
- DocumentDB 是相容 MongoDB API 的受管文件資料庫，架構類似 Aurora（共用儲存、最多 15 個 replica、PITR），但並非支援所有 MongoDB 功能，遷移前要驗證相容性。
- OpenSearch Service 以倒排索引提供全文搜尋、模糊比對、聚合與日誌分析；正式環境使用 3 個 dedicated master node 與 Multi-AZ（with Standby）。
- OpenSearch 的 hot、UltraWarm、cold 分層搭配 ISM 自動化 index 生命週期，可以大幅降低日誌保存成本；不想管節點時可用 OpenSearch Serverless。
- OpenSearch 是衍生的搜尋視圖，不是 source of truth；資料應由 owner 透過 CDC 或事件同步，且必須能 reindex 重建。
- Neptune 是圖資料庫，支援 property graph（Gremlin、openCypher）與 RDF（SPARQL），適合多層關係走訪，例如推薦、詐欺偵測與知識圖譜。
- Keyspaces 是 serverless、相容 Cassandra CQL 的 wide-column 資料庫，主要價值在於讓既有 Cassandra 工作負載少改程式就能改用受管服務。
- Timestream for LiveAnalytics 自 2025 年 6 月 20 日起不再開放新客戶；新的時間序列工作負載可用 Timestream for InfluxDB，或以 DynamoDB、S3 + Athena 實作。
- QLDB 已終止支援；需要可驗證歷史時，以 Aurora PostgreSQL 的 append-only 表、雜湊鏈與 S3 Object Lock 實作。
- MemoryDB 是耐久的 Redis 相容主要資料庫；只需要加速其他資料庫時用 ElastiCache。
- Redshift 是欄式、MPP 的資料倉儲，服務 OLAP 分析；交易處理（OLTP）仍由 RDS、Aurora、DynamoDB 負責，兩者可透過 zero-ETL 串接。
- Polyglot persistence 的原則是每類資料只有一個 owner，其他資料庫是透過 CDC／outbox 冪等同步、可重建的衍生視圖。
- 每增加一種資料庫就增加同步、備份、監控與技能成本；現有資料庫能以合理成本滿足時就不要新增。
- RDS for Oracle 的 License Included 只有 Standard Edition 2，Enterprise Edition 要 BYOL；需要 OS 存取用 RDS Custom；RDS 不支援 Oracle RAC。
- Babelfish for Aurora PostgreSQL 讓 SQL Server 應用程式以 T-SQL 與 TDS 協定連到 Aurora PostgreSQL，是減少程式改寫又能擺脫 SQL Server 授權的選項。

## 本章練習題

### 練習 29-1｜SAA｜單選｜旅館全文搜尋

Wanderly 的旅館資料存在 Aurora MySQL。產品團隊希望使用者能用多個關鍵字搜尋旅館介紹，結果要依相關度排序、能容忍錯字，並同時顯示「有泳池」「有停車場」等分類的數量。目前使用 `LIKE '%關鍵字%'` 查詢，每次需要數秒且結果沒有排序。資料變更後幾秒內反映在搜尋結果即可。

最合適的做法是什麼？

- A. 為 Aurora 的介紹欄位建立 B-tree 索引，並增加 Aurora Replica 分擔查詢
- B. 把旅館資料改存到 DynamoDB，並為每個關鍵字建立 GSI
- C. 建立 Amazon OpenSearch Service domain，把 Aurora 的變更同步到 OpenSearch 建立搜尋索引，搜尋請求改查 OpenSearch
- D. 在 Aurora 前加上 ElastiCache，快取每一組關鍵字的查詢結果

> [!answer]- 答案：C
> **A ✗** 前後都有萬用字元的 `LIKE` 無法使用 B-tree 索引，增加 replica 只是讓更多機器做全表掃描，也沒有相關度排序與錯字容忍。
>
> **B ✗** DynamoDB 擅長依 key 存取，不提供全文搜尋與相關度排序；為每個關鍵字建 GSI 不可行。
>
> **C ✓** OpenSearch 以倒排索引提供全文搜尋、相關度評分、模糊比對與聚合（分面統計）。Aurora 仍是 source of truth，變更以 near real-time 方式同步，符合「幾秒內反映」的需求。
>
> **D ✗** 快取只能加速「重複的相同查詢」，關鍵字組合千變萬化，命中率低；而且第一次查詢仍然慢、沒有排序與錯字容忍。
>
> **考點**：SAA-3.3｜OpenSearch 全文搜尋與衍生索引

### 練習 29-2｜SAA｜單選｜多層關係推薦

Wanderly 要推出「和你旅遊喜好相似的人也訂了」功能。查詢需要從某位使用者出發，找出訂過相同旅館的其他使用者，再找出這些使用者訂過、但該使用者沒去過的旅館，有時還要再往外擴一層。目前 Aurora 上的多層 self-join 隨層數增加而急遽變慢。

最適合評估的資料庫是什麼？

- A. Amazon Neptune，以使用者與旅館為節點、訂房為邊，用 openCypher 或 Gremlin 查詢
- B. Amazon Redshift，把訂單資料載入後用 SQL 計算
- C. Amazon Keyspaces，以使用者 ID 作為 partition key
- D. Amazon DocumentDB，把每位使用者的所有訂單嵌入一份文件

> [!answer]- 答案：A
> **A ✓** 這是典型的多層、層數可變的關係走訪。圖資料庫直接記錄節點之間的邊，走下一層的成本只和相關的邊數有關，不需要多次 join 整張表。Neptune 支援 property graph 與 openCypher／Gremlin。
>
> **B ✗** Redshift 適合大規模彙總分析，可以離線計算推薦，但不適合每個使用者請求即時的多層關係查詢。
>
> **C ✗** Keyspaces 適合依 partition key 讀取大量資料，不支援 join 或關係走訪，跨使用者的多層查詢需要在應用程式中反覆查詢。
>
> **D ✗** 把訂單嵌入使用者文件能快速讀取「某人的訂單」，但「誰也訂了這間旅館」需要反向查詢所有文件，多層走訪仍然昂貴。
>
> **考點**：SAA-3.3｜Neptune 與圖資料模型

### 練習 29-3｜SAA｜單選｜MongoDB 遷移到受管服務

併購來的旅行社有一套在 EC2 上自建的 MongoDB，存放行程商品文件，維運人員即將離職。團隊希望改用 AWS 受管服務，降低修補與備份的營運負擔，並且盡量不修改使用 MongoDB driver 的應用程式。應用程式使用的都是常見的 CRUD、索引與聚合功能。

最合適的目標資料庫是什麼？

- A. Amazon DynamoDB，把每份文件存成一個 item
- B. Amazon Aurora PostgreSQL，把文件存成 JSONB 欄位
- C. Amazon OpenSearch Service，因為它可以存放 JSON 文件
- D. Amazon DocumentDB，並在遷移前驗證應用程式使用的 MongoDB 功能都在相容範圍內

> [!answer]- 答案：D
> **A ✗** DynamoDB 是受管且可存巢狀資料，但它的 API 與查詢方式和 MongoDB 不同，需要改寫資料存取層。
>
> **B ✗** JSONB 能存放文件，但應用程式要從 MongoDB driver 改為 SQL，程式改動大。
>
> **C ✗** OpenSearch 是搜尋引擎，不適合作為行程商品的主要資料庫，也不相容 MongoDB API。
>
> **D ✓** DocumentDB 相容 MongoDB API，應用程式可以沿用 MongoDB driver；它是受管服務，自動處理修補、備份與 failover。因為相容的是特定版本的 API，遷移前仍要驗證使用的功能。
>
> **考點**：SAA-3.3、SAA-2.2｜DocumentDB 與 MongoDB 相容性

### 練習 29-4｜SAA｜單選｜Cassandra 改用 serverless

旅行社的行程事件系統使用自建的 Apache Cassandra 叢集，應用程式以 CQL 與 Cassandra driver 存取資料。團隊希望不再管理節點、修復與擴充叢集，改用依流量自動擴縮的服務，同時把應用程式改動降到最低。

最合適的方案是什麼？

- A. 遷移到 Amazon DynamoDB，並使用 on-demand capacity
- B. 遷移到 Amazon Keyspaces（for Apache Cassandra）
- C. 遷移到 Amazon DocumentDB Elastic Clusters
- D. 把 Cassandra 搬到 EC2 Auto Scaling group，用腳本自動加入新節點

> [!answer]- 答案：B
> **A ✗** DynamoDB 是 serverless，但 API 與 CQL 不同，需要改寫資料存取層，不符合「改動最低」。
>
> **B ✓** Keyspaces 是 serverless、相容 CQL 與 Cassandra driver 的服務，沒有節點要管理，可依流量自動擴縮，既有應用程式通常只需調整連線設定。
>
> **C ✗** DocumentDB 相容的是 MongoDB API，不是 Cassandra。
>
> **D ✗** 在 EC2 上自建仍要處理修復、compaction 與升級，營運負擔沒有減少。
>
> **考點**：SAA-3.3、SAA-4.3｜Keyspaces 與 Cassandra 相容性

### 練習 29-5｜SAA｜單選｜新的時間序列工作負載

Wanderly 要為合作旅館的智慧客房建立新的感測器資料平台。每間房每 10 秒回報溫度與用電，查詢主要是「過去 24 小時每 5 分鐘平均值」這類時間範圍聚合。團隊原本就使用 InfluxDB 的 line protocol 與 Grafana 儀表板，希望改用 AWS 受管服務。這是一個全新的 AWS 帳號與工作負載。

最合適的選擇是什麼？

- A. Amazon Timestream for LiveAnalytics，使用 memory store 與 magnetic store
- B. Amazon RDS for MySQL，以時間欄位建立索引
- C. Amazon Timestream for InfluxDB
- D. Amazon Neptune，以感測器為節點、量測值為邊

> [!answer]- 答案：C
> **A ✗** LiveAnalytics 的分層設計適合時間序列，但它自 2025 年 6 月 20 日起已不再開放新客戶，全新的工作負載不能以它為基礎。
>
> **B ✗** 關聯式資料庫可以存時間序列，但每天數千萬筆寫入會讓索引持續膨脹，時間範圍聚合越來越慢，而且不相容團隊既有的 InfluxDB 工具。
>
> **C ✓** Timestream for InfluxDB 是受管的 InfluxDB，相容 InfluxDB API 與 line protocol，可以直接搭配 Grafana，適合新的時間序列工作負載。
>
> **D ✗** 量測值不是關係，圖資料庫不適合時間範圍聚合。
>
> **考點**：SAA-3.3｜時間序列資料庫與服務現況

### 練習 29-6｜SAA｜單選｜交易資料庫與分析

Wanderly 財務團隊每天要對過去三年、約 20 億筆訂單資料執行營收與取消率的彙總分析，目前在 Aurora 的 read replica 上執行，每次需要 40 分鐘以上，還會讓 replica 的複寫延遲升高。團隊希望分析查詢在數分鐘內完成，而且不影響訂房交易。

最合適的做法是什麼？

- A. 把 Aurora 的 instance class 升級到最大規格
- B. 把訂單資料改存到 DynamoDB，並用 Scan 執行分析
- C. 在 Aurora 前面加上 ElastiCache 快取分析結果
- D. 透過 zero-ETL 整合把 Aurora 的資料複製到 Amazon Redshift，在 Redshift 上執行分析

> [!answer]- 答案：D
> **A ✗** 更大的 instance 能稍微加速，但列式儲存的 OLTP 資料庫掃描數十億列本質上就慢，成本也高。
>
> **B ✗** DynamoDB 的 Scan 會讀取整張表並消耗大量容量，不適合大規模分析。
>
> **C ✗** 分析查詢條件常常變動，快取命中率低，而且第一次執行仍需 40 分鐘。
>
> **D ✓** Redshift 是欄式、MPP 的資料倉儲，專為大量資料的彙總分析設計；zero-ETL 整合自動把交易資料近即時複製過去，分析不再影響 Aurora。
>
> **考點**：SAA-3.3、SAA-3.5｜OLTP 與 OLAP 的分工

### 練習 29-7｜SAA｜單選｜搜尋索引損壞的復原

Wanderly 的工程師修改了 OpenSearch 的 index mapping，結果中文斷詞設定錯誤，搜尋結果大量失準。旅館資料的 source of truth 在 DocumentDB，並透過 change streams 同步到 OpenSearch。團隊要在不影響訂房的情況下修復搜尋。

最合適的做法是什麼？

- A. 以正確的 mapping 建立新 index，從 DocumentDB 重新匯入全部旅館資料，完成後把搜尋流量切到新 index
- B. 從 OpenSearch 的 replica shard 還原出正確的資料
- C. 把 DocumentDB 還原到修改 mapping 之前的時間點
- D. 直接在現有 index 上修改欄位型別，讓 OpenSearch 自動重新分析既有文件

> [!answer]- 答案：A
> **A ✓** OpenSearch 是衍生的搜尋視圖，可以從 owner 重建。用正確的 mapping 建新 index 並重新匯入，再切換流量（例如透過 index alias），全程不影響 DocumentDB 與訂房。
>
> **B ✗** Replica shard 是 primary shard 的即時副本，使用同一個錯誤的 mapping，無法提供正確版本。
>
> **C ✗** DocumentDB 的資料本身是正確的，問題在 OpenSearch 的 mapping；還原 DocumentDB 會遺失之後的正常變更，完全沒有必要。
>
> **D ✗** 既有欄位的型別與分析設定通常不能直接修改，即使能改也不會自動重新分析已寫入的文件，需要 reindex。
>
> **考點**：SAA-3.3、SAA-2.2｜OpenSearch 不是 source of truth

### 練習 29-8｜SAA｜選兩項｜OpenSearch 正式環境高可用

Wanderly 要把旅館搜尋上線到正式環境的 OpenSearch Service domain。需求是：單一節點或一個 AZ 故障時搜尋仍可使用，叢集管理不能因為查詢負載過重而不穩定。

哪兩個設定最合適？（選兩項）

- A. 只使用 1 個 data node，並每小時建立 snapshot
- B. 啟用 Multi-AZ（建議使用 Multi-AZ with Standby），並為 index 設定 replica shard
- C. 把 domain 放在 public endpoint，讓使用者直接查詢
- D. 使用 3 個 dedicated master node
- E. 關閉 replica shard 以提高寫入速度

> [!answer]- 答案：B、D
> **A ✗** 單一 data node 本身就是單點故障；snapshot 用於還原，不能在故障時立即接手查詢。
>
> **B ✓** Multi-AZ 把節點分散到多個 AZ，並讓 replica shard 放在與 primary shard 不同的 AZ；一個 AZ 故障時，其他 AZ 的副本仍能提供查詢。
>
> **C ✗** 公開 endpoint 與高可用無關，反而增加暴露面；搜尋應透過應用程式或 API 存取。
>
> **D ✓** Dedicated master node 專門管理叢集狀態，不受查詢負載影響；3 個節點讓一個節點故障時仍能維持多數決。
>
> **E ✗** 沒有 replica shard，任何存有 primary shard 的節點故障都會讓部分資料無法查詢。
>
> **考點**：SAA-2.2｜OpenSearch dedicated master 與 Multi-AZ

### 練習 29-9｜SAA｜單選｜可驗證的變更歷史

Wanderly 要建立會員點數系統。稽核要求保留每一次點數變動的完整歷史，任何人都不能事後修改或刪除歷史紀錄，稽核時要能驗證歷史未被竄改，且財務人員要能用 SQL 查詢。這是一個 2026 年的新專案。

最合適的設計是什麼？

- A. 使用 Amazon QLDB 作為點數帳本
- B. 在 Aurora PostgreSQL 建立 append-only 的歷史表並撤銷應用程式帳號的 UPDATE／DELETE 權限，每筆紀錄保存前一筆的雜湊值，並定期匯出到啟用 S3 Object Lock compliance mode 的 bucket
- C. 使用 Amazon Managed Blockchain，由 Wanderly 自己維護所有節點
- D. 把點數存在 DynamoDB，並為每個 item 設定 TTL

> [!answer]- 答案：B
> **A ✗** QLDB 已於 2025 年 7 月終止支援，不能作為新專案的選項。
>
> **B ✓** Append-only 表搭配權限控制防止應用程式修改歷史，雜湊鏈讓稽核能驗證紀錄是否被竄改，S3 Object Lock compliance mode 讓匯出的紀錄在保存期間內任何人都無法刪改；Aurora PostgreSQL 也提供財務人員需要的 SQL。
>
> **C ✗** 區塊鏈解決多個互不信任組織共同維護帳本的問題；只有 Wanderly 一方時，它帶來大量不必要的複雜度。
>
> **D ✗** TTL 會自動刪除資料，與「完整保留歷史」相反，DynamoDB 本身也不提供 SQL 與防竄改驗證。
>
> **考點**：SAA-1.3、SAA-3.3｜QLDB 終止支援後的 ledger 設計

### 練習 29-10｜SAA｜單選｜DocumentDB 讀取擴充

Wanderly 的旅館內容存在 DocumentDB，cluster 有 1 個 primary instance。旅館頁面的讀取量在旅遊旺季成長 5 倍，primary 的 CPU 長期在 90% 以上，寫入量則沒有明顯變化。團隊希望在不改變資料模型的情況下提高讀取能力，並同時改善可用性。

最合適的做法是什麼？

- A. 改用 DocumentDB Elastic Clusters，把資料分片到多個節點
- B. 把 primary instance 的儲存容量加倍
- C. 在其他 AZ 新增 replica instance，讓應用程式的讀取改用 reader endpoint
- D. 為每個 AZ 建立獨立的 DocumentDB cluster，並由應用程式同時寫入

> [!answer]- 答案：C
> **A ✗** Elastic Clusters 用於寫入量或資料量超過單一 writer 的情境，需要選擇 shard key，複雜度較高；本題只有讀取增加。
>
> **B ✗** DocumentDB 儲存自動成長，而且瓶頸是 CPU，不是儲存容量。
>
> **C ✓** DocumentDB replica 共用 cluster storage，新增後立即能分擔讀取；reader endpoint 把連線分散到各 replica。replica 放在不同 AZ，也是 primary 故障時自動 failover 的候選，同時改善可用性。
>
> **D ✗** 多個獨立 cluster 加上應用程式雙寫，會產生資料不一致與部分失敗的問題。
>
> **考點**：SAA-3.3、SAA-2.2｜DocumentDB replica 與 reader endpoint

### 練習 29-11｜SAP｜單選｜Oracle 遷移與第三方代理程式

旅行社有一套 Oracle Database Enterprise Edition，公司持有有效的 EE 授權與軟體保證。這套資料庫需要安裝一個第三方的稽核代理程式在作業系統上，並修改部分 OS 層級的設定。公司希望在 3 個月內遷移到 AWS，盡可能使用受管服務的自動備份與修補，並沿用既有授權。應用程式使用大量 PL/SQL，短期內不打算改寫。

最合適的方案是什麼？

- A. 遷移到 Amazon RDS for Oracle，使用 License Included 的 Enterprise Edition
- B. 使用 SCT 把 schema 轉換到 Aurora PostgreSQL，再以 DMS 搬遷資料
- C. 在 EC2 Dedicated Hosts 上自行安裝 Oracle，並自行撰寫備份與修補腳本
- D. 遷移到 Amazon RDS Custom for Oracle，使用 BYOL

> [!answer]- 答案：D
> **A ✗** RDS for Oracle 的 License Included 只提供 Standard Edition 2，沒有 Enterprise Edition；而且標準 RDS 不允許登入作業系統安裝代理程式。
>
> **B ✗** 大量 PL/SQL 的轉換工作量大，與「短期內不改寫、3 個月內完成」衝突，也浪費了既有的 EE 授權。
>
> **C ✗** EC2 自建能滿足 OS 存取與 BYOL，但備份、修補都要自己處理，不符合「盡可能使用受管服務」。
>
> **D ✓** RDS Custom 提供受管資料庫的自動化能力，同時允許存取作業系統以安裝第三方代理程式與調整設定；RDS Custom for Oracle 使用 BYOL，可以沿用既有 EE 授權。
>
> **考點**：SAP-4.2、SAP-1.5｜RDS Custom 與 Oracle 授權

### 練習 29-12｜SAP｜單選｜擺脫 SQL Server 授權

旅行社的訂單管理系統使用 SQL Server Standard Edition，應用程式以 .NET 撰寫，大量使用 T-SQL 查詢與預存程序。公司希望在一年內大幅降低資料庫授權成本，並改用受管服務，但開發團隊人力有限，無法改寫大部分的資料存取程式碼。評估工具顯示絕大多數 T-SQL 功能都在可支援範圍內。

最合適的方案是什麼？

- A. 遷移到 Aurora PostgreSQL 並啟用 Babelfish，讓應用程式以 T-SQL 與 TDS 協定連線
- B. 遷移到 Amazon RDS for SQL Server，使用 License Included
- C. 在 EC2 上安裝 SQL Server，並使用 Dedicated Hosts 降低授權費
- D. 遷移到 Amazon DynamoDB，用 PartiQL 取代 T-SQL

> [!answer]- 答案：A
> **A ✓** Babelfish 讓 Aurora PostgreSQL 理解 T-SQL 與 SQL Server 的 TDS 連線協定，應用程式可以只做少量修改就連上，同時不再需要 SQL Server 授權，也是受管服務。評估工具已確認相容程度，風險可控。
>
> **B ✗** RDS for SQL Server 是受管服務，但 License Included 的費用仍包含 SQL Server 授權，無法「大幅降低授權成本」。
>
> **C ✗** EC2 自建仍需要 SQL Server 授權，營運負擔也更高。
>
> **D ✗** DynamoDB 的資料模型與交易方式完全不同，PartiQL 也不是 T-SQL，需要大規模改寫。
>
> **考點**：SAP-4.3、SAP-2.6｜Babelfish for Aurora PostgreSQL

### 練習 29-13｜SAP｜選兩項｜多資料庫的資料一致性

Wanderly 的新架構中，旅館內容的 source of truth 在 DocumentDB，搜尋使用 OpenSearch，推薦使用 Neptune。目前應用程式在每次更新旅館時依序寫入這三個資料庫，偶爾某一個寫入失敗，造成三邊資料不一致，且很難找出哪些資料不同步。團隊希望三邊最終一致、可以自動恢復，並能在需要時重建衍生資料。

哪兩個做法最合適？（選兩項）

- A. 在應用程式中把三個寫入包在一個分散式交易中，確保同時成功或失敗
- B. 把 OpenSearch 設為 source of truth，因為它能同時提供查詢與搜尋
- C. 應用程式只寫入 DocumentDB，由 change streams 驅動事件管道，以冪等方式更新 OpenSearch 與 Neptune，失敗時自動重試
- D. 縮短 OpenSearch 的 refresh interval，讓三個資料庫的資料保持同步
- E. 保留從 DocumentDB 全量重新匯入 OpenSearch 與 Neptune 的流程，並定期比對資料以發現不一致

> [!answer]- 答案：C、E
> **A ✗** DocumentDB、OpenSearch 與 Neptune 之間沒有共同的分散式交易機制，應用程式無法讓三者原子性地一起提交。
>
> **B ✗** OpenSearch 是 near real-time 的搜尋引擎，沒有跨文件交易，mapping 變更需要重建，不適合當 source of truth。
>
> **C ✓** 寫入只進入 owner，避免 dual write；change streams 把每次變更可靠地送出，冪等處理讓重送的事件不會造成錯誤，失敗自動重試讓衍生視圖最終一致。
>
> **D ✗** Refresh interval 只影響 OpenSearch 多快能搜到已寫入的資料，無法解決寫入失敗造成的不一致。
>
> **E ✓** 衍生視圖必須能從 owner 重建；全量重新匯入處理 mapping 變更或大規模錯誤，定期比對（reconciliation）找出漏掉的事件。
>
> **考點**：SAP-2.4、SAP-4.4｜polyglot persistence 與 CDC 同步

### 練習 29-14｜SAP｜單選｜日誌分析的保存成本

Wanderly 把所有應用程式日誌送到 OpenSearch Service，每天約 500 GB。資安規定要保存 1 年，但實際上 95% 的查詢只針對最近 7 天，偶爾會查 30–90 天前的日誌，更舊的只在稽核時查詢。目前所有資料都放在 hot data node 的 EBS 上，儲存成本每月持續攀升。團隊希望在不影響最近 7 天查詢效能的前提下，以最少的營運工作大幅降低成本。

最合適的做法是什麼？

- A. 把所有 index 的 replica 數改為 0，以減少一半的儲存量
- B. 啟用 UltraWarm 與 cold storage，以 ISM 政策讓 index 每天 rollover、7 天後移到 UltraWarm、90 天後移到 cold、1 年後刪除
- C. 每天把舊 index 的 snapshot 存到 S3 並刪除 index，需要時再手動還原
- D. 換成更大的 data node instance type，讓每個節點裝更多資料

> [!answer]- 答案：B
> **A ✗** 移除 replica 確實減少儲存，但任何節點故障都會讓部分資料無法查詢，犧牲可用性；而且仍然把一整年資料放在昂貴的 hot 層。
>
> **B ✓** UltraWarm 以 S3 加上節點快取保存唯讀資料，成本遠低於 hot；cold storage 更便宜，適合只在稽核時查詢的資料。ISM 政策自動化 rollover、分層移動與刪除，營運工作最少，最近 7 天仍在 hot 層。
>
> **C ✗** Snapshot 可以低成本保存，但每次查詢舊資料都要手動還原，營運工作多，也無法即時查詢 30–90 天的資料。
>
> **D ✗** 更大的節點只是把資料放進更大的 hot 儲存，單位成本沒有下降。
>
> **考點**：SAP-3.5、SAP-2.6｜OpenSearch 儲存分層與 ISM

### 練習 29-15｜SAP｜單選｜詐欺圖譜的跨 Region 災難復原

Wanderly 的詐欺偵測系統使用 Neptune，在東京 Region 保存帳號、裝置、付款方式之間的關係圖。法遵要求：東京 Region 發生災難時，大阪 Region 要在一小時內恢復詐欺查詢與寫入，資料遺失不超過一分鐘；平時大阪的風控分析師也需要低延遲讀取這份圖資料。團隊希望不撰寫自訂的複寫程式。

最合適的方案是什麼？

- A. 每小時建立 Neptune snapshot 並複製到大阪，災難時從 snapshot 還原
- B. 在大阪建立獨立的 Neptune cluster，由應用程式同時寫入兩個 Region
- C. 建立 Neptune Global Database，以東京為 primary、大阪為 secondary；平時大阪提供唯讀查詢，災難時把大阪提升為可寫入的 primary
- D. 把圖資料每天匯出到 S3，啟用 S3 Cross-Region Replication 到大阪，災難時用 bulk loader 重新載入

> [!answer]- 答案：C
> **A ✗** 每小時的 snapshot 代表最多可能遺失一小時資料，超過一分鐘的 RPO；平時大阪也沒有可查詢的資料。
>
> **B ✗** 應用程式雙寫需要自訂程式並處理部分失敗與不一致，違反「不撰寫自訂複寫程式」。
>
> **C ✓** Neptune Global Database 把 primary Region 的資料持續非同步複寫到 secondary Region，複寫延遲通常很短，符合一分鐘的 RPO；secondary 平時提供低延遲唯讀查詢，災難時可提升為 primary 接手寫入。
>
> **D ✗** 每天匯出的 RPO 是一天，大量重新載入也很難在一小時內完成。
>
> **考點**：SAP-2.2、SAP-1.3｜Neptune Global Database

### 練習 29-16｜SAP｜選兩項｜AI 助理的向量儲存

Wanderly 要為 AI 旅遊助理建立 RAG（檢索增強生成）功能，需要儲存約 300 萬筆旅館介紹與評論的向量，並依語意相似度查詢。旅館資料目前存在 Aurora PostgreSQL。團隊希望選擇有原生向量搜尋能力的 AWS 受管服務，並傾向減少需要維運的元件。

哪兩個選項是合適的向量儲存？（選兩項）

- A. 在既有的 Aurora PostgreSQL 啟用 pgvector 擴充，把向量和旅館資料存在同一個資料庫
- B. Amazon Timestream for InfluxDB，以時間戳記錄每個向量
- C. Amazon ElastiCache for Memcached，以向量內容作為 key
- D. Amazon OpenSearch Serverless 的 vector search collection
- E. Amazon Redshift，以 SQL 的 `ORDER BY` 計算距離

> [!answer]- 答案：A、D
> **A ✓** pgvector 讓 Aurora PostgreSQL 支援向量欄位與相似度搜尋。資料已經在 Aurora，向量和旅館資料放在一起不需要新增資料庫，也能在同一筆查詢中結合一般欄位條件，元件最少。
>
> **B ✗** Timestream for InfluxDB 是時間序列資料庫，沒有原生的向量相似度搜尋。
>
> **C ✗** Memcached 只能依完整 key 查詢，無法做「最接近」的相似度搜尋。
>
> **D ✓** OpenSearch Serverless 的 vector search collection 提供原生 k-NN 向量搜尋，並自動擴縮，不需要管理節點；向量數量成長或需要結合全文搜尋時是常見選擇。
>
> **E ✗** Redshift 是分析型資料倉儲，自己用 SQL 計算每筆向量的距離需要掃描全部資料，不適合即時的相似度查詢。
>
> **考點**：SAP-2.5、SAP-4.4｜向量搜尋的資料庫選擇
