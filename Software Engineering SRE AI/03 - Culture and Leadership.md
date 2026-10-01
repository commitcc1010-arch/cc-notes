---
title: "團隊、文化與領導"
part: 2
as_of: 2026-09-30
---

# Part 2　團隊、文化與領導

軟體是社會技術系統。知識流動、決策權、心理安全與衡量方式，會直接改變 codebase 和 production 的品質。

# 第 8 章　HRT、Ownership 與真正的團隊合作

<p class="chapter-question">多人一起寫 code 為什麼不等於團隊？什麼條件能讓不同專長在高壓變更中仍然合作？</p>

<div class="chapter-meta"><span>難度：入門</span><span>Part 2 · 團隊、文化與領導</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

把 humility、respect、trust 轉成可觀察的 review、ownership、求助和決策行為。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node active"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-07-trade-offs-costs-與-architecture-decision-records"><span>上一站</span><strong>07. Trade-offs、Costs 與 Architecture Decision Records</strong></a><div class="position-card current"><span>你在這裡</span><strong>08. HRT、Ownership 與真正的團隊合作</strong></div><a class="position-card" href="#chapter-09-psychological-safety-讓壞消息提早出現"><span>下一站</span><strong>09. Psychological Safety：讓壞消息提早出現</strong></a></div>

本章位於 **Part 2：團隊、文化與領導**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Ownership</h3><div><span>白話定義</span><p>對元件品質、決策、值班與改善負最終責任的明確主體。</p></div><div class="example"><span>具體例子</span><p>平台組維護 deployment API；服務組仍對自己設定錯誤造成的事故負責。</p></div><div class="relevance"><span>本章位置</span><p>AI 可以執行工作但不能承擔組織責任，因此 ownership 不可寫成『模型』。</p></div></section><section class="term-card"><h3>Psychological safety</h3><div><span>白話定義</span><p>成員能提出疑問、承認錯誤和挑戰決策，而不必害怕羞辱或不合理懲罰。</p></div><div class="example"><span>具體例子</span><p>新人可以說『我不懂這個 deploy』，團隊因此在事故前發現 runbook 缺口。</p></div><div class="relevance"><span>本章位置</span><p>安全文化能更早暴露弱信號，是可靠性控制的一部分。</p></div></section><section class="term-card"><h3>Bus factor</h3><div><span>白話定義</span><p>需要多少關鍵成員同時離開，知識缺口才會讓專案無法維持。</p></div><div class="example"><span>具體例子</span><p>只有一人知道憑證輪替流程，休假時到期便造成 outage。</p></div><div class="relevance"><span>本章位置</span><p>文件、輪調、pairing 與自動化可以提高 bus factor。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section></div>

## 為什麼需要這一章？

複雜系統不可能由一人理解所有細節；可靠結果來自成員能暴露不確定、交換局部知識並共同承擔結果。若文化獎勵英雄救火、隱藏錯誤和知識壟斷，工具再成熟也只能更快放大單點決策。HRT 不是要求每個人永遠客氣，而是讓技術爭論不必依靠羞辱、地位或個人防衛來取得結論。

### 真實 Use Case

付款服務在凌晨失敗。懂資料庫的人、懂 deploy 的人和 product owner 各自掌握一部分事實。若大家爭論誰造成事故，恢復會延後；若角色清楚、能安全說「我不知道」，團隊可以先 rollback，再共同重建因果。

<div class="context-grid">
<section><span>問題壓力</span><p>複雜系統不可能由一人理解所有細節；可靠結果來自成員能暴露不確定、交換局部知識並共同承擔結果。若文化獎勵英雄救火、隱藏錯誤和知識壟斷，工具再成熟也只能更快放大單點決策。HRT 不是要求每個人永遠客氣，而是讓技術爭論不必依靠羞辱、地位或個人防衛來取得結論。</p></section>
<section><span>交付能力</span><p>把 humility、respect、trust 轉成可觀察的 review、ownership、求助和決策行為。</p></section>
<section><span>真實場景</span><p>付款服務在凌晨失敗。懂資料庫的人、懂 deploy 的人和 product owner 各自掌握一部分事實。若大家爭論誰造成事故，恢復會延後；若角色清楚、能安全說「我不知道」，團隊可以先 rollback，再共同重建因果。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>共同目標 / 使用者結果
          ↓
   明確 ownership
   ├─ component owner
   ├─ decision owner
   ├─ incident roles
   └─ escalation path
          ↓
Humble: 我的模型可能不完整
Respect: 批評 idea，不貶低人
Trust: 給能力相稱的自治與支援
          ↓
早期暴露風險 → 快速 feedback → 共同修正</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Humility 是承認自己看見的是局部，不是降低標準。它表現在設計文件列出 uncertainty、reviewer 願意被反證、incident commander 主動詢問反方 signal。Respect 是把人與產出分開：可以明確說某變更不安全，但要指出 constraint、evidence 和可改善路徑。Trust 則是讓成員在清楚邊界內做決策，同時提供求助與 rollback。

Ownership 不是「出了事找誰怪罪」，而是誰維持 contract、處理 feedback、安排改善並決定風險。單一元件可以有 primary team，但 production path 通常跨多個 owners；因此 escalation 和 handoff 必須顯式。若所有問題都回到最資深英雄，名義 ownership 並沒有真正分散。

健康團隊會把 cooperation 寫進流程：小型 review 讓意見容易交換、design review 先對齊 constraints、on-call pairing 傳遞操作知識、postmortem 將脆弱點轉成共同資產。文化不是牆上的價值觀，而是資訊遇到壞消息時實際如何流動。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>先對齊共同使用者結果，避免每個職能只優化自己的局部 metric。</p></div><div class="flow-card"><span>2</span><p>為 component、decision、incident 與 escalation 分別指定 owner，避免責任模糊。</p></div><div class="flow-card"><span>3</span><p>在 review 中要求 claim 附 evidence，也允許作者清楚標記 uncertainty。</p></div><div class="flow-card"><span>4</span><p>以 pairing、rotation 和文件降低英雄依賴，使求助不必跨越地位障礙。</p></div><div class="flow-card"><span>5</span><p>事故後檢查系統與 incentives，避免把合理行動簡化成個人失誤。</p></div></div>

## Coding／實務例子

以下用簡單 ownership registry 表示 owner 不是名字註解，而是能被工具驗證的 routing contract。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Ownership:
    team: str
    escalation: str
    runbook: str

REGISTRY = {
    "checkout-api": Ownership("payments", "#payments-oncall", "runbooks/checkout.md"),
    "deploy-platform": Ownership("platform", "#platform-oncall", "runbooks/deploy.md"),
}

def route(component: str) -> Ownership:
    try:
        return REGISTRY[component]
    except KeyError:
        raise ValueError(f"unowned component: {component}")
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Registry 同時提供負責團隊、緊急 escalation 和操作知識入口。</p></div><div class="flow-card"><span>2</span><p>未知 component 立即失敗，讓 ownership 缺口在 CI 或 inventory job 中被看見。</p></div><div class="flow-card"><span>3</span><p>Primary owner 不表示所有修改只能由該團隊完成，而是由它維持 contract 和 review。</p></div><div class="flow-card"><span>4</span><p>真實系統還應加入備援 owner、時區、資料等級與最後驗證日期。</p></div></div>

## Trade-offs 與 Failure Modes

- 過度強調 ownership 可能形成領地意識，使其他人不敢改善或 owner 成為 review bottleneck。
- 只寫團隊名稱卻沒有 on-call、runbook 和 capacity，等同把責任貼標籤。
- 表面和諧若禁止尖銳技術反對，會讓風險延後到 production。
- 把 incident 個人化會鼓勵隱藏資訊，降低下一次早期 signal 的品質。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 讓個人能跨越更多技術領域，但不能因此假設 ownership 不再需要。Agent 可能修改它不理解的下游 contract，也可能讓團隊誤以為「任何人都能維護任何 code」。更成熟的方式是讓 ownership metadata、architecture boundaries 和 escalation path 對 agent 可讀，並要求跨邊界變更自動找到對應 reviewer。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 依 ownership registry 為 diff 找 reviewers 和可能受影響團隊。</li><li>用 agent 將 incident timeline 或 review thread 摘要成共享事實，減少資訊不對稱。</li><li>請 AI 指出設計中的 uncertainty、未回答問題和需要其他 domain owner 的位置。</li><li>以 AI 協助新成員閱讀 runbook、模擬事故和準備向 expert 提問。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Agent 不得成為 owner；每個變更、服務和 production action 都要有具名人類團隊。</li><li>跨 ownership boundary 的修改需要對方 reviewer 或明確 delegated policy。</li><li>AI 摘要不能刪除 dissent、uncertainty 和原始證據連結。</li><li>績效制度不能因使用 AI 較少或較常求助而懲罰成員，否則壞消息會被隱藏。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

資深團隊既不把 ownership 做成封閉領地，也不接受「大家都負責」的空話。好的邊界允許他人貢獻，但清楚誰維持標準、誰能接受風險、誰在事故時回應。AI 可以降低知識入口成本，卻無法替代長期照顧元件、承擔取捨和建立信任的社會責任。

</aside>

## 動手驗證

1. 列出一條 production request path，為每個 component 補上 owner、on-call 和 runbook。
2. 執行範例，加入一個沒有 owner 的 dependency，設計 CI 如何阻止發布。
3. 找一段最近的 review，將人身或偏好式評論改寫成 constraint、evidence 和建議。
4. 請 AI 摘要一次技術爭論，再人工檢查它是否遺漏少數意見與 uncertainty。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. HRT 是否等於避免衝突？</summary>

