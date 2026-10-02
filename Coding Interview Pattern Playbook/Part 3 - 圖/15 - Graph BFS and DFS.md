---
chapter: 15
title: Graph：BFS 與 DFS
part: 3
---

# 第 15 章　Graph：BFS 與 DFS

> [!abstract] 本章地圖
> **一句話**：先把題目畫成圖（節點是什麼、邊是什麼），再用 visited 保證每個節點只處理一次；要「連通、能不能到、整塊標記」用 DFS 或 BFS 都行，要「最少幾步」就用 BFS，因為它按距離一層一層往外擴。
>
> **辨識訊號**：
> - 二維格子上的「島嶼」「區域」「被包圍」「連在一起的一塊」
> - 「最少幾步／幾分鐘／幾次轉換」，而且每一步代價相同
> - 多個起點同時往外擴散（腐爛、感染、火、距離最近的出口）
> - 「能不能從 A 走到 B」「哪些點能到達邊界」，或從終點反著搜比較容易
> - 每次可以把一個字串、密碼鎖、棋盤狀態改一點點，問最少要改幾次
> - 狀態除了位置還帶著額外資訊（剩幾次機會、拿了哪些鑰匙、拜訪過哪些點），而且額外資訊的組合數很小
>
> **核心題**：200、133、994、417、130
>
> **難題**：127、126、1293、847、864

## 15.1 這個 Pattern 解決什麼問題

先看一個最小的例子。一個 5 × 5 的迷宮，`.` 是路、`#` 是牆，要從左上角走到右下角，問最少幾步。最直接的想法是列舉所有路徑、取最短的；可是路徑可以繞圈，也可以在岔路口選不同方向，數量隨著格子數呈指數成長，連 10 × 10 的迷宮都列舉不完。真正的問題是：同一個格子會被無數條不同的路徑反覆經過，而我們每次都從頭重算它之後的部分。

圖搜尋省下的就是這些重複。把每個格子看成節點、相鄰且都不是牆的兩格之間連一條邊，問題就變成「在圖上從起點到終點的最短路徑」。BFS（breadth-first search，廣度優先搜尋）從起點出發，先走完所有距離 1 的點，再走距離 2 的點，以此類推；每個點**第一次被看到的時候**，看到它的那一層就是它的最短距離，之後再從別條路經過它都不會更短，所以直接忽略。於是每個點只進出 queue 一次、每條邊只檢查常數次，總時間 O(V + E)，迷宮就是 O(格子數)。

DFS（depth-first search，深度優先搜尋）用的是同一個「visited 保證只處理一次」的想法，只是走法不同：一路往深處走到底，走不下去再退回上一個岔路口。它不保證先找到最短路徑，但在「把整塊連通區域找出來」「判斷能不能到達」「從邊界往內標記」這類只關心**可達性**的問題上，DFS 和 BFS 一樣是 O(V + E)，程式通常更短。

所以本章所有題目都會變成同樣三個問題：**節點是什麼？邊是什麼？我要的是可達性還是最短步數？** 核心題的節點都是格子或現成的圖節點；難題的關鍵則在於節點不再只是「位置」：Word Ladder 的節點是字串，1293 的節點是「位置＋剩下幾次消除」，847 的節點是「目前所在＋已拜訪集合」。一旦把節點定義對，搜尋本身仍然是同一個 BFS 模板。

## 15.2 辨識訊號

| 題目特徵 | 為什麼是 BFS／DFS | 本章哪一題 |
|---|---|---|
| 格子上數「有幾塊」「最大的一塊」 | 每塊是一個連通元件，從未拜訪的格子出發整塊標記，出發次數就是塊數 | 核心題 1（200） |
| 要複製、序列化或比較一張可能有環的圖 | 走訪所有節點，visited 用「原節點 → 新節點」的 hash map 兼任 | 核心題 2（133） |
| 多個源頭同時擴散，問多久全部被影響 | multi-source BFS：所有源頭一起放進第 0 層，層數就是時間 | 核心題 3（994） |
| 問「哪些格子能流到邊界」或「哪些區域碰不到邊界」 | 從每格出發搜尋太慢；改從邊界反向搜尋，一次搜完 | 核心題 4（417）、核心題 5（130） |
| 每次改一個字元，最少幾次從 A 變成 B | 狀態是字串，邊是「差一個字元」，等權最短路 | 難題 1（127）、難題 2（126） |
| 最短路，但有「最多可以打穿 k 道牆」之類的資源限制 | 狀態加上剩餘資源，(位置, 資源) 上做 BFS | 難題 3（1293） |
| 要拜訪所有點或撿齊所有鑰匙，點數或鑰匙數 ≤ 12 | 狀態加上 bitmask，(位置, 集合) 上做 BFS | 難題 4（847）、難題 5（864） |
| 圖有權重但只有 0 和 1 | 0-1 BFS（deque 前後放）；權重一般化就換 Dijkstra（第 18 章） | 994 F2、1293 F1 |

一個實用的反向檢查：如果邊有不同的權重（例如不同道路的長度不同），一般的 BFS 就不能保證「第一次看到就是最短」，要換成 Dijkstra（第 18 章）；如果題目問的是「有向圖的先後順序」或「有沒有環」，那是 topological sort（第 16 章）；如果圖會一直加邊、而且要反覆問「兩點是否連通」，union-find（第 17 章）比每次重新搜尋好。

## 15.3 模板與原理：建圖、BFS、DFS

面試中的圖通常不會直接給你鄰接串列，而是給邊的列表、格子或規則。第一步永遠是決定表示法：節點編號是 0 到 n − 1 時用 `list[list[int]]` 的 adjacency list（鄰接串列）；節點是字串或座標時用 `dict` 或 `defaultdict(list)`；格子則不必建圖，直接用四個方向算鄰居。接著就是兩個模板。

```python
from collections import deque


def build_graph(n: int, edges: list[tuple[int, int]], directed: bool = False) -> list[list[int]]:
    graph = [[] for _ in range(n)]
    for u, v in edges:
        graph[u].append(v)
        if not directed:
            graph[v].append(u)
    return graph


def bfs_dist(graph: list[list[int]], src: int) -> list[int]:
    """回傳 src 到每個節點的最少邊數；到不了是 -1。"""
    dist = [-1] * len(graph)
    dist[src] = 0                      # 入隊時就標記
    queue = deque([src])
    while queue:
        u = queue.popleft()
        for v in graph[u]:
            if dist[v] == -1:          # 第一次看到 v 時的距離就是最短距離
                dist[v] = dist[u] + 1
                queue.append(v)
    return dist


def count_components(graph: list[list[int]]) -> int:
    """迭代式 DFS：用 stack 取代遞迴，數連通元件。"""
    seen = [False] * len(graph)
    comps = 0
    for s in range(len(graph)):
        if seen[s]:
            continue
        comps += 1
        seen[s] = True
        stack = [s]
        while stack:
            u = stack.pop()
            for v in graph[u]:
                if not seen[v]:
                    seen[v] = True
                    stack.append(v)
    return comps


def has_path_recursive(graph: list[list[int]], s: int, t: int) -> bool:
    seen = set()

    def dfs(u: int) -> bool:
        if u == t:
            return True
        seen.add(u)
        return any(v not in seen and dfs(v) for v in graph[u])

    return dfs(s)


g = build_graph(6, [(0, 1), (1, 2), (0, 3), (3, 2), (4, 5)])
assert bfs_dist(g, 0) == [0, 1, 2, 1, -1, -1]
assert bfs_dist(g, 4) == [-1, -1, -1, -1, 0, 1]
assert count_components(g) == 2
assert count_components(build_graph(3, [])) == 3          # 沒有邊：每點自成一塊
assert has_path_recursive(g, 0, 2) and not has_path_recursive(g, 0, 5)
d = build_graph(3, [(0, 1), (1, 2)], directed=True)
assert bfs_dist(d, 2) == [-1, -1, 0]                       # 有向圖不能逆著走
print("all tests passed")
```

**BFS 的 invariant（不變式）**。queue 裡的節點，距離永遠只有兩種值：前面一段是 d、後面一段是 d + 1。一開始只有 src，距離 0，成立。每次從前端取出距離 d 的 u，只會把距離 d + 1 的新節點加到尾端，所以「前段 d、後段 d + 1」仍然成立；當前段的 d 取完了，queue 裡全是 d + 1，下一輪再往後加 d + 2。由此可知節點是**按照距離由小到大**出隊的。某個 v 第一次被看到時，看到它的 u 是所有能到 v 的鄰居中最早出隊的，也就是距離最小的，所以 `dist[u] + 1` 一定是 v 的最短距離。這個論證只依賴「每條邊代價都是 1」，一旦邊有不同權重就失效，這就是 Dijkstra 存在的理由。

**每一行為什麼這樣寫**：

- `dist[src] = 0` 和 `dist[v] = dist[u] + 1` 都寫在**入隊時**，而不是出隊時。如果等到出隊才標記，同一個節點在被處理之前可能被好幾個鄰居重複加入 queue，queue 最多膨脹到 O(E) 個項目；若出隊時又沒有檢查「是否已處理過」，還會重複展開它的鄰居。答案也許仍然正確，但時間與記憶體都多出好幾倍。入隊即標記，保證每個節點恰好入隊一次。
- `dist` 同時是 visited 與答案。用 -1 代表「還沒看過」，省掉一個 `seen` 集合；需要回傳路徑時，再加一個 `parent` 陣列記錄「是誰第一次看到我」。
- 用 `deque.popleft()`，不要用 `list.pop(0)`。後者是 O(n)，會讓整個 BFS 變成 O(V²)。
- 迭代式 DFS 用 `stack.pop()` 取代遞迴。它和遞迴 DFS 的拜訪順序不完全相同（入棧時標記，所以不是嚴格的「先深」），但對可達性、連通元件、整塊標記這些只關心「誰被拜訪」的問題完全等價，而且不會遇到 Python 預設約 1000 層的遞迴上限。
- 遞迴 DFS 適合需要「回溯時做事」的情況，例如 clone 時要先建好鄰居再回傳、或第 16 章的環偵測需要知道節點「正在堆疊中」。格子題用遞迴時，一條蛇形路徑可以深達 m·n 層，要嘛改成迭代，要嘛 `sys.setrecursionlimit`，面試時主動提這點會加分。

**表示法的選擇**。adjacency list 的空間是 O(V + E)，枚舉鄰居的時間與度數成正比，幾乎所有面試題都用它。adjacency matrix 是 O(V²) 空間，只有在 V 很小（≤ 幾百）而且需要 O(1) 查詢「u、v 之間有沒有邊」時才划算。「隱式圖」則完全不建圖：格子的鄰居用方向陣列算出來，Word Ladder 的鄰居用「改一個字元」產生，狀態圖的鄰居用規則推出來。隱式圖是難題的常態，因為節點數可能有 10⁵ 以上，而邊數更多，預先建出來既浪費又沒必要。

## 15.4 Grid、逐層 BFS 與 Multi-source

格子題是圖搜尋最常見的包裝。格子 `(r, c)` 的四個鄰居是 `(r ± 1, c)` 與 `(r, c ± 1)`，只要用一個方向陣列 `DIRS` 加上邊界檢查即可，不需要真的建 adjacency list。下面的模板同時示範兩個在核心題反覆出現的技巧：**multi-source（多源）BFS** 與**逐層處理**。

```python
from collections import deque

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def grid_multi_source_bfs(grid: list[str], sources: list[tuple[int, int]]) -> list[list[int]]:
    """'#' 是牆。回傳每格到最近 source 的步數，到不了是 -1。"""
    m, n = len(grid), len(grid[0])
    dist = [[-1] * n for _ in range(m)]
    queue = deque()
    for r, c in sources:                 # 所有起點一起放進第 0 層
        dist[r][c] = 0
        queue.append((r, c))
    while queue:
        r, c = queue.popleft()
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < m and 0 <= nc < n and grid[nr][nc] != "#" and dist[nr][nc] == -1:
                dist[nr][nc] = dist[r][c] + 1
                queue.append((nr, nc))
    return dist


def bfs_levels(grid: list[str], start: tuple[int, int]) -> list[list[tuple[int, int]]]:
    """逐層 BFS：每一輪把目前 queue 裡的整層處理完。"""
    m, n = len(grid), len(grid[0])
    seen = {start}
    queue = deque([start])
    levels = []
    while queue:
        levels.append(list(queue))
        for _ in range(len(queue)):      # 只處理這一層，新加入的屬於下一層
            r, c = queue.popleft()
            for dr, dc in DIRS:
                nxt = (r + dr, c + dc)
                if 0 <= nxt[0] < m and 0 <= nxt[1] < n and grid[nxt[0]][nxt[1]] != "#" and nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
    return levels


grid = ["...",
        ".#.",
        "..."]
assert grid_multi_source_bfs(grid, [(0, 0)]) == [[0, 1, 2], [1, -1, 3], [2, 3, 4]]
assert grid_multi_source_bfs(grid, [(0, 0), (2, 2)]) == [[0, 1, 2], [1, -1, 1], [2, 1, 0]]
assert grid_multi_source_bfs(["#.#"], [(0, 1)]) == [[-1, 0, -1]]
assert [len(lv) for lv in bfs_levels(grid, (0, 0))] == [1, 2, 2, 2, 1]
print("all tests passed")
```

**Multi-source 為什麼正確**。想像加一個虛擬的超級起點 S，從 S 到每個真正的源頭各連一條代價 0 的邊。從 S 做 BFS，第一步就把所有源頭放進第 0 層，接下來和單源 BFS 完全一樣，所以每格得到的是「到最近源頭」的距離。它的成本是 O(mn)，和源頭數無關；相比之下，對每個源頭各跑一次 BFS 再取最小值，要 O(源頭數 × mn)。核心題 3（994）就是這個模板，542 01 Matrix、286 Walls and Gates 也都是。

**逐層處理**。標準 BFS 用 `dist` 陣列記距離，不需要分層。但有些題目要在「每一層結束時」做事：994 要數過了幾分鐘、847 和 864 要在層數等於答案時回傳、126 要確保同一層的節點不會互相當父節點。這時用 `for _ in range(len(queue))` 包住內層：進入 for 迴圈那一刻的 `len(queue)` 就是這一層的大小，處理期間加入的節點都排在後面，屬於下一層。兩種寫法時間相同，選哪個取決於你需要的是「每個點的距離」還是「層的邊界」。

**反向搜尋**。有時候從每個格子出發去找「能不能到邊界」要做 mn 次搜尋，總共 O((mn)²)；把方向反過來，從邊界出發往內搜，一次就能找出所有「能到達邊界」的格子，O(mn)。核心題 4（417）的「水往低處流」反過來就是「從海洋往高處爬」；核心題 5（130）的「被包圍的區域」反過來就是「從邊界出發碰得到的區域不被包圍」。判斷要不要反向的訊號是：**終點集合很固定（邊界、某一類格子），起點卻是「每一格」**。

```text
grid_multi_source_bfs，sources = (0,0) 與 (2,2)

第 0 層          第 1 層          第 2 層（結束）
S . .            0 1 .            0 1 2
. # .     →      1 # 1     →      1 # 1
. . S            . 1 0            2 1 0

兩個源頭同時擴散：(0,2) 和 (2,0) 在第 2 層被「先到的那一邊」標記，
之後另一邊再碰到時 dist 已經不是 -1，直接跳過，所以每格只入隊一次。
```

## 15.5 狀態圖：當節點不只是位置

本章的五道難題都在同一件事上加碼：**節點不再只是一個位置，而是「位置＋額外資訊」的組合**。判斷要不要加狀態的方法很直接：問自己「兩次走到同一個格子，未來能做的事一樣嗎？」如果一樣，visited 只需要記位置；如果不一樣（一次還剩 2 次打穿牆的機會、另一次只剩 0 次；一次拿著鑰匙 a、另一次沒有），那它們就是**不同的節點**，visited 必須記錄整個狀態。

| 題目 | 節點（狀態） | 狀態數 | 邊 |
|---|---|---|---|
| 127 Word Ladder | 字串 | 字典大小 N | 改一個字元後仍在字典 |
| 1293 消除障礙物 | (r, c, 剩餘消除次數) | m · n · (k + 1) | 走到鄰格；是牆就消耗 1 |
| 847 拜訪所有節點 | (目前節點, 已拜訪集合) | n · 2ⁿ | 走到鄰居，集合加入它 |
| 864 拿齊所有鑰匙 | (r, c, 已持有鑰匙集合) | m · n · 2^K | 走到鄰格；撿鑰匙就更新集合，鎖要有鑰匙才能過 |

**先估狀態數，再決定做法**。BFS 的時間是 O(狀態數 × 每個狀態的鄰居數)。847 的 n ≤ 12，狀態 12 × 4096 ≈ 5 × 10⁴，輕鬆；864 的格子 30 × 30、鑰匙 K ≤ 6，狀態 900 × 64 ≈ 5.8 × 10⁴，也沒問題；1293 的格子 40 × 40、k ≤ 1600，表面上是 1600 × 1601 ≈ 2.6 × 10⁶，但 k ≥ m + n − 3 時可以直接回傳曼哈頓距離，所以真正需要搜尋時 k < 77，狀態不超過 1600 × 77 ≈ 1.2 × 10⁵，再加上「支配剪枝」還會更少。面試時把這個乘法講出來，面試官就知道你的解在限制內。

**支配（dominance）剪枝**。有些狀態維度是「越多越好」：在 1293 中，同一格、同樣步數下，剩 3 次消除的狀態可以做到所有剩 2 次能做到的事。BFS 按步數遞增處理，所以較早記錄的狀態步數一定不比現在多；只要新狀態的剩餘次數沒有超過這一格已記錄的最大值，它就被支配，可以直接丟掉。這把 visited 從 `(r, c, rem)` 的三維集合縮成每格一個整數 `best[r][c]`。注意 bitmask 型的狀態（鑰匙集合）通常沒有全序：拿著 {a} 和拿著 {b} 互不支配，不能這樣剪。

