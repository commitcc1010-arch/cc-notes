---
title: Data Structure Design
tags:
  - coding-interview/pattern
  - data-structure-design
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 19 — Data Structure Design

[[18 - Bit Math and Geometry|← 上一章]] · [[00 - Book Index|目錄]] · [[20 - Matrix Simulation and Parsing|下一章 →]]

> [!abstract] Mental model
> Design 題先寫 API contract，再列出每個操作的目標複雜度與必須長期成立的 invariants。通常需要把兩種資料結構組合：一個負責定位，另一個負責順序、優先級或聚合。

## 回答順序

1. 釐清 API 與錯誤語意。
2. 寫每個操作的複雜度目標。
3. 定義資料結構與 invariants。
4. 走一個完整操作序列。
5. 再討論 concurrency、persistence、TTL 與 distribution。

---

## 核心題 1：LRU Cache

### 題目

固定容量 cache，`get` 與 `put` 平均 $O(1)$，超過容量刪 least recently used。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 固定容量 cache，get 與 put 平均 $O(1)$，超過容量刪 least recently used。
>
> **核心轉換：** 使用：
>
> **主要知識點：** Data Structure Composition 與跨結構 invariant。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：LRU Cache
      │
      ├─ 暴力路線：讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度
      │
      ▼  找出本題最關鍵的轉換
核心觀察：使用：
      │
Pattern toolbox：一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access
      │
      ├─ 狀態轉移：每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態
      │
      ├─ 永遠成立：每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 固定容量 cache，get 與 put 平均 $O(1)$，超過容量刪 least recently used。
2. **寫出暴力：** 讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 使用：
4. **定義 state 與轉移：** 使用「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」承載上述觀察，再執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」代表什麼，再說每一步如何「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證」的 base case。
>
> 2. **維持：** 每次執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」後，狀態仍與已處理資料一致。關鍵論證是：逐 API 證明前置 invariant 成立時，操作後仍成立；再逐行計算 worst/amortized complexity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：容量 0、更新既有 key、刪最後元素、空 bucket、stale index、例外中斷與 API 未定義行為。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 解法

使用：

- Hash map：`key -> node`。
- Doubly linked list：head 後是 MRU，tail 前是 LRU。

```python
class LRUNode:
    def __init__(self, key=0, value=0):
        self.key = key
        self.value = value
        self.prev = self.next = None


class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.nodes = {}
        self.head = LRUNode()
        self.tail = LRUNode()
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def _add_front(self, node):
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node

    def get(self, key):
        if key not in self.nodes:
            return -1
        node = self.nodes[key]
        self._remove(node)
        self._add_front(node)
        return node.value

    def put(self, key, value):
        if key in self.nodes:
            node = self.nodes[key]
            node.value = value
            self._remove(node)
            self._add_front(node)
            return
        node = LRUNode(key, value)
        self.nodes[key] = node
        self._add_front(node)
        if len(self.nodes) > self.capacity:
            victim = self.tail.prev
            self._remove(victim)
            del self.nodes[victim.key]
```

### Follow-up 1：原題直接變形
**問：多執行緒下如何保證正確？**

**答：**Map 與 list 更新必須是同一 atomic critical section。最簡單是單一 mutex；高吞吐可分片，但會變成 per-shard LRU 而非嚴格全域 LRU。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《LRU Cache》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：使用： 失效情境包括：需求加入全域排序、持久化、range query 或 distributed consistency 後，原 O(1) 組合通常不再足夠。
>
> 替代路線是：改用 balanced tree、log-structured storage、reverse index、event log 或分散式一致性協定，並重新定義 SLA。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 logical id 與反向索引；對每個 API 回傳 mutation/result record，測試時可重播並驗證所有結構一致。
>
> 套回《LRU Cache》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 併發時整個跨結構 mutation 要有線性化點；持久化需 WAL/transaction，TTL 要有 clock policy 與清理機制。
>
> 此外必須把《LRU Cache》目前隱含的前提寫成 contract：固定容量 cache，get 與 put 平均 $O(1)$，超過容量刪 least recently used。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Time Based Key-Value Store

### 題目

