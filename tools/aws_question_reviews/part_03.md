# R03 獨立內容審查：Part 03（第 32–40 章）

- 審查日期：2026-10-01
- 審查範圍：`tools/aws_question_banks/part_03.json` 全部 90 題
- 對照規格：`tools/aws_question_banks/README.md`、`tools/aws_exam_audits/part_03.md`
- 對照舊題：`tools/aws_architect_deep_content.py` 的 legacy fallback
- 結論：**REVISE**

## 執行摘要

這份題庫的整體方向明顯優於舊 fallback：題幹有 workload constraint、答案位置分散、各章 intent 1–10 完整，而且沒有再使用「服務功能較多」「全部部署」「managed service 自動理解需求」等舊模板。90 題中，多數題目的核心答案可以成立。

目前仍不能發布，原因分成四類：

1. **會改變答案的 factual/current-state 問題**：Dedicated Host 與 Capacity Reservation、ALB fail-open、AWS Batch compute environment、API Gateway quota/WAF 邊界、App Runner 新客戶可用性等。
2. **來源無法做 claim-level 查證**：95 個被引用的官方 source records 只連到整本 Developer Guide 根目錄；source title 也是自動組成的 guide 名稱加 source id，不符合 README 所要求的 exact title/provenance。
3. **27 題至少有一個 explanation 只下結論，沒有解釋 service contract、成立條件或替代方案**。
4. **數題 distractors 過度荒謬或跨層級**，對 SAA/SAP 鑑別度不足。

## 結構、覆蓋與原創性

| 檢查項目 | 結果 | 說明 |
|---|---:|---|
| 題數 | PASS | 第 32–40 章各 10 題，共 90 題。 |
| Intent | PASS | 每章依序包含 intent 1–10，與 audit 主題相符。 |
| 題型 schema | PASS | 72 題單選、18 題五選二；choices、answers、explanations 數量相符。 |
| 答案位置 | PASS | 各章答案分布沒有集中到單一選項。 |
| Task keys | PASS | 所有 task keys 都存在，SAA/SAP level 也有同系列 task mapping。 |
| Source id 完整性 | PASS | 每題引用的 source id 都存在，且至少有 AWS 官方來源。 |
| Source 精確度 | FAIL | 106 個被使用的 official source ids 中，95 個只指向 guide 根目錄，無法定位支持哪一句 service behavior。 |
| Community provenance | PASS | 只使用 7 個 Jayendra Patil 公開文章作 topic/distractor inspiration；沒有 ExamTopics、dump、recalled-live-exam 或「actual questions」來源。 |
| 舊 fallback 重複 | PASS | 對 90 個新 prompt 與第 32–40 章舊 fallback 比對，最高相似度 0.377，沒有 exact/near duplicate；新題內也沒有高度重複 prompt。 |
| 可疑抄寫 | PASS（合理查核範圍內） | 題目以原創中文 scenario 重寫，沒有發現與 source title、舊題或常見 dump wording 的直接重合。 |

### 規格衝突

`README.md` 要求每章至少 7 題單選、至少 2 題複選；`part_03.md` 最後的 implementation acceptance criteria 卻寫「第 10 題五選二，其他九題四選一」。本 bank 採每章 8 單選＋2 複選，符合 README、但不符合 audit 最後一句。

這是中央規格衝突，不應由 revision agent 任意猜測。請由 maintainer 決定以 README 為準，或把 `ch032-q09` 至 `ch040-q09` 改回單選；建議更新 audit，使其與全域 README 一致。

## 必須修正的 factual / answer-set 問題

### `ch032-q06`：T3 credit mode 未指定，觀察結果不唯一

題幹只說 `t3.small` 長期 80% CPU、吞吐下降，但沒有說明是 Standard 還是 Unlimited mode。Standard mode 在 credits 用盡後會回到 baseline；Unlimited mode 可以用 surplus credits 維持超過 baseline 的效能並產生額外費用。現有答案同時混用「效能下降」與「重新估算 unlimited 成本」，因此不能從題幹唯一推出。

Required action：

- 明確指定 Standard mode，答案聚焦 `CPUCreditBalance` 用盡與 baseline throttling；或
- 明確指定 Unlimited mode，移除「吞吐下降必然由 credits 引起」，改問 `CPUSurplusCreditBalance`、`CPUSurplusCreditsCharged` 與長期成本；並修正 metric 的完整名稱。
- 至少兩個 distractors 改成相鄰且可能成立的選項，例如切換 Unlimited、改固定性能 family、scale out，而不是 EBS/placement group 類別錯誤。

