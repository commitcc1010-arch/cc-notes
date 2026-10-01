# AWS 題庫獨立審查：Part 11（第 105–116 章）

- 審查日期：2026-10-01
- 題庫：`tools/aws_question_banks/part_11.json`
- 範圍：120 題；managed service、非同步解耦、HA/SPOF、cell、queue、cache、control/data plane、安全、observability、DR、成本與 migration
- 題庫作者：`P11-A`
- 審查者：獨立審查；未修改題庫
- 考試基準：官方 SAA-C03、SAP-C02 exam guide 與官方 sample questions；未假設或引用未發布的 SAP-C03 guide
- 來源原則：AWS 官方文件決定服務行為；Jayendra Patil 只作主題靈感，不作事實依據；未使用 dumps、回憶真題或 ExamTopics 類來源

## 結論

本 part 的核心架構方向多半正確，尤其是 RTO/RPO、queue overload、cell isolation、static stability、成本單位化與 migration wave 的觀念。不過目前不能出版，必須標記為 `REVISE`，原因不是少數文字瑕疵，而是四個系統性 blocker：

1. `python3 tools/check_aws_question_banks.py --part 11` 直接失敗，共 99 項 `option explanation is too thin` 或 `prompt/tested label is too thin`。
2. 96 題單選中有 93 題的正解是唯一最長選項。只有 `ch105-q01`、`ch107-q02`、`ch116-q05` 例外。
3. 24 題複選的正解組合只有 `AD` 12 題、`BE` 11 題、`BD` 1 題；每章固定第 9 題為 `AD`、第 10 題幾乎固定為 `BE`。這是可直接利用的作答線索。
4. 大量干擾項是「只看名稱長度」「所有工程師共用 admin」「把 RDS 當 container runtime」「DNS 自動提升 database writer」等明顯荒謬選項，不符合官方 sample question 常見的「技術上可行，但違反某一 hard constraint」風格。

因此，即使個別題目的正解方向通過，仍須完成全域重排與干擾項重寫，才能解除出版阻擋。

## 官方考綱與版本基準

- SAA 以 **SAA-C03** 為準：
  <https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html>
- SAP 以 **SAP-C02** 為準：
  <https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html>
- 官方 SAA sample：
  <https://d1.awsstatic.com/training-and-certification/docs-sa-assoc/AWS-Certified-Solutions-Architect-Associate_Sample-Questions.pdf>
- 官方 SAP sample：
  <https://d1.awsstatic.com/training-and-certification/docs-sa-pro/AWS-Certified-Solutions-Architect-Professional_Sample-Questions.pdf>

截至審查日，AWS 官方仍未發布 SAP-C03 exam guide。本 part 使用 `SAA`／`SAP` level，沒有虛構 SAP-C03 標籤，這一點通過。

## 全域修訂要求

### G1：消除答案長度與位置線索

適用 `ch105-q01` 至 `ch116-q10` 全部 120 題。

- 重新排列選項，讓每章單選答案位置不形成規律。
- 不可只把正解縮短；應把干擾項寫成完整、可信的相鄰方案。
- 每個複選章節至少使用多種答案組合，不得維持固定 `AD`／`BE` 模板。
- 重排後同步修正 `answers` 與逐項解析。

### G2：修正自動品質 gate

下列題目至少有一段選項解析少於目前 validator 的最低要求：

- `ch105-q07`, `ch105-q10`
- `ch106-q03`
- `ch107-q02`, `ch107-q07`, `ch107-q09`
- `ch108-q01`–`ch108-q10`
- `ch109-q01`–`ch109-q10`
- `ch110-q02`–`ch110-q05`, `ch110-q07`–`ch110-q10`
- `ch111-q01`–`ch111-q07`, `ch111-q09`, `ch111-q10`
- `ch112-q01`–`ch112-q10`
- `ch113-q01`–`ch113-q10`
- `ch114-q01`–`ch114-q10`
- `ch115-q01`–`ch115-q10`
- `ch116-q01`–`ch116-q10`

另有下列 `tested`／prompt label 過薄：

- `ch114-q07`, `ch114-q10`
- `ch115-q06`, `ch115-q09`, `ch115-q10`
- `ch116-q09`, `ch116-q10`

修法不是填充固定句，而是讓每個錯誤選項說清楚「在什麼條件下它可能合理」以及「本題哪一個限制使它失效」。

### G3：降低跨題重複

至少重寫每組中的一題，使其測量不同能力：

| 重複群組 | 重複內容 | 建議保留的差異 |
|---|---|---|
| `ch105-q03`, `ch105-q10` | managed database escape hatch | 一題測 adoption decision；另一題測實際 exit drill 與 data reconciliation |
| `ch105-q04`, `ch105-q10` | RDS HA、backup、KMS、network、restore | `q04` 保留 SAA configuration；`q10` 改為 SAP exit trigger/cutover evidence |
| `ch106-q02`, `ch106-q05`, `ch106-q10`, `ch109-q05` | visibility、delete-after-commit、idempotency、DLQ | 分別測 competing consumer、external side effect、operating evidence、長任務 heartbeat |
| `ch106-q06`, `ch113-q06`, `ch113-q10` | 沿 queue/data path 找 broken handoff | 一題測 queue metrics；一題測 trace propagation；一題測 business freshness SLO |
| `ch107-q01`, `ch107-q06`, `ch107-q09` | critical path、共同依賴與 game-day evidence | 分成設計 inventory、事故診斷、驗證方法 |
| `ch107-q07`, `ch114-q02`, `ch114-q07`, `ch114-q08` | 依 RTO/RPO 選最低成本 DR | 避免兩題都是「寬鬆目標選 backup/restore」 |
| `ch108-q01`, `ch108-q03`, `ch108-q10` | cell mapping、state/capacity isolation | 加入 resharding、tenant move、cell evacuation 或 global-state exception |
| `ch110-q04`, `ch110-q10` | permission cache freshness/revocation | 留一題安全設計；另一題改測 outage 時 fail-open/fail-closed 決策 |
| `ch111-q02`, `ch111-q04`, `ch111-q06`, `ch111-q08`, `ch111-q10` | local cache、last-known-safe、AppConfig rollback | 加入 cold start、backup preload、poll interval、deployment monitor 與 configuration version 的不同故障 |
| `ch112-q01`, `ch112-q08` | identity/network/data 三層安全 | 一題保留觀念；另一題改為實際 cross-account policy evaluation |
| `ch113-q01`, `ch113-q08` | business SLO 加 logs/traces | 一題測 SLI 定義；一題測 alarm/runbook/evidence |
| `ch114-q03`, `ch114-q10` | restore test 才能證明 RTO/RPO | 一題測 AWS Backup 設定；一題測 drill evidence 與 data-loss measurement |
| `ch116-q03`, `ch116-q09`, `ch116-q10` | migration wave、rollback、handoff | 分別測 wave grouping、factory feedback、completion/decommission gate |

