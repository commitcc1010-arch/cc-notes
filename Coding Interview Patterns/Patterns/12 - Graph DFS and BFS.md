---
title: Graph DFS and BFS
tags:
  - coding-interview/pattern
  - graph
  - dfs
  - bfs
status: complete
updated: 2026-09-30
core_questions: 3
hard_questions: 5
followups_per_question: 4
visual_explanations: true
deep_solution_layer: true
---

# 12 — Graph I：DFS and BFS

[[11 - Heap Top-K and K-way Merge|← 上一章]] · [[00 - Book Index|目錄]] · [[13 - Graph DAG Union-Find and Shortest Path|下一章 →]]

> [!abstract] Mental model
> Graph 題先定義 node、edge 與 state。DFS 適合完整探索與 component；BFS 適合未加權最短步數。當「同一位置但剩餘資源不同」時，它們是不同 state。

---

## 核心題 1：Number of Islands


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 計算 0/1 grid 中四方向相連的陸地 connected components 數。
>
> **核心轉換：** 每遇到未訪問陸地就發現一個新 component，答案加一，再用 DFS/BFS 標記整座 island，避免之後重複計數。
>
> **主要知識點：** Graph DFS/BFS、State Graph 與最短步數。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Number of Islands
      │
      ├─ 暴力路線：從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態
      │
      ▼  找出本題最關鍵的轉換
核心觀察：每遇到未訪問陸地就發現一個新 component，答案加一，再用 DFS/BFS 標記整座 island，避免之後重複計數。
      │
Pattern toolbox：node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue
      │
      ├─ 狀態轉移：從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier
      │
      ├─ 永遠成立：visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 計算 0/1 grid 中四方向相連的陸地 connected components 數。
2. **寫出暴力：** 從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 每遇到未訪問陸地就發現一個新 component，答案加一，再用 DFS/BFS 標記整座 island，避免之後重複計數。
4. **定義 state 與轉移：** 使用「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」承載上述觀察，再執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」代表什麼，再說每一步如何「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開」的 base case。
>
> 2. **維持：** 每次執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」後，狀態仍與已處理資料一致。關鍵論證是：可達性用 path length induction；無權最短路證明 BFS 第一次到達時已走最少 edges。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：圖不連通、cycle、node identity、grid 邊界、狀態除位置外還有資源，以及何時可標 visited。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def num_islands(grid):
    rows, cols = len(grid), len(grid[0])

    def dfs(r, c):
        if not (0 <= r < rows and 0 <= c < cols):
            return
        if grid[r][c] != "1":
            return
        grid[r][c] = "0"
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            dfs(r + dr, c + dc)

    count = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "1":
                count += 1
                dfs(r, c)
    return count
```

### Follow-up 1：原題直接變形
**問：陸地逐筆加入，每次回傳 island 數？**

**答：**使用 Union-Find。新增陸地先讓 count 加一，再與四周已存在陸地 union；每次成功合併 count 減一。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Number of Islands》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：每遇到未訪問陸地就發現一個新 component，答案加一，再用 DFS/BFS 標記整座 island，避免之後重複計數。 失效情境包括：若 edge weight 不相等，普通 BFS 不保最短；若 visited key 遺漏資源維度，會錯誤合併不同狀態。
>
> 替代路線是：改用 0-1 BFS、Dijkstra、A*、bidirectional BFS 或壓縮 state；多 query 可預處理 connected components。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent[state] 與造成轉移的 action；抵達 target 後逆向重建 path，全部最短路則保存多個 parents。
>
> 套回《Number of Islands》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超大圖採 frontier batching、外部 visited 或雙向搜尋；分散式 traversal 要處理重複訊息與 eventual consistency。
>
> 此外必須把《Number of Islands》目前隱含的前提寫成 contract：計算 0/1 grid 中四方向相連的陸地 connected components 數。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 2：Clone Graph


<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 深拷貝一個可能含 cycle 的 graph。
>
> **核心轉換：** map old_node→new_node 同時負責 identity preservation 與 visited；第一次看到節點就先建立 clone，再遞迴／迭代連接 neighbors。
>
> **主要知識點：** Graph DFS/BFS、State Graph 與最短步數。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Clone Graph
      │
      ├─ 暴力路線：從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態
      │
      ▼  找出本題最關鍵的轉換
核心觀察：map old_node→new_node 同時負責 identity preservation 與 visited；第一次看到節點就先建立 clone，再遞迴／迭代連接 neighbors。
      │
Pattern toolbox：node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue
      │
      ├─ 狀態轉移：從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier
      │
      ├─ 永遠成立：visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 深拷貝一個可能含 cycle 的 graph。
2. **寫出暴力：** 從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** map old_node→new_node 同時負責 identity preservation 與 visited；第一次看到節點就先建立 clone，再遞迴／迭代連接 neighbors。
4. **定義 state 與轉移：** 使用「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」承載上述觀察，再執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」代表什麼，再說每一步如何「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開」的 base case。
>
> 2. **維持：** 每次執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」後，狀態仍與已處理資料一致。關鍵論證是：可達性用 path length induction；無權最短路證明 BFS 第一次到達時已走最少 edges。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：圖不連通、cycle、node identity、grid 邊界、狀態除位置外還有資源，以及何時可標 visited。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
def clone_graph(node):
    if not node:
        return None
    copies = {}

    def dfs(original):
        if original in copies:
            return copies[original]
        copy = Node(original.val)
        copies[original] = copy
        copy.neighbors = [dfs(neighbor) for neighbor in original.neighbors]
        return copy

    return dfs(node)
```

