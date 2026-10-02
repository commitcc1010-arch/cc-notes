---
chapter: 5
title: Two Pointers
part: 1
---

# 第 5 章　Two Pointers

> [!abstract] 本章地圖
> **一句話**：用兩個只往單一方向移動的索引掃過資料，每一步都用一個「被丟掉的候選不可能更好」的論證排除一整批答案，把 O(n²) 的配對枚舉壓成 O(n)。
>
> **辨識訊號**：
> - 輸入已排序（或可以先排序），要找「一對／三個」數滿足和、差、乘積的條件
> - 要求 O(1) 額外空間的原地處理：去重、移除、分區、把某類元素搬到一邊
> - 答案由「左端」與「右端」兩個位置決定，而且其中一端的移動方向可以被證明
> - 陣列可以看成函數 i → nums[i]，問「重複」或「環」，又不能修改輸入、不能用額外空間
> - 「從某個位置往兩側擴張」或「兩端往中間收縮」的最佳化
>
> **核心題**：167、15、11、75、977
>
> **難題**：42、287、923、1793、2009

## 5.1 這個 Pattern 解決什麼問題

先看一個最小的例子：一個由小到大排好的陣列 `[1, 3, 4, 6, 8]`，問有沒有兩個數加起來是 10。暴力解是枚舉所有 i < j 的數對，共 n(n − 1)/2 組，O(n²)。用 hash set 可以做到 O(n) 時間，但需要 O(n) 額外空間，而且完全沒有用到「已排序」這個條件。排序其實提供了非常強的資訊：只要知道某個數對的和太小，就能一次推論出很多其他數對也太小。

把所有數對的和排成一張表，第 i 列第 j 行是 `nums[i] + nums[j]`。因為陣列遞增，每一列從左到右遞增，每一行從上到下也遞增。從右上角（最小的數配最大的數）開始看：如果和太小，這一列其他位置都在它左邊，只會更小，所以**整列都可以丟掉**；如果和太大，這一行其他位置都在它下方，只會更大，所以**整行都可以丟掉**。每比較一次就消掉一列或一行，表的範圍每次縮小一格，最多 n − 1 次就走完整張表。這兩個「列」與「行」的索引，就是 two pointers（雙指標）。

這個例子說明了 two pointers 真正在做的事：它不是「用兩個變數掃陣列」這種寫法上的技巧，而是一種**排除論證**。每移動一次指標，都必須能說出「被跳過的那些候選為什麼不可能是答案」。說得出來，複雜度就是兩個指標的總移動距離 O(n)；說不出來，就算程式看起來對，也可能在某個輸入上漏掉答案。

本章的題目可以分成三個家族。**相向指標**從兩端往中間收縮，靠排序或某種單調性排除候選（167、15、11、977、42、923）；**同向指標**兩個指標都往右走，一個負責讀、一個負責寫，或一快一慢追出環（75 的分區、287 的 Floyd 判環、2009 的窗口）；**中心擴張**則從一個固定點往兩側長，每一步選比較有利的一側（1793）。三者共同的骨架是：指標只往一個方向動，總移動次數有上限，每一步都有排除理由。

## 5.2 辨識訊號

| 題目特徵 | 為什麼是 two pointers | 本章哪一題 |
|---|---|---|
| 排序陣列中找兩數和等於、小於或最接近 target | 和對兩個指標分別單調，每次比較能丟掉一整列或一整行 | 核心題 1（167） |
| 找三個（或 k 個）數的組合，且要去除重複 | 排序後固定一個數，剩下的是兩數和；排序也讓重複值相鄰，容易跳過 | 核心題 2（15）、難題 3（923） |
| 「兩端的位置」決定答案，例如寬度乘以較短邊 | 移動較長的一端只會更差，所以較短的一端可以安全丟掉 | 核心題 3（11）、難題 1（42） |
| 原地把元素分成兩類或三類、O(1) 空間 | 讀寫指標或三個邊界指標維護「已分好的區域」 | 核心題 4（75） |
| 排序陣列經過一個「先降後升」的轉換（平方、絕對值、二次函數） | 最大值一定在兩端，從兩端往中間取就是逆序 | 核心題 5（977） |
| 值落在 [1, n]、不能修改、O(1) 空間找重複 | 把 i → nums[i] 看成鏈結，重複值就是環的入口，用快慢指標 | 難題 2（287） |
| 子陣列必須包含某個固定位置 k，最佳化「最小值 × 長度」 | 從 k 往外擴張，每次往較大的一側長 | 難題 4（1793） |
| 排序後找「值域長度固定的窗口」最多包含幾個元素 | 左端右移時右端只會右移，兩個指標各走 n 步 | 難題 5（2009） |

一個實用的反向檢查：如果你說不出「為什麼這一步可以移動這個指標而不會漏掉答案」，就先別寫 two pointers。很多題目（例如未排序陣列的 Two Sum，第 4 章核心題 1）用 hash 更直接；排序本身要 O(n log n)，若題目要回傳原始索引，排序還會打亂索引，需要額外處理。

## 5.3 模板與原理：相向、同向、分區

Two pointers 沒有像 binary search 那樣「一份程式套全部」的模板，但有三個骨架，本章每一題都是其中之一加上題目特有的排除規則。

```python
import random


def pair_with_sum(nums: list[int], target: int) -> tuple[int, int] | None:
    """相向：在排序陣列中找和為 target 的一對索引，找不到回傳 None。"""
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        s = nums[lo] + nums[hi]
        if s == target:
            return lo, hi
        if s < target:
            lo += 1          # nums[lo] 配剩下最大的數都不夠，配誰都不夠
        else:
            hi -= 1          # nums[hi] 配剩下最小的數都太大，配誰都太大
    return None


def compact(nums: list[int], keep) -> int:
    """同向讀寫：把 keep(x) 為 True 的元素依原順序搬到前面，回傳保留的個數。"""
    write = 0
    for read in range(len(nums)):
        if keep(nums[read]):
            nums[write] = nums[read]
            write += 1
    return write


def partition3(nums: list[int], pivot: int) -> tuple[int, int]:
    """分區：原地重排成 < pivot | == pivot | > pivot，回傳中段的 [lt, gt)。"""
    lt, i, gt = 0, 0, len(nums) - 1
    while i <= gt:
        if nums[i] < pivot:
            nums[lt], nums[i] = nums[i], nums[lt]
            lt += 1
            i += 1
        elif nums[i] > pivot:
            nums[i], nums[gt] = nums[gt], nums[i]
            gt -= 1              # 換過來的元素還沒看過，i 不動
        else:
            i += 1
    return lt, gt + 1


assert pair_with_sum([1, 3, 4, 6, 8], 10) == (2, 3)
assert pair_with_sum([1, 3, 4, 6, 8], 2) is None
assert pair_with_sum([], 0) is None
assert pair_with_sum([5, 5], 10) == (0, 1)
a = [0, 1, 0, 3, 12]
k = compact(a, lambda x: x != 0)
assert a[:k] == [1, 3, 12]
b = [7, 7]
assert compact(b, lambda x: x > 7) == 0
for _ in range(500):
    arr = [random.randint(0, 6) for _ in range(random.randint(0, 12))]
    p = random.randint(0, 6)
    orig = sorted(arr)
    lt, gt = partition3(arr, p)
    assert sorted(arr) == orig
    assert all(x < p for x in arr[:lt])
    assert all(x == p for x in arr[lt:gt])
    assert all(x > p for x in arr[gt:])
print("all tests passed")
```

**相向指標的 invariant**：「如果答案存在，它一定在 `[lo, hi]` 之內」。一開始範圍是整個陣列，自然成立。`s < target` 時，`nums[lo]` 和範圍內任何數相加都 ≤ `nums[lo] + nums[hi] < target`，所以 lo 不可能是答案的一部分，`lo += 1` 不會破壞 invariant；`s > target` 對稱。迴圈條件是 `lo < hi`，因為同一個元素不能用兩次；每一步範圍縮小 1，最多 n − 1 步。

**同向讀寫的 invariant**：「`nums[:write]` 恰好是 `nums[:read]` 中該保留的元素，依原順序排列」。因為 `write <= read` 永遠成立，寫入只會覆蓋已經讀過的位置，不會破壞還沒讀的資料，所以不需要額外陣列。這個骨架是穩定的（保留元素的相對順序不變），適用於 26、27、80、283 這類「原地移除或去重」的題目。

**分區的 invariant**：把陣列看成四段，`[0, lt)` 全部 < pivot、`[lt, i)` 全部 == pivot、`[i, gt]` 還沒看過、`(gt, n)` 全部 > pivot。每一步看 `nums[i]`：比 pivot 小就和 `nums[lt]` 交換，換過來的一定是 == pivot 的元素（或 `lt == i` 時就是自己），所以 i 和 lt 都能前進；比 pivot 大就和 `nums[gt]` 交換，但換過來的元素還沒看過，**i 不能前進**；等於就直接前進。每一步讓未知區縮小 1，所以一共 n 步。這就是核心題 4 的 Dutch national flag（荷蘭國旗）演算法，也是 quicksort 三路分區的核心。

**選哪一個骨架**。看題目要的是什麼：要「一對」滿足條件的元素，而且有單調性可以排除，用相向；要原地保留或移除元素、維持順序，用同向讀寫；要把元素按類別放到不同區域、不在乎同類內的順序，用分區。三者的時間都是 O(n)、空間 O(1)，差別只在 invariant。

## 5.4 相向指標為什麼不會漏解：消去整列與整行

相向指標最常被面試官追問的是正確性：「你怎麼確定跳過的數對裡沒有答案？」最清楚的回答是把 5.1 節的和表畫出來，說明每一步消掉了哪一列或哪一行。

```text
nums = [1, 3, 4, 6, 8]，target = 10；表格是 nums[i] + nums[j]（只看 i < j）

            j=1  j=2  j=3  j=4
             3    4    6    8
i=0   1      4    5    7   [9]   ← 步驟1：(0,4)=9 < 10，整列 i=0 都 ≤ 9，刪掉
i=1   3           7    9  [11]   ← 步驟2：(1,4)=11 > 10，整行 j=4 都 ≥ 11，刪掉
                                 ← 步驟3：(1,3)=9 < 10，整列 i=1 都 ≤ 9，刪掉
i=2   4               [10]  12   ← 步驟4：(2,3)=10，找到
i=3   6                     14

步驟  lo  hi  nums[lo]+nums[hi]  動作
 1     0   4        9           lo = 1   （1 配最大的 8 都不夠）
 2     1   4       11           hi = 3   （8 配最小的剩餘 3 都太大）
 3     1   3        9           lo = 2
 4     2   3       10           回傳 (2, 3)
```

第 1 步，`(0, 4)` 是第 0 列最右邊、也就是最大的一格，它都只有 9，整列就不可能有 10；第 2 步，`(1, 4)` 是第 4 行最上面、也就是剩下範圍內最小的一格，它已經是 11，整行都太大。每一步刪掉的都是「目前剩下範圍的一整列或一整行」，所以剩下的範圍永遠是一個子矩形 `[lo, hi]`，答案若存在必在其中。

這個論證可以推廣成一句話：**相向指標要成立，必須存在一個「指標所在的那一端已經被完整評估」的理由**。在 167 中，理由是和的單調性；在核心題 3（11）中，理由是「較短的那條線，配任何更近的線，水量都不會超過目前這組」；在難題 1（42）中，理由是「較低那一側的最大值，已經決定了這一格的水位」。同一個骨架，排除理由各不相同，這正是面試時要說清楚的部分。

反過來，如果排除理由不成立，相向指標就會出錯。例如在**未排序**的陣列上找兩數和，`s < target` 時無法推論任何東西；在 3Sum 中若沒有先排序，固定第一個數之後的兩數和也沒有單調性。寫相向指標之前，先問自己：這個問題的「和表」在哪兩個方向上單調？

## 5.5 同向指標：讀寫、快慢與窗口

同向指標的兩個指標都往右走，差別在於它們代表什麼。最常見的有三種：

1. **讀寫指標**：read 掃過每個元素，write 指向下一個要寫入的位置，用於原地過濾、去重、壓縮（26、80、283）。5.3 節的 `compact` 是標準形；去重時判斷條件看的是「已寫入的結果」而不是原陣列。
2. **快慢指標**：在鏈結串列或「函數圖」i → f(i) 上，慢的一次走一步、快的一次走兩步。若有環，兩者一定會在環上相遇；再讓一個指標回到起點，兩者同速前進，相遇點就是環的入口（Floyd 判環演算法）。第 11 章核心題 3（141／142）在鏈結串列上使用它，本章難題 2（287）把陣列當成函數圖使用它。
3. **窗口**：左右指標夾出一段連續區間，右端擴張、左端收縮，同時維護窗口內的統計量。當窗口需要計數或頻率表時，就是第 6 章的 sliding window；本章難題 5（2009）是在**排序後的值**上開窗，只需要比較兩端的值，所以仍是最單純的 two pointers。

```python
import random


def keep_at_most_k(nums: list[int], k: int) -> int:
    """80 題的推廣：排序陣列中每個值最多保留 k 個，原地處理，回傳新長度。"""
    write = 0
    for read in range(len(nums)):
        if write < k or nums[write - k] != nums[read]:   # 和「已寫入的」第 write-k 個比
            nums[write] = nums[read]
            write += 1
    return write


def cycle_entry(f, x0):
    """Floyd：從 x0 沿 f 走，回傳第一個重複出現的值（環的入口）。前提：一定有環。"""
    slow = fast = x0
    while True:
        slow = f(slow)
        fast = f(f(fast))
        if slow == fast:
            break
    slow = x0
    while slow != fast:
        slow = f(slow)
        fast = f(fast)
    return slow


a = [1, 1, 1, 2, 2, 3]
n = keep_at_most_k(a, 2)
assert a[:n] == [1, 1, 2, 2, 3]
b = [0, 0, 1, 1, 1, 1, 2, 3, 3]
n = keep_at_most_k(b, 1)
assert b[:n] == [0, 1, 2, 3]
assert keep_at_most_k([], 2) == 0
for _ in range(300):
    arr = sorted(random.randint(0, 4) for _ in range(random.randint(0, 12)))
    kk = random.randint(1, 3)
    expect = [x for i, x in enumerate(arr) if arr[:i].count(x) < kk]
    m = keep_at_most_k(arr, kk)
    assert arr[:m] == expect
for mod in (7, 31, 1009):
    for x0 in range(5):
        f = lambda x, mod=mod: (x * x + 1) % mod
        seen, x = set(), x0
        while x not in seen:
            seen.add(x)
            x = f(x)
        assert cycle_entry(f, x0) == x
print("all tests passed")
```

`keep_at_most_k` 的判斷值得多看一眼：要決定 `nums[read]` 能不能保留，要比較的是**已寫入結果**中的 `nums[write - k]`，而不是原陣列的 `nums[read - k]`。因為結果是排序的，若 `nums[write - k]` 等於目前的值，代表結果裡最後 k 個都是這個值，已經滿了。如果誤用 `nums[read - k]`，那個位置可能已經被覆寫，答案就會錯。

Floyd 演算法的正確性在難題 2 會完整證明。這裡先記住它的兩個前提：從起點出發一定會進入環（在有限的定義域上，函數反覆作用必然重複），以及我們要的答案剛好是「環的入口」。快慢指標只用 O(1) 空間，代價是需要兩個階段，總步數 O(尾巴長度 + 環長度)。

