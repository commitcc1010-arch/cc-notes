---
title: Binary Search
tags:
  - coding-interview/pattern
  - binary-search
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 05 — Binary Search

[[04 - Prefix Sum and Difference Array|← 上一章]] · [[00 - Book Index|目錄]] · [[06 - Sorting Intervals and Sweep Line|下一章 →]]

> [!abstract] Mental model
> Binary search 的本質是尋找單調 predicate 的邊界。資料不一定是陣列；只要「答案 `x` 是否可行」從某點開始永遠為真或永遠為假，就能搜尋答案空間。

## 統一模板：第一個 True

```python
def first_true(lo, hi, feasible):
    while lo < hi:
        mid = (lo + hi) // 2
        if feasible(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo
```

---

## 核心題 1：Find First and Last Position

### 題目

在排序陣列中找 target 的第一與最後位置，不存在回傳 `[-1,-1]`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 在排序陣列中找 target 的第一與最後位置，不存在回傳 [-1,-1]。
>
> **核心轉換：** 分別找第一個 >= target 的位置與第一個 > target 的位置；答案是 left 與 right-1，而不是命中後向兩側線性掃描。
>
> **主要知識點：** Binary Search on Boundary／Answer。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Find First and Last Position
      │
      ├─ 暴力路線：逐一測試每個 index 或答案值，直到找到第一個可行者
      │
      ▼  找出本題最關鍵的轉換
核心觀察：分別找第一個 >= target 的位置與第一個 > target 的位置；答案是 left 與 right-1，而不是命中後向兩側線性掃描。
      │
Pattern toolbox：一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF
      │
      ├─ 狀態轉移：測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍
      │
      ├─ 永遠成立：真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 在排序陣列中找 target 的第一與最後位置，不存在回傳 [-1,-1]。
2. **寫出暴力：** 逐一測試每個 index 或答案值，直到找到第一個可行者。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 分別找第一個 >= target 的位置與第一個 > target 的位置；答案是 left 與 right-1，而不是命中後向兩側線性掃描。
4. **定義 state 與轉移：** 使用「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」承載上述觀察，再執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」代表什麼，再說每一步如何「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False」的 base case。
>
> 2. **維持：** 每次執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」後，狀態仍與已處理資料一致。關鍵論證是：先證明 predicate 單調，再證明 lo/hi 更新不排除答案，最後用區間嚴格縮小證明終止。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空陣列、重複值、off-by-one、mid overflow、不可行答案、負數除法與浮點精度。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
from bisect import bisect_left, bisect_right

def search_range(nums, target):
    left = bisect_left(nums, target)
    if left == len(nums) or nums[left] != target:
        return [-1, -1]
    return [left, bisect_right(nums, target) - 1]
```

### Follow-up 1：原題直接變形
**問：不用 library 如何寫 `lower_bound`？**

```python
def lower_bound(nums, target):
    lo, hi = 0, len(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] >= target:
            hi = mid
        else:
            lo = mid + 1
    return lo
