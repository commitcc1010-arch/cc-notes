# P03 Audit：第 32–40 章 Compute / Application Architecture

## 審核契約

- 範圍只涵蓋第 32–40 章目前由 `practice_questions()` 產生的章末題。
- 下列是原創題目「意圖規格」，不是考古題、洩漏題或可直接發布的題幹。
- 每章恰好 10 個意圖，依序覆蓋：服務選型、runtime mechanism、scaling signal、concrete config、health/draining、failure diagnosis、cost、SAA、SAP、multi-response。
- 每個意圖必須由實作者補成具體 scenario；不得再使用「功能較多」「全部部署」「managed service 自動理解 business requirements」等跨章通用填充選項。
- 單選題有一個可證明的最佳原則與三個 plausible distractors。每章至少兩題為五選二複選，
  其中第 10 題固定整合兩個相互補足的正確原則；另一題由章節內容決定。

## 全域發現

1. 第 32、34、36 章已有逐字相同的正確／錯誤選項。原因是 alias profile 被映射回 primary profile：
   - 第 32 章 `Amazon Machine Images`、`Placement groups` 都映射成 `Amazon EC2`，造成 Q2、Q3 重複。
   - 第 34 章 `AWS Auto Scaling` 映射成 `Amazon EC2 Auto Scaling`，造成 Q2、Q3 重複。
   - 第 36 章 `Lambda concurrency` 映射成 `AWS Lambda`，造成 Q2、Q3 重複。
2. 每章 Q1 與 Q4 都在重問「選 primary service」，只是把答案從敘述改成設定清單，知識增量很低。
3. 每章 Q5 使用相同的「跨帳號 owner、guardrail、canary、evidence」答案。這些原則本身合理，但沒有綁定該服務的 deployment unit、rollback boundary、health signal 或資料相容性，不能有效測 SAP 能力。
4. 多數錯誤選項不是 plausible distractor。例如「全部部署」「等故障後人工處理」「服務會自動理解需求」不會讓具備最低背景的考生猶豫。
5. 現有五題沒有穩定覆蓋 concrete values/relationships、health transition、常見錯誤訊號、成本翻轉點與真正的 multi-response trade-off。

## Source key registry

既有 exam keys：`saa-d2`、`saa-d3`、`saa-d4`、`sap-d2`、`sap-d3`、`sap-d4`。以下 product keys 應在實作題目時指向 AWS 官方文件：

- `ec2-types` — EC2 instance types and workload characteristics.
- `ec2-ami` — AMI lifecycle, launch permissions, copy and deprecation.
- `ec2-placement` — cluster, partition and spread placement groups.
- `ec2-status` — system, instance and attached-EBS status checks.
- `ec2-purchase` — On-Demand, Savings Plans, Reserved Instances, Spot, Dedicated Hosts.
- `ebs-types` — gp3, io2, st1 and sc1 performance contracts.
- `ebs-lifecycle` — EBS attachment, persistence, delete-on-termination and instance store.
- `ebs-snapshots` — incremental snapshots, restore, archive and application consistency.
- `asg-target-tracking` — target tracking, predefined/custom metrics and warmup.
- `asg-health` — ELB health checks, grace period, lifecycle hooks and instance refresh.
- `asg-mixed` — mixed instances, capacity-optimized Spot and allocation strategies.
- `alb-routing` — listeners, rules, target groups and request routing.
- `alb-health` — health checks, fail-open behavior and target reason codes.
- `alb-attributes` — deregistration delay, stickiness, idle timeout and access logs.
- `lambda-runtime` — execution environment lifecycle and reuse.
- `lambda-concurrency` — reserved/provisioned concurrency, scaling and throttling.
- `lambda-events` — synchronous, asynchronous and poll-based event handling.
- `lambda-sqs` — SQS event source scaling, partial batch response and visibility timeout.
- `api-rest-http` — REST API versus HTTP API feature and cost selection.
- `api-auth` — IAM, JWT/Cognito and Lambda authorizers; API keys are not authentication.
- `api-operations` — throttling, metrics, stages, canary release and integration errors.
- `containers-choice` — ECS, EKS, Fargate and EC2 capacity decision guide.
- `ecs-runtime` — task definitions, services, task/execution roles and `awsvpc`.
- `ecs-scaling` — service auto scaling, capacity providers and deployment health.
- `eks-operations` — control plane, nodes, pod identity, upgrades and disruption budgets.
- `ecr-supply-chain` — digest/tag behavior, immutability, scanning and replication.
- `batch-runtime` — job definitions, queues, compute environments, retries and timeouts.
- `emr-runtime` — EMR on EC2, EMR Serverless, managed scaling and S3 data.
- `spot-interruption` — interruption notices, rebalance recommendation and checkpointing.
- `beanstalk-runtime` — environments, platform versions and deployment policies.
- `apprunner-runtime` — source/image deployment, autoscaling, health and networking.
- `lightsail-scope` — fixed bundles and the operational limits of the simplified platform.

---

## 第 32 章：EC2 Instance、AMI 與 Placement

### Current-question audit

- **Q1 ambiguous:** 一個題幹同時塞入 HPC、socket license 與 horizontally scalable web 三種不同 workload，正確答案只是把三個決策重新念一遍，沒有要求考生真正選 instance/tenancy/placement。
- **Q2 duplicate:** A 與 D 逐字相同；其中一個被標正確、另一個標錯誤。
- **Q3 duplicate:** C 與 D 逐字相同；其中一個被標正確、另一個標錯誤。
- **Q4 redundant:** 與 Q2 都只是選 EC2 加同一串參數，沒有測 instance family、AMI 或 placement 的選擇。
- **Q5 weak/ambiguous:** workload decision 與 generic rollout 被固定成兩個答案，但題幹沒有 migration unit、license、capacity 或 rollback 條件。
- **Missing:** cluster/partition/spread、burstable credits、network/EBS bandwidth、AMI permissions/copy、status checks、capacity reservation、purchase model 與 Dedicated Host 邊界。

### Ten replacement intents

1. **Service choice — instance family by bottleneck**
   - Intent：給定 memory-bound in-memory analytics、GPU inference、一般 web 三種 profile 中的一種，要求依量測到的 bottleneck 選 family，而非只比 vCPU。
   - Correct principle：先以 workload 的 constrained resource 選 general/compute/memory/accelerated family，再用 benchmark 決定 size。
   - Distractors：D1 因資料量大一律選 storage optimized；D2 因要高可用一律選最大的 instance；D3 因價格低一律選 burstable instance。
   - Task/source：`SAA-3.2` / `ec2-types`

2. **Runtime mechanism — AMI launch contract**
   - Intent：辨認 launch template 使用 AMI 啟動時，AMI、instance type、EBS snapshot、user data 各自負責什麼。
   - Correct principle：AMI提供 boot/root-volume template；instance type決定 compute envelope；launch-time networking、IAM role與user data仍需另外設定。
   - Distractors：D1 AMI持續同步所有 running-instance changes；D2 AMI決定 subnet route table；D3 AMI本身提供跨 AZ failover。
   - Task/source：`SAA-3.2` / `ec2-ami`

3. **Scaling signal — EC2 bottleneck before scale-out**
   - Intent：服務 latency 上升但平均 CPU 低，Network bandwidth 與 EBS throughput 已到 instance limit，問下一個動作。
   - Correct principle：先確認 instance-level network/EBS limits與應用瓶頸；scale up 或 scale out 必須針對受限資源。
   - Distractors：D1 只把 CloudWatch CPU threshold 降低；D2 建新 AMI 即可增加 bandwidth；D3 改成 spread placement group即可消除單機上限。
   - Task/source：`SAA-3.2` / `ec2-types`

4. **Concrete config — low-latency HPC placement**
   - Intent：要求同一 AZ 內 tightly coupled MPI nodes 的 launch 設定。
   - Correct principle：使用支援 enhanced networking 的相容 instance types，放入同一 cluster placement group；接受其容量與單 AZ trade-off。
   - Distractors：D1 spread placement group跨 hosts以取得最低 latency；D2 partition placement group保證所有 nodes在同一 rack；D3 Dedicated Hosts自動形成 HPC low-latency fabric。
   - Task/source：`SAA-3.2` / `ec2-placement`

5. **Health/draining — status check response**
   - Intent：區分 system status check failed 與 instance status check failed 的處置。
   - Correct principle：system failure偏向底層 host/network，可 stop/start 或 recover 到新 host；instance failure先查 guest OS、network/config，再依可替換設計重建。
   - Distractors：D1 兩者都只需重啟 application process；D2 system check failed表示 security group擋住 ALB；D3 instance check failed必然是 AZ outage。
   - Task/source：`SAA-2.2` / `ec2-status`

