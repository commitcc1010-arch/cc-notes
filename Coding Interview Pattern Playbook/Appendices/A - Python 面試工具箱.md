# 附錄 A　Python 面試工具箱

> [!abstract] 本附錄地圖
> **用途**：第 3 章 3.9 節列出了面試最常用的 Python 工具與幾個陷阱，本附錄是它的詳細版。每一節說明一種工具的用法、複雜度與容易出錯的地方，並附一段可以直接執行的範例。
>
> **你會找到**：
> - 內建容器：`list`、`tuple`、`dict`、`set`，以及 `collections` 的 `deque`、`Counter`、`defaultdict`、`OrderedDict`
> - 演算法工具：`heapq`（max-heap、tie-breaker、lazy deletion）、`bisect`（含 `key` 參數）、排序與 `cmp_to_key`、`itertools`
> - 記憶化與遞迴：`functools.cache`、`lru_cache`、遞迴深度與改寫成迭代的時機
> - 字串、整數與位元運算的細節：負數的除法與取餘、無限精度整數、`bit_count` 與負數的位元表示
> - 常見陷阱清單，以及面試時的程式風格建議
>
> **讀法**：第一次可以快速瀏覽複雜度表；寫題時遇到不確定的語法再回來查對應小節。所有程式都以 Python 3.11+ 與標準函式庫為準。

## A.1 list 與 tuple

`list` 是動態陣列（dynamic array）：元素連續存放，所以索引是 O(1)，在尾端增刪是攤銷 O(1)，但在開頭或中間插入、刪除時，後面的元素都要搬移，成本是 O(n)。面試中最常見的效能錯誤就是把 `list` 當 queue 用，在迴圈裡呼叫 `pop(0)`，讓原本 O(n) 的 BFS 變成 O(n²)；這種情況要改用 A.3 節的 `deque`。另一個要記住的是切片（slicing）會複製，`nums[1:]` 的成本與切出來的長度成正比，在遞迴中反覆切片很容易讓複雜度多一個 n 的因子。

`tuple` 是不可變的序列。因為不可變，只要元素都可雜湊（hashable），`tuple` 本身就可以雜湊，所以能當 `dict` 的 key 或放進 `set`，例如用 `(row, col)` 記錄走過的格子、用 `(i, j)` 當記憶化的狀態。`tuple` 之間依字典序（lexicographic order）比較：先比第一個元素，相同再比第二個，這個性質在排序與 heap 中非常好用（A.4、A.7 節）。

| 操作 | 複雜度 | 說明 |
|---|---|---|
| `lst[i]`、`lst[i] = x`、`len(lst)` | O(1) | |
| `lst.append(x)`、`lst.pop()` | 攤銷 O(1) | 當 stack 用 |
| `lst.pop(i)`、`lst.insert(i, x)`、`del lst[i]` | O(n − i) | 開頭最慢，O(n) |
| `x in lst`、`lst.index(x)`、`lst.count(x)` | O(n) | 需要頻繁查詢就改用 `set` |
| `lst[a:b]` | O(b − a) | 產生新的 list |
| `lst.extend(other)`、`lst + other` | O(k)、O(n + k) | `+` 會建立新 list |
| `lst.sort()`、`sorted(lst)` | O(n log n) | 穩定排序 |
| `min`、`max`、`sum`、`lst.reverse()`、`lst.copy()` | O(n) | |
| `[0] * n` | O(n) | 預先配置 DP 陣列 |

```python
nums = [3, 1, 4]
nums.append(1)
assert nums.pop() == 1 and nums == [3, 1, 4]
assert nums.pop(0) == 3                 # O(n)：後面的元素都要左移
nums.insert(0, 9)                       # O(n)
assert nums == [9, 1, 4]
assert nums[-1] == 4 and nums[::-1] == [4, 1, 9]

# 切片是複製：改副本不影響原本的 list
tail = nums[1:]
tail[0] = 100
assert nums == [9, 1, 4]

# 解包、enumerate、zip（zip 以較短的為準）
first, *rest = [1, 2, 3]
assert first == 1 and rest == [2, 3]
assert list(enumerate("ab")) == [(0, "a"), (1, "b")]
assert list(zip([1, 2, 3], "ab")) == [(1, "a"), (2, "b")]

# argmax：用 key 取出最大值的索引
vals = [5, 9, 2, 9]
assert max(range(len(vals)), key=vals.__getitem__) == 1   # 平手時取第一個

# list.sort() 原地排序並回傳 None
arr = [3, 1, 2]
assert arr.sort() is None and arr == [1, 2, 3]

# tuple 可雜湊，可當 key；依字典序比較
visited = {(0, 0), (1, 2)}
assert (1, 2) in visited
assert (1, 5) < (2, 0) and (1, 2) < (1, 2, 0)

# list 不可雜湊，不能當 key
try:
    _ = {[1, 2]: 0}
    raised = False
except TypeError:
    raised = True
assert raised

# 交換兩個變數不需要暫存
a, b = 1, 2
a, b = b, a
assert (a, b) == (2, 1)
print("all tests passed")
```

## A.2 dict 與 set

`dict` 與 `set` 都是 hash table，查詢、插入、刪除平均 O(1)。這個「平均」有兩個前提要記得：第一，計算 hash 本身要時間，字串或 `tuple` 當 key 時成本是 O(key 長度)；第二，最壞情況（大量碰撞）會退化到 O(n)，但面試中以平均情況討論是慣例。從 Python 3.7 起 `dict` 保證保留插入順序，所以走訪 `dict` 的順序就是第一次插入 key 的順序，這在需要「依出現順序輸出」的題目中很方便。

計數與分組有幾種寫法。`d.get(k, 0) + 1` 最直接；`d.setdefault(k, []).append(v)` 可以在一行內完成分組；更常見的是直接用 A.6 節的 `Counter` 與 `defaultdict`。要注意走訪 `dict` 時不能改變它的大小，否則會丟出 `RuntimeError`；需要邊走邊刪時，先用 `list(d)` 複製一份 key。

`set` 支援集合運算：交集 `&`、聯集 `|`、差集 `-`、對稱差 `^`、子集 `<=`。`set` 本身不可雜湊，要把集合當 key 時用 `frozenset`。另外 `{}` 是空的 `dict`，空的 `set` 要寫 `set()`。

| 操作 | 平均複雜度 | 說明 |
|---|---|---|
| `d[k]`、`d[k] = v`、`k in d`、`del d[k]`、`d.get(k)` | O(1) | 最壞 O(n)；key 的 hash 成本另計 |
| `d.pop(k, default)`、`d.setdefault(k, v)` | O(1) | |
| 走訪 `d`、`d.items()`、`d.copy()` | O(n) | |
| `s.add(x)`、`s.discard(x)`、`x in s` | O(1) | `remove` 找不到會丟 `KeyError` |
| `a & b` | O(min(len(a), len(b))) | |
| `a \| b` | O(len(a) + len(b)) | |
| `a - b`、`a <= b` | O(len(a)) | |
| `set(iterable)` | O(n) | 一次去重 |

```python
count: dict[str, int] = {}
for ch in "banana":
    count[ch] = count.get(ch, 0) + 1
assert count == {"b": 1, "a": 3, "n": 2}
assert list(count) == ["b", "a", "n"]          # 保留插入順序

groups: dict[int, list[str]] = {}
for w in ["hi", "a", "yo"]:
    groups.setdefault(len(w), []).append(w)
assert groups == {2: ["hi", "yo"], 1: ["a"]}

assert count.pop("b") == 1 and "b" not in count
assert count.pop("zzz", None) is None          # 給預設值就不會丟 KeyError

# 值 → 索引的反向對照表（Two Sum 的核心）
pos = {v: i for i, v in enumerate([10, 20, 30])}
assert pos[20] == 1

# 走訪時改變大小會出錯；先複製 key
d = {1: "a", 2: "b", 3: "c"}
try:
    for k in d:
        del d[k]
    raised = False
except RuntimeError:
    raised = True
assert raised
d = {1: "a", 2: "b", 3: "c"}
for k in list(d):
    if k % 2 == 1:
        del d[k]
assert d == {2: "b"}

# 集合運算
a, b = {1, 2, 3}, {2, 3, 4}
assert a & b == {2, 3} and a | b == {1, 2, 3, 4}
assert a - b == {1} and a ^ b == {1, 4}
assert {2, 3} <= a
s: set[int] = set()
s.add(5)
s.discard(7)                                   # 不存在也不報錯
assert s == {5} and type({}) is dict

# frozenset 可雜湊，可以當 key
seen = {frozenset({1, 2}): "pair"}
assert seen[frozenset({2, 1})] == "pair"
print("all tests passed")
```

