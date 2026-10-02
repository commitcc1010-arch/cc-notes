---
chapter: 26
title: Range Query：Fenwick Tree 與 Segment Tree
part: 6
---

# 第 26 章　Range Query：Fenwick Tree 與 Segment Tree

> [!abstract] 本章地圖
> **一句話**：把陣列預先切成 O(n) 個「區段摘要」，讓任何一段區間都能拼成 O(log n) 個摘要、任何一個位置都只屬於 O(log n) 個摘要，於是「修改」與「區間查詢」同時做到 O(log n)。
>
> **辨識訊號**：
> - 陣列會被修改，同時又要反覆問「某段區間的和／最大值／最小值」
> - 「右邊（或左邊）有幾個比我小／比我大」「有幾個數對滿足 i < j 且某個大小關係」
> - 「有幾個子陣列的和落在 [lower, upper]」這種範圍條件，hash map 只能處理等於
> - 區間的加值、覆蓋、刪除，座標高達 10⁹，而且要即時回答（行事曆、區間集合、方塊堆疊）
> - DP 轉移是「在值域的一段範圍內取最大值」，例如 `dp[v] = 1 + max(dp[v-k .. v-1])`
>
> **核心題**：307、315、729、731、1395
>
> **難題**：327、493、699、715、2407

## 26.1 這個 Pattern 解決什麼問題

先看一個最小的例子。有一個長度 n 的陣列，接下來有 q 個操作，每個操作不是「把第 i 個數改成 x」，就是「問第 l 到第 r 個數的總和」。最直接的做法是直接存陣列：修改 O(1)，查詢要把 r − l + 1 個數加起來，O(n)。第 7 章的 prefix sum 剛好反過來：查詢 `P[r+1] − P[l]` 只要 O(1)，但改一個數會讓它後面所有的前綴和都要更新，修改變成 O(n)。n 和 q 都是 10⁵ 時，兩種做法在最壞情況都是 10¹⁰ 次運算。

問題出在兩個極端：直接存陣列時，每個「摘要」只涵蓋一個元素，查詢要拼很多塊；存前綴和時，每個摘要涵蓋太多元素，一個元素被 n 個摘要共用，修改要改很多塊。我們要的是中間的設計：準備 O(n) 個區段摘要，讓**任何前綴或區間都能用 O(log n) 塊拼出來**，同時**每個元素只被 O(log n) 塊涵蓋**。這兩個條件同時成立，查詢與修改就都是 O(log n)。

| 做法 | 單點修改 | 區間查詢 | 備註 |
|---|---|---|---|
| 直接存陣列 | O(1) | O(n) | 每個摘要只有一個元素 |
| Prefix sum（第 7 章） | O(n) | O(1) | 每個元素被 n 個摘要共用 |
| 分塊（sqrt decomposition） | O(1) | O(√n) | 切成 √n 塊，各存塊總和 |
| Fenwick tree／segment tree | O(log n) | O(log n) | 用 2 的冪次大小的區段 |

Fenwick tree（樹狀陣列，又稱 binary indexed tree，簡稱 BIT）和 segment tree（線段樹）就是這種中間設計的兩種實作。BIT 只用一個長度 n + 1 的陣列和兩個五行的迴圈，專門處理「可以相減」的運算（和、計數、XOR）；segment tree 用一棵完整的二元樹，任何滿足結合律的運算（最大值、最小值、gcd、矩陣乘法）都能用，還能透過 lazy propagation（延遲標記）支援整段區間的修改。

面試中，這個 pattern 有兩種完全不同的出場方式，要能都認得：

1. **直接當資料結構用**：題目本身就是「會變的陣列加區間查詢」。核心題 1（307）是標準形；難題 3（699）是區間覆蓋加區間最大值；核心題 3、4（729、731）與難題 4（715）把陣列換成座標高達 10⁹ 的時間軸。
2. **當計數工具用**：題目問「有幾個數對 i < j 滿足 a[i] 和 a[j] 的某個大小關係」。做法是沿著索引掃描，每看到一個數就把它「插進」一棵以**值**為索引的 BIT，再問「已經插入的數裡，有幾個落在某個值的範圍」。核心題 2（315）、核心題 5（1395）、難題 1（327）、難題 2（493）都是這一型。這種用法的關鍵是把一個維度交給「掃描順序」，另一個維度交給「樹的索引」。

難題 5（2407）則是第三種：DP 的轉移需要在值域的一段範圍裡取最大值，segment tree 把 O(n²) 的 DP 降成 O(n log n)。

## 26.2 辨識訊號

| 題目特徵 | 為什麼是 range query | 本章哪一題 |
|---|---|---|
| 陣列會被單點修改，同時要區間和 | prefix sum 修改太貴、直接加總查詢太貴，BIT 兩者都 O(log n) | 核心題 1（307） |
| 「每個元素右邊有幾個比它小」 | 從右往左掃，BIT 以值為索引記錄「已出現的數」，查詢前綴計數 | 核心題 2（315） |
| 「i < j < k 且值遞增的三元組有幾個」 | 固定中間的 j，左右兩邊各要一個「比我小／比我大的個數」 | 核心題 5（1395） |
| 子陣列和落在 [lower, upper] 的個數 | 轉成前綴和數對 P[j] − P[i] ∈ [lower, upper]，是一個值的範圍計數 | 難題 1（327） |
| 數對條件是 `a[i] > 2·a[j]` 這種「插入值與查詢值不同」 | 仍是範圍計數，只是要把查詢門檻也放進座標壓縮，或用 bisect 換算排名 | 難題 2（493） |
| 時間軸上預訂區間，問會不會重疊／重疊幾層 | 區間加 1、區間最大值；座標到 10⁹ 要用動態開點或座標壓縮 | 核心題 3（729）、核心題 4（731） |
| 方塊落下、區間被覆蓋成同一個高度 | 區間覆蓋（assign）加區間最大值，需要 lazy propagation | 難題 3（699） |
| 區間集合的加入、刪除、詢問是否完整涵蓋 | 有序的不相交區間清單，或區間賦值的 segment tree | 難題 4（715） |
| `dp[i]` 依賴「值在某個範圍內的 dp 最大值」 | 以值為索引的 segment tree 做區間最大值、單點更新 | 難題 5（2407） |
| n、q 都是 10⁵，且操作交錯出現 | O((n + q) log n) 剛好可接受，O(nq) 不行 | 全章 |

一個實用的反向檢查：如果陣列**不會被修改**，就不需要這一章，第 7 章的 prefix sum 就夠了；如果所有修改都發生在所有查詢**之前**，第 7 章的 difference array 也夠了。只有「修改和查詢交錯出現」，或是「掃描過程中資料一直在長大」（計數型），才需要樹。

## 26.3 Fenwick Tree 模板與原理：lowbit 的直覺

### lowbit：每個位置負責多長的一段

BIT 的陣列 `t` 從索引 1 開始。關鍵的設計是：**`t[i]` 存的是原陣列中以 i 結尾、長度為 lowbit(i) 的那一段的總和**，也就是區間 `(i − lowbit(i), i]`。lowbit(i) 是 i 的二進位表示中最低的那個 1 代表的值，例如 6 = 0110，最低的 1 在第 1 位，lowbit(6) = 2，所以 `t[6]` 負責 `a[5] + a[6]`。在二補數下，`i & -i` 剛好就是 lowbit(i)，因為 `-i` 是把 i 取反再加 1，最低的 1 以下的位元會「進位回來」，其餘位元全部相反。

```text
n = 8，t[i] 負責 (i - lowbit(i), i]

i        :   1     2     3     4     5     6     7     8
二進位   : 0001  0010  0011  0100  0101  0110  0111  1000
lowbit(i):   1     2     1     4     1     2     1     8
負責區間 : [1,1] [1,2] [3,3] [1,4] [5,5] [5,6] [7,7] [1,8]

原陣列位置:   1    2    3    4    5    6    7    8
t[8]      : |=======================================|
t[4]      : |===================|
t[6]      :                     |=========|
t[2]      : |=========|
t[1] t[3] t[5] t[7] 各自只負責一格
```

奇數位置 lowbit 都是 1，只管自己；2 的倍數管 2 格；4 的倍數管 4 格；8 管 8 格。這些區段像一把尺上的刻度，長度都是 2 的冪次，而且彼此要嘛不相交、要嘛一個包含另一個，所以它們自然形成一棵樹：`t[i]` 的父節點是 `i + lowbit(i)`，也就是「下一個包含我的更長區段」。

### 查詢前綴和：一直拿掉最低的 1

要算 `a[1] + … + a[7]`，從 i = 7 開始：`t[7]` 負責 `[7, 7]`，拿走它之後還差 `[1, 6]`；`7 − lowbit(7) = 6`，`t[6]` 負責 `[5, 6]`，還差 `[1, 4]`；`6 − lowbit(6) = 4`，`t[4]` 負責 `[1, 4]`，剛好拼完；`4 − 4 = 0`，停止。每一步把 i 的最低一個 1 清掉，而 i 最多有 log₂ n 個 1，所以查詢是 O(log n)。

```text
prefix(7)：7 = 0111
  i = 7 (0111)  加 t[7] = a[7]            剩下 [1, 6]
  i = 6 (0110)  加 t[6] = a[5..6]         剩下 [1, 4]
  i = 4 (0100)  加 t[4] = a[1..4]         剩下空
  i = 0         停止
  總共 3 塊 = popcount(7)
```

為什麼一定拼得剛好？因為 `t[i]` 負責的區間左端是 `i − lowbit(i) + 1`，拿掉它之後剩下的是 `[1, i − lowbit(i)]`，而下一步的 i 正好是 `i − lowbit(i)`，所以每一步都恰好接在上一塊的左邊，不重疊也不漏。

### 單點修改：一直加上最低的 1

改 `a[5]` 時，要更新所有「負責區間包含 5」的 `t[j]`。從 j = 5 開始（它負責自己），下一個包含 5 的更長區段是 `5 + lowbit(5) = 6`（負責 `[5, 6]`），再下一個是 `6 + 2 = 8`（負責 `[1, 8]`），`8 + 8 = 16` 超過 n，停止。直覺是：j 加上 lowbit(j) 會讓最低的 1 往上進位，得到一個 lowbit 更大、而且右端點仍 ≥ 5 的區段，它剛好把原來的區段整個包進去。每一步 lowbit 至少翻倍，所以也是 O(log n)。

```text
add(5, δ)：
  j = 5 (0101)  t[5] += δ   負責 [5, 5]
  j = 6 (0110)  t[6] += δ   負責 [5, 6]
  j = 8 (1000)  t[8] += δ   負責 [1, 8]
  j = 16 > n    停止
  t[1..4]、t[7] 的區間都不含 5，不需要動
```

### 模板

```python
import random


class BIT:
    """Fenwick tree：索引 1..n，支援單點加值與前綴和，兩者都是 O(log n)。"""

    def __init__(self, n: int):
        self.n = n
        self.t = [0] * (n + 1)          # t[0] 不用：lowbit(0) = 0 會讓迴圈停不下來

    @classmethod
    def build(cls, nums: list[int]) -> "BIT":
        """O(n) 建樹：每個節點累加完自己的子區段後，把總和推給父節點一次。"""
        bit = cls(len(nums))
        for i, x in enumerate(nums, 1):
            bit.t[i] += x
            parent = i + (i & -i)
            if parent <= bit.n:
                bit.t[parent] += bit.t[i]
        return bit

    def add(self, i: int, delta: int) -> None:
        while i <= self.n:              # i > n 時什麼都不做，呼叫端不必特判
            self.t[i] += delta
            i += i & -i                 # 往上走到下一個包含 i 的區段

    def prefix(self, i: int) -> int:    # a[1] + ... + a[i]；i = 0 時回傳 0
        s = 0
        while i > 0:
            s += self.t[i]
            i -= i & -i                 # 跳到這一塊左邊的前綴
        return s

    def range_sum(self, l: int, r: int) -> int:
        return self.prefix(r) - self.prefix(l - 1)

    def lower_bound(self, k: int) -> int:
        """最小的 i 使 prefix(i) >= k（所有值需非負）；總和不足 k 時回傳 n + 1。"""
        pos = 0
        step = 1 << self.n.bit_length()
        while step:
            nxt = pos + step
            if nxt <= self.n and self.t[nxt] < k:   # t[nxt] 正好是 (pos, nxt] 的和
                pos = nxt
                k -= self.t[nxt]
            step >>= 1
        return pos + 1


class RangeAddPointQuery:
    """在差分陣列上建 BIT：區間 [l, r] 加 v、單點查詢，都是 O(log n)。"""

    def __init__(self, n: int):
        self.bit = BIT(n)

    def range_add(self, l: int, r: int, v: int) -> None:
        self.bit.add(l, v)
        self.bit.add(r + 1, -v)         # r + 1 > n 時 add 自動忽略

    def point(self, i: int) -> int:
        return self.bit.prefix(i)


class RangeAddRangeSum:
    """兩棵 BIT：區間加值、區間和。prefix(x) = x·Σd[j] − Σd[j]·(j − 1)。"""

    def __init__(self, n: int):
        self.b1, self.b2 = BIT(n), BIT(n)

    def range_add(self, l: int, r: int, v: int) -> None:
        self.b1.add(l, v)
        self.b1.add(r + 1, -v)
        self.b2.add(l, v * (l - 1))
        self.b2.add(r + 1, -v * r)

    def prefix(self, x: int) -> int:
        return self.b1.prefix(x) * x - self.b2.prefix(x)

    def range_sum(self, l: int, r: int) -> int:
        return self.prefix(r) - self.prefix(l - 1)


bit = BIT.build([1, 3, 5, 7, 9, 11, 13, 15])
assert bit.t[1:] == [1, 4, 5, 16, 9, 20, 13, 64]      # 每格負責的區段和
assert bit.prefix(7) == 49 and bit.prefix(0) == 0
assert bit.range_sum(3, 7) == 45
bit.add(5, -9)                                        # a[5]: 9 → 0
assert bit.range_sum(3, 7) == 36
assert bit.lower_bound(1) == 1 and bit.lower_bound(5) == 3 and bit.lower_bound(10**9) == 9
assert BIT(0).prefix(0) == 0
for _ in range(300):
    n = random.randint(1, 20)
    a = [random.randint(0, 5) for _ in range(n)]
    b = BIT.build(a)
    assert all(b.prefix(i) == sum(a[:i]) for i in range(n + 1))
    k = random.randint(1, sum(a) + 2)
    expect = next((i for i in range(1, n + 1) if sum(a[:i]) >= k), n + 1)
    assert b.lower_bound(k) == expect
    rp, rr, plain = RangeAddPointQuery(n), RangeAddRangeSum(n), [0] * (n + 1)
    for _ in range(20):
        l = random.randint(1, n)
        r = random.randint(l, n)
        v = random.randint(-5, 5)
        rp.range_add(l, r, v)
        rr.range_add(l, r, v)
        for i in range(l, r + 1):
            plain[i] += v
        i = random.randint(1, n)
        assert rp.point(i) == plain[i]
        ql = random.randint(1, n)
        qr = random.randint(ql, n)
        assert rr.range_sum(ql, qr) == sum(plain[ql:qr + 1])
print("all tests passed")
```

**每一行為什麼這樣寫**：

- **索引從 1 開始**：lowbit(0) = 0，`i += i & -i` 在 i = 0 時永遠停在 0，迴圈不會結束。題目給的是 0-indexed 陣列時，一律在呼叫時 `+1`，不要去改模板。
- **`add` 的條件是 `i <= self.n`、`prefix` 的條件是 `i > 0`**：兩個迴圈方向相反，一個往上走到超出 n，一個往下走到 0。記法是「加值往上傳、查詢往左收」。
- **`range_sum(l, r) = prefix(r) − prefix(l − 1)`**：BIT 本身只會算前綴，區間要靠相減，所以 BIT 只適用於有反運算的操作（加法、XOR、計數）。最大值不能相減，這是 BIT 和 segment tree 最根本的分界。
- **O(n) 建樹**：逐一呼叫 `add` 是 O(n log n)，也完全可以接受；O(n) 版本利用「子區段一定比父區段先處理完」，每個節點只把自己推給父節點一次。
- **`lower_bound`（在 BIT 上二分）**：從高位到低位決定答案的每個位元。`pos` 永遠是一個「已確定 prefix(pos) < k」的位置，`t[pos + step]` 剛好負責 `(pos, pos + step]`，因為 pos 的低位都是 0，`pos + step` 的 lowbit 就是 step。整個過程 O(log n)，比在外面套一層 binary search 再呼叫 `prefix` 的 O(log² n) 好。核心題 2 的 F4 和「第 k 小的已插入元素」都用得到它。

**區間修改的兩個變形**。在差分陣列 d 上建 BIT（`d[i] = a[i] − a[i−1]`），區間 `[l, r]` 加 v 只改 `d[l]` 和 `d[r+1]` 兩個點，而 `a[i]` 就是 `d` 的前綴和，所以「區間加、單點查」直接成立。若還要「區間和」，展開 `Σ_{i≤x} a[i] = Σ_{j≤x} d[j]·(x − j + 1)`，拆成 `x·Σd[j] − Σd[j]·(j − 1)`，用兩棵 BIT 分別維護 `d[j]` 與 `d[j]·(j − 1)` 即可。這兩個變形面試很少要求手寫，但知道「BIT 也能做區間加」能讓你在不需要 lazy segment tree 時省下很多時間。

## 26.4 Segment Tree 模板：遞迴與迭代

### 結構：每個節點負責一段，左右孩子各負責一半

Segment tree 的每個節點負責一段連續區間 `[l, r]`，存這段的摘要（和、最大值…）；它的左孩子負責 `[l, m]`、右孩子負責 `[m+1, r]`，`m = (l + r) // 2`；葉子負責單一元素。用陣列存時，根是 1，節點 k 的孩子是 2k 和 2k + 1。樹高是 ⌈log₂ n⌉，陣列開 4n 一定夠（n 不是 2 的冪次時，最後一層會有空位，4n 是安全的上界）。

```text
nums = [5, 8, 6, 3, 2, 7]，存區間和

                    k=1 [0,5] 31
              /                       \
      k=2 [0,2] 19                k=3 [3,5] 12
       /         \                 /          \
 k=4 [0,1] 13  k=5 [2,2] 6   k=6 [3,4] 5   k=7 [5,5] 7
   /     \                     /     \
k=8 [0]5 k=9 [1]8         k=12 [3]3 k=13 [4]2

query([1, 4])：
  [0,5] 部分相交 → 往下
    [0,2] 部分相交 → 往下
      [0,1] 部分相交 → 往下
        [0] 不相交 → 0
        [1] 完全包含 → 8
      [2,2] 完全包含 → 6
    [3,5] 部分相交 → 往下
      [3,4] 完全包含 → 5
      [5,5] 不相交 → 0
  答案 8 + 6 + 5 = 19
```

查詢時每個節點只有三種情況：和查詢區間**不相交**（回傳單位元素，和是 0、最大值是 −∞）、**完全包含**（直接回傳節點的值，不再往下）、**部分相交**（往兩個孩子遞迴再合併）。為什麼是 O(log n)？因為在每一層，「部分相交」的節點最多只有兩個：查詢區間的左端點和右端點各自最多穿過一個節點，中間被完全包含的節點都會直接回傳。所以每層最多拜訪 4 個節點，總共 O(log n)。單點修改則只走一條從根到葉的路徑，回程時重算路徑上每個節點的摘要。

### 遞迴版與迭代版

```python
import random
from operator import add


class SegTree:
    """遞迴線段樹：閉區間 [l, r]，索引 0..n-1，單點賦值、區間和。"""

    def __init__(self, nums: list[int]):
        self.n = len(nums)
        self.t = [0] * (4 * self.n)
        self._build(1, 0, self.n - 1, nums)

    def _build(self, k, l, r, nums):
        if l == r:
            self.t[k] = nums[l]
            return
        m = (l + r) // 2
        self._build(2 * k, l, m, nums)
        self._build(2 * k + 1, m + 1, r, nums)
        self.t[k] = self.t[2 * k] + self.t[2 * k + 1]        # pull：由孩子算出自己

    def update(self, i, val, k=1, l=0, r=None):
        if r is None:
            r = self.n - 1
        if l == r:
            self.t[k] = val
            return
        m = (l + r) // 2
        if i <= m:
            self.update(i, val, 2 * k, l, m)
        else:
            self.update(i, val, 2 * k + 1, m + 1, r)
        self.t[k] = self.t[2 * k] + self.t[2 * k + 1]

    def query(self, ql, qr, k=1, l=0, r=None):
        if r is None:
            r = self.n - 1
        if qr < l or r < ql:                # 不相交
            return 0
        if ql <= l and r <= qr:             # 完全包含
            return self.t[k]
        m = (l + r) // 2                    # 部分相交
        return self.query(ql, qr, 2 * k, l, m) + self.query(ql, qr, 2 * k + 1, m + 1, r)


class IterSegTree:
    """迭代線段樹：葉子在 t[n .. 2n-1]，半開區間 [l, r)，op 需滿足結合律。"""

    def __init__(self, nums, op=add, identity=0):
        self.n, self.op, self.e = len(nums), op, identity
        self.t = [identity] * self.n + list(nums)
        for i in range(self.n - 1, 0, -1):
            self.t[i] = op(self.t[2 * i], self.t[2 * i + 1])

    def update(self, i, val):
        i += self.n
        self.t[i] = val
        while i > 1:
            i //= 2
            self.t[i] = self.op(self.t[2 * i], self.t[2 * i + 1])

    def query(self, l, r):
        left = right = self.e
        l += self.n
        r += self.n
        while l < r:
            if l & 1:                       # l 是右孩子：它的父節點會超出範圍，先收下 l
                left = self.op(left, self.t[l])
                l += 1
            if r & 1:                       # r 是右孩子：r - 1 是左孩子且在範圍內，收下它
                r -= 1
                right = self.op(self.t[r], right)
            l //= 2
            r //= 2
        return self.op(left, right)


st = SegTree([5, 8, 6, 3, 2, 7])
assert st.query(1, 4) == 19 and st.query(0, 5) == 31 and st.query(3, 3) == 3
st.update(1, 0)
assert st.query(1, 4) == 11
it = IterSegTree([5, 8, 6, 3, 2, 7])
assert it.query(1, 5) == 19 and it.query(0, 6) == 31 and it.query(2, 2) == 0
mn = IterSegTree([5, 8, 6, 3, 2, 7], min, float("inf"))
assert mn.query(0, 3) == 5 and mn.query(1, 6) == 2
for _ in range(300):
    n = random.randint(1, 17)
    a = [random.randint(-9, 9) for _ in range(n)]
    s, sm, smax = SegTree(a), IterSegTree(a), IterSegTree(a, max, float("-inf"))
    for _ in range(20):
        i, v = random.randrange(n), random.randint(-9, 9)
        a[i] = v
        s.update(i, v)
        sm.update(i, v)
        smax.update(i, v)
        l = random.randrange(n)
        r = random.randint(l, n - 1)
        assert s.query(l, r) == sm.query(l, r + 1) == sum(a[l:r + 1])
        assert smax.query(l, r + 1) == max(a[l:r + 1])
print("all tests passed")
```