**關鍵：**先放入 map 再遞迴 neighbors，否則 cycle 會無限遞迴。

### Follow-up 1：原題直接變形
**問：圖非常深？**

**答：**改用 BFS queue，先建立 start copy；彈出原節點時建立尚未複製的 neighbors 並連 edge，避免 recursion depth。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Clone Graph》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：map old_node→new_node 同時負責 identity preservation 與 visited；第一次看到節點就先建立 clone，再遞迴／迭代連接 neighbors。 失效情境包括：若 edge weight 不相等，普通 BFS 不保最短；若 visited key 遺漏資源維度，會錯誤合併不同狀態。
>
> 替代路線是：改用 0-1 BFS、Dijkstra、A*、bidirectional BFS 或壓縮 state；多 query 可預處理 connected components。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent[state] 與造成轉移的 action；抵達 target 後逆向重建 path，全部最短路則保存多個 parents。
>
> 套回《Clone Graph》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超大圖採 frontier batching、外部 visited 或雙向搜尋；分散式 traversal 要處理重複訊息與 eventual consistency。
>
> 此外必須把《Clone Graph》目前隱含的前提寫成 contract：深拷貝一個可能含 cycle 的 graph。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 核心題 3：Rotting Oranges

### 題目

腐爛橘子每分鐘感染上下左右新鮮橘子，求全部腐爛所需時間。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 腐爛橘子每分鐘感染上下左右新鮮橘子，求全部腐爛所需時間。
>
> **核心轉換：** multi-source BFS 把所有初始 rotten oranges 同時入 queue；每一層代表一分鐘，並用 fresh count 判斷是否仍有不可達橘子。
>
> **主要知識點：** Graph DFS/BFS、State Graph 與最短步數。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Rotting Oranges
      │
      ├─ 暴力路線：從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態
      │
      ▼  找出本題最關鍵的轉換
核心觀察：multi-source BFS 把所有初始 rotten oranges 同時入 queue；每一層代表一分鐘，並用 fresh count 判斷是否仍有不可達橘子。
      │
Pattern toolbox：node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue
      │
      ├─ 狀態轉移：從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier
      │
      ├─ 永遠成立：visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 腐爛橘子每分鐘感染上下左右新鮮橘子，求全部腐爛所需時間。
2. **寫出暴力：** 從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** multi-source BFS 把所有初始 rotten oranges 同時入 queue；每一層代表一分鐘，並用 fresh count 判斷是否仍有不可達橘子。
4. **定義 state 與轉移：** 使用「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」承載上述觀察，再執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」代表什麼，再說每一步如何「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開」的 base case。
>
> 2. **維持：** 每次執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」後，狀態仍與已處理資料一致。關鍵論證是：可達性用 path length induction；無權最短路證明 BFS 第一次到達時已走最少 edges。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：圖不連通、cycle、node identity、grid 邊界、狀態除位置外還有資源，以及何時可標 visited。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

```python
from collections import deque

def oranges_rotting(grid):
    rows, cols = len(grid), len(grid[0])
    q = deque()
    fresh = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 2:
                q.append((r, c, 0))
            elif grid[r][c] == 1:
                fresh += 1

    minutes = 0
    while q:
        r, c, minutes = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1:
                grid[nr][nc] = 2
                fresh -= 1
                q.append((nr, nc, minutes + 1))
    return minutes if fresh == 0 else -1
```

