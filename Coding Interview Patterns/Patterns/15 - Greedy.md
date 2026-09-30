---
title: Greedy
tags:
  - coding-interview/pattern
  - greedy
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 15 — Greedy

[[14 - Backtracking|← 上一章]] · [[00 - Book Index|目錄]] · [[16 - DP 1D and State Machine|下一章 →]]

> [!abstract] Mental model
> Greedy 不是「每次選看起來最好」。必須證明局部選擇可被某個 optimal solution 接受。常用證明是 exchange argument、stays-ahead 或維護可達範圍。

---

## 核心題 1：Jump Game


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 判斷從 index 0 能否到達最後 index。
>
> **核心轉換：** 掃描時維護目前所有可達位置能延伸到的 farthest；若 i>farthest 代表 frontier 已斷裂，否則用 i+nums[i] 擴張。
>
> **主要知識點：** Greedy Choice、Exchange Argument 與可行區間。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Jump Game
      │
      ├─ 暴力路線：枚舉所有決策序列或以 DP 保存每一步的所有歷史
      │
      ▼  找出本題最關鍵的轉換
核心觀察：掃描時維護目前所有可達位置能延伸到的 farthest；若 i>farthest 代表 frontier 已斷裂，否則用 i+nums[i] 擴張。
      │
Pattern toolbox：目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit
      │
      ├─ 狀態轉移：每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要
      │
      ├─ 永遠成立：目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 判斷從 index 0 能否到達最後 index。
2. **寫出暴力：** 枚舉所有決策序列或以 DP 保存每一步的所有歷史。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 掃描時維護目前所有可達位置能延伸到的 farthest；若 i>farthest 代表 frontier 已斷裂，否則用 i+nums[i] 擴張。
4. **定義 state 與轉移：** 使用「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」承載上述觀察，再執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」代表什麼，再說每一步如何「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功」的 base case。
>
> 2. **維持：** 每次執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」後，狀態仍與已處理資料一致。關鍵論證是：使用 exchange argument、stays-ahead 或 cut property，證明任一最優解都能轉成包含 greedy choice 的最優解。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：局部最佳不等於全域最佳、排序 tie、不可達、負成本、恰好／至多限制與 overflow。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def can_jump(nums):
    farthest = 0
    for i, jump in enumerate(nums):
        if i > farthest:
            return False
        farthest = max(farthest, i + jump)
    return True
```

**Invariant：**`[0,farthest]` 中所有位置都可由某條路徑到達。

### Follow-up 1：原題直接變形
**問：求最少 jumps？**

**答：**把目前可達區間視為 BFS layer。掃完 `[layer_start,layer_end]` 後，下一層邊界是期間看到的最遠位置。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Jump Game》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：掃描時維護目前所有可達位置能延伸到的 farthest；若 i>farthest 代表 frontier 已斷裂，否則用 i+nums[i] 擴張。 失效情境包括：找不到 exchange/stays-ahead 證明時，不應只因範例通過就相信 greedy；額外限制常使支配關係失效。
>
> 替代路線是：回到 DP、shortest path、min-cost flow、binary search on answer 或 exhaustive search 驗證小輸入。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每次實際選擇的 item/index；若摘要只存數值，另存 predecessor 才能輸出完整 greedy schedule。
>
> 套回《Jump Game》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上 greedy 需討論 competitive ratio；真實排程加入取消、公平性與資源鎖後，原 proof 必須重新建立。
>
> 此外必須把《Jump Game》目前隱含的前提寫成 contract：判斷從 index 0 能否到達最後 index。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Gas Station

### 題目

環形加油站中，找能走完整圈的起點；保證最多一解。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 環形加油站中，找能走完整圈的起點；保證最多一解。
>
> **核心轉換：** 總油量不足則無解；掃描中 current tank 一旦為負，先前區間內任何站都不能作起點，因此下一站成為新候選。
>
> **主要知識點：** Greedy Choice、Exchange Argument 與可行區間。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Gas Station
      │
      ├─ 暴力路線：枚舉所有決策序列或以 DP 保存每一步的所有歷史
      │
      ▼  找出本題最關鍵的轉換
核心觀察：總油量不足則無解；掃描中 current tank 一旦為負，先前區間內任何站都不能作起點，因此下一站成為新候選。
      │
Pattern toolbox：目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit
      │
      ├─ 狀態轉移：每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要
      │
      ├─ 永遠成立：目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 環形加油站中，找能走完整圈的起點；保證最多一解。
2. **寫出暴力：** 枚舉所有決策序列或以 DP 保存每一步的所有歷史。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 總油量不足則無解；掃描中 current tank 一旦為負，先前區間內任何站都不能作起點，因此下一站成為新候選。
4. **定義 state 與轉移：** 使用「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」承載上述觀察，再執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」代表什麼，再說每一步如何「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功」的 base case。
>
> 2. **維持：** 每次執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」後，狀態仍與已處理資料一致。關鍵論證是：使用 exchange argument、stays-ahead 或 cut property，證明任一最優解都能轉成包含 greedy choice 的最優解。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：局部最佳不等於全域最佳、排序 tie、不可達、負成本、恰好／至多限制與 overflow。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def can_complete_circuit(gas, cost):
    total = current = 0
    start = 0
    for i, (gain, spend) in enumerate(zip(gas, cost)):
        delta = gain - spend
        total += delta
        current += delta
        if current < 0:
            start = i + 1
            current = 0
    return start if total >= 0 else -1
```