```

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Find First and Last Position》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：分別找第一個 >= target 的位置與第一個 > target 的位置；答案是 left 與 right-1，而不是命中後向兩側線性掃描。 失效情境包括：若 feasible(x) 不單調，binary search 即使程式終止也沒有語意保證；若一次 predicate 太貴，總複雜度也可能超標。
>
> 替代路線是：改用 DP、parametric search 的更快判定器、selection algorithm 或直接掃描；浮點題可固定迭代次數。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：找到邊界後再跑一次 constrained reconstruction；partition 題保存 cut，路徑題在 predicate 中保存 parent 或第二階段重建。
>
> 套回《Find First and Last Position》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production API 要明確定義精度、上下界與 predicate timeout；昂貴 predicate 可 cache，但 cache key 必須包含所有限制。
>
> 此外必須把《Find First and Last Position》目前隱含的前提寫成 contract：在排序陣列中找 target 的第一與最後位置，不存在回傳 [-1,-1]。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Search in Rotated Sorted Array

### 題目

嚴格遞增陣列旋轉後，找 target index。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 嚴格遞增陣列旋轉後，找 target index。
>
> **核心轉換：** 每次至少有一半仍排序。先判斷哪一半有序，再判斷 target 是否位於其值域。
>
> **主要知識點：** Binary Search on Boundary／Answer。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Search in Rotated Sorted Array
      │
      ├─ 暴力路線：逐一測試每個 index 或答案值，直到找到第一個可行者
      │
      ▼  找出本題最關鍵的轉換
核心觀察：每次至少有一半仍排序。先判斷哪一半有序，再判斷 target 是否位於其值域。
      │
Pattern toolbox：一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF
      │
      ├─ 狀態轉移：測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍
      │
      ├─ 永遠成立：真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 嚴格遞增陣列旋轉後，找 target index。
2. **寫出暴力：** 逐一測試每個 index 或答案值，直到找到第一個可行者。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 每次至少有一半仍排序。先判斷哪一半有序，再判斷 target 是否位於其值域。
4. **定義 state 與轉移：** 使用「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」承載上述觀察，再執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」代表什麼，再說每一步如何「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False」的 base case。
>
> 2. **維持：** 每次執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」後，狀態仍與已處理資料一致。關鍵論證是：先證明 predicate 單調，再證明 lo/hi 更新不排除答案，最後用區間嚴格縮小證明終止。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空陣列、重複值、off-by-one、mid overflow、不可行答案、負數除法與浮點精度。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 推導

每次至少有一半仍排序。先判斷哪一半有序，再判斷 target 是否位於其值域。

```python
def search_rotated(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[lo] <= nums[mid]:
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1
```

### Follow-up 1：原題直接變形
**問：允許重複值？**

**答：**當 `nums[lo] == nums[mid] == nums[hi]` 時無法判斷有序側，只能 `lo += 1; hi -= 1`。Worst case 退化為 $O(n)$。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Search in Rotated Sorted Array》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：每次至少有一半仍排序。先判斷哪一半有序，再判斷 target 是否位於其值域。 失效情境包括：若 feasible(x) 不單調，binary search 即使程式終止也沒有語意保證；若一次 predicate 太貴，總複雜度也可能超標。
>
> 替代路線是：改用 DP、parametric search 的更快判定器、selection algorithm 或直接掃描；浮點題可固定迭代次數。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：找到邊界後再跑一次 constrained reconstruction；partition 題保存 cut，路徑題在 predicate 中保存 parent 或第二階段重建。
>
> 套回《Search in Rotated Sorted Array》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production API 要明確定義精度、上下界與 predicate timeout；昂貴 predicate 可 cache，但 cache key 必須包含所有限制。
>
> 此外必須把《Search in Rotated Sorted Array》目前隱含的前提寫成 contract：嚴格遞增陣列旋轉後，找 target index。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Koko Eating Bananas

### 題目

有多堆香蕉，速度 `k` 表示每小時從一堆吃最多 `k` 根。求在 `h` 小時內吃完的最小整數速度。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 有多堆香蕉，速度 k 表示每小時從一堆吃最多 k 根。求在 h 小時內吃完的最小整數速度。
>
> **核心轉換：** 速度越大，所需時數單調不增；以 feasible(k)=總時數<=h 搜尋第一個 True，範圍為 1 到最大 pile。
>
> **主要知識點：** Binary Search on Boundary／Answer。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Koko Eating Bananas
      │
      ├─ 暴力路線：逐一測試每個 index 或答案值，直到找到第一個可行者
      │
      ▼  找出本題最關鍵的轉換
核心觀察：速度越大，所需時數單調不增；以 feasible(k)=總時數<=h 搜尋第一個 True，範圍為 1 到最大 pile。
      │
Pattern toolbox：一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF
      │
      ├─ 狀態轉移：測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍
      │
      ├─ 永遠成立：真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 有多堆香蕉，速度 k 表示每小時從一堆吃最多 k 根。求在 h 小時內吃完的最小整數速度。
2. **寫出暴力：** 逐一測試每個 index 或答案值，直到找到第一個可行者。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 速度越大，所需時數單調不增；以 feasible(k)=總時數<=h 搜尋第一個 True，範圍為 1 到最大 pile。
4. **定義 state 與轉移：** 使用「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」承載上述觀察，再執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」代表什麼，再說每一步如何「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False」的 base case。
>
> 2. **維持：** 每次執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」後，狀態仍與已處理資料一致。關鍵論證是：先證明 predicate 單調，再證明 lo/hi 更新不排除答案，最後用區間嚴格縮小證明終止。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空陣列、重複值、off-by-one、mid overflow、不可行答案、負數除法與浮點精度。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def min_eating_speed(piles, h):
    def feasible(speed):
        return sum((pile + speed - 1) // speed for pile in piles) <= h

    lo, hi = 1, max(piles)
    while lo < hi:
        mid = (lo + hi) // 2
        if feasible(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo
```

**Invariant：**答案始終位於 `[lo, hi]`；`feasible(speed)` 對 speed 單調。

### Follow-up 1：原題直接變形
**問：如何避免 `sum` 很早已超過 `h` 卻繼續計算？**

**答：**在 `feasible` 中逐堆累加，一旦 hours 超過 `h` 立即回傳 `False`。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Koko Eating Bananas》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：速度越大，所需時數單調不增；以 feasible(k)=總時數<=h 搜尋第一個 True，範圍為 1 到最大 pile。 失效情境包括：若 feasible(x) 不單調，binary search 即使程式終止也沒有語意保證；若一次 predicate 太貴，總複雜度也可能超標。
>
> 替代路線是：改用 DP、parametric search 的更快判定器、selection algorithm 或直接掃描；浮點題可固定迭代次數。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：找到邊界後再跑一次 constrained reconstruction；partition 題保存 cut，路徑題在 predicate 中保存 parent 或第二階段重建。
>
> 套回《Koko Eating Bananas》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production API 要明確定義精度、上下界與 predicate timeout；昂貴 predicate 可 cache，但 cache key 必須包含所有限制。
>
> 此外必須把《Koko Eating Bananas》目前隱含的前提寫成 contract：有多堆香蕉，速度 k 表示每小時從一堆吃最多 k 根。求在 h 小時內吃完的最小整數速度。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Median of Two Sorted Arrays

### 題目

在 $O(\log(m+n))$ 時間內找兩個排序陣列合併後的 median。

> [!tip]- 三層提示
> 1. 不要真的 merge；在較短陣列選切點。
> 2. 左半總元素數固定。
> 3. 正確 partition 需滿足 `Aleft <= Bright` 且 `Bleft <= Aright`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 在 $O(\log(m+n))$ 時間內找兩個排序陣列合併後的 median。
>
> **核心轉換：** 在短陣列 a 選左半元素數 i，另一陣列左半數量便是 j = half-i。若 a[i-1] > b[j]，i 太大；若 b[j-1] > a[i]，i 太小。
>
> **主要知識點：** Binary Search on Boundary／Answer。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Median of Two Sorted Arrays
      │
      ├─ 暴力路線：逐一測試每個 index 或答案值，直到找到第一個可行者
      │
      ▼  找出本題最關鍵的轉換
核心觀察：在短陣列 a 選左半元素數 i，另一陣列左半數量便是 j = half-i。若 a[i-1] > b[j]，i 太大；若 b[j-1] > a[i]，i 太小。
      │
Pattern toolbox：一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF
      │
      ├─ 狀態轉移：測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍
      │
      ├─ 永遠成立：真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 在 $O(\log(m+n))$ 時間內找兩個排序陣列合併後的 median。
2. **寫出暴力：** 逐一測試每個 index 或答案值，直到找到第一個可行者。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 在短陣列 a 選左半元素數 i，另一陣列左半數量便是 j = half-i。若 a[i-1] > b[j]，i 太大；若 b[j-1] > a[i]，i 太小。
4. **定義 state 與轉移：** 使用「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」承載上述觀察，再執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(\log\min(m,n))$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」代表什麼，再說每一步如何「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False」的 base case。
>
> 2. **維持：** 每次執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」後，狀態仍與已處理資料一致。關鍵論證是：先證明 predicate 單調，再證明 lo/hi 更新不排除答案，最後用區間嚴格縮小證明終止。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空陣列、重複值、off-by-one、mid overflow、不可行答案、負數除法與浮點精度。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

在短陣列 `a` 選左半元素數 `i`，另一陣列左半數量便是 `j = half-i`。若 `a[i-1] > b[j]`，`i` 太大；若 `b[j-1] > a[i]`，`i` 太小。

```python
def find_median_sorted_arrays(a, b):
    if len(a) > len(b):
        a, b = b, a
    m, n = len(a), len(b)
    half = (m + n + 1) // 2
    lo, hi = 0, m

    while lo <= hi:
        i = (lo + hi) // 2
        j = half - i
        a_left = float("-inf") if i == 0 else a[i - 1]
        a_right = float("inf") if i == m else a[i]
        b_left = float("-inf") if j == 0 else b[j - 1]
        b_right = float("inf") if j == n else b[j]

        if a_left <= b_right and b_left <= a_right:
            if (m + n) % 2:
                return max(a_left, b_left)
            return (max(a_left, b_left) + min(a_right, b_right)) / 2
        if a_left > b_right:
            hi = i - 1
        else:
            lo = i + 1
```

- 時間：$O(\log\min(m,n))$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：改求合併後第 `k` 小元素？**

**答：**令左半大小為 `k` 而非 `(m+n+1)//2`，搜尋 `i` 的合法範圍 `max(0,k-n)..min(k,m)`；合法 partition 的左半最大值即答案。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Median of Two Sorted Arrays》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：在短陣列 a 選左半元素數 i，另一陣列左半數量便是 j = half-i。若 a[i-1] > b[j]，i 太大；若 b[j-1] > a[i]，i 太小。 失效情境包括：若 feasible(x) 不單調，binary search 即使程式終止也沒有語意保證；若一次 predicate 太貴，總複雜度也可能超標。
>
> 替代路線是：改用 DP、parametric search 的更快判定器、selection algorithm 或直接掃描；浮點題可固定迭代次數。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：找到邊界後再跑一次 constrained reconstruction；partition 題保存 cut，路徑題在 predicate 中保存 parent 或第二階段重建。
>
> 套回《Median of Two Sorted Arrays》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production API 要明確定義精度、上下界與 predicate timeout；昂貴 predicate 可 cache，但 cache key 必須包含所有限制。
>
> 此外必須把《Median of Two Sorted Arrays》目前隱含的前提寫成 contract：在 $O(\log(m+n))$ 時間內找兩個排序陣列合併後的 median。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Split Array Largest Sum

### 題目

將非負陣列切成恰 `m` 個非空連續區間，使各區間和的最大值最小。

> [!tip]- 三層提示
> 1. 猜一個最大允許和 `limit`。
> 2. Greedy 計算在該 limit 下最少需要幾段。
> 3. `limit` 越大，需要的段數不會增加。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 將非負陣列切成恰 m 個非空連續區間，使各區間和的最大值最小。
>
> **核心轉換：** 答案介於最大單一元素與全部總和。對 limit，由左至右盡量填滿一段可得到最少段數；若最少段數不超過 m，就能再切細成恰 m 段。
>
> **主要知識點：** Binary Search on Boundary／Answer。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Split Array Largest Sum
      │
      ├─ 暴力路線：逐一測試每個 index 或答案值，直到找到第一個可行者
      │
      ▼  找出本題最關鍵的轉換
核心觀察：答案介於最大單一元素與全部總和。對 limit，由左至右盡量填滿一段可得到最少段數；若最少段數不超過 m，就能再切細成恰 m 段。
      │
Pattern toolbox：一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF
      │
      ├─ 狀態轉移：測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍
      │
      ├─ 永遠成立：真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 將非負陣列切成恰 m 個非空連續區間，使各區間和的最大值最小。
2. **寫出暴力：** 逐一測試每個 index 或答案值，直到找到第一個可行者。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 答案介於最大單一元素與全部總和。對 limit，由左至右盡量填滿一段可得到最少段數；若最少段數不超過 m，就能再切細成恰 m 段。
4. **定義 state 與轉移：** 使用「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」承載上述觀察，再執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log \sum nums)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」代表什麼，再說每一步如何「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False」的 base case。
>
> 2. **維持：** 每次執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」後，狀態仍與已處理資料一致。關鍵論證是：先證明 predicate 單調，再證明 lo/hi 更新不排除答案，最後用區間嚴格縮小證明終止。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空陣列、重複值、off-by-one、mid overflow、不可行答案、負數除法與浮點精度。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

