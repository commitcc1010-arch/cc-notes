---
chapter: 16
title: Topological Sort
part: 3
---

# 第 16 章　Topological Sort

> [!abstract] 本章地圖
> **一句話**：把「誰必須在誰之前」畫成有向圖，反覆拿走「已經沒有任何前置條件」的節點；能全部拿完就得到一個合法順序，拿不完就代表有環。
>
> **辨識訊號**：
> - 題目出現「先修課」「依賴」「必須先完成」「建置順序」「安裝順序」這類先後關係
> - 要判斷一組先後條件是否矛盾（有沒有循環依賴）
> - 要求「任一個合法順序」，或從比較結果反推字母順序、排名
> - 在有向無環圖上求最長路徑、最早完成時間、路徑計數，或任何「狀態只依賴前驅」的 DP
> - 無向樹上要「從外往內一層層剝葉子」找中心
> - 圖中要區分「會走進環」與「一定走得出去」的節點
>
> **核心題**：207、210、802、310、1462
>
> **難題**：269、329、1203、1857、2050

## 16.1 這個 Pattern 解決什麼問題

先看一個最小的例子。你要編譯六個模組，編號 0 到 5，有幾條依賴：0 要在 1 和 2 之前編譯，1 和 2 都要在 3 之前，3 和 5 都要在 4 之前。問題是：給一個能照著做完的順序，或者回報「不可能」。把每條依賴畫成一條有向邊 `u → v`（u 必須在 v 之前），題目就變成：把圖的節點排成一列，使得每條邊都從左指向右。這種排列叫做 topological order（拓撲順序），求它的過程就是 topological sort（拓撲排序）。

最直接的暴力解是試所有 n! 種排列，逐一檢查每條邊，顯然不可行。稍微聰明一點的做法是模擬人的直覺：「找一個所有前置條件都已經完成的模組，把它做掉，重複這件事。」如果每一輪都重新掃描所有節點、檢查它的每條入邊是否都已完成，一輪要 O(V + E)，總共 n 輪，是 O(V · (V + E))。瓶頸在於每一輪都重新數了一次「還剩幾個前置條件沒完成」，而這個數字其實每次只會因為剛做完的那個模組而改變。

Kahn 演算法就是把這個數字存起來。每個節點維護 in-degree（入度，尚未完成的前置條件數），一開始把入度為 0 的節點放進 queue；每取出一個節點 u，就把它所有後繼 v 的入度減 1，減到 0 的 v 代表「最後一個前置條件剛剛完成」，放進 queue。每條邊只會被減一次，所以整體是 O(V + E)。如果最後取出的節點數少於 V，剩下的節點入度永遠不會歸零，原因只有一個：它們在環上，或者被環上的節點擋住。

這個 pattern 的價值不只在「排出一個順序」。拓撲順序保證處理某個節點時，它所有的前驅都已經處理完，這正是 dynamic programming 需要的性質：最長路徑、最早完成時間、可達性、路徑計數，都可以在拓撲順序上一次掃完。本章後半的難題大多是「拓撲排序 + 一個沿著邊傳遞的 DP」，而第 21 章以後的 DP，本質上也是在狀態圖的拓撲順序上計算。

## 16.2 辨識訊號

| 題目特徵 | 為什麼是 topological sort | 本章哪一題 |
|---|---|---|
| 「先修課」「依賴」，問能不能全部完成 | 能完成 ⇔ 依賴圖沒有環；Kahn 取出的節點數等於 V 就無環 | 核心題 1（207） |
| 要回傳一個合法的完成順序 | Kahn 的取出順序就是一個拓撲順序 | 核心題 2（210） |
| 「從這個節點出發，是否每條路都會停下來」 | 反向圖上從終點往回做 Kahn，能被剝掉的就是安全節點 | 核心題 3（802） |
| 無向樹，要找讓高度最小的根 | 一層層剝葉子，最後剩下的一或兩個節點是中心 | 核心題 4（310） |
| 大量「u 是否為 v 的（間接）前置」查詢 | 沿拓撲順序傳遞祖先集合，得到 transitive closure（遞移閉包） | 核心題 5（1462） |
| 已排序的字串清單，反推字母順序 | 相鄰兩字第一個不同的字元給出一條邊，再做拓撲排序 | 難題 1（269） |
| 格子裡嚴格遞增的路徑 | 「從小走到大」天然無環，格子就是一個隱式 DAG，最長路徑 = BFS 層數 | 難題 2（329） |
| 兩層限制：組內相鄰、又要滿足項目依賴 | 對組與項目各做一次拓撲排序再組合 | 難題 3（1203） |
| 路徑上的最大值／計數，且可能有環 | Kahn 同時負責偵測環與提供 DP 的計算順序 | 難題 4（1857）、難題 5（2050） |

一個實用的反向檢查：如果題目的關係是**無向**的（「a 和 b 是朋友」），或者關係允許循環且題目要你處理循環本身（「找出所有強連通元件」），單純的拓撲排序就不夠，要換成 Union-Find（第 17 章）或 SCC（strongly connected components，強連通元件）演算法。拓撲排序只定義在有向無環圖 DAG（directed acyclic graph）上，它對環唯一能做的事是「偵測到它」。

## 16.3 模板與原理：Kahn 演算法（BFS 入度法）

全章最常用的模板是 Kahn 演算法。它同時回答兩個問題：有沒有環，以及一個合法順序是什麼。

```python
import random
from collections import deque
from itertools import permutations


def topo_sort_kahn(n: int, edges: list[tuple[int, int]]) -> list[int]:
    """edges 中的 (u, v) 代表 u 必須排在 v 之前；有環時回傳 []。"""
    graph = [[] for _ in range(n)]
    indegree = [0] * n
    for u, v in edges:
        graph[u].append(v)
        indegree[v] += 1
    queue = deque(i for i in range(n) if indegree[i] == 0)
    order = []
    while queue:
        u = queue.popleft()
        order.append(u)                  # u 的所有前驅都已經在 order 裡
        for v in graph[u]:
            indegree[v] -= 1             # u 完成了，v 少一個未完成的前置
            if indegree[v] == 0:
                queue.append(v)
    return order if len(order) == n else []


def is_topological(order: list[int], n: int, edges) -> bool:
    if sorted(order) != list(range(n)):
        return False
    pos = {v: i for i, v in enumerate(order)}
    return all(pos[u] < pos[v] for u, v in edges)


def has_order_brute(n: int, edges) -> bool:
    return any(is_topological(list(p), n, edges) for p in permutations(range(n)))


edges = [(0, 1), (0, 2), (1, 3), (2, 3), (3, 4), (5, 4)]
assert topo_sort_kahn(6, edges) == [0, 5, 1, 2, 3, 4]
assert topo_sort_kahn(3, []) == [0, 1, 2]                    # 沒有邊：任何順序都合法
assert topo_sort_kahn(2, [(0, 1), (1, 0)]) == []             # 兩點環
assert topo_sort_kahn(1, [(0, 0)]) == []                     # 自環
assert topo_sort_kahn(2, [(0, 1), (0, 1)]) == [0, 1]         # 重複邊：入度加兩次也減兩次
assert topo_sort_kahn(0, []) == []                           # 空圖：空順序也是合法順序
for _ in range(300):
    n = random.randint(1, 6)
    es = [(random.randrange(n), random.randrange(n)) for _ in range(random.randint(0, 8))]
    order = topo_sort_kahn(n, es)
    if has_order_brute(n, es):
        assert is_topological(order, n, es)
    else:
        assert order == []
print("all tests passed")
```

```text
edges: 0→1, 0→2, 1→3, 2→3, 3→4, 5→4

        0 ──→ 1 ──┐
        │         ↓
        └──→ 2 ──→ 3 ──→ 4
                         ↑
        5 ───────────────┘

初始入度：0:0  1:1  2:1  3:2  4:2  5:0        queue = [0, 5]

步驟  取出  更新入度                     queue 之後     order
 1     0    1:1→0 入隊，2:1→0 入隊       [5, 1, 2]     [0]
 2     5    4:2→1                        [1, 2]        [0, 5]
 3     1    3:2→1                        [2]           [0, 5, 1]
 4     2    3:1→0 入隊                   [3]           [0, 5, 1, 2]
 5     3    4:1→0 入隊                   [4]           [0, 5, 1, 2, 3]
 6     4    （沒有後繼）                 []            [0, 5, 1, 2, 3, 4]
取出 6 個 = n → 無環，order 是一個合法順序
```

步驟 2 取出 5 時，4 的入度只從 2 降到 1，因為 4 還在等 3；直到步驟 5 取出 3，4 的最後一個前置完成，它才入隊。這就是入度的意義：它不是「有幾條入邊」的靜態數字，而是「還有幾個前驅沒被取出」的動態計數。

**Invariant（迴圈不變式）**。演算法維持兩件事：第一，`indegree[v]` 永遠等於「v 的前驅中尚未被取出的個數」；第二，queue 裡的每個節點入度都是 0、而且還沒被取出。一個節點只有在入度歸零的那一刻入隊一次，之後入度不會再變，所以它恰好被取出一次。取出 u 時它的入度是 0，代表它所有前驅都已經在 `order` 裡，因此每條邊 `w → u` 都從左指向右：`order` 在任何時刻都是一個合法的部分順序。

**為什麼取不完就代表有環**。假設迴圈結束時還剩下節點沒取出，任取一個剩下的節點 x，它的入度 > 0，代表它有一個前驅 y 也還沒取出；y 同樣有一個沒取出的前驅 z……剩下的節點是有限的，一直往回走必定重複，也就找到一個環。反過來，環上的節點互相卡住，誰的入度都不可能先歸零，所以有環時一定取不完。這兩個方向合起來就是：**`len(order) == n` ⇔ 圖是 DAG**。

**每一行為什麼這樣寫**：

- 建圖時 `graph[u].append(v)` 而且 `indegree[v] += 1`：邊的方向決定一切。先問清楚題目的 `[a, b]` 是「a 在 b 之前」還是「b 在 a 之前」（207 和 1462 的定義剛好相反），寫在註解裡。
- 初始化把**所有**入度為 0 的節點放進 queue：包括完全沒有邊的孤立節點。只從節點 0 開始是常見錯誤，孤立節點會被漏掉，`len(order)` 就小於 n，被誤判成有環。
- 用 `deque` 而不是 `list.pop(0)`：後者每次 O(n)。其實這裡用 stack 也正確，任何「入度為 0 的節點」都可以下一個取出；用 queue 會讓輸出按「層」排列，這個性質在求最少學期數（核心題 1 F2）、最長遞增路徑（難題 2）時很有用。
- 重複邊不需要去重：同一條邊建了兩次，入度就加兩次，取出 u 時也會減兩次，結果一致。但如果建圖時用 `set` 去重了邊，入度也必須用去重後的邊來算，兩者不一致就會出錯（難題 1 的陷阱）。
- 複雜度 O(V + E)：每個節點入隊、出隊一次，每條邊在建圖與減入度時各被看一次。

## 16.4 第二種模板：DFS 三色法

另一種做法是 DFS。關鍵觀察是：**在 DAG 上做 DFS，一個節點「完成」（所有後繼都探索完）的時間一定晚於它所有後繼的完成時間**。所以把節點按完成順序記下來（postorder，後序），再整個反轉，就是一個拓撲順序。偵測環則需要三種顏色：白色是還沒拜訪，灰色是正在遞迴堆疊上（拜訪了但還沒完成），黑色是已經完成。DFS 時如果走到一個灰色節點，代表從它出發又繞回它自己，也就是遇到 back edge（回邊），圖中有環。

```python
import random
import sys
from collections import deque

WHITE, GRAY, BLACK = 0, 1, 2


def topo_sort_dfs(n: int, edges) -> list[int]:
    graph = [[] for _ in range(n)]
    for u, v in edges:
        graph[u].append(v)
    color = [WHITE] * n
    post = []

    def dfs(u: int) -> bool:            # 回傳 False 代表發現環
        color[u] = GRAY
        for v in graph[u]:
            if color[v] == GRAY:        # 回到正在堆疊上的節點：back edge
                return False
            if color[v] == WHITE and not dfs(v):
                return False
        color[u] = BLACK                # 所有後繼都完成了，u 才完成
        post.append(u)
        return True

    for s in range(n):
        if color[s] == WHITE and not dfs(s):
            return []
    return post[::-1]


def topo_sort_dfs_iterative(n: int, edges) -> list[int]:
    """與上面相同，但用顯式堆疊，n 到 10⁵ 也不會超過遞迴深度。"""
    graph = [[] for _ in range(n)]
    for u, v in edges:
        graph[u].append(v)
    color = [WHITE] * n
    post = []
    for s in range(n):
        if color[s] != WHITE:
            continue
        color[s] = GRAY
        stack = [(s, iter(graph[s]))]
        while stack:
            u, it = stack[-1]
            v = next(it, None)
            if v is None:               # u 的鄰居都看完了
                stack.pop()
                color[u] = BLACK
                post.append(u)
            elif color[v] == GRAY:
                return []
            elif color[v] == WHITE:
                color[v] = GRAY
                stack.append((v, iter(graph[v])))
    return post[::-1]


def is_topological(order, n, edges):
    pos = {v: i for i, v in enumerate(order)}
    return sorted(order) == list(range(n)) and all(pos[u] < pos[v] for u, v in edges)


def kahn_ok(n, edges):
    indeg = [0] * n
    graph = [[] for _ in range(n)]
    for u, v in edges:
        graph[u].append(v)
        indeg[v] += 1
    q = deque(i for i in range(n) if indeg[i] == 0)
    seen = 0
    while q:
        u = q.popleft()
        seen += 1
        for v in graph[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return seen == n


edges = [(0, 1), (0, 2), (1, 3), (2, 3), (3, 4), (5, 4)]
assert is_topological(topo_sort_dfs(6, edges), 6, edges)
assert topo_sort_dfs(2, [(0, 1), (1, 0)]) == []
assert topo_sort_dfs(1, [(0, 0)]) == []
assert topo_sort_dfs(3, [(0, 1), (0, 2), (1, 2)]) == [0, 1, 2]   # 兩條路到 2：黑色節點不是環
chain = [(i, i + 1) for i in range(99_999)]
assert topo_sort_dfs_iterative(100_000, chain) == list(range(100_000))
for _ in range(300):
    n = random.randint(1, 7)
    es = [(random.randrange(n), random.randrange(n)) for _ in range(random.randint(0, 10))]
    a, b = topo_sort_dfs(n, es), topo_sort_dfs_iterative(n, es)
    if kahn_ok(n, es):
        assert is_topological(a, n, es) and is_topological(b, n, es)
    else:
        assert a == [] and b == []
print("all tests passed")
```

```text
edges: 0→1, 0→2, 1→3, 2→3, 3→4, 5→4，鄰居依加入順序拜訪

呼叫                顏色變化                     post（完成順序）
dfs(0)              0 灰
  dfs(1)            1 灰
    dfs(3)          3 灰
      dfs(4)        4 灰 → 4 黑                  [4]
    3 黑                                         [4, 3]
  1 黑                                           [4, 3, 1]
  dfs(2)            2 灰；看到 3 是黑色，略過
  2 黑                                           [4, 3, 1, 2]
0 黑                                             [4, 3, 1, 2, 0]
dfs(5)              5 灰；看到 4 是黑色，略過
5 黑                                             [4, 3, 1, 2, 0, 5]
反轉 → [5, 0, 2, 1, 3, 4]，每條邊都從左指向右
```

**為什麼需要三色而不是兩色**。只用 visited（拜訪過／沒拜訪過）兩種狀態，無法區分「這個節點在目前的遞迴路徑上」（灰）與「它在別的分支已經完成」（黑）。上面 dfs(2) 看到 3 已經拜訪過，但 3 是黑色，代表從 3 出發的一切都已經處理完，0 → 2 → 3 和 0 → 1 → 3 只是兩條匯合的路，不是環。如果把「拜訪過」一律當成環，像 `[(0, 1), (0, 2), (1, 2)]` 這種菱形會被誤判。無向圖找環才用兩色加 parent，有向圖一定要三色。

**為什麼反轉後序是合法順序**。考慮任一條邊 `u → v`。DFS 處理到這條邊時，v 只可能是三種顏色之一：白色，就會遞迴進 v，v 在 u 之前完成；黑色，v 早就完成了；灰色，那是環，DAG 中不會發生。所以在 DAG 中 v 永遠比 u 早進入 `post`，反轉後 u 在 v 前面。

**遞迴深度**。Python 預設遞迴上限約 1000，一條長度 10⁵ 的鏈會讓遞迴版爆掉。面試時可以說「我先寫遞迴版，若 n 很大我會改成顯式堆疊」，或直接用 Kahn，它天生是迭代的。`sys.setrecursionlimit` 只能部分緩解，深度太大時仍可能讓直譯器的 C 堆疊溢位，不建議依賴。

## 16.5 兩種模板怎麼選，以及拓撲順序上的 DP

| | Kahn（BFS 入度法） | DFS 三色法 |
|---|---|---|
| 產生順序 | 直接是拓撲順序 | 反轉後序 |
| 偵測環 | 取出數 < n | 遇到灰色節點 |
| 找出環本身 | 只能知道「剩下的節點」，要另外追 | 灰色節點到目前節點的堆疊就是環 |
| 實作風險 | 低，完全迭代 | 遞迴深度、三色寫錯 |
| 額外能力 | 按層處理（學期數、最長路徑層數）；換成 heap 可得字典序最小 | 天然配合 memoization（記憶化），只計算從某點出發可達的部分 |
| 本章使用 | 207、210、310、1462、269、1203、1857、2050 | 207 F1、802、329 的記憶化解法 |

