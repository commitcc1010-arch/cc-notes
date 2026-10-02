---
chapter: 21
title: DP：一維與狀態機
part: 5
---

# 第 21 章　DP：一維與狀態機

> [!abstract] 本章地圖
> **一句話**：把「暴力遞迴裡重複出現的子問題」用一個狀態命名、記下答案，再依照依賴順序填表；一維 DP 的狀態是「前 i 個元素」或「數值 v」，狀態機 DP 再加上「此刻處在哪一種情況」。
>
> **辨識訊號**：
> - 問「最大／最小／最長／有幾種方法／能不能做到」，而且每一步的選擇會影響之後能做的選擇
> - 試過貪婪卻找得到反例（硬幣 `[1, 3, 4]` 湊 6、不能相鄰的搶劫）
> - 暴力遞迴的參數只有一兩個整數，遞迴樹裡同一組參數出現很多次
> - 規則裡有「冷卻」「最多 k 次」「持有／未持有」這類**模式切換**，就畫狀態機
> - n 在 10³–10⁴ 時 O(n²) 可接受；n 到 10⁵ 時要找 O(n log n) 的轉移（排序加 binary search、patience sorting）
> - 計數題要求答案對 10⁹ + 7 取模，幾乎一定是 DP
>
> **核心題**：198、322、300、139、91
>
> **難題**：188、354、403、1235、1335

## 21.1 這個 Pattern 解決什麼問題

先看一個最小的例子：爬一座 n 階的樓梯，每次可以爬 1 階或 2 階，有幾種不同的爬法？最直接的想法是遞迴：最後一步不是從第 n − 1 階跨 1 階上來，就是從第 n − 2 階跨 2 階上來，這兩類爬法互不重疊、合起來就是全部，所以 `f(n) = f(n − 1) + f(n − 2)`，而 `f(0) = f(1) = 1`。這個式子完全正確，但直接寫成遞迴非常慢：算 `f(5)` 要呼叫 15 次函式，算 `f(20)` 要 21891 次，算 `f(40)` 要超過 3 × 10⁸ 次，呼叫次數本身就以費波那契數的速度成長。

慢的原因畫出遞迴樹就一目了然：`f(3)` 被算了兩次，`f(2)` 被算了三次，越小的子問題被重複算越多次。可是不同的子問題其實只有 `f(0)` 到 `f(n)` 共 n + 1 個，每個的答案都是固定的，與「是誰呼叫它」無關。只要第一次算出來就記下來，之後直接查表，總工作量就從指數降到 O(n)。這就是 dynamic programming（動態規劃，簡稱 DP）的全部核心：**子問題會重複（overlapping subproblems），而且大問題的答案可以由小問題的答案組合出來（optimal substructure）**，於是每個子問題只算一次。

```text
f(5) 的遞迴樹：15 次呼叫，只有 6 個不同的子問題
                        f(5)
                 ┌───────┴────────┐
               f(4)              f(3)  ← 第 2 次算 f(3)
            ┌───┴────┐          ┌─┴──┐
          f(3)      f(2)      f(2)  f(1)
         ┌─┴──┐    ┌─┴─┐     ┌─┴─┐
       f(2)  f(1) f(1) f(0) f(1) f(0)
      ┌─┴─┐
    f(1) f(0)

記下答案之後（memoization）：每個子問題只展開一次
f(5) → f(4) → f(3) → f(2) → f(1)、f(0)
              ↑ 之後再遇到 f(3)、f(2) 直接查表
```

```python
from functools import cache

calls = 0


def climb_naive(n: int) -> int:
    global calls
    calls += 1
    if n <= 1:
        return 1
    return climb_naive(n - 1) + climb_naive(n - 2)


@cache
def climb_memo(n: int) -> int:
    if n <= 1:
        return 1
    return climb_memo(n - 1) + climb_memo(n - 2)


assert climb_naive(5) == 8 and calls == 15
calls = 0
assert climb_naive(20) == 10946 and calls == 21891   # 呼叫次數 = 2·f(n) − 1，指數成長
assert climb_memo(90) == 4660046610375530309         # 記憶化後 n = 90 也瞬間完成
assert climb_memo(0) == 1 and climb_memo(1) == 1
print("all tests passed")
```

這個例子也說明了 DP 和 backtracking（回溯，第 19 章）的分界。兩者都從「列舉所有選擇」的遞迴出發；backtracking 要的是**所有解本身**，每條路徑都不同，沒有東西可以共用；DP 要的是所有解的**彙總值**（最大、最小、個數、存在與否），而彙總值只依賴少數幾個參數，所以可以共用。面試時看到「最多／最少／幾種」而不是「列出全部」，就應該先問自己：如果把遞迴寫出來，它的參數有幾種組合？如果組合數是多項式級的，DP 就能把指數時間壓成多項式時間。

## 21.2 辨識訊號

| 題目特徵 | 為什麼是 DP | 本章哪一題 |
|---|---|---|
| 沿著陣列做「選或不選」，選了會限制鄰近的選擇 | 未來只需要知道「前面最好能拿多少」，不需要知道具體選了誰 | 核心題 1（198） |
| 湊出某個數值的最少件數或方法數，物品可重複用 | 子問題只由「剩下的數值」決定，數值範圍不大 | 核心題 2（322） |
| 最長的「遞增」「可串接」子序列 | 以第 i 個元素結尾的最佳值，只依賴它前面能接上的元素 | 核心題 3（300）、難題 2（354） |
| 字串能否切成合法片段、有幾種切法 | 「前 i 個字元能否切好」只依賴更短的前綴 | 核心題 4（139）、核心題 5（91） |
| 規則有模式切換：持有／未持有、冷卻、剩幾次交易 | 每一天的「狀態」是有限幾種，畫成狀態機，每條邊是一種動作 | 難題 1（188）、21.6 節 |
| 位置本身不夠，還要知道「上一步怎麼來的」 | 把上一步的資訊（上次跳多遠）放進狀態 | 難題 3（403） |
| 帶權重的區間挑選、不能重疊 | 依結束時間排序後，「選這個」接上的是 binary search 找到的前驅 | 難題 4（1235） |
| 依序切成恰好 d 段，最小化每段代價的總和 | 狀態多一維「已經用了幾段」，轉移枚舉最後一段的起點 | 難題 5（1335） |
| 貪婪找得到反例 | 局部最佳不保證全域最佳，必須考慮所有選擇再取最好 | 322 的 `[1, 3, 4]` 湊 6、198 的 `[2, 1, 1, 2]` |

一個實用的反向檢查：如果題目要你**輸出所有方案**（所有切法、所有組合），答案本身就可能是指數大小，DP 最多只能幫你剪枝，主體仍然是 backtracking；如果貪婪有簡單的交換論證（第 20 章），就不需要 DP。另一個反向訊號是狀態裡必須記住「已經用過哪些元素」：那是 bitmask DP（第 24 章），只有 n ≤ 20 左右才可行。

## 21.3 DP 的四個要素：狀態、轉移、base case、計算順序

每一個 DP 解法都要回答四個問題，面試時最好按這個順序說出口。這裡用 746. Min Cost Climbing Stairs 當例子：樓梯有 n 階，踏上第 i 階要付 `cost[i]`；你可以從第 0 或第 1 階出發，每次爬 1 或 2 階，目標是走到第 n 階（樓頂，不用付錢），求最小花費。例如 `cost = [10, 15, 20]` 時答案是 15（從第 1 階出發，付 15 後一次爬 2 階到樓頂）。

**一、狀態（state）**：用一句中文說清楚 `dp[i]` 代表什麼，而且這句話要精確到「包含哪些、不包含哪些」。這裡定義 `dp[i]` = 「走到第 i 階、但還沒付第 i 階費用時，最少已經花了多少」。這句話決定了一切：答案就是 `dp[n]`；而且第 i 階的費用不算在 `dp[i]` 裡，是離開它時才付。若狀態的定義含糊（「到第 i 階的花費」到底含不含 `cost[i]`？），轉移式一定會寫錯，這是 DP 最常見的錯誤來源。

**二、轉移（transition）**：問「到達這個狀態的**最後一步**是什麼？」。走到第 i 階，最後一步要嘛是從 i − 1 跨 1 階（離開 i − 1 時付了 `cost[i − 1]`），要嘛是從 i − 2 跨 2 階。所有到達 i 的走法恰好分成這兩類，各自的最佳值是 `dp[i − 1] + cost[i − 1]` 與 `dp[i − 2] + cost[i − 2]`，所以 `dp[i]` 取兩者的最小值。「最後一步」的分類必須**完整**（不漏掉任何走法）而且對最佳化題來說可以重疊，對計數題來說必須**互斥**（不重複計數）。

**三、base case（初始值）**：最小、不能再用轉移拆解的狀態。這裡 `dp[0] = dp[1] = 0`，因為可以直接從第 0 或第 1 階出發，到達它們不必付任何錢。base case 常見的陷阱是「空的情況」：空字串能不能切（139 題的 `dp[0] = True`）、湊出 0 元要幾枚硬幣（322 題的 `dp[0] = 0`）、空字串有幾種解碼（91 題的 `dp[0] = 1`）。這些值不是隨便選的，而是讓轉移式在最小的情況也成立的唯一選擇。

**四、計算順序（order）**：每個狀態都必須在它依賴的狀態之後計算。`dp[i]` 依賴 `dp[i − 1]` 和 `dp[i − 2]`，所以 i 由小到大即可。更一般地說，把每個狀態畫成一個點、依賴關係畫成箭頭，就得到一張有向無環圖（DAG）；計算順序就是這張圖的拓撲順序（第 16 章）。如果依賴關係出現環（A 依賴 B、B 又依賴 A），就不能直接 DP，要改變狀態定義，或改用最短路演算法（第 18 章）。

```text
cost = [1, 100, 1, 1, 1, 100, 1, 1, 100, 1]，n = 10
dp[i] = min(dp[i-1] + cost[i-1], dp[i-2] + cost[i-2])

i      :  0   1    2    3    4    5    6    7    8    9   10
cost   :  1  100   1    1    1   100   1    1   100   1    -
dp     :  0   0    1    2    2    3    3    4    4    5    6
來自   :  -   -   i-2  i-1  i-2  i-1  i-2  i-1  i-2  i-2  i-1

逐格填寫（每格只看左邊兩格）：
dp[2] = min(dp[1]+100, dp[0]+1) = min(100, 1) = 1
dp[3] = min(dp[2]+1,   dp[1]+100) = min(2, 100) = 2
dp[4] = min(dp[3]+1,   dp[2]+1)   = min(3, 2)   = 2
dp[5] = min(dp[4]+1,   dp[3]+1)   = min(3, 3)   = 3
dp[6] = min(dp[5]+100, dp[4]+1)   = min(103, 3) = 3
 …
dp[10] = min(dp[9]+1,  dp[8]+100) = min(6, 104) = 6

依賴圖（DAG）：每個點只有來自左邊兩格的箭頭，所以由左往右填
 0 ──▶ 1 ──▶ 2 ──▶ 3 ──▶ … ──▶ 10
 └─────────▶┘└─────────▶┘
```

「來自」那一列記錄了每格取的是哪一個選擇，從 `dp[10]` 沿著它往回走（10 ← 9 ← 7 ← 6 ← 4 ← 2 ← 0）就能還原最佳路線：從第 0 階出發，依序踏 0、2、4、6、7、9，付了六個 1。這就是 21.7 節要講的「還原最佳解」。

## 21.4 從暴力遞迴推出 DP：四個版本

面試時很少有人能直接寫出 bottom-up 的表格。比較可靠的路線是從暴力遞迴出發，一步一步改寫，每一步都保證正確：

1. **寫出暴力遞迴**：定義一個函式，參數描述「剩下的問題」，回傳值是這個剩下問題的答案。關鍵要求是**函式必須是純函式**：回傳值只依賴參數，不依賴全域變數或一路累積的「路徑」。如果你的 backtracking 把目前總和放在參數裡往下傳、在葉子更新全域最佳值，那它不能直接記憶化；要改寫成「回傳從這裡開始的最佳值」，讓子問題的答案和「怎麼走到這裡」無關。
2. **加上記憶化（memoization，top-down）**：用 `functools.cache` 或一個 dict 記住每組參數的答案。此時狀態就是函式的參數，狀態數 × 每個狀態的轉移成本 = 時間複雜度。
3. **改成 bottom-up 填表（tabulation）**：把參數變成陣列索引，找出計算順序，用迴圈從 base case 往上填。這一步消除了遞迴深度限制，也讓下一步成為可能。
4. **空間壓縮**：如果 `dp[i]` 只依賴固定幾個前面的格子，只保留那幾格。一維 DP 常常可以從 O(n) 壓到 O(1)。

```python
import random
from functools import cache


def min_cost_brute(cost: list[int]) -> int:
    """版本 1：暴力遞迴。go(i) = 從第 i 階（尚未付費）走到樓頂的最小花費。"""
    n = len(cost)

    def go(i: int) -> int:
        if i >= n:
            return 0
        return cost[i] + min(go(i + 1), go(i + 2))

    return min(go(0), go(1))


def min_cost_memo(cost: list[int]) -> int:
    """版本 2：同一個遞迴加上 cache，O(n) 個狀態、每個 O(1)。"""
    n = len(cost)

    @cache
    def go(i: int) -> int:
        if i >= n:
            return 0
        return cost[i] + min(go(i + 1), go(i + 2))

    return min(go(0), go(1))


def min_cost_table(cost: list[int]) -> int:
    """版本 3：bottom-up。dp[i] = 走到第 i 階（尚未付費）的最小花費。"""
    n = len(cost)
    dp = [0] * (n + 1)
    for i in range(2, n + 1):
        dp[i] = min(dp[i - 1] + cost[i - 1], dp[i - 2] + cost[i - 2])
    return dp[n]


def min_cost_rolling(cost: list[int]) -> int:
    """版本 4：dp[i] 只依賴前兩格，用兩個變數滾動，O(1) 空間。"""
    prev2 = prev1 = 0                       # dp[i-2]、dp[i-1]
    for i in range(2, len(cost) + 1):
        prev2, prev1 = prev1, min(prev1 + cost[i - 1], prev2 + cost[i - 2])
    return prev1


for f in (min_cost_brute, min_cost_memo, min_cost_table, min_cost_rolling):
    assert f([10, 15, 20]) == 15
    assert f([1, 100, 1, 1, 1, 100, 1, 1, 100, 1]) == 6
    assert f([5, 7]) == 5                   # 兩階：直接從第 0 階跨 2 階
    assert f([0, 0, 0, 0]) == 0
for _ in range(300):
    c = [random.randint(0, 20) for _ in range(random.randint(2, 12))]
    assert min_cost_brute(c) == min_cost_memo(c) == min_cost_table(c) == min_cost_rolling(c)
print("all tests passed")
```

注意版本 1、2 的狀態定義和版本 3、4 是**相反方向**的：遞迴版的 `go(i)` 是「從 i 走到終點」（後綴），表格版的 `dp[i]` 是「從起點走到 i」（前綴）。兩種都對，選哪一種看哪個比較自然：遞迴時「從這裡出發還要多少」最好想；填表時「走到這裡最少要多少」最好填。重要的是每一種都要把定義寫在註解裡，不要在同一份程式裡混用。

**top-down 與 bottom-up 怎麼選**。top-down 的好處是寫起來直接（從暴力遞迴加一行 `@cache`），而且只會計算真正被走到的狀態，狀態稀疏時（難題 3 的青蛙過河）特別划算。壞處是 Python 的遞迴深度預設只有 1000 左右，n = 10⁴ 的線性遞迴就會 `RecursionError`；可以用 `sys.setrecursionlimit` 調高，但深度太大時仍可能讓直譯器崩潰，面試時要主動說出這個風險。bottom-up 沒有深度問題、常數較小，也才能做空間壓縮；代價是必須自己想清楚計算順序。實務上的建議是：**用 top-down 想清楚狀態與轉移，用 bottom-up 寫最終版本**，如果時間不夠，top-down 加 `@cache` 也是完全合格的答案。

**狀態要放什麼**。設計狀態時問一個問題：「站在這個位置做下一個決定時，**未來需要知道過去的什麼**？」只把這些資訊放進狀態，其他的全部丟掉。爬樓梯只需要知道站在第幾階；不能相鄰的搶劫（核心題 1）需要知道「上一間有沒有搶」，可以放進狀態，也可以靠「前 i 間的最佳值」的定義隱含處理；股票題需要知道「手上有沒有股票、還剩幾次交易」；青蛙過河需要知道「上一跳多遠」。狀態放少了，轉移時缺資訊、答案錯；放多了，狀態數爆炸、超時。DP 題的難度幾乎全部集中在這一步。

## 21.5 一維 DP 的模板

一維 DP 雖然千變萬化，轉移的「形狀」只有幾種。看到題目先判斷屬於哪一種，就知道複雜度大概是多少、要往哪個方向優化。

| 形狀 | 轉移 | 複雜度 | 例子 |
|---|---|---|---|
| A. 常數個前驅 | `dp[i]` 由 `dp[i−1]`、`dp[i−2]` 等固定幾格決定 | O(n) 時間、O(1) 空間 | 70、746、198、91 |
| B. 枚舉所有前驅 | `dp[i] = best(dp[j] ⊕ w(j, i))`，j 走遍 i 之前所有位置 | O(n²)，常可用二分或長度上限加速 | 300、139、1335 |
| C. 以數值為狀態 | `dp[v]` 由 `dp[v − c]`（c 是每種物品）決定 | O(V · m)，V 是數值上限 | 322、279、377 |
| D. 排序後二分找前驅 | 先排序，`dp[i] = max(dp[i−1], w_i + dp[p(i)])`，p(i) 用 binary search | O(n log n) | 1235、1751、2008 |
| E. 狀態機 | 每個位置有 s 種狀態，`dp[i][state]` 由 `dp[i−1][*]` 決定 | O(n · s) 時間、O(s) 空間 | 188、309、714、198 |
| F. 分段 | 多一維「用了幾段」，`dp[k][i] = best(dp[k−1][j] + cost(j, i))` | O(k · n²)，常可用 monotonic stack 加速 | 1335、410、813 |

下面四段模板對應 A–D，E 在 21.6 節，F 在難題 5。每段都刻意寫成「先寫定義註解、再寫 base case、再寫迴圈」的順序，面試時照這個順序寫，幾乎不會漏掉東西。

```python
import bisect


def shape_a_climb(n: int) -> int:
    """A. 常數個前驅：爬 n 階、每次 1 或 2 階的方法數。dp[i] = dp[i-1] + dp[i-2]。"""
    a, b = 1, 1                              # dp[0]、dp[1]
    for _ in range(n - 1):
        a, b = b, a + b
    return b if n >= 1 else 1


def shape_b_longest_chain(nums: list[int]) -> int:
    """B. 枚舉所有前驅：最長的子序列，使後一個能被前一個整除（368 的長度版）。
    dp[i] = 排序後以 nums[i] 結尾的最長鏈長。"""
    nums = sorted(nums)
    dp = [1] * len(nums)
    for i in range(len(nums)):
        for j in range(i):
            if nums[i] % nums[j] == 0:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp, default=0)


def shape_c_perfect_squares(n: int) -> int:
    """C. 以數值為狀態：n 最少能寫成幾個完全平方數的和（279）。
    dp[v] = 湊出 v 的最少平方數個數。"""
    squares = [k * k for k in range(1, int(n ** 0.5) + 1)]
    dp = [0] + [n] * n                       # 最差就是 n 個 1
    for v in range(1, n + 1):
        for s in squares:
            if s > v:
                break
            dp[v] = min(dp[v], dp[v - s] + 1)
    return dp[n]


def shape_d_weighted_intervals(intervals: list[tuple[int, int, int]]) -> int:
    """D. 排序後二分找前驅：(start, end, weight) 不重疊的最大權重和（end 可以接 start）。
    dp[i] = 只考慮依結束時間排序後的前 i 個區間的最佳值。"""
    intervals = sorted(intervals, key=lambda t: t[1])
    ends = [e for _, e, _ in intervals]
    dp = [0] * (len(intervals) + 1)
    for i, (s, e, w) in enumerate(intervals, 1):
        p = bisect.bisect_right(ends, s)     # 結束時間 <= s 的區間個數
        dp[i] = max(dp[i - 1], dp[p] + w)
    return dp[-1]


assert [shape_a_climb(n) for n in range(6)] == [1, 1, 2, 3, 5, 8]
assert shape_b_longest_chain([1, 2, 3, 4, 8]) == 4          # 1 → 2 → 4 → 8
assert shape_b_longest_chain([]) == 0
assert shape_c_perfect_squares(12) == 3                     # 4 + 4 + 4
assert shape_c_perfect_squares(13) == 2                     # 4 + 9
assert shape_c_perfect_squares(1) == 1
assert shape_d_weighted_intervals([(1, 3, 5), (2, 5, 6), (4, 6, 5), (6, 7, 4)]) == 14
assert shape_d_weighted_intervals([]) == 0
print("all tests passed")
```