答案介於最大單一元素與全部總和。對 `limit`，由左至右盡量填滿一段可得到最少段數；若最少段數不超過 `m`，就能再切細成恰 `m` 段。

```python
def split_array(nums, m):
    def feasible(limit):
        groups = 1
        current = 0
        for x in nums:
            if current + x > limit:
                groups += 1
                current = x
            else:
                current += x
        return groups <= m

    lo, hi = max(nums), sum(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if feasible(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo
```

- 時間：$O(n\log \sum nums)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：元素可為負數？**

**答：**greedy feasibility 不再正確，因為先超過 limit 的區段可能靠後續負數降回來；需改用 DP，binary-search predicate 也必須重新證明。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Split Array Largest Sum》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：答案介於最大單一元素與全部總和。對 limit，由左至右盡量填滿一段可得到最少段數；若最少段數不超過 m，就能再切細成恰 m 段。 失效情境包括：若 feasible(x) 不單調，binary search 即使程式終止也沒有語意保證；若一次 predicate 太貴，總複雜度也可能超標。
>
> 替代路線是：改用 DP、parametric search 的更快判定器、selection algorithm 或直接掃描；浮點題可固定迭代次數。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：找到邊界後再跑一次 constrained reconstruction；partition 題保存 cut，路徑題在 predicate 中保存 parent 或第二階段重建。
>
> 套回《Split Array Largest Sum》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production API 要明確定義精度、上下界與 predicate timeout；昂貴 predicate 可 cache，但 cache key 必須包含所有限制。
>
> 此外必須把《Split Array Largest Sum》目前隱含的前提寫成 contract：將非負陣列切成恰 m 個非空連續區間，使各區間和的最大值最小。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Find K-th Smallest Pair Distance