## 5.6 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 在未排序的陣列上直接用相向指標 | 某些輸入找不到答案，或回傳錯的數對 | 先確認單調性：排序，或說明「移動哪一端不會漏解」 |
| 迴圈條件寫成 `lo <= hi` | 同一個元素被用了兩次，例如 target = 2 × nums[i] 時誤報 | 數對問題用 `lo < hi`；只有「每個位置都要處理」的題目（977、42）才用 `<=` |
| 3Sum 去重只跳過第一個數 | 輸出中出現重複的三元組 | 固定的數與找到答案後的 lo 都要跳過重複值；或在找到答案後一併移動兩端 |
| 分區時和右端交換後仍然 `i += 1` | 換過來的 0 或 2 沒被處理，結果沒排好 | 換過來的元素還沒看過，i 必須留在原地 |
| 讀寫指標比較原陣列而不是已寫入的結果 | 去重或「最多保留 k 個」時結果錯誤 | 判斷條件看 `nums[write - k]`，它是結果的一部分 |
| 計數題用「找到就兩端各移一步」 | 有重複值時漏算，例如 `[2, 2, 2]` 中和為 4 的數對有 3 對 | 遇到相等時要整段計算重複值的組合數（923） |
| 快慢指標從錯誤的起點出發 | 287 題回傳一個不是重複值的數 | 起點必須是「不在環上」的節點；287 用索引 0，因為沒有任何值會指向 0 |
| 窗口大小用了去重後的長度 | 2009 題答案偏小或偏大 | 窗口的值域長度由原始 n 決定，去重只影響「窗口裡有幾個可保留的數」 |
| 排序後回傳索引 | 回傳的是排序後的位置，不是原始位置 | 需要原始索引時排序 `(value, index)` 的配對，或改用 hash |

## 核心題 1｜167. Two Sum II - Input Array Is Sorted｜Medium

### 題目

給一個以非遞減順序排好的整數陣列 `numbers`（索引從 **1** 開始），以及整數 `target`。請找出兩個不同的位置 `index1 < index2`，使 `numbers[index1] + numbers[index2] == target`，回傳 `[index1, index2]`。題目保證恰好有一組解，同一個元素不能用兩次，而且只能使用 O(1) 的額外空間。限制：`2 <= len(numbers) <= 3 × 10⁴`，元素與 `target` 都在 `-1000` 到 `1000` 之間。

- 範例 1：`numbers = [2, 7, 11, 15]`、`target = 9`，回傳 `[1, 2]`（2 + 7 = 9）。
- 範例 2：`numbers = [2, 3, 4]`、`target = 6`，回傳 `[1, 3]`（2 + 4 = 6，不能用 3 + 3）。
- 範例 3（邊界）：`numbers = [-1, 0]`、`target = -1`，回傳 `[1, 2]`，只有兩個元素而且含負數。
- 範例 4（邊界）：`numbers = [3, 3]`、`target = 6`，回傳 `[1, 2]`，兩個相同的值在不同位置是允許的。

### 思路

暴力解枚舉所有 i < j，O(n²)，n = 3 × 10⁴ 時約 4.5 × 10⁸ 組，太慢。第 4 章核心題 1 的 hash 做法是 O(n) 時間，但要 O(n) 空間，違反題目限制。利用排序的第一個想法是：對每個 i，在它右邊 binary search `target - numbers[i]`，時間 O(n log n)、空間 O(1)，已經符合限制，但還沒有把排序的資訊用到極致。

瓶頸在於每個 i 的搜尋彼此獨立，沒有互相利用。關鍵觀察來自 5.4 節的和表：讓 lo 從最左、hi 從最右出發，比較 `numbers[lo] + numbers[hi]` 與 target。和太小時，lo 配上範圍內最大的數都不夠，lo 不可能是答案，右移；和太大時，hi 配上範圍內最小的數都太大，hi 不可能是答案，左移。invariant 是「答案的兩個位置都在 `[lo, hi]` 之內」，每一步縮小範圍 1，所以最多 n − 1 步。

有重複值時這個論證完全不受影響，因為它只用到「非遞減」：`numbers[lo] + numbers[j] <= numbers[lo] + numbers[hi]` 對所有 j ≤ hi 都成立。回傳時記得加 1 轉成題目的 1-indexed。

```text
numbers = [2, 7, 11, 15]，target = 18
index:     0  1   2   3

步驟  lo  hi  numbers[lo] + numbers[hi]   比較     動作
 1     0   3      2 + 15 = 17            < 18    lo = 1   （2 配最大的 15 都不夠）
 2     1   3      7 + 15 = 22            > 18    hi = 2   （15 配剩下最小的 7 都太大）
 3     1   2      7 + 11 = 18            = 18    回傳 [2, 3]

範圍變化：[2 7 11 15] → 2 [7 11 15] → 2 [7 11] 15
```

第 1 步排除的是「2 和任何數的配對」，因為 2 + 15 已經是 2 能達到的最大和；第 2 步排除的是「15 和剩下任何數的配對」，因為 7 是剩下範圍內最小的數。兩步之後範圍只剩 `[7, 11]`，剛好就是答案。

### 解法

```python
import random
from bisect import bisect_left


def two_sum_sorted(numbers: list[int], target: int) -> list[int]:
    lo, hi = 0, len(numbers) - 1
    while lo < hi:
        s = numbers[lo] + numbers[hi]
        if s == target:
            return [lo + 1, hi + 1]          # 題目要 1-indexed
        if s < target:
            lo += 1
        else:
            hi -= 1
    return [-1, -1]                          # 題目保證有解；保留給 follow-up 用


def two_sum_bisect(numbers: list[int], target: int) -> list[int]:
    """O(n log n) 對照：對每個 i 在右側二分搜尋補數。"""
    for i, x in enumerate(numbers):
        j = bisect_left(numbers, target - x, i + 1)
        if j < len(numbers) and numbers[j] == target - x:
            return [i + 1, j + 1]
    return [-1, -1]


assert two_sum_sorted([2, 7, 11, 15], 9) == [1, 2]
assert two_sum_sorted([2, 3, 4], 6) == [1, 3]
assert two_sum_sorted([-1, 0], -1) == [1, 2]
assert two_sum_sorted([3, 3], 6) == [1, 2]
assert two_sum_sorted([2, 7, 11, 15], 18) == [2, 3]
assert two_sum_sorted([1, 2], 5) == [-1, -1]
for _ in range(500):
    arr = sorted(random.randint(-10, 10) for _ in range(random.randint(2, 10)))
    t = random.randint(-20, 20)
    pairs = [(i, j) for i in range(len(arr)) for j in range(i + 1, len(arr)) if arr[i] + arr[j] == t]
    got = two_sum_sorted(arr, t)
    if pairs:
        i, j = got[0] - 1, got[1] - 1
        assert i < j and arr[i] + arr[j] == t
        b = two_sum_bisect(arr, t)
        assert arr[b[0] - 1] + arr[b[1] - 1] == t
    else:
        assert got == [-1, -1] == two_sum_bisect(arr, t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每一步 lo 加一或 hi 減一，兩者相遇前最多 n − 1 步。空間 O(1)，只用兩個索引。bisect 版本是 O(n log n)、O(1) 空間，可以當作面試中的中間步驟。邊界情況：n = 2 時只比較一次；重複值（`[3, 3]`）不影響，因為 `lo < hi` 保證兩個位置不同；`lo <= hi` 是錯的寫法，在 `[1, 3]`、target = 6 這類情況，lo 與 hi 最後會停在同一個 3 上，回傳 `[2, 2]`，把同一個元素用了兩次；負數不影響單調性；值的範圍很小，Python 不必擔心溢位，但在 Java／C++ 中若值可達 2³¹，`numbers[lo] + numbers[hi]` 要用 64 位元或改寫成 `numbers[lo] < target - numbers[hi]`。

### Follow-up

> [!question]- F1. 如果不保證唯一解，要回傳所有「值不重複」的數對呢？
> 找到 `s == target` 時記錄 `(numbers[lo], numbers[hi])`，然後把 lo 往右跳過所有等於 `numbers[lo]` 的元素、hi 往左跳過所有等於 `numbers[hi]` 的元素，再繼續。跳過重複值不會漏解，因為同一個值的其他位置只會產生相同的數對。時間仍是 O(n)。這個去重動作正是核心題 2（3Sum）內層迴圈的寫法，面試官常用這個 follow-up 銜接到 3Sum。

> [!question]- F2. 如果要數「和小於 target」的數對 (i, j) 有幾組呢？
> 相向指標仍然適用，但要改成計數：`numbers[lo] + numbers[hi] < target` 時，lo 配上 `lo + 1 … hi` 的每一個都小於 target（因為 hi 已經是最大的），一次加上 `hi - lo` 組，然後 `lo += 1`；否則 `hi -= 1`。時間 O(n)。和落在區間 `[L, U]` 的數對數量就是 count(< U + 1) − count(< L)，這是 2563 題 Count the Number of Fair Pairs 的解法；套在 3Sum 上就是 259 題 3Sum Smaller。

> [!question]- F3. 如果找不到剛好等於 target 的數對，要回傳和最接近 target 的那一對呢？
> 用同樣的移動規則，額外記錄目前 `|s - target|` 最小的數對。正確性來自同一個排除論證：`s < target` 時，lo 和範圍內其他數的和都 ≤ s，離 target 只會更遠或一樣，所以丟掉 lo 不會錯過更接近的數對；`s > target` 對稱。O(n) 時間、O(1) 空間。套在 3Sum 上就是 16 題 3Sum Closest。

> [!question]- F4. 如果資料存在一棵 BST 裡，而不是排序陣列呢（653. Two Sum IV）？
> BST 的中序走訪就是排序序列，所以用兩個迭代器模擬相向指標：一個用 stack 做正向中序（由小到大），一個做反向中序（由大到小），每次依和的大小推進其中一個，兩者的值相遇時停止。每個節點最多被推入、彈出一次，時間 O(n)，空間 O(h)，h 是樹高。比起先中序走訪存成陣列（O(n) 空間），這個做法在樹很平衡時只需要 O(log n) 空間。

> [!question]- F5. 如果陣列沒有排序，但仍然要求 O(1) 額外空間呢？
> 可以先原地排序（例如 heapsort，O(1) 空間）再用相向指標，總時間 O(n log n)。但若題目要求回傳原始索引，原地排序會遺失索引，必須排序 `(值, 原索引)` 的配對，這又需要 O(n) 空間；此時 O(n) 時間、O(n) 空間的 hash 做法（第 4 章核心題 1）通常是更好的取捨。面試時要說清楚三者的時間與空間：hash O(n)／O(n)、排序加指標 O(n log n)／O(1) 或 O(n)、暴力 O(n²)／O(1)。

## 核心題 2｜15. 3Sum｜Medium

### 題目

給一個整數陣列 `nums`，找出所有和為 0 的三元組 `[nums[i], nums[j], nums[k]]`，其中 i、j、k 是三個互不相同的位置。輸出中不能有重複的三元組（以值的多重集合判斷，`[-1, 0, 1]` 和 `[0, -1, 1]` 算同一組），三元組與輸出的順序不限。限制：`3 <= len(nums) <= 3000`，元素在 `-10⁵` 到 `10⁵` 之間。

- 範例 1：`nums = [-1, 0, 1, 2, -1, -4]`，回傳 `[[-1, -1, 2], [-1, 0, 1]]`。兩個 -1 在不同位置，所以 `[-1, -1, 2]` 合法；`[-1, 0, 1]` 可以用任一個 -1 組成，但只輸出一次。
- 範例 2：`nums = [0, 1, 1]`，回傳 `[]`。
- 範例 3（邊界）：`nums = [0, 0, 0]`，回傳 `[[0, 0, 0]]`；`nums = [0, 0, 0, 0]` 也只回傳 `[[0, 0, 0]]`。
- 範例 4（邊界）：`nums = [-2, -2, 1, 1, 1, 3]`，回傳 `[[-2, 1, 1]]`，重複值很多但答案只有一組。

### 思路

暴力解枚舉所有三元組 O(n³)，再用 set 去重；n = 3000 時約 4.5 × 10⁹ 組，不可行。降一維的標準想法是：固定第一個數 `nums[i]`，問題變成「在其他元素中找兩數和為 `-nums[i]`」。若用 hash set 做內層，總時間 O(n²)，但去重很麻煩，因為同一組值可能從不同的 i、不同的順序產生多次。

關鍵是**先排序**。排序帶來兩個好處：第一，固定 i 之後，在 `nums[i+1:]` 上找兩數和就是核心題 1，可以用相向指標 O(n) 完成，總共 O(n²)；第二，相同的值會相鄰，去重只需要「跳過和前一個相同的值」。我們規定每個三元組都以排序後的形式 `a <= b <= c` 產生，a 來自位置 i、b 和 c 來自 i 右邊，這樣每組值只會有一種產生方式。

去重有兩個地方。外層：若 `nums[i] == nums[i - 1]`，以這個值當 a 的所有三元組在上一輪都找過了（上一輪的右側範圍還多包含了現在這個位置），直接跳過。內層：找到一組之後，lo 要跳過所有和 `nums[lo]` 相同的值，否則下一步會再找到同一組 `(a, b, c)`；hi 不必另外跳，因為 lo 換成更大的 b 之後，和會變大，hi 自然會往左移過舊的 c。另外，`nums[i] > 0` 時三個數都是正的，不可能和為 0，可以提早結束。

```text
排序後 nums = [-4, -1, -1, 0, 1, 2]
index:          0   1   2  3  4  5

i=0 (a=-4)，找 b + c = 4，範圍 [1, 5]
  lo=1 hi=5  -1 + 2 = 1  < 4   lo=2
  lo=2 hi=5  -1 + 2 = 1  < 4   lo=3
  lo=3 hi=5   0 + 2 = 2  < 4   lo=4
  lo=4 hi=5   1 + 2 = 3  < 4   lo=5，lo == hi 結束（沒有解）

i=1 (a=-1)，找 b + c = 1，範圍 [2, 5]
  lo=2 hi=5  -1 + 2 = 1  = 1   記錄 [-1, -1, 2]；lo 跳過重複到 3，hi=4
  lo=3 hi=4   0 + 1 = 1  = 1   記錄 [-1, 0, 1]；lo=4，hi=3 結束

i=2 (a=-1)  nums[2] == nums[1]，跳過（以 -1 開頭的組合已經找完）

i=3 (a=0)，找 b + c = 0，範圍 [4, 5]
  lo=4 hi=5   1 + 2 = 3  > 0   hi=4，結束
i=4 之後右側不足兩個元素，結束
```

i = 2 被跳過是去重的關鍵：如果不跳，它會在範圍 `[3, 5]` 中再找到 `[-1, 0, 1]`。注意 i = 1 時，b 可以取到位置 2 的另一個 -1，所以 `[-1, -1, 2]` 不會因為外層去重而被漏掉；外層只跳過「當 a 的值重複」，不限制 b 和 a 相同。

### 解法

```python
import random
from itertools import combinations


