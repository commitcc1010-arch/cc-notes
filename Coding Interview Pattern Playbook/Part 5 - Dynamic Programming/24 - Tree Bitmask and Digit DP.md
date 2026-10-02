---
chapter: 24
title: DP：樹、Bitmask 與數位
part: 5
---

# 第 24 章　DP：樹、Bitmask 與數位

> [!abstract] 本章地圖
> **一句話**：當子問題不是「陣列的前 i 個」，而是「一棵子樹」「一個已用元素的集合」或「一個數字的前幾位」時，把狀態換成節點、bitmask 或（位置, tight, started），DP 的轉移邏輯完全不變。
>
> **辨識訊號**：
> - 輸入是一棵樹，每個節點要做選擇，而且相鄰節點互相限制（選了父節點就不能選子節點、要被鄰居覆蓋）
> - 要對「每一個節點」回答「以它為根」或「子樹外面」的問題，n 到 10⁴–10⁵，不能每個節點各做一次 DFS
> - n ≤ 20（常見 12–16），要排列、分組、指派，或「拜訪所有點」：狀態是一個「已經用掉哪些元素」的集合
> - 格子的寬度 ≤ 8–10，每一列的選擇只和上一列有關：一整列的選法壓成一個 bitmask
> - 「[1, N] 中有多少個數滿足某個位數性質」，N 高達 10⁹–10¹⁸，不能逐一檢查
>
> **核心題**：337、338、526、1986、902
>
> **難題**：834、943、1349、233、2376

## 24.1 這個 Pattern 解決什麼問題

第 21–23 章的 DP 都有一個共同點：子問題可以用一兩個整數索引描述，例如「前 i 個房子」「`s[:i]` 與 `t[:j]`」「區間 `[i, j]`」，於是狀態自然排成一維或二維表格，按索引順序填完即可。本章的三種技巧處理的是另一類題目：子問題的形狀不是一段前綴或區間，而是**一棵子樹、一個集合、一個數字的前綴**。它們看起來很不一樣，但面試時的思考步驟一模一樣：先問「做完一部分之後，後面的決策只需要知道什麼」，把那份資訊設計成狀態，再找一個保證子問題先算完的順序。

**樹 DP**。在一棵樹上，每個節點的子樹彼此不相交，而且只透過這個節點和外界連接。所以「子樹 u 的最佳解」只需要知道 u 自己的少量狀態（u 有沒有被選、u 有沒有被覆蓋），就能和外面拼起來。具體做法是後序走訪（postorder，先處理子節點再處理自己）：每個節點回傳一個小小的 tuple，父節點用子節點回傳的 tuple 組合出自己的 tuple。暴力枚舉每個節點選或不選是 O(2ⁿ)，樹 DP 是 O(n)。當題目要求「每個節點當根時的答案」，再加一遍由上往下的走訪，把「子樹外面」的資訊傳下去，這叫 rerooting（換根），一樣是 O(n)，不需要做 n 次 DFS。

**Bitmask DP**。排列、分組、走訪所有點這類問題，暴力解是 n! 種順序；但很多時候，後面的決策只在乎「哪些元素已經用掉」，不在乎用掉的順序。例如排列題只要知道已經放了哪些數字，就知道下一個位置是第幾個；TSP（traveling salesman problem，旅行推銷員問題）只要知道走過哪些城市、現在停在哪裡，就能決定接下來怎麼走。把「哪些元素已用」編成一個 n 位元的整數 mask，狀態數從 n! 降到 2ⁿ 或 2ⁿ · n。n = 15 時 15! ≈ 1.3 × 10¹²，而 2¹⁵ · 15 ≈ 5 × 10⁵，差距是天壤之別。

**數位 DP**。「1 到 N 之間有幾個數字的位數各不相同」，N 到 10⁹ 時逐一檢查太慢。關鍵是：一個數合不合法，只取決於它的位數序列；而由左到右決定每一位時，「目前前綴是否還貼著 N 的前綴」（tight）決定了下一位能填多大，「是否已經開始寫非零數字」（started）決定前導零該不該算。把位置、這兩個旗標和題目需要的少量資訊（位數和、已用過的數字集合）當狀態，總狀態數只有「位數 × 小狀態 × 4」，N = 10¹⁸ 也只需要幾千到幾萬次運算。

三者的共同結構可以用一句話記住：**樹 DP 把子問題切在子樹邊界，bitmask DP 把子問題壓成集合，數位 DP 把子問題切在位數邊界**。本章的核心題各示範一種最標準的形式，難題則示範三種技巧最常見的進階版本：rerooting（834）、TSP 型的 `dp[mask][last]`（943）、逐列的 profile DP（1349）、累加型的數位 DP（233）、數位 DP 加上 bitmask（2376）。

## 24.2 辨識訊號

| 題目特徵 | 為什麼是這個技巧 | 本章哪一題 |
|---|---|---|
| 樹上每個節點選或不選，相鄰的不能同時選 | 子樹只透過根和外界接觸，每個節點回傳（選, 不選）兩個狀態 | 核心題 1（337） |
| 對每個節點都要算一個「全樹」的量（距離和、最遠距離） | 先後序算子樹內，再前序傳子樹外，O(n) 而不是 O(n²) | 難題 1（834） |
| 要對 0…n 每個數算某個位元性質 | `i` 的答案可以由 `i >> 1` 或 `i & (i − 1)` 得到，這是所有 bitmask DP 的基本零件 | 核心題 2（338） |
| n ≤ 15 的排列計數，條件只和「位置、放的值」有關 | 已放的值的集合決定了下一個位置，`dp[mask]` 取代 n! | 核心題 3（526） |
| n ≤ 14 的分組、裝箱、分配工作 | `dp[mask]` 表示把 mask 這些元素處理完的最佳值，轉移是枚舉子集合或加一個元素 | 核心題 4（1986） |
| 「拜訪全部」「串接全部」「排列使總成本最小」，成本只和相鄰兩個元素有關 | TSP 型狀態 `dp[mask][last]` | 難題 2（943） |
| 格子寬度 ≤ 8，同列、相鄰列有衝突限制 | 一列的選法壓成 bitmask，`dp[row][mask]` 只看上一列 | 難題 3（1349） |
| 「[1, N] 中有幾個數……」，N 到 10⁹ 以上 | 數位 DP：位置 + tight + started + 小狀態 | 核心題 5（902）、難題 4（233）、難題 5（2376） |

兩個反向檢查很實用。第一，bitmask DP 的上限非常硬：2ⁿ · n 在 n = 20 時約 2 × 10⁷，Python 已經吃力；3ⁿ 在 n = 14 時約 4.8 × 10⁶，到 n = 16 就是 4.3 × 10⁷。看到 n ≤ 12、14、15、16、20 這類奇怪的小上限，幾乎就是在暗示指數級狀態；反過來，n = 10⁵ 的題目絕對不是 bitmask DP。第二，數位 DP 的訊號是「答案只跟數字的十進位寫法有關」；如果條件是「x 是質數」「x 的因數個數」這種和寫法無關的性質，數位 DP 幫不上忙。

## 24.3 模板一：樹 DP（後序回傳狀態與 rerooting）

樹 DP 有兩種形式。**後序回傳狀態**：以某個節點為根，每個節點用子節點的結果算出自己的結果，答案在根上。**Rerooting**：題目要每個節點當根時的答案，先做一遍後序算出「子樹內」的資訊，再做一遍前序算出「子樹外」的資訊，兩者合併。下面的模板用一般的無向樹（邊列表）示範，因為二元樹只是它的特例。

```python
import random
from collections import deque
from itertools import combinations


def rooted_order(n: int, edges: list[list[int]], root: int = 0):
    """回傳 (parent, order)：order 是 BFS 順序，父節點一定排在子節點前面。"""
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    parent = [-1] * n
    seen = [False] * n
    seen[root] = True
    order = [root]
    for u in order:                      # 邊走邊擴充的 list 就是 BFS 佇列
        for v in adj[u]:
            if not seen[v]:
                seen[v] = True
                parent[v] = u
                order.append(v)
    return parent, order


def max_independent_set(n: int, edges: list[list[int]], weight: list[int]) -> int:
    """後序回傳狀態：take[u] = 選 u 時子樹的最大權重，skip[u] = 不選 u 時的最大權重。"""
    parent, order = rooted_order(n, edges)
    take = weight[:]                     # 選 u：先放進 u 自己的權重
    skip = [0] * n
    for u in reversed(order):            # 反向 BFS 順序：子節點一定先處理完
        p = parent[u]
        if p >= 0:                       # 把 u 的兩個狀態併進父節點
            take[p] += skip[u]           # 選了 p，u 就不能選
            skip[p] += max(take[u], skip[u])
    return max(take[0], skip[0])


def eccentricity(n: int, edges: list[list[int]]) -> list[int]:
    """Rerooting：回傳每個節點到離它最遠的節點的距離。"""
    parent, order = rooted_order(n, edges)
    down1 = [0] * n                      # 往子樹走的最長距離
    down2 = [0] * n                      # 往「另一個」子節點走的最長距離
    best = [-1] * n                      # down1 是經由哪個子節點
    for u in reversed(order):            # 第一遍：後序，算子樹內的資訊
        p = parent[u]
        if p >= 0:
            cand = down1[u] + 1
            if cand > down1[p]:
                down2[p], down1[p], best[p] = down1[p], cand, u
            elif cand > down2[p]:
                down2[p] = cand
    up = [0] * n                         # 第一步走向父節點的最長距離（子樹外）
    for u in order[1:]:                  # 第二遍：前序，把子樹外的資訊往下傳
        p = parent[u]
        sibling = down2[p] if best[p] == u else down1[p]
        up[u] = 1 + max(up[p], sibling)
    return [max(down1[u], up[u]) for u in range(n)]


def random_tree(n):
    return [[i, random.randrange(i)] for i in range(1, n)]


def brute_mis(n, edges, w):
    best = 0
    for r in range(n + 1):
        for chosen in combinations(range(n), r):
            s = set(chosen)
            if all(not (u in s and v in s) for u, v in edges):
                best = max(best, sum(w[i] for i in chosen))
    return best


def brute_ecc(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    res = []
    for s in range(n):
        dist = [-1] * n
        dist[s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if dist[v] < 0:
                    dist[v] = dist[u] + 1
                    q.append(v)
        res.append(max(dist))
    return res


edges = [[0, 1], [0, 2], [2, 3], [2, 4], [4, 5]]
assert max_independent_set(6, edges, [1, 5, 2, 4, 1, 6]) == 15     # 選 1、3、5
assert max_independent_set(1, [], [7]) == 7
assert eccentricity(6, edges) == [3, 4, 2, 3, 3, 4]
assert eccentricity(1, []) == [0]
assert eccentricity(2, [[0, 1]]) == [1, 1]
for _ in range(300):
    n = random.randint(1, 9)
    es = random_tree(n)
    w = [random.randint(0, 9) for _ in range(n)]
    assert max_independent_set(n, es, w) == brute_mis(n, es, w)
    assert eccentricity(n, es) == brute_ecc(n, es)
print("all tests passed")
```

**後序回傳狀態的三個步驟**。第一步，**定義每個節點要回傳什麼**：問自己「父節點在決定自己時，需要知道子節點的什麼？」最大權重獨立集（maximum weight independent set，選一些不相鄰的節點使權重和最大）中，父節點選了自己，子節點就不能選，所以父節點需要「子節點不選時的最佳值」；父節點不選，子節點選不選都可以，所以還需要「子節點選時的最佳值」。於是每個節點回傳 `(take, skip)` 兩個數。第二步，**寫出合併式**：`take[p] = w[p] + Σ skip[c]`、`skip[p] = Σ max(take[c], skip[c])`，對每個子節點 c 加總，因為不同子樹之間互不影響。第三步，**決定處理順序**：子節點必須先算完。

**為什麼用 BFS 順序取代遞迴**。Python 預設的遞迴深度上限約 1000，而一條長鏈的樹深度就是 n。`rooted_order` 先用 BFS 得到一個「父節點一定在子節點之前」的順序，**倒過來走就是一個合法的後序**：處理 u 的時候，u 的所有子節點都排在 u 後面，已經在倒序中先處理過了。這個寫法完全不用遞迴，n = 10⁵ 的鏈也沒問題；面試時若樹的深度有保證（例如題目說樹是平衡的），直接寫遞迴 DFS 也可以，但要能說出深度的風險。二元樹題目（核心題 1）用遞迴寫比較直觀，本書兩種都會示範。

**Rerooting 的想法**。`eccentricity` 要算每個節點到最遠節點的距離。對每個節點各做一次 BFS 是 O(n²)。觀察：從 u 出發的最長路徑，第一步要嘛走向某個子節點（留在 u 的子樹內），要嘛走向父節點（離開子樹）。第一種在後序就能算出，記為 `down1[u]`；第二種記為 `up[u]`，它等於 1 加上「從父節點 p 出發、但不回到 u 的子樹」的最長距離，也就是 `max(up[p], p 往其他子節點的最長距離)`。麻煩在「排除 u 這個子節點」：max 不能用減法撤銷，所以每個節點記住最長和次長兩個值，以及最長值來自哪個子節點；若 u 正好是最長的來源就用次長，否則用最長。這是 rerooting 最常見的技巧，稱為 **top-2**。

```text
樹（以 0 為根）：      0
                    /   \
                   1     2
                        / \
                       3   4
                            \
                             5

第一遍（後序，由下往上）：down1 = 往子樹走的最長距離
節點:     5   4   3   2   1   0
down1:    0   1   0   2   0   3
down2:    0   0   0   1   0   1      （2 的次長來自 3；0 的次長來自 1）
best:     -   5   -   4   -   2

第二遍（前序，由上往下）：up[u] = 1 + max(up[p], 父節點往「別的」子節點的最長)
u=1: p=0，best[0]=2≠1 → 用 down1[0]=3 → up[1] = 1 + max(0, 3) = 4
u=2: p=0，best[0]=2=2 → 用 down2[0]=1 → up[2] = 1 + max(0, 1) = 2
u=3: p=2，best[2]=4≠3 → 用 down1[2]=2 → up[3] = 1 + max(2, 2) = 3
u=4: p=2，best[2]=4=4 → 用 down2[2]=1 → up[4] = 1 + max(2, 1) = 3
u=5: p=4，best[4]=5=5 → 用 down2[4]=0 → up[5] = 1 + max(3, 0) = 4

答案 = max(down1, up)：[3, 4, 2, 3, 3, 4]
```

**Rerooting 何時可以用減法**。如果合併運算可以撤銷（加總、計數、XOR），就不需要 top-2：父節點的總和減掉子節點的貢獻，就是「排除這個子節點」的結果。難題 1（834）的距離和就是這種情況，換根公式只有一行。如果合併是 max、min、gcd 這類不能撤銷的運算，就用 top-2，或用前綴／後綴陣列計算「除了第 i 個子節點以外」的合併值。面試時先判斷合併運算能不能撤銷，再決定寫法。

## 24.4 模板二：Bitmask DP（子集枚舉與 TSP 型狀態）

Bitmask 用一個整數的第 i 個位元表示「元素 i 在不在集合裡」。下表是本章會反覆用到的操作，全部 O(1)：

| 操作 | 寫法 | 說明 |
|---|---|---|
| i 在不在 mask 裡 | `mask >> i & 1` | Python 中 `>>` 優先於 `&`，等同 `(mask >> i) & 1` |
| 加入 i | `mask \| 1 << i` | `<<` 優先於 `\|` |
| 移除 i | `mask & ~(1 << i)` 或 `mask ^ 1 << i`（確定 i 在裡面時） | |
| 最低位的 1 | `mask & -mask` | 2 的補數：`-mask` 把最低位的 1 以上全部翻轉 |
| 拿掉最低位的 1 | `mask & (mask - 1)` | 核心題 2 的 DP 就靠它 |
| 元素個數 | `mask.bit_count()`（3.10+）或 `bin(mask).count("1")` | 也可以用 DP 預先算好 |
| 全集 | `(1 << n) - 1` | |
| 枚舉 mask 的子集合 | `sub = (sub - 1) & mask` | 見下方模板 |

```python
import random
from itertools import permutations


def subset_sums(a: list[int]) -> list[int]:
    """sums[mask] = mask 所選元素的總和；每個 mask 由「拿掉最低位」的子問題 O(1) 得到。"""
    n = len(a)
    sums = [0] * (1 << n)
    for mask in range(1, 1 << n):
        low = mask & -mask                       # 最低位的 1
        sums[mask] = sums[mask ^ low] + a[low.bit_length() - 1]
    return sums


def submasks(mask: int):
    """由大到小列出 mask 的所有子集合（含 mask 本身與 0）。"""
    sub = mask
    while True:
        yield sub
        if sub == 0:
            return
        sub = (sub - 1) & mask


def tsp(dist: list[list[int]]) -> int:
    """Held–Karp：從 0 出發、每個點恰好拜訪一次、回到 0 的最短總長。"""
    n = len(dist)
    if n == 1:
        return 0
    INF = float("inf")
    full = 1 << n
    dp = [[INF] * n for _ in range(full)]       # dp[mask][u]：走過 mask、停在 u
    dp[1][0] = 0
    for mask in range(1, full, 2):               # 只看含起點 0 的 mask
        for u in range(n):
            cur = dp[mask][u]
            if cur == INF:
                continue
            for v in range(n):
                if mask >> v & 1:
                    continue
                nxt = mask | 1 << v
                if cur + dist[u][v] < dp[nxt][v]:
                    dp[nxt][v] = cur + dist[u][v]
    return min(dp[full - 1][u] + dist[u][0] for u in range(1, n))


def brute_tsp(dist):
    n = len(dist)
    if n == 1:
        return 0
    best = float("inf")
    for p in permutations(range(1, n)):
        route = (0,) + p + (0,)
        best = min(best, sum(dist[route[i]][route[i + 1]] for i in range(n)))
    return best


assert subset_sums([3, 5, 7]) == [0, 3, 5, 8, 7, 10, 12, 15]
assert sorted(submasks(0b101)) == [0b000, 0b001, 0b100, 0b101]
assert list(submasks(0)) == [0]
for n in range(8):                               # 所有 (mask, sub) 配對共有 3^n 個
    assert sum(1 for m in range(1 << n) for _ in submasks(m)) == 3 ** n
d = [[0, 10, 15, 20], [10, 0, 35, 25], [15, 35, 0, 30], [20, 25, 30, 0]]
assert tsp(d) == 80                              # 0 → 1 → 3 → 2 → 0
assert tsp([[0]]) == 0
for _ in range(100):
    n = random.randint(2, 7)
    m = [[0 if i == j else random.randint(1, 20) for j in range(n)] for i in range(n)]
    assert tsp(m) == brute_tsp(m)
print("all tests passed")
```

**順序：為什麼 `for mask in range(1 << n)` 就夠了**。bitmask DP 的轉移通常是「從較小的集合走到較大的集合」：加入一個元素（`mask | 1 << v`），或由子集合組成（`sub ⊆ mask`）。子集合在數值上一定 ≤ 原集合，因為它只是把某些 1 變成 0，所以按數值由小到大處理 mask，任何 mask 被用到之前，它的所有子集合都已經算完。這就是 bitmask DP 的「拓撲順序」，不需要依元素個數分層。

