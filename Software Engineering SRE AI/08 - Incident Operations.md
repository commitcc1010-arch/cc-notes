---
title: "Incident、On-call 與學習"
part: 7
as_of: 2026-09-30
---

# Part 7　Incident、On-call 與學習

當模型失效時，如何降低傷害、恢復服務、保護人員，並把事故轉成新的工程資產。

# 第 43 章　On-call 與 Evidence-driven Troubleshooting

<p class="chapter-question">Pager 響起後，如何在資訊不足和時間壓力下縮小假設，而不是隨機重啟與同時改很多東西？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 7 · Incident、On-call 與學習</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

建立健康 on-call 系統與科學化調查迴路：observe、localize、hypothesize、test、mitigate、verify。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node active"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-42-data-pipelines-provenance-backup-與-integrity"><span>上一站</span><strong>42. Data Pipelines、Provenance、Backup 與 Integrity</strong></a><div class="position-card current"><span>你在這裡</span><strong>43. On-call 與 Evidence-driven Troubleshooting</strong></div><a class="position-card" href="#chapter-44-emergency-response-與-incident-command"><span>下一站</span><strong>44. Emergency Response 與 Incident Command</strong></a></div>

本章位於 **Part 7：Incident、On-call 與學習**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>On-call</h3><div><span>白話定義</span><p>在指定時段負責接收 production 事件並協調恢復的輪值制度。</p></div><div class="example"><span>具體例子</span><p>Pager 在夜間通知 checkout SLO 快速燃燒，值班者依 runbook rollback。</p></div><div class="relevance"><span>本章位置</span><p>健康 on-call 需要可控事件量、訓練、支援和事故後改善時間。</p></div></section><section class="term-card"><h3>Troubleshooting</h3><div><span>白話定義</span><p>以證據縮小假設空間，找出能解釋症狀並可被反證的原因。</p></div><div class="example"><span>具體例子</span><p>先比較最近變更與健康區域差異，再驗證 database latency 是否共同上升。</p></div><div class="relevance"><span>本章位置</span><p>它不是隨機重啟；AI 產生的假設也必須連回證據。</p></div></section><section class="term-card"><h3>Actionable alert</h3><div><span>白話定義</span><p>代表使用者影響或迫近風險，而且值班者能採取具體行動的通知。</p></div><div class="example"><span>具體例子</span><p>快速消耗 error budget 且 runbook 有 rollback 步驟時 page on-call。</p></div><div class="relevance"><span>本章位置</span><p>每個異常都 page 會造成 alert fatigue，使真正事故被忽略。</p></div></section><section class="term-card"><h3>Observability</h3><div><span>白話定義</span><p>能否從系統輸出推斷內部狀態、因果與失敗位置的能力。</p></div><div class="example"><span>具體例子</span><p>Trace 顯示 request 在付款 dependency 耗掉 1.8 秒，而非只知道整體慢。</p></div><div class="relevance"><span>本章位置</span><p>Logs、metrics、traces、profiles 與變更事件需以共同 identifiers 串接。</p></div></section></div>

## 為什麼需要這一章？

On-call 是 production feedback 的最後人類迴路。事件量過多、alert 無行動、runbook 過時或只有少數 expert 能處理，會造成疲勞並讓恢復依賴英雄。Troubleshooting 在壓力下更容易受 confirmation bias、最近事件和同時操作干擾，因此需要固定方法和角色支援。

### 真實 Use Case

Checkout error 上升。值班者若先重啟所有 pods，可能暫時改變症狀並破壞 evidence；若先確認使用者範圍、最近 changes、healthy/unhealthy 差異與 dependency traces，可發現只有新版本在特定 region 使用錯 config，安全 rollback。

<div class="context-grid">
<section><span>問題壓力</span><p>On-call 是 production feedback 的最後人類迴路。事件量過多、alert 無行動、runbook 過時或只有少數 expert 能處理，會造成疲勞並讓恢復依賴英雄。Troubleshooting 在壓力下更容易受 confirmation bias、最近事件和同時操作干擾，因此需要固定方法和角色支援。</p></section>
<section><span>交付能力</span><p>建立健康 on-call 系統與科學化調查迴路：observe、localize、hypothesize、test、mitigate、verify。</p></section>
<section><span>真實場景</span><p>Checkout error 上升。值班者若先重啟所有 pods，可能暫時改變症狀並破壞 evidence；若先確認使用者範圍、最近 changes、healthy/unhealthy 差異與 dependency traces，可發現只有新版本在特定 region 使用錯 config，安全 rollback。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>actionable page
    ↓ acknowledge / assess severity / protect focus
scope: users, regions, versions, operations
    ↓
timeline + recent changes + dependency health
    ↓
hypotheses ranked by evidence
    ↓
one safe test / comparison at a time
    ↓
mitigate (rollback / shed / failover)
    ↓
verify SLI recovery + watch
    ↓
handoff / incident / follow-up</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

健康 on-call 需要可控事件量、合理輪值、訓練、shadow、backup 和 recovery time。Page 應有 owner、SLO、scope 和 first actions；runbook 讓一般值班者安全處理，不應只寫「找某人」。交班保存目前 impact、已驗證事實、操作、假設和下一步。

Troubleshooting 先分 symptom 與 cause。建立時間線、確認 blast radius、比較健康/不健康 cohort、檢查最近 change，再提出能被反證的假設。一次改一個變數，保存 query 和結果。Mitigation 的目標是使用者恢復，不必等待完整 root cause；rollback、load shed 和 feature disable 常比現場改 code 安全。