**證明要點：**若從 `start` 到 `i` 累積為負，這段內任何位置作起點都無法跨過 `i`，可一起排除。

### Follow-up 1：原題直接變形
**問：回傳所有可行起點？**

**答：**單一 reset greedy 不夠。可用 doubled prefix sums＋monotonic deque，檢查每個起點後 `n` 步內 prefix 最小值是否不低於起點 prefix。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Gas Station》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：總油量不足則無解；掃描中 current tank 一旦為負，先前區間內任何站都不能作起點，因此下一站成為新候選。 失效情境包括：找不到 exchange/stays-ahead 證明時，不應只因範例通過就相信 greedy；額外限制常使支配關係失效。
>
> 替代路線是：回到 DP、shortest path、min-cost flow、binary search on answer 或 exhaustive search 驗證小輸入。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每次實際選擇的 item/index；若摘要只存數值，另存 predecessor 才能輸出完整 greedy schedule。
>
> 套回《Gas Station》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上 greedy 需討論 competitive ratio；真實排程加入取消、公平性與資源鎖後，原 proof 必須重新建立。
>
> 此外必須把《Gas Station》目前隱含的前提寫成 contract：環形加油站中，找能走完整圈的起點；保證最多一解。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Task Scheduler

### 題目

相同 task 執行間至少隔 `n` 個 interval，求完成所有 tasks 的最短時間。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 相同 task 執行間至少隔 n 個 interval，求完成所有 tasks 的最短時間。
>
> **核心轉換：** 瓶頸由最高頻 task 建立的 frame 決定；答案至少是 (maxFreq-1)(n+1)+並列最高頻 task 數，也不能小於 tasks 總數。
>
> **主要知識點：** Greedy Choice、Exchange Argument 與可行區間。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Task Scheduler
      │
      ├─ 暴力路線：枚舉所有決策序列或以 DP 保存每一步的所有歷史
      │
      ▼  找出本題最關鍵的轉換
核心觀察：瓶頸由最高頻 task 建立的 frame 決定；答案至少是 (maxFreq-1)(n+1)+並列最高頻 task 數，也不能小於 tasks 總數。
      │
Pattern toolbox：目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit
      │
      ├─ 狀態轉移：每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要
      │
      ├─ 永遠成立：目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 相同 task 執行間至少隔 n 個 interval，求完成所有 tasks 的最短時間。
2. **寫出暴力：** 枚舉所有決策序列或以 DP 保存每一步的所有歷史。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 瓶頸由最高頻 task 建立的 frame 決定；答案至少是 (maxFreq-1)(n+1)+並列最高頻 task 數，也不能小於 tasks 總數。
4. **定義 state 與轉移：** 使用「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」承載上述觀察，再執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」代表什麼，再說每一步如何「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功」的 base case。
>
> 2. **維持：** 每次執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」後，狀態仍與已處理資料一致。關鍵論證是：使用 exchange argument、stays-ahead 或 cut property，證明任一最優解都能轉成包含 greedy choice 的最優解。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：局部最佳不等於全域最佳、排序 tie、不可達、負成本、恰好／至多限制與 overflow。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
from collections import Counter