官方依據：

- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances-standard-mode.html
- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances-unlimited-mode.html

### `ch032-q09`：Dedicated Host 與 On-Demand Capacity Reservation 不能如此組合

答案 B 要求 `host` tenancy 的 Dedicated Hosts；答案 D 的 On-Demand Capacity Reservation 支援 `default` 或 `dedicated` tenancy，不是 Dedicated Host 的 `host` tenancy。D 不能被描述成與 B 相容的第二個獨立容量保證。

Required action（二選一）：

- 保留 socket/core visibility：答案改成先在指定 AZ 配置足夠且相容的 Dedicated Hosts，按每 host 可容納的 instance 數量計算 capacity；不要再把 ODCR 當成 host capacity。
- 保留 ODCR：移除需要 host socket/core visibility 的條件，改成適用 `default`/`dedicated` tenancy 的 workload。

官方依據：

- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/capacity-reservations-considerations.html
- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/dedicated-hosts-overview.html
- https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ComputeReservation.html

### `ch035-q06`：把「全部 unhealthy」直接映射成 503，忽略 ALB fail-open

ALB target group 若所有 registered targets 都 unhealthy，會 fail open，仍把 request 送往所有 targets；503 比較可靠的條件是 target group 沒有 registered targets，或 registered targets 全在 `unused` 狀態。題幹的「沒有 healthy targets」同時涵蓋這兩種不同結果，因此答案 B 不唯一。

Required action：

- 把第一個現象改成「target group 沒有 registered targets／targets 都是 unused」，才對應 503；或
- 題目明確測 fail-open，將「全部 unhealthy」對應到仍可能路由至 unhealthy targets。
- 解析需分開寫「target health 狀態」與「client 所見 HTTP status」，不能視為一對一。

官方依據：

- https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html
- https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-troubleshooting.html

### `ch037-q04`：Usage plan quota 不是 hard limit

API Gateway usage-plan throttling 與 quota 是 best effort。若「限制每個 partner quota」代表 billing、entitlement 或不可超過的硬限制，現有 C 不完整；還需要 application/backend 端的 durable metering 與 authorization。

Required action：

- 題幹明確寫「best-effort traffic shaping/metering」；或
- 保留 hard quota 要求，答案加入 backend counter/entitlement enforcement。
- 解析要明確說 API key 不是 authentication，usage-plan quota 也不應作成本或權限的唯一控制。

官方依據：

- https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html

### `ch037-q10`：WAF 與 usage-plan 能力沒有綁定 API type

現題把 authorizer、stage/account throttling、usage plans 與「WAF rate controls」放在同一答案，但沒有說 API 是 REST API 還是 HTTP API。API Gateway usage plans/API keys 是 REST API 能力；AWS WAF 直接關聯的 API Gateway resource 也是 REST API stage。HTTP API 若要 WAF，通常需要在前面放 CloudFront 等受支援入口。

Required action：

- 題幹指定「Regional REST API」，保留 usage plan 與直接 WAF association；或
- 題幹保留 generic Internet API，答案分支說明 HTTP API 需使用相容的 edge/WAF 架構。
- 同時註明 usage-plan quota 是 best effort，真正 downstream protection 還需 Lambda reserved concurrency/backpressure。

官方依據：

- https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html
- https://docs.aws.amazon.com/waf/latest/developerguide/waf-chapter.html

### `ch038-q10`：Scanning 與 immutability 不等於「已核准才可部署」

Tag immutability 防止 tag 被覆寫，scanning 產生 vulnerability findings；兩者本身都不會阻止未經核准的 image 被部署。現有 B 只有「release 記錄」而沒有 enforceable admission/deployment gate。

Required action：

- 加入 image signing（AWS Signer/ECR managed signing 或同等機制）與 CI/CD policy gate，部署時驗證 signature、scan severity 與 digest allowlist。
- 保留 digest pinning、replication 與目標 Region pull test，但解析要把 artifact identity、vulnerability evidence、approval enforcement 分成三層。

官方依據：

- https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-tag-mutability.html
- https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html
- https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-signing.html

### `ch039-q02`：單一 Batch compute environment 不能同時是 EC2 與 SPOT type