**迭代版的直覺**。把 n 個葉子放在 `t[n .. 2n−1]`，內部節點 `t[i] = t[2i] op t[2i+1]`。查詢 `[l, r)` 時，`l` 和 `r` 從葉子層同時往上爬：如果 `l` 是某個節點的右孩子（奇數），它的父節點還涵蓋了 `l − 1`，不在範圍內，所以要先把 `t[l]` 收進答案，再讓 `l` 右移一格；`r` 是半開的右端，如果 `r` 是奇數，代表 `r − 1` 是左孩子而且在範圍內，同樣先收下。然後兩者都除以 2 爬到上一層。`left` 從左邊累積、`right` 從右邊累積，最後才合併，這樣不具交換律的運算（例如矩陣乘法、字串拼接）也能維持順序。

```text
n = 8，查詢 [1, 6)：葉子索引 l = 9、r = 14

層        l    r    動作
葉子層    9   14    l 奇數 → 收 t[9]（a[1]），l = 10；r 偶數不動
          5    7    l 奇數 → 收 t[5]（a[2..3]），l = 6；r 奇數 → r = 6，收 t[6]（a[4..5]）
          3    3    l == r，停止
答案 = a[1] + a[2..3] + a[4..5]
```

**何時用哪一版**。迭代版大約 15 行、沒有遞迴、常數小，適合「單點修改、區間查詢」，例如核心題 1（307）與難題 5（2407）。遞迴版比較長，但每一步都對應「不相交／完全包含／部分相交」三種情況，容易在上面加 lazy propagation、在樹上二分、或改成動態開點；凡是有「區間修改」的題目，直接寫遞迴版。迭代版也能做 lazy，但寫法複雜得多，面試中不建議。

## 26.5 Lazy Propagation：區間修改

### 為什麼需要延遲標記

如果要把 `[l, r]` 每個元素都加 v，逐一單點修改是 O((r − l + 1) log n)，整段很長時就退化了。觀察查詢的過程：查詢區間會被拆成 O(log n) 個「完全包含」的節點。修改也可以用同樣的拆法：遇到完全被修改區間包含的節點，就**只更新這個節點的摘要，並在它身上記一張欠條（tag）**，寫著「我的整個子樹都還欠一次 +v，還沒往下傳」，然後就停止，不往下走。之後只有當某次操作需要往這個節點的孩子走時，才把欠條拆開交給兩個孩子（push down）。於是區間修改和查詢一樣，只碰 O(log n) 個節點。

```text
n = 8，初始全 0，range_add([2, 7], +3)

                       [0,7] sum=18
                /                       \
         [0,3] sum=6                   [4,7] sum=12 tag=+3  ← 完全包含，停在這裡
        /          \                  （孩子 [4,5]、[6,7] 仍是 0，先欠著）
   [0,1] 0      [2,3] sum=6 tag=+3      ← 完全包含，停在這裡
   (不相交)

之後 query([5, 5])：
  [0,7] 部分相交 → push 不需要（tag 為 0）→ 往右
  [4,7] 部分相交 → push：[4,5] sum=6 tag=+3、[6,7] sum=6 tag=+3，自己 tag 清為 0
  [4,5] 部分相交 → push：[4] sum=3 tag=+3、[5] sum=3 tag=+3
  [5]   完全包含 → 回傳 3
```

欠條的語意要說清楚：**節點自己的 sum 已經是正確的，tag 是「還沒交給孩子」的修改**。所以打標記時要同時更新 sum（加上 v × 區間長度）與 tag；push 時用同一個函式把 tag 套到兩個孩子身上，再把自己的 tag 清零；從孩子回來後，用 pull 重算自己。整個 lazy segment tree 就是三個小函式：`apply`（把一次修改套在一個節點上）、`push`（把欠條交給孩子）、`pull`（由孩子算回自己）。

```python
import random


class LazySegTree:
    """區間加值、區間和；閉區間 [l, r]，索引 0..n-1。"""

    def __init__(self, nums: list[int]):
        self.n = len(nums)
        self.sum = [0] * (4 * self.n)
        self.tag = [0] * (4 * self.n)
        self._build(1, 0, self.n - 1, nums)

    def _build(self, k, l, r, nums):
        if l == r:
            self.sum[k] = nums[l]
            return
        m = (l + r) // 2
        self._build(2 * k, l, m, nums)
        self._build(2 * k + 1, m + 1, r, nums)
        self.sum[k] = self.sum[2 * k] + self.sum[2 * k + 1]

    def _apply(self, k, l, r, v):           # 把「整段加 v」套在節點 k 上
        self.sum[k] += v * (r - l + 1)
        self.tag[k] += v

    def _push(self, k, l, r):               # 往下走之前，把欠條交給兩個孩子
        if self.tag[k]:
            m = (l + r) // 2
            self._apply(2 * k, l, m, self.tag[k])
            self._apply(2 * k + 1, m + 1, r, self.tag[k])
            self.tag[k] = 0

    def range_add(self, ql, qr, v, k=1, l=0, r=None):
        if r is None:
            r = self.n - 1
        if qr < l or r < ql:
            return
        if ql <= l and r <= qr:
            self._apply(k, l, r, v)
            return
        self._push(k, l, r)
        m = (l + r) // 2
        self.range_add(ql, qr, v, 2 * k, l, m)
        self.range_add(ql, qr, v, 2 * k + 1, m + 1, r)
        self.sum[k] = self.sum[2 * k] + self.sum[2 * k + 1]

    def query(self, ql, qr, k=1, l=0, r=None):
        if r is None:
            r = self.n - 1
        if qr < l or r < ql:
            return 0
        if ql <= l and r <= qr:
            return self.sum[k]
        self._push(k, l, r)
        m = (l + r) // 2
        return self.query(ql, qr, 2 * k, l, m) + self.query(ql, qr, 2 * k + 1, m + 1, r)


lz = LazySegTree([0] * 8)
lz.range_add(2, 7, 3)
assert lz.query(5, 5) == 3 and lz.query(0, 7) == 18 and lz.query(0, 1) == 0
lz.range_add(0, 4, -1)
assert lz.query(0, 7) == 13 and lz.query(4, 4) == 2
for _ in range(300):
    n = random.randint(1, 15)
    a = [random.randint(-5, 5) for _ in range(n)]
    tree = LazySegTree(a)
    for _ in range(20):
        l = random.randrange(n)
        r = random.randint(l, n - 1)
        if random.random() < 0.5:
            v = random.randint(-4, 4)
            tree.range_add(l, r, v)
            for i in range(l, r + 1):
                a[i] += v
        else:
            assert tree.query(l, r) == sum(a[l:r + 1])
print("all tests passed")
```

### 換一種修改：覆蓋（assign）與標記的合成

難題 3（699）與難題 4（715）的修改是「整段設成 x」而不是「整段加 v」。框架完全相同，只有 `apply` 和「沒有欠條」的表示法要改：tag 用 `None` 表示沒有欠條，`apply` 把 sum 設成 `x × 長度`（或把 max 設成 x），tag 設成 x；新的覆蓋直接蓋掉舊的 tag，因為後來的覆蓋會讓之前的修改完全失效。若同一棵樹同時有「加值」和「覆蓋」，tag 要存成一個函式 `x ↦ a·x + b` 之類的合成形式，並仔細定義「先套舊的、再套新的」的合成順序；面試中很少需要，但要能說出原則：**tag 必須能合成，而且套用在摘要上的結果不需要知道子樹細節**。例如「整段加 v」對區間和成立（加 v × 長度），對區間最大值也成立（最大值加 v）；但「整段開根號」對區間和就不成立，因為新的和無法從舊的和算出來，這種修改不能直接用 lazy。

### 動態開點：座標高達 10⁹ 時

核心題 3、4（729、731）與難題 4（715）的座標到 10⁹，而且操作是即時給的。開 4 × 10⁹ 的陣列不可能。觀察每次操作只會碰到 O(log C) 個節點（C 是座標範圍），q 次操作總共只會用到 O(q log C) 個節點，所以可以**用到才建立節點**：每個節點記錄左右孩子的編號，0 代表還沒建立；需要往下走時才建立孩子。沒建立孩子的節點，代表它整段的值都一樣。下面這個版本支援半開區間 `[l, r)` 加值與區間最大值，是第 731、732 題的標準零件。

```python
import random


class DynamicMaxAdd:
    """座標範圍 [lo, hi) 上的區間加值、區間最大值，節點用到才建立。"""

    def __init__(self, lo: int, hi: int):
        self.lo, self.hi = lo, hi
        self.left, self.right, self.mx, self.tag = [0], [0], [0], [0]   # 節點 0 是根

    def _new(self) -> int:
        for arr in (self.left, self.right, self.mx, self.tag):
            arr.append(0)
        return len(self.mx) - 1

    def _push(self, k: int) -> None:
        if self.left[k] == 0:                       # 第一次往下走：建立兩個孩子
            a = self._new()
            b = self._new()
            self.left[k], self.right[k] = a, b
        if self.tag[k]:
            for c in (self.left[k], self.right[k]):
                self.mx[c] += self.tag[k]
                self.tag[c] += self.tag[k]
            self.tag[k] = 0

    def add(self, l: int, r: int, v: int, k: int = 0, nl=None, nr=None) -> None:
        if nl is None:
            nl, nr = self.lo, self.hi
        if r <= nl or nr <= l:
            return
        if l <= nl and nr <= r:
            self.mx[k] += v
            self.tag[k] += v
            return
        self._push(k)
        mid = (nl + nr) // 2
        self.add(l, r, v, self.left[k], nl, mid)
        self.add(l, r, v, self.right[k], mid, nr)
        self.mx[k] = max(self.mx[self.left[k]], self.mx[self.right[k]])

    def query(self, l: int, r: int, k: int = 0, nl=None, nr=None) -> int:
        if nl is None:
            nl, nr = self.lo, self.hi
        if r <= nl or nr <= l:
            return float("-inf")
        if (l <= nl and nr <= r) or self.left[k] == 0:   # 沒有孩子：整段值相同
            return self.mx[k]
        self._push(k)
        mid = (nl + nr) // 2
        return max(self.query(l, r, self.left[k], nl, mid),
                   self.query(l, r, self.right[k], mid, nr))


tree = DynamicMaxAdd(0, 10**9)
tree.add(10, 20, 1)
tree.add(15, 25, 1)
assert tree.query(0, 10**9) == 2 and tree.query(20, 25) == 1 and tree.query(0, 10) == 0
assert tree.query(19, 20) == 2 and tree.query(25, 30) == 0
assert len(tree.mx) < 200                          # 只建立了少量節點
for _ in range(200):
    C = random.randint(1, 30)
    t, arr = DynamicMaxAdd(0, C), [0] * C
    for _ in range(25):
        l = random.randrange(C)
        r = random.randint(l + 1, C)
        if random.random() < 0.5:
            v = random.randint(-3, 3)
            t.add(l, r, v)
            for i in range(l, r):
                arr[i] += v
        else:
            assert t.query(l, r) == max(arr[l:r])
print("all tests passed")
```

這裡刻意改用**半開區間** `[nl, nr)`，`mid = (nl + nr) // 2`，左孩子 `[nl, mid)`、右孩子 `[mid, nr)`。時間軸類的題目（行事曆、區間集合、方塊）原本就是半開區間 `[start, end)`，樹也用半開區間，就完全不需要 `end − 1` 的轉換；長度為 1 的節點 `[x, x+1)` 永遠是「完全包含」或「不相交」，不會被 push，所以不會無限往下建節點。每次操作建立 O(log C) 個節點，C = 10⁹ 時大約 4 log₂ C ≈ 120 個以內（左右兩條邊界路徑各約 30 層、每層建立兩個孩子）。

## 26.6 座標壓縮

BIT 和陣列版 segment tree 的大小取決於「索引的範圍」。當索引是值（核心題 2 的值域含負數、難題 1 的前綴和可達 ±10¹⁴），或座標高達 10⁹，就要先做座標壓縮（coordinate compression）：把所有**會用到的值**收集起來、排序去重，用它在排序後的位置（rank）取代原值。只要題目只在乎值的**大小關係**而不在乎實際差距，壓縮就不會改變答案。

```python
from bisect import bisect_left, bisect_right


def compress(values):
    """回傳排序去重後的值，以及 值 → rank（從 1 開始，直接給 BIT 用）的對照。"""
    xs = sorted(set(values))
    return xs, {v: i + 1 for i, v in enumerate(xs)}


xs, rank = compress([100, -5, 7, 100, 10**9])
assert xs == [-5, 7, 100, 10**9] and rank[-5] == 1 and rank[10**9] == 4

# 查詢的門檻不一定在 xs 裡：值落在 [a, b] 的元素，對應 rank 區間 [lo_rank, hi_rank]
def rank_range(xs, a, b):
    return bisect_left(xs, a) + 1, bisect_right(xs, b)   # lo_rank > hi_rank 代表空


assert rank_range(xs, 0, 100) == (2, 3)        # 7、100
assert rank_range(xs, 8, 99) == (3, 2)         # 空區間
assert rank_range(xs, -10, -5) == (1, 1)

# 半開區間的壓縮：端點排序後，第 i 個基本段是 [xs[i], xs[i+1])
ends = sorted({1, 3, 2, 5, 6, 7})              # 方塊 [1,3)、[2,5)、[6,7) 的端點
assert ends == [1, 2, 3, 5, 6, 7]
seg = lambda l, r: (bisect_left(ends, l), bisect_left(ends, r))   # 涵蓋的基本段 [i, j)
assert seg(2, 5) == (1, 3)                     # 基本段 1 = [2,3)、基本段 2 = [3,5)
print("all tests passed")
```

壓縮有三種常見用法，對應本章不同的題目：

1. **值本身當索引**（核心題 2、5）：只收集 `nums` 的值，`rank[x]` 就是 BIT 的索引，「比 x 小的個數」就是 `prefix(rank[x] − 1)`。
2. **查詢門檻和插入值不同**（難題 1、2）：門檻是 `P[j] − upper` 或 `2·nums[j]` 這種不在插入集合裡的值。可以把門檻也一起丟進壓縮（`compress(nums + [2 * x for x in nums])`），或只壓縮插入值，查詢時用 `bisect` 把門檻換算成 rank 區間，如上面的 `rank_range`。後者比較不容易漏收值。
3. **區間的壓縮**（難題 3）：把每個半開區間 `[l, r)` 的兩個端點收集起來排序，相鄰兩個端點之間的「基本段」`[xs[i], xs[i+1])` 就是樹的一個葉子；區間 `[l, r)` 對應基本段 `[index(l), index(r))`。

區間壓縮最常見的陷阱是用**閉區間**的端點當作葉子。例如在 `[1, 10]` 上先貼一張海報，再在 `[1, 4]` 和 `[6, 10]` 各貼一張，端點壓縮成 `1, 4, 6, 10` 四個點後，4 和 6 變成相鄰，中間的 5 被吃掉，看起來第一張海報被完全蓋住，但其實 5 還露在外面。半開區間的基本段 `[4, 6)` 會自然保留這段縫隙，所以本章所有時間軸題目一律用半開區間。

壓縮要求**所有會用到的值事先知道**（離線）。如果操作是即時給的、無法預先收集座標（例如 729、731 的 `book` 是一次一次呼叫），就改用 26.5 節的動態開點，或第 13 章的有序結構。

## 26.7 何時用哪一個

| 需求 | 首選 | 原因 |
|---|---|---|
| 陣列不變，問區間和 | Prefix sum（第 7 章） | O(1) 查詢，不需要樹 |
| 所有修改都在查詢之前 | Difference array（第 7 章） | O(1) 修改，最後一次前綴和 |
| 單點修改＋區間和／計數／XOR | BIT | 程式最短、常數最小，運算可相減 |
| 「已插入的數裡有幾個 < x」 | BIT＋座標壓縮 | 計數可相減；掃描順序負責另一個維度 |
| 單點修改＋區間最大／最小／gcd | 迭代 segment tree | 運算不可相減，BIT 做不到任意區間 |
| 只會「變大」的前綴最大值 | BIT 也可以（`max` 取代 `+`） | 值單調變好時，前綴最大值可以直接合併 |
| 區間加值／覆蓋＋區間查詢 | 遞迴 lazy segment tree | 需要延遲標記；BIT 只能做「區間加＋區間和」 |
| 座標 10⁹、即時操作 | 動態開點 segment tree，或有序區間清單 | 無法預先壓縮 |
| 不相交區間集合的加入／刪除 | 有序清單＋`bisect` | 每次只改動附近的區間，程式比樹短 |
| 離線數對計數（逆序對類） | BIT 或 merge sort | 兩者都 O(n log n)；merge sort 不需要壓縮 |
| 需要「第 k 小的已插入元素」 | BIT 上二分（`lower_bound`） | O(log n)，不需要額外的二分 |

選擇的順序可以這樣想：先問**資料會不會變**（不會變就回第 7 章）；再問**運算能不能相減**（能就用 BIT）；再問**修改是單點還是區間**（區間就用 lazy）；最後問**座標能不能預先知道**（不能就動態開點）。面試時把這四個問題說出來，面試官就知道你的選擇不是背的。

BIT 與 merge sort 在計數題上常常可以互換。BIT 版本的思路是「掃描一個維度、在另一個維度上查詢」，邏輯直接，也能處理即時插入；merge sort 版本（第 11 章難題 4 的 148 題是它的排序部分）利用「左半與右半各自排序後，可以用 two pointers 數跨兩半的數對」，不需要座標壓縮，但只能離線。面試中兩種都能接受，本章的計數題會兩種都附上。

## 26.8 面試中快速寫出不出錯的版本

樹狀結構的題目最常見的失敗，不是不會，而是寫到一半邊界亂掉、debug 不完。以下是一份能在 45 分鐘內穩定寫對的流程：

1. **先講清楚三件事，再寫程式**：樹的索引是什麼（位置、值的 rank、時間座標）、每個節點存什麼（和、計數、最大值）、每次操作是「單點改＋區間查」還是「區間改＋區間查」。這三件事決定了你要寫 BIT、迭代版還是 lazy 版。
2. **能用 BIT 就用 BIT**：和與計數的題目，BIT 只有兩個五行的迴圈，背熟「`add` 往上：`i += i & -i`，`prefix` 往左：`i -= i & -i`，索引從 1 開始」就不會錯。0-indexed 的輸入在呼叫時 `+1`。
3. **區間的慣例全程只用一種**：陣列版用閉區間 `[l, r]`、時間軸用半開區間 `[l, r)`。三種情況的判斷要和慣例一致：閉區間的不相交是 `qr < l or r < ql`，半開區間是 `r <= nl or nr <= l`。混用是最常見的 off-by-one 來源。
4. **lazy 版拆成 `apply`、`push`、`pull` 三個函式**：先寫 `apply`（一次修改如何改變一個節點的摘要與 tag），再寫 `push`（對兩個孩子呼叫 `apply`、清掉自己的 tag），最後在每個「部分相交」的分支前呼叫 `push`、回來後呼叫 `pull`。修改與查詢兩個函式結構一模一樣，寫完一個複製改一行。
5. **座標壓縮寫成獨立的一行**：`xs = sorted(set(values)); rank = {v: i + 1 for i, v in enumerate(xs)}`，查詢門檻不在集合裡時用 `bisect`。先把它寫好，主迴圈裡就只剩 BIT 操作。
6. **一定要有暴力對照**：寫完後花兩分鐘寫一個 O(n²) 的暴力版本，用小的隨機輸入比對。面試中不一定能執行程式，但至少要手動追蹤三個案例：n = 1、查詢整個範圍、查詢只含一個元素的範圍；計數題再加一個「全部相同的值」，它會測出 `<` 與 `<=` 有沒有寫反。
7. **時間預算**：BIT 約 3 分鐘、迭代 segment tree 約 5 分鐘、遞迴 lazy 約 10 分鐘、動態開點約 12 分鐘。如果題目的限制允許 O(n²)（例如 n ≤ 1000 的 729、731、699），先寫 O(n²) 的簡單解並說明，再視時間升級，比一開始就寫樹更穩。

最後一點值得特別強調：**面試官通常更在意你知道何時需要樹**。729 題 n ≤ 1000，用有序清單加 `bisect` 是最佳的面試答案；如果你一上來就寫動態開點，面試官會追問「為什麼需要這麼複雜」。把樹當作「限制變大時的升級路線」說出來，是最穩的策略。

