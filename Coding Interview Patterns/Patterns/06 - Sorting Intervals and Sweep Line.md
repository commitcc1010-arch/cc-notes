---
title: Sorting Intervals and Sweep Line
tags:
  - coding-interview/pattern
  - intervals
  - sweep-line
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 06 — Sorting, Intervals and Sweep Line

[[05 - Binary Search|← 上一章]] · [[00 - Book Index|目錄]] · [[07 - Stack and Monotonic Stack|下一章 →]]

> [!abstract] Mental model
> 排序把全域混亂轉成局部關係。Interval 題通常先依 start 排序；sweep line 則把區間轉成 start/end events，沿座標軸維護「目前活躍集合」。

## 面試前先確認

- 區間是 closed `[a,b]` 還是 half-open `[a,b)`？
- 端點相等算重疊嗎？
- 輸入是否已排序？
- 要合併、計數、分配資源，還是回答查詢？

---

## 核心題 1：Merge Intervals


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 合併所有重疊區間並回傳互不重疊、依起點排序的結果。
>
> **核心轉換：** 先按 start 排序；若下一段 start <= 已合併尾段 end 就延長 end，否則尾段已不可能再被未來區間碰到，可安全輸出。
>
> **主要知識點：** Sorting、Intervals 與 Sweep Line。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Merge Intervals
      │
      ├─ 暴力路線：逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件
      │
      ▼  找出本題最關鍵的轉換
核心觀察：先按 start 排序；若下一段 start <= 已合併尾段 end 就延長 end，否則尾段已不可能再被未來區間碰到，可安全輸出。
      │
Pattern toolbox：依 start/end 排序後的事件流，加上目前 active intervals 的摘要
      │
      ├─ 狀態轉移：掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案
      │
      ├─ 永遠成立：掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 合併所有重疊區間並回傳互不重疊、依起點排序的結果。
2. **寫出暴力：** 逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 先按 start 排序；若下一段 start <= 已合併尾段 end 就延長 end，否則尾段已不可能再被未來區間碰到，可安全輸出。
4. **定義 state 與轉移：** 使用「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」承載上述觀察，再執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log n)$；空間：$O(n)$，包含輸出

> [!tip] 一句話記憶
> 先說清楚「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」代表什麼，再說每一步如何「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間」的 base case。
>
> 2. **維持：** 每次執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」後，狀態仍與已處理資料一致。關鍵論證是：排序建立全域處理順序；再證明只有事件點會改變答案，且每個區間在 start/end 各影響一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：端點相等是否算重疊、閉區間／半開區間、tie order、零長度區間與輸出排序。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def merge_intervals(intervals):
    intervals.sort(key=lambda x: x[0])
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return merged
```

- 時間：$O(n\log n)$
- 空間：$O(n)$，包含輸出

### Follow-up 1：原題直接變形
**問：half-open intervals `[a,b)` 的端點相等是否合併？**

**答：**依語意決定。若 `[1,2)` 與 `[2,3)` 被視為連續但不重疊，判斷應使用 `start >= previous_end` 來分開。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Merge Intervals》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：先按 start 排序；若下一段 start <= 已合併尾段 end 就延長 end，否則尾段已不可能再被未來區間碰到，可安全輸出。 失效情境包括：若事件持續線上到達或需要任意刪除，單次離線排序不夠；高維區間也可能無法直接 sweep。
>
> 替代路線是：改用 ordered map、interval tree、segment tree、coordinate compression，或針對二維以上做多層 sweep。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：合併題保存來源區間；排程題保存 room/resource id；skyline 題在 active maximum 改變時輸出 turning point。
>
> 套回《Merge Intervals》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Calendar 類服務需處理併發預約的 transaction、時區與重試；大量座標先壓縮，並定義端點語意為 API contract。
>
> 此外必須把《Merge Intervals》目前隱含的前提寫成 contract：合併所有重疊區間並回傳互不重疊、依起點排序的結果。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Insert Interval

### 題目

已排序且互不重疊的 intervals 中插入一個 interval，必要時合併。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 已排序且互不重疊的 intervals 中插入一個 interval，必要時合併。
>
> **核心轉換：** 依序分成完全在新區間左側、與新區間重疊、完全在右側三段；中間重疊區只需累積 min start 與 max end。
>
> **主要知識點：** Sorting、Intervals 與 Sweep Line。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Insert Interval
      │
      ├─ 暴力路線：逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件
      │
      ▼  找出本題最關鍵的轉換
核心觀察：依序分成完全在新區間左側、與新區間重疊、完全在右側三段；中間重疊區只需累積 min start 與 max end。
      │
Pattern toolbox：依 start/end 排序後的事件流，加上目前 active intervals 的摘要
      │
      ├─ 狀態轉移：掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案
      │
      ├─ 永遠成立：掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 已排序且互不重疊的 intervals 中插入一個 interval，必要時合併。
2. **寫出暴力：** 逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 依序分成完全在新區間左側、與新區間重疊、完全在右側三段；中間重疊區只需累積 min start 與 max end。
4. **定義 state 與轉移：** 使用「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」承載上述觀察，再執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(n)$ output

> [!tip] 一句話記憶
> 先說清楚「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」代表什麼，再說每一步如何「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間」的 base case。
>
> 2. **維持：** 每次執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」後，狀態仍與已處理資料一致。關鍵論證是：排序建立全域處理順序；再證明只有事件點會改變答案，且每個區間在 start/end 各影響一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：端點相等是否算重疊、閉區間／半開區間、tie order、零長度區間與輸出排序。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def insert_interval(intervals, new_interval):
    answer = []
    i = 0
    start, end = new_interval

    while i < len(intervals) and intervals[i][1] < start:
        answer.append(intervals[i])
        i += 1

    while i < len(intervals) and intervals[i][0] <= end:
        start = min(start, intervals[i][0])
        end = max(end, intervals[i][1])
        i += 1
    answer.append([start, end])
    answer.extend(intervals[i:])
    return answer
```

