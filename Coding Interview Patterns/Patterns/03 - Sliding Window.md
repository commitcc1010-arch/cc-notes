---
title: Sliding Window
tags:
  - coding-interview/pattern
  - sliding-window
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 03 — Sliding Window

[[02 - Two Pointers|← 上一章]] · [[00 - Book Index|目錄]] · [[04 - Prefix Sum and Difference Array|下一章 →]]

> [!abstract] Mental model
> Window 適合連續區間，且加入右端、移除左端後，合法性或分數可以增量更新。核心不是模板，而是定義「何時合法」以及左端應移動到哪裡。

## 三種模板

1. 固定長度：每次加入一個、移除一個。
2. 最長合法 window：右端擴張，不合法時縮左端。
3. 最短滿足 window：擴張到滿足，再盡量縮小。

---

## 核心題 1：Longest Substring Without Repeating Characters

### 題目

求沒有重複字元的最長 substring 長度。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 求沒有重複字元的最長 substring 長度。
>
> **核心轉換：** 用 last_seen 記錄字元最新位置；right 前進時，left 直接跳到重複字元上次位置的下一格，但不能後退。
>
> **主要知識點：** Sliding Window 與可逆的區間狀態。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Longest Substring Without Repeating Characters
      │
      ├─ 暴力路線：枚舉所有連續區間，並對每個區間重新計算是否合法
      │
      ▼  找出本題最關鍵的轉換
核心觀察：用 last_seen 記錄字元最新位置；right 前進時，left 直接跳到重複字元上次位置的下一格，但不能後退。
      │
Pattern toolbox：window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count
      │
      ├─ 狀態轉移：右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻
      │
      ├─ 永遠成立：每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 求沒有重複字元的最長 substring 長度。
2. **寫出暴力：** 枚舉所有連續區間，並對每個區間重新計算是否合法。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 用 last_seen 記錄字元最新位置；right 前進時，left 直接跳到重複字元上次位置的下一格，但不能後退。
4. **定義 state 與轉移：** 使用「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」承載上述觀察，再執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(\text{alphabet})$

> [!tip] 一句話記憶
> 先說清楚「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」代表什麼，再說每一步如何「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案」的 base case。
>
> 2. **維持：** 每次執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」後，狀態仍與已處理資料一致。關鍵論證是：證明摘要在 add/remove 後與真實 window 一致，並證明 left 的單調前進不會跳過任何可行區間。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 window、答案不存在、重複字元、負數破壞 sum 單調性，以及 deque 中過期 index。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def length_of_longest_substring(s):
    last = {}
    left = best = 0
    for right, ch in enumerate(s):
        if ch in last and last[ch] >= left:
            left = last[ch] + 1
        last[ch] = right
        best = max(best, right - left + 1)
    return best