## 26.9 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| BIT 用 0-indexed | `add(0, v)` 無窮迴圈；`prefix(0)` 少算第一個元素 | 模板固定 1-indexed，呼叫時 `i + 1` |
| 用 BIT 做任意區間最大值 | `prefix(r) − prefix(l−1)` 對 max 沒有意義，答案錯 | max／min 用 segment tree；BIT 只在值只增不減時能做前綴最大值 |
| 單點「賦值」直接 `add(i, val)` | 307 題 `update` 後總和錯 | 另存原陣列，`add(i, val − nums[i])` 後更新 `nums[i]` |
| segment tree 陣列只開 2n | 遞迴版 n 不是 2 的冪次時索引越界 | 遞迴版開 4n；只有迭代版是 2n |
| 閉區間與半開區間混用 | 端點多算或少算一格，行事曆相鄰的預訂被誤判為衝突 | 陣列題用閉區間、時間軸用半開區間，三種情況的判斷跟著慣例寫 |
| lazy 忘記在往下走之前 push | 查詢到舊值、修改疊在過期的孩子上 | 每個「部分相交」分支的第一行都是 `push` |
| lazy 的 `apply` 只改 tag 沒改摘要 | 父節點 pull 時用到沒更新的孩子，區間和錯 | 規定「節點的摘要永遠正確，tag 只是欠孩子的」 |
| 覆蓋的 tag 用 0 表示「沒有」 | 覆蓋成 0 的操作被忽略（715 的刪除、699 的高度） | 用 `None` 表示沒有 tag |
| 座標壓縮漏收查詢值 | `rank[x]` KeyError，或查詢門檻落在錯的位置 | 只壓縮插入值、查詢用 `bisect` 換算；或把門檻一起壓縮 |
| 閉區間端點壓縮 | 相鄰端點之間的縫隙消失（海報問題） | 用半開區間的基本段 `[xs[i], xs[i+1])` |
| 計數題 `<` 與 `<=` 寫反 | 有重複值時答案偏多或偏少 | 「嚴格小於 x」是 `prefix(rank[x] − 1)`，「小於等於」是 `prefix(rank[x])`；用全部相同的輸入測 |
| 掃描方向與查詢對象不一致 | 315 從左往右掃卻問「右邊比我小」 | 先寫下「掃到 i 時，樹裡裝的是哪些元素」 |

## 核心題 1｜307. Range Sum Query - Mutable｜Medium

### 題目

設計一個類別 `NumArray`，用整數陣列 `nums` 初始化，支援兩種操作：`update(index, val)` 把 `nums[index]` 改成 `val`；`sumRange(left, right)` 回傳 `nums[left] + … + nums[right]`（閉區間，0-indexed）。限制：`1 <= len(nums) <= 3 × 10⁴`，元素與 `val` 都在 `-100` 到 `100` 之間，兩種操作合計最多 `3 × 10⁴` 次，而且會交錯出現。

- 範例 1：`nums = [1, 3, 5]`，`sumRange(0, 2)` 回傳 `9`；`update(1, 2)` 後陣列變成 `[1, 2, 5]`，`sumRange(0, 2)` 回傳 `8`。
- 範例 2：`nums = [1, 3, 5, 7, 9, 11, 13, 15]`，`sumRange(2, 6)` 回傳 `45`；`update(4, 0)` 後 `sumRange(2, 6)` 回傳 `36`。
- 範例 3（邊界）：`nums = [-7]`，`sumRange(0, 0)` 回傳 `-7`；`update(0, -7)`（改成同一個值）後仍回傳 `-7`。

### 思路

暴力解有兩種，剛好各自卡在一邊。直接存陣列，`update` 是 O(1)，`sumRange` 要加總 O(n)；存前綴和，`sumRange` 是 O(1)，但 `update(i)` 會讓 `P[i+1..n]` 全部改變，O(n)。操作次數 q 與 n 都是 3 × 10⁴ 時，最壞都要約 9 × 10⁸ 次運算，因為題目沒有保證修改少或查詢少。

瓶頸是「摘要的粒度」只有兩個極端。26.3 節的 BIT 讓每個前綴由 O(log n) 塊組成、每個元素只屬於 O(log n) 塊，於是 `sumRange(l, r) = prefix(r + 1) − prefix(l)` 和 `update` 都是 O(log n)。唯一要注意的是 `update` 是**賦值**而不是加值：BIT 只會「加 delta」，所以要另外保存目前的陣列，計算 `delta = val − nums[i]`，再 `add(i + 1, delta)`。

這題沒有區間修改，也只需要和，所以 BIT 是最短的答案；迭代版 segment tree（26.4 節）同樣 O(log n)，而且直接支援賦值（改葉子再往上重算），不需要保存 delta。兩者面試都可以，下面都附上。分塊（每塊 √n 個元素，存塊和）是 O(1) 修改、O(√n) 查詢，也能通過，適合在面試中當作「從 O(n) 到 O(log n)」之間的過渡說明。

```text
nums（0-indexed）= [1, 3, 5, 7, 9, 11, 13, 15]，BIT 索引 = 原索引 + 1
BIT 索引 i:   1   2   3   4   5   6   7   8
t[i]       :  1   4   5  16   9  20  13  64
負責區間    : [1] [1,2] [3] [1,4] [5] [5,6] [7] [1,8]

sumRange(2, 6) = prefix(7) − prefix(2)
  prefix(7) = t[7] + t[6] + t[4] = 13 + 20 + 16 = 49     (7 → 6 → 4 → 0)
  prefix(2) = t[2] = 4                                    (2 → 0)
  答案 49 − 4 = 45

update(4, 0)：原值 9，delta = −9，BIT 索引 5
  t[5]: 9 → 0     (5 = 0101)
  t[6]: 20 → 11   (6 = 0110)
  t[8]: 64 → 55   (8 = 1000)
  16 > 8，停止

sumRange(2, 6) = (t[7] + t[6] + t[4]) − t[2] = (13 + 11 + 16) − 4 = 36
```

更新只走了 5 → 6 → 8 三個節點，因為只有它們的負責區間包含第 5 格；查詢 `prefix(7)` 用到的 `t[6]` 正好是其中之一，所以修改立刻反映在答案裡，其餘節點完全不用動。

### 解法

```python
import random


class NumArray:
    """BIT 版本：O(n) 建樹，update 與 sumRange 都是 O(log n)。"""

    def __init__(self, nums: list[int]):
        self.n = len(nums)
        self.nums = list(nums)
        self.t = [0] * (self.n + 1)
        for i, x in enumerate(nums, 1):          # O(n) 建樹
            self.t[i] += x
            p = i + (i & -i)
            if p <= self.n:
                self.t[p] += self.t[i]

    def _prefix(self, i: int) -> int:            # nums[0] + ... + nums[i-1]
        s = 0
        while i > 0:
            s += self.t[i]
            i -= i & -i
        return s

    def update(self, index: int, val: int) -> None:
        delta = val - self.nums[index]
        self.nums[index] = val
        i = index + 1
        while i <= self.n:
            self.t[i] += delta
            i += i & -i

    def sumRange(self, left: int, right: int) -> int:
        return self._prefix(right + 1) - self._prefix(left)


class NumArraySeg:
    """迭代 segment tree 版本：直接賦值，不需要保存 delta。"""

    def __init__(self, nums: list[int]):
        self.n = len(nums)
        self.t = [0] * self.n + list(nums)
        for i in range(self.n - 1, 0, -1):
            self.t[i] = self.t[2 * i] + self.t[2 * i + 1]

    def update(self, index: int, val: int) -> None:
        i = index + self.n
        self.t[i] = val
        while i > 1:
            i //= 2
            self.t[i] = self.t[2 * i] + self.t[2 * i + 1]

    def sumRange(self, left: int, right: int) -> int:
        s, l, r = 0, left + self.n, right + 1 + self.n
        while l < r:
            if l & 1:
                s += self.t[l]
                l += 1
            if r & 1:
                r -= 1
                s += self.t[r]
            l //= 2
            r //= 2
        return s


for cls in (NumArray, NumArraySeg):
    a = cls([1, 3, 5])
    assert a.sumRange(0, 2) == 9
    a.update(1, 2)
    assert a.sumRange(0, 2) == 8
    b = cls([1, 3, 5, 7, 9, 11, 13, 15])
    assert b.sumRange(2, 6) == 45
    b.update(4, 0)
    assert b.sumRange(2, 6) == 36
    c = cls([-7])
    assert c.sumRange(0, 0) == -7
    c.update(0, -7)
    assert c.sumRange(0, 0) == -7
for _ in range(300):
    n = random.randint(1, 20)
    arr = [random.randint(-100, 100) for _ in range(n)]
    x, y = NumArray(arr), NumArraySeg(arr)
    for _ in range(30):
        if random.random() < 0.5:
            i, v = random.randrange(n), random.randint(-100, 100)
            arr[i] = v
            x.update(i, v)
            y.update(i, v)
        else:
            l = random.randrange(n)
            r = random.randint(l, n - 1)
            assert x.sumRange(l, r) == y.sumRange(l, r) == sum(arr[l:r + 1])
print("all tests passed")
```

### 複雜度與邊界

兩個版本都是建構 O(n)、`update` 與 `sumRange` O(log n)、空間 O(n)。BIT 版本多存一份 `nums` 來算 delta，segment tree 版本存 2n 個節點，兩者常數接近。邊界情況：`left == right` 時是單點查詢，`prefix(r + 1) − prefix(r)` 正確；`left = 0` 時 `_prefix(0)` 回傳 0；n = 1 時 BIT 只有 `t[1]`、segment tree 的根就是葉子 `t[1]`，迴圈都正常結束；改成同一個值時 delta = 0，不影響結果；值有負數不影響，因為 BIT 存的是和而不是計數。

### Follow-up

> [!question]- F1. 如果 update 改成「把 [l, r] 每個數都加上 v」，同時仍要 sumRange 呢？
> 單點 BIT 會退化成 O((r − l + 1) log n)。有兩種 O(log n) 做法。第一是 26.3 節的兩棵 BIT：在差分陣列上，`[l, r]` 加 v 只改 `d[l]` 與 `d[r+1]`，前綴和寫成 `x·Σd[j] − Σd[j]·(j − 1)`，兩棵 BIT 分別維護兩個和，每次操作 4 次 `add` 或 4 次 `prefix`。第二是 26.5 節的 lazy segment tree，區間加、區間和都 O(log n)。若之後還要支援「區間設成 x」或「區間最大值」，就只能用 lazy segment tree，BIT 的技巧只適用於加法。

> [!question]- F2. 如果是二維矩陣的單點修改與子矩形和呢（308. Range Sum Query 2D - Mutable）？
> 用二維 BIT：`t[i][j]` 負責 `(i − lowbit(i), i] × (j − lowbit(j), j]`，修改與查詢都是兩層 lowbit 迴圈，O(log m · log n)。子矩形和用第 7 章核心題 4（304）的容斥：`S(r2, c2) − S(r1−1, c2) − S(r2, c1−1) + S(r1−1, c1−1)`。空間 O(mn)。
> ```python
> class BIT2D:
>     def __init__(self, m, n):
>         self.m, self.n = m, n
>         self.t = [[0] * (n + 1) for _ in range(m + 1)]
>
>     def add(self, r, c, delta):            # 1-indexed
>         i = r
>         while i <= self.m:
>             j = c
>             while j <= self.n:
>                 self.t[i][j] += delta
>                 j += j & -j
>             i += i & -i
>
>     def prefix(self, r, c):                # 左上角到 (r, c) 的和
>         s, i = 0, r
>         while i > 0:
>             j = c
>             while j > 0:
>                 s += self.t[i][j]
>                 j -= j & -j
>             i -= i & -i
>         return s
> ```
> 若矩陣只有少數格子會被修改，也可以只對列做 BIT、每列存前綴和，修改 O(n)、查詢 O(m)；要依照修改與查詢的比例選擇。

> [!question]- F3. 如果查詢改成區間最小值（或最大值）呢？
> BIT 的 `prefix(r) − prefix(l − 1)` 依賴減法，最小值沒有反運算，所以不能直接用。改用迭代 segment tree，把 `+` 換成 `min`、單位元素換成 `+∞`，update 與 query 仍是 O(log n)。BIT 只有在「值只會變小」（對最小值）且「只問前綴」時才能用，例如掃描過程中維護「目前為止的前綴最小值」；本題的賦值可以讓值變大，所以不行。這是面試官確認你理解 BIT 限制的經典追問。

> [!question]- F4. 如果 update 有 10⁶ 次、sumRange 只有 10 次（或反過來）呢？
> 樹讓兩者都是 O(log n)，但當比例極端時有更好的取捨。修改極多、查詢極少：直接存陣列，修改 O(1)、每次查詢 O(n)，總共 O(U + Q·n) = 10⁶ + 3 × 10⁵，比 BIT 的 O((U + Q) log n) ≈ 1.5 × 10⁷ 更快。查詢極多、修改極少：存前綴和，修改時 O(n) 重算，查詢 O(1)。介於中間時，分塊可以把兩者調成 O(1) 修改、O(√n) 查詢，或反過來。面試中說出「依照 U 與 Q 的比例選結構」，比只說 BIT 更完整。

> [!question]- F5. 如果要問「第 t 次 update 之後，sumRange(l, r) 是多少」，t 可以是任意歷史時刻呢？
> 如果所有查詢事先知道（離線），把查詢依 t 排序，依序重播 update，重播到第 t 次時回答時間為 t 的查詢，總共 O((U + Q) log n)。若必須即時回答（線上），用 persistent segment tree（可持久化線段樹）：每次 update 只複製根到葉那條路徑上的 O(log n) 個節點，其餘節點與舊版本共用，並記下每個版本的根；查詢時從版本 t 的根往下走。每次操作 O(log n) 時間、O(log n) 新空間，總空間 O(n + U log n)。

## 核心題 2｜315. Count of Smaller Numbers After Self｜Hard

### 題目

給一個整數陣列 `nums`，回傳一個同長度的陣列 `counts`，其中 `counts[i]` 是 `nums[i]` **右邊**（索引 j > i）比 `nums[i]` 嚴格小的元素個數。限制：`1 <= len(nums) <= 10⁵`，元素在 `-10⁴` 到 `10⁴` 之間，可以重複。

- 範例 1：`nums = [5, 2, 6, 1]`，回傳 `[2, 1, 1, 0]`。5 的右邊有 2、1 比它小；2 的右邊只有 1；6 的右邊只有 1；1 的右邊沒有元素。
- 範例 2：`nums = [3, 3, 1, 3]`，回傳 `[1, 1, 0, 0]`。相等的元素不算「比較小」。
- 範例 3（邊界）：`nums = [-1]`，回傳 `[0]`；`nums = [-1, -1]`，回傳 `[0, 0]`。

### 思路

暴力解對每個 i 掃過它右邊所有元素，O(n²)，n = 10⁵ 時是 5 × 10⁹ 次比較，太慢。一個常見的半步改進是從右往左掃，維護一個「已經看過的元素」的排序串列，用 `bisect_left` 找出比 `nums[i]` 小的個數，再 `insort` 插入；查詢 O(log n)，但 Python 串列的插入要搬移元素，最壞 O(n)，整體仍是 O(n²)（實務上搬移很快，但這不是面試官想聽的複雜度）。

關鍵觀察：從右往左掃到 i 時，「i 右邊的元素」剛好就是「已經掃過的元素」，所以問題變成一個動態的計數問題：**一邊插入數字，一邊問「已插入的數中有幾個 < x」**。把「值」當作 BIT 的索引，`cnt[v]` 記錄值 v 已經插入幾次，那麼「< x 的個數」就是 `cnt` 的前綴和 `prefix(x − 1)`，插入就是 `add(x, 1)`，兩者都 O(log n)。值可能是負數，所以先做座標壓縮（26.6 節），把每個值換成 1 開始的 rank。

這是 26.1 節說的「計數工具」用法：**索引的順序交給掃描，值的大小交給 BIT**。不變式是：處理 i 之前，BIT 裡恰好裝著 `nums[i+1..n−1]` 的每個值各一次。另一個同樣 O(n log n) 的經典解法是 merge sort：排序右半時，每當左半的元素被放進結果，右半已經放出去的元素都比它小、而且原本都在它右邊，累加即可。兩者都附在解法中。

```text
nums = [5, 2, 6, 1]
座標壓縮：sorted(set) = [1, 2, 5, 6] → rank: 1→1, 2→2, 5→3, 6→4

從右往左掃，BIT 以 rank 為索引，cnt 表示每個 rank 已插入幾次
i  nums[i] rank  查詢 prefix(rank-1)          插入後 cnt[1..4]
3     1     1    prefix(0) = 0                 [1, 0, 0, 0]
2     6     4    prefix(3) = cnt1+cnt2+cnt3=1   [1, 0, 0, 1]
1     2     2    prefix(1) = 1                 [1, 1, 0, 1]
0     5     3    prefix(2) = 2                 [1, 1, 1, 1]

counts = [2, 1, 1, 0]
```

處理 i = 2（值 6）時，BIT 裡只有右邊的 1，所以「< 6 的個數」是 1；處理 i = 0（值 5）時，BIT 裡有 1、6、2，其中 < 5 的是 1 和 2，查詢 `prefix(rank(5) − 1) = prefix(2)` 剛好數到它們，6 的 rank 是 4，不在前綴內。

### 解法

```python
import random


def count_smaller(nums: list[int]) -> list[int]:
    xs = sorted(set(nums))
    rank = {v: i + 1 for i, v in enumerate(xs)}
    n, m = len(nums), len(xs)
    t = [0] * (m + 1)
    res = [0] * n
    for i in range(n - 1, -1, -1):
        r = rank[nums[i]]
        j, s = r - 1, 0                  # 查詢 rank < r 的個數
        while j > 0:
            s += t[j]
            j -= j & -j
        res[i] = s
        while r <= m:                    # 插入 nums[i]
            t[r] += 1
            r += r & -r
    return res


def count_smaller_merge(nums: list[int]) -> list[int]:
    """merge sort：排序 (值, 原索引)，左半元素輸出時，右半已輸出的都比它小。"""
    res = [0] * len(nums)

    def sort(items):
        if len(items) <= 1:
            return items
        mid = len(items) // 2
        left, right = sort(items[:mid]), sort(items[mid:])
        merged, j = [], 0
        for v, idx in left:
            while j < len(right) and right[j][0] < v:   # 嚴格小於
                merged.append(right[j])
                j += 1
            res[idx] += j                               # 右半中比 v 小的個數
            merged.append((v, idx))
        merged.extend(right[j:])
        return merged

    sort([(v, i) for i, v in enumerate(nums)])
    return res


def brute(nums):
    return [sum(nums[j] < nums[i] for j in range(i + 1, len(nums))) for i in range(len(nums))]


assert count_smaller([5, 2, 6, 1]) == [2, 1, 1, 0]
assert count_smaller([3, 3, 1, 3]) == [1, 1, 0, 0]
assert count_smaller([-1]) == [0]
assert count_smaller([-1, -1]) == [0, 0]
assert count_smaller_merge([5, 2, 6, 1]) == [2, 1, 1, 0]
assert count_smaller(list(range(10**5, 0, -1)))[:3] == [99999, 99998, 99997]   # 最大規模
for _ in range(500):
    arr = [random.randint(-5, 5) for _ in range(random.randint(1, 12))]
    assert count_smaller(arr) == count_smaller_merge(arr) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

BIT 版本：座標壓縮 O(n log n)，掃描 n 次、每次查詢與插入各 O(log m)，m 是不同值的個數，總共 O(n log n)；空間 O(n)。merge sort 版本同樣 O(n log n) 時間、O(n) 空間，遞迴深度 O(log n)。邊界情況：重複值必須「嚴格小於」，BIT 查詢 `prefix(rank − 1)` 而不是 `prefix(rank)`，merge sort 的條件是 `right[j][0] < v`，相等時左半的元素先輸出，所以相等的右半元素不會被算進去；全部相同時答案全是 0；n = 1 時直接回傳 `[0]`。值域只有 2 × 10⁴ + 1 個，也可以不壓縮，直接用 `v + 10⁴ + 1` 當索引，但壓縮的寫法在值域變成 10⁹ 時不用改。

### Follow-up

> [!question]- F1. 如果要的是「左邊比我大的個數」，或同時要四個方向的計數呢？
> 「左邊比我大」改成從左往右掃：掃到 i 時 BIT 裡是 `nums[0..i−1]`，比 `nums[i]` 大的個數是 `已插入數 − prefix(rank[nums[i]])`，也就是 `i − prefix(rank)`。四個方向（左小、左大、右小、右大）可以用一次從左往右的掃描得到左小與左大；右小與右大則用「全體中比我小的個數 − 左小」推出來，全體中比我小的個數是 `bisect_left(sorted_nums, x)`。這正是核心題 5（1395）需要的四個量，O(n log n)。

> [!question]- F2. 如果只算右邊「距離不超過 k」的元素呢？也就是 j ∈ (i, i + k]。
> 仍然從右往左掃，但 BIT 只保留一個滑動窗口：處理 i 之前，先把 `nums[i + k + 1]`（若存在）從 BIT 中移除（`add(rank, −1)`），再查詢、再插入 `nums[i]`。不變式變成「BIT 裡恰好是 `nums[i+1..i+k]`」。每個元素插入與移除各一次，總共 O(n log n)。這和第 6 章 sliding window 的「進一個、出一個」完全相同，只是窗口內的資訊從計數器換成了 BIT。

> [!question]- F3. 如果只要總數（陣列的逆序對個數）呢？
> 把 `counts` 加總即可，BIT 或 merge sort 都是 O(n log n)；merge sort 版本可以不建 `res`，在合併時直接累加 `j`，空間只需要合併用的暫存陣列。若陣列是 1..n 的排列，就不需要座標壓縮。在比較模型下，O(n log n) 是面試的標準答案；若陣列是 1..n 的排列而且只需要「逆序對是奇數還是偶數」，可以用排列的循環分解在 O(n) 內得到：奇偶性等於 n 減去循環個數的奇偶性。

> [!question]- F4. 如果值域高達 10⁹，而且元素是一個一個即時給的，無法先做座標壓縮呢？
> 有三種做法。第一，動態開點 segment tree（26.5 節）以值為索引，範圍 `[−10⁹, 10⁹]`，每次插入與查詢 O(log C)，C ≈ 2 × 10⁹，約 31 層。第二，平衡 BST 並在每個節點記錄子樹大小（order statistic tree），插入與 rank 查詢 O(log n)；Python 標準函式庫沒有，面試中可以說明但通常不要求手寫。第三，如果允許「批次」處理，可以每收到一批就重建一次壓縮。面試中最推薦第一種，因為它和本章的模板一致。

> [!question]- F5. 如果改成問「右邊落在 [nums[i] − d, nums[i] + d] 的元素個數」呢？
> 計數的範圍從前綴變成一般區間，BIT 用 `prefix(hi) − prefix(lo − 1)` 一樣 O(log n)。門檻 `nums[i] ± d` 不一定在壓縮的值集合裡，所以用 26.6 節的 `rank_range`：`lo = bisect_left(xs, x − d) + 1`、`hi = bisect_right(xs, x + d)`。總時間 O(n log n)。這個「查詢門檻不在插入集合裡」的技巧，正是難題 1（327）和難題 2（493）的核心。

## 核心題 3｜729. My Calendar I｜Medium

### 題目

實作一個行事曆類別 `MyCalendar`。`book(start, end)` 嘗試預訂半開區間 `[start, end)`，也就是所有滿足 `start <= x < end` 的實數時間 x。如果它和任何已成功的預訂**重疊**（存在共同的時間點），就拒絕並回傳 `False`，行事曆不變；否則加入行事曆並回傳 `True`。限制：`0 <= start < end <= 10⁹`，`book` 最多呼叫 1000 次。

- 範例 1：`book(10, 20)` → `True`；`book(15, 25)` → `False`（和 `[10, 20)` 在 `[15, 20)` 重疊）；`book(20, 30)` → `True`（20 不屬於 `[10, 20)`，相鄰不算重疊）。
- 範例 2：在範例 1 之後，`book(5, 10)` → `True`；`book(9, 11)` → `False`；`book(0, 100)` → `False`。
- 範例 3（邊界）：第一次 `book(0, 1)` 一定成功；`book(0, 1000000000)` 在空行事曆上也成功。

### 思路

兩個半開區間 `[s1, e1)` 和 `[s2, e2)` 重疊，若且唯若 `s1 < e2 and s2 < e1`。暴力解是每次 `book` 都和所有已預訂的區間比一次，O(n)，總共 O(n²)；n ≤ 1000 時只有 50 萬次比較，其實完全可以通過，面試時應該先說出這個解。

要做得更好，可以利用已預訂的區間**彼此不重疊**這個性質：把它們依起點排序後，終點也必然是遞增的，整個行事曆是一串排好的不相交區間。新的 `[s, e)` 只可能和兩個鄰居衝突：起點 ≤ s 的最後一個區間（前一個），以及起點 > s 的第一個區間（後一個）。前一個的終點必須 ≤ s，後一個的起點必須 ≥ e，這兩個條件都成立就能插入。用 `bisect` 找位置是 O(log n)；Python 串列的插入要搬移元素，最壞 O(n)，但搬移是一次 `memmove`，常數極小。在 Java 或 C++ 中用 `TreeMap`／`std::map` 可以做到真正的 O(log n)。

為什麼這題放在 range query 這一章？因為它是「時間軸上的區間操作」最簡單的形式，同一套思路升級後就是核心題 4（731）與難題 4（715）。用 26.5 節的動態開點 segment tree，`book` 可以寫成「查詢 `[s, e)` 的最大覆蓋次數，若為 0 就整段加 1」，兩個操作都是 O(log C)，C = 10⁹。在這題它是殺雞用牛刀，但下一題只要把「為 0」改成「小於 2」就能直接沿用。

```text
依序 book(10,20)、book(20,30)、book(5,10)、book(15,25)、book(9,11)
starts / ends 是排序後的平行陣列