認知負荷也要管理。大型事故升級 incident command，小事件限制聊天室人數；固定記錄者避免值班者同時操作和寫報告。恢復後 watch SLI，確認不是短暫波動。Repeated pages 需轉 reliability work，不應把人類睡眠當無限 buffer。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>建立 page quality、輪值、shadow、backup、handoff 和休息標準。</p></div><div class="flow-card"><span>2</span><p>先確認 user impact、scope、timeline、recent changes 和可用 safe actions。</p></div><div class="flow-card"><span>3</span><p>提出可反證 hypotheses，按 evidence/成本排序，一次驗證一項。</p></div><div class="flow-card"><span>4</span><p>優先 mitigation 恢復使用者，所有 mutation 記錄並能 rollback。</p></div><div class="flow-card"><span>5</span><p>以 SLI 驗證恢復與 watch，重複事件建立 owner/action 而非習慣化。</p></div></div>

## Coding／實務例子

範例用 evidence table 排序假設，避免只因『最近常見』就先操作。分數是結構化思考，不是自動 root cause。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Hypothesis:
    name: str
    supporting: int
    conflicting: int
    test_minutes: int
    test_risk: int

def priority(h: Hypothesis) -> float:
    evidence = h.supporting - 2 * h.conflicting
    cost = max(1, h.test_minutes + 3 * h.test_risk)
    return evidence / cost

candidates = [
    Hypothesis("bad rollout", 4, 0, 2, 1),
    Hypothesis("database", 2, 2, 8, 2),
]
print(sorted(candidates, key=priority, reverse=True))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Conflicting evidence 的權重較高，避免 confirmation bias 忽略反例。</p></div><div class="flow-card"><span>2</span><p>先測低風險、快速、資訊量高的假設，不等於它一定是 root cause。</p></div><div class="flow-card"><span>3</span><p>Production mutation 的 test risk 應高於唯讀 query 或 cohort comparison。</p></div><div class="flow-card"><span>4</span><p>每次結果要更新 table，不讓已被反證的假設反覆出現。</p></div></div>

## Trade-offs 與 Failure Modes

- 隨機重啟可能破壞 evidence，且未確認是否真的改善 user SLI。
- 同時修改多項設定，恢復後無法知道哪個 action 有效。
- 只有 primary on-call 懂服務，輪值其他人只是呼叫樹入口。
- 將每次 page 視為個人表現問題，團隊不會投資降低事件量。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI-SRE 很適合在事件初期收集 context、建立 timeline、關聯 recent changes、搜尋相似 incidents 和產生 hypotheses。它也可能把 correlation 寫成 root cause、被過時 runbook 誤導或在壓力下過度操作。最佳實務是 evidence-linked、read-only-first：每個主張附 query/trace/change，模型清楚分 facts、inferences 和 unknowns。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 在 page 時自動準備 SLO、scope、recent changes、top traces 和 owners。</li><li>用 agent 建立 supporting/conflicting evidence table 與下一個唯讀驗證。</li><li>請 AI 搜尋相似 postmortems，但比較差異而非直接套用舊根因。</li><li>讓 agent 產生 handoff/incident timeline，減少值班者文書負荷。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>預設只讀 telemetry；mutation 必須 runbook allowlist、policy 或人類批准。</li><li>AI 輸出明確標 fact/inference/unknown，附原始 evidence 與時間。</li><li>任何 remediation 有 scope、idempotency、rollback、watch 和 audit。</li><li>Agent timeout 或不可用時，原始 alert/runbook 和人類流程仍可運作。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

優秀 troubleshooter 的核心不是記得所有故障，而是快速建立可驗證模型並保護 evidence。AI 可以擴大記憶與搜尋，但 production judgment 仍取決於當前系統、變更與使用者影響。健康 on-call 的終點是事件逐步減少、更多人能安全處理，而非某位英雄恢復得越來越快。

</aside>

## 動手驗證

1. 挑一個歷史 incident，重建 scope、timeline、hypotheses、tests、mitigation。
2. 執行 hypothesis ranking，加入一個高支持但高風險 production test。
3. 檢查十個 pages 是否 actionable、能否由一般 on-call 依 runbook處理。
4. 讓 AI 調查一段合成 telemetry，評分 evidence links、unknowns 和過度推論。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Troubleshooting 第一個技術問題通常是什麼？</summary>

確認使用者 impact 和 scope：哪些 journeys、regions、versions、tenants、時間受影響，先避免在錯誤範圍猜根因。

</details>

<details class="qa"><summary>Q2. Mitigation 與 root cause 有何差別？</summary>

Mitigation 先恢復或限制傷害；root cause 分析解釋事故條件並防止再發。可先 rollback，再慢慢找完整原因。

</details>

<details class="qa"><summary>Q3. 為何一次只改一個變數？</summary>

保留因果辨識；多項同時改變，即使恢復也不知道何者有效，且可能引入新風險。

</details>

<details class="qa"><summary>Q4. 健康 on-call 需要哪些組織條件？</summary>

可控 page 量、actionable alerts、訓練/shadow、backup、runbooks、合理輪值、事故後改善和休息。

</details>

<details class="qa"><summary>Q5. AI incident summary 最大風險？</summary>

