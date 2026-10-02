---
chapter: 17
title: Union-Find
part: 3
---

# 第 17 章　Union-Find

> [!abstract] 本章地圖
> **一句話**：把「誰和誰屬於同一群」表示成一片森林，每一群用樹根當代表；合併兩群只要改一個指標，查詢兩點是否同群只要比較兩個根，兩種操作都近乎 O(1)。
>
> **辨識訊號**：
> - 關係是**無向、可傳遞**的：朋友的朋友是朋友、相等的相等是相等、共用 email 的帳號是同一人
> - 邊或關係**一條一條加進來**，過程中要反覆問「這兩點連通了嗎」「現在有幾群」
> - 「加入哪一條邊時第一次形成環」「哪條邊是多餘的」
> - 「最小的門檻 t，讓起點和終點連通」，或查詢帶著「只能用權重 < limit 的邊」這種限制
> - 操作是**刪除**（打掉磚塊、拆掉邊），而刪除可以離線知道全部順序
> - 「同時讓兩種角色都連通」「最小生成樹」這類需要逐邊決定「要不要用」的題目
>
> **核心題**：547、684、721、990、1319
>
> **難題**：685、778、803、1579、1697

## 17.1 這個 Pattern 解決什麼問題

先看一個小問題。社群網站有 n 個使用者，交友紀錄一筆一筆送進來：「3 和 7 成為朋友」「7 和 2 成為朋友」……每收到一筆，產品經理都想知道兩件事：任意兩個人現在是否在同一個朋友圈（朋友的朋友也算），以及現在一共有幾個朋友圈。最直接的做法是每次查詢都從其中一人出發跑一次 BFS 或 DFS（第 15 章），看能不能走到另一個人，單次 O(n + m)，m 筆紀錄、q 次查詢就是 O(q · (n + m))，紀錄一多就完全跑不動。

瓶頸在於每次查詢都從零開始重新探索整張圖，可是兩次查詢之間圖只多了一條邊，之前算過的連通資訊全部被丟掉了。換個角度想：我們其實不需要知道「怎麼走過去」，只需要知道「是不是同一群」。如果每一群都有一個公認的代表，查詢就變成「兩人的代表是不是同一個」；新增一條邊時，若兩人原本不同群，就讓其中一群的代表改認另一群的代表為老大，兩群就合成一群。這就是 union-find（並查集，也叫 disjoint set union，DSU）。

Union-find 用一片森林來實作這個想法：每個元素有一個 `parent` 指標，指向同群中的另一個元素，沿著指標一路往上走，最後會停在指向自己的根，根就是這一群的代表。`find(x)` 回傳 x 的根，`union(a, b)` 把 a 的根掛到 b 的根下面。單純這樣做，樹可能退化成一條長鏈，`find` 變成 O(n)；加上兩個優化（path compression 路徑壓縮、union by size 按大小合併）之後，每次操作的攤銷成本是 O(α(n))，α 是反 Ackermann 函數，在任何實際的 n 下都不超過 4，可以當作常數。

這個資料結構的能力邊界很清楚，也正是辨識它的關鍵：它擅長**只增不減**的等價關係，支援「合併」與「查詢是否同群」，以及在根上維護整群的統計量（大小、最小值、和）。它不擅長刪除（拆開一群）、不知道群內的路徑長什麼樣、也不處理有方向的關係。本章所有題目都在這個邊界內，難題則示範三個把問題「推回邊界內」的技巧：把刪除倒過來變成加入（803）、把門檻排序後逐步加入（778、1697）、用多個 union-find 分別描述不同角色（1579）。

## 17.2 辨識訊號

| 題目特徵 | 為什麼是 union-find | 本章哪一題 |
|---|---|---|
| 給一張圖（矩陣或邊列表），問有幾個連通元件 | 每條邊做一次 union，成功合併就讓元件數減一 | 核心題 1（547）、核心題 5（1319） |
| 依序加入邊，問「哪一條邊第一次形成環」 | union 時兩端已經同根，代表這條邊閉合了一個環 | 核心題 2（684）、難題 1（685） |
| 物件之間透過「共用某個屬性」而被視為同一個 | 共用屬性是傳遞的等價關係，把物件和屬性連起來即可 | 核心題 3（721） |
| 一堆 `==` 與 `!=` 限制，問是否可能同時成立 | `==` 是等價關係（合併），`!=` 只需事後檢查兩邊不同根 | 核心題 4（990） |
| 「最少加幾條邊／搬幾條線才能全部連通」 | 答案由元件數決定：k 個元件需要 k − 1 條邊 | 核心題 5（1319） |
| 「時間 t 之後才能通過」「最小門檻讓兩點連通」 | 把格子或邊依門檻排序後逐一加入，第一次連通的門檻就是答案 | 難題 2（778）、難題 5（1697） |
| 依序刪除東西，每次問「掉了多少」 | union-find 不支援刪除；離線倒序後刪除變成加入 | 難題 3（803） |
| 兩種角色各自要連通、有共用的邊 | 用兩個 union-find，共用邊優先，Kruskal 式的貪婪 | 難題 4（1579） |

一個實用的反向檢查：如果題目要的是**最短距離或實際路徑**，union-find 給不出來，要用 BFS 或 Dijkstra（第 15、18 章）；如果關係是**有方向**的（a 依賴 b 不代表 b 依賴 a），要用拓撲排序（第 16 章）；如果圖是一次給定、只問一次連通元件，BFS／DFS 和 union-find 都可以，選你最不容易寫錯的那一個。Union-find 真正的優勢出現在「邊陸續加入、查詢穿插其中」的情境。

## 17.3 模板與原理：森林、根與兩個優化

全書的 union-find 都以下面這份為準：用陣列存 `parent` 與 `size`，`find` 用迭代寫法做 path compression，`union` 按大小合併並回傳「是否真的合併了」，同時維護集合數 `count`。

```python
import random
from collections import deque


class DSU:
    def __init__(self, n: int):
        self.parent = list(range(n))   # parent[x] == x 代表 x 是根
        self.size = [1] * n            # 只有根的 size 有意義
        self.count = n                 # 目前的集合數

    def find(self, x: int) -> int:
        root = x
        while self.parent[root] != root:       # 第一趟：走到根
            root = self.parent[root]
        while self.parent[x] != root:          # 第二趟：沿路直接指向根（path compression）
            nxt = self.parent[x]
            self.parent[x] = root
            x = nxt
        return root

    def union(self, a: int, b: int) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False                       # 已在同一集合：這條邊形成環
        if self.size[ra] < self.size[rb]:      # union by size：小樹掛到大樹下
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        self.count -= 1
        return True

    def connected(self, a: int, b: int) -> bool:
        return self.find(a) == self.find(b)


d = DSU(5)
assert d.union(0, 1) and d.union(3, 4)
assert d.connected(0, 1) and not d.connected(1, 3)
assert d.count == 3
assert not d.union(1, 0)                       # 重複合併回傳 False
assert d.union(1, 4) and d.count == 2
assert d.size[d.find(3)] == 4
assert DSU(1).find(0) == 0
big = DSU(200000)
for i in range(199999):                       # 一條長鏈：迭代版 find 不會遞迴過深
    big.union(i, i + 1)
assert big.count == 1 and big.connected(0, 199999)

for _ in range(200):                           # 和 BFS 求連通元件對照
    n = random.randint(1, 12)
    edges = [(random.randrange(n), random.randrange(n)) for _ in range(random.randint(0, 15))]
    dsu = DSU(n)
    for a, b in edges:
        dsu.union(a, b)
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    comp = [-1] * n
    c = 0
    for s in range(n):
        if comp[s] == -1:
            comp[s] = c
            q = deque([s])
            while q:
                u = q.popleft()
                for v in adj[u]:
                    if comp[v] == -1:
                        comp[v] = c
                        q.append(v)
            c += 1
    assert dsu.count == c
    for a in range(n):
        for b in range(n):
            assert dsu.connected(a, b) == (comp[a] == comp[b])
print("all tests passed")
```

**Invariant（不變式）**。任何時刻，森林中的每一棵樹恰好是一個集合；兩個元素同集合，若且唯若沿 `parent` 走上去會到同一個根。一開始每個元素自成一棵樹，自動成立。`union` 只把一棵樹的根接到另一棵樹的根下，兩棵樹合成一棵，其他樹不受影響，所以 invariant 保持。`find` 的 path compression 只把路徑上的節點改成直接指向根，它們仍在同一棵樹、根不變，所以也不破壞 invariant。這也說明了為什麼 `union` 一定要先 `find` 到根再接：如果把非根節點 `a` 直接接到 `b` 下，`a` 原本的父節點和 `a` 之間的連結被切斷，原本的一棵樹就被拆成兩棵，集合被錯誤地拆開。

```text
n = 6，依序 union(0,1)、union(2,3)、union(1,3)、union(4,5)、union(5,3)

union(0,1)：size 相同，1 掛到 0 下        parent: [0 0 2 3 4 5]
union(2,3)：3 掛到 2 下                   parent: [0 0 2 2 4 5]
union(1,3)：find(1)=0、find(3)=2，同大小，2 掛到 0 下
                                          parent: [0 0 0 2 4 5]
            0                 size[0] = 4
           / \
          1   2
              |
              3
union(4,5)：5 掛到 4 下                   parent: [0 0 0 2 4 4]
union(5,3)：find(5)=4（size 2）、find(3)：3 → 2 → 0（size 4）
            path compression 讓 3 直接指向 0；小樹 4 掛到大樹 0 下
                                          parent: [0 0 0 0 0 4]
              0               size[0] = 6，count = 1
           / | | \
          1  2 3  4
                  |
                  5
```

最後一步展示了兩個優化同時作用：`find(3)` 走過 3 → 2 → 0 之後，第二趟把 3 直接改成指向 0，下次再查 3 只要一步；合併時大小為 2 的樹掛到大小為 4 的樹下，而不是反過來，這樣「變深一層」的只有少數的那 2 個節點。

**為什麼兩個優化缺一不可**。只做 union by size：一個節點每次「變深一層」，它所在的樹大小至少翻倍，而樹的大小不超過 n，所以任何節點的深度不超過 log₂ n，`find` 最差 O(log n)。只做 path compression：單次 `find` 可能很長，但走過的路徑都被壓平，攤銷下來 m 次操作是 O(m log n)。兩者同時使用時，Tarjan 證明了 m 次操作總共 O(m · α(n))。面試時說「近乎常數，嚴格來說是反 Ackermann 函數」就夠了，不需要推導；但要能說出只用其中一個優化時是 O(log n)。

**每一行為什麼這樣寫**：

- `find` 用兩趟迭代而不是遞迴：遞迴版 `parent[x] = find(parent[x])` 很短，但在還沒壓縮的長鏈上遞迴深度可達 n，Python 預設的遞迴上限是 1000，n = 10⁵ 時會直接 `RecursionError`。另一個常見的單趟寫法是 path halving：`while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]`，每走一步就讓節點跳過一層，同樣保證 O(α(n))，本章的題解多半用它，因為只有三行。
- `union` 回傳 bool：「這次是否真的合併」幾乎是每一題都要用的資訊，數元件（成功就 `count -= 1`）、找環（失敗就是環）、Kruskal（成功才算用到這條邊）都靠它。
- `size` 只在根上維護：非根節點的 `size` 是過時的值，要查一群的大小一律寫 `size[find(x)]`。
- union by rank（按樹高的上界合併）和 union by size 的效果相同；size 多了一個好處是可以直接回答「這群有多少人」，所以本書一律用 size。

**元素不是 0..n−1 的整數時**。email、字串變數、座標這類 key，有兩種做法：先用 dict 把每個 key 編號成 0..n−1，再用陣列版（核心題 3 就是這樣）；或直接用 dict 當 `parent`，第一次看到 key 時 `parent.setdefault(x, x)`。前者常數較小、也能用 `count`；後者在 key 數量事先不知道時比較方便。

## 17.4 在根上掛資訊：計數、大小與帶權 union-find

因為每一群只有一個根，任何「整群的統計量」都可以存在根上，合併時把兩個根的值合起來即可：大小相加、最小值取 min、元素總和相加、「這群有沒有碰到邊界」取 or。這讓很多題目不需要額外的資料結構。例如難題 3 的 803 需要「目前和天花板相連的磚有幾塊」，就是一個虛擬節點加上根上的 `size`；第 4 章核心題 3（128 Longest Consecutive Sequence）的串流版本，是把 x 和 x ± 1 合併後問最大的 `size`。

更進一步，可以在**每條 parent 邊**上存一個值，表示「我相對於父節點的關係」，稱為帶權 union-find（weighted union-find）。最經典的例子是 399. Evaluate Division：已知 `a / b = 2`、`b / c = 3`，問 `a / c`。把 `ratio[x]` 定義為「x 的值 ÷ parent[x] 的值」，`find` 壓縮路徑時把沿路的比值乘起來，壓縮完 `ratio[x]` 就是「x ÷ 根」；同一群的兩個變數相除，只要 `ratio[a] / ratio[b]`。

```python
import random


class WeightedDSU:
    """ratio[x] = x 的值 ÷ parent[x] 的值；find 後 ratio[x] = x ÷ 根。"""

    def __init__(self):
        self.parent: dict[str, str] = {}
        self.ratio: dict[str, float] = {}

    def add(self, x: str) -> None:
        if x not in self.parent:
            self.parent[x] = x
            self.ratio[x] = 1.0

    def find(self, x: str) -> str:
        p = self.parent[x]
        if p != x:
            root = self.find(p)                  # 先讓 p 直接指向根，ratio[p] = p ÷ 根
            self.ratio[x] *= self.ratio[p]       # x ÷ 根 = (x ÷ p) × (p ÷ 根)
            self.parent[x] = root
        return self.parent[x]

    def union(self, a: str, b: str, value: float) -> None:
        """記錄 a ÷ b = value。"""
        self.add(a)
        self.add(b)
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            # 要讓 ra 掛到 rb 下：ra ÷ rb = (a ÷ b) × (b ÷ rb) ÷ (a ÷ ra)
            self.parent[ra] = rb
            self.ratio[ra] = value * self.ratio[b] / self.ratio[a]

    def query(self, a: str, b: str) -> float:
        if a not in self.parent or b not in self.parent or self.find(a) != self.find(b):
            return -1.0
        return self.ratio[a] / self.ratio[b]


w = WeightedDSU()
w.union("a", "b", 2.0)      # a / b = 2
w.union("b", "c", 3.0)      # b / c = 3
assert abs(w.query("a", "c") - 6.0) < 1e-9
assert abs(w.query("c", "a") - 1 / 6) < 1e-9
assert w.query("a", "x") == -1.0
assert abs(w.query("b", "b") - 1.0) < 1e-9
for _ in range(200):
    vals = {ch: random.uniform(0.5, 5) for ch in "pqrstu"}
    dsu = WeightedDSU()
    names = list(vals)
    for _ in range(8):
        a, b = random.sample(names, 2)
        dsu.union(a, b, vals[a] / vals[b])
    for a in names:
        for b in names:
            r = dsu.query(a, b)
            if r != -1.0:
                assert abs(r - vals[a] / vals[b]) < 1e-6
print("all tests passed")
```

合併時的公式是唯一需要推的地方：我們知道 `a ÷ ra`（`ratio[a]`）、`b ÷ rb`（`ratio[b]`）與 `a ÷ b`（value），要求 `ra ÷ rb`。把它寫成 `(ra ÷ a) × (a ÷ b) × (b ÷ rb)`，就是 `value × ratio[b] / ratio[a]`。同一個框架把「乘法」換成「加法」就是差分約束（「x 比 y 大 3」），換成 XOR 就是奇偶性（「x 和 y 顏色不同」，核心題 4 的 F4 與二分圖判定）。這裡用遞迴寫 `find` 是為了讓「先壓縮父節點、再更新自己」的順序清楚；n 很大時要改成迭代或調高遞迴上限。

## 17.5 三種進階用法：虛擬節點、依序啟用、離線倒序

本章的難題幾乎都是在基本模板外面套一層「怎麼餵資料給 union-find」的設計。先把三種最常見的設計看清楚，讀難題時就能直接對上。

**虛擬節點**。當題目有一個「特殊的群」（天花板、邊界、水源、所有人都要連到的總部），與其在根上記錄「這群有沒有碰到它」，不如多開一個編號 n 代表它，把所有屬於它的元素和這個節點 union。之後「x 是否碰到天花板」就是 `connected(x, roof)`，「碰到天花板的有幾個」就是 `size[find(roof)] - 1`。第 15 章核心題 5（130 Surrounded Regions）的 union-find 解法、難題 3（803）都用這招。

**依序啟用（排序後逐一加入）**。題目問「最小的門檻 t，使得 s 和 t 連通」，或每個查詢帶著「只能用權重 < limit 的邊」。觀察是：門檻越大，可用的邊（或格子）越多，連通性只會變好、不會變差，正是 union-find 擅長的只增不減。所以把邊或格子依門檻排序，從小到大加入；第一次讓 s、t 同根時的門檻就是答案（778），或把查詢也依 limit 排序，處理到某個查詢時恰好加入所有 < limit 的邊（1697）。這和 Kruskal 最小生成樹（第 18 章核心題 5）是同一個掃描。

