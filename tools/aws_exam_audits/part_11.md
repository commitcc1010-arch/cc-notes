# P11 Audit：第 105–116 章跨雲 Architecture Patterns

稽核日期：2026-10-01
範圍：只稽核 `AWS Solutions Architect/12 - patterns.md` 的章末五題，並定義替代命題 intent；不重製、改寫或推測真實考題，也不使用 exam dumps。

## 審核契約

- 每章恰好 10 個互不重疊的 knowledge coverage intents。
- 每個 intent 都包含正確原則、三個 plausible distractor concepts、SAA-C03 或 SAP-C02 task mapping，以及 AWS 官方 source key。
- 每章至少包含 failure diagnosis、cost/operations 與 multi-response reasoning；第 10 個 intent 固定為複選推理。
- Portable pattern 必須映射回具體 AWS service、configuration、failure signal 與 operating action，不能只留下抽象口號。
- 截至本稽核日，SAP-C02 仍是現行 Professional exam；AWS 已公告 SAP-C03 於 2026-10-27 開放註冊，SAP-C02 最後應試日為 2026-11-17。本文因此保留專案現有 SAP-C02 task keys，後續應另做 C03 delta audit。

## 跨章共同缺陷

1. 十二章全部套用相同五題模板：Q1 背 decision、Q2 背 primary service 設定清單、Q3 背 profile mechanism、Q4 再選一次 primary service、Q5 固定加入 multi-account/canary/rollback。題型重複而知識密度低。
2. 每章的 decision 與 alternative 都逐字重複出現在 Q1 與 Q5；Q2 的設定清單又在 Q4 原樣重現。五題通常只提供約兩個獨立知識點。
3. 「全部部署」「服務自動理解 business requirements」「等事故後人工處理」「先給 organization-wide AdministratorAccess」反覆充當 distractor，明顯錯誤而不 plausible。
4. 概念章被 `primary component` 生成規則強迫對應單一產品。結果把 Availability Zones、AWS Organizations、Route 53、CloudWatch、AWS Backup、Cost Explorer 或 Migration Hub 當成整個 pattern 的充分實作。
5. Q3 一律詢問 `request/data path`，即使主題實際是 governance、billing、backup、migration portfolio 或 control plane；問題模型與服務責任不相符。
6. Q5 的 generic rollout 答案沒有綁定 queue receipt、cell、cache key、configuration version、recovery point、billing dataset 或 migration wave，不能測 SAP 的具體 operating model。
7. 現況幾乎沒有數值、configuration interaction、failure signal、quota、data freshness、RTO/RPO evidence、unit economics 或 rollback precondition。
8. 多章把另一個正確原則標成錯誤 alternative；在題幹沒有額外 constraint 時形成多重正解。
9. 第 111 章錯把 feature-flag/local-cache 問題的 primary service 設為 Route 53；第 116 章仍向新客戶推薦已停止接受新客戶的 Migration Hub。
10. 替代題庫應測「何時 pattern 不適用」以及服務設定如何實作 pattern，而不是把 portable principle、產品名稱與「least operational overhead」綁成固定口訣。

## Official source key registry

### Exam scope and official practice

