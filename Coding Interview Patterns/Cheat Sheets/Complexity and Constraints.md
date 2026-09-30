---
title: Complexity and Constraints
tags:
  - coding-interview
  - complexity
  - cheat-sheet
status: complete
updated: 2026-09-30
---

# Complexity and Constraints

[[00 - Book Index|回到目錄]]

## 資料結構操作

| 結構 | 查找 | 插入 | 刪除 | 特性 |
|---|---:|---:|---:|---|
| list 尾端 | — | amortized $O(1)$ | $O(1)$ | random access $O(1)$ |
| list 中間 | $O(n)$ | $O(n)$ | $O(n)$ | |
| dict / set | avg $O(1)$ | avg $O(1)$ | avg $O(1)$ | worst case $O(n)$ |
| deque 兩端 | — | $O(1)$ | $O(1)$ | |
| heap | top $O(1)$ | $O(\log n)$ | $O(\log n)$ | 非完整排序 |
| balanced BST | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | Python 無內建 |

## 圖與樹

- DFS/BFS：$O(V + E)$。
- Dijkstra binary heap：$O((V + E)\log V)$。
- Union-Find：近似 $O(1)$ amortized。
- Topological sort：$O(V + E)$。

## 排序

- Comparison sort 下限：$O(n \log n)$。
- Bucket/counting sort 可在值域有限時到 $O(n + k)$。
- Python `sort` 是 stable，時間通常視為 $O(n \log n)$。

## 空間分析

不要漏算：

- recursion call stack。
- queue / heap。
- DP table。
- 輸出本身。

若題目要求「額外空間 $O(1)$」，通常不把輸出計入，但面試時應先確認。
