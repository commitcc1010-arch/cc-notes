# Part 06 Independent Review — Chapters 61–71

- Review date: 2026-10-01
- Bank: `tools/aws_question_banks/part_06.json`
- Scope: Chapters 61–71, 110 original practice questions
- Author recorded by bank: `P06-A`
- Reviewer: independent from the author
- Verdict: revision required before publication

## Review boundary and factual baseline

This review used AWS documentation and the public SAA-C03 and SAP-C02 exam
guides as the factual baseline. Official sample questions were used only to
calibrate question style and depth; none were copied or reconstructed.
Jayendra Patil and other community pages were treated only as topic or
distractor inspiration.

As of 2026-10-01, AWS states that SAP-C03 registration opens on 2026-10-27,
SAP-C02 remains available through 2026-11-17, and SAP-C03 preparation
resources will be published on or after 2026-10-27. Therefore:

- SAP-C02 is the only published Professional blueprint that can currently be
  mapped question by question.
- There is no public official SAP-C03 exam guide or SAP-C03 sample-question
  set available on the review date.
- Current services such as Regional NAT Gateway and Database Savings Plans may
  be included as clearly labelled current-architecture enrichment, but must
  not be presented as confirmed SAP-C03 scored content.

Official timing source:
[AWS Certified Solutions Architect – Professional](https://aws.amazon.com/certification/certified-solutions-architect-professional/).

## Structural and statistical results

The bank has the expected high-level structure:

- 11 chapters and exactly 10 questions per chapter: 110 questions total.
- Each chapter contains intents 1–10.
- 77 single-answer and 33 two-answer questions.
- Single-answer positions are reasonably balanced: A 17, B 19, C 22, D 19.
- All correct-answer positions are also balanced: A 34, B 30, C 30, D 30,
  E 19.
- No exact prompt duplicates or validator-level near-duplicate prompts were
  found.
- No blocked exam-dump source or wording that obviously reconstructs an
  official sample question was found.
- All source URLs returned HTTP 200 after redirects, but several redirects
  reveal inaccurate titles or non-deep links described below.

The current automated bank gate nevertheless fails with 20 problems:

- `aws-otel.github.io` is incorrectly labelled `official`.
- Nineteen question IDs contain at least one explanation below the required
  substantive-explanation threshold.

The answer-position distribution is acceptable and does not require
reshuffling.

## Publication-blocking source and provenance corrections

### 1. `adot-xray` is not an acceptable official-host record

Affected question: `ch067-q09`.

The source is currently:

`https://aws-otel.github.io/docs/getting-started/x-ray`

Even if the project is AWS-maintained, the repository's official-source
contract does not recognize `aws-otel.github.io` as an AWS official host, and
the user explicitly prohibited treating it as official. Make one of these
bounded corrections:

1. Preferably replace it with the official AWS X-Ray migration documentation
   on `docs.aws.amazon.com`, while retaining `cw-otel` and `xray-timeline`; or
2. Relabel it `community` and ensure the question still has a precise official
   AWS source for every factual claim.

The official timeline currently says maintenance mode began on 2026-02-25 and
shows no fixed end-of-support date (`N/A`). Do not add a fabricated 2027
end-of-support deadline:
[X-Ray SDK and daemon support timeline](https://docs.aws.amazon.com/xray/latest/devguide/xray-sdk-daemon-timeline.html).

### 2. `wa-horizontal` redirects to the Reliability Pillar root

Affected question: `ch064-q06`.

The source title claims a horizontal-scaling best practice, but the URL
redirects to the pillar landing page. Replace it with the current exact page:
[REL07-BP03 Obtain resources upon detection that more resources are needed](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_adapt_to_changes_in_demand_dynamically_obtain_resources.html).

### 3. `ec2-network-bw` redirects to a generic instance-types landing page

Affected question: `ch069-q07`.

The record title promises instance network bandwidth limits, but its resolved
URL is only the EC2 instance-types guide root. Replace it with a current exact
network-bandwidth page or the precise instance-family specification pages
used by the scenario. Keep the EBS-optimized source for the separate
instance-side EBS ceiling.

### 4. `jay-nat` points to an image, not the claimed article

Affected inspiration references:

`ch071-q01`, `ch071-q02`, `ch071-q04`, `ch071-q05`, `ch071-q06`,
`ch071-q09`, `ch071-q10`.

The source title claims a NAT Gateway article, but the URL resolves to a PNG.
Replace it with the actual public article URL or remove the inspiration
reference. It cannot serve as article provenance in its current form.

### 5. Broad or mismatched official sources need exact replacements

- `ch062-q06`: `drs-failback` supports failback but not the entire claim about
  protecting VMware/server-hosted workloads through continuous block-level
  replication. Add the exact DRS concepts/requirements source and retain the
  failback page only for failback behavior.
- `ch062-q09`: the scenario is a generic database failback, while
  `drs-failback` is server-workload specific. Remove that source or constrain
  the scenario to a DRS-protected server database. Otherwise cite the actual
  database replication/reconciliation mechanism.
- `ch063-q05`: `backup-restore` is a restore-testing page and does not establish
  backup start-window and cross-account-copy timing. Add exact AWS Backup plan,
  scheduling, and copy documentation.
- `ch064-q08`: `asg-warmup` supports scaling warmup but not the complete
  readiness/target-health claim. Add the exact EC2 Auto Scaling and target
  group health-check documentation.
- `ch064-q09`: the listed sources do not establish all named service metrics
  such as cache hit rate, replica lag, or connection-pool saturation. Add
  precise ElastiCache/RDS/application-pool metric sources, or make the answer
  explicitly a vendor-neutral diagnostic checklist.
- `ch066-q10`: the CloudTrail source is the user-guide home page. Replace it
  with a deep link describing event records or event history.
- `ch067-q08`: `cw-otel` and SQS queue metrics do not precisely document trace
  context propagation or span links across SQS. Add the exact AWS-supported
  OpenTelemetry/SQS propagation source and state whether the implementation
  uses the `AWSTraceHeader` system attribute, message attributes, or OTel span
  links.
- `ch068-q05`: `ec2-ri` describes RI discount application but not Standard
  versus Convertible exchange rules. Add the exact RI offering-class and
  Convertible RI exchange documentation.
- `ch070-q09`: `rds-backup-cost` does not by itself support claims about unused
  read-replica cost, cross-Region transfer, provisioned storage/IOPS, and idle
  development instances. Add exact RDS pricing and replica documentation or
  narrow the answer.
- `ch071-q01`: VPC pricing plus NAT guidance does not fully document Transit
  Gateway and Network Firewall processing charges. Add the exact TGW, Network
  Firewall, and data-transfer pricing sources.
- `ch071-q08`: fault-isolation and VPC-pricing pages do not establish how a
  platform performs locality-aware service routing. Name a concrete supported
  mechanism and cite its official documentation, or recast the answer as an
  application-owned routing design.
- `ch071-q10`: remove the generic CloudTrail source unless the answer explicitly
  uses API-change history; otherwise replace it with the exact CloudTrail event
  lookup source.
- `ch068-q10` and `ch071-q06`: add the AWS certification update page cited
  above. The C02 domain pages alone do not establish the C03 publication date
  or the absence of a C03 guide on 2026-10-01.

## Factual, ambiguity, and mapping corrections by question

### `ch063-q06` — Generic `ReplicaLag` is engine-dependent

The prompt names `ReplicaLag` while leaving the RDS engine unspecified.
Replica-lag metric names and semantics vary by database engine. Specify an
engine for which `ReplicaLag` is the documented metric, or change the wording
to “the engine-appropriate replica-lag metric.” The conceptual answer remains
correct: asynchronous lag is an observation, not a zero-RPO guarantee.

### `ch066-q01` — “Monthly” conflicts with a 28-day rolling interval

The prompt asks for a monthly SLO, while the correct option defines a 28-day
rolling interval. Both are valid CloudWatch SLO designs, but they are not the
same measurement contract. Either:

- change the prompt to request a 28-day rolling SLO; or
- use a calendar-month interval in the answer.

Keep the user-outcome, valid-request population, latency threshold, attainment
goal, and burn-rate action explicit.

### `ch066-q02`, `ch066-q04`, `ch067-q01`, `ch067-q02`, `ch067-q03` — SAA task
mapping is too compute-centric

These questions primarily test metrics, logs, traces, workload visibility, and
diagnosis. SAA-C03 Task 2.2 explicitly includes designing workload
observability and names CloudWatch and X-Ray. SAA-3.2 is about high-performing
and elastic compute and is not the best primary mapping for generic telemetry.

Required mapping corrections:

- `ch066-q02`: `SAA-3.2` → `SAA-2.2`
- `ch066-q04`: `SAA-3.2` → `SAA-2.2`
- `ch067-q01`: `SAA-3.2` → `SAA-2.2`; retain `SAP-3.3`
- `ch067-q02`: `SAA-3.2` → `SAA-2.2`
- `ch067-q03`: `SAA-3.2` → `SAA-2.2`

Official mapping source:
[SAA-C03 Domain 2, Task 2.2](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain2.html).

### `ch067-q09` — Current X-Ray timeline must remain exact

The selected answer is directionally correct, but revise its source metadata
and explanation to say:

- legacy X-Ray SDKs and the daemon entered maintenance mode on 2026-02-25;
- AWS recommends migration to OpenTelemetry;
- the official timeline currently lists end of support as `N/A`.

Do not imply that changing only the exporter is sufficient; instrumentation,
propagation, resource attributes, sampling, and backend compatibility must be
tested.

### `ch068-q09` — Allocation-strategy wording is too vague

“Capacity-aware diversified allocation” is not an exact EC2 Fleet strategy
name and conflates pool selection with diversification. Name the supported
choice and its boundary:

- `price-capacity-optimized` is AWS's general recommendation for most Spot
  workloads; or
- `capacity-optimized` is defensible when interruption cost dominates price.

Then separately state how multiple compatible instance types and AZ pools are
made eligible. Revise the correct choice and explanation so only one exact
strategy follows from the stated priority.

### `ch069-q04` — Compute Optimizer default lookback is factually wrong

The prompt says Compute Optimizer “currently only looks at the last seven
days.” Current AWS documentation says the default analysis lookback is 14
days, and Enhanced Infrastructure Metrics can extend it up to 93 days.

Required correction:

- replace seven days with the 14-day default; and
- retain the need to cover the 30-day seasonal peak, use up-to-93-day enhanced
  metrics where justified, and combine historical data with future business
  events.

Official source:
[What is AWS Compute Optimizer?](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html).

### `ch070-q03` — S3 small-object rule omits the legacy-configuration exception

The correct option says the current default “usually” prevents transition of
objects under 128 KB. Make the version boundary precise:

- lifecycle configurations created from September 2024 onward default to not
  transitioning objects smaller than 128 KB;
- configurations created before September 2024 retain the earlier behavior
  until a lifecycle rule is modified;
- explicit size filters or the lifecycle API header can alter the default.

Without this qualification, an existing-bucket scenario can make the answer
wrong.

Official source:
[S3 Lifecycle transition considerations](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html).

### `ch070-q07` — Sudden 20× DynamoDB demand needs previous-peak/pre-warm
qualification

The answer correctly rejects the claim that on-demand mode can never throttle,
but the prompt specifically says demand may jump 20× suddenly. Revise the
correct option or explanation to include DynamoDB on-demand's previous-peak
scaling boundary: traffic up to twice the previous peak is accommodated
immediately; a larger abrupt jump within roughly 30 minutes can throttle.
Known launches should ramp traffic or pre-warm the table by raising the
previous peak. On-demand remains a reasonable starting mode for unknown
demand, but it is not sufficient by itself for an instantaneous 20× promise.

Official source:
[DynamoDB on-demand capacity mode](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/on-demand-capacity-mode.html).

### `ch071-q08` — The implementation is not self-contained

The correct choice says calls should prefer local targets while retaining
cross-AZ failover, but it never tells the reader who performs that routing.
The answer can vary substantially among an ALB/NLB target group, ECS service
discovery, EKS topology-aware routing, a service mesh, or application-level
discovery.

Name the platform and supported control, state how unhealthy or empty local
zones fall back, and require enough per-zone capacity. Otherwise the answer is
an architectural aspiration rather than a uniquely implementable choice.

## Required explanation expansions

The following options fail the repository's minimum substantive-explanation
gate. Expand each explanation with the violated constraint and the condition
under which the option could become appropriate:

- `ch061-q06`: D
- `ch062-q02`: E
- `ch062-q03`: B
- `ch063-q07`: B
- `ch063-q10`: A
- `ch064-q08`: A
- `ch064-q09`: D
- `ch064-q10`: A
- `ch065-q08`: B
- `ch065-q09`: A and D
- `ch066-q03`: B
- `ch066-q04`: C
- `ch066-q06`: C
- `ch067-q08`: E
- `ch068-q05`: B
- `ch069-q06`: C
- `ch069-q08`: A and D
- `ch071-q01`: C
- `ch071-q03`: B

This is not merely a character-count issue. For example, `ch068-q05` option B
should explain that Standard RIs can be modified in limited documented ways
but cannot be exchanged like Convertible RIs, rather than only saying they
cannot move to arbitrary AWS services.

## Distractor-quality corrections

Several distractors are so implausible that a candidate can answer without
understanding AWS. Replace them with realistic near-misses:

- `ch061-q06` D: replace tag color with a plausible but insufficient
  cross-Region dependency design.
- `ch063-q03` C and E: replace purchasing discounts and printer supplies with
  realistic RTO mistakes, such as excluding DNS convergence or blindly adding
  parallel durations.
- `ch063-q07` C: replace “ALB timeout makes the database appear” with a
  plausible readiness/health-check sequencing mistake.
- `ch064-q05` C: SQS retention cannot be infinite. Use the 14-day maximum or
  another plausible “store backlog instead of increasing processing
  capacity” misconception.
- `ch065-q02` C: replace the impossible 101% threshold with a realistic 100%
  threshold that leaves no lead time.
- `ch065-q09` A, B, and D: replace tag, DNS-name, and global-name distractions
  with plausible quota-scope, IaC dry-run, or control-plane-versus-data-plane
  mistakes.
- `ch067-q06` B: replace destructive table deletion with a plausible but
  premature DynamoDB capacity increase made without checking retries or
  caller-side waiting.
- `ch068-q04` C: replace the Reserved DB Instance/EC2 mismatch with a realistic
  Regional RI versus Zonal RI or Capacity Reservation confusion.
- `ch071-q04` D: replace “renaming a subnet makes it public” with the common
  mistake of adding an IGW route while omitting public addressing.

All revised distractors still need complete per-option explanations.

## Cross-question overlap and coverage

No exact duplicate was found, but these semantic clusters should be tightened:

- `ch062-q10`, `ch063-q08`, `ch063-q09`, and `ch063-q10` all test that resource
  or assessment success does not prove recovery. Preserve the distinct focus
  of backup completion, assessment posture, transaction validation, and RTO
  clock in both prompts and explanations.
- `ch064-q09`, `ch067-q01`, `ch067-q06`, and `ch067-q07` repeatedly use p99 plus
  traces to find a bottleneck. Make `ch064-q09` primarily a multi-signal
  constrained-stage question, leaving trace mechanics to Chapter 67.
- `ch069-q09` and `ch070-q10` both use canary/after-state SLO and cost
  validation. Keep the former specific to compute family replacement and the
  latter specific to storage/database usage drivers.

Containers and platform orchestration are not materially tested in this part,
apart from Fargate eligibility under Compute Savings Plans. That is not a
factual defect if the book covers ECS, EKS, and platform scaling in their
dedicated chapters. Do not force generic ECS/EKS distractors into this part.
For `ch071-q08`, however, the locality mechanism must be concrete if a
container platform is named.

## Questions that are substantively acceptable after source/format fixes

The remaining questions have a defensible answer set and current core
behavior. In particular:

- Multi-AZ, RDS Multi-AZ/read-replica, Route 53 failover, ARC, DR strategy,
  backup isolation, and game-day principles are directionally sound.
- Service Quotas Automatic Management is correctly treated as limited to
  supported adjustable quotas and not as guaranteed approval.
- CloudWatch metrics/logs/traces, sparse-metric missing-data behavior,
  composite alarms, EMF cardinality, CloudTrail, and AWS Config have the right
  responsibility boundaries, subject to the task/source corrections above.
- Savings Plans do not reserve EC2 capacity; Zonal RIs and On-Demand Capacity
  Reservations are correctly separated from pure billing commitments.
- Regional NAT Gateway and Database Savings Plans are current services on the
  review date and are properly framed as current extensions rather than
  confirmed SAP-C02/C03 scored items, once the certification-timing source is
  added.
- The core answers for S3 gateway endpoints, public/private NAT Gateway,
  CloudFront caching, gp3, Athena columnar layouts, and DynamoDB partition-key
  design are correct.

## Required re-review

After a separate revision agent changes the bank:

1. Run `python3 tools/check_aws_question_banks.py --part 6`.
2. Recheck every ID and source listed above against the revised JSON.
3. Confirm the `adot-xray` official-host violation is gone.
4. Confirm the Compute Optimizer, S3 Lifecycle, DynamoDB on-demand, X-Ray
   timeline, and SAP-C03 date boundaries remain exact.
5. Re-run answer-distribution and duplicate checks.

REVISE

## Verification

- Verification date: 2026-10-01
- Scope: re-review of the revised `part_06.json` against every required
  correction above
- Bank modifications by verifier: none

### Checks that now pass

- `python3 tools/check_aws_question_banks.py --part 6` passes: 110 questions
  across 11 chapters.
- All option explanations now satisfy the structural length gate.
- Question count, single/multi schema, intents, IDs, and answer indexes remain
  valid.
- Answer placement remains balanced: single answers A 17, B 19, C 22, D 19;
  all answer positions A 34, B 30, C 30, D 30, E 19.
- No exact or high-similarity duplicate prompts were found. The previously
  identified recovery-proof, tracing, and cost-validation clusters now retain
  distinct mechanisms and decision targets.
- The `adot-xray` record and all `aws-otel.github.io` official provenance have
  been removed. `ch067-q09` now uses official AWS X-Ray timeline and
  OpenTelemetry migration deep links.
- The invalid `jay-nat` image provenance has been removed from the affected
  Chapter 71 questions.
- All official source records use accepted AWS hosts. Every source URL was
  reachable during verification; one AWS Backup request was transiently reset
  and returned HTTP 200 on retry.
- The previously broad or mismatched sources were replaced or supplemented:
  DRS concepts, AWS Backup scheduling/cross-account copy, Auto Scaling and ELB
  health, ElastiCache/RDS metrics, CloudTrail events, SQS trace propagation,
  RI modification/exchange, EC2 network bandwidth, RDS/TGW/Network Firewall
  pricing, and EKS locality guidance now have precise deep links.
- The observability questions now map to `SAA-2.2` instead of incorrectly
  treating generic metrics/tracing as elastic-compute task `SAA-3.2`.
- `ch063-q06` now specifies RDS MySQL before using `ReplicaLag`.
- `ch066-q01` now explicitly asks for a 28-day rolling SLO.
- `ch067-q08` now identifies the SQS `AWSTraceHeader` system attribute and
  distinguishes Lambda automatic propagation from manually instrumented
  consumers.
- `ch068-q09` now names `capacity-optimized` and separates strategy selection
  from making multiple instance-type/AZ pools eligible.
- `ch069-q04` correctly uses the 14-day Compute Optimizer default and up-to-93
  day Enhanced Infrastructure Metrics period.
- `ch070-q03` correctly includes the September 2024 S3 Lifecycle compatibility
  boundary for pre-existing configurations and the explicit override
  mechanisms.
- `ch070-q07` now explains DynamoDB on-demand's previous-peak boundary and the
  need to ramp or pre-warm before a known abrupt 20× launch.
- `ch071-q08` now names EKS with Istio locality load balancing, retains
  cross-zone failover, and cites the exact EKS networking-cost guidance.
- The SAP-C03 timing is correctly written as future state: on 2026-10-01,
  registration has not opened; 2026-10-27 and 2026-11-17 are future dates.
  The revised questions do not present a SAP-C03 guide or sample-question set
  as already available.
- The implausible distractors identified in the original review were replaced
  with realistic near-misses. The one exception is the new ambiguity described
  below.

### Remaining required corrections

1. **`ch065-q09` is not uniquely answerable.**

   Options A, B, and D all describe real, material gaps in the stated recovery
   validation:

   - A correctly says quota scope and the recovery Region's applied value were
     not checked.
   - B correctly says a change set or small resource creation does not validate
     production-scale quotas, capacity, or load.
   - D correctly distinguishes control-plane template acceptance from
     production data-plane limits.

   Option C is merely a longer superset of those valid observations. Asking
   which gap is “largest” makes the result depend on wording length rather than
   a unique AWS mechanism, and B and D are especially close to duplicates.
   Rewrite the prompt to request the **most complete next validation action**
   and make A/B/D contain mutually distinct but insufficient approaches, or
   rewrite them so they each violate a concrete requirement. Keep only one
   defensible answer.

2. **`ch068-q05` still overstates current Standard RI modification scope.**

   Option B's explanation says Standard RIs can be modified for “network
   platform.” The current EC2 User Guide lists Availability Zone, scope, and
   instance size within the same family/generation, subject to platform,
   tenancy, and size-flexibility restrictions. It does not list network
   platform as a current general modification choice. Remove “network
   platform” and describe only the currently documented attributes and
   restrictions. This also avoids reviving obsolete EC2-Classic-era wording.

3. **The `xray-timeline` source metadata still implies a known EOS date.**

   The question and its correct explanation are now accurate: maintenance mode
   began on 2026-02-25 and the official end-of-support field is `N/A`.
   However, the source record's `usage` still says “Maintenance mode and
   end-of-support dates for legacy instrumentation.” Change it to
   “Maintenance-mode date and current end-of-support status” so metadata does
   not imply that a future EOS date has been announced.

Because one question remains ambiguous and two factual/provenance descriptions
remain broader than the current official record, Part 06 is not yet ready for
publication.

REVISE

## Final Verification

- Verification date: 2026-10-01
- Scope: third-round read-only verification of the three remaining findings
- Bank modifications by verifier: none

### `ch065-q09` — verified uniquely answerable

The prompt now asks for the **most complete next validation action** before
signing an RTO and 10× disaster-capacity claim.

- A performs quota and capacity inventory but omits production-scale recovery
  deployment and representative load.
- B performs production-scale load testing but carries unverified primary
  Region quota assumptions into the recovery Region.
- C combines recovery-Region quota scope, applied values, increase lead time,
  production-scale deployment, startup timing, downstream headroom, business
  SLOs, and the real RTO clock.
- D excludes startup and failover work by pre-warming before starting the RTO
  clock and does not test post-failure downstream headroom.

Only C satisfies the full stated contract. A, B, and D are now distinct,
plausible but incomplete approaches rather than independently correct answers.

### `ch068-q05` — verified against current Standard RI modification scope

Option B's explanation now limits Standard RI modification to the attributes
documented by the current EC2 User Guide:

- Availability Zone within the same Region;
- Regional versus zonal scope; and
- instance size within the same instance family and generation, subject to
  Linux/UNIX, default-tenancy, footprint, and size-flexibility restrictions.

The obsolete/generalized “network platform” claim has been removed. The
question also correctly distinguishes limited RI modification from exchanging
a Convertible RI for another Convertible RI configuration.

### `xray-timeline` metadata — verified without a future EOS assertion

The source metadata now reads:

`Maintenance-mode date and current end-of-support status.`

This accurately reflects the official status on 2026-10-01: maintenance mode
started on 2026-02-25 and the end-of-support field is `N/A`. It does not claim
that a later EOS date has already been announced.

### Final gate

`python3 tools/check_aws_question_banks.py --part 6` passes with 110 questions
across 11 chapters. All three remaining findings from the second-round
verification are resolved.

VERIFIED