**離線倒序**。union-find 不支援「拆開」，可是如果所有刪除操作事先都知道（離線），就可以先把要刪的東西全部刪掉，得到最終狀態，再**倒著**一個一個加回去。倒著看，每一步都是加入，union-find 就能處理；每一步「加回去前後的差異」恰好對應正向時「刪除造成的變化」。難題 3（803）是代表題，1970 Last Day Where You Can Still Cross、2382 Maximum Segment Sum After Removals 也是同一招。

```text
三種設計對應的「餵資料」方式

虛擬節點         依序啟用（778）                 離線倒序（803）
  roof           門檻 t: 0 1 2 3 4 …            正向：打掉 h1, h2, h3
 / | \           每到一個 t 就加入               倒向：先全打掉，再放回 h3, h2, h1
a  b  c          高度 = t 的格子並 union          放回 h_i 時 roof 群變大多少
                 第一次 find(s)==find(t) 停下     = 正向打掉 h_i 時掉了多少（再減 1）
```

**和 BFS／DFS 怎麼選**。一次給定的靜態圖，問連通元件或某兩點是否連通，BFS／DFS 是 O(n + m)，union-find 是 O(m · α(n))，兩者等價，選熟悉的。邊陸續加入、查詢穿插時，union-find 每次 O(α(n))，BFS 每次 O(n + m)，union-find 完勝。需要距離、路徑、層數時，只能用 BFS。需要處理有向關係時，union-find 不適用。有刪除且必須線上回答時，兩者都不好，要用更進階的結構（離線分治、link-cut tree），面試中幾乎不會要求寫出來，但要能說出「union-find 不支援刪除」。

## 17.6 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| `union` 時直接寫 `parent[a] = b`，沒有先找根 | 原本同一群的元素被拆開，元件數算錯，而且很難重現 | 一律 `parent[find(a)] = find(b)`，或呼叫封裝好的 `union` |
| 遞迴版 `find` 遇到長鏈 | n = 10⁵ 時 `RecursionError` 或極慢 | 用迭代的兩趟壓縮或 path halving |
| 比較 `parent[a] == parent[b]` 判斷同群 | 路徑還沒壓縮時，同群的節點父節點不同，誤判為不同群 | 一定比較 `find(a) == find(b)`；最後統計分組時也要對每個元素呼叫 `find` |
| 讀非根節點的 `size` | 拿到過時的大小 | 一律 `size[find(x)]` |
| 元件數忘記只在「真的合併」時減一 | 重複邊或環讓元件數變成負的 | `union` 回傳 bool，成功才 `count -= 1` |
| 節點編號從 1 開始卻開了大小 n 的陣列 | `IndexError`，或把節點 0 誤算成一個元件 | 開 `n + 1` 個位置，統計時從 1 開始；或先把輸入減一 |
| 990 這類題目把 `==` 和 `!=` 混在同一趟處理 | 先檢查 `a != b` 時兩者還沒被合併，誤判為可行 | 先處理所有「合併」類限制，再檢查所有「不合併」類限制 |
| 803 這類倒序題沒區分「打在空格」 | 把原本就是空格的位置當成磚加回去，多算掉落數 | 移除時用減一標記，加回時只有恢復成 1 的才算 |
| 依門檻排序時把 `<` 寫成 `<=` | 1697 這種「嚴格小於 limit」的查詢多加了一條邊 | 先確認題目是嚴格還是非嚴格，寫成 `while edges[k][2] < limit` |

## 核心題 1｜547. Number of Provinces｜Medium

### 題目

有 n 座城市，用一個 n × n 的 0／1 矩陣 `is_connected` 描述它們之間的直接道路：`is_connected[i][j] == 1` 代表城市 i 和 j 之間有道路直接相連。矩陣是對稱的，對角線全是 1（城市和自己相連）。如果 a 和 b 直接相連、b 和 c 直接相連，則 a 和 c 間接相連。一個「省」是一群直接或間接相連的城市，而且和群外的城市都不相連。請回傳省的個數。限制：`1 <= n <= 200`。

- 範例 1：`is_connected = [[1, 1, 0], [1, 1, 0], [0, 0, 1]]`，城市 0 和 1 相連、2 獨立，回傳 `2`。
- 範例 2：`is_connected = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]`，三座城市互不相連，回傳 `3`。
- 範例 3：`[[1, 0, 0, 1], [0, 1, 1, 0], [0, 1, 1, 1], [1, 0, 1, 1]]`，邊有 0–3、1–2、2–3，四座城市全部連成一省，回傳 `1`；注意 0 和 1 沒有直接相連，是透過 3、2 間接相連。
- 範例 4（邊界）：`[[1]]`，只有一座城市，回傳 `1`。

### 思路

這題的本質是「無向圖的連通元件數」，圖用鄰接矩陣表示。最直接的做法是 DFS：從每個還沒拜訪過的城市出發，把能走到的城市全部標記，出發的次數就是省的個數。因為圖是鄰接矩陣，拜訪一個城市時要掃過整列 n 個位置找鄰居，總時間 O(n²)，這已經是讀完輸入的下限，所以 DFS 本身就是最佳解。

用 union-find 寫同樣是 O(n² · α(n))。思路是：一開始假設每座城市自成一省，省數 = n；掃過矩陣的上三角，每看到一個 1 就把 i、j 合併，**只有在兩者原本不同省時**才讓省數減一。為什麼只看上三角？因為矩陣對稱，`(i, j)` 和 `(j, i)` 描述同一條路，對角線則是城市自己，都不會帶來新的合併。這題當作 union-find 的第一題，重點是建立兩個習慣：用「成功合併的次數」來數元件，以及知道 union-find 和 DFS 在靜態圖上是等價的選擇。

關鍵的 invariant 是：處理完前若干條路之後，`provinces` 等於「只用這些路時的連通元件數」。每條新路若連接兩個不同元件，元件數恰好少一；若兩端已在同一元件，這條路是多餘的，元件數不變。所以最後的 `provinces` 就是答案。

```text
範例 3：is_connected 的上三角中值為 1 的位置：(0,3)、(1,2)、(2,3)

初始       parent: [0 1 2 3]   省數 4      {0} {1} {2} {3}
(0,3)      find(0)=0、find(3)=3，不同 → 合併，3 掛到 0 下
           parent: [0 1 2 0]   省數 3      {0,3} {1} {2}
(1,2)      find(1)=1、find(2)=2，不同 → 合併，2 掛到 1 下
           parent: [0 1 1 0]   省數 2      {0,3} {1,2}
(2,3)      find(2)=1、find(3)=0，不同 → 合併（同大小，0 掛到 1 下）
           parent: [1 1 1 0]   省數 1      {0,1,2,3}

最後再 find(3)：3 → 0 → 1，path halving 讓 3 直接指向 1
```

第三步是本題最重要的一步：城市 2 和 3 的直接道路，把兩個已經各有兩座城市的省合併起來。此時 `find(2)` 和 `find(3)` 分別找到兩省的代表 1 和 0，合併的是**兩個根**，而不是 2 和 3 本身；如果直接寫 `parent[2] = 3`，城市 1 就會和 2 失去連結，省數算錯。

### 解法

```python
import random


def find_circle_num(is_connected: list[list[int]]) -> int:
    n = len(is_connected)
    parent = list(range(n))
    size = [1] * n

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]      # path halving：每走一步就跳過一層
            x = parent[x]
        return x

    provinces = n
    for i in range(n):
        for j in range(i + 1, n):              # 矩陣對稱，只看上三角
            if is_connected[i][j]:
                ri, rj = find(i), find(j)
                if ri != rj:
                    if size[ri] < size[rj]:
                        ri, rj = rj, ri
                    parent[rj] = ri
                    size[ri] += size[rj]
                    provinces -= 1
    return provinces


def find_circle_num_dfs(is_connected: list[list[int]]) -> int:
    n = len(is_connected)
    seen = [False] * n
    count = 0
    for s in range(n):
        if seen[s]:
            continue
        count += 1
        seen[s] = True
        stack = [s]
        while stack:
            u = stack.pop()
            for v in range(n):
                if is_connected[u][v] and not seen[v]:
                    seen[v] = True
                    stack.append(v)
    return count


assert find_circle_num([[1, 1, 0], [1, 1, 0], [0, 0, 1]]) == 2
assert find_circle_num([[1, 0, 0], [0, 1, 0], [0, 0, 1]]) == 3
assert find_circle_num([[1]]) == 1
assert find_circle_num([[1, 0, 0, 1], [0, 1, 1, 0], [0, 1, 1, 1], [1, 0, 1, 1]]) == 1
for _ in range(300):
    n = random.randint(1, 9)
    m = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if random.random() < 0.2:
                m[i][j] = m[j][i] = 1
    assert find_circle_num(m) == find_circle_num_dfs(m)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n² · α(n))：掃描上三角 n(n − 1)/2 個位置，每個 1 做兩次 `find`。空間 O(n)，只有 `parent` 與 `size`（不含輸入矩陣）。DFS 版本時間 O(n²)、空間 O(n)。邊界情況：n = 1 時迴圈不執行，回傳 1；全部互不相連時省數維持 n；全部相連時恰好成功合併 n − 1 次，省數為 1，其餘的 1 都落在「已同根」的分支。這題的輸入是矩陣，所以不論圖多稀疏都要 O(n²)；若輸入改成邊列表，就是 F2 的情況。

### Follow-up

> [!question]- F1. 如果還要回傳每個省有哪些城市，或最大的省有幾座城市呢？
> 合併完成後，對每座城市呼叫一次 `find(i)`，用 dict 把 i 放進 `groups[find(i)]`，每個 value 就是一省的城市列表，O(n · α(n))。注意不能直接用 `parent[i]` 分組，因為還沒被壓縮的節點的 parent 不一定是根。最大的省則不需要分組：union by size 的 `size[root]` 已經是整群大小，掃過所有根（`parent[i] == i`）取最大值即可，O(n)。如果要在合併過程中隨時回報最大省，就在每次成功合併後更新 `best = max(best, size[ri])`。

> [!question]- F2. 如果城市數 n 到 10⁵，道路改用邊列表 `roads` 給出（m 條）呢？
> 鄰接矩陣會有 10¹⁰ 個位置，根本放不下，所以輸入一定是邊列表。這時 union-find 直接對每條邊做一次 union，時間 O(n + m · α(n))，空間 O(n)，而且**不需要建鄰接串列**；DFS 則要先建 O(n + m) 的鄰接串列，再用迭代的 stack 避免遞迴過深。兩者複雜度相同，union-find 在這裡的實作通常更短，也是面試官希望聽到你主動比較的點。

> [!question]- F3. 如果道路是一條一條修好的，每修好一條就要回報目前的省數呢？
> 這是 union-find 相對 DFS 的真正優勢。維護 `provinces`，每條新路做一次 union，成功就減一，然後回報，每次 O(α(n))，m 條路共 O(m · α(n))。若改用 DFS，每次都要重算 O(n + m)，總共 O(m · (n + m))。這也是 305. Number of Islands II 的結構：格子一格一格變成陸地，每次回報島嶼數（第 15 章核心題 1 的 F2）。

> [!question]- F4. 如果道路會被拆除，拆除後要回報省數呢？
> Union-find 不支援拆開集合。若所有拆除事件事先都知道，就用 17.5 節的離線倒序：先把所有會被拆的路拿掉，建出最終狀態的 union-find，再倒著把路一條一條加回去，倒序時的省數序列反轉後就是正向的答案，總共 O((n + m) · α(n))，難題 3（803）是同一個技巧。若必須線上回答，可以在每次拆除後重跑一次 DFS，O(n + m)；更快的做法需要動態連通性（dynamic connectivity）資料結構，面試中通常只要說出「離線倒序」即可。

> [!question]- F5. 如果矩陣大到放不進記憶體，只能一列一列從磁碟讀入呢？
> Union-find 只需要 O(n) 的記憶體：一次讀入一列 i，對這列中所有 `j > i` 且值為 1 的位置做 union，讀完就丟掉這一列。整個過程只循序讀檔一次，沒有隨機存取。DFS 則必須在拜訪 u 時讀第 u 列，存取順序由搜尋決定，等於對磁碟做隨機讀取，慢很多。這是 union-find 「邊可以用任意順序、只看一次」的性質在外部記憶體上的應用。

## 核心題 2｜684. Redundant Connection｜Medium

### 題目

有一棵 n 個節點（編號 1 到 n）的無向樹，有人在它上面多加了一條邊，這條邊連接兩個不同的節點，而且不和原本的邊重複。給你加邊後的 n 條邊 `edges`（每條 `[a, b]`），請回傳一條可以刪除的邊，使得剩下的 n − 1 條邊恰好形成一棵 n 個節點的樹。如果有多個答案，回傳在 `edges` 中**最後出現**的那一條。限制：`3 <= n <= 1000`，沒有重複的邊。

- 範例 1：`edges = [[1, 2], [1, 3], [2, 3]]`，三條邊構成一個三角形，刪掉任何一條都可以，回傳最後出現的 `[2, 3]`。
- 範例 2：`edges = [[1, 2], [2, 3], [3, 4], [1, 4], [1, 5]]`，環是 1–2–3–4–1，環上的邊依序是 `[1, 2]`、`[2, 3]`、`[3, 4]`、`[1, 4]`，最後出現的是 `[1, 4]`。
- 範例 3：`edges = [[3, 4], [1, 2], [2, 4], [3, 5], [2, 5]]`，環是 2–4–3–5–2，回傳 `[2, 5]`；注意不在環上的 `[1, 2]` 不能刪，刪了 1 就斷開了。

### 思路

先想清楚「可以刪的邊」是哪些。n 個節點、n 條邊的連通圖恰好有一個環；刪掉環上的任何一條邊，剩下的仍然連通而且無環，就是一棵樹；刪掉不在環上的邊（橋），圖會斷成兩塊。所以候選答案就是環上的所有邊，題目要的是其中在輸入裡最後出現的那一條。

暴力解是從最後一條邊往前試：刪掉它，檢查剩下的 n − 1 條邊是否無環（或是否連通），第一個通過的就是答案。每次檢查 O(n)，最多試 n 次，總共 O(n²)，n = 1000 時能過，但沒有利用任何結構。

關鍵觀察：**依輸入順序把邊一條一條加入 union-find，第一條「兩端已經同根」的邊就是答案**。理由是：在它之前的邊都成功合併，形成一片無環的森林；這條邊的兩端在森林裡已經連通，所以它和森林中的那條路徑一起構成圖中唯一的環。環上的其他邊都在它之前出現，所以它就是環上最後出現的邊。這個論證同時保證了「找到就可以立刻回傳」，不需要掃完所有邊。

```text
範例 2：edges = [1,2] [2,3] [3,4] [1,4] [1,5]

加入邊    find 兩端        結果         目前的森林
[1,2]     1 vs 2  不同     合併         1-2
[2,3]     2 vs 3  不同     合併         1-2-3
[3,4]     3 vs 4  不同     合併         1-2-3-4
[1,4]     1 vs 4  相同！   回傳 [1,4]   1-2-3-4 已經把 1 和 4 連起來了
                                        [1,4] 閉合了環 1-2-3-4-1
（[1,5] 不需要再看）
```

第四步時，1 和 4 已經透過 2、3 連通，所以 `[1, 4]` 是多餘的。環上的邊 `[1, 2]`、`[2, 3]`、`[3, 4]` 都更早出現，所以 `[1, 4]` 是環上最後一條。若輸入改成 `[1, 4]` 先出現、`[3, 4]` 最後出現，同樣的程式會在 `[3, 4]` 時回傳，答案自動正確。

### 解法

```python
import random


def find_redundant_connection(edges: list[list[int]]) -> list[int]:
    n = len(edges)
    parent = list(range(n + 1))                # 節點編號 1..n

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v in edges:
        ru, rv = find(u), find(v)
        if ru == rv:                           # u、v 早已連通：這條邊閉合了環
            return [u, v]
        parent[ru] = rv
    return []                                  # 依題意不會發生


def brute(edges):
    n = len(edges)
    for k in range(n - 1, -1, -1):             # 從最後一條往前試
        parent = list(range(n + 1))

        def find(x):
            while parent[x] != x:
                x = parent[x]
            return x

        ok = True
        for i, (u, v) in enumerate(edges):
            if i == k:
                continue
            ru, rv = find(u), find(v)
            if ru == rv:
                ok = False
                break
            parent[ru] = rv
        if ok:
            return edges[k]