- 時間：$O(n)$
- 空間：$O(n)$ output

### Follow-up 1：原題直接變形
**問：一次插入大量 intervals？**

**答：**若離線處理，將新舊 intervals 合併後一次排序與 merge；逐筆呼叫 insert 可能退化為 $O(nq)$。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Insert Interval》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：依序分成完全在新區間左側、與新區間重疊、完全在右側三段；中間重疊區只需累積 min start 與 max end。 失效情境包括：若事件持續線上到達或需要任意刪除，單次離線排序不夠；高維區間也可能無法直接 sweep。
>
> 替代路線是：改用 ordered map、interval tree、segment tree、coordinate compression，或針對二維以上做多層 sweep。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：合併題保存來源區間；排程題保存 room/resource id；skyline 題在 active maximum 改變時輸出 turning point。
>
> 套回《Insert Interval》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Calendar 類服務需處理併發預約的 transaction、時區與重試；大量座標先壓縮，並定義端點語意為 API contract。
>
> 此外必須把《Insert Interval》目前隱含的前提寫成 contract：已排序且互不重疊的 intervals 中插入一個 interval，必要時合併。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Meeting Rooms II

### 題目

給會議時間，求同時容納所有會議所需最少房間數。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 給會議時間，求同時容納所有會議所需最少房間數。
>
> **核心轉換：** 依 start 排序；min heap 保存目前房間的結束時間。若最早結束時間不晚於新會議 start，可重用該房間。
>
> **主要知識點：** Sorting、Intervals 與 Sweep Line。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Meeting Rooms II
      │
      ├─ 暴力路線：逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件
      │
      ▼  找出本題最關鍵的轉換
核心觀察：依 start 排序；min heap 保存目前房間的結束時間。若最早結束時間不晚於新會議 start，可重用該房間。
      │
Pattern toolbox：依 start/end 排序後的事件流，加上目前 active intervals 的摘要
      │
      ├─ 狀態轉移：掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案
      │
      ├─ 永遠成立：掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 給會議時間，求同時容納所有會議所需最少房間數。
2. **寫出暴力：** 逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 依 start 排序；min heap 保存目前房間的結束時間。若最早結束時間不晚於新會議 start，可重用該房間。
4. **定義 state 與轉移：** 使用「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」承載上述觀察，再執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」代表什麼，再說每一步如何「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間」的 base case。
>
> 2. **維持：** 每次執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」後，狀態仍與已處理資料一致。關鍵論證是：排序建立全域處理順序；再證明只有事件點會改變答案，且每個區間在 start/end 各影響一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：端點相等是否算重疊、閉區間／半開區間、tie order、零長度區間與輸出排序。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 推導

依 start 排序；min heap 保存目前房間的結束時間。若最早結束時間不晚於新會議 start，可重用該房間。

