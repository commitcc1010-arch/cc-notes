---
title: Matrix Simulation and Parsing
tags:
  - coding-interview/pattern
  - matrix
  - simulation
  - parsing
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 20 — Matrix, Simulation and Parsing

[[19 - Data Structure Design|← 上一章]] · [[00 - Book Index|目錄]]

> [!abstract] Mental model
> Implementation-heavy 題不一定需要新演算法。先把狀態、方向、邊界與更新順序明文化；若規則有 precedence 或巢狀結構，先寫 grammar 再寫 parser。

---

## 核心題 1：Spiral Matrix


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 依順時針 spiral order 輸出矩陣所有元素。
>
> **核心轉換：** 維護 top/bottom/left/right 四邊界；走完一條邊立即內縮，走 bottom 與 left 前重新檢查邊界避免重複。
>
> **主要知識點：** Matrix Simulation、Parser 與精確狀態轉移。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Spiral Matrix
      │
      ├─ 暴力路線：直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence
      │
      ▼  找出本題最關鍵的轉換
核心觀察：維護 top/bottom/left/right 四邊界；走完一條邊立即內縮，走 bottom 與 left 前重新檢查邊界避免重複。
      │
Pattern toolbox：明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state
      │
      ├─ 狀態轉移：把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token
      │
      ├─ 永遠成立：每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 依順時針 spiral order 輸出矩陣所有元素。
2. **寫出暴力：** 直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 維護 top/bottom/left/right 四邊界；走完一條邊立即內縮，走 bottom 與 left 前重新檢查邊界避免重複。
4. **定義 state 與轉移：** 使用「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」承載上述觀察，再執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」代表什麼，再說每一步如何「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態」的 base case。
>
> 2. **維持：** 每次執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」後，狀態仍與已處理資料一致。關鍵論證是：用 step induction 證明每次 transition 等同題目規則；parser 依 grammar 結構證明 precedence 與 associativity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：矩陣空維度、四個邊界交錯、同步／非同步更新、visited、unary minus、空白、括號與終止條件。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def spiral_order(matrix):
    answer = []
    top, bottom = 0, len(matrix) - 1
    left, right = 0, len(matrix[0]) - 1

    while top <= bottom and left <= right:
        for c in range(left, right + 1):
            answer.append(matrix[top][c])
        top += 1

        for r in range(top, bottom + 1):
            answer.append(matrix[r][right])
        right -= 1

        if top <= bottom:
            for c in range(right, left - 1, -1):
                answer.append(matrix[bottom][c])
            bottom -= 1

        if left <= right:
            for r in range(bottom, top - 1, -1):
                answer.append(matrix[r][left])
            left += 1
    return answer
