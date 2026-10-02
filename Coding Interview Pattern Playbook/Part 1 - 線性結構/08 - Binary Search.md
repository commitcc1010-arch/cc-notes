---
chapter: 8
title: Binary Search
part: 1
---

# 第 8 章　Binary Search

> [!abstract] 本章地圖
> **一句話**：只要能把問題改寫成「一段 False 之後接著一段 True」的單調判斷，就能每次丟掉一半的候選，用 O(log n) 次判斷找到第一個 True。
>
> **辨識訊號**：
> - 輸入已排序，或是「部分有序」（旋轉過的排序陣列、先增後減）
> - 題目明說要 O(log n)，或 n 很大、值域高達 10⁹ 而 O(n) 掃值域不可行
> - 「最小的最大值」「最大的最小值」「至少要多快、多大才做得到」
> - 「第 k 小」但候選總數是 n² 或 m·n，無法全部列出再排序
> - 存在一個「給定答案 x，能不能做到？」的檢查，而且 x 越大越容易（或越難）
>
> **核心題**：34、33、153、875、1011
>
> **難題**：4、410、668、719、2040

## 8.1 這個 Pattern 解決什麼問題

先看一個最小的例子。你有 n 個版本的程式，編號 1 到 n，某一版之後全部壞掉，你只能呼叫 `is_bad(v)` 詢問某一版壞了沒，要找出第一個壞掉的版本。最直接的做法是從 1 開始一個一個問，最差要問 n 次。可是這些答案有一個很強的結構：只要第 v 版是壞的，v 之後一定全壞；只要第 v 版是好的，v 之前一定全好。把每一版的答案排成一列，長相必定是 `F F F … F T T … T`。

有了這個結構，每問一次中間的版本就能丟掉一半。問到 `is_bad(mid)` 是 True，代表答案在 mid 或 mid 左邊，右半邊不必再看；問到 False，代表答案一定在 mid 右邊，左半邊（含 mid）可以全部丟掉。每次候選數量減半，所以 n = 10⁹ 也只需要大約 30 次詢問。這就是 binary search（二分搜尋）真正在做的事：它不是「在排序陣列裡找一個數」的專用技巧，而是「在單調的 F/T 序列中找分界點」的通用方法。

把這個觀念記住，本章所有題目都會變成同一個問題：**我的 F/T 序列是什麼？分界點代表什麼？** 排序陣列找第一個 ≥ target 的位置，序列是 `nums[i] >= target`；旋轉陣列找最小值，序列是 `nums[i] <= nums[-1]`；Koko 吃香蕉找最慢速度，序列是「速度 k 能不能在 h 小時內吃完」。差別只在 F/T 的定義與搜尋的範圍，迴圈本身一模一樣。

這也說明了 binary search 為什麼常被低估。很多題目表面上跟排序毫無關係（分配工作、切陣列、找第 k 小的乘積），但只要能寫出一個「答案 x 可不可行」的單調檢查，就能把「找最佳值」轉成「找第一個可行的 x」。前者通常需要聰明的構造，後者只需要一個 O(n) 的貪婪檢查加上 O(log 值域) 次迭代。

## 8.2 辨識訊號

| 題目特徵 | 為什麼是 binary search | 本章哪一題 |
|---|---|---|
| 排序陣列中找某個值的第一個／最後一個位置 | `nums[i] >= target` 對 i 單調 | 核心題 1（34） |
| 排序陣列被旋轉過，要求 O(log n) | 每次切一半，至少有一半是有序的；或可定義單調的「在哪一段」判斷 | 核心題 2（33）、核心題 3（153） |
| 「最小的速度／容量／時間，使得能在限制內完成」 | 可行性對答案單調：容量越大越容易裝完 | 核心題 4（875）、核心題 5（1011） |
| 「把陣列切成 k 段，最小化最大段和」 | 「最大段和 ≤ x 能否切成 ≤ k 段」對 x 單調，檢查用貪婪 | 難題 2（410） |
| 「第 k 小」而候選數為 m·n 或 n² | 「≤ x 的候選有幾個」對 x 單調，計數比列舉便宜 | 難題 3（668）、難題 4（719）、難題 5（2040） |
| 兩個排序陣列、要求 O(log(m+n)) | 在較短陣列上二分「切在哪裡」，切點的合法性是單調的 | 難題 1（4） |
| n ≤ 10⁵ 而答案值域 ≤ 10⁹ 或 10¹⁸ | O(n log 值域) 剛好可接受，O(值域) 不行 | 875、1011、410、2040 |

一個實用的反向檢查：如果你想到的檢查函式「答案 x 可不可行」不是單調的（x = 5 可行、x = 6 不可行、x = 7 又可行），binary search 就不能用，要換成 DP 或其他方法。

## 8.3 模板與原理：第一個 True

全書只需要記一個 binary search 模板：**在半開區間 `[lo, hi)` 中，找第一個讓 `pred` 為 True 的整數；如果全部是 False，回傳 `hi`**。所有「找邊界」「找最小可行答案」「找第 k 小」都直接套它；需要「最後一個 True」時用一行轉換得到。

```python
from bisect import bisect_left, bisect_right
from typing import Callable


def first_true(lo: int, hi: int, pred: Callable[[int], bool]) -> int:
    """在 [lo, hi) 中找第一個 pred 為 True 的整數；全為 False 時回傳 hi。

    前提：pred 在 [lo, hi) 上單調，形如 F F … F T T … T。
    """
    while lo < hi:
        mid = (lo + hi) // 2
        if pred(mid):
            hi = mid          # mid 可能就是答案，保留在範圍內
        else:
            lo = mid + 1      # mid 確定不是答案，連同左邊一起丟掉
    return lo


def last_true(lo: int, hi: int, pred: Callable[[int], bool]) -> int:
    """在 [lo, hi) 中找最後一個 pred 為 True 的整數；全為 False 時回傳 lo - 1。

    前提：pred 形如 T T … T F F … F。
    """
    return first_true(lo, hi, lambda x: not pred(x)) - 1


nums = [1, 3, 3, 5, 8]
assert first_true(0, len(nums), lambda i: nums[i] >= 3) == 1    # lower bound
assert first_true(0, len(nums), lambda i: nums[i] > 3) == 3     # upper bound
assert first_true(0, len(nums), lambda i: nums[i] >= 9) == 5    # 全 False，回傳 hi
assert first_true(0, 0, lambda i: True) == 0                    # 空區間
assert first_true(-10, 10, lambda x: x >= -3) == -3             # 負數範圍也成立
assert first_true(1, 10**9, lambda x: x * x >= 10**10) == 10**5 # 在答案空間上搜尋
assert last_true(0, len(nums), lambda i: nums[i] <= 3) == 2     # 最後一個 ≤ 3 的位置
assert last_true(0, 101, lambda x: x * x <= 50) == 7            # 整數平方根
assert last_true(0, len(nums), lambda i: nums[i] < 0) == -1     # 全 False
for x in range(-1, 10):
    assert first_true(0, len(nums), lambda i: nums[i] >= x) == bisect_left(nums, x)
    assert first_true(0, len(nums), lambda i: nums[i] > x) == bisect_right(nums, x)
print("all tests passed")
```

**Invariant（迴圈不變式）**。整個迴圈維持兩件事：`lo` 左邊（`< lo` 的位置）全部確定是 False；`hi` 以及它右邊（`>= hi` 的位置）全部是 True，或是超出範圍的哨兵。一開始 `lo` 左邊沒有東西、`hi` 是範圍外，兩條都自動成立。每一步：`pred(mid)` 是 True，於是 `mid` 以右都是 True（單調性），令 `hi = mid` 不破壞第二條；`pred(mid)` 是 False，於是 `mid` 以左都是 False，令 `lo = mid + 1` 不破壞第一條。迴圈結束時 `lo == hi`，左邊全 False、自己以右全 True，所以 `lo` 就是第一個 True。

**每一行為什麼這樣寫**：

- `while lo < hi`：區間 `[lo, hi)` 非空才需要繼續；`lo == hi` 時答案已經確定，不必再看。
- `mid = (lo + hi) // 2`：因為 `lo < hi`，所以 `lo <= mid < hi`，mid 一定落在範圍內，`pred(mid)` 不會越界；而且 `pred(hi)` 永遠不會被呼叫，這讓 `hi` 可以安心當作「範圍外」。Python 的 `//` 是向下取整，負數範圍也成立；在 Java／C++ 要寫成 `lo + (hi - lo) / 2` 避免溢位。
- `hi = mid`（不是 `mid - 1`）：mid 是 True，它本身可能就是第一個 True，不能丟掉。
- `lo = mid + 1`（不是 `mid`）：mid 是 False，一定不是答案；更重要的是，因為 mid 向下取整，當 `hi = lo + 1` 時 `mid == lo`，若寫 `lo = mid` 區間不會縮小，迴圈永遠不會結束。
- 每一步區間長度至少減半（`hi - lo` 從 L 變成 ⌊L/2⌋ 或 ⌈L/2⌉ − 1），所以迴圈最多執行 ⌈log₂(L+1)⌉ 次。

**`hi` 的兩種用法，同一份程式**。在索引上搜尋時，呼叫 `first_true(0, n, pred)`，回傳 `n` 代表「找不到」，pred 永遠不會碰到 `nums[n]`。在答案空間上搜尋時，通常知道上界 `hi` 一定可行（例如 Koko 用最大那堆的速度一定吃得完），就呼叫 `first_true(lo, hi, pred)`：如果 `[lo, hi)` 中都不可行，回傳的 `hi` 剛好就是那個一定可行的答案，不需要特判。這是把搜尋範圍設計成半開區間最大的好處。

**最後一個 True**。像「最大的最小值」「整數平方根」這類題目，序列長相是 `T T … T F F … F`，要找最後一個 T。上面的 `last_true` 把 pred 取反變成 `F … F T … T`，第一個 T（也就是原本的第一個 F）往左一格就是答案。也可以直接寫 `lo = mid` 的版本，但那時必須改用向上取整 `mid = (lo + hi + 1) // 2`，否則 `hi = lo + 1` 時 `mid == lo`、`lo = mid` 就會無窮迴圈。記一個模板加一行轉換，比記兩種取整規則不容易出錯。

**Python 的 `bisect`**。`bisect_left(a, x)` 就是 `first_true(0, len(a), lambda i: a[i] >= x)`，`bisect_right(a, x)` 就是 `a[i] > x` 的版本。Python 3.10 起 `bisect_left(range(lo, hi), True, key=pred)` 也能在答案空間上搜尋（`range` 支援索引，不會真的建出串列），回傳值要再加上 `lo`。面試時可以用 `bisect`，但要能說出它對應的 F/T 序列；遇到自訂判斷的題目，自己寫 `first_true` 通常更清楚。

## 8.4 兩種思維：在索引上找邊界、在答案空間上搜尋

**思維一：在索引上找邊界**。搜尋範圍是陣列的索引 `0 … n`，pred 直接讀陣列的值，例如 `nums[i] >= target`。核心題 1（34）是標準形；核心題 2、3（33、153）的陣列被旋轉過，整體不是排序的，但仍然能定義出對索引單調的判斷，例如「i 是否落在旋轉後的右段」等價於 `nums[i] <= nums[-1]`。這類題目的關鍵是**找出那條把陣列切成兩段的性質**，而不是死守「陣列要排序」。

**思維二：在答案空間上搜尋**。題目要的是某個最佳數值（最慢速度、最小容量、最小的最大段和、第 k 小的數），直接構造很難，但「給定 x，做得到嗎？」很好檢查，而且可行性對 x 單調。於是搜尋範圍不再是索引，而是答案的值域 `[下界, 上界]`，pred 是一個 O(n) 左右的檢查函式。核心題 4、5（875、1011）是標準形；難題 2（410）把檢查換成「能否切成 ≤ k 段」；難題 3–5（668、719、2040）把檢查換成「≤ x 的候選是否至少 k 個」，也就是「第 k 小 = 第一個讓 count(≤ x) ≥ k 的 x」。

```text
思維一：在索引上找邊界（34，target = 8）
index:   0  1  2  3  4  5
nums:    5  7  7  8  8  10
pred:    F  F  F  T  T  T      pred(i) = nums[i] >= 8
                   ↑ 第一個 T = 3

思維二：在答案空間上搜尋（875，piles = [3, 6, 7, 11]，h = 8）
速度 k:  1   2   3   4   5   6   7  …  11
所需時數 27  15  10   8   8   6   5  …   4
pred:    F   F   F   T   T   T   T  …   T   pred(k) = 時數 <= 8
                     ↑ 第一個 T = 4
```

在答案空間上搜尋時，有三件事要先想清楚，面試時也最好直接說出口：

1. **單調性**：為什麼 x 可行時 x + 1 也可行？例如容量越大，同樣的貪婪裝法只會用更少天。沒有單調性就不能二分。
2. **上下界**：下界要小到不會漏掉答案、又不能讓檢查函式出錯（Koko 的速度不能是 0，否則除以零；運貨的容量不能小於最重的包裹，否則貪婪會卡住）。上界要保證一定可行，這樣可以直接當作 `hi` 傳入。
3. **檢查函式的複雜度**：總時間是 O(檢查成本 × log(上界 − 下界))。值域 10⁹ 大約 30 次，10¹⁰ 大約 34 次，10¹⁸ 大約 60 次。

第 k 小類題目還有第四件事：**答案為什麼一定是真的候選值**？因為第一個讓 count(≤ x) ≥ k 的 x，滿足 count(≤ x − 1) < k ≤ count(≤ x)，也就是恰好有候選值等於 x，所以不需要額外驗證「x 是否出現過」。

## 8.5 `lo < hi` 與 `lo <= hi`：兩種寫法怎麼選

教科書和網路上最常見的另一種寫法是閉區間 `[lo, hi]` 加 `while lo <= hi`。兩種寫法都正確，差別在「區間的語意」與「mid 是否被保留」：

| | `while lo < hi`（本書主模板） | `while lo <= hi` |
|---|---|---|
| 區間語意 | 半開 `[lo, hi)`，或「答案在 `[lo, hi]` 且 `hi` 已知可行」 | 閉區間 `[lo, hi]`，每個位置都還沒檢查 |
| 更新 | `hi = mid`、`lo = mid + 1` | `hi = mid - 1`、`lo = mid + 1` |
| mid 的處理 | True 時保留 mid 當候選 | 每次都把 mid 排除，需要時另外記錄 `ans = mid` |
| 結束狀態 | `lo == hi`，就是答案 | `lo == hi + 1`，區間為空 |
| 最適合 | 找邊界、找第一個可行答案、第 k 小 | 找某個確切的值，找到就能提前 `return` |

```python
def exact_search(nums: list[int], target: int) -> int:
    """閉區間寫法：找到 target 就立刻回傳索引，否則回傳 -1。"""
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def lower_bound_closed(nums: list[int], target: int) -> int:
    """閉區間寫法也能找邊界，但要用 ans 記住目前最好的候選。"""
    lo, hi, ans = 0, len(nums) - 1, len(nums)
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] >= target:
            ans = mid
            hi = mid - 1
        else:
            lo = mid + 1
    return ans


nums = [2, 4, 4, 4, 9]
assert exact_search(nums, 9) == 4
assert exact_search(nums, 4) in (1, 2, 3)
assert exact_search(nums, 5) == -1
assert exact_search([], 1) == -1
assert [lower_bound_closed(nums, t) for t in (1, 2, 4, 5, 9, 10)] == [0, 0, 1, 4, 4, 5]
print("all tests passed")
```

