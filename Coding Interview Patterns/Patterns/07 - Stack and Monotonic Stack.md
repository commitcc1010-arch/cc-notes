---
title: Stack and Monotonic Stack
tags:
  - coding-interview/pattern
  - stack
  - monotonic-stack
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 07 — Stack and Monotonic Stack

[[06 - Sorting Intervals and Sweep Line|← 上一章]] · [[00 - Book Index|目錄]] · [[08 - Linked List|下一章 →]]

> [!abstract] Mental model
> Stack 保存「最近尚未完成的工作」。Monotonic stack 進一步刪除已被新元素支配、未來不可能成為答案的候選，使每個元素最多進出一次。

## 辨認訊號

- 括號、巢狀語法、undo。
- 下一個更大／更小元素。
- 以某元素作為最小值或高度時的最大範圍。
- 維持 lexicographically smallest／largest subsequence。

---

## 核心題 1：Valid Parentheses


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 判斷括號字串是否每個 opening bracket 都以正確種類與巢狀順序關閉。
>
> **核心轉換：** stack 保存尚未匹配的 opening brackets；遇 closing bracket 時，它只能匹配 stack top，最後 stack 必須為空。
>
> **主要知識點：** Stack、Monotonic Stack 與延後決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Valid Parentheses
      │
      ├─ 暴力路線：對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構
      │
      ▼  找出本題最關鍵的轉換
核心觀察：stack 保存尚未匹配的 opening brackets；遇 closing bracket 時，它只能匹配 stack top，最後 stack 必須為空。
      │
Pattern toolbox：stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序
      │
      ├─ 狀態轉移：新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區
      │
      ├─ 永遠成立：stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 判斷括號字串是否每個 opening bracket 都以正確種類與巢狀順序關閉。
2. **寫出暴力：** 對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** stack 保存尚未匹配的 opening brackets；遇 closing bracket 時，它只能匹配 stack top，最後 stack 必須為空。
4. **定義 state 與轉移：** 使用「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」承載上述觀察，再執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」代表什麼，再說每一步如何「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選」的 base case。
>
> 2. **維持：** 每次執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」後，狀態仍與已處理資料一致。關鍵論證是：證明被 pop 的元素答案在此刻首次確定，或已被新元素永久支配；每個元素最多 push/pop 一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：相等值該用 < 或 <=、括號方向、剩餘 stack、index/value 混用與 expression unary operator。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def valid_parentheses(s):
    match = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in s:
        if ch in match:
            if not stack or stack.pop() != match[ch]:
                return False
        else:
            stack.append(ch)
    return not stack
```

- 時間：$O(n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：若 `*` 可以代表 `(`、`)` 或空字串？**

**答：**維護目前未匹配左括號數的最小值與最大值。遇 `(` 都加一、`)` 都減一、`*` 讓範圍變成 `[low-1, high+1]`；`low` 不低於零，`high<0` 立即失敗，最後 `low==0` 才可行。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Valid Parentheses》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：stack 保存尚未匹配的 opening brackets；遇 closing bracket 時，它只能匹配 stack top，最後 stack 必須為空。 失效情境包括：若答案依賴任意遠的雙向資訊且沒有支配順序，單一 stack 無法壓縮候選。
>
> 替代路線是：改用 deque、balanced tree、prefix/suffix arrays、DP 或 parser；需要隨機刪除時通常不再是 stack。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：stack 中保存 index、前驅與局部貢獻；parser 保存 AST node，最後可重建區間、運算樹或選擇序列。
>
> 套回《Valid Parentheses》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超深巢狀輸入要避免 recursion overflow；parser 應限制 expression size。併發共享 stack 必須定義線性化點。
>
> 此外必須把《Valid Parentheses》目前隱含的前提寫成 contract：判斷括號字串是否每個 opening bracket 都以正確種類與巢狀順序關閉。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Daily Temperatures

### 題目

對每天溫度，回傳還要等幾天才會遇到更高溫；不存在為零。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 對每天溫度，回傳還要等幾天才會遇到更高溫；不存在為零。
>
> **核心轉換：** monotonic decreasing stack 保存尚未找到更高溫的 indices；新溫度較高時依序 pop，當下 index 就是被 pop 日子的第一個答案。
>
> **主要知識點：** Stack、Monotonic Stack 與延後決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Daily Temperatures
      │
      ├─ 暴力路線：對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構
      │
      ▼  找出本題最關鍵的轉換
核心觀察：monotonic decreasing stack 保存尚未找到更高溫的 indices；新溫度較高時依序 pop，當下 index 就是被 pop 日子的第一個答案。
      │
Pattern toolbox：stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序
      │
      ├─ 狀態轉移：新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區
      │
      ├─ 永遠成立：stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 對每天溫度，回傳還要等幾天才會遇到更高溫；不存在為零。
2. **寫出暴力：** 對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** monotonic decreasing stack 保存尚未找到更高溫的 indices；新溫度較高時依序 pop，當下 index 就是被 pop 日子的第一個答案。
4. **定義 state 與轉移：** 使用「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」承載上述觀察，再執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」代表什麼，再說每一步如何「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選」的 base case。
>
> 2. **維持：** 每次執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」後，狀態仍與已處理資料一致。關鍵論證是：證明被 pop 的元素答案在此刻首次確定，或已被新元素永久支配；每個元素最多 push/pop 一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：相等值該用 < 或 <=、括號方向、剩餘 stack、index/value 混用與 expression unary operator。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def daily_temperatures(temperatures):
    answer = [0] * len(temperatures)
    stack = []
    for i, value in enumerate(temperatures):
        while stack and temperatures[stack[-1]] < value:
            previous = stack.pop()
            answer[previous] = i - previous
        stack.append(i)
    return answer
```

