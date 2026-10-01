---
title: "P08 Audit — Chapters 79–90: SAP Enterprise Architecture"
task: P08-audit-v2
chapters:
  - 79
  - 80
  - 81
  - 82
  - 83
  - 84
  - 85
  - 86
  - 87
  - 88
  - 89
  - 90
intents_per_chapter: 10
total_intents: 120
as_of: 2026-10-01
exam_dumps_used: false
---

# P08 Audit — Chapters 79–90: SAP Enterprise Architecture

## Scope and version boundary

- This is an audit and replacement coverage specification for the current five-question sets in Chapters 79–90. It does not reproduce, paraphrase, or infer live exam questions.
- Every chapter below has exactly ten original knowledge-coverage intents, numbered 1–10 within that chapter. Each intent identifies one unique hard constraint/correct principle, exactly three plausible distractor concepts, a SAA-C03 or SAP-C02 task mapping, and official AWS source keys.
- The project task IDs remain the current `SAP-1.1` through `SAP-4.4` mappings in `aws_architect_model.py`. As of 2026-10-01, AWS says SAP-C03 registration opens on 2026-10-27 and the last SAP-C02 exam date is 2026-11-17. Re-map this audit when the project adopts SAP-C03; do not silently reuse SAP-C02 task IDs.
- Product documentation, not an exam guide or practice resource, is authoritative for service behavior. Community notes and exam dumps are excluded.

## Cross-chapter defects in the current questions

- All twelve chapters reuse the same five shapes: broad service selection, a bundled settings list, a “request/data path” mechanism, a least-operations restatement, and a generic two-answer governance item.
- Questions 1 and 5 usually repeat the chapter thesis; Questions 2 and 4 usually repeat the primary component and the same setting list. This produces only two or three effective decisions per chapter.
- “AWS automatically understands business requirements,” “deploy everything,” “wait for failure and handle it manually,” and “grant organization-wide AdministratorAccess” recur as obviously bad distractors. They do not discriminate between plausible architectures.
- Control-plane services such as Organizations, Migration Hub, Cost Explorer, and the Well-Architected Tool are repeatedly described as if they were in an application request/data path.
- The fifth question applies the same canary, rollback, second-Region, and owner boilerplate to unrelated domains. It does not test chapter-specific ownership, evidence, rollout, or recovery mechanics.
- Several service names and assumptions are version-sensitive. AWS Application Migration Service was renamed AWS Transform MGN in June 2026. AWS Migration Hub and AWS Application Discovery Service have not been open to new customers since 2025-11-07, with AWS Transform identified as the current alternative. The AWS .NET modernization tool family that includes App2Container is also unavailable to new customers, while AWS Transform now provides source-code containerization workflows. Data Exports CUR 2.0 is the current export model; DynamoDB global tables can use MREC or MRSC; and Snowball Edge is unavailable to new customers.

## Official source-key registry

### Exam tasks and current exam status