```

### Follow-up 1：原題直接變形
**問：為什麼下邊與左邊需要額外 boundary check？**

**答：**走完上、右邊後，單 row 或單 column 可能已被完全消耗；沒有檢查會重複輸出。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Spiral Matrix》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：維護 top/bottom/left/right 四邊界；走完一條邊立即內縮，走 bottom 與 left 前重新檢查邊界避免重複。 失效情境包括：規則具有長距離互動或需要回溯時，單次局部 simulation 不夠；grammar 模糊時 stack parser 也可能誤解。
>
> 替代路線是：採 double buffering、event queue、state graph search、recursive descent、Pratt parser 或建立 AST。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：記錄每步 action/board diff；parser 建 AST。這些 witness 能重播 simulation 或顯示完整運算順序。
>
> 套回《Spiral Matrix》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 不可信輸入要限制步數、矩陣大小與 parser depth；simulation loop 必須證明終止，並支援 deterministic replay。
>
> 此外必須把《Spiral Matrix》目前隱含的前提寫成 contract：依順時針 spiral order 輸出矩陣所有元素。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Set Matrix Zeroes

### 題目

若某格為零，把其整 row 與 column 設為零，要求 $O(1)$ 額外空間。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 若某格為零，把其整 row 與 column 設為零，要求 $O(1)$ 額外空間。
>
> **核心轉換：** 用第一 row/column 當 marker 儲存哪些列欄需清零，另以兩個 flag 保存第一 row/column 自己原本是否含 0。
>
> **主要知識點：** Matrix Simulation、Parser 與精確狀態轉移。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Set Matrix Zeroes
      │
      ├─ 暴力路線：直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence
      │
      ▼  找出本題最關鍵的轉換
核心觀察：用第一 row/column 當 marker 儲存哪些列欄需清零，另以兩個 flag 保存第一 row/column 自己原本是否含 0。
      │
Pattern toolbox：明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state
      │
      ├─ 狀態轉移：把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token
      │
      ├─ 永遠成立：每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 若某格為零，把其整 row 與 column 設為零，要求 $O(1)$ 額外空間。
2. **寫出暴力：** 直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 用第一 row/column 當 marker 儲存哪些列欄需清零，另以兩個 flag 保存第一 row/column 自己原本是否含 0。
4. **定義 state 與轉移：** 使用「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」承載上述觀察，再執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」代表什麼，再說每一步如何「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態」的 base case。
>
> 2. **維持：** 每次執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」後，狀態仍與已處理資料一致。關鍵論證是：用 step induction 證明每次 transition 等同題目規則；parser 依 grammar 結構證明 precedence 與 associativity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：矩陣空維度、四個邊界交錯、同步／非同步更新、visited、unary minus、空白、括號與終止條件。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def set_zeroes(matrix):
    rows, cols = len(matrix), len(matrix[0])
    first_row_zero = any(matrix[0][c] == 0 for c in range(cols))
    first_col_zero = any(matrix[r][0] == 0 for r in range(rows))

    for r in range(1, rows):
        for c in range(1, cols):
            if matrix[r][c] == 0:
                matrix[r][0] = 0
                matrix[0][c] = 0

    for r in range(1, rows):
        for c in range(1, cols):
            if matrix[r][0] == 0 or matrix[0][c] == 0:
                matrix[r][c] = 0

    if first_row_zero:
        for c in range(cols):
            matrix[0][c] = 0
    if first_col_zero:
        for r in range(rows):
            matrix[r][0] = 0
```

### Follow-up 1：原題直接變形
**問：為什麼 first row/column 要獨立 flag？**

**答：**它們同時被借來當 marker，本身原本是否含零的資訊會被後續標記覆蓋。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Set Matrix Zeroes》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：用第一 row/column 當 marker 儲存哪些列欄需清零，另以兩個 flag 保存第一 row/column 自己原本是否含 0。 失效情境包括：規則具有長距離互動或需要回溯時，單次局部 simulation 不夠；grammar 模糊時 stack parser 也可能誤解。
>
> 替代路線是：採 double buffering、event queue、state graph search、recursive descent、Pratt parser 或建立 AST。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：記錄每步 action/board diff；parser 建 AST。這些 witness 能重播 simulation 或顯示完整運算順序。
>
> 套回《Set Matrix Zeroes》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 不可信輸入要限制步數、矩陣大小與 parser depth；simulation loop 必須證明終止，並支援 deterministic replay。
>
> 此外必須把《Set Matrix Zeroes》目前隱含的前提寫成 contract：若某格為零，把其整 row 與 column 設為零，要求 $O(1)$ 額外空間。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Rotate Image

### 題目

將 `n×n` matrix 原地順時針旋轉 90 度。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 將 n×n matrix 原地順時針旋轉 90 度。
>
> **核心轉換：** 先沿主對角線 transpose，再反轉每一 row；座標 (r,c) 因而映射到 (c,n-1-r)，且每步都可原地完成。
>
> **主要知識點：** Matrix Simulation、Parser 與精確狀態轉移。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Rotate Image
      │
      ├─ 暴力路線：直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence
      │
      ▼  找出本題最關鍵的轉換
核心觀察：先沿主對角線 transpose，再反轉每一 row；座標 (r,c) 因而映射到 (c,n-1-r)，且每步都可原地完成。
      │
Pattern toolbox：明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state
      │
      ├─ 狀態轉移：把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token
      │
      ├─ 永遠成立：每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 將 n×n matrix 原地順時針旋轉 90 度。
