---
title: DP 2D Sequence and Interval
tags:
  - coding-interview/pattern
  - dynamic-programming
  - interval-dp
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 17 — DP II：Sequence, Knapsack and Interval

[[16 - DP 1D and State Machine|← 上一章]] · [[00 - Book Index|目錄]] · [[18 - Bit Math and Geometry|下一章 →]]

> [!abstract] Mental model
> 兩序列 DP 的 state 常是兩個 prefix；interval DP 常把「最後完成哪個操作」當分割點；knapsack 則在物品與容量間做取捨。

---

## 核心題 1：Longest Common Subsequence


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 求兩字串不必連續但保持相對順序的最長共同 subsequence 長度。
>
> **核心轉換：** dp[i][j] 表示 a[:i] 與 b[:j] 的 LCS；末字元相同走 diagonal+1，不同則丟棄其中一個末字元並取上、左較大值。
>
> **主要知識點：** 2D／Interval DP 與結構化子問題。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Longest Common Subsequence
      │
      ├─ 暴力路線：枚舉所有對齊、切點或操作序列，造成指數分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：dp[i][j] 表示 a[:i] 與 b[:j] 的 LCS；末字元相同走 diagonal+1，不同則丟棄其中一個末字元並取上、左較大值。
      │
Pattern toolbox：dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案
      │
      ├─ 狀態轉移：依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間
      │
      ├─ 永遠成立：填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 求兩字串不必連續但保持相對順序的最長共同 subsequence 長度。
2. **寫出暴力：** 枚舉所有對齊、切點或操作序列，造成指數分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** dp[i][j] 表示 a[:i] 與 b[:j] 的 LCS；末字元相同走 diagonal+1，不同則丟棄其中一個末字元並取上、左較大值。
4. **定義 state 與轉移：** 使用「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」承載上述觀察，再執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」代表什麼，再說每一步如何「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案」的 base case。
>
> 2. **維持：** 每次執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」後，狀態仍與已處理資料一致。關鍵論證是：依 prefix sum 或 interval length induction，證明 transition 對所有可能的最後決策做完整且不重複分類。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 prefix、區間長度順序、i-1/j-1、重複計數、字元匹配規則與記憶體 O(nm)。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def longest_common_subsequence(a, b):
    previous = [0] * (len(b) + 1)
    for char_a in a:
        current = [0] * (len(b) + 1)
        for j, char_b in enumerate(b, 1):
            if char_a == char_b:
                current[j] = previous[j - 1] + 1
            else:
                current[j] = max(previous[j], current[j - 1])
        previous = current
    return previous[-1]