def least_interval(tasks, n):
    counts = Counter(tasks).values()
    maximum = max(counts)
    max_count = sum(value == maximum for value in counts)
    frame = (maximum - 1) * (n + 1) + max_count
    return max(len(tasks), frame)
```

### Follow-up 1：原題直接變形
**問：每種 task 有不同 cooldown？**

**答：**公式不再成立。使用 max heap 選可執行的最高剩餘頻率 task，再以 queue/min heap 管理各 task 的下一個可用時間。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Task Scheduler》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：瓶頸由最高頻 task 建立的 frame 決定；答案至少是 (maxFreq-1)(n+1)+並列最高頻 task 數，也不能小於 tasks 總數。 失效情境包括：找不到 exchange/stays-ahead 證明時，不應只因範例通過就相信 greedy；額外限制常使支配關係失效。
>
> 替代路線是：回到 DP、shortest path、min-cost flow、binary search on answer 或 exhaustive search 驗證小輸入。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每次實際選擇的 item/index；若摘要只存數值，另存 predecessor 才能輸出完整 greedy schedule。
>
> 套回《Task Scheduler》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上 greedy 需討論 competitive ratio；真實排程加入取消、公平性與資源鎖後，原 proof 必須重新建立。
>
> 此外必須把《Task Scheduler》目前隱含的前提寫成 contract：相同 task 執行間至少隔 n 個 interval，求完成所有 tasks 的最短時間。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Candy

### 題目

每位小孩至少一顆糖；rating 較高者必須比相鄰 rating 較低者多。求最少糖果。

> [!tip]- 三層提示
> 1. 左右鄰居形成兩組獨立限制。
> 2. 左到右滿足左鄰居限制。
> 3. 右到左滿足右鄰居限制，取兩者最大。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每位小孩至少一顆糖；rating 較高者必須比相鄰 rating 較低者多。求最少糖果。
>
> **核心轉換：** 第一次 pass 若 rating[i] > rating[i-1]，令糖果比左邊多一。第二次從右往左，對下降坡度補足 max(current,right+1)。
>
> **主要知識點：** Greedy Choice、Exchange Argument 與可行區間。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Candy
      │
      ├─ 暴力路線：枚舉所有決策序列或以 DP 保存每一步的所有歷史
      │
      ▼  找出本題最關鍵的轉換
核心觀察：第一次 pass 若 rating[i] > rating[i-1]，令糖果比左邊多一。第二次從右往左，對下降坡度補足 max(current,right+1)。
      │
Pattern toolbox：目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit
      │
      ├─ 狀態轉移：每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要
      │
      ├─ 永遠成立：目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每位小孩至少一顆糖；rating 較高者必須比相鄰 rating 較低者多。求最少糖果。
2. **寫出暴力：** 枚舉所有決策序列或以 DP 保存每一步的所有歷史。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 第一次 pass 若 rating[i] > rating[i-1]，令糖果比左邊多一。第二次從右往左，對下降坡度補足 max(current,right+1)。
4. **定義 state 與轉移：** 使用「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」承載上述觀察，再執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」代表什麼，再說每一步如何「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功」的 base case。
>
> 2. **維持：** 每次執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」後，狀態仍與已處理資料一致。關鍵論證是：使用 exchange argument、stays-ahead 或 cut property，證明任一最優解都能轉成包含 greedy choice 的最優解。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：局部最佳不等於全域最佳、排序 tie、不可達、負成本、恰好／至多限制與 overflow。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

第一次 pass 若 `rating[i] > rating[i-1]`，令糖果比左邊多一。第二次從右往左，對下降坡度補足 `max(current,right+1)`。

```python
def candy(ratings):
    n = len(ratings)
    candies = [1] * n
    for i in range(1, n):
        if ratings[i] > ratings[i - 1]:
            candies[i] = candies[i - 1] + 1
    for i in range(n - 2, -1, -1):
        if ratings[i] > ratings[i + 1]:
            candies[i] = max(candies[i], candies[i + 1] + 1)
    return sum(candies)