不是。HRT 讓團隊可以直接而有證據地挑戰 idea，同時不羞辱人；真正的技術分歧應更早被提出，而非被禮貌掩蓋。

</details>

<details class="qa"><summary>Q2. Ownership 與 blame 最大差異是什麼？</summary>

Ownership 指維持 contract、回應 feedback 和安排改善的責任；blame 把系統結果簡化成個人道德問題，通常無法降低再發風險。

</details>

<details class="qa"><summary>Q3. 為什麼『大家都負責』通常不可靠？</summary>

沒有清楚 primary owner 時，維護、值班和跨團隊協調容易被假設成別人會處理；共享參與仍需要明確 accountable party。

</details>

<details class="qa"><summary>Q4. Trust 如何避免變成無限制授權？</summary>

信任應搭配能力、風險邊界、observability 和 rollback。給予範圍內自治並保留支援與升級，不等於取消 review 或 control。

</details>

<details class="qa"><summary>Q5. AI 為何不能被列為 service owner？</summary>

模型不承擔法律、商業和倫理責任，也不會自行維持長期 context、值班與風險接受；工具操作必須回到具名人類 ownership。

</details>

<details class="qa"><summary>Q6. 如何知道團隊過度依賴英雄？</summary>

觀察只有一人能 deploy、事故總找同一人、文件和 rotation 缺失、休假時變更停止，以及重要決策只存在私人記憶。

</details>

<details class="qa"><summary>Q7. 本章對可靠性最直接的影響是什麼？</summary>