把時間相關誤寫成因果、遺漏 conflicting evidence，生成過度完整單一敘事；需附來源與 unknowns。

</details>

<details class="qa"><summary>Q6. Read-only-first 為何重要？</summary>

先建立模型和 evidence，避免 agent 誤判直接改 production；低風險可累積自治 evidence。

</details>

<details class="qa"><summary>Q7. 什麼表示 troubleshooting 系統正在改善？</summary>

MTTD/MTTR、重複 pages、升級到單一 expert 和 unsafe actions 下降，runbook coverage 與一般 on-call 成功率提升。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Being On-Call](https://sre.google/sre-book/being-on-call/)
- [Site Reliability Engineering — Effective Troubleshooting](https://sre.google/sre-book/effective-troubleshooting/)
- [Site Reliability Engineering — Practical Alerting](https://sre.google/sre-book/practical-alerting/)
- [Google Cloud — How Google SRE is using agentic AI](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)

---

# 第 44 章　Emergency Response 與 Incident Command

<p class="chapter-question">事故擴大時，如何避免所有人同時操作、資訊爆炸、決策權模糊和利害關係人失聯？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 7 · Incident、On-call 與學習</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

建立 severity、Incident Commander、Operations、Communication、Planning 與明確交班。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node active"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-43-on-call-與-evidence-driven-troubleshooting"><span>上一站</span><strong>43. On-call 與 Evidence-driven Troubleshooting</strong></a><div class="position-card current"><span>你在這裡</span><strong>44. Emergency Response 與 Incident Command</strong></div><a class="position-card" href="#chapter-45-blameless-postmortem-outage-tracking-與-action-quality"><span>下一站</span><strong>45. Blameless Postmortem、Outage Tracking 與 Action Quality</strong></a></div>

本章位於 **Part 7：Incident、On-call 與學習**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Incident command</h3><div><span>白話定義</span><p>事故中明確分離決策、操作、溝通與記錄角色的協作模型。</p></div><div class="example"><span>具體例子</span><p>Incident Commander 排優先順序；Operations Lead 執行；Comms 更新利害關係人。</p></div><div class="relevance"><span>本章位置</span><p>角色分工降低認知負荷，也避免所有人同時修改 production。</p></div></section><section class="term-card"><h3>Ownership</h3><div><span>白話定義</span><p>對元件品質、決策、值班與改善負最終責任的明確主體。</p></div><div class="example"><span>具體例子</span><p>平台組維護 deployment API；服務組仍對自己設定錯誤造成的事故負責。</p></div><div class="relevance"><span>本章位置</span><p>AI 可以執行工作但不能承擔組織責任，因此 ownership 不可寫成『模型』。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section><section class="term-card"><h3>Least privilege</h3><div><span>白話定義</span><p>身份只取得完成當前任務所需的最小權限、範圍和時間。</p></div><div class="example"><span>具體例子</span><p>調查 agent 可讀 logs，但預設不能 restart production。</p></div><div class="relevance"><span>本章位置</span><p>它限制 prompt injection、誤判或帳號外洩造成的 blast radius。</p></div></section></div>

## 為什麼需要這一章？

大型事故的技術問題常被協作問題放大：多人同時改 production、重要資訊散在私訊、leader 一邊 debug 一邊回管理層、沒人追 action。Incident command 將決策、操作、溝通與記錄分離，讓有限認知資源用在降低使用者傷害。

### 真實 Use Case

全區 checkout outage 時，十位工程師同時進 dashboard、兩人各自 rollback 不同版本、客服沒有 ETA、管理者不斷私訊值班者。宣告 incident、指定 IC/ops/comms/scribe、建立單一 channel 和 action log 後，系統才能有序恢復。

<div class="context-grid">
<section><span>問題壓力</span><p>大型事故的技術問題常被協作問題放大：多人同時改 production、重要資訊散在私訊、leader 一邊 debug 一邊回管理層、沒人追 action。Incident command 將決策、操作、溝通與記錄分離，讓有限認知資源用在降低使用者傷害。</p></section>
<section><span>交付能力</span><p>建立 severity、Incident Commander、Operations、Communication、Planning 與明確交班。</p></section>
<section><span>真實場景</span><p>全區 checkout outage 時，十位工程師同時進 dashboard、兩人各自 rollback 不同版本、客服沒有 ETA、管理者不斷私訊值班者。宣告 incident、指定 IC/ops/comms/scribe、建立單一 channel 和 action log 後，系統才能有序恢復。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>detect / page
   ↓ severity assessment
declare incident + single coordination channel
   ↓
Incident Commander ── priorities / decisions / role assignment
Operations Lead ───── technical actions / verification
Communications ────── users / support / leadership updates
Scribe / Planning ─── timeline / hypotheses / next actions / handoff
   ↓
mitigate → verify → watch → resolve → review</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

先定 severity 和 declaration threshold；寧可早宣告後降級，不要等資訊完整。IC 不必是最懂技術的人，其責任是維持共同目標、分配角色、控制 work in progress、批准高風險 action 和定期重評。Technical experts 放在 operations 才能專心調查。

Communication 是 mitigation 的一部分。使用者需要影響與 workaround，support 需要一致訊息，領導層需要節奏而不是打斷 operator。更新要標記已知、未知、下一次時間，避免猜測 ETA。Action log 記錄誰、何時、做什麼、結果和 rollback。

Emergency access 要預先設計：break-glass 身份、短期權限、雙人核准和完整 audit。事故不是取消控制的理由，而是使用已演練的快速控制。長事故要輪班、交班和休息；疲勞本身會產生第二次事故。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>定義 severity/declaration，建立單一 incident channel、document 和 roles。</p></div><div class="flow-card"><span>2</span><p>IC 管 priorities/decisions；ops 執行；comms 更新；scribe 保存 timeline。</p></div><div class="flow-card"><span>3</span><p>每個 mutation 有 owner、預期、結果、rollback 和同時操作限制。</p></div><div class="flow-card"><span>4</span><p>使用預先演練 break-glass、短期最小權限和 audit。</p></div><div class="flow-card"><span>5</span><p>定期 update/reassess，長事故安排輪班、handoff、watch 和結案條件。</p></div></div>

## Coding／實務例子

範例是 incident action log state machine，防止未指派或未驗證 action 被當成完成。

```python
from dataclasses import dataclass

@dataclass
class Action:
    description: str
    owner: str
    status: str = "proposed"
    result: str = ""

ALLOWED = {
    "proposed": {"approved", "rejected"},
    "approved": {"running", "cancelled"},
    "running": {"verified", "failed", "rolled-back"},
}

def transition(action: Action, new_status: str, result: str = "") -> None:
    if new_status not in ALLOWED.get(action.status, set()):
        raise ValueError(f"invalid transition {action.status}->{new_status}")
    action.status = new_status
    action.result = result
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Action 需要 owner，避免聊天室建議被誤以為有人執行。</p></div><div class="flow-card"><span>2</span><p>Proposed→approved 分離主意與已授權 production action。</p></div><div class="flow-card"><span>3</span><p>Running 不能直接標完成，必須 verified 或記錄 failed/rollback。</p></div><div class="flow-card"><span>4</span><p>真實 log 還要 timestamp、approver、scope、commands、evidence links。</p></div></div>

## Trade-offs 與 Failure Modes

- 最懂技術者同時當 IC/ops/comms，形成認知瓶頸。
- 每個人都能自由 mutation，操作互相覆蓋且無法歸因。
- 過早宣布單一 root cause，團隊忽略矛盾 evidence。
- 狀態更新沒有固定節奏，support/leadership 反覆打斷 operators。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 可以擔任 scribe、timeline builder、translation、status draft 和 evidence retrieval assistant，讓人專注決策；它不適合取代 Incident Commander 或自主接受不可逆風險。AI-specific incidents 還可能包含 prompt injection、model/provider regression、資料洩漏和 tool misuse，需擴充 severity、containment 與 evidence preservation。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 自動整理 action log、決策、evidence 和 unresolved questions。</li><li>用 agent 草擬不同 audience 的 status update，由 comms owner 核准。</li><li>請 AI 搜尋 runbooks/owners/similar incidents，維持單一 incident context。</li><li>讓 AI 對 tool/model actions 建 timeline，支援 AI-specific containment。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>AI 不擔任 IC、不自行宣告 root cause/resolution 或發布外部訊息。</li><li>Production mutation 仍走 identity、approval、bounds、audit 和 rollback。</li><li>Incident prompt/context 視為敏感資料，限制模型、retention 和 access。</li><li>保存 model/instruction/tool trace，containment 後防止 evidence 被覆蓋。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Incident command 的價值在於降低協作熵，而非增加頭銜。小事故可一人兼任，規模擴大就拆角色。AI 最適合接手高頻資訊整理，不能接手價值衝突、風險接受與人員照顧。一次成功恢復也要問是否因英雄運氣，而非可重複系統。

</aside>

## 動手驗證

1. 為一個歷史事故重新分配 IC、ops、comms、scribe，找角色衝突。
2. 執行 action state machine，測未 approved 直接 running 等非法 transition。
3. 寫 status update 模板：impact、known、mitigation、next update、unknown。
4. 設計 AI incident containment：停 model/tool、保留 trace、切 fallback、通知 owners。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. IC 為何不一定是最資深技術者？</summary>

IC 管目標、角色、決策和協作；最深 expert 放 operations 能專注診斷，避免同時承擔溝通與管理。

</details>

<details class="qa"><summary>Q2. 何時應宣告 incident？</summary>

影響跨團隊、severity 不明但可能擴大、需要多角色協作或高風險操作時；可早宣告再降級。

</details>

<details class="qa"><summary>Q3. Action log 最少記什麼？</summary>

時間、description、owner、approver、預期、scope、結果、evidence 和 rollback，讓操作可協調與重建。

</details>

<details class="qa"><summary>Q4. Communication 為何是 mitigation？</summary>

提供 workaround、降低重複請求與支援混亂，保護 operators 不被反覆打斷並維持信任。

</details>

<details class="qa"><summary>Q5. Break-glass 為何仍需 control？</summary>

事故提高 urgency 也提高誤操作風險；使用預先設計的短期權限、雙人核准和 audit，而非共享 root。

</details>

<details class="qa"><summary>Q6. AI 最適合哪個 incident role？</summary>

Scribe/assistant：整理 timeline、查資料、草擬 communication；人類保留 IC、risk 和外部承諾。

</details>

<details class="qa"><summary>Q7. AI-specific incident 要保存哪些 evidence？</summary>

Model/version、prompts/instructions、retrieval、tool calls、identities、policy decisions、outputs 和 affected data。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Emergency Response](https://sre.google/sre-book/emergency-response/)
- [Site Reliability Engineering — Managing Incidents](https://sre.google/sre-book/managing-incidents/)
- [Google Cloud — How Google SRE is using agentic AI](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)
- [Microsoft — Incident response for AI systems](https://learn.microsoft.com/en-us/security/zero-trust/sfi/incident-response-ai-systems)

---

# 第 45 章　Blameless Postmortem、Outage Tracking 與 Action Quality

<p class="chapter-question">事故結束後，如何避免報告變成找戰犯、流水帳，或列出永遠不會完成的 action items？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 7 · Incident、On-call 與學習</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

從 impact、timeline、contributing conditions、decision context 到可驗證改善，建立組織學習迴路。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node active"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-44-emergency-response-與-incident-command"><span>上一站</span><strong>44. Emergency Response 與 Incident Command</strong></a><div class="position-card current"><span>你在這裡</span><strong>45. Blameless Postmortem、Outage Tracking 與 Action Quality</strong></div><a class="position-card" href="#chapter-46-game-day-disaster-recovery-與-reliable-launch"><span>下一站</span><strong>46. Game Day、Disaster Recovery 與 Reliable Launch</strong></a></div>

本章位於 **Part 7：Incident、On-call 與學習**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Blameless postmortem</h3><div><span>白話定義</span><p>在不簡化成人員責備的前提下，重建事故條件、決策與系統性改善。</p></div><div class="example"><span>具體例子</span><p>問『為何合理操作能造成災難』，而不是只寫『工程師按錯按鈕』。</p></div><div class="relevance"><span>本章位置</span><p>產物必須包含 owner、期限和驗證方式，否則只是事故故事。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section><section class="term-card"><h3>Ownership</h3><div><span>白話定義</span><p>對元件品質、決策、值班與改善負最終責任的明確主體。</p></div><div class="example"><span>具體例子</span><p>平台組維護 deployment API；服務組仍對自己設定錯誤造成的事故負責。</p></div><div class="relevance"><span>本章位置</span><p>AI 可以執行工作但不能承擔組織責任，因此 ownership 不可寫成『模型』。</p></div></section><section class="term-card"><h3>Goal–Signal–Metric</h3><div><span>白話定義</span><p>先定義想改善的結果，再找能觀察結果的信號，最後選可計算的代理量。</p></div><div class="example"><span>具體例子</span><p>Goal 是縮短回饋時間；signal 是工程師更快得到有用結果；metric 才是 CI p95 時間。</p></div><div class="relevance"><span>本章位置</span><p>這個順序可降低為了容易量測而優化錯誤目標的風險。</p></div></section></div>

## 為什麼需要這一章？

事故若只歸因「工程師按錯按鈕」，下一位合理操作的人仍會遇到相同系統。若完全不談 decision 和 responsibility，又無法改善 control。Blameless 的目的是理解當時資訊、工具、incentives 和防線為何讓行動看似合理，並建立更強系統。

### 真實 Use Case

部署造成 outage，報告寫「操作員未仔細確認」。深入後發現 staging 與 production 按鈕相鄰、無 canary、rollback 需 20 分鐘、alert 延遲。改善 UI、權限、progressive rollout 和 alert 比要求大家更小心可重複。

<div class="context-grid">
<section><span>問題壓力</span><p>事故若只歸因「工程師按錯按鈕」，下一位合理操作的人仍會遇到相同系統。若完全不談 decision 和 responsibility，又無法改善 control。Blameless 的目的是理解當時資訊、工具、incentives 和防線為何讓行動看似合理，並建立更強系統。</p></section>
<section><span>交付能力</span><p>從 impact、timeline、contributing conditions、decision context 到可驗證改善，建立組織學習迴路。</p></section>
<section><span>真實場景</span><p>部署造成 outage，報告寫「操作員未仔細確認」。深入後發現 staging 與 production 按鈕相鄰、無 canary、rollback 需 20 分鐘、alert 延遲。改善 UI、權限、progressive rollout 和 alert 比要求大家更小心可重複。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>impact / SLO / affected users
        ↓
evidence-based timeline
        ↓
what happened? detection / response / recovery
        ↓
contributing conditions:
design · process · tools · knowledge · incentives · luck
        ↓
what went well / made worse / where defenses failed
        ↓
actions ranked by risk reduction
owner + deadline + verification + durable tracking
        ↓
fleet trends / recurring themes → roadmap / platform / policy</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Postmortem 先準確描述 impact 與 timeline，再分析 contributing factors；避免單一 root cause，因複雜事故通常需要多個條件同時存在。記錄 decisions based on information available，不用事後全知視角評判。What went well 能保留有效防線，near misses 和 luck 也要記錄。

Action item 要改變系統：消除 hazard、加自動 guard、縮小 blast radius、改善 detection/response 或建立演練。每項有 owner、deadline、priority、verification 和 tracking；「提醒大家」「多加測試」太模糊。修文件可能必要，但高風險問題只靠文件通常較弱。

單一 postmortem 之外要追 outage corpus：impact、duration、detection、cause categories、repeat、action completion 和 recurring dependencies。分類不是追責，而是發現跨團隊槓桿，例如 deployment、quota 或 identity 平台反覆出問題。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>以 user/SLO 定義 impact，從可信 evidence 建 timeline 和未知。</p></div><div class="flow-card"><span>2</span><p>分析多個 contributing conditions、failed defenses、decision context 和 luck。</p></div><div class="flow-card"><span>3</span><p>Actions 依風險降低排序，具有 owner、deadline、verification 和追蹤。</p></div><div class="flow-card"><span>4</span><p>Review action 完成不是 ticket closed，而是 signal/experiment 證明改善。</p></div><div class="flow-card"><span>5</span><p>聚合 outage corpus 找 recurring themes，投資跨組織 platform/policy。</p></div></div>

## Coding／實務例子

範例檢查 action item 是否具備最小可執行欄位，防止報告只有願望。

```python
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class FollowUp:
    action: str
    owner: str
    due: date
    verification: str
    risk_reduction: str

def actionable(item: FollowUp) -> bool:
    return all([
        item.action.strip(),
        item.owner.strip(),
        item.verification.strip(),
        item.risk_reduction.strip(),
    ])
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Owner 和 due 讓工作進入真實 capacity/priority，而非留在文末。</p></div><div class="flow-card"><span>2</span><p>Verification 說明如何知道改善生效，例如 game day 或新 SLI。</p></div><div class="flow-card"><span>3</span><p>Risk reduction 將 action 連回事故條件，避免無關 backlog。</p></div><div class="flow-card"><span>4</span><p>完整欄位仍不代表 action 足夠強，reviewer 要比較 hierarchy of controls。</p></div></div>

## Trade-offs 與 Failure Modes

- 把最後觸發者當 root cause，忽略讓單一操作可造成大傷害的系統。
- Action 全是文件/訓練，沒有自動 guard、blast-radius 或 design 改善。
- 報告完成後 actions 無 priority/capacity，數月後全部過期。
- Outage 分類被用於團隊排名，造成少報、降 severity 和失去學習資料。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 可從 logs/chat/actions 草擬 timeline、聚類 outage themes 和生成 action 候選，但也容易補齊缺失事件、過早歸因或把個人語句誤讀成責任。它應保留 provenance、區分 evidence/inference，並由參與者 review。AI 也不應決定人事後果；其輸出本身可能是 incident evidence。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 從多來源建立 timestamped draft，逐項附 source 和 confidence。</li><li>用 agent 將 actions 按 eliminate/guard/detect/respond/document 分類。</li><li>請 AI 聚類季度 incidents，找 recurring dependency、tool 和 process patterns。</li><li>讓 agent 把完成 action 連回新 test、policy、dashboard 或 game-day evidence。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>AI 不得虛構缺失 timeline；未知保留 unknown，conflict 同時呈現。</li><li>敏感 incident data 限定批准模型、participants 和 retention。</li><li>Root cause、責任、人事與 closure 由人類 committee/owners 判斷。</li><li>Generated actions 不能自動建立 destructive changes；先經風險與 owner review。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Postmortem 品質不在文字漂亮，而在組織模型是否更新。專家關心 action hierarchy：刪除危險比提醒更強，automatic guard 比 checklist 更穩；也接受有些事故風險不值得完全消除，但應把接受理由與 SLO/cost 寫清楚。Blameless 與 accountability 可以同時存在。

</aside>

## 動手驗證

1. 挑一份舊 postmortem，將 root-cause 單句改成 contributing conditions graph。
2. 執行 action validator，加入 priority、status、evidence link 和 overdue check。
3. 把十個 actions 分類為 eliminate/guard/detect/respond/document，找過度弱項。
4. 讓 AI 草擬 timeline，人工標出推論、缺失與來源錯誤。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Blameless 是否表示沒有人負責？</summary>

不是。保留事實、decision ownership 和必要 accountability，但不把個人缺陷當完整解釋，專注改變系統條件。

</details>

<details class="qa"><summary>Q2. 為何避免單一 root cause？</summary>

複雜事故通常由多個 design、process、tool、knowledge 和環境條件共同形成；只修最後觸發點容易再發。

</details>

<details class="qa"><summary>Q3. 好 action item 最少需要什麼？</summary>

具體改變、owner、期限、風險連結、verification 和 durable tracking，且優先選較強 control。

</details>

<details class="qa"><summary>Q4. Ticket closed 為何不等於改善完成？</summary>

Code/文件合併不代表防線有效；需 test、game day、SLI 或後續 evidence 驗證。

</details>

<details class="qa"><summary>Q5. Outage tracking 的組織價值？</summary>

跨事故找到 recurring themes 和高槓桿平台投資，而非每隊只修局部表象。

</details>

<details class="qa"><summary>Q6. AI timeline 最大風險？</summary>

把缺失補成合理故事、時間相關寫成因果、忽略 conflicting sources；需 provenance/confidence 和參與者 review。

</details>

<details class="qa"><summary>Q7. 何時可以合理接受某事故風險？</summary>

消除成本高於使用者/商業收益，且有量測、mitigation、owner 和明確風險接受；不是因 backlog 忙就默認。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Postmortem Culture](https://sre.google/sre-book/postmortem-culture/)
- [Site Reliability Engineering — Tracking Outages](https://sre.google/sre-book/tracking-outages/)
- [Site Reliability Engineering — Simplicity](https://sre.google/sre-book/simplicity/)
- [Microsoft — Incident response for AI systems](https://learn.microsoft.com/en-us/security/zero-trust/sfi/incident-response-ai-systems)

---

# 第 46 章　Game Day、Disaster Recovery 與 Reliable Launch

<p class="chapter-question">如何在真正事故前證明 backup、failover、runbook、on-call 和 launch plan 能共同工作？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 7 · Incident、On-call 與學習</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

以 hypothesis-driven exercise 驗證技術與人，將發現轉成 launch gate、automation 和 design 改善。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node active"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-45-blameless-postmortem-outage-tracking-與-action-quality"><span>上一站</span><strong>45. Blameless Postmortem、Outage Tracking 與 Action Quality</strong></a><div class="position-card current"><span>你在這裡</span><strong>46. Game Day、Disaster Recovery 與 Reliable Launch</strong></div><a class="position-card" href="#chapter-47-ai-ready-engineering-organization-與-sre-engagement"><span>下一站</span><strong>47. AI-ready Engineering Organization 與 SRE Engagement</strong></a></div>

本章位於 **Part 7：Incident、On-call 與學習**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Game day</h3><div><span>白話定義</span><p>在受控環境主動注入故障，驗證偵測、操作、架構與人員準備。</p></div><div class="example"><span>具體例子</span><p>關閉一個 dependency，確認 timeout、fallback、alert 和 runbook 是否工作。</p></div><div class="relevance"><span>本章位置</span><p>Game day 把未知問題提前變成可修復問題。</p></div></section><section class="term-card"><h3>Canary release</h3><div><span>白話定義</span><p>先把新版本暴露給少量流量，觀察結果後才擴大。</p></div><div class="example"><span>具體例子</span><p>先讓 1% request 使用新 checkout，再比較錯誤率和 latency。</p></div><div class="relevance"><span>本章位置</span><p>Canary 限制 blast radius；前提是有代表流量、健康指標與快速 rollback。</p></div></section><section class="term-card"><h3>Production</h3><div><span>白話定義</span><p>真實使用者、真實資料與真實商業影響所在的執行環境。</p></div><div class="example"><span>具體例子</span><p>測試環境 timeout 只是紅燈；production timeout 可能讓客戶重複付款。</p></div><div class="relevance"><span>本章位置</span><p>Production 的不確定性使 observability、rollback、capacity 和 incident response 成為必要能力。</p></div></section><section class="term-card"><h3>Invariant（不變條件）</h3><div><span>白話定義</span><p>系統任何合法狀態都必須成立的規則。</p></div><div class="example"><span>具體例子</span><p>銀行轉帳前後，所有帳戶餘額總和不應憑空增加。</p></div><div class="relevance"><span>本章位置</span><p>測試、型別和監控常用來保護 invariant；它比描述每一行實作更穩定。</p></div></section></div>

## 為什麼需要這一章？

文件、架構圖和單元測試無法證明真實權限、跨團隊協作、供應商、backup 和時間壓力下仍能恢復。Game day 在受控範圍注入故障；disaster recovery 驗證大範圍失效與資料恢復；launch review 則在新風險進入前檢查 readiness。

### 真實 Use Case

團隊相信 region failover 只需十分鐘，演練時才發現 DNS TTL、database promotion、secrets 和客服流程未對齊，實際要兩小時。這個安全失敗提供了 production outage 前最便宜的改善機會。

<div class="context-grid">
<section><span>問題壓力</span><p>文件、架構圖和單元測試無法證明真實權限、跨團隊協作、供應商、backup 和時間壓力下仍能恢復。Game day 在受控範圍注入故障；disaster recovery 驗證大範圍失效與資料恢復；launch review 則在新風險進入前檢查 readiness。</p></section>
<section><span>交付能力</span><p>以 hypothesis-driven exercise 驗證技術與人，將發現轉成 launch gate、automation 和 design 改善。</p></section>
<section><span>真實場景</span><p>團隊相信 region failover 只需十分鐘，演練時才發現 DNS TTL、database promotion、secrets 和客服流程未對齊，實際要兩小時。這個安全失敗提供了 production outage 前最便宜的改善機會。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>critical journey / launch risk
        ↓
hypothesis + success criteria (SLO / RTO / RPO / invariant)
        ↓
scope / blast radius / approvals / abort / rollback
        ↓
observe baseline
        ↓
inject failure or rehearse procedure
        ↓
detect → page → coordinate → mitigate → recover → verify
        ↓
gaps → owners/actions → re-test
        ↓
launch checklist / readiness evidence</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

演練從 hypothesis 開始，例如「失去單一區時 checkout 在 15 分鐘內恢復，無資料遺失且 error budget 消耗小於 X」。定義 scope、participants、customer impact、abort、rollback 和 observers。先桌上推演，再 staging，再低風險 production，逐步增加 fidelity。

DR 需同時驗證 control plane、data plane 和人。Backup restore、DNS、identity、secrets、quota、dependencies、communications 和 support 都可能是關鍵路徑。RTO/RPO 要以實測而非文件估計。演練也看是否只有某 expert 能完成。

Reliable launch review 依風險分級，檢查 ownership、SLO/capacity、monitoring/alerting、rollout/rollback、data migration、security/privacy、on-call/runbook 和 dependency readiness。Checklist 不是 approval theater；缺項要對應風險、owner 或正式 exception。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>從 critical journey/launch risk 定義 hypothesis、RTO/RPO/SLO 和 invariant。</p></div><div class="flow-card"><span>2</span><p>由 tabletop→staging→bounded production 漸進提高 fidelity。</p></div><div class="flow-card"><span>3</span><p>事前確認 scope、approvals、abort、rollback、communication 和觀察者。</p></div><div class="flow-card"><span>4</span><p>演練 detection、roles、permissions、dependencies、data restore 與使用者 communication。</p></div><div class="flow-card"><span>5</span><p>將 gaps 轉有 owner/verification actions，修正後重演並更新 launch gate。</p></div></div>

## Coding／實務例子

範例驗證演練結果是否符合 RTO/RPO 與資料 invariant，而不是只記錄『failover 成功』。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class DrillResult:
    recovery_minutes: int
    data_loss_minutes: int
    duplicate_transactions: int
    pages_actionable: bool

def passed(result: DrillResult, rto: int, rpo: int) -> list[str]:
    failures = []
    if result.recovery_minutes > rto:
        failures.append("RTO exceeded")
    if result.data_loss_minutes > rpo:
        failures.append("RPO exceeded")
    if result.duplicate_transactions:
        failures.append("transaction invariant violated")
    if not result.pages_actionable:
        failures.append("alerting/runbook gap")
    return failures
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Recovery 成功仍可能超過承諾時間，需與 RTO 比較。</p></div><div class="flow-card"><span>2</span><p>Data loss 與 duplicate 是不同 integrity dimensions。</p></div><div class="flow-card"><span>3</span><p>Actionable pages 驗證人類 control loop，不只測基礎設施。</p></div><div class="flow-card"><span>4</span><p>Failure list 直接轉成 actions 和下一次 drill acceptance criteria。</p></div></div>

## Trade-offs 與 Failure Modes

- 無 hypothesis 的 chaos 只製造中斷，無法判斷學到什麼。
- 演練永遠由原設計者執行，無法發現知識與權限單點。
- 只測 failover、不測 failback/reconciliation，恢復後留下分裂 state。
- Launch checklist 所有項目都可口頭豁免，實際沒有 gate。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI launch 增加 model/provider regression、prompt injection、RAG poisoning、tool excessive agency、成本暴增和不可重現品質等場景。演練應包含切換模型、停用 tools、fallback、trace preservation 和安全 containment。AI 可產生 scenario、擔任模擬使用者或 scribe，但 production fault scope 和 abort 由 deterministic controls。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 從 architecture/threat model 產生 failure scenarios 和 hidden dependencies。</li><li>用 agent 模擬使用者、support 或 dependency response，增加演練廣度。</li><li>請 AI 即時整理 timeline/gaps，不參與 production mutation。</li><li>讓 agent 比較多次 drill，追蹤 RTO/RPO、action completion 和 recurring gaps。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Production injection 使用 allowlisted faults、硬 scope、time limit、abort 和人類 IC。</li><li>AI scenario 不得包含未批准 secrets/data 或鼓勵繞過 control。</li><li>AI-specific drill 保存 model/prompt/tool trace，並驗證 deterministic fallback。</li><li>Launch exception 有具名 risk owner、期限、補償 control 和 follow-up。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Game day 是把未知變成 backlog 的機器。成熟組織不以「沒有發現問題」為成功，反而希望在安全環境發現真缺口。AI 能擴展 scenario 和觀察能力，但若基本 restore、owner、SLO 都未建立，增加更花俏的 chaos 沒有意義。

</aside>

## 動手驗證

1. 為 region failure 寫 hypothesis、RTO/RPO、scope、abort、roles 和 verification。
2. 執行 drill validator，加入 failback/reconciliation 與 communication 指標。
3. 為新服務完成 launch checklist，將每個缺項連到 risk/owner。
4. 設計 AI-specific game day：provider outage、prompt injection、tool misuse、fallback。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Game day 與隨機 chaos 差別？</summary>

Game day 有明確 hypothesis、success criteria、scope、abort、observation 和 follow-up；不是為破壞而破壞。

</details>

<details class="qa"><summary>Q2. RTO 與 RPO 如何驗證？</summary>

實際量從故障到恢復時間，以及恢復後遺失/需重建的資料時間，不能只讀文件設定。

</details>

<details class="qa"><summary>Q3. 為何要測 failback？</summary>

Failover 後資料、traffic 和 ownership 可能分裂；返回正常狀態與 reconciliation 也可能造成事故。

</details>

<details class="qa"><summary>Q4. Launch checklist 如何避免形式化？</summary>

每項連到具體風險與 evidence，缺項有 owner/exception，並在 incident 後更新；不是全部勾選即可。

</details>

<details class="qa"><summary>Q5. 誰不應總是執行演練？</summary>

只有原作者/最資深 expert；應讓一般 on-call、跨團隊和 support參與，測知識與權限。

</details>

<details class="qa"><summary>Q6. AI-specific drill 需要哪些場景？</summary>

模型/provider 退化、prompt injection、RAG poisoning、tool misuse、cost spike、trace/kill-switch/fallback。

</details>

<details class="qa"><summary>Q7. 演練成功的真正標準？</summary>

在可控傷害下取得可行動新 evidence，完成改善並重測；不是報表寫『所有系統正常』。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Testing for Reliability](https://sre.google/sre-book/testing-reliability/)
- [Site Reliability Engineering — Reliable Product Launches](https://sre.google/sre-book/reliable-product-launches/)
- [Microsoft — Incident response for AI systems](https://learn.microsoft.com/en-us/security/zero-trust/sfi/incident-response-ai-systems)
- [OWASP — Top 10 for LLM Applications 2025](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

---