面試時兩者都要會，預設用 Kahn：它更不容易出錯，也更容易邊寫邊解釋。需要回報「哪個環」或者問題本身是「從某點出發往下走」的遞迴結構時，DFS 更自然。

**拓撲順序上的 DP**。拓撲順序最有用的性質是：處理節點 v 時，v 所有前驅的答案都已經確定。所以任何形如 `dp[v] = combine(dp[u] for u in pred(v))` 的遞推，都可以在 Kahn 取出節點時一併完成，不需要額外的遞迴或記憶化。最長路徑、最早完成時間、路徑數、可達集合都是這個形式。下面的模板一次示範兩種：節點加權的最長路徑，以及從起點到終點的路徑數。

```python
from collections import deque


def dag_dp(n: int, edges, weight: list[int], source: int, target: int):
    """回傳 (最長路徑的節點權重和, 從 source 到 target 的路徑數)；有環回傳 None。"""
    graph = [[] for _ in range(n)]
    indegree = [0] * n
    for u, v in edges:
        graph[u].append(v)
        indegree[v] += 1
    best = weight[:]                          # 以 v 結尾的路徑，至少包含 v 自己
    ways = [0] * n
    ways[source] = 1
    queue = deque(i for i in range(n) if indegree[i] == 0)
    seen = 0
    while queue:
        u = queue.popleft()
        seen += 1                             # 此刻 best[u]、ways[u] 已經是最終值
        for v in graph[u]:
            best[v] = max(best[v], best[u] + weight[v])
            ways[v] += ways[u]
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)
    if seen < n:
        return None
    return max(best, default=0), ways[target]


edges = [(0, 1), (0, 2), (1, 3), (2, 3), (3, 4), (5, 4)]
assert dag_dp(6, edges, [1, 1, 1, 1, 1, 1], 0, 4) == (4, 2)    # 0→1→3→4 共 4 個節點；0 到 4 有兩條路
assert dag_dp(6, edges, [1, 5, 1, 1, 1, 9], 0, 3) == (10, 2)   # 5→4 的權重和 9 + 1 = 10
assert dag_dp(3, [(0, 1), (1, 0)], [1, 1, 1], 0, 1) is None
assert dag_dp(2, [], [3, 4], 0, 1) == (4, 0)                    # 沒有路徑：路徑數為 0
print("all tests passed")
```

`best[v]` 和 `ways[v]` 在 v 入度歸零的那一刻就不會再變，因為之後不會再有指向 v 的邊被處理。這也解釋了 DAG 上的單源最短路徑為什麼不需要 Dijkstra：照拓撲順序做一次 relaxation（鬆弛）就是 O(V + E)，而且邊權為負也沒關係（第 18 章會再對照）。

## 16.6 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 邊的方向建反 | 207 本身不受影響（反向圖有環 ⇔ 原圖有環），但 210 回傳的順序整個顛倒、1462 的查詢答案相反 | 建圖前寫一行註解「`[a, b]` 表示 b → a」，並用範例手動檢查一條邊 |
| 只從節點 0 開始，或漏掉孤立節點 | 沒有任何邊的節點沒被取出，`len(order) < n`，誤判有環 | queue 初始化時掃過全部 n 個節點；269 題要把「出現過的所有字母」都當成節點 |
| 有向圖用兩色 visited 判環 | 菱形 `0→1→2、0→2` 被當成環 | 有向圖用白／灰／黑三色，只有遇到灰色才是環 |
| 忘了檢查 `len(order) == n` | 有環時仍回傳一個「部分順序」 | Kahn 結束後一定比較取出數與節點數 |
| 邊去重與入度不一致 | 入度永遠降不到 0，或提早降到 0 | 要去重就連入度一起用去重後的邊算；不去重就兩邊都不去重 |
| 把無向樹當有向圖做入度 | 310 題每個節點入度都 ≥ 1，queue 一開始就是空的 | 無向圖用「度數 = 1」代表葉子，剝葉子時更新鄰居的度數 |
| 遞迴 DFS 在長鏈上爆深度 | n = 10⁵ 時 `RecursionError` | 改用 Kahn 或顯式堆疊 |
| 用等號比較「合法順序」 | 自己的測試在答案不唯一時誤報失敗 | 寫一個 `is_topological` 驗證器，而不是比對某一個特定答案 |
| 想要字典序最小卻用一般 queue | 輸出合法但不是字典序最小 | 把 queue 換成 min-heap，複雜度變成 O(V log V + E) |

## 核心題 1｜207. Course Schedule｜Medium

### 題目

總共有 `numCourses` 門課，編號 0 到 `numCourses − 1`。陣列 `prerequisites` 中的每一項 `[a, b]` 表示「要修 a 之前，必須先修完 b」。請判斷是否有可能修完所有課程，回傳 True 或 False。限制：`1 <= numCourses <= 2000`，`0 <= len(prerequisites) <= 5000`，每一對 `[a, b]` 互不重複，且 `a != b`。

- 範例 1：`numCourses = 2`、`prerequisites = [[1, 0]]`，回傳 True：先修 0，再修 1。
- 範例 2：`numCourses = 2`、`prerequisites = [[1, 0], [0, 1]]`，回傳 False：0 和 1 互為前置，誰都修不了。
- 範例 3：`numCourses = 4`、`prerequisites = [[1, 0], [2, 1], [3, 2], [1, 3]]`，回傳 False：課程 0 可以修，但 1 → 2 → 3 → 1 形成環。
- 範例 4（邊界）：`numCourses = 3`、`prerequisites = []`，回傳 True：沒有任何限制。

### 思路

暴力解是枚舉所有修課順序，檢查是否每條先修關係都滿足，O(n! · E)，n = 2000 完全不可能。比較合理的暴力是「每一輪掃描所有課，找一門前置都修完的課修掉」，最多 n 輪、每輪 O(V + E)，總共 O(V · (V + E))，約 1.4 × 10⁷，勉強可行，但它重複計算了每門課還差幾個前置。

關鍵觀察是：「能修完所有課」等價於「先修關係圖沒有環」。如果有環，環上每門課都在等另一門，誰都無法開始；如果沒有環，16.3 節證明了 Kahn 演算法一定能把所有節點取出。所以這題不需要真的輸出順序，只要跑一次 Kahn、比較取出的課程數是否等於 `numCourses`。邊的方向這裡設為 `b → a`（b 是 a 的前置，b 要先修），雖然這題就算建反也不影響答案（反向圖的環與原圖一一對應），但下一題會影響，養成習慣比較好。

DFS 三色法同樣可以：對每個白色節點做 DFS，遇到灰色節點就回傳 False。兩者都是 O(V + E)。Kahn 的好處是自然地得到「修完了幾門」，這個數字本身就有意義：例如面試官追問「最多能修幾門」，答案正是 Kahn 取出的節點數（環以及被環擋住的課都修不了，其他都修得了）。

```text
範例 3：numCourses = 4，prerequisites = [[1,0], [2,1], [3,2], [1,3]]
邊（前置 → 課程）：0→1, 1→2, 2→3, 3→1

      0 ──→ 1 ──→ 2
            ↑     │
            └─ 3 ←┘

初始入度：0:0  1:2（來自 0 和 3）  2:1  3:1
queue = [0]

步驟  取出  更新入度          queue
 1     0    1:2→1            []
結束：只取出 1 門課，1 的入度卡在 1（等 3），3 等 2，2 等 1
取出數 1 < 4 → False

對照範例 1：邊 0→1，入度 0:0 1:1
取出 0 → 1 的入度歸零 → 取出 1，共 2 門 = numCourses → True
```

範例 3 中課程 0 雖然能修，但它解開的只是 1 的其中一個前置；1 的另一個前置 3 在環上，所以 1 的入度永遠停在 1。這正是 16.3 節「取不完 ⇔ 有環」的具體樣子：被卡住的節點不一定都在環上（這裡 1、2、3 都在環上，但若再加一門課 4 依賴 3，4 也會被卡住），但卡住的原因一定能追溯到某個環。

### 解法

```python
import random
from collections import deque
from itertools import permutations


def can_finish(num_courses: int, prerequisites: list[list[int]]) -> bool:
    graph = [[] for _ in range(num_courses)]
    indegree = [0] * num_courses
    for course, pre in prerequisites:          # [a, b]：b → a
        graph[pre].append(course)
        indegree[course] += 1
    queue = deque(c for c in range(num_courses) if indegree[c] == 0)
    taken = 0
    while queue:
        c = queue.popleft()
        taken += 1
        for nxt in graph[c]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    return taken == num_courses


def can_finish_dfs(num_courses: int, prerequisites: list[list[int]]) -> bool:
    graph = [[] for _ in range(num_courses)]
    for course, pre in prerequisites:
        graph[pre].append(course)
    color = [0] * num_courses                  # 0 白、1 灰、2 黑
    for s in range(num_courses):
        if color[s]:
            continue
        color[s] = 1
        stack = [(s, iter(graph[s]))]
        while stack:
            u, it = stack[-1]
            v = next(it, None)
            if v is None:
                color[u] = 2
                stack.pop()
            elif color[v] == 1:
                return False
            elif color[v] == 0:
                color[v] = 1
                stack.append((v, iter(graph[v])))
    return True


def brute(n, pre):
    for p in permutations(range(n)):
        pos = {c: i for i, c in enumerate(p)}
        if all(pos[b] < pos[a] for a, b in pre):
            return True
    return False


assert can_finish(2, [[1, 0]]) is True
assert can_finish(2, [[1, 0], [0, 1]]) is False
assert can_finish(4, [[1, 0], [2, 1], [3, 2], [1, 3]]) is False
assert can_finish(3, []) is True
assert can_finish(1, []) is True
assert can_finish(5, [[1, 0], [2, 0], [3, 1], [3, 2], [4, 3]]) is True   # 菱形不是環
for _ in range(300):
    n = random.randint(1, 6)
    pairs = {(random.randrange(n), random.randrange(n)) for _ in range(random.randint(0, 8))}
    pre = [[a, b] for a, b in pairs if a != b]
    assert can_finish(n, pre) == can_finish_dfs(n, pre) == brute(n, pre)
print("all tests passed")
```

### 複雜度與邊界

時間 O(V + E)：建圖 O(E)，每門課入隊、出隊一次，每條邊減一次入度。空間 O(V + E) 存鄰接串列與入度。邊界情況：沒有先修關係時所有課入度為 0，一次全部入隊；只有一門課時直接回傳 True；菱形依賴（兩條路匯到同一門課）不是環，Kahn 只是讓那門課的入度分兩次降到 0，DFS 版會看到黑色節點並略過；題目保證 `a != b`，若出現自環 `[a, a]`，a 的入度至少為 1 且永遠不會歸零，Kahn 會正確回傳 False，不需要特判。

### Follow-up

> [!question]- F1. 如果不可能修完，要回傳其中一個環（例如讓教務處知道哪幾門課互相卡住）？
> 用 DFS 三色法，額外維護遞迴堆疊上的節點序列 `path` 與每個節點在 `path` 中的位置。走到一條邊 `u → v` 而 v 是灰色時，`path[pos[v]:]` 就是從 v 出發繞回 v 的環。時間仍是 O(V + E)。Kahn 做不到這麼直接：它只知道「剩下的節點」，那些節點中有些在環上、有些只是被擋住；若硬要用 Kahn，可以從任一剩下的節點沿著「還沒取出的前驅」一直往回走，走到重複的節點就找到環，因為每個剩下的節點都至少有一個剩下的前驅。
> ```python
> def find_cycle(n, edges):
>     graph = [[] for _ in range(n)]
>     for u, v in edges:
>         graph[u].append(v)
>     color, path, pos = [0] * n, [], {}
>     for s in range(n):
>         if color[s]:
>             continue
>         color[s], pos[s] = 1, 0
>         path.append(s)
>         stack = [iter(graph[s])]
>         while stack:
>             v = next(stack[-1], None)
>             if v is None:
>                 u = path.pop()
>                 color[u] = 2
>                 stack.pop()
>             elif color[v] == 1:
>                 return path[pos[v]:]
>             elif color[v] == 0:
>                 color[v], pos[v] = 1, len(path)
>                 path.append(v)
>                 stack.append(iter(graph[v]))
>     return []
> ```

> [!question]- F2. 如果每學期可以同時修任意多門課（只要前置都修完），最少要幾學期（1136. Parallel Courses）？
> 用 Kahn 按層處理：每一輪把 queue 裡目前所有的課一次取出，視為同一學期，處理完它們的後繼後，新入隊的課屬於下一學期。學期數就是層數，等於 DAG 中最長路徑的節點數。有環則回傳 -1。時間 O(V + E)。寫法是在 `while queue` 內再包一層 `for _ in range(len(queue))`，和第 15 章 BFS 求層數完全相同；也可以用 16.5 節的 DP，`level[v] = max(level[u] + 1)`。

> [!question]- F3. 如果每學期最多只能修 k 門課呢（1494. Parallel Courses II）？
> 這時「每層全取」不再最佳，貪婪地挑「後面依賴最多」或「最長路徑最長」的課都有反例，一般化的問題（有先後限制的多機排程）是 NP-hard。原題 n ≤ 15，所以用 bitmask DP：`dp[mask]` 是修完集合 mask 所需的最少學期數，每一步從「前置都在 mask 裡、自己不在 mask 裡」的課中枚舉大小 ≤ k 的子集合轉移，時間約 O(3ⁿ)。面試中說出「k 有限制後貪婪失效、變成指數級狀態搜尋」並給出 bitmask DP 的狀態定義，就是好的回答（第 24 章會再談 bitmask DP）。

> [!question]- F4. 如果先修關係是一條一條動態加入的，要在「第一次出現環」時立刻回報是哪一條？
> 線上做法：加入邊 `b → a` 之前，先檢查 a 是否已經能走到 b（一次 DFS/BFS），能走到代表這條邊會閉合一個環。每條邊 O(V + E)，總共 O(E · (V + E))。離線做法更快：如果所有邊事先已知，「前 i 條邊是否有環」對 i 單調（加邊只會讓環更容易出現），所以可以對 i 做 binary search（第 8 章），每次用 Kahn 檢查，總共 O((V + E) log E)。這是「二分答案 + 圖演算法」的組合，面試官很喜歡看到你把兩章串起來。

## 核心題 2｜210. Course Schedule II｜Medium

### 題目

條件和上一題相同：`numCourses` 門課，`prerequisites[i] = [a, b]` 表示修 a 之前要先修 b。這次要回傳一個能修完所有課的修課順序（任一個合法順序都可以）；如果不可能，回傳空陣列。限制：`1 <= numCourses <= 2000`，`0 <= len(prerequisites) <= numCourses × (numCourses − 1)`，所有 `[a, b]` 互不重複且 `a != b`。

- 範例 1：`numCourses = 2`、`prerequisites = [[1, 0]]`，回傳 `[0, 1]`。
- 範例 2：`numCourses = 4`、`prerequisites = [[1, 0], [2, 0], [3, 1], [3, 2]]`，回傳 `[0, 1, 2, 3]` 或 `[0, 2, 1, 3]`，兩者都合法。
- 範例 3：`numCourses = 3`、`prerequisites = [[0, 1], [1, 2], [2, 0]]`，回傳 `[]`：三門課形成環。
- 範例 4（邊界）：`numCourses = 1`、`prerequisites = []`，回傳 `[0]`；`numCourses = 3`、沒有限制時，任何排列都合法，例如 `[0, 1, 2]`。

### 思路

上一題只要知道「能不能」，這題要把順序本身交出來。暴力解同樣是枚舉排列，不可行；「每輪掃一遍找可修的課」是 O(V · (V + E))，而這題的 E 可以到 n² ≈ 4 × 10⁶，乘上 V 就太慢了。Kahn 演算法的取出順序本身就是一個拓撲順序，所以這題是 16.3 節模板的直接應用：把 `taken += 1` 換成 `order.append(c)`，最後若 `len(order) < numCourses` 就回傳空陣列。

這題的方向**一定要建對**：`[a, b]` 代表 b 要先修，所以邊是 `b → a`。如果建成 `a → b`，Kahn 仍然能跑完，回傳的卻是完全顛倒的順序，而且在範例 2 這種對稱的例子上不容易一眼看出錯誤。好的習慣是寫完後拿範例 1 手動驗證：`[[1, 0]]` 應該讓 0 排在 1 前面。

另一個重點是**答案不唯一**。範例 2 中 1 和 2 沒有先後關係，誰先都行；Kahn 的輸出取決於 queue 的順序，DFS 的輸出取決於鄰居的拜訪順序。面試時要主動說明這一點，測試時也不要用 `==` 比對某一個答案，而是寫一個驗證器檢查「每條邊都從左指向右，且每門課恰好出現一次」。

```text
範例 2：numCourses = 4，prerequisites = [[1,0], [2,0], [3,1], [3,2]]
邊：0→1, 0→2, 1→3, 2→3

        ┌──→ 1 ──┐
        0        3
        └──→ 2 ──┘

初始入度：0:0  1:1  2:1  3:2         queue = [0]

步驟  取出  更新入度                  queue     order
 1     0    1:1→0 入隊，2:1→0 入隊    [1, 2]    [0]
 2     1    3:2→1                     [2]       [0, 1]
 3     2    3:1→0 入隊                [3]       [0, 1, 2]
 4     3    —                         []        [0, 1, 2, 3]
len(order) = 4 → 回傳 [0, 1, 2, 3]

若鄰接串列的順序是 0→2 先、0→1 後，步驟 1 會讓 queue = [2, 1]，
輸出變成 [0, 2, 1, 3]，同樣合法
```