- `SAP-GUIDE` — [SAP-C02 exam guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)
- `SAP-D1` — [SAP-C02 Domain 1](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain1.html)
- `SAP-D2` — [SAP-C02 Domain 2](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain2.html)
- `SAP-D3` — [SAP-C02 Domain 3](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)
- `SAP-D4` — [SAP-C02 Domain 4](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain4.html)
- `SAP-CERT` — [AWS Certified Solutions Architect – Professional](https://aws.amazon.com/certification/certified-solutions-architect-professional/)

### Organizations, Control Tower, networking, security, and identity

- `ORG-SCP` — [Service control policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)
- `ORG-INHERIT` — [Policy inheritance](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_inheritance_auth.html)
- `ORG-MGMT` — [Management account best practices](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices_mgmt-acct.html)
- `CT-OVERVIEW` — [What is AWS Control Tower?](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html)
- `CT-CONTROLS` — [Control behavior and implementation](https://docs.aws.amazon.com/controltower/latest/controlreference/control-behavior.html)
- `CT-AF` — [Account Factory](https://docs.aws.amazon.com/controltower/latest/userguide/account-factory.html)
- `CT-AFT` — [Account Factory for Terraform overview](https://docs.aws.amazon.com/controltower/latest/userguide/aft-overview.html)
- `CT-DRIFT` — [Types of governance drift](https://docs.aws.amazon.com/controltower/latest/userguide/drift.html)
- `TGW-RT` — [Transit gateway route tables](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html)
- `TGW-APPLIANCE` — [Appliance mode](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpc-attachments.html#appliance-mode)
- `TGW-SHARE` — [Work with shared transit gateways](https://docs.aws.amazon.com/vpc/latest/tgw/working-with-transit-gateways.html)
- `NFW-ARCH` — [AWS Network Firewall deployment models](https://docs.aws.amazon.com/network-firewall/latest/developerguide/architectures.html)
- `NFW-ROUTE` — [AWS Network Firewall route tables](https://docs.aws.amazon.com/network-firewall/latest/developerguide/route-tables.html)
- `GWLB` — [Gateway Load Balancer overview](https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/introduction.html)
- `DX-RESILIENCY` — [Resilience in AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/disaster-recovery-resiliency.html)
- `PRIVATELINK` — [AWS PrivateLink concepts](https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html)
- `R53-RESOLVER` — [What is Route 53 VPC Resolver?](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html)
- `R53-HYBRID` — [Resolving DNS queries between VPCs and on-premises networks](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-overview-DSN-queries-to-vpc.html)
- `R53-DNSFW` — [How Route 53 Resolver DNS Firewall works](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-dns-firewall-overview.html)
- `SRA-LOG` — [Log Archive account](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/log-archive.html)
- `CT-ORGTRAIL` — [Create an organization trail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html)
- `CT-VALIDATION` — [CloudTrail log file integrity validation](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-log-file-validation-intro.html)
- `CT-LAKE` — [CloudTrail Lake event data stores](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/query-event-data-store.html)
- `CONFIG-AGG` — [AWS Config aggregators](https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html)
- `GD-MULTI` — [Managing GuardDuty accounts](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_accounts.html)
- `SH-CENTRAL` — [Security Hub central configuration](https://docs.aws.amazon.com/securityhub/latest/userguide/central-configuration-intro.html)
- `S3-LOCK` — [S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)
- `IDC-PSET` — [IAM Identity Center permission sets](https://docs.aws.amazon.com/singlesignon/latest/userguide/permissionsetsconcept.html)
- `IDC-ABAC` — [Attribute-based access control in IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/abac.html)
- `IDC-DELEGATE` — [Delegated administration for IAM Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/delegated-admin.html)
- `IAM-EVAL` — [IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)
- `IAM-CROSS` — [Cross-account access with roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/tutorial_cross-account-with-roles.html)
- `STS-ASSUME` — [AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)
- `IAM-EXTID` — [Cross-service and cross-account confused deputy prevention](https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html)
- `IAM-SESSION-TAGS` — [Passing session tags in AWS STS](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_session-tags.html)
- `IAM-PROVIDERS` — [Identity providers and federation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers.html)

### Global data, backup, cost, migration, modernization, and improvement

- `R53-ROUTING` — [Route 53 routing policies](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy.html)
- `R53-FAILOVER` — [Route 53 active-passive failover](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover-types.html)
- `GA` — [What is AWS Global Accelerator?](https://docs.aws.amazon.com/global-accelerator/latest/dg/what-is-global-accelerator.html)
- `AURORA-GLOBAL` — [Amazon Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)
- `AURORA-DR` — [Planned and unplanned Aurora global database failover](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html)
- `DDB-GLOBAL` — [DynamoDB global tables](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html)
- `DDB-CONSISTENCY` — [How DynamoDB global tables and their consistency modes work](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/create-gt-mrsc.html)
- `DR` — [Disaster recovery of workloads on AWS](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)
- `ORG-BACKUP` — [Backup policies in AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_backup.html)
- `BACKUP-XACCT` — [Cross-account backup copies](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)
- `VAULT-LOCK` — [AWS Backup Vault Lock](https://docs.aws.amazon.com/aws-backup/latest/devguide/vault-lock.html)
- `BACKUP-RESTORE` — [AWS Backup restore testing](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)
- `BACKUP-VALIDATE` — [Restore testing validation](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html)
- `BACKUP-AUDIT` — [AWS Backup Audit Manager controls](https://docs.aws.amazon.com/aws-backup/latest/devguide/choosing-controls.html)
- `BACKUP-AIRGAP` — [Logically air-gapped vaults](https://docs.aws.amazon.com/aws-backup/latest/devguide/logicallyairgappedvault.html)
- `BACKUP-PITR` — [Continuous backup and point-in-time recovery](https://docs.aws.amazon.com/aws-backup/latest/devguide/point-in-time-recovery.html)
- `BACKUP-LIFECYCLE` — [Backup lifecycle and cold storage](https://docs.aws.amazon.com/aws-backup/latest/devguide/editing-a-backup.html)
- `DATA-EXPORTS` — [Migrate from legacy CUR to Data Exports CUR 2.0](https://docs.aws.amazon.com/cur/latest/userguide/dataexports-migrate.html)
- `COST-TAGS` — [Activate user-defined cost allocation tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html)
- `ACCOUNT-TAGS` — [Account tags for cost allocation](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/account-tags-cost-allocation.html)
- `COST-EXPLORER` — [AWS Billing and Cost Management](https://docs.aws.amazon.com/cost-management/latest/userguide/what-is-costmanagement.html)
- `COST-BUDGETS` — [Managing costs with AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
- `COST-ANOMALY` — [Cost Anomaly Detection](https://docs.aws.amazon.com/cost-management/latest/userguide/manage-ad.html)
- `COST-SHARING` — [RI and Savings Plans discount sharing](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ri-turn-off.html)
- `COST-WA` — [AWS Well-Architected Cost Optimization Pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)
- `MIG-PHASES` — [Phases of a large migration](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/phases.html)
- `MIG-PLAYBOOK` — [Migration playbook for AWS large migrations](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-migration-playbook/)
- `MIG-HUB-CHANGE` — [AWS Migration Hub availability for new customers](https://docs.aws.amazon.com/migrationhub/latest/ug/whatishub.html)
- `SERVICE-AVAILABILITY` — [AWS services and capabilities moving to maintenance](https://aws.amazon.com/about-aws/whats-new/2025/10/aws-service-availability/)
- `ADS-CHANGE` — [AWS Application Discovery Service availability change](https://docs.aws.amazon.com/application-discovery/latest/userguide/application-discovery-service-availability-change.html)
- `ADS` — [Application Discovery Service Agentless Collector dashboard](https://docs.aws.amazon.com/application-discovery/latest/userguide/agentless-collector-dashboard.html)
- `TRANSFORM-ASSESS` — [AWS Transform migration assessments](https://docs.aws.amazon.com/transform/latest/userguide/transform-app-assessments.html)
- `TRANSFORM-WAVES` — [Build a migration plan in AWS Transform](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-review-groupings-and-waves.html)
- `DATASYNC-NET` — [AWS DataSync network requirements](https://docs.aws.amazon.com/datasync/latest/userguide/datasync-network.html)
- `DATASYNC-VERIFY` — [Verify DataSync agent connections](https://docs.aws.amazon.com/datasync/latest/userguide/test-agent-connections.html)
- `STORAGE-GATEWAY` — [Volume Gateway concepts](https://docs.aws.amazon.com/storagegateway/latest/vgw/StorageGatewayConcepts.html)
- `SNOW-CHANGE` — [Snowball Edge availability change](https://docs.aws.amazon.com/snowball/latest/developer-guide/snowball-edge-availability-change.html)
- `MGN` — [What is AWS Transform MGN?](https://docs.aws.amazon.com/mgn/latest/ug/)
- `MGN-FAQ` — [Why AWS Application Migration Service was renamed](https://docs.aws.amazon.com/mgn/latest/ug/General-Questions-FAQ.html)
- `MGN-CUTOVER` — [AWS Transform MGN migration lifecycle](https://docs.aws.amazon.com/mgn/latest/ug/lifecycle.html)
- `DMS` — [AWS Database Migration Service](https://docs.aws.amazon.com/dms/latest/userguide/Welcome.html)
- `DMS-VALIDATE` — [AWS DMS data validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html)
- `DMS-SCHEMA` — [DMS Schema Conversion](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_SchemaConversion.html)
- `DMS-HOMOGENEOUS` — [DMS homogeneous data migrations](https://docs.aws.amazon.com/dms/latest/userguide/data-migrations.html)
- `SCT-ASSESS` — [AWS SCT assessment report](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_AssessmentReport.html)
- `MIG-7RS` — [AWS cloud migration strategies: the 7 Rs](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html)
- `CONTAINERS-GUIDE` — [Choosing an AWS container service](https://docs.aws.amazon.com/decision-guides/latest/containers-on-aws-how-to-choose/guide.html)
- `APP2CONTAINER-CHANGE` — [AWS App2Container availability for new customers](https://docs.aws.amazon.com/app2container/latest/UserGuide/what-is-a2c.html)
- `TRANSFORM-CONTAINERS` — [AWS Transform source-code containerization](https://docs.aws.amazon.com/transform/latest/userguide/transform-containers.html)
- `DECOMPOSE` — [Decomposing monoliths into microservices](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/welcome.html)
- `STRANGLER` — [Strangler fig pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/strangler-fig.html)
- `OUTBOX` — [Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
- `SAGA` — [Saga orchestration pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)
- `MICROSERVICE-DATA` — [Distributed data management](https://docs.aws.amazon.com/whitepapers/latest/microservices-on-aws/distributed-data-management.html)
- `ECS-BG` — [Amazon ECS blue/green deployments](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-type-blue-green.html)
- `LAMBDA-BP` — [AWS Lambda best practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- `WA-MILESTONE` — [Well-Architected Tool milestones](https://docs.aws.amazon.com/wellarchitected/latest/userguide/milestones.html)
- `WA-IMPROVE` — [Implement and track Well-Architected improvements](https://docs.aws.amazon.com/wellarchitected/latest/userguide/implement-and-track-improvements.html)
- `COMPUTE-OPT` — [What is AWS Compute Optimizer?](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is.html)
- `COMPUTE-METRICS` — [Metrics analyzed by Compute Optimizer](https://docs.aws.amazon.com/compute-optimizer/latest/ug/metrics.html)
- `CONFIG-PACK` — [AWS Config conformance packs](https://docs.aws.amazon.com/config/latest/developerguide/conformance-packs.html)
- `OE-WA` — [AWS Well-Architected Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html)

## Separate mapping: official public AWS sample and practice resources only

This mapping is for style and topic calibration, not product-fact authority. It identifies only public resource names, item numbers, and high-level topics; it does not reproduce stems, choices, or explanations. No third-party bank, recalled live item, or exam dump is mapped.

| Resource key | Official public resource | Public item-number status |
|---|---|---|
| `AWS-SAA-SAMPLE` | [SAA-C03 official sample-question PDF](https://d1.awsstatic.com/training-and-certification/docs-sa-assoc/AWS-Certified-Solutions-Architect-Associate_Sample-Questions.pdf) | Ten stable public sample item numbers are available for topic-only mapping. |
| `AWS-SAP-SAMPLE` | [SAP-C02 official sample-question PDF](https://d1.awsstatic.com/training-and-certification/docs-sa-pro/AWS-Certified-Solutions-Architect-Professional_Sample-Questions.pdf) | Ten stable public sample item numbers are available for topic-only mapping. |
| `AWS-CERT-PREP` | [AWS Certification exam preparation resources](https://aws.amazon.com/certification/certification-prep/) | Official Practice Question Sets and Official Practice Exams are described publicly, but their item-level content and stable question numbers are not exposed on the public page. |

| Chapter | Public official sample item/topic mapping | Direct-map statement |
|---|---|---|
| 79 | `AWS-SAP-SAMPLE` Q1: account-level spend alerts while business groups retain account control. Q2: organization-wide deployment of a third-party read role. | Both are adjacent to multi-account governance. **No official public sample maps directly** to Control Tower landing zones, account vending, OU design, SCP semantics, or drift repair. |
| 80 | `AWS-SAA-SAMPLE` Q1: private-subnet internet egress through NAT and routing. | This is adjacent to centralized egress only. **No official public sample maps directly** to TGW segmentation, inspection symmetry, Direct Connect resilience, overlapping CIDR, or hybrid DNS. |
| 81 | `AWS-SAP-SAMPLE` Q2: cross-account access for a centralized monitoring provider. | This is adjacent to centralized security-account access. **No official public sample maps directly** to organization trails, immutable log archives, Config aggregation, delegated GuardDuty/Security Hub administration, or evidence validation. |
| 82 | `AWS-SAP-SAMPLE` Q2: third-party cross-account role deployment. Q6: cross-account role access with one credential set and environment separation. | Both map directly to Intent 3. Q2 is only adjacent to Intent 4 because it does not directly test external ID. No SAA public sample directly tests Identity Center permission sets, ABAC, source identity, or session-policy intersection. |
| 83 | `AWS-SAP-SAMPLE` Q9: two-Region application deployment with regional artifacts, Route 53 routing, and Aurora global data. `AWS-SAA-SAMPLE` Q3: private-IP failover by moving an ENI. | SAP Q9 maps directly to global entry-point and Aurora design in Intents 1–4. SAA Q3 is only an adjacent single-Region failover mechanism. |
| 84 | `AWS-SAA-SAMPLE` Q5: customer-controlled encryption keys for S3 data. | Key custody is adjacent, but **no official public sample maps directly** to organization backup policies, cross-account recovery copies, Vault Lock, logically air-gapped vaults, restore testing, or Backup Audit Manager. |
| 85 | `AWS-SAP-SAMPLE` Q1: billing alerts for autonomous accounts. `AWS-SAA-SAMPLE` Q6: cost-effective temporary compute capacity. | These calibrate cost constraints and alerting, but **no official public sample maps directly** to allocation-tag activation, account tags, CUR 2.0, shared-cost allocation, commitment sharing, or chargeback. |
| 86 | No numbered SAA-C03 or SAP-C02 public sample covers migration inventory, dependency mapping, portfolio assessment, or wave planning. | **No official public sample maps directly.** |
| 87 | No numbered SAA-C03 or SAP-C02 public sample covers AWS Transform MGN, DMS full-load/CDC, DMS Schema Conversion, SCT action items, or migration cutover. | **No official public sample maps directly.** |
| 88 | `AWS-SAP-SAMPLE` Q10: managed-service modernization with lower operational overhead. | This is adjacent to modernization selection. **No official public sample maps directly** to choosing and evidencing each of the 7 Rs. |
| 89 | `AWS-SAP-SAMPLE` Q7: replacing sparse EC2 processing with event-driven compute for cost. Q10: managed-service modernization. `AWS-SAA-SAMPLE` Q7: queue-based decoupling under burst load. | These are adjacent to serverless and decoupling. **No official public sample maps directly** to monolith decomposition, strangler routing, database ownership, outbox/saga, or modernization operating-model boundaries. |
| 90 | `AWS-SAP-SAMPLE` Q7 and Q10: cost-aware redesign and managed modernization. `AWS-SAA-SAMPLE` Q6, Q9, and Q10: cost-effective capacity, safe scaling behavior, and database read optimization. | These calibrate improvement decisions. **No official public sample maps directly** to a falsifiable hypothesis, Well-Architected improvement ownership, reversible multi-account rollout, realized-savings evidence, or a continuous review cadence. |

The `AWS-CERT-PREP` page confirms official question-set and practice-exam offerings, but it does not expose stable item numbers or item topics. Therefore **no direct item-level mapping is asserted** for those account-gated resources.

---

## Chapter 79 — Landing Zone and Multi-account Strategy

### Current-question audit

- Questions 1 and 5 repeat the same OU/account/Control Tower recommendation; Question 4 repeats Organizations settings, so five questions cover only about two independent decisions.
- Question 1 treats the ABAC/account-boundary caveat as an alternative even though it can coexist with the selected landing-zone design.
- Question 2 bundles SCPs, resource control policies, tag policies, backup policies, delegated administration, trusted access, and billing as if they were equivalent controls. They have different evaluation and inheritance semantics.
- Question 3 incorrectly calls Organizations part of a request/data path. It is a governance control plane, and SCPs constrain available permissions rather than granting them.
- Question 4 selects Organizations alone for a requirement that explicitly includes account vending, baselines, and controls; this under-specifies Control Tower/Account Factory.
- Missing density: management-account isolation, OU stability, policy inheritance, exceptions, enrollment/drift, account lifecycle, delegated administrators, quotas, and per-account cost ownership.

### Exactly ten knowledge-coverage intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | SAA-C03 / SAP-C02 task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Choose account boundaries for business units, environments, and regulated workloads. | Use accounts as strong security, quota, billing, and operational blast-radius boundaries; use OUs to group accounts for policy, not as network segments. | One shared account with tags provides equal isolation; create one OU per application resource; use VPCs alone to isolate billing and service quotas. | `SAP-1.4` | `ORG-INHERIT`, `CT-OVERVIEW` |
| 2 | Design an OU hierarchy that remains stable as teams reorganize. | Base top-level OUs on durable governance differences such as production, security, infrastructure, sandbox, and policy needs; represent frequently changing ownership with account metadata and tags. | Mirror the reporting hierarchy exactly; move accounts daily to drive automation; attach every policy directly to individual accounts. | `SAP-1.4` | `ORG-INHERIT`, `CT-OVERVIEW` |
| 3 | Explain what an SCP can and cannot do. | An SCP defines the maximum permissions available to identities in member accounts; it does not grant permissions, and effective access still requires identity/resource policies without an applicable explicit deny. | SCPs grant AdministratorAccess to selected roles; SCPs replace every resource policy; attaching an allow SCP alone authorizes an API call. | `SAP-1.2` | `ORG-SCP`, `IAM-EVAL` |
| 4 | Protect the management account and delegate service administration. | Keep workloads and routine administration out of the management account; use supported delegated administrators and tightly controlled break-glass access. | Run shared production workloads in the management account for convenience; create daily management-account access keys; make every platform engineer the root user. | `SAP-1.4`, `SAP-3.2` | `ORG-MGMT`, `IDC-DELEGATE` |
| 5 | Select Control Tower controls without treating all control types as identical. | Match preventive, detective, and proactive controls to when enforcement must occur, understand the underlying implementation, and preserve an exception/remediation process. | A detective control blocks every create request; a preventive control proves historical compliance; enabling a control automatically remediates every existing resource. | `SAP-1.2`, `SAP-1.4` | `CT-CONTROLS`, `CT-OVERVIEW` |
| 6 | Create a repeatable account-vending workflow. | Use Account Factory or AFT to collect owner, email, OU, network, identity, logging, and cost metadata, apply versioned customizations, and emit lifecycle events. | Let teams create unmanaged accounts and enroll them later; use a shared account plus project tags; encode owner only in an account name. | `SAP-1.4`, `SAP-3.1` | `CT-AF`, `CT-AFT` |
| 7 | Enroll an existing organization into Control Tower safely. | Assess prerequisites and existing resources, enroll accounts/OUs in waves, test controls and identity access, and remediate drift without assuming a greenfield landing zone. | Recreate all accounts in one cutover; enroll the entire organization without dependency testing; delete existing CloudTrail and Config resources first. | `SAP-2.1`, `SAP-3.1` | `CT-OVERVIEW`, `CT-DRIFT` |
| 8 | Diagnose landing-zone drift. | Distinguish resource, control, landing-zone, and account drift; identify the out-of-band change, repair through supported workflows, and remove the bypass path. | Move the account to a different OU and ignore the cause; disable controls to clear the dashboard; treat every drift event as an application outage. | `SAP-3.1`, `SAP-3.2` | `CT-DRIFT`, `CT-CONTROLS` |
| 9 | Roll out a new organization guardrail with bounded blast radius. | Evaluate effective policies on representative accounts, pilot in a test OU, preserve incident-response paths, monitor denied calls, and expand in waves with a documented rollback. | Attach a deny at the root immediately; test only policy syntax; exempt the security team by granting more identity permissions against the deny. | `SAP-1.2`, `SAP-2.1` | `ORG-SCP`, `ORG-INHERIT` |
| 10 | Assign ownership and cost accountability to every account. | Require business owner, technical owner, data class, lifecycle state, budget, and escalation metadata at provisioning; periodically close, quarantine, or transfer orphaned accounts. | Rely on the payer account to own every workload; use account email as the only owner record; retain unused accounts indefinitely because consolidated billing is centralized. | `SAP-1.5`, `SAP-3.1` | `CT-AF`, `ACCOUNT-TAGS`, `COST-BUDGETS` |

---

## Chapter 80 — Centralized Network and Inspection VPC

### Current-question audit

- Questions 1 and 5 repeat the same TGW/inspection-VPC architecture, while Questions 2 and 4 repeat the TGW settings list.
- Question 4 claims that choosing Transit Gateway alone satisfies shared connectivity, centralized egress, and packet inspection. TGW routes traffic but does not inspect it.
- Question 2 lists multicast beside association, propagation, appliance mode, and ECMP without a scenario that needs multicast; the learner can select the longest bundle without understanding any route.
- Question 3 contains a correct Network Firewall mechanism as a distractor, but never tests the complete forward and return path through a stateful appliance.
- “Least operational overhead” is ambiguous because centralized inspection reduces policy duplication but increases shared-path dependency, inter-AZ processing, routing complexity, and ownership.
- Missing density: TGW route-table segmentation, blackholes, RAM ownership, AZ-affine firewall endpoints, appliance mode, hybrid routing, overlapping CIDR, inspection bypass, route rollout, and per-hop cost.
- Hybrid DNS is absent: no current item tests Route 53 Resolver inbound/outbound endpoints, conditional forwarding rules, endpoint-AZ resilience, split-horizon namespace ownership, or DNS Firewall’s separate role.

### Exactly ten knowledge-coverage intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | SAA-C03 / SAP-C02 task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Choose TGW, peering, or PrivateLink for multi-account connectivity. | Use TGW for transitive hub routing and route-domain segmentation, peering for limited non-transitive full-VPC connectivity, and PrivateLink when consumers should reach only a published service. | Use peering as a transitive enterprise hub; use PrivateLink to exchange arbitrary routes; use TGW whenever only one private API must be exposed. | `SAP-1.1` | `TGW-RT`, `PRIVATELINK` |
| 2 | Segment production, development, partner, and shared-services attachments. | Associate each attachment with one TGW route table and deliberately propagate or install only the routes each segment may reach; route-table separation is the segmentation mechanism. | Associate one attachment with multiple route tables simultaneously; assume propagation is identical to association; rely on security groups to hide unintended TGW routes. | `SAP-1.1`, `SAP-1.2` | `TGW-RT` |
| 3 | Force east-west traffic through a stateful inspection VPC. | Build explicit spoke-to-inspection and inspection-to-destination routes, enable appliance mode where needed for flow symmetry, and verify the reverse path uses the same stateful appliance path. | Add only a default route in the source VPC; use asymmetric return routing because Network Firewall is stateless; enable appliance mode on every attachment without understanding the topology. | `SAP-1.1`, `SAP-1.2` | `TGW-APPLIANCE`, `NFW-ROUTE` |
| 4 | Deploy Network Firewall endpoints across failure domains. | Create firewall endpoints in the required AZs and route each AZ through its appropriate endpoint; design for endpoint/AZ failure and avoid accidental cross-AZ hairpins. | Send every AZ through one firewall endpoint; place a firewall endpoint in a public subnet and assume it is an internet gateway; route only the forward path through inspection. | `SAP-1.3`, `SAP-2.4` | `NFW-ARCH`, `NFW-ROUTE` |
| 5 | Decide between AWS Network Firewall and third-party appliances behind GWLB. | Use Network Firewall for AWS-managed stateful/stateless inspection; use GWLB when the requirement depends on a compatible virtual appliance ecosystem, while retaining appliance scaling, health, and routing ownership. | GWLB itself contains firewall policy; Network Firewall transparently runs arbitrary vendor images; an ALB can replace GENEVE-based transparent appliances. | `SAP-1.2`, `SAP-2.5` | `NFW-ARCH`, `GWLB` |
| 6 | Share a central TGW across accounts with clear ownership. | The network account owns the TGW and route policy; participant accounts create or accept attachments as allowed, while AWS RAM sharing does not automatically authorize end-to-end traffic. | RAM sharing propagates every VPC route automatically; participant accounts can always edit owner route tables; joining an organization creates TGW connectivity. | `SAP-1.1`, `SAP-1.4` | `TGW-SHARE`, `TGW-RT` |
| 7 | Integrate hybrid connectivity without a single circuit failure domain. | Use redundant Direct Connect connections in appropriate locations and a tested VPN or other backup path as required; align BGP advertisements, TGW/DX gateway routes, MTU, and failover timers. | One Direct Connect virtual interface is inherently redundant; a VPN backup needs no route-preference testing; BGP reachability proves DNS and application dependencies work. | `SAP-1.1`, `SAP-1.3` | `DX-RESILIENCY`, `TGW-RT` |
| 8 | Handle acquired networks with overlapping CIDR. | Avoid full routed connectivity until addresses are remediated; expose narrow services through PrivateLink or proxies and plan staged renumbering for workloads that need broad bidirectional routing. | TGW longest-prefix matching distinguishes identical CIDRs by account; add more peering connections; use security groups to translate overlapping addresses. | `SAP-1.1`, `SAP-4.2` | `PRIVATELINK`, `TGW-RT` |
| 9 | Design resilient hybrid DNS across accounts and on-premises networks. | Use Route 53 Resolver inbound endpoints for on-premises queries into AWS and outbound endpoints plus conditional forwarding rules for AWS queries to external DNS; deploy endpoint IPs across AZs, centralize/share rules deliberately, and keep DNS Firewall policy distinct from name resolution. | Associate a private hosted zone with an on-premises network directly; use an inbound endpoint for VPC-to-on-premises forwarding; assume DNS Firewall creates forwarding paths and authoritative records. | `SAP-1.1`, `SAP-1.3` | `R53-RESOLVER`, `R53-HYBRID`, `R53-DNSFW` |
| 10 | Roll out central egress while controlling cost and blast radius. | Migrate spokes in waves, measure per-AZ/TGW/NAT/firewall bytes and latency, preserve a tested fallback route, and make the central network team accountable for capacity and incident response. | Move all default routes at once; judge success only by firewall endpoint health; ignore cross-AZ and per-hop processing because centralized services have one flat fee. | `SAP-2.1`, `SAP-2.6` | `NFW-ARCH`, `TGW-RT`, `COST-WA` |

---

## Chapter 81 — Centralized Logging and Security Accounts

### Current-question audit

- Questions 1 and 5 repeat the same log-archive/security-tooling design; Questions 2 and 4 repeat CloudTrail settings.
- Question 1 makes “local operational views plus authoritative cross-account immutable copies” an alternative even though it is compatible with, and often part of, the selected architecture.
- The current wording implies that cross-account storage is automatically immutable. Independence requires destination ownership, restrictive policies, retention controls, key access, and tested retrieval.
- Question 3 reduces CloudTrail to event history versus trails and calls it a request/data-path mechanism; it does not distinguish evidence collection, configuration state, threat detection, and findings aggregation.
- CloudTrail organization delivery, Config aggregation, GuardDuty delegated administration, and Security Hub central configuration have different enablement and Region behavior, but the questions treat them as one integration switch.
- Missing density: data-event scope/cost, log integrity, Object Lock, delegated security administration, finding suppression/workflow, incident-response access, query retention, service coverage, and detection rollout.

### Exactly ten knowledge-coverage intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | SAA-C03 / SAP-C02 task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Place security evidence outside the workload account’s control. | Deliver organization audit logs to a dedicated log-archive account with destination-owned S3/KMS policies and no workload-admin delete path; use a separate security-tooling account for delegated operations. | Keep the only trail in each workload account; let source-account admins manage destination retention; run all security tooling in the management account. | `SAP-1.2`, `SAP-1.4` | `SRA-LOG`, `CT-ORGTRAIL` |
| 2 | Configure an organization trail with deliberate event scope. | Use an organization, multi-Region trail for management events and selectively enable high-value data events or Insights based on threat model, volume, and cost; verify delivery in member accounts and the archive. | Assume event history is a permanent organization archive; enable every data event without cost analysis; create unrelated member trails and assume they form one organization trail. | `SAP-1.2`, `SAP-3.2` | `CT-ORGTRAIL`, `CT-LAKE` |
| 3 | Prove that delivered CloudTrail files were not modified or deleted unnoticed. | Enable log file integrity validation, protect digest and log objects with least privilege and retention controls, and independently monitor delivery gaps; validation detects modification but does not prevent deletion by itself. | KMS encryption proves no object was deleted; integrity validation makes a bucket immutable; CloudTrail event history validates arbitrary application logs. | `SAP-2.3`, `SAP-3.2` | `CT-VALIDATION`, `S3-LOCK` |
| 4 | Choose CloudTrail Lake versus S3-based analytics. | Use CloudTrail Lake for managed event data stores and SQL querying with chosen retention; use S3 plus analytics tooling when an organization needs a broader custom security data lake or independent archive workflow. | Lake automatically ingests every application log; an S3 trail offers no query path; event data store retention is the same as S3 Object Lock. | `SAP-2.5`, `SAP-2.6` | `CT-LAKE`, `SRA-LOG` |
| 5 | Aggregate configuration state without confusing it with API audit. | Use AWS Config recorders/rules and aggregators for resource configuration history and compliance views; use CloudTrail for caller/API evidence. An aggregator does not grant remediation rights in source accounts. | Config records every application request body; CloudTrail determines resource compliance; aggregation copies ownership of resources to the security account. | `SAP-1.2`, `SAP-3.1` | `CONFIG-AGG`, `CT-ORGTRAIL` |
| 6 | Delegate GuardDuty administration across an organization. | Designate the supported delegated administrator, auto-enable required protection plans/Regions for member accounts, and route findings into an owned triage and response workflow. | Enabling GuardDuty in the management account protects all members automatically; findings are preventive controls that block attacks; one Region’s detector covers every Region. | `SAP-1.2`, `SAP-3.2` | `GD-MULTI` |
| 7 | Centralize Security Hub policy while preserving local response context. | Use central configuration for standards and controls, aggregate findings to the delegated administrator, and define ownership, suppression, automation, and exception workflows rather than treating score alone as risk. | A high score proves all workloads are secure; disabling a noisy control is the only suppression mechanism; Security Hub replaces GuardDuty and Config collection. | `SAP-1.2`, `SAP-3.2` | `SH-CENTRAL`, `GD-MULTI`, `CONFIG-AGG` |
| 8 | Design break-glass access that survives a compromised workload account. | Keep incident-response roles and identity dependencies outside the compromised account where possible, pre-authorize evidence access, log use, and test that SCPs and KMS policies do not block responders. | Grant permanent administrator to all SOC users; store break-glass credentials in the workload; attach an SCP deny that also blocks the recovery role. | `SAP-2.3`, `SAP-3.2` | `IAM-CROSS`, `IAM-EVAL`, `SRA-LOG` |
| 9 | Diagnose missing organization evidence. | Check service enablement and Region scope, organization/delegated-admin state, trail or recorder status, destination bucket/KMS policies, delivery errors, and recent account enrollment before assuming no activity occurred. | Treat an empty central dashboard as proof of no events; recreate all member accounts; widen the archive bucket to public write. | `SAP-3.1`, `SAP-3.4` | `CT-ORGTRAIL`, `CONFIG-AGG`, `GD-MULTI` |
| 10 | Roll out new detection and retention policy safely. | Start in audit/observation where supported, estimate event volume and cost, pilot with representative accounts, tune false positives, version exceptions, and expand while preserving immutable raw evidence. | Enable every control and data event at the root in one change; delete raw events after generating findings; let each workload suppress central findings without review. | `SAP-2.1`, `SAP-3.2` | `SH-CENTRAL`, `CT-LAKE`, `S3-LOCK` |

---

## Chapter 82 — Enterprise Identity and Cross-account Authorization

### Current-question audit

- Question 1 bundles workforce federation, workload roles, third-party access, external IDs, and least privilege into one long answer, so recognition of the longest comprehensive option can replace reasoning.
- The ABAC option is not an alternative to Identity Center; it can be part of the same design, making Question 1’s contrast ambiguous.
- Questions 2 and 4 repeat the same Identity Center configuration list, while Question 5 repeats Question 1 plus generic rollout language.
- Question 3 again uses request/data-path wording for a workforce access control plane.
- The set does not test trust policy versus permissions policy, session-policy intersection, source identity, transitive session tags, confused deputy prevention, or emergency-access dependencies.
- “External ID and minimum trust” is too loose: external ID is a condition for a specific confused-deputy scenario, not a secret or a replacement for a correctly scoped principal and permissions.

### Exactly ten knowledge-coverage intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | SAA-C03 / SAP-C02 task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Separate workforce, workload, and customer identity lifecycles. | Use IAM Identity Center/federation for workforce access, IAM roles and workload federation for machines, and an application identity service for end customers; avoid long-lived IAM users for routine access. | Use Identity Center users as application customers; embed one IAM access key in all automation; create a local IAM user for every employee in every account. | `SAP-1.2`, `SAP-1.4` | `IDC-PSET`, `IAM-PROVIDERS` |
| 2 | Map workforce groups to permission sets across accounts. | Define job-function permission sets, assign identity-provider groups to accounts, issue temporary sessions, and manage exceptions through reviewed group/permission-set changes. | Copy IAM users and passwords to member accounts; create one permission set per person; use account root credentials for federated administration. | `SAP-1.4`, `SAP-2.3` | `IDC-PSET` |
| 3 | Evaluate a cross-account AssumeRole request. | The caller needs permission to call `sts:AssumeRole`, the target role trust policy must trust the caller under its conditions, and the resulting session is constrained by role and applicable session/organization policies. | A trust policy alone grants access to every target resource; an identity policy in the source account can override a target explicit deny; joining Organizations creates mutual trust. | `SAP-1.2`, `SAP-2.3` | `STS-ASSUME`, `IAM-CROSS`, `IAM-EVAL` |
| 4 | Prevent the confused-deputy problem for a third-party SaaS provider. | Trust the provider’s specific principal and require a customer-specific external ID supplied by the provider, while limiting role permissions and monitoring assumptions; do not treat the external ID as authentication by itself. | Trust the provider account root without conditions; let the customer choose a reusable public external ID; give the provider a permanent access key in the customer account. | `SAP-2.3`, `SAP-3.2` | `IAM-EXTID`, `STS-ASSUME` |
| 5 | Use ABAC without allowing privilege-bearing tags to be self-issued. | Map trusted identity attributes to session tags, restrict who can set or modify authorization tags, enforce tag-key/value conditions, and retain guardrails for actions that should never be attribute-driven. | Let users set their own `department=security` tag; assume resource tags are an immutable security boundary; replace every explicit sensitive-resource policy with a wildcard ABAC statement. | `SAP-1.2`, `SAP-3.2` | `IDC-ABAC`, `IAM-SESSION-TAGS`, `IAM-EVAL` |
| 6 | Preserve requester identity through role chains. | Use source identity and/or controlled session tags where supported, make required attributes transitive only when intended, and log the resulting sessions so downstream actions remain attributable. | Put the employee password in the role session name; assume CloudTrail always reconstructs an arbitrary upstream identity without configuration; make all tags transitive to every role. | `SAP-2.3`, `SAP-3.2` | `STS-ASSUME`, `IAM-SESSION-TAGS`, `CT-ORGTRAIL` |
| 7 | Bound temporary sessions with session policies and duration. | Treat session policies as an additional intersection that can reduce, not expand, role permissions; choose duration according to task risk and reauthentication needs. | A session policy can grant actions missing from the role; longer duration is always more secure because fewer logins occur; revoking an IdP user instantly invalidates every already-issued session without further controls. | `SAP-1.2`, `SAP-2.3` | `STS-ASSUME`, `IAM-EVAL` |
| 8 | Delegate Identity Center administration without overexposing the management account. | Use supported delegated administration, separate identity assignment duties from permission-set definition where organizationally required, and audit privileged changes. | Make every help-desk operator a management-account administrator; delegate to an arbitrary external account; assume delegation removes all management-account responsibilities. | `SAP-1.4`, `SAP-3.2` | `IDC-DELEGATE`, `ORG-MGMT` |
| 9 | Design emergency access for an IdP or Identity Center outage. | Maintain a tightly controlled, monitored, periodically tested emergency path with independent dependencies, short-lived use, and post-event credential rotation/review. | Create permanent admin users for all engineers; depend on the failed IdP for break-glass approval; exempt emergency access from logging. | `SAP-1.2`, `SAP-1.3` | `IAM-CROSS`, `CT-ORGTRAIL`, `ORG-MGMT` |
| 10 | Roll out a least-privilege permission-set change. | Analyze actual access, create a new version, pilot with a representative group/account, monitor denied and privileged calls, preserve rollback, and remove obsolete assignments after validation. | Edit the only production permission set in place without a pilot; grant AdministratorAccess and rely on training; judge success only by successful login. | `SAP-2.1`, `SAP-3.2` | `IDC-PSET`, `CT-ORGTRAIL`, `IAM-EVAL` |

---

## Chapter 83 — Global Application and Multi-Region Data

### Current-question audit

- Questions 1 and 5 repeat a high-level “choose data semantics first” principle; Questions 2 and 4 repeat Route 53 settings.
- Question 4 is factually unsafe because Route 53 alone cannot satisfy compute readiness, replication, write ownership, secrets, queues, or failover.
- Question 1’s “stateless active-active first” option is compatible with the selected answer and may be the correct staged solution under a least-change constraint.
- The questions focus on DNS mechanics but do not test Route 53 versus Global Accelerator protocol/entry-point differences.
- The set does not distinguish Aurora global database writer topology/write forwarding from DynamoDB global table write modes.
- Any blanket rule that global tables are always eventually consistent is now unsafe; current DynamoDB global tables support MREC and MRSC with different restrictions and trade-offs.

### Exactly ten knowledge-coverage intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | SAA-C03 / SAP-C02 task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Separate global entry-point choice from data architecture. | Select Route 53 or Global Accelerator for traffic requirements, but independently define compute capacity, state replication, write ownership, consistency, and failover/failback. | DNS automatically promotes databases; Global Accelerator replicates application state; a second Region with empty infrastructure is active-active. | `SAP-1.1`, `SAP-1.3` | `R53-ROUTING`, `GA`, `DR` |
| 2 | Choose Route 53 versus Global Accelerator. | Use Route 53 when DNS routing policies and endpoint diversity fit; use Global Accelerator for static anycast IPs and AWS-edge routing of TCP/UDP to healthy regional endpoints. | Route 53 proxies every application packet; Global Accelerator caches HTTP objects; either service makes unhealthy application dependencies healthy. | `SAP-1.1`, `SAP-2.5` | `R53-ROUTING`, `GA` |
| 3 | Design DNS failover without assuming instant traffic movement. | Configure meaningful health evaluation and records, account for resolver/client caches and existing connections, lower TTL before planned changes, and validate the complete regional stack. | TTL zero guarantees immediate failover; a healthy load balancer proves the database is writable; DNS failover terminates established TCP sessions. | `SAP-1.3`, `SAP-2.4` | `R53-FAILOVER`, `DR` |
| 4 | Use Aurora Global Database for single-writer relational state. | Keep an explicit primary writer Region, use secondary Regions for local reads/DR, understand replication lag and write-forwarding behavior where enabled, and use managed switchover/failover with application reconnect and reconciliation. | Every secondary is an independent multi-master writer; a reader endpoint provides global strong consistency; DNS promotion alone changes database write ownership. | `SAP-1.3`, `SAP-2.2` | `AURORA-GLOBAL`, `AURORA-DR` |
| 5 | Choose MREC or MRSC for a DynamoDB global table. | Match the consistency mode to application invariants, latency, Region topology, and service restrictions; do not assert one universal global-table consistency model. | All global tables use last-writer-wins eventual consistency; MRSC removes every cross-Region latency trade-off; MREC provides synchronous quorum writes across Regions. | `SAP-2.4`, `SAP-2.5` | `DDB-GLOBAL`, `DDB-CONSISTENCY` |
| 6 | Prevent conflicting active-active writes. | Partition write ownership by tenant/entity/Region or use a datastore mode that meets the invariant; make operations idempotent and define conflict/reconciliation rules before enabling multiple writers. | Rely on timestamps without clock/conflict analysis; let every Region update the same financial aggregate freely; solve duplicate writes by lowering DNS TTL. | `SAP-1.3`, `SAP-2.4` | `DDB-GLOBAL`, `AURORA-GLOBAL` |
| 7 | Make regional dependencies failover-ready. | Replicate or recreate secrets, keys/policies, images, configuration, quotas, event consumers/checkpoints, certificates, and third-party allowlists; validate them in a game day. | Replicating the database is sufficient; reuse a single-Region KMS key ARN in every Region; assume service quotas and artifacts are global. | `SAP-1.3`, `SAP-2.2` | `DR`, `AURORA-DR` |
| 8 | Preserve data residency in a global design. | Classify data, keep authoritative or restricted fields in approved Regions, route users accordingly, and replicate only permitted projections while documenting legal and operational exceptions. | Latency routing enforces legal residency by itself; Global Accelerator stores data in edge locations; encrypting data permits unrestricted replication. | `SAP-1.2`, `SAP-2.3` | `R53-ROUTING`, `DR` |
| 9 | Perform a controlled regional switchover and failback. | Quiesce or fence writers as required, verify replication state, shift the data role before or with traffic according to the runbook, monitor business invariants, and plan reconciliation/failback. | Change DNS first and let both writers converge; promote a stale Region without measuring lag; treat failback as the exact reverse with no changed state. | `SAP-2.1`, `SAP-2.2` | `AURORA-DR`, `R53-FAILOVER` |
| 10 | Compare availability gain with global operating cost. | Measure regional idle/active capacity, replication writes/storage, cross-Region transfer, observability, and operational testing against required RTO/RPO and latency; use active-passive or read-local designs when full active-active value is unjustified. | Multi-Region always costs the same as Multi-AZ; replication traffic is free; active-active is automatically the lowest-operations design. | `SAP-1.5`, `SAP-2.6` | `DR`, `COST-WA` |

---

## Chapter 84 — Organization-wide Backup, DR, and Compliance

### Current-question audit

- Questions 1 and 5 repeat the same organization backup policy; Questions 2 and 4 repeat the backup-plan settings list.
- Question 1 presents service-native backup as an alternative even though native PITR/replication and organization-wide AWS Backup governance can be complementary.
- Question 2 incorrectly groups cross-account copy with Vault Lock mode settings. Copy configuration belongs to backup plans/vault access and organization setup, not to the lock mode itself.
- “Cross-account immutable copy” is under-specified: the destination account, vault/key policy, lock mode, retention, and source-admin permissions determine independence.
- Question 5’s generic canary rollout does not test backup-policy inheritance, effective-policy validation, restore dependencies, or recovery ownership.
- Missing density: tag/resource assignment, cross-account encryption, default-vault constraints, Vault Lock modes, logically air-gapped vaults, restore testing/validation, Audit Manager scope, PITR, cold-storage minimums, and RTO evidence.

### Exactly ten knowledge-coverage intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | SAA-C03 / SAP-C02 task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Apply a backup baseline through AWS Organizations. | Enable backup policies, attach complete and testable policies at appropriate root/OU/account scopes, select resources by tags or ARNs, specify the service role, and inspect the effective policy. | An SCP schedules backups; a tag policy creates recovery points; an incomplete child fragment is always valid without inherited elements. | `SAP-1.4`, `SAP-2.2` | `ORG-BACKUP`, `ORG-INHERIT` |
| 2 | Isolate recovery points in another account. | Copy to a destination vault owned by a recovery/security account, grant only the copy path, use an appropriate destination KMS key, and ensure source admins cannot delete or alter the destination copy. | Copy to the default vault in the source account; reuse an unshareable service-owned key across accounts; let workload administrators own the destination vault policy. | `SAP-1.2`, `SAP-2.2` | `BACKUP-XACCT`, `SRA-LOG` |
| 3 | Add regional disaster recovery without confusing copy with application readiness. | Create cross-Region copies where required, but separately provision identity, network, compute, quotas, configuration, and restore sequencing needed to meet RTO/RPO. | A cross-Region recovery point is a warm standby application; backup copy guarantees zero RPO; DNS failover restores resources automatically. | `SAP-1.3`, `SAP-2.2` | `BACKUP-XACCT`, `DR` |
| 4 | Choose Governance versus Compliance mode in Vault Lock. | Use Governance mode when specifically privileged administrators may change the lock; use Compliance mode when the lock must become immutable after its grace period, with retention bounds designed before lock-in. | Governance mode cannot be removed by any principal; Compliance mode can be shortened by root; Vault Lock encrypts backups but does not control deletion. | `SAP-1.2`, `SAP-2.3` | `VAULT-LOCK` |
| 5 | Decide when a logically air-gapped vault adds value. | Use it for a separately protected, shareable recovery store with additional security controls and planned restore access; it complements rather than replaces backup creation, validation, and incident runbooks. | It is physically disconnected from AWS at all times; it automatically copies every standard vault; its RAM share makes recovery points public. | `SAP-1.2`, `SAP-2.2` | `BACKUP-AIRGAP`, `BACKUP-XACCT` |
| 6 | Automate restore testing and application validation. | Schedule restore tests, provide or override required metadata, then run post-restore validation of data and application behavior; a completed infrastructure restore alone does not prove the business RTO. | Backup job success proves restore viability; inferred metadata always chooses the production network correctly; delete the restored resource before validation. | `SAP-2.2`, `SAP-3.4` | `BACKUP-RESTORE`, `BACKUP-VALIDATE` |
| 7 | Measure backup compliance with AWS Backup Audit Manager. | Select controls for coverage, frequency, retention, copies, and restore activity, understand account/Region/resource support, and route noncompliance to an owner and remediation workflow. | A framework is a preventive deny policy; one framework automatically evaluates every Region; a compliant report proves application-level recoverability. | `SAP-1.2`, `SAP-3.2` | `BACKUP-AUDIT` |
| 8 | Choose snapshot backup versus continuous PITR. | Use PITR for supported databases when recovery to a fine-grained time within the supported window is required; use scheduled recovery points for longer retention and other recovery patterns, and test both. | Daily snapshots provide second-level RPO; PITR is indefinite archival; read replicas replace recovery points for accidental deletion. | `SAP-2.2`, `SAP-3.4` | `BACKUP-PITR`, `BACKUP-RESTORE` |
| 9 | Optimize backup lifecycle cost without violating retention. | Transition supported recovery points to cold storage only when restore latency and minimum cold-storage duration fit; align expiration with legal holds, copy schedules, and actual recovery demand. | Cold storage supports every resource type identically; delete immediately after transition without minimum-duration cost; storage price alone determines the right lifecycle. | `SAP-2.6`, `SAP-3.5` | `BACKUP-LIFECYCLE`, `COST-WA` |
| 10 | Assign recovery ownership and conduct a ransomware game day. | Name policy, vault/key, restore, application-validation, and incident-command owners; test loss of the workload account, credentials, and primary Region, then preserve evidence and close gaps. | The central backup team alone can validate every application; workload owners may delete failed test evidence; an untested runbook satisfies quarterly recovery proof. | `SAP-3.1`, `SAP-3.4` | `BACKUP-RESTORE`, `SRA-LOG`, `DR` |

---

## Chapter 85 — Portfolio Cost, Tagging, and Chargeback

### Current-question audit

- Questions 1 and 5 repeat the same consolidated-billing/tags/reporting design; Questions 2 and 4 repeat the export settings.
- Question 1 treats showback/chargeback and a stable taxonomy as an alternative even though those are the operating model the technical design must serve.
- The chapter hard-codes the legacy “AWS Cost and Usage Report” label and schema assumptions. Current designs should account for AWS Data Exports and CUR 2.0 migration.
- Question 3 incorrectly places billing exports in a request/data path and implies that resource IDs and tags are automatically complete.
- Question 5’s canary/rollback boilerplate does not test allocation-rule versioning, close-period reconciliation, shared-cost policy, or finance ownership.
- Missing density: activating cost tags, account tags, untaggable/shared costs, Cost Categories, amortized versus unblended views, RI/SP sharing, budget delay, anomaly detection, unit economics, and optimization verification.

### Exactly ten knowledge-coverage intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | SAA-C03 / SAP-C02 task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Build a cost-allocation taxonomy that has accountable owners. | Define stable product, owner, environment, cost-center, and application dimensions; decide which are account-level versus resource-level; assign governance and exception owners before reporting. | Use only the `Name` tag; infer owner from the AWS service; change tag meanings each month to match reporting requests. | `SAP-1.5` | `ACCOUNT-TAGS`, `COST-TAGS` |
| 2 | Make cost allocation tags appear in billing data. | Apply supported tags and activate user-defined cost allocation tag keys in Billing; account for propagation/activation timing and missing historical values. | Any resource tag appears in reports immediately; tag policies activate billing tags; deactivating a key rewrites prior invoices. | `SAP-1.5`, `SAP-3.5` | `COST-TAGS` |
| 3 | Use account tags alongside resource tags. | Use account tags for organization-wide allocation of all metered usage in an account and resource tags for finer workload attribution; design explicit treatment for shared and untaggable charges. | Account tags replace all resource tags; a resource can override the payer account’s identity; support charges automatically inherit an application tag. | `SAP-1.4`, `SAP-1.5` | `ACCOUNT-TAGS`, `COST-TAGS` |
| 4 | Select Data Exports CUR 2.0 for detailed analytics. | Use Data Exports/CUR 2.0 with a controlled S3 destination and query pipeline, understand its schema and refresh cadence, and migrate legacy CUR consumers deliberately. | Cost Explorer is a line-item export; CUR 2.0 is a real-time stream; changing export schema cannot affect downstream queries. | `SAP-1.5`, `SAP-2.5` | `DATA-EXPORTS`, `COST-EXPLORER` |
| 5 | Choose the correct cost metric for showback. | State whether the view uses unblended, blended, amortized, net, or effective commitment cost and keep the rule consistent with the business question; reconcile to the payer bill. | One metric is universally correct; monthly cash purchase price equals service consumption; credits and refunds should always be allocated by raw usage. | `SAP-1.5` | `COST-EXPLORER`, `COST-WA` |
| 6 | Allocate shared platform costs transparently. | Define direct, fixed, proportional, or usage-driver allocation for TGW, data platforms, support, and security; expose both raw and allocated views and version the rule with finance approval. | Charge every shared cost to the central team forever; divide equally regardless of consumption; hide allocation logic from consuming teams. | `SAP-1.5`, `SAP-3.5` | `DATA-EXPORTS`, `COST-WA` |
| 7 | Design RI and Savings Plans ownership and sharing. | Decide which accounts may share discounts, measure utilization and coverage, allocate benefits consistently, and separate commitment-purchase ownership from workload consumption accountability. | Discounts always remain in the purchasing account; turning off sharing cancels the commitment; buy commitments from one week of peak usage. | `SAP-1.5`, `SAP-2.6` | `COST-SHARING`, `COST-EXPLORER` |
| 8 | Use Budgets without treating them as real-time circuit breakers. | Create actual and forecast thresholds with owners and optional actions, but account for billing-data delay and use service quotas or application controls for immediate technical limiting. | A budget alert stops spend instantly; budget data updates per request; a forecast threshold proves no cost overrun can occur. | `SAP-1.5`, `SAP-3.5` | `COST-BUDGETS` |
| 9 | Detect anomalous spend separately from fixed thresholds. | Use Cost Anomaly Detection for deviations from expected patterns, tune monitor scope and subscribers, investigate root cause, and retain Budgets for planned thresholds and Marketplace cases not covered. | Anomaly detection enforces an SCP; every cost increase is anomalous; it replaces ownership and tagging. | `SAP-1.5`, `SAP-3.5` | `COST-ANOMALY`, `COST-BUDGETS` |
| 10 | Prove an optimization improved unit economics. | Baseline business volume, service cost, performance, and reliability; deploy the change safely; measure cost per successful transaction/customer and verify savings were not shifted into risk or toil. | Declare success from a lower monthly bill during lower demand; count projected savings as realized savings; ignore data-transfer and operational labor. | `SAP-2.6`, `SAP-3.5` | `COST-WA`, `DATA-EXPORTS` |

---

## Chapter 86 — Migration Assessment, Portfolio, and Wave Planning

### Current-question audit

- Questions 1 and 5 repeat the same inventory/dependency/wave statement; Questions 2 and 4 repeat a Migration Hub settings bundle.
- Question 1 makes Discovery Service data plus owner/traffic validation an alternative even though it is required input to the selected portfolio plan.
- Question 3 contains two compatible truths—Migration Hub aggregation and discovery collection—but frames them as competing mechanisms in a nonexistent application data path.
- The settings list mixes evolving Migration Hub/Orchestrator concepts without testing application grouping, dependency confidence, business calendar, or cutover readiness.
- The tool landscape is now version-sensitive: AWS Migration Hub and AWS Application Discovery Service have not been open to new customers since 2025-11-07, and AWS points new customers to AWS Transform. Hard-coding older product workflows without an availability boundary is obsolete and factually unsafe.
- Missing density: portfolio disposition, data quality, dependency groups, landing-zone/hybrid readiness, transfer method, wave exit criteria, migration factory throughput, rollback, owner sign-off, and benefits tracking.

### Exactly ten knowledge-coverage intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | SAA-C03 / SAP-C02 task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Build a decision-grade migration inventory with the current service boundary. | For new customers, use AWS Transform assessment workflows and combine their output with CMDB/cloud records, owner interviews, utilization history, licensing, criticality, classification, dependencies, and lifecycle status; treat Migration Hub/Application Discovery Service as legacy-customer paths after the 2025-11-07 availability change. | Recommend Application Discovery Service to every new customer; treat the server list as the application portfolio; use one day of CPU as the sizing baseline. | `SAP-4.1` | `TRANSFORM-ASSESS`, `MIG-HUB-CHANGE`, `ADS-CHANGE`, `SERVICE-AVAILABILITY`, `MIG-PHASES` |
| 2 | Group assets into applications and dependency move groups. | Migrate components that must function together, including shared databases, identity, DNS, file exchange, batch schedules, and external partners; do not split solely to reach a server-count target. | Put equal numbers of servers in each wave; group only by operating system; ignore low-volume connections as nondependencies. | `SAP-4.1`, `SAP-4.2` | `ADS`, `TRANSFORM-WAVES` |
| 3 | Validate discovered dependencies. | Use process/network evidence over a representative period and corroborate it with application owners, architecture records, and cutover rehearsals because encrypted, intermittent, or business dependencies can be missed or misclassified. | Discovery output is a complete business map; owner interviews alone replace traffic evidence; one quiet weekend captures all batch dependencies. | `SAP-4.1` | `ADS`, `TRANSFORM-WAVES` |
| 4 | Build a migration business case from multiple scenarios. | Compare right-sized target options, licensing, migration effort, dual-running cost, data transfer, operational change, risk, and expected business outcomes; record assumptions for later validation. | Compare only on-premises hardware depreciation with EC2 list price; assume every server runs 24×7 unchanged; count unapproved projected savings as committed value. | `SAP-1.5`, `SAP-4.1` | `TRANSFORM-ASSESS`, `COST-WA` |
| 5 | Sequence waves by prerequisites and learning value. | Establish landing zone, identity, network, security, operations, and shared-data prerequisites; start with representative low-risk workloads, then increase complexity while respecting business blackout periods. | Move the most critical coupled estate first; sort only by server ID; postpone all platform readiness until the first cutover. | `SAP-2.1`, `SAP-4.2` | `MIG-PHASES`, `MIG-PLAYBOOK` |
| 6 | Define wave entry and exit criteria. | Require validated inventory, target design, security review, test/cutover/rollback plans, owner approval, capacity, support readiness, and measurable post-cutover acceptance before declaring a wave complete. | Mark complete when replication starts; skip rollback after one successful test; accept infrastructure health without business validation. | `SAP-2.1`, `SAP-4.2` | `TRANSFORM-WAVES`, `MIG-PLAYBOOK` |
| 7 | Choose online versus physical data transfer for a migration wave. | Calculate data volume, change rate, available bandwidth, transfer window, security, and seeding/validation needs; use DataSync for supported online transfers and current approved physical-transfer options when online transfer cannot meet the window. | Choose Snowball Edge for every new customer; estimate only raw bytes and ignore change rate; use DMS to copy arbitrary NAS files. | `SAP-1.1`, `SAP-4.2` | `DATASYNC-NET`, `SNOW-CHANGE` |
| 8 | Design hybrid connectivity and DNS as temporary production architecture. | Provide resilient DX/VPN paths, BGP routing, Route 53 Resolver endpoints/rules, identity, monitoring, and capacity for the entire coexistence period; test circuit, route, and DNS failure and prevent migration traffic from starving production. | One DX connection is enough because migration is temporary; build hybrid DNS after workloads move; send bulk transfer through an untested production bottleneck. | `SAP-1.1`, `SAP-1.3` | `DX-RESILIENCY`, `R53-RESOLVER`, `R53-HYBRID`, `DATASYNC-VERIFY` |
| 9 | Distinguish migration transfer from persistent hybrid storage. | Use DataSync for scheduled/one-time file or object movement and Storage Gateway when applications must continue using supported local file, volume, or tape interfaces backed by AWS storage. | Storage Gateway is the fastest generic one-time copy tool; DataSync presents a permanent iSCSI volume; either service provides transactional database CDC. | `SAP-4.2` | `DATASYNC-NET`, `STORAGE-GATEWAY` |
| 10 | Operate a migration factory with accountable throughput. | Standardize repeatable playbooks and automation, assign wave/application/platform owners, limit work in progress, track blockers and escaped defects, and feed lessons into later waves rather than optimizing only server count. | Centralize every decision in one architect; start all waves concurrently; measure success only by migrated server totals. | `SAP-3.1`, `SAP-4.2` | `MIG-PLAYBOOK`, `TRANSFORM-WAVES` |

---

## Chapter 87 — AWS Transform MGN, DMS, and Schema Conversion

### Current-question audit

- The chapter and questions use the former name “AWS Application Migration Service.” AWS renamed it AWS Transform MGN in June 2026, so the title and service references need a dated alias.
- Question 1 bundles server block replication, database data movement, and schema conversion into one answer; Questions 2–4 then test only MGN.
- Question 4 is substantively wrong: choosing MGN alone cannot meet a requirement that explicitly includes database engine conversion and low-downtime data migration.
- Question 3 tests only the MGN staging flow and leaves DMS CDC, task recovery, validation, and schema conversion unmeasured.
- The set assumes SCT is the only schema-conversion path and omits the current managed DMS Schema Conversion feature.
- Missing density: MGN test versus cutover, source write fencing, DMS task modes, native homogeneous migrations, CDC lag, LOB/unsupported objects, validation, schema action items, cutover sequencing, rollback, and hybrid bandwidth.

### Exactly ten knowledge-coverage intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | SAA-C03 / SAP-C02 task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Match the migration tool to server, data, schema, and file responsibilities. | Use AWS Transform MGN for server rehost through block replication, DMS for supported database migration/replication, schema-conversion tooling for heterogeneous semantics, and DataSync for file/object transfer. | Use MGN to convert stored procedures; use DMS to clone an operating-system disk; use DataSync for database transaction-log CDC. | `SAP-4.2` | `MGN`, `DMS`, `DMS-SCHEMA`, `DATASYNC-NET` |
| 2 | Plan an MGN staging network and replication path. | Size and secure the staging subnet, replication servers, routing/endpoints, bandwidth, and service permissions; monitor backlog/lag and avoid competing with production traffic. | Replication bypasses network capacity planning; the cutover subnet must be the staging subnet; install the agent and assume every blocked port is auto-remediated. | `SAP-1.1`, `SAP-4.2` | `MGN`, `DATASYNC-VERIFY` |
| 3 | Use MGN test launches before cutover. | Launch isolated test instances from current replicated state, execute technical and business validation, correct launch settings/post-launch actions, and finalize testing before scheduling cutover. | Test against production DNS immediately; treat a booted EC2 instance as application acceptance; finalize cutover before owners validate dependencies. | `SAP-2.1`, `SAP-4.2` | `MGN-CUTOVER`, `MGN` |
| 4 | Execute and finalize an MGN cutover with rollback awareness. | Quiesce source activity as required, confirm replication state, launch the latest cutover instance, shift dependencies/traffic, validate, and finalize only after the rollback window and source-of-truth decision are explicit. | Keep both source and cutover instances writable indefinitely; finalize before validation to save cost; assume MGN provides automatic failback like a DR service. | `SAP-2.2`, `SAP-4.2` | `MGN-CUTOVER`, `MGN-FAQ` |
| 5 | Select DMS full load, CDC, or full load plus CDC. | Choose the task mode from downtime and synchronization requirements; provision source logging/retention, endpoints, mappings, and task capacity so CDC can catch up before cutover. | Full load automatically captures later changes; CDC creates all target schema semantics; increasing target storage always removes source-log lag. | `SAP-4.2` | `DMS` |
| 6 | Decide between DMS homogeneous migration and conventional replication tasks. | Use homogeneous serverless data migrations where supported and where native-tool behavior/secondary-object handling fits; use standard DMS tasks or native methods according to validation, engine, and operational requirements. | Homogeneous migration works between unrelated engines; it always includes built-in validation; one method has identical object support for every engine. | `SAP-4.2`, `SAP-4.3` | `DMS-HOMOGENEOUS`, `DMS` |
| 7 | Convert a heterogeneous database schema and code. | Use DMS Schema Conversion or AWS SCT to assess and convert supported objects, review action items, manually remediate unsupported semantics, and regression-test application SQL and behavior. | Schema conversion migrates all table data automatically; a successful DDL conversion proves stored code equivalence; rename data types until the report is empty without application tests. | `SAP-4.2`, `SAP-4.3` | `DMS-SCHEMA`, `SCT-ASSESS` |
| 8 | Configure DMS mappings, LOB handling, and task capacity. | Scope tables explicitly, choose LOB mode/limits and parallelism from actual data, provision replication capacity for source/target throughput, and test restart/recovery behavior. | Unlimited LOB mode has no performance trade-off; wildcard mappings safely include future unsupported tables; task memory cannot affect full-load behavior. | `SAP-2.5`, `SAP-4.2` | `DMS` |
| 9 | Validate migrated data without overclaiming correctness. | Enable DMS data validation or an appropriate comparison workflow, investigate mismatches, and add application-level counts, constraints, reconciliation, and business acceptance; row validation is not semantic proof. | Successful task status proves every row and stored procedure; validation replaces target constraints; compare only total database size. | `SAP-2.4`, `SAP-4.2` | `DMS-VALIDATE`, `SCT-ASSESS` |
| 10 | Cut over a heterogeneous database with minimal downtime. | Freeze incompatible DDL, let CDC lag reach an approved threshold, stop or fence source writes, apply final changes, validate target data/application behavior, switch endpoints, and retain a time-bounded rollback/reconciliation plan. | Change DNS while both databases accept writes; cut over after full load regardless of CDC lag; delete the source immediately to prove commitment. | `SAP-2.1`, `SAP-2.2` | `DMS`, `DMS-VALIDATE`, `DMS-SCHEMA` |

---

## Chapter 88 — 7Rs: Rehost to Refactor

### Current-question audit

- Questions 1 and 5 repeat the seven-strategy list and generic rollout language.
- Question 1’s rehost-versus-refactor trade-off option is compatible with the selected portfolio strategy, so it is not a clean single-answer contrast.
- Questions 2–4 incorrectly make Migration Hub configuration the answer to a business/architecture disposition decision. A tracking tool does not choose an R.
- Question 3 again invents an application request/data path for a portfolio control plane.
- The set names the seven strategies but does not test the decision boundary for retain, retire, relocate, rehost, replatform, repurchase, or refactor.
- Missing density: evidence and owner for each disposition, exit deadlines, licensing, dependency effects, target operating model, modernization timing, reversibility, benefits, and portfolio balancing.

### Exactly ten knowledge-coverage intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | SAA-C03 / SAP-C02 task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Choose an R from business outcome, deadline, and technical constraints. | Evaluate business value, lifecycle, dependencies, compliance, time, skills, target operating model, cost, and modernization benefit; record an owner, evidence, and review date for the chosen strategy. | Pick one R for the whole portfolio; choose the newest service by default; let the migration tool select the disposition automatically. | `SAP-4.1`, `SAP-4.2` | `MIG-7RS`, `TRANSFORM-ASSESS` |
| 2 | Retire an application safely. | Confirm no required consumers or records remain, meet retention/legal obligations, archive or migrate authoritative data, revoke access, terminate contracts/resources, and monitor for missed use. | Stop the servers before dependency validation; retain all licenses indefinitely; label an unknown-owner system “retire” to improve the plan. | `SAP-4.1` | `MIG-7RS`, `MIG-PLAYBOOK` |
| 3 | Retain a workload with an explicit revisit trigger. | Retain when migration is currently unjustified or blocked, but document risk, support horizon, security controls, owner, integration needs, and a dated event that reopens the decision. | “Retain” means no future investment or owner; leave unsupported systems unpatched; exclude retained dependencies from hybrid planning. | `SAP-4.1`, `SAP-3.2` | `MIG-7RS`, `MIG-PHASES` |
| 4 | Relocate a compatible virtualized environment. | Use relocation when moving the existing platform/workloads with minimal architectural change is supported and strategically justified; validate licensing, network, operations, and later modernization constraints. | Relocate means converting every VM to Lambda; it removes all hypervisor operations automatically; choose it without checking platform compatibility. | `SAP-4.2` | `MIG-7RS`, `TRANSFORM-ASSESS` |
| 5 | Rehost under a fixed data-center exit deadline. | Use MGN or another appropriate method to move supported servers quickly with minimal application change, while planning target security, resilience, rightsizing, and post-migration optimization. | Rehost preserves every source IP and dependency automatically; it is always the lowest lifetime cost; treat lift-and-shift as completion of modernization. | `SAP-4.2` | `MIG-7RS`, `MGN` |
| 6 | Replatform for a bounded operational improvement. | Change selected platform components—such as moving a database to a managed compatible service—without redesigning the application’s core architecture; test compatibility and rollback. | Replatform is a full domain rewrite; no application testing is needed because the engine is “compatible”; replatform every component in the same cutover. | `SAP-4.2`, `SAP-4.3` | `MIG-7RS`, `DMS-HOMOGENEOUS` |
| 7 | Repurchase a SaaS or packaged replacement. | Compare functional fit, data migration/export, identity, integration, compliance, contract/exit terms, and process change; treat adoption and decommissioning as a business transformation. | Repurchase means moving the same license to EC2; SaaS removes data-governance responsibility; select solely from subscription price. | `SAP-4.1`, `SAP-4.2` | `MIG-7RS`, `TRANSFORM-ASSESS` |
| 8 | Refactor only where differentiated value justifies the risk. | Use refactor for high-value capabilities needing new scale, resilience, speed, or operating economics; define incremental boundaries, measurable outcomes, and a staged migration rather than a deadline-blocking rewrite. | Refactor every legacy workload before data-center exit; split into microservices by code package; declare success when new infrastructure deploys. | `SAP-4.3`, `SAP-4.4` | `MIG-7RS`, `DECOMPOSE`, `STRANGLER` |
| 9 | Balance portfolio strategy against a fixed exit date. | Retire/retain/repurchase where justified, rehost or relocate the deadline-critical majority, and reserve replatform/refactor capacity for high-value candidates without putting the exit on the critical path. | Refactor the hardest 20% first; migrate only easy systems and leave the facility open; assign all workloads to rehost without reviewing retirement. | `SAP-4.1`, `SAP-4.2` | `MIG-PHASES`, `MIG-7RS` |
| 10 | Revisit disposition after migration using realized outcomes. | Compare actual cost, incidents, performance, delivery speed, and owner toil with the business case; move rehosted workloads into an owned optimization/modernization backlog or document why no further change is warranted. | The R decision is permanent; projected TCO is sufficient evidence; close the migration program before operational owners accept the workload. | `SAP-3.1`, `SAP-3.5`, `SAP-4.4` | `COST-WA`, `WA-IMPROVE`, `MIG-7RS` |

---

## Chapter 89 — Monolith to Containers/Serverless

### Current-question audit

- Question 1 has two compatible correct concepts: container/serverless are deployment choices, and strangler plus contract/state separation is the modernization approach.
- Questions 2 and 4 repeat ECS settings; Question 3 tests only ECS task/service mechanics.
- Question 4 is factually unsafe: choosing ECS does not discover domain boundaries, separate data ownership, or make teams independently deployable.
- The chapter frames ECS versus EKS versus Lambda as the central decision even though architecture boundaries, state, contracts, and ownership determine whether modernization succeeds.
- Any recommendation to use App2Container without an availability qualifier is obsolete for new customers after 2025-11-07; current coverage should recognize AWS Transform source-code containerization while preserving the principle that tooling does not discover correct domain boundaries.
- The generic fifth question does not test schema compatibility, dual running, traffic shift, event replay, or business rollback.
- Missing density: business-capability decomposition, strangler routing, shared-database exit, outbox/saga, idempotency, API/event versioning, platform versus product ownership, canary evidence, observability, and transition cost.

### Exactly ten knowledge-coverage intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | SAA-C03 / SAP-C02 task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Choose a service boundary by business capability and change ownership. | Extract a cohesive capability with its own team, contract, data responsibility, scaling/failure needs, and independent release value; do not split merely by technical layer or class count. | Create one service per database table; split UI, business logic, and data into separate services for every domain; use team size alone as the boundary. | `SAP-4.3`, `SAP-4.4` | `DECOMPOSE` |
| 2 | Apply the strangler pattern to a live monolith. | Put a controlled routing/facade boundary in front of the system, divert selected functionality to the new component, validate behavior and rollback, then remove the old path only after traffic and dependencies are gone. | Rewrite all features before routing any traffic; duplicate writes forever without reconciliation; remove the monolith endpoint before consumers migrate. | `SAP-2.1`, `SAP-4.4` | `STRANGLER`, `DECOMPOSE` |
| 3 | Decide whether current containerization tooling is sufficient. | For supported new-customer workflows, AWS Transform can generate and deploy container artifacts from source, while existing App2Container customers can retain that path; in either case, containerization improves packaging but does not modernize ownership, state, scaling, or release coupling by itself. | Recommend App2Container to every new customer; assume a container makes a component stateless; moving a monolith to EKS creates independently owned microservices. | `SAP-4.2`, `SAP-4.4` | `TRANSFORM-CONTAINERS`, `APP2CONTAINER-CHANGE`, `CONTAINERS-GUIDE`, `DECOMPOSE` |
| 4 | Select ECS, EKS, or Lambda from the operating contract. | Use ECS for AWS-native container orchestration, EKS when Kubernetes APIs/ecosystem are a requirement, and Lambda for event/request workloads that fit its execution model; include team skill and platform ownership. | EKS is always more portable and therefore cheaper; Lambda is a long-running server replacement; ECS executes Kubernetes operators directly. | `SAP-2.5`, `SAP-2.6` | `CONTAINERS-GUIDE`, `LAMBDA-BP` |
| 5 | Remove a shared database as an independence bottleneck. | Establish authoritative data ownership per capability, expose controlled APIs/events or transitional views, migrate data incrementally, and reconcile dual-running state before removing shared writes. | Give every service unrestricted write access to all schemas; copy all tables to every service; split compute first and call the system decoupled. | `SAP-2.4`, `SAP-4.3` | `MICROSERVICE-DATA`, `DECOMPOSE` |
| 6 | Publish an event atomically with a state change. | Use a transactional outbox or equivalent design so the business write and event record commit together; deliver with retries and idempotent consumers rather than an unsafe database-plus-broker dual write. | Write the database then send once with no recovery; use a longer HTTP timeout for atomicity; mark the event delivered before committing business state. | `SAP-2.4`, `SAP-3.4` | `OUTBOX` |
| 7 | Coordinate a business transaction across services. | Use local transactions plus saga orchestration/compensation when a workflow spans independently owned stores; define irreversible steps, idempotency, timeout, and reconciliation. | Use a distributed database transaction across arbitrary services by default; retry every step forever; treat compensation as guaranteed restoration of the exact prior world. | `SAP-2.4`, `SAP-4.3` | `SAGA`, `MICROSERVICE-DATA` |
| 8 | Version APIs and events during incremental extraction. | Prefer backward-compatible additions, tolerant consumers, explicit semantic versions for breaking changes, and a measured deprecation window; preserve correlation and idempotency keys across old/new paths. | Rename fields in place because JSON is schemaless; publish database rows as the permanent contract; remove old versions after the first successful canary. | `SAP-2.1`, `SAP-4.4` | `DECOMPOSE`, `OUTBOX` |
| 9 | Roll out a new containerized capability with business rollback. | Use blue/green, linear, or canary traffic shift as appropriate, validate application and business metrics, maintain schema compatibility, and define how writes/events are handled if traffic returns to the old version. | Roll back only the task definition after an irreversible schema change; shift all traffic when containers are healthy; ignore duplicate events during dual running. | `SAP-2.1`, `SAP-3.4` | `ECS-BG`, `OUTBOX` |
| 10 | Define platform and product-team ownership during modernization. | The platform team owns paved-road runtime, identity, networking, observability, and deployment capabilities; product teams own service behavior, data, SLOs, cost, and on-call outcomes, with explicit interfaces between them. | The platform team owns every application incident; each product team builds an unrelated cluster and security model; no team owns shared migration adapters. | `SAP-3.1`, `SAP-4.4` | `OE-WA`, `CONTAINERS-GUIDE` |

---

## Chapter 90 — Continuous Improvement of Existing Systems

### Current-question audit

- Questions 1 and 5 repeat the same baseline/reversible-change principle; Questions 2 and 4 repeat Well-Architected Tool fields.
- Question 3 incorrectly describes the Well-Architected Tool as a request/data-path component.
- Question 4 implies that selecting the Tool implements low-risk improvement. It records review state and risks; owners must design, deploy, and validate changes.
- Compute Optimizer is treated as a generic alternative rather than a recommendation source whose confidence depends on metric history, memory visibility, preferences, and workload context.
- The fifth question’s generic multi-account canary text does not test hypothesis, owner, success threshold, abort condition, or state rollback.
- Missing density: workload definition, risk prioritization, SLO/business baseline, recommendation validation, Config drift, improvement ownership, safe rollout, reliability testing, realized savings, and feedback cadence.

### Exactly ten knowledge-coverage intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | SAA-C03 / SAP-C02 task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Define the workload and baseline before proposing improvement. | Identify owners, users, critical journeys, architecture/dependencies, security obligations, SLOs, incidents, deployment lead time, and unit cost so a change has a measurable starting point. | Define the workload as one AWS account; baseline only CPU average; start with a preferred service and search for a problem it solves. | `SAP-3.1` | `WA-MILESTONE`, `OE-WA` |
| 2 | Turn a Well-Architected review into an owned improvement plan. | Use lenses to identify risks, prioritize by business impact and dependency, assign owner/date/evidence, implement iteratively, and save milestones to compare state over time. | The Tool auto-remediates high-risk items; close every risk in one sprint regardless of value; use a milestone as proof that production behavior improved. | `SAP-3.1` | `WA-MILESTONE`, `WA-IMPROVE` |
| 3 | Choose the first improvement under limited capacity. | Rank candidates by expected risk reduction or business value divided by cost/uncertainty, address enabling dependencies, and prefer a reversible change that creates evidence for the next decision. | Choose the newest AWS service; fix the easiest dashboard item only; begin a full rewrite because it can address many issues eventually. | `SAP-3.1`, `SAP-4.4` | `WA-IMPROVE`, `OE-WA` |
| 4 | Evaluate a Compute Optimizer recommendation. | Check metric coverage, lookback, memory or external metrics where relevant, performance-risk assumptions, seasonality, architecture constraints, and price-performance before accepting or rejecting the recommendation. | Apply every recommendation automatically to production; assume missing memory means memory is unused; use average CPU alone to size latency-sensitive workloads. | `SAP-3.3`, `SAP-3.5` | `COMPUTE-OPT`, `COMPUTE-METRICS` |
| 5 | Use AWS Config for drift and policy evidence. | Record supported resource configuration, evaluate managed/custom rules or conformance packs, aggregate where needed, and give remediation an owner and safe execution boundary; compliance state is not runtime health. | Config captures every application transaction; a conformance pack guarantees regulatory certification; automatic remediation is safe without rollback or scope controls. | `SAP-3.1`, `SAP-3.2` | `CONFIG-PACK`, `CONFIG-AGG` |
| 6 | Write a falsifiable improvement hypothesis. | State the proposed change, expected business/technical effect, leading and guardrail metrics, observation window, cost, abort threshold, and rollback; reject changes whose benefit cannot be distinguished from normal variation. | “Migrate because managed is better”; success equals deployment completion; measure only the metric the change is designed to improve. | `SAP-3.1`, `SAP-3.3` | `OE-WA`, `WA-IMPROVE` |
| 7 | Roll out a reversible change across accounts or services. | Use versioned IaC/configuration, pilot scope, canary or waves, health and business alarms, bake time, and an exercised rollback that accounts for schemas, queues, and other mutable state. | Change every account at the root simultaneously; roll back compute while leaving incompatible data changes; use resource health as the only abort signal. | `SAP-2.1`, `SAP-3.4` | `ECS-BG`, `CT-DRIFT`, `OE-WA` |
| 8 | Improve reliability through a tested failure hypothesis. | Select the largest credible failure mode, inject or simulate it within a bounded scope, observe detection and recovery, compare RTO/RPO/SLO results, and update architecture and runbooks. | Add a second Region without a game day; count backups instead of restoring; perform an uncontrolled production outage to maximize realism. | `SAP-3.4` | `DR`, `BACKUP-RESTORE`, `OE-WA` |
| 9 | Verify that a cost change produced realized savings. | Compare normalized post-change cost and performance over a representative period, include migration/dual-run/data-transfer/toil costs, and confirm the owner captured or reinvested the saving. | Report recommendation-estimated savings as realized; compare a low-demand week to peak season; exclude operational labor and transition cost. | `SAP-3.5` | `COMPUTE-OPT`, `DATA-EXPORTS`, `COST-WA` |
| 10 | Establish a continuous architecture-improvement cadence. | Review SLOs, incidents, security findings, cost, technical debt, and prior hypotheses on a regular cadence; maintain a prioritized owner-backed backlog and retire controls or systems that no longer add value. | Run one annual review with no follow-up; retain every control forever; make the central architecture team the sole owner of all improvements. | `SAP-3.1`, `SAP-4.4` | `WA-IMPROVE`, `OE-WA` |

---

## Requested coverage trace

| Required area | Primary chapter/intents |
|---|---|
| Multi-account governance; Organizations, Control Tower, and SCPs | Chapter 79, especially Intents 1–9 |
| Identity federation and cross-account authorization | Chapter 82 |
| Centralized networking, inspection, hybrid connectivity, and DNS | Chapter 80, especially Intents 1–10; Chapter 86 Intent 8 |
| Backup governance, recovery testing, compliance, and evidence | Chapter 84; Chapter 81 |
| Cost allocation, showback, chargeback, and realized savings | Chapter 85; Chapter 90 Intent 9 |
| Migration portfolio, dependencies, factory, and waves | Chapter 86 |
| AWS Transform MGN, DMS, SCT/schema conversion, cutover, and rollback | Chapter 87 |
| 7Rs disposition decisions | Chapter 88 |
| Modernization, containers/serverless, state separation, and operating model | Chapter 89 |
| Continuous improvement, reversible rollout, rollback, and evidence | Chapter 90 |

## Implementation acceptance criteria

- Chapters 79–90 must each contain exactly ten audit intents numbered 1–10: 120 total.
- Each intent must remain an internal coverage specification with one principal decision boundary, not a full exam prompt or option set.
- Every intent must contain one unique correct principle and exactly three plausible distractor concepts that could become valid under different constraints; do not reuse the current absurd boilerplate distractors.
- Future item explanations derived from these specifications must state the hard constraint, why each distractor fails here, the condition that would flip the answer, the SAA-C03 or SAP-C02 task ID, and at least one official product source key.
- Static validation must reject duplicate normalized choices, duplicate intents, invalid task/source keys, fewer or more than ten intents per chapter, missing distractor explanations, or a control-plane tool described as an application data-path component.
- Version-sensitive validation must flag the former AWS Application Migration Service name, legacy-only CUR assumptions, blanket eventual-consistency claims for DynamoDB global tables, and Snowball Edge recommendations for new customers.
- Version-sensitive validation must also flag unqualified new-customer recommendations for AWS Migration Hub, AWS Application Discovery Service, or App2Container.
- Official practice resources remain separate from product-fact sources. No exam dump, recalled live item, or third-party question bank may be ingested.
- Only `tools/aws_exam_audits/part_08.md` is created by this task.

SUPERSET_WORKER_DONE task P08-audit-v2
