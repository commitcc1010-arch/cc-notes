# Part 10 independent review

審查範圍：`tools/aws_question_banks/part_10.json`，第 97–104 章，共 80 題。
審查基準日期：2026-10-01。
基準來源：AWS 官方 SAA-C03、SAP-C02 exam guide、官方 sample 的題型風格，以及各服務當期官方文件。社群文章只可作主題靈感，不作答案依據。本次未使用 dumps，也未發現直接重製官方 sample 或可辨識真題的文字。

## 總結

- 題型結構完整：64 題單選、16 題複選；每題都有四個或五個選項，正解數量和「選兩項」指示一致，每個選項也都有解析。
- 第 97、100、101、103 章的大部分架構判斷正確；第 104 章對 AgentCore Identity、Policy、Guardrails、human approval、STS session 與冪等性的責任邊界，大方向也正確。
- 目前仍不能發布。存在 API 限制不成立、隔離方案缺少必要條件、Vault Lock mode 含糊、失效的官方 deep link、考綱映射錯誤、來源不足，以及可從固定模板猜答案等問題。

## 考試版本與 enrichment 邊界

截至 2026-10-01，可核對的正式官方版本仍是 SAA-C03 與 SAP-C02；本次未找到可用來正式映射題目的 AWS 官方 SAP-C03 exam guide 或 sample。不得自行把題目標成 SAP-C03。

SAP-C02 guide 的 Emerging Topics 明確說明：考試可能包含 5 題不計分的 emerging-topic questions，而且列出 Amazon Bedrock AgentCore、AgentCore Identity、AgentCore Policy、Bedrock Guardrails 與 Step Functions human oversight。這能支持第 104 章作為 enrichment／unscored preparation，但 Emerging Topics 不是正式 task ID，也不能暗示這十題都是 SAP-C02 的計分範圍。

## 必須修正

### 1. 第 104 章全部使用不存在的 task key

題號：`ch104-q01`–`ch104-q10`

問題：

- 十題都含有 `SAP-C02-Emerging`，但 `TASKS` 與 SAP-C02 exam guide 均沒有這個 task ID。
- `python3 tools/check_aws_question_banks.py --part 10` 因此直接回報 10 個 unknown task-key errors。
- Emerging Topics 是「可能出現、5 題、不計分」的獨立說明，不是 Domain 1–4 下的一個 task。

修法：

1. 從十題移除 `SAP-C02-Emerging`。
2. 額外使用非 task-key metadata 或章節標記，例如 `scope: "SAP-C02 emerging topic / unscored"`；正文也要明說這是 enrichment。
3. 其餘 `SAP-1.2`、`SAP-2.3` 等正式 task key 只能保留在題目確實測試該 task 的一般架構能力時，不能用它把 AgentCore 服務細節偽裝成正式計分考點。
4. 在 AWS 正式發布 SAP-C03 guide/sample 前，不得加入 SAP-C03 mapping。

### 2. 固定答案位置模板可被猜中

範圍：第 97–104 章全部。

問題：

- 第 97、98、99、101、102、103、104 章的十題答案位置完全相同：
  `2, 0, 3, 1, 0, 2, 1, 3, [0,4], [1,3]`。
- 八章的第 9 題全部是 `[0,4]`，第 10 題全部是 `[1,3]`。
- 全 part 的 A/B/C/D 總數雖不算嚴重失衡，但章內順序高度規律，考生不理解內容也能利用模板猜題。

修法：

- 對每章獨立重排選項，同步更新 `answers` 與每個 index 的 explanation。
- 重新檢查每章及全 part 的答案分布，但不要使用另一組固定輪替模板。
- 重排後以腳本確認沒有兩章共享完整十題答案序列。

### 3. S3 single PUT 敘述在檔案大小上不成立

題號：`ch099-q01`

問題：

