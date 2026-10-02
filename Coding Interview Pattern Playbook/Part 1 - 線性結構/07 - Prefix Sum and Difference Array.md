---
chapter: 7
title: Prefix Sum 與 Difference Array
part: 1
---

# 第 7 章　Prefix Sum 與 Difference Array

> [!abstract] 本章地圖
> **一句話**：任何子陣列都是「兩個前綴相減」，所以子陣列的問題可以改寫成「找一對前綴」的問題；反過來，任何區間修改都可以只改兩個端點，最後用一次前綴和還原。
>
> **辨識訊號**：
> - 大量的區間和查詢，而陣列本身不變（或很少變）
> - 「和為 k 的子陣列有幾個／最長多長」，而且陣列**有負數**，sliding window 失效
> - 「0 和 1 一樣多」「每個母音出現偶數次」這類「兩種計數相等」或「奇偶性」的子陣列條件
> - 大量「把區間 [l, r) 都加上 d」的操作，最後才問結果或最大值
> - 二維矩陣中的子矩形和，或要把二維問題壓成一維
> - 要對「所有子陣列」的某個量求總和，而這個量可以拆成前綴的線性組合
>
> **核心題**：238、560、525、304、1094
>
> **難題**：1074、363、862、1371、2281

## 7.1 這個 Pattern 解決什麼問題

先看一個最小的例子。給一個長度 n 的陣列，接著有 q 次詢問，每次問「索引 l 到 r − 1 的元素和是多少」。最直接的做法是每次把那一段加起來，一次最多 O(n)，總共 O(nq)；n 和 q 都是 10⁵ 時就是 10¹⁰ 次加法，完全不可行。浪費在哪裡？相鄰兩次詢問 `[2, 9)` 和 `[2, 10)` 幾乎是同一段，我們卻從頭重算。

prefix sum（前綴和）的想法是預先算好 `P[i] = nums[0] + … + nums[i − 1]`，也就是「前 i 個元素的和」。因為 `[l, r)` 這一段恰好是「前 r 個」扣掉「前 l 個」，所以區間和等於 `P[r] − P[l]`，每次詢問 O(1)。前處理 O(n)，總共 O(n + q)。這一步本身很簡單，真正有力量的是它帶來的觀點轉換：**每一個子陣列都對應一對前綴 (l, r)**，子陣列的和是兩個數相減。

有了這個觀點，很多原本要枚舉 O(n²) 個子陣列的問題，都變成「對每個 r，在它之前的前綴中找一個符合條件的 l」。條件是「相等」時用 hash map（第 4 章）一次 O(1) 查到，例如「和為 k 的子陣列」就是找 `P[l] = P[r] − k`；條件是「不等式」時，就要用排序結構或 monotonic deque（單調雙端佇列）來維護候選的前綴。本章的核心題 2、3 與難題 1、4 都是「等式 + hash map」，難題 2、3 是「不等式 + 有序結構」。

difference array（差分陣列）是前綴和的反向操作。若要做很多次「把 `[l, r)` 全部加上 d」，每次逐一修改要 O(n)；改成只在 `diff[l] += d`、`diff[r] −= d` 記下「從 l 開始多 d、從 r 開始少 d」，所有修改做完後對 diff 做一次前綴和，就得到每個位置的總增量。修改 O(1)，還原 O(n)。前綴和與差分的關係就像積分與微分：對差分陣列做前綴和會得到原陣列，對前綴和陣列做差分也會得到原陣列。記住這一對互逆的操作，「多次查詢」用前綴和，「多次修改」用差分。

## 7.2 辨識訊號

| 題目特徵 | 為什麼是 prefix sum／difference array | 本章哪一題 |
|---|---|---|
| 陣列不變，大量區間和查詢 | 區間和 = 兩個前綴相減，O(1) 回答 | 7.3 節模板、核心題 4（304） |
| 「除了自己以外」的乘積、和、最大值 | 答案 = 左邊的前綴 ⊕ 右邊的後綴，兩次掃描 | 核心題 1（238） |
| 和為 k 的子陣列個數，陣列有負數 | 有負數時窗口和不單調，sliding window 失效；改成找 `P[l] = P[r] − k` | 核心題 2（560） |
| 「兩種元素一樣多」的最長子陣列 | 把一種當 +1、另一種當 −1，條件變成「和為 0」，也就是兩個前綴相等 | 核心題 3（525） |
| 每個字元出現偶數次、奇偶性條件 | 前綴的奇偶性可以壓成 bitmask，條件變成兩個前綴的 mask 相同 | 難題 4（1371） |
| 大量區間加值，最後問結果或最大值 | 差分只改兩個端點，最後一次前綴和還原 | 核心題 5（1094） |
| 子矩形和等於／不超過某值 | 固定上下兩列，把每一行壓成一個數，變成一維子陣列問題 | 難題 1（1074）、難題 2（363） |
| 「和至少 k 的最短子陣列」，有負數 | 不等式條件，用遞增的 monotonic deque 維護有用的前綴 | 難題 3（862） |
| 對所有子陣列求「最小值 × 和」的總和 | 和可寫成前綴相減，對 l、r 求和就變成前綴和的前綴和 | 難題 5（2281） |

一個實用的反向檢查：如果陣列**全是非負數**而條件是「和 ≥ k」或「和 ≤ k」，窗口和會隨右端點單調增加，第 6 章的 sliding window 用 O(1) 空間就能做到，不需要前綴和；前綴和真正不可取代的情況是**有負數**、**條件是等式**，或**要回答很多次查詢**。

## 7.3 模板與原理：前綴和與差分

本書統一使用**半開區間**：`P` 的長度是 n + 1，`P[i]` 是 `nums[:i]` 的和，`P[0] = 0`；`[l, r)` 的和是 `P[r] − P[l]`。這和 Python 的切片 `nums[l:r]` 完全對應，也讓空子陣列（l = r）自然地得到 0，不需要特判。

```python
from itertools import accumulate


def build_prefix(nums: list[int]) -> list[int]:
    """P[i] = sum(nums[:i])，長度 n + 1。"""
    prefix = [0] * (len(nums) + 1)
    for i, x in enumerate(nums):
        prefix[i + 1] = prefix[i] + x
    return prefix


def range_sum(prefix: list[int], l: int, r: int) -> int:
    """回傳 sum(nums[l:r])，0 <= l <= r <= n。"""
    return prefix[r] - prefix[l]


def apply_range_adds(n: int, updates: list[tuple[int, int, int]]) -> list[int]:
    """每個 (l, r, d) 代表把 [l, r) 全部加上 d；回傳長度 n 的最終增量。"""
    diff = [0] * (n + 1)              # 多一格，讓 r = n 時 diff[r] 不越界
    for l, r, d in updates:
        diff[l] += d                  # 從 l 開始多 d
        diff[r] -= d                  # 從 r 開始把 d 扣回來
    out, running = [], 0
    for i in range(n):
        running += diff[i]            # 對差分做前綴和 = 還原
        out.append(running)
    return out


nums = [2, -1, 3, 0, 5]
P = build_prefix(nums)
assert P == [0, 2, 1, 4, 4, 9]
assert P == list(accumulate(nums, initial=0))          # 標準函式庫的寫法
for l in range(len(nums) + 1):
    for r in range(l, len(nums) + 1):
        assert range_sum(P, l, r) == sum(nums[l:r])     # 包含 l == r 的空區間
assert build_prefix([]) == [0]
assert apply_range_adds(5, [(1, 4, 2), (0, 2, 3), (4, 5, -1)]) == [3, 5, 2, 2, -1]
assert apply_range_adds(3, []) == [0, 0, 0]
assert apply_range_adds(3, [(0, 3, 7)]) == [7, 7, 7]  # r = n，用到多出來的那一格
print("all tests passed")
```

**Invariant（不變式）**。前綴和的不變式是「`prefix[i]` 永遠等於前 i 個元素的和」：`prefix[0] = 0` 是空前綴，每多看一個元素就加上它。差分的不變式是「掃到位置 i 時，`running` 等於所有覆蓋 i 的修改的 d 總和」：一個修改 (l, r, d) 在 `running` 經過 l 時被加進來，經過 r 時被扣掉，所以只有 l ≤ i < r 的位置受到影響。

**每一行為什麼這樣寫**：

- `prefix` 多一格而不是和 nums 一樣長：這樣 `P[r] − P[l]` 對所有 0 ≤ l ≤ r ≤ n 都成立，包含從索引 0 開始的區間（`P[0] = 0`）。若用「`P[i]` = 前 i + 1 個元素的和」的閉區間寫法，從 0 開始的區間就要特判 `l == 0`，這是最常見的差一錯誤來源。
- `diff` 也多一格：修改到陣列尾端（r = n）時，`diff[n] −= d` 不會越界；這一格在還原時不會被讀到，所以不影響結果。
- 題目的區間若是閉區間 `[l, r]`（例如 1109 題的航班編號），就寫 `diff[r + 1] −= d`，並讓 diff 長度至少 n + 1。寫程式前先確認題目的端點語意，比事後除錯容易得多。
- `itertools.accumulate(nums, initial=0)` 是同一件事的標準函式庫寫法；面試時用它沒問題，但手寫迴圈比較容易解釋，也方便順手維護其他資訊（例如核心題 3 的 first occurrence）。

**時間與空間**。前綴和建立 O(n)、每次查詢 O(1)、空間 O(n)。差分每次修改 O(1)、還原 O(n)。兩者的限制也很明確：前綴和假設陣列在查詢期間**不變**，差分假設所有修改**做完之後**才讀取。查詢和修改交錯出現時，兩者都會退化成每次 O(n)，那就是第 26 章 Fenwick tree 與 segment tree 的領域。

## 7.4 前綴和 + Hash Map：把子陣列條件變成前綴的配對

這是本章最重要的模板。目標是「數出（或找出最長的）滿足某條件的子陣列」，做法是從左往右掃，對每個右端點 r 問：「之前出現過的前綴中，有幾個（或最早的是哪一個）能和現在的前綴配成合法的子陣列？」

```python
from collections import Counter


def count_subarrays_with_sum(nums: list[int], k: int) -> int:
    """和恰好為 k 的非空子陣列個數。"""
    seen = Counter({0: 1})       # 空前綴 P[0] = 0 出現過一次
    total = running = 0
    for x in nums:
        running += x             # running = P[r]
        total += seen[running - k]   # 先查：找 P[l] = P[r] - k，l < r
        seen[running] += 1       # 後存：讓之後的 r 可以用到這個前綴
    return total


def longest_subarray_with_sum(nums: list[int], k: int) -> int:
    """和恰好為 k 的最長子陣列長度，不存在則回傳 0。"""
    first = {0: -1}              # 前綴值 -> 最早出現的「結尾索引」，空前綴在 -1
    best = running = 0
    for i, x in enumerate(nums):
        running += x
        if running - k in first:
            best = max(best, i - first[running - k])
        first.setdefault(running, i)  # 只記第一次，越早越長
    return best


assert count_subarrays_with_sum([1, 1, 1], 2) == 2
assert count_subarrays_with_sum([1, -1, 0], 0) == 3       # [1,-1]、[0]、[1,-1,0]
assert count_subarrays_with_sum([], 0) == 0               # 空子陣列不算
assert longest_subarray_with_sum([1, -1, 5, -2, 3], 3) == 4
assert longest_subarray_with_sum([-2, -1, 2, 1], 1) == 2
assert longest_subarray_with_sum([1, 2], 9) == 0
print("all tests passed")
```

**三個細節決定對錯**。第一，`seen` 一開始要有 `{0: 1}`（或 `first = {0: -1}`），代表「空前綴」。少了它，所有從索引 0 開始的子陣列都會漏算，例如 `[1, 1, 1]`、k = 2 時會漏掉 `[1, 1]`（開頭那一段）。第二，**先查再存**：如果先把 `P[r]` 存進去再查 `P[r] − k`，當 k = 0 時會查到自己，等於把空子陣列 `[r, r)` 算進去。第三，「數個數」存出現次數，「找最長」存最早出現的位置，「找最短」存最晚出現的位置；三種題目的 map 存的東西不同，但掃描的骨架一樣。

**為什麼是 O(n)**。每個右端點做一次查詢與一次插入，hash map 的平均成本是 O(1)，所以總共 O(n) 時間、O(n) 空間。和暴力枚舉 O(n²) 個子陣列相比，關鍵在於我們不再枚舉左端點，而是把「所有可能的左端點」壓縮成一張「前綴值 → 次數」的表，查一次就得到所有符合條件的左端點數量。

**改寫條件的技巧**。很多題目表面上不是「和為 k」，但可以換一個「前綴的 key」讓條件變成「兩個 key 相等」或「相差固定值」：

| 子陣列條件 | 前綴的 key | 配對條件 | 例題 |
|---|---|---|---|
| 和為 k | `P[i]` | `P[l] = P[r] − k` | 核心題 2（560） |
| 和可被 k 整除 | `P[i] % k` | 兩個 key 相等 | 974 Subarray Sums Divisible by K |
| 0 與 1 一樣多 | 把 0 當 −1 的 `P[i]` | 兩個 key 相等 | 核心題 3（525） |
| 每個母音出現偶數次 | 五個母音奇偶性的 bitmask | 兩個 mask 相等 | 難題 4（1371） |
| 至多一個字元出現奇數次 | 奇偶性 bitmask | 兩個 mask 相等或只差一個 bit | 1915、1542 |
| 子矩形和為 k | 固定上下列後的行和前綴 | 同 560 | 難題 1（1074） |

相等條件的 key 必須滿足：「子陣列合法」⇔「兩端的 key 符合配對條件」。設計 key 時先在紙上驗證這個等價關係，例如「和可被 k 整除」⇔ `(P[r] − P[l]) % k == 0` ⇔ `P[r] % k == P[l] % k`。Python 的 `%` 對負數也回傳非負的餘數，在 Java／C++ 中則要寫成 `((x % k) + k) % k`。

## 7.5 二維前綴和與二維差分

二維的前綴和定義為 `P[i][j]` = 左上角 `(0, 0)` 到 `(i − 1, j − 1)` 這個矩形的和，大小 `(m + 1) × (n + 1)`。建表與查詢都用 inclusion-exclusion（排容原理）：

```text
建表：P[i+1][j+1] = M[i][j] + P[i][j+1] + P[i+1][j] − P[i][j]

        j    j+1                      上方矩形 P[i][j+1] 與左方矩形 P[i+1][j]
   ┌────┬────┐                        都包含了左上角 P[i][j]，
 i │ 共同│ 上 │                        相加後左上角被算了兩次，要扣掉一次。
   ├────┼────┤
i+1│ 左 │ M  │
   └────┴────┘

查詢 rows [r1, r2)、cols [c1, c2)：
   P[r2][c2] − P[r1][c2] − P[r2][c1] + P[r1][c1]
   （整塊 − 上方 − 左方 + 被扣兩次的左上角）
```

```python
def build_prefix_2d(matrix: list[list[int]]) -> list[list[int]]:
    m, n = len(matrix), len(matrix[0]) if matrix else 0
    P = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m):
        for j in range(n):
            P[i + 1][j + 1] = matrix[i][j] + P[i][j + 1] + P[i + 1][j] - P[i][j]
    return P


def rect_sum(P, r1: int, c1: int, r2: int, c2: int) -> int:
    """rows [r1, r2)、cols [c1, c2) 的和。"""
    return P[r2][c2] - P[r1][c2] - P[r2][c1] + P[r1][c1]


def apply_rect_adds(m: int, n: int, updates) -> list[list[int]]:
    """每個 (r1, c1, r2, c2, d) 把 rows [r1, r2)、cols [c1, c2) 加上 d。"""
    D = [[0] * (n + 1) for _ in range(m + 1)]
    for r1, c1, r2, c2, d in updates:
        D[r1][c1] += d
        D[r1][c2] -= d
        D[r2][c1] -= d
        D[r2][c2] += d          # 被扣了兩次，加回來
    out = [[0] * n for _ in range(m)]
    for i in range(m):
        for j in range(n):       # 對 D 做二維前綴和即還原
            out[i][j] = D[i][j] + (out[i - 1][j] if i else 0) + (out[i][j - 1] if j else 0) \
                - (out[i - 1][j - 1] if i and j else 0)
    return out


M = [[3, 0, 1, 4], [5, 6, 3, 2], [1, 2, 0, 1]]
P = build_prefix_2d(M)
for r1 in range(4):
    for r2 in range(r1, 4):
        for c1 in range(5):
            for c2 in range(c1, 5):
                expect = sum(M[r][c] for r in range(r1, r2) for c in range(c1, c2))
                assert rect_sum(P, r1, c1, r2, c2) == expect
assert rect_sum(P, 1, 1, 3, 3) == 11
assert apply_rect_adds(2, 3, [(0, 0, 2, 2, 1), (1, 1, 2, 3, 5)]) == [[1, 1, 0], [1, 6, 5]]
assert apply_rect_adds(1, 1, []) == [[0]]
print("all tests passed")
```

