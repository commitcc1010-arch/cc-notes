---
title: Graph DAG Union-Find and Shortest Path
tags:
  - coding-interview/pattern
  - graph
  - topological-sort
  - union-find
  - shortest-path
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 13 — Graph II：DAG、Union-Find and Shortest Path

[[12 - Graph DFS and BFS|← 上一章]] · [[00 - Book Index|目錄]] · [[14 - Backtracking|下一章 →]]

> [!abstract] Mental model
> 相依關係用 topological sort；動態合併連通元件用 Union-Find；非負加權最短路用 Dijkstra。先辨認 edge 語意，再選演算法。

---

## 核心題 1：Course Schedule

### 題目

課程 prerequisites 形成 directed edges，判斷能否修完所有課。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 課程 prerequisites 形成 directed edges，判斷能否修完所有課。
>
> **核心轉換：** Kahn topological sort 從 indegree 0 課程開始；每移除一門課就降低後繼 indegree，最後處理數等於 V 才代表沒有 cycle。
>
> **主要知識點：** Topological Order、Union-Find 與 Weighted Shortest Path。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Course Schedule
      │
      ├─ 暴力路線：反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Kahn topological sort 從 indegree 0 課程開始；每移除一門課就降低後繼 indegree，最後處理數等於 V 才代表沒有 cycle。
      │
Pattern toolbox：依問題選 indegree queue、DSU parent/size，或 distance＋priority queue
      │
      ├─ 狀態轉移：拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation
      │
      ├─ 永遠成立：已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 課程 prerequisites 形成 directed edges，判斷能否修完所有課。
2. **寫出暴力：** 反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Kahn topological sort 從 indegree 0 課程開始；每移除一門課就降低後繼 indegree，最後處理數等於 V 才代表沒有 cycle。
4. **定義 state 與轉移：** 使用「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」承載上述觀察，再執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(V+E)$；空間：$O(V+E)$

> [!tip] 一句話記憶
> 先說清楚「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」代表什麼，再說每一步如何「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短」的 base case。
>
> 2. **維持：** 每次執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」後，狀態仍與已處理資料一致。關鍵論證是：分別用 partial order、component equivalence relation 或 cut property 證明每次 greedy/relaxation 安全。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複 edge、自環、負權、不可達、directed/undirected 混淆、DSU index 與 stale heap entry。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
from collections import deque

def can_finish(num_courses, prerequisites):
    graph = [[] for _ in range(num_courses)]
    indegree = [0] * num_courses
    for course, prerequisite in prerequisites:
        graph[prerequisite].append(course)
        indegree[course] += 1

    q = deque(i for i, degree in enumerate(indegree) if degree == 0)
    completed = 0
    while q:
        node = q.popleft()
        completed += 1
        for neighbor in graph[node]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                q.append(neighbor)
    return completed == num_courses