## A.3 deque

`collections.deque` 是雙端佇列（double-ended queue），兩端的 `append`、`appendleft`、`pop`、`popleft` 都是 O(1)，所以 BFS 的 queue、monotonic deque（單調佇列）都用它。它的代價是隨機存取不快：`dq[0]` 與 `dq[-1]` 是 O(1)，但存取中間的元素是 O(n)，也不支援切片。設定 `maxlen` 後，超過長度時會自動從另一端丟掉元素，適合「只保留最近 k 個」的情境。

BFS 需要「一層一層」處理時，常見寫法是在每層開始時記下 `len(q)`，只彈出這麼多個元素；這樣不需要在 queue 中額外存距離。monotonic deque 則是存索引、維持對應值單調，用來在 O(n) 內求每個滑動窗口的最大值（第 6 章難題 2（239. Sliding Window Maximum））。

| 操作 | 複雜度 | 說明 |
|---|---|---|
| `append`、`appendleft`、`pop`、`popleft` | O(1) | |
| `dq[0]`、`dq[-1]`、`len(dq)` | O(1) | |
| `dq[i]`（中間） | O(n) | 不支援切片 |
| `x in dq`、`dq.remove(x)` | O(n) | |
| `dq.rotate(k)` | O(k) | 正數向右轉 |
| `deque(maxlen=k)` 的 `append` | O(1) | 滿了自動丟掉另一端 |

```python
from collections import deque

q = deque([1, 2, 3])
q.append(4)
q.appendleft(0)
assert q.popleft() == 0 and q.pop() == 4
assert q[0] == 1 and q[-1] == 3
q.rotate(1)
assert list(q) == [3, 1, 2]

recent = deque(maxlen=3)
for x in range(5):
    recent.append(x)
assert list(recent) == [2, 3, 4]


def bfs_levels(grid: list[str], start: tuple[int, int]) -> int:
    """回傳從 start 走到最遠可達格子的步數；'#' 是牆。"""
    rows, cols = len(grid), len(grid[0])
    seen = {start}
    q = deque([start])
    steps = -1
    while q:
        steps += 1
        for _ in range(len(q)):            # 只處理目前這一層
            r, c = q.popleft()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != "#" and (nr, nc) not in seen:
                    seen.add((nr, nc))
                    q.append((nr, nc))
    return steps


assert bfs_levels(["..", ".."], (0, 0)) == 2
assert bfs_levels([".#", "#."], (0, 0)) == 0


def window_max(nums: list[int], k: int) -> list[int]:
    dq: deque[int] = deque()               # 存索引，對應的值由前往後遞減
    out = []
    for i, x in enumerate(nums):
        while dq and nums[dq[-1]] <= x:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - k:                 # 隊首已離開窗口
            dq.popleft()
        if i >= k - 1:
            out.append(nums[dq[0]])
    return out


assert window_max([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]
assert window_max([4], 1) == [4]
print("all tests passed")
```

## A.4 heapq

`heapq` 把一般的 `list` 當成 binary heap 操作，而且只有 min-heap：`heap[0]` 永遠是最小值。`heappush` 與 `heappop` 是 O(log n)，`heapify` 把現成的 list 原地變成 heap 只要 O(n)，比逐一 push 的 O(n log n) 好。`heappushpop(h, x)` 先 push 再 pop、`heapreplace(h, x)` 先 pop 再 push，都只做一次調整，在維護大小為 k 的 heap 時很常用。

**max-heap 技巧。** 數值的 max-heap 最簡單的做法是存負值，取出時再加負號。字串或其他不能取負的值，可以包一個 `__lt__` 反向比較的類別。Python 3.14 起標準函式庫也公開了 `heappush_max` 等函式，但面試環境的版本不一定這麼新，存負值是最保險的寫法。

**tuple 比較與 tie-breaker。** heap 中放 `(priority, item)` 時，priority 相同就會比較 item；如果 item 是 `dict` 或自訂物件這種不能比較的型別，會丟出 `TypeError`。解法是在中間放一個遞增的計數器當 tie-breaker（平手時的決勝欄位），例如 `(priority, next(counter), item)`，計數器永遠不會相同，所以不會比較到 item，而且相同 priority 時會依加入順序取出。反過來，有時題目正需要多欄位的順序，例如「頻率高的優先，頻率相同時字典序小的優先」，直接放 `(-freq, word)` 就能讓 tuple 比較替你完成。

**lazy deletion（延遲刪除）。** heap 不支援有效率地刪除任意元素，`list.remove` 加上重新 `heapify` 是 O(n)。延遲刪除的做法是：要刪除某個值時，先在一個計數表中記下「這個值待刪除」，不真的去動 heap；等到它浮到堆頂時再丟掉。每個元素最多被 push 與 pop 各一次，所以總成本仍是每次操作攤銷 O(log n)，代價是 heap 中可能暫時留著已刪除的元素，大小上限是總 push 次數。這個技巧用在滑動窗口中位數、The Skyline Problem（第 9 章難題 1（218））等需要「從 heap 中移除離開窗口的元素」的題目。

| 操作 | 複雜度 | 說明 |
|---|---|---|
| `heapq.heappush(h, x)`、`heapq.heappop(h)` | O(log n) | |
| `heapq.heapify(lst)` | O(n) | 原地 |
| `h[0]` | O(1) | 只看不取 |
| `heapq.heappushpop`、`heapq.heapreplace` | O(log n) | 一次調整 |
| `heapq.nlargest(k, it)`、`heapq.nsmallest(k, it)` | O(n log k) | k 接近 n 時直接排序 |
| `heapq.merge(*sorted_iters)` | 每個元素 O(log k) | 合併 k 個已排序序列 |
| lazy deletion 的 `remove` | O(1) | 實際刪除攤銷到 `pop` |

```python
import heapq
from collections import Counter
from itertools import count

nums = [5, 1, 8, 3, 9, 2]
h = nums[:]
heapq.heapify(h)
assert h[0] == 1 and heapq.heappop(h) == 1 and h[0] == 2

# max-heap：存負值
max_heap = [-x for x in nums]
heapq.heapify(max_heap)
assert -heapq.heappop(max_heap) == 9 and -max_heap[0] == 8


# 不能取負的值：用反向比較的包裝類別
class Desc:
    __slots__ = ("val",)

    def __init__(self, val: str) -> None:
        self.val = val

    def __lt__(self, other: "Desc") -> bool:
        return self.val > other.val


words_heap = [Desc(w) for w in ["pear", "apple", "zoo"]]
heapq.heapify(words_heap)
assert heapq.heappop(words_heap).val == "zoo"


# 大小為 k 的 min-heap 保留最大的 k 個
def top_k(nums: list[int], k: int) -> list[int]:
    heap: list[int] = []
    for x in nums:
        if len(heap) < k:
            heapq.heappush(heap, x)
        elif x > heap[0]:
            heapq.heapreplace(heap, x)
    return sorted(heap, reverse=True)


assert top_k(nums, 3) == [9, 8, 5] == heapq.nlargest(3, nums)

# tie-breaker：priority 相同時不要比較到 dict
tasks: list[tuple[int, int, dict]] = []
order = count()
for pri, payload in [(2, {"id": "a"}), (1, {"id": "b"}), (1, {"id": "c"})]:
    heapq.heappush(tasks, (pri, next(order), payload))
assert [heapq.heappop(tasks)[2]["id"] for _ in range(3)] == ["b", "c", "a"]

# 多欄位順序：頻率高的優先，相同時字典序小的優先
freq = Counter(["b", "a", "c", "a", "b", "d"])
heap2 = [(-f, w) for w, f in freq.items()]
heapq.heapify(heap2)
assert [heapq.heappop(heap2)[1] for _ in range(3)] == ["a", "b", "c"]

# 合併已排序序列
assert list(heapq.merge([1, 4, 7], [2, 5], [3, 6])) == [1, 2, 3, 4, 5, 6, 7]


class LazyMinHeap:
    """支援刪除任意值的 min-heap；remove 只登記，等浮到堆頂才真的丟掉。"""

    def __init__(self) -> None:
        self.heap: list[int] = []
        self.pending: Counter[int] = Counter()   # 值 → 尚未實際刪除的次數
        self.size = 0                            # 有效元素個數

    def push(self, x: int) -> None:
        heapq.heappush(self.heap, x)
        self.size += 1

    def remove(self, x: int) -> None:            # 呼叫者保證 x 存在
        self.pending[x] += 1
        self.size -= 1

    def _prune(self) -> None:
        while self.heap and self.pending[self.heap[0]] > 0:
            self.pending[heapq.heappop(self.heap)] -= 1

    def top(self) -> int:
        self._prune()
        return self.heap[0]

    def pop(self) -> int:
        self._prune()
        self.size -= 1
        return heapq.heappop(self.heap)


lh = LazyMinHeap()
for x in [5, 1, 3, 1]:
    lh.push(x)
lh.remove(1)
assert lh.top() == 1 and lh.size == 3      # 還有另一個 1
lh.remove(1)
assert lh.pop() == 3 and lh.size == 1 and lh.top() == 5
print("all tests passed")
```