**Bidirectional BFS（雙向 BFS）**。如果起點和終點都已知、而且每個節點的鄰居很多（Word Ladder 每個字有 25 × L 個候選），從兩端同時往中間搜通常快很多：單向 BFS 要擴展到深度 d，大約碰到 b^d 個節點；雙向各擴展到 d/2，總共約 2 · b^(d/2)。實作的重點是**每輪擴展比較小的那一邊**，以及兩邊相遇的判斷要在產生鄰居時就做。難題 1 會完整實作。

```text
狀態圖的直覺（1293，k = 1）：同一格可以是不同的節點

           (r=1, c=1, rem=1)        還能再打穿一道牆
格子 (1,1) <
           (r=1, c=1, rem=0)        已經用完

兩者「未來能走的路」不同 → 必須當成兩個節點分開 visited
但 rem=1 支配 rem=0 → 若 rem=1 已經更早到過，rem=0 再來就可以丟掉
```

## 15.6 BFS 還是 DFS：怎麼選

兩者時間都是 O(V + E)，選擇的依據是題目要什麼，以及實作上的風險。

| 情況 | 選擇 | 理由 |
|---|---|---|
| 等權圖的最少步數 | BFS | 只有 BFS 保證第一次看到就是最短；DFS 找到的路徑不一定最短 |
| 連通元件、整塊標記、可達性 | 都可以，迭代 DFS 程式最短 | 只關心「誰被拜訪」，順序不重要 |
| 需要在「離開節點時」做事（後序） | 遞迴 DFS | 例如 clone 後回傳、樹形 DP、環偵測與拓撲排序（第 16 章） |
| 列舉所有路徑或所有解 | DFS + backtracking（第 19 章） | 需要沿路維護當前路徑，回溯時復原 |
| 列舉所有最短路徑 | BFS 建分層 DAG，再 DFS 回溯 | 難題 2（126）：先用 BFS 確定距離，才不會列舉到非最短路徑 |
| 圖很深（一條長鏈、蛇形格子） | BFS 或迭代 DFS | 遞迴 DFS 會超過 Python 的遞迴上限 |
| 圖很寬、記憶體有限 | DFS | BFS 的 queue 可能裝下一整層（例如完全二元樹的最底層有 V/2 個點） |

最後一點的記憶體差異在面試中偶爾會被問到：BFS 的額外空間是「最寬的一層」，DFS 是「最深的一條路徑」。在格子上兩者最差都是 O(mn)，但形狀不同的圖會有很大差別。

## 15.7 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 出隊時才標記 visited | 同一點被重複加入 queue，格子題超時或記憶體暴增 | 一律在 `append` 的同一處標記 |
| 用 `list.pop(0)` 當 queue | 大格子超時，整體退化成 O(V²) | 用 `collections.deque` 的 `popleft()` |
| 格子題遞迴 DFS 沒注意深度 | 300 × 300 的全陸地格子觸發 RecursionError | 改用迭代 stack，或說明需要調高遞迴上限 |
| 邊界檢查順序錯 | `grid[nr][nc]` 在檢查範圍前就讀取，負索引在 Python 不報錯卻讀到另一邊 | 先寫 `0 <= nr < m and 0 <= nc < n`，再讀格子 |
| 狀態圖只用位置當 visited | 1293、864 回傳 -1 或偏大的答案，因為較差的狀態先佔住了格子 | 先問「兩次到同一格，未來能做的事一樣嗎」，不一樣就把資訊放進狀態 |
| 有權重的圖仍用 BFS | 答案偏大：邊數最少的路徑不一定總權重最小 | 權重全 1 用 BFS，只有 0／1 用 0-1 BFS，其他用 Dijkstra（第 18 章） |
| multi-source 寫成每個源頭各跑一次 | 正確但 O(源頭數 × mn)，大格子超時 | 所有源頭一起放進第 0 層 |
| 逐層 BFS 的層數多算或少算一 | 994 在最後一層之後多加一分鐘 | 用「還有新鮮橘子」當迴圈條件，或在回傳前想清楚層數的意義 |
| 修改輸入卻沒告知 | 呼叫端之後再用這個 grid 時資料已被改掉 | 面試時說明「我會把走過的格子改掉以省空間」，或另開 visited |
| 有向圖當成無向圖建邊 | 可達性多算 | 建圖時確認方向；417 這類題反向搜時，邊的方向也要跟著反 |

## 核心題 1｜200. Number of Islands｜Medium

### 題目

給一個 m × n 的二維格子 `grid`，每格是字元 `'1'`（陸地）或 `'0'`（水）。上下左右相鄰的陸地屬於同一座島，**對角線不算相鄰**；格子外圍全部視為水。請回傳島嶼的數量。限制：`1 <= m, n <= 300`。

- 範例 1：
  ```
  1 1 1 1 0
  1 1 0 1 0
  1 1 0 0 0
  0 0 0 0 0
  ```
  回傳 `1`，所有陸地都連在一起。
- 範例 2：
  ```
  1 1 0 0 0
  1 1 0 0 0
  0 0 1 0 0
  0 0 0 1 1
  ```
  回傳 `3`：左上 2 × 2 一塊、中間單獨一格、右下兩格一塊。
- 範例 3（邊界）：`[["1","0","1"],["0","1","0"],["1","0","1"]]` 回傳 `5`，五塊陸地只靠對角線相鄰，彼此都不相連。
- 範例 4（邊界）：`[["0"]]` 回傳 `0`；`[["1"]]` 回傳 `1`。

### 思路

最直覺的暴力想法是「對每一對陸地判斷它們連不連通」，再把連通的歸成一組；判斷一對要做一次搜尋 O(mn)，陸地對數是 O((mn)²)，總共 O((mn)³)，300 × 300 的格子完全不可行。瓶頸在於同一座島被反覆搜尋了很多次，而我們其實只需要知道「每座島」一次。

關鍵觀察：島嶼就是圖上的**連通元件**。把每塊陸地當節點、上下左右相鄰的陸地之間連邊，問題就是「這張圖有幾個連通元件」。標準做法是從左上到右下掃描每一格，遇到一塊**還沒被拜訪過的陸地**，就代表發現一座新島，計數加一，然後用 DFS 或 BFS 把這座島上所有陸地都標記為已拜訪（俗稱「淹掉」整座島）。之後掃描再遇到這座島的其他格子時，它們已被標記，不會重複計數。

正確性的 invariant 是：**掃描到 (r, c) 之前，所有被標記的格子恰好構成「已經計數過的島」的聯集**。發現新陸地時，它沒被標記，代表它不屬於任何已計數的島，所以一定是新島；接著的搜尋會把它所在的整個連通元件標記完，invariant 繼續成立。每格最多被標記一次、每次標記檢查 4 個鄰居，所以總時間 O(mn)。

標記的方式有兩種：另開一個 `seen` 陣列，或直接把走過的 `'1'` 改成 `'0'`。後者省下 O(mn) 的額外空間，但會修改輸入；面試時要說明你的選擇，若面試官要求不能修改輸入，就用 `seen`。搜尋本身用迭代 DFS（stack）或 BFS（queue）都可以，因為這題只在乎誰被拜訪，不在乎順序；但**不要用遞迴 DFS 走 300 × 300 的格子**，全陸地時遞迴深度可以接近 9 × 10⁴，會超過 Python 的遞迴上限。

```text
範例 2，逐格掃描（* 表示已被標記）

起始                (0,0) 是新陸地 → 島數 1   (2,2) 是新陸地 → 島數 2   (3,3) 是新陸地 → 島數 3
1 1 0 0 0           * * 0 0 0                * * 0 0 0                * * 0 0 0
1 1 0 0 0           * * 0 0 0                * * 0 0 0                * * 0 0 0
0 0 1 0 0    →      0 0 1 0 0         →      0 0 * 0 0         →      0 0 * 0 0
0 0 0 1 1           0 0 0 1 1                0 0 0 1 1                0 0 0 * *

(0,0) 出發的 DFS：stack [(0,0)] → 彈出 (0,0)，推入 (1,0)、(0,1)
                → 彈出 (0,1)，推入 (1,1) → 彈出 (1,1) → 彈出 (1,0)，鄰居都已標記
掃描繼續：(0,1)、(1,0)、(1,1) 都已標記，跳過；直到 (2,2) 才遇到新的陸地。
(3,3) 出發時順便標記 (3,4)，所以掃到 (3,4) 時不會再加一。
```

這個過程也說明了為什麼「掃描順序」不影響答案：不論從哪一格先發現一座島，搜尋都會把整座島標記完，計數只在每座島第一次被碰到時加一。

### 解法

```python
import random
from collections import deque

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def num_islands(grid: list[list[str]]) -> int:
    """迭代式 DFS，不修改輸入。"""
    if not grid or not grid[0]:
        return 0
    m, n = len(grid), len(grid[0])
    seen = [[False] * n for _ in range(m)]
    count = 0
    for r in range(m):
        for c in range(n):
            if grid[r][c] != "1" or seen[r][c]:
                continue
            count += 1                       # 遇到一塊新的陸地：島嶼數 +1
            seen[r][c] = True
            stack = [(r, c)]
            while stack:                     # 把整座島淹掉（標記成已看過）
                x, y = stack.pop()
                for dx, dy in DIRS:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < m and 0 <= ny < n and grid[nx][ny] == "1" and not seen[nx][ny]:
                        seen[nx][ny] = True
                        stack.append((nx, ny))
    return count


def num_islands_bfs(grid: list[list[str]]) -> int:
    """BFS 版本：直接把走過的陸地改成 '0'（會修改輸入）。"""
    if not grid or not grid[0]:
        return 0
    m, n = len(grid), len(grid[0])
    count = 0
    for r in range(m):
        for c in range(n):
            if grid[r][c] != "1":
                continue
            count += 1
            grid[r][c] = "0"
            queue = deque([(r, c)])
            while queue:
                x, y = queue.popleft()
                for dx, dy in DIRS:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < m and 0 <= ny < n and grid[nx][ny] == "1":
                        grid[nx][ny] = "0"
                        queue.append((nx, ny))
    return count


def num_islands_uf(grid: list[list[str]]) -> int:
    """Union-Find 對照版。"""
    m, n = len(grid), len(grid[0])
    parent = list(range(m * n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    land = 0
    for r in range(m):
        for c in range(n):
            if grid[r][c] == "1":
                land += 1
                for nr, nc in ((r + 1, c), (r, c + 1)):
                    if nr < m and nc < n and grid[nr][nc] == "1":
                        a, b = find(r * n + c), find(nr * n + nc)
                        if a != b:
                            parent[a] = b
                            land -= 1
    return land


g1 = [list("11110"), list("11010"), list("11000"), list("00000")]
g2 = [list("11000"), list("11000"), list("00100"), list("00011")]
assert num_islands(g1) == 1
assert num_islands(g2) == 3
assert num_islands([list("0")]) == 0
assert num_islands([list("1")]) == 1
assert num_islands([list("101"), list("010"), list("101")]) == 5   # 對角線不算相連
assert num_islands([]) == 0
for _ in range(300):
    m, n = random.randint(1, 7), random.randint(1, 7)
    g = [[random.choice("01") for _ in range(n)] for _ in range(m)]
    expect = num_islands_uf(g)
    assert num_islands(g) == expect
    assert num_islands_bfs([row[:] for row in g]) == expect
print("all tests passed")
```

### 複雜度與邊界

時間 O(mn)：外層掃描每格一次，每格最多被標記、入棧一次，每次檢查 4 個鄰居。空間：`seen` 版本 O(mn)；原地修改版本省掉 `seen`，但 stack 或 queue 本身最差仍是 O(mn)（DFS 的 stack 在全陸地時可以同時裝下很大比例的格子；BFS 的 queue 只裝目前的前緣，在全陸地的格子上大約是 O(m + n)，但有牆的形狀下不保證，仍以 O(mn) 為上界）。邊界情況：全水回傳 0；全陸地回傳 1；只有一列或一行時退化成數連續的 `'1'` 段；只靠對角線相鄰的陸地各自成島。注意 LeetCode 給的是字元 `'1'` 而不是整數 1，比較時寫錯型別會讓答案永遠是 0。

### Follow-up

> [!question]- F1. 如果要回傳最大那座島的面積呢（695. Max Area of Island）？
> 同一個掃描框架，只是在每次「淹島」的搜尋中多數一個計數器：每從 stack 彈出一格就加一，搜尋結束時這座島的面積就確定了，和目前最大值比較即可。時間仍是 O(mn)、空間 O(mn)。如果要的是「最多把一格水改成陸地後的最大面積」（827. Making A Large Island），就先用一次掃描替每座島編號並記錄面積，再對每格水看它四個鄰居屬於哪些**不同**的島（用 set 去重），面積相加再加一，同樣 O(mn)。

> [!question]- F2. 如果陸地是一格一格加進來的，每加一格就要回報目前的島數呢（305. Number of Islands II）？
> 每次重跑一次 DFS 是 O(mn)，k 次操作共 O(k · mn)，太慢。改用 union-find（第 17 章）：新增一格陸地時島數先加一，再檢查四個鄰居，若鄰居也是陸地且屬於不同集合就 union，並把島數減一。每次操作是 O(α(mn))，近乎常數，總共 O(mn + k)。要注意同一格被重複加入時不能再加一。這題是「離線用 DFS、線上用 union-find」的典型例子：DFS 擅長一次性整體計算，union-find 擅長只加不減的增量合併。

> [!question]- F3. 如果要數「形狀不同」的島有幾種（694. Number of Distinct Islands）？
> 每次淹島時，把島上每一格的座標減去起點座標，得到相對位置的序列；因為掃描順序固定（由上到下、由左到右）而且搜尋順序也固定，相同形狀的島一定產生相同的序列。把序列轉成 tuple 放進 set，最後 set 的大小就是答案，時間 O(mn)。另一種常見寫法是記錄 DFS 的「方向路徑」，但必須在**回溯時也記錄一個符號**，否則不同形狀可能產生相同的方向字串。若旋轉、鏡射後相同也算同一種（711），就要對每座島產生 8 種變換後的座標，各自正規化（平移到最小座標為原點並排序），取字典序最小的當代表。

> [!question]- F4. 如果格子大到放不進記憶體，只能一列一列串流讀入呢？
> 只保留「上一列」和「目前這一列」，在這兩列的格子上做 union-find。每讀入一列，先把同列相鄰的陸地 union，再和上一列對應位置的陸地 union。關鍵是判斷一座島什麼時候「結束」：當上一列某個集合在目前這一列沒有任何格子延續，這座島就不會再長大，可以計數並丟棄。做法是處理完新的一列後，檢查上一列每個集合的代表是否出現在新列中。記憶體 O(n)，時間 O(mn · α(n))。這題考的是你能不能把全域的連通性拆成局部的增量合併。

> [!question]- F5. 如果對角線也算相鄰呢？
> 把方向陣列從 4 個擴充成 8 個（加上 `(±1, ±1)`），其餘完全不變，時間仍是 O(mn)，只是常數變成兩倍。用 union-find 的版本則要多檢查右下與左下兩個方向（右、下、右下、左下四個「往前」的鄰居就足夠涵蓋所有對）。面試官問這題通常是想確認你的程式有把「相鄰的定義」抽象成方向陣列，而不是把四個方向寫死在四段 if 裡。

## 核心題 2｜133. Clone Graph｜Medium

### 題目

給一張**連通的無向圖**中的某個節點 `node`，請回傳這張圖的**深複製**（deep copy）。每個節點有一個整數 `val` 和一個鄰居串列 `neighbors: list[Node]`。複製後的圖要和原圖結構完全相同，但不能共用任何一個節點物件。節點的 `val` 從 1 到 n 互不相同，`0 <= n <= 100`；圖中沒有自環也沒有重複邊；如果輸入是 `None`（空圖），回傳 `None`。

- 範例 1：四個節點組成一個環，`1 – 2 – 3 – 4 – 1`。用鄰接串列表示為 `[[2, 4], [1, 3], [2, 4], [1, 3]]`（第 i 項是節點 i + 1 的鄰居）。回傳複製後的節點 1，從它出發走出來的結構應該仍是 `[[2, 4], [1, 3], [2, 4], [1, 3]]`。
- 範例 2（邊界）：`[[]]`，只有一個節點、沒有鄰居，回傳一個新的節點 1。
- 範例 3（邊界）：`[]`，空圖，回傳 `None`。

### 思路

最天真的寫法是遞迴：複製節點 u，然後對每個鄰居遞迴複製，把結果接到 u 的副本上。問題立刻出現：圖有環，1 的鄰居是 2，2 的鄰居又有 1，遞迴會在 1 和 2 之間無限來回；就算沒有環，同一個節點被多個鄰居指到時（例如 1 和 3 都連到 2、4），它會被複製好幾次，結果的結構和原圖不一樣。所以真正的需求是：**每個原節點恰好對應一個副本，而且要能隨時查到它的副本**。

這正是 visited 的角色，只是要升級成 hash map：`copies[原節點] = 副本`。走訪時遇到一個鄰居，先查 map：已經有副本就直接用它，沒有就建立副本、登記進 map、排進待處理。這個 map 一次解決了兩個問題：它防止無限迴圈（等同 visited），也保證共用的節點只被複製一次（等同 memoization）。

用 BFS 時，流程是：建立起點的副本並入隊；每次取出一個原節點 `cur`，對它的每個鄰居 `nb`，若 `nb` 沒有副本就建立並入隊，然後把 `copies[nb]` 加到 `copies[cur].neighbors`。每條無向邊會在兩個端點各處理一次，剛好對應副本中兩個方向的鄰居關係。用遞迴 DFS 也可以，但要注意**先登記再遞迴**：建立副本後立刻放進 map，再去複製鄰居，否則遇到環時會因為 map 裡還沒有自己而無限遞迴。