### Follow-up 1：原題直接變形
**問：不同感染源速度不同？**

**答：**邊權不再相同，改用 multi-source Dijkstra；heap 初始放入所有來源與時間零。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Rotting Oranges》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：multi-source BFS 把所有初始 rotten oranges 同時入 queue；每一層代表一分鐘，並用 fresh count 判斷是否仍有不可達橘子。 失效情境包括：若 edge weight 不相等，普通 BFS 不保最短；若 visited key 遺漏資源維度，會錯誤合併不同狀態。
>
> 替代路線是：改用 0-1 BFS、Dijkstra、A*、bidirectional BFS 或壓縮 state；多 query 可預處理 connected components。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent[state] 與造成轉移的 action；抵達 target 後逆向重建 path，全部最短路則保存多個 parents。
>
> 套回《Rotting Oranges》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超大圖採 frontier batching、外部 visited 或雙向搜尋；分散式 traversal 要處理重複訊息與 eventual consistency。
>
> 此外必須把《Rotting Oranges》目前隱含的前提寫成 contract：腐爛橘子每分鐘感染上下左右新鮮橘子，求全部腐爛所需時間。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

# 上限題

## 難題 1：Word Ladder II

### 題目

每次改一個字母且中間字必須在 dictionary。回傳從 begin 到 end 的所有最短轉換序列。

> [!tip]- 三層提示
> 1. BFS 找最短距離。
> 2. 不能找到 end 就立刻停止整層，因為同層還可能產生其他最短 parent。
> 3. 保存 `child -> all shortest parents`，最後 backtrack。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每次改一個字母且中間字必須在 dictionary。回傳從 begin 到 end 的所有最短轉換序列。
>
> **核心轉換：** BFS 依層建立 parent DAG。第一次發現 word 時設定 distance；若另一條 edge 也得到相同 distance，就追加 parent。完成 end 所在層後停止，再反向重建所有 paths。
>
> **主要知識點：** Graph DFS/BFS、State Graph 與最短步數。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Word Ladder II
      │
      ├─ 暴力路線：從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態
      │
      ▼  找出本題最關鍵的轉換
核心觀察：BFS 依層建立 parent DAG。第一次發現 word 時設定 distance；若另一條 edge 也得到相同 distance，就追加 parent。完成 end 所在層後停止，再反向重建所有 paths。
      │
Pattern toolbox：node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue
      │
      ├─ 狀態轉移：從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier
      │
      ├─ 永遠成立：visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每次改一個字母且中間字必須在 dictionary。回傳從 begin 到 end 的所有最短轉換序列。
2. **寫出暴力：** 從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** BFS 依層建立 parent DAG。第一次發現 word 時設定 distance；若另一條 edge 也得到相同 distance，就追加 parent。完成 end 所在層後停止，再反向重建所有 paths。
4. **定義 state 與轉移：** 使用「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」承載上述觀察，再執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」代表什麼，再說每一步如何「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開」的 base case。
>
> 2. **維持：** 每次執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」後，狀態仍與已處理資料一致。關鍵論證是：可達性用 path length induction；無權最短路證明 BFS 第一次到達時已走最少 edges。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：圖不連通、cycle、node identity、grid 邊界、狀態除位置外還有資源，以及何時可標 visited。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

BFS 依層建立 parent DAG。第一次發現 word 時設定 distance；若另一條 edge 也得到相同 distance，就追加 parent。完成 end 所在層後停止，再反向重建所有 paths。

```python
from collections import defaultdict, deque

def find_ladders(begin, end, word_list):
    words = set(word_list)
    if end not in words:
        return []

    parents = defaultdict(list)
    distance = {begin: 0}
    q = deque([begin])
    found_distance = None

    while q:
        word = q.popleft()
        d = distance[word]
        if found_distance is not None and d >= found_distance:
            continue
        chars = list(word)
        for i, original in enumerate(chars):
            for code in range(ord("a"), ord("z") + 1):
                ch = chr(code)
                if ch == original:
                    continue
                chars[i] = ch
                candidate = "".join(chars)
                if candidate not in words:
                    continue
                if candidate not in distance:
                    distance[candidate] = d + 1
                    q.append(candidate)
                if distance[candidate] == d + 1:
                    parents[candidate].append(word)
                if candidate == end:
                    found_distance = d + 1
            chars[i] = original

    if end not in distance:
        return []

    answer = []
    path = [end]

    def build(word):
        if word == begin:
            answer.append(path[::-1])
            return
        for parent in parents[word]:
            path.append(parent)
            build(parent)
            path.pop()

    build(end)
    return answer
```