`set(key,value,timestamp)` 時間戳嚴格遞增；`get(key,t)` 回傳時間不超過 `t` 的最新值。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** set(key,value,timestamp) 時間戳嚴格遞增；get(key,t) 回傳時間不超過 t 的最新值。
>
> **核心轉換：** 每個 key 對應一條按 timestamp 排序的 history；set 直接 append，get 用 upper_bound 找第一個 >t 的位置再退一格。
>
> **主要知識點：** Data Structure Composition 與跨結構 invariant。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Time Based Key-Value Store
      │
      ├─ 暴力路線：讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度
      │
      ▼  找出本題最關鍵的轉換
核心觀察：每個 key 對應一條按 timestamp 排序的 history；set 直接 append，get 用 upper_bound 找第一個 >t 的位置再退一格。
      │
Pattern toolbox：一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access
      │
      ├─ 狀態轉移：每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態
      │
      ├─ 永遠成立：每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** set(key,value,timestamp) 時間戳嚴格遞增；get(key,t) 回傳時間不超過 t 的最新值。
2. **寫出暴力：** 讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 每個 key 對應一條按 timestamp 排序的 history；set 直接 append，get 用 upper_bound 找第一個 >t 的位置再退一格。
4. **定義 state 與轉移：** 使用「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」承載上述觀察，再執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」代表什麼，再說每一步如何「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證」的 base case。
>
> 2. **維持：** 每次執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」後，狀態仍與已處理資料一致。關鍵論證是：逐 API 證明前置 invariant 成立時，操作後仍成立；再逐行計算 worst/amortized complexity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：容量 0、更新既有 key、刪最後元素、空 bucket、stale index、例外中斷與 API 未定義行為。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
from collections import defaultdict
from bisect import bisect_right

class TimeMap:
    def __init__(self):
        self.history = defaultdict(list)

    def set(self, key, value, timestamp):
        self.history[key].append((timestamp, value))

    def get(self, key, timestamp):
        entries = self.history[key]
        index = bisect_right(entries, (timestamp, chr(0x10FFFF))) - 1
        return "" if index < 0 else entries[index][1]
```

- `set`：$O(1)$ amortized
- `get`：$O(\log n)$

### Follow-up 1：原題直接變形
**問：set 的 timestamps 可能 out of order？**

**答：**普通 list append 不再保持排序。可用 balanced BST／sorted map；若 write 多 read 少，也可先 append，查詢前 lazy sort 並標記 dirty。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Time Based Key-Value Store》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：每個 key 對應一條按 timestamp 排序的 history；set 直接 append，get 用 upper_bound 找第一個 >t 的位置再退一格。 失效情境包括：需求加入全域排序、持久化、range query 或 distributed consistency 後，原 O(1) 組合通常不再足夠。
>
> 替代路線是：改用 balanced tree、log-structured storage、reverse index、event log 或分散式一致性協定，並重新定義 SLA。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 logical id 與反向索引；對每個 API 回傳 mutation/result record，測試時可重播並驗證所有結構一致。
>
> 套回《Time Based Key-Value Store》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 併發時整個跨結構 mutation 要有線性化點；持久化需 WAL/transaction，TTL 要有 clock policy 與清理機制。
>
> 此外必須把《Time Based Key-Value Store》目前隱含的前提寫成 contract：set(key,value,timestamp) 時間戳嚴格遞增；get(key,t) 回傳時間不超過 t 的最新值。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Insert Delete GetRandom O(1)

### 題目

支援插入、刪除與等機率取任一元素，平均皆 $O(1)$。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 支援插入、刪除與等機率取任一元素，平均皆 $O(1)$。
>
> **核心轉換：** array 提供 O(1) random index，map 提供 value→index；刪除時把尾元素 swap 到洞的位置，再 pop 並同步 map。
>
> **主要知識點：** Data Structure Composition 與跨結構 invariant。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Insert Delete GetRandom O(1)
      │
      ├─ 暴力路線：讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度
      │
      ▼  找出本題最關鍵的轉換
核心觀察：array 提供 O(1) random index，map 提供 value→index；刪除時把尾元素 swap 到洞的位置，再 pop 並同步 map。
      │
Pattern toolbox：一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access
      │
      ├─ 狀態轉移：每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態
      │
      ├─ 永遠成立：每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 支援插入、刪除與等機率取任一元素，平均皆 $O(1)$。
2. **寫出暴力：** 讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** array 提供 O(1) random index，map 提供 value→index；刪除時把尾元素 swap 到洞的位置，再 pop 並同步 map。
4. **定義 state 與轉移：** 使用「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」承載上述觀察，再執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」代表什麼，再說每一步如何「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證」的 base case。
>
> 2. **維持：** 每次執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」後，狀態仍與已處理資料一致。關鍵論證是：逐 API 證明前置 invariant 成立時，操作後仍成立；再逐行計算 worst/amortized complexity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：容量 0、更新既有 key、刪最後元素、空 bucket、stale index、例外中斷與 API 未定義行為。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
import random

class RandomizedSet:
    def __init__(self):
        self.values = []
        self.index = {}

    def insert(self, value):
        if value in self.index:
            return False
        self.index[value] = len(self.values)
        self.values.append(value)
        return True

    def remove(self, value):
        if value not in self.index:
            return False
        i = self.index[value]
        last = self.values[-1]
        self.values[i] = last
        self.index[last] = i
        self.values.pop()
        del self.index[value]
        return True

    def getRandom(self):
        return random.choice(self.values)
```