```text
範例 1：1 – 2 – 3 – 4 – 1，BFS 從 1 開始（[] 表示副本的鄰居串列）

步驟  出隊  處理鄰居                       copies 新增    副本的鄰居
 0     -    建立 1'，入隊 1                 1→1'          1':[]
 1     1    鄰居 2：無副本 → 建 2'、入隊     2→2'          1':[2']
            鄰居 4：無副本 → 建 4'、入隊     4→4'          1':[2', 4']
 2     2    鄰居 1：已有 1'                                2':[1']
            鄰居 3：無副本 → 建 3'、入隊     3→3'          2':[1', 3']
 3     4    鄰居 1：已有；鄰居 3：已有                     4':[1', 3']
 4     3    鄰居 2：已有；鄰居 4：已有                     3':[2', 4']
結束：每個原節點恰好一個副本，副本之間的邊和原圖一一對應
```

注意步驟 3 和 4：節點 3 在步驟 2 就被建立了副本，所以處理 4 的鄰居 3 時直接拿到 `3'`，而不是再建一個。如果沒有這個 map，`3'` 會被建立兩次，`2'` 和 `4'` 會各自指向不同的 3，結構就錯了。

### 解法

```python
from collections import deque


class Node:
    def __init__(self, val: int = 0, neighbors: list["Node"] | None = None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []


def clone_graph(node: Node | None) -> Node | None:
    if node is None:
        return None
    copies = {node: Node(node.val)}          # 原節點 → 複製節點；同時當作 visited
    queue = deque([node])
    while queue:
        cur = queue.popleft()
        for nb in cur.neighbors:
            if nb not in copies:             # 第一次看到：建立複製並排入 queue
                copies[nb] = Node(nb.val)
                queue.append(nb)
            copies[cur].neighbors.append(copies[nb])   # 接上複製版的邊
    return copies[node]


def clone_graph_dfs(node: Node | None) -> Node | None:
    copies: dict[Node, Node] = {}

    def dfs(u: Node) -> Node:
        if u in copies:
            return copies[u]
        copy = Node(u.val)
        copies[u] = copy                     # 先登記再遞迴，遇到環才不會無限遞迴
        copy.neighbors = [dfs(v) for v in u.neighbors]
        return copy

    return dfs(node) if node else None


def build(adj: list[list[int]]) -> Node | None:
    """adj[i] 是節點 i+1 的鄰居（1-indexed），回傳節點 1。"""
    if not adj:
        return None
    nodes = [Node(i + 1) for i in range(len(adj))]
    for i, nbs in enumerate(adj):
        nodes[i].neighbors = [nodes[j - 1] for j in nbs]
    return nodes[0]


def collect(node: Node | None) -> dict[int, Node]:
    out, stack = {}, [node] if node else []
    while stack:
        u = stack.pop()
        if u.val in out:
            continue
        out[u.val] = u
        stack.extend(u.neighbors)
    return out


def to_adj(node: Node | None) -> list[list[int]]:
    nodes = collect(node)
    return [[v.val for v in nodes[i].neighbors] for i in sorted(nodes)]


for fn in (clone_graph, clone_graph_dfs):
    for adj in ([[2, 4], [1, 3], [2, 4], [1, 3]], [[]], [], [[2], [1]]):
        orig = build(adj)
        copy = fn(orig)
        assert to_adj(copy) == adj
        if orig:
            a, b = collect(orig), collect(copy)
            assert all(a[k] is not b[k] for k in a)          # 沒有任何節點被共用
print("all tests passed")
```

測試除了檢查結構相同，還用 `is not` 確認每個副本都是新物件；只比較 `val` 的測試抓不到「直接回傳原節點」這種錯誤。

### 複雜度與邊界

時間 O(V + E)：每個節點建立一次副本、入隊一次；每條無向邊在兩端各被看一次。空間 O(V)：map 有 V 個項目，queue 最多 V 個（不計輸出本身的 O(V + E)）。邊界情況：`None` 輸入直接回傳 `None`；單一節點沒有鄰居時，迴圈不做任何事，回傳新的單節點；兩個節點互為鄰居時，環的處理靠 map。遞迴版本在 n ≤ 100 時沒有深度問題，但如果 n 到 10⁵ 且圖是一條長鏈，就要改用 BFS 或迭代 DFS。用節點物件本身當 map 的 key 依賴 Python 物件預設以 identity 雜湊；若題目保證 `val` 唯一，也可以用 `val` 當 key，改成一個長度 n + 1 的陣列。

### Follow-up

> [!question]- F1. 如果圖不連通，輸入給的是所有節點的串列呢？
> 對串列中每個節點，若它還沒有副本，就以它為起點跑一次同樣的 BFS，所有起點共用同一個 `copies` map。最後依原串列的順序回傳 `[copies[u] for u in nodes]`。時間仍是 O(V + E)，因為共用 map 保證每個節點只被處理一次。這和核心題 1 的「掃描每格、遇到沒拜訪的就出發」是同一個外層迴圈結構。

> [!question]- F2. 如果是有向圖，或節點還有一個指向任意節點的 random 指標呢（138. Copy List with Random Pointer）？
> 有向圖完全不需要改：程式本來就只沿著 `neighbors` 的方向走，每條有向邊被處理一次。若起點不能到達所有節點，就和 F1 一樣需要所有節點的串列。random 指標只是多一種邊，在處理鄰居時一併處理 `random` 即可，同樣用 map 查副本。138 題的 linked list 版本還有 O(1) 額外空間的解法（把副本插在原節點後面、利用 `next` 找到副本，再拆開兩條串列），但那依賴 linked list 每個節點只有一個 `next` 的結構，一般圖做不到，第 11 章難題 3 會詳細說明。

> [!question]- F3. 如果要把圖序列化成字串、再從字串還原（例如透過網路傳送）呢？
> 序列化時先用 BFS 給每個節點一個從 0 開始的新編號（第一次看到的順序），然後輸出每個節點的 `val` 與鄰居的編號串列，例如 `"1:1,3|2:0,2|..."`；用編號而不是 `val` 才能處理 `val` 重複的情況。反序列化時先建出所有節點，再依編號接上鄰居，兩者都是 O(V + E)。這題的重點是：**物件的身分（identity）不能被序列化，必須換成穩定的編號**，map 就是在做這件事。

> [!question]- F4. 如果節點數很大，遞迴版本會怎樣？要怎麼改？
> 遞迴 DFS 的深度等於 DFS 樹的最長路徑，在一條 10⁵ 個節點的長鏈上會超過 Python 預設約 1000 層的遞迴上限而拋出 RecursionError。改成 BFS（上面的主解法）或用顯式 stack 的迭代 DFS 即可；迭代版的寫法是：建立副本並入棧，彈出時把每個鄰居的副本接上，沒有副本的鄰居先建立再入棧，和 BFS 只差在 `pop()` 與 `popleft()`。調高 `sys.setrecursionlimit` 也能暫時解決，但 CPython 的 C stack 仍可能溢位，不是可靠的做法。