- `saa-guide` — [SAA-C03 Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)
- `saa-d1` — [SAA-C03 Domain 1](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)
- `saa-d2` — [SAA-C03 Domain 2](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain2.html)
- `saa-d3` — [SAA-C03 Domain 3](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain3.html)
- `saa-d4` — [SAA-C03 Domain 4](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain4.html)
- `sap-guide` — [SAP-C02 Exam Guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)
- `sap-d1` — [SAP-C02 Domain 1](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain1.html)
- `sap-d2` — [SAP-C02 Domain 2](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain2.html)
- `sap-d3` — [SAP-C02 Domain 3](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)
- `sap-d4` — [SAP-C02 Domain 4](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain4.html)
- `cert-saa` — [AWS Certified Solutions Architect – Associate preparation page](https://aws.amazon.com/certification/certified-solutions-architect-associate/)
- `cert-sap` — [AWS Certified Solutions Architect – Professional preparation and version notice](https://aws.amazon.com/certification/certified-solutions-architect-professional/)

### Architecture and service behavior

- `wa-ops` — [Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)
- `wa-observe` — [Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)
- `wa-rel` — [Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)
- `wa-bulkhead` — [REL10-BP03 Use bulkhead architectures](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_fault_isolation_use_bulkhead.html)
- `wa-sec` — [Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
- `wa-cost` — [Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)
- `builders-static` — [Static stability using Availability Zones](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)
- `builders-shuffle` — [Workload isolation using shuffle sharding](https://aws.amazon.com/builders-library/workload-isolation-using-shuffle-sharding/)
- `cell-router` — [Serverless cell-router pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/serverless-cell-router-architecture.html)
- `cell-guide` — [Reducing scope of impact with cell-based architecture](https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/welcome.html)
- `rds-overview` — [What is Amazon RDS?](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)
- `rds-multiaz` — [RDS Multi-AZ deployments](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html)
- `msk-overview` — [What is Amazon MSK?](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html)
- `fargate-ecs` — [Architect for AWS Fargate for Amazon ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- `sqs-vis` — [SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)
- `sqs-dlq` — [SQS dead-letter queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)
- `sqs-metrics` — [CloudWatch metrics for SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)
- `asg-sqs` — [Scale an Auto Scaling group from SQS backlog](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-using-sqs-queue.html)
- `eventbridge-patterns` — [EventBridge event patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)
- `eventbridge-retry` — [EventBridge retry policy and DLQ](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-retry-policy.html)
- `stepfn-types` — [Standard and Express Workflows](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html)
- `ec2-az` — [Regions and Availability Zones](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html)
- `elb-health` — [ALB target-group health checks](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html)
- `org-isolation` — [SEC01-BP01 Separate workloads using accounts](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_securely_operate_multi_accounts.html)
- `route53-health` — [Route 53 health checks and DNS failover](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover.html)
- `elasticache-cache` — [ElastiCache caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)
- `dax-consistency` — [DAX and DynamoDB consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.consistency.html)
- `cloudfront-cache` — [CloudFront cache key](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)
- `appconfig-overview` — [What is AWS AppConfig?](https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html)
- `appconfig-deploy` — [Deploying AppConfig configuration](https://docs.aws.amazon.com/appconfig/latest/userguide/deploying-feature-flags.html)
- `appconfig-agent` — [AppConfig Agent local cache for ECS/EKS](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-integration-containers-agent.html)
- `ssm-agent` — [Working with SSM Agent](https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent.html)
- `iam-eval` — [IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)
- `vpc-sg` — [VPC security groups](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)
- `vpc-nacl` — [VPC network ACLs](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html)
- `kms-concepts` — [AWS KMS key concepts](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html)
- `lf-permissions` — [Lake Formation permissions reference](https://docs.aws.amazon.com/lake-formation/latest/dg/lf-permissions-reference.html)
- `cw-slo` — [CloudWatch Application Signals SLOs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)
- `cw-alarms` — [Using CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Alarms.html)
- `xray` — [What is AWS X-Ray?](https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html)
- `synthetics` — [CloudWatch Synthetics canaries](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html)
- `dr-options` — [Disaster recovery options on AWS](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)
- `backup-plan` — [Create an AWS Backup plan](https://docs.aws.amazon.com/aws-backup/latest/devguide/creating-a-backup-plan.html)
- `backup-restore-test` — [AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)
- `aurora-global-dr` — [Aurora Global Database switchover and failover](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)
- `cost-explorer` — [Analyzing costs with Cost Explorer](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html)
- `cur` — [AWS Cost and Usage Reports](https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html)
- `compute-optimizer` — [What is AWS Compute Optimizer?](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html)
- `budgets` — [Managing costs with AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
- `migration-wave` — [Migration wave planning](https://docs.aws.amazon.com/prescriptive-guidance/latest/application-portfolio-assessment-guide/wave-planning.html)
- `migration-7rs` — [Migration strategy: the 7 Rs](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html)
- `migrationhub-change` — [Migration Hub availability change](https://docs.aws.amazon.com/transform/latest/launchguide/migrationhub-availability-change.html)
- `transform-wave` — [AWS Transform migration planning](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-review-groupings-and-waves.html)
- `mgn` — [What is AWS Application Migration Service?](https://docs.aws.amazon.com/mgn/latest/ug/what-is-application-migration-service.html)
- `dms` — [What is AWS Database Migration Service?](https://docs.aws.amazon.com/dms/latest/userguide/Welcome.html)
- `datasync` — [What is AWS DataSync?](https://docs.aws.amazon.com/datasync/latest/userguide/what-is-datasync.html)

---

## 第 105 章：Managed Service 優先與 Escape Hatch

### 現有題目缺陷

- Q1 沒有給 relational、Kafka、container workload 的實際需求，卻直接把 RDS 當主要答案；「選最高 managed abstraction」與「自管以滿足特殊 protocol/compliance」都可能合理。
- Q2 與 Q4 重複同一組 RDS 設定；沒有測 engine compatibility、Multi-AZ/read replica 差異、quota、maintenance、restore 或 migration path。
- Q3 的 RDS mechanism 基本正確，但只考 profile recognition；沒有驗證 customer 仍負責 schema、query、identity、capacity planning 與 recovery objectives。
- Q5 再次重複 Q1 decision，generic canary/guardrail 與 database 或 streaming migration 的實際 rollback unit 無關。
- 本章應比較完整 TCO、責任矩陣、不可接受的 feature gap、資料可攜性、quota、exit trigger 與 coexistence migration。

### Portable pattern → AWS services and configuration

| Portable pattern | AWS implementation | Configuration / evidence |
|---|---|---|
| 購買 undifferentiated operations | RDS、MSK、ECS on Fargate | RDS engine/Multi-AZ/backups；MSK mode/brokers/partitions/auth；Fargate task CPU/memory/network/IAM |
| 保留 differentiating contract | Application schema/API/event contract | Versioned schema、idempotency、RTO/RPO、load test、service quota alarms |
| 預先設計 escape hatch | DMS、DataSync、Kafka-compatible clients、portable container image | Export/replication test、target compatibility、cutover/rollback runbook、data reconciliation |

### Ten replacement intents

1. **Responsibility boundary — managed does not mean zero ownership.**
   - Correct principle: AWS can own infrastructure provisioning, patching and common recovery tasks while the customer still owns data model, access, query/application behavior, capacity assumptions and business correctness.
   - Distractors: managed service guarantees correct schema；AWS owns every RTO/RPO decision；customer must patch the RDS host OS.
   - Task/source: `SAA-1.2, SAA-2.2` / `rds-overview, fargate-ecs`

2. **Service choice — choose abstraction from the required contract.**
   - Correct principle: choose RDS for managed relational semantics, MSK when Kafka protocol/ecosystem is a hard requirement, and Fargate for container execution without node management; “most managed” is subordinate to functional constraints.
   - Distractors: choose RDS for any persistent state；choose MSK for every asynchronous job；choose Fargate to obtain a managed database.
   - Task/source: `SAA-2.1, SAA-3.2, SAA-3.3` / `rds-overview, msk-overview, fargate-ecs`

3. **Escape-hatch design — define portability before adoption.**
   - Correct principle: record data/export formats, protocol compatibility, service quotas, unavailable features, target alternatives and measurable exit triggers before the managed service becomes critical.
   - Distractors: portability means avoiding all AWS-specific features；a backup alone proves another engine can ingest the data；quota increases eliminate every feature gap.
   - Task/source: `SAP-2.4, SAP-4.3, SAP-4.4` / `rds-overview, msk-overview`

4. **Concrete configuration — turn a managed default into a production contract.**
   - Correct principle: explicitly configure version, topology, encryption, network, backup/retention, maintenance, monitoring and quotas; defaults are inputs to review, not proof of fitness.
   - Distractors: Multi-AZ also supplies arbitrary read scaling；encryption automatically grants KMS use；latest engine version removes upgrade testing.
   - Task/source: `SAA-1.3, SAA-2.2, SAA-3.3` / `rds-overview, kms-concepts`

5. **Migration path — coexist before irreversible cutover.**
   - Correct principle: test target compatibility, replicate or export representative data, run shadow/canary traffic where semantics permit, reconcile results, freeze writes deliberately and preserve a bounded rollback path.
   - Distractors: restore the first production backup only after cutover；dual-write forever without reconciliation；DNS rollback reverses incompatible data changes.
   - Task/source: `SAP-2.1, SAP-4.2, SAP-4.3` / `rds-overview, migration-wave`

6. **Failure diagnosis — managed service is healthy but the workload fails.**
   - Correct principle: distinguish service health from quota exhaustion, throttling, connection/partition limits, unsupported features, client retry behavior and downstream saturation before replacing the service.
   - Distractors: healthy control-plane status proves data-plane success；increase instance size for every authorization failure；open network access to bypass a quota.
   - Task/source: `SAP-3.3, SAP-3.4` / `rds-overview, msk-overview, fargate-ecs`

7. **Cost/operations — compare TCO, not unit price.**
   - Correct principle: compare service charges with idle capacity, staffing, on-call, patch/upgrade work, backup testing, failure risk, migration effort and opportunity cost at the same SLO.
   - Distractors: self-managed is cheaper whenever hourly compute is lower；managed is always cheaper；engineering labor is outside architecture cost.
   - Task/source: `SAA-4.2, SAA-4.3, SAP-2.6` / `wa-cost, wa-ops`

8. **SAA scenario — select the least operationally burdensome valid option.**
   - Correct principle: first eliminate options that miss SQL/Kafka/container requirements, then choose the valid design with the smallest customer-managed infrastructure surface and explicit HA/backup/security settings.
   - Distractors: always choose serverless；always choose EC2 for control；select the option listing the most services.
   - Task/source: `SAA-2.1, SAA-2.2` / `saa-d2, rds-overview, fargate-ecs`

9. **SAP operating model — govern managed services as a portfolio.**
   - Correct principle: assign service owners, approved versions, quota reviews, upgrade waves, exception criteria, portability tests and deprecation/exit plans across accounts.
   - Distractors: central team receives permanent admin in every account；each workload silently chooses any engine version；a second Region replaces ownership and runbooks.
   - Task/source: `SAP-1.4, SAP-3.1, SAP-4.4` / `sap-d1, sap-d3, wa-ops`

10. **Multi-response — adopt a managed database with a credible exit path (choose two).**
    - Correct principle: choose both a production RDS contract with tested backup/HA/security and a periodically tested export/replication plus compatibility/reconciliation plan; either alone is incomplete.
    - Distractors: avoid backups because Multi-AZ exists；build a self-managed standby without testing data semantics；grant broad admin so migration tools cannot be blocked.
    - Task/source: `SAP-2.4, SAP-4.2` / `rds-overview, migration-wave`

---

## 第 106 章：Decouple Independently Scalable Components

### 現有題目缺陷

- Q1 的 asynchronous decision 與「同步仍適合即時確認」並不互斥；題幹沒有指定 upload response 必須確認到哪個 durable boundary。
- Q2 與 Q4 重複 SQS 設定清單，沒有逐一測 visibility、retention、DLQ、FIFO、long polling 或 batch 的效果。
- Q3 只背 receive/visibility/delete 流程，未測 duplicate delivery、idempotency、partial failure 或 poison-message recovery。
- EventBridge 與 Step Functions 只當錯誤 peer，未測 fan-out routing、workflow state、callback、archive/replay 或 cross-account permissions。
- Q5 沒有把 event schema、queue ownership、consumer rollout、redrive 或 backward compatibility納入 SAP migration。

### Portable pattern → AWS services and configuration

| Portable pattern | AWS implementation | Configuration / evidence |
|---|---|---|
| 分離 arrival rate 與 processing rate | SQS + Lambda/ECS workers | Queue type、visibility、batch、DLQ、consumer concurrency、oldest-message age |
| 分離 producer 與多個 consumers | EventBridge/SNS → per-consumer targets/queues | Event pattern/filter、target retry/DLQ、resource policy、schema version |
| 顯式保存 workflow state | Step Functions | Standard/Express、Retry/Catch、timeout、callback token、execution history |

### Ten replacement intents

1. **Contract boundary — decide what the synchronous response guarantees.**
   - Correct principle: acknowledge only after the required durable acceptance point; background outcomes use status/event callbacks, while operations needing immediate business confirmation remain synchronous.
   - Distractors: enqueue and wait for every consumer before responding；return success before any durable write；make every read asynchronous.
   - Task/source: `SAA-2.1` / `saa-d2, sqs-vis`

2. **Work distribution — use SQS for competing consumers.**
   - Correct principle: one work item is processed by one logical consumer attempt, with visibility, delete-after-commit, idempotency and DLQ behavior aligned to processing time.
   - Distractors: one shared queue gives every subscriber a copy；delete on receipt to prevent duplicates；retention controls invisibility.
   - Task/source: `SAA-2.1, SAA-2.2` / `sqs-vis, sqs-dlq`

3. **Event routing — use EventBridge for fact-based fan-out.**
   - Correct principle: publish stable domain facts, match event fields with rules, and give failure-sensitive consumers their own buffering/retry boundary.
   - Distractors: EventBridge is an ordered replay log；a matching rule authorizes the target；input transformation is equivalent to filtering.
   - Task/source: `SAA-2.1, SAP-2.4` / `eventbridge-patterns, eventbridge-retry`

4. **Orchestration — use Step Functions when state and sequencing matter.**
   - Correct principle: choose a workflow when retries, branches, compensation, long waits or audit history are part of one business process; routing a fact alone does not require orchestration.
   - Distractors: sleep inside Lambda for human approval；use SQS receipt order as a multi-step state machine；use Express for every multi-day callback.
   - Task/source: `SAA-2.1, SAP-2.1` / `stepfn-types`

5. **Delivery semantics — design for duplicate and partial processing.**
   - Correct principle: make side effects idempotent, set visibility above normal work time, extend long jobs, delete only after commit and isolate poison messages with a tested redrive policy.
   - Distractors: Standard queues provide exactly-once business effects；FIFO removes the need for idempotency；DLQ is permanent archival storage.
   - Task/source: `SAA-2.2` / `sqs-vis, sqs-dlq`

6. **Failure diagnosis — producer succeeded but work never completed.**
   - Correct principle: trace acceptance, rule/queue delivery, visible/in-flight counts, oldest age, retries/DLQ, consumer errors/throttles and downstream latency to find the first broken handoff.
   - Distractors: successful `SendMessage` proves the side effect committed；increase retention before checking consumers；inspect only producer CPU.
   - Task/source: `SAP-3.4` / `sqs-metrics, eventbridge-retry, wa-observe`

7. **Cost/operations — reduce polling and orchestration waste.**
   - Correct principle: use long polling, right-sized batches, bounded retention, appropriate workflow type and selective telemetry; avoid paying to process expired or duplicate work.
   - Distractors: short poll continuously for lowest cost；larger batches always reduce failure cost；archive every event indefinitely.
   - Task/source: `SAA-4.2, SAP-2.6` / `sqs-metrics, stepfn-types, wa-cost`

8. **SAA scenario — asynchronous image processing.**
   - Correct principle: store the upload durably, enqueue independent transformations, scale consumers from backlog/age and expose completion status without blocking the upload request.
   - Distractors: call every transformer synchronously；use one Lambda invocation that sleeps until approval；use EventBridge alone as a work backlog.
   - Task/source: `SAA-2.1, SAA-2.2` / `saa-d2, sqs-vis`

9. **SAP operating model — evolve contracts across accounts.**
   - Correct principle: version event schemas compatibly, scope bus/queue policies, assign retry/DLQ owners, deploy consumers independently and preserve replay/redrive evidence during migration.
   - Distractors: rename fields in place because JSON is schemaless；share one DLQ without source ownership；grant organization-wide event publication.
   - Task/source: `SAP-1.4, SAP-2.4, SAP-4.4` / `sap-d1, eventbridge-patterns, eventbridge-retry`

10. **Multi-response — make asynchronous processing recoverable (choose two).**
    - Correct principle: choose both idempotent delete-after-commit consumers with visibility/DLQ controls and end-to-end correlation/status evidence for every handoff.
    - Distractors: acknowledge before durable acceptance；disable retries to avoid duplicates；increase queue retention instead of consumer capacity.
    - Task/source: `SAP-2.4, SAP-3.4` / `sqs-vis, sqs-dlq, wa-observe`

---

## 第 107 章：Eliminate Single Points of Failure

### 現有題目缺陷

- Q2/Q4 把 Availability Zones 當成可「選擇並設定」的單一服務；AZ 分散只有在 compute、ingress、state、egress 與 dependency 都實作時才成立。
- Q1 的 dependency inventory 是合理原則，但沒有讓考生找出具體單點，例如單 AZ NAT、不可讀 standby、單一 IdP、KMS policy owner 或 deployment operator。
- Q3 只考 AZ 定義；沒有測 static stability、failure detection、capacity after failure 或 client reconnect。
- Q4 宣稱選 AZ 加一串泛設定即可消除單點，未涵蓋 data tier、DNS、identity、secrets、quota 或 operational authority。
- Q5 generic rollout 沒有要求 game day、failover evidence、N+1 capacity、return path 或 recovery owner。

### Portable pattern → AWS services and configuration

| Portable pattern | AWS implementation | Configuration / evidence |
|---|---|---|
| 跨 failure domain 放置 redundant capacity | Multi-AZ ASG/ECS + ELB | Subnets across AZs、health checks、deregistration、minimum healthy capacity |
| 資料層自動 failover | RDS Multi-AZ/Aurora | Standby/readable topology、endpoint、backup、failover alarms、client reconnect |
| 故障時不依賴受損 control plane | Static per-AZ capacity、Route 53/ARC data-plane controls | N+1 capacity、zonal evacuation test、routing-control runbook |

### Ten replacement intents

1. **Dependency inventory — identify every required single owner/path.**
   - Correct principle: enumerate ingress, compute, state, egress, identity, keys, DNS, deployment and human approval dependencies; availability is bounded by every required link.
   - Distractors: three EC2 instances guarantee HA；managed services cannot be single dependencies；only servers count as SPOFs.
   - Task/source: `SAA-2.2, SAP-1.3` / `wa-rel, builders-static`

2. **Compute/ingress — survive loss of one AZ.**
   - Correct principle: place healthy capacity and load-balancer nodes/targets across multiple AZs, retain sufficient post-failure capacity and drain/replace failed targets automatically.
   - Distractors: three instances in one AZ；one target group with one healthy target；cross-zone routing creates capacity in an empty AZ.
   - Task/source: `SAA-2.2` / `ec2-az, elb-health`

3. **Data topology — distinguish HA from read scaling.**
   - Correct principle: use an RDS topology whose failover semantics meet the requirement; traditional Multi-AZ standby provides HA, while read replicas address read capacity and can lag.
   - Distractors: every Multi-AZ standby serves reads；a read replica guarantees synchronous zero-RPO failover；backup schedule provides live HA.
   - Task/source: `SAA-2.2, SAA-3.3` / `rds-multiaz`

4. **Egress and network path — avoid a hidden zonal choke point.**
   - Correct principle: route each private subnet through an appropriate healthy egress path and validate return routes, endpoints and cross-AZ dependencies; one shared zonal appliance can defeat multi-AZ compute.
   - Distractors: a NAT gateway is automatically cross-Region；security groups supply missing routes；cross-AZ NAT has no resilience or cost trade-off.
   - Task/source: `SAA-2.2, SAA-3.4, SAA-4.4` / `ec2-az, wa-rel`

5. **Static stability — preserve existing service during control impairment.**
   - Correct principle: pre-provision or locally cache what the data plane needs so existing traffic can continue when capacity, configuration or orchestration control APIs are impaired.
   - Distractors: create all replacement capacity only after the outage；perform a fresh control lookup per request；use retries without a bounded fallback.
   - Task/source: `SAP-1.3, SAP-2.4` / `builders-static, dr-options`

6. **Failure diagnosis — “multi-AZ” label but outage still occurs.**
   - Correct principle: verify actual resource placement, healthy capacity, state replication, DNS/endpoint behavior, dependency AZs, quotas and client retry/reconnect; labels do not prove the critical path.
   - Distractors: lower DNS TTL for every database error；add a fourth instance in the failed AZ；assume an ELB health check validates data correctness.
   - Task/source: `SAP-3.4` / `elb-health, rds-multiaz, wa-observe`

7. **Cost/operations — buy only the failure domains the SLO needs.**
   - Correct principle: compare Multi-AZ and Multi-Region cost, cross-AZ transfer, idle headroom, failover automation and test burden against quantified business impact.
   - Distractors: active-active is always cheapest；Single-AZ plus snapshots meets an availability SLO；redundant idle capacity has no value.
   - Task/source: `SAA-4.2, SAA-4.3, SAP-2.6` / `wa-cost, dr-options`

8. **SAA scenario — highly available regional web application.**
   - Correct principle: use multi-AZ load-balanced stateless compute plus a matching HA data tier, and remove local session/state dependencies.
   - Distractors: single-AZ ASG behind CloudFront；multi-AZ compute with Single-AZ database；store sessions on one instance and enable stickiness.
   - Task/source: `SAA-2.1, SAA-2.2` / `saa-d2, elb-health, rds-multiaz`

9. **SAP operating model — prove automatic replacement and recovery.**
   - Correct principle: run zonal game days, measure capacity and business success after failure, test DNS/client behavior, assign owners and preserve rollback/failback procedures.
   - Distractors: rely only on service SLA；declare success when resources show `running`；test failover without business transactions.
   - Task/source: `SAP-1.3, SAP-2.4, SAP-3.4` / `sap-d1, wa-rel, builders-static`

10. **Multi-response — remove two independent critical-path SPOFs (choose two).**
    - Correct principle: choose both multi-AZ ingress/compute with post-failure capacity and a tested HA data/identity/key path that applications can reconnect to.
    - Distractors: add instances only to one AZ；create an unused second Region without data；depend on one person to approve every failover.
    - Task/source: `SAA-2.2, SAP-2.4` / `elb-health, rds-multiaz, wa-rel`

---

## 第 108 章：Blast Radius 與 Cell-based Architecture

### 現有題目缺陷

- Q2–Q4 將 AWS Organizations 當成 cell-based runtime architecture；accounts/OUs/SCPs 能提供治理與隔離，但不會建立 cell router、tenant mapping、per-cell capacity 或 data partition。
- Q1 的 cell principle 正確，但沒有指定 partition key、cell size、mapping ownership、cross-cell dependency 或 reassignment semantics。
- Route 53 與 DynamoDB 只當相鄰服務，未測 thin router、cell map、tenant pinning、shuffle sharding 或 per-cell state。
- Q5 仍是通用 canary；真正的 rollout unit 應是 cell，且需避免一次更新所有 cells。
- 缺少 noisy-neighbor quota、global-layer minimization、cell evacuation、N+1 capacity、data movement 和 duplicated-capacity cost。

### Portable pattern → AWS services and configuration

| Portable pattern | AWS implementation | Configuration / evidence |
|---|---|---|
| 將 workload 切成獨立 cells | Separate AWS accounts/Regions or repeated per-cell stacks | Per-cell VPC/compute/queue/database/quota、independent alarms and deployments |
| Global layer 只做 routing | Route 53/CloudFront/API Gateway/Lambda router + DynamoDB mapping | Tenant-to-cell map、health-aware route、small stateless router、cached mapping |
| 限制 noisy-neighbor overlap | Tenant shards、SQS fair queues/message groups、shuffle sharding | Per-tenant quotas、concurrency limits、contributor metrics、isolation test |

### Ten replacement intents

1. **Cell boundary — choose partition key and maximum impact.**
   - Correct principle: define which tenants/users/partitions share a cell, size cells from acceptable impact and capacity, and keep authoritative state inside the assigned cell.
   - Distractors: partition only by random request；place every tenant in all cells；treat an OU as a runtime shard.
   - Task/source: `SAP-1.3, SAP-2.4` / `cell-guide, wa-bulkhead`

2. **Thin routing layer — route without becoming the largest cell.**
   - Correct principle: the router should perform only stable tenant-to-cell lookup and health-aware forwarding, scale horizontally, cache mappings and avoid business processing or shared mutable workload state.
   - Distractors: put all authorization and transactions in one router instance；query every cell per request；let the router create cells synchronously on demand.
   - Task/source: `SAP-2.4, SAP-2.5` / `cell-router, builders-static`

3. **State isolation — avoid cross-cell synchronous dependencies.**
   - Correct principle: each cell owns its compute, queues and data; shared services must be minimized, replicated, partitioned or made non-critical so one failure does not cross boundaries.
   - Distractors: use one global database for every write；share one queue without tenant limits；call another cell synchronously for normal requests.
   - Task/source: `SAP-1.3, SAP-3.4` / `cell-guide, wa-bulkhead`

4. **Account and organization boundary — use the right isolation layer.**
   - Correct principle: AWS accounts provide strong security/billing boundaries and Organizations applies guardrails, but application cells still require routing, capacity and data isolation inside or across accounts.
   - Distractors: an SCP distributes application traffic；an OU is an availability zone；consolidated billing merges failure domains.
   - Task/source: `SAP-1.4` / `org-isolation, sap-d1`

5. **Noisy-neighbor control — isolate disproportionate tenants.**
   - Correct principle: enforce per-tenant admission, concurrency and storage limits; use shard/message-group assignment and contributor signals so one tenant cannot consume the cell.
   - Distractors: only increase global capacity；use one constant partition key for order；monitor aggregate CPU without tenant dimensions.
   - Task/source: `SAA-2.1, SAP-2.5` / `builders-shuffle, sqs-metrics`

6. **Failure diagnosis — one cell failure affects all customers.**
   - Correct principle: find shared router, identity, queue, database, configuration or deployment dependencies; verify tenant mapping and that alarms/automation act on one cell rather than the fleet.
   - Distractors: add more tenants to the failed cell；fail every cell together for consistency；inspect only the affected cell's EC2 CPU.
   - Task/source: `SAP-3.4` / `cell-guide, wa-observe`

7. **Cost/operations — balance isolation with duplicated capacity.**
   - Correct principle: model per-cell fixed headroom, data duplication, deployment/observability overhead and cell-movement cost against reduced incident impact and safer rollout.
   - Distractors: maximum number of cells is always cheapest；one global cell has no risk cost；unused failover capacity should never be funded.
   - Task/source: `SAP-1.5, SAP-2.6` / `wa-cost, cell-guide`

8. **SAA scenario — isolate a high-volume enterprise tenant.**
   - Correct principle: assign the tenant to an isolated shard/cell with its own capacity and data path while keeping the routing contract stable for the client.
   - Distractors: add the tenant to the same hot partition；give it organization administrator access；move only DNS while retaining the shared bottleneck.
   - Task/source: `SAA-2.1, SAA-2.2` / `saa-d2, builders-shuffle`

9. **SAP operating model — deploy by cell and preserve rollback.**
   - Correct principle: version the same cell stack, canary one low-risk cell, observe business/error metrics, roll through waves, and keep cell-specific rollback and ownership.
   - Distractors: update all cells simultaneously for consistency；allow configuration drift per cell without inventory；use only a global dashboard.
   - Task/source: `SAP-2.1, SAP-3.1, SAP-3.4` / `sap-d2, sap-d3, cell-guide`

10. **Multi-response — contain a tenant-specific overload (choose two).**
    - Correct principle: choose both tenant-to-cell/shuffle-shard assignment with per-tenant limits and independent per-cell capacity/data/deployment boundaries.
    - Distractors: one global queue with no attribution；one global database connection pool；a thick router that executes every transaction.
    - Task/source: `SAP-1.3, SAP-2.4` / `builders-shuffle, cell-router, wa-bulkhead`

---

## 第 109 章：Queue 吸收 Burst，而非無限 Overload

### 現有題目缺陷

- Q1 的 broad answer 同時塞入 bounded backlog、age SLO、autoscaling、admission control 和 shedding，沒有測任何一項如何配置；SQS 本身也沒有可直接設定的 max queue depth。
- Q2 與 Q4 再次重複完整 SQS profile；與第 106 章高度重疊，沒有聚焦 sustained overload。
- Q3 只背 receive lifecycle，不測 arrival rate、service rate、queueing delay、deadline 或 in-flight saturation。
- `增加 retention 不增加 capacity` 是正確原則，卻只當 alternative 重複；題目應要求計算其對 stale work 與成本的影響。
- 缺少 backlog-per-worker target、oldest age、noisy tenant/fair queue metrics、expired-work dropping 和 downstream protection。

### Portable pattern → AWS services and configuration

| Portable pattern | AWS implementation | Configuration / evidence |
|---|---|---|
| Buffer short burst | SQS Standard/FIFO | Retention、visibility、batch、DLQ、message deadline attribute |
| Scale service rate | EC2 Auto Scaling/Lambda/ECS consumers | Backlog per worker、oldest age、maximum concurrency、scale-in protection |
| Bound accepted work | Producer admission/rate limit + load shedding | Request quota、deadline check、tenant limits、rejection metric |

### Ten replacement intents

1. **Queueing math — compare arrival and service rates.**
   - Correct principle: a queue drains only when sustained service capacity exceeds arrival rate; if λ remains above μ, backlog and age grow until retention/deadline loss.
   - Distractors: more retention increases μ；more queue partitions always increase consumer capacity；depth can remain bounded when λ exceeds μ forever.
   - Task/source: `SAA-2.1, SAP-2.5` / `sqs-metrics, wa-rel`

2. **SLO signal — age and deadline matter more than depth alone.**
   - Correct principle: monitor oldest-message age, visible/in-flight counts and business deadline; the same depth can be acceptable or failed depending on processing time and value horizon.
   - Distractors: message count equals latency in every workload；retention is the business deadline；NumberOfMessagesReceived counts unique completed work.
   - Task/source: `SAA-2.2, SAP-3.3` / `sqs-metrics`

3. **Autoscaling metric — scale from backlog per active worker.**
   - Correct principle: target acceptable backlog per worker from latency SLO divided by average processing time; raw queue depth is not proportional to fleet capacity.
   - Distractors: scale only from average CPU；divide backlog by desired rather than active capacity during failure；set target to queue retention seconds.
   - Task/source: `SAA-3.2, SAP-2.5` / `asg-sqs`

4. **Admission and shedding — bound work outside the queue.**
   - Correct principle: reject, defer or degrade low-value work before enqueue when capacity/deadline budget is exhausted, and drop expired work explicitly rather than processing stale requests.
   - Distractors: purge the whole queue on every alarm；increase retention indefinitely；return success while silently discarding required work.
   - Task/source: `SAP-2.4, SAP-2.5` / `wa-rel, sqs-metrics`

5. **Consumer lifecycle — protect long and duplicate-prone work.**
   - Correct principle: align visibility with processing, extend with heartbeat, make effects idempotent, delete after commit and use DLQ/redrive for repeated failure.
   - Distractors: delete before work begins；set visibility to zero for long jobs；use `maxReceiveCount=1` for every transient error.
   - Task/source: `SAA-2.2` / `sqs-vis, sqs-dlq`

6. **Failure diagnosis — queue age rises after consumer scale-out.**
   - Correct principle: inspect active workers, in-flight limit, errors/throttles, processing duration, hot FIFO groups, downstream saturation and expired work; more workers may only move the bottleneck.
   - Distractors: conclude low worker CPU means no bottleneck；increase queue retention；add consumers beyond the database connection budget.
   - Task/source: `SAP-3.3, SAP-3.4` / `sqs-metrics, asg-sqs`

7. **Cost/operations — stop paying for empty or obsolete work.**
   - Correct principle: use long polling/batching, right-size retention, filter expired work, tune concurrency to downstream capacity and measure cost per completed business unit.
   - Distractors: short poll at maximum frequency；retain poison messages forever in the source queue；maximize batch size regardless of partial failures.
   - Task/source: `SAA-4.2, SAP-2.6` / `sqs-metrics, wa-cost`

8. **SAA scenario — absorb a short promotion burst.**
   - Correct principle: enqueue durable independent work, size baseline plus elastic consumers to drain within the latency target, and alarm on age/DLQ rather than accepting unlimited delay.
   - Distractors: synchronous calls to every worker；one FIFO message group for all orders；retention increase as the only scaling action.
   - Task/source: `SAA-2.1, SAA-3.2` / `saa-d2, asg-sqs`

9. **SAP operating model — protect quiet tenants from a noisy tenant.**
   - Correct principle: attribute messages by tenant/group, enforce quotas, use fair-queue or shard isolation where appropriate, and monitor noisy versus quiet-group age before moving tenants.
   - Distractors: aggregate all tenants under one unlabelled stream；raise every tenant's limit together；use one global DLQ with no source metadata.
   - Task/source: `SAP-1.3, SAP-2.5, SAP-3.3` / `sqs-metrics, builders-shuffle`

10. **Multi-response — recover from sustained overload (choose two).**
    - Correct principle: choose both capacity/backlog-per-worker scaling within downstream limits and producer-side admission/deadline shedding that prevents unbounded obsolete work.
    - Distractors: increase retention only；disable DLQ to preserve order；process oldest work even after its business deadline.
    - Task/source: `SAP-2.4, SAP-2.5` / `asg-sqs, sqs-metrics`

---

## 第 110 章：Cache 不是正確性來源

### 現有題目缺陷

- Q1 對 authorization cache 只回答一般 TTL/invalidation；未要求撤權時 fail-safe、最大 stale window、negative cache 或 bypass path。
- Q2/Q4 重複 ElastiCache 設定清單，沒有測 cache-aside race、eviction、cluster mode、replica lag、endpoint/failover 或 memory pressure。
- Q3 的 application-managed cache flow 基本正確，但沒有比較 ElastiCache、DAX 與 CloudFront 的不同 cache contract。
- Q1 的 write-through/read-through alternative 也是正確補充原則，題幹不足以把它排除。
- Q5 generic rollout 沒有處理 cache key/version、warm-up、dual read、invalidation fan-out 或 cold-cache backend protection。

### Portable pattern → AWS services and configuration

| Portable pattern | AWS implementation | Configuration / evidence |
|---|---|---|
| Cache 加速 authoritative store | ElastiCache Valkey/Redis OSS/Memcached | TTL、eviction、cluster mode、replicas/Multi-AZ、memory/connection metrics |
| API-compatible read cache | DAX in front of DynamoDB | Item/query TTL、node/AZ topology、eventual-read tolerance、write path |
| HTTP edge cache | CloudFront | Cache policy/key、TTL、headers/cookies/query strings、invalidation/versioned paths |

### Ten replacement intents

1. **Authority — identify the durable source of truth.**
   - Correct principle: cache contents may disappear or become stale; correctness-critical reads and writes require a named authoritative store and a valid miss/degraded path.
   - Distractors: Redis replica makes the cache authoritative automatically；cache persistence replaces database backup；a cache miss proves the entity does not exist.
   - Task/source: `SAA-2.2, SAA-3.3` / `elasticache-cache`

2. **Cache-aside flow — make miss handling explicit.**
   - Correct principle: read cache, fetch the authoritative store on miss, populate with bounded TTL and return; node loss increases latency but must not change truth.
   - Distractors: clients query the database only after TTL reaches half；a new empty node is fatal by definition；lazy loading prevents stale values.
   - Task/source: `SAA-3.3` / `elasticache-cache`

3. **Freshness — coordinate writes, invalidation and TTL.**
   - Correct principle: define write-through, write-around or invalidate-after-write semantics, handle partial failure/order races and use TTL as a bound rather than a correctness proof.
   - Distractors: write-through cannot fail partially；delete cache before an uncommitted database write and correctness is guaranteed；TTL zero maximizes hit ratio.
   - Task/source: `SAP-2.4, SAP-2.5` / `elasticache-cache, dax-consistency`

4. **Security/inventory cache — fail safely on stale privilege or stock.**
   - Correct principle: revoked access or unavailable inventory must not remain allowed solely because of stale cache; use short bounded freshness, version/revocation signals and authoritative confirmation for high-risk actions.
   - Distractors: cache `allow` forever for availability；treat cache miss as authorization deny in every public-data use case；use longer TTL during an incident.
   - Task/source: `SAA-1.2, SAP-2.3` / `wa-sec, elasticache-cache`

5. **Stampede protection — prevent synchronized origin overload.**
   - Correct principle: combine TTL jitter, request coalescing/single-flight, stale-while-revalidate or controlled warm-up with origin rate limits.
   - Distractors: expire every hot key at the same second；remove all TTLs；let every miss independently query the database.
   - Task/source: `SAA-2.1, SAP-2.5` / `elasticache-cache, wa-rel`

6. **Failure diagnosis — hit ratio drops and database latency spikes.**
   - Correct principle: inspect evictions, memory fragmentation, expired keys, key cardinality, client endpoint/failover, hot keys and origin capacity; identify whether cache loss or origin slowdown came first.
   - Distractors: add database replicas before checking evictions；increase TTL for revoked permissions；assume Multi-AZ eliminates cold-cache effects.
   - Task/source: `SAP-3.3, SAP-3.4` / `elasticache-cache, wa-observe`

7. **Cost/operations — optimize useful hit ratio, not cache size alone.**
   - Correct principle: right-size nodes/serverless usage, TTL and cache-key cardinality; compare memory/requests/data transfer with origin savings and operational failover needs.
   - Distractors: cache every unique response indefinitely；include all cookies in every CloudFront cache key；largest cluster always has lowest cost per useful hit.
   - Task/source: `SAA-4.3, SAP-2.6` / `cloudfront-cache, wa-cost`

8. **SAA scenario — choose ElastiCache, DAX or CloudFront.**
   - Correct principle: use ElastiCache for general application data structures/sessions, DAX for DynamoDB-compatible eventually consistent acceleration, and CloudFront for HTTP edge caching.
   - Distractors: use DAX for relational joins；use CloudFront as a Redis session store；use ElastiCache to authorize AWS API calls.
   - Task/source: `SAA-3.3, SAA-3.4` / `elasticache-cache, dax-consistency, cloudfront-cache`

9. **SAP operating model — deploy cache changes without origin collapse.**
   - Correct principle: version cache keys, canary TTL/policy changes, pre-warm only justified hot sets, cap miss concurrency and retain rollback compatible with old/new data formats.
   - Distractors: flush every production cache at once；change serialized format in place without key version；disable origin protection during warm-up.
   - Task/source: `SAP-2.1, SAP-3.3` / `elasticache-cache, cloudfront-cache`

10. **Multi-response — make a permission cache safe (choose two).**
    - Correct principle: choose both an authoritative authorization decision/revocation path and a bounded TTL/versioned invalidation design whose failure mode denies or rechecks high-risk actions.
    - Distractors: persist cached allows indefinitely；treat network location as authorization；make cache availability the only SLO.
    - Task/source: `SAP-2.3, SAP-2.4` / `wa-sec, elasticache-cache`

---

## 第 111 章：Control Plane 與 Data Plane 分離

### 現有題目缺陷

- Q1 的 scenario 明確是 feature flag/local last-known-safe configuration，但解析錯稱答案是 Route 53 能力；primary component mapping 與題意矛盾。
- Q2/Q4 選 Route 53 設定而把 AppConfig 當 distractor，屬明確錯誤。AppConfig 的 validators、deployment strategy、CloudWatch rollback 與 Agent cache 才直接實作本章 pattern。
- Q3 只描述 DNS mechanism，沒有回答 feature-flag data plane 如何在 control plane/network impairment 下繼續。
- `強一致 control lookup per request` 被當可翻轉 alternative，但對高可用 runtime path 通常是待避免依賴；題目沒有提出必須即時撤權的特殊條件。
- 缺少 configuration version、local cache initialization、poll interval/retrieval cost、rollback alarm、emergency override 和 stale-policy boundary。

### Portable pattern → AWS services and configuration

| Portable pattern | AWS implementation | Configuration / evidence |
|---|---|---|
| 發布後由 local state 提供 runtime read | AWS AppConfig Agent | Local endpoint/cache、poll interval、IAM data-plane actions、initialization behavior |
| 慢速且可驗證的 control update | AppConfig configuration profile/deployment | Validators、deployment strategy、bake time、CloudWatch alarm rollback、version |
| 故障切換依賴高可用 data-plane control | Route 53/ARC routing controls | Health checks、routing controls、TTL、pre-created endpoints/runbook |

### Ten replacement intents

1. **Classification — identify control-plane and data-plane operations.**
   - Correct principle: creating/updating configuration or resources is control-plane work; serving requests with already published state is data-plane work and should not require a fresh management operation.
   - Distractors: every AWS API is data plane；DNS record update and cached answer are the same operation；CloudFormation handles each user request.
   - Task/source: `SAA-2.2, SAP-2.4` / `dr-options, builders-static`

2. **Local configuration — survive temporary AppConfig/network impairment.**
   - Correct principle: retrieve deployed configuration through AppConfig Agent/local cache and define a last-known-safe/default startup policy; do not block every request on remote configuration lookup.
   - Distractors: call `StartDeployment` per request；discard cached configuration on transient timeout；store secrets in feature flags for convenience.
   - Task/source: `SAA-2.2` / `appconfig-overview, appconfig-agent`

3. **Safe publication — validate, stage and automatically roll back.**
   - Correct principle: use configuration profiles/validators, gradual deployment strategy, bake time and business/technical CloudWatch alarms to revert harmful configuration.
   - Distractors: edit all production parameters directly；rollback only application binaries；treat syntax validation as business validation.
   - Task/source: `SAA-1.2, SAP-2.1` / `appconfig-deploy, cw-alarms`

4. **Freshness boundary — decide when stale configuration is unsafe.**
   - Correct principle: classify flags by acceptable staleness; availability-oriented tuning can use last-known-safe state, while revocation/kill decisions may require shorter TTL, version checks or a fail-safe path.
   - Distractors: one poll interval fits every flag；stale authorization always fails open；zero cache TTL improves resilience.
   - Task/source: `SAP-2.3, SAP-2.4` / `appconfig-agent, wa-sec`

5. **Fleet operations — keep SSM out of the per-request path.**
   - Correct principle: use Systems Manager documents/associations/automation for fleet management, but applications should not require Run Command or a live management session to serve normal traffic.
   - Distractors: execute an SSM document for every HTTP request；open SSH when SSM is delayed；store request state in Automation executions.
   - Task/source: `SAA-1.2, SAP-3.1` / `ssm-agent, wa-ops`

6. **Failure diagnosis — control plane is unavailable and traffic stops.**
   - Correct principle: identify synchronous management/config lookups, cache initialization gaps, expired credentials, missing endpoints and untested defaults; prove existing published state can continue independently.
   - Distractors: repeatedly create new resources；lower every TTL to zero；increase application CPU.
   - Task/source: `SAP-3.4` / `builders-static, appconfig-agent, wa-observe`

7. **Cost/operations — control retrieval frequency and rollout toil.**
   - Correct principle: use local agent caching and rational polling, consolidate configuration reads, automate validation/rollback and retain only necessary versions/telemetry.
   - Distractors: remote fetch per request is cheapest；poll every millisecond for all flags；manual all-at-once edits reduce operational cost.
   - Task/source: `SAP-1.5, SAP-2.6, SAP-3.1` / `appconfig-overview, wa-cost`

8. **SAA scenario — safe feature flag for ECS tasks.**
   - Correct principle: deploy a validated flag gradually with AppConfig, retrieve through a sidecar/local endpoint, alarm on business errors and continue with cached last-known-safe data during a service/network interruption.
   - Distractors: use Route 53 weighted records as the flag store；restart all tasks for every flag read；query Parameter Store remotely on every request without cache.
   - Task/source: `SAA-1.2, SAA-2.2` / `appconfig-deploy, appconfig-agent`

9. **SAP operating model — govern configuration across accounts/Regions.**
   - Correct principle: separate author/approver/deployer roles, version configuration, deploy in waves, replicate required sources/keys, predefine emergency controls and audit every change.
   - Distractors: share one administrator credential；allow each Region to drift silently；depend on creating recovery resources during the outage.
   - Task/source: `SAP-1.4, SAP-2.1, SAP-3.1` / `sap-d1, appconfig-deploy, wa-ops`

10. **Multi-response — preserve runtime during configuration failure (choose two).**
    - Correct principle: choose both local last-known-safe/default serving and validated gradual control-plane deployment with alarms/automatic rollback.
    - Distractors: synchronous control lookup for every request；all-at-once production update；Route 53 as the primary feature-flag database.
    - Task/source: `SAP-2.4, SAP-3.4` / `appconfig-agent, appconfig-deploy`

---

## 第 112 章：Identity、Network、Data 三層安全

### 現有題目缺陷

- Q1 的 identity/network/data 分工與 defense-in-depth 敘述同時正確，卻只標前者。
- Q2/Q3 只測 IAM 設定與 policy evaluation，未測題名中的 network reachability 或 data authorization/encryption。
- Q4 需求明確要求三層控制，正解卻只選 IAM，屬不完整方案；private VPC、KMS/Lake Formation 與 application tenant authorization仍缺失。
- IAM 設定清單偏向 users/access keys，未鼓勵 federation、roles、temporary credentials、SCP/RCP、permissions boundary 與 resource policy。
- Q5 generic governance 沒有處理 key policy、cross-account trust、SG/NACL return traffic、Lake Formation column filters 或 evidence chain。

### Portable pattern → AWS services and configuration

| Portable pattern | AWS implementation | Configuration / evidence |
|---|---|---|
| Identity：誰能做什麼 | IAM/Identity Center/Organizations | Role trust、identity/resource policies、SCP/RCP、permissions boundary、Access Analyzer |
| Network：封包能否到達 | VPC routes、SG、NACL、PrivateLink/endpoints | Source/destination/port、stateful return、ordered NACL rules、flow logs |
| Data：取得後能看哪一部分 | KMS + service policy + Lake Formation | Key policy/grant、encryption context、table/column/row grants、retention/backup |

### Ten replacement intents

1. **Layering — separate authentication, reachability and data use.**
   - Correct principle: identity authorization, network path filtering and data encryption/fine-grained access address different failure modes and must all satisfy the request.
   - Distractors: private subnet grants tenant authorization；KMS encryption blocks all network access；security group determines database row permissions.
   - Task/source: `SAA-1.1, SAA-1.2, SAA-1.3` / `saa-d1, wa-sec`

2. **IAM evaluation — compute effective permission.**
   - Correct principle: evaluate identity/resource grants with boundaries, session policies and Organizations controls; any applicable explicit deny overrides an allow.
   - Distractors: SCP grants permissions directly；resource policy always overrides explicit deny；permissions boundary expands identity permissions.
   - Task/source: `SAA-1.1, SAP-2.3` / `iam-eval`

3. **Network controls — distinguish SG and NACL behavior.**
   - Correct principle: security groups are stateful resource/ENI controls; NACLs are stateless ordered subnet controls requiring explicit return-path rules.
   - Distractors: SG rules are processed in numeric order；NACL automatically allows responses；route tables perform IAM authorization.
   - Task/source: `SAA-1.2, SAA-3.4` / `vpc-sg, vpc-nacl`

4. **KMS authorization — data policy and key policy both matter.**
   - Correct principle: caller/service access to encrypted data must also be authorized to use the KMS key; choose AWS owned/managed/customer managed key according to control, audit, sharing and cost needs.
   - Distractors: `s3:GetObject` always grants `kms:Decrypt`；AWS managed keys can be freely shared cross-account；encryption removes the need for TLS.
   - Task/source: `SAA-1.3, SAP-2.3` / `kms-concepts, iam-eval`

5. **Fine-grained analytics — apply Lake Formation permissions.**
   - Correct principle: use Lake Formation grants/data filters for table/column/row scope while retaining necessary IAM and registered-location permissions.
   - Distractors: VPC membership grants all table columns；`DESCRIBE` permits queries；KMS key access alone grants Lake Formation `SELECT`.
   - Task/source: `SAA-1.3, SAP-2.3` / `lf-permissions`

6. **Failure diagnosis — private service receives AccessDenied or leaks data.**
   - Correct principle: trace principal/session, identity/resource/SCP/RCP/key policies, route/SG/NACL, service data permissions and application tenant checks; “private” proves only reachability constraints.
   - Distractors: open the SG to fix KMS denial；grant administrator to diagnose permanently；assume successful TCP connection proves row authorization.
   - Task/source: `SAP-3.2` / `iam-eval, vpc-sg, kms-concepts, lf-permissions`

7. **Cost/operations — design sustainable security telemetry and keys.**
   - Correct principle: use the minimum necessary customer-managed keys, scoped logs/flow logs and reusable guardrails while preserving audit, rotation, retention and incident evidence.
   - Distractors: one customer-managed key per object without need；disable logs to reduce cost；one global administrator role reduces security toil safely.
   - Task/source: `SAP-1.5, SAP-3.1, SAP-3.2` / `kms-concepts, wa-cost, wa-sec`

8. **SAA scenario — private analytics with column restrictions.**
   - Correct principle: use role-based access, private network paths/SGs, encryption and Lake Formation column grants; each control remains independently reviewable.
   - Distractors: private subnet alone；KMS decrypt alone；NACL rule alone.
   - Task/source: `SAA-1.1, SAA-1.2, SAA-1.3` / `saa-d1, lf-permissions`

9. **SAP operating model — multi-account security ownership.**
   - Correct principle: separate workloads by account, apply organization guardrails, delegate security services, centralize evidence and let workload owners manage scoped runtime permissions without management-account workloads.
   - Distractors: all teams share management-account admin；one flat VPC is the security boundary；SCPs replace IAM roles.
   - Task/source: `SAP-1.2, SAP-1.4, SAP-3.2` / `org-isolation, wa-sec`

10. **Multi-response — authorize a cross-account encrypted data query (choose two).**
    - Correct principle: choose both explicit principal/resource/Lake Formation authorization for the intended data scope and compatible KMS key policy/grants plus a permitted network path.
    - Distractors: public endpoint with secret URL；identity policy only when destination denies access；SG reference as the database authorization rule.
    - Task/source: `SAP-2.3, SAP-3.2` / `iam-eval, kms-concepts, lf-permissions`

---

## 第 113 章：Observability 跟隨 Business Outcome

### 現有題目缺陷

- Q1 的 business-first observability 與 synthetic/real-user telemetry 都是正確且互補；把前者標唯一答案造成歧義。
- Q2/Q4 重複 CloudWatch 設定清單，未要求 custom business metric、dimension cardinality、percentile、missing-data policy 或 alarm action。
- Q3 只考 telemetry ingestion；沒有測 metrics/logs/traces 的角色或如何從 stale outcome 找到 queue/downstream cause。
- Q4 單選 CloudWatch 仍不完整：需 application instrumentation、SLO、trace context、synthetic/RUM 和 runbook，不是建立 dashboard 即完成。
- Q5 中 synthetic/RUM 也是合理第二答案，現行 `C、D` 之外存在第三個正確概念。

### Portable pattern → AWS services and configuration

| Portable pattern | AWS implementation | Configuration / evidence |
|---|---|---|
| 先量測 user/business outcome | CloudWatch custom metrics/Application Signals SLO | Success、latency、freshness、correctness、SLI period/error budget |
| 再用 internals 解釋 | CloudWatch metrics/logs + X-Ray/OTel traces | Correlation ID、dimensions、percentiles、sampling、service map |
| 從外部持續驗證 | CloudWatch Synthetics and real-user signals | Canary schedule/script/steps、alarms、screenshots、trace integration |

### Ten replacement intents

1. **SLI/SLO — define the user-visible success contract.**
   - Correct principle: measure completed business transaction, latency/freshness/correctness and an explicit target/window; resource uptime is only supporting evidence.
   - Distractors: CPU below 50% is a payment SLO；Lambda invocation success proves fresh data；service SLA is the application SLI.
   - Task/source: `SAA-2.2, SAP-2.4` / `cw-slo, wa-observe`

2. **Telemetry roles — use metrics, logs and traces together.**
   - Correct principle: metrics show aggregate trend, logs provide detailed events and traces connect one request across dependencies; none alone proves every outcome.
   - Distractors: traces replace all metrics；logs automatically define SLOs；host metrics reveal every business error.
   - Task/source: `SAA-2.2, SAP-3.1` / `wa-observe, xray`

3. **Metric design — choose dimensions, statistic and period deliberately.**
   - Correct principle: emit a bounded-cardinality business metric, use suitable percentiles/rates, periods and missing-data behavior, then alarm on symptoms tied to user impact.
   - Distractors: use customer ID as an unlimited metric dimension；average hides no tail latency；one datapoint always proves an incident.
   - Task/source: `SAA-3.2, SAP-3.3` / `cw-alarms, wa-observe`

4. **Outside-in monitoring — detect failures before or beyond real traffic.**
   - Correct principle: synthetic canaries execute critical paths without user traffic, while real-user signals reveal actual device/region distributions; correlate both with backend telemetry.
   - Distractors: canaries replace load testing and RUM；RUM works with zero users；a health endpoint that always returns 200 proves checkout.
   - Task/source: `SAA-2.2, SAP-3.4` / `synthetics, cw-slo`

5. **Trace propagation — preserve causality across async boundaries.**
   - Correct principle: propagate correlation/trace identifiers through API, event and queue metadata, sample intentionally and annotate searchable business context without sensitive payloads.
   - Distractors: use timestamps alone as global identity；sample only failed requests after the fact；put credentials in trace annotations.
   - Task/source: `SAP-3.1, SAP-3.3` / `xray, wa-observe`

6. **Failure diagnosis — Lambda is successful but data is two hours stale.**
   - Correct principle: follow freshness SLI to event acceptance, queue/stream age, retries/DLQ, function duration/throttles and downstream commit; invocation success may only mean one step returned.
   - Distractors: increase Lambda memory before checking lag；inspect only error count；declare no incident because HTTP status is 200.
   - Task/source: `SAP-3.3, SAP-3.4` / `sqs-metrics, xray, wa-observe`

7. **Cost/operations — control telemetry volume and cardinality.**
   - Correct principle: set log retention, sampling, metric resolution and dimensions by diagnostic value; aggregate common paths and retain high-value audit/incident evidence.
   - Distractors: retain debug logs forever；emit one metric dimension per request ID；disable tracing completely to save cost.
   - Task/source: `SAP-1.5, SAP-2.6, SAP-3.1` / `wa-cost, wa-observe`

8. **SAA scenario — monitor a payment API.**
   - Correct principle: alarm on payment success/error/latency and dependency symptoms, run a safe synthetic transaction, and retain correlated logs/traces for failed requests.
   - Distractors: EC2 CPU dashboard only；CloudTrail management events only；DNS query count as payment correctness.
   - Task/source: `SAA-2.2, SAA-3.2` / `saa-d2, synthetics, cw-alarms`

9. **SAP operating model — cross-account observability and response.**
   - Correct principle: standardize telemetry schema, centralize searchable evidence with least privilege, define SLO owners and alarm/runbook actions, and test incident access during account/Region impairment.
   - Distractors: central account receives unrestricted write access to workloads；every team invents metric names；alarms have no named owner.
   - Task/source: `SAP-1.4, SAP-3.1, SAP-3.4` / `sap-d1, wa-ops, wa-observe`

10. **Multi-response — detect and explain a stale-data incident (choose two).**
    - Correct principle: choose both a freshness/business SLO with outside-in alarm and correlated queue/application/downstream metrics, logs and traces that identify the broken handoff.
    - Distractors: host CPU dashboard only；successful deployment event only；increase log retention without adding correlation.
    - Task/source: `SAP-3.1, SAP-3.4` / `cw-slo, sqs-metrics, xray`

---

## 第 114 章：RTO/RPO 決定 DR，而非服務名稱

### 現有題目缺陷

- Q1 的 end-to-end RTO/RPO decomposition 與「service SLA 不等於 DR」均正確，題幹不足以排除後者。
- Q2/Q4 固定選 AWS Backup，但 backup-only 不一定滿足秒/分鐘級目標；應先由 objectives 選 backup、pilot light、warm standby 或 active-active。
- Q3 把 backup plan 描述為 request/data path，分類錯誤；backup/restore多為 recovery/control workflow。
- Aurora Global Database 設定清單中的 `global write` 容易誤導為 multi-writer；Global Database一般仍需明確 global-writer/write-forwarding 與 failover semantics。
- Q5 未測 fencing、lag、headless secondary、secret/key/network parity、quota、restore validation 或 failback。

### Portable pattern → AWS services and configuration

| Portable pattern | AWS implementation | Configuration / evidence |
|---|---|---|
| RPO 決定資料保護頻率/lag | AWS Backup/PITR、service-native replication、Aurora Global Database | Schedule/continuous backup、copy、replication lag、RPO alarm |
| RTO 決定常駐 capacity 與 automation | Backup/restore、pilot light、warm standby、active-active | IaC、pre-created network/identity、desired capacity、quota、runbook |
| Recovery 是 end-to-end transaction | Route 53/ARC + application validation | Fencing、routing control、DNS/client behavior、business smoke test、failback |

### Ten replacement intents

1. **Objectives — distinguish RTO and RPO.**
   - Correct principle: RTO measures time to restore a working business service; RPO measures acceptable data loss in time and is constrained by backup interval or replication lag.
   - Distractors: RPO is repair duration；RTO is backup frequency；service uptime SLA directly sets both values.
   - Task/source: `SAA-2.2, SAP-2.2` / `dr-options`

2. **Strategy choice — map objectives to recovery pattern.**
   - Correct principle: choose backup/restore, pilot light, warm standby or multi-site according to RTO/RPO, cost, complexity and failure scope; lower objectives usually require more live capacity and automation.
   - Distractors: active-active is always simplest；backup-only guarantees seconds；an empty VPC is warm standby.
   - Task/source: `SAA-2.2, SAP-2.2, SAP-2.6` / `dr-options`

3. **Backup contract — configure recoverable points, not job success alone.**
   - Correct principle: align schedule/PITR, start/completion window, vault/KMS, lifecycle, cross-account/Region copy and resource assignment to data classification and RPO.
   - Distractors: longer retention lowers RTO automatically；copying a recovery point launches the application；Multi-AZ removes corruption recovery needs.
   - Task/source: `SAA-2.2, SAA-4.1` / `backup-plan`

4. **Aurora Global Database — distinguish switchover and failover.**
   - Correct principle: planned switchover synchronizes healthy clusters for zero-data-loss role change; unplanned failover can lose unreplicated writes and requires lag, fencing, endpoint and configuration-parity controls.
   - Distractors: asynchronous replication guarantees zero RPO；every secondary accepts local writes；Route 53 alone promotes the database.
   - Task/source: `SAP-2.2, SAP-2.4` / `aurora-global-dr`

5. **Traffic and dependency recovery — restore more than the database.**
   - Correct principle: pre-create network, identity, keys, secrets, quotas and application artifacts; fence old writers, activate capacity and use a resilient routing-control procedure before business validation.
   - Distractors: only lower DNS TTL；database promotion preserves every open connection；create IAM/KMS dependencies during the outage without testing.
   - Task/source: `SAP-1.3, SAP-2.2` / `dr-options, route53-health`

6. **Failure diagnosis — database promoted in seconds but RTO is two hours.**
   - Correct principle: measure detection, decision/approval, data readiness, dependency restoration, capacity scale, DNS/client cache, reconnect and business validation separately to find the dominant delay.
   - Distractors: improve database promotion again；count from DNS change rather than incident start；ignore manual approval time.
   - Task/source: `SAP-3.4` / `aurora-global-dr, dr-options, wa-observe`

7. **Cost/operations — choose the lowest-cost strategy that meets objectives.**
   - Correct principle: compare storage, replication, idle compute, cross-Region transfer, licenses, automation, testing and operational complexity; overbuilding DR is also an architecture defect.
   - Distractors: multi-site always has lowest TCO；backup storage is the only DR cost；never fund periodic game days.
   - Task/source: `SAP-2.6, SAP-3.5` / `dr-options, wa-cost`

8. **SAA scenario — four-hour RTO and one-day RPO.**
   - Correct principle: use suitably scheduled protected backups plus tested IaC restore/cutover that completes within four hours, avoiding unnecessary active-active capacity.
   - Distractors: synchronous cross-Region multi-writer；Route 53 record only；daily backup with no restore test.
   - Task/source: `SAA-2.2, SAA-4.1` / `saa-d2, backup-plan, backup-restore-test`

9. **SAP operating model — execute and fail back safely.**
   - Correct principle: define declaration authority, automated ordered runbook, communication, fencing, evidence, degraded-operation limits, old-Region reintegration and tested failback.
   - Distractors: both Regions resume writes independently；failback immediately when the console is green；keep runbooks without named owners.
   - Task/source: `SAP-1.3, SAP-2.2, SAP-3.4` / `sap-d1, aurora-global-dr, dr-options`

10. **Multi-response — prove recovery objectives (choose two).**
    - Correct principle: choose both periodic automated restore/failover timing against RTO/RPO and application-level integrity/business transaction validation before declaring recovery.
    - Distractors: backup job `COMPLETED` only；standby resources visible in console；architecture diagram marked Multi-Region.
    - Task/source: `SAP-2.2, SAP-2.4` / `backup-restore-test, dr-options`

---

## 第 115 章：Cost 是 Architecture Constraint

### 現有題目缺陷

- Q1 的 unit economics 與 total-cost principle 都正確且互補；把「人力、風險、遷移、機會成本」標成錯誤 alternative 造成明顯歧義。
- Q2/Q4 重複 Cost Explorer 欄位，且題幹稱其決定「安全、流量、容量或資料行為」，與 billing analysis 工具責任不符。
- Q3 把 Cost Explorer 放進 request/data path；它分析延遲更新的 billing dataset，不處理 workload request。
- Q4 選 Cost Explorer 不能實作 cost-optimized architecture，只能協助觀察；真正動作需 rightsizing、lifecycle、purchase model、data path 或 architecture change。
- 缺少 amortized/unblended cost、allocation/tag coverage、anomaly delay、CUR/Data Exports、Budgets、cross-AZ/NAT transfer、commitment utilization 與 cost-per-outcome。

### Portable pattern → AWS services and configuration

| Portable pattern | AWS implementation | Configuration / evidence |
|---|---|---|
| 以 unit economics 驗證 architecture | Cost Explorer + custom business denominator | Filter/group/date、amortized cost、transactions/tenants/GB、trend/forecast |
| 建立細粒度 allocation | CUR/Data Exports to S3/Athena/Redshift | Resource IDs、tags、hourly/daily grain、split costs、allocation rules |
| 將 insight 轉成 guardrail/action | Budgets、Compute Optimizer、service configuration | Forecast alerts/actions、rightsizing validation、storage lifecycle、purchase mix |

### Ten replacement intents

1. **Unit economics — divide cost by a business outcome.**
   - Correct principle: track cost per successful transaction, tenant, active user or processed GB and separate fixed from variable cost so growth efficiency is visible.
   - Distractors: total monthly bill alone shows efficiency；lower unit price guarantees lower unit cost；failed requests belong in no denominator.
   - Task/source: `SAA-4.1, SAA-4.2, SAA-4.3, SAP-1.5` / `wa-cost, cost-explorer`

2. **Allocation — make spend attributable before optimizing.**
   - Correct principle: use account boundaries, cost categories/tags and consistent ownership, and measure unallocated spend; tag activation is not retroactive proof of historical ownership.
   - Distractors: resource name is a guaranteed billing dimension；one shared account improves chargeback accuracy；all costs can be allocated from CPU metrics alone.
   - Task/source: `SAP-1.4, SAP-1.5` / `wa-cost, cur`

3. **Tool choice — Cost Explorer versus CUR/Data Exports.**
   - Correct principle: use Cost Explorer for interactive trends/forecast/coverage and CUR/Data Exports for detailed line-item analysis, custom allocation and BI pipelines.
   - Distractors: Cost Explorer is the real-time request meter；CUR automatically changes resources；Budgets replaces detailed billing data.
   - Task/source: `SAP-1.5, SAP-3.5` / `cost-explorer, cur`

4. **Rightsizing — validate recommendations against SLO and seasonality.**
   - Correct principle: use Compute Optimizer as evidence, then load-test and review memory, network, storage, licenses, peaks and failover headroom before changing capacity.
   - Distractors: automatically apply every cheapest recommendation；CPU alone represents all resources；stop every idle-looking standby.
   - Task/source: `SAA-4.2, SAP-2.6` / `compute-optimizer, wa-cost`

5. **Architecture cost drivers — optimize data path and retention.**
   - Correct principle: inspect cross-AZ/Region/NAT transfer, idle replicas, request frequency, storage class/lifecycle and unlimited telemetry/backup retention; commitments cannot repair inefficient flow.
   - Distractors: buy RI/Savings Plans before removing idle architecture；data transfer is never material；retain every object/log forever.
   - Task/source: `SAA-4.1, SAA-4.4, SAP-3.5` / `wa-cost, cur`

6. **Failure diagnosis — unexpected daily cost spike.**
   - Correct principle: compare actual/forecast and detailed line items by account/service/usage/resource/tag, correlate deployment/traffic anomalies, and distinguish delayed billing data from current resource state.
   - Distractors: terminate the largest instance immediately without evidence；assume Cost Explorer is second-by-second；inspect only list price.
   - Task/source: `SAP-1.5, SAP-3.5` / `cost-explorer, cur, budgets`

7. **Cost/operations — match purchase model to stable usage.**
   - Correct principle: cover measured stable baseline with appropriate commitments, use On-Demand for uncertain demand and interruption-tolerant Spot for flexible work; monitor utilization and coverage.
   - Distractors: purchase commitment for projected peak only；run critical singleton only on Spot；Savings Plans guarantee AZ capacity.
   - Task/source: `SAA-4.2, SAP-2.6` / `wa-cost, budgets`

8. **SAA scenario — choose the cost-effective valid architecture.**
   - Correct principle: satisfy security, resilience and performance first, then compare total recurring service/transfer/storage/operations cost instead of selecting the smallest headline price.
   - Distractors: always select serverless；always select Reserved Instances；remove Multi-AZ despite the availability requirement.
   - Task/source: `SAA-4.1, SAA-4.2, SAA-4.3, SAA-4.4` / `saa-d4, wa-cost`

9. **SAP operating model — build a FinOps feedback loop.**
   - Correct principle: assign owners and budgets, publish allocation/unit metrics, review anomalies and recommendations, approve tested changes and verify realized savings without SLO regression.
   - Distractors: finance owns cost without engineering input；recommendations auto-close after export；one annual review is sufficient.
   - Task/source: `SAP-1.5, SAP-3.1, SAP-3.5` / `sap-d1, sap-d3, wa-cost`

10. **Multi-response — reduce cost without hiding risk (choose two).**
    - Correct principle: choose both removal/rightsizing of measured waste with SLO validation and redesign of dominant transfer/retention/request drivers with post-change unit-cost evidence.
    - Distractors: buy more commitments before measuring baseline；delete recovery points below RPO；disable observability needed to prove success.
    - Task/source: `SAP-2.6, SAP-3.5` / `compute-optimizer, cur, wa-cost`

---

## 第 116 章：Migration 由 Business Value 與 Dependency Graph 驅動

### 現有題目缺陷

- Q1 的 outcome/dependency wave principle 與「早期 waves 應包含代表性 dependency」都可同時成立，卻把後者標成錯誤 alternative。
- Q2–Q4 仍以 Migration Hub 為新 migration 的 primary service。AWS Migration Hub 已於 2025-11-07 停止接受新客戶；既有客戶可完成現有專案，新專案官方建議 AWS Transform。
- Q3 把 portfolio tracking 工具稱為 request/data path；Migration Hub/Transform本身不是 server、database 或 file migration data mover。
- Q4 的 task mapping 寫成「SAA 基礎」而非專案中的有效 task key。
- 缺少 7 Rs、hard/soft dependency、move group/wave、MGN/DMS/DataSync 邊界、cutover/freeze/rollback、hypercare、decommission 和 realized business benefit。

### Portable pattern → AWS services and configuration

| Portable pattern | AWS implementation | Configuration / evidence |
|---|---|---|
| 以 outcome、portfolio、dependency 排 waves | AWS Transform + AWS Prescriptive Guidance | Discovery data、application grouping、move groups、7R recommendation、priority/risk/wave |
| 依 state/protocol 選 migration engine | MGN、DMS、DataSync | Replication settings/lag、source-target endpoints、CDC、verification、test/cutover |
| Migration 完成於 operating-model/business change | Landing zone/IaC/operations + decommission | SLO/cost/release metrics、owner/runbook、license/DC exit、rollback/hypercare evidence |

### Ten replacement intents

1. **Business case and 7 Rs — choose the migration outcome.**
   - Correct principle: classify retire, retain, rehost, relocate, repurchase, replatform or refactor from business drivers, risk, time and target operating model rather than assuming every server must move unchanged.
   - Distractors: rehost every workload first by default；retain means migration failure；refactor is always the fastest data-center exit.
   - Task/source: `SAP-4.1, SAP-4.2, SAP-4.4` / `migration-7rs, sap-d4`

2. **Discovery — build a trustworthy portfolio and dependency graph.**
   - Correct principle: combine inventory, process/network observations, owners, criticality, data, latency and business calendars; tooling data must be validated with application teams.
   - Distractors: one week of network flow reveals every batch dependency；CMDB is always complete；shared monitoring traffic makes all applications one dependency group.
   - Task/source: `SAP-4.1` / `migration-wave, transform-wave`

3. **Wave design — group hard dependencies and limit change risk.**
   - Correct principle: put co-dependent applications in move groups, prioritize waves by outcomes/risk/readiness, keep waves manageable and include design, cutover, rollback, hypercare and closure.
   - Distractors: group only by server count；split low-latency app/database hard dependencies；make the first wave the entire critical business domain.
   - Task/source: `SAP-4.1, SAP-4.2` / `migration-wave, transform-wave`

4. **Current service mapping — AWS Transform versus Migration Hub.**
   - Correct principle: use AWS Transform for new portfolio planning/grouping/waves; Migration Hub is limited to existing customers completing ongoing projects after the 2025 availability change.
   - Distractors: recommend Migration Hub to every new customer；treat AWS Transform as a block replication agent；assume existing Migration Hub projects were shut down immediately.
   - Task/source: `SAP-4.1, SAP-4.2` / `migrationhub-change, transform-wave`

5. **Migration engine choice — match tool to state and protocol.**
   - Correct principle: use MGN for server rehost/block replication, DMS for database migration/CDC and DataSync for file/object transfer; portfolio tooling coordinates but does not replace movers.
   - Distractors: use DMS as a general POSIX file copier；use DataSync to convert database schema；use MGN to refactor application code automatically.
   - Task/source: `SAA-2.1, SAP-4.2, SAP-4.3` / `mgn, dms, datasync`

6. **Failure diagnosis — cutover starts but application cannot go live.**
   - Correct principle: check replication/CDC lag, missing dependencies, DNS/network/identity/KMS, target capacity/configuration, data reconciliation, acceptance tests and rollback deadline before forcing traffic.
   - Distractors: server boot proves migration success；change DNS despite failed data validation；delete the source to prevent rollback ambiguity.
   - Task/source: `SAP-2.4, SAP-4.2` / `migration-wave, mgn, dms`

7. **Cost/operations — measure realized migration benefit.**
   - Correct principle: include migration factory/tooling, dual-run, transfer, licenses, retraining and modernization cost; after cutover verify unit cost, release speed, SLO and actual source/license decommission.
   - Distractors: EC2 running means the business case is achieved；ignore dual-run and egress；keep the data center indefinitely while claiming exit savings.
   - Task/source: `SAP-1.5, SAP-2.6, SAP-4.1` / `wa-cost, migration-wave`

8. **SAA scenario — simple rehost versus managed replatform.**
   - Correct principle: choose MGN when rapid low-change server rehost is the constraint; choose an appropriate managed target when operational reduction justifies tested application/database changes.
   - Distractors: use Migration Hub as the block replication tool；use DMS for the whole VM；refactor during a fixed short outage without testing.
   - Task/source: `SAA-2.1, SAA-4.2` / `saa-d2, saa-d4, mgn, rds-overview`

9. **SAP operating model — run waves with governance and learning.**
   - Correct principle: assign wave/application owners, landing-zone/security readiness, runbook rehearsals, change control, rollback authority, hypercare and post-wave metrics; feed lessons into later waves.
   - Distractors: migration team owns production forever；all waves overlap without resource limits；close a wave before operational handover.
   - Task/source: `SAP-1.4, SAP-3.1, SAP-4.2` / `migration-wave, sap-d1, sap-d4`

10. **Multi-response — complete a migration wave safely (choose two).**
    - Correct principle: choose both validated dependency-aware cutover/rollback with replication and business acceptance evidence and post-cutover operational handover/decommission metrics tied to the business case.
    - Distractors: successful target VM launch only；immediate source deletion before acceptance；leave licenses and source capacity running without an owner.
    - Task/source: `SAP-4.2, SAP-4.4` / `migration-wave, transform-wave`

---

## Official public AWS sample/practice resource mapping

This section maps official public resources to audit use. It intentionally does not copy their questions, answers or distractors.

| Official resource | Audit use | What it must not be used to infer | Source key |
|---|---|---|---|
| SAA-C03 Exam Guide and domain pages | Validate task wording, scope, multiple-choice/multiple-response rules and domain alignment for intents 105–115; use product docs for factual behavior. | It is not a complete product specification or a promise that a particular service/configuration will appear. | `saa-guide, saa-d1, saa-d2, saa-d3, saa-d4` |
| SAP-C02 Exam Guide and domain pages | Validate organizational complexity, new solution, continuous improvement, migration/modernization and multi-response depth. | It is not an exam dump, fixed question bank or substitute for current service documentation. | `sap-guide, sap-d1, sap-d2, sap-d3, sap-d4` |
| AWS Certification Official Practice Question Set for SAA | Calibrate scenario length, hard-constraint reading and plausibility of three distractors before publishing original items. | Do not copy, paraphrase, enumerate or use the set to estimate exact live-exam topic frequency. | `cert-saa` |
| AWS Certification Official Practice Exam for SAA | Run timed readiness checks, classify misses by task/pattern and return to the official product source for each factual gap. | A score does not prove every chapter intent is covered, and the questions must not be reproduced in this repository. | `cert-saa` |
| AWS Skill Builder SAA Exam Prep Plan, Builder Labs, Cloud Quest and SimuLearn links | Map configuration and failure-diagnosis intents to hands-on or guided practice, especially queues, HA, security, observability and cost. | Completion badges do not replace restore, failover, load or permission evidence for the book's scenarios. | `cert-saa` |
| AWS Certification Official Practice Question Set for SAP-C02 | Calibrate long-form constraint conflicts, organization/migration context and all-or-nothing multi-response reasoning. | Do not copy or transform questions into chapter exercises, and do not use third-party recollections as supplements. | `cert-sap` |
| AWS Certification Official Practice Exam for SAP-C02 | Assess portfolio-level trade-off reasoning and identify weak SAP tasks before the announced retirement date. | It does not validate future SAP-C03 coverage; a separate delta audit is required after official C03 resources are released. | `cert-sap` |
| AWS Skill Builder SAP Exam Prep Plan, Builder Labs and SimuLearn links | Practice operating-model, failure-recovery, cost and migration decisions with official guided resources. | Labs are examples, not universal reference architectures; validate final principles against the source registry above. | `cert-sap` |
| SAP version notice | Keep this audit on SAP-C02 as of 2026-10-01 while flagging the future C03 registration and C02 retirement dates for follow-up. | Do not map unreleased C03 task statements by assumption. | `cert-sap` |

## Validation checklist

- Audited chapters: 105–116.
- Exactly ten intents per chapter: yes.
- Correct principle and exactly three distractor concepts per intent: yes.
- Failure diagnosis, cost/operations and multi-response coverage per chapter: yes.
- Portable pattern mapped to AWS service and configuration per chapter: yes.
- Official SAA-C03/SAP-C02 task and source keys: yes.
- Official public sample/practice resources mapped separately: yes.
- Exam dumps or copied official questions used: no.
- Other files intentionally edited: no.

SUPERSET_WORKER_DONE task P11-audit