```python
from heapq import heappush, heappop

def min_meeting_rooms(intervals):
    intervals.sort()
    heap = []
    for start, end in intervals:
        if heap and heap[0] <= start:
            heappop(heap)
        heappush(heap, end)
    return len(heap)
```

### Follow-up 1：原題直接變形
**問：還要回傳每場會議被分配到哪個 room？**

**答：**heap 保存 `(end, room_id)`；另外維護下一個 room id。彈出可用 room 後把它重新推回新 end，並記錄 assignment。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Meeting Rooms II》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：依 start 排序；min heap 保存目前房間的結束時間。若最早結束時間不晚於新會議 start，可重用該房間。 失效情境包括：若事件持續線上到達或需要任意刪除，單次離線排序不夠；高維區間也可能無法直接 sweep。
>
> 替代路線是：改用 ordered map、interval tree、segment tree、coordinate compression，或針對二維以上做多層 sweep。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：合併題保存來源區間；排程題保存 room/resource id；skyline 題在 active maximum 改變時輸出 turning point。
>
> 套回《Meeting Rooms II》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Calendar 類服務需處理併發預約的 transaction、時區與重試；大量座標先壓縮，並定義端點語意為 API contract。
>
> 此外必須把《Meeting Rooms II》目前隱含的前提寫成 contract：給會議時間，求同時容納所有會議所需最少房間數。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Employee Free Time

### 題目

每位員工有一組已排序且互不重疊的工作區間，找所有人共同空閒的有限區間。

> [!tip]- 三層提示
> 1. 所有人共同空閒，就是所有忙碌區間 union 的 gaps。
> 2. 將 intervals flatten 後排序。
> 3. Merge 時遇到下一段 start 大於目前 end，即產生 gap。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每位員工有一組已排序且互不重疊的工作區間，找所有人共同空閒的有限區間。
>
> **核心轉換：** 把所有人的忙碌區間視為同一組 intervals。依 start 排序並維護目前 union 的最右端；下一段若不重疊，中間就是共同空閒。
>
> **主要知識點：** Sorting、Intervals 與 Sweep Line。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Employee Free Time
      │
      ├─ 暴力路線：逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件
      │
      ▼  找出本題最關鍵的轉換
核心觀察：把所有人的忙碌區間視為同一組 intervals。依 start 排序並維護目前 union 的最右端；下一段若不重疊，中間就是共同空閒。
      │
Pattern toolbox：依 start/end 排序後的事件流，加上目前 active intervals 的摘要
      │
      ├─ 狀態轉移：掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案
      │
      ├─ 永遠成立：掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每位員工有一組已排序且互不重疊的工作區間，找所有人共同空閒的有限區間。
2. **寫出暴力：** 逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 把所有人的忙碌區間視為同一組 intervals。依 start 排序並維護目前 union 的最右端；下一段若不重疊，中間就是共同空閒。
4. **定義 state 與轉移：** 使用「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」承載上述觀察，再執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(N\log N)$；空間：$O(N)$

> [!tip] 一句話記憶
> 先說清楚「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」代表什麼，再說每一步如何「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間」的 base case。
>
> 2. **維持：** 每次執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」後，狀態仍與已處理資料一致。關鍵論證是：排序建立全域處理順序；再證明只有事件點會改變答案，且每個區間在 start/end 各影響一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：端點相等是否算重疊、閉區間／半開區間、tie order、零長度區間與輸出排序。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

把所有人的忙碌區間視為同一組 intervals。依 start 排序並維護目前 union 的最右端；下一段若不重疊，中間就是共同空閒。

```python
def employee_free_time(schedule):
    intervals = sorted(
        interval
        for employee in schedule
        for interval in employee
    )
    if not intervals:
        return []

    answer = []
    current_end = intervals[0][1]
    for start, end in intervals[1:]:
        if start > current_end:
            answer.append([current_end, start])
            current_end = end
        else:
            current_end = max(current_end, end)
    return answer
```

- 時間：$O(N\log N)$
- 空間：$O(N)$

### Follow-up 1：原題直接變形
**問：每位員工的 intervals 已排序，如何利用？**