> [!question]- F5. 如果要判斷兩張圖（各給一個起點）的結構是否完全相同呢？
> 從兩個起點同時做 BFS，維護一個「左圖節點 → 右圖節點」的對應 map。每次取出一對 (u, u')，先比較 `val` 與鄰居數，再按順序把鄰居配對：若左鄰居已有對應，就檢查它是否正好對應到右鄰居；若沒有，就建立對應並入隊。任何不一致立刻回傳 False。這是在「鄰居順序也要相同」的前提下 O(V + E)；如果鄰居順序可以不同，就變成圖同構（graph isomorphism）問題，目前沒有已知的多項式時間演算法，面試中說明這個區別即可。

## 核心題 3｜994. Rotting Oranges｜Medium

### 題目

給一個 m × n 的格子 `grid`，每格是 0（空格）、1（新鮮橘子）或 2（腐爛橘子）。每過一分鐘，所有腐爛橘子會讓上下左右相鄰的新鮮橘子變成腐爛；空格不會傳染，也擋住傳染。請回傳讓所有新鮮橘子都腐爛所需的最少分鐘數；如果有新鮮橘子永遠不會腐爛，回傳 -1。限制：`1 <= m, n <= 10`。

- 範例 1：`[[2, 1, 1], [1, 1, 0], [0, 1, 1]]` 回傳 `4`。
- 範例 2：`[[2, 1, 1], [0, 1, 1], [1, 0, 1]]` 回傳 `-1`，左下角的橘子被空格隔開，永遠不會被傳染。
- 範例 3（邊界）：`[[0, 2]]` 回傳 `0`，一開始就沒有新鮮橘子，不需要任何時間。
- 範例 4（邊界）：`[[1]]` 回傳 `-1`，有新鮮橘子但沒有任何腐爛源。
- 範例 5：`[[2, 1, 1, 1, 2]]` 回傳 `2`，兩端同時往中間傳染。

### 思路

暴力解就是照題目模擬：每一分鐘掃描整個格子，找出所有「旁邊有腐爛橘子」的新鮮橘子，把它們一起變爛（要先收集再一起改，否則同一分鐘內會連鎖傳染），直到某一分鐘沒有任何變化。每分鐘 O(mn)，最多要跑 O(mn) 分鐘（例如一條蛇形的長鏈），總共 O((mn)²)。這題 m, n ≤ 10 其實也能過，但同樣的題型在 542 01 Matrix 等題目中 mn 可以到 10⁴ 以上，模擬就不行了。瓶頸是：每一分鐘都重新掃描那些早就爛掉、或還離得很遠的橘子。

關鍵觀察：一顆橘子腐爛的時間，等於它到**最近的**初始腐爛橘子的最短距離（只能經過有橘子的格子）。因為傳染每分鐘走一步、所有源頭同時進行，最先抵達某顆橘子的就是距離最近的那個源頭。所以答案是「所有新鮮橘子到最近源頭距離的最大值」，而這正是 15.4 節的 multi-source BFS：把所有初始腐爛橘子同時放進第 0 層，BFS 第 d 層的橘子就是第 d 分鐘腐爛的。

實作上用逐層 BFS 最自然：每處理完一層就是過了一分鐘。同時維護一個 `fresh` 計數，每傳染一顆就減一；迴圈條件寫成 `while queue and fresh`，這樣最後一顆新鮮橘子腐爛後立刻停止，不會因為最後一層還在 queue 裡而多算一分鐘。結束後若 `fresh > 0`，代表有橘子不可達，回傳 -1。

```text
範例 1，逐層 BFS（每層 = 一分鐘）

第 0 分鐘        第 1 分鐘        第 2 分鐘        第 3 分鐘        第 4 分鐘
2 1 1            2 2 1            2 2 2            2 2 2            2 2 2
1 1 0     →      2 1 0     →      2 2 0     →      2 2 0     →      2 2 0
0 1 1            0 1 1            0 1 1            0 2 1            0 2 2

queue（層）:
第 0 層 [(0,0)]                         fresh = 6
第 1 層 [(1,0), (0,1)]                  fresh = 4
第 2 層 [(1,1), (0,2)]                  fresh = 2    (1,1) 被 (1,0) 先傳染，(0,1) 再看到時已是 2
第 3 層 [(2,1)]                         fresh = 1
第 4 層 [(2,2)]                         fresh = 0 → 迴圈結束，回傳 4
```

第 2 層的 (1,1) 同時是 (1,0) 和 (0,1) 的鄰居，BFS 先處理到誰就由誰傳染，另一個再看到時它已經是 2，不會重複入隊。這就是「入隊時標記」在這題的具體樣子：把 1 改成 2 本身就是標記。

### 解法

```python
import random
from collections import deque


def oranges_rotting(grid: list[list[int]]) -> int:
    m, n = len(grid), len(grid[0])
    queue = deque()
    fresh = 0
    for r in range(m):
        for c in range(n):
            if grid[r][c] == 2:
                queue.append((r, c))
            elif grid[r][c] == 1:
                fresh += 1
    minutes = 0
    while queue and fresh:                       # fresh 為 0 就不必再擴散
        minutes += 1
        for _ in range(len(queue)):              # 這一分鐘會傳染出去的只有目前這一層
            r, c = queue.popleft()
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if 0 <= nr < m and 0 <= nc < n and grid[nr][nc] == 1:
                    grid[nr][nc] = 2
                    fresh -= 1
                    queue.append((nr, nc))
    return minutes if fresh == 0 else -1


def simulate(grid: list[list[int]]) -> int:
    """逐分鐘模擬的暴力解，用來對照。"""
    g = [row[:] for row in grid]
    m, n = len(g), len(g[0])
    t = 0
    while True:
        rot = [(r, c) for r in range(m) for c in range(n) if g[r][c] == 1 and any(
            0 <= r + dr < m and 0 <= c + dc < n and g[r + dr][c + dc] == 2
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
        if not rot:
            break
        for r, c in rot:
            g[r][c] = 2
        t += 1
    return -1 if any(1 in row for row in g) else t


assert oranges_rotting([[2, 1, 1], [1, 1, 0], [0, 1, 1]]) == 4
assert oranges_rotting([[2, 1, 1], [0, 1, 1], [1, 0, 1]]) == -1
assert oranges_rotting([[0, 2]]) == 0                  # 沒有新鮮橘子
assert oranges_rotting([[0]]) == 0
assert oranges_rotting([[1]]) == -1                    # 有新鮮橘子但沒有腐爛源
assert oranges_rotting([[2, 1, 1, 1, 2]]) == 2         # 兩個源頭同時擴散
for _ in range(300):
    m, n = random.randint(1, 6), random.randint(1, 6)
    g = [[random.choice((0, 1, 1, 2)) for _ in range(n)] for _ in range(m)]
    assert oranges_rotting([row[:] for row in g]) == simulate(g)
print("all tests passed")
```

### 複雜度與邊界

時間 O(mn)：每顆橘子最多入隊一次，每次檢查 4 個鄰居；初始掃描也是 O(mn)。空間 O(mn)，queue 最多裝下所有橘子。邊界情況：沒有新鮮橘子時迴圈一次都不跑，回傳 0（即使也沒有腐爛橘子）；有新鮮橘子但沒有腐爛源時 queue 一開始就空，回傳 -1；被空格完全隔開的新鮮橘子會讓 `fresh` 停在正數。常見的 off-by-one：若迴圈條件只寫 `while queue`，最後一層腐爛的橘子還會被取出處理一輪，`minutes` 會多一，需要在結尾減一並特判「本來就沒有新鮮橘子」；用 `while queue and fresh` 可以一次避開這兩個陷阱。這個解法會修改輸入，若不允許，就另開 `dist` 陣列。

### Follow-up

> [!question]- F1. 如果要回傳每一格橘子腐爛的時間（或每格到最近腐爛橘子的距離）呢？
> 改用 15.4 節的 `dist` 寫法：所有源頭 `dist = 0`，其餘 -1，BFS 時 `dist[nr][nc] = dist[r][c] + 1`。這就是 542 01 Matrix（每格到最近的 0 的距離）與 286 Walls and Gates（每個空房間到最近的門的距離），時間空間都是 O(mn)。如果距離改成曼哈頓距離而且沒有障礙物，還可以用兩次 DP 掃描（左上到右下、右下到左上）做到 O(mn) 且不用 queue，但有障礙物時只能用 BFS。

> [!question]- F2. 如果某些格子的橘子比較「硬」，需要被傳染 2 分鐘才會爛呢？
> 這時每條邊的代價不再相同，第一次被看到不一定是最早腐爛的時間，BFS 失效。把它看成加權最短路：走進一般格子代價 1、走進硬格子代價 2，用 Dijkstra（第 18 章）從所有源頭同時出發，答案是所有橘子最短時間的最大值，O(mn log(mn))。如果代價只有 1 和 2 這種小整數，也可以把硬格子拆成兩個節點（中間多一個虛擬點），讓所有邊代價變回 1，再用普通 BFS，O(mn)。若有些傳染是瞬間發生（代價 0），就用 0-1 BFS：代價 0 的鄰居放到 deque 前端、代價 1 的放到尾端。

> [!question]- F3. 如果格子是 10⁹ × 10⁹ 但只有 10⁵ 顆橘子（稀疏）呢？
> 不能開二維陣列。把橘子的座標放進 hash map（座標 → 狀態），BFS 時鄰居用座標加減算出，只有在 map 中且是新鮮橘子才入隊。時間與空間都變成 O(橘子數)，和格子大小無關。這是「隱式圖」的典型用法：圖的節點只有實際存在的東西，邊靠規則即時產生。

> [!question]- F4. 如果可以額外指定一顆新鮮橘子變爛，要讓總時間最短，該選哪一顆？
> 最直接的做法是對每顆新鮮橘子 c，把它加入源頭後重跑一次 multi-source BFS，取最小值，O(橘子數 × mn)，在這題的限制下完全可行。面試時可以再提一個觀察：只有在「原本最晚腐爛的那些橘子」附近放新源頭才可能改善答案，以及若有橘子原本不可達，新源頭必須放在那個孤立區域裡（若有多個孤立區域，一顆不夠，直接回傳 -1）。一般化的「放 k 個源頭讓最大距離最小」是 k-center 問題，屬於 NP-hard，所以不要宣稱有多項式時間的最佳解。

## 核心題 4｜417. Pacific Atlantic Water Flow｜Medium

### 題目

給一個 m × n 的整數矩陣 `heights`，代表一座島上每格的海拔。島的**上邊與左邊**臨太平洋，**下邊與右邊**臨大西洋。下雨時水可以從一格流到上下左右相鄰、海拔**小於或等於**它的格子；邊界上的格子可以直接流進它所鄰接的海洋。請回傳所有「水能同時流進兩個海洋」的格子座標 `[r, c]`（順序不限，這裡統一排序後回傳）。限制：`1 <= m, n <= 200`，`0 <= heights[r][c] <= 10⁵`。

- 範例 1：
  ```
  1 2 2 3 5
  3 2 3 4 4
  2 4 5 3 1
  6 7 1 4 5
  5 1 1 2 4
  ```
  回傳 `[[0,4],[1,3],[1,4],[2,2],[3,0],[3,1],[4,0]]`。例如 (2,2) 的海拔 5：往上 3 → 2 → 2 可以流到上邊（太平洋），往右 3 → 1 可以流到右邊（大西洋）。
- 範例 2（邊界）：`[[7]]` 回傳 `[[0,0]]`，唯一的格子同時在四個邊上。
- 範例 3（邊界）：只有一列 `[[1, 2, 3]]`，每格都同時在上邊與下邊，所以全部都是答案。

### 思路

直覺做法是對每一格做一次搜尋，沿著「不升高」的方向走，看能不能碰到兩個海洋的邊界。每次搜尋 O(mn)，共 mn 格，總共 O((mn)²)，200 × 200 時是 1.6 × 10⁹，太慢。想用 memoization 記住「這格能不能到太平洋」也會遇到麻煩：海拔相同的相鄰格子之間可以雙向流動，圖中有環，遞迴到一半時鄰居的答案還沒算出來，不能直接引用（見 F4）。

關鍵觀察是**把方向反過來**。「水從格子 X 流得到太平洋」等價於「從太平洋沿岸的某一格，逆著水流方向走得到 X」，而逆著水流的規則是「只能走到海拔**大於或等於**自己的鄰居」。太平洋沿岸就是上邊與左邊所有格子，把它們全部當作源頭做一次 multi-source 搜尋，就能一次得到所有能流進太平洋的格子集合 P；同理從下邊與右邊出發得到集合 A。答案就是 P ∩ A。兩次搜尋各 O(mn)，總共 O(mn)。

這個轉換之所以成立，是因為「可達性」在反轉所有邊之後恰好反過來：原圖中 X 能走到 Y，當且僅當反向圖中 Y 能走到 X。原問題是「很多起點、固定的終點集合（海岸）」，反過來就變成「固定的起點集合、問能到哪些點」，這正是 multi-source 搜尋最擅長的形狀。要特別小心的是比較方向：原本是「流向 ≤ 自己的鄰居」，反向後是「爬向 ≥ 自己的鄰居」，寫成 `>` 會漏掉海拔相同的平地。

```text
範例 1，P = 從太平洋逆流可達，A = 從大西洋逆流可達，B = 兩者皆可

heights              逆流搜尋結果
1 2 2 3 5            P P P P B
3 2 3 4 4            P P P B B
2 4 5 3 1    →       P P B A A
6 7 1 4 5            B B A A A
5 1 1 2 4            B A A A A

以 (2,2)=5 為例：
太平洋側：(0,2)=2 → (1,2)=3 → (2,2)=5   每步海拔不降，逆流可達 → 屬於 P
大西洋側：(2,4)=1 → (2,3)=3 → (2,2)=5   每步海拔不降，逆流可達 → 屬於 A
(3,2)=1 被四周的高地包住，只能從大西洋側的 (4,2)=1 平著走進來，所以是 A 不是 B
```

### 解法

```python
import random
from collections import deque


def pacific_atlantic(heights: list[list[int]]) -> list[list[int]]:
    m, n = len(heights), len(heights[0])

    def reach(starts: list[tuple[int, int]]) -> set[tuple[int, int]]:
        """從海岸往內「逆流」：只能走到不比自己低的鄰居。"""
        seen = set(starts)
        queue = deque(starts)
        while queue:
            r, c = queue.popleft()
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if (0 <= nr < m and 0 <= nc < n and (nr, nc) not in seen
                        and heights[nr][nc] >= heights[r][c]):
                    seen.add((nr, nc))
                    queue.append((nr, nc))
        return seen

    pacific = reach([(0, c) for c in range(n)] + [(r, 0) for r in range(1, m)])
    atlantic = reach([(m - 1, c) for c in range(n)] + [(r, n - 1) for r in range(m - 1)])
    return sorted([r, c] for r, c in pacific & atlantic)


def brute(heights: list[list[int]]) -> list[list[int]]:
    """對每一格順流做一次搜尋，O((mn)²)，用來對照。"""
    m, n = len(heights), len(heights[0])
    out = []
    for sr in range(m):
        for sc in range(n):
            pac = atl = False
            seen, stack = {(sr, sc)}, [(sr, sc)]
            while stack:
                r, c = stack.pop()
                pac |= r == 0 or c == 0
                atl |= r == m - 1 or c == n - 1
                for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                    if 0 <= nr < m and 0 <= nc < n and (nr, nc) not in seen and heights[nr][nc] <= heights[r][c]:
                        seen.add((nr, nc))
                        stack.append((nr, nc))
            if pac and atl:
                out.append([sr, sc])
    return out


h = [[1, 2, 2, 3, 5],
     [3, 2, 3, 4, 4],
     [2, 4, 5, 3, 1],
     [6, 7, 1, 4, 5],
     [5, 1, 1, 2, 4]]
assert pacific_atlantic(h) == [[0, 4], [1, 3], [1, 4], [2, 2], [3, 0], [3, 1], [4, 0]]
assert pacific_atlantic([[7]]) == [[0, 0]]                  # 單格同時碰到兩個海洋
assert pacific_atlantic([[1, 2, 3]]) == [[0, 0], [0, 1], [0, 2]]   # 只有一列：每格都同時靠兩海
assert pacific_atlantic([[3, 3], [3, 3]]) == [[0, 0], [0, 1], [1, 0], [1, 1]]
for _ in range(300):
    m, n = random.randint(1, 6), random.randint(1, 6)
    g = [[random.randint(0, 4) for _ in range(n)] for _ in range(m)]
    assert pacific_atlantic(g) == brute(g)
print("all tests passed")
```

### 複雜度與邊界

時間 O(mn)：兩次搜尋各自讓每格最多入隊一次，交集也是 O(mn)。空間 O(mn)，兩個 visited 集合加上 queue。邊界情況：只有一列或一行時，每格同時靠兩個海洋，全部都是答案；整片海拔相同時全部都是答案，這考驗比較是否寫成 `>=`；四個角落中，右上角 (0, n−1) 和左下角 (m−1, 0) 一定是答案，因為它們同時在兩個海洋的邊上。建立源頭串列時要避免把角落加兩次（上面寫法中左邊從第 1 列開始），不過即使重複，`seen` 是集合也不會出錯，只是多入隊一次。若 m · n 很大，可以把 set 換成兩個 m × n 的布林陣列，常數更小。

### Follow-up

> [!question]- F1. 如果要的是「只能流進太平洋、不能流進大西洋」的格子呢？
> 同樣的兩次搜尋，最後改用集合差 `pacific - atlantic`，O(mn)。如果要分別統計四種類別（只到太平洋、只到大西洋、兩者、都不能）的數量，就對每格查兩個布林值歸類，仍是 O(mn)。「都不能」是真的可能出現的：四周鄰居都比它高的盆地格子，水哪裡也流不出去，例如 `[[9, 9, 9], [9, 1, 9], [9, 9, 9]]` 中間的 1。反向搜尋從海岸往內爬時會被高牆擋住，自然不會把它放進任何一個集合，不需要特別處理。

> [!question]- F2. 如果有 k 個不同的出口（不只兩個海洋），要找能流到所有出口的格子呢？
> 對每個出口做一次逆流搜尋，得到 k 個集合，取交集，O(k · mn)。若 k 不大（≤ 30），可以讓每格存一個 bitmask，第 i 次搜尋把第 i 個 bit 打開，最後找出 mask 全為 1 的格子，避免建立 k 個集合。另一種思路是一次 BFS 傳遞 bitmask：每格的 mask 是「能從哪些出口逆流到達」，但因為圖有環（平地），單次傳播需要反覆更新直到不變，最差仍是 O(k · mn)，並不比分開搜尋好。

> [!question]- F3. 如果水只能流向「嚴格更低」的格子呢？
> 只需要把逆流條件從 `>=` 改成 `>`。此時圖變成**有向無環圖**（DAG），因為每走一步海拔嚴格上升，不可能繞回來。DAG 上可以安全地用 DFS + memoization：`can_reach_pacific(r, c)` = 自己在太平洋邊上，或任一個更低的鄰居可以到太平洋，每格只計算一次，O(mn)。這也回答了為什麼原題不能直接 memo：允許相等時平地會形成環。

> [!question]- F4. 為什麼不能從每格順流 DFS 再加 memoization？要怎麼修正？
> 平地讓圖有環：A、B 海拔相同且相鄰時，A 的答案依賴 B，B 也依賴 A。DFS 先進入 A，再進入 B，B 看到 A 「正在計算中」，此時若把 A 當成 False 並 memo 住 B 的結果，B 的答案可能是錯的（A 其實之後會從別的方向找到海洋）。正確的修正是先把圖做強連通元件縮點（SCC，例如 Tarjan 演算法），同一個 SCC 內的格子答案相同，縮點後的圖是 DAG，再做 memo，O(mn)。但這比反向 BFS 複雜得多，面試時說明這個陷阱並選擇反向搜尋，才是好的取捨。

> [!question]- F5. 用遞迴 DFS 寫逆流搜尋可以嗎？
> 邏輯完全相同，但 200 × 200 的格子在最壞情況（例如一條螺旋狀上升的路徑）下遞迴深度可達 4 × 10⁴，超過 Python 預設的遞迴上限。面試中可以用遞迴寫得很簡潔，但要主動說明這個風險並提出迭代版本（把 `queue.popleft()` 換成 `stack.pop()` 就是迭代 DFS）。在 C++ 或 Java 中預設的呼叫堆疊也只有幾 MB，同樣可能溢位，所以這不只是 Python 的問題。

## 核心題 5｜130. Surrounded Regions｜Medium

### 題目

給一個 m × n 的字元矩陣 `board`，每格是 `'X'` 或 `'O'`。上下左右相連的 `'O'` 組成一個區域；如果一個區域**完全被 `'X'` 包圍**，也就是區域中沒有任何一格位於矩陣的邊界上，就把這個區域的所有 `'O'` 改成 `'X'`。請**原地修改** `board`，不需要回傳。限制：`1 <= m, n <= 200`。

- 範例 1：
  ```
  X X X X          X X X X
  X O O X    →     X X X X
  X X O X          X X X X
  X O X X          X O X X
  ```
  中間的三個 `'O'` 被包圍，翻成 `'X'`；左下角的 `'O'` 在邊界上，保留。
- 範例 2（邊界）：`[["X"]]` 不變。
- 範例 3（邊界）：`[["O","O"],["O","O"]]` 不變，所有 `'O'` 都在邊界上。
- 範例 4：一個環狀的 `'O'` 區域只要有一格碰到邊界，整個區域都保留，即使它大部分在內部。

### 思路

直覺做法是對每個 `'O'` 區域整塊找出來，檢查其中有沒有格子在邊界上，沒有就整塊翻掉。這其實已經是 O(mn) 了（每格只屬於一個區域），但寫起來要先收集整個區域再決定，而且「在搜尋途中碰到邊界」不能立刻停止，否則區域會只翻一半。更簡潔的做法來自**反向思考**：與其找「被包圍的區域」，不如找「沒被包圍的區域」。

觀察：一個 `'O'` 區域沒被包圍，當且僅當它有某一格在邊界上；換句話說，**從邊界上的 `'O'` 出發能走到的所有 `'O'`，就是全部不該翻的格子**，其餘的 `'O'` 一定被包圍。所以分三步：第一步，從四條邊上的每個 `'O'` 出發做 DFS，把走到的 `'O'` 暫時改成 `'#'`（標記為安全）；第二步，掃描整個矩陣，剩下的 `'O'` 全部翻成 `'X'`；第三步，把 `'#'` 還原成 `'O'`。這和核心題 4 是同一個「從邊界反向搜尋」的想法。

用第三種字元 `'#'` 做標記，是原地修改題常見的技巧：它同時扮演 visited，又不需要額外的 m × n 陣列。第二步和第三步可以合併成一次掃描，因為每格的處理只看自己。注意第一步必須在第二步之前全部完成：如果邊掃描邊翻轉，可能在發現某區域連到邊界之前，就已經把它的一部分翻掉了。

```text
範例 1

原始              步驟 1：從邊界的 O 出發標記 #     步驟 2+3：O → X，# → O
X X X X           X X X X                        X X X X
X O O X           X O O X                        X X X X
X X O X    →      X X O X                 →      X X X X
X O X X           X # X X                        X O X X

邊界上的 O 只有 (3,1)；從它出發的 DFS 鄰居 (2,1) 是 X，所以只標記自己。
中間的 (1,1)、(1,2)、(2,2) 沒被任何邊界 O 碰到 → 翻成 X。

範例 4（環狀區域）
X X X X X         X X X X X                       X X X X X
X O O O X         X # # # X                       X O O O X
X O X O X    →    X # X # X                →      X O X O X
X O O O O         X # # # #                       X O O O O
X X X X X         X X X X X                       X X X X X
(3,4) 在右邊界上，從它出發可以繞整個環一圈，所以整個環都安全。
```

### 解法

```python
import random


def solve(board: list[list[str]]) -> None:
    """原地修改：被 'X' 完全包圍的 'O' 區域翻成 'X'。"""
    if not board or not board[0]:
        return
    m, n = len(board), len(board[0])

    def protect(r: int, c: int) -> None:
        if board[r][c] != "O":
            return
        board[r][c] = "#"                       # 和邊界相連：暫時標成 '#'
        stack = [(r, c)]
        while stack:
            x, y = stack.pop()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < m and 0 <= ny < n and board[nx][ny] == "O":
                    board[nx][ny] = "#"
                    stack.append((nx, ny))

    for r in range(m):
        protect(r, 0)
        protect(r, n - 1)
    for c in range(n):
        protect(0, c)
        protect(m - 1, c)
    for r in range(m):
        for c in range(n):
            if board[r][c] == "O":
                board[r][c] = "X"               # 沒被保護到的 'O' 一定被包圍
            elif board[r][c] == "#":
                board[r][c] = "O"               # 還原


def brute(board: list[list[str]]) -> list[list[str]]:
    """對每個 'O' 區域整塊找出來，看有沒有碰到邊界。"""
    m, n = len(board), len(board[0])
    out = [row[:] for row in board]
    seen = set()
    for r in range(m):
        for c in range(n):
            if board[r][c] == "O" and (r, c) not in seen:
                comp, stack = [], [(r, c)]
                seen.add((r, c))
                while stack:
                    x, y = stack.pop()
                    comp.append((x, y))
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if 0 <= nx < m and 0 <= ny < n and board[nx][ny] == "O" and (nx, ny) not in seen:
                            seen.add((nx, ny))
                            stack.append((nx, ny))
                if not any(x in (0, m - 1) or y in (0, n - 1) for x, y in comp):
                    for x, y in comp:
                        out[x][y] = "X"
    return out


b = [list("XXXX"), list("XOOX"), list("XXOX"), list("XOXX")]
solve(b)
assert b == [list("XXXX"), list("XXXX"), list("XXXX"), list("XOXX")]
b = [list("X")]
solve(b)
assert b == [list("X")]
b = [list("OO"), list("OO")]                      # 全部在邊界上，一個都不翻
solve(b)
assert b == [list("OO"), list("OO")]
b = [list("XXXXX"), list("XOOOX"), list("XOXOX"), list("XOOOO"), list("XXXXX")]
solve(b)                                          # 環狀區域經由 (3, 4) 接到邊界
assert b == [list("XXXXX"), list("XOOOX"), list("XOXOX"), list("XOOOO"), list("XXXXX")]
for _ in range(300):
    m, n = random.randint(1, 7), random.randint(1, 7)
    g = [[random.choice("XXO") for _ in range(n)] for _ in range(m)]
    expect = brute(g)
    solve(g)
    assert g == expect
print("all tests passed")
```

### 複雜度與邊界

時間 O(mn)：邊界出發的搜尋讓每個 `'O'` 最多被標記一次，最後的掃描是 O(mn)。額外空間：標記直接寫在 board 上，只有 stack 是 O(mn)（最差整片 `'O'` 時）。邊界情況：一列或一行時所有格子都在邊界上，什麼都不翻；四個角落會被 `protect` 呼叫兩次，但第二次看到的是 `'#'` 會直接返回；整片 `'X'` 時三個步驟都不做任何事。`protect` 開頭的 `board[r][c] != "O"` 檢查同時處理了「是 X」和「已標記」兩種情況。若改用遞迴 DFS，200 × 200 的全 `'O'` 內部會遞迴很深，所以這裡用迭代 stack。

### Follow-up

> [!question]- F1. 如果要數有幾格陸地永遠走不到邊界呢（1020. Number of Enclaves）？
> 完全相同的結構：從邊界上的每格陸地出發做 DFS，把能到的陸地全部標記（或直接改成水），最後數剩下的陸地格數即可，O(mn)。差別只在最後一步是「計數」而不是「翻轉」。這類題的共同訊號是「碰不碰得到邊界」，解法一律是從邊界反向出發，而不是對每格判斷。

> [!question]- F2. 如果要數「被水完全包圍的島」有幾座（1254. Number of Closed Islands）？
> 先從邊界出發把所有碰到邊界的陸地淹掉（它們不算封閉），再對剩下的陸地做核心題 1 的數島嶼。兩次掃描都是 O(mn)。另一種寫法是一次搜尋：對每座島 DFS，途中若碰到邊界就把旗標設為 False，但**不能提前停止**，必須把整座島標記完，否則同一座島的剩餘部分之後會被當成新島。先淹邊界的寫法避開了這個陷阱，通常更不容易寫錯。

> [!question]- F3. 能不能用 union-find 做？什麼時候會想這樣做？
> 可以：建一個虛擬節點 `BORDER`，把所有邊界上的 `'O'` 和它 union，內部相鄰的 `'O'` 互相 union，最後所有不和 `BORDER` 同集合的 `'O'` 翻成 `'X'`，時間 O(mn · α(mn))。單次計算時 DFS 更簡單；但如果之後格子會不斷有 `'X'` 被改成 `'O'`，而每次都要回答「某格是否被包圍」，union-find 能增量處理，不必每次重跑整個搜尋。注意 union-find 不支援刪除，若是 `'O'` 變成 `'X'`，就要用離線倒序處理等技巧（第 17 章難題 3 的 803 就是這個想法）。

> [!question]- F4. 如果要求 O(1) 額外空間，連 stack 都不能用呢？
> 標記已經是原地的，剩下的是搜尋用的 stack。一種 O(1) 空間的做法是**反覆掃描**：先把邊界的 `'O'` 標成 `'#'`，然後不斷掃描整個矩陣，只要某個 `'O'` 有鄰居是 `'#'` 就把它也標成 `'#'`，直到某一輪沒有任何變化。每輪 O(mn)，最差要 O(mn) 輪（蛇形的長區域每輪只前進一格），總共 O((mn)²)。所以這是用時間換空間，面試中說明這個取捨即可；實務上 O(mn) 的 stack 幾乎總是可以接受的。

> [!question]- F5. 如果對角線相鄰的 `'O'` 也算同一個區域呢？
> 「包圍」的定義跟著變：對角相鄰也算連通時，`'O'` 可以從兩個 `'X'` 的對角縫隙鑽出去。做法不變，只要把 `protect` 的四個方向改成八個方向即可，時間仍是 O(mn)。面試時值得主動確認相鄰的定義，因為它直接決定答案；例如 `[[O,X,O],[X,O,X],[O,X,O]]` 的中央 `'O'`：四方向時它的上下左右都是 `'X'`，被包圍而翻轉；八方向時它透過對角線和四個角落的 `'O'` 相連，而角落在邊界上，所以保留。

## 難題 1｜127. Word Ladder｜Hard

### 題目

給起始字 `begin`、目標字 `end` 和一個字典 `word_list`。一次「轉換」是把目前的字恰好改掉一個字母，而且改完的字必須在字典中（`begin` 本身不必在字典裡）。請回傳從 `begin` 變到 `end` 的最短轉換序列中**包含幾個字**（含頭尾）；如果做不到，回傳 0。限制：所有字長度相同 `1 <= L <= 10`，只含小寫英文字母；字典最多 5000 個字且互不重複；`begin != end`。

- 範例 1：`begin = "hit"`、`end = "cog"`、`word_list = ["hot","dot","dog","lot","log","cog"]`，回傳 `5`，其中一條最短序列是 `hit → hot → dot → dog → cog`。
- 範例 2：同樣的 `begin` 與 `end`，但字典是 `["hot","dot","dog","lot","log"]`，回傳 `0`，因為 `cog` 不在字典中，最後一步不合法。
- 範例 3（邊界）：`begin = "a"`、`end = "c"`、`word_list = ["a","b","c"]`，回傳 `2`：`a → c` 一步就到。
- 範例 4（邊界）：`begin = "hot"`、`end = "dog"`、`word_list = ["hot","dog"]`，回傳 `0`，兩字差了兩個字母，中間沒有可用的字。

### 提示

> [!tip]- 提示 1
> 把每個字當成一個節點，兩個字只差一個字母就連一條邊。題目問的「最短轉換序列」在這張圖上是什麼？每條邊的代價一樣嗎？

> [!tip]- 提示 2
> 這是等權圖的最短路，用 BFS。真正的瓶頸是「找鄰居」：兩兩比較所有字要 O(N² · L)。換個方向想：一個長度 L 的字，改一個字母只有 25 · L 種可能，能不能直接產生候選再查字典？

> [!tip]- 提示 3
> 另一種找鄰居的方法是「通配符桶」：把 `hot` 放進 `*ot`、`h*t`、`ho*` 三個桶，同一個桶裡的字彼此恰好差一個字母（就在 `*` 的位置）。BFS 時從桶裡取鄰居，用過的桶清空。若還要更快，從 `begin` 和 `end` 兩端同時 BFS，每次擴展比較小的那一邊。

### 詳解

**為什麼直覺做法不夠**。直接的 DFS 或 backtracking 會列舉所有轉換序列再取最短，數量是指數級的，而且 DFS 第一次碰到 `end` 時的路徑不一定最短。換成 BFS 方向就對了，但若先把圖建出來：對每一對字檢查是否差一個字母，N = 5000、L = 10 時是 C(5000, 2) × 10 ≈ 1.25 × 10⁸ 次字元比較，在 Python 中很慢，而且大部分字對根本不相鄰。

**突破點一：不建圖，直接產生鄰居**。圖是隱式的：一個字的鄰居就是「改掉一個位置的字母後仍在字典中」的字。每個字最多 25 · L 個候選，每個候選建字串 O(L)、查 set 平均 O(L)（雜湊要讀過整個字串），所以每個字 O(26 · L²)，BFS 總共 O(N · 26 · L²)，N = 5000、L = 10 時約 1.3 × 10⁷，可以接受。

**突破點二：通配符桶**。把每個字的 L 個「挖掉一個字母」的版本當成 key，例如 `hot` 產生 `*ot`、`h*t`、`ho*`。兩個字差恰好一個字母，當且僅當它們有一個共同的 key。所以預先建好 `key → 字串列表` 的 map，BFS 時一個字的鄰居就是它 L 個桶裡所有的字。建桶 O(N · L²)，BFS 時每個桶處理完就清空（桶裡的字此時都已入隊，之後再有人查這個桶也不會得到新東西），所以每個桶只被完整掃描一次。這個做法和字母表大小無關，字母表很大（例如 Unicode）時優勢明顯。

**正確性**。BFS 保證第一次把 `end` 取出時，`dist[end]` 就是最少的邊數，加一（或像程式裡一樣把 `begin` 的距離設為 1）就是序列中的字數。字典裡沒有 `end` 時一定做不到，可以一開始就回傳 0，省下整個搜尋。

**Bidirectional BFS**。設最短距離是 d、每個字平均有 b 個鄰居，單向 BFS 最多會碰到約 b^d 個字；從兩端各走 d/2 步再相遇，總共約 2 · b^(d/2)。實作要點：用兩個集合 `front`、`back` 代表兩邊目前的前緣；每輪只擴展**比較小**的那個集合（這讓兩邊大致平衡，也是效能的主要來源）；產生候選時若候選已在對面的集合中，代表兩邊相遇，回傳目前的步數。拜訪過的字直接從字典中移除，兩邊共用同一份「未拜訪」的字典。

```text
範例 1：BFS 的層（dist 是序列中的字數）

通配符桶（只列有兩個字以上的）：
*ot: hot dot lot     h*t: hit hot     d*g: dog     *og: dog log cog
do*: dot dog         lo*: lot log     l*t: lot     ...

層 1   hit
        └─ h*t → hot
層 2   hot
        └─ *ot → dot, lot          （*ot 桶清空）
層 3   dot                 lot
        └─ do* → dog        └─ lo* → log
層 4   dog                 log
        └─ *og → cog        （log 再查 *og 時桶已空）
層 5   cog  = end → 回傳 5

雙向 BFS：hit 側 = {hit}，cog 側 = {cog}
第 1 輪  1 vs 1，擴展 hit 側           → hit 側 = {hot}           steps = 2
第 2 輪  1 vs 1，擴展 hit 側           → hit 側 = {dot, lot}      steps = 3
第 3 輪  2 > 1，交換，改擴展 cog 側    → cog 側 = {dog, log}      steps = 4
第 4 輪  2 vs 2，不交換，擴展 cog 側：dog 改一字得到 dot ∈ hit 側 → 相遇，回傳 5
```

### 解法

```python
import random
from collections import defaultdict, deque


def ladder_length(begin: str, end: str, word_list: list[str]) -> int:
    words = set(word_list)
    if end not in words:
        return 0
    L = len(begin)
    buckets = defaultdict(list)                  # "h*t" → ["hot", "hit", ...]
    for w in words | {begin}:
        for i in range(L):
            buckets[w[:i] + "*" + w[i + 1:]].append(w)
    dist = {begin: 1}
    queue = deque([begin])
    while queue:
        w = queue.popleft()
        if w == end:
            return dist[w]
        for i in range(L):
            key = w[:i] + "*" + w[i + 1:]
            for nxt in buckets[key]:
                if nxt not in dist:
                    dist[nxt] = dist[w] + 1
                    queue.append(nxt)
            buckets[key] = []                    # 這個桶的所有字都已入隊，之後不必再掃
    return 0


def ladder_length_bidirectional(begin: str, end: str, word_list: list[str]) -> int:
    words = set(word_list)
    if end not in words:
        return 0
    if begin == end:
        return 1
    words.discard(begin)
    words.discard(end)
    front, back = {begin}, {end}
    steps = 1
    letters = "abcdefghijklmnopqrstuvwxyz"
    while front and back:
        if len(front) > len(back):               # 永遠擴展比較小的那一邊
            front, back = back, front
        steps += 1
        nxt_front = set()
        for w in front:
            for i in range(len(w)):
                for ch in letters:
                    cand = w[:i] + ch + w[i + 1:]
                    if cand in back:
                        return steps
                    if cand in words:
                        words.remove(cand)       # 移出字典 = 標記為已拜訪
                        nxt_front.add(cand)
        front = nxt_front
    return 0


assert ladder_length("hit", "cog", ["hot", "dot", "dog", "lot", "log", "cog"]) == 5
assert ladder_length("hit", "cog", ["hot", "dot", "dog", "lot", "log"]) == 0   # end 不在字典
assert ladder_length("a", "c", ["a", "b", "c"]) == 2
assert ladder_length("hot", "dog", ["hot", "dog"]) == 0                         # 無法一步一字母
assert ladder_length_bidirectional("hit", "cog", ["hot", "dot", "dog", "lot", "log", "cog"]) == 5
assert ladder_length_bidirectional("a", "c", ["a", "b", "c"]) == 2
for _ in range(300):
    L = random.randint(1, 3)
    pool = ["".join(random.choice("abc") for _ in range(L)) for _ in range(random.randint(1, 12))]
    b = "".join(random.choice("abc") for _ in range(L))
    e = random.choice(pool)
    assert ladder_length(b, e, pool) == ladder_length_bidirectional(b, e, pool)
print("all tests passed")
```

隨機測試讓兩種寫法互相對照，並刻意讓 `begin` 可能等於 `end`、字典可能有重複，確保兩者在這些情況下行為一致。

### 複雜度與邊界

通配符桶版本：建桶 O(N · L²)（N 個字、每字 L 個 key、每個 key 長 L）；BFS 中每個字產生 L 個 key 各 O(L)，每個桶只完整掃描一次，總共 O(N · L²)。空間 O(N · L²)，桶裡存了 N · L 個字的參照，key 本身共 N · L 個、每個長 L。字母枚舉版本是 O(N · 26 · L²) 時間、O(N · L) 空間。雙向 BFS 的最差複雜度相同，但在鄰居多、距離長的字典上實際碰到的字少很多。邊界情況：`end` 不在字典直接回傳 0；`begin` 不在字典也沒關係，它只是起點；字典中出現 `begin` 時要注意不要把它當成新節點再入隊（程式中 `dist` 已有 `begin`，桶版本自然跳過；雙向版本先把它從字典移除）。長度 L = 1 時所有字彼此相鄰，答案最多是 2。

### Follow-up

> [!question]- F1. 如果要回傳其中一條最短轉換序列（而不只是長度）呢？
> 在 BFS 中多記一個 `parent` map：某個字第一次被看到時，記下是誰看到它。找到 `end` 後沿著 `parent` 一路往回走到 `begin`，反轉後就是一條最短序列。時間與空間仍是 O(N · L²)，回溯只多 O(d)。若要的是**所有**最短序列，`parent` 只記一個就不夠了，因為同一個字可能被同一層的好幾個字看到，這就是難題 2（126）。

> [!question]- F2. 雙向 BFS 一定比較快嗎？最差情況是什麼？
> 不一定。它的優勢來自「兩個半徑 d/2 的球加起來遠小於一個半徑 d 的球」，前提是圖的分支度夠大且大致均勻。若圖接近一條鏈（每個字只有一兩個鄰居），兩者都是 O(N)，雙向只多了常數成本。若一端的分支度遠大於另一端，「每次擴展較小的一邊」可以避免從大的那端擴展，這是雙向 BFS 最重要的一行。最差時間複雜度仍是 O(N · 26 · L²)，所以面試時應該說「實務上通常快很多」，而不是宣稱複雜度降低了。

> [!question]- F3. 如果字典固定，但要回答很多組 (begin, end) 查詢呢？
> 每次查詢跑一次 BFS 是 O(N · L²)，q 次就是 O(q · N · L²)。若查詢的 `end` 都相同，從 `end` 反向做一次 BFS 得到所有字到 `end` 的距離，再為每個通配符桶預先記下「桶內所有字到 `end` 的最小距離」；之後每次查詢只需看 `begin` 的 L 個桶，取最小值加一，O(L²)，不必掃描桶的內容。若 `begin` 與 `end` 都任意，可以預先把字典的連通元件標好（用 BFS 或 union-find，第 17 章），兩字不在同一個元件時立刻回傳 0；同一元件內仍需 BFS 或雙向 BFS。全點對最短路要 O(N²) 空間，N = 5000 時有 2500 萬個值，可以存，但用 Python 計算偏慢，是否值得取決於查詢數。

> [!question]- F4. 如果每次轉換也可以插入或刪除一個字母呢？
> 鄰居多了兩類：長度 L ± 1 的字。「改一個字母」仍用 `h*t` 型的 key；「刪除一個字母」可以產生 L 個刪掉一個字元的版本（`hot` → `ot`、`ht`、`ho`），只要某個長度 L − 1 的字典字恰好等於其中之一，就代表兩者差一次插入／刪除（兩個等長的字若刪掉同一個位置後相同，則是原本的「改一個字母」）。實作時可以把「刪除版本」也當成桶的 key（例如加上前綴標記類型），讓長度不同的字也能互相找到。BFS 本身不變，時間仍是 O(N · L²) 量級。這也是拼字檢查中 symmetric delete 方法的核心想法。

> [!question]- F5. 433. Minimum Genetic Mutation 和 752. Open the Lock 跟這題有什麼關係？
> 它們是同一個模板換了鄰居規則。433 的字長 8、字母只有 A、C、G、T，每個字最多 24 個候選；752 的狀態是四位數密碼 `0000` 到 `9999`，每次轉一格，每個狀態恰好 8 個鄰居，總共 10⁴ 個狀態，而 `deadends` 只是一開始就標為已拜訪的節點。三題的共同點是：**狀態可以列舉、鄰居由規則產生、每一步代價相同**，看到這三個條件就用 BFS，若起點終點都已知且分支度大，再考慮雙向 BFS。

### 心得

關鍵突破是把字看成節點、把「改一個字母」看成邊，然後不建圖、用通配符桶或字母枚舉即時產生鄰居。它和核心題的差別不在搜尋本身，而在**隱式圖**：節點不是格子、鄰居要自己定義，而且找鄰居的成本才是瓶頸。面試時建議先說清楚圖的定義與 BFS 的理由，再比較兩種找鄰居的方法（兩兩比較 O(N² · L) vs 產生候選 O(N · 26 · L²)），寫出單向版本後主動提雙向 BFS 作為優化；這題的雙向版本也是面試官最常追問的方向，它的程式結構要練到能直接寫出來。

## 難題 2｜126. Word Ladder II｜Hard

### 題目

設定和難題 1 完全相同：起始字 `begin`、目標字 `end`、字典 `word_list`，每次改一個字母且新字必須在字典中。但這次要回傳**所有**最短轉換序列，每條序列是一個字串列表（從 `begin` 到 `end`）；做不到時回傳空列表。序列之間順序不限（這裡排序後回傳以便測試）。限制：`1 <= L <= 5`，字典最多 500 個字，題目保證所有最短序列的總長度不會超過 10⁵。

- 範例 1：`begin = "hit"`、`end = "cog"`、`word_list = ["hot","dot","dog","lot","log","cog"]`，回傳 `[["hit","hot","dot","dog","cog"], ["hit","hot","lot","log","cog"]]`。
- 範例 2：同上但字典沒有 `cog`，回傳 `[]`。
- 範例 3（邊界）：`begin = "a"`、`end = "c"`、`word_list = ["a","b","c"]`，回傳 `[["a","c"]]`；`a → b → c` 雖然合法，但不是最短。
- 範例 4：`begin = "ab"`、`end = "cd"`、`word_list = ["ad","cb","cd"]`，回傳 `[["ab","ad","cd"], ["ab","cb","cd"]]`，兩條路在中間分岔、最後匯合。

### 提示

> [!tip]- 提示 1
> 「所有最短路徑」可以拆成兩件事：先知道每個字離 `begin` 多遠，再只沿著「距離剛好加一」的邊列舉路徑。哪個演算法能給你距離？

> [!tip]- 提示 2
> BFS 時，一個字可能同時被上一層的好幾個字看到，這些都是它在最短路徑上的「父節點」，全部要記下來。所以不能在第一次看到時就把它標為已拜訪，那會丟掉第二個父節點。什麼時候標記才對？

> [!tip]- 提示 3
> 以「層」為單位標記：處理一層之前，把這一層的字全部從字典移除；這一層產生的下一層字可以有多個父節點，但同層與更早的字都不能再被當成子節點。找到 `end` 所在的那一層就停止，最後從 `end` 沿著父節點 DFS 回溯到 `begin`。

### 詳解

**為什麼直覺做法不行**。最自然的寫法是讓 queue 裡放「整條路徑」而不只是最後一個字，取出路徑時嘗試延伸，碰到 `end` 就記錄，並在路徑長度超過已知最短長度時停止。它是正確的，但 queue 中同時存在大量共享前綴的部分路徑；同一個字被不同路徑經過時，每條路徑都會各自延伸一次，部分路徑的數量可以隨著層數呈指數成長，其中絕大多數最後根本到不了 `end`。題目特別保證「輸出總長度不超過 10⁵」，就是暗示解法應該只花和輸出成正比的時間去列舉路徑，而不是把時間浪費在死路上。

**突破點一：先 BFS 建分層 DAG**。BFS 會把字分成第 0、1、2…層（距離 `begin` 的步數）。一條轉換序列是最短的，當且僅當它每一步都從第 i 層走到第 i + 1 層：若某一步留在同一層或往回走，總步數就超過 `end` 的層數。所以只要保留「第 i 層 → 第 i + 1 層」的邊，就得到一個分層的 DAG（有向無環圖），DAG 中每條從 `begin` 到 `end` 的路徑都是最短路，反之亦然。

**突破點二：按層標記 visited**。一般 BFS 在第一次看到 v 時標記，第二個看到 v 的同層節點會被擋掉，這在只要距離時沒問題，但在這題會丟失父節點。範例 1 中 `cog` 同時是第 4 層 `dog` 和 `log` 的鄰居，兩者都是它的父節點。正確的做法是**以層為單位**：處理第 i 層之前，把第 i 層的所有字從字典中移除；擴展第 i 層時，任何仍在字典中的鄰居都屬於第 i + 1 層，把父節點記下來（可以多個）。這保證同層之間的邊、往回的邊都不會被記錄，而跨層的邊一條都不漏。

**突破點三：從 end 往回 DFS**。有了 `parents` map 之後，從 `end` 出發，沿著父節點往回走到 `begin`，每走到 `begin` 就得到一條路徑（反轉後輸出）。為什麼從 `end` 往回而不是從 `begin` 往前？因為從 `end` 往回走的每一個節點，一定都在某條 `begin` 到 `end` 的最短路徑上（它是 `end` 的祖先，且 BFS 保證它能從 `begin` 到達），所以回溯時**沒有任何死路**，花的時間和輸出大小成正比。從 `begin` 往前走則會進入很多到不了 `end` 的分支（例如同一層的其他字），白白浪費時間。

**何時停止**。一旦某一層產生了 `end`，就不需要再往下一層擴展，因為更深的層只會產生更長的路徑。但**這一層必須完整處理完**，因為 `end` 的其他父節點可能還在這一層後面才被處理到。

```text
範例 1 的分層 DAG（箭頭指向父節點）

層 0   hit
        ↑
層 1   hot
       ↗   ↖
層 2  dot   lot
       ↑     ↑
層 3  dog   log
       ↖   ↗
層 4   cog          ← 這一層出現 end，停止

parents:  hot:[hit]  dot:[hot]  lot:[hot]  dog:[dot]  log:[lot]  cog:[dog, log]

從 cog 回溯（path 是反著累積的）：
cog → dog → dot → hot → hit   反轉 → hit hot dot dog cog
cog → log → lot → hot → hit   反轉 → hit hot lot log cog

如果在「第一次看到」時就標記：處理 dog 時 cog 被標記，
處理 log 時看到 cog 已拜訪就跳過 → parents[cog] 只有 [dog]，少一條路徑。
```

### 解法

```python
import random
from collections import defaultdict, deque


def find_ladders(begin: str, end: str, word_list: list[str]) -> list[list[str]]:
    words = set(word_list)
    if end not in words:
        return []
    words.discard(begin)
    parents = defaultdict(list)          # word → 上一層中能一步到它的所有字
    layer = {begin}
    found = False
    while layer and not found:
        words -= layer                   # 整層一起移出字典：同層的字不能互相當父節點
        nxt = defaultdict(list)
        for w in layer:
            for i in range(len(w)):
                for ch in "abcdefghijklmnopqrstuvwxyz":
                    cand = w[:i] + ch + w[i + 1:]
                    if cand in words:
                        nxt[cand].append(w)
        for child, ps in nxt.items():
            parents[child].extend(ps)
        found = end in nxt
        layer = set(nxt)
    if not found:
        return []
    paths, path = [], [end]

    def backtrack(w: str) -> None:       # 從 end 沿 parents 走回 begin
        if w == begin:
            paths.append(path[::-1])
            return
        for p in parents[w]:
            path.append(p)
            backtrack(p)
            path.pop()

    backtrack(end)
    return sorted(paths)


def brute(begin: str, end: str, word_list: list[str]) -> list[list[str]]:
    """BFS 帶著整條路徑，列出所有最短路徑（小輸入才可用）。"""
    words = set(word_list)
    if end not in words:
        return []
    adj = lambda a, b: sum(x != y for x, y in zip(a, b)) == 1
    best, out = None, []
    queue = deque([[begin]])
    while queue:
        p = queue.popleft()
        if best is not None and len(p) > best:
            break
        if p[-1] == end:
            best = len(p)
            out.append(p)
            continue
        for w in words:
            if w not in p and adj(p[-1], w):
                queue.append(p + [w])
    return sorted(out)


assert find_ladders("hit", "cog", ["hot", "dot", "dog", "lot", "log", "cog"]) == [
    ["hit", "hot", "dot", "dog", "cog"], ["hit", "hot", "lot", "log", "cog"]]
assert find_ladders("hit", "cog", ["hot", "dot", "dog", "lot", "log"]) == []
assert find_ladders("a", "c", ["a", "b", "c"]) == [["a", "c"]]
assert find_ladders("ab", "cd", ["ad", "cb", "cd"]) == [["ab", "ad", "cd"], ["ab", "cb", "cd"]]
for _ in range(300):
    L = random.randint(1, 3)
    pool = list({"".join(random.choice("abc") for _ in range(L)) for _ in range(random.randint(1, 9))})
    b = "".join(random.choice("abc") for _ in range(L))
    e = random.choice(pool)
    if b == e:
        continue
    assert find_ladders(b, e, pool) == brute(b, e, pool)
print("all tests passed")
```

`brute` 就是「詳解」第一段描述的路徑 BFS，小輸入下用它驗證分層 DAG 的做法沒有漏掉或多出任何路徑。

### 複雜度與邊界

BFS 階段和難題 1 相同：每個字只會在一層中被擴展一次，每次產生 26 · L 個候選、每個 O(L)，共 O(N · 26 · L²)。`parents` 中的邊數最多是 DAG 的邊數，O(N · 26 · L)。回溯階段與輸出成正比：設共有 P 條最短路徑、每條長 d + 1，回溯時間是 O(P · d)，因為沒有死路，每次遞迴都在某條會被輸出的路徑上；再加上產生每條路徑的 `path[::-1]` 也是 O(d)。P 可以是指數級的（例如每一層都有兩個可互換的字），這是輸出本身的大小，任何演算法都無法避免。邊界情況：`end` 不在字典回傳空列表；`begin` 在字典中時要先移除，否則它可能被當成某個字的子節點；只有一條路徑時正常輸出；遞迴深度等於最短距離 d ≤ N，在 N ≤ 500 時安全。

### Follow-up

> [!question]- F1. 如果只要回傳「最短序列有幾條」而不列舉呢？
> 在分層 BFS 時同時做計數 DP：`ways[begin] = 1`，每記錄一條父邊 `w → cand`，就做 `ways[cand] += ways[w]`。因為整層的父節點都在處理下一層之前就計算完成，加總順序沒有問題。答案是 `ways[end]`，時間 O(N · 26 · L²)，完全不需要列舉路徑。條數可能非常大，在其他語言中要注意溢位或依題目要求取模；Python 的整數不會溢位。這也說明了為什麼這題的題目要限制輸出大小：計數是多項式時間，列舉卻可能是指數。

> [!question]- F2. 可以用雙向 BFS 加速嗎？要注意什麼？
> 可以，而且在字典大時效果明顯。做法是兩邊各自分層擴展、每次擴展較小的一邊，記錄父邊時要依「目前是從哪一端擴展」決定方向（從 `end` 那端擴展時，邊要反過來存）。最關鍵的細節是：**一旦兩邊在某一層相遇，必須把這一層完整處理完**，收集所有相遇的邊，而不是在第一次相遇就停，否則會漏掉經過其他相遇點的最短路徑。之後同樣從 `end` 往回溯。複雜度的最差情況不變，但實際搜尋的字少很多。

> [!question]- F3. 如果只要字典序最小的那一條最短序列呢？
> 先從 `end` 反向做一次 BFS，得到每個字到 `end` 的距離 `d`。然後從 `begin` 開始貪婪：每一步在所有「距離比目前少一」的鄰居中選字典序最小的，直到抵達 `end`。因為每個選擇都保證仍在某條最短路徑上（距離剛好少一），而字典序是逐位比較的，貪婪地讓每一個位置最小就是整體最小。時間 O(N · 26 · L²)，不需要列舉所有路徑。

> [!question]- F4. 為什麼回溯要從 end 往 begin，而不是從 begin 沿著 children 往 end？
> 從 `begin` 往前走時，分層 DAG 中有很多節點根本到不了 `end`（例如 `end` 那一層的其他字，或沒有通往 `end` 的分支），DFS 會走進這些死路再退回來，時間可能遠大於輸出大小。從 `end` 沿著父節點往回走，每個被拜訪的節點都是 `end` 的祖先，而所有祖先都能從 `begin` 到達，所以每一步都會產生至少一條輸出路徑，總時間是 O(輸出大小)。若一定要從 `begin` 往前，就要先從 `end` 反向標記「哪些節點能到 `end`」，只沿著被標記的子節點走，效果相同。

### 心得

關鍵突破是把「列舉所有最短路徑」拆成兩階段：BFS 建出只含「第 i 層 → 第 i + 1 層」邊的分層 DAG，再從 `end` 沿父節點回溯。最容易錯的是 visited 的時機：要以**層**為單位移除，而不是第一次看到就標記，否則同層的第二個父節點會被丟掉。它和難題 1 共用同一個找鄰居的方法，差別在 BFS 要保留多個父節點，以及回溯要從終點開始以避免死路。面試時先講清楚「分層 DAG 中的路徑恰好就是所有最短路徑」這個等價關係，再說明按層標記與從終點回溯兩個細節，面試官就能確定你理解為什麼這個做法既不漏也不多。

## 難題 3｜1293. Shortest Path in a Grid with Obstacles Elimination｜Hard

### 題目

給一個 m × n 的格子 `grid`，0 是空地、1 是障礙物。你從左上角 (0, 0) 出發，要走到右下角 (m − 1, n − 1)，每步可以往上下左右移動一格。途中**最多可以消除 k 個障礙物**（走進障礙物格子就算消除一個）。請回傳最少的步數；若無論如何都到不了，回傳 -1。限制：`1 <= m, n <= 40`，`1 <= k <= m · n`，起點與終點保證是 0（下面的範例也示範 k = 0 的情況，同一個程式照樣適用）。

- 範例 1：
  ```
  0 0 0
  1 1 0
  0 0 0
  0 1 1
  0 0 0
  ```
  `k = 1`，回傳 `6`：沿著右邊往下走，在 (3, 2) 消除一個障礙物，路線是 (0,0) → (0,1) → (0,2) → (1,2) → (2,2) → (3,2) → (4,2)。若 k = 0，只能繞 S 形，要 10 步。
- 範例 2：`[[0,1,1],[1,1,1],[1,0,0]]`、`k = 1`，回傳 `-1`：至少要打穿兩個障礙物才能到終點。
- 範例 3（邊界）：`[[0]]`，回傳 `0`，起點就是終點。
- 範例 4（邊界）：`[[0,1],[1,0]]`，`k = 0` 時回傳 `-1`，`k = 1` 時回傳 `2`。

### 提示

> [!tip]- 提示 1
> 沒有 k 的話這就是普通的格子 BFS。加上 k 之後，兩次走到同一個格子，未來能做的事一樣嗎？

> [!tip]- 提示 2
> 不一樣：剩 2 次消除和剩 0 次消除，能走的路完全不同。所以 BFS 的狀態要是 (r, c, 剩餘消除次數)，visited 也要記這三個值。估算一下狀態數，在限制內嗎？

> [!tip]- 提示 3
> 兩個優化。第一，同一格若曾經以更多的剩餘次數到過，現在的狀態就被支配了，可以把 visited 縮成每格一個 `best[r][c]`。第二，曼哈頓距離 m + n − 2 的路徑最多經過 m + n − 3 個中間格，k 至少這麼多時直接回傳 m + n − 2。

### 詳解

**為什麼只記位置的 visited 行不通**。最直覺的修改是在普通 BFS 裡多帶一個 `rem`，遇到障礙就減一，但 visited 仍然只記 (r, c)。問題在於：BFS 第一次到達某格時，抵達它的那條路徑可能剛好**浪費了消除次數**，例如繞過去本來不需要打牆、卻因為打牆的路比較早到而先佔住了這一格；之後那條沒打牆、剩餘次數較多的路徑再到這格時被擋掉，而它正是唯一能在後面打穿關鍵障礙的路徑。下面的視覺化給出一個具體的反例。

**突破點：把剩餘資源放進狀態**。這是 15.5 節的狀態圖：節點是 (r, c, rem)，從 (r, c, rem) 可以走到鄰格 (r', c', rem − grid[r'][c'])，前提是結果 ≥ 0。每條邊代價都是一步，所以在這張狀態圖上做 BFS，第一次取出任何 (m − 1, n − 1, ·) 的狀態時，步數就是答案。狀態數是 m · n · (k + 1)，每個狀態 4 條邊。

**支配剪枝**。同一格、步數不多於現在、而剩餘次數不少於現在的狀態，能做到現在這個狀態能做的一切。BFS 按步數遞增處理，所以任何先前記錄在 (r, c) 的狀態步數都 ≤ 現在；只要現在的 `rem` 沒有超過該格記錄過的最大 `rem`，就被支配，可以丟掉。於是 visited 變成一個整數陣列 `best[r][c]`，新狀態只有在 `rem > best[r][c]` 時才入隊。程式中 `best` 初始為 -1，剛好讓「rem = 0 卻走進障礙物」產生的 `nrem = -1` 自動被 `nrem > best` 擋下，不需要另外檢查 `nrem >= 0`。

**提早結束**。從 (0, 0) 到 (m − 1, n − 1) 的任何路徑至少要 m + n − 2 步；一條只往右和往下的路徑恰好這麼長，經過 m + n − 3 個中間格（扣掉起點和終點）。如果 `k >= m + n - 3`，就算這些格子全是障礙物也能打穿，答案直接是 m + n − 2。這個檢查同時把狀態數的 k 壓到 m + n − 3 以下，最差狀態數從 m · n · (m · n + 1) 降為 O(m · n · (m + n))。

```text
反例：只用 (r, c) 當 visited 會出錯，k = 1，鄰居順序 下、上、右、左
0 0 1 1
1 0 1 0
正確答案：(0,0) → (0,1) → (1,1) → 打穿 (1,2) → (1,3)，4 步

只記位置的 BFS：
第 1 步  (1,0) 打牆 rem=0、(0,1) rem=1
第 2 步  從 (1,0) 先到 (1,1)，rem=0 → (1,1) 被標記
         從 (0,1) 再到 (1,1) 被擋掉（而它 rem=1）
第 3 步  (1,1) rem=0 打不穿 (1,2) → 最後回傳 -1  ✗

範例 1 用 (r, c, rem) + best 剪枝的 BFS（列出每一步新入隊的狀態）
步數 0  (0,0,1)
步數 1  (0,1,1) (1,0,0)
步數 2  (0,2,1) (1,1,0) (2,0,0)
步數 3  (1,2,1) (2,1,0) (3,0,0) …          (1,2) 同一層先 rem=0 後 rem=1，兩個都入隊
步數 4  (2,2,1) (4,0,0) …
步數 5  (3,2,0) (2,1,1) (4,1,0)            (2,1) 第二次入隊：rem 從 0 提高到 1
步數 6  (4,2,0) = 終點 → 回傳 6
```

`(2,1)` 在第 3 步以 rem = 0 到達、第 5 步以 rem = 1 再次到達，這正是支配剪枝允許的情況：步數多了，但剩餘資源也多了，兩者互不支配，必須保留。

### 解法

```python
import random
from collections import deque


def shortest_path(grid: list[list[int]], k: int) -> int:
    m, n = len(grid), len(grid[0])
    if k >= m + n - 3:                       # 曼哈頓路徑最多經過 m+n-3 個中間格，全打穿也夠
        return m + n - 2
    best = [[-1] * n for _ in range(m)]      # best[r][c] = 抵達 (r, c) 時剩餘最多的消除次數
    best[0][0] = k
    queue = deque([(0, 0, k)])
    steps = 0
    while queue:
        for _ in range(len(queue)):
            r, c, rem = queue.popleft()
            if r == m - 1 and c == n - 1:
                return steps
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if 0 <= nr < m and 0 <= nc < n:
                    nrem = rem - grid[nr][nc]
                    if nrem > best[nr][nc]:          # 只有「剩更多」才值得再走一次
                        best[nr][nc] = nrem
                        queue.append((nr, nc, nrem))
        steps += 1
    return -1


def brute(grid: list[list[int]], k: int) -> int:
    """完整的 (r, c, rem) 狀態 BFS，不做支配剪枝。"""
    m, n = len(grid), len(grid[0])
    seen = {(0, 0, k)}
    queue = deque([(0, 0, k, 0)])
    while queue:
        r, c, rem, d = queue.popleft()
        if (r, c) == (m - 1, n - 1):
            return d
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < m and 0 <= nc < n:
                nrem = rem - grid[nr][nc]
                if nrem >= 0 and (nr, nc, nrem) not in seen:
                    seen.add((nr, nc, nrem))
                    queue.append((nr, nc, nrem, d + 1))
    return -1


g = [[0, 0, 0],
     [1, 1, 0],
     [0, 0, 0],
     [0, 1, 1],
     [0, 0, 0]]
assert shortest_path(g, 1) == 6
assert shortest_path([[0, 1, 1], [1, 1, 1], [1, 0, 0]], 1) == -1
assert shortest_path([[0]], 0) == 0
assert shortest_path([[0, 1], [1, 0]], 0) == -1
assert shortest_path([[0, 1], [1, 0]], 1) == 2
assert shortest_path([[0, 0, 1, 1], [1, 0, 1, 0]], 1) == 4      # 只記位置會錯的反例
for _ in range(400):
    m, n = random.randint(1, 6), random.randint(1, 6)
    grid = [[random.choice((0, 0, 1)) for _ in range(n)] for _ in range(m)]
    grid[0][0] = grid[m - 1][n - 1] = 0
    kk = random.randint(0, 4)
    assert shortest_path(grid, kk) == brute(grid, kk)
print("all tests passed")
```

### 複雜度與邊界

時間與空間 O(m · n · K)，K = min(k, m + n − 3) + 1 是剩餘次數的可能值數：每格最多以 K 種不同的 `rem` 入隊（每次入隊 `best` 嚴格變大），每次檢查 4 個鄰居。40 × 40 時最多約 1600 × 77 ≈ 1.2 × 10⁵ 個狀態。`best` 本身只需 O(mn)，但 queue 最差仍可能裝 O(m · n · K) 個狀態。邊界情況：1 × 1 的格子 m + n − 3 = −1，任何 k 都觸發提早回傳 0；k = 0 時退化成普通 BFS；終點保證是 0，所以抵達終點時不需要再檢查 `rem`。如果拿掉提早結束的檢查，程式仍然正確，只是 k 很大時會慢很多。

### Follow-up

> [!question]- F1. 如果不限制 k，而是問「最少要消除幾個障礙物才能到終點」呢（2290. Minimum Obstacle Removal to Reach Corner）？
> 這時代價不是步數，而是打穿的障礙物數：走進空地代價 0、走進障礙物代價 1。這是 0-1 BFS 的標準情境：用 deque，代價 0 的鄰居放到前端（`appendleft`）、代價 1 的放到尾端，第一次取出終點時的代價就是答案，O(mn)。也可以用 Dijkstra，O(mn log(mn))。注意這裡的狀態只需要位置，因為我們最小化的就是消除次數本身，沒有另一個要同時追蹤的資源。

> [!question]- F2. 能不能用 A* 加速？
> 可以。A* 是 Dijkstra（在這題等同 BFS）加上一個啟發函數 h，優先展開「已走步數 + h」最小的狀態。曼哈頓距離 `(m − 1 − r) + (n − 1 − c)` 永遠不會高估真正的剩餘步數（admissible），所以 A* 找到的仍是最短路。在障礙物稀疏、k 很小的格子上，A* 會優先往終點方向走，展開的狀態數通常少很多；最差情況下複雜度不變，還多了 heap 的 log 因子。面試中可以作為加分的討論，但主解法用 BFS 就夠了。

> [!question]- F3. 如果要回傳實際路徑（以及在哪裡消除障礙物）呢？
> 對每個狀態 (r, c, rem) 記錄它的前一個狀態，用 dict 存 `parent[(r, c, rem)] = (pr, pc, prem)`。找到終點後沿著 parent 往回走，路徑上 `rem` 減少的那幾步就是消除障礙物的位置。注意這裡不能只用 `best[r][c]` 存 parent，因為同一格可能以不同的 `rem` 出現在不同的路徑上；parent 必須以完整狀態為 key，空間是 O(m · n · K)。

> [!question]- F4. 如果有兩種資源（例如可以打穿牆 k 次、也可以跳過水 j 次）呢？
> 狀態變成 (r, c, 剩餘打牆次數, 剩餘跳水次數)，狀態數 m · n · (k + 1) · (j + 1)。支配剪枝仍然可以做，但不再是單一整數的比較：一個狀態被支配，當且僅當同一格有另一個步數不多、且**兩種**剩餘都不少的狀態。這是二維的 Pareto 前緣，不能用一個 `best[r][c]` 表示；實作上最簡單的是直接用四維 visited，若要剪枝就對每格維護一份 Pareto 前緣列表。面試時能說出「多種資源時支配關係只是偏序」就足夠展現理解。

### 心得

關鍵突破是「兩次到同一格，剩下的消除次數不同，未來就不同」，所以狀態要是 (r, c, rem)，而支配關係讓 visited 縮成每格一個 `best` 值。它是 15.5 節狀態圖的第一個例子，和難題 4、5 的差別在於這裡的額外資訊有全序（越多越好），所以能剪枝；鑰匙集合沒有全序，就只能完整記錄。面試時先用一個小反例說明為什麼只記位置會錯，再提出擴充狀態與估算狀態數，最後補上提早結束的檢查；能把「BFS 按步數遞增，所以先記錄的狀態步數一定不多」這句話說清楚，剪枝的正確性就站得住。

## 難題 4｜847. Shortest Path Visiting All Nodes｜Hard

### 題目

給一張有 n 個節點（編號 0 到 n − 1）的**連通無向圖**，以鄰接串列 `graph` 表示，`graph[i]` 是節點 i 的所有鄰居。請回傳一條**拜訪所有節點**的路徑最少需要幾條邊。你可以從任何節點出發、在任何節點結束，可以重複拜訪節點，也可以重複使用邊。限制：`1 <= n <= 12`，圖中沒有自環與重複邊。

- 範例 1：星形圖 `graph = [[1,2,3],[0],[0],[0]]`（0 是中心），回傳 `4`，例如 `1 → 0 → 2 → 0 → 3`。
- 範例 2：`graph = [[1],[0,2,4],[1,3,4],[2],[1,2]]`，回傳 `4`，例如 `0 → 1 → 4 → 2 → 3`。
- 範例 3（邊界）：`graph = [[]]`，只有一個節點，回傳 `0`。
- 範例 4：一條鏈 `0 – 1 – 2 – 3`，回傳 `3`，從一端走到另一端；若從中間出發就需要折返，會更長。

### 提示

> [!tip]- 提示 1
> 因為可以重複拜訪，普通的 visited（每個節點只走一次）一定不對：範例 1 必須經過中心三次。那麼「同一個節點走第二次」什麼時候是有意義的？

> [!tip]- 提示 2
> 第二次站在同一個節點時，如果「已經拜訪過的節點集合」不同，未來要做的事就不同。所以狀態是 (目前節點, 已拜訪集合)。n ≤ 12，集合可以用一個 12 位元的 bitmask 表示，狀態有多少個？

> [!tip]- 提示 3
> 在 (node, mask) 上做 BFS，每條邊代價 1。起點可以任選，所以一開始把所有 (i, 1 << i) 一起放進第 0 層（multi-source）。第一個 mask 等於全集的狀態，它所在的層數就是答案。

### 詳解

**為什麼直覺做法不行**。這題很像旅行推銷員（TSP）：要經過所有點。暴力法是枚舉 n! 種拜訪順序，每兩個相鄰目標之間走最短路（先用 BFS 或 Floyd–Warshall 算出兩兩距離），12! ≈ 4.8 × 10⁸，太慢。而普通 BFS 以節點為 visited 時，每個節點只能進一次，星形圖這種「必須反覆回到中心」的結構就走不出來。真正的障礙是：**只看「目前在哪」不足以描述進度**。

**突破點：狀態 = (目前節點, 已拜訪集合)**。兩個走法若目前都在節點 u、而且已拜訪的集合都是 S，那麼它們接下來的最佳走法完全相同，只需要保留步數較少的那個。所以把 (u, S) 當成狀態圖的節點：從 (u, S) 沿著原圖的邊走到鄰居 v，就到了 (v, S ∪ {v})，代價 1。原問題變成「從任一個 (i, {i}) 出發，到任一個 (·, 全集) 的最短路」，這是等權圖的最短路，用 BFS。狀態數 n · 2ⁿ = 12 × 4096 = 49152，每個狀態最多 n − 1 條邊，總共不超過 54 萬次轉移。

**Multi-source 起點**。可以從任何節點出發，等同於加一個虛擬起點、連到每個 (i, {i}) 代價 0，也就是把它們全部放進 BFS 的第 0 層。這比對每個起點各跑一次 BFS 快 n 倍。

**正確性**。狀態圖中的每條路徑對應原圖中的一條走法（可以重複節點與邊），反之亦然；mask 只會增加，等於全集表示所有節點都拜訪過了。BFS 按步數遞增處理狀態，第一個被取出的全集狀態，其步數就是所有走法中最少的。

```text
範例 1：星形圖，0 是中心。mask 的寫法是 bit3 bit2 bit1 bit0（節點 3 在最左）

第 0 層  (0,0001) (1,0010) (2,0100) (3,1000)          所有起點一起
第 1 層  (1,0011) (2,0101) (3,1001)                   從中心往外
         (0,0011) (0,0101) (0,1001)                   從葉子回中心
第 2 層  (2,0111) (3,1011) (1,0111) (3,1101) (1,1011) (2,1101)
第 3 層  (0,0111) (0,1011) (0,1101)                   必須回到中心才能去下一個葉子
第 4 層  (3,1111) …  ← mask = 1111，回傳 4

其中一條：(1,0010) → (0,0011) → (2,0111) → (0,0111) → (3,1111)
對應原圖：1 → 0 → 2 → 0 → 3
注意 (0,0011) 和 (0,0111) 都站在節點 0，但 mask 不同，所以是不同的狀態；
若只用節點當 visited，第二次回到 0 會被擋掉，永遠拿不到 1111。
```

### 解法

```python
import itertools
import random
from collections import deque


def shortest_path_length(graph: list[list[int]]) -> int:
    n = len(graph)
    full = (1 << n) - 1
    seen = [[False] * (1 << n) for _ in range(n)]
    queue = deque()
    for i in range(n):                        # 每個節點都可以當起點：multi-source
        seen[i][1 << i] = True
        queue.append((i, 1 << i))
    steps = 0
    while queue:
        for _ in range(len(queue)):
            u, mask = queue.popleft()
            if mask == full:
                return steps
            for v in graph[u]:
                nmask = mask | (1 << v)
                if not seen[v][nmask]:
                    seen[v][nmask] = True
                    queue.append((v, nmask))
        steps += 1
    return -1                                 # 題目保證連通，不會走到這裡


def brute(graph: list[list[int]]) -> int:
    """先算兩兩最短距離，再枚舉拜訪順序（TSP 路徑版）。"""
    n = len(graph)
    INF = float("inf")
    d = [[0 if i == j else INF for j in range(n)] for i in range(n)]
    for u in range(n):
        for v in graph[u]:
            d[u][v] = 1
    for k in range(n):
        for i in range(n):
            for j in range(n):
                d[i][j] = min(d[i][j], d[i][k] + d[k][j])
    return min(sum(d[p[i]][p[i + 1]] for i in range(n - 1)) for p in itertools.permutations(range(n)))


assert shortest_path_length([[1, 2, 3], [0], [0], [0]]) == 4
assert shortest_path_length([[1], [0, 2, 4], [1, 3, 4], [2], [1, 2]]) == 4
assert shortest_path_length([[]]) == 0                       # 只有一個節點
assert shortest_path_length([[1], [0]]) == 1
assert shortest_path_length([[1], [0, 2], [1, 3], [2]]) == 3  # 一條鏈：從端點走到另一端
for _ in range(200):
    n = random.randint(1, 6)
    edges = {(i, random.randrange(i)) for i in range(1, n)}    # 先保證連通
    for _ in range(random.randint(0, 4)):
        a, b = random.sample(range(n), 2) if n > 1 else (0, 0)
        if a != b:
            edges.add((max(a, b), min(a, b)))
    graph = [[] for _ in range(n)]
    for a, b in edges:
        graph[a].append(b)
        graph[b].append(a)
    assert shortest_path_length(graph) == brute(graph)
print("all tests passed")
```

`brute` 用的是「兩兩最短距離 + 枚舉順序」：最佳走法一定可以拆成「依某個順序第一次拜訪每個節點，相鄰兩個之間走最短路」，所以它是正確的對照，只是 O(n! · n)。

### 複雜度與邊界

時間 O(2ⁿ · n²)：共 n · 2ⁿ 個狀態，每個狀態展開最多 n − 1 個鄰居（更精確地說是 O(2ⁿ · E)，E 是邊數）。空間 O(n · 2ⁿ)，`seen` 表與 queue。n = 12 時約 5 × 10⁴ 個狀態、數十萬次轉移，Python 也能在很短時間內跑完。邊界情況：n = 1 時起始狀態就是全集，第 0 層就回傳 0；兩個節點回傳 1；題目保證連通，所以一定有解，若不保證連通，BFS 結束都沒碰到全集就回傳 -1。`seen` 用二維 list 比用 set 存 tuple 快很多，這在 Python 中值得一提。

### Follow-up

> [!question]- F1. 如果規定必須從節點 0 出發呢？如果還要回到起點呢？
> 必須從 0 出發時，第 0 層只放 (0, 1)，其餘不變，複雜度相同。若還要回到起點（TSP 的「巡迴」版本），終止條件改成「取出的狀態是 (0, 全集)」，而不是任何全集狀態；因為允許重複經過，拿到全集後 BFS 會繼續擴展直到走回 0。兩種變形都是把起點或終點的集合縮小，狀態圖本身不變，這正是狀態圖建模的好處。

> [!question]- F2. 如果邊有權重（不同的長度）呢？
> BFS 失效，因為步數最少不等於總長度最短。有兩種做法：一是在同一個 (node, mask) 狀態圖上跑 Dijkstra（第 18 章），O(n · 2ⁿ · n · log(n · 2ⁿ))；二是 Held–Karp 位元 DP：先用 Floyd–Warshall 算出兩兩最短距離 O(n³)，再令 `dp[mask][u]` = 拜訪完 mask 且停在 u 的最短距離，轉移 `dp[mask | 1<<v][v] = min(dp[mask][u] + d[u][v])`，O(2ⁿ · n²)。第二種沒有 heap，常數更小，也是第 24 章 bitmask DP 的標準範例。

> [!question]- F3. 如果 n 是 50 甚至 1000 呢？
> 一般圖上這個問題是 NP-hard：它包含了「是否存在漢彌爾頓路徑」（答案是否等於 n − 1），所以不要期待多項式時間的精確解，2ⁿ 的狀態數是本質。若圖是**樹**，則有漂亮的公式：每條邊至少要走一次，不必回頭的邊最多是一條最長路徑，所以答案是 2(n − 1) − 直徑，直徑用兩次 BFS 求出，O(n)。面試時能指出一般情況的困難度、並給出特殊結構的解，比硬套 bitmask 更有說服力。

> [!question]- F4. 如果只需要拜訪其中 k 個指定的節點（k ≤ 12），但整張圖有 10⁴ 個節點呢？
> 狀態 (node, mask) 會變成 10⁴ × 2¹²，約 4 × 10⁷，太大。改成兩階段：先從每個指定節點各跑一次 BFS，得到指定節點之間的兩兩最短距離（k 次 BFS，O(k · (V + E))）；再在這 k 個點上做 F2 的 Held–Karp DP，O(2ᵏ · k²)。關鍵觀察是：中間經過的非指定節點只是「通道」，不需要出現在 mask 裡。難題 5 的 F3 也是同樣的「先縮成關鍵點的小圖」技巧。

### 心得

關鍵突破是看出「目前在哪」不足以描述進度，必須加上「已拜訪哪些點」，而 n ≤ 12 這個極小的限制就是在提示 bitmask。它和難題 3 都是把資訊放進狀態，但這裡的 mask 沒有支配關係（{0, 1} 和 {0, 2} 無法比較），所以只能完整記錄 n · 2ⁿ 個狀態。面試時先說明為什麼普通 visited 不行（星形圖要回到中心三次），再定義狀態與估算狀態數，最後提到 multi-source 起點；如果面試官追問權重，就自然接到 Held–Karp DP，這展現了你知道 BFS 與 DP 在這裡是同一個狀態空間的兩種走法。

## 難題 5｜864. Shortest Path to Get All Keys｜Hard

### 題目

給一個 m × n 的格子 `grid`（以字串列表表示），每格是以下之一：`'.'` 空地、`'#'` 牆、`'@'` 起點、小寫字母 `'a'`–`'f'` 是鑰匙、大寫字母 `'A'`–`'F'` 是鎖。你從起點出發，每步往上下左右移動一格，不能走出格子、不能穿牆；走到鑰匙格就自動撿起；只有持有對應的小寫鑰匙時才能走進鎖的格子。鑰匙的種類是英文字母的前 K 種，`1 <= K <= 6`，每種鑰匙恰好一把、每種鎖恰好一個。請回傳撿齊所有鑰匙的最少步數；做不到則回傳 -1。限制：`1 <= m, n <= 30`。

- 範例 1：`["@.a..", "###.#", "b.A.B"]` 回傳 `8`：先往右兩步拿 `a`，再往右一步、往下兩步到 (2,3)，接著往左一步用 `a` 穿過 `A`，最後再往左兩步拿到 `b`（2 + 3 + 1 + 2 = 8）。
- 範例 2：`["@..aA", "..B#.", "....b"]` 回傳 `6`：先往右三步拿 `a`，再往右一步用 `a` 穿過 `A`，往下兩步拿到 `b`；若先去拿 `b`，從左邊繞過 `B` 走到 `b` 就要 6 步，之後還得回頭拿 `a`。
- 範例 3（邊界）：`["@Aa"]` 回傳 `-1`：鑰匙 `a` 被它自己的鎖 `A` 擋住。
- 範例 4（邊界）：`["a@b"]` 回傳 `3`：先往左拿 `a`（1 步），再走回頭往右拿 `b`（2 步）；必須重複經過起點。

### 提示

> [!tip]- 提示 1
> 最短步數、每步代價相同 → BFS。但範例 4 必須走回頭路經過起點，所以只記位置的 visited 不夠。兩次站在同一格，什麼不一樣？

> [!tip]- 提示 2
> 手上的鑰匙不同，能通過的鎖就不同。狀態是 (r, c, 持有的鑰匙集合)，K ≤ 6，集合用 6 位元的 bitmask 表示，總狀態數是多少？

> [!tip]- 提示 3
> 在 (r, c, keys) 上做逐層 BFS。走到鎖時檢查 `keys` 的對應位元；走到鑰匙時把位元打開。第一個 `keys` 等於全集的狀態所在層數就是答案。

### 詳解

**為什麼只記位置不行**。普通格子 BFS 中每格只進一次，但這題常常必須走回頭路：拿到鑰匙後回到原本過不去的鎖前面。範例 4 中，起點在第 1 步就被標記，拿到 `a` 之後要回到起點再往右，卻因為起點已被拜訪而被擋掉，BFS 會錯誤地回傳 -1。根本原因和難題 3、4 相同：**同一個位置，手上的資源不同，未來能走的路就不同**。

**突破點：狀態 = (r, c, keys)**。keys 是一個 K 位元的 bitmask，第 i 位為 1 代表持有第 i 把鑰匙。從 (r, c, keys) 走到鄰格 (r', c')：牆不能走；鎖要檢查 `keys` 中對應的位元；鑰匙格把位元打開得到新的 `keys'`；其餘不變。狀態數 m · n · 2ᴷ ≤ 900 × 64 = 57600，每個狀態 4 條邊，非常小。和難題 3 不同的是，鑰匙集合之間只有偏序（{a} 和 {b} 互不支配），所以不能用一個 `best[r][c]` 剪枝，visited 必須記完整的三元組。

**一個常見的誤解**：「是不是應該按照某種順序拿鑰匙，用 K! 種順序分別計算？」那是另一種正確的做法（見 F3），但在格子上直接做狀態 BFS，所有順序都被 BFS 同時探索，不需要枚舉。BFS 的層數保證第一個 `keys` 為全集的狀態就是最少步數，正確性與 15.3 節的論證完全相同，只是節點換成了三元組。

**全集怎麼算**。不要假設 K 種鑰匙就是 `a` 到第 K 個字母，直接掃描格子，把出現的每個小寫字母的位元 OR 進 `full`。如果格子裡沒有任何鑰匙，`full = 0`，起始狀態就是全集，回傳 0。

```text
範例 1：["@.a..", "###.#", "b.A.B"]，bit1 bit0 = b a

     c=0 c=1 c=2 c=3 c=4
r=0   @   .   a   .   .
r=1   #   #   #   .   #
r=2   b   .   A   .   B

步數  狀態 (r, c, keys)        說明
 0    (0,0,00)                起點
 1    (0,1,00)
 2    (0,2,01)                撿到 a，keys 變成 01；(0,2,00) 從未存在
 3    (0,3,01)  (0,1,01)      (0,1) 以 keys=01 再次被拜訪，是新狀態
 4    (1,3,01)  (0,4,01)  (0,0,01)
 5    (2,3,01)
 6    (2,2,01)  (2,4)?        (2,2) 是 A，持有 a → 可通過；(2,4) 是 B，沒有 b → 擋住
 7    (2,1,01)
 8    (2,0,11)                撿到 b，keys = 11 = full → 回傳 8
```

注意第 3 步的 `(0,1,01)`：位置 (0,1) 在第 1 步已經以 `keys = 00` 拜訪過，但現在手上多了 `a`，是不同的狀態，必須允許。範例 4 的回頭路也是同樣的道理。

### 解法

```python
import heapq
import random
from collections import deque


def shortest_path_all_keys(grid: list[str]) -> int:
    m, n = len(grid), len(grid[0])
    full = 0
    for r in range(m):
        for c in range(n):
            ch = grid[r][c]
            if ch == "@":
                start = (r, c)
            elif ch.islower():
                full |= 1 << (ord(ch) - ord("a"))
    seen = {(start[0], start[1], 0)}
    queue = deque([(start[0], start[1], 0)])
    steps = 0
    while queue:
        for _ in range(len(queue)):
            r, c, keys = queue.popleft()
            if keys == full:
                return steps
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if not (0 <= nr < m and 0 <= nc < n):
                    continue
                ch = grid[nr][nc]
                if ch == "#":
                    continue
                if ch.isupper() and not keys >> (ord(ch) - ord("A")) & 1:
                    continue                          # 鎖住而且沒有對應的鑰匙
                nkeys = keys | (1 << (ord(ch) - ord("a"))) if ch.islower() else keys
                if (nr, nc, nkeys) not in seen:
                    seen.add((nr, nc, nkeys))
                    queue.append((nr, nc, nkeys))
        steps += 1
    return -1


def via_key_points(grid: list[str]) -> int:
    """F3 的做法：只在起點與鑰匙之間建圖，再對 (點, 鑰匙集合) 做 Dijkstra。"""
    m, n = len(grid), len(grid[0])
    points = {grid[r][c]: (r, c) for r in range(m) for c in range(n) if grid[r][c] == "@" or grid[r][c].islower()}
    full = 0
    for ch in points:
        if ch != "@":
            full |= 1 << (ord(ch) - ord("a"))

    def bfs(src: tuple[int, int], keys: int) -> dict[str, int]:
        dist = {src: 0}
        queue = deque([src])
        found = {}
        while queue:
            r, c = queue.popleft()
            ch = grid[r][c]
            if ch.islower() and (r, c) != src:
                found[ch] = dist[(r, c)]
                if not keys >> (ord(ch) - ord("a")) & 1:
                    continue                          # 撿到新鑰匙就停在這裡，交給 Dijkstra
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if 0 <= nr < m and 0 <= nc < n and (nr, nc) not in dist:
                    t = grid[nr][nc]
                    if t == "#" or (t.isupper() and not keys >> (ord(t) - ord("A")) & 1):
                        continue
                    dist[(nr, nc)] = dist[(r, c)] + 1
                    queue.append((nr, nc))
        return found

    best = {("@", 0): 0}
    heap = [(0, "@", 0)]
    while heap:
        d, p, keys = heapq.heappop(heap)
        if keys == full:
            return d
        if d > best[(p, keys)]:
            continue
        for ch, w in bfs(points[p], keys).items():
            nk = keys | (1 << (ord(ch) - ord("a")))
            if d + w < best.get((ch, nk), float("inf")):
                best[(ch, nk)] = d + w
                heapq.heappush(heap, (d + w, ch, nk))
    return -1


for f in (shortest_path_all_keys, via_key_points):
    assert f(["@.a..", "###.#", "b.A.B"]) == 8
    assert f(["@..aA", "..B#.", "....b"]) == 6
    assert f(["@Aa"]) == -1                   # 鑰匙被自己的鎖擋住
    assert f(["@"]) == 0                      # 沒有鑰匙
    assert f(["a@b"]) == 3                    # 先拿近的、走回頭路
for _ in range(300):
    m, n = random.randint(1, 5), random.randint(1, 5)
    cells = [random.choice("..#") for _ in range(m * n)]
    kinds = random.randint(0, min(3, (m * n - 1) // 2))
    pos = random.sample(range(m * n), 1 + 2 * kinds)
    cells[pos[0]] = "@"
    for i in range(kinds):
        cells[pos[1 + 2 * i]] = "abc"[i]
        cells[pos[2 + 2 * i]] = "ABC"[i]
    g = ["".join(cells[r * n:(r + 1) * n]) for r in range(m)]
    assert shortest_path_all_keys(g) == via_key_points(g)
print("all tests passed")
```

主解法是 `shortest_path_all_keys`；`via_key_points` 是 F3 描述的另一種做法，兩者在隨機格子上互相對照。

### 複雜度與邊界

時間與空間 O(m · n · 2ᴷ)：每個 (r, c, keys) 狀態最多入隊一次，每次檢查 4 個鄰居。30 × 30、K = 6 時最多 57600 個狀態。邊界情況：沒有鑰匙時 `full = 0`，第 0 層就回傳 0；鑰匙被自己的鎖或牆完全擋住時，BFS 會把所有可達狀態走完後回傳 -1；鎖對應的鑰匙不存在於格子中時（題目保證不會發生），那扇鎖永遠打不開，程式也自然處理。位元運算的優先順序要小心：`keys >> i & 1` 在 Python 中是 `(keys >> i) & 1`，因為位移的優先順序高於 `&`；不確定時加括號。`seen` 用 set 存 tuple 已經夠快；若要更快，可以開 `m × n × 2ᴷ` 的布林陣列。

### Follow-up

> [!question]- F1. 如果鑰匙用一次就會消失（打開鎖之後鎖保持開啟）呢？
> 每種字母現在有三種狀態：還沒撿、撿了但還沒用、已經用掉（門已開），所以 keys 要擴充成每種字母 2 個位元，或兩個 mask：`held` 與 `opened`。走進鎖格時：若 `opened` 已有它就直接通過；否則需要 `held` 有它，然後把它從 `held` 移到 `opened`。狀態數變成 m · n · 3ᴷ，K = 6 時 900 × 729 ≈ 6.6 × 10⁵，仍可接受。這個變形考的是你能否精確描述「什麼資訊會影響未來」，而不只是套用 bitmask。

> [!question]- F2. 如果撿齊鑰匙之後還要走到某個出口（或回到起點）呢？
> 狀態圖不變，只改終止條件：取出的狀態要同時滿足 `keys == full` 且位置是出口。因為 BFS 會在撿齊鑰匙之後繼續擴展 `keys = full` 的狀態，自然會找到到出口的最短路。也可以分兩段：先算撿齊鑰匙的所有終點狀態，再從它們做 multi-source BFS 到出口，但直接改終止條件最簡單，複雜度仍是 O(m · n · 2ᴷ)。

> [!question]- F3. 如果格子很大（例如 1000 × 1000），但鑰匙只有 K ≤ 6 把呢？
> m · n · 2ᴷ = 6.4 × 10⁷，在 Python 中太慢。觀察到真正的「決策點」只有起點和 K 把鑰匙：兩個決策點之間一定走最短路。所以把問題縮成 K + 1 個關鍵點上的圖：從每個關鍵點、以目前持有的鑰匙做 BFS，算出到其他鑰匙的距離（遇到新鑰匙就停，因為撿起它會改變狀態），再在 (關鍵點, keys) 這 (K + 1) · 2ᴷ 個狀態上跑 Dijkstra（邊權是 BFS 算出的距離）。上面的 `via_key_points` 就是這個做法。BFS 的次數最多 (K + 1) · 2ᴷ 次，每次 O(mn)，但實際上只有可達的 (點, keys) 組合才會觸發，通常遠少於上界；若同一組 (點, keys) 的 BFS 結果做快取，就不會重複計算。

> [!question]- F4. 如果只需要撿齊其中任意 t 把鑰匙（t < K）呢？
> 終止條件改成 `popcount(keys) >= t`，也就是 `keys.bit_count() >= t`（Python 3.10 起）。狀態圖和 BFS 都不變，第一個滿足條件的狀態的層數就是答案。這說明了 bitmask 狀態的好處：目標條件可以是任何關於集合的判斷（包含某些特定鑰匙、至少幾把、某兩把不能同時持有），只要在取出狀態時檢查即可，搜尋本身不必修改。

### 心得

關鍵突破是把「手上有哪些鑰匙」放進狀態，讓走回頭路變成合法的新節點；K ≤ 6 是在提示 2ᴷ 很小。它結合了難題 3 的「資源影響未來」與難題 4 的「bitmask 記錄集合」：位置像 1293、集合像 847。面試時先用範例 4（`a@b`）說明為什麼普通 visited 會失敗，再定義三元組狀態並算出 m · n · 2ᴷ 的上界，最後寫逐層 BFS；被問到大格子時，提出「只在關鍵點之間建圖再 Dijkstra」，就展現了你知道何時該把狀態空間縮小。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 連通元件、整塊標記 | 「有幾塊」「最大的一塊」「把某區域全部改掉」 | 外層掃描每個未拜訪節點，內層 DFS／BFS 標記整塊 | 核心題 1（200）、695、547（第 17 章核心題 1）、733 Flood Fill |
| 圖的走訪與複製 | 給一個節點，要處理整張可能有環的圖 | hash map「原節點 → 新節點」兼任 visited | 核心題 2（133）、138（第 11 章難題 3）、1490 |
| 單源等權最短路 | 「最少幾步」，每步代價相同 | BFS，入隊時標記；需要路徑時記 parent | 1091 Shortest Path in Binary Matrix、752 Open the Lock、433 |
| Multi-source BFS | 多個起點同時擴散；「到最近的某物」 | 所有源頭放進第 0 層，等同虛擬超級源點 | 核心題 3（994）、542 01 Matrix、286 Walls and Gates、1162 |
| 反向搜尋 | 起點是「每一格」，終點是固定集合（邊界、海洋） | 從終點集合出發，沿反向邊搜一次 | 核心題 4（417）、核心題 5（130）、1020、1254 |
| 隱式圖 | 節點是字串或狀態，鄰居由規則產生 | 不建圖；用通配符桶或枚舉產生鄰居 | 難題 1（127）、433、752、773 Sliding Puzzle |
| 雙向 BFS | 起點終點都已知、分支度大 | 兩個前緣，每次擴展較小的一邊 | 難題 1（127）、752 |
| 列舉所有最短路徑 | 「回傳所有最短的…」 | BFS 建分層 DAG（按層標記），從終點回溯 | 難題 2（126） |
| 狀態 + 資源 | 「最多可以…k 次」，資源影響未來 | 狀態 (位置, 剩餘資源)；有全序時用 `best` 支配剪枝 | 難題 3（1293）、787（第 18 章核心題 2） |
| 狀態 + 集合 | 要拜訪所有點、撿齊所有東西，數量 ≤ 12 | 狀態 (位置, bitmask)，multi-source 起點 | 難題 4（847）、難題 5（864）、943（第 24 章難題 2） |
| 0-1 BFS | 邊權只有 0 和 1 | deque：代價 0 放前端、代價 1 放尾端 | 2290、1368（第 18 章難題 2） |

**下限與上限**。最簡單的形式是「格子 + 連通元件」（200、733），考的只是 visited 和邊界檢查寫對；再往上一層是 multi-source 與反向搜尋（994、417、130），難點從寫程式轉到**選對起點**：從哪裡出發、往哪個方向搜，才能一次搜完。上限的題目難在三個地方：第一，**圖是隱式的**，節點要自己定義、鄰居要自己產生，而找鄰居的成本可能才是瓶頸（127）；第二，**visited 的語意要改**，例如 126 要按層標記才不會丟失父節點；第三，**節點要擴充成狀態**，並且要能估算狀態數、看出能否支配剪枝（1293、847、864）。這三種困難常常疊加，例如 864 同時是狀態圖、bitmask，大格子版本還要先縮成關鍵點圖再跑 Dijkstra。

**與其他 pattern 的關係**。第 12 章的二元樹 DFS／BFS 是本章的特例：樹沒有環，所以不需要 visited。連通性問題也可以用 union-find（第 17 章）：一次性計算時 DFS 更簡單，但若邊是逐步加入的（305 Number of Islands II）或要反覆查詢兩點是否連通，union-find 更好。有向圖的先後關係、環偵測與拓撲排序在第 16 章，用的是 DFS 的後序或 BFS 的入度（Kahn 演算法）。邊有權重時 BFS 就不再正確，要換成 Dijkstra（第 18 章）；邊權只有 0 和 1 時用 0-1 BFS。狀態 + bitmask 的 BFS 和 bitmask DP（第 24 章）是同一個狀態空間的兩種走法：等權最短路用 BFS，帶權或有更複雜的轉移時用 DP。列舉所有路徑（而不只是最短）屬於 backtracking（第 19 章）。

**容易混淆之處**。第一，「最短」不一定是 BFS：只有每步代價相同時才是，權重不同就是 Dijkstra。第二，DFS 不能求等權最短路：它找到的第一條路徑不一定最短，若硬要用 DFS 就必須列舉所有路徑，是指數時間。第三，「同一格可以走兩次」不代表沒有 visited，而是 visited 的單位要從「位置」擴充成「狀態」。第四，multi-source BFS 和「對每個源頭各跑一次 BFS」的結果相同，但複雜度差了源頭數倍。第五，按層標記（126）和入隊時標記（一般 BFS）各有用途：只要距離時用後者，需要所有父節點時用前者。

## 本章重點整理

- 圖搜尋先回答三個問題：節點是什麼、邊是什麼、要可達性還是最短步數；可達性用 DFS 或 BFS 都可以，等權最短路只能用 BFS。
- BFS 的 invariant 是「queue 中的距離只有 d 與 d + 1 兩種」，所以節點按距離遞增出隊，第一次看到就是最短距離；這個論證依賴每條邊代價相同。
- 一律在**入隊時**標記 visited；用 `deque.popleft()`；格子題先檢查邊界再讀格子。
- 格子上的遞迴 DFS 可能深達 m · n 層，Python 中改用迭代 stack，或主動說明遞迴上限的風險。
- 連通元件的標準結構是「外層掃描每個未拜訪節點、內層搜尋整塊」，外層每次出發就是一個新元件（200）。
- 複製或序列化有環的圖時，hash map「原節點 → 新節點」同時是 visited 與 memo；遞迴版本要先登記再遞迴（133）。
- Multi-source BFS 把所有源頭放進第 0 層，等同虛擬超級源點，複雜度與源頭數無關（994）。
- 起點是「每一格」、終點是固定集合時，改從終點集合反向搜尋一次（417、130）；反向時比較方向也要跟著反。
- 隱式圖不建圖，鄰居即時產生；Word Ladder 用通配符桶或字母枚舉，起點終點已知時可用雙向 BFS，每次擴展較小的一邊（127）。
- 列舉所有最短路徑：BFS 按層標記建分層 DAG，再從終點沿父節點回溯，時間與輸出成正比（126）。
- 「兩次到同一個位置，未來能做的事一樣嗎？」不一樣就把資訊放進狀態：剩餘資源（1293）、已拜訪集合（847）、持有鑰匙（864）。
- 先估算狀態數（m · n · (k + 1)、n · 2ⁿ、m · n · 2ᴷ）確認在限制內；資源有全序時用 `best` 支配剪枝，集合沒有全序就完整記錄。
- 邊有權重時換 Dijkstra（第 18 章），只有 0／1 權重時用 0-1 BFS；有向圖的順序與環在第 16 章，增量連通性用 union-find（第 17 章）。