AWS Batch managed compute environment 的 compute resource `type` 是 `EC2`、`SPOT`、`FARGATE` 或 `FARGATE_SPOT` 之一。若同一 job queue 要同時有 On-Demand 與 Spot，應關聯不同 compute environments 並設定 order，而不是說一個 compute environment「同時允許 EC2 與 Spot」。

Required action：

- 題幹改成「job queue 關聯一個 SPOT CE 與一個 EC2 CE」；或只保留單一 type。
- 答案 C 改成 scheduler 依 queue priority、dependency、CE order 與 compatible capacity placement。
- 答案 B 解析不要說「compute environment 可配置 EC2/Spot/Fargate」而讓讀者誤以為同一 CE 可混用。

官方依據：

- https://docs.aws.amazon.com/batch/latest/userguide/compute_environments.html
- https://docs.aws.amazon.com/batch/latest/APIReference/API_ComputeResource.html
- https://docs.aws.amazon.com/batch/latest/userguide/job_queue_compute_environments.html

### `ch039-q05`：不要保證 Batch job 一定收到可用的 Spot graceful signal

Checkpoint 與 retry 的方向正確，但「收到 interruption notice 就捕捉 termination signal」寫得像 AWS Batch 對所有執行型態都保證同一 application signal。可靠設計不能只賭最後兩分鐘的通知或 signal。

Required action：

- 改成定期 checkpoint、縮小 job unit、設 retry strategy；若 runtime 確實把 SIGTERM/interruption event 傳入 container，再把它當額外的 final checkpoint 機會。
- 解析加入「interruption notice 不是 durable recovery mechanism」。

官方依據：

- https://docs.aws.amazon.com/batch/latest/userguide/bestpractice9.html
- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html

### `ch039-q07`：Spot 敘述必須只套用到 EMR on EC2

答案把「transient EMR cluster 或 EMR Serverless」與「diversified Spot」接在同一句，容易讓讀者以為 EMR Serverless 可選 Spot。Spot fleet/instance group 是 EMR on EC2 的 capacity 選項；EMR Serverless 使用其 managed capacity/pricing model。

Required action：

- 明確拆成：EMR on EC2 transient cluster 的 task/core capacity 可評估 diversified Spot；EMR Serverless 不使用使用者選定的 Spot purchase option。
- 增加 workload startup、pre-initialized capacity、job duration與 operational control 的翻轉條件。

官方依據：

- https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-instances-guidelines.html
- https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/what-is-emr-serverless.html

### `ch039-q10`：On-Demand fallback 需要具體 Batch topology

「保留必要 On-Demand fallback」本身合理，但沒有交代它不是 SPOT CE 裡的一個開關。讀者需要知道要建立另一個 `EC2` compute environment，關聯到 job queue，設定 order/策略並驗證容量不足時的 scheduler 行為。

Required action：

- 在 B 與解析加入「多樣化 SPOT CE＋獨立 EC2 On-Demand CE，兩者關聯到 queue」。
- 不要把 fallback 描述成任何 Spot request 都保證立即轉成 On-Demand；deadline-sensitive job 還要有 queue、priority、quota 與容量測試。

官方依據：

- https://docs.aws.amazon.com/batch/latest/userguide/job_queue_compute_environments.html
- https://docs.aws.amazon.com/batch/latest/userguide/spot_fleet_IAM_role.html

### `ch040-q01`、`ch040-q08`：App Runner 已不對新客戶開放

截至本審查日期，AWS App Runner 已停止接受新客戶。`ch040-q08` 把 App Runner 當作新團隊的無條件首選，`ch040-q01` 也未提供「帳號已是既有 App Runner 客戶」條件，因而不是 2026-10-01 可普遍執行的答案。

Required action：

- 若保留 App Runner 機制題，題幹必須明確寫「既有 App Runner customer/account」，並標為 existing-customer/enrichment。
- 新 workload 選型題應換成目前可供新客戶採用的服務組合，再按 container、host control、autoscaling、TLS 與操作負擔決勝。
- `ch040-q08` 必須重寫答案集合，不能只在 explanation 補註。

官方依據：

- https://docs.aws.amazon.com/apprunner/latest/dg/what-is-apprunner.html
- https://aws.amazon.com/apprunner/

### `ch040-q10`：`service role` 不是 application 存取私有資料庫的通用身分

App Runner 存取 AWS APIs 的 application identity 是 instance role；從 ECR 部署時另有 access role。Elastic Beanstalk application 通常使用 EC2 instance profile。現有 E 把這些都寫成 `service role/secret access`，會讓初學者混淆 control-plane role 與 runtime principal。