## A.5 bisect

`bisect` 在已排序的序列上做 binary search（二分搜尋）。`bisect_left(a, x)` 回傳第一個 `>= x` 的位置，`bisect_right(a, x)` 回傳第一個 `> x` 的位置，兩者相減就是 `x` 出現的次數。記住這兩個定義，其他問題都能換算：最後一個 `<= x` 的位置是 `bisect_right(a, x) - 1`，最後一個 `< x` 的位置是 `bisect_left(a, x) - 1`。結果可能等於 `len(a)`，用它當索引前要先檢查邊界。

Python 3.10 起 `bisect` 系列函式支援 `key` 參數，但要注意一個不對稱：`key` 只套用在序列的元素上，**不會**套用在要找的 `x` 上，所以 `x` 要傳「已經轉換過的值」。例如在依開始時間排序的區間中找開始時間為 4 的位置，要寫 `bisect_left(intervals, 4, key=lambda iv: iv[0])`，而不是傳一個區間進去。`insort` 則相反，它會對插入的元素套用 `key`。

`key` 參數還能讓你用 `bisect` 對答案做二分（第 8 章）：`range` 物件支援索引與長度，把「這個答案是否可行」寫成回傳 `bool` 的 `key`，因為 `False < True`，`bisect_left(range(lo, hi), True, key=feasible)` 就是第一個可行答案的偏移量。面試時這個寫法很精簡，但要能說清楚它要求 `feasible` 單調（前段全是 `False`、後段全是 `True`）；如果面試官希望看到手寫的二分，就改用第 8 章的模板。

`insort` 的搜尋是 O(log n)，但插入 `list` 仍是 O(n)，所以「不斷插入並查詢排名」的題目用 `insort` 會是 O(n²)。標準函式庫沒有平衡樹結構；有些線上評測平台預裝第三方的 sorted container，但面試中要先問能不能用，否則改用 heap 加 lazy deletion、Fenwick tree（樹狀陣列，第 26 章）等做法。

| 操作 | 複雜度 | 結果的意義 |
|---|---|---|
| `bisect_left(a, x)` | O(log n) | 第一個 `>= x` 的索引 |
| `bisect_right(a, x)` | O(log n) | 第一個 `> x` 的索引 |
| `bisect_left(a, x, lo, hi)` | O(log(hi − lo)) | 只在 `a[lo:hi]` 範圍內搜尋，不複製 |
| `bisect_left(a, x, key=f)` | O(log n) 次 `f` | `x` 必須是已轉換的值 |
| `insort(a, x)` | O(n) | 搜尋 O(log n)，插入 O(n) |

```python
from bisect import bisect_left, bisect_right, insort

arr = [1, 3, 3, 3, 7]
assert bisect_left(arr, 3) == 1 and bisect_right(arr, 3) == 4
assert bisect_right(arr, 3) - bisect_left(arr, 3) == 3     # 出現次數
assert bisect_left(arr, 8) == len(arr)                     # 找不到時可能是 len(a)
assert bisect_right(arr, 5) - 1 == 3                       # 最後一個 <= 5
assert bisect_left(arr, 3) - 1 == 0                        # 最後一個 < 3


def contains(a: list[int], x: int) -> bool:
    i = bisect_left(a, x)
    return i < len(a) and a[i] == x


assert contains(arr, 7) and not contains(arr, 4) and not contains([], 1)

# key 只套用在元素上，x 要傳已轉換的值
intervals = [(1, "a"), (4, "b"), (9, "c")]
assert bisect_left(intervals, 4, key=lambda iv: iv[0]) == 1
insort(intervals, (5, "z"), key=lambda iv: iv[0])          # insort 會對新元素套用 key
assert [iv[0] for iv in intervals] == [1, 4, 5, 9]


# 對答案二分：最小的吃香蕉速度（第 8 章核心題 4（875））
def min_eating_speed(piles: list[int], h: int) -> int:
    def feasible(speed: int) -> bool:
        return sum((p + speed - 1) // speed for p in piles) <= h

    lo, hi = 1, max(piles)
    return lo + bisect_left(range(lo, hi + 1), True, key=feasible)


assert min_eating_speed([3, 6, 7, 11], 8) == 4
assert min_eating_speed([30, 11, 23, 4, 20], 5) == 30
assert min_eating_speed([1], 1) == 1
print("all tests passed")
```

## A.6 Counter、defaultdict 與 OrderedDict

**Counter** 是專門用來計數的 `dict` 子類別。查詢不存在的 key 會回傳 0 而且不會插入，所以可以直接寫 `c[x] += 1`。`most_common(k)` 回傳前 k 個最常見的元素，次數相同時依第一次出現的順序。`Counter` 支援加減與交集、聯集（取最小、最大次數），其中 `-` 會丟掉結果不是正數的項目，`subtract` 則會保留負數。Python 3.10 起兩個 `Counter` 用 `==` 比較時，次數為 0 的項目視為不存在，但 `len(c)` 仍會算進次數為 0 的 key；滑動窗口中如果用 `len(c)` 代表「窗口內有幾種元素」，次數降到 0 時要記得 `del`。

**defaultdict** 在存取不存在的 key 時，自動用工廠函式建立預設值，常見的有 `defaultdict(list)` 建圖與分組、`defaultdict(int)` 計數、`defaultdict(set)` 去重的鄰接表。它的陷阱是「只是讀取也會插入」：`if graph[x]:` 會在 `graph` 中新增 `x`，可能改變走訪的結果或在走訪時改變大小，單純判斷存在請用 `x in graph` 或 `graph.get(x)`。

**OrderedDict** 在一般 `dict` 已經保留順序之後，仍有兩個獨特的 O(1) 操作：`move_to_end(k)` 把 key 移到最後（`last=False` 則移到最前），`popitem(last=False)` 彈出最前面的項目。這正是 LRU cache（最近最少使用快取，第 27 章）需要的兩個操作：存取時移到尾端，容量滿了從前端淘汰。面試中如果面試官要求手寫，就要改成 hash map 加雙向 linked list，但先用 `OrderedDict` 說明思路，再說明底層怎麼實作，是很好的溝通方式。

| 操作 | 複雜度 | 說明 |
|---|---|---|
| `Counter(iterable)` | O(n) | |
| `c[x]`、`c[x] += 1` | O(1) | 不存在回傳 0，讀取不插入 |
| `c.most_common(k)` | O(n log k) | 不給 k 則 O(n log n) |
| `c1 + c2`、`c1 - c2`、`c1 & c2`、`c1 \| c2` | O(len(c1) + len(c2)) | 結果只留正數 |
| `c.total()` | O(n) | 3.10 起，所有次數的總和 |
| `defaultdict(f)[k]` | O(1) | 不存在時呼叫 `f()` 並插入 |
| `od.move_to_end(k)`、`od.popitem(last=False)` | O(1) | LRU cache |