**答：**用 heap 做 k-way merge，每次取所有員工目前最早的 interval，總時間 $O(N\log E)$，`E` 是員工數。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Employee Free Time》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：把所有人的忙碌區間視為同一組 intervals。依 start 排序並維護目前 union 的最右端；下一段若不重疊，中間就是共同空閒。 失效情境包括：若事件持續線上到達或需要任意刪除，單次離線排序不夠；高維區間也可能無法直接 sweep。
>
> 替代路線是：改用 ordered map、interval tree、segment tree、coordinate compression，或針對二維以上做多層 sweep。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：合併題保存來源區間；排程題保存 room/resource id；skyline 題在 active maximum 改變時輸出 turning point。
>
> 套回《Employee Free Time》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Calendar 類服務需處理併發預約的 transaction、時區與重試；大量座標先壓縮，並定義端點語意為 API contract。
>
> 此外必須把《Employee Free Time》目前隱含的前提寫成 contract：每位員工有一組已排序且互不重疊的工作區間，找所有人共同空閒的有限區間。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：The Skyline Problem

### 題目

每棟建築為 `[left, right, height]`。回傳城市輪廓高度改變的關鍵點。

> [!tip]- 三層提示
> 1. 在每個建築 start/end 的 x 座標處才可能改變輪廓。
> 2. Sweep 時需要目前最高且尚未結束的建築。
> 3. 用 max heap 保存 `(-height, right)`，並 lazy delete 已結束建築。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每棟建築為 [left, right, height]。回傳城市輪廓高度改變的關鍵點。
>
> **核心轉換：** 建立 start events，加上所有 right 座標作為空 event。對同一 x 先推入所有開始的建築，再移除 right <= x 的 heap 頂。若目前最高高度與上一高度不同，就輸出關鍵點。
>
> **主要知識點：** Sorting、Intervals 與 Sweep Line。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：The Skyline Problem
      │
      ├─ 暴力路線：逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件
      │
      ▼  找出本題最關鍵的轉換
核心觀察：建立 start events，加上所有 right 座標作為空 event。對同一 x 先推入所有開始的建築，再移除 right <= x 的 heap 頂。若目前最高高度與上一高度不同，就輸出關鍵點。
      │
Pattern toolbox：依 start/end 排序後的事件流，加上目前 active intervals 的摘要
      │
      ├─ 狀態轉移：掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案
      │
      ├─ 永遠成立：掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每棟建築為 [left, right, height]。回傳城市輪廓高度改變的關鍵點。
2. **寫出暴力：** 逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 建立 start events，加上所有 right 座標作為空 event。對同一 x 先推入所有開始的建築，再移除 right <= x 的 heap 頂。若目前最高高度與上一高度不同，就輸出關鍵點。
4. **定義 state 與轉移：** 使用「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」承載上述觀察，再執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」代表什麼，再說每一步如何「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間」的 base case。
>
> 2. **維持：** 每次執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」後，狀態仍與已處理資料一致。關鍵論證是：排序建立全域處理順序；再證明只有事件點會改變答案，且每個區間在 start/end 各影響一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：端點相等是否算重疊、閉區間／半開區間、tie order、零長度區間與輸出排序。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

建立 start events，加上所有 right 座標作為空 event。對同一 x 先推入所有開始的建築，再移除 `right <= x` 的 heap 頂。若目前最高高度與上一高度不同，就輸出關鍵點。

```python
from heapq import heappush, heappop

def get_skyline(buildings):
    events = []
    for left, right, height in buildings:
        events.append((left, -height, right))
        events.append((right, 0, 0))
    events.sort()

    heap = [(0, float("inf"))]
    answer = []
    i = 0
    while i < len(events):
        x = events[i][0]
        while i < len(events) and events[i][0] == x:
            _, neg_height, right = events[i]
            if neg_height:
                heappush(heap, (neg_height, right))
            i += 1
        while heap[0][1] <= x:
            heappop(heap)
        height = -heap[0][0]
        if not answer or answer[-1][1] != height:
            answer.append([x, height])
    return answer
```