Required action：

- 分別說明 App Runner instance role、ECR access role、Beanstalk EC2 instance profile。
- Network reachability（subnet/routes/SG/NAT/endpoints）、database authentication、Secrets Manager/KMS authorization 要分開列出。

官方依據：

- https://docs.aws.amazon.com/apprunner/latest/dg/security_iam_service-with-iam.html
- https://docs.aws.amazon.com/apprunner/latest/dg/manage-access.html
- https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/concepts-roles.html

## App Runner 的 exam scope / current-state 標示

以下題目的機制在既有 App Runner 客戶仍有教學價值，但都應標記為 **existing-customer / enrichment**，不能讓讀者誤以為它是 2026 年新架構的預設選項：

- `ch040-q01`
- `ch040-q02`
- `ch040-q03`
- `ch040-q05`
- `ch040-q06`
- `ch040-q07`
- `ch040-q08`
- `ch040-q10`

`ch040-q01` 與 `ch040-q08` 需要改答案；其餘題目至少要補 scope/current-state badge。SAA-C03/SAP-C02 題庫應把主要分數放在 exam guide 明確涵蓋、且新客戶仍可採用的 architecture decisions；App Runner 可留作 abstraction comparison，不應佔本章八題。

## Explanation 未達 substantive level

下列 27 題至少有一個 option explanation 只有簡短斷言，沒有指出具體 service contract、為何不滿足題幹，或在哪個條件下會成為合理選項：

- `ch034-q08`
- `ch036-q03`
- `ch036-q05`
- `ch036-q09`
- `ch036-q10`
- `ch037-q05`
- `ch037-q06`
- `ch037-q07`
- `ch037-q08`
- `ch037-q09`
- `ch037-q10`
- `ch038-q02`
- `ch038-q05`
- `ch038-q06`
- `ch038-q07`
- `ch039-q01`
- `ch039-q02`
- `ch039-q03`
- `ch039-q05`
- `ch039-q06`
- `ch039-q07`
- `ch039-q09`
- `ch039-q10`
- `ch040-q05`
- `ch040-q07`
- `ch040-q08`
- `ch040-q09`

Required action：

- 每個短 explanation 至少補上「違反哪個 constraint／service mechanism」。
- 對 plausible alternative 補「在什麼改題條件下它會變正確」。
- 不要只寫「不是需求」「會失敗」「成本較高」；應具體說明 identity、network、state、quota、lifecycle 或 billing boundary。

## Distractor 鑑別度不足

以下題目有兩個以上明顯跨層級或荒謬選項，初學者不需理解核心機制也能排除：

| Question | 問題 | Required action |
|---|---|---|
| `ch032-q06` | EBS、detailed monitoring、placement group 都不是 CPU credit 的相鄰方案。 | 改成 Standard/Unlimited、M/T/C family、scale-out、credit cost 等真正會競爭的選項。 |
| `ch033-q08` | SG 控制 volume deletion、instance store terminate 後保留，都是類別錯誤。 | 比較 launch-template block mapping、API launch override、ASG lifecycle/backup 之間的差異。 |
| `ch034-q02` | ALB listener 建 EC2 並寫 AMI 過度荒謬。 | 改成 EC2 Fleet、launch template、ASG policy/alarm 責任邊界。 |
| `ch037-q03` | API key 數量與 CORS 幾乎沒有診斷迷惑性。 | 改成 Gateway overhead、authorizer latency、Lambda duration、integration saturation 等可觀察選項。 |
| `ch038-q04` | Public ECR 取得 DynamoDB 權限、SG 授權 API action 過度簡單。 | 用 task role、execution role、EC2 instance profile、repository policy 的相鄰邊界設計選項。 |
| `ch039-q06` | Route 53 TTL 與 ALB health path 與 Spark 完全無關。 | 用 data skew、executor memory overhead、shuffle partition、Spot executor loss、S3 layout 等真正診斷分支。 |
| `ch040-q03` | VPC connector 數量與 image size 不是 autoscaling 的合理候選。 | 比較 `MaxConcurrency`、`MinSize`、`MaxSize` 與 latency/throughput trade-off；並加 existing-customer scope。 |

## Source provenance 必須全體補強

適用 question IDs：**`ch032-q01` 至 `ch040-q10` 全部 90 題**。

目前多數 source records 只有類似下列內容：