```python
from collections import Counter, OrderedDict, defaultdict

c = Counter("abracadabra")
assert c["a"] == 5 and c["z"] == 0 and "z" not in c        # 讀取不插入
assert c.most_common(2) == [("a", 5), ("b", 2)]
assert Counter("listen") == Counter("silent")                # anagram 判斷
assert c.total() == 11

x, y = Counter(a=3, b=1), Counter(a=1, b=2)
assert x + y == Counter(a=4, b=3)
assert x - y == Counter(a=2)                                 # b 變負，被丟掉
assert x & y == Counter(a=1, b=1) and x | y == Counter(a=3, b=2)
x.subtract(y)
assert x == Counter(a=2, b=-1)                               # subtract 保留負數

# 次數降到 0 的 key 仍在 len 裡
window = Counter("ab")
window["a"] -= 1
assert window == Counter("b") and len(window) == 2
if window["a"] == 0:
    del window["a"]
assert len(window) == 1

# defaultdict 建圖
graph: defaultdict[int, list[int]] = defaultdict(list)
for u, v in [(1, 2), (1, 3), (2, 3)]:
    graph[u].append(v)
    graph[v].append(u)
assert graph[1] == [2, 3] and len(graph) == 3
_ = graph[99]                                                # 只是讀取也會插入
assert 99 in graph and len(graph) == 4
assert 100 not in graph and graph.get(100) is None           # 這兩種寫法不會插入

nested: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
nested["u"]["v"] += 2
assert nested["u"]["v"] == 2


class LRUCache:
    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self.data: OrderedDict[int, int] = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.data:
            return -1
        self.data.move_to_end(key)                           # 標記為最近使用
        return self.data[key]

    def put(self, key: int, value: int) -> None:
        self.data[key] = value
        self.data.move_to_end(key)
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)                    # 淘汰最久未使用的


cache = LRUCache(2)
cache.put(1, 1)
cache.put(2, 2)
assert cache.get(1) == 1
cache.put(3, 3)                                              # 淘汰 2
assert cache.get(2) == -1 and cache.get(3) == 3
cache.put(1, 10)                                             # 更新既有的 key
assert cache.get(1) == 10 and len(cache.data) == 2
print("all tests passed")
```

## A.7 排序：sorted、key 與 cmp_to_key

`sorted(iterable)` 回傳新的 list，`lst.sort()` 原地排序並回傳 `None`，兩者都是 O(n log n) 的穩定排序（stable sort）：鍵相同的元素保持原本的相對順序，而且 `reverse=True` 也維持穩定性。`key` 函式對每個元素只計算一次，所以 `key=len` 或 `key=lambda x: (x[1], x[0])` 的額外成本是 O(n) 次呼叫。

多欄位排序最常見的寫法是讓 `key` 回傳 `tuple`，數值欄位要遞減時取負號，例如 `key=lambda p: (-p.score, p.name)`。字串欄位不能取負，有兩個辦法：一是利用穩定性分兩次排序，先依次要欄位排，再依主要欄位排；二是用 `functools.cmp_to_key` 寫比較函式。比較函式回傳負數代表第一個參數排在前面、正數代表排在後面、0 代表相等。

`cmp_to_key` 在「排序規則無法用單一 key 表示」時才需要，典型例子是 Largest Number（179）：要把數字排成最大的串接結果，規則是 `a + b > b + a` 時 `a` 在前。這個規則依賴兩個元素之間的關係，不容易寫成單一 key。比較的成本是字串長度 L，所以總複雜度是 O(n log n · L)。

| 寫法 | 複雜度 | 何時用 |
|---|---|---|
| `sorted(a)`、`a.sort()` | O(n log n) | 穩定；`sort` 回傳 `None` |
| `sorted(a, key=f)` | O(n log n) 次比較 + n 次 `f` | 單一或 tuple 鍵 |
| `sorted(a, key=lambda x: (-x[1], x[0]))` | 同上 | 數值遞減、次要遞增 |
| 兩次穩定排序 | 2 × O(n log n) | 字串欄位要遞減 |
| `sorted(a, key=cmp_to_key(cmp))` | O(n log n) 次 `cmp` | 規則只能寫成兩兩比較 |
| `sorted(range(n), key=a.__getitem__)` | O(n log n) | argsort，取得排序後的原始索引 |

```python
from functools import cmp_to_key

people = [("bob", 90), ("amy", 95), ("cat", 90), ("dan", 80)]
# 分數遞減，同分時名字遞增
assert sorted(people, key=lambda p: (-p[1], p[0])) == [
    ("amy", 95), ("bob", 90), ("cat", 90), ("dan", 80)]

# 名字遞減、分數遞增：先依次要欄位排，再依主要欄位排
by_name_desc = sorted(people, key=lambda p: p[0], reverse=True)
two_pass = sorted(by_name_desc, key=lambda p: p[1])
assert two_pass == [("dan", 80), ("cat", 90), ("bob", 90), ("amy", 95)]

# reverse=True 仍是穩定的
pairs = [(1, "a"), (0, "b"), (1, "c")]
assert sorted(pairs, key=lambda p: p[0], reverse=True) == [(1, "a"), (1, "c"), (0, "b")]

# argsort
vals = [30, 10, 20]
assert sorted(range(len(vals)), key=vals.__getitem__) == [1, 2, 0]

# 依 value 排序 dict
score = {"x": 3, "y": 1, "z": 2}
assert [k for k, _ in sorted(score.items(), key=lambda kv: kv[1])] == ["y", "z", "x"]


def largest_number(nums: list[int]) -> str:
    def cmp(a: str, b: str) -> int:
        if a + b > b + a:
            return -1                      # a 排在前面
        if a + b < b + a:
            return 1
        return 0

    strs = sorted(map(str, nums), key=cmp_to_key(cmp))
    result = "".join(strs)
    return "0" if result[0] == "0" else result


assert largest_number([3, 30, 34, 5, 9]) == "9534330"
assert largest_number([10, 2]) == "210"
assert largest_number([0, 0]) == "0"
print("all tests passed")
```

## A.8 itertools

`itertools` 的函式都回傳惰性（lazy）的 iterator：元素在需要時才產生，而且只能走訪一次，需要重複使用時要先轉成 `list`。面試中最常用的是以下幾個：`accumulate` 算前綴和或前綴最大值（第 7 章），`initial=0` 可以讓結果多一個開頭的 0，對應 prefix sum 的慣用寫法；`pairwise` 依序產生相鄰的兩個元素，用來比較相鄰差；`groupby` 把**連續**相同的元素分成一組，適合 run-length encoding（連續字元壓縮），但它不會先排序，要依值分組必須先排序。

`product`、`permutations`、`combinations` 能直接列舉所有組合，在 n 很小時（第 3 章 3.2 節的 n ≤ 10 左右）可以拿來寫暴力解或對拍測試。要注意 `permutations` 以「位置」區分元素，輸入有重複值時會產生重複的排列；而且面試官通常想看你手寫 backtracking（第 19 章），能說出「這裡可以用 `itertools`，但我先手寫來展示剪枝」是比較好的做法。

| 函式 | 產生的個數 | 時間 | 典型用途 |
|---|---|---|---|
| `accumulate(a)`、`accumulate(a, initial=0)` | n、n + 1 | O(n) | prefix sum |
| `accumulate(a, max)` | n | O(n) | 前綴最大值 |
| `pairwise(a)` | n − 1 | O(n) | 相鄰差、相鄰比較 |
| `groupby(a)` | 連續段數 | O(n) | run-length encoding |
| `product(a, b)`、`product(a, repeat=r)` | \|a\|·\|b\|、\|a\|ʳ | 與輸出成正比 | 多層迴圈、方向向量 |
| `permutations(a, r)` | n! / (n − r)! | O(r) 每個 | 排列暴力解 |
| `combinations(a, r)` | C(n, r) | O(r) 每個 | 組合暴力解 |
| `chain.from_iterable(lists)` | 總長度 | O(總長度) | 攤平二維 list |

```python
from itertools import accumulate, chain, combinations, groupby, pairwise, permutations, product
from math import comb, perm

nums = [3, 1, 4, 1, 5]
prefix = list(accumulate(nums, initial=0))
assert prefix == [0, 3, 4, 8, 9, 14]
assert prefix[4] - prefix[1] == 1 + 4 + 1             # nums[1:4] 的和
assert list(accumulate(nums, max)) == [3, 3, 4, 4, 5]

assert [b - a for a, b in pairwise(nums)] == [-2, 3, -3, 4]
assert list(pairwise([7])) == []


def rle(s: str) -> str:
    return "".join(f"{ch}{len(list(grp))}" for ch, grp in groupby(s))


assert rle("aaabccdd") == "a3b1c2d2" and rle("") == ""
assert [k for k, _ in groupby("abab")] == ["a", "b", "a", "b"]          # 只合併連續的
assert [k for k, _ in groupby(sorted("abab"))] == ["a", "b"]

# 八個方向的鄰居
dirs = [(dr, dc) for dr, dc in product((-1, 0, 1), repeat=2) if (dr, dc) != (0, 0)]
assert len(dirs) == 8
assert list(product("ab", [0, 1])) == [("a", 0), ("a", 1), ("b", 0), ("b", 1)]

items = [1, 2, 3, 4]
assert len(list(permutations(items, 2))) == perm(4, 2) == 12
assert len(list(combinations(items, 2))) == comb(4, 2) == 6
assert list(combinations(items, 3))[0] == (1, 2, 3)                     # 依輸入順序產生
assert len(list(permutations([1, 1, 2]))) == 6                          # 重複值也被視為不同
assert len(set(permutations([1, 1, 2]))) == 3

assert list(chain.from_iterable([[1, 2], [], [3]])) == [1, 2, 3]

it = accumulate([1, 2])
assert list(it) == [1, 3] and list(it) == []                            # iterator 只能用一次
print("all tests passed")
```