```

- 時間：$O(V+E)$
- 空間：$O(V+E)$

### Follow-up 1：原題直接變形
**問：回傳一個合法修課順序？**

**答：**保存 pop 出 queue 的順序；若最後長度不是 `num_courses`，回傳空陣列。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Course Schedule》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Kahn topological sort 從 indegree 0 課程開始；每移除一門課就降低後繼 indegree，最後處理數等於 V 才代表沒有 cycle。 失效情境包括：負權會破壞 Dijkstra；刪 edge 不適合普通 DSU；有 cycle 就不存在完整 topological order。
>
> 替代路線是：改用 Bellman-Ford、DAG relaxation、offline dynamic connectivity、SCC 或更完整的 dynamic graph structure。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：Topological 保存 pop order；DSU 額外保存 union edge；shortest path 保存 parent，最後重建順序或路徑。
>
> 套回《Course Schedule》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 動態圖要考慮版本與增量更新；分散式 dependency graph 需處理 partial failure，路徑服務要監控 stale weights。
>
> 此外必須把《Course Schedule》目前隱含的前提寫成 contract：課程 prerequisites 形成 directed edges，判斷能否修完所有課。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Redundant Connection

### 題目

一棵無向 tree 多加一條 edge，找出造成 cycle 的 edge。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 一棵無向 tree 多加一條 edge，找出造成 cycle 的 edge。
>
> **核心轉換：** 依輸入順序 union endpoints；若兩端在加入前已有同一 root，這條 edge 連接同一 component，正是造成 cycle 的 redundant edge。
>
> **主要知識點：** Topological Order、Union-Find 與 Weighted Shortest Path。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Redundant Connection
      │
      ├─ 暴力路線：反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：依輸入順序 union endpoints；若兩端在加入前已有同一 root，這條 edge 連接同一 component，正是造成 cycle 的 redundant edge。
      │
Pattern toolbox：依問題選 indegree queue、DSU parent/size，或 distance＋priority queue
      │
      ├─ 狀態轉移：拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation
      │
      ├─ 永遠成立：已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 一棵無向 tree 多加一條 edge，找出造成 cycle 的 edge。
2. **寫出暴力：** 反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 依輸入順序 union endpoints；若兩端在加入前已有同一 root，這條 edge 連接同一 component，正是造成 cycle 的 redundant edge。
4. **定義 state 與轉移：** 使用「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」承載上述觀察，再執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」代表什麼，再說每一步如何「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短」的 base case。
>
> 2. **維持：** 每次執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」後，狀態仍與已處理資料一致。關鍵論證是：分別用 partial order、component equivalence relation 或 cut property 證明每次 greedy/relaxation 安全。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複 edge、自環、負權、不可達、directed/undirected 混淆、DSU index 與 stale heap entry。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def find_redundant_connection(edges):
    parent = list(range(len(edges) + 1))
    size = [1] * len(parent)

    def find(x):
        while x != parent[x]:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return False
        if size[ra] < size[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        size[ra] += size[rb]
        return True

    for a, b in edges:
        if not union(a, b):
            return [a, b]
```

### Follow-up 1：原題直接變形
**問：為什麼 Union-Find 適合這題，不適合直接回答最短路？**

**答：**它只維護「是否屬於同一 connected component」，不保存路徑結構與距離。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Redundant Connection》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：依輸入順序 union endpoints；若兩端在加入前已有同一 root，這條 edge 連接同一 component，正是造成 cycle 的 redundant edge。 失效情境包括：負權會破壞 Dijkstra；刪 edge 不適合普通 DSU；有 cycle 就不存在完整 topological order。
>
> 替代路線是：改用 Bellman-Ford、DAG relaxation、offline dynamic connectivity、SCC 或更完整的 dynamic graph structure。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：Topological 保存 pop order；DSU 額外保存 union edge；shortest path 保存 parent，最後重建順序或路徑。
>
> 套回《Redundant Connection》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 動態圖要考慮版本與增量更新；分散式 dependency graph 需處理 partial failure，路徑服務要監控 stale weights。
>
> 此外必須把《Redundant Connection》目前隱含的前提寫成 contract：一棵無向 tree 多加一條 edge，找出造成 cycle 的 edge。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Network Delay Time

### 題目

Directed weighted graph 中，訊號由 source 出發，求所有節點收到訊號所需時間；不可達回傳 `-1`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** Directed weighted graph 中，訊號由 source 出發，求所有節點收到訊號所需時間；不可達回傳 -1。
>
> **核心轉換：** Dijkstra 每次 settle 目前距離最小的節點並 relax outgoing edges；所有節點最短距離的最大值就是廣播完成時間。
>
> **主要知識點：** Topological Order、Union-Find 與 Weighted Shortest Path。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Network Delay Time
      │
      ├─ 暴力路線：反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Dijkstra 每次 settle 目前距離最小的節點並 relax outgoing edges；所有節點最短距離的最大值就是廣播完成時間。
      │
Pattern toolbox：依問題選 indegree queue、DSU parent/size，或 distance＋priority queue
      │
      ├─ 狀態轉移：拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation
      │
      ├─ 永遠成立：已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** Directed weighted graph 中，訊號由 source 出發，求所有節點收到訊號所需時間；不可達回傳 -1。