二維差分是一維差分的直接推廣：一次矩形修改只動四個角，最後做一次二維前綴和還原。符號的規律和查詢的排容完全一樣（左上 +、右上 −、左下 −、右下 +），記住一個就記住兩個。

另一個二維技巧在難題 1、2 會反覆用到：**固定上下兩列，把中間每一行的和壓成一個數**。對每一對 (top, bottom)，令 `col[c]` 為第 c 行在 top 到 bottom 之間的和，所有「上下邊界恰好是 top、bottom」的子矩形，就一一對應到 `col` 的子陣列。枚舉 O(m²) 對列，每對用一維的方法 O(n) 處理，總共 O(m² · n)。這比對子矩形的四個邊界暴力枚舉 O(m² n²) 少了一個 n。

## 7.6 前綴的推廣：運算、不等式與前綴的前綴

**換一種運算**。前綴和能用「相減」取出區間，是因為加法有反元素。只要運算有反元素，同樣的技巧就成立：XOR 的反元素是自己（`X[r] ^ X[l]` 就是區間 XOR），模質數下非零元素的乘法有反元素（模反元素）。沒有反元素的運算（max、min、gcd、含 0 的乘法）就不能「相減」，但仍然可以做「前綴 + 後綴」：核心題 1 的「除了自己以外的乘積」就是左邊前綴積乘右邊後綴積，完全不需要除法。

**條件是不等式時**。「和 ≥ k」「和 ≤ k」這種條件，hash map 查不到，因為合法的左端點不是一個值，而是一個範圍。這時要依照額外的結構選工具：

| 條件 | 陣列元素 | 工具 | 例題 |
|---|---|---|---|
| 和 ≥ k 的最短／和 ≤ k 的最長 | 非負 | sliding window（第 6 章），O(n) | 209 Minimum Size Subarray Sum |
| 和 ≥ k 的最短 | 可負 | 遞增 monotonic deque，O(n) | 難題 3（862） |
| 不超過 k 的最大子陣列和 | 可負 | 排序結構中找最小的 `P[l] ≥ P[r] − k`，O(n log n) | 難題 2（363） |
| 和落在 [lo, hi] 的子陣列個數 | 可負 | merge sort 或 Fenwick tree 計數，O(n log n) | 327 Count of Range Sum（第 26 章難題 1） |

**前綴的前綴**。有些題目要對**所有子陣列**的和再求和，例如難題 5。子陣列 `[l, r)` 的和是 `P[r] − P[l]`，對一整個範圍的 l 與 r 求和，會出現 Σ P[r] 與 Σ P[l]，這兩者又是前綴陣列 `P` 的區間和，所以再建一層 `PP[i] = P[0] + … + P[i − 1]` 就能 O(1) 算出。「前綴和的前綴和」聽起來繞，但本質只是把同一個模板套兩次。

## 7.7 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 前綴陣列和原陣列一樣長（閉區間定義） | 從索引 0 開始的區間要特判，常漏掉或多減一個元素 | 一律用長度 n + 1、`P[0] = 0`、`[l, r)` 的和是 `P[r] − P[l]` |
| hash map 忘了放入空前綴 `{0: 1}` | 從開頭開始的合法子陣列全被漏算 | 初始化時就放入空前綴；找最長時放 `{0: -1}` |
| 先存再查 | k = 0 時把空子陣列算進去，答案偏大 | 對每個 r，先用 `P[r]` 查詢，再把 `P[r]` 存入 |
| 找最長卻覆寫成最新位置 | 長度偏短 | 找最長存「第一次出現」，用 `setdefault`；找最短才存最新位置 |
| 有負數仍用 sliding window | 某些輸入少算或多算，例如 560 的 `[1, -1, 1]` | 先問「元素會不會是負的」；有負數就用前綴和 + hash map 或 deque |
| 差分陣列沒有多一格 | 修改到尾端時 `diff[n]` 越界 | diff 長度至少 n + 1；閉區間題目用 `diff[r + 1]` |
| 區間端點語意搞錯 | 1094 題下車點仍算在車上，容量被多算 | 先確認題目是 `[from, to)` 還是 `[from, to]`，再決定減在 `to` 或 `to + 1` |
| 二維排容的符號錯 | 子矩形和在某些位置錯，邊緣的查詢最容易錯 | 記「整塊 − 上 − 左 + 左上」，並用暴力法對所有子矩形驗證一次 |
| 負數取模 | Java／C++ 中 `P % k` 可能為負，974 題計數錯誤 | Python 的 `%` 天生非負；其他語言寫 `((x % k) + k) % k` |
| 溢位 | 前綴和可達 n × max，超過 32 位元 | Python 不受影響；Java／C++ 用 64 位元整數，取模題每步取模 |

## 核心題 1｜238. Product of Array Except Self｜Medium

### 題目

給一個整數陣列 `nums`，回傳一個同樣長度的陣列 `answer`，其中 `answer[i]` 是 `nums` 中**除了 `nums[i]` 以外**所有元素的乘積。限制：**不能使用除法**，時間必須是 O(n)；進階要求是除了輸出陣列以外只用 O(1) 的額外空間。`2 <= len(nums) <= 10⁵`，`-30 <= nums[i] <= 30`，題目保證任何前綴或後綴的乘積都能放進 32 位元整數。

- 範例 1：`nums = [1, 2, 3, 4]`，回傳 `[24, 12, 8, 6]`。例如 `answer[1] = 1 × 3 × 4 = 12`。
- 範例 2：`nums = [-1, 1, 0, -3, 3]`，回傳 `[0, 0, 9, 0, 0]`。只有 `answer[2]` 不含那個 0，等於 `(-1) × 1 × (-3) × 3 = 9`。
- 範例 3（邊界）：`nums = [0, 0]`，回傳 `[0, 0]`；兩個 0 時每個位置都至少乘到另一個 0。
- 範例 4（邊界）：`nums = [5, 7]`，回傳 `[7, 5]`。

### 思路

暴力解是對每個 i 把其他 n − 1 個數乘起來，O(n²)。最自然的優化是「先算全部的乘積 T，再讓 `answer[i] = T / nums[i]`」，O(n)；但題目禁止除法，而且這個做法遇到 0 會壞掉：只要陣列中有 0，T 就是 0，除以 `nums[i] = 0` 更是未定義。瓶頸在於：我們想從整體「扣掉」一個元素，可是乘法在有 0 時沒有反元素，扣不掉。

關鍵觀察是不要扣，而是**拼**：除了 i 以外的元素，恰好是「i 左邊的全部」加上「i 右邊的全部」。所以 `answer[i] = L[i] × R[i]`，其中 `L[i] = nums[0] × … × nums[i − 1]` 是前綴積（不含 i），`R[i] = nums[i + 1] × … × nums[n − 1]` 是後綴積（不含 i）。L 從左往右一次掃描就能算出（`L[i + 1] = L[i] × nums[i]`），R 從右往左一次掃描算出，兩者都是 O(n)。整個過程只用乘法，0 也不需要特判：0 會自然地讓它右邊所有的 L 和左邊所有的 R 變成 0。

要做到 O(1) 額外空間，就把 L 直接寫進輸出陣列，第二趟從右往左時用一個變數 `right` 累積後綴積，邊走邊乘進去。這裡的 invariant 是：第一趟結束時 `answer[i] = L[i]`；第二趟處理到 i 時，`right` 恰好是 `nums[i + 1:]` 的乘積，所以 `answer[i] *= right` 之後就是最終答案，再把 `nums[i]` 乘進 `right` 留給 i − 1 用。

```text
nums = [1, 2, 3, 4]

第一趟（左 → 右）：answer[i] = 左邊所有數的乘積，left 先寫入再乘上 nums[i]
i      0    1    2    3
left   1    1    2    6      ← 寫入 answer[i] 時的 left
answer 1    1    2    6
                              寫完後 left = left × nums[i]：1 → 1 → 2 → 6 → 24

第二趟（右 → 左）：answer[i] *= right，right 先用再乘上 nums[i]
i      3    2    1    0
right  1    4   12   24      ← 乘入 answer[i] 時的 right
answer 6×1  2×4  1×12 1×24
     = 6    8    12   24

結果 answer = [24, 12, 8, 6]

nums = [-1, 1, 0, -3, 3] 的 L 與 R：
i      0    1    2    3    4
L      1   -1   -1    0    0     ← 0 之後的前綴積全為 0
R      0    0    9    3    1     ← 0 之前的後綴積全為 0
L×R    0    0    9    0    0
```

第一趟每一格寫入的都是「乘上自己之前」的 left，所以 `answer[0] = 1`（空前綴的乘積），`answer[3] = 1 × 2 × 3 = 6`。第二趟對稱地，`answer[3]` 乘上空後綴的 1，`answer[0]` 乘上 `2 × 3 × 4 = 24`。第二個例子說明 0 的效果：只有 0 自己所在的位置，左右兩邊都不含 0，答案才不是 0。

### 解法

```python
import random
from math import prod


def product_except_self(nums: list[int]) -> list[int]:
    n = len(nums)
    answer = [1] * n
    left = 1
    for i in range(n):              # answer[i] = nums[:i] 的乘積
        answer[i] = left
        left *= nums[i]
    right = 1
    for i in range(n - 1, -1, -1):  # 乘上 nums[i+1:] 的乘積
        answer[i] *= right
        right *= nums[i]
    return answer


def brute(nums):
    return [prod(nums[:i] + nums[i + 1:]) for i in range(len(nums))]


assert product_except_self([1, 2, 3, 4]) == [24, 12, 8, 6]
assert product_except_self([-1, 1, 0, -3, 3]) == [0, 0, 9, 0, 0]
assert product_except_self([0, 0]) == [0, 0]
assert product_except_self([5, 7]) == [7, 5]
assert product_except_self([0, 4, 0, 2]) == [0, 0, 0, 0]
assert product_except_self([2, 0, 3]) == [0, 6, 0]
for _ in range(500):
    arr = [random.randint(-4, 4) for _ in range(random.randint(2, 9))]
    assert product_except_self(arr) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：兩趟線性掃描。空間：除了輸出陣列以外只有 `left`、`right` 兩個變數，O(1)；題目約定輸出陣列不算額外空間。邊界情況：恰好一個 0 時，只有 0 的位置答案非零；兩個以上的 0 時答案全為 0，演算法不需要特判，乘法本身會處理；n = 2 時答案是把兩個數交換；負數只影響符號，不影響流程。在 Java／C++ 中要注意中間的 `left`、`right` 是否溢位：題目只保證前綴與後綴乘積在 32 位元內，而 `left` 在第一趟最後會乘上最後一個元素，變成整個陣列的乘積，這個值不在保證範圍內，可以改成迴圈最後一輪不乘，或用 64 位元整數。

### Follow-up

> [!question]- F1. 如果允許使用除法，要怎麼正確處理 0？
> 先數 0 的個數 z，並算出所有**非零**元素的乘積 T。z ≥ 2 時答案全為 0；z = 1 時只有 0 所在的位置答案是 T，其餘為 0；z = 0 時 `answer[i] = T // nums[i]`（整除是精確的，因為 nums[i] 整除 T）。時間 O(n)、額外空間 O(1)。這個做法的教訓是：除法版本要處理三種情況，而前綴積加後綴積的版本完全不需要分類，這也是為什麼面試官要禁止除法，他想看你能不能找到不依賴反元素的拆法。

> [!question]- F2. 如果要回答很多次「區間 [l, r) 的乘積」查詢呢？
> 前綴積 `Q[r] / Q[l]` 需要除法，而 0 會讓之後的前綴積全變 0、無法還原。做法是把 0 分開處理：另建前綴計數 `Z[i]` 記錄前 i 個元素中 0 的個數，只對非零元素建前綴積。查詢時若 `Z[r] − Z[l] > 0` 答案就是 0，否則是非零前綴積的商。若結果要模一個質數 p（且元素都不是 p 的倍數），除法改成乘以模反元素 `pow(Q[l], p − 2, p)`；若模數不是質數，模反元素不一定存在，就改用 sparse table 或 segment tree（第 26 章），O(log n) 查詢。前處理 O(n)，每次查詢 O(1) 或 O(log p)。

> [!question]- F3. 如果改成「除了自己以外的最大值」或「除了自己以外的 gcd」呢？
> 同樣的「前綴 ⊕ 後綴」拆法適用於任何**有結合律**的運算，不需要反元素。建 `pre[i] = op(nums[:i])` 與 `suf[i] = op(nums[i+1:])`，答案是 `op(pre[i], suf[i])`；空前綴用該運算的單位元素（max 用 −∞，gcd 用 0，因為 gcd(0, x) = x）。時間 O(n)、空間 O(n)，也可以像本題一樣把其中一個寫在輸出陣列裡省掉一個陣列。這個套路在「刪除一個元素後的最大 gcd」「去掉一個區間後的最小值」等題目中都會出現。

> [!question]- F4. 如果輸入是二維矩陣，要每個格子「除了自己以外所有格子的乘積」並對 12345 取模呢（2906. Construct Product Matrix）？
> 把矩陣依列優先展開成一維，問題就和本題完全相同：第一趟從頭到尾算前綴積寫入輸出，第二趟從尾到頭乘上後綴積，每次乘法後都對 12345 取模。關鍵是 12345 = 3 × 5 × 823 不是質數，很多元素沒有模反元素，所以「總乘積除以自己」在這裡連取模版本都不能用，前綴積加後綴積是唯一乾淨的 O(mn) 解。時間 O(mn)，額外空間 O(1)（不計輸出）。

> [!question]- F5. 如果陣列很長、乘積可能溢位，但只需要比較答案的大小或正負號呢？
> 把乘積換成對數和：`log|answer[i]| = Σ_{j ≠ i} log|nums[j]|`，這就變成「除了自己以外的和」，用總和減掉自己即可（加法有反元素）；正負號則是「除了自己以外負數個數的奇偶性」，同樣用總數減自己。0 要另外計數：0 的個數扣掉自己後仍大於 0，答案就是 0。時間 O(n)。浮點對數有精度誤差，只適合比較大小，不適合要精確值的場合；要精確值時 Python 的大整數可以直接算，但 n 很大時乘積的位數會讓每次乘法變慢。

## 核心題 2｜560. Subarray Sum Equals K｜Medium

### 題目

給一個整數陣列 `nums` 和一個整數 `k`，回傳和恰好等於 `k` 的**連續非空子陣列**個數。陣列中**可以有負數和 0**。限制：`1 <= len(nums) <= 2 × 10⁴`，`-1000 <= nums[i] <= 1000`，`-10⁷ <= k <= 10⁷`。

- 範例 1：`nums = [1, 1, 1]`、`k = 2`，回傳 `2`：`[1, 1]` 出現在索引 0–1 和 1–2 兩個位置，位置不同就算不同的子陣列。
- 範例 2：`nums = [3, 4, 7, 2, -3, 1, 4, 2]`、`k = 7`，回傳 `4`：`[3, 4]`、`[7]`、`[7, 2, -3, 1]`、`[1, 4, 2]`。
- 範例 3（邊界）：`nums = [0, 0, 0]`、`k = 0`，回傳 `6`：長度 1 的有 3 個、長度 2 的有 2 個、長度 3 的有 1 個。
- 範例 4（邊界）：`nums = [1, -1, 1]`、`k = 1`，回傳 `3`：`[1]`（索引 0）、`[1]`（索引 2）、`[1, -1, 1]`。

### 思路

暴力解是枚舉所有子陣列。直接枚舉左右端點再加總是 O(n³)；固定左端點 l、讓右端點往右延伸並累加，可以降到 O(n²)，n = 2 × 10⁴ 時是 2 × 10⁸ 次，在 Python 中太慢。很多人第一個想到的優化是第 6 章的 sliding window：和太小就擴右邊、太大就縮左邊。但這需要「窗口變長和就變大」的單調性，有負數時不成立，例如範例 4 的 `[1, -1, 1]`：窗口 `[1]` 和已經是 1，再擴到 `[1, -1]` 和反而變小，sliding window 無法判斷該擴還是該縮，會漏掉 `[1, -1, 1]`。

關鍵觀察是 7.4 節的轉換：子陣列 `nums[l:r]` 的和等於 `P[r] − P[l]`，所以「和為 k」等價於 **`P[l] = P[r] − k`**。固定右端點 r，問題變成「在 `P[0], P[1], …, P[r − 1]` 中，有幾個等於 `P[r] − k`？」這是一個純粹的計數查詢，用 hash map 記錄每個前綴值出現的次數，就能 O(1) 回答。從左往右掃一次，每一步先查 `seen[P[r] − k]` 加進答案，再把 `P[r]` 存入，總共 O(n)。

