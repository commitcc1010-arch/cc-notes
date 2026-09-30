---
title: Heap Top-K and K-way Merge
tags:
  - coding-interview/pattern
  - heap
  - top-k
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 11 — Heap, Top-K and K-way Merge

[[10 - BST and Trie|← 上一章]] · [[00 - Book Index|目錄]] · [[12 - Graph DFS and BFS|下一章 →]]

> [!abstract] Mental model
> Heap 不維持完整排序，只保證能快速取得目前最小或最大候選。當只需要 top K、動態 median、或多條排序序列的下一個元素時，完整排序通常是多做的工作。

---

## 核心題 1：Kth Largest Element


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 找未排序陣列中的第 k 大元素。
>
> **核心轉換：** 維持 size k 的 min heap：root 是目前看過元素中的第 k 大門檻；新元素進 heap 後若超過 k，就淘汰最小者。
>
> **主要知識點：** Heap、Top-K 與 K-way Merge。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Kth Largest Element
      │
      ├─ 暴力路線：反覆排序全部候選，或每次都線性尋找目前最小／最大值
      │
      ▼  找出本題最關鍵的轉換
核心觀察：維持 size k 的 min heap：root 是目前看過元素中的第 k 大門檻；新元素進 heap 後若超過 k，就淘汰最小者。
      │
Pattern toolbox：size-k heap 或由多條已排序序列各提供一個 frontier 的 heap
      │
      ├─ 狀態轉移：加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列
      │
      ├─ 永遠成立：heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 找未排序陣列中的第 k 大元素。
2. **寫出暴力：** 反覆排序全部候選，或每次都線性尋找目前最小／最大值。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 維持 size k 的 min heap：root 是目前看過元素中的第 k 大門檻；新元素進 heap 後若超過 k，就淘汰最小者。
4. **定義 state 與轉移：** 使用「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」承載上述觀察，再執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log k)$；空間：$O(k)$

> [!tip] 一句話記憶
> 先說清楚「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」代表什麼，再說每一步如何「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻」的 base case。
>
> 2. **維持：** 每次執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」後，狀態仍與已處理資料一致。關鍵論證是：證明被丟棄者不可能優於 heap 內門檻，或 k-way merge 每次 pop 都是所有未輸出元素的全域最小。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：min/max heap 符號、tie breaker、lazy deletion、空 heap、k 大於元素數與 mutable key。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
from heapq import heappush, heappop

def find_kth_largest(nums, k):
    heap = []
    for x in nums:
        heappush(heap, x)
        if len(heap) > k:
            heappop(heap)
    return heap[0]