```

**Invariant：**計算答案時 `[left, right]` 沒有重複字元。

- 時間：$O(n)$
- 空間：$O(\text{alphabet})$

### Follow-up 1：原題直接變形
**問：最多允許 `k` 種不同字元？**

**答：**用 count map；種類數超過 `k` 時從左端移除，count 變零就刪 key。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Longest Substring Without Repeating Characters》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：用 last_seen 記錄字元最新位置；right 前進時，left 直接跳到重複字元上次位置的下一格，但不能後退。 失效情境包括：若移除左端後無法局部撤銷狀態，或合法性對擴張／收縮不具單調性，普通 window 就不適用。
>
> 替代路線是：改用 prefix sum＋hash、balanced tree、monotonic deque 或離線排序；固定長度 window 則通常更簡單。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：最佳長度之外同時保存 best_left/best_right；若要全部答案，需先定義重疊與去重語意，再收集所有達標區間。
>
> 套回《Longest Substring Without Repeating Characters》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 很適合 window，但要限制 retained events、處理 event-time 與 out-of-order data；高流量時可分 key 維護獨立 window。
>
> 此外必須把《Longest Substring Without Repeating Characters》目前隱含的前提寫成 contract：求沒有重複字元的最長 substring 長度。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Max Consecutive Ones III

### 題目

二進位陣列中最多可把 `k` 個 0 變成 1，求最長連續 1 區間。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 二進位陣列中最多可把 k 個 0 變成 1，求最長連續 1 區間。
>
> **核心轉換：** window 只需維護其中 0 的數量；zeros > k 時收縮 left，重新合法後用 window 長度更新答案。
>
> **主要知識點：** Sliding Window 與可逆的區間狀態。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Max Consecutive Ones III
      │
      ├─ 暴力路線：枚舉所有連續區間，並對每個區間重新計算是否合法
      │
      ▼  找出本題最關鍵的轉換
核心觀察：window 只需維護其中 0 的數量；zeros > k 時收縮 left，重新合法後用 window 長度更新答案。
      │
Pattern toolbox：window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count
      │
      ├─ 狀態轉移：右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻
      │
      ├─ 永遠成立：每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 二進位陣列中最多可把 k 個 0 變成 1，求最長連續 1 區間。
2. **寫出暴力：** 枚舉所有連續區間，並對每個區間重新計算是否合法。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** window 只需維護其中 0 的數量；zeros > k 時收縮 left，重新合法後用 window 長度更新答案。
4. **定義 state 與轉移：** 使用「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」承載上述觀察，再執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」代表什麼，再說每一步如何「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案」的 base case。
>
> 2. **維持：** 每次執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」後，狀態仍與已處理資料一致。關鍵論證是：證明摘要在 add/remove 後與真實 window 一致，並證明 left 的單調前進不會跳過任何可行區間。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 window、答案不存在、重複字元、負數破壞 sum 單調性，以及 deque 中過期 index。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def longest_ones(nums, k):
    left = zeros = best = 0
    for right, x in enumerate(nums):
        zeros += x == 0
        while zeros > k:
            zeros -= nums[left] == 0
            left += 1
        best = max(best, right - left + 1)
    return best
```

- 時間：$O(n)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：每個位置翻轉成本不同，總預算為 `B`？**

**答：**把 `zeros` 改成 window 內的總翻轉成本；成本超過 `B` 時縮左端。前提是成本皆非負，合法性才有單調性。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Max Consecutive Ones III》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：window 只需維護其中 0 的數量；zeros > k 時收縮 left，重新合法後用 window 長度更新答案。 失效情境包括：若移除左端後無法局部撤銷狀態，或合法性對擴張／收縮不具單調性，普通 window 就不適用。
>
> 替代路線是：改用 prefix sum＋hash、balanced tree、monotonic deque 或離線排序；固定長度 window 則通常更簡單。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：最佳長度之外同時保存 best_left/best_right；若要全部答案，需先定義重疊與去重語意，再收集所有達標區間。
>
> 套回《Max Consecutive Ones III》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 很適合 window，但要限制 retained events、處理 event-time 與 out-of-order data；高流量時可分 key 維護獨立 window。
>
> 此外必須把《Max Consecutive Ones III》目前隱含的前提寫成 contract：二進位陣列中最多可把 k 個 0 變成 1，求最長連續 1 區間。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Minimum Size Subarray Sum

### 題目

給正整數陣列與 target，求總和至少 target 的最短連續 subarray 長度。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 給正整數陣列與 target，求總和至少 target 的最短連續 subarray 長度。
>
> **核心轉換：** 正數保證右擴 sum 只增、左縮 sum 只減；每次 sum 達標就持續縮左端，找出該 right 的最短合法 window。
>
> **主要知識點：** Sliding Window 與可逆的區間狀態。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Minimum Size Subarray Sum
      │
      ├─ 暴力路線：枚舉所有連續區間，並對每個區間重新計算是否合法
      │
      ▼  找出本題最關鍵的轉換
核心觀察：正數保證右擴 sum 只增、左縮 sum 只減；每次 sum 達標就持續縮左端，找出該 right 的最短合法 window。
      │