形狀 B 是最容易超時的一種：n = 10⁴ 時 O(n²) 是 10⁸，在 Python 中會超時。看到它要立刻想三種加速：**長度上限**（139 題的字典單字最長 20，j 只需要看 i 前面 20 格）、**單調性讓前驅可以二分**（300 題的 patience sorting）、**單調結構維護候選**（1335 題的 monotonic stack）。形狀 C 的複雜度和**數值大小**有關，屬於 pseudo-polynomial（偽多項式）：amount = 10⁴ 沒問題，amount = 10⁹ 就不行，這時要換想法（核心題 2 的 F4）。

## 21.6 狀態機 DP：股票類的畫法

有一類題目，每一步可以做的動作取決於「目前處在什麼情況」：手上有股票才能賣、剛賣完要冷卻一天才能買、交易次數用完就不能再買。這種題目最好的方法是**先畫狀態機，再把圖翻譯成程式**，而不是直接想 `dp` 陣列。步驟如下：

1. **列出狀態**：每一天結束時，你可能處在哪幾種情況？每一種情況要能完全決定「明天可以做什麼」。
2. **畫出邊**：每一種動作（買、賣、休息）是一條從「昨天的狀態」到「今天的狀態」的箭頭，箭頭上標它對收益的影響（買是 −price、賣是 +price、休息是 0）。
3. **翻譯成轉移**：今天某個狀態的值 = 所有指向它的箭頭中，「昨天起點狀態的值 + 箭頭權重」的最大值。有幾個箭頭指向它，max 裡就有幾項。
4. **初始值與答案**：第一天之前，只有「空手」狀態是可達的（值為 0），其他狀態設成 −∞；答案是最後一天所有「合法結束」狀態的最大值。

以 309. Best Time to Buy and Sell Stock with Cooldown 為例：可以交易任意多次，但賣出後的隔天不能買。每天結束時有三種情況：`hold`（手上有股票）、`sold`（今天剛賣，所以明天必須休息）、`rest`（空手且明天可以買）。

```text
309 的狀態機（每條邊代表「一天」）

        休息 (+0)                     休息 (+0)
        ┌─────┐                       ┌─────┐
        │     ▼                       │     ▼
      ┌──────────┐    買 (−p)       ┌──────────┐
 ┌──▶ │   rest   │ ───────────────▶ │   hold   │
 │    └──────────┘                  └──────────┘
 │                                       │
 │ 冷卻一天 (+0)                          │ 賣 (+p)
 │    ┌──────────┐                       │
 └─── │   sold   │ ◀─────────────────────┘
      └──────────┘

翻譯成轉移（箭頭指向誰，就寫進誰的 max）：
hold[i] = max(hold[i-1],        rest[i-1] - p)   ← 「休息」與「買」兩條邊指向 hold
sold[i] = hold[i-1] + p                          ← 只有「賣」指向 sold
rest[i] = max(rest[i-1],        sold[i-1])       ← 「休息」與「冷卻」指向 rest

prices = [1, 2, 3, 0, 2]，初始 hold = −∞、sold = −∞、rest = 0
day  p   hold                 sold            rest
 0   1   max(−∞, 0−1)  = −1   −∞+1 = −∞       max(0, −∞) = 0
 1   2   max(−1, 0−2)  = −1   −1+2 = 1        max(0, −∞) = 0
 2   3   max(−1, 0−3)  = −1   −1+3 = 2        max(0, 1)  = 1
 3   0   max(−1, 1−0)  = 1    −1+0 = −1       max(1, 2)  = 2
 4   2   max(1, 2−2)   = 1    1+2  = 3        max(2, −1) = 2
答案 = max(sold, rest) = 3    （第 0 天買、第 1 天賣、第 2 天冷卻、第 3 天買、第 4 天賣）
```

第 3 天是關鍵：`hold` 從 −1 變成 1，因為「第 2 天的 rest = 1」（第 1 天賣出賺 1、第 2 天冷卻完）可以在價格 0 時買進。如果沒有冷卻規則，第 2 天的 `sold = 2` 也能在第 3 天直接買，答案會變成 4；狀態機把「剛賣完不能買」這條規則變成「`sold` 沒有直接指向 `hold` 的箭頭」，完全不需要額外的 if。

**同一張圖，換幾條邊就是另一題**。121 題（只能交易一次）是 `rest → hold → done` 一條單行道；122 題（不限次數、無冷卻）只需要 `hold` 與 `free` 兩個狀態互相指；714 題（每筆交易有手續費）是在「賣」的邊上多扣 fee；123 與 188 題（最多 k 次交易）是把狀態展開成 `hold₁, sold₁, hold₂, sold₂, …`，第 j 次買只能從 `sold_{j−1}` 出發（難題 1）。核心題 1 的 House Robber 也能畫成兩個狀態：`robbed`（這間搶了）只能從 `skipped` 走過來，`skipped` 可以從任何狀態走過來。

```python
import random
from itertools import product


def max_profit_cooldown(prices: list[int]) -> int:
    """309：狀態機 hold／sold／rest。"""
    hold, sold, rest = float("-inf"), float("-inf"), 0
    for p in prices:
        hold, sold, rest = max(hold, rest - p), hold + p, max(rest, sold)   # 同時更新
    return max(sold, rest)


def max_profit_fee(prices: list[int], fee: int) -> int:
    """714：狀態機 hold／free，賣出時扣手續費。"""
    hold, free = float("-inf"), 0
    for p in prices:
        hold, free = max(hold, free - p), max(free, hold + p - fee)
    return free


def brute_cooldown(prices):
    """把每天的動作（0 休息、1 買、2 賣）全部列舉，檢查合法性。"""
    best = 0
    for acts in product(range(3), repeat=len(prices)):
        holding, cool, profit, ok = False, False, 0, True
        for a, p in zip(acts, prices):
            if a == 1:
                if holding or cool:
                    ok = False
                    break
                holding, profit = True, profit - p
                cool = False
            elif a == 2:
                if not holding:
                    ok = False
                    break
                holding, profit, cool = False, profit + p, True
            else:
                cool = False
        if ok and not holding:
            best = max(best, profit)
    return best


assert max_profit_cooldown([1, 2, 3, 0, 2]) == 3
assert max_profit_cooldown([1]) == 0
assert max_profit_cooldown([5, 4, 3]) == 0                  # 一路下跌，不交易
assert max_profit_fee([1, 3, 2, 8, 4, 9], 2) == 8
assert max_profit_fee([1, 3, 7, 5, 10, 3], 3) == 6
for _ in range(200):
    pr = [random.randint(0, 9) for _ in range(random.randint(1, 7))]
    assert max_profit_cooldown(pr) == brute_cooldown(pr)
print("all tests passed")
```

**兩個實作細節**。第一，**同一天的所有狀態要用昨天的值同時更新**。Python 的多重賦值 `hold, sold, rest = …` 會先算完右邊再一起賦值，剛好就是「同時更新」；如果分成三行寫，`sold = hold + p` 用到的就是今天剛更新過的 `hold`，等於允許同一天買又賣，在冷卻題會算出錯的答案。第二，**不可達的狀態用 −∞，不要用 0**。第一天之前不可能持有股票，若把 `hold` 初始化成 0，就等於免費送你一張股票，第一天就能「賣出」憑空賺錢。

## 21.7 還原最佳解、計數與最佳化的差別

**還原最佳解**。DP 表只存「最佳值」，不存「怎麼做到的」。要還原方案有兩種做法：一是在填表時另外記錄每格取了哪個選擇（parent／choice 陣列），最後從答案格子沿著記錄往回走；二是不另外記錄，從答案格子開始，逐一檢查哪一個轉移的值剛好等於這一格的值，往那個前驅走。第二種不用額外空間，但每一步要重算轉移；如果已經做了空間壓縮，表格只剩最後幾格，就無法回溯，必須保留完整的表或 choice 陣列。面試官常在你寫完最佳值之後問「那要輸出方案呢？」，先說清楚「需要保留 O(n) 的表或 choice 陣列」，再寫回溯迴圈。

**計數、最佳化、存在性用同一張表，運算不同**。最佳化題的轉移用 `min`／`max`，「最後一步」的分類可以重疊（重複考慮同一個方案沒關係）；計數題用 `+`，分類必須**互斥且完整**，否則會重複計數；存在性題用 `or`（`any`）。計數題最常見的陷阱是「組合」與「排列」的混淆：用硬幣湊出 amount 的方法數，如果 `[1, 2]` 和 `[2, 1]` 算同一種（518 題，第 23 章核心題 3），外層迴圈要跑硬幣、內層跑數值，強迫硬幣按固定順序出現；如果算不同種（377 題），外層跑數值、內層跑硬幣，每個數值的最後一枚可以是任何硬幣。

```python
def ways_combinations(coins: list[int], amount: int) -> int:
    """518：硬幣的多重集合相同就算同一種。外層硬幣、內層數值。"""
    dp = [1] + [0] * amount
    for c in coins:
        for v in range(c, amount + 1):
            dp[v] += dp[v - c]
    return dp[amount]


def ways_permutations(coins: list[int], amount: int) -> int:
    """377：順序不同算不同種。外層數值、內層硬幣（最後一枚是哪一枚）。"""
    dp = [1] + [0] * amount
    for v in range(1, amount + 1):
        for c in coins:
            if c <= v:
                dp[v] += dp[v - c]
    return dp[amount]


def min_cost_path(cost: list[int]) -> list[int]:
    """746 的還原：回傳踏過的階梯編號。"""
    n = len(cost)
    dp, came = [0] * (n + 1), [-1] * (n + 1)
    for i in range(2, n + 1):
        a, b = dp[i - 1] + cost[i - 1], dp[i - 2] + cost[i - 2]
        dp[i], came[i] = (a, i - 1) if a <= b else (b, i - 2)
    path, i = [], came[n]
    while i >= 0:
        path.append(i)
        i = came[i]
    return path[::-1]


assert ways_combinations([1, 2, 5], 5) == 4      # 5、2+2+1、2+1+1+1、1×5
assert ways_permutations([1, 2, 3], 4) == 7      # 1111、112、121、211、22、13、31
assert ways_combinations([2], 3) == 0 == ways_permutations([2], 3)
assert ways_combinations([7], 0) == 1            # 湊出 0 元：什麼都不拿，一種
assert min_cost_path([1, 100, 1, 1, 1, 100, 1, 1, 100, 1]) == [0, 2, 4, 6, 7, 9]
assert min_cost_path([10, 15, 20]) == [1]
print("all tests passed")
```

**取模**。計數題的答案常大到要對 10⁹ + 7 取模。Python 的整數不會溢位，可以最後再取模，但數字變很大時加法會變慢；習慣上在每次加法後就取模。減法之後取模要小心負數，Python 的 `%` 會回傳非負值，Java／C++ 則要寫 `((a − b) % M + M) % M`。

## 21.8 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 狀態定義含糊（含不含第 i 個、是「以 i 結尾」還是「前 i 個」） | 轉移式差一格、答案偏移 | 先用一句完整的中文寫出 `dp[i]` 的定義，寫在註解裡 |
| base case 隨便設 | 空字串、湊 0 元、第一天的狀態算錯 | 問「最小的情況，正確答案是什麼？」：`dp[0] = True`、`dp[0] = 0`、空字串的解碼數 = 1 |
| 不可達狀態初始化成 0 | 股票題第一天就能憑空賣出、湊硬幣時湊不出的數值被當成 0 枚 | 最大化用 −∞、最小化用 +∞（或一個不可能的大數），最後再判斷是否可達 |
| 狀態機分行更新 | 同一天又買又賣，冷卻題答案偏大 | 用多重賦值同時更新，或明確保存昨天的值 |
| 計數題的分類重疊 | 方法數偏大 | 每個方案恰好屬於一個「最後一步」；組合 vs 排列的迴圈順序要對 |
| 空間壓縮後的覆蓋順序錯 | 0/1 背包變成完全背包、或反過來 | 壓縮前先畫出依賴方向，決定內層迴圈正著跑還是倒著跑 |
| top-down 遞迴太深 | n = 10⁴ 時 `RecursionError` | 改寫 bottom-up，或主動說明 `sys.setrecursionlimit` 的風險 |
| 狀態少放了資訊 | 403 只記「能不能到這顆石頭」，答案錯 | 問「下一個決定需要知道過去的什麼？」，那些資訊都要進狀態 |
| 把可以貪婪的題寫成 DP（或反過來） | 超時，或在有反例的題目上用了貪婪 | 先找貪婪的反例；找不到反例也證明不了，就用 DP |
| 忘記答案不在 `dp[n]` | LIS 回傳 `dp[-1]` 而不是 `max(dp)` | 狀態是「以 i 結尾」時，答案是所有 i 的最佳值 |

## 核心題 1｜198. House Robber｜Medium

### 題目

一條街上有 n 間房子排成一列，第 i 間藏有 `nums[i]` 元（非負整數）。相鄰的兩間房子裝有連動的警報器，只要在同一晚搶了任意兩間**相鄰**的房子，警報就會響。請回傳在不觸發警報的前提下，一晚最多能搶到多少錢。限制：`1 <= n <= 100`，`0 <= nums[i] <= 400`。

- 範例 1：`nums = [1, 2, 3, 1]`，回傳 `4`（搶第 0 與第 2 間，1 + 3）。
- 範例 2：`nums = [2, 7, 9, 3, 1]`，回傳 `12`（搶第 0、2、4 間，2 + 9 + 1）。
- 範例 3（貪婪的反例）：`nums = [2, 1, 1, 2]`，回傳 `4`（搶頭尾兩間）。只搶偶數位置或只搶奇數位置都只有 3。
- 範例 4（邊界）：`nums = [5]`，回傳 `5`；`nums = [0, 0, 0]`，回傳 `0`。

### 思路

暴力解是列舉每間房子搶或不搶，共 2ⁿ 種組合，再排除有相鄰的組合，n = 100 時完全不可行。兩個常見的直覺都不對：「交錯搶（全偶數或全奇數）」在範例 3 失敗，因為最佳解可能連續跳過兩間；「每次挑剩下最大的那間」在 `[3, 4, 3]` 失敗，挑了 4 之後兩邊的 3 都不能搶，總共 4，而最佳是 3 + 3 = 6。這說明每個選擇會影響鄰居，必須同時考慮兩種可能。

把暴力遞迴寫成「從第 i 間開始往右，最多能搶多少」：`go(i) = max(go(i + 1), nums[i] + go(i + 2))`。前一項是不搶第 i 間、直接看下一間；後一項是搶第 i 間，於是第 i + 1 間不能搶、從 i + 2 繼續。這個遞迴的參數只有 i，只有 n + 1 種不同的值，但遞迴樹和 21.1 節的爬樓梯一模一樣，同一個 `go(i)` 被算了指數多次，所以加上記憶化就是 O(n)。

改成 bottom-up：定義 `dp[i]` = 「只考慮前 i 間房子（索引 0 到 i − 1）時，最多能搶多少」。看第 i − 1 間（前 i 間中的最後一間）：不搶它，答案就是 `dp[i − 1]`；搶它，則第 i − 2 間不能搶，答案是 `dp[i − 2] + nums[i − 1]`。所以 `dp[i] = max(dp[i − 1], dp[i − 2] + nums[i − 1])`，base case 是 `dp[0] = 0`（沒有房子）、`dp[1] = nums[0]`。為什麼 `dp[i − 2]` 就夠了，不需要知道「第 i − 2 間有沒有搶」？因為 `dp[i − 2]` 只用到前 i − 2 間，第 i − 2 間（索引）根本不在裡面，和第 i − 1 間也不相鄰；這正是把狀態定義成「前 i 間」而不是「以第 i 間結尾」的好處。

```text
nums = [2, 7, 9, 3, 1]
dp[i] = max(dp[i-1]（不搶第 i-1 間）, dp[i-2] + nums[i-1]（搶第 i-1 間）)

i          :   0    1    2    3    4    5
最後一間   :   -    2    7    9    3    1
dp         :   0    2    7   11   11   12

逐格填寫：
dp[1] = max(dp[0], 0 + 2)       = max(0, 2)       = 2    搶 2
dp[2] = max(dp[1], dp[0] + 7)   = max(2, 7)       = 7    搶 7（放棄 2）
dp[3] = max(dp[2], dp[1] + 9)   = max(7, 2+9=11)  = 11   搶 9，接上 dp[1] 的 2
dp[4] = max(dp[3], dp[2] + 3)   = max(11, 7+3=10) = 11   不搶 3
dp[5] = max(dp[4], dp[3] + 1)   = max(11, 11+1)   = 12   搶 1，接上 dp[3]

回溯：dp[5] ≠ dp[4] → 搶第 4 間，跳到 dp[3]
      dp[3] ≠ dp[2] → 搶第 2 間，跳到 dp[1]
      dp[1] ≠ dp[0] → 搶第 0 間
方案 = {0, 2, 4}，2 + 9 + 1 = 12
```

第 3 格是第一個「真正的取捨」：搶 9 就得放棄 7，但能接上前面的 2，總共 11 比 7 好。第 4 格選擇不搶 3，因為 7 + 3 = 10 比 11 小；第 5 格則因為 1 可以接在 11 後面而更新。每一格只看左邊兩格，所以用兩個變數滾動就夠了。

### 解法

