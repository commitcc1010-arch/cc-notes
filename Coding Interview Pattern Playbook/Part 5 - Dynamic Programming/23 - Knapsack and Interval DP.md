---
chapter: 23
title: DP：背包與區間
part: 5
---

# 第 23 章　DP：背包與區間

> [!abstract] 本章地圖
> **一句話**：背包 DP 是「逐一決定每個物品要不要拿（或拿幾個），狀態只記剩下的容量」；區間 DP 是「一段連續區間的答案，由它內部更短的區間組合而成，所以依長度由小到大計算」。
>
> **辨識訊號**：
> - 「從陣列中挑一些數，使總和恰好是／不超過某個值」「能不能分成兩堆一樣大」
> - 「有幾種方法湊出 amount」，而且數值範圍（總和、amount）不大，可以當作陣列索引
> - 每個數只能用一次 → 0/1 背包；可以重複使用 → 完全背包；要分清楚順序算不算不同
> - 字串或陣列的答案取決於「頭尾兩端怎麼配對」，例如回文、插入幾個字元變回文
> - 「合併相鄰的東西」「切開一根棍子」「戳破氣球」，每次操作的成本取決於當時左右鄰居或整段的總和
> - n 只有 100 到 500，暗示可以接受 O(n²) 個狀態、每個狀態 O(n) 轉移的 O(n³)
>
> **核心題**：416、494、518、516、1312
>
> **難題**：312、664、546、1000、1547

## 23.1 這個 Pattern 解決什麼問題

先看一個小問題：給你 `[3, 34, 4, 12, 5, 2]`，能不能從中挑出幾個數，使總和恰好是 9？暴力解是列舉所有子集，每個數有「拿」與「不拿」兩種選擇，共 2ⁿ 種，n = 40 就已經是 10¹² 等級。可是仔細看，當我們由左往右決定時，**真正影響後續的只有「目前湊到多少」這一個數字**，至於是用 4 + 5 還是 3 + 4 + 2 湊到 9，對後面的決定完全沒有差別。於是 2ⁿ 條路徑會大量匯流到同一個狀態「看完前 i 個數、目前總和是 s」，狀態總數只有 n × (目標 + 1) 個。這就是背包 DP（knapsack DP，背包動態規劃）的核心：**把「選了哪些」壓縮成「選完之後剩下什麼資源」**，只要資源（容量、總和、金額）的範圍不大，就能用一張表記住所有可能。

背包的另一個面向是**計數**。「湊出 amount 有幾種方法」和「能不能湊出 amount」用的是同一張表，只是把 `or` 換成 `+`，把 `max` 換成 `+`。但計數會帶出一個很容易出錯的問題：`1 + 2` 和 `2 + 1` 算一種還是兩種？答案完全取決於兩層迴圈的順序，23.4 節會用同一張表把兩種順序各走一次，讓你看清楚差別從哪裡來。

第二類問題長得很不一樣。給一個字串 `"bbbab"`，問最長的回文子序列（palindromic subsequence，不必連續的回文）有多長。這時「從左到右逐一決定」不再自然，因為回文是由**兩端**往中間配對的：`s[0]` 要和誰配對，取決於右端的字元。把狀態定為「子字串 `s[i..j]` 的答案」，`s[i..j]` 的答案只依賴 `s[i+1..j-1]`、`s[i+1..j]`、`s[i..j-1]` 這些**更短**的區間。這就是區間 DP（interval DP）：狀態是一段連續區間，轉移來自它內部的子區間，所以只要依「區間長度由小到大」計算，需要的值一定已經算好。

區間 DP 最難的地方通常不是寫迴圈，而是**選對「最後一步」**。戳破氣球（難題 1）如果想「第一顆戳哪顆」，左右兩半會因為鄰居改變而互相糾纏；改想「最後一顆戳哪顆」，它的左右鄰居就固定是區間外的兩顆，兩半變得完全獨立。本章的五道難題，有四道的關鍵突破都是「換一個角度定義最後一步，讓子問題獨立」。

## 23.2 辨識訊號

| 題目特徵 | 為什麼是這個 pattern | 本章哪一題 |
|---|---|---|
| 挑一些數使總和恰好是 S／2，數值總和不大（≤ 2 × 10⁴） | 0/1 背包的可行性版本，狀態是「能否湊出 s」 | 核心題 1（416） |
| 每個數前面放 + 或 −，數出等於 target 的方法數 | 正號集合的和 P 被 target 與總和唯一決定，變成 0/1 計數背包 | 核心題 2（494） |
| 硬幣可以無限使用，數出湊成 amount 的組合數 | 完全背包的計數版本，外層硬幣、內層金額避免重複計算排列 | 核心題 3（518） |
| 字串上的「最長回文子序列」「最少插入幾個字元變回文」 | 答案由兩端是否相等決定，`s[i..j]` 只依賴更短的區間 | 核心題 4（516）、核心題 5（1312） |
| 每次操作的分數取決於左右鄰居，操作後鄰居會改變 | 枚舉區間內「最後一個」被處理的元素，左右子區間獨立 | 難題 1（312） |
| 一次可以覆蓋一整段，相同字元可以「借」前面那一筆一起印 | 區間 DP 中讓左端點和右邊某個相同字元合併 | 難題 2（664） |
| 移除連續同色區塊得分 k²，移除後兩邊會接起來 | 區間不足以描述狀態，要多記「左邊黏著幾個同色」 | 難題 3（546） |
| 每次合併相鄰 K 堆，成本是總和 | 區間 DP 加上「這段最後會剩幾堆」的可行性條件 | 難題 4（1000） |
| 依序切一根棍子，每刀成本是當下那段的長度 | 枚舉「第一刀」切在哪裡，等價於區間合併的反向 | 難題 5（1547） |
| n ≤ 100～500 而且題目是「最佳化一段序列的操作順序」 | 區間 DP 的狀態 O(n²)、轉移 O(n)，總共 O(n³) 剛好可接受 | 難題 1–5 |

一個實用的區分方式：**背包題的狀態維度是「資源的數值」**（總和、金額），所以要看數值範圍；**區間題的狀態維度是「位置」**（i、j），所以要看長度 n。如果題目的總和高達 10⁹ 而 n ≤ 40，背包 DP 的表放不下，要改用 meet in the middle；如果 n 高達 10⁵，O(n²) 個區間狀態也放不下，通常代表有貪婪或其他結構可用。

## 23.3 背包模板與原理：0/1 背包與完全背包

**問題定義**。有 n 個物品，第 i 個重 `w[i]`、價值 `v[i]`，背包容量 C，求能裝入的最大總價值。**0/1 背包**：每個物品最多拿一次。**完全背包**（unbounded knapsack）：每個物品可以拿任意多次。

**二維狀態**。令 `dp[i][c]` = 只考慮前 i 個物品、容量上限 c 時的最大價值。考慮第 i 個物品（索引 i − 1）時只有兩種選擇：

- 不拿：`dp[i][c] = dp[i-1][c]`。
- 拿（0/1）：`dp[i][c] = dp[i-1][c - w] + v`。拿了之後，**前 i − 1 個物品**只能用剩下的 c − w。
- 拿（完全）：`dp[i][c] = dp[i][c - w] + v`。拿了一個之後，**第 i 個物品還可以再拿**，所以從同一列的 `dp[i][c - w]` 轉移，那個值本身可能已經拿過第 i 個物品了。

0/1 與完全背包唯一的差別，就是「拿」的轉移來自上一列還是同一列。用 `w = [1, 3, 4]`、`v = [15, 20, 30]`、C = 4 畫出 0/1 背包的二維表：

```text
0/1 背包：dp[i][c] = max(dp[i-1][c], dp[i-1][c-w] + v)

                 c=0   c=1   c=2   c=3   c=4
i=0 (不用物品)     0     0     0     0     0
i=1 (w=1,v=15)    0    15    15    15    15     ← 只有一個物品，容量 ≥ 1 就拿
i=2 (w=3,v=20)    0    15    15    20    35     ← c=4：max(上方 15, 左上 dp[1][1]+20 = 35)
i=3 (w=4,v=30)    0    15    15    20    35     ← c=4：max(上方 35, dp[2][0]+30 = 30) = 35

每一格只看「正上方」和「上一列往左 w 格」兩個值：
             dp[i-1][c-w] ─┐
                           ├─→ dp[i][c]
             dp[i-1][c]   ─┘
```

**一維空間壓縮**。因為第 i 列只依賴第 i − 1 列，可以只留一個長度 C + 1 的陣列 `dp[c]`，在原地把「上一列」更新成「這一列」。問題在於：更新 `dp[c]` 時要讀 `dp[c - w]`，那一格現在裝的是上一列的值，還是這一列已經更新過的值？**答案由內層迴圈的方向決定**：

- **0/1 背包，c 由大到小**。更新 `dp[c]` 時，比 c 小的 `dp[c - w]` 還沒被這一輪碰過，仍然是上一列的值，等價於 `dp[i-1][c-w]`，所以每個物品最多被用一次。
- **完全背包，c 由小到大**。更新 `dp[c]` 時，`dp[c - w]` 已經在這一輪更新過，等價於 `dp[i][c-w]`，裡面可能已經拿過這個物品，所以同一個物品可以累加多次。

用單一物品 `w = 1, v = 15`、C = 3 就能看出兩個方向的差別：

```text
初始 dp = [0, 0, 0, 0]

由小到大（完全背包）：
c=1: dp[1] = max(0, dp[0]+15) = 15      dp = [0, 15,  0,  0]
c=2: dp[2] = max(0, dp[1]+15) = 30      dp = [0, 15, 30,  0]   ← dp[1] 已含一個物品，再拿一次
c=3: dp[3] = max(0, dp[2]+15) = 45      dp = [0, 15, 30, 45]   ← 同一個物品用了三次

由大到小（0/1 背包）：
c=3: dp[3] = max(0, dp[2]+15) = 15      dp = [0,  0,  0, 15]   ← dp[2] 還是上一列的 0
c=2: dp[2] = max(0, dp[1]+15) = 15      dp = [0,  0, 15, 15]
c=1: dp[1] = max(0, dp[0]+15) = 15      dp = [0, 15, 15, 15]   ← 每格最多一個物品
```

記憶方式：**由大到小讀到的是「舊的」，由小到大讀到的是「新的」**。0/1 要舊值，完全背包要新值。

```python
import random
from itertools import product


def knapsack_01_2d(w: list[int], v: list[int], cap: int) -> int:
    n = len(w)
    dp = [[0] * (cap + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        wi, vi = w[i - 1], v[i - 1]
        for c in range(cap + 1):
            dp[i][c] = dp[i - 1][c]                                  # 不拿
            if c >= wi:
                dp[i][c] = max(dp[i][c], dp[i - 1][c - wi] + vi)     # 拿：從上一列轉移
    return dp[n][cap]


def knapsack_01(w: list[int], v: list[int], cap: int) -> int:
    dp = [0] * (cap + 1)
    for wi, vi in zip(w, v):
        for c in range(cap, wi - 1, -1):      # 由大到小：dp[c - wi] 仍是上一列的值
            dp[c] = max(dp[c], dp[c - wi] + vi)
    return dp[cap]


def knapsack_unbounded(w: list[int], v: list[int], cap: int) -> int:
    dp = [0] * (cap + 1)
    for wi, vi in zip(w, v):
        for c in range(wi, cap + 1):          # 由小到大：dp[c - wi] 可能已含這個物品
            dp[c] = max(dp[c], dp[c - wi] + vi)
    return dp[cap]


def brute_01(w, v, cap):
    best = 0
    for pick in product((0, 1), repeat=len(w)):
        if sum(p * x for p, x in zip(pick, w)) <= cap:
            best = max(best, sum(p * x for p, x in zip(pick, v)))
    return best


def brute_unbounded(w, v, cap):
    best = [0] * (cap + 1)                    # 直接枚舉最後拿的物品，作為對照
    for c in range(1, cap + 1):
        best[c] = max([best[c - x] + y for x, y in zip(w, v) if x <= c] + [0])
    return best[cap]


assert knapsack_01_2d([1, 3, 4], [15, 20, 30], 4) == 35
assert knapsack_01([1, 3, 4], [15, 20, 30], 4) == 35
assert knapsack_unbounded([1, 3, 4], [15, 20, 30], 4) == 60
assert knapsack_01([1], [15], 3) == 15 and knapsack_unbounded([1], [15], 3) == 45
assert knapsack_01([5], [10], 4) == 0                # 物品比容量大
assert knapsack_01([], [], 10) == 0                  # 沒有物品
for _ in range(300):
    n = random.randint(0, 6)
    w = [random.randint(1, 6) for _ in range(n)]
    v = [random.randint(0, 9) for _ in range(n)]
    cap = random.randint(0, 12)
    assert knapsack_01(w, v, cap) == knapsack_01_2d(w, v, cap) == brute_01(w, v, cap)
    assert knapsack_unbounded(w, v, cap) == brute_unbounded(w, v, cap)
print("all tests passed")
```

**每一行為什麼這樣寫**：

- `dp` 長度 `cap + 1`，`dp[c]` 的語意是「容量**不超過** c 的最大價值」，所以全部初始化為 0；如果題目要求「恰好裝滿 c」，要改成 `dp[0] = 0`、其他為 −∞，否則沒裝滿的狀態會被當成合法。
- 0/1 的內層迴圈下界是 `wi`，因為 `c < wi` 時放不下，`dp[c]` 維持不變，不必走過去。
- 外層迴圈是物品、內層是容量。對最大化問題，0/1 背包**必須**外層物品（否則一維陣列無法區分「上一列」）；完全背包兩種順序都對，因為「最大價值」不在乎物品的拿取順序。
- 時間 O(n · C)，空間從 O(n · C) 降為 O(C)。代價是丟失了「哪些物品被選中」的資訊，要回溯選法就得保留二維表（核心題 1 F1）。

**這是「偽多項式」**。O(n · C) 看起來是多項式，但 C 是輸入的**數值**而不是長度：C = 10⁹ 時只要寫 10 位數就能讓表大到放不下。所以背包 DP 只有在總和、容量、金額不大（通常 ≤ 10⁴～10⁵）時可用，看到數值很大就要換方法。

## 23.4 計數型背包：組合與排列的迴圈順序

計數版本把 `max` 換成 `+`：`dp[j]` = 湊出 j 的方法數，`dp[0] = 1`（什麼都不拿是一種方法）。以硬幣可以無限使用為例，有兩種看起來都很合理的寫法：

```python
def count_combinations(coins: list[int], amount: int) -> int:
    """不計順序：1+2 和 2+1 算同一種（518）。"""
    dp = [1] + [0] * amount
    for c in coins:                           # 外層硬幣
        for j in range(c, amount + 1):        # 內層金額，由小到大（完全背包）
            dp[j] += dp[j - c]
    return dp[amount]


def count_permutations(coins: list[int], amount: int) -> int:
    """計順序：1+2 和 2+1 算兩種（377. Combination Sum IV）。"""
    dp = [1] + [0] * amount
    for j in range(1, amount + 1):            # 外層金額
        for c in coins:                       # 內層硬幣：枚舉「最後一枚」是哪一種
            if c <= j:
                dp[j] += dp[j - c]
    return dp[amount]


def count_01(nums: list[int], target: int) -> int:
    """每個數最多用一次的子集計數（494 的核心）。"""
    dp = [1] + [0] * target
    for x in nums:
        for j in range(target, x - 1, -1):    # 由大到小
            dp[j] += dp[j - x]
    return dp[target]


assert count_combinations([1, 2], 4) == 3              # 1111、112、22
assert count_permutations([1, 2], 4) == 5              # 1111、112、121、211、22
assert count_combinations([1, 2, 5], 5) == 4
assert count_permutations([1, 2, 5], 5) == 9
assert count_combinations([2], 3) == 0 and count_permutations([2], 3) == 0
assert count_combinations([7], 0) == 1 == count_permutations([7], 0)
assert count_01([1, 1, 2], 2) == 2                     # {1,1}、{2}
assert count_01([0, 1], 1) == 2                        # 0 拿或不拿都行
print("all tests passed")
```

**為什麼外層硬幣就不會重複**。外層依序處理硬幣 1、再處理硬幣 2，處理硬幣 2 時，`dp[j - 2]` 只包含「用硬幣 1 和硬幣 2」的方法。換句話說，每一種方法都被強制寫成「先全部的 1、再全部的 2」這個**標準順序**，每個多重集合恰好被數一次。外層金額則不同：`dp[j]` 枚舉「最後一枚硬幣是哪一種」，`1 + 2` 的最後一枚是 2、`2 + 1` 的最後一枚是 1，它們走不同的分支，被當成兩種。

```text
coins = [1, 2]，amount = 4

外層硬幣（組合）：
                 j=0  j=1  j=2  j=3  j=4
初始              1    0    0    0    0
處理硬幣 1 後      1    1    1    1    1     只用 1：每個金額恰好一種
處理硬幣 2 後      1    1    2    2    3     j=4：dp[4] = 1 + dp[2] = 1 + 2
                                          → {1111}、{1,1,2}、{2,2}，每種多重集合一次

外層金額（排列）：dp[j] = dp[j-1] + dp[j-2]
                 j=0  j=1  j=2  j=3  j=4
                  1    1    2    3    5
j=3：最後一枚是 1 → dp[2] = 2 種（11|1、2|1）
     最後一枚是 2 → dp[1] = 1 種（1|2）
     共 3 種：111、21、12 ← 21 和 12 分開算了
```

整理成一張表，四種組合一次記住：

| 每個物品 | 順序是否算不同 | 外層 | 內層方向 | 例題 |
|---|---|---|---|---|
| 最多一次（0/1） | 不算（子集） | 物品 | 金額由大到小 | 416、494 |
| 無限次（完全） | 不算（組合） | 物品 | 金額由小到大 | 518 |
| 無限次（完全） | 算（排列） | 金額 | 物品（任意順序） | 377、70 爬樓梯 |
| 最多一次 | 算（排列） | 物品 | 多一維「選了幾個」，由大到小 | 答案是 Σ dp[k][target] · k! |