Pattern toolbox：window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count
      │
      ├─ 狀態轉移：右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻
      │
      ├─ 永遠成立：每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 給正整數陣列與 target，求總和至少 target 的最短連續 subarray 長度。
2. **寫出暴力：** 枚舉所有連續區間，並對每個區間重新計算是否合法。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 正數保證右擴 sum 只增、左縮 sum 只減；每次 sum 達標就持續縮左端，找出該 right 的最短合法 window。
4. **定義 state 與轉移：** 使用「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」承載上述觀察，再執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」代表什麼，再說每一步如何「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案」的 base case。
>
> 2. **維持：** 每次執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」後，狀態仍與已處理資料一致。關鍵論證是：證明摘要在 add/remove 後與真實 window 一致，並證明 left 的單調前進不會跳過任何可行區間。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 window、答案不存在、重複字元、負數破壞 sum 單調性，以及 deque 中過期 index。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def min_subarray_len(target, nums):
    left = total = 0
    answer = len(nums) + 1
    for right, x in enumerate(nums):
        total += x
        while total >= target:
            answer = min(answer, right - left + 1)
            total -= nums[left]
            left += 1
    return 0 if answer == len(nums) + 1 else answer
```

**為何要求正數？**移除左端一定使總和不增加，window 合法性才單調。

### Follow-up 1：原題直接變形
**問：若陣列允許負數？**

**答：**一般 window 失效，因為擴張可能讓 sum 下降。需改用 prefix sum＋monotonic deque，見本章難題的 Shortest Subarray with Sum at Least K 變體。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Minimum Size Subarray Sum》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：正數保證右擴 sum 只增、左縮 sum 只減；每次 sum 達標就持續縮左端，找出該 right 的最短合法 window。 失效情境包括：若移除左端後無法局部撤銷狀態，或合法性對擴張／收縮不具單調性，普通 window 就不適用。
>
> 替代路線是：改用 prefix sum＋hash、balanced tree、monotonic deque 或離線排序；固定長度 window 則通常更簡單。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：最佳長度之外同時保存 best_left/best_right；若要全部答案，需先定義重疊與去重語意，再收集所有達標區間。
>
> 套回《Minimum Size Subarray Sum》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 很適合 window，但要限制 retained events、處理 event-time 與 out-of-order data；高流量時可分 key 維護獨立 window。
>
> 此外必須把《Minimum Size Subarray Sum》目前隱含的前提寫成 contract：給正整數陣列與 target，求總和至少 target 的最短連續 subarray 長度。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Minimum Window Substring

### 題目

在 `s` 中找最短 substring，使其包含 `t` 的所有字元與重複次數。

> [!tip]- 三層提示
> 1. `need[ch]` 是需求次數。
> 2. 不要每次掃完整張表判斷是否滿足。
> 3. 記錄有多少種字元已精確達標 `formed`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 在 s 中找最短 substring，使其包含 t 的所有字元與重複次數。
>
> **核心轉換：** 右端加入字元；當某字元 count 恰好達需求時，formed += 1。所有種類達標後，持續移動左端縮小；若移除後低於需求，window 失效。
>
> **主要知識點：** Sliding Window 與可逆的區間狀態。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Minimum Window Substring
      │
      ├─ 暴力路線：枚舉所有連續區間，並對每個區間重新計算是否合法
      │
      ▼  找出本題最關鍵的轉換
核心觀察：右端加入字元；當某字元 count 恰好達需求時，formed += 1。所有種類達標後，持續移動左端縮小；若移除後低於需求，window 失效。
      │
Pattern toolbox：window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count
      │
      ├─ 狀態轉移：右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻
      │
      ├─ 永遠成立：每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 在 s 中找最短 substring，使其包含 t 的所有字元與重複次數。
2. **寫出暴力：** 枚舉所有連續區間，並對每個區間重新計算是否合法。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 右端加入字元；當某字元 count 恰好達需求時，formed += 1。所有種類達標後，持續移動左端縮小；若移除後低於需求，window 失效。
4. **定義 state 與轉移：** 使用「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」承載上述觀察，再執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(s+t)$；空間：$O(\text{alphabet})$

> [!tip] 一句話記憶
> 先說清楚「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」代表什麼，再說每一步如何「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案」的 base case。
>
> 2. **維持：** 每次執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」後，狀態仍與已處理資料一致。關鍵論證是：證明摘要在 add/remove 後與真實 window 一致，並證明 left 的單調前進不會跳過任何可行區間。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 window、答案不存在、重複字元、負數破壞 sum 單調性，以及 deque 中過期 index。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

右端加入字元；當某字元 count 恰好達需求時，`formed += 1`。所有種類達標後，持續移動左端縮小；若移除後低於需求，window 失效。

```python
from collections import Counter, defaultdict