**Invariant：**stack 中 index 對應溫度由底到頂非遞增，且都還沒找到下一個更高溫。

### Follow-up 1：原題直接變形
**問：陣列是 circular？**

**答：**走訪 `2n` 次，index 使用 `i % n`；第二輪只負責解決 stack，不再加入已確定的新 index。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Daily Temperatures》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：monotonic decreasing stack 保存尚未找到更高溫的 indices；新溫度較高時依序 pop，當下 index 就是被 pop 日子的第一個答案。 失效情境包括：若答案依賴任意遠的雙向資訊且沒有支配順序，單一 stack 無法壓縮候選。
>
> 替代路線是：改用 deque、balanced tree、prefix/suffix arrays、DP 或 parser；需要隨機刪除時通常不再是 stack。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：stack 中保存 index、前驅與局部貢獻；parser 保存 AST node，最後可重建區間、運算樹或選擇序列。
>
> 套回《Daily Temperatures》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超深巢狀輸入要避免 recursion overflow；parser 應限制 expression size。併發共享 stack 必須定義線性化點。
>
> 此外必須把《Daily Temperatures》目前隱含的前提寫成 contract：對每天溫度，回傳還要等幾天才會遇到更高溫；不存在為零。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Largest Rectangle in Histogram

### 題目

柱狀圖中找最大矩形面積。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 柱狀圖中找最大矩形面積。
>
> **核心轉換：** 當看到較矮柱時，stack 頂較高柱的右邊界被確定。彈出高度 h 後，新的 stack 頂是左側第一個更矮位置。
>
> **主要知識點：** Stack、Monotonic Stack 與延後決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Largest Rectangle in Histogram
      │
      ├─ 暴力路線：對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構
      │
      ▼  找出本題最關鍵的轉換
核心觀察：當看到較矮柱時，stack 頂較高柱的右邊界被確定。彈出高度 h 後，新的 stack 頂是左側第一個更矮位置。
      │
Pattern toolbox：stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序
      │
      ├─ 狀態轉移：新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區
      │
      ├─ 永遠成立：stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 柱狀圖中找最大矩形面積。
2. **寫出暴力：** 對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 當看到較矮柱時，stack 頂較高柱的右邊界被確定。彈出高度 h 後，新的 stack 頂是左側第一個更矮位置。
4. **定義 state 與轉移：** 使用「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」承載上述觀察，再執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」代表什麼，再說每一步如何「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選」的 base case。
>
> 2. **維持：** 每次執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」後，狀態仍與已處理資料一致。關鍵論證是：證明被 pop 的元素答案在此刻首次確定，或已被新元素永久支配；每個元素最多 push/pop 一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：相等值該用 < 或 <=、括號方向、剩餘 stack、index/value 混用與 expression unary operator。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 推導

當看到較矮柱時，stack 頂較高柱的右邊界被確定。彈出高度 `h` 後，新的 stack 頂是左側第一個更矮位置。