assert find_redundant_connection([[1, 2], [1, 3], [2, 3]]) == [2, 3]
assert find_redundant_connection([[1, 2], [2, 3], [3, 4], [1, 4], [1, 5]]) == [1, 4]
assert find_redundant_connection([[3, 4], [1, 2], [2, 4], [3, 5], [2, 5]]) == [2, 5]
assert find_redundant_connection([[1, 4], [3, 4], [1, 3], [1, 2], [4, 5]]) == [1, 3]
for _ in range(300):
    n = random.randint(3, 9)
    tree = [[random.randint(1, v - 1), v] for v in range(2, n + 1)]
    while True:
        a, b = random.sample(range(1, n + 1), 2)
        if [a, b] not in tree and [b, a] not in tree:
            break
    edges = tree + [[a, b]]
    random.shuffle(edges)
    assert find_redundant_connection(edges) == brute(edges)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n · α(n))：每條邊兩次 `find`，最多處理 n 條。空間 O(n)。這裡為了簡潔只用了 path halving，沒有 union by size，單次最差仍是攤銷 O(log n)，n = 1000 時完全沒有差別；面試時可以說明「加上 union by size 就是 α(n)」。邊界情況：節點從 1 開始編號，所以 `parent` 開 n + 1 個位置；環可能只由三條邊組成（範例 1），也可能包含所有 n 個節點；多出來的邊可能出現在輸入的任何位置，包括第一條（例如第四個 assert，`[1, 4]` 最先出現但答案是後面閉合環的 `[1, 3]`）。

### Follow-up

> [!question]- F1. 如果要回傳環上的所有邊呢？
> 找到閉合環的邊 `[u, v]` 之後，環上其他的邊就是「之前的森林中 u 到 v 的唯一路徑」。用之前成功合併的邊建鄰接串列，從 u 做一次 DFS／BFS 記錄父節點，走到 v 後沿父節點回溯，就得到路徑上的所有邊，加上 `[u, v]` 就是整個環，O(n)。另一個不需要 union-find 的做法是「剝葉子」：反覆刪除度數為 1 的節點（和第 16 章核心題 4 的 310 同一個想法），最後剩下的節點都在環上，O(n)。

> [!question]- F2. 如果多加的不是一條而是 k 條邊，最少要刪幾條才能變回樹？刪哪些？
> 圖有 n 個節點、n − 1 + k 條邊且連通，一棵生成樹恰好用 n − 1 條，所以必須刪掉恰好 k 條。依序做 union，所有失敗的邊（兩端已同根）就是一組合法的刪除集合：成功的邊構成一棵生成樹。時間 O((n + k) · α(n))。若題目要求「刪除的邊盡量是後面出現的」，這組答案剛好也滿足：它就是用輸入順序當優先序的 Kruskal，被丟掉的是每個環上最後被考慮的邊。

> [!question]- F3. 如果每條邊有權重，要刪掉一條邊讓剩下的樹總權重最小呢？
> 只有環上的邊能刪，刪掉權重最大的那條，剩下的總權重最小。先用本題的方法找到閉合環的邊，再用 F1 的方法求出整個環，取權重最大的一條，O(n)。若有多個附加邊（F2 的情況），問題就變成最小生成樹：依權重由小到大排序後做 Kruskal，被丟掉的邊就是要刪的邊，O(m log m)（第 18 章核心題 5）。

> [!question]- F4. 如果邊是有方向的，原本是一棵有根樹呢？
> 有方向之後，「刪一條邊讓它變回有根樹」多了一個條件：每個節點最多一個父節點。多出來的邊可能造成某個節點有兩個父節點、可能造成有向環，也可能兩者同時發生，單純的「第一條閉合環的邊」不再正確。這就是難題 1（685），要先檢查入度為 2 的節點，再分情況用 union-find 判斷。

## 核心題 3｜721. Accounts Merge｜Medium

### 題目

給一個帳號列表 `accounts`，每個帳號是一個字串陣列，第一個元素是使用者名稱，其餘元素是這個帳號登記的 email。如果兩個帳號有任何一個共同的 email，它們就屬於同一個人；這個關係會傳遞（A 和 B 共用一個 email、B 和 C 共用另一個，A、B、C 都是同一人）。名稱相同不代表同一人，但同一人的所有帳號名稱一定相同。請把屬於同一人的帳號合併，每個人輸出一個列表：第一個是名稱，後面是這個人所有 email **去重並依字典序排序**。人與人之間的輸出順序不限。限制：`1 <= len(accounts) <= 1000`，每個帳號最多 10 個 email，每個 email 最多 30 個字元。

- 範例 1：`[["John", "js@m.co", "john@m.co"], ["John", "js@m.co", "j00@m.co"], ["Mary", "mary@m.co"], ["John", "jb@m.co"]]`，前兩個 John 共用 `js@m.co` 是同一人，第四個 John 沒有共用 email，是另一個人。回傳 `[["John", "j00@m.co", "john@m.co", "js@m.co"], ["Mary", "mary@m.co"], ["John", "jb@m.co"]]`（順序不限）。
- 範例 2（間接相連）：`[["A", "a@x", "b@x"], ["A", "c@x"], ["A", "c@x", "b@x"]]`，第 1 和第 3 個共用 `b@x`，第 2 和第 3 個共用 `c@x`，三個合成一個人：`[["A", "a@x", "b@x", "c@x"]]`。
- 範例 3（邊界）：同一個帳號裡重複登記同一個 email，例如 `[["Z", "z@x", "z@x"]]`，輸出要去重：`[["Z", "z@x"]]`。

### 思路

暴力解是反覆掃描：任兩個帳號的 email 集合有交集就合併，合併後可能和其他帳號產生新的交集，所以要一直重複到不再變化。每一輪最多比較 O(n²) 對，每對比較 O(k)（k 是每個帳號的 email 數），最多要合併 n − 1 次，最差 O(n³ · k)。問題在於「共用 email」是傳遞關係，暴力解靠反覆掃描來追蹤傳遞，浪費大量重複比較。

傳遞關係正是 union-find 的強項。把每個帳號看成一個節點；對每個 email，記住**第一個擁有它的帳號** `owner[email]`；之後再看到同一個 email，就把目前帳號和 `owner[email]` union。這樣不需要比較帳號兩兩之間的交集，每個 email 只會觸發至多一次 union。所有 email 處理完後，同一個根底下的帳號就是同一個人，再把每個 email 依 `find(owner[email])` 分組、排序即可。

為什麼「只和第一個擁有者合併」就夠了？假設 email e 出現在帳號 i₁、i₂、…、i_t（依出現順序），我們做了 union(i₂, i₁)、union(i₃, i₁)……，這些帳號全部被連到 i₁ 所在的集合，等價於把它們兩兩合併。另一種常見的建模是「對 email 做 union-find」：每個帳號把自己的所有 email 和第一個 email 合併。兩者都正確，對帳號做 union-find 的節點數較少（最多 1000），而且 `owner` 這個 dict 同時完成了 email 去重。

```text
範例 1：
帳號 0: John  js@m.co  john@m.co
帳號 1: John  js@m.co  j00@m.co
帳號 2: Mary  mary@m.co
帳號 3: John  jb@m.co

處理順序與 owner：
帳號 0  js@m.co   → owner = 0
        john@m.co → owner = 0
帳號 1  js@m.co   → 已被 0 擁有 → union(1, 0)     parent: [0 0 2 3]
        j00@m.co  → owner = 1
帳號 2  mary@m.co → owner = 2
帳號 3  jb@m.co   → owner = 3

分組（email → find(owner)）：
  js@m.co → 0   john@m.co → 0   j00@m.co → find(1) = 0
  mary@m.co → 2   jb@m.co → 3
輸出：["John", j00, john, js]  ["Mary", mary]  ["John", jb]
```

`j00@m.co` 的擁有者是帳號 1，但分組時用的是 `find(1) = 0`，所以它和帳號 0 的 email 歸在一起。這就是 17.6 節的錯誤「用 `parent` 而不是 `find` 分組」最容易出現的地方：如果之後還有更多合併讓 0 掛到別人底下，`parent[1]` 就不再是根了。

### 解法

```python
import random
from collections import defaultdict


def accounts_merge(accounts: list[list[str]]) -> list[list[str]]:
    n = len(accounts)
    parent = list(range(n))                    # 對「帳號索引」做 union-find

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    owner: dict[str, int] = {}                 # email → 第一個出現它的帳號
    for i, acc in enumerate(accounts):
        for email in acc[1:]:
            if email in owner:
                ri, rj = find(i), find(owner[email])
                if ri != rj:
                    parent[ri] = rj
            else:
                owner[email] = i

    groups: dict[int, list[str]] = defaultdict(list)
    for email, i in owner.items():             # 每個 email 只出現一次，天然去重
        groups[find(i)].append(email)
    return [[accounts[root][0]] + sorted(emails) for root, emails in groups.items()]


def brute(accounts):
    groups = [(acc[0], set(acc[1:])) for acc in accounts]
    changed = True
    while changed:                             # 反覆合併任兩個有交集的群，直到不再變化
        changed = False
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                if groups[i][1] & groups[j][1]:
                    groups[i] = (groups[i][0], groups[i][1] | groups[j][1])
                    groups.pop(j)
                    changed = True
                    break
            if changed:
                break
    return [[name] + sorted(emails) for name, emails in groups]


def norm(res):
    return sorted(res)


ex1 = [["John", "js@m.co", "john@m.co"], ["John", "js@m.co", "j00@m.co"],
       ["Mary", "mary@m.co"], ["John", "jb@m.co"]]
assert norm(accounts_merge(ex1)) == norm([["John", "j00@m.co", "john@m.co", "js@m.co"],
                                          ["Mary", "mary@m.co"], ["John", "jb@m.co"]])
ex2 = [["A", "a@x", "b@x"], ["A", "c@x"], ["A", "c@x", "b@x"]]
assert accounts_merge(ex2) == [["A", "a@x", "b@x", "c@x"]]
assert accounts_merge([["Z", "z@x", "z@x"]]) == [["Z", "z@x"]]   # 同一帳號內重複的 email
for _ in range(300):
    pool = [f"e{i}" for i in range(10)]
    accs = []
    for _ in range(random.randint(1, 6)):
        accs.append(["N"] + random.sample(pool, random.randint(1, 3)))
    assert norm(accounts_merge(accs)) == norm(brute(accs))
print("all tests passed")
```

### 複雜度與邊界

令 n 是帳號數、E 是 email 總數（含重複）、L 是 email 長度。建 `owner` 與 union 是 O(E · (L + α(n)))，L 來自字串雜湊；排序輸出是 O(E log E · L)，主導了總時間。空間 O(E · L)，用來存 `owner` 與分組。邊界情況：同一帳號內重複的 email 第二次出現時，`owner` 已經是自己，`find(i) == find(i)`，不會出錯也不會重複輸出；名稱相同但沒有共用 email 的帳號必須分開（範例 1 的第四個 John）；只有一個帳號時直接輸出排序後的 email；輸出的名稱取根帳號的名稱，題目保證同一人的帳號名稱相同，所以取哪一個都一樣。

### Follow-up

> [!question]- F1. 如果帳號是一筆一筆註冊進來的，每次註冊後都要能回答「某個 email 屬於哪個人」呢？
> 把 union-find 改成長期存在的結構：`owner` 與 `parent` 持續維護，新帳號進來時照本題的迴圈處理它的 email，每個 email O(L + α(n))。查詢「email 屬於哪個人」就是 `find(owner[email])`，O(L + α(n))。若還要隨時輸出某人的完整 email 清單，就在根上維護一個 email 串列，合併時把小串列接到大串列（small-to-large），每個 email 最多被搬 O(log n) 次，總成本 O(E log n)。

> [!question]- F2. 如果除了 email，共用電話號碼也算同一個人呢？
> 只要把「識別屬性」的種類擴充即可：`owner` 的 key 改成 `("email", e)` 或 `("phone", p)` 這樣的 tuple，避免 email 和電話字串碰巧相同時被誤判，其餘程式完全不變，時間仍是 O(屬性總數 · α(n)) 加上排序。這說明了 union-find 的建模重點：節點是「要被分組的東西」（帳號），邊是「讓它們等價的證據」（任何共用的識別屬性），證據可以有很多種。

> [!question]- F3. 如果使用者可以從帳號中刪除某個 email，合併結果要隨之更新呢？
> 刪除一個 email 可能讓原本的一個人拆成好幾個（那個 email 是唯一的橋），union-find 無法拆開。實務做法是：只重建受影響的那一群，把這群的帳號（刪掉該 email 後）重新跑一次本題的演算法，成本和這群的大小成正比，而不是整個資料庫。若刪除事件可以批次離線處理，也可以用 17.5 節的倒序技巧。面試時說清楚「union-find 只支援合併，刪除要局部重建或離線倒序」就是到位的回答。

> [!question]- F4. 如果有十億個帳號，分散在很多台機器上呢？
> 單機的 union-find 放不下，常見做法是把問題改寫成「二分圖（帳號、email）的連通元件」，用分散式連通元件演算法：每個節點從自己的 ID 開始，每一輪把鄰居中最小的 ID 傳播給自己（label propagation），直到不再變化，輪數和圖的直徑成正比。實務上會先在每台機器上用本地 union-find 把局部的群合併，再只交換跨機器的邊，大幅減少輪數與通訊量。這題在面試中通常用來測試你是否知道 union-find 的「單機、記憶體內」前提。

## 核心題 4｜990. Satisfiability of Equality Equations｜Medium

### 題目

給一個字串陣列 `equations`，每個字串長度恰好 4，形式是 `"a==b"` 或 `"a!=b"`，其中 a、b 是小寫英文字母（可以相同），代表一個單字母變數。請判斷能否給每個變數指定一個整數，讓所有方程式同時成立。限制：`1 <= len(equations) <= 500`。

- 範例 1：`["a==b", "b!=a"]`，a 等於 b 又不等於 b，不可能，回傳 `False`。
- 範例 2：`["b==a", "a==b"]`，令 a = b = 1 即可，回傳 `True`。
- 範例 3：`["a==b", "b!=c", "c==a"]`，由 `a==b` 和 `c==a` 推出 b == c，和 `b!=c` 矛盾，回傳 `False`。注意矛盾的 `!=` 出現在兩個 `==` 中間。
- 範例 4（邊界）：`["a!=a"]` 回傳 `False`；`["a!=b", "b!=c", "c!=a"]` 回傳 `True`，因為整數有無限多個，三個變數可以取三個不同的值。

### 思路

暴力解是嘗試所有指定：26 個變數各取一個值，值只需要 26 種（最多 26 個不同的群），組合數是 26²⁶，完全不可能。就算只看出現的 k 個變數，k^k 也很快爆炸。需要看出結構。

關鍵觀察有兩個。第一，`==` 是等價關係（自反、對稱、傳遞），所有 `==` 會把變數分成若干群，同一群的變數**必須**相等，這是 union-find 的標準用途。第二，`!=` 只限制兩個變數不能相等，而不同群之間沒有任何「必須相等」的理由：我們可以給每一群一個不同的整數，這樣所有跨群的 `!=` 都自動成立。所以整個問題等價於：**有沒有任何一個 `!=` 的兩端落在同一群**？

這直接導出兩趟的演算法：第一趟只處理 `==`，把兩邊 union；第二趟只處理 `!=`，若兩邊 `find` 相同就回傳 False。順序非常重要：如果按輸入順序一邊合併一邊檢查，範例 3 的 `b!=c` 被檢查時 b、c 還不在同一群，會誤判為沒問題，之後的 `c==a` 才把它們合併。必須等所有「必須相等」的資訊都到齊，才能判斷「不能相等」是否被違反。

```text
範例 3：["a==b", "b!=c", "c==a"]

第一趟（只看 ==）：
  "a==b"  union(a, b)     群：{a, b} {c}
  "b!=c"  跳過
  "c==a"  union(c, a)     群：{a, b, c}

第二趟（只看 !=）：
  "b!=c"  find(b) == find(c) → 矛盾，回傳 False

若錯誤地一趟處理：
  "a==b"  union             群：{a, b} {c}
  "b!=c"  find(b) ≠ find(c) → 暫時沒問題   ← 漏掉了
  "c==a"  union             群：{a, b, c}
  回傳 True（錯誤）
```

一趟處理的錯誤版本示範了為什麼要分兩趟：`!=` 的檢查必須在等價關係「完全封閉」之後才有意義。同樣的「先合併、再檢查」結構在很多題目中出現，例如判斷一組字串的相似關係與禁止關係是否衝突。

### 解法