## Source 與 deep-link 審查

### 可達性

89 個 source URL 經 redirect 後都回傳 HTTP 200，未發現 dead link。社群來源均只出現在 `inspiration_ids`，未冒充官方來源。

### 必須補強的精確官方來源

| 題號 | 問題 | 建議官方 deep link |
|---|---|---|
| `ch105-q05`, `ch116-q08` | heterogeneous schema conversion 只引用 DMS overview，未區分 schema 與 data migration | <https://docs.aws.amazon.com/dms/latest/userguide/schema-conversion.html> |
| `ch105-q09` | 選項明確使用 AWS Config，來源卻沒有 Config aggregation/compliance 文件 | 加入 AWS Config aggregator 或 conformance-pack 精確頁 |
| `ch106-q09` | 宣稱 replay 與 cross-account policy，來源只有 event pattern/retry 與 generic IAM | 加入 EventBridge archive/replay、event-bus resource policy 精確頁 |
| `ch108-q05`, `ch109-q09` | 使用 multi-tenant fairness/fair queue，但沒有 SQS Fair Queues 文件 | <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-fair-queues.html> |
| `ch111-q02`, `ch111-q04`, `ch111-q06`, `ch111-q08`, `ch111-q10` | `last-known-safe`／cold-start backup 行為未由目前 Agent overview 精確支撐 | <https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-agent-how-to-use.html>；若聲稱 disk backup/preload，另加對應 `BACKUP_DIRECTORY`／`PRELOAD_BACKUP` 文件 |
| `ch112-q04`, `ch112-q10` | cross-account SSE-KMS 權限只引用 generic concepts | 加入 KMS cross-account key policy 與 S3 SSE-KMS cross-account access 文件 |
| `ch112-q05`, `ch112-q10` | row/column filter 應直接連到 Lake Formation data filters | 加入 Lake Formation data filter 精確頁 |
| `ch113-q04`, `ch113-q08` | 題目使用 CloudWatch RUM，但 source 沒有 RUM 文件 | <https://docs.aws.amazon.com/xray/latest/devguide/xray-services-RUM.html> 或 CloudWatch RUM user guide |
| `ch113-q05` | 跨 SQS trace propagation 只引用 X-Ray overview | <https://docs.aws.amazon.com/xray/latest/devguide/xray-services-sqs.html> |
| `ch115-q02` | 成本標籤歷史行為已支援最多 12 個月 backfill | <https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-allocation-backfill.html> |
| `ch115-q03` | 只引用 legacy CUR overview，未精確支撐 CUR 2.0/Data Exports | <https://docs.aws.amazon.com/cur/latest/userguide/dataexports-processing.html> |
| `ch115-q04` | Compute Optimizer 的 RDS CPU/memory/network/EBS 建議需精確來源 | <https://docs.aws.amazon.com/compute-optimizer/latest/ug/view-rds-recommendations> |
| `ch115-q05` | 題目指定 S3 gateway endpoint，來源只到 generic endpoint concepts | 加入 S3 gateway endpoint 與 route-table 精確頁 |
| `ch116-q06` | MGN cutover 診斷應引用 MGN replication/cutover 文件，不應以 DMS CDC 混合支撐 | 加入 MGN replication status、launch/cutover 精確頁 |

`mgn`、`migrationhub-change`、`vpc-endpoints`、`builders-shuffle`、`cell-guide` 目前都會 redirect。Redirect 本身不構成錯誤，但出版前宜改成 redirect 後的 canonical URL，避免未來失效。

## 逐題審查

表中「內容通過」只代表 AWS 事實、唯一性與主要 task mapping 沒有額外 blocker；所有題目仍受 G1，列在 G2 的題目也仍須補足解析。

### 第 105 章

| ID | 結果 | 精確修訂要求 |
|---|---|---|
| `ch105-q01` | 內容通過 | RDS shared-responsibility 方向正確；可補 RDS shared-responsibility 精確來源。 |
| `ch105-q02` | REVISE | `SAA-3.3` 是 database solution，不精確對應 Kafka ingestion/streaming；改成 `SAA-3.5`，保留 `SAA-2.1`。 |
| `ch105-q03` | REVISE | 與 `ch105-q10` 重複。保留 adoption 前的 exit criteria；不要再重複目前 HA checklist。 |
| `ch105-q04` | 內容通過 | Multi-AZ、PITR、CMK、private subnets 與 SG contract 正確。 |
| `ch105-q05` | REVISE | Heterogeneous schema change 不可只寫「assessment + DMS full load/CDC」；加入 DMS Schema Conversion/AWS SCT、unsupported-object remediation 與 conversion validation。 |
| `ch105-q06` | 內容通過 | `available` 不代表 connection/lock/I/O/retry 健康，診斷順序合理。 |
| `ch105-q07` | REVISE | TCO 正解合理，但逐項解析未達 gate；把三個錯誤選項改成有條件成立的 managed/self-managed trade-off。 |
| `ch105-q08` | 內容通過 | 不需 host/GPU/privileged access 的不規則 OCI workload 選 ECS on Fargate 合理。 |
| `ch105-q09` | REVISE | AWS Config/Organizations claim 缺精確官方來源；補 aggregator/delegated governance 文件。 |
| `ch105-q10` | REVISE | 與 `q03`、`q04` 大幅重複且解析過薄；改成實際 exit drill、dual-write/cutover 或 engine compatibility failure。 |