- BFS 圖建立與字長、dictionary 大小相關
- 輸出所有 paths 本身可能指數大

### Follow-up 1：原題直接變形
**問：只求一條最短 path？**

**答：**每個 word 只保存一個 parent；第一次發現 end 後即可在完成必要狀態時重建。記憶體大幅下降。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Word Ladder II》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：BFS 依層建立 parent DAG。第一次發現 word 時設定 distance；若另一條 edge 也得到相同 distance，就追加 parent。完成 end 所在層後停止，再反向重建所有 paths。 失效情境包括：若 edge weight 不相等，普通 BFS 不保最短；若 visited key 遺漏資源維度，會錯誤合併不同狀態。
>
> 替代路線是：改用 0-1 BFS、Dijkstra、A*、bidirectional BFS 或壓縮 state；多 query 可預處理 connected components。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent[state] 與造成轉移的 action；抵達 target 後逆向重建 path，全部最短路則保存多個 parents。
>
> 套回《Word Ladder II》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超大圖採 frontier batching、外部 visited 或雙向搜尋；分散式 traversal 要處理重複訊息與 eventual consistency。
>
> 此外必須把《Word Ladder II》目前隱含的前提寫成 contract：每次改一個字母且中間字必須在 dictionary。回傳從 begin 到 end 的所有最短轉換序列。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 2：Shortest Path in a Grid with Obstacles Elimination

### 題目

網格中可消除最多 `k` 個障礙，求左上到右下最短步數。

> [!tip]- 三層提示
> 1. State 不只是 `(r,c)`，還包含剩餘消除次數。
> 2. 同一位置若以更多剩餘次數到達，會支配較少剩餘次數的 state。
> 3. BFS，並為每格只保存目前看過的最大 remaining。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 網格中可消除最多 k 個障礙，求左上到右下最短步數。
>
> **核心轉換：** BFS 保證第一次到終點步數最短。best[r][c] 保存到此格時最多剩餘消除數；新的 state 若不比它大，就不可能提供更好的未來。
>
> **主要知識點：** Graph DFS/BFS、State Graph 與最短步數。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Shortest Path in a Grid with Obstacles Elimination
      │
      ├─ 暴力路線：從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態
      │
      ▼  找出本題最關鍵的轉換
核心觀察：BFS 保證第一次到終點步數最短。best[r][c] 保存到此格時最多剩餘消除數；新的 state 若不比它大，就不可能提供更好的未來。
      │
Pattern toolbox：node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue
      │
      ├─ 狀態轉移：從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier
      │
      ├─ 永遠成立：visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 網格中可消除最多 k 個障礙，求左上到右下最短步數。
2. **寫出暴力：** 從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** BFS 保證第一次到終點步數最短。best[r][c] 保存到此格時最多剩餘消除數；新的 state 若不比它大，就不可能提供更好的未來。
4. **定義 state 與轉移：** 使用「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」承載上述觀察，再執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」代表什麼，再說每一步如何「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開」的 base case。
>
> 2. **維持：** 每次執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」後，狀態仍與已處理資料一致。關鍵論證是：可達性用 path length induction；無權最短路證明 BFS 第一次到達時已走最少 edges。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：圖不連通、cycle、node identity、grid 邊界、狀態除位置外還有資源，以及何時可標 visited。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

BFS 保證第一次到終點步數最短。`best[r][c]` 保存到此格時最多剩餘消除數；新的 state 若不比它大，就不可能提供更好的未來。

```python
from collections import deque

def shortest_path(grid, k):
    rows, cols = len(grid), len(grid[0])
    if rows == 1 and cols == 1:
        return 0
    q = deque([(0, 0, k, 0)])
    best = [[-1] * cols for _ in range(rows)]
    best[0][0] = k

    while q:
        r, c, remaining, steps = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            next_remaining = remaining - grid[nr][nc]
            if next_remaining < 0:
                continue
            if nr == rows - 1 and nc == cols - 1:
                return steps + 1
            if next_remaining > best[nr][nc]:
                best[nr][nc] = next_remaining
                q.append((nr, nc, next_remaining, steps + 1))
    return -1
```