### 題目

所有 index pair 的距離定義為 `abs(nums[i]-nums[j])`，求第 `k` 小距離。

> [!tip]- 三層提示
> 1. 排序後 binary search 距離 `d`。
> 2. 計算距離不超過 `d` 的 pair 數量。
> 3. 用 sliding left pointer 在 $O(n)$ 完成計數。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 所有 index pair 的距離定義為 abs(nums[i]-nums[j])，求第 k 小距離。
>
> **核心轉換：** 排序後，對每個 right，移動 left 直到 nums[right]-nums[left] <= d；以 right 結尾有 right-left 個合法 pair。Pair 數量對 d 單調。
>
> **主要知識點：** Binary Search on Boundary／Answer。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Find K-th Smallest Pair Distance
      │
      ├─ 暴力路線：逐一測試每個 index 或答案值，直到找到第一個可行者
      │
      ▼  找出本題最關鍵的轉換
核心觀察：排序後，對每個 right，移動 left 直到 nums[right]-nums[left] <= d；以 right 結尾有 right-left 個合法 pair。Pair 數量對 d 單調。
      │
Pattern toolbox：一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF
      │
      ├─ 狀態轉移：測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍
      │
      ├─ 永遠成立：真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 所有 index pair 的距離定義為 abs(nums[i]-nums[j])，求第 k 小距離。