def min_window(s, t):
    if not t:
        return ""
    need = Counter(t)
    have = defaultdict(int)
    required = len(need)
    formed = 0
    left = 0
    best = (float("inf"), 0, 0)

    for right, ch in enumerate(s):
        have[ch] += 1
        if ch in need and have[ch] == need[ch]:
            formed += 1

        while formed == required:
            if right - left + 1 < best[0]:
                best = (right - left + 1, left, right + 1)
            removed = s[left]
            have[removed] -= 1
            if removed in need and have[removed] < need[removed]:
                formed -= 1
            left += 1

    return "" if best[0] == float("inf") else s[best[1]:best[2]]
```

- 時間：$O(|s|+|t|)$
- 空間：$O(\text{alphabet})$

### Follow-up 1：原題直接變形
**問：`s` 是無限 stream，無法保存全部內容？**

**答：**只保存與 `t` 有關的 `(index, char)` queue。Window 長度仍用原始 index 計算；若必須輸出 substring 本身，仍需保存最佳 window 的內容或能回讀來源。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Minimum Window Substring》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：右端加入字元；當某字元 count 恰好達需求時，formed += 1。所有種類達標後，持續移動左端縮小；若移除後低於需求，window 失效。 失效情境包括：若移除左端後無法局部撤銷狀態，或合法性對擴張／收縮不具單調性，普通 window 就不適用。
>
> 替代路線是：改用 prefix sum＋hash、balanced tree、monotonic deque 或離線排序；固定長度 window 則通常更簡單。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：最佳長度之外同時保存 best_left/best_right；若要全部答案，需先定義重疊與去重語意，再收集所有達標區間。
>
> 套回《Minimum Window Substring》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 很適合 window，但要限制 retained events、處理 event-time 與 out-of-order data；高流量時可分 key 維護獨立 window。
>
> 此外必須把《Minimum Window Substring》目前隱含的前提寫成 contract：在 s 中找最短 substring，使其包含 t 的所有字元與重複次數。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Sliding Window Maximum

### 題目

回傳每個長度為 `k` 的 window 中最大值，要求 $O(n)$。

> [!tip]- 三層提示
> 1. Heap 可做 $O(n\log n)$，但舊元素移除麻煩。
> 2. 若新值不小於 deque 尾端，尾端永遠不可能再成為最大值。
> 3. Deque 保存 index，且對應值單調遞減。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 回傳每個長度為 k 的 window 中最大值，要求 $O(n)$。
>
> **核心轉換：** 加入 i 前，移除 deque 尾端所有不大於 nums[i] 的 index；它們比新元素更小且更早過期。再移除已離開 window 的頭部。Deque 頭永遠是當前最大值。
>
> **主要知識點：** Sliding Window 與可逆的區間狀態。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Sliding Window Maximum
      │
      ├─ 暴力路線：枚舉所有連續區間，並對每個區間重新計算是否合法
      │
      ▼  找出本題最關鍵的轉換
核心觀察：加入 i 前，移除 deque 尾端所有不大於 nums[i] 的 index；它們比新元素更小且更早過期。再移除已離開 window 的頭部。Deque 頭永遠是當前最大值。
      │
Pattern toolbox：window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count
      │
      ├─ 狀態轉移：右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻
      │
      ├─ 永遠成立：每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 回傳每個長度為 k 的 window 中最大值，要求 $O(n)$。
2. **寫出暴力：** 枚舉所有連續區間，並對每個區間重新計算是否合法。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 加入 i 前，移除 deque 尾端所有不大於 nums[i] 的 index；它們比新元素更小且更早過期。再移除已離開 window 的頭部。Deque 頭永遠是當前最大值。
4. **定義 state 與轉移：** 使用「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」承載上述觀察，再執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；每個 index 最多進出 deque 一次；空間：$O(k)$

> [!tip] 一句話記憶
> 先說清楚「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」代表什麼，再說每一步如何「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案」的 base case。
>
> 2. **維持：** 每次執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」後，狀態仍與已處理資料一致。關鍵論證是：證明摘要在 add/remove 後與真實 window 一致，並證明 left 的單調前進不會跳過任何可行區間。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 window、答案不存在、重複字元、負數破壞 sum 單調性，以及 deque 中過期 index。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

加入 `i` 前，移除 deque 尾端所有不大於 `nums[i]` 的 index；它們比新元素更小且更早過期。再移除已離開 window 的頭部。Deque 頭永遠是當前最大值。

```python
from collections import deque

