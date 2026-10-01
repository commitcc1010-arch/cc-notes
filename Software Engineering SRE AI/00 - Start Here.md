# 導讀　這不是兩本書的摘要，而是一套工程 Operating System

《Software Engineering at Google》主要回答：程式碼如何跨越時間、規模與多人協作，仍然能被安全修改。《Site Reliability Engineering》主要回答：服務進入 production 後，如何在真實故障、流量與組織壓力下持續提供使用者價值。

本書將兩者重組成一條生命週期，而不是要求讀者在兩本書之間來回跳轉：

```text
Intent → Design → Code → Review → Test / Build → CI → Release → Production
  ↑                                                                  ↓
  └──── Docs / Rules / Platform ← Postmortem ← Incident ← SLO / Telemetry
```

AI 是這條路徑的新執行者，但不是新的責任主體：

```text
Human intent / risk ownership
          ↓
bounded context → agent plan → sandboxed tools → deterministic evidence
          ↓                                     ↓
independent review ← audit / eval ← canary / production feedback
```

## 這本書對「自包含」的定義

- 名詞第一次使用前，先有白話定義、具體例子與本章位置。
- 每章先說 context、use case 和完整 blueprint，再談工具與實作。
- 外部連結只是來源核對；理解正文不需要跳出本書。
- 每章都有 coding 或可執行實務模型、逐步 walkthrough、trade-offs。
- 每章都有 AI Shift、目前可移植的 industry practices 與 guardrails。
- 每章至少七組 follow-up questions，答案不是一句提示，而是解釋判斷。
- 所有 Q&A 在 EPUB 會被轉為普通內容並強制展開。

## 一個反覆使用的判斷框架

面對任何工程元件，依序問：

1. 它替哪個使用者或下游解決什麼問題？
2. Input、output、state、owner 和 failure contract 是什麼？
3. 沒有它時，哪種成本或風險會出現？
4. 它提供的 evidence 是否足以支持下一個決策？
5. 它在哪些 scale、risk 或 cost 下不再合理？
6. AI 能協助哪一段？哪些 judgment、permission 和 accountability 必須留給人？
7. 失敗如何停止、rollback、觀測並轉成下一次改進？

## 建議閱讀方式

第一次只保留每章四件事：為何存在、blueprint、核心 invariant、AI boundary。第二次再執行 example/lab。第三次挑自己公司的真實 service，將章節 artifact 寫出來：ADR、SLO、test portfolio、runbook、postmortem 或 agent policy。

本書截至 2026-09-30 整理 AI-assisted development 與 AI-SRE 實務。具體模型和產品會快速變化；context、verification、least privilege、eval、observability、ownership 和 gradual autonomy 等原則較能跨工具保留。