最後一列值得注意：「每個數最多用一次而且順序算不同」不能直接把迴圈對調，因為外層金額時同一個數可能在不同位置被重複使用。正確做法是先數「大小為 k、總和為 target 的子集有幾個」（`dp[k][s]`，0/1 背包多一維），每個這樣的子集恰好有 k! 種排列，再加總。若排列還有額外限制（例如相鄰元素要滿足某個條件），排列數就不再是 k!，這時「用過哪些」必須進入狀態，要改用第 24 章的 bitmask DP。

## 23.5 區間 DP 模板與原理：依長度由小到大

**狀態定義**。`dp[i][j]` = 只看區間 `[i, j]`（閉區間）時的最佳答案。這個定義隱含一個前提：**區間內部的最佳決策不受區間外影響**，或者區間外的影響可以用少數參數描述（例如難題 1 的左右邊界、難題 3 的額外同色盒子數）。寫區間 DP 之前，最重要的是先確認這個獨立性成立。

**兩種常見的轉移**：

1. **枚舉分割點**：`dp[i][j] = best over k (dp[i][k] ⊕ dp[k+1][j]) + cost(i, j)`。區間被切成兩段，各自獨立求解。合併石頭、切棍子、戳氣球、矩陣連乘都屬於這類，轉移 O(n)，總時間 O(n³)。
2. **處理兩端**：`dp[i][j]` 由 `dp[i+1][j-1]`、`dp[i+1][j]`、`dp[i][j-1]` 決定，看 `s[i]` 和 `s[j]` 能不能配對。回文類題目屬於這類，轉移 O(1)，總時間 O(n²)。

**計算順序**。`dp[i][j]` 依賴的每一個子區間都**比 [i, j] 短**，所以外層迴圈枚舉長度 `length = 1, 2, …, n`，內層枚舉起點 i，`j = i + length - 1`，就能保證需要的值都已經算好。另一種等價寫法是 i 由 n − 1 往下、j 由 i 往上：依賴的 `dp[i+1][…]` 在 i 更大的那一列已經算過，`dp[i][j-1]` 在同一列左邊已經算過。兩種都對，依長度的寫法比較直觀、也比較容易說服面試官；第二種寫法方便把空間壓成一維（核心題 4 F3）。

以「每次合併相鄰兩堆石頭，成本是兩堆的總和，求合併成一堆的最小成本」為例（難題 4 的 K = 2 特例），`stones = [3, 2, 4, 1]`：

```text
dp[i][j] = min over k in [i, j) (dp[i][k] + dp[k+1][j]) + sum(i..j)
最後一次合併把 [i..k] 和 [k+1..j] 兩堆併起來，成本一定是整段的總和

依長度填表（對角線 → 往右上）：

         j=0  j=1  j=2  j=3
i=0       0    5   14   20       length 1：對角線全是 0（一堆不用合併）
i=1            0    6   12       length 2：dp[0][1] = 3+2 = 5，dp[1][2] = 6，dp[2][3] = 5
i=2                 0    5       length 3：dp[0][2] = min(0+6, 5+0) + 9 = 14
i=3                      0                 dp[1][3] = min(0+5, 6+0) + 7 = 12
                                 length 4：dp[0][3] = min(0+12, 5+5, 14+0) + 10 = 20

填表順序：
  length 1     length 2      length 3      length 4
  ■ . . .      ■ ■ . .       ■ ■ ■ .       ■ ■ ■ ■
  . ■ . .      . ■ ■ .       . ■ ■ ■       . ■ ■ ■
  . . ■ .      . . ■ ■       . . ■ ■       . . ■ ■
  . . . ■      . . . ■       . . . ■       . . . ■
```

`dp[0][3]` 的三個候選分別是「最後一次合併 3 | 2 4 1」「3 2 | 4 1」「3 2 4 | 1」，中間那個 5 + 5 + 10 = 20 最好：先合併 3 + 2、再合併 4 + 1、最後合併 5 + 5。每一格只讀它左邊同一列與下方同一行的格子，這些都屬於更短的區間。

```python
import random
from functools import cache


def merge_adjacent_pairs(stones: list[int]) -> int:
    n = len(stones)
    prefix = [0]
    for x in stones:
        prefix.append(prefix[-1] + x)
    dp = [[0] * n for _ in range(n)]
    for length in range(2, n + 1):                 # 依長度由小到大
        for i in range(n - length + 1):
            j = i + length - 1
            dp[i][j] = min(dp[i][k] + dp[k + 1][j] for k in range(i, j))
            dp[i][j] += prefix[j + 1] - prefix[i]  # 最後一次合併的成本 = 整段總和
    return dp[0][n - 1] if n else 0


def merge_adjacent_pairs_rev(stones: list[int]) -> int:
    """等價的順序：i 由大到小、j 由小到大。"""
    n = len(stones)
    prefix = [0]
    for x in stones:
        prefix.append(prefix[-1] + x)
    dp = [[0] * n for _ in range(n)]
    for i in range(n - 2, -1, -1):
        for j in range(i + 1, n):
            dp[i][j] = min(dp[i][k] + dp[k + 1][j] for k in range(i, j)) + prefix[j + 1] - prefix[i]
    return dp[0][n - 1] if n else 0


def brute(stones):
    @cache
    def go(t):
        if len(t) <= 1:
            return 0
        return min(t[i] + t[i + 1] + go(t[:i] + (t[i] + t[i + 1],) + t[i + 2:]) for i in range(len(t) - 1))
    return go(tuple(stones))


assert merge_adjacent_pairs([3, 2, 4, 1]) == 20
assert merge_adjacent_pairs([5]) == 0
assert merge_adjacent_pairs([]) == 0
assert merge_adjacent_pairs([1, 1]) == 2
for _ in range(300):
    s = [random.randint(1, 9) for _ in range(random.randint(1, 7))]
    assert merge_adjacent_pairs(s) == merge_adjacent_pairs_rev(s) == brute(s)
print("all tests passed")
```

**為什麼不能依 i 由小到大**。如果外層 i 從 0 開始，計算 `dp[0][3]` 時需要 `dp[1][3]`，但 i = 1 那一列還沒算，讀到的是初始值 0，答案會偏小而且不會報錯。區間 DP 的 bug 幾乎都是這種「讀到還沒算的格子」，所以寫完迴圈後，務必對一格具體的 `dp[i][j]` 檢查它依賴的格子是不是都已經填好。

**top-down 也可以**。用 `@cache` 寫 `solve(i, j)` 遞迴，計算順序由遞迴自動決定，不必想迴圈方向。缺點是 Python 的遞迴有額外常數，而且 n 較大時要調高遞迴深度上限；狀態有三維（難題 3）或轉移不規則時，top-down 往往更好寫。面試時兩種都可以，但要能說出「依長度遞增」這個順序為什麼正確。

## 23.6 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 0/1 背包一維時內層由小到大 | 同一個數被用了很多次，例如問 `[2]` 能否湊出 4 會回傳 True | 0/1 由大到小、完全背包由小到大；記「大到小讀舊值」 |
| 計數時迴圈順序放反 | 518 的答案變成排列數（`[1, 2, 5]`、5 得到 9 而不是 4） | 組合：外層物品；排列：外層金額。先問「順序算不算不同」 |
| 忘記 `dp[0] = 1`，或把它設成 0 | 所有計數都是 0 | 空集合湊出 0 是一種方法；最佳化問題則依題意決定 0 或 −∞ |
| 494 沒檢查 `(S + target)` 的奇偶與範圍 | P 不是整數或為負，陣列索引錯誤或回傳非 0 | `abs(target) > S` 或 `(S + target)` 為奇數時直接回傳 0 |
| 「恰好裝滿」和「不超過」混用 | 回傳了沒裝滿的價值 | 恰好：除了 `dp[0]` 其他初始化為 −∞；不超過：全部初始化為 0 |
| 區間 DP 依 i 由小到大計算 | 讀到還沒算的 `dp[i+1][j]`，答案偏小或偏大但不報錯 | 外層依長度，或 i 由大到小 |
| 區間端點定義不一致（開區間與閉區間混用） | 312、1547 差一格，邊界被重複計算或漏算 | 寫下「dp[i][j] 是否包含 i 和 j」，並在填表前用長度 1、2 的情況手算 |
| 想「第一步」導致子問題不獨立 | 312 的 DP 推不出來，或寫出錯誤的轉移 | 改想「最後一步」：最後一個被處理的元素，其左右邊界是固定的 |
| 區間狀態資訊不足 | 546 用 `dp[i][j]` 寫出錯誤答案 | 檢查「區間外的東西會不會影響區間內的分數」，有就加維度 |
| 背包數值太大仍硬開陣列 | 記憶體爆掉或超時 | 總和 ≥ 10⁶ 時改用 bitset、meet in the middle，或重新檢查題目限制 |

## 核心題 1｜416. Partition Equal Subset Sum｜Medium

### 題目

給一個只含正整數的陣列 `nums`，判斷能否把它分成兩個子集（每個元素恰好屬於其中一個），使兩個子集的元素和相等。回傳 True 或 False。限制：`1 <= len(nums) <= 200`，`1 <= nums[i] <= 100`，所以總和最多 2 × 10⁴。

- 範例 1：`nums = [1, 5, 11, 5]`，回傳 `True`，分法是 `[1, 5, 5]` 與 `[11]`，兩邊都是 11。
- 範例 2：`nums = [1, 2, 3, 5]`，回傳 `False`。總和 11 是奇數，不可能平分。
- 範例 3：`nums = [2, 2, 3, 5]`，回傳 `False`。總和 12 是偶數，但湊不出 6（2 + 2 = 4、2 + 3 = 5、2 + 2 + 3 = 7…都不是 6）。
- 範例 4（邊界）：`nums = [7]`，回傳 `False`；`nums = [4, 4]`，回傳 `True`。

### 思路

先做一個轉換：兩個子集的和相等，代表每一邊都是總和 S 的一半。所以 S 是奇數時直接回傳 False；S 是偶數時，問題等價於「**能不能挑出一些數，總和恰好是 T = S / 2**」，剩下的數自然就是另一半。這個轉換把「分成兩組」變成「挑一組」，是這題最重要的一步。

暴力解是列舉所有 2ⁿ 個子集，檢查是否有一個的和等於 T，n = 200 完全不可行。用 backtracking 加剪枝在隨機資料上可能很快，但最差仍是指數。瓶頸在於很多不同的子集會得到相同的總和，例如 `1 + 5` 和 `6` 對後面的選擇沒有任何差別，我們卻把它們當成不同的分支各走一次。

關鍵觀察：由左往右決定每個數拿或不拿時，後續只關心「目前湊到的總和」。令 `dp[s]` = 看過目前這些數之後，能否湊出總和 s。每看一個數 x，新的可達集合是「舊的可達集合」聯集「舊的可達集合各加 x」。這是 23.3 節的 0/1 背包可行性版本，每個數只能用一次，所以一維寫法的內層必須由大到小。不變式是：處理完前 i 個數後，`dp[s]` 為 True 若且唯若前 i 個數中存在一個子集和為 s。

```text
nums = [1, 5, 11, 5]，S = 22，T = 11
s:              0  1  2  3  4  5  6  7  8  9 10 11
初始            T  .  .  .  .  .  .  .  .  .  .  .
處理 1 後       T  T  .  .  .  .  .  .  .  .  .  .     dp[1] ← dp[0]
處理 5 後       T  T  .  .  .  T  T  .  .  .  .  .     dp[6] ← dp[1]，dp[5] ← dp[0]
處理 11 後      T  T  .  .  .  T  T  .  .  .  .  T     dp[11] ← dp[0]
處理 5 後       T  T  .  .  .  T  T  .  .  .  T  T     dp[10] ← dp[5]，dp[11] 已是 T

內層由大到小的重要性（處理第二個 5 時）：
s=11: dp[11] |= dp[6]  (舊值 T)
s=10: dp[10] |= dp[5]  (舊值 T)  → 10 = 5 + 5，用的是第一個 5 和第二個 5
s=6 : dp[6]  |= dp[1]
s=5 : dp[5]  |= dp[0]
若改成由小到大，s=5 先被設成 T，s=10 再讀到「這一輪」的 dp[5]，等於同一個 5 用了兩次。
在這個例子剛好不影響，但 nums = [1, 5] 時 S = 6、T = 3，由小到大處理 1 會讓 dp[1]、dp[2]、dp[3] 連鎖變成 T，
等於同一個 1 用了三次，錯誤地回傳 True。
```

第三列處理 11 時，只有 `dp[11] ← dp[0]` 成功，代表單獨拿 11 就能湊出 11，答案已經確定；最後一列的 5 讓 10 也變成可達。實作上可以在 `dp[T]` 變成 True 時提早結束。

### 解法

```python
import random
from itertools import product


def can_partition(nums: list[int]) -> bool:
    total = sum(nums)
    if total % 2:
        return False
    target = total // 2
    dp = [True] + [False] * target
    for x in nums:
        for s in range(target, x - 1, -1):     # 0/1 背包：由大到小
            if dp[s - x]:
                dp[s] = True
        if dp[target]:
            return True
    return dp[target]


def can_partition_bitset(nums: list[int]) -> bool:
    total = sum(nums)
    if total % 2:
        return False
    bits = 1                                   # 第 s 個位元 = 能否湊出 s
    for x in nums:
        bits |= bits << x                      # 舊集合 ∪ 舊集合 + x，一次處理所有 s
    return (bits >> (total // 2)) & 1 == 1


def brute(nums):
    total = sum(nums)
    return total % 2 == 0 and any(
        2 * sum(x for p, x in zip(pick, nums) if p) == total
        for pick in product((0, 1), repeat=len(nums)))


assert can_partition([1, 5, 11, 5]) is True
assert can_partition([1, 2, 3, 5]) is False
assert can_partition([2, 2, 3, 5]) is False
assert can_partition([7]) is False
assert can_partition([4, 4]) is True
assert can_partition([100] * 200) is True
assert can_partition([1, 5]) is False
for _ in range(500):
    arr = [random.randint(1, 12) for _ in range(random.randint(1, 10))]
    assert can_partition(arr) == can_partition_bitset(arr) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n · T)，T = S / 2 ≤ 10⁴，n ≤ 200，最多 2 × 10⁶ 次更新。空間 O(T)。bitset 版本的時間是 O(n · T / w)，w 是機器字長，Python 的大整數位移在 C 層一次處理很多位元，實際上比雙層迴圈快數十倍。邊界情況：總和為奇數直接 False；只有一個元素時 T = x / 2 < x，內層迴圈不執行，回傳 False；某個元素大於 T 時它不可能放進「和為 T」的那一邊，迴圈下界 `x - 1` 讓它自動被跳過（如果某個元素恰好等於 T，答案是 True）；`dp[0] = True` 代表空集合，是所有轉移的起點。

### Follow-up

> [!question]- F1. 如果要回傳其中一組實際的分法呢？
> 一維陣列丟失了「是哪個數讓 s 變成可達」的資訊，所以要保留二維的 `reach[i][s]`（前 i 個數能否湊出 s），再從 `(n, T)` 往回走：若 `reach[i-1][s]` 為 True，代表第 i 個數不必拿；否則一定拿了它，`s -= nums[i-1]`。時間仍是 O(n · T)，空間變成 O(n · T)，n = 200、T = 10⁴ 時是 2 × 10⁶ 個布林值，可以接受。若空間很緊，也可以只存「每個 s 第一次變成可達時是被哪個 i 更新的」（`parent[s] = i`），回溯時沿著 `s → s - nums[parent[s]-1]` 走，空間 O(T)；因為 s 第一次可達時用的數一定比湊出 `s - x` 的那些數更晚出現，回溯不會重複使用同一個數。
> ```python
> def partition_parts(nums):
>     total = sum(nums)
>     if total % 2:
>         return None
>     T = total // 2
>     parent = [-1] * (T + 1)
>     parent[0] = len(nums)                   # 哨兵：0 一開始就可達
>     for i, x in enumerate(nums):
>         for s in range(T, x - 1, -1):
>             if parent[s] == -1 and parent[s - x] != -1:
>                 parent[s] = i
>     if parent[T] == -1:
>         return None
>     left, s = [], T
>     while s:
>         left.append(nums[parent[s]])
>         s -= nums[parent[s]]
>     return left
> ```

> [!question]- F2. 如果目標改成讓兩組的差距最小，回傳最小差距（1049. Last Stone Weight II 的本質）？
> 同一張可達表，只是不再要求恰好 T。兩組的和是 a 與 S − a，差距 |S − 2a|，所以要找最大的可達 a ≤ S / 2。跑完 0/1 背包後從 `S // 2` 往下找第一個 True 的 a，答案是 S − 2a。時間 O(n · S)，空間 O(S)。1049 題「兩兩相撞剩下的最小重量」之所以等價，是因為任何相撞順序最後的結果都可以寫成「一組正號、一組負號」的和，而任何正負號分法也都能用某個相撞順序實現。

> [!question]- F3. 如果元素可以是負數或 0 呢？
> 0 不影響答案（放哪一邊都可以），可以直接忽略。負數讓總和的範圍變成 `[負數總和, 正數總和]`，陣列索引不能是負的，所以要加上偏移量 `offset = -(負數總和)`，或乾脆用 Python 的 `set` 存可達的和：`reach = {s + x for s in reach} | reach`，時間 O(n · R)，R 是可能的和的範圍。另外要注意題意：若要求兩個子集都非空，全部元素和為 0 時「全部放一邊」不算數，要額外檢查是否存在非空真子集和為 0。

