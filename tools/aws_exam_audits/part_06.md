---
title: P06 Audit — AWS Chapters 61–71
tags:
  - aws
  - certification
  - exam-audit
task: P06-audit
audit_date: 2026-10-01
---

# Part 06 Audit — Chapters 61–71: Reliability, Performance, Observability, and Cost

Scope: audit only. This note identifies defects in the current five-question chapter sets and specifies exactly ten original replacement **knowledge coverage intents per chapter**. It does not reproduce live exam items, copy full official sample questions, or use exam dumps.

The project currently maps SAP work to SAP-C02. AWS has announced that SAP-C03 registration opens on 2026-10-27 and that SAP-C02 retires after 2026-11-17. The mappings below therefore remain explicitly SAP-C02 and must be revalidated before generating a SAP-C03 bank.

## Audit-wide findings

- Every chapter has only five questions and reuses the same selection, settings, mechanism, generic SAA, and generic SAP-governance template.
- Questions 1 and 4 usually duplicate the same conclusion. Question 5 repeats multi-account owner, canary, rollback, AdministratorAccess, and empty-standby boilerplate rather than testing chapter-specific SAP judgment.
- Many correct choices are chapter summaries rather than executable architectures. The longest and most comprehensive option is visibly favored.
- Distractors such as “deploy everything,” “managed services understand business requirements,” and “wait for failure and fix it manually” are not plausible.
- Concept chapters are incorrectly forced through the first listed product. Service Quotas, Compute Optimizer, AWS Backup, and Savings Plans are even described as if they were application request/data-path components.
- The replacement bank must contain 110 intents total: exactly 10 for each of Chapters 61–71.

## Official source key

### Exam blueprints and legal calibration resources