- 題目說 80–300 GiB 的檔案使用 single PUT，而且會在上傳到 95% 時才中斷。S3 single-operation upload 的上限是 5 GB；80–300 GiB 根本不能用單次 PUT 成功進行到 95%。
- 正解 multipart upload 仍然正確，但題幹建立在不可能的現況上，會誤教 API 限制。

修法（二擇一）：

- 保留 80–300 GiB：改成「目前 client 嘗試 single PUT，立即因大小限制失敗／架構審查發現無法支援」，再問如何支援可恢復上傳；或
- 保留「95% 時中斷」：把檔案大小改成低於 single PUT 上限，再用可恢復性與平行傳輸需求導向 multipart upload。

同時加入官方 `Uploading objects`／S3 object-size constraints 的 deep link，不要只引用 multipart overview。

### 4. DynamoDB `LeadingKeys` 方案缺少 per-request principal 邊界

題號：`ch098-q02`

問題：

- 正解把 tenant ID 放入 partition-key prefix 並使用 `dynamodb:LeadingKeys`，方向正確，但題幹明說是「pooled Lambda role」。
- 如果所有租戶真的共用同一個靜態 execution role，IAM condition 本身不知道本次 request 的可信 tenant 是誰；把所有 tenant prefixes 都授權給同一 role，仍無法阻止程式錯誤或注入造成跨租戶讀取。
- `LeadingKeys` 也不是讓 `Scan` 自動變安全的功能。官方 fine-grained access 範例通常會把 key value 綁到 principal/session tag，並限制不符合 key-scoped 模型的 actions。

修法：

- 在選項與解析中補上必要條件：從已驗證 caller 建立 tenant context，為每個 request 使用可驗證的 tenant-scoped session/principal tag 或等價的 tenant-specific authorization boundary，將 `LeadingKeys` 綁到該值，並禁止／另行隔離 `Scan` 與任何不能保持 tenant key scope 的 access path。
- 如果不打算引入 per-tenant assumed session，就不要宣稱 shared pooled role 的 IAM policy 已形成完整的強隔離；應明確說明 application authorization 仍是必要邊界。

### 5. Vault Lock 必須區分 governance 與 compliance mode

題號：`ch100-q06`

問題：

- 題目要求 privileged admin 在 retention 期間也不能刪除 recovery point。
- 正解只說「使用受保護 vault 與 Vault Lock」，沒有指定 mode。Governance mode 可由有足夠 IAM 權限的使用者移除 lock；題目要求對應的是 Compliance mode，且必須理解 grace time 結束後的不可逆性。

修法：

- 正解改為明確使用 AWS Backup Vault Lock Compliance mode，設定正確 min/max retention 與 changeable grace time；在 grace time 結束前完成 KMS、role、restore 與 retention 驗證。
- 干擾項與解析要說明 Governance mode 適合防止非預期操作，但不滿足「特權管理員也不能移除」的要求。
- 引用官方 `Vault Lock modes` deep link，而不只是一個泛用 Vault Lock 頁面。

### 6. Security Hub 名稱與 scope 要使用目前服務邊界

題號：`ch100-q07`

問題：

- 本題實際測試的是跨 Organizations 聚合 posture findings 與 delegated administrator，應使用目前官方名稱 `AWS Security Hub CSPM`，避免與新的 broader Security Hub 體驗／其他能力混稱。
- 現有正解仍合理，但 prompt、tested、source title 應精確。

修法：

- 把本題的 service name、tested 與來源改為 AWS Security Hub CSPM delegated administrator／Organizations integration。
- 保留「delegated administrator 不等於任意 workload remediation permission」的解析；這部分正確。

### 7. Kinesis 與 MSK 比較缺少 MSK 證據，且 migration task mapping 不成立

題號：`ch102-q01`

問題：