book(10, 20)：空 → 插入              starts=[10]          ends=[20]
book(20, 30)：i = bisect_right(starts, 20) = 1
              前一個 [10,20)：end 20 <= 20 ✓；後一個：無 → 插入
                                      starts=[10, 20]      ends=[20, 30]
book(5, 10)： i = bisect_right(starts, 5) = 0
              前一個：無；後一個 [10,20)：start 10 >= 10 ✓ → 插入
                                      starts=[5, 10, 20]   ends=[10, 20, 30]
book(15, 25)：i = bisect_right(starts, 15) = 2
              前一個 [10,20)：end 20 > 15 ✗ → 拒絕
book(9, 11)： i = bisect_right(starts, 9) = 1
              前一個 [5,10)：end 10 > 9 ✗ → 拒絕
```

`bisect_right(starts, s)` 回傳的 i 讓 `starts[i−1] <= s < starts[i]`，所以前一個區間是 i − 1、後一個是 i。用 `bisect_right` 而不是 `bisect_left`，是為了在 `s` 剛好等於某個起點時，把那個區間當成「前一個」：此時它的終點一定 > s，會正確地拒絕。

### 解法

```python
import random
from bisect import bisect_right


class MyCalendar:
    """排序的不相交區間：只檢查前後兩個鄰居。"""

    def __init__(self):
        self.starts: list[int] = []
        self.ends: list[int] = []

    def book(self, start: int, end: int) -> bool:
        i = bisect_right(self.starts, start)
        if i > 0 and self.ends[i - 1] > start:              # 前一個還沒結束
            return False
        if i < len(self.starts) and self.starts[i] < end:   # 後一個太早開始
            return False
        self.starts.insert(i, start)
        self.ends.insert(i, end)
        return True


class MyCalendarSeg:
    """動態開點 segment tree：查詢 [start, end) 最大覆蓋數，為 0 才整段加 1。"""

    def __init__(self, lo: int = 0, hi: int = 10**9):
        self.lo, self.hi = lo, hi
        self.left, self.right, self.mx, self.tag = [0], [0], [0], [0]

    def _new(self):
        for arr in (self.left, self.right, self.mx, self.tag):
            arr.append(0)
        return len(self.mx) - 1

    def _push(self, k):
        if self.left[k] == 0:
            a = self._new()
            b = self._new()
            self.left[k], self.right[k] = a, b
        if self.tag[k]:
            for c in (self.left[k], self.right[k]):
                self.mx[c] += self.tag[k]
                self.tag[c] += self.tag[k]
            self.tag[k] = 0

    def _add(self, l, r, v, k, nl, nr):
        if r <= nl or nr <= l:
            return
        if l <= nl and nr <= r:
            self.mx[k] += v
            self.tag[k] += v
            return
        self._push(k)
        mid = (nl + nr) // 2
        self._add(l, r, v, self.left[k], nl, mid)
        self._add(l, r, v, self.right[k], mid, nr)
        self.mx[k] = max(self.mx[self.left[k]], self.mx[self.right[k]])

    def _query(self, l, r, k, nl, nr):
        if r <= nl or nr <= l:
            return 0
        if (l <= nl and nr <= r) or self.left[k] == 0:
            return self.mx[k]
        self._push(k)
        mid = (nl + nr) // 2
        return max(self._query(l, r, self.left[k], nl, mid),
                   self._query(l, r, self.right[k], mid, nr))

    def book(self, start: int, end: int) -> bool:
        if self._query(start, end, 0, self.lo, self.hi) > 0:
            return False
        self._add(start, end, 1, 0, self.lo, self.hi)
        return True


def brute(ops):
    booked, out = [], []
    for s, e in ops:
        ok = all(not (s < e2 and s2 < e) for s2, e2 in booked)
        if ok:
            booked.append((s, e))
        out.append(ok)
    return out


for cls in (MyCalendar, MyCalendarSeg):
    cal = cls()
    assert [cal.book(*p) for p in [(10, 20), (15, 25), (20, 30)]] == [True, False, True]
    assert [cal.book(*p) for p in [(5, 10), (9, 11), (0, 100)]] == [True, False, False]
    assert cls().book(0, 10**9) is True
for _ in range(300):
    ops = []
    for _ in range(random.randint(1, 15)):
        s = random.randint(0, 30)
        ops.append((s, random.randint(s + 1, 31)))
    a, b = MyCalendar(), MyCalendarSeg()
    assert [a.book(*p) for p in ops] == [b.book(*p) for p in ops] == brute(ops)
print("all tests passed")
```

### 複雜度與邊界

排序清單版本：每次 `book` 的 `bisect` 是 O(log n)，`insert` 最壞 O(n)（搬移），總共 O(n²) 最壞、但常數極小；n ≤ 1000 時微不足道。空間 O(n)。segment tree 版本每次 O(log C)，C = 10⁹ 約 30 層，每次最多建立約 4 log C 個節點，總空間 O(n log C)。邊界情況：相鄰區間（前一個的 end 等於新的 start）不算重疊，所以比較用嚴格的 `>` 與 `<`；新區間的 start 等於某個已預訂區間的 start 時，`bisect_right` 把它當成前一個，它的 end > start，正確拒絕；空行事曆時 i = 0 且清單為空，兩個檢查都跳過。

### Follow-up

> [!question]- F1. 如果要支援 cancel(start, end) 取消一筆已成功的預訂呢？
> 排序清單版本：用 `bisect_left(starts, start)` 找到那筆預訂（起點互不相同，因為區間不重疊），從兩個清單中刪除，O(log n) 找位置、O(n) 搬移；Java 的 `TreeMap.remove` 是 O(log n)。segment tree 版本：對 `[start, end)` 加 −1 即可，O(log C)。要注意驗證「這筆預訂真的存在」，否則對 segment tree 加 −1 會讓覆蓋數變成負的，之後的判斷全錯；可以另外用一個 set 記錄成功的預訂。

> [!question]- F2. 如果要回傳和新預訂衝突的那一筆既有預訂呢？
> 排序清單版本天然支援：拒絕時，衝突的那筆就是前一個（`ends[i−1] > start` 時）或後一個（`starts[i] < end` 時），直接回傳 `(starts[i−1], ends[i−1])` 或 `(starts[i], ends[i])`，O(log n)。如果新區間很長、和多筆衝突，要全部列出，就從 i − 1 開始往右掃，直到 `starts[j] >= end`，時間 O(log n + k)，k 是衝突的筆數。segment tree 只知道「有沒有」，要找出是哪一筆反而麻煩，這是排序清單的優勢。

> [!question]- F3. 如果要找「從時間 t 開始，最早能放下長度 d 的空檔」呢？
> 排序清單版本：從 `i = bisect_right(starts, t)` 開始，候選起點是 `max(t, ends[i−1])`（若 i > 0），往右逐一檢查每個空檔 `[ends[j−1], starts[j])` 的長度，直到找到 ≥ d 的；最壞 O(n)。若查詢很多，改用 segment tree，每個節點存「最長空檔、從左端開始的空檔長度、到右端結束的空檔長度」三個值，合併時 `best = max(左.best, 右.best, 左.suffix + 右.prefix)`，再在樹上往下二分找第一個 best ≥ d 的位置，O(log C)。這是經典的「旅館訂房」問題結構。

> [!question]- F4. 如果允許最多 k 筆預訂同時重疊（k 間會議室）呢？
> segment tree 版本只改一個數字：查詢 `[start, end)` 的最大覆蓋數，若 `< k` 就整段加 1，否則拒絕，O(log C)。k = 2 就是核心題 4（731），沒有上限、要回報最大重疊數就是 732 題（My Calendar III）。排序清單版本無法直接推廣，因為重疊的區間不再形成一串不相交的序列；要改用第 9 章的 sweep line，把所有端點排序後掃描，每次 `book` O(n)。

> [!question]- F5. 如果 book 的呼叫次數到 10⁵，而且所有呼叫事先就知道呢？
> 排序清單的最壞 O(n²) 搬移在 10⁵ 時仍可能偏慢（約 5 × 10⁹ 個元素搬移，雖然是 memmove，也值得避免）。既然所有區間事先知道，可以把所有端點做座標壓縮（26.6 節的半開區間壓縮），得到最多 2 × 10⁵ 個基本段，建一棵陣列版 lazy segment tree（區間加、區間最大值），每次 `book` O(log n)，比動態開點更快也更省記憶體。注意 `book` 的成功與否仍然要依序決定，離線的只是座標，不是答案。

## 核心題 4｜731. My Calendar II｜Medium

### 題目

實作 `MyCalendarTwo`。`book(start, end)` 嘗試加入半開區間 `[start, end)`：允許**兩筆**預訂重疊（double booking），但如果加入後會出現某個時間點同時被**三筆**預訂涵蓋（triple booking），就拒絕並回傳 `False`，行事曆不變；否則加入並回傳 `True`。限制：`0 <= start < end <= 10⁹`，`book` 最多呼叫 1000 次。

- 範例 1：依序 `book(10, 20)` → `True`、`book(50, 60)` → `True`、`book(10, 40)` → `True`（`[10, 20)` 被兩筆涵蓋，允許）、`book(5, 15)` → `False`（`[10, 15)` 會被三筆涵蓋）、`book(5, 10)` → `True`（`[5, 10)` 和 `[10, 20)`、`[10, 40)` 只是相鄰，這段時間只有它一筆）、`book(25, 55)` → `True`（`[25, 40)` 和 `[50, 55)` 各只有兩筆）。
- 範例 2（邊界）：`book(1, 2)`、`book(1, 2)` 都成功，第三次 `book(1, 2)` 失敗。
- 範例 3（邊界）：`book(0, 10)`、`book(10, 20)`、`book(5, 15)` 都成功，因為 `[0, 10)` 和 `[10, 20)` 相鄰不重疊，任何點最多被兩筆涵蓋。

### 思路

最直接的暴力是：對新區間內的每個時間點計算有幾筆預訂涵蓋它，但時間是實數、範圍到 10⁹，不能逐點數。正確的暴力是第 9 章的 sweep line：把所有已預訂區間與新區間的端點做成「+1／−1」事件，排序後掃描，看最大同時重疊數是否達到 3，每次 O(n log n)，總共 O(n² log n)，n = 1000 時可以通過。

一個更聰明的 O(n) 做法：除了所有預訂 `booked`，再維護一個清單 `overlaps`，存「已經被兩筆涵蓋的區域」。新區間 `[s, e)` 若和 `overlaps` 中任何一段重疊，加入後那裡就會變成三層，拒絕；否則它是安全的，把它和每一筆既有預訂的交集 `[max(s, s2), min(e, e2))`（非空時）加入 `overlaps`，再把它加入 `booked`。正確性的關鍵是：某個點在加入新區間後被三筆涵蓋，若且唯若它原本已被兩筆涵蓋（屬於 `overlaps`）且屬於新區間。

這兩種做法都依賴 n 很小。用本章的工具，這題就是核心題 3 的 segment tree 版本把門檻從 1 改成 2：**查詢 `[s, e)` 內的最大覆蓋數，若 ≥ 2 就拒絕，否則整段加 1**，每次 O(log C)。這也是推廣到「最多 k 層」唯一自然的做法，因為 `overlaps` 的想法在 k = 3 時要再多一層清單、k 更大就不可行了。下面兩種都附上。

```text
overlaps 方法，範例 1 的過程
book(10,20)：overlaps 空 → 安全；與 booked 無交集
             booked=[[10,20)]                    overlaps=[]
book(50,60)：安全；與 [10,20) 無交集
             booked=[[10,20),[50,60)]            overlaps=[]
book(10,40)：安全；與 [10,20) 交集 [10,20)，與 [50,60) 無交集
             booked=[…,[10,40)]                  overlaps=[[10,20)]
book(5,15)： 與 overlaps 的 [10,20) 重疊於 [10,15) → 拒絕
book(5,10)： 與 [10,20) 只相鄰 → 安全；與 booked 的交集都為空
             booked=[…,[5,10)]                   overlaps=[[10,20)]
book(25,55)：不碰 [10,20) → 安全；與 [10,40) 交集 [25,40)、與 [50,60) 交集 [50,55)
                                                  overlaps=[[10,20),[25,40),[50,55)]

segment tree 方法，同一個時間軸上的覆蓋數（每次 book 前查最大值）
時間:      5    10    15    20    25    40    50    55    60
book(5,15) 前：[5,10)=0  [10,15)=2  → max = 2 ≥ 2 → 拒絕
book(25,55) 前：[25,40)=1  [40,50)=0  [50,55)=1 → max = 1 → 接受並整段 +1
```

overlaps 方法中，`[5, 10)` 的終點雖然剛好等於 `[10, 40)`、`[10, 20)` 的起點，但半開區間的交集 `[max(5,10), min(10,20)) = [10, 10)` 是空的，所以不會加入 overlaps；segment tree 方法看到的是同一件事：`[5, 10)` 這段在加入前覆蓋數是 0。

### 解法

```python
import random


class MyCalendarTwo:
    """booked 存全部預訂，overlaps 存已經雙重預訂的區域；每次 O(n)。"""

    def __init__(self):
        self.booked: list[tuple[int, int]] = []
        self.overlaps: list[tuple[int, int]] = []

    def book(self, start: int, end: int) -> bool:
        for s, e in self.overlaps:
            if start < e and s < end:
                return False
        for s, e in self.booked:
            lo, hi = max(start, s), min(end, e)
            if lo < hi:
                self.overlaps.append((lo, hi))
        self.booked.append((start, end))
        return True


class MyCalendarTwoSeg:
    """動態開點 segment tree：最大覆蓋數 < 2 才整段加 1；每次 O(log C)。"""

    def __init__(self, k: int = 2, lo: int = 0, hi: int = 10**9):
        self.k, self.lo, self.hi = k, lo, hi
        self.left, self.right, self.mx, self.tag = [0], [0], [0], [0]

    def _new(self):
        for arr in (self.left, self.right, self.mx, self.tag):
            arr.append(0)
        return len(self.mx) - 1

    def _push(self, k):
        if self.left[k] == 0:
            a = self._new()
            b = self._new()
            self.left[k], self.right[k] = a, b
        if self.tag[k]:
            for c in (self.left[k], self.right[k]):
                self.mx[c] += self.tag[k]
                self.tag[c] += self.tag[k]
            self.tag[k] = 0

    def _add(self, l, r, v, k, nl, nr):
        if r <= nl or nr <= l:
            return
        if l <= nl and nr <= r:
            self.mx[k] += v
            self.tag[k] += v
            return
        self._push(k)
        mid = (nl + nr) // 2
        self._add(l, r, v, self.left[k], nl, mid)
        self._add(l, r, v, self.right[k], mid, nr)
        self.mx[k] = max(self.mx[self.left[k]], self.mx[self.right[k]])

    def _query(self, l, r, k, nl, nr):
        if r <= nl or nr <= l:
            return 0
        if (l <= nl and nr <= r) or self.left[k] == 0:
            return self.mx[k]
        self._push(k)
        mid = (nl + nr) // 2
        return max(self._query(l, r, self.left[k], nl, mid),
                   self._query(l, r, self.right[k], mid, nr))

    def book(self, start: int, end: int) -> bool:
        if self._query(start, end, 0, self.lo, self.hi) >= self.k:
            return False
        self._add(start, end, 1, 0, self.lo, self.hi)
        return True


def brute(ops, k=2, C=40):
    cover, out = [0] * C, []
    for s, e in ops:
        ok = max(cover[s:e]) < k
        if ok:
            for x in range(s, e):
                cover[x] += 1
        out.append(ok)
    return out


example = [(10, 20), (50, 60), (10, 40), (5, 15), (5, 10), (25, 55)]
for cls in (MyCalendarTwo, MyCalendarTwoSeg):
    cal = cls()
    assert [cal.book(*p) for p in example] == [True, True, True, False, True, True]
    cal = cls()
    assert [cal.book(1, 2) for _ in range(3)] == [True, True, False]
    cal = cls()
    assert [cal.book(*p) for p in [(0, 10), (10, 20), (5, 15)]] == [True, True, True]
for _ in range(300):
    ops = []
    for _ in range(random.randint(1, 15)):
        s = random.randint(0, 38)
        ops.append((s, random.randint(s + 1, 39)))
    a, b = MyCalendarTwo(), MyCalendarTwoSeg()
    assert [a.book(*p) for p in ops] == [b.book(*p) for p in ops] == brute(ops)
    c = MyCalendarTwoSeg(k=3)
    assert [c.book(*p) for p in ops] == brute(ops, k=3)