**兩種轉移**。第一種是 **一次加一個元素**：`dp[mask | 1 << v]` 由 `dp[mask]` 推出，每個 mask 試 n 個元素，總共 O(2ⁿ · n)。核心題 3（526）的排列計數、核心題 4（1986）的「把下一個任務塞進目前的 session」都是這種。第二種是 **一次加一整組**：`dp[mask]` 由 `dp[mask ^ sub]` 推出，sub 是 mask 的一個子集合，代表最後一組。對每個 mask 枚舉所有子集合，總數是 Σ 2^|mask| = 3ⁿ，因為每個元素只有三種情況：不在 mask、在 mask 不在 sub、在 sub。n = 14 時 3ⁿ ≈ 4.8 × 10⁶，可以接受；n = 20 時 3.5 × 10⁹，不行。

**子集合枚舉為什麼正確**。`sub = (sub - 1) & mask` 的意思是：把 sub 減 1（最低位的 1 變成 0，它以下全部變成 1），再用 `& mask` 把不屬於 mask 的位元清掉。如果把 mask 的位元抽出來排成一個緊湊的二進位數，這個操作正好是那個緊湊數減 1，所以它會由大到小走過 mask 的每一個子集合，各一次。sub 走到 0 後要停止，否則 `(0 - 1) & mask` 又會變回 mask，形成無窮迴圈；模板中先 `yield` 再檢查 `sub == 0`，讓空集合也被列出來。

**TSP 型狀態 `dp[mask][last]`**。當成本取決於「相鄰兩個元素」（城市 u 走到 v 的距離、字串 u 接 v 的重疊長度），只記住集合不夠，因為下一步的成本還取決於最後一個元素是誰。於是狀態加一維 `last`：`dp[mask][u]` 是「走過 mask 中的每個點各一次、目前停在 u」的最小成本。轉移是選一個不在 mask 裡的 v：`dp[mask | 1 << v][v] = min(dp[mask][u] + dist[u][v])`。狀態數 2ⁿ · n、每個狀態 n 種轉移，總共 O(2ⁿ · n²)，這就是 Held–Karp 演算法。n = 12 時約 2¹² × 12² ≈ 5.9 × 10⁵ 次轉移，難題 2（943）正是這個規模。第 15 章難題 4（847）的「拜訪所有節點」用 BFS 在同一個 (node, mask) 狀態圖上找最短路，那是無權版本；有權時就是這裡的 DP。

```text
tsp 的狀態轉移（4 個城市，起點 0；mask 由右往左是城市 0、1、2、3）
dp[0001][0] = 0
dp[0011][1] = 10        0 → 1
dp[0101][2] = 15        0 → 2
dp[1001][3] = 20        0 → 3
dp[1011][3] = min(dp[0011][1] + d[1][3]) = 10 + 25 = 35          0 → 1 → 3
dp[1111][2] = min(dp[1011][1] + d[1][2], dp[1011][3] + d[3][2])
            = min(45 + 35, 35 + 30) = 65                          0 → 1 → 3 → 2
答案 = min over u 的 dp[1111][u] + d[u][0]，其中 u = 2 時 65 + 15 = 80
```

`dp[1011][1] = 45` 來自 `0 → 3 → 1`（20 + 25），`dp[1011][3] = 35` 來自 `0 → 1 → 3`。同樣的集合 {0, 1, 3}，停在不同的城市成本不同，後續的轉移也不同，這就是 `last` 這一維存在的理由。

## 24.5 模板三：數位 DP（tight 與 started）

數位 DP 回答的是「[1, N] 中有幾個整數滿足某個位數性質」。做法是把 N 寫成字串 `s`，由左到右逐位決定 x 的每一位數字，同時記住三種資訊：

- **pos**：目前在決定第幾位。
- **tight**：到目前為止，x 的前綴是否和 `s` 的前綴完全相同。若 tight，這一位最多只能填 `s[pos]`，否則 x 會超過 N；若不 tight，代表前面某一位已經填得比 N 小，之後每一位都可以自由填 0–9。
- **started**：x 是否已經寫下第一個非零數字。我們把所有比 N 短的數字也看成補了前導零的 len(s) 位數，例如 N = 1000 時，12 被看成 `0012`。started 為 False 的那些 0 是「還沒開始」，不能當成真正的數字 0 處理。

再加上題目需要的 **state**（位數和、上一位數字、已用過的數字集合……），就得到下面的模板：

```python
from functools import cache


def digit_dp(N: int, init, step, accept) -> int:
    """計算 [1, N] 中有多少整數 x 合法：從 init 開始，依序把 x 的每一位（不含前導零）
    餵給 step(state, d)，最後由 accept(state) 判斷。step 回傳 None 代表這個前綴已經不合法。"""
    if N <= 0:
        return 0
    s = str(N)

    @cache
    def go(pos: int, state, tight: bool, started: bool) -> int:
        if pos == len(s):
            return int(started and accept(state))   # 全是前導零的「數」是 0，不計
        limit = int(s[pos]) if tight else 9
        total = 0
        for d in range(limit + 1):
            nt = tight and d == limit               # 這一位也貼著 N，下一位繼續受限
            if not started and d == 0:
                total += go(pos + 1, state, nt, False)  # 仍是前導零：狀態不變
            else:
                ns = step(state, d)
                if ns is not None:
                    total += go(pos + 1, ns, nt, True)
        return total

    return go(0, init, True, False)


def count_digit_sum_mod(N: int, k: int) -> int:
    """[1, N] 中位數和可被 k 整除的整數個數。"""
    return digit_dp(N, 0, lambda r, d: (r + d) % k, lambda r: r == 0)


def count_no_adjacent_equal(N: int) -> int:
    """[1, N] 中相鄰位數都不相同的整數個數。state = 上一位數字。"""
    return digit_dp(N, -1, lambda last, d: None if d == last else d, lambda last: True)


def in_range(L: int, R: int, f) -> int:
    return f(R) - f(L - 1)


assert count_digit_sum_mod(20, 3) == 6            # 3 6 9 12 15 18
assert count_no_adjacent_equal(12) == 11          # 只有 11 不合法
assert count_no_adjacent_equal(0) == 0
assert in_range(100, 120, count_no_adjacent_equal) == sum(
    1 for x in range(100, 121) if all(a != b for a, b in zip(str(x), str(x)[1:])))
for N in list(range(0, 300)) + [999, 1000, 1001, 4321]:
    assert count_digit_sum_mod(N, 7) == sum(1 for x in range(1, N + 1) if sum(map(int, str(x))) % 7 == 0)
    assert count_no_adjacent_equal(N) == sum(
        1 for x in range(1, N + 1) if all(a != b for a, b in zip(str(x), str(x)[1:])))
assert count_digit_sum_mod(10**18, 9) == 10**18 // 9   # 位數和 ≡ x (mod 9)，大 N 也只有幾千個狀態
print("all tests passed")
```

**tight 怎麼轉移**。只有當這一位也填了上限（`d == limit`）而且前面一直貼著 N（`tight`）時，下一位才繼續受限。一旦某一位填得比 N 小，後面就永遠自由。所以整個遞迴中，tight 為 True 的狀態只有一條路徑（每個 pos 一個），大部分計算都發生在 tight 為 False 的狀態，而那些狀態和 N 無關，可以被大量共用。

**started 為什麼不可少**。看 `count_no_adjacent_equal(1000)`：如果把前導零當成真的數字，12 會被讀成 `0 0 1 2`，前兩位都是 0，被誤判為「相鄰相同」而不計入。started 的作用是讓前導零不進入 state：還沒開始時填 0，state 保持 init（這裡是 -1，代表「沒有上一位」），直到第一個非零數字才開始真正的轉移。另一個作用是排除 0 本身：所有位數都是前導零的「數」就是 0，題目問的是 [1, N]，終點時 `started` 為 False 要回傳 0。有些題目的 state 對前導零不敏感（例如位數和，前導零不改變和），這時 started 只用來排除 0；但養成一律帶著 started 的習慣，能避免核心題 5 F1、難題 4 F1 這類「數字集合包含 0」的錯誤。

```text
count_no_adjacent_equal(12)：s = "12"
go(pos=0, state=-1, tight=T, started=F)，limit = s[0] = 1
├─ d=0：前導零 → go(1, -1, tight=F, started=F)，limit = 9
│        ├─ d=0：前導零 → go(2, -1, F, F) → 結束但沒開始 → 0      （這是 0 本身）
│        └─ d=1..9：開始 → go(2, d, F, T) → 1 個 × 9              （1 到 9）
│        小計 9
└─ d=1：開始，tight 延續 → go(1, 1, tight=T, started=T)，limit = s[1] = 2
         ├─ d=0：state 1→0 → 10 合法                1
         ├─ d=1：和上一位相同 → step 回傳 None       0   （11 被排除）
         └─ d=2：state 1→2，tight 延續 → 12 合法     1
         小計 2
總計 9 + 2 = 11
```

**複雜度**。狀態數是 len(s) × |state| × 2 × 2，每個狀態試最多 10 個數字。位數和 mod k 的版本，N = 10¹⁸ 時只有 19 × k × 4 個狀態；已用數字集合的版本（難題 5）是 10 × 1024 × 4 個，都非常小。要算區間 [L, R]，用 `f(R) − f(L − 1)`，這和 prefix sum（第 7 章）是同一個想法。

**另一種寫法：只對「不 tight」的狀態記憶化**。很多教材的模板把 tight 從快取的 key 拿掉，只在 `not tight` 時查表，並讓同一份快取在多次查詢間共用（例如同時算 f(R) 和 f(L − 1)）。這在多組查詢時比較快，但寫法稍長；面試時用上面把 tight 放進 key 的版本最不容易錯，複雜度也只差常數。

## 24.6 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 樹 DP 用遞迴處理 10⁴ 以上的鏈 | `RecursionError`，或在其他語言中 stack overflow | 用 BFS 順序倒著走當作後序；或確認深度有保證再用遞迴 |
| 樹 DP 只回傳一個數字 | 337 這類題目算錯：父節點不知道子節點「選了」還是「沒選」 | 先問父節點需要知道什麼，每種情況一個狀態，回傳 tuple |
| rerooting 用減法撤銷 max | 某些節點的答案多算了經過自己子樹的路徑 | 合併是 max／min 時用 top-2 或前綴／後綴，加總才用減法 |
| 對所有 mask 做 O(2ⁿ) 的子集合迴圈（`for sub in range(1 << n): if sub & mask == sub`） | 複雜度變成 4ⁿ，n = 14 時 2.7 × 10⁸ | 用 `sub = (sub - 1) & mask` 只走真正的子集合，總共 3ⁿ |
| 子集合枚舉忘了在 sub = 0 時停止 | 無窮迴圈 | `if sub == 0: break` 放在更新之前；需要空集合時先處理再停 |
| 運算子優先序 | `1 << i - 1` 是 `1 << (i - 1)` 而不是 `(1 << i) - 1`；在 C++／Java 中 `mask & 1 << i == 0` 會被解讀成 `mask & ((1 << i) == 0)` | 不確定就加括號；判斷位元用 `mask >> i & 1`，全集寫 `(1 << n) - 1` |
| bitmask 的位元編號和題目的 1-indexed 混用 | 526 這類題目差一位，答案偏移 | 統一用 `1 << (v - 1)` 代表數值 v，或把題目先轉成 0-indexed |
| 數位 DP 忘了 started | 位數集合包含 0、相鄰限制、相異數字等題目錯誤地把前導零算進去 | 前導零階段不呼叫 step，state 保持初始值 |
| tight 的轉移寫成 `tight or d == limit` | 前綴已經比 N 小卻又被限制，少算很多數 | 只有 `tight and d == limit` 才延續 |
| 區間 [L, R] 寫成 `f(R) − f(L)` | 少算了 L 本身 | `f(R) − f(L − 1)`，並確認 `f(0)` 回傳 0 |
| 數位 DP 把 N 本身漏掉或多算 0 | 答案差 1 | 終點時 `started` 才算一個數；tight 一路到底的路徑就是 N 本身，要計入 |

## 核心題 1｜337. House Robber III｜Medium

### 題目

一個小偷發現一個社區的房子排成一棵二元樹：根節點是入口，每個節點是一間房子，節點的值是屋內的金額（非負整數）。如果同一晚有**兩間直接相連的房子**（父子關係）都被闖入，警報就會響。請回傳不觸發警報的前提下，小偷最多能偷到多少錢。限制：節點數在 1 到 10⁴ 之間，`0 <= val <= 10⁴`。輸入以 LeetCode 的層序串列表示，`None` 代表空子樹。

- 範例 1：`[3, 2, 3, None, 3, None, 1]`，回傳 `7`。偷根的 3、左子節點的右孩子 3、右子節點的右孩子 1。
- 範例 2：`[3, 4, 5, 1, 3, None, 1]`，回傳 `9`。偷 4 和 5（兩者都是根的孩子，彼此不相連）。
- 範例 3（邊界）：`[5]`，回傳 `5`；空樹回傳 `0`。
- 範例 4（邊界）：一條往左偏的鏈 `4 → 1 → 2 → 3`，回傳 `7`（偷 4 和 3）。注意「隔一層偷」不一定最好：這裡偷第 1、3 層是 4 + 2 = 6，偷第 2、4 層是 1 + 3 = 4，最佳解 4 + 3 跳過了兩層。

### 思路

暴力解是對每個節點決定偷或不偷，檢查是否有相鄰的兩間都被偷，O(2ⁿ · n)。稍微聰明一點的遞迴是：「以 node 為根的最佳值 = max(偷 node 加上四個孫子子樹的最佳值, 不偷 node 加上兩個孩子子樹的最佳值)」。這個式子是對的，但每個節點會被祖父和父親各呼叫一次，子問題大量重複；加上以節點為 key 的 memo 後是 O(n)，不過要維護一個 hash map，而且「孫子」的寫法很容易漏掉空節點的判斷。

真正的瓶頸是：父節點在做決定時，需要知道「孩子被偷時子樹最多多少」和「孩子沒被偷時子樹最多多少」兩個數字，而只回傳一個數字的遞迴把這兩者混在一起了，只好再往下看到孫子。解法是讓每個節點**同時回傳兩個狀態** `(take, skip)`：`take` 是「偷這個節點」時子樹的最佳值，`skip` 是「不偷這個節點」時的最佳值。這就是 24.3 節後序回傳狀態的標準形。

轉移式直接由題目的限制寫出：偷了 node，兩個孩子都不能偷，所以 `take = node.val + left.skip + right.skip`；不偷 node，兩個孩子各自想偷就偷、不偷就不偷，取各自較好的那個，所以 `skip = max(left.take, left.skip) + max(right.take, right.skip)`。空節點回傳 `(0, 0)`。答案是根的 `max(take, skip)`。因為左右子樹沒有任何共用的節點，兩邊的最佳值可以直接相加，這是樹 DP 成立的根本原因。

```text
範例 2：[3, 4, 5, 1, 3, None, 1]

            3
          /   \
         4     5
        / \     \
       1   3     1

後序計算（take, skip）：
節點      take                     skip                              回傳
1（左左）  1 + 0 + 0 = 1            0                                 (1, 0)
3（左右）  3 + 0 + 0 = 3            0                                 (3, 0)
4         4 + 0 + 0 = 4            max(1,0) + max(3,0) = 4           (4, 4)
1（右右）  1                        0                                 (1, 0)
5         5 + 0 + 0 = 5            (空)0 + max(1,0) = 1              (5, 1)
3（根）    3 + 4 + 1 = 8            max(4,4) + max(5,1) = 9           (8, 9)

答案 = max(8, 9) = 9
```

節點 4 的兩個狀態剛好相同：偷 4 是 4，不偷 4 而偷兩個孩子 1 + 3 也是 4。根的 `skip = 9` 代表「不偷根，左子樹取 4、右子樹取偷 5 的 5」。如果根改成偷，兩個孩子都不能偷，只剩 `4.skip + 5.skip = 4 + 1`，加上 3 只有 8。整個過程每個節點只算一次，而且每一步只看兩個孩子的 tuple。

### 解法