讓壞消息、未知與跨 domain 風險能早期流動；越早暴露，修復成本和 production blast radius 通常越低。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — How to Work Well on Teams](https://abseil.io/resources/swe-book/html/ch02.html)
- [Software Engineering at Google — Knowledge Sharing](https://abseil.io/resources/swe-book/html/ch03.html)
- [Site Reliability Engineering — Managing Incidents](https://sre.google/sre-book/managing-incidents/)
- [DORA 2025 — AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)

---

# 第 9 章　Psychological Safety：讓壞消息提早出現

<p class="chapter-question">心理安全為什麼是工程控制，而不只是讓工作氣氛舒服？</p>

<div class="chapter-meta"><span>難度：初階</span><span>Part 2 · 團隊、文化與領導</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

建立能安全提出疑問、承認錯誤和升級風險的機制，同時維持高技術標準。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node active"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-08-hrt-ownership-與真正的團隊合作"><span>上一站</span><strong>08. HRT、Ownership 與真正的團隊合作</strong></a><div class="position-card current"><span>你在這裡</span><strong>09. Psychological Safety：讓壞消息提早出現</strong></div><a class="position-card" href="#chapter-10-knowledge-sharing-readability-與-bus-factor"><span>下一站</span><strong>10. Knowledge Sharing、Readability 與 Bus Factor</strong></a></div>

本章位於 **Part 2：團隊、文化與領導**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Psychological safety</h3><div><span>白話定義</span><p>成員能提出疑問、承認錯誤和挑戰決策，而不必害怕羞辱或不合理懲罰。</p></div><div class="example"><span>具體例子</span><p>新人可以說『我不懂這個 deploy』，團隊因此在事故前發現 runbook 缺口。</p></div><div class="relevance"><span>本章位置</span><p>安全文化能更早暴露弱信號，是可靠性控制的一部分。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section><section class="term-card"><h3>Ownership</h3><div><span>白話定義</span><p>對元件品質、決策、值班與改善負最終責任的明確主體。</p></div><div class="example"><span>具體例子</span><p>平台組維護 deployment API；服務組仍對自己設定錯誤造成的事故負責。</p></div><div class="relevance"><span>本章位置</span><p>AI 可以執行工作但不能承擔組織責任，因此 ownership 不可寫成『模型』。</p></div></section><section class="term-card"><h3>Incident command</h3><div><span>白話定義</span><p>事故中明確分離決策、操作、溝通與記錄角色的協作模型。</p></div><div class="example"><span>具體例子</span><p>Incident Commander 排優先順序；Operations Lead 執行；Comms 更新利害關係人。</p></div><div class="relevance"><span>本章位置</span><p>角色分工降低認知負荷，也避免所有人同時修改 production。</p></div></section></div>

## 為什麼需要這一章？

複雜系統的早期危險通常先以弱信號出現：新人看不懂 deploy、值班者覺得 alert 不可信、工程師擔心 migration 無法 rollback。若說出疑慮會被嘲笑或影響績效，這些資訊就會留在個人腦中，直到 production 用更昂貴的方式證明它們。

### 真實 Use Case

發布會議中，一位工程師發現 rollback script 從未在新 schema 上測過。若團隊把「別阻礙進度」當文化，他可能沉默；若 pause-and-check 被視為專業行為，十分鐘 game day 可能避免數小時 outage。

<div class="context-grid">
<section><span>問題壓力</span><p>複雜系統的早期危險通常先以弱信號出現：新人看不懂 deploy、值班者覺得 alert 不可信、工程師擔心 migration 無法 rollback。若說出疑慮會被嘲笑或影響績效，這些資訊就會留在個人腦中，直到 production 用更昂貴的方式證明它們。</p></section>
<section><span>交付能力</span><p>建立能安全提出疑問、承認錯誤和升級風險的機制，同時維持高技術標準。</p></section>
<section><span>真實場景</span><p>發布會議中，一位工程師發現 rollback script 從未在新 schema 上測過。若團隊把「別阻礙進度」當文化，他可能沉默；若 pause-and-check 被視為專業行為，十分鐘 game day 可能避免數小時 outage。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>弱信號
  ├─「我不懂」
  ├─「這裡沒有證據」
  ├─「我操作錯了」
  └─「這個 SLO 可能不代表使用者」
          ↓
安全通道 + 無報復升級 + 明確回應
          ↓
question / review / pause / experiment
          ↓
更早、更便宜的 failure discovery

心理安全 + 高標準 ≠ 降低要求</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

心理安全的核心是 interpersonal risk：成員是否能在不知道答案、不同意權威或承認失誤時仍被公平對待。它與績效標準是兩條軸；團隊可以同時要求嚴格 evidence，又不因提問者職級、口音或過去錯誤忽略訊息。

安全要有結構支持。Design review 可固定詢問反方和 rollback；incident 開場明確說明先恢復、後分析；leader 公開修正自己的判斷；升級管道不必經過被挑戰者本人。若只說「歡迎提問」，但提出問題後沒有回應，文化不會改變。

另一方面，心理安全不是所有 idea 都同樣正確，也不是免除 accountability。對高風險操作仍要追蹤誰做了什麼、當時有哪些 evidence、policy 是否合理。Blameless 的意思是理解行動所在系統，不是刪除事實或後果。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>Leader 主動說出自己的 uncertainty，示範模型可以被修正。</p></div><div class="flow-card"><span>2</span><p>Review 和 launch checklist 固定詢問 dissent、rollback 與 missing evidence。</p></div><div class="flow-card"><span>3</span><p>事故中分離恢復與責任調查，保護即時資訊流。</p></div><div class="flow-card"><span>4</span><p>對提出風險的人回報處理結果，讓升級行為被正向強化。</p></div><div class="flow-card"><span>5</span><p>定期以匿名 survey、retrospective 和行為例子檢查安全感，而非只靠口號。</p></div></div>

## Coding／實務例子

這個簡單的 preflight 函式把『可以按暫停』做成流程。任何一項未知都回傳阻擋原因，而不是讓職級決定是否忽略。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class LaunchEvidence:
    rollback_tested: bool
    owner_oncall: bool
    slo_dashboard_ready: bool
    dissent_resolved: bool

def launch_decision(e: LaunchEvidence) -> tuple[bool, list[str]]:
    missing = [
        name for name, ready in vars(e).items()
        if not ready
    ]
    return (not missing, missing)

ready, reasons = launch_decision(
    LaunchEvidence(True, True, False, False)
)
print("GO" if ready else f"PAUSE: {reasons}")
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Checklist 把提出疑慮從個人勇氣轉成正常工作流程。</p></div><div class="flow-card"><span>2</span><p><code>dissent_resolved</code> 不表示所有人同意，而是反對理由已被 owner 回應並記錄。</p></div><div class="flow-card"><span>3</span><p>Missing dashboard 是可修復的 evidence gap，不是某人的能力評價。</p></div><div class="flow-card"><span>4</span><p>高風險 launch 的 decision owner 仍需接受剩餘風險並留下理由。</p></div></div>

## Trade-offs 與 Failure Modes

- 匿名管道有助揭露問題，但若所有溝通都匿名，團隊難以共同解決具體細節。
- 把任何不舒服都稱為不安全，可能阻止必要且尊重的績效或風險討論。
- Leader 說歡迎反對，卻獎勵永不延誤發布的人，實際 incentives 仍會壓制信號。
- 過度 checklist 化可能讓人機械勾選，而不理解真正風險。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 讓成員能私下詢問「不敢問的問題」，降低學習門檻；但也可能讓人隱藏不理解、直接採用模型答案，或因監控 prompt 而不敢探索。組織需要清楚說明 AI 使用資料如何保留、是否用於績效，以及何時必須向人升級。安全使用 AI 包含能公開說「模型建議但我沒有驗證」。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>提供私密的 AI 教學助手，幫助新人形成更精確的人類提問。</li><li>讓 AI 在 design review 產生 red-team questions，確保少數觀點被討論。</li><li>用 AI 匿名聚類 retrospective 主題，但保留原意與可選擇退出。</li><li>讓 incident assistant 主動標記 conflicting evidence，而非只生成單一敘事。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>不得用 prompt 數、求助內容或 AI 錯誤作為未告知的個人績效監控。</li><li>敏感人事、健康和客戶資料不得進入未批准模型。</li><li>AI 回答要明確標示 uncertainty 和來源，允許成員不接受其權威。</li><li>任何 safety concern 都要有人類 escalation path，不能被 bot 自動關閉。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

心理安全最可靠的測試不是 survey 分數，而是壞消息到來時 leader 怎麼做：提出風險的人是否被感謝、發布是否真的能 pause、事故資訊是否被懲罰性使用。AI 可以提供另一個提問入口，但如果組織權力和 incentives 沒有改變，它只會成為更安靜的繞道。

</aside>

## 動手驗證

1. 回想最近一次有人挑戰發布，記錄 leader、流程和績效信號如何回應。
2. 執行範例，為不同風險等級設計可接受的 missing evidence。
3. 在下一份 design doc 加入『最強反對理由』與『哪些信號會讓我們停下』。
4. 撰寫 AI 使用透明政策：哪些 prompt 被保留、誰能看、不能用於哪些決策。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. 心理安全如何直接改善可靠性？</summary>

它讓未知、錯誤和弱信號在 production 事故前被提出，縮短發現時間；資訊若因人際風險被壓制，技術控制也得不到正確輸入。

</details>

<details class="qa"><summary>Q2. 心理安全是否與高標準衝突？</summary>

不衝突。可以嚴格要求 evidence、測試和改進，同時不羞辱提問或犯錯的人；安全是討論方式，高標準是結果要求。

</details>

<details class="qa"><summary>Q3. Blameless 是否表示不追蹤誰做了操作？</summary>

不是。必須重建行動、權限和決策脈絡；blameless 是避免用個人缺陷取代系統分析，仍保留 accountability 與必要後果。

</details>

<details class="qa"><summary>Q4. 為什麼只說『歡迎提問』不夠？</summary>

成員會根據過往回應和 incentives 判斷風險。需要固定流程、leader 示範、無報復升級和對問題的實際處理結果。

</details>

<details class="qa"><summary>Q5. AI 如何降低又可能傷害心理安全？</summary>

它提供低壓學習入口；但 prompt 監控、模型權威和私下採用未驗證答案可能讓真實未知更難被團隊看見。

</details>

<details class="qa"><summary>Q6. `dissent_resolved` 應如何解讀？</summary>

不是要求一致同意，而是反對內容被準確記錄、由 decision owner 回應，剩餘風險與決策理由可被追蹤。

</details>

<details class="qa"><summary>Q7. 如何辨認表面安全、實際不安全的團隊？</summary>

會議沒有衝突但事故總是意外、發布從不 pause、同一批人發言、壞消息私下流傳，以及提出風險者被標記成不合作。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — How to Work Well on Teams](https://abseil.io/resources/swe-book/html/ch02.html)
- [Software Engineering at Google — Knowledge Sharing](https://abseil.io/resources/swe-book/html/ch03.html)
- [Site Reliability Engineering — Postmortem Culture](https://sre.google/sre-book/postmortem-culture/)
- [NIST — Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)

---

# 第 10 章　Knowledge Sharing、Readability 與 Bus Factor

<p class="chapter-question">如何把『問那位資深工程師』變成任何人與 agent 都能走的可靠知識路徑？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 2 · 團隊、文化與領導</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

設計知識從發現、驗證、發布、搜尋到淘汰的生命週期，而不是堆積更多文件。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node active"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-09-psychological-safety-讓壞消息提早出現"><span>上一站</span><strong>09. Psychological Safety：讓壞消息提早出現</strong></a><div class="position-card current"><span>你在這裡</span><strong>10. Knowledge Sharing、Readability 與 Bus Factor</strong></div><a class="position-card" href="#chapter-11-engineering-for-equity-為不同使用者設計"><span>下一站</span><strong>11. Engineering for Equity：為不同使用者設計</strong></a></div>

本章位於 **Part 2：團隊、文化與領導**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Bus factor</h3><div><span>白話定義</span><p>需要多少關鍵成員同時離開，知識缺口才會讓專案無法維持。</p></div><div class="example"><span>具體例子</span><p>只有一人知道憑證輪替流程，休假時到期便造成 outage。</p></div><div class="relevance"><span>本章位置</span><p>文件、輪調、pairing 與自動化可以提高 bus factor。</p></div></section><section class="term-card"><h3>Design document</h3><div><span>白話定義</span><p>在昂貴實作前對齊問題、需求、架構、資料流、失敗模式與 rollout 的文件。</p></div><div class="example"><span>具體例子</span><p>支付服務改資料模型前，先描述雙寫、回填、驗證與 rollback。</p></div><div class="relevance"><span>本章位置</span><p>AI 可以協助檢查缺項，但設計責任與風險接受仍由人承擔。</p></div></section><section class="term-card"><h3>Context engineering</h3><div><span>白話定義</span><p>設計模型在做決策時能看見哪些規格、程式碼、文件、工具結果與限制。</p></div><div class="example"><span>具體例子</span><p>只說『修 bug』通常不足；提供重現步驟、相關 module、測試命令和完成條件更可靠。</p></div><div class="relevance"><span>本章位置</span><p>AI 時代的文件、repository 結構與工具輸出同時服務人類與 agent。</p></div></section><section class="term-card"><h3>Provenance（來源鏈）</h3><div><span>白話定義</span><p>記錄 artifact、資料或答案由哪些輸入、工具、版本與操作者產生。</p></div><div class="example"><span>具體例子</span><p>Container image 可追到 commit、lockfile、builder identity 和簽章。</p></div><div class="relevance"><span>本章位置</span><p>AI 回答也需保存 retrieval sources、model version 與 tool trace 才能稽核。</p></div></section></div>

## 為什麼需要這一章？

知識若只存在個人腦中，團隊的 capacity 和可靠性就被最稀缺的人限制；若全部寫成文件卻無法搜尋、沒有 owner 或過時，讀者仍會回去問人。知識分享真正要管理的是可信來源、發現路徑、更新責任和實作 feedback。

### 真實 Use Case

新值班者遇到 queue lag，搜尋得到三份互相衝突的 runbook；最舊一份排名第一，指示已不存在的按鈕。文件很多，但知識系統失敗。正確入口應標記 canonical、owner、最後驗證與 service version。

<div class="context-grid">
<section><span>問題壓力</span><p>知識若只存在個人腦中，團隊的 capacity 和可靠性就被最稀缺的人限制；若全部寫成文件卻無法搜尋、沒有 owner 或過時，讀者仍會回去問人。知識分享真正要管理的是可信來源、發現路徑、更新責任和實作 feedback。</p></section>
<section><span>交付能力</span><p>設計知識從發現、驗證、發布、搜尋到淘汰的生命週期，而不是堆積更多文件。</p></section>
<section><span>真實場景</span><p>新值班者遇到 queue lag，搜尋得到三份互相衝突的 runbook；最舊一份排名第一，指示已不存在的按鈕。文件很多，但知識系統失敗。正確入口應標記 canonical、owner、最後驗證與 service version。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Tacit knowledge / incident / design
            ↓
        capture draft
            ↓
expert review + runnable verification
            ↓
canonical home + owner + version + metadata
            ↓
search / onboarding / agent retrieval
            ↓
usage feedback + freshness check
            ↓
update / supersede / archive</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

知識有 tacit 和 explicit 兩種。Tacit knowledge 包含判斷、例外和肌肉記憶，不可能一次全部文件化；pairing、rotation、office hours 和 incident shadowing 能傳遞這部分。Explicit knowledge 則應有 canonical home、結構、owner 和更新觸發，例如 API contract、runbook 與 ADR。

Readability 不只是語法漂亮，而是讓 codebase 的慣例能被一致教導與 review。文件解釋 why 和入口，code/test/schema 則保存可執行 truth。最健康的知識路徑通常是薄入口加深層來源：一頁 service map 指到 design、dashboard、runbook 和 source，而不是複製所有內容。

文件也需要 lifecycle。建立時記錄 audience、owner、last verified、scope 和 supersedes；使用時提供 feedback；系統或 API 變更時由 CI 提醒相關文件；無法維護的內容應 archive。搜尋排名必須偏好 canonical 和新鮮來源，否則更多文件會降低答案品質。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>先畫 service knowledge map，連到 source、owner、API、dashboard、runbook 和 ADR。</p></div><div class="flow-card"><span>2</span><p>對操作文件加入可執行命令或 smoke check，讓內容能被定期驗證。</p></div><div class="flow-card"><span>3</span><p>以 pairing、rotation 和 teaching 補充無法完全文字化的 tacit judgment。</p></div><div class="flow-card"><span>4</span><p>為文件設定 owner、last verified、version 和 superseded-by metadata。</p></div><div class="flow-card"><span>5</span><p>追蹤搜尋失敗、重複提問和 incident confusion，作為知識產品的 feedback。</p></div></div>

## Coding／實務例子

用 metadata 驗證文件新鮮度。真實 CI 可以在服務版本改變或期限到期時提醒 owner，而不是靜默相信內容。

```python
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class Doc:
    path: str
    owner: str
    verified: date
    canonical: bool

def stale(doc: Doc, today: date, max_age_days: int = 180) -> bool:
    return (today - doc.verified).days > max_age_days

doc = Doc("runbooks/queue-lag.md", "messaging", date(2026, 4, 1), True)
print(stale(doc, date(2026, 9, 30)))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Metadata 讓搜尋和 CI 能辨認 canonical 與可能過時內容。</p></div><div class="flow-card"><span>2</span><p>固定 180 天只是預設；高風險 runbook 應依變更或 game day 驗證得更頻繁。</p></div><div class="flow-card"><span>3</span><p>Fresh date 不證明內容正確，verification 應包含實際演練或命令結果。</p></div><div class="flow-card"><span>4</span><p>沒有 owner 的文件即使今天正確，也缺少未來更新責任。</p></div></div>

## Trade-offs 與 Failure Modes

- 要求所有知識都寫成長文件，會增加維護成本並壓抑分享。
- 同一內容複製到多處會產生分叉；入口應連結 canonical source。
- 只靠搜尋 popularity 會讓舊但常見文件持續排名較高。
- 將 tacit judgment 假裝完全文件化，可能讓新人過度自信執行高風險操作。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

在 AI 時代，repository、文件和工具輸出同時成為人類與 agent 的 context substrate。RAG 能快速找到片段，但若來源互相衝突、ACL 錯誤或沒有 freshness，模型只會更流暢地輸出過時答案。最佳實務是先改善 source-of-truth、metadata 和 access control，再增加生成層；短小的 agent instruction 應指向可驗證資料，而不是複製整個知識庫。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>用 AI 將 incident、review 和 design 討論草擬成可搜尋知識，再由 owner 核准。</li><li>建立 ACL-aware retrieval，只取回使用者原本有權閱讀的 canonical sources。</li><li>讓 agent 回答時附來源、版本和 last verified，未知時明確升級給 expert。</li><li>分析重複問題與無結果搜尋，找出缺少的文件、工具或 training。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>不得因索引或 embedding 讓 agent 繞過原始文件 ACL。</li><li>回答必須保留 provenance；無來源的生成文字不能成為 production runbook。</li><li>對高風險操作只提供經 game day 驗證的步驟，並要求人類確認當前環境。</li><li>文件變更與 agent instruction 一樣進 version control、review 和 freshness checks。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

知識平台的成功指標不是頁數，而是正確答案的 time-to-find、重複求助是否下降、值班是否能安全執行，以及來源能否隨系統改變。AI 能大幅改善 interface，但不能修復混亂的底層知識；先做 information architecture 和 ownership，模型才是乘數。

</aside>

## 動手驗證

1. 為一個服務建立一頁 knowledge map，不複製內容，只連到六個 canonical artifacts。
2. 執行範例，將 freshness threshold 改成依文件風險分級。
3. 搜尋三個常見問題，記錄找到答案所需時間、來源衝突與缺口。
4. 讓 AI 回答一個 runbook 問題，要求逐句附來源，再人工驗證權限和版本。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. 為什麼文件數量不是知識分享的好指標？</summary>

頁數不代表可找到、可信或新鮮。大量重複與過時文件反而增加搜尋成本；應看 time-to-correct-answer、使用與維護 feedback。

</details>

<details class="qa"><summary>Q2. Tacit knowledge 如何傳遞？</summary>

透過 pairing、rotation、teaching、incident shadowing 和實作 review；文件能記錄原則與入口，但無法完全取代情境判斷。

</details>

<details class="qa"><summary>Q3. Canonical home 有什麼作用？</summary>

讓更新、連結和搜尋指向同一 source of truth，避免多份副本逐漸產生不同答案。

</details>

<details class="qa"><summary>Q4. Freshness date 為何不足以保證正確？</summary>

日期可能只是形式更新；高風險內容應透過 smoke test、game day 或實際操作證據驗證。

</details>

<details class="qa"><summary>Q5. RAG 為何不能自動解決知識混亂？</summary>

Retrieval 只會從既有來源取片段；來源衝突、過時或 ACL 錯誤時，生成層可能把問題包裝成更有說服力的錯誤。

</details>

<details class="qa"><summary>Q6. Agent instruction 應該多長？</summary>

保持短而具導航性：說明邊界、核心命令、禁區和 canonical sources。大量易變細節應留在可版本與驗證的深層文件。

</details>

<details class="qa"><summary>Q7. Bus factor 改善的證據是什麼？</summary>

關鍵操作可由多位受訓成員完成、休假不阻塞、on-call 不總升級同一人，且知識入口與演練能持續運作。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Knowledge Sharing](https://abseil.io/resources/swe-book/html/ch03.html)
- [Software Engineering at Google — Documentation](https://abseil.io/resources/swe-book/html/ch10.html)
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)
- [Google Cloud — Agent observability](https://docs.cloud.google.com/stackdriver/docs/observability/agent-observability)

---

# 第 11 章　Engineering for Equity：為不同使用者設計

<p class="chapter-question">如果平均使用者一切正常，為什麼產品仍可能對某些群體系統性失敗？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 2 · 團隊、文化與領導</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

把 equity 轉成需求分群、資料檢查、可及性測試、錯誤預算切片和申訴機制。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node active"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-10-knowledge-sharing-readability-與-bus-factor"><span>上一站</span><strong>10. Knowledge Sharing、Readability 與 Bus Factor</strong></a><div class="position-card current"><span>你在這裡</span><strong>11. Engineering for Equity：為不同使用者設計</strong></div><a class="position-card" href="#chapter-12-tech-lead-manager-與-decision-rights"><span>下一站</span><strong>12. Tech Lead、Manager 與 Decision Rights</strong></a></div>

本章位於 **Part 2：團隊、文化與領導**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Equity（公平可及）</h3><div><span>白話定義</span><p>依不同使用者與成員的處境提供必要支持，而非假設所有人有相同能力與資源。</p></div><div class="example"><span>具體例子</span><p>CLI 只靠顏色表示錯誤會排除色覺差異使用者；公平設計會同時提供文字和符號。</p></div><div class="relevance"><span>本章位置</span><p>AI 資料與模型可能延續偏差，需在需求、測試和監控中顯式處理。</p></div></section><section class="term-card"><h3>Constraint（限制條件）</h3><div><span>白話定義</span><p>解法必須遵守的硬邊界，例如延遲、相容性、預算、法規或權限。</p></div><div class="example"><span>具體例子</span><p>登入 API p99 必須低於 300ms，而且舊手機版本仍能使用。</p></div><div class="relevance"><span>本章位置</span><p>工程取捨必須先知道 constraint；AI agent 也需要把它寫進完成條件。</p></div></section><section class="term-card"><h3>Eval（評估）</h3><div><span>白話定義</span><p>以可重複資料和評分規則，量測 AI 系統是否完成目標、遵守限制並安全失敗。</p></div><div class="example"><span>具體例子</span><p>除了答案正確率，也檢查 agent 是否用了禁止的工具、是否引用正確來源。</p></div><div class="relevance"><span>本章位置</span><p>Eval 是 AI 版本的 executable specification；沒有 eval 就無法知道模型或 prompt 更新是否退步。</p></div></section><section class="term-card"><h3>Goal–Signal–Metric</h3><div><span>白話定義</span><p>先定義想改善的結果，再找能觀察結果的信號，最後選可計算的代理量。</p></div><div class="example"><span>具體例子</span><p>Goal 是縮短回饋時間；signal 是工程師更快得到有用結果；metric 才是 CI p95 時間。</p></div><div class="relevance"><span>本章位置</span><p>這個順序可降低為了容易量測而優化錯誤目標的風險。</p></div></section></div>

## 為什麼需要這一章？

平均值會隱藏少數群體的嚴重失敗。裝置較舊、網路較慢、使用不同語言、需要輔助科技或不符合訓練資料主流的人，可能在整體 success rate 看似良好時持續受傷。Equity 要求團隊在需求、設計、測試與監控中看見差異，而不是等投訴證明存在。

### 真實 Use Case

語音登入整體成功率 97%，但對特定口音只有 72%。若 dashboard 只看全域 aggregate，團隊會宣稱達標；若按合法且隱私安全的 cohort 分析，就會發現產品可靠性分配不公平。

<div class="context-grid">
<section><span>問題壓力</span><p>平均值會隱藏少數群體的嚴重失敗。裝置較舊、網路較慢、使用不同語言、需要輔助科技或不符合訓練資料主流的人，可能在整體 success rate 看似良好時持續受傷。Equity 要求團隊在需求、設計、測試與監控中看見差異，而不是等投訴證明存在。</p></section>
<section><span>交付能力</span><p>把 equity 轉成需求分群、資料檢查、可及性測試、錯誤預算切片和申訴機制。</p></section>
<section><span>真實場景</span><p>語音登入整體成功率 97%，但對特定口音只有 72%。若 dashboard 只看全域 aggregate，團隊會宣稱達標；若按合法且隱私安全的 cohort 分析，就會發現產品可靠性分配不公平。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>User research / affected groups
          ↓
requirements + accessibility + harm model
          ↓
representative data / test cohorts
          ↓
design + fallback + appeal path
          ↓
slice metrics / SLO / qualitative feedback
          ↓
发现 disparity → prioritize → verify improvement

平均成功率 ─X→ 代表每個群體都成功</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Equality 是給所有人相同條件；equity 則考慮不同起點和障礙，使每個人能合理取得結果。工程上先問誰可能被預設排除：網速、裝置、語言、身心能力、地理、付款方式、資料代表性與權力關係。這不是列完清單，而是邀請受影響者參與需求與測試。

Metrics 必須能切片，但切片本身涉及隱私與統計風險。樣本太小會洩露身分或產生不穩定結論；只用敏感屬性又可能違反政策。需要與 privacy、legal 和 domain experts 合作，使用最小資料、聚合門檻和明確 retention。

設計也要提供 fallback 和 appeal。自動判斷若錯誤，使用者是否知道發生什麼、能否改正資料、是否有人類管道？在 AI 系統中，公平不是只在 model benchmark 測一次，而是從資料、介面、工具權限到 production drift 的端到端責任。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>在需求階段列出可能受影響群體與失敗後果，邀請代表性使用者研究。</p></div><div class="flow-card"><span>2</span><p>建立 accessibility、低頻寬、舊裝置、語言與資料切片的測試矩陣。</p></div><div class="flow-card"><span>3</span><p>以隱私安全方式量測分群 SLI，設定最低樣本與不公開細粒度資料。</p></div><div class="flow-card"><span>4</span><p>為高影響自動決策提供解釋、fallback、人工覆核與申訴。</p></div><div class="flow-card"><span>5</span><p>發布後監控 drift 和 disparity，將改善列入有 owner 的產品 backlog。</p></div></div>

## Coding／實務例子

用簡單函式顯示 aggregate success 如何掩蓋 cohort 差異。Production 分析還需 confidence interval 與 privacy threshold。

```python
events = {
    "fast_network": (9700, 10000),
    "slow_network": (720, 1000),
}

def rate(success: int, total: int) -> float:
    return success / total if total else 0.0

all_success = sum(x[0] for x in events.values())
all_total = sum(x[1] for x in events.values())
print("overall", rate(all_success, all_total))

for cohort, counts in events.items():
    print(cohort, rate(*counts))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>大群體權重高，使 overall 約 94.7%，但慢網路群體只有 72%。</p></div><div class="flow-card"><span>2</span><p>Slice 指標用來找系統差異，不應直接用來評價或歧視個人。</p></div><div class="flow-card"><span>3</span><p>真實資料要有 minimum cohort size、consent、access control 和 retention。</p></div><div class="flow-card"><span>4</span><p>定量 signal 應與使用者訪談和申訴資料交叉，避免只看可量測者。</p></div></div>

## Trade-offs 與 Failure Modes

- 切片太細可能暴露個人，且小樣本波動會造成錯誤決策。
- 只優化已知 cohorts 可能漏掉交叉身份與未被標記的新群體。
- 公平 metric 之間可能衝突，不能期待單一公式替代價值判斷。
- 增加 fallback 若流程羞辱、昂貴或等待過久，形式上存在仍不可及。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 使語言、無障礙和個人化介面更容易建立，也可能繼承訓練資料偏差、對低代表群體 hallucinate，或讓有付費工具的人獲得不成比例優勢。每個 agent workflow 都應檢查資料來源、拒絕與錯誤率切片、可及性、人工申訴和模型更新 drift；不能用單一 overall eval 宣稱公平。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>用 AI 產生多語與 accessibility 測試候選，再由母語者和實際使用者驗證。</li><li>建立分群 eval set，檢查模型、retrieval 與 tool outcomes 而非只看文字風格。</li><li>讓 AI 協助分析大量 qualitative feedback，但保留原始聲音和 minority themes。</li><li>在設計 review 讓模型提出可能被預設排除的情境，作為人類研究起點。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>敏感屬性與使用者內容必須有合法目的、最小化、ACL 和 retention policy。</li><li>不得讓模型自行決定公平定義或高影響申訴結果。</li><li>Eval 報告必須同時呈現 overall、重要 slices、樣本量與 uncertainty。</li><li>高影響 AI 決策需要人類覆核、使用者可理解通知與可行的 contest path。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Domain expert 不會把 equity 當發布前 checklist，而會把它視為可靠性分配問題：誰得到錯誤預算、誰承受 latency、誰有能力恢復。最重要的工作通常不是選一個 fairness formula，而是讓受影響群體進入需求與 feedback loop，並確保不公平 signal 能真的改變 roadmap。

</aside>

## 動手驗證

1. 執行範例並新增第三個小 cohort，觀察 overall 對它有多不敏感。
2. 為你熟悉的產品列出五種非主流使用環境及各自失敗後果。
3. 設計一份 slice dashboard，加入樣本量、隱私門檻和 qualitative feedback 入口。
4. 為 AI 自動判斷流程畫出通知、fallback、人工覆核和申訴路徑。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Equity 與 equality 的差別是什麼？</summary>

Equality 提供相同條件；equity 考慮不同障礙與起點，設計必要支持，使不同群體能取得合理結果。

</details>

<details class="qa"><summary>Q2. 為什麼 overall metric 可能誤導？</summary>

大群體主導加權平均，少數群體的嚴重失敗可能只讓總數小幅變動；需要代表性 slices 和 qualitative evidence。

</details>

<details class="qa"><summary>Q3. 切片越細是否越好？</summary>

不是。小樣本不穩定且可能洩露身分；應依風險選重要 cohorts，設定聚合門檻並遵守資料最小化。

</details>

<details class="qa"><summary>Q4. 公平問題可以由一個數學 metric 解決嗎？</summary>

通常不能。不同公平定義可能衝突，還涉及歷史、權力和後果；metric 提供 evidence，但價值取捨需要跨領域治理。

</details>

<details class="qa"><summary>Q5. AI 如何幫助 accessibility？</summary>

可協助產生替代文字、多語介面、語音與個人化輔助，但輸出仍需實際使用者與專家驗證，避免流暢卻不準確。

</details>

<details class="qa"><summary>Q6. 為何 appeal path 是系統設計的一部分？</summary>

高影響自動化必然會有錯誤；若使用者無法知道、修正或覆核，模型錯誤就成為不可逆傷害。

</details>

<details class="qa"><summary>Q7. 如何知道 equity 工作不是形式勾選？</summary>

分群 evidence 會影響 priority、SLO、設計和資源；受影響者能參與並看見改善，而不是只在文件列出一段聲明。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Engineering for Equity](https://abseil.io/resources/swe-book/html/ch04.html)
- [Software Engineering at Google — Measuring Engineering Productivity](https://abseil.io/resources/swe-book/html/ch07.html)
- [NIST — Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)
- [OWASP — Top 10 for LLM Applications 2025](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

---

# 第 12 章　Tech Lead、Manager 與 Decision Rights

<p class="chapter-question">Leader 應親自做所有重要決定，還是完全放手？如何讓速度、品質與人成長同時成立？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 2 · 團隊、文化與領導</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

分清方向、決策、執行、諮詢與風險接受，建立能力相稱的 delegation ladder。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node active"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-11-engineering-for-equity-為不同使用者設計"><span>上一站</span><strong>11. Engineering for Equity：為不同使用者設計</strong></a><div class="position-card current"><span>你在這裡</span><strong>12. Tech Lead、Manager 與 Decision Rights</strong></div><a class="position-card" href="#chapter-13-leading-at-scale-從個人影響力到平台與制度"><span>下一站</span><strong>13. Leading at Scale：從個人影響力到平台與制度</strong></a></div>

本章位於 **Part 2：團隊、文化與領導**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Ownership</h3><div><span>白話定義</span><p>對元件品質、決策、值班與改善負最終責任的明確主體。</p></div><div class="example"><span>具體例子</span><p>平台組維護 deployment API；服務組仍對自己設定錯誤造成的事故負責。</p></div><div class="relevance"><span>本章位置</span><p>AI 可以執行工作但不能承擔組織責任，因此 ownership 不可寫成『模型』。</p></div></section><section class="term-card"><h3>ADR（Architecture Decision Record）</h3><div><span>白話定義</span><p>短篇記錄決策背景、選項、選擇、代價與未來重訪條件的文件。</p></div><div class="example"><span>具體例子</span><p>記錄為何選 queue 而非同步 RPC，以及流量降到何種程度時可簡化。</p></div><div class="relevance"><span>本章位置</span><p>ADR 保存『為什麼』，避免人或 AI 只看現況後重複已否決的方案。</p></div></section><section class="term-card"><h3>Trade-off（取捨）</h3><div><span>白話定義</span><p>改善某個目標通常會增加另一種成本，工程決策需比較整體結果。</p></div><div class="example"><span>具體例子</span><p>更多測試提高信心，但也增加執行時間和維護成本。</p></div><div class="relevance"><span>本章位置</span><p>本書不提供永遠正確的工具選擇，而是提供判斷何時值得的模型。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section></div>

## 為什麼需要這一章？

團隊常因角色含糊而卡住：Tech Lead 以為 manager 決架構，manager 以為 senior engineer 已對齊，工程師等待批准，事故時又沒人知道誰能 rollback。領導的核心不是成為最大吞吐量的個人，而是設計一個團隊能持續做出好決策並成長的系統。

### 真實 Use Case

資料 migration 需要選擇 rollout。TL 負責技術 constraints，PM 說明使用者期限，manager 確保人力與 escalation，service owner 接受 production risk，實作者準備計畫。若所有權力集中 TL，速度和接班都受限；若無 decision owner，討論永遠不結束。

<div class="context-grid">
<section><span>問題壓力</span><p>團隊常因角色含糊而卡住：Tech Lead 以為 manager 決架構，manager 以為 senior engineer 已對齊，工程師等待批准，事故時又沒人知道誰能 rollback。領導的核心不是成為最大吞吐量的個人，而是設計一個團隊能持續做出好決策並成長的系統。</p></section>
<section><span>交付能力</span><p>分清方向、決策、執行、諮詢與風險接受，建立能力相稱的 delegation ladder。</p></section>
<section><span>真實場景</span><p>資料 migration 需要選擇 rollout。TL 負責技術 constraints，PM 說明使用者期限，manager 確保人力與 escalation，service owner 接受 production risk，實作者準備計畫。若所有權力集中 TL，速度和接班都受限；若無 decision owner，討論永遠不結束。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Mission / priorities
        ↓
Decision map
  ├─ who decides?
  ├─ who must be consulted?
  ├─ who executes?
  ├─ who accepts risk?
  └─ when to escalate?
        ↓
Delegation ladder
tell → propose → decide with review → decide and inform → own
        ↓
feedback / coaching / expanded autonomy</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Tech Lead 通常照顧技術方向、quality bar、跨元件取捨與技術 mentoring；manager 照顧團隊健康、人才、資源、績效和組織介面。實際公司可能不同，因此重點不是職稱，而是 decision rights 要寫清楚。Product、security、privacy 和 SRE 也可能對某些風險有否決或簽核責任。

Delegation 不是二元。對陌生高風險任務，leader 可先提供具體方向；能力與 context 增加後，成員先提出方案，再逐步取得直接決定並通知的權限。每次都由 leader 重做會阻止成長；完全放手卻不提供 constraints 和 feedback 則是 abandonment。

好的 leader 管理系統 bottleneck。他們讓工作可見、限制 work in progress、清除跨團隊阻塞、建立 review coverage，並保留深入技術的能力以判斷風險。最重要的是讓成功不依賴自己在線：文件、delegated ownership 和 successor growth 都是領導產出。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>為常見決策建立 decision map，明確 decide、consult、execute、risk owner。</p></div><div class="flow-card"><span>2</span><p>依任務風險與成員熟悉度選 delegation level，提前說明 escalation triggers。</p></div><div class="flow-card"><span>3</span><p>使用 design/ADR 對齊 constraints，不在實作完成後才重新爭論方向。</p></div><div class="flow-card"><span>4</span><p>以定期 feedback 校準 autonomy，指出 evidence 和影響，而非只給模糊評語。</p></div><div class="flow-card"><span>5</span><p>追蹤 leader 是否成為 review、deploy 或跨團隊資訊的單點瓶頸。</p></div></div>

## Coding／實務例子

用政策函式表達 delegation 取決於風險和 readiness，而不是只看職級。數字不是績效分數，而是討論起點。

```python
LEVELS = {
    1: "follow explicit plan",
    2: "propose, leader decides",
    3: "decide with required review",
    4: "decide and inform",
    5: "own outcome and policy",
}

def delegation_level(risk: int, familiarity: int) -> int:
    # risk/familiarity: 1..5
    raw = familiarity - max(0, risk - 3)
    return min(5, max(1, raw))

print(LEVELS[delegation_level(risk=5, familiarity=3)])
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>高風險會降低當前 delegation level，但不代表永久否定成員能力。</p></div><div class="flow-card"><span>2</span><p>Familiarity 包含 domain、production 和組織 context，不只是 coding skill。</p></div><div class="flow-card"><span>3</span><p>Required review 是 guardrail，也可成為刻意教學點。</p></div><div class="flow-card"><span>4</span><p>成熟團隊應記錄何種 evidence 能提升 level，避免權力只靠主觀感受。</p></div></div>

## Trade-offs 與 Failure Modes

- Decision map 太細會讓每個小決定都等待矩陣查詢，應聚焦高頻或高風險邊界。
- Leader 以品質為由重寫所有 code，會造成 learned helplessness 和單點瓶頸。
- 只委派執行、不委派問題理解與決策，成員無法成長為 owner。
- 過早給 production mutation 權限，可能把 coaching 問題轉成使用者事故。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 讓 leader 可以更快取得選項、摘要和 draft，也容易製造『看起來什麼都完成』的錯覺。Decision rights 必須延伸到 agent：誰可以要求它改 code、誰核准 merge、哪些 tool 能用、誰接受結果風險。Leader 的新能力包括設計 agent-friendly environment、評估 evidence，而不是親自閱讀每一行生成內容。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 準備 one-on-one 或 design review 的事實摘要，但由人決定回饋與優先級。</li><li>用 agent 對 ADR 做 pre-review，找缺少 constraints、owners 和 rollback。</li><li>把 delegation policy 編碼到 repository 和 tool permissions，減少每次臨時判斷。</li><li>用 AI 產生 coaching exercises、事故模擬和不同難度的成長任務。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>不得將人事評估、升遷或懲處直接委派給模型決定。</li><li>Agent autonomy 必須有具名 sponsor、scope、expires、audit 和 emergency revoke。</li><li>AI 摘要可能省略語氣與少數證據，高影響決策必須回看原始資料。</li><li>Leader 對模型建議的採用負責，不能用『AI 說的』轉移 accountability。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

最好的 leader 不是做最多決策，而是提升團隊正確做決策的範圍。他們保留足夠深度辨認危險，卻把 context、權限和 feedback 分散出去。AI 會讓執行更便宜，因此 leader 更要把注意力放在 problem selection、constraints、系統性風險和人的成長。

</aside>

## 動手驗證

1. 列出團隊五種常見決策，為每種填 decide、consult、execute 和 risk owner。
2. 執行範例，為同一成員比較低風險文件和高風險 schema migration 的 delegation。
3. 找出 leader 每週三個重複 approval，判斷能否改成 policy 或 guardrail。
4. 為 coding agent 寫一份 delegation card：scope、allowed tools、required checks、approval、expiry。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Tech Lead 與 manager 的固定分工是什麼？</summary>

沒有跨公司的固定答案；常見上 TL 偏技術方向與品質，manager 偏人員與組織。真正重要的是每類決策的權利與責任被顯式化。

</details>

<details class="qa"><summary>Q2. Delegation 和 abandonment 有何差別？</summary>

Delegation 提供目標、constraints、權限、支援、feedback 和 escalation；abandonment 只丟出任務，卻不提供成功條件與必要 context。

</details>

<details class="qa"><summary>Q3. 為什麼 familiarity 不等同 coding 年資？</summary>

高風險決策還需要 domain、使用者、production、法規與組織 context；資深工程師進入陌生領域也可能需要較多 review。

</details>

<details class="qa"><summary>Q4. Leader 如何知道自己成為瓶頸？</summary>

大量工作等待其 review/approval、休假時停止、其他成員不敢決策、資訊只經由他傳遞，或同類問題反覆升級。

</details>

<details class="qa"><summary>Q5. AI 能否決定工程師績效？</summary>

不應。它可整理可驗證事實，但評估涉及 context、偏差和高影響人事責任，需要透明政策與人類 judgment。

</details>

<details class="qa"><summary>Q6. Agent 的 delegation 與人的 delegation 最大差異？</summary>

Agent 沒有組織責任、穩定長期記憶和價值判斷，因此權限需更機械化限制、完整 audit，且結果必須由人類 owner 承擔。

</details>

<details class="qa"><summary>Q7. 領導成功最可持續的證據是什麼？</summary>

團隊在 leader 不在線時仍能依共同方向做出好決策、知道何時升級、持續產生新 owners，且品質與健康沒有下降。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — How to Lead a Team](https://abseil.io/resources/swe-book/html/ch05.html)
- [Software Engineering at Google — Leading at Scale](https://abseil.io/resources/swe-book/html/ch06.html)
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)
- [NIST — Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)

---

# 第 13 章　Leading at Scale：從個人影響力到平台與制度

<p class="chapter-question">當 leader 無法參與每個 project、review 和 incident 時，如何保持方向一致而不中央集權？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 2 · 團隊、文化與領導</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

以 mission、principles、interfaces、平台和領導網路放大判斷，並用 local feedback 防止制度失真。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node active"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-12-tech-lead-manager-與-decision-rights"><span>上一站</span><strong>12. Tech Lead、Manager 與 Decision Rights</strong></a><div class="position-card current"><span>你在這裡</span><strong>13. Leading at Scale：從個人影響力到平台與制度</strong></div><a class="position-card" href="#chapter-14-measuring-engineering-productivity-without-gaming"><span>下一站</span><strong>14. Measuring Engineering Productivity without Gaming</strong></a></div>

本章位於 **Part 2：團隊、文化與領導**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Scale（規模）</h3><div><span>白話定義</span><p>程式碼量、資料量、請求量、團隊數或系統存活時間增加後出現的新約束。</p></div><div class="example"><span>具體例子</span><p>十人可口頭協調；一千人需要可搜尋文件、標準化 review 與自動 policy。</p></div><div class="relevance"><span>本章位置</span><p>Scale 不是單純把數字放大，常會改變最適合的架構與流程。</p></div></section><section class="term-card"><h3>Ownership</h3><div><span>白話定義</span><p>對元件品質、決策、值班與改善負最終責任的明確主體。</p></div><div class="example"><span>具體例子</span><p>平台組維護 deployment API；服務組仍對自己設定錯誤造成的事故負責。</p></div><div class="relevance"><span>本章位置</span><p>AI 可以執行工作但不能承擔組織責任，因此 ownership 不可寫成『模型』。</p></div></section><section class="term-card"><h3>Coupling（耦合）</h3><div><span>白話定義</span><p>一個元件改變時，另一個元件也必須跟著改變的程度。</p></div><div class="example"><span>具體例子</span><p>前端直接依賴資料庫欄位名稱，使 schema rename 同時破壞 UI。</p></div><div class="relevance"><span>本章位置</span><p>Sustainable design 會讓必要耦合顯式化，並降低偶然耦合。</p></div></section><section class="term-card"><h3>Goal–Signal–Metric</h3><div><span>白話定義</span><p>先定義想改善的結果，再找能觀察結果的信號，最後選可計算的代理量。</p></div><div class="example"><span>具體例子</span><p>Goal 是縮短回饋時間；signal 是工程師更快得到有用結果；metric 才是 CI p95 時間。</p></div><div class="relevance"><span>本章位置</span><p>這個順序可降低為了容易量測而優化錯誤目標的風險。</p></div></section></div>

## 為什麼需要這一章？

小團隊 leader 可以靠直接溝通校正方向；規模增加後，任何需要 leader 親自出席的流程都會排隊。若只增加規則，組織變慢；若完全下放，團隊可能重複平台、採用不相容 contract，或在共同 production 上製造風險。Scale leadership 要把判斷轉成可重用環境，而不是複製個人指令。

### 真實 Use Case

二十個服務各自設計 deployment，導致 audit、rollback 和 on-call 工具不同。中央團隊若逐一審核會成為瓶頸；更好的做法是提供 paved road：安全預設、可觀測 rollout、self-service 和清楚的例外流程。

<div class="context-grid">
<section><span>問題壓力</span><p>小團隊 leader 可以靠直接溝通校正方向；規模增加後，任何需要 leader 親自出席的流程都會排隊。若只增加規則，組織變慢；若完全下放，團隊可能重複平台、採用不相容 contract，或在共同 production 上製造風險。Scale leadership 要把判斷轉成可重用環境，而不是複製個人指令。</p></section>
<section><span>交付能力</span><p>以 mission、principles、interfaces、平台和領導網路放大判斷，並用 local feedback 防止制度失真。</p></section>
<section><span>真實場景</span><p>二十個服務各自設計 deployment，導致 audit、rollback 和 on-call 工具不同。中央團隊若逐一審核會成為瓶頸；更好的做法是提供 paved road：安全預設、可觀測 rollout、self-service 和清楚的例外流程。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Mission / user outcomes
        ↓
few durable principles
        ↓
interfaces + paved road platform + policy-as-code
        ↓
distributed owners / tech leads / communities
        ↓
local decisions + fast feedback
        ↓
portfolio signals / incidents / user research
        └────────────→ improve principles &amp; platform</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Scale leadership 的第一層是 direction：少數持久原則和可量測結果，讓 local teams 能自行判斷。若 strategy 只是專案清單，任何新情況都要回中央詢問。第二層是 enablement：提供平台、templates、libraries 和 specialist consultation，把安全做法變成最容易的路。

第三層是 leadership network。Staff engineers、managers、SRE、security champions 和 communities of practice 分散 context 與 judgment。中央團隊維持跨組織 invariants；local owners 保有 use-case 知識和執行自治。例外不是失敗，而是重要 feedback：若大量團隊走 escape hatch，可能代表 paved road 不適合。

制度需要雙向 feedback。Portfolio metrics 看等待、stability 和採用；使用者研究了解平台 friction；incident 和 exception review 找未知需求。若中央只量 compliance，團隊會形式採用或建立 shadow systems。Scale 的目標是提高整體決策品質，不是讓每個服務外觀相同。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>將 strategy 表達成使用者結果、constraints 和少數 durable principles。</p></div><div class="flow-card"><span>2</span><p>把高頻、安全的共同路徑做成 self-service paved road 和 policy-as-code。</p></div><div class="flow-card"><span>3</span><p>建立 distributed leaders 與 communities，讓 domain context 不必全回中央。</p></div><div class="flow-card"><span>4</span><p>為合法例外提供有期限、可觀測的 escape hatch，而非逼迫地下繞過。</p></div><div class="flow-card"><span>5</span><p>用 platform user research、queue time、incidents 和 exception patterns 更新制度。</p></div></div>

## Coding／實務例子

以下把平台採用看成產品 funnel，而非命令。若使用者在 setup 或 deploy 流失，應改善平台，而不只要求 compliance。

```python
funnel = {
    "visited_docs": 1000,
    "created_service": 720,
    "first_deploy": 510,
    "slo_configured": 260,
    "oncall_ready": 180,
}

previous = None
for step, users in funnel.items():
    conversion = 1.0 if previous is None else users / previous
    print(step, f"{conversion:.1%}")
    previous = users
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>每一步 conversion 顯示平台使用者遇到的 friction，不直接責怪團隊。</p></div><div class="flow-card"><span>2</span><p>SLO 和 on-call 準備大幅流失，可能表示流程太晚、文件不足或責任不清。</p></div><div class="flow-card"><span>3</span><p>採用率必須與 reliability 和 developer experience 一起看，避免只追求數字。</p></div><div class="flow-card"><span>4</span><p>Qualitative interviews 能解釋 funnel，但應抽樣不同規模與成熟度團隊。</p></div></div>

## Trade-offs 與 Failure Modes

- Paved road 若變成唯一道路，特殊 latency、法規或資料需求可能被錯誤壓平。
- 大量中央政策增加 cognitive load，團隊可能只求通過而不理解風險。
- 平台沒有產品管理和 SLO 時，會把所有下游效率綁在不可靠 dependency 上。
- 只表揚跨組織 launch，不投資 maintenance，會留下無 owner 的廣泛系統。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 使個人與團隊能快速建立局部工具，因此 scale organization 更需要共用 agent platform、approved models、tool broker、policy 和 context sources。最佳做法不是中央 team 寫所有 prompts，而是提供身份、sandbox、eval、audit 和 reusable tools，讓 local owners 在 guardrails 內組合。Agent exception 和失敗資料也應回饋平台。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>建立組織級 agent tool catalog，重用認證、audit 和結構化輸出。</li><li>提供 repository scaffold、eval harness 和安全預設，降低每隊自建成本。</li><li>用 AI 分析跨服務 incidents、exceptions 和重複元件，找平台機會。</li><li>建立 domain-specific agents，由 local owner 維護知識，中央平台維護控制面。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>模型和 tools 必須使用 workload identity，不共享長期個人憑證。</li><li>平台提供最小權限、quota、cost attribution、kill switch 和 audit。</li><li>Local domain owner 核准資料來源與 action policy，中央不得假設通用 context 足夠。</li><li>採用率不是唯一成功指標；同時看 failure、rework、security 和 user experience。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Scale leader 的槓桿不是更多 mandate，而是讓好選擇具有最低 friction、壞選擇難以意外發生、真正例外能被看見。AI 平台尤其如此：若 approved path 太慢，團隊會把秘密貼進公共 chatbot；若只禁止不提供替代，治理只會失去 visibility。

</aside>

## 動手驗證

1. 選一項跨團隊政策，判斷能否改成安全預設、library 或 automated check。
2. 執行 funnel 範例，設計三個 qualitative 問題解釋最大流失。
3. 列出兩種 legitimate escape hatch，為它們設定 owner、expiry 和 review。
4. 畫出公司 AI platform control plane：identity、model、tool、data、eval、audit 和 kill switch。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Scale leadership 為何不能只增加規則？</summary>

規則需要理解、審核和更新，數量增加會提高等待與 cognitive load。應把高頻 invariants 轉成平台預設和自動 feedback。

</details>

<details class="qa"><summary>Q2. Paved road 的核心價值是什麼？</summary>

讓安全、可維護、可觀測的共同做法成為最容易採用的路，同時降低每個團隊重建基礎設施的成本。

</details>

<details class="qa"><summary>Q3. Escape hatch 為何必要？</summary>

真實 domain 有合法特殊 constraints；沒有透明例外路徑，團隊會建立不可見繞道，使中央更無法管理風險。

</details>

<details class="qa"><summary>Q4. 平台 adoption funnel 能回答什麼？</summary>

它顯示使用者在哪個步驟流失，提供 friction signal；仍需訪談理解原因，不能直接把流失視為團隊不合作。

</details>

<details class="qa"><summary>Q5. 中央 AI 團隊與 local owner 如何分工？</summary>

中央維護 identity、sandbox、models、tool broker、eval/audit 基礎；local owner 維護 domain data、workflow、風險和 action policy。

</details>

<details class="qa"><summary>Q6. 為何 AI 禁令可能降低安全？</summary>

若工作需求仍存在而沒有可用替代，成員會使用未批准工具，組織失去資料流與風險 visibility；治理要提供可行 paved road。

</details>

<details class="qa"><summary>Q7. 成功的 scale system 有何特徵？</summary>

Local decisions 快、共同 invariants 穩定、例外可見、平台有良好體驗與可靠性，且制度會依 feedback 持續更新。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Leading at Scale](https://abseil.io/resources/swe-book/html/ch06.html)
- [Software Engineering at Google — Compute as a Service](https://abseil.io/resources/swe-book/html/ch25.html)
- [DORA 2025 — AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)
- [Google Cloud — How Google SRE is using agentic AI](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)

---

# 第 14 章　Measuring Engineering Productivity without Gaming

<p class="chapter-question">如何知道工程系統真的改善，而不是只讓 dashboard 數字變漂亮？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 2 · 團隊、文化與領導</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

從 goal、signal、metric 建立平衡量測，結合速度、品質、認知負荷與使用者結果。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node active"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-13-leading-at-scale-從個人影響力到平台與制度"><span>上一站</span><strong>13. Leading at Scale：從個人影響力到平台與制度</strong></a><div class="position-card current"><span>你在這裡</span><strong>14. Measuring Engineering Productivity without Gaming</strong></div><a class="position-card" href="#chapter-15-style-guide-rules-與-automation"><span>下一站</span><strong>15. Style Guide、Rules 與 Automation</strong></a></div>

本章位於 **Part 2：團隊、文化與領導**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Goal–Signal–Metric</h3><div><span>白話定義</span><p>先定義想改善的結果，再找能觀察結果的信號，最後選可計算的代理量。</p></div><div class="example"><span>具體例子</span><p>Goal 是縮短回饋時間；signal 是工程師更快得到有用結果；metric 才是 CI p95 時間。</p></div><div class="relevance"><span>本章位置</span><p>這個順序可降低為了容易量測而優化錯誤目標的風險。</p></div></section><section class="term-card"><h3>Goodhart’s Law</h3><div><span>白話定義</span><p>當代理量成為硬目標，人會優化數字而不是原始目的，使指標失去資訊。</p></div><div class="example"><span>具體例子</span><p>以 commit 數評績效，工程師便拆出大量沒有價值的小 commit。</p></div><div class="relevance"><span>本章位置</span><p>AI 採用率、接受行數與 token 數同樣不適合作為個人績效目標。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section><section class="term-card"><h3>SLO（Service Level Objective）</h3><div><span>白話定義</span><p>某段時間內希望 SLI 達到的明確目標。</p></div><div class="example"><span>具體例子</span><p>28 天內 99.9% 有效 API request 成功。</p></div><div class="relevance"><span>本章位置</span><p>SLO 讓可靠性、告警和發布決策共享同一尺度。</p></div></section></div>

## 為什麼需要這一章？

工程工作包含設計、排障、溝通、預防風險和刪除複雜度，不能用 lines of code、commit 或 ticket 數直接代表價值。任何單一 metric 成為績效目標後，都可能被拆分、延後或選擇性記錄。量測的目的應是回答可行動問題，而不是替個人排序製造虛假客觀性。

### 真實 Use Case

公司導入 coding assistant 後，accepted suggestions 上升 300%，但 PR 變大、review queue 增長、rollback 增加。若只看 adoption 會宣稱成功；若 goal 是更快且穩定地交付使用者價值，就必須同時看 lead time、rework、change failure 和 developer experience。

<div class="context-grid">
<section><span>問題壓力</span><p>工程工作包含設計、排障、溝通、預防風險和刪除複雜度，不能用 lines of code、commit 或 ticket 數直接代表價值。任何單一 metric 成為績效目標後，都可能被拆分、延後或選擇性記錄。量測的目的應是回答可行動問題，而不是替個人排序製造虛假客觀性。</p></section>
<section><span>交付能力</span><p>從 goal、signal、metric 建立平衡量測，結合速度、品質、認知負荷與使用者結果。</p></section>
<section><span>真實場景</span><p>公司導入 coding assistant 後，accepted suggestions 上升 300%，但 PR 變大、review queue 增長、rollback 增加。若只看 adoption 會宣稱成功；若 goal 是更快且穩定地交付使用者價值，就必須同時看 lead time、rework、change failure 和 developer experience。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Question: 我們想改善什麼決策？
        ↓
Goal: 使用者價值 / 工程結果
        ↓
Signals: 哪些現象表示變好？
  ├─ speed / flow
  ├─ quality / stability
  ├─ satisfaction / cognitive load
  ├─ collaboration / learning
  └─ cost / sustainability
        ↓
Metrics + qualitative evidence
        ↓
segment / triangulate / inspect gaming
        ↓
action → observe unintended effects</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

先寫問題和 actionability。例如「CI 是否阻礙小批次整合，若是要投資哪個 bottleneck？」比「工程師生產力是多少？」更可回答。Goal 描述希望達成的結果；signal 是可觀察現象；metric 才是資料計算。反過來先挑現成欄位，容易把工具可量測的東西誤認為重要。

量測應 triangulate。Repository data 看 flow，incident data 看外溢風險，survey 看 cognitive load，訪談解釋原因。每種資料都有 bias：ticket 不記錄非正式協助，survey 有回應偏差，lead time 可能因 batch definition 不同失真。指標要分群看 distribution，不只平均。

避免用 team-system metrics 排個人。個人 LOC、review comments 或 AI acceptance 會鼓勵競爭與 gaming，傷害共享工作。使用 metrics 應先公開定義、用途、保留和限制，與被量測者共同解讀。每次改善也要看 counter-metrics，防止局部優化。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>從一個具體決策問題開始，確認量測結果會導致什麼 action。</p></div><div class="flow-card"><span>2</span><p>使用 GSM 定義 goal、至少三個 signals，再選能代表它們的 metrics。</p></div><div class="flow-card"><span>3</span><p>同時量 flow、quality、human experience 和 user outcome，避免單軸優化。</p></div><div class="flow-card"><span>4</span><p>查看 p50/p90、cohort 和 trend，搭配 survey、訪談與抽樣案例。</p></div><div class="flow-card"><span>5</span><p>預先寫出 gaming 和 unintended effects，設定 counter-metrics 與停止條件。</p></div></div>

## Coding／實務例子

範例建立平衡 scorecard，但不把不同單位硬加成個人分數。程式只標記需要共同調查的 tension。

```python
team = {
    "lead_time_hours": 8,
    "change_failure_rate": 0.18,
    "review_wait_hours": 11,
    "developer_satisfaction": 3.1,  # 1..5
}

def tensions(m: dict) -> list[str]:
    findings = []
    if m["lead_time_hours"] < 12 and m["change_failure_rate"] > 0.15:
        findings.append("speed improved, stability needs investigation")
    if m["review_wait_hours"] > m["lead_time_hours"] / 2:
        findings.append("review queue dominates lead time")
    if m["developer_satisfaction"] < 3.5:
        findings.append("quantitative gains may hide cognitive load")
    return findings

print(tensions(team))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>函式尋找 metrics 間的 tension，而不是算出『生產力 78 分』。</p></div><div class="flow-card"><span>2</span><p>Threshold 應依服務與歷史 baseline 設定，範例數字不是跨公司的標準。</p></div><div class="flow-card"><span>3</span><p>Finding 是調查起點，需要看 sample PR、incident 和訪談。</p></div><div class="flow-card"><span>4</span><p>Team-level 系統 metric 用於改善環境，不應直接分配個人績效。</p></div></div>

## Trade-offs 與 Failure Modes

- 單一 composite score 隱藏 trade-off，且權重難以公開辯護。
- Metric definition 改變或工具遷移會製造假趨勢，需要版本與註記。
- 只看平均會隱藏少數超長 review、特定時區或新人的困難。
- 觀測本身改變行為；成員若不信任用途，資料品質和心理安全都會下降。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 時代最容易被濫用的 metrics 是生成行數、suggestion acceptance、prompt 數和 agent 完成任務數。它們量 adoption 或 activity，不等於使用者價值。DORA 類型的實務更重視 AI 是否縮短 feedback、改善 flow，同時維持 stability、quality 和 developer experience；也要量 review/rework 是否被下游吸收。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>比較使用 AI 前後的 lead time、review wait、rework、change failure 和 satisfaction。</li><li>用 agent 分析 qualitative survey 主題，但保留匿名、樣本量和原文抽查。</li><li>量 agent task 的一次通過率、人工接管率、tool failure 和 policy violation。</li><li>以 experiment 或 phased rollout 比較相似團隊，避免把同時期變化都歸因 AI。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>禁止以 AI usage 或 acceptance rate 直接評估個人績效。</li><li>公開 telemetry 收集範圍、用途、retention 和誰能查看，允許合理 opt-out。</li><li>AI 產生的 metric 解釋必須可追到 query、definition 和原始 aggregate。</li><li>任何速度改善都配對 stability、security、review load 和使用者 outcome counter-metrics。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Domain expert 會把 metrics 當對話和實驗工具，而不是真理。最有價值的結果常是發現原本假設錯了，例如 CI 不是 bottleneck，需求反覆才是。若 dashboard 不能改變資源、流程或產品決策，就不值得長期收集；量測本身也有隱私、維護和信任成本。

</aside>

## 動手驗證

1. 選一個工程問題，寫 Goal、三個 Signals、每個 Signal 一個 Metric。
2. 執行範例，新增 deploy frequency，觀察它是否提供新資訊或只是 activity。
3. 為 metrics 寫 data contract：definition、source、owner、retention、known bias。
4. 設計 AI pilot scorecard，必須同時包含 flow、quality、human 和 user 四類 evidence。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. 為什麼 LOC 不適合衡量個人生產力？</summary>

價值可能來自刪除 code、設計、review、協助與預防事故；以 LOC 作目標會鼓勵膨脹和避免共享工作，且不同問題不可比較。

</details>

<details class="qa"><summary>Q2. Goal、Signal、Metric 的順序有何價值？</summary>

先定義結果和可觀察現象，再選數字，能降低因工具容易取得某資料就錯把它當目標的風險。

</details>

<details class="qa"><summary>Q3. Triangulation 是什麼？</summary>

用多種有不同偏差的證據交叉，例如 repository flow、incidents、survey 和訪談；一致時信心增加，衝突時提供新的調查線索。

</details>

<details class="qa"><summary>Q4. Counter-metric 有什麼作用？</summary>

監控改善某目標是否傷害另一目標，例如 deployment 變快時同看 change failure、review load 和 burnout。

</details>

<details class="qa"><summary>Q5. AI suggestion acceptance 能回答什麼？</summary>

主要回答工具功能被採用多少，不能單獨證明工作更快、品質更好或使用者獲益；還需 outcome evidence。

</details>

<details class="qa"><summary>Q6. 為什麼不建議把所有 metrics 合成一分？</summary>

Composite score 隱藏不同單位、取捨與 uncertainty，容易被 gaming；保留多維 tension 更有助於找出系統 bottleneck。

</details>

<details class="qa"><summary>Q7. 何時應停止收集 metric？</summary>

當它沒有可行動 decision、成本或隱私風險超過收益、定義不再可信，或更直接 evidence 已可取得時。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Measuring Engineering Productivity](https://abseil.io/resources/swe-book/html/ch07.html)
- [Software Engineering at Google — Preface](https://abseil.io/resources/swe-book/html/pr01.html)
- [DORA 2025 — AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)
- [OpenAI — Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)

---