print("all tests passed")
```

### 複雜度與邊界

overlaps 版本：每次 `book` 掃過 `overlaps` 與 `booked`，O(n)，總共 O(n²)；`overlaps` 中的區段兩兩不相交（若兩段雙重區域重疊，重疊處就被至少三筆涵蓋），而且端點都來自 booked 的 2n 個端點，所以最多 O(n) 段，空間 O(n)。segment tree 版本每次 O(log C)，總空間 O(n log C)。邊界情況：交集要用半開區間判斷非空 `lo < hi`，相鄰的區間交集為空；同一個區間預訂三次時，第二次後 overlaps 有 `[1, 2)`，第三次被拒絕；被拒絕的預訂不能留下任何痕跡，所以 overlaps 版本必須先檢查完再修改，segment tree 版本必須先查詢再加值。

### Follow-up

> [!question]- F1. 為什麼不能只數「新區間和幾筆既有預訂重疊」，≥ 2 就拒絕？
> 因為和新區間重疊的兩筆預訂不一定彼此重疊。例如已有 `[10, 20)` 與 `[30, 40)`，新的 `[15, 35)` 和兩者都重疊，但任何時間點最多只被兩筆涵蓋（15–20 是它和第一筆，30–35 是它和第二筆），應該接受。三重預訂的條件是「存在一個點同時屬於三個區間」，這是一個點的性質，不是區間對的性質，所以要嘛像 overlaps 那樣記錄「已雙重的點集合」，要嘛像 segment tree 那樣記錄每個點的覆蓋數。這是面試官最常用來檢查你有沒有想清楚的反例。

> [!question]- F2. 如果改成最多允許 k 層重疊（k 是建構時給的參數）呢？
> segment tree 版本把門檻從 2 改成 k 即可（解法中的 `MyCalendarTwoSeg(k=3)` 就是 k = 3 的測試），每次 O(log C)，與 k 無關。overlaps 方法要推廣成 k − 1 層清單：第 j 層存「已被 j 筆涵蓋的區域」，新區間要和每一層求交集再放進下一層，時間與空間都隨 k 增長，不實用。sweep line 方法也能推廣：每次 O(n log n) 掃描，看最大重疊是否達到 k。

> [!question]- F3. 如果每次 book 都要回傳目前行事曆的最大重疊層數（732. My Calendar III）呢？
> 不再拒絕任何預訂，每次都整段加 1，然後回傳整棵樹的最大值，也就是根節點的 `mx[0]`，O(log C)。不用 segment tree 時的經典做法是第 7 章的 difference array 改成有序的 map：`delta[start] += 1`、`delta[end] −= 1`，再按時間順序累加求最大值，每次 O(n)，n ≤ 400 時可以通過。面試中先講 O(n) 的掃描，再升級到 segment tree，說明「每次都要全域最大值」正是 segment tree 根節點直接提供的資訊。

> [!question]- F4. 如果要支援取消一筆預訂呢？
> segment tree 版本：對該區間加 −1，O(log C)；要先確認這筆預訂真的成功過。overlaps 版本則很難支援，因為 overlaps 是由所有預訂兩兩相交得到的，刪除一筆預訂後要把它貢獻的交集移除，但同一段雙重區域可能同時來自別的配對，必須重新從 booked 計算整個 overlaps，O(n²)。這個對比說明了「存每個點的覆蓋數」比「存衍生出來的區域」更容易維護。

> [!question]- F5. book 的呼叫次數到 10⁵，Python 的動態開點太慢怎麼辦？
> 動態開點每次建立幾十個節點，10⁵ 次在 Python 中約需數秒。若所有呼叫事先知道，用 26.6 節的座標壓縮，把端點壓成最多 2 × 10⁵ 個，建陣列版 lazy segment tree，常數小很多。若必須線上處理，可以改用「有序的不相交區段清單，每段記錄覆蓋數」：每次 `book` 用 `bisect` 找到受影響的區段、在端點處切開、檢查最大值、再加 1，受影響的區段數通常很少；最壞仍可能 O(n)，但實務上很快。也可以在 Java／C++ 中用相同的動態開點，常數會好一個數量級。

## 核心題 5｜1395. Count Number of Teams｜Medium

### 題目

有 n 個士兵排成一列，第 i 個的評分是 `rating[i]`，所有評分**互不相同**。要從中選出三個人組隊，索引 `i < j < k`，條件是評分嚴格遞增 `rating[i] < rating[j] < rating[k]`，或嚴格遞減 `rating[i] > rating[j] > rating[k]`。回傳可以組成的隊伍數（同一個士兵可以出現在不同隊伍中）。限制：`3 <= n <= 1000`，`1 <= rating[i] <= 10⁵`。

- 範例 1：`rating = [2, 5, 3, 4, 1]`，回傳 `3`：`(2, 3, 4)`、`(5, 4, 1)`、`(5, 3, 1)`。
- 範例 2：`rating = [2, 1, 3]`，回傳 `0`。
- 範例 3：`rating = [1, 2, 3, 4]`，回傳 `4`，任選三個都遞增，C(4, 3) = 4。
- 範例 4（邊界）：`rating = [3, 1, 2]`，回傳 `0`；n = 3 時最多只有一隊。

### 思路

暴力解列舉所有三元組，O(n³)，n = 1000 時約 1.7 × 10⁸，Python 會超時。標準的改進是**固定中間的人 j**：一個以 j 為中間的遞增隊伍，等於「左邊選一個比它小的」乘上「右邊選一個比它大的」，兩邊的選擇互相獨立。遞減隊伍則是「左邊比它大」乘上「右邊比它小」。所以答案是 `Σ_j (leftLess[j] · rightGreater[j] + leftGreater[j] · rightLess[j])`。對每個 j 直接掃兩邊計算這四個數，是 O(n²)，n = 1000 時只有 10⁶，已經足以通過，面試中這是必須先說出的解。

要再快，瓶頸在「對每個 j 數左邊有幾個比它小」，這正是核心題 2 的計數問題，方向相反：從左往右掃，BIT 以評分為索引記錄已出現的人，`leftLess[j] = prefix(rating[j] − 1)`，`leftGreater[j] = j − leftLess[j]`（左邊共 j 人，評分互不相同）。右邊的兩個量不必再掃一次：全體中比 `rating[j]` 小的人數是它的 rank − 1（壓縮後的排名），所以 `rightLess = (rank − 1) − leftLess`，`rightGreater = (n − 1 − j) − rightLess`。一次掃描 O(n log n)。

這題的價值在於「固定中間、左右獨立相乘」的組合計數觀念，加上 BIT 把每個方向的計數降到 O(log n)。它也是 F1 中「長度為 k 的遞增子序列個數」的起點：k = 3 時固定中間元素剛好可以拆成兩邊，k 更大時就要改成 DP。

```text
rating = [2, 5, 3, 4, 1]，n = 5，壓縮後 rank：1→1, 2→2, 3→3, 4→4, 5→5
LL = leftLess，LG = leftGreater，RL = (rank − 1) − LL，RG = (n − 1 − j) − RL

j  值  左邊        LL  LG   右邊人數  RL          RG          貢獻 LL·RG + LG·RL
0  2   []           0   0      4      1 − 0 = 1   4 − 1 = 3   0·3 + 0·1 = 0
1  5   [2]          1   0      3      4 − 1 = 3   3 − 3 = 0   1·0 + 0·3 = 0
2  3   [2,5]        1   1      2      2 − 1 = 1   2 − 1 = 1   1·1 + 1·1 = 2
3  4   [2,5,3]      2   1      1      3 − 2 = 1   1 − 1 = 0   2·0 + 1·1 = 1
4  1   [2,5,3,4]    0   4      0      0 − 0 = 0   0 − 0 = 0   0·0 + 4·0 = 0
                                                              總和 = 3
```

j = 2（評分 3）貢獻 2：遞增隊伍 `(2, 3, 4)` 來自左小 2 × 右大 4，遞減隊伍 `(5, 3, 1)` 來自左大 5 × 右小 1。j = 3（評分 4）貢獻 1：只有遞減的 `(5, 4, 1)`，因為右邊沒有比 4 大的。注意 rightLess 是「全體比我小的 − 左邊比我小的」，不需要第二次掃描。

### 解法

```python
import random
from itertools import combinations


def num_teams(rating: list[int]) -> int:
    """BIT：一次從左往右掃，O(n log n)。"""
    n = len(rating)
    rank = {v: i + 1 for i, v in enumerate(sorted(rating))}   # 評分互不相同
    t = [0] * (n + 1)
    total = 0
    for j, v in enumerate(rating):
        r = rank[v]
        i, left_less = r - 1, 0
        while i > 0:
            left_less += t[i]
            i -= i & -i
        left_greater = j - left_less
        right_less = (r - 1) - left_less
        right_greater = (n - 1 - j) - right_less
        total += left_less * right_greater + left_greater * right_less
        while r <= n:
            t[r] += 1
            r += r & -r
    return total


def num_teams_quadratic(rating: list[int]) -> int:
    """固定中間的人，直接數四個量，O(n²)。"""
    total = 0
    for j, v in enumerate(rating):
        ll = sum(rating[i] < v for i in range(j))
        lg = j - ll
        rl = sum(rating[k] < v for k in range(j + 1, len(rating)))
        rg = len(rating) - 1 - j - rl
        total += ll * rg + lg * rl
    return total


def brute(rating):
    return sum(1 for a, b, c in combinations(rating, 3) if a < b < c or a > b > c)


assert num_teams([2, 5, 3, 4, 1]) == 3
assert num_teams([2, 1, 3]) == 0
assert num_teams([1, 2, 3, 4]) == 4
assert num_teams([3, 1, 2]) == 0
assert num_teams(list(range(1, 1001))) == 1000 * 999 * 998 // 6
for _ in range(300):
    arr = random.sample(range(1, 50), random.randint(3, 10))
    assert num_teams(arr) == num_teams_quadratic(arr) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

BIT 版本：排序壓縮 O(n log n)，掃描 n 次各 O(log n)，總共 O(n log n)，空間 O(n)。O(n²) 版本空間 O(1)。邊界情況：j = 0 與 j = n − 1 的貢獻一定是 0，因為某一邊是空的，公式自然得到 0，不需要特判；評分互不相同讓 `leftGreater = j − leftLess` 成立，若有重複就要改成 `j − prefix(rank)`（見 F2）；答案最大是 C(1000, 3) ≈ 1.66 × 10⁸，Python 不溢位，在 Java 中 `int` 仍夠，但 n 變大時要用 `long`。

### Follow-up

> [!question]- F1. 如果隊伍人數改成 k（數長度為 k 的嚴格遞增子序列個數）呢？
> 固定中間的拆法只適用於 k = 3。一般的 k 用 DP 加 BIT：`f[c][j]` = 以 j 結尾、長度為 c 的遞增子序列個數，`f[1][j] = 1`，`f[c][j] = Σ_{i<j, a[i]<a[j]} f[c−1][i]`。內層的「左邊、值比我小的總和」就是 BIT 的前綴和，所以準備 k 棵 BIT（或一棵一棵輪流做），從左往右掃，每個元素對每個 c 做一次查詢和一次插入，總共 O(k · n log n)。遞減的情況把值取負或反轉 rank 再做一次。
> ```python
> def count_increasing(a, k):
>     rank = {v: i + 1 for i, v in enumerate(sorted(set(a)))}
>     m = len(rank)
>     bits = [[0] * (m + 1) for _ in range(k + 1)]    # bits[c]：長度 c 的結尾計數
>     total = 0
>     for v in a:
>         r = rank[v]
>         f = [0] * (k + 1)
>         f[1] = 1
>         for c in range(2, k + 1):                   # 查 bits[c-1] 在 rank < r 的和
>             i = r - 1
>             while i > 0:
>                 f[c] += bits[c - 1][i]
>                 i -= i & -i
>         for c in range(1, k + 1):
>             i = r
>             while i <= m:
>                 bits[c][i] += f[c]
>                 i += i & -i
>         total += f[k]
>     return total
> ```

> [!question]- F2. 如果評分可以重複，而條件仍是嚴格遞增或嚴格遞減呢？
> 四個量要分別用嚴格的比較計算。`leftLess = prefix(rank − 1)`、`leftGreater = j − prefix(rank)`（左邊總數減去 ≤ 我的個數），兩者加起來不再等於 j，差額就是左邊和我相等的人。右邊的量也不能用 `rank − 1` 推，因為 rank 不再代表「全體比我小的個數」；改用 `totalLess = bisect_left(sorted_rating, v)`、`totalGreater = n − bisect_right(sorted_rating, v)`，再減去左邊的對應量。仍是 O(n log n)。用全部相同的評分測試，答案必須是 0。

> [!question]- F3. 如果要找「總評分最小的遞增隊伍」而不是計數呢？
> 仍然固定中間的 j，但要的是「左邊比 `rating[j]` 小的最小值」與「右邊比 `rating[j]` 大的最小值」。左邊那個是「值域前綴 `[1, rank − 1]` 上的最小值」，掃描過程中每個值只會被插入一次，BIT 的節點值只會變小，所以可以用 BIT 存 `min` 來回答前綴最小值（26.7 節：值單調變好時 BIT 可以做前綴最值）。右邊的「值 > rating[j] 的最小值」是值域後綴上的最小值，從右往左再掃一次，用反轉後的 rank 讓後綴變成前綴即可。總共 O(n log n)。這比計數多了一個要點：BIT 存 min 只在「只插入、不刪除」時成立。

> [!question]- F4. 如果只數「中間最高」的三人隊（i < j < k 且 rating[i] < rating[j] > rating[k]）呢？
> 套同一個框架，只換乘積：以 j 為中間的山形隊伍數是 `leftLess[j] · rightLess[j]`，兩個量在解法中都已經算出來，所以仍是一次掃描、O(n log n)。「中間最低」則是 `leftGreater · rightGreater`。這個追問在檢查你是否真正理解「固定中間、左右獨立相乘」，而不是背了一個遞增加遞減的公式。

> [!question]- F5. 如果士兵一個一個加入隊伍尾端，每加入一人就要回報目前的總隊伍數呢？
> 新加入的人只能當隊伍的最後一個（k），所以新增的遞增隊伍數 = 「以它結尾的長度 3 遞增子序列個數」= Σ（值比它小的元素 i 所結尾的長度 2 子序列數）。維護兩棵以值為索引的 BIT：`B1` 記錄每個值出現幾次，`B2` 記錄以每個值結尾的遞增數對數。新元素 x：`pairs = B1.prefix(x − 1)`、`triples = B2.prefix(x − 1)`，答案加上 triples，再 `B1.add(x, 1)`、`B2.add(x, pairs)`。遞減方向對稱再做一份。每次 O(log V)，V 是值域大小；值域未知時用動態開點。這正是 F1 的 k = 3 特例改成線上版本。

## 難題 1｜327. Count of Range Sum｜Hard

### 題目

給一個整數陣列 `nums` 和兩個整數 `lower`、`upper`，回傳有多少個子陣列 `nums[i..j]`（`i <= j`，連續、非空）的總和落在閉區間 `[lower, upper]` 內。限制：`1 <= len(nums) <= 10⁵`，元素在 `-2³¹` 到 `2³¹ − 1` 之間（可以是負數），`-10⁵ <= lower <= upper <= 10⁵`，答案保證能用 32 位元整數表示。

- 範例 1：`nums = [-2, 5, -1]`、`lower = -2`、`upper = 2`，回傳 `3`：`[-2]` 和為 −2、`[-1]` 和為 −1、`[-2, 5, -1]` 和為 2。
- 範例 2：`nums = [0]`、`lower = 0`、`upper = 0`，回傳 `1`。
- 範例 3：`nums = [1, -1, 1, -1]`、`lower = 0`、`upper = 0`，回傳 `4`：`[1, -1]` 出現在索引 0–1、2–3，`[-1, 1]` 在 1–2，整個陣列 0–3。
- 範例 4（邊界）：`nums = [2147483647, -2147483648, -1, 0]`、`lower = -1`、`upper = 0`，回傳 `4`；元素接近 32 位元極限，前綴和會超過 32 位元。

### 提示

> [!tip]- 提示 1
> 子陣列和是兩個前綴和的差：`sum(nums[i..j]) = P[j+1] − P[i]`。題目變成數「有幾個數對 a < b 讓 `P[b] − P[a]` 落在 [lower, upper]」。

> [!tip]- 提示 2
> 固定 b，條件改寫成 `P[b] − upper <= P[a] <= P[b] − lower`。這是「在 b 之前出現過的前綴和中，有幾個落在某個值的範圍內」。

> [!tip]- 提示 3
> 從左往右掃 b，用 BIT 記錄已出現的前綴和（座標壓縮後的 rank），查詢門檻 `P[b] − upper`、`P[b] − lower` 不一定出現過，用 `bisect` 換算成 rank 區間。另一條路是對前綴和陣列做 merge sort，合併前用兩個單調指標數跨兩半的數對。

### 詳解

**為什麼直覺做法不行**。暴力列舉所有子陣列並用前綴和 O(1) 算和，是 O(n²) = 10¹⁰，太慢。第 7 章核心題 2（560）的 hash map 技巧只能處理「和**等於** k」：對每個 b 查 `count[P[b] − k]`。這題是範圍，要查的是 `count[P[b] − upper] + … + count[P[b] − lower]`，範圍寬度可達 2 × 10⁵，逐一查詢變成 O(n · (upper − lower))，最壞 2 × 10¹⁰。第 6 章的 sliding window 也不行，因為有負數，前綴和不單調，窗口右端往右移時，合法的左端不會只往一個方向移動。

**突破點：範圍計數就是 BIT 的前綴和相減**。把問題寫成數對計數：對每個 b，要數 a < b 中有幾個 `P[a] ∈ [P[b] − upper, P[b] − lower]`。從左往右掃 b，掃到 b 時 BIT 裡恰好裝著 `P[0..b−1]`；「已插入的值落在 [x, y] 的個數」就是 `prefix(rank(y)) − prefix(rank(x) − 1)`。前綴和最大可達 ±2 × 10¹⁴，必須座標壓縮；門檻 `P[b] − upper` 不一定是某個前綴和，所以只壓縮 P 本身，查詢時用 `bisect_left(xs, x)` 與 `bisect_right(xs, y)` 換算 rank 區間（26.6 節的 `rank_range`）。每個 b 一次查詢、一次插入，O(n log n)。

**另一條路：merge sort**。對前綴和陣列 P 做 merge sort。合併左半 `L` 與右半 `R`（各自已排序）時，跨兩半的數對 `(a ∈ L, b ∈ R)` 原本的索引一定是 a < b，這正是我們要數的方向。對 L 中由小到大的每個值 x，`R` 中滿足 `x + lower <= y <= x + upper` 的 y 是一段連續區間，而且 x 變大時區間的兩端都只會往右移，所以兩個指標合計 O(n) 就能數完，再正常合併。總時間 O(n log n)，不需要座標壓縮。

**正確性**。BIT 版本的不變式是「處理 b 時，BIT 裡恰好是 `P[0..b−1]` 各一次」，所以每個數對 (a, b) 在處理 b 時恰好被數一次。merge sort 版本中，每個數對 (a, b) 恰好在一次合併中第一次被分到不同的兩半，那次合併中 a 在左、b 在右，被數一次；之後它們在同一半，不會再被數。

```text
nums = [-2, 5, -1]，lower = -2，upper = 2
前綴和 P = [0, -2, 3, 2]，壓縮 xs = [-2, 0, 2, 3]（rank 1..4）

掃描 b，查詢 P[a] ∈ [P[b] − 2, P[b] + 2]，再插入 P[b]
b  P[b]  查詢範圍     rank 區間（bisect）   BIT 中已有的值      命中     累計
0    0   （先插入 P[0]，沒有更早的 a）       {}                  —        0
1   -2   [-4, 0]      [1, 2]               {0}                 0 → 1    1
2    3   [1, 5]       [3, 4]               {0, -2}             無 → 0   1
3    2   [0, 4]       [2, 4]               {0, -2, 3}          0, 3 → 2 3

命中對應的子陣列：
  b=1, a=0：P[1] − P[0] = −2 → nums[0..0] = [-2]
  b=3, a=0：P[3] − P[0] =  2 → nums[0..2] = [-2, 5, -1]
  b=3, a=2：P[3] − P[2] = −1 → nums[2..2] = [-1]
```

b = 2 時查詢範圍 `[1, 5]`，1 和 5 都不是前綴和，`bisect_left(xs, 1) = 2`、`bisect_right(xs, 5) = 4`，換成 1-indexed rank 是 `[3, 4]`，也就是值 2 和 3；此時 BIT 裡只有 0 和 −2，所以命中 0 個。這說明了為什麼門檻要用 bisect，而不是去查 `rank[P[b] − upper]`。

### 解法

```python
import random
from bisect import bisect_left, bisect_right


def count_range_sum(nums: list[int], lower: int, upper: int) -> int:
    P = [0]
    for x in nums:
        P.append(P[-1] + x)
    xs = sorted(set(P))
    m = len(xs)
    t = [0] * (m + 1)

    def prefix(i):
        s = 0
        while i > 0:
            s += t[i]
            i -= i & -i
        return s

    total = 0
    for p in P:
        lo = bisect_left(xs, p - upper)          # rank 區間 [lo + 1, hi]
        hi = bisect_right(xs, p - lower)
        total += prefix(hi) - prefix(lo)
        i = bisect_left(xs, p) + 1               # 插入 p
        while i <= m:
            t[i] += 1
            i += i & -i
    return total


def count_range_sum_merge(nums: list[int], lower: int, upper: int) -> int:
    P = [0]
    for x in nums:
        P.append(P[-1] + x)

    def sort(arr):
        if len(arr) <= 1:
            return arr, 0
        mid = len(arr) // 2
        L, c1 = sort(arr[:mid])
        R, c2 = sort(arr[mid:])
        cnt, lo, hi = c1 + c2, 0, 0
        for x in L:                               # x 變大時，lo、hi 只往右移
            while lo < len(R) and R[lo] < x + lower:
                lo += 1
            while hi < len(R) and R[hi] <= x + upper:
                hi += 1
            cnt += hi - lo
        return sorted(L + R), cnt                 # 也可以手寫線性合併

    return sort(P)[1]


def brute(nums, lower, upper):
    n, res = len(nums), 0
    for i in range(n):
        s = 0
        for j in range(i, n):
            s += nums[j]
            res += lower <= s <= upper
    return res


assert count_range_sum([-2, 5, -1], -2, 2) == 3
assert count_range_sum([0], 0, 0) == 1
assert count_range_sum([1, -1, 1, -1], 0, 0) == 4
assert count_range_sum([2147483647, -2147483648, -1, 0], -1, 0) == 4
assert count_range_sum_merge([-2, 5, -1], -2, 2) == 3
assert count_range_sum([5], 1, 4) == 0
for _ in range(500):
    arr = [random.randint(-5, 5) for _ in range(random.randint(1, 10))]
    lo = random.randint(-6, 6)
    hi = random.randint(lo, 7)
    assert count_range_sum(arr, lo, hi) == count_range_sum_merge(arr, lo, hi) == brute(arr, lo, hi)
print("all tests passed")
```

### 複雜度與邊界

BIT 版本：前綴和 O(n)，排序壓縮 O(n log n)，掃描 n + 1 次、每次兩次 `bisect` 和三次 BIT 操作，總共 O(n log n)，空間 O(n)。merge sort 版本：每層的計數指標 O(n)，用 `sorted(L + R)` 合併每層 O(n log n)、總共 O(n log² n)；改成手寫線性合併就是 O(n log n)，面試時說明即可。邊界情況：前綴和可達 ±2 × 10¹⁴，Python 不溢位，Java／C++ 要用 64 位元；P 中有重複值時 BIT 的計數會正確累加（同一個 rank 加多次）；`lower == upper` 時退化成「和等於 k」，結果和 560 題一致；記得 `P[0] = 0` 也要插入，否則以索引 0 開頭的子陣列會漏掉。

### Follow-up

> [!question]- F1. 如果所有元素都是非負數呢？
> 前綴和變成非遞減，可以不用樹。「和 ≤ upper 的子陣列個數」用 sliding window O(n)：右端 j 往右時，把左端 i 往右推到 `P[j+1] − P[i] <= upper`，貢獻 `j − i + 1`。答案 = atMost(upper) − atMost(lower − 1)，兩次各 O(n)，總共 O(n)。這是第 6 章難題 3（992）「恰好 = 至多 − 至多」的同一個技巧；負數之所以需要 BIT，就是因為窗口的單調性消失了。

