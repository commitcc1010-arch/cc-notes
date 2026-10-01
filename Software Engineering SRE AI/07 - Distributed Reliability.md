---
title: "Distributed Systems Reliability"
part: 6
as_of: 2026-09-30
---

# Part 6　Distributed Systems Reliability

流量、等待、失敗與資料跨越多台機器後，局部合理行為可能組合成全域災難。本 Part 專門建立故障模型。

# 第 37 章　Load Balancing：從入口到 Backend 選擇

<p class="chapter-question">平均分配 request 為什麼不一定公平？如何同時考慮健康、容量、locality、長連線和失敗？</p>

<div class="chapter-meta"><span>難度：中階</span><span>Part 6 · Distributed Systems Reliability</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

拆解 frontend 與 datacenter load balancing，理解 policy、health、feedback 和 failover 的完整迴路。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node active"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-36-capacity-planning-performance-與-provisioning"><span>上一站</span><strong>36. Capacity Planning、Performance 與 Provisioning</strong></a><div class="position-card current"><span>你在這裡</span><strong>37. Load Balancing：從入口到 Backend 選擇</strong></div><a class="position-card" href="#chapter-38-queue-backpressure-overload-與-load-shedding"><span>下一站</span><strong>38. Queue、Backpressure、Overload 與 Load Shedding</strong></a></div>

本章位於 **Part 6：Distributed Systems Reliability**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Load balancing</h3><div><span>白話定義</span><p>依健康、容量和策略把工作分配到多個處理者。</p></div><div class="example"><span>具體例子</span><p>Least-loaded 將新 request 送給目前並發較少的 backend。</p></div><div class="relevance"><span>本章位置</span><p>平均分配不等於公平；慢 request、cache locality 和異質容量都會影響結果。</p></div></section><section class="term-card"><h3>Capacity</h3><div><span>白話定義</span><p>系統在指定品質下能承受的工作量與資源上限。</p></div><div class="example"><span>具體例子</span><p>服務在 p99 低於 300ms 時，每台最多穩定處理 800 RPS。</p></div><div class="relevance"><span>本章位置</span><p>Capacity planning 必須考慮成長、尖峰、故障冗餘和補資源所需 lead time。</p></div></section><section class="term-card"><h3>Service（服務）</h3><div><span>白話定義</span><p>長時間運行、透過網路或訊息介面替其他人或系統提供能力的軟體。</p></div><div class="example"><span>具體例子</span><p>付款 API 接收 request，驗證、寫入資料庫，再回傳成功或失敗。</p></div><div class="relevance"><span>本章位置</span><p>SRE 的可靠性目標通常以服務向使用者提供的行為為單位。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section></div>

## 為什麼需要這一章？

多個 replicas 能提升 capacity 與 availability，但需要決定每個 request 送到哪裡。Round robin 在每個工作成本相同時簡單有效；若有慢 request、異質機器、cache locality 或長連線，表面平均 request 數可能形成嚴重不平均。Balancer 還要避免把流量送給已失效或尚未 warmed 的 backend。

### 真實 Use Case

三台 backend 中一台處理大報表，另外兩台處理小查詢。Round robin 各收到相同 request 數，但第一台 CPU/queue 爆滿。Least-loaded 或 cost-aware policy 能使用 active work，而不只計數。

<div class="context-grid">
<section><span>問題壓力</span><p>多個 replicas 能提升 capacity 與 availability，但需要決定每個 request 送到哪裡。Round robin 在每個工作成本相同時簡單有效；若有慢 request、異質機器、cache locality 或長連線，表面平均 request 數可能形成嚴重不平均。Balancer 還要避免把流量送給已失效或尚未 warmed 的 backend。</p></section>
<section><span>交付能力</span><p>拆解 frontend 與 datacenter load balancing，理解 policy、health、feedback 和 failover 的完整迴路。</p></section>
<section><span>真實場景</span><p>三台 backend 中一台處理大報表，另外兩台處理小查詢。Round robin 各收到相同 request 數，但第一台 CPU/queue 爆滿。Least-loaded 或 cost-aware policy 能使用 active work，而不只計數。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>Client / edge
   ↓ DNS / anycast / global routing
Frontend load balancer
   ↓ region / service / policy
Datacenter balancer
   ↓
candidate backends
  ├─ discovery / membership
  ├─ health / readiness
  ├─ capacity / weight
  ├─ locality / affinity
  └─ active load / outlier
   ↓
chosen backend → result/latency feedback → update health/load</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Load balancing 先決定候選集合，再使用 policy 排序。Membership 來自 service discovery；health 應區分 alive、ready 和 overloaded；weight 表示異質 capacity；locality 降低延遲與跨區成本；affinity 改善 cache，但可能造成 hot key。Policy 需要知道自己優化哪個目標。

Frontend balancing 面對 client、TLS、region 和 global failover；datacenter balancing 在內部選 backend，可取得更細 load signal。Per-request、per-connection 和 per-session 分配不同：WebSocket/stream 長時間占住 backend，connection count 比 request round robin 更重要。

Health feedback 有延遲且可能不完整。若每個 client 同時 eject 同一 backend，剩餘節點可能瞬間過載；需要 outlier detection、slow start、connection draining 和 capacity-aware failover。Retry 也要計入負載，不能讓 balancer 把同一 request 在集群內反覆放大。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>建立 service discovery 與 readiness，先排除不可服務 candidates。</p></div><div class="flow-card"><span>2</span><p>依工作成本選 round-robin、weighted、least-loaded、hash 或 locality policy。</p></div><div class="flow-card"><span>3</span><p>對新/恢復 backend slow start，移除時 connection draining。</p></div><div class="flow-card"><span>4</span><p>使用 latency/error/load feedback 做 outlier detection，但限制 eject 比例。</p></div><div class="flow-card"><span>5</span><p>在 zone/region failover 前確認剩餘 capacity，將 retries 納入 demand。</p></div></div>

## Coding／實務例子

範例用 normalized active load 選擇 backend，讓容量較大的節點可承擔更多並發。