## A.9 functools.cache、lru_cache 與遞迴深度

`@functools.cache` 把函式的回傳值依參數存起來，相同參數第二次呼叫時直接回傳，是寫 top-down DP（記憶化遞迴，memoization，第 21 章）最快的方法。它等同於 `@lru_cache(maxsize=None)`；`lru_cache(maxsize=k)` 則只保留最近使用的 k 筆，面試中幾乎都用不設上限的版本。記憶化後的時間複雜度是「狀態數 × 每個狀態的轉移成本」，空間是快取的狀態數加上遞迴深度。

使用時有三個細節。第一，參數必須可雜湊，`list` 要轉成 `tuple`，或改成傳索引。第二，快取掛在函式物件上，如果把函式定義在模組層級，多個測試案例之間會共用快取，不同輸入可能讀到舊結果，記憶體也不會釋放；最乾淨的做法是把記憶化的 helper 定義在解題函式內部，每次呼叫都是新的快取，否則就在每次使用前呼叫 `cache_clear()`。第三，`cache_info()` 可以看命中次數，用來確認狀態數是否符合你的分析。

Python 預設的遞迴上限約為 1000 層（`sys.getrecursionlimit()`），超過會丟出 `RecursionError`。用 `sys.setrecursionlimit` 調高上限可以應付幾千到一兩萬層，但上限只是 Python 層的檢查，真正的 stack 空間依平台與版本而定，調得太高時可能讓整個行程崩潰。判斷準則是看遞迴深度的最壞情況：平衡樹的 DFS 深度是 O(log n)，不需要擔心；但退化成鏈狀的樹、n 達 10⁵ 的 linked list 遞迴、在路徑狀的圖上做 DFS、狀態一路依賴 `n - 1` 的記憶化遞迴，深度都可能是 O(n)。遇到這些情況，DFS 改成手動維護 stack 的迭代版本，DP 改成 bottom-up 填表，這也是面試官很常追問的 follow-up。

| 項目 | 複雜度或數值 | 說明 |
|---|---|---|
| `@cache` 命中時的查詢 | 平均 O(參數 hash 成本) | 參數要可雜湊 |
| 記憶化遞迴的時間 | 狀態數 × 每狀態轉移成本 | |
| 記憶化遞迴的空間 | 狀態數 + 最大遞迴深度 | |
| `f.cache_clear()`、`f.cache_info()` | O(快取大小)、O(1) | |
| 預設遞迴上限 | 約 1000 層 | 依環境可能不同 |
| `sys.setrecursionlimit(k)` | | 只放寬檢查，不保證 stack 夠用 |

```python
import sys
from functools import cache, lru_cache


def count_paths(grid: tuple[str, ...]) -> int:
    """從左上走到右下（只能往右或往下，'#' 是障礙）的路徑數。"""
    rows, cols = len(grid), len(grid[0])

    @cache                                  # 定義在內部：每次呼叫都是新的快取
    def dp(r: int, c: int) -> int:
        if r >= rows or c >= cols or grid[r][c] == "#":
            return 0
        if (r, c) == (rows - 1, cols - 1):
            return 1
        return dp(r + 1, c) + dp(r, c + 1)

    return dp(0, 0)


assert count_paths(("...", "...", "...")) == 6
assert count_paths(("...", ".#.", "...")) == 2
assert count_paths(("#",)) == 0


@lru_cache(maxsize=None)
def fib(n: int) -> int:
    return n if n < 2 else fib(n - 1) + fib(n - 2)


assert fib(80) == 23416728348467685
assert fib.cache_info().currsize == 81      # 恰好 81 個狀態
fib.cache_clear()
assert fib.cache_info().currsize == 0

# list 不可雜湊，不能直接當參數
@cache
def total(xs: tuple[int, ...]) -> int:
    return sum(xs)


try:
    total([1, 2])                           # type: ignore[arg-type]
    raised = False
except TypeError:
    raised = True
assert raised and total((1, 2)) == 3


# 遞迴太深會丟出 RecursionError
def depth(n: int) -> int:
    return 0 if n == 0 else 1 + depth(n - 1)


try:
    depth(5000)
    raised = False
except RecursionError:
    raised = True
assert raised

old = sys.getrecursionlimit()
sys.setrecursionlimit(10_000)               # 調高上限後幾千層可以跑
assert depth(5000) == 5000
sys.setrecursionlimit(old)


# 深度可能是 O(n) 時改成迭代：手動維護 stack 的 DFS
def reachable(n: int, edges: list[tuple[int, int]], src: int) -> int:
    graph: list[list[int]] = [[] for _ in range(n)]
    for u, v in edges:
        graph[u].append(v)
        graph[v].append(u)
    seen = [False] * n
    seen[src] = True
    stack = [src]
    while stack:
        u = stack.pop()
        for v in graph[u]:
            if not seen[v]:
                seen[v] = True
                stack.append(v)
    return sum(seen)


n = 100_000                                 # 一條很長的路徑，遞迴版會爆
assert reachable(n, [(i, i + 1) for i in range(n - 1)], 0) == n
assert reachable(3, [], 1) == 1


# 記憶化遞迴改成 bottom-up：爬樓梯，每次走 1 或 2 階
def climb(n: int) -> int:
    prev, cur = 1, 1                        # ways(0)、ways(1)
    for _ in range(n - 1):
        prev, cur = cur, prev + cur
    return cur


assert climb(1) == 1 and climb(2) == 2 and climb(5) == 8
assert climb(100_000) > 10 ** 20_000           # n = 10⁵ 也不會碰到遞迴上限
print("all tests passed")
```

## A.10 字串操作

Python 的 `str` 不可變，所有「修改」都會建立新字串。因此在迴圈中用 `s += ch` 累積字串，最壞情況是 O(n²)（CPython 有時會做原地最佳化，但不保證，分析時不要依賴它）；正確做法是把片段收集到 `list`，最後用 `"".join(parts)` 一次串接，總成本 O(總長度)。同理，需要逐字修改的題目（例如反轉單字、原地替換）先用 `list(s)` 轉成字元陣列，改完再 `join`。

切片 `s[a:b]` 與 `s[::-1]` 都會複製，成本與長度成正比；比較兩個字串、計算字串的 hash 也是 O(長度)。這些成本在分析時常被忽略，例如「把每個子字串放進 `set`」看起來是 O(n²) 個子字串，實際上切片與 hash 讓它變成 O(n³)。`sub in s` 與 `s.find(sub)` 的成本至少和 `len(s)` 成正比，不能當成 O(1)。

`split()` 不帶參數時會以任意連續空白切割並丟掉頭尾空白，`split(" ")` 則嚴格以單一空格切割，連續空格會產生空字串，處理「多個空格」的題目時兩者差很多。字元與編碼之間用 `ord` 與 `chr` 轉換，`ord(ch) - ord("a")` 是把小寫字母對應到 0–25 的慣用寫法，可以用長度 26 的陣列取代 `dict` 計數。`isalnum`、`isalpha`、`isdigit` 會把 Unicode 的字母與數字也算進去，題目明確限定 ASCII 時沒有問題，但要知道 `"²".isdigit()` 也是 `True`，真的需要判斷 0–9 時可以寫 `"0" <= ch <= "9"`。

| 操作 | 複雜度 | 說明 |
|---|---|---|
| `s[i]`、`len(s)` | O(1) | |
| `s[a:b]`、`s[::-1]` | O(b − a)、O(n) | 產生新字串 |
| `"".join(parts)` | O(總長度) | 累積字串的正確做法 |
| 迴圈中 `s += t` | 最壞 O(n²) | 改用 `list` 加 `join` |
| `s == t`、`hash(s)` | O(長度) | |
| `sub in s`、`s.find(sub)`、`s.count(sub)` | 至少 O(len(s)) | 找不到時 `find` 回傳 -1，`index` 丟 `ValueError` |
| `s.split()`、`s.strip()`、`s.lower()`、`s.replace(a, b)` | O(n) | |
| `ord(ch)`、`chr(code)` | O(1) | |

