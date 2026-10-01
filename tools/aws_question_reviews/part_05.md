# Independent Review R05 — Part 05

- Reviewer: `R05`（非作者；題庫作者為 `P05-A`）
- Review date: 2026-10-01
- Scope: `tools/aws_question_banks/part_05.json`
- Chapters: 52–60
- Questions reviewed: 90 / 90
- Governing contract: `tools/aws_question_banks/README.md`
- Intent specification: `tools/aws_exam_audits/part_05.md`

## Review result summary

The bank is structurally complete and substantially better than the legacy
five-question fallback, but it is not yet publishable. The most important
defects are:

1. `ch054-q06` does not have a defensible two-answer set: retrying only failed
   `PutRecords` entries with the same partition key does not preserve strict
   order after a partial success.
2. `ch053-q05` contains an outdated blanket statement about SNS replay. Current
   SNS FIFO topics support message archiving and replay, although they still do
   not provide Kinesis-style continuously managed consumer offsets.
3. `ch058-q01` substantially duplicates `ch089-q06` in another bank.
4. Several SAP task mappings use the wrong official task number.
5. Several questions cite a nearby service overview rather than the official
   document that supports the exact mechanism being tested.
6. Eleven questions have distractors that are too irrelevant or impossible to
   calibrate an exam-ready learner.

## Structural and provenance checks

### Passed

- Exactly 9 chapters and 90 questions.
- Every chapter contains intents `1` through `10` exactly once.
- Every chapter contains 7 single-answer and 3 two-answer questions.
- Single-answer questions have four choices and one answer; multi-answer
  questions have five choices and two answers.
- No duplicate choice exists inside a question.
- Correct-answer positions satisfy the contract: no chapter uses one letter
  position more than four times.
- All 49 declared source URLs returned HTTP 200 after redirects on the review
  date.
- Every question references at least one source labelled `official`.
- Community sources are limited to public Jayendra Patil study articles. No
  ExamTopics, braindump, recalled-live-exam, VCE, or “actual exam questions”
  source is present.
- Exact-search checks on distinctive prompt text found no public copied wording.
- Normalized comparison with the old five-question fallback found no material
  prompt or answer-choice reuse.
- Within Part 05, no repeated prompt was found.

### Failed

- Cross-bank comparison found `ch058-q01` and `ch089-q06` testing the same
  order-commit-then-EventBridge crash scenario with the same transactional
  outbox answer.
- The source table omits the official SAP-C02 Domain 3 page even though 22
  questions carry `SAP-3.x` task keys.
- Several question-level sources do not support the exact claim made in the
  question or explanation. These are listed below.

## Official references used for the current-behavior review