invariant 是：處理到右端點 r 時，`seen` 恰好記錄了 `P[0]` 到 `P[r − 1]` 的出現次數。`P[0] = 0`（空前綴）一開始就要放進去，它代表「左端點在 0」的子陣列；查詢在存入之前做，保證 l < r，也就是子陣列非空。這兩個細節是這題最常寫錯的地方，k = 0 的範例 3 可以同時檢查兩者。

```text
nums = [3, 4, 7, 2, -3, 1, 4, 2]，k = 7
seen 初始 {0: 1}

 r  nums[r-1]  P[r]  P[r]-k  seen[P[r]-k]  累計  對應的子陣列
 1      3        3     -4         0          0
 2      4        7      0         1          1    P[0]=0 → nums[0:2] = [3, 4]
 3      7       14      7         1          2    P[2]=7 → nums[2:3] = [7]
 4      2       16      9         0          2
 5     -3       13      6         0          2
 6      1       14      7         1          3    P[2]=7 → nums[2:6] = [7, 2, -3, 1]
 7      4       18     11         0          3
 8      2       20     13         1          4    P[5]=13 → nums[5:8] = [1, 4, 2]

前綴值的時間軸（括號內是 r）：
0(0)  3(1)  7(2)  14(3)  16(4)  13(5)  14(6)  18(7)  20(8)
       └─ 7 = 0+7 ┘     14 在 r=3 和 r=6 各出現一次，
                        但兩者都只是被查詢的「右端」，查的都是 7
```

表中第 r = 6 列最能說明為什麼需要前綴和：`[7, 2, -3, 1]` 中間有負數，sliding window 在窗口 `[7, 2]`（和 9 > 7）時會縮左邊，丟掉 7，從此再也看不到這個子陣列；前綴和則不在乎中間怎麼起伏，只看兩端的前綴值 14 和 7 相差 k。

### 解法

```python
import random
from collections import Counter


def subarray_sum(nums: list[int], k: int) -> int:
    seen = Counter({0: 1})          # 空前綴
    total = running = 0
    for x in nums:
        running += x
        total += seen[running - k]  # 先查：l < r
        seen[running] += 1          # 後存
    return total


def brute(nums, k):
    n, count = len(nums), 0
    for l in range(n):
        s = 0
        for r in range(l, n):
            s += nums[r]
            count += s == k
    return count


assert subarray_sum([1, 1, 1], 2) == 2
assert subarray_sum([3, 4, 7, 2, -3, 1, 4, 2], 7) == 4
assert subarray_sum([0, 0, 0], 0) == 6
assert subarray_sum([1, -1, 1], 1) == 3
assert subarray_sum([5], 5) == 1
assert subarray_sum([5], 0) == 0
assert subarray_sum([-1, -1, 1], 0) == 1
for _ in range(500):
    arr = [random.randint(-3, 3) for _ in range(random.randint(1, 12))]
    kk = random.randint(-4, 4)
    assert subarray_sum(arr, kk) == brute(arr, kk)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每個元素做一次 hash map 查詢與一次更新，平均 O(1)。空間 O(n)：最差情況每個前綴值都不同。邊界情況：k = 0 時「先查再存」保證不會把空子陣列算進去，範例 3 的 `[0, 0, 0]` 會得到 1 + 2 + 3 = 6；全部元素都是 0 而 k = 0 時答案是 n(n + 1)/2，可達 2 × 10⁸，Python 不溢位，Java 用 `int` 仍夠但要留意；負數讓前綴值可能為負，hash map 不受影響。用 `Counter` 查詢不存在的 key 會回傳 0 而不會插入新 key，所以 `seen[running - k]` 不會讓表變大。

### Follow-up

> [!question]- F1. 如果要回傳和為 k 的最長子陣列長度呢（325. Maximum Size Subarray Sum Equals k）？
> 把「次數」改成「最早出現的位置」：`first = {0: -1}`，對每個 i 若 `P − k` 在表中，就用 `i − first[P − k]` 更新答案，再用 `setdefault(P, i)` 只記第一次出現。因為同一個前綴值越早出現，配出來的子陣列越長，後來的出現永遠不會更好。時間 O(n)、空間 O(n)。若要最短的，改成每次都覆寫成最新的位置。這就是 7.4 節「數個數存次數、找最長存最早、找最短存最晚」的規則。

> [!question]- F2. 如果改成「和可被 k 整除」的子陣列個數呢（974. Subarray Sums Divisible by K）？
> `(P[r] − P[l]) % k == 0` 等價於 `P[r] % k == P[l] % k`，所以 key 改成前綴和對 k 的餘數，查詢的對象從 `P − k` 改成「同一個餘數」。餘數只有 k 種，可以用長度 k 的陣列代替 hash map，空間 O(k)。Python 的 `%` 對負數回傳非負值（`-1 % 5 == 4`），可以直接用；Java／C++ 要寫 `((P % k) + k) % k`，否則 −1 和 4 會被當成不同的 key 而漏算。時間 O(n)。

> [!question]- F3. 如果陣列只有 0 和 1（或全是非負數），能不能用 O(1) 空間（930. Binary Subarrays With Sum）？
> 可以。非負時窗口和對右端點單調，「和 ≤ k 的子陣列個數」可以用 sliding window O(n)、O(1) 空間算出：對每個右端點，縮左端點直到和 ≤ k，貢獻 `r − l + 1` 個。於是「恰好 k」= at_most(k) − at_most(k − 1)。這個「恰好 = 至多相減」的技巧是第 6 章難題 3（992）的核心；前綴和 + hash map 則是不論正負都能用的通用解，代價是 O(n) 空間。

> [!question]- F4. 如果要列出所有和為 k 的子陣列（起訖索引）呢？
> 把 hash map 的值從「次數」改成「出現過的位置清單」，每次查到 `P − k` 時就把清單中每個位置 l 配上目前的 r 輸出。時間是 O(n + 輸出數量)，無法更好，因為答案本身可能有 Θ(n²) 個（例如全 0 而 k = 0）。面試時要先說明「輸出可能是平方級」，再給這個輸出敏感（output-sensitive）的做法；若只要回傳任意一個，存第一次出現的位置即可，O(n)。

> [!question]- F5. 如果要數「和落在 [lower, upper] 之間」的子陣列個數呢（327. Count of Range Sum）？
> 條件變成 `P[r] − upper ≤ P[l] ≤ P[r] − lower`，合法的左端點是一個**值的範圍**，hash map 只能查單一值，不夠用。要用能回答「之前的前綴中，有幾個落在 [a, b]」的結構：對前綴值做座標壓縮後用 Fenwick tree，每步兩次前綴查詢與一次更新，O(n log n)；或用 merge sort 在合併時以 two pointers 計數，同樣 O(n log n)。這是第 26 章難題 1，也是 7.6 節「條件是不等式時要換工具」的例子。

## 核心題 3｜525. Contiguous Array｜Medium

### 題目

給一個只包含 0 和 1 的陣列 `nums`，回傳 0 的個數與 1 的個數**相等**的最長連續子陣列長度；若不存在，回傳 0。限制：`1 <= len(nums) <= 10⁵`，`nums[i]` 只會是 0 或 1。

- 範例 1：`nums = [0, 1]`，回傳 `2`。
- 範例 2：`nums = [1, 1, 1, 0, 1, 0, 0, 1, 1]`，回傳 `6`：例如索引 1 到 6 的 `[1, 1, 0, 1, 0, 0]` 有三個 0、三個 1。
- 範例 3（邊界）：`nums = [1, 1, 1]`，回傳 `0`，沒有任何 0。
- 範例 4（邊界）：`nums = [0, 1, 1, 0, 1, 1, 1, 0]`，回傳 `4`：`[0, 1, 1, 0]`，最長的平衡子陣列在開頭。

### 思路

暴力解是枚舉左端點，往右延伸時同時維護 0 和 1 的個數，相等就更新答案，O(n²)，n = 10⁵ 時太慢。sliding window 也不適用，因為「相等」不是單調條件：窗口變長時，差值可能上升也可能下降，無法決定何時縮左邊。

關鍵觀察是把「兩種計數相等」改寫成「和為 0」：把每個 0 看成 −1、每個 1 看成 +1，子陣列中 0 與 1 一樣多 ⇔ 這段的和為 0 ⇔ **兩端的前綴和相等**，`P[l] = P[r]`。於是題目變成「找兩個相等的前綴值，距離最遠」，也就是 7.4 節「找最長」的模板：hash map 記錄每個前綴值**第一次出現**的位置，之後再遇到同一個值，距離就是一個候選答案。前綴值 `P[i]` 可以理解為「到目前為止 1 比 0 多幾個」，兩個時間點的差值相同，代表這段期間 1 和 0 增加得一樣多。

為什麼只需要記第一次出現？因為對同一個前綴值，越早的左端點配出來的子陣列越長，後面的出現永遠不會比第一次更好，所以第一次之後就不必再更新。空前綴 `P[0] = 0` 要預先記在位置 −1（以「結尾索引」計），讓從開頭開始的平衡子陣列（範例 4 的 `[0, 1, 1, 0]`）能被算到。前綴值的範圍是 −n 到 n，也可以用長度 2n + 1 的陣列代替 hash map，常數更小。

```text
nums = [1, 1, 1, 0, 1, 0, 0, 1, 1]，0 → -1、1 → +1
first 初始 {0: -1}

 i  nums[i]  前綴值  first 中有嗎？         候選長度   first（更新後）
 0     1        1     沒有，記 first[1]=0       -       {0:-1, 1:0}
 1     1        2     沒有，記 first[2]=1       -       {…, 2:1}
 2     1        3     沒有，記 first[3]=2       -       {…, 3:2}
 3     0        2     有，first[2]=1           3-1=2     不變
 4     1        3     有，first[3]=2           4-2=2     不變
 5     0        2     有，first[2]=1           5-1=4     不變
 6     0        1     有，first[1]=0           6-0=6 ★   不變
 7     1        2     有，first[2]=1           7-1=6     不變
 8     1        3     有，first[3]=2           8-2=6     不變
答案 6

前綴值的時間軸（前綴值 = 到目前為止 1 比 0 多幾個）：
i:       -1   0   1   2   3   4   5   6   7   8
前綴值:    0   1   2   3   2   3   2   1   2   3
              ↑                       ↑
              └──── 同為 1，相距 6 ────┘   → nums[1:7] 平衡
```

i = 6 時前綴值回到 1，而 1 第一次出現在 i = 0，所以 `nums[1:7]`（索引 1 到 6）這段的淨變化是 0，也就是 0 和 1 一樣多，長度 6。把前綴值想成一條每步上升或下降 1 的折線，任何兩個同高的點之間都是一段平衡子陣列，題目要的是同一高度上距離最遠的兩點；i = 7、8 雖然也和更早的點同高，但距離都沒有超過 6。

### 解法

```python
import random


def find_max_length(nums: list[int]) -> int:
    n = len(nums)
    first = [-2] * (2 * n + 1)      # 前綴值 + n 當索引；-2 代表還沒出現過
    first[n] = -1                   # 前綴值 0 出現在「位置 -1」（空前綴）
    best = balance = 0
    for i, x in enumerate(nums):
        balance += 1 if x == 1 else -1
        key = balance + n
        if first[key] == -2:
            first[key] = i          # 只記第一次出現
        else:
            best = max(best, i - first[key])
    return best


def brute(nums):
    best = 0
    for l in range(len(nums)):
        diff = 0
        for r in range(l, len(nums)):
            diff += 1 if nums[r] else -1
            if diff == 0:
                best = max(best, r - l + 1)
    return best


assert find_max_length([0, 1]) == 2
assert find_max_length([1, 1, 1, 0, 1, 0, 0, 1, 1]) == 6
assert find_max_length([1, 1, 1]) == 0
assert find_max_length([0, 1, 1, 0, 1, 1, 1, 0]) == 4
assert find_max_length([0]) == 0
assert find_max_length([0, 0, 1, 1, 0, 1]) == 6     # 整個陣列都平衡
for _ in range(500):
    arr = [random.randint(0, 1) for _ in range(random.randint(1, 14))]
    assert find_max_length(arr) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：一次掃描，每步 O(1)。空間 O(n)：`first` 陣列長度 2n + 1；用 dict 時最差也是 O(n)。邊界情況：全是 1 或全是 0 時前綴值嚴格單調，永遠不會重複，答案 0；整個陣列平衡時最後的前綴值回到 0，和空前綴配對得到 n；用 −2 而不是 −1 當「未出現」的標記，因為 −1 已經被空前綴用掉了（這是用陣列取代 dict 時最容易踩的坑）。答案一定是偶數，因為 0 和 1 一樣多。

### Follow-up

> [!question]- F1. 如果要數「0 和 1 一樣多」的子陣列有幾個呢？
> 把「第一次出現的位置」換成「出現次數」，就是核心題 2（560）在 k = 0 時的特例：對每個前綴值 b，答案加上 `count[b]`，再把 `count[b]` 加一，初始 `count[0] = 1`。時間 O(n)。等價地，答案是 Σ C(c_b, 2)，c_b 是每個前綴值出現的次數（包含空前綴），因為任選兩個同值的前綴都構成一段平衡子陣列。全部交替的 `[0, 1, 0, 1, …]` 是計數最多的情況之一，答案是平方級，Python 不必擔心溢位。

> [!question]- F2. 如果陣列有 0、1、2 三種值，要三者一樣多的最長子陣列呢？
> 一個前綴值不夠表示三種計數，但「三者一樣多」等價於「c1 − c0 和 c2 − c0 這兩個差值，在兩端相同」。所以 key 改成 tuple `(c1 − c0, c2 − c0)`，存第一次出現的位置，其他完全一樣，O(n) 時間、O(n) 空間。推廣到 m 種值時 key 是 m − 1 個差值，建 key 的成本是 O(m)，總共 O(nm)。這是「把相等條件編碼成前綴的 key」最一般的形式。

> [!question]- F3. 如果改成「1 比 0 多」的最長子陣列呢（1124. Longest Well-Performing Interval）？
> 條件變成 `P[r] − P[l] > 0`，是不等式。若 `P[r] > 0`，整個前綴 `[0, r)` 就合法，長度 r。否則，因為前綴值每次只變化 ±1、且從 0 出發，第一個小於 `P[r]` 的值一定是 `P[r] − 1` 第一次出現的位置（要降到更小的值，必須先經過 `P[r] − 1`），所以只要查 `first[P[r] − 1]`。這個「步長為 1 所以不會跳過」的觀察讓不等式退化成等式查詢，O(n) 時間。一般步長的數列就沒有這個性質，要改用單調堆疊（類似 962. Maximum Width Ramp）。

> [!question]- F4. 如果陣列是環狀的（子陣列可以從尾端繞回開頭）呢？
> 繞回開頭的子陣列，恰好是某個「不繞回」的子陣列的補集。設整個陣列的前綴值總和為 D，若補集的和為 D，則繞回的那一段和為 0，也就是平衡。所以答案是兩者的最大值：不繞回的最長平衡子陣列（原題），以及 n 減去「和恰好為 D 的最短非空子陣列」的長度。後者用 7.4 節「找最短存最晚」的模板：hash map 每次都覆寫成最新位置，查詢 `P − D`。兩趟都是 O(n) 時間、O(n) 空間。D = 0 時整個陣列本身就平衡，答案直接是 n。驗證時可以把陣列複製一份接在後面暴力檢查長度不超過 n 的子陣列，作為對照。

## 核心題 4｜304. Range Sum Query 2D - Immutable｜Medium

### 題目

設計一個類別 `NumMatrix`。建構時傳入一個 m × n 的整數矩陣 `matrix`；之後會呼叫很多次 `sumRegion(row1, col1, row2, col2)`，回傳以 `(row1, col1)` 為左上角、`(row2, col2)` 為右下角（**兩端都包含**）的子矩形中所有元素的和。矩陣建好後不會再改變。要求每次 `sumRegion` 都是 O(1)。限制：`1 <= m, n <= 200`，元素在 `-10⁴` 到 `10⁴` 之間，`sumRegion` 最多呼叫 10⁴ 次，且 `0 <= row1 <= row2 < m`、`0 <= col1 <= col2 < n`。

以下範例都使用這個矩陣：

```text
        col 0  col 1  col 2  col 3
row 0     3      0      1      4
row 1     5      6      3      2
row 2     1      2      0      1
```

- 範例 1：`sumRegion(1, 1, 2, 2)` 回傳 `11`，也就是 6 + 3 + 2 + 0。
- 範例 2：`sumRegion(0, 0, 2, 3)` 回傳 `28`，整個矩陣的和。
- 範例 3（邊界）：`sumRegion(2, 3, 2, 3)` 回傳 `1`，單一格。
- 範例 4（邊界）：`sumRegion(0, 1, 2, 1)` 回傳 `8`，只有一行（0 + 6 + 2）；從第 0 列開始的查詢不需要特判。