6. **Failure diagnosis — T-family credit exhaustion**
   - Intent：低平均 CPU 的 T-family instance 在長時間高負載後 throughput 降低，要求判讀 credit metrics。
   - Correct principle：burstable instances依 CPU credits運作；持續 baseline 以上負載應檢查 credit balance/surplus，必要時改用固定性能 family。
   - Distractors：D1 增加 AMI volume size；D2 改成 spread placement group；D3 開啟 detailed monitoring就會恢復 credits。
   - Task/source：`SAP-2.5` / `ec2-types`

7. **Cost — commitment and interruption trade-off**
   - Intent：穩定 baseline 加可重試尖峰 fleet，要求選 purchase mix。
   - Correct principle：穩定使用量用 Savings Plans/RI 類承諾折扣，fault-tolerant彈性部分用 diversified Spot，短期不可預測部分保留 On-Demand。
   - Distractors：D1 全部 Dedicated Hosts最省錢；D2 全部 Spot並假設永不中斷；D3 為尖峰購買長期 commitment但不看利用率。
   - Task/source：`SAA-4.2` / `ec2-purchase`

8. **SAA — placement group semantics**
   - Intent：把 cluster、partition、spread 對應到 tightly coupled HPC、rack-aware distributed system、少量 critical instances。
   - Correct principle：cluster優化低 latency；partition讓大型分散式系統知道 failure partitions；spread把少量 instances分散到底層硬體。
   - Distractors：D1 cluster提供跨 Region DR；D2 spread適合無上限的大型 node fleet；D3 partition自動複寫 application data。
   - Task/source：`SAA-2.2` / `ec2-placement`

9. **SAP — license and capacity architecture**
   - Intent：BYOL 軟體要求 socket/core visibility，且 cutover 時必須保證特定 AZ 有容量。
   - Correct principle：license需要 host-level visibility時選 Dedicated Hosts；容量保證另以 Capacity Reservation／capacity planning處理，兩者責任不可混淆。
   - Distractors：D1 Dedicated Instances提供同等 host socket控制；D2 Savings Plans保證指定 AZ 容量；D3 cluster placement group本身保證任意規模容量。
   - Task/source：`SAP-2.5`, `SAP-2.6` / `ec2-purchase`, `ec2-placement`

10. **Multi-response — immutable and resilient EC2 rollout（選兩項）**
    - Intent：跨多 AZ 更新 web fleet，要求避免 in-place snowflakes 並限制 failed AMI blast radius。
    - Correct principles：C1 建立 versioned AMI/launch-template version並以 instance refresh或新 ASG逐批替換；C2 以跨 AZ fleet、健康門檻與 rollback alarm驗證新版本。
    - Distractors：D1 SSH進每台 production instance手改；D2 覆寫同一 AMI identity並假設所有 launches內容一致；D3 一次終止全部舊 instances再觀察。
    - Task/source：`SAP-2.4` / `ec2-ami`, `asg-health`

---

## 第 33 章：EBS、Instance Store 與 EC2 Lifecycle

### Current-question audit

- **Q1 broad but under-specified:** 把 database log 與 transcoding scratch放同一題，正確選項只是重述章節摘要；沒有問 volume type、persistence 或 lifecycle。
- **Q2 partly invalid distractor:** `EC2 instance store` 被 alias 成完整 EC2 profile，因此錯誤選項列的是 instance family、AMI、SG 等，不是 instance-store configuration。
- **Q3 weak distractor:** 把 EC2 Nitro/AMI 機制當成 EBS 的唯一 peer，未比較 instance store與 snapshot restore。
- **Q4 redundant:** 再次要求選 EBS 及整串設定，與 Q1/Q2 的判斷高度重疊。
- **Q5 generic:** 沒有測 snapshot consistency、cross-Region copy、restore time、KMS 或 EC2 termination semantics。
- **Missing:** reboot/stop/terminate差異、gp3/io2/st1/sc1、queue/latency metrics、Fast Snapshot Restore、snapshot archive、delete-on-termination、Multi-Attach限制。

### Ten replacement intents

1. **Service choice — durable block versus ephemeral scratch**
   - Intent：同一 EC2 workload 有 durable database volume 與可重建 temporary shuffle data，要求分別選 storage。
   - Correct principle：需要 stop/start後保留且可 snapshot的 block state用 EBS；高 I/O、可重建、與 host生命週期綁定的 scratch可用 instance store。
   - Distractors：D1 全放 instance store並靠 reboot保存；D2 全放 EBS Snapshot直接掛載讀寫；D3 用 S3取代需要 in-place block updates的 database volume。
   - Task/source：`SAA-3.1` / `ebs-lifecycle`

2. **Runtime mechanism — volume and snapshot scope**
   - Intent：辨認 EBS volume、EC2 attachment與 snapshot的 durability/scope。
   - Correct principle：EBS volume是 AZ-scoped network block device；snapshot是 regional incremental backup，可在可用區內建立新 volume，跨 Region需 copy。
   - Distractors：D1 volume會同步掛載到 Region所有 AZ；D2 snapshot是可直接 mount的 shared filesystem；D3 detach會自動把 volume轉成 S3 object。
   - Task/source：`SAA-2.2` / `ebs-lifecycle`, `ebs-snapshots`

3. **Scaling signal — storage performance diagnosis**
   - Intent：database latency升高，要求從 VolumeRead/WriteOps、throughput、queue length及 instance EBS bandwidth判斷瓶頸。
   - Correct principle：同時比較 workload demand、volume provisioned limits與 EC2 EBS-optimized bandwidth；只增加 IOPS不一定修正 throughput或instance上限。
   - Distractors：D1 只看 EC2 CPUUtilization；D2 增加 snapshot數量提高 live volume IOPS；D3 開啟 encryption會自動倍增 throughput。
   - Task/source：`SAP-2.5` / `ebs-types`

4. **Concrete config — gp3 versus io2**
   - Intent：一般 production volume需要獨立調整 size、IOPS、throughput；極低 latency/high durability database另有高 IOPS需求。
   - Correct principle：一般用途先評估 gp3的獨立 IOPS/throughput；關鍵高 IOPS、低 latency與更高 durability需求評估 io2，並按實測配置。
   - Distractors：D1 st1用於高 IOPS random OLTP；D2 sc1用於 latency-sensitive boot volume；D3 gp2永遠比 gp3便宜且可獨立調整所有參數。
   - Task/source：`SAA-3.1`, `SAA-4.1` / `ebs-types`

5. **Health/draining — application-consistent detach/snapshot**
   - Intent：在不中斷資料正確性的前提下 snapshot 多 volume database。
   - Correct principle：先使用 database-native backup或 quiesce/freeze I/O，協調多 volume時間點，再建立 snapshots並實際 restore驗證。
   - Distractors：D1 直接 snapshot即可保證 transaction-consistent；D2 先強制 detach mounted volume而不 flush；D3 snapshot完成代表 RTO自動符合。
   - Task/source：`SAA-2.2` / `ebs-snapshots`

6. **Failure diagnosis — lifecycle data loss**
   - Intent：instance stop/start後 temporary data消失，但 EBS root仍存在，要求判斷原因。
   - Correct principle：instance store只保證在同一 instance生命週期內的暫存；reboot通常保留，但 stop/hibernate/terminate或host loss不可當持久契約。
   - Distractors：D1 EBS delete-on-termination刪除了所有 instance store；D2 security group阻止本機 NVMe mount；D3 snapshot lifecycle policy清除了 running disk。
   - Task/source：`SAA-2.2` / `ebs-lifecycle`

7. **Cost — right-size performance and backups**
   - Intent：大量低使用率 io2 volumes與多年 snapshots造成成本上升，要求不犧牲恢復目標的優化。
   - Correct principle：依實測改用適當 volume type/size/IOPS，刪除 orphaned volumes，使用 lifecycle/Archive管理長期 snapshots並定期 restore測試。
   - Distractors：D1 刪除所有 snapshots只保留 replication；D2 將 database改用 sc1不測 latency；D3 停止 EC2就假設 EBS volume不計費。
   - Task/source：`SAA-4.1`, `SAP-2.6` / `ebs-types`, `ebs-snapshots`

8. **SAA — delete-on-termination and root/data volumes**
   - Intent：終止 ASG instance時 root應刪除，但獨立 data volume要保留供調查。
   - Correct principle：在 block device mapping分別設定 `DeleteOnTermination`；不要以「EBS一定持久」推論終止後所有 volumes都保留。
   - Distractors：D1 此行為只能由 security group控制；D2 snapshot policy會覆寫 delete-on-termination；D3 將 data volume設為 instance store即可保留。
   - Task/source：`SAA-2.2` / `ebs-lifecycle`