- 時間：$O(n\log n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：同一 x 同時有 start 與 end，為何要整組處理後才輸出？**

**答：**輪廓在同一座標只能有一個最終高度。逐 event 輸出會產生同 x 的暫時高度與重複關鍵點。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《The Skyline Problem》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：建立 start events，加上所有 right 座標作為空 event。對同一 x 先推入所有開始的建築，再移除 right <= x 的 heap 頂。若目前最高高度與上一高度不同，就輸出關鍵點。 失效情境包括：若事件持續線上到達或需要任意刪除，單次離線排序不夠；高維區間也可能無法直接 sweep。
>
> 替代路線是：改用 ordered map、interval tree、segment tree、coordinate compression，或針對二維以上做多層 sweep。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：合併題保存來源區間；排程題保存 room/resource id；skyline 題在 active maximum 改變時輸出 turning point。
>
> 套回《The Skyline Problem》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Calendar 類服務需處理併發預約的 transaction、時區與重試；大量座標先壓縮，並定義端點語意為 API contract。
>
> 此外必須把《The Skyline Problem》目前隱含的前提寫成 contract：每棟建築為 [left, right, height]。回傳城市輪廓高度改變的關鍵點。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：My Calendar III

### 題目

逐筆加入 half-open booking `[start,end)`，每次回傳歷史上最大同時重疊數。

> [!tip]- 三層提示
> 1. 把 interval 轉成 `start:+1, end:-1`。
> 2. 任一座標的 active 數是 event delta 的 prefix sum。
> 3. 每次 booking 後掃排序 events 可先得到簡潔正確解。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 逐筆加入 half-open booking [start,end)，每次回傳歷史上最大同時重疊數。
>
> **核心轉換：** Difference map 保存事件。每次加入後按時間排序並累加，最大 prefix 即最大 overlap。這不是最佳漸進複雜度，但在 booking 數量中等時清楚可靠。
>
> **主要知識點：** Sorting、Intervals 與 Sweep Line。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：My Calendar III
      │
      ├─ 暴力路線：逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Difference map 保存事件。每次加入後按時間排序並累加，最大 prefix 即最大 overlap。這不是最佳漸進複雜度，但在 booking 數量中等時清楚可靠。
      │
Pattern toolbox：依 start/end 排序後的事件流，加上目前 active intervals 的摘要
      │
      ├─ 狀態轉移：掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案
      │
      ├─ 永遠成立：掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 逐筆加入 half-open booking [start,end)，每次回傳歷史上最大同時重疊數。
2. **寫出暴力：** 逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Difference map 保存事件。每次加入後按時間排序並累加，最大 prefix 即最大 overlap。這不是最佳漸進複雜度，但在 booking 數量中等時清楚可靠。
4. **定義 state 與轉移：** 使用「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」承載上述觀察，再執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：空間：$O(M)$

> [!tip] 一句話記憶
> 先說清楚「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」代表什麼，再說每一步如何「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間」的 base case。
>
> 2. **維持：** 每次執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」後，狀態仍與已處理資料一致。關鍵論證是：排序建立全域處理順序；再證明只有事件點會改變答案，且每個區間在 start/end 各影響一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：端點相等是否算重疊、閉區間／半開區間、tie order、零長度區間與輸出排序。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Difference map 保存事件。每次加入後按時間排序並累加，最大 prefix 即最大 overlap。這不是最佳漸進複雜度，但在 booking 數量中等時清楚可靠。

```python
class MyCalendarThree:
    def __init__(self):
        self.delta = {}

    def book(self, start, end):
        self.delta[start] = self.delta.get(start, 0) + 1
        self.delta[end] = self.delta.get(end, 0) - 1
        active = best = 0
        for time in sorted(self.delta):
            active += self.delta[time]
            best = max(best, active)
        return best
```

- 單次：$O(M\log M)$，`M` 為不同端點數
- 空間：$O(M)$

### Follow-up 1：原題直接變形
**問：booking 數十萬筆時如何改善？**

**答：**使用 dynamic segment tree。每次對 `[start,end-1]` range add 1，root 維護全域 maximum；單次約 $O(\log C)$，`C` 是座標範圍。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《My Calendar III》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Difference map 保存事件。每次加入後按時間排序並累加，最大 prefix 即最大 overlap。這不是最佳漸進複雜度，但在 booking 數量中等時清楚可靠。 失效情境包括：若事件持續線上到達或需要任意刪除，單次離線排序不夠；高維區間也可能無法直接 sweep。
>
> 替代路線是：改用 ordered map、interval tree、segment tree、coordinate compression，或針對二維以上做多層 sweep。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：合併題保存來源區間；排程題保存 room/resource id；skyline 題在 active maximum 改變時輸出 turning point。
>
> 套回《My Calendar III》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Calendar 類服務需處理併發預約的 transaction、時區與重試；大量座標先壓縮，並定義端點語意為 API contract。
>
> 此外必須把《My Calendar III》目前隱含的前提寫成 contract：逐筆加入 half-open booking [start,end)，每次回傳歷史上最大同時重疊數。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Minimum Interval to Include Each Query

### 題目

對每個 query，找包含它的最短 interval 長度；不存在回傳 `-1`。

> [!tip]- 三層提示
> 1. Queries 可以離線排序。
> 2. Sweep 到 query 時，加入所有 `start <= query` 的 intervals。
> 3. Heap 依 interval length 排序，並移除 `end < query` 的失效區間。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 對每個 query，找包含它的最短 interval 長度；不存在回傳 -1。
>
> **核心轉換：** 排序 intervals 與帶原 index 的 queries。Heap 保存 (length,end)；每個 interval 只加入一次、只移除一次。
>
> **主要知識點：** Sorting、Intervals 與 Sweep Line。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Minimum Interval to Include Each Query
      │
      ├─ 暴力路線：逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件
      │
      ▼  找出本題最關鍵的轉換
核心觀察：排序 intervals 與帶原 index 的 queries。Heap 保存 (length,end)；每個 interval 只加入一次、只移除一次。
      │
Pattern toolbox：依 start/end 排序後的事件流，加上目前 active intervals 的摘要
      │
      ├─ 狀態轉移：掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案
      │
      ├─ 永遠成立：掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 對每個 query，找包含它的最短 interval 長度；不存在回傳 -1。
2. **寫出暴力：** 逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 排序 intervals 與帶原 index 的 queries。Heap 保存 (length,end)；每個 interval 只加入一次、只移除一次。
4. **定義 state 與轉移：** 使用「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」承載上述觀察，再執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O((n+q)\log n)$；空間：$O(n+q)$

> [!tip] 一句話記憶
> 先說清楚「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」代表什麼，再說每一步如何「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間」的 base case。
>
> 2. **維持：** 每次執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」後，狀態仍與已處理資料一致。關鍵論證是：排序建立全域處理順序；再證明只有事件點會改變答案，且每個區間在 start/end 各影響一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：端點相等是否算重疊、閉區間／半開區間、tie order、零長度區間與輸出排序。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

排序 intervals 與帶原 index 的 queries。Heap 保存 `(length,end)`；每個 interval 只加入一次、只移除一次。

```python
from heapq import heappush, heappop

def min_interval(intervals, queries):
    intervals.sort()
    ordered_queries = sorted((q, i) for i, q in enumerate(queries))
    answer = [-1] * len(queries)
    heap = []
    i = 0

    for query, original_index in ordered_queries:
        while i < len(intervals) and intervals[i][0] <= query:
            start, end = intervals[i]
            heappush(heap, (end - start + 1, end))
            i += 1
        while heap and heap[0][1] < query:
            heappop(heap)
        if heap:
            answer[original_index] = heap[0][0]
    return answer
```

- 時間：$O((n+q)\log n)$
- 空間：$O(n+q)$

### Follow-up 1：原題直接變形
**問：queries 在線上到達、不可排序？**

**答：**需使用 interval tree、segment tree 或其他動態 stabbing-query 結構；離線 sweep 的簡潔性來自 query 可排序。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Minimum Interval to Include Each Query》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：排序 intervals 與帶原 index 的 queries。Heap 保存 (length,end)；每個 interval 只加入一次、只移除一次。 失效情境包括：若事件持續線上到達或需要任意刪除，單次離線排序不夠；高維區間也可能無法直接 sweep。
>
> 替代路線是：改用 ordered map、interval tree、segment tree、coordinate compression，或針對二維以上做多層 sweep。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：合併題保存來源區間；排程題保存 room/resource id；skyline 題在 active maximum 改變時輸出 turning point。
>
> 套回《Minimum Interval to Include Each Query》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Calendar 類服務需處理併發預約的 transaction、時區與重試；大量座標先壓縮，並定義端點語意為 API contract。
>
> 此外必須把《Minimum Interval to Include Each Query》目前隱含的前提寫成 contract：對每個 query，找包含它的最短 interval 長度；不存在回傳 -1。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Amount of New Area Painted Each Day

### 題目

每天粉刷整數座標 half-open 區間 `[start,end)`，回傳當天第一次被粉刷的單位長度。

> [!tip]- 三層提示
> 1. 已粉刷位置不應被日後重複逐格掃描。
> 2. 讓每個已粉刷座標指向下一個可能尚未粉刷的位置。
> 3. 這是 Union-Find 的「successor」用法。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每天粉刷整數座標 half-open 區間 [start,end)，回傳當天第一次被粉刷的單位長度。
>
> **核心轉換：** parent[x] 表示 x 已粉刷，下一個候選是 find(x)。每個整數單位第一次被粉刷後，將它 union 到 x+1；日後查找會透過 path compression 跳過整段。
>
> **主要知識點：** Sorting、Intervals 與 Sweep Line。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Amount of New Area Painted Each Day
      │
      ├─ 暴力路線：逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件
      │
      ▼  找出本題最關鍵的轉換
核心觀察：parent[x] 表示 x 已粉刷，下一個候選是 find(x)。每個整數單位第一次被粉刷後，將它 union 到 x+1；日後查找會透過 path compression 跳過整段。
      │
Pattern toolbox：依 start/end 排序後的事件流，加上目前 active intervals 的摘要
      │
      ├─ 狀態轉移：掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案
      │
      ├─ 永遠成立：掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每天粉刷整數座標 half-open 區間 [start,end)，回傳當天第一次被粉刷的單位長度。
2. **寫出暴力：** 逐對檢查所有區間是否重疊，或對每個時間點重算活躍事件。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** parent[x] 表示 x 已粉刷，下一個候選是 find(x)。每個整數單位第一次被粉刷後，將它 union 到 x+1；日後查找會透過 path compression 跳過整段。
4. **定義 state 與轉移：** 使用「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」承載上述觀察，再執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O((D+q)\alpha(D))$，D 為最終真正粉刷的整數單位數；空間：$O(D)$

> [!tip] 一句話記憶
> 先說清楚「依 start/end 排序後的事件流，加上目前 active intervals 的摘要」代表什麼，再說每一步如何「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「掃描位置之前的事件已完全結算；active state 恰代表跨越目前座標的區間」的 base case。
>
> 2. **維持：** 每次執行「掃過事件座標；開始事件加入狀態，結束事件移除，並在狀態改變處更新答案」後，狀態仍與已處理資料一致。關鍵論證是：排序建立全域處理順序；再證明只有事件點會改變答案，且每個區間在 start/end 各影響一次。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：端點相等是否算重疊、閉區間／半開區間、tie order、零長度區間與輸出排序。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

`parent[x]` 表示 `x` 已粉刷，下一個候選是 `find(x)`。每個整數單位第一次被粉刷後，將它 union 到 `x+1`；日後查找會透過 path compression 跳過整段。

```python
def amount_painted(paint):
    parent = {}

    def find(x):
        if x not in parent:
            return x
        parent[x] = find(parent[x])
        return parent[x]

    answer = []
    for start, end in paint:
        fresh = 0
        x = find(start)
        while x < end:
            fresh += 1
            parent[x] = x + 1
            x = find(x)
        answer.append(fresh)
    return answer
```

- 時間：$O((D+q)\alpha(D))$，`D` 為最終真正粉刷的整數單位數
- 空間：$O(D)$

### Follow-up 1：原題直接變形
**問：座標是任意實數區間，不能逐單位處理？**

**答：**改維護已覆蓋 interval union。可用 ordered map 找與新區間重疊或相鄰的區間，計算新增長度後合併；或離線 coordinate compression＋segment tree。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Amount of New Area Painted Each Day》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：parent[x] 表示 x 已粉刷，下一個候選是 find(x)。每個整數單位第一次被粉刷後，將它 union 到 x+1；日後查找會透過 path compression 跳過整段。 失效情境包括：若事件持續線上到達或需要任意刪除，單次離線排序不夠；高維區間也可能無法直接 sweep。
>
> 替代路線是：改用 ordered map、interval tree、segment tree、coordinate compression，或針對二維以上做多層 sweep。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：合併題保存來源區間；排程題保存 room/resource id；skyline 題在 active maximum 改變時輸出 turning point。
>
> 套回《Amount of New Area Painted Each Day》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Calendar 類服務需處理併發預約的 transaction、時區與重試；大量座標先壓縮，並定義端點語意為 API contract。
>
> 此外必須把《Amount of New Area Painted Each Day》目前隱含的前提寫成 contract：每天粉刷整數座標 half-open 區間 [start,end)，回傳當天第一次被粉刷的單位長度。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 會先定義端點語意。
- [ ] 能選擇 merge、events、heap 或 ordered structure。
- [ ] 知道 offline query 為何可以排序。
- [ ] 能處理同座標多事件的 tie。