def three_sum(nums: list[int]) -> list[list[int]]:
    nums = sorted(nums)
    n = len(nums)
    res = []
    for i in range(n - 2):
        if nums[i] > 0:                          # 最小的數已經是正的，之後不可能和為 0
            break
        if i > 0 and nums[i] == nums[i - 1]:     # 這個 a 已經處理過
            continue
        lo, hi = i + 1, n - 1
        while lo < hi:
            s = nums[i] + nums[lo] + nums[hi]
            if s < 0:
                lo += 1
            elif s > 0:
                hi -= 1
            else:
                res.append([nums[i], nums[lo], nums[hi]])
                lo += 1
                hi -= 1
                while lo < hi and nums[lo] == nums[lo - 1]:   # 跳過重複的 b
                    lo += 1
    return res


def brute(nums):
    return sorted({tuple(sorted(t)) for t in combinations(nums, 3) if sum(t) == 0})


def canon(res):
    return sorted(tuple(t) for t in res)


assert canon(three_sum([-1, 0, 1, 2, -1, -4])) == [(-1, -1, 2), (-1, 0, 1)]
assert three_sum([0, 1, 1]) == []
assert three_sum([0, 0, 0]) == [[0, 0, 0]]
assert three_sum([0, 0, 0, 0]) == [[0, 0, 0]]
assert three_sum([-2, -2, 1, 1, 1, 3]) == [[-2, 1, 1]]
assert canon(three_sum([-4, -2, -2, -2, 0, 1, 2, 2, 2, 3, 3, 4, 4, 6, 6])) == brute(
    [-4, -2, -2, -2, 0, 1, 2, 2, 2, 3, 3, 4, 4, 6, 6])
for _ in range(500):
    arr = [random.randint(-5, 5) for _ in range(random.randint(3, 10))]
    res = three_sum(arr)
    assert len(res) == len(set(map(tuple, res)))     # 沒有重複
    assert canon(res) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n²)：排序 O(n log n)，外層 n 次、每次內層相向指標 O(n)。空間：除了輸出之外，Python 的 `sorted` 需要 O(n) 的複本；若允許修改輸入，用 `nums.sort()` 原地排序，額外空間是排序本身的 O(log n) 到 O(n)（Timsort 最差 O(n)）。邊界情況：全部是 0 時外層只處理 i = 0，內層找到一組後 lo 一路跳過所有 0；全部同號時不會有解，正數情況下第一輪就 `break`；`[0, 0, 0, 0]` 這類大量重複的輸入，去重邏輯保證只輸出一次；外層去重必須寫 `nums[i] == nums[i - 1]`（和前一個比），寫成和後一個比 `nums[i] == nums[i + 1]` 會漏掉 `[-1, -1, 2]` 這種 a 和 b 相同的組合。

### Follow-up

> [!question]- F1. 如果要找和最接近 target 的三元組和呢（16. 3Sum Closest）？
> 架構完全相同：排序、固定 i、內層相向指標，每次計算 `s = nums[i] + nums[lo] + nums[hi]`，更新 `|s - target|` 最小的 s；`s < target` 時 lo 右移、`s > target` 時 hi 左移、相等時直接回傳。正確性是核心題 1 F3 的排除論證。不需要去重（答案是一個數值），但跳過重複的 i 仍可減少工作量。時間 O(n²)、空間 O(1)。

> [!question]- F2. 如果是 4Sum（18 題），甚至 kSum 呢？
> 遞迴降維：排序後，kSum 固定第一個數再遞迴解 (k−1)Sum，直到 k = 2 時用相向指標。每層都用「和前一個相同就跳過」去重。時間 O(n^(k−1))：4Sum 是 O(n³)。可以加剪枝：若目前最小的 k 個數之和已大於 target，或最大的 k 個數之和小於 target，直接回傳。4Sum 的 target 可以是任意整數、元素可達 10⁹，四個數相加會超過 32 位元，Java／C++ 要用 long；另外 4Sum 不能用 `nums[i] > 0` 提早結束，因為 target 可能是負數。

> [!question]- F3. 如果只要數「和小於 target」的三元組有幾組呢（259. 3Sum Smaller）？
> 排序後固定 i，內層用核心題 1 F2 的計數技巧：`nums[i] + nums[lo] + nums[hi] < target` 時，lo 配上 `lo + 1 … hi` 的每個位置都符合，一次加 `hi - lo` 組，然後 `lo += 1`；否則 `hi -= 1`。因為這題問的是位置的組合數而不是不重複的值，所以**不能**去重。時間 O(n²)、空間 O(1)。

> [!question]- F4. 能不能比 O(n²) 更快？
> 一般情況下目前沒有已知明顯更快的演算法，3SUM 在複雜度理論中被當作「難以做到明顯低於平方」的代表問題（3SUM conjecture），很多幾何問題的下限都是從它歸約而來，所以面試中 O(n²) 就是最佳答案。特殊情況可以更快：若值域很小（|值| ≤ U），可以用多項式乘法（FFT）在 O(n + U log U) 內算出所有兩數和的出現次數，再對每個 c 查詢 -c，這主要用於計數版本。

> [!question]- F5. 如果不允許排序（例如要保留原始索引）呢？
> 用 hash：外層固定 i，內層掃 `j > i`，用一個 set 記錄看過的值，若 `-nums[i] - nums[j]` 在 set 中就找到一組；把三元組排序成 tuple 放進結果的 set 去重。時間仍是 O(n²)，但空間 O(n)，而且常數較大。若要回傳索引而不是值，則記錄值到索引的 dict。面試時通常先講排序版本，因為它的去重最乾淨；面試官堅持保留索引時再換成 hash，並說明空間的代價。

## 核心題 3｜11. Container With Most Water｜Medium

### 題目

給一個長度為 n 的非負整數陣列 `height`，第 i 個值代表在 x = i 處有一條高 `height[i]` 的垂直線。選兩條線 i < j，它們和 x 軸圍成一個容器，能裝的水量是 `(j - i) × min(height[i], height[j])`（容器不能傾斜，中間的其他線不影響）。回傳最大的水量。限制：`2 <= n <= 10⁵`，`0 <= height[i] <= 10⁴`。

- 範例 1：`height = [1, 8, 6, 2, 5, 4, 8, 3, 7]`，回傳 `49`。選 i = 1（高 8）與 j = 8（高 7），寬 7、高 min(8, 7) = 7。
- 範例 2：`height = [1, 1]`，回傳 `1`。
- 範例 3：`height = [4, 3, 2, 1, 4]`，回傳 `16`，最外側兩條線同高，寬 4 × 高 4。
- 範例 4（邊界）：`height = [0, 2]`，回傳 `0`，有一條線高度是 0 時裝不了水。

### 思路

暴力解枚舉所有 i < j，O(n²)，n = 10⁵ 時約 5 × 10⁹ 組，太慢。這題沒有排序，相向指標的單調性要從水量公式本身找：水量是「寬 × 較短邊」，從最寬的一組 `(0, n − 1)` 出發，往內移動一定讓寬度變小，唯一的希望是讓較短邊變高。

關鍵觀察：假設 `height[l] < height[r]`。考慮 l 和任何更近的 j（l < j < r）配對：寬度 `j - l < r - l`，高度 `min(height[l], height[j]) <= height[l]`，所以水量一定小於 `(r - l) × height[l]`，也就是目前這一組。換句話說，**較短的那條線 l，最好的搭檔就是目前的 r**，它已經被完整評估過，可以丟掉，`l += 1`。若移動較長的 r 則沒有這個保證，而且新的組合寬度變小、高度仍被 l 限制，只會更差。

invariant 是「最佳解要嘛已經被記錄在 best 中，要嘛兩條線都在 `[l, r]` 之內」。每一步丟掉一條「所有可能的配對都不會超過已記錄值」的線，所以 invariant 維持；`l == r` 時範圍內不再有配對，best 就是答案。兩條線等高時，兩條都可以丟掉（任何一條配更近的線，高度都不超過這個共同高度、寬度更小），程式中移哪一條都正確。

```text
height = [1, 8, 6, 2, 5, 4, 8, 3, 7]
index:    0  1  2  3  4  5  6  7  8

步驟  l  r  寬  min(h[l], h[r])  水量  best  動作（移較短的一側）
 1    0  8   8   min(1, 7) = 1     8     8   h[l] < h[r]，l = 1
 2    1  8   7   min(8, 7) = 7    49    49   h[r] 較短，r = 7
 3    1  7   6   min(8, 3) = 3    18    49   r = 6
 4    1  6   5   min(8, 8) = 8    40    49   等高，移 r：r = 5
 5    1  5   4   min(8, 4) = 4    16    49   r = 4
 6    1  4   3   min(8, 5) = 5    15    49   r = 3
 7    1  3   2   min(8, 2) = 2     4    49   r = 2
 8    1  2   1   min(8, 6) = 6     6    49   r = 1，l == r 結束
```

第 1 步，高度 1 的那條線無論配誰，高度都被限制在 1，而它配 r = 8 時寬度已經最大，所以它的最佳值 8 已經記下，可以丟掉。第 2 步之後 l = 1 的高度 8 很高，於是一直移動較短的 r；第 4 步兩邊都是 8，雖然水量 40 沒有超過 49，但移哪一邊都安全。總共 8 步，正好是 n − 1。

### 解法

```python
import random


def max_area(height: list[int]) -> int:
    l, r = 0, len(height) - 1
    best = 0
    while l < r:
        h = min(height[l], height[r])
        best = max(best, (r - l) * h)
        if height[l] < height[r]:     # l 較短：它配任何更近的線都不會更好
            l += 1
        else:                         # r 較短或等高：丟掉 r
            r -= 1
    return best


def brute(height):
    n = len(height)
    return max((j - i) * min(height[i], height[j]) for i in range(n) for j in range(i + 1, n))


assert max_area([1, 8, 6, 2, 5, 4, 8, 3, 7]) == 49
assert max_area([1, 1]) == 1
assert max_area([4, 3, 2, 1, 4]) == 16
assert max_area([0, 2]) == 0
assert max_area([1, 2, 1]) == 2
assert max_area([10**4] * 10**5) == 10**4 * (10**5 - 1)
for _ in range(500):
    h = [random.randint(0, 10) for _ in range(random.randint(2, 12))]
    assert max_area(h) == brute(h)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每一步 l 或 r 移動一格，共 n − 1 步。空間 O(1)。邊界情況：n = 2 時只計算一次；有高度 0 的線時水量是 0，不影響比較；全部等高時最佳解是最外側的兩條，第一步就記錄到；嚴格遞增或遞減的陣列也只要 n − 1 步。比較時用 `<` 還是 `<=` 都正確，因為等高時兩條線都可以丟。這題常被誤解成「中間的線會擋水」，題目明確說明不會，若中間的線會形成牆，就變成難題 1（42）或第 10 章難題 1（84）的問題。

### Follow-up

> [!question]- F1. 為什麼等高時兩條線都可以丟？能不能兩邊同時移動？
> 設 `height[l] == height[r] == H`。l 配任何 j（l < j < r）的水量 ≤ (j − l) × H < (r − l) × H，r 配任何 i（l < i < r）也一樣，所以 l 和 r 的最佳配對都是彼此，已經被記錄。因此等高時可以同時 `l += 1` 與 `r -= 1`，正確性不變，只是少一步迭代；漸進複雜度仍是 O(n)。面試時能說出這一點，代表你理解排除論證，而不是背「移較短的那邊」。

> [!question]- F2. 如果線的位置不是等間距的，而是給一個遞增的座標陣列 x 呢？
> 水量變成 `(x[j] - x[i]) × min(height[i], height[j])`。排除論證只用到「往內移動寬度會變小」，而 x 遞增保證了這一點，所以同一個演算法直接成立，只要把 `r - l` 換成 `x[r] - x[l]`，時間仍是 O(n)。若座標沒有排序，先把 `(x, height)` 依 x 排序，總時間 O(n log n)。

> [!question]- F3. 能不能在移動時跳過不可能更好的線，減少計算？
> 可以。丟掉較短的 l 之後，新的 l 如果高度 ≤ 剛丟掉的那條，寬度更小、高度不會更高，水量一定不會超過剛才那組，所以可以用 `while l < r and height[l] <= h: l += 1` 一次跳過，r 那側同理。這是常數優化，最差情況（嚴格遞增）仍是 O(n)；面試時可以提一句，但不需要為了它犧牲程式的清晰度。

> [!question]- F4. 如果中間的線會擋水，要找「區間內最短線 × 區間長度」的最大值呢？
> 那就不是這題了：水量由整段區間的最小值決定，變成 84. Largest Rectangle in Histogram。相向指標在那裡不成立，因為「丟掉較短的一端」可能丟掉一個包含很高中段的區間；標準解是 monotonic stack，對每根柱子找左右第一個比它矮的位置，O(n)，見第 10 章難題 1。若再加上「區間必須包含位置 k」的限制，就是本章難題 4（1793），那時從 k 往外擴張的指標又能成立。

## 核心題 4｜75. Sort Colors｜Medium

### 題目

給一個只包含 0、1、2 的陣列 `nums`（分別代表紅、白、藍三種顏色），請**原地**重排，使相同顏色相鄰，順序為 0、1、2。不能使用函式庫的排序。進階要求：只掃一遍、O(1) 額外空間。限制：`1 <= len(nums) <= 300`。

- 範例 1：`nums = [2, 0, 2, 1, 1, 0]`，結果為 `[0, 0, 1, 1, 2, 2]`。
- 範例 2：`nums = [2, 0, 1]`，結果為 `[0, 1, 2]`。
- 範例 3（邊界）：`nums = [1]`，不變；`nums = [2, 2, 2]`，不變。
- 範例 4（邊界）：`nums = [2, 1, 0]`，完全逆序，結果 `[0, 1, 2]`。

### 思路

一般排序是 O(n log n)。因為只有三種值，counting sort（計數排序）可以兩遍完成：第一遍數出 0、1、2 各有幾個，第二遍依序寫回，O(n) 時間、O(1) 空間。這已經是漸進最佳，但需要兩遍，而且當元素不是單純的數字、而是帶有顏色欄位的物件時，「寫回」需要另外保存物件，計數法就不夠用了。

一遍完成的做法是 5.3 節的三路分區，也就是 Dijkstra 提出的 Dutch national flag 問題。用三個指標把陣列切成四區：`[0, lt)` 全是 0、`[lt, i)` 全是 1、`[i, gt]` 尚未檢查、`(gt, n)` 全是 2。每一步檢查 `nums[i]`：是 0 就和 `nums[lt]` 交換，兩個指標都前進；是 2 就和 `nums[gt]` 交換，gt 後退，**i 不動**；是 1 就 i 前進。未知區每一步縮小一格，`i > gt` 時未知區為空，排序完成。

兩個不對稱的地方是這題的重點。和 lt 交換後 i 可以前進，因為 `nums[lt]` 位於 `[lt, i)` 這個全是 1 的區域（或者 `lt == i`，換的是自己），換過來的一定是 1，已經在正確的區域；和 gt 交換後 i 不能前進，因為從 gt 換過來的元素來自未知區，可能是 0、1、2 任何一個，必須再檢查一次。迴圈條件是 `i <= gt` 而不是 `i < gt`，因為 gt 指向的位置本身也還沒檢查。

```text
nums = [2, 0, 2, 1, 1, 0]
區域：[0, lt) = 0｜[lt, i) = 1｜[i, gt] 未知｜(gt, n) = 2

