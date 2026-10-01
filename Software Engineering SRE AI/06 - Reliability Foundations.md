---
title: "SRE 與可靠性模型"
part: 5
as_of: 2026-09-30
---

# Part 5　SRE 與可靠性模型

把可靠性從感覺改成可量測的產品決策，以 SLO、error budget、observability、alerting 與 capacity 管理 production。

# 第 30 章　Production Environment、Operations 與 SRE

<p class="chapter-question">SRE 和傳統維運、DevOps、平台工程有何關係？為什麼只是把工程師加入值班仍不夠？</p>

<div class="chapter-meta"><span>難度：入門</span><span>Part 5 · SRE 與可靠性模型</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

以使用者可靠性與長期工程改善為中心，分清 service ownership、operations work 和 SRE 方法。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node active"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-29-continuous-delivery-canary-與-rollback"><span>上一站</span><strong>29. Continuous Delivery、Canary 與 Rollback</strong></a><div class="position-card current"><span>你在這裡</span><strong>30. Production Environment、Operations 與 SRE</strong></div><a class="position-card" href="#chapter-31-toil-automation-與逐步取得自治"><span>下一站</span><strong>31. Toil、Automation 與逐步取得自治</strong></a></div>

本章位於 **Part 5：SRE 與可靠性模型**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Site Reliability Engineering</h3><div><span>白話定義</span><p>以軟體工程方法設計與營運可靠 production 系統的職能與實務。</p></div><div class="example"><span>具體例子</span><p>SRE 不只手動重啟服務，而會修 automation、capacity model、alert 和架構。</p></div><div class="relevance"><span>本章位置</span><p>核心是讓操作經驗轉成可重複的工程機制。</p></div></section><section class="term-card"><h3>Service（服務）</h3><div><span>白話定義</span><p>長時間運行、透過網路或訊息介面替其他人或系統提供能力的軟體。</p></div><div class="example"><span>具體例子</span><p>付款 API 接收 request，驗證、寫入資料庫，再回傳成功或失敗。</p></div><div class="relevance"><span>本章位置</span><p>SRE 的可靠性目標通常以服務向使用者提供的行為為單位。</p></div></section><section class="term-card"><h3>Production</h3><div><span>白話定義</span><p>真實使用者、真實資料與真實商業影響所在的執行環境。</p></div><div class="example"><span>具體例子</span><p>測試環境 timeout 只是紅燈；production timeout 可能讓客戶重複付款。</p></div><div class="relevance"><span>本章位置</span><p>Production 的不確定性使 observability、rollback、capacity 和 incident response 成為必要能力。</p></div></section><section class="term-card"><h3>Ownership</h3><div><span>白話定義</span><p>對元件品質、決策、值班與改善負最終責任的明確主體。</p></div><div class="example"><span>具體例子</span><p>平台組維護 deployment API；服務組仍對自己設定錯誤造成的事故負責。</p></div><div class="relevance"><span>本章位置</span><p>AI 可以執行工作但不能承擔組織責任，因此 ownership 不可寫成『模型』。</p></div></section></div>

## 為什麼需要這一章？

Production 需要部署、監控、容量、事故、權限、資料保護和支援。若團隊只靠人手逐項操作，服務成長會帶來線性 toil；若開發者把部署後問題完全交給另一組，設計也不會收到真實 feedback。SRE 的重點是用軟體工程、量測和共同 incentives 改善營運系統，而不只是換職稱。

### 真實 Use Case

一個服務每週因記憶體洩漏重啟。Operations 每次快速處理但問題持續；SRE 會先建立可靠偵測與安全重啟，再分析 heap、修復 leak、加入 regression test 和 capacity guard，使未來事件量下降。

<div class="context-grid">
<section><span>問題壓力</span><p>Production 需要部署、監控、容量、事故、權限、資料保護和支援。若團隊只靠人手逐項操作，服務成長會帶來線性 toil；若開發者把部署後問題完全交給另一組，設計也不會收到真實 feedback。SRE 的重點是用軟體工程、量測和共同 incentives 改善營運系統，而不只是換職稱。</p></section>
<section><span>交付能力</span><p>以使用者可靠性與長期工程改善為中心，分清 service ownership、operations work 和 SRE 方法。</p></section>
<section><span>真實場景</span><p>一個服務每週因記憶體洩漏重啟。Operations 每次快速處理但問題持續；SRE 會先建立可靠偵測與安全重啟，再分析 heap、修復 leak、加入 regression test 和 capacity guard，使未來事件量下降。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Product / service team
  ├─ feature &amp; architecture ownership
  └─ production responsibility
            ↕ shared SLO / error budget
SRE / platform
  ├─ reliability engineering
  ├─ automation / observability / capacity
  ├─ incident practices
  └─ reusable platform &amp; standards

manual response → understand pattern → engineer system → fewer future events</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Operations 是維持服務運行所需的活動；DevOps 常指開發與營運共同責任的文化與方法；SRE 是一種具體實作：由具軟體工程能力的團隊管理 availability、latency、performance、change、monitoring、emergency 和 capacity，並限制手動 toil 以保留工程時間。平台工程則把常見能力做成自助產品。實際組織可重疊，重點是 contract 而非名稱。

Service team 不應因有 SRE 就放棄 production ownership。SRE 需要有權要求可靠性工作、停止危險發布或退出無法持續的 engagement；產品團隊仍需修 code、理解 domain 和承擔 roadmap。共享 SLO/error budget 能避免一方只追 feature、另一方只追零變更。

SRE 工作應產生槓桿：自動化、簡化、capacity model、reliable release、incident learning 和 platform。手動操作有時必要，尤其在未知事故，但之後要問能否消除、降低頻率或讓一般 on-call 安全處理。若 SRE 永遠充當 ticket queue，就失去工程目的。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>明確定義 service owner、SRE engagement、on-call 和 escalation 的責任。</p></div><div class="flow-card"><span>2</span><p>用 SLI/SLO/error budget 對齊可靠性與發布，而非抽象爭論。</p></div><div class="flow-card"><span>3</span><p>追蹤 operation work 與 engineering work，保留改善長期系統的 capacity。</p></div><div class="flow-card"><span>4</span><p>將重複事故轉成 code、automation、platform、test 或 design change。</p></div><div class="flow-card"><span>5</span><p>定期檢查 engagement 是否仍有槓桿；沒有共同承諾時調整或退出。</p></div></div>

## Coding／實務例子

用分類函式區分純操作與具有長期槓桿的工程工作。真實任務可能同時包含兩者，應按實際時間拆分。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Work:
    repeated: bool
    manual: bool
    scales_with_service: bool
    reduces_future_work: bool

def classify(work: Work) -> str:
    if work.repeated and work.manual and work.scales_with_service:
        return "toil"
    if work.reduces_future_work:
        return "engineering"
    return "operations"

print(classify(Work(True, True, True, False)))
print(classify(Work(False, False, False, True)))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>重複、手動、隨服務線性成長是 toil 的強 signals。</p></div><div class="flow-card"><span>2</span><p>修 automation 或架構能減少未來工作，屬工程投資。</p></div><div class="flow-card"><span>3</span><p>一次性 incident response 可能是 operations，但其 follow-up 可成為 engineering。</p></div><div class="flow-card"><span>4</span><p>分類目的是調整資源與系統，不是貶低必要的操作工作。</p></div></div>

## Trade-offs 與 Failure Modes

- 把所有 manual work 都稱為 toil，會忽略需要判斷與學習的高價值操作。
- SRE 成為產品團隊的永久 ticket queue，無時間做根因改善。
- 只用 uptime 衡量 SRE，可能鼓勵禁止變更而非建立安全 delivery。
- 平台沒有使用者研究與 SLO，會把下游團隊綁在另一個不可靠服務。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI-SRE 能搜尋 telemetry、整理事件、執行標準 runbook 和產生修復候選，最適合降低資訊整理與重複診斷 toil；它不會自動解決 service ownership 和 incentives。導入順序應從唯讀調查、建議、需批准操作，再到可逆低風險自治。每次 AI 操作仍由具名 service/SRE owner 承擔，且要留下 evidence 和 audit。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 彙整 logs、metrics、traces、changes 和相似 incidents，建立 investigation brief。</li><li>用 agent 執行唯讀 health checks 與 runbook 導航，縮短 context gathering。</li><li>請 AI 將重複 tickets 聚類，找值得 automation/platform 投資的 toil。</li><li>讓 agent 草擬 code fix、test 和 postmortem action，由 owners review。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Production agent 預設 read-only，mutation 使用專用 identity、最小 scope 和 approval。</li><li>每個結論連回原始 telemetry/change，不接受無 evidence 的 root-cause 宣告。</li><li>操作有 step/time/resource budget、idempotency、rollback 和 kill switch。</li><li>量人工接管、錯誤建議、policy violation 和 incident impact，不只量省下時間。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Domain expert 會區分「讓操作更快」和「讓操作不再需要」。AI 很容易把 ticket 處理自動化，卻讓根本架構問題繼續存在。高槓桿 SRE 仍會投資簡化、可靠 release、capacity 和 service design；Agent 是執行與資訊介面，不是可靠性策略本身。

</aside>

## 動手驗證