### 第 106 章

| ID | 結果 | 精確修訂要求 |
|---|---|---|
| `ch106-q01` | 內容通過 | Success 應在 object 與 durable work record 都持久化後才回覆，方向正確。 |
| `ch106-q02` | 內容通過 | Competing consumers、visibility、delete-after-commit、idempotency、DLQ 正確。 |
| `ch106-q03` | REVISE | 架構正確，但解析過薄；說清楚 EventBridge target delivery retry/DLQ 與 consumer queue DLQ 是兩個不同 failure boundary。 |
| `ch106-q04` | REVISE | `SAP-2.1` 是 deployment strategy，非 workflow reliability；改為 `SAP-2.4`，並保留 `SAA-2.1`。 |
| `ch106-q05` | 內容通過 | FIFO 也不能讓任意外部付款 side effect 變 exactly once，解析正確。 |
| `ch106-q06` | 內容通過 | Producer success 只證明 queue acceptance；逐跳排查合理。 |
| `ch106-q07` | 內容通過 | Long polling、合理 batching 與 partial-failure boundary 正確。 |
| `ch106-q08` | REVISE | 三個獨立 queue 仍需要明確 fan-out；正解應寫 S3→EventBridge/SNS→三個 queue，否則看不出每個 queue 如何收到同一上傳事件。 |
| `ch106-q09` | REVISE | Replay、redrive 與 cross-account resource policy 缺精確來源；明確區分 EventBridge archive/replay、target DLQ redrive 與 SQS replay。 |
| `ch106-q10` | 內容通過 | Crash safety、idempotent commit 與 end-to-end evidence 正確，但應與其他 queue 題拉開。 |

### 第 107 章

| ID | 結果 | 精確修訂要求 |
|---|---|---|
| `ch107-q01` | 內容通過 | SPOF inventory 包含 runtime、identity、egress、control 與人員 dependency，正確。 |
| `ch107-q02` | REVISE | 12 台的計算正確；補足錯誤選項解析並加入 ASG desired/min/max 或 zonal capacity 前提。 |
| `ch107-q03` | 內容通過 | Traditional Multi-AZ、Multi-AZ DB cluster/readable standby 與 read replica 的責任已適當區分。 |
| `ch107-q04` | 內容通過 | Per-AZ NAT 與同 AZ route、S3/DynamoDB gateway endpoint 的方向正確。 |
| `ch107-q05` | 內容通過 | Static stability 與 last-known-good data plane 正確。 |
| `ch107-q06` | 內容通過 | 應追 state、identity、egress、quota 與 client reconnect，而非只看 ALB，正確。 |
| `ch107-q07` | REVISE | DR/TCO 判斷正確但解析過薄，且與第 114 章重複；改成具體成本數據或 failure-impact 計算題。 |
| `ch107-q08` | 內容通過 | Multi-AZ stateless web + external session + Multi-AZ DB 是合理答案。 |
| `ch107-q09` | REVISE | Game-day evidence 正確但解析過薄；補 stop condition、steady-state hypothesis、blast-radius guardrail。 |
| `ch107-q10` | 內容通過 | Database 與 key/approval path 都是獨立 SPOF；正解合理。 |

### 第 108 章

| ID | 結果 | 精確修訂要求 |
|---|---|---|
| `ch108-q01` | REVISE | 內容合理但全題解析過薄；加入 12,000/200 對應至少 60 個 cell 的容量、skew 與 headroom 討論。 |
| `ch108-q02` | REVISE | 「健康轉送」可能暗示把 tenant 任意切到另一個沒有其 state 的 cell；改成 router 只選定該 tenant 所屬 cell 的健康 endpoint，cell relocation 必須有獨立 state-move protocol。 |
| `ch108-q03` | REVISE | 內容正確但解析過薄；說明 shared database 何時可接受，例如有 per-cell partition/quota 且不在同步共同故障路徑。 |
| `ch108-q04` | REVISE | 只映射 `SAP-1.4` 不足；題目核心是 fault isolation，加入 `SAP-1.3` 或 `SAP-2.4`。 |
| `ch108-q05` | REVISE | 正解合理；若使用 SQS Fair Queues，必須明說 standard queue 的 `MessageGroupId` 是 tenant identifier，且 fair queue 不等同 hard per-tenant rate limit。 |
| `ch108-q06` | REVISE | 內容正確但解析過薄；加入 global router/config/identity 的 correlation 與 deployment scope evidence。 |
| `ch108-q07` | REVISE | 內容正確但解析過薄；加入 fixed overhead、minimum viable cell、tenant skew 與 evacuation capacity。 |
| `ch108-q08` | REVISE | 內容正確但解析過薄；說明 dedicated cell 不必等於 dedicated account，並定義資料搬移與 routing cutover。 |
| `ch108-q09` | REVISE | 內容正確但解析過薄；補 template version、backward compatibility、canary admission 與 rollback window。 |
| `ch108-q10` | REVISE | 與 `q01/q03/q05` 重複；改測 cell evacuation、resharding 或 global service exception。 |

### 第 109 章

| ID | 結果 | 精確修訂要求 |
|---|---|---|
| `ch109-q01` | REVISE | 流量守恆正確；補淨增長 2,000 件/秒與 retention 耗盡時間/容量的推理，而非只寫「backlog 增加」。 |
| `ch109-q02` | REVISE | 訊號選擇正確；干擾項「queue 名稱長度」不具考試品質，改成 depth-only、receive-rate-only 等可信但不足的方案。 |
| `ch109-q03` | REVISE | 60 件/worker 計算正確；補公式 `acceptable latency / average processing time`、p95 偏差與 in-flight 處理。 |
| `ch109-q04` | REVISE | Stale-work shedding 正確；說明 expiry 由 application/message attribute 實作，SQS 不會自動理解業務 deadline。 |
| `ch109-q05` | REVISE | ChangeMessageVisibility 方向正確；說清楚它是 per-message extension，不是 SQS 自動 heartbeat，且仍可能 duplicate。 |
| `ch109-q06` | REVISE | Downstream bottleneck 結論正確；加入 database connection/transaction budget 與受控 concurrency。 |
| `ch109-q07` | REVISE | 組合正確但解析過薄；batch partial failure 必須具體到使用的 consumer integration。 |
| `ch109-q08` | REVISE | Queue 吸收短 burst 正確；加入 3 分鐘 drain-rate/capacity estimate，避免只考口號。 |
| `ch109-q09` | REVISE | 加入 SQS Fair Queues 精確來源；明確說 fair queue 降低 quiet tenant dwell time，但不提供 hard rate cap，必要時仍需 admission/concurrency quota。 |
| `ch109-q10` | REVISE | 與 `q01/q04/q08` 重複；改成量化 sustained overload 的 admission threshold 或 graceful degradation policy。 |

