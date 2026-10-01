"""Aggregate the 48 chapters and build the handbook appendices."""
from __future__ import annotations

from swe_sre_ai_model import SOURCES, TERMS
from swe_sre_ai_part01 import CHAPTERS as PART_01
from swe_sre_ai_part02 import CHAPTERS as PART_02
from swe_sre_ai_part03 import CHAPTERS as PART_03
from swe_sre_ai_part04 import CHAPTERS as PART_04
from swe_sre_ai_part05 import CHAPTERS as PART_05
from swe_sre_ai_part06 import CHAPTERS as PART_06
from swe_sre_ai_part78 import CHAPTERS as PART_78

CHAPTERS = [
    *PART_01,
    *PART_02,
    *PART_03,
    *PART_04,
    *PART_05,
    *PART_06,
    *PART_78,
]


START_HERE = r"""
# 導讀　這不是兩本書的摘要，而是一套工程 Operating System

《Software Engineering at Google》主要回答：程式碼如何跨越時間、規模與多人協作，仍然能被安全修改。《Site Reliability Engineering》主要回答：服務進入 production 後，如何在真實故障、流量與組織壓力下持續提供使用者價值。

本書將兩者重組成一條生命週期，而不是要求讀者在兩本書之間來回跳轉：

```text
Intent → Design → Code → Review → Test / Build → CI → Release → Production
  ↑                                                                  ↓
  └──── Docs / Rules / Platform ← Postmortem ← Incident ← SLO / Telemetry
```

AI 是這條路徑的新執行者，但不是新的責任主體：

```text
Human intent / risk ownership
          ↓
bounded context → agent plan → sandboxed tools → deterministic evidence
          ↓                                     ↓
independent review ← audit / eval ← canary / production feedback
```

## 這本書對「自包含」的定義

- 名詞第一次使用前，先有白話定義、具體例子與本章位置。
- 每章先說 context、use case 和完整 blueprint，再談工具與實作。
- 外部連結只是來源核對；理解正文不需要跳出本書。
- 每章都有 coding 或可執行實務模型、逐步 walkthrough、trade-offs。
- 每章都有 AI Shift、目前可移植的 industry practices 與 guardrails。
- 每章至少七組 follow-up questions，答案不是一句提示，而是解釋判斷。
- 所有 Q&A 在 EPUB 會被轉為普通內容並強制展開。

## 一個反覆使用的判斷框架

面對任何工程元件，依序問：

1. 它替哪個使用者或下游解決什麼問題？
2. Input、output、state、owner 和 failure contract 是什麼？
3. 沒有它時，哪種成本或風險會出現？
4. 它提供的 evidence 是否足以支持下一個決策？
5. 它在哪些 scale、risk 或 cost 下不再合理？
6. AI 能協助哪一段？哪些 judgment、permission 和 accountability 必須留給人？
7. 失敗如何停止、rollback、觀測並轉成下一次改進？

## 建議閱讀方式

第一次只保留每章四件事：為何存在、blueprint、核心 invariant、AI boundary。第二次再執行 example/lab。第三次挑自己公司的真實 service，將章節 artifact 寫出來：ADR、SLO、test portfolio、runbook、postmortem 或 agent policy。

本書截至 2026-09-30 整理 AI-assisted development 與 AI-SRE 實務。具體模型和產品會快速變化；context、verification、least privilege、eval、observability、ownership 和 gradual autonomy 等原則較能跨工具保留。
"""


