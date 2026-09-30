---
title: Interview Operating System
tags:
  - coding-interview
  - communication
status: complete
updated: 2026-09-30
---

# Interview Operating System

[[01 - How to Use This Book|← 上一章]] · [[00 - Book Index|目錄]] · [[03 - Pattern Decision Tree|下一章 →]]

## 七階段流程

### 1. Clarify

先問會改變解法的問題：

- 輸入可否為空？
- 是否有重複值、負數、overflow？
- 是否排序？
- 要回傳任一答案、全部答案，還是數量？
- 可以修改輸入嗎？
- 資料一次給完，還是 streaming？

### 2. 建立小例子

至少準備：

- 最小輸入。
- 一般案例。
- 容易誤判的邊界案例。

### 3. 說出 Brute Force

Brute force 不是浪費時間。它提供：

- 正確性基準。
- 可以被消除的重複工作。
- 最佳化方向。

### 4. 找到重複工作或結構

常見訊號：

- 重複查找 → Hash map。
- 連續區間 → Window / Prefix。
- 單調性 → Binary search / monotonic structure。
- 所有選擇 → Backtracking。
- 重疊子問題 → DP。
- 關係與連通 → Graph。

### 5. 先說 invariant，再寫程式

例：

> 視窗 `[left, right]` 在每次計算答案前都滿足「沒有重複字元」。

> heap 永遠保存目前看過的最大 `k` 個元素，所以 heap root 是第 `k` 大。

### 6. 寫可以執行的程式

- 先寫 function signature。
- 再寫主要迴圈。
- 最後補 helper。
- 不要在未定義資料結構時同時寫五個 helper。

### 7. 主動測試

依序測：

1. Empty / single element。
2. 全部相同。
3. 嚴格遞增或遞減。
4. 答案在開頭、結尾或不存在。
5. 最大值、負值與重複值。

## 面試時可以直接使用的敘述

> 我先確認回傳的是任一組答案還是全部答案，因為這會影響去重方式。

> Brute force 需要枚舉所有配對，時間是 $O(n^2)$。重複工作是對先前元素的查找，因此我會用 hash map 降成平均 $O(1)$ 查找。

> 在開始 coding 前，我先定義 invariant：……

> 我會先測最小輸入，再測重複值與答案不存在的情況。

## 卡住時的恢復順序

1. 把 constraints 轉成可接受複雜度。
2. 寫出 brute force。
3. 圈出重複工作。
4. 問「資料是否有單調性、順序、連續性或重疊狀態」。
5. 嘗試把答案改成 decision problem。
6. 縮小輸入，手算狀態變化。

> [!tip] 面試官給的提示是合作訊號
> 接到提示後，先重述你理解的意思，再把它接到現有解法。不要只回答「喔，了解」然後沉默。