1. 列出團隊一週 operations tasks，依 toil/operations/engineering 分類並估時間。
2. 執行分類範例，為灰色任務補上『是否需要人類 judgment』維度。
3. 為 product/SRE 寫 engagement contract：SLO、ownership、toil、退出條件。
4. 設計 AI-SRE autonomy ladder，為每級列 allowed actions、evidence 和 approval。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. SRE 最簡潔的定義是什麼？</summary>

用軟體工程方法設計與營運可靠 production 系統，將操作經驗轉成可重複的 automation、platform 和 architecture。

</details>

<details class="qa"><summary>Q2. DevOps、SRE、platform 是否互斥？</summary>

不互斥。DevOps 偏文化/原則，SRE 是具體可靠性實作，platform 提供自助能力；組織可依情境重疊。

</details>

<details class="qa"><summary>Q3. 為何 service team 不能把 production 全交給 SRE？</summary>

Domain design 和 feature changes 決定大部分風險；沒有共同 ownership，開發得不到 feedback，SRE 也無法單方面修所有根因。

</details>

<details class="qa"><summary>Q4. 手動工作何時不是 toil？</summary>

一次性、需要高判斷、帶來學習或不隨服務線性成長時；但仍可檢查是否能降低風險與負擔。

</details>

<details class="qa"><summary>Q5. AI-SRE 最安全的起點？</summary>

唯讀 context gathering、資料關聯、runbook 導航和建議，先評估 precision 與人類使用方式，再逐步授權。

</details>

<details class="qa"><summary>Q6. 為什麼只量 AI 節省時間不足？</summary>

錯誤建議、額外 review、風險、接管和事故可能把成本轉移；需同看品質、policy、stability 和使用者結果。

</details>

<details class="qa"><summary>Q7. SRE engagement 何時應改變？</summary>