### Follow-up 1：原題直接變形
**問：若每個障礙消除成本不同？**

**答：**若步數仍是主要目標、成本只是 budget，state 保存 remaining budget 仍可 BFS，但狀態數增大；若目標也包含成本，需 Dijkstra 或 multi-criteria shortest path。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Shortest Path in a Grid with Obstacles Elimination》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：BFS 保證第一次到終點步數最短。best[r][c] 保存到此格時最多剩餘消除數；新的 state 若不比它大，就不可能提供更好的未來。 失效情境包括：若 edge weight 不相等，普通 BFS 不保最短；若 visited key 遺漏資源維度，會錯誤合併不同狀態。
>
> 替代路線是：改用 0-1 BFS、Dijkstra、A*、bidirectional BFS 或壓縮 state；多 query 可預處理 connected components。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent[state] 與造成轉移的 action；抵達 target 後逆向重建 path，全部最短路則保存多個 parents。
>
> 套回《Shortest Path in a Grid with Obstacles Elimination》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超大圖採 frontier batching、外部 visited 或雙向搜尋；分散式 traversal 要處理重複訊息與 eventual consistency。
>
> 此外必須把《Shortest Path in a Grid with Obstacles Elimination》目前隱含的前提寫成 contract：網格中可消除最多 k 個障礙，求左上到右下最短步數。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 3：Bus Routes

### 題目

每條 bus route 是循環停靠站列表。可在相同站換車，求 source 到 target 最少搭幾班 bus。

> [!tip]- 三層提示
> 1. BFS 的一層應代表搭一班新 bus。
> 2. 建立 `stop -> routes`。
> 3. Route 一旦展開過不必再展開；stop 也可標記避免重複。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 每條 bus route 是循環停靠站列表。可在相同站換車，求 source 到 target 最少搭幾班 bus。
>
> **核心轉換：** Queue 保存目前可到達 stops 與已搭 bus 數。從 stop 找所有未搭過 routes，搭上後可到 route 的所有 stops。
>
> **主要知識點：** Graph DFS/BFS、State Graph 與最短步數。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Bus Routes
      │
      ├─ 暴力路線：從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態
      │
      ▼  找出本題最關鍵的轉換
核心觀察：Queue 保存目前可到達 stops 與已搭 bus 數。從 stop 找所有未搭過 routes，搭上後可到 route 的所有 stops。
      │
Pattern toolbox：node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue
      │
      ├─ 狀態轉移：從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier
      │
      ├─ 永遠成立：visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 每條 bus route 是循環停靠站列表。可在相同站換車，求 source 到 target 最少搭幾班 bus。
2. **寫出暴力：** 從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** Queue 保存目前可到達 stops 與已搭 bus 數。從 stop 找所有未搭過 routes，搭上後可到 route 的所有 stops。
4. **定義 state 與轉移：** 使用「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」承載上述觀察，再執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(\text{total route entries})$；空間：同級

> [!tip] 一句話記憶
> 先說清楚「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」代表什麼，再說每一步如何「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開」的 base case。
>
> 2. **維持：** 每次執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」後，狀態仍與已處理資料一致。關鍵論證是：可達性用 path length induction；無權最短路證明 BFS 第一次到達時已走最少 edges。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：圖不連通、cycle、node identity、grid 邊界、狀態除位置外還有資源，以及何時可標 visited。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

Queue 保存目前可到達 stops 與已搭 bus 數。從 stop 找所有未搭過 routes，搭上後可到 route 的所有 stops。

```python
from collections import defaultdict, deque

def num_buses_to_destination(routes, source, target):
    if source == target:
        return 0
    stop_to_routes = defaultdict(list)
    for route_id, stops in enumerate(routes):
        for stop in stops:
            stop_to_routes[stop].append(route_id)

    q = deque([(source, 0)])
    seen_stops = {source}
    seen_routes = set()

    while q:
        stop, buses = q.popleft()
        for route_id in stop_to_routes[stop]:
            if route_id in seen_routes:
                continue
            seen_routes.add(route_id)
            for next_stop in routes[route_id]:
                if next_stop == target:
                    return buses + 1
                if next_stop not in seen_stops:
                    seen_stops.add(next_stop)
                    q.append((next_stop, buses + 1))
    return -1
```