- title：`Amazon API Gateway Developer Guide — apigw-auth`
- URL：`https://docs.aws.amazon.com/apigateway/latest/developerguide/`

這只能證明「可能在這本 guide 裡」，不能支持題目的特定 assertion。Revision agent 必須：

1. 將 title 改成官方頁面的真實標題。
2. URL deep-link 到實際章節，例如 usage plans、target-group health checks、reserved concurrency、ECR endpoints。
3. 一題若同時聲稱兩個獨立機制，加入兩個精確 sources，不要只靠 exam guide。
4. Exam guide 只支持 scope/task mapping，不能單獨支持產品行為。
5. Community source 只保留 inspiration metadata；所有答案判定仍以官方文件為準。

## 逐題 disposition

下表的 `OK*` 代表核心答案成立，但仍需完成上面的全體 source deep-link 修正。`REVISE` 代表另有題目內容、scope、解析或 distractor 動作。

### 第 32 章

| ID | 結果 | 說明 |
|---|---|---|
| `ch032-q01` | OK* | Memory-bound evidence 足以唯一選 memory optimized＋benchmark。 |
| `ch032-q02` | OK* | AMI 與 launch-time contract 分界正確。 |
| `ch032-q03` | OK* | Network/EBS instance ceiling 診斷方向成立。 |
| `ch032-q04` | OK* | Cluster placement group 與單 AZ trade-off 正確。 |
| `ch032-q05` | OK* | System status check 與 guest/application failure 分界可成立。 |
| `ch032-q06` | REVISE | 未指定 Standard/Unlimited；metric 名稱與 distractors 也需修正。 |
| `ch032-q07` | OK* | Baseline commitment、Spot burst、On-Demand gap 的組合成立。 |
| `ch032-q08` | OK* | 三種 placement strategy 對應正確。 |
| `ch032-q09` | REVISE | Dedicated Host 與 ODCR tenancy 不相容，現答案集合不成立。 |
| `ch032-q10` | OK* | Versioned AMI/template、wave、alarm/rollback 合理。 |

### 第 33 章

| ID | 結果 | 說明 |
|---|---|---|
| `ch033-q01` | OK* | Durable block state 與 ephemeral scratch 分界清楚。 |
| `ch033-q02` | OK* | EBS volume AZ scope、snapshot Region scope 與 cross-Region copy 正確。 |
| `ch033-q03` | OK* | 同時檢查 volume 與 instance EBS limits 正確。 |
| `ch033-q04` | OK* | gp3/io2 與 HDD distractors 的 workload mapping 成立。 |
| `ch033-q05` | OK* | Application-consistent snapshot 需要 quiesce/checkpoint。 |
| `ch033-q06` | OK* | Instance store lifecycle 解釋正確。 |
| `ch033-q07` | OK* | Rightsizing、orphan cleanup、archive、restore test 方向成立；精確來源須補 archive retrieval/minimum-duration 限制。 |
| `ch033-q08` | REVISE | 答案正確，但 distractors 鑑別度過低。 |
| `ch033-q09` | OK* | Snapshot copy、KMS、FSR/初始化與 RTO 關係成立。 |
| `ch033-q10` | OK* | Backup isolation 與實際 restore evidence 能回答董事會要求。 |

### 第 34 章

| ID | 結果 | 說明 |
|---|---|---|
| `ch034-q01` | OK* | Scheduled/predictive/target tracking 對應正確。 |
| `ch034-q02` | REVISE | 核心答案正確，但 ALB 寫 AMI 等 distractor 太弱。 |
| `ch034-q03` | OK* | Backlog-per-worker 與 oldest-age evidence 適合 queue worker。 |
| `ch034-q04` | OK* | Warmup、health grace、readiness 的角色分開後可成立。 |
| `ch034-q05` | OK* | Termination lifecycle hook 適合 bounded drain/checkpoint。 |
| `ch034-q06` | OK* | Activity reason、subnet IP、quota、capacity 的診斷順序合理。 |
| `ch034-q07` | OK* | Mixed instances/Spot diversification 答案成立。 |
| `ch034-q08` | REVISE | 答案成立，但至少一個 explanation 未達 substantive level。 |
| `ch034-q09` | OK* | Fixed LT version、instance refresh、checkpoints/alarms/rollback 合理。 |
| `ch034-q10` | OK* | Scaling 與 at-least-once correctness 被分開處理。 |

### 第 35 章

