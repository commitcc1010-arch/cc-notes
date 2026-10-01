# R04 獨立審查報告：Part 04（第 41–51 章）

- Reviewer：R04（非作者）
- Author artifact：`tools/aws_question_banks/part_04.json`
- 審查日期：2026-10-01
- 審查範圍：第 41–51 章，共 110 題
- 審查依據：
  - `tools/aws_question_banks/README.md`
  - `tools/aws_exam_audits/part_04.md`
  - 現行 AWS 官方文件與 SAA-C03／SAP-C02 scope
  - `tools/aws_architect_deep_content.py` 中的舊 fallback 題

## 結論摘要

本 part 的結構品質明顯優於舊五題模板：11 章皆為 10 題、intent 1–10 各一次，共 77 題單選與 33 題複選；每章均為 7 題單選、3 題複選，答案位置沒有單一字母超過每章 4 次。110 個題幹沒有 exact duplicate，也沒有高相似度的跨題題幹。

逐題審查結果：

- 可保留：97 題
- 必須修訂：13 題
- 最終判定：`REVISE`

需要修訂的題目：

`ch041-q01`、`ch041-q03`、`ch041-q10`、`ch042-q08`、`ch044-q08`、`ch044-q09`、`ch045-q01`、`ch046-q04`、`ch046-q10`、`ch047-q09`、`ch048-q10`、`ch050-q10`、`ch051-q09`

## 結構、來源與原創性檢查

### 通過項目

- 章節範圍為 41–51，總題數 110。
- 每章 intent 皆為 1–10，沒有缺漏或重複。
- 每題的 choice、answer index、逐選項 explanation 與 task mapping 結構完整。
- 每題至少引用一項 AWS 官方來源。
- Top-level sources 共 172 筆：156 筆 AWS 官方來源、16 筆 Jayendra Patil 公開學習文章。
- 所有官方來源 URL 在審查時可存取。
- 未引用 ExamTopics、braindump、recalled live questions、Pass4Sure 或宣稱「actual exam questions」的來源。
- 對 16 篇 community inspiration page 做文字比對，題幹與選項未發現長句直接複製。
- 110 題內沒有完全相同的正解文字集合。

### 需要修正的 provenance metadata

- `ch041-q01` 的 `inspiration_ids` 同時含 community source 與 `aws-saa-sample`。
- `ch045-q01` 的 `inspiration_ids` 同時含 community source 與 `aws-sap-sample`。

README contract 將 `inspiration_ids` 定義為 community inspiration；官方 sample questions 可作形式校準，但不應偽裝成 community inspiration，也不應作為服務行為的 factual source。

Required action：

- `ch041-q01`：重寫題目時一併移除 `aws-saa-sample` 的 community-inspiration mapping。
- `ch045-q01`：從 `inspiration_ids` 移除 `aws-sap-sample`，或先修改全域 schema，明確增加 `official_style_source_ids`；不可只讓 metadata 類型自相矛盾。

## 必須修訂的逐題發現

### `ch041-q01` — 舊 fallback 題的實質重用

現題與舊第 41 章 fallback「多台 Linux servers、append、POSIX/advisory locks、rename directories」使用相同的完整辨識訊號與同一答案。雖然句子加長，解題路徑沒有改變，不符合「replace the old five-question template; do not reuse its prompt or choices」。

Required action：

- 保留 intent 1「Object API 與 POSIX 語意」，但換成不同 use case，例如：
  - SQLite／database file 需要 random in-place writes；
  - build system 依賴 hard link、file ownership、atomic file replacement；
  - application 要 memory-map 一個共享檔案。
- 不可再同時使用 append、lock、directory rename 這組舊題的三個提示。
- 重新建立四個合理 distractors，不要只是把舊答案擴寫。

### `ch041-q03` — 舊 fallback 題與選項配對高度重疊

現題再次使用 Account A 的 reader role、Account B bucket、特定 prefix、`ListBucket` 對 bucket ARN、`GetObject` 對 object ARN。它同時重現舊第 41 章 fallback 第 1 題的 scenario 與第 2 題的 Action/Resource 配對。