9. **SAP — cross-Region recovery and restore latency**
   - Intent：encrypted EBS-based application需跨 Region DR，且大量 volumes必須在 RTO內恢復性能。
   - Correct principle：複製 snapshots與可用 KMS key到目標 Region，預先演練 restore；若 first-read初始化不符合 RTO，評估 Fast Snapshot Restore或預初始化。
   - Distractors：D1 AZ-scoped volume可直接 attach到另一 Region；D2 Multi-Attach是跨 Region replication；D3 snapshot copy自動搬移 running EC2 network identity。
   - Task/source：`SAP-2.4` / `ebs-snapshots`

10. **Multi-response — resilient EBS database recovery（選兩項）**
    - Intent：單 AZ EBS database必須降低資料遺失風險並證明可恢復。
    - Correct principles：C1 建立符合 RPO的 application-consistent snapshot/backup排程並保護 KMS permissions；C2 定期在隔離環境 restore，量測完整 application RTO與資料驗證。
    - Distractors：D1 只監控 `StatusCheckFailed`便視為 backup；D2 把同一 volume Multi-Attach到不同 AZ；D3 只增加 volume IOPS便能防止誤刪。
    - Task/source：`SAP-2.4`, `SAP-2.6` / `ebs-snapshots`

---

## 第 34 章：Auto Scaling 與 Scaling Metrics

### Current-question audit

- **Q1 internally ambiguous:** 題幹已指出 queue age升高與 CPU低，D「queue depth per worker更直接」其實也是合理答案；標準答案 C只是泛稱 target tracking。
- **Q2 duplicate:** B 與 C 逐字相同，一個正確、一個錯誤。
- **Q3 duplicate:** A 與 B 逐字相同，一個正確、一個錯誤。
- **Q4 redundant:** 再次要求選 ASG與完整參數清單，沒有讓考生計算或判讀 scaling signal。
- **Q5 generic:** 沒有測 instance refresh、mixed instances、lifecycle hook、predictive scaling、warmup或 scale-in protection。
- **Missing:** metric proportionality、metric dimensions、backlog-per-instance、default instance warmup、health source、termination/draining、capacity rebalance與 insufficient capacity。

### Ten replacement intents

1. **Service choice — scaling policy type**
   - Intent：比較穩定週期性尖峰、未知需求波動與一次性預定活動。
   - Correct principle：未知且可量測的 demand用 target tracking；固定已知時間用 scheduled scaling；有足夠歷史與週期性可評估 predictive scaling。
   - Distractors：D1 所有情況都用 step scaling；D2 只提高 max size不設定 policy；D3 依每台 instance磁碟使用率作 fleet demand signal。
   - Task/source：`SAA-3.2` / `asg-target-tracking`

2. **Runtime mechanism — desired capacity reconciliation**
   - Intent：要求描述 launch template、desired capacity、AZ placement與 scaling policy的關係。
   - Correct principle：policy改變 desired capacity；ASG依 launch template與 subnets啟停 instances並持續調和健康容量，而非代理 application requests。
   - Distractors：D1 CloudWatch alarm直接建立 EC2且 ASG不參與；D2 launch template持續修改已運行 instances；D3 target tracking只增加 instance size不改數量。
   - Task/source：`SAA-2.2` / `asg-target-tracking`

3. **Scaling signal — SQS backlog per worker**
   - Intent：平均處理時間固定，SQS積壓上升且 CPU低，要求建立自訂 target metric。
   - Correct principle：使用 backlog per active worker（必要時結合 age of oldest message與處理時間/SLO），讓 metric隨 capacity增加而下降。
   - Distractors：D1 使用 queue總訊息數但忽略 fleet size；D2 使用 ALB healthy host count；D3 使用平均 CPU並將 target設為零。
   - Task/source：`SAA-3.2`, `SAP-2.5` / `asg-target-tracking`

4. **Concrete config — launch and warmup contract**
   - Intent：新 instance需 8 分鐘初始化，早期 CPU高，問 target tracking必要設定。
   - Correct principle：版本化 launch template、設定合理 default instance warmup/health grace，避免新 capacity尚未可用就被計入 metric或再次 scale。
   - Distractors：D1 將 cooldown設為零以加速；D2 只延長 ALB idle timeout；D3 把 desired/min/max全部設成同值仍稱 autoscaling。
   - Task/source：`SAA-3.2` / `asg-target-tracking`, `asg-health`

5. **Health/draining — safe scale-in**
   - Intent：worker正在處理長任務時 ASG scale-in，要求避免中途終止。
   - Correct principle：使用 lifecycle hook或 instance scale-in protection，先停止接新工作、完成/checkpoint目前工作，再發出 lifecycle completion；設定 timeout/fallback。
   - Distractors：D1 只延長 CloudWatch period；D2 將 health check grace當成永久 draining；D3 關閉所有 health checks。
   - Task/source：`SAA-2.2` / `asg-health`

6. **Failure diagnosis — ASG cannot launch**
   - Intent：desired增加但 instances停在 Pending或 launch failures，要求建立診斷順序。
   - Correct principle：查 scaling activity與 reason，再查 quota、launch-template權限/AMI、subnet IP、instance-type capacity與 AZ限制；不能只看 CPU alarm。
   - Distractors：D1 重建 ALB listener certificate；D2 增加 deregistration delay；D3 降低 desired capacity並宣稱問題修復。
   - Task/source：`SAP-3.3` / `asg-health`, `asg-mixed`

7. **Cost — mixed instances and Spot**
   - Intent：stateless web fleet需要穩定 baseline與便宜 burst，且能容忍部分 interruption。
   - Correct principle：以 mixed instances policy/capacity providers組合 On-Demand baseline與 diversified, capacity-optimized Spot；保留健康與再平衡機制。
   - Distractors：D1 單一最便宜 Spot instance type與單 AZ；D2 全部 Dedicated Hosts；D3 只買 Savings Plans便會自動 scale。
   - Task/source：`SAA-4.2`, `SAP-2.6` / `asg-mixed`

8. **SAA — metric proportionality**
   - Intent：從 CPUUtilization、RequestCountPerTarget、queue total、deployment count中選適合 target tracking的 metric。
   - Correct principle：metric應代表 demand/capacity比例，capacity增加時平均值能朝 target回落；ALB request count per target常符合 web fleet。
   - Distractors：D1 累積 lifetime request count；D2 fixed deployment version number；D3 healthy host count作為唯一 demand metric。
   - Task/source：`SAA-3.2` / `asg-target-tracking`

9. **SAP — fleet refresh with rollback**
   - Intent：數百個 ASG跨帳號更新 AMI，要求控制 blast radius並可回復。
   - Correct principle：鎖定 launch-template version，分 wave執行 instance refresh，設定 minimum healthy percentage、checkpoint/alarm與明確 rollback到前版。
   - Distractors：D1 修改 `$Latest`後一次 terminate全部 instances；D2 用 user data SSH手改既有 fleet；D3 只在 management account保存 AMI而不分享 launch permission。
   - Task/source：`SAP-2.4`, `SAP-3.3` / `asg-health`

10. **Multi-response — queue-worker scaling（選兩項）**
    - Intent：SQS worker要在五分鐘內壓低 backlog，同時不得重複或中斷昂貴工作。
    - Correct principles：C1 以 backlog-per-instance/oldest-age與已知處理時間設定 scaling target；C2 scale-in前用 visibility timeout、idempotency及 lifecycle draining/checkpoint保護工作。
    - Distractors：D1 只依平均 CPU；D2 將 SQS retention設短以讓 backlog消失；D3 每次 scale-in先 purge queue。
    - Task/source：`SAP-2.4`, `SAP-2.5` / `asg-target-tracking`, `asg-health`

---

## 第 35 章：ALB＋ASG 高可用 Web Tier

### Current-question audit

- **Q1 incomplete:** 題幹要求部署時「不可掉 session」，但標準答案只有 ALB＋ASG與 application health，沒有外部 session store或可驗證的 draining，因此未完整滿足需求。C 的外部 session store反而是必要設計的一部分。
- **Q2 list recognition only:** 列出七個設定名，沒有測 listener rule、health path、target type或 timeout效果。
- **Q3 broadly correct but shallow:** 沒有測 request route、health route與 target registration三條不同路徑。
- **Q4 redundant:** 與 Q1/Q2再次選 ALB。
- **Q5 generic:** 沒有測 blue/green target groups、deregistration delay、connection draining、ASG replacement或 session state。
- **Missing:** ALB 502/503/504、fail-open、slow start、deregistration delay、RequestCountPerTarget、cross-zone behavior、sticky-session限制與 target-group deployment。