2. **寫出暴力：** 逐一測試每個 index 或答案值，直到找到第一個可行者。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 排序後，對每個 right，移動 left 直到 nums[right]-nums[left] <= d；以 right 結尾有 right-left 個合法 pair。Pair 數量對 d 單調。
4. **定義 state 與轉移：** 使用「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」承載上述觀察，再執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log n+n\log W)$；空間：排序空間

> [!tip] 一句話記憶
> 先說清楚「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」代表什麼，再說每一步如何「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False」的 base case。
>
> 2. **維持：** 每次執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」後，狀態仍與已處理資料一致。關鍵論證是：先證明 predicate 單調，再證明 lo/hi 更新不排除答案，最後用區間嚴格縮小證明終止。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空陣列、重複值、off-by-one、mid overflow、不可行答案、負數除法與浮點精度。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

排序後，對每個 `right`，移動 `left` 直到 `nums[right]-nums[left] <= d`；以 `right` 結尾有 `right-left` 個合法 pair。Pair 數量對 `d` 單調。

```python
def smallest_distance_pair(nums, k):
    nums.sort()

    def count_at_most(distance):
        count = left = 0
        for right in range(len(nums)):
            while nums[right] - nums[left] > distance:
                left += 1
            count += right - left
        return count

    lo, hi = 0, nums[-1] - nums[0]
    while lo < hi:
        mid = (lo + hi) // 2
        if count_at_most(mid) >= k:
            hi = mid
        else:
            lo = mid + 1
    return lo
```