```python
import random
from itertools import combinations


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def build(values):
    """由 LeetCode 式的層序串列（None 表示空）建樹。"""
    if not values or values[0] is None:
        return None
    nodes = [None if v is None else TreeNode(v) for v in values]
    kids = iter(nodes[1:])
    for node in nodes:
        if node:
            node.left, node.right = next(kids, None), next(kids, None)
    return nodes[0]


def rob(root: TreeNode | None) -> int:
    def dfs(node):                      # 回傳 (選 node 的最佳值, 不選 node 的最佳值)
        if node is None:
            return 0, 0
        l_take, l_skip = dfs(node.left)
        r_take, r_skip = dfs(node.right)
        take = node.val + l_skip + r_skip            # 選了自己，孩子都不能選
        skip = max(l_take, l_skip) + max(r_take, r_skip)  # 不選自己，孩子各自取最好
        return take, skip

    return max(dfs(root))


def rob_iterative(root: TreeNode | None) -> int:
    """不用遞迴：BFS 順序倒著處理就是後序，適合很深的樹。"""
    if root is None:
        return 0
    order = [root]
    for node in order:
        order.extend(c for c in (node.left, node.right) if c)
    best = {None: (0, 0)}
    for node in reversed(order):
        lt, ls = best[node.left]
        rt, rs = best[node.right]
        best[node] = (node.val + ls + rs, max(lt, ls) + max(rt, rs))
    return max(best[root])


def brute(root):
    nodes, edges = [], []
    stack = [(root, None)]
    while stack:
        node, par = stack.pop()
        if node:
            nodes.append(node)
            if par is not None:
                edges.append((par, node))
            stack += [(node.left, node), (node.right, node)]
    best = 0
    for r in range(len(nodes) + 1):
        for pick in combinations(nodes, r):
            s = set(map(id, pick))
            if all(not (id(a) in s and id(b) in s) for a, b in edges):
                best = max(best, sum(x.val for x in pick))
    return best


assert rob(build([3, 2, 3, None, 3, None, 1])) == 7
assert rob(build([3, 4, 5, 1, 3, None, 1])) == 9
assert rob(build([])) == 0
assert rob(build([5])) == 5
assert rob(build([4, 1, None, 2, None, 3])) == 7          # 左偏的鏈：4 + 3
chain = TreeNode(1)
cur = chain
for i in range(2, 20001):                                  # 深度 2 萬的鏈，遞迴會爆
    cur.right = TreeNode(i)
    cur = cur.right
assert rob_iterative(chain) == sum(range(2, 20001, 2))     # 隔一個選，選偶數比較大
for _ in range(300):
    vals = [random.choice([None, *range(10)]) for _ in range(random.randint(0, 10))]
    t = build(vals)
    assert rob(t) == rob_iterative(t) == brute(t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每個節點恰好處理一次，每次 O(1)。空間 O(h)，h 是樹高，用於遞迴堆疊；最差（鏈狀）是 O(n)。迭代版本用 O(n) 的 `order` 與 `best`，但不受 Python 遞迴深度限制，題目上限 10⁴ 個節點時，一條鏈就會超過預設的 1000 層，所以面試時要主動提到這一點，或至少說「可以用 `sys.setrecursionlimit` 或改成迭代」。邊界情況：空樹回傳 0；只有一個節點時 `take = val`、`skip = 0`；金額可以是 0，不影響轉移；最佳解不一定是「隔層偷」（範例 4），這正是只按層數交錯的貪婪會錯的原因。

### Follow-up

> [!question]- F1. 如果要回傳被偷的房子是哪些呢？
> 先用同樣的後序算出每個節點的 `(take, skip)` 並存起來（例如存在 dict 或節點欄位），再從根開始由上往下還原：用一個參數 `parent_taken` 表示父節點是否被偷。若 `parent_taken` 為 True，這個節點只能不偷；否則比較 `take` 和 `skip`，取較大的那個（相等時任選）。決定之後把結果當作 `parent_taken` 傳給兩個孩子。還原是一次前序走訪，O(n) 時間、O(n) 空間。這是所有 DP 都適用的「先算值、再沿著最佳選擇走回去」的做法，樹 DP 的特點是還原時要把父節點的決定往下傳。

> [!question]- F2. 如果最多只能偷 k 間房子呢？
> 狀態要多一維「子樹內偷了幾間」：`take[j]`、`skip[j]` 是子樹內恰好偷 j 間時的最佳值。合併兩個孩子時，左邊偷 i 間、右邊偷 j 間，合起來偷 i + j 間，這是 max-plus 的卷積（tree knapsack，樹上背包）。
> ```python
> NEG = float("-inf")
>
> def rob_at_most_k(root, k):
>     def merge(a, b):                  # a[i] + b[j] → res[i + j]，只保留到 k
>         res = [NEG] * (k + 1)
>         for i, x in enumerate(a):
>             if x == NEG:
>                 continue
>             for j, y in enumerate(b[:k + 1 - i]):
>                 if y != NEG:
>                     res[i + j] = max(res[i + j], x + y)
>         return res
>
>     def dfs(node):                    # 回傳 (take, skip)，索引 j = 子樹內恰好偷 j 間
>         if node is None:
>             base = [0] + [NEG] * k
>             return [NEG] * (k + 1), base
>         lt, ls = dfs(node.left)
>         rt, rs = dfs(node.right)
>         both = merge(ls, rs)
>         take = [NEG] + [both[j - 1] + node.val if both[j - 1] != NEG else NEG for j in range(1, k + 1)]
>         skip = merge([max(x, y) for x, y in zip(lt, ls)], [max(x, y) for x, y in zip(rt, rs)])
>         return take, skip
>
>     take, skip = dfs(root)
>     return max(max(take), max(skip))
>
> # 樹 [3, 2, 3, null, 3, null, 1]：最多偷 3 間得 7，最多 1 間得 3
> ```
> `take[j]` 要求節點本身被偷，所以兩個孩子都只能用 `skip`；`skip` 時每個孩子可以取 `take`、`skip` 的逐項較大者。每個節點固定做 O(k²) 的合併，總共 O(n · k²)。若把陣列長度限制在 `min(子樹大小, k) + 1`，可以證明總成本是 O(n · k)：每一對「分屬左右子樹的節點」只會在它們的最低共同祖先處被合併一次，而長度上限 k 讓大子樹的合併不會超過 k² 的量級。面試中先寫出 O(n · k²) 的版本，再說出這個上界即可。

> [!question]- F3. 如果社區不是樹，而是樹再多一條邊（形成恰好一個環）呢？
> 這叫 pseudo-tree（基環樹）。找出環上任一條邊 (u, v)，把它拿掉就變回一棵樹。這條邊的限制是「u 和 v 不能同時被偷」，所以分兩種情況：強制 u 不偷（以 u 為根做樹 DP，答案取 `skip[u]`），或強制 v 不偷（以 v 為根，答案取 `skip[v]`），兩者取最大。兩種情況涵蓋了所有合法選法，因為合法選法中 u、v 至少有一個沒被偷。總時間 O(n)。這和 213（House Robber II）處理環狀陣列的手法完全相同：環狀限制拆成兩個線性（或樹狀）問題。

> [!question]- F4. 如果樹不是二元樹，而是一般的樹，以邊列表給出呢（例如公司聚會不能同時邀請直屬上司與下屬）？
> 轉移式不變，只是把「左右兩個孩子」換成「所有孩子」的加總：`take[u] = w[u] + Σ skip[c]`、`skip[u] = Σ max(take[c], skip[c])`。實作上用 24.3 節的 `max_independent_set`：先 BFS 得到父節點與順序，再倒序把每個節點的兩個值加到父節點上，O(n) 時間、O(n) 空間，不用遞迴。如果邊列表給的是有向的「上司 → 下屬」，根就是沒有上司的那個人；若有多個根（森林），對每棵樹各做一次再相加。

> [!question]- F5. 如果要計算「達到最大金額的偷法有幾種」呢？
> 每個狀態改成存一對 `(最佳值, 方法數)`。合併時：`take` 的方法數是兩個孩子 `skip` 方法數的乘積；`skip` 對每個孩子先取 `take` 與 `skip` 中較大的，若兩者相等則方法數相加，再把左右兩邊的方法數相乘。最後在根比較 `take` 與 `skip`，相等時方法數相加。仍是 O(n)，方法數可能很大，題目通常會要求對 10⁹ + 7 取模。要注意值為 0 的節點會讓「偷」與「不偷」打平，方法數因此翻倍，這是驗證程式的好測試。

## 核心題 2｜338. Counting Bits｜Easy

### 題目

給一個非負整數 n，回傳一個長度為 n + 1 的陣列 `ans`，其中 `ans[i]` 是 i 的二進位表示中 1 的個數（也叫 popcount 或 Hamming weight），i 從 0 到 n。限制：`0 <= n <= 10⁵`。題目的追問要求：能否在 O(n) 時間內完成，而且不使用語言內建的 popcount 函式。

- 範例 1：`n = 2`，回傳 `[0, 1, 1]`（0 → `0`、1 → `1`、2 → `10`）。
- 範例 2：`n = 5`，回傳 `[0, 1, 1, 2, 1, 2]`（3 → `11`、4 → `100`、5 → `101`）。
- 範例 3（邊界）：`n = 0`，回傳 `[0]`。
- 範例 4（邊界）：`ans[15] = 4`（`1111`），`ans[16] = 1`（`10000`）：跨過 2 的冪次時 1 的個數會突然掉下來。

### 思路

暴力解是對每個 i 逐位數 1 的個數：不斷 `i & 1` 再 `i >>= 1`，每個數 O(log i)，總共 O(n log n)。用 Brian Kernighan 的技巧（不斷 `i &= i − 1`，每次消掉一個 1）可以變成 O(Σ popcount(i))，平均約 (log n)/2 次，仍然不是 O(n)。

瓶頸在於每個數都從頭數起，完全沒有利用「比它小的數已經數過了」。這是 DP 的典型訊號：i 的答案能不能由某個更小的數的答案 O(1) 推出？有兩個自然的選擇。第一，**右移一位**：`i >> 1` 是把 i 的最低位丟掉，所以 i 的 1 的個數等於 `i >> 1` 的個數加上被丟掉的那一位 `i & 1`。第二，**拿掉最低位的 1**：`i & (i − 1)` 恰好比 i 少一個 1，所以 `ans[i] = ans[i & (i − 1)] + 1`。兩種情況中，被參照的數都比 i 小，所以由小到大填表即可，每格 O(1)。

這題看似和本章其他題無關，其實是 bitmask DP 最基本的零件：「一個集合的某個量，可以由拿掉一個元素後的子集合 O(1) 推出」。24.4 節的 `subset_sums` 用的就是拿掉最低位的版本，核心題 3（526）需要每個 mask 的 popcount 來知道「下一個是第幾個位置」，核心題 4（1986）需要每個 mask 的任務總和。理解這題，就是理解為什麼 bitmask DP 可以按數值由小到大填表。

```text
i    二進位    i >> 1   i & 1   ans[i] = ans[i >> 1] + (i & 1)
0    0000       -        -     0
1    0001       0        1     ans[0] + 1 = 1
2    0010       1        0     ans[1] + 0 = 1
3    0011       1        1     ans[1] + 1 = 2
4    0100       2        0     ans[2] + 0 = 1
5    0101       2        1     ans[2] + 1 = 2
6    0110       3        0     ans[3] + 0 = 2
7    0111       3        1     ans[3] + 1 = 3
8    1000       4        0     ans[4] + 0 = 1

另一種：拿掉最低位的 1
i = 6 (0110)：6 & 5 = 0110 & 0101 = 0100 = 4 → ans[6] = ans[4] + 1 = 2
i = 8 (1000)：8 & 7 = 1000 & 0111 = 0000 = 0 → ans[8] = ans[0] + 1 = 1
```

表中可以看到另一個規律：從 2ᵏ 到 2ᵏ⁺¹ − 1 這一段，答案是前一段 0 到 2ᵏ − 1 的答案逐項加 1，因為只是多了最高位的那個 1。這也可以寫成一個 DP（`ans[i] = ans[i − highbit] + 1`），三種寫法本質相同：都是「把 i 拆成一個位元加上一個更小的數」。

### 解法

```python
import random


def count_bits(n: int) -> list[int]:
    ans = [0] * (n + 1)
    for i in range(1, n + 1):
        ans[i] = ans[i >> 1] + (i & 1)      # 右移一位去掉最低位，再把最低位加回來
    return ans


def count_bits_lowbit(n: int) -> list[int]:
    ans = [0] * (n + 1)
    for i in range(1, n + 1):
        ans[i] = ans[i & (i - 1)] + 1       # 拿掉最低位的 1，剛好少一個 1
    return ans


assert count_bits(2) == [0, 1, 1]
assert count_bits(5) == [0, 1, 1, 2, 1, 2]
assert count_bits(0) == [0]
assert count_bits(16)[-1] == 1 and count_bits(15)[-1] == 4
big = 10**5
assert count_bits(big) == count_bits_lowbit(big) == [bin(i).count("1") for i in range(big + 1)]
for _ in range(100):
    n = random.randint(0, 300)
    assert count_bits(n) == [bin(i).count("1") for i in range(n + 1)]
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每個 i 只做一次右移、一次 AND、一次加法與一次查表。空間 O(n)，就是輸出陣列本身，不需要額外空間。邊界情況：n = 0 時迴圈不執行，回傳 `[0]`；`i >> 1` 在 i = 1 時是 0，查到 `ans[0] = 0`，正確；`i & (i − 1)` 在 i 是 2 的冪次時得到 0，答案為 1。Python 的整數沒有位數限制，若改用 C++／Java，n 在題目範圍內用 32 位元整數即可。

### Follow-up

> [!question]- F1. 如果 n 高達 10¹⁸，只要 0 到 n 所有數的 1 的總個數呢？
> 不能逐一列舉，改成逐位元計數。第 b 個位元在 0, 1, 2, … 中以週期 2^(b+1) 重複「2^b 個 0、2^b 個 1」。0 到 n 共有 n + 1 個數，完整的週期有 `(n + 1) // 2^(b+1)` 個，每個貢獻 2^b 個 1；剩下不足一個週期的 `r = (n + 1) % 2^(b+1)` 個數中，有 `max(0, r − 2^b)` 個在這一位是 1。對每個位元加總，O(log n)。
> ```python
> def total_bits(n):
>     total, b = 0, 0
>     while (1 << b) <= n:
>         cycle = 1 << (b + 1)
>         total += (n + 1) // cycle * (1 << b) + max(0, (n + 1) % cycle - (1 << b))
>         b += 1
>     return total
> ```
> 這是二進位版本的難題 4（233. Number of Digit One），那裡要數的是十進位中 1 的個數，用的是同一個「每一位獨立計數」的想法。

> [!question]- F2. 如果要數 [0, n] 中恰好有 k 個 1 的數有幾個呢？
> 這是二進位的數位 DP，而且可以直接用組合數。由高位往低位掃 n 的位元，維護目前已經固定的 1 的個數 `ones`：遇到 n 的第 b 位是 1 時，若讓 x 在這一位填 0，後面 b 個位元就完全自由，要再放 `k − ones` 個 1，共 C(b, k − ones) 種；然後讓 x 在這一位填 1（繼續 tight），`ones += 1`。掃完後若 `ones == k`，n 本身也算一個。時間 O(log n)。這正是 24.5 節模板中「tight 分支」與「自由分支」的拆法，只是自由分支的計數有封閉公式，不必遞迴。

> [!question]- F3. 能不能用同樣的技巧，在 O(2ⁿ) 內算出一個長度 n 的陣列所有子集合的總和？
> 可以，把「1 的個數」換成「選到的元素總和」：`sums[mask] = sums[mask & (mask − 1)] + a[最低位的 1 的索引]`，最低位索引用 `(mask & -mask).bit_length() − 1` 取得。每個 mask O(1)，總共 O(2ⁿ)，比對每個 mask 重新加總的 O(2ⁿ · n) 少了一個 n。這就是 24.4 節的 `subset_sums`，核心題 4（1986）用它預先算出每組任務的總時間，判斷能不能放進同一個 session。

> [!question]- F4. 如果要的是每個數的二進位 1 的個數的奇偶性（parity）呢？能否不用陣列、直接算單一個 64 位元數的 parity？
> 陣列版本只要把加法換成 XOR：`par[i] = par[i >> 1] ^ (i & 1)`，O(n)。單一個數則可以用「摺疊」：`x ^= x >> 32; x ^= x >> 16; x ^= x >> 8; x ^= x >> 4; x ^= x >> 2; x ^= x >> 1`，最後 `x & 1` 就是 parity，O(log w) 次運算（w 是位元數）。原理是 XOR 兩半之後，低半部每一位的 parity 等於原本兩個位置的 parity 之和，一路摺到只剩一位。需要大量查詢時，也可以先建 2¹⁶ 大小的查表，每個 64 位元數分四塊查表再 XOR。

## 核心題 3｜526. Beautiful Arrangement｜Medium

### 題目

給一個正整數 n，考慮 1 到 n 的所有排列 `perm`（位置也用 1 到 n 編號）。一個排列稱為「美麗的」，若對每個位置 i，下列兩個條件至少有一個成立：`perm[i]` 能被 i 整除，或 i 能被 `perm[i]` 整除。請回傳美麗排列的個數。限制：`1 <= n <= 15`。

- 範例 1：`n = 2`，回傳 `2`。`[1, 2]`：位置 1 放 1、位置 2 放 2，都整除；`[2, 1]`：位置 1 放 2（2 能被 1 整除），位置 2 放 1（位置編號 2 能被 1 整除）。
- 範例 2：`n = 3`，回傳 `3`：`[1, 2, 3]`、`[2, 1, 3]`、`[3, 2, 1]`。例如 `[1, 3, 2]` 不合法，因為位置 2 放 3，3 不能被 2 整除、2 也不能被 3 整除。
- 範例 3（邊界）：`n = 1`，回傳 `1`。
- 範例 4：`n = 4` 回傳 `8`；`n = 15` 回傳 `24679`。

### 思路

暴力解是列出全部 n! 個排列逐一檢查，15! ≈ 1.3 × 10¹²，不可能。Backtracking（第 19 章）邊放邊檢查、遇到不合法就剪枝，實際上快很多：每個位置能放的值通常只有幾個（位置 i 只能放 i 的倍數或因數），n = 15 時可以在時限內完成。但它的最差複雜度仍然難以估計，而且同一個「已經用掉的數字集合」會從很多條不同的路徑抵達，每次都重新展開後面的搜尋。

關鍵觀察是：**決定下一個位置能放什麼，只需要知道哪些數字已經用掉**，不需要知道它們是按什麼順序放的。因為我們由位置 1 開始依序填，用掉了幾個數字就代表填到了第幾個位置；剩下可以放的數字就是不在集合裡的那些。所以把「已用數字的集合」編成 bitmask，定義 `dp[mask]` = 用掉 mask 這些數字、填好前 `popcount(mask)` 個位置的合法方法數。這正是 24.4 節「一次加一個元素」的轉移：對每個 mask，下一個位置 `pos = popcount(mask) + 1`，嘗試每個不在 mask 裡、而且和 pos 相容的 v，把方法數加到 `dp[mask | bit(v)]`。

狀態數從 n! 降到 2ⁿ = 32768，每個狀態試 n 個值，總共約 5 × 10⁵ 次運算。為什麼可以合併？因為兩條路徑若用掉的數字集合相同，它們接下來的所有可能完全一樣，方法數只要算一次再相乘（這裡是相加到下一個狀態）。這就是 bitmask DP 相對於 backtracking 的本質優勢：backtracking 是在排列樹上展開，DP 是在 2ⁿ 個集合構成的 DAG 上累加。

```text
n = 3，位置 pos 可放的值：pos 1 → {1, 2, 3}；pos 2 → {1, 2}；pos 3 → {1, 3}
mask 由右往左是數字 1、2、3

mask   已用     pos  可放（不在 mask 且相容）   推到
000    {}       1    1, 2, 3                  dp[001] += 1, dp[010] += 1, dp[100] += 1
001    {1}      2    2                        dp[011] += 1
010    {2}      2    1                        dp[011] += 1           → dp[011] = 2
100    {3}      2    1, 2                     dp[101] += 1, dp[110] += 1
011    {1,2}    3    3                        dp[111] += 2
101    {1,3}    3    （2 和 3 互不整除）        —
110    {2,3}    3    1                        dp[111] += 1           → dp[111] = 3
```

`dp[011] = 2` 代表兩種把 {1, 2} 放進位置 1、2 的方法（`[1, 2]` 與 `[2, 1]`），它們之後只能在位置 3 放 3，所以一次就把 2 加給 `dp[111]`；backtracking 會把這個後續展開兩次。`mask = 101` 是一條死路：位置 3 只剩 2 可放，而 2 與 3 互不整除，於是 `dp[101]` 的方法數不會傳下去。

### 解法

```python
from itertools import permutations


def count_arrangement(n: int) -> int:
    full = 1 << n
    dp = [0] * full                # dp[mask]：用掉 mask 這些數、填好前 popcount(mask) 個位置的方法數
    dp[0] = 1
    for mask in range(full):
        if dp[mask] == 0:
            continue
        pos = mask.bit_count() + 1               # 下一個要填的位置（1-indexed）
        for v in range(1, n + 1):
            bit = 1 << (v - 1)
            if not mask & bit and (v % pos == 0 or pos % v == 0):
                dp[mask | bit] += dp[mask]
    return dp[full - 1]


def brute(n):
    return sum(all(p[i - 1] % i == 0 or i % p[i - 1] == 0 for i in range(1, n + 1))
               for p in permutations(range(1, n + 1)))


assert count_arrangement(1) == 1
assert count_arrangement(2) == 2
assert count_arrangement(3) == 3
assert count_arrangement(4) == 8
for n in range(1, 9):
    assert count_arrangement(n) == brute(n)
assert count_arrangement(15) == 24679
print("all tests passed")
```

### 複雜度與邊界