步驟  lt  i  gt  nums[i]  動作                       結果
 1     0  0   5     2     與 gt 交換，gt = 4          [0 0 2 1 1 | 2]
 2     0  0   4     0     與 lt 交換（自己），lt=1 i=1 [0 | 0 2 1 1 | 2]
 3     1  1   4     0     與 lt 交換（自己），lt=2 i=2 [0 0 | 2 1 1 | 2]
 4     2  2   4     2     與 gt 交換，gt = 3          [0 0 | 1 1 | 2 2]
 5     2  2   3     1     i = 3                      [0 0 | 1 | 1 | 2 2]
 6     2  3   3     1     i = 4                      [0 0 | 1 1 | 2 2]
結束  i = 4 > gt = 3
```

第 1 步把最前面的 2 換到最後，換過來的是 0，此時 i 沒有前進，第 2 步才處理這個 0；第 4 步同樣換來一個 1，下一步再檢查它。如果在第 1 步之後讓 i 前進，這個 0 就會被留在 1 的區域裡，結果出錯。

### 解法

```python
import random


def sort_colors(nums: list[int]) -> None:
    lt, i, gt = 0, 0, len(nums) - 1
    while i <= gt:
        if nums[i] == 0:
            nums[lt], nums[i] = nums[i], nums[lt]
            lt += 1
            i += 1                    # 換過來的是 1（或自己），已經就位
        elif nums[i] == 2:
            nums[i], nums[gt] = nums[gt], nums[i]
            gt -= 1                   # 換過來的還沒檢查，i 不動
        else:
            i += 1


def sort_colors_counting(nums: list[int]) -> None:
    """兩遍的 counting sort 對照。"""
    c = [0, 0, 0]
    for x in nums:
        c[x] += 1
    nums[:] = [0] * c[0] + [1] * c[1] + [2] * c[2]


for case, expect in [([2, 0, 2, 1, 1, 0], [0, 0, 1, 1, 2, 2]), ([2, 0, 1], [0, 1, 2]),
                     ([1], [1]), ([2, 2, 2], [2, 2, 2]), ([2, 1, 0], [0, 1, 2]), ([0], [0])]:
    a = case[:]
    sort_colors(a)
    assert a == expect