### 思路

暴力解是每次查詢都把子矩形加總，一次最多 O(mn) = 4 × 10⁴，10⁴ 次查詢共 4 × 10⁸，太慢。比較好一點的做法是對每一列分別建一維前綴和，查詢時對 row1 到 row2 的每一列做一次 O(1) 的區間和，每次查詢 O(m)，總共 2 × 10⁶，可以接受但不符合 O(1) 的要求。瓶頸是我們仍然逐列累加；要做到 O(1)，就必須讓「很多列的和」也能用常數個預先算好的值組合出來。

關鍵是 7.5 節的二維前綴和：`P[i][j]` = 左上角 `(0, 0)` 到 `(i − 1, j − 1)` 的矩形和，大小 (m + 1) × (n + 1)，第 0 列與第 0 行全為 0。任何一個子矩形，都可以寫成四個「從原點出發」的矩形的加減：整塊 `P[r2 + 1][c2 + 1]`，扣掉上方 `P[r1][c2 + 1]`，扣掉左方 `P[r2 + 1][c1]`，因為左上角那塊 `P[r1][c1]` 被扣了兩次，再加回一次。建表本身也用同樣的排容：`P[i + 1][j + 1] = M[i][j] + P[i][j + 1] + P[i + 1][j] − P[i][j]`。

題目的座標是閉區間，而 P 是半開區間的定義，所以轉換時右下角要加一：閉區間 `[r1, r2]` 對應半開 `[r1, r2 + 1)`。把轉換集中寫在 `sumRegion` 的一行裡，建表和查詢的邏輯就都只需要處理半開區間，不會在多個地方各自加減一。多出來的第 0 列與第 0 行是哨兵，讓 r1 = 0 或 c1 = 0 的查詢不必特判。

```text
P（(m+1) × (n+1)，P[i][j] = 前 i 列、前 j 行的和）
         j=0  j=1  j=2  j=3  j=4
  i=0     0    0    0    0    0
  i=1     0    3    3    4    8
  i=2     0    8   14   18   24
  i=3     0    9   17   21   28

建表一格：P[2][2] = M[1][1] + P[1][2] + P[2][1] − P[1][1] = 6 + 3 + 8 − 3 = 14

查詢 sumRegion(1, 1, 2, 2) → 半開 rows [1, 3)、cols [1, 3)
  整塊  P[3][3] = 21    (rows 0–2, cols 0–2)
− 上方  P[1][3] =  4    (row 0,    cols 0–2)
− 左方  P[3][1] =  9    (rows 0–2, col 0)
+ 左上  P[1][1] =  3    (row 0,    col 0) ← 被上方和左方各扣一次
= 21 − 4 − 9 + 3 = 11

     col0 col1 col2
row0 [ 3 ][ 0    1 ]  ← 上方
row1 [ 5 ][ 6    3 ]  ┐
row2 [ 1 ][ 2    0 ]  ┘ 目標 = 6+3+2+0
      ↑ 左方
```

圖中可以看到，整塊 21 包含目標 11、上方一列的 0 + 1、左方一行的 5 + 1，以及左上角的 3；扣掉上方 4（3 + 0 + 1）和左方 9（3 + 5 + 1）時，3 被扣了兩次，加回 3 之後剩下的正好是目標。

### 解法

```python
import random


class NumMatrix:
    def __init__(self, matrix: list[list[int]]):
        m, n = len(matrix), len(matrix[0])
        P = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m):
            row_sum = 0                         # 這一列到第 j 行的和
            for j in range(n):
                row_sum += matrix[i][j]
                P[i + 1][j + 1] = P[i][j + 1] + row_sum   # 上方矩形 + 本列前綴
        self.P = P

    def sumRegion(self, row1: int, col1: int, row2: int, col2: int) -> int:
        P = self.P
        r2, c2 = row2 + 1, col2 + 1            # 閉區間 → 半開區間
        return P[r2][c2] - P[row1][c2] - P[r2][col1] + P[row1][col1]


M = [[3, 0, 1, 4], [5, 6, 3, 2], [1, 2, 0, 1]]
nm = NumMatrix(M)
assert nm.sumRegion(1, 1, 2, 2) == 11
assert nm.sumRegion(0, 0, 2, 3) == 28
assert nm.sumRegion(2, 3, 2, 3) == 1
assert nm.sumRegion(0, 1, 2, 1) == 8
assert NumMatrix([[-7]]).sumRegion(0, 0, 0, 0) == -7
for _ in range(100):
    m, n = random.randint(1, 5), random.randint(1, 5)
    A = [[random.randint(-9, 9) for _ in range(n)] for _ in range(m)]
    obj = NumMatrix(A)
    r1, r2 = sorted(random.randrange(m) for _ in range(2))
    c1, c2 = sorted(random.randrange(n) for _ in range(2))
    expect = sum(A[r][c] for r in range(r1, r2 + 1) for c in range(c1, c2 + 1))
    assert obj.sumRegion(r1, c1, r2, c2) == expect
print("all tests passed")
```

建表時用了一個等價但更不容易寫錯的寫法：`P[i + 1][j + 1]` = 上方的矩形 `P[i][j + 1]` 加上本列從第 0 行到第 j 行的和 `row_sum`。這和排容公式算出的是同一個數，但只有一個加法，不必記符號。

### 複雜度與邊界

建構 O(mn) 時間與 O(mn) 空間；每次查詢 O(1)，四次讀取與三次加減。邊界情況：查詢從第 0 列或第 0 行開始時，會讀到 P 的第 0 列或第 0 行，它們都是 0，自動正確；單一格的查詢 r1 = r2、c1 = c2 也是同一個公式；元素有負數不影響，因為只用到加減。總和最大是 4 × 10⁴ × 10⁴ = 4 × 10⁸，在 32 位元範圍內，但建表過程的中間值也要確認不溢位，Java 用 `int` 剛好可以。若矩陣可能是空的（m = 0 或 n = 0），建構時要先判斷，原題保證不會。

### Follow-up

> [!question]- F1. 如果矩陣會被修改呢（308. Range Sum Query 2D - Mutable）？
> 二維前綴和一次修改要更新 O(mn) 個格子，太貴。三種取捨：一是每列各自維護一維前綴和，修改 O(n)、查詢 O(m)；二是每列各用一棵 Fenwick tree，修改 O(log n)、查詢 O(m log n)；三是二維 Fenwick tree（每個節點本身也是一棵 Fenwick），修改與查詢都是 O(log m · log n)，空間 O(mn)。面試時先問修改和查詢的比例：若修改極少，就每次修改後重建前綴和；若兩者一樣多，二維 Fenwick 最平衡。這是第 26 章核心題 1（307）的二維版本。

> [!question]- F2. 如果要對每個格子算「以它為中心、半徑 k 的方塊和」呢（1314. Matrix Block Sum）？
> 對格子 (i, j)，方塊是 rows `[max(0, i − k), min(m, i + k + 1))`、cols `[max(0, j − k), min(n, j + k + 1))`，邊界要夾在矩陣範圍內，然後用一次 O(1) 的 `rect_sum` 查詢。總時間 O(mn)，與 k 無關；若直接對每格加總方塊，則是 O(mn · k²)。這題的難點只有邊界夾取，半開區間的寫法讓上界用 `min(m, i + k + 1)` 一次寫對。

> [!question]- F3. 如果要找「和不超過 threshold 的最大正方形邊長」，而且元素都非負呢（1292）？
> 有了二維前綴和，任一正方形的和都是 O(1)。元素非負時，正方形越大和越大，所以可以對邊長做 binary search（第 8 章），每次檢查所有位置，O(mn log min(m, n))。更好的做法是利用「答案只會遞增」：依序把每個格子當作右下角，只嘗試邊長 best + 1，成功就讓 best 加一；因為若某處有邊長 best + 2 的合法正方形，它內部也包含邊長 best + 1 的合法正方形（非負），會更早被找到。每格 O(1)，總時間 O(mn)。

> [!question]- F4. 如果是三維（或 d 維）的區塊和查詢呢？
> 三維前綴和 `P[i][j][k]` 的查詢需要 2³ = 8 項的排容，符號依「取上界的維度數」決定：取上界的維度數與總維度同奇偶時為正。d 維就是 2^d 項。建表時不必寫 2^d 項的公式：依序沿著每一個維度做一次一維前綴和（先沿 x 軸累加，再沿 y 軸，再沿 z 軸），結果就是 d 維前綴和，總時間 O(d · N)，N 是格子總數。這個「逐維累加」的寫法在二維時也成立，正是本題解法中先算列內前綴再加上方的做法。

## 核心題 5｜1094. Car Pooling｜Medium

### 題目

一輛車有 `capacity` 個空座位，只會往東開（位置只增不減）。給一個陣列 `trips`，其中 `trips[i] = [numPassengers, from, to]` 代表第 i 組有 `numPassengers` 位乘客，在位置 `from` 上車、在位置 `to` 下車。判斷能不能載完所有乘客，也就是在任何位置，車上的人數都不超過 `capacity`。下車發生在抵達 `to` 的那一刻，所以在位置 `to` 下車的人不會和在 `to` 上車的人同時佔用座位。限制：`1 <= len(trips) <= 1000`，`1 <= numPassengers <= 100`，`0 <= from < to <= 1000`，`1 <= capacity <= 10⁵`。

- 範例 1：`trips = [[2, 1, 5], [3, 3, 7]]`、`capacity = 4`，回傳 `False`：位置 3 到 5 之間車上有 5 人。
- 範例 2：同樣的 trips、`capacity = 5`，回傳 `True`。
- 範例 3（邊界）：`trips = [[2, 1, 5], [3, 5, 7]]`、`capacity = 3`，回傳 `True`：第一組在 5 下車，第二組在 5 上車，不重疊。
- 範例 4：`trips = [[2, 1, 5], [3, 3, 7], [1, 4, 6]]`、`capacity = 5`，回傳 `False`：位置 4 時車上有 6 人。

### 思路

暴力解是對每一組乘客，把他們在 `[from, to)` 之間的每一個位置都加上人數，最後檢查是否有位置超過容量。位置最多 1001 個、trips 最多 1000 組，最差 10⁶ 次，其實能過；但若位置範圍是 10⁹，這個做法就完全不可行，而且它把「一組乘客」拆成了很多次逐點修改，浪費在重複的區間更新上。

關鍵觀察是：一組乘客對車上人數的影響，只發生在兩個時間點——在 `from` 人數加 p，在 `to` 人數減 p。中間的位置人數不變，所以根本不需要逐點記錄。這正是 7.3 節的 difference array：`diff[from] += p`、`diff[to] −= p`，所有 trips 處理完後，從位置 0 往東對 diff 做前綴和，`running` 就是每個位置的車上人數，只要某處超過 capacity 就回傳 False。區間 `[from, to)` 是半開的，恰好對應「在 to 下車」的語意，所以減在 `to` 而不是 `to + 1`。

為什麼同一個位置的上車和下車不會互相干擾？因為同一位置的所有增減會先在 `diff[x]` 中加總，前綴和一次加上淨變化：範例 3 在位置 5 有 −2 和 +3，淨變化 +1，車上人數從 2 變 3，不會出現「先上車變 5 人」的錯誤中間狀態。如果改用「排序事件」的做法，就必須讓同一位置的下車排在上車之前，差分陣列則天生處理好了這件事。

```text
trips = [[2, 1, 5], [3, 3, 7], [1, 4, 6]]，capacity = 5

差分：位置 1 +2、位置 5 −2；位置 3 +3、位置 7 −3；位置 4 +1、位置 6 −1
位置 x:      0   1   2   3   4   5   6   7   8
diff[x]:     0  +2   0  +3  +1  −2  −1  −3   0
running:     0   2   2   5   6   4   3   0   0
                             ↑ 6 > 5 → False

時間軸：
位置   0   1   2   3   4   5   6   7
組1        [===============)            2 人
組2                [===============)    3 人
組3                    [=======)        1 人
人數   0   2   2   5   6   4   3   0
```

逐位置看 running：位置 1 第一組上車變 2；位置 3 第二組上車變 5，剛好等於容量；位置 4 第三組上車變 6，超過容量，可以立刻回傳 False。時間軸圖中，三段區間在位置 4 同時重疊，這就是人數的最高點。

### 解法

```python
import random


def car_pooling(trips: list[list[int]], capacity: int) -> bool:
    max_loc = max(to for _, _, to in trips)
    diff = [0] * (max_loc + 1)
    for p, start, end in trips:
        diff[start] += p              # 在 start 上車
        diff[end] -= p                # 在 end 下車（半開區間）
    running = 0
    for delta in diff:
        running += delta
        if running > capacity:
            return False
    return True


def car_pooling_events(trips: list[list[int]], capacity: int) -> bool:
    """位置範圍很大時：只看有事件的位置，O(n log n)。"""
    events = []
    for p, start, end in trips:
        events.append((start, p))
        events.append((end, -p))
    events.sort()                     # 同位置時 -p < +p，下車先處理
    running = 0
    for _, delta in events:
        running += delta
        if running > capacity:
            return False
    return True


def brute(trips, capacity):
    load = [0] * 1002
    for p, s, e in trips:
        for x in range(s, e):
            load[x] += p
    return max(load) <= capacity


assert car_pooling([[2, 1, 5], [3, 3, 7]], 4) is False
assert car_pooling([[2, 1, 5], [3, 3, 7]], 5) is True
assert car_pooling([[2, 1, 5], [3, 5, 7]], 3) is True
assert car_pooling([[2, 1, 5], [3, 3, 7], [1, 4, 6]], 5) is False
assert car_pooling([[9, 0, 1]], 9) is True
assert car_pooling([[9, 0, 1]], 8) is False
for _ in range(500):
    tr = []
    for _ in range(random.randint(1, 6)):
        s = random.randint(0, 9)
        tr.append([random.randint(1, 5), s, random.randint(s + 1, 10)])
    cap = random.randint(1, 15)
    assert car_pooling(tr, cap) == brute(tr, cap) == car_pooling_events(tr, cap)
print("all tests passed")
```

### 複雜度與邊界

差分版本時間 O(n + L)、空間 O(L)，n 是 trips 數、L 是最大位置（≤ 1000）。事件排序版本時間 O(n log n)、空間 O(n)，與位置範圍無關。邊界情況：一組乘客在 `to` 下車、另一組在同一位置上車時，差分陣列把兩者合併成淨變化，排序版本靠 tuple 排序讓負數（下車）先處理；單一 trip 的人數就超過容量時，在 `from` 那一格就會回傳 False；diff 的長度取 `max_loc + 1`，因為最大的 `to` 也要寫入。檢查 `running > capacity` 用嚴格大於，剛好等於容量是允許的。

### Follow-up

> [!question]- F1. 如果位置的範圍是 0 到 10⁹ 呢？
> 差分陣列需要 O(L) 空間，不可行。改用事件排序（解法中的第二個函式）：只有 2n 個位置會改變人數，排序後依序累加，O(n log n) 時間、O(n) 空間。另一種寫法是用 `Counter` 把同一位置的增減合併，再對 key 排序後累加，效果相同，也自然解決了同位置上下車的順序問題。這就是第 9 章 sweep line（掃描線）的基本形：差分陣列是「位置稠密」時的掃描線，排序事件是「位置稀疏」時的差分陣列。

> [!question]- F2. 如果要回傳「最少需要幾個座位」，或第一個超載的位置呢？
> 最少座位就是 running 在整個掃描中的最大值，把 `return False` 改成 `best = max(best, running)`，O(n + L)。第一個超載的位置是 running 第一次超過 capacity 時的索引 x，在差分版本中就是迴圈當時的位置；事件版本則是當時事件的位置。這兩個問題和第 9 章核心題 5（253. Meeting Rooms II）是同一題：會議是區間、會議室是座位，最少會議室數就是同時進行的會議數的最大值。

> [!question]- F3. 如果要回傳每個位置最終的值，而且區間是兩端都包含的呢（1109. Corporate Flight Bookings）？
> 1109 題給 `bookings[i] = [first, last, seats]`，代表航班 first 到 last（1-indexed、**兩端都包含**）每班都多 seats 個座位，要回傳每個航班的總座位數。做法是 `diff[first − 1] += seats`、`diff[last] −= seats`（轉成 0-indexed 的半開區間 `[first − 1, last)`），再做一次前綴和輸出整個陣列，O(n + 航班數)。這題和本題的差別只在端點語意，正好是 7.7 節「區間端點語意搞錯」最常發生的地方。