```python
import random
from itertools import product


def rob(nums: list[int]) -> int:
    prev2, prev1 = 0, 0                     # dp[i-2]、dp[i-1]
    for x in nums:
        prev2, prev1 = prev1, max(prev1, prev2 + x)
    return prev1


def rob_state_machine(nums: list[int]) -> int:
    """同一題的狀態機寫法：robbed = 這間搶了、skipped = 這間沒搶。"""
    robbed, skipped = float("-inf"), 0
    for x in nums:
        robbed, skipped = skipped + x, max(robbed, skipped)
    return max(robbed, skipped)


def brute(nums):
    best = 0
    for pick in product((0, 1), repeat=len(nums)):
        if all(not (pick[i] and pick[i + 1]) for i in range(len(nums) - 1)):
            best = max(best, sum(x for x, p in zip(nums, pick) if p))
    return best


assert rob([1, 2, 3, 1]) == 4
assert rob([2, 7, 9, 3, 1]) == 12
assert rob([2, 1, 1, 2]) == 4
assert rob([3, 4, 3]) == 6
assert rob([5]) == 5
assert rob([0, 0, 0]) == 0
for _ in range(300):
    arr = [random.randint(0, 20) for _ in range(random.randint(1, 10))]
    assert rob(arr) == rob_state_machine(arr) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)，每間房子只做一次 max；空間 O(1)，只保留 `dp[i − 1]` 與 `dp[i − 2]`。邊界情況：n = 1 時迴圈跑一次，`prev1 = max(0, 0 + nums[0])`，正確；全為 0 時答案為 0；因為金額非負，「什麼都不搶」的 0 是合法下界，所以初始值用 0 不會出錯。若題目允許負數金額，`max` 仍然正確（負的房子永遠不會被選，因為「不搶」的選項一直都在），但狀態機寫法中 `robbed` 的初始值必須是 −∞ 而不是 0。

### Follow-up

> [!question]- F1. 如果房子排成一圈，第一間和最後一間也相鄰呢（213. House Robber II）？
> 環狀的唯一新限制是「第 0 間和第 n − 1 間不能同時搶」，所以最佳解一定屬於「不搶第 0 間」或「不搶第 n − 1 間」兩類之一（兩類可以重疊，最佳化題沒關係）。分別對 `nums[1:]` 和 `nums[:-1]` 各跑一次原本的線性版本，取較大者即可，時間 O(n)、空間 O(1)。n = 1 時兩個切片都是空的，要特判回傳 `nums[0]`。這個「把環拆成兩條鏈」的技巧在環狀 DP 中很常見，例如環狀的最大子陣列和（918 題）也是用類似的分類。

> [!question]- F2. 如果要回傳實際搶了哪些房子呢？
> 保留完整的 `dp` 陣列（O(n) 空間），從 i = n 往回走：若 `dp[i] == dp[i − 1]`，代表最佳值不需要第 i − 1 間，令 i −= 1；否則第 i − 1 間一定被搶，記下它並令 i −= 2（相鄰的第 i − 2 間不能搶）。回溯 O(n)。相等時優先「不搶」只是其中一種選法；若題目要求字典序最小的方案或搶最少間，要在相等時改變優先順序，或在 dp 裡額外存第二關鍵字（例如 `(金額, −間數)` 的 tuple）。
> ```python
> def rob_houses(nums):
>     n = len(nums)
>     dp = [0] * (n + 1)
>     for i in range(1, n + 1):
>         dp[i] = max(dp[i - 1], (dp[i - 2] if i >= 2 else 0) + nums[i - 1])
>     picked, i = [], n
>     while i > 0:
>         if dp[i] == dp[i - 1]:
>             i -= 1
>         else:
>             picked.append(i - 1)
>             i -= 2
>     return picked[::-1]          # [2, 7, 9, 3, 1] → [0, 2, 4]
> ```

> [!question]- F3. 740. Delete and Earn：選一個數 x 得到 x 分，但所有 x − 1 和 x + 1 都會被刪掉，最多得幾分？
> 選了一個 x 之後，其他所有的 x 也應該都選（它們不會再被刪掉，選了只加分），所以每個值 v 的收益是 `v × 出現次數`；而「選 v 就不能選 v − 1 和 v + 1」正是相鄰不能同時搶。若值域 V 很小，建一個長度 V + 1 的陣列 `gain[v]` 再跑 House Robber，O(n + V)；若值域很大（10⁹），把出現過的不同值排序，相鄰兩個值只有差 1 時才互相衝突，差大於 1 時前一個的最佳值可以直接接上，O(n log n)。這是面試中很典型的「把新題目轉成已知 DP」的例子。

> [!question]- F4. 如果限制改成「搶過的任意兩間之間至少要隔 k 間」呢？
> 狀態定義不變，只是「搶第 i − 1 間」時，上一間能搶的最晚是第 i − k − 2 間，所以 `dp[i] = max(dp[i − 1], dp[max(0, i − k − 1)] + nums[i − 1])`。時間 O(n)；空間可以用長度 k + 2 的環狀緩衝區保留最近幾格，O(k)。原題就是 k = 1 的特例。這個 follow-up 是在檢查你是否真的理解 `dp[i − 2]` 的來由，而不是背公式。

> [!question]- F5. 如果最多只能搶 m 間房子呢？
> 「搶了幾間」變成未來需要知道的資訊，狀態要多一維：`dp[i][j]` = 前 i 間中恰好搶 j 間的最大金額（不可達設為 −∞），`dp[i][j] = max(dp[i − 1][j], dp[i − 2][j − 1] + nums[i − 1])`，答案是 `max(dp[n][0..m])`。時間與空間 O(n · m)，空間可以壓成兩列 O(m)。若 m 與 n 都很大（10⁵），可以用「對每間的懲罰 λ 做 binary search」的 Aliens trick 把複雜度降到 O(n log V)，前提是答案對 m 是凹函數；這是進階技巧，難題 1 的 F3 會完整示範。

## 核心題 2｜322. Coin Change｜Medium

### 題目

給一組互不相同的硬幣面額 `coins` 與一個目標金額 `amount`，每種面額的硬幣有無限多枚。請回傳湊出剛好 `amount` 所需的**最少**硬幣數；如果不可能湊出，回傳 `-1`。限制：`1 <= len(coins) <= 12`，`1 <= coins[i] <= 2³¹ − 1`，`0 <= amount <= 10⁴`。

- 範例 1：`coins = [1, 2, 5]`、`amount = 11`，回傳 `3`（5 + 5 + 1）。
- 範例 2：`coins = [2]`、`amount = 3`，回傳 `-1`。
- 範例 3（貪婪的反例）：`coins = [1, 3, 4]`、`amount = 6`，回傳 `2`（3 + 3）。先拿最大的 4 會得到 4 + 1 + 1，共 3 枚。
- 範例 4（邊界）：`coins = [1]`、`amount = 0`，回傳 `0`，不需要任何硬幣。

### 思路

直覺的貪婪是「每次拿不超過剩餘金額的最大面額」，在日常的硬幣系統（1、5、10、50）上恰好正確，但範例 3 說明它一般來說是錯的：先拿 4 之後剩下的 2 只能用兩個 1。暴力遞迴則是「第一枚硬幣拿哪一種」：`f(a) = 1 + min(f(a − c) for c in coins)`，`f(0) = 0`，a < 0 不合法。這個遞迴的分支數是 m（面額數），深度最多 amount，總呼叫數是指數級。

關鍵觀察：`f(a)` 只依賴剩下的金額 a，與「之前用了哪些硬幣」無關，而 a 只有 amount + 1 種可能。所以狀態是 `dp[a]` = 「湊出金額 a 的最少硬幣數」，轉移是看**最後一枚**硬幣：若最後一枚是 c，前面就是湊出 a − c 的最佳方案，`dp[a] = min(dp[a − c] + 1)`，對所有 c ≤ a 且 `dp[a − c]` 可達取最小。base case `dp[0] = 0`；湊不出的金額設成一個不可能的大數（例如 amount + 1，因為任何可行解最多用 amount 枚 1 元），最後若 `dp[amount]` 仍是這個大數就回傳 −1。計算順序是 a 由小到大，因為 `dp[a]` 只依賴比 a 小的格子。

這題也可以看成最短路：把 0 到 amount 每個金額當成一個點，從 a 到 a + c 有一條長度 1 的邊，答案是從 0 到 amount 的最短路徑長，所以用 BFS（第 15 章）也能解，複雜度相同。BFS 的好處是找到 amount 就能提早停，壞處是要多一個 queue；DP 表的好處是一次算出所有金額的答案。這個「DP 就是 DAG 上的最短路」的觀點，對理解為什麼計算順序重要很有幫助。

```text
coins = [1, 3, 4]，amount = 6
dp[a] = min(dp[a-1], dp[a-3], dp[a-4]) + 1    （a - c < 0 的項不存在）

a      :  0   1   2   3   4   5   6
dp     :  0   1   2   1   1   2   2
最後一枚:  -   1   1   3   4   1   3

逐格填寫：
dp[1] = dp[0]+1                              = 1     (1)
dp[2] = dp[1]+1                              = 2     (1+1)
dp[3] = min(dp[2]+1, dp[0]+1)      = min(3, 1)    = 1     (3)
dp[4] = min(dp[3]+1, dp[1]+1, dp[0]+1) = min(2, 2, 1) = 1  (4)
dp[5] = min(dp[4]+1, dp[2]+1, dp[1]+1) = min(2, 3, 2) = 2  (4+1)
dp[6] = min(dp[5]+1, dp[3]+1, dp[2]+1) = min(3, 2, 3) = 2  (3+3)

貪婪的路徑：6 → 拿 4 → 2 → 拿 1 → 1 → 拿 1 → 0，共 3 枚
DP 的路徑：dp[6] 的最後一枚是 3 → dp[3] 的最後一枚是 3 → dp[0]，共 2 枚
```

`dp[6]` 這一格展示了 DP 比貪婪多做的事：它同時考慮了「最後一枚是 1、3、4」三種情況，發現最後一枚用 4 時前面要湊 2（2 枚），反而比最後一枚用 3、前面湊 3（1 枚）差。貪婪只看了其中一種就做決定，DP 則把所有可能都比較過。

### 解法

```python
import random
import sys
from collections import deque
from functools import cache


def coin_change(coins: list[int], amount: int) -> int:
    INF = amount + 1                         # 任何可行解最多 amount 枚，所以 amount+1 代表不可達
    dp = [0] + [INF] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if c <= a and dp[a - c] + 1 < dp[a]:
                dp[a] = dp[a - c] + 1
    return dp[amount] if dp[amount] != INF else -1


def coin_change_memo(coins: list[int], amount: int) -> int:
    sys.setrecursionlimit(max(1000, amount + 100))   # 遞迴深度最多 amount

    @cache
    def f(a: int) -> float:
        if a == 0:
            return 0
        return min((f(a - c) + 1 for c in coins if c <= a), default=float("inf"))

    res = f(amount)
    return -1 if res == float("inf") else int(res)


def coin_change_bfs(coins: list[int], amount: int) -> int:
    dist = [-1] * (amount + 1)
    dist[0] = 0
    q = deque([0])
    while q:
        a = q.popleft()
        if a == amount:
            return dist[a]
        for c in coins:
            b = a + c
            if b <= amount and dist[b] == -1:
                dist[b] = dist[a] + 1
                q.append(b)
    return -1


assert coin_change([1, 2, 5], 11) == 3
assert coin_change([2], 3) == -1
assert coin_change([1, 3, 4], 6) == 2
assert coin_change([1], 0) == 0
assert coin_change([2147483647], 2) == -1          # 面額遠大於 amount
assert coin_change([186, 419, 83, 408], 6249) == 20
for _ in range(300):
    cs = random.sample(range(1, 15), random.randint(1, 4))
    a = random.randint(0, 60)
    assert coin_change(cs, a) == coin_change_memo(cs, a) == coin_change_bfs(cs, a)