```python
import itertools
import random


def equations_possible(equations: list[str]) -> bool:
    parent = list(range(26))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for eq in equations:                       # 第一趟：只處理 ==
        if eq[1] == "=":
            a, b = ord(eq[0]) - 97, ord(eq[3]) - 97
            parent[find(a)] = find(b)
    for eq in equations:                       # 第二趟：檢查每個 != 有沒有被迫相等
        if eq[1] == "!":
            if find(ord(eq[0]) - 97) == find(ord(eq[3]) - 97):
                return False
    return True


def brute(equations):
    vars_ = sorted({eq[0] for eq in equations} | {eq[3] for eq in equations})
    k = len(vars_)
    for vals in itertools.product(range(k), repeat=k):   # k 個變數，k 種值就足以表示任何分組
        env = dict(zip(vars_, vals))
        if all((env[e[0]] == env[e[3]]) == (e[1] == "=") for e in equations):
            return True
    return False


assert equations_possible(["a==b", "b!=a"]) is False
assert equations_possible(["b==a", "a==b"]) is True
assert equations_possible(["a==b", "b==c", "a==c"]) is True
assert equations_possible(["a==b", "b!=c", "c==a"]) is False
assert equations_possible(["c==c", "b==d", "x!=z"]) is True
assert equations_possible(["a!=a"]) is False                 # 自己不等於自己
assert equations_possible(["a!=b", "b!=c", "c!=a"]) is True   # 整數有無限多個，可以三個都不同
for _ in range(300):
    letters = "abcde"
    eqs = [random.choice(letters) + random.choice(["==", "!="]) + random.choice(letters)
           for _ in range(random.randint(1, 6))]
    assert equations_possible(eqs) == brute(eqs)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n · α(26))，n 是方程式數，也就是 O(n)；空間 O(26) = O(1)。邊界情況：`"a!=a"` 時兩邊是同一個變數，`find` 必然相同，正確回傳 False，不需要特判；`"a==a"` 只是讓 a 和自己合併，不影響任何東西；只有 `!=` 而沒有 `==` 時每個變數自成一群，永遠回傳 True；變數只有 26 個，所以這題的 union-find 不需要任何優化也很快，但寫出 path halving 是好習慣。

### Follow-up

> [!question]- F1. 如果要回傳「造成矛盾」的那一組方程式呢？
> 第二趟找到矛盾的 `x!=y` 後，還要給出一串 `==` 證明 x 和 y 被迫相等。建一張只含 `==` 邊的無向圖（每條邊記錄它來自第幾個方程式），從 x 做 BFS 到 y，路徑上的邊對應的方程式加上 `x!=y`，就是一組最小的矛盾證據，O(n)。Union-find 本身只知道「同群」，不記錄「為什麼同群」，所以要證據時必須另外建圖，這是它和 BFS 的分工。

> [!question]- F2. 如果方程式是線上一個一個送進來的，要在每一個送進來後立刻判斷是否仍然可滿足呢？
> 不能再先做完所有 `==`。在每個根上維護一個集合 `bans[root]`，存「和這群不能相等的其他群的代表」。收到 `x!=y` 時若同根就矛盾，否則把彼此的根加進對方的 `bans`。收到 `x==y` 時若兩根不同，先檢查 ry 是否在 `bans[rx]` 裡，在就矛盾；否則合併，把小的 `bans` 併入大的（small-to-large），並更新其中元素指向的根（或在查詢時再 `find` 一次）。每條限制被搬移 O(log n) 次，總時間 O(n log n)。

> [!question]- F3. 如果加入 `<` 與 `>` 的方程式呢？
> 先用 union-find 處理所有 `==`，把每一群縮成一個點；接著把每個 `a<b` 變成有向邊 `find(a) → find(b)`。若某個 `<` 的兩端同群（a < a），直接矛盾；否則可滿足若且唯若這張縮點後的有向圖沒有環，用拓撲排序檢查（第 16 章核心題 1），O(n)。`!=` 仍然只要檢查兩端不同群，因為可以在拓撲序中給每群不同的值。

> [!question]- F4. 如果變數只能是 0 或 1（布林值）呢？
> 情況完全改變：`a!=b`、`b!=c`、`a!=c` 在整數中可滿足，在布林中卻不行，因為只有兩個值，a ≠ b 且 b ≠ c 推出 a == c。這時要用帶權 union-find 記錄奇偶性：`parity[x]` 是「x 和父節點是否不同」，`find` 時沿路 XOR 累積；`x==y` 要求兩者相對根的奇偶性相同，`x!=y` 要求不同，合併時算出兩根之間應有的奇偶值，若已同根就檢查是否一致。每個限制 O(α(n))。這等價於判斷一張圖是否為二分圖（785. Is Graph Bipartite），也是 17.4 節帶權 union-find 的 XOR 版本。

## 核心題 5｜1319. Number of Operations to Make Network Connected｜Medium

### 題目

有 n 台電腦（編號 0 到 n − 1），用網路線 `connections` 相連，`connections[i] = [a, b]` 代表 a 和 b 之間有一條線。任何兩台電腦只要直接或間接相連就能通訊。你可以做以下操作任意次：拔掉一條現有的線，改插到任意兩台原本沒有直接相連的電腦之間。請回傳讓所有電腦都能互相通訊的最少操作次數；若不可能，回傳 -1。限制：`1 <= n <= 10⁵`，`1 <= len(connections) <= min(n(n − 1)/2, 10⁵)`，沒有重複的線。

- 範例 1：`n = 4`、`connections = [[0, 1], [0, 2], [1, 2]]`，0、1、2 形成三角形，3 孤立。拔掉 `[1, 2]` 改接到 1 和 3，回傳 `1`。
- 範例 2：`n = 6`、`connections = [[0, 1], [0, 2], [0, 3], [1, 2], [1, 3]]`，0–3 這一群有 5 條線但只需要 3 條，多出 2 條，正好能接上孤立的 4 和 5，回傳 `2`。
- 範例 3：`n = 6`、`connections = [[0, 1], [0, 2], [0, 3], [1, 2]]`，只有 4 條線，6 台電腦至少需要 5 條，回傳 `-1`。
- 範例 4（邊界）：`n = 1`、`connections = []`，只有一台電腦，已經連通，回傳 `0`。

### 思路

這題看起來像是要模擬「拔哪一條、插到哪裡」，但其實只要兩個數字。先想下限：若目前有 c 個連通元件，每次操作最多讓元件數減一（新插的一條線最多連接兩個元件），所以至少需要 c − 1 次。再想可行性：連通 n 台電腦至少需要 n − 1 條線，線總數 < n − 1 時無論怎麼搬都不可能，回傳 -1。

關鍵的觀察是：**只要線總數 ≥ n − 1，c − 1 次就一定做得到**。每個元件若有 s 台電腦、e 條線，維持它連通只需要 s − 1 條，多出來的 e − (s − 1) 條是「多餘的線」（拔掉它不會讓元件斷開，因為它在某個環上）。所有元件的多餘線總數是 m − (n − c)，而 m ≥ n − 1 推出 m − (n − c) ≥ c − 1，所以多餘的線足夠用來把 c 個元件串起來；每次拔一條多餘的線去連接兩個不同元件，元件數減一且不會造成新的斷開。

於是演算法就是：若 m < n − 1 回傳 -1；否則用 union-find 數連通元件 c，回傳 c − 1。暴力模擬（每次找一條多餘線、找兩個不同元件）同樣是 O(n + m)，但邏輯更長；數學化之後程式只剩幾行，而面試的重點是能說清楚「為什麼多餘的線一定夠」。

```text
範例 2：n = 6，m = 5 ≥ n - 1 = 5，可能可行

加入邊      結果                元件
[0,1]       合併                {0,1} {2} {3} {4} {5}       c = 5
[0,2]       合併                {0,1,2} {3} {4} {5}         c = 4
[0,3]       合併                {0,1,2,3} {4} {5}           c = 3
[1,2]       已同根 → 多餘線 1                               c = 3
[1,3]       已同根 → 多餘線 2                               c = 3

c = 3 個元件，需要 c - 1 = 2 次操作；多餘線 2 條 ≥ 2，足夠
操作 1：拔 [1,2]，接 3–4      {0,1,2,3,4} {5}
操作 2：拔 [1,3]，接 4–5      {0,1,2,3,4,5}
```

union 失敗的兩條邊 `[1, 2]`、`[1, 3]` 就是多餘的線。這也說明了為什麼「m ≥ n − 1」就足以保證可行：成功合併的邊恰好有 n − c 條，其餘 m − (n − c) 條都是多餘的，在 m ≥ n − 1 時這個數字至少是 c − 1。

### 解法

```python
import random


def make_connected(n: int, connections: list[list[int]]) -> int:
    if len(connections) < n - 1:               # 連通 n 台至少要 n - 1 條線
        return -1
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    components = n
    for a, b in connections:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            components -= 1
    return components - 1


def brute(n, connections):
    """BFS 數元件，並獨立數出多餘的線，驗證「多餘線 ≥ 元件數 − 1」。"""
    adj = [[] for _ in range(n)]
    for a, b in connections:
        adj[a].append(b)
        adj[b].append(a)
    seen, comps = [False] * n, 0
    for s in range(n):
        if not seen[s]:
            comps += 1
            seen[s] = True
            stack = [s]
            while stack:
                u = stack.pop()
                for v in adj[u]:
                    if not seen[v]:
                        seen[v] = True
                        stack.append(v)
    spare = len(connections) - (n - comps)     # 每個元件的生成樹用掉「節點數 − 1」條
    return comps - 1 if spare >= comps - 1 else -1


assert make_connected(4, [[0, 1], [0, 2], [1, 2]]) == 1
assert make_connected(6, [[0, 1], [0, 2], [0, 3], [1, 2], [1, 3]]) == 2
assert make_connected(6, [[0, 1], [0, 2], [0, 3], [1, 2]]) == -1
assert make_connected(1, []) == 0
assert make_connected(3, []) == -1
assert make_connected(5, [[0, 1], [1, 2], [2, 0], [3, 4]]) == 1
for _ in range(300):
    n = random.randint(1, 9)
    pairs = [[a, b] for a in range(n) for b in range(a + 1, n)]
    conns = random.sample(pairs, random.randint(0, len(pairs)))
    assert make_connected(n, conns) == brute(n, conns)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n + m · α(n))，m 是線的數量：初始化 `parent` O(n)，每條線兩次 `find`。空間 O(n)。邊界情況：n = 1 時不需要任何線，m = 0 ≥ 0 通過檢查，元件數 1，回傳 0；m < n − 1 必須在建 union-find 之前就回傳 -1，這不只是優化，也避免了「元件數 − 1」被誤當成答案；孤立的電腦（沒有任何線）各自是一個元件，初始化時已經算進 `components = n`；題目保證沒有重複的線，但即使有，重複的線會被當成多餘線，結論仍然成立。

### Follow-up

> [!question]- F1. 如果要輸出具體的操作（拔哪條、接到哪兩台）呢？
> 在 union 的過程中，把失敗的邊收集成 `spare` 列表；結束後收集每個元件的一個代表（所有 `find(i) == i` 的 i）。答案是 c − 1 個操作：第 k 個操作拔掉 `spare[k]`，改接到 `reps[0]` 和 `reps[k + 1]`。因為 `spare` 至少有 c − 1 條（前面的證明），這組操作一定湊得齊；拔掉多餘線不會讓任何元件斷開，所以每次操作都讓元件數恰好減一。整體 O(n + m · α(n))。

> [!question]- F2. 如果不能拔線，只能買新的線來接呢？
> 這時線的數量限制消失，答案永遠是 c − 1：k 個元件之間至少要 k − 1 條新線，而用 c − 1 條把各元件的代表串成一條鏈就夠了。程式只要拿掉 `m < n − 1` 的判斷，O(n + m · α(n))。若新線有不同的價格（例如接 i 和 j 的成本是兩台的距離），問題就變成「已有部分邊、求最小生成樹」：先把現有的線以成本 0 union 起來，再對候選的新線做 Kruskal，O(E log E)，第 18 章核心題 5（1584）是同類。

> [!question]- F3. 如果線是陸續接上的，每接上一條就要回報目前的答案呢？
> 維護兩個數：元件數 c 與線的總數 m。每接一條線 m += 1，union 成功則 c −= 1；目前的答案就是 `c - 1 if m >= n - 1 else -1`，每次 O(α(n))。注意多餘線的數量不需要另外維護，因為它等於 m − (n − c)，而前面的證明說明「m ≥ n − 1」和「多餘線 ≥ c − 1」是等價的。這是 union-find 增量維護全域統計量的典型用法。

> [!question]- F4. 如果有些線是焊死的（不能拔），只有標記為可移動的線能搬呢？
> 元件數 c 不變（仍用所有線計算），但「多餘線」必須是可移動的。做法是先 union 所有固定線，得到元件數 c_f，再 union 可移動線：成功合併的可移動線恰好 c_f − c 條，它們是維持現有連通性必須保留的，失敗的 M − (c_f − c) 條（M 是可移動線總數）才可以拔。答案是 `c - 1 if M - (c_f - c) >= c - 1 else -1`，O(n + m · α(n))。「固定線先合併」為什麼能讓可拔的線最多？因為任何保持相同連通性的選法，都至少要用 c_f − c 條可移動線來補足固定線連不起來的部分，這和難題 4（1579）「共用邊優先」是同一個交換論證。

## 難題 1｜685. Redundant Connection II｜Hard

### 題目

一棵有根樹是一張有向圖：恰好一個根節點沒有父節點，其他每個節點恰好有一個父節點，所有節點都是根的後代。給一棵 n 個節點（編號 1 到 n）的有根樹，有人多加了一條有向邊 `[u, v]`（u ≠ v，而且不是原本就有的邊），邊的方向是「父 → 子」。給你加邊後的 n 條邊 `edges`，請回傳一條可以刪除的邊，使剩下的圖恰好是一棵 n 個節點的有根樹；若有多個答案，回傳在 `edges` 中最後出現的那一條。限制：`3 <= n <= 1000`。

- 範例 1：`edges = [[1, 2], [1, 3], [2, 3]]`，節點 3 有兩個父節點（1 和 2），刪掉任一條都可以，回傳最後出現的 `[2, 3]`。
- 範例 2：`edges = [[1, 2], [2, 3], [3, 4], [4, 1], [1, 5]]`，每個節點都只有一個父節點，但 1 → 2 → 3 → 4 → 1 形成有向環，環上任一條都能刪，回傳最後出現的 `[4, 1]`。
- 範例 3：`edges = [[2, 1], [3, 1], [4, 2], [1, 4]]`，節點 1 有兩個父節點（2 和 3），同時 1 → 4 → 2 → 1 是有向環。刪 `[3, 1]` 的話環還在，所以只能刪 `[2, 1]`，它同時解決兩個問題，回傳 `[2, 1]`。
- 範例 4（邊界）：`edges = [[1, 2], [2, 3], [3, 1]]`，整張圖就是一個環，沒有根；刪掉任一條都會讓被斷開的終點成為根，回傳最後出現的 `[3, 1]`。

### 提示

> [!tip]- 提示 1
> 和 684 不同，有向的版本有兩種「壞掉」的方式：某個節點有兩個父節點，或圖中有有向環。先想想多加的那條邊 `[u, v]` 指向的 v，如果原本就有父節點會怎樣、如果 v 是根又會怎樣。

> [!tip]- 提示 2
> 如果有節點 v 的入度是 2，答案一定是指向 v 的兩條邊之一，稱它們為 cand1（較早出現）和 cand2（較晚出現）。如果沒有入度 2 的節點，多加的邊一定指向根，圖中有一個有向環，答案就是環上最後出現的邊，和 684 一樣。

> [!tip]- 提示 3
> 有入度 2 時，先假設刪掉 cand2，把其餘的邊當作無向邊用 union-find 加入。若過程中沒有形成環，刪 cand2 就是對的；若仍然形成環，代表 cand2 不在環上而 cand1 在，答案是 cand1。

### 詳解

**為什麼直接套 684 不行**。684 的論證是「第一條閉合環的邊就是答案」，前提是只要無環就是樹。有向的情況下，「把邊當無向邊看沒有環」還不夠：每個節點還必須恰好一個父節點。範例 1 中，依序加入 `[1, 2]`、`[1, 3]`、`[2, 3]`，第三條閉合了無向環，684 的方法回傳 `[2, 3]`，碰巧對；但在範例 3 中，依序加入 `[2, 1]`、`[3, 1]`、`[4, 2]`、`[1, 4]`，第四條閉合了無向環 1–4–2–1，684 的方法會回傳 `[1, 4]`，可是刪掉它之後節點 1 仍有兩個父節點，不是有根樹。所以必須把「入度」這個有向的條件納入考量。

**分類多加的邊 `[u, v]`**。原本的樹中每個非根節點恰好有一個父節點。若 v 不是根，加邊後 v 的入度變成 2，這是情況 A；此時 u 可能是 v 的後代（形成有向環，範例 3），也可能不是（沒有環，範例 1）。若 v 是根，加邊後所有節點入度都是 1，沒有入度 2 的節點，但根被接到它的後代 u 之下，形成一個經過根的有向環，這是情況 B（範例 2、4）。情況 B 中，刪掉環上任何一條邊都能讓那條邊的終點成為新的根，所以答案是環上最後出現的邊，和 684 完全相同：把邊依序當無向邊加入，第一條閉合環的就是答案。