- 時間：$O(n\log n+n\log W)$
- 空間：排序空間

### Follow-up 1：原題直接變形
**問：為什麼找的是第一個 `count >= k` 的距離？**

**答：**距離 `d` 若已有至少 `k` 個 pair 不大於它，則第 `k` 小值不會大於 `d`；第一個滿足者正是第 `k` 小距離。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Find K-th Smallest Pair Distance》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：排序後，對每個 right，移動 left 直到 nums[right]-nums[left] <= d；以 right 結尾有 right-left 個合法 pair。Pair 數量對 d 單調。 失效情境包括：若 feasible(x) 不單調，binary search 即使程式終止也沒有語意保證；若一次 predicate 太貴，總複雜度也可能超標。
>
> 替代路線是：改用 DP、parametric search 的更快判定器、selection algorithm 或直接掃描；浮點題可固定迭代次數。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：找到邊界後再跑一次 constrained reconstruction；partition 題保存 cut，路徑題在 predicate 中保存 parent 或第二階段重建。
>
> 套回《Find K-th Smallest Pair Distance》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production API 要明確定義精度、上下界與 predicate timeout；昂貴 predicate 可 cache，但 cache key 必須包含所有限制。
>
> 此外必須把《Find K-th Smallest Pair Distance》目前隱含的前提寫成 contract：所有 index pair 的距離定義為 abs(nums[i]-nums[j])，求第 k 小距離。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：K-th Smallest Product of Two Sorted Arrays

### 題目

兩個排序整數陣列可含負數與零。所有跨陣列 pair product 中，求第 `k` 小值。

> [!tip]- 三層提示
> 1. Binary search product `x`，計算有多少 product `<= x`。
> 2. 固定 `a`：若 `a>0`，在 `b` 中找 `b<=x/a`。
> 3. 若 `a<0`，不等號反向，要找 `b>=ceil(x/a)`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 兩個排序整數陣列可含負數與零。所有跨陣列 pair product 中，求第 k 小值。
>
> **核心轉換：** Product 的搜尋範圍由四個端點乘積決定。countle(x) 對每個 a 用 binary search 計算符合的 b 數量。
>
> **主要知識點：** Binary Search on Boundary／Answer。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：K-th Smallest Product of Two Sorted Arrays
      │
      ├─ 暴力路線：逐一測試每個 index 或答案值，直到找到第一個可行者
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Product 的搜尋範圍由四個端點乘積決定。countle(x) 對每個 a 用 binary search 計算符合的 b 數量。
      │