print("all tests passed")
```

### 複雜度與邊界

時間 O(amount · m)，m 是面額數：每個金額枚舉一次所有面額。空間 O(amount)。這是 pseudo-polynomial（偽多項式）複雜度：它和 amount 的**數值**成正比，而不是和輸入的位元數成正比，amount = 10⁴ 很快，amount = 10⁹ 就不行（見 F4）。邊界情況：amount = 0 時直接回傳 0；面額大於 amount 時被 `c <= a` 擋掉，不會產生負索引；不可達用 amount + 1 而不是 `float("inf")`，可以讓整個陣列保持整數；top-down 版本的遞迴深度可達 amount，必須調高遞迴限制，這也是面試中偏好 bottom-up 的理由之一。

### Follow-up

> [!question]- F1. 如果要問「有幾種湊法」呢？[1, 2] 和 [2, 1] 算同一種（518. Coin Change II）。
> 把 min 換成加法，但迴圈順序必須是**外層硬幣、內層金額**：`for c in coins: for a in range(c, amount + 1): dp[a] += dp[a − c]`，`dp[0] = 1`。外層跑硬幣等於規定「先決定用幾枚第一種、再決定第二種……」，每個多重集合只會以一種順序被數到。若反過來外層跑金額，數到的是「排列數」（377 題，[1, 2] 和 [2, 1] 不同）。時間仍是 O(amount · m)。這是第 23 章核心題 3 的主題，21.7 節有兩種迴圈的對照程式。

> [!question]- F2. 如果要回傳實際用了哪些硬幣呢？
> 填表時多存一個 `last[a]` 記錄 `dp[a]` 取最小值時的最後一枚硬幣，最後從 amount 往回走：`while a > 0: res.append(last[a]); a -= last[a]`。回溯最多走 `dp[amount]` 步。若不想多開陣列，也可以在回溯時對每個 c 檢查 `dp[a − c] == dp[a] − 1`，找到一個就往那裡走，每步 O(m)。若要所有最佳方案，就在這張「最佳轉移圖」上做 DFS，方案數可能是指數級。

> [!question]- F3. 如果每種硬幣的數量有限（第 i 種最多 kᵢ 枚）呢？
> 這變成 bounded knapsack（有界背包，第 23 章）。最直接的做法是把每一枚硬幣都當成 0/1 背包的一個物品，金額迴圈要**倒著跑**，避免同一枚被用兩次，時間 O(amount · Σkᵢ)。更快的做法是 binary splitting：把 kᵢ 拆成 1、2、4、…、剩餘量這幾包，每包當一個 0/1 物品，任何 0 到 kᵢ 的數量都能由這些包組合出來，時間降到 O(amount · Σ log kᵢ)。面試時能說出「無限枚 = 正著跑、有限枚 = 倒著跑」的差別，就代表你理解空間壓縮的依賴方向。

> [!question]- F4. 如果 amount 高達 10⁹，但面額都不大（最大面額 C ≤ 500）呢？
> O(amount · m) 不可行。關鍵觀察：最佳解中「不是最大面額」的硬幣少於 C 枚。理由是任取 C 枚硬幣，它們的前綴和模 C 必有兩個相同（或有一個為 0），所以其中某一段的總和是 C 的倍數 t·C；這一段每枚面額都小於 C，枚數一定多於 t，換成 t 枚最大面額會更少，與最佳矛盾。所以非最大面額的總和小於 C²，只要對 0 到 min(amount, C²) 跑 DP，再枚舉「非最大面額的總和 r」（r ≡ amount mod C）：答案是 `min(dp[r] + (amount − r) // C)`。時間 O(C² · m)，與 amount 無關。
> ```python
> def coin_change_large(coins, amount):
>     big = max(coins)
>     limit = min(amount, big * big)
>     INF = float("inf")
>     dp = [0] + [INF] * limit
>     for v in range(1, limit + 1):
>         dp[v] = min((dp[v - c] + 1 for c in coins if c <= v), default=INF)
>     best = min((dp[r] + (amount - r) // big
>                 for r in range(amount % big, limit + 1, big)), default=INF)
>     return -1 if best == INF else best
> ```

> [!question]- F5. 什麼樣的面額系統可以放心用貪婪？怎麼檢查？
> 貪婪對所有金額都最佳的系統稱為 canonical coin system，例如 `[1, 5, 10, 25]`。檢查方法：對 0 到某個上界的每個金額，比較貪婪的枚數和 DP 的最佳枚數，全部相同就是 canonical。已知的結果是，若存在反例，最小的反例一定小於「最大兩種面額之和」，所以只要對這個範圍跑一次本題的 DP，時間 O((c_m + c_{m−1}) · m)。面試中更重要的是說出結論：貪婪是否正確取決於面額，不能預設；不確定時就用 DP，或者用這個方法先驗證。

## 核心題 3｜300. Longest Increasing Subsequence｜Medium

### 題目

給一個整數陣列 `nums`，回傳其中最長的**嚴格遞增子序列**的長度。子序列是從原陣列刪掉零個或多個元素、其餘元素保持原本相對順序得到的序列，不需要連續。限制：`1 <= len(nums) <= 2500`，元素在 `-10⁴` 到 `10⁴` 之間。進階要求：O(n log n)。

- 範例 1：`nums = [10, 9, 2, 5, 3, 7, 101, 18]`，回傳 `4`，例如 `[2, 3, 7, 18]` 或 `[2, 5, 7, 101]`。
- 範例 2：`nums = [0, 1, 0, 3, 2, 3]`，回傳 `4`（`[0, 1, 2, 3]`）。
- 範例 3（邊界）：`nums = [7, 7, 7, 7]`，回傳 `1`，因為要求嚴格遞增，相等的元素不能接在一起。
- 範例 4（邊界）：`nums = [5]`，回傳 `1`。

### 思路

暴力解是列舉全部 2ⁿ 個子序列，檢查是否遞增，O(2ⁿ · n)。要設計 DP，先想「延伸一個遞增子序列時需要知道什麼」：要在後面接上 x，只需要知道這個子序列的**最後一個元素**是否小於 x，前面長什麼樣不重要。所以狀態定義成 `dp[i]` = 「以 `nums[i]` 結尾的最長遞增子序列長度」。轉移看倒數第二個元素是誰：它可以是任何 j < i 且 `nums[j] < nums[i]` 的元素，於是 `dp[i] = 1 + max(dp[j])`，沒有這樣的 j 時 `dp[i] = 1`。答案是 `max(dp)`，而不是 `dp[n − 1]`，因為最長的子序列不一定以最後一個元素結尾。這是形狀 B（枚舉所有前驅），O(n²)。

O(n²) 在 n = 2500 時約 3 × 10⁶ 次比較，可以通過；但 n = 10⁵ 時就不行（難題 2 正是這種規模）。要加速，換一個角度定義狀態：`tails[k]` = 「所有長度為 k + 1 的遞增子序列中，**最小的結尾值**」。直覺是，同樣長度的子序列，結尾越小，未來越容易被接上，所以只需要記住最小的那個結尾。兩個關鍵性質：一、`tails` 是嚴格遞增的，因為一個長度 k + 2、結尾為 t 的子序列，去掉最後一個元素就得到一個長度 k + 1、結尾小於 t 的子序列，所以 `tails[k] < tails[k + 1]`；二、處理新元素 x 時，x 能接在所有「結尾 < x」的子序列後面，最長的那一個是 `tails` 中最後一個小於 x 的位置。

因為 `tails` 遞增，「第一個 ≥ x 的位置」k 可以用 binary search（第 8 章）在 O(log n) 找到：x 接在長度 k 的子序列後面，形成長度 k + 1、結尾為 x 的子序列，而 x ≤ 原本的 `tails[k]`，所以令 `tails[k] = x`；若 k 等於 `len(tails)`，代表 x 比所有結尾都大，LIS 變長一格，直接 append。最後 `len(tails)` 就是答案。這個方法也叫 patience sorting（耐心排序），因為它像在玩接龍時把牌放到「第一個頂端 ≥ 它的牌堆」上。

```text
nums = [10, 9, 2, 5, 3, 7, 101, 18]

方法一：O(n²)，dp[i] = 以 nums[i] 結尾的 LIS 長度
i     :   0   1   2   3   4   5    6    7
nums  :  10   9   2   5   3   7  101   18
dp    :   1   1   1   2   2   3    4    4
前驅  :   -   -   -   2   2  3/4  5    5

dp[3]（5）：前面比 5 小的只有 2（dp=1）            → 2
dp[4]（3）：前面比 3 小的只有 2（dp=1）            → 2
dp[5]（7）：比 7 小的有 2、5、3，最大 dp 是 2      → 3
dp[6]（101）：前面全部都比較小，最大 dp 是 3       → 4
dp[7]（18）：除了 101 都比較小，最大 dp 是 3       → 4
答案 = max(dp) = 4

方法二：O(n log n)，tails[k] = 長度 k+1 的遞增子序列的最小結尾
x     bisect_left 位置  動作              tails
10          0           append            [10]
 9          0           tails[0] = 9      [9]
 2          0           tails[0] = 2      [2]
 5          1           append            [2, 5]
 3          1           tails[1] = 3      [2, 3]
 7          2           append            [2, 3, 7]
101         3           append            [2, 3, 7, 101]
18          3           tails[3] = 18     [2, 3, 7, 18]
答案 = len(tails) = 4
```

處理 3 的那一步最能說明 `tails` 的意義：原本長度 2 的最小結尾是 5（子序列 `[2, 5]`），現在發現 `[2, 3]` 也是長度 2、結尾更小，就把 5 換成 3。之後的 7 不論接在 5 或 3 後面都一樣，但如果後面出現 4，只有結尾為 3 的版本能接上。要注意 `tails` **不一定是一個真正的子序列**：例如 `[3, 4, 1]` 處理完後 `tails = [1, 4]`，但 1 在 4 的後面；它只是「每個長度的最佳結尾」的紀錄，長度才是正確的。若要還原真正的 LIS，見 F1。

### 解法

```python
import bisect
import random
from itertools import combinations


def length_of_lis_n2(nums: list[int]) -> int:
    dp = [1] * len(nums)                    # dp[i] = 以 nums[i] 結尾的 LIS 長度
    for i in range(len(nums)):
        for j in range(i):
            if nums[j] < nums[i] and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
    return max(dp, default=0)


def length_of_lis(nums: list[int]) -> int:
    tails: list[int] = []                   # tails[k] = 長度 k+1 的遞增子序列的最小結尾
    for x in nums:
        k = bisect.bisect_left(tails, x)    # 第一個 >= x 的位置；嚴格遞增所以用 left
        if k == len(tails):
            tails.append(x)
        else:
            tails[k] = x
    return len(tails)


def brute(nums):
    for length in range(len(nums), 0, -1):
        for c in combinations(nums, length):
            if all(c[i] < c[i + 1] for i in range(length - 1)):
                return length
    return 0


assert length_of_lis([10, 9, 2, 5, 3, 7, 101, 18]) == 4
assert length_of_lis([0, 1, 0, 3, 2, 3]) == 4
assert length_of_lis([7, 7, 7, 7]) == 1
assert length_of_lis([5]) == 1
assert length_of_lis([3, 4, 1]) == 2
assert length_of_lis(list(range(2500))) == 2500
for _ in range(300):
    arr = [random.randint(-5, 5) for _ in range(random.randint(1, 9))]
    assert length_of_lis(arr) == length_of_lis_n2(arr) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

O(n²) 版本時間 O(n²)、空間 O(n)；patience sorting 版本時間 O(n log n)（每個元素一次 binary search），空間 O(n)（最壞情況 `tails` 長度為 n）。邊界情況：全部相等時每個 x 的 `bisect_left` 位置都是 0，`tails` 永遠只有一格，答案 1；嚴格遞增時每次都 append，答案 n；嚴格遞減時每次都替換 `tails[0]`，答案 1。**`bisect_left` 與 `bisect_right` 的選擇決定了嚴格與否**：嚴格遞增用 left（相等的 x 會取代而不是接在後面），非嚴格遞增用 right（見 F2）。O(n²) 版本最常見的錯誤是回傳 `dp[-1]`。

### Follow-up

> [!question]- F1. 如果要回傳一個實際的最長遞增子序列呢？
> 在 patience sorting 中改存「索引」：`tails_idx[k]` 是長度 k + 1 的最佳結尾在 `nums` 中的索引，另外用 `parent[i]` 記錄元素 i 接在誰後面，也就是放入時 `tails_idx[k − 1]`（k = 0 時為 −1）。最後從 `tails_idx[-1]` 沿著 `parent` 往回走，就得到一條真正的 LIS。因為 `parent` 記錄的是 i 被放入當下的前一個結尾，那個元素的索引一定小於 i、值一定小於 `nums[i]`，所以還原出來的一定合法。時間仍是 O(n log n)，額外空間 O(n)。
> ```python
> def lis_sequence(nums):
>     tails_idx, parent = [], [-1] * len(nums)
>     for i, x in enumerate(nums):
>         k = bisect.bisect_left([nums[t] for t in tails_idx], x)   # 為了清楚；實作可自寫二分
>         parent[i] = tails_idx[k - 1] if k > 0 else -1
>         if k == len(tails_idx):
>             tails_idx.append(i)
>         else:
>             tails_idx[k] = i
>     out, i = [], tails_idx[-1] if tails_idx else -1
>     while i != -1:
>         out.append(nums[i])
>         i = parent[i]
>     return out[::-1]      # [10, 9, 2, 5, 3, 7, 101, 18] → [2, 3, 7, 18]
> ```
> 上面為了易讀每次都建了一個值的串列，那會讓複雜度變成 O(n²)；正式寫法是另外維護一個與 `tails_idx` 同步的值陣列，或自己寫比較 `nums[tails_idx[mid]]` 的 binary search。

> [!question]- F2. 如果改成「非嚴格遞增」（允許相等），或問「最少刪除幾個元素讓陣列變成遞增」呢？
> 非嚴格遞增只要把 `bisect_left` 換成 `bisect_right`：相等的 x 會接在相同值的後面而不是取代它，`[7, 7, 7, 7]` 的答案就變成 4。最少刪除幾個元素讓陣列嚴格遞增，答案是 `n − LIS`，因為留下來的元素本身就是一個遞增子序列，留得越多越好。注意「最少**修改**幾個元素讓陣列嚴格遞增」不同：被保留的元素之間還要留得下足夠的整數空間，常見做法是把 `nums[i]` 換成 `nums[i] − i`，再求非嚴格遞增的 LIS，答案是 n 減去它。

> [!question]- F3. 如果要數「最長遞增子序列有幾條」呢（673. Number of Longest Increasing Subsequence）？
> 在 O(n²) DP 上多存一個 `cnt[i]` = 以 i 結尾、長度為 `dp[i]` 的子序列個數。枚舉 j 時，若 `dp[j] + 1 > dp[i]` 就更新長度並令 `cnt[i] = cnt[j]`；若 `dp[j] + 1 == dp[i]` 就 `cnt[i] += cnt[j]`。答案是所有 `dp[i] == max(dp)` 的 `cnt[i]` 之和，O(n²)。要 O(n log n)，就把值壓縮後用 Fenwick tree（第 26 章）維護「值 < x 的元素中，(最長長度, 對應個數)」的前綴最佳值，每個元素一次查詢與一次更新。例子：`[1, 3, 5, 4, 7]` 有兩條長度 4 的 LIS（1-3-5-7 與 1-3-4-7）。

> [!question]- F4. 1671. Minimum Number of Removals to Make Mountain Array：最少刪除幾個元素讓陣列變成山形？
> 山形是先嚴格遞增再嚴格遞減，峰頂兩側都至少要有一個元素。對每個位置 i 算兩個值：`L[i]` = 以 i 結尾的 LIS 長度（從左往右做 patience sorting，記錄每個元素放入的位置 + 1），`R[i]` = 從右往左、以 i 結尾的 LIS 長度（也就是從 i 開始往右的最長遞減子序列）。以 i 為峰頂的最長山形長度是 `L[i] + R[i] − 1`，前提是 `L[i] > 1` 且 `R[i] > 1`。答案是 n 減去最大值，時間 O(n log n)。這是 LIS 當作「零件」的典型用法：要的不是整體的 LIS，而是「以每個位置結尾」的 LIS。

> [!question]- F5. 如果元素以串流的方式到來，要隨時回報目前的 LIS 長度呢？
> patience sorting 天生就是線上演算法：每來一個 x 做一次 binary search 更新 `tails`，O(log L)，`len(tails)` 隨時就是目前前綴的 LIS 長度，空間 O(L)，L 是目前的 LIS 長度，可能遠小於 n。O(n²) 的 DP 則不行，因為每個新元素都要掃過全部歷史。若串流中還會**刪除**元素，`tails` 無法回退，就要改用值域上的 segment tree 維護「以值 v 結尾的最長長度」，且刪除會讓依賴它的狀態失效，通常需要離線處理或重算，這時應該先和面試官確認刪除的模式。

## 核心題 4｜139. Word Break｜Medium

### 題目

給一個字串 `s` 和一個字典 `wordDict`（互不相同的字串串列），判斷 `s` 能不能切成一個或多個字典中的單字依序串接而成。同一個單字可以重複使用。限制：`1 <= len(s) <= 300`，`1 <= len(wordDict) <= 1000`，每個單字長度 1 到 20，全部是小寫英文字母。

- 範例 1：`s = "leetcode"`、`wordDict = ["leet", "code"]`，回傳 `True`（`"leet" + "code"`）。
- 範例 2：`s = "applepenapple"`、`wordDict = ["apple", "pen"]`，回傳 `True`，`"apple"` 用了兩次。
- 範例 3：`s = "catsandog"`、`wordDict = ["cats", "dog", "sand", "and", "cat"]`，回傳 `False`。前面能切成 `"cats" + "and"` 或 `"cat" + "sand"`，但剩下的 `"og"` 怎麼切都不行。
- 範例 4（邊界）：`s = "a"`、`wordDict = ["b"]`，回傳 `False`。

### 思路

暴力解是 backtracking：從開頭試每一個是單字的前綴，切下來之後對剩下的字串遞迴。最差情況是指數級，經典的例子是 `s = "aaaa…ab"`、字典是 `["a", "aa", "aaa", "aaaa"]`：前面的 a 有指數多種切法，每一種都要走到最後才發現 b 切不掉。但仔細看，遞迴的參數只有「從第幾個字元開始」，不論前面怎麼切，只要切到同一個位置，剩下的問題就完全一樣。所以不同的子問題只有 n + 1 個，這就是重疊子問題。

狀態定義成 `dp[i]` = 「前綴 `s[:i]` 能不能切成字典單字」。轉移看**最後一個單字**：如果最後一個單字是 `s[j:i]`，那麼前綴 `s[:j]` 必須能切好，所以 `dp[i] = any(dp[j] and s[j:i] in words)`。base case 是 `dp[0] = True`：空字串「切成零個單字」是合法的，這個定義讓「整個前綴就是一個單字」的情況（j = 0）自然成立。答案是 `dp[n]`。

直接枚舉所有 j 是 O(n²) 次切片，每次切片與 hash 又要 O(n)，總共 O(n³)。因為單字最長只有 L = 20，最後一個單字的長度不會超過 L，所以 j 只需要看 `[i − L, i)`，總時間降到 O(n · L²)（L 個候選，每個切片與 hash 是 O(L)）。另一個常數優化是一旦找到一個成立的 j 就 `break`，因為存在性題目只要一個證據就夠。

```text
s = "catsandog"，wordDict = {cats, dog, sand, and, cat}，L = 4
dp[i] = 存在 j 使 dp[j] 為 True 且 s[j:i] 在字典中

s      :     c   a   t   s   a   n   d   o   g
i      :  0   1   2   3   4   5   6   7   8   9
dp     :  T   F   F   T   T   F   F   T   F   F

填寫重點（只列出 dp[j] = T 的候選 j）：
dp[3]：j=0, s[0:3]="cat"  ∈ 字典                       → T
dp[4]：j=0, s[0:4]="cats" ∈ 字典                       → T
dp[5]：j=3 "sa"、j=4 "a" 都不在                        → F
dp[6]：j=3 "san"、j=4 "an" 都不在                      → F
dp[7]：j=3, s[3:7]="sand" ∈ 字典                       → T
       （j=4, s[4:7]="and" 也成立，break 前只需一個）
dp[8]：j=4 "ando"（長度 4）、j=7 "o" 都不在             → F
dp[9]：j=7, s[7:9]="og" 不在；j=5、6 的 dp 為 F          → F
答案 dp[9] = F
```

這張表說明了為什麼 DP 比 backtracking 快：`dp[7] = T` 有兩種切法（cat|sand 和 cats|and），backtracking 會分別從這兩種切法出發，各自嘗試切 `"og"`；DP 只記住「位置 7 可以到達」，`"og"` 只被檢查一次。當切法數是指數級時，這個差別就是指數與多項式的差別。

### 解法

```python
from functools import cache


def word_break(s: str, word_dict: list[str]) -> bool:
    words = set(word_dict)
    max_len = max(map(len, words))
    n = len(s)
    dp = [True] + [False] * n                # dp[i] = s[:i] 能否切好
    for i in range(1, n + 1):
        for j in range(max(0, i - max_len), i):
            if dp[j] and s[j:i] in words:
                dp[i] = True
                break
    return dp[n]


def word_break_memo(s: str, word_dict: list[str]) -> bool:
    words = set(word_dict)
    max_len = max(map(len, words))

    @cache
    def ok(i: int) -> bool:                  # s[i:] 能否切好
        if i == len(s):
            return True
        return any(s[i:j] in words and ok(j)
                   for j in range(i + 1, min(len(s), i + max_len) + 1))

    return ok(0)


cases = [
    ("leetcode", ["leet", "code"], True),
    ("applepenapple", ["apple", "pen"], True),
    ("catsandog", ["cats", "dog", "sand", "and", "cat"], False),
    ("a", ["b"], False),
    ("aaaaaaa", ["aaaa", "aaa"], True),
    ("a" * 299 + "b", ["a", "aa", "aaa", "aaaa"], False),   # backtracking 會指數爆炸
]
for s, d, want in cases:
    assert word_break(s, d) == want == word_break_memo(s, d)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n · L²)：n 個位置，每個位置最多 L 個候選 j，每個候選的切片與 hash 是 O(L)；建立字典的 set 另需 O(總字元數)。空間 O(n + 總字元數)。邊界情況：`dp[0] = True` 是讓「整個前綴就是一個單字」成立的關鍵；字典中有比 s 更長的單字時，`max(0, i − max_len)` 保證 j 不會是負數；top-down 版本的遞迴深度最多 n = 300，Python 預設限制足夠。若不用長度上限 L，時間是 O(n³)，n = 300 仍可通過，但面試時應該主動提出這個優化。

### Follow-up

> [!question]- F1. 如果要回傳所有切法（140. Word Break II）呢？
> 答案本身可能是指數多個（`"aaa…a"` 配上 `["a", "aa"]` 的切法數是費波那契數），所以不可能有多項式演算法，只能讓「每一個輸出」的成本合理。做法是 top-down 記憶化：`go(i)` 回傳 `s[i:]` 的所有切法串列，對每個是單字的 `s[i:j]`，把它接在 `go(j)` 的每個結果前面。記憶化保證每個後綴的切法只被組裝一次；再先用本題的 DP 判斷可行性，可以避免在切不完的分支上浪費時間。總時間是 O(n · L + 輸出總長度) 的量級。
> ```python
> def word_break_all(s, word_dict):
>     words, n = set(word_dict), len(s)
>     max_len = max(map(len, words))
>
>     @cache
>     def go(i):
>         if i == n:
>             return [[]]
>         return [[s[i:j]] + rest
>                 for j in range(i + 1, min(n, i + max_len) + 1) if s[i:j] in words
>                 for rest in go(j)]
>
>     return [" ".join(p) for p in go(0)]   # "catsanddog" → ["cat sand dog", "cats and dog"]
> ```

> [!question]- F2. 如果要問「最少用幾個單字」或「有幾種切法」呢？
> 同一張表、換一種運算。最少單字數：`dp[i] = min(dp[j] + 1)`，`dp[0] = 0`，不可達設 +∞，這是形狀 B 的最佳化版。切法數：`dp[i] = Σ dp[j]`（對所有 `s[j:i]` 是單字的 j），`dp[0] = 1`，通常要取模；因為「最後一個單字」不同的切法一定不同，分類互斥，所以加法不會重複計數。兩者時間都是 O(n · L²)。這是 21.7 節「存在性用 or、最佳化用 min、計數用 +」的直接應用。

> [!question]- F3. 如果字典很大、單字很長（L 到 10³），怎麼加速？
> 瓶頸是每個 (j, i) 都要切片並 hash 一個長度 i − j 的字串，總共 O(n · L²)。改用 Trie（字首樹，第 13 章）：把字典建成 trie，對每個 `dp[j] = True` 的起點 j，從 `s[j]` 開始沿著 trie 往下走，每走到一個「單字結尾」的節點 i，就令 `dp[i] = True`；遇到 trie 中沒有的字元就停。每個起點最多走 L 步、每步 O(1)，總時間 O(n · L + 總字元數)。若還要更快，可以用 Aho-Corasick 自動機一次找出所有單字在 s 中的出現位置，時間 O(n + 總字元數 + 出現次數)。

> [!question]- F4. 472. Concatenated Words：找出字典中所有「能由至少兩個其他單字串接而成」的單字。
> 對每個單字 w 跑一次本題的 DP，但字典要排除 w 自己（或要求至少切成兩段）。把單字依長度排序後逐一處理，處理 w 時只把比它短的單字放進集合，因為組成 w 的單字一定比 w 短；判斷完再把 w 加入集合。每個單字的成本是 O(|w|²)（或用 trie 降到 O(|w| · L)），總時間 O(Σ|w|²)。這是第 13 章難題 5 的主題，關鍵是把「每個單字都是一次 word break」看出來。

> [!question]- F5. 如果每個字典單字最多只能用一次呢？
> 狀態「切到第 i 個字元」就不夠了，因為未來需要知道哪些單字已經用掉，狀態要變成 `(i, 已用單字的集合)`，狀態數是 n · 2^m。只有字典很小（m ≤ 15 左右）時才能用 bitmask DP（第 24 章）；一般情況要用 backtracking 加上剪枝，例如先用原本的 DP 判斷「不限次數時剩下的後綴能否切好」，切不好就直接剪掉。這個 follow-up 在檢查你是否理解「可重複使用」正是讓狀態只剩一個整數的原因。

## 核心題 5｜91. Decode Ways｜Medium

### 題目

一段只含字母 A–Z 的訊息依照 `A → "1"`、`B → "2"`、…、`Z → "26"` 編碼成數字字串。給一個只含數字的字串 `s`，回傳它有幾種解碼方式。注意 `"06"` 不是合法的編碼（不能有前導 0），所以 `"0"` 本身也無法解碼。保證答案在 32 位元整數範圍內。限制：`1 <= len(s) <= 100`，`s` 只含數字，可能有前導 0。

- 範例 1：`s = "12"`，回傳 `2`：`"AB"`（1, 2）或 `"L"`（12）。
- 範例 2：`s = "226"`，回傳 `3`：`"BZ"`（2, 26）、`"VF"`（22, 6）、`"BBF"`（2, 2, 6）。
- 範例 3（邊界）：`s = "06"`，回傳 `0`；`s = "10"`，回傳 `1`（只能是 10 → J）。
- 範例 4（邊界）：`s = "2101"`，回傳 `1`：只有 2, 10, 1。`21, 0, 1` 和 `2, 1, 01` 都因為 0 不能單獨解碼或作為前導而失敗。

### 思路

暴力解是遞迴地決定「下一個字母用 1 位還是 2 位數字」：`ways(i)` = `s[i:]` 的解碼數，若 `s[i] != '0'` 可以取 1 位，貢獻 `ways(i + 1)`；若 `s[i:i+2]` 介於 10 到 26，可以取 2 位，貢獻 `ways(i + 2)`。分支數是 2，深度 n，最多 O(2ⁿ) 次呼叫；全是 1 的字串，解碼數就是費波那契數。和爬樓梯一樣，參數只有 i，所以只有 n + 1 個不同的子問題。

bottom-up 版本定義 `dp[i]` = 「前綴 `s[:i]` 的解碼數」。看**最後一個字母**用了幾位數字：如果用 1 位，`s[i − 1]` 必須是 1–9，前面 `s[:i − 1]` 有 `dp[i − 1]` 種解碼；如果用 2 位，`s[i − 2:i]` 必須是 10–26（這個範圍自動排除了前導 0 的 `"05"`），前面有 `dp[i − 2]` 種。兩種情況的最後一個字母不同，互斥，所以直接相加：`dp[i] = [s[i−1] ≠ '0'] · dp[i − 1] + [10 ≤ s[i−2:i] ≤ 26] · dp[i − 2]`。base case：`dp[0] = 1`（空字串有一種解碼：什麼都不解），`dp[1] = 1 if s[0] != '0' else 0`。

為什麼 `dp[0] = 1` 而不是 0？因為它是讓轉移在 i = 2 時成立的唯一值：`"12"` 的「整段 12」這種解碼，前面剩下空字串，必須被數成 1 種，才會得到 `dp[2] = 1 + 1 = 2`。0 是這題最大的陷阱，只要字串中出現 0，它前一位必須是 1 或 2，否則整個答案為 0；DP 會自然處理這件事，因為那一格的兩項都是 0，之後所有格子都是 0。

```text
s = "226"
dp[i] = （s[i-1] 是 1–9 ? dp[i-1] : 0）+（s[i-2:i] 在 10–26 ? dp[i-2] : 0）

i         :  0    1    2    3
最後 1 位 :  -   "2"  "2"  "6"
最後 2 位 :  -    -   "22" "26"
dp        :  1    1    2    3

dp[1] = "2" 可單獨解                  → dp[0]          = 1
dp[2] = "2" 可單獨解 → dp[1]=1；"22" 合法 → dp[0]=1    = 2
dp[3] = "6" 可單獨解 → dp[2]=2；"26" 合法 → dp[1]=1    = 3

s = "2101"
i         :  0    1    2    3    4
最後 1 位 :  -   "2"  "1"  "0"  "1"
最後 2 位 :  -    -   "21" "10" "01"
dp        :  1    1    2    1    1

dp[3]："0" 不能單獨解 → 0；"10" 合法 → dp[1] = 1     = 1
dp[4]："1" 可單獨解 → dp[3] = 1；"01" 有前導 0 → 0   = 1
```