> [!question]- F4. 如果要分成 k 個和相等的子集呢（698. Partition to K Equal Sum Subsets）？
> 背包 DP 不能直接推廣：兩組時「挑一組湊出 S / 2」就夠了，但 k 組時要同時追蹤 k − 1 個桶子各裝了多少，而且不同元素必須進不同桶子，狀態爆炸。標準做法是第 19 章難題 4 的 backtracking 加剪枝（元素由大到小排序、相同狀態的桶子只試一次），或第 24 章的 bitmask DP：`dp[mask]` = 用了 mask 這些元素之後，目前這個桶子裝了多少（對 S / k 取餘數），時間 O(n · 2ⁿ)，n ≤ 16 時可行。

> [!question]- F5. 如果 n ≤ 40 但每個元素高達 10⁹ 呢？
> 這時 T 高達 2 × 10¹⁰，背包表放不下，2⁴⁰ 的暴力也太慢。改用 meet in the middle：把陣列切成前後兩半，各自列舉 2²⁰ ≈ 10⁶ 個子集和，把後半的和放進 set，再對前半的每個和 a 檢查 `T - a` 是否在 set 中。時間 O(2^(n/2))，空間 O(2^(n/2))。這是背包 DP 的「偽多項式」限制最典型的反例：狀態維度是數值時，數值一大就要改成以 n 為主的演算法。

## 核心題 2｜494. Target Sum｜Medium

### 題目

給一個非負整數陣列 `nums` 和一個整數 `target`。在每個數前面放上 `+` 或 `-`，串成一個運算式，例如 `nums = [2, 1]` 可以得到 `+2-1`。回傳運算結果恰好等於 `target` 的運算式個數。限制：`1 <= len(nums) <= 20`，`0 <= nums[i] <= 1000`，`sum(nums) <= 1000`，`-1000 <= target <= 1000`。

- 範例 1：`nums = [1, 1, 1, 1, 1]`、`target = 3`，回傳 `5`：五個 1 中選一個放負號，其餘放正號，共五種。
- 範例 2：`nums = [1]`、`target = 1`，回傳 `1`。
- 範例 3（邊界）：`nums = [0, 0, 1]`、`target = 1`，回傳 `4`。兩個 0 各自可以放 + 或 −，運算結果都不變，`+0` 和 `-0` 被視為不同的運算式。
- 範例 4（邊界）：`nums = [1, 2]`、`target = 4`，回傳 `0`，因為 |target| 大於總和 3。

### 思路

暴力解是每個數各試 + 與 −，共 2ⁿ 種，n = 20 時約 10⁶，其實勉強可以，但這只是因為這題 n 很小；面試官要看的是你能不能把它化成多項式的 DP。直接的 DP 是 `dp[i][s]` = 前 i 個數能湊出運算結果 s 的方法數，s 的範圍是 `[-S, S]`，要加偏移量，時間 O(n · S)。這已經夠好，但有一個更漂亮的轉換。

關鍵觀察：令放正號的數的和為 P、放負號的數的和為 N，則 `P − N = target`、`P + N = S`，兩式相加得 **P = (S + target) / 2**。也就是說，只要挑出一個和為 P 的子集放正號，其餘放負號，運算結果就一定是 target，而且不同的子集對應不同的運算式（每個位置的符號由它是否在子集中唯一決定）。所以答案就是「和為 P 的子集個數」，這是 23.4 節的 0/1 計數背包。若 S + target 是奇數或為負，P 不是非負整數，答案為 0。

這個轉換把 s 的範圍從 2S + 1 縮小到 P + 1，而且不需要偏移量。0 的處理也自動正確：處理 x = 0 時，內層迴圈 `dp[s] += dp[s - 0]` 讓每個 `dp[s]` 加倍，正好對應「這個 0 放 + 或 − 兩種選擇」。

```text
nums = [1, 1, 1, 1, 1]，target = 3
S = 5，P = (5 + 3) / 2 = 4：挑出和為 4 的子集放正號

dp[s] = 和為 s 的子集個數（內層由大到小）
s:            0   1   2   3   4
初始           1   0   0   0   0
第 1 個 1 後    1   1   0   0   0
第 2 個 1 後    1   2   1   0   0
第 3 個 1 後    1   3   3   1   0
第 4 個 1 後    1   4   6   4   1
第 5 個 1 後    1   5  10  10   5   ← dp[4] = 5

每一列都是 dp_new[s] = dp_old[s] + dp_old[s-1]（巴斯卡三角形），
dp[4] = C(5, 4) = 5：從五個 1 中挑四個放正號。
```

表格剛好是巴斯卡三角形，因為所有數都是 1 時，「和為 s 的子集數」就是 C(i, s)。這讓我們可以快速檢查表格有沒有填錯。

### 解法

```python
import random
from functools import cache
from itertools import product


def find_target_sum_ways(nums: list[int], target: int) -> int:
    total = sum(nums)
    if abs(target) > total or (total + target) % 2:
        return 0
    p = (total + target) // 2
    dp = [1] + [0] * p
    for x in nums:
        for s in range(p, x - 1, -1):           # 0/1 計數背包：由大到小
            dp[s] += dp[s - x]
    return dp[p]


def find_target_sum_ways_memo(nums: list[int], target: int) -> int:
    """直接的 (i, 目前和) 記憶化，作為對照。"""
    @cache
    def go(i: int, cur: int) -> int:
        if i == len(nums):
            return int(cur == target)
        return go(i + 1, cur + nums[i]) + go(i + 1, cur - nums[i])
    return go(0, 0)


def brute(nums, target):
    return sum(sum(sg * x for sg, x in zip(signs, nums)) == target
               for signs in product((1, -1), repeat=len(nums)))


assert find_target_sum_ways([1, 1, 1, 1, 1], 3) == 5
assert find_target_sum_ways([1], 1) == 1
assert find_target_sum_ways([0, 0, 1], 1) == 4
assert find_target_sum_ways([1, 2], 4) == 0
assert find_target_sum_ways([1, 2], -3) == 1           # 負的 target
assert find_target_sum_ways([1, 2], 2) == 0            # S + target 為奇數
assert find_target_sum_ways([0, 0, 0], 0) == 8
for _ in range(500):
    arr = [random.randint(0, 5) for _ in range(random.randint(1, 8))]
    t = random.randint(-15, 15)
    assert find_target_sum_ways(arr, t) == find_target_sum_ways_memo(arr, t) == brute(arr, t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n · P)，P ≤ S ≤ 1000，空間 O(P)。記憶化版本的狀態是 (i, 目前和)，最多 n × (2S + 1) 個，時間 O(n · S)，同樣可以通過，但常數比較大。邊界情況：`abs(target) > S` 時 P 會是負數或大於 S，直接回傳 0；`(S + target)` 為奇數時 P 不是整數，回傳 0；`target` 為負時轉換仍然成立，因為 P = (S + target) / 2 只要非負就合法；元素為 0 時，內層迴圈的下界是 `0 - 1 = -1`，s 會一路走到 0，讓 `dp[0]` 也加倍，所以每個 0 讓答案乘 2，這正是題意要的。

### Follow-up

> [!question]- F1. 能不能讓表更小？如果 target 是很大的負數呢？
> 和為 P 的子集與和為 S − P 的子集一一對應（取補集），所以兩者的個數相同，可以改算 `min(P, S − P)`，表的大小最多 S / 2 + 1。S − P = (S − target) / 2 正是「放負號的數的和」N，所以 target 為很大的負數時，P 接近 0，表本來就小；target 為很大的正數時，改算 N 就好。這個觀察也說明了 `answer(target) == answer(-target)`，因為把所有符號翻轉就是一一對應。

> [!question]- F2. 如果要列出所有符合的運算式呢？
> 輸出本身可能有 2ⁿ 個（例如全部是 0 而 target = 0），所以任何演算法最差都是 O(2ⁿ · n)。做法是 backtracking（第 19 章），但可以用 DP 表剪枝：先從後往前算 `ways[i][s]` = 從第 i 個數開始湊出 s 的方法數，回溯時只走 `ways > 0` 的分支，保證每條探索的路徑最後都會產生一個答案，不會浪費時間在死路上。時間 O(n · S + 輸出大小 × n)。

> [!question]- F3. 如果每個數除了 + 和 −，還可以選擇「不使用」呢？
> 正負號的轉換不再成立，因為每個數有三種狀態，不能只用一個子集描述。回到直接的 DP：`dp[s]` = 目前運算結果為 s 的方法數，s 的範圍 `[-S, S]` 用偏移量 S 對應到 `[0, 2S]`，每個數 x 的轉移是 `new[s] = dp[s] + dp[s - x] + dp[s + x]`。因為同時從左右兩邊轉移，一維陣列無法原地更新，要用兩個陣列輪流。時間 O(n · S)，空間 O(S)。

> [!question]- F4. 如果 nums 可以有負數呢？
> 對負數 x 而言，放 + 或 − 等於對 |x| 放 − 或 +，所以把每個數取絕對值，方法數完全不變（一一對應：翻轉那個位置的符號）。取絕對值後就回到原題的轉換。這是面試中很好的一個觀察：先問「負數的符號會不會被我們放的符號吸收」，就不必重新設計 DP。

> [!question]- F5. 如果答案非常大，要對 10⁹ + 7 取餘數呢？
> 只要每次 `dp[s] = (dp[s] + dp[s - x]) % MOD` 即可，因為轉移只有加法，取餘數不影響正確性。Python 的整數不會溢位，但當 n 和 S 都很大時（例如 n = 10³、S = 10⁵），不取餘數會讓數字長到數百位數，每次加法變慢，所以就算不要求，取餘數也是常數優化。在 Java／C++ 中更是必須，否則 int 溢位。

## 核心題 3｜518. Coin Change II｜Medium

### 題目

給一個整數 `amount` 和一個面額互不相同的硬幣陣列 `coins`，每種硬幣可以無限使用。回傳湊出 `amount` 的**組合**數；只要使用的各面額數量相同，就算同一種組合，與順序無關。湊不出來回傳 0。限制：`1 <= len(coins) <= 300`，`1 <= coins[i] <= 5000`，`0 <= amount <= 5000`，答案保證在 32 位元有號整數範圍內。

- 範例 1：`amount = 5`、`coins = [1, 2, 5]`，回傳 `4`：`5`、`2+2+1`、`2+1+1+1`、`1+1+1+1+1`。
- 範例 2：`amount = 3`、`coins = [2]`，回傳 `0`。
- 範例 3（邊界）：`amount = 0`、`coins = [7]`，回傳 `1`：什麼都不拿就是一種組合。
- 範例 4：`amount = 10`、`coins = [10]`，回傳 `1`。

### 思路

暴力解是遞迴枚舉「每種硬幣用幾枚」，例如 `count(i, rest)` = 用第 i 種以後的硬幣湊出 rest 的組合數，枚舉第 i 種用 0、1、2… 枚，沒有記憶化時是指數級。加上記憶化後狀態是 (i, rest)，共 m × (amount + 1) 個，但每個狀態要枚舉用幾枚，轉移 O(amount / coin)，總時間 O(m · amount²) 的量級，仍然偏慢。

改進有兩步。第一步是去掉「枚舉用幾枚」：用第 i 種硬幣湊出 rest，要嘛一枚都不用（交給後面的硬幣），要嘛**至少用一枚**，拿掉一枚後還是可以繼續用第 i 種，所以 `count(i, rest) = count(i+1, rest) + count(i, rest - coin[i])`。這就是 23.3 節完全背包的「從同一列轉移」，轉移變成 O(1)。第二步是壓成一維：外層依序處理每種硬幣，內層金額由小到大，讓 `dp[j - c]` 讀到的是「已經可以用這種硬幣」的新值。

這題的核心陷阱是迴圈順序。如果外層金額、內層硬幣，`dp[j]` 枚舉的是「最後一枚是哪種硬幣」，`2+1+1+1` 和 `1+2+1+1` 會被當成不同的方法，得到的是排列數（377 題）。外層硬幣則強迫每種組合以「面額出現的順序」被構造一次：處理硬幣 2 時，所有方法都只含 1 和 2，處理硬幣 5 時再加上 5，不會有「先 2 再 1」的版本。不變式是：處理完前 i 種硬幣後，`dp[j]` = 只用前 i 種硬幣湊出 j 的組合數。

```text
coins = [1, 2, 5]，amount = 5，dp[j] += dp[j - c]（內層由小到大）
j:              0  1  2  3  4  5
初始             1  0  0  0  0  0
處理 1 後        1  1  1  1  1  1     只用 1：每個金額一種
處理 2 後        1  1  2  2  3  3     dp[4] = 1 + dp[2] = 1 + 2：{1111, 112, 22}
處理 5 後        1  1  2  2  3  4     dp[5] = 3 + dp[0] = 4：多了 {5}

處理 2 時 dp[4] 的細節（由小到大，dp[2] 已經更新過）：
dp[2] = 1 + dp[0] = 2          {11, 2}
dp[4] = 1 + dp[2] = 1 + 2 = 3  {1111} + {11 再加 2, 2 再加 2}
                                         └─ 112 ─┘ └─ 22 ─┘  ← 2 被用了兩次，因為 dp[2] 已含 2

錯誤順序（外層金額）得到的 dp：1 1 2 3 5 9
dp[3] = dp[2] + dp[1] = 3：{1+1+1, 2+1, 1+2} ← 2+1 和 1+2 被分開計算
```

第二列 `dp[4] = 3` 展示了完全背包「由小到大」的意義：更新 `dp[4]` 時讀到的 `dp[2]` 已經包含了「用一枚 2」的方法，所以 `22` 是在 `dp[2]` 的 `2` 之上再加一枚 2 得到的。錯誤順序得到 9 而不是 4，差距全部來自順序被重複計算。

### 解法

```python
import random
from functools import cache


def change(amount: int, coins: list[int]) -> int:
    dp = [1] + [0] * amount
    for c in coins:                            # 外層硬幣：保證只數組合
        for j in range(c, amount + 1):         # 內層由小到大：同一種硬幣可重複使用
            dp[j] += dp[j - c]
    return dp[amount]


def change_2d(amount: int, coins: list[int]) -> int:
    """二維版本：ways[i][j] = 只用前 i 種硬幣湊出 j 的組合數。"""
    m = len(coins)
    ways = [[0] * (amount + 1) for _ in range(m + 1)]
    ways[0][0] = 1
    for i in range(1, m + 1):
        c = coins[i - 1]
        for j in range(amount + 1):
            ways[i][j] = ways[i - 1][j] + (ways[i][j - c] if j >= c else 0)
    return ways[m][amount]


