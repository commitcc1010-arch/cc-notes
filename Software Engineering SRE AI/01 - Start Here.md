---
title: "先建立全局模型"
part: 0
as_of: 2026-09-30
---

# Part 0　先建立全局模型

先看完整生命週期與共同語言。後面不是 46 個孤立主題，而是逐步放大同一條從需求到事故學習的 feedback loop。

# 第 1 章　從一行程式碼到可靠服務

<p class="chapter-question">一段在筆電上正確執行的程式，距離能被真實使用者長期信任，究竟還差哪些工程能力？</p>

<div class="chapter-meta"><span>難度：入門</span><span>Part 0 · 先建立全局模型</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

建立全書唯一的黃金路徑：能把需求、程式碼、交付、production、事故與學習放進同一張圖。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node active"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><div class="position-card muted"><span>上一站</span><strong>全書導讀</strong></div><div class="position-card current"><span>你在這裡</span><strong>01. 從一行程式碼到可靠服務</strong></div><a class="position-card" href="#chapter-02-共同語言-service-feedback-與-ai-agent"><span>下一站</span><strong>02. 共同語言：Service、Feedback 與 AI Agent</strong></a></div>

本章位於 **Part 0：先建立全局模型**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Software（軟體）</h3><div><span>白話定義</span><p>可被電腦執行的指令、資料與設定；真正的產品還包括部署方式、依賴、監控和操作流程。</p></div><div class="example"><span>具體例子</span><p>一個 Python 檔可以運算價格，但沒有資料庫 migration、部署與告警時，還不是可長期營運的服務。</p></div><div class="relevance"><span>本章位置</span><p>本書把 code 放回完整生命週期，避免把『寫完函式』誤認為『工程完成』。</p></div></section><section class="term-card"><h3>Service（服務）</h3><div><span>白話定義</span><p>長時間運行、透過網路或訊息介面替其他人或系統提供能力的軟體。</p></div><div class="example"><span>具體例子</span><p>付款 API 接收 request，驗證、寫入資料庫，再回傳成功或失敗。</p></div><div class="relevance"><span>本章位置</span><p>SRE 的可靠性目標通常以服務向使用者提供的行為為單位。</p></div></section><section class="term-card"><h3>Production</h3><div><span>白話定義</span><p>真實使用者、真實資料與真實商業影響所在的執行環境。</p></div><div class="example"><span>具體例子</span><p>測試環境 timeout 只是紅燈；production timeout 可能讓客戶重複付款。</p></div><div class="relevance"><span>本章位置</span><p>Production 的不確定性使 observability、rollback、capacity 和 incident response 成為必要能力。</p></div></section><section class="term-card"><h3>Lifecycle（生命週期）</h3><div><span>白話定義</span><p>一項變更從需求、設計、實作、驗證、發布、運行到淘汰的完整時間線。</p></div><div class="example"><span>具體例子</span><p>新增欄位不只改 schema，還要 migration、雙讀寫、監控、清除舊格式。</p></div><div class="relevance"><span>本章位置</span><p>SWE 管理變更的長期成本；SRE 管理變更進入 production 後的風險。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section></div>

## 為什麼需要這一章？

初學者常把軟體工作想成「理解需求、寫完 code、測試通過」。但真實服務還要面對多人同時修改、依賴升級、部署失敗、流量尖峰、機器故障、資料相容性、值班和多年維護。若沒有共同生命週期，每個團隊只優化自己眼前的一段：開發追求快、維運追求不變、管理只看產出數字，最後由使用者承擔斷裂處。

### 真實 Use Case

團隊要為購物網站新增折扣功能。函式算對價格只是起點；還要確認舊手機能解析 response、不同時區不會算錯日期、reviewer 看得懂規則、artifact 可重現、canary 沒傷害使用者、dashboard 看得見錯價，並能在事故後還原與修正。