時間 O(2ⁿ · n)：2ⁿ 個 mask，每個試 n 個值，n = 15 時約 4.9 × 10⁵。空間 O(2ⁿ)。`if dp[mask] == 0: continue` 跳過抵達不了的狀態，實際上只會處理一部分 mask。邊界情況：n = 1 時只有 `[1]`；位元編號用 `1 << (v − 1)` 對應數值 v，若忘了減 1，n = 15 時會用到第 15 位，雖然 Python 不會出錯，但 `full − 1` 的全集就對不上；`pos` 必須是 `popcount(mask) + 1` 而不是 `popcount(mask)`，因為位置是 1-indexed。

### Follow-up

> [!question]- F1. 如果要列出所有美麗排列，而不只是計數呢？
> 這時輸出本身可能很大（n = 15 時 24679 個排列），計數 DP 幫不上忙，要用 backtracking 逐一產生。做法是對每個位置先預先算出相容的值清單，DFS 時用 bitmask 記錄已用的值；可以再用計數 DP 的結果剪枝：先由後往前算出 `ways[mask]`（已用 mask 時剩下的完成方式數），DFS 時只走 `ways[新 mask] > 0` 的分支，保證每條路徑都會走到一個解，總時間 O(輸出量 × n)，不會在死路上浪費時間。

> [!question]- F2. 為什麼很多 backtracking 解法從最後一個位置往前填，會比較快？
> 位置越大，相容的值越少：位置 1 能放任何數，位置 13（質數）只能放 1 和 13。從大位置開始填，搜尋樹的上層分支數少，衝突也更早出現，剪枝發生在樹的頂端，能砍掉的子樹更大。這和「最受限的變數先決定」（most constrained variable first）是同一個 heuristic，在數獨（第 19 章難題 2）中也常用。但這只影響 backtracking 的常數；bitmask DP 的 O(2ⁿ · n) 和填寫順序無關。

> [!question]- F3. 如果要回傳字典序第 k 小的美麗排列呢？
> 先由大到小的 mask 算出 `ways[mask]`：`ways[全集] = 1`，`ways[mask] = Σ ways[mask | bit(v)]`，v 是不在 mask 中、與 `popcount(mask) + 1` 相容的值。接著從位置 1 開始，依序嘗試 v = 1, 2, …：若 `k <= ways[mask | bit(v)]`，就把 v 放在這個位置並往下一個位置；否則 `k -= ways[mask | bit(v)]`，試下一個 v。若一開始 `k > ways[0]` 就回傳空。預處理 O(2ⁿ · n)，建構 O(n²)。這是「用計數 DP 做字典序第 k 個」的通用手法，第 28 章難題 3（60. Permutation Sequence）是沒有限制、計數有公式的版本。

> [!question]- F4. 如果相容條件換成任意的「位置 i 可以放哪些值」的表格呢？
> DP 完全不變，只是把整除判斷換成查表 `allowed[pos][v]`，仍是 O(2ⁿ · n)。這個問題等價於「計算一個二分圖的完美匹配數」，也就是 0/1 矩陣的 permanent（積和式），在一般情況下是 #P-hard，不存在已知的多項式演算法，所以指數級的 bitmask DP（或 Ryser 公式，同樣 O(2ⁿ · n)）就是標準解法。面試中說出這個連結，能解釋為什麼題目把 n 限制在 15。

> [!question]- F5. 如果 n 增加到 20 呢？
> 2²⁰ · 20 ≈ 2 × 10⁷ 次運算，C++／Java 一秒內可完成，Python 大約需要十幾秒，要靠常數優化：預先算好每個位置的相容值 bitmask `ok[pos]`，轉移時只枚舉 `ok[pos] & ~mask` 中的位元（用 `x & -x` 逐一取出最低位），跳過不相容的值；並且只處理 `dp[mask] > 0` 的狀態。相容值平均只有幾個，實際運算量會降到數百萬。記憶體方面 2²⁰ 個整數約 8 MB（用 `array` 或 list 皆可）。再大到 n = 25 以上，就要換成 meet-in-the-middle 或其他結構觀察，單純的 2ⁿ 已經不夠。

## 核心題 4｜1986. Minimum Number of Work Sessions to Finish the Tasks｜Medium

### 題目

有 n 個任務，第 i 個需要 `tasks[i]` 小時。你以「工作時段」（session）為單位工作，每個 session 最多連續工作 `sessionTime` 小時，之後必須休息。一個任務一旦開始就必須在同一個 session 內做完；做完一個任務可以立刻開始下一個；任務可以用**任意順序**完成。請回傳完成所有任務所需的最少 session 數。限制：`1 <= n <= 14`，`1 <= tasks[i] <= 10`，`max(tasks) <= sessionTime <= 15`。

- 範例 1：`tasks = [1, 2, 3]`、`sessionTime = 3`，回傳 `2`：{1, 2} 一個 session、{3} 一個 session。
- 範例 2：`tasks = [3, 1, 3, 1, 1]`、`sessionTime = 8`，回傳 `2`：{3, 3, 1, 1} 與 {1}。
- 範例 3：`tasks = [4, 3, 3, 2, 2, 2]`、`sessionTime = 8`，回傳 `2`：{4, 2, 2} 與 {3, 3, 2}，總時數 16 剛好塞滿兩個 session。
- 範例 4（邊界）：`tasks = [1, 2, 3, 4, 5]`、`sessionTime = 15`，回傳 `1`；所有任務都等於 `sessionTime` 時，回傳 n。

### 思路

這題就是 bin packing（裝箱問題）：把物品放進容量固定的箱子，最小化箱子數。它是 NP-hard，沒有已知的多項式解，所以 n ≤ 14 的限制是在告訴你：接受指數級，但要比 n! 或 nⁿ 好。暴力解是把每個任務指派到某個 session，最多 nⁿ 種；或枚舉任務的所有順序再依序塞，n! ≈ 8.7 × 10¹⁰。直覺的貪婪「由大到小，放進第一個放得下的 session」（First Fit Decreasing）在範例 3 會失敗：4 + 3 = 7 之後，第二個 3 只能開新的 session；第一個 2 放不進 7（會變成 9），只好放進 3 變成 5，第二個 2 讓它變成 7，第三個 2 兩個 session 都放不下，只能開第三個，但最佳解只要兩個。

**做法一：一次加一個任務，狀態是（session 數, 目前 session 的負載）**。把任務依某個順序一個一個放，每個任務要嘛塞進目前這個 session（如果放得下），要嘛開一個新的 session。後面的決策只需要知道「哪些任務已經做完」和「目前 session 用了多少時間」。關鍵的觀察是：對同一個已完成集合 mask，`(session 數, 負載)` 字典序越小越好。若 session 數較少，就算負載較大，也可以「立刻開一個新 session」變成 `(c + 1, 0)`，仍然不比 session 數更多的狀態差；session 數相同時，負載越小顯然越好。所以每個 mask 只需要保留字典序最小的那一對，`dp[mask]` 是一對數字而不是一張表，總共 O(2ⁿ · n)。

為什麼這樣能找到最佳解？取一個最佳分組 S₁, …, Sₖ，按「S₁ 的任務、S₂ 的任務……」的順序把任務加入，DP 中一定有一條路徑照這個順序走。沿著固定順序「放得下就放、放不下就開新的」是連續切段的貪婪，第 8 章核心題 5（1011）證明過它使用的段數最少，而 S₁…Sₖ 本身就是一種切成 k 段的方式，所以這條路徑最多用 k 個 session。DP 對所有順序取最小值，答案不會超過 k。

**做法二：一次加一整個 session，枚舉子集合**。先用核心題 2 的技巧算出每個任務集合的總時數 `total[sub]`，`total[sub] <= sessionTime` 的 sub 就是一個合法的 session。`dp[mask] = min(dp[mask ^ sub] + 1)`，sub 走過 mask 中所有合法的子集合。為了避免同一種分組被以不同順序重複考慮，固定「最後一組一定包含 mask 中編號最小的任務」，只枚舉剩下部分的子集合。複雜度 O(3ⁿ)，n = 14 時約 4.8 × 10⁶（固定最低位後再減半）。做法二比較慢，但它不依賴「字典序最小就是最好」這種特殊的支配關係，限制改變時（F3）更容易推廣。

```text
做法一，tasks = [1, 2, 3]，sessionTime = 3（mask 由右往左是任務 0、1、2）
dp[000] = (1, 0)
mask  dp       加入任務           結果                         更新
000   (1,0)    t0=1 → (1,1)      t1=2 → (1,2)    t2=3 → (1,3)   dp[001], dp[010], dp[100]
001   (1,1)    t1=2 → 1+2=3 ≤ 3  → (1,3)                         dp[011] = (1,3)
               t2=3 → 1+3 > 3    → 開新的 (2,3)                  dp[101] = (2,3)
010   (1,2)    t0=1 → (1,3)                                      dp[011] 維持 (1,3)
               t2=3 → (2,3)                                      dp[110] = (2,3)
011   (1,3)    t2=3 → (2,3)                                      dp[111] = (2,3)
100   (1,3)    t0=1 → (2,1)  比 (2,3) 好                         dp[101] = (2,1)
               t1=2 → (2,2)  比 (2,3) 好                         dp[110] = (2,2)
101   (2,1)    t1=2 → (2,3)                                      dp[111] 維持 (2,3)
110   (2,2)    t0=1 → (2,3)                                      dp[111] 維持 (2,3)
答案 dp[111] 的 session 數 = 2
```

注意 `dp[101]` 先被 `001` 更新成 `(2, 3)`（先做 1 再做 3，3 塞不下只好開新的），後來被 `100` 改成 `(2, 1)`（先做 3 占滿一個 session，再開新的做 1）。兩者 session 數相同，但後者負載較小，之後還能再塞 2 小時。這就是「同一個集合、不同順序」需要用支配關係取捨的地方。

### 解法

```python
import random


def min_sessions(tasks: list[int], session_time: int) -> int:
    """O(2ⁿ · n)：dp[mask] = (已開的 session 數, 最後一個 session 已用的時間)，取字典序最小。"""
    n = len(tasks)
    full = 1 << n
    INF = (n + 1, 0)
    dp = [INF] * full
    dp[0] = (1, 0)                              # 開著一個空的 session
    for mask in range(full):
        cnt, load = dp[mask]
        if cnt > n:
            continue
        for i in range(n):
            if mask >> i & 1:
                continue
            t = tasks[i]
            nxt = (cnt, load + t) if load + t <= session_time else (cnt + 1, t)
            if nxt < dp[mask | 1 << i]:
                dp[mask | 1 << i] = nxt
    return dp[full - 1][0]


def min_sessions_submask(tasks: list[int], session_time: int) -> int:
    """O(3ⁿ)：dp[mask] = min(dp[mask ^ sub] + 1)，sub 是一個裝得進單一 session 的子集合。"""
    n = len(tasks)
    full = 1 << n
    total = [0] * full
    for mask in range(1, full):
        low = mask & -mask
        total[mask] = total[mask ^ low] + tasks[low.bit_length() - 1]
    dp = [0] + [n] * (full - 1)
    for mask in range(1, full):
        low = mask & -mask                      # 最後一組固定包含最低位的任務，避免重複枚舉
        rest = mask ^ low
        sub = rest
        while True:
            group = sub | low
            if total[group] <= session_time and dp[mask ^ group] + 1 < dp[mask]:
                dp[mask] = dp[mask ^ group] + 1
            if sub == 0:
                break
            sub = (sub - 1) & rest
    return dp[full - 1]


def brute(tasks, T):
    best = len(tasks)

    def place(i, loads):
        nonlocal best
        if len(loads) >= best:
            return
        if i == len(tasks):
            best = len(loads)
            return
        for j in range(len(loads)):
            if loads[j] + tasks[i] <= T:
                loads[j] += tasks[i]
                place(i + 1, loads)
                loads[j] -= tasks[i]
        loads.append(tasks[i])
        place(i + 1, loads)
        loads.pop()

    place(0, [])
    return best


assert min_sessions([1, 2, 3], 3) == 2
assert min_sessions([3, 1, 3, 1, 1], 8) == 2
assert min_sessions([1, 2, 3, 4, 5], 15) == 1
assert min_sessions([5], 5) == 1
assert min_sessions([4, 3, 3, 2, 2, 2], 8) == 2        # 4+2+2、3+3+2；大的先放的貪婪要 3 個
assert min_sessions_submask([4, 3, 3, 2, 2, 2], 8) == 2
assert min_sessions([10] * 14, 10) == 14               # 每個任務各占一個 session
for _ in range(300):
    n = random.randint(1, 8)
    T = random.randint(10, 15)
    ts = [random.randint(1, 10) for _ in range(n)]
    assert min_sessions(ts, T) == min_sessions_submask(ts, T) == brute(ts, T)
big = [random.randint(1, 10) for _ in range(14)]
assert min_sessions(big, 15) == min_sessions_submask(big, 15)   # n = 14 的最大規模
print("all tests passed")
```

### 複雜度與邊界

做法一：時間 O(2ⁿ · n)，n = 14 時約 2.3 × 10⁵ 次轉移；空間 O(2ⁿ)。做法二：時間 O(3ⁿ)（固定最低位後約 3ⁿ / 2），預先計算 `total` 是 O(2ⁿ)；空間 O(2ⁿ)。邊界情況：題目保證 `max(tasks) <= sessionTime`，所以每個任務單獨一個 session 一定可行，答案最多是 n，`INF` 設成 `(n + 1, 0)` 足夠；若沒有這個保證，要先檢查並回傳 -1，否則做法一會把放不下的任務放進新的 session 卻沒發現超時。`dp[0] = (1, 0)` 表示「開著一個空 session」，若只有零個任務，答案應為 0，這題 n ≥ 1 所以不必特判。

### Follow-up

> [!question]- F1. 如果要輸出每個 session 做了哪些任務呢？
> 做法二最直接：更新 `dp[mask]` 時同時記下使用的那一組 `choice[mask] = group`。最後從全集開始，不斷取出 `choice[mask]` 作為一個 session，再令 `mask ^= choice[mask]`，直到 mask 為 0。額外空間 O(2ⁿ)，還原 O(答案)。做法一也可以記錄每個 mask 的前驅（是從哪個 mask 加入哪個任務），還原出完整的加入順序，再依序切出 session。

> [!question]- F2. 如果 session 數固定為 k，要最小化最長的那個 session 呢（1723. Find Minimum Time to Finish All Jobs）？
> 這是同一個子集合結構，換一個目標。令 `f[j][mask]` 為用 j 個工人做完 mask 時最長工時的最小值，`f[j][mask] = min over sub ⊆ mask of max(f[j − 1][mask ^ sub], total[sub])`，時間 O(k · 3ⁿ)。另一種做法是對答案二分（第 8 章）：給定上限 X，問「每組總和 ≤ X 時最少要幾組」，這正好是本題，用做法一 O(2ⁿ · n) 判斷是否 ≤ k（二分的下界要取 max(jobs)，否則做法一會把放不下的單一任務硬塞進新的 session），總共 O(2ⁿ · n · log(Σ tasks))，通常更快。

> [!question]- F3. 如果每個 session 除了時間上限，最多只能做 c 個任務呢？
> 做法一的支配關係失效了：狀態要變成 (session 數, 負載, 任務數)，而 (2, 3, 2) 和 (2, 5, 1)（前者負載小但已用掉較多任務名額，後者相反）誰比較好取決於後面的任務，沒有全序可比，不能只保留一個。做法二完全不受影響，只要把合法 session 的條件改成 `total[sub] <= sessionTime and sub.bit_count() <= c`，仍是 O(3ⁿ)。這是兩種做法最重要的差別：做法一靠一個特殊的支配關係壓縮狀態，做法二只要求「一組合不合法」可以獨立判斷，適用範圍更廣。

> [!question]- F4. 為什麼不能用貪婪？能不能先排序再 DP 來加速？
> 範例 3 已經顯示 First Fit Decreasing 會多用一個 session。更根本的原因是 bin packing 是 NP-hard，任何多項式時間的貪婪都有反例（FFD 保證不超過最佳解的約 11/9 倍加一個常數，但不保證最佳）。排序本身不會改變 DP 的複雜度，但能幫助 backtracking 剪枝：由大到小放、相同大小的任務只嘗試一種放法、已經嘗試過的「相同負載的 session」不再重試，這是第 19 章難題 4（698. Partition to K Equal Sum Subsets）的手法，面試中可以作為 DP 之外的另一種解法提出。

> [!question]- F5. 如果 n 增加到 20 呢？
> 做法二的 3²⁰ ≈ 3.5 × 10⁹ 已經不可行；做法一的 2²⁰ · 20 ≈ 2 × 10⁷ 在 C++ 中很快，Python 約需數秒到十幾秒。可以加兩個優化：只處理可抵達的 mask（`dp[mask]` 不是 INF），以及用 `~mask & (full − 1)` 配合 `x & -x` 只枚舉沒做的任務。另一個角度是先用總時數算出下界 ⌈Σ tasks / sessionTime⌉，再從下界開始對 k 做「能否用 k 個 session」的 backtracking 判斷，實務上常常在下界就成功。

## 核心題 5｜902. Numbers At Most N Given Digit Set｜Hard

### 題目

給一個由 `'1'` 到 `'9'` 組成、由小到大排序且不重複的字元陣列 `digits`，以及正整數 n。你可以任意次數地使用 `digits` 中的數字（每個數字可重複使用）寫出正整數，例如 `digits = ["1", "3", "5"]` 時可以寫出 13、551、1351315。請回傳能寫出的正整數中，有多少個 ≤ n。限制：`1 <= len(digits) <= 9`，`1 <= n <= 10⁹`。

- 範例 1：`digits = ["1", "3", "5", "7"]`、`n = 100`，回傳 `20`：一位數 4 個（1、3、5、7），兩位數 16 個（11 到 77），三位數最小是 111 > 100。
- 範例 2：`digits = ["1", "4", "9"]`、`n = 1000000000`，回傳 `29523`：長度 1 到 9 的都可以，共 3 + 3² + … + 3⁹ = 29523；十位數最小是 1111111111 > n。
- 範例 3（邊界）：`digits = ["7"]`、`n = 8`，回傳 `1`；`n = 7` 時也是 `1`（n 本身算進去）；`n = 6` 時是 `0`。
- 範例 4：`digits = ["3", "4", "8"]`、`n = 4`，回傳 `2`（3 和 4）。

### 思路

暴力解是枚舉所有能寫出的數，再和 n 比較。長度 L 的數有 kᴸ 個（k = `len(digits)`），n = 10⁹ 時最多 9⁹ ≈ 3.9 × 10⁸ 個，太慢；或者從 1 到 n 逐一檢查每個數的位數是否都在 digits 中，O(n log n)，同樣太慢。瓶頸在於這兩種做法都一個一個地處理數字，但「≤ n」這個條件其實只取決於數字的前綴：一旦某一位比 n 的那一位小，後面每一位都可以自由選，那些數字可以用一個乘法一次算完。

這就是 24.5 節的數位 DP。把能寫出的數分成兩類。**比 n 短的數**：一定小於 n，長度 L 的有 kᴸ 個，對 L = 1 … len(n) − 1 加總。**和 n 一樣長的數**：由左到右逐位比較。在第 i 位，若我們填一個比 `s[i]` 小的數字，後面的 `len − 1 − i` 位就完全自由，貢獻 `(比 s[i] 小的數字個數) × k^(len − 1 − i)`；若填和 `s[i]` 相同的數字，就繼續貼著 n 往下一位（這就是 tight 狀態）；若 `s[i]` 根本不在 digits 中，就不可能再貼著走，結束。若每一位都能貼著走到底，n 本身也算一個。