def brute(amount, coins):
    @cache
    def go(i, rest):                           # 第 i 種硬幣用幾枚，逐一枚舉
        if i == len(coins):
            return int(rest == 0)
        return sum(go(i + 1, rest - k * coins[i]) for k in range(rest // coins[i] + 1))
    return go(0, amount)


assert change(5, [1, 2, 5]) == 4
assert change(3, [2]) == 0
assert change(0, [7]) == 1
assert change(10, [10]) == 1
assert change(4, [2, 1]) == 3                  # 硬幣順序不影響組合數
assert change(500, [3, 5, 7, 8, 9, 10, 11]) == change_2d(500, [3, 5, 7, 8, 9, 10, 11])
for _ in range(300):
    cs = random.sample(range(1, 12), random.randint(1, 4))
    amt = random.randint(0, 30)
    assert change(amt, cs) == change_2d(amt, cs) == brute(amt, cs)
print("all tests passed")
```

### 複雜度與邊界

時間 O(m · amount)，m 是硬幣種類數，最多 300 × 5000 = 1.5 × 10⁶。空間 O(amount)。邊界情況：`amount = 0` 時回傳 `dp[0] = 1`，空組合也算一種；硬幣面額大於 amount 時內層迴圈不執行；面額互不相同是題目保證，若有重複面額，外層硬幣會把同一面額處理兩次，等於把它當成兩種不同的硬幣，答案會偏大，要先去重；題目只保證 `dp[amount]` 在 32 位元內，其他金額的 `dp[j]` 不一定（例如 `coins = [2]` 時 `dp[2] = 1` 而 `dp[3] = 0`，小金額的方法數完全可能比 amount 多），所以在 Java／C++ 中中間值可能溢位，要用 64 位元整數；Python 沒有這個問題。

### Follow-up

> [!question]- F1. 如果順序不同算不同的方法呢（377. Combination Sum IV）？
> 把兩層迴圈對調：外層金額 j 由 1 到 amount，內層枚舉所有硬幣 c，`dp[j] += dp[j - c]`。此時 `dp[j]` 的意義是「最後一枚是 c」的方法數加總，不同的順序走不同的分支，所以數的是排列。時間仍是 O(m · amount)。要注意 377 只保證最終答案在 32 位元內，中間的 `dp[j]` 卻可能溢位，所以在 Java／C++ 中常見做法是用 unsigned 或在超過上限時截斷；Python 沒有這個問題。
> ```python
> def combination_sum4(nums, target):
>     dp = [1] + [0] * target
>     for j in range(1, target + 1):
>         for c in nums:
>             if c <= j:
>                 dp[j] += dp[j - c]
>     return dp[target]
> ```

> [!question]- F2. 如果每種硬幣最多只能用一枚呢？
> 變成 0/1 計數背包，把內層改成由大到小：`for j in range(amount, c - 1, -1): dp[j] += dp[j - c]`。這樣 `dp[j - c]` 讀到的是「還沒用這枚硬幣」的舊值，每枚硬幣最多被算一次。這就是核心題 2（494）在轉換之後用的迴圈。同一個問題只改一個迴圈方向就從「無限次」變成「最多一次」，面試時能直接指出這一點，代表你理解兩者的差別。

> [!question]- F3. 如果第 i 種硬幣最多只能用 cnt[i] 枚（多重背包）呢？
> 直接展開成 cnt[i] 個 0/1 物品是 O(amount · Σcnt)。更好的做法是前綴和：用第 i 種硬幣 c 時，`new[j] = Σ_{t=0..cnt} old[j - t·c]`，也就是同一個餘數類（j mod c 相同）上、長度為 cnt + 1 的滑動視窗和。對每個餘數類由小到大維護視窗和，每種硬幣 O(amount)，總時間 O(m · amount)，與 cnt 無關。
> ```python
> def change_bounded(amount, coins, cnt):
>     dp = [1] + [0] * amount
>     for c, k in zip(coins, cnt):
>         new = dp[:]
>         for r in range(c):
>             window = 0
>             for idx, j in enumerate(range(r, amount + 1, c)):
>                 window += dp[j]
>                 if idx > k:
>                     window -= dp[j - (k + 1) * c]
>                 new[j] = window
>         dp = new
>     return dp[amount]
> ```

> [!question]- F4. 為什麼第 21 章核心題 2（322. Coin Change，最少硬幣數）不必在意迴圈順序？
> 322 求的是 `min`，同一個組合的不同排列給出相同的硬幣數，取最小值時重複計算不會改變結果；計數用 `+`，重複就會多算。所以 322 外層金額或外層硬幣都對，518 只有外層硬幣對。這個對比的一般規則是：**最佳化問題對重複不敏感，計數問題對重複敏感**。寫計數 DP 時，一定要先想清楚「每一種要數的東西，是不是恰好被一條轉移路徑產生」。

> [!question]- F5. 如果規定恰好使用 k 枚硬幣呢？
> 狀態多一維：`dp[t][j]` = 用恰好 t 枚硬幣湊出 j 的組合數。外層仍然是硬幣（保證組合），內層對 t 和 j 都由小到大：`dp[t][j] += dp[t-1][j-c]`，從「同一種硬幣處理中」的新值轉移，所以同一面額可以重複。時間 O(m · k · amount)，空間 O(k · amount)。若 k 很小，這個額外的維度幾乎不增加成本；若只要求「至多 k 枚」，答案是 Σ_{t ≤ k} dp[t][amount]。

## 核心題 4｜516. Longest Palindromic Subsequence｜Medium

### 題目

給一個字串 `s`，回傳它最長的回文子序列（palindromic subsequence）的長度。子序列是刪掉零個或多個字元、不改變剩下字元順序得到的字串，不必連續；回文是正讀反讀都一樣的字串。限制：`1 <= len(s) <= 1000`，`s` 只含小寫英文字母。

- 範例 1：`s = "bbbab"`，回傳 `4`，最長回文子序列是 `"bbbb"`（刪掉中間的 a）。
- 範例 2：`s = "cbbd"`，回傳 `2`，是 `"bb"`。
- 範例 3：`s = "character"`，回傳 `5`，例如 `"carac"`。
- 範例 4（邊界）：`s = "a"`，回傳 `1`；`s = "abcd"`，回傳 `1`，任何單一字元都是回文。

### 思路

暴力解是列舉 2ⁿ 個子序列，逐一檢查是否回文並記錄最長的，n = 1000 不可能。從左往右的一維 DP 也不好定義，因為一個字元能不能留下，取決於右邊有沒有對應的字元可以配對，資訊在兩端。這正是區間 DP 的訊號：**回文是從兩端往中間配對的**。

令 `dp[i][j]` = 子字串 `s[i..j]`（含兩端）中最長回文子序列的長度。看兩端的字元：

- `s[i] == s[j]`：兩者可以當作回文的最外層，`dp[i][j] = dp[i+1][j-1] + 2`。為什麼一定要配對？假設最佳解沒有同時用上 s[i] 和 s[j]，它就只用了 `s[i+1..j]` 或 `s[i..j-1]` 的字元，最外層的某個字元 c 可以換成 s[i] 和 s[j]（它們相等），長度不會變短，所以配對永遠不會更差。
- `s[i] != s[j]`：兩者不可能同時是回文的最外層，至少有一個要丟掉，`dp[i][j] = max(dp[i+1][j], dp[i][j-1])`。

基底是 `dp[i][i] = 1`，以及 i > j 的空區間為 0（`i + 1 > j - 1` 發生在長度 2 時）。每個狀態只依賴更短的區間，依 23.5 節的順序計算：i 由大到小、j 由小到大，或依長度遞增。

```text
s = "bbbab"，dp[i][j] = s[i..j] 的最長回文子序列長度
index:  0 1 2 3 4
s:      b b b a b

       j=0  j=1  j=2  j=3  j=4
i=0     1    2    3    3    4
i=1          1    2    2    3
i=2               1    1    3
i=3                    1    1
i=4                         1

i 由大到小計算（每一列從對角線往右）：
i=3：dp[3][4]：a ≠ b → max(dp[4][4], dp[3][3]) = 1
i=2：dp[2][3]：b ≠ a → max(1, 1) = 1
     dp[2][4]：b == b → dp[3][3] + 2 = 3              "bab"
i=1：dp[1][2]：b == b → dp[2][1](空) + 2 = 2
     dp[1][3]：b ≠ a → max(dp[2][3]=1, dp[1][2]=2) = 2
     dp[1][4]：b == b → dp[2][3] + 2 = 3              "bbb" 或 "bab"
i=0：dp[0][4]：b == b → dp[1][3] + 2 = 4              "bbbb"
```

最後一格 `dp[0][4]` 的兩端都是 b，配對後問題縮小成 `s[1..3] = "bba"`，那裡的最佳是 `"bb"`，外面包上一對 b 得到 `"bbbb"`。注意 `dp[1][2]` 讀到的 `dp[2][1]` 是 i > j 的空區間，必須當作 0，程式中靠陣列初始值 0 處理。

### 解法

```python
import random
from functools import cache
from itertools import combinations


def longest_palindrome_subseq(s: str) -> int:
    n = len(s)
    dp = [[0] * n for _ in range(n)]
    for i in range(n - 1, -1, -1):              # i 由大到小：dp[i+1][*] 已經算好
        dp[i][i] = 1
        for j in range(i + 1, n):               # j 由小到大：dp[i][j-1] 已經算好
            if s[i] == s[j]:
                dp[i][j] = dp[i + 1][j - 1] + 2  # 長度 2 時讀到 dp[i+1][i] = 0
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j - 1])
    return dp[0][n - 1]


def longest_palindrome_subseq_1d(s: str) -> int:
    """O(n) 空間：只保留第 i+1 列，用 prev_diag 記住 dp[i+1][j-1]。"""
    n = len(s)
    row = [0] * n                               # row[j] 代表 dp[i+1][j]
    for i in range(n - 1, -1, -1):
        prev_diag = 0                           # dp[i+1][i]，空區間
        row[i] = 1
        for j in range(i + 1, n):
            keep = row[j]                       # dp[i+1][j]，覆蓋前先存起來
            if s[i] == s[j]:
                row[j] = prev_diag + 2
            else:
                row[j] = max(row[j], row[j - 1])
            prev_diag = keep
    return row[n - 1]


def brute(s):
    for k in range(len(s), 0, -1):
        for idx in combinations(range(len(s)), k):
            t = "".join(s[i] for i in idx)
            if t == t[::-1]:
                return k
    return 0


assert longest_palindrome_subseq("bbbab") == 4
assert longest_palindrome_subseq("cbbd") == 2
assert longest_palindrome_subseq("character") == 5
assert longest_palindrome_subseq("a") == 1
assert longest_palindrome_subseq("abcd") == 1
assert longest_palindrome_subseq("aaaa") == 4
for _ in range(400):
    t = "".join(random.choice("abc") for _ in range(random.randint(1, 10)))
    assert longest_palindrome_subseq(t) == longest_palindrome_subseq_1d(t) == brute(t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n²)，共 n(n + 1) / 2 個狀態，每個 O(1)；n = 1000 時約 5 × 10⁵ 次計算。二維版本空間 O(n²)，一維版本 O(n)。邊界情況：長度 1 時迴圈只設 `dp[0][0] = 1`；長度 2 且兩字元相同時讀到 `dp[i+1][i]`，那是空區間，值為 0，所以結果是 2；全部字元相同時答案是 n；全部字元不同時答案是 1。一維版本最容易錯的是 `prev_diag`：更新 `row[j]` 之前要先存下舊的 `row[j]`（也就是 `dp[i+1][j]`），它會在下一個 j 變成 `dp[i+1][j]`，也就是新 j 的左下對角。

### Follow-up

> [!question]- F1. 如果要回傳實際的回文子序列呢？
> 保留二維表，從 `(0, n-1)` 開始往內走：兩端相等就把字元放進「左半」並走到 `(i+1, j-1)`；不相等就走到 `dp[i+1][j]` 與 `dp[i][j-1]` 中較大的那一邊；當 `i == j` 時那個字元是正中間。最後答案是 `左半 + 中間 + reversed(左半)`。回溯最多走 n 步，總時間仍是 O(n²)，空間 O(n²)。
> ```python
> def lps_string(s):
>     n = len(s)
>     dp = [[0] * n for _ in range(n)]
>     for i in range(n - 1, -1, -1):
>         dp[i][i] = 1
>         for j in range(i + 1, n):
>             dp[i][j] = dp[i + 1][j - 1] + 2 if s[i] == s[j] else max(dp[i + 1][j], dp[i][j - 1])
>     left, mid, i, j = [], "", 0, n - 1
>     while i <= j:
>         if i == j:
>             mid = s[i]
>             break
>         if s[i] == s[j]:
>             left.append(s[i]); i += 1; j -= 1
>         elif dp[i + 1][j] >= dp[i][j - 1]:
>             i += 1
>         else:
>             j -= 1
>     return "".join(left) + mid + "".join(reversed(left))
> ```

> [!question]- F2. 為什麼「s 和 reverse(s) 的最長公共子序列」也等於答案？
> 任何回文子序列 p 在 s 中出現，它的反轉 p 也在 reverse(s) 中出現，所以 LPS ≤ LCS(s, reverse(s))。反方向較微妙：s 與 reverse(s) 的某個最長公共子序列本身不一定是回文，但已知一定存在一個等長的回文公共子序列（把公共子序列在 s 中的位置與它在 reverse(s) 中對應的位置配對，取較好的一半再鏡射即可構造），所以兩者長度相等，可以直接套用第 22 章核心題 3（1143）的 LCS 模板，時間空間同樣 O(n²)。面試時兩種都可以，但區間 DP 的寫法更直接，也更容易回溯出真正的回文。

> [!question]- F3. 和第 25 章核心題 1（5. Longest Palindromic Substring）有什麼不同？
> 子字串要求連續，所以兩端不相等時不能「丟掉一端繼續找」，`s[i..j]` 是回文若且唯若 `s[i] == s[j]` 且 `s[i+1..j-1]` 是回文，狀態是布林值而不是長度。這讓子字串版本可以用「中心擴展」做到 O(n²) 時間、O(1) 空間，甚至用 Manacher 做到 O(n)；子序列版本則沒有已知的 O(n^(2−ε)) 一般解法（它和 LCS 一樣，在常見的複雜度假設下被認為無法顯著快於 O(n²)）。面試官常把兩題放在一起問，重點是說出「不連續時 `max(dp[i+1][j], dp[i][j-1])` 這個轉移才有意義」。

> [!question]- F4. 如果問「最多刪掉 k 個字元能否變成回文」呢（1216. Valid Palindrome III）？
> 刪掉的字元數最少是 n − LPS（留下最長回文子序列，其他全刪），所以答案是 `n - longest_palindrome_subseq(s) <= k`，O(n²)。若 n 很大（例如 10⁵）而 k 很小，可以把問題轉成 s 與 reverse(s) 之間「只允許插入與刪除」的編輯距離：它恰好等於 2 × (n − LPS)，條件變成編輯距離 ≤ 2k。編輯距離 ≤ 2k 的路徑不可能離開主對角線超過 2k 格，所以只要計算寬度 O(k) 的對角帶，時間 O(n · k)。

> [!question]- F5. 如果要數「不同的」回文子序列有幾個呢（730. Count Different Palindromic Subsequences）？
> 計數時重複是主要難點：`"aa"` 的回文子序列 `"a"` 不論取哪個位置都只算一次。做法是讓狀態再加一維「最外層字元是哪個字母」，或在 `s[i] == s[j]` 時找出 `(i, j)` 內與 s[i] 相同的最左與最右位置 l、r，依內部同字母的個數分三種情況：沒有時 `dp[i][j] = 2·dp[i+1][j-1] + 2`（多了單字母與雙字母兩個新回文）；恰好一個時 `2·dp[i+1][j-1] + 1`（單字母已經算過）；至少兩個時 `2·dp[i+1][j-1] − dp[l+1][r-1]`（扣掉被 l、r 包住而重複的部分）。兩端不同時用排容 `dp[i+1][j] + dp[i][j-1] − dp[i+1][j-1]`。時間 O(n²)（預處理 next／prev 位置）。這題展示了區間 DP 在計數時要格外處理重複，和 23.4 節「組合 vs 排列」是同一類問題。

## 核心題 5｜1312. Minimum Insertion Steps to Make a String Palindrome｜Hard

### 題目

給一個字串 `s`，每一步可以在任意位置插入任意一個字元。回傳讓 `s` 變成回文所需的最少步數。限制：`1 <= len(s) <= 500`，`s` 只含小寫英文字母。

- 範例 1：`s = "zzazz"`，回傳 `0`，本來就是回文。
- 範例 2：`s = "mbadm"`，回傳 `2`，例如插入成 `"mbdadbm"` 或 `"mbadabm"`。
- 範例 3：`s = "leetcode"`，回傳 `5`，例如 `"leetcodocteel"`。
- 範例 4（邊界）：`s = "a"`，回傳 `0`；`s = "ab"`，回傳 `1`（`"aba"` 或 `"bab"`）。

### 思路

暴力解是 BFS：每一步在 n + 1 個位置插入 26 種字元之一，搜尋第一個變成回文的字串，分支數巨大，完全不可行。換個角度看最終的回文：它的兩端一定相等。對原字串的兩端 `s[i]` 與 `s[j]`，只有兩種情況：

- `s[i] == s[j]`：讓它們互相配對當最外層，問題縮小成 `s[i+1..j-1]`，`dp[i][j] = dp[i+1][j-1]`。
- `s[i] != s[j]`：它們不能互相配對，所以最外層一定有一個是插入的字元。插入一個 `s[i]` 在右端讓 `s[i]` 配對，剩下 `s[i+1..j]`；或插入一個 `s[j]` 在左端，剩下 `s[i..j-1]`。`dp[i][j] = 1 + min(dp[i+1][j], dp[i][j-1])`。

基底：長度 ≤ 1 的區間已經是回文，`dp[i][i] = 0`，空區間也是 0。這和核心題 4 的結構幾乎一模一樣，差別只是把「最長保留多少」換成「最少插入多少」。事實上兩者有一個精確的關係：**最少插入數 = n − LPS(s)**。直覺是：最長回文子序列的字元可以直接當作骨架，其他每個字元都需要插入一個鏡像字元來配對；反過來，任何插入 k 個字元得到的回文中，原字元彼此配對的那些構成 s 的一個回文子序列，長度至少 n − k。

```text
s = "mbadm"，dp[i][j] = 讓 s[i..j] 變成回文的最少插入數
index:  0 1 2 3 4
s:      m b a d m

       j=0  j=1  j=2  j=3  j=4
i=0     0    1    2    3    2
i=1          0    1    2    3
i=2               0    1    2
i=3                    0    1
i=4                         0

依長度計算：
長度 2：dp[0][1] "mb"：m ≠ b → 1 + min(0, 0) = 1；dp[1][2]、dp[2][3]、dp[3][4] 同理都是 1
長度 3：dp[1][3] "bad"：b ≠ d → 1 + min(dp[2][3]=1, dp[1][2]=1) = 2
        dp[0][2] "mba"：2；dp[2][4] "adm"：2
長度 4：dp[0][3] "mbad"：1 + min(dp[1][3]=2, dp[0][2]=2) = 3
        dp[1][4] "badm"：1 + min(dp[2][4]=2, dp[1][3]=2) = 3
長度 5：dp[0][4] "mbadm"：m == m → dp[1][3] = 2

驗證關係：LPS("mbadm") = 3（例如 "mam"、"mbm"），n − LPS = 5 − 3 = 2 ✓
```

最後一格的兩端都是 m，直接配對，問題變成讓 `"bad"` 變回文；`"bad"` 的兩端不同，例如先在右邊插入 b 變成 `"badb"`，再處理 `"ad"`，插入一個 a 或 d，總共 2 步，得到 `"mbdadbm"`。

### 解法

