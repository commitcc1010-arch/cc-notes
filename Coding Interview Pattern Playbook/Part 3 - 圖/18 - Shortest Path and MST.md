---
chapter: 18
title: Shortest Path 與 Minimum Spanning Tree
part: 3
---

# 第 18 章　Shortest Path 與 Minimum Spanning Tree

> [!abstract] 本章地圖
> **一句話**：邊有權重時，用 priority queue 每次「定案」目前成本最小的狀態（Dijkstra），或照邊數／時間的順序逐層鬆弛（Bellman-Ford、DAG DP）；要用最小總成本把所有點連起來，就每次加入跨越切割的最便宜邊（Kruskal、Prim）。
>
> **辨識訊號**：
> - 圖或格子的邊有不同的「代價」：時間、價格、高度差、機率、翻轉次數
> - 「最少花費／最短時間從 A 到 B」，而且 BFS 的「邊數最少」不等於「總代價最小」
> - 「路徑的成本是路上最大的那一步」「成功機率是各段相乘」這類非加總的路徑成本
> - 有額外限制：最多 k 次轉機、總時間不超過 T、要「第二短」的答案
> - 「用最小總成本把所有點連起來」「每對點都能互通，修路總價最小」
> - 「拿掉哪條邊會讓圖不連通」：bridge（橋）與連通性的上限題
>
> **核心題**：743、787、1631、1514、1584
>
> **難題**：882、1368、1928、2045、1192

## 18.1 這個 Pattern 解決什麼問題

先看一個小例子。城市 0 到城市 3 有兩條路線：0 → 1 → 3 走兩段公路，每段 10 分鐘；0 → 2 → 4 → 3 走三段市區道路，每段 2 分鐘。第 15 章的 BFS 會先找到 0 → 1 → 3，因為它的**邊數**比較少；可是它要 20 分鐘，另一條只要 6 分鐘。BFS 的保證是「第一次看到某個點時，走的邊數最少」，這個保證只在每條邊代價相同時才等於「總代價最小」。一旦邊有不同的權重，BFS 的層次就失去意義，必須換一種擴展順序。

暴力的修補是：不管第一次看到與否，只要找到更短的路就更新並重新擴展。這就是 Bellman-Ford 的精神：把所有邊重複鬆弛（relaxation，用「經過 u 再走 u→v」更新 v 的距離）V − 1 輪，O(V·E)。它總是正確，但對每個點都重複做了很多無用的更新。Dijkstra 的觀察是：如果所有邊權都非負，那麼**目前所有候選中距離最小的那個點，它的距離已經不可能再被改善**，因為任何其他路線都要先經過一個距離更大（或相等）的點，再加上非負的代價。於是每次從 priority queue（優先佇列，這裡用 heap）取出最小的點並「定案」，每個點只需要擴展一次，時間降到 O(E log V)。

這個「依成本由小到大定案」的想法比最短路徑本身更通用。只要路徑成本滿足「延伸路徑不會讓成本變好」，同一份程式就能處理路上最大高度差（核心題 3）、成功機率連乘（核心題 4）、只有 0 和 1 兩種代價的格子（難題 2，用 deque 取代 heap）。節點也不必是原圖的點：當題目有「最多 k 次轉機」「時間上限」這類額外限制時，把限制放進狀態 `(點, 已用資源)`，在擴大後的狀態圖上做同樣的事（核心題 2、難題 3）。

本章的另一半是 minimum spanning tree（MST，最小生成樹）：不是求兩點之間的最短路，而是挑一組邊把所有點連起來，總權重最小。它和最短路徑常被混淆，但目標完全不同：最短路徑樹讓「從起點到每個點」都最短，MST 讓「整棵樹的總和」最小。MST 的核心是 cut property（切割性質）：任何把點分成兩邊的切割，跨越它的最便宜邊一定可以放進某棵 MST。Kruskal 用排序加 union-find（第 17 章）實作它，Prim 則用和 Dijkstra 幾乎一樣的 heap 迴圈實作。最後，難題 5 的 bridge 問的是「哪些邊是所有生成樹都必須包含的」，它用 DFS 的 low-link 技巧，作為本章圖論的上限題。

## 18.2 辨識訊號

| 題目特徵 | 為什麼是這個 pattern | 本章哪一題 |
|---|---|---|
| 邊有非負權重，求單一起點到某點／所有點的最短距離 | 非負權重下，heap 中最小的距離不可能再被改善，可以直接定案 | 核心題 1（743） |
| 最短路徑但限制「最多 k 條邊」 | 加上邊數維度後，Dijkstra 的「便宜就好」不再成立；用 k + 1 輪 Bellman-Ford 或擴充狀態 | 核心題 2（787） |
| 路徑成本是「路上最大的一步」，要最小化它 | max 和加法一樣滿足「延伸不會變好」，Dijkstra 換一行；也可二分答案或 union-find | 核心題 3（1631） |
| 成功機率連乘，要最大化 | 機率 ≤ 1，乘上去只會變小，等價於最大化版本的 Dijkstra；取 −log 後就是最短路 | 核心題 4（1514） |
| 「把所有點連起來的最小成本」 | 正是 MST；完全圖用 O(V²) 的 Prim，稀疏圖用 Kruskal | 核心題 5（1584） |
| 邊被細分成很多小節點，問步數內能到幾個點 | 不必真的展開節點：在原圖做 Dijkstra，再用剩餘步數計算每條邊上能走到的部分 | 難題 1（882） |
| 格子中「照指示走不用錢，改方向要 1」 | 邊權只有 0 和 1，用 0-1 BFS（deque）取代 heap，O(V + E) | 難題 2（1368） |
| 同時有費用與時間兩種資源，時間有上限 | 狀態加上時間；時間嚴格遞增讓狀態圖是 DAG，可以 DP 或帶支配剪枝的 Dijkstra | 難題 3（1928） |
| 「第二短」的路徑或時間 | 每個點保留前兩個不同的距離；所有邊代價相同時 BFS 就夠 | 難題 4（2045） |
| 「拿掉哪條邊會讓網路斷開」 | bridge：DFS tree 上子樹繞不回祖先的那條 tree edge，Tarjan low-link | 難題 5（1192） |
| 邊權為 1 或圖沒有權重 | 不需要本章，第 15 章的 BFS 就是最佳 | 第 15 章 |

一個實用的反向檢查：先問「每條邊的代價一樣嗎？」一樣就用 BFS（第 15 章）；只有 0 和 1 就用 0-1 BFS；非負的一般權重用 Dijkstra；有負權重用 Bellman-Ford，或在 DAG 上照拓撲順序做 DP（第 16 章）。題目若問「連起所有點的最小成本」而不是「從某點出發」，就是 MST，不要寫成最短路徑。

## 18.3 模板與原理：Dijkstra

本章的主模板是 lazy deletion（延遲刪除）版本的 Dijkstra：heap 裡可以同時存在同一個點的多筆紀錄，彈出時若比目前已知的距離大，就當作過期紀錄丟掉。這樣不需要支援「降低某個 key」的 heap，Python 的 `heapq` 直接可用。

```python
import heapq
import random
from math import inf


def dijkstra(n: int, edges: list[tuple[int, int, int]], src: int) -> tuple[list[float], list[int]]:
    """有向圖、非負邊權。回傳 (dist, parent)；到不了的點 dist 為 inf。"""
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
    dist = [inf] * n
    parent = [-1] * n
    dist[src] = 0
    heap = [(0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:              # 過期的紀錄：u 已經用更短的距離處理過
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:         # relaxation（鬆弛）
                dist[v] = nd
                parent[v] = u
                heapq.heappush(heap, (nd, v))
    return dist, parent


def path_to(parent: list[int], t: int) -> list[int]:
    path = []
    while t != -1:
        path.append(t)
        t = parent[t]
    return path[::-1]


def bellman_ford(n, edges, src):
    dist = [inf] * n
    dist[src] = 0
    for _ in range(n - 1):
        for u, v, w in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
    return dist


edges = [(0, 1, 4), (0, 2, 1), (2, 1, 2), (1, 3, 1), (2, 3, 5)]
dist, parent = dijkstra(4, edges, 0)
assert dist == [0, 3, 1, 4]
assert path_to(parent, 3) == [0, 2, 1, 3]
assert dijkstra(3, [(0, 1, 0)], 0)[0] == [0, 0, inf]      # 0 權重邊、到不了的點
assert dijkstra(1, [], 0)[0] == [0]
for _ in range(300):
    n = random.randint(1, 7)
    es = [(random.randrange(n), random.randrange(n), random.randint(0, 9))
          for _ in range(random.randint(0, 15))]
    d, p = dijkstra(n, es, 0)
    assert d == bellman_ford(n, es, 0)
    for t in range(n):
        if d[t] < inf:                                       # 重建的路徑長度等於 dist
            pth = path_to(p, t)
            w = {}
            for u, v, c in es:
                w[(u, v)] = min(w.get((u, v), inf), c)
            assert pth[0] == 0 and sum(w[(a, b)] for a, b in zip(pth, pth[1:])) == d[t]
print("all tests passed")
```

**Invariant（不變式）**。把「已經以正確距離彈出過」的點稱為已定案集合 S。迴圈維持兩件事：S 中每個點的 `dist` 都是真正的最短距離；不在 S 中的點，`dist[v]` 是「只經過 S 中的點、最後一步進入 v」的最短路徑長度，而 heap 中一定有一筆 `(dist[v], v)`。每次彈出最小的 `(d, u)` 時，任何從起點到 u 的路徑，第一次離開 S 時會到達某個不在 S 的點 x，這一段的長度至少是 `dist[x] >= d`，之後剩下的邊權都非負，所以整條路徑至少是 d。因此 d 就是 u 的最短距離，可以把 u 加入 S，並用它鬆弛鄰居來維持第二條。

**非負權重為什麼是必要條件**。上面的論證最後一步用到「剩下的邊權非負」。若有負邊，例如 0 → 1 權重 2、0 → 2 權重 3、2 → 1 權重 −2，教科書版的 Dijkstra（用 visited 標記定案點、定案後不再處理）會先以距離 2 定案點 1，之後才發現 0 → 2 → 1 只要 1；點 1 已經定案，這個更短的距離不會再傳給它的鄰居。lazy deletion 版本因為允許重新推入，只要不提早結束、沒有負環，最後其實會得到正確距離，但「彈出即定案」已不成立，最差會退化成指數時間；本章常用的「第一次彈出終點就回傳」「數到第 n 個定案點」等提早結束寫法則會直接答錯，負環時更是無窮迴圈。面試時有負權重就直接說 Bellman-Ford（18.5 節）。

**每一行為什麼這樣寫**：

- `if d > dist[u]: continue`：同一個點可能被推入多次，只有距離等於目前最佳值的那一筆有效。不寫這行結果仍然正確，但每筆過期紀錄都會把 u 的鄰居重掃一次（雖然鬆弛都會失敗），最差可達 O(V · E)。這裡要用 `>` 而不是 `>=`：剛好相等的那筆就是有效紀錄。
- `if nd < dist[v]`：只有嚴格變短才推入，避免相同距離的紀錄堆滿 heap。若題目要「最短路徑有幾條」，才需要處理相等的情況（見核心題 1 F3）。
- heap 存 `(距離, 點)`：tuple 依第一個元素比較；距離相同時會比較點的編號，點若是不可比較的物件（例如自訂類別），要多放一個遞增的計數器當第二欄。
- `parent[v] = u`：每次成功鬆弛就覆寫，最後留下的是最短路徑樹上的父節點，從終點往回走就得到路徑。

**複雜度**。每條邊最多造成一次推入，heap 最多有 E 筆，每次操作 O(log E) = O(log V)（因為 E ≤ V²），總時間 O((V + E) log V)，空間 O(V + E)。當圖很稠密（E 接近 V²，例如核心題 5 的完全圖），用陣列取代 heap、每輪線性掃描找最小值的版本是 O(V²)，反而更快。

**提早結束**。如果只要一個終點 t 的距離，第一次彈出 t 時就可以回傳，因為它已經定案。若要「所有點都定案後的最大距離」（核心題 1），可以數彈出了幾個有效點，第 n 個就是答案。

## 18.4 換掉「路徑成本」與「狀態」：Dijkstra 的推廣

Dijkstra 的正確性只用到兩個性質。第一，**延伸不會變好**：路徑多走一條邊，成本不會比原本更優。第二，**前綴比較可以傳遞**：若路徑 P 比 Q 好，兩者都接上同一條邊 e 之後，P + e 仍然不比 Q + e 差。加法配非負權重滿足這兩點；把加法換成其他滿足這兩點的運算，模板只改一行。

| 路徑成本 | 合併運算 | 目標 | 延伸不會變好的理由 | 本章題目 |
|---|---|---|---|---|
| 總長度 | `d + w`，w ≥ 0 | 最小化 | 加上非負數不會變小 | 核心題 1（743）、難題 1（882） |
| 路上最大的一步（bottleneck） | `max(d, w)` | 最小化 | 取最大值不會變小 | 核心題 3（1631） |
| 成功機率 | `p * q`，0 ≤ q ≤ 1 | 最大化 | 乘上 ≤ 1 的數不會變大 | 核心題 4（1514） |
| 只有 0、1 的代價 | `d + w`，w ∈ {0, 1} | 最小化 | 同總長度，但可用 deque | 難題 2（1368） |
| 抵達時間（含等待） | `f(t)`，f 遞增且 f(t) ≥ t | 最小化 | 晚出發不會早到 | 難題 4（2045） |

```python
import heapq
import random
from collections import deque
from math import inf


def zero_one_bfs(n: int, adj: list[list[tuple[int, int]]], src: int) -> list[float]:
    """邊權只有 0 或 1。0 的鄰居放 deque 前端，1 的放後端。"""
    dist = [inf] * n
    dist[src] = 0
    dq = deque([src])
    while dq:
        u = dq.popleft()
        for v, w in adj[u]:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                if w == 0:
                    dq.appendleft(v)
                else:
                    dq.append(v)
    return dist


def minimax_path(n: int, adj: list[list[tuple[int, int]]], src: int) -> list[float]:
    """路徑成本 = 路上最大的邊權；求每個點的最小可能成本。"""
    best = [inf] * n
    best[src] = 0
    heap = [(0, src)]
    while heap:
        c, u = heapq.heappop(heap)
        if c > best[u]:
            continue
        for v, w in adj[u]:
            nc = max(c, w)              # 唯一和 Dijkstra 不同的一行
            if nc < best[v]:
                best[v] = nc
                heapq.heappush(heap, (nc, v))
    return best


def dijkstra_adj(n, adj, src):
    dist = [inf] * n
    dist[src] = 0
    heap = [(0, src)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(heap, (d + w, v))
    return dist


def minimax_brute(n, adj, src):
    # 對每個門檻 T，只用 <= T 的邊做可達性
    ws = sorted({0} | {w for u in range(n) for _, w in adj[u]})
    best = [inf] * n
    for T in ws:
        seen = {src}
        st = [src]
        while st:
            u = st.pop()
            for v, w in adj[u]:
                if w <= T and v not in seen:
                    seen.add(v)
                    st.append(v)
        for v in seen:
            best[v] = min(best[v], T)
    return best


adj = [[(1, 0), (2, 1)], [(3, 1)], [(3, 0)], []]
assert zero_one_bfs(4, adj, 0) == [0, 0, 1, 1]
adj2 = [[(1, 5), (2, 2)], [(3, 1)], [(3, 4)], []]
assert minimax_path(4, adj2, 0) == [0, 5, 2, 4]          # 0→2→3 的最大邊 4 < 0→1→3 的 5
assert zero_one_bfs(2, [[], []], 0) == [0, inf]
for _ in range(300):
    n = random.randint(1, 7)
    a01 = [[] for _ in range(n)]
    aw = [[] for _ in range(n)]
    for _ in range(random.randint(0, 14)):
        u, v = random.randrange(n), random.randrange(n)
        a01[u].append((v, random.randint(0, 1)))
        aw[u].append((v, random.randint(0, 9)))
    assert zero_one_bfs(n, a01, 0) == dijkstra_adj(n, a01, 0)
    assert minimax_path(n, aw, 0) == minimax_brute(n, aw, 0)
print("all tests passed")
```

**0-1 BFS 為什麼正確**。Dijkstra 需要 heap，是因為候選距離可能是任意值。邊權只有 0 和 1 時，deque 中的距離永遠只有兩種：前段是 d、後段是 d + 1。從距離 d 的點走代價 0 的邊得到 d，放到前端；走代價 1 的邊得到 d + 1，放到後端。deque 因此始終是排序的，`popleft` 取出的就是最小距離，效果等同 heap，但每次操作 O(1)，總時間 O(V + E)。同一個點可能被放入兩次（先以 d + 1 放到後端，後來又以 d 放到前端），所以和 lazy Dijkstra 一樣靠 `dist` 比較來忽略過期紀錄；上面的寫法在彈出時不檢查，但鬆弛條件 `dist[u] + w < dist[v]` 會讓過期的 u 擴展不出任何東西。

**狀態圖**。很多題目的「最佳」不只取決於位置。787 題限制轉機次數，到達同一個城市時「便宜但轉機多」和「貴但轉機少」都可能有用，只保留最便宜的會出錯；1928 題同時有費用與時間上限，也是一樣。解法是把狀態擴充成 `(點, 已用資源)`，在狀態圖上跑最短路徑。代價是狀態數乘上資源的範圍，所以要先估算：787 是 n × (k + 1)，1928 是 n × (maxTime + 1)。當資源（邊數、時間）每走一步嚴格增加時，狀態圖沒有環，按資源由小到大逐層 DP 就是 DAG 上的最短路徑，連 heap 都不需要。這和第 15 章 15.5 節「狀態圖：當節點不只是位置」的 BFS 是同一個想法，只是邊多了權重。

**支配（dominance）剪枝**。在狀態圖上跑 Dijkstra 時，若已經彈出過狀態 `(v, r)`，之後再彈出 `(v, r')` 且 r' ≥ r（資源用得更多），由於 heap 依成本排序，後者成本也不低，它在每個方面都不比前者好，可以直接丟掉。於是每個點只需記錄「目前彈出過的最少資源」，不需要開完整的 n × R 表。核心題 2 和難題 3 都附上這個寫法。

## 18.5 Bellman-Ford、Floyd-Warshall 與 DAG：何時不用 Dijkstra

