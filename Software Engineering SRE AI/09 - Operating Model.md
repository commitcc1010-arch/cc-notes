---
title: "組織落地與 Capstone"
part: 8
as_of: 2026-09-30
---

# Part 8　組織落地與 Capstone

將前面所有概念組成能在 startup、中型公司與大型組織逐步採用的 engineering operating system。

# 第 47 章　AI-ready Engineering Organization 與 SRE Engagement

<p class="chapter-question">如何讓 AI 從個人工具變成可治理、可量測、可擴張的組織能力，而不形成 shadow systems？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 8 · 組織落地與 Capstone</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

建立 policy、data/context、platform、eval、identity、skills、ownership 和自治成熟度模型。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node active"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-46-game-day-disaster-recovery-與-reliable-launch"><span>上一站</span><strong>46. Game Day、Disaster Recovery 與 Reliable Launch</strong></a><div class="position-card current"><span>你在這裡</span><strong>47. AI-ready Engineering Organization 與 SRE Engagement</strong></div><a class="position-card" href="#chapter-48-capstone-從-commit-到可靠服務的完整-operating-system"><span>下一站</span><strong>48. Capstone：從 Commit 到可靠服務的完整 Operating System</strong></a></div>

本章位於 **Part 8：組織落地與 Capstone**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Scale（規模）</h3><div><span>白話定義</span><p>程式碼量、資料量、請求量、團隊數或系統存活時間增加後出現的新約束。</p></div><div class="example"><span>具體例子</span><p>十人可口頭協調；一千人需要可搜尋文件、標準化 review 與自動 policy。</p></div><div class="relevance"><span>本章位置</span><p>Scale 不是單純把數字放大，常會改變最適合的架構與流程。</p></div></section><section class="term-card"><h3>Ownership</h3><div><span>白話定義</span><p>對元件品質、決策、值班與改善負最終責任的明確主體。</p></div><div class="example"><span>具體例子</span><p>平台組維護 deployment API；服務組仍對自己設定錯誤造成的事故負責。</p></div><div class="relevance"><span>本章位置</span><p>AI 可以執行工作但不能承擔組織責任，因此 ownership 不可寫成『模型』。</p></div></section><section class="term-card"><h3>Least privilege</h3><div><span>白話定義</span><p>身份只取得完成當前任務所需的最小權限、範圍和時間。</p></div><div class="example"><span>具體例子</span><p>調查 agent 可讀 logs，但預設不能 restart production。</p></div><div class="relevance"><span>本章位置</span><p>它限制 prompt injection、誤判或帳號外洩造成的 blast radius。</p></div></section><section class="term-card"><h3>Eval（評估）</h3><div><span>白話定義</span><p>以可重複資料和評分規則，量測 AI 系統是否完成目標、遵守限制並安全失敗。</p></div><div class="example"><span>具體例子</span><p>除了答案正確率，也檢查 agent 是否用了禁止的工具、是否引用正確來源。</p></div><div class="relevance"><span>本章位置</span><p>Eval 是 AI 版本的 executable specification；沒有 eval 就無法知道模型或 prompt 更新是否退步。</p></div></section></div>

## 為什麼需要這一章？

零散導入 AI 時，每人使用不同模型、把資料貼到不同服務、重複建立 agents，組織看不見風險也無法共享成果。只發布禁令又沒有安全替代，使用需求會轉入 shadow AI。AI-ready 不是購買 license，而是讓使用者能在低 friction guardrails 內取得可靠 context、tools 和 feedback。

### 真實 Use Case

十個團隊各自做 incident bot，使用個人 token、不同 log 權限和未版本化 prompts。中央平台提供 approved models、workload identity、tool broker、audit、eval harness 和 reusable incident skill；domain teams 維護各自 runbook、SLO 和 action policy。