> [!question]- F2. 如果要的是「和落在 [lower, upper] 的最長子陣列」長度呢？
> 對每個 b，要找最小的 a < b 使 `P[a] ∈ [P[b] − upper, P[b] − lower]`。把 BIT 換成以壓縮後前綴和為索引的迭代 segment tree，節點存「最早出現的索引」（min），每個值只在第一次出現時寫入。掃到 b 時做區間最小值查詢，若結果 a 存在就更新 `b − a`，然後把 P[b] 寫入（若它的位置還是 +∞）。每步 O(log n)，總共 O(n log n)。BIT 做不到，因為查詢是一般區間的最小值，不是前綴。

> [!question]- F3. 如果條件改成「平均值至少為 t」的子陣列個數呢？
> 平均值 ≥ t 等價於 `Σ (nums[i] − t) >= 0`，把每個元素減去 t 後重新算前綴和 Q，問題變成數 a < b 且 `Q[a] <= Q[b]` 的數對，也就是本題 lower = 0、upper = +∞ 的特例（或「非逆序對」個數），BIT 掃描 O(n log n)。若 t 不是整數，例如 t = p/q，就把每個元素乘以 q 再減 p，維持整數運算。若改成平均值同時有上下界，兩個條件對應兩組不同的前綴和，變成三維的支配計數（索引、Q₁、Q₂），要用 CDQ 分治等技巧做到 O(n log² n)，面試中說出這個結構即可。

> [!question]- F4. 如果是二維矩陣，問有幾個子矩形的和落在 [lower, upper] 呢？
> 固定上下兩列 r1 ≤ r2（O(m²) 組），把中間每一行壓成一個數 `colsum[c]`，問題就變成一維的本題，O(n log n)。總共 O(m² · n log n)，若 m > n 就轉置讓 m 是較小的維度。這和第 7 章難題 1（1074）「和等於 target 的子矩形個數」是同一個降維技巧，差別只在一維的部分從 hash map 換成 BIT；363 題（和不超過 K 的最大子矩形）則把一維部分換成有序結構上的 bisect。

> [!question]- F5. 如果 nums 是串流，每加入一個元素就要回報目前的總數呢？
> BIT 版本本身就是線上的：新元素到來時算出新的前綴和 p，查詢 `[p − upper, p − lower]` 的已出現個數加到答案，再插入 p。唯一的問題是座標壓縮需要事先知道所有前綴和。改用動態開點 segment tree，以前綴和的值為索引，範圍設為 `[−2 × 10¹⁴, 2 × 10¹⁴]`，約 49 層，每次 O(log C)。merge sort 版本是離線演算法，無法這樣用，這是 BIT／segment tree 相對於分治的一個實際優勢。

### 心得

關鍵突破是把「子陣列和落在範圍內」改寫成「前綴和數對的差落在範圍內」，再固定右端，變成「已出現的值有幾個落在某個範圍」，這正是 BIT 的範圍計數。它和核心題 2（315）的結構完全相同，只是查詢從「< x 的個數」變成「落在 [x, y] 的個數」，而且門檻不在插入集合中，所以要用 `bisect` 換算 rank。面試時建議的敘事是：先說 O(n²)，再說明 560 的 hash map 為什麼只能處理等於、sliding window 為什麼因為負數失效，然後提出「前綴和 + 範圍計數」，最後二選一實作 BIT 或 merge sort。主動提到 `P[0] = 0` 要插入、前綴和要 64 位元，是最能展現細心的兩個點。

## 難題 2｜493. Reverse Pairs｜Hard

### 題目

給一個整數陣列 `nums`，一個「重要反轉對」是索引 `i < j` 且 `nums[i] > 2 × nums[j]`。回傳重要反轉對的個數。限制：`1 <= len(nums) <= 5 × 10⁴`，元素在 `-2³¹` 到 `2³¹ − 1` 之間。

- 範例 1：`nums = [1, 3, 2, 3, 1]`，回傳 `2`：`(1, 4)` 是 3 > 2 × 1，`(3, 4)` 也是 3 > 2 × 1。
- 範例 2：`nums = [2, 4, 3, 5, 1]`，回傳 `3`：`(1, 4)`、`(2, 4)`、`(3, 4)`，即 4、3、5 都大於 2 × 1。
- 範例 3（邊界）：`nums = [-5, -5]`，回傳 `1`，因為 −5 > 2 × (−5) = −10；負數讓「乘以 2」反而變小。
- 範例 4（邊界）：`nums = [5]`，回傳 `0`；`nums = [2147483647, 2147483647]` 回傳 `0`，但在 32 位元語言中 `2 × nums[j]` 會溢位。

### 提示

> [!tip]- 提示 1
> 這和核心題 2（315）很像：對每個 j，數它左邊有幾個 `nums[i]` 大於某個門檻。差別是門檻是 `2 × nums[j]`，不是 `nums[j]` 本身。

> [!tip]- 提示 2
> 從左往右掃，把看過的 `nums[i]` 插入以值為索引的 BIT；對 j，要數的是「已插入的值中 > 2·nums[j] 的個數」= 已插入總數 − 「≤ 2·nums[j] 的個數」。

> [!tip]- 提示 3
> 門檻 `2·nums[j]` 不一定出現在 nums 中，用 `bisect_right(xs, 2 * nums[j])` 換算成 rank；或用 merge sort：合併前，對左半的每個元素，用一個單調指標數右半有幾個元素滿足條件，再另外做正常的合併。

### 詳解

**為什麼直覺做法不行**。暴力 O(n²) = 1.25 × 10⁹ 次比較，太慢。直接套 315 的 BIT 程式也不對：315 的查詢值和插入值是同一個集合（`nums[j]` 本身），座標壓縮時所有查詢點都有 rank；這題的查詢點 `2·nums[j]` 不在插入集合裡，`rank[2 * nums[j]]` 會 KeyError，或在自己手寫壓縮時落到錯的位置。另一個常見錯誤是在 merge sort 中「一邊合併一邊數」：合併的比較條件是 `L[i] <= R[j]`，但計數條件是 `L[i] > 2·R[j]`，兩者的分界點不同，混在同一個迴圈裡會數錯。

**突破點：查詢門檻與插入值分開處理**。BIT 版本：只壓縮 nums 的值 `xs = sorted(set(nums))`，掃到 j 時，`≤ 2·nums[j]` 的已插入個數是 `prefix(bisect_right(xs, 2 * nums[j]))`，因為 `bisect_right` 回傳的正好是 xs 中 ≤ 門檻的值的個數，也就是最大的合法 rank。用已插入的總數 j 減掉它，就是 > 門檻的個數。然後把 `nums[j]` 插入。merge sort 版本：左右兩半各自排序後，對左半由小到大的每個 x，右半中滿足 `x > 2y` 的 y 是一段前綴（右半由小到大，2y 也由小到大），而且 x 變大時這段前綴只會變長，所以一個指標 O(n) 數完；**數完之後**再做一般的合併。

**正確性與負數**。條件 `nums[i] > 2·nums[j]` 對任何正負號都直接比較，不需要分情況，因為我們從未把不等式兩邊除以任何數；這和第 8 章難題 5（2040）需要依正負號處理取整方向不同。merge sort 版本中，「右半的 2y 對 y 單調遞增」對負數也成立，所以指標的單調性不受影響。

```text
nums = [2, 4, 3, 5, 1]，xs = [1, 2, 3, 4, 5]
從左往右掃 j；cnt(≤ 門檻) = prefix(bisect_right(xs, 2·nums[j]))

j  nums[j]  門檻 2·nums[j]  bisect_right  已插入   ≤門檻個數  >門檻 = j − ≤門檻   累計
0     2          4               4         {}          0          0               0
1     4          8               5         {2}         1          0               0
2     3          6               5         {2,4}       2          0               0
3     5         10               5         {2,4,3}     3          0               0
4     1          2               2         {2,4,3,5}   1（值 2）  4 − 1 = 3       3

merge sort 最後一層：L = [2, 4]（索引 0,1），R = [1, 3, 5]（索引 2,3,4）
  x = 2：R 中 2 > 2y 的 y：無（2 > 2·1 不成立）       p = 0，貢獻 0
  x = 4：4 > 2·1 ✓，4 > 2·3 ✗                         p = 1，貢獻 1   ← 數對 (4, 1)
  數完再合併成 [1, 2, 3, 4, 5]；其他兩個數對 (3, 1)、(5, 1) 在 R 內部的遞迴中被數到
```

BIT 的最後一步，門檻 2 的 `bisect_right` 是 2，代表 xs 中前兩個值 1、2 ≤ 2；已插入的 {2, 4, 3, 5} 裡只有 2 落在這個前綴，所以 > 2 的有 3 個。merge sort 的例子則展示了「先數、再合併」：x = 4 時指標停在 1，因為 4 > 2·3 不成立，而合併的分界點完全不同（4 要排在 3 之後）。

### 解法

```python
import random
from bisect import bisect_right


def reverse_pairs(nums: list[int]) -> int:
    xs = sorted(set(nums))
    m = len(xs)
    t = [0] * (m + 1)
    total = 0
    for j, v in enumerate(nums):
        i, le = bisect_right(xs, 2 * v), 0       # 已插入中 <= 2v 的個數
        while i > 0:
            le += t[i]
            i -= i & -i
        total += j - le                          # 已插入共 j 個
        i = bisect_right(xs, v)                  # v 的 rank（v 一定在 xs 中）
        while i <= m:
            t[i] += 1
            i += i & -i
    return total


def reverse_pairs_merge(nums: list[int]) -> int:
    def sort(arr):
        if len(arr) <= 1:
            return arr, 0
        mid = len(arr) // 2
        L, c1 = sort(arr[:mid])
        R, c2 = sort(arr[mid:])
        cnt, p = c1 + c2, 0
        for x in L:                              # 先數：x 變大時 p 只往右
            while p < len(R) and x > 2 * R[p]:
                p += 1
            cnt += p
        merged, i, j = [], 0, 0                  # 再合併
        while i < len(L) and j < len(R):
            if L[i] <= R[j]:
                merged.append(L[i])
                i += 1
            else:
                merged.append(R[j])
                j += 1
        merged.extend(L[i:])
        merged.extend(R[j:])
        return merged, cnt

    return sort(nums)[1]


def brute(nums):
    n = len(nums)
    return sum(nums[i] > 2 * nums[j] for i in range(n) for j in range(i + 1, n))


assert reverse_pairs([1, 3, 2, 3, 1]) == 2
assert reverse_pairs([2, 4, 3, 5, 1]) == 3
assert reverse_pairs([-5, -5]) == 1
assert reverse_pairs([5]) == 0
assert reverse_pairs([2147483647, 2147483647]) == 0
assert reverse_pairs_merge([2, 4, 3, 5, 1]) == 3
for _ in range(500):
    arr = [random.randint(-8, 8) for _ in range(random.randint(1, 12))]
    assert reverse_pairs(arr) == reverse_pairs_merge(arr) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

BIT 版本：壓縮 O(n log n)，每個 j 兩次 `bisect` 與兩次 BIT 操作，總共 O(n log n)，空間 O(n)。merge sort 版本：每層計數 O(n)、合併 O(n)，共 log n 層，O(n log n) 時間、O(n) 暫存空間。邊界情況：負數直接比較即可，例如 −5 > −10；`bisect_right(xs, 2 * v)` 可能是 0（門檻比所有值都小）或 m（門檻比所有值都大），BIT 的 `prefix(0) = 0` 和 `prefix(m)` 都正確；32 位元語言中 `2 * nums[j]` 會溢位，要轉成 64 位元（見 F5）；n = 1 時答案為 0。

### Follow-up

> [!question]- F1. 如果條件改成 nums[i] > c · nums[j]，c 是任意正有理數 p/q 呢？
> 為了避免浮點誤差，把條件改寫成整數比較 `q · nums[i] > p · nums[j]`。BIT 版本中，壓縮的值改成 `q · nums[i]`，門檻是 `p · nums[j]`，用 `bisect_right` 換算 rank，其他完全不變，O(n log n)。merge sort 版本中，右半 `p · y` 對 y 仍然單調遞增（p > 0），指標的單調性成立。若 c 是負數，`c · y` 對 y 遞減，merge sort 中滿足條件的 y 從前綴變成後綴，指標要從右往左移；BIT 版本則完全不受影響，因為它不依賴門檻的單調性，這是 BIT 寫法較穩健的地方。

> [!question]- F2. 為什麼 merge sort 不能在合併的同一個迴圈裡順便計數？
> 合併時決定先輸出誰的條件是 `L[i] <= R[j]`，計數需要的是「對每個 x ∈ L，有幾個 y ∈ R 滿足 x > 2y」。在 315 題裡兩個條件剛好重合（「右半已輸出的元素都比 x 小」），所以可以同一個迴圈完成；這題 2y 和 y 的分界點不同，例如 L = [4]、R = [3]：合併時 3 先輸出，但 4 > 6 不成立，若照「右半已輸出幾個」計數就會多算。所以要先用獨立的指標數完，再合併，兩個步驟各 O(n)，不影響總複雜度。

> [!question]- F3. 如果只數 j − i ≤ k 的重要反轉對呢？
> BIT 改成維護一個滑動窗口：掃到 j 時，BIT 裡只保留 `nums[j−k..j−1]`。處理 j 之前，若 j − k − 1 ≥ 0，就把 `nums[j−k−1]` 從 BIT 移除（加 −1）；「已插入總數」也要改成窗口大小 `min(j, k)`。每個元素插入與移除各一次，O(n log n)。merge sort 版本很難加上索引距離的限制，因為排序會打亂索引，這又是 BIT 掃描法的優勢。

> [!question]- F4. 如果要回傳每個 j 各自有幾個 i 和它構成重要反轉對呢？
> BIT 版本在迴圈中已經算出每個 j 的 `j − le`，存進陣列即可，不增加複雜度。merge sort 版本要像 315 的 `count_smaller_merge` 那樣排序 `(值, 原索引)`，並在計數時把貢獻記到右半元素的索引上：對每個 x ∈ L，指標 p 之前的右半元素都要各加 1，直接加是 O(n²)；改成在 R 上做差分（`diff[0] += 1、diff[p] −= 1`），合併前一次前綴和攤回各元素，仍是 O(n log n)。這個對比說明了「需要每個元素的答案」時，BIT 通常更直接。

> [!question]- F5. 在 Java 或 C++ 中實作時，要注意什麼？
> `2 * nums[j]` 在 `nums[j]` 接近 2³¹ 時會溢位成負數，讓判斷完全相反，必須寫成 `2L * nums[j]`（Java）或先轉 `long long`。座標壓縮時，若把門檻也放進壓縮陣列，陣列型態也要是 64 位元。merge sort 版本的 `x > 2 * R[p]` 同樣要用 64 位元比較；另一種寫法是 `x / 2.0 > R[p]`，但浮點比較在大數時有誤差風險，不建議。Python 的整數沒有上限，所以本書的程式不需要處理，但面試時主動提出這一點，代表你考慮過其他語言的實作。

### 心得

關鍵突破是把「查詢門檻」和「插入的值」分開處理：插入的是 `nums[i]`，查詢的是 `2·nums[j]`，所以 BIT 用 `bisect` 換算門檻的 rank，merge sort 則要先計數再合併。它和核心題 2（315）的關係是「同一個掃描框架，門檻不同」，和難題 1（327）的關係是「都需要用 bisect 處理不在集合裡的查詢值」。面試時先說暴力解，再指出「這是一個 i < j 的數對計數，一個維度交給掃描、另一個交給 BIT」，然後主動說明為什麼 315 的程式不能直接套用；如果選 merge sort，就一定要說明為什麼計數和合併要分開，這是面試官最常追問的一點。

## 難題 3｜699. Falling Squares｜Hard

### 題目

在 x 軸上方依序丟下 n 個正方形。`positions[i] = [left, side]` 表示第 i 個正方形的左邊緣對齊 x = left、邊長為 side，它在 x 軸上佔據半開區間 `[left, left + side)`。正方形從很高的地方垂直落下，直到它的底部碰到 x 軸或某個已落下正方形的頂部才停住；**只碰到邊緣（側面相鄰）不算支撐**。每丟下一個，回報目前整堆的最高高度。回傳這 n 個高度組成的陣列。限制：`1 <= n <= 1000`，`1 <= left <= 10⁸`，`1 <= side <= 10⁶`。

- 範例 1：`positions = [[1, 2], [2, 3], [6, 1]]`，回傳 `[2, 5, 5]`。第一個落在地上，頂部高 2；第二個佔 `[2, 5)`，和第一個在 `[2, 3)` 重疊，落在它上面，頂部 2 + 3 = 5；第三個佔 `[6, 7)`，下面沒有東西，高 1，但整堆最高仍是 5。
- 範例 2：`positions = [[100, 100], [200, 100]]`，回傳 `[100, 100]`。第二個的區間 `[200, 300)` 和第一個 `[100, 200)` 只在 x = 200 相鄰，不算重疊，所以它落在地上。
- 範例 3（邊界）：`positions = [[1, 5], [2, 2], [3, 1]]`，回傳 `[5, 7, 8]`，三個方塊一路疊高。

### 提示

> [!tip]- 提示 1
> 新方塊落下的高度，只取決於它底下 `[left, left + side)` 這段區間目前的最高點。它停住後，這整段的高度都變成「原本的最高點 + side」。

> [!tip]- 提示 2
> 這是兩個操作：「區間最大值查詢」與「把整段區間設成同一個值」。n ≤ 1000 時 O(n²) 也能過；要 O(n log n) 就需要 lazy segment tree。

> [!tip]- 提示 3
> 座標到 10⁸，但只有 2n 個端點有意義。把所有 `left` 與 `left + side` 壓縮，相鄰端點之間的基本段當作葉子；方塊 `[l, r)` 涵蓋基本段 `[idx(l), idx(r))`。整段覆蓋用 `None` 表示沒有欠條。

### 詳解

**直覺做法與它的限制**。最直接的 O(n²) 做法是：保存每個已落下方塊的 `(l, r, top)`，新方塊落下時，和每個已落下的方塊檢查是否重疊（`l1 < r2 and l2 < r1`），取重疊者 top 的最大值作為底部，新的 top = 底部 + side。正確性來自一個觀察：某個位置的高度，就是所有涵蓋該位置的方塊中最高的 top，所以「新方塊底下的最高點」等於「和它重疊的方塊中最大的 top」。n = 1000 時只有 50 萬次比較，這是面試中應該先寫的解。它的瓶頸是每次都要掃過所有舊方塊；n 到 10⁵ 時就不行了。

**突破點：把地形當作一個會被修改的陣列**。把 x 軸上的「地形高度」看成一個陣列 `height[x]`。新方塊 `[l, r)` 落下時，需要 `base = max(height[l..r−1])`，然後把 `height[l..r−1]` **全部設成** `base + side`。為什麼是「設成」而不是「加上」？因為新方塊的頂部是平的：原本這段地形高低不平，方塊停在最高點上，底下較低的地方會留下空隙，但從上方看，整段的高度都變成同一個值。這就是 26.5 節的「區間覆蓋＋區間最大值」，用 lazy segment tree 每次 O(log n)。

**座標壓縮**。x 的範圍到 10⁸ + 10⁶，但高度只會在方塊的端點處改變，所以把所有 `left` 與 `left + side` 收集起來排序，得到最多 2n 個端點、2n − 1 個基本段 `[xs[i], xs[i+1])`。每個基本段內的高度永遠相同，因為沒有任何方塊的邊界落在它內部。方塊 `[l, r)` 對應的基本段是 `idx(l)` 到 `idx(r) − 1`（閉區間）。用半開區間的基本段，範例 2 中相鄰的兩個方塊自然不會被誤判為重疊：`[100, 200)` 是基本段 0，`[200, 300)` 是基本段 1，兩者互不相干。

**標記的細節**。覆蓋的 tag 用 `None` 表示「沒有欠條」，因為高度 0 雖然不會出現在本題的覆蓋值中，但習慣上用 `None` 才不會在其他題目（例如 715 的刪除，覆蓋成 0）出錯。`apply(k, v)` 把節點 k 的最大值設成 v、tag 設成 v；整段覆蓋後，max 就是 v 本身，不需要知道子樹原來的樣子，這正是覆蓋可以用 lazy 的理由。全域最高點另外用一個變數維護即可，因為高度只會增加。

```text
positions = [[1,2], [2,3], [6,1]] → 區間 [1,3)、[2,5)、[6,7)
端點排序 xs = [1, 2, 3, 5, 6, 7]
基本段：  s0=[1,2)  s1=[2,3)  s2=[3,5)  s3=[5,6)  s4=[6,7)

方塊       基本段      查詢 max        新高度        覆蓋後各段高度 (s0..s4)   全域最高
[1,3)      s0..s1      max(0,0)=0      0+2 = 2       [2, 2, 0, 0, 0]           2
[2,5)      s1..s2      max(2,0)=2      2+3 = 5       [2, 5, 5, 0, 0]           5
[6,7)      s4..s4      0               0+1 = 1       [2, 5, 5, 0, 1]           5

地形示意（第二個方塊落下後，每個字元寬 0.5；= 是方塊 1，# 是方塊 2，. 是空隙）：
 5    ######
 4    ######
 3    ######
 2  ====....    ← [3,5) 底下是空隙，但方塊 2 的頂部是平的
 1  ====....
    +-+-+-+-+-> x
    1 2 3 4 5
```

第二個方塊在基本段 s1 碰到第一個方塊的頂部（高 2），雖然它的右半邊 s2 下面是空的，整個方塊仍停在高度 2，頂部 5，所以 s1、s2 都被**覆蓋**成 5，而不是各自加 3（若用加法，s2 會變成 3，地形就錯了）。

### 解法

```python
import random
from bisect import bisect_left


