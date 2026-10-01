# Part 09 Audit — Chapters 91–96: AI and Emerging Architecture

Scope: audit the current five-question sets for Chapters 91–96 and specify exactly ten original replacement knowledge intents per chapter. This is an audit/blueprint, not a publishable question bank. It does not copy official sample questions, reconstruct live exam items, or use exam dumps.

Audit date: 2026-10-01.

## Audit-wide findings

- All six chapters use the same five-question template: broad service selection, a bundled settings list, a generic mechanism, “least operational overhead,” and a generic multi-account rollout. Questions 2 and 4 usually test the same service/configuration recognition, while Question 5 repeats nearly identical canary, administrator-access, and empty-standby choices across chapters.
- Five questions cannot cover the required boundaries among Bedrock inference, SageMaker AI, RAG ingestion/retrieval, agents, guardrails, identity, human approval, evaluation, observability, cost, and failure isolation.
- Several distractors are deliberately absurd rather than plausible: “deploy every option,” “the service automatically understands every business requirement,” and organization-wide `AdministratorAccess`. They do not test partial knowledge.
- The current SAP-C02 guide explicitly lists Bedrock Guardrails, AgentCore Identity, and Step Functions human-oversight workflows as **emerging pretest topics that do not affect the score**. The current SAA-C03 guide has no equivalent emerging-topic section. P09-specific AgentCore/guardrail/human-oversight questions therefore should be labeled `SAP Emerging`, not `SAA`.
- Chapter 91's `model access` wording is outdated for commercial Regions. Bedrock foundation-model access is enabled by default when the caller has the required AWS Marketplace and IAM permissions; model/Region support, provider prerequisites, and subscription completion still must be checked.
- “Bedrock versus SageMaker” is presented as a false binary. Bedrock now includes several customization paths, while SageMaker AI remains the choice when the architecture needs fuller control of training workflows, frameworks, deployment, and infrastructure.
- “Private,” “encrypted,” “guarded,” and “authorized” are repeatedly treated as interchangeable. PrivateLink changes the network path; KMS protects configured data at rest; Guardrails evaluates content; IAM or downstream application policy authorizes actions. None replaces the others.
- Model invocation logging, agent traces, RAG evaluation data, prompts, retrieved chunks, and outputs can all contain sensitive information. The audit must distinguish Bedrock's default data-handling behavior from customer-enabled logging and application-owned storage.
- A successful HTTP/model response is not proof of retrieval relevance, factual grounding, safe tool effects, correct tenant authorization, or acceptable cost. AI operations require stage-specific quality, safety, latency, error, and business signals.

## Official AWS source keys

Only official public AWS documentation is keyed below.

### Exam scope and task statements

- `EX-SAA` — [AWS Certified Solutions Architect - Associate (SAA-C03) exam guide](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)
- `EX-SAA-D1` — [SAA-C03 Domain 1: Design Secure Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)
- `EX-SAP` — [AWS Certified Solutions Architect - Professional (SAP-C02) exam guide, including Emerging Topics](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02.html)
- `EX-SAP-D1` — [SAP-C02 Domain 1: Design Solutions for Organizational Complexity](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain1.html)
- `EX-SAP-D2` — [SAP-C02 Domain 2: Design for New Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain2.html)
- `EX-SAP-D3` — [SAP-C02 Domain 3: Continuous Improvement for Existing Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)
- `EX-SAP-D4` — [SAP-C02 Domain 4: Accelerate Workload Migration and Modernization](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain4.html)

### Bedrock, SageMaker AI, and inference

