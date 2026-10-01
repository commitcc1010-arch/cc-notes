---
title: "讓變更可以長期維持"
part: 3
as_of: 2026-09-30
---

# Part 3　讓變更可以長期維持

把 style、review、documentation、version control、dependencies 與大型遷移組成可重複的變更系統。

# 第 15 章　Style Guide、Rules 與 Automation

<p class="chapter-question">哪些一致性問題值得制定規則？哪些應交給工具，而不是在 review 中反覆辯論？</p>

<div class="chapter-meta"><span>難度：入門</span><span>Part 3 · 讓變更可以長期維持</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

用可讀性、缺陷預防與互通性決定規則，並把可機械判斷的部分自動化。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node active"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-14-measuring-engineering-productivity-without-gaming"><span>上一站</span><strong>14. Measuring Engineering Productivity without Gaming</strong></a><div class="position-card current"><span>你在這裡</span><strong>15. Style Guide、Rules 與 Automation</strong></div><a class="position-card" href="#chapter-16-code-review-正確性-理解與小型變更"><span>下一站</span><strong>16. Code Review：正確性、理解與小型變更</strong></a></div>

本章位於 **Part 3：讓變更可以長期維持**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Style rule</h3><div><span>白話定義</span><p>為一致性、可讀性或避免缺陷而制定的程式碼規則。</p></div><div class="example"><span>具體例子</span><p>Python formatter 統一引號與縮排，review 不必反覆爭論格式。</p></div><div class="relevance"><span>本章位置</span><p>可機械判斷的規則應由工具執行，人類 review 專注語意。</p></div></section><section class="term-card"><h3>Static analysis</h3><div><span>白話定義</span><p>不實際執行完整程式，就分析程式結構、型別、資料流或規則。</p></div><div class="example"><span>具體例子</span><p>Type checker 在 CI 發現函式可能回傳 <code>None</code> 卻被當整數使用。</p></div><div class="relevance"><span>本章位置</span><p>它為人與 agent 提供快速、確定性、可自動化的 feedback。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section><section class="term-card"><h3>Constraint（限制條件）</h3><div><span>白話定義</span><p>解法必須遵守的硬邊界，例如延遲、相容性、預算、法規或權限。</p></div><div class="example"><span>具體例子</span><p>登入 API p99 必須低於 300ms，而且舊手機版本仍能使用。</p></div><div class="relevance"><span>本章位置</span><p>工程取捨必須先知道 constraint；AI agent 也需要把它寫進完成條件。</p></div></section></div>

## 為什麼需要這一章？

多人 codebase 若每個檔案都有不同命名、格式和錯誤處理，讀者必須先解碼作者個人風格，review 也浪費時間爭論括號與排序。但規則過多、沒有理由或只能靠人記憶，也會提高摩擦並讓重要風險淹沒在細節中。Style system 的目標是降低不必要選擇，不是追求個人審美統一。

### 真實 Use Case

團隊 review 一個 500 行變更，留言一半在引號、import 排序和命名；真正的授權漏洞只得到匆忙檢查。導入 formatter、linter 和少數有理由的規則後，人類注意力可集中在 behavior、security 與 architecture。

<div class="context-grid">
<section><span>問題壓力</span><p>多人 codebase 若每個檔案都有不同命名、格式和錯誤處理，讀者必須先解碼作者個人風格，review 也浪費時間爭論括號與排序。但規則過多、沒有理由或只能靠人記憶，也會提高摩擦並讓重要風險淹沒在細節中。Style system 的目標是降低不必要選擇，不是追求個人審美統一。</p></section>
<section><span>交付能力</span><p>用可讀性、缺陷預防與互通性決定規則，並把可機械判斷的部分自動化。</p></section>
<section><span>真實場景</span><p>團隊 review 一個 500 行變更，留言一半在引號、import 排序和命名；真正的授權漏洞只得到匆忙檢查。導入 formatter、linter 和少數有理由的規則後，人類注意力可集中在 behavior、security 與 architecture。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Repeated confusion / defects
          ↓
rule proposal + rationale + scope
          ↓
can machine decide?
  ├─ yes → formatter / linter / compiler / CI
  └─ no  → examples + reviewer judgment
          ↓
autofix where safe
          ↓
measure noise / exceptions / defect prevention
          ↓
update or remove rule</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

一條好規則應解決可描述的成本，例如避免 shadowed variable、統一 public API 命名、禁止無 deadline RPC。它要有 scope、examples、例外和 enforcement。只有「我們一直這樣寫」不足以要求整個組織支付遵守成本。

Automation 按確定性分層。Formatter 能安全重排 whitespace，應自動修；linter 可辨認 AST pattern，最好給精確位置與 autofix；需要 domain judgment 的設計規則則留給 review。把主觀規則硬做成高噪音 lint，工程師會學會忽略所有警告。

Rule rollout 也需要 migration。新規則若一次讓十萬檔案失敗，會阻塞無關工作；可先 warning、批次修舊 code，再對新/修改 code 強制。規則本身是產品：有 owner、版本、文件、feedback 和 deprecation。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>從真實 review friction 或 defect 找規則理由，不從個人偏好開始。</p></div><div class="flow-card"><span>2</span><p>判斷規則是否可精確機械化；能 autofix 的不要浪費 reviewer 時間。</p></div><div class="flow-card"><span>3</span><p>提供 good/bad examples、例外和申訴路徑，避免文字規則含糊。</p></div><div class="flow-card"><span>4</span><p>以 warning、bulk fix、new-code enforcement 分階段 rollout。</p></div><div class="flow-card"><span>5</span><p>量 false positive、suppression、執行時間和缺陷效果，定期刪除低價值規則。</p></div></div>

## Coding／實務例子

這個 AST linter 禁止沒有 timeout 的 `requests.get`。它比字串搜尋可靠，且錯誤訊息能直接告訴作者如何修正。