步驟 1 之後 queue 裡同時有 1 和 2，這代表它們「同時可修」，先取哪一個都不會違反任何限制。這也是 F1「字典序最小」只需要把 queue 換成 heap 的原因：Kahn 在每一步都有選擇權，heap 只是規定了選擇的方式。

### 解法

```python
import random
from collections import deque


def find_order(num_courses: int, prerequisites: list[list[int]]) -> list[int]:
    graph = [[] for _ in range(num_courses)]
    indegree = [0] * num_courses
    for course, pre in prerequisites:          # [a, b]：b 要先修，邊 b → a
        graph[pre].append(course)
        indegree[course] += 1
    queue = deque(c for c in range(num_courses) if indegree[c] == 0)
    order = []
    while queue:
        c = queue.popleft()
        order.append(c)
        for nxt in graph[c]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    return order if len(order) == num_courses else []


def valid(order, n, pre):
    if sorted(order) != list(range(n)):
        return False
    pos = {c: i for i, c in enumerate(order)}
    return all(pos[b] < pos[a] for a, b in pre)


def has_cycle(n, pre):                         # 對照組：用「可達」判斷環，O(n · (n + E))
    graph = [[] for _ in range(n)]
    for a, b in pre:
        graph[b].append(a)
    for s in range(n):
        stack, seen = list(graph[s]), set()
        while stack:
            u = stack.pop()
            if u == s:
                return True
            if u not in seen:
                seen.add(u)
                stack.extend(graph[u])
    return False


assert find_order(2, [[1, 0]]) == [0, 1]
assert find_order(4, [[1, 0], [2, 0], [3, 1], [3, 2]]) in ([0, 1, 2, 3], [0, 2, 1, 3])
assert find_order(3, [[0, 1], [1, 2], [2, 0]]) == []
assert find_order(1, []) == [0]
assert valid(find_order(3, []), 3, [])
assert find_order(3, [[1, 0], [1, 2]]) in ([0, 2, 1], [2, 0, 1])   # 1 有兩個前置
for _ in range(500):
    n = random.randint(1, 7)
    pairs = {(random.randrange(n), random.randrange(n)) for _ in range(random.randint(0, 10))}
    pre = [[a, b] for a, b in pairs if a != b]
    got = find_order(n, pre)
    assert (got == []) == has_cycle(n, pre)
    if got:
        assert valid(got, n, pre)
print("all tests passed")
```

### 複雜度與邊界

時間 O(V + E)，空間 O(V + E)。這題 E 最多約 4 × 10⁶，鄰接串列是必要的；用 V × V 的鄰接矩陣會讓 Kahn 每取出一個節點都要掃一整列，變成 O(V²)，在 E 接近 V² 時兩者相當，但 E 小時浪費很多。邊界情況：沒有先修關係時回傳 `[0, 1, …, n − 1]`（queue 的初始順序）；有環時回傳 `[]` 而不是部分順序；`numCourses = 1` 時回傳 `[0]`；同一門課有多個前置時，它的入度要等全部前置取出才歸零，這正是 Kahn 處理「AND 條件」的方式。

### Follow-up

> [!question]- F1. 如果有多個合法順序，要回傳字典序最小的那一個？
> 把 `deque` 換成 min-heap：每一步都從「目前可修的課」中挑編號最小的。這是正確的，因為字典序比較從第一個位置開始，而第一個位置只能是入度為 0 的課，選最小的一定不會更差；選定之後，剩下的問題是同一個問題在較小的圖上，歸納即可。時間 O(V log V + E)。注意不能先跑一般 Kahn 再排序，排序會破壞先後限制。
> ```python
> import heapq
> def smallest_order(n, pre):
>     graph, indeg = [[] for _ in range(n)], [0] * n
>     for a, b in pre:
>         graph[b].append(a)
>         indeg[a] += 1
>     heap = [c for c in range(n) if indeg[c] == 0]
>     heapq.heapify(heap)
>     order = []
>     while heap:
>         c = heapq.heappop(heap)
>         order.append(c)
>         for nxt in graph[c]:
>             indeg[nxt] -= 1
>             if indeg[nxt] == 0:
>                 heapq.heappush(heap, nxt)
>     return order if len(order) == n else []
> ```

> [!question]- F2. 怎麼判斷合法順序是否唯一（444. Sequence Reconstruction 的核心）？
> 跑 Kahn 時檢查：只要某一刻 queue 裡同時有兩個以上的節點，就代表那兩門課誰先都行，順序不唯一。反過來，如果每一步 queue 都恰好只有一個節點，順序就是唯一的，而且此時相鄰的兩門課之間一定有一條直接的邊（否則後者不會恰好在前者取出時入度歸零）。時間仍是 O(V + E)，只多一個 `len(queue) > 1` 的判斷。等價的說法是：拓撲順序唯一 ⇔ 這個順序中每一對相鄰節點之間都有邊，也就是 DAG 中存在一條經過所有節點的路徑（Hamiltonian path）。

> [!question]- F3. 如果給你一個修課順序，要驗證它是否合法？
> 先檢查它是 0 到 n − 1 的一個排列（長度為 n、沒有重複），再建一個 `pos[c]` 表示課程 c 在順序中的位置，最後檢查每一對 `[a, b]` 都滿足 `pos[b] < pos[a]`。時間 O(V + E)，完全不需要做拓撲排序。這個驗證器在面試中很實用：當題目答案不唯一時，你可以用它說明自己的測試策略，面試官會知道你不是只會比對範例輸出。

> [!question]- F4. 如果要計算總共有多少個合法的修課順序？
> 這是計數所有 linear extensions（線性延伸），一般情況是 #P-complete，沒有多項式解。n 小（約 20 以內）時用 bitmask DP：`dp[mask]` 是「已經修完的集合恰好是 mask」的排法數，若課 c 不在 mask 中且它的前置集合 `need[c]` 是 mask 的子集，就從 `dp[mask]` 轉移到 `dp[mask | 1 << c]`，時間 O(2ⁿ · n)。若圖是一棵 out-tree（每門課最多一個前置），有封閉公式 n! / Π(子樹大小)，O(n) 即可。這種「結構特殊才有公式」的觀察，是面試官判斷候選人深度的好題目。

## 核心題 3｜802. Find Eventual Safe States｜Medium

### 題目

給一張有 n 個節點（編號 0 到 n − 1）的有向圖，`graph[i]` 是節點 i 的所有出邊指向的節點。沒有出邊的節點稱為 terminal node（終點）。如果從節點 i 出發，**不論怎麼走，每一條路徑最後都會停在某個終點**，就稱 i 為安全節點。請由小到大回傳所有安全節點。限制：`1 <= n <= 10⁴`，總邊數 `<= 4 × 10⁴`，圖中可能有自環 `i → i`，`graph[i]` 內沒有重複。

- 範例 1：`graph = [[1, 2], [2, 3], [5], [0], [5], [], []]`，回傳 `[2, 4, 5, 6]`。0 → 1 → 3 → 0 是一個環，所以 0、1、3 都不安全；2 只能走到 5，4 只能走到 5，5 和 6 是終點。
- 範例 2：`graph = [[1, 2, 3, 4], [1, 2], [3, 4], [0, 4], []]`，回傳 `[4]`。1 有自環，0 → 3 → 0 是環，2 能走到 3 進入環。
- 範例 3（邊界）：`graph = [[0]]`，回傳 `[]`：唯一的節點有自環，永遠走不完。
- 範例 4（邊界）：`graph = [[], [], []]`，回傳 `[0, 1, 2]`：每個節點都是終點。

### 思路

先把「安全」翻譯成圖的語言：從 i 出發的每條路都會停下來，等價於「從 i 出發走不到任何環」。暴力解是對每個節點各做一次 DFS，看它能不能走到一個環，每次 O(V + E)，總共 O(V · (V + E))，約 5 × 10⁸，太慢。浪費在於：如果節點 2 已經確定安全，所有只會走到 2 的節點其實不必再走一遍 2 後面的路。

關鍵觀察是安全性有一個遞迴結構：**i 安全 ⇔ i 的每一個後繼都安全**（終點沒有後繼，自動安全）。這是一個「全部都要滿足」的 AND 條件，和 Kahn 演算法的入度完全同構：入度記錄「還有幾個前驅沒完成」，這裡要記錄的是「還有幾個後繼沒被確認安全」，也就是**出度**。所以把圖的邊全部反轉，從終點（出度 0）開始做 Kahn：每確認一個節點安全，就把所有指向它的節點的出度減 1，減到 0 代表那個節點的所有後繼都已確認安全，它也安全。最後被取出的節點就是全部的安全節點。

另一個角度是 DFS 三色法：一個節點在 DFS 中若碰到灰色節點（環），它就是不安全的，而且整條遞迴路徑上的節點都能走到那個環，全都不安全；只有順利變成黑色的節點才安全。一個巧妙的實作細節是：**不安全的節點直接永遠留在灰色**，之後別的節點碰到它時，「碰到灰色」的規則會自動把它們也判成不安全，不需要第四種顏色。兩種方法都是 O(V + E)。

```text
範例 1：graph = [[1,2], [2,3], [5], [0], [5], [], []]
原圖：0→1, 0→2, 1→2, 1→3, 2→5, 3→0, 4→5

      ┌───────────┐
      ↓           │
      0 ──→ 1 ──→ 3            環：0 → 1 → 3 → 0
      │     │
      ↓     ↓
      2 ←───┘
      │
      ↓
      5 ←── 4                  6（孤立的終點）

出度：0:2  1:2  2:1  3:1  4:1  5:0  6:0
反向邊（誰指向我）：5←{2,4}  2←{0,1}  3←{1}  0←{3}  1←{0}

queue = [5, 6]（終點）
步驟  取出  反向鄰居出度更新              queue      安全
 1     5    2:1→0 入隊，4:1→0 入隊        [6, 2, 4]  {5}
 2     6    —                             [2, 4]     {5, 6}
 3     2    0:2→1，1:2→1                  [4]        {5, 6, 2}
 4     4    —                             []         {5, 6, 2, 4}
結束：0、1、3 的出度卡在 1（都還有一條邊指向環內）
回傳 sorted → [2, 4, 5, 6]
```

步驟 3 取出 2 時，0 和 1 各少了一個「待確認的後繼」，但 0 還有後繼 1、1 還有後繼 3 沒被確認，而 3 指向 0，三者互相等待，就像 207 題中環上的課程互相卡住。差別只在方向：207 等的是前驅，這題等的是後繼，所以這題在反向圖上做 Kahn。

### 解法

```python
import random
from collections import deque


def eventual_safe_nodes(graph: list[list[int]]) -> list[int]:
    n = len(graph)
    reverse = [[] for _ in range(n)]
    outdegree = [len(nbrs) for nbrs in graph]
    for u, nbrs in enumerate(graph):
        for v in nbrs:
            reverse[v].append(u)               # 反向邊 v → u
    queue = deque(u for u in range(n) if outdegree[u] == 0)
    safe = [False] * n
    while queue:
        v = queue.popleft()
        safe[v] = True
        for u in reverse[v]:
            outdegree[u] -= 1                  # u 少一個「還沒確認安全」的後繼
            if outdegree[u] == 0:
                queue.append(u)
    return [u for u in range(n) if safe[u]]


def eventual_safe_nodes_dfs(graph: list[list[int]]) -> list[int]:
    n = len(graph)
    color = [0] * n                            # 0 白、1 灰（在堆疊上或已知不安全）、2 黑（安全）
    for s in range(n):
        if color[s]:
            continue
        color[s] = 1
        stack = [(s, iter(graph[s]))]
        while stack:
            u, it = stack[-1]
            v = next(it, None)
            if v is None:                      # 所有後繼都安全
                color[u] = 2
                stack.pop()
            elif color[v] == 1:                # 走到環或已知不安全的節點
                stack.clear()                  # 堆疊上全部留在灰色 = 不安全
            elif color[v] == 0:
                color[v] = 1
                stack.append((v, iter(graph[v])))
    return [u for u in range(n) if color[u] == 2]


def brute(graph):
    n = len(graph)

    def reach(s):
        seen, stack = set(), list(graph[s])
        while stack:
            u = stack.pop()
            if u not in seen:
                seen.add(u)
                stack.extend(graph[u])
        return seen

    on_cycle = {u for u in range(n) if u in reach(u)}
    return [u for u in range(n) if u not in on_cycle and not (reach(u) & on_cycle)]


assert eventual_safe_nodes([[1, 2], [2, 3], [5], [0], [5], [], []]) == [2, 4, 5, 6]
assert eventual_safe_nodes([[1, 2, 3, 4], [1, 2], [3, 4], [0, 4], []]) == [4]
assert eventual_safe_nodes([[0]]) == []
assert eventual_safe_nodes([[], [], []]) == [0, 1, 2]
assert eventual_safe_nodes_dfs([[1, 2], [2, 3], [5], [0], [5], [], []]) == [2, 4, 5, 6]
chain = [[i + 1] for i in range(9999)] + [[]]            # 長鏈：DFS 版必須是迭代的
assert eventual_safe_nodes_dfs(chain) == list(range(10000))
for _ in range(500):
    n = random.randint(1, 7)
    g = [sorted(random.sample(range(n), random.randint(0, min(3, n)))) for _ in range(n)]
    assert eventual_safe_nodes(g) == eventual_safe_nodes_dfs(g) == brute(g)
print("all tests passed")
```

### 複雜度與邊界

兩種寫法時間都是 O(V + E)：反向 Kahn 每條反向邊被看一次；DFS 每個節點至多入堆疊一次，每條邊至多被 `next` 取出一次，碰到環時清空堆疊也只是把已經入堆疊的節點丟掉。空間 O(V + E)，反向圖需要額外一份邊。邊界情況：自環 `i → i` 讓 i 的出度永遠至少為 1，Kahn 不會取出它，DFS 則在第一次看到自己是灰色時判定不安全；沒有任何邊時全部是終點；題目要求由小到大輸出，Kahn 的取出順序不是排序的，所以用 `safe` 陣列最後再依編號收集，避免額外的排序成本。

### Follow-up

> [!question]- F1. 如果要分辨「本身在環上」和「只是能走到環」的節點呢？
> 拓撲排序只能告訴你哪些節點會碰到環，分不出它們的角色。要知道誰在環上，需要 SCC：用 Tarjan 或 Kosaraju 演算法在 O(V + E) 內把圖分解成強連通元件，節點在環上 ⇔ 它所在的 SCC 大小 ≥ 2，或它有自環。之後「能走到環但不在環上」的節點，就是不安全節點扣掉在環上的節點。面試時能指出「Kahn 剩下的節點 ≠ 環上的節點」，是理解 Kahn 輸出意義的重要細節，207 F1 找環也是同一個觀念。

> [!question]- F2. 如果「安全」的定義改成「存在一條路徑能走到終點」呢？
> 條件從 AND（每個後繼都安全）變成 OR（某個後繼安全），就不需要計數器了：在反向圖上從所有終點做一次普通的 BFS，能被拜訪到的節點都安全，O(V + E)。這個對比很有啟發性：Kahn 的入度（或出度）計數器正是用來實作「全部都滿足才放行」的 AND 條件；若是「任一個滿足就放行」，第一次被碰到就可以入隊，退化成第 15 章的多源 BFS。

> [!question]- F3. 兩人輪流移動棋子的遊戲（例如 913. Cat and Mouse），怎麼決定每個狀態的勝負？
> 這是本題 AND／OR 結構的推廣，稱為 retrograde analysis（逆向分析）。狀態是「棋子位置 + 輪到誰」，從已知勝負的終局狀態開始在反向圖上 BFS：若某狀態輪到 A，而它有一個後繼是 A 必勝，它就是 A 必勝（OR，碰到就決定）；若它的所有後繼都是 B 必勝，它才是 B 必勝（AND，用出度計數器，減到 0 才決定）。始終無法決定的狀態就是和局，對應本題卡在環上的節點。時間 O(狀態數 + 轉移數)。

> [!question]- F4. 如果圖非常大，但只需要判斷某一個起點 s 是否安全？
> 不需要處理整張圖，只要從 s 做一次三色 DFS，探索 s 可達的子圖：碰到灰色就立刻回傳不安全，全部探索完都沒碰到就是安全。時間 O(可達的節點數 + 邊數)，與整張圖的大小無關。若有大量這種單點查詢，就先用反向 Kahn 一次算出所有節點的答案，之後每次查詢 O(1)；兩種做法的取捨取決於查詢數量與可達範圍的大小。

## 核心題 4｜310. Minimum Height Trees｜Medium

### 題目

給一棵有 n 個節點（編號 0 到 n − 1）的無向樹，以 `edges` 列出 n − 1 條邊。任選一個節點當作根，樹的高度定義為根到最遠葉子的邊數。請回傳所有能讓高度最小的根（順序不限）。限制：`1 <= n <= 2 × 10⁴`，`edges` 保證構成一棵樹（連通、無環）。