### 第 110 章

| ID | 結果 | 精確修訂要求 |
|---|---|---|
| `ch110-q01` | 內容通過 | Cache 不應是未定義持久性的唯一 authoritative inventory，方向正確。 |
| `ch110-q02` | REVISE | Cache-aside 流程正確但解析過薄；補 negative caching、stampede 與 source failure 的限制。 |
| `ch110-q03` | REVISE | `commit-after-invalidate` 用語錯誤/含糊，可能仍表示先 invalidate 再 commit，重現題幹 race。改成「先提交 authoritative write，再 invalidate/update cache」，並處理 invalidation failure、versioning 或 outbox。 |
| `ch110-q04` | REVISE | 正解合理但解析過薄；與 `q10` 重複，保留其中一題。 |
| `ch110-q05` | REVISE | Stampede controls 正確；說清楚 stale-while-revalidate 只適用可容忍 stale 的資料，不能泛用於 authorization/inventory。 |
| `ch110-q06` | 內容通過 | Key cardinality、TTL、eviction、endpoint 與 deploy 時序是合理診斷。 |
| `ch110-q07` | REVISE | 移除 `SAA-4.3`；CloudFront cache-key/transfer 是 network/CDN cost，`SAA-4.4` 足夠。 |
| `ch110-q08` | REVISE | 配對正確但解析過薄；補 DAX 只快取 eventually consistent reads，strongly consistent reads 會 bypass cache。 |
| `ch110-q09` | REVISE | Versioned keys/canary/warm-up 正確；解析需說明 namespace doubling 的短期 memory cost。 |
| `ch110-q10` | REVISE | 與 `q04` 幾乎相同；改測 revocation event 遺失、cache partition 或 stale-version comparison。 |

### 第 111 章

| ID | 結果 | 精確修訂要求 |
|---|---|---|
| `ch111-q01` | REVISE | Control/data plane 分類正確，但解析過薄；不要暗示所有 runtime local read 都由 AWS 保證可用。 |
| `ch111-q02` | REVISE | AppConfig Agent local endpoint 正確；`startup default/last-known-safe` 必須說明是 application policy或經 `BACKUP_DIRECTORY/PRELOAD_BACKUP` 配置，不是未設定時的無條件服務保證。 |
| `ch111-q03` | REVISE | Validator、gradual deployment、bake time、alarm rollback 正確；補 alarm 狀態與 deployment monitor 的精確文件。 |
| `ch111-q04` | REVISE | 風險分級正確；若 kill switch 要 30 分鐘內失效，需明確說 poll/cache interval、版本與 endpoint outage 時的 fail-safe。 |
| `ch111-q05` | REVISE | 移除 `SAA-1.2`；本題核心是 resilience/operations，改用 `SAA-2.2`、`SAP-2.4` 或 `SAP-3.1`。 |
| `ch111-q06` | REVISE | 診斷方向正確；補 cold-start 時沒有 cached config 的處理，不能只寫「last-known-safe」。 |
| `ch111-q07` | REVISE | Agent/cache 可降低 retrieval 次數；「共享/批次 retrieval」需明確到 AppConfig Agent 的實際部署與 poll model，避免虛構跨 container 共用行為。 |
| `ch111-q08` | 內容通過 | AppConfig rollout + local retrieval 組合正確；仍受 G1。 |
| `ch111-q09` | REVISE | 跨 account/Region rollout 的實作、IAM delegation 與 artifact replication 缺精確來源；generic AppConfig deployment 頁不足。 |
| `ch111-q10` | REVISE | 與 `q02/q03/q08` 重複；改測 Agent cold start、stale emergency flag 或 rollback alarm unavailable。 |

### 第 112 章

| ID | 結果 | 精確修訂要求 |
|---|---|---|
| `ch112-q01` | REVISE | 三層責任正確但解析過薄；與 `q08` 重複。 |
| `ch112-q02` | REVISE | SCP explicit deny 結論正確；解析補充 SCP 不授權、且需同時存在 identity/resource allow。 |
| `ch112-q03` | REVISE | SG stateful、NACL stateless 正確；說明 ephemeral return port 是 client 端 port，方向取決於 NACL 所在 subnet。 |
| `ch112-q04` | REVISE | Cross-account SSE-KMS 需要 key policy 與 caller permission，正確；補精確 source，並明說 AWS managed key 不能提供一般 cross-account sharing。 |
| `ch112-q05` | REVISE | Lake Formation data filter 正確；補 row filter/column scope 的精確官方頁。 |
| `ch112-q06` | REVISE | 排查順序合理；Athena 還需 query-result S3、Glue Catalog、workgroup 等實際 permission，不能只列 generic policy layers。 |
| `ch112-q07` | REVISE | 成本/營運判斷合理；「每個 object 一把 KMS key」不是真實常見配置，改成 per-object envelope/data key 與過度增加 CMK 邊界的可信比較。 |
| `ch112-q08` | REVISE | 與 `q01` 重複；改成具體 VPC endpoint policy、IAM、KMS 與 Lake Formation deny 的判讀題。 |
| `ch112-q09` | REVISE | Multi-account ownership 正確但解析過薄；補 delegated administrator、log archive/security account responsibility。 |
| `ch112-q10` | REVISE | Prompt 沒要求 private path/audit，E 卻把必要 KMS decrypt 與可選 network/audit 綁成答案。把 private/audit 加入需求，或讓 E 只回答必要 KMS authorization。 |