> [!question]- F4. 如果 trips 是一筆一筆進來的，每來一筆就要判斷能不能接受（接受才加入）呢？
> 差分陣列的前提是「全部修改完才讀取」，交錯的修改和查詢會讓每次查詢都要重新做前綴和，O(L)。線上版本需要支援「區間加值」與「區間最大值」：用 lazy propagation 的 segment tree，每次先查 `[from, to)` 的最大人數加上 p 是否超過 capacity，若沒有才做區間加值，兩者都是 O(log L)。位置範圍大時先離線座標壓縮，或用動態開點。這正是第 26 章核心題 3、4（729、731 My Calendar I／II）的結構。

> [!question]- F5. 如果改成二維：很多次「把某個矩形全部加一」，最後回傳整個矩陣呢（2536. Increment Submatrices by One）？
> 用 7.5 節的二維差分：每次修改只動四個角 `D[r1][c1] += 1`、`D[r1][c2 + 1] −= 1`、`D[r2 + 1][c1] −= 1`、`D[r2 + 1][c2 + 1] += 1`（題目給的是閉區間），最後對 D 做一次二維前綴和。時間 O(q + n²)，q 是修改次數；直接逐格修改則是 O(q · n²)。一個常見的折衷是每列各做一維差分，每次修改 O(列數)，在面試中也可以接受，但要能說出二維差分可以做到 O(1)。

## 難題 1｜1074. Number of Submatrices That Sum to Target｜Hard

### 題目

給一個 m × n 的整數矩陣 `matrix` 和一個整數 `target`，回傳元素和恰好等於 `target` 的**非空子矩形**個數。子矩形由上下左右四個邊界 `(x1, y1, x2, y2)` 決定（`x1 <= x2`、`y1 <= y2`，包含邊界上的格子）；只要任一個邊界不同，就算不同的子矩形，即使元素完全相同。矩陣可以有負數。限制：`1 <= m, n <= 100`，元素在 `-1000` 到 `1000` 之間，`-10⁸ <= target <= 10⁸`。

- 範例 1：`matrix = [[1, -1, 2], [0, 2, -1]]`、`target = 1`，回傳 `7`。例如第 0 列的 `[1]`、第 0 列的 `[-1, 2]`、兩列一起的第 0 行 `[1; 0]`、第 1 列的 `[0, 2, -1]` 等。
- 範例 2：`matrix = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]`、`target = 0`，回傳 `4`，也就是四個角落的單格 0。
- 範例 3（邊界）：`matrix = [[5]]`、`target = 0`，回傳 `0`；`target = 5` 時回傳 `1`。
- 範例 4（邊界）：`matrix = [[1, -1], [-1, 1]]`、`target = 0`，回傳 `5`：兩個橫向的 `[1, -1]`、`[-1, 1]`，兩個直向的，以及整個 2 × 2。

### 提示

> [!tip]- 提示 1
> 二維前綴和可以 O(1) 算出任一子矩形的和，但子矩形有 O(m² n²) 個，在 100 × 100 時是 10⁸ 個，太多了。想一想一維的版本（核心題 2）是怎麼避免枚舉所有子陣列的。

> [!tip]- 提示 2
> 如果子矩形的上邊界和下邊界已經固定，剩下的自由度只有左右邊界。能不能把這個固定高度的「帶狀區域」變成一個一維陣列？

> [!tip]- 提示 3
> 固定上下列 top、bottom，令 `col[c]` 為第 c 行從 top 到 bottom 的和。上下邊界為 top、bottom 的子矩形，一一對應到 `col` 的子陣列，於是問題就是對 `col` 做 560 題。bottom 往下移一列時，`col` 只需加上新的一列，不必重算。

### 詳解

**為什麼直覺做法不夠**。最直接的做法是先建二維前綴和（核心題 4），再枚舉四個邊界，每個子矩形 O(1) 檢查，總共 O(m² n²)。m = n = 100 時是 m(m + 1)/2 × n(n + 1)/2 ≈ 2.5 × 10⁷ 個子矩形，乘上 Python 每次迭代的常數，大約要數十秒，在 C++ 中勉強能過，但這不是面試官要的答案。瓶頸和一維時完全一樣：我們在逐一枚舉左右兩個端點，而核心題 2 已經告訴我們，「和為定值」的計數可以只枚舉一個端點，另一個用 hash map 一次查完。

**突破點：固定上下兩列，把二維壓成一維**。對每一對 `(top, bottom)`，定義 `col[c] = matrix[top][c] + … + matrix[bottom][c]`。一個上下邊界恰好是 top 與 bottom 的子矩形，由左右邊界 `[c1, c2]` 決定，它的和是 `col[c1] + … + col[c2]`，也就是 `col` 的一個子陣列的和。所以「上下邊界為 (top, bottom) 且和為 target 的子矩形個數」等於「`col` 中和為 target 的子陣列個數」，用 560 的 hash map 模板 O(n) 算出。所有 (top, bottom) 的答案加總就是最後的答案，因為每個子矩形恰好有一組上下邊界，不會重複也不會遺漏。

**增量更新 col**。固定 top 之後，讓 bottom 從 top 往下走，每走一列就把 `matrix[bottom]` 加進 `col`，O(n)。這樣不需要二維前綴和，也不需要每次重算 col。總共 O(m²) 對列，每對 O(n)，時間 O(m² · n)。若 m > n，先把矩陣轉置，讓列數是較小的那一維，時間變成 O(min(m, n)² · max(m, n))。

**正確性**。對固定的 (top, bottom)，hash map 模板的正確性就是核心題 2：每個右端點 c2 查到的 `seen[P − target]`，恰好是滿足 `col[c1..c2]` 和為 target 的左端點 c1 的個數。上下邊界的枚舉涵蓋所有 m(m + 1)/2 種組合，每個子矩形被它唯一的上下邊界計算一次。每一對 (top, bottom) 都要**重新**建立 hash map，否則不同高度的前綴會被混在一起配對，配出來的不是矩形。

```text
matrix = [[ 1, -1,  2],
          [ 0,  2, -1]]，target = 1

(top, bottom) = (0, 0)：col = [1, -1, 2]
  c   col[c]  前綴 P   P − 1   seen[P − 1]   seen（更新後）
  0     1       1       0         1          {0:1, 1:1}         ← [1]
  1    -1       0      -1         0          {0:2, 1:1}
  2     2       2       1         1          {0:2, 1:1, 2:1}    ← [-1, 2]
  小計 2

(top, bottom) = (0, 1)：col = [1+0, -1+2, 2-1] = [1, 1, 1]
  前綴 1, 2, 3；查 0, 1, 2 → 各 1 個           ← 三個寬度 1 的直條
  小計 3

(top, bottom) = (1, 1)：col = [0, 2, -1]
  前綴 0, 2, 1；查 -1, 1, 0 → 0, 0, 2 個       ← [0, 2, -1] 與 [2, -1]
  小計 2

總數 2 + 3 + 2 = 7
```

(0, 1) 這一對最能說明壓縮的效果：兩列合起來後每一行的和都是 1，於是 `col = [1, 1, 1]`，三個單行的子陣列各自和為 1，對應三個 2 × 1 的直條子矩形。(1, 1) 中最後一步查到 `seen[0] = 2`，因為空前綴與 c = 0 的前綴都是 0，分別對應整列 `[0, 2, -1]` 與 `[2, -1]`。

### 解法

```python
import random


def num_submatrix_sum_target(matrix: list[list[int]], target: int) -> int:
    if len(matrix) > len(matrix[0]):
        matrix = [list(col) for col in zip(*matrix)]   # 讓列數是較小的一維
    m, n = len(matrix), len(matrix[0])
    total = 0
    for top in range(m):
        col = [0] * n
        for bottom in range(top, m):
            row = matrix[bottom]
            for c in range(n):
                col[c] += row[c]                      # 增量加入新的一列
            seen = {0: 1}                             # 每對 (top, bottom) 重新開始
            running = 0
            for v in col:
                running += v
                total += seen.get(running - target, 0)
                seen[running] = seen.get(running, 0) + 1
    return total


def brute(matrix, target):
    m, n = len(matrix), len(matrix[0])
    count = 0
    for r1 in range(m):
        for r2 in range(r1, m):
            for c1 in range(n):
                for c2 in range(c1, n):
                    s = sum(matrix[r][c] for r in range(r1, r2 + 1) for c in range(c1, c2 + 1))
                    count += s == target
    return count


assert num_submatrix_sum_target([[1, -1, 2], [0, 2, -1]], 1) == 7
assert num_submatrix_sum_target([[0, 1, 0], [1, 1, 1], [0, 1, 0]], 0) == 4
assert num_submatrix_sum_target([[5]], 0) == 0
assert num_submatrix_sum_target([[5]], 5) == 1
assert num_submatrix_sum_target([[1, -1], [-1, 1]], 0) == 5
assert num_submatrix_sum_target([[1], [2], [3]], 3) == 2       # 轉置後的情況
for _ in range(200):
    m, n = random.randint(1, 4), random.randint(1, 4)
    A = [[random.randint(-2, 2) for _ in range(n)] for _ in range(m)]
    t = random.randint(-2, 2)
    assert num_submatrix_sum_target(A, t) == brute(A, t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(min(m, n)² · max(m, n))：m = n = 100 時約 5 × 10⁵ 次 hash map 操作再乘上常數，遠小於暴力的 2.5 × 10⁷ 個子矩形。空間 O(max(m, n))：`col` 與每輪的 hash map。邊界情況：單一格的矩陣只有一個子矩形；target = 0 時「先查再存」保證不算空子陣列；全零矩陣而 target = 0 時，答案是 [m(m + 1)/2] × [n(n + 1)/2]，演算法正確計入；轉置只在 m > n 時做，避免 m = 100、n = 1 這種極端形狀：不轉置是 m² · n = 10⁴，轉置後是 1² · 100 = 100，差了 100 倍。

### Follow-up

> [!question]- F1. 如果要的是「和最大的子矩形」，沒有 target 呢？
> 同樣固定上下兩列壓成 `col`，對 `col` 做 Kadane（最大子陣列和），O(n)，所以總共 O(m² n)。Kadane 本身也是前綴和的觀點：以 c 結尾的最大子陣列和 = `P[c + 1] − min(P[0..c])`，只要維護目前為止最小的前綴。若要回傳座標，在 Kadane 中記錄最小前綴的位置即可。這是很常見的面試題（「最大子矩陣」），和本題的差別只是一維部分從 hash map 換成「維護最小前綴」。

> [!question]- F2. 如果要數「和 ≤ target」的子矩形，而且元素都非負呢？
> 非負時 `col` 也全非負，對固定的 (top, bottom)，「和 ≤ target 的子陣列個數」可以用 sliding window O(n)：右端點每前進一格，縮左端點直到窗口和 ≤ target，貢獻 `r − l + 1` 個。總共 O(m² n)。若元素可負，sliding window 失效，要改成「之前的前綴中有幾個 ≥ P − target」，用座標壓縮加 Fenwick tree，每對列 O(n log n)，總共 O(m² n log n)。

> [!question]- F3. 如果要回傳面積最大的、和為 target 的子矩形呢？
> 對每一對 (top, bottom)，改用 7.4 節「找最長」的模板：hash map 存每個前綴值第一次出現的位置，得到這一對列中最寬的合法子陣列寬度 w，面積就是 `(bottom − top + 1) × w`。所有列對取最大值，O(m² n)。注意面積最大不等於寬度最大或高度最大，必須在每一對列中比較乘積；也不能只存最後一次出現的位置，那樣得到的是最窄的。

> [!question]- F4. m、n 到 1000 時還能更快嗎？
> 這個方法是 O(n³)，n = 1000 時約 10⁹ 次操作，在 Python 中不可行，C++ 也要數秒。對於一般整數矩陣的「子矩形和恰為 target 的計數」，面試中常見的回答是：目前的標準解就是 O(min² · max)，沒有廣為人知的大幅改進；實務上的優化是轉置讓較小的一維當外層、改用陣列代替 hash map（若前綴值範圍小），或在 C++ 中用預先配置的 hash table。若矩陣是 0/1 而問題變成「全 1 的子矩形個數」（1504），則有 O(mn) 的 monotonic stack 解法，那是第 10 章的技巧，和 target 計數是不同的問題。

### 心得

關鍵突破是「固定上下兩列，子矩形就變成一維子陣列」，於是二維問題直接化約成核心題 2，複雜度從 O(m² n²) 降到 O(m² n)。這個降維技巧是本章二維題目的共同骨架：難題 2（363）用同樣的壓縮，只是一維部分換成「不超過 k 的最大子陣列和」；F1 換成 Kadane。面試時建議的敘事是：先說二維前綴和加四重迴圈的 O(m² n²)，指出這等於在一維時枚舉兩個端點，然後說「我固定上下邊界，把每一行壓成一個數，問題就是 560」，最後提醒每對列要重建 hash map、以及轉置讓較小的一維在外層。

## 難題 2｜363. Max Sum of Rectangle No Larger Than K｜Hard

### 題目

給一個 m × n 的整數矩陣 `matrix` 和一個整數 `k`，在所有和**不超過 k** 的子矩形中，回傳最大的那個和。題目保證至少有一個子矩形的和不超過 k。矩陣可以有負數。限制：`1 <= m, n <= 100`，元素在 `-100` 到 `100` 之間，`-10⁵ <= k <= 10⁵`。原題的進階問題是：如果列數遠大於行數，要怎麼做？

- 範例 1：`matrix = [[1, 0, 1], [0, -2, 3]]`、`k = 2`，回傳 `2`：例如子矩形 `[[0, 1], [-2, 3]]` 的和是 2；也有其他和為 2 的子矩形。
- 範例 2：`matrix = [[2, 2, -1]]`、`k = 3`，回傳 `3`：`[2, 2, -1]` 的和是 3。
- 範例 3（邊界）：`matrix = [[5, -6]]`、`k = 4`，回傳 `-1`：三個子矩形的和是 5、−6、−1，只有後兩者不超過 4，較大的是 −1，答案可以是負數。
- 範例 4（邊界）：`matrix = [[-3]]`、`k = -3`，回傳 `-3`，剛好等於 k 也算。

### 提示

> [!tip]- 提示 1
> 先用難題 1 的方法把二維變成一維：固定上下兩列，壓成 `col`。現在的一維問題是：在 `col` 中找「和不超過 k 的最大子陣列和」。

> [!tip]- 提示 2
> 子陣列和是 `P[r] − P[l]`。對固定的 r，要讓 `P[r] − P[l] ≤ k` 且盡量大，等價於找最小的 `P[l]`，使得 `P[l] ≥ P[r] − k`。這是一個「在之前出現過的值中找後繼（successor）」的查詢。

> [!tip]- 提示 3
> 把之前的前綴值放在一個排序結構裡，每次用 binary search 找第一個 ≥ `P[r] − k` 的值，再把 `P[r]` 插入。每對列 O(n log n)。另外，如果這一對列的 Kadane 最大值已經 ≤ k，它就是答案，不必做排序查詢。

### 詳解

**為什麼直覺做法不夠**。降維之後，一維問題的條件是「≤ k」，不是等式，所以核心題 2 的 hash map 查不到：合法的 `P[l]` 不是一個值，而是一個範圍 `[P[r] − k, ∞)`，而我們要的是範圍中最小的那個。sliding window 也不行，因為 `col` 可能有負數，窗口和不單調。暴力的一維做法是對每個 r 掃過所有 l，O(n²)，總共 O(m² n²) ≈ 2.5 × 10⁷（算上 m(m + 1)/2 對列與 n(n + 1)/2 對端點），在 Python 中太慢。

**突破點：在排序的前綴值中找後繼**。固定 r，我們要最大化 `P[r] − P[l]`，同時滿足 `P[r] − P[l] ≤ k`，也就是 `P[l] ≥ P[r] − k`。在這個限制下，`P[l]` 越小越好，所以要找「之前的前綴中，≥ `P[r] − k` 的最小值」，這正是排序結構上的 lower bound：`bisect_left(sorted_prefixes, P[r] − k)`。找到後候選答案是 `P[r] − 那個值`，然後把 `P[r]` 插入排序結構，留給之後的 r 使用。空前綴 0 一開始就在結構中。

**Python 的排序結構**。標準函式庫沒有平衡二元搜尋樹。`bisect.insort` 在 list 中插入，搜尋是 O(log n)，但插入要搬移元素，最差 O(n)；在 n ≤ 100 時這個搬移是一次 C 層級的記憶體複製，非常快，實務上完全可以接受，但面試時要誠實說明它的漸進複雜度。若要嚴格的 O(log n)，可以用離線的座標壓縮加 Fenwick tree（見 F2），或在允許第三方套件時使用 `sortedcontainers.SortedList`。

**Kadane 剪枝**。對每一對列，先用 Kadane O(n) 算出 `col` 的最大子陣列和 s。若 s ≤ k，它就是這一對列在限制下的最佳值，可以跳過排序查詢；若 s > k，才需要做後繼查詢。當 k 很大時，大多數列對都能被剪掉。另外，若某一對列的答案剛好等於 k，就已經是全域最佳，可以直接回傳。

```text
matrix = [[1, 0, 1], [0, -2, 3]]，k = 2

