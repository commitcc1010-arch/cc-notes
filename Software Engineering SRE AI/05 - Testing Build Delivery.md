---
title: "Testing、Build 與 Delivery"
part: 4
as_of: 2026-09-30
---

# Part 4　Testing、Build 與 Delivery

將需求轉成可執行證據，從單元測試一路走到可重現 build、CI、canary 與 rollback。

# 第 22 章　Testing Blueprint：Size、Scope 與風險組合

<p class="chapter-question">Unit、integration、E2E 到底如何組合？為什麼一座 test pyramid 仍不足以決定測試策略？</p>

<div class="chapter-meta"><span>難度：入門</span><span>Part 4 · Testing、Build 與 Delivery</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

分開理解 test size 與 scope，依失敗成本、feedback 速度和 fidelity 建立平衡 portfolio。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node active"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-21-code-search-static-analysis-與-large-scale-changes"><span>上一站</span><strong>21. Code Search、Static Analysis 與 Large-Scale Changes</strong></a><div class="position-card current"><span>你在這裡</span><strong>22. Testing Blueprint：Size、Scope 與風險組合</strong></div><a class="position-card" href="#chapter-23-unit-testing-保護-behavior-不綁死-implementation"><span>下一站</span><strong>23. Unit Testing：保護 Behavior，不綁死 Implementation</strong></a></div>

本章位於 **Part 4：Testing、Build 與 Delivery**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Test size 與 scope</h3><div><span>白話定義</span><p>Size 描述測試能使用的資源與速度；scope 描述跨越多少元件，兩者不是同一件事。</p></div><div class="example"><span>具體例子</span><p>單一函式測試通常 small scope；但若連真資料庫，資源上可能是 medium。</p></div><div class="relevance"><span>本章位置</span><p>分開思考可建立更平衡、可預測的測試組合。</p></div></section><section class="term-card"><h3>Test oracle</h3><div><span>白話定義</span><p>判斷某次執行結果是否正確的規則或已知答案。</p></div><div class="example"><span>具體例子</span><p>排序後必須單調且包含相同元素，比只比對一個範例更完整。</p></div><div class="relevance"><span>本章位置</span><p>Agent 只有在 oracle 明確時才能自主迭代，否則可能把錯誤輸出合理化。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section><section class="term-card"><h3>Invariant（不變條件）</h3><div><span>白話定義</span><p>系統任何合法狀態都必須成立的規則。</p></div><div class="example"><span>具體例子</span><p>銀行轉帳前後，所有帳戶餘額總和不應憑空增加。</p></div><div class="relevance"><span>本章位置</span><p>測試、型別和監控常用來保護 invariant；它比描述每一行實作更穩定。</p></div></section></div>

## 為什麼需要這一章？

只說「多寫 unit test」無法保證整體 service。小測試快速、容易定位，卻看不見跨元件 contract；端到端測試接近真實使用者，卻慢、昂貴且難診斷。測試策略不是選一種，而是讓不同層捕捉不同風險，且整套 suite 仍能提供快速可信的 feedback。

### 真實 Use Case

付款折扣函式的 unit tests 全過，但 checkout service 傳錯 currency field，資料庫 migration 又未部署。只有 contract/integration 能看到第一個問題，release 或 production verification 才能看到第二個。每層證據都不可被另一層完全取代。

<div class="context-grid">
<section><span>問題壓力</span><p>只說「多寫 unit test」無法保證整體 service。小測試快速、容易定位，卻看不見跨元件 contract；端到端測試接近真實使用者，卻慢、昂貴且難診斷。測試策略不是選一種，而是讓不同層捕捉不同風險，且整套 suite 仍能提供快速可信的 feedback。</p></section>
<section><span>交付能力</span><p>分開理解 test size 與 scope，依失敗成本、feedback 速度和 fidelity 建立平衡 portfolio。</p></section>
<section><span>真實場景</span><p>付款折扣函式的 unit tests 全過，但 checkout service 傳錯 currency field，資料庫 migration 又未部署。只有 contract/integration 能看到第一個問題，release 或 production verification 才能看到第二個。每層證據都不可被另一層完全取代。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Scope：跨越多少真實元件？
small ───────────────────────────── large
 function   module   service+DB   multi-service   user journey

Size：允許多少資源與不確定性？
small: CPU/memory only, milliseconds
medium: local process / DB, seconds
large: network / shared env, minutes+

risk → choose earliest faithful test
       + smaller tests for diagnosis
       + few end-to-end proofs</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Size 描述資源限制、速度和隔離；scope 描述多少邏輯或元件被一起驗證。單一 class 測試若呼叫真實網路，scope 小但 size 大；多個 module 在同 process 的 hermetic test，scope 大但仍可能是 small/medium。把兩者混成 unit/integration 名稱會讓期待含糊。

每個重要 behavior 問三題：最早在哪一層能忠實驗證？失敗時如何快速定位？有哪些跨邊界 assumptions 只有較大測試能證明？通常大量 small tests 保護局部 invariants，contract tests 保護介面，少量 end-to-end 保護關鍵 user journeys，production checks 驗證環境與 rollout。

Test portfolio 還要看 cost 和 reliability。Flaky 大測試若經常被忽略，實際證據接近零；非常精確但要兩小時的 suite 會讓 batch 變大。好的策略將快速 gates 放 presubmit，較慢 checks 放 post-submit/staging，並用風險選 relevant tests。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>列出 critical user journeys 與主要 failure modes，而不是先決定測試種類。</p></div><div class="flow-card"><span>2</span><p>為每個風險選最早且足夠忠實的 layer，再補較小 tests 幫助定位。</p></div><div class="flow-card"><span>3</span><p>分別標記 size、scope、runtime、owner、flake rate 和 environment。</p></div><div class="flow-card"><span>4</span><p>Presubmit 保持快速可信；較慢大測試在後續 gate 仍要阻止壞 release。</p></div><div class="flow-card"><span>5</span><p>定期分析 escaped defects，調整缺少的 layer，而不是只追 coverage。</p></div></div>

## Coding／實務例子

以下用資料表表示 test portfolio。程式找出關鍵 behavior 是否只有單一層 evidence，提醒需要獨立證據。