<div class="context-grid">
<section><span>問題壓力</span><p>零散導入 AI 時，每人使用不同模型、把資料貼到不同服務、重複建立 agents，組織看不見風險也無法共享成果。只發布禁令又沒有安全替代，使用需求會轉入 shadow AI。AI-ready 不是購買 license，而是讓使用者能在低 friction guardrails 內取得可靠 context、tools 和 feedback。</p></section>
<section><span>交付能力</span><p>建立 policy、data/context、platform、eval、identity、skills、ownership 和自治成熟度模型。</p></section>
<section><span>真實場景</span><p>十個團隊各自做 incident bot，使用個人 token、不同 log 權限和未版本化 prompts。中央平台提供 approved models、workload identity、tool broker、audit、eval harness 和 reusable incident skill；domain teams 維護各自 runbook、SLO 和 action policy。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>AI policy / risk tiers / approved use
        ↓
identity + data classification + model gateway
        ↓
context layer: canonical docs / code / telemetry / ACL
        ↓
tool platform: schemas / sandbox / approvals / audit / budgets
        ↓
skills / workflows owned by domain teams
        ↓
eval + observability + incidents + user feedback
        ↓
autonomy maturity and portfolio investment

central platform controls mechanisms
local owners control domain intent and risk</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

組織層先定義允許、需審查和禁止 use cases，依資料、side effect 和影響分 risk tiers。政策要清楚回答資料能否送入模型、輸出如何 review、哪些 actions 需批准、retention 和 incident reporting。提供 approved paved road，否則規則難以執行。

平台層提供 model gateway、identity、ACL-aware context、sandbox、tool schemas、budgets、audit、eval 和 observability。Domain teams 擁有 prompt/skill、knowledge sources、acceptance criteria 和 on-call。中央不應成為所有 workflow bottleneck，local 也不能自行繞過共用 security controls。

成熟度可從 assistive chat、scoped agent、agent-created PR、bounded merge、read-only SRE、approved mutation 到低風險 closed loop。每級以風險、eval、歷史 precision、reversibility 和 incident record取得，而非 vendor feature。Portfolio metrics 看 user value、flow、quality、security、cost 和 human experience。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>建立 risk-tiered AI policy、資料分級、approved models 和透明使用規則。</p></div><div class="flow-card"><span>2</span><p>提供 model/context/tool 平台：identity、ACL、sandbox、budget、audit、eval。</p></div><div class="flow-card"><span>3</span><p>中央維護控制機制，domain owners 維護 workflow、knowledge、SLO 和 action policy。</p></div><div class="flow-card"><span>4</span><p>以成熟度梯逐步授權，每級有 entry/exit evidence 和 kill switch。</p></div><div class="flow-card"><span>5</span><p>量 outcome、rework、stability、security、cost、equity 和 developer experience。</p></div></div>

## Coding／實務例子

範例用 risk tier 決定最低 control。規則應在 tool gateway 執行，而非只放在政策文件。