`"2101"` 的 `dp[2] = 2`（2,1 與 21）到了 `dp[3]` 掉回 1：因為 0 必須和前面的 1 綁在一起成為 10，所以「21」這種解法被淘汰，只剩下 `dp[1]` 那一種（2 然後 10）。最後一個 1 只能單獨解碼，因為 `"01"` 不合法。

### 解法

```python
import random
from functools import cache


def num_decodings(s: str) -> int:
    prev2, prev1 = 1, 1 if s[0] != "0" else 0      # dp[0]、dp[1]
    for i in range(2, len(s) + 1):
        cur = 0
        if s[i - 1] != "0":
            cur += prev1
        if 10 <= int(s[i - 2:i]) <= 26:
            cur += prev2
        prev2, prev1 = prev1, cur
    return prev1


def brute(s):
    @cache
    def go(i):
        if i == len(s):
            return 1
        total = 0
        for length in (1, 2):
            piece = s[i:i + length]
            if len(piece) == length and piece[0] != "0" and 1 <= int(piece) <= 26:
                total += go(i + length)
        return total
    return go(0)


assert num_decodings("12") == 2
assert num_decodings("226") == 3
assert num_decodings("06") == 0
assert num_decodings("10") == 1
assert num_decodings("2101") == 1
assert num_decodings("0") == 0
assert num_decodings("100") == 0           # "00" 無法解碼
assert num_decodings("1111111") == 21      # 全是 1：費波那契數
assert num_decodings("27") == 1            # 27 > 26，只能 2, 7
for _ in range(500):
    t = "".join(random.choice("0123456789") for _ in range(random.randint(1, 10)))
    assert num_decodings(t) == brute(t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)，空間 O(1)。邊界情況：開頭是 0 時 `dp[1] = 0`，之後每一格最多只能從 `dp[i − 2]` 拿到值，而 `"0x"` 永遠不在 10–26，所以答案為 0；連續兩個 0（`"100"`）時第二個 0 的兩項都是 0，之後全為 0；`"27"`、`"30"` 這類超過 26 的兩位數不能合併；`int(s[i−2:i])` 在 `"05"` 時得到 5，小於 10，所以前導 0 被自動排除，不需要另外檢查 `s[i − 2] != '0'`。

### Follow-up

> [!question]- F1. 如果字串中可以有 '*'，代表 1 到 9 任一個數字，答案對 10⁹ + 7 取模呢（639. Decode Ways II）？
> 轉移的結構不變，只是「最後一位能單獨解碼的方式數」和「最後兩位能合併的方式數」變成係數：單一字元 `*` 有 9 種，`0` 有 0 種，其他 1 種；兩位數時 `**` 有 15 種（11–19、21–26），`*d` 在 d ≤ 6 時有 2 種（1d、2d）否則 1 種，`1*` 有 9 種、`2*` 有 6 種，其他照原規則。`dp[i] = one(s[i−1]) · dp[i−1] + two(s[i−2], s[i−1]) · dp[i−2]`，每步取模，O(n) 時間、O(1) 空間。
> ```python
> def num_decodings_star(s, mod=10**9 + 7):
>     def one(c):
>         return 9 if c == "*" else (0 if c == "0" else 1)
>
>     def two(a, b):
>         if a == "*" and b == "*":
>             return 15
>         if a == "*":
>             return 2 if b <= "6" else 1
>         if b == "*":
>             return 9 if a == "1" else 6 if a == "2" else 0
>         return 1 if 10 <= int(a + b) <= 26 else 0
>
>     p2, p1 = 1, one(s[0])
>     for i in range(1, len(s)):
>         p2, p1 = p1, (one(s[i]) * p1 + two(s[i - 1], s[i]) * p2) % mod
>     return p1                    # "*" → 9、"1*" → 18、"**" → 96
> ```

> [!question]- F2. 如果要列出所有解碼結果呢？
> 解碼數最多是費波那契數級（長度 100 的全 1 字串約 5.7 × 10²⁰ 種），所以只能用 backtracking 逐一產生，時間與輸出大小成正比。實作上可以先跑一次本題的 DP 算出每個後綴的解碼數，遞迴時跳過解碼數為 0 的分支，保證每一條遞迴路徑都會產生至少一個結果，不會在死路上浪費時間。這是「DP 幫 backtracking 剪枝」的常見組合，也適用於核心題 4 的 F1。

> [!question]- F3. 如果編碼表不是 1–26，而是任意給定的「數字字串 → 字母」對照表（長度不一）呢？
> 那就變成核心題 4 的計數版：把每個合法的編碼當成字典單字，`dp[i] = Σ dp[j]`（對所有 `s[j:i]` 是合法編碼的 j），`dp[0] = 1`。若最長的編碼長度是 L，時間 O(n · L²)，或用 trie 降到 O(n · L)。原題只是 L = 2 且字典是 `{"1", …, "26"}` 的特例，所以兩項轉移就夠。看出這一層，代表你把 91 和 139 當成同一個 pattern，而不是兩道各自背誦的題目。

> [!question]- F4. 如果有很多次查詢，每次問子字串 s[l..r] 的解碼數呢？
> 每次重跑 DP 是 O(n)，q 次查詢 O(q · n)。注意到轉移是線性的：`(dp[i], dp[i−1]) = Mᵢ · (dp[i−1], dp[i−2])`，其中 Mᵢ 是一個只依賴 `s[i−2..i−1]` 的 2×2 矩陣 `[[a, b], [1, 0]]`（a 是最後一位能否單獨解碼，b 是最後兩位能否合併）。子字串的答案就是一段矩陣連乘作用在初始向量 `(dp[1], dp[0])` 上，其中初始值由 `s[l]` 決定，第一個字元不能和 `s[l − 1]` 合併，所以從 l + 2 開始連乘。用 segment tree（第 26 章）維護矩陣乘積，每次查詢 O(log n)。這個「線性轉移 → 矩陣」的觀點也能把 n = 10¹⁸ 的費波那契數降到 O(log n)。

> [!question]- F5. 如果要求解碼後的字串中不能有兩個相鄰的相同字母呢？
> 未來需要知道「上一個字母是什麼」，狀態要多一維：`dp[i][c]` = 前綴 `s[:i]` 解碼後以字母 c 結尾的方式數。轉移時，最後一個字母 c 若由 1 位數字得到，則 `dp[i][c] += Σ_{c' ≠ c} dp[i − 1][c']`；由 2 位數字得到則用 `dp[i − 2]`。用「總和減去自己」可以讓每格 O(1)：`Σ_{c' ≠ c} = total[i − 1] − dp[i − 1][c]`。時間 O(26 · n)，空間 O(26)。這是 21.4 節「未來需要知道什麼，就放進狀態」的直接應用。

## 難題 1｜188. Best Time to Buy and Sell Stock IV｜Hard

### 題目

給一個整數 k 和一個陣列 `prices`，`prices[i]` 是某支股票第 i 天的價格。你**最多**可以完成 k 筆交易（一筆交易 = 買一次再賣一次），而且同一時間最多只能持有一股：必須先賣掉手上的股票才能再買。請回傳能得到的最大利潤。限制：`1 <= k <= 100`，`1 <= len(prices) <= 1000`，`0 <= prices[i] <= 1000`。

- 範例 1：`k = 2`、`prices = [2, 4, 1]`，回傳 `2`（第 0 天以 2 買、第 1 天以 4 賣）。
- 範例 2：`k = 2`、`prices = [3, 2, 6, 5, 0, 3]`，回傳 `7`（2 買 6 賣賺 4，0 買 3 賣賺 3）。
- 範例 3（邊界）：`k = 1`、`prices = [5, 4, 3]`，回傳 `0`，一路下跌時不交易最好。
- 範例 4（邊界）：`k = 100`、`prices = [1, 2, 3, 4, 5]`，回傳 `4`；k 遠大於能用到的交易次數，等同於不限次數。

### 提示

> [!tip]- 提示 1
> 每一天結束時，你的「情況」可以用兩件事描述：手上有沒有股票、已經開始了幾筆交易。把這些情況當成狀態，畫出一張狀態機。

> [!tip]- 提示 2
> 狀態是 `hold[j]`（第 j 筆交易已買入、尚未賣出）與 `sold[j]`（已完成 j 筆交易、手上空）。買入只能從 `sold[j − 1]` 走到 `hold[j]`，賣出從 `hold[j]` 走到 `sold[j]`，休息則停在原狀態。

> [!tip]- 提示 3
> `hold[j] = max(hold[j], sold[j − 1] − p)`、`sold[j] = max(sold[j], hold[j] + p)`，每天對 j = 1…k 更新一次，O(n · k)。當 k ≥ n / 2 時，交易次數不再是限制，直接加總所有上漲的差價。

### 詳解

**為什麼直覺做法不行**。一個常見的直覺是：找出所有「谷底到峰頂」的上漲段，挑利潤最大的 k 段。這在段數 ≤ k 時正確，但段數多於 k 時會錯，因為有時候**合併**兩段比各自保留更好。例如 `[1, 5, 3, 8]`、k = 1：兩個上漲段是 1→5（賺 4）和 3→8（賺 5），挑最大的一段只有 5，但 1 買 8 賣能賺 7。另一個方向是暴力枚舉 2k 個交易日，O(n^{2k})，完全不可行。問題在於每一天的決定（買、賣、不動）會影響之後能做什麼，而影響的方式只取決於「手上有沒有股票、還剩幾次交易」，這正是狀態機 DP 的形狀。

**畫出狀態機**。照 21.6 節的方法列出每天結束時的情況：`sold[0]` 是「還沒做任何交易、空手」；`hold[j]` 是「第 j 筆交易已經買進、還沒賣」；`sold[j]` 是「已完成 j 筆交易、空手」。動作只有三種：休息（停在原狀態）、買（`sold[j − 1] → hold[j]`，利潤 −p）、賣（`hold[j] → sold[j]`，利潤 +p）。這是一條長鏈：`sold₀ → hold₁ → sold₁ → hold₂ → sold₂ → … → sold_k`，每個點有一個指向自己的「休息」邊。把每個狀態的值定義成「處在這個狀態時的最大累積利潤」，轉移就是指向它的兩條邊取 max。

**初始值與答案**。第一天之前只有 `sold[0]` 可達，值為 0；所有 `hold[j]` 是 −∞。`sold[j]`（j ≥ 1）可以初始化為 0：題目是「最多 k 筆」，把 `sold[j]` 定義成「最多完成 j 筆」，那麼一筆都不做的 0 也算在裡面，這讓答案直接是 `sold[k]`，不必再對所有 j 取 max。若定義成「恰好 j 筆」，就要初始化成 −∞，最後取 `max(sold)`，兩種都對，但要和定義一致。

**同一天的更新順序**。程式裡對 j 由小到大**就地**更新：`hold[j]` 用到的 `sold[j − 1]` 可能已經是今天更新過的值，等於允許「今天賣出第 j − 1 筆、今天又買入第 j 筆」。這不會讓答案變大：同一天賣再買，淨效果等於繼續持有，只是多用了一次交易次數，所以任何利用這件事的方案，都有一個交易次數更少、利潤相同的合法方案。`sold[j]` 用到今天的 `hold[j]` 也一樣，代表同一天買賣，利潤為 0。因此就地更新是安全的，不需要複製昨天的陣列；這一點和 21.6 節的冷卻題不同，冷卻題的就地更新會違反規則，所以那裡必須同時更新。

**k 很大時**。每一筆有用的交易至少佔兩天（買的那天和賣的那天不同），而且最佳的不限次數方案由互不重疊的「連續上漲段」組成，最多 ⌊n / 2⌋ 段。所以當 k ≥ n / 2 時，交易次數的限制等於不存在，答案就是 122 題的「加總每一個正的相鄰差價」，O(n)。這個特判不只是優化：k 到 10⁹ 時若不特判，O(n · k) 的陣列根本開不出來。

```text
k = 2，prices = [3, 2, 6, 5, 0, 3]

狀態機（每個狀態都有一條「休息」的自環，圖中省略）
sold₀ ──買(−p)──▶ hold₁ ──賣(+p)──▶ sold₁ ──買(−p)──▶ hold₂ ──賣(+p)──▶ sold₂

初始：sold₀ = 0，hold₁ = hold₂ = −∞，sold₁ = sold₂ = 0（「最多 j 筆」的定義）

day  p   hold₁              sold₁            hold₂               sold₂
 0   3   max(−∞, 0−3) = −3   max(0, −3+3)= 0   max(−∞, 0−3) = −3    max(0, −3+3) = 0
 1   2   max(−3, 0−2) = −2   max(0, −2+2)= 0   max(−3, 0−2) = −2    max(0, 0)    = 0
 2   6   max(−2, 0−6) = −2   max(0, −2+6)= 4   max(−2, 4−6) = −2    max(0, −2+6) = 4
 3   5   max(−2, 0−5) = −2   max(4, −2+5)= 4   max(−2, 4−5) = −1    max(4, −1+5) = 4
 4   0   max(−2, 0−0) = 0    max(4, 0+0) = 4   max(−1, 4−0) = 4     max(4, 4+0)  = 4
 5   3   max(0, 0−3)  = 0    max(4, 0+3) = 4   max(4, 4−3)  = 4     max(4, 4+3)  = 7
答案 sold₂ = 7
```

逐列看：第 2 天 `sold₁` 變成 4，代表「2 買 6 賣」的第一筆交易已經完成；第 3 天 `hold₂ = −1` 是「第一筆賺 4、第 3 天以 5 買進第二筆」，還不是最好的第二筆買點；第 4 天價格跌到 0，`hold₂` 更新為 4 − 0 = 4，也就是帶著第一筆的 4 元利潤以 0 買進；第 5 天以 3 賣出，`sold₂ = 7`。如果 k = 1，答案停在 `sold₁ = 4`：只能做一筆時，2 買 6 賣是最好的。

### 解法

```python
import random
from functools import cache


def max_profit(k: int, prices: list[int]) -> int:
    n = len(prices)
    if k >= n // 2:                                     # 交易次數不構成限制
        return sum(max(0, prices[i] - prices[i - 1]) for i in range(1, n))
    hold = [float("-inf")] * (k + 1)                    # hold[j]：第 j 筆已買入、未賣出
    sold = [0] * (k + 1)                                # sold[j]：最多完成 j 筆、空手
    for p in prices:
        for j in range(1, k + 1):
            hold[j] = max(hold[j], sold[j - 1] - p)
            sold[j] = max(sold[j], hold[j] + p)
    return sold[k]


def brute(k, prices):
    @cache
    def go(i, used, holding):
        if i == len(prices):
            return 0 if not holding else float("-inf")
        best = go(i + 1, used, holding)                 # 休息
        if holding:
            best = max(best, go(i + 1, used, False) + prices[i])
        elif used < k:
            best = max(best, go(i + 1, used + 1, True) - prices[i])
        return best
    return go(0, 0, False)


assert max_profit(2, [2, 4, 1]) == 2
assert max_profit(2, [3, 2, 6, 5, 0, 3]) == 7
assert max_profit(1, [5, 4, 3]) == 0
assert max_profit(100, [1, 2, 3, 4, 5]) == 4
assert max_profit(1, [1, 5, 3, 8]) == 7                # 合併兩段上漲比各自保留好
assert max_profit(2, [1, 5, 3, 8]) == 9
assert max_profit(3, [7]) == 0
for _ in range(500):
    pr = [random.randint(0, 10) for _ in range(random.randint(1, 9))]
    kk = random.randint(1, 5)
    assert max_profit(kk, pr) == brute(kk, pr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n · min(k, n / 2))：k ≥ n / 2 時走 O(n) 的貪婪分支，否則每天更新 2k 個狀態。空間 O(k)，只保留每個狀態的目前值。邊界情況：n = 1 時任何 k 都滿足 k ≥ 0 = n // 2，走貪婪分支回傳 0；價格一路下跌時所有 `sold[j]` 保持 0；價格可以是 0，`hold` 的初始值必須是 −∞ 而不是 0，否則等於第 0 天就免費持有一股；`max_profit(1, [1, 5, 3, 8]) == 7` 這個測試專門檢查「合併上漲段」的情況，貪婪挑段的寫法會在這裡失敗。

### Follow-up

> [!question]- F1. 如果每筆交易有手續費 fee，或賣出後要冷卻一天，同時限制最多 k 筆呢？
> 狀態機的形狀不變，只改邊的權重或起點。手續費：賣出的邊從 `+p` 改成 `+p − fee`，即 `sold[j] = max(sold[j], hold[j] + p − fee)`。冷卻：第 j 筆的買入不能從「今天剛賣出第 j − 1 筆」出發，只能從「昨天以前就已經是 `sold[j − 1]`」出發，所以要保留前一天的 `sold` 陣列，`hold[j] = max(hold[j], sold_yesterday[j − 1] − p)`，而且這時就不能再就地更新了。兩者都是 O(n · k) 時間、O(k) 空間。這個 follow-up 在檢查你是否真的理解每條邊的意義，而不是背了一個公式。

> [!question]- F2. 如果要輸出實際的交易（哪天買、哪天賣）呢？
> 空間壓縮後無法回溯，要保留完整的 `hold[i][j]` 與 `sold[i][j]` 表（O(n · k) 空間）。從 `sold[n − 1][k]` 往回走：若 `sold[i][j] == sold[i − 1][j]`，代表第 i 天在這個狀態休息，往前一天；否則第 i 天賣出，跳到 `hold[i][j]`。在 `hold` 狀態同理：若 `hold[i][j] == hold[i − 1][j]` 就休息，否則第 i 天買入，跳到 `sold[i][j − 1]`（同一天的值，因為我們允許就地更新）。回溯 O(n + k)。注意若同一天出現「賣出又買入」，輸出時要把它合併成一筆持續持有的交易。

> [!question]- F3. 如果 n 和 k 都到 10⁵，O(n · k) 太慢，怎麼辦？
> 設 f(k) 是最多 k 筆交易的最大利潤，它對 k 是凹函數（每多一筆交易帶來的邊際利潤遞減）。於是可以用 Aliens trick（又稱 WQS binary search）：給每筆交易一個懲罰 λ，求「不限次數、每筆扣 λ」的最佳利潤 g(λ)，這就是 714 題的手續費版本，O(n)，同時記錄最佳解用了幾筆交易（相同利潤時取較少筆）。λ 越大，最佳解用的筆數越少；binary search 找最小的 λ 使筆數 ≤ k，答案是 g(λ) + λ · k。時間 O(n log P)，P 是價格上限。另一個做法是用 stack 加 heap 把「谷峰對」合併與拆分，也是 O(n log n)。
> ```python
> def max_profit_aliens(k, prices):
>     def with_fee(fee):                      # 回傳 (最大利潤, 達到它的最少交易數)
>         hold, free = (float("-inf"), 0), (0, 0)
>         for p in prices:                    # 以 (利潤, −筆數) 比大小：利潤相同時筆數少者勝
>             hold, free = (max(hold, (free[0] - p, free[1] - 1)),
>                           max(free, (hold[0] + p - fee, hold[1])))
>         return free[0], -free[1]
>
>     lo, hi = 0, max(prices) + 1             # λ = max+1 時一定一筆都不做
>     while lo < hi:
>         mid = (lo + hi) // 2
>         if with_fee(mid)[1] <= k:
>             hi = mid
>         else:
>             lo = mid + 1
>     return with_fee(lo)[0] + lo * k         # 與 O(n·k) 版本在隨機測試中結果一致
> ```

> [!question]- F4. 如果允許「放空」（先以 p 賣出、之後再以較低價買回），每次放空也算一筆交易呢？
> 在狀態機裡多加一種持倉：`short[j]`（第 j 筆是放空、尚未回補）。邊有四條：`sold[j − 1] → hold[j]`（買，−p）、`hold[j] → sold[j]`（賣，+p）、`sold[j − 1] → short[j]`（放空，+p）、`short[j] → sold[j]`（回補，−p），各自加上休息的自環。轉移變成 `short[j] = max(short[j], sold[j − 1] + p)`、`sold[j] = max(sold[j], hold[j] + p, short[j] − p)`，仍是 O(n · k)。注意這時**不能**再像原題一樣讓 j 由小到大就地更新：同一天「賣出第 j − 1 筆多單、再放空第 j 筆」等於把多單直接翻成空單，它不像「賣出再買回」那樣等價於什麼都沒做，會讓答案偏大（下面的例子會從 14 變成 15）。做法是讓 `hold[j]`、`short[j]` 只用昨天的 `sold[j − 1]`，最簡單的寫法是 j 由大到小更新。例如 `[1, 7, 9, 8, 2]`、k = 2：1 買 9 賣賺 8，再以 8 放空、2 回補賺 6，共 14。這正是狀態機的威力：多一種規則，就是多一個節點與幾條邊。

> [!question]- F5. 為什麼 k ≥ n / 2 時可以直接加總所有上漲差價？這個貪婪為什麼正確？
> 不限次數時（122 題），任何一筆交易「i 買 j 賣」的利潤 `p[j] − p[i]` 都等於中間每天差價之和 `Σ (p[t+1] − p[t])`，所以總利潤不可能超過「所有正的相鄰差價之和」；而這個上界可以達到：每一段連續上漲都在谷底買、峰頂賣。這些連續上漲段互不重疊、每段至少兩天，所以段數 ≤ ⌊n / 2⌋，只要 k 不小於這個數，限制就不會被觸及。面試時能把「k 很大的特判」講成「交易次數的上界」，比只說「這是優化」更有說服力，而且它避免了 k 很大時開出 O(k) 陣列的問題。

### 心得

關鍵突破是把「最多 k 筆交易」變成狀態機上的一條長鏈 `sold₀ → hold₁ → sold₁ → … → sold_k`，每天沿著邊走一步或停在原地，於是交易次數的限制變成「鏈的長度」，不需要任何額外的判斷。它和本章其他題的關係是：21.6 節的冷卻與手續費題是同一張圖換幾條邊，核心題 1 的 House Robber 是只有兩個節點的狀態機。面試時建議先畫圖再寫程式：說出三種動作、每個狀態的意義、−∞ 的初始值，再說明 k ≥ n / 2 的特判和「同一天就地更新為什麼安全」。若面試官繼續追問大 k，能提到 Aliens trick 的凹性與手續費的對應，就是 L5 等級的回答。

## 難題 2｜354. Russian Doll Envelopes｜Hard

### 題目

給一個二維陣列 `envelopes`，`envelopes[i] = [wᵢ, hᵢ]` 代表第 i 個信封的寬和高。一個信封可以放進另一個信封，若且唯若它的寬**和**高都**嚴格**小於另一個。請回傳最多能有幾個信封一層套一層（像俄羅斯娃娃）。信封不能旋轉。限制：`1 <= n <= 10⁵`，`1 <= wᵢ, hᵢ <= 10⁵`。

- 範例 1：`envelopes = [[5, 4], [6, 4], [6, 7], [2, 3]]`，回傳 `3`（`[2, 3] → [5, 4] → [6, 7]`）。
- 範例 2：`envelopes = [[4, 5], [4, 6], [6, 7], [2, 3], [1, 1]]`，回傳 `4`（`[1, 1] → [2, 3] → [4, 5] → [6, 7]`）。`[4, 5]` 和 `[4, 6]` 寬度相同，不能互套。
- 範例 3（邊界）：`envelopes = [[1, 1], [1, 1], [1, 1]]`，回傳 `1`，相同大小的信封不能互套。
- 範例 4（邊界）：只有一個信封時回傳 `1`。

### 提示

> [!tip]- 提示 1
> 如果先依寬度排序，問題就變成在高度上找一個「遞增子序列」。這和核心題 3 有什麼關係？n = 10⁵ 時 O(n²) 能不能接受？

> [!tip]- 提示 2
> 寬度相同的信封不能互套，但只依寬度排序後，它們的高度可能形成遞增序列而被誤算。能不能靠排序的方式，讓同寬的信封在高度上「不可能」同時出現在一條嚴格遞增子序列中？

> [!tip]- 提示 3
> 依寬度遞增排序，寬度相同時依高度**遞減**排序，然後對高度做嚴格遞增的 LIS（patience sorting，`bisect_left`），O(n log n)。

### 詳解

**為什麼直覺做法不行**。這是二維的 LIS：要找一條序列，兩個維度都嚴格遞增。先依寬度排序，就能用核心題 3 的 O(n²) DP：`dp[i]` = 以第 i 個信封為最外層的最多層數，`dp[i] = 1 + max(dp[j])`，對所有 `w[j] < w[i]` 且 `h[j] < h[i]` 的 j。這完全正確，但 n = 10⁵ 時是 10¹⁰ 次比較，遠遠超時。自然的想法是對高度用 patience sorting，但只依寬度排序後，寬度相同的信封會出問題：例如 `[[3, 3], [3, 4]]`，排序後高度是 `[3, 4]`，LIS 長度 2，可是兩個信封寬度一樣，根本不能互套。

**突破點：同寬時高度遞減**。如果寬度相同的信封按高度**由大到小**排列，它們的高度在序列中是遞減的，任何嚴格遞增子序列最多只能從中挑一個。於是「高度的嚴格遞增子序列」中，相鄰兩個信封的寬度一定不同；又因為整體依寬度遞增排序，寬度不同就代表後面的比較寬，而高度也嚴格遞增，所以它們真的能互套。反過來，任何合法的套娃序列，依寬度排序後在這個序列中也是高度嚴格遞增的子序列。兩個方向都成立，所以答案就是高度序列的 LIS。

**正確性的完整論證**。設排序後的高度序列為 H。（一）H 的任一個嚴格遞增子序列都對應一個合法套娃：子序列中相鄰的兩個信封 a 在 b 之前，若 `w_a == w_b`，因為同寬按高度遞減，`h_a >= h_b`，與嚴格遞增矛盾；所以 `w_a < w_b`，又 `h_a < h_b`，a 能放進 b。（二）任一個合法套娃，信封的寬度嚴格遞增，所以在排序後的順序中依序出現，高度也嚴格遞增，是 H 的一個嚴格遞增子序列。因此兩者的最大長度相同。

```text
envelopes = [[4, 5], [4, 6], [6, 7], [2, 3], [1, 1]]

排序（寬度遞增，同寬高度遞減）：
[1, 1]  [2, 3]  [4, 6]  [4, 5]  [6, 7]
高度序列 H = 1, 3, 6, 5, 7

對 H 做 patience sorting（bisect_left，嚴格遞增）：
h    位置  動作            tails
1     0    append          [1]
3     1    append          [1, 3]
6     2    append          [1, 3, 6]
5     2    tails[2] = 5    [1, 3, 5]       ← 同寬的 [4, 5] 取代 [4, 6]，不會接在它後面
7     3    append          [1, 3, 5, 7]
答案 = 4：[1, 1] → [2, 3] → [4, 5] → [6, 7]

若同寬時高度遞增（錯誤的排序）：
[1, 1]  [2, 3]  [4, 5]  [4, 6]  [6, 7]
H = 1, 3, 5, 6, 7 → LIS = 5，把 [4, 5] → [4, 6] 錯算成可以互套
```

這張表展示了排序規則的作用：同寬的 6 和 5 以遞減順序出現，5 只能取代 6 在 `tails` 中的位置，而不能接在 6 後面形成更長的序列。錯誤的遞增排序則讓 5、6 連成一條遞增序列，多算了一層。

### 解法

```python
import bisect
import random


def max_envelopes(envelopes: list[list[int]]) -> int:
    envelopes = sorted(envelopes, key=lambda e: (e[0], -e[1]))   # 寬遞增、同寬高遞減
    tails: list[int] = []
    for _, h in envelopes:
        k = bisect.bisect_left(tails, h)                         # 嚴格遞增
        if k == len(tails):
            tails.append(h)
        else:
            tails[k] = h
    return len(tails)


def brute(envelopes):
    env = sorted(envelopes)
    dp = [1] * len(env)
    for i in range(len(env)):
        for j in range(i):
            if env[j][0] < env[i][0] and env[j][1] < env[i][1]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)