- 範例 1：`n = 4`、`edges = [[1, 0], [1, 2], [1, 3]]`，回傳 `[1]`：以 1 為根高度是 1，以其他節點為根高度是 2。
- 範例 2：`n = 6`、`edges = [[3, 0], [3, 1], [3, 2], [3, 4], [5, 4]]`，回傳 `[3, 4]`：兩者為根時高度都是 2。
- 範例 3（邊界）：`n = 1`、`edges = []`，回傳 `[0]`。
- 範例 4（邊界）：`n = 2`、`edges = [[0, 1]]`，回傳 `[0, 1]`：兩個節點當根的高度都是 1。

### 思路

暴力解是對每個節點做一次 BFS 求高度，取最小者，O(n²)；n = 2 × 10⁴ 時是 4 × 10⁸ 次操作，在 Python 中太慢。要省下工作量，必須看出「最佳的根」有什麼結構。

把以 u 為根的高度記作 ecc(u)，也就是 u 到最遠節點的距離（eccentricity，離心率）。兩個觀察：第一，當樹有至少 3 個節點時，**葉子永遠不是最佳的根**。葉子 l 只有一個鄰居 p，任何從 l 出發的路都先經過 p，所以 ecc(l) = ecc(p) + 1 > ecc(p)（3 個以上節點時 p 的最遠節點不會是 l 自己）。第二，**把所有葉子同時剝掉後，剩下每個節點的 ecc 恰好都減 1**：任何非葉節點的最遠節點一定是葉子（否則還能再往外走），剝掉一層後它最遠只能到那片葉子的鄰居，距離少 1。所以剝葉子不改變剩餘節點之間 ecc 的大小關係，最佳的根一直保留在剩下的樹裡。

於是演算法就是在無向樹上做「拓撲排序」：用度數（degree）代替入度，度數為 1 的是葉子；一層一層剝掉葉子，並更新鄰居的度數，鄰居度數變成 1 就成為下一層的葉子。當剩下的節點數 ≤ 2 時停止，剩下的就是答案。為什麼是 1 或 2 個？只要剩下 ≥ 3 個節點，第一個觀察說葉子不是最佳，還能繼續剝；剩下 2 個時它們相鄰、ecc 相等，都是答案。這兩個節點正是樹的直徑（最長路徑）的中點，直徑邊數為偶數時中點是一個節點，為奇數時是一條邊的兩端。

```text
範例 2：n = 6，edges = [[3,0], [3,1], [3,2], [3,4], [5,4]]

      0   1   2
       \  |  /
          3 ─── 4 ─── 5

度數：0:1  1:1  2:1  3:4  4:2  5:1
第 1 層葉子：[0, 1, 2, 5]           剩下 6 個 > 2，剝掉
  剝 0 → 3 的度數 4→3
  剝 1 → 3 的度數 3→2
  剝 2 → 3 的度數 2→1  ← 3 成為新葉子
  剝 5 → 4 的度數 2→1  ← 4 成為新葉子
剩下 6 − 4 = 2 個：[3, 4]，停止 → 回傳 [3, 4]

驗證：以 3 為根，最遠是 5（3→4→5，距離 2）；以 4 為根，最遠是 0、1、2（距離 2）
以 0 為根，最遠是 5（0→3→4→5，距離 3）
```

每剝一層，所有剩餘節點的高度一起減 1，就像從外往內削一顆洋蔥。直徑 0 → 3 → 4 → 5 有 3 條邊（奇數），所以中心是一條邊 3—4 的兩端。如果再接一個節點 6 在 5 後面，直徑變成 4 條邊，中心就只剩 4。

### 解法

```python
import random
from collections import deque


def find_min_height_trees(n: int, edges: list[list[int]]) -> list[int]:
    if n <= 2:
        return list(range(n))
    adj = [set() for _ in range(n)]
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    leaves = [u for u in range(n) if len(adj[u]) == 1]
    remaining = n
    while remaining > 2:
        remaining -= len(leaves)
        next_leaves = []
        for leaf in leaves:
            nb = adj[leaf].pop()               # 葉子只剩一個鄰居
            adj[nb].remove(leaf)
            if len(adj[nb]) == 1:
                next_leaves.append(nb)
        leaves = next_leaves
    return sorted(leaves)


def brute(n, edges):
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)

    def height(r):
        dist = [-1] * n
        dist[r] = 0
        q = deque([r])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if dist[v] < 0:
                    dist[v] = dist[u] + 1
                    q.append(v)
        return max(dist)

    hs = [height(r) for r in range(n)]
    return [r for r in range(n) if hs[r] == min(hs)]


def random_tree(n):
    return [[i, random.randrange(i)] for i in range(1, n)]


assert find_min_height_trees(4, [[1, 0], [1, 2], [1, 3]]) == [1]
assert find_min_height_trees(6, [[3, 0], [3, 1], [3, 2], [3, 4], [5, 4]]) == [3, 4]
assert find_min_height_trees(1, []) == [0]
assert find_min_height_trees(2, [[0, 1]]) == [0, 1]
assert find_min_height_trees(5, [[0, 1], [1, 2], [2, 3], [3, 4]]) == [2]     # 偶數邊的直徑
assert find_min_height_trees(4, [[0, 1], [1, 2], [2, 3]]) == [1, 2]         # 奇數邊的直徑
for _ in range(500):
    n = random.randint(1, 12)
    es = random_tree(n)
    assert find_min_height_trees(n, es) == brute(n, es)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每個節點恰好被當成葉子剝掉一次（最後剩下的除外），每條邊在剝葉子時被刪一次，`set` 的 `pop` 與 `remove` 平均 O(1)。空間 O(n)。邊界情況：n = 1 時沒有邊，`leaves` 會是空的，必須特判回傳 `[0]`；n = 2 時兩個節點都是葉子，若不特判，`while remaining > 2` 不會執行，回傳兩個節點也正確，但特判讓意圖更清楚；星形樹第一層就剝到只剩中心；鏈狀樹每層只剝兩端，需要 n / 2 層，但總工作量仍是 O(n)。用 `remaining` 計數而不是 `len(leaves)` 判斷停止，因為最後一層的葉子數可能是 1 或 2。

### Follow-up

> [!question]- F1. 如果只要回傳最小高度的數值，不要回傳根呢？
> 最小高度等於 ⌈d / 2⌉，d 是直徑的邊數。直徑可以用兩次 BFS 在 O(n) 求出：從任一點 BFS 找到最遠的 a，再從 a 做 BFS 找到最遠的 b，a 到 b 的距離就是直徑。用剝葉子也可以直接得到：設剝了 r 層後剩下 1 個節點，高度是 r；剩下 2 個節點，高度是 r + 1。兩次 BFS 的方法同時給出直徑路徑，取路徑中間的一或兩個節點就是本題的答案，是另一種 O(n) 解法。

> [!question]- F2. 如果輸入是一般的無向圖（可能有環）而不是樹呢？
> 剝葉子會失效：環上的節點度數永遠 ≥ 2，不會變成葉子，演算法會卡住而剩下整個環以及掛在環上的樹。一般圖的「中心」（離心率最小的節點）沒有已知的線性時間演算法，標準做法是對每個節點做一次 BFS，O(V · (V + E))。如果邊有權重，就要用 Floyd–Warshall 或每點一次 Dijkstra（第 18 章）。面試時能說明「剝葉子依賴樹的性質：非葉節點的最遠點一定是葉子」，就能解釋為什麼它不能推廣到有環的圖。

> [!question]- F3. 如果邊有正權重，要找讓「最遠距離」最小的節點呢？
> 葉子不再是同時「離中心一樣近」，按層剝的論證失效。改用加權直徑：兩次 DFS/BFS（樹上任意兩點路徑唯一，所以累加距離即可）找到加權直徑的兩端 a、b，最佳節點一定在 a 到 b 的路徑上（任何節點的最遠點都是 a 或 b 之一），沿路徑找使 `max(dist(a, u), dist(u, b))` 最小的節點 u。時間 O(n)。若允許把根放在邊的中間，答案就是直徑長度的一半。

> [!question]- F4. 如果目標改成讓「到所有節點的距離總和」最小呢？
> 這是不同的問題，答案也可能不同：一條長鏈上掛著很多葉子時，總和最小的點會被葉子群拉過去，而高度最小的點仍在鏈的中間。最佳點是樹的 centroid（重心）意義下的中位點，可以用 rerooting DP 在 O(n) 內算出每個節點的距離總和：先以 0 為根算出子樹大小與總和，再用 `ans[child] = ans[parent] − size[child] + (n − size[child])` 往下推，這是第 24 章難題 1（834. Sum of Distances in Tree）。面試官常用這個對比確認你知道 center 與 centroid 的差別。

## 核心題 5｜1462. Course Schedule IV｜Medium

### 題目

有 n 門課，編號 0 到 n − 1。`prerequisites[i] = [a, b]` 表示「a 是 b 的直接前置課程，要先修 a 才能修 b」（**注意方向和第 207 題相反**）。前置關係可以傳遞：若 a 是 b 的前置、b 是 c 的前置，則 a 也是 c 的前置。另外給 `queries`，每個 `[u, v]` 問「u 是否為 v 的前置課程（直接或間接）」，回傳一個布林陣列。限制：`2 <= n <= 100`，`0 <= len(prerequisites) <= n(n − 1)/2`，前置關係保證無環且不重複，`1 <= len(queries) <= 10⁴`。

- 範例 1：`n = 2`、`prerequisites = [[1, 0]]`、`queries = [[0, 1], [1, 0]]`，回傳 `[False, True]`：1 是 0 的前置，反過來不是。
- 範例 2：`n = 3`、`prerequisites = [[1, 2], [1, 0], [2, 0]]`、`queries = [[1, 0], [1, 2]]`，回傳 `[True, True]`。
- 範例 3：`n = 5`、`prerequisites = [[0, 1], [1, 2], [0, 3], [3, 2], [2, 4]]`、`queries = [[0, 4], [3, 1], [1, 4]]`，回傳 `[True, False, True]`：0 經由 1 或 3 到 2 再到 4；3 和 1 是兩條平行的分支。
- 範例 4（邊界）：`n = 2`、`prerequisites = []`、`queries = [[1, 0], [0, 1]]`，回傳 `[False, False]`。

### 思路

最直接的做法是每個查詢做一次 BFS／DFS，看 u 能不能走到 v，每次 O(V + E)，總共 O(Q · (V + E))；Q = 10⁴、E ≈ 5000 時約 5 × 10⁷，Python 中偏慢，而且大量查詢會重複走同樣的路。既然 n 只有 100，更好的方向是**先把所有點對的可達關係一次算好**（transitive closure，遞移閉包），之後每個查詢 O(1)。

一種方法是 Floyd–Warshall 風格的三重迴圈：`reach[i][j] |= reach[i][k] and reach[k][j]`，O(n³) = 10⁶，完全可行，也很好寫。另一種方法利用拓撲順序：定義 `anc[v]` 為 v 所有前置課程（祖先）的集合，則 `anc[v]` 等於 v 的每個直接前置 u 的 `anc[u] ∪ {u}` 的聯集。這是 16.5 節的 DP 形式，只要按拓撲順序計算，處理 v 時它所有直接前置的集合都已經完整。

集合用 Python 整數當 bitset（位元集合）：第 u 個位元為 1 代表 u 是祖先，聯集就是 `|`。每次 `|` 處理 n 個位元，實際成本約 n / 64 個機器字，所以總時間是 O(V + E · n / 64)，比 Floyd 的 n³ 少很多；查詢 `(u, v)` 就是看 `anc[v]` 的第 u 位。兩種方法在 n = 100 時都很快，面試時建議先講 Floyd（最簡單），再講拓撲加 bitset（展示你知道怎麼利用 DAG 結構），程式寫後者。

```text
範例 3：n = 5，prerequisites = [[0,1], [1,2], [0,3], [3,2], [2,4]]
邊（前置 → 課程）：0→1, 1→2, 0→3, 3→2, 2→4

      ┌──→ 1 ──┐
      0        2 ──→ 4
      └──→ 3 ──┘

anc 以位元表示，位元順序寫成 {集合}（實際是整數 bitset）
Kahn 取出順序：0, 1, 3, 2, 4
取出  傳遞                                     結果
 0    anc[1] |= anc[0] | {0}  → {0}
      anc[3] |= anc[0] | {0}  → {0}
 1    anc[2] |= anc[1] | {1}  → {0, 1}
 3    anc[2] |= anc[3] | {3}  → {0, 1, 3}
 2    anc[4] |= anc[2] | {2}  → {0, 1, 2, 3}
 4    —

查詢 [0,4]：0 ∈ anc[4] → True
查詢 [3,1]：3 ∈ anc[1] = {0}? → False
查詢 [1,4]：1 ∈ anc[4] → True
```

取出 2 的時刻，`anc[2]` 已經同時收到了 1 那條分支與 3 那條分支的祖先，因為 Kahn 保證 2 要等 1 和 3 都取出後入度才歸零。這就是拓撲順序對 DP 的意義：v 的值在它被取出時已經是最終值，可以安心往下傳。

### 解法

```python
import random
from collections import deque


def check_if_prerequisite(n: int, prerequisites: list[list[int]],
                          queries: list[list[int]]) -> list[bool]:
    graph = [[] for _ in range(n)]
    indegree = [0] * n
    for a, b in prerequisites:                 # [a, b]：a 是 b 的前置，邊 a → b
        graph[a].append(b)
        indegree[b] += 1
    anc = [0] * n                              # anc[v] 的第 u 位 = u 是否為 v 的祖先
    queue = deque(u for u in range(n) if indegree[u] == 0)
    while queue:
        u = queue.popleft()
        for v in graph[u]:
            anc[v] |= anc[u] | (1 << u)
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)
    return [bool(anc[v] >> u & 1) for u, v in queries]


def check_floyd(n, prerequisites, queries):
    reach = [[False] * n for _ in range(n)]
    for a, b in prerequisites:
        reach[a][b] = True
    for k in range(n):
        for i in range(n):
            if reach[i][k]:
                for j in range(n):
                    if reach[k][j]:
                        reach[i][j] = True
    return [reach[u][v] for u, v in queries]


assert check_if_prerequisite(2, [[1, 0]], [[0, 1], [1, 0]]) == [False, True]
assert check_if_prerequisite(3, [[1, 2], [1, 0], [2, 0]], [[1, 0], [1, 2]]) == [True, True]
assert check_if_prerequisite(5, [[0, 1], [1, 2], [0, 3], [3, 2], [2, 4]],
                             [[0, 4], [3, 1], [1, 4]]) == [True, False, True]
assert check_if_prerequisite(2, [], [[1, 0], [0, 1]]) == [False, False]
for _ in range(300):
    n = random.randint(2, 8)
    perm = random.sample(range(n), n)              # 依這個順序只產生「往後」的邊，保證無環
    pairs = {tuple(sorted(random.sample(range(n), 2))) for _ in range(random.randint(0, 12))}
    pre = [[perm[i], perm[j]] for i, j in pairs]
    qs = [[random.randrange(n), random.randrange(n)] for _ in range(10)]
    qs = [q for q in qs if q[0] != q[1]]
    assert check_if_prerequisite(n, pre, qs) == check_floyd(n, pre, qs)
