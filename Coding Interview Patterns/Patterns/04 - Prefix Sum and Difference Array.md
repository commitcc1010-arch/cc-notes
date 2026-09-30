---
title: Prefix Sum and Difference Array
tags:
  - coding-interview/pattern
  - prefix-sum
  - difference-array
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 04 — Prefix Sum and Difference Array

[[03 - Sliding Window|← 上一章]] · [[00 - Book Index|目錄]] · [[05 - Binary Search|下一章 →]]

> [!abstract] Mental model
> Prefix sum 把「區間」轉成兩個邊界狀態的差；difference array 則把「更新整段區間」轉成只改兩個邊界。當負數破壞 sliding window 的單調性時，prefix state 往往仍可使用。

## 兩個基本公式

若 `prefix[i]` 表示前 `i` 個元素總和：

$$
sum(l, r) = prefix[r+1] - prefix[l]
$$

若要對閉區間 `[l, r]` 加上 `x`：

```text
diff[l] += x
diff[r + 1] -= x
```

最後對 `diff` 做一次 prefix sum 即可還原。

---

## 核心題 1：Product of Array Except Self

### 題目

對每個 index，回傳除了自己以外所有元素的乘積；不可使用除法。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 對每個 index，回傳除了自己以外所有元素的乘積；不可使用除法。
>
> **核心轉換：** 答案是「左側乘積 × 右側乘積」。先由左至右把左乘積寫入答案，再由右至左乘上右乘積。
>
> **主要知識點：** Prefix Summary、Difference Array 與離線聚合。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Product of Array Except Self
      │
      ├─ 暴力路線：對每個 query 或每個區間重新走訪所有元素
      │
      ▼  找出本題最關鍵的轉換
核心觀察：答案是「左側乘積 × 右側乘積」。先由左至右把左乘積寫入答案，再由右至左乘上右乘積。
      │
Pattern toolbox：prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件
      │
      ├─ 狀態轉移：把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原
      │
      ├─ 永遠成立：prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 對每個 index，回傳除了自己以外所有元素的乘積；不可使用除法。
2. **寫出暴力：** 對每個 query 或每個區間重新走訪所有元素。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 答案是「左側乘積 × 右側乘積」。先由左至右把左乘積寫入答案，再由右至左乘上右乘積。
4. **定義 state 與轉移：** 使用「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」承載上述觀察，再執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」代表什麼，再說每一步如何「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部」的 base case。
>
> 2. **維持：** 每次執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」後，狀態仍與已處理資料一致。關鍵論證是：由 prefix 定義直接代數化區間公式，證明每個元素的貢獻在進入與離開區間時恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：prefix 長度 n+1、左邊界為 0、負數、整數 overflow、inclusive/exclusive 定義與二維座標偏移。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 推導

答案是「左側乘積 × 右側乘積」。先由左至右把左乘積寫入答案，再由右至左乘上右乘積。

```python
def product_except_self(nums):
    answer = [1] * len(nums)
    prefix = 1
    for i, x in enumerate(nums):
        answer[i] = prefix
        prefix *= x

    suffix = 1
    for i in range(len(nums) - 1, -1, -1):
        answer[i] *= suffix
        suffix *= nums[i]
    return answer
```

- 時間：$O(n)$
- 額外空間：$O(1)$，不含輸出

### Follow-up 1：原題直接變形
**問：陣列含零時為何仍正確？**

**答：**演算法沒有做除法。每個位置只乘真正位於其左、右側的值，因此一個零時只有零所在位置可能非零；兩個以上零時所有答案自然變零。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Product of Array Except Self》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：答案是「左側乘積 × 右側乘積」。先由左至右把左乘積寫入答案，再由右至左乘上右乘積。 失效情境包括：若更新與查詢交錯，靜態 prefix 會因每次更新而失效；若摘要不可結合或不可逆，也無法只靠兩個邊界。
>
> 替代路線是：改用 Fenwick tree、segment tree、ordered prefix states 或 divide-and-conquer；大量離線 query 可考慮排序事件。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存達成最佳 prefix relation 的 index；DP 類 prefix 題保存前驅，區間更新則輸出事件或實際受影響區段。
>
> 套回《Product of Array Except Self》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大資料可做分塊 prefix 與 parallel scan；線上更新要明確選 Fenwick/segment tree，並處理版本、快照與 overflow。
>
> 此外必須把《Product of Array Except Self》目前隱含的前提寫成 contract：對每個 index，回傳除了自己以外所有元素的乘積；不可使用除法。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Subarray Sum Equals K