**何時用哪個**。題目問「找到某個值就好」（核心題 2 的 33 題、「回傳任意一個 target 的位置」），閉區間寫法可以在 `nums[mid] == target` 時提前結束，邏輯最直接。題目問「第一個／最後一個」「最小可行」「第 k 小」，一律用 `lo < hi`：它不需要額外的 `ans` 變數，結束時 `lo` 就是答案，也不會因為忘記更新 `ans` 而出錯。真正危險的是**混用**：用 `while lo < hi` 卻寫 `hi = mid - 1`（會跳過答案），或用 `while lo <= hi` 卻寫 `hi = mid`（`lo == hi` 且 pred 為 True 時區間不再縮小，無窮迴圈）。寫之前先決定區間語意，四行程式就會自然對上。

## 8.6 浮點 binary search

當答案是實數（例如「加油站之間最大距離的最小值」「立方根」「最小平均值」），單調性與 F/T 的想法完全相同，只是沒有「下一個整數」可以 `+ 1`。更新改成 `lo = mid` 或 `hi = mid`，結束條件改成精度或固定次數。

```python
def cube_root(x: float) -> float:
    """回傳 x 的實數立方根，誤差遠小於 1e-9。"""
    lo, hi = min(-1.0, x), max(1.0, x)   # 不論 |x| 大於或小於 1，根都在這個範圍內
    for _ in range(100):                 # 固定次數：每次寬度減半，100 次遠超 double 的精度
        mid = (lo + hi) / 2
        if mid ** 3 >= x:
            hi = mid
        else:
            lo = mid
    return hi


assert abs(cube_root(27.0) - 3.0) < 1e-9
assert abs(cube_root(-8.0) + 2.0) < 1e-9
assert abs(cube_root(0.001) - 0.1) < 1e-9
assert abs(cube_root(0.0)) < 1e-9
assert abs(cube_root(1e12) - 1e4) < 1e-6
print("all tests passed")
```

三個要點。第一，**優先用固定迭代次數**，而不是 `while hi - lo > 1e-9`。當答案很大（例如 10¹²）時，相鄰兩個 double 的間距本身就大於 10⁻⁹，`mid` 會等於 `lo` 或 `hi`，區間再也縮不小，`while` 版本會變成無窮迴圈；固定 100 次則一定會結束，而 double 只有 53 位元的有效位數，大約 60 次之後區間就已經縮到相鄰浮點數。第二，**範圍要包住答案**：`x = 0.001` 的立方根是 0.1，比 x 本身大，所以上界不能直接設成 x。第三，如果題目只要求 10⁻⁶ 的誤差，迭代次數可以用 log₂(初始寬度 ÷ 精度) 估算，例如寬度 10⁸、精度 10⁻⁶ 只需約 47 次；寫在註解裡，面試官會知道你理解收斂速度。

## 8.7 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| `while lo < hi` 搭配 `hi = mid - 1` | 答案剛好在 mid 時被跳過，回傳值少 1 或多 1 | pred 為 True 的 mid 可能是答案，`hi = mid` 保留它 |
| `lo = mid` 搭配向下取整的 mid | `hi = lo + 1` 時區間不縮小，無窮迴圈 | 只寫 `lo = mid + 1`；需要最後一個 True 時用 `last_true` 轉換 |
| pred 不單調 | 某些輸入回傳錯的答案，而且很難重現 | 寫程式前先在紙上把 F/T 序列畫出來，說明為什麼 x 可行則 x + 1 可行 |
| 答案空間的下界太小 | Koko 速度 0 造成除以零；運貨容量小於最重包裹時貪婪檢查算錯 | 下界取「一定不會更小」的值：速度 1、容量 `max(weights)` |
| 上界不是一定可行 | 全部 False 時回傳 `hi`，卻把一個不可行的值當答案 | 上界取保證可行的值（`max(piles)`、`sum(weights)`），或回傳前再檢查一次 |
| 找邊界後沒有驗證 | 34 題 target 不存在時回傳 `[n, n-1]` 或錯的索引 | `first_true` 回傳 `n` 或 `nums[lo] != target` 時要回報找不到 |
| 第 k 小用錯計數 | 用 count(< x) ≥ k 或 count(≤ x) > k，答案偏移 1 | 固定用「第一個讓 count(≤ x) ≥ k 的 x」 |
| 負數除法取整錯 | 2040 題中負數乘積的計數錯誤 | Python 的 `//` 是向下取整；需要向上取整時寫 `-(-p // q)`，並分正負號處理 |
| 浮點 `while hi - lo > eps` | 大數值時卡住、超時 | 改用固定迭代次數 |

## 核心題 1｜34. Find First and Last Position of Element in Sorted Array｜Medium

### 題目

給一個以非遞減順序排列的整數陣列 `nums`（可能有重複），以及一個整數 `target`。請回傳 `target` 在 `nums` 中第一次出現與最後一次出現的索引 `[first, last]`；如果 `target` 不存在，回傳 `[-1, -1]`。要求時間複雜度 O(log n)。限制：`0 <= len(nums) <= 10⁵`，元素與 `target` 都在 `-10⁹` 到 `10⁹` 之間。

- 範例 1：`nums = [5, 7, 7, 8, 8, 10]`、`target = 8`，回傳 `[3, 4]`。
- 範例 2：`nums = [5, 7, 7, 8, 8, 10]`、`target = 6`，回傳 `[-1, -1]`（6 介於 5 和 7 之間，但不存在）。
- 範例 3（邊界）：`nums = []`、`target = 0`，回傳 `[-1, -1]`。
- 範例 4（邊界）：`nums = [2, 2, 2]`、`target = 2`，回傳 `[0, 2]`，整個陣列都是 target。

### 思路

暴力解是從左往右掃，遇到第一個 target 記下 first，繼續掃到最後一個 target 記下 last，時間 O(n)。另一種「半聰明」的做法是先用 binary search 找到任意一個 target，再往左右兩邊擴展；平均看起來很快，但當整個陣列都是 target 時（範例 4），擴展本身就是 O(n)，所以最差仍然是 O(n)。瓶頸在於：我們把「找到 target」當成目標，但題目真正要的是兩個**邊界**。

關鍵觀察是把兩個邊界各自改寫成一個 F/T 序列。first 是「第一個 `nums[i] >= target` 的位置」，因為陣列非遞減，`nums[i] >= target` 對 i 單調；last 則是「第一個 `nums[i] > target` 的位置」往左一格。兩次 `first_true` 各 O(log n)，不論重複多少都不會退化。這兩個位置正是 C++ 的 `lower_bound` 與 `upper_bound`，也是 Python 的 `bisect_left` 與 `bisect_right`。

找到 first 之後要驗證：若 `first == n`（所有元素都比 target 小）或 `nums[first] != target`（第一個 ≥ target 的元素比 target 大），就代表不存在。驗證通過後，第二次搜尋可以從 first 開始，因為 last 一定不會在 first 左邊；這不改變複雜度，但能少一點比較，也讓意圖更清楚。

```text
nums:    5  7  7  8  8  10       target = 8
index:   0  1  2  3  4  5
>= 8:    F  F  F  T  T  T        第一個 T = 3 → first
>  8:    F  F  F  F  F  T        第一個 T = 5 → last = 5 - 1 = 4

第一次搜尋 pred(i) = nums[i] >= 8，範圍 [0, 6)
步驟  lo  hi  mid  nums[mid]  pred  動作
 1     0   6   3      8        T    hi = 3   （3 可能就是答案，保留）
 2     0   3   1      7        F    lo = 2
 3     2   3   2      7        F    lo = 3
結束  lo = hi = 3，nums[3] == 8，first = 3

第二次搜尋 pred(i) = nums[i] > 8，範圍 [3, 6)
步驟  lo  hi  mid  nums[mid]  pred  動作
 1     3   6   4      8        F    lo = 5
 2     5   6   5     10        T    hi = 5
結束  lo = hi = 5，last = 5 - 1 = 4
```

第一次搜尋時，第 1 步看到 `nums[3] = 8` 已經是 target，但我們沒有停下來，因為它不一定是第一個；`hi = 3` 把它保留為候選，再往左確認 1、2 都是 F，才確定 3 是邊界。第二次搜尋找的是「第一個比 8 大的位置」，也就是 10 所在的 5，last 就是它的前一格。

### 解法

```python
from bisect import bisect_left, bisect_right
import random


def first_true(lo, hi, pred):
    while lo < hi:
        mid = (lo + hi) // 2
        if pred(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


def search_range(nums: list[int], target: int) -> list[int]:
    n = len(nums)
    first = first_true(0, n, lambda i: nums[i] >= target)
    if first == n or nums[first] != target:
        return [-1, -1]
    last = first_true(first, n, lambda i: nums[i] > target) - 1
    return [first, last]


def search_range_bisect(nums: list[int], target: int) -> list[int]:
    lo = bisect_left(nums, target)
    if lo == len(nums) or nums[lo] != target:
        return [-1, -1]
    return [lo, bisect_right(nums, target) - 1]


assert search_range([5, 7, 7, 8, 8, 10], 8) == [3, 4]
assert search_range([5, 7, 7, 8, 8, 10], 6) == [-1, -1]
assert search_range([], 0) == [-1, -1]
assert search_range([2, 2, 2], 2) == [0, 2]
assert search_range([1], 1) == [0, 0]
assert search_range([1, 3], 4) == [-1, -1]      # 比所有元素都大
assert search_range([1, 3], 0) == [-1, -1]      # 比所有元素都小
for _ in range(500):
    arr = sorted(random.randint(-3, 3) for _ in range(random.randint(0, 12)))
    t = random.randint(-4, 4)
    idx = [i for i, v in enumerate(arr) if v == t]
    expect = [idx[0], idx[-1]] if idx else [-1, -1]
    assert search_range(arr, t) == expect == search_range_bisect(arr, t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(log n)：兩次 binary search，每次最多 ⌈log₂(n+1)⌉ 輪，與重複次數無關。空間 O(1)，lambda 只是閉包，沒有建立新陣列。邊界情況：空陣列時 `first_true(0, 0, …)` 直接回傳 0 等於 n，走「不存在」分支；target 比所有元素小時 first = 0 但 `nums[0] != target`；target 比所有元素大時 first = n；整個陣列都是 target 時兩次搜尋分別得到 0 與 n，回傳 `[0, n-1]`；負數不影響，因為只做比較。

### Follow-up

> [!question]- F1. 如果只要統計 target 出現幾次呢？
> 次數就是 `bisect_right(nums, target) - bisect_left(nums, target)`，也就是兩個邊界之差，不需要驗證 target 是否存在（不存在時兩者相等，差為 0）。時間仍是 O(log n)。如果同一個陣列要回答 q 次不同 target 的查詢，每次 O(log n)，總共 O(q log n)；若陣列不再變動而值域很小，也可以預先建 `Counter` 讓每次查詢 O(1)，代價是 O(n) 的前處理與空間。

> [!question]- F2. 如果要統計落在區間 [a, b] 的元素個數？
> 答案是 `bisect_right(nums, b) - bisect_left(nums, a)`：第一個 > b 的位置減去第一個 ≥ a 的位置，中間剛好是所有 a ≤ x ≤ b 的元素。若 a > b 結果可能是負數，要先回傳 0。這是很多題目的基本零件，例如 2563 題「計算和落在 [lower, upper] 之間的數對有幾個」：先排序，再對每個 i 在它右邊做這組兩次 bisect，總共 O(n log n)。

> [!question]- F3. 如果陣列是旋轉過的排序陣列（可能有重複），要找 target 的範圍呢？
> 先找出旋轉點 p（最小值的位置，做法見核心題 3），把旋轉後的陣列視為一個「虛擬排序陣列」，虛擬索引 k 對應真實索引 `(k + p) % n`。接著在虛擬索引上做兩次 `first_true`，pred 讀 `nums[(k + p) % n]`，就能得到虛擬區間 `[first, last]`，再換回真實索引。注意 target 的範圍可能**跨過陣列尾端**，例如 `[8, 8, 1, 2, 8]` 中 8 的位置是 4、0、1，所以回傳值要表示成「從 4 繞到 1」或兩段區間。沒有重複時找 p 是 O(log n)，整體 O(log n)；有重複時找 p 最差要 O(n)（例如 `[1, 1, 1, 0, 1]` 必須逐一排除），這是資訊量本身的下限，不是寫法問題。

> [!question]- F4. 如果資料存在磁碟上，每次只能讀一個 block（每塊 B 個元素），怎麼讓讀取次數最少？
> 直接對全域索引做 binary search，每次 mid 都落在不同 block，總共讀 O(log n) 個 block。更好的做法是兩層：先在記憶體裡保存每個 block 的第一個元素（共 n/B 個，稱為 fence pointers），在這份索引上 binary search 找到 target 可能出現的第一個 block，只讀那一塊再在塊內 binary search，讀取次數降為 O(1) 個 block（第一個與最後一個位置可能各在不同 block，所以最多讀幾塊）。若連索引都放不進記憶體，就把索引本身也分塊、一層層往上建，這就是 B-tree 的想法，讀取次數是 O(log_B n)。重複元素跨很多 block 時，first 和 last 各自用一次兩層搜尋即可，不需要讀中間的 block。

> [!question]- F5. 如果陣列長度未知（只能呼叫 get(i)，越界時回傳無限大）呢？
> 先用 exponential search（倍增搜尋）找上界：依序檢查 `get(1)、get(2)、get(4)…`，直到 `get(2^j) >= target`，此時答案一定在 `[2^(j-1), 2^j]` 之間，再在這段做原本的兩次 binary search。倍增需要 O(log p) 次，p 是 target 的位置，所以總時間是 O(log p)，不依賴未知的 n。越界回傳無限大剛好讓 pred `get(i) >= target` 在尾端自動是 True，單調性不受影響。

## 核心題 2｜33. Search in Rotated Sorted Array｜Medium

### 題目

有一個原本嚴格遞增、**元素互不相同**的整數陣列，被人在某個未知位置 k 旋轉：`[a0, a1, …, an-1]` 變成 `[ak, …, an-1, a0, …, ak-1]`（k 也可能是 0，代表沒旋轉）。給你旋轉後的 `nums` 和 `target`，回傳 `target` 的索引，不存在則回傳 -1。要求 O(log n)。限制：`1 <= len(nums) <= 5000`，元素在 `-10⁴` 到 `10⁴` 之間。

- 範例 1：`nums = [4, 5, 6, 7, 0, 1, 2]`、`target = 0`，回傳 `4`。
- 範例 2：`nums = [4, 5, 6, 7, 0, 1, 2]`、`target = 3`，回傳 `-1`。
- 範例 3：`nums = [6, 7, 0, 1, 2, 4, 5]`、`target = 7`，回傳 `1`（target 在旋轉後的左段）。
- 範例 4（邊界）：`nums = [1]`、`target = 0`，回傳 `-1`；`nums = [1, 3]`（沒有旋轉）、`target = 3`，回傳 `1`。

### 思路

暴力解是線性掃描，O(n)。一般的 binary search 不能直接用，因為整個陣列不是排序的：`nums[mid] < target` 時，target 可能在右邊（還在同一段），也可能在左邊（target 在另一段）。所以問題變成：只看 `nums[lo]`、`nums[mid]`、`nums[hi]` 三個值，能不能判斷 target 在哪一半？

關鍵觀察：從任一個 mid 切開，**左半 `[lo, mid]` 和右半 `[mid, hi]` 之中至少有一半是完整排序的**，因為旋轉的斷點最多只有一個，它只能落在其中一半。判斷方式是 `nums[lo] <= nums[mid]`：成立則左半有序（斷點不在左半），否則右半有序。對於有序的那一半，我們可以用頭尾兩個值精確判斷 target 在不在裡面；在就往那半走，不在就往另一半走。每一步仍然丟掉一半，所以是 O(log n)。

因為這題是「找到確切的值就回傳」，用 8.5 節的閉區間 `lo <= hi` 寫法最自然：`nums[mid] == target` 時直接回傳；其他情況 mid 已經確定不是答案，可以 `mid ± 1` 排除。判斷有序的那一半時，條件要用半開區間避免重複檢查 mid：左半有序時判斷 `nums[lo] <= target < nums[mid]`，右半有序時判斷 `nums[mid] < target <= nums[hi]`。

另一種同樣 O(log n) 的做法是兩階段：先用核心題 3 找到最小值的位置 p，再判斷 target 屬於左段 `[0, p)` 還是右段 `[p, n)`（比較 target 和 `nums[-1]`），在那一段做普通的 binary search。兩段式較長，但每一步都是本章的標準模板，比較不容易寫錯，面試時兩種都可以，下面兩種都附上。

```text
範例 1：nums = [4, 5, 6, 7, 0, 1, 2]，target = 0
index:  0  1  2  3  4  5  6