assert max_envelopes([[5, 4], [6, 4], [6, 7], [2, 3]]) == 3
assert max_envelopes([[4, 5], [4, 6], [6, 7], [2, 3], [1, 1]]) == 4
assert max_envelopes([[1, 1], [1, 1], [1, 1]]) == 1
assert max_envelopes([[7, 8]]) == 1
assert max_envelopes([[3, 3], [3, 4]]) == 1                       # 同寬不能互套
assert max_envelopes([[i, i] for i in range(1, 10**5 + 1)]) == 10**5
for _ in range(500):
    e = [[random.randint(1, 6), random.randint(1, 6)] for _ in range(random.randint(1, 8))]
    assert max_envelopes(e) == brute(e)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n log n)：排序一次，之後每個信封一次 binary search。空間 O(n)，用於排序後的副本與 `tails`。邊界情況：所有信封相同時，排序後高度全部相等，每次 `bisect_left` 都回到位置 0，答案 1；寬度全部相同時，高度遞減排列，答案也是 1；高度相同而寬度不同時（`[[1, 5], [2, 5]]`），嚴格遞增讓它們不能互套，`bisect_left` 正確處理。兩個關鍵細節缺一不可：同寬高度遞減、LIS 用 `bisect_left`（嚴格）。

### Follow-up

> [!question]- F1. 如果信封可以旋轉（寬高互換）呢？
> 先把每個信封正規化成 `(min(w, h), max(w, h))`，再跑原本的演算法。理由是：設 a₁ ≤ a₂、b₁ ≤ b₂，若 a 旋轉後能放進 b，也就是 a₁ < b₂ 且 a₂ < b₁，那麼 a₁ ≤ a₂ < b₁ ≤ b₂，於是 a₁ < b₁ 且 a₂ < b₂ 也成立。所以「某種旋轉能放進去」等價於「正規化後能放進去」，只要比較正規化的版本。時間仍是 O(n log n)。這個論證只適用於二維；三維的箱子允許旋轉時，正規化（三邊排序）同樣成立，但三維本身就不能用 LIS 技巧（見 F2）。

> [!question]- F2. 如果是三維的箱子（長、寬、高都要嚴格更小）呢？
> 排序只能消掉一個維度，剩下的兩個維度要同時遞增，patience sorting 無法處理，因為 `tails` 只能依一個值排序。直接的做法是依第一維排序後做 O(n²) DP（1691 題 Maximum Height by Stacking Cuboids 就是這樣，n ≤ 100）。n 很大時，問題變成三維偏序上的最長鏈，可以用 CDQ 分治搭配 Fenwick tree，O(n log² n)，這已經超出一般面試的範圍，但說得出「二維靠排序 + LIS、三維要分治或 O(n²)」就足夠展現理解。

> [!question]- F3. 如果改成「寬和高都小於等於」就能套（非嚴格）呢？
> 同寬的信封現在可以互套（只要高度不大於），所以排序改成寬度遞增、同寬時高度**遞增**，再對高度做非嚴格遞增的 LIS，也就是改用 `bisect_right`。正確性論證和原題對稱：排序後任何非嚴格遞增的高度子序列，寬度也是非嚴格遞增，都能套；任何合法的套法也是這樣的子序列。時間 O(n log n)。這個 follow-up 在檢查你是否理解「遞減排序」和「`bisect_left`」各自是為了處理哪一種「相等」。

> [!question]- F4. 如果每個信封有一個價值，要最大化套在一起的信封總價值呢？
> 這是帶權重的 LIS，`tails` 的「最小結尾」貪婪不再成立，因為長度最長不代表價值最大。改成在高度的值域上維護「以高度 ≤ h 結尾的最大總價值」：依同樣規則排序後，對每個信封查詢高度 < h 的前綴最大值，加上自己的價值，再更新到位置 h。用 Fenwick tree（第 26 章）做前綴 max，每個信封 O(log H)，總時間 O(n log n + n log H)。同寬高度遞減的排序仍然保證同寬的信封不會互相接上，因為高度大的先處理、高度小的查詢不到它。
> ```python
> def max_value_nesting(envs):                   # envs: (w, h, value)
>     envs = sorted(envs, key=lambda e: (e[0], -e[1]))
>     size = max(h for _, h, _ in envs)
>     tree = [0] * (size + 1)
>     best = 0
>     for _, h, v in envs:
>         i, cur = h - 1, 0
>         while i > 0:                            # 前綴 max：高度 <= h-1
>             cur, i = max(cur, tree[i]), i - (i & -i)
>         cur += v
>         best = max(best, cur)
>         i = h
>         while i <= size:
>             tree[i], i = max(tree[i], cur), i + (i & -i)
>     return best
> ```

> [!question]- F5. 如果要輸出實際的套娃順序呢？
> 和核心題 3 的 F1 相同：在 patience sorting 中改存排序後的索引 `tails_idx`，並為每個信封記錄 `parent`（放入時它前一格的 `tails_idx`），最後從 `tails_idx[-1]` 沿 `parent` 回溯，得到從最外層到最內層的序列，反轉後輸出。因為 `parent` 是在放入當下記錄的，那個信封在排序後的位置較前、高度較小，而且依詳解中的論證寬度也較小，所以還原出來的每一對都能真的互套。時間仍是 O(n log n)。

### 心得

關鍵突破是「寬度遞增、同寬高度遞減」這個排序，它把二維的偏序問題變成一維的 LIS：遞減讓同寬的信封在高度上互相排斥，嚴格遞增的 `bisect_left` 再保證高度也嚴格變大。它和核心題 3 是同一個演算法，只是多了一步把問題「降維」的觀察；這也是 LIS 最常見的考法：先排序消掉一個維度，再對另一個維度做 LIS（1626 Best Team With No Conflicts、646 Maximum Length of Pair Chain 也是這個思路）。面試時先說 O(n²) 的二維 DP 作為基準，再指出 n = 10⁵ 需要 O(n log n)，然後用 `[[3, 3], [3, 4]]` 這個反例解釋為什麼同寬要遞減排序，這個反例最能讓面試官確信你懂。

## 難題 3｜403. Frog Jump｜Hard

### 題目

一隻青蛙要過河，河中有一些石頭，位置由遞增的陣列 `stones` 給出，`stones[0] = 0` 是起點，最後一顆石頭是對岸。青蛙一開始站在第一顆石頭上，**第一跳必須跳 1 個單位**；之後若上一跳的距離是 k，下一跳只能是 k − 1、k 或 k + 1（必須是正數），而且只能往前跳、必須落在石頭上。請判斷青蛙能不能跳到最後一顆石頭。限制：`2 <= n <= 2000`，`0 <= stones[i] <= 2³¹ − 1`，`stones[0] = 0`，位置嚴格遞增。

- 範例 1：`stones = [0, 1, 3, 5, 6, 8, 12, 17]`，回傳 `True`：跳 1、2、2、3、4、5，依序經過 0 → 1 → 3 → 5 → 8 → 12 → 17。
- 範例 2：`stones = [0, 1, 2, 3, 4, 8, 9, 11]`，回傳 `False`：4 到 8 的距離是 4，但青蛙到 4 時上一跳最多是 2。
- 範例 3（邊界）：`stones = [0, 2]`，回傳 `False`，第一跳只能是 1。
- 範例 4（邊界）：`stones = [0, 1]`，回傳 `True`。

### 提示

> [!tip]- 提示 1
> 只知道「青蛙能不能站在某顆石頭上」夠不夠？站在同一顆石頭上、但上一跳距離不同，未來能去的地方一樣嗎？

> [!tip]- 提示 2
> 狀態是 (石頭, 上一跳的距離)。站在第 i 顆石頭時，上一跳距離最多是 i（每跳最多比前一跳多 1，第一跳是 1），所以狀態總數是 O(n²)。

> [!tip]- 提示 3
> 依位置順序處理石頭，對每顆石頭維護一個集合「能以哪些距離跳到這裡」。對集合中的每個 k，嘗試 k − 1、k、k + 1，若目標位置有石頭就把距離加進目標的集合。最後檢查終點的集合是否非空。

### 詳解

**為什麼直覺做法不行**。最直接的 DP 是 `dp[i]` = 「能不能站上第 i 顆石頭」，但這個狀態**資訊不足**：能不能從第 i 顆跳到第 j 顆，取決於到達 i 時的上一跳距離。例如範例 1 中，青蛙可以用距離 3（從 3 跳過來）或距離 1（從 5 跳過來）站上位置 6；前者下一跳可以是 2、3、4，後者只能是 1、2。只記「到得了 6」就會丟失這個差別，可能把不可行的跳法當成可行。暴力的 DFS 則在每顆石頭最多有 3 個分支，沒有記憶化時是 O(3ⁿ)。

**突破點：把上一跳的距離放進狀態**。照 21.4 節的原則問：「站在這顆石頭做下一個決定時，未來需要知道過去的什麼？」答案是上一跳的距離 k，而且**只需要** k，不需要更早的歷史。所以狀態是 (stone, k)。能否到達終點只依賴目前的 (stone, k)，有大量重疊：不同的跳法可能以同樣的距離到達同一顆石頭。狀態數的上界：到達第 i 顆石頭（索引）時，已經跳了至多 i 次，每次距離最多比前一次多 1、第一次是 1，所以 k ≤ i，狀態總數 O(n²) = 4 × 10⁶，可以接受。

**計算順序**。青蛙只往前跳，所以 (stone, k) 只會轉移到位置更大的石頭，依位置由小到大處理就是合法的拓撲順序。實作上用一個 dict 把位置對應到「能以哪些距離到達」的集合，起點的集合是 `{0}`，這樣從起點嘗試 0 − 1、0、0 + 1 時只有 1 是正數，自然滿足「第一跳必須是 1」。處理到某顆石頭時，它的集合已經完整（所有能跳到它的都在更前面），對每個 k 嘗試三種跳法，目標位置存在就把距離加入目標的集合。

**提早結束的剪枝**。若某相鄰兩顆石頭的距離 `stones[i] − stones[i − 1] > i`，答案一定是 False：任何越過這段空隙的一跳，起點都是某顆索引 ≤ i − 1 的石頭，那一跳的距離最多是 (i − 1) + 1 = i，跨不過去。這個檢查是 O(n)，可以在 DP 前先做，對「中間有大空隙」的輸入省下大量時間。範例 2 的失敗原因更細：4 到 8 的空隙是 4，而 8 的索引是 5，檢查 `4 > 5` 不成立，剪枝不會觸發；但 DP 會算出到達 4 的距離只有 {1, 2}，下一跳最多 3。

```text
stones = [0, 1, 3, 5, 6, 8, 12, 17]
表格：每顆石頭「能以哪些距離跳到這裡」，依位置順序填寫

石頭  集合 K   對每個 k 嘗試 k-1, k, k+1                 寫入
 0    {0}     k=0：1 → 位置 1 ✓                           1 ← 1
 1    {1}     k=1：0✗(非正)、1→2 ✗、2→3 ✓                 3 ← 2
 3    {2}     k=2：1→4 ✗、2→5 ✓、3→6 ✓                    5 ← 2，6 ← 3
 5    {2}     k=2：1→6 ✓、2→7 ✗、3→8 ✓                    6 ← 1，8 ← 3
 6    {1, 3}  k=1：1→7 ✗、2→8 ✓                           8 ← 2
              k=3：2→8 ✓(已有)、3→9 ✗、4→10 ✗
 8    {2, 3}  k=2：1→9、2→10、3→11 都 ✗
              k=3：2→10 ✗、3→11 ✗、4→12 ✓                 12 ← 4
12    {4}     k=4：3→15 ✗、4→16 ✗、5→17 ✓                 17 ← 5
17    {5}     終點集合非空 → True

路徑回溯：17 ←(5) 12 ←(4) 8 ←(3) 5 ←(2) 3 ←(2) 1 ←(1) 0
```

位置 6 的集合 `{1, 3}` 就是「只記能否到達」會出錯的地方：從 6 以距離 3 到達時可以跳 4 到 10，以距離 1 到達時不行。在這個例子中兩種都沒用上，真正通往終點的路徑走的是 5 → 8（距離 3），然後 8 → 12（距離 4）、12 → 17（距離 5），每一步都把距離加 1。

### 解法