```

**Invariant：**heap 永遠保存目前看過的最大 `k` 個元素。

- 時間：$O(n\log k)$
- 空間：$O(k)$

### Follow-up 1：原題直接變形
**問：平均 $O(n)$ 解法？**

**答：**Quickselect partition，尋找排序後 index `n-k`；平均 $O(n)$、worst case $O(n^2)$，隨機 pivot 可降低風險。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Kth Largest Element》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：維持 size k 的 min heap：root 是目前看過元素中的第 k 大門檻；新元素進 heap 後若超過 k，就淘汰最小者。 失效情境包括：需要任意刪除、rank query 或所有順序統計時，heap 單獨不夠；k 接近 n 時完整排序可能更簡單。
>
> 替代路線是：改用 quickselect、balanced tree、bucket counting、two heaps＋delayed deletion 或 tournament tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：heap entry 保存來源 index、list id、parent 或選擇紀錄；pop 時便可輸出原物件與重建合併路徑。
>
> 套回《Kth Largest Element》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming top-k 需定義時間窗與近似誤差；distributed top-k 可先做 local top-k 再 merge，並處理 stale heap entries。
>
> 此外必須把《Kth Largest Element》目前隱含的前提寫成 contract：找未排序陣列中的第 k 大元素。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Top K Frequent Elements


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 回傳出現頻率最高的 k 個不同元素。
>
> **核心轉換：** 先用 hash 計頻率，再用 size-k heap、bucket by frequency 或 quickselect 選出 top k；核心是比較 distinct keys 而非原陣列元素。
>
> **主要知識點：** Heap、Top-K 與 K-way Merge。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Top K Frequent Elements
      │
      ├─ 暴力路線：反覆排序全部候選，或每次都線性尋找目前最小／最大值
      │
      ▼  找出本題最關鍵的轉換
核心觀察：先用 hash 計頻率，再用 size-k heap、bucket by frequency 或 quickselect 選出 top k；核心是比較 distinct keys 而非原陣列元素。
      │
Pattern toolbox：size-k heap 或由多條已排序序列各提供一個 frontier 的 heap
      │
      ├─ 狀態轉移：加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列
      │
      ├─ 永遠成立：heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 回傳出現頻率最高的 k 個不同元素。
2. **寫出暴力：** 反覆排序全部候選，或每次都線性尋找目前最小／最大值。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 先用 hash 計頻率，再用 size-k heap、bucket by frequency 或 quickselect 選出 top k；核心是比較 distinct keys 而非原陣列元素。
4. **定義 state 與轉移：** 使用「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」承載上述觀察，再執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」代表什麼，再說每一步如何「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻」的 base case。
>
> 2. **維持：** 每次執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」後，狀態仍與已處理資料一致。關鍵論證是：證明被丟棄者不可能優於 heap 內門檻，或 k-way merge 每次 pop 都是所有未輸出元素的全域最小。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：min/max heap 符號、tie breaker、lazy deletion、空 heap、k 大於元素數與 mutable key。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
from collections import Counter
from heapq import nlargest

def top_k_frequent(nums, k):
    frequency = Counter(nums)
    return nlargest(k, frequency, key=frequency.get)
```

### Follow-up 1：原題直接變形
**問：要求 $O(n)$？**

**答：**frequency 最大不超過 `n`，建立 `buckets[count]`，由大到小收集到 `k` 個；這是 counting/bucket sort。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Top K Frequent Elements》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：先用 hash 計頻率，再用 size-k heap、bucket by frequency 或 quickselect 選出 top k；核心是比較 distinct keys 而非原陣列元素。 失效情境包括：需要任意刪除、rank query 或所有順序統計時，heap 單獨不夠；k 接近 n 時完整排序可能更簡單。
>
> 替代路線是：改用 quickselect、balanced tree、bucket counting、two heaps＋delayed deletion 或 tournament tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：heap entry 保存來源 index、list id、parent 或選擇紀錄；pop 時便可輸出原物件與重建合併路徑。
>
> 套回《Top K Frequent Elements》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming top-k 需定義時間窗與近似誤差；distributed top-k 可先做 local top-k 再 merge，並處理 stale heap entries。
>
> 此外必須把《Top K Frequent Elements》目前隱含的前提寫成 contract：回傳出現頻率最高的 k 個不同元素。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Find Median from Data Stream


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 支援持續加入數字，並隨時回傳目前 median。
>
> **核心轉換：** low max heap 保存較小一半，high min heap 保存較大一半。保持 len(low) 等於 len(high) 或多一。
>
> **主要知識點：** Heap、Top-K 與 K-way Merge。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Find Median from Data Stream
      │
      ├─ 暴力路線：反覆排序全部候選，或每次都線性尋找目前最小／最大值
      │
      ▼  找出本題最關鍵的轉換
核心觀察：low max heap 保存較小一半，high min heap 保存較大一半。保持 len(low) 等於 len(high) 或多一。
      │
Pattern toolbox：size-k heap 或由多條已排序序列各提供一個 frontier 的 heap
      │
      ├─ 狀態轉移：加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列
      │
      ├─ 永遠成立：heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 支援持續加入數字，並隨時回傳目前 median。
2. **寫出暴力：** 反覆排序全部候選，或每次都線性尋找目前最小／最大值。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** low max heap 保存較小一半，high min heap 保存較大一半。保持 len(low) 等於 len(high) 或多一。
4. **定義 state 與轉移：** 使用「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」承載上述觀察，再執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」代表什麼，再說每一步如何「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻」的 base case。
>
> 2. **維持：** 每次執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」後，狀態仍與已處理資料一致。關鍵論證是：證明被丟棄者不可能優於 heap 內門檻，或 k-way merge 每次 pop 都是所有未輸出元素的全域最小。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：min/max heap 符號、tie breaker、lazy deletion、空 heap、k 大於元素數與 mutable key。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 推導