### 題目

計算總和恰為 `k` 的連續 subarray 數量；元素可為負數。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 計算總和恰為 k 的連續 subarray 數量；元素可為負數。
>
> **核心轉換：** 若目前 prefix sum 為 p，需要先前存在 p-k。Map 保存每個 prefix sum 出現次數，而不是只保存是否出現。
>
> **主要知識點：** Prefix Summary、Difference Array 與離線聚合。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Subarray Sum Equals K
      │
      ├─ 暴力路線：對每個 query 或每個區間重新走訪所有元素
      │
      ▼  找出本題最關鍵的轉換
核心觀察：若目前 prefix sum 為 p，需要先前存在 p-k。Map 保存每個 prefix sum 出現次數，而不是只保存是否出現。
      │
Pattern toolbox：prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件
      │
      ├─ 狀態轉移：把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原
      │
      ├─ 永遠成立：prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 計算總和恰為 k 的連續 subarray 數量；元素可為負數。
2. **寫出暴力：** 對每個 query 或每個區間重新走訪所有元素。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 若目前 prefix sum 為 p，需要先前存在 p-k。Map 保存每個 prefix sum 出現次數，而不是只保存是否出現。
4. **定義 state 與轉移：** 使用「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」承載上述觀察，再執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」代表什麼，再說每一步如何「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部」的 base case。
>
> 2. **維持：** 每次執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」後，狀態仍與已處理資料一致。關鍵論證是：由 prefix 定義直接代數化區間公式，證明每個元素的貢獻在進入與離開區間時恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：prefix 長度 n+1、左邊界為 0、負數、整數 overflow、inclusive/exclusive 定義與二維座標偏移。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 推導

若目前 prefix sum 為 `p`，需要先前存在 `p-k`。Map 保存每個 prefix sum 出現次數，而不是只保存是否出現。

```python
from collections import defaultdict

def subarray_sum(nums, k):
    frequency = defaultdict(int)
    frequency[0] = 1
    prefix = answer = 0
    for x in nums:
        prefix += x
        answer += frequency[prefix - k]
        frequency[prefix] += 1
    return answer
```

- 時間：$O(n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：改成最長總和為 `k` 的 subarray？**

**答：**保存每個 prefix sum 第一次出現的位置。要最大長度，所以相同 prefix 只保留最早 index。

```python
def longest_subarray_sum_k(nums, k):
    first = {0: -1}
    prefix = best = 0
    for i, x in enumerate(nums):
        prefix += x
        if prefix - k in first:
            best = max(best, i - first[prefix - k])
        first.setdefault(prefix, i)
    return best
```

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Subarray Sum Equals K》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：若目前 prefix sum 為 p，需要先前存在 p-k。Map 保存每個 prefix sum 出現次數，而不是只保存是否出現。 失效情境包括：若更新與查詢交錯，靜態 prefix 會因每次更新而失效；若摘要不可結合或不可逆，也無法只靠兩個邊界。
>
> 替代路線是：改用 Fenwick tree、segment tree、ordered prefix states 或 divide-and-conquer；大量離線 query 可考慮排序事件。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存達成最佳 prefix relation 的 index；DP 類 prefix 題保存前驅，區間更新則輸出事件或實際受影響區段。
>
> 套回《Subarray Sum Equals K》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大資料可做分塊 prefix 與 parallel scan；線上更新要明確選 Fenwick/segment tree，並處理版本、快照與 overflow。
>
> 此外必須把《Subarray Sum Equals K》目前隱含的前提寫成 contract：計算總和恰為 k 的連續 subarray 數量；元素可為負數。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Corporate Flight Bookings

### 題目

有 `n` 個航班。每筆預訂 `[first, last, seats]` 表示對整段航班增加座位數，回傳各航班總預訂數。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 有 n 個航班。每筆預訂 [first, last, seats] 表示對整段航班增加座位數，回傳各航班總預訂數。
>
> **核心轉換：** 每筆 range update 只改起點與終點後一格，最後累加 difference array。
>
> **主要知識點：** Prefix Summary、Difference Array 與離線聚合。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Corporate Flight Bookings
      │
      ├─ 暴力路線：對每個 query 或每個區間重新走訪所有元素
      │
      ▼  找出本題最關鍵的轉換
核心觀察：每筆 range update 只改起點與終點後一格，最後累加 difference array。
      │
Pattern toolbox：prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件
      │
      ├─ 狀態轉移：把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原
      │
      ├─ 永遠成立：prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 有 n 個航班。每筆預訂 [first, last, seats] 表示對整段航班增加座位數，回傳各航班總預訂數。
2. **寫出暴力：** 對每個 query 或每個區間重新走訪所有元素。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 每筆 range update 只改起點與終點後一格，最後累加 difference array。
4. **定義 state 與轉移：** 使用「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」承載上述觀察，再執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n + q)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」代表什麼，再說每一步如何「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部」的 base case。
>
> 2. **維持：** 每次執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」後，狀態仍與已處理資料一致。關鍵論證是：由 prefix 定義直接代數化區間公式，證明每個元素的貢獻在進入與離開區間時恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：prefix 長度 n+1、左邊界為 0、負數、整數 overflow、inclusive/exclusive 定義與二維座標偏移。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 推導

