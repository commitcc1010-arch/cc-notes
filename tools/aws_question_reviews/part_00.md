# R00 獨立實質審查：part_00（第 1–10 章）

審查日期：2026-10-01
Reviewer：R00（非題庫作者 P00-A）
範圍：`tools/aws_question_banks/part_00.json` 全部 100 題
依據：`tools/aws_question_banks/README.md`、`tools/aws_exam_audits/part_00.md`、SAA-C03／SAP-C02 官方 exam guide 與現行 AWS 產品文件

## 結論摘要

- 結構完整：10 章、100 題；每章 intents 1–10 各一次，且每章為 8 題單選、2 題複選。
- 答案位置分布合格；題內沒有重複選項，Part 00 內沒有重複或近似重複題幹。
- 與目前其他 1,060 題跨 part 比對，未發現高度近似題幹。
- 與舊五題 fallback 的題幹、選項與解析全文比較，最高正規化相似度為 0.122，沒有實質沿用舊模板措辭。
- 52 個 official source 與 13 個 community source 在審查日皆可開啟；community source 未出現 ExamTopics、braindump、recalled/live/actual exam questions 等標記。
- 對 Jayendra 來源做 10 個連續英文 token 比對，未發現題幹或選項直接照抄。
- 解析普遍比舊題完整，通常有說明錯項違反的限制；但 38 題仍有 correctness、task mapping、來源精度或 distractor rigor 問題。
- 其中 6 題會直接造成錯誤或不唯一學習，不能發布：`ch001-q04`、`ch002-q10`、`ch005-q06`、`ch005-q08`、`ch006-q10`、`ch008-q08`。

整體判定為 **REVISE**。其餘 62 題可保留；38 題依下列精確動作修訂後應再由不同 reviewer 複核。

## Status key

- `OK`：答案集合唯一，核心事實、scope、解析、來源與干擾項可接受。
- `ANSWER`：正解未完整滿足題幹，或題目缺少使答案唯一的條件。
- `CURRENT`：敘述未反映 2026-10-01 的現行 AWS 行為。
- `MAP`：SAA-C03／SAP-C02 task key 不對應實際被測能力。
- `SOURCE`：現有官方來源過於寬泛、漏掉選項中的重要事實，或 URL 已退化。
- `RIGOR`：多個 distractors 與情境無關或明顯荒謬，無法提供相應考試層級的鑑別力。

## 100 題逐題覆核矩陣

| 章 | Question-by-question disposition |
|---|---|
| 1 | `q01 MAP`; `q02 MAP`; `q03 MAP`; `q04 ANSWER/MAP`; `q05 MAP`; `q06 MAP`; `q07 MAP`; `q08 MAP`; `q09 MAP`; `q10 MAP` |
| 2 | `q01 OK`; `q02 SOURCE`; `q03 OK`; `q04 OK`; `q05 OK`; `q06 OK`; `q07 OK`; `q08 OK`; `q09 OK`; `q10 ANSWER/CURRENT` |
| 3 | `q01 OK`; `q02 SOURCE`; `q03 OK`; `q04 SOURCE`; `q05 SOURCE`; `q06 OK`; `q07 SOURCE`; `q08 OK`; `q09 OK`; `q10 MAP/SOURCE` |
| 4 | `q01 OK`; `q02 SOURCE`; `q03 OK`; `q04 SOURCE`; `q05 OK`; `q06 OK`; `q07 OK`; `q08 OK`; `q09 OK`; `q10 SOURCE/RIGOR` |
| 5 | `q01 OK`; `q02 OK`; `q03 OK`; `q04 OK`; `q05 OK`; `q06 ANSWER/SOURCE`; `q07 OK`; `q08 ANSWER/SOURCE`; `q09 MAP`; `q10 MAP/RIGOR` |
| 6 | `q01 OK`; `q02 OK`; `q03 OK`; `q04 OK`; `q05 OK`; `q06 SOURCE`; `q07 OK`; `q08 OK`; `q09 MAP`; `q10 CURRENT/ANSWER/MAP/SOURCE` |
| 7 | `q01 OK`; `q02 OK`; `q03 OK`; `q04 OK`; `q05 RIGOR`; `q06 OK`; `q07 OK`; `q08 OK`; `q09 SOURCE`; `q10 OK` |
| 8 | `q01 OK`; `q02 OK`; `q03 OK`; `q04 OK`; `q05 RIGOR`; `q06 OK`; `q07 OK`; `q08 ANSWER`; `q09 OK`; `q10 OK` |
| 9 | `q01 SOURCE`; `q02 OK`; `q03 RIGOR`; `q04 OK`; `q05 OK`; `q06 OK`; `q07 OK`; `q08 OK`; `q09 OK`; `q10 OK` |
| 10 | `q01 OK`; `q02 OK`; `q03 RIGOR`; `q04 OK`; `q05 RIGOR`; `q06 MAP`; `q07 MAP`; `q08 OK`; `q09 MAP`; `q10 OK` |