Required action：

- 保留 intent 3，但改成不同授權問題，例如：
  - 比較 direct bucket-policy grant 與 `AssumeRole`；
  - S3 Access Point 跨帳號加 SSE-KMS；
  - `s3:ListBucketVersions`、version ARN 與 KMS encryption context。
- 不可再使用 `AnalyticsReader`／`raw/` prefix 或將舊的兩個 ARN 配對直接搬入正解。

### `ch041-q10` — Compliance retention 與 legal hold 被寫成可互換

Prompt 要求固定七年 retention，期間一般管理者不能刪除。正解 C 寫成「Compliance mode 或適當 legal hold」。兩者不是同一契約：

- Compliance-mode retention 有固定 retain-until date，受保留版本在期限內不可刪除或縮短。
- Legal hold 沒有固定到期日，而且具 `s3:PutObjectLegalHold` 權限的 principal 可以移除。

因此「legal hold 作為七年 compliance retention 的替代方案」會讓正解含有不成立的分支。

Required action：

- 將 C 改為明確的七年 Object Lock Compliance-mode retention。
- Legal hold 只能寫成額外、無固定期限的保留控制，不能以 `or` 取代 compliance retention。
- Explanation 必須說明 Governance mode、Compliance mode、legal hold 的移除權限差異。
- 官方依據：[S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)。

### `ch042-q08` — 漏掉 10 KB Lifecycle transition 的現行預設行為

題目使用大量 10 KB objects，並假設第二天以 Lifecycle 轉入 IA/Glacier。對 2024 年 9 月之後建立或修改的 Lifecycle configuration，S3 預設不轉移小於 128 KB 的 objects；只有明確使用 object-size filter 才能改變此行為。

目前 A/E 的成本原則合理，但題目漏掉這個直接決定「transition 會不會發生」的前置條件。

Required action：

- 在 prompt 明確說明團隊是否設定 `ObjectSizeGreaterThan`／`ObjectSizeLessThan`。
- 若未設定，正解必須指出 10 KB objects 預設不會被 Lifecycle transition。
- 若明確允許小物件轉層，再比較 minimum billable size、minimum duration、request、metadata 與 retrieval cost。
- 保持恰好兩個正解。
- 官方依據：[S3 Lifecycle transition constraints](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html)。

### `ch044-q08`、`ch044-q09` — Snowball Edge 的 2026 可用性必須進入答案解析與來源

兩題已用「既有且仍符合 ordering 資格的客戶」限制 scenario，因此目前 answer set 仍可成立；但在 2026 年，Snowball Edge 不再提供給新客戶。只把條件藏在 prompt，解析卻仍以一般現行服務口吻描述，容易讓初學者形成錯誤的採購結論。

Required action：