每筆 range update 只改起點與終點後一格，最後累加 difference array。

```python
def corp_flight_bookings(bookings, n):
    diff = [0] * (n + 1)
    for first, last, seats in bookings:
        diff[first - 1] += seats
        diff[last] -= seats

    answer = [0] * n
    running = 0
    for i in range(n):
        running += diff[i]
        answer[i] = running
    return answer
```

- 時間：$O(n + q)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：若是 2D 矩形區域更新？**

**答：**2D difference array 對矩形四角做加減；最後先按 row、再按 column 做 prefix sum。概念是 inclusion-exclusion。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Corporate Flight Bookings》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：每筆 range update 只改起點與終點後一格，最後累加 difference array。 失效情境包括：若更新與查詢交錯，靜態 prefix 會因每次更新而失效；若摘要不可結合或不可逆，也無法只靠兩個邊界。
>
> 替代路線是：改用 Fenwick tree、segment tree、ordered prefix states 或 divide-and-conquer；大量離線 query 可考慮排序事件。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存達成最佳 prefix relation 的 index；DP 類 prefix 題保存前驅，區間更新則輸出事件或實際受影響區段。
>
> 套回《Corporate Flight Bookings》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大資料可做分塊 prefix 與 parallel scan；線上更新要明確選 Fenwick/segment tree，並處理版本、快照與 overflow。
>
> 此外必須把《Corporate Flight Bookings》目前隱含的前提寫成 contract：有 n 個航班。每筆預訂 [first, last, seats] 表示對整段航班增加座位數，回傳各航班總預訂數。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Count of Range Sum

### 題目

計算有多少 subarray 的總和落在 `[lower, upper]`。

> [!tip]- 三層提示
> 1. 轉成 prefix sums：需要計算多少 pair `(i,j)` 滿足範圍差。
> 2. 固定左半 prefix，右半符合值會形成排序後的連續區間。
> 3. 在 merge sort 中用兩個 pointer 計數。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 計算有多少 subarray 的總和落在 [lower, upper]。
>
> **核心轉換：** 對 prefix sums 做 divide and conquer。遞迴後左右兩半皆已排序。對每個左半值 x，在右半找：
>
> **主要知識點：** Prefix Summary、Difference Array 與離線聚合。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Count of Range Sum
      │
      ├─ 暴力路線：對每個 query 或每個區間重新走訪所有元素
      │
      ▼  找出本題最關鍵的轉換
核心觀察：對 prefix sums 做 divide and conquer。遞迴後左右兩半皆已排序。對每個左半值 x，在右半找：
      │
Pattern toolbox：prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件
      │
      ├─ 狀態轉移：把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原
      │
      ├─ 永遠成立：prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 計算有多少 subarray 的總和落在 [lower, upper]。