**情況 A 的判斷**。入度 2 的節點 v 有兩條入邊 cand1（較早）與 cand2（較晚），答案一定是其中一條，因為不刪它們，v 永遠有兩個父節點。先試刪 cand2（它較晚出現，若兩者都可以，題目要它）：把除了 cand2 以外的 n − 1 條邊當無向邊加入 union-find。若沒有形成環，這 n − 1 條邊構成一棵無向的生成樹，而且每個節點入度 ≤ 1（v 只剩 cand1），恰好一個節點入度 0，於是它是以那個節點為根的有根樹，刪 cand2 正確。若形成了環，代表刪掉 cand2 後環還在，所以 cand2 不在那個環上；而題目保證有解，唯一的另一個選擇 cand1 必定在環上，刪它才能同時消除環和入度 2，答案是 cand1。

**為什麼「有環就回傳 cand1」不需要確認環上有 cand1**。可以這樣看：情況 A 中若有環，環一定經過 v（環上每個節點入度至少 1，而非環的部分是樹狀結構；多出來的入度只在 v），而環上進入 v 的那條邊不是 cand1 就是 cand2；既然 cand2 已經被拿掉而環還在，它就是 cand1。這個論證是程式能寫得這麼短的關鍵。

```text
範例 3：edges = [2,1] [3,1] [4,2] [1,4]

第一步：找入度 2 的節點
  [2,1] → parent_of[1] = 2
  [3,1] → 1 已經有父節點 2 → cand1 = [2,1]，cand2 = [3,1]
  [4,2] → parent_of[2] = 4
  [1,4] → parent_of[4] = 1

第二步：跳過 cand2，其餘當無向邊加入 union-find
  [2,1]    find(2) ≠ find(1)   合併        {1,2}
  [3,1]    跳過（cand2）
  [4,2]    find(4) ≠ find(2)   合併        {1,2,4}
  [1,4]    find(1) == find(4)  形成環！    1 → 4 → 2 → 1
  → 環還在，cand2 不在環上，回傳 cand1 = [2,1]

驗證：刪掉 [2,1] 後剩 [3,1] [4,2] [1,4]：3 → 1 → 4 → 2，根是 3，是有根樹
```

範例 3 同時有入度 2 和環，所以兩個候選中只有一個是對的。如果演算法只看入度、直接回傳較晚的 cand2，就會留下環 1 → 4 → 2 → 1，而 3 → 1 只是掛在環外，沒有任何節點是根。union-find 在這裡的角色是「檢查剩下的邊有沒有環」，入度檢查則負責縮小候選範圍。

### 解法

```python
import random


def find_redundant_directed_connection(edges: list[list[int]]) -> list[int]:
    n = len(edges)
    parent_of = [0] * (n + 1)
    cand1 = cand2 = None
    for u, v in edges:                         # 找有沒有節點被兩條邊指到
        if parent_of[v]:
            cand1, cand2 = [parent_of[v], v], [u, v]   # cand1 較早出現，cand2 較晚
        else:
            parent_of[v] = u

    uf = list(range(n + 1))

    def find(x: int) -> int:
        while uf[x] != x:
            uf[x] = uf[uf[x]]
            x = uf[x]
        return x

    for u, v in edges:
        if [u, v] == cand2:                    # 先假設刪掉較晚的那條
            continue
        ru, rv = find(u), find(v)
        if ru == rv:                           # 仍然有環
            return cand1 if cand1 else [u, v]
        uf[ru] = rv
    return cand2                               # 刪掉 cand2 後無環：它就是答案


def is_rooted_tree(n, edges):
    indeg = [0] * (n + 1)
    children = [[] for _ in range(n + 1)]
    for u, v in edges:
        indeg[v] += 1
        children[u].append(v)
    roots = [x for x in range(1, n + 1) if indeg[x] == 0]
    if len(roots) != 1 or any(indeg[x] > 1 for x in range(1, n + 1)):
        return False
    seen, stack = {roots[0]}, [roots[0]]
    while stack:
        for c in children[stack.pop()]:
            if c not in seen:
                seen.add(c)
                stack.append(c)
    return len(seen) == n


def brute(edges):
    n = len(edges)
    for k in range(n - 1, -1, -1):
        if is_rooted_tree(n, edges[:k] + edges[k + 1:]):
            return edges[k]


assert find_redundant_directed_connection([[1, 2], [1, 3], [2, 3]]) == [2, 3]
assert find_redundant_directed_connection([[1, 2], [2, 3], [3, 4], [4, 1], [1, 5]]) == [4, 1]
assert find_redundant_directed_connection([[2, 1], [3, 1], [4, 2], [1, 4]]) == [2, 1]
assert find_redundant_directed_connection([[1, 2], [2, 3], [3, 1]]) == [3, 1]
for _ in range(500):
    n = random.randint(3, 8)
    order = list(range(1, n + 1))
    random.shuffle(order)
    tree = [[order[random.randrange(i)], order[i]] for i in range(1, n)]
    while True:
        u, v = random.sample(range(1, n + 1), 2)
        if [u, v] not in tree:
            break
    edges = tree + [[u, v]]
    random.shuffle(edges)
    assert find_redundant_directed_connection(edges) == brute(edges)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n · α(n))：一趟掃描找入度 2，一趟 union-find。空間 O(n)。邊界情況：多加的邊可能是 `[v 的後代, v]`（同時有入度 2 與環），也可能是 `[任意節點, v]` 而沒有環，也可能指向根（只有環）；三種情況都要涵蓋，測試中的隨機樹與隨機附加邊就是為了覆蓋它們。多加的邊也可能是「反向邊」，例如原本有 `[1, 2]`，多加 `[2, 1]`：若 1 是根，2 → 1 讓根有了父節點，屬於情況 B，環是 1 → 2 → 1，回傳兩者中較晚出現的那條。`brute` 用「從最後一條往前試、第一個能形成有根樹的」驗證「最後出現」的要求。

### Follow-up

> [!question]- F1. 如果不保證有解（輸入可能是任意 n 條有向邊），要判斷能否刪一條邊變成有根樹呢？
> 可能壞掉的方式變多：可能有入度 3 的節點、多個入度 2 的節點、多個環，或刪完仍不連通。最穩健的做法是先檢查：入度 ≥ 3 或有兩個以上入度 2 的節點，直接無解；有一個入度 2 時只有兩個候選，各自刪掉後用 O(n) 檢查「恰好一個入度 0、無環且全部可達」；沒有入度 2 時候選是環上的邊，可以先找出那個有向環（DFS 三色標記，第 16 章），再逐一檢查，或注意到刪任一條環上的邊效果都一樣、只需檢查一條。總時間 O(n)。

> [!question]- F2. 如果多加的不是一條而是 k 條有向邊，最少刪幾條能變回有根樹？
> 必須刪恰好 k 條（有根樹恰好 n − 1 條邊）。這時問題變成「在有向圖中找一棵生成的有根樹（arborescence）」，是否存在以及要刪哪些，候選組合是指數級的，一般化之後要用最小樹形圖演算法（Chu–Liu／Edmonds，O(nm)）：給每條邊權重，例如「越晚出現越貴」，求最小樹形圖，不在其中的邊就是要刪的。面試中很少要寫出來，但能說出「有向版的最小生成樹是 Edmonds 演算法，不是 Kruskal」就很好。

> [!question]- F3. 如果不只要回傳答案，還要回傳刪除後的根是哪個節點呢？
> 刪除答案邊後，根就是唯一入度 0 的節點，再掃一次 O(n) 即可。也可以直接推：情況 A 中，原本的根仍是根（多加的邊指向非根節點 v，刪掉任一條入邊後根的入度仍是 0），就是第一趟掃描中 `parent_of` 為 0 的節點；情況 B 中，被刪掉的邊 `[u, v]` 的終點 v 成為新的根，因為它失去了唯一的父節點。這個推導可以當作驗證答案的 sanity check。

> [!question]- F4. 如果要回傳「所有」可以刪除的邊，而不只是最後出現的那一條呢？
> 依情況分開。情況 A（有入度 2 的節點 v）：答案只可能是 cand1 或 cand2，各自刪掉後用 O(n) 檢查是否為有根樹（恰好一個入度 0、無環），兩個都通過就都回傳；例如範例 1 兩條都可以，範例 3 只有 `[2, 1]` 可以。情況 B（只有環）：環上每一條邊都可以刪。找環的方法是從閉合環的那條邊 `[u, v]` 出發，沿著 `parent_of` 從 u 往上走，直到回到 v，路上經過的邊加上 `[u, v]` 就是整個環，O(n)。整體仍是 O(n)。

### 心得

關鍵突破是把多加的邊依「指向的節點是不是根」分成兩類：指向非根會造成入度 2，候選縮成兩條；指向根只會造成環，退化成 684。Union-find 在兩種情況中做的事完全一樣，都是「檢查剩下的邊當無向邊看有沒有環」，差別只在跳過哪條邊。它和核心題 2（684）的關係是：684 只需要「無環」一個條件，這題多了「入度 ≤ 1」，所以要先用入度把候選縮小。面試時建議先畫出三種情況（入度 2 無環、入度 2 有環、只有環），各舉一個三四個節點的例子，再說明程式如何用「跳過 cand2」一次區分前兩種；最容易被追問的是「為什麼有環時回傳 cand1 一定對」，要能說出「環必經過 v、且 cand2 已被拿掉」。

## 難題 2｜778. Swim in Rising Water｜Hard

### 題目

給一個 n × n 的整數網格 `grid`，`grid[r][c]` 是格子 (r, c) 的海拔，所有值恰好是 0 到 n² − 1 的一個排列（互不相同）。開始下雨，時間 t 時各處水深都是 t。你可以從一格游到上下左右相鄰的另一格，條件是**兩格的海拔都不超過 t**；游泳本身不花時間，而且同一時刻可以游任意遠。你從 (0, 0) 出發，請回傳最早在什麼時間 t 可以抵達 (n − 1, n − 1)。限制：`1 <= n <= 50`。

- 範例 1：`grid = [[0, 2], [1, 3]]`，t = 3 時右下角的 3 才被淹沒，之前右下角都不能進入，回傳 `3`。
- 範例 2：`grid = [[0, 1, 2, 3, 4], [24, 23, 22, 21, 5], [12, 13, 14, 15, 16], [11, 17, 18, 19, 20], [10, 9, 8, 7, 6]]`，最佳路線沿外圈走 0 → 1 → … → 5 → 16 → 15 → 14 → 13 → 12 → 11 → 10 → … → 6，路上最高的格子是 16，回傳 `16`。
- 範例 3：`grid = [[0, 3, 4], [1, 2, 8], [7, 6, 5]]`，路線 0 → 1 → 2 → 6 → 5 的最大值是 6；走上面 0 → 3 → 4 → 8 → 5 要 8，回傳 `6`。
- 範例 4（邊界）：`grid = [[0]]` 回傳 `0`；`grid = [[3, 2], [0, 1]]` 起點本身海拔 3，最早 t = 3 才能離開起點，回傳 `3`。

### 提示

> [!tip]- 提示 1
> 時間 t 時能走的格子，就是海拔 ≤ t 的所有格子。答案是「最小的 t，使得起點和終點在海拔 ≤ t 的格子中連通」。t 越大，能走的格子只會越多。

> [!tip]- 提示 2
> 連通性對 t 單調，所以可以對 t 二分，每次用 BFS 檢查，O(n² log n²)。能不能不重跑 BFS？想想「t 從 0 增加到 n² − 1，每次多一格可以走」對 union-find 意味著什麼。

> [!tip]- 提示 3
> 依海拔從小到大一格一格「啟用」：啟用海拔 t 的格子時，和已啟用的鄰居 union。第一次 `find(起點) == find(終點)` 時的 t 就是答案。因為海拔是排列，可以用一個陣列直接由 t 找到格子。

### 詳解

**把題目翻譯成連通性**。「游泳不花時間」這個條件很關鍵：時間 t 時，所有海拔 ≤ t 的格子組成一張子圖，在同一個連通元件裡的格子之間可以瞬間移動。所以「時間 t 能否抵達終點」等價於「起點和終點在海拔 ≤ t 的子圖中連通」。答案就是讓這件事成立的最小 t，也等於「所有從起點到終點的路徑中，路徑上最大海拔的最小值」，這種「最小化路徑上的最大值」的問題叫 minimax path（瓶頸路徑）。

**三種解法**。第一種是二分答案加 BFS（第 8 章的思維二）：pred(t) =「海拔 ≤ t 的格子中起點能否走到終點」，t 越大越容易，F…F T…T，範圍 `[grid[0][0], n² − 1]`，每次 BFS O(n²)，總共 O(n² log n)。第二種是修改版 Dijkstra（第 18 章核心題 3 的 1631 是同類）：路徑成本定義為「目前為止的最大海拔」，用 heap 每次擴展成本最小的格子，O(n² log n)。第三種是本章的 union-find：既然 t 增加時可走的格子只增不減，就讓 t 從 0 開始遞增，每一步把海拔恰好為 t 的格子啟用並和已啟用的鄰居合併，然後問起點和終點是否同根。第一次同根時的 t 就是答案。

**為什麼依序啟用是對的**。處理完 t 之後，已啟用的格子恰好是海拔 ≤ t 的格子，union-find 中的集合恰好是這張子圖的連通元件，因為每個格子啟用時都和所有已啟用的鄰居合併過，而之後啟用的格子在它啟用時也會回頭和它合併，任何一條「兩端都 ≤ t」的相鄰關係都至少被處理過一次。所以第一個讓起點與終點同根的 t，就是讓它們在子圖中連通的最小 t。因為海拔是 0..n² − 1 的排列，每個 t 恰好啟用一格，可以預先建 `pos[t]` 直接找到它，不需要排序，總時間 O(n² · α(n²))。

```text
範例 3：grid =  0 3 4      格子編號   0 1 2
                1 2 8                 3 4 5
                7 6 5                 6 7 8

t   啟用格子(海拔)   和已啟用鄰居合併        含起點 0 的集合       起點與終點(8)同根？
0   (0,0) 海拔 0     無                      {0}                   否（終點未啟用）
1   (1,0) 海拔 1     和 (0,0)                {0, 3}                否
2   (1,1) 海拔 2     和 (1,0)                {0, 3, 4}             否
3   (0,1) 海拔 3     和 (0,0)、(1,1)          {0, 1, 3, 4}          否
4   (0,2) 海拔 4     和 (0,1)                {0, 1, 2, 3, 4}       否
5   (2,2) 海拔 5     無（鄰居 8、6 未啟用）  終點自成一群 {8}       否
6   (2,1) 海拔 6     和 (1,1)、(2,2)          {0, 1, 2, 3, 4, 7, 8} 是 → 回傳 6

已啟用（t = 6）：   0 3 4
                   1 2 .
                   . 6 5
```

t = 5 時終點已經啟用了，但它的鄰居（海拔 8 和 6）都還在水面上，所以它是孤島；t = 6 時中間下方那格被淹沒，它同時接上上方的 2 和右邊的 5，兩個集合合併，起點與終點第一次同根。這也說明了為什麼不能只在「啟用終點」時檢查：連通常常發生在啟用某個中間格子的時候。

### 解法

```python
import heapq
import random


def swim_in_water(grid: list[list[int]]) -> int:
    n = len(grid)
    pos = [0] * (n * n)
    for r in range(n):
        for c in range(n):
            pos[grid[r][c]] = r * n + c       # 高度是 0..n²-1 的排列：高度 → 格子編號
    parent = list(range(n * n))
    active = [False] * (n * n)

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for t in range(n * n):                     # 時間 t：高度為 t 的格子變得可以進入
        cell = pos[t]
        active[cell] = True
        r, c = divmod(cell, n)
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < n and 0 <= nc < n and active[nr * n + nc]:
                parent[find(nr * n + nc)] = find(cell)
        if active[0] and active[n * n - 1] and find(0) == find(n * n - 1):
            return t
    return n * n - 1                           # 不會走到這裡


def swim_dijkstra(grid):
    n = len(grid)
    best = [[float("inf")] * n for _ in range(n)]
    best[0][0] = grid[0][0]
    pq = [(grid[0][0], 0, 0)]
    while pq:
        t, r, c = heapq.heappop(pq)
        if (r, c) == (n - 1, n - 1):
            return t
        if t > best[r][c]:
            continue
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < n and 0 <= nc < n:
                nt = max(t, grid[nr][nc])
                if nt < best[nr][nc]:
                    best[nr][nc] = nt
                    heapq.heappush(pq, (nt, nr, nc))


assert swim_in_water([[0, 2], [1, 3]]) == 3
assert swim_in_water([[0, 1, 2, 3, 4], [24, 23, 22, 21, 5], [12, 13, 14, 15, 16],
                      [11, 17, 18, 19, 20], [10, 9, 8, 7, 6]]) == 16
assert swim_in_water([[0]]) == 0
assert swim_in_water([[3, 2], [0, 1]]) == 3               # 起點本身最高
assert swim_in_water([[0, 3, 4], [1, 2, 8], [7, 6, 5]]) == 6
for _ in range(300):
    n = random.randint(1, 6)
    vals = list(range(n * n))
    random.shuffle(vals)
    g = [vals[i * n:(i + 1) * n] for i in range(n)]
    assert swim_in_water(g) == swim_dijkstra(g)