- 題目以 Kafka compatibility、clients、Connect 與 broker ecosystem 作為 Kinesis/MSK 分界，但來源只有 Kinesis API/quotas，沒有任何 MSK 官方文件。
- 題目說的是「新 IoT 平台」，沒有既有 workload migration/modernization 情境，卻映射 `SAP-4.4 Determine opportunities for modernization and enhancements`。
- 題幹要求數小時 replay，但 source list 也沒有 Kinesis retention deep link。

修法：

- 加入官方 `What is Amazon MSK?` 或 MSK developer guide 的 Kafka compatibility deep link，以及 Kinesis retention deep link。
- 移除 `SAP-4.4`；保留 `SAA-3.5`、`SAP-2.5` 即可。若要保留 4.4，必須把題幹改成既有 Kafka／legacy ingestion workload 的 modernization decision。

### 8. Raw-zone 題目的來源與 task mapping 不貼合

題號：`ch102-q05`

問題：

- `glue-catalog-crawlers` 與 `s3-lifecycle` 無法充分支持「append-only raw zone、獨立 curated zone、lineage/checkpoint」這整組架構主張。
- 題目核心是可重建性、資料完整性與 pipeline reliability；現有 `SAP-2.3 Determine security controls` 並非最直接的 mapping。

修法：

- 加入 AWS 官方 data-lake zone/reference architecture、Data Analytics Lens 或資料 lineage/reprocessing guidance 的精確 deep link。
- 將 SAP mapping 改為 `SAP-2.4` 或其他真正對應 reliability/operational recovery 的正式 task；若保留 `SAP-2.3`，題幹必須明確加入不可竄改、retention 或 data-security requirement。

### 9. Glue schema 題映射到 performance improvement 不正確

題號：`ch102-q06`

問題：

- 問題是 crawler 自動發布 breaking schema、造成 production consumers 失敗，核心是 operational excellence／reliability。
- `SAP-3.3 Determine a strategy to improve performance` 不符合本題 tested intent。

修法：

- 將 `SAP-3.3` 改成 `SAP-3.1` 或 `SAP-3.4`，並保留 `SAA-3.5`、`SAP-2.5` 中與資料處理方案相關的映射。

### 10. `agentcore-policy` 是 soft-404，不是有效 deep link

題號：`ch104-q04`、`ch104-q05`、`ch104-q06`、`ch104-q10`

問題：

- source ID `agentcore-policy` 指向
  `.../policy-example-overview.html`。它雖回 HTTP 200，但內容是通用 Amazon Bedrock AgentCore error shell，沒有對應文章 `<h1>`，不能算可驗證的官方 deep link。

修法：

- 依題目改用目前存在的官方頁面，例如：
  - `.../policy-understanding.html`
  - `.../example-policies.html`
  - `.../policy-common-patterns.html`
- `ch104-q06` 若要支持 human approval，除 Step Functions callback 文件外，應加入 SAP-C02 guide 的 Emerging Topics 說明或當期 AgentCore human-in-the-loop 官方 guidance。

### 11. Agent observability 題缺少 AgentCore trace/tool telemetry 來源

題號：`ch104-q10`

問題：

- 正解同時主張 tool outcome、trace ID、latency/error/token metrics 與成本歸屬。
- 現有 `bedrock-runtime-metrics` 和 model invocation logging 主要支持 Bedrock model inference；它們不足以支持 AgentCore runtime/tool trace 的完整敘述。

修法：

- 加入目前 AgentCore Observability 的精確官方 deep link，並在解析中區分：
  - AgentCore runtime/session/tool traces；
  - Bedrock model invocation logs/metrics；
  - application inference profile 的模型成本歸屬。
- 不要暗示單一 telemetry service 自動涵蓋上述三層。

### 12. Queue/concurrency 題缺少其所依賴的精確設定來源

題號：`ch097-q05`、`ch098-q05`

問題：

- 正解明確依賴 SQS event source mapping 的 maximum concurrency，但 `lambda-concurrency` 是 function reserved/provisioned concurrency 的泛用頁面，不足以證明 event-source maximum-concurrency 行為。
- 第 97 題還把 concurrency ceiling 近似為每秒 2,000 筆；實際安全速率也受 batch size、每批處理時間、retry 與 downstream latency 影響。