2. **寫出暴力：** 反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Dijkstra 每次 settle 目前距離最小的節點並 relax outgoing edges；所有節點最短距離的最大值就是廣播完成時間。
4. **定義 state 與轉移：** 使用「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」承載上述觀察，再執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」代表什麼，再說每一步如何「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短」的 base case。
>
> 2. **維持：** 每次執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」後，狀態仍與已處理資料一致。關鍵論證是：分別用 partial order、component equivalence relation 或 cut property 證明每次 greedy/relaxation 安全。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複 edge、自環、負權、不可達、directed/undirected 混淆、DSU index 與 stale heap entry。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
from heapq import heappush, heappop

def network_delay_time(times, n, source):
    graph = [[] for _ in range(n + 1)]
    for u, v, weight in times:
        graph[u].append((v, weight))

    distance = [float("inf")] * (n + 1)
    distance[source] = 0
    heap = [(0, source)]
    while heap:
        dist, node = heappop(heap)
        if dist != distance[node]:
            continue
        for neighbor, weight in graph[node]:
            candidate = dist + weight
            if candidate < distance[neighbor]:
                distance[neighbor] = candidate
                heappush(heap, (candidate, neighbor))

    answer = max(distance[1:])
    return -1 if answer == float("inf") else answer
```

### Follow-up 1：原題直接變形
**問：有負權 edge 但沒有 negative cycle？**

**答：**Dijkstra 不再正確。改用 Bellman–Ford，或 DAG 上依 topological order relaxation。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Network Delay Time》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Dijkstra 每次 settle 目前距離最小的節點並 relax outgoing edges；所有節點最短距離的最大值就是廣播完成時間。 失效情境包括：負權會破壞 Dijkstra；刪 edge 不適合普通 DSU；有 cycle 就不存在完整 topological order。
>
> 替代路線是：改用 Bellman-Ford、DAG relaxation、offline dynamic connectivity、SCC 或更完整的 dynamic graph structure。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：Topological 保存 pop order；DSU 額外保存 union edge；shortest path 保存 parent，最後重建順序或路徑。
>
> 套回《Network Delay Time》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 動態圖要考慮版本與增量更新；分散式 dependency graph 需處理 partial failure，路徑服務要監控 stale weights。
>
> 此外必須把《Network Delay Time》目前隱含的前提寫成 contract：Directed weighted graph 中，訊號由 source 出發，求所有節點收到訊號所需時間；不可達回傳 -1。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Alien Dictionary

### 題目

給一組依外星字母順序排序的 words，推導任一合法字母順序；無解回傳空字串。

> [!tip]- 三層提示
> 1. 相鄰 words 的第一個不同字元決定一條 precedence edge。
> 2. 較長字串排在其完整 prefix 前面是非法。
> 3. 建圖後做 topological sort。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 給一組依外星字母順序排序的 words，推導任一合法字母順序；無解回傳空字串。
>
> **核心轉換：** 先為所有出現字元建立節點。比較每對相鄰 words，第一個不同位置 a != b 產生 a -> b。只加入新 edge 時增加 indegree，避免重複計數。
>
> **主要知識點：** Topological Order、Union-Find 與 Weighted Shortest Path。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Alien Dictionary
      │
      ├─ 暴力路線：反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：先為所有出現字元建立節點。比較每對相鄰 words，第一個不同位置 a != b 產生 a -> b。只加入新 edge 時增加 indegree，避免重複計數。
      │
Pattern toolbox：依問題選 indegree queue、DSU parent/size，或 distance＋priority queue
      │
      ├─ 狀態轉移：拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation
      │
      ├─ 永遠成立：已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 給一組依外星字母順序排序的 words，推導任一合法字母順序；無解回傳空字串。
2. **寫出暴力：** 反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 先為所有出現字元建立節點。比較每對相鄰 words，第一個不同位置 a != b 產生 a -> b。只加入新 edge 時增加 indegree，避免重複計數。
4. **定義 state 與轉移：** 使用「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」承載上述觀察，再執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(C+E)$，C 為總字元數；空間：$O(U+E)$，U 為不同字元數

> [!tip] 一句話記憶
> 先說清楚「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」代表什麼，再說每一步如何「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短」的 base case。
>
> 2. **維持：** 每次執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」後，狀態仍與已處理資料一致。關鍵論證是：分別用 partial order、component equivalence relation 或 cut property 證明每次 greedy/relaxation 安全。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複 edge、自環、負權、不可達、directed/undirected 混淆、DSU index 與 stale heap entry。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

先為所有出現字元建立節點。比較每對相鄰 words，第一個不同位置 `a != b` 產生 `a -> b`。只加入新 edge 時增加 indegree，避免重複計數。

```python
from collections import deque