```python
import random
from collections import deque


def min_insertions(s: str) -> int:
    n = len(s)
    dp = [[0] * n for _ in range(n)]
    for length in range(2, n + 1):                  # 依長度由小到大
        for i in range(n - length + 1):
            j = i + length - 1
            if s[i] == s[j]:
                dp[i][j] = dp[i + 1][j - 1]          # 長度 2 時讀到 dp[i+1][i] = 0
            else:
                dp[i][j] = 1 + min(dp[i + 1][j], dp[i][j - 1])
    return dp[0][n - 1]


def min_insertions_via_lps(s: str) -> int:
    n = len(s)
    row = [0] * n
    for i in range(n - 1, -1, -1):                  # 核心題 4 的一維 LPS
        prev_diag, row[i] = 0, 1
        for j in range(i + 1, n):
            keep = row[j]
            row[j] = prev_diag + 2 if s[i] == s[j] else max(row[j], row[j - 1])
            prev_diag = keep
    return n - row[n - 1]


def brute(s):
    """BFS：每一步在任意位置插入 s 中出現過的字元（插入其他字元不會更好）。"""
    seen, q = {s}, deque([(s, 0)])
    while q:
        t, d = q.popleft()
        if t == t[::-1]:
            return d
        for p in range(len(t) + 1):
            for c in set(s):
                u = t[:p] + c + t[p:]
                if u not in seen:
                    seen.add(u)
                    q.append((u, d + 1))


assert min_insertions("zzazz") == 0
assert min_insertions("mbadm") == 2
assert min_insertions("leetcode") == 5
assert min_insertions("a") == 0
assert min_insertions("ab") == 1
assert min_insertions("abcd") == 3
for _ in range(200):
    t = "".join(random.choice("ab") for _ in range(random.randint(1, 6)))
    assert min_insertions(t) == min_insertions_via_lps(t) == brute(t)
for _ in range(300):
    t = "".join(random.choice("abcd") for _ in range(random.randint(1, 12)))
    assert min_insertions(t) == min_insertions_via_lps(t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n²)，n = 500 時約 1.25 × 10⁵ 個狀態。二維版本空間 O(n²)，透過 LPS 的一維版本空間 O(n)。邊界情況：長度 1 時迴圈不執行，回傳 0；長度 2 且兩字元相同時讀到 `dp[i+1][i]`，空區間為 0；全部字元不同時答案是 n − 1（保留任一個字元當中心，其他全部鏡像）；已經是回文時答案是 0。這題標為 Hard，但難點只在「想到區間 DP」，一旦狀態定義對了，程式和核心題 4 幾乎相同。

### Follow-up

> [!question]- F1. 如果要輸出插入後的回文字串呢？
> 從 `(0, n-1)` 依 DP 表往內走：兩端相等就把 s[i] 同時放在左右；不相等時，若 `dp[i+1][j] <= dp[i][j-1]`，代表插入一個 s[i] 在右邊配對比較好，把 s[i] 放在左右兩邊並走到 `(i+1, j)`；否則把 s[j] 放在左右兩邊並走到 `(i, j-1)`。左邊的字元依序放進 `left`、右邊的放進 `right`，最後答案是 `left + 中間 + reversed(right)`。回溯 O(n)，總時間 O(n²)。
> ```python
> def make_palindrome(s):
>     n = len(s)
>     dp = [[0] * n for _ in range(n)]
>     for length in range(2, n + 1):
>         for i in range(n - length + 1):
>             j = i + length - 1
>             dp[i][j] = dp[i + 1][j - 1] if s[i] == s[j] else 1 + min(dp[i + 1][j], dp[i][j - 1])
>     left, mid, i, j = [], "", 0, n - 1
>     while i <= j:
>         if i == j:
>             mid = s[i]; break
>         if s[i] == s[j]:
>             left.append(s[i]); i += 1; j -= 1
>         elif dp[i + 1][j] <= dp[i][j - 1]:
>             left.append(s[i]); i += 1
>         else:
>             left.append(s[j]); j -= 1
>     return "".join(left) + mid + "".join(reversed(left))
> ```

> [!question]- F2. 如果只能在字串的最前面插入呢（214. Shortest Palindrome）？
> 那就不需要 DP：只能在前面加字元時，原字串必須保留一個「最長的回文前綴」，剩下的後綴反轉後加到最前面。找最長回文前綴可以用 KMP 的 failure function：對 `s + "#" + reverse(s)` 算 prefix function，最後一個值就是最長回文前綴的長度，O(n)。這是第 25 章難題 1。對比這兩題能看出：插入位置任意時要考慮兩端的所有配對方式（區間 DP），插入位置固定時結構簡單很多。

> [!question]- F3. 如果改成「最少刪除幾個字元變成回文」呢？
> 答案完全相同，都是 n − LPS(s)。刪除一個沒有配對的字元，和插入一個它的鏡像字元，效果都是「讓它不再需要配對」。DP 轉移也一樣：兩端不同時 `1 + min(dp[i+1][j], dp[i][j-1])`，只是語意從「插入鏡像」變成「刪掉一端」。如果插入和刪除都允許、每次成本 1，答案仍然不變，因為兩種操作在這個問題中可以互相替代，混用不會更省。

> [!question]- F4. 如果還允許「把一個字元替換成另一個」，三種操作成本都是 1 呢？
> 替換能一次解決一對不相等的兩端（把其中一個改成另一個），所以轉移多一個選項：`s[i] != s[j]` 時 `dp[i][j] = min(1 + dp[i+1][j], 1 + dp[i][j-1], 1 + dp[i+1][j-1])`。這類似第 22 章核心題 4（72. Edit Distance）的三種操作，只是比對的對象是字串自己的兩端。時間仍是 O(n²)。若只允許替換，答案就是不相等的對稱位置對數 `sum(s[i] != s[n-1-i] for i in range(n // 2))`，O(n)，不需要 DP。

> [!question]- F5. 如果插入不同字元的成本不同（插入字元 c 的成本是 cost[c]）呢？
> 兩端不同時，插入 s[i] 的鏡像成本是 `cost[s[i]]`，插入 s[j] 的鏡像成本是 `cost[s[j]]`，所以 `dp[i][j] = min(cost[s[i]] + dp[i+1][j], cost[s[j]] + dp[i][j-1])`。兩端相同時仍然可以直接配對：可以證明 `dp[i+1][j-1] <= dp[i+1][j] + cost[s[j]]`（把 s[j] 從任何一個解中拿掉，最多讓一個原本與它配對的同字元改成需要插入，成本恰好是 `cost[s[j]]`），所以配對不會比插入更差。保守的寫法是三種選項都取 min，複雜度不變，O(n²)。

## 難題 1｜312. Burst Balloons｜Hard

### 題目

有 n 顆氣球排成一列，第 i 顆上面寫著數字 `nums[i]`。你要把所有氣球戳破，順序自選。戳破第 i 顆時，得到 `left × nums[i] × right` 枚硬幣，其中 left、right 是**當下**它左右兩邊還沒被戳破的相鄰氣球的數字；如果某一邊已經沒有氣球，就把那邊當作數字 1。戳破之後，它原本的左右鄰居會變成相鄰。回傳能得到的最多硬幣數。限制：`1 <= n <= 300`，`0 <= nums[i] <= 100`。

- 範例 1：`nums = [3, 1, 5, 8]`，回傳 `167`。順序是戳 1（3·1·5 = 15）→ 戳 5（3·5·8 = 120）→ 戳 3（1·3·8 = 24）→ 戳 8（1·8·1 = 8），共 167。
- 範例 2：`nums = [1, 5]`，回傳 `10`：先戳 1 得 1·1·5 = 5，再戳 5 得 1·5·1 = 5。
- 範例 3（邊界）：`nums = [7]`，回傳 `7`（1·7·1）。
- 範例 4（邊界）：`nums = [0, 0]`，回傳 `0`。

### 提示

> [!tip]- 提示 1
> 試著定義「區間 [i, j] 的最佳答案」並枚舉第一顆戳破的氣球，你會發現它戳破之後，左右兩段的氣球變成鄰居，兩段不再獨立。換一個角度：如果枚舉的是區間內**最後**一顆被戳破的氣球呢？

> [!tip]- 提示 2
> 在兩端各補一顆數字 1 的虛擬氣球。令 `dp[i][j]` = 只戳破 i 和 j **之間**（不含 i、j）的所有氣球，而 i、j 本身保留到最後時，能得到的最多硬幣。

> [!tip]- 提示 3
> 若 k 是 (i, j) 之間最後被戳破的，戳它的時候它的鄰居一定是 i 和 j，得分 `a[i]·a[k]·a[j]`；在那之前，(i, k) 和 (k, j) 兩段被 k 隔開、互不影響。`dp[i][j] = max over k (dp[i][k] + dp[k][j] + a[i]·a[k]·a[j])`，依區間長度由小到大計算。

### 詳解

**為什麼直覺做法行不通**。暴力解枚舉 n! 種戳破順序，n = 300 完全不可能；用 bitmask 記住「哪些已經戳破」是 O(2ⁿ · n)，也只能處理 n ≤ 20。自然會想區間 DP：`f(i, j)` = 戳破 `nums[i..j]` 的最多硬幣，枚舉第一顆戳 k。但戳破 k 之後，k − 1 和 k + 1 變成鄰居，左段 `[i, k-1]` 的最後一顆和右段 `[k+1, j]` 的第一顆會互相影響得分，兩段沒有辦法分開求解。問題的根源是：「第一顆」決定之後，剩下的結構反而變複雜了。

**突破點：枚舉最後一顆**。反過來想區間內**最後**被戳破的那顆 k。當 k 被戳破時，區間內其他氣球都已經不在了，所以它的鄰居一定是區間外側的兩顆，數字固定。更重要的是，在 k 被戳破之前，k 一直存在，它像一面牆把區間隔成左右兩段：左段的氣球不論怎麼戳，鄰居都不會越過 k；右段亦然。所以兩段完全獨立。為了讓「區間外側的兩顆」永遠存在，在陣列頭尾補上數字 1，令 `a = [1] + nums + [1]`，`dp[i][j]` 定義為**開區間** (i, j) 內所有氣球都戳破、i 與 j 保留時的最大得分：

`dp[i][j] = max over i < k < j (dp[i][k] + dp[k][j] + a[i]·a[k]·a[j])`，`j = i + 1` 時區間內沒有氣球，`dp = 0`。答案是 `dp[0][n+1]`。

**正確性**。任何戳破順序都恰好有一顆最後戳破的 k，而給定 k，最佳得分就是兩段各自的最佳加上最後一擊，所以取所有 k 的最大值不會漏掉最佳解；反過來，任何「左段的某個順序 + 右段的某個順序 + 最後 k」都能交錯成一個真實的戳破順序，所以 DP 的值都是可以達到的。計算順序依開區間的寬度 `j − i` 由 2 往上，`dp[i][k]` 與 `dp[k][j]` 的寬度都更小，一定已經算好。

```text
nums = [3, 1, 5, 8]，補上邊界後 a = [1, 3, 1, 5, 8, 1]
index:   0  1  2  3  4  5
a:       1  3  1  5  8  1

dp[i][j] = 戳破開區間 (i, j) 內所有氣球的最大得分
       j=1  j=2  j=3  j=4  j=5
i=0     0    3   30  159  167
i=1          0   15  135  159
i=2               0   40   48
i=3                    0   40
i=4                         0

寬度 2（區間內只有一顆）：dp[i][i+2] = a[i]·a[i+1]·a[i+2]
  dp[0][2] = 1·3·1 = 3，dp[1][3] = 3·1·5 = 15，dp[2][4] = 1·5·8 = 40，dp[3][5] = 5·8·1 = 40
寬度 3：dp[1][4]（區間內是 1、5，邊界 3 與 8）
  k=2 最後戳 1：dp[1][2] + dp[2][4] + 3·1·8 = 0 + 40 + 24 = 64
  k=3 最後戳 5：dp[1][3] + dp[3][4] + 3·5·8 = 15 + 0 + 120 = 135 ← 最佳
寬度 5：dp[0][5]（整個陣列）
  k=1 最後戳 3：dp[0][1] + dp[1][5] + 1·3·1 =   0 + 159 + 3 = 162
  k=2 最後戳 1：dp[0][2] + dp[2][5] + 1·1·1 =   3 +  48 + 1 =  52
  k=3 最後戳 5：dp[0][3] + dp[3][5] + 1·5·1 =  30 +  40 + 5 =  75
  k=4 最後戳 8：dp[0][4] + dp[4][5] + 1·8·1 = 159 +   0 + 8 = 167 ← 最佳
```

`dp[0][5]` 的最佳選擇是最後戳 8，代表 8 一直留著當作右側的牆，左邊的 3、1、5 都在 8 存在的情況下被戳破，其中 5 在戳破時能拿到 `3·5·8 = 120` 這個大分數，正是因為 8 還在。這也解釋了為什麼「最後一顆」的觀點自然：大的數字應該留到後面，當作別人的鄰居。

### 解法

```python
import random
from itertools import permutations


def max_coins(nums: list[int]) -> int:
    a = [1] + nums + [1]
    m = len(a)
    dp = [[0] * m for _ in range(m)]
    for width in range(2, m):                    # 開區間 (i, j) 的寬度 j - i
        for i in range(m - width):
            j = i + width
            ai_aj = a[i] * a[j]
            best = 0
            for k in range(i + 1, j):            # k 是 (i, j) 中最後被戳破的
                cand = dp[i][k] + dp[k][j] + ai_aj * a[k]
                if cand > best:
                    best = cand
            dp[i][j] = best
    return dp[0][m - 1]


def brute(nums):
    best = 0
    for order in permutations(range(len(nums))):
        alive, total = list(range(len(nums))), 0
        for idx in order:
            p = alive.index(idx)
            left = nums[alive[p - 1]] if p > 0 else 1
            right = nums[alive[p + 1]] if p + 1 < len(alive) else 1
            total += left * nums[idx] * right
            alive.pop(p)
        best = max(best, total)
    return best


assert max_coins([3, 1, 5, 8]) == 167
assert max_coins([1, 5]) == 10
assert max_coins([7]) == 7
assert max_coins([0, 0]) == 0
assert max_coins([5, 0, 5]) == 30               # 先戳 0，兩個 5 變成鄰居：0 + 25 + 5
for _ in range(200):
    arr = [random.randint(0, 9) for _ in range(random.randint(1, 6))]
    assert max_coins(arr) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n³)：O(n²) 個區間，每個枚舉 O(n) 個 k，實際次數約 n³ / 6，n = 300 時約 4.5 × 10⁶，Python 可以接受。空間 O(n²)。邊界情況：n = 1 時只有寬度 2 的一格，答案是 `1·nums[0]·1`；數字為 0 的氣球最好早點戳（F3）；`dp` 的開區間定義讓 j = i + 1 的格子自然是 0，不需要特判。最常見的 bug 是把 dp 定義成閉區間卻用 `a[i-1]`、`a[j+1]` 當邊界，索引很容易錯一格；用開區間加上虛擬邊界，所有乘積都在陣列內。

### Follow-up

> [!question]- F1. 如果要輸出實際的戳破順序呢？
> 計算 dp 時另外記錄 `choice[i][j]` = 讓 `dp[i][j]` 最大的 k。輸出順序時遞迴：`order(i, j)` = `order(i, k) + order(k, j) + [k]`，k 放在最後，因為它是這個區間最後戳的；左右兩段誰先誰後都可以（它們互不影響），這裡選擇先左後右。總長度 n，回溯 O(n)，整體仍是 O(n³)。輸出的是補上邊界後的索引，要減 1 換回原陣列的索引。

> [!question]- F2. 這和矩陣連乘（matrix chain multiplication）有什麼關係？
> 矩陣連乘：有 n 個矩陣，第 t 個的尺寸是 `d[t-1] × d[t]`，選擇乘法的括號方式讓純量乘法次數最少。`cost[i][j]` = 把第 i + 1 到第 j 個矩陣乘起來的最小成本，最後一次乘法在 k 切開：`cost[i][j] = min over k (cost[i][k] + cost[k][j] + d[i]·d[k]·d[j])`。這和本題的轉移一模一樣，只是 max 換成 min。所以本題可以理解成：把 a 看成維度序列，每戳一顆氣球就是「消掉一個中間維度」。很多面試官會用這個對比確認你理解的是結構，而不是背了題目。

> [!question]- F3. 數字是 0 的氣球可以怎麼處理？
> 可以先把所有 0 去掉再跑 DP。理由是交換論證：在任何順序中把一顆 0 改成「第一個戳」，它自己的得分本來就是 0，不會損失；而原本以它為鄰居的那些戳破，得分本來是 0，現在換成其他非負數的鄰居，只會增加或不變；其他戳破的鄰居不受影響。所以存在一個最佳解先戳掉所有 0，等價於直接刪除它們。這把 n 縮小，在 0 很多時能大幅減少 O(n³) 的工作量。

> [!question]- F4. 如果規定每次只能戳最左邊或最右邊的氣球呢？
> 這時剩下的氣球永遠是連續的一段 `[l, r]`，而且它外側的氣球都已經戳破，所以鄰居很單純：戳最左邊的 `a[l]` 得 `1 · a[l] · a[l+1]`（若 l == r 則 `1 · a[l] · 1`），戳最右邊同理。`f[l][r] = max(a[l]·a[l+1] + f[l+1][r], a[r-1]·a[r] + f[l][r-1])`，轉移 O(1)，總時間 O(n²)。有趣的是這裡「第一步」的觀點就行得通，因為限制讓剩下的集合永遠是一個區間，不會出現兩段互相影響的情況；原題的困難正是來自「戳中間會讓兩段接起來」。

### 心得

關鍵突破是把「第一顆戳哪顆」換成「最後一顆戳哪顆」：最後戳的 k 在整個過程中都存在，像一面牆把區間切成兩個獨立的子問題，而且它被戳時的鄰居固定是區間外側的兩顆。這是本章「選對最後一步」最經典的例子，難題 5（1547）則是反方向「選第一步」也能成立的對照，兩題放在一起看最能理解為什麼。面試時建議先說明「枚舉第一顆會讓兩邊接起來、子問題不獨立」，讓面試官看到你試過直覺做法並找出它失敗的原因，再提出補上邊界 1、開區間 `dp[i][j]`、枚舉最後一顆的轉移，最後用 `[3, 1, 5, 8]` 手算 `dp[1][4]` 驗證。

## 難題 2｜664. Strange Printer｜Hard

### 題目

有一台奇怪的印表機，每一次操作可以選擇一個連續的區間和一個字元，把那個區間全部印成該字元，新印的會**覆蓋**原本的內容。一開始紙是空白的。給一個字串 `s`，回傳印出它所需的最少操作次數。限制：`1 <= len(s) <= 100`，`s` 只含小寫英文字母。

- 範例 1：`s = "aaabbb"`，回傳 `2`：先印 `aaa`，再印 `bbb`。
- 範例 2：`s = "aba"`，回傳 `2`：先把整段印成 `aaa`，再在中間印 `b`。
- 範例 3：`s = "abcabc"`，回傳 `5`。
- 範例 4（邊界）：`s = "a"`，回傳 `1`；`s = "abab"`，回傳 `3`。

### 提示

> [!tip]- 提示 1
> 連續相同的字元一定可以一起印，先把它們壓成一個。接著想：最左邊的字元 s[i] 一定被某一筆印出來，那一筆最好往右延伸到哪裡？

> [!tip]- 提示 2
> 令 `dp[i][j]` = 印出 `s[i..j]` 的最少次數。最簡單的選擇是 s[i] 自己印一筆：`1 + dp[i+1][j]`。什麼時候 s[i] 那一筆可以「免費」順便印到別的位置？

> [!tip]- 提示 3
> 如果 `s[k] == s[i]`（i < k ≤ j），可以讓印 s[k] 的那一筆往左延伸蓋到 i，中間的 `s[i+1..k-1]` 再印在它上面。成本是 `dp[i+1][k-1] + dp[k][j]`，s[i] 不需要額外的一筆。取所有選擇的最小值。

### 詳解

**為什麼直覺做法行不通**。貪婪的「每次印最長的同字元區段」會失敗，例如 `"aba"` 若先分段印 a、b、a 要 3 次，但先印一整段 a 再補 b 只要 2 次，因為覆蓋讓「先印大範圍、再修中間」變得有利。狀態空間搜尋（目前紙上是什麼）是指數級。我們需要一個區間 DP，但要找到正確的「第一個字元怎麼處理」的分解方式。

**突破點：讓 s[i] 搭別人的便車**。考慮 `s[i..j]` 的最左字元 s[i]。在某個最佳解中，印出 s[i] 最終顏色的那一筆，可以假設是這個區間的**第一筆**（在它之前蓋過位置 i 的筆都會被它蓋掉，對 i 沒有貢獻；對其他位置的貢獻可以調整順序保留）。這一筆從 i 往右延伸到某處，在它覆蓋的範圍中，最後仍然顯示 s[i] 顏色的位置都是和 s[i] 相同的字元。有兩種情況：

- 這一筆只負責 s[i] 本身（或延伸範圍內沒有其他位置最終顯示這個顏色）：成本 `1 + dp[i+1][j]`。
- 這一筆延伸到某個同色位置 k（`s[k] == s[i]`），並且 k 最終也顯示這個顏色。那麼 `s[i+1..k-1]` 是在這一筆之上獨立印的，成本 `dp[i+1][k-1]`；而 `s[k..j]` 這部分，我們把「印 s[k] 的那一筆」視為同一筆向左延伸到 i，所以 s[i] 不額外花成本，總共 `dp[i+1][k-1] + dp[k][j]`。

`dp[i][j] = min(1 + dp[i+1][j], min over k (dp[i+1][k-1] + dp[k][j]))`，其中 k 取 `(i, j]` 中所有 `s[k] == s[i]` 的位置，空區間的 dp 為 0。所有依賴的區間都比 [i, j] 短，所以 i 由大到小、j 由小到大計算即可。

**正確性的直覺**。上面兩種情況窮舉了「s[i] 那一筆最遠影響到哪個同色位置」，每一種都把問題拆成兩個獨立的子區間：被這一筆蓋住、但最終顯示別的顏色的中段，以及從 k 開始的右段。因為這一筆在最底層，中段的筆都印在它上面，不會影響 k 以右；右段中與 s[k] 同一筆的部分已經被算進 `dp[k][j]`。本題的程式用 BFS 暴力解在小字串上驗證過，兩者完全一致。

```text
s = "abcba"（沒有連續重複，不必壓縮）
index:  0 1 2 3 4
s:      a b c b a

       j=0  j=1  j=2  j=3  j=4
i=0     1    2    3    3    3
i=1          1    2    2    3
i=2               1    2    3
i=3                    1    2
i=4                         1

dp[1][3]（"bcb"）：
  s[1] 自己一筆：1 + dp[2][3] = 1 + 2 = 3
  k=3（s[3] = b）：dp[2][2] + dp[3][3] = 1 + 1 = 2 ← 先印 bbb，再在中間印 c
dp[0][4]（"abcba"）：
  s[0] 自己一筆：1 + dp[1][4] = 1 + 3 = 4
  k=4（s[4] = a）：dp[1][3] + dp[4][4] = 2 + 1 = 3 ← 最佳

實際的印法（3 筆）：
第 1 筆  a a a a a      印 s[4] 的那一筆向左延伸到 0
第 2 筆    b b b        dp[1][3] 的第一筆
第 3 筆      c          dp[1][3] 的第二筆
結果     a b c b a
```

`dp[0][4]` 選擇 k = 4，意思是「最左邊的 a 和最右邊的 a 用同一筆印」，中間的 `"bcb"` 是印在它上面的獨立子問題，而 `"bcb"` 又用同樣的方式讓兩個 b 共用一筆。

### 解法

```python
import random
from collections import deque


def strange_printer(s: str) -> int:
    t = []
    for c in s:                                  # 連續相同字元壓成一個
        if not t or t[-1] != c:
            t.append(c)
    s, n = "".join(t), len(t)
    dp = [[0] * (n + 1) for _ in range(n + 1)]   # 多一列一行，讓空區間讀到 0
    for i in range(n - 1, -1, -1):
        dp[i][i] = 1
        for j in range(i + 1, n):
            best = 1 + dp[i + 1][j]              # s[i] 自己一筆
            for k in range(i + 1, j + 1):
                if s[k] == s[i]:                 # 印 s[k] 的那一筆向左延伸到 i
                    best = min(best, (dp[i + 1][k - 1] if k - 1 >= i + 1 else 0) + dp[k][j])
            dp[i][j] = best
    return dp[0][n - 1] if n else 0


def brute(s):
    """BFS 搜尋紙上的狀態，'?' 代表空白。"""
    n, chars = len(s), set(s)
    start = "?" * n
    dist, q = {start: 0}, deque([start])
    while q:
        cur = q.popleft()
        if cur == s:
            return dist[cur]
        for i in range(n):
            for j in range(i, n):
                for c in chars:
                    nxt = cur[:i] + c * (j - i + 1) + cur[j + 1:]
                    if nxt not in dist:
                        dist[nxt] = dist[cur] + 1
                        q.append(nxt)


assert strange_printer("aaabbb") == 2
assert strange_printer("aba") == 2
assert strange_printer("abcabc") == 5
assert strange_printer("a") == 1
assert strange_printer("abab") == 3
assert strange_printer("abcba") == 3
for _ in range(200):
    t = "".join(random.choice("abc") for _ in range(random.randint(1, 6)))
    assert strange_printer(t) == brute(t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n³)：O(n²) 個區間，每個枚舉 O(n) 個 k，n = 100 時最多約 n³ / 6 ≈ 1.7 × 10⁵ 次。空間 O(n²)。邊界情況：壓縮後長度可能大幅縮短，例如 `"aaaa"` 變成 `"a"`，答案 1；`dp[i+1][k-1]` 在 k = i + 1 時是空區間，必須是 0（壓縮後 s[i+1] 一定不等於 s[i]，所以這種情況其實不會發生，但程式仍然處理）；所有字元都不同時答案是 n，因為沒有任何 k 可以共用。

### Follow-up

> [!question]- F1. 為什麼可以先把連續相同的字元壓縮成一個？
> 連續相同的一段 `"aaa"`，在任何最佳解中都可以假設它們由同一筆印出：若某一筆印到其中一部分，把它延伸到整段同色區塊，不會破壞其他位置的最終結果（延伸的位置最終也是同一個字元，而之後蓋上去的筆照樣蓋）。所以壓縮不改變答案，卻能讓 n 變小、去掉 `dp[i+1][k-1]` 中 k = i + 1 這種退化情況。這也是面試時很好的開場觀察，能顯示你在找問題的結構。

> [!question]- F2. 如果不允許覆蓋（每個位置只能被印一次）呢？
> 每一筆印出的都是一段連續的同字元區間，而且不能重疊，所以每一筆恰好對應 s 中一個「極大同字元區段」或其中一部分。最少筆數就是極大區段的個數，也就是壓縮後的長度，O(n) 掃一遍即可。這個對比說明了本題的 DP 完全來自覆蓋：覆蓋讓「外層先印、內層再修」成為可能，於是同字元的兩個位置可以共用一筆。

> [!question]- F3. 如果要輸出實際的印刷步驟呢？
> 記錄每個 `dp[i][j]` 選擇的是「自己一筆」還是哪個 k。遞迴展開：選 k 時，把 `[i, k]` 加到 s[i] 那一筆的範圍裡，再遞迴處理中段 `[i+1, k-1]`（這些筆要排在這一筆之後）與右段 `[k, j]`（右段中 s[k] 那一筆的範圍要合併 i 進來）。實作上可以讓遞迴函式回傳「這個區間最底層那一筆的左端點」，讓上層把它往左延伸。步驟數就是 dp 值，展開 O(n²)。輸出順序要確保外層的筆先印、內層的筆後印。

> [!question]- F4. 如果是二維版本：每種顏色只能印一次，而且每次印一個矩形（1591. Strange Printer II），問給定的格子顏色能不能印出來？
> 每種顏色 c 印的矩形至少要是它所有出現位置的外接矩形。若外接矩形內出現別的顏色 d，代表 d 必須在 c 之後印（d 蓋在 c 上面），於是得到一張「c → d」的依賴圖。能印出來若且唯若這張圖沒有環，用第 16 章的 topological sort 檢查即可。顏色最多 60 種，建圖 O(C · m · n)，判環 O(C²)。這題和一維版本的共同精神是「先印底層、後印上層」，但二維版本變成可行性判定而不是最佳化。

### 心得

關鍵突破是「s[i] 那一筆可以向右延伸到某個同色的 s[k]，讓兩個位置共用一筆」，覆蓋讓「先印底層、再修中間」成為可能，於是轉移變成在所有同色位置中選一個合併。它和核心題 4、5 一樣從區間的左端點出發，但轉移不是只看兩端，而是枚舉區間內所有和左端同色的位置；難題 3（546）把同樣的「與後面同色的位置合併」再推進一步，連合併的個數都要記進狀態。面試時先說壓縮連續重複字元，再用 `"aba"` 說明為什麼貪婪分段不對，接著寫出兩種選擇（自己一筆、或與某個 s[k] 共用），最後用小例子手算表格。

## 難題 3｜546. Remove Boxes｜Hard

### 題目

有一列盒子，每個盒子有一個顏色（正整數）`boxes[i]`。每一回合你可以選一段**連續且同色**的盒子（長度 k ≥ 1），把它們移除並得到 k × k 分，移除後左右兩邊的盒子會接在一起。重複直到所有盒子都被移除，回傳最高總分。限制：`1 <= len(boxes) <= 100`，`1 <= boxes[i] <= 100`。

- 範例 1：`boxes = [1, 3, 2, 2, 2, 3, 4, 3, 1]`，回傳 `23`。移除 `2 2 2`（9 分）→ 剩 `[1, 3, 3, 4, 3, 1]`，移除 `4`（1 分）→ `[1, 3, 3, 3, 1]`，移除 `3 3 3`（9 分）→ `[1, 1]`，移除（4 分），共 23。
- 範例 2：`boxes = [1, 1, 1]`，回傳 `9`。
- 範例 3（邊界）：`boxes = [1]`，回傳 `1`。
- 範例 4：`boxes = [2, 1, 2]`，回傳 `5`：先移除 1（1 分），兩個 2 接起來一次移除（4 分）。

### 提示

> [!tip]- 提示 1
> 試試 `dp[i][j]` = 移除 `boxes[i..j]` 的最高分。用 `[2, 1, 2]` 檢查：子區間 `[1, 2]` 的最佳是 2 分，但在整體中，右邊那個 2 其實想等左邊的 2 一起移除。只看區間本身，資訊夠嗎？

> [!tip]- 提示 2
> 區間的分數取決於「區間外有幾個同色盒子會跟它接在一起」。加一個維度：`dp[i][j][k]` = 區間 `boxes[i..j]`，並且 boxes[i] 的左邊還黏著 k 個與 boxes[i] 同色的盒子（它們原本在更左邊，中間的東西已經被清掉）時的最高分。

> [!tip]- 提示 3
> 對 boxes[i] 和它左邊黏著的 k 個盒子只有兩種處理：現在就一起移除，得 `(k+1)² + dp[i+1][j][0]`；或者先清掉 `boxes[i+1..m-1]`，讓它們和後面某個同色的 boxes[m] 接起來：`dp[i+1][m-1][0] + dp[m][j][k+1]`。

### 詳解

**為什麼直覺做法行不通**。貪婪「每次移除最長的同色段」會失敗：`[1, 2, 1, 2, 1]` 中每一段長度都是 1，貪婪無從分辨，若先移除某個 1，三個 1 就再也無法聚在一起；最佳是先移除兩個 2（各 1 分），讓三個 1 接起來一次拿 9 分，共 11 分。普通的區間 DP `dp[i][j]` 也不夠，因為 k² 是**超加性**的：兩段同色的盒子分開移除得 a² + b²，接起來移除得 (a + b)²，後者更多。區間 `[i, j]` 的最佳策略，取決於區間外有沒有同色盒子等著跟它合併，這個資訊不在 (i, j) 裡，所以子問題不獨立。

**突破點：把外部影響變成狀態**。觀察到外部影響只有一種形式：某些與 boxes[i] 同色的盒子，在它們之間的盒子被清掉後，接到了 boxes[i] 的左邊。所以加一個參數 k，`dp[i][j][k]` = 區間 `boxes[i..j]` 加上左邊黏著的 k 個 boxes[i] 色盒子，能得到的最高分。對最左邊這一團（boxes[i] 與它黏著的 k 個）只有兩種命運：

1. **現在移除**：得 `(k + 1)²`，剩下 `boxes[i+1..j]`，左邊不再黏任何東西：`(k+1)² + dp[i+1][j][0]`。
2. **等後面的同色盒子**：選一個 m（i < m ≤ j，`boxes[m] == boxes[i]`），先把中間的 `boxes[i+1..m-1]` 完全清掉（它們不會和兩端同色盒子互動，得 `dp[i+1][m-1][0]`），之後這一團 k + 1 個盒子就黏到 boxes[m] 的左邊：`dp[m][j][k+1]`。

兩種情況取最大值。最左一團的最終命運，一定是「在某個時刻和某些同色盒子一起被移除」；它第一個合併的對象如果是 m，就是情況 2，否則是情況 1，所以這個分解窮舉了所有策略。實作上還有一個重要的剪枝：如果 boxes[i+1] 和 boxes[i] 同色，直接把 i 往右推、k 加一，因為相鄰同色的盒子一起移除永遠不會更差。

```text
boxes = [1, 3, 2, 2, 2, 3, 4, 3, 1]
index:   0  1  2  3  4  5  6  7  8
f(i, j, k) = boxes[i..j] 且左邊黏著 k 個 boxes[i] 色盒子

f(0, 8, 0)  [1 3 2 2 2 3 4 3 1]
├─ 現在移除 1：1 + f(1, 8, 0)
└─ 等 m=8 的 1：f(1, 7, 0) + f(8, 8, 1) ← 最佳
   ├─ f(8, 8, 1) = (1+1)² = 4                         兩個 1 一起移除
   └─ f(1, 7, 0)  [3 2 2 2 3 4 3]
      ├─ 等 m=5 的 3：f(2, 4, 0) + f(5, 7, 1) ← 最佳
      │  ├─ f(2, 4, 0) [2 2 2]：剪枝成 i=4, k=2 → 3² = 9
      │  └─ f(5, 7, 1) [3 4 3]，左邊黏 1 個 3
      │     └─ 等 m=7 的 3：f(6, 6, 0) + f(7, 7, 2) = 1 + 3² = 10
      │     小計 9 + 10 = 19
      └─ （其他選擇都較差）
   小計 19 + 4 = 23
```

這棵樹恰好對應範例的移除順序：最深處先移除 `2 2 2` 和 `4`，讓三個 3 接起來，最後兩個 1 接起來。狀態 `f(5, 7, 1)` 的意義是「`[3, 4, 3]` 而且最左的 3 左邊還黏著一個 3」，這個 1 就是普通區間 DP 表達不出來的資訊。

### 解法

```python
import random
import sys
from functools import cache


def remove_boxes(boxes: list[int]) -> int:
    sys.setrecursionlimit(10000)

    @cache
    def f(i: int, j: int, k: int) -> int:
        if i > j:
            return 0
        while i < j and boxes[i + 1] == boxes[i]:   # 相鄰同色：一起併入左邊那團
            i += 1
            k += 1
        best = (k + 1) ** 2 + f(i + 1, j, 0)          # 現在移除最左一團
        for m in range(i + 1, j + 1):
            if boxes[m] == boxes[i]:                  # 先清掉中間，再和 boxes[m] 接起來
                best = max(best, f(i + 1, m - 1, 0) + f(m, j, k + 1))
        return best

    return f(0, len(boxes) - 1, 0)


def brute(boxes):
    @cache
    def go(t):
        if not t:
            return 0
        best, i = 0, 0
        while i < len(t):
            j = i
            while j + 1 < len(t) and t[j + 1] == t[i]:
                j += 1
            best = max(best, (j - i + 1) ** 2 + go(t[:i] + t[j + 1:]))
            i = j + 1
        return best
    return go(tuple(boxes))


assert remove_boxes([1, 3, 2, 2, 2, 3, 4, 3, 1]) == 23
assert remove_boxes([1, 1, 1]) == 9
assert remove_boxes([1]) == 1
assert remove_boxes([2, 1, 2]) == 5
assert remove_boxes([1, 2, 1, 2, 1]) == 11
for _ in range(300):
    arr = [random.randint(1, 3) for _ in range(random.randint(1, 9))]
    assert remove_boxes(arr) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

狀態數 O(n³)（i、j、k 各至多 n），每個狀態枚舉 O(n) 個 m，時間 O(n⁴)，n = 100 時理論上界是 10⁸，但實際上只有同色的 m 會被枚舉、k 也只會取到「左邊同色盒子的個數」，可達狀態遠少於上界，加上剪枝後可以通過。空間 O(n³)。邊界情況：只有一個盒子時答案 1；全部同色時剪枝讓 k 一路加到 n − 1，答案 n²；遞迴深度最多約 2n，n = 100 時 Python 預設上限也夠，但保險起見調高。剪枝中 `while` 移動 i 時要同步加 k，否則會少算黏著的盒子。

### Follow-up

> [!question]- F1. 如果分數不是 k²，而是任意函數 g(k) 呢？
> DP 的分解完全不依賴 g 的形式：最左一團「現在移除」得 `g(k+1)`，「等後面的同色盒子」的轉移不變，所以只要把 `(k+1)**2` 換成 `g(k+1)` 即可，正確性與複雜度都不變。差別在於剪枝：「相鄰同色一起移除永遠不會更差」需要 g 是超加性（`g(a+b) >= g(a) + g(b)`），k² 滿足；若 g 是線性的（例如 g(k) = k），任何順序的總分都等於盒子總數，DP 就沒有意義；若 g 是次加性的，分開移除反而更好，相鄰同色的剪枝就必須拿掉。

> [!question]- F2. 為什麼把黏著的盒子放在「左邊」？放右邊可以嗎？
> 可以，對稱地定義 `dp[i][j][k]` = 區間右邊黏著 k 個與 boxes[j] 同色的盒子，轉移改成看最右一團：現在移除，或找 i ≤ m < j 中與 boxes[j] 同色的 m 先清掉中間。兩種寫法等價。重點是「只需要記錄一端」：因為我們永遠先處理最左（或最右）一團，另一端的外部影響會在更外層的遞迴中處理，不需要同時記錄兩端的黏著數，狀態維持在 O(n³)。

> [!question]- F3. 能不能寫成 bottom-up？要注意什麼？
> 可以用三維陣列 `dp[i][j][k]`，外層依區間長度遞增，內層對每個 (i, j) 計算所有 k（0 到 i 左邊同色盒子的個數）。轉移時 `dp[i+1][m-1][0]` 和 `dp[m][j][k+1]` 都是更短的區間，所以長度遞增的順序成立。缺點是會計算大量不可達的狀態（k 太大的組合），n = 100 時有 10⁶ 個格子、每格 O(n) 轉移，Python 會比記憶化慢很多；top-down 只計算真正會被用到的狀態，是這題比較好的選擇。

> [!question]- F4. 這題和 488. Zuma Game 有什麼關係？
> 兩題都是「移除連續同色段、兩邊會接起來」，所以都需要考慮「先清掉中間，讓兩端同色的部分接起來」這種策略。但 Zuma 的目標是用手上有限的球**插入**來觸發消除，三個以上才會消、而且會連鎖反應，規則讓區間 DP 的分解不再乾淨（插入的球從哪裡來、連鎖消除會跨區間）。實務上 Zuma 通常用 BFS 或記憶化搜尋整個盤面狀態，靠盤面很短（≤ 16）來控制複雜度。面試中提到這個對比，可以說明為什麼本題能用區間 DP：每次移除的效果只發生在被移除段的兩側，而且只有「接起來」這一種副作用。

### 心得

關鍵突破是發現 `dp[i][j]` 不足以描述子問題，因為區間外的同色盒子會改變區間內的最佳策略，所以加一個維度 k 記錄「左邊黏著幾個同色盒子」，把外部影響變成狀態的一部分。這是本章最難的一題，也是「區間 DP 加維度」的代表；難題 4（1000）的「這段會剩幾堆」是另一個加維度的例子，只是那裡的額外維度恰好可以由長度推出而省掉。面試時建議先用 `[2, 1, 2]` 說明二維狀態為什麼不夠，再定義三維狀態並解釋兩種選擇（現在移除、等後面的同色盒子），最後補上「相鄰同色直接併入」的剪枝與 top-down 實作的理由。

## 難題 4｜1000. Minimum Cost to Merge Stones｜Hard

### 題目

有 n 堆石頭排成一列，第 i 堆有 `stones[i]` 顆。每一次操作必須把**恰好 K 堆相鄰的**石頭合併成一堆，成本是這 K 堆的石頭總數。回傳把所有石頭合併成一堆的最小總成本；如果不可能，回傳 -1。限制：`1 <= n <= 30`，`2 <= K <= 30`，`1 <= stones[i] <= 100`。

- 範例 1：`stones = [3, 2, 4, 1]`、`K = 2`，回傳 `20`：合併 3、2（5）→ `[5, 4, 1]`，合併 4、1（5）→ `[5, 5]`，合併（10），共 20。
- 範例 2：`stones = [3, 2, 4, 1]`、`K = 3`，回傳 `-1`：合併一次剩 2 堆，無法再合併。
- 範例 3：`stones = [3, 5, 1, 2, 6]`、`K = 3`，回傳 `25`：合併 5、1、2（8）→ `[3, 8, 6]`，合併（17），共 25。
- 範例 4（邊界）：`stones = [5]`、任何 K，回傳 `0`，已經是一堆。

### 提示

> [!tip]- 提示 1
> 每次合併讓堆數減少 K − 1。從 n 堆變成 1 堆，需要 n − 1 是 K − 1 的倍數，否則回傳 -1。

> [!tip]- 提示 2
> 23.5 節的 K = 2 版本是 `dp[i][j] = min(dp[i][k] + dp[k+1][j]) + sum(i..j)`。K > 2 時，一段區間不一定能合併成一堆，所以要想清楚 `dp[i][j]` 代表「合併成幾堆」。

> [!tip]- 提示 3
> 令 `dp[i][j]` = 把 `stones[i..j]` 盡量合併（合併到剩 `(j − i) % (K − 1) + 1` 堆）的最小成本。最終結果最左邊那一堆來自某個前綴 `[i..mid]` 合併成的一堆，所以 mid 每次跳 K − 1：`dp[i][j] = min(dp[i][mid] + dp[mid+1][j])`。當 `(j − i) % (K − 1) == 0` 時，這一段最後還能再合併一次成一堆，加上 `sum(i..j)`。

### 詳解

**為什麼直覺做法行不通**。貪婪「每次合併總和最小的 K 堆相鄰石頭」不是最佳的：選擇哪 K 堆會影響之後誰和誰相鄰，局部最小不保證全域最小。例如 K = 2、`[3, 2, 2, 3]`：貪婪先合併和最小的 2 + 2 = 4，得到 `[3, 4, 3]`，再合併 3 + 4 = 7、最後 10，共 21；但先合併 3 + 2（5）、再合併 2 + 3（5）、最後 10，只要 20。貪婪的那一步讓中間變大，之後兩邊都得和它合併。直接把 23.5 節的模板搬過來也不行：K = 3 時，`[i..k]` 和 `[k+1..j]` 未必各自能合併成一堆，「兩堆合併」的轉移本身也不符合「恰好 K 堆」的規則。

**突破點：記錄「這段會剩幾堆」，而且它是確定的**。每次合併讓堆數減少 K − 1，所以長度為 L 的區間合併到不能再合併時，一定剩下 `(L − 1) % (K − 1) + 1` 堆，這個數字只由 L 決定。於是可以定義 `dp[i][j]` = 把 `stones[i..j]` 合併到剩這麼多堆的最小成本。看最終結果中最左邊的那一堆：它是某個前綴 `[i..mid]` 合併成的**一堆**，這要求 `(mid − i) % (K − 1) == 0`，所以 mid 只要枚舉 `i, i + (K−1), i + 2(K−1), …`；剩下的 `[mid+1..j]` 獨立地合併到它自己的最少堆數。

`dp[i][j] = min over mid (dp[i][mid] + dp[mid+1][j])`；若 `(j − i) % (K − 1) == 0`，這段剛好剩 K 堆（左邊一堆加右邊 K − 1 堆），可以再做一次最後的合併，`dp[i][j] += sum(i..j)`。長度小於 K 的區間 dp 為 0（什麼都不能做）。答案是 `dp[0][n-1]`，前提是 `(n − 1) % (K − 1) == 0`。

**正確性**。最左一堆的來源窮舉了所有可能的切分；左右兩部分在最終合併前互不干擾（合併只發生在相鄰的堆之間，而最左一堆是由前綴完整合併而成，右邊的合併不會碰到它），所以兩部分各自取最小值即可。最後一次合併的成本永遠是整段的總和，與中間怎麼合併無關，所以可以在確定能合成一堆時直接加上。

```text
stones = [3, 5, 1, 2, 6]，K = 3，(5 − 1) % 2 == 0 → 可行
prefix sum：sum(i..j) = P[j+1] − P[i]

       j=0  j=1  j=2  j=3  j=4      每格旁邊是「這段最後剩幾堆」
i=0     0    0    9    8   25       長度 1→1 堆、2→2 堆、3→1 堆、4→2 堆、5→1 堆
i=1          0    0    8    8
i=2               0    0    9
i=3                    0    0
i=4                         0

長度 3（可合成一堆，要加總和）：
  dp[0][2] = dp[0][0] + dp[1][2] + (3+5+1) = 0 + 0 + 9 = 9
  dp[1][3] = 0 + 0 + (5+1+2) = 8，dp[2][4] = 0 + 0 + (1+2+6) = 9
長度 4（剩兩堆，不加總和），mid ∈ {i, i+2}：
  dp[0][3] = min(dp[0][0] + dp[1][3], dp[0][2] + dp[3][3]) = min(0 + 8, 9 + 0) = 8
             → [3] [5 1 2 合成 8]
  dp[1][4] = min(dp[1][1] + dp[2][4], dp[1][3] + dp[4][4]) = min(9, 8) = 8
長度 5（可合成一堆）：
  dp[0][4] = min(dp[0][0] + dp[1][4], dp[0][2] + dp[3][4]) + 17
           = min(0 + 8, 9 + 0) + 17 = 25
```

`dp[0][4]` 的最佳選擇是 mid = 0：最左一堆就是原本的 3，右邊 `[5, 1, 2, 6]` 合併到剩兩堆（先合 5、1、2 得 8），三堆 `[3, 8, 6]` 再一次合併。另一個選擇 mid = 2 代表先合 3、5、1，成本 9 比 8 高。

### 解法

```python
import random
from functools import cache


def merge_stones(stones: list[int], K: int) -> int:
    n = len(stones)
    if (n - 1) % (K - 1):
        return -1
    prefix = [0]
    for x in stones:
        prefix.append(prefix[-1] + x)
    dp = [[0] * n for _ in range(n)]
    for length in range(K, n + 1):                   # 長度 < K 的區間成本為 0
        for i in range(n - length + 1):
            j = i + length - 1
            dp[i][j] = min(dp[i][mid] + dp[mid + 1][j] for mid in range(i, j, K - 1))
            if (length - 1) % (K - 1) == 0:          # 剛好剩 K 堆，再合併一次
                dp[i][j] += prefix[j + 1] - prefix[i]
    return dp[0][n - 1]


def brute(stones, K):
    @cache
    def go(t):
        if len(t) == 1:
            return 0
        if len(t) < K:
            return float("inf")
        return min(sum(t[i:i + K]) + go(t[:i] + (sum(t[i:i + K]),) + t[i + K:])
                   for i in range(len(t) - K + 1))
    r = go(tuple(stones))
    return -1 if r == float("inf") else r


assert merge_stones([3, 2, 4, 1], 2) == 20
assert merge_stones([3, 2, 4, 1], 3) == -1
assert merge_stones([3, 5, 1, 2, 6], 3) == 25
assert merge_stones([5], 4) == 0
assert merge_stones([1, 2, 3], 3) == 6
for _ in range(300):
    kk = random.randint(2, 4)
    arr = [random.randint(1, 9) for _ in range(random.randint(1, 7))]
    assert merge_stones(arr, kk) == brute(arr, kk)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n³ / K)：O(n²) 個區間，每個枚舉 O(n / (K − 1)) 個 mid。n = 30 時非常快。空間 O(n²)。邊界情況：n = 1 時 `(0) % (K − 1) == 0`，迴圈不執行，回傳 0；`(n − 1) % (K − 1) != 0` 時一開始就回傳 -1；K > n 且 n > 1 時一定不可行，同一個條件就會擋下；mid 的範圍 `range(i, j, K − 1)` 保證 `[i..mid]` 的長度 ≡ 1 (mod K − 1)，而且 mid < j，右段非空。K = 2 時每個 mid 都合法、每段都能合成一堆，退化成 23.5 節的模板。

### Follow-up

> [!question]- F1. 如果不要求相鄰，任意 K 堆都可以合併呢？
> 這就是 Huffman coding：K = 2 時每次取最小的兩堆合併，用 min-heap 做，O(n log n)，這是 1167. Minimum Cost to Connect Sticks，heap 的用法見第 14 章。一般的 K 用 K-ary Huffman：若 `(n − 1) % (K − 1) != 0`，補上若干個 0 讓它整除，然後每次取最小的 K 堆。相鄰限制讓 Huffman 的交換論證失效（最小的兩堆可能不相鄰），所以原題必須用區間 DP。這個對比很值得在面試中主動提出。

> [!question]- F2. 有沒有比較直觀的三維狀態寫法？
> 有：`f[i][j][p]` = 把 `stones[i..j]` 合併成恰好 p 堆的最小成本。轉移是 `f[i][j][p] = min over mid (f[i][mid][1] + f[mid+1][j][p-1])`（最左一堆來自前綴），以及 `f[i][j][1] = f[i][j][K] + sum(i..j)`。不可能的狀態設為無限大。時間 O(n³ · K)，比二維版本慢一個 K 倍，但每個狀態的意義非常清楚，面試時先寫三維版本、再說明「堆數其實由長度決定，所以 p 這一維可以拿掉」，是很好的講解順序。

> [!question]- F3. 如果石頭排成一個環（K = 2）呢？
> 環上的最後一次合併一定把環切成兩段，等價於「環上有某一條相鄰關係從頭到尾都沒被用到」，把環從那裡剪開就是一條鏈。做法是把陣列複製一份接在後面（長度 2n），在上面跑同樣的區間 DP，答案是所有長度 n 的區間 `dp[i][i+n-1]` 的最小值。時間 O((2n)³) = O(n³)，只是常數變成 8 倍。這是區間 DP 處理環狀結構的標準技巧，戳氣球的環狀版本也可以用同樣的想法。

> [!question]- F4. 如果 K = 2 而 n 高達 5000 呢？
> O(n³) 太慢。K = 2 的轉移 `dp[i][j] = min(dp[i][k] + dp[k+1][j]) + w(i, j)`，其中 `w(i, j)` 是區間和，滿足四邊形不等式（quadrangle inequality）與區間包含單調性，所以可以用 Knuth 優化：最佳分割點滿足 `opt[i][j-1] <= opt[i][j] <= opt[i+1][j]`，只枚舉這個範圍，總時間降為 O(n²)。難題 5 的 F2 附了 Knuth 優化的程式。更進一步還有 Garsia–Wachs 演算法可以做到 O(n log n)，但面試中能說出 Knuth 優化與它成立的條件就很足夠了。

> [!question]- F5. 為什麼可行的條件恰好是 (n − 1) % (K − 1) == 0？
> 必要性：每次合併把 K 堆變成 1 堆，堆數減少 K − 1，從 n 減到 1 共減少 n − 1，所以 n − 1 必須是 K − 1 的倍數。充分性：只要堆數 ≥ K，就一定能找到 K 堆相鄰的石頭合併（任取最左邊的 K 堆），每次減少 K − 1，條件成立時最後恰好剩 1 堆。這也是 DP 中「長度 L 的區間最後剩 `(L − 1) % (K − 1) + 1` 堆」的由來：一直合併直到堆數小於 K。

### 心得

關鍵突破是「長度為 L 的區間合併到不能再合併時，剩下的堆數由 L 唯一決定」，於是 `dp[i][j]` 有明確的意義，而且最左一堆一定來自長度 ≡ 1 (mod K − 1) 的前綴，讓分割點每次跳 K − 1。它是 23.5 節 K = 2 模板的推廣，也和難題 5（1547）互為鏡像：切棍子倒過來看就是 K = 2 的合併。面試時先講可行條件 (n − 1) % (K − 1) == 0，再提出三維狀態 `f[i][j][p]` 作為直觀版本，最後說明 p 可以由長度推出而省掉，這個「先寫清楚、再壓維度」的順序最容易讓面試官跟上。

## 難題 5｜1547. Minimum Cost to Cut a Stick｜Hard

### 題目

有一根長度為 n 的木棍，刻度從 0 到 n。給一個陣列 `cuts`，表示必須在這些刻度位置各切一刀，切的**順序可以自選**。每一刀的成本是當下被切的那一段木棍的長度，切完後木棍變成兩段。回傳切完所有位置的最小總成本。限制：`2 <= n <= 10⁶`，`1 <= len(cuts) <= min(n − 1, 100)`，`1 <= cuts[i] <= n − 1`，`cuts` 中的值互不相同。

- 範例 1：`n = 7`、`cuts = [1, 3, 4, 5]`，回傳 `16`。依序切 3（成本 7）、5（成本 4，切 [3, 7]）、1（成本 3，切 [0, 3]）、4（成本 2，切 [3, 5]），共 16。若照原順序 1、3、4、5 切，成本是 7 + 6 + 4 + 3 = 20。
- 範例 2：`n = 9`、`cuts = [5, 6, 1, 4, 2]`，回傳 `22`。
- 範例 3（邊界）：`n = 2`、`cuts = [1]`，回傳 `2`：只有一刀，成本就是整根長度。
- 範例 4：`n = 10`、`cuts = [5]`，回傳 `10`。

### 提示

> [!tip]- 提示 1
> n 高達 10⁶，但切點最多 100 個。狀態應該定義在「切點」上，而不是長度上。把切點排序，並在兩端補上 0 和 n。

> [!tip]- 提示 2
> 令 `dp[i][j]` = 把刻度 `p[i]` 到 `p[j]` 這一段，在它內部所有切點都切完的最小成本（p 是排序並補上端點後的切點）。在這一段上切的第一刀成本是多少？和切在哪裡有關嗎？

> [!tip]- 提示 3
> 第一刀的成本永遠是 `p[j] − p[i]`，與切在哪裡無關；切在 p[k] 之後，左右兩段完全獨立。`dp[i][j] = p[j] − p[i] + min over i < k < j (dp[i][k] + dp[k][j])`，依區間寬度由小到大計算。

### 詳解

**為什麼直覺做法行不通**。枚舉所有切的順序是 m!，m = 100 不可能。貪婪「每次切在最接近中間的位置」聽起來合理（讓兩段長度平均），但它不是最佳的，因為成本取決於切點的分佈而不只是長度。例如 n = 8、cuts = `[3, 4, 5]`：先切最接近中間的 4（成本 8），兩邊各剩一刀、各 4，共 16；但先切 5（成本 8），再切 3（成本 5）、4（成本 2），共 15。以 n 當作狀態維度也不行，n 高達 10⁶，O(n²) 的區間就放不下。

**突破點：在切點上做區間 DP，枚舉第一刀**。把 cuts 排序，令 `p = [0] + sorted(cuts) + [n]`，共 m + 2 個點。任何時刻的每一段木棍，它的兩端一定是 p 中的某兩個點，所以狀態只需要 O(m²) 個。考慮區間 `[p[i], p[j]]`：在它上面切的第一刀，不論切在哪個內部切點 p[k]，成本都是整段長度 `p[j] − p[i]`；切完後左段 `[p[i], p[k]]` 和右段 `[p[k], p[j]]` 互不影響。所以 `dp[i][j] = p[j] − p[i] + min over k (dp[i][k] + dp[k][j])`，相鄰兩點之間沒有切點，`dp[i][i+1] = 0`。

這題和戳氣球（難題 1）的方向相反：戳氣球必須枚舉**最後**一顆，因為第一顆戳完會讓兩邊接起來；切棍子枚舉**第一刀**就可以，因為切開之後兩段本來就是分開的。判斷該用「第一步」還是「最後一步」，就看哪一個會讓剩下的部分變成獨立的子問題。

**正確性**。區間內的切法一定有一個第一刀，枚舉所有可能的第一刀就窮舉了所有策略；第一刀之後兩段獨立，各自取最小值即可。所有被依賴的區間寬度都更小，依寬度遞增計算。

```text
n = 7，cuts = [1, 3, 4, 5] → p = [0, 1, 3, 4, 5, 7]
index:   0  1  2  3  4  5
p:       0  1  3  4  5  7

dp[i][j] = 切完 p[i]..p[j] 內部所有切點的最小成本
       j=1  j=2  j=3  j=4  j=5
i=0     0    3    7   10   16
i=1          0    3    6   12
i=2               0    2    6
i=3                    0    3
i=4                         0

寬度 2（內部只有一個切點）：dp[i][i+2] = p[i+2] − p[i]
  dp[0][2] = 3，dp[1][3] = 3，dp[2][4] = 2，dp[3][5] = 3
寬度 3：dp[0][3] = 4 + min(dp[0][1] + dp[1][3], dp[0][2] + dp[2][3]) = 4 + min(3, 3) = 7
寬度 5：dp[0][5] = 7 + min over k
  k=1（先切 1）：dp[0][1] + dp[1][5] =  0 + 12 = 12
  k=2（先切 3）：dp[0][2] + dp[2][5] =  3 +  6 =  9 ← 最佳
  k=3（先切 4）：dp[0][3] + dp[3][5] =  7 +  3 = 10
  k=4（先切 5）：dp[0][4] + dp[4][5] = 10 +  0 = 10
  dp[0][5] = 7 + 9 = 16
```

最佳的第一刀切在 3，左段 `[0, 3]` 只剩切點 1（成本 3），右段 `[3, 7]` 有切點 4、5，`dp[2][5] = 6` 代表先切 5（成本 4）再切 4（成本 2）。總和 7 + 3 + 6 = 16。

### 解法

```python
import random
from itertools import permutations
from bisect import bisect_left, insort


def min_cost(n: int, cuts: list[int]) -> int:
    p = [0] + sorted(cuts) + [n]
    m = len(p)
    dp = [[0] * m for _ in range(m)]
    for width in range(2, m):                    # 寬度 1 的區間內部沒有切點，成本 0
        for i in range(m - width):
            j = i + width
            dp[i][j] = p[j] - p[i] + min(dp[i][k] + dp[k][j] for k in range(i + 1, j))
    return dp[0][m - 1]


def brute(n, cuts):
    best = float("inf")
    for order in permutations(cuts):
        pts, total = [0, n], 0
        for c in order:
            idx = bisect_left(pts, c)
            total += pts[idx] - pts[idx - 1]     # 當下所在那一段的長度
            insort(pts, c)
        best = min(best, total)
    return best


assert min_cost(7, [1, 3, 4, 5]) == 16
assert min_cost(9, [5, 6, 1, 4, 2]) == 22
assert min_cost(2, [1]) == 2
assert min_cost(10, [5]) == 10
assert min_cost(10**6, [1, 999999]) == 10**6 + 999999
for _ in range(200):
    nn = random.randint(2, 30)
    cs = random.sample(range(1, nn), random.randint(1, min(nn - 1, 6)))
    assert min_cost(nn, cs) == brute(nn, cs)
print("all tests passed")
```

### 複雜度與邊界

時間 O(m³)，m 是切點數，m = 100 時約 1.7 × 10⁵ 次，與 n 無關；排序 O(m log m)。空間 O(m²)。邊界情況：只有一個切點時 dp 表只有一格寬度 2 的區間，答案 n；cuts 沒有排序是常態，一定要先排序；補上 0 和 n 兩個端點是讓「整根木棍」也能表示成一個區間；n 很大時成本總和可達 100 × 10⁶ = 10⁸，Python 沒問題，在 Java 中 int 仍然足夠，但若 n 到 10⁹ 就要用 long。

### Follow-up

> [!question]- F1. 這題和「合併石頭」有什麼關係？
> 把時間倒過來看：切完之後木棍變成 m + 1 段，長度分別是 `p[1] − p[0], p[2] − p[1], …`；倒過來就是把這些小段**兩兩相鄰合併**回整根，每次合併的成本是合併後那一段的長度。所以本題等價於難題 4 的 K = 2 版本（23.5 節的模板），石頭的重量就是各段的長度。用 `[1, 2, 1, 1, 2]` 跑 23.5 節的 `merge_adjacent_pairs` 會得到同樣的 16。能看出這個對應，代表你理解區間 DP 的「第一步」與「最後一步」是同一件事的兩個方向。

> [!question]- F2. 能不能比 O(m³) 更快？
> 可以用 Knuth 優化做到 O(m²)。成本函式 `w(i, j) = p[j] − p[i]` 滿足四邊形不等式（實際上是等式）與區間包含單調性，所以最佳的第一刀位置滿足 `opt[i][j-1] <= opt[i][j] <= opt[i+1][j]`。對每個 (i, j) 只枚舉這個範圍內的 k，攤銷後每條對角線的總枚舉量是 O(m)，總共 O(m²)。
> ```python
> def min_cost_knuth(n, cuts):
>     p = [0] + sorted(cuts) + [n]
>     m = len(p)
>     dp = [[0] * m for _ in range(m)]
>     opt = [[0] * m for _ in range(m)]
>     for i in range(m - 2):
>         dp[i][i + 2] = p[i + 2] - p[i]
>         opt[i][i + 2] = i + 1
>     for width in range(3, m):
>         for i in range(m - width):
>             j = i + width
>             best, arg = float("inf"), -1
>             for k in range(opt[i][j - 1], opt[i + 1][j] + 1):
>                 if dp[i][k] + dp[k][j] < best:
>                     best, arg = dp[i][k] + dp[k][j], k
>             dp[i][j] = best + p[j] - p[i]
>             opt[i][j] = arg
>     return dp[0][m - 1]
> ```

> [!question]- F3. 如果切的順序已經固定（必須照 cuts 的順序切），只要計算總成本呢？
> 沒有選擇就不需要 DP，問題變成「每一刀時，找出它所在那一段的左右端點」。正向模擬用排序容器（`bisect.insort`）找前驅與後繼，Python 的 list 插入是 O(m)，總共 O(m²)；用平衡樹可以做到 O(m log m)。更漂亮的是倒過來做：先把所有切點都切好（排序後就是 m + 1 段，用雙向鏈結串列串起來），再依相反順序「黏回去」，每黏一個點 c，它當下所在那段的長度就是鏈結串列中左右鄰居的距離，然後把 c 從串列中刪除，每步 O(1)，總共 O(m log m)（排序）。

> [!question]- F4. 如果要最大化總成本呢？
> 把 min 換成 max 即可，DP 的分解（枚舉第一刀、兩段獨立）不依賴目標的方向，時間仍是 O(m³)。不過 Knuth 優化的單調性證明是針對最小化與四邊形不等式的組合，最大化時不能直接套用，要嘛接受 O(m³)，要嘛另外證明對應的單調性。面試時這類追問的重點是說清楚「哪些部分只依賴子問題獨立（可以沿用），哪些部分依賴目標函數的性質（不能沿用）」。

> [!question]- F5. 如果要輸出最佳的切割順序呢？
> 計算時記錄 `choice[i][j]` = 讓 `dp[i][j]` 最小的 k。輸出時從 `(0, m−1)` 開始做前序遍歷：先輸出 `p[choice[i][j]]`（這一段的第一刀），再遞迴處理左段 `(i, k)` 與右段 `(k, j)`。左右兩段的切法可以任意交錯，因為它們互不影響，前序遍歷只是其中一種合法順序。回溯 O(m)，總時間仍由 DP 主導。

### 心得

關鍵突破有兩個：狀態定義在「切點」而不是「長度」上，讓 n = 10⁶ 的問題只剩 O(m²) 個狀態；以及第一刀的成本與切在哪裡無關，切開後兩段天然獨立，所以枚舉第一刀就夠了。它和難題 1（312）形成最好的對照：戳氣球必須枚舉最後一步，切棍子枚舉第一步即可，判斷的依據都是「哪一種選法讓剩下的部分變成獨立子問題」；倒過來看，它又等於難題 4 的 K = 2 合併。面試時先指出 n 很大但切點很少，再寫出補端點、排序與 O(m³) 的 DP，若時間充足可以提 Knuth 優化把它降到 O(m²)。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 0/1 背包（可行性） | 每個數最多用一次，問能否湊出某個和 | `dp[s] = dp[s] or dp[s-x]`，內層由大到小；可用 bitset | 核心題 1（416）、1049、2035（meet in the middle） |
| 0/1 背包（計數） | 每個數最多用一次，問有幾種子集 | `dp[s] += dp[s-x]`，內層由大到小；先做代數轉換 | 核心題 2（494）、879 Profitable Schemes |
| 0/1 背包（最佳化、多維容量） | 每個物品有兩種以上的成本 | 每一維容量都由大到小 | 474 Ones and Zeroes、879 |
| 完全背包（組合計數） | 物品無限次、順序不算 | 外層物品、內層金額由小到大 | 核心題 3（518） |
| 完全背包（排列計數） | 物品無限次、順序算不同 | 外層金額、內層物品 | 377 Combination Sum IV、70 Climbing Stairs |
| 完全背包（最佳化） | 最少硬幣、最大價值 | 迴圈順序不影響 min／max | 322（第 21 章核心題 2）、279 Perfect Squares |
| 多重背包 | 每種物品有數量上限 | 二進位拆分或同餘類滑動視窗 | 核心題 3 F3、2585 Number of Ways to Earn Points |
| 區間 DP：兩端配對 | 回文、兩端字元的取捨 | `dp[i+1][j-1]`、`dp[i+1][j]`、`dp[i][j-1]`，O(n²) | 核心題 4（516）、核心題 5（1312）、730、1216 |
| 區間 DP：枚舉分割點 | 合併、切割、括號化，成本與整段有關 | `dp[i][k] + dp[k+1][j] + cost`，O(n³) | 難題 4（1000）、難題 5（1547）、矩陣連乘 |
| 區間 DP：枚舉最後一步 | 操作後鄰居改變 | 最後處理的元素以區間外側為鄰居，兩半獨立 | 難題 1（312）、1039 Minimum Score Triangulation |
| 區間 DP：同色合併 | 相同字元可以共用一次操作 | 讓 s[i] 和右邊某個同色 s[k] 合併 | 難題 2（664）、難題 3（546） |
| 區間 DP：加維度 | 區間外的東西會影響區間內的分數 | 多記「黏著幾個」「剩幾堆」等參數 | 難題 3（546）、難題 4（1000） |
| 環狀區間 | 首尾相接 | 複製陣列成 2n，取長度 n 的區間最佳值 | 難題 4 F3 |

**下限與上限**。背包最簡單的形式是 416：一個數字、一個方向、一張布林表，考的是「轉換成子集和」與「內層由大到小」。往上一層是 494 和 518，難點轉移到計數：要先做代數轉換（494 的 P = (S + target) / 2），或想清楚迴圈順序對應的是組合還是排列（518 與 377）。區間 DP 的入門是 516 與 1312，狀態和轉移都很直接，考的是計算順序。上限的題目難在三個地方：第一，**選對「最後一步」或「第一步」**，讓子問題獨立（312 必須枚舉最後一顆，1547 枚舉第一刀即可）；第二，**區間狀態不夠用**，必須找出區間外影響的最小描述並加成一個維度（546 的黏著數、1000 的剩餘堆數）；第三，**證明分解窮舉了所有策略**，例如 664 的「s[i] 那一筆延伸到哪個同色位置」需要一個「它可以是最底層」的論證。

**與其他 pattern 的關係**。背包是第 21 章一維 DP 的延伸：322 Coin Change 就是完全背包的最佳化版本，只是第 21 章用「金額」當狀態、沒有強調物品維度。區間 DP 與第 22 章的二維序列 DP 長得很像（都是二維表），差別在於第 22 章的 `dp[i][j]` 是「兩個字串的前綴」，依 i、j 遞增計算即可；區間 DP 的 `dp[i][j]` 是「同一個序列的一段」，必須依長度計算。516 同時屬於兩者：它既是區間 DP，也等於 s 與 reverse(s) 的 LCS（第 22 章核心題 3）。當背包的「容量」換成「已選集合」時，就變成第 24 章的 bitmask DP；當 n 小（≤ 40）但數值大時，背包要改用 meet in the middle 或第 19 章的 backtracking。

**容易混淆之處**。第一，「挑一些數湊出目標」不一定是背包：如果數值很大而 n 很小，要用 meet in the middle；如果要求的是「連續子陣列」，那是第 7 章的 prefix sum 或第 6 章的 sliding window。第二，「合併」類題目不一定是區間 DP：沒有相鄰限制時是 Huffman 貪婪（第 14 章 heap）。第三，區間 DP 的 `dp[i][j]` 有開區間（312、1547）和閉區間（516、1000）兩種定義，寫之前先決定，並用長度 1、2 的情況手算驗證，這是最常見的差一錯誤來源。第四，計數問題對重複極度敏感：518 和 377 只差迴圈順序，730 需要排容去重，寫完一定要用暴力解對拍。

## 本章重點整理

- 背包 DP 的本質是把「選了哪些」壓縮成「用掉多少資源」，狀態維度是數值，所以只有在總和或容量不大時可用（偽多項式）；數值大而 n 小時改用 meet in the middle。
- 0/1 背包與完全背包只差一個轉移來源：「拿」從上一列（0/1）或同一列（完全）轉移；壓成一維時，0/1 內層由大到小讀舊值，完全背包由小到大讀新值。
- 計數背包的迴圈順序決定數的是什麼：外層物品是組合（518），外層金額是排列（377）；最佳化問題（322）對順序不敏感，計數問題對重複極度敏感。
- `dp[0]` 的初始值要依題意：計數為 1（空集合）、可行性為 True、「不超過容量」的最佳化全部為 0、「恰好裝滿」的最佳化除 `dp[0]` 外為 −∞。
- 很多背包題要先做轉換：416 把「分兩組」變成「湊出 S / 2」，494 用 P − N = target、P + N = S 推出 P = (S + target) / 2，記得檢查奇偶與範圍。
- 區間 DP 的狀態是 `dp[i][j]` = 一段連續區間的答案，前提是區間內的最佳決策不受區間外影響；若有影響，就把影響變成額外的維度（546 的黏著數）。
- 區間 DP 一律依長度由小到大計算（或 i 由大到小、j 由小到大），確保依賴的較短區間都已算好；依 i 由小到大是最常見的隱形 bug。
- 兩種轉移：兩端配對（516、1312，O(n²)）與枚舉分割點（1000、1547，O(n³)）；n ≤ 500 時 O(n³) 是合理的訊號。
- 選對「最後一步」或「第一步」是區間 DP 的核心：312 枚舉最後戳的氣球，因為它的鄰居固定是區間外側；1547 枚舉第一刀，因為切開後兩段本來就獨立。
- 開區間加虛擬邊界（312 補 1、1547 補 0 與 n）可以消除邊界特判；寫之前先決定開或閉區間，並手算長度 1、2 的格子。
- 1000 的關鍵是「長度 L 的區間最後一定剩 (L − 1) % (K − 1) + 1 堆」，讓三維狀態壓回二維；可行性條件是 (n − 1) % (K − 1) == 0。
- 區間 DP 可以用 Knuth 優化把 O(n³) 降到 O(n²)，條件是成本函式滿足四邊形不等式（合併石頭、切棍子適用）；環狀問題則把陣列複製成兩倍長度。