修法：

- 加入官方 `Configuring maximum concurrency for Amazon SQS event sources` deep link。
- 解析改成先由 batch size、服務時間與重試率估算可接受 concurrency，再以 event-source maximum concurrency／function reserved concurrency形成 ceiling；不要把 concurrent executions 直接等同 RPS。

### 13. SQS visibility timeout 題缺少直接來源

題號：`ch099-q04`

問題：

- 正解的關鍵條件是 visibility timeout 必須覆蓋正常轉碼時間，但來源只有 standard queue at-least-once 與 DLQ，沒有 visibility timeout 官方文件。

修法：

- 加入 SQS visibility timeout 的官方 deep link；補充 timeout 過短會重複交付、過長會延後失敗重試，並應和 Lambda/event-source timeout 或 worker heartbeat/change-visibility 策略協調。

### 14. MediaConvert queue 題的 source 太泛

題號：`ch099-q06`

問題：

- 正解同時依賴 queue priority、on-demand queue 與 reserved queue/capacity 的選擇，但目前只引用泛用 `Working with queues`。

修法：

- 加入 MediaConvert job priority 與 reserved queues/capacity 的精確官方 deep links。
- 解析要明確指出 priority 只比較同一 queue 中的 jobs，不會在不同 queues 間建立全域排序，也不會增加 service quota/capacity。

### 15. Observability 題錯映射到 performance task

題號：`ch099-q09`

問題：

- 本題測試 pipeline correlation、failure localization、DLQ 與 safe redrive；沒有 performance objective 或 performance improvement decision。
- `SAP-3.3` 不應只因題目提到 metrics 就加入。

修法：

- 移除 `SAP-3.3`，保留 `SAP-3.1` 與 `SAP-3.4`。

## 重複度與題目鑑別力

### 16. DR 與 fencing 題有實質重複

下列題組不是逐字相同，但正解邏輯、錯誤選項與解題步驟高度重疊：

- `ch097-q08` 與 `ch103-q04`：都是「先 promote/fence/驗證資料，再切 Route 53」。
- `ch097-q07` 與 `ch103-q06`：都是「DNS 不能保證 single writer，需 data-layer fencing」。
- `ch103-q01` 與 `ch103-q10`：都是「Tier A 用 replication/warm standby，低階 tier 用 backup/restore」。
- `ch097-q09` 與 `ch103-q10`：都以保留既定 DR objective 為條件做成本分層。

修法：

- 每組至少重寫一題，測不同的 failure boundary，而不是只換敘事。
- 可改測：Aurora managed switchover 與 unplanned failover 的差異、Global Database write forwarding 限制、Route 53 ARC routing control/readiness、backup restore throughput、quota/capacity ramp、DNS failback 的 stale connections，或 reconciliation evidence。

### 17. 部分干擾項過度荒謬，低於官方 sample 的鑑別力

題號：`ch099-q01`、`ch103-q01`、`ch103-q10`、`ch104-q01`、`ch104-q03`、`ch104-q04`、`ch104-q05`、`ch104-q08`、`ch104-q10`

問題：

- 多個選項屬於一眼即可排除的極端錯誤，例如把 administrator secret 放進 prompt、讓 KMS 做內容審查、用 cost tag 證明 authorization、所有 workload 一律 active-active。
- 這些解析雖然正確，卻沒有測到相鄰服務或相似設計的真正邊界。

修法：

- 每題至少提供兩個合理但因一個精確限制而失敗的 near-neighbor distractors。
- 例如第 104 章可比較：AgentCore Policy 與 IAM 的 enforcement point、Guardrails 與 Automated Reasoning checks、user-delegated OAuth 與 M2M、Bedrock invocation logging 與 AgentCore Observability、Step Functions callback 與 Activities／Express workflow 限制。
- 新干擾項的解析必須指出錯在 scope、availability、identity、consistency、quota 或 execution semantics，不要只說「不安全」。