### Ten replacement intents

1. **Service choice — ALB plus ASG responsibility split**
   - Intent：HTTP app需 host/path routing、跨 AZ與故障替換，要求選元件組合。
   - Correct principle：ALB負責 L7 routing與只送往可用 targets；ASG負責維持/替換 EC2 capacity；兩者透過 target group與 ELB health integration連接。
   - Distractors：D1 只用 Route 53逐 request分流；D2 只用 ASG便可終止 TLS/path route；D3 只用 ALB便可重建 failed EC2。
   - Task/source：`SAA-2.1`, `SAA-2.2` / `alb-routing`, `asg-health`

2. **Runtime mechanism — listener to target**
   - Intent：追蹤 HTTPS request從 listener、certificate、priority rule、target group到 target port的流程。
   - Correct principle：ALB在 listener接受/終止 TLS，依規則選 target group，再在 target group內選 healthy target；security groups與target port仍須允許路徑。
   - Distractors：D1 target group自己解析 public DNS再選 AZ；D2 ASG launch template執行 host-header routing；D3 ACM certificate安裝到每個 EC2才可由 ALB終止 TLS。
   - Task/source：`SAA-3.2` / `alb-routing`

3. **Scaling signal — requests per target**
   - Intent：每個 web instance約能處理固定 request rate，CPU受 background jobs干擾，要求選 ASG metric。
   - Correct principle：使用 ALB `RequestCountPerTarget` target tracking，並以 latency/error作驗證；metric直接表示每個 active target的 demand。
   - Distractors：D1 ALB總 lifetime requests；D2 ASG desired capacity本身；D3 Route 53 query count。
   - Task/source：`SAA-3.2` / `asg-target-tracking`, `alb-routing`

4. **Concrete config — public ALB/private targets**
   - Intent：要求配置 internet-facing ALB，EC2不得接受 internet直接連線。
   - Correct principle：ALB跨 public subnets、443 listener與 ACM certificate；targets在 private subnets；app SG只允許 ALB SG到 app port；target group設實際 health path。
   - Distractors：D1 EC2配置 public IP並允許 `0.0.0.0/0`到 app port；D2 ALB放單一 private subnet仍稱 public HA；D3 database SG直接允許 ALB SG而略過 app authorization。
   - Task/source：`SAA-1.2`, `SAA-2.2` / `alb-routing`

5. **Health/draining — zero-drop replacement**
   - Intent：部署時有長請求，要求舊 target停止接新流量但完成 in-flight requests。
   - Correct principle：先將 target deregister，設定符合請求上限的 deregistration delay，讓 ASG lifecycle/deployment等待 draining；應用也要處理 termination signal。
   - Distractors：D1 把 health check interval設得更長即等同 draining；D2 立即 terminate再靠 client重試所有操作；D3 開 stickiness即可保證 in-flight request完成。
   - Task/source：`SAA-2.2` / `alb-attributes`, `asg-health`

6. **Failure diagnosis — distinguish 502/503/504**
   - Intent：根據 ALB metrics/access logs與 target health reason code診斷錯誤。
   - Correct principle：503常指無可用 target/容量；504指連線或 response timeout；502常見於 target reset、malformed response或 TLS/backend protocol問題，需逐層查證。
   - Distractors：D1 所有 5xx都只需增加 ASG max；D2 504必然是 DNS failure；D3 502必然是 ACM certificate到期。
   - Task/source：`SAP-3.4` / `alb-health`, `alb-attributes`

7. **Cost — LCU and architecture trade-off**
   - Intent：ALB成本因 new connections、active connections、processed bytes或 rule evaluations上升，要求先定位再優化。
   - Correct principle：依 LCU構成與 access logs找主導維度；可透過 keep-alive、CloudFront caching、規則簡化或 payload優化處理，不能只減少 target數。
   - Distractors：D1 將 ALB改為 single AZ；D2 關閉 health checks減少所有 LCU；D3 買 EC2 Savings Plans會降低 ALB LCU。
   - Task/source：`SAP-2.6` / `alb-routing`

8. **SAA — state externalization**
   - Intent：ASG替換 instance後使用者 session遺失，要求最低耦合修正。
   - Correct principle：讓 instances stateless，session/token放外部共享 store或使用可驗證 signed token；stickiness只能作相容措施，不能成為故障後持久保證。
   - Distractors：D1 把 session寫 instance store並延長 stickiness；D2 禁用 ASG health replacement；D3 只增加 ALB idle timeout。
   - Task/source：`SAA-2.1`, `SAA-2.2` / `alb-attributes`

9. **SAP — blue/green web rollout**
   - Intent：需要逐步把 production流量移到新 ASG，錯誤率超標自動回復。
   - Correct principle：使用獨立 versioned green target group/ASG，先通過 health與 smoke test，再以 weighted forwarding或 deployment service分流；以 business/error alarms回切。
   - Distractors：D1 在同一 instances上覆寫 binaries且無版本；D2 同時修改 schema為不相容版本再切 100%；D3 只看 CloudFormation成功便刪除 blue。
   - Task/source：`SAP-2.1`, `SAP-2.4` / `alb-routing`, `asg-health`

10. **Multi-response — resilient ALB/ASG tier（選兩項）**
    - Intent：web tier遇到單 AZ失效與 application deadlock時仍需服務。
    - Correct principles：C1 ALB與 ASG配置至少兩個 AZ並維持足夠 healthy capacity；C2 使用真正驗證依賴/關鍵路徑的 application health endpoint，讓 ALB停止送流量且 ASG可替換。
    - Distractors：D1 health endpoint永遠回 200；D2 只用 EC2 system status check判斷 app deadlock；D3 將所有 session保存在單一 instance local disk。
    - Task/source：`SAA-2.2`, `SAP-2.4` / `alb-health`, `asg-health`

---

## 第 36 章：Lambda Execution、Concurrency 與 Cold Start

### Current-question audit

- **Q1 incomplete/ambiguous:** 題幹的 hard constraint是 RDS最多 200 connections，但答案只說 reserved concurrency與可選 provisioned concurrency；沒有要求每 invocation的 connection數、RDS Proxy或同步/非同步入口，因此不能證明不超過 200。
- **Q2 duplicate:** A 與 D 逐字相同，一個正確、一個錯誤。
- **Q3 duplicate:** C 與 D 逐字相同，一個正確、一個錯誤。
- **Q4 redundant:** 再次要求選 Lambda與完整參數清單。
- **Q5 generic:** 把 reserved/provisioned concurrency與跨帳號 rollout固定為答案，沒有 event source、alias、version、DLQ、partial batch response或 downstream quota。
- **Missing:** invocation models、execution-environment reuse、reserved與 provisioned差別、SQS poller scaling、visibility timeout、partial batch failure、throttle原因、RDS Proxy、memory/CPU cost與 alias deployment。

### Ten replacement intents

1. **Service choice — Lambda versus containers**
   - Intent：比較短、事件驅動、bursty工作與長時間、穩定高利用率、需要自訂 daemon/host控制的服務。
   - Correct principle：短期無狀態事件與快速彈性優先 Lambda；長時間或需完整 runtime/sidecar/host控制時評估 ECS/Fargate/EC2，並以總成本與操作需求決定。
   - Distractors：D1 只要是 Python就一律 Lambda；D2 只要流量低就使用 EKS；D3 以 provisioned concurrency取代所有長時間服務。
   - Task/source：`SAA-3.2`, `SAA-4.2` / `lambda-runtime`, `containers-choice`

2. **Runtime mechanism — execution environment reuse**
   - Intent：辨認 cold initialization、handler invocation、frozen environment reuse與 `/tmp`/global memory的可靠性。
   - Correct principle：初始化資源可在 warm environment重用以降低成本，但 environment可隨時被替換；global memory與 `/tmp`只能當 cache，durable state必須外部化。
   - Distractors：D1 同一 function永遠只有一個 process；D2 每次 invocation一定是全新 environment；D3 provisioned concurrency使 global variables成為 durable database。
   - Task/source：`SAA-3.2` / `lambda-runtime`

3. **Scaling signal — concurrency and event lag**
   - Intent：SQS consumer延遲升高，要求區分 concurrency utilization、iterator/oldest-message age與 downstream saturation。
   - Correct principle：以 event lag/oldest age衡量是否跟得上需求，以 concurrent executions/throttles判斷容量上限，同時把 downstream quota納入最大 concurrency。
   - Distractors：D1 只看 invocation總數；D2 只增加 function timeout；D3 將 DLQ message count當成即時可用 concurrency。
   - Task/source：`SAP-2.5` / `lambda-concurrency`, `lambda-sqs`