(top, bottom) = (0, 1)：col = [1, -2, 4]，Kadane 最大值 = 4 > 2，需要排序查詢
  r  col  P[r]  需要 P[l] >= P[r]−2   排序的前綴（查詢前）   找到   候選
  1   1    1         −1                [0]                    0     1 − 0 = 1
  2  −2   −1         −3                [0, 1]                 0    −1 − 0 = −1
  3   4    3          1                [−1, 0, 1]             1     3 − 1 = 2  ★
  這一對列的最佳值 = 2（子陣列 col[1:3] = [−2, 4]，即 cols 1–2）

(top, bottom) = (0, 0)：col = [1, 0, 1]，Kadane 最大值 = 2 <= 2 → 直接取 2
(top, bottom) = (1, 1)：col = [0, −2, 3]，Kadane 最大值 = 3 > 2，查詢後最佳值 = 1

全域答案 = max(2, 2, 1) = 2
```

(0, 1) 這一對列在 r = 3 時，前綴 3 要配一個 ≥ 1 的最小前綴，排序結構中是 `[-1, 0, 1]`，lower bound 找到 1（來自 r = 1），所以子陣列是 `col[1:3]`，和為 2，對應原矩陣中 cols 1–2、rows 0–1 的子矩形 `[[0, 1], [-2, 3]]`。如果直接取最小的前綴 −1，會得到 3 − (−1) = 4，超過 k，這就是為什麼要找「≥ 下限的最小值」而不是「最小值」。

### 解法

```python
import random
from bisect import bisect_left, insort


def max_sum_submatrix(matrix: list[list[int]], k: int) -> int:
    if len(matrix) > len(matrix[0]):
        matrix = [list(col) for col in zip(*matrix)]   # 外層枚舉較小的一維
    m, n = len(matrix), len(matrix[0])
    best = float("-inf")
    for top in range(m):
        col = [0] * n
        for bottom in range(top, m):
            for c in range(n):
                col[c] += matrix[bottom][c]
            # Kadane：若最大子陣列和已經 <= k，就是這一對列的最佳值
            cur = kadane = float("-inf")
            for v in col:
                cur = v if cur < 0 else cur + v
                kadane = max(kadane, cur)
            if kadane <= k:
                best = max(best, kadane)
            else:
                prefixes, running = [0], 0
                for v in col:
                    running += v
                    i = bisect_left(prefixes, running - k)   # 最小的 P[l] >= P[r] - k
                    if i < len(prefixes):
                        best = max(best, running - prefixes[i])
                    insort(prefixes, running)
            if best == k:
                return k
    return best


def brute(matrix, k):
    m, n = len(matrix), len(matrix[0])
    best = float("-inf")
    for r1 in range(m):
        for r2 in range(r1, m):
            for c1 in range(n):
                for c2 in range(c1, n):
                    s = sum(matrix[r][c] for r in range(r1, r2 + 1) for c in range(c1, c2 + 1))
                    if s <= k:
                        best = max(best, s)
    return best


assert max_sum_submatrix([[1, 0, 1], [0, -2, 3]], 2) == 2
assert max_sum_submatrix([[2, 2, -1]], 3) == 3
assert max_sum_submatrix([[5, -6]], 4) == -1
assert max_sum_submatrix([[-3]], -3) == -3
assert max_sum_submatrix([[2], [2], [-1]], 3) == 3            # 轉置的情況
for _ in range(300):
    m, n = random.randint(1, 4), random.randint(1, 4)
    A = [[random.randint(-5, 5) for _ in range(n)] for _ in range(m)]
    kk = random.randint(-5, 8)
    if brute(A, kk) != float("-inf"):                          # 題目保證有解
        assert max_sum_submatrix(A, kk) == brute(A, kk)
print("all tests passed")
```

### 複雜度與邊界

令 a = min(m, n)、b = max(m, n)。列對有 O(a²) 組，每組壓縮與 Kadane 是 O(b)，排序查詢在平衡樹中是 O(b log b)，所以總時間 O(a² · b log b)；用 `insort` 時插入的搬移成本使最差情況成為 O(a² · b²)，但在 b ≤ 100 時這個搬移非常快。空間 O(b)。邊界情況：k 為負數時，`P[r] − k` 比 `P[r]` 還大，可能找不到後繼，所以要檢查 `i < len(prefixes)`；剛好等於 k 的子矩形是合法的，`bisect_left` 找的是 ≥，能找到等於下限的值；Kadane 的 `cur` 初始為 −∞，讓全負數的 `col` 也能得到正確的最大值（最大的單一元素）；`best == k` 時提早回傳是正確的，因為不可能有更大的合法值。

### Follow-up

> [!question]- F1. 如果列數遠大於行數（例如 m = 10⁴、n = 10）呢？
> 外層要枚舉**較小**的那一維。若照原樣固定上下列，有 m² / 2 = 5 × 10⁷ 對，太多；改成固定左右兩行（n² / 2 = 50 對），把每一列在這兩行之間的和壓成長度 m 的陣列，對它做排序後繼查詢，每對 O(m log m)，總共 O(n² · m log m)。程式中就是先轉置矩陣，這正是解法第一行在做的事，也是原題進階問題的答案。

> [!question]- F2. Python 沒有 TreeSet，怎麼做到嚴格的 O(log n) 插入與後繼查詢？
> 對固定的一對列，所有前綴值 `P[0..n]` 事先就能算出，所以可以離線做座標壓縮：排序去重得到 `vals`，用 Fenwick tree 記錄「哪些值已經插入」。查詢「≥ x 的最小已插入值」時，先用 `bisect_left(vals, x)` 得到位置 p，再用 Fenwick 算出位置 < p 的已插入個數 c，最後用 Fenwick 的 binary lifting 找第 c + 1 個已插入的值；插入就是在對應位置加一。每次操作 O(log n)，每對列 O(n log n)。
> ```python
> from bisect import bisect_left
> from itertools import accumulate
>
> def max_sum_no_larger(arr, k):
>     P = list(accumulate(arr, initial=0))
>     vals = sorted(set(P))
>     m, LOG = len(vals), len(vals).bit_length()
>     tree = [0] * (m + 1)
>     def add(i):
>         i += 1
>         while i <= m:
>             tree[i] += 1
>             i += i & -i
>     def count_below(i):                  # 已插入且位置 < i 的個數
>         s = 0
>         while i > 0:
>             s += tree[i]
>             i -= i & -i
>         return s
>     def kth(c):                          # 第 c 個已插入值的位置（0-indexed）
>         pos = 0
>         for b in range(LOG, -1, -1):
>             nxt = pos + (1 << b)
>             if nxt <= m and tree[nxt] < c:
>                 pos, c = nxt, c - tree[nxt]
>         return pos
>     best, inserted = float("-inf"), 1
>     add(bisect_left(vals, 0))
>     for cur in P[1:]:
>         c = count_below(bisect_left(vals, cur - k))
>         if c < inserted:
>             best = max(best, cur - vals[kth(c + 1)])
>         add(bisect_left(vals, cur))
>         inserted += 1
>     return best
> ```

> [!question]- F3. 如果條件改成「和恰好等於 k」，要回傳是否存在或個數呢？
> 等式條件就不需要排序結構了，降維後直接用核心題 2 的 hash map：個數就是難題 1（1074），存在性則是查到任何一個就提早回傳。每對列 O(n)，總共 O(a² · b)，比本題少一個 log。這個對比說明了本題的難點：「≤ k」讓查詢從「找一個值」變成「找一個範圍中的最小值」，hash map 必須換成有序結構。

> [!question]- F4. 如果矩陣的元素都非負呢？
> 非負時壓縮後的 `col` 也非負，窗口和隨右端點單調增加，於是「≤ k 的最大子陣列和」可以用 sliding window：右端點前進一格，若窗口和超過 k 就縮左端點，每次更新最佳值，O(b)。總時間 O(a² · b)，不需要排序結構。面試時先問「元素會不會是負的」，正是為了判斷能不能用這個更簡單的解；有負數時必須回到前綴和加後繼查詢。

> [!question]- F5. 如果要找「和最接近 k」（可以大於 k）的子矩形呢？
> 對每個 r，最接近的 `P[r] − P[l]` 對應到 `P[l]` 最接近 `P[r] − k`，所以要在排序結構中同時查**後繼**（≥ `P[r] − k` 的最小值，使和 ≤ k）和**前驅**（< `P[r] − k` 的最大值，使和 > k），兩者取與 k 的差距較小者。`bisect_left` 回傳的位置 i 是後繼，i − 1 就是前驅，多一次比較而已，複雜度不變。這是「排序結構 + 前綴和」最一般的形式，一維版本也常以「最接近 0 的子陣列和」出現。

### 心得

關鍵突破有兩層：先用難題 1 的降維把二維變一維，再把「和 ≤ k 的最大值」改寫成「在之前的前綴中找 ≥ `P[r] − k` 的最小值」，也就是有序結構上的後繼查詢。它和難題 1 的唯一差別是條件從等式變成不等式，工具就從 hash map 升級成排序結構；和 F4 的對比則說明，不等式條件在非負時可以用 sliding window，有負數時才需要有序結構。面試時要主動處理兩件事：外層枚舉較小的一維（原題的進階問題），以及說清楚 Python 的 `insort` 插入是 O(n) 搬移，若面試官要求嚴格的 log，就提出座標壓縮加 Fenwick tree。

## 難題 3｜862. Shortest Subarray with Sum at Least K｜Hard

### 題目

給一個整數陣列 `nums`（**可以有負數**）和一個正整數 `k`，回傳和**至少為 k** 的最短非空連續子陣列長度；若不存在，回傳 −1。限制：`1 <= len(nums) <= 10⁵`，`-10⁵ <= nums[i] <= 10⁵`，`1 <= k <= 10⁹`。

- 範例 1：`nums = [1]`、`k = 1`，回傳 `1`。
- 範例 2：`nums = [1, 2]`、`k = 4`，回傳 `−1`，總和只有 3。
- 範例 3：`nums = [2, -1, 2]`、`k = 3`，回傳 `3`：只有整個陣列的和 3 達標。
- 範例 4：`nums = [3, -2, 5, -1, 4]`、`k = 7`，回傳 `3`：`[5, -1, 4]` 的和是 8；長度 2 的子陣列最大和只有 4。

### 提示

> [!tip]- 提示 1
> 如果陣列全是正數，這就是 sliding window（209 題）。負數破壞了什麼？試著用前綴和 P 把條件寫成 `P[r] − P[l] ≥ k`，你要對每個 r 找最大的 l。

> [!tip]- 提示 2
> 考慮兩個候選左端點 i < j。如果 `P[i] ≥ P[j]`，對任何未來的 r，j 都比 i 好：j 更靠右（子陣列更短），而且 `P[j]` 更小（子陣列和更大）。所以 i 可以永遠丟掉。

> [!tip]- 提示 3
> 維護一個 deque，裡面的索引遞增、P 值也嚴格遞增。對新的 r：先從前端彈出所有 `P[r] − P[front] ≥ k` 的索引並更新答案（它們之後只會配出更長的子陣列）；再從後端彈出所有 `P[back] ≥ P[r]` 的索引；最後把 r 放進後端。

### 詳解

**為什麼直覺做法不夠**。暴力是 O(n²) 枚舉。sliding window 的做法（和夠了就縮左邊）依賴「窗口縮短，和就變小」：全正數時成立，但有負數時，縮掉一個負數反而讓和變大，窗口的伸縮不再對應和的增減。範例 4 中，窗口 `[3, -2, 5]` 和是 6，擴到 `[3, -2, 5, -1]` 和是 5，再擴到整個陣列是 9 ≥ 7，此時縮左邊丟掉 3 得到 6 < 7，sliding window 就停止縮了；但真正的答案 `[5, -1, 4]` 需要同時丟掉 3 和 −2，而丟掉 3 之後的中間狀態不合法，窗口無法跨過它。前綴和加 hash map 也不行，因為條件是不等式。

**突破點：哪些前綴值得當左端點**。把條件寫成 `P[r] − P[l] ≥ k`、要最小化 `r − l`。對固定的 r，我們想要「最右邊的、P 值夠小的 l」。兩個觀察決定了哪些 l 值得保留。第一，**被支配的候選可以丟**：若 i < j 且 `P[i] ≥ P[j]`，那麼對任何 r > j，用 j 當左端點的和 `P[r] − P[j]` 不小於用 i 的，長度還更短，所以 i 永遠不會是最佳解，可以丟掉。丟完之後，留下的候選在索引遞增的同時，P 值也嚴格遞增，這就是 monotonic deque（第 6 章難題 2 的 sliding window maximum 用的是同一種結構）。第二，**用過的候選可以丟**：若某個候選 i 已經滿足 `P[r] − P[i] ≥ k`，它和 r 配出長度 `r − i`；之後任何 r' > r 和 i 配出的長度只會更長，所以 i 的最佳搭檔就是 r，記錄答案後就可以把 i 從前端丟掉。

**為什麼從前端彈**。deque 中的 P 值由前往後遞增，前端是 P 值最小的候選，若連它都不滿足 `P[r] − P[front] ≥ k`，後面的更不可能滿足。反過來，只要前端滿足，就記錄並彈出，再檢查新的前端，直到不滿足為止；被彈出的候選中，越靠後的長度越短，所以最後彈出的那一個給出這一輪最短的答案，但每一個都要拿來更新答案。

**為什麼是 O(n)**。每個索引最多進 deque 一次、出 deque 一次（不論從前端還是後端），所以總操作數是 O(n)。正確性來自前面兩個觀察：被丟掉的候選，要嘛被另一個候選支配，要嘛已經找到了最佳搭檔，丟掉它們不會錯過任何更短的答案。

```text
nums = [3, -2, 5, -1, 4]，k = 7
P    = [0, 3, 1, 6, 5, 9]（索引 0..5）

 r  P[r]  前端彈出（P[r]−P[front] >= 7）    後端彈出（P[back] >= P[r]）   deque（索引:P）     最短
 0   0    —                                  —                             [0:0]               ∞
 1   3    3−0=3 不夠                         —                             [0:0, 1:3]          ∞
 2   1    1−0=1 不夠                         彈出 1（P=3 >= 1）             [0:0, 2:1]          ∞
 3   6    6−0=6 不夠                         —                             [0:0, 2:1, 3:6]     ∞
 4   5    5−0=5 不夠                         彈出 3（P=6 >= 5）             [0:0, 2:1, 4:5]     ∞
 5   9    9−0=9 ✓ 長度 5，彈出 0             —                             [4:5, 5:9]          3
          9−1=8 ✓ 長度 3，彈出 2
          9−5=4 不夠，停

答案 3：l = 2、r = 5，nums[2:5] = [5, -1, 4]
```

r = 2 那一步是整題的關鍵：索引 1 的前綴是 3，索引 2 的前綴是 1，更右也更小，所以索引 1 被支配而彈出。若沒有這一步，deque 會是 `[0, 1, 2, …]`，P 值不單調；到 r = 5 時彈出 0 之後，前端是索引 1（P = 3），9 − 3 = 6 < 7 就停了，永遠看不到後面的索引 2，答案會錯成 5。

### 解法

```python
import random
from collections import deque


def shortest_subarray(nums: list[int], k: int) -> int:
    n = len(nums)
    P = [0] * (n + 1)
    for i, x in enumerate(nums):
        P[i + 1] = P[i] + x
    best = n + 1
    dq = deque()                         # 索引遞增，P 值嚴格遞增
    for r in range(n + 1):
        while dq and P[r] - P[dq[0]] >= k:
            best = min(best, r - dq.popleft())   # 前端找到最佳搭檔，之後不再需要
        while dq and P[dq[-1]] >= P[r]:
            dq.pop()                     # 被 r 支配：r 更右、P 更小
        dq.append(r)
    return best if best <= n else -1


def brute(nums, k):
    n, best = len(nums), float("inf")
    for l in range(n):
        s = 0
        for r in range(l, n):
            s += nums[r]
            if s >= k:
                best = min(best, r - l + 1)
                break
    return best if best != float("inf") else -1


