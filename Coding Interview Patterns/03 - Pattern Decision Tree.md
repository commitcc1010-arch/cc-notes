---
title: Pattern Decision Tree
tags:
  - coding-interview
  - cheat-sheet
status: complete
updated: 2026-09-30
---

# Pattern Decision Tree

[[02 - Interview Operating System|← 上一章]] · [[00 - Book Index|目錄]]

## 第一層：題目在問什麼

| 訊號 | 先檢查 |
|---|---|
| 配對、頻率、去重、是否存在 | [[01 - Hashing and Counting]] |
| 已排序、由兩端逼近、原地重排 | [[02 - Two Pointers]] |
| 最長／最短連續 subarray 或 substring | [[03 - Sliding Window]] |
| 區間和、子陣列數量、大量 range update | [[04 - Prefix Sum and Difference Array]] |
| 排序資料或答案具有單調可行性 | [[05 - Binary Search]] |
| 區間重疊、會議、事件時間軸 | [[06 - Sorting Intervals and Sweep Line]] |
| 最近未完成項目、下一個更大／更小 | [[07 - Stack and Monotonic Stack]] |
| 節點重接、不能 random access | [[08 - Linked List]] |
| 父子階層、subtree 回傳資訊 | [[09 - Binary Tree]] |
| 有序樹搜尋、prefix dictionary | [[10 - BST and Trie]] |
| 動態維持最小／最大或前 K 名 | [[11 - Heap Top-K and K-way Merge]] |
| 網格／關係的可達性與最少步數 | [[12 - Graph DFS and BFS]] |
| 相依順序、連通合併、加權路徑 | [[13 - Graph DAG Union-Find and Shortest Path]] |
| 列舉所有合法組合 | [[14 - Backtracking]] |
| 每一步可證明安全地做局部選擇 | [[15 - Greedy]] |
| 一維歷史狀態或有限狀態機 | [[16 - DP 1D and State Machine]] |
| 兩序列、區間切割、網格狀態 | [[17 - DP 2D Sequence and Interval]] |
| XOR、位元、數論、座標 | [[18 - Bit Math and Geometry]] |
| 要設計 API 並維持多個 invariant | [[19 - Data Structure Design]] |
| 規則很多、照步驟更新世界狀態 | [[20 - Matrix Simulation and Parsing]] |

## 第二層：Constraints 對複雜度的暗示

| `n` 大小 | 常見可接受上限 |
|---:|---|
| `n <= 20` | $O(2^n)$、backtracking、bitmask |
| `n <= 100` | $O(n^3)$ 有機會 |
| `n <= 1,000` | $O(n^2)$ |
| `n <= 100,000` | $O(n \log n)$ |
| `n <= 1,000,000` | $O(n)$ |
| `n` 極大但答案範圍有限 | $O(\log answer)$ |

## 第三層：容易混淆的選擇

### Sliding Window vs Prefix Sum

- Window：加入右端、移除左端後，狀態可以增量維護。
- Prefix：要查任意區間，或負數破壞 window 單調性。

### Greedy vs DP

- Greedy：能證明目前選擇不會讓未來變差。
- DP：同一狀態有多種歷史，需要比較後保留最佳值。

### BFS vs Dijkstra

- 每條邊成本相同 → BFS。
- 非負但不同權重 → Dijkstra。
- 有負權邊 → Bellman–Ford 類方法。

### Heap vs Binary Search on Answer

- 要動態取目前最小／最大 → Heap。
- 能快速判斷「答案 `x` 是否可行」，且可行性單調 → Binary search。
