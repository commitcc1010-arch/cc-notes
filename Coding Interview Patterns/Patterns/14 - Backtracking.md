---
title: Backtracking
tags:
  - coding-interview/pattern
  - backtracking
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 14 — Backtracking

[[13 - Graph DAG Union-Find and Shortest Path|← 上一章]] · [[00 - Book Index|目錄]] · [[15 - Greedy|下一章 →]]

> [!abstract] Mental model
> Backtracking 是 DFS 搜尋 decision tree：做選擇、更新狀態、遞迴、復原。效能差異主要來自剪枝、選擇順序與是否消除對稱狀態。

## 通用模板

```python
def backtrack(state):
    if complete(state):
        record(state)
        return
    for choice in choices(state):
        apply(choice)
        backtrack(state)
        undo(choice)
```

---

## 核心題 1：Subsets


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 列出陣列的所有 subsets。
>
> **核心轉換：** 決策樹每個 index 只有選與不選兩條分支；path 表示前 i 個元素的決策，走到 n 時恰得到一個 subset。
>
> **主要知識點：** Backtracking、Constraint Propagation 與搜尋樹剪枝。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Subsets
      │
      ├─ 暴力路線：生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：決策樹每個 index 只有選與不選兩條分支；path 表示前 i 個元素的決策，走到 n 時恰得到一個 subset。
      │
Pattern toolbox：path（已做決定）、剩餘 choices、增量 constraint state
      │
      ├─ 狀態轉移：選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝
      │
      ├─ 永遠成立：進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 列出陣列的所有 subsets。
2. **寫出暴力：** 生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 決策樹每個 index 只有選與不選兩條分支；path 表示前 i 個元素的決策，走到 n 時恰得到一個 subset。
4. **定義 state 與轉移：** 使用「path（已做決定）、剩餘 choices、增量 constraint state」承載上述觀察，再執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「path（已做決定）、剩餘 choices、增量 constraint state」代表什麼，再說每一步如何「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前」的 base case。
>
> 2. **維持：** 每次執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」後，狀態仍與已處理資料一致。關鍵論證是：以決策深度 induction 證明枚舉完整；以 constraint 證明被剪掉的 subtree 不含合法答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複候選、restore 遺漏、可重用元素、答案 copy、終止條件與 exponential recursion depth。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def subsets(nums):
    answer = []
    path = []

    def dfs(index):
        answer.append(path[:])
        for i in range(index, len(nums)):
            path.append(nums[i])
            dfs(i + 1)
            path.pop()

    dfs(0)
    return answer