- 時間：$O(\text{total route entries})$
- 空間：同級

### Follow-up 1：原題直接變形
**問：每條 route 有不同票價，求最低票價？**

**答：**把 route transition 權重改成票價，使用 Dijkstra；state 可以是 stop 或 route，依換乘成本定義建圖。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Bus Routes》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：Queue 保存目前可到達 stops 與已搭 bus 數。從 stop 找所有未搭過 routes，搭上後可到 route 的所有 stops。 失效情境包括：若 edge weight 不相等，普通 BFS 不保最短；若 visited key 遺漏資源維度，會錯誤合併不同狀態。
>
> 替代路線是：改用 0-1 BFS、Dijkstra、A*、bidirectional BFS 或壓縮 state；多 query 可預處理 connected components。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent[state] 與造成轉移的 action；抵達 target 後逆向重建 path，全部最短路則保存多個 parents。
>
> 套回《Bus Routes》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超大圖採 frontier batching、外部 visited 或雙向搜尋；分散式 traversal 要處理重複訊息與 eventual consistency。
>
> 此外必須把《Bus Routes》目前隱含的前提寫成 contract：每條 bus route 是循環停靠站列表。可在相同站換車，求 source 到 target 最少搭幾班 bus。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 4：Cut Off Trees for Golf Event

### 題目

網格 `0` 不可走、`1` 空地、`>1` 為樹高。必須依高度由小到大砍樹，求最少總步數，無法完成回傳 `-1`。

> [!tip]- 三層提示
> 1. 砍樹順序固定。
> 2. 每兩棵相鄰目標間是一次 grid shortest path。
> 3. 對每段使用 BFS，任何一段不可達即失敗。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 網格 0 不可走、1 空地、>1 為樹高。必須依高度由小到大砍樹，求最少總步數，無法完成回傳 -1。
>
> **核心轉換：** 收集並排序 (height,r,c)。從 (0,0) 依序 BFS 到下一棵樹；砍完後該格可通行。
>
> **主要知識點：** Graph DFS/BFS、State Graph 與最短步數。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Cut Off Trees for Golf Event
      │
      ├─ 暴力路線：從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態
      │
      ▼  找出本題最關鍵的轉換
核心觀察：收集並排序 (height,r,c)。從 (0,0) 依序 BFS 到下一棵樹；砍完後該格可通行。
      │
Pattern toolbox：node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue
      │
      ├─ 狀態轉移：從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier
      │
      ├─ 永遠成立：visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 網格 0 不可走、1 空地、>1 為樹高。必須依高度由小到大砍樹，求最少總步數，無法完成回傳 -1。
2. **寫出暴力：** 從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 收集並排序 (height,r,c)。從 (0,0) 依序 BFS 到下一棵樹；砍完後該格可通行。
4. **定義 state 與轉移：** 使用「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」承載上述觀察，再執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：以原解法標示的時間與空間複雜度為準；面試時需逐段說明每個迴圈與資料結構的成本。

> [!tip] 一句話記憶
> 先說清楚「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」代表什麼，再說每一步如何「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開」的 base case。
>
> 2. **維持：** 每次執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」後，狀態仍與已處理資料一致。關鍵論證是：可達性用 path length induction；無權最短路證明 BFS 第一次到達時已走最少 edges。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：圖不連通、cycle、node identity、grid 邊界、狀態除位置外還有資源，以及何時可標 visited。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

收集並排序 `(height,r,c)`。從 `(0,0)` 依序 BFS 到下一棵樹；砍完後該格可通行。

```python
from collections import deque

def cut_off_tree(forest):
    rows, cols = len(forest), len(forest[0])
    trees = sorted(
        (forest[r][c], r, c)
        for r in range(rows)
        for c in range(cols)
        if forest[r][c] > 1
    )
    if forest[0][0] == 0:
        return -1 if trees else 0

    def distance(sr, sc, tr, tc):
        q = deque([(sr, sc, 0)])
        seen = {(sr, sc)}
        while q:
            r, c, steps = q.popleft()
            if (r, c) == (tr, tc):
                return steps
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if (
                    0 <= nr < rows and 0 <= nc < cols
                    and forest[nr][nc] != 0
                    and (nr, nc) not in seen
                ):
                    seen.add((nr, nc))
                    q.append((nr, nc, steps + 1))
        return -1

    total = 0
    r = c = 0
    for _, tr, tc in trees:
        steps = distance(r, c, tr, tc)
        if steps == -1:
            return -1
        total += steps
        r, c = tr, tc
    return total
```