print("all tests passed")
```

### 複雜度與邊界

拓撲加 bitset：時間 O(V + E · V / w + Q)，w 是機器字長（64），因為每條邊做一次 V 位元的 OR；空間 O(V² / w) 存所有祖先集合。Floyd：時間 O(V³)，空間 O(V²)。在 n = 100、E ≤ 4950 的限制下，兩者都在毫秒級。邊界情況：沒有前置關係時所有 `anc` 都是 0，每個查詢都是 False；查詢 `[u, v]` 的方向要對應「u 是 v 的祖先」，所以是檢查 `anc[v]` 的第 u 位，而不是 `anc[u]` 的第 v 位；題目保證無環，若不保證，Kahn 會漏掉環上與被環擋住的節點，祖先集合不完整，見 F3。

### Follow-up

> [!question]- F1. 如果 n 高達 10⁵、邊數 10⁵、查詢 10⁵ 呢？
> 完整的遞移閉包需要 n² = 10¹⁰ 個位元，放不下；每個查詢各做一次 BFS 又是 10¹⁰ 級。一般 DAG 的可達性查詢沒有已知的「線性前處理 + O(1) 查詢」方法，實務做法是分塊 bitset：每次只處理 64（或 Python 中更大的整數寬度）個來源節點，沿拓撲順序傳遞一個代表「被這批來源中哪些可達」的位元遮罩，每批 O(V + E)，總共 O((V + E) · V / w)，再把查詢按來源分批回答。若圖是一棵樹（每門課只有一個直接前置），就可以用 DFS 的進出時間戳：u 是 v 的祖先 ⇔ `tin[u] <= tin[v] and tout[v] <= tout[u]`，O(n) 前處理、O(1) 查詢。

> [!question]- F2. 如果要回傳每門課總共有幾門（直接或間接）前置課程呢？
> 算完 `anc` 之後，每門課的答案就是 `anc[v].bit_count()`（Python 3.10 起），整體 O(V · V / w)。注意不能只用「直接前置數的總和」或「沿路徑累加」計算，因為菱形結構會讓同一個祖先從兩條路被數兩次：範例 3 中 2 的祖先是 {0, 1, 3}，共 3 門，但如果把 1 的 1 門和 3 的 1 門加上 1、3 本身，就會得到 4，把 0 算了兩次。集合聯集正是用來去重的。

> [!question]- F3. 如果前置關係可能有環（例如「互相建議先修」），要回答可達性呢？
> 先求 SCC，把每個強連通元件縮成一個節點，得到的 condensation graph（縮點圖）一定是 DAG。同一個 SCC 內的任兩個節點互相可達；不同 SCC 之間的可達性，就在縮點圖上用本題的拓撲加 bitset 計算。總時間 O(V + E) 求 SCC，再加上本題的 O(E · V / w)。這是「有環圖先縮點再拓撲排序」的標準套路，第 18 章難題 5 的 Tarjan 演算法用的是同一種 low-link 技巧。

> [!question]- F4. 如果除了「是不是前置」，還要回答「最少要經過幾門課」呢？
> 可達性只需要 OR，最短距離需要 min 與加法：`dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])`，仍可用 Floyd–Warshall，O(V³)。也可以從每個來源 u 做一次 BFS（邊權皆為 1），O(V · (V + E))，n = 100 時都很快。若要的是「最多經過幾門課」（最長鏈），在 DAG 上可以從每個來源沿拓撲順序做最長路徑 DP，O(V · (V + E))；在一般圖上最長簡單路徑是 NP-hard，這又是 DAG 結構帶來的好處。

## 難題 1｜269. Alien Dictionary｜Hard

### 題目

某種外星語言使用小寫英文字母，但字母之間的順序和英文不同、而且未知。給你一份這種語言的字典 `words`，字串之間已經**依照外星字母順序做字典序排列**。請推出一個與這份字典一致的字母順序，回傳一個由所有出現過的字母（各出現一次）組成的字串；如果有多種可能，回傳任一種；如果字典本身矛盾、不存在任何一致的順序，回傳空字串。字典序的規則和一般相同：從第一個字元開始比，第一個不同的字元決定先後；若一個字串是另一個的前綴，較短的排在前面。限制：`1 <= len(words) <= 100`，`1 <= len(words[i]) <= 100`。

- 範例 1：`words = ["wrt", "wrf", "er", "ett", "rftt"]`，回傳 `"wertf"`。
- 範例 2：`words = ["baa", "abcd", "abca", "cab", "cad"]`，回傳 `"bdac"`，這也是唯一合法的答案。
- 範例 3：`words = ["z", "x", "z"]`，回傳 `""`：由前兩個字得到 z 在 x 前，由後兩個字得到 x 在 z 前，矛盾。
- 範例 4（邊界）：`words = ["abc", "ab"]`，回傳 `""`：「ab」是「abc」的前綴，卻排在後面，任何字母順序都不可能。`words = ["z", "z"]` 則回傳 `"z"`。

### 提示

> [!tip]- 提示 1
> 字典序只透過「第一個不同的字元」傳遞資訊。比較兩個相鄰的字，你能得到什麼關於字母順序的結論？

> [!tip]- 提示 2
> 每一對相鄰字串的第一個不同字元 `a`、`b` 給出一條邊 `a → b`（a 排在 b 前面）。只需要比較相鄰的字串，不需要比較所有字串對。接著要找一個滿足所有邊的字母順序。

> [!tip]- 提示 3
> 對字母做拓撲排序。兩種情況要回傳空字串：圖中有環；或某一對相鄰字串中，前一個字比後一個長、而後一個是前一個的前綴。所有出現過的字母都是節點，即使它沒有任何邊。

### 詳解

**為什麼直覺做法不夠**。暴力解是枚舉 26! 種字母排列，檢查字典是否依該順序排序，完全不可行。另一個常見的錯誤直覺是「同一位置的字元依序出現的順序就是字母順序」，例如把每個字的第一個字母依序列出來；但只有在前面的字元都相同時，後面的字元才有比較意義，`"wrt"` 與 `"er"` 的第二個字元 r 和 r 之間並沒有任何關係。所以第一步必須精確地從字典中萃取出「真正有被保證的」先後關係。

**萃取邊：只看相鄰字串的第一個不同字元**。兩個字串 s < t（在外星順序下），從左往右比，第一個不同的位置 i 上必定有 `s[i]` 在 `t[i]` 之前，i 之後的字元沒有任何資訊。為什麼只比相鄰的字就夠？因為「整份字典有序」等價於「每一對相鄰的字有序」（字典序是遞移的）：若某個字母順序讓所有相鄰對都有序，整份字典自然有序；反之亦然。所以相鄰對產生的邊集合，恰好刻畫了「字母順序一致」的充要條件，不多也不少。比較非相鄰的字只會得到被這些邊推得出來的冗餘邊。

**兩種矛盾**。第一種是前綴矛盾：相鄰的 s、t 在較短者的長度內完全相同，但 s 比 t 長，例如 `"abc"` 在 `"ab"` 前面。這不是任何字母順序能修補的，必須直接回傳空字串，而且這種情況不會產生任何邊，所以拓撲排序本身偵測不到，一定要特判。第二種是循環矛盾：邊形成環，例如 z → x 且 x → z，Kahn 演算法取不完所有字母。只有這兩種情況會無解；只要沒有前綴矛盾且邊集合無環，任一個拓撲順序都讓所有相鄰對有序。

**節點與重複邊**。所有出現在任何字串中的字母都必須輸出，即使它不參與任何比較：例如 `["ab", "adc"]` 只給出 b → d，a 和 c 沒有任何邊，但答案仍要包含 a、b、c、d 四個字母，沒有邊的字母可以放在任何位置。同一條邊也可能從多對相鄰字串得到，例如 `["ab", "b", "ca", "cb"]` 中第一對與第三對都給出 a → b。用 `set` 去重邊時，入度也必須只在「新增成功」時加 1，否則入度永遠降不到 0，這是 16.6 節表格中「去重與入度不一致」的典型陷阱。

```text
範例 2：words = ["baa", "abcd", "abca", "cab", "cad"]

相鄰比較                   第一個不同的位置    得到的邊
"baa"  vs "abcd"           0：b vs a            b → a
"abcd" vs "abca"           3：d vs a            d → a
"abca" vs "cab"            0：a vs c            a → c
"cab"  vs "cad"            2：b vs d            b → d

字母圖：
      b ──→ d ──→ a ──→ c
      │           ↑
      └───────────┘

入度：a:2  b:0  c:1  d:1           queue = [b]
步驟  取出  更新                    queue     順序
 1     b    a:2→1，d:1→0 入隊       [d]       b
 2     d    a:1→0 入隊              [a]       bd
 3     a    c:1→0 入隊              [c]       bda
 4     c    —                       []        bdac
取出 4 個 = 字母數 4 → 回傳 "bdac"
```

每一步 queue 裡都只有一個字母，所以這個順序是唯一的（核心題 2 F2 的判準）。如果把最後一個字 `"cad"` 拿掉，就少了 b → d 這條邊，只剩 b → a、d → a、a → c：b 和 d 都在 a 前面，但彼此沒有先後，queue 一開始會同時有 b 和 d，`"bdac"` 與 `"dbac"` 都合法，答案就不唯一了。

### 解法

```python
import random
from collections import deque
from itertools import permutations


def alien_order(words: list[str]) -> str:
    letters = {c for w in words for c in w}
    graph = {c: set() for c in letters}
    indegree = {c: 0 for c in letters}
    for s, t in zip(words, words[1:]):
        for a, b in zip(s, t):
            if a != b:
                if b not in graph[a]:          # 去重：只有新邊才增加入度
                    graph[a].add(b)
                    indegree[b] += 1
                break
        else:                                  # 較短長度內完全相同
            if len(s) > len(t):
                return ""                      # 前綴矛盾，例如 "abc" 在 "ab" 前
    queue = deque(sorted(c for c in letters if indegree[c] == 0))
    order = []
    while queue:
        c = queue.popleft()
        order.append(c)
        for d in sorted(graph[c]):             # 排序只是讓輸出可重現
            indegree[d] -= 1
            if indegree[d] == 0:
                queue.append(d)
    return "".join(order) if len(order) == len(letters) else ""


def consistent(words, order):
    rank = {c: i for i, c in enumerate(order)}
    keys = [[rank[c] for c in w] for w in words]
    return all(a <= b for a, b in zip(keys, keys[1:]))


def brute_exists(words):
    letters = sorted({c for w in words for c in w})
    return any(consistent(words, p) for p in permutations(letters))


assert alien_order(["wrt", "wrf", "er", "ett", "rftt"]) == "wertf"
assert alien_order(["baa", "abcd", "abca", "cab", "cad"]) == "bdac"
assert alien_order(["z", "x", "z"]) == ""
assert alien_order(["abc", "ab"]) == ""
assert alien_order(["z", "z"]) == "z"
assert sorted(alien_order(["ab", "adc"])) == ["a", "b", "c", "d"]      # c 沒有任何邊也要輸出
for _ in range(800):
    alphabet = random.sample("abcde", random.randint(1, 5))
    words = ["".join(random.choice(alphabet) for _ in range(random.randint(1, 3)))
             for _ in range(random.randint(1, 6))]
    if random.random() < 0.6:                  # 多數測資是「真的依某個順序排好」的字典
        secret = random.sample(alphabet, len(alphabet))
        words.sort(key=lambda w: [secret.index(c) for c in w])
    got = alien_order(words)
    if got:
        assert sorted(got) == sorted({c for w in words for c in w}) and consistent(words, got)
    else:
        assert not brute_exists(words)
print("all tests passed")
```

### 複雜度與邊界

設 C 為所有字串的總長度、U 為不同字母數（≤ 26）。萃取邊時每對相鄰字串最多比到較短者的長度，總共 O(C)；邊數最多 min(len(words) − 1, U²)，拓撲排序 O(U + U²)，所以總時間 O(C)，空間 O(U²)（加上 O(U) 的入度）。程式中為了輸出可重現而做的 `sorted` 只作用在至多 26 個字母上，不影響複雜度。邊界情況：只有一個字時沒有任何邊，回傳它的所有字母（任意順序）；相鄰兩字完全相同時不產生邊也不矛盾；前綴矛盾一定要在 `for … else` 中特判；字母只出現在某些字的「第一個不同位置之後」時，它不會有邊，但仍要輸出。

### Follow-up

> [!question]- F1. 如果要求在答案不唯一時回傳字典序（以英文字母順序）最小的那一個呢？
> 把 queue 換成 min-heap，每次從入度為 0 的字母中挑英文順序最小的，理由和核心題 2 F1 相同：第一個位置只能從入度為 0 的字母中選，選最小的不會更差，之後的問題是同型的子問題。字母最多 26 個，時間仍是 O(C + U² + U log U)。面試官有時會改問「若答案不唯一就回傳空字串」，那就在 Kahn 的每一步檢查 queue 的大小是否為 1。

> [!question]- F2. 如果改成給你字母順序，要驗證字典是否有序呢（953. Verifying an Alien Dictionary）？
> 建 `rank[c]`，依序比較每一對相鄰字串：找到第一個不同的字元，比較兩者的 rank；若前者較大就回傳 False；若完全相同到較短者結束，且前一個字比較長，也回傳 False。只比較相鄰對已經足夠，理由同詳解中的遞移性。時間 O(C)。也可以直接把每個字轉成 rank 的串列再用 Python 的串列比較，寫法更短，但會多 O(C) 的空間。

> [!question]- F3. 如果要列出所有可能的字母順序呢？
> 用 backtracking 枚舉所有拓撲順序：維護目前的入度，在每一步嘗試每一個入度為 0、尚未使用的字母，把它加入順序、扣減後繼的入度後遞迴，返回時恢復入度。每個完整的順序花 O(U + E) 產生，總時間 O(答案個數 × (U + E))，答案個數最多 U!，這是輸出大小本身的下限。若只要「個數」不要列出，U ≤ 20 左右可以用 bitmask DP（核心題 2 F4），26 個字母時 2²⁶ ≈ 6.7 × 10⁷ 個狀態，在 Python 中偏重但在 C++ 中可行。

> [!question]- F4. 如果字典很大（例如 10⁶ 個字），而且是分批串流進來的呢？
> 萃取邊只需要「上一個字」和「這一個字」，所以可以邊讀邊比，只保留前一個字串與一張至多 26 × 26 的邊表，記憶體 O(最長字長 + U²)，不需要存整份字典。前綴矛盾在讀到的當下就能回報。拓撲排序在最後一次做，O(U²)。如果中途要隨時回報「目前是否矛盾」，每新增一條邊時用一次 O(U²) 的 DFS 檢查新邊是否形成環即可，因為邊最多只有 U² 條，總成本有上限 O(U⁴)，與字典大小無關。

### 心得

關鍵突破是「只有相鄰兩字的第一個不同字元帶有資訊，而且這些邊恰好就是全部的限制」，把字串問題轉成字母上的拓撲排序。它和核心題 2 的差別在於圖要自己從資料中萃取，並且有一種拓撲排序偵測不到的矛盾（前綴），所以面試時最容易失分的地方不是 Kahn，而是建圖的三個細節：前綴矛盾的特判、沒有邊的字母也要輸出、去重邊時入度要一致。講解時建議先用範例畫出邊表，再說「接下來就是第 210 題」，最後主動列出這三個邊界，面試官通常會特別追問前綴的情況。

## 難題 2｜329. Longest Increasing Path in a Matrix｜Hard

### 題目

給一個 m × n 的整數矩陣 `matrix`。從任一格出發，每一步可以往上、下、左、右移動到相鄰的格子（不能斜走、不能走出邊界），而且**每一步移動到的格子的值都必須嚴格大於目前格子**。請回傳最長的遞增路徑包含幾個格子。限制：`1 <= m, n <= 200`，`0 <= matrix[i][j] <= 2³¹ − 1`。

- 範例 1：`matrix = [[9, 9, 4], [6, 6, 8], [2, 1, 1]]`，回傳 `4`，路徑之一是 1 → 2 → 6 → 9。
- 範例 2：`matrix = [[3, 4, 5], [3, 2, 6], [2, 2, 1]]`，回傳 `4`，路徑是 3 → 4 → 5 → 6。
- 範例 3（邊界）：`matrix = [[1]]`，回傳 `1`：單一格子本身就是長度 1 的路徑。
- 範例 4（邊界）：所有格子的值都相同，例如 `[[7, 7], [7, 7]]`，回傳 `1`：不能走到相等的格子。

### 提示

> [!tip]- 提示 1
> 從每一格出發做 DFS 會重複探索大量相同的子路徑。從某一格出發的最長路徑長度，只取決於那一格本身，能不能存起來？

> [!tip]- 提示 2
> 「只能往更大的值走」代表這張圖一定沒有環：沿著任何路徑值都嚴格遞增，不可能回到起點。把每一格當節點、從小值指向相鄰的大值，這是一個 DAG。

> [!tip]- 提示 3
> 在這個 DAG 上求最長路徑。用 Kahn 演算法：入度是「比自己小的鄰居個數」，從所有局部最小值開始一層層 BFS，總層數就是答案。這樣完全不需要遞迴。

### 詳解

**為什麼直覺做法不夠**。對每一格做一次不加記憶的 DFS，探索所有遞增路徑，最差情況下路徑數是指數級的（例如 `matrix[r][c] = r + c` 這種往右、往下都遞增的棋盤，光是從左上角走到右下角的遞增路徑就有 C(m + n − 2, m − 1) 種）。加上 memoization（記憶化）之後，`longest(r, c) = 1 + max(longest(相鄰且更大的格子))`，每格只算一次，O(mn)，這是大多數人第一個寫出的正確解。但它在 Python 中有一個真實的問題：遞迴深度可以和路徑長度一樣長，一條蛇形遞增的路徑可以長達 40000 格，遠超 Python 的預設遞迴上限，`sys.setrecursionlimit` 調大也可能讓直譯器的 C 堆疊溢位。

**突破點：這是一個隱式 DAG**。memoization 之所以正確，是因為「往更大的值走」不可能形成環，所以遞迴不會無限展開，每格的答案只依賴值更大的鄰居。換個角度，這正是 16.5 節的拓撲順序 DP：把每格看成節點，邊從小值指向相鄰的大值，題目就是求 DAG 的最長路徑（以節點數計）。DAG 最長路徑在拓撲順序上 O(V + E) 就能求出，而這裡 V = mn、E ≤ 4mn。

**用 Kahn 的層數當答案**。每格的入度是「值比它小的相鄰格子數」，入度為 0 的格子是局部最小值，路徑一定能從它們開始。Kahn 一層一層處理：第 1 層是所有局部最小值，處理一層時把它們指向的大鄰居入度減 1，歸零的進入下一層。一個格子在第 k 層被取出，代表以它為終點的最長路徑恰好有 k 個格子：它的所有小鄰居都在更早的層，而且至少有一個在第 k − 1 層（否則它會更早歸零）。所以總層數就是全圖最長路徑的長度。整個過程沒有遞迴，深度問題自然消失。

**另一種拓撲順序：排序**。值越小的格子越早處理，本身就是一個合法的拓撲順序（每條邊都從小值指向大值）。所以也可以把所有格子按值排序，依序計算 `dp[r][c] = 1 + max(dp[較小的鄰居])`，O(mn log mn)。這個寫法比 Kahn 短，但多了排序的 log 因子；它也展示了一個重要的觀念：**拓撲順序不一定要用 Kahn 算出來**，只要找得到一個保證「邊從前指向後」的順序就行，例如按值、按時間、按座標。

```text
範例 1：
        c0  c1  c2
  r0     9   9   4
  r1     6   6   8
  r2     2   1   1

入度（比自己小的相鄰格子數）：
  r0     1   2   0
  r1     1   1   3
  r2     1   0   0