```

### Follow-up 1：原題直接變形
**問：輸入含重複值，輸出不能重複？**

**答：**先排序；同一 recursion level 中，若 `i > start` 且 `nums[i] == nums[i-1]` 就跳過。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Subsets》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：決策樹每個 index 只有選與不選兩條分支；path 表示前 i 個元素的決策，走到 n 時恰得到一個 subset。 失效情境包括：若重疊子問題很多，純 backtracking 會重算；若剪枝沒有有效 lower bound，最壞情況仍指數。
>
> 替代路線是：加入 memoization/bitmask DP、branch-and-bound、constraint ordering、meet-in-the-middle 或 exact cover。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：path 本身就是 witness；若只求一解可及早停止，若求最優需保存 best_path 與對應 objective。
>
> 套回《Subsets》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production solver 應設 time/node budget、可取消與部分結果；平行搜尋要避免共享 mutable path 並平衡 subtree。
>
> 此外必須把《Subsets》目前隱含的前提寫成 contract：列出陣列的所有 subsets。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Combination Sum

### 題目

候選正整數可重複使用，找所有總和為 target 的組合。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 候選正整數可重複使用，找所有總和為 target 的組合。
>
> **核心轉換：** 依 index 限制後續只能選目前或更右的候選以避免 permutation duplicates；remaining 變負時剪枝，變 0 時收集 path。
>
> **主要知識點：** Backtracking、Constraint Propagation 與搜尋樹剪枝。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Combination Sum
      │
      ├─ 暴力路線：生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：依 index 限制後續只能選目前或更右的候選以避免 permutation duplicates；remaining 變負時剪枝，變 0 時收集 path。
      │
Pattern toolbox：path（已做決定）、剩餘 choices、增量 constraint state
      │
      ├─ 狀態轉移：選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝
      │
      ├─ 永遠成立：進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 候選正整數可重複使用，找所有總和為 target 的組合。
2. **寫出暴力：** 生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 依 index 限制後續只能選目前或更右的候選以避免 permutation duplicates；remaining 變負時剪枝，變 0 時收集 path。
4. **定義 state 與轉移：** 使用「path（已做決定）、剩餘 choices、增量 constraint state」承載上述觀察，再執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「path（已做決定）、剩餘 choices、增量 constraint state」代表什麼，再說每一步如何「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前」的 base case。
>
> 2. **維持：** 每次執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」後，狀態仍與已處理資料一致。關鍵論證是：以決策深度 induction 證明枚舉完整；以 constraint 證明被剪掉的 subtree 不含合法答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複候選、restore 遺漏、可重用元素、答案 copy、終止條件與 exponential recursion depth。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def combination_sum(candidates, target):
    candidates.sort()
    answer, path = [], []

    def dfs(start, remaining):
        if remaining == 0:
            answer.append(path[:])
            return
        for i in range(start, len(candidates)):
            value = candidates[i]
            if value > remaining:
                break
            path.append(value)
            dfs(i, remaining - value)
            path.pop()

    dfs(0, target)
    return answer
```

### Follow-up 1：原題直接變形
**問：每個值最多使用一次且輸入有 duplicate？**

**答：**遞迴改傳 `i+1`，並在同一層跳過相同值。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Combination Sum》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：依 index 限制後續只能選目前或更右的候選以避免 permutation duplicates；remaining 變負時剪枝，變 0 時收集 path。 失效情境包括：若重疊子問題很多，純 backtracking 會重算；若剪枝沒有有效 lower bound，最壞情況仍指數。
>
> 替代路線是：加入 memoization/bitmask DP、branch-and-bound、constraint ordering、meet-in-the-middle 或 exact cover。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：path 本身就是 witness；若只求一解可及早停止，若求最優需保存 best_path 與對應 objective。
>
> 套回《Combination Sum》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production solver 應設 time/node budget、可取消與部分結果；平行搜尋要避免共享 mutable path 並平衡 subtree。
>
> 此外必須把《Combination Sum》目前隱含的前提寫成 contract：候選正整數可重複使用，找所有總和為 target 的組合。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：N-Queens


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 在 n×n 棋盤放 n 個 queens，使任兩者不共享 row、column 或 diagonal。
>
> **核心轉換：** 逐 row 放一個 queen；columns、row-col 與 row+col 三個 set 能 O(1) 判斷衝突，離開分支時必須完整 restore。
>
> **主要知識點：** Backtracking、Constraint Propagation 與搜尋樹剪枝。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：N-Queens
      │
      ├─ 暴力路線：生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：逐 row 放一個 queen；columns、row-col 與 row+col 三個 set 能 O(1) 判斷衝突，離開分支時必須完整 restore。
      │
Pattern toolbox：path（已做決定）、剩餘 choices、增量 constraint state
      │
      ├─ 狀態轉移：選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝
      │
      ├─ 永遠成立：進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 在 n×n 棋盤放 n 個 queens，使任兩者不共享 row、column 或 diagonal。
