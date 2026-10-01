# AI Autonomy Maturity Model

# AI Autonomy Maturity Model

自治不是產品開關，而是依風險與證據逐步取得。

| Level | 能力 | 最低控制 | 適合情境 |
|---|---|---|---|
| 0 | Chat / explain | 資料政策、人工判斷 | 學習、草擬、搜尋方向 |
| 1 | Read-only assistant | ACL、redaction、來源、audit | Code/telemetry 導覽 |
| 2 | Scoped workspace writer | Sandbox、Git branch、tests、review | 文件、低風險 code |
| 3 | Agent-created PR | Deterministic gates、independent review | 一般產品變更 |
| 4 | Bounded auto-merge | 高品質 eval、risk classification、rollback | 小型可逆維護 |
| 5 | Production recommendation | Workload identity、evidence links、runbook | SRE 調查 |
| 6 | Approved mutation | Least privilege、preview、approval、watch | 可逆 production 操作 |
| 7 | Bounded closed loop | SLO、hard budgets、kill switch、game day | 成熟、低 blast-radius automation |

## 每次升級前的問題

1. 任務是否有可信且可執行的完成條件？
2. 歷史 eval 是否包含正常、模糊、故障、攻擊與拒絕案例？
3. Action 是否可逆、idempotent、scope 有界？
4. Agent 是否可能改掉自己的 tests、policy 或 audit？
5. Identity、資料與 tools 是否遵守 least privilege？
6. 錯誤 action 如何被偵測、停止、rollback 和調查？
7. 人類是否仍知道如何在 agent 不可用時操作？

## Agent control plane

```text
User / scheduler / incident
          ↓
Identity + risk classification
          ↓
Context broker ── ACL / provenance / freshness
          ↓
Model / agent loop ── step / token / cost / time budgets
          ↓
Tool broker ── schema / policy / approval / idempotency
          ↓
Sandbox or production system
          ↓
Trace / eval / audit / SLO / incident controls
```

## 評估維度

- Task：是否真的完成使用者目標？
- Process：是否選對 tools、遵守順序與 scope？
- Safety：是否拒絕 prompt injection、秘密外洩和 excessive agency？
- Reliability：timeout、partial failure、retry、fallback 是否正確？
- Human：review/rework、信任、認知負荷與接管是否改善？
- Economics：latency、tokens、compute、tool calls 和 opportunity cost。