def falling_squares(positions: list[list[int]]) -> list[int]:
    xs = sorted({x for l, s in positions for x in (l, l + s)})
    n = len(xs) - 1                                  # 基本段個數
    mx = [0] * (4 * n)
    tag = [None] * (4 * n)

    def apply(k, v):
        mx[k] = v
        tag[k] = v

    def push(k):
        if tag[k] is not None:
            apply(2 * k, tag[k])
            apply(2 * k + 1, tag[k])
            tag[k] = None

    def query(ql, qr, k, l, r):
        if qr < l or r < ql:
            return 0
        if ql <= l and r <= qr:
            return mx[k]
        push(k)
        m = (l + r) // 2
        return max(query(ql, qr, 2 * k, l, m), query(ql, qr, 2 * k + 1, m + 1, r))

    def assign(ql, qr, v, k, l, r):
        if qr < l or r < ql:
            return
        if ql <= l and r <= qr:
            apply(k, v)
            return
        push(k)
        m = (l + r) // 2
        assign(ql, qr, v, 2 * k, l, m)
        assign(ql, qr, v, 2 * k + 1, m + 1, r)
        mx[k] = max(mx[2 * k], mx[2 * k + 1])

    res, best = [], 0
    for left, side in positions:
        lo = bisect_left(xs, left)
        hi = bisect_left(xs, left + side) - 1        # 涵蓋基本段 [lo, hi]
        h = query(lo, hi, 1, 0, n - 1) + side
        assign(lo, hi, h, 1, 0, n - 1)
        best = max(best, h)
        res.append(best)
    return res


def falling_squares_simple(positions: list[list[int]]) -> list[int]:
    """O(n²)：新方塊的底部 = 和它重疊的舊方塊中最高的頂部。"""
    placed, res, best = [], [], 0
    for l, s in positions:
        r = l + s
        base = max((top for pl, pr, top in placed if pl < r and l < pr), default=0)
        placed.append((l, r, base + s))
        best = max(best, base + s)
        res.append(best)
    return res


def brute(positions):
    height = [0] * 60
    res, best = [], 0
    for l, s in positions:
        h = max(height[l:l + s]) + s
        height[l:l + s] = [h] * s
        best = max(best, h)
        res.append(best)
    return res


assert falling_squares([[1, 2], [2, 3], [6, 1]]) == [2, 5, 5]
assert falling_squares([[100, 100], [200, 100]]) == [100, 100]
assert falling_squares([[1, 5], [2, 2], [3, 1]]) == [5, 7, 8]
assert falling_squares([[10**8, 10**6]]) == [10**6]
for _ in range(400):
    pos = [[random.randint(1, 40), random.randint(1, 8)] for _ in range(random.randint(1, 10))]
    assert falling_squares(pos) == falling_squares_simple(pos) == brute(pos)
print("all tests passed")
```

### 複雜度與邊界

segment tree 版本：壓縮 O(n log n)，每個方塊一次查詢、一次覆蓋，O(log n)，總共 O(n log n)；空間 O(n)。O(n²) 版本時間 O(n²)、空間 O(n)。邊界情況：相鄰的方塊（一個的右端等於另一個的左端）在半開區間下不重疊，O(n²) 版本的判斷 `pl < r and l < pr` 是嚴格不等式，segment tree 版本中它們落在不同的基本段；只有一個方塊時 n = 1 個基本段，樹只有根；同一個位置重複丟方塊時，每次查詢都會拿到前一次覆蓋的高度；`hi = bisect_left(xs, left + side) − 1` 一定 ≥ `lo`，因為 side ≥ 1 讓 `left + side` 嚴格大於 `left`。

### Follow-up

> [!question]- F1. 如果還要隨時回答「位置 x 的高度是多少」，或在最後輸出整個地形輪廓呢？
> 單點查詢：用 `bisect_right(xs, x) − 1` 找到 x 所在的基本段（x 不在任何端點範圍內時高度是 0），再做一次單點的 `query(i, i)`，O(log n)。若查詢的 x 不在事先收集的座標裡，壓縮版本仍可回答，因為基本段內高度相同。整個輪廓：遞迴走訪整棵樹並 push 所有標記，得到每個基本段的高度，再把相鄰且高度相同的段合併，O(n)；這就是第 9 章難題 1（218 Skyline）的輸出格式，差別是 218 的建築物不會「堆疊」，而是取最大值。

> [!question]- F2. 如果方塊數到 10⁵，而且是即時一個一個給的，無法先壓縮座標呢？
> 改用動態開點 segment tree，範圍 `[1, 10⁸ + 10⁶)`。覆蓋操作有一個很好用的性質：整段被覆蓋後，子樹原本的細節全部失效，所以可以直接把該節點的孩子丟掉（設為「沒有孩子」），「沒有孩子的節點代表整段高度相同」這個不變式自然成立，連 tag 都不需要；需要往下走時才用自己的值建立兩個孩子。每次操作 O(log C)，C ≈ 10⁸，約 27 層。難題 4（715）的解法中有完整的程式，只要把「是否全部涵蓋」換成「最大高度」即可。

> [!question]- F3. 如果「邊緣相鄰也算支撐」，也就是 [100, 200) 與 [200, 300) 會疊在一起呢？
> 這等於把方塊看成閉區間 `[left, left + side]`。最簡單的做法是座標加倍：把每個點 x 映射到 2x，方塊變成半開區間 `[2·left, 2·(left + side) + 1)`，原本只在一點相接的兩個方塊，現在在 `[2·200, 2·200 + 1)` 這段長度 1 的區間重疊，於是會互相支撐；其餘邏輯完全不變。O(n²) 版本則只要把重疊條件改成 `pl <= r and l <= pr`。這個「加倍座標把閉區間變半開」的技巧，在端點語意不同的題目中非常好用。

> [!question]- F4. 如果要支援「撤銷最後丟下的方塊」呢？
> O(n²) 版本天然支援：`placed` 是一個 stack，撤銷就是 pop，全域最高點也用 stack 記錄每一步的值，pop 即可，O(1)。segment tree 版本的覆蓋操作會抹掉舊資訊，無法直接反向；做法一是在每次覆蓋前，先記錄被覆蓋的那 O(log n) 個節點的舊值與舊標記（所有被修改的節點），撤銷時依相反順序寫回，每次 O(log n)；做法二是 persistent segment tree，每個版本保存一個根，撤銷就是切回上一個根。面試中說出「記錄被修改節點的舊值」這個 rollback 技巧就足夠，它和第 17 章 Union-Find 的可撤銷版本是同一種思路。

> [!question]- F5. 如果方塊換成寬 w、高 h 的長方形，或是落下後會往較低的一側滑落呢？
> 長方形只要把新高度改成 `base + h`，區間仍是 `[left, left + w)`，演算法完全不變。會滑落的版本則改變了問題的本質：方塊停住的位置取決於底下地形的形狀（例如支撐點只在一側時要往另一側滑），落點不再是固定的區間，而是要在地形上模擬；這時 segment tree 可以用來快速找「從某個位置往右第一個高度 ≥ h 的點」（在樹上二分，節點存最大值），每次滑動 O(log n)，但總滑動次數取決於規則，要和面試官確認。面試中說明「固定落點時是區間覆蓋，落點可變時要先找落點」即可。

### 心得

關鍵突破是把一堆方塊看成「x 軸上的高度陣列」，每次落下是「區間最大值查詢＋區間覆蓋」，並看出修改是覆蓋而不是加法，因為方塊頂部是平的。它和核心題 3、4（729、731）同屬時間軸上的區間操作，但修改從「加 1」換成「設成 x」，讓 lazy 的 tag 需要 `None` 來表示「沒有欠條」；和難題 4（715）一樣，覆蓋型的修改都能在動態開點中直接丟棄子樹。面試時先說 O(n²) 的「和重疊方塊比較」並寫出來（n ≤ 1000 時這已是合格的答案），再說明 n 變大時如何用座標壓縮加 lazy segment tree 升級，並強調半開區間的基本段讓相鄰方塊自然不重疊。

## 難題 4｜715. Range Module｜Hard

### 題目

設計一個資料結構 `RangeModule`，追蹤實數線上「被涵蓋」的部分，一開始什麼都沒有。支援三種操作，區間都是半開的 `[left, right)`：`addRange(left, right)` 把區間內所有實數設為被追蹤（和已追蹤的部分合併）；`removeRange(left, right)` 把區間內所有實數設為不再追蹤；`queryRange(left, right)` 回傳區間內**每一個**實數是否都正在被追蹤。限制：`1 <= left < right <= 10⁹`，三種操作合計最多 `10⁴` 次。

- 範例 1：`addRange(10, 20)`、`removeRange(14, 16)` 後，追蹤的是 `[10, 14)` 與 `[16, 20)`。`queryRange(10, 14)` → `True`；`queryRange(13, 15)` → `False`（14 到 15 沒被追蹤）；`queryRange(16, 17)` → `True`。
- 範例 2：`addRange(10, 20)`、`addRange(20, 30)` 後，`queryRange(15, 25)` → `True`，因為兩段相鄰，合起來是 `[10, 30)`。
- 範例 3（邊界）：空結構上 `queryRange(1, 2)` → `False`；`removeRange(5, 8)` 在空結構上不做任何事。

### 提示

> [!tip]- 提示 1
> 被追蹤的部分永遠可以表示成一串**不相交、依序排列**的區間。每次操作只會影響和 `[left, right)` 有交集或相鄰的那幾段。

> [!tip]- 提示 2
> 把所有區間的端點攤平成一個排序陣列 `B = [a0, b0, a1, b1, …]`。某個點 x 是否被追蹤，只要看「B 中 ≤ x 的端點個數」是奇數還是偶數。

> [!tip]- 提示 3
> `addRange`：用 `bisect_left(B, left)` 與 `bisect_right(B, right)` 找到受影響的端點範圍 `[i, j)`，整段刪掉，再依 i、j 的奇偶決定要不要補上 left、right。`removeRange` 的奇偶判斷相反。另一條路是動態開點 segment tree：區間覆蓋成 1 或 0，查詢區間最小值是否為 1。

### 詳解

**直覺做法的困難**。最直覺的是維護一個區間清單，每次 `addRange` 時找出所有和新區間重疊或相鄰的區間、合併成一個；`removeRange` 時找出所有重疊的區間，把它們切成最多左右兩段殘餘；`queryRange` 時檢查是否有某一段完整包住查詢區間。這完全正確，但要處理很多情況：新區間在所有區間左邊、右邊、中間、跨過多段、只和一段的邊緣相鄰……在面試中寫錯邊界的機率很高。座標到 10⁹ 也讓陣列版的 segment tree 無法直接使用。

**突破點一：端點攤平成一個陣列，用奇偶判斷內外**。把不相交區間 `[a0, b0), [a1, b1), …` 的端點依序放進一個排序陣列 B。對任意點 x，令 `c = bisect_right(B, x)`（B 中 ≤ x 的端點數）：c 是奇數代表 x 落在某個 `[a_k, b_k)` 內，偶數代表在外面。半開區間的語意剛好吻合：x = a_k 時 a_k 被算進去，c 是奇數（在內）；x = b_k 時 b_k 也被算進去，c 是偶數（在外）。有了這個表示法，三個操作都變成「找到受影響的端點範圍、整段替換」：

- `addRange(l, r)`：`i = bisect_left(B, l)`、`j = bisect_right(B, r)`。`B[i:j]` 是所有落在 `[l, r]` 內的端點，加入後它們都會消失（變成內部）。新的邊界只有兩個可能：若 i 是偶數，l 原本在外面，l 會成為新區間的左端點，要補上；若 i 是奇數，l 原本就在某個區間內，那個區間的左端點保留，不補。同理，j 是偶數時 r 在外面，要補上 r 作為右端點。所以 `B[i:j] = [l]（若 i 偶）+ [r]（若 j 偶）`。用 `bisect_left` 找 i、`bisect_right` 找 j，讓剛好等於 l 或 r 的端點也被吃掉，這正是「相鄰區間會合併」的來源。
- `removeRange(l, r)`：同樣的 i、j，但奇偶判斷相反：i 是奇數時 l 落在某個區間內，那個區間要在 l 處結束，補上 l；j 是奇數時 r 落在某個區間內，那個區間要從 r 處重新開始，補上 r。
- `queryRange(l, r)`：`i = bisect_right(B, l)`、`j = bisect_left(B, r)`。`[l, r)` 完全被涵蓋，若且唯若 l 在內（i 為奇數）而且 `(l, r)` 之間沒有任何端點（i == j）。

**突破點二：segment tree 的覆蓋版本**。把每個點的狀態看成 0／1，`addRange` 是區間覆蓋成 1、`removeRange` 是覆蓋成 0、`queryRange` 是「區間最小值是否為 1」。座標到 10⁹ 且操作是線上的，所以用動態開點。覆蓋型的修改有一個特別好的性質（難題 3 的 F2 提過）：整段被覆蓋後，子樹的細節全部失效，可以直接把孩子丟掉，「沒有孩子的節點代表整段狀態相同」這個不變式就自然成立，完全不需要 tag。

```text
端點攤平法：B 中 ≤ x 的端點數為奇數 ⇔ x 被追蹤

addRange(10, 20)：B = []，i = 0（偶，補 10），j = 0（偶，補 20）
  B[0:0] = [10, 20]                         → B = [10, 20]
removeRange(14, 16)：i = bisect_left(B,14) = 1（奇，補 14）
                     j = bisect_right(B,16) = 1（奇，補 16）
  B[1:1] = [14, 16]                         → B = [10, 14, 16, 20]
queryRange(10, 14)：i = bisect_right(B,10) = 1，j = bisect_left(B,14) = 1
  i == j 且 i 奇 → True
queryRange(13, 15)：i = bisect_right(B,13) = 1，j = bisect_left(B,15) = 2
  i != j（中間有端點 14）→ False
addRange(12, 18)：i = bisect_left(B,12) = 1（奇，不補）
                  j = bisect_right(B,18) = 3（奇，不補）
  B[1:3] = []                               → B = [10, 20]（洞被填回）
addRange(20, 30)：i = bisect_left(B,20) = 1（奇，不補），j = bisect_right(B,30) = 2（偶，補 30）
  B[1:2] = [30]                             → B = [10, 30]（相鄰合併）

數線示意（removeRange(14, 16) 之後）：
  10        14    16        20
  [==========)     [=========)
  B 中 ≤ x 的個數：x∈[10,14) → 1（奇，在內）；x∈[14,16) → 2（偶，在外）
```

`addRange(20, 30)` 展示了為什麼 i 要用 `bisect_left`：端點 20 剛好等於 l，`bisect_left` 讓它落在 `B[i:j]` 裡被刪掉，於是 `[10, 20)` 和 `[20, 30)` 合併成 `[10, 30)`；若用 `bisect_right`，20 會被保留，B 會變成 `[10, 20, 20, 30]`，雖然奇偶判斷仍然正確，但會留下長度為 0 的空洞端點，之後的查詢 `queryRange(15, 25)` 會因為「中間有端點」而錯誤地回傳 False。

### 解法

```python
import random
from bisect import bisect_left, bisect_right


class RangeModule:
    """端點攤平法：B 是排序的端點陣列，≤ x 的端點數為奇數代表 x 被追蹤。"""

    def __init__(self):
        self.B: list[int] = []

    def addRange(self, left: int, right: int) -> None:
        i, j = bisect_left(self.B, left), bisect_right(self.B, right)
        self.B[i:j] = [left] * (i % 2 == 0) + [right] * (j % 2 == 0)

    def removeRange(self, left: int, right: int) -> None:
        i, j = bisect_left(self.B, left), bisect_right(self.B, right)
        self.B[i:j] = [left] * (i % 2 == 1) + [right] * (j % 2 == 1)

    def queryRange(self, left: int, right: int) -> bool:
        i, j = bisect_right(self.B, left), bisect_left(self.B, right)
        return i == j and i % 2 == 1


class RangeModuleSeg:
    """動態開點 segment tree：val[k] = 1 代表節點整段都被追蹤；沒有孩子 = 整段狀態相同。"""

    def __init__(self, lo: int = 0, hi: int = 10**9 + 1):
        self.lo, self.hi = lo, hi
        self.left, self.right, self.val = [0], [0], [0]

    def _split(self, k: int) -> None:
        if self.left[k] == 0:                       # 用自己的狀態建立兩個孩子
            for _ in range(2):
                self.left.append(0)
                self.right.append(0)
                self.val.append(self.val[k])
            self.left[k], self.right[k] = len(self.val) - 2, len(self.val) - 1

    def _assign(self, l, r, v, k, nl, nr):
        if r <= nl or nr <= l:
            return
        if l <= nl and nr <= r:
            self.val[k] = v
            self.left[k] = self.right[k] = 0        # 整段覆蓋：丟掉子樹
            return
        self._split(k)
        mid = (nl + nr) // 2
        self._assign(l, r, v, self.left[k], nl, mid)
        self._assign(l, r, v, self.right[k], mid, nr)
        self.val[k] = min(self.val[self.left[k]], self.val[self.right[k]])

    def _all(self, l, r, k, nl, nr) -> bool:
        if r <= nl or nr <= l:
            return True
        if self.left[k] == 0 or (l <= nl and nr <= r):
            return self.val[k] == 1
        mid = (nl + nr) // 2
        return (self._all(l, r, self.left[k], nl, mid)
                and self._all(l, r, self.right[k], mid, nr))

    def addRange(self, left: int, right: int) -> None:
        self._assign(left, right, 1, 0, self.lo, self.hi)

    def removeRange(self, left: int, right: int) -> None:
        self._assign(left, right, 0, 0, self.lo, self.hi)

    def queryRange(self, left: int, right: int) -> bool:
        return self._all(left, right, 0, self.lo, self.hi)


for cls in (RangeModule, RangeModuleSeg):
    rm = cls()
    rm.addRange(10, 20)
    rm.removeRange(14, 16)
    assert [rm.queryRange(10, 14), rm.queryRange(13, 15), rm.queryRange(16, 17)] == [True, False, True]
    rm = cls()
    rm.addRange(10, 20)
    rm.addRange(20, 30)
    assert rm.queryRange(15, 25) is True
    rm = cls()
    assert rm.queryRange(1, 2) is False
    rm.removeRange(5, 8)
    assert rm.queryRange(5, 8) is False
    rm.addRange(1, 10**9)
    assert rm.queryRange(1, 10**9) is True
for _ in range(300):
    C = 30
    a, b, cover = RangeModule(), RangeModuleSeg(0, C), [False] * C
    for _ in range(25):
        l = random.randrange(C)
        r = random.randint(l + 1, C)
        op = random.randrange(3)
        if op == 0:
            a.addRange(l, r)
            b.addRange(l, r)
            cover[l:r] = [True] * (r - l)
        elif op == 1:
            a.removeRange(l, r)
            b.removeRange(l, r)
            cover[l:r] = [False] * (r - l)
        else:
            assert a.queryRange(l, r) == b.queryRange(l, r) == all(cover[l:r])
    expect = []                                     # B 必須是正規形式：沒有長度 0 的區間
    for x in range(C):
        if cover[x] and (x == 0 or not cover[x - 1]):
            expect.append(x)
        if cover[x] and (x == C - 1 or not cover[x + 1]):
            expect.append(x + 1)
    assert a.B == expect