<div class="context-grid">
<section><span>問題壓力</span><p>初學者常把軟體工作想成「理解需求、寫完 code、測試通過」。但真實服務還要面對多人同時修改、依賴升級、部署失敗、流量尖峰、機器故障、資料相容性、值班和多年維護。若沒有共同生命週期，每個團隊只優化自己眼前的一段：開發追求快、維運追求不變、管理只看產出數字，最後由使用者承擔斷裂處。</p></section>
<section><span>交付能力</span><p>建立全書唯一的黃金路徑：能把需求、程式碼、交付、production、事故與學習放進同一張圖。</p></section>
<section><span>真實場景</span><p>團隊要為購物網站新增折扣功能。函式算對價格只是起點；還要確認舊手機能解析 response、不同時區不會算錯日期、reviewer 看得懂規則、artifact 可重現、canary 沒傷害使用者、dashboard 看得見錯價，並能在事故後還原與修正。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>使用者問題
    ↓
需求 / Constraints / SLO
    ↓
Design → Code → Review → Test → Build → CI
                                      ↓
                                 Artifact
                                      ↓
                         Canary → Production
                                      ↓
                     Metrics / Logs / Traces
                                      ↓
                         Alert → Incident
                                      ↓
                  Postmortem → Test / Rule / Doc
                                      └──────────→ 下一次變更</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

這張圖同時包含兩種流動。上半部是 change flow：一個想法逐漸被約束、實作、驗證，再成為可部署 artifact。下半部是 evidence flow：真實世界把 latency、error、使用者行為和事故送回團隊，迫使模型更新。只畫前半部會得到「交付工廠」，只畫後半部則變成永遠救火的 operations。

Software Engineering at Google 關心的是 change 如何跨越時間與規模仍可安全進行；SRE 關心的是服務進入 production 後，如何用工程方法控制風險。兩者不是開發與維運的兩個島，而是同一個 feedback loop 的前後段。Review、test、CI 是發布前的感測器；SLI、alert 和 incident 是發布後的感測器。

可靠服務不是「從不失敗」。它是知道哪些行為最重要、允許多少失敗、如何限制 blast radius、何時停止發布，以及怎麼把事故留下的知識轉成永久資產。這也解釋為何本書會從文化談到 consensus：它們都在保護同一條價值流。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>把使用者可見需求轉成 constraints、API contract 與可量測的成功條件。</p></div><div class="flow-card"><span>2</span><p>以 review、test、build 和 CI 建立發布前的快速 feedback。</p></div><div class="flow-card"><span>3</span><p>以 canary、SLI、logs、metrics 和 traces 建立發布後的真實 feedback。</p></div><div class="flow-card"><span>4</span><p>事故發生時先限制傷害、恢復服務，再把教訓編碼成 test、rule、tool 或 document。</p></div><div class="flow-card"><span>5</span><p>定期刪除已無價值的流程與元件，避免 feedback loop 被歷史成本拖慢。</p></div></div>

## Coding／實務例子

下面用一個極小的 Python pipeline 表示變更只有通過每個 gate 才能前進。它不是 CI 產品，而是讓你看見『信心來自多個獨立證據』。

