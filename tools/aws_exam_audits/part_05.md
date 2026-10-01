# Part 05 Audit — Chapters 52–60: Integration / Distributed Systems

Scope: audit only. This file records defects in the current five-question chapter sets and specifies ten replacement **question intents** per chapter. It deliberately does not reproduce AWS exam questions or provide ready-to-publish question dumps.

## Source key

- `EX-SAA2` — [SAA-C03 Domain 2: Design Resilient Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain2.html)
- `EX-SAA3` — [SAA-C03 Domain 3: Design High-Performing Architectures](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain3.html)
- `EX-SAP2` — [SAP-C02 Domain 2: Design for New Solutions](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain2.html)
- `EX-SAP3` — [SAP-C02 Domain 3: Continuous Improvement](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)
- `EX-SAP4` — [SAP-C02 Domain 4: Migration and Modernization](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain4.html)
- `SQS-VIS` — [Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)
- `SQS-DLQ` — [Amazon SQS dead-letter queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)
- `SQS-FIFO` — [Exactly-once processing in Amazon SQS FIFO queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues-exactly-once-processing.html)
- `SQS-RET` — [Amazon SQS message retention period](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/quotas-messages.html)
- `SQS-LONG` — [Amazon SQS short and long polling](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-short-and-long-polling.html)
- `SQS-METRIC` — [Available CloudWatch metrics for Amazon SQS](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)
- `SQS-POLICY` — [Access management for encrypted SQS queues with least-privilege policies](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-least-privilege-policy.html)
- `SQS-SSE` — [Configuring server-side encryption for an SQS queue](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-configure-sse-existing-queue.html)
- `LAMBDA-SQS` — [Using Lambda with Amazon SQS](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
- `SNS-FANOUT` — [Fanout Amazon SNS notifications to Amazon SQS queues](https://docs.aws.amazon.com/sns/latest/dg/sns-sqs-as-subscriber.html)
- `SNS-FILTER` — [Amazon SNS subscription filter policies](https://docs.aws.amazon.com/sns/latest/dg/sns-subscription-filter-policies.html)
- `SNS-DELIVERY` — [Amazon SNS message delivery retries](https://docs.aws.amazon.com/sns/latest/dg/sns-message-delivery-retries.html)
- `SNS-FIFO` — [Amazon SNS FIFO topics](https://docs.aws.amazon.com/sns/latest/dg/sns-fifo-topics.html)
- `EB-PATTERN` — [Amazon EventBridge event patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)
- `EB-RETRY` — [Event retry policy and dead-letter queues](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-retry-policy.html)
- `EB-ARCHIVE` — [Archiving and replaying events in Amazon EventBridge](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-archive-event.html)
- `EB-XACCOUNT` — [Sending and receiving Amazon EventBridge events between AWS accounts](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-cross-account.html)
- `KDS-FUND` — [Amazon Kinesis Data Streams terminology and concepts](https://docs.aws.amazon.com/streams/latest/dev/key-concepts.html)
- `KDS-CAP` — [Kinesis Data Streams quotas and limits](https://docs.aws.amazon.com/streams/latest/dev/service-sizes-and-limits.html)
- `KDS-EFO` — [Developing consumers with enhanced fan-out](https://docs.aws.amazon.com/streams/latest/dev/enhanced-consumers.html)
- `KDS-RET` — [Changing the Kinesis Data Streams data retention period](https://docs.aws.amazon.com/streams/latest/dev/kinesis-extended-retention.html)
- `KDS-MON` — [Monitoring Kinesis Data Streams](https://docs.aws.amazon.com/streams/latest/dev/monitoring-with-cloudwatch.html)
- `SF-TYPE` — [Standard and Express Workflows](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html)
- `SF-ERROR` — [Handling errors in Step Functions workflows](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html)
- `SF-CALLBACK` — [Callback with task token](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html#connect-wait-token)
- `SF-INTEGRATION` — [Integrating services with Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/integrate-services.html)
- `SF-LOG` — [Logging Step Functions executions](https://docs.aws.amazon.com/step-functions/latest/dg/cw-logs.html)
- `SDK-RETRY` — [AWS SDK retry behavior](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html)
- `WA-RETRY` — [REL05-BP03 Control and limit retry calls](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html)
- `PG-TIMEOUT` — [Timeout, retry, and backoff with jitter](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/retry-backoff.html)
- `PG-CIRCUIT` — [Circuit breaker pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/circuit-breaker.html)
- `PG-SAGA` — [Saga orchestration pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/saga-orchestration.html)
- `PG-OUTBOX` — [Transactional outbox pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
- `DDB-COND` — [DynamoDB condition expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)
- `DDB-TXN` — [DynamoDB transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transactions.html)
- `LAMBDA-IDEMP` — [AWS Lambda Powertools idempotency utility](https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/)
- `LAMBDA-CONC` — [Configuring reserved concurrency for Lambda](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)
- `WA-QUEUE` — [REL05-BP06 Make systems stateless where possible](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_stateless.html)
- `WA-ASYNC` — [REL04-BP04 Make all responses idempotent](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure_idempotent.html)

---

## Chapter 52 — SQS Standard, FIFO, Visibility, and DLQ

### Existing defects

- Only five template-shaped questions exist; service selection, settings, mechanism, distractor recognition, and enterprise governance are repeated instead of testing ten independent SQS decisions.
- Question 1 marks visibility timeout and DLQ configuration as an alternative, although both are required by the stated 1–10 minute worker scenario. The item is therefore ambiguous.
- Question 2 treats all SQS settings as one correct bundle. It cannot tell whether the learner understands which field controls invisibility, retention, receive cost, ordering, or poison-message isolation.
- Question 3 understates Standard queue duplicate delivery and does not test receipt handles, in-flight messages, visibility extension, or delete-after-commit.
- Question 5 uses generic multi-account/canary language that is weakly related to queue semantics and fails to test queue policies, redrive allow policies, alarms, or consumer recovery.
- Missing coverage: Standard versus FIFO throughput/ordering trade-off, message group parallelism, retention clock behavior after DLQ movement, long polling, Lambda partial batch response, backlog-age diagnosis, and concrete redrive configuration.

### Ten replacement intents

1. **Intent — Select Standard versus FIFO for a bursty image pipeline.**
   - Correct principle: choose Standard when maximum throughput and loose ordering are acceptable; choose FIFO only when ordering/deduplication is a business requirement, then distribute independent work across message groups.
   - Three realistic distractors: choose FIFO merely because it sounds more reliable; choose SNS because it pushes notifications; choose Kinesis because all asynchronous work is assumed to require replay.
   - Metadata: `SAA | SAA-2.1 | EX-SAA2, SQS-FIFO`

2. **Intent — Set and extend visibility timeout for variable 1–10 minute processing.**
   - Correct principle: set visibility above normal processing time, extend it with `ChangeMessageVisibility` for long jobs, and delete only after the side effect commits; timeout expiry permits redelivery, not cancellation.
   - Three realistic distractors: set visibility equal to producer latency; delete on receive to prevent duplicates; increase retention instead of visibility.
   - Metadata: `SAA | SAA-2.2 | SQS-VIS`

3. **Intent — Design a poison-message DLQ and redrive policy.**
   - Correct principle: configure `RedrivePolicy` with a tested `maxReceiveCount`, grant the source through the DLQ redrive allow policy where needed, alarm on the DLQ, fix the cause, then redrive deliberately.
   - Three realistic distractors: use a DLQ as permanent archival storage; set `maxReceiveCount=1` for every transient failure; automatically redrive continuously without correcting the consumer.
   - Metadata: `SAA | SAA-2.2 | SQS-DLQ, SQS-METRIC`

4. **Intent — Reason about source/DLQ retention and message age.**
   - Correct principle: make DLQ retention longer than source retention; for Standard queues the original enqueue timestamp is retained when moved, while FIFO enqueue time resets on DLQ movement.
   - Three realistic distractors: retention starts over for every Standard redrive; visibility timeout determines deletion date; DLQ messages never expire.
   - Metadata: `SAP | SAP-3.4 | SQS-DLQ, SQS-RET`

5. **Intent — Reduce empty receives and cost for intermittent consumers.**
   - Correct principle: enable long polling with `ReceiveMessageWaitTimeSeconds` up to 20 seconds and ensure the client HTTP timeout exceeds the wait time.
   - Three realistic distractors: set visibility timeout to 20 seconds; use short polling more frequently; increase message retention to reduce empty responses.
   - Metadata: `SAA | SAA-2.1 | SQS-LONG`

6. **Intent — Preserve per-order ordering while scaling unrelated orders.**
   - Correct principle: use a FIFO queue with `MessageGroupId=order_id`; ordering is within a group, while many groups provide parallelism. Deduplication IDs suppress duplicate sends only within the documented deduplication window.
   - Three realistic distractors: use one constant message group for the whole company; use a Standard queue with a sort attribute; assume content-based dedup removes duplicate business effects forever.
   - Metadata: `SAA | SAA-2.1 | SQS-FIFO`

7. **Intent — Configure Lambda consumption without replaying an entire failed batch.**
   - Correct principle: tune batch size/window and event-source concurrency, make handlers idempotent, and return partial batch failures so successfully processed records are not retried with failed records.
   - Three realistic distractors: delete messages manually before Lambda returns; set queue retention to zero; disable all retries and drop failures.
   - Metadata: `SAA | SAA-2.2 | LAMBDA-SQS, WA-ASYNC`

8. **Intent — Diagnose a growing queue during a promotion.**
   - Correct principle: compare arrival and processing rates; use `ApproximateAgeOfOldestMessage`, visible/in-flight counts, error/throttle metrics, and downstream latency. Scale consumers or shed expired work rather than merely increasing retention.
   - Three realistic distractors: conclude that low EC2 CPU proves sufficient capacity; monitor only total messages ever sent; increase retention and claim throughput improved.
   - Metadata: `SAP | SAP-3.3 | SQS-METRIC`

9. **Intent — Secure a cross-account producer and encrypted queue.**
   - Correct principle: use a least-privilege SQS resource policy for the external principal plus producer identity permissions, require TLS, and authorize KMS use when a customer-managed key is selected.
   - Three realistic distractors: make the queue public and rely on an unguessable URL; attach only an IAM policy in the queue owner account to a foreign principal; assume SSE automatically authorizes KMS use.
   - Metadata: `SAP | SAP-2.4 | EX-SAP2, SQS-POLICY, SQS-SSE`

10. **Intent — Review concrete CloudFormation for a production worker queue.**
    - Correct principle: recognize `VisibilityTimeout`, `ReceiveMessageWaitTimeSeconds`, `MessageRetentionPeriod`, `RedrivePolicy`, encryption, and a longer-lived DLQ; validate values against processing latency and recovery time.
    - Three realistic distractors: put `maxReceiveCount` on the DLQ rather than source queue; substitute `DelaySeconds` for visibility; omit monitoring because redrive is configured.
    - Metadata: `SAP | SAP-3.1 | SQS-VIS, SQS-DLQ, SQS-LONG`

---

## Chapter 53 — SNS, EventBridge, and Publish–Subscribe

### Existing defects

- The chapter title covers two routing services plus SQS fan-out, but current questions silently appoint SNS as the primary answer even when the prompt explicitly requires content-based routing, making SNS and EventBridge both plausible.
- The “correct” choice in Question 1 is a comparison sentence, not an executable architecture; it does not establish whether subscribers require queues, replay, ordering, or push delivery.
- Questions 2–4 repeat profile text and test recognition of service names rather than filter scope, delivery policy, retry/DLQ ownership, event-bus policy, or target permissions.
- The existing set does not distinguish SNS subscription filtering from EventBridge event patterns, SNS FIFO from EventBridge ordering, or archive/replay from durable stream retention.
- Cross-account event buses, per-subscriber SQS buffering, raw message delivery, target DLQs, schema evolution, and failure diagnosis are absent.

### Ten replacement intents

1. **Intent — Choose SNS, EventBridge, SQS, or Kinesis from delivery semantics.**
   - Correct principle: use SNS for direct push fan-out, EventBridge for rule-based event routing/integration, SQS for durable pull buffering/backpressure, and Kinesis for ordered retained streams with independent replaying consumers.
   - Three realistic distractors: select SNS whenever there is JSON; select EventBridge whenever more than one consumer exists; select SQS when every consumer must independently receive the same message without separate queues.
   - Metadata: `SAA | SAA-2.1 | SNS-FANOUT, EB-PATTERN, EX-SAA2`

2. **Intent — Build durable fan-out to independently scaling subscribers.**
   - Correct principle: publish once to SNS and subscribe one SQS queue per consumer; each queue owns its backlog, retry, DLQ, permissions, and scaling policy.
   - Three realistic distractors: attach all workers to one shared queue and expect each to see every message; call all services synchronously from the producer; subscribe email endpoints for machine processing.
   - Metadata: `SAA | SAA-2.2 | SNS-FANOUT`

3. **Intent — Apply filtering at the correct layer.**
   - Correct principle: use SNS filter policies on message attributes or body for subscriptions; use EventBridge event patterns against the event envelope/detail. Validate missing fields and numeric/string matching explicitly.
   - Three realistic distractors: filter only inside every consumer and claim no unwanted delivery cost; put an EventBridge pattern on an SNS subscription; assume `"300"` and numeric `300` always match identically.
   - Metadata: `SAA | SAA-2.1 | SNS-FILTER, EB-PATTERN`

4. **Intent — Configure delivery retries and DLQs without confusing service roles.**
   - Correct principle: SNS delivery behavior depends on endpoint protocol and delivery policy; EventBridge retries target delivery and can send exhausted events to an SQS DLQ. A target DLQ does not replace consumer-level failure handling.
   - Three realistic distractors: attach an SNS topic as an EventBridge DLQ; assume EventBridge retries forever; use the source event bus archive as a poison-message DLQ.
   - Metadata: `SAA | SAA-2.2 | SNS-DELIVERY, EB-RETRY`

5. **Intent — Decide whether replay requirements fit EventBridge archive.**
   - Correct principle: EventBridge archive/replay can re-submit matching historical events to an event bus, but it is not a partitioned ordered log; choose Kinesis/MSK for sustained ordered replay and consumer offsets.
   - Three realistic distractors: claim archive preserves global event order; use SNS message retention for month-long replay; use an SQS DLQ as the primary analytics event store.
   - Metadata: `SAP | SAP-2.5 | EB-ARCHIVE, KDS-FUND`

6. **Intent — Preserve ordering across SNS-to-SQS fan-out.**
   - Correct principle: use an SNS FIFO topic with SQS FIFO subscriptions, compatible message group/deduplication design, and understand that non-SQS endpoint types are not equivalent FIFO subscribers.
   - Three realistic distractors: connect an SNS Standard topic to FIFO queues and claim end-to-end order; use one global message group and expect high parallelism; assume EventBridge rules preserve producer order.
   - Metadata: `SAA | SAA-2.1 | SNS-FIFO, SQS-FIFO`

7. **Intent — Authorize cross-account EventBridge publication and targeting.**
   - Correct principle: combine event-bus resource policy, sender identity permission, target permissions/role where required, and narrowly scoped organization/account conditions.
   - Three realistic distractors: grant `events:*` to everyone because the bus is not public HTTP; add only a target Lambda execution role; rely on matching rules as an authorization boundary.
   - Metadata: `SAP | SAP-2.4 | EB-XACCOUNT`

8. **Intent — Diagnose “rule matched but target received nothing.”**
   - Correct principle: inspect matched/invocation/failed-invocation metrics, event-pattern shape, target resource policy or invocation role, retry age/attempts, DLQ permissions, and target throttling.
   - Three realistic distractors: increase archive retention first; alter DNS because EventBridge uses service endpoints; assume successful `PutEvents` proves target delivery.
   - Metadata: `SAP | SAP-3.4 | EB-PATTERN, EB-RETRY`

9. **Intent — Evolve an event contract safely across many consumers.**
   - Correct principle: publish facts with stable source/detail-type, version schemas compatibly, make consumers ignore unknown fields, and use new event versions for breaking semantic changes.
   - Three realistic distractors: rename existing fields in place because EventBridge is schemaless; publish commands naming every consumer; let each consumer infer business meaning from free-form text.
   - Metadata: `SAP | SAP-4.4 | EB-PATTERN, EX-SAP4`

10. **Intent — Review a concrete paid-order EventBridge rule.**
    - Correct principle: match `source`, `detail-type`, and `detail.status=PAID`; send each slow or failure-sensitive consumer through its own SQS queue and configure target retry/DLQ plus least-privilege permissions.
    - Three realistic distractors: place `status` at the event root when producers put it under `detail`; route directly to several fragile HTTP targets without buffering; treat an input transformer as a filter.
    - Metadata: `SAA → SAP | SAA-2.1 / SAP-2.4 | EB-PATTERN, EB-RETRY`

---

## Chapter 54 — Kinesis Ordering, Partitioning, and Consumer Scaling

### Existing defects

- Question 2 contains two byte-for-byte identical Kinesis configuration choices but marks only one correct.
- Question 3 contains two byte-for-byte identical mechanism choices but marks only one correct. Both questions are invalid.
- The current questions conflate partition-key design, capacity mode, enhanced fan-out, and Firehose delivery into broad bundles instead of testing their distinct effects.
- “Each shard has sequence order” is too loose: ordering is observed in shard order, while producer retries, aggregation, resharding, and multi-shard business keys still require careful semantics.
- Missing coverage: per-shard read/write limits, hot partitions, `PutRecords` partial failures, iterator age diagnosis, resharding, on-demand versus provisioned mode, retention/replay, KCL leases/checkpoints, and EFO cost/trade-offs.

### Ten replacement intents

1. **Intent — Select Kinesis Data Streams instead of SQS, SNS, or Firehose.**
   - Correct principle: use Kinesis Data Streams when multiple consumers need a retained, replayable stream with ordering per partition-key/shard path; use SQS for work distribution and Firehose for managed delivery to destinations.
   - Three realistic distractors: use one SQS queue so every consumer independently sees every record; use Firehose for arbitrary low-latency stateful consumer code; use SNS as a multi-day replay log.
   - Metadata: `SAA | SAA-3.5 | KDS-FUND, EX-SAA3`

2. **Intent — Choose a partition key that preserves required order without a hot shard.**
   - Correct principle: use the smallest business key whose events must be ordered, such as `customer_id`; distribute unrelated keys broadly and avoid low-cardinality constants.
   - Three realistic distractors: use `tenant` when one tenant generates most traffic; randomize every record key despite per-order ordering; use event timestamp, which can cluster bursts and destroy entity order.
   - Metadata: `SAA | SAA-3.5 | KDS-FUND`

3. **Intent — Calculate provisioned shard capacity from read/write demand.**
   - Correct principle: account for per-shard record/byte write limits and read limits, number of consumers, headroom, and hot-key skew; shard count is not derived from average events alone.
   - Three realistic distractors: size only from daily storage volume; assume EFO increases write capacity; assume adding consumers automatically creates shards.
   - Metadata: `SAA | SAA-3.5 | KDS-CAP`

4. **Intent — Decide between on-demand and provisioned capacity mode.**
   - Correct principle: use on-demand for unpredictable traffic and reduced capacity management; use provisioned when traffic is predictable and explicit shard planning/control is justified, while still respecting partition-key distribution and service limits.
   - Three realistic distractors: use on-demand to guarantee no throttling under any jump; use provisioned because retention requires shards; switch to EFO to remove producer throttling.
   - Metadata: `SAA | SAA-3.5 | KDS-CAP`

5. **Intent — Isolate several high-throughput consumers.**
   - Correct principle: enhanced fan-out gives registered consumers dedicated read throughput and push-style HTTP/2 delivery per shard; shared-throughput polling consumers compete for shard read capacity.
   - Three realistic distractors: EFO creates a copy of the stream per consumer; EFO increases producer write throughput; Firehose is required before every EFO consumer.
   - Metadata: `SAA | SAA-3.5 | KDS-EFO`

6. **Intent — Handle `PutRecords` partial failure correctly.**
   - Correct principle: inspect each record result, retry only failed records with bounded backoff/jitter, preserve the partition key, and make downstream effects idempotent because producer retries can duplicate records.
   - Three realistic distractors: retry the entire successful-and-failed batch indefinitely; treat HTTP 200 as all records accepted; change failed records to random keys and claim ordering remains.
   - Metadata: `SAP | SAP-3.4 | KDS-FUND, WA-RETRY`

7. **Intent — Diagnose rising `IteratorAgeMilliseconds`.**
   - Correct principle: determine whether consumers are underprovisioned, throttled, erroring, blocked on a downstream dependency, or concentrated on hot shards; scale consumer processing and/or reshard based on the actual bottleneck.
   - Three realistic distractors: increase stream retention and call the lag fixed; increase producer rate to rebalance reads; monitor only incoming bytes.
   - Metadata: `SAP | SAP-3.3 | KDS-MON`

8. **Intent — Plan retention and replay after a consumer defect.**
   - Correct principle: set retention to cover detection plus repair/replay time, store consumer checkpoints independently, and replay from the required sequence/timestamp while protecting downstream idempotency.
   - Three realistic distractors: rely on checkpoints as backups of record payloads; assume default retention is permanent; replay by republishing into the same partition with new random keys.
   - Metadata: `SAP | SAP-3.4 | KDS-RET, KDS-FUND`

9. **Intent — Scale KCL consumers and understand leases.**
   - Correct principle: KCL workers coordinate shard leases and checkpoints; useful parallelism is bounded by active shards, and resharding changes child-shard assignment rather than making unlimited threads useful.
   - Three realistic distractors: run hundreds of workers against one shard to multiply ordered throughput; share one checkpoint across unrelated applications; checkpoint before a non-idempotent side effect commits.
   - Metadata: `SAP | SAP-2.5 | KDS-FUND`

10. **Intent — Review a concrete three-consumer stream architecture.**
    - Correct principle: partition by user/order identity, choose mode/shard capacity from traffic, use EFO for consumers needing isolated throughput, alarm on write throttles and iterator age, retain enough for recovery, and encrypt/control access.
    - Three realistic distractors: use a constant partition key to ensure global ordering; send the stream through one shared SQS queue for all consumers; use Firehose as the only path even when consumers require custom per-record processing and replay.
    - Metadata: `SAA → SAP | SAA-3.5 / SAP-2.5 | KDS-CAP, KDS-EFO, KDS-MON`

---

## Chapter 55 — Step Functions, Workflows, and Human Approval

### Existing defects

- Question 2 has two overlapping valid configuration answers but declares only one correct.
- Question 3 has two substantively correct descriptions—durable state transitions/task tokens and ASL/service integrations/execution history—but declares only one correct.
- The set names Standard and Express without testing their execution semantics, duration, delivery guarantees, pricing dimensions, observability, or supported integration patterns.
- Human approval is mentioned but no question tests callback-token secrecy, heartbeat/timeout, one-time completion, or evidence shown to an approver.
- Missing coverage: `Retry`/`Catch` ordering, `States.ALL` constraints, service-integration patterns, Map/Distributed Map, execution redrive, payload/history limits, compensation versus rollback, and least-privilege execution roles.

### Ten replacement intents

1. **Intent — Choose Standard versus Express for a 72-hour approval workflow.**
   - Correct principle: use Standard for long-running, auditable, durable workflows and callback waits; Express is intended for high-volume, short-duration workloads and has different execution/delivery/observability semantics.
   - Three realistic distractors: use Express because it is always cheaper; keep a Lambda invocation sleeping for 72 hours; use EventBridge Scheduler alone to represent the whole branching workflow.
   - Metadata: `SAA | SAA-2.1 | SF-TYPE`

2. **Intent — Select Request Response, Run a Job, or Wait for Callback.**
   - Correct principle: use request-response for immediate API completion, `.sync` for supported jobs whose completion Step Functions tracks, and `.waitForTaskToken` for external/human completion.
   - Three realistic distractors: poll from a Lambda loop; use a Wait state as proof that an external job succeeded; expose the task token in a public approval URL without identity checks.
   - Metadata: `SAA | SAA-2.1 | SF-INTEGRATION, SF-CALLBACK`

3. **Intent — Configure safe retries for a payment task.**
   - Correct principle: retry only transient/throttling errors with bounded attempts/backoff/jitter where available, catch terminal errors, and make payment idempotent because workflow retries do not undo side effects.
   - Three realistic distractors: retry `States.ALL` forever; retry business validation failures; rely on Standard workflow durability as exactly-once payment execution.
   - Metadata: `SAA | SAA-2.2 | SF-ERROR, WA-RETRY`

4. **Intent — Order `Retry` and `Catch` rules correctly.**
   - Correct principle: Step Functions evaluates retriers and catchers in array order; specific errors should precede broad matches, and `States.ALL` must be last and alone in its catcher/retrier entry where required.
   - Three realistic distractors: put `States.ALL` first; assume Catch runs before Retry; use `States.Timeout` to catch every nested execution failure.
   - Metadata: `SAP | SAP-2.4 | SF-ERROR`

5. **Intent — Model parallel checks and aggregate their results.**
   - Correct principle: use Parallel for a fixed set of concurrent branches and Map/Distributed Map for collections; define failure tolerance and output shaping rather than spawning unbounded Lambda fan-out.
   - Three realistic distractors: use Choice to run branches concurrently; put a Wait state between sequential checks and call it parallel; use one Lambda to orchestrate thousands of child calls without backpressure.
   - Metadata: `SAA | SAA-2.1 | SF-INTEGRATION`

6. **Intent — Implement secure human approval.**
   - Correct principle: pause with a task token, authenticate/authorize the approver, bind the decision to workflow/request context, set heartbeat/timeout where appropriate, prevent token replay, and store decision evidence.
   - Three realistic distractors: email an unauthenticated yes/no URL; log full tokens in broadly readable logs; assume an SNS delivery receipt is approval.
   - Metadata: `SAP | SAP-2.4 | SF-CALLBACK, SF-LOG`

7. **Intent — Distinguish compensation from database rollback.**
   - Correct principle: a saga compensating task is a new business action that semantically reverses a prior committed action; it can fail and must be idempotent, observable, and retryable.
   - Three realistic distractors: assume Catch automatically rolls back all prior services; keep one cross-service database transaction open for days; delete execution history to undo side effects.
   - Metadata: `SAP | SAP-2.4 | PG-SAGA, SF-ERROR`

8. **Intent — Diagnose a workflow stuck or repeatedly failing.**
   - Correct principle: inspect execution history/CloudWatch logs, current state, service-integration permissions, timeout/heartbeat, retry counts, payload/history limits, and downstream throttles before redrive or starting a replacement execution.
   - Three realistic distractors: increase Lambda memory for every state; delete and recreate the state machine immediately; infer application success from `StartExecution` acceptance.
   - Metadata: `SAP | SAP-3.1 | SF-LOG, SF-ERROR`

9. **Intent — Secure the state-machine execution role and data.**
   - Correct principle: grant only actions/resources used by service integrations, protect sensitive inputs/outputs/logs, and avoid passing secrets or oversized documents through every state.
   - Three realistic distractors: attach AdministratorAccess because integrations are dynamic; rely on the caller’s permissions after execution starts; put credentials directly in ASL parameters.
   - Metadata: `SAP | SAP-2.4 | SF-INTEGRATION, SF-LOG`

10. **Intent — Review concrete ASL containing payment, retry, callback, timeout, and compensation.**
    - Correct principle: verify transient-only retry, explicit task timeout, callback heartbeat/timeout, terminal Catch path, idempotent payment/compensation, and an execution type compatible with long waits.
    - Three realistic distractors: accept `States.ALL` before specific errors; accept Express for a multi-day callback; treat a `Succeed` state as proof all external side effects committed exactly once.
    - Metadata: `SAA → SAP | SAA-2.2 / SAP-3.4 | SF-TYPE, SF-ERROR, SF-CALLBACK`

---

## Chapter 56 — Retry, Backoff, Jitter, and Timeout

### Existing defects

- The service-profile alias maps “AWS SDK retry behavior” to Amazon SQS, corrupting Questions 2–4.
- Question 2 marks SQS queue settings as the correct SDK retry configuration.
- Question 3 marks the SQS receive/visibility/delete lifecycle as the SDK retry mechanism.
- Question 4 again recommends configuring SQS fields as the answer to a synchronous retry-storm problem.
- The only sound statements are broad prose in Questions 1 and 5; they do not test retryable error classification, retry ownership, adaptive versus standard SDK mode, token buckets, jitter, deadline budgeting, or `Retry-After`.
- Existing distractors are generic (“buy more capacity,” “deploy all services”) and do not resemble realistic timeout/retry mistakes.

### Ten replacement intents

1. **Intent — Classify which failures are safe and useful to retry.**
   - Correct principle: retry transient connection failures, throttling, and selected 5xx responses only when the operation is idempotent or protected by an idempotency token; do not retry validation/auth failures without a state change.
   - Three realistic distractors: retry every 4xx; never retry throttling; retry non-idempotent payment submission with a new token each time.
   - Metadata: `SAA | SAA-2.2 | SDK-RETRY, PG-TIMEOUT`

2. **Intent — Set a timeout budget across a call chain.**
   - Correct principle: derive per-attempt connection/request timeouts and retry count from one end-to-end deadline, leaving time for upstream handling; a downstream timeout must not exceed the caller’s remaining budget.
   - Three realistic distractors: set every layer to the same 30-second timeout; omit connect/TLS timeout because request timeout exists; allow each retry to restart an unlimited deadline.
   - Metadata: `SAP | SAP-2.4 | WA-RETRY, PG-TIMEOUT`

3. **Intent — Prevent synchronized retry storms.**
   - Correct principle: use capped exponential backoff with jitter and bounded attempts; jitter spreads client retries so recovery capacity is not hit simultaneously.
   - Three realistic distractors: retry immediately three times; use deterministic exponential backoff without jitter for millions of clients; add a fixed one-second sleep forever.
   - Metadata: `SAA | SAA-2.2 | PG-TIMEOUT`

4. **Intent — Assign retry ownership in a five-layer system.**
   - Correct principle: place retries at the layer with enough semantic knowledge, disable or tightly bound redundant lower/upper retries, and calculate total amplification before deployment.
   - Three realistic distractors: allow every layer three retries because each setting is small; retry only at the database regardless of operation semantics; hide retries from metrics.
   - Metadata: `SAP | SAP-3.4 | WA-RETRY`

5. **Intent — Choose AWS SDK standard versus adaptive retry mode.**
   - Correct principle: standard mode is the generally recommended cross-service default; adaptive mode adds client-side rate limiting and should be used only when clients are pooled at the throttling-resource scope, otherwise one throttled resource can delay unrelated calls.
   - Three realistic distractors: adaptive mode guarantees no throttling; legacy mode is preferred for new applications; adaptive mode should share one client across all Regions and tables.
   - Metadata: `SAP | SAP-2.5 | SDK-RETRY`

6. **Intent — Respect service throttling feedback.**
   - Correct principle: honor retryable/throttling responses and `Retry-After` where supplied, reduce offered load, and combine client retry limits with concurrency/rate controls.
   - Three realistic distractors: treat 429 as permanent data corruption; ignore server delay hints and retry faster; increase socket timeout as the only throttle response.
   - Metadata: `SAA | SAA-2.2 | SDK-RETRY, WA-RETRY`

7. **Intent — Move retries to a queue when immediate completion is unnecessary.**
   - Correct principle: enqueue failed asynchronous work with controlled delay/redrive and DLQ handling; this changes the user contract to eventual completion and still requires idempotency and age limits.
   - Three realistic distractors: put every synchronous authorization request on a queue without changing the API contract; use queue retention as retry frequency; redrive poison messages infinitely.
   - Metadata: `SAA | SAA-2.1 | SQS-VIS, SQS-DLQ`

8. **Intent — Combine circuit breaking with retry without creating two amplifiers.**
   - Correct principle: bounded retries handle brief faults; a circuit breaker stops calls during sustained failure, probes recovery in half-open state, and provides fallback/load shedding where business-safe.
   - Three realistic distractors: retry inside an open circuit; use a circuit breaker to make non-idempotent operations safe; reset the breaker on every process restart without shared/appropriate state considerations.
   - Metadata: `SAP | SAP-3.4 | PG-CIRCUIT, WA-RETRY`

9. **Intent — Diagnose a post-deployment increase in downstream traffic.**
   - Correct principle: correlate original requests with attempts, throttle/timeout rates, retry quotas, latency percentiles, and layer-specific retry logs; an unchanged business request rate can still produce amplified downstream load.
   - Three realistic distractors: use only successful request count; attribute all added traffic to users; raise max attempts before identifying the retrying layer.
   - Metadata: `SAP | SAP-3.1 | SDK-RETRY, WA-RETRY`

10. **Intent — Review concrete SDK retry configuration.**
    - Correct principle: identify retry mode, bounded `max_attempts`, connection/request timeouts, idempotency token strategy, and metrics; verify that total worst-case duration fits the caller deadline.
    - Three realistic distractors: configure SQS visibility fields as SDK retries; set `max_attempts=0` and claim backoff is enabled; set a high retry count with no timeout because the SDK uses jitter.
    - Metadata: `SAA → SAP | SAA-2.2 / SAP-2.4 | SDK-RETRY, PG-TIMEOUT`

---

## Chapter 57 — Idempotency, Deduplication, and the Exactly-Once Illusion

### Existing defects

- Current questions bind the conceptual requirement to generic DynamoDB service selection and test table capacity/index settings that are unrelated to idempotency correctness.
- Question 3’s correct answer describes DynamoDB partitioning, not idempotency state transitions or duplicate-request behavior.
- Question 4 recommends an entire DynamoDB configuration checklist, although idempotency specifically needs a conditional claim/write, stable key, stored result/status, expiry policy, and race handling.
- FIFO deduplication is named but its limited deduplication interval and send-side scope are not tested.
- Missing coverage: stable business idempotency keys, in-progress versus completed records, atomic conditional writes, response replay, TTL limitations, concurrent duplicates, transactional side effects, consumer idempotency, and observability.

### Ten replacement intents

1. **Intent — Choose a stable idempotency key for payment creation.**
   - Correct principle: the client reuses one operation key for retries of the same logical payment; scope it to tenant/operation and reject incompatible payload reuse.
   - Three realistic distractors: generate a new UUID on every retry; use transport request ID assigned by each gateway hop; deduplicate only by current timestamp.
   - Metadata: `SAA | SAA-2.2 | LAMBDA-IDEMP, WA-ASYNC`

2. **Intent — Claim an operation atomically under concurrent duplicate requests.**
   - Correct principle: use a conditional put/update such as “key does not exist” to create an `IN_PROGRESS` record; only one caller performs the side effect and others observe/wait/replay according to policy.
   - Three realistic distractors: read then unconditionally write; rely on eventually consistent reads to serialize writers; store the key after charging the card.
   - Metadata: `SAA | SAA-2.2 | DDB-COND, LAMBDA-IDEMP`

3. **Intent — Return the original result after a successful duplicate.**
   - Correct principle: persist completion status and enough response/reference data to return the same logical outcome without repeating the side effect.
   - Three realistic distractors: return a generic error for every duplicate; execute again because the first HTTP response was lost; delete the idempotency record immediately after success.
   - Metadata: `SAA | SAA-2.2 | LAMBDA-IDEMP`

4. **Intent — Recover an idempotency record left `IN_PROGRESS` by a crash.**
   - Correct principle: use an in-progress expiry/lease and operation-specific reconciliation; after expiry, determine whether the external side effect committed before safely retrying.
   - Three realistic distractors: assume `IN_PROGRESS` means no side effect occurred; immediately delete all in-progress records; wait forever to avoid duplicates.
   - Metadata: `SAP | SAP-3.4 | LAMBDA-IDEMP, DDB-COND`

5. **Intent — Distinguish SQS FIFO deduplication from business idempotency.**
   - Correct principle: FIFO dedup suppresses duplicate sends within its documented window; it does not cover later re-publication, consumer side-effect retries, or duplicate requests arriving by another channel.
   - Three realistic distractors: claim FIFO makes payment processing exactly once; use a new deduplication ID on retry; omit consumer idempotency because order is preserved.
   - Metadata: `SAA | SAA-2.1 | SQS-FIFO, WA-ASYNC`

6. **Intent — Make an SQS/Lambda batch consumer idempotent.**
   - Correct principle: derive a business event identity, conditionally record/process it, commit the side effect before acknowledging success, and use partial batch failure for only failed records.
   - Three realistic distractors: deduplicate only by Lambda invocation ID; acknowledge the batch before writes complete; assume visibility timeout prevents duplicate processing.
   - Metadata: `SAA | SAA-2.2 | LAMBDA-SQS, LAMBDA-IDEMP`

7. **Intent — Couple idempotency state and DynamoDB business writes.**
   - Correct principle: when both are in DynamoDB and fit transaction constraints, use `TransactWriteItems` to atomically enforce the idempotency condition and business state change; external side effects still need reconciliation.
   - Three realistic distractors: use a transaction to atomically commit a third-party payment; put the two writes in separate async Lambdas; rely on DynamoDB Streams to prevent the initial duplicate.
   - Metadata: `SAP | SAP-2.4 | DDB-TXN, DDB-COND`

8. **Intent — Set idempotency-record expiry safely.**
   - Correct principle: retain records for at least the maximum legitimate retry/replay horizon; DynamoDB TTL cleanup is asynchronous, so application logic must evaluate expiry rather than rely on exact deletion time.
   - Three realistic distractors: set TTL equal to one network timeout; use TTL as an exact scheduler; never expire records regardless of privacy/cost requirements.
   - Metadata: `SAP | SAP-2.6 | LAMBDA-IDEMP, DDB-COND`

9. **Intent — Diagnose duplicate charges despite a FIFO queue.**
   - Correct principle: trace producer dedup IDs, redelivery/visibility, consumer retries, idempotency-key reuse, and the side-effect commit boundary; FIFO queue delivery features do not guarantee exactly-once external effects.
   - Three realistic distractors: increase FIFO throughput mode; increase message retention; switch to a Standard queue to expose duplicates faster.
   - Metadata: `SAP | SAP-3.4 | SQS-FIFO, LAMBDA-IDEMP`

10. **Intent — Review a concrete idempotency state machine.**
    - Correct principle: require stable key plus payload hash, conditional `IN_PROGRESS` claim, bounded lease, atomic/ordered side effect, `COMPLETED` result storage, replay behavior, expiry, and duplicate metrics.
    - Three realistic distractors: a cache-only `SET` with no durability requirement analysis; a record written only after success; a unique key generated by the server for each received attempt.
    - Metadata: `SAA → SAP | SAA-2.2 / SAP-3.4 | LAMBDA-IDEMP, DDB-COND, DDB-TXN`

---

## Chapter 58 — Saga, Transactional Outbox, and Eventual Consistency

### Existing defects

- The chapter combines three related but distinct concerns, yet every current question defaults to Step Functions as though it alone solved the database/message dual-write problem.
- Question 2 tests generic Step Functions settings instead of outbox table schema, atomic write, publication checkpoint, duplicate publication, or retention.
- Question 3 describes orchestration mechanics but does not validate the transactional outbox invariant.
- The current “correct” answer combines outbox and saga in one sentence, so the learner can pass without distinguishing event-publication reliability from multi-service compensation.
- Missing coverage: orchestration versus choreography, semantic compensation, irreversible steps, duplicate events, event ordering/versioning, DynamoDB Streams/CDC, stuck-saga diagnosis, reconciliation, and migration strategy.

### Ten replacement intents

1. **Intent — Identify and eliminate the database/message dual-write gap.**
   - Correct principle: write business state and an outbox record in the same local transaction, then publish asynchronously; publication can be at least once, so consumers and the publisher need idempotent handling.
   - Three realistic distractors: commit the database then publish directly and retry best-effort; publish first then update the database; use a distributed lock around two unrelated managed services.
   - Metadata: `SAP | SAP-2.4 | PG-OUTBOX`

2. **Intent — Design a usable outbox record.**
   - Correct principle: include immutable event ID, aggregate/business key, event type/version, payload/reference, creation time, publication status/checkpoint, and ordering data where required.
   - Three realistic distractors: store only free-form payload text; use publication timestamp as the sole identity; overwrite one row per aggregate and lose intermediate transitions.
   - Metadata: `SAP | SAP-2.4 | PG-OUTBOX`

3. **Intent — Publish an outbox through DynamoDB Streams or CDC.**
   - Correct principle: atomically update the aggregate and outbox/item, consume the change stream, publish with stable event identity, and tolerate duplicate stream/event delivery.
   - Three realistic distractors: let the Lambda query the table periodically with an eventually consistent full scan only; delete outbox data before target acknowledgement; assume Streams provides exactly-once downstream effects.
   - Metadata: `SAA → SAP | SAA-2.1 / SAP-2.4 | PG-OUTBOX, DDB-TXN`

4. **Intent — Choose saga orchestration versus choreography.**
   - Correct principle: orchestration centralizes sequence, timeout, compensation, and visibility; choreography reduces central coordination but requires strict event contracts and can become difficult to trace as participants grow.
   - Three realistic distractors: claim choreography has no coupling; claim orchestration creates one ACID transaction; use SNS fan-out as an automatic compensation engine.
   - Metadata: `SAP | SAP-4.4 | PG-SAGA, SF-INTEGRATION`

5. **Intent — Define a semantic compensation for a committed step.**
   - Correct principle: compensation is a new idempotent business action such as refunding or releasing inventory, not a technical rollback; it needs its own failure/retry/escalation policy.
   - Three realistic distractors: restore every database from backup; delete audit records to imitate rollback; reverse an irreversible shipment without a manual exception path.
   - Metadata: `SAA → SAP | SAA-2.2 / SAP-2.4 | PG-SAGA`

6. **Intent — Order irreversible or hard-to-compensate actions.**
   - Correct principle: perform reversible/reservable steps first, place irreversible steps late, use reservation/expiry where possible, and define manual reconciliation for non-compensable outcomes.
   - Three realistic distractors: ship before payment authorization; retry irreversible actions without identity; hold cross-service locks until a human responds.
   - Metadata: `SAP | SAP-2.4 | PG-SAGA`

7. **Intent — Preserve aggregate event order during duplicate publication.**
   - Correct principle: use aggregate sequence/version, stable event IDs, conditional state transitions, and consumers that reject/hold stale or out-of-order versions according to the domain contract.
   - Three realistic distractors: rely on EventBridge global ordering; use wall-clock timestamps from different hosts as perfect order; deduplicate solely by event type.
   - Metadata: `SAP | SAP-3.4 | PG-OUTBOX, SQS-FIFO`

8. **Intent — Diagnose a saga stuck after payment.**
   - Correct principle: correlate saga/aggregate ID across execution history, outbox backlog, event delivery, participant state, retries, and compensation state; reconcile authoritative business records before blind redrive.
   - Three realistic distractors: restart every service; replay the entire event archive with no idempotency; mark the saga successful because the orchestrator is running.
   - Metadata: `SAP | SAP-3.1 | PG-SAGA, PG-OUTBOX, SF-LOG`

9. **Intent — Define convergence and user-visible eventual consistency.**
   - Correct principle: expose pending/confirmed/failed states, set a convergence SLO, offer status polling/callback, and run reconciliation; do not present provisional multi-service work as final.
   - Three realistic distractors: hide all intermediate states and return success immediately; force every read through one global lock; promise zero inconsistency while using asynchronous participants.
   - Metadata: `SAA | SAA-2.2 | PG-SAGA`

10. **Intent — Migrate synchronous order processing to saga/outbox safely.**
    - Correct principle: introduce stable operation/event identities, dual-run or shadow selected events, version contracts, canary participants, measure lag/duplicates/compensations, and retain a reversible cutover path.
    - Three realistic distractors: switch all producers and consumers simultaneously; publish database rows without a schema contract; delete the old reconciliation path on first successful test.
    - Metadata: `SAP | SAP-4.3 | EX-SAP4, PG-SAGA, PG-OUTBOX`

---

## Chapter 59 — Circuit Breaker, Bulkhead, and Backpressure

### Existing defects

- Questions 2–4 incorrectly make Elastic Load Balancing the primary mechanism. ELB listener/target-group settings do not implement application circuit breaking, bulkheads, or bounded backpressure.
- Question 3 tests an ELB request path instead of closed/open/half-open breaker behavior.
- Existing items do not distinguish timeout, retry, circuit breaker, rate limit, concurrency limit, queue, bulkhead, and load shedding.
- Reserved Lambda concurrency and SQS are shown only as generic distractors although both can be concrete bulkhead/backpressure controls.
- Missing coverage: breaker thresholds/window/probes, fallback safety, resource-pool isolation, bounded backlog, queue-age SLO, admission control, overload diagnosis, autoscaling lag, and per-tenant blast radius.

### Ten replacement intents

1. **Intent — Select the right overload/failure control.**
   - Correct principle: timeout bounds waiting, retry handles brief recoverable faults, circuit breaker stops calls to a persistently failing dependency, bulkhead isolates scarce resources, and backpressure/load shedding limits admitted work.
   - Three realistic distractors: use only an ALB health check for a slow optional dependency; retry indefinitely; autoscale the caller while the downstream is hard-failed.
   - Metadata: `SAA | SAA-2.2 | PG-CIRCUIT, WA-RETRY`

2. **Intent — Configure breaker state transitions.**
   - Correct principle: trip from closed to open using an error/slow-call threshold over a meaningful window, wait before limited half-open probes, then close on recovery or reopen on probe failure.
   - Three realistic distractors: open permanently after one error; send full production load in half-open; reset the failure count on every request.
   - Metadata: `SAP | SAP-3.4 | PG-CIRCUIT`

3. **Intent — Choose a business-safe fallback.**
   - Correct principle: degrade optional recommendations to cached/default results, but fail closed or queue/reconcile operations whose correctness cannot be approximated, such as payment authorization.
   - Three realistic distractors: return success without executing payment; use stale authorization decisions indefinitely; fail the entire checkout because recommendations are unavailable.
   - Metadata: `SAA | SAA-2.2 | PG-CIRCUIT`

4. **Intent — Isolate an optional dependency with bulkheads.**
   - Correct principle: assign separate thread/connection/concurrency pools and limits so recommendation saturation cannot consume checkout-critical resources.
   - Three realistic distractors: share one unbounded thread pool for efficiency; use one global circuit breaker for all downstreams; add more ALB targets without isolating client-side resources.
   - Metadata: `SAA | SAA-3.2 | PG-CIRCUIT`

5. **Intent — Use Lambda reserved concurrency as a blast-radius control.**
   - Correct principle: reserve/limit concurrency for functions to protect downstream capacity and ensure critical functions retain capacity; monitor throttles and provide queue/retry/DLQ behavior appropriate to invocation type.
   - Three realistic distractors: set every function’s reserved concurrency to the account maximum; assume reserved concurrency increases downstream database connections safely; discard throttled asynchronous events immediately.
   - Metadata: `SAA | SAA-3.2 | LAMBDA-CONC`

6. **Intent — Bound an asynchronous backlog.**
   - Correct principle: define maximum useful message age/backlog, scale from arrival rate and age, reject or expire work that can no longer meet its deadline, and keep a DLQ/reconciliation path.
   - Three realistic distractors: use infinite retention; monitor only queue depth; process oldest work even after its business deadline while new critical work waits.
   - Metadata: `SAA | SAA-2.1 | SQS-METRIC, SQS-RET`

7. **Intent — Apply backpressure to a synchronous API.**
   - Correct principle: enforce rate/concurrency/admission limits before scarce resources saturate, return an explicit retryable response where appropriate, and coordinate client backoff/jitter.
   - Three realistic distractors: accept every request into an unbounded in-memory queue; increase API timeout; return HTTP 200 before work is admitted.
   - Metadata: `SAP | SAP-2.5 | WA-RETRY, PG-TIMEOUT`

8. **Intent — Diagnose cascading latency with normal CPU.**
   - Correct principle: inspect thread/connection pool saturation, in-flight requests, queue age, downstream latency/errors, retries, breaker state, and rejected work; CPU can remain low while requests wait on I/O.
   - Three realistic distractors: conclude there is no overload because CPU is 30%; scale storage first; increase all timeouts, retaining blocked resources longer.
   - Metadata: `SAP | SAP-3.3 | PG-CIRCUIT, SQS-METRIC`

9. **Intent — Isolate noisy tenants.**
   - Correct principle: apply per-tenant quotas/concurrency/queues or cells so one tenant cannot exhaust shared capacity; retain a global safety limit and fair scheduling.
   - Three realistic distractors: one global FIFO queue with one message group; rely only on average account traffic; give premium tenants unlimited concurrency against the same database pool.
   - Metadata: `SAP | SAP-2.4 | EX-SAP2, LAMBDA-CONC`

10. **Intent — Review a concrete resilient call path.**
    - Correct principle: client deadline → bounded retry with jitter → per-dependency concurrency pool → circuit breaker → timeout → safe fallback, with metrics for attempts, rejections, open duration, saturation, and business success.
    - Three realistic distractors: ELB target health alone; retries outside the deadline with no cap; circuit breaker plus unbounded queue that merely postpones overload.
    - Metadata: `SAA → SAP | SAA-2.2 / SAP-3.4 | PG-CIRCUIT, WA-RETRY, PG-TIMEOUT`

---

## Chapter 60 — Stateless, Stateful, Synchronous, and Asynchronous

### Existing defects

- Questions 2–4 incorrectly reduce this architecture chapter to Amazon SQS configuration and mechanism.
- The current primary scenario mentions a ten-minute report but never tests the complete asynchronous job API: acceptance response, job identity/status, durable result, callback/polling, cancellation, expiry, and idempotency.
- Statelessness is treated as “use SQS,” with no examination of session state, local disk, leader/lease state, caches, databases, or sticky sessions.
- Synchronous versus asynchronous trade-offs are repeated as prose but not tied to consistency, user contract, timeout, backpressure, or failure recovery.
- Missing coverage: state ownership, externalized sessions, queue versus workflow, status/result stores, immediate-consistency boundaries, autoscaling/failover, duplicate job submission, and migration from a stateful monolith.

### Ten replacement intents

1. **Intent — Identify hidden instance-local state that blocks horizontal scaling.**
   - Correct principle: move durable sessions, uploaded artifacts, job status, and coordination state to appropriate shared/durable stores; keep only disposable caches/temp data locally.
   - Three realistic distractors: enable load-balancer stickiness and call the service stateless; copy local disk during every scale-out; store authoritative state only in process memory.
   - Metadata: `SAA | SAA-2.2 | WA-QUEUE`

2. **Intent — Choose synchronous versus asynchronous interaction from the user contract.**
   - Correct principle: use synchronous calls for bounded, immediate results; use asynchronous submission for long/variable work, return an operation ID, and expose eventual completion explicitly.
   - Three realistic distractors: keep an HTTP connection open for a ten-minute report; make every payment eventually consistent; return success before durable job acceptance.
   - Metadata: `SAA | SAA-2.1 | EX-SAA2, WA-ASYNC`

3. **Intent — Design a complete asynchronous report API.**
   - Correct principle: `POST` idempotently creates/accepts a job and returns `202` plus job ID/status URL; a durable store tracks state, workers consume queued work, results go to durable storage, and clients poll or receive a callback/notification.
   - Three realistic distractors: return a worker hostname for later lookup; store status only in SQS; keep the API process alive until the worker finishes.
   - Metadata: `SAA | SAA-2.1 | SQS-VIS, WA-ASYNC`

4. **Intent — Place each category of state with an explicit owner.**
   - Correct principle: transactional truth belongs in a database, large immutable output in object storage, ephemeral session/cache in a cache with a durable fallback as required, workflow progress in a workflow/state store, and messages in a queue—not vice versa.
   - Three realistic distractors: use SQS as the queryable job-status database; use ElastiCache as the only payment ledger; put large report binaries in Step Functions state.
   - Metadata: `SAA | SAA-2.2 | WA-QUEUE, SF-TYPE`

5. **Intent — Avoid confusing sticky sessions with high availability.**
   - Correct principle: stickiness can preserve affinity but leaves session availability and rebalancing concerns; externalized session state allows another healthy instance to serve the next request.
   - Three realistic distractors: claim stickiness replicates memory across AZs; place all sessions on one EC2 instance with an Auto Scaling group; use DNS TTL as session storage.
   - Metadata: `SAA | SAA-2.2 | WA-QUEUE`

6. **Intent — Select SQS versus Step Functions for long-running work.**
   - Correct principle: use SQS when independent workers need buffering/retry/backpressure; use Step Functions when the job has explicit multi-step state, branching, callbacks, timeout, and compensation; combine them when both contracts are needed.
   - Three realistic distractors: use EventBridge archive as a work queue; put orchestration state inside one Lambda loop; use Step Functions solely to increase SQS throughput.
   - Metadata: `SAA | SAA-2.1 | SQS-VIS, SF-INTEGRATION`

7. **Intent — Preserve immediate consistency where the business requires it.**
   - Correct principle: keep authorization, invariant checks, or confirmed inventory reservation on a synchronous/transactional boundary when the caller must know the result; move independent side effects such as email/analytics asynchronously.
   - Three realistic distractors: asynchronously approve payment after telling the buyer it succeeded; synchronously wait for analytics and email before checkout completes; use eventual consistency without exposing pending state.
   - Metadata: `SAP | SAP-2.4 | PG-SAGA, WA-ASYNC`

8. **Intent — Make async submission and processing safe under duplicate delivery.**
   - Correct principle: use a stable idempotency key for job creation, durable job identity/status, idempotent workers, delete/ack only after durable progress, and reconcile uncertain outcomes.
   - Three realistic distractors: create a new job ID for every client retry; rely on visibility timeout as deduplication; mark complete before writing the result object.
   - Metadata: `SAP | SAP-3.4 | LAMBDA-IDEMP, SQS-VIS`

9. **Intent — Diagnose “accepted but never completed.”**
   - Correct principle: trace job ID from API acceptance to queue, worker receive/in-flight state, downstream dependency, result write, status transition, retries/DLQ, and notification; alarm on job age and state-transition latency.
   - Three realistic distractors: check only API 2xx rate; increase client polling frequency; raise retention without finding the blocked stage.
   - Metadata: `SAP | SAP-3.1 | SQS-METRIC, SF-LOG`

10. **Intent — Migrate a sticky-session monolith to a scalable architecture.**
    - Correct principle: inventory state, externalize sessions/files/jobs incrementally, introduce idempotent APIs and async boundaries where latency warrants, canary stateless instances, then remove stickiness after failover tests.
    - Three realistic distractors: disable stickiness before moving session state; rewrite every synchronous path as events in one cutover; share an NFS directory for all state without evaluating locking, throughput, or failure semantics.
    - Metadata: `SAP | SAP-4.3 | EX-SAP4, WA-QUEUE, WA-ASYNC`

---

## Cross-chapter audit conclusion

- The replacement set contains exactly 90 intents: 10 for each of Chapters 52–60.
- The intents are deliberately non-duplicative: queue delivery, pub/sub routing, retained streams, durable workflows, retry control, idempotent effects, distributed transactions, overload containment, and state/interaction placement each have a separate decision boundary.
- Every chapter includes service semantics, concrete configuration, failure diagnosis, and both SAA-level workload selection and SAP-level operating/recovery architecture.
- These are original assessment specifications derived from public AWS documentation and exam-domain objectives. They are not copied exam items, recollections of live questions, or answer dumps.

SUPERSET_WORKER_DONE
{
  "task": "P05-audit",
  "status": "complete",
  "files_created": ["tools/aws_exam_audits/part_05.md"],
  "chapters_audited": [52, 53, 54, 55, 56, 57, 58, 59, 60],
  "intent_count": 90,
  "questions_per_chapter": 10,
  "other_files_modified": false
}
