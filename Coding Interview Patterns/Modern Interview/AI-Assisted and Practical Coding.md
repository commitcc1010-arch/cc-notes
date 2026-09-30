---
title: AI-Assisted and Practical Coding
tags:
  - coding-interview
  - ai-assisted-coding
  - practical-coding
status: complete
updated: 2026-09-30
---

# AI-Assisted and Practical Coding

[[00 - Book Index|回到目錄]]

## 新型面試在測什麼

- 能否閱讀陌生程式碼。
- 能否辨認 AI 產生但語意錯誤的實作。
- 能否把模糊需求轉成明確 contract。
- 能否設計測試，而不是只讓 sample 通過。
- 能否解釋自己接受或拒絕某段建議的原因。

## AI-assisted 工作流程

1. 自己先寫 specification 與 edge cases。
2. 要求 AI 提出小範圍實作，不一次產生整個系統。
3. 檢查 invariant、複雜度與依賴。
4. 先讀 diff，再執行測試。
5. 增加 adversarial tests。
6. 能不用 AI 從頭解釋每一行。

## 練習一：審查錯誤的 LRU

題目：候選實作在 `get` 時沒有把節點移到 MRU，且更新既有 key 時重複建立節點。

應指出：

- 哪個 invariant 被破壞。
- 最小失敗測試。
- 修正後每個操作為何仍是 $O(1)$。

```python
cache.put(1, 10)
cache.put(2, 20)
assert cache.get(1) == 10
cache.put(3, 30)
assert cache.get(2) == -1
```

## 練習二：模糊的 Rate Limiter

開始 coding 前必須詢問：

- 限制是 per user、per token 還是 global？
- fixed window、sliding window 或 token bucket？
- 多執行緒或多機器嗎？
- 時鐘回撥怎麼處理？
- 超過限制要 drop、queue 還是 retry？

## 練習三：測試 AI 產生的 Binary Search

至少測：

- 空陣列。
- 單元素存在／不存在。
- 答案在第一與最後位置。
- 重複值。
- `lo + 1 == hi`。

> [!warning]
> 是否允許 AI 由公司與面試輪次決定。沒有明確允許時，不要自行使用。