```python
import random
from functools import cache


def can_cross(stones: list[int]) -> bool:
    for i in range(1, len(stones)):
        if stones[i] - stones[i - 1] > i:        # 這段空隙任何一跳都跨不過
            return False
    reach = {s: set() for s in stones}           # 位置 → 能以哪些距離跳到這裡
    reach[0].add(0)
    for s in stones:                             # 依位置遞增：合法的計算順序
        for k in reach[s]:
            for step in (k - 1, k, k + 1):
                if step > 0 and s + step in reach:
                    reach[s + step].add(step)
    return bool(reach[stones[-1]])


def can_cross_memo(stones: list[int]) -> bool:
    pos, last = set(stones), stones[-1]

    @cache
    def go(s: int, k: int) -> bool:              # 站在 s、上一跳 k，能否到終點
        if s == last:
            return True
        return any(go(s + step, step) for step in (k + 1, k, k - 1)
                   if step > 0 and s + step in pos)

    return go(0, 0)


def brute(stones):
    pos, last = set(stones), stones[-1]

    def go(s, k):
        if s == last:
            return True
        return any(go(s + st, st) for st in (k - 1, k, k + 1) if st > 0 and s + st in pos)
    return go(0, 0)


assert can_cross([0, 1, 3, 5, 6, 8, 12, 17]) is True
assert can_cross([0, 1, 2, 3, 4, 8, 9, 11]) is False
assert can_cross([0, 2]) is False
assert can_cross([0, 1]) is True
assert can_cross(list(range(2000))) is True       # 每跳 1，O(n²) 個狀態也很快
for _ in range(500):
    n = random.randint(2, 9)
    st = [0] + sorted(random.sample(range(1, 20), n - 1))
    assert can_cross(st) == can_cross_memo(st) == brute(st)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n²)：狀態 (石頭, 距離) 最多 O(n²) 個，每個做 3 次 O(1) 的 hash 查詢。空間 O(n²)，最壞情況每顆石頭的集合都有 O(n) 個距離。邊界情況：第一跳只能是 1，用起點集合 `{0}` 自然處理，`[0, 2]` 會因為 1 不是石頭而失敗；`step > 0` 排除了 k = 1 時的 0 距離（原地跳）；位置可達 2³¹ − 1，用 dict 而不是以位置為索引的陣列；top-down 版本的遞迴深度最多 n = 2000，超過 Python 的預設限制，實際使用要調高或改用 bottom-up，這也是為什麼主解法用 bottom-up。

### Follow-up

> [!question]- F1. 如果要問「最少跳幾次」才能到終點呢？
> 每一跳的成本都是 1，所以在狀態圖 (石頭, 距離) 上做 BFS（第 15 章），第一次到達終點的層數就是答案，O(n²)。也可以沿用本題的 DP 順序：因為只往前跳，狀態圖是 DAG，依位置順序做 `dist[(s + step, step)] = min(dist[(s + step, step)], dist[(s, k)] + 1)` 也正確，同樣 O(n²)。例如範例 1 最少要 6 跳；`[0, 1, 2, 3, 4, 5, 6]` 最少 3 跳（1、2、3）。這說明了 BFS 和 DP 在 DAG 上的等價性：DP 是依拓撲順序鬆弛，BFS 是依距離順序鬆弛。

> [!question]- F2. 如果要輸出一條可行的跳法呢？
> 在把 step 加進 `reach[s + step]` 時，同時記錄 `parent[(s + step, step)] = (s, k)`（只在第一次加入時記錄）。到達終點後，從終點集合中任取一個距離 k，沿著 parent 回溯到 `(0, 0)`，再反轉就是石頭序列。額外空間 O(n²)，回溯 O(n)。若要所有可行跳法，路徑數可能是指數級，只能在「能到達終點」的狀態子圖上做 DFS 逐一列出。

> [!question]- F3. 如果青蛙也可以往回跳呢？
> 往回跳讓狀態圖出現環（例如往前跳 2、再往回跳 2），「依位置順序」不再是合法的計算順序，DP 不能直接用。這時要把它當成一般的圖搜尋：在 (石頭, 距離) 上做 BFS 或 DFS，用 visited 集合避免重複訪問，仍是 O(n²) 個狀態。這個 follow-up 點出了 DP 的前提：狀態之間的依賴必須是 DAG；只要有環，就要換成圖演算法（第 15、18 章）。

> [!question]- F4. 如果每一跳的成本是距離的平方，要最小化總成本呢？
> 這是 (石頭, 距離) 狀態圖上的最短路。一般帶權最短路需要 Dijkstra（第 18 章），但這張圖是 DAG（只往前跳），所以依位置順序做一次 DP 鬆弛就夠：`cost[(s + step, step)] = min(cost[(s + step, step)], cost[(s, k)] + step²)`，答案是終點所有狀態的最小值，O(n²)，比 Dijkstra 的 O(n² log n) 少一個 log。能說出「DAG 上的最短路用拓撲順序 DP，不需要 Dijkstra」，代表你理解 DP 和最短路的關係。

> [!question]- F5. 為什麼「上一跳的距離最多是 i」？這個上界對複雜度有什麼影響？
> 到達索引為 i 的石頭時，青蛙最多跳了 i 次（每次至少前進一顆石頭）；第一跳是 1，之後每跳最多比前一跳多 1，所以第 t 跳的距離最多是 t ≤ i。因此每顆石頭的集合最多 i 個元素，總狀態數 Σ i = O(n²)，這是本題 O(n²) 複雜度的來源。若沒有這個上界（例如題目允許第一跳任意長），狀態數就要以「位置差的種類」來估計，最多仍是 O(n²)，因為一跳的距離一定是某兩顆石頭的位置差，所以 (石頭, 距離) 的組合數不超過石頭對的數量。

### 心得

關鍵突破是「位置不夠，要加上上一跳的距離」，這是 21.4 節「未來需要知道什麼就放進狀態」最直接的例子；狀態數的上界 k ≤ i 則讓 O(n²) 有了保證。它和本章其他題的關係是：核心題 1–5 的狀態都只有一個索引或數值，這題示範了一維 DP 何時必須「加一維」；而依位置順序處理、用 dict 存稀疏狀態的寫法，和 top-down 記憶化只計算可達狀態是同一個想法。面試時先指出 `dp[stone]` 為什麼不夠（舉出位置 6 有兩種距離的例子），再說明狀態 (stone, k) 和它的上界，最後提出 O(n) 的空隙剪枝，三步講完，整個解法就很有說服力。

## 難題 4｜1235. Maximum Profit in Job Scheduling｜Hard

### 題目

有 n 份工作，第 i 份從 `startTime[i]` 開始、在 `endTime[i]` 結束，完成可得 `profit[i]`。你要挑選一些**時間互不重疊**的工作，使總收益最大。如果一份工作在時間 X 結束，另一份恰好在 X 開始，兩者不算重疊，可以同時選。限制：`1 <= n <= 5 × 10⁴`，`1 <= startTime[i] < endTime[i] <= 10⁹`，`1 <= profit[i] <= 10⁴`。

- 範例 1：`startTime = [1, 2, 3, 3]`、`endTime = [3, 4, 5, 6]`、`profit = [50, 10, 40, 70]`，回傳 `120`（選 [1, 3] 與 [3, 6]，50 + 70）。
- 範例 2：`startTime = [1, 2, 3, 4, 6]`、`endTime = [3, 5, 10, 6, 9]`、`profit = [20, 20, 100, 70, 60]`，回傳 `150`（選 [1, 3]、[4, 6]、[6, 9]）。
- 範例 3：`startTime = [1, 1, 1]`、`endTime = [2, 3, 4]`、`profit = [5, 6, 4]`，回傳 `6`，三份工作兩兩重疊，只能選一份。
- 範例 4（邊界）：只有一份工作時回傳它的收益。

### 提示

> [!tip]- 提示 1
> 沒有權重時（每份工作價值相同），「依結束時間排序、能選就選」的貪婪是最佳的（第 9 章、第 20 章）。有權重時這個貪婪為什麼失效？

> [!tip]- 提示 2
> 依結束時間排序後，對第 i 份工作只有兩個選擇：不選它，答案和前 i − 1 份相同；選它，就只能再搭配「結束時間 ≤ 它的開始時間」的那些工作。後者在排序後是一段前綴。

> [!tip]- 提示 3
> `dp[i] = max(dp[i − 1], profit_i + dp[p(i)])`，其中 p(i) = 結束時間 ≤ `start_i` 的工作個數，用 `bisect_right(ends, start_i)` 在 O(log n) 找到。總時間 O(n log n)。

### 詳解

**為什麼直覺做法不行**。無權重的區間排程（最多選幾個不重疊區間）可以用「結束最早的先選」的貪婪解決，但有權重時，一份結束得早卻很便宜的工作，可能擋掉一份很賺的工作。範例 2 中，如果貪婪先選結束最早的 [1, 3]（20），再選 [4, 6]（70）、[6, 9]（60），剛好得到 150；但只要把 [3, 10] 的收益改成 1000，最佳解就變成 [1, 3] + [3, 10] = 1020，貪婪仍然選 150 的那一組。依收益排序的貪婪也一樣容易舉出反例。暴力解列舉所有子集，O(2ⁿ · n)。

**突破點：排序後變成「選或不選」的一維 DP**。依結束時間排序之後，定義 `dp[i]` = 「只考慮前 i 份工作（結束時間最早的 i 份）時的最大收益」。看第 i 份工作（排序後的第 i 份）：不選它，答案是 `dp[i − 1]`；選它，那麼其他被選的工作都必須在它開始之前結束，也就是結束時間 ≤ `start_i`。因為工作依結束時間排序，這些工作恰好是一段前綴，長度 `p(i) = bisect_right(ends, start_i)`，而這段前綴中能挑到的最大收益就是 `dp[p(i)]`。所以 `dp[i] = max(dp[i − 1], profit_i + dp[p(i)])`。這和 House Robber 的「選或不選」是同一個形狀，只是「上一個能搭配的位置」不再是固定的 i − 2，而要用 binary search 找。

**為什麼 p(i) ≤ i − 1、轉移合法**。結束時間 ≤ `start_i` 的工作，結束時間都嚴格小於 `end_i`（因為 `start_i < end_i`），所以它們在排序中都排在第 i 份之前，p(i) 不會把第 i 份自己或它後面的工作算進來，即使有多份工作的結束時間相同也一樣。而 `dp[p(i)]` 只用到這段前綴，其中每份工作都不和第 i 份重疊，選了它們再加上第 i 份一定合法。反過來，任何包含第 i 份的合法方案，其他工作都在這段前綴裡，收益不超過 `dp[p(i)] + profit_i`。所以轉移既不會漏掉方案，也不會產生非法方案。

```text
範例 2：依結束時間排序
編號  (start, end, profit)
 1    (1, 3, 20)
 2    (2, 5, 20)
 3    (4, 6, 70)
 4    (6, 9, 60)
 5    (3, 10, 100)
ends = [3, 5, 6, 9, 10]

dp[i] = max(dp[i-1], profit_i + dp[p(i)])，p(i) = bisect_right(ends, start_i)

i  工作          p(i) = bisect_right(ends, start)   不選 dp[i-1]   選 profit+dp[p]    dp[i]
0  -             -                                  -              -                  0
1  (1, 3, 20)    bisect_right(ends, 1) = 0           0             20 + dp[0] = 20     20
2  (2, 5, 20)    bisect_right(ends, 2) = 0          20             20 + dp[0] = 20     20
3  (4, 6, 70)    bisect_right(ends, 4) = 1          20             70 + dp[1] = 90     90
4  (6, 9, 60)    bisect_right(ends, 6) = 3          90             60 + dp[3] = 150   150
5  (3, 10, 100)  bisect_right(ends, 3) = 1         150            100 + dp[1] = 120   150
答案 dp[5] = 150

回溯：dp[5] = dp[4] → 不選 5；dp[4] ≠ dp[3] → 選 4，跳到 dp[p(4)] = dp[3]
      dp[3] ≠ dp[2] → 選 3，跳到 dp[1]；dp[1] ≠ dp[0] → 選 1
方案 = {(1,3), (4,6), (6,9)}
```

第 4 列是 `bisect_right` 的關鍵：工作 (6, 9) 的開始時間 6 恰好等於 (4, 6) 的結束時間，題目允許這兩份相接，所以要找「結束時間 ≤ 6」的工作，用 `bisect_right`；若誤用 `bisect_left`，p(4) 會變成 2，(4, 6) 被排除，`dp[4]` 只剩 max(90, 60 + dp[2] = 80) = 90，最終答案也會跟著算錯。第 5 列的工作 (3, 10) 收益最高，但它和 (4, 6)、(6, 9) 重疊，選它只能搭配 (1, 3)，總共 120，不如不選。

### 解法

```python
import bisect
import random


def job_scheduling(start_time: list[int], end_time: list[int], profit: list[int]) -> int:
    jobs = sorted(zip(start_time, end_time, profit), key=lambda t: t[1])
    ends = [e for _, e, _ in jobs]
    dp = [0] * (len(jobs) + 1)                   # dp[i] = 前 i 份工作（依結束時間）的最大收益
    for i, (s, _, p) in enumerate(jobs, 1):
        k = bisect.bisect_right(ends, s)         # 結束時間 <= s 的工作個數
        dp[i] = max(dp[i - 1], dp[k] + p)
    return dp[-1]


def brute(s, e, p):
    n, best = len(s), 0
    for mask in range(1 << n):
        chosen = sorted((s[i], e[i]) for i in range(n) if mask >> i & 1)
        if all(chosen[t][1] <= chosen[t + 1][0] for t in range(len(chosen) - 1)):
            best = max(best, sum(p[i] for i in range(n) if mask >> i & 1))
    return best


assert job_scheduling([1, 2, 3, 3], [3, 4, 5, 6], [50, 10, 40, 70]) == 120
assert job_scheduling([1, 2, 3, 4, 6], [3, 5, 10, 6, 9], [20, 20, 100, 70, 60]) == 150
assert job_scheduling([1, 1, 1], [2, 3, 4], [5, 6, 4]) == 6
assert job_scheduling([5], [10], [7]) == 7
assert job_scheduling([1, 2, 3, 4, 6], [3, 5, 10, 6, 9], [20, 20, 1000, 70, 60]) == 1020
for _ in range(500):
    n = random.randint(1, 7)
    s = [random.randint(1, 10) for _ in range(n)]
    e = [x + random.randint(1, 5) for x in s]
    p = [random.randint(1, 20) for _ in range(n)]
    assert job_scheduling(s, e, p) == brute(s, e, p)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n log n)：排序 O(n log n)，之後每份工作一次 binary search。空間 O(n)，用於排序後的工作、`ends` 與 `dp`。邊界情況：相接的工作（結束 = 開始）可以同時選，所以用 `bisect_right`；多份工作結束時間相同時，排序後彼此相鄰，`bisect_right(ends, s)` 只會算到結束時間 ≤ s 的那些，不會包含它們自己（因為 s < 自己的結束時間）；時間值到 10⁹，DP 以工作為索引而不是以時間為索引，所以值域大小不影響複雜度。

### Follow-up

> [!question]- F1. 如果要回傳實際選了哪些工作呢？
> 保留 `dp` 陣列與每份工作的 p(i)，從 i = n 往回走：若 `dp[i] == dp[i − 1]`，第 i 份沒選，令 i −= 1；否則第 i 份被選，記下它並跳到 i = p(i)。回溯 O(n)，因為每一步 i 至少減 1。上面的視覺化示範了這個過程。注意跳的目標是 p(i) 而不是 i − 2，這是它和 House Robber（核心題 1 F2）回溯的唯一差別；兩者的結構完全相同，都是「選或不選，選了就跳到上一個相容的位置」。

> [!question]- F2. 如果最多只能選 k 份工作呢（1751. Maximum Number of Events That Can Be Attended II 的形式）？
> 狀態多一維：`dp[j][i]` = 前 i 份工作中最多選 j 份的最大收益，`dp[j][i] = max(dp[j][i − 1], profit_i + dp[j − 1][p(i)])`。p(i) 與 j 無關，先算好存起來，之後每層 O(n)，總時間 O(n log n + n · k)，空間可以只保留兩層 O(n)。注意 1751 題的事件是**閉區間**，同一天結束和開始的事件不能同時參加，所以 p(i) 要改成 `bisect_left(ends, start_i)`（結束時間嚴格小於開始時間）。題目的「相接算不算重疊」只影響 left 或 right 的選擇，但這正是最容易錯的地方。

> [!question]- F3. 如果所有工作的收益都一樣，問最多能選幾份呢？
> 這時貪婪就是最佳的：依結束時間排序，能選就選（目前工作的開始時間 ≥ 上一份被選工作的結束時間），O(n log n)。正確性是交換論證：最佳解的第一份工作可以換成結束最早的工作而不影響後面（它結束得更早，留下的空間只會更多），歸納下去即可。這就是 435. Non-overlapping Intervals（第 9 章核心題 3）的反面。面試時能說清楚「權重相同時貪婪成立、權重不同時要 DP」，代表你理解兩個 pattern 的分界。

> [!question]- F4. 如果時間的範圍很小（例如所有時間都 ≤ 10⁵），能不能不排序工作？
> 可以改成以時間為狀態：`dp[t]` = 到時間 t 為止的最大收益，`dp[t] = max(dp[t − 1], max(dp[start] + profit for 結束於 t 的工作))`。先把工作依結束時間分桶，總時間 O(T + n)，T 是時間上限。2008. Maximum Earnings From Taxi 就是這個形式（乘客 i 的收益是 `end − start + tip`）。時間範圍大時，把出現過的時間點做座標壓縮，就回到 O(n log n)。兩種寫法的選擇取決於「工作數」和「時間範圍」哪個小，這也是第 3 章「從限制推 pattern」的應用。

> [!question]- F5. 如果工作依結束時間遞增的順序陸續到來，要隨時回報目前的最大收益呢？
> 本題的 DP 天生就是線上的：維護兩個平行陣列 `ends` 與 `best`（`best[i]` 是前 i 份工作的最佳值，對 i 非遞減）。新工作 (s, e, p) 到來時，用 `bisect_right(ends, s)` 找到 k，候選值是 `best[k] + p`，與目前最佳值取 max 後 append，每份工作 O(log n)。若工作以**任意順序**到來，前綴結構會被破壞，要改用以時間為鍵的 balanced BST 或 segment tree（第 26 章），維護「結束時間 ≤ t 的最大收益」，每次插入與查詢 O(log n)；但插入一份新工作可能改變之後所有時間點的答案，需要支援區間更新，複雜度與實作難度都明顯上升。

### 心得

關鍵突破是「依結束時間排序」：排序之後，「選這份工作時還能搭配哪些工作」恰好是一段前綴，於是帶權重的區間排程變成和 House Robber 一樣的「選或不選」，前驅位置則用 binary search 找。它和本章其他題的關係是：核心題 1 的前驅是固定的 i − 2，這題的前驅是 `bisect_right` 找到的 p(i)；難題 2 的 354 也是「先排序再 DP」，排序都是為了讓相容的元素形成有序的結構。面試時先舉一個貪婪的反例（把長工作的收益調大），再說明排序後的兩種選擇，最後強調 `bisect_right` 是因為相接不算重疊，這個細節面試官幾乎一定會確認。

## 難題 5｜1335. Minimum Difficulty of a Job Schedule｜Hard

### 題目

有 n 份工作必須**依序**完成（要做第 i 份，必須先完成第 0 到 i − 1 份），第 i 份的難度是 `jobDifficulty[i]`。你要把這些工作安排在 d 天內完成，每天至少做一份；一天的難度是當天所做工作中的**最大**難度，整個排程的難度是 d 天難度的**總和**。請回傳最小的排程難度；如果無法安排（工作數少於天數），回傳 `-1`。限制：`1 <= n <= 300`，`0 <= jobDifficulty[i] <= 1000`，`1 <= d <= 10`。

- 範例 1：`jobDifficulty = [6, 5, 4, 3, 2, 1]`、`d = 2`，回傳 `7`：第一天做前 5 份（最大 6），第二天做最後一份（1）。
- 範例 2：`jobDifficulty = [9, 9, 9]`、`d = 4`，回傳 `-1`，三份工作排不滿四天。
- 範例 3：`jobDifficulty = [7, 1, 7, 1, 7, 1]`、`d = 3`，回傳 `15`，例如 `[7, 1] | [7, 1] | [7, 1]`，7 + 7 + 1 = 15。
- 範例 4（邊界）：`jobDifficulty = [1, 1, 1]`、`d = 3`，回傳 `3`，每天一份；`d = 1` 時答案是 `max(jobDifficulty)`。

