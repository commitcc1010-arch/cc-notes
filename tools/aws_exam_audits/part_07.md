# Part 07 Audit — Chapters 72–78: Deployment and Operations

Audit date: 2026-10-01

Scope: audit the 35 current chapter questions and provide **exactly ten distinct knowledge-coverage audit intents for each Chapter 72–78**. These are internal coverage specifications, not exam questions. They do not reproduce full prompts or options, copy official questions, reconstruct live exam items, or use exam dumps.

Task mappings use the current SAA-C03 and SAP-C02 blueprints. SAP-C02 remains the active Professional exam on the audit date; AWS has announced SAP-C03 registration for 2026-10-27 and testing for 2026-11-18, so this file must be remapped when the SAP-C03 guide and official preparation assets become authoritative.

## Official AWS source keys

### Exam blueprints and public calibration resources

- `EX-SAA1` — [SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)
- `EX-SAA2` — [SAA-C03 Domain 2: Design Resilient Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain2.html)
- `EX-SAP2` — [SAP-C02 Domain 2: Design for New Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain2.html)
- `EX-SAP3` — [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)
- `EX-SAP-STATUS` — [AWS Certified Solutions Architect - Professional exam update](https://aws.amazon.com/certification/certified-solutions-architect-professional/)
- `SAA-SAMPLE` — [SAA-C03 official public sample questions PDF](https://d1.awsstatic.com/training-and-certification/docs-sa-assoc/AWS-Certified-Solutions-Architect-Associate_Sample-Questions.pdf)
- `SAP-SAMPLE` — [SAP-C02 official public sample questions PDF](https://d1.awsstatic.com/training-and-certification/docs-sa-pro/AWS-Certified-Solutions-Architect-Professional_Sample-Questions.pdf)
- `CERT-PREP` — [AWS Certification exam preparation resources](https://aws.amazon.com/certification/certification-prep/)

### CloudFormation, CDK, and infrastructure as code

- `CFN-CORE` — [What is AWS CloudFormation?](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html)
- `CFN-TEMPLATE` — [CloudFormation template sections](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-anatomy.html)
- `CFN-PARAM` — [Parameters section](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html)
- `CFN-DEPEND` — [DependsOn attribute](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-dependson.html)
- `CFN-NESTED` — [Work with nested stacks](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-nested-stacks.html)
- `CFN-STACKSETS` — [CloudFormation StackSets concepts](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html)
- `CFN-BEST` — [CloudFormation best practices](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html)
- `CFN-GUARD` — [AWS CloudFormation Guard](https://docs.aws.amazon.com/cfn-guard/latest/ug/what-is-guard.html)
- `CFN-DYNREF` — [Dynamic references](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references.html)
- `CDK-CORE` — [What is the AWS CDK?](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
- `CDK-BOOTSTRAP` — [Bootstrap AWS CDK environments](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping-env.html)

### Change sets, drift, protection, and rollback

- `CFN-CHANGESET` — [Update stacks using change sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets.html)
- `CFN-DRIFT` — [Detect unmanaged configuration changes with drift detection](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html)
- `CFN-DRIFT-AWARE` — [Use drift-aware change sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/drift-aware-change-sets.html)
- `CFN-STACKPOLICY` — [Prevent updates to stack resources](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/protect-stack-resources.html)
- `CFN-DELETE` — [DeletionPolicy attribute](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-deletionpolicy.html)
- `CFN-REPLACE` — [UpdateReplacePolicy attribute](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-updatereplacepolicy.html)
- `CFN-TERM` — [Protect a stack from deletion](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-protect-stacks.html)
- `CFN-IMPORT` — [Import AWS resources into a CloudFormation stack](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resource-import-existing-stack.html)
- `CFN-ROLLBACK` — [Roll back a stack on CloudWatch alarm breaches](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-rollback-triggers.html)
- `CFN-CONTINUE` — [Continue rolling back an update](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-continueupdaterollback.html)

### CI/CD and deployment strategies

- `CP-CONCEPTS` — [AWS CodePipeline concepts](https://docs.aws.amazon.com/codepipeline/latest/userguide/concepts.html)
- `CP-XACCOUNT` — [Create a cross-account CodePipeline pipeline](https://docs.aws.amazon.com/codepipeline/latest/userguide/pipelines-create-cross-account.html)
- `CP-APPROVAL` — [Manage approval actions in CodePipeline](https://docs.aws.amazon.com/codepipeline/latest/userguide/approvals.html)
- `CP-CFN` — [CloudFormation deploy action reference](https://docs.aws.amazon.com/codepipeline/latest/userguide/action-reference-CloudFormation.html)
- `CD-DEPLOYCFG` — [Work with CodeDeploy deployment configurations](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-configurations.html)
- `CD-BLUEGREEN` — [CodeDeploy blue/green deployments](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-steps-ecs.html)
- `CD-LAMBDA` — [CodeDeploy deployments on Lambda](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-steps-lambda.html)
- `CD-EC2` — [CodeDeploy deployments on EC2/on-premises](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-steps.html)
- `CD-ROLLBACK` — [Roll back and redeploy with CodeDeploy](https://docs.aws.amazon.com/codedeploy/latest/userguide/deployments-rollback-and-redeploy.html)
- `CD-ALARMS` — [Monitor CodeDeploy deployments with CloudWatch alarms](https://docs.aws.amazon.com/codedeploy/latest/userguide/monitoring-create-alarms.html)
- `WA-CHANGE` — [OPS06-BP01 Plan for unsuccessful changes](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mit_deploy_risks_plan_for_unsuccessful_changes.html)
- `WA-ROLLBACK` — [OPS06-BP04 Automate testing and rollback](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mit_deploy_risks_rollback.html)

### Systems Manager, patching, and fleet operations

- `SSM-NODE` — [Configure managed-node permissions](https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-launch-managed-instance.html)
- `SSM-VPCE` — [Create VPC endpoints for Systems Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-create-vpc.html)
- `SSM-SESSION` — [AWS Systems Manager Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)
- `SSM-SESSIONLOG` — [Session Manager logging limitations](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-logging.html)
- `SSM-RUNCOMMAND` — [Run commands at scale](https://docs.aws.amazon.com/systems-manager/latest/userguide/send-commands-multiple.html)
- `SSM-INVENTORY` — [AWS Systems Manager Inventory](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-inventory.html)
- `SSM-STATE` — [AWS Systems Manager State Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-state.html)
- `SSM-MW` — [AWS Systems Manager Maintenance Windows](https://docs.aws.amazon.com/systems-manager/latest/userguide/maintenance-windows.html)
- `SSM-STATE-MW` — [Choose between State Manager and Maintenance Windows](https://docs.aws.amazon.com/systems-manager/latest/userguide/state-manager-vs-maintenance-windows.html)
- `SSM-PATCHPOLICY` — [Patch policy configurations in Quick Setup](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-patch-policies.html)
- `SSM-PATCHBASE` — [Predefined and custom patch baselines](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-predefined-and-custom-patch-baselines.html)
- `SSM-PATCHACTION` — [AWS-RunPatchBaseline operations](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-aws-runpatchbaseline.html)
- `SSM-QUICKSETUP` — [Configure organization patching with Quick Setup](https://docs.aws.amazon.com/systems-manager/latest/userguide/quick-setup-patch-manager.html)
- `SSM-COMPLIANCE` — [AWS Systems Manager Compliance](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-compliance.html)

### Config, CloudTrail, EventBridge, and remediation

- `CONFIG-CORE` — [What is AWS Config?](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)
- `CONFIG-RULES` — [Evaluate resources with AWS Config rules](https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config.html)
- `CONFIG-REMED` — [Remediate noncompliant resources with AWS Config rules](https://docs.aws.amazon.com/config/latest/developerguide/remediation.html)
- `CONFIG-AUTOREMED` — [Set up automatic remediation](https://docs.aws.amazon.com/config/latest/developerguide/setup-autoremediation.html)
- `CONFIG-ORG` — [Deploy organization conformance packs](https://docs.aws.amazon.com/config/latest/developerguide/conformance-pack-organization-apis.html)
- `CONFIG-AGG` — [Aggregate AWS Config data](https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html)
- `CT-EVENTS` — [CloudTrail events](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-events.html)
- `EB-DIRECT` — [AWS service events in EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-service-event.html)
- `EB-CLOUDTRAIL` — [CloudTrail-delivered AWS service events in EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-service-event-cloudtrail.html)
- `EB-RETRY` — [Retry policies for EventBridge targets](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-retry-policy.html)
- `EB-DLQ` — [Dead-letter queues for EventBridge targets](https://docs.aws.amazon.com/eventbridge/latest/userguide/rule-dlq.html)
- `LAMBDA-IDEMPOTENT` — [Lambda best practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- `SSM-AUTOMATION` — [AWS Systems Manager Automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html)
- `S3-BPA` — [Block public access to S3 storage](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html)

### Backup, restore testing, resilience, and operational excellence

- `BACKUP-PLANS` — [AWS Backup plans](https://docs.aws.amazon.com/aws-backup/latest/devguide/about-backup-plans.html)
- `BACKUP-RESTORE` — [Restore a backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/restoring-a-backup.html)
- `BACKUP-RESTORETEST` — [Restore testing in AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)
- `BACKUP-VALIDATE` — [Validate restore testing jobs](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing-validation.html)
- `BACKUP-XACCOUNT` — [Create backup copies across AWS accounts](https://docs.aws.amazon.com/aws-backup/latest/devguide/create-cross-account-backup.html)
- `BACKUP-ENCRYPT` — [Encryption for backups in AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/encryption.html)
- `BACKUP-VAULTLOCK` — [AWS Backup Vault Lock](https://docs.aws.amazon.com/aws-backup/latest/devguide/vault-lock.html)
- `BACKUP-AUDIT` — [AWS Backup Audit Manager](https://docs.aws.amazon.com/aws-backup/latest/devguide/aws-backup-audit-manager.html)
- `FIS-CORE` — [What is AWS Fault Injection Service?](https://docs.aws.amazon.com/fis/latest/userguide/what-is.html)
- `FIS-STOP` — [Stop conditions for AWS Fault Injection Service](https://docs.aws.amazon.com/fis/latest/userguide/stop-conditions.html)
- `RESILIENCE-HUB` — [What is AWS Resilience Hub?](https://docs.aws.amazon.com/resilience-hub/latest/userguide/what-is.html)
- `CW-AGENT` — [Collect metrics, logs, and traces with the CloudWatch agent](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)
- `CW-ALARMS` — [Use Amazon CloudWatch alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- `WA-OE` — [Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/operational-excellence.html)
- `WA-OBSERVE` — [Implement observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)
- `WA-READY` — [Operational readiness and change management](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/operational-readiness.html)
- `WA-ORR` — [OPS07-BP02 Ensure a consistent review of operational readiness](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ready_to_support_const_orr.html)
- `WA-RESPOND` — [Responding to events](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/responding-to-events.html)
- `WA-ALERT` — [OPS10-BP02 Have a process per alert](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_event_response_process_per_alert.html)
- `WA-RUNBOOK` — [OPS10-BP01 Use a process for event, incident, and problem management](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_event_response_process.html)
- `WA-EVOLVE` — [OPS11-BP02 Perform post-incident analysis](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops.html)
- `WA-TOOL` — [AWS Well-Architected Tool](https://docs.aws.amazon.com/wellarchitected/latest/userguide/intro.html)

## Cross-chapter findings

- All seven chapters use the same five-question generator pattern: broad service selection, one settings bundle, one mechanism statement, a least-operational-overhead restatement, and generic SAP governance. Questions 4 and 5 repeatedly restate earlier answers instead of adding a new failure boundary.
- Distractors such as deploying every option, assuming a managed service understands all business requirements, or granting organization-wide administrator access are implausibly weak. They reduce the need to reason about replacement behavior, traffic percentage, alarm state, concurrency, identity, evidence, or recovery dependencies.
- The current questions frequently conflate a product with an end-to-end process. CloudFormation does not replace source control and release governance; CodeDeploy does not make data changes reversible; Systems Manager does not remove operating-system repository dependencies; AWS Config does not prevent every unsafe API call; AWS Backup does not validate an application transaction; the Well-Architected Tool does not operate the workload.
- CI/CD, immutable artifact promotion, cross-account artifact and role access, realistic rollback boundaries, customer-impact observability, automation idempotency, restore validation, and evidence-driven operational improvement are materially underrepresented.
- No currently used service name in Chapters 72–78 is itself retired. The principal currency risk is blueprint metadata: SAP-C02 is still active on the audit date but has announced transition dates, so treating this mapping as timeless would make it obsolete.

---

## Chapter 72 — CloudFormation and Infrastructure as Code

### Current-question defects

- **Duplicate/invalid — Question 2:** options A and D are byte-for-byte identical CloudFormation setting lists, but only D is marked correct.
- **Duplicate/invalid — Question 3:** options C and D are byte-for-byte identical dependency-processing and rollback statements, but only C is marked correct.
- **Incorrect — Question 1 explanation:** it assigns CloudFormation's declarative-template responsibility to the CDK. CDK is an authoring framework that synthesizes CloudFormation templates; CloudFormation remains the deployment state engine in the normal CDK workflow.
- **Incorrect — Question 4 explanation:** the manual-operations distractor is described with CloudFormation's dependency-graph mechanism.
- **Ambiguous — Questions 1 and 5:** CloudFormation and CDK are treated as competing products even though a valid design commonly uses both. The questions do not establish a differentiating constraint such as direct template review versus reusable programming-language abstractions.
- **Low-density — Questions 4 and 5:** Question 4 repeats Question 2's settings bundle, and Question 5 repeats the chapter summary plus generic governance.
- **Coverage gap:** no current question tests implicit dependencies, explicit `DependsOn`, nested-stack ownership, StackSets permission modes, CDK bootstrap assets, policy-as-code checks, secret handling, immutable promotion, or failed-stack diagnosis.

### Ten knowledge-coverage audit intents

1. **Intent — Separate the IaC authoring layer from the deployment state engine.**
   - Hard constraint: A team wants reusable programming-language constructs but must retain a reviewable deployment plan and authoritative lifecycle state.
   - Correct principle: Use CDK as an authoring and synthesis layer when its abstractions add value; review the synthesized CloudFormation template and let CloudFormation own stack state, resource creation, update, deletion, events, and rollback.
   - Three plausible distractor concepts: (1) CDK directly manages AWS resources without CloudFormation state; (2) CloudFormation is only a template formatter and CDK owns rollback; (3) use console changes after synthesis because the CDK application will automatically adopt them.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.1`
   - Official source keys: `EX-SAA2, EX-SAP2, CFN-CORE, CDK-CORE`

2. **Intent — Parameterize environments without embedding secrets or creating uncontrolled divergence.**
   - Hard constraint: Development, staging, and production need different values, but the infrastructure definition must remain one reviewed source and credentials must not appear in templates or ordinary parameter values.
   - Correct principle: Use parameters, mappings, conditions, and environment-specific configuration deliberately; use dynamic references or a secrets service for sensitive values, and constrain/validate parameters instead of cloning independently edited templates.
   - Three plausible distractor concepts: (1) place database passwords in template defaults so deployments are reproducible; (2) maintain one manually edited template copy per account; (3) put every environment difference in a mapping even when the value must rotate independently.
   - Task mapping: `SAA-C03 SAA-1.2, SAA-2.2 | SAP-C02 SAP-2.1, SAP-2.3`
   - Official source keys: `EX-SAA1, EX-SAA2, EX-SAP2, CFN-TEMPLATE, CFN-PARAM, CFN-DYNREF`

3. **Intent — Distinguish implicit resource dependencies from explicit ordering.**
   - Hard constraint: Parallel creation is desirable, but one resource operation must not begin until another operation has completed even though no property reference expresses that relationship.
   - Correct principle: CloudFormation infers dependencies from references such as `Ref`, `GetAtt`, and substitutions; add `DependsOn` only for an additional ordering requirement that CloudFormation cannot infer, because unnecessary explicit dependencies reduce parallelism.
   - Three plausible distractor concepts: (1) add `DependsOn` between every pair of resources to make the stack reliable; (2) rely on YAML declaration order as the creation order; (3) use stack outputs to force same-stack creation dependencies.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.1`
   - Official source keys: `EX-SAA2, EX-SAP2, CFN-CORE, CFN-DEPEND`

4. **Intent — Design stack boundaries around ownership and failure scope.**
   - Hard constraint: Shared networking, stateful data, and frequently deployed application resources have different owners and change rates, and one application update must not unnecessarily endanger all layers.
   - Correct principle: Split stacks by lifecycle, ownership, and blast radius; use nested stacks for composition under one root lifecycle and stable outputs/interfaces between independently operated stacks, while avoiding circular cross-stack dependencies.
   - Three plausible distractor concepts: (1) put the entire organization in one stack so rollback is atomic; (2) create a nested stack whenever resources are in different files, regardless of ownership; (3) couple stacks with bidirectional exports so each can update the other.
   - Task mapping: `SAP-C02 SAP-2.1, SAP-3.1`
   - Official source keys: `EX-SAP2, EX-SAP3, CFN-NESTED, CFN-BEST`

5. **Intent — Choose the correct StackSets permission and rollout model.**
   - Hard constraint: A baseline must reach many accounts and Regions with bounded concurrent impact, delegated administration, and behavior for newly added organization accounts.
   - Correct principle: Use service-managed permissions with AWS Organizations when automatic account/OU targeting and trusted access fit; use self-managed permissions when explicitly managed administration/execution roles are required, and set concurrency and failure tolerance to limit blast radius.
   - Three plausible distractor concepts: (1) use one ordinary stack in the management account to create resources in every member account; (2) set maximum concurrency with zero failure tolerance for the fastest safe production rollout; (3) assume adding an account to an OU updates self-managed StackSets automatically.
   - Task mapping: `SAA-C03 SAA-1.1, SAA-2.2 | SAP-C02 SAP-2.1`
   - Official source keys: `EX-SAA1, EX-SAA2, EX-SAP2, CFN-STACKSETS`

6. **Intent — Account for the CDK bootstrap and asset publishing boundary.**
   - Hard constraint: A pipeline must deploy CDK applications across accounts and Regions without developer credentials or ad hoc asset buckets.
   - Correct principle: Bootstrap each target environment with the required trusted roles and asset resources, restrict which principals/accounts may use them, and publish synthesized templates and assets through the deployment pipeline before CloudFormation execution.
   - Three plausible distractor concepts: (1) the CDK CLI can deploy cross-account without target bootstrap resources; (2) store permanent production access keys in the source repository; (3) share one public asset bucket across all accounts to avoid KMS and role configuration.
   - Task mapping: `SAP-C02 SAP-2.1, SAP-2.3`
   - Official source keys: `EX-SAP2, CDK-CORE, CDK-BOOTSTRAP, CP-XACCOUNT`

7. **Intent — Apply syntax, policy, and change checks at the correct stages.**
   - Hard constraint: A pipeline must reject malformed templates and organization-policy violations before production, but a passed static check must not be represented as proof that deployment will succeed.
   - Correct principle: Perform template parsing/validation, policy-as-code checks such as CloudFormation Guard, synthesis tests, and a change-set review as separate controls; retain integration and post-deployment validation because static checks cannot prove service quotas, permissions, or runtime behavior.
   - Three plausible distractor concepts: (1) a successful template validation proves every resource property is deployable; (2) a change set replaces policy-as-code because both show proposed resources; (3) run compliance checks only after production so they evaluate actual resources.
   - Task mapping: `SAP-C02 SAP-2.1, SAP-3.1, SAP-3.2`
   - Official source keys: `EX-SAP2, EX-SAP3, CFN-GUARD, CFN-CHANGESET, CFN-BEST`

8. **Intent — Promote one reviewed template and artifact set through environments.**
   - Hard constraint: Audit evidence must show that the production infrastructure definition is the same reviewed build tested in staging, with only approved environment parameters changing.
   - Correct principle: Version and immutably store the synthesized template and referenced assets, promote that same revision through pipeline stages, and inject controlled environment configuration rather than resynthesizing or rebuilding from a moving branch in production.
   - Three plausible distractor concepts: (1) resynthesize from the latest main branch at each environment; (2) patch the production template in the console after approval; (3) rebuild artifacts separately in production so they contain production-specific code.
   - Task mapping: `SAP-C02 SAP-2.1, SAP-3.1`
   - Official source keys: `EX-SAP2, EX-SAP3, CP-CONCEPTS, CP-CFN, CFN-BEST`

9. **Intent — Expose stack outputs without leaking or overcoupling state.**
   - Hard constraint: Downstream deployment stages need stable identifiers, but secrets and frequently changing implementation details must not become globally coupled exports.
   - Correct principle: Use outputs for non-sensitive values needed by operators or automation, and use cross-stack exports only for stable same-Region interfaces with clear ownership; keep secrets in dedicated secret stores and avoid export relationships that block safe replacement.
   - Three plausible distractor concepts: (1) output plaintext secrets because stack outputs are visible only to CloudFormation; (2) export every resource ARN to make all stacks reusable; (3) use outputs as a runtime configuration database with independent write semantics.
   - Task mapping: `SAA-C03 SAA-1.2, SAA-2.2 | SAP-C02 SAP-2.1`
   - Official source keys: `EX-SAA1, EX-SAA2, EX-SAP2, CFN-TEMPLATE, CFN-DYNREF, CFN-BEST`

10. **Intent — Diagnose a failed IaC deployment from authoritative events and dependency state.**
   - Hard constraint: A stack deployment failed midway, and responders must identify the first causal failure without assuming the last rollback event is the root cause.
   - Correct principle: Inspect stack and resource events in time order, follow dependency failures back to the earliest service/API error, verify permissions, quotas, parameters, and custom-resource behavior, and preserve logs/evidence before retrying a corrected version.
   - Three plausible distractor concepts: (1) recreate the stack repeatedly until eventual consistency resolves every error; (2) treat all `UPDATE_FAILED` resources as independent root causes; (3) disable rollback in production so failed resources remain usable.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.1, SAP-3.1`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, CFN-CORE, CFN-BEST`

---

## Chapter 73 — Change Sets, Drift, and Rollback

### Current-question defects

- **Ambiguous — Question 2:** the marked generic CloudFormation settings and the rejected chapter-specific change-set controls can both be necessary; the stem does not establish why the generic bundle is the single best answer.
- **Ambiguous/incorrectly scored — Question 3:** option B correctly describes the CloudFormation state engine, while option C correctly describes change-set comparison. Asking broadly for the CloudFormation mechanism leaves both true.
- **Incorrect/low-density — Question 4:** the marked answer does not require a change set even though the hard constraint is previewing replacement and deletion before execution.
- **Incorrect/incomplete — Questions 1 and 5:** stack policy, `DeletionPolicy`, and `UpdateReplacePolicy` are collapsed into one protection concept. They govern different operations and cannot be substituted for one another.
- **Overclaim — drift wording:** the questions imply drift detection proves all manual or runtime differences are known. Coverage depends on resource support and explicitly modeled properties.
- **Low-density — Question 5:** generic canary/governance language is repeated instead of testing rollback triggers, retained-resource ownership, import, failed rollback recovery, or external side effects.
- **Coverage gap:** no current question tests the no-change-set-success guarantee, nested changes, drift-aware reconciliation, termination protection, snapshot applicability, resource import, or `ContinueUpdateRollback`.

### Ten knowledge-coverage audit intents

1. **Intent — Treat a change set as a preview, not an execution guarantee.**
   - Hard constraint: A production update can replace a stateful resource and must be reviewed before any mutation occurs.
   - Correct principle: Create and inspect a change set for additions, modifications, replacements, and removals; require approval for destructive impact, but still validate permissions, quotas, service behavior, and runtime health because successful change-set creation does not guarantee successful execution.
   - Three plausible distractor concepts: (1) execute every successfully created change set because rollback makes it risk-free; (2) use drift detection instead of a change set to predict template updates; (3) infer data preservation solely from a resource's `Modify` label.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.1, SAP-3.1`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, CFN-CHANGESET`

2. **Intent — Review nested-stack impact at the level where changes execute.**
   - Hard constraint: A root-stack update changes nested templates, and reviewers must see child-resource replacements rather than approving only a parent template URL change.
   - Correct principle: Include nested stacks in change-set analysis when supported and inspect child changes and dependency order; do not assume a root-level summary exposes every stateful replacement or that child failures are isolated from the root operation.
   - Three plausible distractor concepts: (1) approve only the root stack because nested stacks have independent rollback; (2) update child stacks directly whenever the root change set is too large; (3) assume changing a nested template URL never changes child resources.
   - Task mapping: `SAP-C02 SAP-2.1, SAP-3.1`
   - Official source keys: `EX-SAP2, EX-SAP3, CFN-CHANGESET, CFN-NESTED`

3. **Intent — Interpret drift detection within its support and modeling limits.**
   - Hard constraint: An audit requires evidence about console changes, but the workload includes resource types and default properties that might not be fully represented in the template.
   - Correct principle: Use drift detection to compare supported resources and explicitly declared properties with expected configuration; treat `IN_SYNC` as scoped evidence, not proof of complete runtime correctness, implicit defaults, application state, or external-system consistency.
   - Three plausible distractor concepts: (1) `IN_SYNC` proves no human changed any AWS setting; (2) drift detection compares application data and third-party dependencies; (3) omit important properties from the template so drift detection uses service defaults as the desired state.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-3.1, SAP-3.2`
   - Official source keys: `EX-SAA2, EX-SAP3, CFN-DRIFT`

4. **Intent — Reconcile drift by choosing an authoritative source explicitly.**
   - Hard constraint: A production console change fixed an incident, and blindly reverting it or silently accepting it could each cause another outage.
   - Correct principle: Determine whether the reviewed IaC definition or the emergency live configuration should become authoritative, test the decision, then update the template/adopt actual state or deliberately revert the resource; use drift-aware change information where available and retain the incident rationale.
   - Three plausible distractor concepts: (1) always overwrite live state from source control immediately; (2) always edit the template to match any console change; (3) mark the drift exception resolved without changing either source or resource.
   - Task mapping: `SAP-C02 SAP-3.1, SAP-3.2, SAP-3.4`
   - Official source keys: `EX-SAP3, CFN-DRIFT, CFN-DRIFT-AWARE, CFN-CHANGESET`

5. **Intent — Use stack policies for update restrictions, not deletion retention.**
   - Hard constraint: Normal application resources may update, but specified stateful resources require an explicit temporary override before CloudFormation can update or replace them.
   - Correct principle: Apply a stack policy to deny selected update actions and use a narrowly scoped temporary override when an approved update is needed; recognize that stack policies do not protect resources from stack deletion and do not define retained physical-resource behavior.
   - Three plausible distractor concepts: (1) a stack policy retains all protected resources when the stack is deleted; (2) `DeletionPolicy` blocks property updates to a resource; (3) termination protection is a per-resource update allowlist.
   - Task mapping: `SAA-C03 SAA-1.3, SAA-2.2 | SAP-C02 SAP-2.1, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAA2, EX-SAP2, EX-SAP3, CFN-STACKPOLICY`

6. **Intent — Distinguish `DeletionPolicy` from `UpdateReplacePolicy`.**
   - Hard constraint: A database must be preserved both when removed from the template and when an update requires replacement of its physical resource.
   - Correct principle: Configure `DeletionPolicy` for deletion caused by stack deletion or template removal and `UpdateReplacePolicy` for the old physical resource during replacement; set both when both paths require retention or a supported snapshot.
   - Three plausible distractor concepts: (1) `DeletionPolicy: Retain` automatically governs replacement; (2) `UpdateReplacePolicy` protects a resource removed from the template; (3) either attribute prevents CloudFormation from creating the replacement resource.
   - Task mapping: `SAA-C03 SAA-1.3, SAA-2.2 | SAP-C02 SAP-2.1, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAA2, EX-SAP2, EX-SAP3, CFN-DELETE, CFN-REPLACE`

7. **Intent — Assign ownership and lifecycle for retained or snapshotted resources.**
   - Hard constraint: Retained databases and snapshots must not become untracked, unpatched, or indefinitely billed after their stack relationship ends.
   - Correct principle: Treat retention as transfer of lifecycle responsibility: record the physical resource, encryption key, access owner, backup/retention schedule, cleanup decision, and import or migration plan; use `Snapshot` only for resource types that support that behavior.
   - Three plausible distractor concepts: (1) retained resources remain fully managed by the deleted stack; (2) every CloudFormation resource supports `Snapshot`; (3) retention automatically copies data to another account and rotates its KMS key.
   - Task mapping: `SAA-C03 SAA-1.3 | SAP-C02 SAP-2.1, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAP2, EX-SAP3, CFN-DELETE, CFN-REPLACE, CFN-IMPORT`

8. **Intent — Separate stack termination protection from resource lifecycle policies.**
   - Hard constraint: Operators must be prevented from accidentally deleting a production stack, while an approved update still needs normal resource-level controls.
   - Correct principle: Enable termination protection to block stack deletion through CloudFormation, and separately use stack policies and deletion/update-replacement policies for update and resource disposition; protect nested-stack deletion through the root stack's controls.
   - Three plausible distractor concepts: (1) termination protection prevents all updates and replacements; (2) a stack policy blocks the `DeleteStack` operation; (3) termination protection guarantees retained data if it is disabled before deletion.
   - Task mapping: `SAA-C03 SAA-1.3, SAA-2.2 | SAP-C02 SAP-2.1, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAA2, EX-SAP2, EX-SAP3, CFN-TERM, CFN-STACKPOLICY, CFN-DELETE`

9. **Intent — Use rollback triggers as bounded health evidence.**
   - Hard constraint: A stack update may complete at the control plane while customer error rate breaches an agreed threshold shortly afterward.
   - Correct principle: Associate appropriate CloudWatch alarms as rollback triggers and choose a monitoring window that can observe the failure mode; ensure missing-data behavior and alarm dimensions are deliberate, while recognizing rollback cannot undo committed data or external side effects.
   - Three plausible distractor concepts: (1) any alarm in the account automatically triggers stack rollback; (2) a rollback trigger monitors indefinitely after the update; (3) stack rollback reverses database writes and third-party API calls.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.1, SAP-3.1, SAP-3.4`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, CFN-ROLLBACK, CW-ALARMS`

10. **Intent — Recover safely from `UPDATE_ROLLBACK_FAILED`.**
   - Hard constraint: Rollback is blocked because one resource cannot return to its prior state, but responders must restore stack operability without falsely declaring skipped resources healthy.
   - Correct principle: Correct the underlying permission, dependency, or resource condition first when possible, then continue rollback; skip only the minimum necessary resources, understand they can be inconsistent with the template, and reconcile or import them before the next update.
   - Three plausible distractor concepts: (1) skip every failed resource to force the stack to `UPDATE_ROLLBACK_COMPLETE`; (2) delete the stack immediately because continued rollback cannot preserve resources; (3) treat skipped resources as automatically synchronized with the previous template.
   - Task mapping: `SAP-C02 SAP-2.1, SAP-3.1, SAP-3.4`
   - Official source keys: `EX-SAP2, EX-SAP3, CFN-CONTINUE, CFN-DRIFT, CFN-IMPORT`

---

## Chapter 74 — Blue/Green, Canary, and Rolling Deployment

### Current-question defects

- **Ambiguous/incorrectly scored — Question 1:** option D's expand/contract database principle is required by the stated old/new schema compatibility constraint, yet it is rejected as merely adjacent.
- **Low-density — Question 1:** the marked answer is a strategy taxonomy and does not require a compute platform, traffic increment, bake time, health signal, stop condition, or blue-environment retention period.
- **Low-density/duplicate — Questions 2 and 4:** both test the same CodeDeploy configuration bundle without distinguishing EC2/on-premises in-place deployment, EC2/ECS blue/green deployment, or Lambda alias traffic shifting.
- **Ambiguous/incorrectly scored — Question 5:** the database compatibility principle is again rejected even though traffic reversal can fail when the previous application cannot use the new schema.
- **Incorrect implication — rollback wording:** retaining the blue environment can reverse compute traffic quickly, but it cannot reverse writes, messages, schema migrations, or third-party effects.
- **Coverage gap:** CodePipeline stage design, immutable artifacts, cross-account roles and artifact keys, realistic alarms, bake time, lifecycle hooks, termination wait, approval evidence, and forward-compatible data changes are absent.

### Ten knowledge-coverage audit intents

1. **Intent — Select all-at-once or rolling deployment from capacity and mixed-version constraints.**
   - Hard constraint: The fleet cannot afford full duplicate capacity, but it must retain enough serving capacity and tolerate a bounded period with old and new versions running together.
   - Correct principle: Use a rolling deployment with batch size and minimum healthy capacity chosen from load headroom and version compatibility; use all-at-once only when downtime or total simultaneous exposure is explicitly acceptable.
   - Three plausible distractor concepts: (1) rolling deployment never mixes application versions; (2) all-at-once provides the smallest release blast radius; (3) choose the largest batch solely to minimize deployment duration.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.1, SAP-3.1`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, CD-DEPLOYCFG, CD-EC2`

2. **Intent — Choose blue/green when fast traffic reversal justifies duplicate capacity.**
   - Hard constraint: The release requires near-zero interruption and a rapid application-tier reversal, and the business accepts temporary parallel-environment cost.
   - Correct principle: Provision and validate a replacement environment, shift traffic only after readiness checks, retain the original environment for the agreed observation/termination interval, and price the duplicate capacity and state synchronization explicitly.
   - Three plausible distractor concepts: (1) blue/green uses no additional capacity; (2) deleting blue immediately after cutover preserves fast rollback; (3) traffic reversal automatically reverses data written while green served requests.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.1, SAP-3.4`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, CD-BLUEGREEN, WA-CHANGE`

3. **Intent — Bound unknown release risk with canary or linear traffic shifting.**
   - Hard constraint: A defect is expected to appear only under production traffic, but initial customer exposure must be limited and evaluated before broader rollout.
   - Correct principle: Shift a small traffic percentage, observe for a failure-mode-appropriate bake period using technical and business alarms, then continue linearly or complete the shift only if stop criteria remain healthy.
   - Three plausible distractor concepts: (1) a 1% canary needs no bake period because exposure is small; (2) use deployment completion status as the only canary health signal; (3) increase traffic on a fixed timer even while alarms are breaching.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.1, SAP-3.1, SAP-3.3`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, CD-DEPLOYCFG, CD-ALARMS, WA-ROLLBACK`

4. **Intent — Apply Lambda version-and-alias semantics to a deployment.**
   - Hard constraint: A serverless release needs weighted traffic between immutable revisions and automatic reversal without changing clients.
   - Correct principle: Publish an immutable Lambda version, route an alias between the current and target versions through CodeDeploy, run configured validation hooks, and use alarms/rollback to restore alias traffic; do not treat `$LATEST` as an immutable release.
   - Three plausible distractor concepts: (1) split production traffic directly between two `$LATEST` revisions; (2) changing an environment variable on a published version mutates that release; (3) a Lambda canary automatically migrates or reverses downstream data.
   - Task mapping: `SAA-C03 SAA-2.1, SAA-2.2 | SAP-C02 SAP-2.1`
   - Official source keys: `EX-SAA2, EX-SAP2, CD-LAMBDA, CD-ROLLBACK`

5. **Intent — Model an ECS blue/green deployment with target groups and validation hooks.**
   - Hard constraint: New tasks must be tested before production traffic, production traffic must switch through the load balancer, and failed validation must not leave both task sets ambiguously active.
   - Correct principle: Use distinct original and replacement task sets/target groups, optional test traffic for validation, lifecycle hooks at the correct phases, production traffic shifting, alarms, and an explicit original-task-set termination interval.
   - Three plausible distractor concepts: (1) register old and new tasks in one target group and call it blue/green; (2) use an ALB health check as proof of complete business-flow correctness; (3) terminate the original task set before production traffic reaches green.
   - Task mapping: `SAA-C03 SAA-2.1, SAA-2.2 | SAP-C02 SAP-2.1, SAP-3.1`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, CD-BLUEGREEN, CD-ALARMS`

6. **Intent — Distinguish EC2/on-premises in-place and blue/green deployment mechanics.**
   - Hard constraint: A legacy fleet has local state and limited spare capacity, while another stateless fleet can be replaced behind a load balancer.
   - Correct principle: Use in-place deployment only when updating existing instances and its temporary capacity/version effects are acceptable; prefer blue/green replacement for stateless fleets when clean rollback, immutable hosts, and extra capacity are acceptable, with a tested agent/AppSpec lifecycle.
   - Three plausible distractor concepts: (1) CodeDeploy in-place creates a complete replacement Auto Scaling group automatically; (2) blue/green is always safer for state stored only on instance disks; (3) AppSpec hooks remove the need for load balancer health checks.
   - Task mapping: `SAP-C02 SAP-2.1, SAP-3.1, SAP-3.4`
   - Official source keys: `EX-SAP2, EX-SAP3, CD-EC2, CD-BLUEGREEN`

7. **Intent — Build once and promote the same immutable application revision.**
   - Hard constraint: Production must run the exact binary/container revision that passed lower-environment tests, not a rebuild from equivalent source.
   - Correct principle: Produce a versioned immutable artifact once, record its digest/revision and test evidence, and promote that artifact through pipeline stages with environment configuration kept external; do not rebuild at the production boundary.
   - Three plausible distractor concepts: (1) rebuild in each account because identical source guarantees identical output; (2) overwrite the artifact under a stable key after approval; (3) bake production credentials into the artifact so no deployment role is needed.
   - Task mapping: `SAP-C02 SAP-2.1, SAP-3.1`
   - Official source keys: `EX-SAP2, EX-SAP3, CP-CONCEPTS, WA-CHANGE`

8. **Intent — Secure cross-account deployment roles, artifacts, and encryption keys.**
   - Hard constraint: A tooling account deploys to staging and production accounts, and neither the build service nor developers may hold permanent production credentials.
   - Correct principle: Use narrowly trusted cross-account roles, explicit artifact-bucket and KMS-key permissions, separation of pipeline and target-account privileges, and approval where required; ensure each action can read the exact input artifact it is authorized to deploy.
   - Three plausible distractor concepts: (1) store an IAM user's production access keys in CodeBuild environment variables; (2) grant the tooling account administrator access to every target account; (3) use the default artifact encryption key without checking cross-account key policy access.
   - Task mapping: `SAA-C03 SAA-1.1 | SAP-C02 SAP-2.1, SAP-2.3`
   - Official source keys: `EX-SAA1, EX-SAP2, CP-XACCOUNT, CP-CONCEPTS`

9. **Intent — Preserve old/new application compatibility across data changes.**
   - Hard constraint: Traffic may reach either application version during rollout or rollback, and both versions share a mutable database and event stream.
   - Correct principle: Use expand/contract changes: add backward-compatible structures first, deploy code that tolerates both forms, migrate/backfill safely, stop old writers/readers, then remove obsolete structures in a later release; plan compensation for irreversible side effects.
   - Three plausible distractor concepts: (1) drop or rename the old column in the same step as the canary starts; (2) blue/green compute makes database rollback automatic; (3) replay every emitted event after rollback without idempotency analysis.
   - Task mapping: `SAP-C02 SAP-2.1, SAP-3.1, SAP-3.4`
   - Official source keys: `EX-SAP2, EX-SAP3, WA-CHANGE, WA-ROLLBACK`

10. **Intent — Define automatic rollback from customer-impact and technical evidence.**
   - Hard constraint: A release can pass host health checks while payment success falls, and the response must occur within a stated time without oscillating on noisy metrics.
   - Correct principle: Combine business outcome, latency/error, dependency, and saturation signals with deliberate periods, thresholds, missing-data behavior, and bake time; connect appropriate alarms to deployment rollback and preserve evidence for diagnosis.
   - Three plausible distractor concepts: (1) use CPU utilization alone for every deployment; (2) roll back whenever any single request fails; (3) trust a successful CodeDeploy status as proof that customers are unaffected.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.1, SAP-3.1, SAP-3.3`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, CD-ALARMS, CD-ROLLBACK, CW-ALARMS, WA-ROLLBACK`

---

## Chapter 75 — Systems Manager, Patching, and Fleet Management

### Current-question defects

- **Low-density — Question 1:** it lists five Systems Manager capabilities without testing managed-node identity, agent health, service connectivity, OS repository access, or target selection.
- **Ambiguous — Question 2:** both the broad Systems Manager settings and Session Manager-specific security/logging settings are relevant to the private-fleet scenario.
- **Overgeneralized — Question 3:** all behavior is summarized as the agent polling a control plane; feature-specific channels, permissions, endpoints, and logging limits are not tested.
- **Incorrectly weak distractor — Question 4:** Patch Manager is dismissed despite the emergency patch requirement. The meaningful distinction is patch orchestration versus interactive administration.
- **Ambiguous — Question 5:** immutable replacement is rejected even though it is often preferable for stateless fleets and the stem does not require in-place patching.
- **Low-density — Questions 4 and 5:** the chapter summary and generic governance answer repeat earlier material instead of testing concurrency, failure thresholds, reboot behavior, patch evidence, or failed-wave recovery.
- **Coverage gap:** scan versus install, patch policies/baselines, Quick Setup, maintenance windows, Inventory, State Manager, Session Manager tunnel logging limits, and repository reachability are absent.

### Ten knowledge-coverage audit intents

1. **Intent — Establish every prerequisite for a managed node.**
   - Hard constraint: Private EC2 and hybrid servers must be managed without inbound administration ports, but installing an agent alone is insufficient.
   - Correct principle: Provide a supported/current SSM Agent, a valid instance profile or hybrid activation identity, least-privilege Systems Manager permissions, correct time/DNS, and outbound HTTPS reachability to the required service endpoints before expecting management operations to work.
   - Three plausible distractor concepts: (1) open inbound TCP 443 from administrators to each node; (2) install SSM Agent without an IAM identity; (3) attach an IAM role only to the human operator and assume the node inherits it.
   - Task mapping: `SAA-C03 SAA-1.2 | SAP-C02 SAP-2.1, SAP-2.3`
   - Official source keys: `EX-SAA1, EX-SAP2, SSM-NODE, SSM-VPCE`

2. **Intent — Separate Systems Manager control connectivity from operating-system repository access.**
   - Hard constraint: Nodes have private Systems Manager endpoints but patch installation still fails while downloading packages.
   - Correct principle: Verify both the Systems Manager service channels and access to each operating system's configured patch repositories or approved mirrors; VPC endpoints for Systems Manager do not automatically provide Linux/Windows package content.
   - Three plausible distractor concepts: (1) Systems Manager VPC endpoints mirror every OS vendor repository; (2) successful Session Manager access proves patch payloads are reachable; (3) add an inbound security-group rule so the package manager can receive updates.
   - Task mapping: `SAA-C03 SAA-1.2 | SAP-C02 SAP-2.3, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAP2, EX-SAP3, SSM-VPCE, SSM-PATCHACTION`

3. **Intent — Choose Session Manager for interactive access while respecting logging limits.**
   - Hard constraint: Administrators need audited emergency shell access without bastions or shared SSH keys, and the audit statement must accurately describe which session content can be logged.
   - Correct principle: Use Session Manager with IAM-controlled access and configured CloudWatch Logs/S3 destinations for supported shell sessions; do not claim command-content logging for SSH or port-forwarding sessions because those encrypted tunnels are not inspectable by Session Manager logging.
   - Three plausible distractor concepts: (1) Session Manager requires an inbound SSH rule; (2) enabling S3 logging records all port-forwarded database traffic; (3) share one IAM principal because the session transcript identifies the OS user.
   - Task mapping: `SAA-C03 SAA-1.1, SAA-1.2 | SAP-C02 SAP-2.3, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAP2, EX-SAP3, SSM-SESSION, SSM-SESSIONLOG`

4. **Intent — Bound Run Command blast radius with concurrency and error controls.**
   - Hard constraint: A command must run on thousands of nodes, but simultaneous execution and cascading failure must remain below specified fleet percentages.
   - Correct principle: Target nodes by governed tags/resource groups, set `max-concurrency` and `max-errors` as appropriate numbers or percentages, begin with a canary cohort, and collect per-target invocation status and command output.
   - Three plausible distractor concepts: (1) target all nodes with unlimited concurrency because Run Command is managed; (2) set `max-errors` to the fleet size so the command always completes; (3) use Session Manager interactively on every node for better consistency.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.1, SAP-3.1, SAP-3.2`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, SSM-RUNCOMMAND`

5. **Intent — Select Inventory, State Manager, Run Command, or Maintenance Windows by responsibility.**
   - Hard constraint: The team separately needs fleet facts, continuously enforced configuration, an immediate one-time action, and disruptive work in an approved period.
   - Correct principle: Use Inventory to collect metadata, State Manager associations to maintain desired configuration/compliance, Run Command for controlled commands, and Maintenance Windows for scheduled disruptive tasks with duration, targets, tasks, concurrency, and error thresholds.
   - Three plausible distractor concepts: (1) use Inventory to change package state; (2) use Run Command as a durable desired-state declaration; (3) use a Maintenance Window as an interactive shell gateway.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.1, SAP-3.1`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, SSM-INVENTORY, SSM-STATE, SSM-MW, SSM-STATE-MW`

6. **Intent — Define patch approval policy independently from execution scheduling.**
   - Hard constraint: Security requires delayed automatic approval for normal updates, explicit rejection of a problematic patch, and separate treatment by operating system/product.
   - Correct principle: Use predefined or custom patch baselines/policies to define approved, rejected, and approval-delay rules per supported OS/product, and use a schedule or maintenance window to decide when scans or installations execute.
   - Three plausible distractor concepts: (1) a maintenance window decides which CVEs are approved; (2) approving a patch in a baseline installs it immediately on every node; (3) one Linux baseline can classify Windows updates identically.
   - Task mapping: `SAA-C03 SAA-1.2 | SAP-C02 SAP-2.3, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAP2, EX-SAP3, SSM-PATCHBASE, SSM-PATCHPOLICY`

7. **Intent — Distinguish patch scan, install, and reboot evidence.**
   - Hard constraint: An audit asks whether required updates are installed and effective, not merely whether a scan command succeeded.
   - Correct principle: Use scan to classify compliance without installation, use install to apply approved patches, choose reboot behavior deliberately, and verify post-reboot application health and patch compliance because a successful scan is not proof of installation.
   - Three plausible distractor concepts: (1) `Scan` remediates every missing approved patch; (2) `NoReboot` means every installed patch is fully active; (3) command success proves the application restarted and serves traffic.
   - Task mapping: `SAA-C03 SAA-1.2 | SAP-C02 SAP-2.3, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAP2, EX-SAP3, SSM-PATCHACTION, SSM-COMPLIANCE`

8. **Intent — Execute patch waves without violating workload availability.**
   - Hard constraint: A clustered service must remain above minimum healthy capacity while nodes drain, patch, reboot, and rejoin.
   - Correct principle: Patch a canary wave first, coordinate load balancer/cluster drain and health validation, set maintenance-window concurrency/error thresholds below failure tolerance, reserve enough capacity, and stop promotion when application-level checks fail.
   - Three plausible distractor concepts: (1) patch one node per Availability Zone only after taking every other node offline; (2) rely on patch-command success instead of service health; (3) patch 100% concurrently because Multi-AZ automatically preserves all quorum and capacity constraints.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.3, SAP-3.1, SAP-3.4`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, SSM-MW, SSM-STATE-MW, SSM-PATCHACTION`

9. **Intent — Govern patch policies across accounts and Regions.**
   - Hard constraint: An organization needs centrally defined patch schedules and compliance visibility while member-account roles and target scope remain least privilege.
   - Correct principle: Use Systems Manager Quick Setup patch policies with the intended organization/OUs, Regions, targeting, baseline, schedule, and reboot configuration; delegate administration deliberately and monitor configuration deployment plus node compliance.
   - Three plausible distractor concepts: (1) one maintenance window in the management account directly patches all member accounts; (2) organization targeting removes the need for managed-node roles and connectivity; (3) delete a referenced custom baseline without updating the patch policy.
   - Task mapping: `SAA-C03 SAA-1.1 | SAP-C02 SAP-2.1, SAP-2.3, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAP2, EX-SAP3, SSM-QUICKSETUP, SSM-PATCHPOLICY, SSM-COMPLIANCE`

10. **Intent — Choose immutable replacement or in-place patching from workload state.**
   - Hard constraint: Stateless Auto Scaling nodes can be replaced from a tested image, while legacy/stateful nodes cannot all be rebuilt within the maintenance deadline.
   - Correct principle: Prefer rebuilding and replacing stateless nodes from a patched, tested image when it reduces drift and rollback complexity; use controlled in-place patching for nodes that cannot yet be replaced, with backup, canary, health, and recovery plans appropriate to their state.
   - Three plausible distractor concepts: (1) in-place patch every node because Patch Manager is always lower risk; (2) terminate a stateful node before verifying durable external state; (3) assume every OS patch can be cleanly uninstalled as rollback.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.1, SAP-2.3, SAP-3.2, SAP-3.4`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, SSM-PATCHPOLICY, SSM-PATCHACTION, WA-CHANGE`

---

## Chapter 76 — Event-driven Remediation

### Current-question defects

- **Low-density — Question 1:** the marked answer bundles Config, CloudTrail, EventBridge, Lambda, Automation, risk evaluation, remediation, and notification, so it does not test each service boundary.
- **Incorrectly rejected alternative — Questions 1 and 5:** approval and dry-run controls are treated as incompatible with fast remediation even though they are appropriate for ambiguous or destructive actions.
- **Incorrect category — Question 3:** AWS Config is presented as if it were in an application request/data path. It records/evaluates configuration state; CloudTrail supplies API activity and EventBridge routes events.
- **Incomplete/incorrect — Question 4:** selecting Config settings alone cannot guarantee minute-level containment without trigger latency, remediation target, IAM, retries, exceptions, and evidence.
- **Missing preventive control:** the public-S3 scenario omits account/organization S3 Block Public Access and frames detect-and-repair as preferable to prevention.
- **Low-density — Question 5:** generic governance is repeated while idempotency, duplicate events, stale evaluations, loops, dead-letter handling, and source-IaC correction are not tested.
- **Coverage gap:** direct service events versus CloudTrail-delivered events, Config aggregation versus enforcement, conformance packs, automatic-remediation caveats, and human approval boundaries are absent.

### Ten knowledge-coverage audit intents

1. **Intent — Prefer prevention when an unsafe state can be blocked authoritatively.**
   - Hard constraint: S3 public access must be impossible across an account or organization except through explicitly governed exceptions.
   - Correct principle: Apply S3 Block Public Access at the strongest appropriate boundary and use policy guardrails before relying on detective remediation; retain Config/CloudTrail/EventBridge for visibility, attribution, and exception monitoring.
   - Three plausible distractor concepts: (1) AWS Config prevents the public-access API call; (2) CloudTrail automatically reverses a bucket policy; (3) allow public access briefly and depend on a scheduled daily rule to remove it.
   - Task mapping: `SAA-C03 SAA-1.3 | SAP-C02 SAP-2.3, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAP2, EX-SAP3, S3-BPA, CONFIG-RULES, CT-EVENTS`

2. **Intent — Configure AWS Config scope before claiming complete configuration history.**
   - Hard constraint: Compliance evidence must cover the intended resource types, Regions, and accounts without silently excluding newly introduced resources.
   - Correct principle: Configure recorders and delivery appropriately in each required Region/account, choose recording scope deliberately, retain configuration history, and verify rule-supported resource types before treating Config as complete inventory or evidence.
   - Three plausible distractor concepts: (1) enabling Config in one Region records every global and regional resource everywhere; (2) creating a rule automatically starts recording all resources; (3) an aggregator creates missing configuration history in source accounts.
   - Task mapping: `SAA-C03 SAA-1.3 | SAP-C02 SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAP3, CONFIG-CORE, CONFIG-RULES, CONFIG-AGG`

3. **Intent — Select change-triggered or periodic compliance evaluation by detectable fact.**
   - Hard constraint: One control must react to supported configuration changes quickly, while another depends on a condition that is not emitted as a relevant configuration-item change.
   - Correct principle: Use change-triggered evaluation when relevant recorded resource changes can initiate the rule and periodic evaluation when compliance requires scheduled reassessment; match maximum execution frequency to the response objective and do not promise instantaneous enforcement.
   - Three plausible distractor concepts: (1) periodic Config rules block noncompliant API requests synchronously; (2) change-triggered rules continuously evaluate external business transactions; (3) set every rule periodic because it always has lower detection latency.
   - Task mapping: `SAA-C03 SAA-1.3, SAA-2.2 | SAP-C02 SAP-3.1, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAA2, EX-SAP3, CONFIG-RULES`

4. **Intent — Attribute actor, configuration state, and runtime impact to the correct evidence sources.**
   - Hard constraint: Responders must answer who changed a resource, what its configuration became, and whether customers were harmed.
   - Correct principle: Use CloudTrail for recorded API actor/request evidence, Config for resource configuration history and rule compliance, and CloudWatch/application telemetry for runtime health; correlate timestamps and identifiers rather than asking one service to prove all three.
   - Three plausible distractor concepts: (1) Config identifies every console user's complete session intent; (2) CloudTrail proves the application remained healthy after the change; (3) CloudWatch metrics preserve the full old and new IAM policy document automatically.
   - Task mapping: `SAA-C03 SAA-1.3, SAA-2.2 | SAP-C02 SAP-3.1, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAA2, EX-SAP3, CT-EVENTS, CONFIG-CORE, CW-AGENT`

5. **Intent — Distinguish direct EventBridge service events from CloudTrail-delivered API events.**
   - Hard constraint: A remediation needs the lowest practical detection latency and the exact event fields necessary to target the changed resource.
   - Correct principle: Prefer a native direct service event when it represents the required state transition; use CloudTrail-delivered events for supported API activity when actor/action evidence is the trigger, and test event patterns against actual schemas rather than assuming all AWS events arrive through one path.
   - Three plausible distractor concepts: (1) every AWS service event is delivered only after CloudTrail log-file publication; (2) EventBridge records long-term configuration history; (3) use a broad pattern matching every API call and let the target discover intent.
   - Task mapping: `SAA-C03 SAA-2.1 | SAP-C02 SAP-3.1, SAP-3.2`
   - Official source keys: `EX-SAA2, EX-SAP3, EB-DIRECT, EB-CLOUDTRAIL, CT-EVENTS`

6. **Intent — Use Config automatic remediation only for well-defined current state.**
   - Hard constraint: A known-safe action should correct a noncompliant resource automatically, but Config's compliance snapshot can become stale before the remediation executes.
   - Correct principle: Associate an idempotent SSM Automation document with least-privilege parameters and retry controls, re-check current state inside the automation before mutation, and record success/failure because automatic remediation can act from a stale evaluation.
   - Three plausible distractor concepts: (1) a Config remediation always receives a strongly consistent current resource state; (2) give the automation administrator access so parameter mapping cannot fail; (3) retry a destructive step indefinitely until compliance changes.
   - Task mapping: `SAA-C03 SAA-1.3 | SAP-C02 SAP-3.1, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAP3, CONFIG-REMED, CONFIG-AUTOREMED, SSM-AUTOMATION`

7. **Intent — Put human approval around ambiguous or high-impact remediation.**
   - Hard constraint: The detected state may be a legitimate exception, and automatic deletion or network isolation could cause a larger outage than the original issue.
   - Correct principle: Fully automate only bounded, reversible, well-understood actions; for destructive or context-dependent actions, gather evidence, perform dry-run/precondition checks, request an accountable approval, enforce timeout/escalation, and preserve the decision trail.
   - Three plausible distractor concepts: (1) all security findings must be remediated with no approval regardless of impact; (2) route every low-risk deterministic correction to a week-long change board; (3) approve based only on the resource name without current dependencies or exception data.
   - Task mapping: `SAP-C02 SAP-3.1, SAP-3.2`
   - Official source keys: `EX-SAP3, SSM-AUTOMATION, WA-RESPOND, WA-RUNBOOK`

8. **Intent — Make event-driven remediation idempotent and failure-aware.**
   - Hard constraint: Events can be duplicated, retried, delayed, or fail delivery, yet repeated handling must not corrupt state or silently lose the remediation.
   - Correct principle: Design the target to re-read current state and produce the same safe result on repeat invocation, configure retry age/attempts and an SQS dead-letter queue, alarm on failed/dropped delivery, and provide a controlled replay process.
   - Three plausible distractor concepts: (1) EventBridge guarantees exactly-once target execution; (2) disable retries to avoid duplicate changes and accept lost events; (3) use an in-memory Lambda flag as the durable deduplication record.
   - Task mapping: `SAA-C03 SAA-2.1, SAA-2.2 | SAP-C02 SAP-3.1, SAP-3.2, SAP-3.4`
   - Official source keys: `EX-SAA2, EX-SAP3, EB-RETRY, EB-DLQ, LAMBDA-IDEMPOTENT`

9. **Intent — Prevent remediation loops and preserve approved exceptions.**
   - Hard constraint: An IaC deployment repeatedly recreates a setting that automation removes, and some resources have time-bounded approved exceptions.
   - Correct principle: Detect loop signatures, exclude or encode approved exceptions with owner/expiry, stop after bounded retries, notify the source owner, and correct the authoritative IaC/policy or workflow instead of continuously fighting it at runtime.
   - Three plausible distractor concepts: (1) increase EventBridge retry attempts until the remediation wins permanently; (2) disable all compliance evaluation for the affected resource type; (3) store exceptions as permanent free-text tags with no owner or expiration.
   - Task mapping: `SAP-C02 SAP-3.1, SAP-3.2, SAP-3.4`
   - Official source keys: `EX-SAP3, CONFIG-AUTOREMED, EB-RETRY, CFN-DRIFT, WA-EVOLVE`

10. **Intent — Separate organization-wide policy deployment, aggregation, and remediation authority.**
   - Hard constraint: A central security team needs common controls and visibility across accounts, but member workloads retain scoped remediation ownership and regional data sources.
   - Correct principle: Use organization conformance packs for common Config rule/remediation definitions where appropriate, aggregators for centralized compliance views, and explicitly delegated execution roles for remediation; an aggregator is read-oriented consolidation, not an enforcement engine.
   - Three plausible distractor concepts: (1) a Config aggregator automatically fixes every noncompliant member resource; (2) deploy a conformance pack only in the management account and assume regional member resources are evaluated; (3) give the central remediation role unrestricted access to all services because controls are organization-wide.
   - Task mapping: `SAA-C03 SAA-1.1 | SAP-C02 SAP-2.3, SAP-3.1, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAP2, EX-SAP3, CONFIG-ORG, CONFIG-AGG, CONFIG-REMED`

---

## Chapter 77 — Backup, Restore Testing, and Game Day

### Current-question defects

- **Ambiguous — Question 1:** automated restore validation and a guarded game day are complementary, but the game-day option is rejected despite the requirement to prove an end-to-end payment recovery.
- **Overclaim — Questions 1, 2, and 4:** AWS Backup restore testing can automate resource restores, but application-level validation, DNS, secrets, event replay, and a business transaction require an explicit validation workflow.
- **Low-density — Question 3:** it tests where recovery points are written and copied, not whether recovery meets RTO/RPO or produces usable application state.
- **Ambiguous — Question 5:** the restore-validation, game-day, and governance actions can all be required, leaving more plausible correct actions than the marked select-two format allows.
- **Incorrect terminology:** “auditable rollback” is reused from deployment chapters, but backup coverage must distinguish restore, point-in-time recovery, failover, failback, and test cleanup.
- **Coverage gap:** backup windows, feature support, copy/KMS prerequisites, Vault Lock governance/compliance modes, restore roles, validation events, measured RTO, Audit Manager, and FIS stop conditions are not tested.

### Ten knowledge-coverage audit intents

1. **Intent — Translate RPO and retention into backup-plan behavior.**
   - Hard constraint: The business specifies maximum data loss and retention, and a nominal schedule that misses its start/completion window does not satisfy the objective.
   - Correct principle: Set backup frequency, start/completion windows, lifecycle, and retention from the required recovery-point objective and compliance policy; monitor job completion and the age of the latest usable recovery point rather than equating schedule configuration with achieved RPO.
   - Three plausible distractor concepts: (1) a daily schedule always proves a 24-hour RPO; (2) retention duration determines restore time; (3) a backup job that never started still counts because the rule was configured.
   - Task mapping: `SAA-C03 SAA-1.3, SAA-2.2 | SAP-C02 SAP-2.2, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAA2, EX-SAP2, EX-SAP3, BACKUP-PLANS`

2. **Intent — Design vault, encryption, and restore authority together.**
   - Hard constraint: Recovery points must be encrypted and recoverable by the designated recovery team even if workload administrators lose access or the original role is compromised.
   - Correct principle: Choose vault and KMS controls with service-specific encryption behavior, key policies, backup/restore roles, and recovery-account access tested end to end; do not create backups that the recovery authority cannot decrypt or restore.
   - Three plausible distractor concepts: (1) any AWS managed key can be shared across accounts without policy changes; (2) vault access permission automatically grants KMS decrypt permission; (3) use the compromised workload role as the only restore principal.
   - Task mapping: `SAA-C03 SAA-1.3 | SAP-C02 SAP-2.2, SAP-2.3, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAP2, EX-SAP3, BACKUP-ENCRYPT, BACKUP-RESTORE`

3. **Intent — Build a supported cross-account and cross-Region copy path.**
   - Hard constraint: A recovery point must survive source-account compromise and a Regional disruption, but copy support and encryption prerequisites vary by resource.
   - Correct principle: Verify the protected resource and backup type support the required copy, configure organization/account trust, destination vault and KMS permissions, schedule or on-demand copy, retention, and restore testing in the destination; do not assume copying is universal or transitive.
   - Three plausible distractor concepts: (1) every AWS Backup resource supports every cross-account cross-Region copy combination; (2) a source-account vault policy alone grants destination-key use; (3) a cross-Region replica is automatically an immutable cross-account backup.
   - Task mapping: `SAA-C03 SAA-1.3, SAA-2.2 | SAP-C02 SAP-2.2, SAP-3.2, SAP-3.4`
   - Official source keys: `EX-SAA1, EX-SAA2, EX-SAP2, EX-SAP3, BACKUP-XACCOUNT, BACKUP-ENCRYPT`

4. **Intent — Apply Vault Lock without confusing governance and compliance guarantees.**
   - Hard constraint: Recovery points require write-once-read-many retention, but the organization needs an explicit decision about whether privileged administrators may alter the lock during an initial governance period.
   - Correct principle: Choose Vault Lock mode and retention controls according to the immutability requirement, test the policy before an irreversible compliance-mode commitment, and preserve separate access/KMS/recovery procedures because Vault Lock does not by itself prove restorability.
   - Three plausible distractor concepts: (1) Vault Lock validates application data during restore; (2) compliance-mode settings can always be shortened later by the root user; (3) Vault Lock automatically copies recovery points to an isolated account.
   - Task mapping: `SAA-C03 SAA-1.3 | SAP-C02 SAP-2.2, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAP2, EX-SAP3, BACKUP-VAULTLOCK`

5. **Intent — Configure restore testing as a recurring resource-recovery control.**
   - Hard constraint: Selected protected resource types must be restored on a schedule from eligible recovery points without operators manually choosing each backup.
   - Correct principle: Create restore-testing plans and selections with the required frequency, recovery-point age, restore role, and restore metadata; verify supported resource behavior and monitor the resulting restore jobs and restore time.
   - Three plausible distractor concepts: (1) a backup plan automatically creates a restore-testing plan; (2) restore testing validates every application dependency without additional logic; (3) select the newest recovery point only and infer that older retained points are usable.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.2, SAP-3.4`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, BACKUP-RESTORETEST, BACKUP-RESTORE`

6. **Intent — Add event-driven validation to a completed restore test.**
   - Hard constraint: A resource-level restore can complete successfully while data integrity or application behavior remains invalid.
   - Correct principle: Match the restore-job completion event in EventBridge, invoke an explicit validation workflow, test data/application invariants, and report validation results back to AWS Backup within the validation window; preserve validation logs and failure evidence.
   - Three plausible distractor concepts: (1) `COMPLETED` restore status proves business transactions work; (2) run validation before the restored resource becomes available; (3) omit the validation result because AWS Backup infers it from Lambda success.
   - Task mapping: `SAA-C03 SAA-2.1, SAA-2.2 | SAP-C02 SAP-2.2, SAP-3.1, SAP-3.4`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, BACKUP-VALIDATE, BACKUP-RESTORETEST, EB-DIRECT`

7. **Intent — Isolate restore testing from production and clean up safely.**
   - Hard constraint: Recovery tests must not overwrite production, leak restored sensitive data, collide with DNS/network names, or leave expensive resources indefinitely.
   - Correct principle: Restore into an isolated account/VPC or otherwise separated environment with scoped credentials, masked access where required, deterministic naming and dependency configuration; use the restore-testing validation window and service cleanup behavior deliberately and verify deletion.
   - Three plausible distractor concepts: (1) restore over the production resource to prove the backup is current; (2) give validators production administrator access for convenience; (3) assume every restored resource is deleted immediately when its restore job reaches `COMPLETED`.
   - Task mapping: `SAA-C03 SAA-1.3, SAA-2.2 | SAP-C02 SAP-2.2, SAP-2.3, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAA2, EX-SAP2, EX-SAP3, BACKUP-RESTORETEST, BACKUP-VALIDATE`

8. **Intent — Measure application RTO and usable recovery, not only resource restore duration.**
   - Hard constraint: Audit evidence requires the complete payment path to be usable within the objective, including infrastructure, data, secrets, DNS, event processing, and capacity.
   - Correct principle: Timestamp the recovery declaration, restore/deploy dependencies in tested order, validate data and business transactions, measure achieved RTO and effective recovery point, reconcile/replay events safely, and record gaps plus corrective actions.
   - Three plausible distractor concepts: (1) use the database restore job duration as the complete application RTO; (2) stop timing when CloudFormation creates resources before traffic validation; (3) replay all queued events without checking duplicates or ordering.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.2, SAP-3.1, SAP-3.4`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, BACKUP-RESTORE, BACKUP-VALIDATE, RESILIENCE-HUB`

9. **Intent — Run a guarded game day for dependencies and human recovery procedures.**
   - Hard constraint: Automated restore testing does not prove detection, escalation, decision making, external dependencies, failover/failback, or on-call execution under incident conditions.
   - Correct principle: Define a hypothesis, scope, steady-state/customer metrics, owners, stop conditions, communications, and rollback/recovery actions; use FIS only for supported controlled fault injection, execute the runbook, measure outcomes, and perform cleanup/failback.
   - Three plausible distractor concepts: (1) use FIS instead of restoring backups to prove data recoverability; (2) run an unbounded production experiment without CloudWatch stop conditions; (3) call a tabletop discussion a successful technical restore test.
   - Task mapping: `SAP-C02 SAP-2.2, SAP-3.1, SAP-3.4`
   - Official source keys: `EX-SAP2, EX-SAP3, FIS-CORE, FIS-STOP, WA-RESPOND`

10. **Intent — Produce durable backup-compliance and recovery-test evidence.**
   - Hard constraint: Auditors need repeatable evidence of protected-resource coverage, job success, retention controls, restore validation, exceptions, and remediation ownership.
   - Correct principle: Use AWS Backup Audit Manager controls/reports plus job, vault, validation, and restore evidence; reconcile scope against inventory, document exceptions with owners and expiry, and track failed controls/tests to completion rather than treating a generated report as proof of application recovery.
   - Three plausible distractor concepts: (1) an Audit Manager compliant result proves every business transaction was restored; (2) report only successful backup jobs and omit unprotected resources; (3) close failed restore tests after rerunning the report without corrective work.
   - Task mapping: `SAA-C03 SAA-1.3 | SAP-C02 SAP-2.2, SAP-3.1, SAP-3.2`
   - Official source keys: `EX-SAA1, EX-SAP2, EX-SAP3, BACKUP-AUDIT, BACKUP-VALIDATE, WA-EVOLVE`

---

## Chapter 78 — Operational Excellence and Continuous Improvement

### Current-question defects

- **Incorrect attribution — Question 1:** the process is broadly sound, but the explanation credits the Well-Architected Tool with implementing ownership, SLOs, alarms, runbooks, and postmortems. The tool records reviews, risks, milestones, and improvements; teams and operating systems implement the practices.
- **Category error — Question 2:** workload metadata such as Regions, lenses, profiles, milestones, and sharing is said to determine runtime security, traffic, capacity, or data behavior.
- **Category error — Question 3:** the Well-Architected Tool is not in the request/data path. The CloudWatch option describes runtime telemetry, while the marked option describes a review workflow.
- **Incorrect/low-density — Question 4:** selecting the Well-Architected Tool cannot by itself reduce hundreds of noisy alarms or provide an actionable on-call response.
- **Ambiguous — Question 5:** the rejected statement that managed services reduce some toil but do not remove workload ownership is a correct operational principle compatible with both marked answers.
- **Obsolete-risk metadata — Question 5 explanation:** it maps to nonexistent `SAP-3.5` operational-excellence coverage; in SAP-C02, Task 3.5 is cost optimization. Operational excellence is Task 3.1.
- **Coverage gap:** customer-impact indicators, alarm actionability, logs/metrics/traces correlation, runbook versus playbook, operational readiness, deployment context, incident command, post-incident action ownership, and game-day learning are absent.

### Ten knowledge-coverage audit intents

1. **Intent — Assign operational ownership before production responsibility is ambiguous.**
   - Hard constraint: Multiple teams build and depend on the workload, but alerts and recovery actions require one accountable responder and explicit escalation at every hour.
   - Correct principle: Define service ownership, on-call coverage, dependency contacts, escalation paths, decision authority, and business communication responsibilities; managed services reduce selected toil but do not assume application outcomes, quotas, cost, security, or incident ownership.
   - Three plausible distractor concepts: (1) assign every alarm to a shared unowned channel; (2) rely on AWS Support as the primary application on-call team; (3) list all teams as equally accountable without a decision owner.
   - Task mapping: `SAP-C02 SAP-3.1`
   - Official source keys: `EX-SAP3, WA-OE, WA-RESPOND`

2. **Intent — Express repeatable operations and environment changes as reviewed code.**
   - Hard constraint: Routine recovery and maintenance actions vary by operator and leave incomplete evidence.
   - Correct principle: Version infrastructure, configuration, observability, and automation documents; review and test changes through controlled pipelines, make routine operations repeatable and reversible where possible, and preserve execution logs plus approvals.
   - Three plausible distractor concepts: (1) keep the authoritative runbook only in an engineer's shell history; (2) automate an unstable manual procedure before defining preconditions and stop criteria; (3) bypass review for operational code because it is not application code.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-2.1, SAP-3.1`
   - Official source keys: `EX-SAA2, EX-SAP2, EX-SAP3, WA-OE, SSM-AUTOMATION, CFN-BEST`

3. **Intent — Build observability from metrics, logs, and traces around workload questions.**
   - Hard constraint: Responders must distinguish a dependency bottleneck, application regression, and capacity saturation without paging on every raw metric.
   - Correct principle: Instrument relevant metrics, structured logs, and traces with correlation identifiers and consistent context; choose telemetry from explicit operational questions and retain it long enough for incident and trend analysis.
   - Three plausible distractor concepts: (1) collect only host CPU because managed services expose all application causes through it; (2) log every payload indefinitely without privacy or cost controls; (3) enable tracing but omit service/deployment identifiers needed for correlation.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-3.1, SAP-3.3`
   - Official source keys: `EX-SAA2, EX-SAP3, WA-OBSERVE, CW-AGENT`

4. **Intent — Define customer-facing indicators and objectives before tuning alarms.**
   - Hard constraint: Hundreds of infrastructure alarms fire while the team cannot state whether customers can complete the critical transaction.
   - Correct principle: Define measurable customer/business success indicators and objectives, relate component metrics to those outcomes, and use error-budget or objective risk to prioritize engineering and response; resource health alone is insufficient.
   - Three plausible distractor concepts: (1) use instance availability as the payment-success SLO; (2) page on every metric that deviates from its daily average; (3) define the objective after incidents so it matches observed performance.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-3.1, SAP-3.3`
   - Official source keys: `EX-SAA2, EX-SAP3, WA-OBSERVE, WA-OE`

5. **Intent — Make every page actionable and owned.**
   - Hard constraint: An alarm that wakes an operator must have a known customer/business impact, response, owner, and escalation, or it must not remain a page.
   - Correct principle: Set meaningful thresholds/windows/missing-data behavior, route to an accountable role, attach diagnostic and response context, test notification delivery, and demote/remove alarms that require no timely human or automated action.
   - Three plausible distractor concepts: (1) page on all warning-level events to avoid missing anything; (2) create alarms without runbooks because experts will remember the response; (3) leave permanently firing alarms active as dashboard indicators.
   - Task mapping: `SAP-C02 SAP-3.1`
   - Official source keys: `EX-SAP3, CW-ALARMS, WA-ALERT, WA-RESPOND`

6. **Intent — Correlate deployments and configuration changes with workload behavior.**
   - Hard constraint: Error rate rises after one of several application, infrastructure, and configuration releases, and responders need the causal sequence quickly.
   - Correct principle: Record deployment/change identifiers and timestamps, annotate dashboards/events, correlate them with metrics, logs, traces, CloudTrail, and Config state, and compare pre/post baselines before deciding rollback or forward repair.
   - Three plausible distractor concepts: (1) infer the cause from the most recent commit without runtime evidence; (2) use CloudTrail alone to explain customer latency; (3) remove deployment markers after success to reduce dashboard clutter.
   - Task mapping: `SAA-C03 SAA-2.2 | SAP-C02 SAP-3.1, SAP-3.3`
   - Official source keys: `EX-SAA2, EX-SAP3, WA-OBSERVE, CT-EVENTS, CONFIG-CORE, CP-CONCEPTS`

7. **Intent — Distinguish runbooks for known procedures from playbooks for investigation.**
   - Hard constraint: Operators need deterministic steps for recurring actions and guided diagnosis for incidents whose exact cause is not yet known.
   - Correct principle: Use runbooks with prerequisites, commands/automation, validation, rollback, and evidence for known procedures; use playbooks with hypotheses, branching diagnostics, escalation, and decision points for investigation, and test both during readiness reviews and exercises.
   - Three plausible distractor concepts: (1) write one linear runbook for every possible unknown incident; (2) omit validation because successful command execution proves recovery; (3) keep playbooks generic enough that they name no signals or owners.
   - Task mapping: `SAP-C02 SAP-3.1`
   - Official source keys: `EX-SAP3, WA-READY, WA-RUNBOOK, SSM-AUTOMATION`

8. **Intent — Gate production launch and major change on operational readiness.**
   - Hard constraint: A feature is functionally complete, but ownership, alarms, quotas, support access, rollback, data recovery, and dependency capacity have not all been proven.
   - Correct principle: Run a consistent operational readiness review before launch and significant changes, require evidence for critical checklist items, assign owners and deadlines for accepted risks, and repeat reviews as the workload and learned practices evolve.
   - Three plausible distractor concepts: (1) waive readiness because a managed service passed deployment; (2) use a checklist with no evidence or accountable approver; (3) perform an ORR only once when the first version launches.
   - Task mapping: `SAP-C02 SAP-2.1, SAP-3.1, SAP-3.4`
   - Official source keys: `EX-SAP2, EX-SAP3, WA-READY, WA-ORR`

9. **Intent — Manage incidents by business impact, escalation, and communication.**
   - Hard constraint: Multiple alarms and teams activate during an outage, and uncoordinated technical actions risk conflicting changes and delayed customer communication.
   - Correct principle: Declare and prioritize the event by business impact, assign incident leadership and technical roles, use explicit escalation and communication paths, maintain a timestamped decision log, and coordinate recovery/rollback changes through one operating process.
   - Three plausible distractor concepts: (1) let every team independently change production until one fix works; (2) prioritize by alarm count rather than customer impact; (3) delay all stakeholder communication until root cause is certain.
   - Task mapping: `SAP-C02 SAP-3.1`
   - Official source keys: `EX-SAP3, WA-RESPOND, WA-RUNBOOK`

10. **Intent — Convert incidents, reviews, and game days into completed improvements.**
   - Hard constraint: The organization repeatedly records the same risk because post-incident findings and Well-Architected review items lack owners, priority, deadlines, and verification.
   - Correct principle: Perform blameless evidence-based post-incident analysis, identify contributing system/process factors, prioritize corrective actions, assign owners and due dates, verify effectiveness through tests/game days and runtime evidence, and use Well-Architected milestones to record review progress rather than replace operations.
   - Three plausible distractor concepts: (1) close the incident after adding another alarm with no response process; (2) use a Well-Architected milestone as proof that remediation is deployed; (3) focus corrective action on the individual operator and leave systemic conditions unchanged.
   - Task mapping: `SAP-C02 SAP-3.1, SAP-3.4`
   - Official source keys: `EX-SAP3, WA-EVOLVE, WA-TOOL, FIS-CORE, WA-ORR`

---

## Separate mapping to official public AWS sample and practice resources

This mapping names only the official resource, question number, and topic. It does not reproduce question text, options, or answer explanations.

| Chapter | Public official sample mapping by question number/topic | Directness statement |
|---|---|---|
| Chapter 72 | `SAP-SAMPLE` Question 2 — deploy a cross-account IAM role with CloudFormation StackSets. | Directly calibrates Chapter 72 Intent 5 at a basic StackSets/service-selection level. It does not cover CDK synthesis/bootstrap, dependencies, policy-as-code, immutable template promotion, or stack diagnosis. No `SAA-SAMPLE` question maps directly. |
| Chapter 73 | No released SAA-C03 or SAP-C02 sample item directly tests change-set review, drift reconciliation, stack policies, `DeletionPolicy`, `UpdateReplacePolicy`, rollback triggers, resource import, or failed rollback recovery. | **No official public sample maps directly.** |
| Chapter 74 | `SAP-SAMPLE` Question 9 concerns a two-Region active-active application deployment architecture, but it does not test rolling, blue/green, canary, CodeDeploy traffic shifting, deployment alarms, or schema compatibility. | Adjacent architecture context only; **no official public sample maps directly** to the Chapter 74 intents. |
| Chapter 75 | `SAP-SAMPLE` Question 5 — use Systems Manager Run Command to manage an EC2 fleet without opening an administrative inbound port. `SAA-SAMPLE` Question 1 — private-subnet internet egress needed to obtain software patches. | SAP Question 5 directly calibrates Chapter 75 Intent 1's no-inbound-management principle and is adjacent to Intent 4. SAA Question 1 is only adjacent to Intent 2 because it tests egress, not Systems Manager or patch orchestration. |
| Chapter 76 | `SAP-SAMPLE` Question 1 uses a CloudWatch billing alarm for notification, which is adjacent to detection and alerting but not configuration remediation. | **No official public sample maps directly** to Config/EventBridge remediation, preventive controls, idempotency, approvals, loops, or organization conformance packs. |
| Chapter 77 | `SAP-SAMPLE` Question 9 includes multi-Region availability, but it does not test AWS Backup, immutable vaults, restore testing, validation, measured recovery, Audit Manager, or fault-injection game days. | **No official public sample maps directly.** |
| Chapter 78 | `SAP-SAMPLE` Question 1 includes threshold notification through CloudWatch, but it does not test customer-impact observability, alert ownership, readiness reviews, incident management, post-incident analysis, or continuous improvement. | Adjacent alarm mechanics only; **no official public sample maps directly** to the Chapter 78 intents. |

### Official practice resources without public item-level mappings

AWS publicly lists the resources below through `CERT-PREP`, but their current item text and stable question-number/topic index are not exposed on the public landing page. This audit therefore does not invent item-level mappings.

| Official practice resource | Appropriate use for Part 07 | Public question-number status |
|---|---|---|
| SAA-C03 Official Practice Question Set | Calibrate SAA task coverage for secure workload access, data protection, infrastructure integrity, highly available deployment, and backup/recovery. | **No public item-level number/topic mapping is asserted.** |
| SAP-C02 Official Practice Question Set | Calibrate SAP deployment strategy, configuration management, patching, business continuity, monitoring, automated remediation, and operational-excellence trade-offs. | **No public item-level number/topic mapping is asserted.** |
| SAA-C03 Official Practice Exam | Use as a full-blueprint readiness check after chapter coverage is implemented; retain only domain/task weakness data. | **No public item-level number/topic mapping is available.** |
| SAP-C02 Official Practice Exam | Use as a timed readiness check for the active C02 blueprint before its announced retirement; do not infer SAP-C03 coverage from it. | **No public item-level number/topic mapping is available.** |
| Official Exam Prep courses and enhanced courses | Use for official domain review, labs, and remediation of weak task areas; use product documentation as the factual authority for service behavior. | **No stable public question-number/topic mapping is available.** |

## Completion verification

- Chapter headings present: Chapters 72, 73, 74, 75, 76, 77, and 78 — exactly seven.
- Chapter-local intent numbering: 1–10 under every chapter.
- Intent total: 7 chapters × 10 intents = exactly 70.
- Every intent contains a unique hard constraint, a correct principle, exactly three plausible distractor concepts, an SAA-C03 or SAP-C02 task mapping, and official AWS source keys.
- Required coverage is explicit: CloudFormation/IaC, dependencies, change sets, drift, deletion/update policies, CI/CD, deployment strategies, rollback, observability, Systems Manager, patching/fleet management, EventBridge/remediation, backup restore testing, game days, and operational excellence.
- Only `tools/aws_exam_audits/part_07.md` is modified by this audit.

SUPERSET_WORKER_DONE task P07-audit-v2