| ID | 結果 | 說明 |
|---|---|---|
| `ch035-q01` | OK* | ALB traffic plane 與 ASG capacity controller 分工正確。 |
| `ch035-q02` | OK* | Listener、rule、target group、target port 與 SG flow 正確。 |
| `ch035-q03` | OK* | `RequestCountPerTarget` 比 CPU 更符合題目 evidence。 |
| `ch035-q04` | OK* | Public ALB/private targets 與 SG reference 成立。 |
| `ch035-q05` | OK* | Deregistration delay 需搭配 application/lifecycle draining。 |
| `ch035-q06` | REVISE | 忽略 all-unhealthy fail-open；503 條件需重寫。 |
| `ch035-q07` | OK* | 先找 LCU 主導維度，再以 edge cache/payload 優化合理。 |
| `ch035-q08` | OK* | Stickiness 不是 session durability；外部化 state 正確。 |
| `ch035-q09` | OK* | Blue/green target groups、weighted shift、business alarms 成立。 |
| `ch035-q10` | OK* | Multi-AZ headroom 與 application-aware health 是互補答案。 |

### 第 36 章

| ID | 結果 | 說明 |
|---|---|---|
| `ch036-q01` | OK* | Lambda 與 persistent container workload 邊界正確。 |
| `ch036-q02` | OK* | Execution environment reuse 只能作 optimization，不是 correctness。 |
| `ch036-q03` | REVISE | 答案可成立；補強 DLQ distractor explanation。 |
| `ch036-q04` | OK* | Provisioned 與 reserved concurrency 責任分界正確。 |
| `ch036-q05` | REVISE | Partial batch 答案正確；兩個 explanation 過短。 |
| `ch036-q06` | OK* | Concurrency budget、RDS Proxy/reuse、backpressure 合理。 |
| `ch036-q07` | OK* | Cost-per-success 與時段化 provisioned concurrency 正確。 |
| `ch036-q08` | OK* | Sync、async、poll-based retry ownership 正確。 |
| `ch036-q09` | REVISE | Canary/alias 答案成立；補強刪舊版 distractor explanation。 |
| `ch036-q10` | REVISE | 答案成立；補強 unbounded fan-out explanation。 |

### 第 37 章

| ID | 結果 | 說明 |
|---|---|---|
| `ch037-q01` | OK* | 題目 constraints 足以選 HTTP API。 |
| `ch037-q02` | OK* | Gateway authentication 與 backend resource authorization 分界正確。 |
| `ch037-q03` | REVISE | 核心診斷正確；distractors 太弱。 |
| `ch037-q04` | REVISE | Usage-plan quota 需標 best effort，hard quota 要 backend enforcement。 |
| `ch037-q05` | REVISE | Rollout 答案正確；explanations 過短。 |
| `ch037-q06` | REVISE | 429/502/504 對應可成立；需補各錯項的具體 failure contract。 |
| `ch037-q07` | REVISE | HTTP API＋cache 方向成立；explanation 未達 substantive level。 |
| `ch037-q08` | REVISE | Private REST API 答案成立；兩個 explanation 過短。 |
| `ch037-q09` | REVISE | Multi-Region 答案成立；DR 解析需補足 state/connection/DNS 邊界。 |
| `ch037-q10` | REVISE | API type、WAF association、usage-plan best-effort 與 explanation 都需修正。 |

### 第 38 章

| ID | 結果 | 說明 |
|---|---|---|
| `ch038-q01` | OK* | ECS/EKS 與 Fargate/EC2 的兩層選型正確。 |
| `ch038-q02` | REVISE | Scheduling path 正確；ALB distractor explanation 過短。 |
| `ch038-q03` | OK* | Service scaling 與 cluster capacity scaling 分層正確。 |
| `ch038-q04` | REVISE | 答案正確；應使用相鄰 IAM role distractors。 |
| `ch038-q05` | REVISE | Deployment controls 正確；至少一個 explanation 過短。 |
| `ch038-q06` | REVISE | Identity/network image-pull diagnosis 正確；至少一個 explanation 過短。 |
| `ch038-q07` | REVISE | Fargate/EC2 cost trade-off 正確；至少一個 explanation 過短。 |
| `ch038-q08` | OK* | `awsvpc`、private subnet、SG、ECR/S3 path 成立。 |
| `ch038-q09` | OK* | 先盤點 compatibility，再升 control plane/add-ons/nodes 並用 PDB/headroom，內容可成立。 |
| `ch038-q10` | REVISE | Immutability/scanning 不等於 enforceable image approval。 |