4. **Concrete config — reserved versus provisioned concurrency**
   - Intent：一個 latency-sensitive API需降低 cold starts，另一個批次 function不得耗盡全帳號 concurrency。
   - Correct principle：provisioned concurrency預先準備 environments以降低啟動 latency；reserved concurrency保留並限制 function可用 concurrency，兩者解決不同問題。
   - Distractors：D1 provisioned concurrency是 account-wide hard throttle；D2 reserved concurrency保證沒有 cold start；D3 memory設定直接等於 concurrent execution數。
   - Task/source：`SAA-3.2`, `SAA-4.2` / `lambda-concurrency`

5. **Health/draining — safe SQS batch handling**
   - Intent：Lambda處理 10-message batch，其中一筆失敗，要求避免九筆成功訊息被反覆處理。
   - Correct principle：程式需 idempotent，啟用/report partial batch failures，正確設定 visibility timeout、retry與 DLQ；失敗項目才回 queue。
   - Distractors：D1 handler捕捉所有錯誤並永遠回成功；D2 每次失敗 purge整個 queue；D3 將 batch size設大即可消除重複。
   - Task/source：`SAA-2.1`, `SAA-2.2` / `lambda-sqs`

6. **Failure diagnosis — throttles and database exhaustion**
   - Intent：Lambda出現 throttles，RDS同時 `too many connections`，要求判斷 account/function/downstream三層限制。
   - Correct principle：檢查 account unreserved concurrency、function reserved concurrency、event-source maximum concurrency與 database connection model；用合理 cap、connection reuse/RDS Proxy及 backpressure修正。
   - Distractors：D1 增加 provisioned concurrency且不限制 spillover；D2 延長 timeout讓 connections占用更久；D3 把 function移出 VPC即可提高 RDS connection limit。
   - Task/source：`SAP-2.5`, `SAP-3.3` / `lambda-concurrency`

7. **Cost — memory, duration and provisioned capacity**
   - Intent：CPU-bound function提高 memory後執行時間大幅縮短，另有全天 provisioned concurrency低利用率，要求成本判斷。
   - Correct principle：Lambda memory同時分配更多 CPU，應以 cost-per-success benchmark；provisioned concurrency只留給有 latency SLO的版本/時段，避免閒置配置。
   - Distractors：D1 永遠選最低 memory最便宜；D2 provisioned concurrency只在 invocation時收費；D3 延長 timeout會自動降低 billed duration。
   - Task/source：`SAA-4.2`, `SAP-2.6` / `lambda-concurrency`

8. **SAA — invocation model and retry**
   - Intent：比較 API Gateway同步、EventBridge/SNS非同步與 SQS poll-based invocation的 retry/error destination責任。
   - Correct principle：同步 caller看到回應並決定重試；非同步由 Lambda queue/retry並可配置 destination/DLQ；SQS由 event source mapping輪詢且訊息生命週期由 visibility/DLQ控制。
   - Distractors：D1 三種模式都只重試一次；D2 API Gateway成功接收等於 background work完成；D3 Lambda DLQ會攔截所有同步 4xx。
   - Task/source：`SAA-2.1`, `SAA-2.2` / `lambda-events`, `lambda-sqs`

9. **SAP — versioned canary and rollback**
   - Intent：跨多帳號部署 Lambda，需逐步轉移流量並以業務錯誤率自動 rollback。
   - Correct principle：發布 immutable version，以 alias作 stable endpoint並使用 weighted shift/CodeDeploy hooks；alarm綁定 errors、latency與 business metric，rollback回前一 version。
   - Distractors：D1 clients直接呼叫 `$LATEST`；D2 覆寫同一 deployment package且不記版本；D3 只看 stack CREATE_COMPLETE便切 100%。
   - Task/source：`SAP-2.1`, `SAP-2.4` / `lambda-runtime`

10. **Multi-response — protect an RDS-backed Lambda API（選兩項）**
    - Intent：流量可突增百倍，但 database只能承受有限 sessions且 p95 cold-start有要求。
    - Correct principles：C1 以 reserved/event-source concurrency把最大並行量限制在 downstream budget內並對 caller實施 backpressure；C2 使用 RDS Proxy/安全 connection reuse減少 connection churn，若 latency SLO需要再對 published alias配置 provisioned concurrency。
    - Distractors：D1 取消所有 concurrency limits；D2 每次 invocation建立多個新 DB connections且不關閉；D3 只增加 Lambda timeout。
    - Task/source：`SAP-2.5`, `SAP-2.6` / `lambda-concurrency`

---

## 第 37 章：API Gateway 與 Serverless API

### Current-question audit

- **Q1 under-specified:** 每客戶 quota、request validation、canary stage偏向 REST API feature set，但答案只寫泛稱 API Gateway，沒有要求選 REST/HTTP API；考生無法證明 feature compatibility。
- **Q2 mixed product features:** 把 REST/HTTP/WebSocket、usage plans、request behavior放在同一串，容易暗示所有 API types都支援相同功能。
- **Q3 shallow:** 描述基本 proxy path，沒有區分 authentication、authorization、mapping、integration與 backend response。
- **Q4 redundant:** 與 Q1/Q2再次選 API Gateway。
- **Q5 generic:** 沒有 custom domain、stage/version、multi-Region DNS、private API、resource policy或 safe client migration。
- **Missing:** REST vs HTTP API、API key不是 authentication、usage plan限制、429/502/504、integration latency、private endpoint、resource policy、canary release與成本翻轉。

### Ten replacement intents

1. **Service choice — REST API versus HTTP API versus ALB**
   - Intent：給定 JWT、低成本 proxy API、API keys/usage plans、request validation/caching或既有 container routing需求，要求選入口。
   - Correct principle：只需低成本 HTTP/JWT proxy時優先 HTTP API；需要 REST API特有的 usage plans、API keys、validation、mapping/caching等能力時選 REST API；單純 VPC service L7 routing可評估 ALB。
   - Distractors：D1 因 API Gateway名稱含 API就永遠選 REST；D2 API key需求可由 ALB listener原生完成；D3 WebSocket API可直接取代所有 synchronous HTTP APIs。
   - Task/source：`SAA-3.2`, `SAA-4.2` / `api-rest-http`

2. **Runtime mechanism — request authorization path**
   - Intent：追蹤 custom domain/stage、route、authorizer、mapping/integration到 backend的順序。
   - Correct principle：Gateway先匹配 API/stage/route並執行適用的 IAM/JWT/Lambda authorization與 request processing，再呼叫 integration；backend仍需驗證業務權限與資料 invariant。
   - Distractors：D1 API key就是 end-user identity；D2 Cognito user pool直接執行 Lambda integration；D3 stage deployment會自動修改 backend database schema。
   - Task/source：`SAA-1.2` / `api-auth`, `api-operations`

3. **Scaling signal — API and integration metrics**
   - Intent：API latency升高，要求區分 Gateway overhead、backend latency、client errors與 throttling。
   - Correct principle：對照 `Latency`與 `IntegrationLatency`、4XX/5XX、Count及 throttles；若 IntegrationLatency主導應查 backend，429則查 usage/account/stage throttles與 client behavior。
   - Distractors：D1 只看 Lambda memory；D2 只看 Route 53 query count；D3 增加 API key數量會提高 backend capacity。
   - Task/source：`SAP-3.3` / `api-operations`

4. **Concrete config — authenticated tenant API**
   - Intent：行動 app需 JWT身份、tenant-level authorization、每 consumer throttling與可追蹤 stage。
   - Correct principle：以 Cognito/OIDC JWT authorizer驗證 token，backend依 claims做 tenant authorization；若確需 usage plan/API key則使用支援的 REST API配置，且 API key不可取代身份驗證。
   - Distractors：D1 只要求 `x-api-key`便視為使用者登入；D2 CORS allow-origin就是 authorization；D3 resource policy `Principal:"*"`可安全識別 tenant。
   - Task/source：`SAA-1.2` / `api-auth`, `api-rest-http`

5. **Health/draining — compatible API rollout**
   - Intent：新 API版本可能改 request/response schema，要求不中斷舊 mobile clients。
   - Correct principle：維持 backward-compatible contract或 versioned route/stage，先 canary小流量，監控 error/latency/business metrics，再逐步 promotion；backend變更採 expand/contract。
   - Distractors：D1 原 route直接改為 incompatible schema；D2 只提高 integration timeout；D3 刪除舊 stage迫使所有 clients升級。
   - Task/source：`SAP-2.1`, `SAP-2.4` / `api-operations`