`low` max heap 保存較小一半，`high` min heap 保存較大一半。保持 `len(low)` 等於 `len(high)` 或多一。

```python
from heapq import heappush, heappop

class MedianFinder:
    def __init__(self):
        self.low = []
        self.high = []

    def addNum(self, num):
        heappush(self.low, -num)
        heappush(self.high, -heappop(self.low))
        if len(self.high) > len(self.low):
            heappush(self.low, -heappop(self.high))

    def findMedian(self):
        if len(self.low) > len(self.high):
            return -self.low[0]
        return (-self.low[0] + self.high[0]) / 2
```

### Follow-up 1：原題直接變形
**問：數值範圍固定在 `0..100`？**

**答：**用長度 101 的 counting array，查 median 時累加頻率即可；插入 $O(1)$、查詢 $O(100)$，可視為常數。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Find Median from Data Stream》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：low max heap 保存較小一半，high min heap 保存較大一半。保持 len(low) 等於 len(high) 或多一。 失效情境包括：需要任意刪除、rank query 或所有順序統計時，heap 單獨不夠；k 接近 n 時完整排序可能更簡單。
>
> 替代路線是：改用 quickselect、balanced tree、bucket counting、two heaps＋delayed deletion 或 tournament tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：heap entry 保存來源 index、list id、parent 或選擇紀錄；pop 時便可輸出原物件與重建合併路徑。
>
> 套回《Find Median from Data Stream》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming top-k 需定義時間窗與近似誤差；distributed top-k 可先做 local top-k 再 merge，並處理 stale heap entries。
>
> 此外必須把《Find Median from Data Stream》目前隱含的前提寫成 contract：支援持續加入數字，並隨時回傳目前 median。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Sliding Window Median

### 題目

回傳每個長度 `k` 的 window median。

> [!tip]- 三層提示
> 1. 沿用雙 heap，但現在還要刪除離開 window 的元素。
> 2. Heap 不支援刪除任意元素，使用 delayed deletion。
> 3. 額外維護兩個 heap 的「有效大小」，在 heap top 失效時 prune。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 回傳每個長度 k 的 window median。
>
> **核心轉換：** small 是 max heap、large 是 min heap。delayed[value] 記錄等待刪除次數。移除元素時只減有效 size；若它碰巧在 heap top，才真正彈出。
>
> **主要知識點：** Heap、Top-K 與 K-way Merge。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Sliding Window Median
      │
      ├─ 暴力路線：反覆排序全部候選，或每次都線性尋找目前最小／最大值
      │
      ▼  找出本題最關鍵的轉換
核心觀察：small 是 max heap、large 是 min heap。delayed[value] 記錄等待刪除次數。移除元素時只減有效 size；若它碰巧在 heap top，才真正彈出。
      │
Pattern toolbox：size-k heap 或由多條已排序序列各提供一個 frontier 的 heap
      │
      ├─ 狀態轉移：加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列
      │
      ├─ 永遠成立：heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 回傳每個長度 k 的 window median。
2. **寫出暴力：** 反覆排序全部候選，或每次都線性尋找目前最小／最大值。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** small 是 max heap、large 是 min heap。delayed[value] 記錄等待刪除次數。移除元素時只減有效 size；若它碰巧在 heap top，才真正彈出。
4. **定義 state 與轉移：** 使用「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」承載上述觀察，再執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log k)$ amortized；空間：$O(k)$ 有效元素，加 lazy entries

> [!tip] 一句話記憶
> 先說清楚「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」代表什麼，再說每一步如何「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻」的 base case。
>
> 2. **維持：** 每次執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」後，狀態仍與已處理資料一致。關鍵論證是：證明被丟棄者不可能優於 heap 內門檻，或 k-way merge 每次 pop 都是所有未輸出元素的全域最小。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：min/max heap 符號、tie breaker、lazy deletion、空 heap、k 大於元素數與 mutable key。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