### Follow-up 1：原題直接變形
**問：如何加速大量 BFS？**

**答：**可使用 bidirectional BFS、A* Manhattan heuristic，或在障礙結構固定時預先計算 connected components 先快速判斷不可達；最短距離仍需搜尋。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Cut Off Trees for Golf Event》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：收集並排序 (height,r,c)。從 (0,0) 依序 BFS 到下一棵樹；砍完後該格可通行。 失效情境包括：若 edge weight 不相等，普通 BFS 不保最短；若 visited key 遺漏資源維度，會錯誤合併不同狀態。
>
> 替代路線是：改用 0-1 BFS、Dijkstra、A*、bidirectional BFS 或壓縮 state；多 query 可預處理 connected components。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent[state] 與造成轉移的 action；抵達 target 後逆向重建 path，全部最短路則保存多個 parents。
>
> 套回《Cut Off Trees for Golf Event》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超大圖採 frontier batching、外部 visited 或雙向搜尋；分散式 traversal 要處理重複訊息與 eventual consistency。
>
> 此外必須把《Cut Off Trees for Golf Event》目前隱含的前提寫成 contract：網格 0 不可走、1 空地、>1 為樹高。必須依高度由小到大砍樹，求最少總步數，無法完成回傳 -1。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->

---

## 難題 5：Swim in Rising Water

### 題目

網格值是地面高度。時間 `t` 時可走高度不超過 `t` 的格子，求左上到右下最早時間。

> [!tip]- 三層提示
> 1. Path cost 不是 edge sum，而是路徑上的最大高度。
> 2. Dijkstra 的 distance 改成「到此處最小可能的最大值」。
> 3. Relaxation 是 `max(current_cost, neighbor_height)`。

<!-- deep-learning:start -->
> [!abstract] 這題真正考什麼
>
> **題目目標：** 網格值是地面高度。時間 t 時可走高度不超過 t 的格子，求左上到右下最早時間。
>
> **核心轉換：** 使用 minimax Dijkstra。Heap 每次取目前可能到達時間最小的 state；第一次彈出終點時已最優。
>
> **主要知識點：** Graph DFS/BFS、State Graph 與最短步數。面試官要確認你能先定義 state 與 invariant，再從限制推導出資料結構，而不是只背函式。

### 視覺化題解：從暴力到最佳模型

```text
題目：Swim in Rising Water
      │
      ├─ 暴力路線：從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態
      │
      ▼  找出本題最關鍵的轉換
核心觀察：使用 minimax Dijkstra。Heap 每次取目前可能到達時間最小的 state；第一次彈出終點時已最優。
      │
Pattern toolbox：node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue
      │
      ├─ 狀態轉移：從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier
      │
      ├─ 永遠成立：visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開
      │
      ▼
在狀態足以回答題目時更新／輸出答案
```

### 五步推導

1. **重述輸出：** 網格值是地面高度。時間 t 時可走高度不超過 t 的格子，求左上到右下最早時間。
2. **寫出暴力：** 從每個起點重複搜尋，或在路徑中不記錄 visited 而反覆進入同一狀態。先估算它為何會超過 constraints，不要直接跳答案。
3. **找瓶頸與轉換：** 使用 minimax Dijkstra。Heap 每次取目前可能到達時間最小的 state；第一次彈出終點時已最優。
4. **定義 state 與轉移：** 使用「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」承載上述觀察，再執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。寫 code 前先用一個小例子手動走過每次狀態變化。
5. **定義回傳時機：** 只有在 invariant 成立時才更新答案；目前解法的成本為：時間：$O(n^2\log n)$；空間：$O(n^2)$

> [!tip] 一句話記憶
> 先說清楚「node/state、adjacency generator、visited，以及 DFS stack 或分層 BFS queue」代表什麼，再說每一步如何「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」。只要 state、transition、invariant 三句能閉合，程式碼通常只是翻譯。