第 1 層：(0,2)=4  (2,1)=1  (2,2)=1                     ← 局部最小值
  (0,2)=4 → (0,1)=9 入度 2→1；(1,2)=8 入度 3→2
  (2,1)=1 → (2,0)=2 入度 1→0；(1,1)=6 入度 1→0
  (2,2)=1 → (1,2)=8 入度 2→1
第 2 層：(2,0)=2  (1,1)=6
  (2,0)=2 → (1,0)=6 入度 1→0
  (1,1)=6 → (0,1)=9 入度 1→0；(1,2)=8 入度 1→0       （(1,0)=6 相等，不是邊）
第 3 層：(1,0)=6  (0,1)=9  (1,2)=8
  (1,0)=6 → (0,0)=9 入度 1→0
第 4 層：(0,0)=9
共 4 層 → 答案 4，對應路徑 1 → 2 → 6 → 9（(2,1) → (2,0) → (1,0) → (0,0)）
```

注意 (1,1) 和 (1,0) 都是 6，它們之間沒有邊，所以 (1,0) 要等 (2,0)=2 處理完才歸零。(0,1)=9 在第 3 層，因為它最長只能從 1 → 6 → 9 走來；(0,0)=9 卻在第 4 層，因為它可以接在 1 → 2 → 6 後面。層數不是值的大小，而是「最長能接多長」。

### 解法

```python
import random
from collections import deque


def longest_increasing_path(matrix: list[list[int]]) -> int:
    m, n = len(matrix), len(matrix[0])
    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
    indegree = [[0] * n for _ in range(m)]
    for r in range(m):
        for c in range(n):
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < m and 0 <= nc < n and matrix[nr][nc] < matrix[r][c]:
                    indegree[r][c] += 1
    queue = deque((r, c) for r in range(m) for c in range(n) if indegree[r][c] == 0)
    layers = 0
    while queue:
        layers += 1
        for _ in range(len(queue)):            # 一次處理一整層
            r, c = queue.popleft()
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < m and 0 <= nc < n and matrix[nr][nc] > matrix[r][c]:
                    indegree[nr][nc] -= 1
                    if indegree[nr][nc] == 0:
                        queue.append((nr, nc))
    return layers


def longest_by_sorting(matrix: list[list[int]]) -> int:
    m, n = len(matrix), len(matrix[0])
    dp = [[1] * n for _ in range(m)]
    for v, r, c in sorted((matrix[r][c], r, c) for r in range(m) for c in range(n)):
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < m and 0 <= nc < n and matrix[nr][nc] < v:
                dp[r][c] = max(dp[r][c], dp[nr][nc] + 1)
    return max(map(max, dp))


def brute(matrix):
    m, n = len(matrix), len(matrix[0])

    def go(r, c):
        best = 1
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < m and 0 <= nc < n and matrix[nr][nc] > matrix[r][c]:
                best = max(best, 1 + go(nr, nc))
        return best

    return max(go(r, c) for r in range(m) for c in range(n))


assert longest_increasing_path([[9, 9, 4], [6, 6, 8], [2, 1, 1]]) == 4
assert longest_increasing_path([[3, 4, 5], [3, 2, 6], [2, 2, 1]]) == 4
assert longest_increasing_path([[1]]) == 1
assert longest_increasing_path([[7, 7], [7, 7]]) == 1
assert longest_increasing_path([[1, 2, 3, 4, 5]]) == 5
snake = [[r * 200 + (c if r % 2 == 0 else 199 - c) for c in range(200)] for r in range(200)]
assert longest_increasing_path(snake) == 40000          # 遞迴版在這裡會超過遞迴深度
for _ in range(300):
    m, n = random.randint(1, 4), random.randint(1, 4)
    g = [[random.randint(0, 6) for _ in range(n)] for _ in range(m)]
    assert longest_increasing_path(g) == longest_by_sorting(g) == brute(g)
print("all tests passed")
```

### 複雜度與邊界

Kahn 版本時間 O(mn)：每格入隊出隊一次，每格檢查 4 個鄰居兩次（算入度一次、減入度一次）；空間 O(mn) 存入度與 queue。排序版本時間 O(mn log mn)、空間 O(mn)。記憶化 DFS 也是 O(mn)，但遞迴深度最差 O(mn)。邊界情況：單一格子時它的入度為 0，一層就結束，回傳 1；全部相等時每格入度都是 0，全部在第 1 層，回傳 1；相等的鄰居既不算入度也不算出邊，比較必須用嚴格的 `<` 與 `>`；值可到 2³¹ − 1，Python 沒有溢位問題，題目也只比較大小。

### Follow-up

> [!question]- F1. 如果要回傳路徑本身，而不只是長度呢？
> 用排序版本最直接：計算 `dp` 時同時記錄 `parent[r][c]`，也就是讓 `dp[r][c]` 達到最大值的那個較小鄰居。最後從 `dp` 最大的格子出發，沿 `parent` 往回走到局部最小值，再把序列反轉。Kahn 版本也可以：在減入度時，若 `層數[鄰居] = 層數[自己] + 1` 就記錄 parent。時間與空間都仍是 O(mn)（排序版多一個 log 因子），只是多存一張 parent 表。

> [!question]- F2. 如果要計算「嚴格遞增路徑的總數」呢（2328. Number of Increasing Paths in a Grid）？
> 把 max 換成加法：`cnt[r][c] = 1 + Σ cnt[較小的鄰居]`，代表以 (r, c) 結尾的遞增路徑數（1 是只含自己的路徑），按拓撲順序（排序或 Kahn）計算，答案是所有格子的總和，題目通常要求對 10⁹ + 7 取模。時間 O(mn)（Kahn）或 O(mn log mn)（排序）。這和 16.5 節模板中 `ways` 的計算一模一樣，再次說明「拓撲順序 + 沿邊傳遞」可以套用任何可結合的運算。

> [!question]- F3. 如果允許走到「相等」的格子（非嚴格遞增），但每格只能走一次呢？
> 圖就有環了（相等的相鄰格子可以來回），問題變成在一般圖上找最長簡單路徑，這是 NP-hard，就算限制在格子圖上，判斷是否存在 Hamiltonian path 也是 NP-complete，所以沒有多項式解。面試中能指出這一點很加分。如果題目改成「相等的格子可以重複經過，但只算『不同的值』的個數」，就可以先把相等且相連的格子用 BFS 或 Union-Find（第 17 章）縮成一個節點，縮完之後又是 DAG，再做最長路徑。

> [!question]- F4. 如果矩陣非常大（例如 10⁴ × 10⁴），無法一次放進記憶體呢？
> 排序版本需要全域排序，不適合。Kahn 版本的每一層可以分散在任何位置，也不適合串流。可行的做法是按值域分批：把格子按值分成若干區間，從最小的值區間開始處理，每格的 dp 只依賴更小值的鄰居，而那些鄰居一定在已處理的批次中；因此只要把每格的 dp 存在磁碟（或與矩陣同樣大小的外部陣列）中，依值的順序逐批讀取並更新。這本質上仍是「按值排序是拓撲順序」，只是把排序換成外部排序（external sort），I/O 成本 O((mn / B) log(mn / B))，B 是區塊大小。

### 心得

關鍵突破是看出「嚴格遞增」讓格子圖自動成為 DAG，於是最長遞增路徑就是 DAG 的最長路徑，Kahn 的層數就是答案。它和本章其他題的差別在於圖是隱式的：沒有人給你邊，邊由「相鄰且更大」動態決定，入度也要自己算。面試時通常先寫記憶化 DFS（最自然），然後主動提出「這個 DAG 的路徑最長可以有 40000 格，Python 遞迴會爆，我改成 Kahn 按層 BFS」，再說明層數為什麼等於最長路徑長度。能把記憶化 DFS 與拓撲排序說成同一件事的兩種寫法，是這題最有說服力的講法。

## 難題 3｜1203. Sort Items by Groups Respecting Dependencies｜Hard

### 題目

有 n 個項目（編號 0 到 n − 1）與 m 個組（編號 0 到 m − 1）。`group[i]` 是項目 i 所屬的組，`-1` 代表它不屬於任何組。`beforeItems[i]` 列出所有必須排在項目 i **之前**的項目。請回傳一個包含全部 n 個項目的排列，同時滿足：第一，同一組的項目在排列中**彼此相鄰**（連成一段）；第二，`beforeItems` 的所有先後關係都成立。有多個答案時回傳任一個；不存在時回傳空陣列。限制：`1 <= m <= n <= 3 × 10⁴`，`beforeItems[i]` 不含重複、也不含 i 自己。

- 範例 1：`n = 6`、`m = 2`、`group = [-1, 0, 0, 1, 1, -1]`、`beforeItems = [[], [3], [1], [], [3], [2]]`，一個合法答案是 `[3, 4, 0, 1, 2, 5]`：組 1 的 {3, 4} 連在一起、組 0 的 {1, 2} 連在一起，而且 3 在 1、4 之前，1 在 2 之前，2 在 5 之前。
- 範例 2：`n = 8`、`m = 2`、`group = [-1, -1, 1, 0, 0, 1, 0, -1]`、`beforeItems = [[], [6], [5], [6], [3, 6], [], [], []]`，一個合法答案是 `[6, 3, 4, 1, 5, 2, 0, 7]`。
- 範例 3：`n = 3`、`m = 2`、`group = [0, 1, 0]`、`beforeItems = [[], [0], [1]]`，回傳 `[]`。項目之間 0 → 1 → 2 沒有環，但 0、2 同組而 1 在別組，組 0 必須同時在組 1 之前與之後。
- 範例 4（邊界）：`n = 2`、`m = 1`、`group = [0, 0]`、`beforeItems = [[1], [0]]`，回傳 `[]`：同一組內部有環。

### 提示

> [!tip]- 提示 1
> 如果沒有「同組相鄰」的限制，這就是核心題 2。相鄰的限制代表每一組可以被當成一個整體來排序。那麼組與組之間的先後關係從哪裡來？

> [!tip]- 提示 2
> 項目 p 必須在 i 之前，而兩者屬於不同組，就代表 p 的組必須整個排在 i 的組之前。這給出一張「組的依賴圖」。組內的順序則由組內的項目依賴決定。`-1` 的項目要怎麼處理才不必特判？

> [!tip]- 提示 3
> 先給每個 `-1` 的項目一個獨立的新組號。然後做兩次拓撲排序：一次在項目圖上（所有依賴），一次在組圖上（跨組的依賴）。任一個有環就無解；否則依組的順序輸出，每組內部依項目拓撲順序中的相對順序輸出。

### 詳解

**為什麼直覺做法不夠**。直接對項目做一次拓撲排序，可以滿足依賴，卻不保證同組相鄰：範例 1 的 Kahn 順序是 `[0, 3, 1, 4, 2, 5]`，組 1 的 3 和 4 中間夾了 1。試圖在 Kahn 過程中「優先挑同組的項目」也不可靠：某組的下一個項目可能還在等另一組的項目，這時被迫切換組，之前那組就被切成兩段，而且這種貪婪在可行的輸入上也可能失敗。問題的根源是兩層限制混在一起：組與組的先後是一個拓撲問題，組內的先後是另一個拓撲問題，應該把它們分開。

**把 -1 變成獨立的組**。不屬於任何組的項目沒有相鄰限制，但若把它視為「只有自己一個成員的組」，相鄰限制自動成立（一個元素永遠是連續的），兩層的處理就完全一致，不需要任何特判。實作上從 m 開始依序發新組號，組數變成 m 加上 -1 項目的個數，最多 n。

**兩張圖**。項目圖包含所有依賴邊 `p → i`。組圖只包含跨組的依賴：若 `group[p] != group[i]`，加一條 `group[p] → group[i]`；同組的依賴不進組圖（否則就是自環，會被誤判為有環）。對兩張圖各做一次 Kahn。組圖有環代表某兩組必須互相在對方之前（範例 3）；項目圖有環則可能發生在組內（範例 4），這種環在組圖中看不到，所以兩個檢查缺一不可。跨組的項目環一定會反映成組圖的環，因此兩張圖都無環時，問題一定有解。

**組合與正確性**。輸出時依組的拓撲順序逐組輸出，每組內部依「項目拓撲順序中的相對順序」輸出，做法是把項目拓撲順序依組分到各個桶子裡。為什麼正確？同組相鄰顯然成立。對任一條依賴 `p → i`：若跨組，組圖保證 p 的組整個在 i 的組之前；若同組，項目拓撲順序中 p 在 i 之前，而分桶保留了相對順序，所以組內 p 仍在 i 之前。一個拓撲順序限制到任意子集上，仍然是那個子集的合法順序，這是可以「一次排序、分桶使用」的原因。

```text
範例 1：group = [-1, 0, 0, 1, 1, -1]，beforeItems = [[], [3], [1], [], [3], [2]]
-1 重新編號：項目 0 → 組 2，項目 5 → 組 3      group = [2, 0, 0, 1, 1, 3]

依賴邊（p → i）      同組？        組圖的邊
3 → 1               1 vs 0 否      組1 → 組0
1 → 2               0 vs 0 是      —
3 → 4               1 vs 1 是      —
2 → 5               0 vs 3 否      組0 → 組3

項目 Kahn：入度 0:0 1:1 2:1 3:0 4:1 5:1
  取出 0；取出 3 → 1、4 入隊；取出 1 → 2 入隊；取出 4；取出 2 → 5 入隊；取出 5
  項目順序 = [0, 3, 1, 4, 2, 5]
組 Kahn：入度 組0:1 組1:0 組2:0 組3:1
  取出 組1 → 組0 入隊；取出 組2；取出 組0 → 組3 入隊；取出 組3
  組順序 = [1, 2, 0, 3]

分桶（保留項目順序中的相對順序）：
  組0: [1, 2]   組1: [3, 4]   組2: [0]   組3: [5]
依組順序輸出：組1 [3, 4] + 組2 [0] + 組0 [1, 2] + 組3 [5] = [3, 4, 0, 1, 2, 5]
```

注意項目順序 `[0, 3, 1, 4, 2, 5]` 本身並不滿足相鄰限制，但它只被用來決定「組內的相對順序」：組 0 取出 1、2，組 1 取出 3、4。組之間的位置完全由組順序決定，兩層資訊各司其職。

### 解法

```python
import random
from collections import deque
from itertools import permutations


def topo(adj: list[list[int]], indegree: list[int]) -> list[int]:
    queue = deque(u for u in range(len(adj)) if indegree[u] == 0)
    order = []
    while queue:
        u = queue.popleft()
        order.append(u)
        for v in adj[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)
    return order if len(order) == len(adj) else []


def sort_items(n: int, m: int, group: list[int], before_items: list[list[int]]) -> list[int]:
    group = group[:]
    for i in range(n):
        if group[i] == -1:                     # 不屬於任何組：自成一組
            group[i] = m
            m += 1
    item_adj, item_in = [[] for _ in range(n)], [0] * n
    group_adj, group_in = [[] for _ in range(m)], [0] * m
    for i in range(n):
        for p in before_items[i]:              # p 必須在 i 之前
            item_adj[p].append(i)
            item_in[i] += 1
            if group[p] != group[i]:
                group_adj[group[p]].append(group[i])
                group_in[group[i]] += 1
    item_order = topo(item_adj, item_in)
    group_order = topo(group_adj, group_in)
    if not item_order or not group_order:
        return []
    buckets = [[] for _ in range(m)]
    for i in item_order:
        buckets[group[i]].append(i)
    return [i for g in group_order for i in buckets[g]]


def valid(ans, n, group, before):
    if sorted(ans) != list(range(n)):
        return False
    pos = {x: k for k, x in enumerate(ans)}
    if any(pos[p] > pos[i] for i in range(n) for p in before[i]):
        return False
    for g in set(group) - {-1}:
        idx = sorted(pos[i] for i in range(n) if group[i] == g)
        if idx[-1] - idx[0] != len(idx) - 1:   # 不相鄰
            return False
    return True


assert sort_items(6, 2, [-1, 0, 0, 1, 1, -1], [[], [3], [1], [], [3], [2]]) == [3, 4, 0, 1, 2, 5]
ex2 = (8, 2, [-1, -1, 1, 0, 0, 1, 0, -1], [[], [6], [5], [6], [3, 6], [], [], []])
assert valid(sort_items(*ex2), ex2[0], ex2[2], ex2[3])
assert sort_items(3, 2, [0, 1, 0], [[], [0], [1]]) == []
assert sort_items(2, 1, [0, 0], [[1], [0]]) == []
assert sort_items(1, 1, [-1], [[]]) == [0]
for _ in range(400):
    n = random.randint(1, 6)
    m = random.randint(1, n)
    grp = [random.randint(-1, m - 1) for _ in range(n)]
    bef = [random.sample([j for j in range(n) if j != i], random.randint(0, min(2, n - 1)))
           for i in range(n)]
    got = sort_items(n, m, grp, bef)
    exists = any(valid(list(p), n, grp, bef) for p in permutations(range(n)))
    assert (valid(got, n, grp, bef) if got else not exists)