```python
from dataclasses import dataclass, field

@dataclass
class Change:
    name: str
    evidence: dict[str, bool] = field(default_factory=dict)

GATES = ("review", "unit_test", "contract_test", "build", "canary")

def releasable(change: Change) -> bool:
    missing = [gate for gate in GATES if not change.evidence.get(gate)]
    if missing:
        print("BLOCKED:", ", ".join(missing))
        return False
    print("READY:", change.name)
    return True

candidate = Change(
    "discount-v2",
    {"review": True, "unit_test": True, "contract_test": True,
     "build": True, "canary": False},
)
releasable(candidate)
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p><code>Change</code> 不等同 source code；它攜帶讓人相信這次修改安全的 evidence。</p></div><div class="flow-card"><span>2</span><p>每個 gate 捕捉不同失敗，不能因 unit test 通過就宣稱 production 一定安全。</p></div><div class="flow-card"><span>3</span><p><code>canary=False</code> 表示真實環境仍缺證據，因此 pipeline 正確地阻止全面發布。</p></div><div class="flow-card"><span>4</span><p>Production telemetry 之後應回寫新的 evidence，而不是讓部署成為流程終點。</p></div></div>

## Trade-offs 與 Failure Modes

- Gate 越多不一定越安全；重複、慢或高噪音檢查會鼓勵人繞過整套流程。
- 所有 gate 都由同一個錯誤假設產生時，數量再多也不是獨立證據。
- 只量 deployment 成功而不量使用者結果，會把『程式啟動』誤認為『功能正確』。
- 沒有 owner 的 postmortem action item 會讓 feedback loop 在最後一步斷掉。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 把變更產生速度提高後，最先出現的瓶頸通常不是打字，而是規格品質、context、驗證、審查與整合。工程師的角色會更多轉向定義 intent、constraints、acceptance criteria 和風險邊界；agent 可探索與實作，但不能替組織承擔產品承諾。若只把 AI 接在 code 方塊，整條生命週期其他部分沒有升級，結果通常是更快產生更多待 review、待修復和待理解的變更。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 agent 依明確需求建立小型 plan、修改隔離 branch，並列出它取得的證據。</li><li>用 AI 摘要 diff、找可能受影響的 call sites，協助 reviewer 建立地圖。</li><li>讓 AI 根據失敗 test 或 telemetry 產生候選假設，但要求附上可驗證步驟。</li><li>在 postmortem 後讓 AI 草擬新的 tests、runbook 或 static rule，再由 owner 採納。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Agent 只能取得任務需要的 repository、tool 和環境權限；production 預設唯讀。</li><li>完成條件必須包含 deterministic build、test、lint 和安全檢查，不能以模型自評取代。</li><li>高風險變更需要獨立 reviewer；產生變更的同一段對話不能自行批准。</li><li>保存 model、prompt/instruction、tool trace、commit 與結果，讓問題可重現與稽核。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

資深工程師不會問「我們用了多少 AI」，而會問 feedback loop 是否變短且仍可信：需求到證據的時間是否下降、rollback 是否更快、review 負荷是否合理、缺陷是否外溢。AI 自治權應依風險與歷史成功證據逐步擴大；低風險文件修正和 production schema migration 不應使用同一套批准政策。

</aside>

## 動手驗證

1. 選一個最近做過的功能，畫出從需求到 production 的真實路徑，標出每個等待點與 handoff。
2. 在圖上用紅色標記錯誤最晚會在哪裡被發現，再思考能否把 signal 往前移。
3. 執行範例，逐一拿掉 gate，寫出哪類錯誤可能因此進入 production。
4. 為一個 coding agent 任務寫出 intent、constraints、驗證命令與禁止操作四個欄位。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. 為什麼『測試通過』仍不代表服務可靠？</summary>

測試只涵蓋已建模的輸入與環境；production 還有真實流量分布、依賴故障、容量、設定和操作因素。可靠性需要發布前與發布後的多層 evidence，並讓新事故回饋到測試。

</details>

<details class="qa"><summary>Q2. SWE 與 SRE 在黃金路徑中如何分工？</summary>

SWE 主要降低長期修改 codebase 的成本與風險；SRE 主要控制服務在 production 的可靠性與營運成本。兩者透過 CI/CD、change management、testing 和 telemetry 相接，不能完全分離。

</details>

<details class="qa"><summary>Q3. 為何 postmortem 必須產生工程資產？</summary>

只有故事不會改變下一次系統行為。將教訓變成 test、alert、runbook、API constraint 或自動化，才能讓同類錯誤更早被攔截或更快恢復。

</details>

<details class="qa"><summary>Q4. 更多 gate 何時反而降低可靠性？</summary>

當 gate 太慢、重複、flaky 或無法解釋時，開發者會延後整合、批次變大或尋找繞過方法。好的 gate 必須對應具體風險，並提供快速且可行動的 feedback。

</details>

<details class="qa"><summary>Q5. AI 在這條路徑中最適合扮演什麼角色？</summary>

它適合加速探索、草擬、搜尋、測試候選、證據整理與低風險操作；人仍需定義產品 intent、接受風險、處理價值衝突並對結果負責。

</details>

<details class="qa"><summary>Q6. 如何判斷 agent 是否可以自動 merge？</summary>

依變更風險、可逆性、測試完整度、blast radius、歷史成功率和 audit 能力決定。先從小型、可回退、deterministic checks 完整的範圍開始，失敗就降低自治。

</details>

<details class="qa"><summary>Q7. 本章最重要的 invariant 是什麼？</summary>

任何變更前進到下一階段時，都應帶著與風險相稱、可被別人檢查的 evidence；不能只因作者或模型表示有信心就前進。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Preface](https://abseil.io/resources/swe-book/html/pr01.html)
- [Site Reliability Engineering — Introduction](https://sre.google/sre-book/introduction/)
- [DORA 2025 — AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)

---

# 第 2 章　共同語言：Service、Feedback 與 AI Agent

<p class="chapter-question">如果讀者連 service、deployment、context、agent、eval 都不熟，如何建立足以閱讀後續 46 章的共同模型？</p>

<div class="chapter-meta"><span>難度：入門</span><span>Part 0 · 先建立全局模型</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

用一個最小服務拆清楚 request、state、dependency、deployment、telemetry，以及 AI agent 的 observe–act loop。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node active"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-01-從一行程式碼到可靠服務"><span>上一站</span><strong>01. 從一行程式碼到可靠服務</strong></a><div class="position-card current"><span>你在這裡</span><strong>02. 共同語言：Service、Feedback 與 AI Agent</strong></div><a class="position-card" href="#chapter-03-programming-與-software-engineering-的差別"><span>下一站</span><strong>03. Programming 與 Software Engineering 的差別</strong></a></div>

本章位於 **Part 0：先建立全局模型**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Service（服務）</h3><div><span>白話定義</span><p>長時間運行、透過網路或訊息介面替其他人或系統提供能力的軟體。</p></div><div class="example"><span>具體例子</span><p>付款 API 接收 request，驗證、寫入資料庫，再回傳成功或失敗。</p></div><div class="relevance"><span>本章位置</span><p>SRE 的可靠性目標通常以服務向使用者提供的行為為單位。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section><section class="term-card"><h3>AI Agent</h3><div><span>白話定義</span><p>能接收目標、規劃步驟、呼叫工具、觀察結果並迭代的模型系統。</p></div><div class="example"><span>具體例子</span><p>Coding agent 搜尋 repository、修改檔案、跑測試，再依失敗訊息修正。</p></div><div class="relevance"><span>本章位置</span><p>Agent 增加速度與自治，也帶來 excessive agency、秘密外洩與不可預測操作等新風險。</p></div></section><section class="term-card"><h3>Context engineering</h3><div><span>白話定義</span><p>設計模型在做決策時能看見哪些規格、程式碼、文件、工具結果與限制。</p></div><div class="example"><span>具體例子</span><p>只說『修 bug』通常不足；提供重現步驟、相關 module、測試命令和完成條件更可靠。</p></div><div class="relevance"><span>本章位置</span><p>AI 時代的文件、repository 結構與工具輸出同時服務人類與 agent。</p></div></section><section class="term-card"><h3>Eval（評估）</h3><div><span>白話定義</span><p>以可重複資料和評分規則，量測 AI 系統是否完成目標、遵守限制並安全失敗。</p></div><div class="example"><span>具體例子</span><p>除了答案正確率，也檢查 agent 是否用了禁止的工具、是否引用正確來源。</p></div><div class="relevance"><span>本章位置</span><p>Eval 是 AI 版本的 executable specification；沒有 eval 就無法知道模型或 prompt 更新是否退步。</p></div></section></div>

## 為什麼需要這一章？

工程討論很容易因同一個詞代表不同層級而失焦。例如「服務掛了」可能是 process 已退出、API error rate 上升、dependency timeout，或只是某個使用者流程失敗；「AI 幫我修」也可能只是補全一行，或是具備 shell、Git 和 production 工具的自治 agent。本章先把後文常用物件與邊界定義清楚。

### 真實 Use Case

我們建立一個 `/quote` API：client 傳入商品與數量，service 讀取 catalog dependency，計算價格並回覆。接著讓 coding agent 修正折扣 bug。這個小場景同時包含 request、state、dependency、test、deployment、telemetry、context 和 tool permission。

<div class="context-grid">
<section><span>問題壓力</span><p>工程討論很容易因同一個詞代表不同層級而失焦。例如「服務掛了」可能是 process 已退出、API error rate 上升、dependency timeout，或只是某個使用者流程失敗；「AI 幫我修」也可能只是補全一行，或是具備 shell、Git 和 production 工具的自治 agent。本章先把後文常用物件與邊界定義清楚。</p></section>
<section><span>交付能力</span><p>用一個最小服務拆清楚 request、state、dependency、deployment、telemetry，以及 AI agent 的 observe–act loop。</p></section>
<section><span>真實場景</span><p>我們建立一個 <code>/quote</code> API：client 傳入商品與數量，service 讀取 catalog dependency，計算價格並回覆。接著讓 coding agent 修正折扣 bug。這個小場景同時包含 request、state、dependency、test、deployment、telemetry、context 和 tool permission。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Client ──request──&gt; Quote Service ──query──&gt; Catalog
   ▲                     │                    │
   └────response─────────┘                    │
                         ├─ process memory     │
                         ├─ database state &lt;───┘
                         └─ logs / metrics / traces

Human intent
   ↓
[Agent: observe → reason/plan → tool call → observe]
   │       context: code + docs + test output
   └────── tools: search / edit / test / git</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Service 是一個責任邊界，不等同單一 process 或機器。它可能有多個 replicas、資料庫、queue 和外部 dependencies，但對 client 提供一組相對穩定的 contract。Request 是一次互動，state 是跨互動保存的事實，deployment 則是把特定 artifact 與 configuration 放入某個 environment 的動作。

Telemetry 是系統主動留下的可觀察輸出；feedback 則要更進一步，讓輸出改變決策。例如 log 存在但沒有人或工具讀取，就不是有效 feedback loop。Metrics 適合趨勢與聚合，logs 適合離散事件，traces 適合跨元件因果路徑；三者不是互相取代。

語言模型只會根據目前 context 產生下一步輸出。Agent harness 把模型放進迴圈，提供 tools、記憶、停止條件和權限。Eval 是在多個固定或代表性案例上量測 agent 是否完成任務、遵守 policy 並安全失敗。這些名詞會在後面逐步深化，此處先建立邊界。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>Client 依 API contract 送出 request；service 驗證輸入並建立 request-scoped context。</p></div><div class="flow-card"><span>2</span><p>Service 呼叫 dependency 或讀寫 state，任何跨網路互動都可能慢、失敗或重複。</p></div><div class="flow-card"><span>3</span><p>Response 只代表這次互動的結果；可靠性需聚合大量 valid events 才能判斷。</p></div><div class="flow-card"><span>4</span><p>Deployment 改變 production 正在執行的 artifact/config，telemetry 應能標記這個 change event。</p></div><div class="flow-card"><span>5</span><p>Agent 每次工具呼叫都改變外部世界，因此 harness 必須管理 context、permission、budget 和 stop condition。</p></div></div>

## Coding／實務例子

這個例子同時展示 request handler 與一個極小的 agent loop。Agent 本身不神奇：它只是根據 observation 選 action，工具執行後再取得新的 observation。

```python
from dataclasses import dataclass