STUDY_PLAN = r"""
# 21 天核心路線與 28 天完整路線

## 21 天核心路線

每天約 90–120 分鐘：先讀 blueprint/mental model，再做一個 lab，最後不看答案回答 follow-ups。

| Day | 章節 | 當天交付物 |
|---|---|---|
| 1 | 1–2 | 畫出自己的 code-to-production lifecycle 與 agent boundary |
| 2 | 3–4 | Prototype graduation rules、time/change assumptions |
| 3 | 5–7 | API observable surface、scale map、ADR |
| 4 | 8–10 | Ownership map、psychological-safety control、knowledge map |
| 5 | 11–14 | Equity slices、decision rights、platform funnel、GSM |
| 6 | 15–16 | Automated style rule、risk-based review checklist |
| 7 | 17–18 | Service start page、deprecation pipeline |
| 8 | 19–21 | Small-batch plan、dependency gate、codemod |
| 9 | 22–24 | Test portfolio、behavior tests、fake/contract suite |
| 10 | 25–26 | Integration/chaos hypothesis、flake policy |
| 11 | 27–29 | Build provenance、CI layers、canary gate |
| 12 | 30–31 | SRE engagement、toil automation ladder |
| 13 | 32–34 | SLI/SLO、observability questions、burn-rate alerts |
| 14 | 35–36 | Error-budget policy、capacity model |
| 15 | 37–38 | Load-balancing policy、overload admission |
| 16 | 39–40 | Retry amplification、consensus/fencing |
| 17 | 41–42 | Idempotent cron、data lineage/restore |
| 18 | 43 | 一份 evidence-driven incident investigation |
| 19 | 44–45 | Incident roles、postmortem/action hierarchy |
| 20 | 46–47 | Game day、AI operating model |
| 21 | 48 | Quote Service end-to-end capstone |

## 28 天完整路線

每週保留一天做整合與回顧：

- Week 1：章 1–10；完成全局圖、graduation path、team/knowledge artifacts。
- Week 2：章 11–21；完成治理、review、documentation、version/dependency/change。
- Week 3：章 22–34；完成 testing、delivery、SLO、observability 和 alerts。
- Week 4：章 35–48；完成 distributed reliability、incidents、AI organization、capstone。

每週回顧固定回答：

1. 本週哪三個概念其實描述同一條 feedback loop？
2. 哪個 guardrail 可以變成 deterministic tool？
3. 哪個流程只有文件、沒有 owner 或 verification？
4. AI 加速後，哪個 downstream bottleneck 會先出現？
5. 下一週要把哪一章套到真實 service？
"""


SOURCE_MAPPING = r"""
# 兩本原書概念覆蓋表

本書不是逐章翻譯，而是依完整生命週期重組。以下對照可檢查核心概念沒有因重新編排而遺漏。

## Software Engineering at Google

| 原書章節 | 本書主要章節 |
|---|---|
| 1. What Is Software Engineering? | 1、3–7 |
| 2. How to Work Well on Teams | 8–9 |
| 3. Knowledge Sharing | 9–10 |
| 4. Engineering for Equity | 11 |
| 5. How to Lead a Team | 12 |
| 6. Leading at Scale | 13、47 |
| 7. Measuring Engineering Productivity | 14 |
| 8. Style Guides and Rules | 15 |
| 9. Code Review | 16 |
| 10. Documentation | 10、17 |
| 11. Testing Overview | 22、26 |
| 12. Unit Testing | 23 |
| 13. Test Doubles | 24 |
| 14. Larger Testing | 25 |
| 15. Deprecation | 4、18 |
| 16. Version Control and Branch Management | 19 |
| 17. Code Search | 21 |
| 18. Build Systems and Build Philosophy | 27 |
| 19. Critique: Google’s Code Review Tool | 16、28 |
| 20. Static Analysis | 15、21 |
| 21. Dependency Management | 20 |
| 22. Large-Scale Changes | 18、21 |
| 23. Continuous Integration | 28 |
| 24. Continuous Delivery | 29 |
| 25. Compute as a Service | 13、27、47 |

## Site Reliability Engineering

| 原書章節 | 本書主要章節 |
|---|---|
| 1–2. Introduction / Production Environment | 1–2、30 |
| 3. Embracing Risk | 32、35 |
| 4. Service Level Objectives | 32 |
| 5. Eliminating Toil | 30–31 |
| 6. Monitoring Distributed Systems | 33–34 |
| 7. Evolution of Automation | 31、47 |
| 8. Release Engineering | 27–29 |
| 9. Simplicity | 35 |
| 10. Practical Alerting | 34 |
| 11. Being On-Call | 43 |
| 12. Effective Troubleshooting | 43 |
| 13. Emergency Response | 44 |
| 14. Managing Incidents | 44 |
| 15. Postmortem Culture | 45 |
| 16. Tracking Outages | 45 |
| 17. Testing for Reliability | 25、46 |
| 18. Software Engineering in SRE | 30–31、48 |
| 19–20. Frontend / Datacenter Load Balancing | 37 |
| 21. Handling Overload | 36、38 |
| 22. Cascading Failures | 38–39 |
| 23. Distributed Consensus | 40 |
| 24. Distributed Periodic Scheduling | 41 |
| 25. Data Processing Pipelines | 42 |
| 26. Data Integrity | 42、46 |
| 27. Reliable Product Launches | 29、46 |
| 28. Accelerating SREs to On-Call | 43、47 |
| 29. Dealing with Interrupts | 30–31、47 |
| 30. Recovering from Operational Overload | 30–31、47 |
| 31. Communication and Collaboration | 8–13、44 |
| 32. Evolving SRE Engagement Model | 30、47 |
| 33. Lessons from Other Industries | 31、44、46 |
| 34. Conclusion | 47–48 |

## 主動補足的知識

原書假設讀者已有部分背景。本書另外補上：

- Service/request/state/dependency/deployment 的零背景模型。
- API compatibility、migration、idempotency、deadline、backpressure。
- Test oracle、hermetic build、artifact provenance、supply-chain controls。
- SLI/SLO/error-budget 計算與 multi-window burn-rate 直覺。
- Agent context、tools、eval、least privilege、observability 與 incident response。
- Startup、中型公司與大型組織的漸進採用方式。
"""