這裡不需要 started 旗標的原因是：digits 不含 0，所以「比 n 短的數」可以單獨用公式處理，不會和前導零混淆。用模板寫的時候，started 的作用就是「這一位可以選擇繼續留白」，留白代表數字更短。下面的解法同時給出公式版與模板版，兩者等價：公式版直接把模板中「不 tight 的分支」用 k 的冪次算出來。

```text
digits = [1, 3, 5, 7]（k = 4），n = 5372，s = "5372"

比 n 短的數：k¹ + k² + k³ = 4 + 16 + 64 = 84

和 n 等長，逐位貼著 n：
i  s[i]  比 s[i] 小的 digits   貢獻（後面 3-i 位自由）     s[i] 在 digits 中？
0   5    {1, 3}      → 2       2 × 4³ = 128              是，繼續貼著
1   3    {1}         → 1       1 × 4² = 16               是，繼續貼著
2   7    {1, 3, 5}   → 3       3 × 4¹ = 12               是，繼續貼著
3   2    {1}         → 1       1 × 4⁰ = 1                否 → 結束（5372 本身寫不出來）

總計 84 + 128 + 16 + 12 + 1 = 241
```

第 0 位填 1 或 3 時，數字已經小於 5000，後面三位每一位都有 4 種選擇，所以是 2 × 64。第 0 位填 5 就必須繼續比第 1 位，依此類推。第 3 位 `s[3] = 2` 不在 digits 中，代表沒有任何能寫出的數和 5372 前三位相同而且第四位等於 2，tight 路徑在這裡中斷，n 本身不計入。

### 解法

```python
import random
from bisect import bisect_left
from functools import cache
from itertools import product


def at_most_n_given_digit_set(digits: list[str], n: int) -> int:
    s = str(n)
    L, k = len(s), len(digits)
    total = sum(k ** length for length in range(1, L))   # 比 n 短的數：每一位自由選
    for i, ch in enumerate(s):                            # 和 n 等長：逐位貼著 n 走
        smaller = bisect_left(digits, ch)                 # 這一位填比 s[i] 小的數字
        total += smaller * k ** (L - 1 - i)               # 之後的 L-1-i 位自由
        if ch not in digits:                              # 無法再貼著 n 走下去
            return total
    return total + 1                                      # 每一位都能貼著走：n 本身也算


def at_most_n_digit_dp(digits: list[str], n: int) -> int:
    """24.5 節模板的寫法：state 不需要，只要 tight 與 started。"""
    s = str(n)
    allowed = [int(d) for d in digits]

    @cache
    def go(pos: int, tight: bool, started: bool) -> int:
        if pos == len(s):
            return int(started)
        limit = int(s[pos]) if tight else 9
        total = 0
        if not started:                                   # 這一位繼續留白（前導零）
            total += go(pos + 1, False, False)
        for d in allowed:
            if d > limit:
                break
            total += go(pos + 1, tight and d == limit, True)
        return total

    return go(0, True, False)


def brute(digits, n):
    count = 0
    for length in range(1, len(str(n)) + 1):
        for combo in product(digits, repeat=length):
            count += int("".join(combo)) <= n
    return count


assert at_most_n_given_digit_set(["1", "3", "5", "7"], 100) == 20
assert at_most_n_given_digit_set(["1", "4", "9"], 1000000000) == 29523
assert at_most_n_given_digit_set(["7"], 8) == 1
assert at_most_n_given_digit_set(["7"], 7) == 1
assert at_most_n_given_digit_set(["7"], 6) == 0
assert at_most_n_given_digit_set(["3", "4", "8"], 4) == 2
for _ in range(300):
    ds = sorted(random.sample("123456789", random.randint(1, 4)))
    n = random.randint(1, 5000)
    assert at_most_n_given_digit_set(ds, n) == at_most_n_digit_dp(ds, n) == brute(ds, n)
print("all tests passed")
```

### 複雜度與邊界

時間 O(L · log k)，L = len(str(n)) ≤ 10：公式版每一位做一次 `bisect_left`，`ch not in digits` 在長度 ≤ 9 的串列上是 O(k)，可以忽略。模板版的狀態是 L × 2 × 2，每個狀態試 k 個數字，O(L · k)。空間 O(L)。邊界情況：n 是一位數時「比 n 短」的部分為 0；n 的第一位比所有 digits 都小（例如 digits = ["7"]、n = 6）時，第 0 位的貢獻是 0 而且 tight 立刻中斷，答案只剩比 n 短的部分；每一位都在 digits 中時要記得 `+ 1` 把 n 本身算進去（範例 3 的 n = 7）。

### Follow-up

> [!question]- F1. 如果 digits 可以包含 0 呢？
> 公式版的「長度 L 的數有 kᴸ 個」就錯了，因為第一位不能是 0：長度 L 的數有 (k − 1) × k^(L − 1) 個（若 0 在 digits 中）。等長部分的第 0 位也不能填 0。用模板寫最不容易出錯：started 為 False 時，「填 0」代表繼續留白而不是真的寫下 0，所以在數字迴圈中跳過 `not started and d == 0` 的情況，只透過留白分支處理。這就是為什麼 24.5 節建議一律帶著 started：同一份程式不論 digits 有沒有 0 都正確，O(L · k)。

> [!question]- F2. 如果要算的是 [lo, hi] 區間內能寫出的數有幾個呢？
> 用 `f(hi) − f(lo − 1)`，其中 f(x) 是本題的答案（≤ x 的個數），並定義 f(0) = 0。lo = 1 時會呼叫 f(0)；公式版對 `"0"` 剛好回傳 0（0 不在 digits 中，tight 立刻中斷），但若 digits 允許 0（F1），模板版的 started 才能保證 0 不被計入，所以最好明確寫 `if x <= 0: return 0`。這是數位 DP 的標準用法：所有「區間計數」都轉成兩個「前綴計數」相減，和第 7 章 prefix sum 是同一個想法。時間 O(L · log k)。

> [!question]- F3. 如果要回傳能寫出的數中第 k 小的那一個呢？
> 能寫出的數依大小排序，恰好是「先依長度、同長度依字典序」，這和以 k 為基底、但數字是 1…k 而非 0…k−1 的 bijective numeration（雙射記數法）一一對應。所以第 K 個數可以這樣產生：重複執行 `K -= 1; 取 digits[K % k]; K //= k`，直到 K = 0，再把取出的數字反轉。例如 digits = ["1", "3", "5"] 時，第 4 個是 11、第 12 個是 55、第 13 個是 111。時間 O(log K ÷ log k)，即輸出的位數（k = 1 時只有 1、11、111… 這一串，第 K 個就是 K 個 1）。若還要求 ≤ n，先用本題算出總數判斷 K 是否超過即可。

> [!question]- F4. 如果每個數字最多只能使用一次呢？
> 狀態要多記「哪些數字已經用過」，這就是數位 DP 加 bitmask：`go(pos, used_mask, tight, started)`，每一位只能從 digits 中還沒用過的數字選。狀態數 L × 2ᵏ × 4，k ≤ 9 時最多 10 × 512 × 4，非常小。也可以用排列數直接算：比 n 短、長度 L 的數有 P(k, L) 種；等長部分在第 i 位，比 `s[i]` 小而且還沒用過的數字個數 × P(k − i − 1, L − i − 1)。這和難題 5（2376. Count Special Integers）是同一個結構，那題的 digits 是全部 0–9，因此還要處理首位不能是 0。

> [!question]- F5. 如果還要求寫出的數能被 m 整除呢？
> 再加一個 state：目前前綴對 m 的餘數 r。下一位填 d 時新的餘數是 `(r · 10 + d) % m`，終點時 r = 0 才計入。前導零不影響餘數（`0 · 10 + 0 = 0`），但為了排除 0 本身仍需要 started。狀態數 L × m × 4，每個試 k 個數字，O(L · m · k)。m 到 10³ 時完全沒問題。這展示了數位 DP 的擴充方式：每多一個條件，就在 state 裡多記一份「讀完前綴後，判斷那個條件所需的最少資訊」。

## 難題 1｜834. Sum of Distances in Tree｜Hard

### 題目

有一棵 n 個節點的無向樹，節點編號 0 到 n − 1，以 n − 1 條邊 `edges[i] = [a, b]` 給出。請回傳長度為 n 的陣列 `answer`，其中 `answer[i]` 是節點 i 到其他所有節點的距離（邊數）總和。限制：`1 <= n <= 3 × 10⁴`，輸入保證是一棵樹。

- 範例 1：`n = 6`、`edges = [[0, 1], [0, 2], [2, 3], [2, 4], [2, 5]]`，回傳 `[8, 12, 6, 10, 10, 10]`。例如節點 0 到 1、2、3、4、5 的距離是 1、1、2、2、2，總和 8。
- 範例 2（邊界）：`n = 1`、`edges = []`，回傳 `[0]`。
- 範例 3（邊界）：`n = 2`、`edges = [[1, 0]]`，回傳 `[1, 1]`。
- 範例 4：一條 0 − 1 − 2 − … − (n−1) 的鏈，端點的答案是 0 + 1 + … + (n − 1) = n(n − 1)/2，中點最小。

### 提示

> [!tip]- 提示 1
> 對每個節點各做一次 BFS 是 O(n²)，n = 3 × 10⁴ 時約 9 × 10⁸，太慢。先只算一個節點（例如根 0）的答案，能不能 O(n) 做到？

> [!tip]- 提示 2
> 以 0 為根，後序算出每個子樹的大小 `size[u]` 和「u 到子樹內所有節點的距離和」`down[u]`。根的答案就是 `down[0]`。接著想：如果把「根」從父節點 p 移到它的孩子 u，每個節點的距離會怎麼變？

> [!tip]- 提示 3
> 從 p 換到 u 時，u 子樹內的 `size[u]` 個節點都近了 1，其他 `n − size[u]` 個節點都遠了 1。所以 `ans[u] = ans[p] − size[u] + (n − size[u])`，前序走一遍就能算出全部。

### 詳解

**為什麼直覺做法不夠**。最直接的是從每個節點出發做一次 BFS 或 DFS，把距離加總，每次 O(n)，總共 O(n²)。也可以想成：答案等於「所有節點對的距離」按端點分配，而所有節點對有 n²/2 個，逐對計算一定是 O(n²)。要做到 O(n)，必須讓相鄰節點的答案互相利用，而不是各自從頭算。這正是 24.3 節的 rerooting：先在固定的根上算出子樹內的資訊，再沿著邊把答案從父節點「推」給子節點。

**第一遍：子樹內的資訊**。以 0 為根。`size[u]` 是 u 的子樹有幾個節點，`down[u]` 是 u 到它子樹內所有節點的距離和。後序合併時，孩子 c 的子樹裡每個節點到 u 的距離，都是它到 c 的距離再加 1，所以 c 對 `down[u]` 的貢獻是 `down[c] + size[c]`：原本的距離和，加上每個節點多走的那一步。根的子樹就是整棵樹，所以 `ans[0] = down[0]`。

**第二遍：換根公式**。假設已經知道 `ans[p]`，u 是 p 的孩子。把觀察點從 p 移到 u：u 子樹內的 `size[u]` 個節點，到 u 的距離比到 p 少 1；u 子樹外的 `n − size[u]` 個節點，要先走到 p 再走到它們，所以距離多 1。因此 `ans[u] = ans[p] − size[u] + (n − size[u])`。這個式子只用到 p 的答案和 u 的子樹大小，O(1)。按 BFS 順序（父節點先於子節點）計算，每個節點計算時它的父節點已經完成。

**為什麼這裡可以用減法**。換根時要「從 p 的答案中扣掉 u 子樹的貢獻」，而距離和是加總，可以直接撤銷；不必像 24.3 節的 eccentricity（最遠距離）那樣保留最長與次長。這題的公式甚至更簡單：連 `down[u]` 都不需要在第二遍出現，因為「u 子樹內的距離和」的變化量只取決於節點數。正確性可以用歸納法：根的答案正確，若父節點的答案正確，換根公式逐一考慮每個節點距離的增減，得到的子節點答案也正確。

```text
範例 1：以 0 為根
        0
       / \
      1   2
         /|\
        3 4 5

第一遍（後序）：
節點  size  down
3      1    0
4      1    0
5      1    0
2      4    (0+1) + (0+1) + (0+1) = 3
1      1    0
0      6    (down[1]+size[1]) + (down[2]+size[2]) = (0+1) + (3+4) = 8

第二遍（前序），ans[u] = ans[p] − size[u] + (6 − size[u])：
ans[0] = 8
ans[1] = 8 − 1 + 5 = 12       （只有 1 自己變近，其他 5 個都變遠）
ans[2] = 8 − 4 + 2 = 6        （2、3、4、5 變近，0、1 變遠）
ans[3] = 6 − 1 + 5 = 10
ans[4] = 6 − 1 + 5 = 10
ans[5] = 6 − 1 + 5 = 10
```

從 0 換到 2 時，2 的子樹有 4 個節點（2、3、4、5），它們都近了 1，只有 0 和 1 遠了 1，淨減少 2，所以 `ans[2] = 6` 是全樹最小。這也說明了換根公式的另一個意義：`ans[u] − ans[p] = n − 2 · size[u]`，只要孩子的子樹超過一半，往那裡移動就會變小（F2）。

### 解法

```python
import random
from collections import deque


def sum_of_distances_in_tree(n: int, edges: list[list[int]]) -> list[int]:
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    parent = [-1] * n
    order = [0]
    seen = [False] * n
    seen[0] = True
    for u in order:                              # BFS 順序：父節點在子節點之前
        for v in adj[u]:
            if not seen[v]:
                seen[v] = True
                parent[v] = u
                order.append(v)

    size = [1] * n                               # size[u]：u 的子樹節點數
    down = [0] * n                               # down[u]：u 到子樹內所有節點的距離和
    for u in reversed(order):                    # 第一遍：後序
        p = parent[u]
        if p >= 0:
            size[p] += size[u]
            down[p] += down[u] + size[u]         # u 子樹的每個節點離 p 再遠 1

    ans = [0] * n
    ans[0] = down[0]                             # 根的答案就是 down
    for u in order[1:]:                          # 第二遍：前序換根
        ans[u] = ans[parent[u]] - size[u] + (n - size[u])
    return ans


def brute(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    res = []
    for s in range(n):
        dist = [-1] * n
        dist[s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if dist[v] < 0:
                    dist[v] = dist[u] + 1
                    q.append(v)
        res.append(sum(dist))
    return res


assert sum_of_distances_in_tree(6, [[0, 1], [0, 2], [2, 3], [2, 4], [2, 5]]) == [8, 12, 6, 10, 10, 10]
assert sum_of_distances_in_tree(1, []) == [0]
assert sum_of_distances_in_tree(2, [[1, 0]]) == [1, 1]
n = 30000
path = [[i, i + 1] for i in range(n - 1)]                # 3 萬個節點的鏈，遞迴會爆
res = sum_of_distances_in_tree(n, path)
assert res[0] == n * (n - 1) // 2 and res[n // 2] == (n // 2) * (n // 2 + 1) // 2 + (n // 2 - 1) * (n // 2) // 2
for _ in range(300):
    m = random.randint(1, 12)
    es = [[i, random.randrange(i)] for i in range(1, m)]
    assert sum_of_distances_in_tree(m, es) == brute(m, es)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：建鄰接表、BFS、後序、前序各一遍。空間 O(n)：鄰接表、`parent`、`order`、`size`、`down`、`ans`。邊界情況：n = 1 時沒有邊，`order = [0]`，兩個迴圈都不做事，回傳 `[0]`；邊的方向任意（`[1, 0]` 與 `[0, 1]` 相同），因為建的是無向鄰接表；答案的最大值出現在長鏈的端點，約 n²/2 ≈ 4.5 × 10⁸，Python 不會溢位，在 Java／C++ 用 `int` 剛好夠（< 2³¹），但距離和的中間運算若有加權（F1）就要用 64 位元。用 BFS 順序取代遞迴，是因為 3 × 10⁴ 個節點的鏈會超過 Python 的遞迴深度。

### Follow-up

> [!question]- F1. 如果每條邊有權重 w（距離是路徑上的權重和）呢？
> 兩個式子各乘上邊權即可。後序：`down[p] += down[u] + w(p, u) · size[u]`，因為 u 子樹的每個節點都多走一條權重 w 的邊。前序：`ans[u] = ans[p] + w(p, u) · (n − 2 · size[u])`，子樹內 `size[u]` 個節點各近了 w，子樹外 `n − size[u]` 個各遠了 w。BFS 時把邊權記在 `parent_w[v]` 裡，仍是 O(n)。權重可以很大時，答案可能超過 2⁶³，要確認語言的整數範圍。

> [!question]- F2. 如果只要找出「到所有節點距離和最小」的那個節點呢？
> 由 `ans[u] − ans[p] = n − 2 · size[u]` 可知，從 p 走向孩子 u 會讓答案變小，若且唯若 `size[u] > n / 2`。所以從根開始，只要有某個孩子的子樹超過一半就往那裡走，走到所有孩子的子樹都 ≤ n / 2 為止，這個節點就是樹的 centroid（重心），距離和最小。只需要第一遍的 `size`，O(n)。這也是第 16 章核心題 4（310. Minimum Height Trees）F4 提到的「距離和最小點」與「高度最小點」的差別：前者是 centroid，後者是直徑的中點。

> [!question]- F3. 如果只要算每個節點到「k 個指定節點」的距離和呢（例如到所有商店的總距離）？
> 把 `size[u]` 換成「u 子樹內的指定節點數」`cnt[u]`，n 換成指定節點總數 K。後序：`down[p] += down[u] + cnt[u]`；前序：`ans[u] = ans[p] − cnt[u] + (K − cnt[u])`。推導完全相同，因為換根時變近的是子樹內的指定節點、變遠的是子樹外的指定節點。O(n)。更一般地，給每個節點一個權重 `c[v]`，求 Σ c[v] · dist(u, v)，就把 `cnt` 換成子樹權重和。

> [!question]- F4. 如果要的是距離平方和 Σ dist(u, v)² 呢？
> 一個節點整體移動 1 時，平方和的變化需要一次和與零次和：(d + 1)² = d² + 2d + 1。所以每個子樹維護三個量：節點數 S₀、距離和 S₁、距離平方和 S₂。從孩子 c 合併到 p 時，c 子樹的量要「整體加 1」：S₂ 變成 S₂ + 2S₁ + S₀、S₁ 變成 S₁ + S₀、S₀ 不變，再加到 p 上。換根時同樣的位移公式，分別對子樹內（−1：S₂ − 2S₁ + S₀）和子樹外（+1）套用，因為三個量都是加總，可以用減法撤銷。仍是 O(n)。這展示了 rerooting 的通用條件：狀態在「整體平移一步」下有封閉的更新式，而且合併可以撤銷。

> [!question]- F5. 如果要的是每個節點到最遠節點的距離呢？
> 合併運算變成 max，不能用減法撤銷，要用 24.3 節的 top-2：後序時每個節點記住經由不同孩子的最長與次長向下距離，以及最長來自哪個孩子；前序時 `up[u] = 1 + max(up[p], 父節點經由「另一個」孩子的最長距離)`。答案是 `max(down1[u], up[u])`，O(n)。也可以用樹的直徑：先 BFS 找到直徑的兩個端點 a、b，每個節點的最遠距離等於 `max(dist(u, a), dist(u, b))`，三次 BFS 即可，這是更短的寫法，但只適用於「最遠距離」這個特定問題。

### 心得

關鍵突破是換根公式 `ans[u] = ans[p] − size[u] + (n − size[u])`：把觀察點沿著一條邊移動一步，只有「子樹內變近、子樹外變遠」兩群節點，變化量只取決於子樹大小。它是核心題 1（337）後序回傳狀態的延伸：第一遍仍是後序合併子樹資訊，第二遍則把「子樹外」的資訊由上往下傳，這就是 rerooting 的完整形態；第 12 章難題 5（2458）也是同一種兩遍走訪。面試時先說 O(n²) 的「每個節點做一次 BFS」，再說「我先算根的答案，然後看根移動一步時答案怎麼變」，在白板上畫出一條邊把樹切成兩半，寫出兩群節點的增減，公式就自然出現；最後主動說明為什麼用 BFS 順序取代遞迴。

## 難題 2｜943. Find the Shortest Superstring｜Hard

### 題目

給一個字串陣列 `words`，請回傳一個最短的字串，使得 `words` 中的每個字串都是它的子字串。若有多個最短的答案，回傳任意一個即可。題目保證 `words` 中沒有任何一個字串是另一個字串的子字串，而且字串彼此不同。限制：`1 <= len(words) <= 12`，`1 <= len(words[i]) <= 20`，只含小寫英文字母。

- 範例 1：`words = ["alex", "loves", "leetcode"]`，三者之間沒有任何重疊，任何串接順序都是最短，例如 `"alexlovesleetcode"`（長度 17）。
- 範例 2：`words = ["catg", "ctaagt", "gcta", "ttca", "atgcatc"]`，回傳 `"gctaagttcatgcatc"`（長度 16）：`gcta` 與 `ctaagt` 重疊 `cta`，`ctaagt` 與 `ttca` 重疊 `t`，`ttca` 與 `catg` 重疊 `ca`，`catg` 與 `atgcatc` 重疊 `atg`。
- 範例 3（邊界）：`words = ["abc"]`，回傳 `"abc"`。
- 範例 4：`words = ["ab", "bc", "cd"]`，回傳 `"abcd"`。

### 提示

> [!tip]- 提示 1
> 因為沒有字串是另一個的子字串，最短的 superstring 一定是把所有字串排成某個順序，相鄰兩個盡量重疊後串起來。問題變成：找一個排列，使相鄰兩兩的重疊總和最大。

> [!tip]- 提示 2
> 先算出 `overlap[i][j]`：`words[i]` 的後綴與 `words[j]` 的前綴最長能重疊多少。這樣「排列的總長度」就只取決於相鄰兩個字串，這是 TSP 的結構。

> [!tip]- 提示 3
> `dp[mask][last]` = 已經用了 mask 中的字串、最後一個是 last 時，最多能省下多少字元。轉移是接上一個不在 mask 中的 nxt，增加 `overlap[last][nxt]`。記下每個狀態是從哪個 last 來的，最後倒推出順序。

### 詳解

**為什麼直覺做法不夠**。最常見的直覺是貪婪：每次找重疊最大的兩個字串合併，重複到只剩一個。這是著名的 greedy superstring 演算法，實務上表現不錯，但不保證最短。暴力枚舉所有排列是 12! ≈ 4.8 × 10⁸，每個排列再花 O(n) 計算長度，太慢。但排列的總長度有一個很強的結構：它等於所有字串長度的總和減去相鄰兩兩的重疊，而相鄰兩個字串的重疊只取決於這兩個字串本身，和其他字串放在哪裡無關。

**為什麼最短解一定是「排列 + 最大重疊」**。在最短的 superstring 中，每個字串都出現在某個起點。因為沒有字串是另一個的子字串，若把它們依起點排序，終點的順序也相同（起點較早的若終點較晚，就會包住後面那個）。所以相鄰兩個字串在 superstring 中要嘛重疊、要嘛接續，而且在最短解中，相鄰的重疊一定取最大值，否則可以把後面整段往左移，得到更短的字串。於是問題完全化為：找一個排列 π，最大化 Σ `overlap[π(t)][π(t+1)]`。

**這就是 TSP**。把每個字串看成城市，「從 i 走到 j」的收益是 `overlap[i][j]`，要找一條拜訪每個城市恰好一次的路徑（不需要回到起點），使總收益最大。用 24.4 節的 `dp[mask][last]`：已經用掉 mask 這些字串、最後一個是 last 時，最大的總重疊。起點是 `dp[1 << i][i] = 0`（任何字串都可以當第一個），轉移 `dp[mask | 1 << nxt][nxt] = max(dp[mask][last] + overlap[last][nxt])`。答案是 `max over last of dp[全集][last]`，最短長度是總長度減去它。因為還要輸出字串本身，所以另外記 `parent[mask][last]`，從最佳的結尾一路往回找出順序，再依序把每個字串去掉重疊部分接上。

```text
範例 2 的 overlap 矩陣（列 = 前一個，行 = 後一個）
            catg  ctaagt  gcta  ttca  atgcatc