```python
tests = [
    {"name": "discount-unit", "behavior": "price", "size": "small", "scope": 1},
    {"name": "checkout-contract", "behavior": "price", "size": "medium", "scope": 2},
    {"name": "buy-journey", "behavior": "purchase", "size": "large", "scope": 5},
]

def evidence_for(behavior: str) -> list[dict]:
    return [test for test in tests if test["behavior"] == behavior]

for behavior in ("price", "purchase"):
    evidence = evidence_for(behavior)
    print(behavior, len(evidence), {item["size"] for item in evidence})
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p><code>price</code> 有 small 與 medium 兩層，局部診斷與跨 contract 都有 evidence。</p></div><div class="flow-card"><span>2</span><p><code>purchase</code> 只有 large journey；失敗時難定位，可能需要較小 component tests。</p></div><div class="flow-card"><span>3</span><p>層數不是越多越好，每個新增測試都要對應不同風險或診斷價值。</p></div><div class="flow-card"><span>4</span><p>真實 inventory 應加入 runtime、flake rate、owner 和最後失敗時間。</p></div></div>

## Trade-offs 與 Failure Modes

- Test pyramid 被當成固定比例，忽略系統 architecture 和失敗成本。
- 大測試大量重複同一路徑，執行慢卻沒有增加獨立 evidence。
- 只看 line coverage 會鼓勵執行程式碼但沒有 meaningful assertions。
- 測試環境與 production 差異太大，綠燈只能證明假環境。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 可以快速產生大量 tests，真正稀缺的是正確 oracle、代表性資料與風險模型。Agent 常根據目前 implementation 生成 assertions，因而把 bug 固化成預期。AI 最有價值的用法是從 requirements、incidents、contracts 和 mutation results 找測試缺口，而非只替每行 code 補一個鏡像測試。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 從 user journey 和歷史 incidents 產生 failure-mode matrix。</li><li>請 agent 為每個 behavior 建議最早忠實 layer，說明無法用更小測試的原因。</li><li>用 AI 產生 boundary/property cases，再由 domain owner確認 oracle。</li><li>讓 agent 分析 suite runtime、flake 和 escaped defects，提出 portfolio 調整。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>AI 不得只讀 implementation 生成 expected output；需同時提供 contract/requirement。</li><li>新增測試必須證明能在故障注入或 mutation 下失敗，避免空 assertions。</li><li>Agent 不得為縮短時間自行刪除、skip 或降低 required tests。</li><li>Production data 用於 tests 前要匿名化、最小化並遵守 retention。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

專家不問「unit test 比例多少」，而問每個高風險 behavior 有哪些獨立 evidence、最晚在哪裡發現、失敗後多快定位。Portfolio 應隨架構和事故演化；若 service contract 已成主要風險，就應把投資移到 contract tests，而不是維持漂亮金字塔。

</aside>

## 動手驗證

1. 列出一個服務五個 critical behaviors，為每個填最早忠實 test layer。
2. 執行範例，加入 flake rate 和 runtime，找最不划算的測試。
3. 挑一次 escaped defect，指出哪個 layer 應該更早捕捉以及 oracle。
4. 讓 AI 生成十個測試，再用 mutation 或故意 bug 驗證每個是否真的有辨識力。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Test size 與 scope 差在哪裡？</summary>

Size 描述資源、速度和隔離限制；scope 描述一次測試涵蓋多少邏輯與元件。兩者相關但不等同。

</details>

<details class="qa"><summary>Q2. 為何不能只用 E2E 測試？</summary>

它接近使用者但慢、脆弱、難定位，無法快速告訴作者是哪個局部 invariant 壞掉；需要較小 tests 配合。

</details>

<details class="qa"><summary>Q3. 為何不能只用 unit tests？</summary>

它們無法證明元件間 schema、配置、網路、資料庫和部署環境正確，需要 contract/integration/release evidence。

</details>

<details class="qa"><summary>Q4. Coverage 能回答什麼？</summary>

哪些程式碼被執行；不能證明 assertions 有意義、重要 behaviors 被涵蓋或錯誤能被偵測。

</details>

<details class="qa"><summary>Q5. AI-generated test 最大的 oracle 風險？</summary>

模型從有 bug 的 implementation 推導 expected output，產生永遠同意目前 code 的鏡像測試。

</details>

<details class="qa"><summary>Q6. Presubmit 為何不一定跑全部 tests？</summary>

全量可能太慢或昂貴；可用 dependency/test selection 跑快速 relevant set，再在後續 gate 補完整驗證。

</details>

<details class="qa"><summary>Q7. 如何知道 portfolio 應更新？</summary>

看 escaped defects、flake、runtime、架構變更、incident patterns 和 user criticality，找 evidence 缺口或重複。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Testing Overview](https://abseil.io/resources/swe-book/html/ch11.html)
- [Software Engineering at Google — Larger Testing](https://abseil.io/resources/swe-book/html/ch14.html)
- [Site Reliability Engineering — Testing for Reliability](https://sre.google/sre-book/testing-reliability/)
- [OpenAI — Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)

---

# 第 23 章　Unit Testing：保護 Behavior，不綁死 Implementation

<p class="chapter-question">為什麼有些 unit tests 讓重構更安全，有些卻讓任何內部修改都要重寫測試？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 4 · Testing、Build 與 Delivery</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

以 public behavior、state transition 和 invariants 寫快速、清楚、具辨識力的 tests。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node active"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-22-testing-blueprint-size-scope-與風險組合"><span>上一站</span><strong>22. Testing Blueprint：Size、Scope 與風險組合</strong></a><div class="position-card current"><span>你在這裡</span><strong>23. Unit Testing：保護 Behavior，不綁死 Implementation</strong></div><a class="position-card" href="#chapter-24-test-doubles-fake-stub-mock-的選擇"><span>下一站</span><strong>24. Test Doubles：Fake、Stub、Mock 的選擇</strong></a></div>

本章位於 **Part 4：Testing、Build 與 Delivery**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Unit test</h3><div><span>白話定義</span><p>針對小範圍行為、快速且隔離的測試。</p></div><div class="example"><span>具體例子</span><p>輸入購物車項目，驗證折扣規則和邊界值。</p></div><div class="relevance"><span>本章位置</span><p>好 unit test 保護公開行為，不綁死私有方法的實作順序。</p></div></section><section class="term-card"><h3>Test oracle</h3><div><span>白話定義</span><p>判斷某次執行結果是否正確的規則或已知答案。</p></div><div class="example"><span>具體例子</span><p>排序後必須單調且包含相同元素，比只比對一個範例更完整。</p></div><div class="relevance"><span>本章位置</span><p>Agent 只有在 oracle 明確時才能自主迭代，否則可能把錯誤輸出合理化。</p></div></section><section class="term-card"><h3>Invariant（不變條件）</h3><div><span>白話定義</span><p>系統任何合法狀態都必須成立的規則。</p></div><div class="example"><span>具體例子</span><p>銀行轉帳前後，所有帳戶餘額總和不應憑空增加。</p></div><div class="relevance"><span>本章位置</span><p>測試、型別和監控常用來保護 invariant；它比描述每一行實作更穩定。</p></div></section><section class="term-card"><h3>Hermetic test/build</h3><div><span>白話定義</span><p>結果只由明確宣告的輸入決定，不受網路、目前時間、機器或外部狀態影響。</p></div><div class="example"><span>具體例子</span><p>測試使用固定 timezone、fake clock 和本地 fixture。</p></div><div class="relevance"><span>本章位置</span><p>Hermeticity 讓 CI 與 agent 能重現失敗，也是可靠 cache 的前提。</p></div></section></div>

## 為什麼需要這一章？

Unit test 的價值是給作者快速、精確 feedback，並讓未來重構仍保持使用者可見 behavior。若測試直接呼叫 private method、驗證每次內部呼叫順序或複製 implementation 邏輯，它會對設計細節敏感，卻可能在真正 behavior 錯誤時仍然通過。

### 真實 Use Case

折扣引擎原本先算會員折扣再算 coupon，測試 mock 每一步順序。團隊重構成一次規則表，結果相同但所有 tests 壞掉。更好的測試輸入購物車與規則，驗證最終金額、拒絕條件和不變量。

<div class="context-grid">
<section><span>問題壓力</span><p>Unit test 的價值是給作者快速、精確 feedback，並讓未來重構仍保持使用者可見 behavior。若測試直接呼叫 private method、驗證每次內部呼叫順序或複製 implementation 邏輯，它會對設計細節敏感，卻可能在真正 behavior 錯誤時仍然通過。</p></section>
<section><span>交付能力</span><p>以 public behavior、state transition 和 invariants 寫快速、清楚、具辨識力的 tests。</p></section>
<section><span>真實場景</span><p>折扣引擎原本先算會員折扣再算 coupon，測試 mock 每一步順序。團隊重構成一次規則表，結果相同但所有 tests 壞掉。更好的測試輸入購物車與規則，驗證最終金額、拒絕條件和不變量。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Requirement / contract
       ↓
Arrange: minimal meaningful state
       ↓
Act: one public behavior
       ↓
Assert:
  result / state / externally visible effect
  + invariant / error semantics
       ↓
clear failure message

Implementation refactor ── should not break if behavior unchanged</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

測試名稱應描述情境與結果，例如 `expired_coupon_does_not_reduce_total`，而不是 `test_apply_2`。Arrange 保持最小、Act 聚焦單一行為、Assert 檢查重要輸出和 side effects。每個 test 應讓讀者知道哪個 contract 被保護。

測 behavior 不代表只能黑箱。內部複雜演算法可直接測純函式或 state machine，但選擇的是穩定 seam，而不是任何 private helper。Property tests 很適合 invariants，例如總額不為負、排序保持元素集合、重試不重複扣款。Boundary 和 error paths 往往比更多 happy examples 有價值。

Unit tests 要 deterministic、fast 和 independent。控制 clock、random、locale 和 environment；每個 test 自建 state，不依執行順序。失敗訊息應比較 domain values，避免巨大 snapshot 讓 reviewer 看不出真正差異。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>從 requirement 列 behavior、boundary、error 和 invariant，再寫測試。</p></div><div class="flow-card"><span>2</span><p>透過穩定 public seam 執行，避免驗證不必要的內部呼叫順序。</p></div><div class="flow-card"><span>3</span><p>使用 fake clock/random 和 local state，保持 deterministic、independent。</p></div><div class="flow-card"><span>4</span><p>讓每個 test 名稱與 assertion 表達一個可讀 contract。</p></div><div class="flow-card"><span>5</span><p>用 mutation、故意 bug 或 property cases確認測試真的能失敗。</p></div></div>

## Coding／實務例子

範例用 Python 標準庫 `unittest` 保護折扣 behavior；實作可改成規則表而不必重寫測試。

```python
import unittest
from decimal import Decimal

def final_price(price: Decimal, member: bool, coupon: Decimal) -> Decimal:
    if price < 0 or coupon < 0:
        raise ValueError("amounts must be non-negative")
    member_price = price * (Decimal("0.9") if member else Decimal("1"))
    return max(Decimal("0"), member_price - coupon)

class PriceTest(unittest.TestCase):
    def test_member_and_coupon_never_make_total_negative(self):
        self.assertEqual(
            final_price(Decimal("100"), True, Decimal("200")),
            Decimal("0"),
        )

    def test_negative_coupon_is_rejected(self):
        with self.assertRaises(ValueError):
            final_price(Decimal("100"), False, Decimal("-1"))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>第一個 test 同時提供具體 example 和 total non-negative invariant。</p></div><div class="flow-card"><span>2</span><p>測試不關心函式先算會員還是 coupon，只關心 contract 結果。</p></div><div class="flow-card"><span>3</span><p><code>Decimal</code> 避免金額測試受 binary float 誤差影響。</p></div><div class="flow-card"><span>4</span><p>Error case 驗證 invalid state 被拒絕，而不是默默產生錯價。</p></div></div>

## Trade-offs 與 Failure Modes

- 每個 private helper 都有 test，重構時產生大量無價值修改。
- 過度 snapshot 只顯示整份輸出改變，reviewer 難判斷重要差異。
- 只測 examples、不測 boundaries 和 invariants，容易漏掉組合空間。
- 測試依目前時間、全域 state 或執行順序，產生 flakiness。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 能從 requirement 產生 table-driven cases、boundary 和 property 候選，也能用 mutation 找弱 assertions。但模型容易生成重複 happy paths、mock implementation 和沒有辨識力的 assertions。可靠 workflow 是先由人定義 behavior/invariants，agent 擴展 cases，最後執行 mutation 或故意 defect 驗證 test oracle。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 把自然語言 contract 轉成 equivalence classes、boundaries 和 error cases。</li><li>請 agent 生成 property tests，明確說明每個 property 的 domain 理由。</li><li>用 AI 分析重構時大量失敗 tests，辨認哪些綁定 implementation。</li><li>讓 agent 做 mutation testing，找出即使 code 被破壞仍通過的 tests。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Expected values 優先來自 requirement、independent model 或手算，不從 implementation 複製。</li><li>AI 新增 tests 不得修改 production behavior 來配合錯誤 assertion。</li><li>禁止以大量 snapshots 取代針對性 domain assertions。</li><li>所有 generated tests 通過 style、runtime、flake 和 mutation quality gates。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

好 unit test 是可執行 contract 和設計 feedback。若一個 behavior 很難在隔離下測試，可能表示依賴與 state 邊界不清；但不要為了測試而把所有 internal details public。專家追求少量高訊息 assertions，而非 test count 或 coverage 百分比。

</aside>

## 動手驗證

1. 執行範例，故意移除 `max(0)`，確認哪個 test 失敗。
2. 加入 quantity、tax 和 currency，先列 invariants 再寫 cases。
3. 找三個重構時常壞的 tests，改成只觀察 public behavior。
4. 讓 AI 生成十個 cases，刪除重複者並說明每個剩餘 case 的新資訊。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. 測 behavior 是什麼意思？</summary>

透過穩定介面驗證使用者或 caller 可觀察結果、state 和 error semantics，而非鎖定不必要的內部步驟。

</details>

<details class="qa"><summary>Q2. Private helper 是否永遠不能直接測？</summary>

不是。若它代表穩定且複雜的演算法 seam，可直接測；問題是為每個暫時實作細節建立脆弱 contract。

</details>

<details class="qa"><summary>Q3. Property test 與 example test 如何互補？</summary>

Example 易讀且固定具體情境；property 探索較大輸入空間並保護 invariant。兩者能同時提供說明和廣度。

</details>

<details class="qa"><summary>Q4. Mutation testing 能告訴什麼？</summary>

故意改壞 production code，檢查 tests 是否偵測；若 mutation 存活，可能是 oracle/coverage 弱或 mutation 不重要。

</details>

<details class="qa"><summary>Q5. AI 為何容易生成鏡像測試？</summary>

它同時看到 implementation 和 test，傾向重述目前計算，而非從獨立 requirement 推導期望。

</details>

<details class="qa"><summary>Q6. Unit test 太多為何也可能有害？</summary>

重複、綁實作和低價值 tests 增加 runtime、維護與修改噪音，降低 suite 信任；重點是風險 coverage。

</details>

<details class="qa"><summary>Q7. 測試困難一定代表設計不好嗎？</summary>