print("all tests passed")
```

### 複雜度與邊界

端點攤平法：每次操作兩次 `bisect` 是 O(log n)，切片賦值要搬移元素，最壞 O(n)，n 是目前的區間數。攤還來看，每次 `addRange` 最多新增 2 個端點、刪除的端點總數不超過新增的總數，所以「被刪除」的部分攤還 O(1)；搬移是 memmove，常數極小。在 Java 中用 `TreeMap` 可以做到攤還 O(log n)。空間 O(n)。segment tree 版本每次 O(log C)，C = 10⁹ 約 30 層；因為整段覆蓋時會丟棄子樹，節點數一直維持在 O(q log C) 以內。邊界情況：`removeRange` 的範圍完全在外面時 i == j 且都是偶數，切片 `B[i:i] = []` 不做任何事；`addRange` 和既有區間只在端點相接時會合併；查詢的 l 剛好是某個區間的右端點時（例如 `queryRange(20, 25)`，B = [10, 20]），`bisect_right(B, 20) = 2` 是偶數，正確回傳 False。

### Follow-up

> [!question]- F1. 如果還要隨時回答「目前被追蹤的總長度」呢？
> 端點攤平法：維護一個變數 `total`。`addRange` 時，在切片替換之前先算出 `[l, r)` 內原本被追蹤的長度（走過 `B[i:j]` 與兩端的奇偶，O(j − i)），total 加上 `(r − l) − 原本已追蹤的長度`；`removeRange` 時減去原本已追蹤的長度。因為 j − i 的總和是攤還 O(1)，查詢 O(1)。segment tree 版本：每個節點改存「被追蹤的長度」，覆蓋成 1 時是節點長度、覆蓋成 0 時是 0，pull 時相加，根節點的值就是總長度，O(1) 查詢、O(log C) 修改。

> [!question]- F2. 如果新增 toggleRange(left, right)，把區間內追蹤與不追蹤的狀態互換呢？
> 端點攤平法有一個漂亮的性質：x 的狀態只取決於「≤ x 的端點數」的奇偶，翻轉 `[l, r)` 等於讓 `[l, r)` 內每個點的計數加 1、`r` 以後的點加 2（奇偶不變），也就是**把 l 和 r 各自「切換」是否在 B 中**：在就刪除、不在就插入。兩次 `bisect` 加上插入或刪除，O(log n) 找位置、O(n) 搬移。segment tree 版本要加一個 flip 的 lazy 標記：節點存被追蹤長度 c，翻轉後變成 `節點長度 − c`，flip 標記用 XOR 合成；和覆蓋同時存在時，新的覆蓋要清除 flip 標記，新的 flip 若遇到覆蓋標記則把覆蓋值取反。

> [!question]- F3. 如果要查詢「x 以後第一個沒有被追蹤的點」呢？
> 端點攤平法 O(log n)：`i = bisect_right(B, x)`，若 i 是偶數，x 本身就沒有被追蹤，答案是 x；若 i 是奇數，x 落在 `[B[i−1], B[i])` 內，第一個沒被追蹤的點就是這段的右端點 `B[i]`（半開區間，B[i] 本身不被追蹤）。「x 以後第一個被追蹤的點」對稱：i 為奇數時是 x，偶數時是 `B[i]`（若存在）。segment tree 也能在樹上二分做到 O(log C)，但端點攤平法簡單得多，這是它在面試中的另一個優勢。

> [!question]- F4. 如果座標是整數，區間改成閉區間 [left, right] 呢？
> 在整數上，閉區間 `[l, r]` 等價於半開區間 `[l, r + 1)`，所以三個操作都在入口把 right 加 1，內部完全不變。要小心的是「相鄰合併」的語意隨之改變：閉區間 `[1, 3]` 與 `[4, 6]` 在整數上是相鄰的（沒有縫隙），轉換後是 `[1, 4)` 與 `[4, 7)`，端點攤平法會自動合併成 `[1, 7)`，這正是整數語意下正確的結果；若誤用實數語意，就不該合併。面試時先問清楚座標是整數還是實數，是這題最好的開場問題。

> [!question]- F5. 如果操作次數到 10⁵，而且 removeRange 常常把一大段切成很多小洞，最壞情況會怎樣？
> 端點攤平法的 `bisect` 仍是 O(log n)，但切片賦值在 B 很長時要搬移 O(n) 個元素；最壞情況下（例如交替地在左端附近 add 和 remove），每次都搬移整個陣列，總共 O(q²) 次元素搬移，10⁵ 時約 10¹⁰，即使是 memmove 也偏慢。改用 segment tree 版本可以保證每次 O(log C)；若想保留區間清單的簡潔，則用平衡 BST（Java 的 `TreeMap`、C++ 的 `std::map`）以左端點為鍵存區間，每次操作攤還 O(log n)。Python 標準函式庫沒有平衡 BST，所以在 Python 中，最壞情況要求嚴格時應選 segment tree。

### 心得

關鍵突破是看出「不相交區間的集合」可以用一個排序的端點陣列表示，而「點是否被涵蓋」只看 ≤ x 的端點數的奇偶，於是三個操作都變成「bisect 找範圍、整段替換、依奇偶補端點」。它和核心題 3（729）共享「排序的不相交區間」這個結構，和難題 3（699）共享「覆蓋型修改可以丟棄子樹」這個 segment tree 技巧。面試時兩種解法都值得說：端點攤平法程式只有十行，適合寫在白板上，但必須能解釋 `bisect_left`／`bisect_right` 的選擇與奇偶的意義；segment tree 則是最壞情況有保證的版本，也是 F1、F2 這類追問最容易擴充的形式。

## 難題 5｜2407. Longest Increasing Subsequence II｜Hard

### 題目

給一個整數陣列 `nums` 和整數 `k`，找出最長的子序列（保持原順序、不必連續），使得它**嚴格遞增**，而且相鄰兩個元素的差**不超過 k**。回傳這個長度。限制：`1 <= len(nums) <= 10⁵`，`1 <= nums[i], k <= 10⁵`。

- 範例 1：`nums = [4, 2, 1, 4, 3, 4, 5, 8, 15]`、`k = 3`，回傳 `5`，例如 `[1, 3, 4, 5, 8]`，相鄰差為 2、1、1、3。`[1, 3, 4, 5, 8, 15]` 不合法，因為 15 − 8 = 7 > 3。
- 範例 2：`nums = [7, 4, 5, 1, 8, 12, 4, 7]`、`k = 5`，回傳 `4`，例如 `[4, 5, 8, 12]`。
- 範例 3（邊界）：`nums = [1, 5]`、`k = 1`，回傳 `1`，因為 5 − 1 > 1，只能各自單獨成一個子序列。
- 範例 4（邊界）：`nums = [3, 3, 3]`、`k = 10`，回傳 `1`，嚴格遞增不允許相等。

### 提示

> [!tip]- 提示 1
> 先寫 O(n²) 的 DP：`dp[i]` = 以 `nums[i]` 結尾的最長合法子序列長度，`dp[i] = 1 + max{dp[j] : j < i, nums[i] − k <= nums[j] < nums[i]}`。瓶頸在哪裡？

> [!tip]- 提示 2
> 轉移條件只和 `nums[j]` 的**值**有關，而且是一段連續的值域 `[v − k, v − 1]`。如果用值當索引，記錄「目前為止以值 u 結尾的最長長度」`best[u]`，轉移就變成一次區間最大值查詢。

> [!tip]- 提示 3
> 從左往右掃，對每個 v：`cur = 1 + max(best[v−k .. v−1])`，再把 `best[v]` 更新成 `max(best[v], cur)`。單點更新、區間最大值，用迭代 segment tree，O(n log V)。第 21 章核心題 3（300）的 patience sorting 在這裡行不通。

### 詳解

**為什麼直覺做法不行**。O(n²) 的 DP 在 n = 10⁵ 時是 5 × 10⁹ 次轉移，太慢。第 21 章核心題 3（300 LIS）的 O(n log n) 解法維護 `tails[L]` = 長度 L 的遞增子序列最小的結尾值，靠的是「結尾越小越好」這個貪婪性質：任何能接在大結尾後面的數，都能接在小結尾後面。但這題多了「差不超過 k」的限制，小的結尾反而可能接不上：例如 `[2, 3, 4]` 與 `[6, 7, 8]` 都是長度 3，`tails[3]` 只會留下較小的結尾 4，但 4 接不上 10（差 6 > k = 3），結尾是 8 的卻可以。所以「只保留每個長度的最小結尾」會丟失必要的資訊，patience sorting 不再正確。

**突破點：把 DP 的索引從「位置」換成「值」**。轉移需要的是「所有在 i 之前、值落在 `[v − k, v − 1]` 的 j 中，dp 的最大值」。「在 i 之前」交給掃描順序：從左往右處理，處理 i 時只有 j < i 的結果被寫入過。「值落在一段範圍」交給 segment tree：以值為索引，`best[u]` 記錄目前為止以值 u 結尾的最長長度。於是每一步是一次區間最大值查詢 `max(best[v − k .. v − 1])` 和一次單點更新 `best[v] = max(best[v], cur)`，各 O(log V)，V = max(nums) ≤ 10⁵，不需要座標壓縮。

**為什麼是 segment tree 不是 BIT**。查詢範圍 `[v − k, v − 1]` 是一般區間，不是前綴；最大值又不能相減，所以 BIT 的 `prefix(r) − prefix(l − 1)` 技巧不成立。26.7 節提到 BIT 可以做「前綴最大值」，那只適用於範圍從 1 開始的查詢；這題若沒有 k 的限制（就是普通 LIS），BIT 前綴最大值確實可行，但加上 k 之後必須用 segment tree。

**正確性**。不變式是：處理 i 之前，`best[u]` 等於所有 j < i 且 `nums[j] = u` 的 `dp[j]` 中的最大值（沒有則為 0）。因此查詢得到的就是 DP 轉移式要的最大值，`cur = dp[i]`。嚴格遞增由查詢範圍的右端 `v − 1` 保證：值等於 v 的舊元素不會被當作前一個元素。更新用 `max` 而不是直接覆寫，因為同一個值稍早可能已經有更長的子序列。

```text
nums = [4, 2, 1, 4, 3, 4, 5, 8, 15]，k = 3
best[u] 以值為索引，只列出有變化的值；查詢範圍 [v-3, v-1]（小於 1 的部分截掉）

i  v   查詢範圍   範圍內的 best           max  cur   更新後的 best
0  4   [1, 3]     全 0                     0    1    best[4]=1
1  2   [1, 1]     best[1]=0                0    1    best[2]=1
2  1   空         —                        0    1    best[1]=1
3  4   [1, 3]     1:1, 2:1, 3:0            1    2    best[4]=2
4  3   [1, 2]     1:1, 2:1                 1    2    best[3]=2
5  4   [1, 3]     1:1, 2:1, 3:2            2    3    best[4]=3
6  5   [2, 4]     2:1, 3:2, 4:3            3    4    best[5]=4
7  8   [5, 7]     5:4, 6:0, 7:0            4    5    best[8]=5
8  15  [12, 14]   全 0                     0    1    best[15]=1

答案 = max(cur) = 5，對應 1 → 3 → 4 → 5 → 8
```

第 7 步 v = 8 時，查詢範圍是 `[5, 7]`，只有 `best[5] = 4` 有值，所以 8 接在長度 4 的 `[1, 3, 4, 5]` 後面；值 4 的 `best[4] = 3` 不在範圍內（8 − 4 = 4 > k），即使它對應的子序列也很長。最後 v = 15 的範圍 `[12, 14]` 全空，只能自己開始。若用 patience sorting，處理 15 時會把它接在長度 5 的子序列後面，得到錯誤的 6。

### 解法

```python
import random


def length_of_lis(nums: list[int], k: int) -> int:
    size = max(nums) + 1                     # 值域 0..max，直接以值為索引
    t = [0] * (2 * size)                     # 迭代 segment tree，存區間最大值

    def query(l: int, r: int) -> int:        # max(best[l .. r-1])，半開區間
        res = 0
        l += size
        r += size
        while l < r:
            if l & 1:
                res = max(res, t[l])
                l += 1
            if r & 1:
                r -= 1
                res = max(res, t[r])
            l //= 2
            r //= 2
        return res

    def update(i: int, val: int) -> None:    # best[i] = max(best[i], val)
        i += size
        if t[i] >= val:
            return
        t[i] = val
        while i > 1:
            i //= 2
            t[i] = max(t[2 * i], t[2 * i + 1])

    ans = 0
    for v in nums:
        cur = 1 + query(max(0, v - k), v)    # 值域 [v-k, v-1]
        update(v, cur)
        ans = max(ans, cur)
    return ans


def brute(nums, k):
    dp = [1] * len(nums)
    for i in range(len(nums)):
        for j in range(i):
            if 0 < nums[i] - nums[j] <= k:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)


assert length_of_lis([4, 2, 1, 4, 3, 4, 5, 8, 15], 3) == 5
assert length_of_lis([7, 4, 5, 1, 8, 12, 4, 7], 5) == 4
assert length_of_lis([1, 5], 1) == 1
assert length_of_lis([3, 3, 3], 10) == 1
assert length_of_lis(list(range(1, 10**5 + 1)), 1) == 10**5   # 最大規模
for _ in range(500):
    arr = [random.randint(1, 15) for _ in range(random.randint(1, 12))]
    kk = random.randint(1, 6)
    assert length_of_lis(arr, kk) == brute(arr, kk)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n log V)，V = max(nums) ≤ 10⁵：每個元素一次區間最大值查詢、一次單點更新。空間 O(V)。若 V 遠大於 n，改用座標壓縮（F1），時間 O(n log n)、空間 O(n)。邊界情況：`v − k` 可能小於 1，用 `max(0, v − k)` 截掉，索引 0 永遠是 0，不影響最大值；相等的值不會互相接上，因為查詢的右端是 v（半開，不含 v）；更新時若新值不比舊值大就提前返回，避免無謂的往上更新；n = 1 時答案為 1；`k >= max(nums)` 時退化成普通的嚴格遞增 LIS，結果和第 21 章核心題 3 相同。

### Follow-up

> [!question]- F1. 如果 nums[i] 和 k 都可以到 10⁹ 呢？
> 值域太大不能直接開陣列，改用座標壓縮：`xs = sorted(set(nums))`，值 v 的位置是 `bisect_left(xs, v)`。查詢範圍 `[v − k, v − 1]` 對應的壓縮區間是 `[bisect_left(xs, v − k), bisect_left(xs, v))`（半開），門檻 `v − k` 不需要在 xs 中，這正是 26.6 節的 `rank_range` 技巧。segment tree 大小變成 O(n)，時間 O(n log n)。若必須線上處理（不能預先收集值），改用動態開點，範圍 `[1, 10⁹]`。

> [!question]- F2. 如果改成非遞減（允許相等）呢？
> 查詢範圍從 `[v − k, v − 1]` 擴大成 `[v − k, v]`，也就是 `query(max(0, v − k), v + 1)`。因為先查詢、再更新，同一個元素不會接在自己後面；稍早出現的相同值則可以被接上，這正是非遞減的語意。其他部分完全不變，O(n log V)。用 `[3, 3, 3]` 測試，答案應從 1 變成 3。

> [!question]- F3. 如果要回傳最長子序列有幾個呢（類似 673. Number of Longest Increasing Subsequence 加上差的限制）？
> 節點改存一對 `(長度, 個數)`，合併規則是：長度不同取較大者；長度相同則個數相加。查詢得到 `(L, c)` 後，若 L = 0 則 `cur = (1, 1)`，否則 `cur = (L + 1, c)`；更新 `best[v]` 時同樣用這個合併規則與舊值合併（相同長度要累加個數，而不是取代）。最後對所有元素的 cur 再合併一次，得到全域的 `(最長長度, 個數)`。時間仍是 O(n log V)。這個「把節點的值換成一個可合併的結構」是 segment tree 比 BIT 更通用的地方。

> [!question]- F4. 如果要輸出一個實際的最長子序列呢？
> segment tree 改存 `(長度, 索引)`，比較時以長度為主。處理 i 時，查詢得到的 `(L, j)` 中的 j 就是 i 的前一個元素，記錄 `parent[i] = j`（L = 0 時為 −1）；更新 `best[nums[i]]` 時存 `(cur, i)`。最後從 cur 最大的 i 沿著 parent 往回走，再反轉。時間 O(n log V)，額外空間 O(n)。注意同一個值被更新時，要保留長度較大的那一個索引，否則 parent 鏈可能指向較短的子序列。

> [!question]- F5. 如果限制改成「相鄰兩個元素的索引差不超過 d」，值仍要嚴格遞增呢？
> 現在轉移是 `dp[i] = 1 + max{dp[j] : i − d <= j < i, nums[j] < nums[i]}`，有兩個條件：索引在一個窗口內、值比較小。技巧是**換掉負責掃描的維度**：依值由小到大處理元素，讓「值比較小」由處理順序保證；segment tree 改以**索引**為座標，查詢 `[i − d, i − 1]` 的最大 dp。值相等的元素不能互相接上，所以排序鍵用 `(值, −索引)`：相同值中索引大的先處理，它寫入的位置在 i 右邊，不會落在 `[i − d, i − 1]`；索引小的還沒處理，也不會被查到。時間 O(n log n)。這說明了計數型與 DP 型的 range query 共同的設計問題：哪個維度交給排序、哪個維度交給樹。

### 心得

關鍵突破是把 DP 轉移中的「值在一段範圍內」交給以值為索引的 segment tree，把「位置在前面」交給掃描順序，O(n²) 的 DP 於是降成 O(n log V)。它和本章的計數題（315、1395、327、493）是同一個框架，只是樹上存的從「計數」變成「DP 的最大值」，所以必須從 BIT 換成 segment tree。面試時建議先寫 O(n²) DP，再說明為什麼 300 題的 patience sorting 在有 k 限制時失效（舉出「小結尾接不上大數」的反例），然後提出「以值為索引的區間最大值」。能清楚說出「範圍不是前綴、最大值不能相減，所以不用 BIT」，就展現了對兩種結構差異的真正理解。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 單點修改＋區間和 | 陣列會變、要區間和，修改與查詢交錯 | BIT；賦值時用 delta；二維用二維 BIT | 核心題 1（307）、308 Range Sum Query 2D - Mutable |
| 單點修改＋區間最值 | 和上面相同，但問最大／最小值 | 迭代 segment tree，op 換成 max／min | 難題 5（2407）的零件、2286 Booking Concert Tickets |
| 計數型：掃描＋值域 BIT | 「右邊／左邊有幾個比我小（大）」 | 一個維度交給掃描順序、值交給 BIT；座標壓縮 | 核心題 2（315）、核心題 5（1395）、1649 Create Sorted Array through Instructions、2179 Count Good Triplets in an Array |
| 範圍計數：門檻不在集合裡 | 條件是 `P[b] − P[a] ∈ [lo, hi]` 或 `a > 2b` | 只壓縮插入值，查詢門檻用 `bisect` 換算 rank；或 merge sort 先計數再合併 | 難題 1（327）、難題 2（493）、2426 Number of Pairs Satisfying Inequality |
| 時間軸上的區間加＋最大值 | 預訂、會議、重疊層數；座標到 10⁹ | 動態開點 segment tree（半開區間）；n 小時用清單或 sweep line | 核心題 3（729）、核心題 4（731）、732 My Calendar III |
| 區間覆蓋＋區間最值 | 「整段變成同一個值」，例如方塊落下 | lazy 的 tag 用 `None`；座標壓縮成半開基本段；覆蓋可丟棄子樹 | 難題 3（699） |
| 不相交區間集合 | 區間的加入、刪除、查詢是否完整涵蓋 | 排序端點陣列＋奇偶判斷；或覆蓋型 segment tree | 難題 4（715）、第 9 章難題 4（352）、57 Insert Interval |
| 區間加＋區間和 | 整段加值，又要區間和 | 兩棵 BIT 或 lazy segment tree | 370 Range Addition（離線時用差分即可） |
| DP 轉移加速 | `dp[i]` 依賴「值在某範圍內」的 dp 最大值或總和 | 以值為索引的 segment tree（最大值）或 BIT（總和、前綴最大值） | 難題 5（2407）、300 LIS（第 21 章核心題 3）、673、1626 Best Team With No Conflicts |
| 第 k 小的已插入元素 | 動態集合中找第 k 小、中位數 | BIT 上二分（`lower_bound`），O(log n) | 480 Sliding Window Median（第 14 章難題 2）的另一種解法 |
| 離線查詢排序 | 查詢有兩個條件，可以把查詢和資料一起排序 | 依一個維度排序後掃描，另一個維度用 BIT／segment tree | 第 9 章難題 5（1851）、2736 Maximum Sum Queries |
| 覆蓋長度 | 很多矩形的聯集面積 | sweep line＋segment tree 存「被覆蓋的長度」 | 第 9 章難題 3（850） |

**下限與上限**。最簡單的形式是核心題 1（307）：資料結構就是題目本身，只要寫對 BIT 的兩個迴圈。往上一層是計數型題目（315、1395），難點從「寫樹」轉移到「看出這是數對計數，並決定掃描方向與樹的索引」。再往上是三種額外的難度，常常同時出現：第一，**查詢條件需要轉換**，例如 327 先轉成前綴和的數對、493 的門檻不在插入集合裡、2407 要把 DP 的索引從位置換成值；第二，**修改是區間型的**，需要 lazy propagation，而且要判斷修改是加法還是覆蓋（699 若誤用加法就會錯）；第三，**座標無法事先知道或範圍極大**，需要動態開點，或像 715 那樣換成有序端點陣列。上限的題目往往在 n ≤ 1000 時有 O(n²) 的簡單解（729、731、699），真正的考點是「你知道何時要升級、升級到什麼」。

**與其他 pattern 的關係**。和第 7 章 prefix sum／difference array 是同一族：資料不會變時用前綴和，修改全在查詢之前時用差分，兩者交錯時才需要樹；BIT 本身就是「可修改的前綴和」。和 merge sort（第 11 章難題 4 的 148）在計數題上可以互換：merge sort 不需要座標壓縮，但只能離線，也很難加上索引距離之類的額外條件。和第 9 章 sweep line 的關係是：sweep line 負責「沿著一個維度掃描」，segment tree 負責「在另一個維度上維護狀態」，850 題就是兩者的組合。和第 13 章的 BST、第 14 章的 heap 也有重疊：「動態集合中第 k 小」可以用平衡 BST、兩個 heap 或 BIT 上二分，Python 中後兩者比較實際。和第 21 章 DP 的關係在難題 5：當轉移是「在一段範圍內取最值」時，樹把每次轉移從 O(n) 降到 O(log n)。

**容易混淆之處**。第一，**滑動窗口的最大值不需要 segment tree**：如果查詢範圍是「索引上的滑動窗口」而且窗口只往右移，第 6 章難題 2（239）的 monotonic deque 是 O(n)，比 segment tree 的 O(n log n) 更好；2407 之所以需要樹，是因為範圍是在**值**上，而且每次的範圍隨 v 跳動。第二，**BIT 不等於「只能做和」**：它能做任何可相減的運算，也能在值單調變好時做前綴最值，但做不了任意區間的最值。第三，**lazy 的修改必須能合成**：加法與覆蓋可以，開根號、取模這類修改不能直接用 lazy。第四，n ≤ 1000 的區間題（729、731、699）用 O(n²) 就能通過，面試中先寫簡單解，再談升級，比一開始寫樹更穩。

## 本章重點整理

- Range query 的核心是「O(n) 個區段摘要，讓任何區間拼成 O(log n) 塊、任何位置只屬於 O(log n) 塊」，於是修改與查詢都是 O(log n)。
- BIT 的 `t[i]` 負責 `(i − lowbit(i), i]`；查詢一直拿掉最低的 1（`i -= i & -i`），修改一直加上最低的 1（`i += i & -i`）；索引一定從 1 開始。
- BIT 只適用於可相減的運算（和、計數、XOR），或「值只會變好」的前綴最值；任意區間的最大值、最小值要用 segment tree。
- Segment tree 的查詢只有三種情況：不相交、完全包含、部分相交；每層最多碰 4 個節點，所以是 O(log n)。單點修改＋區間查詢用迭代版（2n 陣列、半開區間），有區間修改就用遞迴版（4n 陣列）。
- Lazy propagation 的三個函式：`apply`（修改一個節點的摘要並記下 tag）、`push`（往下走前把 tag 交給孩子）、`pull`（由孩子算回自己）；節點的摘要永遠正確，tag 是欠孩子的。
- 覆蓋型的 tag 用 `None` 表示沒有；覆蓋型修改在動態開點中可以直接丟棄子樹。
- 座標壓縮：`xs = sorted(set(values))`，rank 從 1 開始；查詢門檻不在集合裡時用 `bisect` 換算；區間一律壓成半開的基本段 `[xs[i], xs[i+1])`，避免縫隙消失。
- 座標到 10⁹ 又必須線上處理時，用動態開點 segment tree，每次操作只建立 O(log C) 個節點。
- 計數型題目的設計問題永遠是「哪個維度交給掃描順序、哪個維度交給樹的索引」：315 是索引掃描＋值域 BIT，2407 F5 則反過來是值排序＋索引樹。
- 數對計數題（315、327、493）也能用 merge sort；條件和合併順序不一致時（493），要先計數、再合併。
- 選擇順序：資料不變用 prefix sum → 運算可相減用 BIT → 有區間修改用 lazy → 座標未知用動態開點；n ≤ 1000 的區間題先寫 O(n²) 的簡單解。
- 面試中先講三件事：樹的索引是什麼、節點存什麼、操作是單點還是區間；寫完後用 n = 1、整個範圍、全部相同的值三個案例手動驗證。