catg          -     0      1     0      3
ctaagt        0     -      0     1      0
gcta          0     3      -     0      1
ttca          2     0      0     -      1
atgcatc       1     1      0     0      -

最佳路徑：gcta → ctaagt → ttca → catg → atgcatc
重疊：         3    +   1   +  2   +   3    = 9
總長：4 + 6 + 4 + 4 + 7 = 25，最短 = 25 − 9 = 16

逐步接起來：
gcta
gcta + agt          （ctaagt 去掉重疊的 cta）     = gctaagt
gctaagt + tca       （ttca 去掉重疊的 t）         = gctaagttca
gctaagttca + tg     （catg 去掉重疊的 ca）        = gctaagttcatg
gctaagttcatg + catc （atgcatc 去掉重疊的 atg）    = gctaagttcatgcatc
```

這個例子中，最大的單一重疊是 3（`gcta → ctaagt`、`catg → atgcatc`），兩者都被用上；但進入 catg 的邊只能選一條：`ttca → catg` 的 2 或 `atgcatc → catg` 的 1，DP 透過枚舉所有 (mask, last) 自動做出了取捨。還原時從 `dp[11111][atgcatc]` 開始，依 parent 找到 catg、ttca、ctaagt、gcta，再反轉順序。

### 解法

```python
import random
from itertools import permutations


def shortest_superstring(words: list[str]) -> str:
    n = len(words)
    # overlap[i][j]：words[i] 的後綴與 words[j] 的前綴最長重疊多少
    overlap = [[0] * n for _ in range(n)]
    for i, a in enumerate(words):
        for j, b in enumerate(words):
            if i != j:
                for k in range(min(len(a), len(b)) - 1, 0, -1):
                    if a.endswith(b[:k]):
                        overlap[i][j] = k
                        break

    full = 1 << n
    dp = [[-1] * n for _ in range(full)]          # dp[mask][last]：最多能省下的字元數
    parent = [[-1] * n for _ in range(full)]
    for i in range(n):
        dp[1 << i][i] = 0
    for mask in range(1, full):
        for last in range(n):
            if dp[mask][last] < 0:
                continue
            for nxt in range(n):
                if mask >> nxt & 1:
                    continue
                nm = mask | 1 << nxt
                val = dp[mask][last] + overlap[last][nxt]
                if val > dp[nm][nxt]:
                    dp[nm][nxt] = val
                    parent[nm][nxt] = last

    # 還原順序：從最佳的結尾往回走
    last = max(range(n), key=lambda i: dp[full - 1][i])
    mask, order = full - 1, []
    while last != -1:
        order.append(last)
        prev = parent[mask][last]
        mask ^= 1 << last
        last = prev
    order.reverse()

    result = words[order[0]]
    for a, b in zip(order, order[1:]):
        result += words[b][overlap[a][b]:]
    return result


def brute_len(words):
    best = float("inf")
    for p in permutations(words):
        s = p[0]
        for w in p[1:]:
            k = max((k for k in range(min(len(s), len(w)), -1, -1) if s.endswith(w[:k])), default=0)
            s += w[k:]
        best = min(best, len(s))
    return best


def check(words):
    s = shortest_superstring(words)
    assert all(w in s for w in words)
    return len(s)


assert shortest_superstring(["alex", "loves", "leetcode"]) in (
    "alexlovesleetcode", "leetcodealexloves", "lovesleetcodealex",
    "alexleetcodeloves", "leetcodelovesalex", "lovesalexleetcode")
assert check(["catg", "ctaagt", "gcta", "ttca", "atgcatc"]) == 16   # gctaagttcatgcatc
assert shortest_superstring(["abc"]) == "abc"
assert check(["ab", "bc", "cd"]) == 4                                 # abcd
for _ in range(200):
    pool = set()
    while len(pool) < random.randint(1, 6):
        pool.add("".join(random.choice("ab") for _ in range(random.randint(2, 5))))
    ws = [w for w in pool if not any(w != o and w in o for o in pool)]  # 題目保證沒有子字串關係
    assert check(ws) == brute_len(ws)
big = ["".join(random.choice("abc") for _ in range(20)) for _ in range(12)]
assert all(w in shortest_superstring(big) for w in big)                  # n = 12 的最大規模
print("all tests passed")
```

### 複雜度與邊界

時間 O(n² · L² + 2ⁿ · n²)，L ≤ 20 是字串長度：overlap 矩陣每一對最多比較 L 次、每次 `endswith` O(L)，共 O(n² · L²)，可以忽略；DP 有 2ⁿ · n 個狀態、每個 n 種轉移，n = 12 時約 5.9 × 10⁵。空間 O(2ⁿ · n)，用於 `dp` 與 `parent`。邊界情況：n = 1 時直接回傳該字串，DP 只有一個狀態；重疊長度上限是 `min(len(a), len(b)) − 1`，因為重疊等於整個字串就代表它是另一個的子字串，題目保證不會發生；還原時要先記住 `prev` 再從 mask 中拿掉 last，順序錯了會讀到錯誤的 parent。

### Follow-up

> [!question]- F1. 如果不保證「沒有字串是另一個的子字串」，也可能有重複字串呢？
> 先做預處理：去掉重複，再把所有是其他字串子字串的字串刪掉，因為只要包含了較長的那個，較短的自然也被包含。預處理 O(n² · L²)。之後剩下的字串滿足原題的保證，用同樣的 DP。若不預處理，「排列 + 相鄰最大重疊」的推論會失效：例如 `["abc", "b"]`，`b` 應該被完全包在 `abc` 裡，但排列模型會把它接在前面或後面，得到長度 4 而不是 3。

> [!question]- F2. 如果只要最短的長度，不用輸出字串呢？
> 不需要 `parent`，空間減半；答案是 `Σ len(words) − max over last of dp[全集][last]`，時間仍是 O(2ⁿ · n²)。空間還能再省：這個 DP 的每次轉移只加入一個字串，所以 popcount 為 t 的狀態只依賴 popcount 為 t − 1 的狀態。依 popcount 分層處理、只保留相鄰兩層（用 dict 存 mask），空間降到 O(C(n, n/2) · n)，n = 12 時約 924 · 12 個值。面試中提出「只需要長度時可以省掉還原資訊」即可。

> [!question]- F3. 如果是環狀的 superstring（字串頭尾相接，每個字串可以跨過接縫）呢？
> 環狀時路徑要回到起點，變成真正的 TSP 迴路。因為環沒有起點，可以固定 `words[0]` 為第一個：`dp[1][0] = 0`，最後答案是 `max over last of dp[全集][last] + overlap[last][0]`，最短環長是總長度減去它。時間同樣 O(2ⁿ · n²)。固定起點是 24.4 節 `tsp` 模板的做法，它避免了 n 倍的重複計算（同一個環從 n 個不同的起點算 n 次）。

> [!question]- F4. 如果 n 是 50 或 100 呢？
> 2ⁿ 不可行，精確解在一般情況下是 NP-hard（shortest common superstring 是 NP-hard），只能用近似或 heuristic。標準做法是 greedy merge：重複選出重疊最大的一對合併，O(n³ · L) 或用 heap 加速；已知它的長度不超過最佳解的 3.5 倍，並且猜想不超過 2 倍。另一種是把問題看成最大權重的 Hamiltonian path，用 assignment 問題的解做 cycle cover，再把環切開接起來，有可證明的近似比。面試中說出「NP-hard → 指數 DP 或近似」並給出貪婪即可。

> [!question]- F5. 如果多個最短答案中要回傳字典序最小的那一個呢？
> 只比較重疊總和不夠，因為同樣長度的不同順序會產生不同的字串。一種正確的做法是讓 DP 由後往前存「最佳的後半段字串」：`best[mask][first]` = 用 mask 中的字串、以 first 開頭的最短且字典序最小的 superstring，轉移 `words[first][:len − overlap[first][nxt]] + best[mask ^ bit(first)][nxt]`，先比長度再比字典序。狀態數 2ⁿ · n，每個存一個長度最多 240 的字串，比較成本 O(n · L)，總時間 O(2ⁿ · n² · n · L)，n = 12 時仍可接受。由前往後存的版本不正確，因為前綴相同不保證整體最小，這是很好的追問點。

### 心得

關鍵突破是兩次化約：先證明最短 superstring 一定是「某個排列、相鄰取最大重疊」，再發現總長度只取決於相鄰兩兩的重疊，於是問題變成 TSP，用 `dp[mask][last]` 解決。和本章其他題的關係：核心題 3（526）的 `dp[mask]` 只需要知道集合，因為下一步的限制只取決於「第幾個位置」；這題的成本取決於最後一個元素，所以多一維 last，這是兩種 bitmask DP 狀態最重要的分界。面試時先說明子字串保證的作用、畫出 overlap 矩陣，再寫出 DP 與還原；被問到 n 變大時，能說出 NP-hard 與貪婪近似，就是完整的回答。

## 難題 3｜1349. Maximum Students Taking Exam｜Hard

### 題目

教室的座位是一個 m × n 的字元矩陣 `seats`，`'.'` 是好的座位，`'#'` 是壞掉的座位（不能坐）。學生考試時能看到**左邊、右邊、左前方、右前方**四個相鄰座位的人的考卷，但看不到正前方和正後方的人。請安排學生坐在好的座位上，使得沒有任何學生能看到別人的考卷，回傳最多能坐幾個學生。限制：`1 <= m, n <= 8`。

- 範例 1：三列分別是 `# . # # . #`、`. # # # # .`、`# . # # . #`，回傳 `4`：第 0 列和第 2 列的第 1、4 行都坐人。第 1 列的第 0、5 行雖然是好座位，但坐在那裡的人能從左前方、右前方看到第 0 列第 1、4 行的考卷，兩邊只能擇一。
- 範例 2：5 × 2 的教室，五列分別是 `. #`、`# #`、`# .`、`# #`、`. #`，回傳 `3`：三個好座位分散在第 0、2、4 列，彼此都不在相鄰的列，全部可以坐。
- 範例 3：5 × 5 的教室，五列分別是 `# . . . #`、`. # . # .`、`. . # . .`、`. # . # .`、`# . . . #`，回傳 `10`。
- 範例 4（邊界）：`[["#"]]` 回傳 `0`；8 × 8 全是好座位時回傳 `32`，每一列隔一個座位坐一人。

### 提示

> [!tip]- 提示 1
> 一個學生只會和同一列、以及相鄰列的人衝突。所以如果一列一列地決定，第 r 列能怎麼坐，只取決於第 r − 1 列怎麼坐。

> [!tip]- 提示 2
> 每一列最多 8 個座位，一列的坐法可以用一個 8 位元的 mask 表示。列內的限制是「沒有兩個 1 相鄰」：`mask & (mask >> 1) == 0`；還要只坐好座位：`mask & ~good[r] == 0`。

> [!tip]- 提示 3
> 相鄰兩列的限制是「左前方、右前方沒有人」：`cur & (prev << 1) == 0` 而且 `cur & (prev >> 1) == 0`。`dp[r][cur] = max over 相容的 prev (dp[r − 1][prev]) + popcount(cur)`。

### 詳解

**為什麼直覺做法不夠**。暴力解是對每個好座位決定坐或不坐，最多 2⁶⁴ 種，完全不可能。逐格 backtracking 加剪枝在稀疏的教室裡可行，但 8 × 8 全是好座位時仍然是天文數字。貪婪（例如先把某一列坐滿，再處理其他列）會失敗：範例 1 若第 1 列先坐了第 0、5 行，第 0、2 列的四個好座位就全部被擋住，只能坐 2 人。這是一個「最大獨立集」問題：把座位當節點、互相看得到的座位連邊，要選最多個互不相鄰的節點。一般圖的最大獨立集是 NP-hard，所以必須利用這張圖的特殊結構。

**突破點：衝突只跨一列，而一列很窄**。學生能看到的四個方向中，左右在同一列，左前方、右前方在前一列。所以第 r 列的人只和第 r − 1 列、第 r 列、第 r + 1 列的人有關。如果由上往下一列一列地決定，決定第 r 列時只需要知道第 r − 1 列的完整坐法，更早的列已經和第 r 列無關。一列只有 n ≤ 8 個座位，完整坐法就是一個 n 位元的 mask。這種「把一整列（或一整個邊界）的狀態壓成 bitmask」的 DP 叫 profile DP 或 broken profile DP 的列版本，是 bitmask DP 在格子題上最常見的形式。

**狀態與轉移**。`dp[r][cur]` = 前 r 列已經安排好、第 r 列的坐法是 cur 時，最多坐了幾人。cur 本身要合法：只坐好座位（`cur & ~good[r] == 0`）、同列不相鄰（`cur & (cur >> 1) == 0`）。從上一列 prev 轉移過來時，第 r 列第 j 行的人能看到第 r − 1 列第 j − 1 行和第 j + 1 行，所以要求 `cur & (prev << 1) == 0` 而且 `cur & (prev >> 1) == 0`。正前方（`cur & prev`）不在限制中，因為題目說看不到。轉移式 `dp[r][cur] = popcount(cur) + max(dp[r − 1][prev])`，對所有相容的 prev 取最大；第 0 列的「上一列」視為空的 mask 0。

**狀態數比 2ⁿ 小得多**。沒有兩個相鄰 1 的 n 位元 mask 個數是 Fibonacci 數 F(n + 2)，n = 8 時只有 55 個。所以每一列最多 55 個狀態、每個狀態最多和 55 個上一列狀態比較，總共 m × 55² ≈ 2.4 × 10⁴ 次，非常快。解法中先列出這 55 個 `candidates`，每一列再用 `good[r]` 過濾，只保留真正可行的坐法。