```python
import random
from math import inf


def bellman_ford(n: int, edges: list[tuple[int, int, int]], src: int) -> list[float] | None:
    """可處理負邊；若從 src 可達負環則回傳 None。"""
    dist = [inf] * n
    dist[src] = 0
    for _ in range(n - 1):
        changed = False
        for u, v, w in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                changed = True
        if not changed:                  # 提早結束：這一輪沒有任何改善
            break
    for u, v, w in edges:                # 第 n 輪還能鬆弛 → 有負環
        if dist[u] + w < dist[v]:
            return None
    return dist


def floyd_warshall(n: int, edges: list[tuple[int, int, int]]) -> list[list[float]]:
    d = [[0 if i == j else inf for j in range(n)] for i in range(n)]
    for u, v, w in edges:
        d[u][v] = min(d[u][v], w)
    for k in range(n):                   # 只允許經過 0..k 當中繼點
        dk = d[k]
        for i in range(n):
            dik = d[i][k]
            if dik == inf:
                continue
            di = d[i]
            for j in range(n):
                if dik + dk[j] < di[j]:
                    di[j] = dik + dk[j]
    return d


edges = [(0, 1, 4), (0, 2, 5), (1, 2, -3), (2, 3, 2)]
assert bellman_ford(4, edges, 0) == [0, 4, 1, 3]          # 負邊讓 0→1→2 比 0→2 短
assert bellman_ford(3, [(0, 1, 1), (1, 2, -2), (2, 1, 1)], 0) is None   # 1→2→1 是負環
assert bellman_ford(2, [(1, 0, -5)], 0) == [0, inf]       # 負邊不可達，不影響
fw = floyd_warshall(4, edges)
assert fw[0] == [0, 4, 1, 3] and fw[3][0] == inf
for _ in range(200):
    n = random.randint(1, 6)
    es = [(random.randrange(n), random.randrange(n), random.randint(0, 9)) for _ in range(random.randint(0, 12))]
    fw = floyd_warshall(n, es)
    for s in range(n):
        assert fw[s] == bellman_ford(n, es, s)
print("all tests passed")
```

**Bellman-Ford 的 invariant**。第 i 輪結束後，`dist[v]` 不超過「最多用 i 條邊」的最短路徑長度。最短路徑若存在（沒有負環），一定是不重複點的簡單路徑，最多 V − 1 條邊，所以 V − 1 輪後全部正確。若第 V 輪還能鬆弛，代表有一條路徑越走越短，也就是可達的負環。注意上面的寫法在同一輪中會用到本輪剛更新的值，所以第 i 輪後可能已經包含超過 i 條邊的路徑；這不影響最終正確性，但如果題目**限制邊數**（核心題 2），每輪必須從上一輪的複本延伸，才能精確控制「最多 i 條邊」。

**Floyd-Warshall 的 invariant**。外層第 k 輪結束後，`d[i][j]` 是「中繼點只能用 0..k」的最短距離。加入中繼點 k 時，新路徑要嘛不經過 k（原值），要嘛是 i → k → j，兩段都只用 0..k−1 當中繼點，所以 `d[i][k] + d[k][j]` 就是唯一的新候選。k 必須放在最外層，這是最常見的寫錯方式。時間 O(V³)，V ≤ 400 左右可行；可處理負邊，若最後某個 `d[i][i] < 0` 則有負環。

**DAG 上的最短路徑**。沒有環時，照拓撲順序（第 16 章）把每個點的出邊鬆弛一次就完成，O(V + E)，負權重也沒問題，因為處理 v 時所有指向 v 的邊都已經處理過。把權重取負號就能求 DAG 上的最長路徑（例如第 16 章難題 5 的 2050 題）。一般圖上的最長簡單路徑是 NP-hard，不要在有環的圖上這樣做。

| 情況 | 演算法 | 時間 | 本章或他章 |
|---|---|---|---|
| 無權重或權重全相同 | BFS | O(V + E) | 第 15 章 |
| 權重只有 0、1 | 0-1 BFS | O(V + E) | 難題 2（1368） |
| 非負權重、單一起點 | Dijkstra（heap） | O(E log V) | 核心題 1、3、4，難題 1 |
| 非負權重、稠密圖 | Dijkstra（陣列） | O(V²) | 核心題 1 F4 |
| 有負權重、單一起點 | Bellman-Ford | O(V·E) | 核心題 1 F2 |
| 限制最多 k 條邊 | k + 1 輪 Bellman-Ford（每輪用複本） | O(k·E) | 核心題 2（787） |
| DAG（可有負權重） | 拓撲順序 + 鬆弛 | O(V + E) | 第 16 章、難題 3 的時間 DP |
| 所有點對、V 小 | Floyd-Warshall | O(V³) | 1334、399 |
| 所有點對、稀疏非負 | 每點一次 Dijkstra | O(V·E log V) | 核心題 1 F5 |

## 18.6 Minimum Spanning Tree：Kruskal 與 Prim

連通無向圖的 spanning tree（生成樹）是包含所有 V 個點、恰好 V − 1 條邊、沒有環的子圖；MST 是總權重最小的那一棵。兩個經典演算法都建立在同一個性質上。