print("all tests passed")
```

### 複雜度與邊界

Union-find 版本時間 O(n² · α(n²))：每個格子啟用一次，各做至多四次 union；因為海拔是排列，用 `pos` 陣列代替排序。空間 O(n²)。Dijkstra 版本 O(n² log n)。邊界情況：n = 1 時 t = 0 啟用唯一的格子，它同時是起點和終點，立刻回傳 0；起點海拔很高時（範例 4 的 3），在它被啟用前 `active[0]` 是 False，不會誤判；同理終點也要檢查 `active`，否則兩個都還沒啟用的格子 `find` 會各自回傳自己，雖然不相等不會出錯，但明確檢查比較清楚。答案至少是 `max(grid[0][0], grid[n-1][n-1])`，因為兩端都必須被淹沒。

### Follow-up

> [!question]- F1. 如果海拔不是排列（可以重複、範圍到 10⁹）呢？
> 不能再用 `pos[t]` 直接定位，改成把所有格子依海拔排序，依序啟用；海拔相同的格子可以一起處理，也可以逐一處理（答案只在處理完某個海拔的所有格子後才需要檢查，但逐一檢查也不會錯，因為第一次連通時的海拔就是答案）。時間 O(n² log n) 主要花在排序。二分答案加 BFS 在值域大時是 O(n² log V)，V 是值域，也可以先把二分的範圍限制在出現過的海拔上，變成 O(n² log n)。

> [!question]- F2. 如果還要輸出一條實際的路線呢？
> Union-find 只知道「連通了」，不知道怎麼走。拿到答案 T 之後，在海拔 ≤ T 的格子上從起點做一次 BFS 記錄父節點，回溯到終點就是一條合法路線，O(n²)。若要求在所有最佳路線中步數最少，這次 BFS 本身就保證最短步數。Dijkstra 版本則可以在擴展時直接記錄前驅，不需要第二次搜尋，這是兩種解法在 follow-up 上的差異。

> [!question]- F3. 如果有 q 組不同的起點與終點要問最早時間呢？
> 每組重跑一次是 O(q · n²)。離線的做法是把所有查詢掛在 union-find 上：依序啟用格子，每次合併兩個集合時檢查哪些查詢的兩端剛好變成同根，這個合併時的 t 就是它們的答案；用 small-to-large 讓每個查詢被搬動 O(log q) 次。更通用的做法是建「最小生成樹」（或 Kruskal reconstruction tree）：兩點之間的 minimax 路徑值等於它們在最小瓶頸生成樹上路徑的最大權重，之後每個查詢用 LCA（第 12 章核心題 5）在 O(log n) 內回答。這也是難題 5（1697）的線上版本。

> [!question]- F4. 如果改成「路徑上相鄰格子海拔差的最大值要最小」呢（1631. Path With Minimum Effort）？
> 成本從「格子的海拔」變成「相鄰兩格的差」，也就是從點權變成邊權。union-find 的做法一樣：把所有相鄰格子對當成邊，權重是海拔差，依權重排序後逐一 union，第一次讓起點與終點同根的權重就是答案，O(n² log n)。這就是在網格圖上跑 Kruskal 並提早停止。第 18 章核心題 3 會用 Dijkstra 解同一題，兩者對照可以看出：minimax 路徑問題同時有「最短路徑」與「最小生成樹」兩種觀點。

### 心得

關鍵突破是看出「時間 t 能否抵達」只取決於海拔 ≤ t 的格子是否把起點和終點連起來，而 t 增加時可走的格子只增不減，於是把整個問題變成依海拔順序做 union。它和本章其他題的關係是：核心題 1–5 的邊是一次給定的，這題的「邊」由一個門檻控制，按門檻排序後就回到最基本的連通性問題；難題 5（1697）把同樣的掃描用在多個查詢上。面試時建議三種解法都提：先說二分答案加 BFS（最容易想到），再說 Dijkstra 的 minimax 變形，最後說 union-find 依序啟用並指出它最簡單、而且複雜度最好；面試官常追問「為什麼可以這樣做」，答案就是單調性：t 越大，連通性只會變好。

## 難題 3｜803. Bricks Falling When Hit｜Hard

### 題目

給一個 m × n 的 0／1 網格 `grid`，1 代表磚塊、0 代表空格。一塊磚是「穩定的」，若且唯若它在最上面一列（直接黏在天花板上），或它上下左右相鄰的磚中至少有一塊是穩定的。給一串打擊位置 `hits`，依序處理：第 i 擊把 `hits[i]` 位置的磚打掉（如果那裡本來就是空的，什麼都不發生），接著所有因此變得不穩定的磚會立刻掉落並消失（掉落的磚不會砸到或卡住其他磚）。請回傳陣列 `result`，`result[i]` 是第 i 擊造成**掉落**的磚塊數，不包含被直接打掉的那一塊。限制：`1 <= m, n <= 200`，`1 <= len(hits) <= 4 × 10⁴`，所有打擊位置互不相同。初始狀態若有不穩定的磚，視為在第一擊之前就已掉落，不計入任何一擊。

- 範例 1：`grid = [[1, 0, 0, 0], [1, 1, 1, 0]]`、`hits = [[1, 0]]`。打掉 (1, 0) 後，(1, 1) 和 (1, 2) 失去和天花板的連結，掉落 2 塊，回傳 `[2]`。
- 範例 2：`grid = [[1, 0, 0, 0], [1, 1, 0, 0]]`、`hits = [[1, 1], [1, 0]]`。第一擊打掉 (1, 1)，沒有磚掉落；第二擊打掉 (1, 0)，它下面和右邊都沒有磚，也沒有掉落，回傳 `[0, 0]`。
- 範例 3：`grid = [[1, 1, 1], [0, 1, 0], [0, 1, 0]]`、`hits = [[0, 1], [1, 1]]`。第一擊打掉天花板上的 (0, 1)，(1, 1)、(2, 1) 只靠它連到天花板，掉落 2 塊；第二擊打的 (1, 1) 已經掉了，是空格，回傳 `[2, 0]`。
- 範例 4（邊界）：`grid = [[0, 0], [0, 0]]`、`hits = [[1, 1]]`，打在空格上，回傳 `[0]`。

### 提示

> [!tip]- 提示 1
> 每一擊後重新從天花板做一次 BFS 是 O(hits · mn)，最多 4 × 10⁴ × 4 × 10⁴，太慢。「打掉磚塊」是刪除操作，union-find 不支援刪除；能不能把時間倒過來看？

> [!tip]- 提示 2
> 先把所有會被打到的磚全部移除，得到「最後的狀態」，用 union-find 建出它的連通情況，並用一個虛擬節點代表天花板。然後倒著把磚一塊一塊放回去，每放回一塊就是一次加入。

> [!tip]- 提示 3
> 放回第 i 擊的磚之前與之後，比較天花板所在集合的大小。增加的量減去放回的那一塊本身，就是正向時第 i 擊造成的掉落數（不能小於 0）。要分辨「這一擊原本打在空格」的情況。

### 詳解

**為什麼直覺做法不夠**。直接模擬：每一擊後從最上面一列的所有磚做 BFS，標記穩定的磚，其餘的全部移除。單次 O(mn)，總共 O(hits · mn) ≈ 4 × 10⁴ × 4 × 10⁴ = 1.6 × 10⁹，太慢。比較聰明的模擬是只從被打掉那格的四個鄰居出發，檢查它們還能不能走到天花板，但在最差情況下（打掉的是唯一的支撐點，下面掛著一大片），每次仍要走過一大片磚，最差複雜度不變。根本問題是：正向的過程是「刪除」，而刪除會讓連通性變差，判斷「這一大片還連不連得到天花板」需要重新搜尋。

**突破點：時間倒流**。把整個過程倒著看：最後的狀態是「所有被打的位置都空了，而且所有不穩定的磚都掉了」。倒著播放時，第 i 擊變成「把 `hits[i]` 的磚放回去」，而那些在第 i 擊時掉落的磚，倒著看就是「隨著這塊磚放回而重新接上天花板」的磚。放回是加入操作，連通性只會變好，正好是 union-find 擅長的。用一個虛擬節點 `roof` 代表天花板，把最上面一列的磚和它 union；那麼「目前穩定的磚數」就是 `size[find(roof)] − 1`。

**對應關係與正確性**。令 S_i 是「打完前 i 擊之後的磚塊配置，但先不考慮掉落」，也就是原始網格移除 `hits[0..i−1]`。正向時第 i 擊掉落的磚，恰好是在 S_i 中和天花板連通、在 S_{i+1} 中不和天花板連通、而且不是 `hits[i]` 本身的磚。關鍵在於：一塊磚在某一擊之後是否穩定，只取決於「它在當下的配置中是否連到天花板」，而之前掉落的磚本來就不連天花板，它們存不存在都不影響任何人的穩定性。所以我們可以忽略「掉落」這件事，只看 S_i：倒著從 S_hits 開始，每放回一塊磚就得到前一個 S，roof 集合的大小差就是兩個狀態之間穩定磚數的差，再減去放回的那一塊本身（若它自己接上了天花板）。若放回的磚沒有接上天花板，差是 0，`max(0, 差 − 1)` 也是 0。

**打在空格的處理**。題目允許打在本來就是空格的位置（或已經掉落的位置）。前者在移除時要區分：用 `grid[r][c] -= 1` 標記，原本是磚的變成 0，原本是空格的變成 −1；倒著加回時 `+= 1`，只有恢復成 1 的才是真的磚，才需要 union。後者（打在已經掉落的磚）不需要特別處理：在倒序中它被放回時，周圍的配置讓它無法連到天花板（否則它在正向時就不會掉落），所以算出的差是 0。

```text
範例 1：grid = 1 0 0 0      hits = [(1,0)]
               1 1 1 0

步驟 1：移除所有打擊位置（(1,0) 原本是磚 → 變成 0）
         1 0 0 0
         0 1 1 0
步驟 2：對最終狀態建 union-find（roof = 虛擬節點）
         (0,0) 在第一列 → union(roof)        roof 群：{roof, (0,0)}        size 2
         (1,1)-(1,2) 相鄰 → union              另一群：{(1,1), (1,2)}
步驟 3：倒著放回 hits[0] = (1,0)
         放回前 size(roof) = 2
         (1,0) 不在第一列；鄰居 (0,0) 是磚 → union，roof 群吸收 (1,0)
                             鄰居 (1,1) 是磚 → union，roof 群吸收 {(1,1),(1,2)}
         放回後 size(roof) = 5
         result[0] = max(0, 5 - 2 - 1) = 2
```

放回 (1, 0) 讓 roof 群從 2 變成 5，增加的 3 塊中有一塊是 (1, 0) 自己，另外 2 塊是正向時被它「拖下去」的 (1, 1) 和 (1, 2)。倒著看，它們是被 (1, 0) 重新接回天花板的。

### 解法

```python
import random


def hit_bricks(grid: list[list[int]], hits: list[list[int]]) -> list[int]:
    m, n = len(grid), len(grid[0])
    roof = m * n                               # 虛擬節點：代表「天花板」
    parent = list(range(m * n + 1))
    size = [1] * (m * n + 1)

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            size[rb] += size[ra]

    g = [row[:] for row in grid]
    for r, c in hits:                          # 先把所有會被打掉的磚移除
        g[r][c] -= 1                           # 原本是空格的會變成 -1，代表「打空了」

    def attach(r: int, c: int) -> None:        # 把 (r, c) 和天花板、四周的磚連起來
        idx = r * n + c
        if r == 0:
            union(idx, roof)
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < m and 0 <= nc < n and g[nr][nc] == 1:
                union(idx, nr * n + nc)

    for r in range(m):                         # 最終狀態的連通情況
        for c in range(n):
            if g[r][c] == 1:
                attach(r, c)

    res = [0] * len(hits)
    for i in range(len(hits) - 1, -1, -1):     # 倒著把磚放回去
        r, c = hits[i]
        g[r][c] += 1
        if g[r][c] != 1:                       # 這一擊打的是空格，什麼都沒發生
            continue
        before = size[find(roof)]
        attach(r, c)
        after = size[find(roof)]
        res[i] = max(0, after - before - 1)    # 新接上天花板的磚，扣掉被打的那一塊本身
    return res


def brute(grid, hits):
    g = [row[:] for row in grid]
    m, n = len(g), len(g[0])
    res = []

    def drop_unstable():
        stable = set()
        stack = [(0, j) for j in range(n) if g[0][j] == 1]
        stable.update(stack)
        while stack:
            x, y = stack.pop()
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < m and 0 <= ny < n and g[nx][ny] == 1 and (nx, ny) not in stable:
                    stable.add((nx, ny))
                    stack.append((nx, ny))
        fell = 0
        for x in range(m):
            for y in range(n):
                if g[x][y] == 1 and (x, y) not in stable:
                    g[x][y] = 0
                    fell += 1
        return fell

    drop_unstable()                            # 初始就不穩定的磚先掉落，不計入任何一擊
    for r, c in hits:
        if g[r][c] == 0:
            res.append(0)
            continue
        g[r][c] = 0
        fell = drop_unstable()
        res.append(fell)
    return res


assert hit_bricks([[1, 0, 0, 0], [1, 1, 1, 0]], [[1, 0]]) == [2]
assert hit_bricks([[1, 0, 0, 0], [1, 1, 0, 0]], [[1, 1], [1, 0]]) == [0, 0]
assert hit_bricks([[1]], [[0, 0]]) == [0]
assert hit_bricks([[0, 0], [0, 0]], [[1, 1]]) == [0]                 # 打在空格
assert hit_bricks([[1, 1, 1], [0, 1, 0], [0, 1, 0]], [[0, 1], [1, 1]]) == [2, 0]
for _ in range(500):
    m, n = random.randint(1, 5), random.randint(1, 5)
    grid = [[random.randint(0, 1) for _ in range(n)] for _ in range(m)]
    cells = [[r, c] for r in range(m) for c in range(n)]
    hits = random.sample(cells, random.randint(1, len(cells)))
    assert hit_bricks(grid, hits) == brute(grid, hits)