CATALOG = {"book": 300, "pen": 20}

def quote(item: str, quantity: int) -> int:
    if item not in CATALOG:
        raise KeyError("unknown item")
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    return CATALOG[item] * quantity

@dataclass
class ToolResult:
    ok: bool
    output: str

def tiny_agent(goal: str, tools: dict):
    observation = f"goal={goal}"
    for step in range(3):                 # 明確的 action budget
        action = "run_tests" if step == 0 else "stop"
        if action == "stop":
            return observation
        result: ToolResult = tools[action]()
        observation = result.output
        if result.ok:
            return "verified: " + observation
    return "budget exhausted"
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p><code>quote</code> 的 contract 包含正常輸出和兩種明確錯誤，這比『回一個數字』更完整。</p></div><div class="flow-card"><span>2</span><p><code>tiny_agent</code> 只有被注入的 tools，模型或策略不能憑空取得其他權限。</p></div><div class="flow-card"><span>3</span><p><code>range(3)</code> 是最小停止條件，避免錯誤 observation 造成無限 tool loop。</p></div><div class="flow-card"><span>4</span><p>成功條件來自 <code>ToolResult.ok</code> 的外部證據，而不是 agent 自己說『應該好了』。</p></div></div>

## Trade-offs 與 Failure Modes

- 把 service 等同 process，會忽略 load balancer、replicas、state 和 dependencies。
- 只收集 telemetry 不建立 owner、threshold 和 action，資料會變成昂貴噪音。
- 把聊天模型稱為 agent，會低估 tool permission 與 side effect 的安全問題。
- Eval 只測快樂路徑，agent 就可能在 timeout、惡意輸入或缺權限時做出危險補救。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 時代最重要的新共同語言是「模型能力」與「系統能力」的分離。模型可能擅長推理，但 agent 是否可靠取決於 context 是否正確、tools 是否設計良好、環境是否隔離、eval 是否代表真實工作，以及失敗時能否停止。這和 service reliability 相似：單一函式正確不代表整個 production path 可靠。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>用 agent 搜尋 codebase 與解釋資料流，但要求列出實際檔案與證據。</li><li>把測試、type checker、API schema 和 policy check 暴露成結構化 tools。</li><li>對重複任務建立 representative eval set，版本更新前後比較結果。</li><li>將 tool trace 與 deployment/incident timeline 串接，知道 AI 做過哪些外部操作。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>區分 read、write、deploy、production mutation 四級 tool 權限，預設從 read-only 開始。</li><li>限制 steps、wall-clock、token、金額與可觸及資源，超限必須安全停止。</li><li>敏感資料進入 context 前先做 ACL、redaction 和 retention 檢查。</li><li>Eval 同時包含正確案例、模糊需求、工具失敗、prompt injection 和拒絕案例。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Domain expert 會先問 agent 的 control plane：誰定義 tool、誰核准權限、誰看 audit、模型故障時如何 fallback。若團隊只能展示漂亮 demo，卻無法回答這四題，系統仍處於實驗階段。反過來，並非所有工作都需要 agent；固定 schema transformation 用普通程式通常更便宜、可預測且易測。