> [!success]- 正確性證明骨架
>
> 1. **初始化：** 在尚未處理任何輸入時，建立的空狀態符合定義；也就是「visited 中的狀態已被完整處理或已有不劣距離；BFS queue 按距離非遞減順序展開」的 base case。
>
> 2. **維持：** 每次執行「從 frontier 取出狀態，產生合法 neighbors；首次到達或取得更佳狀態時加入 frontier」後，狀態仍與已處理資料一致。關鍵論證是：可達性用 path length induction；無權最短路證明 BFS 第一次到達時已走最少 edges。
>
> 3. **終止：** 迴圈或遞迴結束時，所有可能影響答案的候選都已被處理；由 invariant 可直接推出回傳值正確。

> [!warning]- 最容易錯的地方
>
> 優先手算並測試：圖不連通、cycle、node identity、grid 邊界、狀態除位置外還有資源，以及何時可標 visited。
>
> 不要只跑 sample。至少準備最小輸入、全部相同、答案不存在、答案在邊界，以及會讓錯誤 invariant 立即暴露的反例。
<!-- deep-learning:end -->

### 詳解

使用 minimax Dijkstra。Heap 每次取目前可能到達時間最小的 state；第一次彈出終點時已最優。

```python
from heapq import heappush, heappop

def swim_in_water(grid):
    n = len(grid)
    heap = [(grid[0][0], 0, 0)]
    best = [[float("inf")] * n for _ in range(n)]
    best[0][0] = grid[0][0]

    while heap:
        cost, r, c = heappop(heap)
        if cost != best[r][c]:
            continue
        if (r, c) == (n - 1, n - 1):
            return cost
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < n:
                next_cost = max(cost, grid[nr][nc])
                if next_cost < best[nr][nc]:
                    best[nr][nc] = next_cost
                    heappush(heap, (next_cost, nr, nc))
```

- 時間：$O(n^2\log n)$
- 空間：$O(n^2)$

### Follow-up 1：原題直接變形
**問：還有什麼解法？**

**答：**Binary search 時間 `t`，用 DFS/BFS 檢查只走高度 `<=t` 是否可達；或依高度逐格啟用並用 Union-Find，起點終點連通時的高度即答案。

<!-- deep-followups:start -->
> [!question]- Follow-up 2：如果《Swim in Rising Water》的 constraints 改變，原方法何時會失效？
>
> **答案：先指出失效的假設，而不是立刻換資料結構。**
>
> 目前解法依賴的核心是：使用 minimax Dijkstra。Heap 每次取目前可能到達時間最小的 state；第一次彈出終點時已最優。 失效情境包括：若 edge weight 不相等，普通 BFS 不保最短；若 visited key 遺漏資源維度，會錯誤合併不同狀態。
>
> 替代路線是：改用 0-1 BFS、Dijkstra、A*、bidirectional BFS 或壓縮 state；多 query 可預處理 connected components。 面試時應比較新舊方案的時間、空間、實作風險，以及新限制是否真的值得增加複雜度。

> [!question]- Follow-up 3：如果要回傳可驗證的完整解，而不只是最終數值或布林值？
>
> **答案：把 reconstruction 資訊視為 state 的一部分。**
>
> 針對這個 pattern，典型做法是：保存 parent[state] 與造成轉移的 action；抵達 target 後逆向重建 path，全部最短路則保存多個 parents。
>
> 套回《Swim in Rising Water》時，先定義 witness 是 index、路徑、切點、操作序列或資料結構快照；只在答案改善時更新其 predecessor。最後由終點反向重建，並用原題條件重新驗證。這通常增加 O(n) 級別儲存；若原本做了空間壓縮，需在記憶體與可重建性之間取捨。

> [!question]- Follow-up 4：如果改成線上更新、超大資料或 production API，還要補哪些設計？
>
> **答案：先保護 invariant，再談擴充。**
>
> 超大圖採 frontier batching、外部 visited 或雙向搜尋；分散式 traversal 要處理重複訊息與 eventual consistency。
>
> 此外必須把《Swim in Rising Water》目前隱含的前提寫成 contract：網格值是地面高度。時間 t 時可走高度不超過 t 的格子，求左上到右下最早時間。加入 metrics 與 property-based tests，持續檢查 state 與輸出是否一致；若允許近似答案，還要明確定義誤差界線與退化策略，而不是只說「加 cache／加機器」。
<!-- deep-followups:end -->
## 本章檢查

- [ ] 先定義 graph 的 node、edge、state。
- [ ] BFS level 對應題目真正成本。
- [ ] 資源不同時不會錯誤合併 state。
- [ ] 能辨認 multi-source 與 minimax path。