```

### Follow-up 1：原題直接變形
**問：回傳實際 LCS？**

**答：**保存完整 table，從右下角回走：字元相同就加入答案並斜走；否則走向較大鄰格。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Longest Common Subsequence》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：dp[i][j] 表示 a[:i] 與 b[:j] 的 LCS；末字元相同走 diagonal+1，不同則丟棄其中一個末字元並取上、左較大值。 失效情境包括：若 transition 還依賴未被 state 表示的 context，二維 DP 不足；維度增加可能讓複雜度不可接受。
>
> 替代路線是：壓縮 rolling rows、bitset、Knuth/Monge 類優化、memoization pruning，或改用 automaton/graph。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 transition choice；由 dp[m][n] 逆推 alignment、切點或操作。空間壓縮版本通常需 Hirschberg 或重算。
>
> 套回《Longest Common Subsequence》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 長序列需限制 table、分塊或近似；增量編輯可考慮局部 recompute，但最壞仍可能影響整張表。
>
> 此外必須把《Longest Common Subsequence》目前隱含的前提寫成 contract：求兩字串不必連續但保持相對順序的最長共同 subsequence 長度。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Edit Distance

### 題目

允許插入、刪除、替換一個字元，求把 `a` 轉成 `b` 的最少操作數。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 允許插入、刪除、替換一個字元，求把 a 轉成 b 的最少操作數。
>
> **核心轉換：** dp[i][j] 比較兩個 prefix；末字元相同沿用 diagonal，否則從刪除、插入、替換三個前驅取最小再加一。
>
> **主要知識點：** 2D／Interval DP 與結構化子問題。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Edit Distance
      │
      ├─ 暴力路線：枚舉所有對齊、切點或操作序列，造成指數分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：dp[i][j] 比較兩個 prefix；末字元相同沿用 diagonal，否則從刪除、插入、替換三個前驅取最小再加一。
      │
Pattern toolbox：dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案
      │
      ├─ 狀態轉移：依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間
      │
      ├─ 永遠成立：填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 允許插入、刪除、替換一個字元，求把 a 轉成 b 的最少操作數。
2. **寫出暴力：** 枚舉所有對齊、切點或操作序列，造成指數分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** dp[i][j] 比較兩個 prefix；末字元相同沿用 diagonal，否則從刪除、插入、替換三個前驅取最小再加一。
4. **定義 state 與轉移：** 使用「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」承載上述觀察，再執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」代表什麼，再說每一步如何「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案」的 base case。
>
> 2. **維持：** 每次執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」後，狀態仍與已處理資料一致。關鍵論證是：依 prefix sum 或 interval length induction，證明 transition 對所有可能的最後決策做完整且不重複分類。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 prefix、區間長度順序、i-1/j-1、重複計數、字元匹配規則與記憶體 O(nm)。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def edit_distance(a, b):
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, 1):
        current = [i] + [0] * len(b)
        for j, char_b in enumerate(b, 1):
            if char_a == char_b:
                current[j] = previous[j - 1]
            else:
                current[j] = 1 + min(
                    previous[j],      # delete
                    current[j - 1],   # insert
                    previous[j - 1],  # replace
                )
        previous = current
    return previous[-1]
```

### Follow-up 1：原題直接變形
**問：三種操作成本不同？**

**答：**transition 分別加上 delete/insert/replace cost；相同字元仍可直接沿用 diagonal。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Edit Distance》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：dp[i][j] 比較兩個 prefix；末字元相同沿用 diagonal，否則從刪除、插入、替換三個前驅取最小再加一。 失效情境包括：若 transition 還依賴未被 state 表示的 context，二維 DP 不足；維度增加可能讓複雜度不可接受。
>
> 替代路線是：壓縮 rolling rows、bitset、Knuth/Monge 類優化、memoization pruning，或改用 automaton/graph。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 transition choice；由 dp[m][n] 逆推 alignment、切點或操作。空間壓縮版本通常需 Hirschberg 或重算。
>
> 套回《Edit Distance》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 長序列需限制 table、分塊或近似；增量編輯可考慮局部 recompute，但最壞仍可能影響整張表。
>
> 此外必須把《Edit Distance》目前隱含的前提寫成 contract：允許插入、刪除、替換一個字元，求把 a 轉成 b 的最少操作數。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Partition Equal Subset Sum


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 判斷正整數陣列能否分成總和相同的兩個 subsets。
>
> **核心轉換：** 總和必須為偶數，問題化為 0/1 subset sum target=sum/2；容量由大到小更新，確保每個數只使用一次。
>
> **主要知識點：** 2D／Interval DP 與結構化子問題。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Partition Equal Subset Sum
      │
      ├─ 暴力路線：枚舉所有對齊、切點或操作序列，造成指數分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：總和必須為偶數，問題化為 0/1 subset sum target=sum/2；容量由大到小更新，確保每個數只使用一次。
      │
Pattern toolbox：dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案
      │
      ├─ 狀態轉移：依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間
      │
      ├─ 永遠成立：填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 判斷正整數陣列能否分成總和相同的兩個 subsets。
2. **寫出暴力：** 枚舉所有對齊、切點或操作序列，造成指數分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 總和必須為偶數，問題化為 0/1 subset sum target=sum/2；容量由大到小更新，確保每個數只使用一次。
4. **定義 state 與轉移：** 使用「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」承載上述觀察，再執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」代表什麼，再說每一步如何「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案」的 base case。
>
> 2. **維持：** 每次執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」後，狀態仍與已處理資料一致。關鍵論證是：依 prefix sum 或 interval length induction，證明 transition 對所有可能的最後決策做完整且不重複分類。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 prefix、區間長度順序、i-1/j-1、重複計數、字元匹配規則與記憶體 O(nm)。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def can_partition(nums):
    total = sum(nums)
    if total % 2:
        return False
    target = total // 2
    possible = [False] * (target + 1)
    possible[0] = True
    for value in nums:
        for current in range(target, value - 1, -1):
            possible[current] |= possible[current - value]
    return possible[target]