def alien_order(words):
    graph = {ch: set() for word in words for ch in word}
    indegree = {ch: 0 for ch in graph}

    for first, second in zip(words, words[1:]):
        if len(first) > len(second) and first.startswith(second):
            return ""
        for a, b in zip(first, second):
            if a != b:
                if b not in graph[a]:
                    graph[a].add(b)
                    indegree[b] += 1
                break

    q = deque(ch for ch, degree in indegree.items() if degree == 0)
    order = []
    while q:
        ch = q.popleft()
        order.append(ch)
        for neighbor in graph[ch]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                q.append(neighbor)
    return "".join(order) if len(order) == len(graph) else ""
```

- 時間：$O(C+E)$，`C` 為總字元數
- 空間：$O(U+E)$，`U` 為不同字元數

### Follow-up 1：原題直接變形
**問：要求 lexicographically smallest 合法順序？**

**答：**把 zero-indegree queue 改成 min heap。這只定義多個合法拓撲序中的選擇方式。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Alien Dictionary》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：先為所有出現字元建立節點。比較每對相鄰 words，第一個不同位置 a != b 產生 a -> b。只加入新 edge 時增加 indegree，避免重複計數。 失效情境包括：負權會破壞 Dijkstra；刪 edge 不適合普通 DSU；有 cycle 就不存在完整 topological order。
>
> 替代路線是：改用 Bellman-Ford、DAG relaxation、offline dynamic connectivity、SCC 或更完整的 dynamic graph structure。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：Topological 保存 pop order；DSU 額外保存 union edge；shortest path 保存 parent，最後重建順序或路徑。
>
> 套回《Alien Dictionary》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 動態圖要考慮版本與增量更新；分散式 dependency graph 需處理 partial failure，路徑服務要監控 stale weights。
>
> 此外必須把《Alien Dictionary》目前隱含的前提寫成 contract：給一組依外星字母順序排序的 words，推導任一合法字母順序；無解回傳空字串。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Critical Connections in a Network

### 題目

找無向連通圖中所有 bridges：移除後會使圖不連通的 edges。

> [!tip]- 三層提示
> 1. DFS tree 中，child 是否能透過 back edge 回到 ancestor？
> 2. `disc[u]` 是發現時間，`low[u]` 是子樹可到達的最早時間。
> 3. 若 `low[v] > disc[u]`，edge `(u,v)` 是 bridge。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 找無向連通圖中所有 bridges：移除後會使圖不連通的 edges。
>
> **核心轉換：** DFS 時忽略回到 parent 的 edge。回程更新 low[node]；若 child 的整個子樹都無法回到 node 或更早 ancestor，這條 tree edge 是唯一連接。
>
> **主要知識點：** Topological Order、Union-Find 與 Weighted Shortest Path。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Critical Connections in a Network
      │
      ├─ 暴力路線：反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：DFS 時忽略回到 parent 的 edge。回程更新 low[node]；若 child 的整個子樹都無法回到 node 或更早 ancestor，這條 tree edge 是唯一連接。
      │
Pattern toolbox：依問題選 indegree queue、DSU parent/size，或 distance＋priority queue
      │
      ├─ 狀態轉移：拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation
      │
      ├─ 永遠成立：已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 找無向連通圖中所有 bridges：移除後會使圖不連通的 edges。
2. **寫出暴力：** 反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** DFS 時忽略回到 parent 的 edge。回程更新 low[node]；若 child 的整個子樹都無法回到 node 或更早 ancestor，這條 tree edge 是唯一連接。
4. **定義 state 與轉移：** 使用「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」承載上述觀察，再執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(V+E)$；空間：$O(V+E)$

> [!tip] 一句話記憶
> 先說清楚「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」代表什麼，再說每一步如何「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短」的 base case。
>
> 2. **維持：** 每次執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」後，狀態仍與已處理資料一致。關鍵論證是：分別用 partial order、component equivalence relation 或 cut property 證明每次 greedy/relaxation 安全。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複 edge、自環、負權、不可達、directed/undirected 混淆、DSU index 與 stale heap entry。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

DFS 時忽略回到 parent 的 edge。回程更新 `low[node]`；若 child 的整個子樹都無法回到 node 或更早 ancestor，這條 tree edge 是唯一連接。

```python
def critical_connections(n, connections):
    graph = [[] for _ in range(n)]
    for u, v in connections:
        graph[u].append(v)
        graph[v].append(u)

    discovery = [-1] * n
    low = [0] * n
    timer = 0
    bridges = []

    def dfs(node, parent):
        nonlocal timer
        discovery[node] = low[node] = timer
        timer += 1
        for neighbor in graph[node]:
            if neighbor == parent:
                continue
            if discovery[neighbor] == -1:
                dfs(neighbor, node)
                low[node] = min(low[node], low[neighbor])
                if low[neighbor] > discovery[node]:
                    bridges.append([node, neighbor])
            else:
                low[node] = min(low[node], discovery[neighbor])

    for node in range(n):
        if discovery[node] == -1:
            dfs(node, -1)
    return bridges
