---
title: "Software Engineering 的根基"
part: 1
as_of: 2026-09-30
---

# Part 1　Software Engineering 的根基

把程式放進時間、規模與成本中思考，理解為何今天能跑不等於多年後仍可安全改動。

# 第 3 章　Programming 與 Software Engineering 的差別

<p class="chapter-question">為什麼會寫出正確程式，仍不足以設計一個可由團隊維護十年的系統？</p>

<div class="chapter-meta"><span>難度：入門</span><span>Part 1 · Software Engineering 的根基</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

學會把『現在可運行』擴張成『在時間、團隊與環境改變後仍可理解、修改和營運』。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node active"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-02-共同語言-service-feedback-與-ai-agent"><span>上一站</span><strong>02. 共同語言：Service、Feedback 與 AI Agent</strong></a><div class="position-card current"><span>你在這裡</span><strong>03. Programming 與 Software Engineering 的差別</strong></div><a class="position-card" href="#chapter-04-time-and-change-軟體為什麼會老化"><span>下一站</span><strong>04. Time and Change：軟體為什麼會老化</strong></a></div>

本章位於 **Part 1：Software Engineering 的根基**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Software（軟體）</h3><div><span>白話定義</span><p>可被電腦執行的指令、資料與設定；真正的產品還包括部署方式、依賴、監控和操作流程。</p></div><div class="example"><span>具體例子</span><p>一個 Python 檔可以運算價格，但沒有資料庫 migration、部署與告警時，還不是可長期營運的服務。</p></div><div class="relevance"><span>本章位置</span><p>本書把 code 放回完整生命週期，避免把『寫完函式』誤認為『工程完成』。</p></div></section><section class="term-card"><h3>Lifecycle（生命週期）</h3><div><span>白話定義</span><p>一項變更從需求、設計、實作、驗證、發布、運行到淘汰的完整時間線。</p></div><div class="example"><span>具體例子</span><p>新增欄位不只改 schema，還要 migration、雙讀寫、監控、清除舊格式。</p></div><div class="relevance"><span>本章位置</span><p>SWE 管理變更的長期成本；SRE 管理變更進入 production 後的風險。</p></div></section><section class="term-card"><h3>Constraint（限制條件）</h3><div><span>白話定義</span><p>解法必須遵守的硬邊界，例如延遲、相容性、預算、法規或權限。</p></div><div class="example"><span>具體例子</span><p>登入 API p99 必須低於 300ms，而且舊手機版本仍能使用。</p></div><div class="relevance"><span>本章位置</span><p>工程取捨必須先知道 constraint；AI agent 也需要把它寫進完成條件。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section></div>

## 為什麼需要這一章？

Programming 通常聚焦把目前問題轉成可執行演算法；software engineering 還必須處理需求會變、呼叫者未知、團隊會換人、依賴會升級、硬體與法規會改變。若只優化當下寫法，未來每次變更都可能增加不可見的協調成本，直到系統再也不敢改。

### 真實 Use Case

一位工程師用 80 行 script 每天匯入報表，最初非常成功。半年後它成為營運關鍵流程：五個團隊依賴欄位順序、密碼寫在筆電、失敗無告警、作者休假便沒人敢動。演算法沒有錯，但軟體工程系統不存在。

<div class="context-grid">
<section><span>問題壓力</span><p>Programming 通常聚焦把目前問題轉成可執行演算法；software engineering 還必須處理需求會變、呼叫者未知、團隊會換人、依賴會升級、硬體與法規會改變。若只優化當下寫法，未來每次變更都可能增加不可見的協調成本，直到系統再也不敢改。</p></section>
<section><span>交付能力</span><p>學會把『現在可運行』擴張成『在時間、團隊與環境改變後仍可理解、修改和營運』。</p></section>
<section><span>真實場景</span><p>一位工程師用 80 行 script 每天匯入報表，最初非常成功。半年後它成為營運關鍵流程：五個團隊依賴欄位順序、密碼寫在筆電、失敗無告警、作者休假便沒人敢動。演算法沒有錯，但軟體工程系統不存在。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Programming
problem → algorithm → code → output

Software Engineering
problem + changing constraints
   ↓
architecture + ownership + contracts
   ↓
code + tests + docs + build + rollout + telemetry
   ↓
operate / migrate / deprecate / learn
   └───────────────────────────────→ future changes</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

兩者不是高低之分，而是積分範圍不同。短命、單人、可丟棄的程式可能只需要 programming；一旦輸出被其他人依賴、程式要跨時間維護，工程問題便出現。最常見的錯誤是系統已變成基礎設施，團隊仍以一次性 script 的治理方式對待。

工程化的核心不是加入更多文件或會議，而是讓重要假設顯式、讓風險有 owner、讓修改有快速 evidence。測試保護 behavior，API contract 管理邊界，version control 保存歷史，CI 縮短 feedback，SLO 對齊使用者結果。每項機制都應能回答它降低哪種未來成本。

因此「最佳實務」不能脫離壽命與規模。兩週後刪除的 prototype 不值得建立全球多區部署；處理薪資十年的服務則不應依賴作者記憶。資深判斷在於辨識軟體何時跨過工程化門檻，以及採用足夠而不過度的機制。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>先估計軟體壽命、使用者、修改者、資料價值和故障影響。</p></div><div class="flow-card"><span>2</span><p>列出最可能改變的 assumptions，為高成本變化建立 contract 或 seam。</p></div><div class="flow-card"><span>3</span><p>建立最小 ownership、version control、test、deployment 和 telemetry。</p></div><div class="flow-card"><span>4</span><p>隨依賴與影響擴大，逐步增加 review、rollout、SLO 和 incident 機制。</p></div><div class="flow-card"><span>5</span><p>定期重新評估：prototype 可能升級為產品，舊產品也可能應該被淘汰。</p></div></div>

## Coding／實務例子

以下用同一個資料轉換示範 script 與可維護 component 的差別。後者沒有更聰明的演算法，但把 contract、錯誤和變更點顯式化。

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class LineItem:
    sku: str
    quantity: int
    unit_price: Decimal

def invoice_total(items: list[LineItem]) -> Decimal:
    # Return total; reject invalid business state explicitly.
    total = Decimal("0")
    for item in items:
        if item.quantity <= 0:
            raise ValueError(f"{item.sku}: quantity must be positive")
        if item.unit_price < 0:
            raise ValueError(f"{item.sku}: price cannot be negative")
        total += item.unit_price * item.quantity
    return total
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p><code>Decimal</code> 表達金額 constraint，避免 binary float 的隱性誤差。</p></div><div class="flow-card"><span>2</span><p><code>LineItem</code> 把欄位名稱與型別變成 contract，不依賴位置神秘的 list。</p></div><div class="flow-card"><span>3</span><p>Invalid state 立即失敗並帶 context，呼叫者可監控而非得到錯價。</p></div><div class="flow-card"><span>4</span><p>Docstring 和 type hints 同時幫助人、static tool 與 coding agent理解邊界。</p></div></div>