```python
import ast

def missing_timeout(source: str) -> list[int]:
    tree = ast.parse(source)
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "get":
            continue
        has_timeout = any(k.arg == "timeout" for k in node.keywords)
        if not has_timeout:
            lines.append(node.lineno)
    return lines

print(missing_timeout('requests.get("https://example.com")'))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>AST 分析理解 call 與 keyword 結構，不會因換行或空白改變失效。</p></div><div class="flow-card"><span>2</span><p>範例仍可能把非 <code>requests</code> 物件的 <code>.get()</code> 誤判，production rule 需 type information。</p></div><div class="flow-card"><span>3</span><p>診斷應附建議，例如 <code>timeout=(1, 3)</code>，降低修復成本。</p></div><div class="flow-card"><span>4</span><p>安全 autofix 需知道團隊 timeout policy；不知道時只提示，不應隨機填值。</p></div></div>

## Trade-offs 與 Failure Modes

- 規則數持續增加卻從不刪除，會讓每次變更支付歷史治理成本。
- False positive 太高會訓練工程師忽略警告或大量 suppression。
- 只在文件寫規則、不在工具或 review checklist 呈現，實際遵守會依記憶而不一致。
- 一次格式化全 repository 若和功能修改混在一起，會破壞 blame 和 review。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 可以解釋規則、產生 autofix 和協助遷移，但自然語言 prompt 不是可靠 enforcement。Agent 可能為了讓 CI 綠燈加入 suppression、刪除檢查或使用不同寫法繞過 pattern。業界較穩健的做法是把規則放進 formatter、linter、type checker 和 policy-as-code，讓 AI 與人都接受同一 deterministic feedback。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 根據 lint 診斷修正多個檔案，並將修改維持為獨立 commit。</li><li>用 agent 分析高頻 review comments，找值得自動化的重複規則。</li><li>請 AI 為規則草擬 rationale、good/bad examples 和 migration plan。</li><li>讓 AI 聚類 suppressions，找出 false positive 或真正架構例外。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Agent 不得修改 lint configuration、baseline 或 suppression 來自行通過檢查。</li><li>新 AI-generated rule 先在歷史 code 和代表性 repositories 量 precision。</li><li>Autofix 必須可重跑、產生穩定 diff，並通過 semantic tests。</li><li>Rule owner 核准 policy；模型只能提出候選和 evidence。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

成熟 style system 的成功標誌是 review 幾乎不再討論可機械決定的細節，同時規則數保持克制。重要規則應靠編譯器和工具成為環境的一部分；需要 judgment 的地方保留原則與範例。AI 讓修改更便宜，但也使中央 guardrails 更重要，否則每個生成片段都可能發明新方言。

</aside>

## 動手驗證

1. 蒐集最近二十則 review comments，分類成可 autofix、可 lint、需 judgment。
2. 執行 AST 範例，加入對 `requests.post` 與 timeout value 範圍的檢查。
3. 為新規則寫 warning→bulk fix→enforce rollout，包含 rollback。
4. 讓 AI 嘗試修復十個 lint findings，檢查它是否加入 suppression 或改變 behavior。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Style guide 最重要的目標是什麼？</summary>

降低不必要差異造成的閱讀、review 和互通成本，並預防已知缺陷；不是把某人的審美變成組織真理。

</details>

<details class="qa"><summary>Q2. 哪些規則應交給 formatter？</summary>

能在不需要 domain judgment 下穩定決定、可安全自動修正的格式規則，例如 whitespace、import 排序和一致排版。

</details>

<details class="qa"><summary>Q3. 為什麼 linter precision 很重要？</summary>

高 false positive 會消耗注意力、促使 suppression，最後連真正警告也失去信任。

</details>

<details class="qa"><summary>Q4. 新規則為何需要 staged rollout？</summary>

大型既有 codebase 可能有大量違規；直接阻塞全部變更會把 migration 成本丟給無關作者，造成繞過。

</details>

<details class="qa"><summary>Q5. AI 為何不能只靠 prompt 遵守規則？</summary>

Prompt 是機率性指引，可能遺漏或被其他 context 覆蓋；deterministic tool 才能對每次變更一致 enforcement。

</details>

<details class="qa"><summary>Q6. 何時應刪除一條規則？</summary>

當原始 defect 不再存在、工具已用更好方式涵蓋、噪音超過收益，或它與新架構衝突時。

</details>

<details class="qa"><summary>Q7. Review 應保留哪些 style judgment？</summary>

命名是否表達 domain、API 是否一致、抽象是否可理解等需語境判斷的部分；仍應引用原則而非純偏好。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Style Guides and Rules](https://abseil.io/resources/swe-book/html/ch08.html)
- [Software Engineering at Google — Static Analysis](https://abseil.io/resources/swe-book/html/ch20.html)
- [GitHub — Review AI-generated code](https://docs.github.com/copilot/tutorials/review-ai-generated-code)
- [DORA 2025 — AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)

---

# 第 16 章　Code Review：正確性、理解與小型變更

<p class="chapter-question">Code review 如何同時保護 production、分享知識，又不成為所有變更的排隊瓶頸？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 3 · 讓變更可以長期維持</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

建立作者與 reviewer 的共同 contract：小而完整的 diff、風險導向審查、快速往返與可驗證結論。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node active"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-15-style-guide-rules-與-automation"><span>上一站</span><strong>15. Style Guide、Rules 與 Automation</strong></a><div class="position-card current"><span>你在這裡</span><strong>16. Code Review：正確性、理解與小型變更</strong></div><a class="position-card" href="#chapter-17-documentation-design-doc-與-api-contract"><span>下一站</span><strong>17. Documentation、Design Doc 與 API Contract</strong></a></div>

本章位於 **Part 3：讓變更可以長期維持**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Code review</h3><div><span>白話定義</span><p>變更進入主線前，由另一個視角檢查正確性、設計、測試、可理解性與風險。</p></div><div class="example"><span>具體例子</span><p>Reviewer 發現 retry 沒有 deadline，避免 production thread 永久耗盡。</p></div><div class="relevance"><span>本章位置</span><p>Review 同時是品質閘門、知識分享與 ownership 轉移。</p></div></section><section class="term-card"><h3>Ownership</h3><div><span>白話定義</span><p>對元件品質、決策、值班與改善負最終責任的明確主體。</p></div><div class="example"><span>具體例子</span><p>平台組維護 deployment API；服務組仍對自己設定錯誤造成的事故負責。</p></div><div class="relevance"><span>本章位置</span><p>AI 可以執行工作但不能承擔組織責任，因此 ownership 不可寫成『模型』。</p></div></section><section class="term-card"><h3>Invariant（不變條件）</h3><div><span>白話定義</span><p>系統任何合法狀態都必須成立的規則。</p></div><div class="example"><span>具體例子</span><p>銀行轉帳前後，所有帳戶餘額總和不應憑空增加。</p></div><div class="relevance"><span>本章位置</span><p>測試、型別和監控常用來保護 invariant；它比描述每一行實作更穩定。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section></div>

## 為什麼需要這一章？

Review 不是找錯字比賽，也不是 reviewer 重寫作者風格。它要確認變更目的合理、behavior 正確、測試可信、系統仍可理解且風險可控制。變更越大，reviewer 能建立的心智模型越差；等待越久，作者又會累積更多修改，使 feedback loop 進一步惡化。

### 真實 Use Case

一個 2,000 行 PR 同時改 schema、business logic、logging 和格式。即使 reviewer 花三小時，也難判斷 migration 是否可 rollback。若拆成 schema expand、雙寫、讀路徑、cleanup 四個可獨立驗證的 changes，每次風險和意圖都更清楚。

<div class="context-grid">
<section><span>問題壓力</span><p>Review 不是找錯字比賽，也不是 reviewer 重寫作者風格。它要確認變更目的合理、behavior 正確、測試可信、系統仍可理解且風險可控制。變更越大，reviewer 能建立的心智模型越差；等待越久，作者又會累積更多修改，使 feedback loop 進一步惡化。</p></section>
<section><span>交付能力</span><p>建立作者與 reviewer 的共同 contract：小而完整的 diff、風險導向審查、快速往返與可驗證結論。</p></section>
<section><span>真實場景</span><p>一個 2,000 行 PR 同時改 schema、business logic、logging 和格式。即使 reviewer 花三小時，也難判斷 migration 是否可 rollback。若拆成 schema expand、雙寫、讀路徑、cleanup 四個可獨立驗證的 changes，每次風險和意圖都更清楚。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Author
  ├─ clear intent / context / risk
  ├─ small coherent diff
  ├─ tests + self-review
  └─ rollout / rollback when needed
          ↓
Automated checks
          ↓
Reviewer
  ├─ contract / correctness / invariants
  ├─ design / readability / ownership
  ├─ security / operations / tests
  └─ classify: blocking / suggestion / question
          ↓
author response → evidence → approval → merge</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Author 先降低 review 成本：說明 why、non-goals、主要風險和驗證證據；diff 只包含一個 coherent change；自動格式與測試已完成。Reviewer 先理解目的，再沿資料流、failure path 和 invariants 檢查，不應從第一行開始只挑局部 syntax。

Comment 要分類。Blocking 表示 correctness、security、contract 或長期維護風險，應附理由；suggestion 是可改善但不阻塞；question 表示 reviewer 模型缺口。若所有偏好都 blocking，review 會成為權力工具。作者也應回覆證據，而非只寫 done。

Review latency 與品質都重要。設定 reviewer coverage、輪值和 escalation，避免變更卡在特定 expert。小批次讓 review 快速，卻仍需完整：不能把必須一起保持 invariant 的修改拆到主線暫時壞掉。可使用 feature flag、兼容層或 hidden path 安全拆分。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>作者先寫 change summary、risk、test evidence、rollout 和 rollback。</p></div><div class="flow-card"><span>2</span><p>自動 checks 先處理格式、type、常見安全和測試，保留人類注意力。</p></div><div class="flow-card"><span>3</span><p>Reviewer 由 intent→contract→failure path→operations→readability 順序建立模型。</p></div><div class="flow-card"><span>4</span><p>留言標記 blocking/suggestion/question，雙方用 evidence 解決而非職級。</p></div><div class="flow-card"><span>5</span><p>追蹤 review wait、round trips、escaped defects 和 reviewer load，改善系統。</p></div></div>

## Coding／實務例子

以下是簡化的 risk-based reviewer router。真實系統可從 changed paths、schema 和 labels 判斷需要哪些 domain owners。

```python
OWNERS = {
    "db/": {"database"},
    "auth/": {"security"},
    "deploy/": {"sre"},
}

def required_reviewers(changed_paths: list[str]) -> set[str]:
    reviewers = {"service-owner"}
    for path in changed_paths:
        for prefix, owners in OWNERS.items():
            if path.startswith(prefix):
                reviewers |= owners
    return reviewers

print(required_reviewers(["auth/token.py", "db/migrations/042.sql"]))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>每個 change 至少需要 service owner，跨特殊風險邊界再增加 domain reviewer。</p></div><div class="flow-card"><span>2</span><p>Router 降低作者不知道該找誰的等待，但不能保證 reviewer 真有 capacity。</p></div><div class="flow-card"><span>3</span><p>Path 規則可能漏掉間接影響，應搭配 dependency 和 semantic checks。</p></div><div class="flow-card"><span>4</span><p>Approval 是責任轉移與共享理解，不只是滿足數量。</p></div></div>

## Trade-offs 與 Failure Modes

- PR 過大會讓 reviewer 只檢查表面，重要風險被大量文字稀釋。
- 過度要求多個 reviewers 會增加 latency，且每人可能假設別人已深入看。
- Rubber stamp 讓流程有 approval 但沒有獨立 evidence。
- 只看 happy path code、不看 rollback、metrics 和 cleanup，會把 production 工作留到部署時。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 可以摘要 diff、尋找相關 contract、生成 review checklist 和指出候選 edge cases，但也可能讓 code volume 超過人類審查能力。AI-generated code 應視為外部 contribution：作者必須能解釋，deterministic checks 先行，reviewer 仍檢查意圖與風險。若使用 AI reviewer，最好與生成變更的 context 分離，避免共享同一盲點。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 產生 change map：入口、state changes、dependencies、failure paths 和 tests。</li><li>用 agent 比較 diff 與 API/schema contracts，列出可能 breaking changes。</li><li>請獨立 AI reviewer 尋找 missing tests、security、timeout 和 rollback 問題。</li><li>讓 AI 將 reviewer comments 聚類成需要修正、需決策與可選建議。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>作者必須執行並理解變更；不得貼上模型輸出後把責任交給 reviewer。</li><li>AI review 不能是唯一 approval，尤其是 auth、data、infra 和 production mutation。</li><li>同一 agent 不得產生、修改 checks 再自行宣告通過；保留獨立 gate。</li><li>限制 diff size 和 task scope，避免產碼速度淹沒 review capacity。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Review 的長期價值是維持 shared ownership 和 codebase 可理解性，而不只是攔 bug。高成熟團隊會把重複 comments 轉成工具、把 expert bottleneck 轉成文件與 training，並根據風險調整 review 深度。AI 可擴大 reviewer 視野，但『看過更多文字』不等於做出更好 judgment。