```

**為何倒序？**確保每個元素只使用一次。

### Follow-up 1：原題直接變形
**問：可無限使用每個 value？**

**答：**容量改成由小到大更新，讓本輪剛得到的 state 可以再次使用同一 value。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Partition Equal Subset Sum》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：總和必須為偶數，問題化為 0/1 subset sum target=sum/2；容量由大到小更新，確保每個數只使用一次。 失效情境包括：若 transition 還依賴未被 state 表示的 context，二維 DP 不足；維度增加可能讓複雜度不可接受。
>
> 替代路線是：壓縮 rolling rows、bitset、Knuth/Monge 類優化、memoization pruning，或改用 automaton/graph。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 transition choice；由 dp[m][n] 逆推 alignment、切點或操作。空間壓縮版本通常需 Hirschberg 或重算。
>
> 套回《Partition Equal Subset Sum》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 長序列需限制 table、分塊或近似；增量編輯可考慮局部 recompute，但最壞仍可能影響整張表。
>
> 此外必須把《Partition Equal Subset Sum》目前隱含的前提寫成 contract：判斷正整數陣列能否分成總和相同的兩個 subsets。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Regular Expression Matching

### 題目

Pattern 中 `.` 匹配任一字元，`*` 表示前一元素可出現零次或多次。判斷整個字串是否匹配。

> [!tip]- 三層提示
> 1. State 是 `(i,j)`：`s[i:]` 是否匹配 `p[j:]`。
> 2. 先判斷目前字元是否匹配。
> 3. 若下一個 pattern 是 `*`，可跳過整組，或匹配一個字元後留在同一 pattern。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** Pattern 中 . 匹配任一字元， 表示前一元素可出現零次或多次。判斷整個字串是否匹配。
>
> **核心轉換：** p[j+1]=='' 時：
>
> **主要知識點：** 2D／Interval DP 與結構化子問題。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Regular Expression Matching
      │
      ├─ 暴力路線：枚舉所有對齊、切點或操作序列，造成指數分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：p[j+1]=='' 時：
      │
Pattern toolbox：dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案
      │
      ├─ 狀態轉移：依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間
      │
      ├─ 永遠成立：填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** Pattern 中 . 匹配任一字元， 表示前一元素可出現零次或多次。判斷整個字串是否匹配。
2. **寫出暴力：** 枚舉所有對齊、切點或操作序列，造成指數分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** p[j+1]=='' 時：
4. **定義 state 與轉移：** 使用「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」承載上述觀察，再執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(sp)$；空間：$O(sp)$

> [!tip] 一句話記憶
> 先說清楚「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」代表什麼，再說每一步如何「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案」的 base case。
>
> 2. **維持：** 每次執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」後，狀態仍與已處理資料一致。關鍵論證是：依 prefix sum 或 interval length induction，證明 transition 對所有可能的最後決策做完整且不重複分類。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 prefix、區間長度順序、i-1/j-1、重複計數、字元匹配規則與記憶體 O(nm)。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

`p[j+1]=='*'` 時：

- 零次：`dp(i,j+2)`
- 至少一次：`first_match and dp(i+1,j)`

```python
from functools import lru_cache

def is_match(s, p):
    @lru_cache(None)
    def dp(i, j):
        if j == len(p):
            return i == len(s)
        first = i < len(s) and (p[j] == s[i] or p[j] == ".")
        if j + 1 < len(p) and p[j + 1] == "*":
            return dp(i, j + 2) or (first and dp(i + 1, j))
        return first and dp(i + 1, j + 1)

    return dp(0, 0)