Pattern toolbox：一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF
      │
      ├─ 狀態轉移：測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍
      │
      ├─ 永遠成立：真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 兩個排序整數陣列可含負數與零。所有跨陣列 pair product 中，求第 k 小值。
2. **寫出暴力：** 逐一測試每個 index 或答案值，直到找到第一個可行者。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Product 的搜尋範圍由四個端點乘積決定。countle(x) 對每個 a 用 binary search 計算符合的 b 數量。
4. **定義 state 與轉移：** 使用「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」承載上述觀察，再執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log m\log W)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」代表什麼，再說每一步如何「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False」的 base case。
>
> 2. **維持：** 每次執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」後，狀態仍與已處理資料一致。關鍵論證是：先證明 predicate 單調，再證明 lo/hi 更新不排除答案，最後用區間嚴格縮小證明終止。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空陣列、重複值、off-by-one、mid overflow、不可行答案、負數除法與浮點精度。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Product 的搜尋範圍由四個端點乘積決定。`count_le(x)` 對每個 `a` 用 binary search 計算符合的 `b` 數量。

```python
from bisect import bisect_left, bisect_right

def kth_smallest_product(nums1, nums2, k):
    products = [
        nums1[0] * nums2[0],
        nums1[0] * nums2[-1],
        nums1[-1] * nums2[0],
        nums1[-1] * nums2[-1],
    ]

    def ceil_div(x, y):
        return -((-x) // y)

    def count_le(limit):
        count = 0
        for a in nums1:
            if a > 0:
                count += bisect_right(nums2, limit // a)
            elif a == 0:
                if limit >= 0:
                    count += len(nums2)
            else:
                threshold = ceil_div(limit, a)
                count += len(nums2) - bisect_left(nums2, threshold)
        return count

    lo, hi = min(products), max(products)
    while lo < hi:
        mid = (lo + hi) // 2
        if count_le(mid) >= k:
            hi = mid
        else:
            lo = mid + 1
    return lo
```

- 時間：$O(n\log m\log W)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：如何降低每次 `count_le` 的複雜度？**

**答：**按正、零、負拆分陣列後，可利用 two pointers 對同號與異號乘積做線性計數，把單次檢查改善到 $O(n+m)$，但實作與邊界更複雜。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《K-th Smallest Product of Two Sorted Arrays》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Product 的搜尋範圍由四個端點乘積決定。countle(x) 對每個 a 用 binary search 計算符合的 b 數量。 失效情境包括：若 feasible(x) 不單調，binary search 即使程式終止也沒有語意保證；若一次 predicate 太貴，總複雜度也可能超標。
>
> 替代路線是：改用 DP、parametric search 的更快判定器、selection algorithm 或直接掃描；浮點題可固定迭代次數。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：找到邊界後再跑一次 constrained reconstruction；partition 題保存 cut，路徑題在 predicate 中保存 parent 或第二階段重建。
>
> 套回《K-th Smallest Product of Two Sorted Arrays》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production API 要明確定義精度、上下界與 predicate timeout；昂貴 predicate 可 cache，但 cache key 必須包含所有限制。
>
> 此外必須把《K-th Smallest Product of Two Sorted Arrays》目前隱含的前提寫成 contract：兩個排序整數陣列可含負數與零。所有跨陣列 pair product 中，求第 k 小值。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Minimize Max Distance to Gas Station

### 題目

在排序座標間新增 `k` 個加油站，使任意相鄰站最大距離最小，回傳誤差容許範圍內的答案。

> [!tip]- 三層提示
> 1. 答案是實數，但「最大距離至多 `d` 是否可行」仍單調。
> 2. 長度 `gap` 要切成每段不超過 `d`，需要多少新站？
> 3. 數量是 `ceil(gap/d)-1`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 在排序座標間新增 k 個加油站，使任意相鄰站最大距離最小，回傳誤差容許範圍內的答案。
>
> **核心轉換：** Binary search 浮點答案。固定最大間距 d，加總每個 gap 所需新站；不超過 k 即可行。固定迭代 60–80 次可避免浮點停止條件問題。
>
> **主要知識點：** Binary Search on Boundary／Answer。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Minimize Max Distance to Gas Station
      │
      ├─ 暴力路線：逐一測試每個 index 或答案值，直到找到第一個可行者
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Binary search 浮點答案。固定最大間距 d，加總每個 gap 所需新站；不超過 k 即可行。固定迭代 60–80 次可避免浮點停止條件問題。
      │