`small` 是 max heap、`large` 是 min heap。`delayed[value]` 記錄等待刪除次數。移除元素時只減有效 size；若它碰巧在 heap top，才真正彈出。

```python
from collections import defaultdict
from heapq import heappush, heappop

class DualHeap:
    def __init__(self, k):
        self.small = []
        self.large = []
        self.delayed = defaultdict(int)
        self.small_size = 0
        self.large_size = 0
        self.k = k

    def prune(self, heap):
        while heap:
            value = -heap[0] if heap is self.small else heap[0]
            if self.delayed[value] == 0:
                break
            self.delayed[value] -= 1
            heappop(heap)

    def balance(self):
        if self.small_size > self.large_size + 1:
            heappush(self.large, -heappop(self.small))
            self.small_size -= 1
            self.large_size += 1
            self.prune(self.small)
        elif self.small_size < self.large_size:
            heappush(self.small, -heappop(self.large))
            self.small_size += 1
            self.large_size -= 1
            self.prune(self.large)

    def add(self, value):
        if not self.small or value <= -self.small[0]:
            heappush(self.small, -value)
            self.small_size += 1
        else:
            heappush(self.large, value)
            self.large_size += 1
        self.balance()

    def remove(self, value):
        self.delayed[value] += 1
        if value <= -self.small[0]:
            self.small_size -= 1
            if value == -self.small[0]:
                self.prune(self.small)
        else:
            self.large_size -= 1
            if self.large and value == self.large[0]:
                self.prune(self.large)
        self.balance()

    def median(self):
        if self.k % 2:
            return -self.small[0]
        return (-self.small[0] + self.large[0]) / 2


def median_sliding_window(nums, k):
    dh = DualHeap(k)
    for x in nums[:k]:
        dh.add(x)
    answer = [dh.median()]
    for i in range(k, len(nums)):
        dh.add(nums[i])
        dh.remove(nums[i - k])
        answer.append(dh.median())
    return answer
```

- 時間：$O(n\log k)$ amortized
- 空間：$O(k)$ 有效元素，加 lazy entries

### Follow-up 1：原題直接變形
**問：為何不能只比較待刪值與 partition boundary 判斷它在哪個 heap？**

**答：**即使重複值跨兩個 heap，刪除任一相同值都不影響 multiset 語意；有效 size 與 lazy count 最終會在正確 top 被消耗，因此以 boundary 分類仍可維持數量 invariant。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Sliding Window Median》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：small 是 max heap、large 是 min heap。delayed[value] 記錄等待刪除次數。移除元素時只減有效 size；若它碰巧在 heap top，才真正彈出。 失效情境包括：需要任意刪除、rank query 或所有順序統計時，heap 單獨不夠；k 接近 n 時完整排序可能更簡單。
>
> 替代路線是：改用 quickselect、balanced tree、bucket counting、two heaps＋delayed deletion 或 tournament tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：heap entry 保存來源 index、list id、parent 或選擇紀錄；pop 時便可輸出原物件與重建合併路徑。
>
> 套回《Sliding Window Median》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming top-k 需定義時間窗與近似誤差；distributed top-k 可先做 local top-k 再 merge，並處理 stale heap entries。
>
> 此外必須把《Sliding Window Median》目前隱含的前提寫成 contract：回傳每個長度 k 的 window median。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Smallest Range Covering Elements from K Lists

### 題目

每個 list 已排序，找最短區間，使每個 list 至少有一個元素落在其中。

> [!tip]- 三層提示
> 1. Heap 保存每個 list 目前選中的元素。
> 2. 同時追蹤目前最大值。
> 3. 每次只能前進最小值所屬 list；其他前進不會改善左邊界。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每個 list 已排序，找最短區間，使每個 list 至少有一個元素落在其中。
>
> **核心轉換：** Heap 有 k 個候選。當前 range 是 [heapmin,currentmax]。彈出最小值並把同 list 下一值推入；某 list 用完時無法再覆蓋全部 lists，結束。
>
> **主要知識點：** Heap、Top-K 與 K-way Merge。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Smallest Range Covering Elements from K Lists
      │
      ├─ 暴力路線：反覆排序全部候選，或每次都線性尋找目前最小／最大值
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Heap 有 k 個候選。當前 range 是 [heapmin,currentmax]。彈出最小值並把同 list 下一值推入；某 list 用完時無法再覆蓋全部 lists，結束。
      │