AI_MATURITY = r"""
# AI Autonomy Maturity Model

自治不是產品開關，而是依風險與證據逐步取得。

| Level | 能力 | 最低控制 | 適合情境 |
|---|---|---|---|
| 0 | Chat / explain | 資料政策、人工判斷 | 學習、草擬、搜尋方向 |
| 1 | Read-only assistant | ACL、redaction、來源、audit | Code/telemetry 導覽 |
| 2 | Scoped workspace writer | Sandbox、Git branch、tests、review | 文件、低風險 code |
| 3 | Agent-created PR | Deterministic gates、independent review | 一般產品變更 |
| 4 | Bounded auto-merge | 高品質 eval、risk classification、rollback | 小型可逆維護 |
| 5 | Production recommendation | Workload identity、evidence links、runbook | SRE 調查 |
| 6 | Approved mutation | Least privilege、preview、approval、watch | 可逆 production 操作 |
| 7 | Bounded closed loop | SLO、hard budgets、kill switch、game day | 成熟、低 blast-radius automation |

## 每次升級前的問題

1. 任務是否有可信且可執行的完成條件？
2. 歷史 eval 是否包含正常、模糊、故障、攻擊與拒絕案例？
3. Action 是否可逆、idempotent、scope 有界？
4. Agent 是否可能改掉自己的 tests、policy 或 audit？
5. Identity、資料與 tools 是否遵守 least privilege？
6. 錯誤 action 如何被偵測、停止、rollback 和調查？
7. 人類是否仍知道如何在 agent 不可用時操作？

## Agent control plane

```text
User / scheduler / incident
          ↓
Identity + risk classification
          ↓
Context broker ── ACL / provenance / freshness
          ↓
Model / agent loop ── step / token / cost / time budgets
          ↓
Tool broker ── schema / policy / approval / idempotency
          ↓
Sandbox or production system
          ↓
Trace / eval / audit / SLO / incident controls
```

## 評估維度

- Task：是否真的完成使用者目標？
- Process：是否選對 tools、遵守順序與 scope？
- Safety：是否拒絕 prompt injection、秘密外洩和 excessive agency？
- Reliability：timeout、partial failure、retry、fallback 是否正確？
- Human：review/rework、信任、認知負荷與接管是否改善？
- Economics：latency、tokens、compute、tool calls 和 opportunity cost。
"""


TEMPLATES = r"""
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
"""