- `AI-DECIDE` — [Amazon Bedrock or Amazon SageMaker AI?](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/bedrock-or-sagemaker.html)
- `BR-ACCESS` — [Request access to Amazon Bedrock models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)
- `BR-CONVERSE` — [Inference using the Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html)
- `BR-XREGION` — [Route inference requests with cross-Region inference](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html)
- `BR-XREGION-SUPPORT` — [Supported Regions and models for inference profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html)
- `BR-CUSTOM` — [Customize a model in Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/custom-models.html)
- `BR-DATA` — [Data protection in Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/data-protection.html)
- `BR-ZDR` — [Amazon Bedrock abuse detection and default zero-data-retention model](https://docs.aws.amazon.com/bedrock/latest/userguide/abuse-detection.html)
- `BR-PRIVATE` — [Use interface VPC endpoints with Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/vpc-interface-endpoints.html)
- `BR-ENCRYPT` — [Data encryption in Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/data-encryption.html)
- `BR-ERRORS` — [Troubleshoot Amazon Bedrock API error codes](https://docs.aws.amazon.com/bedrock/latest/userguide/troubleshooting-api-error-codes.html)
- `BR-SCALE` — [Amazon Bedrock scaling and throughput best practices](https://docs.aws.amazon.com/bedrock/latest/userguide/scaling-throughput-best-practices.html)

### Knowledge Bases, RAG, and evaluation

- `KB-RAG` — [Query a knowledge base and generate cited responses](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-retrieve-generate.html)
- `KB-PERM` — [Create a service role for Amazon Bedrock Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-permissions.html)
- `KB-USER-PERM` — [Permissions to create, manage, retrieve, and retrieve-and-generate](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-prereq-permissions-general.html)
- `KB-SYNC` — [Synchronize a Knowledge Bases data source](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-data-source-sync-ingest.html)
- `KB-DELETE` — [Delete documents from a knowledge base](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-direct-ingestion-delete.html)
- `KB-ENCRYPT` — [Encryption of knowledge base resources](https://docs.aws.amazon.com/bedrock/latest/userguide/encryption-kb.html)
- `KB-EVAL` — [Evaluate RAG sources with Amazon Bedrock evaluations](https://docs.aws.amazon.com/bedrock/latest/userguide/evaluation-kb.html)
- `KB-EVAL-METRICS` — [RAG retrieve-only and retrieve-and-generate metrics](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-eval-retrieve.html)
- `BR-MODEL-EVAL` — [Create a model evaluation job using an LLM as a judge](https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-type-judge.html)

### Agents, guardrails, and identity

- `AG-ACTION` — [Add an action group to an Amazon Bedrock agent](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-action-add.html)
- `AG-PERM` — [Create a service role for Amazon Bedrock Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-permissions.html)
- `AG-TRACE` — [Trace an Amazon Bedrock agent's orchestration path](https://docs.aws.amazon.com/bedrock/latest/userguide/trace-events.html)
- `GR-COMP` — [Amazon Bedrock Guardrails components](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-components.html)
- `GR-HOW` — [How Amazon Bedrock Guardrails works](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-how.html)
- `GR-USE` — [Use Guardrails with inference, agents, Knowledge Bases, and flows](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use.html)
- `GR-APPLY` — [Use the independent ApplyGuardrail API](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-independent-api.html)
- `GR-TEST` — [Test and version a guardrail](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-test.html)
- `GR-MON` — [Monitor and enforce Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-enforcements.html)
- `AC-PATTERN` — [AgentCore Identity supported authentication patterns](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/common-use-cases.html)
- `AC-INBOUND` — [Configure an AgentCore inbound JWT authorizer](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/inbound-jwt-authorizer.html)
- `AC-RUNTIME-AUTH` — [AgentCore Runtime inbound and outbound authentication](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-oauth.html)
- `AC-WORKLOAD` — [Understand AgentCore workload identities](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/understanding-agent-identities.html)
- `AC-TOKEN` — [Get an AgentCore workload access token](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/get-workload-access-token.html)
- `AC-OUTBOUND` — [Obtain OAuth credentials with AgentCore Identity](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/obtain-credentials.html)
- `IAM-EVAL` — [IAM policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)
- `STS-SESSION` — [Control permissions for assumed-role sessions](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_control-access_assumerole.html)
- `STS-TAGS` — [Pass session tags in AWS STS](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_session-tags.html)
- `STS-SOURCE` — [Monitor and control assumed roles with source identity](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_control-access_monitor.html)

### Human approval and AI operations

- `SF-CALLBACK` — [Step Functions callback with task token](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html)
- `SF-INTEGRATION` — [Step Functions optimized service integration patterns](https://docs.aws.amazon.com/step-functions/latest/dg/integrate-optimized.html)
- `SF-TASK` — [Step Functions Task state timeout and heartbeat fields](https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html)
- `SF-VERSION` — [Step Functions versions and aliases](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-cd-aliasing-versioning.html)
- `SF-XACCOUNT` — [Access cross-account resources from Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-cross-acct-sync-pattern.html)
- `BR-LOG` — [Monitor model invocation using CloudWatch Logs and Amazon S3](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html)
- `BR-METRIC` — [Monitor Bedrock runtime inference with CloudWatch metrics](https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-runtime-metrics.html)
- `BR-OTPS` — [Diagnose invocation latency with output tokens per second](https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-runtime-otps.html)
- `BR-COST-AIP` — [Application inference profiles for cost attribution](https://docs.aws.amazon.com/bedrock/latest/userguide/cost-mgmt-application-inference-profiles.html)
- `BR-CLOUDTRAIL` — [Monitor Amazon Bedrock API calls with CloudTrail](https://docs.aws.amazon.com/bedrock/latest/userguide/logging-using-cloudtrail.html)
- `SM-MONITOR` — [Monitor model bias drift in SageMaker AI](https://docs.aws.amazon.com/sagemaker/latest/dg/clarify-model-monitor-bias-drift-schedule.html)

## Official public sample and practice resource map

This mapping is intentionally separate from the product-document source keys. It describes legitimate calibration resources without reproducing their questions.

| Key | Official resource | Permitted use in this project | Limitation |
|---|---|---|---|
| `PRACT-SAA-SAMPLE` | [SAA-C03 official sample questions PDF](https://d1.awsstatic.com/training-and-certification/docs-sa-assoc/AWS-Certified-Solutions-Architect-Associate_Sample-Questions.pdf) | Calibrate single-choice/multiple-response shape, plausible distractors, and explanation depth. | The 2022 sample is not a coverage map and predates the P09 emerging services. |
| `PRACT-SAP-SAMPLE` | [SAP-C02 official sample questions PDF](https://d1.awsstatic.com/training-and-certification/docs-sa-pro/AWS-Certified-Solutions-Architect-Professional_Sample-Questions.pdf) | Calibrate long scenario structure, interacting constraints, and multi-service reasoning. | The 2022 sample predates the current SAP emerging-topic additions. |
| `PRACT-SAA-PREP` | [AWS Certified Solutions Architect - Associate preparation hub](https://aws.amazon.com/certification/certified-solutions-architect-associate/) | Use the canonical AWS page to reach the current Exam Prep Plan, Official Practice Question Set, and Official Practice Exam. | Some linked activities require sign-in or a subscription; do not scrape or republish them. |
| `PRACT-SAP-PREP` | [AWS Certified Solutions Architect - Professional preparation hub](https://aws.amazon.com/certification/certified-solutions-architect-professional/) | Use the canonical AWS page to reach the current Exam Prep Plan, Official Practice Question Set, and Official Practice Exam. | Access conditions and exam versions can change; the page is not permission to copy question text. |
| `PRACT-SFN-CALLBACK` | [Step Functions callback sample project](https://docs.aws.amazon.com/step-functions/latest/dg/callback-task-sample-sqs.html) | Practice implementation of a callback workflow using AWS-owned sample infrastructure. | It is a product sample, not evidence that a specific implementation will appear on an exam. |

Rules:

- Use the exam guides for scope/task mapping and product documentation for service facts.
- Use official samples only to calibrate item style; do not infer topic frequency from a small sample.
- Do not copy, lightly paraphrase, screenshot, or bulk-extract questions from AWS Skill Builder.
- Reject recalled live questions, “actual exam” files, braindumps, and third-party dump sites even if they claim accuracy.

---

## Chapter 91 — Amazon Bedrock Architecture

### Current-question defects

- **Duplicate/low-density:** Questions 2 and 4 both reward selecting the same broad Bedrock settings bundle. Questions 1 and 5 repeat the chapter decision rather than testing separate inference, RAG, agent, or network boundaries.
- **Ambiguous:** Question 1 requires RAG, filtering, private data, and answer sources, but its correct choice merely says to “layer” Bedrock features. It does not require a Knowledge Base query mode that returns citations, a server-side authorization design, or a guardrail.
- **Outdated:** Listing `model access` as an ordinary enablement switch is stale for commercial Regions. Access is enabled by default with the required Marketplace/IAM permissions, subject to model/provider/Region prerequisites and subscription completion.
- **Factually unsafe:** The Bedrock/SageMaker comparison implies Bedrock is only a pre-trained-model API. Current Bedrock supports customization paths; SageMaker AI remains differentiated by deeper control over training, frameworks, deployment, and infrastructure.
- **Factually unsafe:** A single answer bundles inference profiles, KMS, VPC endpoints, generation parameters, invocation logging, and IAM as if all were one setting and all were always required. They govern different contracts.
- **Missing:** Converse versus native model APIs, current model acquisition, cross-Region inference data boundaries, application inference profiles, Knowledge Bases citations/filtering, agent action-group permissions, and concrete 400/429/503/529 diagnosis.

### Exactly ten replacement knowledge intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | Task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Choose Bedrock or SageMaker AI for two production AI workloads. | Prefer Bedrock for managed access to supported foundation models and AWS-native GenAI building blocks; prefer SageMaker AI when the requirement is fuller control of training workflows, frameworks, endpoints, and infrastructure. Do not claim that Bedrock has no customization capabilities. | Choose Bedrock only because the model is generative; choose SageMaker only because training data exists; choose both without identifying a responsibility boundary. | `SAP-4.4` | `AI-DECIDE`, `BR-CUSTOM`, `EX-SAP-D4` |
| 2 | Diagnose a first invocation that fails even though commercial-Region model access appears enabled. | Verify model availability in the selected Region, caller IAM, AWS Marketplace permissions/subscription state, and any provider-specific first-use prerequisite; do not prescribe a legacy blanket “request model access” step. | Add a VPC endpoint to accept a provider EULA; increase token quota for an authorization error; create a Knowledge Base to enable the base model. | `SAP-2.3` | `BR-ACCESS`, `BR-ERRORS`, `EX-SAP-D2` |
| 3 | Select Converse versus `InvokeModel` for a multi-model chat application. | Use Converse/ConverseStream for a consistent messages interface across models that support it, while checking model-specific feature support and passing model-specific parameters where required. | Assume every model supports identical tools and fields; use `InvokeModel` because Converse cannot stream; infer that a consistent API makes model outputs semantically interchangeable. | `SAP-4.4` | `BR-CONVERSE`, `EX-SAP-D4` |
| 4 | Trace a cited RAG answer through its data path. | Knowledge Bases ingests/chunks/embeds/indexes source data; `RetrieveAndGenerate` retrieves context, invokes a supported generation model, and returns citation structures that the application must preserve and render. | Claim model pretraining creates the citations; use `Retrieve` alone and expect a generated answer; discard citation metadata and reconstruct source links from model text. | `SAP-2.5` | `KB-RAG`, `KB-PERM`, `EX-SAP-D2` |
| 5 | Tune poor RAG retrieval without changing the foundation model first. | Evaluate chunking, embedding/index choice, retrieval count, metadata filters, reranking, and source freshness separately from generation parameters; measure retrieval before blaming the model. | Raise temperature to improve document recall; add more output tokens to fix missing chunks; use a guardrail as a vector-search relevance control. | `SAP-3.3` | `KB-RAG`, `KB-SYNC`, `KB-EVAL`, `EX-SAP-D3` |
| 6 | Authorize a Bedrock agent action group that performs refunds. | Give the agent service role only required model/Knowledge Base/action permissions, allow the Bedrock service principal to invoke the action Lambda with a scoped resource policy, and enforce customer/refund authorization inside the trusted tool path. | Give the model direct administrator credentials; rely on the action schema as authorization; attach only a Lambda execution role and omit the Lambda resource policy. | `SAP-2.3` | `AG-ACTION`, `AG-PERM`, `IAM-EVAL`, `EX-SAP` |
| 7 | Place Guardrails correctly in a Bedrock application architecture. | Use Guardrails to assess configured input/output content; retain IAM, tenant filtering, tool authorization, validation, and approval controls because content filtering is not an authorization system. | Treat a denied-topic policy as an IAM deny; assume a guardrail guarantees factual accuracy; use network isolation as a substitute for harmful-content controls. | `SAP-2.3` | `GR-HOW`, `GR-USE`, `EX-SAP` |
| 8 | Design private application access to Bedrock. | An interface VPC endpoint gives VPC resources a private network path to supported Bedrock endpoints; it does not place Bedrock inside the customer VPC or authorize models, documents, or tool actions. | Add PrivateLink and remove IAM; claim PrivateLink prevents customer code from logging prompts; use a gateway endpoint intended for S3 as the Bedrock runtime endpoint. | `SAP-2.3` | `BR-PRIVATE`, `BR-DATA`, `EX-SAP-D2` |
| 9 | Choose between cross-Region and application inference profiles. | Cross-Region profiles route supported model requests among documented destination Regions for throughput/resilience; application inference profiles attribute supported runtime usage to tagged applications. Treat geographic/global routing and cost allocation as different decisions. | Use an application profile to keep processing in one Region; claim a global profile has an immutable destination list; assume either profile is a provisioned-capacity reservation. | `SAP-2.5`, `SAP-2.6` | `BR-XREGION`, `BR-XREGION-SUPPORT`, `BR-COST-AIP`, `EX-SAP-D2` |
| 10 | Diagnose Bedrock inference failures by error class. | Separate validation/model/Region problems (`400`), account quota throttling (`429`), and transient service/model capacity (`503`/`529`); bound concurrency and use backoff with jitter only for retryable failures. | Retry every `400` indefinitely; treat every `503` as proof of an account quota; increase `max_tokens` to reduce token reservation and throttling. | `SAP-3.4` | `BR-ERRORS`, `BR-SCALE`, `EX-SAP-D3` |

---

## Chapter 92 — Generative AI Data Security

### Current-question defects

- **Duplicate/low-density:** Questions 2 and 4 repeat the Chapter 91 Bedrock settings bundle. Question 3 tests a generic Bedrock runtime sentence rather than a data boundary.
- **Ambiguous:** “Private connectivity can reduce internet exposure” is a complementary control for the stated medical workload, not an alternative that the learner should reject.
- **Factually unsafe:** “IAM controls the model and knowledge base” is not a complete tenant-isolation statement. IAM can authorize Bedrock API/resource access, but the architecture still needs trusted document partitioning or mandatory server-side metadata filtering and vector-store controls.
- **Factually unsafe:** The failure prose can be read as if Bedrock permanently stores prompts/traces by default. Bedrock documents default zero data retention for model inputs/outputs, while model invocation logging is customer-enabled and disabled by default. Application logs, traces, data stores, and evaluation outputs have separate retention.
- **Low-density:** KMS, PrivateLink, Macie, tenant boundaries, source-bucket permissions, vector-store permissions, logging, deletion, and evaluation data are named but never tested as separate controls.
- **Missing:** Model-provider access boundary, invocation-log payload risk, Knowledge Bases service role, KMS dependencies, ingestion deletion semantics, and security of evaluation datasets/results.

### Exactly ten replacement knowledge intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | Task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Build a complete GenAI data-flow inventory before selecting controls. | Classify and assign owners/retention for user input, system prompts, retrieved chunks, embeddings, tool arguments/results, model output, traces, invocation logs, evaluation datasets, and human-review evidence. | Inventory only the original S3 documents; treat embeddings as non-sensitive hashes; exclude rejected prompts because no answer was returned. | `SAP-1.2` | `BR-DATA`, `BR-LOG`, `AG-TRACE`, `EX-SAP-D1` |
| 2 | Explain the Bedrock model-provider data boundary. | Bedrock documentation states that model providers do not have access to Bedrock deployment accounts, service logs, customer prompts, or completions; still apply data minimization because customer systems and enabled features can store or expose data. | Assume no application log can retain a prompt; infer that IAM is unnecessary because providers lack access; claim every downstream tool inherits Bedrock's boundary. | `SAP-2.3` | `BR-DATA`, `BR-ZDR`, `EX-SAP-D2` |
| 3 | Configure model invocation logging for a regulated workload. | Invocation logging is disabled by default and can collect request/response data for supported `bedrock-runtime` calls into configured CloudWatch Logs and/or S3 destinations; minimize captured content and set destination access, encryption, and retention explicitly. | Enable debug logging and grant all developers read access; assume CloudTrail contains full model prompts; rely on deleting the Bedrock logging configuration to delete existing destination data. | `SAP-2.3` | `BR-LOG`, `BR-CLOUDTRAIL`, `BR-ENCRYPT`, `EX-SAP-D2` |
| 4 | Separate private network routing from authorization and data filtering. | Use the appropriate Bedrock interface endpoints and endpoint policies/security controls for the network path, while retaining IAM, data-source permissions, tenant filters, and application authorization. | Treat a VPC endpoint policy as row-level document security; remove TLS because traffic is private; assume a private endpoint stops the application from sending excessive PII. | `SAP-1.2` | `BR-PRIVATE`, `BR-DATA`, `IAM-EVAL`, `EX-SAP-D1` |
| 5 | Design KMS boundaries across a Knowledge Bases pipeline. | Account separately for source-object encryption, Knowledge Base/vector-store encryption options, secrets, temporary evaluation data, and the service role's KMS permissions; a KMS key does not grant Bedrock access without matching IAM/key authorization. | One Bedrock KMS setting encrypts every connected store automatically; key rotation provides tenant authorization; an alias alone grants decrypt permission. | `SAP-2.3` | `BR-ENCRYPT`, `KB-ENCRYPT`, `KB-PERM`, `EX-SAP-D2` |
| 6 | Prevent cross-tenant retrieval in a shared RAG application. | Enforce tenant identity in trusted server code and use a design that cannot omit the tenant boundary, such as separate knowledge/index boundaries or mandatory server-generated metadata filters plus vector-store controls. Treat metadata filtering as retrieval scope, not standalone authorization. | Accept a tenant filter supplied directly by the prompt; rely on the model to ignore another tenant's chunks; use a PII guardrail as the only tenant boundary. | `SAP-2.3` | `KB-RAG`, `KB-USER-PERM`, `IAM-EVAL`, `EX-SAP-D2` |
| 7 | Scope the Knowledge Bases service role and trust relationship. | Grant only required source bucket, embedding model, vector store, secrets, and KMS access; restrict the Bedrock trust with source-account/resource conditions where supported and separate builder permissions from runtime retrieval permissions. | Give the service role `AdministratorAccess`; grant the end user direct access to every source bucket; use the model invocation role as the vector database's anonymous credential. | `SAP-1.2` | `KB-PERM`, `KB-USER-PERM`, `EX-SAP-D1` |
| 8 | Remove a revoked document from the effective RAG corpus. | Delete the document through the supported direct-ingestion API or remove it from the data source and run a successful sync; verify removal from the vector store and relevant caches rather than assuming source deletion is instantaneous. | Delete only the original S3 object and skip sync; shorten model output tokens; delete the embedding model to remove one document. | `SAP-3.2` | `KB-SYNC`, `KB-DELETE`, `EX-SAP-D3` |
| 9 | Use Guardrails for sensitive information without overstating protection. | Configure supported sensitive-information entities/custom regex with `BLOCK` or `ANONYMIZE` as appropriate, then retain data classification, access control, minimization, and downstream output validation. | Treat anonymization as irreversible cryptographic tokenization; assume every domain identifier is a built-in PII type; allow broad retrieval because output masking will always catch leakage. | `SAP-2.3` | `GR-COMP`, `GR-HOW`, `BR-DATA`, `EX-SAP` |
| 10 | Secure RAG/model evaluation jobs and results. | Treat prompt datasets, ground truth, retrieved text, generated responses, judge outputs, and reports as sensitive; scope S3/IAM/KMS access and retention, and do not expose production secrets merely to obtain realistic evaluation data. | Publish evaluation reports because they contain only scores; reuse unrestricted production logs as the test set; assume an evaluator model cannot receive sensitive context. | `SAP-3.2` | `KB-EVAL`, `BR-MODEL-EVAL`, `KB-ENCRYPT`, `EX-SAP-D3` |

---

## Chapter 93 — Bedrock Guardrails and Responsible AI

### Current-question defects

- **Ambiguous:** Question 1 marks “Guardrails are a defense layer, not a replacement for authorization, prompt-injection defenses, and business validation” incorrect even though it is an essential part of the correct architecture.
- **Duplicate:** Questions 2 and 4 test the same list of filters. Questions 1 and 5 repeat “apply Guardrails plus a human process.”
- **Factually unsafe:** The chapter implies that Guardrails can prevent a high-risk transaction. Guardrails evaluates configured content; trusted tool authorization, deterministic validation, and approval must stop unauthorized side effects.
- **Factually unsafe:** “Topic/policy filters and denied content” is imprecise terminology. Current configurable policies include content filters, denied topics, word filters, sensitive-information filters, contextual-grounding checks, and other documented components; each has different inputs and effects.
- **Overbroad mechanism:** “Before and after inference” does not describe every integration. `ApplyGuardrail` can be called independently at chosen points, while integrated inference/agent/Knowledge Base behavior depends on the API and selected content.
- **Missing:** Prompt-attack input filter, filter strengths, PII actions, custom regex, contextual-grounding thresholds, selective assessment, `DRAFT` versus immutable versions, intervention telemetry, false positives, and regression testing.

### Exactly ten replacement knowledge intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | Task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Define the responsibility boundary of a guardrail. | Guardrails provides configured content/safety assessments and interventions. It does not replace IAM, tenant authorization, source trust, schema/business validation, idempotency, or human approval for high-risk actions. | Use a denied topic as a refund authorization policy; treat PrivateLink as a content filter; allow every tool call because final output is guarded. | `SAP-1.2`, `SAP-2.3` | `GR-HOW`, `GR-USE`, `EX-SAP` |
| 2 | Configure content-filter strengths and prompt-attack handling. | Choose input/output filter strengths from measured risk and false-positive tolerance; prompt attacks are a content-filter category with documented tier/direction constraints, so do not assume an output prompt-attack control. | Set every category to maximum without testing; use word filters to detect all jailbreak semantics; lower the model temperature as the only prompt-injection defense. | `SAP-2.3` | `GR-COMP`, `GR-TEST`, `EX-SAP` |
| 3 | Define a denied-topic policy for regulated advice. | Describe the prohibited topic clearly with representative examples, then test paraphrases and borderline allowed content; denied topics are semantic policy controls, not exact-string blocklists or authorization rules. | Add only the phrase “investment advice”; use a denied topic to grant licensed users access; assume topic denial proves legal compliance without review. | `SAP-1.2` | `GR-COMP`, `GR-TEST`, `EX-SAP` |
| 4 | Select sensitive-information actions. | Use supported PII entity types and custom regex definitions, selecting `BLOCK` or `ANONYMIZE` according to the data contract; validate both user input and generated output paths that need protection. | Treat `ANONYMIZE` as deletion from all logs; use a profanity list for account numbers; block all numbers and call it precise PII control. | `SAP-2.3` | `GR-COMP`, `GR-APPLY`, `EX-SAP` |
| 5 | Apply word filters without confusing them with semantic controls. | Use managed profanity and exact custom word/phrase lists for lexical requirements; use denied topics or content filters when meaning rather than exact terms is the policy concern. | Expect a word list to catch every synonym; use a denied topic for an exact secret marker; conclude that masking one word makes the whole answer safe. | `SAP-2.3` | `GR-COMP`, `GR-HOW`, `EX-SAP` |
| 6 | Configure contextual-grounding checks for RAG output. | Supply the relevant source, query, and response context and calibrate grounding/relevance thresholds on a representative set; the check can flag deviations but is not a universal truth oracle. | Run grounding without source text; set a threshold from one example; assume a grounded answer is authorized and complete. | `SAP-3.2` | `GR-COMP`, `GR-APPLY`, `KB-EVAL`, `EX-SAP-D3` |
| 7 | Insert `ApplyGuardrail` into a custom pipeline. | Call `ApplyGuardrail` on selected `INPUT` or `OUTPUT` content at the point where intervention is useful, inspect assessments/action, and define fail-open/fail-closed behavior explicitly. | Label model output as `INPUT` without consequence; assume the API invokes the foundation model; ignore `GUARDRAIL_INTERVENED` and return the unfiltered text. | `SAP-2.3` | `GR-APPLY`, `GR-MON`, `EX-SAP-D2` |
| 8 | Attach a guardrail to an agent without overstating tool protection. | Associating a guardrail applies it to documented agent prompts/responses; separately validate action parameters and authorize side effects in the action-group/tool implementation before committing them. | Assume the guardrail is the Lambda resource policy; execute the tool before checking trusted constraints; rely on the model's refusal text as rollback. | `SAP-2.3` | `GR-USE`, `AG-ACTION`, `AG-PERM`, `EX-SAP` |
| 9 | Promote a tested guardrail configuration. | Iterate in `DRAFT`, test/benchmark it, create an immutable version snapshot, and update the application to reference the intended version; editing the draft does not silently update deployed references. | Point production permanently at untested `DRAFT`; assume creating a version redirects all applications; delete an in-use version before disassociating dependencies. | `SAP-2.1` | `GR-TEST`, `GR-USE`, `EX-SAP-D2` |
| 10 | Operate Guardrails with measurable quality and safety goals. | Maintain allowed/blocked/adversarial regression sets; measure interventions, false accepts, false rejects, latency, and business escalations; review CloudWatch/CloudTrail signals without logging unnecessary sensitive text. | Optimize only for the number of blocked prompts; declare success after resource creation; inspect only HTTP errors and ignore incorrect interventions. | `SAP-3.1`, `SAP-3.2` | `GR-TEST`, `GR-MON`, `BR-CLOUDTRAIL`, `EX-SAP-D3` |

---

## Chapter 94 — Agent Identity and Tool Authorization

### Current-question defects

- **Scope mismatch/outdated:** All five items are labeled SAA or SAA→SAP even though AgentCore Identity is explicitly identified by the current SAP-C02 guide as an emerging pretest topic.
- **Factually unsafe:** “Exchange a workload/user identity for short-term scoped credentials” conflates AgentCore workload access tokens, downstream OAuth/API credentials, and AWS STS credentials. A workload access token authorizes access to AgentCore services such as outbound credential providers; it is not a generic AWS API credential.
- **Ambiguous:** Question 1 mixes “preserve requester identity,” tool scope, and audit but does not state whether the target is an AgentCore Runtime, a third-party OAuth resource server, or an AWS API. Those use different mechanisms.
- **Low-density:** The settings bundle combines identity providers, workload identity, credential providers, OAuth scopes, token vault, and resource policy without testing inbound authentication, outbound authorization, or AWS IAM separately.
- **Duplicate:** Questions 2 and 4 repeat the same AgentCore settings recognition. Questions 1 and 5 repeat the broad least-privilege statement.
- **Missing:** SigV4 versus JWT inbound mode, JWT claim validation, workload-token purpose, user-delegated versus machine-to-machine OAuth, on-behalf-of exchange, vault/provider scoping, STS session restriction, action-group Lambda permissions, and stage-specific auth failure diagnosis.

### Exactly ten replacement knowledge intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | Task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Distinguish Bedrock Agents authorization from AgentCore Identity. | Bedrock Agents uses an agent service role plus resource permissions for model, Knowledge Base, and action-group access. AgentCore Identity supplies identity/authentication and outbound credential patterns for AgentCore-hosted or integrated agents. Select the mechanism from the runtime and target. | Add AgentCore Identity to fix a missing Lambda resource policy; use the Bedrock agent role as an end-user OAuth token; assume the two services share one automatic permission model. | `SAP-2.3` | `AG-PERM`, `AG-ACTION`, `AC-WORKLOAD`, `EX-SAP` |
| 2 | Choose AgentCore Runtime inbound authentication mode. | A Runtime version supports either IAM SigV4 or JWT bearer-token inbound authentication, not both simultaneously; use separate versions/endpoints when both caller populations are required. | Enable SigV4 and JWT on the same version; use an outbound OAuth provider as the inbound authorizer; treat TLS client IP as the caller identity. | `SAP-2.3` | `AC-RUNTIME-AUTH`, `EX-SAP` |
| 3 | Configure an inbound JWT authorizer. | Validate the trusted issuer/discovery/JWKS path and constrain expected clients, scopes, and claims; successful JWT validation authenticates the request but downstream code still enforces tenant and business authorization. | Accept any token with a non-expired `exp`; use OAuth scopes as AWS IAM policies automatically; infer that a valid signature authorizes every tool. | `SAP-1.2` | `AC-INBOUND`, `IAM-EVAL`, `EX-SAP` |
| 4 | Explain workload identity and workload access-token scope. | A workload identity is the stable agent identity; its workload access token carries agent/user context for authorized access to first-party AgentCore identity services such as outbound credential providers. It is not an arbitrary AWS access key/session token. | Send the workload token directly to S3; store it in prompts for later reuse; treat workload identity as the human approver's identity. | `SAP-2.3` | `AC-WORKLOAD`, `AC-TOKEN`, `EX-SAP` |
| 5 | Choose user-delegated or machine-to-machine outbound OAuth. | Use user-delegated authorization when the downstream action must be on behalf of a person and machine-to-machine credentials for application-owned access; request only scopes accepted by the downstream authorization server. | Use client credentials for every user-owned Google Drive file; use a user token as an AWS role trust policy; request broad scopes because the agent prompt will self-restrict. | `SAP-2.3` | `AC-PATTERN`, `AC-OUTBOUND`, `EX-SAP` |
| 6 | Use on-behalf-of token exchange across an agent hop. | Where supported, exchange an authenticated inbound user token for an audience-scoped downstream token that binds user and workload identity; the downstream resource server must still validate and authorize that token. | Forward the original bearer token to every audience; assume token exchange grants permissions absent from the source authorization; authorize only by the agent name and ignore the represented user. | `SAP-2.3` | `AC-PATTERN`, `AC-TOKEN`, `EX-SAP` |
| 7 | Keep OAuth client secrets/API credentials out of agent context. | Configure supported credential providers/vault storage, scope provider access to authorized workload identities, and retrieve short-lived/resource-specific credentials at execution time instead of embedding secrets in prompts or code. | Put the API key in the system prompt; share one unrestricted provider ARN across all agents; log returned access tokens for debugging. | `SAP-1.2` | `AC-OUTBOUND`, `AC-WORKLOAD`, `BR-DATA`, `EX-SAP-D1` |
| 8 | Authorize an agent that calls AWS APIs with STS. | Use a narrowly scoped IAM role; apply session policies to reduce the role's permissions, session tags for ABAC where appropriate, and source identity for durable audit attribution. Effective permissions remain bounded by the role and applicable guardrails. | Use an OAuth scope as an `s3:GetObject` permission; expect a session policy to grant beyond the role; put a mutable role-session name in place of source identity. | `SAP-1.2`, `SAP-2.3` | `STS-SESSION`, `STS-TAGS`, `STS-SOURCE`, `IAM-EVAL`, `EX-SAP-D1` |
| 9 | Enforce authorization for a Bedrock agent action-group Lambda. | Scope the agent service role, add the Lambda resource policy for the Bedrock service principal with source conditions, validate the represented customer and action limits server-side, and make the side effect idempotent. | Trust model-generated `customerId`; attach only `AWSLambdaBasicExecutionRole`; let a guardrail decide the refund ceiling. | `SAP-2.3` | `AG-PERM`, `AG-ACTION`, `IAM-EVAL`, `EX-SAP` |
| 10 | Diagnose an agent authorization failure without broadening access. | Identify the failing stage: inbound SigV4/JWT, workload-token acquisition, credential-provider/consent, downstream OAuth `403`, STS/IAM denial, or tool business-policy denial. Correlate CloudTrail and application audit IDs, then change only the failing policy/claim/scope. | Add administrator access after any `403`; rotate the foundation model; increase inference quota to fix an invalid JWT audience. | `SAP-3.2` | `AC-INBOUND`, `AC-TOKEN`, `AC-OUTBOUND`, `BR-CLOUDTRAIL`, `EX-SAP-D3` |

---

## Chapter 95 — Human-in-the-loop Approval

### Current-question defects

- **Scope mismatch:** The chapter is labeled partly SAA even though the current SAP-C02 guide explicitly names Step Functions human-oversight workflows as an emerging pretest topic.
- **Ambiguous:** Question 1 marks risk-tiering (“low-risk reversible actions may automate; higher risk escalates”) incorrect, although that principle is necessary to decide when human approval is warranted.
- **Factually unsafe:** “Send an approval token” does not by itself make an approval secure. A task token is a callback capability; the approval application still must authenticate/authorize the approver, protect the token, bind the decision to evidence, and prevent replay.
- **Low-density:** Question 2 lists many unrelated Step Functions fields but never tests Standard versus Express callback support, same-account token return, timeouts, heartbeat, reject/expire branches, or approver identity.
- **Duplicate:** Questions 1, 4, and 5 all select Step Functions and the same generic audit/canary language.
- **Missing:** Notification versus workflow state, revalidation after approval, idempotent side effects, cross-account constraints, versions/aliases, sensitive execution data, and failure paths for abandoned approvals.

### Exactly ten replacement knowledge intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | Task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Decide which AI actions require human approval. | Classify by impact, reversibility, monetary/security boundary, confidence/evidence, and regulatory need; automate low-risk reversible actions only within explicit limits and escalate higher-risk cases. | Require approval for every read-only answer; auto-execute any action above a model-confidence threshold; remove approval whenever latency is inconvenient. | `SAP-2.3` | `EX-SAP`, `EX-SAP-D2` |
| 2 | Select the Step Functions workflow/integration pattern for a long approval. | Use a Standard Workflow with a supported `.waitForTaskToken` callback integration for a long external/human wait; Express Workflows do not support callback integration patterns. | Keep a Lambda invocation sleeping for days; use Express because it has higher throughput; use an SNS publish response as proof of approval. | `SAP-2.1` | `SF-CALLBACK`, `SF-INTEGRATION`, `EX-SAP` |
| 3 | Complete a callback safely. | Return the exact task token through `SendTaskSuccess` or `SendTaskFailure` from an authorized principal in the same AWS account as the token; treat completion as one workflow transition, not a reusable approval credential. | Return the token from any account; invoke `StartExecution` to complete the waiting task; reuse one token for several refunds. | `SAP-2.3` | `SF-CALLBACK`, `IAM-EVAL`, `EX-SAP-D2` |
| 4 | Secure an approval web/API endpoint. | Authenticate the human, authorize that user for the action/amount/tenant, bind the decision to request ID and evidence digest, keep the task token server-side, and expose only a short-lived application decision handle. | Put the raw task token in a public URL; accept an email click without current authentication; authorize solely because the token is syntactically valid. | `SAP-1.2`, `SAP-2.3` | `SF-CALLBACK`, `IAM-EVAL`, `EX-SAP-D1` |
| 5 | Configure abandoned-approval behavior. | Set an explicit task timeout and, where a worker protocol supports it, heartbeat behavior; route timeout, rejection, and malformed callback to separate states with escalation/compensation rather than waiting indefinitely. | Use SQS retention as the workflow timeout; retry the approval notification forever; treat timeout as automatic approval. | `SAP-2.4` | `SF-TASK`, `SF-CALLBACK`, `EX-SAP-D2` |
| 6 | Give an approver sufficient and bounded evidence. | Present the proposed action, affected resources/customer, policy/risk reason, model/retrieval evidence, expiration, and expected side effect while minimizing unrelated sensitive prompt/context data. | Show only “Approve?”; expose the complete hidden prompt and every retrieved record; let the model summarize away the exact amount/resource identifier. | `SAP-2.3` | `BR-DATA`, `AG-TRACE`, `SF-CALLBACK`, `EX-SAP` |
| 7 | Distinguish notification from durable approval state. | SNS/email/chat can notify an approver, but Step Functions owns the waiting state, timeout, and transition; delivery success is not an approval decision. | Treat an SNS delivery receipt as approval; store state only in the email inbox; republish notifications to roll back a completed action. | `SAP-2.4` | `SF-CALLBACK`, `SF-INTEGRATION`, `EX-SAP-D2` |
| 8 | Execute the side effect after approval without TOCTOU or duplication. | Revalidate current policy/resource state after approval, use an idempotency key tied to the approved request, atomically record execution status where possible, and require a new approval if material facts changed or approval expired. | Trust stale pre-approval authorization forever; retry a non-idempotent refund blindly; allow the model to change the amount after approval. | `SAP-2.4` | `SF-CALLBACK`, `IAM-EVAL`, `EX-SAP-D2` |
| 9 | Design a cross-account approval workflow. | Step Functions can assume a scoped target-account role for resource actions, but callback task tokens must be returned by a principal in the token's account; use a broker/API in that account rather than sending the callback directly from another account. | Send `SendTaskSuccess` directly from any target account; share one administrator role across all accounts; copy the state machine ARN and assume tokens become portable. | `SAP-1.4`, `SAP-2.3` | `SF-XACCOUNT`, `SF-CALLBACK`, `EX-SAP-D1` |
| 10 | Roll out and audit approval workflow changes. | Publish immutable state-machine versions, use aliases for controlled traffic shifting, preserve approver/action/outcome evidence with least-privilege retention, and test old in-flight executions plus rollback behavior. | Edit the latest definition in place and assume running executions change; log raw credentials with evidence; deploy a second Region without testing callback routing or target roles. | `SAP-2.1`, `SAP-3.1` | `SF-VERSION`, `SF-CALLBACK`, `BR-DATA`, `EX-SAP-D2`, `EX-SAP-D3` |

---

## Chapter 96 — AI Observability, Cost, and Failure Isolation

### Current-question defects

- **Duplicate/low-density:** Questions 2 and 4 again select the Chapter 91 Bedrock settings bundle. Neither tests observability configuration.
- **Factually unsafe:** The explanation credits generic Bedrock inference with measuring retrieval quality, tool success, guardrail rejection, and business outcome. These require separate service telemetry, traces, evaluation jobs, and application metrics.
- **Factually unsafe:** Choosing Bedrock plus model-access/VPC/KMS settings does not diagnose a wrong citation or a threefold token-cost increase.
- **Ambiguous:** CloudWatch is rejected as “only another service,” even though Bedrock publishes runtime metrics to CloudWatch and invocation logging can deliver to CloudWatch Logs. It is complementary, not an alternative.
- **Low-density:** The chapter mentions hallucination, cost, tools, and latency but never tests invocation-log enablement, token metrics, output-length effects, agent trace, RAG evaluation, model evaluation, cost allocation, or error classes.
- **Missing:** SageMaker endpoint drift boundaries, per-request versus aggregated cost attribution, sensitive traces/logs, 429 versus 503/529, retry storms, config/version regression, and business-success SLOs.

### Exactly ten replacement knowledge intents

| # | Knowledge coverage intent | Correct principle | Three plausible distractor concepts | Task mapping | Official source keys |
|---|---|---|---|---|---|
| 1 | Define an end-to-end AI operation trace and SLO set. | Correlate request ID across authentication, retrieval, prompt assembly, model invocation, guardrail, agent/tool calls, and business commit; measure quality, safety, latency, availability, and successful-task cost separately. | Use HTTP `200` as the only SLO; monitor only model latency; combine all failures into one “AI error” counter without stage labels. | `SAP-3.1`, `SAP-3.4` | `AG-TRACE`, `BR-METRIC`, `KB-EVAL`, `EX-SAP-D3` |
| 2 | Enable invocation logging without creating a data leak. | Invocation logging is opt-in and can contain model inputs/outputs for supported runtime operations; select destinations/content deliberately, restrict access, encrypt, set retention, and document endpoint/API coverage. | Assume logging is already enabled; grant all engineers access to raw prompts; use invocation logs as proof that a tool side effect committed. | `SAP-3.1`, `SAP-3.2` | `BR-LOG`, `BR-DATA`, `BR-CLOUDTRAIL`, `EX-SAP-D3` |
| 3 | Interpret Bedrock runtime CloudWatch metrics. | Use invocation/error/throttle/latency and input/output-token metrics for service behavior and demand; these metrics do not directly measure factuality, retrieval relevance, tenant authorization, or business success. | Infer hallucination rate from `InvocationLatency`; treat low throttles as proof of answer quality; calculate exact invoice cost from one token metric without pricing/context. | `SAP-3.3`, `SAP-3.5` | `BR-METRIC`, `EX-SAP-D3` |
| 4 | Diagnose a latency increase caused by longer answers versus slower generation. | Compare time to first token, output-token count, invocation latency, and derived output tokens per second; longer output can raise latency while generation throughput remains stable. | Scale retrieval because any latency increase is vector search; lower input-token count and ignore output length; alarm only on average latency across different models. | `SAP-3.3` | `BR-OTPS`, `BR-METRIC`, `EX-SAP-D3` |
| 5 | Use an agent trace to isolate a wrong or failed action. | Inspect the traced knowledge-base query/result, action-group input/output, orchestration step, and failure reason; protect trace data and correlate the trace with downstream transaction/audit records. | Treat trace reasoning text as authoritative business evidence; expose traces to end users by default; assume a successful tool return proves the external side effect committed exactly once. | `SAP-3.1`, `SAP-3.4` | `AG-TRACE`, `BR-DATA`, `EX-SAP-D3` |
| 6 | Evaluate RAG retrieval separately from answer generation. | Run retrieve-only evaluation for context relevance/coverage and retrieve-and-generate evaluation for response characteristics; compare configurations on a representative dataset with ground truth where the metric requires it. | Tune temperature before measuring retrieval; evaluate only final prose and ignore missing source chunks; use one anecdotal query as the release gate. | `SAP-3.3` | `KB-EVAL`, `KB-EVAL-METRICS`, `EX-SAP-D3` |
| 7 | Design a model-evaluation release gate. | Use fixed and adversarial datasets, appropriate automatic/LLM-judge/human review, versioned prompts/configuration, and explicit quality/safety/latency/cost thresholds; treat judge output as a measurement with limitations, not ground truth. | Promote the model with the highest single aggregate score; let the candidate model grade itself only; change model and prompt simultaneously without recording either version. | `SAP-3.1`, `SAP-3.2` | `BR-MODEL-EVAL`, `GR-TEST`, `EX-SAP-D3` |
| 8 | Choose Bedrock evaluation or SageMaker Model Monitor for the owned serving path. | Use Bedrock evaluation/telemetry for Bedrock GenAI/RAG behavior; use SageMaker Model Monitor/Clarify capabilities when operating SageMaker endpoints and monitoring applicable data/model/bias drift. Match the control to the service that owns inference. | Attach SageMaker Model Monitor directly to a Bedrock invocation; use a Bedrock guardrail as numeric feature-drift detection; assume either service supplies application business labels automatically. | `SAP-3.3` | `AI-DECIDE`, `KB-EVAL`, `SM-MONITOR`, `EX-SAP-D3` |
| 9 | Attribute Bedrock cost by application and request. | Use tagged application inference profiles for supported aggregated application/workload billing attribution and invocation/request metadata plus token logs for finer operational analysis; do not represent aggregated daily billing data as exact per-request cost. | Use a cross-Region profile as a cost-allocation tag; infer per-request dollars from CloudWatch latency; share one untagged model ID and allocate cost by guesswork. | `SAP-2.6`, `SAP-3.5` | `BR-COST-AIP`, `BR-METRIC`, `BR-LOG`, `EX-SAP-D2`, `EX-SAP-D3` |
| 10 | Isolate capacity failures and stop retry amplification during a config rollout. | Distinguish quota throttles (`429`) from transient capacity (`503`/`529`), cap concurrency, queue where appropriate, retry retryable errors with bounded backoff/jitter, and roll back the prompt/model/profile/config version when canary quality/cost/error gates regress. | Retry immediately with unbounded concurrency; request a quota increase for every `503`; keep a costly prompt because HTTP success rate is unchanged. | `SAP-2.4`, `SAP-3.4` | `BR-ERRORS`, `BR-SCALE`, `BR-METRIC`, `EX-SAP-D2`, `EX-SAP-D3` |

---

## Requested-topic coverage map

| Requested area | Primary intents |
|---|---|
| Bedrock | 91.2–91.10, 92.2–92.5, 96.2–96.4 |
| SageMaker AI | 91.1, 96.8 |
| RAG | 91.4–91.5, 92.6–92.8, 93.6, 96.6 |
| Agents | 91.6, 93.8, 94.1, 94.9, 96.5 |
| Guardrails | 91.7, 92.9, all Chapter 93 |
| AI operations | all Chapter 96 |
| Identity | 91.6, 92.6–92.7, all Chapter 94, 95.3–95.4 |
| Data boundaries | all Chapter 92; 93.4; 94.7; 96.2 |
| Evaluation | 92.10, 93.6 and 93.10, 96.6–96.8 |
| Configuration | 91.2–91.3 and 91.9, 92.3–92.8, 93.2–93.9, 94.2–94.9, 95.5 and 95.10, 96.2 and 96.9–96.10 |
| Failure modes | 91.10, 92.8, 93.7–93.10, 94.10, 95.5 and 95.8–95.10, 96.1–96.5 and 96.10 |

## Completion checks

- Chapters audited: 91, 92, 93, 94, 95, 96.
- Replacement knowledge intents: exactly 60 total, exactly 10 per chapter.
- Every intent includes one correct principle, exactly three plausible distractor concepts, project task mapping, and official AWS source keys.
- Product statements are bounded to the cited AWS service documentation and avoid claiming that a managed service supplies application authorization, factual correctness, tenant isolation, or side-effect safety automatically.
- Official samples/practice resources are mapped separately and no question text is copied.
- Intended artifact: `tools/aws_exam_audits/part_09.md`; no other file should be edited for P09.

SUPERSET_WORKER_DONE task P09-audit
