---
title: How to Use This Book
tags:
  - coding-interview
  - study-plan
status: complete
updated: 2026-09-30
---

# 如何使用這本書

[[00 - Book Index|← 回到目錄]] · [[02 - Interview Operating System|下一章 →]]

## 本書的問題層級

每個 pattern 固定包含八道完整題解：

- **核心題 × 3**：建立最小但完整的 mental model。
- **上限題 × 5**：探索 pattern 與其他技巧交界時最困難的變形。

> [!note] 「上限題」的定義
> 這裡指能代表該 domain 推理上限與跨 pattern 變化的題目，不完全等同網站上的 Hard badge；有些 Medium 題在 follow-up 後反而更能測出真正理解。

每一道題都有一致的完整學習層：

1. 題目真正想測的知識點與核心轉換。
2. 從暴力到最佳模型的視覺化流程。
3. state、transition、invariant 與五步推導。
4. 正確性證明骨架與最容易錯的邊界。
5. 完整 Python 解答與複雜度。
6. **4 組 Follow-up**：原題直接變形、限制改動、答案重建、線上／production 化。

上限題另有三層漸進提示。新增的深入證明、陷阱與 Follow-up 預設折疊；第一次閱讀先走主線，需要時再展開。

## 一題的正確使用方法

### 第一次：限制時間

- 核心題：15–20 分鐘。
- 上限題：25–35 分鐘。
- 時間到就看「提示一」，不要直接看答案。
- 再思考 5 分鐘；仍卡住才看下一層提示。

### 第二次：關閉答案重寫

你必須能回答：

- 狀態或資料結構代表什麼？
- 每次迭代前後，什麼條件永遠成立？
- 為什麼不會漏答案？
- 為什麼不會重複計算？
- 最大輸入下會不會超時或爆記憶體？

### 第三次：做 Follow-up

Follow-up 才是判斷是否真正理解的地方。原題可能靠記憶，限制改動後仍能推導，才代表模型已內化。

每題依序回答：

1. 原題直接變形：確認演算法細節。
2. Constraints 改變：指出哪個假設失效，提出替代方案。
3. 完整答案重建：回傳 index、path、cut、操作序列或可驗證 witness。
4. 線上／production：討論記憶體、併發、版本、SLA 與測試。

若只能說「換一個資料結構」卻無法指出原 invariant 為何失效，仍不算完成。

## 三色標記

- 🟢：能在時限內獨立完成並解釋。
- 🟡：看一層提示後完成。
- 🔴：看過答案仍無法隔天重建。

建議在每章 frontmatter 或自己的追蹤頁記錄：

```yaml
confidence: yellow
last_reviewed: 2026-09-30
next_review: 2026-10-02
```

## 間隔複習

| 時間 | 任務 |
|---|---|
| 當天 | 理解並手寫 |
| +1 天 | 從空白重建 |
| +3 天 | 只看題目與限制重做 |
| +7 天 | 做 follow-up |
| +14 天 | 混合 mock 中重做 |

## 語言策略

本書以 Python 3 為主，因為程式碼短，面試時能把時間放在推理。若實際面試使用 Java、C++ 或 TypeScript：

1. 先用 Python 理解 pattern。
2. 用目標語言重寫 template。
3. 特別練習 comparator、heap、queue、set、overflow 與字串處理。

參考 [[Python Interview Toolbox]]。

## 誠實的能力邊界

完成本書應能涵蓋一般軟體工程 coding interview 的主要演算法與資料結構變形，但以下職位仍需要額外準備：

- ML：機率、線性代數、ML implementation。
- Embedded：C/C++、記憶體與硬體限制。
- Frontend：JavaScript runtime、DOM、非同步與 UI 實作。
- Database：SQL、transaction、query planning。
- Quant：機率、組合數學與數值方法。