```

- 時間：$O(V+E)$
- 空間：$O(V+E)$

### Follow-up 1：原題直接變形
**問：找 articulation points？**

**答：**非 root 節點 `u` 若有 child `v` 滿足 `low[v] >= disc[u]`，`u` 是 articulation point；DFS root 則需至少兩個 DFS children。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Critical Connections in a Network》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：DFS 時忽略回到 parent 的 edge。回程更新 low[node]；若 child 的整個子樹都無法回到 node 或更早 ancestor，這條 tree edge 是唯一連接。 失效情境包括：負權會破壞 Dijkstra；刪 edge 不適合普通 DSU；有 cycle 就不存在完整 topological order。
>
> 替代路線是：改用 Bellman-Ford、DAG relaxation、offline dynamic connectivity、SCC 或更完整的 dynamic graph structure。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：Topological 保存 pop order；DSU 額外保存 union edge；shortest path 保存 parent，最後重建順序或路徑。
>
> 套回《Critical Connections in a Network》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 動態圖要考慮版本與增量更新；分散式 dependency graph 需處理 partial failure，路徑服務要監控 stale weights。
>
> 此外必須把《Critical Connections in a Network》目前隱含的前提寫成 contract：找無向連通圖中所有 bridges：移除後會使圖不連通的 edges。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Reconstruct Itinerary

### 題目

每張 ticket `[from,to]` 必須恰使用一次，從指定機場出發；多個答案取 lexicographically smallest itinerary。

> [!tip]- 三層提示
> 1. 這是使用每條 edge 一次的 Eulerian path。
> 2. 每個出發點的 destinations 用 min heap。
> 3. Hierholzer：走到無 edge 才把 node 加進答案，最後反轉。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每張 ticket [from,to] 必須恰使用一次，從指定機場出發；多個答案取 lexicographically smallest itinerary。
>
> **核心轉換：** 不能一般 greedy 地把最小 destination 直接永久放入答案，因為可能走到 dead end。Hierholzer 在回程時建立答案，確保所有 edge 都被接入同一路徑。
>
> **主要知識點：** Topological Order、Union-Find 與 Weighted Shortest Path。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Reconstruct Itinerary
      │
      ├─ 暴力路線：反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：不能一般 greedy 地把最小 destination 直接永久放入答案，因為可能走到 dead end。Hierholzer 在回程時建立答案，確保所有 edge 都被接入同一路徑。
      │
Pattern toolbox：依問題選 indegree queue、DSU parent/size，或 distance＋priority queue
      │
      ├─ 狀態轉移：拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation
      │
      ├─ 永遠成立：已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每張 ticket [from,to] 必須恰使用一次，從指定機場出發；多個答案取 lexicographically smallest itinerary。
2. **寫出暴力：** 反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 不能一般 greedy 地把最小 destination 直接永久放入答案，因為可能走到 dead end。Hierholzer 在回程時建立答案，確保所有 edge 都被接入同一路徑。
4. **定義 state 與轉移：** 使用「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」承載上述觀察，再執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(E\log E)$；空間：$O(E)$

> [!tip] 一句話記憶
> 先說清楚「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」代表什麼，再說每一步如何「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短」的 base case。
>
> 2. **維持：** 每次執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」後，狀態仍與已處理資料一致。關鍵論證是：分別用 partial order、component equivalence relation 或 cut property 證明每次 greedy/relaxation 安全。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複 edge、自環、負權、不可達、directed/undirected 混淆、DSU index 與 stale heap entry。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

不能一般 greedy 地把最小 destination 直接永久放入答案，因為可能走到 dead end。Hierholzer 在回程時建立答案，確保所有 edge 都被接入同一路徑。

```python
from collections import defaultdict
from heapq import heapify, heappop