### 第 39 章

| ID | 結果 | 說明 |
|---|---|---|
| `ch039-q01` | REVISE | Service boundary 正確；至少一個 explanation 過短。 |
| `ch039-q02` | REVISE | 單一 CE 不可同時為 EC2 與 SPOT；題幹與解析需重寫。 |
| `ch039-q03` | REVISE | Placement diagnosis 正確；至少一個 explanation 過短。 |
| `ch039-q04` | OK* | Array/decomposition、timeout、`evaluateOnExit` 方向正確；可補 array-size 限制。 |
| `ch039-q05` | REVISE | 改成 periodic checkpoint＋retry，不保證所有 Batch jobs 都收到同一 signal。 |
| `ch039-q06` | REVISE | 核心診斷正確；distractors 應改成 Spark/EMR 相鄰原因，解析也需加深。 |
| `ch039-q07` | REVISE | Spot 只能套用至 EMR on EC2；Serverless 必須分開說明。 |
| `ch039-q08` | OK* | Step Functions orchestration 與 EMR execution 分界清楚。 |
| `ch039-q09` | REVISE | Multi-account 原則成立；至少一個 explanation 過短。 |
| `ch039-q10` | REVISE | On-Demand fallback topology 與多個 explanations 都需補強。 |

### 第 40 章

| ID | 結果 | 說明 |
|---|---|---|
| `ch040-q01` | REVISE | App Runner 新客戶不可用；答案需加 existing-customer 條件或改服務。 |
| `ch040-q02` | REVISE | 機制正確，但 App Runner 須標 existing-customer/enrichment。 |
| `ch040-q03` | REVISE | 機制可成立；補 current-state scope 並提高 distractor 鑑別度。 |
| `ch040-q04` | OK* | Beanstalk immutable/traffic splitting 選型成立；精確來源須補 load-balanced environment 限制。 |
| `ch040-q05` | REVISE | Health/draining 原則成立；App Runner scope 與短 explanation 需修正。 |
| `ch040-q06` | REVISE | VPC connector outbound/NAT 邏輯成立；加 existing-customer scope。 |
| `ch040-q07` | REVISE | TCO 原則成立；加 existing-customer scope並補 explanation。 |
| `ch040-q08` | REVISE | 新團隊不能把 App Runner 當普遍可用首選；答案集合必須重寫。 |
| `ch040-q09` | REVISE | Modernization 答案成立；補強 Lambda distractor explanation。 |
| `ch040-q10` | REVISE | App Runner scope與 runtime IAM role 名稱不精確。 |

## Revision 完成條件

Revision agent 必須完成以下全部項目，才可重新送審：

1. 修正本報告列出的 13 組 factual/current-state 題目：
   - `ch032-q06`
   - `ch032-q09`
   - `ch035-q06`
   - `ch037-q04`
   - `ch037-q10`
   - `ch038-q10`
   - `ch039-q02`
   - `ch039-q05`
   - `ch039-q07`
   - `ch039-q10`
   - `ch040-q01`
   - `ch040-q08`
   - `ch040-q10`
2. 為所有 90 題補 exact official titles 與 deep links。
3. 補強列出的 27 題短 explanations。
4. 重寫列出的 7 題低鑑別度 distractors。
5. 將所有 App Runner 題標成 existing-customer/enrichment，並降低它在 SAA-C03/SAP-C02 核心題庫的占比。
6. 由 maintainer 解決「每章 2 題複選」與 audit「只有第 10 題複選」的規格衝突。
7. Revision 後由另一位 reviewer 重新確認答案集合，而不是只跑 schema validator。

## 最終判定

**REVISE**

## Verification