### 第 113 章

| ID | 結果 | 精確修訂要求 |
|---|---|---|
| `ch113-q01` | REVISE | Business SLI 正確；解析補 numerator、denominator、window 與 duplicate/late completion 定義。 |
| `ch113-q02` | REVISE | Metrics/logs/traces 分工正確；干擾項過於絕對，改成三種 telemetry 都有但選錯順序/粒度的方案。 |
| `ch113-q03` | REVISE | 移除 `SAA-3.2`；題目是 observability/cardinality，不是 compute performance。使用 `SAP-3.1`/`SAP-3.3`，或重寫成 SAA resilient monitoring。 |
| `ch113-q04` | REVISE | Synthetics + RUM 組合正確；補 CloudWatch RUM 官方來源與測試交易不污染 production 的設計。 |
| `ch113-q05` | REVISE | 補 SQS/X-Ray trace-header 文件；說明自訂 business correlation ID 與 X-Ray trace context 不完全相同。 |
| `ch113-q06` | REVISE | 診斷方向正確但與 `q10`、`ch106-q06` 重複；改測 freshness watermark 或 late/out-of-order data。 |
| `ch113-q07` | REVISE | Telemetry cost controls 正確；補 audit logs 不應任意 sampling，以及 tail-based/ratio sampling 的限制。 |
| `ch113-q08` | REVISE | 組合合理；補 RUM/Synthetics/X-Ray 精確 source，並與 `q01` 拉開。 |
| `ch113-q09` | REVISE | Cross-account observability operating model 正確；加入具體 CloudWatch cross-account observability/OAM 或集中 logging source。 |
| `ch113-q10` | REVISE | 與 `q06` 重複；改測「偵測 freshness」與「定位 broken handoff」的不同訊號，並補足解析。 |

### 第 114 章

| ID | 結果 | 精確修訂要求 |
|---|---|---|
| `ch114-q01` | REVISE | RPO/RTO 解讀正確；補量測起訖點與 business service 恢復定義。 |
| `ch114-q02` | REVISE | Backup/restore 對寬鬆目標合理，但與 `q08` 幾乎相同；改成 pilot light/warm standby 的邊界題。 |
| `ch114-q03` | REVISE | AWS Backup contract 正確；`PITR` 是否可用依 resource type 而異，不可泛稱所有 AWS Backup resource 都有 PITR。 |
| `ch114-q04` | REVISE | Aurora Global Database switchover RPO 0、unplanned failover 可能有非零 RPO，事實正確；補 writer endpoint/client reconnect 與版本前提。 |
| `ch114-q05` | REVISE | 「複寫 keys」改成「在 DR Region 預建適當 KMS key，或在支援/需要時使用 multi-Region key」；一般 regional KMS key 不會自動複寫。 |
| `ch114-q06` | REVISE | RTO decomposition 正確；補 parallel/serial critical path 與每段 owner。 |
| `ch114-q07` | REVISE | `tested` 太空泛；改成「同一 RTO/RPO 下比較 backup/restore、pilot light、warm standby、active-active 的 TCO」。 |
| `ch114-q08` | REVISE | 與 `q02` 重複；保留一題即可。 |
| `ch114-q09` | REVISE | Fencing/failback 正確；補 DNS/client caching、write authority 與 data reconciliation 的順序。 |
| `ch114-q10` | REVISE | `tested` 過薄且與 `q03` 重複；改成量化 restore drill 的 RTO/RPO evidence。 |

### 第 115 章

| ID | 結果 | 精確修訂要求 |
|---|---|---|
| `ch115-q01` | REVISE | Unit cost 正確；應實際算出每單成本由 0.10 降至 0.08，並討論 failed/cancelled denominator。 |
| `ch115-q02` | REVISE | 「啟用不會追溯改寫所有歷史」已不完整。AWS 支援管理帳號將 cost allocation tag activation status 回填最多 12 個月；改成說明 backfill window 與資源當時沒有 tag value 的限制。 |
| `ch115-q03` | REVISE | 分工正確；加入 CUR 2.0/Data Exports 精確文件，避免只用 legacy CUR overview。 |
| `ch115-q04` | REVISE | Compute Optimizer 判斷合理；明確說是 RDS DB instance，加入 RDS recommendation 的 CPU/memory/network/EBS IOPS/throughput source。 |
| `ch115-q05` | REVISE | S3 gateway endpoint 方向正確；補 route table/endpoint policy、DNS/path 驗證與 NAT bytes before/after。 |
| `ch115-q06` | REVISE | `tested` 過薄；改成 billing-dimension drill-down、data freshness 與 deployment correlation，並補 Cost Explorer/CUR 更新延遲來源。 |
| `ch115-q07` | REVISE | Purchase mix 合理；補 Savings Plans、RI 與 Spot interruption/diversification 的精確官方 source，不能只引用 Cost Pillar。 |
| `ch115-q08` | REVISE | 「先滿足 constraints 再最低成本」正確；干擾項太明顯，改成兩個都達 99.95% 但 data transfer/operations 不同的方案。 |
| `ch115-q09` | REVISE | `tested` 過薄；補 anomaly→owner→change→realized savings 的完整 feedback loop。 |
| `ch115-q10` | REVISE | `tested` 過薄且與 `q04/q05` 重複；改測 commitment coverage、waste removal 與 SLO regression 的 trade-off。 |

### 第 116 章