def find_itinerary(tickets, start="JFK"):
    graph = defaultdict(list)
    for source, destination in tickets:
        graph[source].append(destination)
    for source in graph:
        heapify(graph[source])

    route = []

    def visit(airport):
        heap = graph[airport]
        while heap:
            visit(heappop(heap))
        route.append(airport)

    visit(start)
    return route[::-1]
```

- 時間：$O(E\log E)$
- 空間：$O(E)$

### Follow-up 1：原題直接變形
**問：如何驗證 itinerary 是否使用所有 tickets？**

**答：**答案節點數必須為 `len(tickets)+1`。若題目不保證存在 Eulerian path，還應檢查 degree 條件與連通性。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Reconstruct Itinerary》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：不能一般 greedy 地把最小 destination 直接永久放入答案，因為可能走到 dead end。Hierholzer 在回程時建立答案，確保所有 edge 都被接入同一路徑。 失效情境包括：負權會破壞 Dijkstra；刪 edge 不適合普通 DSU；有 cycle 就不存在完整 topological order。
>
> 替代路線是：改用 Bellman-Ford、DAG relaxation、offline dynamic connectivity、SCC 或更完整的 dynamic graph structure。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：Topological 保存 pop order；DSU 額外保存 union edge；shortest path 保存 parent，最後重建順序或路徑。
>
> 套回《Reconstruct Itinerary》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 動態圖要考慮版本與增量更新；分散式 dependency graph 需處理 partial failure，路徑服務要監控 stale weights。
>
> 此外必須把《Reconstruct Itinerary》目前隱含的前提寫成 contract：每張 ticket [from,to] 必須恰使用一次，從指定機場出發；多個答案取 lexicographically smallest itinerary。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Cheapest Flights Within K Stops

### 題目

Directed weighted flights 中，最多經過 `k` 個中繼站，求 source 到 destination 最低價格。

> [!tip]- 三層提示
> 1. 最多 `k` 個 stops 等於最多 `k+1` 條 edges。
> 2. 一般 Dijkstra 的「只保留每 node 最短距離」可能丟掉 edge 較少但稍貴的狀態。
> 3. 做 `k+1` 輪 Bellman–Ford，且每輪從上一輪 copy relaxation。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** Directed weighted flights 中，最多經過 k 個中繼站，求 source 到 destination 最低價格。
>
> **核心轉換：** distance[v] 在第 i 輪代表最多使用 i 條 edges 的最短價格。必須從舊 distance 轉移到 copy，避免同一輪連續使用多條 edge。
>
> **主要知識點：** Topological Order、Union-Find 與 Weighted Shortest Path。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Cheapest Flights Within K Stops
      │
      ├─ 暴力路線：反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：distance[v] 在第 i 輪代表最多使用 i 條 edges 的最短價格。必須從舊 distance 轉移到 copy，避免同一輪連續使用多條 edge。
      │
Pattern toolbox：依問題選 indegree queue、DSU parent/size，或 distance＋priority queue
      │
      ├─ 狀態轉移：拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation
      │
      ├─ 永遠成立：已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** Directed weighted flights 中，最多經過 k 個中繼站，求 source 到 destination 最低價格。
2. **寫出暴力：** 反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** distance[v] 在第 i 輪代表最多使用 i 條 edges 的最短價格。必須從舊 distance 轉移到 copy，避免同一輪連續使用多條 edge。
4. **定義 state 與轉移：** 使用「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」承載上述觀察，再執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(kE)$；空間：$O(V)$

> [!tip] 一句話記憶
> 先說清楚「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」代表什麼，再說每一步如何「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短」的 base case。
>
> 2. **維持：** 每次執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」後，狀態仍與已處理資料一致。關鍵論證是：分別用 partial order、component equivalence relation 或 cut property 證明每次 greedy/relaxation 安全。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複 edge、自環、負權、不可達、directed/undirected 混淆、DSU index 與 stale heap entry。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

`distance[v]` 在第 `i` 輪代表最多使用 `i` 條 edges 的最短價格。必須從舊 distance 轉移到 copy，避免同一輪連續使用多條 edge。

```python
def find_cheapest_price(n, flights, source, destination, k):
    distance = [float("inf")] * n
    distance[source] = 0

    for _ in range(k + 1):
        next_distance = distance[:]
        for u, v, price in flights:
            if distance[u] != float("inf"):
                next_distance[v] = min(
                    next_distance[v],
                    distance[u] + price,
                )
        distance = next_distance

    return -1 if distance[destination] == float("inf") else distance[destination]