2. **寫出暴力：** 生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 逐 row 放一個 queen；columns、row-col 與 row+col 三個 set 能 O(1) 判斷衝突，離開分支時必須完整 restore。
4. **定義 state 與轉移：** 使用「path（已做決定）、剩餘 choices、增量 constraint state」承載上述觀察，再執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「path（已做決定）、剩餘 choices、增量 constraint state」代表什麼，再說每一步如何「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前」的 base case。
>
> 2. **維持：** 每次執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」後，狀態仍與已處理資料一致。關鍵論證是：以決策深度 induction 證明枚舉完整；以 constraint 證明被剪掉的 subtree 不含合法答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複候選、restore 遺漏、可重用元素、答案 copy、終止條件與 exponential recursion depth。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def solve_n_queens(n):
    columns, diagonals, anti_diagonals = set(), set(), set()
    board = [["."] * n for _ in range(n)]
    answer = []

    def dfs(row):
        if row == n:
            answer.append(["".join(line) for line in board])
            return
        for col in range(n):
            if col in columns or row - col in diagonals or row + col in anti_diagonals:
                continue
            columns.add(col)
            diagonals.add(row - col)
            anti_diagonals.add(row + col)
            board[row][col] = "Q"
            dfs(row + 1)
            board[row][col] = "."
            columns.remove(col)
            diagonals.remove(row - col)
            anti_diagonals.remove(row + col)

    dfs(0)
    return answer