## 已通過的檢查

- `single` 題皆為 4 選 1；`multi` 題皆為 5 選 2，題幹有明示選兩項。
- 未發現不存在的 `source_id`；除了 `agentcore-policy` soft-404 外，其餘官方 URL 在本次檢查可存取。
- 每個 choice index 都有 explanation，且正解與解析的正反標示一致。
- 未發現完全相同的 prompt 或 tested string，也未發現直接複製官方 sample／公開 dump 的跡象。
- `ch099-q10` 使用 MediaConvert 並把 Elastic Transcoder 視為 2025-11-13 結束支援的 legacy 選項，符合 2026 新架構邊界。
- `ch104-q01` 將 Bedrock Agents Classic 視為 maintenance mode、既有客戶可繼續使用而新設計採 AgentCore，符合當期官方文件；需要修的是 exam-scope 標示與答案模板，不是這個服務判斷。
- 其餘未列出的題目，在此次逐題檢查中未發現會改變正解的 AWS 事實錯誤。

REVISE

## Verification

重新審查日期：2026-10-01。只檢查修訂後的 `part_10.json`，未修改題庫。所有晚於本日的日期均未當成既有事實；未找到且未使用尚未發布的 SAP-C03 exam guide/sample。

### 已確認修正

- Task keys：`SAP-C02-Emerging` 已從 `ch104-q01`–`ch104-q10` 全部移除；`python3 tools/check_aws_question_banks.py --part 10` 現已通過。十題改用獨立 `scope` 明確標示為 SAP-C02 Emerging Topics enrichment／unscored preparation，並明說不宣稱 SAP-C03 或計分範圍。剩餘正式 task keys 均存在，且與題目的安全、可靠性、成本或 modernization 能力相符。
- S3 題幹：`ch099-q01` 已改成架構審查發現 80–300 GiB 不可用 single `PutObject`，不再描述不可能發生的 95% single-PUT upload。正解仍是 multipart upload，選項與解析已同步。
- DynamoDB tenant boundary：`ch098-q02` 已補入可信 tenant context、tenant-scoped session/principal tag、`dynamodb:LeadingKeys`，並明確禁止或隔離 `Scan` 等不能維持 key scope 的路徑；不再把列出所有租戶前綴的共用靜態 role 說成完整隔離。
- Vault Lock：`ch100-q06` 已明確選擇 Compliance mode，說明 min/max retention、grace time、不可移除邊界，以及 Governance mode 可被具權限管理員移除。
- CSPM：`ch100-q07` 的 prompt、tested、source title 與解釋均已改為 AWS Security Hub CSPM delegated administrator，且仍正確區分 delegated administration 與 workload remediation permissions。
- Sources：SQS maximum concurrency、SQS visibility timeout、MediaConvert job priority/reserved queues、MSK、Kinesis retention、data-lake zones、AgentCore Cedar/policy patterns 與 AgentCore Observability 均已補入可用的官方 deep links；舊 `agentcore-policy` soft-404 已移除。
- Task mapping：`ch102-q01` 已移除不成立的 `SAP-4.4`；`ch102-q05` 改為 reliability/data-pipeline mapping；`ch102-q06` 改為 `SAP-3.4`；`ch099-q09` 已移除 `SAP-3.3`。
- 重複：原先列出的 DR/fencing 重複均已改成不同考點：planned switchover、Route 53 ARC safety rules、restore throughput、Aurora write forwarding。未發現完全重複 prompt/tested，也沒有兩章再使用相同的完整十題答案序列。
- Distractors：原列 `ch099-q01`、`ch103-q01`、`ch103-q10` 與第 104 章題目已改為較可信的 near-neighbor choices，解析能指出 scope、identity、consistency、capacity 或 enforcement-point 差異。
- Current availability：MediaConvert／Elastic Transcoder 邊界和 Bedrock Agents Classic maintenance-mode 敘述截至本日仍合理；未使用 2026-10-01 之後的發布資訊。

