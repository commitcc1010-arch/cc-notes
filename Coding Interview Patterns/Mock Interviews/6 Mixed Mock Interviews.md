---
title: 6 Mixed Mock Interviews
tags:
  - coding-interview
  - mock-interview
status: complete
updated: 2026-09-30
mock_count: 6
---

# 6 Mixed Mock Interviews

[[00 - Book Index|回到目錄]]

## 使用規則

- 不先看 pattern 名稱。
- 口述 clarifying questions、brute force、最佳化與 invariant。
- 寫完主動測試。
- 時間到才開答案連結。
- 每場結束依 rubric 自評。

## 評分 Rubric（每場 20 分）

| 項目 | 分數 |
|---|---:|
| 釐清需求與 edge cases | 3 |
| Brute force 與複雜度 | 3 |
| Pattern 辨認與推導 | 4 |
| 正確且可執行程式碼 | 5 |
| 測試與 bug 修正 | 3 |
| Follow-up | 2 |

16–20：面試可用；12–15：需複習黃色題；低於 12：重做相關章節。

---

## Mock 1：Meta-style Speed Round（35 分鐘）

### Question A（17 分鐘）

計算總和恰為 `k` 的連續 subarray 數量；數字可為負。

- Follow-up：改求最長長度。
- 答案：[[04 - Prefix Sum and Difference Array#核心題 2：Subarray Sum Equals K]]

### Question B（17 分鐘）

找 binary tree 中兩個指定節點的 lowest common ancestor。

- Follow-up：不保證兩節點存在。
- 答案：[[09 - Binary Tree#核心題 2：Lowest Common Ancestor]]

---

## Mock 2：Amazon-style Robust Implementation（45 分鐘）

### Question A（30 分鐘）

實作固定容量 LRU cache，所有操作平均 $O(1)$。

- Follow-up：加入 TTL 與 thread safety。
- 答案：[[19 - Data Structure Design#核心題 1：LRU Cache]]

### Question B（15 分鐘）

計算 0/1 grid 的 islands 數量。

- Follow-up：陸地逐筆加入，每次回傳 island 數。
- 答案：[[12 - Graph DFS and BFS#核心題 1：Number of Islands]]

---

## Mock 3：Google-style Transformation（45 分鐘）

### Question A（20 分鐘）

求能在指定時間內處理完所有工作量的最小整數速度。

- Follow-up：說明 predicate 的單調性。
- 答案：[[05 - Binary Search#核心題 3：Koko Eating Bananas]]

### Question B（25 分鐘）

陣列含負數，求總和至少 `k` 的最短 subarray。

- Follow-up：若全為正數，如何簡化？
- 答案：[[04 - Prefix Sum and Difference Array#難題 5：Shortest Subarray with Sum at Least K]]

---

## Mock 4：Graph Round（45 分鐘）

### Question A（25 分鐘）

由已排序的外星字典推導字母順序。

- Follow-up：回傳 lexicographically smallest order。
- 答案：[[13 - Graph DAG Union-Find and Shortest Path#難題 1：Alien Dictionary]]

### Question B（20 分鐘）

計算 weighted network 中訊號傳到所有節點的時間。

- Follow-up：若出現負權 edge？
- 答案：[[13 - Graph DAG Union-Find and Shortest Path#核心題 3：Network Delay Time]]

---

## Mock 5：Dynamic Programming Round（45 分鐘）

### Question A（18 分鐘）

使用可重複硬幣組成 amount，求最少硬幣數。

- Follow-up：改成計算組合數量。
- 答案：[[16 - DP 1D and State Machine#核心題 3：Coin Change]]

### Question B（27 分鐘）

實作支援 `.` 與 `*` 的完整 regular-expression matching。

- Follow-up：`*` 改成 glob 語意。
- 答案：[[17 - DP 2D Sequence and Interval#難題 1：Regular Expression Matching]]

---

## Mock 6：Modern Practical Coding（60 分鐘）

### Question A（35 分鐘）

實作支援括號與四則運算的 expression evaluator。

- Follow-up：加入變數與 assignment。
- 答案：[[20 - Matrix Simulation and Parsing#難題 1：Basic Calculator III]]

### Question B（25 分鐘）

閱讀 LFU cache 實作並回答：

1. `min_freq` 何時更新？
2. 相同 frequency 如何決定 victim？
3. 更新既有 key 是否增加 frequency？
4. 哪些更新必須是 atomic？

- 答案：[[08 - Linked List#難題 4：LFU Cache]]