```

- 時間：$O(kE)$
- 空間：$O(V)$

### Follow-up 1：原題直接變形
**問：用 Dijkstra 要如何修正 state？**

**答：**heap state 必須包含 `(cost,node,edges_used)`，並為每個 node 的不同 edge count 保存最佳成本，不能只存一個 distance。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Cheapest Flights Within K Stops》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：distance[v] 在第 i 輪代表最多使用 i 條 edges 的最短價格。必須從舊 distance 轉移到 copy，避免同一輪連續使用多條 edge。 失效情境包括：負權會破壞 Dijkstra；刪 edge 不適合普通 DSU；有 cycle 就不存在完整 topological order。
>
> 替代路線是：改用 Bellman-Ford、DAG relaxation、offline dynamic connectivity、SCC 或更完整的 dynamic graph structure。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：Topological 保存 pop order；DSU 額外保存 union edge；shortest path 保存 parent，最後重建順序或路徑。
>
> 套回《Cheapest Flights Within K Stops》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 動態圖要考慮版本與增量更新；分散式 dependency graph 需處理 partial failure，路徑服務要監控 stale weights。
>
> 此外必須把《Cheapest Flights Within K Stops》目前隱含的前提寫成 contract：Directed weighted flights 中，最多經過 k 個中繼站，求 source 到 destination 最低價格。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Remove Max Number of Edges to Keep Graph Traversable

### 題目

Edges 有三類：只能 Alice 用、只能 Bob 用、兩人共用。刪除最多 edges，同時讓 Alice 與 Bob 各自仍能走遍所有節點。

> [!tip]- 三層提示
> 1. 共用 edge 價值最高，先處理。
> 2. Alice、Bob 各有自己的 Union-Find。
> 3. 無法成功 union 的 edge 就是 redundant，可刪除。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** Edges 有三類：只能 Alice 用、只能 Bob 用、兩人共用。刪除最多 edges，同時讓 Alice 與 Bob 各自仍能走遍所有節點。
>
> **核心轉換：** 先把 type 3 edge 同時 union 到兩個 DSU；再各自處理 type 1、2。最後兩個 DSU 都必須只剩一個 component。
>
> **主要知識點：** Topological Order、Union-Find 與 Weighted Shortest Path。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Remove Max Number of Edges to Keep Graph Traversable
      │
      ├─ 暴力路線：反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑
      │
      ▼  找出本題最關鍵的轉換
核心觀察：先把 type 3 edge 同時 union 到兩個 DSU；再各自處理 type 1、2。最後兩個 DSU 都必須只剩一個 component。
      │
Pattern toolbox：依問題選 indegree queue、DSU parent/size，或 distance＋priority queue
      │
      ├─ 狀態轉移：拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation
      │
      ├─ 永遠成立：已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** Edges 有三類：只能 Alice 用、只能 Bob 用、兩人共用。刪除最多 edges，同時讓 Alice 與 Bob 各自仍能走遍所有節點。
2. **寫出暴力：** 反覆掃描所有 dependencies、每次連通查詢都 DFS，或枚舉所有加權路徑。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 先把 type 3 edge 同時 union 到兩個 DSU；再各自處理 type 1、2。最後兩個 DSU 都必須只剩一個 component。
4. **定義 state 與轉移：** 使用「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」承載上述觀察，再執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(E\alpha(V))$；空間：$O(V)$

> [!tip] 一句話記憶
> 先說清楚「依問題選 indegree queue、DSU parent/size，或 distance＋priority queue」代表什麼，再說每一步如何「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「已輸出的拓撲點依賴已滿足；DSU root 代表 component；Dijkstra settled distance 已是最短」的 base case。
>
> 2. **維持：** 每次執行「拓撲排序移除零入度點；DSU 合併 roots；最短路只從目前最小 tentative distance 做 relaxation」後，狀態仍與已處理資料一致。關鍵論證是：分別用 partial order、component equivalence relation 或 cut property 證明每次 greedy/relaxation 安全。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：重複 edge、自環、負權、不可達、directed/undirected 混淆、DSU index 與 stale heap entry。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

先把 type 3 edge 同時 union 到兩個 DSU；再各自處理 type 1、2。最後兩個 DSU 都必須只剩一個 component。

```python
class DSU:
    def __init__(self, n):
        self.parent = list(range(n + 1))
        self.size = [1] * (n + 1)
        self.components = n

    def find(self, x):
        while x != self.parent[x]:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        self.components -= 1
        return True