Pattern toolbox：size-k heap 或由多條已排序序列各提供一個 frontier 的 heap
      │
      ├─ 狀態轉移：加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列
      │
      ├─ 永遠成立：heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每個 list 已排序，找最短區間，使每個 list 至少有一個元素落在其中。
2. **寫出暴力：** 反覆排序全部候選，或每次都線性尋找目前最小／最大值。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Heap 有 k 個候選。當前 range 是 [heapmin,currentmax]。彈出最小值並把同 list 下一值推入；某 list 用完時無法再覆蓋全部 lists，結束。
4. **定義 state 與轉移：** 使用「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」承載上述觀察，再執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(N\log k)$；空間：$O(k)$

> [!tip] 一句話記憶
> 先說清楚「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」代表什麼，再說每一步如何「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻」的 base case。
>
> 2. **維持：** 每次執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」後，狀態仍與已處理資料一致。關鍵論證是：證明被丟棄者不可能優於 heap 內門檻，或 k-way merge 每次 pop 都是所有未輸出元素的全域最小。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：min/max heap 符號、tie breaker、lazy deletion、空 heap、k 大於元素數與 mutable key。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Heap 有 `k` 個候選。當前 range 是 `[heap_min,current_max]`。彈出最小值並把同 list 下一值推入；某 list 用完時無法再覆蓋全部 lists，結束。

```python
from heapq import heapify, heappop, heappush

def smallest_range(nums):
    heap = []
    current_max = float("-inf")
    for row, values in enumerate(nums):
        heap.append((values[0], row, 0))
        current_max = max(current_max, values[0])
    heapify(heap)

    best_left, best_right = heap[0][0], current_max
    while True:
        value, row, index = heappop(heap)
        if current_max - value < best_right - best_left:
            best_left, best_right = value, current_max
        if index + 1 == len(nums[row]):
            break
        next_value = nums[row][index + 1]
        current_max = max(current_max, next_value)
        heappush(heap, (next_value, row, index + 1))
    return [best_left, best_right]
```

- 時間：$O(N\log k)$
- 空間：$O(k)$

### Follow-up 1：原題直接變形
**問：相同長度時要較小 left？**

**答：**更新條件改為比較 tuple `(right-left,left)`，Python 可直接比較。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Smallest Range Covering Elements from K Lists》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Heap 有 k 個候選。當前 range 是 [heapmin,currentmax]。彈出最小值並把同 list 下一值推入；某 list 用完時無法再覆蓋全部 lists，結束。 失效情境包括：需要任意刪除、rank query 或所有順序統計時，heap 單獨不夠；k 接近 n 時完整排序可能更簡單。
>
> 替代路線是：改用 quickselect、balanced tree、bucket counting、two heaps＋delayed deletion 或 tournament tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：heap entry 保存來源 index、list id、parent 或選擇紀錄；pop 時便可輸出原物件與重建合併路徑。
>
> 套回《Smallest Range Covering Elements from K Lists》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming top-k 需定義時間窗與近似誤差；distributed top-k 可先做 local top-k 再 merge，並處理 stale heap entries。
>
> 此外必須把《Smallest Range Covering Elements from K Lists》目前隱含的前提寫成 contract：每個 list 已排序，找最短區間，使每個 list 至少有一個元素落在其中。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：IPO

### 題目

最多完成 `k` 個專案。每個專案有啟動資本與利潤；完成後資本增加。求最大最終資本。

> [!tip]- 三層提示
> 1. 依 required capital 排序。
> 2. 當前可做專案中，選 profit 最大者。
> 3. Sweep capital 並用 max heap 保存已解鎖 profits。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 最多完成 k 個專案。每個專案有啟動資本與利潤；完成後資本增加。求最大最終資本。
>
> **核心轉換：** 每輪把所有 required <= capital 的專案加入 heap。選最大 profit 是安全的：它不會降低未來資本，只會解鎖至少同樣多的專案。
>
> **主要知識點：** Heap、Top-K 與 K-way Merge。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：IPO
      │
      ├─ 暴力路線：反覆排序全部候選，或每次都線性尋找目前最小／最大值
      │
      ▼  找出本題最關鍵的轉換