6. **Failure diagnosis — 429, 502 and 504**
   - Intent：依 execution/access logs與 metrics辨認 throttling、integration response格式錯誤及 backend timeout。
   - Correct principle：429通常是 throttling/quota；502常見於 integration失敗或 Lambda proxy response格式錯；504指 integration未在限制內回應，應修 backend或改 asynchronous pattern。
   - Distractors：D1 429表示 JWT signature一定錯；D2 502只能靠提高 account quota；D3 504可由延長 client DNS TTL修復。
   - Task/source：`SAA-2.2`, `SAP-3.4` / `api-operations`

7. **Cost — HTTP API and caching trade-off**
   - Intent：高流量 simple JWT proxy不需要 REST特有 features，要求降低 request cost與 backend負載。
   - Correct principle：若 feature fit成立可選較低成本 HTTP API；若重複 GET適合 caching則評估 REST cache或 CloudFront，並計入 cache correctness與 invalidation。
   - Distractors：D1 為省錢移除 authentication；D2 所有 request改 WebSocket；D3 將 throttling設無限可降低單價。
   - Task/source：`SAA-4.2`, `SAP-2.6` / `api-rest-http`

8. **SAA — private API access**
   - Intent：只有 VPC內 workloads可呼叫 REST API，不能走 public internet。
   - Correct principle：使用 private REST API、execute-api interface VPC endpoint、resource policy限制 endpoint/VPC/principal，並正確設定 private DNS與 security groups。
   - Distractors：D1 edge-optimized public endpoint配難猜 URL；D2 只設定 API key；D3 NAT Gateway會把 public API自動變 private。
   - Task/source：`SAA-1.2` / `api-auth`

9. **SAP — multi-Region API failover**
   - Intent：regional APIs跨兩 Region，要求低 RTO、custom domain與資料一致性設計。
   - Correct principle：每 Region部署獨立 Regional API/backend，使用 Route 53/Global Accelerator適用入口與健康策略；同步處理 certificates、DNS、identity、state replication及 idempotent failover。
   - Distractors：D1 單一 edge-optimized API自動複寫 backend資料；D2 降 TTL即可保證零 RTO且現有 connections切換；D3 只複製 Lambda code便完成 DR。
   - Task/source：`SAP-2.4` / `api-operations`

10. **Multi-response — secure public API（選兩項）**
    - Intent：internet-facing API需使用者身份、濫用保護與可控 backend負載。
    - Correct principles：C1 使用適合的 JWT/IAM/Lambda authorizer並在 backend執行 resource-level authorization；C2 配置 throttling/quota、WAF或 rate controls及可觀測的 4XX/5XX/latency alarms。
    - Distractors：D1 只用 API key作 authentication；D2 CORS阻止所有非瀏覽器攻擊；D3 將 Lambda reserved concurrency取消以避免 429。
    - Task/source：`SAA-1.2`, `SAA-2.1` / `api-auth`, `api-operations`

---

## 第 38 章：ECS、EKS、Fargate 與 ECR

### Current-question audit

- **Q1 combined-answer flaw:** 題幹同時有「無 Kubernetes經驗的十個服務」與「必須使用 K8s operator的 vendor產品」，答案把 ECS/EKS/Fargate全部列出，沒有要求將兩個 workload分開選型。
- **Q2 list recognition only:** 沒有測 `taskRoleArn`與 `executionRoleArn`的差別，也沒有要求可部署的 task definition。
- **Q3 basic but incomplete:** 只描述 ECS scheduler，未涵蓋 EC2/Fargate capacity、networking、health或 image pull。
- **Q4 redundant:** 再次要求選 ECS。
- **Q5 generic:** 沒有 cluster upgrade、capacity provider、deployment circuit breaker、PDB、ECR digest或 supply-chain control。
- **Missing:** ECS/EKS choice、Fargate/EC2 boundary、task/execution role、`awsvpc` ENI、service scaling、deployment health、image pull failure、Spot capacity、EKS upgrade與 ECR immutability.

### Ten replacement intents

1. **Service choice — ECS versus EKS versus Fargate**
   - Intent：分開呈現 AWS-native microservices、Kubernetes operator workload及需 privileged/daemon/host access的 workload。
   - Correct principle：無 K8s contract時 ECS降低平台負擔；需 Kubernetes API/operator時選 EKS；ECS/EKS都可視限制使用 Fargate，需 host/daemon/特殊 instance控制時用 EC2 nodes。
   - Distractors：D1 所有 containers都選 EKS；D2 Fargate是獨立 orchestrator可取代 ECS/EKS；D3 ECR能排程 containers所以不需 orchestrator。
   - Task/source：`SAA-3.2`, `SAP-4.4` / `containers-choice`

2. **Runtime mechanism — ECS service scheduling**
   - Intent：追蹤 ECR image、task definition、service desired count、capacity provider、ENI與 target group。
   - Correct principle：task definition定義 image/resources/roles；service scheduler在 capacity provider上維持 tasks；`awsvpc`為 task配置 ENI，LB target group只路由 healthy tasks。
   - Distractors：D1 ECR repository policy決定 desired task count；D2 ALB listener直接建立 Fargate capacity；D3 task role負責 ECS agent拉 image且 execution role只供 application使用。
   - Task/source：`SAA-2.1` / `ecs-runtime`

3. **Scaling signal — service and cluster capacity**
   - Intent：ECS service CPU低但 ALB request latency與 requests/target升高，另有 tasks因無 capacity停在 Pending。
   - Correct principle：service scaling依 workload metric增加 task desired count；EC2 capacity provider/cluster scaling另負責增加 container instances，兩層都需有容量與正確 signal。
   - Distractors：D1 增加 ECR repository size；D2 只增加 task desired count且忽略 cluster capacity；D3 只擴 EC2 nodes但固定 service desired count。
   - Task/source：`SAA-3.2`, `SAP-2.5` / `ecs-scaling`

4. **Concrete config — task role and execution role**
   - Intent：container需讀 DynamoDB，ECS agent需從 private ECR拉 image並寫 logs。
   - Correct principle：application AWS API權限放 task role；image pull、secret retrieval與 log driver等 agent動作放 execution role；兩者皆 least privilege。
   - Distractors：D1 全部放 EC2 instance role並共用 AdministratorAccess；D2 repository public即可解決 DynamoDB權限；D3 security group可授權 `dynamodb:GetItem`。
   - Task/source：`SAA-1.2` / `ecs-runtime`, `ecr-supply-chain`

5. **Health/draining — rolling ECS deployment**
   - Intent：新 task啟動慢且有長連線，要求避免部署期間容量不足或中斷。
   - Correct principle：設定 container/target-group health、health grace、minimum/maximum healthy percent或 circuit breaker，並配合 target deregistration delay與 application graceful shutdown。
   - Distractors：D1 新 image push後立即 stop全部舊 tasks；D2 只增加 ECR scan frequency；D3 把 health command固定為 `exit 0`。
   - Task/source：`SAA-2.2`, `SAP-2.4` / `ecs-scaling`

6. **Failure diagnosis — CannotPullContainerError**
   - Intent：private-subnet tasks無法啟動並回報 image pull timeout/authorization error。
   - Correct principle：分別查 execution-role ECR權限、repository policy、image tag/digest、DNS與到 ECR/S3的 NAT或 VPC endpoints；不要把 task role當 execution role。
   - Distractors：D1 提高 ALB idle timeout；D2 增加 service desired count；D3 修改 application DynamoDB permissions。
   - Task/source：`SAP-3.3` / `ecs-runtime`, `ecr-supply-chain`

7. **Cost — Fargate versus EC2/Spot**
   - Intent：bursty小服務與高利用率大型 fleet，要求依 utilization與操作成本選 capacity。
   - Correct principle：Fargate適合免節點管理與變動需求；穩定高利用率可比較 EC2 capacity providers/Savings Plans，容錯 workloads可加入 Fargate Spot/EC2 Spot並分散容量。
   - Distractors：D1 Fargate在所有 utilization下必然最低成本；D2 EKS control plane費用會讓 ECS tasks免費；D3 將 CPU/memory request設為零以不計費。
   - Task/source：`SAA-4.2`, `SAP-2.6` / `containers-choice`, `ecs-scaling`