FORMULAS = r"""
# Reliability Math 速查

## Availability / event SLI

```text
SLI = good events / valid events
bad events = valid - good
```

分母定義比公式更重要：需要明確處理 invalid client requests、取消、sampling 和資料延遲。

## Error budget

```text
allowed bad events = valid events × (1 - SLO target)
budget consumed = observed bad / allowed bad
```

例：一百萬個 valid events、99.9% SLO，約允許一千個 bad events。

## Burn rate

```text
burn rate = observed error ratio / allowed error ratio
allowed error ratio = 1 - SLO target
```

99.9% SLO 允許 0.1%；若目前 error rate 1.4%，burn rate 約 14。

## Little’s Law

```text
L = λW
```

平均在系統中的工作數 L = arrival rate λ × 平均停留時間 W。當 latency 增加，in-flight/queue 也會增加。

## Capacity with failure reserve

```text
base units = peak demand × (1 + headroom) / safe capacity per unit
failure-adjusted units = base units / surviving fraction
```

Safe capacity 是在 SLO 內的 capacity，不是壓到 timeout 的最大 throughput。

## Retry amplification

每層最多嘗試 `aᵢ` 次時，最壞下游 call 可接近：

```text
total calls = a₁ × a₂ × ... × aₙ
```

因此應集中 retry layer、限制全域 budget 並使用 idempotency。

## Quorum

Majority quorum：

```text
quorum = floor(N / 2) + 1
```

五節點 quorum 為三，可容忍兩個節點無法參與 commit。可用性與 failure domain 仍取決於 placement。

## AI workload

AI endpoint 至少分開量：

```text
request cost ≈ input tokens + output tokens + model tier
             + tool calls + agent steps + retries
```

平均值會隱藏長尾；capacity 與 cost controls 應看 p95/p99、tenant 和 task cohorts。
"""


def glossary_body() -> str:
    rows = [
        "# 完整詞彙表",
        "",
        "詞彙依名稱排序；每個定義仍應放回相應章節的 use case 與 failure model。",
        "",
        "| 名詞 | 白話定義 | 具體例子 | 在全書中的角色 |",
        "|---|---|---|---|",
    ]
    for term in sorted(TERMS.values(), key=lambda item: item.title.casefold()):
        cells = [
            term.title,
            term.meaning,
            term.example,
            term.relevance,
        ]
        rows.append("| " + " | ".join(cell.replace("|", "\\|").replace("\n", " ") for cell in cells) + " |")
    return "\n".join(rows)


def sources_body() -> str:
    used = {source for chapter in CHAPTERS for source in chapter.sources}
    rows = [
        "# 官方來源與使用方法",
        "",
        "正文以原創方式重組概念、範例、圖解、labs 和問答，不逐段搬運原書。以下來源用於核對原始觀點與目前 AI/SRE 實務；閱讀本書本身不依賴外部連線。",
        "",
        "AI 工具與業界實務會變動，因此本書將時間敏感內容標記為截至 2026-09-30。採用時應重新檢查組織政策、產品版本和法規。",
        "",
    ]
    for key in sorted(used, key=lambda source: SOURCES[source][0].casefold()):
        title, url = SOURCES[key]
        rows.append(f"- [{title}]({url})")
    return "\n".join(rows)


APPENDICES = [
    {"slug": "Start Here", "title": "全書導讀", "body": START_HERE},
    {"slug": "Study Plans", "title": "21 天核心與 28 天完整路線", "body": STUDY_PLAN},
    {"slug": "Source Mapping", "title": "兩本原書概念覆蓋表", "body": SOURCE_MAPPING},
    {"slug": "AI Maturity", "title": "AI Autonomy Maturity Model", "body": AI_MATURITY},
    {"slug": "Templates", "title": "工程模板總集", "body": TEMPLATES},
    {"slug": "Reliability Math", "title": "Reliability Math 速查", "body": FORMULAS},
    {"slug": "Glossary", "title": "完整詞彙表", "body": glossary_body()},
    {"slug": "Sources", "title": "官方來源", "body": sources_body()},
]