### Follow-up 1：原題直接變形
**問：允許 duplicate？**

**答：**Map 改為 `value -> set(indices)`。刪除時取任一 index，與尾端交換，並同步更新兩個 index sets。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Insert Delete GetRandom O(1)》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：array 提供 O(1) random index，map 提供 value→index；刪除時把尾元素 swap 到洞的位置，再 pop 並同步 map。 失效情境包括：需求加入全域排序、持久化、range query 或 distributed consistency 後，原 O(1) 組合通常不再足夠。
>
> 替代路線是：改用 balanced tree、log-structured storage、reverse index、event log 或分散式一致性協定，並重新定義 SLA。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 logical id 與反向索引；對每個 API 回傳 mutation/result record，測試時可重播並驗證所有結構一致。
>
> 套回《Insert Delete GetRandom O(1)》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 併發時整個跨結構 mutation 要有線性化點；持久化需 WAL/transaction，TTL 要有 clock policy 與清理機制。
>
> 此外必須把《Insert Delete GetRandom O(1)》目前隱含的前提寫成 contract：支援插入、刪除與等機率取任一元素，平均皆 $O(1)$。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：LFU Cache

> [!tip]- 三層提示
> 1. `key -> (value,frequency)`。
> 2. 每個 frequency 需要維持自己的 LRU 順序。
> 3. 維護目前最小 frequency。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 固定容量 cache 依最低使用頻率淘汰，頻率相同時淘汰最久未使用者。
>
> **核心轉換：** 結構是：
>
> **主要知識點：** Data Structure Composition 與跨結構 invariant。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：LFU Cache
      │
      ├─ 暴力路線：讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度
      │
      ▼  找出本題最關鍵的轉換
核心觀察：結構是：
      │
Pattern toolbox：一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access
      │
      ├─ 狀態轉移：每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態
      │
      ├─ 永遠成立：每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 固定容量 cache 依最低使用頻率淘汰，頻率相同時淘汰最久未使用者。
2. **寫出暴力：** 讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 結構是：
4. **定義 state 與轉移：** 使用「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」承載上述觀察，再執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」代表什麼，再說每一步如何「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證」的 base case。
>
> 2. **維持：** 每次執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」後，狀態仍與已處理資料一致。關鍵論證是：逐 API 證明前置 invariant 成立時，操作後仍成立；再逐行計算 worst/amortized complexity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：容量 0、更新既有 key、刪最後元素、空 bucket、stale index、例外中斷與 API 未定義行為。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

結構是：

- `values[key] = (value,freq)`。
- `freq_to_keys[freq]` 是 ordered set，最前端為最舊 key。
- `min_freq` 直接指出淘汰 bucket。