```

- 時間：$O(n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：能否 $O(1)$ 額外空間？**

**答：**可按上升、下降 slope 長度計算 mountain 貢獻，峰頂取兩側較大高度；實作較容易 off-by-one，面試先給雙 pass 穩定版本。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Candy》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：第一次 pass 若 rating[i] > rating[i-1]，令糖果比左邊多一。第二次從右往左，對下降坡度補足 max(current,right+1)。 失效情境包括：找不到 exchange/stays-ahead 證明時，不應只因範例通過就相信 greedy；額外限制常使支配關係失效。
>
> 替代路線是：回到 DP、shortest path、min-cost flow、binary search on answer 或 exhaustive search 驗證小輸入。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每次實際選擇的 item/index；若摘要只存數值，另存 predecessor 才能輸出完整 greedy schedule。
>
> 套回《Candy》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上 greedy 需討論 competitive ratio；真實排程加入取消、公平性與資源鎖後，原 proof 必須重新建立。
>
> 此外必須把《Candy》目前隱含的前提寫成 contract：每位小孩至少一顆糖；rating 較高者必須比相鄰 rating 較低者多。求最少糖果。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Minimum Number of Refueling Stops

### 題目

從 0 出發，油箱初始油量固定。每個 station 有位置與可加油量；求到 target 最少停靠數。

> [!tip]- 三層提示
> 1. 行駛到沒油前，所有已經過 stations 都是可選候選。
> 2. 需要加油時，回頭選可得油量最大的 station。
> 3. 用 max heap 保存已經過但尚未使用的油量。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 從 0 出發，油箱初始油量固定。每個 station 有位置與可加油量；求到 target 最少停靠數。
>
> **核心轉換：** 按位置 sweep。若目前油量到不了下一個 station／target，就反覆取過去最大油量。延後決定可保留最大彈性。
>
> **主要知識點：** Greedy Choice、Exchange Argument 與可行區間。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Minimum Number of Refueling Stops
      │
      ├─ 暴力路線：枚舉所有決策序列或以 DP 保存每一步的所有歷史
      │
      ▼  找出本題最關鍵的轉換
核心觀察：按位置 sweep。若目前油量到不了下一個 station／target，就反覆取過去最大油量。延後決定可保留最大彈性。
      │
Pattern toolbox：目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit
      │
      ├─ 狀態轉移：每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要
      │
      ├─ 永遠成立：目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 從 0 出發，油箱初始油量固定。每個 station 有位置與可加油量；求到 target 最少停靠數。
2. **寫出暴力：** 枚舉所有決策序列或以 DP 保存每一步的所有歷史。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 按位置 sweep。若目前油量到不了下一個 station／target，就反覆取過去最大油量。延後決定可保留最大彈性。
4. **定義 state 與轉移：** 使用「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」承載上述觀察，再執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」代表什麼，再說每一步如何「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功」的 base case。
>
> 2. **維持：** 每次執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」後，狀態仍與已處理資料一致。關鍵論證是：使用 exchange argument、stays-ahead 或 cut property，證明任一最優解都能轉成包含 greedy choice 的最優解。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：局部最佳不等於全域最佳、排序 tie、不可達、負成本、恰好／至多限制與 overflow。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

按位置 sweep。若目前油量到不了下一個 station／target，就反覆取過去最大油量。延後決定可保留最大彈性。

```python
from heapq import heappush, heappop

def min_refuel_stops(target, start_fuel, stations):
    heap = []
    fuel = start_fuel
    stops = 0
    for position, amount in stations + [[target, 0]]:
        while fuel < position and heap:
            fuel -= heappop(heap)
            stops += 1
        if fuel < position:
            return -1
        heappush(heap, -amount)
    return stops