核心觀察：每輪把所有 required <= capital 的專案加入 heap。選最大 profit 是安全的：它不會降低未來資本，只會解鎖至少同樣多的專案。
      │
Pattern toolbox：size-k heap 或由多條已排序序列各提供一個 frontier 的 heap
      │
      ├─ 狀態轉移：加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列
      │
      ├─ 永遠成立：heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 最多完成 k 個專案。每個專案有啟動資本與利潤；完成後資本增加。求最大最終資本。
2. **寫出暴力：** 反覆排序全部候選，或每次都線性尋找目前最小／最大值。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 每輪把所有 required <= capital 的專案加入 heap。選最大 profit 是安全的：它不會降低未來資本，只會解鎖至少同樣多的專案。
4. **定義 state 與轉移：** 使用「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」承載上述觀察，再執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log n+k\log n)$；空間：$O(n)$

> [!tip] 一句話記憶
> 先說清楚「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」代表什麼，再說每一步如何「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻」的 base case。
>
> 2. **維持：** 每次執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」後，狀態仍與已處理資料一致。關鍵論證是：證明被丟棄者不可能優於 heap 內門檻，或 k-way merge 每次 pop 都是所有未輸出元素的全域最小。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：min/max heap 符號、tie breaker、lazy deletion、空 heap、k 大於元素數與 mutable key。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

每輪把所有 `required <= capital` 的專案加入 heap。選最大 profit 是安全的：它不會降低未來資本，只會解鎖至少同樣多的專案。

```python
from heapq import heappush, heappop

def find_maximized_capital(k, capital, profits, required):
    projects = sorted(zip(required, profits))
    heap = []
    index = 0
    for _ in range(k):
        while index < len(projects) and projects[index][0] <= capital:
            heappush(heap, -projects[index][1])
            index += 1
        if not heap:
            break
        capital -= heappop(heap)
    return capital
```

- 時間：$O(n\log n+k\log n)$
- 空間：$O(n)$

### Follow-up 1：原題直接變形
**問：profit 可以是負數？**

**答：**因為最多做 `k` 個，不是恰好做，heap 最大 profit 若不大於零就應停止；負 profit 可能降低資本並失去選項。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《IPO》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：每輪把所有 required <= capital 的專案加入 heap。選最大 profit 是安全的：它不會降低未來資本，只會解鎖至少同樣多的專案。 失效情境包括：需要任意刪除、rank query 或所有順序統計時，heap 單獨不夠；k 接近 n 時完整排序可能更簡單。
>
> 替代路線是：改用 quickselect、balanced tree、bucket counting、two heaps＋delayed deletion 或 tournament tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：heap entry 保存來源 index、list id、parent 或選擇紀錄；pop 時便可輸出原物件與重建合併路徑。
>
> 套回《IPO》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming top-k 需定義時間窗與近似誤差；distributed top-k 可先做 local top-k 再 merge，並處理 stale heap entries。
>
> 此外必須把《IPO》目前隱含的前提寫成 contract：最多完成 k 個專案。每個專案有啟動資本與利潤；完成後資本增加。求最大最終資本。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Maximum Performance of a Team

### 題目

選最多 `k` 位工程師，performance 為速度總和乘以團隊最低效率。

> [!tip]- 三層提示
> 1. 依 efficiency 由高到低枚舉。
> 2. 當處理某人時，他的 efficiency 是目前候選團隊的最低值。
> 3. 只需維持最大的 `k` 個 speeds。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 選最多 k 位工程師，performance 為速度總和乘以團隊最低效率。
>
> **核心轉換：** 按效率降序。加入目前 speed，若超過 k 人就移除最小 speed。此時 heap 中 speed sum 在目前最低效率下最大。
>
> **主要知識點：** Heap、Top-K 與 K-way Merge。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Maximum Performance of a Team
      │
      ├─ 暴力路線：反覆排序全部候選，或每次都線性尋找目前最小／最大值
      │
      ▼  找出本題最關鍵的轉換