2. **寫出暴力：** 直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 先沿主對角線 transpose，再反轉每一 row；座標 (r,c) 因而映射到 (c,n-1-r)，且每步都可原地完成。
4. **定義 state 與轉移：** 使用「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」承載上述觀察，再執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」代表什麼，再說每一步如何「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態」的 base case。
>
> 2. **維持：** 每次執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」後，狀態仍與已處理資料一致。關鍵論證是：用 step induction 證明每次 transition 等同題目規則；parser 依 grammar 結構證明 precedence 與 associativity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：矩陣空維度、四個邊界交錯、同步／非同步更新、visited、unary minus、空白、括號與終止條件。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def rotate(matrix):
    n = len(matrix)
    for r in range(n):
        for c in range(r + 1, n):
            matrix[r][c], matrix[c][r] = matrix[c][r], matrix[r][c]
    for row in matrix:
        row.reverse()
```

**推導：**沿主對角線 transpose，再水平反轉。

### Follow-up 1：原題直接變形
**問：逆時針 90 度？**

**答：**transpose 後反轉 row 的順序；或先水平反轉再 transpose。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Rotate Image》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：先沿主對角線 transpose，再反轉每一 row；座標 (r,c) 因而映射到 (c,n-1-r)，且每步都可原地完成。 失效情境包括：規則具有長距離互動或需要回溯時，單次局部 simulation 不夠；grammar 模糊時 stack parser 也可能誤解。
>
> 替代路線是：採 double buffering、event queue、state graph search、recursive descent、Pratt parser 或建立 AST。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：記錄每步 action/board diff；parser 建 AST。這些 witness 能重播 simulation 或顯示完整運算順序。
>
> 套回《Rotate Image》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 不可信輸入要限制步數、矩陣大小與 parser depth；simulation loop 必須證明終止，並支援 deterministic replay。
>
> 此外必須把《Rotate Image》目前隱含的前提寫成 contract：將 n×n matrix 原地順時針旋轉 90 度。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Basic Calculator III

### 題目

計算含整數、空白、`+ - * /` 與括號的運算式；除法向零截斷。

> [!tip]- 三層提示
> 1. 寫 grammar：`expr -> term (+/- term)*`。
> 2. `term -> factor (*// factor)*`。
> 3. `factor` 是數字、括號 expression，並處理 unary sign。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 計算含整數、空白、+ - / 與括號的運算式；除法向零截斷。
>
> **核心轉換：** Recursive descent 讓函式結構直接對應 precedence。共享 index 指向下一個尚未消費字元。
>
> **主要知識點：** Matrix Simulation、Parser 與精確狀態轉移。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Basic Calculator III
      │
      ├─ 暴力路線：直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Recursive descent 讓函式結構直接對應 precedence。共享 index 指向下一個尚未消費字元。
      │
Pattern toolbox：明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state
      │
      ├─ 狀態轉移：把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token
      │
      ├─ 永遠成立：每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 計算含整數、空白、+ - / 與括號的運算式；除法向零截斷。
2. **寫出暴力：** 直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Recursive descent 讓函式結構直接對應 precedence。共享 index 指向下一個尚未消費字元。
4. **定義 state 與轉移：** 使用「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」承載上述觀察，再執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(parenthesis\ depth)$

> [!tip] 一句話記憶
> 先說清楚「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」代表什麼，再說每一步如何「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態」的 base case。
>
> 2. **維持：** 每次執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」後，狀態仍與已處理資料一致。關鍵論證是：用 step induction 證明每次 transition 等同題目規則；parser 依 grammar 結構證明 precedence 與 associativity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：矩陣空維度、四個邊界交錯、同步／非同步更新、visited、unary minus、空白、括號與終止條件。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Recursive descent 讓函式結構直接對應 precedence。共享 index 指向下一個尚未消費字元。

```python
def calculate(expression):
    index = 0

    def skip_spaces():
        nonlocal index
        while index < len(expression) and expression[index] == " ":
            index += 1

    def divide_zero(a, b):
        value = abs(a) // abs(b)
        return -value if (a < 0) != (b < 0) else value

    def parse_factor():
        nonlocal index
        skip_spaces()
        sign = 1
        while index < len(expression) and expression[index] in "+-":
            if expression[index] == "-":
                sign *= -1
            index += 1
            skip_spaces()

        if expression[index] == "(":
            index += 1
            value = parse_expression()
            skip_spaces()
            index += 1
            return sign * value

        value = 0
        while index < len(expression) and expression[index].isdigit():
            value = value * 10 + int(expression[index])
            index += 1
        return sign * value

    def parse_term():
        nonlocal index
        value = parse_factor()
        while True:
            skip_spaces()
            if index >= len(expression) or expression[index] not in "*/":
                return value
            operator = expression[index]
            index += 1
            right = parse_factor()
            value = value * right if operator == "*" else divide_zero(value, right)

    def parse_expression():
        nonlocal index
        value = parse_term()
        while True:
            skip_spaces()
            if index >= len(expression) or expression[index] not in "+-":
                return value
            operator = expression[index]
            index += 1
            right = parse_term()
            value = value + right if operator == "+" else value - right

    return parse_expression()
```

- 時間：$O(n)$
- 空間：$O(parenthesis\ depth)$

### Follow-up 1：原題直接變形
**問：加入變數與 assignment？**

**答：**Lexer 需辨識 identifier；parser 增加 assignment rule，evaluation environment 用 map 保存變數。若要先建 AST，再把 parse 與 evaluate 分離。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Basic Calculator III》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Recursive descent 讓函式結構直接對應 precedence。共享 index 指向下一個尚未消費字元。 失效情境包括：規則具有長距離互動或需要回溯時，單次局部 simulation 不夠；grammar 模糊時 stack parser 也可能誤解。
>
> 替代路線是：採 double buffering、event queue、state graph search、recursive descent、Pratt parser 或建立 AST。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：記錄每步 action/board diff；parser 建 AST。這些 witness 能重播 simulation 或顯示完整運算順序。
>
> 套回《Basic Calculator III》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 不可信輸入要限制步數、矩陣大小與 parser depth；simulation loop 必須證明終止，並支援 deterministic replay。
>
> 此外必須把《Basic Calculator III》目前隱含的前提寫成 contract：計算含整數、空白、+ - / 與括號的運算式；除法向零截斷。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Robot Room Cleaner

### 題目

你只能透過 `move()`、`turnLeft()`、`turnRight()`、`clean()` 控制未知房間中的機器人。清理所有可達格。

> [!tip]- 三層提示
> 1. 自己建立相對座標系與 visited。
> 2. DFS 四個方向。
> 3. 從 child 回來後，必須讓 robot 回到原格且恢復原方向。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 你只能透過 move()、turnLeft()、turnRight()、clean() 控制未知房間中的機器人。清理所有可達格。
>
> **核心轉換：** goback 轉 180 度、前進、再轉 180 度。每層固定嘗試四次：若前方可走且未訪問則遞迴；之後右轉，保持 direction index 與實體方向同步。
>
> **主要知識點：** Matrix Simulation、Parser 與精確狀態轉移。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Robot Room Cleaner
      │
      ├─ 暴力路線：直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence
      │
      ▼  找出本題最關鍵的轉換
核心觀察：goback 轉 180 度、前進、再轉 180 度。每層固定嘗試四次：若前方可走且未訪問則遞迴；之後右轉，保持 direction index 與實體方向同步。
      │
Pattern toolbox：明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state
      │
      ├─ 狀態轉移：把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token
      │
      ├─ 永遠成立：每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 你只能透過 move()、turnLeft()、turnRight()、clean() 控制未知房間中的機器人。清理所有可達格。
2. **寫出暴力：** 直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** goback 轉 180 度、前進、再轉 180 度。每層固定嘗試四次：若前方可走且未訪問則遞迴；之後右轉，保持 direction index 與實體方向同步。
4. **定義 state 與轉移：** 使用「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」承載上述觀察，再執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」代表什麼，再說每一步如何「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態」的 base case。
>
> 2. **維持：** 每次執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」後，狀態仍與已處理資料一致。關鍵論證是：用 step induction 證明每次 transition 等同題目規則；parser 依 grammar 結構證明 precedence 與 associativity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：矩陣空維度、四個邊界交錯、同步／非同步更新、visited、unary minus、空白、括號與終止條件。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

`go_back` 轉 180 度、前進、再轉 180 度。每層固定嘗試四次：若前方可走且未訪問則遞迴；之後右轉，保持 direction index 與實體方向同步。

```python
def clean_room(robot):
    directions = [(-1, 0), (0, 1), (1, 0), (0, -1)]
    visited = set()

    def go_back():
        robot.turnRight()
        robot.turnRight()
        robot.move()
        robot.turnRight()
        robot.turnRight()

    def dfs(r, c, direction):
        visited.add((r, c))
        robot.clean()

        for offset in range(4):
            next_direction = (direction + offset) % 4
            dr, dc = directions[next_direction]
            nr, nc = r + dr, c + dc
            if (nr, nc) not in visited and robot.move():
                dfs(nr, nc, next_direction)
                go_back()
            robot.turnRight()

    dfs(0, 0, 0)
```

### Follow-up 1：原題直接變形
**問：move 有耗電成本，如何降低重複路徑？**

**答：**未知地圖下首次探索仍需 traversal；可先探索並建圖，再在已知 graph 上規劃較短清掃 route。這可能轉成 graph coverage／route optimization。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Robot Room Cleaner》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：goback 轉 180 度、前進、再轉 180 度。每層固定嘗試四次：若前方可走且未訪問則遞迴；之後右轉，保持 direction index 與實體方向同步。 失效情境包括：規則具有長距離互動或需要回溯時，單次局部 simulation 不夠；grammar 模糊時 stack parser 也可能誤解。
>
> 替代路線是：採 double buffering、event queue、state graph search、recursive descent、Pratt parser 或建立 AST。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：記錄每步 action/board diff；parser 建 AST。這些 witness 能重播 simulation 或顯示完整運算順序。
>
> 套回《Robot Room Cleaner》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 不可信輸入要限制步數、矩陣大小與 parser depth；simulation loop 必須證明終止，並支援 deterministic replay。
>
> 此外必須把《Robot Room Cleaner》目前隱含的前提寫成 contract：你只能透過 move()、turnLeft()、turnRight()、clean() 控制未知房間中的機器人。清理所有可達格。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Candy Crush

### 題目

在 board 中，水平或垂直至少三個相同 candy 同時消除；上方 candy 落下。重複直到穩定。

> [!tip]- 三層提示
> 1. 同一輪所有 match 必須同時標記，不能找到就立即清除。
> 2. 用負號標記待消除，同時保留原 candy identity。
> 3. 每 column 由下向上 compact 非零值。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 在 board 中，水平或垂直至少三個相同 candy 同時消除；上方 candy 落下。重複直到穩定。
>
> **核心轉換：** 掃描 horizontal 與 vertical triples；一旦發現，延伸整段並標負。使用 abs 讓已標記 candy 仍可參與另一方向 match。然後 gravity。
>
> **主要知識點：** Matrix Simulation、Parser 與精確狀態轉移。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Candy Crush
      │
      ├─ 暴力路線：直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence
      │
      ▼  找出本題最關鍵的轉換
核心觀察：掃描 horizontal 與 vertical triples；一旦發現，延伸整段並標負。使用 abs 讓已標記 candy 仍可參與另一方向 match。然後 gravity。
      │
Pattern toolbox：明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state
      │
      ├─ 狀態轉移：把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token
      │
      ├─ 永遠成立：每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 在 board 中，水平或垂直至少三個相同 candy 同時消除；上方 candy 落下。重複直到穩定。
2. **寫出暴力：** 直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 掃描 horizontal 與 vertical triples；一旦發現，延伸整段並標負。使用 abs 讓已標記 candy 仍可參與另一方向 match。然後 gravity。
4. **定義 state 與轉移：** 使用「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」承載上述觀察，再執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」代表什麼，再說每一步如何「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態」的 base case。
>
> 2. **維持：** 每次執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」後，狀態仍與已處理資料一致。關鍵論證是：用 step induction 證明每次 transition 等同題目規則；parser 依 grammar 結構證明 precedence 與 associativity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：矩陣空維度、四個邊界交錯、同步／非同步更新、visited、unary minus、空白、括號與終止條件。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

掃描 horizontal 與 vertical triples；一旦發現，延伸整段並標負。使用 `abs` 讓已標記 candy 仍可參與另一方向 match。然後 gravity。

```python
def candy_crush(board):
    rows, cols = len(board), len(board[0])

    while True:
        crush = False
        for r in range(rows):
            c = 0
            while c < cols:
                end = c + 1
                while end < cols and abs(board[r][end]) == abs(board[r][c]):
                    end += 1
                if board[r][c] != 0 and end - c >= 3:
                    crush = True
                    for x in range(c, end):
                        board[r][x] = -abs(board[r][x])
                c = end

        for c in range(cols):
            r = 0
            while r < rows:
                end = r + 1
                while end < rows and abs(board[end][c]) == abs(board[r][c]):
                    end += 1
                if board[r][c] != 0 and end - r >= 3:
                    crush = True
                    for x in range(r, end):
                        board[x][c] = -abs(board[x][c])
                r = end

        if not crush:
            return board

        for c in range(cols):
            write = rows - 1
            for r in range(rows - 1, -1, -1):
                if board[r][c] > 0:
                    board[write][c] = board[r][c]
                    write -= 1
            while write >= 0:
                board[write][c] = 0
                write -= 1
```

### Follow-up 1：原題直接變形
**問：為什麼一定會終止？**

**答：**每輪若不穩定，至少消除三個 candy，非零 candy 總數嚴格下降；因此最多有限輪。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Candy Crush》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：掃描 horizontal 與 vertical triples；一旦發現，延伸整段並標負。使用 abs 讓已標記 candy 仍可參與另一方向 match。然後 gravity。 失效情境包括：規則具有長距離互動或需要回溯時，單次局部 simulation 不夠；grammar 模糊時 stack parser 也可能誤解。
>
> 替代路線是：採 double buffering、event queue、state graph search、recursive descent、Pratt parser 或建立 AST。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：記錄每步 action/board diff；parser 建 AST。這些 witness 能重播 simulation 或顯示完整運算順序。
>
> 套回《Candy Crush》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 不可信輸入要限制步數、矩陣大小與 parser depth；simulation loop 必須證明終止，並支援 deterministic replay。
>
> 此外必須把《Candy Crush》目前隱含的前提寫成 contract：在 board 中，水平或垂直至少三個相同 candy 同時消除；上方 candy 落下。重複直到穩定。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Contain Virus

### 題目

每天選一個感染區域建牆隔離；選擇下一天會感染最多未感染格的區域。其他區域向四周擴散。求總牆數。

> [!tip]- 三層提示
> 1. 每天先找所有 infected connected components。
> 2. 對每個 component 同時計算 frontier set 與需要的 wall edges。
> 3. 隔離 frontier 最大者，其他 components 才擴散。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每天選一個感染區域建牆隔離；選擇下一天會感染最多未感染格的區域。其他區域向四周擴散。求總牆數。
>
> **核心轉換：** Frontier 使用 set，因為同一未感染格可能接觸多個 infected cells；walls 則按 boundary edge 計數，不能去重。
>
> **主要知識點：** Matrix Simulation、Parser 與精確狀態轉移。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Contain Virus
      │
      ├─ 暴力路線：直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Frontier 使用 set，因為同一未感染格可能接觸多個 infected cells；walls 則按 boundary edge 計數，不能去重。
      │
Pattern toolbox：明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state
      │
      ├─ 狀態轉移：把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token
      │
      ├─ 永遠成立：每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每天選一個感染區域建牆隔離；選擇下一天會感染最多未感染格的區域。其他區域向四周擴散。求總牆數。
2. **寫出暴力：** 直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Frontier 使用 set，因為同一未感染格可能接觸多個 infected cells；walls 則按 boundary edge 計數，不能去重。
4. **定義 state 與轉移：** 使用「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」承載上述觀察，再執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」代表什麼，再說每一步如何「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態」的 base case。
>
> 2. **維持：** 每次執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」後，狀態仍與已處理資料一致。關鍵論證是：用 step induction 證明每次 transition 等同題目規則；parser 依 grammar 結構證明 precedence 與 associativity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：矩陣空維度、四個邊界交錯、同步／非同步更新、visited、unary minus、空白、括號與終止條件。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Frontier 使用 set，因為同一未感染格可能接觸多個 infected cells；walls 則按 boundary edge 計數，不能去重。

```python
def contain_virus(grid):
    rows, cols = len(grid), len(grid[0])
    total_walls = 0

    while True:
        seen = set()
        regions = []
        frontiers = []
        walls = []

        for start_r in range(rows):
            for start_c in range(cols):
                if grid[start_r][start_c] != 1 or (start_r, start_c) in seen:
                    continue
                stack = [(start_r, start_c)]
                seen.add((start_r, start_c))
                region = []
                frontier = set()
                wall_count = 0

                while stack:
                    r, c = stack.pop()
                    region.append((r, c))
                    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nr, nc = r + dr, c + dc
                        if not (0 <= nr < rows and 0 <= nc < cols):
                            continue
                        if grid[nr][nc] == 0:
                            frontier.add((nr, nc))
                            wall_count += 1
                        elif grid[nr][nc] == 1 and (nr, nc) not in seen:
                            seen.add((nr, nc))
                            stack.append((nr, nc))

                regions.append(region)
                frontiers.append(frontier)
                walls.append(wall_count)

        if not regions:
            break
        quarantine = max(range(len(regions)), key=lambda i: len(frontiers[i]))
        if not frontiers[quarantine]:
            break

        total_walls += walls[quarantine]
        for r, c in regions[quarantine]:
            grid[r][c] = -1
        for i, frontier in enumerate(frontiers):
            if i != quarantine:
                for r, c in frontier:
                    grid[r][c] = 1

    return total_walls
```

### Follow-up 1：原題直接變形
**問：若每天可以隔離兩個區域，選 frontier 最大的兩個一定最優嗎？**

**答：**不一定。兩區 frontier 可能重疊，隔離效益不是獨立相加；需依新目標做組合選擇或最佳化，原題 greedy 規則是 specification，不是自行證明的最優策略。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Contain Virus》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Frontier 使用 set，因為同一未感染格可能接觸多個 infected cells；walls 則按 boundary edge 計數，不能去重。 失效情境包括：規則具有長距離互動或需要回溯時，單次局部 simulation 不夠；grammar 模糊時 stack parser 也可能誤解。
>
> 替代路線是：採 double buffering、event queue、state graph search、recursive descent、Pratt parser 或建立 AST。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：記錄每步 action/board diff；parser 建 AST。這些 witness 能重播 simulation 或顯示完整運算順序。
>
> 套回《Contain Virus》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 不可信輸入要限制步數、矩陣大小與 parser depth；simulation loop 必須證明終止，並支援 deterministic replay。
>
> 此外必須把《Contain Virus》目前隱含的前提寫成 contract：每天選一個感染區域建牆隔離；選擇下一天會感染最多未感染格的區域。其他區域向四周擴散。求總牆數。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：The Maze III

### 題目

球朝一個方向會一直滾到牆或洞。找從起點進洞的最短距離；距離相同取 lexicographically smallest directions string。

> [!tip]- 三層提示
> 1. 每次 action 的 edge weight 是實際滾動格數。
> 2. 使用 Dijkstra，不是普通 BFS。
> 3. Heap key 同時放 `(distance,path)`，自然處理 tie。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 球朝一個方向會一直滾到牆或洞。找從起點進洞的最短距離；距離相同取 lexicographically smallest directions string。
>
> **核心轉換：** 從停靠點向四方向模擬滾動，遇洞立即停。best[(r,c)] 保存目前最佳 (distance,path)；heap 依 tuple 順序選最短且字典序最小 state。
>
> **主要知識點：** Matrix Simulation、Parser 與精確狀態轉移。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：The Maze III
      │
      ├─ 暴力路線：直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence
      │
      ▼  找出本題最關鍵的轉換
核心觀察：從停靠點向四方向模擬滾動，遇洞立即停。best[(r,c)] 保存目前最佳 (distance,path)；heap 依 tuple 順序選最短且字典序最小 state。
      │
Pattern toolbox：明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state
      │
      ├─ 狀態轉移：把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token
      │
      ├─ 永遠成立：每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 球朝一個方向會一直滾到牆或洞。找從起點進洞的最短距離；距離相同取 lexicographically smallest directions string。
2. **寫出暴力：** 直接照直覺修改世界狀態，導致同一輪更新彼此干擾，或在 parser 中混合所有 precedence。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 從停靠點向四方向模擬滾動，遇洞立即停。best[(r,c)] 保存目前最佳 (distance,path)；heap 依 tuple 順序選最短且字典序最小 state。
4. **定義 state 與轉移：** 使用「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」承載上述觀察，再執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：每次 expansion 會模擬滾動；可預處理停點改善；空間：$O(RC)$

> [!tip] 一句話記憶
> 先說清楚「明確的座標／方向／邊界，或 token stream、operator/value stacks、grammar state」代表什麼，再說每一步如何「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每一步前，位置、方向與資料結構完整描述世界；同步輪次中讀取的都是同一版舊狀態」的 base case。
>
> 2. **維持：** 每次執行「把一輪分成讀取舊狀態、標記變更、提交新狀態；parser 依 grammar 層級消耗 token」後，狀態仍與已處理資料一致。關鍵論證是：用 step induction 證明每次 transition 等同題目規則；parser 依 grammar 結構證明 precedence 與 associativity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：矩陣空維度、四個邊界交錯、同步／非同步更新、visited、unary minus、空白、括號與終止條件。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

從停靠點向四方向模擬滾動，遇洞立即停。`best[(r,c)]` 保存目前最佳 `(distance,path)`；heap 依 tuple 順序選最短且字典序最小 state。

```python
from heapq import heappush, heappop

def find_shortest_way(maze, ball, hole):
    rows, cols = len(maze), len(maze[0])
    directions = [
        (1, 0, "d"),
        (0, -1, "l"),
        (0, 1, "r"),
        (-1, 0, "u"),
    ]
    start = tuple(ball)
    target = tuple(hole)
    heap = [(0, "", start[0], start[1])]
    best = {start: (0, "")}

    while heap:
        distance, path, r, c = heappop(heap)
        if best[(r, c)] != (distance, path):
            continue
        if (r, c) == target:
            return path

        for dr, dc, label in directions:
            nr, nc = r, c
            steps = 0
            while (
                0 <= nr + dr < rows
                and 0 <= nc + dc < cols
                and maze[nr + dr][nc + dc] == 0
            ):
                nr += dr
                nc += dc
                steps += 1
                if (nr, nc) == target:
                    break

            candidate = (distance + steps, path + label)
            if steps and candidate < best.get((nr, nc), (float("inf"), "~")):
                best[(nr, nc)] = candidate
                heappush(heap, (candidate[0], candidate[1], nr, nc))

    return "impossible"
```

- 時間：每次 expansion 會模擬滾動；可預處理停點改善
- 空間：$O(RC)$

### Follow-up 1：原題直接變形
**問：有大量不同起終點 query？**

**答：**預先把每格四方向的下一停點、距離與是否經過洞建成 graph；每次 query 再跑 Dijkstra，避免重複逐格模擬。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《The Maze III》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：從停靠點向四方向模擬滾動，遇洞立即停。best[(r,c)] 保存目前最佳 (distance,path)；heap 依 tuple 順序選最短且字典序最小 state。 失效情境包括：規則具有長距離互動或需要回溯時，單次局部 simulation 不夠；grammar 模糊時 stack parser 也可能誤解。
>
> 替代路線是：採 double buffering、event queue、state graph search、recursive descent、Pratt parser 或建立 AST。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：記錄每步 action/board diff；parser 建 AST。這些 witness 能重播 simulation 或顯示完整運算順序。
>
> 套回《The Maze III》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 不可信輸入要限制步數、矩陣大小與 parser depth；simulation loop 必須證明終止，並支援 deterministic replay。
>
> 此外必須把《The Maze III》目前隱含的前提寫成 contract：球朝一個方向會一直滾到牆或洞。找從起點進洞的最短距離；距離相同取 lexicographically smallest directions string。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 會把方向與 boundary 明確列出。
- [ ] 同步更新與逐步更新不會混淆。
- [ ] Parser 會先定義 grammar 與 precedence。
- [ ] Simulation 會證明終止條件。