```python
from dataclasses import dataclass

@dataclass
class Backend:
    name: str
    active: int
    capacity: int
    healthy: bool = True

def choose(backends: list[Backend]) -> Backend:
    candidates = [b for b in backends if b.healthy and b.capacity > 0]
    if not candidates:
        raise RuntimeError("no healthy backend")
    return min(candidates, key=lambda b: b.active / b.capacity)

pool = [
    Backend("a", active=8, capacity=10),
    Backend("b", active=12, capacity=30),
]
print(choose(pool).name)
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>比較 <code>active/capacity</code>，b 雖 active 較多但相對更空閒。</p></div><div class="flow-card"><span>2</span><p>Health 與 capacity 都是候選 gate；沒有 candidate 時應 fail fast 或 fallback。</p></div><div class="flow-card"><span>3</span><p>真實實作要處理 concurrent updates、EWMA latency、slow start 和 tie breaking。</p></div><div class="flow-card"><span>4</span><p>Selection 之後要原子增加 active，完成/取消時減少，避免 load signal 漂移。</p></div></div>

## Trade-offs 與 Failure Modes

- 只做 active health check，backend 雖能回 ping 卻無法處理真 request。
- Failover 未預留 capacity，把區域故障轉成全域過載。
- Sticky hash 遇到 hot tenant，使單一 backend 持續飽和。
- Outlier ejection 太積極，短暫抖動讓大量健康 capacity 同時被移除。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI 系統的 load balancing 還包含 model routing：依任務風險、複雜度、latency、成本和資料政策選模型或 provider。語意 router 可由模型協助，但 quota、allowlist、region、fallback 和最大成本必須 deterministic。Routing policy 需用代表性 eval 驗證，避免把某語言、tenant 或困難案例系統性送到較差模型。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 分析 request features，提出 model-tier 或 tool routing 候選。</li><li>使用 eval 比較 quality/latency/cost frontier，建立 routing policy。</li><li>以 agent 摘要 backend/model health、quota 和 recent regressions。</li><li>讓 AI 分析 hot cohorts 與 cache locality，提出 shard/balancer 調整。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>模型/provider 必須在資料區域、合規、allowlist 和 tenant policy 內選擇。</li><li>每 request 有成本/latency budget，超出時使用安全 fallback 或拒絕。</li><li>Router 更新走 version、shadow、canary 和 cohort fairness evaluation。</li><li>LLM router 不直接控制全域 membership/ejection，保留 deterministic bounds。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Balancer 是動態控制系統，不是單一演算法題。專家會問 signal 有多舊、失效時剩餘 capacity、長連線如何 draining、retry 如何計費。AI model routing 同樣要防止局部品質最佳化犧牲成本、公平或資料治理；簡單 static route 常是更可靠 baseline。

</aside>

## 動手驗證

1. 執行選擇器，加入第三台異質 backend、unhealthy 和零 capacity cases。
2. 為 HTTP request、WebSocket 和 batch job 分別選 balancing signal。
3. 設計 zone failover capacity 計算與最大 eject 比例。
4. 建立模型 routing matrix：quality、latency、cost、data policy、fallback。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Round robin 何時足夠？</summary>

Backends 同質、request 成本近似、連線短且 health 穩定時，簡單 policy 可提供低成本與可預測性。

</details>

<details class="qa"><summary>Q2. Health 和 readiness 有何差別？</summary>

Alive 表示 process 回應；ready 表示目前具備依賴、warm state 和 capacity 能服務真流量。

</details>

<details class="qa"><summary>Q3. 為何 failover 可能造成第二次事故？</summary>

剩餘區域未預留 capacity，新增流量使 queue、latency、retry 上升，形成 cascading failure。

</details>

<details class="qa"><summary>Q4. Sticky routing 的收益與風險？</summary>

提升 cache/session locality，但 hot key、節點移除和重分配可能不均；需 virtual nodes/limits。

</details>

<details class="qa"><summary>Q5. Least-loaded signal 為何可能過時？</summary>

分散式觀測與更新有延遲；大量 clients 看到同一舊值可能同時選同一 backend，需隨機化與本地 accounting。

</details>

<details class="qa"><summary>Q6. AI model router 需要哪些 guardrails？</summary>

資料/模型 allowlist、quality eval、cost/latency budget、fallback、cohort monitoring、versioned rollout 和 deterministic quota。

</details>

<details class="qa"><summary>Q7. Balancer 最重要的全域 invariant？</summary>

任何 routing/failover 決策都不能讓可用工作量長期超過剩餘安全 capacity，且失敗要可快速停止。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Load Balancing](https://sre.google/sre-book/load-balancing-frontend/)
- [Site Reliability Engineering — Handling Overload](https://sre.google/sre-book/handling-overload/)
- [Google Cloud — Agent observability](https://docs.cloud.google.com/stackdriver/docs/observability/agent-observability)
- [OpenAI — Agent Evals](https://developers.openai.com/api/docs/guides/agent-evals)

---

# 第 38 章　Queue、Backpressure、Overload 與 Load Shedding

<p class="chapter-question">系統不能處理更多工作時，為什麼早點拒絕通常比全部排隊更可靠？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 6 · Distributed Systems Reliability</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

建立 bounded queue、admission control、priority、deadline 和 graceful degradation，防止等待無限增長。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node active"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-37-load-balancing-從入口到-backend-選擇"><span>上一站</span><strong>37. Load Balancing：從入口到 Backend 選擇</strong></a><div class="position-card current"><span>你在這裡</span><strong>38. Queue、Backpressure、Overload 與 Load Shedding</strong></div><a class="position-card" href="#chapter-39-cascading-failure-deadline-retry-backoff-與-circuit-breaker"><span>下一站</span><strong>39. Cascading Failure：Deadline、Retry、Backoff 與 Circuit Breaker</strong></a></div>

本章位於 **Part 6：Distributed Systems Reliability**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Backpressure</h3><div><span>白話定義</span><p>下游無法再安全接收工作時，向上游傳回減速或拒絕信號。</p></div><div class="example"><span>具體例子</span><p>Queue 滿時 API 回 429，而不是無限接受並耗盡記憶體。</p></div><div class="relevance"><span>本章位置</span><p>沒有 backpressure，局部過載會透過等待與 retry 擴散。</p></div></section><section class="term-card"><h3>Load shedding</h3><div><span>白話定義</span><p>過載時主動拒絕低優先或超過容量的工作，以保護仍可完成的請求。</p></div><div class="example"><span>具體例子</span><p>先拒絕報表刷新，保留付款流量。</p></div><div class="relevance"><span>本章位置</span><p>拒絕必須早、便宜且可觀測；在昂貴工作做完後才拒絕沒有保護效果。</p></div></section><section class="term-card"><h3>Capacity</h3><div><span>白話定義</span><p>系統在指定品質下能承受的工作量與資源上限。</p></div><div class="example"><span>具體例子</span><p>服務在 p99 低於 300ms 時，每台最多穩定處理 800 RPS。</p></div><div class="relevance"><span>本章位置</span><p>Capacity planning 必須考慮成長、尖峰、故障冗餘和補資源所需 lead time。</p></div></section><section class="term-card"><h3>Constraint（限制條件）</h3><div><span>白話定義</span><p>解法必須遵守的硬邊界，例如延遲、相容性、預算、法規或權限。</p></div><div class="example"><span>具體例子</span><p>登入 API p99 必須低於 300ms，而且舊手機版本仍能使用。</p></div><div class="relevance"><span>本章位置</span><p>工程取捨必須先知道 constraint；AI agent 也需要把它寫進完成條件。</p></div></section></div>

## 為什麼需要這一章？

當 arrival rate 長期高於 service rate，queue 必然增長。無界 queue 看似不丟 request，實際只是把失敗延後：memory 上升、deadline 過期、使用者重試、舊工作阻塞新工作，最後全部超時。可靠系統要把 capacity limit 顯式化並向上游傳遞。

### 真實 Use Case

服務每秒能處理 1,000 request，流量持續 1,500。若全部排隊，十秒後已有 5,000 等待，p99 持續上升；若 bounded queue 滿時立即 429 並提供 retry-after，至少已接受工作能在 deadline 內完成。

<div class="context-grid">
<section><span>問題壓力</span><p>當 arrival rate 長期高於 service rate，queue 必然增長。無界 queue 看似不丟 request，實際只是把失敗延後：memory 上升、deadline 過期、使用者重試、舊工作阻塞新工作，最後全部超時。可靠系統要把 capacity limit 顯式化並向上游傳遞。</p></section>
<section><span>交付能力</span><p>建立 bounded queue、admission control、priority、deadline 和 graceful degradation，防止等待無限增長。</p></section>
<section><span>真實場景</span><p>服務每秒能處理 1,000 request，流量持續 1,500。若全部排隊，十秒後已有 5,000 等待，p99 持續上升；若 bounded queue 滿時立即 429 並提供 retry-after，至少已接受工作能在 deadline 內完成。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>arrival λ → admission control
               ├─ within budget → bounded queue → workers μ
               ├─ low priority → shed / degrade
               ├─ expired deadline → reject early
               └─ tenant quota exceeded → throttle
                         ↓
backpressure signal: 429 / retry-after / flow control
                         ↓
upstream slows, drops, or chooses fallback

λ &gt; μ 持續存在時，任何 queue 終將滿</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Queue 的目的吸收短 burst 與解耦速度，不是創造 capacity。用 Little’s Law 可理解平均在系統中的工作量約等於 arrival rate × 平均時間；等待增加會直接推高 in-flight 和資源。Queue 應有 size、age/deadline、priority 和 ownership。

Admission control 在昂貴工作前判斷是否能完成。可使用 concurrency limit、token bucket、tenant quota、load signal 和 deadline。Load shedding 要便宜且明確：優先拒絕低價值、過期或可重試工作，保護 critical path。Graceful degradation 可停用推薦、縮小 response 或使用 stale cache。

Backpressure 必須端到端。下游回 429/UNAVAILABLE 時，上游要尊重 retry-after、限制 retry 和傳遞 deadline；若每層都有獨立 queue，壓力被隱藏並疊加。監控要看 queue depth、oldest age、admission/rejection、completion within deadline 和 fairness。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>量 arrival/service rate、work cost、deadline 和 burst，設定 bounded queue。</p></div><div class="flow-card"><span>2</span><p>在昂貴步驟前做 admission，過期或超 quota 工作早期拒絕。</p></div><div class="flow-card"><span>3</span><p>按 user/business priority 與 tenant fairness shed，提供清楚 retry/fallback。</p></div><div class="flow-card"><span>4</span><p>將 backpressure、deadline 和 retry budget向上游傳遞，避免多層隱藏 queue。</p></div><div class="flow-card"><span>5</span><p>監控 queue age、completion within deadline、shed rate 和剩餘 capacity。</p></div></div>

## Coding／實務例子

範例是有優先級與期限的 admission decision。即使 queue 有空，已過期工作也不應進入。

```python
from dataclasses import dataclass
from time import monotonic