## Trade-offs 與 Failure Modes

- 過早工程化會延長探索週期，使尚未確認的需求被錯誤抽象固定。
- 完全不工程化會讓成功 prototype 在依賴增加後突然成為高風險 legacy。
- 抽象越多不等於越可維護；錯誤抽象會把不相關變化綁在一起。
- 只補文件不補 executable checks，文件可能很快與真實行為分離。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 讓產生可運行 prototype 的成本大幅下降，因此 programming 到 engineering 之間的落差反而更危險。Demo 可能在一天內吸引使用者，卻沒有 owner、security、migration 或 observability。另一方面，AI 也能降低補齊 tests、docs、codemods 和 runbooks 的成本；關鍵是把它用於建立長期 feedback，而非只追求第一版速度。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 先列出需求中的 assumptions、external consumers 和 failure modes。</li><li>請 agent 在實作前提出最小 contract 與驗證計畫，再生成 code。</li><li>用 AI 將成功 prototype 盤點成 production-readiness backlog。</li><li>定期用 agent 搜尋重複邏輯、孤兒程式、無 owner job 和失效文件候選。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Prototype 升 production 前必須經 security、data、ownership 和 rollback review。</li><li>AI 生成的 abstraction 需以目前至少兩個真實 use cases 驗證，避免 speculative design。</li><li>禁止以『模型已解釋』取代 tests、type checks 和實際執行證據。</li><li>對快速生成的臨時工具設定 owner、expiry date 和資料處理邊界。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

成熟團隊會建立「graduation path」而非禁止 prototype：探索期允許低 ceremony，但一旦觸及真實資料、多人依賴或值班責任，就必須升級 contract、tests、deployment 和 ownership。AI 時代最昂貴的不是寫 code，而是讓大量無治理的成功實驗悄悄變成永久系統。

</aside>

## 動手驗證

1. 挑一個現有 script，列出它的使用者、資料、執行頻率、失敗影響和單點知識。
2. 執行範例並新增一個稅率需求，觀察哪個介面需要改變。
3. 為 prototype 定義三個 graduation triggers，例如真實個資、第二位使用者、每日排程。
4. 請 AI 為同一需求生成 prototype plan 與 production plan，比較多出的工程責任。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Programming 與 software engineering 最核心差異是什麼？</summary>

Programming 解決目前計算問題；software engineering 把程式放進時間、多人協作、部署和營運中，管理持續修改的成本與風險。

</details>

<details class="qa"><summary>Q2. 何時一次性 script 開始需要工程化？</summary>

當它被多人或關鍵流程依賴、處理重要資料、需要長期運行、作者不再是唯一操作者，或失敗會有顯著影響時。

</details>

<details class="qa"><summary>Q3. 為什麼更多 abstraction 不必然更好？</summary>

抽象本身增加間接層和學習成本；若變化軸判斷錯誤，反而把不同需求綁死。應以真實重複與穩定 contract 驅動。

</details>

<details class="qa"><summary>Q4. 文件為何不能取代 executable checks？</summary>

文件可能過時且不會阻止錯誤進入主線；test、type 和 schema 能在每次變更自動驗證。兩者互補：文件解釋意圖，checks 保護可機械判斷的規則。

</details>

<details class="qa"><summary>Q5. AI 為何同時縮短與擴大 engineering gap？</summary>

它讓 prototype 更快，也能協助補 tests/docs；若組織只獎勵 demo 速度，無治理 code 會更快累積。若流程要求 evidence，AI 則能降低建立 evidence 的成本。

</details>

<details class="qa"><summary>Q6. 如何避免 production-readiness 變成沉重官僚？</summary>

依風險分級，使用自動 checks 和預設平台，讓低風險服務走短路徑；只有資料、權限、不可逆 migration 等高風險項目需要深度 review。

</details>

<details class="qa"><summary>Q7. 本章的專家判斷題是什麼？</summary>