核心觀察：按效率降序。加入目前 speed，若超過 k 人就移除最小 speed。此時 heap 中 speed sum 在目前最低效率下最大。
      │
Pattern toolbox：size-k heap 或由多條已排序序列各提供一個 frontier 的 heap
      │
      ├─ 狀態轉移：加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列
      │
      ├─ 永遠成立：heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 選最多 k 位工程師，performance 為速度總和乘以團隊最低效率。
2. **寫出暴力：** 反覆排序全部候選，或每次都線性尋找目前最小／最大值。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 按效率降序。加入目前 speed，若超過 k 人就移除最小 speed。此時 heap 中 speed sum 在目前最低效率下最大。
4. **定義 state 與轉移：** 使用「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」承載上述觀察，再執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log n)$；空間：$O(k)$

> [!tip] 一句話記憶
> 先說清楚「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」代表什麼，再說每一步如何「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻」的 base case。
>
> 2. **維持：** 每次執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」後，狀態仍與已處理資料一致。關鍵論證是：證明被丟棄者不可能優於 heap 內門檻，或 k-way merge 每次 pop 都是所有未輸出元素的全域最小。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：min/max heap 符號、tie breaker、lazy deletion、空 heap、k 大於元素數與 mutable key。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

按效率降序。加入目前 speed，若超過 `k` 人就移除最小 speed。此時 heap 中 speed sum 在目前最低效率下最大。

```python
from heapq import heappush, heappop

def max_performance(speed, efficiency, k):
    engineers = sorted(
        zip(efficiency, speed),
        reverse=True,
    )
    heap = []
    speed_sum = best = 0
    for eff, spd in engineers:
        heappush(heap, spd)
        speed_sum += spd
        if len(heap) > k:
            speed_sum -= heappop(heap)
        best = max(best, speed_sum * eff)
    return best % 1_000_000_007
```

- 時間：$O(n\log n)$
- 空間：$O(k)$

### Follow-up 1：原題直接變形
**問：要求恰好 `k` 人？**

**答：**只有 heap size 達 `k` 時才更新答案；其餘邏輯相同。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Maximum Performance of a Team》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：按效率降序。加入目前 speed，若超過 k 人就移除最小 speed。此時 heap 中 speed sum 在目前最低效率下最大。 失效情境包括：需要任意刪除、rank query 或所有順序統計時，heap 單獨不夠；k 接近 n 時完整排序可能更簡單。
>
> 替代路線是：改用 quickselect、balanced tree、bucket counting、two heaps＋delayed deletion 或 tournament tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：heap entry 保存來源 index、list id、parent 或選擇紀錄；pop 時便可輸出原物件與重建合併路徑。
>
> 套回《Maximum Performance of a Team》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming top-k 需定義時間窗與近似誤差；distributed top-k 可先做 local top-k 再 merge，並處理 stale heap entries。
>
> 此外必須把《Maximum Performance of a Team》目前隱含的前提寫成 contract：選最多 k 位工程師，performance 為速度總和乘以團隊最低效率。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Minimum Cost to Hire K Workers

### 題目

每位 worker 有 quality 與最低 wage。所有被選者依同一 quality 比率支付，且每人薪資不得低於最低要求；求聘 `k` 人最小成本。

> [!tip]- 三層提示
> 1. 若選定最高要求 ratio `wage/quality`，所有人都按此 ratio 支付。
> 2. 依 ratio 升序枚舉最高 ratio。
> 3. 在已符合 ratio 的人中保留 quality 總和最小的 `k` 人。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每位 worker 有 quality 與最低 wage。所有被選者依同一 quality 比率支付，且每人薪資不得低於最低要求；求聘 k 人最小成本。
>
> **核心轉換：** 依 ratio 由小到大。當前 worker 決定目前最高 ratio；max heap 保存選中的 qualities，超過 k 就移除最大 quality。
>
> **主要知識點：** Heap、Top-K 與 K-way Merge。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Minimum Cost to Hire K Workers
      │
      ├─ 暴力路線：反覆排序全部候選，或每次都線性尋找目前最小／最大值
      │
      ▼  找出本題最關鍵的轉換