def max_sliding_window(nums, k):
    q = deque()
    answer = []
    for i, x in enumerate(nums):
        while q and nums[q[-1]] <= x:
            q.pop()
        q.append(i)
        if q[0] <= i - k:
            q.popleft()
        if i >= k - 1:
            answer.append(nums[q[0]])
    return answer
```

- 時間：$O(n)$；每個 index 最多進出 deque 一次
- 空間：$O(k)$

### Follow-up 1：原題直接變形
**問：同時要 window minimum？**

**答：**再維護一個值單調遞增的 deque。兩者操作互相獨立，總時間仍為 $O(n)$。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Sliding Window Maximum》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：加入 i 前，移除 deque 尾端所有不大於 nums[i] 的 index；它們比新元素更小且更早過期。再移除已離開 window 的頭部。Deque 頭永遠是當前最大值。 失效情境包括：若移除左端後無法局部撤銷狀態，或合法性對擴張／收縮不具單調性，普通 window 就不適用。
>
> 替代路線是：改用 prefix sum＋hash、balanced tree、monotonic deque 或離線排序；固定長度 window 則通常更簡單。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：最佳長度之外同時保存 best_left/best_right；若要全部答案，需先定義重疊與去重語意，再收集所有達標區間。
>
> 套回《Sliding Window Maximum》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 很適合 window，但要限制 retained events、處理 event-time 與 out-of-order data；高流量時可分 key 維護獨立 window。
>
> 此外必須把《Sliding Window Maximum》目前隱含的前提寫成 contract：回傳每個長度為 k 的 window 中最大值，要求 $O(n)$。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Substring with Concatenation of All Words

### 題目

`words` 中所有字串等長。找出 `s` 中所有起點，使該 substring 恰由所有 words 各使用一次、任意順序串接而成。

> [!tip]- 三層提示
> 1. Window 的移動單位不是一個字元，而是一個 word 長度。
> 2. 不同起點 offset 彼此獨立。
> 3. 某 word 次數過多時，從左端移除 word 直到合法。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** words 中所有字串等長。找出 s 中所有起點，使該 substring 恰由所有 words 各使用一次、任意順序串接而成。
>
> **核心轉換：** 對 offset 0..wordlen-1 各跑一次 sliding window。Window 只包含完整 word token；遇到不存在的 word 就清空，遇到過量就縮左端。
>
> **主要知識點：** Sliding Window 與可逆的區間狀態。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Substring with Concatenation of All Words
      │
      ├─ 暴力路線：枚舉所有連續區間，並對每個區間重新計算是否合法
      │
      ▼  找出本題最關鍵的轉換
核心觀察：對 offset 0..wordlen-1 各跑一次 sliding window。Window 只包含完整 word token；遇到不存在的 word 就清空，遇到過量就縮左端。
      │
Pattern toolbox：window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count
      │
      ├─ 狀態轉移：右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻
      │
      ├─ 永遠成立：每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** words 中所有字串等長。找出 s 中所有起點，使該 substring 恰由所有 words 各使用一次、任意順序串接而成。
2. **寫出暴力：** 枚舉所有連續區間，並對每個區間重新計算是否合法。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 對 offset 0..wordlen-1 各跑一次 sliding window。Window 只包含完整 word token；遇到不存在的 word 就清空，遇到過量就縮左端。
4. **定義 state 與轉移：** 使用「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」承載上述觀察，再執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(s)$ 次 token 操作，切片成本依 word 長度；空間：$O(words)$

> [!tip] 一句話記憶
> 先說清楚「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」代表什麼，再說每一步如何「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案」的 base case。
>
> 2. **維持：** 每次執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」後，狀態仍與已處理資料一致。關鍵論證是：證明摘要在 add/remove 後與真實 window 一致，並證明 left 的單調前進不會跳過任何可行區間。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 window、答案不存在、重複字元、負數破壞 sum 單調性，以及 deque 中過期 index。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

對 offset `0..word_len-1` 各跑一次 sliding window。Window 只包含完整 word token；遇到不存在的 word 就清空，遇到過量就縮左端。

```python
from collections import Counter, defaultdict