print("all tests passed")
```

### 複雜度與邊界

時間 O((mn + h) · α(mn))，h 是打擊次數：建最終狀態時每格至多四次 union，倒序時每一擊至多五次 union。空間 O(mn)。暴力模擬是 O(h · mn)。邊界情況：打在空格時移除後變 −1，加回後變 0，`!= 1` 直接跳過，結果為 0；被打的磚在第一列時，放回它會直接和 roof 合併，它本身算在增加量中，所以要減一；放回的磚沒有接上天花板時（四周沒有穩定的磚、自己也不在第一列），roof 的大小不變，差為 0，`max(0, −1)` 防止出現負數；初始就不穩定的磚在最終狀態中也不連 roof，倒序過程中只有被某次放回接上時才會被計入，這和「初始不穩定的磚在第一擊之前就掉落」的定義一致，`brute` 也用同樣的定義對照。

### Follow-up

> [!question]- F1. 如果打擊是線上送來的（看不到未來的打擊），必須每擊立刻回答呢？
> 倒序技巧需要事先知道所有打擊，線上時就失效了。可行的做法是正向模擬但只局部搜尋：打掉 (r, c) 後，對它的每個鄰居做 BFS，一旦碰到第一列就停止（代表這片仍穩定），否則整片都掉落並刪除。掉落的磚只會被刪一次，所以「真的掉落」的搜尋總成本是 O(mn)；但「仍穩定」的搜尋可能每次都走很遠，最差 O(h · mn)。實務上可以同時從四個鄰居並行 BFS，先碰到天花板的停止，讓成本和較小的那片成正比。面試中說出「離線倒序 O((mn + h) α)，線上只能局部搜尋」就足夠了。

> [!question]- F2. 如果掉落的磚會砸在下面的磚上停住（像俄羅斯方塊）呢？
> 掉落的磚會改變其他位置的配置，而且掉到哪裡取決於下方的形狀，倒序時無法知道「這塊磚原本從哪裡掉下來」，倒序技巧失效。這時只能正向模擬：每一擊後找出不穩定的連通塊，把每塊當成剛體往下移動，直到碰到穩定的磚或底部，再更新穩定性。每一擊的成本和受影響的磚數與移動距離有關，最差 O(mn · m)。這個對比說明了原題「掉落的磚直接消失」這個設定，正是讓倒序成立的關鍵。

> [!question]- F3. 如果同一個位置可以被打很多次（打掉後有人放回新的磚）呢？
> 只要所有操作（打掉、放回）事先都知道，仍然可以離線，但不能再用「先全部移除、再倒著加回」這麼簡單的方式，因為倒序時「放回」變成了刪除。一般化的工具是「離線動態連通性」：把每塊磚存在的時間區間掛到時間軸的線段樹上，對線段樹做 DFS，進入節點時 union、離開時用可回滾的 union-find（不做 path compression，只做 union by size，記錄每次修改以便撤銷）還原，總時間 O((mn + h) log h · log mn)。這是競賽等級的技巧，面試中說出名稱與想法即可。

> [!question]- F4. 如果要問每一擊後「還有幾塊磚是穩定的」，而不是掉了幾塊呢？
> 這是同一個倒序過程的另一種讀法：倒序時，處理完第 i 擊（放回 `hits[i]`）之前的 `size[find(roof)] − 1`，就是正向打完第 i 擊之後的穩定磚數。把 `before − 1` 存下來即可，O(1) 額外成本。這也是很多倒序題的共同結構：倒序時「放回前」的狀態對應正向時「這一步之後」的狀態，寫程式時要對準兩個時間軸。

### 心得

關鍵突破是把「刪除」倒過來變成「加入」，再用虛擬節點 roof 讓「穩定磚數」變成一個集合的 size。它和本章其他題的關係是：難題 2（778）、難題 5（1697）把門檻排序後依序加入，這題則是把時間倒過來依序加入，兩者都是把問題推回 union-find「只增不減」的能力範圍內；虛擬節點的想法也出現在第 15 章核心題 5（130）的 union-find 解法中。面試時建議先說暴力 BFS 的 O(h · mn)，指出瓶頸是「刪除會讓連通性變差」，再提出倒序；最容易被追問的兩個細節是「打在空格怎麼辦」（−1 標記）和「為什麼要減一」（被放回的那一塊本身不算掉落），要主動說清楚。

## 難題 4｜1579. Remove Max Number of Edges to Keep Graph Fully Traversable｜Hard

### 題目

有一張 n 個節點（編號 1 到 n）的無向圖，邊有三種類型：type 1 只有 Alice 能走，type 2 只有 Bob 能走，type 3 兩人都能走。`edges[i] = [type, u, v]`。如果從任一節點出發都能走到所有其他節點，就說這張圖對某人是「完全可走」的。請回傳最多能刪除幾條邊，使得刪除後的圖對 Alice 和 Bob 都仍然完全可走；如果原圖就做不到，回傳 -1。限制：`1 <= n <= 10⁵`，`1 <= len(edges) <= min(10⁵, 3n(n − 1)/2)`，所有邊都是不同的 `(type, u, v)` 三元組。

- 範例 1：`n = 4`，`edges = [[3, 1, 2], [3, 2, 3], [1, 1, 3], [1, 2, 4], [1, 1, 2], [2, 3, 4]]`。保留 `[3, 1, 2]`、`[3, 2, 3]`、`[1, 2, 4]`、`[2, 3, 4]` 就夠了，可以刪掉 `[1, 1, 3]` 和 `[1, 1, 2]`，回傳 `2`。
- 範例 2：`n = 4`，`edges = [[3, 1, 2], [3, 2, 3], [1, 1, 4], [2, 1, 4]]`，每條邊都不能少，回傳 `0`。
- 範例 3：`n = 4`，`edges = [[3, 2, 3], [1, 1, 2], [2, 3, 4]]`，Alice 走不到 4、Bob 走不到 1，回傳 `-1`。
- 範例 4（邊界）：`n = 2`，`edges = [[1, 1, 2], [2, 1, 2], [3, 1, 2]]`，一條 type 3 邊就同時滿足兩人，另外兩條都能刪，回傳 `2`。

### 提示

> [!tip]- 提示 1
> 最多刪幾條 = 總邊數 − 最少保留幾條。對 Alice 來說，可用的邊是 type 1 和 type 3；對 Bob 是 type 2 和 type 3。每個人至少需要一棵生成樹。

> [!tip]- 提示 2
> 一條 type 3 邊能同時為兩人服務，一條 type 1 或 type 2 只能為一個人服務。直覺上應該優先使用 type 3。用兩個 union-find 分別記錄 Alice 和 Bob 的連通狀態。

> [!tip]- 提示 3
> 先處理所有 type 3：只要它在任一人的 union-find 中能合併就保留（其實兩邊狀態相同）。再分別用 type 1 補 Alice、type 2 補 Bob，能合併才保留。最後兩人都只剩一個元件才有解，答案是總邊數減去保留數。

### 詳解

**為什麼直覺做法不夠**。暴力解是枚舉要保留的邊集合，檢查兩人是否都連通，2^m 種，不可能。也有人會想分別對 Alice 和 Bob 各求一棵生成樹再取聯集，但兩棵生成樹可能選了不同的 type 3 邊，聯集就會比必要的多：例如三個節點之間有三條 type 3 邊 a–b、b–c、c–a，Alice 選了 {a–b, b–c}、Bob 選了 {b–c, c–a}，聯集有三條，但其實兩人共用同一棵兩條邊的樹就夠了。問題的核心是**如何讓兩個人盡量共用邊**。

**突破點：type 3 優先的貪婪**。每個人最終各需要恰好 n − 1 條邊組成生成樹（保留更多是浪費）。設保留的 type 3 有 k 條，它們同時算進兩人的生成樹；那麼 Alice 還需要 n − 1 − k 條 type 1，Bob 還需要 n − 1 − k 條 type 2，總保留數是 k + 2(n − 1 − k) = 2(n − 1) − k。所以**要最小化保留數，就要最大化共用的 type 3 數量 k**。而在只含 type 3 邊的圖中，能放進一個森林（無環）的邊數最多是 n − c₃（c₃ 是只用 type 3 時的元件數），用 union-find 依序加入 type 3 邊、保留成功合併的那些，恰好拿到這個最大值。

**為什麼這樣一定最優**。這是一個交換論證（也是 matroid 貪婪的特例）。假設某個最佳解在 Alice 的生成樹中用了 type 3 森林 F₃（k 條）。因為只用 type 3 時有 c₃ 個元件，任何 type 3 森林最多 n − c₃ 條；我們的貪婪拿到了 n − c₃ 條，k ≤ n − c₃，所以貪婪的保留數 2(n − 1) − (n − c₃) 不會大於最佳解的 2(n − 1) − k。剩下的問題是：貪婪選了 type 3 森林之後，type 1 與 type 2 能不能把兩人各自補成生成樹？這只取決於 type 3 森林的**連通元件劃分**，而所有極大的 type 3 森林劃分都相同（都等於只用 type 3 時的元件），所以只要原圖對 Alice 可行，type 1 就一定補得起來，Bob 同理。

**演算法與答案**。兩個 union-find `alice`、`bob`。第一輪處理 type 3：同時 union 到兩邊，成功就保留（兩邊的狀態在這一輪始終相同，所以結果一致）。第二輪：type 1 只 union 到 `alice`，type 2 只 union 到 `bob`，成功才保留。最後若任一邊的元件數不是 1，回傳 -1；否則回傳 `len(edges) − 保留數`。這其實就是兩次 Kruskal，只是共用邊「權重最低」先處理。

```text
範例 1：n = 4，edges = [3,1,2] [3,2,3] [1,1,3] [1,2,4] [1,1,2] [2,3,4]

第一輪：type 3
  [3,1,2]   alice 合併 {1,2}、bob 合併 {1,2}             保留 1
  [3,2,3]   alice 合併 {1,2,3}、bob 合併 {1,2,3}         保留 2
第二輪：type 1 → alice，type 2 → bob
  [1,1,3]   alice：1、3 已同根                            刪
  [1,2,4]   alice：合併 {1,2,3,4}                         保留 3
  [1,1,2]   alice：已同根                                 刪
  [2,3,4]   bob：合併 {1,2,3,4}                           保留 4

alice 元件數 1、bob 元件數 1 → 答案 = 6 - 4 = 2

若反過來先處理 type 1（錯誤的順序）：
  [1,1,3] [1,2,4] [1,1,2]   alice 用 3 條 type 1 就連通了              保留 3
  [3,1,2] [3,2,3]           alice 已不需要，但 bob 需要                保留 5
  [2,3,4]                   bob 合併                                   保留 6
  答案 = 6 - 6 = 0（錯誤，正確答案是 2）
```

最後一段示範了順序的重要性：先用專屬邊讓 Alice 連通，之後的 type 3 對 Alice 而言都是多餘的，但 Bob 還是需要它們，於是同一段連通性被 type 1 和 type 3 各付了一次。type 3 優先就是在避免這種重複付費。

### 解法

```python
import itertools
import random


class DSU:
    def __init__(self, n: int):
        self.parent = list(range(n + 1))       # 節點編號 1..n
        self.count = n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        self.parent[ra] = rb
        self.count -= 1
        return True


def max_num_edges_to_remove(n: int, edges: list[list[int]]) -> int:
    alice, bob = DSU(n), DSU(n)
    used = 0
    for t, u, v in edges:                      # 第一輪：共用邊（type 3）優先
        if t == 3:
            a = alice.union(u, v)
            b = bob.union(u, v)                # 兩邊的狀態永遠相同，a == b
            used += a or b
    for t, u, v in edges:                      # 第二輪：各自的專屬邊
        if t == 1:
            used += alice.union(u, v)
        elif t == 2:
            used += bob.union(u, v)
    if alice.count != 1 or bob.count != 1:
        return -1
    return len(edges) - used


def brute(n, edges):
    m = len(edges)
    for keep in range(m + 1):                  # 保留的邊越少越好，從小到大試
        for subset in itertools.combinations(edges, keep):
            ok = True
            for who in (1, 2):
                d = DSU(n)
                for t, u, v in subset:
                    if t == 3 or t == who:
                        d.union(u, v)
                ok &= d.count == 1
            if ok:
                return m - keep
    return -1


assert max_num_edges_to_remove(4, [[3, 1, 2], [3, 2, 3], [1, 1, 3], [1, 2, 4], [1, 1, 2], [2, 3, 4]]) == 2
assert max_num_edges_to_remove(4, [[3, 1, 2], [3, 2, 3], [1, 1, 4], [2, 1, 4]]) == 0
assert max_num_edges_to_remove(4, [[3, 2, 3], [1, 1, 2], [2, 3, 4]]) == -1
assert max_num_edges_to_remove(1, []) == 0
assert max_num_edges_to_remove(2, [[1, 1, 2], [2, 1, 2], [3, 1, 2]]) == 2   # 一條共用邊取代兩條專屬邊
for _ in range(300):
    n = random.randint(1, 5)
    edges = []
    for _ in range(random.randint(0, 7)):
        if n >= 2:
            u, v = random.sample(range(1, n + 1), 2)
            edges.append([random.randint(1, 3), u, v])
    assert max_num_edges_to_remove(n, edges) == brute(n, edges)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n + m · α(n))，m 是邊數：兩輪掃描，每條邊至多兩次 union。空間 O(n)，兩個 union-find。暴力枚舉是 O(2^m · m)。邊界情況：n = 1 時兩人本來就完全可走，所有邊都能刪（`brute` 驗證了 n = 1 且沒有邊的情況）；只要有一人無法連通就回傳 -1，即使另一人可以；type 3 在第一輪時 `alice.union` 和 `bob.union` 的結果必定相同，程式用 `a or b` 只是保險；同一對節點可以有不同類型的邊（範例 4），三種都是不同的邊；節點從 1 開始，`parent` 開 n + 1 個位置，元件數從 n 開始計，不把 0 算進去。

### Follow-up

> [!question]- F1. 如果每條邊有權重，要讓保留的邊總權重最小（仍然兩人都完全可走）呢？
> 這是兩個生成樹共用部分邊的最佳化，type 3 優先不再一定最好：一條很貴的 type 3 可能不如一條便宜的 type 1 加一條便宜的 type 2。type 3 的價值在於同時提供兩份連通性，但一旦權重不同，「共用」和「便宜」就互相拉扯，一般情況下沒有簡單的貪婪，要靠更一般的組合最佳化工具或搜尋；但若題目保證每條 type 3 的權重都 ≤ 對應的 type 1 與 type 2，原本的交換論證仍成立，只要在每一輪內部依權重排序做 Kruskal 即可，O(m log m)。面試中能指出「無權版本的貪婪依賴每條邊的價值相同」就足夠。

> [!question]- F2. 如果有 k 個人（不只兩人），每條邊標記一組能走它的人呢？
> 推廣後的直覺是「能服務越多人的邊越優先」，依「能走它的人數」由多到少處理，每個人一個 union-find，一條邊只要對其中某人能合併就保留，並 union 到所有能走它的人身上。但當不同的人集合交錯時（例如 {A, B} 與 {B, C} 兩類邊），這個貪婪不一定最優，因為邊的價值不再是全序的；兩人的情況恰好是「type 3 包含 type 1 和 type 2」的巢狀結構，貪婪才成立。面試時能說出「巢狀時貪婪對、交錯時不一定」是加分的觀察。

> [!question]- F3. 如果要輸出具體保留了哪些邊呢？
> 在兩輪掃描中，把 union 成功的邊加入 `kept` 列表即可，type 3 只要在第一輪成功就記一次。這組邊對 Alice 是 type 1 與 type 3 構成的生成樹、對 Bob 是 type 2 與 type 3 構成的生成樹。時間仍是 O(n + m · α(n))。若題目要求在多個最佳解中選「保留的 type 3 最多」或「字典序最小」，只要在每一輪內部調整處理順序即可，因為保留數只取決於每一輪的元件數變化。

> [!question]- F4. 如果邊是陸續加入的，每加入一條就要回報目前「最多能刪幾條」（或 -1）呢？
> 增量情況下要小心：新加入的 type 3 可能讓之前保留的 type 1、type 2 變成多餘。好在答案只取決於數量：保留數 = (n − c₃) + (c₃ − c_A) + (c₃ − c_B)，其中 c₃ 是只用 type 3 的元件數，c_A 是 Alice 用 type 1 和 type 3 的元件數，c_B 同理。維護三個 union-find（只含 type 3、Alice、Bob），每條新邊 union 到對應的結構，三個元件數各 O(α(n)) 更新，答案是 `m - 保留數`（c_A 與 c_B 都是 1 時），否則 -1。這個公式化的觀點也是證明貪婪最優的另一種寫法。

### 心得

關鍵突破是把「最多刪幾條」改寫成「最少保留 2(n − 1) − k 條，k 是共用的 type 3 數」，於是目標變成最大化 k，而 type 3 優先的 union-find 正好讓 k 達到上限 n − c₃。它和本章的關係是：核心題 5（1319）用「成功合併的邊數」計算多餘的線，這題把同一個計算做在兩個 union-find 上，並加上「誰先處理」的貪婪；本質上是 Kruskal（第 18 章核心題 5）在無權圖上的應用。面試時先說「每人需要一棵生成樹」，再寫出保留數公式 2(n − 1) − k，最後說明為什麼 type 3 優先能讓 k 最大；這比只說「直覺上共用邊比較好」有說服力得多。

## 難題 5｜1697. Checking Existence of Edge Length Limited Paths｜Hard

### 題目

有一張 n 個節點（編號 0 到 n − 1）的無向圖，邊列表 `edge_list[i] = [u, v, dis]` 表示 u 和 v 之間有一條長度為 dis 的邊，**兩點之間可能有多條邊**。給一串查詢 `queries[j] = [p, q, limit]`，對每個查詢判斷：是否存在一條從 p 到 q 的路徑，路徑上**每一條**邊的長度都**嚴格小於** limit。回傳布林陣列。限制：`2 <= n <= 10⁵`，`1 <= len(edge_list), len(queries) <= 10⁵`，`p != q`，長度與 limit 在 `1` 到 `10⁹` 之間。

- 範例 1：`n = 3`，`edge_list = [[0, 1, 2], [1, 2, 4], [2, 0, 8], [1, 0, 16]]`，`queries = [[0, 1, 2], [0, 2, 5]]`。0 到 1 的邊長是 2 和 16，都不小於 2，回傳 False；0 → 1 → 2 用邊長 2 和 4，都小於 5，回傳 True。結果 `[False, True]`。
- 範例 2：`n = 5`，`edge_list = [[0, 1, 10], [1, 2, 5], [2, 3, 9], [3, 4, 13]]`，`queries = [[0, 4, 14], [1, 4, 13]]`。第一個查詢可以用所有邊，True；第二個查詢不能用長度 13 的邊，4 就孤立了，False。結果 `[True, False]`。
- 範例 3（邊界）：`n = 2`、`edge_list = [[0, 1, 5]]`、`queries = [[0, 1, 5], [0, 1, 6]]`，limit 等於邊長時不能用（嚴格小於），回傳 `[False, True]`。

### 提示

> [!tip]- 提示 1
> 每個查詢只用長度 < limit 的邊跑一次 BFS，O(q · (n + m))，太慢。如果 limit 越大，可用的邊只會越多；能不能讓多個查詢共用同一份計算？

> [!tip]- 提示 2
> 查詢可以離線處理（題目一次給完所有查詢）。把查詢依 limit 由小到大排序，邊也依長度排序。處理到某個查詢時，所有長度 < limit 的邊應該都已經被加入。

> [!tip]- 提示 3
> 用一個指標掃過排序後的邊，在處理每個查詢前，把長度 < limit 的邊全部 union。然後回答 `find(p) == find(q)`。記得把答案寫回查詢的原始位置。

### 詳解