print("all tests passed")
```

### 複雜度與邊界

設 E 為所有 `beforeItems` 的總長度。重新編號 O(n)；建兩張圖 O(n + E)；兩次 Kahn 分別是 O(n + E) 與 O(組數 + E)，組數 ≤ n；分桶與輸出 O(n)。總時間 O(n + E)，空間 O(n + E)。邊界情況：所有項目都是 -1 時每個項目自成一組，組圖與項目圖同構，答案就是一般的拓撲排序；所有項目同一組時組圖沒有邊，答案就是項目拓撲順序；組圖可能有重複邊（兩組之間有多條跨組依賴），入度加了幾次就會減幾次，不需要去重；有些組可能沒有任何項目（題目允許），它們的桶子是空的，出現在組順序中也不影響輸出。

### Follow-up

> [!question]- F1. 能不能把兩層合併成一張圖、只做一次拓撲排序？
> 可以用虛擬節點：每組 g 加兩個節點「入口 S_g」與「出口 T_g」，組內每個項目 i 加邊 `S_g → i → T_g`；跨組依賴 `p → i` 改成 `T_{group[p]} → S_{group[i]}`，同組依賴保持 `p → i`。這張 n + 2·組數 個節點的圖無環 ⇔ 原問題有解。但普通的 Kahn 仍可能讓兩組的項目交錯，所以輸出時要改成「一旦取出 S_g，就先把 g 的項目全部處理完」：S_g 的入度歸零，代表所有指向它的 T_h 都已取出，也就是 g 的所有前置組的項目都已完成；而 g 的項目除了 S_g 之外只會等組內項目，所以用一個局部 queue 一定能把它們連續做完，最後再取出 T_g。這其實就是本題兩層做法的另一種寫法，複雜度同樣 O(n + E)。

> [!question]- F2. 如果組是巢狀的（組裡面還有子組，形成一棵階層樹），每一層都要求相鄰呢？
> 遞迴套用本題：在階層樹的每個節點上，把它的子節點（子組或項目）當成要排序的單位。每條依賴 `p → i` 只在 p 與 i 的最低共同祖先（LCA）那一層產生作用，變成「LCA 底下包含 p 的子節點 → 包含 i 的子節點」的邊；同一層內做一次 Kahn，有環就無解。每條依賴只被分配到一層，所以總共是 O(n + E) 次拓撲排序工作，加上找 LCA 的成本（樹深為 h 時，每條依賴 O(h)，或用倍增 O(log h)）。本題就是深度為 2 的特例。

> [!question]- F3. 如果無解，要說明是「組之間矛盾」還是「組內矛盾」，並指出是哪些項目？
> 兩次 Kahn 已經區分了兩種情況：組圖取不完是組之間矛盾，項目圖取不完但組圖正常則是組內矛盾。要指出具體的環，就在對應的圖上用核心題 1 F1 的三色 DFS 找環：組內環直接回報項目；組之間的環回報的是組的序列，再把每條組邊還原成造成它的那一對項目（建組圖時順便記錄每條組邊的來源 `(p, i)`）。時間 O(n + E)。面試中能把「為什麼會無解」講清楚，比只回傳空陣列更有價值。

> [!question]- F4. 如果要求每組內部的項目在合法的前提下，盡量依編號由小到大排列（組內字典序最小）呢？
> 組之間的先後完全由組順序決定，跨組的依賴已經被組順序滿足，所以組內的排列只受「組內的依賴」限制，各組可以獨立處理。對每一組只取組內邊，用 min-heap 版本的 Kahn（核心題 2 F1）得到組內字典序最小的順序，再依組順序串接。所有組的總成本是 O((n + E) log n)。注意不能直接把全域的項目 Kahn 換成 heap 再分桶：在全域順序中，一個編號小的組內項目可能因為還在等別組的前置而較晚取出，分桶後組內順序就不是「只看組內邊」時的字典序最小。各組獨立處理才把不相干的跨組限制排除乾淨。

### 心得

關鍵突破是把「同組相鄰」解讀成「組本身也要做拓撲排序」，再用「-1 自成一組」消除特判，於是問題拆成兩個獨立的第 210 題，最後用「拓撲順序限制到子集仍然合法」把兩層組合起來。它和本章其他題的關係是：核心題 2 是單層的拓撲排序；這題是兩層；F2 的巢狀版本是任意層。面試時建議先畫出範例 1 的兩張圖，說明為什麼需要兩個環檢查（範例 3 與範例 4 各對應一種），再寫一個共用的 `topo` 函式呼叫兩次，程式會短很多，也不容易在兩份 Kahn 之間抄錯變數。

## 難題 4｜1857. Largest Color Value in a Directed Graph｜Hard

### 題目

給一張有 n 個節點（編號 0 到 n − 1）、m 條邊的有向圖，以及長度為 n 的字串 `colors`，`colors[i]` 是節點 i 的顏色（小寫英文字母）。`edges[j] = [a, b]` 是一條從 a 到 b 的有向邊。一條路徑 `x1 → x2 → … → xk` 的 color value 定義為：路徑上出現次數最多的那個顏色的出現次數。請回傳所有路徑中最大的 color value；如果圖中有環，回傳 -1。限制：`1 <= n <= 10⁵`，`0 <= m <= 10⁵`，可能有自環。

- 範例 1：`colors = "abaca"`、`edges = [[0, 1], [0, 2], [2, 3], [3, 4]]`，回傳 `3`：路徑 0 → 2 → 3 → 4 的顏色是 a、a、c、a，a 出現 3 次。
- 範例 2：`colors = "a"`、`edges = [[0, 0]]`，回傳 `-1`：自環就是環。
- 範例 3：`colors = "abc"`、`edges = []`，回傳 `1`：每個節點自己就是一條路徑。
- 範例 4（邊界）：`colors = "bbbb"`、`edges = [[0, 1], [1, 2], [2, 3]]`，回傳 `4`。

### 提示

> [!tip]- 提示 1
> 有環就回傳 -1，所以題目隱含了一件事：答案只在 DAG 上有意義。先想辦法偵測環，同時得到一個處理順序。

> [!tip]- 提示 2
> 「出現次數最多的顏色」很難直接追蹤，但只有 26 種顏色。如果固定一種顏色 c，問題變成「路徑上最多能有幾個顏色 c 的節點」，這是什麼問題？

> [!tip]- 提示 3
> 固定顏色 c 時，就是 DAG 上的節點加權最長路徑（顏色為 c 的節點權重 1，其他 0）。26 種顏色可以在同一次 Kahn 中一起算：`dp[v][c]` 是「以 v 結尾的路徑中顏色 c 最多出現幾次」，沿邊取 max，取出 v 時再把 v 自己的顏色加 1。

### 詳解

**為什麼直覺做法不夠**。暴力解是列舉所有路徑並統計顏色，DAG 中路徑數可以是指數級（一串菱形就會讓路徑數倍增）。從每個節點各做一次 DFS 也一樣會重複計算。用一個 `dp[v]` 記錄「以 v 結尾的最大 color value」也不對，因為 color value 不能從前驅的 color value 推出來：前驅最好的路徑可能以顏色 b 為主，接上 v 之後，以顏色 a 為主的另一條路徑才變成最好的。也就是說，**單一數字的狀態丟失了太多資訊**。

**突破點：把狀態展開成每種顏色**。「最多的顏色出現幾次」等於「對每種顏色 c，c 出現幾次」的最大值，而「以 v 結尾的路徑上 c 最多出現幾次」是一個可以沿邊傳遞的量：`dp[v][c] = max(dp[u][c] for u in pred(v)) + (colors[v] == c)`。這是 16.5 節的最長路徑 DP，只是同時做 26 份。因為 max 與加法都只依賴前驅，按拓撲順序計算就正確。整體答案是所有 `dp[v][c]` 的最大值。

**Kahn 一次做兩件事**。這題的環偵測與 DP 用同一次 Kahn：如果取出的節點數少於 n 就回傳 -1；否則 DP 已經在取出過程中算完。實作上的小技巧是：沿邊傳遞時只取 max，等到 v 被取出時（此刻它所有前驅都已處理），才把 `dp[v][colors[v]]` 加 1。另一個觀察是答案只需要在「每個節點自己的顏色」上取最大：`dp[v][c]` 對 c ≠ `colors[v]` 的值只是從某個前驅複製過來的，而顏色 c 的計數只會在顏色為 c 的節點上增加，所以全域最大值一定出現在某個 `dp[v][colors[v]]`。

**為什麼不必限定從源點出發**。路徑可以從任何節點開始，但把路徑往前延伸到一個入度為 0 的節點，各顏色的計數只會增加或不變，所以最佳路徑可以假設從源點開始、在匯點結束。Kahn 的 `dp` 天然地考慮了所有起點：每個節點在取出時至少包含「只有自己」的路徑。

```text
範例 1：colors = "abaca"，edges = 0→1, 0→2, 2→3, 3→4
節點顏色：0:a  1:b  2:a  3:c  4:a

      0(a) ──→ 2(a) ──→ 3(c) ──→ 4(a)
       │
       └──→ 1(b)

dp 只列出 a、b、c 三欄（其他顏色都是 0）
Kahn 順序：0, 1, 2, 3, 4

取出  自己的顏色 +1 後          傳遞給後繼（逐欄取 max）
 0    dp[0] = a1 b0 c0         dp[1] = a1 b0 c0；dp[2] = a1 b0 c0
 1    dp[1] = a1 b1 c0         —
 2    dp[2] = a2 b0 c0         dp[3] = a2 b0 c0
 3    dp[3] = a2 b0 c1         dp[4] = a2 b0 c1
 4    dp[4] = a3 b0 c1         —

各節點自己的顏色欄：dp[0][a]=1, dp[1][b]=1, dp[2][a]=2, dp[3][c]=1, dp[4][a]=3
取出 5 個 = n，無環 → 答案 3
```

取出 1 時，`dp[1]` 是 a1 b1：從 0 繼承了一個 a，加上自己的 b，路徑 0 → 1 上 a、b 各一次。若只用單一數字記錄「最大 color value」，`dp[1]` 會是 1，完全不知道 a 和 b 各是幾次；這張表說明了為什麼狀態必須保留每種顏色。

### 解法

```python
import random
from collections import deque


def largest_path_value(colors: str, edges: list[list[int]]) -> int:
    n = len(colors)
    graph = [[] for _ in range(n)]
    indegree = [0] * n
    for a, b in edges:
        graph[a].append(b)
        indegree[b] += 1
    col = [ord(ch) - ord("a") for ch in colors]
    dp = [[0] * 26 for _ in range(n)]           # dp[v][c]：以 v 結尾的路徑上顏色 c 最多幾次
    queue = deque(v for v in range(n) if indegree[v] == 0)
    seen = best = 0
    while queue:
        u = queue.popleft()
        seen += 1
        dp[u][col[u]] += 1                      # 所有前驅都處理完了，才加上自己
        best = max(best, dp[u][col[u]])
        for v in graph[u]:
            dp[v] = list(map(max, dp[v], dp[u]))
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)
    return best if seen == n else -1


def brute(colors, edges):
    n = len(colors)
    graph = [[] for _ in range(n)]
    for a, b in edges:
        graph[a].append(b)
    best = 0

    def dfs(u, on_path, counts):                # 回傳 False 代表遇到環
        nonlocal best
        if u in on_path:
            return False
        on_path.add(u)
        counts[colors[u]] = counts.get(colors[u], 0) + 1
        best = max(best, max(counts.values()))
        ok = all(dfs(v, on_path, counts) for v in graph[u])
        counts[colors[u]] -= 1
        on_path.remove(u)
        return ok

    return best if all(dfs(s, set(), {}) for s in range(n)) else -1