@dataclass(frozen=True)
class Request:
    deadline: float
    priority: int       # larger is more important

def admit(req: Request, queue_size: int, max_queue: int,
          min_priority_when_busy: int = 5) -> tuple[bool, str]:
    if monotonic() >= req.deadline:
        return False, "expired"
    if queue_size >= max_queue:
        return False, "queue-full"
    if queue_size >= max_queue * 0.8 and req.priority < min_priority_when_busy:
        return False, "shed-low-priority"
    return True, "accepted"
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Deadline 先檢查，避免對使用者已放棄的工作浪費 capacity。</p></div><div class="flow-card"><span>2</span><p>Queue hard bound 防止 memory 和等待無限制增長。</p></div><div class="flow-card"><span>3</span><p>接近飽和先 shed 低 priority，保護 critical traffic。</p></div><div class="flow-card"><span>4</span><p>Priority 必須有公平與反濫用 policy，不能讓每個 caller 都標最高。</p></div></div>

## Trade-offs 與 Failure Modes

- Queue 太大讓 dashboard 看似少拒絕，但 latency 和 wasted work 持續增加。
- 每層 retry + queue 疊加，使最終 deadline 失去控制。
- 只按先來先服務，昂貴低價值 job 可阻塞短 critical request。
- Load shedding 在完成昂貴 auth/database 後才執行，已無保護作用。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI requests 的工作量差異可能跨數個數量級：context、output tokens、tool calls 和 agent steps 都會延長占用。Admission 要先估 budget、限制 max context/steps/concurrency，並提供較小模型、摘要 context 或 non-agent fallback。不能靠模型自己決定是否超出資源，hard quotas 必須在 harness 外層。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 預估任務類型與建議 model tier，但由 policy 套用 hard budgets。</li><li>使用 agent 分析 queue cohorts、long-tail steps 和 tenant fairness。</li><li>在過載時讓 AI feature 降級為搜尋、模板或短回答，而非全失敗。</li><li>讓 agent 根據明確 runbook提出 shed/limit 變更，先 dry-run。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Context、output、steps、tools、concurrency 和 spend 都有硬上限。</li><li>Agent 無權把自己的 priority 提高或繞過 tenant quota。</li><li>Tool calls 傳遞 deadline/idempotency，超時後停止後續規劃。</li><li>Overload mode 和降級由 deterministic signal 啟動，保留 kill switch。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

過載不是例外，而是容量有限系統必須定義的正常模式。專家會在設計時回答「我們先犧牲什麼、如何告知 caller、保護哪個 invariant」。AI 使單一 request 成本更不可預測，因此 admission 與 budget 比無限 autoscaling 更重要。

</aside>

## 動手驗證

1. 用 λ=1500、μ=1000 計算每秒 queue 成長，估十秒延遲。
2. 執行 admission，測 expired、80% threshold、full 和 high-priority cases。
3. 畫一條跨三服務的 deadline/backpressure/retry 傳遞。
4. 為 AI endpoint 定義 context/token/steps/concurrency/spend 與降級表。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Queue 能否解決持續 λ&gt;μ？</summary>

不能。它只吸收短 burst；長期超載必須增加 service rate、降低 arrival、shed 或降級，否則任何有限 queue 都會滿。

</details>

<details class="qa"><summary>Q2. 為何 queue age 比 depth 有時更重要？</summary>

不同工作成本與容量下相同 depth 的等待不同；oldest age 直接反映是否接近 deadline。

</details>

<details class="qa"><summary>Q3. Load shedding 為何要早？</summary>

在昂貴工作前拒絕才能保留 CPU/IO/connection；完成大半後才拒絕已支付成本。

</details>

<details class="qa"><summary>Q4. Backpressure 如何跨服務傳遞？</summary>

用明確 status/retry-after、deadline、bounded retries 和上游 admission，避免每層獨立無限排隊。

</details>

<details class="qa"><summary>Q5. Priority queue 最大風險？</summary>

低優先工作飢餓、caller 濫標高優先和公平問題；需 quota、aging 和治理。

</details>

<details class="qa"><summary>Q6. AI request 為何更需要 admission？</summary>

工作量由 tokens、tools、steps 決定且長尾大，單一任務可占用大量成本與 concurrency。

</details>

<details class="qa"><summary>Q7. Overload design 最重要的產品問題？</summary>