| ID | 結果 | 精確修訂要求 |
|---|---|---|
| `ch116-q01` | REVISE | 7 Rs 方向正確；補每個 business driver 如何排除/偏好 rehost、repurchase、replatform、refactor。 |
| `ch116-q02` | REVISE | Discovery 方法正確；干擾項太弱，加入 agentless collector、Application Discovery Service/AWS Transform 與觀測窗口的可信方案。 |
| `ch116-q03` | REVISE | Move group 正確；與 `q09/q10` 重複，改測依賴分類與 wave sequencing。 |
| `ch116-q04` | REVISE | Current behavior 正確：Migration Hub 自 2025-11-07 起不接受新客戶，既有客戶可完成進行中專案；補 canonical availability-change link。 |
| `ch116-q05` | 內容通過 | MGN、DMS、DataSync 的 responsibility pairing 正確。 |
| `ch116-q06` | REVISE | Prompt 只有 MGN，正解卻寫 `CDC lag`；MGN 是 block-level replication，不是 DMS CDC。改成 MGN replication status/lag、launch settings、network/dependency/acceptance；若另有 database CDC，必須在 prompt 明說。 |
| `ch116-q07` | REVISE | Business-value 判斷正確；補 decommission、license termination、dual-run exit criteria 與 benefit owner。 |
| `ch116-q08` | REVISE | Engine change 不只是「managed database/DMS」；加入 DMS Schema Conversion（或 legacy AWS SCT）處理 schema/code conversion，DMS 處理 data full load/CDC。 |
| `ch116-q09` | REVISE | 移除 `SAP-1.4`，題幹沒有 multi-account design；以 `SAP-3.1`、`SAP-4.2` 為主。`tested` 也需具體化。 |
| `ch116-q10` | REVISE | 移除 `SAP-4.4`，題目是 migration completion/operational handoff，不是 modernization opportunity；加入 `SAP-3.1` 或只保留 `SAP-4.2`。 |

## 出版前驗證條件

修訂後至少須全部通過：

1. `python3 tools/check_aws_question_banks.py --part 11`
2. 96 題單選的「正解為唯一最長選項」比例不得形成可利用模式。
3. 24 題複選答案位置須分散，不能維持每章 `q09=AD`、`q10=BE`。
4. 上述 factual/task/source 修訂逐項回歸。
5. 重跑跨 part 相似度與人工審查，確認沒有把 Part 11 的 portable pattern 題改寫成其他章節的同義題。
6. 題庫檔案不得引入 dumps、回憶真題或社群題庫逐字/近似重製；官方 sample 僅校準題型與推理深度。

REVISE

## Maintainer Final Verification

驗證日期：2026-10-01（星期四）。本輪由 maintainer 在停止 subagent 後直接完成；
所有晚於今日的公告或生效日均仍視為未來。

- Part 11 validator 通過：120 題、12 章；原有 IDs、intents 與每章題型分布完整。
- 96 題單選答案位置 A／B／C／D 各 24 題，正解長度排名 1–4 亦各 24 題；
  24 題複選分散為多種組合，不再使用固定 `AD`／`BE` 模板。
- 前次列出的 36 個跨章填充模板逐一掃描為 0；再以 16 字以上 clause 掃描全部
  choices 與 explanations，沒有相同 clause 出現在三題以上。解析均回到該題的
  service mechanism、hard constraint 或 operating trade-off。
- `ch106-q08` 已有 EventBridge/SNS fan-out 來源；`ch108-q02` 僅允許 assigned cell
  內的健康 endpoint；`ch110-q03` 使用 database commit → outbox/invalidation/version
  的順序，且不再引用 DAX consistency 作一般 cache ordering 證據。
- AppConfig backup/preload、SQS Fair Queues、Lake Formation filters、RUM/X-Ray/OAM、
  DR options、Savings Plans、MGN replication/cutover 等均使用題目 claim 對應的官方
  deep links。
- MGN 不再與 DMS CDC 混淆；cost-tag backfill、cache ordering、KMS Region 邊界、
  DMS Schema Conversion 與 migration task mappings 均已修正。
- 題庫不含 SAP-C03 guide 假設、exam dump、回憶真題，亦未把 2026-10-01 之後事件
  描述為已發生。

VERIFIED

## Final Verification

- 最終第三輪驗證日期：2026-10-01（Thursday）。
- 時間邊界：只採用截至 2026-10-01 已發布的 AWS 官方資料；題庫未出現 `SAP-C03`、2026-11/12 或 2027 年以後事件，也未把未來事件寫成已發生。
- 驗證範圍：唯讀檢查修訂後 `part_11.json` 的 120/120 題、12 章與 115 個 sources；未修改題庫。
- Validator 仍通過：`✅ AWS question banks passed: 120 questions across 12 chapters`。

### 已通過

1. **36 個模板 clause 已全部清零。**

   - 前一輪列出的 36 個完整 clause 在 prompt、choices 與 explanations 中均為 0 次。
   - 以中文標點重新切分所有選項與解析後，長度至少 16 字且跨 3 題以上重複的 clause 為 0。
   - 完全相同的 explanation 為 0。前一輪指出的無關填充已移除；抽查與前輪問題表相關的解析後，內容均回到各題的 constraint、service mechanism 或 trade-off。

2. **答案位置仍平衡。**

   - 96 題單選：A=24、B=24、C=24、D=24；每章均為 A/B/C/D 各 2 題。
   - 單選正解的選項長度排名也恰為：最長 24、第二長 24、第三長 24、最短 24；其中正解為「唯一最長」者 23/96。
   - 24 題複選共 9 種答案組合；各位置被選為正解的次數為 A=10、B=9、C=10、D=9、E=10，位置本身沒有偏斜。

3. **上一輪表列的 sources、facts 與 mappings 均已修正。**

   - `ch106-q08` 已加入 EventBridge pattern 與 SNS→SQS fan-out 官方來源。
   - `ch108-q02` 已限定 router 只能在 tenant 所屬 cell 內選健康 endpoint；跨 cell 前必須先遷移 authoritative state、fence 舊 writer 並更新 mapping。
   - `ch110-q03` 已改用 transactional outbox 精確來源，並保持 database commit → reliable invalidation → version/TTL 防 stale refill 的正確順序。
   - `ch111-q02/q04/q06/q10` 的 AppConfig Agent source 已改為包含 container/ECS Agent 啟動與 backup/preload 設定的有效 deep link。
   - `ch113-q08` 已只保留 `SAA-2.2`。
   - `ch114-q08` 已加入 AWS DR options 官方來源。
   - `ch115-q07/q10` 已分別引用 Savings Plans recommendations、coverage 與 utilization 的有效 deep links。
   - `ch116-q06` 已使用有效的 MGN replication metrics 與 cutover deep links，且未再把 DMS CDC 當成 MGN replication。
   - `ch116-q08` 已改為 SAP，mapping 為 `SAP-4.2`、`SAP-4.3`。