**為什麼直覺做法不夠**。對每個查詢重新建圖並 BFS，是 O(q · (n + m))，在 10⁵ × 2 × 10⁵ = 2 × 10¹⁰ 的規模下完全不行。二分搜尋也幫不上忙，因為每個查詢的 limit 不同、起訖點也不同。真正的浪費在於：limit 較大的查詢所用的邊集合，**包含** limit 較小的查詢所用的邊集合，可是每次 BFS 都從零開始，沒有重複利用。

**突破點：離線排序，讓邊只增不減**。如果按 limit 由小到大處理查詢，那麼從一個查詢到下一個查詢，可用的邊只會多、不會少，這正是 union-find 的只增不減。把邊依長度排序，用指標 k 記錄「已經 union 到第幾條邊」；輪到 limit 為 L 的查詢時，把所有長度 < L 而還沒加入的邊加入，然後問 p、q 是否同根。每條邊只會被加入一次，所以總共 O(m) 次 union。這和難題 2（778）依門檻依序啟用是同一個掃描，差別只在這裡有很多個查詢，所以查詢也要排序。

**正確性**。處理查詢 j 時，union-find 中恰好包含所有長度 < limit_j 的邊：因為查詢依 limit 遞增處理，之前加入的邊都 < 之前的 limit ≤ limit_j；而 while 迴圈會把剩下所有 < limit_j 的邊補上，並在第一條 ≥ limit_j 的邊停下。所以集合劃分恰好是「只用長度 < limit_j 的邊」的連通元件，`find(p) == find(q)` 就是答案。多重邊不影響：重複的邊只會讓 union 回傳「已同根」，不改變任何東西。

```text
範例 1：邊依長度排序：(0,1,2) (1,2,4) (2,0,8) (1,0,16)
        查詢依 limit 排序：Q0 = (0,1, limit 2)、Q1 = (0,2, limit 5)

處理 Q0（limit = 2）：
  邊 (0,1,2)：2 < 2？否 → 停下，不加入任何邊
  集合：{0} {1} {2}      find(0) ≠ find(1) → ans[0] = False
處理 Q1（limit = 5）：
  邊 (0,1,2)：2 < 5 → union(0,1)      {0,1} {2}
  邊 (1,2,4)：4 < 5 → union(1,2)      {0,1,2}
  邊 (2,0,8)：8 < 5？否 → 停下
  find(0) == find(2) → ans[1] = True

答案寫回原位：[False, True]
```

指標 k 在整個過程中只往前走：處理 Q1 時不需要重新考慮 Q0 時看過的邊，這是離線排序省下工作量的地方。注意 Q0 的 limit 剛好等於邊長 2，「嚴格小於」讓這條邊不能用；如果把條件寫成 `<=`，就會錯誤地回答 True。

### 解法

```python
import random
from collections import deque


def distance_limited_paths_exist(n: int, edge_list: list[list[int]],
                                 queries: list[list[int]]) -> list[bool]:
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    edges = sorted(edge_list, key=lambda e: e[2])
    order = sorted(range(len(queries)), key=lambda i: queries[i][2])   # 依 limit 由小到大處理
    ans = [False] * len(queries)
    k = 0
    for i in order:
        p, q, limit = queries[i]
        while k < len(edges) and edges[k][2] < limit:                  # 嚴格小於
            u, v, _ = edges[k]
            parent[find(u)] = find(v)
            k += 1
        ans[i] = find(p) == find(q)
    return ans


def brute(n, edge_list, queries):
    res = []
    for p, q, limit in queries:
        adj = [[] for _ in range(n)]
        for u, v, d in edge_list:
            if d < limit:
                adj[u].append(v)
                adj[v].append(u)
        seen = {p}
        dq = deque([p])
        while dq:
            u = dq.popleft()
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    dq.append(v)
        res.append(q in seen)
    return res


assert distance_limited_paths_exist(3, [[0, 1, 2], [1, 2, 4], [2, 0, 8], [1, 0, 16]],
                                    [[0, 1, 2], [0, 2, 5]]) == [False, True]
assert distance_limited_paths_exist(5, [[0, 1, 10], [1, 2, 5], [2, 3, 9], [3, 4, 13]],
                                    [[0, 4, 14], [1, 4, 13]]) == [True, False]
assert distance_limited_paths_exist(2, [], [[0, 1, 100]]) == [False]
assert distance_limited_paths_exist(2, [[0, 1, 5]], [[0, 1, 5], [0, 1, 6]]) == [False, True]
for _ in range(300):
    n = random.randint(2, 7)
    el = [[*random.sample(range(n), 2), random.randint(1, 10)] for _ in range(random.randint(0, 10))]
    qs = [[*random.sample(range(n), 2), random.randint(1, 12)] for _ in range(random.randint(1, 8))]
    assert distance_limited_paths_exist(n, el, qs) == brute(n, el, qs)
print("all tests passed")
```

### 複雜度與邊界

時間 O(m log m + q log q + (m + q) · α(n))：排序邊與查詢，之後每條邊 union 一次、每個查詢 find 兩次。空間 O(n + q)，`parent`、查詢的排序索引與答案陣列（排序後的邊列表另佔 O(m)）。邊界情況：limit 等於邊長時該邊不能用，while 條件必須是 `<`；兩點之間的多重邊和自然重複的邊都只是失敗的 union；沒有任何邊時所有查詢都是 False；查詢排序時只排索引，答案要寫回 `ans[i]` 的原位，不能依處理順序 append。

### Follow-up

> [!question]- F1. 如果查詢是線上的（必須依序回答，不能排序），而邊列表是固定的呢（1724. Checking Existence of Edge Length Limited Paths II）？
> 預先依邊長做一次 Kruskal，但 union 時**不做 path compression**、只做 union by size，並在被掛上去的根上記錄掛上去時的邊長 `time[x]`。這樣樹高是 O(log n)，而且從任一節點往上走，經過的 `time` 是遞增的。查詢 (p, q, limit) 時，從 p 往上走，只走 `time < limit` 的父邊，停下的節點就是「只用 < limit 的邊時 p 所在集合的代表」；對 q 做同樣的事，比較兩者是否相同。每個查詢 O(log n)，前處理 O(m log m)。
> ```python
> class TimedDSU:
>     def __init__(self, n, edge_list):
>         self.parent, self.size = list(range(n)), [1] * n
>         self.time = [float("inf")] * n          # time[x]：x 被掛到父節點下時的邊長
>         for u, v, d in sorted(edge_list, key=lambda e: e[2]):
>             ru, rv = self._root(u), self._root(v)
>             if ru != rv:
>                 if self.size[ru] > self.size[rv]:
>                     ru, rv = rv, ru
>                 self.parent[ru], self.time[ru] = rv, d
>                 self.size[rv] += self.size[ru]
>
>     def _root(self, x):
>         while self.parent[x] != x:
>             x = self.parent[x]
>         return x
>
>     def _root_before(self, x, limit):           # 只走「時間 < limit」的父邊
>         while self.parent[x] != x and self.time[x] < limit:
>             x = self.parent[x]
>         return x
>
>     def query(self, p, q, limit):
>         return self._root_before(p, limit) == self._root_before(q, limit)
> ```

> [!question]- F2. 如果每個查詢要問的是「最小的 limit 讓 p、q 連通」呢？
> 這是 minimax 路徑問題：答案是 p 到 q 所有路徑中「最大邊長」的最小值（再加一，因為題目是嚴格小於）。最小生成樹有一個性質：任意兩點在 MST 上的路徑，正好是它們之間的 minimax 路徑。所以先用 Kruskal 建 MST，O(m log m)，再用 binary lifting 預處理每個節點往上 2^k 步的祖先與沿路最大邊長，每個查詢在 O(log n) 內求出 LCA 路徑上的最大邊長（第 12 章核心題 5 的 F4）。F1 的 TimedDSU 也能回答：讓 p、q 往上走到最近的共同祖先，路上最大的 `time` 就是答案。

> [!question]- F3. 如果查詢不是問「是否連通」，而是問「p 在只用 < limit 的邊時能到達幾個節點」呢？
> 同樣的離線掃描，只是回答時改成 `size[find(p)]`，因為 union by size 已經在根上維護了集合大小。若要的是「能到達的節點中編號最小的是誰」或「節點權重的總和」，就在根上維護對應的值，合併時取 min 或相加，17.4 節的「在根上掛資訊」直接適用。每個查詢仍是 O(α(n))，總時間不變。

> [!question]- F4. 如果邊也會陸續加入（邊與查詢交錯，而且查詢要的是「當下」的圖）呢？
> 這時有兩個維度：時間（邊何時加入）和長度（是否 < limit），單純依 limit 排序會把「還沒加入」的邊也算進去。若所有事件都可以離線，可以把每條邊看成「時間 ≥ t_e 且長度 < limit 才可用」，對時間做分治（CDQ 分治）或按時間塊重建；比較好寫的做法是對事件分塊：每 B 個事件，用目前所有的邊重建一次 F1 的 TimedDSU，O(m log m)；塊內新加入的邊至多 B 條，回答查詢時先用 TimedDSU 求出 p、q 以及這些新邊兩端「只用 < limit 的舊邊」時的代表，再在這至多 2B + 2 個代表構成的小圖上，用新邊中長度 < limit 的那些做一次 BFS，每個查詢 O(B log n)。取 B ≈ √m 時總時間約 O(q √m · log m)。面試中這通常是開放討論，重點是指出「兩個單調維度無法同時用一次排序處理」。

### 心得

關鍵突破是把查詢依 limit 排序，讓「可用的邊」隨著處理順序只增不減，於是 q 次獨立的 BFS 變成一次 Kruskal 式的掃描，每條邊只處理一次。它和本章其他題的關係是：難題 2（778）是同一個掃描在單一查詢上的版本，難題 3（803）用時間倒流達到同樣的「只增不減」，三題一起構成了 union-find 最重要的離線技巧。面試時先說每個查詢 BFS 的 O(q(n + m))，指出「limit 大的查詢的邊集合包含 limit 小的」，然後提出排序加雙指標；寫程式時要特別說明三件事：只排序索引以便寫回原位、`<` 而非 `<=`、多重邊不需要特別處理。若面試官追問線上版本，就用 F1 的「不壓縮路徑、記錄合併時間」接上。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 數連通元件 | 給一張圖，問有幾群、最大群多大 | 初始 count = n，成功 union 才減一；size 存在根上 | 核心題 1（547）、200（第 15 章）、323 Number of Connected Components |
| 偵測環、找多餘邊 | 「第一條讓圖不再是樹的邊」 | union 失敗即為閉合環的邊 | 核心題 2（684）、261 Graph Valid Tree |
| 有向樹的多餘邊 | 有根樹多一條有向邊 | 先用入度縮小候選，再用 union-find 檢查剩下的邊有無環 | 難題 1（685） |
| 透過共用屬性分組 | 「共用任一 email／電話就是同一人」 | 把物件和屬性的第一個擁有者合併；key 不是整數時先編號 | 核心題 3（721）、839 Similar String Groups、947 Most Stones Removed |
| 等式與不等式限制 | `==` 必須合併、`!=` 不能同群 | 先合併所有等式，再檢查所有不等式 | 核心題 4（990）、1061 Lexicographically Smallest Equivalent String |
| 用元件數算答案 | 「最少加幾條／搬幾條邊」 | 答案由元件數 c 與多餘邊數決定，通常是 c − 1 | 核心題 5（1319）、947 |
| 依門檻依序啟用 | 「最小的 t 讓兩點連通」「minimax 路徑」 | 依權重排序格子或邊，逐一 union，第一次連通即答案 | 難題 2（778）、1631、1102 Path With Maximum Minimum Value |
| 離線查詢排序 | 每個查詢帶一個門檻，可以離線 | 查詢與邊都排序，雙指標加入 | 難題 5（1697）、2503 Maximum Number of Points From Grid Queries |
| 離線倒序 | 依序刪除，每次問變化 | 先全刪，倒著加回；虛擬節點計數 | 難題 3（803）、1970 Last Day Where You Can Still Cross、2382 |
| 多個 union-find | 不同角色有不同可用的邊 | 每個角色一個 union-find，共用邊優先 | 難題 4（1579） |
| 最小生成樹 | 連通所有點、總成本最小 | Kruskal：邊依權重排序，union 成功才保留 | 1584（第 18 章核心題 5）、1135 |
| 帶權 union-find | 變數之間有比值、差值或奇偶關係 | 父邊上存相對值，find 時沿路累積 | 399 Evaluate Division、785 的 XOR 版本、核心題 4 F4 |
| 線上門檻查詢 | 門檻查詢不能排序 | 不壓縮路徑、記錄合併時間；或 Kruskal reconstruction tree | 1724（難題 5 F1） |

**下限與上限**。最簡單的形式是「給一張圖、數元件」，例如 547 與 323，考的只是模板寫對、知道只在成功合併時減一。中間層是把題目建模成連通性：721 要想到節點是帳號、邊是共用 email；990 要想到 `==` 與 `!=` 要分兩趟；1319 要從元件數推出答案並證明多餘的線一定夠。上限的題目難在三個方向，常常需要先做一個不屬於 union-find 本身的觀察：第一，**把問題推回只增不減**，例如 803 的時間倒流、778 與 1697 的門檻排序，沒有這一步 union-find 根本無法使用；第二，**和其他條件組合**，例如 685 要先用入度把候選縮成兩條、1579 要用交換論證證明共用邊優先；第三，**union-find 本身要擴充**，例如帶權 union-find 處理比值與奇偶、記錄合併時間的 union-find 回答線上門檻查詢、可回滾的 union-find 處理離線動態連通性。

**與其他 pattern 的關係**。Union-find 和 BFS／DFS（第 15 章）在靜態圖的連通性上是等價的，選擇的依據是「邊是否陸續加入」與「是否需要路徑或距離」：要距離選 BFS，邊陸續加入選 union-find。和拓撲排序（第 16 章）的分界是方向：有向的依賴關係用拓撲排序，無向的等價關係用 union-find；990 F3 示範了兩者組合，先用 union-find 縮點，再拓撲排序。和最小生成樹、最短路徑（第 18 章）的關係最緊密：Kruskal 就是「排序 + union-find」，而 778、1631 這類 minimax 路徑題同時有 Dijkstra 和 Kruskal 兩種解法。和 binary search（第 8 章）的關係是：「二分答案 + BFS 檢查連通」幾乎都能改寫成「排序 + union-find 依序加入」，後者少一個 log，而且不需要重複搜尋。

**容易混淆之處**。第一，union-find 不支援刪除，看到刪除先問「能不能離線倒序」，不能的話通常要換方法，而不是硬改 union-find。第二，union-find 只知道「是否同群」，不知道「怎麼連過去」，題目要路徑、要證據（990 F1）時要另外建圖搜尋。第三，有向圖的連通性（強連通元件）不能用 union-find，因為 a 能到 b 不代表 b 能到 a；685 用 union-find 只是在檢查「當作無向邊看有沒有環」，方向的部分由入度檢查負責。第四，path compression 會破壞樹的形狀，需要「沿著原始結構往上走」的技巧（1724 的合併時間、可回滾 union-find）時，必須只用 union by size 而不壓縮路徑。

## 本章重點整理

- Union-find 用森林表示等價關係：每群一棵樹、根是代表；`find` 找根、`union` 把一個根掛到另一個根下，兩者同根代表同群。
- 一定要同時用 path compression（或 path halving）與 union by size，每次操作攤銷 O(α(n))，近乎常數；只用其中一個是 O(log n)。
- `find` 用迭代寫法，避免 Python 的遞迴深度限制；`union` 回傳「是否真的合併」，數元件、找環、Kruskal 都靠它。
- 判斷同群、分組輸出時一律用 `find(x)`，不要直接讀 `parent[x]`；整群的統計量（size、最小值、總和）存在根上，讀取時用 `size[find(x)]`。
- 數元件：初始 count = n，成功合併才減一；k 個元件需要 k − 1 條邊才能連通，1319 的答案就是元件數減一（線總數足夠時）。
- 依序加入邊時，第一條兩端已同根的邊閉合了環，而且是環上最後出現的邊（684）；有向版本要先用入度縮小候選（685）。
- 等價與不等價限制要分兩趟：先合併所有 `==`，再檢查所有 `!=`（990）；變數只有兩種值時要改用帶權（奇偶）union-find。
- 帶權 union-find 在父邊上存相對關係（比值、差值、XOR），`find` 時沿路累積，用來處理 399 這類「變數之間的關係」題目。
- 三個把問題推回「只增不減」的技巧：虛擬節點代表特殊群（803 的天花板）、依門檻排序後依序加入（778、1697）、離線倒序把刪除變成加入（803）。
- 多個角色各自要連通時，每人一個 union-find，共用邊優先處理，保留數 = 2(n − 1) − 共用邊數（1579），這是 Kruskal 的交換論證。
- 「最小化路徑上最大值」的 minimax 問題，同時可以用排序 + union-find、Dijkstra 變形、二分答案 + BFS 解，union-find 最簡單也最快。
- Union-find 的能力邊界：不支援刪除、不給路徑或距離、不處理有向關係；需要線上門檻查詢時，改成不壓縮路徑並記錄合併時間。