assert shortest_subarray([1], 1) == 1
assert shortest_subarray([1, 2], 4) == -1
assert shortest_subarray([2, -1, 2], 3) == 3
assert shortest_subarray([3, -2, 5, -1, 4], 7) == 3
assert shortest_subarray([-5, -1], 1) == -1
assert shortest_subarray([84, -37, 32, 40, 95], 167) == 3
for _ in range(500):
    arr = [random.randint(-6, 6) for _ in range(random.randint(1, 10))]
    kk = random.randint(1, 12)
    assert shortest_subarray(arr, kk) == brute(arr, kk)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：建前綴和 O(n)，每個索引進出 deque 各最多一次。空間 O(n)：前綴陣列與 deque。邊界情況：全為負數時沒有任何子陣列達標，回傳 −1；單一元素就 ≥ k 時答案是 1；後端彈出用 `>=` 而不是 `>`，因為 P 值相等時右邊的候選長度更短，左邊的被支配；前綴和的範圍可達 ±10¹⁰，超過 32 位元，Java／C++ 要用 64 位元整數；`best` 初始化為 n + 1 當作「不存在」的哨兵，最後再轉成 −1。

### Follow-up

> [!question]- F1. 如果陣列全是正數（或非負）呢（209. Minimum Size Subarray Sum）？
> 這時 sliding window 就夠了：右端點每前進一格，只要窗口和 ≥ k 就記錄長度並縮左端點。因為元素非負，縮短窗口只會讓和變小，「和夠了就縮」不會錯過答案。時間 O(n)、空間 O(1)，不需要前綴陣列和 deque。也可以用前綴和加 binary search（非負時前綴和遞增），O(n log n)，這是第 6 章核心題 2 的 F1 寫過的版本，但 sliding window 最好。

> [!question]- F2. 如果要的是和至少為 k 的**最長**子陣列呢？
> 對固定的 r，要找最左邊的、`P[l] ≤ P[r] − k` 的 l。候選左端點只需要「前綴最小值」：從左往右掃，只保留 P 值創新低的索引，形成一個 P 值嚴格遞減的堆疊（比它更右但 P 不更小的索引，永遠不會比它好）。接著讓 r 從右往左掃，只要 `P[r] − P[堆疊頂] ≥ k` 就更新答案並彈出堆疊頂（更左的 r 只會配出更短的長度）。兩趟都是 O(n)。這和 962. Maximum Width Ramp 是同一個技巧，差別只是把條件 `nums[l] ≤ nums[r]` 換成前綴差 ≥ k。

> [!question]- F3. 如果要數有幾個子陣列的和至少為 k 呢？
> 計數需要知道每個 r 之前有幾個 `P[l] ≤ P[r] − k`，這是範圍計數查詢，deque 只保留了部分候選，不夠用。做法是把所有前綴值座標壓縮，用 Fenwick tree 記錄每個值出現的次數：對每個 r，先查「≤ `P[r] − k` 的個數」加進答案，再把 `P[r]` 加入。時間 O(n log n)。這就是 327 題（第 26 章難題 1）的單邊版本。

> [!question]- F4. 如果陣列是環狀的，子陣列可以從尾端繞回開頭（但長度不超過 n）呢？
> 把陣列複製一份接在後面，在長度 2n 的前綴和上做同樣的 deque，但多一條規則：前端索引與 r 的距離超過 n 時就從前端彈出，因為子陣列長度不能超過 n。被彈出的索引對之後的 r 距離只會更遠，所以丟掉是安全的。每個索引仍然最多進出一次，時間 O(n)、空間 O(n)。這是第 6 章難題 2（239）「窗口大小限制」與本題「前綴支配」的組合。

### 心得

關鍵突破是看出「左端點候選可以被支配」：更右而前綴更小的候選，在任何未來的右端點上都更好，所以留下的候選前綴必然嚴格遞增，形成 monotonic deque；再加上「已經配到的左端點不會再有更好的搭檔」，前端也能安全彈出。它把三個想法串起來：前綴和把子陣列和變成兩數之差（本章）、不等式條件需要有序結構（難題 2）、單調性讓有序結構退化成 deque（第 6 章難題 2、第 10 章）。面試時先說明 sliding window 為什麼在負數時失效（最好舉出範例 4 那種需要「跨過」不合法中間狀態的例子），再說兩條彈出規則與它們的理由，最後才寫程式。

## 難題 4｜1371. Find the Longest Substring Containing Vowels in Even Counts｜Medium

### 題目

給一個只含小寫英文字母的字串 `s`，回傳最長的子字串長度，使得這個子字串中五個母音 `a`、`e`、`i`、`o`、`u` **每一個都出現偶數次**（0 次也算偶數）。子音的出現次數不受限制。限制：`1 <= len(s) <= 5 × 10⁵`。

- 範例 1：`s = "eleetminicoworoep"`，回傳 `13`：子字串 `"leetminicowor"` 中 e、i、o 各出現兩次，a、u 出現 0 次。
- 範例 2：`s = "leetcodeisgreat"`，回傳 `5`：`"leetc"` 中 e 出現兩次，其他母音 0 次。
- 範例 3（邊界）：`s = "bcbcbc"`，回傳 `6`，沒有母音，整個字串都合法。
- 範例 4（邊界）：`s = "a"`，回傳 `0`，唯一的子字串中 a 出現 1 次；`s = "aa"` 回傳 `2`。

### 提示

> [!tip]- 提示 1
> 「偶數次」只在乎奇偶性。子字串 `s[l:r]` 中某個母音出現偶數次，等價於前 r 個字元與前 l 個字元中，這個母音出現次數的奇偶性相同。

> [!tip]- 提示 2
> 五個母音的奇偶性可以壓成一個 5 bit 的整數 mask，每遇到一個母音就把對應的 bit 做 XOR。子字串合法 ⇔ 兩端的 mask 相同。

> [!tip]- 提示 3
> 現在是「找兩個相等的前綴 key，距離最遠」，和核心題 3（525）完全一樣：記錄每個 mask 第一次出現的位置，mask 只有 32 種，可以用長度 32 的陣列；空前綴的 mask 是 0，位置記為 −1。

### 詳解

**為什麼直覺做法不夠**。暴力是枚舉所有子字串，對每個子字串數五個母音，O(n²) 甚至 O(n³)；n = 5 × 10⁵ 時連 O(n²) 都是 2.5 × 10¹¹，完全不可行。sliding window 也不適用：「每個母音偶數次」不是單調條件，窗口加入一個 e 會讓它從合法變不合法，再加入一個 e 又變回合法，無法決定何時該縮左邊。直接套前綴和也有問題：五個母音各自有一個計數，條件是「五個差值都是偶數」，不是單一數字相等。

**突破點：只保留奇偶性，壓成 bitmask**。對每個母音 v，令 `cnt_v(i)` 為前 i 個字元中 v 的個數。`s[l:r]` 中 v 出現偶數次 ⇔ `cnt_v(r) − cnt_v(l)` 是偶數 ⇔ `cnt_v(r) % 2 == cnt_v(l) % 2`。所以我們不需要真正的計數，只需要每個母音在每個前綴的奇偶性，一個 bit 就夠了。把五個 bit 合成一個整數 `mask(i)`：a 是 bit 0、e 是 bit 1、i 是 bit 2、o 是 bit 3、u 是 bit 4。讀到母音時對應的 bit 翻轉（`mask ^= 1 << b`），讀到子音時 mask 不變。五個條件同時成立 ⇔ `mask(l) == mask(r)`，問題就變成核心題 3 的「找兩個相等的 key，距離最遠」。

**為什麼 XOR 是對的運算**。XOR 是「模 2 的加法」，而模 2 的加法有反元素（就是自己），所以它和前綴和一樣能「相減」：`mask(r) ^ mask(l)` 就是 `s[l:r]` 中每個母音出現次數的奇偶性，等於 0 代表全部是偶數。這也是 7.6 節說的：只要運算有反元素，前綴的技巧就成立。key 只有 2⁵ = 32 種，所以用長度 32 的陣列記錄第一次出現的位置，比 hash map 更快，空間 O(1)。

**正確性**。和 525 相同：對每個 r，最長的合法子字串的左端點是 `mask(r)` 第一次出現的位置，因為同一個 mask 越早出現，配出來的子字串越長。空前綴 mask 為 0、位置 −1，讓「從開頭開始就合法」的子字串（範例 2 的 `"leetc"`）也能被算到。所有 r 的候選取最大值就是答案。

```text
s = "eleetminicoworoep"，bit 順序（由高到低）u o i e a
first[00000] = -1

 i  字元  mask    第一次？         候選長度
 0   e   00010   是，first=0
 1   l   00010   否（first=0）      1
 2   e   00000   否（first=-1）     3
 3   e   00010   否（first=0）      3
 4   t   00010   否                 4
 5   m   00010   否                 5
 6   i   00110   是，first=6
 7   n   00110   否（first=6）      1
 8   i   00010   否（first=0）      8
 9   c   00010   否                 9
10   o   01010   是，first=10
11   w   01010   否（first=10）     1
12   o   00010   否（first=0）     12
13   r   00010   否（first=0）     13 ★
14   o   01010   否（first=10）     4
15   e   01000   是，first=15
16   p   01000   否（first=15）     1

答案 13：mask(14) = mask(1) = 00010（以前綴長度計），子字串 s[1:14] = "leetminicowor"
```

i = 13 的 mask 是 00010（只有 e 是奇數次），它第一次出現在 i = 0（讀完第一個 e 之後）。所以從 i = 1 到 i = 13 這一段，e 的奇偶性沒有變、其他母音的奇偶性也沒有變，代表每個母音在這段中都出現偶數次。表中也能看到 i = 2 時 mask 回到 00000，和空前綴配對，得到從開頭開始的 `"ele"`，長度 3。

### 解法

```python
import random


def find_the_longest_substring(s: str) -> int:
    bit = {"a": 1, "e": 2, "i": 4, "o": 8, "u": 16}
    first = [-2] * 32                 # -2 代表這個 mask 還沒出現過
    first[0] = -1                     # 空前綴
    mask = best = 0
    for i, ch in enumerate(s):
        mask ^= bit.get(ch, 0)        # 子音不改變 mask
        if first[mask] == -2:
            first[mask] = i
        else:
            best = max(best, i - first[mask])
    return best


def brute(s):
    best = 0
    for l in range(len(s)):
        for r in range(l + 1, len(s) + 1):
            if all(s[l:r].count(v) % 2 == 0 for v in "aeiou"):
                best = max(best, r - l)
    return best


assert find_the_longest_substring("eleetminicoworoep") == 13
assert find_the_longest_substring("leetcodeisgreat") == 5
assert find_the_longest_substring("bcbcbc") == 6
assert find_the_longest_substring("a") == 0
assert find_the_longest_substring("aa") == 2
assert find_the_longest_substring("aeiouaeiou") == 10
for _ in range(300):
    t = "".join(random.choice("aeb") for _ in range(random.randint(1, 12)))
    assert find_the_longest_substring(t) == brute(t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：一次掃描，每步一次 XOR 與一次陣列存取。空間 O(1)：`first` 固定 32 格，`bit` 固定 5 個鍵。邊界情況：沒有母音的字串 mask 永遠是 0，每一步都和空前綴配對，答案是 n；只有一個母音時 mask 從頭到尾都不是 0，只能在字元之間配對；用 −2 而不是 −1 當「未出現」的標記，因為 −1 已經代表空前綴。n 到 5 × 10⁵ 時 Python 的迴圈約需零點幾秒，若要更快，可以先把字串轉成 mask 的變化序列，但在面試中這個寫法已經足夠。

### Follow-up

> [!question]- F1. 如果要數有幾個子字串滿足「每個母音都出現偶數次」呢？
> 把「第一次出現的位置」換成「出現次數」：`count = [0] * 32`、`count[0] = 1`，對每個前綴先把 `count[mask]` 加進答案，再把 `count[mask]` 加一。這是核心題 2 的模板，只是 key 從前綴和換成 mask。時間 O(n)、空間 O(1)。等價地，答案是 Σ C(c_m, 2)，c_m 是每個 mask 出現的次數（含空前綴）。

> [!question]- F2. 如果條件放寬成「至多一個母音出現奇數次」呢？
> 合法 ⇔ `mask(l) ^ mask(r)` 是 0 或只有一個 bit 為 1。所以對每個 r，除了查 `first[mask]`，還要查五個 `first[mask ^ (1 << b)]`，取最長的那個，每步 6 次查詢，O(6n)。計數版本就是 1915. Number of Wonderful Substrings（字母 a 到 j，10 個 bit，數「至多一個字母奇數次」的子字串），每步 11 次查詢，O(11n)。1542. Longest Awesome Substring（數字字串、能重排成回文的最長子字串）也是同一個結構，因為「能重排成回文」⇔「至多一個字元出現奇數次」。

> [!question]- F3. 如果改成「每個母音出現的次數都是 3 的倍數」呢？
> 奇偶性換成「模 3 的餘數」，每個母音需要 3 種狀態，五個母音共 3⁵ = 243 種。把狀態編碼成以 3 為底的五位數：讀到第 b 個母音時，把第 b 位加一並取模 3，也就是 `key = key − d·3^b + ((d + 1) % 3)·3^b`，d 是該位目前的值。其餘完全一樣：存每個 key 第一次出現的位置，O(n) 時間、O(243) 空間。這說明 bitmask 只是「模 2」的特例，一般的「計數模 m」條件都能用 m 進位的狀態編碼。

> [!question]- F4. 如果要求 26 個字母都出現偶數次呢？
> mask 變成 26 bit，共 2²⁶ ≈ 6.7 × 10⁷ 種，用陣列記錄第一次出現的位置要佔數百 MB，不划算。但實際出現的 mask 最多只有 n + 1 種，所以改用 hash map，時間 O(n)、空間 O(min(n, 2²⁶))。面試時可以說：key 的空間小（32、1024）時用陣列，key 的空間大時用 hash map，兩者的演算法完全相同，只是存放方式不同。

### 心得

關鍵突破是「偶數次只在乎奇偶性，而奇偶性的前綴可以用 XOR 壓成一個 mask」，於是五個條件合併成一個等式 `mask(l) == mask(r)`，問題回到核心題 3 的「最早出現位置」模板。它展示了本章最重要的一個想法：子陣列條件只要能寫成「兩端的某個 key 相等」，就是 O(n) 的前綴 + hash map；設計 key 是整個解法的核心，後面的程式幾乎都一樣。面試時先說明為什麼 sliding window 不行（條件不單調），再提出奇偶性與 XOR，最後主動提到 F2 的「至多一個奇數」變形，展現你理解 key 之間「只差一個 bit」的查詢方式。

## 難題 5｜2281. Sum of Total Strength of Wizards｜Hard

### 題目

有 n 位巫師排成一列，第 i 位的力量是 `strength[i]`（正整數）。對一段連續的巫師（子陣列），定義它的**總力量**為「這段中最弱的力量」乘以「這段所有力量的總和」。請回傳所有非空連續子陣列的總力量之和，結果對 10⁹ + 7 取模。限制：`1 <= len(strength) <= 10⁵`，`1 <= strength[i] <= 10⁹`。

- 範例 1：`strength = [1, 3, 1, 2]`，回傳 `44`。例如子陣列 `[3, 1, 2]` 的總力量是 1 × 6 = 6，`[3]` 是 3 × 3 = 9；十個子陣列的總力量相加是 44。
- 範例 2：`strength = [5, 4, 6]`，回傳 `213`：`[5]` 25、`[4]` 16、`[6]` 36、`[5, 4]` 4 × 9 = 36、`[4, 6]` 4 × 10 = 40、`[5, 4, 6]` 4 × 15 = 60，總和 213。
- 範例 3（邊界）：`strength = [7]`，回傳 `49`。
- 範例 4（邊界）：`strength = [2, 2]`，回傳 `4 + 4 + 2 × 4 = 16`；最小值重複時，每個子陣列只能被計算一次。

### 提示

> [!tip]- 提示 1
> 子陣列有 O(n²) 個，不能逐一計算。換個角度：對每個位置 i，考慮所有「以 strength[i] 為最小值」的子陣列，它們的貢獻是 `strength[i] × (這些子陣列的和的總和)`。

> [!tip]- 提示 2
> 用 monotonic stack 找出 i 左邊第一個嚴格更小的位置 L、右邊第一個小於或等於的位置 R。以 i 為最小值的子陣列，就是左端點 l ∈ (L, i]、右端點 r ∈ [i, R) 的所有組合。一邊用嚴格、一邊用非嚴格，避免重複計算相同的最小值。

> [!tip]- 提示 3
> 子陣列和是 `P[r + 1] − P[l]`。對所有 (l, r) 組合求和，會得到 `(i − L) × Σ P[r + 1] − (R − i) × Σ P[l]`，而這兩個 Σ 都是前綴陣列 P 的區間和，所以再建一層前綴和 PP，就能 O(1) 算出。

### 詳解

**為什麼直覺做法不夠**。暴力是固定左端點，往右延伸時維護目前的最小值與總和，每個子陣列 O(1)，總共 O(n²)；n = 10⁵ 時是 5 × 10⁹ 個子陣列，太慢。只用 monotonic stack 的貢獻法（第 10 章難題 5 的 907 題 Sum of Subarray Minimums）可以 O(n) 算出「所有子陣列最小值的和」，因為那題每個子陣列只貢獻 `min`，以 i 為最小值的子陣列有 `(i − L) × (R − i)` 個，直接相乘即可。但本題每個子陣列貢獻的是 `min × sum`，不同子陣列的 sum 不同，不能只數個數，必須算出「這些子陣列的和的總和」。

**第一步：把每個子陣列歸給唯一的最小值**。對每個 i，令 L 為 i 左邊第一個 `strength[L] < strength[i]` 的位置（不存在時 L = −1），R 為 i 右邊第一個 `strength[R] <= strength[i]` 的位置（不存在時 R = n）。左端點 l ∈ [L + 1, i]、右端點 r ∈ [i, R − 1] 的子陣列，都以 `strength[i]` 為最小值。若有多個位置的值都等於最小值，一邊嚴格、一邊不嚴格的規則讓子陣列只歸給其中**最右邊**的那一個：對較左的那個最小值，R 會停在較右的那個，於是它的範圍不包含較右的位置；範例 4 的 `[2, 2]` 正是用來檢查這一點。L、R 各用一次 monotonic stack 求出，O(n)。

**第二步：用前綴的前綴算出「和的總和」**。令 P 為前綴和（`P[t]` = 前 t 個元素的和），子陣列 `[l, r]` 的和是 `P[r + 1] − P[l]`。對所有 l ∈ [L + 1, i]、r ∈ [i, R − 1] 求和：

```text
Σ_l Σ_r (P[r+1] − P[l])
  = (l 的個數) × Σ_r P[r+1]  −  (r 的個數) × Σ_l P[l]
  = (i − L) × (P[i+1] + … + P[R])  −  (R − i) × (P[L+1] + … + P[i])