</aside>

## 動手驗證

1. 將一個大型 change 拆成四個可獨立 merge、保持 invariant 的步驟。
2. 執行 router 範例，加入 documentation-only 與 emergency fix 的 policy。
3. 挑一份 PR，依 intent、contract、failure、operations、readability 五層重做 review。
4. 讓兩個不同 context 的 AI 分別寫 code 與 review，比較共享盲點是否減少。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Code review 的首要目的為何不是找最多錯？</summary>

它要讓變更以可接受風險進入共享 codebase，包含正確性、設計、測試、可理解性和 ownership；留言數不是品質。

</details>

<details class="qa"><summary>Q2. 小型 change 為何更容易高品質 review？</summary>

Reviewer 能建立完整心智模型、feedback 更快，錯誤定位和 revert 更容易；巨大 diff 會超過注意力。

</details>

<details class="qa"><summary>Q3. Blocking comment 應符合什麼條件？</summary>

涉及 correctness、security、contract、顯著維護或 production 風險，並應說明理由與可驗證改善；純偏好通常不應阻塞。

</details>

<details class="qa"><summary>Q4. 多 reviewers 為何可能降低責任感？</summary>

每個人可能只看自己部分或假設他人深入檢查，形成 diffusion of responsibility；需明確 reviewer role。

</details>

<details class="qa"><summary>Q5. AI-generated code 為何應被視為未受信 contribution？</summary>

模型可能缺本地 context、生成不存在 API 或不安全 pattern；必須由 owner 理解並以 checks 和獨立 review 建立 evidence。

</details>

<details class="qa"><summary>Q6. 作者說『tests pass』為何不足？</summary>

需知道哪些 tests、是否涵蓋 contract/failure、環境是否代表 production；同時要檢查測試本身的 oracle。

</details>

<details class="qa"><summary>Q7. 如何讓 review 不成為 bottleneck？</summary>