def find_substring(s, words):
    if not s or not words:
        return []
    width = len(words[0])
    need = Counter(words)
    answer = []

    for offset in range(width):
        left = offset
        used = 0
        have = defaultdict(int)
        for right in range(offset, len(s) - width + 1, width):
            word = s[right:right + width]
            if word not in need:
                have.clear()
                used = 0
                left = right + width
                continue

            have[word] += 1
            used += 1
            while have[word] > need[word]:
                removed = s[left:left + width]
                have[removed] -= 1
                used -= 1
                left += width

            if used == len(words):
                answer.append(left)
                removed = s[left:left + width]
                have[removed] -= 1
                used -= 1
                left += width
    return answer
```

- 時間：$O(|s|)$ 次 token 操作，切片成本依 word 長度
- 空間：$O(|words|)$

### Follow-up 1：原題直接變形
**問：words 長度不相同？**

**答：**固定步長 window 不再成立。一般版本接近 word-break search：可用 trie 找每個位置可匹配的 word，再以 memoized DFS 追蹤剩餘 multiset；狀態數可能指數成長。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Substring with Concatenation of All Words》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：對 offset 0..wordlen-1 各跑一次 sliding window。Window 只包含完整 word token；遇到不存在的 word 就清空，遇到過量就縮左端。 失效情境包括：若移除左端後無法局部撤銷狀態，或合法性對擴張／收縮不具單調性，普通 window 就不適用。
>
> 替代路線是：改用 prefix sum＋hash、balanced tree、monotonic deque 或離線排序；固定長度 window 則通常更簡單。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：最佳長度之外同時保存 best_left/best_right；若要全部答案，需先定義重疊與去重語意，再收集所有達標區間。
>
> 套回《Substring with Concatenation of All Words》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 很適合 window，但要限制 retained events、處理 event-time 與 out-of-order data；高流量時可分 key 維護獨立 window。
>
> 此外必須把《Substring with Concatenation of All Words》目前隱含的前提寫成 contract：words 中所有字串等長。找出 s 中所有起點，使該 substring 恰由所有 words 各使用一次、任意順序串接而成。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Minimum Number of K Consecutive Bit Flips

### 題目

每次可翻轉長度恰為 `k` 的連續 bits。求把陣列全變成 1 的最少操作，無法完成回傳 `-1`。

> [!tip]- 三層提示
> 1. 從左到右時，離開 index `i` 後再也不能改它。
> 2. 因此若目前有效值是 0，這裡必須翻。
> 3. 用 difference / queue 記錄哪些翻轉仍有效。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每次可翻轉長度恰為 k 的連續 bits。求把陣列全變成 1 的最少操作，無法完成回傳 -1。
>
> **核心轉換：** parity 表示目前位置被有效翻轉幾次的奇偶性。若 bit ^ parity == 0，唯一選擇是在 i 開始翻；若長度超界則無解。用 started[i] 在 i+k 時移除其影響。
>
> **主要知識點：** Sliding Window 與可逆的區間狀態。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Minimum Number of K Consecutive Bit Flips
      │
      ├─ 暴力路線：枚舉所有連續區間，並對每個區間重新計算是否合法
      │
      ▼  找出本題最關鍵的轉換
核心觀察：parity 表示目前位置被有效翻轉幾次的奇偶性。若 bit ^ parity == 0，唯一選擇是在 i 開始翻；若長度超界則無解。用 started[i] 在 i+k 時移除其影響。
      │
Pattern toolbox：window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count
      │
      ├─ 狀態轉移：右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻
      │
      ├─ 永遠成立：每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每次可翻轉長度恰為 k 的連續 bits。求把陣列全變成 1 的最少操作，無法完成回傳 -1。
2. **寫出暴力：** 枚舉所有連續區間，並對每個區間重新計算是否合法。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** parity 表示目前位置被有效翻轉幾次的奇偶性。若 bit ^ parity == 0，唯一選擇是在 i 開始翻；若長度超界則無解。用 started[i] 在 i+k 時移除其影響。
4. **定義 state 與轉移：** 使用「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」承載上述觀察，再執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(n)$；queue 可降為 $O(k)$

> [!tip] 一句話記憶
> 先說清楚「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」代表什麼，再說每一步如何「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案」的 base case。
>
> 2. **維持：** 每次執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」後，狀態仍與已處理資料一致。關鍵論證是：證明摘要在 add/remove 後與真實 window 一致，並證明 left 的單調前進不會跳過任何可行區間。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 window、答案不存在、重複字元、負數破壞 sum 單調性，以及 deque 中過期 index。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

`parity` 表示目前位置被有效翻轉幾次的奇偶性。若 `bit ^ parity == 0`，唯一選擇是在 `i` 開始翻；若長度超界則無解。用 `started[i]` 在 `i+k` 時移除其影響。

```python
def min_k_bit_flips(nums, k):
    started = [0] * len(nums)
    parity = flips = 0
    for i, bit in enumerate(nums):
        if i >= k:
            parity ^= started[i - k]
        if bit ^ parity == 0:
            if i + k > len(nums):
                return -1
            started[i] = 1
            parity ^= 1
            flips += 1
    return flips