2. **寫出暴力：** 對每個 query 或每個區間重新走訪所有元素。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 對 prefix sums 做 divide and conquer。遞迴後左右兩半皆已排序。對每個左半值 x，在右半找：
4. **定義 state 與轉移：** 使用「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」承載上述觀察，再執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」代表什麼，再說每一步如何「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部」的 base case。
>
> 2. **維持：** 每次執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」後，狀態仍與已處理資料一致。關鍵論證是：由 prefix 定義直接代數化區間公式，證明每個元素的貢獻在進入與離開區間時恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：prefix 長度 n+1、左邊界為 0、負數、整數 overflow、inclusive/exclusive 定義與二維座標偏移。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

對 prefix sums 做 divide and conquer。遞迴後左右兩半皆已排序。對每個左半值 `x`，在右半找：

```text
x + lower <= y <= x + upper
```

由於左半 `x` 遞增，兩個右半 pointer 也只向前走。計數後完成標準 merge。

```python
def count_range_sum(nums, lower, upper):
    prefix = [0]
    for x in nums:
        prefix.append(prefix[-1] + x)

    def sort_count(lo, hi):
        if hi - lo <= 1:
            return 0
        mid = (lo + hi) // 2
        count = sort_count(lo, mid) + sort_count(mid, hi)

        start = end = mid
        for i in range(lo, mid):
            while start < hi and prefix[start] - prefix[i] < lower:
                start += 1
            while end < hi and prefix[end] - prefix[i] <= upper:
                end += 1
            count += end - start

        merged = []
        i, j = lo, mid
        while i < mid and j < hi:
            if prefix[i] <= prefix[j]:
                merged.append(prefix[i])
                i += 1
            else:
                merged.append(prefix[j])
                j += 1
        merged.extend(prefix[i:mid])
        merged.extend(prefix[j:hi])
        prefix[lo:hi] = merged
        return count

    return sort_count(0, len(prefix))
```

**正確性：**每個合法 pair 要嘛完全位於左半、完全位於右半，或跨越兩半。遞迴計算前兩類，兩 pointer 精確計算跨半 pair，因此不漏不重。