Pattern toolbox：一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF
      │
      ├─ 狀態轉移：測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍
      │
      ├─ 永遠成立：真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 在排序座標間新增 k 個加油站，使任意相鄰站最大距離最小，回傳誤差容許範圍內的答案。
2. **寫出暴力：** 逐一測試每個 index 或答案值，直到找到第一個可行者。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Binary search 浮點答案。固定最大間距 d，加總每個 gap 所需新站；不超過 k 即可行。固定迭代 60–80 次可避免浮點停止條件問題。
4. **定義 state 與轉移：** 使用「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」承載上述觀察，再執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log(\text{precision}^{-1}))$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「一段答案空間加上 monotonic predicate：FFFFFTTT 或 TTTTTFFFFF」代表什麼，再說每一步如何「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「真正答案始終位於目前 [lo, hi]；每次更新後區間仍包含第一個 True 或最後一個 False」的 base case。
>
> 2. **維持：** 每次執行「測試 mid，根據 predicate 丟棄一整半不可能包含邊界的範圍」後，狀態仍與已處理資料一致。關鍵論證是：先證明 predicate 單調，再證明 lo/hi 更新不排除答案，最後用區間嚴格縮小證明終止。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空陣列、重複值、off-by-one、mid overflow、不可行答案、負數除法與浮點精度。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Binary search 浮點答案。固定最大間距 `d`，加總每個 gap 所需新站；不超過 `k` 即可行。固定迭代 60–80 次可避免浮點停止條件問題。

```python
import math

def minmax_gas_dist(stations, k):
    def needed(distance):
        total = 0
        for a, b in zip(stations, stations[1:]):
            total += math.ceil((b - a) / distance) - 1
        return total

    lo = 0.0
    hi = max(b - a for a, b in zip(stations, stations[1:]))
    for _ in range(70):
        mid = (lo + hi) / 2
        if needed(mid) <= k:
            hi = mid
        else:
            lo = mid
    return hi
```

- 時間：$O(n\log(\text{precision}^{-1}))$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：若 `k` 很小，還有什麼方法？**

**答：**用 max heap 保存每個原始 gap 在目前分段數下的最大子段長度，每次把新站放進當前最大 gap。時間約 $O((n+k)\log n)$，適合小 `k`，但浮點 tie 與證明需更小心。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Minimize Max Distance to Gas Station》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Binary search 浮點答案。固定最大間距 d，加總每個 gap 所需新站；不超過 k 即可行。固定迭代 60–80 次可避免浮點停止條件問題。 失效情境包括：若 feasible(x) 不單調，binary search 即使程式終止也沒有語意保證；若一次 predicate 太貴，總複雜度也可能超標。
>
> 替代路線是：改用 DP、parametric search 的更快判定器、selection algorithm 或直接掃描；浮點題可固定迭代次數。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：找到邊界後再跑一次 constrained reconstruction；partition 題保存 cut，路徑題在 predicate 中保存 parent 或第二階段重建。
>
> 套回《Minimize Max Distance to Gas Station》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production API 要明確定義精度、上下界與 predicate timeout；昂貴 predicate 可 cache，但 cache key 必須包含所有限制。
>
> 此外必須把《Minimize Max Distance to Gas Station》目前隱含的前提寫成 contract：在排序座標間新增 k 個加油站，使任意相鄰站最大距離最小，回傳誤差容許範圍內的答案。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 能先寫出 monotonic predicate。
- [ ] 會區分搜尋 index 與搜尋 answer。
- [ ] 能處理 first true / last false 邊界。
- [ ] 遇到負數、重複值、浮點時會重新檢查 predicate。