```

### Follow-up 1：原題直接變形
**問：油箱有容量上限？**

**答：**回頭一次加入整站油量的模型可能違反容量，greedy proof 失效。需以位置與剩餘油量做 DP／shortest path，或根據補給規則重新建模。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Minimum Number of Refueling Stops》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：按位置 sweep。若目前油量到不了下一個 station／target，就反覆取過去最大油量。延後決定可保留最大彈性。 失效情境包括：找不到 exchange/stays-ahead 證明時，不應只因範例通過就相信 greedy；額外限制常使支配關係失效。
>
> 替代路線是：回到 DP、shortest path、min-cost flow、binary search on answer 或 exhaustive search 驗證小輸入。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每次實際選擇的 item/index；若摘要只存數值，另存 predecessor 才能輸出完整 greedy schedule。
>
> 套回《Minimum Number of Refueling Stops》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上 greedy 需討論 competitive ratio；真實排程加入取消、公平性與資源鎖後，原 proof 必須重新建立。
>
> 此外必須把《Minimum Number of Refueling Stops》目前隱含的前提寫成 contract：從 0 出發，油箱初始油量固定。每個 station 有位置與可加油量；求到 target 最少停靠數。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Course Schedule III

### 題目

每門課有 duration 與 deadline；一次只能上一門，求最多能完成幾門。

> [!tip]- 三層提示
> 1. 依 deadline 早到晚處理。
> 2. 先把課加入；若總時間超過目前 deadline，刪除已選課中 duration 最長者。
> 3. 刪最長課能為未來釋放最多時間，且不減少已選課數。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每門課有 duration 與 deadline；一次只能上一門，求最多能完成幾門。
>
> **核心轉換：** Max heap 保存已選 durations。每次超時，移除最長課；對相同課程數，此策略使總使用時間最小，因此最有利於未來。
>
> **主要知識點：** Greedy Choice、Exchange Argument 與可行區間。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Course Schedule III
      │
      ├─ 暴力路線：枚舉所有決策序列或以 DP 保存每一步的所有歷史
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Max heap 保存已選 durations。每次超時，移除最長課；對相同課程數，此策略使總使用時間最小，因此最有利於未來。
      │
Pattern toolbox：目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit
      │
      ├─ 狀態轉移：每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要
      │
      ├─ 永遠成立：目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每門課有 duration 與 deadline；一次只能上一門，求最多能完成幾門。
2. **寫出暴力：** 枚舉所有決策序列或以 DP 保存每一步的所有歷史。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Max heap 保存已選 durations。每次超時，移除最長課；對相同課程數，此策略使總使用時間最小，因此最有利於未來。
4. **定義 state 與轉移：** 使用「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」承載上述觀察，再執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」代表什麼，再說每一步如何「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功」的 base case。
>
> 2. **維持：** 每次執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」後，狀態仍與已處理資料一致。關鍵論證是：使用 exchange argument、stays-ahead 或 cut property，證明任一最優解都能轉成包含 greedy choice 的最優解。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：局部最佳不等於全域最佳、排序 tie、不可達、負成本、恰好／至多限制與 overflow。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Max heap 保存已選 durations。每次超時，移除最長課；對相同課程數，此策略使總使用時間最小，因此最有利於未來。

```python
from heapq import heappush, heappop

def schedule_course(courses):
    courses.sort(key=lambda item: item[1])
    durations = []
    total = 0
    for duration, deadline in courses:
        total += duration
        heappush(durations, -duration)
        if total > deadline:
            total += heappop(durations)
    return len(durations)