```

### Follow-up 1：原題直接變形
**問：只求解法數量並追求速度？**

**答：**用 bitmask 表示 columns 與兩類 diagonals；以 `available & -available` 每次取最低可用 bit。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《N-Queens》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：逐 row 放一個 queen；columns、row-col 與 row+col 三個 set 能 O(1) 判斷衝突，離開分支時必須完整 restore。 失效情境包括：若重疊子問題很多，純 backtracking 會重算；若剪枝沒有有效 lower bound，最壞情況仍指數。
>
> 替代路線是：加入 memoization/bitmask DP、branch-and-bound、constraint ordering、meet-in-the-middle 或 exact cover。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：path 本身就是 witness；若只求一解可及早停止，若求最優需保存 best_path 與對應 objective。
>
> 套回《N-Queens》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production solver 應設 time/node budget、可取消與部分結果；平行搜尋要避免共享 mutable path 並平衡 subtree。
>
> 此外必須把《N-Queens》目前隱含的前提寫成 contract：在 n×n 棋盤放 n 個 queens，使任兩者不共享 row、column 或 diagonal。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Sudoku Solver

### 題目

填滿 9×9 Sudoku，使每 row、column、3×3 box 都包含 1–9 且不重複。

> [!tip]- 三層提示
> 1. 維護每 row/column/box 已使用集合。
> 2. 每次不要固定選下一格；選候選最少的空格。
> 3. 這是 MRV（minimum remaining values）剪枝。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 填滿 9×9 Sudoku，使每 row、column、3×3 box 都包含 1–9 且不重複。
>
> **核心轉換：** 初始化三組 sets 與空格列表。每層在尚未處理的空格中找候選數最少者，交換到目前位置；若沒有候選立即回退。
>
> **主要知識點：** Backtracking、Constraint Propagation 與搜尋樹剪枝。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Sudoku Solver
      │
      ├─ 暴力路線：生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：初始化三組 sets 與空格列表。每層在尚未處理的空格中找候選數最少者，交換到目前位置；若沒有候選立即回退。
      │
Pattern toolbox：path（已做決定）、剩餘 choices、增量 constraint state
      │
      ├─ 狀態轉移：選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝
      │
      ├─ 永遠成立：進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 填滿 9×9 Sudoku，使每 row、column、3×3 box 都包含 1–9 且不重複。
2. **寫出暴力：** 生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 初始化三組 sets 與空格列表。每層在尚未處理的空格中找候選數最少者，交換到目前位置；若沒有候選立即回退。
4. **定義 state 與轉移：** 使用「path（已做決定）、剩餘 choices、增量 constraint state」承載上述觀察，再執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「path（已做決定）、剩餘 choices、增量 constraint state」代表什麼，再說每一步如何「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前」的 base case。
>
> 2. **維持：** 每次執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」後，狀態仍與已處理資料一致。關鍵論證是：以決策深度 induction 證明枚舉完整；以 constraint 證明被剪掉的 subtree 不含合法答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複候選、restore 遺漏、可重用元素、答案 copy、終止條件與 exponential recursion depth。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

初始化三組 sets 與空格列表。每層在尚未處理的空格中找候選數最少者，交換到目前位置；若沒有候選立即回退。

```python
def solve_sudoku(board):
    rows = [set() for _ in range(9)]
    cols = [set() for _ in range(9)]
    boxes = [set() for _ in range(9)]
    blanks = []

    for r in range(9):
        for c in range(9):
            if board[r][c] == ".":
                blanks.append((r, c))
            else:
                value = board[r][c]
                rows[r].add(value)
                cols[c].add(value)
                boxes[(r // 3) * 3 + c // 3].add(value)

    digits = set("123456789")

    def dfs(position):
        if position == len(blanks):
            return True

        best = position
        best_choices = None
        for i in range(position, len(blanks)):
            r, c = blanks[i]
            box = (r // 3) * 3 + c // 3
            choices = digits - rows[r] - cols[c] - boxes[box]
            if best_choices is None or len(choices) < len(best_choices):
                best, best_choices = i, choices
            if not best_choices:
                return False

        blanks[position], blanks[best] = blanks[best], blanks[position]
        r, c = blanks[position]
        box = (r // 3) * 3 + c // 3
        choices = digits - rows[r] - cols[c] - boxes[box]

        for value in choices:
            board[r][c] = value
            rows[r].add(value)
            cols[c].add(value)
            boxes[box].add(value)
            if dfs(position + 1):
                return True
            rows[r].remove(value)
            cols[c].remove(value)
            boxes[box].remove(value)
            board[r][c] = "."

        blanks[position], blanks[best] = blanks[best], blanks[position]
        return False

    dfs(0)
```

### Follow-up 1：原題直接變形
**問：如何驗證題目是否有唯一解？**

**答：**不要找到第一組就停止；計數到 2 即可提早終止。0 組無解、1 組唯一、至少 2 組非唯一。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Sudoku Solver》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：初始化三組 sets 與空格列表。每層在尚未處理的空格中找候選數最少者，交換到目前位置；若沒有候選立即回退。 失效情境包括：若重疊子問題很多，純 backtracking 會重算；若剪枝沒有有效 lower bound，最壞情況仍指數。
>
> 替代路線是：加入 memoization/bitmask DP、branch-and-bound、constraint ordering、meet-in-the-middle 或 exact cover。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：path 本身就是 witness；若只求一解可及早停止，若求最優需保存 best_path 與對應 objective。
>
> 套回《Sudoku Solver》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production solver 應設 time/node budget、可取消與部分結果；平行搜尋要避免共享 mutable path 並平衡 subtree。
>
> 此外必須把《Sudoku Solver》目前隱含的前提寫成 contract：填滿 9×9 Sudoku，使每 row、column、3×3 box 都包含 1–9 且不重複。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Expression Add Operators

### 題目

在 digit string 中插入 `+`、`-`、`*`，使運算結果等於 target；數字不可有前導零。

> [!tip]- 三層提示
> 1. 枚舉下一個 operand 的結束位置。
> 2. 保存目前 expression value。
> 3. 為處理乘法 precedence，再保存上一個 term。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 在 digit string 中插入 +、-、，使運算結果等於 target；數字不可有前導零。
>
> **核心轉換：** 若目前值為 value、上一 term 為 last，加入乘法 last current 時，把舊 last 從 value 移除再加入新乘積：
>
> **主要知識點：** Backtracking、Constraint Propagation 與搜尋樹剪枝。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Expression Add Operators
      │
      ├─ 暴力路線：生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：若目前值為 value、上一 term 為 last，加入乘法 last current 時，把舊 last 從 value 移除再加入新乘積：
      │
Pattern toolbox：path（已做決定）、剩餘 choices、增量 constraint state
      │
      ├─ 狀態轉移：選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝
      │
      ├─ 永遠成立：進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 在 digit string 中插入 +、-、，使運算結果等於 target；數字不可有前導零。
2. **寫出暴力：** 生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 若目前值為 value、上一 term 為 last，加入乘法 last current 時，把舊 last 從 value 移除再加入新乘積：
4. **定義 state 與轉移：** 使用「path（已做決定）、剩餘 choices、增量 constraint state」承載上述觀察，再執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「path（已做決定）、剩餘 choices、增量 constraint state」代表什麼，再說每一步如何「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前」的 base case。
>
> 2. **維持：** 每次執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」後，狀態仍與已處理資料一致。關鍵論證是：以決策深度 induction 證明枚舉完整；以 constraint 證明被剪掉的 subtree 不含合法答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複候選、restore 遺漏、可重用元素、答案 copy、終止條件與 exponential recursion depth。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

若目前值為 `value`、上一 term 為 `last`，加入乘法 `last * current` 時，把舊 last 從 value 移除再加入新乘積：

```text
value - last + last * current
```

```python
def add_operators(num, target):
    answer = []

    def dfs(index, expression, value, last):
        if index == len(num):
            if value == target:
                answer.append(expression)
            return

        for end in range(index + 1, len(num) + 1):
            if end > index + 1 and num[index] == "0":
                break
            token = num[index:end]
            current = int(token)
            if index == 0:
                dfs(end, token, current, current)
            else:
                dfs(end, expression + "+" + token, value + current, current)
                dfs(end, expression + "-" + token, value - current, -current)
                dfs(
                    end,
                    expression + "*" + token,
                    value - last + last * current,
                    last * current,
                )

    dfs(0, "", 0, 0)
    return answer
```

### Follow-up 1：原題直接變形
**問：加入除法？**

**答：**仍可保存 last term，但必須先定義整數除法語意、除零與截斷方向。若加入括號，狀態會大幅擴張，較適合 grammar parsing＋DP。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Expression Add Operators》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：若目前值為 value、上一 term 為 last，加入乘法 last current 時，把舊 last 從 value 移除再加入新乘積： 失效情境包括：若重疊子問題很多，純 backtracking 會重算；若剪枝沒有有效 lower bound，最壞情況仍指數。
>
> 替代路線是：加入 memoization/bitmask DP、branch-and-bound、constraint ordering、meet-in-the-middle 或 exact cover。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：path 本身就是 witness；若只求一解可及早停止，若求最優需保存 best_path 與對應 objective。
>
> 套回《Expression Add Operators》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production solver 應設 time/node budget、可取消與部分結果；平行搜尋要避免共享 mutable path 並平衡 subtree。
>
> 此外必須把《Expression Add Operators》目前隱含的前提寫成 contract：在 digit string 中插入 +、-、，使運算結果等於 target；數字不可有前導零。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Remove Invalid Parentheses

### 題目

刪除最少括號使字串合法，回傳所有不同結果；非括號字元不可刪。

> [!tip]- 三層提示
> 1. 先掃一次算出至少要刪多少左、右括號。
> 2. DFS 決定保留或刪除括號。
> 3. 維護 balance，任何 prefix 都不可為負。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 刪除最少括號使字串合法，回傳所有不同結果；非括號字元不可刪。
>
> **核心轉換：** 預先計算 removeleft、removeright。Backtracking 時：
>
> **主要知識點：** Backtracking、Constraint Propagation 與搜尋樹剪枝。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Remove Invalid Parentheses
      │
      ├─ 暴力路線：生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：預先計算 removeleft、removeright。Backtracking 時：
      │
Pattern toolbox：path（已做決定）、剩餘 choices、增量 constraint state
      │
      ├─ 狀態轉移：選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝
      │
      ├─ 永遠成立：進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 刪除最少括號使字串合法，回傳所有不同結果；非括號字元不可刪。
2. **寫出暴力：** 生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 預先計算 removeleft、removeright。Backtracking 時：
4. **定義 state 與轉移：** 使用「path（已做決定）、剩餘 choices、增量 constraint state」承載上述觀察，再執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「path（已做決定）、剩餘 choices、增量 constraint state」代表什麼，再說每一步如何「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前」的 base case。
>
> 2. **維持：** 每次執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」後，狀態仍與已處理資料一致。關鍵論證是：以決策深度 induction 證明枚舉完整；以 constraint 證明被剪掉的 subtree 不含合法答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複候選、restore 遺漏、可重用元素、答案 copy、終止條件與 exponential recursion depth。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

預先計算 `remove_left`、`remove_right`。Backtracking 時：

- 刪除括號會消耗對應 quota。
- 保留 `)` 前需 `balance > 0`。
- 結尾必須 quota 與 balance 全為零。

```python
def remove_invalid_parentheses(s):
    remove_left = remove_right = 0
    for ch in s:
        if ch == "(":
            remove_left += 1
        elif ch == ")":
            if remove_left:
                remove_left -= 1
            else:
                remove_right += 1

    answer = set()

    def dfs(index, left_remove, right_remove, balance, path):
        if index == len(s):
            if left_remove == right_remove == balance == 0:
                answer.add("".join(path))
            return

        ch = s[index]
        if ch == "(" and left_remove:
            dfs(index + 1, left_remove - 1, right_remove, balance, path)
        elif ch == ")" and right_remove:
            dfs(index + 1, left_remove, right_remove - 1, balance, path)

        if ch == "(":
            path.append(ch)
            dfs(index + 1, left_remove, right_remove, balance + 1, path)
            path.pop()
        elif ch == ")":
            if balance > 0:
                path.append(ch)
                dfs(index + 1, left_remove, right_remove, balance - 1, path)
                path.pop()
        else:
            path.append(ch)
            dfs(index + 1, left_remove, right_remove, balance, path)
            path.pop()

    dfs(0, remove_left, remove_right, 0, [])
    return list(answer)
```

### Follow-up 1：原題直接變形
**問：如何避免 set 才去重？**

**答：**在同一 recursion level 對連續相同括號只刪第一個；實作要小心「保留」與「刪除」分支的 index 語意。Set 是較簡潔可靠版本。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Remove Invalid Parentheses》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：預先計算 removeleft、removeright。Backtracking 時： 失效情境包括：若重疊子問題很多，純 backtracking 會重算；若剪枝沒有有效 lower bound，最壞情況仍指數。
>
> 替代路線是：加入 memoization/bitmask DP、branch-and-bound、constraint ordering、meet-in-the-middle 或 exact cover。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：path 本身就是 witness；若只求一解可及早停止，若求最優需保存 best_path 與對應 objective。
>
> 套回《Remove Invalid Parentheses》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production solver 應設 time/node budget、可取消與部分結果；平行搜尋要避免共享 mutable path 並平衡 subtree。
>
> 此外必須把《Remove Invalid Parentheses》目前隱含的前提寫成 contract：刪除最少括號使字串合法，回傳所有不同結果；非括號字元不可刪。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Partition to K Equal Sum Subsets

### 題目

將陣列每個元素恰使用一次，分成 `k` 組且各組總和相同。

> [!tip]- 三層提示
> 1. 總和必須能被 `k` 整除。
> 2. 大數先放可更早失敗。
> 3. 相同 bucket sum 是對稱狀態，只需嘗試一次。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 將陣列每個元素恰使用一次，分成 k 組且各組總和相同。
>
> **核心轉換：** 排序 descending，依序把數放入 buckets。若兩個 buckets 當前 sum 相同，把元素放入其中任一個產生等價狀態，因此跳過重複 sum。
>
> **主要知識點：** Backtracking、Constraint Propagation 與搜尋樹剪枝。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Partition to K Equal Sum Subsets
      │
      ├─ 暴力路線：生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：排序 descending，依序把數放入 buckets。若兩個 buckets 當前 sum 相同，把元素放入其中任一個產生等價狀態，因此跳過重複 sum。
      │
Pattern toolbox：path（已做決定）、剩餘 choices、增量 constraint state
      │
      ├─ 狀態轉移：選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝
      │
      ├─ 永遠成立：進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 將陣列每個元素恰使用一次，分成 k 組且各組總和相同。
2. **寫出暴力：** 生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 排序 descending，依序把數放入 buckets。若兩個 buckets 當前 sum 相同，把元素放入其中任一個產生等價狀態，因此跳過重複 sum。
4. **定義 state 與轉移：** 使用「path（已做決定）、剩餘 choices、增量 constraint state」承載上述觀察，再執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「path（已做決定）、剩餘 choices、增量 constraint state」代表什麼，再說每一步如何「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前」的 base case。
>
> 2. **維持：** 每次執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」後，狀態仍與已處理資料一致。關鍵論證是：以決策深度 induction 證明枚舉完整；以 constraint 證明被剪掉的 subtree 不含合法答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複候選、restore 遺漏、可重用元素、答案 copy、終止條件與 exponential recursion depth。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

排序 descending，依序把數放入 buckets。若兩個 buckets 當前 sum 相同，把元素放入其中任一個產生等價狀態，因此跳過重複 sum。

```python
def can_partition_k_subsets(nums, k):
    total = sum(nums)
    if total % k:
        return False
    target = total // k
    nums.sort(reverse=True)
    if nums[0] > target:
        return False

    buckets = [0] * k

    def dfs(index):
        if index == len(nums):
            return True
        value = nums[index]
        tried = set()
        for i in range(k):
            if buckets[i] in tried:
                continue
            if buckets[i] + value <= target:
                tried.add(buckets[i])
                buckets[i] += value
                if dfs(index + 1):
                    return True
                buckets[i] -= value
            if buckets[i] == 0:
                break
        return False

    return dfs(0)
```

### Follow-up 1：原題直接變形
**問：`n <= 16` 時有什麼替代解？**

**答：**Bitmask DP。`dp[mask]` 保存目前最後一組已累積到 target 的餘數；從已可達 mask 加入未使用元素，狀態數 $O(2^n)$。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Partition to K Equal Sum Subsets》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：排序 descending，依序把數放入 buckets。若兩個 buckets 當前 sum 相同，把元素放入其中任一個產生等價狀態，因此跳過重複 sum。 失效情境包括：若重疊子問題很多，純 backtracking 會重算；若剪枝沒有有效 lower bound，最壞情況仍指數。
>
> 替代路線是：加入 memoization/bitmask DP、branch-and-bound、constraint ordering、meet-in-the-middle 或 exact cover。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：path 本身就是 witness；若只求一解可及早停止，若求最優需保存 best_path 與對應 objective。
>
> 套回《Partition to K Equal Sum Subsets》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production solver 應設 time/node budget、可取消與部分結果；平行搜尋要避免共享 mutable path 並平衡 subtree。
>
> 此外必須把《Partition to K Equal Sum Subsets》目前隱含的前提寫成 contract：將陣列每個元素恰使用一次，分成 k 組且各組總和相同。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Unique Paths III

### 題目

網格有起點、終點、空格與障礙；從起點到終點，必須恰好走過每個非障礙格一次。計算路徑數。

> [!tip]- 三層提示
> 1. 計算還剩多少可走格。
> 2. DFS 時把目前格標記為 visited。
> 3. 到終點時，只有剩餘格數恰為 1 才算。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 網格有起點、終點、空格與障礙；從起點到終點，必須恰好走過每個非障礙格一次。計算路徑數。
>
> **核心轉換：** 這是 Hamiltonian-path 類 backtracking。remaining 包含目前尚未走訪的非障礙格；進入鄰居時減一。
>
> **主要知識點：** Backtracking、Constraint Propagation 與搜尋樹剪枝。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Unique Paths III
      │
      ├─ 暴力路線：生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支
      │
      ▼  找出本題最關鍵的轉換
核心觀察：這是 Hamiltonian-path 類 backtracking。remaining 包含目前尚未走訪的非障礙格；進入鄰居時減一。
      │
Pattern toolbox：path（已做決定）、剩餘 choices、增量 constraint state
      │
      ├─ 狀態轉移：選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝
      │
      ├─ 永遠成立：進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 網格有起點、終點、空格與障礙；從起點到終點，必須恰好走過每個非障礙格一次。計算路徑數。
2. **寫出暴力：** 生成所有排列／子集後才檢查是否合法，浪費大量必然失敗的分支。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 這是 Hamiltonian-path 類 backtracking。remaining 包含目前尚未走訪的非障礙格；進入鄰居時減一。
4. **定義 state 與轉移：** 使用「path（已做決定）、剩餘 choices、增量 constraint state」承載上述觀察，再執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「path（已做決定）、剩餘 choices、增量 constraint state」代表什麼，再說每一步如何「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「進入 dfs 時，path 合法且 state 精確描述其影響；離開分支後狀態恢復到呼叫前」的 base case。
>
> 2. **維持：** 每次執行「選一個 choice → 更新狀態 → 遞迴 → 完整復原；一旦不可能完成就立即剪枝」後，狀態仍與已處理資料一致。關鍵論證是：以決策深度 induction 證明枚舉完整；以 constraint 證明被剪掉的 subtree 不含合法答案。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複候選、restore 遺漏、可重用元素、答案 copy、終止條件與 exponential recursion depth。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

這是 Hamiltonian-path 類 backtracking。`remaining` 包含目前尚未走訪的非障礙格；進入鄰居時減一。

```python
def unique_paths_iii(grid):
    rows, cols = len(grid), len(grid[0])
    remaining = 0
    start = None
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != -1:
                remaining += 1
            if grid[r][c] == 1:
                start = (r, c)

    def dfs(r, c, left):
        if grid[r][c] == 2:
            return 1 if left == 1 else 0

        original = grid[r][c]
        grid[r][c] = -1
        paths = 0
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != -1:
                paths += dfs(nr, nc, left - 1)
        grid[r][c] = original
        return paths

    return dfs(start[0], start[1], remaining)
```

### Follow-up 1：原題直接變形
**問：格子數不超過 20，如何用 memo？**

**答：**把 visited cells 壓成 bitmask，memo state 為 `(position,mask)`；轉移到未使用鄰居。時間約 $O(V2^V)$，可避免不同路徑到同狀態的重算。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Unique Paths III》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：這是 Hamiltonian-path 類 backtracking。remaining 包含目前尚未走訪的非障礙格；進入鄰居時減一。 失效情境包括：若重疊子問題很多，純 backtracking 會重算；若剪枝沒有有效 lower bound，最壞情況仍指數。
>
> 替代路線是：加入 memoization/bitmask DP、branch-and-bound、constraint ordering、meet-in-the-middle 或 exact cover。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：path 本身就是 witness；若只求一解可及早停止，若求最優需保存 best_path 與對應 objective。
>
> 套回《Unique Paths III》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Production solver 應設 time/node budget、可取消與部分結果；平行搜尋要避免共享 mutable path 並平衡 subtree。
>
> 此外必須把《Unique Paths III》目前隱含的前提寫成 contract：網格有起點、終點、空格與障礙；從起點到終點，必須恰好走過每個非障礙格一次。計算路徑數。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 每個遞迴都有明確 choice、apply、undo。
- [ ] 會排序或使用 MRV 讓失敗提早。
- [ ] 能消除對稱狀態。
- [ ] 知道輸出大小本身可能指數成長。