```python
import string

parts = []
for i in range(3):
    parts.append(str(i))
assert "-".join(parts) == "0-1-2"

assert "  a  b ".split() == ["a", "b"]
assert "a  b".split(" ") == ["a", "", "b"]                 # 連續空格產生空字串
assert "a,b,,c".split(",") == ["a", "b", "", "c"]
assert "  hi \n".strip() == "hi"


def reverse_words(s: str) -> str:
    return " ".join(reversed(s.split()))


assert reverse_words("  the sky  is blue ") == "blue is sky the"

# ord / chr 與長度 26 的計數陣列
assert ord("a") == 97 and chr(ord("a") + 2) == "c"
counts = [0] * 26
for ch in "hello":
    counts[ord(ch) - ord("a")] += 1
assert counts[ord("l") - ord("a")] == 2
assert string.ascii_lowercase[:3] == "abc"


def is_palindrome(s: str) -> bool:
    """只看英數字、忽略大小寫（第 5 章 two pointers 的熱身題）。"""
    i, j = 0, len(s) - 1
    while i < j:
        if not s[i].isalnum():
            i += 1
        elif not s[j].isalnum():
            j -= 1
        elif s[i].lower() != s[j].lower():
            return False
        else:
            i, j = i + 1, j - 1
    return True


assert is_palindrome("A man, a plan, a canal: Panama")
assert not is_palindrome("race a car") and is_palindrome("")
assert "²".isdigit() and not ("0" <= "²" <= "9")          # Unicode 數字的陷阱

# 字串不可變：逐字修改先轉 list
chars = list("hello")
chars[0] = "j"
assert "".join(chars) == "jello"
try:
    s = "hello"
    s[0] = "j"                                             # type: ignore[index]
    raised = False
except TypeError:
    raised = True
assert raised

assert "banana".find("na") == 2 and "banana".find("xy") == -1
assert "banana".count("a") == 3 and "abc" < "abd" < "b"   # 字典序比較
assert "abc"[::-1] == "cba" and "abc".startswith("ab")
print("all tests passed")
```

## A.11 整數與數學

Python 的 `int` 是無限精度（arbitrary precision）：不會溢位，`2 ** 100` 可以精確計算。好處是不用擔心中間結果溢位，壞處是兩件事要主動處理。第一，題目若要求模擬 32 位元整數（例如 Reverse Integer（7）、String to Integer（8）），要自己檢查是否超出 `-2**31` 到 `2**31 - 1`。第二，數字非常大時運算不再是 O(1)，乘法的成本隨位數成長；需要「對 10⁹ + 7 取餘」的題目，應該在每一步取餘，讓數字維持小。

除法有三個要分清楚的運算子。`/` 永遠回傳 `float`，即使整除也一樣；`//` 是向負無窮取整（floor division）；`%` 的結果與除數同號，並滿足 `a == (a // b) * b + a % b`。所以 `-7 // 2 == -4`、`-7 % 3 == 2`，和 C、Java 的向零取整不同。需要向零取整時，`int(a / b)` 在數字超過 2⁵³ 左右會因為浮點精度出錯，精確的寫法是先對絕對值做 `//` 再補上正負號。正整數的向上取整用 `(a + b - 1) // b` 或 `-(-a // b)`。

常用的數學函式有：`divmod(a, b)` 一次取得商與餘數；`pow(a, b, m)` 用快速冪在 O(log b) 次乘法內算出 `a ** b % m`，`pow(a, -1, m)` 求模反元素（m 為質數或與 a 互質時）；`math.gcd`、`math.lcm` 接受多個參數；`math.comb(n, k)` 與 `math.perm(n, k)` 精確計算組合數與排列數；`math.isqrt(n)` 回傳 ⌊√n⌋ 的精確整數，判斷完全平方數要用它而不是 `int(math.sqrt(n))`，後者在大數時會出錯。`float("inf")`（或 `math.inf`）可以當最小值、最短距離的初始值，它和整數比較沒有問題，但不能轉成 `int`。最後，`round` 使用「四捨六入五成雙」（banker's rounding），`round(2.5) == 2`。

| 操作 | 複雜度 | 說明 |
|---|---|---|
| 一般大小的 `+`、`-`、`*`、`//`、`%` | O(1) | 位數很大時隨位數成長 |
| `a // b`、`a % b` | O(1) | 向負無窮取整；`%` 與除數同號 |
| `divmod(a, b)` | O(1) | 回傳 `(a // b, a % b)` |
| `pow(a, b, m)` | O(log b) 次乘法 | 快速冪；`b = -1` 求反元素 |
| `math.gcd(a, b)` | O(log min(a, b)) | 輾轉相除法 |
| `math.isqrt(n)` | O(log n) 量級 | 精確整數平方根 |
| `math.comb(n, k)` | 與結果位數有關 | 精確，不會溢位 |

```python
import math

assert 2 ** 100 == 1267650600228229401496703205376      # 無限精度
assert 7 / 7 == 1.0 and isinstance(7 / 7, float)        # / 永遠是 float

# // 向負無窮取整，% 與除數同號
assert 7 // 2 == 3 and -7 // 2 == -4 and 7 // -2 == -4
assert -7 % 3 == 2 and 7 % -3 == -2
assert divmod(-7, 2) == (-4, 1)
for a, b in [(7, 3), (-7, 3), (7, -3), (-7, -3)]:
    assert a == (a // b) * b + a % b


def div_trunc(a: int, b: int) -> int:
    """向零取整的整數除法（C／Java 的行為），對大數也精確。"""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


assert div_trunc(-7, 2) == -3 and div_trunc(7, -2) == -3 and div_trunc(7, 2) == 3
big = 10 ** 17 + 1
assert int(big / 1) != big and div_trunc(big, 1) == big  # 浮點除法在大數時失準


def ceil_div(a: int, b: int) -> int:
    return -(-a // b)


assert ceil_div(7, 2) == 4 and ceil_div(6, 2) == 3 and (7 + 2 - 1) // 2 == 4

# 32 位元範圍檢查
INT_MAX, INT_MIN = 2 ** 31 - 1, -(2 ** 31)
assert not INT_MIN <= 1534236469 * 10 <= INT_MAX

MOD = 10 ** 9 + 7
assert pow(2, 10, 1000) == 24 and pow(3, 200, MOD) == 3 ** 200 % MOD
inv = pow(3, -1, MOD)
assert 3 * inv % MOD == 1                               # 模反元素

assert math.gcd(12, 18) == 6 and math.gcd(12, 18, 8) == 2
assert math.lcm(4, 6) == 12 and math.comb(5, 2) == 10 and math.perm(5, 2) == 20
n = (10 ** 16 + 1) ** 2
assert math.isqrt(n) == 10 ** 16 + 1
assert int(math.sqrt(n)) != 10 ** 16 + 1                # 浮點平方根在大數時出錯

best = float("inf")
for x in [5, 3, 8]:
    best = min(best, x)
assert best == 3 and 10 ** 30 < math.inf and -math.inf < -(10 ** 30)
try:
    int(float("inf"))
    raised = False
except OverflowError:
    raised = True
assert raised

assert round(2.5) == 2 and round(3.5) == 4              # 五成雙
assert 0.1 + 0.2 != 0.3 and math.isclose(0.1 + 0.2, 0.3)
print("all tests passed")
```

## A.12 位元運算

位元運算在狀態壓縮 DP（bitmask DP，第 24 章）、子集列舉與一些 XOR 技巧題（第 28 章）中很常見。最常用的幾個恆等式：`x & 1` 判斷奇偶；`x >> k & 1` 取第 k 位；`x | (1 << k)`、`x & ~(1 << k)`、`x ^ (1 << k)` 分別設定、清除、反轉第 k 位；`x & (x - 1)` 清掉最低位的 1，可以用來判斷 2 的冪；`x & -x` 取出最低位的 1，是 Fenwick tree 的核心操作。`int.bit_count()`（3.10 起）回傳 1 的個數，`bit_length()` 回傳表示 `abs(x)` 需要的位元數。

列舉一個 mask 的所有子集有標準寫法：`sub = mask`，每次 `sub = (sub - 1) & mask`，直到 0。對所有 mask 都列舉子集的總成本是 O(3ⁿ)，而不是 O(4ⁿ)，因為每個位元只有「不在 mask」「在 mask 不在子集」「在子集」三種狀態。

負數是 Python 位元運算最容易出錯的地方。Python 的整數沒有固定寬度，概念上負數是「向左無限延伸的 1」的二補數（two's complement），所以 `-1 >> 1` 仍是 `-1`，用 `while x: x >>= 1` 處理負數會變成無窮迴圈。`bin(-5)` 是 `'-0b101'`，不是 32 位元的表示；`(-5).bit_count()` 回傳 2，算的是絕對值。題目要求 32 位元語意（例如 Number of 1 Bits 傳入負數、Sum of Two Integers（371））時，先用 `x & 0xFFFFFFFF` 轉成無號表示，算完若結果 `>= 2**31` 再減去 `2**32` 轉回有號數。`~x` 等於 `-x - 1`。