### 提示

> [!tip]- 提示 1
> 這是「把陣列切成恰好 d 段連續子陣列，最小化各段最大值的總和」。和第 8 章難題 2 的 410（最小化各段總和的最大值）比較：為什麼這題不能用 binary search 答案？

> [!tip]- 提示 2
> 狀態需要兩個資訊：已經安排了幾天、已經做完前幾份工作。`dp[k][i]` = 用 k 天做完前 i 份工作的最小難度。轉移時枚舉最後一天從哪一份工作開始。

> [!tip]- 提示 3
> `dp[k][i] = min over j (dp[k − 1][j] + max(jd[j..i − 1]))`，j 從 i − 1 往回枚舉，同時維護區間最大值，每個 (k, i) 是 O(n)，總共 O(d · n²) ≈ 9 × 10⁵。進一步可以用 monotonic stack 降到 O(d · n)。

### 詳解

**為什麼直覺做法不行**。和 410 比較最能看出差別：410 是「最小化各段總和的**最大值**」，可行性「每段 ≤ X」對 X 單調，所以能二分答案加貪婪檢查；這題是「最小化各段最大值的**總和**」，沒有一個單一的門檻可以檢查，每一段的代價都會累加到答案裡，二分答案無從下手。貪婪也不行：例如「把最難的工作單獨放一天」在範例 1 中正確，但在 `[1, 10, 1, 10]`、d = 2 時，切成 `[1, 10] | [1, 10]` 得 20，而 `[1] | [10, 1, 10]` 只有 11，貪婪很難找到這種切法。暴力枚舉 d − 1 個切點是 C(n − 1, d − 1)，n = 300、d = 10 時約 4.7 × 10¹⁶，不可行。

**狀態與轉移**。依 21.4 節的方法，暴力遞迴是「從第 i 份工作開始，還剩 k 天，最少難度多少」，參數 (i, k) 只有 n · d 種組合，所以可以 DP。bottom-up 版本定義 `dp[k][i]` = 「用恰好 k 天做完前 i 份工作的最小難度」，不可能時為 +∞。看**最後一天**：它做的是第 j 到第 i − 1 份工作（j ≤ i − 1），難度是 `max(jd[j..i − 1])`；前 j 份工作必須用 k − 1 天完成，最少 `dp[k − 1][j]`，而且每天至少一份工作，所以 j ≥ k − 1。於是 `dp[k][i] = min_{k−1 ≤ j ≤ i−1} (dp[k − 1][j] + max(jd[j..i − 1]))`，base case `dp[0][0] = 0`，其他 `dp[0][i] = +∞`。答案是 `dp[d][n]`。

**計算區間最大值**。直接對每個 (k, i, j) 重算 `max(jd[j..i − 1])` 會多一個 O(n)，變成 O(d · n³)。技巧是讓 j 從 i − 1 **往回**枚舉，同時維護一個變數 `m = max(m, jd[j])`，每多看一個 j，區間就向左延伸一格，最大值 O(1) 更新。這樣每個 (k, i) 只需 O(n)，總共 O(d · n²) = 10 × 300² = 9 × 10⁵，很快。這是形狀 F（分段 DP）的標準寫法，第 8 章難題 2 的 410 也有一個 O(k · n²) 的同型 DP。

```text
jobDifficulty = [7, 1, 7, 1, 7, 1]，d = 3
dp[k][i] = 用 k 天做完前 i 份工作的最小難度（∞ = 不可能）

           i=1   i=2   i=3   i=4   i=5   i=6
k=1          7     7     7     7     7     7      （前綴最大值）
k=2          ∞     8    14     8    14     8
k=3          ∞     ∞    15    15    15    15      → 答案 dp[3][6] = 15

k=2 的幾格（j 從 i-1 往回，m 是最後一天的最大值）：
dp[2][2]：j=1 → dp[1][1] + max(1)       = 7 + 1  = 8
dp[2][3]：j=2 → dp[1][2] + max(7)       = 7 + 7  = 14
          j=1 → dp[1][1] + max(1, 7)    = 7 + 7  = 14            → 14
dp[2][4]：j=3 → dp[1][3] + max(1)       = 7 + 1  = 8             → 8
          （j=2、1 時最後一天含 7，都是 14）
k=3 的最後一格：
dp[3][6]：j=5 → dp[2][5] + max(1)       = 14 + 1 = 15
          j=4 → dp[2][4] + max(7, 1)    = 8 + 7  = 15
          j=3 → dp[2][3] + max(1, 7, 1) = 14 + 7 = 21
          j=2 → dp[2][2] + max(7,1,7,1) = 8 + 7  = 15            → 15
```

`k = 2` 那一列呈現「8、14 交錯」：前 i 份工作若以 1 結尾，可以讓最後一天只做那個 1，難度 7 + 1 = 8；若以 7 結尾，最後一天必然含 7，只能是 7 + 7 = 14。到了 `k = 3`，最佳值都是 15，最後一格有三種切法都達到 15，例如 `[7, 1] | [7, 1, 7] | [1]` 和 `[7] | [1] | [7, 1, 7, 1]`。

### 解法

```python
import random
from functools import cache


def min_difficulty(job_difficulty: list[int], d: int) -> int:
    n = len(job_difficulty)
    if n < d:
        return -1
    INF = float("inf")
    prev = [0] + [INF] * n                       # dp[0][i]：0 天只能做完 0 份工作
    for k in range(1, d + 1):
        cur = [INF] * (n + 1)
        for i in range(k, n + 1):                # 至少 k 份工作才排得滿 k 天
            m = 0
            for j in range(i - 1, k - 2, -1):    # 最後一天做 jd[j..i-1]，j >= k-1
                m = max(m, job_difficulty[j])
                if prev[j] + m < cur[i]:
                    cur[i] = prev[j] + m
        prev = cur
    return prev[n]


def brute(jd, d):
    n = len(jd)

    @cache
    def go(i, k):                                # 從第 i 份開始、還剩 k 天
        if k == 0:
            return 0 if i == n else float("inf")
        best, m = float("inf"), 0
        for j in range(i, n - k + 1):            # 今天做 jd[i..j]，後面每天至少一份
            m = max(m, jd[j])
            best = min(best, m + go(j + 1, k - 1))
        return best

    res = go(0, d)
    return -1 if res == float("inf") else res


assert min_difficulty([6, 5, 4, 3, 2, 1], 2) == 7
assert min_difficulty([9, 9, 9], 4) == -1
assert min_difficulty([7, 1, 7, 1, 7, 1], 3) == 15
assert min_difficulty([1, 1, 1], 3) == 3
assert min_difficulty([1, 10, 1, 10], 2) == 11
assert min_difficulty([11, 111, 22, 222, 33, 333, 44, 444], 6) == 843
assert min_difficulty([0], 1) == 0
for _ in range(500):
    jd = [random.randint(0, 9) for _ in range(random.randint(1, 9))]
    dd = random.randint(1, 5)
    assert min_difficulty(jd, dd) == brute(jd, dd)
print("all tests passed")
```

### 複雜度與邊界

時間 O(d · n²)：d 層，每層 n 個 i，每個 i 往回枚舉最多 n 個 j，區間最大值隨 j 延伸 O(1) 更新。空間 O(n)，只保留上一層與這一層。邊界情況：n < d 時直接回傳 −1；j 的下界 k − 1 保證前 k − 1 天每天至少一份，否則會用到 `dp[k − 1][j] = ∞` 的格子，雖然結果仍正確，但白白浪費時間；難度可以是 0，所以區間最大值的初始值 `m = 0` 是安全的（若難度可能為負，要改成 −∞）；d = 1 時答案是整個陣列的最大值。

### Follow-up

> [!question]- F1. 能不能把每一層從 O(n²) 降到 O(n)？
> 可以，用 monotonic stack（第 10 章）。固定 k，`cur[i] = min_j (prev[j] + max(jd[j..i − 1]))`。當 i 增加、新工作 x = `jd[i − 1]` 加入時，所有「區間最大值 ≤ x」的起點 j，最大值都會變成 x，可以合併成一組；最大值比 x 大的組則不受影響。所以用一個 stack 存「(這組的最大值, 這組起點中最小的 prev[j], 到這組為止的最佳候選)」，最大值由底到頂遞減。新 x 進來時，彈出所有最大值 ≤ x 的組，把它們的最小 prev 合併（再加上 j = i − 1 自己），得到新組的候選 `best + x`，再和下一組留下的最佳候選取 min。每個 j 只進出 stack 一次，每層 O(n)，總時間 O(d · n)。
> ```python
> def min_difficulty_stack(jd, d):
>     n, INF = len(jd), float("inf")
>     if n < d:
>         return -1
>     prev = [0] + [INF] * n
>     for _ in range(d):
>         cur, stack = [INF] * (n + 1), []        # stack: (組內最大值, 組內最小 prev, 累積最佳)
>         for i in range(1, n + 1):
>             x, best = jd[i - 1], prev[i - 1]   # 最後一天只做第 i-1 份
>             while stack and stack[-1][0] <= x:
>                 best = min(best, stack.pop()[1])
>             cand = best + x
>             if stack:
>                 cand = min(cand, stack[-1][2])  # 最大值更大的組，代價不受 x 影響
>             stack.append((x, best, cand))
>             cur[i] = cand
>         prev = cur
>     return prev[n]                              # 與 O(d·n²) 版本在隨機測試中一致
> ```

> [!question]- F2. 如果要輸出每一天做哪些工作呢？
> 保留完整的 d × (n + 1) 表，並在更新 `cur[i]` 時記錄達到最小值的 j（`choice[k][i] = j`）。最後從 (d, n) 開始，每次讀出 j = `choice[k][i]`，第 k 天做的就是 `jd[j..i − 1]`，然後令 (k, i) = (k − 1, j)，直到 k = 0。空間 O(d · n)，回溯 O(d)。若用了 F1 的 monotonic stack 版本，要在 stack 的每一組中多存「達到最小 prev 的 j」，才能還原切點。

> [!question]- F3. 如果目標改成「最小化最難的那一天」（各天難度的最大值）呢？
> 那就變回第 8 章難題 2 的 410 形式：可行性「每天的難度都 ≤ X」對 X 單調，所以可以二分答案。給定 X，每份工作的難度必須 ≤ X（否則不可行），而在這個條件下，任何切法每天的最大值都 ≤ X，只要能切成恰好 d 段即可，也就是 n ≥ d。所以答案其實就是 `max(jd)`（只要 n ≥ d），連二分都不需要。這個對比很好地說明了「最大值的總和」為什麼難：每一天的代價都會累加，沒有門檻可以檢查，只能 DP。

> [!question]- F4. 如果工作之間沒有順序限制，可以任意分配到 d 天呢？
> 沒有順序限制時就不需要 DP。設排序後 a₀ ≤ a₁ ≤ … ≤ a_{n−1}：最難的工作一定是某一天的最大值，其他 d − 1 天的最大值是另外 d − 1 份不同的工作，總和至少是 `a_{n−1} + a₀ + … + a_{d−2}`。這個下界可以達到：讓最簡單的 d − 1 份工作各自單獨一天，其餘全部放在同一天。所以答案是 `a[-1] + sum(a[:d − 1])`，O(n log n)。這個 follow-up 說明了 DP 的必要性來自「依序」的限制；限制拿掉之後，問題結構完全改變。

> [!question]- F5. 如果每天最多只能做 m 份工作呢？
> 只是讓最後一天的起點 j 多一個下界：最後一天做 `jd[j..i − 1]`，共 i − j 份，必須 ≤ m，所以 j ≥ i − m。轉移變成 `dp[k][i] = min_{max(k − 1, i − m) ≤ j ≤ i − 1} (dp[k − 1][j] + max(jd[j..i − 1]))`，時間 O(d · n · m)。若 m · d < n，無論怎麼排都做不完，直接回傳 −1。若想保留 F1 的 monotonic stack 優化，則要變成「滑動窗口」版本：stack 底部超出窗口的組要從底部移除，可以改用 deque 實作，但每組內的最小 prev 也要能隨窗口更新，實作明顯更複雜，面試中通常說明 O(d · n · m) 即可。

### 心得

關鍵突破是看出這是「分段 DP」：狀態 (天數, 已完成的工作數)，轉移枚舉最後一天的起點，並讓 j 往回枚舉以 O(1) 維護區間最大值。它和本章其他題的關係是：核心題 1–5 都是單一維度的狀態，這題示範了「切成 k 段」時多一維「已用幾段」的標準做法；和第 8 章 410 的對比則說明了「最大值的總和」與「總和的最大值」為什麼需要完全不同的工具。面試時先說 O(d · n²) 的 DP 並給出 9 × 10⁵ 的估算，證明它已經足夠快；如果面試官追問更快的做法，再提出 monotonic stack 的 O(d · n)，並說明「最大值 ≤ x 的起點會被合併」這個觀察。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 常數個前驅 | `dp[i]` 只依賴前面固定幾格；「選或不選」「走 1 步或 2 步」 | 兩三個變數滾動，O(1) 空間 | 核心題 1（198）、核心題 5（91）、70、746、213、740 |
| 枚舉所有前驅 | 「以 i 結尾」的最佳值，前驅可以是任何 j < i | O(n²)；用長度上限、二分或單調結構加速 | 核心題 3（300）、核心題 4（139）、368、673、1048 |
| 以數值為狀態 | 湊出某個總和、物品可重複使用 | `dp[v]` 由 `dp[v − c]` 轉移；計數題注意迴圈順序 | 核心題 2（322）、279、377、518（第 23 章） |
| 狀態機 | 持有／未持有、冷卻、剩幾次機會 | 先畫圖：節點是狀態、邊是動作；−∞ 表示不可達 | 難題 1（188）、121、122、123、309、714、801 |
| 排序後 LIS | 二維偏序、兩個維度都要遞增 | 一維排序、同值反向排序，另一維做 patience sorting | 難題 2（354）、1626、646、1691（三維時退回 O(n²)） |
| 狀態加一維 | 位置不夠，還需要「上一步」的資訊 | 問「下一個決定需要知道什麼」，放進狀態；用 dict 存稀疏狀態 | 難題 3（403）、核心題 5 F5、1027（狀態加上公差） |
| 排序後二分找前驅 | 帶權重的區間挑選、不能重疊 | 依結束時間排序，`dp[i] = max(dp[i − 1], w_i + dp[p(i)])` | 難題 4（1235）、1751、2008、2054 |
| 分段 DP | 依序切成恰好 k 段，代價可加總 | `dp[k][i]` 枚舉最後一段起點；monotonic stack 或其他單調性優化 | 難題 5（1335）、410（第 8 章難題 2）、813、1278 |

**下限與上限**。最簡單的一維 DP 是爬樓梯與 House Robber：狀態一眼就看得出來，轉移只有兩項，考的是能不能從暴力遞迴走到 O(1) 空間，並說清楚 base case。中間層是核心題 2–5：狀態仍是一個整數，但要想清楚「最後一步」的完整分類（最後一枚硬幣、最後一個單字、最後一個字母用幾位數），以及 base case 的精確意義（空字串、湊出 0 元）。上限的題目難在三個地方，而且常常同時出現：第一，**狀態不是現成的**，必須做一個觀察才能定義，例如 403 要加上「上一跳的距離」，188 要把交易次數展開成狀態機；第二，**需要先做一個變換**，DP 才會成形，例如 354 的特殊排序、1235 的依結束時間排序；第三，**轉移太慢，需要另一個 pattern 來加速**，例如 300 的 binary search、1335 的 monotonic stack、188 大 k 時的 Aliens trick。

**與其他 pattern 的關係**。DP 和 backtracking（第 19 章）都從同一棵遞迴樹出發：backtracking 列舉每一個葉子，DP 在「子問題只依賴少數參數」時把相同的子樹合併，所以「要所有解」用 backtracking、「要彙總值」用 DP，兩者也常一起出現（139 F1、91 F2 用 DP 剪枝 backtracking）。DP 和 greedy（第 20 章）的分界是反例：硬幣、帶權區間排程有反例，所以要 DP；無權區間排程、canonical 硬幣系統有交換論證，所以貪婪就夠。DP 和最短路（第 15、18 章）本質相同：DP 是在 DAG 上依拓撲順序鬆弛，322 可以用 BFS、403 F4 不需要 Dijkstra，都是這個觀點的應用；依賴關係有環時，DP 失效，要改用圖演算法。binary search（第 8 章）常是 DP 的零件（300、354、1235），而 410 則是「二分答案能取代 DP」的例子。本章之後，第 22 章把狀態擴充成兩個索引（兩個字串、網格），第 23 章處理背包與區間 DP，第 24 章處理樹、bitmask 與數位 DP，它們的思考方法與本章完全相同：先定義狀態，再找最後一步。

**容易混淆之處**。第一，「以 i 結尾」和「前 i 個」是兩種不同的狀態定義：前者（300、354）答案是 `max(dp)`，後者（198、139、1235）答案是 `dp[n]`，混用會差一格或回傳錯的格子。第二，計數題的「組合」與「排列」：518 和 377 的程式只差在兩層迴圈的順序，答案卻完全不同。第三，`bisect_left` 與 `bisect_right`：嚴格遞增的 LIS 用 left、非嚴格用 right；1235 中相接的工作可以同時選，所以用 right，而 1751 的閉區間要用 left，這類一個字元的差別最容易在面試中出錯。第四，狀態機題就地更新是否安全要逐題判斷：188 的就地更新安全，309 的冷卻題則必須同時更新。

## 本章重點整理

- DP = 暴力遞迴 + 記住子問題的答案 + 依照依賴順序計算；適用的前提是子問題重疊，而且大問題的答案能由小問題組合出來。
- 每個 DP 解法都要回答四件事：狀態的精確定義、轉移（看「最後一步」）、base case（最小情況的正確答案）、計算順序（依賴圖的拓撲順序）。
- 從暴力遞迴推出 DP：先寫出純函式的遞迴，參數就是狀態；加上 `@cache` 得到 top-down；改成迴圈得到 bottom-up；只依賴固定幾格時做空間壓縮。
- 設計狀態時問：「做下一個決定時，未來需要知道過去的什麼？」只把這些放進狀態；放少了答案錯（403 只記石頭），放多了狀態爆炸。
- 一維 DP 的轉移形狀：常數個前驅（O(n)）、枚舉所有前驅（O(n²)，可用長度上限或二分加速）、以數值為狀態（偽多項式）、排序後二分找前驅（O(n log n)）、狀態機、分段。
- 狀態機 DP 的畫法：列出每天結束時的狀態、每種動作是一條帶權重的邊、每個狀態取所有入邊的 max；不可達的狀態用 −∞；同一天的狀態原則上用昨天的值同時更新。
- 最佳化用 min／max（分類可重疊）、計數用 +（分類必須互斥且完整）、存在性用 or；硬幣計數「外層硬幣」是組合數、「外層金額」是排列數。
- LIS 有兩種解法：O(n²) 的「以 i 結尾」DP，與 O(n log n) 的 patience sorting（`tails[k]` = 長度 k + 1 的最小結尾）；嚴格用 `bisect_left`、非嚴格用 `bisect_right`，`tails` 不一定是真正的子序列。
- 二維偏序先排序消掉一維：354 依寬度遞增、同寬高度遞減，再對高度做嚴格 LIS。
- 帶權區間排程依結束時間排序後是「選或不選」：`dp[i] = max(dp[i − 1], w_i + dp[bisect_right(ends, start_i)])`；相接可選用 right，不可相接用 left。
- 分段 DP 多一維「已用幾段」，j 往回枚舉以 O(1) 維護區間最大值；需要更快時用 monotonic stack 合併「最大值 ≤ x」的起點。
- 還原方案要保留完整的表或 choice 陣列，從答案格子沿著取最佳值的轉移往回走；做了空間壓縮就無法回溯。
- top-down 寫起來快、只算可達狀態，但 Python 遞迴深度有限；bottom-up 沒有深度問題，也才能空間壓縮。面試時用 top-down 想、用 bottom-up 寫。