- 時間：$O(n\log n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：資料逐筆到達，要在線上查目前 range-sum 數量？**

**答：**需要支援「先前 prefix 中有多少落在 `[p-upper, p-lower]`」的 ordered multiset，可使用 coordinate-compressed Fenwick tree 或 balanced BST。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Count of Range Sum》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：對 prefix sums 做 divide and conquer。遞迴後左右兩半皆已排序。對每個左半值 x，在右半找： 失效情境包括：若更新與查詢交錯，靜態 prefix 會因每次更新而失效；若摘要不可結合或不可逆，也無法只靠兩個邊界。
>
> 替代路線是：改用 Fenwick tree、segment tree、ordered prefix states 或 divide-and-conquer；大量離線 query 可考慮排序事件。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存達成最佳 prefix relation 的 index；DP 類 prefix 題保存前驅，區間更新則輸出事件或實際受影響區段。
>
> 套回《Count of Range Sum》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大資料可做分塊 prefix 與 parallel scan；線上更新要明確選 Fenwick/segment tree，並處理版本、快照與 overflow。
>
> 此外必須把《Count of Range Sum》目前隱含的前提寫成 contract：計算有多少 subarray 的總和落在 [lower, upper]。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Reverse Pairs

### 題目

計算 index pair `i < j` 且 `nums[i] > 2 * nums[j]` 的數量。

> [!tip]- 三層提示
> 1. 與 inversion count 相似。
> 2. 左右兩半排序後，對每個左值找右半第一個不符合的位置。
> 3. 計數與 merge 必須分開處理。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 計算 index pair i < j 且 nums[i] > 2 nums[j] 的數量。
>
> **核心轉換：** 遞迴排序左右半。對每個左值 nums[i]，右 pointer 持續前進，所有已通過的右值都形成 reverse pair。最後 merge。
>
> **主要知識點：** Prefix Summary、Difference Array 與離線聚合。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Reverse Pairs
      │
      ├─ 暴力路線：對每個 query 或每個區間重新走訪所有元素
      │
      ▼  找出本題最關鍵的轉換
核心觀察：遞迴排序左右半。對每個左值 nums[i]，右 pointer 持續前進，所有已通過的右值都形成 reverse pair。最後 merge。
      │
Pattern toolbox：prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件
      │
      ├─ 狀態轉移：把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原
      │
      ├─ 永遠成立：prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 計算 index pair i < j 且 nums[i] > 2 nums[j] 的數量。
2. **寫出暴力：** 對每個 query 或每個區間重新走訪所有元素。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 遞迴排序左右半。對每個左值 nums[i]，右 pointer 持續前進，所有已通過的右值都形成 reverse pair。最後 merge。
4. **定義 state 與轉移：** 使用「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」承載上述觀察，再執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」代表什麼，再說每一步如何「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部」的 base case。
>
> 2. **維持：** 每次執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」後，狀態仍與已處理資料一致。關鍵論證是：由 prefix 定義直接代數化區間公式，證明每個元素的貢獻在進入與離開區間時恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：prefix 長度 n+1、左邊界為 0、負數、整數 overflow、inclusive/exclusive 定義與二維座標偏移。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

遞迴排序左右半。對每個左值 `nums[i]`，右 pointer 持續前進，所有已通過的右值都形成 reverse pair。最後 merge。

```python
def reverse_pairs(nums):
    def sort_count(lo, hi):
        if hi - lo <= 1:
            return 0
        mid = (lo + hi) // 2
        count = sort_count(lo, mid) + sort_count(mid, hi)

        j = mid
        for i in range(lo, mid):
            while j < hi and nums[i] > 2 * nums[j]:
                j += 1
            count += j - mid

        merged = []
        i, j = lo, mid
        while i < mid and j < hi:
            if nums[i] <= nums[j]:
                merged.append(nums[i])
                i += 1
            else:
                merged.append(nums[j])
                j += 1
        merged.extend(nums[i:mid])
        merged.extend(nums[j:hi])
        nums[lo:hi] = merged
        return count

    return sort_count(0, len(nums))
```

- 時間：$O(n\log n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：條件變成 `nums[i] > c * nums[j]`，`c` 是正整數？**

**答：**相同方法仍成立，因為排序後對固定左值，符合條件的右半範圍仍是 prefix；注意固定寬度整數語言的 overflow。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Reverse Pairs》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：遞迴排序左右半。對每個左值 nums[i]，右 pointer 持續前進，所有已通過的右值都形成 reverse pair。最後 merge。 失效情境包括：若更新與查詢交錯，靜態 prefix 會因每次更新而失效；若摘要不可結合或不可逆，也無法只靠兩個邊界。
>
> 替代路線是：改用 Fenwick tree、segment tree、ordered prefix states 或 divide-and-conquer；大量離線 query 可考慮排序事件。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存達成最佳 prefix relation 的 index；DP 類 prefix 題保存前驅，區間更新則輸出事件或實際受影響區段。
>
> 套回《Reverse Pairs》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大資料可做分塊 prefix 與 parallel scan；線上更新要明確選 Fenwick/segment tree，並處理版本、快照與 overflow。
>
> 此外必須把《Reverse Pairs》目前隱含的前提寫成 contract：計算 index pair i < j 且 nums[i] > 2 nums[j] 的數量。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Maximum Sum of 3 Non-Overlapping Subarrays

### 題目

選三段長度皆為 `k`、互不重疊的 subarray，使總和最大；相同總和時回傳 lexicographically smallest 起點。

> [!tip]- 三層提示
> 1. 先算每個長度 `k` window 的和。
> 2. 對每個 middle window，最佳 left 與 right 可以預處理。
> 3. left 遇到相等保留較早；right 反向掃時遇到相等選較早。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 選三段長度皆為 k、互不重疊的 subarray，使總和最大；相同總和時回傳 lexicographically smallest 起點。
>
> **核心轉換：** window[i] 是從 i 開始的長度 k 總和。bestleft[i] 保存 [0..i] 最大 window index；bestright[i] 保存 [i..end] 最大 window index。枚舉 middle 起點即可。
>
> **主要知識點：** Prefix Summary、Difference Array 與離線聚合。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Maximum Sum of 3 Non-Overlapping Subarrays
      │
      ├─ 暴力路線：對每個 query 或每個區間重新走訪所有元素
      │
      ▼  找出本題最關鍵的轉換
核心觀察：window[i] 是從 i 開始的長度 k 總和。bestleft[i] 保存 [0..i] 最大 window index；bestright[i] 保存 [i..end] 最大 window index。枚舉 middle 起點即可。
      │
Pattern toolbox：prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件
      │
      ├─ 狀態轉移：把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原
      │
      ├─ 永遠成立：prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 選三段長度皆為 k、互不重疊的 subarray，使總和最大；相同總和時回傳 lexicographically smallest 起點。
2. **寫出暴力：** 對每個 query 或每個區間重新走訪所有元素。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** window[i] 是從 i 開始的長度 k 總和。bestleft[i] 保存 [0..i] 最大 window index；bestright[i] 保存 [i..end] 最大 window index。枚舉 middle 起點即可。
4. **定義 state 與轉移：** 使用「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」承載上述觀察，再執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」代表什麼，再說每一步如何「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部」的 base case。
>
> 2. **維持：** 每次執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」後，狀態仍與已處理資料一致。關鍵論證是：由 prefix 定義直接代數化區間公式，證明每個元素的貢獻在進入與離開區間時恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：prefix 長度 n+1、左邊界為 0、負數、整數 overflow、inclusive/exclusive 定義與二維座標偏移。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

`window[i]` 是從 `i` 開始的長度 `k` 總和。`best_left[i]` 保存 `[0..i]` 最大 window index；`best_right[i]` 保存 `[i..end]` 最大 window index。枚舉 middle 起點即可。

```python
def max_sum_three_subarrays(nums, k):
    n = len(nums)
    window = []
    total = sum(nums[:k])
    window.append(total)
    for i in range(k, n):
        total += nums[i] - nums[i - k]
        window.append(total)

    m = len(window)
    best_left = [0] * m
    for i in range(1, m):
        if window[i] > window[best_left[i - 1]]:
            best_left[i] = i
        else:
            best_left[i] = best_left[i - 1]

    best_right = [0] * m
    best_right[-1] = m - 1
    for i in range(m - 2, -1, -1):
        if window[i] >= window[best_right[i + 1]]:
            best_right[i] = i
        else:
            best_right[i] = best_right[i + 1]

    answer = None
    best_total = -1
    for mid in range(k, m - k):
        left = best_left[mid - k]
        right = best_right[mid + k]
        current = window[left] + window[mid] + window[right]
        if current > best_total:
            best_total = current
            answer = [left, mid, right]
    return answer
```

- 時間：$O(n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：改成選 `m` 段固定長度區間？**

**答：**使用 DP：`dp[t][i]` 表示前 `i` 個位置選 `t` 段的最佳值，轉移為跳過 `i` 或選以 `i` 結尾的 window；要回傳 lexicographically smallest 解需保存選擇或 parent。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Maximum Sum of 3 Non-Overlapping Subarrays》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：window[i] 是從 i 開始的長度 k 總和。bestleft[i] 保存 [0..i] 最大 window index；bestright[i] 保存 [i..end] 最大 window index。枚舉 middle 起點即可。 失效情境包括：若更新與查詢交錯，靜態 prefix 會因每次更新而失效；若摘要不可結合或不可逆，也無法只靠兩個邊界。
>
> 替代路線是：改用 Fenwick tree、segment tree、ordered prefix states 或 divide-and-conquer；大量離線 query 可考慮排序事件。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存達成最佳 prefix relation 的 index；DP 類 prefix 題保存前驅，區間更新則輸出事件或實際受影響區段。
>
> 套回《Maximum Sum of 3 Non-Overlapping Subarrays》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大資料可做分塊 prefix 與 parallel scan；線上更新要明確選 Fenwick/segment tree，並處理版本、快照與 overflow。
>
> 此外必須把《Maximum Sum of 3 Non-Overlapping Subarrays》目前隱含的前提寫成 contract：選三段長度皆為 k、互不重疊的 subarray，使總和最大；相同總和時回傳 lexicographically smallest 起點。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Number of Submatrices That Sum to Target

### 題目

計算矩陣中總和等於 target 的子矩形數量。

> [!tip]- 三層提示
> 1. 先固定上下邊界。
> 2. 把兩 row 之間每一 column 的總和壓成一維陣列。
> 3. 對一維陣列使用 Subarray Sum Equals K。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 計算矩陣中總和等於 target 的子矩形數量。
>
> **核心轉換：** 枚舉 top，逐步增加 bottom，維護每個 column 在這兩 row 間的總和 compressed。每次把問題降成一維 prefix-sum counting。
>
> **主要知識點：** Prefix Summary、Difference Array 與離線聚合。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Number of Submatrices That Sum to Target
      │
      ├─ 暴力路線：對每個 query 或每個區間重新走訪所有元素
      │
      ▼  找出本題最關鍵的轉換
核心觀察：枚舉 top，逐步增加 bottom，維護每個 column 在這兩 row 間的總和 compressed。每次把問題降成一維 prefix-sum counting。
      │
Pattern toolbox：prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件
      │
      ├─ 狀態轉移：把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原
      │
      ├─ 永遠成立：prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 計算矩陣中總和等於 target 的子矩形數量。
2. **寫出暴力：** 對每個 query 或每個區間重新走訪所有元素。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 枚舉 top，逐步增加 bottom，維護每個 column 在這兩 row 間的總和 compressed。每次把問題降成一維 prefix-sum counting。
4. **定義 state 與轉移：** 使用「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」承載上述觀察，再執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(rows^2 \cdot cols)$；可轉置讓較小維度被平方；空間：$O(cols)$

> [!tip] 一句話記憶
> 先說清楚「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」代表什麼，再說每一步如何「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部」的 base case。
>
> 2. **維持：** 每次執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」後，狀態仍與已處理資料一致。關鍵論證是：由 prefix 定義直接代數化區間公式，證明每個元素的貢獻在進入與離開區間時恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：prefix 長度 n+1、左邊界為 0、負數、整數 overflow、inclusive/exclusive 定義與二維座標偏移。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

枚舉 `top`，逐步增加 `bottom`，維護每個 column 在這兩 row 間的總和 `compressed`。每次把問題降成一維 prefix-sum counting。

```python
from collections import defaultdict

def num_submatrix_sum_target(matrix, target):
    rows, cols = len(matrix), len(matrix[0])
    answer = 0
    for top in range(rows):
        compressed = [0] * cols
        for bottom in range(top, rows):
            for c in range(cols):
                compressed[c] += matrix[bottom][c]

            frequency = defaultdict(int)
            frequency[0] = 1
            prefix = 0
            for x in compressed:
                prefix += x
                answer += frequency[prefix - target]
                frequency[prefix] += 1
    return answer
```

- 時間：$O(rows^2 \cdot cols)$；可轉置讓較小維度被平方
- 空間：$O(cols)$

### Follow-up 1：原題直接變形
**問：矩陣很高但 column 很少？**

**答：**目前做法正合適；若 row 比 column 多很多，可先轉置矩陣，讓平方的是較小維度，複雜度變成 $O(\min(R,C)^2\max(R,C))$。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Number of Submatrices That Sum to Target》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：枚舉 top，逐步增加 bottom，維護每個 column 在這兩 row 間的總和 compressed。每次把問題降成一維 prefix-sum counting。 失效情境包括：若更新與查詢交錯，靜態 prefix 會因每次更新而失效；若摘要不可結合或不可逆，也無法只靠兩個邊界。
>
> 替代路線是：改用 Fenwick tree、segment tree、ordered prefix states 或 divide-and-conquer；大量離線 query 可考慮排序事件。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存達成最佳 prefix relation 的 index；DP 類 prefix 題保存前驅，區間更新則輸出事件或實際受影響區段。
>
> 套回《Number of Submatrices That Sum to Target》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大資料可做分塊 prefix 與 parallel scan；線上更新要明確選 Fenwick/segment tree，並處理版本、快照與 overflow。
>
> 此外必須把《Number of Submatrices That Sum to Target》目前隱含的前提寫成 contract：計算矩陣中總和等於 target 的子矩形數量。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Shortest Subarray with Sum at Least K

### 題目

陣列可含負數，求總和至少 `k` 的最短非空 subarray。

> [!tip]- 三層提示
> 1. 需要找最小 `j-i`，使 `prefix[j]-prefix[i] >= k`。
> 2. 若較晚的 prefix 不大於較早 prefix，較早者永遠不會更好。
> 3. 維護 prefix 值遞增的 deque。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 陣列可含負數，求總和至少 k 的最短非空 subarray。
>
> **核心轉換：** 對每個 j：
>
> **主要知識點：** Prefix Summary、Difference Array 與離線聚合。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Shortest Subarray with Sum at Least K
      │
      ├─ 暴力路線：對每個 query 或每個區間重新走訪所有元素
      │
      ▼  找出本題最關鍵的轉換
核心觀察：對每個 j：
      │
Pattern toolbox：prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件
      │
      ├─ 狀態轉移：把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原
      │
      ├─ 永遠成立：prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 陣列可含負數，求總和至少 k 的最短非空 subarray。
2. **寫出暴力：** 對每個 query 或每個區間重新走訪所有元素。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 對每個 j：
4. **定義 state 與轉移：** 使用「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」承載上述觀察，再執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「prefix[i] 表示前 i 個元素的摘要；或 difference 只記錄區間更新的邊界事件」代表什麼，再說每一步如何「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「prefix 精確代表某個固定前綴；任意區間只依賴兩個邊界狀態，不再重掃內部」的 base case。
>
> 2. **維持：** 每次執行「把區間問題改寫成兩個 prefix 的關係，或先標記差分、最後一次累積還原」後，狀態仍與已處理資料一致。關鍵論證是：由 prefix 定義直接代數化區間公式，證明每個元素的貢獻在進入與離開區間時恰被計算一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：prefix 長度 n+1、左邊界為 0、負數、整數 overflow、inclusive/exclusive 定義與二維座標偏移。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

對每個 `j`：

1. 若 deque 頭與 `j` 已形成合法區間，持續彈頭以取得更短答案。
2. 若 deque 尾的 prefix 不小於目前 prefix，彈尾；目前 index 更晚且 prefix 更小，未來一定更優。

```python
from collections import deque

def shortest_subarray(nums, k):
    prefix = [0]
    for x in nums:
        prefix.append(prefix[-1] + x)

    q = deque()
    answer = len(nums) + 1
    for j, value in enumerate(prefix):
        while q and value - prefix[q[0]] >= k:
            answer = min(answer, j - q.popleft())
        while q and prefix[q[-1]] >= value:
            q.pop()
        q.append(j)
    return -1 if answer == len(nums) + 1 else answer
```

- 時間：$O(n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：只含正數時應使用哪個解法？**

**答：**一般 sliding window 更簡單，空間 $O(1)$。Monotonic deque 是為了解決負數使 prefix 不再單調的情況。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Shortest Subarray with Sum at Least K》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：對每個 j： 失效情境包括：若更新與查詢交錯，靜態 prefix 會因每次更新而失效；若摘要不可結合或不可逆，也無法只靠兩個邊界。
>
> 替代路線是：改用 Fenwick tree、segment tree、ordered prefix states 或 divide-and-conquer；大量離線 query 可考慮排序事件。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存達成最佳 prefix relation 的 index；DP 類 prefix 題保存前驅，區間更新則輸出事件或實際受影響區段。
>
> 套回《Shortest Subarray with Sum at Least K》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 大資料可做分塊 prefix 與 parallel scan；線上更新要明確選 Fenwick/segment tree，並處理版本、快照與 overflow。
>
> 此外必須把《Shortest Subarray with Sum at Least K》目前隱含的前提寫成 contract：陣列可含負數，求總和至少 k 的最短非空 subarray。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 能從 subarray 問題寫出 prefix pair 關係。
- [ ] 知道 count 要保存頻率、max length 要保存最早位置。
- [ ] 能用 difference array 處理大量 range update。
- [ ] 會辨認 merge-sort counting 與 monotonic prefix。