```

- 時間：$O(|s||p|)$
- 空間：$O(|s||p|)$

### Follow-up 1：原題直接變形
**問：若 `*` 是 glob 語意，代表任意字元序列，而不是重複前一元素？**

**答：**transition 改為 `dp(i,j+1)` 跳過星號，或 `i<len(s) and dp(i+1,j)` 讓星號吞一個字元。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Regular Expression Matching》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：p[j+1]=='' 時： 失效情境包括：若 transition 還依賴未被 state 表示的 context，二維 DP 不足；維度增加可能讓複雜度不可接受。
>
> 替代路線是：壓縮 rolling rows、bitset、Knuth/Monge 類優化、memoization pruning，或改用 automaton/graph。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 transition choice；由 dp[m][n] 逆推 alignment、切點或操作。空間壓縮版本通常需 Hirschberg 或重算。
>
> 套回《Regular Expression Matching》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 長序列需限制 table、分塊或近似；增量編輯可考慮局部 recompute，但最壞仍可能影響整張表。
>
> 此外必須把《Regular Expression Matching》目前隱含的前提寫成 contract：Pattern 中 . 匹配任一字元， 表示前一元素可出現零次或多次。判斷整個字串是否匹配。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Distinct Subsequences

### 題目

計算 `s` 中有多少 subsequences 等於 `t`。

> [!tip]- 三層提示
> 1. 掃描 `s`，`dp[j]` 表示形成 `t[:j]` 的方法數。
> 2. 若目前字元等於 `t[j-1]`，可把形成較短 prefix 的方法接上。
> 3. `j` 必須倒序更新，避免同一 `s` 字元使用多次。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 計算 s 中有多少 subsequences 等於 t。
>
> **核心轉換：** dp[0]=1，因為空 target 可由任何 prefix 以一種方式形成。匹配時 dp[j] += dp[j-1]。
>
> **主要知識點：** 2D／Interval DP 與結構化子問題。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Distinct Subsequences
      │
      ├─ 暴力路線：枚舉所有對齊、切點或操作序列，造成指數分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：dp[0]=1，因為空 target 可由任何 prefix 以一種方式形成。匹配時 dp[j] += dp[j-1]。
      │
Pattern toolbox：dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案
      │
      ├─ 狀態轉移：依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間
      │
      ├─ 永遠成立：填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 計算 s 中有多少 subsequences 等於 t。
2. **寫出暴力：** 枚舉所有對齊、切點或操作序列，造成指數分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** dp[0]=1，因為空 target 可由任何 prefix 以一種方式形成。匹配時 dp[j] += dp[j-1]。
4. **定義 state 與轉移：** 使用「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」承載上述觀察，再執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(st)$；空間：$O(t)$

> [!tip] 一句話記憶
> 先說清楚「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」代表什麼，再說每一步如何「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案」的 base case。
>
> 2. **維持：** 每次執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」後，狀態仍與已處理資料一致。關鍵論證是：依 prefix sum 或 interval length induction，證明 transition 對所有可能的最後決策做完整且不重複分類。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 prefix、區間長度順序、i-1/j-1、重複計數、字元匹配規則與記憶體 O(nm)。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

`dp[0]=1`，因為空 target 可由任何 prefix 以一種方式形成。匹配時 `dp[j] += dp[j-1]`。

```python
def num_distinct(s, t):
    dp = [0] * (len(t) + 1)
    dp[0] = 1
    for ch in s:
        for j in range(len(t), 0, -1):
            if ch == t[j - 1]:
                dp[j] += dp[j - 1]
    return dp[-1]