步驟1  lo=0 mid=3 hi=6   [4 5 6 7] 0 1 2
       nums[lo]=4 <= nums[mid]=7 → 左半 [4..7] 有序
       0 不在 [4, 7) → 往右：lo = 4
步驟2  lo=4 mid=5 hi=6   4 5 6 7 [0 1] 2
       nums[lo]=0 <= nums[mid]=1 → 左半 [0..1] 有序
       0 在 [0, 1) → 往左：hi = 4
步驟3  lo=4 mid=4 hi=4   nums[4] = 0 == target → 回傳 4

範例 3：nums = [6, 7, 0, 1, 2, 4, 5]，target = 7
步驟1  lo=0 mid=3 hi=6   6 7 0 [1 2 4 5]
       nums[lo]=6 > nums[mid]=1 → 右半 [1..5] 有序
       7 不在 (1, 5] → 往左：hi = 2
步驟2  lo=0 mid=1 hi=2   nums[1] = 7 == target → 回傳 1
```

範例 1 的第 1 步，左半 `[4, 5, 6, 7]` 有序而 0 不在其中，所以 0 必在右半；第 2 步右半剩 `[0, 1, 2]`，此時它沒有斷點，演算法退化成普通的 binary search。範例 3 的斷點在左半，因此右半有序，用右半的範圍 `(1, 5]` 判斷 7 不在其中，往左找到。

### 解法

```python
import random
from bisect import bisect_left


def search(nums: list[int], target: int) -> int:
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[lo] <= nums[mid]:                 # 左半 [lo, mid] 有序
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:                                     # 右半 [mid, hi] 有序
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1


def search_two_phase(nums: list[int], target: int) -> int:
    n = len(nums)
    # 第一階段：最小值位置 = 第一個 nums[i] <= nums[-1] 的 i（核心題 3）
    lo, hi = 0, n - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] <= nums[-1]:
            hi = mid
        else:
            lo = mid + 1
    p = lo
    # 第二階段：target <= nums[-1] 代表它只可能在右段 [p, n)
    left, right = (p, n) if target <= nums[-1] else (0, p)
    i = bisect_left(nums, target, left, right)
    return i if i < right and nums[i] == target else -1


assert search([4, 5, 6, 7, 0, 1, 2], 0) == 4
assert search([4, 5, 6, 7, 0, 1, 2], 3) == -1
assert search([6, 7, 0, 1, 2, 4, 5], 7) == 1
assert search([1], 0) == -1
assert search([1], 1) == 0
assert search([1, 3], 3) == 1
assert search([3, 1], 1) == 1
for _ in range(500):
    base = sorted(random.sample(range(-20, 20), random.randint(1, 10)))
    k = random.randrange(len(base))
    arr = base[k:] + base[:k]
    t = random.randint(-21, 21)
    expect = arr.index(t) if t in arr else -1
    assert search(arr, t) == expect == search_two_phase(arr, t)
print("all tests passed")
```

### 複雜度與邊界

兩種寫法時間都是 O(log n)，空間 O(1)。邊界情況：長度 1 時 `lo == mid == hi`，`nums[lo] <= nums[mid]` 成立，走左半分支後區間變空；`nums[lo] <= nums[mid]` 必須用 `<=` 而不是 `<`，因為 `lo == mid` 時（例如剩兩個元素 `[3, 1]`）左半只有一個元素，它當然是有序的，若用 `<` 會誤判成右半有序並用錯誤的範圍判斷；沒有旋轉（k = 0）時每一步左半都有序，退化成普通 binary search。這題的前提是元素互不相同，有重複時 `nums[lo] == nums[mid]` 就無法判斷哪一半有序，見 F1。

### Follow-up

> [!question]- F1. 如果陣列可以有重複元素呢（81. Search in Rotated Sorted Array II）？
> 當 `nums[lo] == nums[mid] == nums[hi]` 時，無法判斷斷點在哪一半，例如 `[1, 1, 1, 0, 1]` 和 `[1, 0, 1, 1, 1]` 從這三個位置看起來一模一樣。此時只能確定 `nums[lo]` 和 `nums[hi]` 都不是 target（因為已經和 mid 比過），所以 `lo += 1`、`hi -= 1` 各縮一格再繼續；其他情況照原本的邏輯。平均仍很快，但最差是 O(n)，而且這是下限：陣列全是 1 只有一個 0 時，任何演算法都得看過幾乎所有位置才能找到 0。

> [!question]- F2. 如果題目改成回傳陣列被旋轉了幾次（k 是多少）？
> 旋轉次數就是最小值的索引，因為原本在索引 0 的最小值被移到了索引 k。用核心題 3 的 `first_true(0, n - 1, lambda i: nums[i] <= nums[-1])` 直接得到 k，O(log n)。若要的是「往右旋轉」的次數，答案同樣是 k；往左旋轉的次數則是 `(n - k) % n`。面試官常用這題確認你知道 33 與 153 是同一個結構。

> [!question]- F3. 能不能只用一個單調的 pred，套用「第一個 True」模板一次解決？
> 可以。定義一個函式把每個元素映射成「（所在段落，值）」：在右段（`x <= nums[-1]`）的元素映射成 `(1, x)`，在左段的映射成 `(0, x)`。旋轉後的陣列在這個映射下是嚴格遞增的，target 也用同樣方式映射成 `key_t`，於是答案就是 `first_true(0, n, lambda i: key(nums[i]) >= key_t)`，最後檢查該位置是否等於 target。時間 O(log n)。這個寫法的好處是完全沿用標準模板，也能直接推廣到核心題 1 F3 的範圍查詢。

> [!question]- F4. 如果陣列是「先嚴格遞增再嚴格遞減」的山形陣列，要找 target 呢（1095. Find in Mountain Array）？
> 分三次 binary search。第一次找山頂：pred 為 `nums[i] > nums[i + 1]`，在 `[0, n - 1)` 上是 F…F T…T，第一個 True 就是山頂 p。第二次在遞增段 `[0, p]` 做普通的 lower bound 找 target。找不到再在遞減段 `[p, n)` 上搜尋，pred 改成 `nums[i] <= target`（遞減段上這個條件是 F…F T…T）。總共 O(log n) 次存取。題目要求有多個位置時回傳較小的索引，所以先搜遞增段。原題限制最多呼叫 100 次 `get`：找山頂每輪要讀 `nums[mid]` 與 `nums[mid + 1]` 兩個值，約 2 log₂ n 次，兩段的搜尋各約 log₂ n 次，n = 10⁴ 時合計約 4 × 14 = 56 次，在限制內；若擔心常數，可以快取已讀過的位置。

## 核心題 3｜153. Find Minimum in Rotated Sorted Array｜Medium

### 題目

一個長度為 n、**元素互不相同**的嚴格遞增陣列，被旋轉了 1 到 n 次（旋轉 n 次等於沒變）。旋轉一次的意思是把最後一個元素移到最前面，例如 `[0, 1, 2, 4, 5, 6, 7]` 旋轉 4 次會變成 `[4, 5, 6, 7, 0, 1, 2]`。給你旋轉後的 `nums`，回傳其中的最小值，要求 O(log n)。限制：`1 <= n <= 5000`，元素在 `-5000` 到 `5000` 之間。

- 範例 1：`nums = [3, 4, 5, 1, 2]`，回傳 `1`。
- 範例 2：`nums = [4, 5, 6, 7, 0, 1, 2]`，回傳 `0`。
- 範例 3（邊界，沒有旋轉效果）：`nums = [11, 13, 15, 17]`，回傳 `11`。
- 範例 4（邊界）：`nums = [7]`，回傳 `7`；`nums = [2, 1]`，回傳 `1`。

### 思路

暴力解是 `min(nums)`，O(n)。也可以線性找「第一個比前一個小的位置」，同樣 O(n)。要做到 O(log n)，就必須找出一個對索引單調的判斷。

旋轉後的陣列由兩段遞增序列組成：左段 `[ak, …, an-1]` 全部比右段 `[a0, …, ak-1]` 大，最小值就是右段的第一個元素。關鍵觀察是：**一個元素屬於右段，若且唯若它 ≤ 最後一個元素 `nums[-1]`**。因為最後一個元素是右段的最大值，右段所有元素都 ≤ 它；而左段每個元素都比右段所有元素大，當然也 > `nums[-1]`。所以 `pred(i) = nums[i] <= nums[-1]` 在索引上是 F…F T…T，第一個 True 就是最小值的位置。沒有旋轉時左段是空的，整排都是 T，第一個 T 就是索引 0，不需要特判。

搜尋範圍可以是 `[0, n - 1)`，並把 `hi = n - 1` 當作「一定為 True」的上界，因為 `nums[-1] <= nums[-1]` 永遠成立。這正是 8.3 節說的半開區間用法：如果前面全部是 F，回傳的 n - 1 剛好就是答案。很多版本寫成比較 `nums[mid]` 與 `nums[hi]`（目前區間的右端），邏輯等價：`hi` 永遠停在右段裡，所以 `nums[hi]` 也是一個「右段代表」。

```text
nums = [5, 6, 7, 8, 9, 1, 2]，nums[-1] = 2
index:      0  1  2  3  4  5  6
nums:       5  6  7  8  9  1  2
<= 2:       F  F  F  F  F  T  T      第一個 T = 5 → 最小值 1
            └── 左段 ──┘  └右段┘

步驟  lo  hi  mid  nums[mid]  <= 2?  動作
 1     0   6   3      8         F     lo = 4
 2     4   6   5      1         T     hi = 5
 3     4   5   4      9         F     lo = 5
結束  lo = hi = 5，回傳 nums[5] = 1
```

第 1 步 mid 落在左段（8 > 2），最小值一定在它右邊；第 2 步 mid 落在右段（1 ≤ 2），最小值在它或它的左邊，所以 `hi = 5` 保留它；第 3 步確認 4 號位置的 9 仍在左段，於是邊界收斂在 5。

### 解法

```python
import random


def find_min(nums: list[int]) -> int:
    lo, hi = 0, len(nums) - 1          # hi = n - 1 一定滿足 nums[i] <= nums[-1]
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] <= nums[-1]:      # mid 在右段：最小值在 mid 或其左邊
            hi = mid
        else:                          # mid 在左段：最小值在 mid 右邊
            lo = mid + 1
    return nums[lo]