- [SAP-C02 Domain 2](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain2.html)
- [SAP-C02 Domain 3](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain3.html)
- [SAP-C02 Domain 4](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-professional-02/solutions-architect-professional-02-domain4.html)
- [Amazon SNS FIFO topics](https://docs.aws.amazon.com/sns/latest/dg/sns-fifo-topics.html)
- [Amazon EventBridge event patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)
- [Amazon EventBridge retry policy and DLQs](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-retry-policy.html)
- [Kinesis `PutRecords` API](https://docs.aws.amazon.com/kinesis/latest/APIReference/API_PutRecords.html)
- [Handling duplicate Kinesis records](https://docs.aws.amazon.com/streams/latest/dev/kinesis-record-processor-duplicates.html)
- [Step Functions workflow types](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html)
- [Step Functions Map state](https://docs.aws.amazon.com/step-functions/latest/dg/state-map.html)
- [AWS SDK retry behavior](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html)
- [DynamoDB TTL](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)
- [REL05-BP04: Fail fast and limit queues](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_fail_fast.html)

## Status key

- `OK`: answer set, current behavior, scope, distractors, explanation, and
  provenance are acceptable.
- `ANSWER`: answer set is ambiguous or incorrect.
- `CURRENT`: current AWS behavior is omitted or misstated.
- `MAP`: SAA-C03/SAP-C02 task mapping is incorrect.
- `SOURCE`: source coverage is insufficient for the exact tested claim.
- `DUP`: material overlap with another question bank.
- `RIGOR`: distractors are too implausible for the declared exam level.

## All-question disposition

| Chapter | Question-by-question disposition |
|---|---|
| 52 | `q01 OK`; `q02 OK`; `q03 OK`; `q04 OK`; `q05 OK`; `q06 OK`; `q07 OK`; `q08 RIGOR`; `q09 MAP`; `q10 OK` |
| 53 | `q01 OK`; `q02 OK`; `q03 OK`; `q04 OK`; `q05 CURRENT/SOURCE`; `q06 OK`; `q07 MAP`; `q08 SOURCE/RIGOR`; `q09 OK`; `q10 OK` |
| 54 | `q01 OK`; `q02 OK`; `q03 OK`; `q04 OK`; `q05 OK`; `q06 ANSWER/SOURCE`; `q07 RIGOR`; `q08 OK`; `q09 SOURCE`; `q10 OK` |
| 55 | `q01 OK`; `q02 OK`; `q03 OK`; `q04 OK`; `q05 SOURCE`; `q06 MAP`; `q07 OK`; `q08 RIGOR`; `q09 MAP`; `q10 OK` |
| 56 | `q01 OK`; `q02 OK`; `q03 OK`; `q04 OK`; `q05 RIGOR`; `q06 SOURCE`; `q07 OK`; `q08 OK`; `q09 OK`; `q10 RIGOR` |
| 57 | `q01 OK`; `q02 OK`; `q03 OK`; `q04 OK`; `q05 OK`; `q06 OK`; `q07 OK`; `q08 MAP/SOURCE/RIGOR`; `q09 OK`; `q10 OK` |
| 58 | `q01 DUP`; `q02 OK`; `q03 CURRENT/SOURCE`; `q04 OK`; `q05 RIGOR`; `q06 OK`; `q07 CURRENT/SOURCE`; `q08 RIGOR`; `q09 OK`; `q10 CURRENT/MAP` |
| 59 | `q01 SOURCE`; `q02 OK`; `q03 OK`; `q04 SOURCE`; `q05 OK`; `q06 SOURCE`; `q07 SOURCE`; `q08 RIGOR`; `q09 SOURCE`; `q10 SOURCE` |
| 60 | `q01 OK`; `q02 SOURCE`; `q03 SOURCE`; `q04 SOURCE`; `q05 OK`; `q06 OK`; `q07 OK`; `q08 OK`; `q09 RIGOR`; `q10 OK` |

## Required corrections

### 1. Unique answer set and technical correctness

#### `ch054-q06`

The selected answers are B and D. D is correct, but B is not sufficient for the
prompt's strict-order requirement. `PutRecords` can partially succeed and does
not guarantee record ordering. If a later record succeeds while an earlier
record fails, retrying only the failed record can insert it after the later
record even when the partition key is unchanged.

Required action:

- Keep the per-entry failure check, bounded retry, stable partition key, and
  downstream idempotency concepts.
- Either remove “保留同一 account 的順序” from the prompt, or change B to an
  ordering-safe design: serialize writes per ordering key with `PutRecord` and
  `SequenceNumberForOrdering` where applicable, or attach aggregate sequence
  numbers and make the consumer detect/reorder/reject out-of-order events.
- Add the Kinesis `PutRecords` API and ordering documentation to `source_ids`.
- Re-evaluate the two selected answers after rewriting; do not leave B+D as-is.

#### `ch058-q03`

Choice E says to update publication status after “target acknowledgement.” A
successful EventBridge `PutEvents` entry acknowledges ingestion by the event
bus; it does not prove that every downstream rule target completed.

Required action:

- Replace “target acknowledgement” with the exact durable-handoff boundary.
- Require the publisher to inspect `FailedEntryCount` and each `PutEvents`
  result entry, retry only failed entries, and mark the outbox item handed off
  only after successful bus acceptance.
- Keep downstream retries, target DLQs, and consumer idempotency as separate
  responsibilities.
- Add official `PutEvents` API plus DynamoDB Streams/Lambda failure-handling
  sources.

#### `ch058-q10`

“Shadow/dual-run” is unsafe wording for a state-changing saga because naïvely
running old and new paths can charge, reserve, or ship twice.

Required action:

- Specify a non-mutating shadow path, or dual-publish only to disabled,
  compare-only, or demonstrably idempotent consumers.
- State which path owns side effects during each migration phase.
- Preserve canary, observability, reconciliation, and rollback requirements.

### 2. Current AWS behavior

#### `ch053-q05`

The answer Kinesis Data Streams remains defensible because the prompt requires
independent consumer positions and repeated stream processing. However, choice
A's explanation says SNS does not offer long-term replay. Current SNS FIFO
topics support message archiving and replay, so that blanket statement is
outdated.

Required action:

- Rewrite A as a properly configured SNS FIFO archive/replay alternative.
- Explain why it still loses here: it does not provide Kinesis-style
  continuously managed per-consumer offsets and arbitrary stream-processing
  semantics.
- Keep Kinesis as the answer only if the prompt continues to make those offset
  and processing requirements explicit.
- Add the current SNS FIFO message archiving/replay documentation.

#### `ch058-q07`

The selected answer remains correct, because EventBridge does not provide
global ordering. The explanation is nevertheless too broad for current
EventBridge behavior: AWS Custom Event Bus now has FIFO ordering scoped to an
event group and publisher account.

Required action:

- Qualify the false distractor as “global ordering across publishers/groups.”
- Explain that classic rule delivery has no global-order contract and that
  Custom Event Bus FIFO scope still does not replace aggregate sequence
  validation in the consumer.
- Add the current official EventBridge ordering/deduplication source.

### 3. Cross-question duplication

#### `ch058-q01`

This question materially duplicates `ch089-q06`: both use an order database
commit followed by EventBridge publication, crash in the gap, and transactional
outbox as the answer.

Required action:

- Replace `ch058-q01` with a distinct intent-1 outbox scenario, such as a
  publisher crash after successful publish but before marking the outbox row
  sent.
- Test duplicate publication, stable event identity, and consumer idempotency
  rather than repeating the missing-event dual-write gap.
- Keep `intent: 1`, but ensure normalized prompt similarity to `ch089-q06` is
  materially lower.

### 4. SAP-C02 task mapping

Official SAP-C02 Domain 2 defines task 2.3 as security controls and task 2.4 as
reliability; Domain 4 task 4.4 covers application and infrastructure
modernization.

Required mapping changes:

- `ch052-q09`: replace `SAP-2.4` with `SAP-2.3`.
- `ch053-q07`: replace `SAP-2.4` with `SAP-2.3`.
- `ch055-q06`: add `SAP-2.3` as the primary mapping. Retain `SAP-2.4` only if
  the question explicitly keeps approval timeout/recovery as a second tested
  dimension.
- `ch055-q09`: replace `SAP-2.4` with `SAP-2.3`.
- `ch057-q08`: replace `SAP-2.6` with `SAP-3.4`, unless the prompt is rewritten
  to ask an explicit cost-optimization decision.
- `ch058-q10`: replace `SAP-4.3` with `SAP-4.4`.

### 5. Missing or insufficient exact-mechanism sources

The following content is broadly correct, but its current `source_ids` do not
support the exact mechanism asserted. Add the named official material without
removing the existing useful sources.

- `ch053-q08`: EventBridge CloudWatch metrics and Lambda target-permission
  documentation.
- `ch054-q06`: Kinesis `PutRecords` partial-failure and ordering documentation.
- `ch054-q09`: current KCL lease/checkpoint and duplicate-record handling
  documentation.
- `ch055-q05`: Step Functions Inline/Distributed Map documentation.
- `ch056-q06`: an authoritative source for the exact `Retry-After` behavior.
  Under this bank's AWS-only fact-source rule, preferably reframe the scenario
  as an AWS response using the documented retry-after hint instead of an
  unspecified partner API.
- `ch057-q08`: DynamoDB TTL documentation stating that deletion is asynchronous
  and normally occurs within days, not at an exact second.
- `ch058-q03`: EventBridge `PutEvents` per-entry results and DynamoDB
  Streams/Lambda retry/checkpoint documentation.
- `ch058-q07`: current EventBridge ordering/deduplication documentation.
- `ch059-q01`, `ch059-q04`, `ch059-q09`, `ch059-q10`: AWS bulkhead/cell or
  load-shedding guidance supporting isolated bounded resource pools.
- `ch059-q06`, `ch059-q07`: REL05-BP04 or equivalent official fail-fast,
  bounded-queue, throttling, and load-shedding guidance.
- `ch060-q02`, `ch060-q03`: AWS asynchronous request-reply/API integration
  guidance supporting durable acceptance, operation IDs, status endpoints, and
  callbacks.
- `ch060-q04`: Step Functions service quota/payload documentation supporting
  the claim that large report binaries should be referenced rather than passed
  in workflow state.

Part-level provenance action:

- Add `aws-sap-d3` for the official SAP-C02 Domain 3 page.
- Use it to validate the mappings on:
  `ch052-q04`, `ch052-q08`, `ch052-q10`, `ch053-q08`, `ch054-q06`,
  `ch054-q07`, `ch054-q08`, `ch055-q08`, `ch055-q10`, `ch056-q04`,
  `ch056-q08`, `ch056-q09`, `ch057-q04`, `ch057-q09`, `ch057-q10`,
  `ch058-q07`, `ch058-q08`, `ch059-q02`, `ch059-q08`, `ch059-q10`,
  `ch060-q08`, and `ch060-q09`.

### 6. Distractor realism and SAP difficulty

Most explanations identify the violated constraint and are sufficient for a
learning-oriented bank. The following questions, however, make the correct
answer conspicuous because two or more distractors are unrelated, impossible
configurations, or obviously unsafe rather than viable neighboring designs:

- `ch052-q08`
- `ch053-q08`
- `ch054-q07`
- `ch055-q08`
- `ch056-q05`
- `ch056-q10`
- `ch057-q08`
- `ch058-q05`
- `ch058-q08`
- `ch059-q08`
- `ch060-q09`

Required action for each listed ID:

- Preserve its intent and correct principle.
- Replace at least two weak distractors with technically valid neighboring
  designs that fail one named requirement such as ordering, recovery time,
  failure isolation, authorization scope, operational burden, or cost.
- For SAP-labelled questions, add enough constraints that the learner must
  compare two plausible architectures rather than select the only non-absurd
  option.
- Update every replaced option's explanation to state both the violated
  constraint and the scenario in which that option would become appropriate.

## Explanation sufficiency

Except for the current-behavior and realism findings above, the explanations
are internally consistent with their selected answers and identify the
relevant failure boundary. No additional explanation-only defect was found.

## Final verdict

REVISE

1. Fix the answer set and ordering semantics in `ch054-q06`.
2. Update current-service behavior in `ch053-q05`, `ch058-q03`,
   `ch058-q07`, and `ch058-q10`.
3. Replace cross-bank duplicate `ch058-q01`.
4. Correct task mappings on `ch052-q09`, `ch053-q07`, `ch055-q06`,
   `ch055-q09`, `ch057-q08`, and `ch058-q10`.
5. Add exact official provenance for `ch053-q08`, `ch054-q06`,
   `ch054-q09`, `ch055-q05`, `ch056-q06`, `ch057-q08`, `ch058-q03`,
   `ch058-q07`, `ch059-q01`, `ch059-q04`, `ch059-q06`, `ch059-q07`,
   `ch059-q09`, `ch059-q10`, `ch060-q02`, `ch060-q03`, and `ch060-q04`;
   also add the part-level SAP-C02 Domain 3 source.
6. Strengthen distractors on `ch052-q08`, `ch053-q08`, `ch054-q07`,
   `ch055-q08`, `ch056-q05`, `ch056-q10`, `ch057-q08`, `ch058-q05`,
   `ch058-q08`, `ch059-q08`, and `ch060-q09`.

## Verification

- Verification date: 2026-10-01
- Scope: all 90 revised questions in `part_05.json`
- Method: repeated structural checks, answer-set review, official-source URL
  resolution, current AWS behavior verification, and normalized cross-bank
  comparison.
- The question bank JSON was not modified during verification.

### Corrections that now pass

- Structure still passes: 90 questions, intents 1–10 exactly once per chapter,
  7 single-answer plus 3 multi-answer questions per chapter, valid answer
  indices, no within-question duplicate choices, and acceptable answer-position
  distribution.
- `ch054-q06` now has a defensible B+D answer set. B correctly moves strict
  ordering to serialized `PutRecord` calls using the previous successful
  sequence number as `SequenceNumberForOrdering`; C correctly explains why
  retrying failed `PutRecords` entries with the same partition key alone cannot
  restore the original batch order.
- `ch053-q05` now acknowledges that SNS FIFO supports archive retention of up
  to 365 days and subscription replay, while correctly distinguishing that
  feature from Kinesis consumer-managed offsets and stream processing.
- `ch058-q07` now describes current EventBridge semantics accurately: classic
  rule delivery does not provide global ordering, and Custom Event Bus FIFO
  ordering is scoped to the same event group within the same publisher
  account.
- `ch058-q01` no longer repeats the missing-event dual-write scenario from
  `ch089-q06`. It now tests the separate publish-succeeded/local-sent-marker-
  failed duplicate window and requires stable event identity plus consumer
  idempotency.
- `ch058-q03` now separates successful event-bus ingestion from downstream
  target completion and requires inspection of `FailedEntryCount` and
  per-entry `PutEvents` results.
- `ch058-q10` now assigns side-effect ownership to one path at every migration
  phase and restricts shadow/dual-publish consumers to disabled, compare-only,
  or proven-idempotent behavior.
- Step Functions coverage now passes: `ch055-q05` cites the official Map state
  documentation; `ch055-q03` and `ch055-q04` retain correct bounded-retry and
  first-matching `Retry`/`Catch` semantics; callback, timeout, execution-role,
  and logging questions remain defensible.
- The requested task mappings are corrected:
  `ch052-q09 → SAP-2.3`, `ch053-q07 → SAP-2.3`,
  `ch055-q06 → SAP-2.3/SAP-2.4`, `ch055-q09 → SAP-2.3`,
  `ch057-q08 → SAP-3.4`, and `ch058-q10 → SAP-4.4`.
- The SAP-C02 Domain 3 source is present, and the previously listed SAP-3.x
  questions now use it except `ch057-q08`; that question's `SAP-3.4` mapping is
  correct, but adding `aws-sap-d3` to its `source_ids` would make task
  provenance consistent with the rest of the part.
- The eleven distractor sets identified in the original review were rewritten
  into more credible neighboring designs with condition-specific
  explanations.
- All declared source URLs return HTTP 200 after redirects. All newly added
  mechanism sources other than the Billing Conductor item resolve directly to
  the expected official document.

### Remaining required corrections

1. `ch056-q06` — exact source provenance remains incomplete.
   `billingconductor-throttle` points to
   `API_ThrottlingException.html`, but AWS redirects that URL to the Billing
   Conductor API Reference root rather than a page that documents
   `retryAfterSeconds`. The field is visible in legacy AWS Java SDK v1
   generated documentation, but that is not the exact current service API
   source declared by the JSON. Either:
   - replace the source with a current official AWS SDK/service-model page that
     directly documents Billing Conductor `retryAfterSeconds`; or
   - rewrite the scenario to use the currently documented
     `x-amz-retry-after` behavior and cite the current AWS SDK retry guide.

2. `ch059-q04` — cross-bank scenario duplication remains. It substantially
   overlaps `ch065-q06`: both use checkout and personalized recommendations
   sharing concurrency/connection pools, recommendations exhausting the pool,
   and isolated bounded pools as the answer. Rewrite `ch059-q04` with a
   different bulkhead scenario and resource boundary while preserving intent
   4; for example, isolate latency-sensitive authentication from batch-export
   work using separate database or HTTP client pools.

3. `ch057-q08` — add `aws-sap-d3` to `source_ids` so the newly corrected
   `SAP-3.4` mapping has the same direct exam-task provenance as the other
   SAP-3.x questions in this part.

REVISE

## Final Verification

- Verification date: 2026-10-01
- Scope: only the three remaining findings from the preceding verification.
- The question bank JSON was not modified.

1. `ch056-q06` passes. It no longer uses the Billing Conductor claim or source.
   The question now distinguishes standard and adaptive retry modes and tests
   `x-amz-retry-after` using the official AWS SDK for Python v1 retry page. That
   page directly documents that the value is an integer number of milliseconds,
   invalid values are ignored, the standard HTTP `Retry-After` header is
   ignored, and a valid value participates in the documented bounded backoff
   calculation. The declared `sdk-retry-modes` and
   `sdk-python-retry-header` records resolve to the relevant official AWS
   documentation.

2. `ch059-q04` passes. It now uses latency-sensitive authentication and
   deferrable nightly audit exports sharing RDS and HTTP client pools. This is
   materially different from the previously compared `ch065-q06`
   checkout/personalized-recommendations graceful-degradation scenario. The
   shared reusable principle is bulkhead isolation, but the workload,
   operational constraints, resource boundary, and decision requested are no
   longer duplicates.

3. `ch057-q08` passes. Its task mapping remains `SAP-3.4`, and its
   `source_ids` now include `aws-sap-d3` together with the exact DynamoDB TTL
   and idempotency sources.

All three outstanding actions are resolved.

VERIFIED
