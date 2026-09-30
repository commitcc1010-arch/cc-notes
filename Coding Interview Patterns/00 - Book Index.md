---
title: Coding Interview Patterns
aliases:
  - Coding Interview Pattern Handbook
  - 程式面試模式手冊
tags:
  - coding-interview
  - algorithms
  - study-guide
status: complete
updated: 2026-09-30
core_patterns: 20
core_questions: 60
hard_questions: 100
followups: 640
visual_explanations: 160
---

# Coding Interview Patterns

> [!abstract] 20 個模型、160 題視覺化題解與 640 組 Follow-ups
> 這本書的目標不是背題，而是把看似不同的面試題壓縮成 20 個可以辨認、推導、證明與實作的模型。每章含 3 題核心題與 5 題高難度題；每題都有考點拆解、視覺化流程、五步推導、正確性證明、邊界陷阱、Python 解答，以及 4 組不同維度的 follow-up 與答案。

## 從這裡開始

1. [[01 - How to Use This Book|如何使用本書]]
2. [[02 - Interview Operating System|面試解題流程]]
3. [[03 - Pattern Decision Tree|Pattern Decision Tree]]
4. 選擇 [[14-Day Sprint]] 或 [[21-Day Complete]]
5. 開始 Pattern 章節

## 全書地圖

```mermaid
flowchart LR
    A[釐清輸入與限制] --> B{資料有順序嗎}
    B -->|雙端或已排序| C[Two Pointers / Binary Search]
    B -->|連續區間| D[Sliding Window / Prefix Sum]
    B -->|局部最值| E[Heap / Monotonic Stack]
    B -->|關係與連通| F[Tree / Graph]
    B -->|列舉選擇| G[Backtracking / DP]
    B -->|操作序列| H[Greedy / Simulation]
    B -->|需要 O(1) 查找| I[Hashing / Design]
```

## Part I：基礎設施

- [[01 - How to Use This Book]]
- [[02 - Interview Operating System]]
- [[03 - Pattern Decision Tree]]
- [[Python Interview Toolbox]]
- [[Complexity and Constraints]]

## Part II：20 個 Patterns

| # | Pattern | 核心題 | 難題 | 狀態 |
|---:|---|---:|---:|---|
| 1 | [[01 - Hashing and Counting]] | 3 | 5 | 完整章節 |
| 2 | [[02 - Two Pointers]] | 3 | 5 | 完整章節 |
| 3 | [[03 - Sliding Window]] | 3 | 5 | 完整章節 |
| 4 | [[04 - Prefix Sum and Difference Array]] | 3 | 5 | 完整章節 |
| 5 | [[05 - Binary Search]] | 3 | 5 | 完整章節 |
| 6 | [[06 - Sorting Intervals and Sweep Line]] | 3 | 5 | 完整章節 |
| 7 | [[07 - Stack and Monotonic Stack]] | 3 | 5 | 完整章節 |
| 8 | [[08 - Linked List]] | 3 | 5 | 完整章節 |
| 9 | [[09 - Binary Tree]] | 3 | 5 | 完整章節 |
| 10 | [[10 - BST and Trie]] | 3 | 5 | 完整章節 |
| 11 | [[11 - Heap Top-K and K-way Merge]] | 3 | 5 | 完整章節 |
| 12 | [[12 - Graph DFS and BFS]] | 3 | 5 | 完整章節 |
| 13 | [[13 - Graph DAG Union-Find and Shortest Path]] | 3 | 5 | 完整章節 |
| 14 | [[14 - Backtracking]] | 3 | 5 | 完整章節 |
| 15 | [[15 - Greedy]] | 3 | 5 | 完整章節 |
| 16 | [[16 - DP 1D and State Machine]] | 3 | 5 | 完整章節 |
| 17 | [[17 - DP 2D Sequence and Interval]] | 3 | 5 | 完整章節 |
| 18 | [[18 - Bit Math and Geometry]] | 3 | 5 | 完整章節 |
| 19 | [[19 - Data Structure Design]] | 3 | 5 | 完整章節 |
| 20 | [[20 - Matrix Simulation and Parsing]] | 3 | 5 | 完整章節 |

## Part III：公司與現代面試

- [[Big Tech Last-Mile Playbook]]
- [[AI-Assisted and Practical Coding]]
- [[6 Mixed Mock Interviews]]
- [[Sources and Survey Methodology]]

## 每一題的完成標準

- [ ] 可以用一句話說出辨認訊號
- [ ] 可以先提出正確但較慢的解法
- [ ] 可以從視覺圖重建 state、transition 與答案更新時機
- [ ] 可以說明最佳解法的 invariant
- [ ] 可以在沒有 IDE 的情況下寫出主體
- [ ] 可以自己產生邊界測試
- [ ] 可以回答限制改動、答案重建與 production 化的 follow-up

> [!warning] 「看完」不等於「會做」
> 讀完解法後，隔天必須從空白重新寫一次。若只能看懂、不能重建，就仍屬於未完成。