```python
def largest_rectangle_area(heights):
    stack = []
    best = 0
    for i, height in enumerate(heights + [0]):
        while stack and heights[stack[-1]] > height:
            h = heights[stack.pop()]
            left = stack[-1] if stack else -1
            best = max(best, h * (i - left - 1))
        stack.append(i)
    return best
```

- 時間：$O(n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：相等高度應不應彈出？**

**答：**`>` 或 `>=` 都能設計成正確版本，但左右邊界 tie 規則必須一致。使用 `>` 會保留相等高度，較早位置在最後取得較寬範圍。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Largest Rectangle in Histogram》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：當看到較矮柱時，stack 頂較高柱的右邊界被確定。彈出高度 h 後，新的 stack 頂是左側第一個更矮位置。 失效情境包括：若答案依賴任意遠的雙向資訊且沒有支配順序，單一 stack 無法壓縮候選。
>
> 替代路線是：改用 deque、balanced tree、prefix/suffix arrays、DP 或 parser；需要隨機刪除時通常不再是 stack。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：stack 中保存 index、前驅與局部貢獻；parser 保存 AST node，最後可重建區間、運算樹或選擇序列。
>
> 套回《Largest Rectangle in Histogram》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超深巢狀輸入要避免 recursion overflow；parser 應限制 expression size。併發共享 stack 必須定義線性化點。
>
> 此外必須把《Largest Rectangle in Histogram》目前隱含的前提寫成 contract：柱狀圖中找最大矩形面積。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Maximal Rectangle

### 題目

在只含 0/1 的矩陣中找全為 1 的最大矩形面積。

> [!tip]- 三層提示
> 1. 逐 row 思考。
> 2. 把每一 row 當成 histogram 的底。
> 3. 遇 1 高度加一，遇 0 歸零，再解 Largest Rectangle。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 在只含 0/1 的矩陣中找全為 1 的最大矩形面積。
>
> **核心轉換：** heights[c] 表示以目前 row 為底，column c 向上連續 1 的高度。每更新一 row，就呼叫 histogram 解法。
>
> **主要知識點：** Stack、Monotonic Stack 與延後決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Maximal Rectangle
      │
      ├─ 暴力路線：對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構
      │
      ▼  找出本題最關鍵的轉換
核心觀察：heights[c] 表示以目前 row 為底，column c 向上連續 1 的高度。每更新一 row，就呼叫 histogram 解法。
      │
Pattern toolbox：stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序
      │
      ├─ 狀態轉移：新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區
      │
      ├─ 永遠成立：stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 在只含 0/1 的矩陣中找全為 1 的最大矩形面積。
2. **寫出暴力：** 對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** heights[c] 表示以目前 row 為底，column c 向上連續 1 的高度。每更新一 row，就呼叫 histogram 解法。
4. **定義 state 與轉移：** 使用「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」承載上述觀察，再執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(RC)$；空間：$O(C)$

> [!tip] 一句話記憶
> 先說清楚「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」代表什麼，再說每一步如何「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選」的 base case。
>
> 2. **維持：** 每次執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」後，狀態仍與已處理資料一致。關鍵論證是：證明被 pop 的元素答案在此刻首次確定，或已被新元素永久支配；每個元素最多 push/pop 一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：相等值該用 < 或 <=、括號方向、剩餘 stack、index/value 混用與 expression unary operator。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

`heights[c]` 表示以目前 row 為底，column `c` 向上連續 1 的高度。每更新一 row，就呼叫 histogram 解法。

```python
def maximal_rectangle(matrix):
    if not matrix:
        return 0
    heights = [0] * len(matrix[0])
    best = 0

    def histogram(values):
        stack = []
        answer = 0
        for i, value in enumerate(values + [0]):
            while stack and values[stack[-1]] > value:
                height = values[stack.pop()]
                left = stack[-1] if stack else -1
                answer = max(answer, height * (i - left - 1))
            stack.append(i)
        return answer

    for row in matrix:
        for c, value in enumerate(row):
            heights[c] = heights[c] + 1 if value == "1" or value == 1 else 0
        best = max(best, histogram(heights))
    return best
```

- 時間：$O(RC)$
- 空間：$O(C)$

### Follow-up 1：原題直接變形
**問：要回傳矩形座標？**

**答：**histogram 彈出時已知高度、左右邊界與目前 row；top row 是 `row-height+1`。更新最佳面積時一起保存 `(top,left,bottom,right)`。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Maximal Rectangle》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：heights[c] 表示以目前 row 為底，column c 向上連續 1 的高度。每更新一 row，就呼叫 histogram 解法。 失效情境包括：若答案依賴任意遠的雙向資訊且沒有支配順序，單一 stack 無法壓縮候選。
>
> 替代路線是：改用 deque、balanced tree、prefix/suffix arrays、DP 或 parser；需要隨機刪除時通常不再是 stack。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：stack 中保存 index、前驅與局部貢獻；parser 保存 AST node，最後可重建區間、運算樹或選擇序列。
>
> 套回《Maximal Rectangle》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超深巢狀輸入要避免 recursion overflow；parser 應限制 expression size。併發共享 stack 必須定義線性化點。
>
> 此外必須把《Maximal Rectangle》目前隱含的前提寫成 contract：在只含 0/1 的矩陣中找全為 1 的最大矩形面積。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Basic Calculator

### 題目

計算含非負整數、空白、`+`、`-` 與括號的運算式。

> [!tip]- 三層提示
> 1. 逐字累積目前 number。
> 2. 遇 `+/-` 時把上一個 number 套用目前 sign。
> 3. 遇 `(` 保存外層 result 與 sign；遇 `)` 合併。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 計算含非負整數、空白、+、- 與括號的運算式。
>
> **核心轉換：** Stack 不保存每個 token，而是保存進入括號前的 (result, sign)。目前括號算完後，outerresult + outersign innerresult。
>
> **主要知識點：** Stack、Monotonic Stack 與延後決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Basic Calculator
      │
      ├─ 暴力路線：對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Stack 不保存每個 token，而是保存進入括號前的 (result, sign)。目前括號算完後，outerresult + outersign innerresult。
      │
Pattern toolbox：stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序
      │
      ├─ 狀態轉移：新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區
      │
      ├─ 永遠成立：stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 計算含非負整數、空白、+、- 與括號的運算式。
2. **寫出暴力：** 對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Stack 不保存每個 token，而是保存進入括號前的 (result, sign)。目前括號算完後，outerresult + outersign innerresult。
4. **定義 state 與轉移：** 使用「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」承載上述觀察，再執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(depth)$

> [!tip] 一句話記憶
> 先說清楚「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」代表什麼，再說每一步如何「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選」的 base case。
>
> 2. **維持：** 每次執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」後，狀態仍與已處理資料一致。關鍵論證是：證明被 pop 的元素答案在此刻首次確定，或已被新元素永久支配；每個元素最多 push/pop 一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：相等值該用 < 或 <=、括號方向、剩餘 stack、index/value 混用與 expression unary operator。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Stack 不保存每個 token，而是保存進入括號前的 `(result, sign)`。目前括號算完後，`outer_result + outer_sign * inner_result`。

```python
def calculate(expression):
    result = number = 0
    sign = 1
    stack = []

    for ch in expression:
        if ch.isdigit():
            number = number * 10 + int(ch)
        elif ch in "+-":
            result += sign * number
            number = 0
            sign = 1 if ch == "+" else -1
        elif ch == "(":
            stack.append(result)
            stack.append(sign)
            result = 0
            sign = 1
        elif ch == ")":
            result += sign * number
            number = 0
            outer_sign = stack.pop()
            outer_result = stack.pop()
            result = outer_result + outer_sign * result

    return result + sign * number
```

- 時間：$O(n)$
- 空間：$O(depth)$

### Follow-up 1：原題直接變形
**問：加入 `*`、`/` 與 operator precedence？**

**答：**可用兩個 stacks 實作 shunting-yard，或寫 recursive descent parser：`expr -> term -> factor`。詳見 [[20 - Matrix Simulation and Parsing]]。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Basic Calculator》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Stack 不保存每個 token，而是保存進入括號前的 (result, sign)。目前括號算完後，outerresult + outersign innerresult。 失效情境包括：若答案依賴任意遠的雙向資訊且沒有支配順序，單一 stack 無法壓縮候選。
>
> 替代路線是：改用 deque、balanced tree、prefix/suffix arrays、DP 或 parser；需要隨機刪除時通常不再是 stack。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：stack 中保存 index、前驅與局部貢獻；parser 保存 AST node，最後可重建區間、運算樹或選擇序列。
>
> 套回《Basic Calculator》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超深巢狀輸入要避免 recursion overflow；parser 應限制 expression size。併發共享 stack 必須定義線性化點。
>
> 此外必須把《Basic Calculator》目前隱含的前提寫成 contract：計算含非負整數、空白、+、- 與括號的運算式。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Remove Duplicate Letters

### 題目

刪除重複字母，使每種字母恰出現一次，並回傳 lexicographically smallest 結果。

> [!tip]- 三層提示
> 1. 每個字母只能留一次。
> 2. 若 stack 尾端比新字母大，而且尾端之後還會出現，就可安全刪掉。
> 3. 需要 `last occurrence` 與 `in_stack`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 刪除重複字母，使每種字母恰出現一次，並回傳 lexicographically smallest 結果。
>
> **核心轉換：** 新字母尚未使用時，持續彈出較大且未來仍可補回的尾端。若尾端不會再出現，就不能刪。
>
> **主要知識點：** Stack、Monotonic Stack 與延後決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Remove Duplicate Letters
      │
      ├─ 暴力路線：對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構
      │
      ▼  找出本題最關鍵的轉換
核心觀察：新字母尚未使用時，持續彈出較大且未來仍可補回的尾端。若尾端不會再出現，就不能刪。
      │
Pattern toolbox：stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序
      │
      ├─ 狀態轉移：新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區
      │
      ├─ 永遠成立：stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 刪除重複字母，使每種字母恰出現一次，並回傳 lexicographically smallest 結果。
2. **寫出暴力：** 對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 新字母尚未使用時，持續彈出較大且未來仍可補回的尾端。若尾端不會再出現，就不能刪。
4. **定義 state 與轉移：** 使用「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」承載上述觀察，再執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(\text{alphabet})$

> [!tip] 一句話記憶
> 先說清楚「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」代表什麼，再說每一步如何「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選」的 base case。
>
> 2. **維持：** 每次執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」後，狀態仍與已處理資料一致。關鍵論證是：證明被 pop 的元素答案在此刻首次確定，或已被新元素永久支配；每個元素最多 push/pop 一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：相等值該用 < 或 <=、括號方向、剩餘 stack、index/value 混用與 expression unary operator。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

新字母尚未使用時，持續彈出較大且未來仍可補回的尾端。若尾端不會再出現，就不能刪。

```python
def remove_duplicate_letters(s):
    last = {ch: i for i, ch in enumerate(s)}
    stack = []
    used = set()

    for i, ch in enumerate(s):
        if ch in used:
            continue
        while stack and stack[-1] > ch and last[stack[-1]] > i:
            used.remove(stack.pop())
        stack.append(ch)
        used.add(ch)
    return "".join(stack)
```

- 時間：$O(n)$
- 空間：$O(\text{alphabet})$

### Follow-up 1：原題直接變形
**問：每個字母要保留恰好 `need[ch]` 次？**

**答：**把 `used` 改成已選次數，另存剩餘次數。彈出尾端前需確認「彈出後，剩餘出現仍足以補到需求」；這是相同 greedy proof 的多重版本。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Remove Duplicate Letters》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：新字母尚未使用時，持續彈出較大且未來仍可補回的尾端。若尾端不會再出現，就不能刪。 失效情境包括：若答案依賴任意遠的雙向資訊且沒有支配順序，單一 stack 無法壓縮候選。
>
> 替代路線是：改用 deque、balanced tree、prefix/suffix arrays、DP 或 parser；需要隨機刪除時通常不再是 stack。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：stack 中保存 index、前驅與局部貢獻；parser 保存 AST node，最後可重建區間、運算樹或選擇序列。
>
> 套回《Remove Duplicate Letters》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超深巢狀輸入要避免 recursion overflow；parser 應限制 expression size。併發共享 stack 必須定義線性化點。
>
> 此外必須把《Remove Duplicate Letters》目前隱含的前提寫成 contract：刪除重複字母，使每種字母恰出現一次，並回傳 lexicographically smallest 結果。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Create Maximum Number

### 題目

從兩個陣列各保留相對順序，共選 `k` 個 digits，組成 lexicographically largest 序列。

> [!tip]- 三層提示
> 1. 枚舉從第一個陣列取幾個。
> 2. 單一陣列取長度 `t` 的最大 subsequence 可用 monotonic stack。
> 3. 合併兩 subsequences 時不能只比較當前 digit；相等時要比較剩餘 suffix。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 從兩個陣列各保留相對順序，共選 k 個 digits，組成 lexicographically largest 序列。
>
> **核心轉換：** pick(nums,t) 使用可刪除數量 drop=len(nums)-t，遇更大 digit 時彈出較小尾端。枚舉合法 split，再 lexicographically merge。
>
> **主要知識點：** Stack、Monotonic Stack 與延後決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Create Maximum Number
      │
      ├─ 暴力路線：對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構
      │
      ▼  找出本題最關鍵的轉換
核心觀察：pick(nums,t) 使用可刪除數量 drop=len(nums)-t，遇更大 digit 時彈出較小尾端。枚舉合法 split，再 lexicographically merge。
      │
Pattern toolbox：stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序
      │
      ├─ 狀態轉移：新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區
      │
      ├─ 永遠成立：stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 從兩個陣列各保留相對順序，共選 k 個 digits，組成 lexicographically largest 序列。
2. **寫出暴力：** 對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** pick(nums,t) 使用可刪除數量 drop=len(nums)-t，遇更大 digit 時彈出較小尾端。枚舉合法 split，再 lexicographically merge。
4. **定義 state 與轉移：** 使用「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」承載上述觀察，再執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：樸素 suffix 比較下 worst case 約 $O(k^2\min(n,k))$；空間：$O(k)$

> [!tip] 一句話記憶
> 先說清楚「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」代表什麼，再說每一步如何「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選」的 base case。
>
> 2. **維持：** 每次執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」後，狀態仍與已處理資料一致。關鍵論證是：證明被 pop 的元素答案在此刻首次確定，或已被新元素永久支配；每個元素最多 push/pop 一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：相等值該用 < 或 <=、括號方向、剩餘 stack、index/value 混用與 expression unary operator。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

`pick(nums,t)` 使用可刪除數量 `drop=len(nums)-t`，遇更大 digit 時彈出較小尾端。枚舉合法 split，再 lexicographically merge。

```python
def max_number(nums1, nums2, k):
    def pick(nums, size):
        drop = len(nums) - size
        stack = []
        for x in nums:
            while drop and stack and stack[-1] < x:
                stack.pop()
                drop -= 1
            stack.append(x)
        return stack[:size]

    def greater(a, i, b, j):
        while i < len(a) and j < len(b) and a[i] == b[j]:
            i += 1
            j += 1
        return j == len(b) or (i < len(a) and a[i] > b[j])

    def merge(a, b):
        answer = []
        i = j = 0
        while i < len(a) or j < len(b):
            if greater(a, i, b, j):
                answer.append(a[i])
                i += 1
            else:
                answer.append(b[j])
                j += 1
        return answer

    best = []
    start = max(0, k - len(nums2))
    end = min(k, len(nums1))
    for take1 in range(start, end + 1):
        candidate = merge(
            pick(nums1, take1),
            pick(nums2, k - take1),
        )
        best = max(best, candidate)
    return best
```

- 時間：樸素 suffix 比較下 worst case 約 $O(k^2\min(n,k))$
- 空間：$O(k)$

### Follow-up 1：原題直接變形
**問：如何改善大量相同 digits 導致的 suffix 重複比較？**

**答：**可對兩個 subsequence 的 suffix 建 rank、rolling hash＋LCP，或 suffix-array 類結構，讓 lexicographic suffix comparison 更快。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Create Maximum Number》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：pick(nums,t) 使用可刪除數量 drop=len(nums)-t，遇更大 digit 時彈出較小尾端。枚舉合法 split，再 lexicographically merge。 失效情境包括：若答案依賴任意遠的雙向資訊且沒有支配順序，單一 stack 無法壓縮候選。
>
> 替代路線是：改用 deque、balanced tree、prefix/suffix arrays、DP 或 parser；需要隨機刪除時通常不再是 stack。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：stack 中保存 index、前驅與局部貢獻；parser 保存 AST node，最後可重建區間、運算樹或選擇序列。
>
> 套回《Create Maximum Number》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超深巢狀輸入要避免 recursion overflow；parser 應限制 expression size。併發共享 stack 必須定義線性化點。
>
> 此外必須把《Create Maximum Number》目前隱含的前提寫成 contract：從兩個陣列各保留相對順序，共選 k 個 digits，組成 lexicographically largest 序列。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Sum of Subarray Minimums

### 題目

所有 subarray 的最小值總和，答案取模。

> [!tip]- 三層提示
> 1. 不要枚舉 subarray；改問每個元素貢獻給多少 subarray。
> 2. 找左邊第一個較小值、右邊第一個小於等於值。
> 3. 貢獻為 `value * left_choices * right_choices`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 所有 subarray 的最小值總和，答案取模。
>
> **核心轉換：** 單調遞增 stack。遇較小值時，彈出的 index mid 得到右邊界 i；彈出後 stack 頂是左邊第一個不大於它的位置。使用嚴格／非嚴格 tie 規則，讓重複值的 subarray 只歸屬一個位置。
>
> **主要知識點：** Stack、Monotonic Stack 與延後決策。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Sum of Subarray Minimums
      │
      ├─ 暴力路線：對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構
      │
      ▼  找出本題最關鍵的轉換
核心觀察：單調遞增 stack。遇較小值時，彈出的 index mid 得到右邊界 i；彈出後 stack 頂是左邊第一個不大於它的位置。使用嚴格／非嚴格 tie 規則，讓重複值的 subarray 只歸屬一個位置。
      │
Pattern toolbox：stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序
      │
      ├─ 狀態轉移：新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區
      │
      ├─ 永遠成立：stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 所有 subarray 的最小值總和，答案取模。
2. **寫出暴力：** 對每個位置向左右掃描尋找第一個滿足條件的元素，或反覆解析巢狀結構。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 單調遞增 stack。遇較小值時，彈出的 index mid 得到右邊界 i；彈出後 stack 頂是左邊第一個不大於它的位置。使用嚴格／非嚴格 tie 規則，讓重複值的 subarray 只歸屬一個位置。
4. **定義 state 與轉移：** 使用「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」承載上述觀察，再執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「stack 保存尚未找到答案的候選；monotonic stack 另維持值的單調順序」代表什麼，再說每一步如何「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「stack 內元素仍未被未來資訊解決，且其順序足以代表所有尚未完成的必要候選」的 base case。
>
> 2. **維持：** 每次執行「新元素到來時，彈出已能確定答案或已被支配的候選，再把自己加入等待區」後，狀態仍與已處理資料一致。關鍵論證是：證明被 pop 的元素答案在此刻首次確定，或已被新元素永久支配；每個元素最多 push/pop 一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：相等值該用 < 或 <=、括號方向、剩餘 stack、index/value 混用與 expression unary operator。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

單調遞增 stack。遇較小值時，彈出的 index `mid` 得到右邊界 `i`；彈出後 stack 頂是左邊第一個不大於它的位置。使用嚴格／非嚴格 tie 規則，讓重複值的 subarray 只歸屬一個位置。

```python
def sum_subarray_mins(arr):
    mod = 1_000_000_007
    stack = []
    answer = 0
    values = arr + [float("-inf")]

    for i, value in enumerate(values):
        while stack and values[stack[-1]] > value:
            mid = stack.pop()
            left = stack[-1] if stack else -1
            answer += values[mid] * (mid - left) * (i - mid)
        stack.append(i)
    return answer % mod
```

- 時間：$O(n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：求所有 subarray 的 range（max-min）總和？**

**答：**分別計算每個元素作為 maximum 與 minimum 的總貢獻，再做 `sum_max - sum_min`。兩次 monotonic stack 的不等號方向相反。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Sum of Subarray Minimums》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：單調遞增 stack。遇較小值時，彈出的 index mid 得到右邊界 i；彈出後 stack 頂是左邊第一個不大於它的位置。使用嚴格／非嚴格 tie 規則，讓重複值的 subarray 只歸屬一個位置。 失效情境包括：若答案依賴任意遠的雙向資訊且沒有支配順序，單一 stack 無法壓縮候選。
>
> 替代路線是：改用 deque、balanced tree、prefix/suffix arrays、DP 或 parser；需要隨機刪除時通常不再是 stack。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：stack 中保存 index、前驅與局部貢獻；parser 保存 AST node，最後可重建區間、運算樹或選擇序列。
>
> 套回《Sum of Subarray Minimums》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超深巢狀輸入要避免 recursion overflow；parser 應限制 expression size。併發共享 stack 必須定義線性化點。
>
> 此外必須把《Sum of Subarray Minimums》目前隱含的前提寫成 contract：所有 subarray 的最小值總和，答案取模。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 能說出 stack 中尚未完成的是什麼。
- [ ] 能定義 monotonic stack 的順序。
- [ ] 知道相等值的 tie-breaking 會影響重複計數。
- [ ] 能用 sentinel 清空 stack。