```

- 時間：$O(n\log n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：每門課有不同價值，要最大化總價值？**

**答：**刪最長 duration 不再保證最優；這變成 deadline knapsack 類 DP，依 deadline／總時間更新最大價值。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Course Schedule III》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Max heap 保存已選 durations。每次超時，移除最長課；對相同課程數，此策略使總使用時間最小，因此最有利於未來。 失效情境包括：找不到 exchange/stays-ahead 證明時，不應只因範例通過就相信 greedy；額外限制常使支配關係失效。
>
> 替代路線是：回到 DP、shortest path、min-cost flow、binary search on answer 或 exhaustive search 驗證小輸入。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每次實際選擇的 item/index；若摘要只存數值，另存 predecessor 才能輸出完整 greedy schedule。
>
> 套回《Course Schedule III》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上 greedy 需討論 competitive ratio；真實排程加入取消、公平性與資源鎖後，原 proof 必須重新建立。
>
> 此外必須把《Course Schedule III》目前隱含的前提寫成 contract：每門課有 duration 與 deadline；一次只能上一門，求最多能完成幾門。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Patching Array

### 題目

排序正整數陣列中可加入最少數字，使 `[1,n]` 每個值都能表示成某個 subset sum。

> [!tip]- 三層提示
> 1. 維護目前可表示連續範圍 `[1,miss)`。
> 2. 若下一數 `x <= miss`，範圍可延伸到 `miss+x`。
> 3. 若 `x > miss`，唯一最有效 patch 是 `miss`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 排序正整數陣列中可加入最少數字，使 [1,n] 每個值都能表示成某個 subset sum。
>
> **核心轉換：** 當 [1,miss) 都可表示：
>
> **主要知識點：** Greedy Choice、Exchange Argument 與可行區間。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Patching Array
      │
      ├─ 暴力路線：枚舉所有決策序列或以 DP 保存每一步的所有歷史
      │
      ▼  找出本題最關鍵的轉換
核心觀察：當 [1,miss) 都可表示：
      │
Pattern toolbox：目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit
      │
      ├─ 狀態轉移：每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要
      │
      ├─ 永遠成立：目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 排序正整數陣列中可加入最少數字，使 [1,n] 每個值都能表示成某個 subset sum。
2. **寫出暴力：** 枚舉所有決策序列或以 DP 保存每一步的所有歷史。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 當 [1,miss) 都可表示：
4. **定義 state 與轉移：** 使用「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」承載上述觀察，再執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(len(nums)+\log n)$；空間：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」代表什麼，再說每一步如何「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功」的 base case。
>
> 2. **維持：** 每次執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」後，狀態仍與已處理資料一致。關鍵論證是：使用 exchange argument、stays-ahead 或 cut property，證明任一最優解都能轉成包含 greedy choice 的最優解。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：局部最佳不等於全域最佳、排序 tie、不可達、負成本、恰好／至多限制與 overflow。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

當 `[1,miss)` 都可表示：

- 加入 `x <= miss`，可表示原範圍與每個值加 x，合併成 `[1,miss+x)`。
- 若 x 太大，`miss` 本身無法表示；patch `miss` 可把範圍翻倍到 `[1,2*miss)`，是最大延伸。

```python
def min_patches(nums, n):
    miss = 1
    index = patches = 0
    while miss <= n:
        if index < len(nums) and nums[index] <= miss:
            miss += nums[index]
            index += 1
        else:
            miss += miss
            patches += 1
    return patches