| 操作 | 結果 | 說明 |
|---|---|---|
| `x & 1`、`x >> k & 1` | 最低位、第 k 位 | |
| `x \| (1 << k)`、`x & ~(1 << k)`、`x ^ (1 << k)` | 設定、清除、反轉第 k 位 | |
| `x & (x - 1)` | 清掉最低位的 1 | `x > 0 and x & (x - 1) == 0` 判斷 2 的冪 |
| `x & -x` | 最低位的 1 | Fenwick tree |
| `x.bit_count()`、`x.bit_length()` | 1 的個數、位元長度 | 都以 `abs(x)` 計算 |
| `x & 0xFFFFFFFF` | 32 位元無號表示 | 處理負數 |
| `~x` | `-x - 1` | |
| 列舉 mask 的子集 | 2^popcount(mask) 個 | 全部 mask 合計 O(3ⁿ) |

```python
x = 0b10110
assert x & 1 == 0 and (x >> 2) & 1 == 1
assert x | (1 << 0) == 0b10111 and x & ~(1 << 1) == 0b10100 and x ^ (1 << 4) == 0b00110
assert x & (x - 1) == 0b10100 and x & -x == 0b10
assert x.bit_count() == 3 and x.bit_length() == 5 and (0).bit_length() == 0


def is_power_of_two(n: int) -> bool:
    return n > 0 and n & (n - 1) == 0


assert is_power_of_two(1) and is_power_of_two(64) and not is_power_of_two(0) and not is_power_of_two(6)

# XOR：成對的數字互相抵消（Single Number）
nums = [4, 1, 2, 1, 2]
acc = 0
for v in nums:
    acc ^= v
assert acc == 4


def subsets(mask: int) -> list[int]:
    out, sub = [], mask
    while True:
        out.append(sub)
        if sub == 0:
            break
        sub = (sub - 1) & mask
    return out


assert sorted(subsets(0b101)) == [0b000, 0b001, 0b100, 0b101]
assert len(subsets(0b1111)) == 16 and subsets(0) == [0]
n = 4
assert sum(len(subsets(m)) for m in range(1 << n)) == 3 ** n

# 負數：無限延伸的二補數
assert -1 >> 1 == -1 and -5 >> 1 == -3 and ~5 == -6
assert bin(-5) == "-0b101" and (-5).bit_count() == 2 and (-1).bit_length() == 1

MASK = 0xFFFFFFFF


def to_signed32(v: int) -> int:
    v &= MASK
    return v - (1 << 32) if v >= 1 << 31 else v


assert (-1) & MASK == 4294967295 and ((-1) & MASK).bit_count() == 32
assert to_signed32(4294967295) == -1 and to_signed32(5) == 5


def add_without_plus(a: int, b: int) -> int:
    """用位元運算模擬 32 位元加法（Sum of Two Integers）。"""
    a, b = a & MASK, b & MASK
    while b:
        a, b = (a ^ b) & MASK, ((a & b) << 1) & MASK
    return to_signed32(a)


assert add_without_plus(2, 3) == 5 and add_without_plus(-2, 3) == 1 and add_without_plus(-4, -6) == -10
print("all tests passed")
```

## A.13 常見陷阱

這一節把面試中最常見的 Python 錯誤集中在一起。它們的共通點是：程式能執行、小範例可能也對，但結果在某些情況下悄悄出錯，面試時很難當場除錯。先看總表，再看每一項的示範。

| 陷阱 | 症狀 | 怎麼避免 |
|---|---|---|
| 可變的預設參數 `def f(acc=[])` | 多次呼叫之間殘留上一次的資料 | 預設值用 `None`，在函式內建立 |
| `[[0] * n] * m` | 改一格，整欄一起變 | `[[0] * n for _ in range(m)]` |
| backtracking 中 `res.append(path)` | 最後所有結果都是空的或相同 | `res.append(path[:])` 存副本 |
| 走訪 list 時刪除元素 | 跳過某些元素 | 用 comprehension 建新 list，或從尾端往回走 |
| 用 `is` 比較值 | 小數字正確、大數字或 list 出錯 | 值用 `==`，只有 `None` 用 `is` |
| `/` 與 `//` 混用、`int(a / b)` | 索引變成 `float`、大數失準、負數方向錯 | 整數運算一律 `//`，向零取整用 A.11 的寫法 |
| 內層函式修改外層變數 | `UnboundLocalError` | `nonlocal`，或改成修改容器的內容 |
| 深遞迴 | `RecursionError` 或行程崩潰 | 改成迭代或 bottom-up（A.9） |

**可變的預設參數。** 預設值在函式**定義時**只建立一次，之後每次呼叫共用同一個物件。所以 `def dfs(node, path=[])` 會讓不同次呼叫的路徑混在一起。

**淺複製。** `[[0] * n] * m` 外層的 `* m` 只複製參考，m 列其實是同一個 list。同樣的問題出現在 backtracking：`path` 是同一個 list 在遞迴中反覆修改，記錄答案時要存 `path[:]` 或 `list(path)` 的副本，否則最後所有答案都指向同一個（已被清空的）list。巢狀結構要完整複製時用 `copy.deepcopy`。

**迴圈中修改 list。** 一邊用 `for x in lst` 走訪一邊 `lst.remove(x)`，會讓迭代器的索引與內容錯位，跳過緊接在被刪元素後面的那一個。

**`==` 與 `is`。** `==` 比較值，`is` 比較是否為同一個物件。CPython 會快取小整數，所以 `is` 在小數字上「剛好正確」，換成大數字或兩個內容相同的 list 就會出錯；唯一應該用 `is` 的是和 `None` 比較。

**整數除法。** `/` 回傳 `float`，拿來當索引會丟出 `TypeError`，例如 `mid = (lo + hi) / 2` 是常見的 binary search 錯誤。負數的方向問題見 A.11。

**nonlocal。** 內層函式中對外層變數賦值（包括 `count += 1`），Python 會把它當成內層的區域變數，讀取時就丟出 `UnboundLocalError`。DFS 中累計答案時，要宣告 `nonlocal count`，或把答案放在 list、`self` 的屬性中修改內容（修改內容不是重新賦值，不需要 `nonlocal`）。

**深遞迴。** 見 A.9 節：深度可能到 O(n) 而且 n 很大時，改成迭代。

```python
import copy


# 1. 可變的預設參數
def collect_bad(x: int, acc: list[int] = []) -> list[int]:   # noqa: B006
    acc.append(x)
    return acc


def collect_good(x: int, acc: list[int] | None = None) -> list[int]:
    if acc is None:
        acc = []
    acc.append(x)
    return acc


collect_bad(1)
assert collect_bad(2) == [1, 2]                     # 殘留上一次的 1
collect_good(1)
assert collect_good(2) == [2]

# 2. 淺複製
bad = [[0] * 3] * 2
bad[0][0] = 1
assert bad == [[1, 0, 0], [1, 0, 0]] and bad[0] is bad[1]
good = [[0] * 3 for _ in range(2)]
good[0][0] = 1
assert good == [[1, 0, 0], [0, 0, 0]]
nested = [[1, 2], [3]]
shallow, deep = nested[:], copy.deepcopy(nested)
nested[0].append(9)
assert shallow[0] == [1, 2, 9] and deep[0] == [1, 2]


def subsets(nums: list[int], snapshot: bool) -> list[list[int]]:
    res: list[list[int]] = []
    path: list[int] = []

    def backtrack(i: int) -> None:
        if i == len(nums):
            res.append(path[:] if snapshot else path)
            return
        path.append(nums[i])
        backtrack(i + 1)
        path.pop()
        backtrack(i + 1)

    backtrack(0)
    return res


assert subsets([1, 2], snapshot=False) == [[], [], [], []]     # 全部指向同一個 path
assert subsets([1, 2], snapshot=True) == [[1, 2], [1], [2], []]

# 3. 迴圈中修改 list
nums = [2, 2, 3, 4]
for v in nums:
    if v % 2 == 0:
        nums.remove(v)
assert nums == [2, 3]                               # 第二個 2 被跳過
nums = [2, 2, 3, 4]
assert [v for v in nums if v % 2 != 0] == [3]
for i in range(len(nums) - 1, -1, -1):              # 從尾端往回刪也安全
    if nums[i] % 2 == 0:
        del nums[i]
assert nums == [3]

# 4. == 與 is
a, b = [1, 2], [1, 2]
assert a == b and a is not b
big1, big2 = int("100000"), int("100000")
assert big1 == big2                                 # 值的比較一律用 ==
result = None
assert result is None

# 5. 整數除法
lo, hi = 0, 7
assert isinstance((lo + hi) / 2, float) and (lo + hi) // 2 == 3
try:
    _ = [10, 20, 30][(0 + 2) / 2]                   # type: ignore[index]
    raised = False
except TypeError:
    raised = True
assert raised


# 6. nonlocal
def count_nodes_bad(depth: int) -> int:
    total = 0

    def dfs(d: int) -> None:
        total += 1                                  # type: ignore[misc]  # noqa: F841
        if d > 0:
            dfs(d - 1)
            dfs(d - 1)

    dfs(depth)
    return total


try:
    count_nodes_bad(2)
    raised = False
except UnboundLocalError:
    raised = True
assert raised


def count_nodes(depth: int) -> int:
    total = 0

    def dfs(d: int) -> None:
        nonlocal total
        total += 1
        if d > 0:
            dfs(d - 1)
            dfs(d - 1)

    dfs(depth)
    return total


assert count_nodes(0) == 1 and count_nodes(2) == 7


def count_nodes_box(depth: int) -> int:
    box = [0]                                       # 修改容器內容，不需要 nonlocal

    def dfs(d: int) -> None:
        box[0] += 1
        if d > 0:
            dfs(d - 1)
            dfs(d - 1)

    dfs(depth)
    return box[0]


assert count_nodes_box(3) == 15
print("all tests passed")
```