**Cut property（切割性質）**。把點任意分成兩群 A 與 B，跨越兩群的邊中最便宜的那一條 e，一定屬於某一棵 MST。理由是交換論證：拿任意一棵 MST T，若 e 不在 T 中，把 e 加進去會形成一個環，這個環一定還有另一條跨越 A、B 的邊 e'（環要從 A 走到 B 再走回來）；把 e' 換成 e，得到的仍是生成樹，而且權重不增（w(e) ≤ w(e')），所以也是 MST。

**Cycle property（環性質）**。反過來，任一個環上嚴格最重的邊，一定不在任何 MST 中。Kruskal 跳過「兩端已經連通」的邊，就是在套用它：這條邊加入會形成環，而它是那個環上最後被考慮（最重）的邊。

```python
import heapq
import random
from itertools import combinations
from math import inf


class DSU:
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.size = [1] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]   # path halving
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        return True


def kruskal(n: int, edges: list[tuple[int, int, int]]) -> float:
    """無向圖。回傳 MST 總權重；不連通時回傳 inf。"""
    dsu, total, used = DSU(n), 0, 0
    for u, v, w in sorted(edges, key=lambda e: e[2]):
        if dsu.union(u, v):              # 連接兩個不同元件，才是安全的邊
            total += w
            used += 1
            if used == n - 1:
                break
    return total if used == n - 1 else inf


def prim(n: int, edges: list[tuple[int, int, int]]) -> float:
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        adj[u].append((v, w))
        adj[v].append((u, w))
    in_tree = [False] * n
    total, count = 0, 0
    heap = [(0, 0)]                      # (連到樹的邊權, 點)
    while heap and count < n:
        w, u = heapq.heappop(heap)
        if in_tree[u]:
            continue
        in_tree[u] = True
        total += w
        count += 1
        for v, wv in adj[u]:
            if not in_tree[v]:
                heapq.heappush(heap, (wv, v))
    return total if count == n else inf


def brute_mst(n, edges):
    best = inf
    for sub in combinations(edges, n - 1):
        d = DSU(n)
        if all(d.union(u, v) for u, v, _ in sub):
            best = min(best, sum(w for _, _, w in sub))
    return best


edges = [(0, 1, 1), (1, 2, 2), (0, 2, 3), (2, 3, 4), (1, 3, 5)]
assert kruskal(4, edges) == prim(4, edges) == 7          # 選 1、2、4
assert kruskal(3, [(0, 1, 1)]) == prim(3, [(0, 1, 1)]) == inf   # 不連通
assert kruskal(1, []) == prim(1, []) == 0
for _ in range(200):
    n = random.randint(1, 5)
    es = [(random.randrange(n), random.randrange(n), random.randint(0, 9)) for _ in range(random.randint(0, 8))]
    assert kruskal(n, es) == prim(n, es) == brute_mst(n, es)
print("all tests passed")
```

**Kruskal**：把邊依權重排序，由小到大考慮，兩端在不同元件就加入。每次加入的邊，是「它的一端所在元件」對其餘點這個切割的最便宜跨越邊（更便宜的邊都已考慮過，要嘛已加入、要嘛兩端同元件），由 cut property 知道它是安全的。時間 O(E log E)，瓶頸是排序，union-find 幾乎是常數。

**Prim**：從任一點開始長一棵樹，每次加入「一端在樹內、一端在樹外」的最便宜邊，切割就是「樹內 vs 樹外」，直接套用 cut property。程式和 Dijkstra 幾乎一樣，唯一差別是 heap 的 key：Dijkstra 存「起點到 v 的總距離 `d + w`」，Prim 存「v 連到樹的那一條邊 `w`」。heap 版 O(E log V)；完全圖（E = V²）時改用陣列版每輪掃描最小值，O(V²)，見核心題 5。

**和最短路徑樹的差別**。以點 0 為起點，邊 0–1 權重 3、0–2 權重 3、1–2 權重 1：最短路徑樹選 0–1、0–2（總和 6，每個點到 0 都最短），MST 選 1–2 加上任一條 3（總和 4，但 1、2 之中有一個點到 0 的樹上距離變成 3 + 1 = 4）。面試時若題目說「所有點都要能互通、總成本最小」，是 MST；說「從總部到每個點都要最快」，是最短路徑。

## 18.7 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 有權重的圖仍用 BFS 的「第一次看到就定案」 | 答案偏大：邊數最少的路徑不一定總權重最小 | 定案的時機是**從 heap 彈出**時，不是推入或第一次看到時 |
| 少了 `if d > dist[u]: continue` | 結果正確但很慢，大測資超時 | lazy deletion 一定要跳過過期紀錄 |
| 在有負權重的圖上用 Dijkstra | 某些點的距離偏大，或在負環上無窮迴圈 | 有負邊改用 Bellman-Ford；DAG 用拓撲順序 |
| 有邊數限制卻只用一維 `dist` 剪枝 | 787 題中「便宜但轉機多」的狀態擋掉了「貴但轉機少」的可行解 | 限制邊數時用每輪複本的 Bellman-Ford，或狀態加上邊數並用支配剪枝 |
| Bellman-Ford 限制邊數時就地更新 | 一輪內串起多條邊，k 的限制失效 | `prev = dist[:]`，只從上一輪的結果延伸 |
| 最大化問題直接用 `heapq` | 先彈出最小的機率，定案錯誤 | 存負值模擬 max-heap，或把機率取 −log 變成最小化 |
| 1-indexed 的點用 0-indexed 陣列 | 越界，或漏掉第 n 個點 | 開 `n + 1` 大小，答案計算時跳過索引 0 |
| Floyd-Warshall 把 k 放在內層 | 某些點對的距離沒被更新 | 中繼點 k 必須是最外層迴圈 |
| MST 用 Dijkstra 的 `d + w` 當 key | 得到最短路徑樹，總權重偏大 | Prim 的 key 是「連到樹的單一邊權」 |
| 完全圖先建出所有 V² 條邊再排序 | Kruskal 的 O(V² log V) 加上大量記憶體，偏慢 | 稠密圖用 O(V²) 陣列版 Prim，邊權在需要時才計算 |
| 找 bridge 時用「父節點」判斷不走回頭路 | 有平行邊時把非 bridge 誤判為 bridge | 記錄「進入的邊編號」，只跳過那一條邊 |
| 遞迴 DFS 處理 10⁵ 個點 | Python 遞迴深度超限 | 用顯式 stack 的迭代版本（難題 5） |

## 核心題 1｜743. Network Delay Time｜Medium

### 題目

網路中有 n 個節點，編號 1 到 n。給一個陣列 `times`，每個元素 `[u, v, w]` 代表一條**有向**邊：訊號從 u 傳到 v 需要 w 單位時間。現在從節點 k 發出一個訊號，訊號會沿著所有邊同時擴散。請回傳所有 n 個節點都收到訊號所需的最短時間；如果有節點永遠收不到，回傳 -1。限制：`1 <= k <= n <= 100`，`1 <= len(times) <= 6000`，`0 <= w <= 100`，同一對 (u, v) 最多出現一次。

- 範例 1：`times = [[2, 1, 1], [2, 3, 1], [3, 4, 1]]`、`n = 4`、`k = 2`，回傳 `2`。節點 1、3 在時間 1 收到，節點 4 在時間 2 收到。
- 範例 2：`times = [[1, 2, 5], [1, 3, 1], [3, 2, 1], [2, 4, 1]]`、`n = 4`、`k = 1`，回傳 `3`。直達 1 → 2 要 5，繞道 1 → 3 → 2 只要 2，所以節點 2 在時間 2 收到、節點 4 在時間 3 收到。
- 範例 3（邊界）：`times = [[1, 2, 1]]`、`n = 2`、`k = 2`，回傳 `-1`：邊是從 1 到 2，從 2 出發到不了 1。
- 範例 4（邊界）：`n = 1`、`k = 1`，沒有任何邊，回傳 `0`。

### 思路

每個節點收到訊號的時間，就是從 k 到它的最短路徑長度：訊號同時沿所有邊擴散，最早到達的那一條路線決定了時間。所有節點都收到的時間是這些最短距離的**最大值**；只要有一個是無限大就回傳 -1。所以題目其實是「單源最短路徑 + 取最大值」。

暴力解是 Bellman-Ford：把所有邊鬆弛 n − 1 輪，O(n · E) = 100 × 6000 = 6 × 10⁵，在這題的限制下其實可以通過，面試時也值得先提。但它的瓶頸很明顯：每輪都重新檢查所有邊，即使大多數點的距離早已不會再變。範例 2 正是 BFS 的反例：1 → 2 只有一條邊，卻比兩條邊的 1 → 3 → 2 慢，所以「先看到的就是最早」在有權重時不成立。

權重非負，所以可以用 18.3 節的 Dijkstra：heap 中最小的 `(d, u)` 被彈出時，d 一定是 u 的最終答案。題目要的是所有點都定案後的最大值，而 Dijkstra 恰好是**依距離由小到大**定案，所以第 n 個被定案的點，它的距離就是答案，不需要最後再掃一次 `max`。如果 heap 清空時定案的點不到 n 個，代表有點到不了，回傳 -1。

```text
範例 2：邊 1→2(5)、1→3(1)、3→2(1)、2→4(1)，k = 1
dist 初始：1:0  2:∞  3:∞  4:∞

步驟  彈出      狀態    鬆弛                              heap 之後
 1   (0, 1)   定案 1   2: ∞→5，3: ∞→1                    (1,3) (5,2)
 2   (1, 3)   定案 3   2: 5→2（1+1 更短）                 (2,2) (5,2)
 3   (2, 2)   定案 2   4: ∞→3                            (3,4) (5,2)
 4   (3, 4)   定案 4   第 4 個定案 → 回傳 3                (5,2) 還在 heap 中

heap 裡的 (5, 2) 是過期紀錄：點 2 在步驟 3 已經以距離 2 定案，
若繼續執行，彈出 (5, 2) 時 5 > dist[2] = 2，會被 continue 跳過。
```

步驟 1 時，點 2 的暫定距離是 5（直達），但它還沒被彈出，所以不是最終答案；步驟 2 定案點 3 後，經過點 3 的路線把點 2 改善成 2。這正是 Dijkstra 與 BFS 的差別：BFS 在「推入」時就定案，Dijkstra 在「彈出」時才定案。步驟 4 彈出第 4 個有效點，它的距離 3 就是全部收到的時間。

### 解法

```python
import heapq
import random
from math import inf


def network_delay_time(times: list[list[int]], n: int, k: int) -> int:
    adj = [[] for _ in range(n + 1)]
    for u, v, w in times:
        adj[u].append((v, w))
    dist = [inf] * (n + 1)
    dist[k] = 0
    heap = [(0, k)]
    done = 0
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        done += 1
        if done == n:                    # 第 n 個定案的點就是最晚收到的
            return d
        for v, w in adj[u]:
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(heap, (d + w, v))
    return -1


def brute(times, n, k):
    dist = [inf] * (n + 1)
    dist[k] = 0
    for _ in range(n - 1):
        for u, v, w in times:
            dist[v] = min(dist[v], dist[u] + w)
    ans = max(dist[1:])
    return -1 if ans == inf else ans


assert network_delay_time([[2, 1, 1], [2, 3, 1], [3, 4, 1]], 4, 2) == 2
assert network_delay_time([[1, 2, 5], [1, 3, 1], [3, 2, 1], [2, 4, 1]], 4, 1) == 3
assert network_delay_time([[1, 2, 1]], 2, 1) == 1
assert network_delay_time([[1, 2, 1]], 2, 2) == -1
assert network_delay_time([], 1, 1) == 0
for _ in range(400):
    n = random.randint(1, 7)
    ts = [[random.randint(1, n), random.randint(1, n), random.randint(0, 9)] for _ in range(random.randint(0, 16))]
    k = random.randint(1, n)
    assert network_delay_time(ts, n, k) == brute(ts, n, k)
print("all tests passed")
```

### 複雜度與邊界

時間 O(E log E)：每條邊最多推入一次，每次 heap 操作 O(log E)；E ≤ 6000，非常快。空間 O(n + E)，鄰接串列加上 heap。邊界情況：節點是 1-indexed，陣列開 `n + 1`，索引 0 永遠是 inf，但它不會被彈出、也不計入 `done`，所以不影響答案；n = 1 時起點一彈出 `done == 1 == n`，回傳 0；權重可以是 0，Dijkstra 仍然正確（非負即可），兩個點可能同時定案；到不了的點讓 `done` 永遠少於 n，迴圈結束回傳 -1。若用 brute 的 `max(dist[1:])` 寫法，記得不要把索引 0 算進去。

### Follow-up

> [!question]- F1. 如果要回傳最後收到訊號的節點，以及訊號傳到它的路徑呢？
> 在鬆弛成功時記錄 `parent[v] = u`。第 n 個被定案的點就是最後收到的節點（有多個同時收到時任選一個，或依題目規則選編號最小的：把 heap 的 tuple 寫成 `(d, u)` 時，同距離會先彈出編號小的，最後彈出的則是編號最大的）。從它沿 `parent` 往回走到 k，再反轉，就是路徑，O(n)。整體複雜度不變。`parent` 在每次 `dist[v]` 變小時都要覆寫，最後留下的才是最短路徑樹上的父節點。

> [!question]- F2. 如果邊的傳輸時間可以是負數（但保證沒有負環）呢？
> Dijkstra 的「彈出即定案」依賴非負權重，負邊會讓已定案的點被之後的路線改善。改用 Bellman-Ford：鬆弛所有邊 n − 1 輪，O(n · E) = 6 × 10⁵；加上「某一輪沒有任何更新就提前結束」的優化。若還要偵測負環，再跑第 n 輪，仍能鬆弛就代表有可達的負環，此時「最短時間」沒有定義。另一個選擇是 SPFA（用 queue 只重新處理距離剛被改善的點），平均較快，但最差仍是 O(n · E)，面試中說 Bellman-Ford 即可。

> [!question]- F3. 如果要知道每個節點有幾條「最短時間」的路線呢（1976. Number of Ways to Arrive at Destination）？
> 在 Dijkstra 中多維護 `ways[v]`。鬆弛時若 `d + w < dist[v]`，更新距離並令 `ways[v] = ways[u]`；若 `d + w == dist[v]`，則 `ways[v] += ways[u]`（不必重新推入，因為距離沒變）。這要求 u 在彈出時 `ways[u]` 已經是最終值，這成立的前提是**邊權為正**：所有能以最短距離到達 u 的前驅都比 u 更早定案。若有權重 0 的邊，兩個同距離的點互相影響，必須先把同距離的點依 0 邊做拓撲排序，否則會漏算。時間 O(E log V)。

> [!question]- F4. 如果 n = 10⁴ 而且幾乎每對點之間都有邊（E 接近 n²）呢？
> heap 版要 O(E log V) ≈ 10⁸ × 14，太慢。改用陣列版 Dijkstra：維護 `dist` 和 `done` 陣列，每一輪線性掃描找出未定案中距離最小的點，定案後掃它的所有鄰居鬆弛，共 n 輪，每輪 O(n)，總時間 O(n²) = 10⁸ 次簡單操作。它不需要 heap，也沒有過期紀錄。一般規則是 E 接近 V² 時用陣列版，E 接近 V 時用 heap 版，核心題 5 的 Prim 是同樣的取捨。

> [!question]- F5. 如果要回答很多組「從 a 到 b 的最短時間」查詢呢？
> 先看 n 的大小。n ≤ 100（本題限制）時，用 18.5 節的 Floyd-Warshall 預先算出所有點對距離，O(n³) = 10⁶，之後每個查詢 O(1)。n 較大但查詢的起點只有少數幾個時，對每個不同的起點跑一次 Dijkstra 並快取結果，O(S · E log V)，S 是不同起點的數量。若查詢都是「到同一個終點 t」，把所有邊反向，從 t 跑一次 Dijkstra 就同時得到所有起點的答案，O(E log V)。

## 核心題 2｜787. Cheapest Flights Within K Stops｜Medium

### 題目

有 n 個城市，編號 0 到 n − 1。`flights[i] = [from, to, price]` 代表一班從 from 飛到 to 的**單向**航班，票價 price。給起點 `src`、終點 `dst` 與整數 k，請回傳從 src 到 dst、**中途最多停靠 k 個城市**（也就是最多搭 k + 1 班飛機）的最低總票價；做不到就回傳 -1。限制：`1 <= n <= 100`，`0 <= len(flights) <= n(n − 1)/2`，`1 <= price <= 10⁴`，沒有重複航班也沒有自環，`0 <= k < n`，`src != dst`。

- 範例 1：`n = 4`，`flights = [[0, 1, 100], [1, 2, 100], [2, 0, 100], [1, 3, 600], [2, 3, 200]]`，`src = 0`、`dst = 3`、`k = 1`，回傳 `700`。0 → 1 → 2 → 3 只要 400，但停了 1、2 兩站，超過 k = 1；合法的最便宜是 0 → 1 → 3。
- 範例 2：同上但 `k = 2`，回傳 `400`。
- 範例 3：`n = 3`，`flights = [[0, 1, 100], [1, 2, 100], [0, 2, 500]]`，`src = 0`、`dst = 2`、`k = 0`，回傳 `500`，只能直飛；`k = 1` 時回傳 `200`。
- 範例 4（邊界）：`flights = [[0, 1, 5]]`、`src = 0`、`dst = 2`，任何 k 都回傳 `-1`。

### 思路

暴力解是 DFS 列舉所有最多 k + 1 條邊的路徑，取最便宜的；每個點有最多 n − 1 個出邊，最差 O(n^(k+1))，指數級。直覺的改進是直接用 Dijkstra 求最便宜路徑，再檢查停靠數，但這行不通：Dijkstra 對每個點只保留最便宜的那一條路線，而**最便宜的路線可能停太多站**，被它擋掉的「較貴但停得少」的路線才是合法答案。範例 1 中，點 2 最便宜的抵達方式是 0 → 1 → 2（200，用了 2 班），從這裡再飛到 3 就是 3 班，超過限制；如果圖中還有一班 0 → 2 直飛（例如 500），它雖然到點 2 比較貴，卻能再接 2 → 3 成為合法路線，而一維 `dist` 會因為 500 > 200 把它丟掉。

關鍵觀察是：限制的是**邊數**，所以應該依邊數分層。定義 `dist_i[v]` = 最多搭 i 班飛機到達 v 的最低票價，那麼 `dist_{i+1}[v] = min(dist_i[v], min over (u→v) dist_i[u] + price)`。這正是 Bellman-Ford 的一輪鬆弛，只是要求每一輪**只能從上一輪的結果延伸**。做 k + 1 輪，`dist_{k+1}[dst]` 就是答案。實作時每輪先複製 `prev = dist[:]`，用 `prev[u]` 鬆弛、寫進 `dist[v]`。

為什麼一定要複製？Bellman-Ford 的標準寫法在同一輪中會用到本輪剛更新的值，這對「無限制最短路」沒有壞處（只是收斂得更快），但會讓一輪之內串起好幾條邊。下面的視覺化對照了兩種寫法：就地更新時，第一輪就已經算出 0 → 1 → 2 → 3 的 400，k 的限制形同虛設。

另一種同樣正確的做法是在狀態圖上跑 Dijkstra：狀態是 `(城市, 已搭幾班)`，依票價彈出，第一次彈出 dst 就是答案。為了避免狀態爆炸，用 18.4 節的支配剪枝：若某城市已經以「更少或相同的班數」被彈出過，之後彈出的（票價一定不更低）就可以丟掉。

```text
範例 1，k = 1（做 k + 1 = 2 輪），航班順序：0→1, 1→2, 2→0, 1→3, 2→3
城市：          0     1     2     3

正確：每輪從上一輪的複本 prev 延伸
初始            0     ∞     ∞     ∞
第 1 輪 prev =  [0 ∞ ∞ ∞]
  0→1: 0+100           100
  其他邊的起點在 prev 中都是 ∞
結果            0    100    ∞     ∞      ← 最多 1 班
第 2 輪 prev =  [0 100 ∞ ∞]
  1→2: 100+100               200
  1→3: 100+600                     700
  2→3: prev[2] = ∞，不能用本輪剛算出的 200
結果            0    100   200   700     ← 最多 2 班，答案 700

錯誤：就地更新（同一輪就能串起多條邊）
第 1 輪：0→1 得 100；1→2 立刻用 100 得 200；1→3 得 700；2→3 用 200 得 400
結果            0    100   200   400     ← 第 1 輪就出現 3 班的路線，答案錯成 400
```

第 2 輪的關鍵在最後一行：雖然本輪已經算出點 2 可以用 2 班、200 元到達，但 2 → 3 只能用 `prev[2]`，也就是「最多 1 班到達點 2」的價格，而那是 ∞。這保證了第 i 輪的結果只包含最多 i 條邊的路線。

### 解法

```python
import heapq
import random
from math import inf


def find_cheapest_price(n: int, flights: list[list[int]], src: int, dst: int, k: int) -> int:
    dist = [inf] * n
    dist[src] = 0
    for _ in range(k + 1):               # 第 i 輪後：最多用 i 條邊的最便宜價格
        prev = dist[:]                   # 只能從上一輪的結果延伸
        for u, v, w in flights:
            if prev[u] + w < dist[v]:
                dist[v] = prev[u] + w
    return -1 if dist[dst] == inf else dist[dst]


def find_cheapest_price_dijkstra(n, flights, src, dst, k):
    adj = [[] for _ in range(n)]
    for u, v, w in flights:
        adj[u].append((v, w))
    best_edges = [inf] * n               # 已彈出的狀態中，抵達每個點的最少班數
    heap = [(0, src, 0)]                 # (票價, 城市, 已搭班數)
    while heap:
        cost, u, e = heapq.heappop(heap)
        if u == dst:
            return cost
        if e >= best_edges[u] or e == k + 1:
            continue                     # 被支配：更便宜且班數更少的狀態已經出現過
        best_edges[u] = e
        for v, w in adj[u]:
            heapq.heappush(heap, (cost + w, v, e + 1))
    return -1


def brute(n, flights, src, dst, k):
    best = inf

    def dfs(u, cost, e):
        nonlocal best
        if u == dst:
            best = min(best, cost)
            return
        if e == k + 1:
            return
        for a, b, w in flights:
            if a == u:
                dfs(b, cost + w, e + 1)

    dfs(src, 0, 0)
    return -1 if best == inf else best


fl = [[0, 1, 100], [1, 2, 100], [2, 0, 100], [1, 3, 600], [2, 3, 200]]
assert find_cheapest_price(4, fl, 0, 3, 1) == 700
assert find_cheapest_price(4, fl, 0, 3, 2) == 400
fl2 = [[0, 1, 100], [1, 2, 100], [0, 2, 500]]
assert find_cheapest_price(3, fl2, 0, 2, 0) == 500
assert find_cheapest_price(3, fl2, 0, 2, 1) == 200
assert find_cheapest_price(3, [[0, 1, 5]], 0, 2, 2) == -1
fl3 = [[0, 1, 100], [1, 2, 100], [0, 2, 500], [2, 3, 100]]   # 一維 dist 的 Dijkstra 會答 -1
assert find_cheapest_price(4, fl3, 0, 3, 1) == find_cheapest_price_dijkstra(4, fl3, 0, 3, 1) == 600
for _ in range(400):
    n = random.randint(2, 6)
    seen, fls = set(), []
    for _ in range(random.randint(0, 12)):
        u, v = random.sample(range(n), 2)
        if (u, v) not in seen:
            seen.add((u, v))
            fls.append([u, v, random.randint(1, 20)])
    s, d = random.sample(range(n), 2)
    kk = random.randint(0, n - 1)
    exp = brute(n, fls, s, d, kk)
    assert find_cheapest_price(n, fls, s, d, kk) == exp == find_cheapest_price_dijkstra(n, fls, s, d, kk)
print("all tests passed")
```

### 複雜度與邊界

Bellman-Ford 版本時間 O(k · E)，每輪複製陣列 O(n)，總共 O(k · (n + E))，最多約 100 × 5000 = 5 × 10⁵；空間 O(n)。Dijkstra 版本中每個城市被接受的次數不超過 k + 1 次（每次班數嚴格減少），所以最多推入 O(k · E) 筆，時間 O(k · E log(k · E))，實務上常常更快，因為一找到 dst 就停。邊界情況：k = 0 只能直飛，迴圈只跑一輪；k 至多 n − 1，此時限制等於沒有（簡單路徑最多 n − 1 條邊），結果與無限制最短路相同；dst 到不了時回傳 -1；票價都是正的，所以 Dijkstra 版的支配剪枝成立（票價相同時 heap 依班數排序，也不會出錯）。

### Follow-up

> [!question]- F1. 為什麼不能直接用一維 dist 的 Dijkstra，再在推入時檢查「班數 ≤ k + 1」？
> 因為一維 `dist[v]` 只保留最便宜的抵達方式，而那條路線可能已經用掉太多班數。測試中的 `fl3` 就是反例：點 2 最便宜是 0 → 1 → 2（200，2 班），直飛 0 → 2 要 500（1 班）；k = 1 時只有 0 → 2 → 3 合法，但一維 Dijkstra 會因為 500 > 200 而拒絕直飛的狀態，最後回傳 -1。修正方法就是本題的兩種解：讓狀態帶著班數（並用「班數更少才保留」的支配規則），或按班數分層做 Bellman-Ford。

> [!question]- F2. 如果要回傳實際的路線呢？
> Bellman-Ford 版本要保留每一輪的父節點：`parent[i][v]` = 在第 i 輪讓 `dist[v]` 變小的那個 u（若本輪沒有改善，就沿用 `parent[i-1][v]` 並標記來自上一輪）。最後從 `(k + 1, dst)` 開始，依「這一層的值是本輪更新的就退回第 i − 1 層的 u，否則停在同一個點退一層」往回走。空間 O(k · n)。Dijkstra 版本比較簡單：在 heap 的 tuple 裡多放一個指向父狀態的編號，彈出 dst 時沿父狀態往回走即可，空間 O(k · E)。

> [!question]- F3. 如果規定必須「恰好」轉 k 次呢？
> 把每輪的更新改成完全不保留上一輪的值：`cur = [inf] * n`，對每條邊 `cur[v] = min(cur[v], prev[u] + w)`，做 k + 1 輪後 `cur[dst]` 就是恰好搭 k + 1 班的最低價。因為可以重複經過城市（題目的圖可以有環），恰好 k + 1 班的路線可能繞回頭；若要求不重複城市，那就是限制長度的簡單路徑，一般情況是 NP-hard，只能回溯搜尋。時間仍是 O(k · E)。

> [!question]- F4. 如果反過來：給一個預算 B，問最少要轉機幾次才能在預算內到達？
> 依班數由少到多做 Bellman-Ford，每輪結束檢查 `dist[dst] <= B`，第一次成立時的輪數減一就是答案；做滿 n − 1 輪仍不成立就回傳 -1。因為第 i 輪的 `dist[dst]` 對 i 單調不增，也可以對 k 做 binary search（第 8 章），但每次檢查都要重跑 O(k · E)，總時間 O(E · n log n)，反而比直接逐輪檢查的 O(n · E) 慢，面試時說逐輪即可。

> [!question]- F5. 如果 n = 10⁴、k ≤ 10 而航班有 10⁵ 班呢？
> Bellman-Ford 版仍是 O(k · E) = 10⁶，每輪複製 O(n) = 10⁴，總共很快，這正是它的優勢：複雜度與 k 成正比、與路徑上的價格無關。Dijkstra 狀態版在最壞情況是 O(k · E log(k · E))，也可行。若 k 很大（接近 n），限制等於沒有，直接跑普通 Dijkstra，O(E log n)。面試時先問 k 的範圍，再決定寫哪一種，這是「從限制推 pattern」（第 3 章）的典型應用。

## 核心題 3｜1631. Path With Minimum Effort｜Medium

### 題目

給一個 rows × cols 的整數矩陣 `heights`，代表地圖上每一格的高度。你從左上角 `(0, 0)` 出發，要走到右下角 `(rows − 1, cols − 1)`，每一步可以往上、下、左、右移動一格。一條路線的「體力消耗」定義為路線上**相鄰兩格高度差絕對值的最大值**。請回傳所有路線中最小的體力消耗。限制：`1 <= rows, cols <= 100`，`1 <= heights[i][j] <= 10⁶`。

- 範例 1：`heights = [[1, 2, 2], [3, 8, 2], [5, 3, 5]]`，回傳 `2`。路線 1 → 3 → 5 → 3 → 5 的高度差是 2、2、2、2，最大值 2；走 1 → 2 → 2 → 2 → 5 的話，最後一步差 3。
- 範例 2：`heights = [[1, 2, 3], [3, 8, 4], [5, 3, 5]]`，回傳 `1`，路線 1 → 2 → 3 → 4 → 5 每步差 1。
- 範例 3：一個 5 × 5 的矩陣，存在一條全由高度 1 組成、從左上連到右下的路線，回傳 `0`。
- 範例 4（邊界）：`heights = [[7]]`，起點就是終點，回傳 `0`；`heights = [[1, 10]]`，只有一條路，回傳 `9`。

### 思路

暴力解是 DFS 列舉所有簡單路徑，取「最大步差」最小的；路徑數是指數級。這題的特殊之處在於路徑成本不是加總，而是**取最大值**（bottleneck，瓶頸），所以直覺上「最短路徑」的演算法好像用不上。

第一個可行的想法是二分答案（第 8 章）：給一個上限 X，只允許走高度差 ≤ X 的步，問能否從起點走到終點，這是一次 BFS／DFS，O(rows · cols)。X 越大可走的邊越多，可行性單調，所以第一個可行的 X 就是答案，總時間 O(rows · cols · log 10⁶)。這是一個完全正確、面試時很好的答案。

第二個想法更直接：18.4 節說過，Dijkstra 只需要「延伸不會變好」與「前綴比較可傳遞」。把路徑成本定義成 `max(目前成本, 這一步的高度差)`，延伸時取 max 只會變大或不變；若到某格的兩條路線成本 a ≤ b，接上同一步後 `max(a, w) ≤ max(b, w)`。兩個條件都成立，所以把 Dijkstra 的 `d + w` 換成 `max(d, w)`，其他一行不改。終點第一次被彈出時，它的成本就是答案。

下面的視覺化展示了 Dijkstra 的一個重點：終點 (2, 2) 先被推入成本 3（經過右邊那條路），後來又被改善成 2（經過左邊那條路）。如果在推入時就定案（像 BFS 那樣），答案會錯成 3。

```text
heights:            effort（最終值）:
  1  2  2             0  1  1
  3  8  2             2  5  1
  5  3  5             2  2  2

步驟  彈出 (成本, 格)    推入／改善
 1   (0, (0,0))       (1,0)=|3-1|=2   (0,1)=|2-1|=1
 2   (1, (0,1))       (1,1)=max(1,6)=6   (0,2)=max(1,0)=1
 3   (1, (0,2))       (1,2)=max(1,0)=1
 4   (1, (1,2))       (2,2)=max(1,3)=3      ← 終點第一次被看到，成本 3
 5   (2, (1,0))       (2,0)=max(2,2)=2   (1,1)=max(2,5)=5（改善 6）
 6   (2, (2,0))       (2,1)=max(2,2)=2
 7   (2, (2,1))       (2,2)=max(2,2)=2      ← 改善 3 → 2
 8   (2, (2,2))       終點被彈出 → 回傳 2
```

步驟 4 時，右邊那條路 1 → 2 → 2 → 2 已經走到終點旁，最後一步高度差 3，所以終點暫定 3。但 heap 裡還有成本 2 的格子沒處理，它們可能找到更好的路，所以終點還不能定案。步驟 5–7 沿左邊那條路，每一步的差都是 2，於是終點被改善成 2，並在步驟 8 被彈出定案。

第三種做法是 union-find（第 17 章）：把所有相鄰格子的邊依高度差排序，由小到大合併，起點和終點第一次連通時，當下那條邊的權重就是答案。這其實是 Kruskal（18.6 節）：MST 上兩點之間的路徑，正是 minimax 路徑。三種方法的關係在 F1 說明。

### 解法

```python
import heapq
import random
from math import inf


def minimum_effort_path(heights: list[list[int]]) -> int:
    rows, cols = len(heights), len(heights[0])
    effort = [[inf] * cols for _ in range(rows)]
    effort[0][0] = 0
    heap = [(0, 0, 0)]
    while heap:
        e, r, c = heapq.heappop(heap)
        if (r, c) == (rows - 1, cols - 1):
            return e                      # 終點第一次被彈出時就是答案
        if e > effort[r][c]:
            continue
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < rows and 0 <= nc < cols:
                ne = max(e, abs(heights[nr][nc] - heights[r][c]))
                if ne < effort[nr][nc]:
                    effort[nr][nc] = ne
                    heapq.heappush(heap, (ne, nr, nc))
    return 0                              # 不會走到這裡：格子一定連通


def minimum_effort_binary_search(heights):
    rows, cols = len(heights), len(heights[0])

    def reachable(limit):
        seen = {(0, 0)}
        stack = [(0, 0)]
        while stack:
            r, c = stack.pop()
            if (r, c) == (rows - 1, cols - 1):
                return True
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if (0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in seen
                        and abs(heights[nr][nc] - heights[r][c]) <= limit):
                    seen.add((nr, nc))
                    stack.append((nr, nc))
        return False

    lo, hi = 0, max(map(max, heights)) - min(map(min, heights))
    while lo < hi:
        mid = (lo + hi) // 2
        if reachable(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


assert minimum_effort_path([[1, 2, 2], [3, 8, 2], [5, 3, 5]]) == 2
assert minimum_effort_path([[1, 2, 3], [3, 8, 4], [5, 3, 5]]) == 1
assert minimum_effort_path([[1, 2, 1, 1, 1], [1, 2, 1, 2, 1], [1, 2, 1, 2, 1],
                            [1, 2, 1, 2, 1], [1, 1, 1, 2, 1]]) == 0
assert minimum_effort_path([[7]]) == 0
assert minimum_effort_path([[1, 10]]) == 9
for _ in range(300):
    r, c = random.randint(1, 5), random.randint(1, 5)
    g = [[random.randint(1, 20) for _ in range(c)] for _ in range(r)]
    assert minimum_effort_path(g) == minimum_effort_binary_search(g)
print("all tests passed")
```

### 複雜度與邊界

Dijkstra 版時間 O(V log V)，V = rows · cols ≤ 10⁴，每格最多 4 條邊，E = O(V)；空間 O(V)。二分版時間 O(V · log H)，H 是高度範圍（≤ 10⁶，約 20 輪），空間 O(V)。union-find 版排序 O(V log V)。邊界情況：1 × 1 的格子起點就是終點，第一次彈出就回傳 0；只有一列或一行時路線唯一，答案是相鄰差的最大值；二分的上界取「最大高度 − 最小高度」一定可行（所有步都允許）；全部高度相同時答案 0。注意終點判斷要放在 `continue` 之前或之後都可以，因為終點第一次被彈出時一定是有效紀錄。

### Follow-up

> [!question]- F1. Dijkstra、二分答案、union-find 三種方法該怎麼選？
> 三者都正確。Dijkstra 是 O(V log V)，程式只比標準模板改一行，最通用；二分答案是 O(V log H)，每次檢查是最簡單的 BFS，H 很小時更快，而且思路最容易對面試官解釋；union-find 是 O(V log V) 排序加近乎線性的合併，當同一張圖要回答很多組「起點 a 到終點 b」的 minimax 查詢時最強：建出 MST 後，任兩點的答案就是 MST 路徑上的最大邊，可以離線依權重排序查詢一起處理（第 17 章難題 5 的 1697 題）。面試時建議寫 Dijkstra，並口頭提另外兩種。

> [!question]- F2. 如果改成「最大化路線上的最小值」呢（1102. Path With Maximum Minimum Value）？
> 對稱地，成本是 `min(目前值, 這格的值)`，要最大化。延伸只會讓 min 變小或不變，所以用 max-heap（存負值）的 Dijkstra：從起點以 `grid[0][0]` 出發，每次彈出目前最大值的格子，鄰居的值是 `min(cur, grid[nr][nc])`，終點第一次被彈出就是答案，O(V log V)。也可以把格子依值由大到小加入 union-find，起點與終點連通時剛加入的格子值就是答案。

> [!question]- F3. 如果允許走八個方向，或可以花一次「免費跳過」讓某一步的高度差不計呢？
> 八個方向只是鄰居多了 4 個，演算法不變，E 變成 8V。「免費一次」要擴充狀態：`(r, c, used)`，used ∈ {0, 1}；used = 0 時可以選擇正常走（成本取 max）或使用免費（成本不變、used 變 1）。狀態數 2V，仍是 Dijkstra，O(V log V)。這和核心題 2 的「把限制放進狀態」是同一個技巧；若免費次數是 k，狀態數變成 (k + 1) · V。

> [!question]- F4. 這題和 778. Swim in Rising Water 有什麼關係？
> 778 的成本是「路線上經過的最高格子高度」，要最小化，也是 bottleneck 路徑，只是成本在節點上而不是邊上：把進入格子 (r, c) 的代價定義成 `grid[r][c]`，起點成本是 `grid[0][0]`，合併運算仍是 max。所以同一份 Dijkstra 改一行就解決，O(V log V)；第 17 章難題 2 用的是 union-find 版本，依高度由小到大把格子加入，直到起點與終點連通。兩題放在一起講，最能說明「bottleneck 路徑 = Dijkstra 換 max = Kruskal」。

## 核心題 4｜1514. Path with Maximum Probability｜Medium

### 題目

給一張 n 個節點（編號 0 到 n − 1）的**無向**圖，`edges[i] = [a, b]` 代表一條邊，`succProb[i]` 是走過這條邊的成功機率。一條路線的成功機率是路線上所有邊機率的乘積。請回傳從 `start` 到 `end` 成功機率最大的路線之機率；若兩點不連通，回傳 0。與正確答案誤差在 10⁻⁵ 以內都算對。限制：`2 <= n <= 10⁴`，`0 <= len(edges) <= 2 × 10⁴`，`0 <= succProb[i] <= 1`，`start != end`，兩點之間最多一條邊。

- 範例 1：`n = 3`，`edges = [[0, 1], [1, 2], [0, 2]]`，`succProb = [0.5, 0.5, 0.2]`，`start = 0`、`end = 2`，回傳 `0.25`。直達只有 0.2，繞道 0 → 1 → 2 是 0.5 × 0.5 = 0.25。
- 範例 2：同上但 `succProb = [0.5, 0.5, 0.3]`，回傳 `0.3`，直達比較好。
- 範例 3（邊界）：`n = 3`，`edges = [[0, 1]]`，`succProb = [0.5]`，`start = 0`、`end = 2`，兩點不連通，回傳 `0`。
- 範例 4（邊界）：唯一的邊機率是 0 時，回傳 `0`；機率是 1 時，回傳 `1`。

### 思路

暴力解是 DFS 列舉所有簡單路徑、取乘積最大的，指數級；Bellman-Ford 的最大化版本（鬆弛 n − 1 輪，`best[v] = max(best[v], best[u] * p)`）是 O(n · E) = 2 × 10⁸，太慢。

這題是 18.4 節表格的第三列：成本的合併是乘法、目標是最大化。檢查兩個條件：因為每條邊的機率 q ≤ 1，`p * q <= p`，**延伸路徑只會讓機率變小或不變**，對應到「延伸不會變好」；若 p₁ ≥ p₂，乘上同一個 q ≥ 0 後 `p₁q >= p₂q`，前綴比較可傳遞。所以 Dijkstra 適用，只是方向反過來：每次彈出目前機率**最大**的點，它的機率已經不可能再提高，因為其他候選都更小，再乘上 ≤ 1 的數只會更小。Python 的 `heapq` 是 min-heap，存 `-p` 就能模擬 max-heap。

另一個等價的看法是取對數：令每條邊的權重為 `-log(q)`，因為 0 < q ≤ 1，權重 ≥ 0；乘積最大 ⟺ log 和最大 ⟺ `-log` 和最小。這把題目變回標準的非負權重最短路徑，也清楚說明了為什麼「q ≤ 1」是關鍵前提：若 q > 1，對應的權重是負數，Dijkstra 就失效了（見 F1）。實作上直接用乘法比較好，不必處理 log(0) 與浮點誤差。

```text
範例 1：0-1 (0.5)、1-2 (0.5)、0-2 (0.2)，start = 0，end = 2
best 初始：0:1.0  1:0  2:0

步驟  彈出 (機率, 點)   鬆弛                         heap 之後（依機率由大到小）
 1   (1.00, 0)        1: 0 → 0.5，2: 0 → 0.2        (0.50,1) (0.20,2)
 2   (0.50, 1)        2: 0.2 → 0.5×0.5 = 0.25       (0.25,2) (0.20,2)
 3   (0.25, 2)        end 被彈出 → 回傳 0.25         (0.20,2) 是過期紀錄
```

步驟 1 時直達的 0.2 先被記錄，但點 2 沒有被彈出，所以還沒定案；步驟 2 彈出機率較大的點 1，經過它的路線把點 2 提高到 0.25。步驟 3 時 heap 裡最大的是 0.25，它就是點 2 的最終答案：剩下的候選 0.2 已經比較小，而任何經過其他點的路線只會更小。

### 解法

```python
import heapq
import random


def max_probability(n: int, edges: list[list[int]], succ_prob: list[float],
                    start: int, end: int) -> float:
    adj = [[] for _ in range(n)]
    for (u, v), p in zip(edges, succ_prob):
        adj[u].append((v, p))
        adj[v].append((u, p))
    best = [0.0] * n
    best[start] = 1.0
    heap = [(-1.0, start)]                # heapq 是 min-heap，存負值模擬 max-heap
    while heap:
        neg_p, u = heapq.heappop(heap)
        p = -neg_p
        if u == end:
            return p
        if p < best[u]:                   # 過期紀錄（最大化，所以方向相反）
            continue
        for v, pv in adj[u]:
            np_ = p * pv
            if np_ > best[v]:
                best[v] = np_
                heapq.heappush(heap, (-np_, v))
    return 0.0


def brute(n, edges, probs, s, t):
    best = [0.0] * n
    best[s] = 1.0
    for _ in range(n):
        for (u, v), p in zip(edges, probs):
            best[v] = max(best[v], best[u] * p)
            best[u] = max(best[u], best[v] * p)
    return best[t]


assert abs(max_probability(3, [[0, 1], [1, 2], [0, 2]], [0.5, 0.5, 0.2], 0, 2) - 0.25) < 1e-9
assert abs(max_probability(3, [[0, 1], [1, 2], [0, 2]], [0.5, 0.5, 0.3], 0, 2) - 0.3) < 1e-9
assert max_probability(3, [[0, 1]], [0.5], 0, 2) == 0.0
assert abs(max_probability(2, [[0, 1]], [1.0], 0, 1) - 1.0) < 1e-12
assert max_probability(2, [[0, 1]], [0.0], 0, 1) == 0.0
for _ in range(300):
    n = random.randint(2, 7)
    es, ps = [], []
    for _ in range(random.randint(0, 12)):
        u, v = random.sample(range(n), 2)
        es.append([u, v])
        ps.append(random.choice([0.0, 0.1, 0.25, 0.5, 0.9, 1.0, random.random()]))
    s, t = random.sample(range(n), 2)
    assert abs(max_probability(n, es, ps, s, t) - brute(n, es, ps, s, t)) < 1e-9
print("all tests passed")
```

### 複雜度與邊界

時間 O(E log E)，E ≤ 2 × 10⁴，每條無向邊在兩個方向各最多推入一次；空間 O(n + E)。邊界情況：機率為 0 的邊永遠不會讓 `np_ > best[v]`（`best` 初始是 0），等於不存在，這正好符合「走不過去」的語意；機率為 1 的邊不降低機率，可能造成多個點機率相同，Dijkstra 仍正確（等同權重 0 的邊）；不連通時 end 永遠不會被彈出，回傳 0.0；過期紀錄的判斷是 `p < best[u]`，方向與最小化版本相反，寫錯成 `>` 會把有效紀錄全部丟掉。浮點連乘可能下溢成 0，見 F3。

### Follow-up

> [!question]- F1. 如果某些邊的「機率」大於 1（例如匯率，走過一次資金會變多）呢？
> 乘上大於 1 的數會變大，「延伸不會變好」不再成立，Dijkstra 會在定案後又被改善，結果錯誤。取 `-log(q)` 後這些邊變成負權重，所以要用 Bellman-Ford：鬆弛 n − 1 輪，O(n · E)。若第 n 輪仍能改善，代表存在一個乘積大於 1 的環，可以無限繞圈讓值變大，這正是「套利偵測」（匯率圖上的負環）。若題目保證沒有這種環，Bellman-Ford 的結果就是最大乘積。

> [!question]- F2. 如果要回傳成功機率最大的路線本身呢？
> 在 `np_ > best[v]` 成立時記錄 `parent[v] = u`，end 被彈出後沿 parent 從 end 走回 start 再反轉，O(n)。機率相同時（例如有機率 1 的邊）可能有多條最佳路線，題目若要求「邊數最少」的那條，可以把 heap 的 tuple 改成 `(-p, 邊數, 點)`，在機率相同時優先處理邊數少的，並把更新條件改成「機率更大，或機率相同但邊數更少」。

> [!question]- F3. 如果路線很長（例如 10⁴ 條邊、每條機率 0.5），浮點數會出什麼問題？
> 0.5¹⁰⁰⁰⁰ 遠小於 double 能表示的最小正數（約 5 × 10⁻³²⁴），乘積會下溢成 0，所有長路線都變得無法比較。解法是改用 log 空間：權重 `-log(q)`，用標準 Dijkstra 加總，比較的是 log 和，不會下溢；最後若需要機率值再取 `exp(-dist)`（可能仍是 0，但路線比較已經正確）。q = 0 的邊直接跳過，因為 log(0) 沒有定義。時間不變，O(E log E)。

> [!question]- F4. 如果是有向圖，而且要回答很多組 (start, end) 的查詢呢？
> 有向只影響建圖：每條邊只加一個方向。多組查詢時，若 n 很小（≤ 400），可以用 Floyd-Warshall 的最大化版本：`p[i][j] = max(p[i][j], p[i][k] * p[k][j])`，O(n³) 預處理、O(1) 查詢；它的正確性同樣依賴機率 ≤ 1。若 n 很大但查詢的起點只有少數幾種，就對每個起點跑一次 Dijkstra 並快取整個 `best` 陣列。

## 核心題 5｜1584. Min Cost to Connect All Points｜Medium

### 題目

平面上有 n 個點，`points[i] = [xᵢ, yᵢ]`，所有點座標互不相同。連接點 i 與點 j 的成本是兩點的曼哈頓距離 `|xᵢ − xⱼ| + |yᵢ − yⱼ|`。請回傳讓所有點互相連通（任兩點之間恰好存在一條簡單路徑）的最小總成本。限制：`1 <= n <= 1000`，`-10⁶ <= xᵢ, yᵢ <= 10⁶`。

- 範例 1：`points = [[0, 0], [2, 2], [3, 10], [5, 2], [7, 0]]`，回傳 `20`。選 (0,0)–(2,2) 成本 4、(2,2)–(5,2) 成本 3、(5,2)–(7,0) 成本 4、(2,2)–(3,10) 成本 9。
- 範例 2：`points = [[3, 12], [-2, 5], [-4, 1]]`，回傳 `18`：(3,12)–(-2,5) 成本 12、(-2,5)–(-4,1) 成本 6。
- 範例 3（邊界）：`points = [[0, 0]]`，只有一個點，不需要任何邊，回傳 `0`。
- 範例 4：`points = [[0, 0], [1, 1], [1, 0], [-1, 1]]`，回傳 `4`。

### 思路

「任兩點之間恰好一條簡單路徑」就是一棵生成樹，所以題目要的是完全圖上的 MST：每對點之間都有一條邊，共 n(n − 1)/2 ≈ 5 × 10⁵ 條。暴力列舉所有生成樹是指數級（完全圖有 n^(n−2) 棵，Cayley 公式），完全不可行；要用 18.6 節的 cut property。

兩種標準做法的成本不一樣。Kruskal 要先產生所有 5 × 10⁵ 條邊並排序，O(n² log n)，記憶體也要存下所有邊；在 Python 中可以通過，但常數偏大。Prim 的陣列版本則完全不建邊：維護 `dist[v]` = 樹外的點 v 連到目前這棵樹的最便宜邊，每一輪掃描所有樹外的點找出最小的 u 加入樹，再用 u 更新其他點的 `dist`，邊的成本在需要時才當場計算。共 n 輪、每輪 O(n)，總時間 O(n²)、空間 O(n)，是完全圖的最佳選擇。

Prim 的正確性直接來自 cut property：每一輪的切割是「樹內 vs 樹外」，`dist` 的最小值就是跨越這個切割的最便宜邊，所以它一定屬於某棵 MST。它和陣列版 Dijkstra（核心題 1 F4）的程式結構完全一樣，唯一差別是更新式：Dijkstra 是 `dist[v] = min(dist[v], dist[u] + w)`，Prim 是 `dist[v] = min(dist[v], w)`。面試時把這個對比說出來，很能展現你理解兩者的本質差異。

```text
points: P0(0,0)  P1(2,2)  P2(3,10)  P3(5,2)  P4(7,0)
dist[v] = v 連到目前這棵樹的最便宜邊（'-' 表示已在樹中）

輪次  加入   本輪成本   累計    dist 之後: P0  P1  P2  P3  P4
 1    P0      0         0               -   4   13   7   7
 2    P1      4         4               -   -    9   3   7
 3    P3      3         7               -   -    9   -   4
 4    P4      4        11               -   -    9   -   -
 5    P2      9        20               -   -    -   -   -
```

第 2 輪加入 P1 後，P3 的 dist 從 7（連到 P0）降到 3（連到 P1），P2 從 13 降到 9；第 3 輪加入 P3 後，P4 從 7 降到 4（|7−5| + |0−2|）。注意 P2 的 dist 一直是 9，因為離它最近的樹內點始終是 P1；最後加入它時，連的就是 (2,2)–(3,10) 那條邊。總和 0 + 4 + 3 + 4 + 9 = 20。

### 解法

```python
import random
from itertools import combinations
from math import inf


def min_cost_connect_points(points: list[list[int]]) -> int:
    n = len(points)
    in_tree = [False] * n
    dist = [inf] * n                      # dist[v] = v 連到目前這棵樹的最便宜邊
    dist[0] = 0
    total = 0
    for _ in range(n):
        u = min((v for v in range(n) if not in_tree[v]), key=dist.__getitem__)
        in_tree[u] = True
        total += dist[u]
        ux, uy = points[u]
        for v in range(n):
            if not in_tree[v]:
                d = abs(ux - points[v][0]) + abs(uy - points[v][1])
                if d < dist[v]:
                    dist[v] = d
    return total


def kruskal_points(points):
    n = len(points)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    edges = sorted((abs(a[0] - b[0]) + abs(a[1] - b[1]), i, j)
                   for (i, a), (j, b) in combinations(enumerate(points), 2))
    total = used = 0
    for w, i, j in edges:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj
            total += w
            used += 1
            if used == n - 1:
                break
    return total


assert min_cost_connect_points([[0, 0], [2, 2], [3, 10], [5, 2], [7, 0]]) == 20
assert min_cost_connect_points([[3, 12], [-2, 5], [-4, 1]]) == 18
assert min_cost_connect_points([[0, 0]]) == 0
assert min_cost_connect_points([[0, 0], [1, 1], [1, 0], [-1, 1]]) == 4
for _ in range(300):
    pts = [[random.randint(-10, 10), random.randint(-10, 10)] for _ in range(random.randint(1, 9))]
    assert min_cost_connect_points(pts) == kruskal_points(pts)
pts = [[random.randint(-10**6, 10**6), random.randint(-10**6, 10**6)] for _ in range(1000)]
assert min_cost_connect_points(pts) == kruskal_points(pts)          # 最大規模
print("all tests passed")
```

### 複雜度與邊界

Prim 陣列版時間 O(n²)：n 輪，每輪掃描找最小值 O(n)、更新 dist O(n)；n = 1000 時約 2 × 10⁶ 次距離計算。空間 O(n)。Kruskal 版時間 O(n² log n)、空間 O(n²)。邊界情況：n = 1 時迴圈只跑一輪，加入 P0 成本 0，回傳 0；座標可以是負數，曼哈頓距離用絕對值，不受影響；最大距離 4 × 10⁶，總和最多約 4 × 10⁹，Python 沒有溢位，Java 要用 `long`。heap 版 Prim 在這裡反而較差：完全圖有 n² 條邊，會推入 O(n²) 筆紀錄，變成 O(n² log n)。

### Follow-up

> [!question]- F1. 如果已經有一些點之間建好了免費的連線，要在此基礎上補齊呢？
> 用 Kruskal 最自然：先把所有既有連線在 union-find 中合併（成本 0），再照原本的方式把候選邊依成本排序、跨元件才加入，直到只剩一個元件，O(n² log n)。用 Prim 也可以：把每個既有連線的成本設成 0 再跑，但要注意 0 成本邊不在「曼哈頓距離」的公式裡，需要額外的查表。這類「部分邊強制選入」的問題，也是 1489 題判斷 critical／pseudo-critical 邊的基本工具：強制選一條邊後重跑 MST，看總成本是否改變。

> [!question]- F2. 如果 n = 10⁵ 呢？
> O(n²) 不再可行，需要利用曼哈頓距離的幾何性質：以每個點為中心把平面分成 8 個 45° 的區域，可以證明 MST 中每個點只需要連到每個區域內最近的點，所以候選邊只有 O(n) 條。做法是把座標做 4 種變換（交換 x、y，取負號），每種變換下依 x + y 或 x − y 排序，用 Fenwick tree（第 26 章）找每個點在某個區域內的最近點，總共產生 4n 條候選邊，再用 Kruskal，O(n log n)。面試中能說出「候選邊可以縮減到 O(n)」以及大致方法就很好，通常不會要求寫完。

> [!question]- F3. 如果距離改成歐幾里得距離呢？
> 演算法不變，O(n²) 的 Prim 仍然適用，只是距離計算換成 `math.dist`；若只需要比較大小，用平方距離可以避免浮點誤差與開根號，但總成本要加總真正的距離，所以最後仍需開根號。n 很大時，歐幾里得 MST 一定是 Delaunay 三角剖分的子圖，三角剖分只有 O(n) 條邊，可以 O(n log n) 求出，但這在面試中屬於知道即可的範圍。

> [!question]- F4. 如果要的是「讓最長的那條連線盡量短」，而不是總和最小呢？
> 這是 minimum bottleneck spanning tree。一個重要的性質是：**任何 MST 同時也是 minimum bottleneck spanning tree**，因為若存在一棵生成樹 T' 的最大邊比 MST 的最大邊 e 還小，把 e 從 MST 移除後會把點分成兩群，T' 是生成樹，必定有一條邊跨越這兩群，而它比 e 小；用它替換 e 就得到總和更小的生成樹，矛盾。所以直接用本題的 Prim，記錄加入過的最大 `dist[u]` 即可，O(n²)。這也解釋了核心題 3 中「用 Kruskal 求 minimax 路徑」為什麼正確。

> [!question]- F5. 如果要回傳實際選了哪些邊呢？
> 在 Prim 中多維護 `link[v]`：每當 `dist[v]` 被點 u 更新成更小的值，就令 `link[v] = u`。點 u 加入樹時（u 不是起點），`(link[u], u)` 就是它連進樹的那條邊，共 n − 1 條。時間、空間複雜度不變。Kruskal 則在 `union` 成功時直接記錄 `(i, j)`。

## 難題 1｜882. Reachable Nodes In Subdivided Graph｜Hard

### 題目

有一張 n 個節點（編號 0 到 n − 1）的**無向**圖。`edges[i] = [u, v, cnt]` 代表原圖中 u 與 v 之間有一條邊，而這條邊被「細分」了：在 u 和 v 之間插入 cnt 個新節點，原本的一條邊變成一條由 cnt + 1 條小邊組成的鏈 `u – x₁ – x₂ – … – x_cnt – v`。cnt = 0 代表不細分。從節點 0 出發，每走一條小邊算一步，最多走 `maxMoves` 步，請回傳在細分後的新圖中，能到達的節點總數（原節點加上新節點）。限制：`1 <= n <= 3000`，`0 <= len(edges) <= min(n(n−1)/2, 10⁴)`，`0 <= cnt <= 10⁴`，`0 <= maxMoves <= 10⁹`，沒有重複邊與自環。

- 範例 1：`edges = [[0, 1, 10], [0, 2, 1], [1, 2, 2]]`、`maxMoves = 6`、`n = 3`，回傳 `13`。
- 範例 2：`edges = [[0, 1, 4], [1, 2, 6], [0, 2, 8], [1, 3, 1]]`、`maxMoves = 10`、`n = 4`，回傳 `23`。
- 範例 3（邊界）：`edges = [[1, 2, 4], [1, 4, 5], [1, 3, 1], [2, 3, 4], [3, 4, 5]]`、`maxMoves = 17`、`n = 5`，節點 0 沒有任何邊，回傳 `1`（只有它自己）。
- 範例 4（邊界）：`maxMoves = 0` 時只能到達節點 0，回傳 `1`。

### 提示

> [!tip]- 提示 1
> 新節點的總數可達 10⁴ × 10⁴ = 10⁸，不能真的把圖展開再 BFS。原圖的節點只有 3000 個，先想想它們各自最快幾步可以到達。

> [!tip]- 提示 2
> 把一條細分邊看成一條權重 cnt + 1 的普通邊，就能用 Dijkstra 求出每個原節點的最短步數 `dist[u]`。原節點能到達 ⟺ `dist[u] <= maxMoves`。

> [!tip]- 提示 3
> 對每條邊 (u, v, cnt) 獨立計算：從 u 這端最多能往鏈裡走 `a = max(0, maxMoves − dist[u])` 個新節點，從 v 那端最多 `b = max(0, maxMoves − dist[v])` 個。兩端可能重疊，所以這條邊貢獻 `min(cnt, a + b)`。

### 詳解

**為什麼直覺做法不行**。最直接的方法是把每條邊真的展開成 cnt 個新節點，在新圖上 BFS 走 maxMoves 層，數走到的節點。可是新節點總數是 Σ cnt，最多 10⁸，記憶體與時間都不夠；maxMoves 也可達 10⁹，逐層 BFS 更是不可能。瓶頸在於大部分新節點都只是「鏈上的一格」，它們沒有分岔，不需要個別處理。

**突破點一：原節點只需要普通的最短路徑**。鏈上沒有分岔，從 u 走到 v 唯一的方式就是走完整條鏈，共 cnt + 1 步。所以從原節點的角度看，細分邊等價於一條權重 cnt + 1 的普通邊。在原圖上跑 Dijkstra（權重非負），得到每個原節點的最少步數 `dist[u]`，`dist[u] <= maxMoves` 的原節點就是可到達的。這一步把 10⁸ 個節點的圖壓縮回 3000 個節點、10⁴ 條邊。

**突破點二：每條邊上的新節點可以獨立計算**。鏈上的新節點只能從鏈的兩端進入。從 u 端進入時，抵達 u 最少要 `dist[u]` 步，剩下 `maxMoves − dist[u]` 步可以往鏈裡走，每一步多覆蓋一個新節點，所以從 u 端最多覆蓋 `a = max(0, maxMoves − dist[u])` 個（但不超過 cnt）。同理從 v 端覆蓋 `b` 個。從 u 端覆蓋的是鏈的前 a 個、從 v 端覆蓋的是後 b 個，兩段合起來的聯集大小是 `min(cnt, a + b)`：若 a + b ≥ cnt 代表兩段重疊或相接，整條鏈都被覆蓋。

**為什麼用最短距離就夠**。某個新節點能被覆蓋，若且唯若存在一條長度 ≤ maxMoves 的路徑到達它，而這條路徑一定經過鏈的某一端（u 或 v）後才進入鏈。走到 u 的最短方式是 `dist[u]`，剩餘步數最多，所以用最短距離計算 a 不會漏掉任何可能；路徑走到鏈中再折返到另一端也不會更好，因為那等於繞道。注意 a、b 是兩條**不同的**路徑（一條經過 u、一條經過 v），題目問的是「能到達的節點」而不是「一次走完能覆蓋的節點」，所以它們可以各自獨立計算，不需要擔心一條路徑同時從兩端進入。

```text
範例 1：0–1 (cnt 10)、0–2 (cnt 1)、1–2 (cnt 2)，maxMoves = 6
權重 = cnt + 1：0–1 為 11、0–2 為 2、1–2 為 3

Dijkstra：
  彈出 (0, 0)：2 暫定 2；1 的候選 11 > maxMoves，被剪枝不推入
  彈出 (2, 2)：1 改善為 2 + 3 = 5
  彈出 (5, 1)：完成
  dist = [0, 5, 2]，三個原節點都 ≤ 6 → 3 個

每條邊的新節點：
  邊      cnt   a = 6 − dist[u]   b = 6 − dist[v]   min(cnt, a + b)
  0–1     10      6 − 0 = 6         6 − 5 = 1         min(10, 7) = 7
  0–2      1      6 − 0 = 6         6 − 2 = 4         min(1, 10) = 1
  1–2      2      6 − 5 = 1         6 − 2 = 4         min(2, 5)  = 2

0–1 這條鏈：0 [x1 x2 x3 x4 x5 x6] x7 x8 x9 [x10] 1
             └─ 從 0 端覆蓋 6 個 ─┘           └ 從 1 端覆蓋 1 個
總數 = 3 + 7 + 1 + 2 = 13
```

0–1 這條鏈的中間 x7、x8、x9 沒被覆蓋：從 0 端走 6 步只到 x6，而節點 1 要 5 步才到（經過 0 → 2 → 1），剩下 1 步只能走到 x10。0–2 這條鏈只有 1 個新節點，兩端都綽綽有餘，`min` 把重複計算的部分截掉。

### 解法

```python
import heapq
import random
from collections import deque
from math import inf


def reachable_nodes(edges: list[list[int]], max_moves: int, n: int) -> int:
    adj = [[] for _ in range(n)]
    for u, v, cnt in edges:
        adj[u].append((v, cnt + 1))       # 走完整條鏈要 cnt + 1 步
        adj[v].append((u, cnt + 1))
    dist = [inf] * n
    dist[0] = 0
    heap = [(0, 0)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v] and nd <= max_moves:   # 超過步數上限的點不必再擴展
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    ans = sum(1 for d in dist if d <= max_moves)    # 原節點
    for u, v, cnt in edges:                         # 每條鏈上的新節點
        a = max(0, max_moves - dist[u]) if dist[u] < inf else 0
        b = max(0, max_moves - dist[v]) if dist[v] < inf else 0
        ans += min(cnt, a + b)
    return ans


def brute(edges, max_moves, n):
    adj = [[] for _ in range(n)]
    nxt = n
    for u, v, cnt in edges:                         # 真的把每條邊展開成鏈
        chain = [u] + list(range(nxt, nxt + cnt)) + [v]
        nxt += cnt
        adj.extend([] for _ in range(cnt))
        for a, b in zip(chain, chain[1:]):
            adj[a].append(b)
            adj[b].append(a)
    dist = {0: 0}
    q = deque([0])
    while q:
        u = q.popleft()
        if dist[u] == max_moves:
            continue
        for v in adj[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return len(dist)


assert reachable_nodes([[0, 1, 10], [0, 2, 1], [1, 2, 2]], 6, 3) == 13
assert reachable_nodes([[0, 1, 4], [1, 2, 6], [0, 2, 8], [1, 3, 1]], 10, 4) == 23
assert reachable_nodes([[1, 2, 4], [1, 4, 5], [1, 3, 1], [2, 3, 4], [3, 4, 5]], 17, 5) == 1
assert reachable_nodes([], 0, 1) == 1
assert reachable_nodes([[0, 1, 0]], 1, 2) == 2           # cnt = 0 的邊
assert reachable_nodes([[0, 1, 5]], 0, 2) == 1           # 一步都不能走
for _ in range(400):
    n = random.randint(1, 5)
    es, seen = [], set()
    for _ in range(random.randint(0, 6)):
        if n < 2:
            break
        u, v = sorted(random.sample(range(n), 2))
        if (u, v) not in seen:
            seen.add((u, v))
            es.append([u, v, random.randint(0, 5)])
    mm = random.randint(0, 12)
    assert reachable_nodes(es, mm, n) == brute(es, mm, n)
print("all tests passed")
```

### 複雜度與邊界

時間 O(E log E + n)：Dijkstra 在 n ≤ 3000、E ≤ 10⁴ 的原圖上，加上一次掃描所有邊；與 Σ cnt（最多 10⁸）和 maxMoves（最多 10⁹）完全無關。空間 O(n + E)。邊界情況：`maxMoves − dist[u]` 在 u 到不了時是負無限大，所以要先判斷 `dist[u] < inf`，或用 `max(0, …)` 截掉（Python 的 `inf` 參與減法得到 `-inf`，`max(0, -inf)` 是 0，兩種寫法都對，程式中寫得明確一點）；cnt = 0 的邊沒有新節點，`min(0, …)` 是 0；節點 0 孤立時 Dijkstra 只定案自己，答案是 1；剪枝 `nd <= max_moves` 只是讓超出步數的點不進 heap，不影響正確性，因為那些點本來就不可達。

### Follow-up

> [!question]- F1. 如果每條鏈上的小邊不是 1 步，而是每條原始邊有自己的單步成本 cᵢ（鏈上每一小步都花 cᵢ）呢？
> 原圖的邊權變成 `(cnt + 1) · cᵢ`，Dijkstra 不變。每條鏈上從 u 端能覆蓋的新節點數變成 `a = (maxMoves − dist[u]) // cᵢ`（剩餘預算除以單步成本，向下取整），b 同理，貢獻仍是 `min(cnt, a + b)`。複雜度不變，O(E log E)。要注意 a 不能超過 cnt，但 `min` 已經處理了。

> [!question]- F2. 如果要回答很多個不同的 maxMoves 查詢呢？
> Dijkstra 的 `dist` 與 maxMoves 無關（去掉剪枝即可），只需要算一次。對每個查詢 M，答案是 `#{u : dist[u] ≤ M} + Σ_edges min(cnt, max(0, M − dist[u]) + max(0, M − dist[v]))`。第一項排序 dist 後用 bisect，O(log n)；第二項是每條邊一個關於 M 的分段線性函數（斷點在 dist[u]、dist[v] 以及兩段相接的那一點），可以把所有斷點排序後離線處理查詢，或每個查詢直接 O(E) 掃描。q 個查詢總共 O(E log E + q · E) 或離線 O((E + q) log(E + q))。

> [!question]- F3. 如果圖是有向的（細分後的鏈只能從 u 走向 v）呢？
> 原圖改成有向邊 u → v，權重 cnt + 1，Dijkstra 照常。鏈上的新節點只能從 u 端進入，所以每條邊的貢獻變成 `min(cnt, max(0, maxMoves − dist[u]))`，v 端不再貢獻。O(E log E)。這個變化說明了原題的 `a + b` 依賴無向圖「兩端都能進入」的性質。

> [!question]- F4. 為什麼不能用 BFS 而要用 Dijkstra？
> 在原圖上，不同的邊代表的步數不同（cnt + 1 從 1 到 10⁴ + 1），邊數最少的路線不一定步數最少，範例 1 中 0 → 1 直達要 11 步、0 → 2 → 1 只要 5 步。若真的展開成單位邊就能用 BFS，但節點數是 10⁸。所以「壓縮成帶權重的原圖 + Dijkstra」是在節點數與演算法之間的取捨：用 log 因子換掉 10⁴ 倍的節點數。

### 心得

關鍵突破是「鏈上沒有分岔」：原節點之間只需要權重 cnt + 1 的普通最短路徑，鏈上的新節點則只看兩端各剩幾步，用 `min(cnt, a + b)` 處理重疊。它和核心題 1 是同一個 Dijkstra，難度在於建模：辨認出細分邊等價於加權邊，並把「數節點」拆成原節點與每條邊兩部分獨立計算。面試時先說展開後 BFS 的做法與它為什麼太大，再提出「壓縮成加權圖」，最後畫一條鏈說明兩端覆蓋與重疊，這個畫面最能讓面試官信服。

## 難題 2｜1368. Minimum Cost to Make at Least One Valid Path in a Grid｜Hard

### 題目

給一個 m × n 的格子 `grid`，每一格有一個方向標誌：1 代表往右、2 代表往左、3 代表往下、4 代表往上。你從左上角 `(0, 0)` 出發，每到一格就照標誌移動到相鄰格；標誌可能指向格子外面。你可以修改任意格子的標誌（每格最多改一次），每改一格成本 1。請回傳讓「從 (0, 0) 照標誌走能到達右下角 (m − 1, n − 1)」所需的最小成本。限制：`1 <= m, n <= 100`，`1 <= grid[i][j] <= 4`。

- 範例 1：`grid = [[1, 1, 1, 1], [2, 2, 2, 2], [1, 1, 1, 1], [2, 2, 2, 2]]`，回傳 `3`。第一列一路往右到 (0, 3)，把它改成往下；第二列一路往左到 (1, 0)，改成往下；第三列往右到 (2, 3)，改成往下，到達終點。
- 範例 2：`grid = [[1, 1, 3], [3, 2, 2], [1, 1, 4]]`，回傳 `0`：照原本的標誌就能走到終點。
- 範例 3：`grid = [[1, 2], [4, 3]]`，回傳 `1`。
- 範例 4（邊界）：`grid = [[4]]`，起點就是終點，不需要修改，回傳 `0`。

### 提示

> [!tip]- 提示 1
> 把每一格看成圖的節點，每一格往四個鄰居各有一條邊。照標誌走的那條邊「免費」，其他三條代表「把這格改成指向那裡」，成本是多少？

> [!tip]- 提示 2
> 題目變成：在邊權只有 0 和 1 的圖上，求 (0, 0) 到 (m − 1, n − 1) 的最短路徑。「每格最多改一次」會不會造成麻煩？想想最短路徑會不會經過同一格兩次。

> [!tip]- 提示 3
> 邊權只有 0、1 時用 0-1 BFS：代價 0 的鄰居放 deque 前端、代價 1 的放後端，O(mn)。

### 詳解

**為什麼直覺做法不行**。直覺是窮舉要修改哪些格子，再模擬走一遍，組合數是 2^(mn)。稍微聰明一點的想法是 DFS／回溯：沿標誌走，卡住（出界或繞圈）時嘗試修改，但「在哪裡改、改成什麼」的選擇會互相影響，沒有明顯的貪婪規則。另一個常見的錯誤直覺是只沿著「從起點照標誌能走到的格子」做 BFS，卻忘了修改後的路線可能完全離開原本的軌跡。

**突破點：把修改變成邊權**。從格子 (r, c) 出發，下一步要去四個鄰居中的哪一個，完全由這一格的標誌決定。標誌指向的鄰居，不用修改就能到，成本 0；其他三個鄰居，要把這格的標誌改成指向它，成本 1。所以建一張圖：每格往四個鄰居各一條有向邊，照標誌的那條權重 0，其他權重 1。任何一組修改方案加上照標誌走的路線，都對應圖上一條路徑，成本等於路徑上權重 1 的邊數；反過來，圖上任何一條路徑也對應一組修改（把路徑上走權重 1 的格子改成指向下一格）。

**「每格最多改一次」為什麼不是問題**。上面的對應要求路徑上每格只被「離開」一次，否則同一格可能被要求指向兩個不同方向。但最短路徑（以成本計）可以假設不重複經過任何格子：如果路徑經過某格兩次，把兩次之間的那段環刪掉，成本不會增加（環上的邊權都 ≥ 0）。所以存在一條最短路徑是簡單路徑，每格最多被離開一次，修改不會衝突。

**用 0-1 BFS 而不是 Dijkstra**。邊權只有 0 和 1，18.4 節的 0-1 BFS 讓 deque 始終維持「前段距離 d、後段距離 d + 1」，每次 `popleft` 都是目前最小距離，效果等同 Dijkstra 但每次操作 O(1)。也可以理解成「分層 BFS」：先把成本 0 能到的格子全部找出來（沿標誌一路走），再從這一層每格花 1 擴展出下一層，依此類推。

```text
範例 1：標誌（→ ← ↓ ↑）           0-1 BFS 求出的 dist（= 需要修改幾次）
  → → → →                          0  0  0  0
  ← ← ← ←                          1  1  1  1
  → → → →                          2  2  2  2
  ← ← ← ←                          3  3  3  3

過程：
成本 0 層：(0,0) 沿 → 免費到 (0,1)、(0,2)、(0,3)；這些格往下走要改標誌，代價 1，放 deque 後端
成本 1 層：(1,0)…(1,3)。例如 (1,3) 沿 ← 免費到 (1,2)、(1,1)、(1,0)，同一層
成本 2 層：(2,0)…(2,3)
成本 3 層：(3,0)…(3,3)，終點 (3,3) 的 dist = 3

一條成本 3 的路線：
  (0,0)→(0,1)→(0,2)→(0,3) 改成 ↓ →(1,3)→(1,2)→(1,1)→(1,0) 改成 ↓
  →(2,0)→(2,1)→(2,2)→(2,3) 改成 ↓ →(3,3)
```

每一列內部都可以沿標誌免費移動，所以整列的成本相同；換到下一列一定要改一次標誌，因為沒有任何格子的標誌是往下的。這張圖也展示了 0-1 BFS 的層次：同一層的格子是用 `appendleft` 連成的，下一層的格子則被 `append` 到尾端，處理完整層才會輪到它們。

### 解法

```python
import heapq
import random
from collections import deque
from math import inf

DIRS = {1: (0, 1), 2: (0, -1), 3: (1, 0), 4: (-1, 0)}


def min_cost(grid: list[list[int]]) -> int:
    m, n = len(grid), len(grid[0])
    dist = [[inf] * n for _ in range(m)]
    dist[0][0] = 0
    dq = deque([(0, 0)])
    while dq:
        r, c = dq.popleft()
        d = dist[r][c]
        for sign, (dr, dc) in DIRS.items():
            nr, nc = r + dr, c + dc
            if 0 <= nr < m and 0 <= nc < n:
                w = 0 if grid[r][c] == sign else 1   # 照標誌走免費，否則要改這格
                if d + w < dist[nr][nc]:
                    dist[nr][nc] = d + w
                    if w == 0:
                        dq.appendleft((nr, nc))
                    else:
                        dq.append((nr, nc))
    return dist[m - 1][n - 1]


def brute(grid):
    m, n = len(grid), len(grid[0])
    dist = {(0, 0): 0}
    heap = [(0, 0, 0)]
    while heap:
        d, r, c = heapq.heappop(heap)
        if d > dist[(r, c)]:
            continue
        for sign, (dr, dc) in DIRS.items():
            nr, nc = r + dr, c + dc
            if 0 <= nr < m and 0 <= nc < n:
                nd = d + (grid[r][c] != sign)
                if nd < dist.get((nr, nc), inf):
                    dist[(nr, nc)] = nd
                    heapq.heappush(heap, (nd, nr, nc))
    return dist[(m - 1, n - 1)]


assert min_cost([[1, 1, 1, 1], [2, 2, 2, 2], [1, 1, 1, 1], [2, 2, 2, 2]]) == 3
assert min_cost([[1, 1, 3], [3, 2, 2], [1, 1, 4]]) == 0
assert min_cost([[1, 2], [4, 3]]) == 1
assert min_cost([[4]]) == 0
assert min_cost([[2, 2, 2]]) == 2                         # 一列且全指向左
for _ in range(400):
    g = [[random.randint(1, 4) for _ in range(random.randint(1, 5))]]
    g += [[random.randint(1, 4) for _ in range(len(g[0]))] for _ in range(random.randint(0, 4))]
    assert min_cost(g) == brute(g)
print("all tests passed")
```

### 複雜度與邊界

時間 O(mn)：每格最多被放進 deque 兩次（一次從後端、一次被改善後從前端），每次處理 4 個鄰居；Dijkstra 版本是 O(mn log(mn))。空間 O(mn)。邊界情況：1 × 1 的格子不論標誌為何都已經在終點，回傳 0；只有一列時，終點在最右邊，每個指向左（或上下）的格子都要改，範例 `[[2, 2, 2]]` 前兩格要改成往右，答案 2；終點格本身的標誌不重要，因為到達即可，程式自然不會計算從終點出發的成本；標誌指向格子外的邊直接忽略（等於那一格沒有免費邊）。

### Follow-up

> [!question]- F1. 如果要回傳應該修改哪些格子、改成什麼方向呢？
> 在鬆弛成功時記錄 `parent[(nr, nc)] = (r, c)`。從終點沿 parent 走回起點，對路徑上每一步 `(r, c) → (nr, nc)`，若 `grid[r][c]` 不是指向 `(nr, nc)` 的方向，就把 `(r, c)` 改成那個方向。修改次數恰好是 `dist[終點]`。因為最短路徑樹上的路徑是簡單路徑，不會出現同一格要改成兩個方向的衝突。時間、空間仍是 O(mn)。

> [!question]- F2. 如果每一格的修改成本不同（cost[r][c]），或改成不同方向的成本不同呢？
> 邊權不再只有 0 和 1，0-1 BFS 失效，改用 Dijkstra：從 (r, c) 照標誌到鄰居的邊權 0，其他方向的邊權 `cost[r][c]`（或 `cost[r][c][方向]`），O(mn log(mn))。若成本是小整數（例如 ≤ 3），也可以用 Dial's algorithm：開 `最大成本 + 1` 個桶子當循環佇列，依距離取出，O(mn · C)。這正是 0-1 BFS 的推廣。

> [!question]- F3. 如果最多只能修改 k 格，問能否到達終點？
> 直接比較 `min_cost(grid) <= k` 即可，O(mn)，不需要把 k 放進狀態，因為我們求的是最小修改次數，它若 ≤ k 就可行。只有當題目同時要最佳化另一個量（例如「最多改 k 格的前提下，最短的步數」）時，才需要狀態 `(r, c, 已改幾格)`，狀態數 mn(k + 1)，用 BFS 依步數分層，並以「改得更少」做支配剪枝。

> [!question]- F4. 如果從終點回到起點也要算（來回都要有合法路徑），修改的格子可以共用呢？
> 兩條路徑共用修改會讓問題變難：同一格在兩條路徑上可能需要指向不同方向，修改不再能獨立加總。一個安全的上界是兩次 0-1 BFS 的成本相加；精確解需要考慮兩條路徑的交互，一般要把狀態變成兩個位置的組合或用 min-cost flow 類的模型，超出一般面試範圍。面試時指出「單一路徑時修改不衝突是因為最短路徑是簡單路徑，兩條路徑就沒有這個保證」即可。

### 心得

關鍵突破是把「修改標誌」翻譯成「走一條代價 1 的邊」，於是組合搜尋變成 0-1 權重的最短路徑。它和本章其他題的關係是：核心題 1 是一般非負權重的 Dijkstra，這題是權重只有 0、1 的特例，用 deque 就能省掉 log；第 15 章的 BFS 則是權重全為 1 的特例。面試時要主動說明「每格最多改一次」為什麼不影響答案（最短路徑不重複經過格子），這是面試官最常追問的一點，也是這個建模是否正確的關鍵。

## 難題 3｜1928. Minimum Cost to Reach Destination in Time｜Hard

### 題目

有 n 個城市（編號 0 到 n − 1），由**無向**道路連接，`edges[i] = [x, y, time]` 代表 x 與 y 之間有一條路，走完要 time 分鐘；兩城市之間可能有多條路。每經過一個城市（包含起點與終點）都要付一次過路費 `passingFees[j]`，重複經過就重複付。你要從城市 0 出發，在 `maxTime` 分鐘內（含）抵達城市 n − 1，請回傳最小總過路費；做不到就回傳 -1。限制：`2 <= n <= 1000`，`n − 1 <= len(edges) <= 1000`，`1 <= time <= 1000`，`1 <= maxTime <= 1000`，`1 <= passingFees[j] <= 1000`，圖保證連通。

- 範例 1：`maxTime = 30`，`edges = [[0, 1, 10], [1, 2, 10], [2, 5, 10], [0, 3, 1], [3, 4, 10], [4, 5, 15]]`，`passingFees = [5, 1, 2, 20, 20, 3]`，回傳 `11`：走 0 → 1 → 2 → 5，時間 30，費用 5 + 1 + 2 + 3。
- 範例 2：同上但 `maxTime = 29`，回傳 `48`：上面那條路要 30 分鐘超時，只能走 0 → 3 → 4 → 5，時間 26，費用 5 + 20 + 20 + 3。
- 範例 3：同上但 `maxTime = 25`，回傳 `-1`：兩條路線都超時。
- 範例 4（邊界）：`n = 2`，`edges = [[0, 1, 3]]`，`passingFees = [4, 6]`；`maxTime = 5` 時回傳 `10`，`maxTime = 2` 時回傳 `-1`。

### 提示

> [!tip]- 提示 1
> 只看費用就是普通的最短路徑（費用在點上，進入點 v 的邊權是 `passingFees[v]`）。問題是「最便宜的路線可能超時」，和核心題 2 的「最便宜的路線可能轉機太多」是同一種困難。

> [!tip]- 提示 2
> 把時間放進狀態：`(城市, 已用時間)`。時間最多 1000、城市最多 1000，狀態數 10⁶。每走一條路時間嚴格增加，所以這張狀態圖有沒有環？

> [!tip]- 提示 3
> 狀態圖是 DAG（時間嚴格遞增），依時間由小到大做 DP：`dp[t][v]` = 恰好在時間 t 抵達 v 的最小費用，`dp[t][y] = min(dp[t − w][x] + fees[y])`。也可以用依費用排序的 Dijkstra，並用「抵達時間更早才保留」剪枝。

### 詳解

**為什麼直覺做法不行**。直覺一：以費用為權重跑 Dijkstra，再檢查時間。範例 2 就是反例：最便宜的路線（11）要 30 分鐘，超過 29；一維的 `cost[v]` 只保留最便宜的抵達方式，會把「較貴但較快」的路線丟掉。直覺二：以時間為權重跑 Dijkstra，找最快的路線。最快的路線（26 分鐘、費用 48）在 maxTime = 30 時不是最便宜的。直覺三：兩者加權成一個分數，但沒有任何固定權重能同時處理「時間是硬限制、費用是目標」。這是典型的**有資源限制的最短路徑**（constrained shortest path），一般情況是 NP-hard，但本題的時間上限只有 1000，可以把時間放進狀態。

**突破點一：時間放進狀態後是 DAG**。狀態 `(v, t)` 表示「在時間 t 位於城市 v」。從 `(x, t)` 走一條時間 w 的路到 y，得到 `(y, t + w)`，費用增加 `fees[y]`。因為 w ≥ 1，時間嚴格遞增，狀態圖沒有環，按 t 由小到大處理就是拓撲順序（第 16 章）。定義 `dp[t][v]` = 恰好在時間 t 抵達 v 的最小費用，`dp[0][0] = fees[0]`，轉移是對每條邊 (x, y, w) 兩個方向各做一次 `dp[t][y] = min(dp[t][y], dp[t − w][x] + fees[y])`。答案是 `min over t ≤ maxTime of dp[t][n − 1]`。時間 O(maxTime · E) = 10⁶，不需要 heap。

**突破點二：Dijkstra 加支配剪枝**。另一種寫法是以費用為主鍵跑 Dijkstra，狀態帶著時間 `(費用, 時間, 城市)`。heap 依費用彈出，所以後彈出的狀態費用不會更低；若城市 v 已經以時間 t₀ 被彈出過，之後彈出的 `(v, t)` 若 t ≥ t₀，就在費用與時間兩方面都不比之前好，可以丟掉。只有「時間更早」的狀態才值得繼續擴展。這就是 18.4 節的支配剪枝，`best_time[v]` 只需要一維。第一次彈出城市 n − 1 時，費用就是答案：任何更便宜的合法狀態都會更早被彈出。

**兩種寫法的比較**。DP 版本的複雜度穩定是 O(maxTime · E)，邏輯簡單、不會出錯，適合時間上限小的情況。Dijkstra 版本通常更快（很早就找到終點），而且不依賴時間是整數或上限很小，但最壞情況每個城市可能被接受很多次（每次時間嚴格變小），上界仍是 O(maxTime · E log)。面試時建議先講 DP 的建模（為什麼是 DAG），再提 Dijkstra 剪枝作為優化。

```text
範例 2：maxTime = 29，fees = [5, 1, 2, 20, 20, 3]
道路：0-1(10) 1-2(10) 2-5(10) 0-3(1) 3-4(10) 4-5(15)

Dijkstra（依費用彈出），best_time 記錄每個城市被接受時的時間
步驟  彈出 (費用, 時間, 城市)   判斷                     推入
 1   (5, 0, 0)               接受，best_time[0]=0      (6,10,1) (25,1,3)
 2   (6, 10, 1)              接受，best_time[1]=10     (8,20,2) (11,20,0)
 3   (8, 20, 2)              接受，best_time[2]=20     2→5 要 30 > 29、2→1 要 30 > 29，都不推
 4   (11, 20, 0)             20 >= best_time[0]=0，被支配，丟掉
 5   (25, 1, 3)              接受，best_time[3]=1      (45,11,4) (30,2,0)
 6   (30, 2, 0)              2 >= 0，被支配，丟掉
 7   (45, 11, 4)             接受，best_time[4]=11     (48,26,5) (65,21,3)
 8   (48, 26, 5)             彈出終點 → 回傳 48

若 maxTime = 30：步驟 3 可以推入 (11, 30, 5)，它會比 (25, 1, 3) 先彈出 → 回傳 11
```

步驟 3 是關鍵：費用最低的路線走到城市 2 時已經用了 20 分鐘，再走 10 分鐘到終點就超過 29，所以這條路線死了。步驟 4、6 展示了支配剪枝：回到城市 0 的狀態費用更高、時間也更晚，不可能比起點那個狀態更有用。最後是較貴但較快的 0 → 3 → 4 → 5 勝出。

### 解法

```python
import heapq
import random
from math import inf


def min_cost_dp(max_time: int, edges: list[list[int]], fees: list[int]) -> int:
    n = len(fees)
    dp = [[inf] * n for _ in range(max_time + 1)]   # dp[t][v]：恰好在時間 t 抵達 v 的最小費用
    dp[0][0] = fees[0]
    for t in range(1, max_time + 1):                 # 時間嚴格遞增 → 依 t 由小到大就是拓撲順序
        cur = dp[t]
        for x, y, w in edges:
            if w <= t:
                prev = dp[t - w]
                if prev[x] + fees[y] < cur[y]:
                    cur[y] = prev[x] + fees[y]
                if prev[y] + fees[x] < cur[x]:
                    cur[x] = prev[y] + fees[x]
    ans = min(dp[t][n - 1] for t in range(max_time + 1))
    return -1 if ans == inf else ans


def min_cost_dijkstra(max_time: int, edges: list[list[int]], fees: list[int]) -> int:
    n = len(fees)
    adj = [[] for _ in range(n)]
    for x, y, w in edges:
        adj[x].append((y, w))
        adj[y].append((x, w))
    best_time = [inf] * n                 # 已接受的狀態中，抵達 v 的最早時間
    heap = [(fees[0], 0, 0)]              # (費用, 時間, 城市)
    while heap:
        cost, t, u = heapq.heappop(heap)
        if u == n - 1:
            return cost
        if t >= best_time[u]:
            continue                      # 被支配：費用不低、時間也不早
        best_time[u] = t
        for v, w in adj[u]:
            if t + w <= max_time:
                heapq.heappush(heap, (cost + fees[v], t + w, v))
    return -1


def brute(max_time, edges, fees):
    n = len(fees)
    best = inf

    def dfs(u, t, cost):
        nonlocal best
        if u == n - 1:
            best = min(best, cost)
        for x, y, w in edges:
            for a, b in ((x, y), (y, x)):
                if a == u and t + w <= max_time:
                    dfs(b, t + w, cost + fees[b])

    dfs(0, 0, fees[0])
    return -1 if best == inf else best


E = [[0, 1, 10], [1, 2, 10], [2, 5, 10], [0, 3, 1], [3, 4, 10], [4, 5, 15]]
F = [5, 1, 2, 20, 20, 3]
for solve in (min_cost_dp, min_cost_dijkstra):
    assert solve(30, E, F) == 11
    assert solve(29, E, F) == 48
    assert solve(25, E, F) == -1
    assert solve(5, [[0, 1, 3]], [4, 6]) == 10
    assert solve(2, [[0, 1, 3]], [4, 6]) == -1
for _ in range(300):
    n = random.randint(2, 5)
    es = [[*random.sample(range(n), 2), random.randint(1, 4)] for _ in range(random.randint(0, 6))]
    fs = [random.randint(1, 9) for _ in range(n)]
    mt = random.randint(1, 8)
    exp = brute(mt, es, fs)
    assert min_cost_dp(mt, es, fs) == exp == min_cost_dijkstra(mt, es, fs)
print("all tests passed")
```

### 複雜度與邊界

DP 版本時間 O(maxTime · E) = 10⁶，空間 O(maxTime · n) = 10⁶（只保留最近 max(w) 層可以降低，但 w 也可能到 1000，意義不大）。Dijkstra 版本中每個城市被接受時時間嚴格遞減，最多 maxTime + 1 次，所以推入次數 O(maxTime · E)，時間 O(maxTime · E log(maxTime · E))，實務上遠低於上界。邊界情況：起點的費用也要付，所以初始值是 `fees[0]` 而不是 0；重複經過城市要重複付費，DP 與 Dijkstra 都自然允許繞路（但繞路只會更貴更慢，不會被選為答案）；兩城市之間可能有多條路，用邊串列而不是鄰接矩陣就不必特別處理；時間剛好等於 maxTime 是合法的（`<=`）。

### Follow-up

> [!question]- F1. 如果 maxTime 高達 10⁹，但城市與道路都只有 100 個呢？
> 時間不能再當 DP 的維度，但可以把角色對調：費用上限是 n · maxFee 量級時，改以費用為維度，`dp[c][v]` = 費用恰好 c 抵達 v 的最短時間，最後找最小的 c 使 `dp[c][n−1] <= maxTime`。若兩者都很大，Dijkstra 加支配剪枝仍然正確，它實際保留的是每個城市的 Pareto front（費用與時間都不被支配的狀態），一般情況下規模可接受，但最壞情況是指數級，這正是 constrained shortest path 是 NP-hard 的原因。面試時說明「哪個資源小就放進狀態」即可。

> [!question]- F2. 如果要回傳實際的路線呢？
> DP 版本記錄 `parent[t][v] = (t − w, x)`，從最佳的 `(t*, n − 1)` 往回走到 `(0, 0)`，空間 O(maxTime · n)。Dijkstra 版本在每個推入的狀態中多存一個指向父狀態的索引（把所有推入的狀態存在一個 list 中，heap 裡放索引），彈出終點後沿父指標回溯。兩者都不增加時間複雜度。

> [!question]- F3. 如果過路費改成在道路上（每條路有自己的費用），或每個城市有等待時間呢？
> 費用在邊上只是改變轉移時加的數字：`dp[t][y] = min(dp[t − w][x] + cost(x, y))`，演算法完全不變。城市有固定的停留時間 s[v] 時，把它併入進入該城市的邊時間：走 x → y 的時間變成 `w + s[y]`，時間仍嚴格遞增，DAG 性質不變。若可以選擇在城市「等待任意時間」，等待不會讓費用變少，所以永遠不需要等待，可以忽略；除非費用隨時間變化（例如尖峰時段加價），那時狀態圖要加上「等一分鐘」的邊，仍是 DAG。

> [!question]- F4. 如果還限制最多經過 k 個城市呢？
> 狀態再加一維變成 `(v, t, 經過城市數)`，DP 是 O(maxTime · k · E)；或者觀察到在本題中，經過城市數本身受時間限制（每條路至少 1 分鐘，所以最多 maxTime 條路），若 k ≥ maxTime 就不必處理。一般而言，每多一種資源限制，狀態就乘上該資源的範圍，面試時先估算狀態數再決定是否可行。

### 心得

關鍵突破是「時間嚴格遞增，所以 `(城市, 時間)` 的狀態圖是 DAG」，有資源限制的最短路徑因此變成依時間分層的 DP；Dijkstra 版本則是用「時間更早才保留」的支配剪枝控制狀態數。它和核心題 2（787）是同一類題：787 的資源是轉機次數，這題是時間；兩題都證明了「一維 dist 只保留最便宜」在有限制時會出錯。面試時先用範例 2 說明單純 Dijkstra 為什麼錯，再提出把時間放進狀態，並估算 maxTime × n = 10⁶ 個狀態可行，最後補上 Dijkstra 剪枝作為常數優化。

## 難題 4｜2045. Second Minimum Time to Reach Destination｜Hard

### 題目

一座城市有 n 個路口（編號 1 到 n），由**無向**道路 `edges[i] = [u, v]` 連接，每條路都要走 `time` 分鐘。每個路口有一個紅綠燈，所有燈在時間 0 同時變成綠燈，之後每 `change` 分鐘切換一次（綠 → 紅 → 綠 …），所有燈同步。你可以在任何時間**抵達**路口，但只能在綠燈時**離開**；綠燈時不能停下等待（到達時若是綠燈就必須立刻出發）。從路口 1 出發（時間 0），請回傳到達路口 n 的「第二短時間」：所有可能抵達時間中，**嚴格大於**最短時間的最小值。路線可以重複經過任何路口（包含 1 和 n）。限制：`2 <= n <= 10⁴`，`n − 1 <= len(edges) <= min(2 × 10⁴, n(n−1)/2)`，圖連通、沒有重複邊，`1 <= time, change <= 10³`。

- 範例 1：`n = 5`，`edges = [[1, 2], [1, 3], [1, 4], [3, 4], [4, 5]]`，`time = 3`、`change = 5`，回傳 `13`。最短是 1 → 4 → 5，時間 6；第二短是 1 → 3 → 4 → 5：時間 3 到 3、時間 6 到 4，此時 6 落在 [5, 10) 的紅燈，等到 10 才出發，13 到 5。
- 範例 2：`n = 2`，`edges = [[1, 2]]`，`time = 3`、`change = 2`，回傳 `11`。最短是 1 → 2，時間 3；第二短是 1 → 2 → 1 → 2：3 到 2（紅燈 [2, 4)，等到 4），7 到 1（紅燈 [6, 8)，等到 8），11 到 2。
- 範例 3（邊界）：`n = 3`，`edges = [[1, 2], [2, 3], [1, 3]]`，`time = 1`、`change = 10`，回傳 `2`：直達 1 → 3 是 1，繞道 1 → 2 → 3 是 2，都不碰到紅燈。
- 範例 4（邊界）：`n = 2`，`edges = [[1, 2]]`，`time = 5`、`change = 100`，回傳 `15`，只能來回 1 → 2 → 1 → 2。

### 提示

> [!tip]- 提示 1
> 每條路的時間都一樣，紅綠燈對所有人同步。如果兩條路線走的**邊數**相同，抵達時間會一樣嗎？邊數多的路線會不會反而比較早到？

> [!tip]- 提示 2
> 抵達時間只取決於邊數，而且邊數越多時間嚴格越大。所以題目變成：找從 1 到 n 的「嚴格第二短」的邊數（路線可以重複經過節點）。

> [!tip]- 提示 3
> 用 BFS，每個節點保存兩個值：最短距離 `first[v]` 與嚴格大於它的次短距離 `second[v]`。一個新的距離 d 若小於 first 就更新 first，若介於 first 與 second 之間就更新 second，兩種情況都把 (v, d) 放進 queue。最後把 `second[n]` 換算成時間。

### 詳解

**為什麼直覺做法不行**。最直接的想法是在狀態 `(路口, 抵達時間)` 上跑 Dijkstra，並讓每個路口最多被彈出兩次（兩個不同的時間）。這是可行的，但要小心處理「同一時間不算兩次」與紅綠燈的等待；另一個直覺是「第二短路徑一定是最短路徑改一條邊」，在一般 k-shortest paths 問題中這需要 Yen's algorithm，太複雜了。真正的突破來自觀察這題的特殊結構：所有邊的時間都相同，紅綠燈也全部同步。

**突破點一：時間只取決於邊數，且嚴格遞增**。定義 `f(k)` = 走 k 條邊後的抵達時間。因為所有路口的燈同步、每條路時間相同，從時間 t 抵達某路口後，下一次抵達的時間是 `leave(t) + time`，其中 `leave(t)` = t（綠燈）或下一個綠燈開始的時間（紅燈），與在哪個路口無關。所以 f(k) 只取決於 k，不取決於走哪條路。而且 `leave(t) >= t` 且 leave 不遞減，加上 time ≥ 1，所以 f(k + 1) > f(k)：**邊數越多，時間嚴格越晚**。因此「第二短時間」= f(第二短的邊數)，題目簡化成在無權圖上找嚴格次短的路線長度。

**突破點二：BFS 保留每個點的前兩個距離**。允許重複經過節點，次短路線長度一定存在：若最短是 d，至少 d + 2 是可行的（在任一條邊上來回一次）；若存在長度 d + 1 的路線，次短就是 d + 1。用 BFS 時，每個點記錄 `first[v]` 和 `second[v]`。從 queue 取出 (u, d) 後，對每個鄰居 v 計算 nd = d + 1：若 nd < first[v]，它是新的最短；若 first[v] < nd < second[v]，它是新的次短（嚴格大於 first）；相等的距離不必重複處理。每個點最多被放入 queue 兩次，所以是 O(n + E)。BFS 的正確性和普通 BFS 一樣：queue 中的距離不遞減，所以每個點第一次被賦值的 first 是最短，第一次被賦值的 second 是嚴格次短。

**換算時間**。拿到次短邊數 k 後，模擬 k 步：若目前時間 t 落在紅燈區間（`(t // change) % 2 == 1`），先等到 `(t // change + 1) * change`，再加上 time。這裡 k 最多約 n + 1，模擬是 O(n)。

```text
範例 1：邊 1-2、1-3、1-4、3-4、4-5，time = 3，change = 5

BFS（每個點保存 first / second）
取出      鄰居更新
(1, 0)    2: first=1   3: first=1   4: first=1
(2, 1)    1: second=2（2 > first[1]=0）
(3, 1)    4: 2 > first[4]=1 → second[4]=2
(4, 1)    3: second[3]=2   5: first[5]=2   (1 的 2 不小於 second[1]，略過)
(1, 2)    2: second[2]=3   (3、4 的 3 不小於它們的 second，略過)
(4, 2)    5: 3 > first[5]=2 → second[5]=3
…         之後的距離都不會再更新任何點
first[5] = 2，second[5] = 3

把邊數換算成時間（綠燈 [0,5)、紅燈 [5,10)、綠燈 [10,15)…）
步  出發前 t   燈號         出發時間   抵達時間
 1     0      綠            0          3
 2     3      綠            3          6
 3     6      紅（[5,10)）  10         13
f(2) = 6（最短），f(3) = 13（第二短）→ 回傳 13
```

最短路線 1 → 4 → 5 只有 2 條邊，在時間 6 抵達，剛好沒有在紅燈時需要出發；次短的 3 條邊路線（1 → 3 → 4 → 5）在時間 6 抵達路口 4 時碰上紅燈，要等 4 分鐘，所以總時間 13。注意 BFS 完全不需要知道紅綠燈，換算是在最後才做，這是把問題拆開的好處。

### 解法

```python
import random
from collections import deque
from math import inf


def second_minimum(n: int, edges: list[list[int]], time: int, change: int) -> int:
    adj = [[] for _ in range(n + 1)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    first = [inf] * (n + 1)               # 最短邊數
    second = [inf] * (n + 1)              # 嚴格大於 first 的次短邊數
    first[1] = 0
    q = deque([(1, 0)])
    while q:
        u, d = q.popleft()
        for v in adj[u]:
            nd = d + 1
            if nd < first[v]:
                first[v] = nd
                q.append((v, nd))
            elif first[v] < nd < second[v]:
                second[v] = nd
                q.append((v, nd))
    t = 0
    for _ in range(second[n]):
        if (t // change) % 2 == 1:        # 紅燈：等到下一個綠燈
            t = (t // change + 1) * change
        t += time
    return t


def brute(n, edges, time, change):
    adj = [[] for _ in range(n + 1)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    # 不用「時間只看邊數」的結論：直接模擬所有 (路口, 抵達時間) 狀態
    frontier = {1: {0}}
    times = set()
    for _ in range(4 * n + 4):
        nxt = {}
        for u, ts in frontier.items():
            for t in ts:
                leave = t if (t // change) % 2 == 0 else (t // change + 1) * change
                for v in adj[u]:
                    nxt.setdefault(v, set()).add(leave + time)
        frontier = nxt
        times |= frontier.get(n, set())
    return sorted(times)[1]


assert second_minimum(5, [[1, 2], [1, 3], [1, 4], [3, 4], [4, 5]], 3, 5) == 13
assert second_minimum(2, [[1, 2]], 3, 2) == 11
assert second_minimum(3, [[1, 2], [2, 3], [1, 3]], 1, 10) == 2
assert second_minimum(2, [[1, 2]], 5, 100) == 15
for _ in range(300):
    n = random.randint(2, 6)
    es = set()
    for v in range(2, n + 1):                                     # 先保證連通
        es.add(tuple(sorted((random.randint(1, v - 1), v))))
    for _ in range(random.randint(0, 5)):
        es.add(tuple(sorted(random.sample(range(1, n + 1), 2))))
    tm, ch = random.randint(1, 6), random.randint(1, 6)
    el = [list(e) for e in es]
    assert second_minimum(n, el, tm, ch) == brute(n, el, tm, ch)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n + E)：每個點最多進 queue 兩次（一次 first、一次 second），每次掃描它的鄰接串列；最後換算時間 O(second[n]) = O(n)。空間 O(n + E)。邊界情況：路口 1 本身的 `second[1]` 也會被更新（走出去再回來），這是必要的，因為次短路線可能經過起點，例如範例 2；圖只有一條邊時次短一定是 first + 2（來回）；紅燈判斷是 `(t // change) % 2 == 1`，t 剛好等於 change 的倍數時，奇數倍代表紅燈剛開始、偶數倍代表綠燈剛開始，例如 change = 5 時 t = 5 是紅、t = 10 是綠；「嚴格大於」用 `first[v] < nd` 排除相等的距離，否則兩條同樣長的最短路線會被誤當成第二短。

### Follow-up

> [!question]- F1. 如果每條路的時間不同呢？
> 「時間只取決於邊數」不再成立，要直接在時間上做 Dijkstra：每個點保留前兩個不同的抵達時間，heap 存 `(抵達時間, 點)`；彈出後計算離開時間 `leave(t)`（紅燈則等到綠燈），對鄰居推入 `leave(t) + w`。每個點最多接受兩次（兩個不同的時間），O(E log E)。正確性依賴「晚到不會早離開」：leave 不遞減，所以抵達時間仍滿足「延伸不會變好」（18.4 節表格最後一列）。

> [!question]- F2. 如果要的是第 k 短的時間（嚴格遞增的第 k 個值）呢？
> 在本題（邊時間相同）的結構下，答案是 f(第 k 小的可行邊數)。每個點保留最多 k 個不同的距離，BFS 中一個距離只要「不等於已存的任何一個且目前存的不足 k 個」就加入，每個點最多入 queue k 次，O(k · (n + E))。在一般加權圖上，每個點最多彈出 k 次的 Dijkstra（允許重複點的 k-shortest walks）是 O(k · E log(kE))；若要求簡單路徑，就要用 Yen's algorithm，複雜得多。

> [!question]- F3. 為什麼次短的邊數只可能是 first + 1 或 first + 2？這能怎麼利用？
> 若最短是 d，在路線上任一條邊來回一次就得到 d + 2，所以次短不超過 d + 2。d + 1 是否可行取決於圖的結構：二分圖（bipartite）中，從 1 到 n 的所有路線長度奇偶性都和 d 相同，d + 1 不可能出現，次短一定是 d + 2；非二分圖則要看是否真的存在長度 d + 1 的路線。這個上界有兩個用途：第一，它保證 BFS 的 `second[n]` 一定有限，不需要處理「沒有第二短」的情況；第二，它限制了換算時間時的模擬步數最多 n + 1 步。面試時說出「答案只有 d + 1 或 d + 2 兩種可能」，也能讓面試官確認你理解了「可以重複經過節點」這個條件的作用。

> [!question]- F4. 如果要回傳一條達到第二短時間的實際路線呢？
> 把 BFS 的狀態看成 `(點, 層別)`，層別 0 代表 first、1 代表 second。每次更新 `first[v]` 或 `second[v]` 時，記錄這個狀態的父狀態 `(u, u 的層別)`，也就是當時從 queue 取出的那一筆（queue 裡要多存層別）。最後從 `(n, 1)` 沿父狀態往回走到 `(1, 0)`，得到的路線長度恰好是 `second[n]`，可能重複經過某些點（例如範例 2 的 1 → 2 → 1 → 2）。狀態數 2n，時間與空間仍是 O(n + E)。

### 心得

關鍵突破是「所有邊時間相同、燈號同步，所以抵達時間只依賴邊數，而且邊數越多越晚」，把一個帶紅綠燈的時間問題化簡成無權圖上的嚴格次短路徑，再用「每個點保留前兩個距離」的 BFS 解決。它和本章其他題的關係是：大部分題目在擴充狀態（787 加轉機、1928 加時間），這題則是發現可以**縮小**狀態，紅綠燈完全不需要進入搜尋。面試時先說明 f(k) 嚴格遞增的理由，再寫 BFS，最後單獨寫一個換算時間的小迴圈，三段分開講最清楚。

## 難題 5｜1192. Critical Connections in a Network｜Hard

### 題目

有 n 台伺服器（編號 0 到 n − 1），由**無向**連線 `connections[i] = [a, b]` 組成一個網路，任兩台伺服器都可以直接或間接互通（圖連通）。一條連線若被移除後，會讓某些伺服器無法再互通，就稱為 critical connection（在圖論中稱為 bridge，橋）。請回傳所有 critical connections，順序不限，每條連線的兩端順序也不限。限制：`2 <= n <= 10⁵`，`n − 1 <= len(connections) <= 10⁵`，沒有自環也沒有重複連線。

- 範例 1：`n = 4`，`connections = [[0, 1], [1, 2], [2, 0], [1, 3]]`，回傳 `[[1, 3]]`。0、1、2 組成一個環，環上任一條邊斷掉都還有另一條路；伺服器 3 只靠 1–3 連著。
- 範例 2：`n = 2`，`connections = [[0, 1]]`，回傳 `[[0, 1]]`。
- 範例 3（邊界）：`n = 3`，`connections = [[0, 1], [1, 2], [2, 0]]`，整個是一個環，回傳 `[]`。
- 範例 4（邊界）：一條長鏈 `0 – 1 – 2 – … – (n−1)`，每一條邊都是 bridge，回傳全部 n − 1 條。

**這題和本章的關係**。它不是最短路徑題，放在本章是作為圖論的上限題。前面所有題目都在問「哪條路最好」或「哪些邊組成最好的樹」，這題問的是更根本的問題：**哪些邊是無可取代的**。一條邊是 bridge，若且唯若它屬於**每一棵**生成樹（拿掉它就不存在生成樹），所以每棵 MST 都必須包含所有 bridge；它也是 1489 題「MST 的 critical edge」在所有權重相同時的特例。拿掉 bridge 之後，兩側之間的最短距離直接變成無限大。工具上，它用的是 DFS tree 加上 low-link，這是第 15 章 DFS 的進階版，也是第 16 章提到的 Tarjan SCC 演算法的核心技巧。

### 提示

> [!tip]- 提示 1
> 暴力法是每次移除一條邊再檢查連通性，O(E · (V + E))，對 10⁵ 太慢。想想 DFS 走出的那棵樹：不在樹上的邊（back edge，回邊）能不能是 bridge？

> [!tip]- 提示 2
> 非樹邊一定在某個環上，所以不是 bridge。樹邊 (p, u) 是 bridge，若且唯若 u 的整棵子樹裡，沒有任何一條 back edge 能連回 p 或 p 的祖先。

> [!tip]- 提示 3
> 記錄每個點的發現時間 `disc[u]`，以及 `low[u]` = u 的子樹經由至多一條 back edge 能到達的最小發現時間。樹邊 (p, u) 是 bridge ⟺ `low[u] > disc[p]`。注意要跳過「進來的那條邊」本身，而不是跳過父節點。

### 詳解

**為什麼直覺做法不行**。最直接的是對每條邊：把它拿掉，做一次 BFS／DFS 檢查圖是否仍連通。每次 O(V + E)，共 E 次，O(E · (V + E)) = 10¹⁰。另一個直覺是「找出所有環，不在任何環上的邊就是 bridge」，概念正確，但列舉所有環本身就是指數級。我們需要一次 DFS 就同時判斷所有邊。

**突破點一：DFS tree 的結構**。在無向圖上做 DFS，每條邊不是 tree edge（樹邊，DFS 由它走到新節點），就是 back edge（回邊，連到已經在目前遞迴路徑上的祖先）；無向圖的 DFS 沒有 cross edge，因為若 u 和 v 之間有邊且 v 未被訪問，DFS 一定會從 u 走到 v。back edge (u, a) 和樹上 a 到 u 的路徑構成一個環，所以 back edge 永遠不是 bridge，bridge 一定是 tree edge。

**突破點二：low-link**。考慮樹邊 (p, u)。拿掉它之後，u 的子樹若要和其他部分保持連通，唯一的方式是子樹中某個點有一條 back edge 連到子樹外，也就是連到 p 或 p 的祖先（無向圖的 back edge 只會連到祖先）。定義 `disc[x]` 為 x 被發現的時間，`low[x]` 為「從 x 的子樹出發，走任意條樹邊往下、再走至多一條 back edge 能到達的最小 disc」。則 (p, u) 是 bridge ⟺ `low[u] > disc[p]`：子樹能到的最早節點比 p 還晚被發現，代表子樹繞不回 p 以上。若 `low[u] <= disc[p]`，子樹有一條 back edge 連到 p 或更早的祖先，和 (p, u) 一起構成環。

**計算 low**。`low[u]` 初始化為 `disc[u]`；遇到 back edge (u, a) 時 `low[u] = min(low[u], disc[a])`；子節點 c 處理完回到 u 時 `low[u] = min(low[u], low[c])`。要跳過「進入 u 的那條樹邊」本身，否則 u 會透過它看到父節點，`low[u]` 永遠 ≤ `disc[p]`，所有 bridge 都會被漏掉。實作時記錄的是「進來的**邊編號**」而不是「父節點」：本題沒有重複連線，兩種寫法結果相同，但若有平行邊（兩條連線都連 p 和 u），第二條邊是合法的 back edge，拿掉其中一條不會斷，用邊編號判斷才不會把它誤判為 bridge（測試中的 `[[0, 1], [0, 1]]`）。

**迭代實作**。n 可達 10⁵，長鏈會讓遞迴深度達 10⁵，超過 Python 預設的遞迴上限（約 1000），即使調高上限也可能讓直譯器 stack overflow。所以用顯式 stack，每個元素存 `(節點, 進入的邊編號, 下一個要看的鄰居索引)`，模擬遞迴的「看下一個鄰居」與「子節點返回後更新 low」兩個時機。

```text
範例 1：邊 e0=0-1、e1=1-2、e2=2-0、e3=1-3

DFS（從 0 開始）                         disc / low 變化
訪問 0                                   disc[0]=0  low[0]=0
  經 e0 訪問 1                           disc[1]=1  low[1]=1
    經 e1 訪問 2                         disc[2]=2  low[2]=2
      看 e1：是進來的邊，跳過
      看 e2：0 已訪問 → back edge        low[2]=min(2, disc[0]=0)=0
    2 返回：low[1]=min(1, low[2]=0)=0；low[2]=0 > disc[1]=1？否 → 1-2 不是 bridge
    經 e3 訪問 3                         disc[3]=3  low[3]=3
      看 e3：是進來的邊，跳過
    3 返回：low[1]=min(0, 3)=0；low[3]=3 > disc[1]=1？是 → 1-3 是 bridge
  1 返回：low[0]=0；low[1]=0 > disc[0]=0？否 → 0-1 不是 bridge
  看 e2：2 已訪問 → back edge，low[0]=min(0, 2)=0

DFS tree：         0
                   |  e0
                   1
                 /   \
           e1  2       3  e3        e2（2 → 0）是 back edge
```

節點 2 的 back edge 讓 `low[2] = 0`，這個值一路往上傳給節點 1，所以 0–1 和 1–2 都「被環保護」；節點 3 的子樹只有自己，沒有任何 back edge，`low[3]` 停在自己的發現時間 3，大於父節點 1 的發現時間，所以 1–3 是唯一的 bridge。

### 解法

```python
import random


def critical_connections(n: int, connections: list[list[int]]) -> list[list[int]]:
    adj = [[] for _ in range(n)]
    for i, (u, v) in enumerate(connections):
        adj[u].append((v, i))
        adj[v].append((u, i))
    disc = [-1] * n                       # DFS 發現時間，-1 代表未訪問
    low = [0] * n                         # 子樹經由至多一條 back edge 能到達的最小發現時間
    bridges = []
    timer = 0
    for root in range(n):
        if disc[root] != -1:
            continue
        disc[root] = low[root] = timer
        timer += 1
        stack = [(root, -1, 0)]           # (節點, 進入它的邊編號, 下一個要看的鄰居索引)
        while stack:
            u, pe, i = stack[-1]
            if i < len(adj[u]):
                stack[-1] = (u, pe, i + 1)
                v, eid = adj[u][i]
                if eid == pe:
                    continue              # 只跳過進來的那條邊（用編號判斷，平行邊才正確）
                if disc[v] == -1:         # tree edge：往下走
                    disc[v] = low[v] = timer
                    timer += 1
                    stack.append((v, eid, 0))
                else:                     # back edge：更新 low
                    low[u] = min(low[u], disc[v])
            else:                         # u 的子樹處理完，回到父節點
                stack.pop()
                if stack:
                    p = stack[-1][0]
                    low[p] = min(low[p], low[u])
                    if low[u] > disc[p]:  # u 的子樹繞不回 p 或更早 → (p, u) 是 bridge
                        bridges.append([p, u])
    return bridges


def brute(n, conns):
    def components(skip):
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        comp = n
        for i, (u, v) in enumerate(conns):
            if i != skip and find(u) != find(v):
                parent[find(u)] = find(v)
                comp -= 1
        return comp

    base = components(-1)
    return {frozenset(e) for i, e in enumerate(conns) if components(i) > base}


def norm(res):
    return {frozenset(e) for e in res}


assert norm(critical_connections(4, [[0, 1], [1, 2], [2, 0], [1, 3]])) == {frozenset((1, 3))}
assert norm(critical_connections(2, [[0, 1]])) == {frozenset((0, 1))}
assert critical_connections(3, [[0, 1], [1, 2], [2, 0]]) == []        # 整個是環
assert critical_connections(2, [[0, 1], [0, 1]]) == []                # 平行邊不是 bridge
for _ in range(400):
    n = random.randint(1, 8)
    conns = [random.sample(range(n), 2) for _ in range(random.randint(0, 10))] if n >= 2 else []
    res = critical_connections(n, conns)
    assert len(res) == len(norm(res)) and norm(res) == brute(n, conns)
big = [[i, i + 1] for i in range(99999)]                               # 長鏈：遞迴版會超過深度上限
assert len(critical_connections(100000, big)) == 99999
print("all tests passed")
```

### 複雜度與邊界

時間 O(V + E)：每個點被發現一次、出棧一次，每條邊在兩個方向的鄰接串列中各被看一次。空間 O(V + E)，鄰接串列加上 disc、low 與 stack。邊界情況：本題保證連通，但程式的外層迴圈對每個未訪問的點都開一次 DFS，所以不連通的圖也正確（每個元件內各自找 bridge）；n = 2 且只有一條邊時它就是 bridge；長鏈測試確認迭代版沒有遞迴深度問題；`low[u]` 的 back edge 更新用 `disc[v]` 而不是 `low[v]`：對 bridge 判斷兩者都正確，但用 `disc[v]` 符合 low 的定義，在求 articulation point 時改用 `low[v]` 可能出錯，所以養成用 `disc[v]` 的習慣比較安全。

### Follow-up

> [!question]- F1. 如果要找的是 critical server（articulation point，割點）：拿掉一台伺服器就會讓網路斷開？
> 同一個 DFS，條件改成：非根節點 p 若有某個子節點 u 滿足 `low[u] >= disc[p]`（注意是 ≥），p 就是割點，因為 u 的子樹最多只能繞回 p 本身，拿掉 p 就斷了；根節點則是「DFS tree 上有兩個以上的子節點」才是割點。時間仍是 O(V + E)。bridge 用 `>`、割點用 `>=` 的差別，是面試官很喜歡追問的細節：bridge 問的是邊，子樹能繞回 p 就夠了；割點問的是點，繞回 p 也沒用，因為 p 本身被拿掉。

> [!question]- F2. 如果要回答「至少要再加幾條邊，才能讓網路中沒有任何 bridge」呢？
> 先把所有 bridge 移除，剩下的每個連通塊稱為 2-edge-connected component，把每塊縮成一個點，bridge 就是連接這些點的邊，縮完一定是一棵樹（bridge tree）。設這棵樹有 L 個葉子（度數為 1 的點），答案是 ⌈L / 2⌉（若根本沒有 bridge，樹只有一個點，答案是 0）：每加一條邊連接兩個葉子，能消掉兩個葉子到它們路徑上的所有 bridge，適當配對（例如依 DFS 順序把第 i 個葉子連到第 i + L/2 個）就能消掉全部。縮點 O(V + E)，總時間 O(V + E)。

> [!question]- F3. 如果是有向圖，問「拿掉哪條邊會讓某些點無法互相到達」呢？
> 有向圖的「互相到達」是 strongly connected component（SCC，強連通元件）。先用 Tarjan 或 Kosaraju 求 SCC（O(V + E)），這和本題同樣使用 disc 與 low，只是多一個 stack 記錄目前 SCC 的成員，並在 `low[u] == disc[u]` 時把 stack 上方的點彈出成一個 SCC。在一個 SCC 內，判斷某條邊是否為「強橋」（拿掉後 SCC 分裂）可以對每條邊做一次檢查，或用支配樹（dominator tree）等進階技巧做到線性，這已超出一般面試範圍。面試時說清楚「無向看 bridge、有向看 SCC」即可。

> [!question]- F4. 如果連線有權重（成本），要找的是「MST 中的關鍵邊」呢（1489. Find Critical and Pseudo-Critical Edges in MST）？
> 一條邊是 critical，若拿掉它之後 MST 的總權重變大（或圖不連通）；是 pseudo-critical，若它不是 critical，但強制選它之後仍能得到同樣權重的 MST。直接的做法是先求原 MST 權重 W，再對每條邊做兩次 Kruskal（一次排除它、一次強制先選它），O(E² α(V))，E ≤ 200 時可行。更快的做法是依權重分組，每組內把已合併的元件縮點，在縮點後的圖上對該組的邊找 bridge：組內的 bridge 就是 critical，其他能連接不同元件的就是 pseudo-critical，O(E log E)。這正好把本題的 bridge 與 18.6 節的 Kruskal 連在一起。

### 心得

關鍵突破是「bridge 一定是 DFS tree 的樹邊，而且它是 bridge ⟺ 下方子樹的 low 比上方節點的發現時間還晚」，用一次 DFS 就同時判斷所有邊。它和本章的關係是從另一個角度看「哪些邊重要」：最短路徑找最好的路、MST 找最便宜的連法，bridge 找的是任何連法都少不了的邊，每棵生成樹（因此每棵 MST）都必須包含它，F4 的 1489 題更直接把它和 Kruskal 結合。面試時先說暴力法 O(E · (V + E))，再畫出 DFS tree 並解釋 back edge 為什麼形成環，接著定義 disc 和 low，最後強調兩個實作細節：跳過的是「進來的邊」而不是父節點，以及大輸入要用迭代 DFS。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 標準單源最短路徑 | 非負邊權，從一點到其他點最少花費 | lazy Dijkstra，彈出時定案；只要一個終點時第一次彈出就回傳 | 核心題 1（743）、1976（計數版）、1334 |
| 非加總的路徑成本 | 「路上最大的一步」「機率連乘」 | 合併運算換成 `max` 或乘法，確認延伸不會變好；最大化用負值 heap | 核心題 3（1631）、核心題 4（1514）、778、1102 |
| 邊數或資源有上限 | 「最多 k 次轉機」「時間不超過 T」 | 依資源分層的 Bellman-Ford／DP，或狀態加資源維度＋支配剪枝 | 核心題 2（787）、難題 3（1928） |
| 0／1 權重 | 「照規則走免費、違反規則代價 1」 | 0-1 BFS：0 放前端、1 放後端，O(V + E) | 難題 2（1368）、2290、第 15 章 1293 F1 |
| 壓縮的圖 | 邊被細分、或大量節點沒有分岔 | 把鏈壓成加權邊跑 Dijkstra，再依剩餘預算計算鏈上的部分 | 難題 1（882） |
| 次短／第 k 短 | 「第二短」「嚴格大於最短的最小值」 | 每個點保留前 k 個不同的距離；邊權相同時用 BFS | 難題 4（2045）、k-shortest walks |
| 負權重 | 邊權可為負、套利、負環偵測 | Bellman-Ford V − 1 輪，第 V 輪仍可鬆弛即有負環 | 核心題 1 F2、核心題 4 F1 |
| DAG 最短／最長路 | 依賴關係、時間嚴格遞增的狀態圖 | 拓撲順序鬆弛一次，O(V + E)，負權也可 | 第 16 章 2050、難題 3 的 DP |
| 所有點對 | 很多組 (a, b) 查詢、V ≤ 400 | Floyd-Warshall，k 在最外層 | 1334、399、核心題 1 F5 |
| MST | 「把所有點連起來的最小總成本」 | 稀疏圖 Kruskal＋union-find；完全圖 O(V²) Prim | 核心題 5（1584）、1135、1168 |
| Bottleneck 路徑 | 最小化路徑上的最大邊 | MST 上的路徑就是 minimax 路徑；也可 Dijkstra 換 max 或二分答案 | 核心題 3（1631）、第 17 章 1697 |
| 不可取代的邊 | 「拿掉哪條邊會斷開」 | DFS tree＋low-link，樹邊 (p, u) 是 bridge ⟺ `low[u] > disc[p]` | 難題 5（1192）、1489 |

**下限與上限**。最簡單的形式是核心題 1：標準 Dijkstra，考的是模板寫對（彈出才定案、跳過過期紀錄）與知道為什麼需要非負權重。中間層是「換掉成本或狀態」：核心題 3、4 把加法換成 max 或乘法，核心題 2 加上邊數限制，考的是你能不能說出 Dijkstra 正確的條件，並在條件被破壞時（787 的一維 dist）找出正確的修補。上限的題目難在三個地方，常常同時出現：第一，**建模**，題目表面不是圖，必須先把修改變成邊權（1368）、把細分的鏈壓成加權邊（882）、或把時間放進狀態（1928）；第二，**縮小問題**，看出紅綠燈同步讓時間只依賴邊數（2045），整個時間維度都不必搜尋；第三，**換一個角度看邊**，bridge（1192）不問哪條路最好，而問哪條邊無可取代，需要 DFS tree 與 low-link 這種完全不同的工具。

**與其他 pattern 的關係**。BFS（第 15 章）是本章的特例：邊權全為 1 時 Dijkstra 的 heap 退化成 queue，0-1 BFS 則介於兩者之間。拓撲排序（第 16 章）提供 DAG 上的最短路徑，不需要 heap 且能處理負權重；難題 3 的時間 DP 本質上就是在狀態 DAG 上照拓撲順序鬆弛。Union-find（第 17 章）是 Kruskal 的引擎，也提供 bottleneck 問題的另一種解法（依權重排序後合併，直到兩點連通）。Heap（第 14 章）是 Dijkstra 與 Prim 的基礎，而 binary search（第 8 章）的「二分答案 + 圖搜尋」是 1631、778 這類 bottleneck 題的替代解。DP（第 21–24 章）和最短路徑的界線在於狀態圖有沒有環：無環就照順序 DP，有環且權重非負就用 Dijkstra。

**容易混淆之處**。第一，最短路徑樹與 MST 不同：前者讓「起點到每個點」最短，後者讓「整棵樹的總和」最小，18.6 節的三角形例子兩者選的邊不一樣；Prim 和 Dijkstra 的程式只差 heap 的 key（`w` 與 `d + w`），寫錯就會得到另一個東西。第二，Dijkstra 加上狀態維度後，一維的 `dist` 剪枝可能出錯（787），要用「資源更少才保留」的支配規則。第三，lazy Dijkstra 在負權重下只有「不提早結束、沒有負環」時才會算對，而且最差是指數時間；一旦加上「彈出終點就回傳」這類提早結束就會答錯，有負權重就用 Bellman-Ford。第四，Bellman-Ford 用來限制邊數時必須每輪從複本延伸，就地更新只適用於無限制的最短路徑。

## 本章重點整理

- 邊權相同用 BFS，只有 0／1 用 0-1 BFS，非負一般權重用 Dijkstra，有負權重用 Bellman-Ford，DAG 用拓撲順序，所有點對且 V 小用 Floyd-Warshall。
- Dijkstra 的不變式：heap 中最小的距離不可能再被改善，所以**彈出時**才定案；lazy deletion 用 `if d > dist[u]: continue` 跳過過期紀錄。
- Dijkstra 適用的條件是「延伸不會變好」與「前綴比較可傳遞」；加法配非負權重、`max`、乘上 ≤ 1 的機率都符合，模板只改合併那一行（1631、1514）。
- 有資源限制（轉機次數、時間）時，一維 `dist` 只保留最便宜，會丟掉「較貴但較省資源」的狀態；改用分層 Bellman-Ford、狀態 DP，或狀態帶資源並用支配剪枝（787、1928）。
- 限制最多 k 條邊的 Bellman-Ford，每一輪都要從上一輪的複本延伸，否則一輪內會串起多條邊。
- 資源每步嚴格增加時，`(點, 資源)` 的狀態圖是 DAG，依資源由小到大 DP 即可，不需要 heap（1928）。
- 建模比演算法更重要：修改標誌 = 代價 1 的邊（1368），細分的鏈 = 權重 cnt + 1 的邊加上兩端剩餘步數的 `min(cnt, a + b)`（882）。
- 「第二短」：每個點保留前兩個不同的距離，嚴格大於才算；邊權與燈號都相同時，時間只依賴邊數，BFS 就夠（2045）。
- MST 的基礎是 cut property：跨越任一切割的最便宜邊一定在某棵 MST 中；Kruskal 是排序加 union-find，Prim 是和 Dijkstra 只差 key 的 heap 迴圈。
- 完全圖（1584）用 O(V²) 的陣列版 Prim，不必建出 V² 條邊；稀疏圖用 Kruskal 或 heap 版 Prim。
- 任何 MST 同時也是 minimum bottleneck spanning tree，MST 上兩點的路徑就是 minimax 路徑，這連起了 1631、778、1697。
- Bridge 一定是 DFS tree 的樹邊，(p, u) 是 bridge ⟺ `low[u] > disc[p]`；跳過「進來的邊編號」而非父節點，大輸入用迭代 DFS（1192）。