不是『是否遵守所有最佳實務』，而是『這個軟體的壽命、依賴與影響是否已要求更多可重複 evidence，而且目前機制是否正好足夠』。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Preface](https://abseil.io/resources/swe-book/html/pr01.html)
- [Site Reliability Engineering — Introduction](https://sre.google/sre-book/introduction/)
- [DORA 2025 — AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)

---

# 第 4 章　Time and Change：軟體為什麼會老化

<p class="chapter-question">程式碼不會像食物腐敗，為什麼一個多年沒改的系統仍會逐漸變得危險？</p>

<div class="chapter-meta"><span>難度：初階</span><span>Part 1 · Software Engineering 的根基</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

看懂軟體老化其實是環境、需求、依賴與知識改變，並學會設計可遷移而非永遠不變的系統。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node active"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-03-programming-與-software-engineering-的差別"><span>上一站</span><strong>03. Programming 與 Software Engineering 的差別</strong></a><div class="position-card current"><span>你在這裡</span><strong>04. Time and Change：軟體為什麼會老化</strong></div><a class="position-card" href="#chapter-05-hyrum-s-law-所有可觀察行為都可能成為依賴"><span>下一站</span><strong>05. Hyrum’s Law：所有可觀察行為都可能成為依賴</strong></a></div>

本章位於 **Part 1：Software Engineering 的根基**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Lifecycle（生命週期）</h3><div><span>白話定義</span><p>一項變更從需求、設計、實作、驗證、發布、運行到淘汰的完整時間線。</p></div><div class="example"><span>具體例子</span><p>新增欄位不只改 schema，還要 migration、雙讀寫、監控、清除舊格式。</p></div><div class="relevance"><span>本章位置</span><p>SWE 管理變更的長期成本；SRE 管理變更進入 production 後的風險。</p></div></section><section class="term-card"><h3>Backward compatibility</h3><div><span>白話定義</span><p>新版本仍能服務舊呼叫者、舊資料或舊協定的能力。</p></div><div class="example"><span>具體例子</span><p>新增 optional JSON field 通常相容；把字串改為物件可能使舊 client 崩潰。</p></div><div class="relevance"><span>本章位置</span><p>大型系統無法原子更新所有使用者，因而需要 migration window。</p></div></section><section class="term-card"><h3>Coupling（耦合）</h3><div><span>白話定義</span><p>一個元件改變時，另一個元件也必須跟著改變的程度。</p></div><div class="example"><span>具體例子</span><p>前端直接依賴資料庫欄位名稱，使 schema rename 同時破壞 UI。</p></div><div class="relevance"><span>本章位置</span><p>Sustainable design 會讓必要耦合顯式化，並降低偶然耦合。</p></div></section><section class="term-card"><h3>Invariant（不變條件）</h3><div><span>白話定義</span><p>系統任何合法狀態都必須成立的規則。</p></div><div class="example"><span>具體例子</span><p>銀行轉帳前後，所有帳戶餘額總和不應憑空增加。</p></div><div class="relevance"><span>本章位置</span><p>測試、型別和監控常用來保護 invariant；它比描述每一行實作更穩定。</p></div></section></div>

## 為什麼需要這一章？

軟體 bytes 不會自行磨損，但周圍世界會動：作業系統停止支援、憑證算法淘汰、客戶行為改變、資料量增長、法律更新、原作者離開。當系統假設與現實的距離增加，每次修改都更難預測，這就是實務上的 software aging。

### 真實 Use Case

十年前的帳號欄位假設 email 永遠唯一且不可變。公司後來支援企業 SSO、帳號合併和隱私刪除；原本看似合理的 primary key 變成每個 migration 都要繞過的歷史約束。

<div class="context-grid">
<section><span>問題壓力</span><p>軟體 bytes 不會自行磨損，但周圍世界會動：作業系統停止支援、憑證算法淘汰、客戶行為改變、資料量增長、法律更新、原作者離開。當系統假設與現實的距離增加，每次修改都更難預測，這就是實務上的 software aging。</p></section>
<section><span>交付能力</span><p>看懂軟體老化其實是環境、需求、依賴與知識改變，並學會設計可遷移而非永遠不變的系統。</p></section>
<section><span>真實場景</span><p>十年前的帳號欄位假設 email 永遠唯一且不可變。公司後來支援企業 SSO、帳號合併和隱私刪除；原本看似合理的 primary key 變成每個 migration 都要繞過的歷史約束。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>時間 t0                    時間 t1
需求 A                     需求 A + B
依賴 v1      ───────→      依賴 v4
資料 10 GB                 資料 20 TB
作者在團隊                 作者已離開
威脅模型 X                 威脅模型 X + Y

若 assumptions 未顯式化：
現實變化 → hidden mismatch → workaround → coupling → 更難改

健康路徑：
signal → compatibility window → migration → cleanup</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

時間問題可以拆成四類。External change 是平台、法規與依賴變動；requirement change 是產品需要不同能力；scale change 是原本可接受的演算法或操作超過容量；knowledge change 是團隊失去設計原因。它們都會讓當初正確的決策失去前提。

可維護性不是預先猜中所有未來，而是降低錯誤猜測的代價。清楚 contract 限制耦合，observability 看見舊路徑仍有誰使用，migration 將大改動拆成可共存階段，deprecation 最終清除舊成本。只加 abstraction 卻不安排 cleanup，會讓系統永久同時背負每一代設計。

時間也改變風險計算。暫時 workaround 若有 owner、期限和移除條件，可以是合理取捨；沒有這些資訊，它就會被後人誤認為必要架構。設計文件和 ADR 的價值是保存 constraint 與決策，不是描述每一行 code。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>辨認設計依賴的 assumptions，區分哪些是 contract、哪些只是目前實作。</p></div><div class="flow-card"><span>2</span><p>為不可原子切換的改動設計 expand、migrate、contract 三階段。</p></div><div class="flow-card"><span>3</span><p>加入 telemetry，量測舊版本、舊欄位和舊 API 的剩餘使用量。</p></div><div class="flow-card"><span>4</span><p>設定 owner、deadline 和 rollback，使暫時相容層不會永久化。</p></div><div class="flow-card"><span>5</span><p>遷移完成後刪除舊 code、flags、metrics 和文件，真正降低複雜度。</p></div></div>

## Coding／實務例子

範例示範 schema evolution：先接受新舊輸入，再逐步把內部表示統一，最後才移除舊格式。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class UserName:
    given: str
    family: str

def parse_name(payload: dict) -> UserName:
    # 新格式優先；migration window 仍接受舊 full_name。
    if "given_name" in payload and "family_name" in payload:
        return UserName(payload["given_name"], payload["family_name"])
    if "full_name" in payload:
        parts = payload["full_name"].strip().split(maxsplit=1)
        return UserName(parts[0], parts[1] if len(parts) == 2 else "")
    raise ValueError("name is required")
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>函式把兩種外部格式立即轉成單一 internal model，避免相容性分支污染整個 codebase。</p></div><div class="flow-card"><span>2</span><p>舊格式 parser 是有期限的 migration layer，不應成為永遠支援的第二套 domain model。</p></div><div class="flow-card"><span>3</span><p>Production 應記錄舊格式使用量，但避免把姓名等敏感資料寫入 log。</p></div><div class="flow-card"><span>4</span><p>只有使用量歸零並經過安全窗口後，才能刪除 <code>full_name</code> 分支。</p></div></div>

## Trade-offs 與 Failure Modes

- 永久同時支援新舊行為會讓測試組合與認知成本持續成長。
- Big-bang migration 簡單但要求所有 producer/consumer 同時更新，通常不適合分散式組織。
- 過度兼容錯誤輸入可能把資料品質問題隱藏到更深層。
- 只看 repository 搜尋結果會漏掉舊 binary、外部客戶、資料檔與未連線裝置。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 能快速產生 code，也會讓 codebase 的變更頻率、重複方案與局部 workaround 增加。長期健康更依賴 machine-readable contracts、版本化文件、可搜尋 decision history 和自動 cleanup signal。Agent 可能從 repository 模仿已過期 pattern，因此 context 必須標明 canonical path、deprecated APIs 和 migration 狀態，而不能假設它自然知道最新設計。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 盤點某 API 的 producers、consumers、schemas、tests 和 documents。</li><li>請 agent 草擬 expand–migrate–contract plan，列出每階段的 rollback 與 telemetry。</li><li>用 AI 搜尋過期 flags、TODO、deprecated call sites，再由 owner 確認刪除。</li><li>讓 AI 比較 ADR 與目前 code，產生可能 drift 的候選清單。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Migration plan 必須以實際 telemetry 驗證，不能只信 agent 的 repository 搜尋。</li><li>Codemod 前先鎖定 AST pattern、建立 dry-run diff 和代表性 tests。</li><li>Deprecated path 在 agent instructions 中明確標記禁止新使用。</li><li>任何自動 cleanup 必須有 owner、可逆 commit 與資料保留檢查。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

真正的時間尺度設計通常不是追求『future-proof』，而是投資在 observability、compatibility seam 和 migration discipline。因為未來不可預測，最有價值的能力是讓錯誤假設可以被發現、局部替換並最終清除。AI 會使修改便宜，但不會使協調與資料相容性自動消失。

</aside>

## 動手驗證

1. 列出一個舊系統的五個原始 assumptions，標記目前是否仍成立。
2. 執行範例，增加第三種 `display_name` 格式，設計不讓分支擴散的方法。
3. 為 `full_name` deprecation 寫三個 metrics：總流量、舊格式比例、最後使用者群。
4. 請 AI 生成 migration plan，再人工找出 repository 之外它可能漏掉的 consumers。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. 軟體為何會老化？</summary>

程式本身不磨損，但需求、依賴、資料規模、威脅和團隊知識會改變。原始 assumptions 與現實的差距使維護風險上升。

</details>

<details class="qa"><summary>Q2. 可維護性是否代表預測所有未來需求？</summary>

不是。它代表建立清楚邊界、feedback、migration 和 cleanup 能力，讓無法預測的變化仍能以可控成本處理。

</details>

<details class="qa"><summary>Q3. Expand–migrate–contract 各做什麼？</summary>

Expand 先讓系統同時接受新舊世界；migrate 轉移資料和使用者並量測；contract 在證據足夠後移除舊路徑。

</details>

<details class="qa"><summary>Q4. 為什麼 compatibility layer 必須有移除計畫？</summary>

每個額外格式都增加 branch、test matrix 和理解成本。沒有 owner、telemetry、deadline 的暫時層很容易永久化。

</details>

<details class="qa"><summary>Q5. AI 為何可能強化舊 pattern？</summary>

模型根據可見 repository 和文件模仿；若 deprecated code 仍大量存在且沒有標記，它可能把歷史解法當成推薦解法。

</details>

<details class="qa"><summary>Q6. Repository 搜尋何時不足以證明舊 API 無人使用？</summary>

外部客戶、離線裝置、舊部署、動態呼叫、資料檔與反射可能不在目前 source tree，需要 runtime telemetry 和溝通。

</details>

<details class="qa"><summary>Q7. 時間與變更章最重要的設計能力是什麼？</summary>

不是避免所有改動，而是安排可共存、可觀測、可回退且可清理的遷移，使每代設計不必永久疊加。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Preface](https://abseil.io/resources/swe-book/html/pr01.html)
- [Software Engineering at Google — Deprecation](https://abseil.io/resources/swe-book/html/ch15.html)
- [DORA 2025 — AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)

---

# 第 5 章　Hyrum’s Law：所有可觀察行為都可能成為依賴

<p class="chapter-question">即使沒有修改正式 API，為什麼重排 JSON、改錯誤文字或提升速度也可能破壞使用者？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 1 · Software Engineering 的根基</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

分清 declared contract、observable behavior 和 accidental dependency，並用 consumer evidence 管理相容性。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node active"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-04-time-and-change-軟體為什麼會老化"><span>上一站</span><strong>04. Time and Change：軟體為什麼會老化</strong></a><div class="position-card current"><span>你在這裡</span><strong>05. Hyrum’s Law：所有可觀察行為都可能成為依賴</strong></div><a class="position-card" href="#chapter-06-scale-and-growth-規模如何改變問題"><span>下一站</span><strong>06. Scale and Growth：規模如何改變問題</strong></a></div>

本章位於 **Part 1：Software Engineering 的根基**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>API Contract</h3><div><span>白話定義</span><p>元件對外承諾的輸入、輸出、錯誤、狀態與相容性規則。</p></div><div class="example"><span>具體例子</span><p><code>get_user(id)</code> 找不到資料時回 <code>None</code> 還是拋 exception，都是 contract。</p></div><div class="relevance"><span>本章位置</span><p>清楚 contract 讓團隊與 agent 能在不理解所有內部細節時安全組合元件。</p></div></section><section class="term-card"><h3>Backward compatibility</h3><div><span>白話定義</span><p>新版本仍能服務舊呼叫者、舊資料或舊協定的能力。</p></div><div class="example"><span>具體例子</span><p>新增 optional JSON field 通常相容；把字串改為物件可能使舊 client 崩潰。</p></div><div class="relevance"><span>本章位置</span><p>大型系統無法原子更新所有使用者，因而需要 migration window。</p></div></section><section class="term-card"><h3>Invariant（不變條件）</h3><div><span>白話定義</span><p>系統任何合法狀態都必須成立的規則。</p></div><div class="example"><span>具體例子</span><p>銀行轉帳前後，所有帳戶餘額總和不應憑空增加。</p></div><div class="relevance"><span>本章位置</span><p>測試、型別和監控常用來保護 invariant；它比描述每一行實作更穩定。</p></div></section><section class="term-card"><h3>Test oracle</h3><div><span>白話定義</span><p>判斷某次執行結果是否正確的規則或已知答案。</p></div><div class="example"><span>具體例子</span><p>排序後必須單調且包含相同元素，比只比對一個範例更完整。</p></div><div class="relevance"><span>本章位置</span><p>Agent 只有在 oracle 明確時才能自主迭代，否則可能把錯誤輸出合理化。</p></div></section></div>

## 為什麼需要這一章？

系統使用者足夠多時，幾乎任何可觀察行為都可能被某人依賴：排序、延遲、錯誤字串、重試次數、未文件化欄位甚至 bug。API 作者心中的 contract 與生態系實際使用的 contract 會逐漸分離，讓『內部重構』意外成為 breaking change。

### 真實 Use Case

搜尋 API 宣稱結果順序未定，但多年來剛好按建立時間回傳。某客戶沒有自己排序，直接顯示第一筆。資料庫換 index 後順序改變，服務 schema 完全相同，使用者畫面卻出錯。

<div class="context-grid">
<section><span>問題壓力</span><p>系統使用者足夠多時，幾乎任何可觀察行為都可能被某人依賴：排序、延遲、錯誤字串、重試次數、未文件化欄位甚至 bug。API 作者心中的 contract 與生態系實際使用的 contract 會逐漸分離，讓『內部重構』意外成為 breaking change。</p></section>
<section><span>交付能力</span><p>分清 declared contract、observable behavior 和 accidental dependency，並用 consumer evidence 管理相容性。</p></section>
<section><span>真實場景</span><p>搜尋 API 宣稱結果順序未定，但多年來剛好按建立時間回傳。某客戶沒有自己排序，直接顯示第一筆。資料庫換 index 後順序改變，服務 schema 完全相同，使用者畫面卻出錯。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Provider
  ├─ declared contract ───────────────┐
  ├─ stable implementation behavior ─┼─→ Consumers observe
  ├─ timing / ordering / errors ──────┤       ↓
  └─ bugs / side effects ─────────────┘   some behavior becomes dependency

安全變更：
inventory consumers → classify behavior → add contract/test
                   or warn/migrate/version → observe → remove</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Contract 有三層。Declared contract 是文件或 schema 承諾；de facto contract 是大量 consumer 已依賴、無法輕易改變的行為；implementation detail 是理論上可改，但仍可能被觀察的現象。Hyrum’s Law 提醒我們不能只靠作者宣告決定後兩者，規模會把可觀察性轉成耦合。

解法不是凍結所有行為，而是降低不必要的可觀察面，並為重要行為提供明確 contract。Response 應避免暴露內部資料結構；錯誤使用 machine-readable code 而非讓 client parse 文字；需要順序就明確指定，不需要就用測試打亂以防 consumer 偷依賴。

相容性決策需要 consumer evidence。Contract tests、usage telemetry、version negotiation、deprecation notice 和 staged rollout 都能縮小未知。Provider test 只能證明自己符合預期，consumer-driven contract 才能發現真實整合假設。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>列出 API 的可觀察面：values、ordering、errors、timing、side effects 和 resource limits。</p></div><div class="flow-card"><span>2</span><p>區分哪些行為應升格為正式 contract，哪些應主動隨機化或隱藏。</p></div><div class="flow-card"><span>3</span><p>建立 provider 與 consumer contract tests，對高風險變更先跑 compatibility suite。</p></div><div class="flow-card"><span>4</span><p>透過 version、feature negotiation 或雙軌輸出安排 migration window。</p></div><div class="flow-card"><span>5</span><p>以 telemetry 和 canary 驗證實際 consumer，而非只靠文件推測。</p></div></div>

## Coding／實務例子

範例刻意把錯誤文字與穩定 error code 分開。Client 應依 code 決策，message 可以改善而不破壞控制流。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ApiError:
    code: str
    message: str
    retryable: bool

def reserve(stock: int, requested: int) -> ApiError | None:
    if requested <= 0:
        return ApiError("INVALID_QUANTITY", "Quantity must be positive", False)
    if requested > stock:
        return ApiError("OUT_OF_STOCK", "Not enough inventory", False)
    return None

def client_action(error: ApiError | None) -> str:
    if error is None:
        return "continue"
    return "retry" if error.retryable else f"show:{error.code}"
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p><code>code</code> 是 machine contract，<code>message</code> 是可以本地化與改善的人類資訊。</p></div><div class="flow-card"><span>2</span><p><code>retryable</code> 把 policy 顯式化，避免每個 consumer 猜哪些錯誤可重試。</p></div><div class="flow-card"><span>3</span><p>若 client 解析 <code>message</code>，哪怕修正文法都可能成為 breaking change。</p></div><div class="flow-card"><span>4</span><p>Contract test 應驗證 code 和 retry semantics，不必鎖死完整英文句子。</p></div></div>

## Trade-offs 與 Failure Modes

- 把所有歷史行為永久化會阻止修 bug、提升效能和簡化系統。
- 只靠 semantic versioning 無法幫助根本不升級或未知的 consumers。
- 過度寬鬆 parser 可能讓無效資料默默擴散，之後更難收緊。
- Latency 改快也可能暴露 race condition，證明 timing 同樣是 observable behavior。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

Coding agent 會大量搜尋並模仿現有 call sites，因此 accidental behavior 可能以更快速度擴散。另一方面，AI 很適合建立 consumer inventory、比較 schemas、產生 compatibility cases 和找 parse-error-string 等脆弱 pattern。關鍵是讓 contract 成為 machine-readable source of truth，避免模型從數量較多但已過期的範例推斷規則。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 agent 搜尋所有 consumers 如何處理 response ordering、errors 和 missing fields。</li><li>用 AI 產生舊版與新版 schema 的 compatibility matrix，再以 contract tests 固化。</li><li>請 AI 找出 parse message、sleep-based timing、依賴 dict order 等 accidental coupling。</li><li>在 API 變更 review 中讓 AI 草擬 consumer impact summary，附實際引用位置。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>AI 找到的 call sites 只是候選集合，必須加上 runtime traffic 和外部 consumer 資料。</li><li>禁止 agent 因測試失敗就擴大 public contract；先判斷測試是否鎖定實作細節。</li><li>Schema、error code 和 compatibility policy 需由 owner 核准並版本化。</li><li>大規模修正先 dry-run、分批 canary，保留快速 revert 和舊版服務路徑。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Domain expert 的重點不是『任何 observable behavior 都不能改』，而是管理 observable surface。越公開、越長壽、consumer 越多的介面，越應以窄 contract、版本策略和 telemetry 投資；單一 repository 內可原子修改的 internal API，則能用大規模變更降低相容成本。

</aside>

## 動手驗證

1. 列出你熟悉 API 的十個 observable behaviors，標記 declared、de facto 或可自由修改。
2. 修改範例中的英文 message，寫一個脆弱 client 與一個正確 client 比較結果。
3. 設計 unordered response 的測試策略，讓 consumer 無法依賴偶然順序。
4. 請 AI 搜尋一個 repository 中解析 exception message 的位置，人工驗證 false positives。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Hyrum’s Law 想提醒什麼？</summary>

當 API 有足夠多使用者，幾乎所有可觀察行為都可能被某人依賴；作者宣告的 contract 不一定等於生態系實際 contract。

</details>

<details class="qa"><summary>Q2. 是否應把所有 accidental behavior 寫入 contract？</summary>

不應。先評估 consumer 影響、合理性和長期成本；可透過 migration 改掉不健康依賴，並減少未來可觀察面。

</details>

<details class="qa"><summary>Q3. Machine-readable error code 為何比文字穩定？</summary>

Code 可被明確版本與測試，文字則需要改善、翻譯且格式易變。控制流依 code，message 才能安全服務人類。

</details>

<details class="qa"><summary>Q4. Consumer-driven contract 提供什麼額外證據？</summary>

它描述真實 consumer 需要的互動，而不只是 provider 自認為提供的行為，能在發布前發現整合假設被破壞。

</details>

<details class="qa"><summary>Q5. 為何效能改善也可能是 breaking change？</summary>

執行順序與 timing 改變可能暴露 race、改變 timeout/retry 或讓依賴舊批次行為的 consumer 出錯。Timing 也是 observable surface。

</details>

<details class="qa"><summary>Q6. AI 如何同時增加與降低 Hyrum 風險？</summary>

它會快速複製現有 accidental pattern，也能更快盤點 consumers 和產生 compatibility tests。結果取決於是否有 canonical contract 與驗證。

</details>

<details class="qa"><summary>Q7. Internal API 與 public API 的策略為何不同？</summary>

Internal API 若所有 consumers 可同一變更原子更新，可用大規模修改降低相容負擔；public API 無法控制更新時間，需要版本、deprecation 和長 compatibility window。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Preface](https://abseil.io/resources/swe-book/html/pr01.html)
- [Software Engineering at Google — Deprecation](https://abseil.io/resources/swe-book/html/ch15.html)
- [Software Engineering at Google — Large-Scale Changes](https://abseil.io/resources/swe-book/html/ch22.html)
- [GitHub — Review AI-generated code](https://docs.github.com/copilot/tutorials/review-ai-generated-code)

---

# 第 6 章　Scale and Growth：規模如何改變問題

<p class="chapter-question">為什麼十人團隊有效的做法，搬到一千人或十年 codebase 後可能完全失效？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 1 · Software Engineering 的根基</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

從 code、traffic、data、organization、time 五種規模辨認相變，避免只做線性擴容。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node active"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-05-hyrum-s-law-所有可觀察行為都可能成為依賴"><span>上一站</span><strong>05. Hyrum’s Law：所有可觀察行為都可能成為依賴</strong></a><div class="position-card current"><span>你在這裡</span><strong>06. Scale and Growth：規模如何改變問題</strong></div><a class="position-card" href="#chapter-07-trade-offs-costs-與-architecture-decision-records"><span>下一站</span><strong>07. Trade-offs、Costs 與 Architecture Decision Records</strong></a></div>

本章位於 **Part 1：Software Engineering 的根基**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Scale（規模）</h3><div><span>白話定義</span><p>程式碼量、資料量、請求量、團隊數或系統存活時間增加後出現的新約束。</p></div><div class="example"><span>具體例子</span><p>十人可口頭協調；一千人需要可搜尋文件、標準化 review 與自動 policy。</p></div><div class="relevance"><span>本章位置</span><p>Scale 不是單純把數字放大，常會改變最適合的架構與流程。</p></div></section><section class="term-card"><h3>Coupling（耦合）</h3><div><span>白話定義</span><p>一個元件改變時，另一個元件也必須跟著改變的程度。</p></div><div class="example"><span>具體例子</span><p>前端直接依賴資料庫欄位名稱，使 schema rename 同時破壞 UI。</p></div><div class="relevance"><span>本章位置</span><p>Sustainable design 會讓必要耦合顯式化，並降低偶然耦合。</p></div></section><section class="term-card"><h3>Ownership</h3><div><span>白話定義</span><p>對元件品質、決策、值班與改善負最終責任的明確主體。</p></div><div class="example"><span>具體例子</span><p>平台組維護 deployment API；服務組仍對自己設定錯誤造成的事故負責。</p></div><div class="relevance"><span>本章位置</span><p>AI 可以執行工作但不能承擔組織責任，因此 ownership 不可寫成『模型』。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section></div>

## 為什麼需要這一章？

規模不只是伺服器數量。當 repository、團隊、資料、請求與時間增加，原本可依賴的人腦同步、全量測試、手動發布和單一 owner 會超過負荷。問題常發生相變：不是慢一點而已，而是協調模型、資料結構或失敗模式根本不同。

### 真實 Use Case

五人團隊可在聊天室通知 API 修改；五百個 consumers 時訊息一定漏接。每天十次部署可人工看 dashboard；每小時數千個 agent changes 時，沒有自動 risk classification 和 policy gates 就無法運作。

<div class="context-grid">
<section><span>問題壓力</span><p>規模不只是伺服器數量。當 repository、團隊、資料、請求與時間增加，原本可依賴的人腦同步、全量測試、手動發布和單一 owner 會超過負荷。問題常發生相變：不是慢一點而已，而是協調模型、資料結構或失敗模式根本不同。</p></section>
<section><span>交付能力</span><p>從 code、traffic、data、organization、time 五種規模辨認相變，避免只做線性擴容。</p></section>
<section><span>真實場景</span><p>五人團隊可在聊天室通知 API 修改；五百個 consumers 時訊息一定漏接。每天十次部署可人工看 dashboard；每小時數千個 agent changes 時，沒有自動 risk classification 和 policy gates 就無法運作。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>規模維度
  code ─────→ search / ownership / modularity / codemod
  people ───→ docs / review policy / platform / governance
  traffic ──→ load balance / capacity / overload control
  data ─────→ partition / migration / integrity / retention
  time ─────→ compatibility / deprecation / knowledge preservation

局部最佳化 × 高耦合
        ↓
coordination edges 約隨參與者快速增加
        ↓
需要自助平台、標準介面與自動 feedback</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

第一步是辨認正在成長的維度，因為解法不同。Traffic scale 可能需要 horizontal replication；organizational scale 需要 ownership 和標準介面；code scale 需要 search、build graph 和 automated refactoring；time scale 需要 migration discipline。用 Kubernetes 解知識孤島，不會有效。

成長最昂貴的是 coordination edges。每個團隊若都必須與所有其他團隊同步，關係數會快速增加。平台、API contract、style、review 和 self-service tools 的目的，是把多對多協調壓縮成穩定介面。標準化會犧牲局部自由，但換得整體可組合性。

Scale 也要求分層 feedback。小系統可每次跑全部測試；巨大 codebase 需要 dependency graph、test selection 與 post-submit verification。小流量可人工觀察；大流量需 SLO、aggregation 和 automation。關鍵不是追求最大規模方案，而是在接近轉折點前建立下一層能力。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>分別量測 code、people、traffic、data 和 time，而非只用『系統很大』描述。</p></div><div class="flow-card"><span>2</span><p>找出目前依賴人腦同步或全域鎖步的 coordination bottleneck。</p></div><div class="flow-card"><span>3</span><p>以 stable interface、ownership 和 self-service platform 減少多對多溝通。</p></div><div class="flow-card"><span>4</span><p>建立分層 feedback：快速局部 checks 加較慢全域 verification。</p></div><div class="flow-card"><span>5</span><p>保留 escape hatch 與例外治理，避免標準平台阻止真正特殊需求。</p></div></div>

## Coding／實務例子

小模型計算團隊溝通邊數。它不是組織定律，但能直觀看出全連接協調為何不可持續。

```python
def coordination_edges(teams: int) -> int:
    return teams * (teams - 1) // 2

for n in (5, 20, 100):
    print(f"{n:>3} teams -> {coordination_edges(n):>5} possible edges")

# 以平台介面取代所有 pairwise 協調：
def platform_edges(teams: int, platform_teams: int = 1) -> int:
    return teams * platform_teams
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>五個團隊只有十條可能關係，人際同步仍可工作。</p></div><div class="flow-card"><span>2</span><p>一百個團隊有 4,950 條 pairwise edges，任何全員口頭協議都會漏失。</p></div><div class="flow-card"><span>3</span><p>共同平台把多數協調改成團隊對穩定介面的關係，接近線性。</p></div><div class="flow-card"><span>4</span><p>平台本身成為關鍵 dependency，因此必須有 SLO、版本與使用者研究。</p></div></div>

## Trade-offs 與 Failure Modes

- 過早建立通用平台可能抽象尚未穩定的需求，成為另一個瓶頸。
- 標準化若沒有 escape hatch，特殊工作會建立 shadow system 繞過治理。
- 只擴機器不降低 coupling，部署和事故 blast radius 仍會成長。
- 把 headcount 或 code lines 當價值，會鼓勵增加規模而非降低必要複雜度。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 提高個人產出後，organization scale 的瓶頸更快從撰寫轉到 review、shared context、platform capacity 和 decision coherence。若每個 agent 都生成自己的 library、framework 和操作方式，局部速度會轉成全域碎片化。業界較成熟的方向是提供共用 agent instructions、標準 tools、內部平台和小批次變更，讓速度沿相同 guardrails 流動。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>用 AI 建立跨 repository dependency 和 ownership 地圖。</li><li>將公司標準封裝成 formatter、policy check、scaffold 和 agent tool。</li><li>讓 agent 依 dependency graph 選 relevant tests，縮短大型 codebase feedback。</li><li>用 AI 摘要跨團隊 change impact，但由 service owners 確認 contract。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>限制 agent 建立新 dependency 或 framework，要求先搜尋 canonical solution。</li><li>平台工具必須版本化、有 SLO、fallback，且不能把所有 production 權限集中給模型。</li><li>變更維持 small batch；產碼更快不能成為巨大 PR 的理由。</li><li>衡量 rework、review queue、duplication 和 incidents，監控 AI 是否放大 coordination cost。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

真正的 scale 技巧是刪除協調，而不是更努力協調。穩定 API、單一 canonical tool、自助平台和清楚 ownership 都是在減少必須同時知道全部細節的人數。但平台不能只服務治理者；若使用者體驗差，團隊會繞路，組織便同時支付官方和 shadow system 兩套成本。

</aside>

## 動手驗證

1. 計算你所在組織可能的 team edges，列出最常見的三種跨團隊同步。
2. 為其中一種同步設計 stable interface 或 self-service workflow。
3. 找一個大型 PR，嘗試拆成五個可獨立驗證、可回退的小變更。
4. 請 AI 搜尋 repository 中功能相似的三個 library，分析整併前需要哪些 owner 證據。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Scale 為何不是單一數字？</summary>

Code、people、traffic、data 和 time 各自產生不同 constraint；必須先辨認哪個維度成長，才知道需要平台、分片、相容或容量方案。

</details>

<details class="qa"><summary>Q2. 為何 pairwise coordination 不可持續？</summary>

參與者增加時可能關係快速增加，人腦和同步會議無法可靠覆蓋。穩定介面與平台能將多對多改成較少的標準關係。

</details>

<details class="qa"><summary>Q3. 平台如何同時降低與增加成本？</summary>

它降低重複建設和協調，但本身成為 dependency、治理與學習成本。只有當共同需求穩定且使用者體驗好時，收益才會超過成本。

</details>

<details class="qa"><summary>Q4. 大型 codebase 為何需要分層測試？</summary>

每次全量執行可能太慢；依 dependency graph 先跑快速 relevant tests，再由 post-submit 或週期工作補全域 coverage，可以兼顧速度與風險。

</details>

<details class="qa"><summary>Q5. AI 為何可能讓 codebase 更碎片化？</summary>

產生新 helper 或 library 很便宜，agent 若不知道 canonical path，就會為每個局部問題創造另一套方案，增加 dependency 和認知成本。

</details>

<details class="qa"><summary>Q6. 如何知道團隊接近 scale 轉折點？</summary>

觀察 review queue、等待時間、重複工具、跨團隊 incident、全量測試時間、手動步驟和 owner 不明等 signals，而非等全面失效。

</details>

<details class="qa"><summary>Q7. 本章最重要的 scale 原則是什麼？</summary>

先減少需要協調的 edges，再自動化剩餘流程；不要用更多會議或更多 AI 生成內容掩蓋高耦合設計。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Preface](https://abseil.io/resources/swe-book/html/pr01.html)
- [Software Engineering at Google — Leading at Scale](https://abseil.io/resources/swe-book/html/ch06.html)
- [Software Engineering at Google — Compute as a Service](https://abseil.io/resources/swe-book/html/ch25.html)
- [DORA 2025 — AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)

---

# 第 7 章　Trade-offs、Costs 與 Architecture Decision Records

<p class="chapter-question">沒有完美解法時，如何讓『我覺得』變成可檢查、可重訪且不假裝精確的工程決策？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 1 · Software Engineering 的根基</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

用 constraints、alternatives、cost model、signals 和 reversal plan 做取捨，並以 ADR 保存決策原因。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node active"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-06-scale-and-growth-規模如何改變問題"><span>上一站</span><strong>06. Scale and Growth：規模如何改變問題</strong></a><div class="position-card current"><span>你在這裡</span><strong>07. Trade-offs、Costs 與 Architecture Decision Records</strong></div><a class="position-card" href="#chapter-08-hrt-ownership-與真正的團隊合作"><span>下一站</span><strong>08. HRT、Ownership 與真正的團隊合作</strong></a></div>

本章位於 **Part 1：Software Engineering 的根基**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Trade-off（取捨）</h3><div><span>白話定義</span><p>改善某個目標通常會增加另一種成本，工程決策需比較整體結果。</p></div><div class="example"><span>具體例子</span><p>更多測試提高信心，但也增加執行時間和維護成本。</p></div><div class="relevance"><span>本章位置</span><p>本書不提供永遠正確的工具選擇，而是提供判斷何時值得的模型。</p></div></section><section class="term-card"><h3>Constraint（限制條件）</h3><div><span>白話定義</span><p>解法必須遵守的硬邊界，例如延遲、相容性、預算、法規或權限。</p></div><div class="example"><span>具體例子</span><p>登入 API p99 必須低於 300ms，而且舊手機版本仍能使用。</p></div><div class="relevance"><span>本章位置</span><p>工程取捨必須先知道 constraint；AI agent 也需要把它寫進完成條件。</p></div></section><section class="term-card"><h3>ADR（Architecture Decision Record）</h3><div><span>白話定義</span><p>短篇記錄決策背景、選項、選擇、代價與未來重訪條件的文件。</p></div><div class="example"><span>具體例子</span><p>記錄為何選 queue 而非同步 RPC，以及流量降到何種程度時可簡化。</p></div><div class="relevance"><span>本章位置</span><p>ADR 保存『為什麼』，避免人或 AI 只看現況後重複已否決的方案。</p></div></section><section class="term-card"><h3>Goal–Signal–Metric</h3><div><span>白話定義</span><p>先定義想改善的結果，再找能觀察結果的信號，最後選可計算的代理量。</p></div><div class="example"><span>具體例子</span><p>Goal 是縮短回饋時間；signal 是工程師更快得到有用結果；metric 才是 CI p95 時間。</p></div><div class="relevance"><span>本章位置</span><p>這個順序可降低為了容易量測而優化錯誤目標的風險。</p></div></section></div>

## 為什麼需要這一章？

工程選擇幾乎都同時改變多個目標：cache 降低 latency 卻增加 stale data；更多 replicas 提高 availability 卻增加成本與一致性難度；嚴格 review 降低缺陷卻增加 lead time。若不顯式列出目標與成本，討論會退化為工具偏好或職級較高者的直覺。

### 真實 Use Case

團隊要決定 checkout 是否採同步呼叫風控，或先接受訂單再非同步審核。前者結果即時但 dependency outage 直接阻塞付款；後者提高 availability，卻需要補償、狀態機和客戶溝通。答案取決於詐欺成本、延遲目標與可逆性。

<div class="context-grid">
<section><span>問題壓力</span><p>工程選擇幾乎都同時改變多個目標：cache 降低 latency 卻增加 stale data；更多 replicas 提高 availability 卻增加成本與一致性難度；嚴格 review 降低缺陷卻增加 lead time。若不顯式列出目標與成本，討論會退化為工具偏好或職級較高者的直覺。</p></section>
<section><span>交付能力</span><p>用 constraints、alternatives、cost model、signals 和 reversal plan 做取捨，並以 ADR 保存決策原因。</p></section>
<section><span>真實場景</span><p>團隊要決定 checkout 是否採同步呼叫風控，或先接受訂單再非同步審核。前者結果即時但 dependency outage 直接阻塞付款；後者提高 availability，卻需要補償、狀態機和客戶溝通。答案取決於詐欺成本、延遲目標與可逆性。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Problem / decision deadline
        ↓
Hard constraints ──→ 不符合者淘汰
        ↓
Alternatives
        ↓
cost dimensions:
latency · reliability · complexity · people · money · security · lock-in
        ↓
choose + assumptions + reversible steps
        ↓
signals / review date / invalidation conditions
        ↓
ADR 更新或 supersede</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

先分 hard constraint 與 preference。法規、資料不可遺失、相容承諾可能是硬限制；使用某語言或雲服務通常只是偏好。把偏好假裝成 constraint 會過早消滅選項，把真正 constraint 當偏好則會產生不可接受風險。

Cost model 不必精準到小數點，但要涵蓋全生命週期。購買成本便宜的工具可能需要更多 on-call；開發最快的架構可能讓每次 migration 都昂貴。至少比較建置、運行、失敗、修改和退出成本。也要指出 uncertainty，避免虛假精確。

ADR 是決策快照：背景、選項、選擇、理由、代價、假設、signals 和何時重訪。它不應成為不可挑戰的聖旨；新 evidence 出現時以新 ADR supersede 舊決策，保留歷史即可。可逆決策應快速實驗，不可逆或 blast radius 大的決策才需要深度分析。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>用一句話定義要做的 decision、owner 和最晚決策時間。</p></div><div class="flow-card"><span>2</span><p>列 hard constraints、goals 和 non-goals，避免每個選項解不同問題。</p></div><div class="flow-card"><span>3</span><p>至少提出三個 alternatives，包括『維持現況』，比較全生命週期成本。</p></div><div class="flow-card"><span>4</span><p>先選可逆、分階段方案，定義 rollout、rollback 與觀測 signals。</p></div><div class="flow-card"><span>5</span><p>寫 ADR 並設定 review trigger，而非讓決策理由留在聊天記錄。</p></div></div>

## Coding／實務例子

範例用加權分數幫助揭露假設。它不是自動決策器；權重與分數本身就是需要討論的 judgment。

```python
OPTIONS = {
    "sync":  {"latency": 2, "availability": 1, "simplicity": 4, "fraud": 5},
    "async": {"latency": 4, "availability": 5, "simplicity": 2, "fraud": 3},
    "hybrid":{"latency": 3, "availability": 4, "simplicity": 3, "fraud": 4},
}
WEIGHTS = {"latency": 2, "availability": 5, "simplicity": 2, "fraud": 4}

def score(option: dict[str, int]) -> int:
    return sum(option[key] * WEIGHTS[key] for key in WEIGHTS)

for name, values in OPTIONS.items():
    print(name, score(values))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>權重顯示此決策特別重視 availability 和 fraud，而非假裝所有面向相等。</p></div><div class="flow-card"><span>2</span><p>分數迫使團隊解釋為何 <code>sync</code> availability 只有 1，從而暴露 dependency 假設。</p></div><div class="flow-card"><span>3</span><p>小幅分數差異不應被解讀成科學證明；可用 prototype 或 canary 收集新 evidence。</p></div><div class="flow-card"><span>4</span><p>ADR 應保存原始 matrix、uncertainty 和之後實際指標，方便校準判斷。</p></div></div>

## Trade-offs 與 Failure Modes

- Weighted matrix 容易把主觀數字包裝成客觀答案，忽略不可加總的 hard constraints。
- 只計算雲端帳單會漏掉 on-call、migration、training 和 opportunity cost。
- 追求可逆性也有代價；永久雙軌設計可能比果斷選擇更複雜。
- ADR 太長、沒有 owner 或從不重訪，會變成另一個失效文件庫。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 很適合發散 alternatives、找遺漏 cost dimensions、整理過往 ADR 和模擬反方，但它傾向給出流暢而不一定適用的建議。Model 不知道組織真正的風險承受、人才、合約和政治約束，除非 context 明確提供。AI 應幫助 decision quality，而不是成為『是模型選的』責任逃生口。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 先扮演支持者與反對者，分別 steelman 每個 alternative。</li><li>請 agent 搜尋 repository、incidents 和 ADR 中與選項相關的本地 evidence。</li><li>用 AI 草擬 ADR 結構、列出未回答問題與可驗證 assumptions。</li><li>決策後讓 AI 定期比較 signals 與 ADR 假設，提出需要重訪的候選。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>ADR 的 owner、risk acceptance 和最終選擇必須是具名的人或團隊。</li><li>要求 AI 引用本地 evidence；沒有資料時明確標為 assumption，不可虛構數字。</li><li>敏感商業、法規與人事 context 只在批准範圍內提供模型。</li><li>高不可逆決策需獨立 review、prototype 或 staged commitment，不能只靠一次生成報告。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

專家通常先問決策是否可逆，再決定分析深度。對可逆選擇，最快取得真實 feedback 的小實驗常勝過長會議；對資料格式、public API、供應商綁定等難逆選擇，退出成本和 migration path 比第一年功能表更重要。好的 ADR 不是證明當時永遠正確，而是讓後人知道當時在什麼 evidence 下合理。

</aside>

## 動手驗證

1. 挑一個待決問題，寫出 hard constraints、三個 options 和『不做』選項。
2. 執行 scoring 範例，調整 weights，觀察答案如何反映價值判斷。
3. 寫一頁 ADR，必須包含 assumptions、rollback、signals 和 review trigger。
4. 讓 AI 提出反方意見，再標記哪些論點有 evidence、哪些只是通用說法。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Hard constraint 與 preference 如何區分？</summary>

Hard constraint 被違反就使方案不可接受；preference 可用其他收益交換。判斷時要問是否存在任何合理情況可以犧牲它。

</details>

<details class="qa"><summary>Q2. 為何一定要包含『維持現況』？</summary>

改變也有 migration 和風險成本；若不比較現況，團隊可能只在新工具間選擇，忽略問題尚未值得解。

</details>

<details class="qa"><summary>Q3. Weighted score 最大風險是什麼？</summary>

主觀權重和分數看起來像客觀數學，讓人忽略 uncertainty、hard constraints 和指標不可直接相加。它應促進討論，不是自動裁決。

</details>

<details class="qa"><summary>Q4. ADR 為什麼要記錄 invalidation condition？</summary>

當關鍵 assumption 不再成立，團隊能主動重訪，而不是把舊決策永久化或靠新人猜測。

</details>

<details class="qa"><summary>Q5. 可逆決策為何通常應快速行動？</summary>

可以用小成本 rollback，真實 feedback 比抽象預測更有資訊；過度分析本身是 opportunity cost。

</details>

<details class="qa"><summary>Q6. AI 在決策中最危險的角色是什麼？</summary>

成為權威或責任替代品。它可生成論點，但不承擔商業、法律和營運後果，也可能缺少本地 context。

</details>

<details class="qa"><summary>Q7. 如何判斷一份 ADR 有價值？</summary>

幾個月後的工程師能用它理解問題、constraints、被否決選項、選擇理由與何時應重訪，而不是只看到最後結論。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Preface](https://abseil.io/resources/swe-book/html/pr01.html)
- [Software Engineering at Google — Measuring Engineering Productivity](https://abseil.io/resources/swe-book/html/ch07.html)
- [DORA 2025 — AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)
- [NIST — Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)

---