```

- 時間：$O(|s||t|)$
- 空間：$O(|t|)$

### Follow-up 1：原題直接變形
**問：只需判斷 t 是否為 subsequence？**

**答：**不需 DP；two pointers 線性掃描即可。計數才需要保存不同選法。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Distinct Subsequences》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：dp[0]=1，因為空 target 可由任何 prefix 以一種方式形成。匹配時 dp[j] += dp[j-1]。 失效情境包括：若 transition 還依賴未被 state 表示的 context，二維 DP 不足；維度增加可能讓複雜度不可接受。
>
> 替代路線是：壓縮 rolling rows、bitset、Knuth/Monge 類優化、memoization pruning，或改用 automaton/graph。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 transition choice；由 dp[m][n] 逆推 alignment、切點或操作。空間壓縮版本通常需 Hirschberg 或重算。
>
> 套回《Distinct Subsequences》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 長序列需限制 table、分塊或近似；增量編輯可考慮局部 recompute，但最壞仍可能影響整張表。
>
> 此外必須把《Distinct Subsequences》目前隱含的前提寫成 contract：計算 s 中有多少 subsequences 等於 t。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Burst Balloons

### 題目

戳破 balloon `i` 得到相鄰尚存 balloon 值乘積。求最大 coins。

> [!tip]- 三層提示
> 1. 第一個戳破的 balloon 其鄰居難以確定。
> 2. 改枚舉某區間「最後一個」被戳破的 balloon。
> 3. 最後戳 `k` 時，其鄰居就是區間外固定邊界。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 戳破 balloon i 得到相鄰尚存 balloon 值乘積。求最大 coins。
>
> **核心轉換：** 兩端加上虛擬 1。dp(left,right) 表示戳完開區間 (left,right) 的最大 coins。枚舉最後戳的 k：
>
> **主要知識點：** 2D／Interval DP 與結構化子問題。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Burst Balloons
      │
      ├─ 暴力路線：枚舉所有對齊、切點或操作序列，造成指數分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：兩端加上虛擬 1。dp(left,right) 表示戳完開區間 (left,right) 的最大 coins。枚舉最後戳的 k：
      │
Pattern toolbox：dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案
      │
      ├─ 狀態轉移：依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間
      │
      ├─ 永遠成立：填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 戳破 balloon i 得到相鄰尚存 balloon 值乘積。求最大 coins。
2. **寫出暴力：** 枚舉所有對齊、切點或操作序列，造成指數分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 兩端加上虛擬 1。dp(left,right) 表示戳完開區間 (left,right) 的最大 coins。枚舉最後戳的 k：
4. **定義 state 與轉移：** 使用「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」承載上述觀察，再執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n^3)$；空間：$O(n^2)$

> [!tip] 一句話記憶
> 先說清楚「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」代表什麼，再說每一步如何「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案」的 base case。
>
> 2. **維持：** 每次執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」後，狀態仍與已處理資料一致。關鍵論證是：依 prefix sum 或 interval length induction，證明 transition 對所有可能的最後決策做完整且不重複分類。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 prefix、區間長度順序、i-1/j-1、重複計數、字元匹配規則與記憶體 O(nm)。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

兩端加上虛擬 `1`。`dp(left,right)` 表示戳完開區間 `(left,right)` 的最大 coins。枚舉最後戳的 `k`：

```text
dp(left,k) + values[left]*values[k]*values[right] + dp(k,right)
```

```python
from functools import lru_cache

def max_coins(nums):
    values = [1] + nums + [1]

    @lru_cache(None)
    def dp(left, right):
        if left + 1 == right:
            return 0
        return max(
            dp(left, k)
            + values[left] * values[k] * values[right]
            + dp(k, right)
            for k in range(left + 1, right)
        )

    return dp(0, len(values) - 1)