8. **SAA — Fargate networking**
   - Intent：Fargate task需 private IP、只接受 ALB流量並存取 S3/ECR。
   - Correct principle：使用 `awsvpc`、private subnets與 task security group；inbound只允許 ALB SG，outbound透過適合的 VPC endpoints/NAT取得依賴。
   - Distractors：D1 Fargate不在 VPC內所以不能用 SG；D2 每個 task必須有 public IP才能拉 ECR；D3 host network mode是 Fargate唯一模式。
   - Task/source：`SAA-1.2`, `SAA-3.2` / `ecs-runtime`

9. **SAP — EKS platform lifecycle**
   - Intent：多團隊 EKS platform需升級 control plane/nodes/add-ons且維持服務。
   - Correct principle：盤點 version skew與 deprecated APIs，先測 add-ons/workloads，再逐批更新 managed node groups；用 PDB、readiness與足夠 spare capacity控制 disruption。
   - Distractors：D1 直接升 production control plane並假設 nodes/pods自動相容；D2 PDB保證 application永不故障；D3 把所有 pods設為不可驅逐即可永久升級。
   - Task/source：`SAP-2.4`, `SAP-4.4` / `eks-operations`

10. **Multi-response — container supply chain（選兩項）**
    - Intent：production只能部署已核准、不可被 tag覆寫的 images，並需跨 Region恢復。
    - Correct principles：C1 啟用 ECR tag immutability/scanning並在 deployment鎖定 image digest；C2 設計 cross-Region/account replication與 repository policy/KMS權限，並驗證目標環境可 pull。
    - Distractors：D1 production永遠使用 `latest`；D2 只掃描 running ALB；D3 將 repository設 public以簡化 DR。
    - Task/source：`SAP-2.3`, `SAP-2.4` / `ecr-supply-chain`

---

## 第 39 章：Batch、EMR 與大型計算

### Current-question audit

- **Q1 broad mapping rather than a decision:** 同時放 Spark ETL、百萬轉檔與 HPC，答案直接列 Batch/EMR/Spot，沒有 workload-specific constraint。
- **Q2 list recognition:** 只問 Batch設定名，未要求 job definition、queue與 compute environment如何互動。
- **Q3 basic:** scheduler敘述正確但未測 jobs長期 RUNNABLE、dependency/retry或 capacity behavior。
- **Q4 redundant:** 與 Q1/Q2再次選 Batch。
- **Q5 generic:** 沒有 data locality、checkpoint、Spot interruption、transient cluster、EMR Serverless或 job-level evidence。
- **Missing:** Batch queue priority、array/multi-node jobs、retry/timeout、compute environment故障、EMR deployment modes、managed scaling、Spot diversification、checkpoint與 orchestration/execution邊界。

### Ten replacement intents

1. **Service choice — Batch versus EMR versus Step Functions**
   - Intent：分別給 containerized independent jobs、Spark/Hadoop distributed data processing與多服務 workflow orchestration。
   - Correct principle：AWS Batch排程可排隊 container jobs；EMR提供 Spark/Hadoop execution engine；Step Functions編排步驟/重試但不是資料處理 engine。
   - Distractors：D1 每個短 job啟一個 EMR cluster；D2 用 Step Functions state transition執行 TB級 shuffle；D3 用 Batch取代所有 Spark framework semantics。
   - Task/source：`SAA-3.2` / `batch-runtime`, `emr-runtime`

2. **Runtime mechanism — Batch queue to compute**
   - Intent：追蹤 submit job、job queue priority、job definition、scheduler與 managed compute environment。
   - Correct principle：job definition描述 image/resources/role/retry；job進 queue後由 scheduler依 priority/dependency與可用 compute environment配置 EC2/Spot/Fargate capacity。
   - Distractors：D1 queue直接保存 input data並取代 S3；D2 job definition建立固定 EC2且永不擴縮；D3 Step Functions必須存在 Batch才能排程。
   - Task/source：`SAA-2.1` / `batch-runtime`

3. **Scaling signal — runnable jobs and resource shape**
   - Intent：大量 jobs長期 RUNNABLE但 compute environment vCPU尚未達 max，要求診斷 capacity scaling。
   - Correct principle：查看 job resource shape、instance-type/GPU相容性、max vCPU、Spot/On-Demand capacity、subnet IP與 service role；queue depth本身不保證可 placement。
   - Distractors：D1 只增加 S3 bucket容量；D2 降低 job timeout會建立更多 instances；D3 增加 Step Functions execution history。
   - Task/source：`SAP-2.5`, `SAP-3.3` / `batch-runtime`

4. **Concrete config — retry, timeout and array jobs**
   - Intent：十萬個相同分片可獨立重試，單一分片不得超過 30 分鐘。
   - Correct principle：使用 array jobs或適當 job decomposition，job definition設定 resource requirements、timeout與按 exit reason的 retry strategy；輸入/output外部化。
   - Distractors：D1 一個巨大 job內自行 fork十萬 process且無 checkpoint；D2 queue retention取代 job timeout；D3 對所有 exit code無限 retry。
   - Task/source：`SAA-2.1`, `SAA-2.2` / `batch-runtime`

5. **Health/draining — Spot interruption handling**
   - Intent：長 batch job跑在 Spot，收到 interruption/rebalance signal時要求減少重算。
   - Correct principle：工作需 checkpoint/idempotent，捕捉 termination signal保存進度，由 queue/retry在其他 capacity重啟；不要把 local instance store當唯一 checkpoint。
   - Distractors：D1 忽略通知因 Spot一定跑完；D2 將 retry attempts設零；D3 把 checkpoint只寫到即將終止的 host。
   - Task/source：`SAA-2.2` / `spot-interruption`, `batch-runtime`

6. **Failure diagnosis — EMR job slow/failing**
   - Intent：Spark stage skew、executor loss與 S3 I/O造成 job超時，要求分層診斷。
   - Correct principle：先看 Spark stage/task metrics與 logs，辨認 skew/shuffle/memory；再檢查 fleet capacity、Spot loss、S3 partition/layout及 network，而非只擴 master node。
   - Distractors：D1 增加 Route 53 TTL；D2 改 ALB health path；D3 只增加 primary node storage即可修所有 executor bottleneck。
   - Task/source：`SAP-3.3` / `emr-runtime`

7. **Cost — transient and managed capacity**
   - Intent：每日兩小時 ETL與全天候互動 cluster，要求比較 transient EMR、EMR Serverless、reserved/Spot capacity。
   - Correct principle：短暫/間歇作業評估 transient cluster或 Serverless並把資料放 S3；穩定需求再比較長駐 capacity，task nodes/容錯部分可用 diversified Spot。
   - Distractors：D1 為每日作業保留最大 cluster全天；D2 將 HDFS作唯一 durable copy後每次 terminate；D3 一律使用 On-Demand最大 instance。
   - Task/source：`SAA-4.2`, `SAP-2.6` / `emr-runtime`, `spot-interruption`

8. **SAA — orchestration versus execution**
   - Intent：ETL需先啟動 EMR job，成功後更新 catalog，失敗時通知並人工核准重跑。
   - Correct principle：Step Functions適合保存 workflow state、branch/retry/callback並呼叫 EMR/Batch integrations；真正 Spark/compute仍由 EMR/Batch執行。
   - Distractors：D1 Step Functions直接取代 Spark executors；D2 EventBridge schedule可保存所有步驟補償狀態；D3 CloudWatch dashboard執行 human approval。
   - Task/source：`SAA-2.1` / `emr-runtime`

9. **SAP — multi-account data processing platform**
   - Intent：中央 data account保存 S3資料，多 workload accounts提交 jobs，要求隔離、成本歸屬與可恢復。
   - Correct principle：分離 data permissions、job role與 compute environment；以 tags/queues/accounts隔離優先級與成本，output/checkpoints寫 durable cross-account storage並保留 audit trail。
   - Distractors：D1 所有 teams共用一個 admin job role；D2 將中間與結果只留在 instance store；D3 以單一 queue且無 priority/quota保證公平。
   - Task/source：`SAP-2.5`, `SAP-2.6` / `batch-runtime`, `emr-runtime`

10. **Multi-response — interruption-tolerant batch fleet（選兩項）**
    - Intent：百萬個可重試 jobs需大幅降低成本且在單一 Spot pool短缺時繼續。
    - Correct principles：C1 使用多 instance families/sizes/AZ與 capacity-optimized allocation分散 Spot pool；C2 jobs採小批次、idempotency與 durable checkpoint，並保留必要 On-Demand fallback。
    - Distractors：D1 固定單一最低價 Spot type；D2 將 queue與結果都放 instance store；D3 關閉 retry避免重複。
    - Task/source：`SAP-2.4`, `SAP-2.6` / `spot-interruption`, `batch-runtime`