```text
範例 1（mask 以「行 0 … 行 5」由左到右書寫，1 表示坐人）
第 0 列好座位：行 1、4        第 1 列：行 0、5        第 2 列：行 1、4

第 0 列：
cur       人數  dp
000000     0    0
010000     1    1
000010     1    1
010010     2    2

第 1 列（cur 的行 j 不能和 prev 的行 j−1、j+1 同時有人）：
cur       相容的 prev                      dp
000000    全部（最大 2）                    0 + 2 = 2
100000    prev 行 1 不能有人：000000、000010  1 + 1 = 2
000001    prev 行 4 不能有人：000000、010000  1 + 1 = 2
100001    只有 000000                       2 + 0 = 2

第 2 列：
cur       相容的 prev                      dp
000000    全部（最大 2）                    0 + 2 = 2
010000    prev 行 0、2 不能有人：000000、000001  1 + 2 = 3
000010    prev 行 3、5 不能有人：000000、100000  1 + 2 = 3
010010    prev 行 0、2、3、5 不能有人：000000    2 + 2 = 4

答案 = max(第 2 列的 dp) = 4
```

第 1 列不論怎麼坐，最多都只有 2 人（坐 `100001` 時第 0 列只能空著）。關鍵在第 2 列的 `010010`：它要求第 1 列完全空著，而第 1 列空著時第 0 列可以坐 2 人，合計 4 人。DP 透過「每個 cur 對所有相容的 prev 取最大」，自動發現了「讓中間那一列全空」這個全域最佳的選擇，這是貪婪做不到的。

### 解法

```python
import random
from itertools import product


def max_students(seats: list[list[str]]) -> int:
    m, n = len(seats), len(seats[0])
    good = [sum(1 << j for j in range(n) if row[j] == ".") for row in seats]
    # 同一列內合法的坐法：只坐好位子，而且沒有兩個人左右相鄰
    candidates = [mask for mask in range(1 << n) if mask & (mask >> 1) == 0]
    dp = {0: 0}                                     # dp[mask]：上一列坐法為 mask 時的最多人數
    for r in range(m):
        new = {}
        for cur in candidates:
            if cur & ~good[r]:
                continue
            people = cur.bit_count()
            best = -1
            for prev, val in dp.items():
                if cur & (prev << 1) or cur & (prev >> 1):   # 左前方、右前方有人
                    continue
                best = max(best, val)
            if best >= 0:
                new[cur] = best + people
        dp = new
    return max(dp.values())


def brute(seats):
    m, n = len(seats), len(seats[0])
    cells = [(r, c) for r in range(m) for c in range(n) if seats[r][c] == "."]
    best = 0
    for pick in product([0, 1], repeat=len(cells)):
        chosen = {cells[i] for i, b in enumerate(pick) if b}
        ok = all((r, c + 1) not in chosen and (r + 1, c - 1) not in chosen and (r + 1, c + 1) not in chosen
                 for r, c in chosen)
        if ok:
            best = max(best, len(chosen))
    return best


ex1 = [["#", ".", "#", "#", ".", "#"],
       [".", "#", "#", "#", "#", "."],
       ["#", ".", "#", "#", ".", "#"]]
ex2 = [[".", "#"], ["#", "#"], ["#", "."], ["#", "#"], [".", "#"]]
ex3 = [["#", ".", ".", ".", "#"],
       [".", "#", ".", "#", "."],
       [".", ".", "#", ".", "."],
       [".", "#", ".", "#", "."],
       ["#", ".", ".", ".", "#"]]
assert max_students(ex1) == 4
assert max_students(ex2) == 3
assert max_students(ex3) == 10
assert max_students([["#"]]) == 0
assert max_students([["."] * 8 for _ in range(8)]) == 32          # 每列隔一個位子坐一人，4 × 8
for _ in range(300):
    m, n = random.randint(1, 4), random.randint(1, 4)
    g = [[random.choice(".#") for _ in range(n)] for _ in range(m)]
    assert max_students(g) == brute(g)
print("all tests passed")
```

### 複雜度與邊界

時間 O(m · F²) ≤ O(m · 4ⁿ)，F = F(n + 2) 是同列不相鄰的 mask 數（n = 8 時 55），實際約 m × 55² 次相容性檢查；列出 candidates 需要 O(2ⁿ)。空間 O(F)，只保留上一列的 dict。邊界情況：第 0 列用 `{0: 0}` 作為虛擬的上一列，這樣第 0 列的每個合法 cur 都相容；某一列全是壞座位時，只有 cur = 0 合法，dp 原樣傳下去；`prev << 1` 可能超出 n 位元，但 cur 只有 n 位元，`&` 之後高位自然消失，不需要遮罩；`dp` 不會變空，因為 cur = 0 永遠合法。

### Follow-up

> [!question]- F1. 有沒有多項式時間的解法？如果教室是 100 × 100 呢？
> 有。觀察所有衝突的方向：左右（同列、相鄰行）、左前方與右前方（相鄰列、相鄰行），**每一種衝突的兩個座位都在相鄰的行**，也就是一個在偶數行、一個在奇數行。所以衝突圖是二分圖（偶數行 vs. 奇數行）。二分圖的最大獨立集 = 節點數 − 最大匹配數（König 定理），最大匹配用 Hungarian（Kuhn）演算法 O(V · E) 或 Hopcroft–Karp O(E√V)。100 × 100 時 V = 10⁴，每個座位最多 6 個衝突鄰居，E ≈ 3 × 10⁴，完全可行，而 profile DP 的 2¹⁰⁰ 不可能。面試中能看出二分結構是很強的加分。

> [!question]- F2. 如果學生也能看到正前方和正後方的人呢？
> profile DP 只要多加一個條件 `cur & prev == 0`，複雜度不變。但 F1 的二分圖解法失效了：正前方的衝突連接同一行的兩個座位，而 (r, c)、(r, c + 1)、(r + 1, c) 中，(r, c + 1) 和 (r + 1, c) 又是對角線關係，三者兩兩衝突，形成三角形，衝突圖不再是二分圖。這時就只能回到指數級的 profile DP，這也說明了題目為什麼特意設計成「看不到正前方」，以及為什麼 m、n 限制在 8。

> [!question]- F3. 如果要計算「坐滿最多人」的坐法有幾種呢？
> 每個 dp 狀態改存 `(最多人數, 方法數)`。轉移時，對所有相容的 prev，找出 `dp[prev]` 人數的最大值，方法數是所有達到這個最大值的 prev 的方法數之和；最後在最後一列的所有 cur 中，取人數最大者的方法數總和。複雜度不變，O(m · F²)。這是 DP 從「最佳值」擴充到「最佳值的計數」的標準手法，和核心題 1 F5 的樹 DP 版本相同。

> [!question]- F4. 如果 m 很大（例如 10⁵ 列）但 n ≤ 8 呢？轉置教室能不能讓 DP 更快？
> m 大不是問題：profile DP 對 m 是線性的，O(m · F²) ≈ 10⁵ × 55² ≈ 3 × 10⁸，Python 偏慢但可以預先算好每對 (prev, cur) 是否相容並只對可行的 cur 做；或直接用 F1 的匹配解。如果是 n 很大而 m 很小，想把教室轉置讓 mask 變窄，要注意轉置後衝突關係會改變：原本的左右（同列）變成上下（同行，`cur & prev`），原本的上下（不衝突）變成同列相鄰（不再限制），對角線維持對角線。所以轉置後的相容條件是 `cur & prev == 0`、`cur & (prev << 1) == 0`、`cur & (prev >> 1) == 0`，同列沒有限制。換句話說，可以沿著任一維做 profile DP，只要相容條件跟著改寫。

### 心得

關鍵突破是看出衝突只跨一列，於是把一整列的坐法壓成 mask，`dp[row][mask]` 只依賴上一列，這是 profile DP 的標準形。和本章其他題的關係：核心題 3、4 的 mask 表示「哪些元素已經用掉」，這題的 mask 表示「邊界上的狀態」，兩者都是把後續決策需要的資訊壓成位元；同列不相鄰的 mask 只有 Fibonacci 個，是 bitmask DP 中常見的「合法狀態遠少於 2ⁿ」的現象。面試時先寫出列內與列間的三個位元條件並各舉一個例子驗證，再寫 DP；若時間允許，提出 F1 的二分圖觀察，展示你能從題目結構中找到多項式解法。

## 難題 4｜233. Number of Digit One｜Hard

### 題目

給一個整數 n，請計算 0 到 n 的所有整數中，數字 1 總共出現了幾次（每個數的每一位都要算）。限制：`0 <= n <= 10⁹`。

- 範例 1：`n = 13`，回傳 `6`：1、10、11、12、13 中，1 出現在 1（一次）、10（一次）、11（兩次）、12（一次）、13（一次）。
- 範例 2（邊界）：`n = 0`，回傳 `0`；`n = 1`，回傳 `1`。
- 範例 3：`n = 100`，回傳 `21`：個位數是 1 的有 10 個（1、11、…、91），十位數是 1 的有 10 個（10 到 19），百位數是 1 的有 1 個（100）。
- 範例 4：`n = 213`，回傳 `146`。

### 提示

> [!tip]- 提示 1
> 逐一數到 10⁹ 太慢。換個角度：不要按「數」來數，而是按「位置」來數。個位數是 1 的數有幾個？十位數是 1 的有幾個？

> [!tip]- 提示 2
> 固定第 p 位（p = 1, 10, 100, …），把 n 拆成三段：比這一位高的 `high = n // (10p)`、這一位 `cur = n // p % 10`、比這一位低的 `low = n % p`。高位取 0 到 high − 1 時，這一位放 1、低位可以任意，共 `high × p` 個。

> [!tip]- 提示 3
> 高位剛好等於 high 時，要看 cur：cur > 1 時這一位放 1、低位任意，p 個；cur = 1 時低位只能是 0 到 low，`low + 1` 個；cur = 0 時這一位放 1 就超過 n，0 個。對每一位加總。也可以用數位 DP，state 是「目前寫了幾個 1」。

### 詳解

**為什麼直覺做法不夠**。逐一把 0 到 n 每個數轉成字串數 1，是 O(n log n)，n = 10⁹ 時約 10¹⁰ 次運算。這題和核心題 5、難題 5 不同：它不是在數「有幾個數滿足條件」，而是在數「所有數的某個量的總和」。但同樣的觀察成立：一大群數字共享相同的前綴，它們的貢獻可以用乘法一次算完，不必逐一處理。

**突破點一：按位置拆開（貢獻法）**。總次數 = Σ（第 p 位是 1 的數的個數），因為每個 1 恰好屬於某一位，這是把「對數求和」換成「對位置求和」的交換求和順序。固定第 p 位，一個數 x ≤ n 的這一位是 1，若且唯若 x 的高位部分 h、這一位 1、低位部分 l 組合起來 ≤ n。分三種情況：h < high 時，不論低位是什麼都 < n，低位有 p 種，h 有 high 種（0 到 high − 1），共 `high × p`；h = high 時，比較這一位：cur > 1 代表放 1 之後已經比 n 小，低位任意，p 種；cur = 1 代表放 1 之後和 n 相同，低位要 ≤ low，`low + 1` 種；cur = 0 代表放 1 就超過 n，0 種。h > high 時一定超過 n。每一位 O(1)，總共 O(log n)。

**突破點二：數位 DP（累加型）**。用 24.5 節的模板，state 記「目前寫了幾個 1」，走到終點時回傳這個數量而不是 1。這樣 `go(0, 0, True)` 回傳的就是所有 ≤ n 的數中 1 的總個數。這裡不需要 started，因為前導零不是 1，不影響計數，而 0 本身也不含 1。狀態數是 位數 × (最多 10 個 1) × 2，非常小。兩種寫法本質相同：貢獻法是把數位 DP 中「不 tight 的分支」用公式 `p` 或 `high × p` 直接算出來。

**正確性的關鍵**。貢獻法中最容易錯的是 cur = 1 的情況：高位等於 high、這一位也等於 n 的這一位時，數字仍然貼著 n（就是數位 DP 中 tight 的路徑），低位只能從 0 到 low，所以是 `low + 1` 而不是 p。cur = 0 時，高位等於 high 的數這一位最多是 0，放不了 1。用 n = 213 驗算：

```text
n = 213

p = 1（個位）：high = 21, cur = 3, low = 0
  高位 0..20：每個都能讓個位是 1           → 21 × 1 = 21   （1, 11, …, 201）
  高位 = 21，cur = 3 > 1：個位放 1 不超過    → 1             （211）
  小計 22

p = 10（十位）：high = 2, cur = 1, low = 3
  高位 0..1：十位放 1、個位任意               → 2 × 10 = 20  （10–19, 110–119）
  高位 = 2，cur = 1：十位放 1，個位只能 0..3  → 3 + 1 = 4    （210, 211, 212, 213）
  小計 24

p = 100（百位）：high = 0, cur = 2, low = 13
  高位只能是 0（沒有更小的）                 → 0
  高位 = 0，cur = 2 > 1：百位放 1、低位任意   → 100          （100–199）
  小計 100

總計 22 + 24 + 100 = 146
```

211 這個數在個位和十位各被算了一次，這是正確的，因為題目數的是「1 出現的次數」而不是「含 1 的數」（F4）。十位那一段的 `low + 1 = 4` 正是 cur = 1 的情況：210 到 213 共 4 個數的十位是 1，再往上就超過 n。

### 解法

```python
import random
from functools import cache


def count_digit_one(n: int) -> int:
    """逐位計數：第 p 位（p = 1, 10, 100, …）是 1 的數有幾個。"""
    total, p = 0, 1
    while p <= n:
        high, cur, low = n // (p * 10), n // p % 10, n % p
        total += high * p                       # 高位取 0 … high−1：低位任意，p 種
        if cur > 1:
            total += p                          # 高位取 high、這位放 1：低位任意
        elif cur == 1:
            total += low + 1                    # 高位取 high、這位放 1：低位只能 0 … low
        p *= 10
    return total


def count_digit_one_dp(n: int) -> int:
    """24.5 節模板：state 是「目前為止寫了幾個 1」，終點把它加進答案。"""
    s = str(n)

    @cache
    def go(pos: int, ones: int, tight: bool) -> int:
        if pos == len(s):
            return ones
        limit = int(s[pos]) if tight else 9
        return sum(go(pos + 1, ones + (d == 1), tight and d == limit) for d in range(limit + 1))

    return go(0, 0, True)


def brute(n):
    return sum(str(i).count("1") for i in range(n + 1))


assert count_digit_one(13) == 6          # 1, 10, 11（兩個）, 12, 13
assert count_digit_one(0) == 0
assert count_digit_one(1) == 1
assert count_digit_one(100) == 21
assert count_digit_one(213) == 146
assert count_digit_one(10**9) == count_digit_one_dp(10**9) == 900000001
for n in list(range(0, 2000)) + [random.randint(0, 10**5) for _ in range(20)]:
    assert count_digit_one(n) == count_digit_one_dp(n) == brute(n)
print("all tests passed")
```

### 複雜度與邊界

貢獻法時間 O(log₁₀ n)，n = 10⁹ 時只有 10 輪；空間 O(1)。數位 DP 時間 O(L² · 10 · 2)，L 是位數，空間是快取的狀態數 O(L²)。邊界情況：n = 0 時 `p <= n` 不成立，迴圈不執行，回傳 0；n 是 10 的冪次（例如 100）時，最高位 cur = 1、low = 0，貢獻 1，就是 n 本身；`p` 會乘到超過 n 才停止，在 Java／C++ 中 n 接近 2³¹ 時 `p * 10` 可能溢位，要用 64 位元整數。

### Follow-up

> [!question]- F1. 如果要數的是數字 d（0 到 9 任意一個）出現的次數呢？
> d = 1 到 9 時，只要把公式中的 1 換成 d：`high × p + (p if cur > d else low + 1 if cur == d else 0)`。d = 0 比較特別，因為前導零不能算：高位部分不能是 0（否則這一位就是前導零），所以高位只能取 1 到 high − 1 再加上等於 high 的情況，變成 `(high − 1) × p + (p if cur > 0 else low + 1)`，而且當 high = 0（這一位已經是最高位）時直接停止。用數位 DP 寫時，就是 24.5 節的 started 旗標：只有 started 為 True 時寫下的 0 才計入。O(log n)。

> [!question]- F2. 如果要算 [lo, hi] 區間內所有數的 1 的總個數呢？
> `count_digit_one(hi) − count_digit_one(lo − 1)`，因為 f(x) 是 0 到 x 的總數，相減剩下 lo 到 hi。lo = 0 時 `f(−1)` 定義為 0。O(log hi)。這是數位 DP 和 prefix sum 共用的「區間 = 兩個前綴相減」技巧，在面試中常被用來檢查你是否會處理 lo 端的 off-by-one。

> [!question]- F3. 如果要的是 1 到 n 所有數的「位數和」呢？
> 位數和 = Σ_{d=1..9} d × (數字 d 出現的次數)，直接用 F1 的公式對九個數字加總，O(9 log n)。也可以用數位 DP：state 改成「目前的位數和」，終點回傳它，或者更省狀態地讓 `go` 同時回傳（剩下的數有幾個, 它們的位數和總和），轉移時把這一位的數字 d 乘上後面的個數加進去。後者的狀態只有 位數 × 2，是累加型數位 DP 的通用寫法。

> [!question]- F4. 如果要數的是「含有至少一個 1 的數」有幾個呢？
> 這是不同的問題：11 只算一次。用補集：含 1 的數 = n − （1 到 n 中完全不含 1 的數）。不含 1 的數用數位 DP 計算，每一位只能填 {0, 2, 3, …, 9}，這就是核心題 5 F1「digits 包含 0」的情況，需要 started 處理前導零。O(log n · 10)。也可以直接用數位 DP 帶一個布林 state「是否已經出現過 1」，終點時為 True 才計入。

> [!question]- F5. 如果是在二進位下數 1 呢？
> 公式完全相同，只是基底從 10 換成 2：第 b 位 p = 2^b，`high = n >> (b + 1)`、`cur = n >> b & 1`、`low = n & (p − 1)`，貢獻 `high × p + (low + 1 if cur == 1 else 0)`（二進位中沒有 cur > 1 的情況）。這就是核心題 2 F1 的週期公式，兩者是同一件事的兩種寫法。任何基底 b 的版本都只是把 10 換成 b，O(log_b n)。

### 心得

關鍵突破是交換求和順序：不按數字逐一數 1，而是對每一位問「這一位是 1 的數有幾個」，再把 n 拆成高位、這一位、低位三段分情況計數。和本章其他題的關係：核心題 5（902）與難題 5（2376）的數位 DP 是「計數型」，終點回傳 1；這題是「累加型」，終點回傳累積的量，模板只改一行。貢獻法其實就是把數位 DP 的自由分支寫成封閉公式。面試時建議先用一個三位數（例如 213）手算三個位置的貢獻，讓面試官看到 cur > 1、cur = 1、cur = 0 三種情況，再寫程式；若面試官要求通用性，再提出數位 DP 的版本。

## 難題 5｜2376. Count Special Integers｜Hard

### 題目

如果一個正整數的十進位表示中，每一位數字都互不相同，就稱它為「特殊整數」。給一個正整數 n，回傳 1 到 n 之間（含兩端）有幾個特殊整數。限制：`1 <= n <= 2 × 10⁹`。