### 尚未通過：複選題仍有可利用的正解長度線索

24 題複選中有 **18 題（75%）的兩個正解恰好就是全題最長的兩個選項**。即使正解位置分布均衡，考生仍可用選項長度顯著提高命中率，因此「答案長度平衡」尚未成立：

`ch105-q09`, `ch105-q10`, `ch106-q10`, `ch107-q09`, `ch107-q10`, `ch108-q09`, `ch108-q10`, `ch109-q09`, `ch109-q10`, `ch110-q09`, `ch111-q09`, `ch111-q10`, `ch112-q09`, `ch113-q09`, `ch114-q09`, `ch115-q10`, `ch116-q09`, `ch116-q10`

修訂時應改寫上述題目的選項長度，但保留目前答案位置與正解內容。建議把「兩個最長選項恰為兩個正解」降到不超過約 1/3，並讓每章至少有一題複選的最長 distractor 長於其中一個正解；修後需重新檢查語意唯一性，避免單純填充無關 clause。

其餘本輪要求均已通過，但上述長度線索仍是可重現的全域品質 blocker。

REVISE

## Verification

- 重新驗證日期：2026-10-01（Thursday）
- 時間邊界：只接受截至 2026-10-01 已發布的 AWS 官方資料；未把任何晚於此日的事件當成已發生
- 驗證範圍：重新讀取修訂後 120/120 題、111 個 sources、原報告全部逐題要求與 G1–G3
- 操作限制：未修改 `tools/aws_question_banks/part_11.json`

### 已修正並通過

1. **99 項 gate 已全部清除。**
   `python3 tools/check_aws_question_banks.py --part 11` 現在通過：

   ```text
   ✅ AWS question banks passed: 120 questions across 12 chapters
   ```

2. **答案位置與正解長度線索已大幅改善。**

   - 96 題單選答案位置：A=24、B=24、C=24、D=24。
   - 正解為唯一最長選項由 93/96 降至 24/96，且每章恰為 2/8，已不再是可直接利用的單一線索。
   - 24 題複選已分散成 9 種組合：AC=4、BD=4、AE=3、CE=3、AD=3、BE=3、BC=2、CD=1、DE=1。
   - 原本固定 `q09=AD`、`q10=BE` 的模板已消失。

3. **原報告指定的主要事實問題已修正。**

   - `ch116-q06` 已明確限定 AWS Transform MGN 的 continuous block-level replication，並排除 DMS CDC；正解不再把 `CDCLatencySource` 當 MGN 指標。
   - `ch115-q02` 已正確寫成管理帳號可申請最多 12 個月 cost allocation tag backfill，且只會回填歷史上實際存在的 tag values。
   - `ch110-q03` 已改成 authoritative database write 先成功，再以 outbox/event/retry 更新或失效 cache，並以 version/TTL 處理 stale refill race。
   - `ch105-q05`、`ch116-q08` 已區分 DMS Schema Conversion/AWS SCT 的 schema/code conversion 與 DMS full load/CDC 的資料搬移。
   - `ch106-q09` 已區分 EventBridge archive/replay、target DLQ 與 event-bus resource policy。
   - `ch108-q05`、`ch109-q09` 已正確說明 SQS Fair Queues 使用 standard queue 的 `MessageGroupId`，且 fair queue 不等於 hard per-tenant quota。
   - `ch114-q03` 已不再把 PITR 泛稱為所有 AWS Backup resource 的共同能力。
   - `ch114-q05` 已把一般 Regional KMS key 與 multi-Region key 的 DR 邊界分開。

4. **原報告指出的主要 task mappings 已修正。**

   - `ch105-q02`：`SAA-3.3` → `SAA-3.5`
   - `ch106-q04`：`SAP-2.1` → `SAP-2.4`
   - `ch108-q04`：加入 `SAP-1.3`
   - `ch110-q07`：移除不相關的 `SAA-4.3`
   - `ch111-q05`：改為 `SAA-2.2`、`SAP-3.1`
   - `ch113-q03`：移除 `SAA-3.2`
   - `ch116-q09`：移除 `SAP-1.4`
   - `ch116-q10`：移除 `SAP-4.4`，改用 `SAP-3.1`、`SAP-4.2`

5. **版本與日期邊界通過。**

   - 題庫仍以官方 SAA-C03 與 SAP-C02 為準。
   - 未出現 `SAP-C03`、`SAP-C03 transition` 或假設未發布 guide 的敘述。
   - 未發現晚於 2026-10-01 的日期被寫成已發生事件。

### 尚未通過：G1/G3 被機械式填充取代，未真正完成 distractor 重寫

雖然 validator 與答案長度統計已通過，但大量選項是以重複附加章節模板句來增加長度。抽取至少 16 字且跨 3 題以上重複的 clause 後，**96/120 題**仍含這種模式：

- 第 105 章：`ch105-q01`–`ch105-q08`
- 第 106 章：`ch106-q01`–`ch106-q04`, `ch106-q06`–`ch106-q08`
- 第 107 章：`ch107-q01`–`ch107-q08`
- 第 108 章：`ch108-q01`–`ch108-q04`, `ch108-q06`–`ch108-q09`
- 第 109 章：`ch109-q01`–`ch109-q08`
- 第 110 章：`ch110-q02`–`ch110-q04`, `ch110-q06`–`ch110-q08`
- 第 111 章：`ch111-q01`–`ch111-q09`
- 第 112 章：`ch112-q01`–`ch112-q04`, `ch112-q06`–`ch112-q08`
- 第 113 章：`ch113-q01`–`ch113-q10`
- 第 114 章：`ch114-q01`–`ch114-q04`, `ch114-q06`–`ch114-q09`
- 第 115 章：`ch115-q01`–`ch115-q04`, `ch115-q06`–`ch115-q09`
- 第 116 章：`ch116-q01`–`ch116-q09`