在 capacity 不足時保護哪些 user journeys、犧牲哪些功能、如何提供可理解 retry/fallback。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Handling Overload](https://sre.google/sre-book/handling-overload/)
- [Site Reliability Engineering — Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/)
- [Software Engineering at Google — Compute as a Service](https://abseil.io/resources/swe-book/html/ch25.html)
- [Google Cloud — Agent observability](https://docs.cloud.google.com/stackdriver/docs/observability/agent-observability)

---

# 第 39 章　Cascading Failure：Deadline、Retry、Backoff 與 Circuit Breaker

<p class="chapter-question">單一 dependency 變慢，為什麼可能讓整個系統在幾分鐘內一起失敗？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 6 · Distributed Systems Reliability</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

理解等待、資源占用與 retry amplification，建立端到端 deadline、retry budget、jitter 和隔離。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node active"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-38-queue-backpressure-overload-與-load-shedding"><span>上一站</span><strong>38. Queue、Backpressure、Overload 與 Load Shedding</strong></a><div class="position-card current"><span>你在這裡</span><strong>39. Cascading Failure：Deadline、Retry、Backoff 與 Circuit Breaker</strong></div><a class="position-card" href="#chapter-40-distributed-consensus-與-critical-state"><span>下一站</span><strong>40. Distributed Consensus 與 Critical State</strong></a></div>

本章位於 **Part 6：Distributed Systems Reliability**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Deadline 與 timeout</h3><div><span>白話定義</span><p>Deadline 是整個操作最晚完成時間；timeout 常是單一步驟最多等待多久。</p></div><div class="example"><span>具體例子</span><p>使用者剩 800ms，下一層不能各自重設 2 秒 timeout。</p></div><div class="relevance"><span>本章位置</span><p>跨服務傳遞剩餘 deadline 可避免每層等待疊加。</p></div></section><section class="term-card"><h3>Retry</h3><div><span>白話定義</span><p>操作失敗後再次嘗試，適合暫時性且可安全重做的錯誤。</p></div><div class="example"><span>具體例子</span><p>遇到短暫 connection reset，以 exponential backoff 加 jitter 重試兩次。</p></div><div class="relevance"><span>本章位置</span><p>無上限 retry 會放大負載；非 idempotent 操作可能造成重複副作用。</p></div></section><section class="term-card"><h3>Circuit breaker</h3><div><span>白話定義</span><p>偵測 dependency 持續失敗後暫停呼叫，給下游恢復時間並快速回退。</p></div><div class="example"><span>具體例子</span><p>付款供應商大量 timeout 時，暫停新呼叫並顯示稍後重試。</p></div><div class="relevance"><span>本章位置</span><p>它是保護機制，不是修復根因；threshold 和恢復探測需要仔細設計。</p></div></section><section class="term-card"><h3>Idempotency</h3><div><span>白話定義</span><p>同一操作執行一次或多次，外部結果相同。</p></div><div class="example"><span>具體例子</span><p>以 payment id 作唯一鍵，重送請求不會重複扣款。</p></div><div class="relevance"><span>本章位置</span><p>Cron、queue、retry 和 agent tool call 都需要 idempotency 才能安全恢復。</p></div></section></div>

## 為什麼需要這一章？

Dependency latency 增加時，caller 的 threads/connections/queue 被占住；timeout 後 retry 又產生更多流量，使下游更慢。多層各重試三次，最壞可把一次 user request 放大成數十次 calls。Cascading failure 是合理局部策略組合出的全域災難。

### 真實 Use Case

Database failover 讓 latency 從 50ms 升到 2s。API timeout 3s、上游 timeout 5s，各 retry 3 次；in-flight 暴增、connection pool 耗盡，連不依賴該資料庫的 endpoint 也失敗。若傳遞 deadline、限制 retry 並隔離 pool，blast radius 可被控制。

<div class="context-grid">
<section><span>問題壓力</span><p>Dependency latency 增加時，caller 的 threads/connections/queue 被占住；timeout 後 retry 又產生更多流量，使下游更慢。多層各重試三次，最壞可把一次 user request 放大成數十次 calls。Cascading failure 是合理局部策略組合出的全域災難。</p></section>
<section><span>交付能力</span><p>理解等待、資源占用與 retry amplification，建立端到端 deadline、retry budget、jitter 和隔離。</p></section>
<section><span>真實場景</span><p>Database failover 讓 latency 從 50ms 升到 2s。API timeout 3s、上游 timeout 5s，各 retry 3 次；in-flight 暴增、connection pool 耗盡，連不依賴該資料庫的 endpoint 也失敗。若傳遞 deadline、限制 retry 並隔離 pool，blast radius 可被控制。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>dependency slows/errors
        ↓
in-flight ↑ / pool occupied / queue ↑
        ↓
timeouts → retries at many layers → offered load ↑
        ↓
more latency/errors ───────────────────┐
        └──────────────────────────────┘ positive feedback

break loop:
deadline propagation · bounded retry budget · exponential backoff+jitter
idempotency · circuit breaker · bulkhead · load shedding · fallback</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Deadline 是 user operation 的總時間預算，應向下傳遞剩餘時間；每層重新設定固定 timeout 會讓總等待倍增。Timeout 要涵蓋 connection、read 和 queue，但太短會把正常長尾變成 retry load，太長則占住資源。應依 latency distribution 和 SLO 校準。

Retry 只適用 transient、可安全重做且剩餘 deadline 足夠的錯誤。選單一合理 layer 重試，設定 max attempts/retry budget、exponential backoff 和 jitter。Idempotency key 防止 response 丟失後重試造成重複付款。非 retryable validation/permission 立即回傳。

Circuit breaker 在持續失敗時快速拒絕，bulkhead 隔離 resource pools，fallback/partial response 保護核心 journey，load shedding 降 offered load。Recovery 要 slow start，否則所有 clients 同時 probe 剛恢復 dependency，再次壓垮。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>設定端到端 deadline 並傳遞剩餘 budget，不在每層重新開始計時。</p></div><div class="flow-card"><span>2</span><p>只 retry transient/idempotent 操作，集中 layer、限制 attempts 和總 retry budget。</p></div><div class="flow-card"><span>3</span><p>使用 exponential backoff + jitter，尊重 retry-after 和 cancellation。</p></div><div class="flow-card"><span>4</span><p>以 circuit breaker、bulkhead、fallback、shed 切斷 positive feedback。</p></div><div class="flow-card"><span>5</span><p>恢復時 slow start，監控 in-flight、retry ratio、queue 和 dependency SLO。</p></div></div>

## Coding／實務例子

範例實作有 deadline、bounded attempts 和 jitter 的 retry。函式使用注入 sleep，方便測試。

```python
import random
import time
from collections.abc import Callable

def retry(
    operation: Callable[[], str],
    deadline: float,
    attempts: int = 3,
    base_delay: float = 0.1,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    last_error = None
    for attempt in range(attempts):
        if time.monotonic() >= deadline:
            raise TimeoutError("deadline exhausted") from last_error
        try:
            return operation()
        except ConnectionError as error:
            last_error = error
            if attempt + 1 == attempts:
                break
            delay = base_delay * (2 ** attempt) * random.uniform(0.5, 1.5)
            sleep(min(delay, max(0, deadline - time.monotonic())))
    raise last_error
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>只 catch <code>ConnectionError</code>，validation 等永久錯誤不重試。</p></div><div class="flow-card"><span>2</span><p>每次 action 前檢查共同 deadline，避免重試超過使用者等待。</p></div><div class="flow-card"><span>3</span><p>Exponential backoff 降頻，jitter 避免所有 clients 同步重試。</p></div><div class="flow-card"><span>4</span><p>測試可注入 fake sleep/random/clock；production 還需 cancellation 與 metrics。</p></div></div>

## Trade-offs 與 Failure Modes

- 每層獨立 retry，流量乘法放大。
- Timeout 小於正常 p99，健康 request 被轉成失敗和 retry。
- Circuit breaker 全域共享錯誤狀態，單 tenant 問題影響所有人。
- Fallback 讀 stale/partial data 卻未標示，造成 silent correctness failure。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

Agent loops 本身就是 retrying distributed workflow：模型可能反覆呼叫同一 tool、在失敗後改參數重試，甚至不同 agents 互相觸發。Harness 必須有全域 deadline、max steps、per-tool retry policy、idempotency keys 和 total spend budget；模型不能靠文字自我約束。Tool errors 要分類 transient/permanent/policy。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 根據結構化 error 建議是否 retry、fallback 或升級，但由 policy執行。</li><li>用 agent 關聯 retry ratio、dependency latency 和 recent changes，建立 cascade timeline。</li><li>請 AI 找出多層 client libraries 的重試設定，計算最壞 amplification。</li><li>讓 agent 草擬 circuit/bulkhead/fallback tests，包含恢復 slow start。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Harness 設 max steps、wall time、tokens、tool calls 和總成本硬限制。</li><li>每個 mutating tool 使用 idempotency key，重試前查詢前次結果。</li><li>Policy errors/permission denied 不重試或改寫指令繞過。</li><li>Agent 不能自行提高 timeout/retry budget；production policy 版本化可稽核。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

專家會先畫 amplification graph：一次 user request 最壞產生多少下游 calls、每個等待占用什麼資源。Retry 是以額外負載換取成功率，只有下游有恢復 capacity 才有幫助。AI agent 的「再試一次」同樣有成本；沒有 global budget 的智能 loop 只是更難看見的 retry storm。

</aside>

## 動手驗證

1. 計算三層各 retry 3 次的最壞 calls，改成只一層 retry 比較。
2. 以 fake operation/sleep 測 retry 成功、永久錯誤、deadline 和 attempts。
3. 為一個 dependency 畫 timeout、pool、queue、retry 和 circuit 的互動。
4. 設計 agent tool policy：error classes、retryable、max attempts、idempotency。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Retry 何時有幫助？</summary>

錯誤是短暫、操作可安全重做、下游有恢復可能且剩餘 deadline/capacity 足夠時。

</details>

<details class="qa"><summary>Q2. 為何多層 retry 危險？</summary>

Attempts 相乘，單一 user request 產生大量下游流量，在故障時進一步壓垮 dependency。

</details>

<details class="qa"><summary>Q3. Deadline 與 timeout 差別？</summary>

Deadline 是整體操作最晚時間；timeout 是某一步等待上限。下游應以剩餘 deadline 設 timeout。

</details>

<details class="qa"><summary>Q4. Jitter 解決什麼？</summary>

打散大量 clients 同時 backoff 完成後的同步重試，避免週期性流量尖峰。

</details>

<details class="qa"><summary>Q5. Circuit breaker 是否修復 dependency？</summary>

不會。它快速隔離持續失敗、保護 caller 和給下游恢復時間；根因仍需修復。

</details>

<details class="qa"><summary>Q6. Agent loop 為何是 retry 系統？</summary>

模型觀察失敗後反覆呼叫 tools，會占用時間、資源和 side effects；需要同樣的 deadline、budget、idempotency。

</details>

<details class="qa"><summary>Q7. Fallback 最大 correctness 風險？</summary>

回傳 stale/partial/estimated data 卻讓 caller 誤以為完整正確；需標示 semantics、限制用途並監控。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/)
- [Site Reliability Engineering — Handling Overload](https://sre.google/sre-book/handling-overload/)
- [Google Cloud — How Google SRE is using agentic AI](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)
- [OWASP — Top 10 for LLM Applications 2025](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

---

# 第 40 章　Distributed Consensus 與 Critical State

<p class="chapter-question">多台機器如何在延遲、重試和故障下，仍對 leader、lock 或 configuration 達成一致？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 6 · Distributed Systems Reliability</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

理解 quorum intersection、term、log、leader election 和 fencing，知道何時使用成熟 consensus service。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node active"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-39-cascading-failure-deadline-retry-backoff-與-circuit-breaker"><span>上一站</span><strong>39. Cascading Failure：Deadline、Retry、Backoff 與 Circuit Breaker</strong></a><div class="position-card current"><span>你在這裡</span><strong>40. Distributed Consensus 與 Critical State</strong></div><a class="position-card" href="#chapter-41-distributed-cron-leases-與-idempotent-jobs"><span>下一站</span><strong>41. Distributed Cron、Leases 與 Idempotent Jobs</strong></a></div>

本章位於 **Part 6：Distributed Systems Reliability**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Distributed consensus</h3><div><span>白話定義</span><p>多個節點即使發生延遲或故障，仍對單一值或操作順序達成一致。</p></div><div class="example"><span>具體例子</span><p>多台 controller 同意目前 leader 和 configuration generation。</p></div><div class="relevance"><span>本章位置</span><p>Consensus 解決 critical state 協調；LLM 的多數意見不是 consensus protocol。</p></div></section><section class="term-card"><h3>Quorum</h3><div><span>白話定義</span><p>足以代表整體並與其他合法集合重疊的節點數。</p></div><div class="example"><span>具體例子</span><p>五個 replica 中三個形成 majority，任意兩個 majority 至少重疊一台。</p></div><div class="relevance"><span>本章位置</span><p>重疊讓新決策能遇到知道舊決策的節點。</p></div></section><section class="term-card"><h3>Invariant（不變條件）</h3><div><span>白話定義</span><p>系統任何合法狀態都必須成立的規則。</p></div><div class="example"><span>具體例子</span><p>銀行轉帳前後，所有帳戶餘額總和不應憑空增加。</p></div><div class="relevance"><span>本章位置</span><p>測試、型別和監控常用來保護 invariant；它比描述每一行實作更穩定。</p></div></section><section class="term-card"><h3>Ownership</h3><div><span>白話定義</span><p>對元件品質、決策、值班與改善負最終責任的明確主體。</p></div><div class="example"><span>具體例子</span><p>平台組維護 deployment API；服務組仍對自己設定錯誤造成的事故負責。</p></div><div class="relevance"><span>本章位置</span><p>AI 可以執行工作但不能承擔組織責任，因此 ownership 不可寫成『模型』。</p></div></section></div>

## 為什麼需要這一章？

分散式系統沒有瞬間共同現在：訊息會延遲、節點會暫停、網路會分割。若兩個 controller 同時以為自己是 leader 並修改 critical state，可能重複排程、覆蓋資料或同時操作資源。Consensus 用協定在部分故障下維持單一決策順序，但付出 latency、availability 和複雜度。

### 真實 Use Case

五個 scheduler replicas 要決定某 job 由誰執行。只用「看到 lock file 不存在就建立」在 network partition 可能產生兩個 owners。使用 majority quorum、term 和 fencing token，舊 leader 即使恢復也不能提交過期操作。

<div class="context-grid">
<section><span>問題壓力</span><p>分散式系統沒有瞬間共同現在：訊息會延遲、節點會暫停、網路會分割。若兩個 controller 同時以為自己是 leader 並修改 critical state，可能重複排程、覆蓋資料或同時操作資源。Consensus 用協定在部分故障下維持單一決策順序，但付出 latency、availability 和複雜度。</p></section>
<section><span>交付能力</span><p>理解 quorum intersection、term、log、leader election 和 fencing，知道何時使用成熟 consensus service。</p></section>
<section><span>真實場景</span><p>五個 scheduler replicas 要決定某 job 由誰執行。只用「看到 lock file 不存在就建立」在 network partition 可能產生兩個 owners。使用 majority quorum、term 和 fencing token，舊 leader 即使恢復也不能提交過期操作。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>clients propose values
        ↓
replicas exchange term / log / votes
        ↓
leader elected by quorum
        ↓
entry replicated to quorum
        ↓
commit order becomes durable/visible

5 nodes → majority 3
any two majorities intersect
partition minority cannot commit

fencing token ↑ each leadership term
resource rejects stale token</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Consensus 的核心不是所有節點永遠同時相同，而是對已提交決策的安全性和順序達成一致。Majority quorum 的交集確保新決策至少接觸知道舊決策的節點。Term/epoch 區分領導世代；log 將操作排序；commit 需要 quorum。網路分割時少數側犧牲 availability 保護單一真相。

Leader election 仍需處理舊 leader。Process 暫停、lease 過期後可能醒來並繼續寫，因此 downstream resource 應接受單調增加的 fencing token，拒絕舊 epoch。只靠 wall-clock lease 需要非常小心 clock drift 與 pause。

不要自行發明 consensus。使用成熟、被驗證的 etcd/Consul/ZooKeeper/database primitives，理解其 session、linearizability、failure 和 capacity。Consensus 不適合所有資料：可合併、可重算或 eventual consistency 的 state 可能用更簡單方法。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>先辨認真正需要單一順序/ownership 的 critical state 與 invariant。</p></div><div class="flow-card"><span>2</span><p>選成熟 consensus/transaction service，理解 consistency、failure 和 limits。</p></div><div class="flow-card"><span>3</span><p>使用 quorum、term/epoch、durable log 和 fencing 保護舊 leader。</p></div><div class="flow-card"><span>4</span><p>Client operations 帶 idempotency/request ID，timeout 後查詢結果再重試。</p></div><div class="flow-card"><span>5</span><p>監控 quorum health、leader changes、commit latency、storage 和 clock/pause。</p></div></div>

## Coding／實務例子

小模型展示 majority quorum 為何相交，以及少數 partition 無法取得 commit quorum。

```python
from itertools import combinations

nodes = {"a", "b", "c", "d", "e"}
majorities = [set(group) for group in combinations(nodes, 3)]

def all_intersect(groups: list[set[str]]) -> bool:
    return all(left & right for left, right in combinations(groups, 2))

print(len(majorities), all_intersect(majorities))

def can_commit(available: set[str], cluster_size: int = 5) -> bool:
    return len(available) >= cluster_size // 2 + 1

print(can_commit({"a", "b"}), can_commit({"a", "b", "c"}))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>五個節點的任意三節點 majority 都與另一 majority 至少交集一台。</p></div><div class="flow-card"><span>2</span><p>兩節點 partition 無法 commit，三節點側可保持進展。</p></div><div class="flow-card"><span>3</span><p>交集是 safety 的直覺，完整協定還要處理 log freshness、terms 和 persistence。</p></div><div class="flow-card"><span>4</span><p>增加 replicas 提高故障容忍也增加通信/operational cost，不是免費可靠性。</p></div></div>

## Trade-offs 與 Failure Modes

- 把 health check 選出的節點當 leader，沒有 quorum/fencing。
- Client timeout 後直接重做 non-idempotent command，可能前次已 commit。
- Consensus store 承載高量非 critical data，造成 latency/容量瓶頸。
- 跨大距離 quorum 為了 durability 犧牲 latency，卻沒有對應使用者需求。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

多個 LLM/agents 投票不是 distributed consensus：模型答案沒有 durable log、quorum intersection、term 或 safety proof。AI 可以協助 operator 理解 topology、分析 leader changes 和生成 runbook，但 critical authorization、lock、configuration commit 必須由 deterministic protocol。Agent 呼叫 consensus service 也要用 fencing、idempotency 和最小權限。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 摘要 consensus telemetry、leader churn 和 storage/latency anomalies。</li><li>用 agent 解釋 protocol trace，找出哪個 term/quorum 阻止 commit。</li><li>請 AI 草擬 failure-injection cases：partition、pause、disk full、stale leader。</li><li>讓 agent 透過高層安全 tool 申請 lock/lease，不直接修改 store internals。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>LLM output 不作 election、authorization、quorum 或 fencing token。</li><li>Agent 使用 workload identity，ACL 只允許指定 prefix/operations。</li><li>Mutating request 帶 request ID/fencing，timeout 後先 read-back。</li><li>Consensus config change 需人類 review、staged rollout、backup 和 rollback plan。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

Consensus 是在明確 failure model 下換取 safety 的昂貴基礎設施。專家先問是否真的需要線性一致或唯一 leader，能否重新計算、分區 ownership 或接受 eventual convergence。若需要，就使用成熟協定並把資料量保持最小；不要讓 AI 的『多數答案』混淆演算法保證。

</aside>

## 動手驗證

1. 執行 quorum 範例，改成 3、4、7 節點並分析可容忍故障。
2. 畫出舊 leader pause、lease 過期、新 leader、舊 leader 恢復的 fencing 流程。
3. 列出一個系統的 critical 與 non-critical state，決定哪些需要 consensus。
4. 讓 AI 解釋一段 leader-election log，要求每個結論引用 term/index evidence。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Consensus 解決的核心問題？</summary>

在訊息延遲、節點故障和網路分割下，對 critical value/操作順序維持一致安全決策。

</details>

<details class="qa"><summary>Q2. Majority quorum 為何重要？</summary>

任意兩個 majority 相交，新的決策會遇到至少一個知道舊決策的節點，協定可保護已提交 state。

</details>

<details class="qa"><summary>Q3. Network partition 時為何少數側停止？</summary>

為避免兩邊各自提交衝突決策，少數側犧牲 availability 保護 safety。

</details>

<details class="qa"><summary>Q4. Fencing token 解決什麼？</summary>

舊 leader 暫停後恢復仍可能操作；下游拒絕較小 epoch/token，防止 stale owner 破壞 state。

</details>

<details class="qa"><summary>Q5. 為何 client timeout 不代表 command 未執行？</summary>

Response 可能丟失但 command 已 commit；重試前需 idempotency/request ID 和 result lookup。

</details>

<details class="qa"><summary>Q6. Agent voting 為何不是 consensus？</summary>

缺乏 durable state、failure model、quorum intersection、term、commit 和 safety proof，只是多個機率性意見。

</details>

<details class="qa"><summary>Q7. 何時不該用 consensus？</summary>

State 可重算、衝突可合併、分區獨立或 eventual consistency 足夠時，較簡單設計可能更可靠便宜。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Distributed Consensus](https://sre.google/sre-book/managing-critical-state/)
- [Site Reliability Engineering — Simplicity](https://sre.google/sre-book/simplicity/)
- [Google Cloud — How Google SRE is using agentic AI](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)
- [NIST — Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)

---

# 第 41 章　Distributed Cron、Leases 與 Idempotent Jobs

<p class="chapter-question">排程器故障或重試時，如何避免 job 漏跑、重複跑或兩台同時執行？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 6 · Distributed Systems Reliability</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

選擇 at-least-once 語意，搭配 lease、fencing、idempotency、checkpoint 和 reconciliation。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node active"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-40-distributed-consensus-與-critical-state"><span>上一站</span><strong>40. Distributed Consensus 與 Critical State</strong></a><div class="position-card current"><span>你在這裡</span><strong>41. Distributed Cron、Leases 與 Idempotent Jobs</strong></div><a class="position-card" href="#chapter-42-data-pipelines-provenance-backup-與-integrity"><span>下一站</span><strong>42. Data Pipelines、Provenance、Backup 與 Integrity</strong></a></div>

本章位於 **Part 6：Distributed Systems Reliability**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Idempotency</h3><div><span>白話定義</span><p>同一操作執行一次或多次，外部結果相同。</p></div><div class="example"><span>具體例子</span><p>以 payment id 作唯一鍵，重送請求不會重複扣款。</p></div><div class="relevance"><span>本章位置</span><p>Cron、queue、retry 和 agent tool call 都需要 idempotency 才能安全恢復。</p></div></section><section class="term-card"><h3>Distributed consensus</h3><div><span>白話定義</span><p>多個節點即使發生延遲或故障，仍對單一值或操作順序達成一致。</p></div><div class="example"><span>具體例子</span><p>多台 controller 同意目前 leader 和 configuration generation。</p></div><div class="relevance"><span>本章位置</span><p>Consensus 解決 critical state 協調；LLM 的多數意見不是 consensus protocol。</p></div></section><section class="term-card"><h3>Dependency</h3><div><span>白話定義</span><p>程式運作所依賴的 library、service、tool、資料格式或團隊。</p></div><div class="example"><span>具體例子</span><p>Web service 依賴資料庫 driver 和外部付款 API。</p></div><div class="relevance"><span>本章位置</span><p>Dependency 帶來升級、供應鏈、安全與可用性成本；AI 可能捏造不存在的套件。</p></div></section><section class="term-card"><h3>Feedback loop（回饋迴路）</h3><div><span>白話定義</span><p>採取行動後取得結果，依結果修正下一次行動的閉環。</p></div><div class="example"><span>具體例子</span><p>CI 發現 regression，團隊修正 code 並把測試保留，未來同類錯誤更早被攔住。</p></div><div class="relevance"><span>本章位置</span><p>優秀工程系統會把 review、test、telemetry 和 postmortem 都變成可累積的 feedback。</p></div></section></div>

## 為什麼需要這一章？

單機 cron 假設機器一直在線；分散式排程需面對 scheduler failover、worker crash、訊息重複、時鐘和長任務。Exactly-once execution 很難：系統可能完成 side effect 卻在記錄成功前 crash。實務通常選 at-least-once delivery，再使 job effect idempotent 或可 reconcile。

### 真實 Use Case

每晚寄帳單的 worker 在寄出後、寫入完成狀態前 crash。新 worker 重試可能寄兩次；若以 invoice ID 作外部 idempotency key，provider 能回傳前次結果而非重複寄送。

<div class="context-grid">
<section><span>問題壓力</span><p>單機 cron 假設機器一直在線；分散式排程需面對 scheduler failover、worker crash、訊息重複、時鐘和長任務。Exactly-once execution 很難：系統可能完成 side effect 卻在記錄成功前 crash。實務通常選 at-least-once delivery，再使 job effect idempotent 或可 reconcile。</p></section>
<section><span>交付能力</span><p>選擇 at-least-once 語意，搭配 lease、fencing、idempotency、checkpoint 和 reconciliation。</p></section>
<section><span>真實場景</span><p>每晚寄帳單的 worker 在寄出後、寫入完成狀態前 crash。新 worker 重試可能寄兩次；若以 invoice ID 作外部 idempotency key，provider 能回傳前次結果而非重複寄送。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>schedule definition
      ↓
leader / partition assigns run_id
      ↓
durable queue (at-least-once)
      ↓
worker obtains lease + fencing token
      ↓
check idempotency / checkpoint
      ↓
perform bounded side effects
      ↓
record result / renew or release lease
      ↓
reconciliation finds missing/stuck/duplicate outcomes</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

先定義 job semantics：可以晚多久、可否重複、是否可分片、最大 runtime、依賴和補跑。Scheduler 產生唯一 run ID 並持久化；queue 提供 at-least-once；worker 取得有期限 lease。Lease 失效後新 worker接手，舊 worker 需被 fencing。

Idempotency 可在資料層用 unique key/upsert，在外部 API 傳 idempotency key，或先查 effect ledger。長 job 使用 checkpoints，使 retry 從安全位置繼續。Side effects 排序很重要：transactional outbox 將資料 commit 與待發事件放同 transaction，再由 publisher 重試。

Reconciliation 是最後安全網：比較應有 runs、實際 effects 和 completion records，找 missing、stuck、duplicate。監控不只 job success，要看 schedule delay、age、attempts、lease churn、partial progress 和 business invariant。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>定義 lateness、duplication、runtime、partition、dependency 和 replay contract。</p></div><div class="flow-card"><span>2</span><p>建立 durable run ID、at-least-once queue、lease/heartbeat 和 fencing。</p></div><div class="flow-card"><span>3</span><p>使每個 side effect idempotent，長任務 checkpoint，跨系統使用 outbox/ledger。</p></div><div class="flow-card"><span>4</span><p>Timeout/retry 傳遞 deadline，限制 attempts 和同時執行。</p></div><div class="flow-card"><span>5</span><p>用 reconciliation 對比 schedule、state 和真實 business effects。</p></div></div>

## Coding／實務例子

範例用 run ID ledger 保證同一批 job effect 只第一次執行。真實資料庫需以 unique constraint/transaction 原子化。

```python
class JobLedger:
    def __init__(self):
        self.completed: dict[str, str] = {}

    def run_once(self, run_id: str, operation) -> str:
        if run_id in self.completed:
            return self.completed[run_id]
        result = operation()
        # Production: unique constraint + transaction or external idempotency key.
        self.completed[run_id] = result
        return result

ledger = JobLedger()
send = lambda: "invoice-sent"
print(ledger.run_once("invoice:2026-09-30:customer-7", send))
print(ledger.run_once("invoice:2026-09-30:customer-7", send))
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Deterministic run ID 對應業務 effect，而不是每次 retry 生成新 UUID。</p></div><div class="flow-card"><span>2</span><p>記憶體 ledger 只示範語意，crash 安全需 durable unique constraint。</p></div><div class="flow-card"><span>3</span><p>若 operation 完成、ledger 尚未寫入仍有 gap，需要 external idempotency 或 outbox。</p></div><div class="flow-card"><span>4</span><p>回傳已存 result 讓 retry caller 得到一致答案。</p></div></div>

## Trade-offs 與 Failure Modes

- 宣稱 exactly once 卻沒有處理 side effect 與 completion record 之間的 crash gap。
- Lease 只有時間沒有 fencing，舊 worker 恢復後仍修改 state。
- 每次 retry 生成新 idempotency key，使重複保護失效。
- 只監控 scheduler 成功，實際業務 effect 遺失無人發現。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

Scheduled agents 會讀資料、呼叫多個 tools、產生不可預測步數，風險高於普通 cron。每個 run 需要固定 goal/context version、專用短期 identity、allowlisted tools、dry-run/approval、idempotency 和 spend/action budgets。Agent 不應從未受信文件接受修改排程或權限的指令。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 對失敗 jobs 分類、摘要 evidence 和建議安全 replay。</li><li>用 agent 將非結構化工作單轉成 versioned job parameters。</li><li>請 AI 產生 reconciliation report，找 schedule/state/business effect 差異。</li><li>讓 agent 執行唯讀定期巡檢，異常時建立 ticket 而非直接 mutation。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>每個 scheduled agent 有固定 owner、goal/instruction version、identity 和 expiry。</li><li>Mutating tools 使用 idempotency/run ID，操作數、時間、tokens 和 spend 有硬上限。</li><li>高風險 job 先 dry-run/preview，需批准後才執行；結果完整 audit。</li><li>RAG/文件中的 prompt injection 不能改變 tool policy、schedule 或 credentials。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

分散式排程的真相通常是「可能重複，所以讓重複安全；可能漏掉，所以持續 reconciliation」。專家不把 exactly-once 當宣傳詞，而會逐個 side effect 分析 crash boundary。Agent 增加更多 side effects，更需要 run ledger、tool-level idempotency 和可重放證據。

</aside>

## 動手驗證

1. 為一個 nightly job 定義 run ID、lateness、retry、idempotency 和 reconciliation。
2. 改寫 ledger 使用 SQLite unique key，模擬 process restart。
3. 畫出 operation 成功、completion write 失敗的 gap，選 outbox 或 external key。
4. 設計 scheduled agent manifest：owner、tools、identity、budgets、approval、audit。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. 為何分散式 job 常選 at-least-once？</summary>

在 worker/scheduler crash 和訊息丟失下較容易確保不漏；重複由 idempotent effect 和 reconciliation 處理。

</details>

<details class="qa"><summary>Q2. Exactly-once 最難的 gap 是什麼？</summary>

外部 side effect 已完成但本地 completion 記錄尚未 commit 時 crash，重試無法知道前次是否成功。

</details>

<details class="qa"><summary>Q3. Run ID 應如何選？</summary>

對同一業務 effect deterministic，例如日期+customer/invoice；retry 必須沿用，不能每次新建。

</details>

<details class="qa"><summary>Q4. Lease 為何還需要 fencing？</summary>

舊 worker 可能 pause 超過 lease 後恢復；fencing token 讓 resource 拒絕舊世代操作。

</details>

<details class="qa"><summary>Q5. Reconciliation 補足什麼？</summary>

將預期 schedule、系統 state 和真實 business effects 比較，找漏跑、重複與卡住，是線上 protocol 外的安全網。

</details>

<details class="qa"><summary>Q6. Scheduled agent 額外風險？</summary>

步數和 tool path 不確定、資料可能含 prompt injection、成本與 side effects 擴大，需要更嚴格 identity/budget/policy。

</details>

<details class="qa"><summary>Q7. 什麼 job 可以安全自動修復？</summary>

Effect 可逆/idempotent、判斷 deterministic、blast radius 小、已演練且有可靠 verification；否則先 ticket/approval。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Distributed Periodic Scheduling](https://sre.google/sre-book/distributed-periodic-scheduling/)
- [Site Reliability Engineering — Distributed Consensus](https://sre.google/sre-book/managing-critical-state/)
- [Google Cloud — How Google SRE is using agentic AI](https://cloud.google.com/blog/products/devops-sre/how-google-sre-is-using-agentic-ai-to-improve-operations/)
- [OWASP — Top 10 for LLM Applications 2025](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

---

# 第 42 章　Data Pipelines、Provenance、Backup 與 Integrity

<p class="chapter-question">Pipeline 顯示成功、backup 檔也存在，為什麼資料仍可能已經錯誤或無法恢復？</p>

<div class="chapter-meta"><span>難度：進階</span><span>Part 6 · Distributed Systems Reliability</span><span>Software Engineering × SRE × AI</span></div>

<aside class="callout promise" markdown="1">
<div class="callout-title">本章完成後</div>

用 immutable inputs、schema、checkpoint、quality gates、lineage、restore drill 和 business invariants 保護資料。

</aside>

## 你現在位於哪裡？

<div class="journey-map" aria-label="全書學習地圖"><span class="journey-node"><b>0</b>先建立全局模型</span><span class="journey-node"><b>1</b>Software Engineering 的根基</span><span class="journey-node"><b>2</b>團隊、文化與領導</span><span class="journey-node"><b>3</b>讓變更可以長期維持</span><span class="journey-node"><b>4</b>Testing、Build 與 Delivery</span><span class="journey-node"><b>5</b>SRE 與可靠性模型</span><span class="journey-node active"><b>6</b>Distributed Systems Reliability</span><span class="journey-node"><b>7</b>Incident、On-call 與學習</span><span class="journey-node"><b>8</b>組織落地與 Capstone</span></div>

<div class="chapter-position"><a class="position-card" href="#chapter-41-distributed-cron-leases-與-idempotent-jobs"><span>上一站</span><strong>41. Distributed Cron、Leases 與 Idempotent Jobs</strong></a><div class="position-card current"><span>你在這裡</span><strong>42. Data Pipelines、Provenance、Backup 與 Integrity</strong></div><a class="position-card" href="#chapter-43-on-call-與-evidence-driven-troubleshooting"><span>下一站</span><strong>43. On-call 與 Evidence-driven Troubleshooting</strong></a></div>

本章位於 **Part 6：Distributed Systems Reliability**。先理解這個 component 接收什麼問題、交付什麼能力，再進入工具或名詞；後文會把結果接回整條生命週期。

## 開始前：四個一定要先懂的概念

<aside class="callout prerequisite" markdown="1">
<div class="callout-title">不需要先跳出去查資料</div>

以下卡片已提供本章需要的最低背景。名詞不是背誦題；請把定義、例子與本章責任連在一起。

</aside>

<div class="term-grid"><section class="term-card"><h3>Data integrity</h3><div><span>白話定義</span><p>資料在儲存、傳輸、處理和恢復後仍正確、完整且符合 invariant。</p></div><div class="example"><span>具體例子</span><p>Backup 存在不代表可恢復；需定期 restore 並驗證 checksum 與業務規則。</p></div><div class="relevance"><span>本章位置</span><p>可靠性最終要保護使用者資料，而不只是 process uptime。</p></div></section><section class="term-card"><h3>Provenance（來源鏈）</h3><div><span>白話定義</span><p>記錄 artifact、資料或答案由哪些輸入、工具、版本與操作者產生。</p></div><div class="example"><span>具體例子</span><p>Container image 可追到 commit、lockfile、builder identity 和簽章。</p></div><div class="relevance"><span>本章位置</span><p>AI 回答也需保存 retrieval sources、model version 與 tool trace 才能稽核。</p></div></section><section class="term-card"><h3>Idempotency</h3><div><span>白話定義</span><p>同一操作執行一次或多次，外部結果相同。</p></div><div class="example"><span>具體例子</span><p>以 payment id 作唯一鍵，重送請求不會重複扣款。</p></div><div class="relevance"><span>本章位置</span><p>Cron、queue、retry 和 agent tool call 都需要 idempotency 才能安全恢復。</p></div></section><section class="term-card"><h3>Invariant（不變條件）</h3><div><span>白話定義</span><p>系統任何合法狀態都必須成立的規則。</p></div><div class="example"><span>具體例子</span><p>銀行轉帳前後，所有帳戶餘額總和不應憑空增加。</p></div><div class="relevance"><span>本章位置</span><p>測試、型別和監控常用來保護 invariant；它比描述每一行實作更穩定。</p></div></section></div>

## 為什麼需要這一章？

資料錯誤常是 silent failure：job 全部綠燈，卻少讀一個 partition、重複計數、schema 錯位或 backup 從未測過 restore。Availability 只表示系統回應，不代表資料正確。Data integrity 需要從 ingest 到處理、儲存、發布與恢復的端到端證據。

### 真實 Use Case

每日營收 pipeline 成功完成，但 upstream 時區改變使最後一小時資料落到隔天。Row count 看似正常，月報逐日偏差。若有 event-time coverage、source→output lineage、對帳 invariant 和 replay，才能發現與修復。

<div class="context-grid">
<section><span>問題壓力</span><p>資料錯誤常是 silent failure：job 全部綠燈，卻少讀一個 partition、重複計數、schema 錯位或 backup 從未測過 restore。Availability 只表示系統回應，不代表資料正確。Data integrity 需要從 ingest 到處理、儲存、發布與恢復的端到端證據。</p></section>
<section><span>交付能力</span><p>用 immutable inputs、schema、checkpoint、quality gates、lineage、restore drill 和 business invariants 保護資料。</p></section>
<section><span>真實場景</span><p>每日營收 pipeline 成功完成，但 upstream 時區改變使最後一小時資料落到隔天。Row count 看似正常，月報逐日偏差。若有 event-time coverage、source→output lineage、對帳 invariant 和 replay，才能發現與修復。</p></section>
</div>

## Blueprint：先看完整 Flow

<pre class="ascii-diagram"><code>source events/files
   ↓ immutable IDs / schema / checksum
ingest → raw durable layer
   ↓ watermark / dedupe / validation
transform stages → checkpoints + lineage
   ↓ quality gates / reconciliation / business invariants
published dataset / model / index
   ↓ consumers

backup → independent storage → restore drill → verify checksum + semantics</code></pre>

先沿箭頭讀一次：誰產生輸入、哪個 component 保存狀態、哪個 gate 能阻止錯誤前進、失敗後如何返回上一層。這張圖是本章所有細節的索引。

## 從零建立心智模型

Pipeline delivery semantics 要明確：at-least-once 需要 dedupe/idempotency，event time 與 processing time 分離，late data 用 watermark 和 correction。每階段保存 input versions、code/config、schema、counts/checksum 和 output lineage，才能 replay 與 root cause。

Quality gate 不只檢查 job exit code。Schema、null/range、uniqueness、referential integrity、distribution drift、completeness 和 business reconciliation 都可能需要。Quarantine invalid data 比默默 drop 更可調查；但 quarantine 也要 SLO、owner 和容量，不能成資料墳場。

Backup 的目標是 restore。定義 RPO（可接受資料遺失時間）與 RTO（恢復時間），使用獨立 failure domain、加密、access control 和 retention；定期在隔離環境 restore，驗證 checksum、schema 和實際業務查詢。不可變/版本化能防 accidental delete 與 ransomware。

### 內部機制：一步一步拆開

<div class="flow-grid"><div class="flow-card"><span>1</span><p>為 source 建 immutable identity、schema、checksum、event time 和 retention。</p></div><div class="flow-card"><span>2</span><p>Pipeline stages 保存 code/config/input/output lineage 與可重放 checkpoint。</p></div><div class="flow-card"><span>3</span><p>Quality gates 同時檢查技術 schema 和 business invariants/reconciliation。</p></div><div class="flow-card"><span>4</span><p>選 delivery semantics，使用 dedupe/idempotency 處理 replay 與 late data。</p></div><div class="flow-card"><span>5</span><p>依 RPO/RTO 設 backup，定期 restore drill 並驗證完整性與可用性。</p></div></div>

## Coding／實務例子

範例以 manifest checksum 驗證輸入是否與宣告相同。真實 pipeline 還需檔案原子發布、schema 與 partition coverage。

```python
from hashlib import sha256
from pathlib import Path

def checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def verify_manifest(entries: dict[Path, str]) -> list[Path]:
    return [
        path for path, expected in entries.items()
        if not path.exists() or checksum(path) != expected
    ]
```

### 如何讀這個例子

<div class="walkthrough-grid"><div class="flow-card"><span>1</span><p>Manifest 將 pipeline input set 和內容 identity 顯式化。</p></div><div class="flow-card"><span>2</span><p>Streaming blocks 避免一次把大檔案讀入記憶體。</p></div><div class="flow-card"><span>3</span><p>Checksum 能發現 bytes 改變，但不能證明業務語意正確。</p></div><div class="flow-card"><span>4</span><p>Manifest 本身需要簽章/provenance，否則 attacker 可同時改檔案與 expected hash。</p></div></div>

## Trade-offs 與 Failure Modes

- Job success 只代表 process 結束，不代表資料完整、唯一或正確。
- 無限保留所有版本會造成成本與敏感資料治理問題。
- Backup 和 production 使用同一權限/failure domain，事故會同時刪除。
- Replay 沒有 idempotency，修復一批資料卻產生重複 side effects。

不要把上面的 trade-off 背成口號。真正要練習的是：指出哪個 constraint 改變後，原本的選擇會不再合理，以及要用哪個 signal 看見它。

## AI 時代：這一章發生了什麼變化？

<aside class="callout ai-shift" markdown="1">
<div class="callout-title">AI Shift</div>

AI/RAG 系統把資料 pipeline 直接連到回答品質。需要記錄 document ACL、版本、來源、chunking、embedding/index、model/eval dataset lineage；防止 stale source、poisoning 和 cross-tenant retrieval。Training/eval 資料也需 consent、license、去重與 contamination 管理。AI 可協助 anomaly/root-cause，但不能以流暢摘要取代 checksum 和 reconciliation。

</aside>

<div class="comparison"><section class="compare-card positive"><h3>適合交給 AI 的工作</h3><ul><li>讓 AI 分析 schema/distribution drift，提出受影響 downstream 和重跑範圍。</li><li>用 agent 產生 data quality rules 候選，再由 domain owner確認 invariant。</li><li>請 AI 為 RAG 回答列 source/version/ACL，建立 unsupported claim eval。</li><li>讓 agent 協助 restore drill、比對 manifests 和產生 evidence report。</li></ul></section><section class="compare-card guardrail"><h3>必須建立的 Guardrails</h3><ul><li>Retrieval 必須 ACL-aware，索引不得讓模型繞過原資料權限。</li><li>保存 source→chunk→embedding/index→answer lineage 和版本。</li><li>外部/使用者資料視為不可信，隔離 prompt instructions 和 tool policy。</li><li>模型不能自行刪除/quarantine/replay 大量資料；需 bounds、preview、approval。</li></ul></section></div>

### Domain Expert Lens

<aside class="callout expert" markdown="1">
<div class="callout-title">不是工具清單，而是判斷邊界</div>

資料可靠性最深的原則是獨立驗證：同一 pipeline 自己產生的 success metric 可能共享同一 bug。使用 source reconciliation、另一種計算、consumer invariant 和 restore drill 建立不同證據。AI 讓非結構化資料可用，也使 provenance、ACL 和 poisoning 成為一級資料工程問題。

</aside>

## 動手驗證

1. 為一個 batch/stream 畫 source、checkpoint、lineage、quality、publish、replay。
2. 執行 checksum 範例，修改檔案後確認 manifest 失敗。
3. 寫三個技術 quality checks 與三個 business invariants。
4. 為 RAG 建 provenance schema：document、ACL、version、chunk、index、answer、eval。

## Follow-up Questions & Answers

<details class="qa"><summary>Q1. Pipeline job 成功為何不等於資料正確？</summary>

Process 可在漏 partition、schema 誤解、重複、時區錯誤下正常結束；需要 completeness、quality 和 business reconciliation。

</details>

<details class="qa"><summary>Q2. Provenance/lineage 有什麼價值？</summary>

能回答輸出由哪些 source、code、config 和版本產生，支援 impact analysis、replay、audit 和 root cause。

</details>

<details class="qa"><summary>Q3. Checksum 能證明什麼與不能證明什麼？</summary>

證明 bytes 與 expected 相同；不能證明 schema、語意、完整 input set 或 expected manifest 本身可信。

</details>

<details class="qa"><summary>Q4. RPO 與 RTO 差別？</summary>

RPO 是可接受遺失多少時間的資料；RTO 是事故後多快恢復服務/資料。

</details>

<details class="qa"><summary>Q5. 為何一定要 restore drill？</summary>

Backup 檔存在不代表權限、工具、schema、依賴和時間內能恢復；只有實際 restore 能驗證。

</details>

<details class="qa"><summary>Q6. RAG 特有的 integrity 風險？</summary>

Stale/poisoned documents、ACL leakage、錯誤 chunk/index、來源缺失和 cross-tenant retrieval。

</details>

<details class="qa"><summary>Q7. Reconciliation 為何應獨立？</summary>

若使用同一 code/assumption 計算輸出與驗證，bug 可能同時存在；獨立 evidence 提高辨識力。

</details>

## 本章官方來源與延伸閱讀

- [Site Reliability Engineering — Data Processing Pipelines](https://sre.google/sre-book/data-processing-pipelines/)
- [Site Reliability Engineering — Data Integrity](https://sre.google/sre-book/data-integrity/)
- [Site Reliability Engineering — Testing for Reliability](https://sre.google/sre-book/testing-reliability/)
- [OWASP — Top 10 for LLM Applications 2025](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

---