核心觀察：依 ratio 由小到大。當前 worker 決定目前最高 ratio；max heap 保存選中的 qualities，超過 k 就移除最大 quality。
      │
Pattern toolbox：size-k heap 或由多條已排序序列各提供一個 frontier 的 heap
      │
      ├─ 狀態轉移：加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列
      │
      ├─ 永遠成立：heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每位 worker 有 quality 與最低 wage。所有被選者依同一 quality 比率支付，且每人薪資不得低於最低要求；求聘 k 人最小成本。
2. **寫出暴力：** 反覆排序全部候選，或每次都線性尋找目前最小／最大值。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 依 ratio 由小到大。當前 worker 決定目前最高 ratio；max heap 保存選中的 qualities，超過 k 就移除最大 quality。
4. **定義 state 與轉移：** 使用「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」承載上述觀察，再執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n\log n)$；空間：$O(k)$

> [!tip] 一句話記憶
> 先說清楚「size-k heap 或由多條已排序序列各提供一個 frontier 的 heap」代表什麼，再說每一步如何「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「heap 精確保存目前仍可能影響答案的最佳候選；root 是下一個輸出或保留集合的門檻」的 base case。
>
> 2. **維持：** 每次執行「加入新候選；若超過容量就移除最不值得保留者，或 pop frontier 後推進其來源序列」後，狀態仍與已處理資料一致。關鍵論證是：證明被丟棄者不可能優於 heap 內門檻，或 k-way merge 每次 pop 都是所有未輸出元素的全域最小。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：min/max heap 符號、tie breaker、lazy deletion、空 heap、k 大於元素數與 mutable key。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

依 ratio 由小到大。當前 worker 決定目前最高 ratio；max heap 保存選中的 qualities，超過 `k` 就移除最大 quality。

```python
from heapq import heappush, heappop

def mincost_to_hire_workers(quality, wage, k):
    workers = sorted(
        (w / q, q)
        for q, w in zip(quality, wage)
    )
    max_heap = []
    quality_sum = 0
    answer = float("inf")

    for ratio, q in workers:
        heappush(max_heap, -q)
        quality_sum += q
        if len(max_heap) > k:
            quality_sum += heappop(max_heap)
        if len(max_heap) == k:
            answer = min(answer, ratio * quality_sum)
    return answer
```

- 時間：$O(n\log n)$
- 空間：$O(k)$

### Follow-up 1：原題直接變形
**問：為何不能只挑 wage 最低的 `k` 人？**

**答：**支付比例由團隊最高 `wage/quality` 決定；低 wage 但 quality 更低的人可能有極高 ratio，反而抬高全隊成本。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Minimum Cost to Hire K Workers》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：依 ratio 由小到大。當前 worker 決定目前最高 ratio；max heap 保存選中的 qualities，超過 k 就移除最大 quality。 失效情境包括：需要任意刪除、rank query 或所有順序統計時，heap 單獨不夠；k 接近 n 時完整排序可能更簡單。
>
> 替代路線是：改用 quickselect、balanced tree、bucket counting、two heaps＋delayed deletion 或 tournament tree。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：heap entry 保存來源 index、list id、parent 或選擇紀錄；pop 時便可輸出原物件與重建合併路徑。
>
> 套回《Minimum Cost to Hire K Workers》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> Streaming top-k 需定義時間窗與近似誤差；distributed top-k 可先做 local top-k 再 merge，並處理 stale heap entries。
>
> 此外必須把《Minimum Cost to Hire K Workers》目前隱含的前提寫成 contract：每位 worker 有 quality 與最低 wage。所有被選者依同一 quality 比率支付，且每人薪資不得低於最低要求；求聘 k 人最小成本。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 知道 min heap 如何維持 top K largest。
- [ ] 會用雙 heap 維持 partition。
- [ ] 會處理 heap 的 lazy deletion。
- [ ] 能將排序 sweep 與 heap 候選集合結合。