- 範例 1：`n = 20`，回傳 `19`：1 到 20 中只有 11 不是特殊整數。
- 範例 2（邊界）：`n = 5`，回傳 `5`：一位數全部都是特殊整數；`n = 1` 回傳 `1`。
- 範例 3：`n = 135`，回傳 `110`：1 到 135 中，非特殊的有 11、22、…、99（9 個）；100、101（2 個）；110 到 119（10 個，每個都含兩個 1）；121、122、131、133（4 個），共 25 個，135 − 25 = 110。
- 範例 4：`n = 4381`，回傳 `2462`（詳解中逐位計算）。

### 提示

> [!tip]- 提示 1
> 這是數位 DP：由左到右決定每一位，需要記住哪些數字已經用過。一共只有 10 個數字，「已用過的集合」可以用一個 10 位元的 bitmask 表示。

> [!tip]- 提示 2
> 前導零要特別處理：`0012` 其實是 12，它的兩個前導 0 不能算作「用過數字 0」。這正是 started 旗標的用途：started 為 False 時填 0 不改變 mask。

> [!tip]- 提示 3
> 不 tight 時，剩下的 k 位可以自由從「沒用過的 10 − u 個數字」中排列，方法數是 P(10 − u, k)，只和 u（用了幾個）有關，和用了哪些無關。所以可以不用 DP，直接逐位貼著 n 用排列數計算。

### 詳解

**為什麼直覺做法不夠**。逐一檢查 1 到 n 是 O(n log n)，n = 2 × 10⁹ 時太慢。可以先觀察答案的上限：特殊整數最多 10 位，總數是 Σ 9 · P(9, L − 1)，約 8.9 × 10⁶，可以全部列舉再數 ≤ n 的有幾個，但這需要 backtracking 產生近千萬個數，在 Python 中仍然很慢，也不是面試官要的答案。真正的做法是數位 DP：一大群數共享前綴時，用一次計算處理掉整群。

**做法一：數位 DP 加上 bitmask**。這是 24.5 節模板最直接的應用，state 是已用數字的 mask。在第 pos 位填 d：若 started 為 False 且 d = 0，代表仍是前導零，mask 不變；否則 d 必須不在 mask 中，新的 mask 是 `mask | 1 << d`。終點時 started 為 True 才算一個數（排除 0）。狀態數是 10 位 × 2¹⁰ 個 mask × 2 × 2，實際可達的遠少於此，每個狀態試 10 個數字。這個做法的好處是完全照模板寫，不需要任何組合數學，換成「每個數字最多用兩次」之類的變形時（F4）也只要改 state。

**做法二：組合計數**。觀察：不 tight 之後，剩下 k 位可以從沒用過的數字中任意排列，方法數 P(10 − u, k) 只取決於已用數字的「個數」u，和是哪些數字無關，所以 bitmask 中的資訊大部分是多餘的。這讓我們可以直接計算。比 n 短、長度 L 的特殊整數：首位 9 種（1 到 9），之後每一位從剩下的數字中選，共 9 · P(9, L − 1)。和 n 等長的：由左到右貼著 n，在第 i 位填一個比 `s[i]` 小、而且還沒被前綴用過的數字（首位不能是 0），之後 L − 1 − i 位自由排列，方法數 P(10 − i − 1, L − 1 − i)；然後把 `s[i]` 加入已用集合繼續。若 `s[i]` 已經被用過，代表 n 的前綴本身就重複了，沒有任何等長的數能繼續貼著 n，停止；若一路走完，n 本身也是特殊整數，加 1。

```text
n = 4381，s = "4381"，L = 4

比 n 短：
長度 1：9                     （1–9）
長度 2：9 × P(9, 1) = 81
長度 3：9 × P(9, 2) = 648
小計 738

和 n 等長，逐位貼著 n：
i  s[i]  已用     可填的較小數字（首位不能是 0）   個數   × P(10−i−1, 3−i)    貢獻
0   4    {}       1, 2, 3                           3      × P(9, 3) = 504     1512
1   3    {4}      0, 1, 2                           3      × P(8, 2) = 56       168
2   8    {4,3}    0, 1, 2, 5, 6, 7                  6      × P(7, 1) = 7         42
3   1    {4,3,8}  0                                 1      × P(6, 0) = 1          1
走完：4381 本身各位不同 → +1

總計 738 + 1512 + 168 + 42 + 1 + 1 = 2462
```

第 0 位填 1、2 或 3 時，數字已經小於 4000，後面三位從剩下的 9 個數字中挑 3 個排列，P(9, 3) = 504。第 2 位要填比 8 小的數字，但 3 和 4 已經被前綴 `43` 用掉，剩下 0、1、2、5、6、7 共 6 個。這一步展示了為什麼等長部分必須追蹤「哪些」數字用過（因為要判斷比 `s[i]` 小的數字中哪些可用），而自由部分只需要知道「幾個」用過。

### 解法

```python
import random
from functools import cache
from math import perm


def count_special_numbers(n: int) -> int:
    """組合計數：比 n 短的直接用排列數，等長的逐位貼著 n 走。"""
    s = str(n)
    L = len(s)
    total = sum(9 * perm(9, length - 1) for length in range(1, L))   # 首位 1–9，之後從剩下 9 個選
    used = set()
    for i, ch in enumerate(s):
        cur = int(ch)
        start = 1 if i == 0 else 0                                    # 首位不能是 0
        smaller = sum(1 for d in range(start, cur) if d not in used)  # 這一位填比 cur 小、沒用過的數字
        total += smaller * perm(10 - i - 1, L - i - 1)                # 後面 L-i-1 位從剩下的數字中排列
        if cur in used:                                               # n 的前綴本身已經重複，tight 路徑中斷
            return total
        used.add(cur)
    return total + 1                                                  # n 本身的位數各不相同


def count_special_dp(n: int) -> int:
    """24.5 節模板：state 是已用數字的 bitmask。"""
    s = str(n)

    @cache
    def go(pos: int, mask: int, tight: bool, started: bool) -> int:
        if pos == len(s):
            return int(started)
        limit = int(s[pos]) if tight else 9
        total = 0
        for d in range(limit + 1):
            nt = tight and d == limit
            if not started and d == 0:
                total += go(pos + 1, mask, nt, False)          # 前導零不佔用數字 0
            elif not mask >> d & 1:
                total += go(pos + 1, mask | 1 << d, nt, True)
        return total

    return go(0, 0, True, False)


def brute(n):
    return sum(1 for x in range(1, n + 1) if len(set(str(x))) == len(str(x)))


assert count_special_numbers(20) == 19          # 只有 11 不合法
assert count_special_numbers(5) == 5
assert count_special_numbers(135) == 110
assert count_special_numbers(1) == 1
assert count_special_numbers(2 * 10**9) == count_special_dp(2 * 10**9) == 5974650
for n in list(range(1, 3000)) + [random.randint(1, 10**5) for _ in range(5)]:
    assert count_special_numbers(n) == count_special_dp(n) == brute(n)
print("all tests passed")
```

### 複雜度與邊界

組合計數：時間 O(L²)，L ≤ 10，每一位掃一次 0 到 9；空間 O(L)。數位 DP：可達狀態最多 L × 2¹⁰ × 4，每個試 10 個數字，約 4 × 10⁵ 次運算；空間是快取大小。邊界情況：n 是一位數時「比 n 短」的部分為 0；首位的「較小數字」從 1 開始，若從 0 開始會把以 0 開頭的等長數（其實是更短的數）重複計算；n 的前綴出現重複（例如 n = 1123 的 `11`）時，要在加入已用集合之前檢查並提早回傳；題目限制 n ≤ 2 × 10⁹，最多 10 位；若要支援更大的 n，先令 `n = min(n, 9876543210)`，因為最大的特殊整數就是 9876543210，任何 11 位以上的數都必有重複數字，不會新增答案。

### Follow-up

> [!question]- F1. 如果要數的是「至少有一個重複數字」的整數呢（1012. Numbers With Repeated Digits）？
> 就是補集：`n − count_special_numbers(n)`。這題在 LeetCode 上是獨立的 Hard，但和本題完全等價。面試中若被問到 1012，先說「直接數有重複的很難，因為重複可以發生在任何兩個位置；改數沒有重複的，再用補集」，這是組合計數中最常用的轉換。時間 O(L²)。

> [!question]- F2. 如果要的是 [lo, hi] 區間內的特殊整數個數呢？
> `f(hi) − f(lo − 1)`，f(0) 定義為 0。要注意 lo = 1 時 `str(0)` 是 `"0"`：組合計數版本會把它當成一位數處理，首位「較小數字」的範圍 `range(1, 0)` 是空的，然後把 0 加入已用集合並在最後 `+1`，錯誤地回傳 1。所以要明確寫 `if x <= 0: return 0`；數位 DP 版本因為有 started，0 自然不計入。這是數位 DP 中典型的 off-by-one 陷阱。

> [!question]- F3. 如果要找第 k 小的特殊整數呢？
> 先決定長度：依序扣掉長度 1、2、… 的個數 9 · P(9, L − 1)，直到 k 落在某個長度 L 內。接著由左到右決定每一位：依序嘗試還沒用過的數字 d（首位從 1 開始），以 d 開頭的完成方式有 P(10 − 已用數 − 1, 剩下位數) 種；若 k 不超過它，就選 d，否則 k 減去它、試下一個 d。時間 O(L · 10)。這和核心題 3 F3、核心題 5 F3 是同一個「用計數做字典序第 k 個」的手法。

> [!question]- F4. 如果放寬成「每個數字最多出現兩次」呢？
> bitmask 不夠了，state 要記每個數字用了 0、1、2 次中的哪一種，可以用 3 進位編碼成 0 到 3¹⁰ − 1 的整數，數位 DP 的狀態數變成 L × 59049 × 4。組合計數的對稱性仍然可以利用：不 tight 時，完成方式數只取決於「有幾個數字還剩 2 次、幾個還剩 1 次」，所以自由分支可以用 (a, b) 兩個計數當 state 做一個小 DP，總狀態只有 11 × 11 × L。面試中提出「先用通用的計數向量 state 寫對，再用對稱性壓縮」是很好的思路展示。

> [!question]- F5. 為什麼組合計數可以不用 bitmask，而數位 DP 的版本需要？能不能把 DP 的狀態也縮小？
> 因為兩者處理的資訊不同。在 tight 的路徑上，要知道「哪些」數字用過，才能判斷比 `s[i]` 小的數字中哪些可填，但 tight 路徑只有一條，所以組合計數直接用一個 set 追蹤即可。在不 tight 的分支中，只需要知道「幾個」數字用過，方法數有封閉公式。所以可以把 DP 的 state 改成 (pos, 已用個數, tight, started)，但 tight 時仍需要真正的集合；實務上就是組合計數的寫法。這說明了數位 DP 的一個通用優化：**不 tight 的狀態與 N 無關，若它們的答案只依賴 state 的某個摘要，就能大幅減少狀態**。

### 心得

關鍵突破是把「位數互不相同」轉成數位 DP 的 state：已用數字的 bitmask，加上處理前導零的 started；進一步觀察到不 tight 時只需要「用了幾個」，就能用排列數直接算出自由分支。它是本章兩種技巧的交會點：數位 DP 的骨架（核心題 5）配上 bitmask 的 state（核心題 3、4），而 started 的重要性在這題最明顯，因為數字 0 本身也是要追蹤的元素。面試時建議先寫數位 DP 版本（模板化、不易錯），用 n = 20 或 n = 135 驗證，再提出組合計數作為優化，並說明兩者的關係；被追問 1012 時用補集一句話回答。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 樹上選點（獨立集、覆蓋） | 樹上每個節點選或不選，相鄰節點互相限制 | 後序回傳每個節點的少數狀態（選／不選／被覆蓋） | 核心題 1（337）、968（第 12 章難題 3）、2646 |
| 樹上路徑與直徑 | 經過某節點的最長路徑、最大路徑和 | 回傳「往下的最佳單鏈」，在節點上合併兩條 | 543、124（第 12 章）、2246 |
| 樹上背包 | 子樹內選 k 個、預算限制 | 子樹狀態多一維數量，合併是 max-plus 卷積，O(n · k) | 核心題 1 F2、有依賴關係的背包（選子節點必須先選父節點） |
| Rerooting（換根） | 對每個節點都問「以它為根」或「子樹外」 | 先後序算子樹內、再前序傳子樹外；可撤銷用減法，不可撤銷用 top-2 | 難題 1（834）、310（第 16 章）、2458（第 12 章）、2581 |
| 位元性質的遞推 | 對 0…n 每個數算位元相關的量 | `i >> 1` 或 `i & (i − 1)` 指向更小的數 | 核心題 2（338）、subset sum 表 |
| 集合狀態（一次加一個） | n ≤ 15–20 的排列、指派、分組，下一步只看已用集合 | `dp[mask]`，O(2ⁿ · n)；必要時用支配關係壓縮附加資訊 | 核心題 3（526）、核心題 4（1986）、1879、1125 |
| 子集合枚舉（一次加一組） | 把元素分成若干組，每組是否合法可獨立判斷 | `sub = (sub − 1) & mask`，O(3ⁿ)；固定最低位避免重複 | 核心題 4 做法二、1723、1655、1494（第 16 章提過） |
| TSP 型 `dp[mask][last]` | 成本取決於相鄰兩個元素，要拜訪／串接全部 | Held–Karp，O(2ⁿ · n²)，記 parent 還原 | 難題 2（943）、847（第 15 章難題 4）、24.4 節的 TSP |
| Profile DP（逐列 bitmask） | 格子寬度 ≤ 8–10，衝突只跨相鄰列 | `dp[row][mask]`，合法 mask 常是 Fibonacci 個 | 難題 3（1349）、1411、1659 |
| 數位 DP（計數型） | 「[1, N] 中有幾個數……」，N 到 10¹⁸ | (pos, state, tight, started)，區間用 f(R) − f(L − 1) | 核心題 5（902）、難題 5（2376）、1012、600 |
| 數位 DP（累加型） | 「所有 ≤ N 的數的某個量的總和」 | 終點回傳累積量；或逐位貢獻法 | 難題 4（233）、核心題 2 F1、1067 |
| 數位 DP ＋ 其他 state | 位數條件再加整除、相鄰關係、集合 | state 加上餘數、上一位、已用 mask | 核心題 5 F5、2376、2719 |

**下限與上限**。三種技巧最簡單的形式都很短：337 是每個節點回傳兩個數；338 是一行遞推；902 是逐位貼著 n 走的乘法。中間層的難點在**狀態設計**：526 要看出「已用集合」決定了下一個位置；1986 要看出 `(session 數, 負載)` 的字典序支配關係，或改用子集合枚舉；834 要寫出換根公式。上限的題目難在三個地方，常常同時出現：第一，**狀態需要額外的一維**，例如 943 的 last、1349 的整列 profile、2376 的已用 mask；第二，**要證明化約是對的**，例如 943 的「最短解一定是排列加最大重疊」、1986 的支配關係、1349 中「衝突只跨一列」；第三，**邊界與還原**，例如數位 DP 的 started 與 f(L − 1)、TSP 型 DP 的 parent 還原、樹 DP 在深樹上的遞迴深度。

**與其他 pattern 的關係**。樹 DP 是第 12 章 binary tree 後序走訪的延伸：第 12 章的「回傳高度、回傳單鏈和」只回傳一個數，本章回傳一組狀態；968 Binary Tree Cameras（第 12 章難題 3）是三狀態的樹 DP。Bitmask DP 和第 19 章 backtracking 處理的是同一類「n 很小的組合問題」：backtracking 在排列樹上展開，bitmask DP 把「相同集合」的節點合併，當子問題大量重複時 DP 指數級地更快，但需要輸出所有解時只能 backtracking。TSP 型 DP 和第 15 章的狀態 BFS（847、864）是同一張 (node, mask) 狀態圖：無權用 BFS、有權用 DP 或 Dijkstra（第 18 章）。數位 DP 和第 7 章 prefix sum 共享「區間 = 兩個前綴相減」的想法，和第 28 章的位元與數學題共享「逐位計數」的技巧；338 F1 與 233 是同一個貢獻法在二進位與十進位上的版本。

**容易混淆之處**。第一，看到 n ≤ 20 不一定是 bitmask DP：如果下一步需要知道完整的順序（不只是集合），2ⁿ 的狀態不夠，要確認「集合 + 少量附加資訊」足以決定後續。第二，bitmask DP 的「一次加一個」與「子集合枚舉」不能隨便互換：前者 O(2ⁿ · n) 但需要附加資訊可以被壓縮（1986 的支配關係），後者 O(3ⁿ) 但更通用（1986 F3）。第三，數位 DP 的 state 對前導零是否敏感因題而異：位數和不敏感，相鄰限制、相異數字、數字 0 的計數都敏感，一律帶著 started 最安全。第四，rerooting 的合併若不能撤銷（max、min），用減法會得到錯的答案，要改用 top-2 或前綴／後綴。

## 本章重點整理

- 三種技巧共用同一個問題：「做完一部分之後，後面只需要知道什麼？」樹 DP 把它切在子樹邊界、bitmask DP 壓成集合、數位 DP 切在位數邊界。
- 樹 DP：先問父節點需要知道孩子的什麼，讓每個節點回傳一個 tuple（例如 337 的 `(take, skip)`），後序合併；不同子樹互不相交，所以可以直接相加。
- 深樹不要用遞迴：BFS 得到「父先於子」的順序，倒序走就是後序，正序走就是前序。
- Rerooting：第一遍後序算子樹內資訊，第二遍前序把子樹外的資訊傳下去；834 的換根公式 `ans[u] = ans[p] − size[u] + (n − size[u])`，max 類合併要用 top-2。
- 位元操作的基本零件：`mask >> i & 1`、`mask | 1 << i`、`mask & -mask`、`mask & (mask − 1)`；338 的 `ans[i] = ans[i >> 1] + (i & 1)` 是所有子集合表格的雛形。
- Bitmask DP 按數值由小到大處理 mask 就是合法的拓撲順序，因為子集合在數值上不比原集合大。
- 「一次加一個」是 O(2ⁿ · n)（526、1986 做法一）；「子集合枚舉」`sub = (sub − 1) & mask` 總共 3ⁿ（1986 做法二），n ≤ 14–16 才可行。
- 成本取決於相鄰兩個元素時用 `dp[mask][last]`（TSP、943），O(2ⁿ · n²)，記 parent 才能還原答案。
- 格子寬度小、衝突只跨相鄰列時，用 profile DP `dp[row][mask]`；同列不相鄰的合法 mask 只有 Fibonacci 個。
- 數位 DP 模板：`go(pos, state, tight, started)`；只有 `tight and d == limit` 才延續 tight；前導零階段不更新 state；終點時 started 才算一個數。
- 區間計數一律用 `f(R) − f(L − 1)`，並確認 `f(0) = 0`；累加型（233）在終點回傳累積量，也可以用逐位貢獻法 O(log n) 算出。
- 不 tight 的狀態與 N 無關；若它們的答案只依賴 state 的摘要（2376 的「用了幾個數字」），就能用組合公式取代 DP。
- 看到 n ≤ 12–20 先想指數級狀態，看到 N ≤ 10¹⁸ 而且條件只和十進位寫法有關先想數位 DP，看到樹加上「每個節點都要答案」先想 rerooting。
