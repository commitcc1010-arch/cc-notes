# 工程模板總集

# 可直接套用的工程模板

## One-page Design Doc

```text
Title / Owner / Reviewers / Status / Last updated
Problem and users
Goals / Non-goals
Hard constraints and SLO
Current system / proposed blueprint
API, state, ownership and failure contracts
Alternatives and trade-offs
Security / privacy / equity
Capacity / overload / dependencies
Migration / rollout / rollback / cleanup
Observability and validation
Open questions / decision deadline
```

## ADR

```text
Decision:
Context and constraints:
Options considered:
Chosen option and why:
Costs / risks accepted:
Assumptions:
Rollout / rollback:
Signals that invalidate this decision:
Owner / decision date / review date:
```

## Code Review Checklist

```text
Intent and user outcome
Contract / compatibility / data migration
Correctness and invariants
Failure path / timeout / retry / idempotency
Security / privacy / authorization
Tests and independent oracle
Observability / rollout / rollback / cleanup
Ownership and documentation
AI-generated scope, evidence and prohibited shortcuts
```

## SLO Worksheet

```text
User journey:
Valid events / exclusions:
Good events:
Measurement point and data delay:
Window and target:
Dependencies / fallback:
Error-budget policy:
Fast- and slow-burn alerts:
Owner / review cadence:
```

## Incident Update

```text
Severity / IC / Ops / Comms / Scribe
Current user impact:
Known facts and evidence:
Unknowns / conflicting evidence:
Mitigation in progress:
Actions taken and result:
Next decision / next update time:
```

## Postmortem Action

```text
Contributing condition:
Risk to reduce:
Action:
Control type: eliminate / guard / detect / respond / document
Owner / due / priority:
Verification:
Rollback or unintended effects:
Tracking link:
```

## Agent Manifest

```yaml
name: checkout-investigator
owner: payments-sre
risk_tier: prod-read
goal: collect evidence and propose next diagnostic step
context:
  - service-catalog
  - slo-dashboard
  - approved-runbooks
tools:
  allow: [metrics.query, logs.query, traces.get, changes.list]
  deny: [shell.exec, deployment.mutate, database.write]
budgets:
  max_steps: 20
  wall_seconds: 180
  max_cost_usd: 2
requirements:
  cite_evidence: true
  distinguish_fact_inference_unknown: true
  human_approval_for_mutation: true
audit:
  retention_days: 90
```