for _ in range(1000):
    arr = [random.randint(0, 2) for _ in range(random.randint(1, 15))]
    a, b = arr[:], arr[:]
    sort_colors(a)
    sort_colors_counting(b)
    assert a == b == sorted(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每一步要嘛 i 前進、要嘛 gt 後退，未知區 `[i, gt]` 每步縮小 1，共 n 步；每個元素最多被交換常數次。空間 O(1)。邊界情況：n = 1 時處理一步就結束；全是 2 時每一步都和 gt 交換（換的是自己），gt 一路降到 −1，i 保持 0，迴圈因 `i > gt` 結束；全是 0 時 lt 和 i 同步前進，每次和自己交換；`gt` 初值是 `n − 1` 而不是 n，因為它指向「最後一個未知的位置」。這個演算法不是穩定的：相同顏色的元素相對順序可能改變，對純數字沒有影響，但對物件可能有影響（見 F2）。

### Follow-up

> [!question]- F1. 如果有 k 種顏色（1 到 k）呢？
> 兩種做法。counting sort：計數後寫回，O(n + k) 時間、O(k) 空間，k 小時最好。若要求 O(1) 額外空間，用「彩虹排序」：遞迴地以顏色範圍的中點 m 做兩路分區（≤ m 放左、> m 放右），再分別處理 `[1, m]` 與 `[m + 1, k]` 兩段，遞迴深度 O(log k)，每層總共 O(n)，總時間 O(n log k)、遞迴堆疊 O(log k)。另一個做法是每次找出目前範圍的最小與最大顏色，用本題的三路分區把它們放到兩端，O(n · k / 2)，k 小時常數很好。

> [!question]- F2. 如果元素是帶顏色的物件，而且要求穩定（同色物件保持原順序）呢？
> Dutch flag 的長距離交換會打亂順序，不是穩定的。穩定的做法是 counting sort 的完整版：先計數算出每種顏色的起始位置，再掃一遍把物件放到輸出陣列的對應位置，O(n) 時間、O(n) 額外空間。若堅持原地，可以用分治的穩定分區（每層用區塊旋轉合併），O(n log n) 時間；更快的原地穩定分區雖然在理論上存在，但非常複雜，面試不會要求。面試時說清楚「穩定、原地、線性」三者在簡單方法中無法同時兼得即可。

> [!question]- F3. 這個分區在 quicksort 中有什麼用途？
> 當陣列有大量重複值時，傳統的兩路分區會讓等於 pivot 的元素全部落在同一側，遞迴退化成 O(n²)（例如全部相同的陣列）。三路分區把「等於 pivot」的元素集中在中間，之後只遞迴處理 `< pivot` 與 `> pivot` 兩段，全相同時一次分區就結束，O(n)。若只有 d 種不同的值，期望時間是 O(n log d)。Python 的 `list.sort` 是 Timsort，不受這個問題影響，但自己實作 quickselect（第 14 章核心題 1 的 215 題）時，三路分區是處理重複值的標準手法。

> [!question]- F4. 如果只有兩類，而且要保持其中一類的相對順序呢（283. Move Zeroes）？
> 用 5.3 節的同向讀寫：read 掃過陣列，遇到非 0 就寫到 write 並前進，最後把 `[write, n)` 填 0。非 0 元素的相對順序不變，因為它們是依讀取順序寫入的。O(n) 時間、O(1) 空間。也可以把「寫入」換成「交換」：`nums[write], nums[read] = nums[read], nums[write]`，這樣一遍完成、不必最後補 0，而且寫入次數等於非 0 元素的個數。這是面試官常用來確認你知道「分區」與「穩定壓縮」差別的題目。

## 核心題 5｜977. Squares of a Sorted Array｜Easy

### 題目

給一個以非遞減順序排好的整數陣列 `nums`（可以有負數），回傳每個元素平方後、同樣以非遞減順序排列的新陣列。進階要求：O(n) 時間。限制：`1 <= len(nums) <= 10⁴`，元素在 `-10⁴` 到 `10⁴` 之間。

- 範例 1：`nums = [-4, -1, 0, 3, 10]`，回傳 `[0, 1, 9, 16, 100]`。
- 範例 2：`nums = [-7, -3, 2, 3, 11]`，回傳 `[4, 9, 9, 49, 121]`，-3 和 3 的平方相同。
- 範例 3（邊界）：`nums = [-3, -2, -1]`，全為負數，回傳 `[1, 4, 9]`，順序完全反轉。
- 範例 4（邊界）：`nums = [5]`，回傳 `[25]`。

### 思路

直接的做法是全部平方再排序，O(n log n)。這沒有用到「輸入已排序」的資訊。問題在於平方會打亂順序：負數部分取平方後變成遞減，非負部分仍然遞增，所以平方後的序列是「先遞減、再遞增」的山谷形狀，最小值在 0 附近，**最大值一定在兩端之一**。

由這個觀察，可以從兩端往中間取：比較 `nums[lo]²` 和 `nums[hi]²`，較大的就是剩下元素中最大的平方，把它放在結果的最後一個空位，然後移動對應的指標。invariant 是「`res[k+1:]` 已經放好剩下範圍以外的所有平方，而且是排序的；`nums[lo..hi]` 是還沒放的元素，它們的平方都 ≤ `res[k+1]`」。每一步放一個，共 n 步。

另一種等價的做法是先用 binary search 找到第一個非負數的位置 p，讓左指標從 p − 1 往左、右指標從 p 往右，每次取較小的平方放到結果前面，就像 merge sort 的合併。兩者都是 O(n)，從外往內的版本不需要找分界點，程式較短；從內往外的版本可以在只需要「前 k 小的平方」時提早停止。

```text
nums = [-4, -1, 0, 3, 10]
平方：  16   1  0  9  100      ← 先遞減再遞增，最大值在兩端

步驟  lo  hi  nums[lo]²  nums[hi]²  放入 res[k]   res
 1     0   4     16        100      k=4: 100     [_, _, _, _, 100]
 2     0   3     16          9      k=3: 16      [_, _, _, 16, 100]
 3     1   3      1          9      k=2: 9       [_, _, 9, 16, 100]
 4     1   2      1          0      k=1: 1       [_, 1, 9, 16, 100]
 5     2   2      0          0      k=0: 0       [0, 1, 9, 16, 100]
```

每一步都從兩端拿較大的平方，並從結果的尾端往前填。第 2 步比較 16 和 9，雖然 -4 的絕對值比 3 大，但它在左邊，這正是兩端比較的意義：兩個候選分別是「最負的數」和「最正的數」，剩下的元素絕對值都不會超過它們。第 5 步 lo == hi，只剩一個元素，也要放進去，所以迴圈要跑滿 n 步（等價於 `while lo <= hi`），不能寫成 `lo < hi`。

### 解法

```python
import random
from bisect import bisect_left


def sorted_squares(nums: list[int]) -> list[int]:
    n = len(nums)
    res = [0] * n
    lo, hi = 0, n - 1
    for k in range(n - 1, -1, -1):          # 從尾端往前填最大的平方
        if abs(nums[lo]) > abs(nums[hi]):
            res[k] = nums[lo] * nums[lo]
            lo += 1
        else:
            res[k] = nums[hi] * nums[hi]
            hi -= 1
    return res


def sorted_squares_merge(nums: list[int]) -> list[int]:
    """從分界點往兩側合併的版本。"""
    p = bisect_left(nums, 0)                # 第一個非負數
    i, j, res = p - 1, p, []
    while i >= 0 or j < len(nums):
        if j == len(nums) or (i >= 0 and -nums[i] < nums[j]):
            res.append(nums[i] * nums[i])
            i -= 1
        else:
            res.append(nums[j] * nums[j])
            j += 1
    return res


assert sorted_squares([-4, -1, 0, 3, 10]) == [0, 1, 9, 16, 100]
assert sorted_squares([-7, -3, 2, 3, 11]) == [4, 9, 9, 49, 121]
assert sorted_squares([-3, -2, -1]) == [1, 4, 9]
assert sorted_squares([5]) == [25]
assert sorted_squares([0, 0]) == [0, 0]
for _ in range(500):
    arr = sorted(random.randint(-20, 20) for _ in range(random.randint(1, 12)))
    expect = sorted(x * x for x in arr)
    assert sorted_squares(arr) == expect == sorted_squares_merge(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)，每個元素恰好被放入結果一次；merge 版本多一次 O(log n) 的二分。空間：輸出 O(n)，額外 O(1)。邊界情況：全為負數時每一步都取左端，結果是原陣列反轉後平方；全為非負數時每一步都取右端；n = 1 時迴圈一次；相同絕對值（-3 與 3）時取哪一端都可以，因為平方相同；用 `for k in range(n - 1, -1, -1)` 控制步數，比 `while lo <= hi` 更不容易寫錯終止條件。值最大 10⁴，平方 10⁸，Python 沒有溢位問題，Java 的 int 也夠用，但若值可達 10⁵ 以上就要用 long。

### Follow-up

> [!question]- F1. 如果把平方換成任意二次函數 f(x) = ax² + bx + c 呢（360. Sort Transformed Array）？
> 二次函數在排序陣列上的形狀由 a 決定。a > 0 時是開口向上的拋物線，最大值在兩端，用本題的方法從尾端往前填較大的值；a < 0 時開口向下，最小值在兩端，改成從前端往後填較小的值；a = 0 時 f 是線性的，任一端都是極值，上面兩個分支都正確。時間 O(n)、空間 O(1)（不含輸出）。
> ```python
> def sort_transformed(nums, a, b, c):
>     f = lambda x: a * x * x + b * x + c
>     n, lo, hi = len(nums), 0, len(nums) - 1
>     res = [0] * n
>     if a >= 0:                                    # 最大值在兩端，從後往前填
>         for k in range(n - 1, -1, -1):
>             if f(nums[lo]) >= f(nums[hi]):
>                 res[k] = f(nums[lo]); lo += 1
>             else:
>                 res[k] = f(nums[hi]); hi -= 1
>     else:                                         # 最小值在兩端，從前往後填
>         for k in range(n):
>             if f(nums[lo]) <= f(nums[hi]):
>                 res[k] = f(nums[lo]); lo += 1
>             else:
>                 res[k] = f(nums[hi]); hi -= 1
>     return res
> ```

> [!question]- F2. 如果要統計平方後有幾個不同的值呢？
> 平方相同等價於絕對值相同，所以問題是「有幾個不同的絕對值」。用相向指標：比較 `abs(nums[lo])` 與 `abs(nums[hi])`，較大的那個算一個新值，然後把該側所有等於這個絕對值的元素都跳過；兩者相等時算一個值，兩側同時跳過。時間 O(n)、空間 O(1)，不需要 set。這個技巧和核心題 2 的去重是同一件事：在排序序列上，相同的值一定相鄰，跳過整段即可。

> [!question]- F3. 如果只需要平方後最小的 k 個呢？
> 用解法中的 merge 版本：先 binary search 找到分界點，從中間往兩側合併，取到 k 個就停止，時間 O(log n + k)。這和 658. Find K Closest Elements 是同一個結構：離某個值（這裡是 0）最近的 k 個元素，在排序陣列中一定是一段連續區間。658 也可以反過來用相向指標，從 `[0, n − 1]` 開始每次丟掉離 x 較遠的一端，直到剩 k 個，O(n − k)；或對區間的左端點做 binary search，O(log(n − k) + k)，見第 8 章。

> [!question]- F4. 能不能不配置新陣列，直接在原陣列上完成？
> 先把每個元素原地平方，陣列就變成「一段遞減接一段遞增」，問題變成原地合併兩段排序序列。原地合併在 O(1) 額外空間下沒有簡單的線性解法：用插入式合併是 O(n²)，用區塊旋轉的分治合併是 O(n log n)。所以實務上的答案是：這題的輸出本來就需要 O(n) 空間，題目也允許回傳新陣列，若真的要原地，就接受 O(n log n) 直接 `sort()`。面試官問這題通常是想看你能否指出「原地合併」才是真正的困難所在。

## 難題 1｜42. Trapping Rain Water｜Hard

### 題目

給 n 個非負整數 `height`，代表寬度皆為 1 的柱子高度，由左到右排列。下雨之後，柱子之間的凹槽會積水，請計算總共能積多少單位的水。柱子之外（最左與最右的外側）沒有牆，水會流走。限制：`1 <= n <= 2 × 10⁴`，`0 <= height[i] <= 10⁵`。

- 範例 1：`height = [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]`，回傳 `6`。
- 範例 2：`height = [4, 2, 0, 3, 2, 5]`，回傳 `9`，各位置分別積 0、2、4、1、2、0。
- 範例 3（邊界）：`height = [3]`，回傳 `0`；`height = [1, 2, 3]`，嚴格遞增，水全部從左側流走，回傳 `0`。
- 範例 4（邊界）：`height = [5, 0, 0, 5]`，回傳 `10`，中間兩格各積 5。

### 提示

> [!tip]- 提示 1
> 不要想「一個凹槽」能裝多少，改成想「每一根柱子的正上方」能積多少水。這個量由什麼決定？

> [!tip]- 提示 2
> 位置 i 上方的水位是 `min(i 左邊（含）最高的柱子, i 右邊（含）最高的柱子)`，積水量是水位減去 `height[i]`。先用兩個陣列存每個位置的左右最大值，就是 O(n) 的解。

> [!tip]- 提示 3
> 要省掉兩個陣列：讓指標從兩端往中間走，維護 `lmax`（左指標以左的最大值）與 `rmax`（右指標以右的最大值）。如果 `lmax < rmax`，左指標那一格的水位已經確定是 `lmax`，因為它右邊真正的最大值只會 ≥ `rmax`。

### 詳解

**為什麼直覺做法不夠**。很多人第一個想法是找「凹槽」：從左邊找一個高柱，往右找到下一個不低於它的柱子，中間就是一個水池。但水池的邊界可能是右邊一根比較矮的柱子（例如 `[5, 0, 3]` 中水位由 3 決定），而且水池可以巢狀（一個大池子裡有小島），用「找凹槽」的思路要處理很多情況。換成逐欄計算就簡單得多：位置 i 的水位是 `min(maxL[i], maxR[i])`，其中 `maxL[i] = max(height[0..i])`、`maxR[i] = max(height[i..n−1])`，積水量是水位減去 `height[i]`（這個值一定 ≥ 0，因為兩個最大值都包含 `height[i]` 本身）。逐欄計算的暴力解是對每個 i 向左右掃描求最大值，O(n²)。

**第一步優化：前綴最大值**。`maxL` 可以由左往右一遍算出，`maxR` 由右往左一遍算出，之後每欄 O(1)，總共 O(n) 時間、O(n) 空間。這在面試中已經是一個合格的答案，但面試官通常會追問 O(1) 空間。

**突破點：不需要知道確切的兩個最大值，只需要知道哪一個比較小**。讓 l、r 從兩端出發，`lmax = max(height[0..l])` 是 l 的「真正左最大值」，`rmax = max(height[r..n−1])` 是 r 的「真正右最大值」。關鍵在於：對 l 來說，它真正的右最大值 `maxR[l] = max(height[l..n−1])` 包含了 `height[r..n−1]`，所以 `maxR[l] >= rmax`。若 `lmax < rmax`，就有 `maxL[l] = lmax < rmax <= maxR[l]`，l 的水位一定是 `lmax`，不管 l 和 r 之間還有什麼柱子。於是 l 這一格的水量確定是 `lmax - height[l]`，可以處理完並右移。反之 `lmax >= rmax` 時，對 r 對稱地成立：`maxL[r] >= lmax >= rmax = maxR[r]`，r 的水位確定是 `rmax`。

**正確性**。每一步都確定一格的積水量，而且算出來的就是 `min(maxL, maxR) − height`，所以總和正確；每一步移動一個指標，n 步後所有格子都被處理過。這和 5.4 節的排除論證是同一個形狀：被處理掉的那一側，是「已經被完整決定」的一側。注意這裡比較的是 `lmax` 與 `rmax`，而不是 `height[l]` 與 `height[r]`；兩種寫法都正確（比較柱高的版本需要另一個論證），但比較最大值的版本最容易說清楚。

```text
height = [2, 0, 3, 1, 0, 1, 2]

高度 3  .  .  #  .  .  .  .
高度 2  #  ~  #  ~  ~  ~  #       # 是柱子，~ 是水
高度 1  #  ~  #  #  ~  #  #
index   0  1  2  3  4  5  6
積水    0  2  0  1  2  1  0  = 6

步驟  l  r  lmax  rmax  比較           處理             累計
 1    0  6   2     2    lmax >= rmax   r=6：2-2 = 0       0
 2    0  5   2     2    lmax >= rmax   r=5：2-1 = 1       1
 3    0  4   2     2    lmax >= rmax   r=4：2-0 = 2       3
 4    0  3   2     2    lmax >= rmax   r=3：2-1 = 1       4
 5    0  2   2     3    lmax <  rmax   l=0：2-2 = 0       4
 6    1  2   2     3    lmax <  rmax   l=1：2-0 = 2       6
 7    2  2   3     3    lmax >= rmax   r=2：3-3 = 0       6
```

第 1–4 步，右側的最大值只有 2，而左側已經有一根高 2 的柱子，所以右指標經過的每一格水位都是 2，可以直接計算，即使中間還有一根更高的 3 也不影響（它只會讓左側的牆更高，而水位由較矮的一側決定）。第 5 步右指標碰到 3，`rmax` 變成 3，此時左側比較矮，換成處理左指標。第 7 步兩指標在最高的柱子相遇，它本身不積水。

### 解法

```python
import random


def trap(height: list[int]) -> int:
    l, r = 0, len(height) - 1
    lmax = rmax = 0
    water = 0
    while l <= r:
        lmax = max(lmax, height[l])     # lmax = max(height[0..l])
        rmax = max(rmax, height[r])     # rmax = max(height[r..n-1])
        if lmax < rmax:                 # l 的右側真正最大值 >= rmax > lmax，水位 = lmax
            water += lmax - height[l]
            l += 1
        else:                           # r 的左側真正最大值 >= lmax >= rmax，水位 = rmax
            water += rmax - height[r]
            r -= 1
    return water


def trap_prefix(height: list[int]) -> int:
    """O(n) 空間的前綴最大值版本。"""
    n = len(height)
    max_l, max_r = [0] * n, [0] * n
    for i in range(n):
        max_l[i] = max(height[i], max_l[i - 1] if i else 0)
    for i in range(n - 1, -1, -1):
        max_r[i] = max(height[i], max_r[i + 1] if i < n - 1 else 0)
    return sum(min(max_l[i], max_r[i]) - height[i] for i in range(n))


def brute(height):
    n = len(height)
    return sum(min(max(height[:i + 1]), max(height[i:])) - height[i] for i in range(n))


assert trap([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]) == 6
assert trap([4, 2, 0, 3, 2, 5]) == 9
assert trap([3]) == 0
assert trap([1, 2, 3]) == 0
assert trap([5, 0, 0, 5]) == 10
assert trap([2, 0, 3, 1, 0, 1, 2]) == 6
assert trap([5, 4, 1, 2]) == 1
for _ in range(1000):
    h = [random.randint(0, 6) for _ in range(random.randint(1, 12))]
    assert trap(h) == trap_prefix(h) == brute(h)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每一步處理一格、移動一個指標，共 n 步。空間 O(1)。前綴版本 O(n) 時間、O(n) 空間。邊界情況：n = 1 時迴圈一次，`lmax == rmax == height[0]`，積水 0；單調遞增或遞減時每格的水位都等於自己的高度；有多根同為最高的柱子時，兩指標可能停在不同的最高柱上，`lmax == rmax` 時走 `else` 分支，水位就是那個最大值，仍然正確。迴圈條件用 `l <= r`，讓每一格（包括相遇的那一格）都被處理一次，這樣不需要額外論證相遇點的積水為 0。總水量不超過 (n − 2) × 10⁵，約 2 × 10⁹，已經逼近 Java int 的上限（約 2.147 × 10⁹），只要限制稍微放寬就會溢位，保險起見用 long。

### Follow-up

> [!question]- F1. 如果是二維的地形高度圖呢（407. Trapping Rain Water II）？
> 二維時一格的水位不再是「左右最大值的較小者」，而是「從這格走到邊界的所有路徑中，路徑上最高點的最小值」。做法是把一維的「從較矮的一側往內處理」推廣：把所有邊界格放進 min-heap，每次彈出高度最低的格子 h，檢查它的四個鄰居，未拜訪的鄰居若比 h 低就積水 `h − 鄰居高度`，然後以 `max(h, 鄰居高度)` 推入 heap。時間 O(mn log(mn))，空間 O(mn)。正確性和本題的雙指標相同：目前邊界上最矮的那一格，決定了它鄰居的水位（第 14 章、第 15 章的 heap 與 BFS 組合）。

> [!question]- F2. 如果柱子是一根一根從右側加進來（串流），要隨時回報目前的總積水量呢？
> 雙指標需要知道右端，不適用於串流；改用 monotonic stack（第 10 章）。stack 中維護高度遞減的柱子索引；新柱子 h 進來時，只要 stack 頂端比 h 矮，就把它彈出當作「底」，與新的 stack 頂端（左牆）和 h（右牆）圍出一層水：寬 `i − left − 1`、高 `min(height[left], h) − height[底]`。每根柱子最多進出 stack 一次，所以每次加入的攤銷成本是 O(1)，總積水量隨時可得。新柱子只會讓已經計入的水位上升而不會下降，所以這種「逐層加水」的計算方式在串流中是正確的。

> [!question]- F3. 能不能用 stack 寫出完整的離線解法？和雙指標有什麼不同？
> 可以，就是 F2 的做法一次跑完。雙指標是「逐欄」計算（每一格的水柱高度），stack 是「逐層」計算（每次彈出時，算一段水平的水層）。兩者都是 O(n) 時間，stack 是 O(n) 空間。stack 版本的優點是只需要從左到右掃一次，能處理串流；雙指標的優點是 O(1) 空間。
> ```python
> def trap_stack(height):
>     st, water = [], 0
>     for i, h in enumerate(height):
>         while st and height[st[-1]] < h:
>             bottom = st.pop()
>             if not st:
>                 break                         # 左邊沒有牆，水會流走
>             left = st[-1]
>             water += (min(height[left], h) - height[bottom]) * (i - left - 1)
>         st.append(i)
>     return water
> ```

> [!question]- F4. 如果每根柱子的寬度不同（給一個寬度陣列 w）呢？
> 逐欄計算的公式只差一個乘數：位置 i 的積水量變成 `(min(maxL[i], maxR[i]) − height[i]) × w[i]`。水位只由高度決定，與寬度無關，所以雙指標的排除論證完全不變，只要在累加時乘上 `w[l]` 或 `w[r]`。時間 O(n)、空間 O(1)。這個 follow-up 是在檢查你是否真的理解「水位由兩側最大值的較小者決定」，而不是背程式。

### 心得

關鍵突破是把「水池」拆成「每一欄的水柱」，而每欄的水位只取決於兩側最大值中**較小的那個**；雙指標利用的是：只要知道哪一側的最大值比較小，就不需要知道另一側確切的最大值。它和核心題 3（11）都是「從兩端往內、處理較矮的一側」，但 11 是挑兩條線、忽略中間，這題是每一欄都要累加，而且水位由整段的最大值決定。面試時建議依序講三個版本：O(n²) 逐欄掃描、O(n) 空間的前綴最大值、O(1) 空間的雙指標，並在講雙指標時明確說出「`lmax < rmax` 時，l 右邊真正的最大值只會 ≥ rmax」這一句，這是整題的正確性所在。

## 難題 2｜287. Find the Duplicate Number｜Medium

### 題目

給一個長度為 n + 1 的整數陣列 `nums`，每個元素都在 `[1, n]` 之間。根據鴿籠原理，至少有一個值重複；題目保證**只有一個值**重複，但它可能出現兩次以上（其他某些值因此沒有出現）。請回傳這個重複的值。限制：不能修改陣列、只能用 O(1) 額外空間、時間要低於 O(n²)。`1 <= n <= 10⁵`。

- 範例 1：`nums = [1, 3, 4, 2, 2]`，回傳 `2`。
- 範例 2：`nums = [3, 1, 3, 4, 2]`，回傳 `3`。
- 範例 3（邊界）：`nums = [3, 3, 3, 3, 3]`，回傳 `3`，重複值出現了 5 次，1、2、4 都沒有出現。
- 範例 4（邊界）：`nums = [1, 1]`，n = 1，回傳 `1`。

### 提示

> [!tip]- 提示 1
> 把陣列看成一個函數：從索引 i 走到索引 `nums[i]`。因為值都在 `[1, n]`，這永遠是合法的索引。從索引 0 開始一直走，會發生什麼事？

> [!tip]- 提示 2
> 沒有任何值等於 0，所以沒有人會走回索引 0，索引 0 一定是一條「尾巴」的起點。走下去一定會進入環。環的入口有什麼特別之處？

> [!tip]- 提示 3
> 環的入口有兩條邊指向它：一條來自尾巴、一條來自環上。兩個不同的索引指向同一個位置，代表它們的值相同。用 Floyd 快慢指標找環的入口（就是第 11 章 142 題的做法）。

### 詳解

**為什麼直覺做法都不行**。排序後找相鄰相等的元素是 O(n log n)，但會修改陣列（或需要 O(n) 的複本）；hash set 是 O(n) 時間但 O(n) 空間；第 4 章難題 1（41）的「把值放到對應索引」或「把看過的位置標成負數」都會修改陣列。用總和減去 1 到 n 的和也不行，因為重複值可能出現很多次，其他值會缺席，差值無法還原出重複值（例如範例 3）。XOR 技巧同理失效。

**一個合格的 O(n log n) 解：對值二分**。令 `count(x)` = 陣列中 ≤ x 的元素個數。若 x 小於重複值 d，`[1, x]` 中的每個值最多出現一次，`count(x) <= x`；若 x ≥ d，大於 x 的值最多各出現一次，共 ≤ n − x 個，所以 `count(x) >= n + 1 − (n − x) = x + 1 > x`。於是 `count(x) > x` 對 x 是 F…F T…T，d 就是第一個 True，可以用第 8 章的模板，O(n log n) 時間、O(1) 空間，滿足所有限制。

**突破點：把陣列變成鏈結串列**。定義 f(i) = `nums[i]`，從 0 出發依序走 0 → f(0) → f(f(0)) → …。因為只有 n + 1 個索引，走下去必然重複，形成「一條尾巴接一個環」的 ρ 形。索引 0 沒有入邊（沒有值是 0），所以 0 不在環上，尾巴長度 a ≥ 1。環的入口 e 有兩個前驅：尾巴上的最後一個節點 p，以及環上的前一個節點 q，而 p ≠ q（p 不在環上）。f(p) = f(q) = e 代表 `nums[p] == nums[q] == e`，**e 就是重複的值**。

**Floyd 演算法為什麼找得到入口**。第一階段，slow 每次走一步、fast 每次走兩步。兩者都進入環之後，fast 每一步都把距離拉近 1，所以在 L（環長）步之內一定相遇。設相遇時 slow 走了 t 步，fast 走了 2t 步，兩者在同一個位置，所以多走的 t 步是 L 的倍數：t ≡ 0 (mod L)。第二階段，把一個指標放回 0，兩個指標都每次走一步。放回 0 的那個走 a 步到達 e；另一個從相遇點（離起點 t 步）再走 a 步，等於從起點走了 t + a 步，它在環上的位置是「入口往前 (t + a − a) mod L = t mod L = 0 步」，也就是 e。在此之前，一個在尾巴上、一個在環上，不可能相遇，所以第一次相遇的地方就是 e。

```text
nums = [1, 3, 4, 2, 2]
index:  0  1  2  3  4

函數圖：0 → 1 → 3 → 2 → 4
                    ↑   ↓
                    └───┘        環 = {2, 4}，入口 = 2
索引 3 和索引 4 都指向 2（nums[3] = nums[4] = 2），所以 2 重複

第一階段（slow 一步、fast 兩步，都從 0 出發）
步   slow   fast
 1    1      3        fast: 0→1→3
 2    3      4        fast: 3→2→4
 3    2      4        fast: 4→2→4
 4    4      4        相遇於 4

第二階段（p 從 0、q 從 4，各走一步）
步   p   q
 1   1   2
 2   3   4
 3   2   2           相遇於 2 → 回傳 2

驗證：尾巴 a = 3（0→1→3→2），環長 L = 2，相遇時 t = 4 是 L 的倍數
```

這個例子中，尾巴是 0 → 1 → 3，第 3 步到達入口 2。第一階段在第 4 步相遇於索引 4，t = 4 剛好是環長 2 的倍數。第二階段 p 走 3 步到達 2，q 從 4 走 3 步：4 → 2 → 4 → 2，也停在 2。

### 解法

```python
import random


def find_duplicate(nums: list[int]) -> int:
    slow = fast = 0
    while True:                       # 第一階段：在環上相遇
        slow = nums[slow]
        fast = nums[nums[fast]]
        if slow == fast:
            break
    slow = 0
    while slow != fast:               # 第二階段：同速前進，相遇點是環的入口
        slow = nums[slow]
        fast = nums[fast]
    return slow


def find_duplicate_bs(nums: list[int]) -> int:
    """對值二分：第一個讓 count(<= x) > x 的 x。O(n log n) 時間、O(1) 空間。"""
    lo, hi = 1, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if sum(x <= mid for x in nums) > mid:
            hi = mid
        else:
            lo = mid + 1
    return lo


def gen(n):
    d = random.randint(1, n)
    c = random.randint(2, n + 1)                     # d 出現 c 次
    others = random.sample([v for v in range(1, n + 1) if v != d], n + 1 - c)
    arr = [d] * c + others
    random.shuffle(arr)
    return arr, d


assert find_duplicate([1, 3, 4, 2, 2]) == 2
assert find_duplicate([3, 1, 3, 4, 2]) == 3
assert find_duplicate([3, 3, 3, 3, 3]) == 3
assert find_duplicate([1, 1]) == 1
assert find_duplicate([2, 2, 2]) == 2
for _ in range(1000):
    arr, d = gen(random.randint(1, 9))
    before = arr[:]
    assert find_duplicate(arr) == d == find_duplicate_bs(arr)
    assert arr == before                             # 沒有修改輸入
print("all tests passed")
```

### 複雜度與邊界

Floyd 版本時間 O(n)：第一階段在 slow 進入環後 L 步內相遇，總步數 ≤ a + L ≤ n + 1；第二階段 a 步。空間 O(1)，沒有修改陣列。二分版本 O(n log n) 時間、O(1) 空間。邊界情況：n = 1（`[1, 1]`）時 0 → 1 → 1，環是自環 {1}，兩階段都正確；重複值出現很多次時（`[3, 3, 3, 3, 3]`），0 → 3 → 3，仍然是自環；起點必須是 0，若從環上的某個索引出發，第二階段找到的是「起點本身」而不是重複值。題目保證值在 `[1, n]` 之內，如果有越界的值，函數圖就不成立，要先檢查。

### Follow-up

> [!question]- F1. 如果允許修改陣列呢？
> 可以用 O(n) 時間、O(1) 空間的標記法：掃過每個值 v，看 `nums[|v|]` 是否已經是負數，是的話 |v| 就是重複值，否則把它設成負數；最後若需要還原就把所有值取絕對值。另一種是 cyclic sort：讓值 v 住在索引 v（陣列有 n + 1 個位置，索引 0 空著），不斷把 `nums[i]` 換到索引 `nums[i]`，若目標位置已經住著相同的值，就找到重複。這兩種都是第 4 章難題 1（41. First Missing Positive）的手法。面試時要指出它們違反了「不能修改輸入」的限制，所以原題才需要 Floyd。

> [!question]- F2. 如果有好幾個不同的值都重複了，Floyd 還能用嗎？
> 能找到「其中一個」重複值，但不能找到全部。論證完全相同：從 0 出發一定會進入某個環，環的入口有兩個前驅，所以入口的值一定重複；但其他重複值可能不在這條路徑上。若要找出所有重複的值（442. Find All Duplicates in an Array，每個值最多出現兩次），就需要 F1 的標記法，O(n) 時間、O(1) 額外空間，但會修改陣列。這也說明了原題「只有一個重複值」的保證，其實是讓答案唯一，而不是 Floyd 正確性的前提。

> [!question]- F3. 如果是 1 到 n 的陣列中，恰好一個值重複一次、一個值缺失呢（645. Set Mismatch）？
> 這時資訊更多，可以用代數：設重複值 d、缺失值 m，`sum(nums) − n(n+1)/2 = d − m`，`sum(x²) − Σi² = d² − m²`，兩式相除得 `d + m`，解聯立方程即可，O(n) 時間、O(1) 空間、不修改陣列。也可以用 XOR 分組：先求 `d ^ m`，取其最低位的 1 把所有值與 1..n 分成兩組，各自 XOR 得到 d 和 m，再掃一遍判斷哪個是重複的。和原題的差別在於「重複一次」：原題重複次數不定，代數法就失效了。

> [!question]- F4. 如果陣列很大、只能循序讀取（例如存在磁帶或串流中，可以重讀但不能隨機存取）呢？
> Floyd 需要隨機存取 `nums[i]`，不適用。對值二分的版本只需要「數 ≤ mid 的元素個數」，每一輪循序讀一遍即可，總共 O(log n) 遍、O(1) 記憶體，總時間 O(n log n)。這是兩種解法在實務上真正的取捨：Floyd 的讀取次數少，但讀取模式是跳躍的；二分讀取次數多，但完全循序，對快取和外部儲存都友善。

### 心得

關鍵突破是把「值在 [1, n] 的陣列」看成函數 i → nums[i]，於是「重複的值」變成「有兩個前驅的節點」，也就是環的入口，而索引 0 沒有入邊保證了它在尾巴上。它和本章其他題的關係比較特別：前面的題目都是相向指標，這題是同向的快慢指標，排除論證換成了「兩者速度差為 1，所以一定相遇」的距離論證。面試時先講二分答案的 O(n log n) 解（這已經滿足所有限制，而且容易證明），再提出 Floyd；講 Floyd 時先畫出 ρ 形圖、說明為什麼入口就是重複值，再推導 t ≡ 0 (mod L)，比直接背兩階段的程式更有說服力。

## 難題 3｜923. 3Sum With Multiplicity｜Medium

### 題目

給一個整數陣列 `arr` 和整數 `target`，回傳滿足 `i < j < k` 且 `arr[i] + arr[j] + arr[k] == target` 的索引三元組個數。答案可能很大，回傳對 `10⁹ + 7` 取模的結果。和核心題 2 不同，這裡數的是**位置**的組合，值相同但位置不同的三元組要分別計算。限制：`3 <= len(arr) <= 3000`，`0 <= arr[i] <= 100`，`0 <= target <= 300`。

- 範例 1：`arr = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]`、`target = 8`，回傳 `20`。值的組合 (1, 2, 5)、(1, 3, 4)、(2, 2, 4)、(2, 3, 3) 各有 8、8、2、2 種位置選法。
- 範例 2：`arr = [1, 1, 2, 2, 2, 2]`、`target = 5`，回傳 `12`。只有 (1, 2, 2)：選一個 1 有 2 種、從四個 2 選兩個有 C(4, 2) = 6 種，共 12 種。
- 範例 3（邊界）：`arr = [2, 1, 3]`、`target = 6`，回傳 `1`。
- 範例 4（邊界）：`arr = [0, 0, 0, 0]`、`target = 0`，回傳 `C(4, 3) = 4`。

### 提示

> [!tip]- 提示 1
> 條件 `arr[i] + arr[j] + arr[k] == target` 對三個位置是對稱的，所以「i < j < k 的三元組個數」等於「三個位置的子集合個數」。排序會改變位置，但不會改變答案。

> [!tip]- 提示 2
> 排序後固定 i，在右側用相向指標找兩數和。找到相等時，不能只把兩端各移一步，因為重複值會產生很多組合。

> [!tip]- 提示 3
> 找到 `arr[lo] + arr[hi] == T` 時分兩種情況：若 `arr[lo] == arr[hi]`，整段 `[lo, hi]` 都是同一個值，貢獻 C(hi − lo + 1, 2) 組；否則數出左端重複的長度 cl 與右端重複的長度 cr，貢獻 cl × cr 組，再把兩端跳過這兩段。另一個方向是：值只有 0 到 100，直接對值計數。

### 詳解

**為什麼核心題 2 的寫法不能直接用**。3Sum 的去重是為了「每組值只輸出一次」，而這題要數的是「每組值有幾種位置選法」，兩者剛好相反。若沿用「找到就 `lo += 1, hi -= 1`」，例如右側是 `[2, 2, 2, 2]`、要找和為 4，相向指標只會數到 (0, 3) 和 (1, 2) 兩組，實際上有 C(4, 2) = 6 組，因為 (0, 1)、(0, 2) 等組合被當成「已排除」而跳過了。問題在於 5.4 節的排除論證只保證「被丟掉的那一端不可能出現在**更好**的答案中」，對「數出所有答案」而言，相等時丟掉一端會漏算它和其他同值元素的配對。

**突破點一：為什麼可以排序**。題目要求 i < j < k，看起來和位置有關，但條件只看三個值的和，與順序無關。所以每個 3 個位置的子集合恰好對應一個 i < j < k 的三元組，答案就是「和為 target 的 3 元素子集合數」。排序只是重新命名位置，子集合的數量不變。

**突破點二：相等時整段計算**。排序後固定 i，令 `T = target − arr[i]`，在 `[i + 1, n − 1]` 上用相向指標。當 `arr[lo] + arr[hi] == T` 時：

- 若 `arr[lo] == arr[hi]`，因為陣列排序，`[lo, hi]` 之間全是這個值，任選兩個位置都符合，共 C(m, 2) 組（m = hi − lo + 1），而且範圍內不可能再有其他組合，直接結束內層。
- 否則 `arr[lo] < arr[hi]`，左端值 x 有 cl 個連續位置，右端值 y 有 cr 個連續位置，任選一個 x 配一個 y 都符合，共 cl × cr 組。之後範圍內不可能再有含 x 或 y 的組合（x 的搭檔只能是 y），所以 lo 跳過整段 x、hi 跳過整段 y。

**另一種做法：對值計數**。因為值只有 0 到 100，可以先數出 `cnt[v]`，再枚舉 x ≤ y ≤ z 且 x + y + z = target 的值組合（z 由 x、y 決定），依相等情況用組合數計算：三者相同是 C(cnt, 3)；兩個相同是 C(cnt, 2) × 另一個的 cnt；三者不同是三個 cnt 相乘。時間 O(n + V²)，V = 101，與 n 幾乎無關。面試時兩種都值得講：雙指標展示 pattern 的掌握，計數法展示你注意到了值域的限制。

```text
例一：arr = [1, 2, 2, 3, 3, 3]，target = 6（兩端值不同的情況）
i=0 (1)，T = 5，範圍 [1, 5] = [2 2 3 3 3]
  lo=1 hi=5  2 + 3 = 5 = T，兩端值不同
             左端 2 的連續段：index 1, 2 → cl = 2
             右端 3 的連續段：index 3, 4, 5 → cr = 3
             貢獻 2 × 3 = 6，lo 跳到 3、hi 跳到 2，結束
i=1 (2)，T = 4，範圍 [2 3 3 3]：2+3=5 > 4，hi 一路左移，沒有解
其餘 i 也沒有解，答案 = 6
驗證：值組合只有 (1, 2, 3)，位置選法 1 × 2 × 3 = 6

例二：arr = [1, 1, 2, 2, 2, 2]，target = 5（兩端值相同的情況）
i=0 (1)，T = 4，範圍 [1, 5] = [1 2 2 2 2]
  lo=1 hi=5  1 + 2 = 3 < 4   lo=2
  lo=2 hi=5  2 + 2 = 4 = T，兩端值相同 → [2, 5] 全是 2，m = 4，貢獻 C(4,2) = 6，結束
i=1 (1)，T = 4，範圍 [2, 5] = [2 2 2 2]
  lo=2 hi=5  2 + 2 = 4 = T，兩端值相同 → m = 4，貢獻 6
i=2 (2)，T = 3，範圍 [2 2 2]：2+2=4 > 3，沒有解
答案 = 12
```

例一說明了「兩端值不同」時要整段乘起來：若找到後只各移一步，只會數到 (1, 5)、(2, 4) 兩組，漏掉 4 組。例二說明了「兩端值相同」時整段都是同一個值，用組合數一次算完；注意 i = 0 和 i = 1 是兩個不同位置的 1，各自都要算，這和 3Sum 跳過重複的 i 正好相反。

### 解法

```python
import random
from itertools import combinations

MOD = 10**9 + 7


def three_sum_multi(arr: list[int], target: int) -> int:
    arr = sorted(arr)
    n, ans = len(arr), 0
    for i in range(n - 2):
        t = target - arr[i]
        lo, hi = i + 1, n - 1
        while lo < hi:
            s = arr[lo] + arr[hi]
            if s < t:
                lo += 1
            elif s > t:
                hi -= 1
            elif arr[lo] == arr[hi]:          # [lo, hi] 全是同一個值
                m = hi - lo + 1
                ans += m * (m - 1) // 2
                break
            else:
                x, y = arr[lo], arr[hi]
                cl = cr = 0
                while arr[lo] == x:
                    cl += 1
                    lo += 1
                while arr[hi] == y:
                    cr += 1
                    hi -= 1
                ans += cl * cr
    return ans % MOD


def three_sum_multi_count(arr: list[int], target: int) -> int:
    """對值計數：O(n + V²)，V = 101。"""
    cnt = [0] * 101
    for v in arr:
        cnt[v] += 1
    ans = 0
    for x in range(101):
        for y in range(x, 101):
            z = target - x - y
            if z < y or z > 100:
                continue
            if x == y == z:
                ans += cnt[x] * (cnt[x] - 1) * (cnt[x] - 2) // 6
            elif x == y:
                ans += cnt[x] * (cnt[x] - 1) // 2 * cnt[z]
            elif y == z:
                ans += cnt[x] * cnt[y] * (cnt[y] - 1) // 2
            else:
                ans += cnt[x] * cnt[y] * cnt[z]
    return ans % MOD


def brute(arr, target):
    return sum(1 for t in combinations(arr, 3) if sum(t) == target) % MOD


assert three_sum_multi([1, 1, 2, 2, 3, 3, 4, 4, 5, 5], 8) == 20
assert three_sum_multi([1, 1, 2, 2, 2, 2], 5) == 12
assert three_sum_multi([2, 1, 3], 6) == 1
assert three_sum_multi([0, 0, 0, 0], 0) == 4
assert three_sum_multi([1, 2, 2, 3, 3, 3], 6) == 6
assert three_sum_multi([0] * 3000, 0) == 3000 * 2999 * 2998 // 6 % MOD
assert three_sum_multi_count([0] * 3000, 0) == 3000 * 2999 * 2998 // 6 % MOD
for _ in range(500):
    arr = [random.randint(0, 6) for _ in range(random.randint(3, 10))]
    t = random.randint(0, 18)
    assert three_sum_multi(arr, t) == three_sum_multi_count(arr, t) == brute(arr, t)
print("all tests passed")
```

### 複雜度與邊界

雙指標版本時間 O(n²)：排序 O(n log n)，外層 n 次，每次內層 O(n)（跳過重複段時每個位置也只經過一次）。空間 O(n)（排序的複本）。計數版本 O(n + V²) 時間、O(V) 空間，V = 101，在本題的限制下遠比 O(n²) 快。邊界情況：全部相同的值（`[0] * 3000`）時，雙指標版本每個 i 都在第一次比較就走「整段相同」分支，總共 O(n)；外層**不能**跳過重複的 i，因為每個位置都是不同的三元組起點；`arr[lo] == arr[hi]` 的分支必須在 `s == t` 之內判斷，不能只看值相等；Python 的整數不會溢位，所以可以最後再取模，其他語言見 F4。

### Follow-up

> [!question]- F1. 如果值的範圍很大（例如到 10⁹），計數法還能用嗎？
> 不能用固定大小的陣列，但可以改成「對不同的值」計數：用 `Counter` 得到 D 個不同值並排序，枚舉 x ≤ y 兩個不同值的組合，z = target − x − y 用 hash 查 cnt，並依相等情況用組合數。時間 O(n + D²)，D ≤ n，最差和雙指標同樣是 O(n²)，但大量重複時快很多。也可以在排序後的不同值上用相向指標找 y、z，O(D²) 時間、O(D) 空間，不需要 hash。

> [!question]- F2. 如果不想排序，有沒有 O(n²) 的 hash 做法？
> 有。把 j 當作中間的索引，維護一個 counter 記錄 `arr[0..j−1]` 每個值出現的次數；對每個 j，掃所有 k > j，答案加上 `left[target − arr[j] − arr[k]]`；處理完 j 之後再把 `arr[j]` 加入 counter。每個 (i, j, k) 恰好在中間索引為 j 時被數一次，時間 O(n²)、空間 O(V) 或 O(n)。這個寫法直接保留了 i < j < k 的順序，不需要「排序不改變答案」的論證，在題目條件不對稱時（例如要求 `arr[i] < arr[j]`）更有用。

> [!question]- F3. 如果改成數「和 ≤ target」的三元組呢？
> 排序後固定 i，內層用核心題 1 F2 的計數技巧：`arr[lo] + arr[hi] <= T` 時，lo 配 `lo + 1 … hi` 每個位置都符合，加上 `hi − lo` 組，然後 `lo += 1`；否則 `hi -= 1`。這個版本反而不需要處理重複值，因為「整段都符合」的計數方式自然把同值的位置分開數了。時間 O(n²)、空間 O(1)（不含排序）。這說明了「等於」的計數比「不等式」的計數更麻煩：相等是一個點，兩端的重複段必須特別處理。

> [!question]- F4. 在 Java 或 C++ 中要注意什麼？
> 答案在取模之前可以到 C(3000, 3) ≈ 4.5 × 10⁹，超過 32 位元整數的上限（約 2.1 × 10⁹），所以累加變數要用 64 位元，或每次加完就取模。組合數 `m * (m - 1) / 2` 中 m 最大 3000，乘積約 9 × 10⁶，不會溢位；但計數版本的 `cnt[x] * (cnt[x] - 1) * (cnt[x] - 2)` 可達 2.7 × 10¹⁰，必須先轉成 64 位元再相乘。Python 沒有這個問題，但面試時主動說出來是加分。

### 心得

關鍵突破有兩個：條件對位置對稱，所以可以排序而不改變答案；以及相向指標在「相等」時不能只丟掉一端，必須把兩端的重複段整段計算（同值則用組合數，異值則相乘）。它和核心題 2（3Sum）是同一個骨架、相反的目標：3Sum 要跳過重複值以免重複輸出，這題要把重複值的組合全部數進來，連外層的 i 都不能跳。面試時先點出「排序不影響答案」，再說明相等時的兩種情況，最後提一句「值域只有 101，可以直接對值計數」，讓面試官知道你同時看到了 pattern 與限制條件。

## 難題 4｜1793. Maximum Score of a Good Subarray｜Hard

### 題目

給一個正整數陣列 `nums` 和一個索引 `k`。子陣列 `nums[i..j]` 的分數定義為 `min(nums[i..j]) × (j − i + 1)`。一個「好的」子陣列必須滿足 `i <= k <= j`（包含位置 k）。回傳好子陣列的最大分數。限制：`1 <= len(nums) <= 10⁵`，`1 <= nums[i] <= 2 × 10⁴`，`0 <= k < len(nums)`。

- 範例 1：`nums = [1, 4, 3, 7, 4, 5]`、`k = 3`，回傳 `15`。最佳子陣列是 `nums[1..5] = [4, 3, 7, 4, 5]`，最小值 3、長度 5。
- 範例 2：`nums = [5, 5, 4, 5, 4, 1, 1, 1]`、`k = 0`，回傳 `20`，取 `nums[0..4]`，最小值 4、長度 5。
- 範例 3（邊界）：`nums = [7]`、`k = 0`，回傳 `7`。
- 範例 4（邊界）：`nums = [1, 100, 1]`、`k = 1`，回傳 `100`，只取 k 本身最好，往外擴會讓最小值掉到 1。

### 提示

> [!tip]- 提示 1
> 子陣列必須包含 k，所以它一定是從 k 往左右兩側延伸出來的。如果固定最小值至少是 v，最長能延伸到哪裡？

> [!tip]- 提示 2
> 從 `i = j = k` 開始，每次往外擴一格。往哪一側擴？想想看：擴到比較小的那一側，會不會錯過什麼？

> [!tip]- 提示 3
> 每次往「下一個元素比較大」的那一側擴（越界視為 0），並更新目前的最小值與分數。可以證明：對每個門檻 v，這個過程一定會經過「包含 k 且所有元素 ≥ v 的最長區間」。

### 詳解

**為什麼直覺做法不夠**。暴力解枚舉所有 i ≤ k ≤ j：固定 i，讓 j 從 k 往右延伸並維護最小值，O(n²)，n = 10⁵ 時太慢。這題看起來像核心題 3（11），可以「從兩端往內收縮」嗎？不行：從 `[0, n − 1]` 開始往內縮，丟掉一端時無法證明它不在最佳解中，因為最小值由整段決定，丟掉一個小值可能讓分數變大，也可能讓長度損失太多。

**突破點：反過來從 k 往外擴**。分數 = 最小值 × 長度。往外擴一格，長度一定加 1，最小值可能不變或下降。從 `[k, k]` 出發，每次在左邊 `nums[i − 1]` 和右邊 `nums[j + 1]` 中選**較大**的一個擴進來（越界那側視為 0），這樣最小值下降得最慢。每擴一次就計算一次分數，取最大值。共 n − 1 步，O(n)。

**正確性：為什麼貪婪擴張不會錯過最佳解**。設最佳解是 `[a, b]`，最小值 m。令 `[L, R]` 是包含 k 且所有元素都 ≥ m 的**最長**區間，則 `[a, b] ⊆ [L, R]`，而 `[L, R]` 的分數 ≥ m × (R − L + 1) ≥ m × (b − a + 1)，所以只要證明貪婪過程一定會經過 `[L, R]` 即可。假設目前的窗口 `[i, j]` 在 `[L, R]` 之內但還沒等於它。兩側的下一個元素中：在 `[L, R]` 之內的那側 ≥ m；在 `[L, R]` 之外的那側（如果有）< m 或越界（視為 0 < m）。所以若只有一側還在 `[L, R]` 內，它的元素嚴格比另一側大，貪婪一定選它；若兩側都還在內，選哪一側都不會離開 `[L, R]`。因此窗口在填滿 `[L, R]` 之前絕不會跨出去，必然會在某一步恰好等於 `[L, R]`，那一步算出的分數 ≥ 最佳解。

```text
nums = [1, 4, 3, 7, 4, 5]，k = 3
index:  0  1  2  3  4  5

步驟  窗口    左鄰  右鄰  擴張   min  長度  分數  best
 0   [3,3]    3     4    —      7    1     7     7
 1   [3,4]    3     4    右     4    2     8     8      右鄰 4 > 左鄰 3
 2   [3,5]    3     5    右     4    3    12    12      右鄰 5 > 左鄰 3
 3   [2,5]    3     0    左     3    4    12    12      右邊越界視為 0
 4   [1,5]    4     0    左     3    5    15    15
 5   [0,5]    1     0    左     1    6     6    15

門檻 v = 3 時，包含 k 且全部 ≥ 3 的最長區間是 [1, 5]，第 4 步恰好經過它
```

第 1、2 步往右擴，因為右側的 4、5 都比左側的 3 大，最小值維持在 4；第 3 步右側已經越界，只能往左擴進 3，最小值降到 3；第 4 步再擴進 4，長度變 5，得到最佳分數 15。如果在第 1 步錯誤地先往左擴進 3，最小值會立刻降到 3，雖然之後仍可能到達 `[1, 5]`，但證明就不成立了，在別的輸入上可能錯過最佳解。

### 解法

```python
import random


def maximum_score(nums: list[int], k: int) -> int:
    n = len(nums)
    i = j = k
    cur = best = nums[k]
    while i > 0 or j < n - 1:
        left = nums[i - 1] if i > 0 else 0          # 越界視為 0（所有元素都 >= 1）
        right = nums[j + 1] if j < n - 1 else 0
        if left >= right:
            i -= 1
            cur = min(cur, left)
        else:
            j += 1
            cur = min(cur, right)
        best = max(best, cur * (j - i + 1))
    return best


def maximum_score_stack(nums: list[int], k: int) -> int:
    """以每個元素為最小值的最長區間（第 10 章 84 題的做法），只取包含 k 的。"""
    n = len(nums)
    left, right, st = [-1] * n, [n] * n, []
    for i, x in enumerate(nums):
        while st and nums[st[-1]] >= x:
            st.pop()
        left[i] = st[-1] if st else -1               # 左邊第一個 < x 的位置
        st.append(i)
    st = []
    for i in range(n - 1, -1, -1):
        while st and nums[st[-1]] >= nums[i]:
            st.pop()
        right[i] = st[-1] if st else n               # 右邊第一個 < x 的位置
        st.append(i)
    return max(nums[p] * (right[p] - left[p] - 1)
               for p in range(n) if left[p] < k < right[p])


def brute(nums, k):
    best = 0
    for i in range(k + 1):
        for j in range(k, len(nums)):
            best = max(best, min(nums[i:j + 1]) * (j - i + 1))
    return best


assert maximum_score([1, 4, 3, 7, 4, 5], 3) == 15
assert maximum_score([5, 5, 4, 5, 4, 1, 1, 1], 0) == 20
assert maximum_score([7], 0) == 7
assert maximum_score([1, 100, 1], 1) == 100
assert maximum_score([2, 2, 2, 2], 3) == 8
for _ in range(1000):
    arr = [random.randint(1, 8) for _ in range(random.randint(1, 10))]
    kk = random.randrange(len(arr))
    assert maximum_score(arr, kk) == maximum_score_stack(arr, kk) == brute(arr, kk)
print("all tests passed")
```

### 複雜度與邊界

貪婪擴張時間 O(n)：每一步窗口長度加 1，共 n − 1 步。空間 O(1)。stack 版本也是 O(n) 時間，但需要 O(n) 空間。邊界情況：n = 1 時迴圈不執行，答案是 `nums[k]`；k 在陣列端點時其中一側一開始就越界，用 0 當哨兵自然只往另一側擴；兩側相等時選哪邊都可以（證明中兩側都在 `[L, R]` 內，或都在外）；哨兵 0 的正確性依賴「所有元素 ≥ 1」，若元素可以是 0，越界側的哨兵 0 會和值為 0 的真實元素打平，`left >= right` 可能選到越界的那一側、讓索引變成 −1，所以哨兵要改成 −1（嚴格小於所有合法值）。

### Follow-up

> [!question]- F1. 如果沒有「必須包含 k」的限制呢？
> 那就是 84. Largest Rectangle in Histogram（第 10 章難題 1）：對每個元素 p，找左右第一個比它小的位置，以 `nums[p]` 為最小值的最長區間長度是 `right[p] − left[p] − 1`，取所有 p 的最大值，monotonic stack O(n)。貪婪擴張在沒有固定點時無法使用，因為不知道從哪裡開始擴；硬要對每個 k 各做一次是 O(n²)。解法中的 `maximum_score_stack` 正是 84 題的程式加上「區間包含 k」的過濾。

> [!question]- F2. 如果有 q 個不同的 k 要查詢呢？
> 每次查詢都做一次擴張是 O(qn)。更好的做法是先用 stack 求出每個 p 的最長區間 `[L_p, R_p]` 與分數 `v_p = nums[p] × (R_p − L_p + 1)`，查詢 k 的答案就是「所有包含 k 的區間中最大的 v_p」。這是區間覆蓋取最大值的問題：把區間依 v_p 由大到小排序，用 union-find 的「下一個未填位置」技巧，把每個區間內還沒填的位置填上 v_p，每個位置只被填一次。總時間 O(n log n + q)，排序是瓶頸；也可以用 segment tree 做區間 chmax（第 26 章）。

> [!question]- F3. 如果分數改成「最小值 × 區間和」呢？
> 這是 1856. Maximum Subarray Min-Product 加上包含 k 的限制。貪婪擴張仍然正確：證明中只用到「在 `[L, R]` 之內，延伸不會讓目標變差」，而所有元素為正時，區間越長和越大，所以 `[L, R]` 的分數 ≥ m × sum(`[a, b]`)。實作時用前綴和 O(1) 算區間和，或在擴張時直接累加。時間 O(n)、空間 O(1)。沒有 k 的版本同樣用 monotonic stack 加前綴和。

> [!question]- F4. 如果要回傳最佳子陣列的端點呢？
> 在更新 best 時一併記錄當時的 `(i, j)` 即可，O(1) 額外成本。要注意分數相同的子陣列可能有很多個，若題目要求「最短」或「最左」的那一個，就要在分數相等時依規則比較，而不是只用 `>` 或 `>=` 決定是否更新。用 `>` 更新會保留最早出現的（也就是較短的）窗口，因為貪婪擴張的窗口長度是遞增的。

### 心得

關鍵突破是把「最小值 × 長度」看成「對每個最小值門檻，取最長的區間」，而從 k 往較大的一側擴張，保證了每個門檻的最長區間都會被經過。它和核心題 3（11）、難題 1（42）是鏡像關係：那兩題從外往內收縮、丟掉較矮的一側；這題從內往外擴張、先吞較高的一側，三者的共同點都是「較矮的那一側決定了瓶頸」。面試時先說 O(n²) 暴力，再提出擴張策略，最重要的是講出「`[L, R]` 一定會被經過」的證明，並提到沒有 k 時這題就是 84，展示你知道 monotonic stack 的通用解。

## 難題 5｜2009. Minimum Number of Operations to Make Array Continuous｜Hard

### 題目

給一個長度為 n 的整數陣列 `nums`。一次操作可以把任意一個元素換成任意整數。若陣列同時滿足兩個條件，就稱為「連續的」：所有元素互不相同，而且 `max(nums) − min(nums) == n − 1`。換句話說，陣列恰好由 n 個連續整數組成（順序不限）。回傳讓 `nums` 變成連續陣列的最少操作次數。限制：`1 <= n <= 10⁵`，`1 <= nums[i] <= 10⁹`。

- 範例 1：`nums = [4, 2, 5, 3]`，回傳 `0`，已經是 2 到 5。
- 範例 2：`nums = [1, 2, 3, 5, 6]`，回傳 `1`，把 1 換成 4 得到 2 到 6。
- 範例 3：`nums = [1, 10, 100, 1000]`，回傳 `3`，保留任何一個，其他三個都要換。
- 範例 4（邊界）：`nums = [8, 8, 8]`，回傳 `2`，重複的值至少要換掉兩個；`nums = [5]`，回傳 `0`。

### 提示

> [!tip]- 提示 1
> 與其想「換掉哪些」，不如想「保留哪些」。最後的陣列是某個 `{s, s + 1, …, s + n − 1}`，保留下來的元素必須滿足什麼條件？

> [!tip]- 提示 2
> 保留的元素必須互不相同，而且都落在 `[s, s + n − 1]` 之內；被換掉的元素可以填補所有空缺。所以答案是 n 減去「某個長度為 n 的值域窗口中，最多包含幾個不同的值」。

> [!tip]- 提示 3
> 把不同的值排序成 `u`。最佳窗口可以假設從某個 `u[i]` 開始；對每個 i，找最大的 j 使 `u[j] <= u[i] + n − 1`。i 增加時 j 不會減少，用兩個同向指標。

### 詳解

**為什麼直覺做法不夠**。直接模擬「換哪一個、換成什麼」的選擇空間是無限的。另一個直覺是以中位數或平均值為中心放一個窗口，但這沒有理論根據：範例 3 中值的分布非常分散，任何一個窗口都只能包含一個值。還有一個常見的錯誤是把窗口長度設成「去重後的個數」，但最後的陣列有 n 個元素（包括被換掉的），值域長度一定是 n，和去重無關。

**突破點：把最少操作變成最多保留**。固定最後的值集合 `S = {s, …, s + n − 1}`。一個元素可以不換，若且唯若它的值在 S 中，而且同一個值只能保留一個（最後要互不相同）。被換掉的元素數量恰好等於 S 中「沒有被保留的值」的數量，因為兩者都是 n 減去保留數，所以一定能填滿所有空缺。於是對固定的 s，操作數是 `n − |{不同的值} ∩ S|`，我們要找一個長度為 n 的整數區間，包含最多個不同的原始值。

**為什麼窗口可以從某個原始值開始**。若最佳窗口 `[s, s + n − 1]` 包含的最小原始值是 `u[i] > s`，把窗口右移到 `[u[i], u[i] + n − 1]`，左邊丟掉的部分沒有任何原始值，右邊只可能多包含一些，所以不會變差。因此只要對每個 i 考慮窗口 `[u[i], u[i] + n − 1]`，數出其中有幾個 `u[j]`。因為 u 是排序的，這個數量是 `j − i`，其中 j 是第一個 `u[j] > u[i] + n − 1` 的位置。i 增加時窗口右端 `u[i] + n − 1` 只會增加，所以 j 只會往右，兩個指標各走一遍，O(m)，m 是不同值的個數；加上排序總共 O(n log n)。

```text
nums = [1, 1, 2, 9, 10, 11, 20]，n = 7
去重排序 u = [1, 2, 9, 10, 11, 20]
index:        0  1  2   3   4   5

  i  u[i]  窗口 [u[i], u[i]+6]   j（第一個超出窗口）  窗口內的值        個數 j-i
  0   1      [1, 7]               2                 1, 2              2
  1   2      [2, 8]               2                 2                 1
  2   9      [9, 15]              5                 9, 10, 11         3   ← 最多
  3  10      [10, 16]             5                 10, 11            2
  4  11      [11, 17]             5                 11                1
  5  20      [20, 26]             6                 20                1

最多保留 3 個 → 操作數 = 7 - 3 = 4
做法：保留 9, 10, 11，把 1, 1, 2, 20 換成 12, 13, 14, 15
```

j 在整個過程中只往右移：i = 0 時 j 移到 2，i = 2 時一口氣移到 5，i = 5 時移到 6，總共移動 6 次。注意兩個 1 只算一次「可保留的值」，另一個 1 一定要換掉；窗口長度用的是原始的 n = 7，不是去重後的 6。若誤用 6，窗口 `[9, 14]` 仍然包含 3 個值，這個例子剛好不受影響，但 `[1, 1, 1, 4]` 這類輸入就會出錯：正確答案是 2（保留 1 和 4，把另外兩個 1 換成 2 和 3），若誤用去重後的長度 2 當窗口，`[1, 2]` 和 `[4, 5]` 都只包含一個值，會得到 3。

### 解法

```python
import random
from bisect import bisect_right


def min_operations(nums: list[int]) -> int:
    n = len(nums)
    u = sorted(set(nums))
    best = j = 0
    for i in range(len(u)):
        while j < len(u) and u[j] <= u[i] + n - 1:   # 窗口長度用原始 n
            j += 1
        best = max(best, j - i)
    return n - best


def min_operations_bisect(nums: list[int]) -> int:
    """同樣的想法，用 binary search 找右端，O(n log n)。"""
    n, u = len(nums), sorted(set(nums))
    return n - max(bisect_right(u, u[i] + n - 1) - i for i in range(len(u)))


def brute(nums):
    n, vals = len(nums), set(nums)
    best = max(sum(1 for v in vals if s <= v <= s + n - 1)
               for s in range(min(nums) - n, max(nums) + 1))
    return n - best


assert min_operations([4, 2, 5, 3]) == 0
assert min_operations([1, 2, 3, 5, 6]) == 1
assert min_operations([1, 10, 100, 1000]) == 3
assert min_operations([8, 8, 8]) == 2
assert min_operations([5]) == 0
assert min_operations([1, 1, 2, 9, 10, 11, 20]) == 4
assert min_operations([1, 1, 2, 3]) == 1
assert min_operations([1, 1, 1, 4]) == 2
for _ in range(1000):
    arr = [random.randint(1, 15) for _ in range(random.randint(1, 8))]
    assert min_operations(arr) == min_operations_bisect(arr) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n log n)，瓶頸是排序；兩個指標各走 m ≤ n 步。空間 O(n)，用於去重後的陣列。bisect 版本同樣 O(n log n)。邊界情況：n = 1 時窗口 `[u[0], u[0]]` 包含自己，答案 0；全部相同時 m = 1，最多保留 1 個，答案 n − 1；值可達 10⁹，`u[i] + n − 1` 在 Python 中沒有問題，在 Java 中約 10⁹ + 10⁵，仍在 int 範圍內但很接近，保險起見用 long；已經連續的陣列在 i = 0 時就得到 best = n。最容易犯的錯是窗口長度用 `len(u)` 或 `len(u) − 1`，以及忘記去重（重複的值會被算成多個可保留的元素）。

### Follow-up

> [!question]- F1. 如果操作改成「把某個元素加 1 或減 1」，要讓陣列變成連續的最少操作次數呢？
> 這時成本是移動距離，不再是「換或不換」。排序成 a 之後，最後的值必定依序對應 `b, b + 1, …, b + n − 1`（排序後一一配對是最佳的，否則交換兩個交叉的配對不會變差），總成本是 Σ |a[i] − (b + i)| = Σ |(a[i] − i) − b|。令 `c[i] = a[i] − i`，這是一維的「找一點使絕對距離和最小」，答案取 c 的中位數。時間 O(n log n)。這個 follow-up 很適合用來測試你是否能辨認「成本模型改變後 pattern 也跟著改變」。

> [!question]- F2. 如果要輸出一個具體的最終陣列呢？
> 先用雙指標找到最佳的 i，最終值集合是 `[u[i], u[i] + n − 1]`。掃一遍原陣列：值在範圍內而且還沒被保留過的，原地保留並記錄；其他位置（範圍外或重複）先標記為待換。再列出範圍內沒有出現的值，依序填入待換的位置。用一個 set 記錄已保留的值，總時間 O(n log n)（排序）加 O(n)。待換位置的數量恰好等於缺少的值的數量，這正是詳解中「一定能填滿」的論證。

> [!question]- F3. 如果只能刪除元素（不能替換），要留下最長的一組連續整數呢？
> 刪除不能填補空缺，所以保留的值本身必須是連續的，問題變成「不同值中最長的連續整數段」，也就是 128. Longest Consecutive Sequence（第 4 章核心題 3），用 hash set 可以 O(n) 完成。對比本題：替換操作讓窗口內的空缺可以被填滿，所以只需要窗口的值域長度固定為 n，不要求窗口內的值連續。兩題的差別完全在操作的能力上，面試時說出這個對比能展示你對題目模型的理解。

> [!question]- F4. 如果目標改成「公差為 d 的等差數列」（d 給定）呢？
> 最終集合是 `{s, s + d, …, s + (n − 1)d}`，保留的元素必須互不相同、模 d 同餘於 s，而且落在 `[s, s + (n − 1)d]` 之內。所以先把不同的值依 `v mod d` 分組，每組內排序後套用同樣的雙指標，窗口條件改成 `u[j] <= u[i] + (n − 1)d`，取所有組中的最大保留數。總時間 O(n log n)。d = 1 時只有一組，就是原題。

### 心得

關鍵突破是把「最少替換」轉成「最多保留」，而保留的條件只有兩個：值互不相同、落在一個長度為 n 的值域窗口內；替換掉的元素一定能填滿空缺，所以窗口內的值不需要連續。之後就是在排序去重的值上做同向雙指標，和難題 3 一樣，排序是讓指標單調的前提。這題和第 6 章的 sliding window 很接近，差別在於窗口是「值域」而不是「索引」，而且不需要頻率表。面試時先說清楚「保留數 = 窗口內不同值的個數」與「窗口可以從某個原始值開始」兩個論證，再寫十行的雙指標，並主動提醒窗口長度要用原始的 n。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 相向：排序陣列的配對 | 排序（或可排序）陣列中找和、差、最接近的數對 | 和太小移 lo、太大移 hi；計數時一次加 `hi − lo` | 核心題 1（167）、1 Two Sum 的排序版、2563、16 |
| 相向：固定一個再配對（kSum） | 三個或更多數的組合，要去重或計數 | 排序後固定外層，內層兩數和；去重跳過相同值，計數時整段處理 | 核心題 2（15）、難題 3（923）、18、259 |
| 相向：較短邊決定瓶頸 | 答案由兩端位置與「較小值」決定 | 移動較矮的一側，因為它已經被完整評估 | 核心題 3（11）、難題 1（42） |
| 相向：兩端是極值 | 排序陣列經過凸函數或絕對值轉換 | 從兩端取較大者、從結果尾端往前填 | 核心題 5（977）、360、658 |
| 同向：讀寫壓縮 | 原地移除、去重、保留至多 k 個，要維持順序 | `write <= read`，條件看已寫入的結果 | 26、27、80、283 |
| 分區（多指標） | 原地把元素分成兩類或三類 | 四區 invariant；和右端交換後 i 不動 | 核心題 4（75）、quicksort 三路分區、905、922 |
| 快慢指標 | 鏈結串列或函數圖 i → f(i) 上的環、中點 | 速度差 1 必在環上相遇；第二階段同速找入口 | 難題 2（287）、141／142、876、202 Happy Number |
| 同向：值域窗口 | 排序後找「值域長度固定」的區間最多包含幾個元素 | 左端右移時右端只會右移 | 難題 5（2009）、1838、2779 |
| 中心擴張 | 答案必須包含某個固定點，或以每個位置為中心 | 每次往較有利的一側擴，證明會經過每個門檻的最大區間 | 難題 4（1793）、5 與 647 回文（第 25 章） |
| 兩個序列各一個指標 | 合併兩個排序序列、找交集、子序列匹配 | 每次推進值較小（或已匹配）的那一個 | 88 Merge Sorted Array、392 Is Subsequence、986（第 9 章核心題 4） |

**下限與上限**。最簡單的形式是「排序陣列 + 相向指標找一對」（167），或「讀寫指標原地移除」（27、283），考的只是迴圈寫對、邊界不重複使用元素。中間層是 3Sum（15）與 Sort Colors（75），難點轉移到去重的細節與多個指標的 invariant。上限的題目難在三個地方：第一，**排除理由不是排序**，必須從目標函數本身找出「哪一端已經被完整評估」，例如 11 的較短邊、42 的較小最大值、1793 的「往較大的一側擴」；第二，**指標的意義需要先轉換問題才看得到**，例如 287 把陣列看成函數圖、2009 把最少替換轉成值域窗口內的最多保留；第三，**相等時的處理**，計數題（923）必須把重複段整段計算，否則相向指標的排除論證會漏算。

**與其他 pattern 的關係**。Two pointers 和 binary search（第 8 章）常是同一題的兩種解法：167 可以對每個元素 bisect（O(n log n)），雙指標更好（O(n)）；反過來，第 8 章難題 4（719）在二分答案時用雙指標做計數。和 sliding window（第 6 章）的界線是：sliding window 是同向雙指標加上窗口內的狀態（頻率表、和、不同元素數），而本章的同向題目只需要比較兩端的值。和 hash（第 4 章）的取捨是空間：未排序的 Two Sum 用 hash O(n)／O(n)，排序後用雙指標 O(n log n)／O(1)。和 monotonic stack（第 10 章）的關係最微妙：42 與 1793 都同時有雙指標解與 stack 解，雙指標通常是 O(1) 空間，但只適用於「從兩端」或「從固定點」出發的問題；沒有固定點時（84）只能用 stack。快慢指標則是第 11 章鏈結串列的核心工具，本章的 287 是它在陣列上的延伸。

**容易混淆之處**。第一，「排序陣列」不代表一定用雙指標：只要找一個值或邊界，binary search 是 O(log n)，雙指標的 O(n) 反而較慢。第二，「兩端往中間收縮」要有排除理由：11 可以、84 不行，差別在於目標是由「兩端的較小值」還是「整段的最小值」決定。第三，計數題與列舉題的去重方向相反：15 要跳過重複，923 要整段計入，259 則完全不需要處理重複。第四，快慢指標的起點必須不在環上：287 用索引 0 是因為沒有值指向它，換成別的起點就可能找到錯的入口。

## 本章重點整理

- Two pointers 的本質是排除論證：每移動一次指標，都要能說出「被跳過的候選為什麼不可能是答案」；說得出來，複雜度就是總移動距離 O(n)。
- 三個骨架：相向（從兩端往內）、同向讀寫或快慢（都往右走）、分區（多個邊界指標維護區域 invariant）；每題都是其中之一加上題目特有的排除規則。
- 相向指標的正確性可以用「和表」說明：和太小丟掉一整列、太大丟掉一整行，剩下的範圍永遠包含答案。
- kSum 的標準做法是排序後固定外層、內層兩數和；列舉要跳過重複（15），計數要整段計算重複段（923），不等式計數一次加 `hi − lo`（259）。
- 「較短邊決定瓶頸」時移動較矮的一側：11 是因為它配任何更近的線都不會更好，42 是因為較小的最大值已經決定了水位。
- 三路分區（75）的四區 invariant：和左端交換後兩個指標都前進，和右端交換後 i 不動，因為換過來的元素還沒檢查過。
- 排序陣列經過平方、絕對值或開口向上的二次函數後，最大值在兩端，從兩端取並從結果尾端往前填（977、360）。
- 讀寫指標去重時要比較已寫入的結果 `nums[write − k]`，而不是原陣列的位置。
- Floyd 判環：快慢指標在環上相遇後，一個回到起點、兩者同速前進，相遇點就是環的入口；287 中入口有兩個前驅，所以它就是重複值。
- 必須包含固定點 k 的「最小值 × 長度」問題，從 k 往較大的一側擴張，會經過每個最小值門檻下的最長區間（1793）；沒有 k 時改用 monotonic stack（84）。
- 「最少替換」常可轉成「最多保留」：2009 中保留的值只要互不相同並落在長度為 n 的值域窗口內，排序去重後用同向雙指標。
- 面試時先講暴力解與 hash 或二分的中間解，再提出雙指標，並主動說出排除理由與邊界（`lo < hi` 不重複使用元素、相等時怎麼處理、溢位）。