def max_num_edges_to_remove(n, edges):
    alice, bob = DSU(n), DSU(n)
    used = 0

    for edge_type, u, v in edges:
        if edge_type == 3:
            merged_a = alice.union(u, v)
            merged_b = bob.union(u, v)
            if merged_a or merged_b:
                used += 1

    for edge_type, u, v in edges:
        if edge_type == 1 and alice.union(u, v):
            used += 1
        elif edge_type == 2 and bob.union(u, v):
            used += 1

    if alice.components != 1 or bob.components != 1:
        return -1
    return len(edges) - used
```

- 時間：$O(E\alpha(V))$
- 空間：$O(V)$

### Follow-up 1：原題直接變形
**問：若有三位使用者與各種共享 subset edge？**

**答：**優先處理可服務最多使用者的 edge 是直覺，但不一定保證全域最佳；一般化版本可能需要 matroid／combinatorial optimization，不能未證明就延伸 greedy。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Remove Max Number of Edges to Keep Graph Traversable》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：先把 type 3 edge 同時 union 到兩個 DSU；再各自處理 type 1、2。最後兩個 DSU 都必須只剩一個 component。 失效情境包括：負權會破壞 Dijkstra；刪 edge 不適合普通 DSU；有 cycle 就不存在完整 topological order。
>
> 替代路線是：改用 Bellman-Ford、DAG relaxation、offline dynamic connectivity、SCC 或更完整的 dynamic graph structure。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：Topological 保存 pop order；DSU 額外保存 union edge；shortest path 保存 parent，最後重建順序或路徑。
>
> 套回《Remove Max Number of Edges to Keep Graph Traversable》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 動態圖要考慮版本與增量更新；分散式 dependency graph 需處理 partial failure，路徑服務要監控 stale weights。
>
> 此外必須把《Remove Max Number of Edges to Keep Graph Traversable》目前隱含的前提寫成 contract：Edges 有三類：只能 Alice 用、只能 Bob 用、兩人共用。刪除最多 edges，同時讓 Alice 與 Bob 各自仍能走遍所有節點。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] Directed dependency 會想到 indegree。
- [ ] 動態連通會想到 Union-Find。
- [ ] 非負權最短路會想到 Dijkstra。
- [ ] 知道 bridge、Eulerian path 與受限 edge count 的特殊狀態。