- 在兩題 explanation 明確註明：Snowball Edge 自 2025-12-15 起停止新客戶使用；此答案只適用於仍具資格的既有客戶。
- 增加現行 Snowball Edge availability 官方來源。
- 至少一個 distractor explanation 說明新客戶需重新評估線上遷移、DataSync、Direct Connect 或 AWS 認可 partner，而不是假設可新訂裝置。
- 不需改變 `ch044-q08` 的 C/E 或 `ch044-q09` 的 B/D answer set。
- 官方依據：[AWS Snowball Edge availability](https://docs.aws.amazon.com/snowball/latest/developer-guide/whatisedge.html)。

### `ch045-q01` — Inspiration metadata 類型錯置

題目本身的答案 A 正確，傳統 RDS Multi-AZ DB instance 的 standby 不提供 application read scaling，read replica 才承接可容忍 lag 的 reporting traffic。

Required action：

- 題目內容可保留。
- 移除 `inspiration_ids` 中的 `aws-sap-sample`，或在全域 contract 先增加獨立的 official style-calibration 欄位。

### `ch046-q04` — 演練觀察值不能變成非同步複寫的硬性 RPO 保證

Aurora Global Database 的跨 Region replication 是非同步。D 選項要求監控 lag 並以演練看到資料缺口不超過五秒；這能驗證 observed behavior，不能保證未來每次災難都具有「最多五秒」的硬上限。

Required action：

- 明確區分：
  - 若五秒是 architecture objective：可用 Global Database、監控 replication lag、設 alarm、演練 failover，並承認事件當下可能超標。
  - 若五秒是不可違反的 hard guarantee：不能只靠 Aurora Global Database 的非同步 secondary 宣稱達成。
- 改寫 prompt，避免「一次演練通過」被視為永久保證。
- Explanation 應說明 planned switchover 與 unplanned failover 的資料損失風險不同。
- 官方依據：[Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html) 與 [switchover/failover](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)。

### `ch046-q10` — 與 `ch045-q10` 實質重複，且未完成 DSQL／Global Database 邊界

`ch045-q10` 與 `ch046-q10` 都以 A/B workload 比較 RDS engine compatibility、Aurora readers/global capabilities、self-managed OS control，連錯誤選項「Aurora 支援 Oracle」及 SQL/extension/TCO 說明都高度重疊。這不符合跨題不重複要求。

Required action：

- 保留 `ch045-q10`，完整重寫 `ch046-q10`。
- 新題應直接區分：
  - RDS for Oracle：保留 managed Oracle engine/edition features。
  - Aurora Global Database：單一 primary writer、跨 Region 非同步 storage replication、secondary reads/DR；write forwarding 仍回 primary commit。
  - Aurora DSQL：serverless、active-active multi-Region endpoints、strong consistency，使用 witness Region，且有 PostgreSQL compatibility、Region set 與 feature limits。
- DSQL 未列在 SAP-C02 service scope 中；若作為 2026 架構補充，`level` 或 explanation 必須明確標為 enrichment，不可冒充 SAP-C02 必考服務。
- 官方依據：
  - [Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)
  - [Aurora DSQL concepts](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with.html)
  - [Aurora DSQL multi-Region active-active](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html)

### `ch047-q09` — MRSC 的核心限制被縮成「自行驗證」

正解 A/E 方向正確，但 E 與 explanation 只寫「驗證 topology、feature limits、latency」，沒有教會讀者 MRSC 與 MREC 的真正差異。對本章最時效敏感的知識點，這個答案密度不足。

Required action：

- MREC explanation 明確寫出非同步 replication、跨 Region concurrent update 的 last-writer-wins/conflict implication。
- MRSC explanation 至少包含：
  - 固定三 Region topology：兩個 replica Regions 加一個 witness Region；
  - strongly consistent multi-Region reads/writes 與 RPO 0；
  - quorum/coordinator distance 帶來的 write latency；
  - 不支援 DynamoDB transactions、TTL 與 LSI；
  - 建立後不能任意加入或移除 Region。
- 重新檢查 payment scenario 是否依賴 transactions 或 TTL；若依賴，MRSC 不可仍列為可行答案。
- 官方依據：
  - [DynamoDB global table consistency modes](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/V2globaltables_HowItWorks.html)
  - [Global tables](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html)

### `ch048-q10` — 與 `ch047-q10` 重複 DAX 選項與解析

`ch047-q10` 已完整測 DAX 的 DynamoDB-only cache scope；`ch048-q10` 再次使用近乎相同的「DAX 是 DynamoDB 專用 accelerator，不是 SQL/OpenSearch general cache」選項與 explanation。

Required action：

- 保留 intent 10 的服務邊界，但改用不同決策訊號，例如：
  - HTTP edge cache 的 cache key/TTL/origin contract；
  - ElastiCache 的 application-managed data structures；
  - MemoryDB 作 durable Valkey-compatible primary database；
  - DAX 的 DynamoDB SDK compatibility 與 eventual/strong read path。
- 不可再次使用「欄位名稱像 partition key 就能 cache SQL/OpenSearch」的同一笑話式 distractor。

### `ch050-q10` — 混淆 Firehose processing-failed records、source backup 與 destination retry

現題的 S3 destination、Lambda transform failure、destination unavailable 被合併成同一個「error prefix」結果。Firehose 的行為必須分開說：

- Lambda transformation failure 可依 processing-failed error prefix 保留失敗 records。
- Source-record backup 是可配置的另一條 S3 backup contract，且設定方式受 destination 類型影響。
- S3 destination delivery 失敗會依服務 retention/retry 行為重試；不能籠統承諾所有 destination failures 都落入同一 error prefix。

目前 E 的「transformation 或 delivery failed data 都由 S3 backup/error output 保留」過度概括。

Required action：

- 改寫 prompt，指定 primary destination、backup bucket 與要處理的 failure type。
- D 保留 buffering/transformation 責任。
- E 拆清 processing-failed prefix、source data backup 與 S3 delivery retry/retention；保持恰好兩個正解。
- Explanation 必須指出 Firehose 不是 arbitrary-offset replay log，若要求重新任意消費原始 stream，應保留 Kinesis/MSK 或另一 durable source。
- 官方依據：
  - [Firehose data transformation failure handling](https://docs.aws.amazon.com/firehose/latest/dev/data-transformation-failure-handling.html)
  - [Firehose source data backup](https://docs.aws.amazon.com/firehose/latest/dev/create-configure-backup.html)
  - [Firehose error handling](https://docs.aws.amazon.com/firehose/latest/dev/handle-failures.html)

### `ch051-q09` — Current availability 被誤標成 SAA/SAP scored knowledge

題目對現況的敘述正確：Timestream for LiveAnalytics 自 2025-06-20 起不接受新客戶；既有客戶仍可管理既有 workload。問題在 scope：答案 D 讓服務 onboarding status 成為 SAA/SAP 正解之一，並映射正式 task keys，但這不是 SAP-C02 架構知識的穩定考點。

Required action：

- 將 scored question 改回 time-series 核心能力：dimensions、time、measures、memory/magnetic retention、late-arriving data 與 query pattern。
- 把「2025-06-20 起停止新客戶」留在 dated enrichment note 或 explanation，不要作為 SAA/SAP 正解判定條件。
- 若作者堅持保留 current-availability 題，`level` 必須明確標為 2026 enrichment，且不可冒充正式 SAA/SAP task coverage。
- 官方依據：[Timestream for LiveAnalytics current availability](https://docs.aws.amazon.com/timestream/latest/developerguide/what-is-timestream.html)。

## 逐章、逐題 disposition

以下列出全部 110 題的審查結果；未列為 REVISE 的題目，其 answer set、intent、來源與解析在本次審查中可接受。

| Chapter | PASS | REVISE |
|---|---|---|
| 41 | `ch041-q02`, `ch041-q04`–`ch041-q09` | `ch041-q01`, `ch041-q03`, `ch041-q10` |
| 42 | `ch042-q01`–`ch042-q07`, `ch042-q09`–`ch042-q10` | `ch042-q08` |
| 43 | `ch043-q01`–`ch043-q10` | — |
| 44 | `ch044-q01`–`ch044-q07`, `ch044-q10` | `ch044-q08`, `ch044-q09` |
| 45 | `ch045-q02`–`ch045-q10` | `ch045-q01` |
| 46 | `ch046-q01`–`ch046-q03`, `ch046-q05`–`ch046-q09` | `ch046-q04`, `ch046-q10` |
| 47 | `ch047-q01`–`ch047-q08`, `ch047-q10` | `ch047-q09` |
| 48 | `ch048-q01`–`ch048-q09` | `ch048-q10` |
| 49 | `ch049-q01`–`ch049-q10` | — |
| 50 | `ch050-q01`–`ch050-q09` | `ch050-q10` |
| 51 | `ch051-q01`–`ch051-q08`, `ch051-q10` | `ch051-q09` |

## 關鍵已通過項目的確認

- `ch042-q09`：S3 Express One Zone 使用同 AZ directory bucket、只放可重建資料，且要求驗證 directory-bucket API/endpoint 差異；正解 B/D 唯一且符合現行服務語意。
- `ch043-q04`：EBS Multi-Attach 正確限制在支援的 io1/io2 與 Nitro instance、同 AZ，且沒有替應用提供 cluster filesystem、locking 或 fencing。
- `ch045-q02`：RDS Multi-AZ DB cluster 的一 writer、兩 readable instances 與傳統 Multi-AZ DB instance 的不可讀 standby 已正確分離。
- `ch045-q06`：RDS Proxy session pinning 與大於 16 KB statement 的限制方向正確。
- `ch046-q05`：Aurora Global Database planned switchover 與 unplanned failover 的責任邊界正確。
- `ch046-q06`：Global write forwarding 保留 primary writer ownership，不是 secondary local commit 或 multi-primary conflict merge。
- `ch047-q06`：6 KB strongly consistent read 為 2 RCUs；6 KB transactional write 為 12 WCUs，計算正確。
- `ch047-q07`：conditional transaction 與 idempotency 分工正確。
- `ch047-q10`：DAX 對 strongly consistent reads 採 pass-through 且不 cache，正解 B/D 正確。
- `ch049-q05`：Lake Formation grants 不會自動覆寫 broad direct S3 access；IAM、S3、KMS 與 registered location 必須共同治理。
- `ch050-q04`：Enhanced fan-out 與 shared read throughput 的差異正確。
- `ch051-q05`：DocumentDB compatibility 不等於 MongoDB feature identity，要求逐項驗證的答案正確。
- `ch051-q08`：Neptune live replicas、PITR 與 Global Database 的責任已正確分離。

## Revision acceptance gate

Revision agent 完成後，R04 建議至少重新執行以下檢查：

1. 13 個 REVISE IDs 的 answer set 是否仍唯一。
2. `ch041-q01`、`ch041-q03` 與舊 fallback 是否已失去相同 scenario/choice structure。
3. `ch045-q10` 與新版 `ch046-q10` 是否不再測同一組 RDS/Aurora 選型。
4. `ch047-q10` 與新版 `ch048-q10` 是否不再複用相同 DAX distractor。
5. `ch042-q08` 是否明確處理小於 128 KB 的 Lifecycle default。
6. `ch047-q09` 是否明確列出 MRSC topology 與 unsupported features。
7. `ch050-q10` 是否分開 transformation failure、source backup 與 destination retry。
8. DSQL、Snowball Edge、Timestream 的時效性內容是否標為 2026 enrichment/current availability，而不是未經說明的 SAP-C02 scored fact。
9. 每章仍維持 10 題、intent 1–10、至少 7 單選與 2 複選，且任一答案位置不超過 4 次。

REVISE

## Verification

重新驗證日期：2026-10-01。此次只讀取修訂後的 `part_04.json`，未修改題庫。

- `ch041-q01`：已修正。Scenario 已改為 SQLite、mmap 與 random in-place writes，和舊 fallback 的 append／lock／directory rename 解題訊號不再重疊；official sample 也已從 `inspiration_ids` 移除。
- `ch041-q03`：已修正。題目改為 direct cross-account grant 與 AssumeRole 的信任邊界，並加入 SSE-KMS 雙重授權；不再重用舊題的 `AnalyticsReader`、`raw/` prefix 與 ListBucket/GetObject ARN 配對。
- `ch041-q10`：已修正。正解明確要求七年 Compliance-mode retention；解析正確區分 Governance bypass、Compliance retain-until date，以及可由具權限 principal 移除且無固定到期日的 legal hold。
- `ch042-q08`：已修正。Prompt 明確指定 2026 年新增、未設定 object-size filter 的 Lifecycle rule；A 正確指出現行預設不 transition 小於 128 KB 的 objects，E 再處理顯式允許小物件後的完整 TCO。
- `ch044-q08`、`ch044-q09`：尚未完全修正。兩題已正確限制為仍有資格的既有客戶，也正確指出 2025-11-07 後不再接受新客戶；此日期符合 AWS Snowball Edge 文件歷史。然而 `ch044-q08` C 的「既有客戶也只有公告的有限續訂期間」及 `ch044-q09` B 的「仍在有限訂購期間內」沒有現行官方文件支持。AWS 現行 availability-change 文件寫的是變更不影響目前使用 Snowball Edge 的客戶，並未宣告這種通用有限續訂窗口。請刪除兩處「有限期間」說法，改成「仍具 AWS 帳戶資格並可成功下單的既有客戶」，並在 `source_ids` 加入 `snowball-edge-availability-change.html` 或官方 Document History 來源。
- `ch045-q01`：已修正。題目與答案維持正確，`inspiration_ids` 現在只含 community source，不再混入 official sample。
- `ch046-q04`：已修正。Prompt 已將五秒定義為 architecture objective 而非同步硬保證；D 與解析明確說明 asynchronous replication、observed lag、planned switchover 與 unplanned failover 的不同。
- `ch046-q10`：已修正。與 `ch045-q10` 的 prompt／choice 相似度已顯著降低；新題正確分離 RDS for Oracle、單一 primary writer 的 Aurora Global Database，以及 active-active、strongly consistent 的 Aurora DSQL。DSQL 也已標為 `SAP + 2026 enrichment`，並說明兩 Region 配置的 witness Region 與相容性限制。
- `ch047-q09`：已修正。MREC 已明述 asynchronous replication 與 last-writer-wins；MRSC 已涵蓋三 Region topology、兩 replicas 加 witness 或三 replicas、RPO 0、quorum write latency、transactions／TTL／LSI 不支援，以及不能任意增減 Region。Prompt 也明確排除 payment table 對這三項不支援功能的依賴。
- `ch048-q10`：已修正。題目已改為 CloudFront HTTP cache contract、ElastiCache 可重建 state 與 MemoryDB durable primary state 的邊界；不再重複 `ch047-q10` 的 DAX strongly-consistent-read 題型或原 distractor。
- `ch050-q10`：已修正。D/E 現在分別處理 buffering/transformation，以及 source-record backup、Lambda processing-failed prefix、Direct PUT 到 S3 的 retry/24-hour retention；沒有再把所有 delivery failure 說成同一 error prefix。
- `ch051-q09`：核心題型已修正，但 provenance 尚需補一項。Scored answer 已改為 dimensions/time/measures、memory/magnetic retention 與 late-arriving writes；2025-06-20 新客戶限制只留在 explanation，不再決定 SAA/SAP 正解。請再把專門的官方來源 `https://docs.aws.amazon.com/timestream/latest/developerguide/AmazonTimestreamForLiveAnalytics-availability-change.html` 加入 `source_ids`；目前引用的 overview page 不包含該生效日。
- 結構回歸：Part 04 仍為 11 章 × 10 題、每章 intents 1–10、每章 7 single + 3 multi；任一答案位置每章最多 4 次。原 `ch045-q10`／`ch046-q10` 與 `ch047-q10`／`ch048-q10` 的跨題重複已消除。

仍需修訂的精確動作：

1. `ch044-q08`：移除「既有客戶只有有限續訂期間」；加入 Snowball Edge availability-change／Document History 官方來源。
2. `ch044-q09`：移除「仍在有限訂購期間內」；改為以帳戶實際 eligibility 為條件並加入同一官方來源。
3. `ch051-q09`：保留目前題目與 answer set，只補上 Timestream for LiveAnalytics availability-change 官方 source ID。

REVISE

## Final Verification

- `ch044-q08`：通過。已移除無官方依據的有限續訂／訂購期間敘述；prompt 與 explanation 均改以既有 AWS 帳戶仍具 Snowball Edge eligibility、且可成功建立 device order 為前提。`source_ids` 已包含官方 `snowball-edge-availability-change` deep link。
- `ch044-q09`：通過。已移除有限訂購期間敘述，Snowball Edge 方案只在既有客戶 eligibility 成立且 device order 可成功建立時適用；`source_ids` 已包含相同的官方 availability-change source。
- `ch051-q09`：通過。`source_ids` 已加入 `timestream-availability-change`，URL 恰為 `https://docs.aws.amazon.com/timestream/latest/developerguide/AmazonTimestreamForLiveAnalytics-availability-change.html`。
- 最終結果：上一輪剩餘三項均已完成，題庫未在本輪修改。

VERIFIED