```

- 時間：$O(n)$
- 空間：$O(n)$；queue 可降為 $O(k)$

### Follow-up 1：原題直接變形
**問：允許翻轉任意長度 `1..k`，還能沿用相同 greedy 嗎？**

**答：**不能直接沿用。「在 i 必須翻」仍可能成立，但選擇哪個長度會影響未來，產生多種狀態；通常需 DP、shortest path state search，或根據新限制找額外 greedy proof。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Minimum Number of K Consecutive Bit Flips》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：parity 表示目前位置被有效翻轉幾次的奇偶性。若 bit ^ parity == 0，唯一選擇是在 i 開始翻；若長度超界則無解。用 started[i] 在 i+k 時移除其影響。 失效情境包括：若移除左端後無法局部撤銷狀態，或合法性對擴張／收縮不具單調性，普通 window 就不適用。
>
> 替代路線是：改用 prefix sum＋hash、balanced tree、monotonic deque 或離線排序；固定長度 window 則通常更簡單。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：最佳長度之外同時保存 best_left/best_right；若要全部答案，需先定義重疊與去重語意，再收集所有達標區間。
>
> 套回《Minimum Number of K Consecutive Bit Flips》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 很適合 window，但要限制 retained events、處理 event-time 與 out-of-order data；高流量時可分 key 維護獨立 window。
>
> 此外必須把《Minimum Number of K Consecutive Bit Flips》目前隱含的前提寫成 contract：每次可翻轉長度恰為 k 的連續 bits。求把陣列全變成 1 的最少操作，無法完成回傳 -1。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Count Subarrays With Fixed Bounds

### 題目

計算 subarray 數量，使其中最小值恰為 `minK`、最大值恰為 `maxK`。

> [!tip]- 三層提示
> 1. 超出 `[minK, maxK]` 的元素會切斷所有合法 window。
> 2. 記錄最近一次看見 `minK` 與 `maxK` 的位置。
> 3. 以 `right` 結尾的合法起點數可以直接算。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 計算 subarray 數量，使其中最小值恰為 minK、最大值恰為 maxK。
>
> **核心轉換：** 維護：
>
> **主要知識點：** Sliding Window 與可逆的區間狀態。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Count Subarrays With Fixed Bounds
      │
      ├─ 暴力路線：枚舉所有連續區間，並對每個區間重新計算是否合法
      │
      ▼  找出本題最關鍵的轉換
核心觀察：維護：
      │
Pattern toolbox：window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count
      │
      ├─ 狀態轉移：右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻
      │
      ├─ 永遠成立：每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 計算 subarray 數量，使其中最小值恰為 minK、最大值恰為 maxK。
2. **寫出暴力：** 枚舉所有連續區間，並對每個區間重新計算是否合法。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 維護：
4. **定義 state 與轉移：** 使用「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」承載上述觀察，再執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「window [left, right] 加上一個可增量更新的摘要，例如 frequency、sum、deque 或 violation count」代表什麼，再說每一步如何「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每次計算答案時，window 滿足題目要求；所有被 left 越過的起點都已完成其最佳可能答案」的 base case。
>
> 2. **維持：** 每次執行「右端擴張納入新元素；若失去合法性，左端收縮並撤銷元素貢獻」後，狀態仍與已處理資料一致。關鍵論證是：證明摘要在 add/remove 後與真實 window 一致，並證明 left 的單調前進不會跳過任何可行區間。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 window、答案不存在、重複字元、負數破壞 sum 單調性，以及 deque 中過期 index。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

維護：

- `bad`：最近一次越界位置。
- `last_min`：最近 `minK`。
- `last_max`：最近 `maxK`。

以 `right` 結尾時，起點必須大於 `bad`，且不能晚於 `min(last_min, last_max)`，所以新增數量是 `max(0, min(last_min,last_max)-bad)`。

```python
def count_subarrays_fixed_bounds(nums, min_k, max_k):
    bad = last_min = last_max = -1
    answer = 0
    for i, x in enumerate(nums):
        if x < min_k or x > max_k:
            bad = i
        if x == min_k:
            last_min = i
        if x == max_k:
            last_max = i
        answer += max(0, min(last_min, last_max) - bad)
    return answer