```

- 時間：$O(n^3)$
- 空間：$O(n^2)$

### Follow-up 1：原題直接變形
**問：如何改 bottom-up？**

**答：**依 interval length 由小到大計算；`left`、`right` 固定後枚舉最後 balloon `k`。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Burst Balloons》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：兩端加上虛擬 1。dp(left,right) 表示戳完開區間 (left,right) 的最大 coins。枚舉最後戳的 k： 失效情境包括：若 transition 還依賴未被 state 表示的 context，二維 DP 不足；維度增加可能讓複雜度不可接受。
>
> 替代路線是：壓縮 rolling rows、bitset、Knuth/Monge 類優化、memoization pruning，或改用 automaton/graph。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 transition choice；由 dp[m][n] 逆推 alignment、切點或操作。空間壓縮版本通常需 Hirschberg 或重算。
>
> 套回《Burst Balloons》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 長序列需限制 table、分塊或近似；增量編輯可考慮局部 recompute，但最壞仍可能影響整張表。
>
> 此外必須把《Burst Balloons》目前隱含的前提寫成 contract：戳破 balloon i 得到相鄰尚存 balloon 值乘積。求最大 coins。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Palindrome Partitioning II

### 題目

把字串切成 palindrome substrings，求最少 cuts。

> [!tip]- 三層提示
> 1. 預先計算 `pal[i][j]`。
> 2. `cuts[i]` 表示 prefix `s[:i]` 的最少 cuts。
> 3. 若 `s[start:end+1]` 是 palindrome，更新 `cuts[end+1] = cuts[start]+1`，並令 `cuts[0]=-1`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 把字串切成 palindrome substrings，求最少 cuts。
>
> **核心轉換：** 先依 substring length 建 palindrome table，再做 prefix DP。cuts[0]=-1 讓整段 palindrome 得到零 cuts。
>
> **主要知識點：** 2D／Interval DP 與結構化子問題。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Palindrome Partitioning II
      │
      ├─ 暴力路線：枚舉所有對齊、切點或操作序列，造成指數分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：先依 substring length 建 palindrome table，再做 prefix DP。cuts[0]=-1 讓整段 palindrome 得到零 cuts。
      │
Pattern toolbox：dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案
      │
      ├─ 狀態轉移：依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間
      │
      ├─ 永遠成立：填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 把字串切成 palindrome substrings，求最少 cuts。
2. **寫出暴力：** 枚舉所有對齊、切點或操作序列，造成指數分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 先依 substring length 建 palindrome table，再做 prefix DP。cuts[0]=-1 讓整段 palindrome 得到零 cuts。
4. **定義 state 與轉移：** 使用「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」承載上述觀察，再執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n^2)$；空間：$O(n^2)$

> [!tip] 一句話記憶
> 先說清楚「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」代表什麼，再說每一步如何「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案」的 base case。
>
> 2. **維持：** 每次執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」後，狀態仍與已處理資料一致。關鍵論證是：依 prefix sum 或 interval length induction，證明 transition 對所有可能的最後決策做完整且不重複分類。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 prefix、區間長度順序、i-1/j-1、重複計數、字元匹配規則與記憶體 O(nm)。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

先依 substring length 建 palindrome table，再做 prefix DP。`cuts[0]=-1` 讓整段 palindrome 得到零 cuts。

```python
def min_cut(s):
    n = len(s)
    palindrome = [[False] * n for _ in range(n)]
    for length in range(1, n + 1):
        for start in range(n - length + 1):
            end = start + length - 1
            palindrome[start][end] = (
                s[start] == s[end]
                and (length <= 2 or palindrome[start + 1][end - 1])
            )

    cuts = [float("inf")] * (n + 1)
    cuts[0] = -1
    for end in range(n):
        for start in range(end + 1):
            if palindrome[start][end]:
                cuts[end + 1] = min(cuts[end + 1], cuts[start] + 1)
    return cuts[n]