```

每個 `P[r + 1]` 被所有 l 共用，所以乘上 l 的個數 `i − L`；每個 `P[l]` 被所有 r 共用，所以乘上 r 的個數 `R − i`。兩個括號都是 P 的連續區間和，令 `PP[t] = P[0] + … + P[t − 1]`，就有 `P[i+1] + … + P[R] = PP[R + 1] − PP[i + 1]`、`P[L+1] + … + P[i] = PP[i + 1] − PP[L + 1]`，各 O(1)。最後乘上 `strength[i]` 就是 i 的貢獻。

**正確性**。每個子陣列都有唯一的「最右邊的最小值」位置 i，而且它的左右端點恰好落在 i 的範圍 (L, i] 與 [i, R) 中，所以每個子陣列被恰好計算一次；對每個 i，代數展開是恆等式，不依賴元素的正負。Python 的大整數讓我們可以先精確計算再取模；在 Java／C++ 中必須每一步取模，而且減法後要加上模數避免負數。

```text
strength = [1, 3, 1, 2]
P  = [0, 1, 4, 5, 7]          （P[t] = 前 t 個的和）
PP = [0, 0, 1, 5, 10, 17]     （PP[t] = P[0] + … + P[t−1]）

 i  值   L   R   l 範圍   r 範圍   正項 (i−L)·ΣP[r+1]   負項 (R−i)·ΣP[l]   和的總和   ×值
 0   1  -1   2   [0,0]    [0,1]    1 × (1+4) = 5         2 × 0 = 0            5         5
 1   3   0   2   [1,1]    [1,1]    1 × 4 = 4             1 × 1 = 1            3         9
 2   1  -1   4   [0,2]    [2,3]    3 × (5+7) = 36        2 × (0+1+4) = 10    26        26
 3   2   2   4   [3,3]    [3,3]    1 × 7 = 7             1 × 5 = 5            2         4
                                                                         總和 = 44

i = 2 的六個子陣列（最小值都是索引 2 的 1）：
  [1,3,1]=5  [1,3,1,2]=7  [3,1]=4  [3,1,2]=6  [1]=1  [1,2]=3   → 和的總和 26 ✓
```

i = 0 的 R 是 2：索引 2 的值也是 1，等於 `strength[0]`，所以 R 停在 2，`[1, 3, 1]` 這種同時包含兩個 1 的子陣列不歸給 i = 0，而是歸給 i = 2（它的 L 是 −1，因為左邊沒有嚴格更小的值）。逐一列出 i = 2 的六個子陣列可以驗證公式：它們的和加起來是 26，和正項 36 減負項 10 一致。

### 解法

```python
import random

MOD = 10**9 + 7


def total_strength(strength: list[int]) -> int:
    n = len(strength)
    left = [-1] * n                   # 左邊第一個嚴格更小的位置
    stack = []
    for i in range(n):
        while stack and strength[stack[-1]] >= strength[i]:
            stack.pop()
        left[i] = stack[-1] if stack else -1
        stack.append(i)
    right = [n] * n                   # 右邊第一個小於或等於的位置
    stack = []
    for i in range(n - 1, -1, -1):
        while stack and strength[stack[-1]] > strength[i]:
            stack.pop()
        right[i] = stack[-1] if stack else n
        stack.append(i)

    P = [0] * (n + 1)
    for i, x in enumerate(strength):
        P[i + 1] = P[i] + x
    PP = [0] * (n + 2)                # PP[t] = P[0] + ... + P[t-1]
    for t in range(n + 1):
        PP[t + 1] = PP[t] + P[t]

    total = 0
    for i, v in enumerate(strength):
        L, R = left[i], right[i]
        pos = (i - L) * (PP[R + 1] - PP[i + 1])     # Σ_r P[r+1]，每項被 i-L 個 l 共用
        neg = (R - i) * (PP[i + 1] - PP[L + 1])     # Σ_l P[l]，每項被 R-i 個 r 共用
        total += v * (pos - neg)
    return total % MOD


def brute(strength):
    n, total = len(strength), 0
    for l in range(n):
        lo, s = float("inf"), 0
        for r in range(l, n):
            lo, s = min(lo, strength[r]), s + strength[r]
            total += lo * s
    return total % MOD


assert total_strength([1, 3, 1, 2]) == 44
assert total_strength([5, 4, 6]) == 213
assert total_strength([7]) == 49
assert total_strength([2, 2]) == 16
assert total_strength([10**9] * 3) == brute([10**9] * 3)      # 大數與取模
for _ in range(500):
    arr = [random.randint(1, 5) for _ in range(random.randint(1, 9))]
    assert total_strength(arr) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：兩次 monotonic stack 各 O(n)（每個索引進出堆疊一次），兩層前綴和各 O(n)，最後一次掃描 O(n)。空間 O(n)。邊界情況：只有一個元素時 L = −1、R = 1，公式給出 v × v；所有元素相同時，一邊嚴格、一邊不嚴格的規則保證每個子陣列只算一次，若兩邊都用嚴格，`[2, 2]` 這種子陣列會被兩個 2 各算一次；`PP` 長度是 n + 2，因為 R 可以是 n、要讀 `PP[n + 1]`。在 Python 中中間值可達 10³³ 的量級（PP 約 10¹⁹，再乘上長度 10⁵ 與力量 10⁹），大整數能處理但會稍慢，可以改成每步取模；在 Java／C++ 中必須每步取模，`pos − neg` 要寫成 `(pos − neg + MOD) % MOD`。

### Follow-up

> [!question]- F1. 如果每個子陣列只貢獻它的最小值（不乘總和）呢（907. Sum of Subarray Minimums）？
> 以 i 為最小值的子陣列有 `(i − L) × (R − i)` 個，貢獻是 `strength[i] × (i − L) × (R − i)`，不需要前綴和，O(n)。L、R 的求法與嚴格／非嚴格的規則完全相同。這是第 10 章難題 5；本題就是在它的基礎上，把「個數」換成「和的總和」，因而多了一層前綴的前綴。面試中若先遇到 907，被追問「如果要乘上子陣列和呢」，就是本題。

> [!question]- F2. 如果把最小值換成最大值呢？
> 只要把兩個 monotonic stack 的比較方向反過來：L 是左邊第一個嚴格更大的位置，R 是右邊第一個大於或等於的位置。和的總和公式完全不變，因為它只依賴範圍 (L, i] 與 [i, R)，與「最小」或「最大」無關。若要算「最大值 × 和」減去「最小值 × 和」的總和（例如 2104 題 Sum of Subarray Ranges 的加權版本），兩次分別計算再相減，O(n)。

> [!question]- F3. 如果不是求總和，而是求所有子陣列中「最小值 × 和」的最大值呢（1856. Maximum Subarray Min-Product）？
> 對每個 i，以它為最小值的子陣列中，元素都是正數，所以範圍越大總和越大，最佳的就是整段 `[L + 1, R − 1]`，乘積為 `strength[i] × (P[R] − P[L + 1])`。用同樣的 monotonic stack 求出 L、R，再用一層前綴和 O(1) 算區間和，取最大值，O(n)。這裡 L、R 兩邊都可以用嚴格或非嚴格，因為求最大值不怕重複計算。注意 1856 要求先取最大值再取模，所以比較時必須用精確值，不能先取模。

> [!question]- F4. 如果力量可以是 0 或負數呢？
> 公式本身是代數恆等式，對任何整數都成立；monotonic stack 求 L、R 也不依賴正負。唯一要注意的是取模：Python 的 `%` 對負數回傳非負值，`total % MOD` 直接正確；在 Java／C++ 中，`v` 為負時 `v × (pos − neg)` 可能為負，要寫成 `((x % MOD) + MOD) % MOD`。另外，F3 那種「取最大值」的變形在有負數時就不成立了，因為範圍越大總和不一定越大，要改成在範圍內找最佳的子區間，需要額外的區間最值查詢。

### 心得

關鍵突破是把「所有子陣列的 min × sum」拆成兩層：先用 monotonic stack 把每個子陣列歸給唯一的最小值，再把一整個矩形範圍的子陣列和，用代數展開成前綴陣列的區間和，於是需要「前綴和的前綴和」。它是本章與第 10 章的交會點：907 題提供了貢獻法的骨架，本章提供了把「和的總和」變成 O(1) 的工具。面試時建議分三步講：先說貢獻法與 L、R 的嚴格／非嚴格規則（並用 `[2, 2]` 說明為什麼），再寫出 `(i − L) × ΣP[r + 1] − (R − i) × ΣP[l]` 的展開，最後說明 PP 的定義與索引。這題的程式不長，但每個索引都容易差一，所以用一個小例子手算 i 的貢獻來驗證，比直接背公式可靠得多。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 區間和查詢 | 陣列不變、大量查詢 | 長度 n + 1 的 P，`P[r] − P[l]` | 303 Range Sum Query、核心題 4（304）、1314 |
| 前綴 ⊕ 後綴分解 | 「除了自己以外」、左右兩邊各自的資訊 | 前綴與後綴各掃一次，不需要反元素 | 核心題 1（238）、2906、42 Trapping Rain Water（第 5 章難題 1） |
| 前綴 + hash map 計數 | 和為 k 的子陣列個數，有負數 | `seen[P − k]`，初始 `{0: 1}`，先查再存 | 核心題 2（560）、974、930、難題 1（1074） |
| 前綴 + 最早位置 | 「最長」的平衡子陣列、和為 k 的最長 | 存每個 key 第一次出現的位置，初始 `{0: −1}` | 核心題 3（525）、325、1124 |
| 前綴 bitmask／狀態編碼 | 奇偶性、出現次數模 m | XOR mask 或 m 進位狀態當 key | 難題 4（1371）、1915、1542 |
| 差分陣列 | 大量區間加值，最後才讀 | `diff[l] += d`、`diff[r] −= d`，最後前綴和 | 核心題 5（1094）、1109、2536（二維） |
| 二維降維 | 子矩形和的計數或最佳化 | 固定上下兩列，壓成一維的 `col` | 難題 1（1074）、難題 2（363）、最大子矩陣 |
| 不等式 + 有序結構 | 「不超過 k 的最大和」「和落在區間內的個數」 | 排序結構中找後繼，或 Fenwick tree 計數 | 難題 2（363）、327（第 26 章難題 1） |
| 不等式 + monotonic deque | 「和至少 k 的最短」，有負數 | 丟掉被支配的前綴、用過的前綴 | 難題 3（862）、F4 的環狀版本 |
| 貢獻法 + 前綴的前綴 | 對所有子陣列求「某值 × 和」的總和 | monotonic stack 求範圍，PP 算和的總和 | 難題 5（2281）、907（第 10 章難題 5）、1856 |

**下限與上限**。最簡單的形式是 303 那種純粹的區間和查詢，考的只是半開區間的索引寫對；稍微進一步是 238，考的是「拼前綴與後綴」而不是「扣掉自己」的觀念。中間層是前綴 + hash map（560、525），難點轉移到兩個地方：看出子陣列條件可以改寫成「兩端的 key 相等」，以及寫對空前綴與先查再存的細節。上限的題目難在三個方面，常常同時出現：第一，**key 不是現成的**，需要先做一次轉換，例如 525 的 0 → −1、1371 的奇偶性 bitmask；第二，**條件是不等式**，hash map 不夠用，要依照額外的結構升級成排序結構（363）、monotonic deque（862）或 Fenwick tree（327）；第三，**要和其他 pattern 組合**，例如 1074 與 363 的二維降維、2281 的 monotonic stack 加前綴的前綴。

**與其他 pattern 的關係**。和 sliding window（第 6 章）最容易混淆：兩者都處理連續子陣列，但 sliding window 需要「窗口變長、和就變大」的單調性，也就是元素非負；有負數、或條件是等式（和恰好為 k）、或是奇偶性這類不單調的條件時，前綴和才是正確的工具。反過來，元素非負而條件是不等式時，sliding window 用 O(1) 空間就能做到，不要用前綴和加 deque 殺雞用牛刀。和 hashing（第 4 章）的關係是：前綴 + hash map 本質上就是 Two Sum，只是配對的對象從「兩個元素」換成「兩個前綴」。和 binary search（第 8 章）的關係是：非負陣列的前綴和遞增，可以在上面 bisect（例如 209 的 O(n log n) 解）。差分陣列是第 9 章 sweep line 的稠密版本，查詢與修改交錯時則要升級成第 26 章的 Fenwick tree 或 segment tree。

**容易混淆之處**。第一，「子陣列」不一定要用前綴和：最大子陣列和（53）用 Kadane 就好，雖然 Kadane 也可以看成「目前前綴減去最小前綴」。第二，前綴和假設陣列不變，若題目有修改操作，前綴和的每次更新都是 O(n)，要先問清楚。第三，「子序列」（不連續）不能用前綴和，因為子序列的和不是兩個前綴相減；看到子序列通常是 DP 或排序後的貪婪。第四，二維題目先問清楚是否需要所有子矩形：只要固定大小的方塊和（1314），二維前綴和就夠了；要所有子矩形的計數或最佳化，才需要降維。

## 本章重點整理

- 前綴和的核心觀點：子陣列 `nums[l:r]` 的和是 `P[r] − P[l]`，任何子陣列問題都可以改寫成「找一對前綴」。
- 一律用長度 n + 1、`P[0] = 0` 的半開區間定義，和 Python 切片對應，空子陣列與從 0 開始的區間都不必特判。
- 差分是前綴和的反向操作：區間加值只改 `diff[l]` 與 `diff[r]`，所有修改做完後一次前綴和還原；閉區間的題目要減在 `r + 1`。
- 前綴 + hash map 模板的三個細節：初始放入空前綴、先查再存、數個數存次數／找最長存最早／找最短存最晚。
- 設計 key 是解題的核心：和為 k 用 `P − k`，整除用 `P % k`，兩種數量相等用 ±1 的和，奇偶性用 XOR bitmask，模 m 用 m 進位狀態。
- 有負數時 sliding window 失效，因為窗口和不再隨長度單調；非負且條件是不等式時，sliding window 比前綴和更省空間。
- 不等式條件要升級工具：「≤ k 的最大和」用排序結構找後繼（363），「≥ k 的最短」用 monotonic deque（862），「落在區間內的個數」用 Fenwick tree（327）。
- 862 的 deque 有兩條彈出規則：前端已配到最佳搭檔就彈出，後端被「更右且前綴更小」的新候選支配就彈出；deque 中的前綴嚴格遞增。
- 「除了自己以外」用前綴 ⊕ 後綴，不需要反元素，適用於乘積（含 0）、max、gcd 等任何有結合律的運算。
- 二維前綴和用「整塊 − 上 − 左 + 左上」；子矩形的計數或最佳化則固定上下兩列，把二維壓成一維，O(min² · max)，並讓較小的一維在外層。
- 對所有子陣列求「某值 × 和」的總和時，用 monotonic stack 把子陣列歸給唯一的位置（一邊嚴格、一邊不嚴格），再用前綴的前綴算出和的總和。
- 前綴和假設陣列不變、差分假設修改全部做完才讀取；查詢與修改交錯時，改用第 26 章的 Fenwick tree 或 segment tree。