## A.14 面試用的程式風格

面試中的程式不只要對，還要讓面試官在幾分鐘內讀懂、相信它是對的。第 2 章談過溝通流程，這一節只談程式本身。好的面試程式有四個特徵：名字說明用途、主函式短而且讀起來像演算法的步驟、邊界在開頭處理掉、型別一眼可見。這些都不會多花你很多時間，卻能明顯降低出錯與被誤解的機會。

**命名。** 迴圈索引用 `i`、`j`，座標用 `r`、`c`，這些是公認的慣例；其他變數要說明用途，例如 `left`、`right`、`window_sum`、`best`、`dist`、`parent`，而不是 `a`、`tmp`、`x2`。常數用全大寫，例如 `DIRS`、`MOD`。名字取得好，可以少講很多解釋，面試官追問「這個變數是什麼」的次數也會變少。

**helper 函式。** 把會重複出現、或本身有清楚意義的邏輯抽成 helper，例如「格子是否在範圍內」「這個速度是否可行」「兩個區間是否重疊」。好處是主函式讀起來像演算法的描述，而且 helper 可以單獨測試、單獨說明正確性。helper 定義在主函式內部可以直接使用外層變數，不必傳一長串參數；需要修改外層變數時記得 A.13 的 `nonlocal`。

**型別提示。** 在函式簽名寫上型別（`def solve(nums: list[int], k: int) -> int:`），能讓面試官立刻知道輸入輸出，也逼你自己確認回傳值的型別，例如要回傳索引還是值、找不到時回傳 `-1` 還是 `None`。函式內的區域變數只在型別不明顯時才標，例如空容器 `graph: dict[int, list[int]] = {}`。Python 3.9 起可以直接寫 `list[int]`、`dict[str, int]`，3.10 起可以用 `X | None`，不必從 `typing` 匯入。

**何時用 class。** 三種情況適合用 class：第一，題目本身是設計題，要求實作一組方法，例如 LRU cache、Min Stack、iterator 類題目；第二，需要一個有狀態、會被重複操作的資料結構，例如 union-find、Trie、Fenwick tree，把狀態與操作包在一起比傳一堆陣列清楚；第三，記錄型的資料欄位很多時，可以用 `dataclass` 取代難讀的 `tuple` 索引。除此之外，一般演算法題寫成函式就好，不需要繼承、抽象類別或設計模式。線上平台常見的 `class Solution` 只是外殼，裡面照樣寫成函式。

| 原則 | 做法 | 避免 |
|---|---|---|
| 命名 | `left`、`right`、`window_sum`、`DIRS` | `a`、`tmp`、`x2`、內建名稱如 `list`、`sum` |
| 結構 | 主函式短，細節抽成 helper | 一個 60 行、縮排五層的函式 |
| 邊界 | 開頭用 early return 處理空輸入 | 在迴圈裡到處檢查特殊情況 |
| 型別 | 函式簽名寫型別提示 | 回傳值有時是 `int` 有時是 `None` 而不說明 |
| class | 設計題、有狀態的資料結構 | 為一般演算法題建立類別階層 |
| 測試 | 寫完用範例與邊界逐行追蹤，再補 `assert` | 寫完直接宣稱完成 |

```python
from collections import deque
from dataclasses import dataclass

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def num_islands(grid: list[list[str]]) -> int:
    """計算 '1' 組成的島嶼個數（第 15 章核心題 1）。"""
    if not grid or not grid[0]:
        return 0
    rows, cols = len(grid), len(grid[0])
    seen = [[False] * cols for _ in range(rows)]

    def in_bounds(r: int, c: int) -> bool:
        return 0 <= r < rows and 0 <= c < cols

    def flood(sr: int, sc: int) -> None:
        seen[sr][sc] = True
        q = deque([(sr, sc)])
        while q:
            r, c = q.popleft()
            for dr, dc in DIRS:
                nr, nc = r + dr, c + dc
                if in_bounds(nr, nc) and grid[nr][nc] == "1" and not seen[nr][nc]:
                    seen[nr][nc] = True
                    q.append((nr, nc))

    islands = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "1" and not seen[r][c]:
                flood(r, c)
                islands += 1
    return islands


assert num_islands([list("110"), list("010"), list("001")]) == 2
assert num_islands([]) == 0 and num_islands([list("000")]) == 0


class UnionFind:
    """有狀態、會被重複操作的資料結構適合包成 class。"""

    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.size = [1] * n
        self.components = n

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
        self.components -= 1
        return True


uf = UnionFind(5)
assert uf.union(0, 1) and uf.union(3, 4) and not uf.union(1, 0)
assert uf.components == 3 and uf.find(0) == uf.find(1) != uf.find(3)


@dataclass(frozen=True, order=True)
class Event:
    time: int
    kind: int          # 0 = 結束、1 = 開始；同時間先處理結束
    room: str


events = sorted([Event(5, 1, "b"), Event(5, 0, "a"), Event(1, 1, "a")])
assert [(e.time, e.kind) for e in events] == [(1, 1), (5, 0), (5, 1)]
print("all tests passed")
```

## 本附錄重點整理

- `list` 只在尾端增刪是 O(1)；`pop(0)`、`insert(0, x)`、`x in lst` 是 O(n)，queue 用 `deque`，查詢用 `set`。切片與字串串接都會複製，成本與長度成正比。
- `dict` 與 `set` 平均 O(1)，但 key 的 hash 成本是 O(key 長度)；走訪時不能改變大小。`defaultdict` 只是讀取也會插入，判斷存在用 `in`。
- `heapq` 只有 min-heap：數值存負值、其他型別包反向比較的類別；放 `(priority, counter, item)` 避免比較到 item；需要刪除任意元素時用 lazy deletion。
- `bisect_left` 是第一個 `>= x`、`bisect_right` 是第一個 `> x`；`key` 只套用在元素上，`x` 要傳已轉換的值；`insort` 仍是 O(n)。
- 排序是穩定的；多欄位用 tuple key，數值遞減取負號，字串遞減用兩次穩定排序，只能兩兩比較的規則用 `cmp_to_key`。
- `@cache` 定義在解題函式內部以免跨測試案例共用；參數要可雜湊。遞迴深度可能到 O(n) 時改成迭代或 bottom-up，`setrecursionlimit` 只放寬檢查。
- `//` 向負無窮取整、`%` 與除數同號；向零取整與大數除法不要用 `float`；完全平方數用 `math.isqrt`；`pow(a, b, m)` 做快速冪。
- Python 整數沒有固定寬度，負數的位元運算要用 `& 0xFFFFFFFF` 模擬 32 位元；`bit_count` 與 `bit_length` 都以絕對值計算。
- 最常見的陷阱：可變預設參數、`[[0] * n] * m`、backtracking 忘記存 `path[:]`、走訪時修改 list、用 `is` 比較值、`/` 當索引、忘記 `nonlocal`。
- 面試程式的風格：有意義的名字、短主函式加 helper、函式簽名寫型別提示、只在設計題與有狀態的資料結構使用 class。