```

- 時間：$O(n^2)$
- 空間：$O(n^2)$

### Follow-up 1：原題直接變形
**問：如何把 palindrome table 空間降到 $O(n)$？**

**答：**以每個中心向外擴張 palindrome，發現 `[left,right]` 時直接更新 prefix cuts；需注意 cuts dependency 的計算順序，或改用 BFS shortest-cut 觀點。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Palindrome Partitioning II》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：先依 substring length 建 palindrome table，再做 prefix DP。cuts[0]=-1 讓整段 palindrome 得到零 cuts。 失效情境包括：若 transition 還依賴未被 state 表示的 context，二維 DP 不足；維度增加可能讓複雜度不可接受。
>
> 替代路線是：壓縮 rolling rows、bitset、Knuth/Monge 類優化、memoization pruning，或改用 automaton/graph。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 transition choice；由 dp[m][n] 逆推 alignment、切點或操作。空間壓縮版本通常需 Hirschberg 或重算。
>
> 套回《Palindrome Partitioning II》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 長序列需限制 table、分塊或近似；增量編輯可考慮局部 recompute，但最壞仍可能影響整張表。
>
> 此外必須把《Palindrome Partitioning II》目前隱含的前提寫成 contract：把字串切成 palindrome substrings，求最少 cuts。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Scramble String

### 題目

字串可遞迴切成兩個非空部分，並選擇是否交換兩部分。判斷 `s1` 能否變成 `s2`。

> [!tip]- 三層提示
> 1. State 是兩段 substring。
> 2. 字元 multiset 不同可立即剪枝。
> 3. 枚舉切點，分成「不交換」與「交換」兩種對應。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 字串可遞迴切成兩個非空部分，並選擇是否交換兩部分。判斷 s1 能否變成 s2。
>
> **核心轉換：** Memoize (a,b)。若相同直接 true，字元頻率不同 false。對每個 cut，檢查：
>
> **主要知識點：** 2D／Interval DP 與結構化子問題。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Scramble String
      │
      ├─ 暴力路線：枚舉所有對齊、切點或操作序列，造成指數分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Memoize (a,b)。若相同直接 true，字元頻率不同 false。對每個 cut，檢查：
      │
Pattern toolbox：dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案
      │
      ├─ 狀態轉移：依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間
      │
      ├─ 永遠成立：填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 字串可遞迴切成兩個非空部分，並選擇是否交換兩部分。判斷 s1 能否變成 s2。
2. **寫出暴力：** 枚舉所有對齊、切點或操作序列，造成指數分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Memoize (a,b)。若相同直接 true，字元頻率不同 false。對每個 cut，檢查：
4. **定義 state 與轉移：** 使用「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」承載上述觀察，再執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：多項式 state 加切點，切片版本常近似 $O(n^4)$；空間：memo 與切片

> [!tip] 一句話記憶
> 先說清楚「dp[i][j] 表示兩個 prefix、某段 interval，或完成特定邊界條件的答案」代表什麼，再說每一步如何「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「填表順序保證所有 dependency 已完成；每格精確涵蓋其定義範圍內的全部合法方案」的 base case。
>
> 2. **維持：** 每次執行「依最後匹配、最後操作或最後切點，把大問題拆成已計算的小矩形／短區間」後，狀態仍與已處理資料一致。關鍵論證是：依 prefix sum 或 interval length induction，證明 transition 對所有可能的最後決策做完整且不重複分類。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：空 prefix、區間長度順序、i-1/j-1、重複計數、字元匹配規則與記憶體 O(nm)。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Memoize `(a,b)`。若相同直接 true，字元頻率不同 false。對每個 cut，檢查：

- `a[:cut] ↔ b[:cut]` 且 suffix 對應。
- `a[:cut] ↔ b[-cut:]` 且其餘對應。

```python
from collections import Counter
from functools import lru_cache

def is_scramble(s1, s2):
    @lru_cache(None)
    def dp(a, b):
        if a == b:
            return True
        if Counter(a) != Counter(b):
            return False
        for cut in range(1, len(a)):
            if dp(a[:cut], b[:cut]) and dp(a[cut:], b[cut:]):
                return True
            if dp(a[:cut], b[-cut:]) and dp(a[cut:], b[:-cut]):
                return True
        return False

    return dp(s1, s2)
```

- 時間：多項式 state 加切點，切片版本常近似 $O(n^4)$
- 空間：memo 與切片

### Follow-up 1：原題直接變形
**問：如何避免反覆建立 substring？**

**答：**state 改為 `(i,j,length)`，用 prefix frequency 快速檢查 multiset；時間與記憶體常數都更好。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Scramble String》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Memoize (a,b)。若相同直接 true，字元頻率不同 false。對每個 cut，檢查： 失效情境包括：若 transition 還依賴未被 state 表示的 context，二維 DP 不足；維度增加可能讓複雜度不可接受。
>
> 替代路線是：壓縮 rolling rows、bitset、Knuth/Monge 類優化、memoization pruning，或改用 automaton/graph。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 transition choice；由 dp[m][n] 逆推 alignment、切點或操作。空間壓縮版本通常需 Hirschberg 或重算。
>
> 套回《Scramble String》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 長序列需限制 table、分塊或近似；增量編輯可考慮局部 recompute，但最壞仍可能影響整張表。
>
> 此外必須把《Scramble String》目前隱含的前提寫成 contract：字串可遞迴切成兩個非空部分，並選擇是否交換兩部分。判斷 s1 能否變成 s2。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 兩序列 state 能解釋 prefix 語意。
- [ ] 知道空 prefix 的 base case。
- [ ] 會辨認「枚舉最後操作」的 interval DP。
- [ ] 會根據 dependency 決定 loop 方向。