```python
CONTROLS = {
    "assist": {"human_review"},
    "code-write": {"sandbox", "tests", "independent_review", "audit"},
    "prod-read": {"workload_identity", "acl", "audit", "redaction"},
    "prod-write": {
        "workload_identity", "least_privilege", "approval",
        "idempotency", "rollback", "audit", "kill_switch",
    },
}

def required_controls(use_case: str) -> set[str]:
    if use_case not in CONTROLS:
        raise ValueError("unclassified AI use case")
    return CONTROLS[use_case]
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Unknown use case fail closed，先分類而不是默認最低控制。</p></div><div class="flow-card"><span>2</span><p>Production read 仍需 ACL/redaction，唯讀不代表無資料風險。</p></div><div class="flow-card"><span>3</span><p>Production write 加入 approval、idempotency、rollback 和 kill switch。</p></div><div class="flow-card"><span>4</span><p>真實 controls 還依資料敏感度、impact、reversibility 和 jurisdiction 調整。</p></div></div>

## Trade-offs 與 Failure Modes

- 中央平台沒有 user research，approved path 太難用而促成 shadow AI。
- 每個 team 自建 tool auth/audit，產生不一致和重複安全漏洞。
- 只量 license adoption/accepted lines，忽略 rework、incidents 和成本。
- Autonomy 因 vendor demo 直接升級，沒有 representative eval 和 rollback。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

業界 AI 工程的共同方向是把 AI 當 sociotechnical change：明確政策、健康可存取資料、成熟 version control、小批次、使用者導向和內部平台缺一不可。Coding/SRE agent 需要 context engineering、deterministic verification、least privilege、eval 和 observability。最重要的管理實務是將 AI 產出責任留給現有 owners，而非建立無人負責的模型層。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>用 AI 分析重複 workflows，找 reusable skills/tools 而非只建聊天介面。</li><li>讓 platform 提供 eval templates、safe sandboxes 和 model routing，自助落地。</li><li>建立 AI champions/community 分享 cases、failures、security 和 domain patterns。</li><li>用 agent 生成 adoption support 與 docs，但由政策/安全 owners 核准。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>所有 agents 有 service catalog entry、owner、risk tier、data sources、tools 和 on-call。</li><li>Tool gateway 統一 identity、ACL、approval、budgets、audit 和 emergency revoke。</li><li>Eval/observability 與模型版本綁定，重大更新走 shadow/canary。</li><li>人事、高影響決策、不可逆 production/data action 保留人類 authority。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

組織不需要一次到達全自治。專家會先選有清楚 oracle、低 blast radius、高重複成本的 use case建立信任，再擴張。若基本 version control、tests、docs 和 SLO 不成熟，AI 會放大缺陷；因此 AI roadmap 其實也是改善工程基礎的 roadmap。

</aside>

## 動手驗證

1. 盤點所有 AI use cases：owner、data、model、tools、risk、eval、incident path。
2. 執行 control mapping，新增 high-impact decision 和 public-content 類別。
3. 畫中央平台/local domain responsibility，找 ownership gap 和 bottleneck。
4. 制定六個月成熟度路線，每級含 use cases、controls、metrics 和退出條件。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. AI-ready organization 不等於什麼？</summary>

不等於全員購買 chatbot 或追 adoption；它需要 policy、data/context、platform、skills、eval、ownership 和安全 feedback。

</details>

<details class="qa"><summary>Q2. 為何純禁令容易失敗？</summary>

真實工作需求仍存在，成員會使用不可見工具；需提供低 friction、功能足夠的 approved paved road。

</details>

<details class="qa"><summary>Q3. 中央平台與 domain team 如何分工？</summary>

中央做 identity/model/tool/eval/audit 機制；domain 定義 intent、knowledge、SLO、風險與 action policy。

</details>

<details class="qa"><summary>Q4. Autonomy maturity 應依什麼升級？</summary>

Representative eval、歷史 precision、可逆性、blast radius、controls、incident record 和 human trust，而非功能可用。

</details>

<details class="qa"><summary>Q5. 唯讀 agent 為何仍有風險？</summary>

可洩漏敏感資料、跨 tenant 存取、產生誤導建議或高成本查詢，需要 ACL、redaction、audit 和 quota。

</details>

<details class="qa"><summary>Q6. AI portfolio 應量哪些 outcome？</summary>

User/business value、flow、rework/quality、stability/security、cost、equity 和 human experience，不只採用。

</details>

<details class="qa"><summary>Q7. 何時不應優先建 agent？</summary>

Problem deterministic 可用普通 automation、沒有可信 context/oracle、流程本身應刪除，或 blast radius 無法控制時。

</details>

## 本章官方來源與延伸閱讀

- [DORA 2025 — AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)
- [Google Cloud — How Google SRE is using agentic AI](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)
- [Site Reliability Engineering — Evolving the SRE Engagement Model](https://sre.google/sre-book/evolving-sre-engagement-model/)

---

# 第 48 章　Capstone：從 Commit 到可靠服務的完整 Operating System

<p class="chapter-question">如何把前 47 章組成一條可執行路徑，設計、發布並營運一個含 AI 助手的服務？</p>

<div class="chapter-meta"><span>難度：綜合實戰</span><span>Part 8 · 組織落地與 Capstone</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

完成一個 end-to-end blueprint：需求、contract、code、tests、CI/CD、SLO、incident、postmortem 與 earned autonomy。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node active"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-47-ai-ready-engineering-organization-與-sre-engagement"><span>上一站</span><strong>47. AI-ready Engineering Organization 與 SRE Engagement</strong></a><div class="position-card current"><span>你在這裡</span><strong>48. Capstone：從 Commit 到可靠服務的完整 Operating System</strong></div><div class="position-card muted"><span>下一站</span><strong>完成全書</strong></div></div>

本章位於 **Part 8：組織落地與 Capstone**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Lifecycle（生命週期）</h3><div><span>白話定義</span><p>一項變更從需求、設計、實作、驗證、發布、運行到淘汰的完整時間線。</p></div><div class="example"><span>具體例子</span><p>新增欄位不只改 schema，還要 migration、雙讀寫、監控、清除舊格式。</p></div><div class="relevance"><span>本章位置</span><p>SWE 管理變更的長期成本；SRE 管理變更進入 production 後的風險。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section><section class="term-card"><h3>SLO（Service Level Objective）</h3><div><span>白話定義</span><p>某段時間內希望 SLI 達到的明確目標。</p></div><div class="example"><span>具體例子</span><p>28 天內 99.9% 有效 API request 成功。</p></div><div class="relevance"><span>本章位置</span><p>SLO 讓可靠性、告警和發布決策共享同一尺度。</p></div></section><section class="term-card"><h3>AI Agent</h3><div><span>白話定義</span><p>能接收目標、規劃步驟、呼叫工具、觀察結果並迭代的模型系統。</p></div><div class="example"><span>具體例子</span><p>Coding agent 搜尋 repository、修改檔案、跑測試，再依失敗訊息修正。</p></div><div class="relevance"><span>本章位置</span><p>Agent 增加速度與自治，也帶來 excessive agency、秘密外洩與不可預測操作等新風險。</p></div></section><section class="term-card"><h3>Provenance（來源鏈）</h3><div><span>白話定義</span><p>記錄 artifact、資料或答案由哪些輸入、工具、版本與操作者產生。</p></div><div class="example"><span>具體例子</span><p>Container image 可追到 commit、lockfile、builder identity 和簽章。</p></div><div class="relevance"><span>本章位置</span><p>AI 回答也需保存 retrieval sources、model version 與 tool trace 才能稽核。</p></div></section></div>

## 為什麼需要這一章？

單獨知道 review、SLO、retry 或 agent guardrail 不代表能設計整體系統。真正困難在於它們如何交接：需求如何成為 test oracle，build evidence 如何跟 artifact 進 production，SLO 如何控制 rollout，incident 如何生成下一個 test，AI 如何在相同 ownership 和 control 中工作。

### 真實 Use Case

Capstone 建立 Quote Service：提供商品報價、依賴 Catalog、寫入 quote ledger，另有 coding agent 協助變更與 SRE assistant 調查。需求是 99.9% availability、p99 300ms、報價不可為負、重試不可產生重複 quote，AI 不得直接無批准修改 production。

<div class="context-grid">
<section><span>問題壓力</span><p>單獨知道 review、SLO、retry 或 agent guardrail 不代表能設計整體系統。真正困難在於它們如何交接：需求如何成為 test oracle，build evidence 如何跟 artifact 進 production，SLO 如何控制 rollout，incident 如何生成下一個 test，AI 如何在相同 ownership 和 control 中工作。</p></section>
<section><span>交付能力</span><p>完成一個 end-to-end blueprint：需求、contract、code、tests、CI/CD、SLO、incident、postmortem 與 earned autonomy。</p></section>
<section><span>真實場景</span><p>Capstone 建立 Quote Service：提供商品報價、依賴 Catalog、寫入 quote ledger，另有 coding agent 協助變更與 SRE assistant 調查。需求是 99.9% availability、p99 300ms、報價不可為負、重試不可產生重複 quote，AI 不得直接無批准修改 production。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>USER / PRODUCT
  ↓ requirements + SLO + threat model
DESIGN
  ↓ API/schema + ADR + failure model + ownership
DEVELOP
  ↓ small commits + style + review + tests
BUILD / CI
  ↓ hermetic artifact + provenance + gates
DELIVER
  ↓ canary + SLO burn + rollback + flag cleanup
OPERATE
  ↓ observability + capacity + alerts + on-call
INCIDENT
  ↓ command + mitigation + evidence + communication
LEARN
  ↓ postmortem + test/rule/runbook/platform improvement
  └──────────────────────────────────────────────→ DESIGN

AI layer:
bounded context → sandbox/tools → deterministic evidence
→ independent review → staged autonomy → audit/evals</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

第一階段定義 product contract：valid input、quote semantics、error codes、idempotency、privacy 和 SLI。Design doc 畫 request/dependency/data flow、timeout/retry、overload、migration 和 ownership；ADR 記錄為何選同步 catalog + stale cache fallback。Threat model 包含外部輸入與 agent tools。

第二階段建立 change system：formatter/linter、unit/property/contract/integration tests、hermetic build、dependency lock/provenance、risk-based review 和 CI。Coding agent 只在 worktree 修改，完成條件由 tests/type/static/security 決定。Artifact build once，以 canary 依 error/latency/correctness SLI 漸進。

第三階段營運：dashboard 連 user journey、dependency、queue、version 和 agent trace；burn-rate alert 有 runbook；capacity 保留 zone failure；load shedding 保護 quote API。SRE assistant 預設唯讀，建立 incident brief；rollback 需批准。事故後 postmortem 將漏掉的 failure 變成 test、policy、alert 或簡化設計，閉合 loop。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>定義需求、non-goals、API/invariants、SLI/SLO/error budget 和 owners。</p></div><div class="flow-card"><span>2</span><p>設計 dependencies、state、timeouts/retries、capacity、overload、security 和 migration。</p></div><div class="flow-card"><span>3</span><p>建立 tests/build/CI/review，產出 immutable artifact、SBOM/provenance。</p></div><div class="flow-card"><span>4</span><p>以 canary/SLO/rollback/feature cleanup 發布，保存 change event。</p></div><div class="flow-card"><span>5</span><p>營運 dashboard/alerts/on-call/incident/postmortem，讓教訓返回 code與平台。</p></div><div class="flow-card"><span>6</span><p>AI agent 使用 context、sandbox、tools、eval、least privilege、audit 和成熟度梯。</p></div></div>

## Coding／實務例子

這個最小 service core 展示 contract、idempotency、dependency timeout 和 invariant。完整 companion lab 會將它接到測試、SLO 和 incident simulation。

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Quote:
    quote_id: str
    sku: str
    quantity: int
    total: Decimal

class QuoteService:
    def __init__(self, catalog, ledger):
        self.catalog = catalog
        self.ledger = ledger

    def create(self, request_id: str, sku: str, quantity: int) -> Quote:
        if quantity <= 0:
            raise ValueError("INVALID_QUANTITY")
        if previous := self.ledger.get(request_id):
            return previous
        price = self.catalog.price(sku, timeout_seconds=0.15)
        total = price * quantity
        if total < 0:
            raise RuntimeError("PRICE_INVARIANT")
        quote = Quote(request_id, sku, quantity, total)
        return self.ledger.put_if_absent(request_id, quote)
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Request ID 同時是 quote identity，retry 會讀回或原子建立同一結果。</p></div><div class="flow-card"><span>2</span><p>Catalog call 有明確 timeout，整體 handler 還需端到端 deadline/retry policy。</p></div><div class="flow-card"><span>3</span><p>Total non-negative 是 domain invariant，即使 dependency 回錯也 fail safe。</p></div><div class="flow-card"><span>4</span><p><code>put_if_absent</code> 需要真資料層 unique/transaction contract，unit fake 與 real 共用 tests。</p></div><div class="flow-card"><span>5</span><p>Service 尚未處理 overload、telemetry 和 fallback；它們由外層 operating system補齊。</p></div></div>

## Trade-offs 與 Failure Modes

- 只完成 service code，沒有 deployment、SLO、owner 和 incident path。
- Coding agent 同時改 tests 和實作，將錯誤 behavior 固化成綠燈。
- Canary 只看 process health，錯價 invariant 沒有 user/business signal。
- AI-SRE assistant 取得過大 production 權限，誤判時 blast radius 無界。
- Postmortem actions 沒有 capacity 和驗證，閉環在文件處中斷。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

Capstone 的 AI 不是額外聊天框，而是兩條受控 workflow。Coding agent 讀 canonical design/contract，在 sandbox 實作並交付 evidence；SRE assistant 讀 ACL-filtered telemetry，區分 facts/inferences，提出唯讀驗證與批准後 remediation。兩者共享 identity、tool gateway、eval、audit 和 incident policy，且都不能修改自己的 guardrails。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>Coding agent 先輸出 plan、affected contracts、tests 和 forbidden operations。</li><li>獨立 reviewer agent從 requirement/ADR 檢查 diff，不共享生成過程的假設。</li><li>SRE assistant 建 incident brief、timeline、hypotheses 和 evidence links。</li><li>以 20 個 coding eval、20 個 incident eval、policy injection cases 做 release gate。</li><li>觀測 agent quality、latency、cost、tool success、unsafe action 和 human takeover。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>所有 AI actions 綁定 workload identity、scope、budgets、tool schema 和 audit。</li><li>模型/skill更新走 eval、shadow、canary；不能直接替換 production behavior。</li><li>Agent 無權修改 tests/policy/SLO 以自我通過，高風險操作 separation of duties。</li><li>Deterministic fallback 能在模型/provider outage 時維持核心 quote journey。</li><li>每次事故可立即 revoke identity、停 tools、保存 traces 並切回人工流程。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

完整 engineering operating system 的目的不是堆齊所有流程，而是讓 evidence 以最低摩擦跟著 change 移動。小團隊可以使用較少工具，但 contract、ownership、可逆性和 feedback 不能消失；大型組織需要平台降低重複。AI 是否成熟，最終看它能否在不稀釋這些原則下縮短從 intent 到可信結果的時間。

</aside>

## 動手驗證

1. 寫 Quote Service design brief：goals/non-goals、contract、invariants、dependencies、owners。
2. 實作 fake/real ledger contract tests、catalog timeout、idempotency 和 property tests。
3. 建立 CI/CD blueprint、artifact provenance、canary health 和 error-budget policy。
4. 模擬 catalog latency→retry→overload incident，執行 IC、rollback、postmortem。
5. 設計 coding/SRE agents 的 context、tools、evals、risk tier 和 autonomy ladder。
6. 將 postmortem 的三個 actions 實際轉成 test、alert/policy 和 design simplification。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Capstone 為何從 SLO/contract 開始而非先寫 code？</summary>

它們定義使用者成功、invariants 和可接受風險，後續 tests、alerts、canary 和 agent acceptance 才有共同 oracle。

</details>

<details class="qa"><summary>Q2. Idempotency 應在哪一層保證？</summary>

API 接收 stable request ID，service 重用結果，資料層以 unique/transaction 原子化，外部 side effects也傳同一 key；需端到端。

</details>

<details class="qa"><summary>Q3. Coding agent 和 reviewer agent 為何分離？</summary>

降低共享同一 context/假設造成的盲點；reviewer從 requirement、contract 和風險建立獨立檢查。

</details>

<details class="qa"><summary>Q4. SRE assistant 為何預設唯讀？</summary>

先累積 evidence 和 precision，限制誤判 blast radius；mutation 需成熟 eval、可逆 tools、approval 和 audit。

</details>

<details class="qa"><summary>Q5. Canary 應看哪些 signals？</summary>

User availability/latency/correctness SLI、business invariant、resource/dependency、cohorts 和 version；不只 process up。

</details>

<details class="qa"><summary>Q6. Postmortem 如何真正閉環？</summary>

Action 進 owner/priority，轉成可執行 control，經 test/game day/SLI驗證，並更新設計與平台。

</details>

<details class="qa"><summary>Q7. Startup 是否需要全部機制？</summary>

不需相同工具規模，但需依風險保留核心：owner、contract、tests、可重現 release、基本 telemetry、rollback和事故學習。

</details>

<details class="qa"><summary>Q8. 整本書最重要的一句話？</summary>

讓每次 change 帶著與風險相稱、可追溯的 evidence 前進，並讓 production 的真實結果回到下一次設計。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Preface](https://abseil.io/resources/swe-book/html/pr01.html)
- [Site Reliability Engineering — Introduction](https://sre.google/sre-book/introduction/)
- [DORA 2025 — AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)
- [Google Cloud — How Google SRE is using agentic AI](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)
- [OpenAI — Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)

---