```

- 時間：$O(len(nums)+\log n)$
- 空間：$O(1)$

### Follow-up 1：原題直接變形
**問：nums 含零或負數？**

**答：**連續覆蓋 proof 依賴所有數為正；零不延伸範圍，負數使 subset-sum 結構完全不同，不能套用此 greedy。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Patching Array》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：當 [1,miss) 都可表示： 失效情境包括：找不到 exchange/stays-ahead 證明時，不應只因範例通過就相信 greedy；額外限制常使支配關係失效。
>
> 替代路線是：回到 DP、shortest path、min-cost flow、binary search on answer 或 exhaustive search 驗證小輸入。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每次實際選擇的 item/index；若摘要只存數值，另存 predecessor 才能輸出完整 greedy schedule。
>
> 套回《Patching Array》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上 greedy 需討論 competitive ratio；真實排程加入取消、公平性與資源鎖後，原 proof 必須重新建立。
>
> 此外必須把《Patching Array》目前隱含的前提寫成 contract：排序正整數陣列中可加入最少數字，使 [1,n] 每個值都能表示成某個 subset sum。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Minimum Initial Energy to Finish Tasks

### 題目

每個 task 為 `[actual_cost, minimum_required]`。開始 task 前能量至少為 minimum，完成後扣 actual；可任意排序，求最小初始能量。

> [!tip]- 三層提示
> 1. 高「門檻與消耗差」的 task 應較早做。
> 2. 依 `minimum - actual` 降序。
> 3. 掃描時，初始能量至少要覆蓋 `spent + minimum`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每個 task 為 [actualcost, minimumrequired]。開始 task 前能量至少為 minimum，完成後扣 actual；可任意排序，求最小初始能量。
>
> **核心轉換：** 排序後維護已消耗 spent。執行目前 task 前，初始能量至少為 spent + minimum。Pairwise exchange 可證明較大 minimum-actual 放前不會需要更多初始能量。
>
> **主要知識點：** Greedy Choice、Exchange Argument 與可行區間。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Minimum Initial Energy to Finish Tasks
      │
      ├─ 暴力路線：枚舉所有決策序列或以 DP 保存每一步的所有歷史
      │
      ▼  找出本題最關鍵的轉換
核心觀察：排序後維護已消耗 spent。執行目前 task 前，初始能量至少為 spent + minimum。Pairwise exchange 可證明較大 minimum-actual 放前不會需要更多初始能量。
      │
Pattern toolbox：目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit
      │
      ├─ 狀態轉移：每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要
      │
      ├─ 永遠成立：目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每個 task 為 [actualcost, minimumrequired]。開始 task 前能量至少為 minimum，完成後扣 actual；可任意排序，求最小初始能量。
2. **寫出暴力：** 枚舉所有決策序列或以 DP 保存每一步的所有歷史。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 排序後維護已消耗 spent。執行目前 task 前，初始能量至少為 spent + minimum。Pairwise exchange 可證明較大 minimum-actual 放前不會需要更多初始能量。
4. **定義 state 與轉移：** 使用「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」承載上述觀察，再執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log n)$；空間：排序空間

> [!tip] 一句話記憶
> 先說清楚「目前可達最遠位置、最小成本 frontier、排序後的候選，或尚未滿足的 deficit」代表什麼，再說每一步如何「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「目前摘要支配所有已看過的其他歷史；若摘要失敗，任何被支配歷史也不可能成功」的 base case。
>
> 2. **維持：** 每次執行「每一步選一個可證明不劣的局部決策，並只保留未來真正需要的摘要」後，狀態仍與已處理資料一致。關鍵論證是：使用 exchange argument、stays-ahead 或 cut property，證明任一最優解都能轉成包含 greedy choice 的最優解。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：局部最佳不等於全域最佳、排序 tie、不可達、負成本、恰好／至多限制與 overflow。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

排序後維護已消耗 `spent`。執行目前 task 前，初始能量至少為 `spent + minimum`。Pairwise exchange 可證明較大 `minimum-actual` 放前不會需要更多初始能量。

```python
def minimum_effort(tasks):
    tasks.sort(key=lambda task: task[1] - task[0], reverse=True)
    spent = answer = 0
    for actual, minimum in tasks:
        answer = max(answer, spent + minimum)
        spent += actual
    return answer
```

- 時間：$O(n\log n)$
- 空間：排序空間

### Follow-up 1：原題直接變形
**問：完成 task 可能獲得能量，actual 可為負數？**

**答：**上述 ordering proof 需重新推導。常見策略是先做能增加能量且可啟動的 tasks，但整體可能變成 scheduling／heap 問題，不能直接沿用 comparator。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Minimum Initial Energy to Finish Tasks》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：排序後維護已消耗 spent。執行目前 task 前，初始能量至少為 spent + minimum。Pairwise exchange 可證明較大 minimum-actual 放前不會需要更多初始能量。 失效情境包括：找不到 exchange/stays-ahead 證明時，不應只因範例通過就相信 greedy；額外限制常使支配關係失效。
>
> 替代路線是：回到 DP、shortest path、min-cost flow、binary search on answer 或 exhaustive search 驗證小輸入。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存每次實際選擇的 item/index；若摘要只存數值，另存 predecessor 才能輸出完整 greedy schedule。
>
> 套回《Minimum Initial Energy to Finish Tasks》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 線上 greedy 需討論 competitive ratio；真實排程加入取消、公平性與資源鎖後，原 proof 必須重新建立。
>
> 此外必須把《Minimum Initial Energy to Finish Tasks》目前隱含的前提寫成 contract：每個 task 為 [actualcost, minimumrequired]。開始 task 前能量至少為 minimum，完成後扣 actual；可任意排序，求最小初始能量。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 能提出 exchange 或 stays-ahead proof。
- [ ] 知道「延後決定」常與 heap 結合。
- [ ] 會辨認 coverage interval invariant。
- [ ] 限制改動後會重新驗證 greedy，而不是硬套。