assert find_min([3, 4, 5, 1, 2]) == 1
assert find_min([4, 5, 6, 7, 0, 1, 2]) == 0
assert find_min([11, 13, 15, 17]) == 11
assert find_min([7]) == 7
assert find_min([2, 1]) == 1
assert find_min([1, 2]) == 1
for _ in range(500):
    base = sorted(random.sample(range(-50, 50), random.randint(1, 12)))
    k = random.randrange(len(base))
    arr = base[k:] + base[:k]
    assert find_min(arr) == min(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(log n)，空間 O(1)。邊界情況：n = 1 時迴圈不執行，直接回傳唯一的元素；沒有旋轉時每個元素都 ≤ `nums[-1]`，pred 全為 True，`hi` 一路往左縮到 0；n = 2 且已旋轉（`[2, 1]`）時 mid = 0，2 > 1 所以 lo = 1。前提是元素互不相同，有重複時 `nums[mid] == nums[-1]` 不能判斷 mid 在哪一段，見 F1。

### Follow-up

> [!question]- F1. 如果陣列有重複元素呢（154. Find Minimum in Rotated Sorted Array II）？
> 改成和目前區間的右端 `nums[hi]` 比較：`nums[mid] > nums[hi]` 時 `lo = mid + 1`；`nums[mid] < nums[hi]` 時 `hi = mid`；相等時無法判斷，但可以安全地 `hi -= 1`，因為就算 `nums[hi]` 是最小值，`nums[mid]` 和它一樣大，最小值仍保留在區間裡。最差情況（例如 `[1, 1, 1, 1, 0, 1, 1]`）退化為 O(n)，這是資訊下限，無法改進。注意這裡不能再用 `nums[-1]` 當固定代表，因為重複值讓「≤ nums[-1]」不再只屬於右段。

> [!question]- F2. 為什麼不能和 nums[0]（或 nums[lo]）比較？
> 因為「≥ nums[0]」的元素在旋轉後是左段，在沒有旋轉時卻是整個陣列，兩種情況下最小值的位置和 pred 的關係不一致。具體來說，若用「第一個 `nums[i] < nums[0]` 的位置」，沒有旋轉時 pred 全為 False，`first_true` 回傳 n，越界了，必須額外特判「若 `nums[0] < nums[-1]` 直接回傳 `nums[0]`」。和 `nums[-1]` 比較則兩種情況統一，因為最後一個元素一定在右段（或整個陣列就是右段）。這是面試官很愛追問的細節，能說清楚代表你真的理解 pred。

> [!question]- F3. 如果要回傳最大值呢？
> 最大值是左段的最後一個元素，也就是最小值位置 p 的前一格：`nums[(p - 1) % n]`。沒有旋轉時 p = 0，`(0 - 1) % n = n - 1`，剛好是最後一個元素，Python 的負數取模讓這個式子不必特判。時間仍是 O(log n)。也可以直接用 `last_true(0, n, lambda i: nums[i] >= nums[0])`，最後一個 ≥ `nums[0]` 的位置就是左段結尾。

> [!question]- F4. 如果陣列不是旋轉過的，而是任意相鄰元素不相等的陣列，要找任一個峰值（162. Find Peak Element）呢？
> 定義 `pred(i) = nums[i] > nums[i + 1]`，在 `[0, n - 1)` 上搜尋，回傳第一個 True（全 False 時回傳 n - 1）。這個 pred 不是全域單調的，但 binary search 仍然正確，因為它維持的 invariant 是「`[lo, hi]` 中一定有峰值」：`nums[mid] < nums[mid + 1]` 時往右走一定會遇到峰值（要嘛一路上升到尾端，要嘛中途開始下降）；`nums[mid] > nums[mid + 1]` 時 mid 或其左邊一定有峰值。O(log n)。這題提醒我們：binary search 需要的不一定是全域單調，而是「每一步都能保證答案在保留的那一半」。

## 核心題 4｜875. Koko Eating Bananas｜Medium

### 題目

有 n 堆香蕉，第 i 堆有 `piles[i]` 根。Koko 選定一個固定的整數速度 k（根／小時），每個小時她挑一堆吃 k 根；若那堆不足 k 根，她吃完那堆就休息到這個小時結束，不會在同一小時去吃別堆。守衛 h 小時後回來，請回傳能在 h 小時內吃完全部香蕉的**最小**速度 k。限制：`1 <= n <= 10⁴`，`n <= h <= 10⁹`，`1 <= piles[i] <= 10⁹`。

- 範例 1：`piles = [3, 6, 7, 11]`、`h = 8`，回傳 `4`。速度 4 時各堆分別需要 1、2、2、3 小時，共 8 小時；速度 3 需要 1 + 2 + 3 + 4 = 10 小時，超過了。
- 範例 2：`piles = [30, 11, 23, 4, 20]`、`h = 5`，回傳 `30`。h 等於堆數，每堆只能用一小時，所以速度必須是最大那堆。
- 範例 3：`piles = [30, 11, 23, 4, 20]`、`h = 6`，回傳 `23`。
- 範例 4（邊界）：`piles = [1000000000]`、`h = 2`，回傳 `500000000`。

### 思路

速度 k 對應的時數是 `hours(k) = Σ ⌈piles[i] / k⌉`，因為每堆各自需要 ⌈p / k⌉ 小時、彼此不能共用時間。暴力解是從 k = 1 開始往上試，第一個讓 `hours(k) <= h` 的 k 就是答案；每次試算 O(n)，最差要試到 `max(piles)` = 10⁹ 次，總共 O(n · max) 太慢。

瓶頸是我們在一個很大的答案範圍裡逐一嘗試。關鍵觀察：**速度越快，時數只會越少或不變**，因為每一項 ⌈p / k⌉ 都隨 k 不增。所以 `pred(k) = hours(k) <= h` 是 F…F T…T，答案就是第一個 True，可以在答案空間上 binary search。這就是 8.4 節的思維二：不直接構造最佳速度，而是反覆問「這個速度夠不夠」。

範圍要想清楚。下界是 1（速度 0 沒有意義，還會除以零）。上界是 `max(piles)`：速度等於最大那堆時每堆剛好一小時，共 n ≤ h 小時，一定可行；再快也不會更少，因為每堆至少要一小時。上界一定可行，所以可以直接把它當 `hi` 傳入半開區間模板。迭代次數約 log₂(10⁹) ≈ 30 次，每次 O(n)。

```text
piles = [3, 6, 7, 11]，h = 8
速度 k:      1   2   3   4   5   6   7   8   9  10  11
hours(k):   27  15  10   8   8   6   5   5   5   5   4
<= 8 ?       F   F   F   T   T   T   T   T   T   T   T

搜尋範圍 [1, 11)，11 = max(piles) 一定可行
步驟  lo  hi  mid  hours(mid)            pred  動作
 1     1  11   6   1+1+2+2 = 6            T    hi = 6
 2     1   6   3   1+2+3+4 = 10           F    lo = 4
 3     4   6   5   1+2+2+3 = 8            T    hi = 5
 4     4   5   4   1+2+2+3 = 8            T    hi = 4
結束  lo = hi = 4
```

第 1 步速度 6 只需 6 小時，太寬裕，答案在 6 或更小；第 2 步速度 3 要 10 小時，太慢，答案至少是 4；第 3、4 步確認 5 和 4 都可行，邊界收斂在 4。注意 `hours(4)` 和 `hours(5)` 都是 8，這表示時數函式會有「平台」，所以題目要的是「最小」速度，用找第一個 True 正好。

### 解法

```python
import math
import random


def min_eating_speed(piles: list[int], h: int) -> int:
    def hours(k: int) -> int:
        return sum((p + k - 1) // k for p in piles)   # 整數向上取整，避免浮點誤差

    lo, hi = 1, max(piles)                           # hi 一定可行，作為半開區間的右端
    while lo < hi:
        mid = (lo + hi) // 2
        if hours(mid) <= h:
            hi = mid
        else:
            lo = mid + 1
    return lo


def brute(piles, h):
    k = 1
    while sum(math.ceil(p / k) for p in piles) > h:
        k += 1
    return k


assert min_eating_speed([3, 6, 7, 11], 8) == 4
assert min_eating_speed([30, 11, 23, 4, 20], 5) == 30
assert min_eating_speed([30, 11, 23, 4, 20], 6) == 23
assert min_eating_speed([10**9], 2) == 5 * 10**8
assert min_eating_speed([1], 1) == 1
assert min_eating_speed([5, 5, 5], 10**9) == 1     # h 很大時速度 1 就夠
for _ in range(300):
    piles = [random.randint(1, 30) for _ in range(random.randint(1, 6))]
    h = random.randint(len(piles), 60)
    assert min_eating_speed(piles, h) == brute(piles, h)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n log M)，M = `max(piles)`：binary search 約 log₂ M 輪，每輪計算 `hours` 需 O(n)。空間 O(1)。邊界情況：h == n 時答案必為 `max(piles)`，迴圈會一路把 lo 推到 hi；h 很大時答案是 1，pred(1) 為 True，hi 一路縮到 1；向上取整用 `(p + k - 1) // k` 而非 `math.ceil(p / k)`，因為 p 到 10⁹ 時浮點除法雖然通常沒事，但整數寫法完全沒有誤差風險；Python 沒有溢位，在 Java 中 `hours` 的總和可達 10⁴ × 10⁹，要用 `long`。

### Follow-up

> [!question]- F1. 如果 h < len(piles) 呢？
> 每堆至少要一小時，所以 h < n 時任何速度都不可能吃完，應回傳 -1（或丟出例外）。在程式開頭加 `if h < len(piles): return -1` 即可。這也說明了上界 `max(piles)` 「一定可行」的前提是 h ≥ n；寫答案空間的 binary search 時，先確認上界真的可行，是避免回傳錯誤答案的關鍵。

> [!question]- F2. 如果 Koko 吃完一堆後，可以在同一小時繼續吃下一堆呢？
> 那麼各堆之間不再浪費時間，總時數就是 ⌈總根數 / k⌉，條件 ⌈S / k⌉ ≤ h 等價於 k ≥ ⌈S / h⌉，答案直接是 `(S + h - 1) // h`，O(n) 算總和即可，不需要 binary search。這個對比很適合在面試中說出來：原題之所以需要二分，是因為每堆的向上取整讓時數函式沒有簡單的反函數。這個值 ⌈S / h⌉ 同時也是原題答案的一個合法下界，可以拿來縮小搜尋範圍。

> [!question]- F3. 能不能縮小搜尋範圍？
> 下界可以從 1 提高到 ⌈S / h⌉（S 是總根數），因為即使沒有任何浪費，速度也至少要這麼快。上界可以取 `min(max(piles), ⌈S / (h − n + 1)⌉)`：因為每堆的向上取整浪費不到一小時，hours(k) < S / k + n，只要 S / k ≤ h − n + 1，就有 hours(k) < h + 1，也就是 hours(k) ≤ h。實務上迭代次數只從 30 降到二十幾次，漸進複雜度不變，但面試時說出這兩個界，能展現你對檢查函式的理解。

> [!question]- F4. 如果同一組 piles 要回答很多個不同的 h 呢？
> 每次重新二分要 O(n log M)，q 次查詢共 O(q · n log M)。若 M 不大（例如 ≤ 10⁶），可以預先算出每個 k 的 hours(k)：利用 ⌈p / k⌉ = 滿足 t·k < p 的非負整數 t 的個數，得到 hours(k) = Σ_{t ≥ 0, t·k < M} G(t·k)，其中 G(v) 是「大於 v 的堆數」，可用值域前綴和 O(1) 查詢。對所有 k 求和的總工作量是 Σ M / k = O(M log M)（調和級數）。hours 對 k 不增，之後每個查詢在這個陣列上 binary search，O(log M)。

> [!question]- F5. 如果堆數 n 高達 10⁷，但每堆的根數只有少數幾種不同的值呢？
> 先用 `Counter` 把相同大小的堆合併成 `(值, 個數)`，hours(k) 變成 Σ 個數 × ⌈值 / k⌉，每次檢查只需 O(D)，D 是不同值的個數。總時間 O(n + D log M)，計數只做一次。這個技巧在答案空間 binary search 中很常見：檢查函式會被呼叫幾十次，任何能讓它變快的前處理都值得做。

## 核心題 5｜1011. Capacity To Ship Packages Within D Days｜Medium

### 題目

輸送帶上依序有 n 個包裹，第 i 個重 `weights[i]`。每天你用一艘船載運，船有固定的載重上限 capacity；每天只能從輸送帶前端依序裝包裹（**不能改變順序**、不能拆開包裹），總重不能超過 capacity。請回傳能在 `days` 天內運完所有包裹的最小 capacity。限制：`1 <= days <= n <= 5 × 10⁴`，`1 <= weights[i] <= 500`。

- 範例 1：`weights = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]`、`days = 5`，回傳 `15`。分法是 `[1, 2, 3, 4, 5]`、`[6, 7]`、`[8]`、`[9]`、`[10]`。
- 範例 2：`weights = [3, 2, 2, 4, 1, 4]`、`days = 3`，回傳 `6`，分法 `[3, 2]`、`[2, 4]`、`[1, 4]`。
- 範例 3（邊界）：`weights = [1, 2, 3, 1, 1]`、`days = 4`，回傳 `3`；容量不能小於最重的包裹 3。
- 範例 4（邊界）：`days = 1` 時答案是 `sum(weights)`；`days = n` 時答案是 `max(weights)`。

### 思路

這題等價於「把陣列切成至多 days 段連續子陣列，最小化最大段和」。暴力做法是列舉所有切法，切點組合數是 C(n−1, days−1)，指數級；DP 可以做到 O(days · n²)，在 n = 5 × 10⁴ 時仍然太慢。

換個問法：**如果容量是 c，最少需要幾天？** 這個問題有簡單的貪婪解：從頭開始裝，裝得下就繼續裝，裝不下就換下一天。貪婪是最佳的，因為當天多裝一個包裹永遠不會讓後面變差：剩下的包裹是原本剩下的後綴，只會更少。更重要的是單調性：容量越大，貪婪需要的天數只會更少或不變，所以 `pred(c) = need_days(c) <= days` 是 F…F T…T，最小容量就是第一個 True。

範圍：下界是 `max(weights)`，容量再小就有包裹永遠裝不上船（這時貪婪程式也會算錯，因為它會把一個裝不下的包裹獨自放一天卻沒發現超重）；上界是 `sum(weights)`，一天就能全部運完，一定可行。檢查 O(n)，迭代 log₂(sum − max) 次，sum 最多 2.5 × 10⁷，約 25 次。

```text
weights = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]，days = 5
容量 c:       10  11  12  13  14  15  16  17
need_days(c):  7   6   6   6   6   5   5   4
<= 5 ?         F   F   F   F   F   T   T   T

搜尋範圍 [10, 55)，55 = sum 一定可行
步驟  lo  hi  mid  need_days  pred  動作
 1    10  55   32      2       T    hi = 32
 2    10  32   21      3       T    hi = 21
 3    10  21   15      5       T    hi = 15
 4    10  15   12      6       F    lo = 13
 5    13  15   14      6       F    lo = 15
結束  lo = hi = 15

貪婪檢查 c = 14：[1 2 3 4]=10 | [5 6]=11 | [7] | [8] | [9] | [10]   → 6 天，F
         c = 15：[1 2 3 4 5]=15 | [6 7]=13 | [8] | [9] | [10]     → 5 天，T
```

c = 14 時，第一天裝到 1 + 2 + 3 + 4 = 10，再加 5 會變 15 超過，只好換天；這一點點的差距讓後面每一段都往後推，最後多用一天。c = 15 剛好讓第一天塞下 5，於是 5 天完成。binary search 不需要知道這些細節，它只是反覆呼叫檢查函式，用 5 次檢查從 45 個候選中找到邊界。

### 解法

```python
import random
from functools import cache


def ship_within_days(weights: list[int], days: int) -> int:
    def need_days(cap: int) -> int:
        used, load = 1, 0
        for w in weights:
            if load + w > cap:          # 今天裝不下，換下一天
                used += 1
                load = 0
            load += w
        return used

    lo, hi = max(weights), sum(weights)
    while lo < hi:
        mid = (lo + hi) // 2
        if need_days(mid) <= days:
            hi = mid
        else:
            lo = mid + 1
    return lo


def brute(weights, days):
    n = len(weights)

    @cache
    def best(i, d):                     # 把 weights[i:] 切成至多 d 段的最小最大段和
        if i == n:
            return 0
        if d == 0:
            return float("inf")
        res, s = float("inf"), 0
        for j in range(i, n):
            s += weights[j]
            res = min(res, max(s, best(j + 1, d - 1)))
        return res

    return best(0, days)


assert ship_within_days([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5) == 15
assert ship_within_days([3, 2, 2, 4, 1, 4], 3) == 6
assert ship_within_days([1, 2, 3, 1, 1], 4) == 3
assert ship_within_days([7, 1, 2], 1) == 10      # days = 1 → sum
assert ship_within_days([7, 1, 2], 3) == 7       # days = n → max
assert ship_within_days([5], 1) == 5
for _ in range(300):
    w = [random.randint(1, 9) for _ in range(random.randint(1, 8))]
    d = random.randint(1, len(w))
    assert ship_within_days(w, d) == brute(w, d)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n log S)，S = `sum(weights)`，每輪檢查 O(n)。空間 O(1)。邊界：下界必須是 `max(weights)` 而不是 1，否則 `need_days` 在 cap 小於某個包裹時會讓那個包裹獨佔一天、回傳一個看似合法的天數，造成錯誤的 True；`days = n` 時答案是 `max(weights)`，pred(lo) 一開始就是 True；`days = 1` 時答案是總和，lo 一路被推到 hi。貪婪中 `load + w > cap` 用嚴格大於，因為剛好等於容量是允許的。

### Follow-up

> [!question]- F1. 如果每天除了重量上限，還限制最多只能裝 m 個包裹呢？
> 在貪婪檢查中多一個條件：`load + w > cap or count == m` 時換天。貪婪仍然最佳（多裝一個包裹不會讓剩下的更難），單調性也仍然成立（容量變大不會讓天數增加），所以 binary search 框架完全不變，O(n log S)。若 m · days < n，則不論容量多大都不可能，要先判斷並回傳 -1。

> [!question]- F2. 如果可以任意改變包裹順序呢？
> 那就變成 bin packing（裝箱問題）的判定版本：「能否把 n 個物品放進 days 個容量 c 的箱子」，這是 NP-complete，binary search 的單調性仍然成立，但檢查函式不再有多項式時間的精確解。面試中可以說：精確解要用 backtracking 加剪枝（第 19 章難題 4 的 698 題 Partition to K Equal Sum Subsets 是同類），實務上用 First Fit Decreasing 等近似演算法，保證使用的箱子數不超過最佳解的約 11/9 倍加一個常數。這個對比說明了原題的「依序裝」是讓貪婪成立的關鍵限制。

> [!question]- F3. 如果要輸出實際的分法呢？
> 先用 binary search 得到最小容量 c*，再用同一個貪婪跑一次，記錄每一天的起訖索引即可，O(n)。要注意貪婪可能用少於 days 天（例如容量 c* 時貪婪只需 3 天而 days = 5）；若題目要求恰好 days 天且每天至少一個包裹，可以把長度大於 1 的段再切開，直到湊滿 days 段；切開不會讓任何一段變重，所以最大值仍是 c*，前提是 n ≥ days。

> [!question]- F4. 如果包裹重量很大（例如到 10⁹）或 n 到 10⁶ 呢？
> 演算法不變，只是迭代次數變成 log₂(n · 10⁹) ≈ 50 次，每次 O(n)，總共約 5 × 10⁷ 次基本操作，在 Python 中需要注意常數。可以把下界提高到 `max(max(weights), ⌈sum / days⌉)`，因為平均每天至少要運 sum / days。在 Java／C++ 中總和要用 64 位元整數。另一個常數優化是先算前綴和，貪婪檢查時用 `bisect_right(prefix, start + cap)` 一次跳到當天最後一個包裹，每次檢查變成 O(days · log n)，當 days 遠小於 n 時明顯更快。

## 難題 1｜4. Median of Two Sorted Arrays｜Hard

### 題目

給兩個已經由小到大排序的整數陣列 `nums1`（長度 m）和 `nums2`（長度 n），回傳兩者合併後的中位數。總長度為奇數時，中位數是正中間那個數；為偶數時，是正中間兩個數的平均。要求時間複雜度 O(log(m + n))。限制：`0 <= m, n <= 1000`，`1 <= m + n <= 2000`，元素在 `-10⁶` 到 `10⁶` 之間。

- 範例 1：`nums1 = [1, 3]`、`nums2 = [2]`，合併後 `[1, 2, 3]`，回傳 `2.0`。
- 範例 2：`nums1 = [1, 2]`、`nums2 = [3, 4]`，合併後 `[1, 2, 3, 4]`，回傳 `(2 + 3) / 2 = 2.5`。
- 範例 3：`nums1 = [1, 3, 8, 9, 15]`、`nums2 = [7, 11, 18, 19, 21, 25]`，合併後第 6 小是 11，回傳 `11.0`。
- 範例 4（邊界）：`nums1 = []`、`nums2 = [5]`，回傳 `5.0`；兩陣列的值區間完全不重疊（`[1, 2]` 與 `[10, 20]`）時回傳 `(2 + 10) / 2 = 6.0`。

### 提示

> [!tip]- 提示 1
> 中位數把合併後的陣列切成「左半」和「右半」，左半的元素個數是固定的 ⌈(m + n) / 2⌉。你不需要真的合併，只需要知道左半由哪些元素組成。

> [!tip]- 提示 2
> 如果左半拿了 `nums1` 的前 i 個，就必須拿 `nums2` 的前 half − i 個。所以整個問題只有一個未知數 i，範圍是 0 到 m。什麼條件下這個切法是「正確的左半」？

> [!tip]- 提示 3
> 切法正確 ⇔ `A[i−1] <= B[j]` 且 `B[j−1] <= A[i]`（j = half − i，越界視為 ±∞）。隨著 i 增加，`A[i]` 變大、`B[j−1]` 變小，所以 `A[i] >= B[j−1]` 對 i 是 F…F T…T。在較短的陣列上找第一個 True。

### 詳解

**為什麼直覺做法不夠**。最直接的是用 merge sort 的合併步驟走到第 ⌈(m+n)/2⌉ 個元素，O(m + n)，空間可以是 O(1)，在面試中這是一個好的起點，但不符合 O(log) 的要求。另一個直覺是「對值做 binary search」：猜一個值 x，用兩次 `bisect` 數 ≤ x 的元素個數，這是 O(log V · log(m+n))，V 是值域，雖然很快但不是題目要求的複雜度，而且偶數長度時要找兩個值。真正的突破是：不要對值、也不要對合併後的位置二分，而是**對「切在哪裡」二分**。

**把中位數變成切法**。令 `half = (m + n + 1) // 2`。假設在 A 的位置 i 切一刀、在 B 的位置 j = half − i 切一刀，左邊共 `half` 個元素。如果左邊每個元素都 ≤ 右邊每個元素，左邊就恰好是合併後最小的 half 個數。因為 A、B 各自有序，「左邊 ≤ 右邊」只需要檢查兩個交叉條件：`A[i−1] <= B[j]` 和 `B[j−1] <= A[i]`。找到這個 i 之後，左半的最大值 `max(A[i−1], B[j−1])` 就是第 half 小的數；總長奇數時它就是中位數，偶數時再取右半的最小值 `min(A[i], B[j])` 平均。

**為什麼可以二分**。定義 `pred(i) = A[i] >= B[half − i − 1]`。i 增加 1 時，`A[i]` 往右移一格（不會變小），`B[j−1]` 往左移一格（不會變大），所以一旦 pred 成立，之後都成立：F…F T…T。取第一個讓 pred 為 True 的 i（若 `[0, m)` 中都不成立，就是 i = m，此時 A 全部進左半）。這個 i 滿足 `B[j−1] <= A[i]`（pred 為 True，或 i = m 時右邊沒有 A 的元素）；同時 pred(i − 1) 為 False，代入 j' = j + 1 得到 `A[i−1] < B[j]`，第二個條件也成立。所以第一個 True 就是正確的切法，不需要分別檢查兩個條件。

**為什麼在較短的陣列上搜尋**。若 m ≤ n，則 `half >= m`，於是對所有 i ∈ [0, m]，j = half − i 都落在 [0, n] 內，不會出現負的 j；而且迴圈中只會在 i < m 時讀 `A[i]`，此時 j ≥ 1，`B[j−1]` 也一定存在。換句話說，交換成「A 較短」之後，迴圈內完全不需要處理越界，只有最後計算左右最大最小值時要用 ±∞ 處理 i 或 j 在端點的情況。時間也因此是 O(log min(m, n))，比要求的更好。

```text
A = [1, 3, 8, 9, 15]（m = 5，較短），B = [7, 11, 18, 19, 21, 25]（n = 6）
half = (5 + 6 + 1) // 2 = 6，pred(i) = A[i] >= B[6 - i - 1]

步驟  lo  hi  i  j=6-i  A[i]  B[j-1]  pred  動作
 1     0   5  2    4      8     19     F    lo = 3   （A 拿太少，左半的 B[3]=19 太大）
 2     3   5  4    2     15     11     T    hi = 4
 3     3   4  3    3      9     18     F    lo = 4
結束  i = 4，j = 2

切法：
A:  1  3  8  9 | 15
B:  7 11       | 18 19 21 25
左半 = {1, 3, 8, 9, 7, 11}，max = max(A[3]=9, B[1]=11) = 11
右半 = {15, 18, 19, 21, 25}，min = min(A[4]=15, B[2]=18) = 15
總長 11 為奇數 → 中位數 = 11
```

第 1 步 i = 2 時，左半包含 B 的前 4 個（到 19），但 A[2] = 8 卻在右半，8 < 19 代表左右交錯，A 拿得太少，要往右；第 2 步 i = 4 時 A[4] = 15 ≥ B[1] = 11 成立，代表這個切法或更左的切法可能正確；第 3 步確認 i = 3 不行（A[3] = 9 < B[2] = 18，又交錯了），所以答案是 i = 4。

### 解法

```python
import random


def find_median_sorted_arrays(nums1: list[int], nums2: list[int]) -> float:
    A, B = (nums1, nums2) if len(nums1) <= len(nums2) else (nums2, nums1)
    m, n = len(A), len(B)
    half = (m + n + 1) // 2
    lo, hi = 0, m                       # i ∈ [0, m]；i = m 作為「全部 False」的結果
    while lo < hi:
        i = (lo + hi) // 2              # i < m，且 j = half - i >= 1
        if A[i] >= B[half - i - 1]:
            hi = i
        else:
            lo = i + 1
    i, j = lo, half - lo
    neg, pos = float("-inf"), float("inf")
    left_max = max(A[i - 1] if i > 0 else neg, B[j - 1] if j > 0 else neg)
    if (m + n) % 2 == 1:
        return float(left_max)
    right_min = min(A[i] if i < m else pos, B[j] if j < n else pos)
    return (left_max + right_min) / 2


def brute(a, b):
    c = sorted(a + b)
    k = len(c)
    return float(c[k // 2]) if k % 2 else (c[k // 2 - 1] + c[k // 2]) / 2


assert find_median_sorted_arrays([1, 3], [2]) == 2.0
assert find_median_sorted_arrays([1, 2], [3, 4]) == 2.5
assert find_median_sorted_arrays([1, 3, 8, 9, 15], [7, 11, 18, 19, 21, 25]) == 11.0
assert find_median_sorted_arrays([], [5]) == 5.0
assert find_median_sorted_arrays([1, 2], [10, 20]) == 6.0
assert find_median_sorted_arrays([10, 20], [1, 2]) == 6.0
assert find_median_sorted_arrays([2, 2], [2, 2, 2]) == 2.0
for _ in range(2000):
    a = sorted(random.randint(-10, 10) for _ in range(random.randint(0, 6)))
    b = sorted(random.randint(-10, 10) for _ in range(random.randint(0, 6)))
    if a or b:
        assert find_median_sorted_arrays(a, b) == brute(a, b)
print("all tests passed")
```

### 複雜度與邊界

時間 O(log min(m, n))：只在較短的陣列上二分。空間 O(1)。邊界情況：其中一個陣列為空時 m = 0，迴圈不執行，i = 0、j = half，答案完全來自 B；兩陣列值域不重疊時，i 會停在 0 或 m，計算左右極值時用 ±∞ 處理越界；有重複值時 pred 用 `>=`，相等的元素不論分到哪邊都不影響極值；`half` 用 `(m + n + 1) // 2` 讓奇數長度時左半多一個，於是中位數永遠是 `left_max`。記得先交換讓 A 較短，否則 j 可能為負，迴圈內讀到 `B[-1]` 這種 Python 不會報錯的錯誤索引。

### Follow-up

> [!question]- F1. 如果要找兩個排序陣列合併後的第 k 小（1-indexed）呢？
> 把 half 換成 k 即可，但 i 的範圍要改成 `[max(0, k − n), min(k, m)]`，因為 B 最多只能提供 n 個、A 最多提供 m 個。在這個範圍內 pred `A[i] >= B[k − i − 1]` 仍然單調，第一個 True 的 i 給出答案 `max(A[i−1], B[k−i−1])`。時間 O(log min(m, n, k))。
> ```python
> def kth_two(A, B, k):
>     if len(A) > len(B):
>         A, B = B, A
>     m, n = len(A), len(B)
>     lo, hi = max(0, k - n), min(k, m)
>     while lo < hi:
>         i = (lo + hi) // 2
>         if A[i] >= B[k - i - 1]:
>             hi = i
>         else:
>             lo = i + 1
>     i, j = lo, k - lo
>     return max(A[i - 1] if i > 0 else float("-inf"), B[j - 1] if j > 0 else float("-inf"))
> ```

> [!question]- F2. 如果是 k 個排序陣列的中位數呢？
> 切法的方法無法直接推廣到 k 個陣列，因為未知數從一個變成 k − 1 個。改用「對值二分」：答案是第一個讓「所有陣列中 ≤ x 的元素總數 ≥ t」的 x（t 是中位數的排名），每次用 k 次 `bisect_right` 計數，時間 O(k log n · log V)，V 是值域；偶數長度時找第 t 和第 t + 1 小。這和難題 3–5 的「第 k 小 = 計數二分」是同一個技巧。如果 k 很大而每個陣列很短，也可以用 heap 做 k-way merge（第 14 章），O(t log k)。

> [!question]- F3. 如果資料是串流，要隨時回報目前的中位數呢？
> 排序陣列的切法不再適用，因為每次插入都會改變陣列。標準做法是兩個 heap：一個 max-heap 存較小的一半、一個 min-heap 存較大的一半，維持兩者大小差不超過 1，插入 O(log n)、查詢 O(1)，這是第 14 章難題 1（295. Find Median from Data Stream）。若還需要刪除任意元素（滑動視窗中位數），就是第 14 章難題 2（480）。

> [!question]- F4. 如果兩個陣列分別存放在兩台機器上，每次只能遠端讀取一個元素，怎麼讓往返次數最少？
> 本題的切法二分每一輪只需要讀 `A[i]` 和 `B[j−1]` 兩個值，結束時再讀最多四個邊界值，所以總共 O(log min(m, n)) 次遠端讀取，兩台機器的讀取可以並行，往返輪數就是二分的輪數。相比之下，合併法需要 O(m + n) 次讀取；對值二分每輪要在兩台機器上各自做一次 binary search，總讀取數是 O(log V · log n)。在分散式系統中，這種「每輪交換常數個值」的特性很重要。

### 心得

關鍵突破是把「找中位數」改寫成「找一個切點 i，使左半恰好是最小的 half 個數」，而切點的合法性對 i 單調，所以又回到第一個 True 的模板。它和本章其他題的關係是：核心題 1–3 在一個陣列的索引上二分，這題在一個「切法」的索引上二分；難題 3–5 則是在值上二分。面試時建議先說 O(m + n) 的合併法，再說「我想在較短陣列上二分切點」，畫出 `A[i−1] | A[i]`、`B[j−1] | B[j]` 的交叉條件，最後說明為什麼第一個讓 `A[i] >= B[j−1]` 的 i 同時滿足另一個條件。把交叉條件畫出來，比背公式更容易讓面試官跟上。

## 難題 2｜410. Split Array Largest Sum｜Hard

### 題目

給一個非負整數陣列 `nums` 和整數 k，把 `nums` 切成 k 段**非空的連續子陣列**，使得各段總和中的最大值盡可能小，回傳這個最小的最大段和。限制：`1 <= len(nums) <= 1000`，`0 <= nums[i] <= 10⁶`，`1 <= k <= min(50, len(nums))`。

- 範例 1：`nums = [7, 2, 5, 10, 8]`、`k = 2`，回傳 `18`。最佳切法是 `[7, 2, 5]` 與 `[10, 8]`，兩段和為 14 與 18。
- 範例 2：`nums = [1, 2, 3, 4, 5]`、`k = 2`，回傳 `9`（`[1, 2, 3]` 與 `[4, 5]`）。
- 範例 3（邊界）：`nums = [1, 4, 4]`、`k = 3`，回傳 `4`，每個元素一段，答案是最大元素。
- 範例 4（邊界）：`nums = [0, 0, 0]`、`k = 2`，回傳 `0`；k = 1 時答案是總和。

### 提示

> [!tip]- 提示 1
> 「最小化最大值」是答案空間 binary search 最典型的訊號。先別想怎麼切，想想：如果規定每段和都不能超過 X，能不能判斷做不做得到？

> [!tip]- 提示 2
> 給定 X，用貪婪從左往右盡量把元素塞進目前這段，超過 X 就開新的一段，得到最少需要的段數。為什麼貪婪是最少的？X 越大段數會怎樣變化？

> [!tip]- 提示 3
> pred(X) = 「最少段數 ≤ k」對 X 單調。段數 < k 時也算可行，因為可以把某段再切開而不增加最大值。範圍是 `[max(nums), sum(nums)]`，找第一個 True。

### 詳解

**為什麼直覺做法不夠**。直接構造切法需要決定 k − 1 個切點，暴力列舉是 C(n − 1, k − 1)，指數級。標準的 DP 是 `dp[j][i]` = 把前 i 個元素切成 j 段的最小最大段和，轉移要枚舉最後一段的起點，`dp[j][i] = min over p (max(dp[j−1][p], sum(p..i−1)))`，時間 O(k · n²)，n = 1000、k = 50 時是 5 × 10⁷，在 Python 中偏慢，而且這個解法完全沒有利用「和是非負」的結構。

**突破點：把最佳化變成判定**。固定一個上限 X，問「能否把 nums 切成不超過 k 段，每段和 ≤ X」。這個判定問題可以用貪婪 O(n) 解決：從左往右累加，加上下一個元素會超過 X 時就切一刀。貪婪得到的段數是最少的，理由是交換論證：任何合法切法的第一段，長度都不會超過貪婪的第一段（貪婪已經塞到極限），所以貪婪剩下的後綴是任何切法剩下後綴的子集；因為元素非負，後綴越短需要的段數只會越少，歸納下去，貪婪的段數 ≤ 任何合法切法。

**單調性與「≤ k 段」**。X 變大時，同樣的切法仍然合法，所以最少段數不增，`pred(X) = 最少段數 <= k` 是 F…F T…T。為什麼段數小於 k 也算可行？因為 n ≥ k，可以把任一個長度 ≥ 2 的段再切開，每切一次段數加一，而切開不會讓任何一段的和變大（元素非負），所以「≤ k 段可行」等價於「恰好 k 段可行」。下界是 `max(nums)`（每個元素都必須完整放進某一段），上界是 `sum(nums)`（一段就全包，一定可行）。

**答案一定是某一段的實際和**。第一個 True 的 X*，貪婪切法的最大段和 M ≤ X*；若 M < X*，則 M 本身也可行，與 X* 是第一個 True 矛盾，所以 M = X*，答案真的能被某個切法達到。這和難題 3 的「答案一定在表中」是同一種論證。

```text
nums = [7, 2, 5, 10, 8]，k = 2，範圍 [10, 32]
X:        10 11 12 13 14 15 16 17 18 19 … 31 32
最少段數:   4  4  4  4  3  3  3  3  2  2 …  2  1
<= 2 ?     F  F  F  F  F  F  F  F  T  T …  T  T

步驟  lo  hi  mid  貪婪切法                          段數  pred  動作
 1    10  32  21   [7 2 5] [10 8]                    2    T    hi = 21
 2    10  21  15   [7 2 5] [10] [8]                  3    F    lo = 16
 3    16  21  18   [7 2 5] [10 8]                    2    T    hi = 18
 4    16  18  17   [7 2 5] [10] [8]                  3    F    lo = 18
結束  lo = hi = 18
```

第 1 步 X = 21 很寬鬆，兩段就夠；第 2 步 X = 15 時 10 + 8 = 18 超過，被迫切成三段；第 3、4 步夾出邊界：17 不行（10 和 8 放不進同一段），18 剛好可以，而 18 也正是 `[10, 8]` 這一段的實際和。

### 解法

```python
import random
from functools import cache


def split_array(nums: list[int], k: int) -> int:
    def pieces(limit: int) -> int:
        count, cur = 1, 0
        for x in nums:
            if cur + x > limit:
                count += 1
                cur = 0
            cur += x
        return count

    lo, hi = max(nums), sum(nums)
    while lo < hi:
        mid = (lo + hi) // 2
        if pieces(mid) <= k:
            hi = mid
        else:
            lo = mid + 1
    return lo


def split_array_dp(nums: list[int], k: int) -> int:
    """O(k · n²) 的 DP，作為對照。"""
    n = len(nums)
    prefix = [0]
    for x in nums:
        prefix.append(prefix[-1] + x)

    @cache
    def dp(i: int, j: int) -> int:     # nums[i:] 切成恰好 j 段非空子陣列
        if j == 1:
            return prefix[n] - prefix[i]
        best = float("inf")
        for p in range(i + 1, n - j + 2):   # 第一段是 nums[i:p]，剩下至少 j - 1 個元素
            best = min(best, max(prefix[p] - prefix[i], dp(p, j - 1)))
        return best

    return dp(0, k)


assert split_array([7, 2, 5, 10, 8], 2) == 18
assert split_array([1, 2, 3, 4, 5], 2) == 9
assert split_array([1, 4, 4], 3) == 4
assert split_array([0, 0, 0], 2) == 0
assert split_array([5, 1, 1], 1) == 7
assert split_array([10**6] * 3, 2) == 2 * 10**6
for _ in range(300):
    arr = [random.randint(0, 9) for _ in range(random.randint(1, 8))]
    kk = random.randint(1, len(arr))
    assert split_array(arr, kk) == split_array_dp(arr, kk)
print("all tests passed")
```

### 複雜度與邊界

Binary search 版本時間 O(n log S)，S = `sum(nums)` ≤ 10⁹，約 30 輪，每輪 O(n)；空間 O(1)。DP 版本 O(k · n²) 時間、O(k · n) 空間。邊界情況：全為 0 時 lo = hi = 0，直接回傳；k = n 時答案是 `max(nums)`，pred(lo) 即為 True；k = 1 時答案是總和。下界不能取 0 或 1：若 X 小於某個元素，貪婪會讓它獨佔一段卻沒發現超過上限，回傳一個偏小的段數而誤判為可行。

### Follow-up

> [!question]- F1. 如果 nums 可以有負數呢？
> 二分框架會失效，原因有兩個：貪婪不再最佳（後面的負數可能讓「多塞一個」變得有利，例如上限 5 時 `[3, 4, -4]` 可以放成一段，但貪婪在 3 + 4 > 5 時就切開了），而且「≤ k 段可行」不再等價於「恰好 k 段可行」（把段切開可能讓某段的和變大）。可行性對 X 仍然單調，但檢查本身要改成 DP：對固定 X，`f[i]` = 前 i 個元素切成每段 ≤ X 的段數範圍，或直接用原本的 O(k · n²) DP 求最佳化版本。面試時能指出「非負」是貪婪的必要條件，就是最好的回答。

> [!question]- F2. 如果目標變成「最大化最小段和」呢（1231. Divide Chocolate）？
> 對稱地，pred(X) = 「每段和都 ≥ X 時，貪婪最多能切出幾段」≥ k，X 越大越難，序列是 T…T F…F，要找最後一個 True，用 8.3 節的 `last_true`。貪婪是累加到 ≥ X 就切一刀並重新開始，最後不足 X 的尾巴併入前一段（不會讓那段變小）。範圍是 `[min(nums), sum(nums) // k]`，時間同樣 O(n log S)。注意 1231 原題的 k 是朋友人數，巧克力要切成 k + 1 塊（自己拿最小的那塊），套用時要把段數換成 k + 1。

> [!question]- F3. 如果每段的成本不是總和，而是「段內最大值減最小值」呢？
> 只要成本對「段的延伸」單調不減，同一個框架就成立。最大值減最小值在段變長時只會變大或不變，所以貪婪「盡量延伸，超過 X 就切」仍然最佳，可行性對 X 單調。檢查時維護目前段的最大值與最小值，O(n)；答案範圍是 `[0, max(nums) − min(nums)]`，總時間 O(n log V)。反之，若成本是「段內平均值」，延伸可能讓成本下降，貪婪就不成立，要回到 DP。

> [!question]- F4. 如果還要回傳實際的切點呢？
> 先二分得到 X*，再用同樣的貪婪跑一次記錄切點，O(n)。若貪婪得到的段數 c < k，需要再補 k − c 刀：從右往左（或任意順序）在還沒切過的位置補切，只要每段非空即可，因為切開不會讓任何段變大。也可以用「從右往左貪婪，同時保證剩下的元素數 ≥ 剩下要切的段數」一次完成，避免第二輪調整。

### 心得

關鍵突破是把「最小化最大段和」改寫成判定問題「每段 ≤ X 時最少要幾段」，而這個判定有 O(n) 的貪婪解，可行性又對 X 單調。它和核心題 5（1011）其實是同一題：運貨的「天數」就是這裡的「段數」，所以真正的難度不在二分，而在說清楚兩件事：貪婪為什麼最少（交換論證，依賴元素非負），以及「≤ k 段可行」為什麼等價於「恰好 k 段可行」。面試時可以先提 O(k · n²) 的 DP 作為正確但較慢的基準，再提出二分答案，並主動說明非負的前提；如果面試官追問負數，就能自然接到 F1。

## 難題 3｜668. Kth Smallest Number in Multiplication Table｜Hard

### 題目

一張 m × n 的乘法表，第 i 列第 j 行（皆從 1 開始）的值是 i × j。給 m、n、k，回傳表中所有 m·n 個數（含重複）由小到大排序後的第 k 個。限制：`1 <= m, n <= 3 × 10⁴`，`1 <= k <= m × n`。

- 範例 1：`m = 3, n = 3, k = 5`，表中的數排序後是 `1, 2, 2, 3, 3, 4, 6, 6, 9`，第 5 個是 `3`。
- 範例 2：`m = 2, n = 3, k = 6`，排序後是 `1, 2, 2, 3, 4, 6`，回傳 `6`。
- 範例 3（邊界）：`m = 1, n = 5, k = 3`，表只有一列 `1 2 3 4 5`，回傳 `3`。
- 範例 4（邊界）：`k = 1` 時回傳 `1`；`k = m × n` 時回傳 `m × n`。

### 提示

> [!tip]- 提示 1
> m·n 最多 9 × 10⁸，不能把表列出來排序，連用 heap 走 k 步都可能太慢。換個問題：給一個數 x，表中有幾個數 ≤ x？

> [!tip]- 提示 2
> 第 i 列是 i, 2i, 3i, …, ni，其中 ≤ x 的有 min(x // i, n) 個。整張表的計數只要 O(m)。

> [!tip]- 提示 3
> count(x) 對 x 單調不減。第 k 小就是第一個讓 count(x) ≥ k 的 x，範圍 `[1, m·n]`。

### 詳解

**為什麼直覺做法不夠**。列出全部 m·n 個數再排序是 O(mn log(mn))，9 × 10⁸ 個數連記憶體都放不下。把每一列看成一條排序串列，用 heap 做 k-way merge（第 14 章），每次彈出最小值再推入同列的下一個，時間 O(k log m)；但 k 可以到 9 × 10⁸，仍然太慢。問題在於這些做法都在「逐一走過」比答案小的數，而答案的排名 k 本身就很大。

**突破點：把「第 k 小」變成計數**。我們不需要知道比答案小的數是哪些，只需要知道有多少個。對任意 x，第 i 列 `i, 2i, …, ni` 中 ≤ x 的個數是 `min(x // i, n)`，所以 `count(x) = Σ_{i=1..m} min(x // i, n)`，O(m) 就能算出。count 對 x 單調不減，`pred(x) = count(x) >= k` 是 F…F T…T，第一個 True 就是答案。搜尋範圍是 `[1, m·n]`，m·n 一定滿足 count = m·n ≥ k，可以當作半開區間的 `hi`。

**為什麼答案一定在表中**。二分找到的是一個整數 x*，它不一定看起來「像」表中的數。但 x* 是第一個讓 count ≥ k 的值，所以 count(x* − 1) < k ≤ count(x*)，代表恰好等於 x* 的數至少有一個（count 增加了），x* 確實出現在表中，而且它就是排序後第 k 個。這個論證適用於所有「計數二分求第 k 小」的題目，包括難題 4 和難題 5，也是為什麼條件必須寫成 `>= k`：若寫成 `> k` 或用 count(< x)，邊界就會偏移一格。

```text
m = 3, n = 3, k = 5
乘法表：          x 與 count(x) = Σ min(x // i, 3)
  1  2  3        x:      1  2  3  4  5  6  7  8  9
  2  4  6        count:  1  3  5  6  6  8  8  8  9
  3  6  9        >= 5 ?  F  F  T  T  T  T  T  T  T

搜尋範圍 [1, 9)，9 = m·n 一定可行
步驟  lo  hi  mid  每列計數 (列1, 列2, 列3)   count  pred  動作
 1     1   9   5   (3, 2, 1)                  6     T    hi = 5
 2     1   5   3   (3, 1, 1)                  5     T    hi = 3
 3     1   3   2   (2, 1, 0)                  3     F    lo = 3
結束  lo = hi = 3
```

第 1 步：x = 5 時第一列 1、2、3 都 ≤ 5，第二列 2、4 兩個，第三列只有 3，共 6 個，已經 ≥ 5，答案 ≤ 5。第 2 步：x = 3 時共 5 個，剛好 ≥ 5。第 3 步：x = 2 只有 3 個，不夠，所以答案是 3。注意 count(4) 和 count(5) 都是 6，表中沒有 5；二分不會停在 5，因為它找的是第一個 True。

### 解法

```python
import random


def find_kth_number(m: int, n: int, k: int) -> int:
    if m > n:
        m, n = n, m                     # 迭代較短的那一維

    def count(x: int) -> int:
        total = 0
        for i in range(1, m + 1):
            if i > x:                   # 之後每一列的第一個數都 > x
                break
            total += min(x // i, n)
        return total

    lo, hi = 1, m * n
    while lo < hi:
        mid = (lo + hi) // 2
        if count(mid) >= k:
            hi = mid
        else:
            lo = mid + 1
    return lo


def brute(m, n, k):
    return sorted(i * j for i in range(1, m + 1) for j in range(1, n + 1))[k - 1]


assert find_kth_number(3, 3, 5) == 3
assert find_kth_number(2, 3, 6) == 6
assert find_kth_number(1, 5, 3) == 3
assert find_kth_number(4, 4, 1) == 1
assert find_kth_number(4, 4, 16) == 16
assert find_kth_number(30000, 30000, 450000000) > 0     # 最大規模也能在時限內完成
for _ in range(300):
    m, n = random.randint(1, 8), random.randint(1, 8)
    k = random.randint(1, m * n)
    assert find_kth_number(m, n, k) == brute(m, n, k)
print("all tests passed")
```

### 複雜度與邊界

時間 O(min(m, n) · log(mn))：二分約 log₂(9 × 10⁸) ≈ 30 輪，每輪迭代較短的一維。空間 O(1)。邊界情況：m = 1 時表就是 `1..n`，答案是 k；k = 1 時 count(1) = 1 ≥ 1，答案 1；k = m·n 時答案是 m·n；`i > x` 時提早結束迴圈，對小的 mid 能省下很多時間；計數最大是 9 × 10⁸，Python 不溢位，在 Java 中用 `int` 尚可，但 `m * n` 的乘法要小心。

### Follow-up

> [!question]- F1. 如果矩陣不是乘法表，而是一般的「每列、每行都遞增」的 n × n 矩陣呢（378. Kth Smallest Element in a Sorted Matrix）？
> 同樣對值二分，但不能再用公式 `x // i` 計數，改用 staircase（階梯）走法：從左下角出發，若當前值 ≤ x，這一列從 0 到當前行的元素都 ≤ x，計數加上「行號 + 1」並往右；否則往上。每次計數 O(n)，總時間 O(n log V)，V 是值域。另一種做法是 heap 做 k-way merge，O(k log n)，k 小時較快。

> [!question]- F2. 如果要第 k 大呢？
> 第 k 大等於第 m·n − k + 1 小，直接呼叫 `find_kth_number(m, n, m * n - k + 1)`，O(min(m, n) log(mn))。也可以直接二分「≥ x 的個數 ≥ k」的最後一個 x，計數式改成 Σ (n − ⌈x / i⌉ + 1) 的非負部分，但轉換成第 k 小比較不容易寫錯，面試時建議用轉換。

> [!question]- F3. 如果表改成加法表（第 i 列第 j 行是 i + j）呢？
> 只要能快速計數，框架完全一樣。第 i 列是 i + 1, i + 2, …, i + n，其中 ≤ x 的個數是 `max(0, min(n, x − i))`，count 仍然 O(m)，範圍是 `[2, m + n]`。更一般地，任何「每列都是排序序列、且能 O(1) 或 O(log n) 算出列內 ≤ x 個數」的隱式矩陣，都可以用這個方法，例如第 k 小的 `a[i] + b[j]` 就是把兩個排序陣列看成加法表（373 題的計數版）。

> [!question]- F4. 如果 k 很小（例如 k ≤ 10⁴）而 m、n 很大呢？
> 這時 heap 更直接：把每列的第一個數 `(i, i, 1)` 放進 min-heap，但只放前 min(m, k) 列（第 k 小不可能在第 k 列之後出現，因為第 i 列最小是 i），彈出 k 次，每次推入同列下一個數。時間 O(k log min(m, k))，與 m、n 無關。面試中可以說：k 小用 heap，k 大用計數二分，兩者的分界取決於 k 與 min(m, n) · log(mn) 的大小。

### 心得

關鍵突破是「第 k 小 = 第一個讓 count(≤ x) ≥ k 的 x」，把一個需要列舉 k 個元素的問題，變成 log(值域) 次的計數。和本章的關係：它是答案空間二分（核心題 4、5）的計數版本，pred 從「做得到嗎」換成「夠 k 個嗎」；難題 4、5 是同一個模板，只是計數函式更難寫。面試時先說 heap 的 O(k log m)，指出 k 可達 9 × 10⁸，然後提出計數二分，並主動解釋「為什麼二分出來的數一定在表中」，這是面試官最常追問的一點。

## 難題 4｜719. Find K-th Smallest Pair Distance｜Hard

### 題目

給一個整數陣列 `nums` 和整數 k。一個數對 `(i, j)`（i < j）的距離定義為 `|nums[i] − nums[j]|`。在所有 n(n − 1)/2 個數對的距離中，回傳第 k 小的那一個。限制：`2 <= n <= 10⁴`，`0 <= nums[i] <= 10⁶`，`1 <= k <= n(n − 1)/2`。

- 範例 1：`nums = [1, 3, 1]`、`k = 1`，三個距離是 2、0、2，第 1 小是 `0`。
- 範例 2：`nums = [1, 6, 1]`、`k = 3`，距離是 5、0、5，排序後 `0, 5, 5`，回傳 `5`。
- 範例 3：`nums = [1, 3, 4, 8]`、`k = 3`，六個距離排序後 `1, 2, 3, 4, 5, 7`，回傳 `3`。
- 範例 4（邊界）：`nums = [1, 1, 1]`、`k = 2`，所有距離都是 0，回傳 `0`。

### 提示

> [!tip]- 提示 1
> 數對有 n(n − 1)/2 ≈ 5 × 10⁷ 個，列舉後排序太慢。距離的值域只有 `[0, 10⁶]`，能不能在值上二分？

> [!tip]- 提示 2
> 給定 d，「距離 ≤ d 的數對有幾個」要怎麼快速計算？先排序，數對的距離就變成 `nums[j] − nums[i]`（j > i）。

> [!tip]- 提示 3
> 排序後，對每個右端點 j，滿足 `nums[j] − nums[i] <= d` 的 i 形成一段連續區間 `[left, j)`，而且 j 往右時 left 只會往右。用 two pointers 在 O(n) 內算出總數，再找第一個讓計數 ≥ k 的 d。

### 詳解

**為什麼直覺做法不夠**。列出所有距離再排序是 O(n² log n)，n = 10⁴ 時有 5 × 10⁷ 個距離，時間和記憶體都不夠。用 quickselect 可以做到 O(n²) 期望時間，但仍要先產生 5 × 10⁷ 個距離。用 heap：排序後每個 i 的距離 `nums[i+1] − nums[i], nums[i+2] − nums[i], …` 是遞增序列，k-way merge 走 k 步，O((n + k) log n)，但 k 最大也是 5 × 10⁷。和難題 3 一樣，瓶頸是「逐一走過比答案小的距離」。

**突破點：在距離的值上二分，用 two pointers 計數**。排序不會改變數對距離的多重集合，所以先排序。對一個 d，定義 `count(d)` = 距離 ≤ d 的數對數。排序後，固定右端點 j，所有 `nums[j] − nums[i] <= d` 的 i 是 j 左邊連續的一段 `[left, j)`，貢獻 `j − left` 個數對；j 往右移時 `nums[j]` 變大，left 只會往右（不會往回），這正是第 5 章 two pointers／第 6 章 sliding window 的單調性，所以一輪計數 O(n)。count 對 d 單調不減，第 k 小就是第一個讓 count(d) ≥ k 的 d，範圍 `[0, max − min]`，上界一定讓所有數對都被算到。

**正確性**。和難題 3 相同：第一個 True 的 d* 滿足 count(d* − 1) < k ≤ count(d*)，所以恰好有距離等於 d*，它是第 k 小。計數用 two pointers 而不是對每個 j 做 `bisect`，是因為 bisect 版本每輪 O(n log n)，雖然也能通過，但 two pointers 更快、也更能展現你看出了單調性。

```text
排序後 nums = [1, 3, 4, 8]，k = 3，範圍 [0, 7]（7 = 8 - 1）
d:        0  1  2  3  4  5  6  7
count(d): 0  1  2  3  4  5  5  6
>= 3 ?    F  F  F  T  T  T  T  T

計數 d = 2 的 two pointers 過程（left 只往右）：
j=0  nums[j]=1  left=0                         貢獻 0
j=1  nums[j]=3  3-1=2 <= 2，left=0              貢獻 1  (1,3)
j=2  nums[j]=4  4-1=3 > 2 → left=1；4-3=1 <= 2  貢獻 1  (3,4)
j=3  nums[j]=8  8-3>2、8-4>2 → left=3           貢獻 0
count(2) = 2 < 3 → F

二分過程（範圍 [0, 7)，7 一定可行）
步驟  lo  hi  mid  count  pred  動作
 1     0   7   3     3     T    hi = 3
 2     0   3   1     1     F    lo = 2
 3     2   3   2     2     F    lo = 3
結束  lo = hi = 3
```

d = 2 的計數展示了 left 的單調性：處理 j = 2 時 left 從 0 移到 1，處理 j = 3 時一路移到 3，之後不會回頭，所以整輪最多移動 n 次。二分只需要三次計數就確定答案是 3，也就是數對 (1, 4) 的距離。

### 解法

```python
import random
from itertools import combinations


def smallest_distance_pair(nums: list[int], k: int) -> int:
    nums = sorted(nums)
    n = len(nums)

    def count(d: int) -> int:           # 距離 <= d 的數對數
        total = left = 0
        for j in range(n):
            while nums[j] - nums[left] > d:
                left += 1
            total += j - left
        return total

    lo, hi = 0, nums[-1] - nums[0]
    while lo < hi:
        mid = (lo + hi) // 2
        if count(mid) >= k:
            hi = mid
        else:
            lo = mid + 1
    return lo


def brute(nums, k):
    return sorted(abs(a - b) for a, b in combinations(nums, 2))[k - 1]


assert smallest_distance_pair([1, 3, 1], 1) == 0
assert smallest_distance_pair([1, 6, 1], 3) == 5
assert smallest_distance_pair([1, 3, 4, 8], 3) == 3
assert smallest_distance_pair([1, 1, 1], 2) == 0
assert smallest_distance_pair([0, 1000000], 1) == 1000000
for _ in range(300):
    arr = [random.randint(0, 20) for _ in range(random.randint(2, 8))]
    kk = random.randint(1, len(arr) * (len(arr) - 1) // 2)
    assert smallest_distance_pair(arr, kk) == brute(arr, kk)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n log n + n log W)，W = `max − min` ≤ 10⁶：排序一次，二分約 20 輪，每輪 two pointers O(n)。空間 O(n)（排序的副本；若可以修改輸入則為 O(1) 額外空間）。邊界情況：所有元素相同時 hi = 0，迴圈不執行，回傳 0；n = 2 時只有一個數對，k 必為 1；while 迴圈中 `left` 不會超過 j，因為 `nums[j] − nums[j] = 0 <= d`，不需要額外判斷 `left < j`。

### Follow-up

> [!question]- F1. 如果 k 很小（例如 k ≤ n）呢？
> 改用 heap：排序後，把每個 i 的最小距離 `(nums[i+1] − nums[i], i, i+1)` 放進 min-heap，彈出 k 次，每次彈出 `(d, i, j)` 後推入 `(nums[j+1] − nums[i], i, j+1)`（若 j + 1 < n）。時間 O((n + k) log n)。k 小時比二分直接；k 接近 n² 時退化成 O(n² log n)。面試中可以先問 k 的範圍，再決定用哪種，這正是「從限制推 pattern」（第 3 章）的應用。

> [!question]- F2. 如果要找第 k 大的距離呢？
> 第 k 大是第 `n(n − 1)/2 − k + 1` 小，直接轉換，O(n log n + n log W)。不要另外寫一個 last_true 版本的計數，因為轉換最不容易出錯。若同時要很多個 k 的答案，每個查詢各做一次二分，計數成本 O(n) 不變。

> [!question]- F3. 如果改成第 k 小的「數對和」 nums[i] + nums[j] 呢？
> 一樣對值二分。排序後計算「和 ≤ s 的數對」用相向的 two pointers（第 5 章核心題 1 的套路）：`i` 從左、`j` 從右，若 `nums[i] + nums[j] <= s`，則 i 與 (i, j] 中所有元素配對都 ≤ s，計數加 `j − i` 並 `i += 1`，否則 `j -= 1`。每輪 O(n)，範圍 `[2·min, 2·max]`，總時間 O(n log n + n log V)。

> [!question]- F4. 如果 nums 的值域很小（例如 W ≤ 1000）但 n 很大（10⁶）呢？
> 改用計數：先統計每個值出現的次數 `cnt[v]`，距離為 0 的數對數是 Σ C(cnt[v], 2)，距離為 d > 0 的是 Σ cnt[v] · cnt[v + d]。全部算出需要 O(W²)，然後從 d = 0 往上累加到 ≥ k，總時間 O(n + W²)，與 n² 無關。這時二分也行（每輪 O(W) 在值域上做 two pointers），但直接計數更簡單。

### 心得

關鍵突破是「排序後，距離 ≤ d 的數對是每個 j 左邊連續的一段」，讓計數變成 two pointers 的 O(n)。這題把三個 pattern 串在一起：排序（打破 i < j 的順序限制）、計數二分（難題 3 的模板）、two pointers（第 5 章）。面試時的敘事是：先說數對太多無法列舉，再說「我在距離的值上二分，問題變成數有幾個數對距離 ≤ d」，最後說明 left 的單調性讓計數變成 O(n)。能把三個步驟分開說清楚，比直接背程式更有說服力。

## 難題 5｜2040. Kth Smallest Product of Two Sorted Arrays｜Hard

### 題目

給兩個由小到大排序的整數陣列 `nums1`（長度 m）、`nums2`（長度 n），以及整數 k。考慮所有 m·n 個乘積 `nums1[i] × nums2[j]`，回傳由小到大第 k 個（1-indexed）。陣列中**可以有負數和 0**。限制：`1 <= m, n <= 5 × 10⁴`，元素在 `-10⁵` 到 `10⁵` 之間，`1 <= k <= m × n`。

- 範例 1：`nums1 = [2, 5]`、`nums2 = [3, 4]`、`k = 2`，乘積 `6, 8, 15, 20`，回傳 `8`。
- 範例 2：`nums1 = [-4, -2, 0, 3]`、`nums2 = [2, 4]`、`k = 6`，乘積排序後 `-16, -8, -8, -4, 0, 0, 6, 12`，回傳 `0`。
- 範例 3：`nums1 = [-2, -1, 0, 1, 2]`、`nums2 = [-3, -1, 2, 4, 5]`、`k = 3`，回傳 `-6`。
- 範例 4（邊界）：`nums1 = [-1]`、`nums2 = [-1]`、`k = 1`，回傳 `1`；全部是 0 時回傳 `0`。

### 提示

> [!tip]- 提示 1
> 這是難題 3 的延伸：m·n 最多 2.5 × 10⁹ 個乘積，必須對乘積的值二分，問「≤ x 的乘積有幾個」。難的是負數。

> [!tip]- 提示 2
> 固定 a = nums1[i]，乘積 a × b 對 b 的單調方向取決於 a 的正負：a > 0 時遞增，a < 0 時遞減，a = 0 時恆為 0。所以 a × b ≤ x 的 b 在 nums2 中是一段前綴（a > 0）或後綴（a < 0）。

> [!tip]- 提示 3
> a > 0：b ≤ ⌊x / a⌋，個數是 `bisect_right(nums2, x // a)`；a < 0：b ≥ ⌈x / a⌉，個數是 `n − bisect_left(nums2, ceil(x / a))`；a = 0：x ≥ 0 時 n 個，否則 0 個。用整數運算算 floor 和 ceil，再找第一個讓計數 ≥ k 的 x。

### 詳解

**為什麼直覺做法不夠**。列出 2.5 × 10⁹ 個乘積不可能。heap 的 k-way merge 在全正數時可行（每列遞增），但有負數時「列」的方向會反轉：a < 0 的那一列，乘積隨 b 遞減，必須從右往左走；正負列混在一起後要四個方向分開處理，而且 k 仍可達 2.5 × 10⁹。另一個常見的直覺是「把正負分組、分別求第 k 小」，可以做，但邊界很多，容易寫錯。計數二分把所有情況統一成一個問題：給 x，數 ≤ x 的乘積有幾個。

**突破點：對每個 a 分正負號計數**。固定 a，我們要數 nums2 中有幾個 b 滿足 a·b ≤ x。a > 0 時兩邊除以 a 不變號，條件是 b ≤ x / a，因為 b 是整數，等價於 b ≤ ⌊x / a⌋，在排序的 nums2 中是一段前綴，個數 `bisect_right(nums2, x // a)`；Python 的 `//` 是向下取整，負的 x 也正確。a < 0 時除以 a 要變號，條件變成 b ≥ x / a，等價於 b ≥ ⌈x / a⌉，是一段後綴，個數 `n − bisect_left(nums2, ⌈x / a⌉)`；向上取整用整數寫成 `-((-x) // a)`，避免浮點誤差。a = 0 時所有乘積都是 0，x ≥ 0 則全部 n 個都算，否則 0 個。

**範圍與正確性**。所有乘積的最小值與最大值一定出現在四個「角落乘積」之中：`nums1[0]·nums2[0]`、`nums1[0]·nums2[-1]`、`nums1[-1]·nums2[0]`、`nums1[-1]·nums2[-1]`，因為固定 a 時 a·b 在 b 的端點取極值，而端點的乘積又在 a 的端點取極值。以四者的最小值為 lo、最大值為 hi，hi 一定滿足 count = m·n ≥ k。count 對 x 單調不減，第一個讓 count ≥ k 的 x 就是答案，理由同難題 3：count 在 x* 處跳升，代表有乘積恰好等於 x*。

```text
nums1 = [-4, -2, 0, 3]，nums2 = [2, 4]，k = 6
所有乘積排序：-16  -8  -8  -4   0   0   6  12
角落乘積：-8, -16, 6, 12 → 範圍 [-16, 12)

count(0) 的計算：
a = -4 (< 0)：需要 b >= ceil(0 / -4) = 0   → {2, 4}   2 個
a = -2 (< 0)：需要 b >= ceil(0 / -2) = 0   → {2, 4}   2 個
a =  0      ：x = 0 >= 0，全部             → 2 個
a =  3 (> 0)：需要 b <= floor(0 / 3) = 0   → {}       0 個
count(0) = 6 >= 6 → T

count(-1) 的計算：
a = -4：b >= ceil(-1 / -4) = ceil(0.25) = 1 → 2 個
a = -2：b >= ceil(-1 / -2) = ceil(0.5)  = 1 → 2 個
a =  0：x = -1 < 0                          → 0 個
a =  3：b <= floor(-1 / 3) = -1             → 0 個
count(-1) = 4 < 6 → F

二分過程
步驟  lo   hi  mid  count  pred  動作
 1   -16   12  -2     4     F    lo = -1
 2    -1   12   5     6     T    hi = 5
 3    -1    5   2     6     T    hi = 2
 4    -1    2   0     6     T    hi = 0
 5    -1    0  -1     4     F    lo = 0
結束  lo = hi = 0
```

第 1 步的 mid = (−16 + 12) // 2 = −2，Python 的向下取整在負數範圍也能讓 mid 落在 `[lo, hi)` 內。count(−1) 的計算展示了負數的關鍵：a = −4 時，−4·b ≤ −1 ⟺ b ≥ 0.25，向上取整成 1，nums2 中 2、4 都符合，對應乘積 −8、−16；若誤用向下取整得到 0，結果在這個例子剛好一樣，但在 nums2 含 0 時就會多算。

### 解法

```python
import random
from bisect import bisect_left, bisect_right


def kth_smallest_product(nums1: list[int], nums2: list[int], k: int) -> int:
    n = len(nums2)

    def count(x: int) -> int:                       # 乘積 <= x 的個數
        total = 0
        for a in nums1:
            if a > 0:
                total += bisect_right(nums2, x // a)        # b <= floor(x / a)
            elif a < 0:
                total += n - bisect_left(nums2, -((-x) // a))  # b >= ceil(x / a)
            elif x >= 0:
                total += n                                   # a = 0，乘積全為 0
        return total

    corners = [nums1[0] * nums2[0], nums1[0] * nums2[-1],
               nums1[-1] * nums2[0], nums1[-1] * nums2[-1]]
    lo, hi = min(corners), max(corners)
    while lo < hi:
        mid = (lo + hi) // 2
        if count(mid) >= k:
            hi = mid
        else:
            lo = mid + 1
    return lo


def brute(a, b, k):
    return sorted(x * y for x in a for y in b)[k - 1]


assert kth_smallest_product([2, 5], [3, 4], 2) == 8
assert kth_smallest_product([-4, -2, 0, 3], [2, 4], 6) == 0
assert kth_smallest_product([-2, -1, 0, 1, 2], [-3, -1, 2, 4, 5], 3) == -6
assert kth_smallest_product([-1], [-1], 1) == 1
assert kth_smallest_product([0, 0], [0], 2) == 0
assert kth_smallest_product([-100000], [100000], 1) == -10**10
for _ in range(500):
    a = sorted(random.randint(-6, 6) for _ in range(random.randint(1, 6)))
    b = sorted(random.randint(-6, 6) for _ in range(random.randint(1, 6)))
    kk = random.randint(1, len(a) * len(b))
    assert kth_smallest_product(a, b, kk) == brute(a, b, kk)
print("all tests passed")
```

### 複雜度與邊界

時間 O(m log n · log V)，V 是乘積範圍（最大 2 × 10¹⁰，約 35 輪），每輪對 nums1 每個元素做一次 bisect。可以先交換讓 nums1 是較短的陣列，變成 O(min(m, n) · log max(m, n) · log V)。空間 O(1)。邊界情況：x 為負時 `x // a`（a > 0）向下取整，例如 −1 // 3 = −1，正確排除了 b = 0；a < 0 時必須用向上取整，`-((-x) // a)` 對所有符號組合都正確；全為 0 時四個角落都是 0，lo = hi = 0；乘積可達 10¹⁰，超過 32 位元，在 Java／C++ 中要用 64 位元整數，而且要小心 `lo + hi` 的溢位與負數除法向零取整的差異（C++ 的 `/` 不是向下取整）。

### Follow-up

> [!question]- F1. 計數能不能從 O(m log n) 降到 O(m + n)？
> 可以。把 nums1 分成負數、零、正數三組。對正數組，a 由小到大時 ⌊x / a⌋ 對 x ≥ 0 是遞減、對 x < 0 是遞增，所以滿足條件的前綴長度單調變化，可以用一個在 nums2 上單向移動的指標取代 bisect；負數組同理用另一個指標處理後綴。每輪計數變成 O(m + n)，總時間 O((m + n) log V)。這和難題 4 用 two pointers 取代 bisect 是同一個優化思路，但這裡方向依 x 的正負而定，實作時要分四種情況，面試中通常說明思路即可，寫 bisect 版本已經足夠。

> [!question]- F2. 如果兩個陣列都只有非負數呢？
> 計數只剩 a > 0 和 a = 0 兩種情況，而且可以用 staircase two pointers：a 由小到大時 ⌊x / a⌋ 遞減，所以 nums2 上的指標只往左移，一輪 O(m + n)。範圍是 `[0, nums1[-1] · nums2[-1]]`。若 k 很小，也可以用 heap 做 k-way merge（373. Find K Pairs with Smallest Sums 的乘積版），O(k log m)。

> [!question]- F3. 如果要的是第 k 小的「和」 nums1[i] + nums2[j] 呢？
> 和不會有正負號翻轉的問題，計數更簡單：對每個 a，個數是 `bisect_right(nums2, x − a)`；或用 staircase two pointers O(m + n)。範圍是 `[nums1[0] + nums2[0], nums1[-1] + nums2[-1]]`。k 小時用 heap（373 題），O(k log min(m, k))。這個對比說明了 2040 的難點完全在計數函式，二分框架和難題 3、4 一模一樣。

> [!question]- F4. 如果有三個排序陣列，要第 k 小的 a · b · c 呢？
> 仍然可以對值二分，但計數要變成「對每一對 (a, b) 數有幾個 c 讓 a·b·c ≤ x」，O(n² log n)，或先把 a·b 的所有乘積排序（n² 個）再用本題的方法對 c 計數。值域變成 10¹⁵，約 50 輪。這類問題在面試中出現時，重點是說出「每多一個陣列，計數的成本乘上 n」，以及什麼時候該先把兩個陣列合併成一個排序的乘積陣列（若 n² 放得進記憶體）。

### 心得

關鍵突破是固定一邊後，乘積對另一邊單調，而方向由正負號決定，於是 ≤ x 的乘積在每一列都是一段前綴或後綴。它是難題 3（乘法表）的推廣：乘法表的每一列都是正數、方向固定，這題的列有三種方向，難度全部集中在計數函式的 floor／ceil 處理。面試時先說「對值二分、問 ≤ x 有幾個」，讓面試官知道你看出了框架，再仔細寫三種情況的計數，最後用一個 x 為負、a 為負的例子手動驗證取整方向，這是最容易出錯也最能展現細心的地方。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 精確查找 | 排序陣列中找某個值，找到即可 | 閉區間 `lo <= hi`，命中就回傳 | 704 Binary Search、74 Search a 2D Matrix |
| 找邊界（lower／upper bound） | 第一個、最後一個、插入位置、出現次數 | `first_true` 搭配 `>=`／`>`；`bisect_left`／`bisect_right` | 核心題 1（34）、35、278 First Bad Version |
| 部分有序 | 旋轉陣列、山形陣列、峰值 | 找出對索引單調的性質（`nums[i] <= nums[-1]`），或判斷哪一半有序 | 核心題 2（33）、核心題 3（153）、81、154、162、1095 |
| 答案空間：最小化可行值 | 「最小的速度／容量／最大值」 | 貪婪檢查 + 單調性；下界取必要條件、上界取必然可行 | 核心題 4（875）、核心題 5（1011）、難題 2（410）、1482、2064 |
| 答案空間：最大化可行值 | 「最大的最小值」「最多能…」 | `last_true` 或取反後的 `first_true` | 1231 Divide Chocolate、1552 Magnetic Force、2226 |
| 計數求第 k 小 | 候選數 m·n 或 n²，問第 k 小 | 「第一個讓 count(≤ x) ≥ k 的 x」，計數用公式、two pointers 或 bisect | 難題 3（668）、難題 4（719）、難題 5（2040）、378、373 |
| 切點二分 | 兩個排序陣列的中位數／第 k 小 | 在較短陣列上二分切點，交叉條件單調 | 難題 1（4） |
| 浮點二分 | 答案是實數，要求某個精度 | 固定迭代次數，`lo = mid`／`hi = mid` | 774 Minimize Max Distance to Gas Station、644 |
| 未知長度 | 只能用 `get(i)` 存取、不知道 n | exponential search 先找上界，再二分 | 702 Search in a Sorted Array of Unknown Size |
| 二分作為零件 | 主演算法中需要在排序結構上查詢 | 維護排序陣列，用 bisect 找位置 | 300 LIS（第 21 章核心題 3）、981（第 27 章核心題 3）、1235（第 21 章難題 4） |

**下限與上限**。最簡單的形式是「排序陣列 + 標準模板」，例如 704 或 35，考的只是迴圈寫對；進一步是核心題 1 的邊界版本，考的是理解 F/T 序列而不是「找到 target」。中間層是答案空間二分（875、1011），難點轉移到兩件事：看出單調性、寫對檢查函式與上下界。上限的題目難在三個地方，常常同時出現：第一，**pred 不是現成的**，必須先做一個結構觀察才能定義，例如 153 的「≤ nums[-1]」、4 的切點交叉條件；第二，**檢查函式本身是另一個 pattern**，例如 410 的貪婪需要交換論證、719 的計數需要 two pointers、2040 的計數需要處理正負號與取整方向；第三，**要證明答案真的存在**，例如計數二分中「第一個 True 一定是實際的候選值」。

**與其他 pattern 的關係**。binary search 與 two pointers（第 5 章）常是同一題的兩種解法：167 Two Sum II 可以對每個元素 bisect（O(n log n)），也可以相向 two pointers（O(n)），通常後者更好；反過來，719 的計數用 two pointers 取代 bisect 才更快。和 sliding window（第 6 章）的關係類似：209 Minimum Size Subarray Sum 可以用 prefix sum 加 bisect 做到 O(n log n)，但 sliding window 是 O(n)。答案空間二分常和貪婪（第 20 章）綁在一起，因為檢查函式幾乎總是一個貪婪；當檢查需要 BFS 或 Union-Find 時，就變成第 18 章核心題 3（1631）或第 17 章難題 2（778）的「二分答案 + 圖搜尋」解法。第 k 小問題也可以用 heap（第 14 章）：k 小時用 heap 的 k-way merge，k 大或候選數巨大時用計數二分，分界取決於限制。

**容易混淆之處**。第一，「最小化最大值」不一定都能二分：只有當可行性對答案單調時才行，若成本函式在延伸時可能下降（例如平均值），或輸入有負數讓貪婪失效，就要改用 DP（第 21–23 章）。第二，「排序陣列」不一定要用二分：如果需要掃過所有元素（例如 977 Squares of a Sorted Array，第 5 章核心題 5），O(n) 的 two pointers 才是重點。第三，旋轉陣列有重複值時，最差複雜度是 O(n)，這是資訊下限，不要宣稱能做到 O(log n)。

## 本章重點整理

- Binary search 的本質是在單調的 F/T 序列中找分界點；任何題目先問「我的 F/T 序列是什麼、第一個 True 代表什麼」。
- 只記一個模板：`while lo < hi`、`mid = (lo + hi) // 2`、True 則 `hi = mid`、False 則 `lo = mid + 1`，結束時 `lo` 就是第一個 True；全為 False 時回傳 `hi`。
- Invariant 是「lo 左邊全 False、hi 及右邊全 True」；用它就能解釋每一行為什麼這樣寫，也能在面試時證明正確性。
- 需要最後一個 True 時，把 pred 取反用同一個模板再減一，或用向上取整的 mid 配 `lo = mid`；混用取整方向是無窮迴圈的主要來源。
- `lo <= hi` 的閉區間寫法適合「找到就回傳」的精確查找；找邊界、最小可行值、第 k 小一律用 `lo < hi`。
- 兩種思維：在索引上找邊界（34、33、153），在答案空間上搜尋（875、1011、410、668、719、2040）；後者先確認單調性、上下界與檢查成本。
- 答案空間的上界要選「一定可行」的值，直接當半開區間的 `hi`，就不必特判全部不可行的情況；下界要避免讓檢查函式出錯（除以零、包裹裝不下）。
- 第 k 小 = 第一個讓 count(≤ x) ≥ k 的 x；計數用公式（668）、two pointers（719）或分正負號的 bisect（2040），答案必定是實際的候選值。
- 旋轉陣列的關鍵是「`nums[i] <= nums[-1]` 代表在右段」；有重複值時最差 O(n)。
- 兩個排序陣列的中位數是在較短陣列上二分切點，第一個讓 `A[i] >= B[j−1]` 的 i 同時滿足兩個交叉條件，複雜度 O(log min(m, n))。
- 浮點二分用固定迭代次數，不要用 `while hi - lo > eps`；範圍要包住答案（0.001 的立方根比 0.001 大）。
- 負數與取整：Python 的 `//` 向下取整，向上取整寫 `-((-x) // a)`；在 Java／C++ 中還要注意溢位和向零取整。