完整可執行實作與 frequency aging follow-up 見 [[08 - Linked List#難題 4：LFU Cache]]。

**核心 invariant：**每個 key 恰存在於一個 frequency bucket；bucket 內依最近使用順序排列；`min_freq` 指向非空最小 bucket。因此 touch 與 eviction 都是平均 $O(1)$。

### Follow-up 1：原題直接變形
**問：如何加入容量依 bytes 而不是 key 數？**

**答：**保存每個 value size 與目前總 bytes；put 後反覆依 LFU/LRU 規則淘汰直到不超容量。單次 put 可能刪除多個項目。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《LFU Cache》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：結構是： 失效情境包括：需求加入全域排序、持久化、range query 或 distributed consistency 後，原 O(1) 組合通常不再足夠。
>
> 替代路線是：改用 balanced tree、log-structured storage、reverse index、event log 或分散式一致性協定，並重新定義 SLA。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 logical id 與反向索引；對每個 API 回傳 mutation/result record，測試時可重播並驗證所有結構一致。
>
> 套回《LFU Cache》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 併發時整個跨結構 mutation 要有線性化點；持久化需 WAL/transaction，TTL 要有 clock policy 與清理機制。
>
> 此外必須把《LFU Cache》目前隱含的前提寫成 contract：固定容量 cache 依最低使用頻率淘汰，頻率相同時淘汰最久未使用者。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：All O`one Data Structure

> [!tip]- 三層提示
> 1. `key -> count` 無法 $O(1)$ 找 min/max。
> 2. 相同 count 的 keys 放入 bucket。
> 3. Buckets 按 count 組成 doubly linked list。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 支援 key 計數增減與 O(1) 取得任一最大／最小計數 key。
>
> **核心轉換：** Key 每次只從 count c 移到相鄰的 c±1 bucket，因此不需要 tree。空 bucket 立即移除，head/tail 直接提供 min/max。
>
> **主要知識點：** Data Structure Composition 與跨結構 invariant。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：All O`one Data Structure
      │
      ├─ 暴力路線：讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Key 每次只從 count c 移到相鄰的 c±1 bucket，因此不需要 tree。空 bucket 立即移除，head/tail 直接提供 min/max。
      │
Pattern toolbox：一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access
      │
      ├─ 狀態轉移：每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態
      │
      ├─ 永遠成立：每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 支援 key 計數增減與 O(1) 取得任一最大／最小計數 key。
2. **寫出暴力：** 讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Key 每次只從 count c 移到相鄰的 c±1 bucket，因此不需要 tree。空 bucket 立即移除，head/tail 直接提供 min/max。
4. **定義 state 與轉移：** 使用「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」承載上述觀察，再執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」代表什麼，再說每一步如何「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證」的 base case。
>
> 2. **維持：** 每次執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」後，狀態仍與已處理資料一致。關鍵論證是：逐 API 證明前置 invariant 成立時，操作後仍成立；再逐行計算 worst/amortized complexity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：容量 0、更新既有 key、刪最後元素、空 bucket、stale index、例外中斷與 API 未定義行為。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Key 每次只從 count `c` 移到相鄰的 `c±1` bucket，因此不需要 tree。空 bucket 立即移除，head/tail 直接提供 min/max。

完整程式碼與 top-k follow-up 見 [[01 - Hashing and Counting#難題 5：All O`one Data Structure]]。

### Follow-up 1：原題直接變形
**問：需要 deterministic 的 min/max key，而不是任意 key？**

**答：**Bucket 內的 set 必須改成 ordered set／heap。取得 key 可更穩定，但刪除與更新通常變成 $O(\log K)$，無法同時保有所有操作嚴格 $O(1)$。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《All O`one Data Structure》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Key 每次只從 count c 移到相鄰的 c±1 bucket，因此不需要 tree。空 bucket 立即移除，head/tail 直接提供 min/max。 失效情境包括：需求加入全域排序、持久化、range query 或 distributed consistency 後，原 O(1) 組合通常不再足夠。
>
> 替代路線是：改用 balanced tree、log-structured storage、reverse index、event log 或分散式一致性協定，並重新定義 SLA。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 logical id 與反向索引；對每個 API 回傳 mutation/result record，測試時可重播並驗證所有結構一致。
>
> 套回《All O`one Data Structure》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 併發時整個跨結構 mutation 要有線性化點；持久化需 WAL/transaction，TTL 要有 clock policy 與清理機制。
>
> 此外必須把《All O`one Data Structure》目前隱含的前提寫成 contract：支援 key 計數增減與 O(1) 取得任一最大／最小計數 key。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Design In-Memory File System

### 題目

支援：

- `ls(path)`
- `mkdir(path)`
- `addContentToFile(path,content)`
- `readContentFromFile(path)`

> [!tip]- 三層提示
> 1. 路徑天然形成 trie/tree。
> 2. Directory node 保存 children；file node 保存 content。
> 3. `ls(file)` 與 `ls(directory)` 的回傳語意不同。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 支援：
>
> **核心轉換：** Node 同時有 children、content 與 isfile。walk 可選擇建立不存在的目錄。
>
> **主要知識點：** Data Structure Composition 與跨結構 invariant。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Design In-Memory File System
      │
      ├─ 暴力路線：讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Node 同時有 children、content 與 isfile。walk 可選擇建立不存在的目錄。
      │
Pattern toolbox：一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access
      │
      ├─ 狀態轉移：每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態
      │
      ├─ 永遠成立：每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 支援：
2. **寫出暴力：** 讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Node 同時有 children、content 與 isfile。walk 可選擇建立不存在的目錄。
4. **定義 state 與轉移：** 使用「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」承載上述觀察，再執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」代表什麼，再說每一步如何「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證」的 base case。
>
> 2. **維持：** 每次執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」後，狀態仍與已處理資料一致。關鍵論證是：逐 API 證明前置 invariant 成立時，操作後仍成立；再逐行計算 worst/amortized complexity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：容量 0、更新既有 key、刪最後元素、空 bucket、stale index、例外中斷與 API 未定義行為。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Node 同時有 `children`、`content` 與 `is_file`。`_walk` 可選擇建立不存在的目錄。

```python
class FileNode:
    def __init__(self):
        self.children = {}
        self.content = []
        self.is_file = False


class FileSystem:
    def __init__(self):
        self.root = FileNode()

    def _parts(self, path):
        return [part for part in path.split("/") if part]

    def _walk(self, path, create=False):
        node = self.root
        for part in self._parts(path):
            if part not in node.children:
                if not create:
                    raise KeyError(path)
                node.children[part] = FileNode()
            node = node.children[part]
        return node

    def ls(self, path):
        node = self._walk(path)
        if node.is_file:
            return [self._parts(path)[-1]]
        return sorted(node.children)

    def mkdir(self, path):
        self._walk(path, create=True)

    def addContentToFile(self, file_path, content):
        node = self._walk(file_path, create=True)
        node.is_file = True
        node.content.append(content)

    def readContentFromFile(self, file_path):
        return "".join(self._walk(file_path).content)
```

### Follow-up 1：原題直接變形
**問：加入 move、delete 與 symbolic link？**

**答：**Move 要防止把目錄移進自己的 descendant；delete 要定義 non-empty directory 語意；symlink resolution 需偵測 cycle 並限制最大跳轉次數。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Design In-Memory File System》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Node 同時有 children、content 與 isfile。walk 可選擇建立不存在的目錄。 失效情境包括：需求加入全域排序、持久化、range query 或 distributed consistency 後，原 O(1) 組合通常不再足夠。
>
> 替代路線是：改用 balanced tree、log-structured storage、reverse index、event log 或分散式一致性協定，並重新定義 SLA。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 logical id 與反向索引；對每個 API 回傳 mutation/result record，測試時可重播並驗證所有結構一致。
>
> 套回《Design In-Memory File System》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 併發時整個跨結構 mutation 要有線性化點；持久化需 WAL/transaction，TTL 要有 clock policy 與清理機制。
>
> 此外必須把《Design In-Memory File System》目前隱含的前提寫成 contract：支援：。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Design Twitter

### 題目

支援發文、follow、unfollow，以及取得自己與 followees 最近十則貼文。

> [!tip]- 三層提示
> 1. 每位使用者的 tweets 自己已按時間排序。
> 2. News feed 是多條排序序列的 top 10 merge。
> 3. Heap 初始只放每條序列最新 tweet，彈出後再放同序列前一則。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 支援發文、follow、unfollow，以及取得自己與 followees 最近十則貼文。
>
> **核心轉換：** 每則 tweet 保存全域遞增 timestamp。取得 feed 時把自己加入 followees，做 bounded k-way merge，最多彈十次。
>
> **主要知識點：** Data Structure Composition 與跨結構 invariant。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Design Twitter
      │
      ├─ 暴力路線：讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度
      │
      ▼  找出本題最關鍵的轉換
核心觀察：每則 tweet 保存全域遞增 timestamp。取得 feed 時把自己加入 followees，做 bounded k-way merge，最多彈十次。
      │
Pattern toolbox：一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access
      │
      ├─ 狀態轉移：每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態
      │
      ├─ 永遠成立：每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 支援發文、follow、unfollow，以及取得自己與 followees 最近十則貼文。
2. **寫出暴力：** 讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 每則 tweet 保存全域遞增 timestamp。取得 feed 時把自己加入 followees，做 bounded k-way merge，最多彈十次。
4. **定義 state 與轉移：** 使用「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」承載上述觀察，再執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：Feed：$O((F+10)\log F)$；發文：$O(1)$

> [!tip] 一句話記憶
> 先說清楚「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」代表什麼，再說每一步如何「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證」的 base case。
>
> 2. **維持：** 每次執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」後，狀態仍與已處理資料一致。關鍵論證是：逐 API 證明前置 invariant 成立時，操作後仍成立；再逐行計算 worst/amortized complexity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：容量 0、更新既有 key、刪最後元素、空 bucket、stale index、例外中斷與 API 未定義行為。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

每則 tweet 保存全域遞增 timestamp。取得 feed 時把自己加入 followees，做 bounded k-way merge，最多彈十次。

```python
from collections import defaultdict
from heapq import heappush, heappop

class Twitter:
    def __init__(self):
        self.time = 0
        self.tweets = defaultdict(list)
        self.follows = defaultdict(set)

    def postTweet(self, user_id, tweet_id):
        self.time += 1
        self.tweets[user_id].append((self.time, tweet_id))

    def follow(self, follower_id, followee_id):
        self.follows[follower_id].add(followee_id)

    def unfollow(self, follower_id, followee_id):
        self.follows[follower_id].discard(followee_id)

    def getNewsFeed(self, user_id):
        users = set(self.follows[user_id])
        users.add(user_id)
        heap = []
        for user in users:
            entries = self.tweets[user]
            if entries:
                index = len(entries) - 1
                time, tweet = entries[index]
                heappush(heap, (-time, tweet, user, index))

        answer = []
        while heap and len(answer) < 10:
            neg_time, tweet, user, index = heappop(heap)
            answer.append(tweet)
            if index > 0:
                time, previous_tweet = self.tweets[user][index - 1]
                heappush(
                    heap,
                    (-time, previous_tweet, user, index - 1),
                )
        return answer
```

- Feed：$O((F+10)\log F)$
- 發文：$O(1)$

### Follow-up 1：原題直接變形
**問：真實系統有數百萬 followees？**

**答：**需討論 fan-out-on-write、fan-out-on-read 或 hybrid。Celebrity 帳號不適合把每篇貼文同步推送給所有 followers；這已進入 system design。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Design Twitter》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：每則 tweet 保存全域遞增 timestamp。取得 feed 時把自己加入 followees，做 bounded k-way merge，最多彈十次。 失效情境包括：需求加入全域排序、持久化、range query 或 distributed consistency 後，原 O(1) 組合通常不再足夠。
>
> 替代路線是：改用 balanced tree、log-structured storage、reverse index、event log 或分散式一致性協定，並重新定義 SLA。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 logical id 與反向索引；對每個 API 回傳 mutation/result record，測試時可重播並驗證所有結構一致。
>
> 套回《Design Twitter》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 併發時整個跨結構 mutation 要有線性化點；持久化需 WAL/transaction，TTL 要有 clock policy 與清理機制。
>
> 此外必須把《Design Twitter》目前隱含的前提寫成 contract：支援發文、follow、unfollow，以及取得自己與 followees 最近十則貼文。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Design Excel Sum Formula

### 題目

設計簡化 spreadsheet：

- `set(cell,value)`
- `get(cell)`
- `sum(cell,references)`，references 可是單格或矩形範圍

被引用儲存格改變後，公式結果應反映新值。

> [!tip]- 三層提示
> 1. Formula 保存 references 與 multiplicity，不要只保存當下結果。
> 2. `get` 可遞迴求值。
> 3. Range 內同一 cell 可能由多個 reference 重複包含，使用 Counter。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 設計簡化 spreadsheet：
>
> **核心轉換：** 簡潔版採 lazy evaluation：普通 cell 保存 value；公式 cell 保存 Counter(referencedcell)。get 遞迴展開公式。題目通常保證沒有 dependency cycle。
>
> **主要知識點：** Data Structure Composition 與跨結構 invariant。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Design Excel Sum Formula
      │
      ├─ 暴力路線：讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度
      │
      ▼  找出本題最關鍵的轉換
核心觀察：簡潔版採 lazy evaluation：普通 cell 保存 value；公式 cell 保存 Counter(referencedcell)。get 遞迴展開公式。題目通常保證沒有 dependency cycle。
      │
Pattern toolbox：一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access
      │
      ├─ 狀態轉移：每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態
      │
      ├─ 永遠成立：每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 設計簡化 spreadsheet：
2. **寫出暴力：** 讓每個 API 都掃描全部資料，或只使用一種結構而無法同時達成所有複雜度。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 簡潔版採 lazy evaluation：普通 cell 保存 value；公式 cell 保存 Counter(referencedcell)。get 遞迴展開公式。題目通常保證沒有 dependency cycle。
4. **定義 state 與轉移：** 使用「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」承載上述觀察，再執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「一個結構負責 O(1) 定位，另一個負責順序、priority、frequency、dependency 或 random access」代表什麼，再說每一步如何「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「每個 logical item 在所有輔助結構中恰有一致表示；每個 pointer/index/bucket 都能互相驗證」的 base case。
>
> 2. **維持：** 每次執行「每個操作按固定次序同步更新所有索引；失敗時不能留下只更新一半的狀態」後，狀態仍與已處理資料一致。關鍵論證是：逐 API 證明前置 invariant 成立時，操作後仍成立；再逐行計算 worst/amortized complexity。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：容量 0、更新既有 key、刪最後元素、空 bucket、stale index、例外中斷與 API 未定義行為。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

簡潔版採 lazy evaluation：普通 cell 保存 value；公式 cell 保存 `Counter(referenced_cell)`。`get` 遞迴展開公式。題目通常保證沒有 dependency cycle。

```python
from collections import Counter

class Excel:
    def __init__(self):
        self.values = {}
        self.formulas = {}

    def _cell(self, row, col):
        return (row, col)

    def _parse(self, text):
        split = 0
        while split < len(text) and text[split].isalpha():
            split += 1
        col_text, row_text = text[:split], text[split:]
        col = 0
        for ch in col_text:
            col = col * 26 + ord(ch) - ord("A") + 1
        return int(row_text), col

    def _expand(self, reference):
        if ":" not in reference:
            return [self._parse(reference)]
        start, end = reference.split(":")
        r1, c1 = self._parse(start)
        r2, c2 = self._parse(end)
        return [
            (r, c)
            for r in range(r1, r2 + 1)
            for c in range(c1, c2 + 1)
        ]

    def set(self, row, column, value):
        cell = self._cell(row, column)
        self.values[cell] = value
        self.formulas.pop(cell, None)

    def get(self, row, column):
        cell = self._cell(row, column)
        if cell not in self.formulas:
            return self.values.get(cell, 0)
        return sum(
            count * self.get(ref_row, ref_col)
            for (ref_row, ref_col), count in self.formulas[cell].items()
        )

    def sum(self, row, column, references):
        cell = self._cell(row, column)
        dependencies = Counter()
        for reference in references:
            dependencies.update(self._expand(reference))
        self.formulas[cell] = dependencies
        self.values.pop(cell, None)
        return self.get(row, column)
```

### Follow-up 1：原題直接變形
**問：大量 get 與更新時如何優化？**

**答：**建立 reverse dependency graph，set 後沿 graph invalidate cache，或直接按 topological order 增量更新 dependents。還必須偵測 formula cycle。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Design Excel Sum Formula》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：簡潔版採 lazy evaluation：普通 cell 保存 value；公式 cell 保存 Counter(referencedcell)。get 遞迴展開公式。題目通常保證沒有 dependency cycle。 失效情境包括：需求加入全域排序、持久化、range query 或 distributed consistency 後，原 O(1) 組合通常不再足夠。
>
> 替代路線是：改用 balanced tree、log-structured storage、reverse index、event log 或分散式一致性協定，並重新定義 SLA。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 logical id 與反向索引；對每個 API 回傳 mutation/result record，測試時可重播並驗證所有結構一致。
>
> 套回《Design Excel Sum Formula》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 併發時整個跨結構 mutation 要有線性化點；持久化需 WAL/transaction，TTL 要有 clock policy 與清理機制。
>
> 此外必須把《Design Excel Sum Formula》目前隱含的前提寫成 contract：設計簡化 spreadsheet：。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 每個 API 的 contract 與複雜度清楚。
- [ ] 能說出跨資料結構 invariant。
- [ ] 會處理更新、刪除與 stale state。
- [ ] 能區分單機演算法題與 distributed system follow-up。
