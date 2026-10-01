# Reliability Math 速查

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