不一定，但常是 coupling、global state 或 side effects 未隔離的 signal；需權衡是否建立 seam，而非盲目改公開 API。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Unit Testing](https://abseil.io/resources/swe-book/html/ch12.html)
- [Software Engineering at Google — Testing Overview](https://abseil.io/resources/swe-book/html/ch11.html)
- [OpenAI — Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)
- [GitHub — Review AI-generated code](https://docs.github.com/copilot/tutorials/review-ai-generated-code)

---

# 第 24 章　Test Doubles：Fake、Stub、Mock 的選擇

<p class="chapter-question">替代真實依賴時，如何避免測試只證明 mock 劇本，而與 production contract 脫節？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 4 · Testing、Build 與 Delivery</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

按測試目的選 fake、stub 或 interaction verification，優先使用行為真實且可共享驗證的替身。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node active"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-23-unit-testing-保護-behavior-不綁死-implementation"><span>上一站</span><strong>23. Unit Testing：保護 Behavior，不綁死 Implementation</strong></a><div class="position-card current"><span>你在這裡</span><strong>24. Test Doubles：Fake、Stub、Mock 的選擇</strong></div><a class="position-card" href="#chapter-25-integration-contract-e2e-load-與-chaos-tests"><span>下一站</span><strong>25. Integration、Contract、E2E、Load 與 Chaos Tests</strong></a></div>

本章位於 **Part 4：Testing、Build 與 Delivery**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Test double</h3><div><span>白話定義</span><p>測試中替代真實依賴的物件，包括 fake、stub、mock 等不同角色。</p></div><div class="example"><span>具體例子</span><p>Fake clock 讓測試控制時間，不必真的等待一小時。</p></div><div class="relevance"><span>本章位置</span><p>錯誤使用 mock 會只驗證自己設定的劇本，與真實依賴 contract 脫節。</p></div></section><section class="term-card"><h3>Unit test</h3><div><span>白話定義</span><p>針對小範圍行為、快速且隔離的測試。</p></div><div class="example"><span>具體例子</span><p>輸入購物車項目，驗證折扣規則和邊界值。</p></div><div class="relevance"><span>本章位置</span><p>好 unit test 保護公開行為，不綁死私有方法的實作順序。</p></div></section><section class="term-card"><h3>API Contract</h3><div><span>白話定義</span><p>元件對外承諾的輸入、輸出、錯誤、狀態與相容性規則。</p></div><div class="example"><span>具體例子</span><p><code>get_user(id)</code> 找不到資料時回 <code>None</code> 還是拋 exception，都是 contract。</p></div><div class="relevance"><span>本章位置</span><p>清楚 contract 讓團隊與 agent 能在不理解所有內部細節時安全組合元件。</p></div></section><section class="term-card"><h3>Hermetic test/build</h3><div><span>白話定義</span><p>結果只由明確宣告的輸入決定，不受網路、目前時間、機器或外部狀態影響。</p></div><div class="example"><span>具體例子</span><p>測試使用固定 timezone、fake clock 和本地 fixture。</p></div><div class="relevance"><span>本章位置</span><p>Hermeticity 讓 CI 與 agent 能重現失敗，也是可靠 cache 的前提。</p></div></section></div>

## 為什麼需要這一章？

外部付款、時間、資料庫和網路使小測試慢或不穩定，因此需要 test double。但不同 doubles 解決不同問題：stub 提供固定輸入，fake 有簡化但可工作的實作，mock 驗證 interaction。把所有依賴都 mock 掉，測試可能只確認自己預先寫的呼叫順序。

### 真實 Use Case

訂單 service mock repository，指定一定呼叫 `save` 一次。重構改成 batch save，business result 正確但 tests 全壞；更糟的是 mock 接受 production repository 不支援的參數。共享 fake 加 contract suite 能更接近真實 semantics。

<div class="context-grid">
<section><span>問題壓力</span><p>外部付款、時間、資料庫和網路使小測試慢或不穩定，因此需要 test double。但不同 doubles 解決不同問題：stub 提供固定輸入，fake 有簡化但可工作的實作，mock 驗證 interaction。把所有依賴都 mock 掉，測試可能只確認自己預先寫的呼叫順序。</p></section>
<section><span>交付能力</span><p>按測試目的選 fake、stub 或 interaction verification，優先使用行為真實且可共享驗證的替身。</p></section>
<section><span>真實場景</span><p>訂單 service mock repository，指定一定呼叫 <code>save</code> 一次。重構改成 batch save，business result 正確但 tests 全壞；更糟的是 mock 接受 production repository 不支援的參數。共享 fake 加 contract suite 能更接近真實 semantics。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Need isolation
   ↓
What must test observe?
  ├─ return controlled data → stub
  ├─ realistic state behavior → fake
  ├─ boundary interaction itself → mock/spy
  └─ actual integration contract → real dependency / emulator

shared contract tests:
      fake ───── must pass same suite ───── real implementation</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Stub 適合讓 dependency 回固定成功或錯誤，測 caller 分支。Fake 適合需要 state 和較真實行為，例如 in-memory repository、fake clock。Mock/spy 只在 interaction 本身是 contract 時使用，例如確保 audit event 被送出或 dangerous API 從未呼叫；不要把每個內部 call sequence 都升格成 contract。

Double 最大風險是 semantic drift。Fake database 若忽略 transaction/unique constraint，測試會接受 production 不可能狀態。解法是讓 fake 和 real implementation 共用 contract tests，限制 fake scope，並保留 integration tests。第三方 API 可使用 provider sandbox 或錄製 fixture，但需管理敏感資料和過時。

Time、random 和 ID generator 是最值得注入的 dependencies。使用 explicit interface 讓 production 實作與 fake 可替換，避免 monkey-patch 全域。設計 seam 應符合 domain，不必為每個 library call 建一層 wrapper。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>先寫測試要觀察的 contract，再選最小合適 double。</p></div><div class="flow-card"><span>2</span><p>需要 state semantics 時優先 fake；只需要固定輸入時使用 stub。</p></div><div class="flow-card"><span>3</span><p>只有 interaction 本身是需求時才驗證 call、參數或順序。</p></div><div class="flow-card"><span>4</span><p>讓 fake 與 real implementation 通過同一 contract suite，監控 drift。</p></div><div class="flow-card"><span>5</span><p>保留少量真實 integration tests，驗證 double 無法模擬的 behavior。</p></div></div>

## Coding／實務例子

範例注入 fake clock，讓 expiry 測試不必 sleep，也不依賴今天日期。

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

class Clock(Protocol):
    def now(self) -> datetime: ...

@dataclass
class FakeClock:
    current: datetime
    def now(self) -> datetime:
        return self.current
    def advance(self, delta: timedelta) -> None:
        self.current += delta

def expired(created: datetime, ttl: timedelta, clock: Clock) -> bool:
    return clock.now() >= created + ttl

clock = FakeClock(datetime(2026, 9, 30, 12, 0))
created = clock.now()
clock.advance(timedelta(minutes=11))
assert expired(created, timedelta(minutes=10), clock)
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Production 可注入 system clock，test 注入可控制的 fake。</p></div><div class="flow-card"><span>2</span><p>Advance 是 deterministic state change，測試不需真的等待十一分鐘。</p></div><div class="flow-card"><span>3</span><p>Boundary 使用 <code>&gt;=</code>，可精確測等於 expiry 的情況。</p></div><div class="flow-card"><span>4</span><p>Clock interface 是有 domain 價值的 seam，不暴露其他 internal details。</p></div></div>

## Trade-offs 與 Failure Modes

- Mock every call 會讓測試等同 implementation transcript。
- Fake 過度簡化真實 constraint，使測試接受不可能資料。
- 錄製第三方 response 可能含 secrets/PII，且 contract 更新後過時。
- 為了可測試建立大量一行 wrapper，增加 abstraction 而沒有降低真正耦合。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 特別容易產生 mock-heavy tests，因為 mock 能快速讓依賴消失並提高 coverage。Review generated tests 時要問：這個 interaction 真的是 contract 嗎？Double 是否可能 drift？是否有更真實 fake/contract test？AI 可協助生成 fake 與共同 contract suite，但 interface semantics 必須由 domain owner 定義。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 將 brittle mocks 分類成 stub、fake、真正 interaction contract。</li><li>請 agent 生成 fake 的 state model 與 real/fake 共用 contract tests。</li><li>用 AI 產生 dependency timeout、partial failure 和 malformed response cases。</li><li>讓 agent 找出 sleep、global clock、random 等適合注入的 nondeterminism。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>禁止 generated mock 驗證無需求支持的 private call sequence。</li><li>Fake 必須有 owner、documented differences 和定期 real contract verification。</li><li>Recorded fixtures 先 redaction，並標記來源版本與更新策略。</li><li>Agent 不得因 integration test 困難就完全刪除真實 dependency evidence。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Test double 是風險交換：用速度和控制換取 fidelity。專家不問「能不能 mock」，而問若 double 說謊，哪個更大層測試會抓到、多久抓到、誰維護 semantics。高價值 fake 往往是共享測試基礎設施產品，不是每個 test 自己拼的物件。

</aside>

## 動手驗證

1. 執行 fake clock 範例，測 expiry 前一微秒、正好到期與時區轉換。
2. 挑一個 mock-heavy test，標出哪些 calls 真的是 public contract。
3. 為 repository fake 和真資料庫寫同一組 create/read/unique contract tests。
4. 讓 AI 重寫 brittle mock，檢查它是否改善 fidelity 而不只是換語法。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Stub、fake、mock 最核心差異？</summary>

Stub 提供固定回答；fake 是簡化但可運作實作；mock/spy 驗證 interactions。選擇取決於測試要觀察什麼。

</details>

<details class="qa"><summary>Q2. 為何 fake 需要 contract tests？</summary>

Fake 可能與 real semantics 漂移；同一 suite 能驗證兩者在重要 contract 上一致，降低假信心。

</details>

<details class="qa"><summary>Q3. 何時 interaction verification 合理？</summary>

Interaction 本身是外部需求或重要 side effect，例如 audit、付款只送一次、禁止危險呼叫；不是每個 internal step。

</details>

<details class="qa"><summary>Q4. Fake clock 比 monkey-patch 時間好在哪裡？</summary>

Dependency 顯式、scope 清楚、可並行且不污染全域，測試能精確控制 boundary。

</details>

<details class="qa"><summary>Q5. AI 為何偏好 mocks？</summary>

它能快速隔離未知依賴並讓測試運行，但容易把目前 implementation call sequence 當 contract。

</details>

<details class="qa"><summary>Q6. 什麼情況應使用真實 dependency？</summary>

要驗證協定、schema、transaction、性能或 double 無法忠實模擬的 behavior 時，通常放在 integration/contract layer。

</details>

<details class="qa"><summary>Q7. 如何評估 double 的成本？</summary>

比較速度/控制收益與 drift、維護、假信心風險，並確認有較高 fidelity evidence 作補充。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Test Doubles](https://abseil.io/resources/swe-book/html/ch13.html)
- [Software Engineering at Google — Larger Testing](https://abseil.io/resources/swe-book/html/ch14.html)
- [OpenAI — Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)
- [GitHub — Review AI-generated code](https://docs.github.com/copilot/tutorials/review-ai-generated-code)

---

# 第 25 章　Integration、Contract、E2E、Load 與 Chaos Tests

<p class="chapter-question">跨元件風險這麼多，如何選擇足夠真實的測試，又不讓 suite 慢到無法使用？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 4 · Testing、Build 與 Delivery</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

用 contract 保護邊界、integration 驗證合作、E2E 證明關鍵旅程，再以 load/chaos 驗證壓力與失敗。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node active"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-24-test-doubles-fake-stub-mock-的選擇"><span>上一站</span><strong>24. Test Doubles：Fake、Stub、Mock 的選擇</strong></a><div class="position-card current"><span>你在這裡</span><strong>25. Integration、Contract、E2E、Load 與 Chaos Tests</strong></div><a class="position-card" href="#chapter-26-hermeticity-flakiness-與-coverage-陷阱"><span>下一站</span><strong>26. Hermeticity、Flakiness 與 Coverage 陷阱</strong></a></div>

本章位於 **Part 4：Testing、Build 與 Delivery**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Test size 與 scope</h3><div><span>白話定義</span><p>Size 描述測試能使用的資源與速度；scope 描述跨越多少元件，兩者不是同一件事。</p></div><div class="example"><span>具體例子</span><p>單一函式測試通常 small scope；但若連真資料庫，資源上可能是 medium。</p></div><div class="relevance"><span>本章位置</span><p>分開思考可建立更平衡、可預測的測試組合。</p></div></section><section class="term-card"><h3>API Contract</h3><div><span>白話定義</span><p>元件對外承諾的輸入、輸出、錯誤、狀態與相容性規則。</p></div><div class="example"><span>具體例子</span><p><code>get_user(id)</code> 找不到資料時回 <code>None</code> 還是拋 exception，都是 contract。</p></div><div class="relevance"><span>本章位置</span><p>清楚 contract 讓團隊與 agent 能在不理解所有內部細節時安全組合元件。</p></div></section><section class="term-card"><h3>Production</h3><div><span>白話定義</span><p>真實使用者、真實資料與真實商業影響所在的執行環境。</p></div><div class="example"><span>具體例子</span><p>測試環境 timeout 只是紅燈；production timeout 可能讓客戶重複付款。</p></div><div class="relevance"><span>本章位置</span><p>Production 的不確定性使 observability、rollback、capacity 和 incident response 成為必要能力。</p></div></section><section class="term-card"><h3>Canary release</h3><div><span>白話定義</span><p>先把新版本暴露給少量流量，觀察結果後才擴大。</p></div><div class="example"><span>具體例子</span><p>先讓 1% request 使用新 checkout，再比較錯誤率和 latency。</p></div><div class="relevance"><span>本章位置</span><p>Canary 限制 blast radius；前提是有代表流量、健康指標與快速 rollback。</p></div></section></div>

## 為什麼需要這一章？

元件各自正確仍可能整合失敗：schema 不同、timeout 不一致、權限缺少、資料庫 index 未建、重試造成重複 side effect。較大測試提供 fidelity，但共享環境、資料和時間增加不確定性。需要清楚知道每種測試要證明的 claim，避免所有東西都塞進端到端。

### 真實 Use Case

訂單 API unit tests 通過，付款 mock 也正常；production 卻因 client retry 送出兩次扣款。Contract test 應驗 idempotency key，integration test 應使用真 persistence，chaos test 則在 response 丟失後重試，驗證外部只產生一次 side effect。

<div class="context-grid">
<section><span>問題壓力</span><p>元件各自正確仍可能整合失敗：schema 不同、timeout 不一致、權限缺少、資料庫 index 未建、重試造成重複 side effect。較大測試提供 fidelity，但共享環境、資料和時間增加不確定性。需要清楚知道每種測試要證明的 claim，避免所有東西都塞進端到端。</p></section>
<section><span>交付能力</span><p>用 contract 保護邊界、integration 驗證合作、E2E 證明關鍵旅程，再以 load/chaos 驗證壓力與失敗。</p></section>
<section><span>真實場景</span><p>訂單 API unit tests 通過，付款 mock 也正常；production 卻因 client retry 送出兩次扣款。Contract test 應驗 idempotency key，integration test 應使用真 persistence，chaos test 則在 response 丟失後重試，驗證外部只產生一次 side effect。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>API/schema boundary → contract test
component + real DB/queue → integration test
critical user journey → E2E test
expected/peak workload → load test
dependency delay/failure → chaos/fault injection
production config/artifact → release/canary verification

每層回答不同 claim；越大越少、越有明確 owner</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Contract test 檢查 producer/consumer 對 request、response、error 和 compatibility 的共同理解，可在真服務前快速執行。Integration test 將數個真元件組合，例如 service + database + migration，驗證 transaction、configuration 和 driver。E2E 從使用者入口穿越主要系統，只保留最關鍵旅程。

Load test 必須有 workload model：arrival pattern、payload、cache warmness、read/write mix 和 SLO；只報最大 RPS 沒意義。Chaos/fault injection 要從 hypothesis 開始，例如「單區 database failover 時 checkout 成功率仍符合 SLO」，在受控 blast radius 注入 latency、error、loss 或 resource pressure。

Environment fidelity 與可重現性要平衡。Ephemeral environment 提高隔離但成本高；shared staging 接近真實但易互相污染。測試資料、secrets、cleanup 和 owner 必須顯式。Production canary 不是取代測試，而是驗證無法完整模擬的最後一段。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>為每個跨邊界 risk 指定最小能忠實證明的 test type。</p></div><div class="flow-card"><span>2</span><p>Contract suite 版本化 schema、errors、idempotency 和 compatibility。</p></div><div class="flow-card"><span>3</span><p>Integration/E2E 使用受控資料、明確 environment、cleanup 和 owner。</p></div><div class="flow-card"><span>4</span><p>Load 先定 workload/SLO；chaos 先定 hypothesis、abort 和 blast radius。</p></div><div class="flow-card"><span>5</span><p>將結果接到 release gate，失敗提供 artifacts、trace 和可行動診斷。</p></div></div>

## Coding／實務例子

以下是 provider/consumer 都能執行的簡化 contract validator，明確保護 required fields 與 error code。

```python
REQUIRED = {"id": str, "total_cents": int, "currency": str}

def validate_order_response(payload: dict) -> list[str]:
    errors = []
    for field, expected_type in REQUIRED.items():
        if field not in payload:
            errors.append(f"missing:{field}")
        elif not isinstance(payload[field], expected_type):
            errors.append(f"type:{field}")
    if payload.get("currency") not in {"TWD", "USD", "JPY"}:
        errors.append("unsupported:currency")
    return errors

assert validate_order_response(
    {"id": "o-1", "total_cents": 300, "currency": "TWD"}
) == []
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Validator 可在 provider test、consumer fixture 和 canary probe 重用。</p></div><div class="flow-card"><span>2</span><p>它保護結構與基本 semantics，但不能證明金額計算或資料庫 transaction。</p></div><div class="flow-card"><span>3</span><p>Schema evolution 要區分新增 optional field 與移除/改型等 breaking change。</p></div><div class="flow-card"><span>4</span><p>Contract failure 應顯示 field 和原因，讓多團隊快速定位 owner。</p></div></div>

## Trade-offs 與 Failure Modes

- E2E 數量過多會重複 setup、共享狀態並產生長 feedback。
- Load test workload 不代表真實分布，結果可能提供錯誤 capacity。
- Chaos 沒有 abort condition 或 owner，會把學習實驗變成真事故。
- Staging 永遠乾淨且流量小，無法暴露 production long-tail 和 contention。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 可以從 API schema 產生 contract cases、建立合成 user journeys、分析 traces 和提出 fault hypotheses；也能操作瀏覽器驗證 UI。但模型可能把 flaky environment 誤判為功能問題，或無限制擴大 chaos。Agent 適合編排已批准 experiments，blast radius、abort 和 production permission 必須 deterministic。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 從 OpenAPI/protobuf 產生 boundary、compatibility 和 malformed cases。</li><li>用 agent 啟動 ephemeral environment、執行 journey 並收集 screenshot/trace。</li><li>請 AI 根據 incident history 提出 fault injection hypotheses 和 expected signals。</li><li>讓 agent 比較 load/chaos traces，聚類 bottleneck 候選並連回 evidence。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Production fault injection 預設需人類核准、明確 scope、abort 和即時監控。</li><li>Agent 只能呼叫 allowlisted fault primitives，不能自由執行任意 infra commands。</li><li>Synthetic/recorded data 不得暴露 PII、secrets 或跨 tenant state。</li><li>AI 診斷是候選假設，release gate 依 deterministic SLO/contract thresholds。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

較大測試的價值來自忠實度，不是規模本身。專家會不斷問能否把同一風險更早移到 contract 或 component test，並把少量昂貴 tests 留給不可拆的 system properties。Chaos 也不是隨機破壞，而是驗證已聲明的 resilience hypothesis。

</aside>

## 動手驗證

1. 為 checkout 建 contract、integration、E2E、load、chaos 各一個 claim。
2. 執行 validator，加入 optional field、wrong type 和未知 currency cases。
3. 設計一次 dependency latency chaos：hypothesis、scope、signals、abort、rollback。
4. 讓 AI 產生 E2E journey，人工刪除與較小 tests 重複且無新 evidence 的步驟。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Contract test 與 integration test 差別？</summary>

Contract 聚焦介面雙方承諾，可在較隔離環境執行；integration 將真實元件組合，驗證實際 driver、配置、transaction 等合作。

</details>

<details class="qa"><summary>Q2. E2E 為何應聚焦關鍵 journey？</summary>

它昂貴、慢且難定位；保留對核心使用者結果的少量證明，細節交給較小 layers。

</details>

<details class="qa"><summary>Q3. Load test 前最重要的輸入是什麼？</summary>

代表真實與尖峰的 workload model 以及品質目標；沒有 request mix、payload、arrival 和 SLO，RPS 數字無法解讀。

</details>

<details class="qa"><summary>Q4. Chaos experiment 必須有哪些安全元素？</summary>

明確 hypothesis、blast radius、owner、observability、abort condition、rollback 和事前核准。

</details>

<details class="qa"><summary>Q5. Production canary 能否取代 staging tests？</summary>

不能。Canary 是最後真實 evidence，仍會影響使用者；前面 tests 先消除已知風險，canary 限制未知風險。

</details>

<details class="qa"><summary>Q6. AI 在較大測試最適合的角色？</summary>

生成 cases、編排環境、收集 artifacts、分析 traces 和提出假設；不可自行決定高風險 production fault。

</details>

<details class="qa"><summary>Q7. 如何降低大測試診斷時間？</summary>

保存每層 logs/traces/artifacts、使用唯一 correlation ID、提供 component health，並以較小 tests 重現局部問題。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Larger Testing](https://abseil.io/resources/swe-book/html/ch14.html)
- [Site Reliability Engineering — Testing for Reliability](https://sre.google/sre-book/testing-reliability/)
- [Site Reliability Engineering — Reliable Product Launches](https://sre.google/sre-book/reliable-product-launches/)
- [Google Cloud — How Google SRE is using agentic AI](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)

---

# 第 26 章　Hermeticity、Flakiness 與 Coverage 陷阱

<p class="chapter-question">測試偶爾失敗為什麼會侵蝕整個工程系統？如何避免 coverage 變成沒有辨識力的目標？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 4 · Testing、Build 與 Delivery</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

找出 nondeterminism、建立隔離與重現，並用 mutation/風險 evidence 補足 coverage 的盲點。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node active"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-25-integration-contract-e2e-load-與-chaos-tests"><span>上一站</span><strong>25. Integration、Contract、E2E、Load 與 Chaos Tests</strong></a><div class="position-card current"><span>你在這裡</span><strong>26. Hermeticity、Flakiness 與 Coverage 陷阱</strong></div><a class="position-card" href="#chapter-27-build-systems-reproducibility-與-provenance"><span>下一站</span><strong>27. Build Systems、Reproducibility 與 Provenance</strong></a></div>

本章位於 **Part 4：Testing、Build 與 Delivery**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Hermetic test/build</h3><div><span>白話定義</span><p>結果只由明確宣告的輸入決定，不受網路、目前時間、機器或外部狀態影響。</p></div><div class="example"><span>具體例子</span><p>測試使用固定 timezone、fake clock 和本地 fixture。</p></div><div class="relevance"><span>本章位置</span><p>Hermeticity 讓 CI 與 agent 能重現失敗，也是可靠 cache 的前提。</p></div></section><section class="term-card"><h3>Flaky test</h3><div><span>白話定義</span><p>程式未改變，但測試有時通過、有時失敗。</p></div><div class="example"><span>具體例子</span><p>依賴真實時間的測試剛好跨過午夜便失敗。</p></div><div class="relevance"><span>本章位置</span><p>Flakiness 會消耗信任；AI 若以重跑掩蓋它，只會讓問題更晚爆發。</p></div></section><section class="term-card"><h3>Test oracle</h3><div><span>白話定義</span><p>判斷某次執行結果是否正確的規則或已知答案。</p></div><div class="example"><span>具體例子</span><p>排序後必須單調且包含相同元素，比只比對一個範例更完整。</p></div><div class="relevance"><span>本章位置</span><p>Agent 只有在 oracle 明確時才能自主迭代，否則可能把錯誤輸出合理化。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section></div>

## 為什麼需要這一章？

Flaky test 讓同一 code 在相同意圖下得到不同 signal。團隊開始重跑、忽略紅燈或把錯誤歸咎環境，真正 regression 便更容易通過。Coverage 則只表示程式碼被執行，若沒有 meaningful oracle，100% 仍可能完全不保護 behavior。

### 真實 Use Case

CI 有一個 5% flake 的 E2E；工程師習慣按 rerun。某天真正 race condition 出現，第二次恰好通過而被 merge。測試仍存在、dashboard coverage 很高，但 feedback 系統已失去可信度。

<div class="context-grid">
<section><span>問題壓力</span><p>Flaky test 讓同一 code 在相同意圖下得到不同 signal。團隊開始重跑、忽略紅燈或把錯誤歸咎環境，真正 regression 便更容易通過。Coverage 則只表示程式碼被執行，若沒有 meaningful oracle，100% 仍可能完全不保護 behavior。</p></section>
<section><span>交付能力</span><p>找出 nondeterminism、建立隔離與重現，並用 mutation/風險 evidence 補足 coverage 的盲點。</p></section>
<section><span>真實場景</span><p>CI 有一個 5% flake 的 E2E；工程師習慣按 rerun。某天真正 race condition 出現，第二次恰好通過而被 merge。測試仍存在、dashboard coverage 很高，但 feedback 系統已失去可信度。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>test inputs
  + source / dependencies / toolchain
  + clock / random / locale / network / scheduling / shared state
        ↓
若未宣告或隔離 → nondeterminism → flaky signal
        ↓
capture seed / environment / trace
        ↓
reproduce → root cause → deterministic fix

coverage → 哪裡執行過
mutation / assertions → 是否能辨認錯誤</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Hermetic test 將所有影響結果的輸入顯式化：固定 dependency、clock、random seed、timezone、locale、filesystem 和 network；每個 test 擁有獨立 state。Concurrency 本身仍可能有多種合法 interleaving，需用 deterministic scheduler、stress repetition 或 invariant 檢查。

Flake 管理先量測與分類：test defect、product race、infrastructure、external dependency。立即保存 seed、logs、trace、machine/environment 和 attempts。Quarantine 只能暫時保護主線，必須有 owner、期限和替代 coverage；無限重跑會把真 defect 變成機率遊戲。

Coverage 用於找完全未執行區域，不應成為唯一目標。Branch coverage、mutation score、property tests 和 escaped defect analysis 提供更多辨識力。某段 error handling 行數少但風險高，應優先於低風險 getter 的百分比。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>讓 test inputs 顯式並隔離 clock、random、network、filesystem 和 shared state。</p></div><div class="flow-card"><span>2</span><p>失敗時保存 seed、environment、logs、trace 和完整 attempt history。</p></div><div class="flow-card"><span>3</span><p>依 test/product/infra/external 分類 flake，指定 owner 和修復期限。</p></div><div class="flow-card"><span>4</span><p>Quarantine 必須保留替代 signal，禁止無上限 rerun 掩蓋問題。</p></div><div class="flow-card"><span>5</span><p>Coverage 搭配 branch、mutation、risk 和 incidents 解讀，不作個人目標。</p></div></div>

## Coding／實務例子

以下以固定 seed 展示如何重現 property test；失敗輸入必須被保存，而不是只寫『random failure』。

```python
import random

def generate_quantities(seed: int, count: int = 5) -> list[int]:
    rng = random.Random(seed)
    return [rng.randint(-2, 5) for _ in range(count)]

def valid_total(values: list[int]) -> bool:
    return sum(max(0, value) for value in values) >= 0

seed = 731
case = generate_quantities(seed)
print(seed, case, valid_total(case))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>本地 <code>Random(seed)</code> 不依賴其他 tests 對 global RNG 的使用。</p></div><div class="flow-card"><span>2</span><p>CI 發現失敗時記錄 seed，作者能產生完全相同 inputs。</p></div><div class="flow-card"><span>3</span><p>Property <code>total &gt;= 0</code> 是 oracle；隨機資料本身沒有判斷能力。</p></div><div class="flow-card"><span>4</span><p>真實 property framework 還會 shrink failure，找到最小反例。</p></div></div>

## Trade-offs 與 Failure Modes

- 增加 rerun 次數會提高綠燈率，但降低 failure signal 的誠實度。
- Quarantine 沒有 owner/expiry，測試會永久離開 required gate。
- 追 coverage target 促使增加無 assertion 或只驗實作的低價值 tests。
- 過度 hermetic 可能完全模擬 production，需保留 real integration evidence。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

Agent 很容易用 rerun、sleep、放寬 assertion、skip 或刪測試讓任務完成，因此 harness 必須明確禁止這些捷徑。AI 可分析 flake logs、聚類 signatures、找共享 state 和產生 deterministic reproduction；但是否 quarantine 需由 policy 決定。Eval 也有 flakiness，應保存 model/version、sampling、tools 和多次分布。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 比較成功/失敗 traces，找 clock、ordering、resource 和 shared-state 差異。</li><li>用 agent 產生最小 reproduction、固定 seed 和額外 instrumentation。</li><li>請 AI 對 coverage gaps 按 user risk 排序，而非只按行數。</li><li>讓 agent 執行 mutation 並整理存活 mutation 對應的 oracle 缺口。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>禁止 agent 透過 sleep、rerun-until-pass、skip、刪除或放寬 assertion 隱藏失敗。</li><li>Quarantine 操作需 issue、owner、expiry、reason 和替代 coverage。</li><li>AI eval 保存完整 configuration 並看分布，不把單次結果視為 deterministic。</li><li>Generated reproduction 必須在乾淨環境多次重現，才可宣稱 root cause。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Flakiness 是 trust incident。修復優先級不只看該 test，而看它污染整個 gate 的程度。專家會把 infra flakes 與 product races 分開治理，且把 coverage 當地圖而非分數。AI 可加速 forensic，但若獎勵只有『把 CI 變綠』，它會選擇最短而非最正確的路。

</aside>

## 動手驗證

1. 把一個依賴 current time 的 test 改成 fake clock，連續跑一百次。
2. 執行 seed 範例，故意建立 failure，保存 seed 並重現。
3. 為 quarantine workflow 寫 required metadata 和 expiry check。
4. 讓 AI 修一個 flaky test，檢查 diff 是否包含禁止捷徑。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Flaky test 為何比單次失敗更危險？</summary>

它破壞團隊對紅燈的信任，形成重跑和忽略習慣，使真正 regression 更容易外溢。

</details>

<details class="qa"><summary>Q2. Hermetic 是否表示完全不測真依賴？</summary>

不是。它適合快速可重現 layers；仍需較高 fidelity integration/release tests 驗證真實 contract。

</details>

<details class="qa"><summary>Q3. Quarantine 的正確用途？</summary>

短期隔離已知高噪音 test，保護主線，同時保留 owner、修復期限和替代 signal；不是永久垃圾桶。

</details>

<details class="qa"><summary>Q4. Coverage 無法證明什麼？</summary>

無法證明 assertions 有意義、重要 behavior 或 boundaries 被測，也無法證明 test 能偵測故障。

</details>

<details class="qa"><summary>Q5. Mutation testing 補充什麼資訊？</summary>

故意改壞 code 看 tests 是否失敗，估計 oracle 的辨識力；仍需判斷 mutation 是否代表重要風險。

</details>

<details class="qa"><summary>Q6. AI 為何容易用錯誤方式修 flake？</summary>

任務通常以 tests green 為完成條件，模型可能選 sleep/rerun/skip 等表面捷徑；需明確政策和 diff review。

</details>

<details class="qa"><summary>Q7. AI eval flakiness 如何處理？</summary>

固定可固定的 inputs/config，保存版本與 traces，重複執行看分布和 confidence，而非只看一次 pass/fail。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Testing Overview](https://abseil.io/resources/swe-book/html/ch11.html)
- [Software Engineering at Google — Continuous Integration](https://abseil.io/resources/swe-book/html/ch23.html)
- [OpenAI — Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)
- [GitHub — Review AI-generated code](https://docs.github.com/copilot/tutorials/review-ai-generated-code)

---

# 第 27 章　Build Systems、Reproducibility 與 Provenance

<p class="chapter-question">為什麼『在我機器可以 build』不是可部署證據？如何確定 production bytes 來自哪些輸入？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 4 · Testing、Build 與 Delivery</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

理解 build graph、declared inputs、hermetic execution、cache、immutable artifact 與供應鏈 provenance。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node active"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-26-hermeticity-flakiness-與-coverage-陷阱"><span>上一站</span><strong>26. Hermeticity、Flakiness 與 Coverage 陷阱</strong></a><div class="position-card current"><span>你在這裡</span><strong>27. Build Systems、Reproducibility 與 Provenance</strong></div><a class="position-card" href="#chapter-28-continuous-integration-把錯誤發現在最便宜的位置"><span>下一站</span><strong>28. Continuous Integration：把錯誤發現在最便宜的位置</strong></a></div>

本章位於 **Part 4：Testing、Build 與 Delivery**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Build</h3><div><span>白話定義</span><p>把 source、dependencies 與設定轉成可部署 artifact 的可重複流程。</p></div><div class="example"><span>具體例子</span><p>將 Python application 和鎖定套件打成帶 digest 的 container image。</p></div><div class="relevance"><span>本章位置</span><p>Build graph 和 provenance 讓團隊知道 production 到底執行哪組輸入。</p></div></section><section class="term-card"><h3>Dependency</h3><div><span>白話定義</span><p>程式運作所依賴的 library、service、tool、資料格式或團隊。</p></div><div class="example"><span>具體例子</span><p>Web service 依賴資料庫 driver 和外部付款 API。</p></div><div class="relevance"><span>本章位置</span><p>Dependency 帶來升級、供應鏈、安全與可用性成本；AI 可能捏造不存在的套件。</p></div></section><section class="term-card"><h3>Hermetic test/build</h3><div><span>白話定義</span><p>結果只由明確宣告的輸入決定，不受網路、目前時間、機器或外部狀態影響。</p></div><div class="example"><span>具體例子</span><p>測試使用固定 timezone、fake clock 和本地 fixture。</p></div><div class="relevance"><span>本章位置</span><p>Hermeticity 讓 CI 與 agent 能重現失敗，也是可靠 cache 的前提。</p></div></section><section class="term-card"><h3>Provenance（來源鏈）</h3><div><span>白話定義</span><p>記錄 artifact、資料或答案由哪些輸入、工具、版本與操作者產生。</p></div><div class="example"><span>具體例子</span><p>Container image 可追到 commit、lockfile、builder identity 和簽章。</p></div><div class="relevance"><span>本章位置</span><p>AI 回答也需保存 retrieval sources、model version 與 tool trace 才能稽核。</p></div></section></div>

## 為什麼需要這一章？

Build 將 source、dependencies、toolchain 和 configuration 轉成 artifact。若輸入未宣告、會讀本機狀態或網路 latest，兩次 build 可能產生不同結果；cache 也會因缺少 dependency edge 回傳過期輸出。Production 出事時，沒有 provenance 就無法回答實際執行什麼。

### 真實 Use Case

工程師從相同 commit build image，一台含舊 generated file，另一台從網路抓到新版 package，digest 不同。Canary 通過的 artifact 與全面部署的並非同一 bytes，測試證據失去連結。

<div class="context-grid">
<section><span>問題壓力</span><p>Build 將 source、dependencies、toolchain 和 configuration 轉成 artifact。若輸入未宣告、會讀本機狀態或網路 latest，兩次 build 可能產生不同結果；cache 也會因缺少 dependency edge 回傳過期輸出。Production 出事時，沒有 provenance 就無法回答實際執行什麼。</p></section>
<section><span>交付能力</span><p>理解 build graph、declared inputs、hermetic execution、cache、immutable artifact 與供應鏈 provenance。</p></section>
<section><span>真實場景</span><p>工程師從相同 commit build image，一台含舊 generated file，另一台從網路抓到新版 package，digest 不同。Canary 通過的 artifact 與全面部署的並非同一 bytes，測試證據失去連結。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>declared sources ─┐
lockfile/deps ────┼→ build graph → sandboxed actions → artifact
toolchain image ──┤          │                         │
config inputs ────┘          └→ content cache          ├→ digest
                                                     └→ provenance

test artifact digest == deployed artifact digest</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Build graph 把 targets 與 inputs/outputs 顯式化。Action key 可由 source、command、toolchain 和 environment hash 產生；相同 key 才能安全重用 cache。若 action 偷讀 undeclared file 或 network，cache correctness 會壞掉。Sandbox 用來迫使依賴顯式。

Reproducible build 追求相同 inputs 產生相同或可驗證等價 artifact。需固定 dependency、timestamps、locale、file ordering 和 toolchain。不是每個語言都完全 bit-for-bit，但至少要能解釋差異並確保測試過的 artifact 原封不動被推進。

Provenance 記錄 source commit、builder identity、commands、dependencies、artifact digest 和簽章。Release pipeline 驗證 artifact 由受信 builder 產生、required tests 對同一 digest 執行。不要在每個環境重新 build，否則 staging evidence 無法轉移到 production。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>將 source、dependencies、toolchain、config 全部宣告為 build inputs。</p></div><div class="flow-card"><span>2</span><p>在 sandbox 禁止 undeclared filesystem/network，驗證 graph 完整。</p></div><div class="flow-card"><span>3</span><p>固定 lockfile、toolchain 和非語意 timestamps，測 reproducibility。</p></div><div class="flow-card"><span>4</span><p>產出 immutable digest 與 provenance，tests/deploy 引用同一 artifact。</p></div><div class="flow-card"><span>5</span><p>保護 builder identity、signing key、cache 和 registry，定期驗證 supply chain。</p></div></div>

## Coding／實務例子

這個小例子以內容 hash 代表 artifact identity；任何 source 或 lockfile 改變都會得到不同 digest。

```python
from hashlib import sha256
from pathlib import Path

def artifact_digest(inputs: list[Path]) -> str:
    digest = sha256()
    for path in sorted(inputs, key=lambda p: str(p)):
        digest.update(str(path).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()

# digest = artifact_digest([Path("app.py"), Path("requirements.lock")])
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>排序 path 避免 filesystem traversal order 讓結果不穩定。</p></div><div class="flow-card"><span>2</span><p>同時 hash 路徑和內容，避免兩個不同 inputs 只因拼接方式碰撞語意。</p></div><div class="flow-card"><span>3</span><p>真實 build 還要納入 compiler/toolchain、flags、environment 和 generated inputs。</p></div><div class="flow-card"><span>4</span><p>Digest 只識別 bytes；provenance 另外回答由誰、如何、從哪個 source 產生。</p></div></div>

## Trade-offs 與 Failure Modes

- Hermetic build 完全禁網路但未提供 dependency mirror，可能讓流程難以採用而被繞過。
- Remote cache 權限不當可被污染，讓受信 build 取得惡意 artifact。
- 每個 environment 重新 build，使測試與部署不是同一 bytes。
- 只保存 image tag，tag 可被覆蓋，無法作 immutable identity。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

Coding agent 可修改 build graph、dependencies 和 generation steps，因此其 sandbox 需要比普通 editor 更嚴格。Agent 不應自由執行 package install scripts 或下載未知 binary。AI 可診斷 missing dependency edge、摘要 build failure 和提出 cache 改善，但 artifact trust 必須由 deterministic builder、identity、digest 和 provenance 建立。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 讀 build graph 和 failure log，提出 undeclared/missing dependency 候選。</li><li>請 agent 產生最小 target 和 affected-tests 分析，縮短 feedback。</li><li>用 AI 比較兩次 build manifest，解釋不重現 inputs。</li><li>讓 agent 草擬 dependency update，受信 builder 重新產生 artifact/provenance。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Agent build 預設 sandbox、最小 egress、readonly credentials 和資源 quota。</li><li>未批准 download/install 必須 fail closed，不能因 build 失敗自行繞過。</li><li>AI 不持有 signing key；簽章由受信獨立 builder 完成。</li><li>只有同一 immutable digest 通過 tests、scan 和 canary後才能升級。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Build system 是軟體供應鏈的 compiler，也是全公司 feedback 基礎設施。專家會投資錯誤訊息、增量速度和 reproducibility，因為每次變更都支付這條路徑。AI 讓 source 變更更頻繁，build graph 的正確性與速度會直接決定 agent 是否能可靠自主迭代。

</aside>

## 動手驗證

1. 為一個 build 列出 source、deps、toolchain、config、environment 五類 inputs。
2. 執行 digest 函式，改 lockfile 一個 byte，確認 artifact identity 改變。
3. 在乾淨環境 build 兩次並比較 digest/manifest，找 nondeterminism。
4. 設計 agent build sandbox：filesystem、network、credentials、CPU/time limits。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Build graph 有什麼作用？</summary>

顯式描述 targets 的 inputs、actions 和 outputs，使系統能正確排序、增量執行、cache 和重建。

</details>

<details class="qa"><summary>Q2. Hermetic build 為何有利 cache？</summary>

所有影響輸出的 inputs 已宣告，相同 action key 才真正代表相同結果；偷讀外部狀態會讓 cache 不可信。

</details>

<details class="qa"><summary>Q3. Reproducible 與 provenance 差別？</summary>

Reproducible 關心相同 inputs 能否得到相同結果；provenance 記錄 artifact 如何、由誰、從哪些 inputs 產生。

</details>

<details class="qa"><summary>Q4. 為何 staging 和 production 不應重新 build？</summary>

重新 build 可能產生不同 bytes，使 staging tests/canary 的 evidence 無法證明 production artifact。

</details>

<details class="qa"><summary>Q5. Digest 和 tag 有何差別？</summary>

Digest 由內容決定且 immutable；tag 是可變名稱，適合人類引用但不能單獨作信任證據。

</details>

<details class="qa"><summary>Q6. AI build 權限為何需要限制？</summary>

Build scripts 可執行任意 code、讀 secrets、下載 dependency；agent 可能受惡意 instructions 或誤判影響。

</details>

<details class="qa"><summary>Q7. Build 系統如何影響工程生產力？</summary>

它位於每次修改 feedback path；慢、不可靠或難診斷會增加 batch、等待和繞過，快速可信則支援小批次。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Build Systems and Build Philosophy](https://abseil.io/resources/swe-book/html/ch18.html)
- [Software Engineering at Google — Dependency Management](https://abseil.io/resources/swe-book/html/ch21.html)
- [OWASP — Top 10 for LLM Applications 2025](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)

---

# 第 28 章　Continuous Integration：把錯誤發現在最便宜的位置

<p class="chapter-question">CI 應該在何時跑哪些 checks？如何同時保持快速、可信與足夠完整？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 4 · Testing、Build 與 Delivery</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

設計 presubmit、post-submit 與 release gates，利用 dependency/test selection 提供分層 feedback。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node active"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-27-build-systems-reproducibility-與-provenance"><span>上一站</span><strong>27. Build Systems、Reproducibility 與 Provenance</strong></a><div class="position-card current"><span>你在這裡</span><strong>28. Continuous Integration：把錯誤發現在最便宜的位置</strong></div><a class="position-card" href="#chapter-29-continuous-delivery-canary-與-rollback"><span>下一站</span><strong>29. Continuous Delivery、Canary 與 Rollback</strong></a></div>

本章位於 **Part 4：Testing、Build 與 Delivery**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Continuous Integration</h3><div><span>白話定義</span><p>頻繁整合小變更，並以自動 build、test 和 analysis 快速回饋。</p></div><div class="example"><span>具體例子</span><p>Pull request 在 merge 前執行 lint、unit、contract 和 security checks。</p></div><div class="relevance"><span>本章位置</span><p>CI 是變更進入共享主線前的早期告警系統。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section><section class="term-card"><h3>Static analysis</h3><div><span>白話定義</span><p>不實際執行完整程式，就分析程式結構、型別、資料流或規則。</p></div><div class="example"><span>具體例子</span><p>Type checker 在 CI 發現函式可能回傳 <code>None</code> 卻被當整數使用。</p></div><div class="relevance"><span>本章位置</span><p>它為人與 agent 提供快速、確定性、可自動化的 feedback。</p></div></section><section class="term-card"><h3>Build</h3><div><span>白話定義</span><p>把 source、dependencies 與設定轉成可部署 artifact 的可重複流程。</p></div><div class="example"><span>具體例子</span><p>將 Python application 和鎖定套件打成帶 digest 的 container image。</p></div><div class="relevance"><span>本章位置</span><p>Build graph 和 provenance 讓團隊知道 production 到底執行哪組輸入。</p></div></section></div>

## 為什麼需要這一章？

CI 的價值不是有一台機器跑 tests，而是頻繁把小變更整合到共享主線，快速指出 incompatibility。Presubmit 若慢到數小時，作者會延後提交；若只跑少量 tests，壞變更進 main 後影響所有人。需要依風險、成本和 signal quality 分層。

### 真實 Use Case

一個共用 library 改動只跑自身 unit tests，merge 後破壞五十個 consumers。全量 presubmit 又要三小時。Build graph 可選 direct/reverse dependencies 的高價值 tests，post-submit 再跑更廣範圍並自動隔離 culprit。

<div class="context-grid">
<section><span>問題壓力</span><p>CI 的價值不是有一台機器跑 tests，而是頻繁把小變更整合到共享主線，快速指出 incompatibility。Presubmit 若慢到數小時，作者會延後提交；若只跑少量 tests，壞變更進 main 後影響所有人。需要依風險、成本和 signal quality 分層。</p></section>
<section><span>交付能力</span><p>設計 presubmit、post-submit 與 release gates，利用 dependency/test selection 提供分層 feedback。</p></section>
<section><span>真實場景</span><p>一個共用 library 改動只跑自身 unit tests，merge 後破壞五十個 consumers。全量 presubmit 又要三小時。Build graph 可選 direct/reverse dependencies 的高價值 tests，post-submit 再跑更廣範圍並自動隔離 culprit。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>local: formatter / focused tests
          ↓
presubmit:
  lint / type / unit / relevant contract / security
          ↓
merge main
          ↓
post-submit:
  wider integration / platform matrix / attribution
          ↓
release candidate:
  E2E / load / compliance / artifact scan
          ↓
canary / production verification</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

每個 gate 有不同時間預算和決策。Local feedback 應秒到分鐘；presubmit 阻止高機率、可歸因錯誤；post-submit 可跑更廣但需快速找 culprit 與修復 main；release gate 驗證 artifact 和 environment。把所有 tests 放最前面不是成熟，而是忽略等待成本。

Test selection 使用 changed files、dependency graph、historical relevance 和風險標籤。它必須保守：不確定時擴大，並以週期全量測試檢查漏失。CI failure 要 actionable：顯示 owner、log、reproduction command 和 flaky status。紅燈無人處理會使 main 長期失去信任。

CI 本身是 production service，有 availability、latency、capacity 和 change management。大規模 agent changes 會增加 queue 和運算成本，需要 prioritization、cache、公平 quota 和取消過期 runs。Metrics 應看 time-to-signal、false signal 和 escaped defects。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>定義 local/presubmit/post-submit/release 各自的決策與時間預算。</p></div><div class="flow-card"><span>2</span><p>依 dependency、risk 和 history 選 relevant tests，週期性全量驗證漏失。</p></div><div class="flow-card"><span>3</span><p>Failure 附 owner、artifact、reproduction、flake 和 culprit attribution。</p></div><div class="flow-card"><span>4</span><p>Main break 有明確 stop-the-line、revert/repair policy 和時間目標。</p></div><div class="flow-card"><span>5</span><p>將 CI 作為服務管理 capacity、queue、cache、SLO 和平台使用者體驗。</p></div></div>

## Coding／實務例子

簡化 test selector 從 changed modules 沿 reverse dependency 找受影響 tests。真實 graph 需處理語言、dynamic loading 和風險加權。

```python
REVERSE_DEPS = {
    "pricing": {"checkout", "invoice"},
    "checkout": {"web"},
    "invoice": set(),
    "web": set(),
}
TESTS = {name: f"test_{name}" for name in REVERSE_DEPS}

def affected(changed: set[str]) -> set[str]:
    seen = set(changed)
    queue = list(changed)
    while queue:
        current = queue.pop()
        for consumer in REVERSE_DEPS.get(current, set()):
            if consumer not in seen:
                seen.add(consumer)
                queue.append(consumer)
    return {TESTS[name] for name in seen}

print(affected({"pricing"}))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Pricing 變更會選自身、checkout、invoice 和 web tests。</p></div><div class="flow-card"><span>2</span><p>Reverse dependency 比只跑 changed module 更能發現 consumer break。</p></div><div class="flow-card"><span>3</span><p>Dynamic/config dependencies 可能不在 graph，需 contract tags 或全量 safety net。</p></div><div class="flow-card"><span>4</span><p>Affected set 可再按 presubmit time budget 與 criticality 排序。</p></div></div>

## Trade-offs 與 Failure Modes

- 過度 aggressive selection 漏跑重要 tests，提供錯誤綠燈。
- Post-submit 紅燈沒人修，main 長期壞掉，使所有 failures 難歸因。
- CI queue 太長會鼓勵大 batch、少提交和本地繞過。
- Flaky tests 與 infra failure 未區分，作者無法採取正確行動。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 可以 triage logs、推薦 tests、修常見 failure 和摘要 change risk；agent 也會顯著增加 CI runs。最佳實務是讓 agent 接收結構化 failure、明確 reproduction 和 budget，不能自行 waive required gates。Test selection 可使用 ML/AI 信號，但 deterministic dependency 與週期全量仍作安全網。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 將 CI failure 分類為 product、test、infra、dependency 或 policy。</li><li>用 agent 根據 diff、graph 和歷史 failures 建議 relevant tests與風險說明。</li><li>請 AI 產生 reproduction steps 和最小修復候選，再重新跑原 gate。</li><li>讓 agent 摘要多個 parallel jobs，指出第一個因果 failure 而非後續噪音。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Agent 不得修改 required-check policy 或把 failure 標為成功。</li><li>AI test selection 有漏失監控，並以 deterministic graph/全量 runs 校驗。</li><li>CI tools 使用隔離 credentials；fork/untrusted code 不取得 production secrets。</li><li>限制每個 agent 的 parallelism、CPU、token 和重試，避免 feedback platform 過載。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

CI 是 pre-production alerting。好的 signal 只在需要 action 時阻止人，並提供足夠 context；壞 CI 和壞 pager 一樣會造成疲勞。AI 能改善診斷，但核心仍是快速、deterministic、可歸因的 checks，以及團隊願意立即修復 main 的社會 contract。

</aside>

## 動手驗證

1. 為 repository 將 checks 分到 local、presubmit、post-submit、release。
2. 執行 selector，加入 dynamic dependency 標籤和 critical test always-run。
3. 量一週 CI queue、runtime、flake、rerun 和 time-to-first-signal。
4. 讓 AI triage 十個 failures，人工評估分類 precision 和 evidence 引用。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. CI 與單純自動跑測試差在哪裡？</summary>

CI 強調頻繁小批次整合共享主線，並用自動 evidence 快速發現 incompatibility；工具只是支援這個工作模式。

</details>

<details class="qa"><summary>Q2. 為何不把所有 tests 放 presubmit？</summary>

全量可能太慢昂貴，延長 feedback 並增加 batch；依風險選 relevant set，後續 gates 補廣度。

</details>

<details class="qa"><summary>Q3. Test selection 如何防止漏失？</summary>

保守 dependency graph、critical always-run、風險標籤、週期全量 tests，並追蹤 escaped failures 校準。

</details>

<details class="qa"><summary>Q4. Main broken 時應怎麼做？</summary>

Stop the line、快速找到 culprit、revert 或 repair，避免在未知壞基線繼續疊加變更。

</details>

<details class="qa"><summary>Q5. AI 能否自行 waive flaky check？</summary>

不應。它可分類與提出 quarantine，但 policy 需 owner、期限和替代 signal；required gate 不能由被測 agent 自行解除。

</details>

<details class="qa"><summary>Q6. CI 為什麼也需要 SLO？</summary>

它是所有工程師依賴的服務；availability、queue 和 latency 直接決定 feedback 與 batch size。

</details>

<details class="qa"><summary>Q7. CI 和 production alerting 的共同原則？</summary>

Signal 要可信、可行動、及時、可歸因，噪音需治理；否則人會忽略真正風險。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Continuous Integration](https://abseil.io/resources/swe-book/html/ch23.html)
- [Software Engineering at Google — Testing Overview](https://abseil.io/resources/swe-book/html/ch11.html)
- [DORA 2025 — AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)

---

# 第 29 章　Continuous Delivery、Canary 與 Rollback

<p class="chapter-question">如何把通過 CI 的 artifact 安全地送到 production，而不把所有信心押在一次大部署？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 4 · Testing、Build 與 Delivery</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

建立 immutable promotion、progressive rollout、health analysis、automatic rollback 和 feature cleanup。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node active"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-28-continuous-integration-把錯誤發現在最便宜的位置"><span>上一站</span><strong>28. Continuous Integration：把錯誤發現在最便宜的位置</strong></a><div class="position-card current"><span>你在這裡</span><strong>29. Continuous Delivery、Canary 與 Rollback</strong></div><a class="position-card" href="#chapter-30-production-environment-operations-與-sre"><span>下一站</span><strong>30. Production Environment、Operations 與 SRE</strong></a></div>

本章位於 **Part 4：Testing、Build 與 Delivery**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Continuous Delivery</h3><div><span>白話定義</span><p>讓每個通過驗證的版本都處於可安全發布狀態；是否自動進 production 可另行決定。</p></div><div class="example"><span>具體例子</span><p>Artifact 通過 staging 後，以同一 digest 做 canary，再逐步擴大。</p></div><div class="relevance"><span>本章位置</span><p>CD 重點是可靠、可重複和可回退，不是單純部署更頻繁。</p></div></section><section class="term-card"><h3>Canary release</h3><div><span>白話定義</span><p>先把新版本暴露給少量流量，觀察結果後才擴大。</p></div><div class="example"><span>具體例子</span><p>先讓 1% request 使用新 checkout，再比較錯誤率和 latency。</p></div><div class="relevance"><span>本章位置</span><p>Canary 限制 blast radius；前提是有代表流量、健康指標與快速 rollback。</p></div></section><section class="term-card"><h3>Production</h3><div><span>白話定義</span><p>真實使用者、真實資料與真實商業影響所在的執行環境。</p></div><div class="example"><span>具體例子</span><p>測試環境 timeout 只是紅燈；production timeout 可能讓客戶重複付款。</p></div><div class="relevance"><span>本章位置</span><p>Production 的不確定性使 observability、rollback、capacity 和 incident response 成為必要能力。</p></div></section><section class="term-card"><h3>Error budget</h3><div><span>白話定義</span><p>SLO 允許的不可靠量；100% 減去目標就是可消耗比例。</p></div><div class="example"><span>具體例子</span><p>99.9% 月 SLO 約允許 0.1% valid events 失敗。</p></div><div class="relevance"><span>本章位置</span><p>它把『穩定或快速』的爭論轉成可觀察的共同政策。</p></div></section></div>

## 為什麼需要這一章？

CI 只能驗證已建模情境；production 有真實流量、資料、依賴和容量。一次把新版本部署到全部 instances，未知問題會立即取得最大 blast radius。Delivery 要讓同一 artifact 逐步取得更多 evidence，每一階段都可停止和回退。

### 真實 Use Case

新 cache strategy 在 staging 正常，但只對 production 長尾 key 造成記憶體暴增。Canary 1% 流量能觀察 RSS、latency 和 error budget，超過 threshold 自動停止；全面部署則可能同時 OOM 所有 replicas。

<div class="context-grid">
<section><span>問題壓力</span><p>CI 只能驗證已建模情境；production 有真實流量、資料、依賴和容量。一次把新版本部署到全部 instances，未知問題會立即取得最大 blast radius。Delivery 要讓同一 artifact 逐步取得更多 evidence，每一階段都可停止和回退。</p></section>
<section><span>交付能力</span><p>建立 immutable promotion、progressive rollout、health analysis、automatic rollback 和 feature cleanup。</p></section>
<section><span>真實場景</span><p>新 cache strategy 在 staging 正常，但只對 production 長尾 key 造成記憶體暴增。Canary 1% 流量能觀察 RSS、latency 和 error budget，超過 threshold 自動停止；全面部署則可能同時 OOM 所有 replicas。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>commit → trusted build → immutable artifact digest
                         ↓
                    staging checks
                         ↓
shadow / dark traffic (optional)
                         ↓
canary 1% → health gate → 10% → gate → 50% → 100%
       │                     │
       └──── stop / rollback ┘

code deploy ≠ feature exposure
feature flag → cohort rollout → measure → remove flag</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Continuous Delivery 表示每個通過版本都可安全發布，不一定代表未經判斷自動部署所有變更。Artifact promotion 必須保持相同 digest；環境差異透過 versioned config 注入。Release metadata 包含 owner、risk、changes、rollback 和 expected signals。

Progressive delivery 從 shadow、internal、small cohort 到 wider traffic。Canary comparison 要看 user-centric SLI、resource、dependency 和 business invariants，並處理流量低、cohort 差異和指標延遲。Automatic rollback 只適合可逆且判斷清楚的失敗；schema/data mutation 可能需要 roll-forward 或兼容設計。

Feature flag 分離 deploy 與 release，支援逐群體開啟和 kill switch；但每個 flag 需要 owner、expiry、預設、安全組合和 cleanup。Delivery pipeline 本身應有 audit、least privilege、separation of duties 和 emergency path。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>Build 一次並以 immutable digest 在環境間 promotion，不重新產生 bytes。</p></div><div class="flow-card"><span>2</span><p>Release 定義 risk、owner、expected signals、steps、abort 和 rollback。</p></div><div class="flow-card"><span>3</span><p>以 canary/cohort 漸進擴大，health gate 同時看 SLO、資源和業務 invariant。</p></div><div class="flow-card"><span>4</span><p>不可逆資料變更使用 expand/migrate/contract，不假設 binary rollback 足夠。</p></div><div class="flow-card"><span>5</span><p>Feature flag 有 owner、expiry、kill switch 和 cleanup，pipeline 保存完整 audit。</p></div></div>

## Coding／實務例子

範例用 canary 與 baseline 的 error rate/latency 做簡化 gate。真實分析還要樣本量、統計和 burn rate。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Health:
    error_rate: float
    p99_ms: float
    requests: int

def promote(canary: Health, baseline: Health) -> tuple[bool, list[str]]:
    reasons = []
    if canary.requests < 1000:
        reasons.append("insufficient sample")
    if canary.error_rate > max(0.01, baseline.error_rate * 1.5):
        reasons.append("error regression")
    if canary.p99_ms > baseline.p99_ms * 1.2:
        reasons.append("latency regression")
    return (not reasons, reasons)
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>先要求最小樣本，避免低流量下因零錯誤產生假信心。</p></div><div class="flow-card"><span>2</span><p>Error 同時有 absolute 與 relative threshold，處理 baseline 很低或很高。</p></div><div class="flow-card"><span>3</span><p>P99 comparison 捕捉平均值看不見的長尾退化。</p></div><div class="flow-card"><span>4</span><p>Gate 回傳原因，operator/agent 能知道停止依據並取得更多 evidence。</p></div></div>

## Trade-offs 與 Failure Modes

- Canary 流量不代表高價值或特殊地區使用者，可能漏掉 cohort-specific 問題。
- Rollback binary 不會自動逆轉已寫入的資料與外部 side effects。
- 過度敏感 automatic rollback 在 noisy metrics 下造成 release oscillation。
- Feature flags 永久化會形成複雜狀態空間與未測組合。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 可以生成 release summary、選風險 signals、分析 canary anomalies 和執行已批准 rollback runbook，但 production mutation 必須 bounded。Agent 不應因單一模糊 metric 自行擴大 rollout；健康判斷使用 deterministic policy，AI 提供解釋與補充 hypotheses。自治可從 read-only observation、建議、需批准操作，再逐步到低風險自動回退。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 依 diff/ownership 產生 release risk map 和需要觀察的 signals。</li><li>用 agent 比較 canary/baseline logs、traces 和 cohorts，提出異常候選。</li><li>請 AI 準備 rollback/roll-forward steps，連到實際 runbook 和 artifact。</li><li>讓 agent 在 shadow mode 模擬 promotion decision，與人類歷史決策比較。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Promotion/rollback threshold 由版本化 policy 執行，模型不能任意修改。</li><li>Production agent 使用專用 identity、最小 scope、step/time limit 和 audit。</li><li>Schema、付款、權限等不可逆變更需人類批准與雙向 compatibility。</li><li>AI action 後持續 watch period，異常能 kill switch 並回到 deterministic control。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Delivery 的本質是管理不確定性，不是追求 deployment 數。成熟系統把 evidence 與 blast radius 同步增加：信心小時只給小流量，證據增加才擴大。AI 能讓觀測與操作更快，但若沒有 deterministic gates、immutable artifact 和可逆設計，只會更快放大錯誤。

</aside>

## 動手驗證

1. 為一個 release 寫 1%→10%→50%→100% rollout，每階段 signals 與 abort。
2. 執行 canary gate，測低樣本、baseline 零錯誤和 p99 regression。
3. 列出 binary rollback 無法修復的三種 side effects，設計 roll-forward。
4. 設計 production agent autonomy ladder：read、recommend、approve-to-act、bounded-auto。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Continuous Delivery 是否等於每次 commit 自動上 production？</summary>

不一定。它表示版本始終可發布、流程可重複安全；是否自動 production 依風險和組織政策。

</details>

<details class="qa"><summary>Q2. 為何 artifact 應 build once promote many？</summary>

確保 staging/canary 測過的 bytes 就是 production bytes，避免重建引入新的 dependency 或 nondeterminism。

</details>

<details class="qa"><summary>Q3. Canary 需要哪些最低條件？</summary>

代表性流量、baseline、足夠樣本、user-centric health signals、abort/rollback、owner 和持續觀測。

</details>

<details class="qa"><summary>Q4. Rollback 為何不總是安全？</summary>

資料 migration、外部 side effect 和 protocol change 可能不相容舊 binary，需要 expand/contract 或 roll-forward。

</details>

<details class="qa"><summary>Q5. Feature flag 最大治理需求？</summary>

Owner、expiry、預設、權限、組合測試與 cleanup；否則行為狀態無限增加。

</details>

<details class="qa"><summary>Q6. AI 為何適合解釋而非單獨決定 promotion？</summary>

它能關聯非結構化 evidence，但輸出機率性；核心 gate 應可重現、可稽核，模型作補充。

</details>

<details class="qa"><summary>Q7. Progressive delivery 的核心不變量？</summary>

在未知度仍高時限制 blast radius；只有得到與風險相稱的新 evidence 才擴大曝光。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Continuous Delivery](https://abseil.io/resources/swe-book/html/ch24.html)
- [Site Reliability Engineering — Release Engineering](https://sre.google/sre-book/release-engineering/)
- [Site Reliability Engineering — Reliable Product Launches](https://sre.google/sre-book/reliable-product-launches/)
- [Google Cloud — How Google SRE is using agentic AI](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)

---