---

## 第 40 章：Elastic Beanstalk、App Runner 與 Managed Platforms

### Current-question audit

- **Q1 ambiguous:** 「標準 Python web app、不管理 cluster、autoscaling、TLS」同時可由 Beanstalk與 App Runner滿足；標準答案又同時列兩者，沒有用 host control、deployment source或 networking需求決勝。
- **Q2 list recognition:** 沒有把 platform version、environment type、deployment policy或 `.ebextensions`映射到實際行為。
- **Q3 partial:** Beanstalk確實管理底層 resources，但題目稱 request/data path，答案其實是 control-plane provisioning，概念標籤錯置。
- **Q4 redundant:** 再次選 Beanstalk。
- **Q5 generic:** 沒有測 immutable/rolling/traffic-splitting deployment、App Runner autoscaling、VPC connector方向、custom domain或平台 escape hatch。
- **Missing:** platform choice boundaries、control plane versus data plane、concurrency scaling、health paths、deployment policies、VPC connector outbound semantics、private ingress、cost floor與何時退回 ECS/EKS。

### Ten replacement intents

1. **Service choice — Beanstalk versus App Runner versus Lightsail**
   - Intent：比較需要 EC2/ASG/ALB control的傳統 app、從 source/image快速上線的 stateless HTTP service及單一低複雜固定預算網站。
   - Correct principle：需保留底層 AWS resource控制選 Beanstalk；想把 build/deploy/runtime autoscaling交給平台且契約是 web service選 App Runner；小型固定 bundle可選 Lightsail。
   - Distractors：D1 App Runner適合任意 privileged host agent；D2 Lightsail是大型 multi-account platform首選；D3 Beanstalk不使用 EC2所以無法調 instance。
   - Task/source：`SAA-3.2`, `SAA-4.2` / `beanstalk-runtime`, `apprunner-runtime`, `lightsail-scope`

2. **Runtime mechanism — control plane versus request path**
   - Intent：分辨 Beanstalk environment provisioning與 App Runner request runtime。
   - Correct principle：Beanstalk以 environment configuration建立/更新 EC2、ASG、LB等 resources，request仍經 LB到 instances；App Runner建立 managed service endpoint並在平台 runtime中部署與擴縮 instances。
   - Distractors：D1 Beanstalk本身逐 request執行 Python handler；D2 App Runner VPC connector是 public HTTP load balancer；D3 Lightsail blueprint持續重新編譯每個 request。
   - Task/source：`SAA-3.2` / `beanstalk-runtime`, `apprunner-runtime`

3. **Scaling signal — App Runner concurrency**
   - Intent：App Runner service latency在尖峰上升，要求理解 min/max size與 per-instance concurrency。
   - Correct principle：autoscaling configuration以最小/最大 instances與 concurrency門檻控制容量；門檻須由每 instance實測吞吐與 latency SLO決定。
   - Distractors：D1 concurrency設越高一定 latency越低；D2 VPC connector數量就是 instance capacity；D3 repository image size決定 request scaling。
   - Task/source：`SAA-3.2` / `apprunner-runtime`

4. **Concrete config — Beanstalk deployment policy**
   - Intent：production需在更新 platform/app時維持完整容量並能快速 rollback，問 rolling、immutable、traffic splitting的選擇。
   - Correct principle：依容量與風險選 immutable或 traffic splitting建立新 capacity並驗證，再替換舊版；rolling可能在部署期間降低 capacity，需明確批次與 health設定。
   - Distractors：D1 all-at-once最適合所有 zero-downtime production；D2 `.ebextensions`可取代版本與 rollback；D3 single-instance environment等同跨 AZ HA。
   - Task/source：`SAA-2.2`, `SAP-2.1` / `beanstalk-runtime`

5. **Health/draining — managed-platform release**
   - Intent：新版本 process啟動成功但 `/health`依賴 database失敗，且舊 requests仍在處理。
   - Correct principle：配置真實 application health path、合理 startup grace與 deployment health threshold；平台切流/終止前讓舊 instances draining並由 application graceful shutdown。
   - Distractors：D1 health endpoint固定回 200；D2 只看 build成功；D3 立即刪舊 environment再測新版本。
   - Task/source：`SAA-2.2`, `SAP-2.4` / `beanstalk-runtime`, `apprunner-runtime`

6. **Failure diagnosis — App Runner VPC networking**
   - Intent：App Runner加 VPC connector後可連 private database，但突然不能連 public package/API endpoint。
   - Correct principle：VPC connector影響 service的 outbound VPC traffic；需在所選 subnets提供 NAT或所需 VPC endpoints/routes/SG。它不等同 inbound private endpoint。
   - Distractors：D1 將 public DNS TTL設低；D2 增加 App Runner max instances；D3 只新增 custom domain certificate。
   - Task/source：`SAP-3.3` / `apprunner-runtime`

7. **Cost — abstraction and idle floor**
   - Intent：低流量服務、穩定高利用率服務與需要大量自訂 sidecars的服務，要求比較平台總成本。
   - Correct principle：比較 provisioned/active compute、request模式、底層 EC2利用率與操作人力；高階平台降低 operations但可能有 idle floor/feature premium，需求超出抽象時 ECS/EC2可能更合適。
   - Distractors：D1 managed程度越高計算費必然越低；D2 Lightsail bundle可無限水平擴展且不增費；D3 Beanstalk服務本身免費所以底層 resources也免費。
   - Task/source：`SAA-4.2`, `SAP-2.6` / `beanstalk-runtime`, `apprunner-runtime`, `lightsail-scope`

8. **SAA — choose the smallest sufficient platform**
   - Intent：單一 stateless container web API從 ECR部署，需 autoscaling、TLS與最少 platform management，無 Kubernetes/host需求。
   - Correct principle：App Runner符合 managed web-service contract；只有需要更多 network/orchestration/sidecar/host控制時才升級到 ECS/EKS/Beanstalk。
   - Distractors：D1 EKS因功能最多；D2 Dedicated Hosts因 TLS；D3 AWS Batch因 image在 ECR。
   - Task/source：`SAA-3.2`, `SAA-4.2` / `apprunner-runtime`, `containers-choice`

9. **SAP — escape-hatch and modernization boundary**
   - Intent：Beanstalk app逐漸需要多個 independently scaled services、service discovery、sidecars與複雜 deployment policy。
   - Correct principle：當需求持續繞過平台 abstraction時，規劃以 strangler/wave遷移到 ECS/EKS等適合 orchestrator；先量測依賴、外部化 state並保留 rollback。
   - Distractors：D1 無限增加 `.ebextensions` shell hooks；D2 所有 services塞回同一 process；D3 直接重寫成 Lambda且不評估 timeout/state。
   - Task/source：`SAP-4.4` / `beanstalk-runtime`, `containers-choice`

10. **Multi-response — production managed web platform（選兩項）**
    - Intent：小團隊使用 App Runner/Beanstalk上 production，要求 safe release與 private dependency access。
    - Correct principles：C1 使用 versioned artifact/image與 application health metrics進行 staged/immutable rollout及 rollback；C2 明確設計 outbound VPC routes/endpoints/SG與 secret/IAM role，使 private dependency可達且 least privilege。
    - Distractors：D1 使用 mutable `latest`且每次自動覆寫 production；D2 將 database放 public subnet以省去 networking；D3 把 build成功視為 production health。
    - Task/source：`SAP-2.1`, `SAP-2.4` / `beanstalk-runtime`, `apprunner-runtime`

---

## Implementation acceptance criteria

- 每章實作後必須恰好 10 題，至少 7 題單選、至少 2 題五選二；第 10 題固定為複選。
- 同章任兩題不得只有服務名稱或 scenario noun不同；跨章不得重用完整 prompt、choice或 explanation句。
- 單選題 choices必須語義互斥；不得讓「正確原則的子集合」同時作為另一個未標答案的選項。
- 每個 explanation必須指出該選項違反的具體 service contract、metric、scope、lifecycle或 cost boundary。
- 每章至少兩題包含可觀察 evidence（metric、status/reason code、log、health state），至少兩題包含具體 configuration relationship。
- `task/source`必須同時包含公開 exam task與 AWS官方 product key；community notes只能補常見誤區，不能作服務行為的唯一依據。
- 自動檢查至少拒絕：同題 choices重複、跨題 prompt高度相似、同一正確 choice重用、答案未完整滿足 scenario、複選答案數錯誤。

SUPERSET_WORKER_DONE
task: P03-audit
scope: chapters 32-40
artifact: tools/aws_exam_audits/part_03.md
chapters_audited: 9
question_intents: 90
status: complete