```

- 時間：$O(n)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：若只要求 `min >= minK` 且 `max <= maxK`？**

**答：**每次遇到越界值更新 `bad`，以 `right` 結尾的所有合法起點為 `bad+1..right`，新增 `right-bad` 個，不再需要追蹤兩個 bound 的出現位置。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Count Subarrays With Fixed Bounds》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：維護： 失效情境包括：若移除左端後無法局部撤銷狀態，或合法性對擴張／收縮不具單調性，普通 window 就不適用。
>
> 替代路線是：改用 prefix sum＋hash、balanced tree、monotonic deque 或離線排序；固定長度 window 則通常更簡單。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：最佳長度之外同時保存 best_left/best_right；若要全部答案，需先定義重疊與去重語意，再收集所有達標區間。
>
> 套回《Count Subarrays With Fixed Bounds》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming 很適合 window，但要限制 retained events、處理 event-time 與 out-of-order data；高流量時可分 key 維護獨立 window。
>
> 此外必須把《Count Subarrays With Fixed Bounds》目前隱含的前提寫成 contract：計算 subarray 數量，使其中最小值恰為 minK、最大值恰為 maxK。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 會定義 window 合法條件。
- [ ] 知道最長合法與最短滿足的收縮時機不同。
- [ ] 能證明每個 index 只進出結構常數次。
- [ ] 遇到負數時會重新檢查單調性。