### 尚未通過

1. 答案雖已解除跨章固定序列，但第 97 章仍有明顯位置偏差。

   - 八題單選中，`ch097-q01`、`q02`、`q03`、`q06`、`q07`、`q08` 六題正解都是 index `0`；沒有任何單選正解位於 index `1`。
   - 全 part 的單選／複選位置總數大致平衡，且章節完整序列不再重複；問題是第 97 章內形成兩段連續的 A/A/A 模式，仍可被利用。
   - 請只重排上述題目的部分 choices，同步調整 `answers` 與 index-based explanations，使第 97 章不要由 6/8 單選集中在同一位置。
   - 第 102 章兩題複選 `ch102-q09`、`ch102-q10` 仍同為 `[1,2]`；建議至少重排其中一題，避免章尾再次形成固定 pair。

2. `ch099-q01` 的題幹已修正，但新增來源仍未直接支持 5 GB single-operation limit。

   - `s3-put-object` 指向 `API_PutObject.html`；目前該頁可存取，但正文沒有列出 `5 GB` single-PUT 上限。
   - 請加入實際明載此限制的 AWS 官方 deep link，例如
     `https://docs.aws.amazon.com/AmazonS3/latest/userguide/upload-objects.html`
     或 AWS S3 FAQ。保留 `PutObject` API source 可作 API 語意來源，但不能單獨標成 upload-size constraint 證據。

3. `ch102-q09` 的 Athena workgroup source 已失效為 deep link。

   - `athena-workgroups` 目前指向
     `https://docs.aws.amazon.com/athena/latest/ug/workgroups.html`，實際會重導到只有導覽殼層的 Athena User Guide 首頁，沒有 workgroup 內容。
   - 請改為目前有效的官方頁面：
     `https://docs.aws.amazon.com/athena/latest/ug/workgroups-manage-queries-control-costs.html`
     或
     `https://docs.aws.amazon.com/athena/latest/ug/manage-queries-control-costs-with-workgroups.html`。
   - 題目正解「用 workgroups 分離 workload、限制掃描量、發布 metrics 與控制成本」本身仍正確；需修的是來源。

REVISE

## Final Verification

最終驗證日期：2026-10-01。只讀取修訂後的 `tools/aws_question_banks/part_10.json`；未修改題庫，也未將任何 2026-10-01 之後的資訊或尚未發布的 SAP-C03 guide 當作既有事實。

- 第 97 章答案位置已修正。八題單選目前依序為 `[1, 2, 3, 3, 2, 1, 0, 2]`，分布為 index 0：1 題、index 1：2 題、index 2：3 題、index 3：2 題；不再出現 6/8 集中於 index 0 或連續 A/A/A 模板。
- `ch102-q09` 與 `ch102-q10` 的複選答案已分別改為 `[1,2]` 與 `[0,3]`，不再使用相同 pair；choices、answers 與逐項 explanations 一致。
- `ch099-q01` 已引用 `s3-upload-objects`：
  `https://docs.aws.amazon.com/AmazonS3/latest/userguide/upload-objects.html`。該官方頁明確記載 single PUT 單次最多 5 GB，並說明大型物件應使用 multipart upload；因此 80–300 GiB 題幹已有 claim-level 官方依據。
- `ch102-q09` 的 `athena-workgroups` 已改為：
  `https://docs.aws.amazon.com/athena/latest/ug/workgroups-manage-queries-control-costs.html`。此 canonical AWS 文件可直接開啟，且明確支持 workload separation、access/config enforcement、query metrics 與 data-usage/cost controls。
- `python3 tools/check_aws_question_banks.py --part 10` 通過：80 題、8 章。

VERIFIED