當服務成熟度、SLO、toil、owner commitment 或組織優先級改變；若只剩 ticket 處理且無改善空間，應重新談 contract。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Introduction](https://sre.google/sre-book/introduction/)
- [Site Reliability Engineering — Eliminating Toil](https://sre.google/sre-book/eliminating-toil/)
- [Site Reliability Engineering — Evolving the SRE Engagement Model](https://sre.google/sre-book/evolving-sre-engagement-model/)
- [Google Cloud — How Google SRE is using agentic AI](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)

---

# 第 31 章　Toil、Automation 與逐步取得自治

<p class="chapter-question">哪些重複工作應自動化？為什麼錯誤流程自動化後，通常只是更快造成事故？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 5 · SRE 與可靠性模型</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

以頻率、風險、穩定性和可驗證性排序 toil，從 runbook 到 deterministic automation 再到 bounded agent。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node active"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-30-production-environment-operations-與-sre"><span>上一站</span><strong>30. Production Environment、Operations 與 SRE</strong></a><div class="position-card current"><span>你在這裡</span><strong>31. Toil、Automation 與逐步取得自治</strong></div><a class="position-card" href="#chapter-32-sli-slo-sla-與-error-budget"><span>下一站</span><strong>32. SLI、SLO、SLA 與 Error Budget</strong></a></div>

本章位於 **Part 5：SRE 與可靠性模型**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Toil</h3><div><span>白話定義</span><p>手動、重複、可自動化、戰術性且隨服務成長線性增加的營運工作。</p></div><div class="example"><span>具體例子</span><p>每天複製 log、手算容量，再逐台修改設定。</p></div><div class="relevance"><span>本章位置</span><p>消除 toil 不是刪除所有操作，而是保留時間做能長期降低操作量的工程。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section><section class="term-card"><h3>AI Agent</h3><div><span>白話定義</span><p>能接收目標、規劃步驟、呼叫工具、觀察結果並迭代的模型系統。</p></div><div class="example"><span>具體例子</span><p>Coding agent 搜尋 repository、修改檔案、跑測試，再依失敗訊息修正。</p></div><div class="relevance"><span>本章位置</span><p>Agent 增加速度與自治，也帶來 excessive agency、秘密外洩與不可預測操作等新風險。</p></div></section><section class="term-card"><h3>Least privilege</h3><div><span>白話定義</span><p>身份只取得完成當前任務所需的最小權限、範圍和時間。</p></div><div class="example"><span>具體例子</span><p>調查 agent 可讀 logs，但預設不能 restart production。</p></div><div class="relevance"><span>本章位置</span><p>它限制 prompt injection、誤判或帳號外洩造成的 blast radius。</p></div></section></div>

## 為什麼需要這一章？

Automation 有建置和維護成本，也會把一個人的錯誤放大到所有機器。若流程尚未理解、例外很多或結果難驗證，立即全自動化會把 tacit judgment 隱藏在脆弱 script。另一方面，長期重複手動工作消耗人力、產生不一致並讓服務無法成長。

### 真實 Use Case

團隊每天手動擴容：看 queue depth、計算 replicas、修改 config、觀察。先將計算與 dry-run 自動化，再建立 bounds 和 rollback，最後才讓 controller 自動執行；直接讓 agent 讀 dashboard 後自由修改整個 cluster 風險過高。

<div class="context-grid">
<section><span>問題壓力</span><p>Automation 有建置和維護成本，也會把一個人的錯誤放大到所有機器。若流程尚未理解、例外很多或結果難驗證，立即全自動化會把 tacit judgment 隱藏在脆弱 script。另一方面，長期重複手動工作消耗人力、產生不一致並讓服務無法成長。</p></section>
<section><span>交付能力</span><p>以頻率、風險、穩定性和可驗證性排序 toil，從 runbook 到 deterministic automation 再到 bounded agent。</p></section>
<section><span>真實場景</span><p>團隊每天手動擴容：看 queue depth、計算 replicas、修改 config、觀察。先將計算與 dry-run 自動化，再建立 bounds 和 rollback，最後才讓 controller 自動執行；直接讓 agent 讀 dashboard 後自由修改整個 cluster 風險過高。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>observe manual work
        ↓
document decision / inputs / exceptions
        ↓
assistive tool (read-only / recommendation)
        ↓
deterministic script + dry-run
        ↓
approval + bounded mutation
        ↓
closed-loop automation with SLO / rollback
        ↓
agent only where semantic ambiguity remains</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

先量 toil：頻率、每次時間、成長率、錯誤率、認知中斷和 on-call 影響。優先處理高頻、高風險且規則穩定的工作。自動化前先寫 inputs、decision、outputs、exceptions 和 verification；若無法說明正確結果，automation 也無法可靠判斷。

成熟度從輔助到閉環。Read-only tool 收集資訊；推薦系統由人核准；deterministic script 有 dry-run、idempotency 和 bounds；controller 根據明確 signal 自動動作並觀察回饋。Agent 適合補足語意解讀、跨工具協調和長尾，但應把危險 action 留在 policy-checked tools。

Automation 需要 ownership、SLO 和 escape hatch。當環境異常或 signal 不可信時，系統要 fail safe、停止並升級，而不是持續重試。每次人工 override 都是 feedback：若頻繁出現，模型或規則需要更新。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>量 toil 的頻率、時間、風險、成長與中斷成本，建立優先序。</p></div><div class="flow-card"><span>2</span><p>先讓人工流程穩定且可說明，再分離收集、決策、執行和驗證。</p></div><div class="flow-card"><span>3</span><p>從 read-only/dry-run 開始，加入 idempotency、bounds、approval 和 rollback。</p></div><div class="flow-card"><span>4</span><p>閉環 automation 監控 action 結果，signal 不可信時停止並升級。</p></div><div class="flow-card"><span>5</span><p>追蹤 overrides、failures 和 avoided work，持續修正或刪除 automation。</p></div></div>

## Coding／實務例子

以下 autoscaler 只計算建議並限制每次變動。Mutation 可由另一個受控元件在核准後執行。

```python
from math import ceil

def desired_replicas(
    queue_depth: int,
    capacity_per_replica: int,
    current: int,
    minimum: int = 2,
    maximum: int = 50,
    max_step: int = 5,
) -> int:
    raw = ceil(queue_depth / capacity_per_replica)
    bounded = min(maximum, max(minimum, raw))
    return min(current + max_step, max(current - max_step, bounded))

print(desired_replicas(4200, 200, current=10))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>計算與執行分離，容易 dry-run、review 和測試。</p></div><div class="flow-card"><span>2</span><p>Min/max 限制絕對範圍，<code>max_step</code> 限制單次 blast radius。</p></div><div class="flow-card"><span>3</span><p>真實 controller 還要 cooldown、health、quota、cost 和 delayed feedback。</p></div><div class="flow-card"><span>4</span><p>若 <code>capacity_per_replica</code> 過時，應停止或保守降級，而非盲目縮放。</p></div></div>

## Trade-offs 與 Failure Modes

- 自動化不穩定流程會把例外與錯誤以機器速度擴散。
- 只算節省工時，不計 maintenance、false action 和 incident 成本。
- 無 idempotency 的重試會重複建立資源或執行副作用。
- Automation owner 離開後無人理解，工具本身變成新的 toil 和風險。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI agents 能處理傳統 automation 難以編碼的語意步驟，但機率性也增加變異。最佳 pattern 是 agent 決定『建議呼叫哪個高層 tool 及參數』，tool broker 用 schema、policy、bounds 和 identity 驗證，再執行 deterministic action。自治權由 eval、shadow mode、歷史 precision 和可逆性逐步取得。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>用 AI 將自然語言 ticket 轉成標準 runbook/automation parameters。</li><li>讓 agent 在 read-only mode 收集 evidence 並產生 dry-run change plan。</li><li>對長尾 exceptions 使用 AI 分類，穩定 pattern 再轉 deterministic code。</li><li>在 shadow mode 比較 agent 建議與人類決策，建立自治 evidence。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Tool broker 驗證 schema、identity、resource scope、bounds 和 policy。</li><li>所有 mutation 有 idempotency key、preview、audit、rollback 和最大 action 數。</li><li>Agent 遇到 conflicting/missing telemetry 必須停止升級，不能猜測補值。</li><li>高風險或不可逆操作永遠要求人類批准與 separation of duties。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Automation maturity 不是從 script 直接跳到全自治。專家會把可確定部分盡量 deterministic，讓 agent 只處理真正需要語意的狹窄區域。最好的 toil elimination 有時是刪除需求、簡化產品或修 upstream design，而不是為錯誤流程建更聰明的機器人。

</aside>

## 動手驗證

1. 建立 toil backlog，以年工時、風險、規則穩定性和可驗證性排序。
2. 執行 autoscaler，測零容量、負 queue、突然降載等 invalid inputs。
3. 將一個 runbook 拆成 observe/decide/act/verify，標記可 deterministic 的步驟。
4. 設計 agent shadow eval：案例、human baseline、precision、unsafe action 和接管條件。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. 哪些 toil 最適合先自動化？</summary>

高頻、隨規模成長、錯誤代價明確、規則穩定且結果可驗證的工作，通常有最大槓桿。

</details>

<details class="qa"><summary>Q2. 為什麼先做 dry-run？</summary>

分離計算與 mutation，讓人和系統檢查 scope、參數與預期結果，降低首次自動化 blast radius。

</details>

<details class="qa"><summary>Q3. Closed-loop automation 需要什麼？</summary>

可靠 signal、明確 policy、bounded action、觀察結果、rollback/stop 和 owner；不是只執行一次 script。

</details>

<details class="qa"><summary>Q4. Agent 與 deterministic automation 如何搭配？</summary>

Agent 處理語意分類和選擇高層 action，deterministic tool 驗證參數、權限與執行，將危險自由度限制在外。

</details>

<details class="qa"><summary>Q5. 頻繁 human override 表示什麼？</summary>

可能 signal 不可信、policy 過時、例外未建模或 automation 使用情境錯誤，是需要調整的 feedback。

</details>

<details class="qa"><summary>Q6. 自動化何時不值得？</summary>

任務低頻低風險、規則快速變、驗證困難，或直接刪除/簡化流程更便宜時。

</details>

<details class="qa"><summary>Q7. 自治權如何逐步取得？</summary>

從 read-only、recommend、dry-run、approve-to-act 到 bounded auto，依 representative eval、shadow 歷史、可逆性和 audit 擴大。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Eliminating Toil](https://sre.google/sre-book/eliminating-toil/)
- [Site Reliability Engineering — The Evolution of Automation at Google](https://sre.google/sre-book/automation-at-google/)
- [Google Cloud — How Google SRE is using agentic AI](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)
- [OWASP — Top 10 for LLM Applications 2025](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

---

# 第 32 章　SLI、SLO、SLA 與 Error Budget

<p class="chapter-question">可靠性如何從『感覺穩定』變成可計算、可告警、能指導發布與投資的產品決策？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 5 · SRE 與可靠性模型</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

從使用者 journey 定義 valid events、good events、窗口與目標，再把允許失敗轉成共同政策。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node active"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-31-toil-automation-與逐步取得自治"><span>上一站</span><strong>31. Toil、Automation 與逐步取得自治</strong></a><div class="position-card current"><span>你在這裡</span><strong>32. SLI、SLO、SLA 與 Error Budget</strong></div><a class="position-card" href="#chapter-33-observability-從輸出重建系統內部狀態"><span>下一站</span><strong>33. Observability：從輸出重建系統內部狀態</strong></a></div>

本章位於 **Part 5：SRE 與可靠性模型**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>SLI（Service Level Indicator）</h3><div><span>白話定義</span><p>以使用者視角量測服務品質的指標。</p></div><div class="example"><span>具體例子</span><p>成功 checkout 數除以所有有效 checkout 數。</p></div><div class="relevance"><span>本章位置</span><p>SLI 是觀測事實；選錯 measurement point 會得到漂亮卻無用的數字。</p></div></section><section class="term-card"><h3>SLO（Service Level Objective）</h3><div><span>白話定義</span><p>某段時間內希望 SLI 達到的明確目標。</p></div><div class="example"><span>具體例子</span><p>28 天內 99.9% 有效 API request 成功。</p></div><div class="relevance"><span>本章位置</span><p>SLO 讓可靠性、告警和發布決策共享同一尺度。</p></div></section><section class="term-card"><h3>SLA（Service Level Agreement）</h3><div><span>白話定義</span><p>服務提供者與客戶之間含後果或補償的正式承諾。</p></div><div class="example"><span>具體例子</span><p>月可用性低於 99.9% 時提供 service credit。</p></div><div class="relevance"><span>本章位置</span><p>內部 SLO 通常應比外部 SLA 更嚴格，留下反應空間。</p></div></section><section class="term-card"><h3>Error budget</h3><div><span>白話定義</span><p>SLO 允許的不可靠量；100% 減去目標就是可消耗比例。</p></div><div class="example"><span>具體例子</span><p>99.9% 月 SLO 約允許 0.1% valid events 失敗。</p></div><div class="relevance"><span>本章位置</span><p>它把『穩定或快速』的爭論轉成可觀察的共同政策。</p></div></section></div>

## 為什麼需要這一章？

服務團隊若沒有共同可靠性定義，開發者會看 server uptime、使用者看交易成功、管理者看投訴，彼此都可能說自己正確。追求 100% 也不實際：成本極高且會阻止有價值變更。SLO 把使用者結果、允許風險和時間窗口放進同一尺度。

### 真實 Use Case

Checkout 有 100 台 server 都在線，但付款 dependency 回 500，使用者仍無法購買。Machine uptime 不是正確 SLI。更好的 event-based SLI 是成功完成的有效 checkout / 所有有效 checkout，並排除明顯 client invalid requests。

<div class="context-grid">
<section><span>問題壓力</span><p>服務團隊若沒有共同可靠性定義，開發者會看 server uptime、使用者看交易成功、管理者看投訴，彼此都可能說自己正確。追求 100% 也不實際：成本極高且會阻止有價值變更。SLO 把使用者結果、允許風險和時間窗口放進同一尺度。</p></section>
<section><span>交付能力</span><p>從使用者 journey 定義 valid events、good events、窗口與目標，再把允許失敗轉成共同政策。</p></section>
<section><span>真實場景</span><p>Checkout 有 100 台 server 都在線，但付款 dependency 回 500，使用者仍無法購買。Machine uptime 不是正確 SLI。更好的 event-based SLI 是成功完成的有效 checkout / 所有有效 checkout，並排除明顯 client invalid requests。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>user journey
   ↓
valid events: 什麼算一次機會？
good events: 什麼結果對使用者夠好？
   ↓
SLI = good / valid
   ↓
SLO = target + window (例如 99.9% / 28d)
   ↓
error budget = valid × (1 - target)
   ↓
burn / policy:
release normally | slow down | reliability work | emergency

SLA = 對外含後果承諾，通常比內部 SLO 寬鬆</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

SLI 要從使用者入口量測，定義 denominator 尤其重要。Availability 可用成功 events；latency 可定義在 threshold 內的 good events；freshness、correctness 和 durability 也可能是 SLI。不要把所有 server metrics 都稱為 SLI，它們是診斷 signals。

SLO 包含目標與窗口。Rolling window 對近期事件敏感，calendar window 易對帳；可依決策選擇。目標應根據使用者需要、dependency、成本和替代方案，不是競賽九數。比依賴更嚴格卻無 fallback 的 SLO 可能不可達。

Error budget 將允許的不可靠量具體化。政策可依剩餘預算或 burn rate 調整 rollout、可靠性工作與 exception。它不是「故意製造錯誤」或每月一定用完，而是承認變更與完美可靠都有成本。SLA 則是含商業後果的外部承諾，需與 legal/product 合作。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>從 critical user journeys 列 valid/good events，選接近使用者的 measurement point。</p></div><div class="flow-card"><span>2</span><p>定義窗口、目標、資料延遲、排除規則和 owner，回放歷史資料驗證。</p></div><div class="flow-card"><span>3</span><p>確認 dependency 與 fallback 能支持目標，估算可靠性提升成本。</p></div><div class="flow-card"><span>4</span><p>把 error budget 接到明確 change/reliability policy，而非只做 dashboard。</p></div><div class="flow-card"><span>5</span><p>定期用 incidents、投訴和產品變化重訪 SLI/SLO，避免量錯目標。</p></div></div>

## Coding／實務例子

範例計算 event-based SLI、允許 bad events 與已消耗比例。用 Decimal 避免展示時的浮點誤差。

```python
from decimal import Decimal

def error_budget(valid: int, good: int, target: Decimal) -> dict:
    bad = valid - good
    allowed_bad = Decimal(valid) * (Decimal("1") - target)
    consumed = Decimal(bad) / allowed_bad if allowed_bad else Decimal("Infinity")
    return {
        "sli": Decimal(good) / Decimal(valid),
        "bad": bad,
        "allowed_bad": allowed_bad,
        "budget_consumed": consumed,
    }

print(error_budget(1_000_000, 999_200, Decimal("0.999")))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>99.9% 目標在一百萬 valid events 中允許約一千 bad events。</p></div><div class="flow-card"><span>2</span><p>實際 bad 為八百，消耗 80% budget；剩餘空間可支援風險決策。</p></div><div class="flow-card"><span>3</span><p>若 denominator 包含惡意或 invalid requests，SLI 可能被扭曲，定義需版本化。</p></div><div class="flow-card"><span>4</span><p>低流量服務 event count 少，可能要結合 time-based 或較長窗口。</p></div></div>

## Trade-offs 與 Failure Modes

- 選 server uptime 而非 user outcome，得到健康機器卻失敗產品。
- 目標任意加九，成本大增但使用者未感知差異。
- 排除規則太寬，把真正服務錯誤標為 client fault。
- Error budget policy 只懲罰開發，不提供可靠性投資與跨團隊責任。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 服務除了 availability/latency，還可能需要 answer quality、groundedness、tool success、policy violation、cost 和 human takeover SLI。品質是機率性且 ground truth 昂貴，可用線上 proxy、抽樣人工 review 和離線 eval 組合。模型更新、prompt、retrieval 和 tools 都是 change，應共用 error budget 與 rollout。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 協助從使用者旅程草擬 SLI 候選與 denominator edge cases。</li><li>對 AI agent 建立 task success、unsafe action、tool error、人工接管和成本 SLI。</li><li>用離線 eval、shadow traffic 和線上抽樣校準品質 proxy。</li><li>讓 agent 解釋 budget burn 的主要 cohorts/changes，附可追溯 query。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>SLO 定義與風險接受由產品/service owners 決定，模型不能自行調低目標。</li><li>LLM-as-judge 需以人類標註校準、版本化並監控 bias/drift。</li><li>品質、policy、latency 和 cost 同時觀測，不能只優化回答分數。</li><li>AI 指標按 cohort 分析但遵守隱私、樣本量和資料最小化。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

好 SLO 是決策介面，不是漂亮數字。它應能回答何時 page、何時放慢 rollout、哪個 reliability project 值得做。專家寧願有一個貼近 user journey 且可行動的 SLO，也不要數十個無人使用的九數；AI 系統更要承認品質不確定並設計抽樣與接管。

</aside>

## 動手驗證

1. 為一個服務寫 valid/good event 定義，列出五個 denominator edge cases。
2. 執行計算器，測 99%、99.9%、99.99% 的 allowed bad 差距。
3. 寫 error-budget policy：正常、快速 burn、耗盡和 exception 四種狀態。
4. 為 AI agent 定義五個 SLI，指出哪個有 ground truth、哪個需 proxy。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. SLI、SLO、SLA 分別是什麼？</summary>

SLI 是量測事實；SLO 是內部目標與窗口；SLA 是對外含後果/補償的承諾。

</details>

<details class="qa"><summary>Q2. Denominator 為何關鍵？</summary>

它定義哪些事件是服務機會；排除過多會掩蓋失敗，包含無效流量又會扭曲使用者可靠性。

</details>

<details class="qa"><summary>Q3. 為何 100% 通常不是好目標？</summary>

成本極高、可能阻止有價值變更，且 dependencies/clients 也非完美；應依使用者需求和成本設定。

</details>

<details class="qa"><summary>Q4. Error budget 如何對齊開發與 SRE？</summary>

將允許風險量化，預算健康時可持續變更，快速燃燒時共同降低風險並投資可靠性。

</details>

<details class="qa"><summary>Q5. Server CPU 是否是 SLI？</summary>

通常是診斷 metric，不直接代表使用者結果；除非 service contract 本身就是提供 CPU 資源。

</details>

<details class="qa"><summary>Q6. AI answer quality 如何做 SLI？</summary>

結合可驗證 task result、policy checks、離線 eval、抽樣人工標註與校準 proxy，並版本化 judge。

</details>

<details class="qa"><summary>Q7. 何時應重訪 SLO？</summary>

產品 journey、使用者期待、dependencies、流量、成本或測量方式改變，以及 incidents 顯示 SLO 未代表傷害時。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Embracing Risk](https://sre.google/sre-book/embracing-risk/)
- [Site Reliability Engineering — Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Site Reliability Engineering — Introduction](https://sre.google/sre-book/introduction/)
- [OpenAI — Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)

---

# 第 33 章　Observability：從輸出重建系統內部狀態

<p class="chapter-question">Metrics、logs、traces 各回答什麼？如何讓值班者從『系統慢』走到可驗證的故障假設？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 5 · SRE 與可靠性模型</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

建立 signal model、共同 context、structured events 與變更關聯，讓 telemetry 真正支援決策。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node active"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-32-sli-slo-sla-與-error-budget"><span>上一站</span><strong>32. SLI、SLO、SLA 與 Error Budget</strong></a><div class="position-card current"><span>你在這裡</span><strong>33. Observability：從輸出重建系統內部狀態</strong></div><a class="position-card" href="#chapter-34-actionable-alerting-與-multi-window-burn-rate"><span>下一站</span><strong>34. Actionable Alerting 與 Multi-window Burn Rate</strong></a></div>

本章位於 **Part 5：SRE 與可靠性模型**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Observability</h3><div><span>白話定義</span><p>能否從系統輸出推斷內部狀態、因果與失敗位置的能力。</p></div><div class="example"><span>具體例子</span><p>Trace 顯示 request 在付款 dependency 耗掉 1.8 秒，而非只知道整體慢。</p></div><div class="relevance"><span>本章位置</span><p>Logs、metrics、traces、profiles 與變更事件需以共同 identifiers 串接。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section><section class="term-card"><h3>Provenance（來源鏈）</h3><div><span>白話定義</span><p>記錄 artifact、資料或答案由哪些輸入、工具、版本與操作者產生。</p></div><div class="example"><span>具體例子</span><p>Container image 可追到 commit、lockfile、builder identity 和簽章。</p></div><div class="relevance"><span>本章位置</span><p>AI 回答也需保存 retrieval sources、model version 與 tool trace 才能稽核。</p></div></section><section class="term-card"><h3>AI Agent</h3><div><span>白話定義</span><p>能接收目標、規劃步驟、呼叫工具、觀察結果並迭代的模型系統。</p></div><div class="example"><span>具體例子</span><p>Coding agent 搜尋 repository、修改檔案、跑測試，再依失敗訊息修正。</p></div><div class="relevance"><span>本章位置</span><p>Agent 增加速度與自治，也帶來 excessive agency、秘密外洩與不可預測操作等新風險。</p></div></section></div>

## 為什麼需要這一章？

監控告訴你已知條件是否異常；observability 更關心能否從輸出探索未知內部狀態。若 metrics 無 user context、logs 無 request ID、traces 無 deployment marker，值班者只能在多個工具間猜測。收集更多資料不等於更可觀測，關鍵是問題可回答與因果可串接。

### 真實 Use Case

Checkout p99 上升。Metric 顯示何時與哪些 region；trace 找到 80% 時間在 catalog；structured log 顯示只發生於新 schema；change event 對應十分鐘前 rollout。四種 evidence 合起來才形成可反證假設。

<div class="context-grid">
<section><span>問題壓力</span><p>監控告訴你已知條件是否異常；observability 更關心能否從輸出探索未知內部狀態。若 metrics 無 user context、logs 無 request ID、traces 無 deployment marker，值班者只能在多個工具間猜測。收集更多資料不等於更可觀測，關鍵是問題可回答與因果可串接。</p></section>
<section><span>交付能力</span><p>建立 signal model、共同 context、structured events 與變更關聯，讓 telemetry 真正支援決策。</p></section>
<section><span>真實場景</span><p>Checkout p99 上升。Metric 顯示何時與哪些 region；trace 找到 80% 時間在 catalog；structured log 顯示只發生於新 schema；change event 對應十分鐘前 rollout。四種 evidence 合起來才形成可反證假設。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>request / job / action
      ↓ common context: trace_id, service, version, region, tenant-safe cohort
metrics ─→ trend / rate / saturation
logs ───→ discrete event / values / decision
traces ─→ causal path / latency attribution
profiles → resource hot spots
changes ─→ deploy / config / feature / agent action
      ↓
query → hypothesis → experiment/action → observe</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Metrics 是聚合時間序列，適合 rate、latency distribution、error、saturation 和 SLO；logs 保存離散事件和決策 context；traces 連接跨服務 spans，顯示關鍵路徑；profiles 找 CPU/memory hot spots；change events 將系統行為和 deploy/config 連接。工具名稱可以不同，問題類型不變。

共同 identifiers 是組合關鍵：trace/request ID、service/version、region、operation、error code 和 safe cohort。Logs 應 structured，避免 parse 自由文字；metrics 控制 label cardinality，避免把 user ID 當 label；traces 使用 sampling，但 errors/high latency 可提高保留。Sensitive fields 需 redaction 和 access control。

Observability 從問題設計，不從「把所有資料收進來」開始。為每個 SLO 與 runbook 列出需要的 diagnosis questions；測試 dashboard 是否能從 symptom 到 owner/action。Telemetry pipeline 也有成本、延遲與 failure，需要 health 和 data quality。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>從 user journey/SLO 定義需要回答的診斷問題與共同 context。</p></div><div class="flow-card"><span>2</span><p>Metrics 用 distribution/rate；logs 結構化；traces 串因果；changes 明確標記。</p></div><div class="flow-card"><span>3</span><p>控制 cardinality、sampling、retention、redaction 和資料存取。</p></div><div class="flow-card"><span>4</span><p>Dashboard 從 symptom→slice→dependency→change→runbook 設計，而非圖表集合。</p></div><div class="flow-card"><span>5</span><p>以 incident/game day 驗證 telemetry 是否足夠、正確且及時。</p></div></div>

## Coding／實務例子

範例建立一致的 structured event，讓 log 與 trace/deployment 可關聯；敏感值不直接記錄。

```python
import json
from datetime import datetime, timezone

def event(trace_id: str, service: str, version: str,
          operation: str, outcome: str, latency_ms: int) -> str:
    return json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "service": service,
        "version": version,
        "operation": operation,
        "outcome": outcome,
        "latency_ms": latency_ms,
    }, sort_keys=True)

print(event("tr-7", "checkout", "a1b2c3", "reserve", "timeout", 803))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>固定 fields 便於 query、aggregation 和 agent tool 使用，不需脆弱 regex。</p></div><div class="flow-card"><span>2</span><p>Version 可將 error 與 rollout 關聯；trace ID 可跨 service 追蹤。</p></div><div class="flow-card"><span>3</span><p>不記 user/payment raw data，必要 cohort 應以 privacy-safe 方式產生。</p></div><div class="flow-card"><span>4</span><p>真實 schema 需版本、required/optional fields 和 ingestion failure monitoring。</p></div></div>

## Trade-offs 與 Failure Modes

- 每個 log 都加高基數 label，造成成本與查詢系統過載。
- 只保留平均 latency，長尾使用者傷害被隱藏。
- Telemetry schema 無 owner，服務各自發明欄位，跨系統無法關聯。
- 把 observability 當事後工具，發布時沒有 version/change marker。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI-SRE 的品質高度依賴 context。Agent observability 除傳統 signals，還需 model/version、prompt/instruction revision、retrieval sources、tool calls、arguments、policy decisions、token/cost、eval 和 human takeover。Agent 回答或動作必須可沿 trace 回到 evidence；若沒有 provenance，流暢 root-cause 敘事反而危險。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 用結構化 query tools 關聯 metrics、logs、traces、changes 和 topology。</li><li>請 agent 產生 hypothesis 時列 supporting、conflicting evidence 和下一個驗證。</li><li>對 agent workflow 建 span：model、retrieval、tool、approval、action 和 result。</li><li>用 AI 聚類高量 logs/incident traces，找未知 pattern，再由 owner 驗證。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Agent 只能讀獲批准 telemetry，查詢結果按使用者/tenant ACL 過濾。</li><li>保存 tool/evidence links、model/instruction version 和 action audit。</li><li>AI 不得以 summary 取代原始 telemetry；關鍵判斷可回看 query/result。</li><li>控制 prompt/log 中 secrets、PII、retention 和 cross-tenant data leakage。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Observability 的終點不是 data lake，而是縮短從 symptom 到安全行動的時間。專家會刪除無人使用、高成本 signals，並投資 context consistency。AI 能自然語言查詢與摘要，但若底層 telemetry 不一致、缺失或無權限模型，agent 只會更快產生錯誤故事。

</aside>

## 動手驗證

1. 選一個 SLO，寫五個 incident 問題，檢查現有 telemetry 能否回答。
2. 執行 structured event，加入 region/error_code 並設計 cardinality policy。
3. 畫出 symptom→metric→trace→log→change→runbook 的調查路徑。
4. 為 agent tool trace 定義 schema，加入 approval、policy、cost 和 result。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Metrics、logs、traces 的主要差異？</summary>

Metrics 看聚合趨勢/分布；logs 看離散事件與 context；traces 看跨元件因果和 latency path，三者互補。

</details>

<details class="qa"><summary>Q2. 為何平均 latency 不足？</summary>

少數極慢請求可能對使用者嚴重，但平均被大量快速請求稀釋；需 percentile/distribution 和 cohorts。

</details>

<details class="qa"><summary>Q3. High-cardinality label 有何問題？</summary>

時間序列數量爆炸，增加成本與查詢負擔；個別 ID 應留 logs/traces，而非 metrics labels。

</details>

<details class="qa"><summary>Q4. Change event 為何重要？</summary>

許多事故和 deploy/config 有關；版本與時間關聯能快速縮小假設並支援 rollback。

</details>

<details class="qa"><summary>Q5. Agent observability 為何要記 tool calls？</summary>

答案之外，外部行動決定安全與結果；需知道模型看了什麼、呼叫何工具、參數、policy 和結果。

</details>

<details class="qa"><summary>Q6. 更多 telemetry 是否總是更好？</summary>

不是。成本、隱私、噪音和資料品質會下降；應從可行動問題、SLO 和 retention 設計。

</details>

<details class="qa"><summary>Q7. 如何驗證 observability 真有用？</summary>

在 incident/game day 從 symptom 出發，能否在合理時間找到 owner、相關 change、故障範圍與安全 action。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Site Reliability Engineering — Effective Troubleshooting](https://sre.google/sre-book/effective-troubleshooting/)
- [Google Cloud — Agent observability](https://docs.cloud.google.com/stackdriver/docs/observability/agent-observability)
- [Google Cloud — How Google SRE is using agentic AI](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)

---

# 第 34 章　Actionable Alerting 與 Multi-window Burn Rate

<p class="chapter-question">什麼情況值得半夜叫醒人？如何同時抓到快速大事故與持續慢性傷害？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 5 · SRE 與可靠性模型</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

以 SLO burn 和可行動性設計 page/ticket/dashboard，建立多窗口、去重與 runbook contract。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node active"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-33-observability-從輸出重建系統內部狀態"><span>上一站</span><strong>33. Observability：從輸出重建系統內部狀態</strong></a><div class="position-card current"><span>你在這裡</span><strong>34. Actionable Alerting 與 Multi-window Burn Rate</strong></div><a class="position-card" href="#chapter-35-simplicity-change-management-與-error-budget-policy"><span>下一站</span><strong>35. Simplicity、Change Management 與 Error-budget Policy</strong></a></div>

本章位於 **Part 5：SRE 與可靠性模型**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Actionable alert</h3><div><span>白話定義</span><p>代表使用者影響或迫近風險，而且值班者能採取具體行動的通知。</p></div><div class="example"><span>具體例子</span><p>快速消耗 error budget 且 runbook 有 rollback 步驟時 page on-call。</p></div><div class="relevance"><span>本章位置</span><p>每個異常都 page 會造成 alert fatigue，使真正事故被忽略。</p></div></section><section class="term-card"><h3>Burn rate</h3><div><span>白話定義</span><p>error budget 被消耗的速度相對於剛好用完整個觀察窗口的速度。</p></div><div class="example"><span>具體例子</span><p>Burn rate 14 表示目前失敗率若持續，預算會比計畫快 14 倍耗盡。</p></div><div class="relevance"><span>本章位置</span><p>多窗口 burn-rate alert 同時兼顧快速事故與持續慢性問題。</p></div></section><section class="term-card"><h3>SLO（Service Level Objective）</h3><div><span>白話定義</span><p>某段時間內希望 SLI 達到的明確目標。</p></div><div class="example"><span>具體例子</span><p>28 天內 99.9% 有效 API request 成功。</p></div><div class="relevance"><span>本章位置</span><p>SLO 讓可靠性、告警和發布決策共享同一尺度。</p></div></section><section class="term-card"><h3>On-call</h3><div><span>白話定義</span><p>在指定時段負責接收 production 事件並協調恢復的輪值制度。</p></div><div class="example"><span>具體例子</span><p>Pager 在夜間通知 checkout SLO 快速燃燒，值班者依 runbook rollback。</p></div><div class="relevance"><span>本章位置</span><p>健康 on-call 需要可控事件量、訓練、支援和事故後改善時間。</p></div></section></div>

## 為什麼需要這一章？

每個異常都 page 會造成 alert fatigue；只設高 error threshold 又可能漏掉長時間小幅傷害。Alert 的目的是在需要人類即時決策、且等待會擴大使用者影響時通知。Machine metric 應先連到 SLO 或明確故障機制，再決定 page。

### 真實 Use Case

99.9% SLO 的服務突然 20% 錯誤，需數分鐘內 page；另一個版本每天 0.2% 額外錯誤，單分鐘不明顯但會耗盡月預算。短/長窗口 burn-rate 組合能同時處理。

<div class="context-grid">
<section><span>問題壓力</span><p>每個異常都 page 會造成 alert fatigue；只設高 error threshold 又可能漏掉長時間小幅傷害。Alert 的目的是在需要人類即時決策、且等待會擴大使用者影響時通知。Machine metric 應先連到 SLO 或明確故障機制，再決定 page。</p></section>
<section><span>交付能力</span><p>以 SLO burn 和可行動性設計 page/ticket/dashboard，建立多窗口、去重與 runbook contract。</p></section>
<section><span>真實場景</span><p>99.9% SLO 的服務突然 20% 錯誤，需數分鐘內 page；另一個版本每天 0.2% 額外錯誤，單分鐘不明顯但會耗盡月預算。短/長窗口 burn-rate 組合能同時處理。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>SLI events → error ratio → budget burn rate
                         ↓
         fast window + confirmation window
         slow window + confirmation window
                         ↓
dedupe / inhibit / route by owner
                         ↓
page: urgent + actionable
ticket: important, not immediate
dashboard/log: diagnostic only
                         ↓
runbook → action → observe → resolve</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Burn rate 是目前 bad-event rate 相對於剛好用完整個 SLO budget 的速度。對 99.9% 目標，允許 error rate 0.1%；目前 1.4% 就是 14 倍 burn。高倍短窗口偵測劇烈事故，較低倍長窗口偵測慢性問題；搭配第二窗口能降低瞬時尖峰噪音。

Page 條件通常是使用者影響/迫近 SLO 風險、需要即時人類 action、且有 owner/runbook。容量快滿但還有數天可處理，適合 ticket；CPU 短暫高但沒有 user impact，可做 diagnostic。每個 alert 要包含 what/where/when、SLO、scope、recent changes 和 first safe actions。

Alert lifecycle 包含 dedupe、group、inhibit 和 auto-resolve。Dependency outage 不應讓每個 downstream 各 page 一次；routing 要考慮 owner 和時區。每次 alert 後回顧 precision、action 和是否能改成 automation/更早 signal。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>從 SLO 或明確 imminent failure 定義 alert，而不是從每個 metric 開始。</p></div><div class="flow-card"><span>2</span><p>使用多窗口 burn rate 抓 fast/slow burn，回放歷史 incidents 校準。</p></div><div class="flow-card"><span>3</span><p>依 urgency/action 分 page、ticket、dashboard，指定 owner 和 runbook。</p></div><div class="flow-card"><span>4</span><p>Dedupe/group/inhibit 下游症狀，alert 內容附 scope、change 和第一步。</p></div><div class="flow-card"><span>5</span><p>回顧 false positive、miss、time-to-action 和 actionability，持續刪除噪音。</p></div></div>

## Coding／實務例子

範例計算 burn rate 並依嚴重度分類。真正 multi-window 會對短長窗口各算並要求同時成立。

```python
def burn_rate(error_rate: float, slo_target: float) -> float:
    allowed = 1.0 - slo_target
    return error_rate / allowed if allowed > 0 else float("inf")

def route(rate: float) -> str:
    if rate >= 14:
        return "page"
    if rate >= 2:
        return "ticket"
    return "dashboard"

rate = burn_rate(error_rate=0.014, slo_target=0.999)
print(rate, route(rate))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>1.4% error 對 99.9% SLO 是約 14 倍 burn，而非『只有 1.4%』。</p></div><div class="flow-card"><span>2</span><p>Routing thresholds 必須結合窗口；單點 rate 容易受低流量與尖峰影響。</p></div><div class="flow-card"><span>3</span><p>低流量服務可用 event count、synthetic 或較長窗口，避免除法噪音。</p></div><div class="flow-card"><span>4</span><p>Ticket 也要 owner/期限，否則慢性 burn 會累積成事故。</p></div></div>

## Trade-offs 與 Failure Modes

- Alert 直接綁 CPU/memory，不驗證是否有 user impact 或可行動。
- Threshold 太靈敏導致疲勞，值班者逐步忽略真正 page。
- 只抓 fast burn，長期小錯誤耗盡預算卻無人處理。
- Runbook 第一個步驟是『找 expert』，實際仍有 bus-factor bottleneck。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 可在 page 前後做 enrichment：關聯 recent changes、top errors、affected cohorts、dependencies 和歷史 incidents，並生成候選 runbook；但不應自己創造 page condition。核心觸發維持可重現的 SLO/policy，避免模型語意漂移半夜叫人。AI 可去重和摘要，但必須保留原始 alert 和 evidence。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 在 alert payload 加入 change、trace、owner、similar incident 和 first checks。</li><li>用 agent 聚類 alert storms，提出 root alert 與 downstream symptoms。</li><li>請 AI 分析歷史 pages 的 actionability、false positives 和 missing context。</li><li>讓 agent 依批准 runbook準備 remediation plan，操作前等待 policy/人類核准。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Page trigger 由 versioned deterministic SLO policy 控制，模型不能臨時改 threshold。</li><li>AI enrichment 有 timeout/fallback；失敗不能延遲原始緊急 page。</li><li>Summary 附 queries/evidence，禁止把猜測寫成已確認 root cause。</li><li>Auto-remediation 只限可逆、bounded、已 game-day 驗證 actions，完整 audit。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

好 alert 是人與系統的 API：輸入代表值得中斷的風險，輸出是值班者能採取的安全行動。專家會毫不猶豫刪除無 action alert，並把 diagnostic data 留在 dashboard。AI 應改善 context density，而不是增加更多語言噪音或把 probabilistic 判斷放在 pager critical path。

</aside>

## 動手驗證

1. 為 99.9% SLO 計算 0.1%、0.5%、1.4% error 的 burn rate。
2. 把十個 alerts 分成 page/ticket/dashboard，為每個寫 action 和 owner。
3. 回放一次 incident，測 multi-window threshold 多早觸發、是否誤報。
4. 設計 AI enrichment schema，限制處理時間並保留原始 evidence links。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. 什麼 alert 值得 page？</summary>

使用者正在受影響或 SLO 快速受威脅、需要即時人類決策、等待會擴大損害，且有可行動 owner/runbook。

</details>

<details class="qa"><summary>Q2. Burn rate 14 代表什麼？</summary>

以目前速度消耗 error budget，會比恰好用完整窗口快 14 倍；不是單純 14% 錯誤。

</details>

<details class="qa"><summary>Q3. 為何需要多窗口？</summary>

短窗口快速抓劇烈事故，長窗口抓持續傷害；確認窗口降低瞬間噪音和低流量誤報。

</details>

<details class="qa"><summary>Q4. CPU 高應直接 page 嗎？</summary>

只有它可靠預示迫近 user impact 且需要即時 action 時；否則作診斷或 ticket signal。

</details>

<details class="qa"><summary>Q5. AI 為何不應決定 page condition？</summary>

Pager 需要穩定可預測和可稽核；模型機率性與版本漂移可能增加誤報/漏報。AI 適合 enrichment。

</details>

<details class="qa"><summary>Q6. Alert review 應量什麼？</summary>

是否真有 action、false/true positive、miss、time-to-detect/action、重複與是否能 automation。

</details>

<details class="qa"><summary>Q7. Dependency outage 如何避免 page storm？</summary>

Topology-aware grouping/inhibition、root alert routing、下游症狀降級，並保留影響範圍供 incident 使用。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Practical Alerting](https://sre.google/sre-book/practical-alerting/)
- [Site Reliability Engineering — Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Site Reliability Engineering — Being On-Call](https://sre.google/sre-book/being-on-call/)
- [Google Cloud — How Google SRE is using agentic AI](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)

---

# 第 35 章　Simplicity、Change Management 與 Error-budget Policy

<p class="chapter-question">可靠性是否等於少改？如何讓系統保持簡單，又不停止必要創新？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 5 · SRE 與可靠性模型</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

用必要複雜度、可逆變更、error-budget 狀態和 cleanup discipline 管理 change。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node active"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-34-actionable-alerting-與-multi-window-burn-rate"><span>上一站</span><strong>34. Actionable Alerting 與 Multi-window Burn Rate</strong></a><div class="position-card current"><span>你在這裡</span><strong>35. Simplicity、Change Management 與 Error-budget Policy</strong></div><a class="position-card" href="#chapter-36-capacity-planning-performance-與-provisioning"><span>下一站</span><strong>36. Capacity Planning、Performance 與 Provisioning</strong></a></div>

本章位於 **Part 5：SRE 與可靠性模型**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Trade-off（取捨）</h3><div><span>白話定義</span><p>改善某個目標通常會增加另一種成本，工程決策需比較整體結果。</p></div><div class="example"><span>具體例子</span><p>更多測試提高信心，但也增加執行時間和維護成本。</p></div><div class="relevance"><span>本章位置</span><p>本書不提供永遠正確的工具選擇，而是提供判斷何時值得的模型。</p></div></section><section class="term-card"><h3>Coupling（耦合）</h3><div><span>白話定義</span><p>一個元件改變時，另一個元件也必須跟著改變的程度。</p></div><div class="example"><span>具體例子</span><p>前端直接依賴資料庫欄位名稱，使 schema rename 同時破壞 UI。</p></div><div class="relevance"><span>本章位置</span><p>Sustainable design 會讓必要耦合顯式化，並降低偶然耦合。</p></div></section><section class="term-card"><h3>Canary release</h3><div><span>白話定義</span><p>先把新版本暴露給少量流量，觀察結果後才擴大。</p></div><div class="example"><span>具體例子</span><p>先讓 1% request 使用新 checkout，再比較錯誤率和 latency。</p></div><div class="relevance"><span>本章位置</span><p>Canary 限制 blast radius；前提是有代表流量、健康指標與快速 rollback。</p></div></section><section class="term-card"><h3>Error budget</h3><div><span>白話定義</span><p>SLO 允許的不可靠量；100% 減去目標就是可消耗比例。</p></div><div class="example"><span>具體例子</span><p>99.9% 月 SLO 約允許 0.1% valid events 失敗。</p></div><div class="relevance"><span>本章位置</span><p>它把『穩定或快速』的爭論轉成可觀察的共同政策。</p></div></section></div>

## 為什麼需要這一章？

Change 是事故重要來源，但完全不變也會累積漏洞、依賴過時和無法滿足使用者。複雜度會增加狀態、交互和操作路徑，使每次 change 更難預測。可靠策略不是禁止發布，而是減少不必要複雜度、縮小 batch、限制 blast radius，並在預算惡化時調整風險。

### 真實 Use Case

服務同時保留三套 cache、六個 feature flags 和兩種 deployment path。每次 incident 都要先判斷組合狀態。刪除舊 cache 和 flags，可能比增加更聰明的自動偵錯更能降低 MTTR。

<div class="context-grid">
<section><span>問題壓力</span><p>Change 是事故重要來源，但完全不變也會累積漏洞、依賴過時和無法滿足使用者。複雜度會增加狀態、交互和操作路徑，使每次 change 更難預測。可靠策略不是禁止發布，而是減少不必要複雜度、縮小 batch、限制 blast radius，並在預算惡化時調整風險。</p></section>
<section><span>交付能力</span><p>用必要複雜度、可逆變更、error-budget 狀態和 cleanup discipline 管理 change。</p></section>
<section><span>真實場景</span><p>服務同時保留三套 cache、六個 feature flags 和兩種 deployment path。每次 incident 都要先判斷組合狀態。刪除舊 cache 和 flags，可能比增加更聰明的自動偵錯更能降低 MTTR。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>product need / reliability need
           ↓
is new complexity necessary?
  ├─ no → delete / simplify / reuse platform
  └─ yes
       ↓
small reversible change + canary + cleanup owner
       ↓
error budget state
  healthy → normal rollout
  fast burn → reduce risk / investigate
  exhausted → reliability work / exceptions only
       ↓
remove flag / old path / temporary compatibility</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Simplicity 不是行數最少，而是狀態、依賴、概念和操作路徑足夠少，使人能預測。抽象可降低重複，也可能增加 indirection；microservice 可隔離 ownership，也可能增加網路 failure。每項 complexity 要對應真 constraint，並有 owner。

Change management 以 small batch、review、test、immutable artifact、canary 和 rollback 降風險。高風險 change 可加 freeze window、specialist review 或 game day，但永久 freeze 會阻止安全更新。Error-budget policy 將風險狀態化：正常時持續發布，快速 burn 時縮小/暫停，耗盡時優先修可靠性，仍保留 security/emergency exception。

Cleanup 是 change 的一部分。Feature flag、雙寫、adapter 和額外 metrics 都應有 owner/expiry。若 roadmap 只計 launch，不計 cleanup，系統會只增不減。Operational review 應追 temporary mechanisms age 和 cognitive load。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>每個新 component/flag/path 說明對應 constraint、owner 和移除條件。</p></div><div class="flow-card"><span>2</span><p>以 small reversible changes、canary 和 same-artifact promotion 管理 rollout。</p></div><div class="flow-card"><span>3</span><p>建立 error-budget policy，定義 healthy/burning/exhausted 的 change 行為。</p></div><div class="flow-card"><span>4</span><p>Security/emergency exception 有具名 decision owner 和額外監控。</p></div><div class="flow-card"><span>5</span><p>將 cleanup 排入原始 project，量 flags、old paths 和 temporary code age。</p></div></div>

## Coding／實務例子

範例將 budget 狀態轉成 change policy。真實政策會使用多 SLO、burn windows 和變更風險級別。

```python
def change_policy(budget_remaining: float, fast_burn: bool, risk: str) -> str:
    if fast_burn:
        return "pause and investigate"
    if budget_remaining <= 0:
        return "reliability/security changes only"
    if budget_remaining < 0.25 and risk == "high":
        return "require executive exception and narrower canary"
    return "normal progressive delivery"

for remaining in (0.8, 0.2, 0.0):
    print(remaining, change_policy(remaining, False, "high"))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Policy 將抽象 reliability 狀態轉成可預期行為，減少臨時爭論。</p></div><div class="flow-card"><span>2</span><p>Fast burn 優先於剩餘比例，因正在發生的事故需要即時 response。</p></div><div class="flow-card"><span>3</span><p>Budget 低不代表禁止所有 change；可靠性和 security fix 仍可能降低風險。</p></div><div class="flow-card"><span>4</span><p>Exception 要縮小 canary、增加 review/monitoring，而非只取得簽名。</p></div></div>

## Trade-offs 與 Failure Modes

- Error budget 被當成懲罰產品團隊，造成隱藏錯誤或修改 SLI。
- Freeze 所有 change 讓漏洞和必要修復延遲，風險反而增加。
- Feature flags 沒有組合測試和 cleanup，產生無法理解的 runtime states。
- 為每個問題新增 service/tool，卻不計 on-call、dependency 和知識成本。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 會讓新增 code、flags、automation 和 services 更便宜，因而增加 accidental complexity 風險。Agent 每次提出新 abstraction 前應先搜尋 canonical solution、列出刪除/簡化選項和 long-term owner。Production AI component 還需要 deterministic fallback 和 kill switch，避免模型不可用時整個 critical path 失效。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 盤點 flags、duplicate libraries、dead paths 和 temporary compatibility age。</li><li>請 agent 在 design alternatives 中固定包含 delete/reuse/do-nothing。</li><li>用 AI 依 error-budget、diff 和 ownership 產生 change risk summary。</li><li>讓 agent 草擬 cleanup PR，依 telemetry 證明舊路徑無使用。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Agent 不得自行增加新的 framework/service/dependency 而無 owner review。</li><li>AI feature 有 fallback、kill switch、quota 和非 AI 路徑的最低服務。</li><li>Error-budget policy 和 exception 由具名 owners 管理，模型不能改 SLI 排除。</li><li>Cleanup 自動化先 dry-run、usage evidence、小批次和可逆 commit。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

專家最大的可靠性貢獻常是刪除：少一個狀態就少一組故障交互。Simplicity 不是反創新，而是讓每項複雜度持續證明價值。AI 時代需把『生成很容易』和『長期 ownership 很昂貴』同時放進決策，否則 code abundance 會變成理解 scarcity。

</aside>

## 動手驗證

1. 盤點服務所有 flags、deploy paths 和 caches，標 owner、age、usage、cleanup。
2. 執行 policy 範例，加入 low/medium risk 和 security exception。
3. 挑一個新 design，強制提出 delete/reuse/do-nothing 三種 alternative。
4. 讓 AI 找 dead code，再以 production telemetry 和 owners 驗證才移除。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Simplicity 是否等於最少 code？</summary>

不是。它關心概念、狀態、依賴和操作是否容易預測；有時多一層清楚 abstraction 反而降低整體複雜度。

</details>

<details class="qa"><summary>Q2. 為何完全停止 change 不可靠？</summary>

漏洞、依賴、使用者和環境仍會變；不更新也累積風險。應降低 change blast radius，而非追求靜止。

</details>

<details class="qa"><summary>Q3. Error-budget policy 有何價值？</summary>

讓可靠性狀態對發布行為有預先同意的影響，減少事故時的部門爭論。

</details>

<details class="qa"><summary>Q4. Budget 耗盡時是否不能部署任何東西？</summary>

通常仍允許降低風險的 reliability/security/emergency changes，並加強 review、canary 和監控。

</details>

<details class="qa"><summary>Q5. Feature flag 為何是暫時 complexity？</summary>

它同時保留多種 behavior；完成 rollout 後若不刪除，狀態組合和測試成本持續存在。

</details>

<details class="qa"><summary>Q6. AI 為何增加 accidental complexity？</summary>

新增 helper、service 和 abstraction 成本下降，但理解、on-call、migration 和 dependency 成本沒有等比下降。

</details>

<details class="qa"><summary>Q7. 何時新 complexity 是合理的？</summary>

它解決明確重要 constraint，收益超過建置/操作/退出成本，有 owner、evidence、fallback 和 cleanup。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Simplicity](https://sre.google/sre-book/simplicity/)
- [Site Reliability Engineering — Embracing Risk](https://sre.google/sre-book/embracing-risk/)
- [Software Engineering at Google — Continuous Delivery](https://abseil.io/resources/swe-book/html/ch24.html)
- [DORA 2025 — AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)

---

# 第 36 章　Capacity Planning、Performance 與 Provisioning

<p class="chapter-question">服務能撐多少流量？為什麼 CPU 還有空，使用者 latency 卻可能已經爆炸？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 5 · SRE 與可靠性模型</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

用 demand、per-unit capacity、utilization knee、headroom、failure reserve 和 provisioning lead time 建模。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node active"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-35-simplicity-change-management-與-error-budget-policy"><span>上一站</span><strong>35. Simplicity、Change Management 與 Error-budget Policy</strong></a><div class="position-card current"><span>你在這裡</span><strong>36. Capacity Planning、Performance 與 Provisioning</strong></div><a class="position-card" href="#chapter-37-load-balancing-從入口到-backend-選擇"><span>下一站</span><strong>37. Load Balancing：從入口到 Backend 選擇</strong></a></div>

本章位於 **Part 5：SRE 與可靠性模型**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Capacity</h3><div><span>白話定義</span><p>系統在指定品質下能承受的工作量與資源上限。</p></div><div class="example"><span>具體例子</span><p>服務在 p99 低於 300ms 時，每台最多穩定處理 800 RPS。</p></div><div class="relevance"><span>本章位置</span><p>Capacity planning 必須考慮成長、尖峰、故障冗餘和補資源所需 lead time。</p></div></section><section class="term-card"><h3>Constraint（限制條件）</h3><div><span>白話定義</span><p>解法必須遵守的硬邊界，例如延遲、相容性、預算、法規或權限。</p></div><div class="example"><span>具體例子</span><p>登入 API p99 必須低於 300ms，而且舊手機版本仍能使用。</p></div><div class="relevance"><span>本章位置</span><p>工程取捨必須先知道 constraint；AI agent 也需要把它寫進完成條件。</p></div></section><section class="term-card"><h3>Load shedding</h3><div><span>白話定義</span><p>過載時主動拒絕低優先或超過容量的工作，以保護仍可完成的請求。</p></div><div class="example"><span>具體例子</span><p>先拒絕報表刷新，保留付款流量。</p></div><div class="relevance"><span>本章位置</span><p>拒絕必須早、便宜且可觀測；在昂貴工作做完後才拒絕沒有保護效果。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section></div>

## 為什麼需要這一章？

Capacity 不只是機器數。Queueing 讓 utilization 接近上限時等待時間非線性上升；memory、connection、IO、dependency quota 可能先於 CPU 成為瓶頸。資源補充有 lead time，故障又會拿走部分 capacity，因此規劃要在流量到來前完成。

### 真實 Use Case

每台 checkout benchmark 可跑 1,000 RPS，但 p99 在 700 RPS 後快速上升。若用理論最大值規劃十台承受 10k RPS，真實 7k 就超過 SLO；再失去一區時會形成 retry storm。

<div class="context-grid">
<section><span>問題壓力</span><p>Capacity 不只是機器數。Queueing 讓 utilization 接近上限時等待時間非線性上升；memory、connection、IO、dependency quota 可能先於 CPU 成為瓶頸。資源補充有 lead time，故障又會拿走部分 capacity，因此規劃要在流量到來前完成。</p></section>
<section><span>交付能力</span><p>用 demand、per-unit capacity、utilization knee、headroom、failure reserve 和 provisioning lead time 建模。</p></section>
<section><span>真實場景</span><p>每台 checkout benchmark 可跑 1,000 RPS，但 p99 在 700 RPS 後快速上升。若用理論最大值規劃十台承受 10k RPS，真實 7k 就超過 SLO；再失去一區時會形成 retry storm。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>demand forecast (baseline / peak / growth / launch)
        ↓
workload model + SLO
        ↓
load test → utilization/latency curve → safe capacity per unit
        ↓
required units =
 demand / safe capacity
 + headroom
 + N+1 / zone failure reserve
        ↓
provisioning lead time / quota / cost
        ↓
online saturation signals → scale / shed / degrade</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

先定 workload 和 SLO，再量 capacity。不同 request 成本差異大，單一 RPS 不夠；可用 weighted work units、read/write mix、payload、cache hit 和 concurrency。Load test 找出 latency knee：在 saturation 前設定 safe utilization，而非使用理論最大 throughput。

Forecast 包含平日、尖峰、成長、launch 和季節，並保留 failure reserve。N+1 或失去一區後仍需服務 critical traffic。Provisioning 考慮 VM/database 建立時間、quota、供應不足和 warming；自動擴容不是即時魔法。長 lead-time 資源要提早訂。

Online control 使用 saturation、queue、latency 和 demand。接近上限時先限制低價值工作、降級 expensive feature、load shed，避免所有 request 一起變慢失敗。Capacity review 要和成本連結：過多 headroom 浪費，過少則用事故支付。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>定義 workload classes、SLO 和 weighted cost，不只看總 RPS。</p></div><div class="flow-card"><span>2</span><p>以 load test 畫 utilization/throughput/latency/error 曲線，找 safe knee。</p></div><div class="flow-card"><span>3</span><p>Forecast baseline/peak/growth/launch，加入 headroom 與 failure reserve。</p></div><div class="flow-card"><span>4</span><p>計入 provisioning lead time、quota、warm-up、regional supply 和 dependency limit。</p></div><div class="flow-card"><span>5</span><p>線上以 queue/saturation 觸發 scale、degrade、priority 和 load shedding。</p></div></div>

## Coding／實務例子

範例依 demand、安全單機容量、headroom 和可用區故障計算 replicas。安全容量應來自 SLO load test。

```python
from math import ceil

def required_replicas(
    peak_rps: int,
    safe_rps_per_replica: int,
    headroom: float = 0.30,
    zones: int = 3,
) -> int:
    demand_with_headroom = peak_rps * (1 + headroom)
    # 失去一區後，剩餘 zones-1 仍承擔全部 demand。
    surviving_fraction = (zones - 1) / zones
    normal_needed = demand_with_headroom / safe_rps_per_replica
    return ceil(normal_needed / surviving_fraction)

print(required_replicas(7000, 700))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>單機 700 是符合 p99 SLO 的 safe capacity，不是壓到 timeout 的最大值。</p></div><div class="flow-card"><span>2</span><p>30% headroom 吸收 forecast error、短峰與 scaling delay。</p></div><div class="flow-card"><span>3</span><p>三區失去一區後只剩三分之二 capacity，因此正常時需更多 replicas。</p></div><div class="flow-card"><span>4</span><p>真實 placement 要確保 replicas 均勻，且 database/dependency 同樣有 reserve。</p></div></div>

## Trade-offs 與 Failure Modes

- 使用平均 RPS 規劃，忽略 peak、burst 和昂貴 request mix。
- Autoscaler 只看 CPU，漏掉 queue、memory、connections 或 dependency quota。
- Scale-up 太慢，尚未生效前 retry 已造成 cascading failure。
- Load test 在 warm cache/簡單 payload，過度估計 production capacity。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI workload 增加 token、context、model tier、tool calls 和外部 API 等新成本。Capacity 需量 TTFT、tokens/sec、concurrency、GPU memory、agent step distribution 和 cost/request；長 agent loop 會持續占資源。AI 可做 forecast/anomaly 解釋，但 quota、admission、max steps 和 spend limits 必須 deterministic，防止 denial-of-wallet。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 分析 workload cohorts、launch plan 和歷史峰值，產生 forecast scenarios。</li><li>用 agent 比較 capacity curve，找 latency knee 和主要 resource bottleneck。</li><li>對 AI request 建 token/context/tool-step 分布與 model-tier routing 模型。</li><li>讓 agent 草擬 scaling/load-shedding plan，附成本、SLO 和 dependency constraints。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>每 request/tenant 設 token、steps、concurrency、time 和 spend quotas。</li><li>Autoscaling policy 不由 LLM 即時自由修改，使用 bounds、cooldown 和 audit。</li><li>AI forecast 必須顯示資料窗口、uncertainty 和 worst-case scenario。</li><li>容量不足時保留 critical deterministic path，能停用 expensive AI features。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Capacity 是可靠性、性能與經濟的交界。專家不以「CPU 低」證明充足，而看使用者 SLO 下的 limiting resource 和失敗情境。AI 系統尤其容易被平均 tokens 掩蓋長尾；先限制單請求工作量，再談無限擴容，通常更可靠也更省成本。

</aside>

## 動手驗證

1. 執行 replicas 計算，改 zones、headroom 和 safe capacity 比較成本。
2. 對一個 service 畫 throughput vs p99 曲線，標出 safe knee。
3. 建立容量表：resource、current、safe max、lead time、owner、shed action。
4. 為 agent 定義 max tokens、steps、tools、concurrency 和降級路徑。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. 為何 capacity 應以 SLO 下的值計算？</summary>

理論最大 throughput 可能伴隨不可接受 latency/error；使用者品質已失敗就不算可用 capacity。

</details>

<details class="qa"><summary>Q2. Headroom 解決什麼？</summary>

Forecast 誤差、短峰、scale delay、單機差異和小故障；仍需依成本與風險校準。

</details>

<details class="qa"><summary>Q3. Autoscaling 為何不能取代 planning？</summary>

資源有偵測、啟動、warm-up、quota 和供應 lead time；突然大峰可能在擴容前已過載。

</details>

<details class="qa"><summary>Q4. CPU 低但 latency 高可能有哪些原因？</summary>

IO、lock、queue、connection pool、dependency、single-thread bottleneck、GC 或 rate limit，需看完整 saturation。

</details>

<details class="qa"><summary>Q5. Load shedding 與 scaling 如何配合？</summary>

Scaling增加未來 capacity；shedding 立即限制當前工作，防止等待/重試擴散，兩者時間尺度不同。

</details>

<details class="qa"><summary>Q6. AI capacity 有哪些特有維度？</summary>

Context/token、model tier、TTFT、tokens/sec、GPU memory、tool calls、steps、cost 和 provider quota。

</details>

<details class="qa"><summary>Q7. Denial-of-wallet 如何防止？</summary>

Per-request/tenant budget、rate/concurrency、max steps、cheaper fallback、anomaly alert 和 hard spend limit。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Introduction](https://sre.google/sre-book/introduction/)
- [Site Reliability Engineering — Handling Overload](https://sre.google/sre-book/handling-overload/)
- [Software Engineering at Google — Compute as a Service](https://abseil.io/resources/swe-book/html/ch25.html)
- [Google Cloud — Agent observability](https://docs.cloud.google.com/stackdriver/docs/observability/agent-observability)

---