assert largest_path_value("abaca", [[0, 1], [0, 2], [2, 3], [3, 4]]) == 3
assert largest_path_value("a", [[0, 0]]) == -1
assert largest_path_value("abc", []) == 1
assert largest_path_value("bbbb", [[0, 1], [1, 2], [2, 3]]) == 4
assert largest_path_value("ab", [[0, 1], [1, 0]]) == -1
n = 10**5                                       # 最大規模的長鏈
assert largest_path_value("ab" * (n // 2), [[i, i + 1] for i in range(n - 1)]) == n // 2
for _ in range(500):
    k = random.randint(1, 6)
    cs = "".join(random.choice("abc") for _ in range(k))
    es = [[random.randrange(k), random.randrange(k)] for _ in range(random.randint(0, 7))]
    assert largest_path_value(cs, es) == brute(cs, es)
print("all tests passed")
```

### 複雜度與邊界

時間 O((n + m) · 26)：每個節點取出一次，每條邊做一次 26 欄的逐欄 max。空間 O(n · 26 + m)：每個節點一個 26 欄的陣列，n = 10⁵ 時是 2.6 × 10⁶ 個整數，Python 中約幾十 MB，可以接受；若記憶體吃緊見 F3。邊界情況：自環讓節點入度永遠 ≥ 1，Kahn 取不完，回傳 -1；沒有邊時每個節點各自是長度 1 的路徑，答案是 1；同一對節點之間有重複邊時，入度加兩次、也減兩次，DP 的 max 重複做一次也不影響結果；有環時即使其他部分的答案已經算出，也必須回傳 -1，所以最後一定要檢查 `seen == n`。

### Follow-up

> [!question]- F1. 如果要回傳達到最大值的那條路徑呢？
> 先用本題找到最佳顏色 c* 與它的值。接著只針對 c* 再跑一次單一顏色的最長路徑 DP（權重是「顏色是否為 c*」），同時記錄每個節點的 parent，也就是讓 `dp[v]` 達到最大的那個前驅。從 `dp[v]` 最大的節點沿 parent 往回走就得到路徑。第二次只有一欄，時間 O(n + m)，空間 O(n)。不在第一次就為 26 種顏色都記 parent，是為了避免 26 倍的額外記憶體。

> [!question]- F2. 如果顏色不是 26 種，而是最多 10⁵ 種不同的整數呢？
> `dp[v]` 展開成 k 欄就是 O((n + m) · k)，k = 10⁵ 時不可行。可以改成逐色處理：對每種顏色 c 單獨做一次「權重 = 是否為 c」的最長路徑，每次 O(n + m)，記憶體 O(n)，拓撲順序只需算一次重複使用。再加一個剪枝：按顏色的總出現次數由大到小處理，一旦某顏色的總次數 ≤ 目前最佳答案，後面的顏色都不可能更好，可以提前結束。最差情況仍是 O(k · (n + m))，但在顏色分布不均時效果很好。面試時誠實說明最差界限，並給出剪枝，就是好的回答。

> [!question]- F3. 如果記憶體很緊，存不下 n × 26 的表呢？
> 把 26 種顏色拆成 26 次獨立的計算：先跑一次 Kahn 得到拓撲順序（同時偵測環），之後對每種顏色 c，沿拓撲順序做一次只有一欄的 DP：`f[v] = max(f[u] for u in pred(v)) + (col[v] == c)`，用完即丟。時間仍是 O(26 · (n + m))，記憶體降到 O(n + m)。這是典型的「用時間換空間」，而且正確性完全來自拓撲順序可以重複使用：順序只依賴圖的結構，不依賴顏色。

> [!question]- F4. 如果要的是「路徑上某兩種顏色 a、b 的出現次數差（a 的次數減 b 的次數）的最大值」呢？
> 把顏色 a 的節點權重設為 +1、顏色 b 的設為 -1、其他為 0，問題變成 DAG 上的最大權重路徑，權重可以是負的。DAG 的優點是負權重也沒關係：`g[v] = w(v) + max(0, max(g[u] for u in pred(v)))`，其中 `max(0, …)` 表示也可以從 v 重新開始路徑，按拓撲順序 O(n + m)。若要對所有 (a, b) 組合求最大值，就是 26 × 25 次，O(650 · (n + m))。這是 2272. Substring With Largest Variance 從字串推廣到 DAG 的版本，同樣是「固定顏色組合後變成一維最佳化」的思路。

### 心得

關鍵突破是把難以追蹤的「最多的顏色」展開成 26 個獨立的計數，每一個都是 DAG 上的節點加權最長路徑，於是可以在同一次 Kahn 中一起算，而 Kahn 同時負責偵測環。它和難題 2、難題 5 是同一族：都是「拓撲順序 + 最長路徑 DP」，差別只在狀態是一個數（難題 2 的層數、難題 5 的完成時間）還是一個向量（這題的 26 欄）。面試時先說明為什麼單一數字的 DP 不對（用範例中節點 1 的 a1 b1 說明），再提出每色一欄的狀態，最後強調 `dp[u][col[u]] += 1` 要在取出時做，而不是在推給後繼時做，這是最容易寫錯的地方。

## 難題 5｜2050. Parallel Courses III｜Hard

### 題目

有 n 門課，編號 **1 到 n**。`relations[j] = [prev, next]` 表示 prev 必須修完才能開始修 next。`time[i]` 是修完第 i + 1 門課需要的月數（注意 `time` 是 0-indexed，課程是 1-indexed）。規則是：任何一門課只要它所有的前置都修完了，就可以在任何時間開始；**同時修幾門課都可以**。請回傳修完所有課程所需的最少月數。題目保證先修關係構成 DAG。限制：`1 <= n <= 5 × 10⁴`，`0 <= len(relations) <= 5 × 10⁴`，`1 <= time[i] <= 10⁴`。

- 範例 1：`n = 3`、`relations = [[1, 3], [2, 3]]`、`time = [3, 2, 5]`，回傳 `8`：課 1、2 同時在第 0 個月開始，分別在第 3、2 個月結束；課 3 必須等到第 3 個月才能開始，在第 8 個月結束。
- 範例 2：`n = 5`、`relations = [[1, 5], [2, 5], [3, 5], [3, 4], [4, 5]]`、`time = [1, 2, 3, 4, 5]`，回傳 `12`：瓶頸是 3 → 4 → 5，共 3 + 4 + 5 = 12 個月。
- 範例 3（邊界）：`n = 1`、`relations = []`、`time = [7]`，回傳 `7`。
- 範例 4（邊界）：`n = 3`、`relations = []`、`time = [4, 9, 2]`，回傳 `9`：全部同時修，取最長的那門。

### 提示

> [!tip]- 提示 1
> 能同時修無限多門課，代表任何課都不必「等名額」，只需要等前置。每門課最早什麼時候能開始？

> [!tip]- 提示 2
> 課 v 最早的開始時間是它所有前置的完成時間的最大值；完成時間是開始時間加上 `time[v]`。這個遞推只依賴前驅，該用什麼順序計算？

> [!tip]- 提示 3
> 沿拓撲順序計算 `finish[v] = time[v] + max(finish[u] for u in pred(v))`（沒有前置時取 0），答案是所有 `finish` 的最大值，也就是 DAG 上「節點加權最長路徑」的長度。

### 詳解

**為什麼直覺做法不夠**。一個常見的錯誤直覺是用核心題 1 F2 的「按層」想法：第一學期修所有入度為 0 的課，等這一層全部修完再修下一層。這會浪費時間：範例 2 中第一層是課 1、2、3，層的長度是 max(1, 2, 3) = 3；第二層是課 4，耗時 4；第三層是課 5，耗時 5，加起來恰好是 12，但只是因為這個例子的瓶頸剛好是每層最長的那門。若把課 1 的時間改成 10，按層會變成 10 + 4 + 5 = 19，實際上課 4 只依賴課 3，可以在第 3 個月就開始，正確答案是 max(10, 3 + 4) + 5 = 15。不同的課應該各自「一準備好就開始」，不必等同一層的其他課。另一個直覺是模擬時間一個月一個月往前走，總月數可達 5 × 10⁸，也不可行。

**突破點：每門課越早開始越好，而且互不干擾**。因為可以同時修任意多門，讓一門課提早開始永遠不會讓其他課變晚，所以最佳排程就是「每門課都在最早可能的時間開始」（as soon as possible）。課 v 的最早開始時間是它所有前置完成時間的最大值，於是 `finish[v] = time[v] + max(finish[u])`。這個遞推只依賴前驅，沿拓撲順序計算即可，答案是 `max(finish)`。

**正確性：為什麼這就是最少月數**。這個值同時是上界與下界。上界：照「最早開始」排程是合法的（每門課都等前置完成才開始），它在 `max(finish)` 時全部完成。下界：任取一條先修鏈 `v1 → v2 → … → vk`，這些課必須依序修，任何排程都至少需要 `time[v1] + … + time[vk]` 個月；`max(finish)` 正是所有鏈中最長的一條（節點加權最長路徑），所以不可能更短。這條最長的鏈在專案管理中叫 critical path（關鍵路徑），整個方法就是 critical path method（CPM）。

```text
範例 2：relations = [[1,5], [2,5], [3,5], [3,4], [4,5]]，time = [1, 2, 3, 4, 5]

    1(1) ──────────────┐
    2(2) ──────────────┤
    3(3) ──→ 4(4) ──→ 5(5)
     └─────────────────┘（3 → 5）

括號內是修課月數；start = 所有前置 finish 的最大值，finish = start + time
Kahn 順序：1, 2, 3, 4, 5

取出  start                      finish     傳遞
 1    0                          0+1 = 1    start[5] = max(0, 1) = 1
 2    0                          0+2 = 2    start[5] = max(1, 2) = 2
 3    0                          0+3 = 3    start[5] = max(2, 3) = 3；start[4] = 3
 4    3                          3+4 = 7    start[5] = max(3, 7) = 7
 5    7                          7+5 = 12   —
答案 = max(finish) = 12，關鍵路徑 3 → 4 → 5

時間軸（月）：
  0    1    2    3    4    5    6    7    8    9   10   11   12
  [課1]
  [ 課2  ]
  [   課3     ][      課4           ][          課5             ]
```

時間軸顯示課 1、2 很早就修完了，它們有 slack（餘裕）：就算晚幾個月開始，也不會影響總時間。真正決定總時間的是沒有任何餘裕的 3 → 4 → 5，這就是 F2 要算的東西。

### 解法

```python
import random
from collections import deque


def minimum_time(n: int, relations: list[list[int]], time: list[int]) -> int:
    graph = [[] for _ in range(n)]
    indegree = [0] * n
    for prev, nxt in relations:                # 轉成 0-indexed
        graph[prev - 1].append(nxt - 1)
        indegree[nxt - 1] += 1
    start = [0] * n                            # 最早開始時間 = 前置完成時間的最大值
    queue = deque(v for v in range(n) if indegree[v] == 0)
    answer = 0
    while queue:
        u = queue.popleft()
        finish = start[u] + time[u]
        answer = max(answer, finish)
        for v in graph[u]:
            start[v] = max(start[v], finish)
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)
    return answer


def brute(n, relations, time):                 # 反覆鬆弛直到不再變動（DAG 上至多 n 輪）
    finish = time[:]
    for _ in range(n):
        for p, q in relations:
            finish[q - 1] = max(finish[q - 1], finish[p - 1] + time[q - 1])
    return max(finish)


def layered(n, relations, time):               # 錯誤的「按層」做法，用來對照
    graph, indeg = [[] for _ in range(n)], [0] * n
    for p, q in relations:
        graph[p - 1].append(q - 1)
        indeg[q - 1] += 1
    layer = [v for v in range(n) if indeg[v] == 0]
    total = 0
    while layer:
        total += max(time[v] for v in layer)
        nxt = []
        for u in layer:
            for v in graph[u]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    nxt.append(v)
        layer = nxt
    return total


assert minimum_time(3, [[1, 3], [2, 3]], [3, 2, 5]) == 8
assert minimum_time(5, [[1, 5], [2, 5], [3, 5], [3, 4], [4, 5]], [1, 2, 3, 4, 5]) == 12
assert minimum_time(1, [], [7]) == 7
assert minimum_time(3, [], [4, 9, 2]) == 9
rel = [[1, 5], [2, 5], [3, 5], [3, 4], [4, 5]]
assert minimum_time(5, rel, [10, 2, 3, 4, 5]) == 15 and layered(5, rel, [10, 2, 3, 4, 5]) == 19
for _ in range(500):
    n = random.randint(1, 8)
    perm = random.sample(range(1, n + 1), n)   # 只產生沿 perm 往後的邊，保證是 DAG
    pairs = {tuple(sorted(random.sample(range(n), 2))) for _ in range(random.randint(0, 10))} if n > 1 else set()
    rel = [[perm[i], perm[j]] for i, j in pairs]
    t = [random.randint(1, 9) for _ in range(n)]
    assert minimum_time(n, rel, t) == brute(n, rel, t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n + E)，E 是 `relations` 的長度：每門課取出一次，每條關係鬆弛一次。空間 O(n + E)。邊界情況：課程編號是 1-indexed 而 `time` 是 0-indexed，建圖時統一轉成 0-indexed 最不容易錯；沒有任何關係時答案是 `max(time)`；答案最大約 5 × 10⁴ × 10⁴ = 5 × 10⁸，Python 沒有溢位問題，Java 用 `int` 也還夠；題目保證無環，若不保證，要在最後檢查取出數是否等於 n（見 F4 最後的說明）並回報無解。

### Follow-up

> [!question]- F1. 如果要輸出關鍵路徑（決定總時間的那條課程鏈）呢？
> 鬆弛時記錄 `parent[v]` 為讓 `start[v]` 達到最大值的那個前置 u（只有在 `finish[u] > start[v]` 時才更新）。結束後從 `finish` 最大的課出發，沿 `parent` 往回走到沒有 parent 的課，再反轉。時間 O(n + E)。關鍵路徑可能不唯一（兩條鏈一樣長），這個做法回傳其中一條；若要所有關鍵課程，用 F2 的 slack。

> [!question]- F2. 如果要找出每門課最多能延後幾個月開始而不影響總時間（slack）呢？
> 做第二次反向的拓撲 DP。設總時間為 T，定義最晚完成時間 `LF[v]`：沒有後繼的課 `LF[v] = T`，否則 `LF[v] = min(LF[w] − time[w] for w in succ(v))`，按拓撲順序的反序計算。slack 就是 `LF[v] − finish[v]`，等於 0 的課就是關鍵課程，任何一門延後都會拖慢整體。時間 O(n + E)。這是專案管理中 CPM 的「前推」與「後推」兩趟計算，面試官若有工程管理背景，常會問到。

> [!question]- F3. 如果同一時間最多只能修 k 門課呢？
> 問題立刻變難：有先後限制的多機排程（P | prec | Cmax）是 NP-hard；就算每門課時間都是 1，只要 k 是輸入的一部分仍是 NP-hard。k = 2 且時間皆為 1 時有 Coffman–Graham 多項式演算法，固定 k ≥ 3 是否有多項式解至今仍是公開問題。實務上用 list scheduling（列表排程）：每當有空閒的名額，就從「前置都完成」的課中挑關鍵路徑最長的那門開始，Graham 證明任何列表排程都不超過最佳解的 2 − 1/k 倍。n 很小時可以用 bitmask DP 求精確解，即核心題 1 F3 的 1494 題。

> [!question]- F4. 如果可以把某一門課的時間縮短 1 個月，要選哪一門才能讓總時間變少？
> 只有位於**每一條**關鍵路徑上的課，縮短它才會讓總時間減少（變成 T − 1，因為時間都是整數，其他不經過它的路徑長度都 ≤ T − 1）。判斷方法是計數：只看「緊的邊」（`finish[u] == start[v]` 的邊），用 16.5 節的路徑數 DP 沿拓撲順序算出 `cnt_in[v]`，也就是從某個開始時間為 0 的課沿緊邊走到 v 的鏈數；再沿反序算出 `cnt_out[v]`，也就是從 v 沿緊邊走到某個 `finish == T` 的課的鏈數。關鍵路徑總數 total 是所有 `finish == T` 的課的 `cnt_in` 之和，而 v 在每條關鍵路徑上 ⇔ `cnt_in[v] × cnt_out[v] == total`。時間 O(n + E)；路徑數可能很大，Python 大整數可以直接算，其他語言可以對一個大質數取模（有極小的誤判機率）。另外，若題目不保證無環，記得照 16.3 節檢查 Kahn 取出的課程數是否為 n，否則回報無解。

### 心得

關鍵突破是「可以無限平行」讓每門課都在最早可能的時間開始，總時間就等於 DAG 上節點加權的最長路徑，沿拓撲順序一次鬆弛就算完。它是 16.5 節模板最直接的應用，也是難題 2（最長路徑以層數計）的加權版本。面試時最有說服力的講法是同時給出上界與下界：最早開始的排程是合法的（上界），任何先修鏈都必須依序修（下界），兩者相等。若面試官追問「每次只能修 k 門」，要能立刻指出問題變成 NP-hard，並給出列表排程或 bitmask DP 的方向，而不是試圖修補原本的貪婪。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 判斷有沒有環 | 「能不能全部完成」「依賴是否矛盾」 | Kahn 取出數 == n；或 DFS 三色遇到灰色 | 核心題 1（207）、2115 Find All Possible Recipes |
| 輸出一個順序 | 「回傳任一合法順序」 | Kahn 的取出順序；或反轉 DFS 後序 | 核心題 2（210）、難題 3（1203） |
| 字典序最小／判斷唯一 | 「多個答案時回傳最小」「順序是否唯一」 | queue 換成 min-heap；每步 queue 大小是否為 1 | 核心題 2 F1、F2，444 Sequence Reconstruction |
| 反向圖上的 Kahn | 「每條路都會停下來」「所有後繼都滿足」 | 反轉邊、用出度當計數器實作 AND 條件 | 核心題 3（802）、913 Cat and Mouse 的逆向分析 |
| 無向樹剝葉子 | 樹的中心、從外往內一層層處理 | 度數為 1 的是葉子，剝到剩 1 或 2 個節點 | 核心題 4（310）、2603 Collect Coins in a Tree |
| 遞移閉包 | 大量「u 能否到達 v」的查詢，n 不大 | 沿拓撲順序傳遞祖先 bitset；或 Floyd–Warshall | 核心題 5（1462）、851 Loud and Rich |
| 從資料萃取邊 | 已排序的序列、比較結果 | 只看相鄰元素的第一個差異；注意拓撲排序偵測不到的矛盾 | 難題 1（269）、953 Verifying an Alien Dictionary |
| 隱式 DAG | 「嚴格遞增」「時間往前」等天然無環的移動規則 | 入度自己算；按值排序本身就是拓撲順序 | 難題 2（329）、2328 Number of Increasing Paths |
| 多層拓撲排序 | 群組必須相鄰、又有項目依賴 | 每層各做一次 Kahn，用「拓撲順序限制到子集仍合法」組合 | 難題 3（1203） |
| 拓撲順序上的 DP | 最長路徑、最早完成時間、路徑數、每色計數 | 取出節點時它的值已是最終值，沿邊傳遞 max／加法 | 難題 4（1857）、難題 5（2050）、1136 Parallel Courses |

**下限與上限**。最簡單的形式是核心題 1、2：圖已經給好、方向寫清楚，只要寫對 Kahn 並檢查取出數，考的是模板熟練度與「邊的方向」這個細節。中間層是換一個角度使用同一個機制：802 把入度換成反向圖的出度，310 把入度換成無向樹的度數，1462 在 Kahn 的過程中順便傳遞集合。上限的題目難在三個地方，經常同時出現：第一，**圖要自己建**，例如 269 要從字典萃取邊、329 的邊由「相鄰且更大」動態決定、1203 要自己構造組圖；第二，**有拓撲排序偵測不到的矛盾或限制**，例如 269 的前綴矛盾、1203 的組內環與相鄰限制；第三，**拓撲排序只是骨架，真正的內容是 DP 的狀態設計**，例如 1857 的 26 欄狀態、2050 的最早開始時間與它的上下界論證。

**與其他 pattern 的關係**。Kahn 演算法就是第 15 章的 BFS 加上一個入度計數器：普通 BFS 在「第一次碰到」時放行（OR 條件），Kahn 在「所有前驅都完成」時放行（AND 條件），802 F2 正好展示了兩者的差別。DFS 三色法則是第 15 章 DFS 的有向版本，記憶化 DFS 與拓撲順序 DP 是同一件事的兩種寫法（329）。無向圖判環與連通性用 Union-Find（第 17 章）更自然，有向圖判環則必須用本章的方法，因為 Union-Find 不記錄方向。最短路徑（第 18 章）在 DAG 上不需要 Dijkstra，照拓撲順序鬆弛一次就是 O(V + E)，負權也成立；最長路徑在一般圖上是 NP-hard，在 DAG 上卻是線性的，這是本章最重要的「結構換效率」例子。Dynamic programming（第 21–24 章）的每一張狀態表，背後都隱含一個狀態依賴的 DAG，填表順序就是它的拓撲順序。

**容易混淆之處**。第一，Kahn 剩下的節點不等於環上的節點，被環擋住的節點也會剩下；要知道誰在環上需要 SCC（802 F1）。第二，「按層」處理不等於最佳排程：層適合計算「學期數」這種每層等長的問題，2050 這種各課時間不同的問題要用最早開始時間，不能用層的最大值相加。第三，拓撲順序通常不唯一，測試要用驗證器而不是比對答案；題目要求字典序最小時才需要 heap。第四，邊的方向在不同題目中定義相反（207 與 1462），建圖前一定先用範例確認。第五，有限制的排程（每學期最多 k 門、每次只能修 k 門）會讓問題從線性變成 NP-hard，面試時要能看出這條界線，而不是硬套 Kahn。

## 本章重點整理

- Topological sort 的本質是反覆拿走「已經沒有未完成前置」的節點；能全部拿完就是 DAG，拿不完就有環，兩者是充要條件。
- Kahn 模板：建鄰接串列與入度、所有入度為 0 的節點入隊、取出時把後繼入度減 1、歸零就入隊、最後檢查取出數是否等於 n，時間 O(V + E)。
- 入度的意義是「還有幾個前驅沒被取出」；它讓 Kahn 實作了 AND 條件，這是它和普通 BFS 唯一的差別。
- DFS 三色法：白色未拜訪、灰色在遞迴堆疊上、黑色已完成；遇到灰色才是環，反轉後序就是拓撲順序。有向圖不能只用兩色。
- Python 中長鏈會讓遞迴 DFS 超過深度上限；預設用 Kahn，或把 DFS 改成顯式堆疊。
- 建圖前先確認邊的方向（207 的 `[a, b]` 是 b → a，1462 是 a → b），並把所有節點（包括孤立節點、沒有邊的字母）放進 queue 的初始化。
- 拓撲順序通常不唯一：字典序最小用 min-heap，判斷唯一看每一步 queue 是否恰好一個節點，測試時用驗證器。
- 換一個計數器就能解不同的問題：反向圖的出度判斷安全節點（802），無向樹的度數剝葉子找中心（310）。
- 拓撲順序上的 DP：取出節點時它的值已經是最終值，可以沿邊傳遞 max（最長路徑、最早完成時間）、加法（路徑數）、聯集（可達集合）。
- 「嚴格遞增」「時間往前」這類規則會形成隱式 DAG；按值排序本身就是一個合法的拓撲順序（329）。
- 從資料萃取邊時，只有相鄰元素的第一個差異帶有資訊；拓撲排序偵測不到的矛盾（前綴、組內環）要另外檢查。
- 無限平行的排程 = DAG 上的節點加權最長路徑（critical path）；一旦限制同時進行的數量，問題就變成 NP-hard。