- **結構與原審查覆蓋：通過。** 修訂後仍為 9 章、每章 10 題，intent 1–10、答案 schema 與 task mapping 正常；原先列出的 27 題短 explanations 已全部補至 substantive level，7 組弱 distractors 也已改成較接近的替代方案。
- **Dedicated Host／ODCR：通過。** `ch032-q09` 已把 host tenancy 的容量單位改為實際配置的 Dedicated Hosts，並正確說明一般 On-Demand Capacity Reservation 只支援 `default`／`dedicated` tenancy，不能供 `host` tenancy 共用。
- **T-family credits：通過。** `ch032-q06` 已指定 Standard mode，正確區分 Standard throttling、Unlimited surplus-credit 成本，以及 `CPUCreditBalance`、`CPUSurplusCreditBalance`、`CPUSurplusCreditsCharged`。
- **ALB fail-open：通過。** `ch035-q06` 已區分「沒有 registered targets」可能回 503，與「所有 registered targets unhealthy」時 ALB fail open 並繼續嘗試路由。
- **API Gateway usage plan／WAF：通過。** `ch037-q04` 已把 hard entitlement 放在 durable backend counter，並把 usage-plan quota 標為 best effort；`ch037-q10` 已明確限定 Regional REST API stage、WAF rate-based rules、Gateway throttling與 Lambda/downstream admission control 的不同責任。
- **ECR scanning／immutability：通過。** `ch038-q10` 已把 digest/tag immutability、vulnerability scanning、AWS Signer/ECR managed signing、CI/CD admission gate 與跨 Region replication 分開，不再把「掃描完成」誤當成「核准部署」。
- **AWS Batch compute environments：仍需修正。** `ch039-q02` 的題幹與答案方向已正確改成獨立 SPOT 與 EC2 compute environments；但 B 的解析仍宣稱合法 `computeResources.type` 只有 `EC2`、`SPOT`、`FARGATE`、`FARGATE_SPOT`。截至 2026-10-01，官方 API 另包含 `ECS_MANAGED_INSTANCES`。請加入該型別，或改寫成「例如」而非完整列舉。官方頁：https://docs.aws.amazon.com/batch/latest/APIReference/API_ComputeResource.html
- **Spot checkpoint：內容通過，source deep link 需修正。** `ch039-q05` 已正確把 periodic durable checkpoint、小工作單位、retry 與 idempotency 當成主要恢復機制，signal 只作額外機會；但 `batch-checkpointing` 仍指向已退回 AWS Batch 首頁的 `bestpractice9.html`，不是有效 claim-level source。請改為目前的 Spot best-practice 頁：https://docs.aws.amazon.com/batch/latest/userguide/bestpractice6.html
- **EMR Serverless：通過。** `ch039-q07` 已明確說明 diversified Spot 只適用於 EMR on EC2，EMR Serverless 使用 managed capacity，不提供客戶選擇 Spot purchase option。
- **Batch Spot／On-Demand fallback：通過。** `ch039-q10` 已將 diversified SPOT CE 與獨立 EC2 On-Demand CE、queue association/order、quota、priority、deadline capacity 分開描述，沒有把 fallback 寫成單一 Spot 開關或必然立即成功。
- **App Runner existing-customer scope：通過。** `ch040-q02`、`ch040-q03`、`ch040-q06`、`ch040-q10` 已標示為既有客戶延伸內容，並使用 2026-04-30 cutoff；新客戶選型 `ch040-q01`、`ch040-q08` 已改用 ECS Express Mode。`ch040-q05`、`ch040-q07` 也不再不必要地綁定 App Runner。
- **App Runner／Beanstalk runtime identity：通過。** `ch040-q10` 已區分 App Runner instance role、ECR access role、Beanstalk EC2 instance profile，以及 network reachability、database authentication、Secrets Manager/KMS authorization。
- **官方來源覆蓋：大致通過，但尚非全部精確。** 90 題都有 exam guide 以外的 product-level official source，114 個使用中的官方 source records 均可取得 HTTP 200，且已不再指向整本 guide 根目錄；但除上述 `batch-checkpointing` 外，`alb-deregistration-delay` 的 URL anchor 錯指 `#modify-target-group-health-settings`，實際應為 `#deregistration-delay`。此 source 影響 `ch035-q05`、`ch038-q05`：https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html#deregistration-delay
- **重新送審條件：** 修正 `ch039-q02` 的 `ECS_MANAGED_INSTANCES` 遺漏，替換 `batch-checkpointing` URL，並修正 `alb-deregistration-delay` anchor；其餘本輪指定項目已驗證通過。

REVISE

## Final Verification

- `ch039-q02`：通過。解析已將 `ECS_MANAGED_INSTANCES` 納入 `computeResources.type` 的非完整舉例，並維持「Spot 與 On-Demand 必須使用不同 compute environments」的正確結論。
- `batch-checkpointing`：通過。URL 已指向 `https://docs.aws.amazon.com/batch/latest/userguide/bestpractice6.html`。
- `alb-deregistration-delay`：通過。URL anchor 已改為 `#deregistration-delay`。
- 本輪僅讀取 `part_03.json` 核對上述三項；三項均已完成，無剩餘修訂要求。

VERIFIED