重複模板包括：

- `另安排staging相容性測試與限時parallel run`
- `以restore與reconciliation報告作變更附件`
- `另設定target retry、DLQ與correlation欄位`
- `另預建跨AZ容量並演練client reconnect`
- `並預留tenant relocation與evacuation capacity`
- `為cache失效與source outage準備runbook`
- `另保存configuration version與deployment history`
- `另以CloudTrail與central logs保存audit evidence`
- `另建立service dashboard與具名alarm owner`
- `並量測declaration、restore與validation時間`
- `另以CUR line item與deployment時間做關聯`
- `另設定wave gate、rollback authority與hypercare`

這不只是風格問題，部分模板已造成選項或解析與題幹不相干：

- `ch105-q04`：RDS production 設定的錯誤選項被附加 quota、資料匯出、parallel run 與 reconciliation，無助於比較 Multi-AZ/PITR/KMS/SG。
- `ch106-q03`、`ch106-q04`：同步 API、Step Functions 與 EventBridge 選項被重複加入 queue age、DLQ、redrive owner，模糊了真正責任邊界。
- `ch107-q07`：DR 成本選項混入與該選項無關的 client reconnect、health canary 與 runbook owner。
- `ch112-q03`：正解解析加入通用的「責任放在正確元件、串成可測 contract」，沒有進一步解釋 ephemeral return-port 方向。
- `ch113-q04`：Synthetics/RUM 正解解析聲稱定義了「rollback 條件」，但此題不是 deployment rollback。
- `ch114-q04`：Aurora Global Database 的 Route 53 錯誤選項解析突然討論 DR TCO，與選項錯誤原因無關。
- `ch115-q07`：purchase-model 正解解析聲稱定義了端到端驗收與 rollback，題目並沒有這些內容。
- `ch116-q03`：`第一波放全部 mission-critical systems` 的解析錯誤談到 mover 的 state/protocol，與 wave-risk 問題無關。
- `ch116-q04`：`既有 Migration Hub projects 已被立即刪除` 的解析又誤插 server block/database CDC/file transfer。

修訂要求：刪除上述模板填充；每個 distractor 必須以該題真正的 hard constraint、service mechanism 或 operating trade-off 解釋，不可用跨章通用句補長度。修完後仍須保持目前答案位置分布，不能退回「正解最長」模式。

### 尚未通過：特定來源、內容與 mapping

| 題號 | 驗證結果與必要修法 |
|---|---|
| `ch106-q08` | 正解已補上 S3→EventBridge/SNS→獨立 queues 的 fan-out，但 `source_ids` 仍只有 SQS/ASG，沒有 EventBridge 或 SNS fan-out 官方來源。 |
| `ch108-q02` | 仍使用含糊的「健康轉送」。應明確限定為已指派 cell 內的健康 endpoint；不得暗示 router 可把 tenant 任意送到沒有其 authoritative state 的另一 cell。 |
| `ch110-q03` | 機制已修正，但 `dax-consistency` 不是一般 database/cache outbox、invalidation ordering 的精確來源。移除不相關 source，或加入支持 write/invalidation pattern 的 AWS 官方架構文件。 |
| `ch111-q02`, `ch111-q04`, `ch111-q06`, `ch111-q10` | `appconfig-agent-backup` URL 會 redirect 到 AppConfig User Guide 首頁，未精確支持 `BACKUP_DIRECTORY/PRELOAD_BACKUP`。改用實際包含這些設定的 AppConfig Agent container/ECS configuration deep link。 |
| `ch113-q08` | `SAA-3.2` 仍是額外且不精確的 mapping；payment observability 題核心是 availability/operations，不是 high-performing elastic compute。保留 `SAA-2.2` 即可。 |
| `ch114-q08` | 題目直接定義 warm standby 與 pilot light 邊界，但 sources 只有 Backup plan/restore testing；應加入 `dr-options`，否則來源不支持該核心分類。 |
| `ch115-q07`, `ch115-q10` | `savings-plans` URL 會 redirect 到 Savings Plans guide 首頁，不是 recommendation/coverage/utilization 的精確 deep link。 |
| `ch116-q06` | MGN 與 DMS CDC 的事實已修正；但 `mgn-replication`、`mgn-cutover` 兩個 URL 都 redirect 到 MGN guide 首頁，仍未達「精確 deep link」要求。 |
| `ch116-q08` | 題目標為 SAA，但 `SAA-2.1`、`SAA-4.2` 都不能精確對應 heterogeneous database migration tooling；應標成 SAP migration 題，或明確註記為 SAA enrichment 而非官方 task coverage。 |

### 最終判定

本輪已確認 gate、答案位置、MGN 非 CDC、cost backfill、cache commit/invalidate、主要 task mapping 與 SAP-C02 版本邊界均有實質改善；但 distractor/解析的機械式填充仍廣泛存在，且上表來源與 mapping 尚未全部修完，因此不能標記為 `VERIFIED`。

REVISE

## Consolidated Maintainer Verification

最終驗證日期：2026-10-01（星期四）。本節檢查的是所有 review 與最後一次人工修訂後的
最新 `part_11.json`，因此取代前一輪對舊檔案的 `REVISE` 判定。

- 題庫 gate 通過：120 題、12 章；96 題單選答案位置 A/B/C/D 各 24 題，正解長度排名
  1–4 亦各 24 題。
- 24 題複選中，正解恰為全題最長選項集合者已由 18 題降至 6 題；答案位置與選項長度
  均不再提供穩定猜題捷徑。
- 前輪列出的 36 個填充模板均為 0 次；以 16 字以上 clause 檢查，沒有同一 clause
  出現在三題以上，也沒有重複 explanation。
- EventBridge/SNS fan-out、cell routing、transactional outbox、AppConfig
  backup/preload、DR options、Savings Plans 與 MGN replication/cutover 的 sources、
  facts 與 mappings 均已逐項修正。
- MGN 未與 DMS CDC 混用；`ch116-q08` 已標為 SAP migration 題；未引用 SAP-C03
  未發布 guide，亦未使用 exam dump 或回憶真題。

VERIFIED