小批次、清楚 ownership、輪值、SLA、automation、風險分級與將重複 comments 轉工具，而不是取消 review。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Code Review](https://abseil.io/resources/swe-book/html/ch09.html)
- [Software Engineering at Google — Continuous Integration](https://abseil.io/resources/swe-book/html/ch23.html)
- [GitHub — Review AI-generated code](https://docs.github.com/copilot/tutorials/review-ai-generated-code)
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)

---

# 第 17 章　Documentation、Design Doc 與 API Contract

<p class="chapter-question">文件應該解釋什麼，才能在 code、團隊與 AI 都持續變動時仍然有用？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 3 · 讓變更可以長期維持</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

建立分層文件架構：入口地圖、contract、決策原因、操作步驟與可驗證範例各司其職。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node active"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-16-code-review-正確性-理解與小型變更"><span>上一站</span><strong>16. Code Review：正確性、理解與小型變更</strong></a><div class="position-card current"><span>你在這裡</span><strong>17. Documentation、Design Doc 與 API Contract</strong></div><a class="position-card" href="#chapter-18-deprecation-如何安全淘汰舊世界"><span>下一站</span><strong>18. Deprecation：如何安全淘汰舊世界</strong></a></div>

本章位於 **Part 3：讓變更可以長期維持**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Design document</h3><div><span>白話定義</span><p>在昂貴實作前對齊問題、需求、架構、資料流、失敗模式與 rollout 的文件。</p></div><div class="example"><span>具體例子</span><p>支付服務改資料模型前，先描述雙寫、回填、驗證與 rollback。</p></div><div class="relevance"><span>本章位置</span><p>AI 可以協助檢查缺項，但設計責任與風險接受仍由人承擔。</p></div></section><section class="term-card"><h3>ADR（Architecture Decision Record）</h3><div><span>白話定義</span><p>短篇記錄決策背景、選項、選擇、代價與未來重訪條件的文件。</p></div><div class="example"><span>具體例子</span><p>記錄為何選 queue 而非同步 RPC，以及流量降到何種程度時可簡化。</p></div><div class="relevance"><span>本章位置</span><p>ADR 保存『為什麼』，避免人或 AI 只看現況後重複已否決的方案。</p></div></section><section class="term-card"><h3>API Contract</h3><div><span>白話定義</span><p>元件對外承諾的輸入、輸出、錯誤、狀態與相容性規則。</p></div><div class="example"><span>具體例子</span><p><code>get_user(id)</code> 找不到資料時回 <code>None</code> 還是拋 exception，都是 contract。</p></div><div class="relevance"><span>本章位置</span><p>清楚 contract 讓團隊與 agent 能在不理解所有內部細節時安全組合元件。</p></div></section><section class="term-card"><h3>Provenance（來源鏈）</h3><div><span>白話定義</span><p>記錄 artifact、資料或答案由哪些輸入、工具、版本與操作者產生。</p></div><div class="example"><span>具體例子</span><p>Container image 可追到 commit、lockfile、builder identity 和簽章。</p></div><div class="relevance"><span>本章位置</span><p>AI 回答也需保存 retrieval sources、model version 與 tool trace 才能稽核。</p></div></section></div>

## 為什麼需要這一章？

Code 能精確表示系統做什麼，卻常無法說明為何這樣做、哪些 alternatives 被否決、使用者期待與操作風險。文件若只是逐行重述 code，很快過時；若只有宏大架構圖，又無法協助實作者與值班者。關鍵是讓不同 artifact 回答不同問題並有明確 owner。

### 真實 Use Case

新工程師要修改 retry，只看到 `max_attempts=3`，不知道這是付款供應商 contract、歷史事故或任意數字。Design doc/ADR 應保留風險理由；API contract 說明 idempotency；runbook 說明事故時如何停用。三種文件不能互相取代。

<div class="context-grid">
<section><span>問題壓力</span><p>Code 能精確表示系統做什麼，卻常無法說明為何這樣做、哪些 alternatives 被否決、使用者期待與操作風險。文件若只是逐行重述 code，很快過時；若只有宏大架構圖，又無法協助實作者與值班者。關鍵是讓不同 artifact 回答不同問題並有明確 owner。</p></section>
<section><span>交付能力</span><p>建立分層文件架構：入口地圖、contract、決策原因、操作步驟與可驗證範例各司其職。</p></section>
<section><span>真實場景</span><p>新工程師要修改 retry，只看到 <code>max_attempts=3</code>，不知道這是付款供應商 contract、歷史事故或任意數字。Design doc/ADR 應保留風險理由；API contract 說明 idempotency；runbook 說明事故時如何停用。三種文件不能互相取代。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Start page / service map
  ├─→ API contract: 對外承諾什麼
  ├─→ Design doc: 問題、需求、架構、failure、rollout
  ├─→ ADR: 某項取捨為何做出
  ├─→ Runbook: 某狀況下如何安全操作
  ├─→ Tutorial: 新手如何完成第一個任務
  └─→ Reference: schema / config / commands

Code / tests / schema = executable truth
Docs = intent, navigation, judgment, operations</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

文件先辨認 audience 與 question。Tutorial 帶人完成任務；how-to 解特定問題；reference 精確列介面；explanation 建立心智模型。把所有內容塞進同一頁，讀者既找不到快速步驟，也無法深入理解。

Design doc 應在昂貴實作前對齊 problem、goals/non-goals、constraints、architecture/data flow、alternatives、failure modes、security/privacy、rollout/rollback 和 observability。它不是要求預測每行 code，而是讓重大假設在容易修改時被挑戰。ADR 則保存單一持久決策。

文件需接近 source of truth。API schema、CLI help 和 config reference 能生成就不要手抄；code review template 提醒文件更新；links 指向 canonical source。每份文件有 owner、last verified 和 supersedes。最重要的 production 步驟應透過 game day 或 smoke test驗證。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>先寫 audience、task 和文件類型，避免一頁同時服務所有人。</p></div><div class="flow-card"><span>2</span><p>Design doc 在實作前對齊 constraints、failure、rollout 和 alternatives。</p></div><div class="flow-card"><span>3</span><p>Contract 以 schema/tests 保護，文件補充 semantics、examples 和 compatibility。</p></div><div class="flow-card"><span>4</span><p>可從 code 生成的 reference 自動生成，減少雙重維護。</p></div><div class="flow-card"><span>5</span><p>為文件設 owner、review trigger、last verified 和 archive 流程。</p></div></div>

## Coding／實務例子

以下以 dataclass 表示 design doc metadata；CI 可檢查高風險設計是否缺 owner、rollback 或 review date。

```python
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class DesignRecord:
    owner: str
    problem: str
    rollback: str
    decision_date: date
    review_on: date

def validate(record: DesignRecord) -> list[str]:
    missing = []
    for field, value in vars(record).items():
        if value in ("", None):
            missing.append(field)
    if record.review_on <= record.decision_date:
        missing.append("review_on must be later")
    return missing
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Schema 只能檢查結構存在，不能判斷 rollback 是否真的可行。</p></div><div class="flow-card"><span>2</span><p>Review date 讓 assumptions 有重新檢查點，特別適合暫時 workaround。</p></div><div class="flow-card"><span>3</span><p>Owner 是回應未來 feedback 的人，不必是唯一作者。</p></div><div class="flow-card"><span>4</span><p>真實 validation 可依資料、權限和 blast radius 要求不同章節。</p></div></div>

## Trade-offs 與 Failure Modes

- 文件 review 變成文法審查，卻沒有挑戰核心 assumptions。
- 圖與文字重複描述 topology，系統一變就互相矛盾。
- 把聊天、issue 和會議記錄當永久文件，缺少結論與 canonical 入口。
- 所有文件都標為重要，沒有 archive，搜尋品質會逐年下降。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 讓文件草擬、摘要與 code explanation 更便宜，也可能大量生成可信度不明的文字。Agent 需要文件作 context，因此文件結構、metadata、provenance 和 freshness 比以前更重要。最佳實務是讓 AI 從 code/schema/tests 草擬，再由 owner 校正 intent；高風險 runbook 需實際演練，不能因生成流暢就視為可操作。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>用 AI 從 diff 草擬 release note、API example 和 design change summary。</li><li>讓 agent 比較 code/schema 與 docs，列出 drift 候選和缺少連結。</li><li>以 AI 為長 design doc 產生不同 audience 的導讀，但保留 canonical 原文。</li><li>讓 AI 在 review 中扮演新手、SRE、安全與未來 maintainer 提出問題。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>AI 生成內容必須標示 owner、來源與驗證日期，不能匿名成為權威。</li><li>禁止把秘密、客戶資料或未公開設計送入未批准模型。</li><li>Runbook 的 destructive commands 必須有 dry-run、scope check 和人類核准。</li><li>Summary 不能取代原始 contract/ADR；高風險決策要可追回完整 evidence。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

最有價值的文件不是最長，而是縮短正確心智模型的建立時間。專家會刻意把可執行 truth 留給 code、test、schema，把 why、trade-off、導航和人類操作留給文字，並建立更新觸發。AI 使文字供給近乎無限，因此可信來源與刪除能力會比寫作速度更稀缺。

</aside>

## 動手驗證

1. 為一個服務建立 start page，只連結 contract、design、dashboard、runbook 和 owner。
2. 執行 metadata validation，新增 `security_review` 作為高風險條件欄位。
3. 把一份逐行重述 code 的文件改寫成 why、constraints 和 examples。
4. 讓 AI 草擬 design doc，人工標記每個沒有本地 evidence 的推測。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Code 已存在，為什麼還需要文件？</summary>

Code 精確描述執行，但通常不保存問題背景、被否決方案、使用者語意、操作方式和決策理由；這些影響未來修改。

</details>

<details class="qa"><summary>Q2. Design doc 與 ADR 差別？</summary>

Design doc 描述一個較完整系統/變更；ADR 聚焦單一持久決策與取捨，可從 design doc 抽出並獨立更新。

</details>

<details class="qa"><summary>Q3. 哪些文件內容應自動生成？</summary>

能由 schema、types、commands 和 source 確定推導的 reference，減少重複；意圖和 judgment 仍需人負責。

</details>

<details class="qa"><summary>Q4. 為什麼 runbook 需要演練？</summary>

文字正確不代表權限、命令、環境和時間壓力下可行；game day 才能驗證完整操作 contract。

</details>

<details class="qa"><summary>Q5. AI 生成文件最大風險是什麼？</summary>

流暢文字掩蓋缺乏來源、錯誤 assumptions 和過時內容，並大量增加搜尋噪音。

</details>

<details class="qa"><summary>Q6. 如何讓 agent 更容易使用文件？</summary>

提供短入口、清楚 heading、metadata、canonical links、可執行命令、版本和 provenance，而非單一巨大無結構頁面。

</details>

<details class="qa"><summary>Q7. 何時應 archive 文件？</summary>

內容被新來源 supersede、owner 不再維護、適用系統已淘汰，或搜尋造成混淆時；保留歷史但降低其 canonical 排名。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Documentation](https://abseil.io/resources/swe-book/html/ch10.html)
- [Software Engineering at Google — Code Review](https://abseil.io/resources/swe-book/html/ch09.html)
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)
- [Google Cloud — Agent observability](https://docs.cloud.google.com/stackdriver/docs/observability/agent-observability)

---

# 第 18 章　Deprecation：如何安全淘汰舊世界

<p class="chapter-question">為什麼刪除一個舊 API 常比建立新 API 更困難？如何避免永遠背負兩套系統？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 3 · 讓變更可以長期維持</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

建立 announce、instrument、migrate、enforce、remove 的完整 deprecation pipeline。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node active"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-17-documentation-design-doc-與-api-contract"><span>上一站</span><strong>17. Documentation、Design Doc 與 API Contract</strong></a><div class="position-card current"><span>你在這裡</span><strong>18. Deprecation：如何安全淘汰舊世界</strong></div><a class="position-card" href="#chapter-19-version-control-branches-與-small-batches"><span>下一站</span><strong>19. Version Control、Branches 與 Small Batches</strong></a></div>

本章位於 **Part 3：讓變更可以長期維持**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Deprecation</h3><div><span>白話定義</span><p>宣布某介面將停止支援，提供替代方案、遷移期與最終移除程序。</p></div><div class="example"><span>具體例子</span><p>舊 API 先發 warning、量測剩餘流量、提供 adapter，最後才刪除。</p></div><div class="relevance"><span>本章位置</span><p>Deprecation 是協調問題，不只是搜尋後直接 rename。</p></div></section><section class="term-card"><h3>Backward compatibility</h3><div><span>白話定義</span><p>新版本仍能服務舊呼叫者、舊資料或舊協定的能力。</p></div><div class="example"><span>具體例子</span><p>新增 optional JSON field 通常相容；把字串改為物件可能使舊 client 崩潰。</p></div><div class="relevance"><span>本章位置</span><p>大型系統無法原子更新所有使用者，因而需要 migration window。</p></div></section><section class="term-card"><h3>Lifecycle（生命週期）</h3><div><span>白話定義</span><p>一項變更從需求、設計、實作、驗證、發布、運行到淘汰的完整時間線。</p></div><div class="example"><span>具體例子</span><p>新增欄位不只改 schema，還要 migration、雙讀寫、監控、清除舊格式。</p></div><div class="relevance"><span>本章位置</span><p>SWE 管理變更的長期成本；SRE 管理變更進入 production 後的風險。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section></div>

## 為什麼需要這一章？

新增通常只需讓新路徑工作；刪除則要證明所有重要 consumers 已離開、資料已轉換、rollback 不再需要。只標記 deprecated 不會自動發生遷移，永久兼容又使每次變更要維護兩套 behavior。淘汰是產品、協調與技術共同問題。

### 真實 Use Case

公司要移除 v1 authentication token。內部 repository 已沒有呼叫，但仍有舊手機、合作夥伴 batch 和離線設備。若直接關閉會造成長尾事故；若沒有 deadline，安全風險永遠存在。

<div class="context-grid">
<section><span>問題壓力</span><p>新增通常只需讓新路徑工作；刪除則要證明所有重要 consumers 已離開、資料已轉換、rollback 不再需要。只標記 deprecated 不會自動發生遷移，永久兼容又使每次變更要維護兩套 behavior。淘汰是產品、協調與技術共同問題。</p></section>
<section><span>交付能力</span><p>建立 announce、instrument、migrate、enforce、remove 的完整 deprecation pipeline。</p></section>
<section><span>真實場景</span><p>公司要移除 v1 authentication token。內部 repository 已沒有呼叫，但仍有舊手機、合作夥伴 batch 和離線設備。若直接關閉會造成長尾事故；若沒有 deadline，安全風險永遠存在。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>inventory consumers + risk
        ↓
announce replacement / timeline / support
        ↓
instrument old usage (privacy-safe)
        ↓
provide adapter / codemod / migration docs
        ↓
warn → rate limit / block new users → final enforcement
        ↓
observe zero-use window + rollback plan
        ↓
remove code / data / flags / metrics / docs</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

第一步是建立 consumer inventory：source call sites、runtime clients、data formats、scheduled jobs 和外部 contracts。接著提供可行替代，說明價值、差異、deadline、支援與例外。只宣布結束日期卻沒有 migration tooling，等於把成本完全轉嫁使用者。

Telemetry 應辨認誰仍在使用舊路徑、頻率和最後時間，同時保護隱私。Migration 可透過 compatibility adapter、dual read/write、backfill、codemod 和 support campaign。對新 consumers 先禁止使用，避免舊需求繼續增加；長尾再逐步 warning、quota 或 staged shutdown。

Remove 要完整。刪 endpoint 後還要清 schema、flags、dashboards、alerts、docs、tests、permissions 和 on-call knowledge。Zero usage 一天通常不足，需要涵蓋週期性 job、季末流程和離線 client。最後保留 decision record，避免未來重新引入同一風險。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>盤點 source、runtime、data 和 external consumers，指定 migration owner。</p></div><div class="flow-card"><span>2</span><p>發布替代方案、差異、deadline、support 和 exception policy。</p></div><div class="flow-card"><span>3</span><p>加入 privacy-safe usage telemetry，阻止新 consumers 採用舊 API。</p></div><div class="flow-card"><span>4</span><p>提供 adapter、codemod、backfill 和 staged enforcement，持續聯繫長尾。</p></div><div class="flow-card"><span>5</span><p>經完整 zero-use window 後移除所有 code、data、flags、docs 和 alerts。</p></div></div>

## Coding／實務例子

範例用 usage registry 決定是否可移除。它明確考慮週期窗口，而不是只看今天流量。

```python
from datetime import date, timedelta

last_seen = {
    "mobile-v1": date(2026, 8, 2),
    "partner-batch": date(2026, 9, 28),
}

def blockers(today: date, quiet_period: timedelta) -> list[str]:
    cutoff = today - quiet_period
    return [
        consumer for consumer, seen in last_seen.items()
        if seen >= cutoff
    ]

print(blockers(date(2026, 9, 30), timedelta(days=60)))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p><code>partner-batch</code> 最近仍使用，不能因 repository 無 call site 就移除。</p></div><div class="flow-card"><span>2</span><p>Quiet period 要涵蓋使用週期；年度流程甚至需要更長證據或主動確認。</p></div><div class="flow-card"><span>3</span><p>Last seen metadata 本身需有資料來源、retention 和身份保護。</p></div><div class="flow-card"><span>4</span><p>Blocker 清空後仍需 final canary/shutdown、rollback 和 support monitoring。</p></div></div>

## Trade-offs 與 Failure Modes

- Deprecated warning 沒有 owner 和 deadline，只會成為永久背景噪音。
- 以 client identifier 記錄使用量若未最小化，可能造成隱私或安全風險。
- Compat adapter 改變 semantics 時，consumer 可能表面遷移但 behavior 已錯。
- 只刪 runtime code、不清資料和 permissions，仍留下攻擊面與維護成本。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 非常適合搜尋 call sites、產生 codemod、草擬 migration PR 和支援回覆，使 deprecation 的機械成本下降。但它看不到所有外部或 runtime consumers，也可能用 adapter 隱藏不相容 semantics。可靠做法是 AI + AST/source inventory + telemetry + owner confirmation 四種 evidence 結合。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 agent 產生 consumer inventory，標記靜態、動態與未知來源。</li><li>用 AI 草擬 codemod 和 migration PR，再以 contract tests 比較 behavior。</li><li>請 AI 分析 usage trend 和聯繫記錄，找長尾與未回覆 owners。</li><li>移除前讓 agent 搜尋 flags、docs、metrics、permissions 和 dead tests。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>不得只依 AI/source search 宣稱零使用；必須有 runtime 和外部 evidence。</li><li>Codemod 需 dry-run、AST constraint、small batches 和可逆 commits。</li><li>涉及資料轉換時先備份、驗證 invariants，禁止模型自由產生 destructive SQL。</li><li>Final shutdown 需人類 decision owner、canary、rollback 與 support coverage。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Deprecation 是架構保持簡單的主要工具。組織若只獎勵 launch，新介面會不斷增加而舊路徑永不消失。專家會在建立 v2 時就編列 migration 和 cleanup 成本，並把 consumer friction 當產品問題，而不是責怪使用者升級太慢。

</aside>

## 動手驗證

1. 為一個舊 API 寫完整 deprecation brief：replacement、owners、deadline、telemetry、support。
2. 執行範例，加入每季一次的 consumer，重新選 quiet period。
3. 設計 expand–migrate–contract 的資料 migration，列每階段 rollback。
4. 讓 AI 產生 codemod，使用十個代表性 fixtures 驗證 semantic equivalence。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. 為何刪除通常比新增難？</summary>

刪除需證明所有 consumers、資料和操作依賴已遷移；新增只需讓新路徑存在。未知長尾使負面證明昂貴。

</details>

<details class="qa"><summary>Q2. Deprecated 標記為何不足？</summary>

它只傳達意圖，沒有 replacement、tooling、owner、deadline 和 enforcement 時，使用者沒有動力或能力遷移。

</details>

<details class="qa"><summary>Q3. Zero usage 要觀察多久？</summary>

依使用週期、離線 client、季節性和風險決定；必須涵蓋合理長尾，或取得 owners 主動確認。

</details>

<details class="qa"><summary>Q4. 為何要先阻止新 consumers？</summary>

否則遷移速度可能低於新增速度，舊路徑永遠無法收斂；先封住入口才能處理存量。

</details>

<details class="qa"><summary>Q5. AI 在 deprecation 中最適合做什麼？</summary>

搜尋、分類、草擬 codemod、建立 PR、整理 usage 和 cleanup checklist；是否相容與可移除仍需 tests、telemetry 和 owner。

</details>

<details class="qa"><summary>Q6. 移除 endpoint 後還要清什麼？</summary>

資料、schema、flags、permissions、dashboards、alerts、tests、docs、runbooks、support 和 dependency，才能真正降低複雜度。

</details>

<details class="qa"><summary>Q7. 成功 deprecation 的產品觀點是什麼？</summary>

讓替代路徑價值清楚、遷移成本低、支援可得，並對 deadline 公平執行；不是把所有痛苦交給 consumers。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Deprecation](https://abseil.io/resources/swe-book/html/ch15.html)
- [Software Engineering at Google — Large-Scale Changes](https://abseil.io/resources/swe-book/html/ch22.html)
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)
- [DORA 2025 — AI Capabilities Model](https://cloud.google.com/blog/products/ai-machine-learning/introducing-doras-inaugural-ai-capabilities-model)

---

# 第 19 章　Version Control、Branches 與 Small Batches

<p class="chapter-question">Git 不只是備份：如何用歷史、branch、commit 和 merge 策略降低整合與回復風險？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 3 · 讓變更可以長期維持</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

讓 main 保持可驗證、小批次快速整合、每個 commit 可理解可回退，並分清 source history 與 release。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node active"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-18-deprecation-如何安全淘汰舊世界"><span>上一站</span><strong>18. Deprecation：如何安全淘汰舊世界</strong></a><div class="position-card current"><span>你在這裡</span><strong>19. Version Control、Branches 與 Small Batches</strong></div><a class="position-card" href="#chapter-20-dependency-management-與-supply-chain"><span>下一站</span><strong>20. Dependency Management 與 Supply Chain</strong></a></div>

本章位於 **Part 3：讓變更可以長期維持**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Version control</h3><div><span>白話定義</span><p>保存變更歷史、身份、分支與可還原狀態的系統。</p></div><div class="example"><span>具體例子</span><p>Git commit 讓團隊看見誰在何時為何改動，並可 revert 壞版本。</p></div><div class="relevance"><span>本章位置</span><p>Coding agent 必須在可審查 branch/worktree 中工作，不能偷偷修改未知狀態。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section><section class="term-card"><h3>Provenance（來源鏈）</h3><div><span>白話定義</span><p>記錄 artifact、資料或答案由哪些輸入、工具、版本與操作者產生。</p></div><div class="example"><span>具體例子</span><p>Container image 可追到 commit、lockfile、builder identity 和簽章。</p></div><div class="relevance"><span>本章位置</span><p>AI 回答也需保存 retrieval sources、model version 與 tool trace 才能稽核。</p></div></section><section class="term-card"><h3>Ownership</h3><div><span>白話定義</span><p>對元件品質、決策、值班與改善負最終責任的明確主體。</p></div><div class="example"><span>具體例子</span><p>平台組維護 deployment API；服務組仍對自己設定錯誤造成的事故負責。</p></div><div class="relevance"><span>本章位置</span><p>AI 可以執行工作但不能承擔組織責任，因此 ownership 不可寫成『模型』。</p></div></section></div>

## 為什麼需要這一章？

版本控制保存的不只是檔案內容，還有誰、何時、為何做了變更，以及哪些狀態可以重現。長壽 branch 讓團隊延後整合，差異和 conflict 持續累積；巨大 commit 混合重構與功能，讓 review、bisect 和 revert 都失去精度。

### 真實 Use Case

團隊開發功能三個月後才合併，期間 main 的 schema、library 和部署流程都改變。最後 integration week 同時處理數百 conflicts 和 behavior changes。若使用 hidden path、feature flag 和小型 commits，每天整合可把風險分散成可觀察步驟。

<div class="context-grid">
<section><span>問題壓力</span><p>版本控制保存的不只是檔案內容，還有誰、何時、為何做了變更，以及哪些狀態可以重現。長壽 branch 讓團隊延後整合，差異和 conflict 持續累積；巨大 commit 混合重構與功能，讓 review、bisect 和 revert 都失去精度。</p></section>
<section><span>交付能力</span><p>讓 main 保持可驗證、小批次快速整合、每個 commit 可理解可回退，並分清 source history 與 release。</p></section>
<section><span>真實場景</span><p>團隊開發功能三個月後才合併，期間 main 的 schema、library 和部署流程都改變。最後 integration week 同時處理數百 conflicts 和 behavior changes。若使用 hidden path、feature flag 和小型 commits，每天整合可把風險分散成可觀察步驟。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>small change
  ↓
local checks → commit with intent
  ↓
short-lived branch / review
  ↓
CI → merge main
  ↓
immutable artifact / release tag
  ↓
canary / production

feature availability ≠ code integration
整合可早，曝光可由 flag / config 晚</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Mainline 應代表可建置、可測且接近可發布的共享狀態。Short-lived branch 降低 divergence；功能尚未完成時，可用 branch by abstraction、feature flag 或未連接入口把 code 安全整合。重點是把 code integration 與 user exposure 分開。

Commit 應是 coherent unit：說明 why、保持 invariants、通過 checks、可獨立 revert。純機械 refactor 與 semantic change 分開，使 reviewer 和 `git bisect` 更可信。History 不需為美觀任意重寫共享分支；provenance 和協作安全優先。

Source version、artifact 和 deployment 要能串接。Production 應知道執行哪個 commit、build inputs、configuration 和 rollout event。Git tag 只是名稱，immutable digest 和 build provenance 才能證明 bytes。Emergency revert 也要走可審查、可監控流程。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>將工作拆成保持 main invariants 的小型 coherent commits。</p></div><div class="flow-card"><span>2</span><p>使用短命 branch，頻繁同步 main，避免延後 integration feedback。</p></div><div class="flow-card"><span>3</span><p>以 flag、abstraction 或 dark launch 分離 code merge 與 user exposure。</p></div><div class="flow-card"><span>4</span><p>Build artifact 綁定 commit、dependencies 和 digest，deployment 記錄同一 identity。</p></div><div class="flow-card"><span>5</span><p>保留 revert、bisect 和 audit 能力，避免混合機械與語意變更。</p></div></div>

## Coding／實務例子

這個 pre-commit 概念檢查阻止巨大混合變更。真實實作可從 Git diff 取得行數、paths 和 labels。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CommitPlan:
    changed_lines: int
    migrations: int
    mechanical_only: bool
    tests_pass: bool

def review_risks(plan: CommitPlan) -> list[str]:
    risks = []
    if plan.changed_lines > 800:
        risks.append("large diff: explain or split")
    if plan.migrations and plan.mechanical_only:
        risks.append("migration cannot be labeled mechanical")
    if not plan.tests_pass:
        risks.append("main invariant would be broken")
    return risks
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>800 行不是普遍上限，只是觸發解釋或拆分的 signal。</p></div><div class="flow-card"><span>2</span><p>Migration 屬 semantic change，不能藏在 formatter/codemod commit。</p></div><div class="flow-card"><span>3</span><p><code>tests_pass</code> 代表 main 的最小 integration contract，仍需依風險增加 checks。</p></div><div class="flow-card"><span>4</span><p>Policy 應允許 generated fixtures 等合理大變更，但要求清楚 provenance。</p></div></div>

## Trade-offs 與 Failure Modes

- 追求極小 commit 若每個中間狀態無法 build，反而破壞 bisect 和 main。
- Feature flags 永不清理會形成組合爆炸和隱藏 dead code。
- 長壽 release branch 可能需要 backport，增加多版本修復成本。
- 只在 tag 記版本，卻無法重現 build dependencies，仍不足以稽核。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

Coding agent 應在隔離 worktree/branch 工作，頻繁 checkpoint，提供清楚 diff summary 和測試證據。AI 能快速修改大量檔案，更需要 scope、small batch 和 reviewable commits；否則一次生成就會跨越多個 ownership boundaries。Agent 不應 force-push、改寫未知使用者變更或自行刪除失敗檔案。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 agent 先提出 commit plan，將 refactor、behavior、migration 和 tests 分離。</li><li>每個可驗證里程碑 checkpoint，失敗時能回到已知狀態。</li><li>用 AI 產生 diff summary、risk paths 和建議 reviewers，附實際檔案。</li><li>讓 agent 協助 bisect 候選與整理 history，但由人選擇 rollback。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Agent 使用獨立 branch/worktree，啟動前先檢查 dirty state，不能覆蓋使用者修改。</li><li>禁止 destructive reset、force-push 和 broad delete，除非明確授權與精確 scope。</li><li>Commit 前執行 required checks；測試失敗不得以刪除或 skip 解決。</li><li>Artifact 和 agent trace 保存 commit identity，production action 可追溯。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

成熟 VCS 策略的核心是縮短 integration distance，而非宗教式選 branch 名稱。只要 main 有強 feedback、變更小、release 可重現、flag 有生命周期，團隊可以依產品節奏選細節。AI 時代尤其要保護 history 作為人類理解與 incident forensic 的證據。

</aside>

## 動手驗證

1. 把一個跨 schema/API/UI 的功能拆成保持 main 可運作的 commits。
2. 執行風險檢查，增加 ownership boundary 和 generated-file 例外。
3. 從 production 版本追到 commit、artifact digest、build 和 deploy event。
4. 給 agent 一個 dirty worktree，設計啟動前檢查與安全停止訊息。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Short-lived branch 為何降低風險？</summary>

它縮短與 main 的差異，讓 conflicts、API 變化和測試問題更早、更小地被發現。

</details>

<details class="qa"><summary>Q2. Code merge 和功能發布如何分離？</summary>

使用 feature flag、branch by abstraction、dark launch 或尚未接線入口，先整合 code，再逐步曝光。

</details>

<details class="qa"><summary>Q3. 好 commit 具備哪些特徵？</summary>

目的 coherent、保持 invariants、通過 checks、message 解釋 why、可獨立 review/revert，且不混合無關機械修改。

</details>

<details class="qa"><summary>Q4. Feature flag 的主要長期風險？</summary>

未清理 flags 產生行為組合、dead code 和測試負擔；每個 flag 需 owner、expiry 和 cleanup。

</details>

<details class="qa"><summary>Q5. Tag 為何不足以重現 production？</summary>

Build 還依賴 dependencies、toolchain、configuration 和 process；需要 immutable artifact digest 和 provenance。

</details>

<details class="qa"><summary>Q6. Agent 為何特別需要 small batches？</summary>

它可瞬間產生大量 diff，但 reviewer attention 和系統 evidence 不會同比增加；小批次限制錯誤範圍並改善理解。

</details>

<details class="qa"><summary>Q7. 何時可以接受大型 commit？</summary>

Generated files、機械 codemod 或不可分割 invariant 可能合理，但應與 semantic change 分開、具 provenance、專用 checks 和清楚說明。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Version Control and Branch Management](https://abseil.io/resources/swe-book/html/ch16.html)
- [Software Engineering at Google — Continuous Integration](https://abseil.io/resources/swe-book/html/ch23.html)
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)
- [GitHub — Review AI-generated code](https://docs.github.com/copilot/tutorials/review-ai-generated-code)

---

# 第 20 章　Dependency Management 與 Supply Chain

<p class="chapter-question">加一個套件只需一行，為什麼它可能帶來多年升級、安全、可靠性和退出成本？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 3 · 讓變更可以長期維持</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

用 inventory、version policy、lockfile、provenance、update cadence 和 removal plan 管理依賴。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node active"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-19-version-control-branches-與-small-batches"><span>上一站</span><strong>19. Version Control、Branches 與 Small Batches</strong></a><div class="position-card current"><span>你在這裡</span><strong>20. Dependency Management 與 Supply Chain</strong></div><a class="position-card" href="#chapter-21-code-search-static-analysis-與-large-scale-changes"><span>下一站</span><strong>21. Code Search、Static Analysis 與 Large-Scale Changes</strong></a></div>

本章位於 **Part 3：讓變更可以長期維持**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Dependency</h3><div><span>白話定義</span><p>程式運作所依賴的 library、service、tool、資料格式或團隊。</p></div><div class="example"><span>具體例子</span><p>Web service 依賴資料庫 driver 和外部付款 API。</p></div><div class="relevance"><span>本章位置</span><p>Dependency 帶來升級、供應鏈、安全與可用性成本；AI 可能捏造不存在的套件。</p></div></section><section class="term-card"><h3>Build</h3><div><span>白話定義</span><p>把 source、dependencies 與設定轉成可部署 artifact 的可重複流程。</p></div><div class="example"><span>具體例子</span><p>將 Python application 和鎖定套件打成帶 digest 的 container image。</p></div><div class="relevance"><span>本章位置</span><p>Build graph 和 provenance 讓團隊知道 production 到底執行哪組輸入。</p></div></section><section class="term-card"><h3>Provenance（來源鏈）</h3><div><span>白話定義</span><p>記錄 artifact、資料或答案由哪些輸入、工具、版本與操作者產生。</p></div><div class="example"><span>具體例子</span><p>Container image 可追到 commit、lockfile、builder identity 和簽章。</p></div><div class="relevance"><span>本章位置</span><p>AI 回答也需保存 retrieval sources、model version 與 tool trace 才能稽核。</p></div></section><section class="term-card"><h3>Constraint（限制條件）</h3><div><span>白話定義</span><p>解法必須遵守的硬邊界，例如延遲、相容性、預算、法規或權限。</p></div><div class="example"><span>具體例子</span><p>登入 API p99 必須低於 300ms，而且舊手機版本仍能使用。</p></div><div class="relevance"><span>本章位置</span><p>工程取捨必須先知道 constraint；AI agent 也需要把它寫進完成條件。</p></div></section></div>

## 為什麼需要這一章？

Dependency 把別人的能力帶入系統，也把其 bugs、release policy、license、transitive graph 和 availability 帶進來。免費下載不等於免費維護；每個版本落後都會累積未來 migration distance。外部 service 更有 latency、quota、資料和 outage coupling。

### 真實 Use Case

團隊為一個字串 helper 引入大型套件，套件又帶入 80 個 transitive dependencies。兩年後出現安全漏洞，但升級跨越三個 major versions 並破壞 runtime。最初節省一小時，後來支付數週 remediation。

<div class="context-grid">
<section><span>問題壓力</span><p>Dependency 把別人的能力帶入系統，也把其 bugs、release policy、license、transitive graph 和 availability 帶進來。免費下載不等於免費維護；每個版本落後都會累積未來 migration distance。外部 service 更有 latency、quota、資料和 outage coupling。</p></section>
<section><span>交付能力</span><p>用 inventory、version policy、lockfile、provenance、update cadence 和 removal plan 管理依賴。</p></section>
<section><span>真實場景</span><p>團隊為一個字串 helper 引入大型套件，套件又帶入 80 個 transitive dependencies。兩年後出現安全漏洞，但升級跨越三個 major versions 並破壞 runtime。最初節省一小時，後來支付數週 remediation。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Need / capability
      ↓
build vs buy vs service
      ↓
evaluate:
API fit · maintenance · security · license
version policy · transitive graph · data/availability · exit
      ↓
pin / lock / verify provenance
      ↓
continuous update + tests + vulnerability response
      ↓
deprecate / replace / remove</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

先評估是否真的需要 dependency，以及它是否比自行維護更便宜。選擇時看 maintainer 活躍、release notes、security process、license、API surface、platform support 和 transitive size。對 service 還要看 SLO、data residency、rate limit、fallback 和 contract。

Version policy 平衡重現與更新。Lockfile 固定解析結果，使 build 可重現；automation 定期提出小升級，避免多年後一次跨越巨大差異。Semantic version 只是供應者宣告，仍需 contract tests 和 canary。Transitive dependencies 也要 inventory，因為漏洞不會因你未直接 import 就消失。

Supply-chain security 需要 provenance、checksum/signature、可信 registry、最小 build permission 和 SBOM。Dependency compromise 可能在 install/build 階段執行 code；sandbox 和 egress control 很重要。最後要有 exit strategy：wrapper seam、data export 和替代方案。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>先比較 build/buy/service，量完整生命週期和退出成本。</p></div><div class="flow-card"><span>2</span><p>審查 API、維護、安全、license、transitive graph 和 operational contract。</p></div><div class="flow-card"><span>3</span><p>用 lockfile、可信來源、checksum/signature、SBOM 和 hermetic build 固定輸入。</p></div><div class="flow-card"><span>4</span><p>定期小步更新，依 tests、vulnerability severity 和 canary 自動化。</p></div><div class="flow-card"><span>5</span><p>透過 wrapper、contract 和 data portability 保留替換能力，刪除無用依賴。</p></div></div>

## Coding／實務例子

用 allowlist 與 metadata 做最小 dependency gate。真實系統應接 registry、license scanner、SBOM 和 vulnerability database。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Package:
    name: str
    source: str
    pinned: bool
    license: str
    maintained: bool

ALLOWED_SOURCES = {"https://packages.example.internal"}
ALLOWED_LICENSES = {"Apache-2.0", "MIT", "BSD-3-Clause"}

def dependency_risks(pkg: Package) -> list[str]:
    checks = {
        "untrusted source": pkg.source not in ALLOWED_SOURCES,
        "not pinned": not pkg.pinned,
        "license review required": pkg.license not in ALLOWED_LICENSES,
        "maintenance risk": not pkg.maintained,
    }
    return [name for name, failed in checks.items() if failed]
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Source allowlist 降低 typosquatting 與未知 registry，但內部 mirror 也要驗證 upstream。</p></div><div class="flow-card"><span>2</span><p>Pinned 讓 build 重現，不表示版本安全；仍需持續 update。</p></div><div class="flow-card"><span>3</span><p>License policy 依組織與使用方式不同，不能把範例當法律意見。</p></div><div class="flow-card"><span>4</span><p>Maintenance 是多維 signal，需看 release、issues、bus factor 和替代品。</p></div></div>

## Trade-offs 與 Failure Modes

- 永遠不更新看似穩定，實際會累積 security 和 compatibility debt。
- 自動更新直接 merge 而無代表性 tests，可能把 upstream regression 快速帶入 production。
- 只掃 direct dependency 會漏掉大部分 transitive supply-chain surface。
- Wrapper 過厚可能重寫整個第三方 API，反而增加自有維護成本。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI coding agents 常會建議或直接加入套件，甚至 hallucinate 不存在或惡意名稱。Dependency 增加必須經 deterministic policy：registry allowlist、existence、版本、license、vulnerability、maintenance 和 provenance。模型可比較 alternatives 與閱讀 release notes，但不能因「popular」就自行擴大 supply-chain surface。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 比較既有 internal library、標準函式庫與第三方 alternatives。</li><li>用 agent 摘要 changelog、breaking changes 和 migration plan，附官方來源。</li><li>請 AI 分析 dependency graph，找重複 major versions 和未使用套件。</li><li>讓 agent 草擬小型 upgrade PR，執行 contract、integration 和 performance tests。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>禁止 agent 從未批准 registry 安裝套件或執行任意 install scripts。</li><li>Dependency change 必須顯式列在 diff，通過 license、SBOM、signature 和 vulnerability gates。</li><li>不存在或名稱相近套件要 fail closed，不能由模型猜測替代。</li><li>高風險 runtime/service dependency 需 owner review、SLO、fallback 和 exit plan。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Dependency policy 的目的不是零依賴，而是讓每項借來的能力有可信來源、持續更新和退出路徑。專家會特別警惕「小功能、大圖譜」與組織同時維護多個等價版本。AI 可降低升級勞力，卻也會降低新增門檻；因此新增 gate 要比以前更清楚。

</aside>

## 動手驗證

1. 選一個 dependency，畫 direct/transitive graph，記錄 owner、license、版本和最後更新。
2. 執行範例，加入 checksum、vulnerability severity 和 transitive count policy。
3. 比較一次小步升級與跨三個 major 的 migration 成本。
4. 要求 AI 建議套件，然後逐項驗證 package existence、registry、maintenance 和 license。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Lockfile 解決什麼，不解決什麼？</summary>

它固定解析版本使 build 可重現；不保證版本無漏洞、license 合適、來源可信或長期可維護。

</details>

<details class="qa"><summary>Q2. 為何 transitive dependency 也屬你的風險？</summary>

它會進入 build/runtime，漏洞或 compromise 同樣影響 artifact，即使 source code 沒直接 import。

</details>

<details class="qa"><summary>Q3. 定期小步更新有何優點？</summary>

差異較小、失敗容易定位、compatibility distance 不會累積；但仍需要 automation 和 tests 控制頻率。

</details>

<details class="qa"><summary>Q4. Wrapper seam 何時有價值？</summary>

外部 API 可能更換且你的需求較窄時，可隔離 contract；若只是完整轉發所有功能，可能只增加無用層。

</details>

<details class="qa"><summary>Q5. AI hallucinated package 為何危險？</summary>

攻擊者可註冊模型常捏造的名稱，誘使 agent 安裝惡意 code；必須以可信 registry 和 policy 驗證。

</details>

<details class="qa"><summary>Q6. Service dependency 還要評估哪些 library 沒有的風險？</summary>

Network latency、availability、quota、data governance、vendor change、regional failure 和 fallback。

</details>

<details class="qa"><summary>Q7. 何時應移除 dependency？</summary>

功能未使用、維護/安全成本超過價值、有標準替代、版本無法更新或退出風險不可接受時。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Dependency Management](https://abseil.io/resources/swe-book/html/ch21.html)
- [Software Engineering at Google — Build Systems and Build Philosophy](https://abseil.io/resources/swe-book/html/ch18.html)
- [OWASP — Top 10 for LLM Applications 2025](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)

---

# 第 21 章　Code Search、Static Analysis 與 Large-Scale Changes

<p class="chapter-question">如何安全修改數千個 call sites，而不是靠人工搜尋取代、巨大 PR 與祈禱？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 3 · 讓變更可以長期維持</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

把大型遷移拆成 inventory、兼容邊界、機械轉換、分批驗證與 cleanup。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node active"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-20-dependency-management-與-supply-chain"><span>上一站</span><strong>20. Dependency Management 與 Supply Chain</strong></a><div class="position-card current"><span>你在這裡</span><strong>21. Code Search、Static Analysis 與 Large-Scale Changes</strong></div><a class="position-card" href="#chapter-22-testing-blueprint-size-scope-與風險組合"><span>下一站</span><strong>22. Testing Blueprint：Size、Scope 與風險組合</strong></a></div>

本章位於 **Part 3：讓變更可以長期維持**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Static analysis</h3><div><span>白話定義</span><p>不實際執行完整程式，就分析程式結構、型別、資料流或規則。</p></div><div class="example"><span>具體例子</span><p>Type checker 在 CI 發現函式可能回傳 <code>None</code> 卻被當整數使用。</p></div><div class="relevance"><span>本章位置</span><p>它為人與 agent 提供快速、確定性、可自動化的 feedback。</p></div></section><section class="term-card"><h3>Codemod</h3><div><span>白話定義</span><p>依語法結構批次修改程式碼的自動轉換。</p></div><div class="example"><span>具體例子</span><p>將所有 <code>old_api(x)</code> 轉為 <code>new_api(value=x)</code>，並保留格式與註解。</p></div><div class="relevance"><span>本章位置</span><p>大型遷移可由 AI 找策略，再由 AST codemod 可靠執行。</p></div></section><section class="term-card"><h3>Scale（規模）</h3><div><span>白話定義</span><p>程式碼量、資料量、請求量、團隊數或系統存活時間增加後出現的新約束。</p></div><div class="example"><span>具體例子</span><p>十人可口頭協調；一千人需要可搜尋文件、標準化 review 與自動 policy。</p></div><div class="relevance"><span>本章位置</span><p>Scale 不是單純把數字放大，常會改變最適合的架構與流程。</p></div></section><section class="term-card"><h3>Backward compatibility</h3><div><span>白話定義</span><p>新版本仍能服務舊呼叫者、舊資料或舊協定的能力。</p></div><div class="example"><span>具體例子</span><p>新增 optional JSON field 通常相容；把字串改為物件可能使舊 client 崩潰。</p></div><div class="relevance"><span>本章位置</span><p>大型系統無法原子更新所有使用者，因而需要 migration window。</p></div></section></div>

## 為什麼需要這一章？

大型 codebase 的變更成本常不在新 API，而在找到所有使用方式、理解例外、協調 owners 和證明修改完整。文字搜尋容易漏 alias、跨語言和 generated code；人工修改又不一致。Large-scale change 需要把 semantic decision 與 mechanical execution 分離。

### 真實 Use Case

公司要把 `send(user, text)` 改為 `send(Message(...))`。有三千個 call sites、不同語言、測試 fixtures 和反射呼叫。直接建立巨大 PR 無人能 review；逐隊手動改則可能拖一年，兩套 API 永久共存。

<div class="context-grid">
<section><span>問題壓力</span><p>大型 codebase 的變更成本常不在新 API，而在找到所有使用方式、理解例外、協調 owners 和證明修改完整。文字搜尋容易漏 alias、跨語言和 generated code；人工修改又不一致。Large-scale change 需要把 semantic decision 與 mechanical execution 分離。</p></section>
<section><span>交付能力</span><p>把大型遷移拆成 inventory、兼容邊界、機械轉換、分批驗證與 cleanup。</p></section>
<section><span>真實場景</span><p>公司要把 <code>send(user, text)</code> 改為 <code>send(Message(...))</code>。有三千個 call sites、不同語言、測試 fixtures 和反射呼叫。直接建立巨大 PR 無人能 review；逐隊手動改則可能拖一年，兩套 API 永久共存。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>define old/new contract
        ↓
code search + index + runtime inventory
        ↓
introduce compatible new API / adapter
        ↓
AST/type-aware codemod + dry run
        ↓
sample review + semantic tests
        ↓
small batches by owner / dependency order
        ↓
block new old-API usage
        ↓
zero-use evidence → remove adapter</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Code search 建立 inventory，但搜尋方式需符合語言。Symbol index 能理解 definition/reference，AST 能辨認 call shape，type information 能區分同名方法；文字搜尋仍適合配置、文件和動態字串。多種 evidence 交叉才能接近完整。

Static analysis 找出 properties 或違規；codemod 執行結構化轉換。最安全流程先建立新 API 和 adapter，使每批修改不破壞 main；對小樣本手動驗證 codemod；產生 deterministic diff；依 owner 或 dependency order 分批提交。新 lint 禁止新增舊用法，migration 才會收斂。

大型修改的 review 重點不是逐行檢查一萬個相同 diff，而是 review transformation specification、代表性 samples、tests 和 exceptions。機械與手工修正分開；每批可回退。最後以 search、build、tests 和 runtime telemetry 證明舊路徑歸零。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>定義 old/new semantics、compatibility 和完成條件，先建立新 API/adapter。</p></div><div class="flow-card"><span>2</span><p>以 symbol、AST、type、text 和 runtime 多種方式建立 call-site inventory。</p></div><div class="flow-card"><span>3</span><p>寫 deterministic codemod，對代表性 patterns 與 negative cases 測試。</p></div><div class="flow-card"><span>4</span><p>依 ownership/dependency 分批執行，機械 diff 與 semantic exceptions 分開 review。</p></div><div class="flow-card"><span>5</span><p>禁止新舊用法、量 migration progress，歸零後移除 adapter 和規則。</p></div></div>

## Coding／實務例子

AST codemod 把 `send(user, text)` 改為 keyword call。範例只處理簡單 shape；真實工具要保留 formatting/comments 並拒絕未知語意。

```python
import ast

class SendMigration(ast.NodeTransformer):
    def visit_Call(self, node: ast.Call):
        self.generic_visit(node)
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "send"
            and len(node.args) == 2
            and not node.keywords
        ):
            return ast.Call(
                func=ast.Name(id="send_message", ctx=ast.Load()),
                args=[],
                keywords=[
                    ast.keyword(arg="user", value=node.args[0]),
                    ast.keyword(arg="text", value=node.args[1]),
                ],
            )
        return node

tree = SendMigration().visit(ast.parse('send(user, "hi")'))
print(ast.unparse(ast.fix_missing_locations(tree)))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Transformer 只修改精確 shape，遇到 keywords、alias 或不同參數數量則保守略過。</p></div><div class="flow-card"><span>2</span><p><code>generic_visit</code> 先走訪巢狀 expressions，避免漏掉 deeper calls。</p></div><div class="flow-card"><span>3</span><p>Output 應通過 formatter、type checker 和 behavior tests。</p></div><div class="flow-card"><span>4</span><p>未轉換 cases 要輸出報告，由人分類新 pattern 或合法 exception。</p></div></div>

## Trade-offs 與 Failure Modes

- Regex replacement 可能修改註解、字串或同名不同函式。
- 一個跨全 repository 巨大 PR 幾乎無法讓 owners 建立局部責任。
- Codemod 過度寬鬆會產生語意錯誤，過度嚴格則留下未量測長尾。
- Migration 沒有禁止新增舊用法，完成率可能一邊修一邊倒退。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 擅長發現使用 patterns、草擬 transformation、解釋 exceptions 和生成 owner-specific PR；但機率性模型不適合直接對數千檔案做不可重現修改。最佳組合是 AI 做 semantic exploration，AST/type-aware tool 做 deterministic execution，CI 和 telemetry 做 proof。AI 處理 codemod 未涵蓋的少數 exceptions，再由 owner review。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 聚類 call-site shapes，幫助設計 codemod pattern 與 negative cases。</li><li>用 agent 為每個 owner 產生小型 migration PR 和 impact summary。</li><li>請 AI 解釋 codemod skipped cases，但要求附 AST/source evidence。</li><li>在 migration dashboard 用 AI 摘要 progress、blockers 和 recurring exceptions。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>大量執行必須由 deterministic、versioned codemod 完成，保證可重跑。</li><li>Agent 修改範圍依 owner/目录限制，禁止一次跨全 repository 自動 merge。</li><li>每批通過 type/build/tests，保留可逆 commit 和 migration progress。</li><li>未知 dynamic consumers 需 runtime telemetry；AI/source search 不能取代。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Large-scale change 是大型 codebase 保持一致的重要能力。若只能永久兼容，系統會被每代 API 疊加拖垮。專家把 change 看成 pipeline 和產品：提供工具、進度、支援、exceptions、enforcement 和 cleanup。AI 讓語意分類更便宜，但確定性與 owner coordination 仍是成功核心。

</aside>

## 動手驗證

1. 執行 codemod，加入 keyword、alias、method call 三種 cases，決定轉換或拒絕。
2. 為一次 API migration 寫 inventory matrix：static、runtime、owners、languages。
3. 將一個 1,000 檔 migration 拆成 dependency-safe batches 和 completion metrics。
4. 讓 AI 聚類二十個 skipped cases，再人工定義新的 deterministic rule。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. 大型修改為何不能只靠文字搜尋？</summary>

文字不知道 symbol、type 和語法 context，會漏 alias/dynamic 使用，也會誤改同名字串與註解；需多種 search evidence。

</details>

<details class="qa"><summary>Q2. 為何先建立 compatibility adapter？</summary>

讓 old/new consumers 共存，每批 migration 都能保持 main 可運作，降低 big-bang 協調和 rollback 風險。

</details>

<details class="qa"><summary>Q3. Codemod review 應看什麼？</summary>

Transformation specification、適用/拒絕 patterns、代表性 samples、semantic tests、determinism 和 exception report，而非逐行相同改動。

</details>

<details class="qa"><summary>Q4. 如何防止 migration 永不完成？</summary>

禁止新使用、明確 owners/deadline、progress telemetry、支援與最終 enforcement，完成後移除 adapter。

</details>

<details class="qa"><summary>Q5. AI 與 AST codemod 如何分工？</summary>

AI 探索與分類語意、處理少數例外；AST/type tool 對大量標準 cases 做可重現確定性轉換。

</details>

<details class="qa"><summary>Q6. 什麼證據能宣稱舊 API 已清除？</summary>

Symbol/text search、build/type checks、tests、runtime telemetry 和外部 owner confirmation 組合，並涵蓋合理觀察窗口。

</details>

<details class="qa"><summary>Q7. Large-scale change 能力的戰略價值？</summary>

讓組織能升級基礎 API、修整架構與移除歷史成本，而不是因 consumer 太多就永久凍結設計。

</details>

## 本章官方來源與延伸閱讀

- [Software Engineering at Google — Code Search](https://abseil.io/resources/swe-book/html/ch17.html)
- [Software Engineering at Google — Static Analysis](https://abseil.io/resources/swe-book/html/ch20.html)
- [Software Engineering at Google — Large-Scale Changes](https://abseil.io/resources/swe-book/html/ch22.html)
- [OpenAI — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices/)

---