- `EX-SAA2` — [SAA-C03 Domain 2: Design Resilient Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain2.html)
- `EX-SAA3` — [SAA-C03 Domain 3: Design High-Performing Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain3.html)
- `EX-SAA4` — [SAA-C03 Domain 4: Design Cost-Optimized Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain4.html)
- `EX-SAP1` — [SAP-C02 Domain 1: Design for Organizational Complexity](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain1.html)
- `EX-SAP2` — [SAP-C02 Domain 2: Design for New Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain2.html)
- `EX-SAP3` — [SAP-C02 Domain 3: Continuous Improvement](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)
- `SAA-SAMPLE` — [Official SAA-C03 public sample questions PDF](https://d1.awsstatic.com/training-and-certification/docs-sa-assoc/AWS-Certified-Solutions-Architect-Associate_Sample-Questions.pdf)
- `SAP-SAMPLE` — [Official SAP-C02 public sample questions PDF](https://d1.awsstatic.com/training-and-certification/docs-sa-pro/AWS-Certified-Solutions-Architect-Professional_Sample-Questions.pdf)
- `SAA-PREP` — [AWS Certified Solutions Architect – Associate preparation page](https://aws.amazon.com/certification/certified-solutions-architect-associate/) — links the AWS Certification Official Practice Question Set and Official Practice Exam.
- `SAP-PREP` — [AWS Certified Solutions Architect – Professional preparation page](https://aws.amazon.com/certification/certified-solutions-architect-professional/) — links the AWS Certification Official Practice Question Set and Official Practice Exam.

Official PDFs may be referenced by question number and topic for calibration, but their full prompts and choices must not be copied into this repository. Skill Builder question sets and practice exams may be used by an authorized learner under AWS terms; they must not be scraped, redistributed, or reconstructed here.

### Reliability and disaster recovery

- `GI-AZ` — [AWS Regions and Availability Zones](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions-availability-zones.html)
- `FAULT-AZ` — [AWS Fault Isolation Boundaries: Availability Zones](https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/availability-zones.html)
- `WA-RTO-RPO` — [REL13-BP01 Define recovery objectives for downtime and data loss](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_objective_defined_recovery.html)
- `WA-DR` — [REL13-BP02 Use defined recovery strategies](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_disaster_recovery.html)
- `DR-OPTIONS` — [Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)
- `R53-FAILOVER` — [Route 53 health checks and DNS failover](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover.html)
- `ARC-RC` — [Amazon Application Recovery Controller routing control](https://docs.aws.amazon.com/r53recovery/latest/dg/routing-control.html)
- `ARC-DATAPLANE` — [ARC routing-control data and control planes](https://docs.aws.amazon.com/r53recovery/latest/dg/data-and-control-planes.html)
- `RDS-MULTIAZ` — [Amazon RDS Multi-AZ deployments](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html)
- `BACKUP-RESTORE` — [AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)
- `BACKUP-AIRGAP` — [AWS Backup logically air-gapped vault](https://docs.aws.amazon.com/aws-backup/latest/devguide/logicallyairgappedvault.html)
- `DRS-FAILBACK` — [AWS Elastic Disaster Recovery recovery and failback](https://docs.aws.amazon.com/drs/latest/userguide/failback.html)
- `RES-HUB-POLICY` — [AWS Resilience Hub resiliency policies](https://docs.aws.amazon.com/resilience-hub/latest/userguide/create-policy.html)
- `FIS-INTRO` — [AWS Fault Injection Service concepts and safeguards](https://docs.aws.amazon.com/fis/latest/userguide/what-is.html)

### Performance, scaling, quotas, and observability

- `CACHE-STRATEGIES` — [ElastiCache caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Strategies.html)
- `RDS-READ` — [Amazon RDS read replicas](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html)
- `ASG-TARGET` — [EC2 Auto Scaling target tracking](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html)
- `ASG-WARMUP` — [EC2 Auto Scaling default instance warmup](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-default-instance-warmup.html)
- `ASG-SCHEDULED` — [EC2 Auto Scaling scheduled scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/schedule_time.html)
- `SQS-METRICS` — [Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)
- `SQ-INTRO` — [AWS Service Quotas concepts](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html)
- `SQ-AUTO` — [Service Quotas Automatic Management](https://docs.aws.amazon.com/servicequotas/latest/userguide/automatic-management.html)
- `LAMBDA-CONC` — [Lambda reserved concurrency](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)
- `SDK-RETRY` — [AWS SDK retry behavior](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html)
- `WA-GRACE` — [REL05-BP01 Implement graceful degradation](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_graceful_degradation.html)
- `CW-CONCEPTS` — [CloudWatch metrics concepts and retention](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html)
- `CW-ALARM` — [Using CloudWatch alarms, M/N, and missing data](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- `CW-COMPOSITE` — [CloudWatch composite alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarm-combining.html)
- `CW-SLO` — [CloudWatch Application Signals service level objectives](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html)
- `CW-EMF` — [CloudWatch embedded metric format and cardinality cost](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html)
- `CWL-CONCEPTS` — [CloudWatch Logs groups, streams, and retention](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html)
- `CW-XACCT` — [CloudWatch cross-account observability](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html)
- `CLOUDTRAIL` — [AWS CloudTrail User Guide](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html)
- `CONFIG` — [What is AWS Config?](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)
- `XRAY-CONCEPTS` — [AWS X-Ray concepts](https://docs.aws.amazon.com/xray/latest/devguide/xray-concepts.html)
- `XRAY-TIMELINE` — [X-Ray SDK and daemon support timeline](https://docs.aws.amazon.com/xray/latest/devguide/xray-sdk-daemon-timeline.html)
- `CW-OTEL` — [OpenTelemetry in Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OpenTelemetry-Sections.html)
- `ADOT-XRAY` — [ADOT Collector X-Ray exporter](https://aws-otel.github.io/docs/getting-started/x-ray)

### Cost, commitments, storage, and network

- `SP-INTRO` — [What are Savings Plans?](https://docs.aws.amazon.com/savingsplans/latest/userguide/)
- `SP-APPLY` — [How Savings Plans apply to usage](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-applying.html)
- `SP-PURCHASE` — [Savings Plans purchase analysis](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-purchase-analysis.html)
- `EC2-RI` — [How EC2 Reserved Instance discounts apply](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/apply_ri.html)
- `EC2-CR` — [EC2 On-Demand Capacity Reservations](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-capacity-reservations.html)
- `SPOT-INTERRUPT` — [Prepare for Spot Instance interruptions](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/prepare-for-interruptions.html)
- `SPOT-REBALANCE` — [EC2 Spot rebalance recommendations](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/rebalance-recommendations.html)
- `CO-INTRO` — [What is AWS Compute Optimizer?](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is.html/)
- `CO-EIM` — [Compute Optimizer enhanced infrastructure metrics](https://docs.aws.amazon.com/compute-optimizer/latest/ug/enhanced-infrastructure-metrics.html)
- `CO-MEM` — [EC2 metrics analyzed by Compute Optimizer](https://docs.aws.amazon.com/compute-optimizer/latest/ug/ec2-metrics-analyzed.html)
- `CO-EXT` — [Compute Optimizer external metrics ingestion](https://docs.aws.amazon.com/compute-optimizer/latest/ug/external-metrics-ingestion)
- `COST-HUB` — [AWS Cost Optimization Hub](https://docs.aws.amazon.com/cost-management/latest/userguide/cost-optimization-hub.html)
- `EC2-CREDITS` — [Monitor CPU credits for burstable instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances-monitoring-cpu-credits.html)
- `S3-LIFECYCLE` — [S3 Lifecycle transition considerations](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html)
- `S3-IT` — [S3 Intelligent-Tiering](https://docs.aws.amazon.com/AmazonS3/latest/userguide/intelligent-tiering.html)
- `ATHENA-COLUMNAR` — [Use columnar storage formats with Athena](https://docs.aws.amazon.com/athena/latest/ug/columnar-storage.html)
- `DDB-CAPACITY` — [Evaluate a DynamoDB table capacity mode](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/CostOptimization_TableCapacityMode.html)
- `DDB-ONDEMAND` — [DynamoDB on-demand capacity mode](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/on-demand-capacity-mode.html)
- `DDB-PARTITIONS` — [DynamoDB partition key design](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html)
- `EBS-TYPES` — [Amazon EBS volume types](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)
- `RDS-BACKUP-COST` — [RDS backup retention and storage cost](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.Retaining.html)
- `NAT-OVERVIEW` — [NAT gateway connectivity types](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway)
- `NAT-COST` — [NAT gateway cost guidance](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html)
- `NAT-METRICS` — [Monitor NAT gateways with CloudWatch](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway-cloudwatch.html)
- `NAT-REGIONAL` — [Regional NAT gateways](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateways-regional.html)
- `S3-GWEP` — [Gateway endpoints for Amazon S3](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-endpoints-s3.html)
- `VPC-PRICING` — [Amazon VPC pricing](https://aws.amazon.com/vpc/pricing/)
- `CF-CACHE` — [CloudFront caching behavior](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/ConfiguringCaching.html)
- `VPC-FLOW` — [VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)

---

## Chapter 61 — Multi-AZ, Multi-Region, and Fault Domains

### Existing defects

- **Duplicate:** Questions 1 and 4 both reward the same “Multi-AZ first, then consider Multi-Region” summary; neither tests a concrete workload dependency.
- **Ambiguous:** Question 5 rejects the true Multi-Region trade-off statement even though it is directly relevant to the requested production migration and can coexist with both marked answers.
- **Low-density:** The settings question lists subnet placement, Auto Scaling distribution, Multi-AZ, cross-zone load balancing, and cost as one bundle, so it cannot reveal which setting changes which failure boundary.
- **Factually unsafe:** “Availability Zone = data-center-level failure domain” is too narrow. An AZ consists of one or more discrete data centers.
- **Factually unsafe:** “Every Region has an independent service control plane” is an unsafe universal claim; scope and dependencies vary by service.
- Route 53 is treated as a generic wrong answer. The set does not test health criteria, resolver caching, false-positive failover, recovery capacity, or data consistency.
- A design can be spread across AZs yet still fail from a shared database, NAT path, identity dependency, quota, deployment, or operator action. No current item tests this.
- Game-day evidence is mentioned only as boilerplate and never asks what must be measured during AZ evacuation, Region evacuation, or failback.

### Ten replacement intents

1. **Intent — Match the failure scope to the isolation boundary.**
   - Correct principle: use multiple AZs to tolerate an AZ-scoped failure and multiple Regions only when the requirement includes Regional loss, sovereignty, or global-service objectives; an AZ is one or more discrete data centers.
   - Three plausible distractors: treat three instances in one AZ as three failure domains; use two subnets in one AZ; assume a second Region is automatically required for every production workload.
   - Mapping: `SAA | SAA-2.2 | GI-AZ, FAULT-AZ, EX-SAA2`

2. **Intent — Audit whether a “Multi-AZ” application is Multi-AZ end to end.**
   - Correct principle: verify compute, load balancing, state, egress, secrets, queues, and operational dependencies across independent AZ paths; the weakest shared dependency limits availability.
   - Three plausible distractors: inspect only the Auto Scaling group subnets; count instances rather than dependencies; accept a Multi-AZ label on the database as proof for the entire workload.
   - Mapping: `SAP | SAP-1.3 | FAULT-AZ, EX-SAP1`

3. **Intent — Distinguish RDS Multi-AZ from read scaling.**
   - Correct principle: choose RDS Multi-AZ for managed availability/failover; use read replicas for read scaling and accept their replication and promotion semantics. Do not direct normal reads to a Multi-AZ standby unless the specific deployment type supports readable standbys.
   - Three plausible distractors: write to both primary and standby; use a read replica as synchronous zero-RPO HA; assume every Multi-AZ topology exposes a reader endpoint.
   - Mapping: `SAA | SAA-2.2 | RDS-MULTIAZ, RDS-READ`

4. **Intent — Preserve service during an AZ loss at the stateless tier.**
   - Correct principle: place healthy targets and capacity in multiple AZs behind a load balancer, configure health checks and Auto Scaling replacement, and verify the remaining AZ capacity can carry the SLO load.
   - Three plausible distractors: keep standby instances stopped in the same AZ; rely on cross-zone load balancing without targets in another AZ; increase instance size without changing placement.
   - Mapping: `SAA | SAA-2.2 | EX-SAA2, SAA-SAMPLE`

5. **Intent — Decide when Multi-Region is justified.**
   - Correct principle: require an explicit Regional failure, residency, or global-latency objective and price the additional data consistency, deployment, security, observability, and operational burden.
   - Three plausible distractors: select Multi-Region because it is always more available; equate backups in another Region with an active application; ignore cross-Region data semantics.
   - Mapping: `SAP | SAP-2.2 | DR-OPTIONS, WA-DR`

6. **Intent — Find hidden shared dependencies in a two-Region design.**
   - Correct principle: inspect identity, DNS, certificates, CI/CD, artifact stores, KMS keys, secrets, quotas, third parties, and operator access; a shared single-Region or single-account dependency can defeat the claim.
   - Three plausible distractors: count only application stacks; assume global service branding means no dependency risk; use one deployment pipeline with artifacts available only in the failed Region.
   - Mapping: `SAP | SAP-1.3 | DR-OPTIONS, EX-SAP1`

7. **Intent — Reason about DNS failover safely.**
   - Correct principle: Route 53 health checks affect future DNS answers; failover still depends on correct health criteria, record policy, TTL and resolver caching, healthy recovery capacity, and consistent data.
   - Three plausible distractors: treat Route 53 as a traffic proxy; promise instantaneous cutover to every client; assume DNS health automatically promotes databases and synchronizes writes.
   - Mapping: `SAA → SAP | SAA-2.2 / SAP-2.4 | R53-FAILOVER`

8. **Intent — Prefer a recovery data-plane control for deliberate Regional evacuation.**
   - Correct principle: pre-provision ARC routing controls and use its highly available data-plane API for a guarded traffic switch; avoid inventing control-plane resources during the incident.
   - Three plausible distractors: edit Route 53 record weights manually during the outage; create the recovery stack after declaring disaster; use an application health endpoint as the only authorization to fail over.
   - Mapping: `SAP | SAP-2.4 | ARC-RC, ARC-DATAPLANE`

9. **Intent — Validate surviving capacity and quotas before declaring fault tolerance.**
   - Correct principle: size steady-state or recovery capacity so the remaining AZ/Region can meet critical SLOs, and pre-check service quotas, IP space, connection limits, and downstream headroom.
   - Three plausible distractors: assume Auto Scaling guarantees capacity; request quotas only after failover; test at average rather than evacuation load.
   - Mapping: `SAP | SAP-3.4 | WA-DR, SQ-INTRO`

10. **Intent — Run an AZ/Region game day and produce evidence.**
    - Correct principle: define hypothesis and stop conditions, inject or simulate the failure safely, measure detection, traffic evacuation, error budget, data correctness, recovery time, and failback, then retain timestamps and corrective actions.
    - Three plausible distractors: stop one idle instance and call it an AZ test; record only that infrastructure deployment succeeded; omit failback and data reconciliation.
    - Mapping: `SAP | SAP-3.4 | FIS-INTRO, WA-DR`

### Official calibration resources

- **Direct public mapping:** `SAA-SAMPLE` Question 8 calibrates a concrete multi-AZ web and database high-availability decision.
- **Direct public mapping:** `SAP-SAMPLE` Question 9 calibrates a two-Region active-active design with routing, artifacts, and a global database.
- `SAA-PREP` and `SAP-PREP` are appropriate for additional official scenario style and multi-response calibration.
- No official public sample directly tests shared dependency analysis, ARC routing controls, surviving-capacity evidence, or an AZ/Region game day.

---

## Chapter 62 — Backup, Pilot Light, Warm Standby, and Active-Active

### Existing defects

- **Ambiguous:** Question 1 gives four outage tolerances but no RPO, workload shape, dependency graph, consistency model, or budget, then maps them to four DR strategies as if time alone determines the answer.
- **Duplicate:** Questions 1, 4, and 5 repeat the same four-strategy ranking rather than testing implementation differences.
- **Low-density:** The settings and mechanism questions test AWS Backup configuration, not the chapter’s distinctions among backup/restore, pilot light, warm standby, hot standby, and multi-site active-active.
- **Factually unsafe:** The explanation implies the strategy statement follows from AWS Backup. AWS Backup is one implementation component; it does not select or implement the complete DR architecture.
- **Factually unsafe:** Cross-account or cross-Region copy support is not a universal property of every protected resource and configuration.
- The chapter omits point-in-time protection from logical corruption, write-conflict handling, control-plane dependency, capacity readiness, and the difference between replication and backup.
- AWS Elastic Disaster Recovery is presented only as a neighboring service. No item tests its server/block-level scope or why it does not replace managed-service-native recovery.
- Failover, failback, identity, DNS, infrastructure as code, quotas, and recovery evidence are absent from the scored knowledge.

### Ten replacement intents

1. **Intent — Select a DR strategy from RTO, RPO, cost, and operational capability.**
   - Correct principle: choose the least complex strategy that demonstrably meets objectives; backup/restore, pilot light, warm standby, and active-active generally trade increasing cost and complexity for lower recovery objectives.
   - Three plausible distractors: choose active-active for every tier; select only by RTO and ignore RPO; infer the strategy from a single AWS service name.
   - Mapping: `SAA → SAP | SAA-2.2 / SAP-2.2 | WA-DR, DR-OPTIONS`

2. **Intent — Design a complete backup-and-restore recovery path.**
   - Correct principle: protect data, code, configuration, and infrastructure definitions; copy recovery points to the required boundary; restore data and redeploy the stack in dependency order within the measured RTO.
   - Three plausible distractors: back up only the database; expect AWS Backup to restore the entire application automatically; keep IaC only in the primary Region.
   - Mapping: `SAA | SAA-2.2 | DR-OPTIONS, BACKUP-RESTORE`

3. **Intent — Identify a true pilot-light design.**
   - Correct principle: keep data replication and core recovery infrastructure ready while non-core compute is absent or switched off and must be deployed or started before traffic can be served.
   - Three plausible distractors: call an always-serving reduced stack pilot light; retain only offline backups; keep full-capacity compute running but route no traffic.
   - Mapping: `SAA | SAA-2.2 | DR-OPTIONS, WA-DR`

4. **Intent — Identify a true warm-standby design.**
   - Correct principle: maintain a scaled-down but fully functional stack that can serve traffic immediately at reduced capacity, then scale it for production load.
   - Three plausible distractors: require deployment of missing application tiers before any request can succeed; store only backups; label an untested full-capacity stack warm standby.
   - Mapping: `SAA | SAA-2.2 | WA-DR`

5. **Intent — Evaluate multi-site active-active data semantics.**
   - Correct principle: active-active serves traffic from multiple Regions and must define write-global, write-local with conflict resolution, or write-partitioned ownership; point-in-time backup remains necessary for corruption.
   - Three plausible distractors: assume asynchronous replication creates one global ACID database; use last-writer-wins without checking business invariants; omit backup because both Regions are active.
   - Mapping: `SAP | SAP-2.4 | DR-OPTIONS, SAP-SAMPLE`

6. **Intent — Decide when AWS Elastic Disaster Recovery fits.**
   - Correct principle: use DRS for server-hosted applications and databases that can be recovered through continuous block-level replication and launched recovery instances; it does not replace native RDS, DynamoDB, S3, or SaaS recovery design.
   - Three plausible distractors: install DRS on an RDS instance; treat DRS as an application-consistent transaction log for every database; use it to replicate serverless control-plane configuration.
   - Mapping: `SAP | SAP-2.2 | DR-OPTIONS, DRS-FAILBACK`

7. **Intent — Combine replication with point-in-time recovery.**
   - Correct principle: replication improves availability and RPO for infrastructure loss but can propagate corruption or malicious changes; preserve independent versioned or point-in-time recovery points.
   - Three plausible distractors: call a read replica an immutable backup; replicate delete/corruption and claim zero data-loss risk; keep backups only in the same compromised account.
   - Mapping: `SAA → SAP | SAA-2.2 / SAP-2.2 | DR-OPTIONS, BACKUP-AIRGAP`

8. **Intent — Isolate backups from workload compromise.**
   - Correct principle: use least privilege, cross-account copies where supported, vault access controls, Vault Lock or a logically air-gapped vault, and tested restore access from the recovery authority.
   - Three plausible distractors: give workload administrators permanent delete access to every vault; use replication alone; encrypt backups with a key that the compromised workload can schedule for deletion.
   - Mapping: `SAP | SAP-2.3 | BACKUP-AIRGAP`

9. **Intent — Design failover and failback as one lifecycle.**
   - Correct principle: automate pre-approved traffic switching, promotion, scaling, and validation; before failback, resynchronize writes from the recovery site and verify consistency and client routing.
   - Three plausible distractors: redirect users before data promotion; fail back by restoring the pre-incident primary over newer recovery data; leave DNS, certificates, and secrets out of the runbook.
   - Mapping: `SAP | SAP-2.2 | WA-DR, DRS-FAILBACK, ARC-RC`

10. **Intent — Prove DR readiness with recurring recovery tests.**
    - Correct principle: execute restore or failover drills, validate business transactions and data, measure achieved RTO/RPO, verify recovery quotas and capacity, record evidence, and remediate drift.
    - Three plausible distractors: accept a successful backup job as proof; test only the database restore; run a tabletop discussion without executing critical recovery steps.
    - Mapping: `SAP | SAP-3.4 | BACKUP-RESTORE, RES-HUB-POLICY, FIS-INTRO`

### Official calibration resources

- **Partial public mapping:** `SAP-SAMPLE` Question 9 calibrates implementation of an active-active two-Region application, but it does not compare the four DR strategies.
- `SAA-PREP` and `SAP-PREP` are the official resources for broader DR scenario and multi-response calibration.
- **No official public sample question maps directly** to backup/restore versus pilot light versus warm standby selection, DRS scope, isolated backup vaults, or failback.

---

## Chapter 63 — RTO/RPO-Driven Disaster Recovery Design

### Existing defects

- **Duplicate:** Chapters 62 and 63 reuse the same AWS Backup, DRS, Route 53, and generic governance structure; Chapter 63 does not earn a separate knowledge boundary.
- **Ambiguous:** In Question 1, the marked critical-path statement and the rejected “backup frequency affects RPO while automation/capacity affects RTO” statement are both correct and complementary.
- **Low-density:** Questions 2–4 again reduce business recovery objectives to AWS Backup fields and mechanism.
- **Factually unsafe:** Backup schedule frequency alone does not equal achieved RPO; start windows, completion, replication lag, consistency, and the last usable recovery point matter.
- **Factually unsafe:** AWS Resilience Hub estimates whether configuration meets a policy. It does not itself make the workload compliant or prove an executed recovery.
- The set does not distinguish objective from average: RTO is a maximum acceptable restoration delay for an event, not MTTR.
- No question calculates the full recovery critical path or treats RPO as a graph across databases, objects, queues/streams, configuration, and secrets.
- There is no scored evidence requirement for successful restore, business validation, data reconciliation, failover, or failback.

### Ten replacement intents

1. **Intent — Define RTO and RPO without conflating them with availability or MTTR.**
   - Correct principle: RTO is the maximum acceptable delay from interruption to service restoration; RPO is the maximum acceptable age of recoverable data. They are business targets for each workload, not averages or product guarantees.
   - Three plausible distractors: define RPO as repair duration; define RTO as annual uptime percentage; use MTTR as an exact substitute for a per-event objective.
   - Mapping: `SAA | SAA-2.2 | WA-RTO-RPO, EX-SAA2`

2. **Intent — Derive recovery objectives from business impact.**
   - Correct principle: classify workflows by downtime and data-loss impact, legal obligations, dependencies, and cost; assign measurable, achievable objectives instead of arbitrary zero values.
   - Three plausible distractors: give every application zero RTO/RPO; copy the database vendor SLA; set targets solely from the current backup schedule.
   - Mapping: `SAP | SAP-2.2 | WA-RTO-RPO, EX-SAP2`

3. **Intent — Build the end-to-end RTO critical path.**
   - Correct principle: include detection, declaration, operator or automation delay, infrastructure readiness, restore/promotion, dependency startup, traffic change, cache/client convergence, and business validation; parallelize only independent steps.
   - Three plausible distractors: measure only database restore time; exclude DNS and client reconnection; add every step arithmetically even when steps run safely in parallel.
   - Mapping: `SAP | SAP-2.2 | WA-DR, DR-OPTIONS`

4. **Intent — Build an RPO data graph for a transaction.**
   - Correct principle: identify every authoritative and derived state needed for a consistent recovery point—database rows, objects, stream offsets/events, workflow state, configuration, and secrets—and reconcile mismatched recovery points.
   - Three plausible distractors: use the database RPO for the whole system; ignore an event stream because it is not a database; restore objects and rows from unrelated timestamps without reconciliation.
   - Mapping: `SAP | SAP-2.4 | WA-RTO-RPO, DR-OPTIONS`

5. **Intent — Translate backup policy into an achievable RPO.**
   - Correct principle: verify the last completed, replicated, decryptable, and restorable recovery point plus job windows and consistency; a nominal hourly schedule does not automatically prove a one-hour RPO.
   - Three plausible distractors: count a started backup as recoverable; ignore copy lag to the recovery account; assume every resource in a plan shares one atomic timestamp.
   - Mapping: `SAA → SAP | SAA-2.2 / SAP-3.4 | BACKUP-RESTORE, DR-OPTIONS`

6. **Intent — Use replication lag as an RPO signal, not a guarantee.**
   - Correct principle: alarm on service-specific lag and stalled replication, understand asynchronous consistency, and retain point-in-time recovery for corruption; test promotion and post-promotion correctness.
   - Three plausible distractors: equate low current lag with guaranteed zero RPO; promote any replica without checking write ownership; replace backup with replication.
   - Mapping: `SAA → SAP | SAA-2.2 / SAP-3.4 | RDS-READ, DR-OPTIONS`

7. **Intent — Sequence dependency recovery to meet the objective.**
   - Correct principle: recover identity, network, keys/secrets, data stores, messaging, compute, and ingress according to real dependencies; pre-stage or parallelize bottlenecks and verify quotas.
   - Three plausible distractors: restore public ingress first; start consumers before their state and idempotency controls exist; assume resource creation success means the application is ready.
   - Mapping: `SAP | SAP-2.2 | WA-DR`

8. **Intent — Interpret a Resilience Hub assessment correctly.**
   - Correct principle: a policy records target RTO/RPO and an assessment estimates configuration posture; use its recommendations and tests, but require executed recovery evidence before claiming the objective is met.
   - Three plausible distractors: treat “policy met” as a contractual guarantee; expect the policy to change application resources automatically; enter zero objectives and accept “near zero” estimates as compliance.
   - Mapping: `SAP | SAP-3.4 | RES-HUB-POLICY`

9. **Intent — Validate a restored workload, not just restored resources.**
   - Correct principle: time the restore, run representative business transactions, verify data completeness and reconciliation, check security and observability, and retain job IDs, timestamps, outputs, and owner sign-off.
   - Three plausible distractors: stop at `COMPLETED` restore status; validate only that instances are running; delete test evidence after cleanup.
   - Mapping: `SAP | SAP-3.1 | BACKUP-RESTORE`

10. **Intent — Conduct a measured DR game day against RTO/RPO.**
    - Correct principle: define the disaster, expected recovery point, clock start/stop, safety controls, traffic and data validation, failback, and acceptance thresholds; use results to revise architecture and runbooks.
    - Three plausible distractors: pause the clock during manual troubleshooting; test only a happy-path promotion; declare success from a tabletop estimate.
    - Mapping: `SAP | SAP-3.4 | FIS-INTRO, WA-RTO-RPO, WA-DR`

### Official calibration resources

- `SAA-PREP` and `SAP-PREP` can legally calibrate official scenario wording, task depth, and multi-response style.
- `SAP-SAMPLE` Question 9 can calibrate the implementation complexity around a low-RTO multi-Region design, but it does not directly test RTO/RPO calculation.
- **No official public sample question maps directly** to RTO critical-path calculation, data-graph RPO, Resilience Hub interpretation, or measured DR-game-day evidence.

---

## Chapter 64 — Cache, Replica, Queue, and Horizontal Scaling

### Existing defects

- **Ambiguous:** The scenario says repeated database reads dominate latency, but the answer combines cache, replicas, queues, and horizontal scaling. Cache and read replica can both be valid without freshness, query, hit-rate, and operational constraints.
- **Duplicate:** Questions 1 and 4 both choose ElastiCache; Questions 2 and 3 merely enumerate its settings and a generic cache path.
- **Low-density:** One settings choice combines engine, serverless/node, cluster mode, replicas, Multi-AZ, TTL, eviction, networking, and encryption.
- **Factually unsafe:** Cache-aside and write-through are application patterns, not behavior ElastiCache automatically implements.
- **Factually unsafe:** Sharding, replicas, Multi-AZ, persistence, and failover semantics differ by Valkey/Redis OSS, Memcached, node-based, and serverless configurations.
- The read-replica description is too universal; endpoint, promotion, lag, cross-Region, and readable-standby behavior depend on engine and topology.
- Queueing is treated as a wrong service name rather than a burst absorber with backlog-age and idempotency consequences.
- No current item tests statelessness, scaling metrics, instance warmup, load-test evidence, tail latency, or the fact that queues do not create downstream capacity.

### Ten replacement intents

1. **Intent — Select cache, read replica, queue, or horizontal scaling from the bottleneck.**
   - Correct principle: cache repeated computations/reads, use read replicas for database read capacity with accepted lag, queue deferrable work to absorb bursts, and horizontally scale stateless parallel work; measure the constrained stage first.
   - Three plausible distractors: add all four controls at once; use a queue to accelerate a synchronous read; add read replicas for a write-bound database.
   - Mapping: `SAA | SAA-3.2 / SAA-3.3 | CACHE-STRATEGIES, RDS-READ, SQS-METRICS, EX-SAA3`

2. **Intent — Implement cache-aside with explicit correctness rules.**
   - Correct principle: on a miss, read the authoritative store and populate the cache; define TTL, invalidation or versioning, stampede control, and acceptable staleness in the application.
   - Three plausible distractors: treat the cache as the only durable copy; set an infinite TTL for mutable records; expect ElastiCache to invalidate entries when RDS rows change.
   - Mapping: `SAA | SAA-3.3 | CACHE-STRATEGIES`

3. **Intent — Design cache failure and eviction behavior.**
   - Correct principle: size memory and choose eviction/persistence/failover settings for the engine, but keep the application able to tolerate misses and protect the database from a cold-cache surge.
   - Three plausible distractors: fail every request when the cache is unavailable; assume replicas prevent every cache miss; repopulate all keys simultaneously after failover.
   - Mapping: `SAP | SAP-3.3 | CACHE-STRATEGIES`

4. **Intent — Route reads safely to an RDS read replica.**
   - Correct principle: direct stale-tolerant reads to the replica endpoint/instance, monitor lag, retain writes on the writer, and handle promotion and client reconnection explicitly.
   - Three plausible distractors: send writes to every replica; promise read-after-write consistency from an asynchronous replica; use a Multi-AZ standby as a generic reader.
   - Mapping: `SAA | SAA-3.3 | RDS-READ, RDS-MULTIAZ`

5. **Intent — Use a queue to absorb a burst without hiding overload.**
   - Correct principle: decouple admission from processing, scale consumers from arrival rate and message age, bound useful backlog, and make processing idempotent; the queue does not increase downstream throughput.
   - Three plausible distractors: use unlimited retention as capacity; monitor only queue depth; acknowledge before durable processing.
   - Mapping: `SAA | SAA-2.1 | SQS-METRICS, SAA-SAMPLE`

6. **Intent — Make the compute tier horizontally scalable.**
   - Correct principle: remove instance-local authoritative session/job/file state, spread instances across AZs, and use health checks and load balancing so any healthy instance can serve the next request.
   - Three plausible distractors: rely permanently on sticky sessions; store user uploads on instance store; copy process memory during scale-out.
   - Mapping: `SAA | SAA-2.1 / SAA-2.2 | ASG-TARGET, EX-SAA2`

7. **Intent — Choose a target-tracking metric with a causal capacity relationship.**
   - Correct principle: use a metric that changes proportionally with load and decreases as capacity increases, set an SLO-safe target, and avoid per-instance or sparse metrics that violate target-tracking assumptions.
   - Three plausible distractors: scale on total fleet CPU credit balance; use request count with no per-target normalization; choose a business total that rises regardless of capacity.
   - Mapping: `SAA | SAA-3.2 | ASG-TARGET`

8. **Intent — Prevent premature scale-in while new capacity warms.**
   - Correct principle: configure default instance warmup and realistic health/readiness checks so initial metrics are not aggregated too early and scale-in does not remove capacity before it contributes.
   - Three plausible distractors: use the health-check grace period as a complete warmup substitute in every policy; set warmup to zero for a slow-starting service; publish healthy before dependencies are ready.
   - Mapping: `SAA | SAA-3.2 | ASG-WARMUP, SAA-SAMPLE`

9. **Intent — Diagnose high p99 with normal average CPU.**
   - Correct principle: inspect dependency latency, cache hit rate, replica lag, connection pools, queue age, throttles, and per-path traces; waiting on I/O or a minority slow path can dominate p99 while CPU remains low.
   - Three plausible distractors: conclude capacity is sufficient from average CPU; resize every instance upward; add a queue to the read path without changing the user contract.
   - Mapping: `SAP | SAP-3.3 | CW-CONCEPTS, XRAY-CONCEPTS`

10. **Intent — Prove a performance change against SLO and cost.**
    - Correct principle: change one primary bottleneck control at a time, load test representative traffic and failure modes, compare p50/p95/p99, errors, backlog/lag, saturation, hit rate, and cost per successful operation.
    - Three plausible distractors: accept lower average latency alone; compare two tests with different traffic; retain cache, replica, and queue changes even when no metric improves.
    - Mapping: `SAP | SAP-2.5 | CW-SLO, CW-CONCEPTS`

### Official calibration resources

- **Direct public mapping:** `SAA-SAMPLE` Question 7 calibrates queue buffering for a bursty workload.
- **Direct public mapping:** `SAA-SAMPLE` Question 9 calibrates Auto Scaling warmup behavior.
- **Direct public mapping:** `SAA-SAMPLE` Question 10 calibrates database read scaling.
- **Direct public mapping:** `SAP-SAMPLE` Question 8 calibrates queue-based backpressure and protecting a downstream database.
- `SAA-PREP` and `SAP-PREP` are appropriate for broader performance/scaling scenarios.
- No official public sample directly tests cache invalidation, cache-stampede recovery, or SLO/cost evidence.

---

## Chapter 65 — Service Quotas, Throttling, and Graceful Degradation

### Existing defects

- **Duplicate:** Questions 1, 4, and 5 repeat “inventory quotas, request increases, monitor usage, and shed optional load.”
- **Low-density:** The marked answer bundles Service Quotas control-plane work with application admission control and graceful degradation, although the service does not implement those application behaviors.
- **Factually unsafe:** Question 3 says quotas are per account and Region as a universal rule. Quotas vary: some are global, some Regional, some adjustable, and some are API-rate or resource limits.
- **Factually unsafe:** The question describes Service Quotas as part of the request/data path. It is a quota discovery and management control plane.
- **Factually unsafe:** “Automatic management” is presented as a generic setting. The feature supports selected quotas and still requires configured thresholds and monitoring; it is not universal unlimited scaling.
- CloudWatch and Lambda are generic distractors even though usage metrics, concurrency controls, throttles, and reserved concurrency are central to the chapter.
- The current set never distinguishes quota exhaustion, downstream saturation, transient throttling, retry storms, backlog growth, or connection/port exhaustion.
- No item tests bounded queues, admission control, bulkheads, critical-capacity reservation, overload game days, or evidence that degradation preserves core transactions.

### Ten replacement intents

1. **Intent — Classify a quota before designing around it.**
   - Correct principle: identify service, quota code, account/Region scope, default and applied values, adjustability, request rate versus resource count, and recovery-environment requirements.
   - Three plausible distractors: assume every quota is Regional; treat an API throttle as EC2 capacity; plan to request every increase during the incident.
   - Mapping: `SAA | SAA-2.2 | SQ-INTRO, EX-SAA2`

2. **Intent — Use Service Quotas Automatic Management within its boundary.**
   - Correct principle: enable it only for supported monitorable quotas, choose a threshold that leaves lead time, and retain owner, budget, downstream, and hard-limit controls.
   - Three plausible distractors: assume all quotas increase without approval; set the threshold at 100 percent; use quota growth as a substitute for capacity testing.
   - Mapping: `SAP | SAP-3.4 | SQ-AUTO`

3. **Intent — Alarm on quota usage and headroom.**
   - Correct principle: use Service Quotas usage metrics or service-specific metrics, compare utilization and growth with forecast demand, and alert early enough to increase capacity or reduce admission.
   - Three plausible distractors: monitor only CPU; alarm only after throttles affect users; use a cost budget as a real-time concurrency limit.
   - Mapping: `SAA → SAP | SAA-2.2 / SAP-3.4 | SQ-INTRO, CW-ALARM, SAP-SAMPLE`

4. **Intent — Distinguish Lambda reserved from provisioned concurrency.**
   - Correct principle: reserved concurrency reserves and caps concurrency to isolate functions and protect downstreams; provisioned concurrency pre-initializes environments to reduce startup latency but does not replace account and function concurrency planning.
   - Three plausible distractors: use provisioned concurrency as an unlimited quota increase; assign every function the account maximum as reserved concurrency; assume reserved concurrency removes downstream database limits.
   - Mapping: `SAA | SAA-3.2 | LAMBDA-CONC, SAP-SAMPLE`

5. **Intent — Handle transient throttling without a retry storm.**
   - Correct principle: retry only retryable failures with bounded attempts, exponential backoff and jitter, idempotency, and a total deadline; sustained overload needs admission reduction or more real capacity.
   - Three plausible distractors: retry immediately forever; increase all timeouts; retry non-idempotent writes without an operation key.
   - Mapping: `SAA | SAA-2.2 | SDK-RETRY, WA-GRACE`

6. **Intent — Reserve scarce capacity for a critical transaction.**
   - Correct principle: isolate checkout from recommendations with separate concurrency, queues, connection pools, or quotas, and shed optional work before shared dependencies saturate.
   - Three plausible distractors: put all requests in one unbounded pool; give optional work the same priority; rely on client retries to create capacity.
   - Mapping: `SAP | SAP-2.4 | WA-GRACE, LAMBDA-CONC`

7. **Intent — Bound an asynchronous queue by usefulness, not storage duration.**
   - Correct principle: define maximum useful age and backlog, monitor oldest-message age and processing rate, scale consumers, and expire or redirect work that cannot meet its business deadline.
   - Three plausible distractors: retain every message indefinitely; use queue depth alone; keep processing stale recommendations while payment events wait.
   - Mapping: `SAA | SAA-2.1 | SQS-METRICS, SAP-SAMPLE`

8. **Intent — Design a truthful graceful-degradation response.**
   - Correct principle: return cached/default/partial results for optional features, but fail closed, queue, or expose pending state where correctness cannot be approximated; preserve observability of degraded mode.
   - Three plausible distractors: return successful payment without authorization; hide degradation from metrics; fail the whole page because recommendations are unavailable.
   - Mapping: `SAA → SAP | SAA-2.2 / SAP-2.4 | WA-GRACE`

9. **Intent — Include quotas in DR and launch readiness.**
   - Correct principle: inventory and request recovery-Region quotas before deployment, test account/Region-specific capacity and IP/connection limits, and avoid assuming primary-Region limits transfer.
   - Three plausible distractors: clone a CloudFormation template and assume quotas clone; request increases after DNS failover; test only control-plane creation with no recovery load.
   - Mapping: `SAP | SAP-2.2 | SQ-INTRO, WA-DR`

10. **Intent — Run an overload game day with business evidence.**
    - Correct principle: inject throttling or cap capacity under safeguards, observe retry volume, queue age, rejection/degradation rate, critical-transaction success, recovery, and cost, then tune thresholds and runbooks.
    - Three plausible distractors: raise every quota before the test; validate only that alarms fired; remove limits and let the downstream fail.
    - Mapping: `SAP | SAP-3.4 | FIS-INTRO, WA-GRACE, CW-SLO`

### Official calibration resources

- **Direct public mapping:** `SAP-SAMPLE` Question 4 calibrates monitoring a concurrency quota and alarming before exhaustion.
- **Direct public mapping:** `SAP-SAMPLE` Question 8 calibrates buffering, concurrency control, and protection of a fixed-capacity database.
- **Partial public mapping:** `SAA-SAMPLE` Question 7 calibrates queue buffering, but not quota management or graceful degradation.
- `SAA-PREP` and `SAP-PREP` can calibrate broader quota, throttling, and multi-response scenarios.
- No official public sample directly tests Service Quotas Automatic Management, truthful degraded-mode contracts, or an overload game day.

---

## Chapter 66 — CloudWatch Metrics, Logs, Alarms, Dashboards, and SLOs

### Existing defects

- **Duplicate:** Questions 1 and 4 both select CloudWatch; Questions 2 and 3 re-list metrics versus logs.
- **Ambiguous:** Question 3 contains two correct chapter mechanisms—metrics/alarms and log-event processing—but marks only the first.
- **Ambiguous:** Question 5 rejects the high-cardinality warning even though it is an important, compatible observability design principle.
- **Low-density:** A single answer bundles namespace, dimensions, resolution, statistics, alarm periods, dashboards, and “retention” without testing any one behavior.
- **Factually unsafe:** CloudWatch metric retention is service-defined and resolution-dependent, not a user-configurable generic retention field like a log-group retention policy.
- **Factually unsafe:** Dashboards and green resource metrics are presented too close to operational proof; they do not establish business success or explain a change.
- No item tests SLI/SLO construction, error-budget burn, percentiles, M-of-N evaluation, missing data, composite alarms, cardinality cost, or alarm noise.
- CloudTrail, Config, traces, and business events are mentioned only in prose; the scored set does not distinguish telemetry from audit/change evidence.

### Ten replacement intents

1. **Intent — Define an SLI and SLO from a user outcome.**
   - Correct principle: choose an SLI such as successful checkout latency or availability, define a target and interval, and use the error budget or burn rate to guide alerts and change risk.
   - Three plausible distractors: use EC2 CPU as the checkout SLO; define “always fast” with no threshold; equate an AWS service SLA with the workload SLO.
   - Mapping: `SAP | SAP-3.1 | CW-SLO, EX-SAP3`

2. **Intent — Place metrics, logs, and traces in complementary roles.**
   - Correct principle: metrics summarize trends and support alarms, logs retain event context, and traces connect one distributed path; correlate them with stable identifiers.
   - Three plausible distractors: convert every log field into a metric dimension; use traces as the only long-term audit record; use dashboards instead of logs.
   - Mapping: `SAA | SAA-3.2 | CW-CONCEPTS, CWL-CONCEPTS, XRAY-CONCEPTS`

3. **Intent — Monitor business outcomes before supporting resources.**
   - Correct principle: alarm on success rate, latency, freshness, backlog age, or completed transactions, then use CPU, memory, throttles, and dependency metrics for diagnosis.
   - Three plausible distractors: declare health from average CPU; alarm only on instance status; count accepted requests as completed orders.
   - Mapping: `SAA → SAP | SAA-2.2 / SAP-3.1 | CW-SLO, CW-CONCEPTS`

4. **Intent — Choose statistics and percentiles that expose tail latency.**
   - Correct principle: use suitable periods and p95/p99 for user latency, retain counts/sample size, and use average only when it represents the decision; sparse or negative-valued data can constrain percentile interpretation.
   - Three plausible distractors: use monthly average for a five-minute SLO; add percentiles across instances; treat p99 as the slowest single request.
   - Mapping: `SAA | SAA-3.2 | CW-CONCEPTS`

5. **Intent — Configure M-of-N and missing-data treatment deliberately.**
   - Correct principle: set period, evaluation periods, datapoints to alarm, and missing-data behavior from the metric’s emission semantics so sparse success, silence, and no traffic are not confused.
   - Three plausible distractors: always treat missing as breaching; alarm on one noisy point for every metric; assume missing data means zero.
   - Mapping: `SAA | SAA-2.2 | CW-ALARM`

6. **Intent — Reduce alert noise with composite alarms and dependencies.**
   - Correct principle: combine underlying alarms to page only when user impact and a relevant failure condition coexist, while retaining component alarms for diagnosis.
   - Three plausible distractors: delete all component alarms; combine unrelated services with OR and page more often; use a dashboard widget as an alarm dependency.
   - Mapping: `SAP | SAP-3.1 | CW-COMPOSITE`

7. **Intent — Control metric cardinality and cost.**
   - Correct principle: dimensions create distinct custom metrics; keep bounded operational dimensions as metrics and place unbounded request/user identifiers in logs or traces.
   - Three plausible distractors: create a dimension for every request ID; assume EMF makes high cardinality free; remove all dimensions and lose service/operation breakdown.
   - Mapping: `SAP | SAP-3.1 | CW-EMF`

8. **Intent — Design log retention, search, and streaming separately.**
   - Correct principle: set log-group retention and encryption, use Logs Insights for interactive queries, metric filters for bounded signals, and subscription filters for continuous downstream processing.
   - Three plausible distractors: use a metric-retention setting to expire logs; use Logs Insights as a permanent streaming destination; create a custom metric for every raw log field.
   - Mapping: `SAA | SAA-2.2 | CWL-CONCEPTS`

9. **Intent — Centralize multi-account observability without erasing ownership.**
   - Correct principle: link source accounts to a monitoring account with cross-account observability, standardize identifiers and access, and retain workload owners and account-local response paths.
   - Three plausible distractors: copy credentials into the monitoring account; move all workloads into one account; assume cross-account views change source retention policies automatically.
   - Mapping: `SAP | SAP-3.1 | CW-XACCT`

10. **Intent — Separate operational evidence from audit and configuration evidence.**
    - Correct principle: use CloudWatch for runtime signals, CloudTrail for API activity, and Config for resource configuration/history; correlate deploy/change events to SLO impact before rollback.
    - Three plausible distractors: use a green dashboard as proof no configuration changed; use CloudTrail as a latency time series; use Config as an application transaction log.
    - Mapping: `SAP | SAP-3.1 | CLOUDTRAIL, CONFIG, CW-SLO`

### Official calibration resources

- **Partial public mapping:** `SAP-SAMPLE` Question 1 calibrates selecting a CloudWatch alarm for a billing threshold.
- **Direct public mapping:** `SAP-SAMPLE` Question 4 calibrates selecting the correct usage metric and threshold for a quota alarm.
- `SAA-PREP` and `SAP-PREP` are the official resources for additional monitoring and operational-excellence calibration.
- **No official public sample question maps directly** to workload SLOs, M-of-N/missing-data behavior, composite alarms, cross-account observability, or CloudTrail-versus-Config evidence.

---

## Chapter 67 — X-Ray, OpenTelemetry, Tracing, and Bottleneck Analysis

### Existing defects

- **Ambiguous:** Question 1 marks trace-context propagation as correct but rejects “metrics find impact, traces locate a path, logs provide detail,” which is also correct and more complete.
- **Duplicate:** Questions 1, 3, and 4 all reward the same X-Ray summary.
- **Low-density:** The settings answer bundles sampling, daemon/SDK/ADOT, annotations/metadata, groups, and trace map without testing their distinct effects.
- **Factually unsafe:** The chapter copies X-Ray segment/subsegment wording into ADOT. OpenTelemetry uses traces and spans; an exporter can translate/send telemetry to X-Ray.
- **Factually unsafe:** A service map supports dependency and latency/error analysis, but visual correlation alone does not prove causal responsibility.
- **Time-sensitive:** AWS states that X-Ray SDKs and daemon entered maintenance mode on 2026-02-25 and reach end of support on 2027-02-25; new instrumentation should prefer OpenTelemetry.
- The current set does not test context loss, async messaging, sampling bias, searchable annotations, sensitive metadata, version/deployment correlation, or tracing cost.
- No official evidence loop connects a p99 regression to one deployment, operation, tenant class, or downstream dependency.

### Ten replacement intents

1. **Intent — Use metrics, logs, and traces in the correct diagnostic sequence.**
   - Correct principle: metrics or SLOs reveal population-level impact, traces isolate representative request paths and dependencies, and logs provide detailed events for the implicated components.
   - Three plausible distractors: sample traces as the only alert signal; inspect random logs before identifying the affected operation; use average CPU to locate a distributed p99 path.
   - Mapping: `SAA → SAP | SAA-3.2 / SAP-3.3 | CW-CONCEPTS, XRAY-CONCEPTS`

2. **Intent — Preserve trace context across synchronous services.**
   - Correct principle: propagate the supported trace headers/context through ingress, application, SDK/client calls, and downstream services, creating child spans/subsegments under the same trace.
   - Three plausible distractors: generate a new root trace in every service; put correlation only in a local log file; trust source IP as a request identity.
   - Mapping: `SAA | SAA-3.2 | XRAY-CONCEPTS, CW-OTEL`

3. **Intent — Interpret X-Ray trace structure and inferred nodes.**
   - Correct principle: segments represent traced services/resources, subsegments represent downstream work, and inferred nodes can arise from downstream call data; missing instrumentation can leave gaps.
   - Three plausible distractors: treat every map edge as a fully instrumented service; equate a segment with an EC2 instance; assume an inferred node contains complete downstream logs.
   - Mapping: `SAA | SAA-3.2 | XRAY-CONCEPTS`

4. **Intent — Design sampling without hiding rare failures.**
   - Correct principle: use sampling rules to control volume and cost, retain bounded baseline coverage, and add targeted rules or complementary error metrics/logs for high-value or rare operations.
   - Three plausible distractors: trace 100 percent indefinitely by default; sample only successful requests; assume a one-percent sample proves no rare error exists.
   - Mapping: `SAP | SAP-3.1 | XRAY-CONCEPTS, CW-SLO`

5. **Intent — Use annotations and metadata safely.**
   - Correct principle: add bounded, searchable business/technical attributes as annotations; keep larger non-indexed diagnostic context as metadata; do not place secrets or unnecessary personal data in telemetry.
   - Three plausible distractors: use customer email as an unbounded indexed annotation; store credentials in metadata because it is not indexed; create a unique annotation key per request.
   - Mapping: `SAP | SAP-3.1 | XRAY-CONCEPTS`

6. **Intent — Treat the service map as a hypothesis generator.**
   - Correct principle: use map latency/error edges to select traces, then inspect timelines, attempts, downstream responses, and correlated logs before assigning causality.
   - Three plausible distractors: blame the node with the largest circle; treat correlation as proof; ignore client-side queuing and retries.
   - Mapping: `SAP | SAP-3.3 | XRAY-CONCEPTS`

7. **Intent — Diagnose a p99 bottleneck from trace timelines.**
   - Correct principle: compare fast and slow traces for the same operation, decompose exclusive time, downstream latency, retries, cold starts, queueing, and connection waits, then validate the suspected constraint with metrics.
   - Three plausible distractors: optimize the longest average service only; sum overlapping parallel spans as serial time; resize every component in the trace.
   - Mapping: `SAP | SAP-3.3 | XRAY-CONCEPTS, CW-CONCEPTS`

8. **Intent — Continue correlation across asynchronous messaging.**
   - Correct principle: propagate or link trace context and a stable business/job identifier through messages, while recognizing producer acceptance and consumer processing are separate timing segments.
   - Three plausible distractors: reuse one trace ID for every queue message; measure queue wait as Lambda execution time; rely on message body text without a stable identifier.
   - Mapping: `SAP | SAP-3.1 | CW-OTEL, SQS-METRICS`

9. **Intent — Migrate new instrumentation from X-Ray SDKs to OpenTelemetry.**
   - Correct principle: instrument with supported OpenTelemetry libraries/ADOT, export to CloudWatch/X-Ray as required, and plan migration before X-Ray SDK/daemon end of support; do not assume ADOT terminology and behavior are identical to legacy SDKs.
   - Three plausible distractors: start a new long-lived implementation on the legacy daemon with no migration plan; remove tracing during migration; assume exporter replacement alone fixes missing application context.
   - Mapping: `SAP | SAP-3.1 | XRAY-TIMELINE, CW-OTEL, ADOT-XRAY`

10. **Intent — Correlate tracing evidence with deployment and cost.**
    - Correct principle: tag/version telemetry with service and deployment identity, compare SLO and trace distributions before/after rollout, bound sampling/cardinality, and retain rollback evidence.
    - Three plausible distractors: use a release timestamp only in a dashboard title; increase sampling until cost is ignored; rollback from one anecdotal trace without population metrics.
    - Mapping: `SAP | SAP-3.3 | CW-SLO, XRAY-CONCEPTS, CW-EMF`

### Official calibration resources

- `SAA-PREP` and `SAP-PREP` can legally calibrate official performance-diagnosis and operational-excellence question style.
- **No official public sample question maps directly** to X-Ray, OpenTelemetry, sampling, annotation/metadata boundaries, async trace propagation, or the 2026–2027 X-Ray SDK support transition.

---

## Chapter 68 — Reserved Instances, Savings Plans, Spot, and Commitments

### Existing defects

- **Duplicate:** Questions 1, 4, and 5 repeat the baseline/Spot/On-Demand portfolio summary.
- **Low-density:** The marked choice combines Savings Plans, Reserved Instances, Spot, and On-Demand, but its explanation describes only Savings Plans.
- **Category error:** Question 3 asks how Savings Plans work in the request/data path. They are a billing construct and do not alter workload routing, capacity, or runtime behavior.
- **Factually unsafe:** “Reserved Instances for EC2/RDS and some Zonal RIs reserve capacity” conflates products. The capacity benefit applies to matching EC2 Zonal RIs, not generic Reserved DB Instances.
- **Factually unsafe:** A Spot interruption warning should not be treated as guaranteed recovery time; workloads must be interruption-tolerant even if notices or rebalance recommendations are unavailable or too late.
- **Time-sensitive/incomplete:** The settings list freezes Savings Plans into Compute/EC2/SageMaker categories. As of the audit date, AWS documentation also describes Database Savings Plans; exam coverage must be version-pinned rather than inferred from the current product catalog.
- The set does not test commitment utilization versus coverage, hourly-commitment waste, sharing, payment options, license/tenancy constraints, or Capacity Reservations.
- No item requires historical-baseline analysis, checkpoint evidence, diversified Spot pools, or organizational ownership of long-lived commitments.

### Ten replacement intents

1. **Intent — Layer purchase options by demand certainty and interruption tolerance.**
   - Correct principle: cover a conservative steady baseline with an appropriate commitment, keep uncertain bursts On-Demand, and use Spot only for fault-tolerant work that can checkpoint, retry, or redistribute.
   - Three plausible distractors: commit to the annual peak; put a singleton stateful service entirely on Spot; use On-Demand for a stable multi-year baseline without evaluating discounts.
   - Mapping: `SAA | SAA-4.2 | SP-INTRO, SPOT-INTERRUPT, SAA-SAMPLE`

2. **Intent — Choose Compute Savings Plans for broad compute flexibility.**
   - Correct principle: Compute Savings Plans exchange an hourly spend commitment for eligible discounts with broader flexibility across EC2 attributes and supported compute services than EC2 Instance Savings Plans.
   - Three plausible distractors: claim they reserve EC2 capacity; assume unused hourly commitment rolls into the next hour; apply them to every AWS charge.
   - Mapping: `SAA | SAA-4.2 | SP-INTRO, SP-APPLY`

3. **Intent — Choose EC2 Instance Savings Plans for a stable family/Region footprint.**
   - Correct principle: accept narrower EC2 family and Region commitment when the workload is stable enough for the typically stronger discount; sizing and eligible usage still determine utilization.
   - Three plausible distractors: use it for Lambda usage; assume it follows any EC2 family worldwide; treat it as a Zonal capacity reservation.
   - Mapping: `SAA | SAA-4.2 | SP-INTRO, SP-APPLY`

4. **Intent — Distinguish an EC2 RI discount from a Capacity Reservation.**
   - Correct principle: Regional RI benefits are billing discounts without a capacity reservation; matching Zonal RIs include a capacity benefit, while On-Demand Capacity Reservations solve capacity assurance and can be combined with eligible discounts.
   - Three plausible distractors: assume every RI reserves capacity in every AZ; use a Capacity Reservation as an automatic discount; treat an RDS Reserved Instance as EC2 capacity.
   - Mapping: `SAA → SAP | SAA-4.2 / SAP-2.6 | EC2-RI, EC2-CR`

5. **Intent — Compare Standard and Convertible EC2 RIs.**
   - Correct principle: use Standard RIs for stable matching attributes and higher discount potential; use Convertible RIs when exchange flexibility is worth a lower discount, subject to offering rules.
   - Three plausible distractors: convert Standard RIs freely to any service; treat Convertible RIs as Spot capacity; assume either class changes the running instance configuration automatically.
   - Mapping: `SAP | SAP-2.6 | EC2-RI`

6. **Intent — Diagnose commitment coverage and utilization separately.**
   - Correct principle: coverage asks how much eligible usage received a discount; utilization asks how much purchased commitment was consumed. Low coverage can coexist with high utilization and vice versa.
   - Three plausible distractors: use coverage as proof no commitment is wasted; buy more when utilization is already low; measure only total bill reduction.
   - Mapping: `SAP | SAP-1.5 | SP-PURCHASE, SP-APPLY`

7. **Intent — Size a commitment from durable baseline evidence.**
   - Correct principle: use representative historical usage, seasonality, planned migrations, architecture changes, and business headroom; commit conservatively because unused hourly commitment is still charged.
   - Three plausible distractors: buy from one week’s peak; assume a rightsizing project will not change usage; commit before deciding whether workloads move to containers or serverless.
   - Mapping: `SAP | SAP-2.6 | SP-PURCHASE`

8. **Intent — Build a Spot workload that survives interruption.**
   - Correct principle: checkpoint durable progress, make work idempotent, diversify instance types and AZ capacity pools, handle interruption notices/rebalance recommendations, and maintain enough non-Spot capacity for critical service.
   - Three plausible distractors: save progress only on instance store; wait until termination to start checkpointing; use one cheapest instance type in one AZ.
   - Mapping: `SAA | SAA-4.2 | SPOT-INTERRUPT, SPOT-REBALANCE`

9. **Intent — Select a Spot allocation approach from the objective.**
   - Correct principle: prefer capacity-aware diversified allocation for resilient fleets; do not optimize only for the lowest instantaneous price when interruption and replacement risk dominate.
   - Three plausible distractors: choose a single pool by lowest price; pin all nodes to one large type; treat `max price` as a capacity guarantee.
   - Mapping: `SAP | SAP-2.6 | SPOT-REBALANCE`

10. **Intent — Govern commitments across an organization and exam versions.**
    - Correct principle: assign purchase ownership, sharing/allocation policy, utilization review, chargeback, and exit assumptions; label newer product families such as Database Savings Plans as current-service extensions until the target exam blueprint confirms coverage.
    - Three plausible distractors: let each account buy independently with no inventory; treat a billing discount as transferable capacity; add every new pricing product to the exam bank without version review.
    - Mapping: `SAP | SAP-1.5 | SP-INTRO, SP-PURCHASE, EX-SAP1`

### Official calibration resources

- **Direct public mapping:** `SAA-SAMPLE` Question 6 calibrates combining a stable baseline discount with non-interruptible burst capacity.
- `SAA-PREP` and `SAP-PREP` are appropriate for Savings Plans, RIs, Spot, and cost-optimization scenarios.
- **No official public sample question maps directly** to coverage-versus-utilization, Capacity Reservations, Spot rebalance handling, organization sharing, or Database Savings Plans.

---

## Chapter 69 — Rightsizing and AWS Compute Optimizer

### Existing defects

- **Duplicate:** Questions 1, 4, and 5 all state that Compute Optimizer recommendations require long-term metrics and validation.
- **Category error:** Question 3 asks for Compute Optimizer behavior in the request/data path. It is an analytics/recommendation service, not a runtime component.
- **Low-density:** The settings item combines opt-in, lookback, enhanced metrics, external ingestion, and recommendation preferences without testing the decisions behind any one of them.
- **Factually unsafe:** “Memory requires an agent” is overly broad. For EC2, memory requires an agent or supported external metric source; other supported resource types expose different metrics.
- **Factually unsafe:** The chapter suggests p95/p99 are direct Compute Optimizer recommendation inputs. They are workload SLO validation signals, not a generic claim about the service’s optimization model.
- The current bank does not test burstable CPU credits, network/EBS limits, monthly seasonality, scheduled scaling, idle resources, or whether the proposed target architecture is compatible.
- It does not distinguish estimated savings from realized savings, or recommendation confidence/performance risk from application acceptance.
- The repeated generic canary/rollback answer never asks what evidence makes a rightsizing rollout safe.

### Ten replacement intents

1. **Intent — Define rightsizing as price-performance optimization, not CPU minimization.**
   - Correct principle: choose the least-cost resource configuration that still meets latency, throughput, availability, and growth objectives across CPU, memory, network, storage, and dependencies.
   - Three plausible distractors: shrink whenever average CPU is below 20 percent; optimize monthly price without an SLO; keep the largest instance because headroom is always safer.
   - Mapping: `SAA | SAA-4.2 | CO-INTRO, CW-SLO`

2. **Intent — Interpret a Compute Optimizer recommendation correctly.**
   - Correct principle: treat it as an evidence-backed candidate with estimated savings and performance risk, not an automatic safe change; validate business context, compatibility, and workload tests.
   - Three plausible distractors: apply every recommendation automatically; ignore underprovisioned findings because cost rises; treat “optimized” as a production guarantee.
   - Mapping: `SAA → SAP | SAA-4.2 / SAP-3.5 | CO-INTRO`

3. **Intent — Supply meaningful memory evidence for EC2 rightsizing.**
   - Correct principle: publish memory metrics through the CloudWatch agent or configure a supported external observability integration; verify namespace, dimensions, permissions, and sufficient history.
   - Three plausible distractors: infer memory from CPU alone; install an agent but never grant metric permissions; assume EC2 publishes guest memory by default.
   - Mapping: `SAP | SAP-3.3 | CO-MEM, CO-EXT`

4. **Intent — Use lookback and enhanced infrastructure metrics for seasonal workloads.**
   - Correct principle: choose a history window that includes relevant peaks; enhanced infrastructure metrics can extend analysis and incur cost, but no finite lookback replaces knowledge of future events.
   - Three plausible distractors: rightsize a month-end service from seven quiet days; assume longer lookback predicts an upcoming launch; enable paid history for every resource without prioritization.
   - Mapping: `SAP | SAP-3.5 | CO-EIM`

5. **Intent — Avoid rightsizing a burstable instance from average CPU alone.**
   - Correct principle: inspect CPU credit balance and surplus charges/usage with latency and throughput; sustained demand may require a non-burstable family or a larger baseline.
   - Three plausible distractors: treat low current CPU as spare sustained capacity; ignore depleted credits; buy unlimited-mode surplus indefinitely without comparing alternatives.
   - Mapping: `SAA | SAA-4.2 | EC2-CREDITS`

6. **Intent — Coordinate instance rightsizing with Auto Scaling.**
   - Correct principle: evaluate fleet-level demand, target metric, min/max/desired capacity, warmup, and instance mix; a smaller instance can increase fleet count or scaling churn rather than reduce total cost.
   - Three plausible distractors: resize one instance and extrapolate to the fleet; keep the same target after changing per-instance capacity without validation; disable Auto Scaling during normal operation.
   - Mapping: `SAA | SAA-3.2 / SAA-4.2 | ASG-TARGET, ASG-WARMUP`

7. **Intent — Check network and EBS ceilings before changing EC2 size.**
   - Correct principle: verify instance network, ENA, EBS bandwidth/IOPS, packet rate, and attached-volume limits; CPU/memory fit alone can create a new bottleneck.
   - Three plausible distractors: assume all sizes in a family have identical I/O; use volume provisioned IOPS as proof the instance can deliver them; test only idle startup.
   - Mapping: `SAA | SAA-3.2 | CO-MEM, EBS-TYPES`

8. **Intent — Use scheduled scaling for known periodic demand.**
   - Correct principle: pre-scale for predictable month-end or campaign peaks, combine with dynamic policies for variance, and keep the steady fleet right-sized rather than paying peak capacity all month.
   - Three plausible distractors: permanently size for the monthly peak; rely on scale-out after the known spike begins; schedule scale-in before long-running work completes.
   - Mapping: `SAA | SAA-3.2 / SAA-4.2 | ASG-SCHEDULED, ASG-TARGET`

9. **Intent — Roll out a rightsizing change with SLO and rollback evidence.**
   - Correct principle: canary a representative slice, load test steady and peak traffic, monitor latency percentiles, errors, saturation, queue/replica lag, and cost, and retain a fast rollback path.
   - Three plausible distractors: change every instance family at once; accept a lower hourly rate despite worse p99; remove the previous launch template immediately.
   - Mapping: `SAP | SAP-3.3 | CW-SLO, CO-INTRO`

10. **Intent — Prioritize organization-wide optimization opportunities.**
    - Correct principle: use Cost Optimization Hub and Compute Optimizer findings with ownership, estimated savings, effort, risk, age, and realized-savings tracking; deduplicate overlapping recommendations.
    - Three plausible distractors: sort only by headline savings; count an accepted recommendation as realized savings; optimize untagged resources without identifying a service owner.
    - Mapping: `SAP | SAP-1.5 / SAP-3.5 | COST-HUB, CO-INTRO`

### Official calibration resources

- **Partial public mapping:** `SAA-SAMPLE` Question 9 calibrates how warmup affects scaling behavior, which is relevant to safe fleet rightsizing.
- **Partial public mapping:** `SAP-SAMPLE` Question 7 calibrates a cost-aware redesign, but not Compute Optimizer.
- `SAA-PREP` and `SAP-PREP` are appropriate for broader rightsizing and cost-improvement calibration.
- **No official public sample question maps directly** to Compute Optimizer, enhanced infrastructure metrics, memory ingestion, burstable credits, or realized-savings evidence.

---

## Chapter 70 — Storage and Database Cost Optimization

### Existing defects

- **Low-density:** Question 1 combines a data-lake scan problem with a DynamoDB capacity problem, then marks a broad answer containing lifecycle, compression, storage classes, gp3, database consolidation, and read patterns.
- **Duplicate:** Questions 1, 4, and 5 repeat the same broad optimization list.
- **Category error:** The S3 Lifecycle explanation is used to justify unrelated Athena, EBS, DynamoDB, and relational database decisions.
- **Factually unsafe:** Lifecycle transitions do not reduce Athena bytes scanned; partitioning, compression, and columnar format address that cost.
- **Factually unsafe:** The statement about minimum object size and duration is too generic. Rules vary by storage class, and current S3 behavior for objects below 128 KB requires version-aware treatment.
- **Ambiguous:** “Serverless/on-demand may cost less when idle; provisioned may cost less when stable” is rejected even though it directly addresses the DynamoDB half of the scenario.
- The current set does not test actual access frequency, retrieval latency/fees, noncurrent versions, Intelligent-Tiering monitoring, DynamoDB hot keys, EBS performance, or backup retention.
- No item asks for a cost-per-business-operation baseline or evidence that a change preserved recoverability and performance.

### Ten replacement intents

1. **Intent — Optimize total cost per successful business operation.**
   - Correct principle: include storage, requests, I/O, compute scan, retrieval, backups, replicas, transfer, and operational effort while preserving latency, durability, and recovery objectives.
   - Three plausible distractors: compare only price per GB-month; remove backups to lower unit cost; move to the cheapest class without modeling access.
   - Mapping: `SAP | SAP-2.6 | EX-SAP2, COST-HUB`

2. **Intent — Choose an S3 storage class and Lifecycle transition from access evidence.**
   - Correct principle: use object age, size, access frequency, retrieval latency, minimum-duration and retrieval charges, and resilience requirements; scope current and noncurrent versions separately.
   - Three plausible distractors: transition every new object immediately; use Deep Archive for millisecond retrieval; expire current versions and assume old versions disappear.
   - Mapping: `SAA | SAA-4.1 | S3-LIFECYCLE, EX-SAA4`

3. **Intent — Handle small-object Lifecycle economics and current behavior.**
   - Correct principle: model per-object request/monitoring overhead and the current default behavior for objects below 128 KB; use explicit size filters only after validating economics and pin the content to the documented service version.
   - Three plausible distractors: assume every small object transitions automatically; treat minimum billable size as actual object size; force transitions because colder storage always wins.
   - Mapping: `SAP | SAP-3.5 | S3-LIFECYCLE`

4. **Intent — Use S3 Intelligent-Tiering for uncertain long-lived access patterns.**
   - Correct principle: use it when access is unpredictable and objects are suitable for tiering, account for monitoring/automation charges and small-object behavior, and opt into archive tiers only when restore latency is acceptable.
   - Three plausible distractors: use it for short-lived tiny objects without analysis; assume optional archive tiers are instant access; treat it as a backup service.
   - Mapping: `SAA | SAA-4.1 | S3-IT`

5. **Intent — Reduce Athena scanned bytes through data layout.**
   - Correct principle: partition on selective query dimensions, compress, and use columnar formats such as Parquet or ORC so queries read required columns and partitions instead of full raw objects.
   - Three plausible distractors: rely on S3 Lifecycle alone; convert to many tiny text files; add a DynamoDB GSI to S3 objects.
   - Mapping: `SAA | SAA-4.1 | ATHENA-COLUMNAR`

6. **Intent — Select EBS gp3 or provisioned-IOPS storage from requirements.**
   - Correct principle: gp3 decouples baseline size, IOPS, and throughput for many workloads; choose io2 when consistent high IOPS/durability requirements justify it, and check instance EBS limits.
   - Three plausible distractors: grow gp3 size only to buy performance; use st1 for latency-sensitive random OLTP; provision volume IOPS above instance capability and expect full delivery.
   - Mapping: `SAA | SAA-4.1 | EBS-TYPES`

7. **Intent — Choose DynamoDB on-demand versus provisioned capacity.**
   - Correct principle: use on-demand for unknown or spiky traffic and lower capacity-management effort; evaluate provisioned with auto scaling or reserved capacity for predictable stable demand using observed consumed capacity and growth.
   - Three plausible distractors: assume on-demand is always cheapest; provision from daily average without peaks; change mode to fix a hot partition.
   - Mapping: `SAA | SAA-4.3 | DDB-CAPACITY, DDB-ONDEMAND`

8. **Intent — Reduce DynamoDB cost through access-pattern and key design.**
   - Correct principle: distribute traffic across high-cardinality partition keys, remove unused GSIs, choose item size/projection and consistency deliberately, and avoid scans that consume broad capacity.
   - Three plausible distractors: add a GSI for every optional query; use a constant partition key; switch to on-demand and ignore hot keys and scans.
   - Mapping: `SAA | SAA-3.3 / SAA-4.3 | DDB-PARTITIONS, DDB-CAPACITY`

9. **Intent — Include backup, replica, and idle-storage cost in database TCO.**
   - Correct principle: inventory retained automated backups/snapshots, read replicas, cross-Region copies, overprovisioned storage/IOPS, and idle instances while preserving required RPO/RTO.
   - Three plausible distractors: delete all snapshots older than the last full backup; count replicas as free HA; reduce backup retention without a compliance or restore analysis.
   - Mapping: `SAP | SAP-3.5 | RDS-BACKUP-COST, WA-RTO-RPO`

10. **Intent — Validate a storage/database cost change with evidence.**
    - Correct principle: compare before/after cost by tagged owner and operation, request/scan/retrieval volume, latency and throttles, restore evidence, and data correctness; account for one-time transition and retrieval charges.
    - Three plausible distractors: use forecast savings as realized savings; ignore first-month transition fees; accept lower cost with an untested restore path.
    - Mapping: `SAP | SAP-1.5 | COST-HUB, CW-SLO, BACKUP-RESTORE`

### Official calibration resources

- `SAA-PREP` and `SAP-PREP` are the official resources for storage/database cost-optimization scenarios.
- **Partial public mapping:** `SAP-SAMPLE` Question 7 calibrates cost-aware managed redesign, but its focus is not this chapter’s storage/database controls.
- **No official public sample question maps directly** to S3 Lifecycle economics, the current small-object transition rule, Intelligent-Tiering, Athena bytes scanned, DynamoDB capacity-mode economics, or database backup TCO.

---

## Chapter 71 — Data Transfer, NAT, Cross-AZ, and Network Cost

### Existing defects

- **Mismatch:** Question 1 correctly proposes endpoints to avoid NAT cost, but its explanation praises NAT Gateway behavior rather than the endpoint path that solves the stated PB-scale S3 problem.
- **Duplicate:** Questions 1, 4, and 5 all repeat “draw the per-GB path and use endpoints/local AZ/CloudFront.”
- **Low-density:** Question 2 combines public/private NAT type, subnet, EIP, per-AZ routes, port capacity, and metrics as though one configuration applies to every NAT design.
- **Factually unsafe:** A private NAT gateway does not use an Elastic IP and does not provide internet access; the current option conflates it with public NAT.
- **Time-sensitive/incomplete:** The chapter assumes only zonal NAT Gateway architecture. AWS now documents Regional NAT Gateway; this must be marked as a current-service extension and not silently injected into older exam mappings.
- **Factually unsafe:** “Use an endpoint to reduce cost” is not universally true. Gateway endpoints and interface endpoints have different availability, routing, policy, hourly, and data-processing economics.
- Cross-AZ charges are treated as a simple penalty; service-specific pricing and managed-service exceptions require a concrete byte path.
- Transit Gateway, centralized inspection, CloudFront cache behavior, NAT port exhaustion, VPC Flow Logs, and cost-allocation evidence are not tested independently.

### Ten replacement intents

1. **Intent — Draw every billed network hop before optimizing.**
   - Correct principle: map source/destination AZ and Region, NAT, endpoint, load balancer, Transit Gateway, inspection, internet/edge, direction, and volume; apply current service pricing to each hop.
   - Three plausible distractors: optimize only instance price; assume one logical request incurs one transfer charge; treat all traffic inside a VPC as free.
   - Mapping: `SAP | SAP-1.5 | VPC-PRICING, EX-SAP1`

2. **Intent — Route private S3 traffic through a gateway endpoint.**
   - Correct principle: associate the S3 gateway endpoint with the required route tables and policies so in-Region VPC-to-S3 traffic avoids internet/NAT paths; validate DNS, policy, and route scope.
   - Three plausible distractors: send S3 traffic to `0.0.0.0/0` through NAT; attach a security group to a gateway endpoint; assume the endpoint grants object access without IAM/bucket policy.
   - Mapping: `SAA | SAA-4.4 | S3-GWEP, NAT-COST, SAA-SAMPLE`

3. **Intent — Compare an interface endpoint with NAT for an AWS service API.**
   - Correct principle: compare interface endpoint hourly/ENI/data processing and per-AZ placement with NAT hourly/data processing/cross-AZ path, while checking service support, private DNS, policy, and traffic volume.
   - Three plausible distractors: declare interface endpoints always cheaper; use an S3 gateway endpoint for every AWS service; ignore cross-AZ access to a single endpoint ENI.
   - Mapping: `SAP | SAP-2.6 | VPC-PRICING, NAT-COST`

4. **Intent — Design a zonal NAT path that avoids accidental cross-AZ dependency.**
   - Correct principle: for zonal NAT gateways, place one in each required AZ and route private subnets to the local-AZ NAT when availability and traffic economics justify it; monitor each gateway.
   - Three plausible distractors: route every AZ through one NAT without accepting its failure/cost path; put the public NAT in a private subnet; assume cross-zone load balancing fixes egress routing.
   - Mapping: `SAA | SAA-2.2 / SAA-4.4 | NAT-OVERVIEW, NAT-COST`

5. **Intent — Distinguish public and private NAT gateways.**
   - Correct principle: public NAT uses an Elastic IP and internet gateway path for outbound internet access; private NAT translates private addresses for private connectivity and does not provide internet egress.
   - Three plausible distractors: assign an EIP to a private NAT for internet access; accept unsolicited inbound internet connections through public NAT; use either type as a stateful firewall policy engine.
   - Mapping: `SAA | SAA-3.4 | NAT-OVERVIEW`

6. **Intent — Evaluate Regional NAT Gateway as a versioned design option.**
   - Correct principle: Regional NAT Gateway is a distinct current service option that simplifies multi-AZ internet egress and scales across AZs; validate Region availability, routing, quotas, failure model, and pricing, and label it outside older exam assumptions unless confirmed.
   - Three plausible distractors: treat it as an alias for several zonal EIPs; assume every SAA-C03/SAP-C02 question includes it; use it for unsolicited inbound internet traffic.
   - Mapping: `SAP | SAP-1.1 / SAP-3.5 | NAT-REGIONAL, EX-SAP1`

7. **Intent — Use CloudFront only when its HTTP edge/cache contract fits.**
   - Correct principle: reduce origin requests and long-distance transfer for cacheable HTTP content by designing cache keys, TTLs, invalidation/versioning, and origin policy; do not treat CloudFront as a generic database or UDP cache.
   - Three plausible distractors: cache personalized responses under one shared key; use CloudFront for arbitrary database replication; set long TTLs with no content-version strategy.
   - Mapping: `SAA | SAA-4.4 | CF-CACHE`

8. **Intent — Reduce cross-AZ chat without sacrificing required resilience.**
   - Correct principle: measure traffic by service/AZ, use topology-aware placement and local targets where appropriate, batch/compress calls, and retain enough multi-AZ capacity and failover behavior to meet availability objectives.
   - Three plausible distractors: force every dependency into one AZ; disable cross-zone behavior without checking uneven capacity; ignore retry-amplified bytes.
   - Mapping: `SAP | SAP-2.5 / SAP-2.6 | FAULT-AZ, VPC-PRICING`

9. **Intent — Price centralized egress and inspection end to end.**
   - Correct principle: count Transit Gateway, NAT, inspection appliance/service, endpoint, cross-AZ, and data-transfer processing in both directions; balance governance against cost, latency, and blast radius.
   - Three plausible distractors: count only the NAT processing charge; centralize all traffic because one gateway must be cheaper; ignore return-path symmetry through stateful inspection.
   - Mapping: `SAP | SAP-1.1 / SAP-2.6 | VPC-PRICING, NAT-COST`

10. **Intent — Produce evidence for a network-cost optimization.**
    - Correct principle: correlate NAT metrics, VPC Flow Logs, route and endpoint configuration, CUR/Cost Explorer dimensions, cache hit rate, and business traffic before and after the change; verify connectivity and failover.
    - Three plausible distractors: infer bytes from request count alone; accept a lower NAT bill while traffic moved to an untracked charge; delete the old route before rollback testing.
    - Mapping: `SAP | SAP-3.5 | NAT-METRICS, VPC-FLOW, CLOUDTRAIL`

### Official calibration resources

- **Direct public mapping:** `SAA-SAMPLE` Question 1 calibrates the private-subnet route to a NAT gateway for internet access.
- `SAA-PREP` and `SAP-PREP` are appropriate for endpoint, routing, and network-cost scenarios.
- **No official public sample question maps directly** to gateway-endpoint cost avoidance, interface-endpoint break-even analysis, cross-AZ transfer pricing, centralized Transit Gateway inspection cost, or Regional NAT Gateway.

---

## Cross-chapter completion check

- Chapters audited: 61–71.
- Replacement coverage: exactly 110 intents, exactly 10 per chapter.
- Required themes are explicit: SLO, RTO, RPO, DR strategy, failover/failback, observability, performance, scaling, cost, commitments, evidence, and game days.
- Every intent includes one correct principle, exactly three plausible distractor concepts, SAA-C03 or SAP-C02 task mapping, and official AWS source keys.
- Official calibration is listed separately for every chapter, and each chapter states when no official public sample maps directly.
- No live exam recollections, exam dumps, or full official sample questions are included.

SUPERSET_WORKER_DONE task P06-audit