`OK` 代表本輪沒有發現必須阻擋發布的問題，不代表未來服務行為更新後不需重驗。

## 1. 必須先修正的答案唯一性與現行事實

### `ch001-q04` — Well-Architected milestone 順序少了初始 baseline

正解 D 把 milestone 寫成「改善後才儲存」。現行 Well-Architected Tool 流程是：完成初次 workload review 後先儲存一個 milestone 作 baseline；架構或改善狀態改變後，再建立後續 milestones 比較進展。沒有初始 baseline，就無法完成題幹所說的季度追蹤。

精確動作：

1. 將 D 改成「定義 workload/owner → 回答 lens questions → 辨識風險與 improvement items → 儲存初始 milestone → 指派並執行改善 → 後續季度或重大變更後再儲存 milestone」。
2. 解析區分 milestone、即時監控和自動 remediation：milestone 是不可變的時間點快照，不會替客戶修資源。
3. 保留 `aws-wa-tool`，並直接引用 [Milestones](https://docs.aws.amazon.com/wellarchitected/latest/userguide/milestones.html)。

### `ch002-q10` — 「資料只能在核准 Region 處理」與 CloudFront edge 路徑矛盾

題幹不只要求資料儲存於核准 Region，也要求個人資料只在該 Region「處理」。目前正解 C 說其他路徑可經 CloudFront policy 回 origin；即使不快取，viewer request 仍會先到 edge，並可能在 edge 終止 TLS、檢查 header 或執行其他處理。A+C 因此不能在目前文字下保證嚴格的 processing residency。

精確動作：

1. 二選一重寫：
   - 若只考 storage residency，把題幹改成「權威資料與持久副本不得離開核准 Region」，並明說敏感 response 禁止 edge cache。
   - 若保留 processing residency，正解必須使用獨立的公開圖片 hostname/distribution；PII API 直接進入核准 Region，不經全球 CloudFront POP。
2. 解析說明「不快取」不等於「沒有在 edge 處理」，data classification、TLS termination、logs、edge functions 都需納入資料流。
3. 加入明確的 CloudFront data-protection／request-flow 官方來源，不要只引用 cache key 文件。

### `ch005-q06` — 未指定 load balancer 類型，TCP health check 的可用性不明

題目以 `/ready` 比較 TCP 與 HTTP health check，但沒有說是 ALB 還是 NLB。ALB target group 的健康協定不是任意 TCP；NLB 才能直接在 TCP、HTTP、HTTPS 等健康協定間選擇。正解 D 的概念比較合理，但不是一個可直接配置的唯一 AWS scenario。

精確動作：

1. 若要保留 TCP 對 HTTP 的比較，把資源明示為 Network Load Balancer，並說 target group 可選 TCP 或 HTTP health check。
2. 若要考 ALB，移除「選 TCP health check」的假設，改成比較淺層 `/live` 與能反映 thread-pool readiness 的 `/ready`。
3. 來源改用對應 load balancer 的 target health 官方頁面，不要只引用 ELB 總覽。

### `ch005-q08` — 「ACM certificate」不足以保證 managed renewal

ACM 中可以有 AWS 簽發的 public certificate，也可以有 imported certificate。Imported certificate 不由 ACM 自動續期。正解 B 只寫「有效的 ACM certificate」，因此不能滿足題幹明示的受管續期要求。

精確動作：

1. 把 B 改成「在 ALB 同 Region 使用 ACM 簽發、符合 managed-renewal eligibility 的 public certificate」。
2. 解析補充：certificate 必須持續被支援的 AWS 服務使用，且 DNS／email validation 等續期條件必須可成立；imported certificate 需自行續期與重新匯入。
3. 加入 [Managed certificate renewal in AWS Certificate Manager](https://docs.aws.amazon.com/acm/latest/userguide/managed-renewal.html)。

### `ch006-q10` — S3 append／rename 的絕對敘述已過時

正解 B 說 S3 不提供 in-place append 與 directory rename。到 2026-10-01，S3 Express One Zone directory buckets 已支援限定形式的 append，並提供 metadata-only、atomic `RenameObject`。S3 仍不是一般 POSIX filesystem，也沒有完整 POSIX locking／directory contract，但不能再以「完全沒有 append 或 rename」作絕對理由。

精確動作：

1. 保留 A，但把 B 改成：「S3 object API 即使在 directory bucket 有限定 append／rename，仍不提供 legacy application 所要求的完整 POSIX file descriptor、任意 in-place mutation、跨目錄語意與 POSIX locking contract。」
2. 解析分開說明 general purpose buckets、S3 Express One Zone directory buckets 與 Mountpoint for S3；不要把特定新能力推論成完整 POSIX filesystem。
3. 加入：
   - [Appending data to objects in directory buckets](https://docs.aws.amazon.com/AmazonS3/latest/userguide/directory-buckets-objects-append.html)
   - [Renaming objects in directory buckets](https://docs.aws.amazon.com/AmazonS3/latest/userguide/directory-buckets-objects-rename.html)
4. 重新檢查兩個正解仍應為 A+B，但 B 必須是「缺少完整 POSIX contract」，而不是已過時的功能絕對否定。

### `ch008-q08` — 「付款資料不可遺失」沒有被正解完整滿足

正解 B 只寫 durable data store、backup 與 tested restore。Backup 可處理時間點恢復，不能單獨保證最後一筆已確認交易零資料損失；「不可遺失」也不是可驗證的工程目標。題目需要明確 RPO、commit acknowledgement 與 replication/fencing contract。

精確動作：

1. 把需求改成可量測的 RPO，例如「已向 client 確認成功的付款不得在單 AZ 故障後遺失，誤刪時 RPO ≤ 5 分鐘」。
2. 正解加入：只有 durable transaction commit/同步 HA 條件成立後才回覆成功；另以隔離 backup/PITR 處理邏輯刪除。
3. 解析區分 HA replication、durability、backup/PITR 和 application acknowledgement；不得再用「durable store + backup」推論絕對零損失。

## 2. SAA-C03／SAP-C02 task mapping 必須修正

### `ch001-q01`–`ch001-q10`

這十題測的是讀題、讀書計畫、素材使用和自我驗收，不是它們目前標註的 SAA/SAP architecture task。例：`SAA-2.1` 是 scalable and loosely coupled architectures，不是 coverage matrix；`SAP-2.4` 是 reliability strategy，不是如何使用 exam guide。

精確動作：

1. 若保留題目，將 `level` 改成 `Orientation`／`Study method`，`task_keys` 使用非考綱的 book-meta key，並在 UI 明示「不計入 SAA/SAP 模擬分數」。
2. 若 schema 強制要求官方 task，則重寫十題為真正測試相應 architecture task 的 scenario；不能只因題幹提到「考試」就掛 task key。
3. `ch001-q04` 除 mapping 外，仍須完成前節 milestone 修正。

### 其他錯誤 mapping

- `ch003-q10`：Fargate customer responsibility／IAM/network 設定不是 `SAP-2.5` performance objective。改為 `SAA-1.2`；若必須保留 SAP 層級，使用 `SAP-2.3` 並增加 enterprise security-control constraint。
- `ch005-q09`：multi-Region DNS failover、fencing、draining 與 rollback 是 reliability／resilience。將 `SAP-2.5` 改為 `SAP-1.3` 或 `SAP-2.4`。
- `ch005-q10`：ALB 502 evidence 與 troubleshooting 不是 `SAP-2.3` security controls。改為 `SAP-3.1`；若題目改成 performance bottleneck 才使用 `SAP-3.3`。
- `ch006-q09`：petabyte NAS 遷移、protocol preservation、incremental copy 與 cutover 是 migration approach。將 `SAP-2.5` 改為 `SAP-4.2`。
- `ch006-q10`：storage semantics 不是 `SAP-2.6` cost optimization。改為 `SAA-3.1`；若保留 SAP level，可使用 `SAP-2.5` 並明確加入 performance objective。
- `ch010-q06`：六 pillars 的整體 trade-off 不能只映射到 `SAP-2.3` security controls。使用涵蓋實際 scenario 的 task 組合，或改成 `SAP-3.1` 並把題目聚焦到 continuous improvement。
- `ch010-q07`：RDS 與自管 EC2 database 的 TCO 是 cost-optimized database，將 `SAA-2.1` 改為 `SAA-4.3`。
- `ch010-q09`：跨帳號 findings、owner、分波 rollout 與 milestones 是 continuous improvement／operational excellence，將 `SAP-2.3` 改為 `SAP-3.1`；只有新增明確 security remediation 時才可另加 `SAP-3.2`。

## 3. 官方來源不足或 URL 退化

以下題目的核心答案多半可保留，但 source provenance 尚未滿足「每個重要事實都有直接 official source」的合約。

### Compute

- `ch003-q02`, `ch003-q10`：`aws-ecs-fargate` 的 `architect-fargate.html` 已導向 ECS developer guide 首頁。改用 [AWS Fargate for Amazon ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html) 與 task networking／IAM 的直接頁面。
- `ch003-q04`：Lambda welcome page 不足以同時支持 API Gateway proxy event、execution-role credentials、DynamoDB authorization 與 VPC networking。加入 Lambda execution role、API Gateway Lambda proxy integration、Lambda VPC internet access 的直接官方來源。
- `ch003-q05`：現有 concurrency 文件支持 throttling／reserved concurrency，但未直接支持 RDS connection pooling、queue 與 backpressure 的全部敘述。加入 RDS Proxy 與 Lambda asynchronous/queue integration 文件，或縮小解析到現有來源可證明的範圍。
- `ch003-q07`：承諾折扣與 duty-cycle 成本比較需要 Savings Plans／ECS-Fargate pricing 官方來源，不能只靠產品概念頁。

### Networking

- `ch002-q02`：選項 D 與解析斷言 Global Accelerator 不快取 objects 且處理 TCP/UDP，但 `source_ids` 漏了已存在的 `aws-global-accelerator`。直接補入。
- `ch004-q02`：VPC 首頁不足以支持「每個 IPv4 subnet 保留五個位址」。加入 [Subnet sizing for IPv4](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html)。
- `ch004-q04`：VPC 首頁不足以支持 TGW/VPN propagation、on-prem return route 與 stateful-inspection symmetry。加入 Transit Gateway route tables、Site-to-Site VPN routing 與 appliance-mode/asymmetric-routing 的精確官方頁面。
- `ch004-q10`：題目直接測 NAT egress，但沒有 NAT Gateway／public-private subnet data path 來源。加入 VPC NAT gateway 與 private subnet example。
- `ch005-q06`：依前節先確定 ALB 或 NLB，再加入該服務 target health 的直接來源。
- `ch005-q08`：加入 ACM managed-renewal eligibility；目前 ACM overview 無法排除 imported certificate。

### Storage and data

- `ch006-q06`：`aws-fsx-guide` 只是 FSx 文件入口。加入 FSx for Windows File Server、FSx for Lustre 的獨立官方頁面，直接支持 SMB/AD 與 Lustre 映射。
- `ch006-q10`：加入 S3 Express One Zone append／rename 現行文件，並修正絕對敘述。
- `ch007-q09`：AWS database overview 與 SAP exam guide 不足以支持 CDC、dual-write、shadow comparison、reconciliation 與 cutover contract。加入 AWS DMS CDC 與資料庫現代化／分階段遷移的官方 prescriptive guidance。
- `ch009-q01`：Reliability pillar 首頁不足以一次定義 SLA、SLI、SLO、RTO、RPO。加入 AWS Well-Architected service-level objectives 與 DR objectives 的直接章節。

## 4. Distractor rigor 不足

下列題目雖然能猜中正解，但錯項多為跨 domain 無關物件或明顯荒謬敘述，未達 declared SAA/SAP level。每題至少把兩個 distractors 改成「局部可行但違反一項明示限制」的 near-miss。

### `ch004-q10`

目前 IAM user 密碼、S3 versioning、EC2 purchase option 都與 outbound packet path 無關，複選題只剩 C+D 可選。

精確動作：改用可混淆的網路方案，例如「private subnet 直接指向 IGW 但 instance 無 public IP」、「NAT gateway 位於沒有 IGW route 的 subnet」、「只檢查 SG egress而忽略 NACL ephemeral return」。

### `ch005-q10`

題幹已證明 DNS 與 client-to-ALB TLS 成功，換 resolver、提高 TTL、domain registration 過期都立即被排除。

精確動作：改用 ALB 502 的鄰近原因／非原因，例如 target reset、malformed HTTP response、backend TLS handshake、health-check success 但 production response invalid，以及會造成 503/504 而非 502 的條件。

### `ch007-q05`

三個錯項分別跳到 RDS、Route 53、Redshift，沒有任何 DynamoDB near-miss。

精確動作：以「只提高 table aggregate capacity」、「誤以為 adaptive capacity 可消除單一 hot key」、「增加不符合 access pattern 的 GSI」等選項取代。

### `ch008-q05`

提高 S3 durability、降低 DNS TTL、反覆重啟單機都不是 ASG max/p99 scenario 的合理 SAP distractor。

精確動作：加入「只提高 ASG max」、「改 scheduled scaling但忽略不可預測尖峰」、「降低 target但不檢查 DB saturation」等部分可行方案，要求讀者以 evidence 選出完整診斷。

### `ch009-q03`

EC2 size 與 Route 53 record 不是 AWS Backup plan 的可信替代。

精確動作：改用「只有 schedule/retention，沒有 cross-account vault」、「有 cross-Region copy但無 restore test」、「依 tag assignment但漏掉 KMS/immutability」等實際設定組合。

### `ch010-q03`

把 HRI 說成 database partition key 是舊 generic-generator bug 的殘影，不像真實治理選項。

精確動作：改成缺少 baseline milestone、沒有 owner/due date、只匯出報告不收 evidence、只追 HRI 不追 remediation status 等 near-miss。

### `ch010-q05`

提高 durability 與換 Region 都無法合理回應 public bucket policy 事故。

精確動作：加入更接近的錯誤方案，例如「只開 Block Public Access但不移除既有 exposure path」、「只加 encryption而不改 authorization」、「只看 IAM identity policy而漏 bucket/access-point policy」。

## 5. 已通過的品質項目

### Intent coverage

第 1–10 章每章都依 audit 順序覆蓋：

1. Purpose
2. Mechanism
3. Concrete setting
4. Data/request flow
5. Failure diagnosis
6. Comparison
7. Cost/operations
8. SAA scenario
9. SAP expansion
10. Multi-response

除了第 1 章屬 meta-learning 而非官方 task 外，其他章節 intent 與題目形狀一致。

### 唯一答案與解析

除前述 6 題外，其餘題目的 selected answer set 可由題幹限制排除其他選項。解析均逐項提供，長度與內容超過合約下限；多數解析也說明 distractor 在何種條件下才可能成立。

### Duplication and provenance safety

- Part 00 內無 exact/near-duplicate prompt。
- 與目前其他 parts 的 1,060 題比對，沒有達到 sequence similarity 0.72 或 token Jaccard 0.58 的題幹。
- 與 legacy fallback 全文比對最高相似度 0.122。
- 13 個 community source 僅作 topic/distractor inspiration；沒有 prohibited dump marker，也沒有發現 10-token 英文連續照抄。
- 題目均為中文原創 scenario，沒有 live-exam recollection 的來源或措辭證據。

## 修訂完成後的再驗收清單

1. 修完 `ch001-q04`, `ch002-q10`, `ch005-q06`, `ch005-q08`, `ch006-q10`, `ch008-q08`，重新判定答案集合。
2. 修正 `ch001-q01`–`ch001-q10`, `ch003-q10`, `ch005-q09`, `ch005-q10`, `ch006-q09`, `ch006-q10`, `ch010-q06`, `ch010-q07`, `ch010-q09` 的 scope/task keys。
3. 補齊本報告 `SOURCE` 清單中的直接官方文件，並移除／替換退化的 Fargate URL。
4. 重寫 `ch004-q10`, `ch005-q10`, `ch007-q05`, `ch008-q05`, `ch009-q03`, `ch010-q03`, `ch010-q05` 的 near-miss distractors。
5. 再跑題內、part 內、跨 part、legacy fallback 與 community wording duplicate checks。
6. 由非 P00-A、非 R00 的 revision reviewer 再次核准，不得由作者自行宣告 PASS。

REVISE

## Verification

重新審查日期：2026-10-01
重新審查範圍：修訂後 `part_00.json` 全部 100 題，並逐項回查本 review 原列的 38 題。

- **結構與 intent：通過。** Part 00 單獨執行 schema／題數／intent／題型／解析長度與重複選項檢查均通過；全域 checker 顯示的其他錯誤都來自 Part 06 以後，與本次 Part 00 驗證無關。
- **Chapter 1 BOOK-META：通過。** `ch001-q01`–`ch001-q10` 已統一改為 `Orientation（不計入 SAA/SAP 模擬分數）` 與 `BOOK-META`，不再把讀書方法錯掛到 SAA-C03／SAP-C02 task。
- **Well-Architected baseline：部分通過。** `ch001-q04` 已正確加入「初次 review 完成後儲存 milestone 作 baseline，改善或重大變更後再建立後續 milestone」，符合現行 Well-Architected Tool 行為。`ch010-q03` 的 distractors 與 milestone 來源也已改善，但正解 D 仍只寫「重大變更後建立 milestone」，沒有明寫初次 review 後先保存 baseline；請在 D 與解析補上初始 baseline。
- **CloudFront processing／data residency：通過。** `ch002-q10` 已將 PII API 與公開圖片拆成不同 hostname/data path；PII 直接進核准 Region，不先經 CloudFront POP，只有非敏感靜態圖片使用獨立 CloudFront distribution。解析也正確指出「不快取」不等於「未在 edge 處理」。
- **NLB／ALB health checks：通過。** `ch005-q06` 已明示 NLB，正確比較 TCP 與 HTTP `/ready` health check；`ch005-q08` 保持 ALB 的 HTTP readiness 情境，沒有再暗示 ALB 可任意使用 TCP health check。
- **ACM imported certificate renewal：通過。** `ch005-q08` 已限定為 ACM 簽發且符合 managed-renewal eligibility 的 public certificate，並明確說 imported certificate 不會由 ACM 自動續期。
- **S3 Express append／`RenameObject`：通過。** `ch006-q10` 已反映 directory bucket 支援受限制 append 與單一 object、metadata-only atomic `RenameObject`；正解改以「仍缺少完整 POSIX file-descriptor、任意 in-place mutation、原子目錄樹與 locking contract」作為真正邊界。
- **No-data-loss／RPO：通過。** `ch008-q08` 已把要求改成可驗證的 durable commit、單一 AZ 故障邊界與誤刪 RPO ≤ 5 分鐘，並區分同步 Multi-AZ HA、commit acknowledgement、隔離 backup/PITR 與前端 elasticity。
- **原列 task mappings：通過。** `ch003-q10`、`ch005-q09`、`ch005-q10`、`ch006-q09`、`ch006-q10`、`ch010-q06`、`ch010-q07`、`ch010-q09` 均已改到符合實際能力面的 task key。
- **原列 distractor rigor：通過。** `ch004-q10`、`ch005-q10`、`ch007-q05`、`ch008-q05`、`ch009-q03`、`ch010-q03`、`ch010-q05` 已改成同 domain 的 near-miss，不再以明顯無關服務湊選項。
- **大多數 provenance 修訂：通過。** Fargate、Lambda execution role/API Gateway/VPC、RDS Proxy/SQS、Savings Plans、NAT、NLB health checks、ACM renewal、FSx、S3 Express、DMS 與 SLI/SLO 的直接官方來源已補入；Part 00 的 93 個來源 URL 本輪均可成功開啟。
- **`ch004-q02` provenance：未通過。** 題目測 `/16` 切 `/20` 與 AWS subnet 保留位址，但 `source_ids` 沒有引用已建立的 `aws-vpc-subnet-sizing`，反而誤掛 `aws-tgw-route-tables`、`aws-vpn-routing`、`aws-tgw-appliance-mode`。請保留 `aws-vpc-guide`、加入 `aws-vpc-subnet-sizing`，並移除三個不相關來源。
- **`ch004-q04` provenance：未通過。** 題目測 TGW/VPN 去回程與 stateful inspection 對稱路徑，卻仍只引用 `aws-vpc-guide`。請把目前誤掛在 `ch004-q02` 的 `aws-tgw-route-tables`、`aws-vpn-routing`、`aws-tgw-appliance-mode` 移到本題。

尚需精確修訂：

1. `ch010-q03`：正解 D 與解析加入初次 review 後的 baseline milestone。
2. `ch004-q02`：改用 `aws-vpc-subnet-sizing`，移除 TGW/VPN/appliance sources。
3. `ch004-q04`：加入 `aws-tgw-route-tables`、`aws-vpn-routing`、`aws-tgw-appliance-mode`。

REVISE

## Final Verification

最終驗證日期：2026-10-01

- `ch010-q03`：通過。正解 D 與其解析均明確寫出「初次 review 完成後先保存 baseline milestone」，並說明重大變更或改善完成後再建立後續 milestone。
- `ch004-q02`：通過。`source_ids` 恰為 `aws-vpc-guide`、`aws-vpc-subnet-sizing`；已移除 `aws-tgw-route-tables`、`aws-vpn-routing`、`aws-tgw-appliance-mode`。
- `ch004-q04`：通過。`source_ids` 已包含 `aws-vpc-guide`、`aws-tgw-route-tables`、`aws-vpn-routing`、`aws-tgw-appliance-mode`。
- 本輪僅讀取 `part_00.json`，未修改題庫。

VERIFIED