</aside>

## 動手驗證

1. 執行 `quote` 的正常、未知商品、零數量三個案例，寫出每個 contract。
2. 替 `tiny_agent` 加入一個永遠失敗的 tool，確認 budget 能停止迴圈。
3. 畫出你熟悉服務的一個 request path，分別標記 process、service、state 與 dependency。
4. 設計五個 eval cases：正常修復、測試失敗、缺檔案權限、惡意文件指令、超過步驟上限。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Service 為何不等同一台 server？</summary>

服務是對外責任與 contract 的邊界；實作可以跨多個 process、replica、資料庫和區域。一台 server 只是某個時間點的執行資源。

</details>

<details class="qa"><summary>Q2. Telemetry 和 feedback 的差別是什麼？</summary>

Telemetry 是輸出資料；feedback 必須讓資料進入決策並改變行為。沒有 owner、threshold、review 或 automation 的 dashboard，可能只是被動資訊。

</details>

<details class="qa"><summary>Q3. 聊天模型何時才成為 agent？</summary>

當系統讓模型在目標下反覆觀察、規劃、呼叫外部工具、接收結果並決定下一步時，才具有 agentic loop；工具 side effects 使權限和停止條件變得重要。

</details>

<details class="qa"><summary>Q4. 為什麼 deterministic 工作不一定適合 LLM？</summary>

固定規則用普通程式可得到相同輸入必有相同輸出、容易測試且成本低。LLM 適合規則難以完整列舉、需要語意判斷的部分，但應把可確定的檢查留給工具。

</details>

<details class="qa"><summary>Q5. Eval 與一般 unit test 有何異同？</summary>

兩者都提供可重複判斷；但 AI 輸出可能非 deterministic，eval 常需資料集、容忍區間、rubric 或 grader，還要看 tool trajectory 和 policy compliance。

</details>

<details class="qa"><summary>Q6. Agent 的 step limit 能解決所有失控問題嗎？</summary>

不能。它只限制一次迴圈長度，仍需 resource quota、tool scope、idempotency、approval 和 audit；三步內也可能做出高破壞操作。

</details>

<details class="qa"><summary>Q7. 本章應保留的最小 agent 模型是什麼？</summary>

Agent = model decision + bounded context + explicit tools + observe/act loop + stop conditions + verification + audit。少了任何一項，都要清楚知道風險由哪裡承擔。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Introduction](https://sre.google/sre-book/introduction/)
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)
- [OpenAI — Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)
- [OWASP — Top 10 for LLM Applications 2025](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

---
