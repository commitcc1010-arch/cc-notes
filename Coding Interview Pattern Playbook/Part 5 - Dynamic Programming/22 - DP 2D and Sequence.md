---
chapter: 22
title: DP：二維與序列比對
part: 5
---

# 第 22 章　DP：二維與序列比對

> [!abstract] 本章地圖
> **一句話**：當子問題要用「兩個位置」才能描述（網格上的格子 (i, j)，或兩個序列的前綴 `s[:i]` 與 `t[:j]`），就開一張二維表 `dp[i][j]`，依照依賴方向一格一格填滿；右下角（或左上角）的格子是答案，沿著轉移往回走就是解。
>
> **辨識訊號**：
> - 網格上只能沿固定方向（右、下）移動，求路徑數、最小成本或最低需求
> - 兩個字串或序列的比對：共同子序列、編輯距離、能不能交錯組成
> - 「s 的子序列中有幾個等於 t」「最少幾次操作把 s 變成 t」
> - 帶 `.`、`?`、`*` 的 pattern matching，要整串匹配
> - 暴力解是在兩個序列上同時做「用或不用、配或不配」的分支，但每個分支的狀態只由兩個索引決定
> - 不只要數值，還要回傳實際的路徑、對齊方式或字串
>
> **核心題**：62、64、1143、72、97
>
> **難題**：10、44、115、174、1092

## 22.1 這個 Pattern 解決什麼問題

第 21 章已經建立了 DP（dynamic programming，動態規劃）的四個步驟：定義狀態、寫出轉移、設定 base case、決定計算順序。一維 DP 的狀態只需要一個索引，例如「前 i 間房子能搶到的最大金額」。本章處理的是**一個索引不夠**的情況：子問題天生由兩個量決定，例如「走到第 i 列第 j 行有幾種走法」，或「`s` 的前 i 個字元和 `t` 的前 j 個字元的最長共同子序列」。四個步驟完全不變，只是狀態變成表格，計算順序變成「表格怎麼填」。

先看一個小問題：`s = "abcde"`、`t = "ace"`，求最長的共同子序列（可以跳著取、但順序不能變）。暴力解列舉 `s` 的所有 2⁵ = 32 個子序列，逐一檢查是不是 `t` 的子序列，時間 O(2ᵐ · n)，m = 1000 時完全不可能。改用遞迴：只看兩個字串的最後一個字元，相同就一起配掉，不同就丟掉其中一邊的最後一個字元，取較好的那個。這個遞迴每次分成兩支，遞迴樹仍是指數級，但仔細看會發現**所有呼叫的參數都是一對前綴長度 (i, j)**，總共只有 (m + 1)(n + 1) 種。指數級的分支其實一直在重算同一批子問題，例如 (i − 1, j − 1) 可以從 (i − 1, j) 走到，也可以從 (i, j − 1) 走到。

```text
LCS(5, 3)  ← 比較 s[4]='e' 和 t[2]='e'，相同
└── LCS(4, 2)  ← 'd' ≠ 'c'
    ├── LCS(3, 2) ← 'c' = 'c'
    │   └── LCS(2, 1) ...
    └── LCS(4, 1) ← 'd' ≠ 'a'
        ├── LCS(3, 1) ← 'c' ≠ 'a'
        │   ├── LCS(2, 1) ...   ← 和上面那一支重複
        │   └── LCS(3, 0) = 0
        └── LCS(4, 0) = 0
LCS(2, 1) 已經被算了兩次；m、n 變大後重複次數呈指數成長，
但不同的 (i, j) 只有 6 × 4 = 24 個。
```

把每個 (i, j) 的答案存進表格、每格只算一次，時間就從指數降到 O(m · n)。網格路徑也是同一件事：從左上走到右下的路徑數是 C(m + n − 2, m − 1)，100 × 100 的網格大約有 10⁵⁸ 條，逐條列舉不可能；可是「走到 (i, j) 的路徑數」只依賴它上面和左邊兩格，一萬個格子各算一次就結束。本章的所有題目都在回答同一組問題：**表格的一格代表什麼？它依賴哪幾格？從哪個角落開始填？答案在哪一格？要不要回溯出解？能不能只留一兩列？**

## 22.2 辨識訊號

| 題目特徵 | 為什麼是二維 DP | 本章哪一題 |
|---|---|---|
| 網格上只能往右或往下，數路徑 | 走到 (i, j) 的方法只來自上面與左邊，沒有環 | 核心題 1（62） |
| 網格上只能往右或往下，求最小總和 | 到 (i, j) 的最佳路徑，前一段也必須是最佳 | 核心題 2（64） |
| 網格路徑上要求「途中隨時都不能低於某值」 | 正向有兩個互相牽制的量，反向只剩一個「之後還需要多少」 | 難題 4（174） |
| 兩個字串的共同子序列、只能刪除讓兩者相等 | 狀態是兩個前綴，最後一個字元配或不配 | 核心題 3（1143）、難題 5（1092） |
| 用插入、刪除、替換把 s 變成 t | 最後一個字元有三種處理方式，各自退回一個更小的前綴對 | 核心題 4（72） |
| 第三個字串是不是前兩個的交錯 | 用掉 s1 的 i 個、s2 的 j 個之後，s3 的位置固定是 i + j | 核心題 5（97） |
| pattern 含 `.`、`*`、`?`，問能否整串匹配 | 狀態是 (s 的前綴, p 的前綴)，`*` 產生「用零次」與「再多用一次」兩條轉移 | 難題 1（10）、難題 2（44） |
| 「s 的子序列中有幾個等於 t」 | 計數版的 LCS：s 的最後一個字元用或不用 | 難題 3（115） |
| 長度 ≤ 1000 的兩個序列，或 ≤ 200 × 200 的網格 | O(m · n) 是 10⁴ 到 10⁶，剛好可接受 | 本章全部 |

反向檢查：如果網格允許往四個方向走（會繞回去，狀態之間有環），就沒有固定的填表順序，DP 不適用，要改成 BFS 或 Dijkstra（第 15、18 章）；如果比的是**同一個字串的一段區間** `s[i..j]`（回文、戳氣球），雖然也是二維表，但依賴的是更短的區間，屬於第 23 章的區間 DP。

## 22.3 模板與原理：網格 DP 與雙序列 DP

二維 DP 有兩種基本形狀，記住兩份模板就能覆蓋本章大部分題目。

**模板 A：網格 DP**。`dp[i][j]` 代表「從起點走到格子 (i, j)」的答案。只能往右、往下時，(i, j) 只會從 (i − 1, j) 和 (i, j − 1) 走過來，所以一列一列、由左到右填，填到 (i, j) 時它依賴的兩格一定已經算好。第一列與第一行只有一個來源，要先處理（或用「表外是無限大／零」的哨兵統一處理）。

**模板 B：雙序列 DP**。`dp[i][j]` 代表「`s` 的前 i 個字元 `s[:i]` 與 `t` 的前 j 個字元 `t[:j]`」的答案。表格大小是 (m + 1) × (n + 1)，多出來的第 0 列、第 0 行代表**空前綴**，是 base case 的位置。轉移只看兩個前綴的最後一個字元 `s[i-1]` 與 `t[j-1]`（注意索引差 1），它們可以配對（退回 (i − 1, j − 1)），也可以只消耗其中一邊（退回 (i − 1, j) 或 (i, j − 1)）。這三個方向就是「對角、上、左」。

下面的 `align_cost` 是雙序列 DP 最一般的形式（序列比對，sequence alignment）：每一步可以把兩個字元對齊（成本 `sub(a, b)`），或讓某一邊的字元對到空白（成本 `gap`），求最小總成本。編輯距離與 LCS 都只是換了成本函式。

```python
import math


def grid_min_cost(cost: list[list[int]]) -> int:
    """模板 A：只能往右、往下，從左上走到右下的最小總成本（含起點與終點）。"""
    m, n = len(cost), len(cost[0])
    INF = math.inf
    dp = [[INF] * n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            if i == 0 and j == 0:
                dp[i][j] = cost[0][0]
                continue
            up = dp[i - 1][j] if i > 0 else INF
            left = dp[i][j - 1] if j > 0 else INF
            dp[i][j] = cost[i][j] + min(up, left)
    return dp[m - 1][n - 1]


def align_cost(s: str, t: str, gap: int, sub) -> int:
    """模板 B：dp[i][j] = s[:i] 與 t[:j] 對齊的最小成本。"""
    m, n = len(s), len(t)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        dp[i][0] = dp[i - 1][0] + gap          # s[:i] 全部對到空白
    for j in range(1, n + 1):
        dp[0][j] = dp[0][j - 1] + gap          # t[:j] 全部對到空白
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = min(
                dp[i - 1][j - 1] + sub(s[i - 1], t[j - 1]),   # 對角：最後兩個字元對齊
                dp[i - 1][j] + gap,                           # 上：s[i-1] 對空白
                dp[i][j - 1] + gap,                           # 左：t[j-1] 對空白
            )
    return dp[m][n]


def edit_distance(s: str, t: str) -> int:
    return align_cost(s, t, 1, lambda a, b: 0 if a == b else 1)


def indel_distance(s: str, t: str) -> int:
    # 不允許替換（不同字元對齊的成本設成無限大）：只能刪除與插入
    return align_cost(s, t, 1, lambda a, b: 0 if a == b else math.inf)


assert grid_min_cost([[1, 3, 1], [1, 5, 1], [4, 2, 1]]) == 7
assert grid_min_cost([[5]]) == 5
assert grid_min_cost([[1, 2, 3]]) == 6                 # 單列
assert edit_distance("horse", "ros") == 3
assert edit_distance("", "abc") == 3
assert edit_distance("same", "same") == 0
# 只能插入刪除時，距離 = m + n − 2 · LCS；"abcde" 與 "ace" 的 LCS 是 3
assert indel_distance("abcde", "ace") == 5 + 3 - 2 * 3
assert indel_distance("abc", "def") == 6
print("all tests passed")
```

**Invariant 與每一行為什麼這樣寫**：

- **填表順序保證依賴已就緒**。兩份模板都是外層 i 由小到大、內層 j 由小到大，也就是 row-major 順序。算 (i, j) 時，上面那一列已經完整算完，同一列左邊的格子也算完，所以 (i − 1, j)、(i, j − 1)、(i − 1, j − 1) 三格都已經是最終值。這是本章所有表格正確性的基礎：**依賴箭頭全部指向「已填過」的區域**。
- **(m + 1) × (n + 1) 而不是 m × n**。多一列一行給空前綴，base case 就有了自然的位置（`dp[0][0]` 是「兩個空字串」），轉移公式在第 1 列、第 1 行也不需要特判。代價是索引錯一位：`dp[i][j]` 看的是 `s[i-1]` 和 `t[j-1]`，這是本章最常見的 off-by-one 來源。
- **網格模板沒有多一列一行**，因為格子本身就是狀態，起點格要算進成本；改用 `INF` 當表外的值，`min(up, left)` 自然會忽略不存在的方向。也可以多開一列一行，把除了「起點的上方」之外的表外格設成 `INF`，寫法更短，但要想清楚哨兵的值。
- **最優子結構**。網格最小成本成立，是因為到 (i, j) 的最佳路徑去掉最後一格，必定是到它前一格的最佳路徑；若不是，換成更好的那條前段，整條路徑就更好，矛盾。雙序列比對成立的理由相同：最佳對齊去掉最後一欄，剩下的一定是較短前綴對的最佳對齊。
- **答案位置**。兩個模板的答案都在右下角 `dp[m-1][n-1]` 或 `dp[m][n]`；但有些題目的答案是整張表的最大值（例如最長共同子字串，見核心題 3 F2），有些題目要反向填、答案在左上角（難題 4）。寫之前先說清楚「答案在哪一格」。

**由上而下（memoization）也可以**。把轉移寫成遞迴、加上 `functools.cache`，就是 top-down DP。它的好處是只會算到真正需要的狀態（例如 pattern 很少 `*` 時），寫起來也最接近思路；缺點是遞迴深度最多 m + n，Python 預設上限約 1000，長度 1000 的兩個字串就要調高 `sys.setrecursionlimit`，而且無法做下面 22.6 的空間壓縮。面試時常見的策略是：先用遞迴把轉移講清楚，再改寫成 bottom-up 表格並壓縮空間。

## 22.4 填表順序：依賴箭頭決定迴圈方向

二維 DP 寫錯最常見的原因不是轉移，而是**填表順序和依賴方向不一致**，結果讀到還沒算好的格子。判斷方法很機械：把一格的轉移畫成箭頭，箭頭指向的格子必須先算。

```text
模板 A／B（62、64、1143、72、97、10、44、115、1092）
依賴：上、左、左上            填表：由上到下、由左到右
     (i-1,j-1)  (i-1,j)
            ↖     ↑
    (i,j-1) ←  (i,j)          答案在右下角

反向網格（174 Dungeon Game）
依賴：下、右                  填表：由下到上、由右到左
           (i,j) → (i,j+1)
             ↓
          (i+1,j)             答案在左上角

區間 DP（第 23 章）
依賴：更短的區間 [i+1, j]、[i, j-1]
填表：依區間長度由短到長，或 i 由大到小、j 由小到大
```

**為什麼 174 要反著填**。有些題目從起點出發時，一格的「好壞」無法只用一個數字描述（難題 4 會看到，正向時要同時記住「目前血量」和「途中最低血量」，兩者互相牽制）；但從終點往回看，每一格只需要回答「從這裡出發到終點，進來時至少要多少血」，又變回一個數字。所以「從哪個角落開始填」本身就是設計的一部分：**選一個方向，讓每一格的答案只需要一個數字、而且只依賴已經算好的格子**。

**同一題常常可以從兩端定義**。LCS 可以定義成「前綴 `s[:i]` 與 `t[:j]`」，也可以定義成「後綴 `s[i:]` 與 `t[j:]`」，後者依賴右下方，迴圈要倒著跑，答案在 `dp[0][0]`。後綴版本在**要從前面開始建構答案**時特別有用，例如難題 5 F2 的「字典序最小的 SCS」：從前往後決定每個字元時，需要知道「剩下的後綴」最佳是多少。

## 22.5 從 DP 表回溯出解

很多面試題先問數值，接著追問「把實際的路徑／字串印出來」。做法是**保留整張表，從答案所在的格子出發，每一步判斷這格的值是由哪一條轉移得到的，就往那個方向退一步**，直到走回 base case。因為每一格的值都等於「某一條轉移的值」，所以一定找得到至少一個來源；有多個來源時任選一個都是最佳解，選法不同會得到不同的合法答案。

```python
def lcs_string(s: str, t: str) -> str:
    m, n = len(s), len(t)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s[i - 1] == t[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    # 回溯：從 (m, n) 走回 (0, 0)
    out = []
    i, j = m, n
    while i > 0 and j > 0:
        if s[i - 1] == t[j - 1]:
            out.append(s[i - 1])        # 這個字元在 LCS 裡，走對角
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1                      # 值來自上方：丟掉 s[i-1]
        else:
            j -= 1                      # 值來自左方：丟掉 t[j-1]
    return "".join(reversed(out))       # 回溯是從尾巴往前收集，最後要反轉


assert lcs_string("abcde", "ace") == "ace"
assert lcs_string("abc", "def") == ""
assert lcs_string("", "abc") == ""
assert len(lcs_string("AGGTAB", "GXTXAYB")) == 4    # "GTAB"
print("all tests passed")
```

三個要點。第一，**回溯需要整張表**，所以空間是 O(m · n)；如果已經把表壓縮成一列，資訊就丟了，必須另外存「每格選了哪個方向」（每格 2 bits）或改用 Hirschberg 演算法（核心題 3 F5）。第二，**回溯的判斷要和轉移一致**：轉移寫「字元相同就走對角」，回溯也要先檢查字元相同；若回溯時改用「值相等」判斷，可能會走到一個值相同但不合法的方向。第三，**收集的順序是反的**，用 list `append` 最後再反轉，比每次在字串前面插入（O(n²)）好。

## 22.6 空間壓縮：只留需要的那幾列

模板 B 的轉移只看「上一列」和「這一列左邊」，所以整張 (m + 1) × (n + 1) 的表可以換成兩列，甚至一列。這是面試官最常追問的優化，也是 L5 等級的面試中「寫完之後還能再好一點」的標準加分項。

```text
二維：dp[i][j] 依賴 dp[i-1][j-1]（↖）、dp[i-1][j]（↑）、dp[i][j-1]（←）

一維：只留一列 row[0..n]，由左到右覆寫
  覆寫 row[j] 之前：row[j]   還是上一列的值 → 就是 ↑
                    row[j-1] 已經是這一列的值 → 就是 ←
                    ↖ 是「上一列的 row[j-1]」，但它剛剛被覆寫了
  → 用一個變數 prev 在覆寫 row[j-1] 之前先存下它

  j:        0     1     2     3
  上一列:  [ a  |  b  |  c  |  d ]
  這一列:  [ a' |  b' |  ?  |    ]    算 row[2] 時：↑ = c，← = b'，↖ = b（存在 prev）
```

```python
def lcs_length_1d(s: str, t: str) -> int:
    if len(t) > len(s):
        s, t = t, s                     # 讓列的長度是較短的那個：O(min(m, n)) 空間
    n = len(t)
    row = [0] * (n + 1)
    for i in range(1, len(s) + 1):
        prev = 0                        # 這一列的 ↖ 起點：dp[i-1][0] = 0
        for j in range(1, n + 1):
            saved = row[j]              # 還沒覆寫前的 row[j] 是 dp[i-1][j]，下一格的 ↖
            if s[i - 1] == t[j - 1]:
                row[j] = prev + 1
            else:
                row[j] = max(row[j], row[j - 1])
            prev = saved
    return row[n]


assert lcs_length_1d("abcde", "ace") == 3
assert lcs_length_1d("ace", "abcde") == 3          # 交換後結果相同
assert lcs_length_1d("", "") == 0
assert lcs_length_1d("aaaa", "aa") == 2
print("all tests passed")
```

**什麼時候可以壓、怎麼壓**：

- 只依賴上一列與左邊：一列加一個 `prev` 變數（LCS、編輯距離、交錯字串、萬用字元匹配）。
- 只依賴上一列與上一列的左邊（沒有 ←）：一列、**j 由大到小**覆寫，就不需要 `prev`（難題 3 的 Distinct Subsequences，與第 23 章 0/1 背包同理）。
- 依賴兩列以前（例如 Damerau 編輯距離的 `dp[i-2][j-2]`）：保留三列輪替。
- 要回溯出解：不能壓縮，或改用 Hirschberg（分治，O(m · n) 時間、O(m + n) 空間）。
- 讓較短的序列當「列」，空間是 O(min(m, n))；有些題目（交錯字串）交換兩個輸入時要一起交換相關的輸入，不能只換一個。

## 22.7 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| `dp[i][j]` 直接讀 `s[i]` 而不是 `s[i-1]` | `IndexError`，或答案少算第一個字元 | 表格多一列一行時，固定寫「`dp[i][j]` 看 `s[i-1]`、`t[j-1]`」，寫在註解裡 |
| 忘記初始化第 0 列、第 0 行 | 編輯距離把 `("", "abc")` 算成 0；匹配題把 `"a*b*"` 對空字串算成 False | 先問「空前綴對空前綴、空前綴對非空前綴」各是多少，寫成獨立的迴圈 |
| 填表順序與依賴方向不符 | 讀到還是初始值的格子，答案偏小或偏大 | 畫出依賴箭頭，迴圈方向讓箭頭都指向已填區域（22.4 節） |
| 壓成一列時覆寫掉對角值 | LCS 偏大或偏小，只在某些輸入出錯 | 覆寫 `row[j]` 前先存起來給下一格當 ↖；或 j 倒著跑（沒有 ← 依賴時） |
| 一維計數題 j 正著跑 | 同一個字元被用了兩次，計數偏大（115 題） | 沒有 ← 依賴時 j 由大到小，或保留兩列 |
| 回溯時用「值相等」而非「轉移條件」判斷方向 | 輸出的字串不是合法的共同子序列 | 回溯的判斷順序與轉移完全一致：先檢查字元相同，再比較上與左 |
| 網格允許四個方向卻用 DP | 依賴形成環，表格怎麼填都不對 | 四方向、可回頭就用 BFS／Dijkstra（第 15、18 章），或改成 DAG 上的 memo（第 16 章難題 2） |
| 把子序列和子字串搞混 | LCS 的轉移用在最長共同子字串，答案偏大 | 子字串要求連續：字元不同時歸零，答案取整張表的最大值 |
| 只記得 top-down，長字串時遞迴過深 | `RecursionError` | 長度上千時改 bottom-up，或調高 `sys.setrecursionlimit` 並說明風險 |

## 核心題 1｜62. Unique Paths｜Medium

### 題目

一個機器人站在 m × n 網格的左上角 (0, 0)，每一步只能往右或往下走一格，目標是走到右下角 (m − 1, n − 1)。請回傳總共有幾條不同的路徑。限制：`1 <= m, n <= 100`，題目保證答案不超過 2 × 10⁹。

- 範例 1：`m = 3`、`n = 7`，回傳 `28`。
- 範例 2：`m = 3`、`n = 2`，回傳 `3`：右下下、下右下、下下右。
- 範例 3（邊界）：`m = 1`、`n = 1`，回傳 `1`。起點就是終點，「什麼都不走」算一條路徑。
- 範例 4（邊界）：`m = 1`、`n = 100`，回傳 `1`，只能一路往右。

### 思路

暴力解是遞迴列舉：從 (0, 0) 出發，每一步試往右與往下，走到終點就計數加一。呼叫次數至少等於答案本身，100 × 100 的網格答案大約是 2.3 × 10⁵⁸（題目的 2 × 10⁹ 保證只是限制了輸入讓答案不會太大），所以指數級的列舉不可行。瓶頸在於：大量不同的路徑會經過同一個格子，而「從這個格子走到終點有幾種方法」每次都被重算。

關鍵觀察是倒過來想最後一步。走到 (i, j) 的最後一步，不是從上面的 (i − 1, j) 往下，就是從左邊的 (i, j − 1) 往右，兩類路徑互不重疊（最後一步不同）且涵蓋全部，所以 `dp[i][j] = dp[i-1][j] + dp[i][j-1]`。第一列的格子只能從左邊一路走來，第一行只能從上面一路走來，所以都是 1。因為只依賴上與左，一列一列、由左到右填，填到 (i, j) 時兩個來源都已算好，這就是 22.3 節的模板 A，只是把 `min` 換成加法。

再進一步，填第 i 列時只需要第 i − 1 列，所以可以只留一列 `row`：由左到右更新 `row[j] += row[j-1]`，更新前的 `row[j]` 是「上面」，`row[j-1]` 已經是這一列的「左邊」，一個加法就完成轉移。這題的依賴沒有對角線，所以不需要 22.6 節的 `prev` 變數。

```text
m = 3，n = 7：dp[i][j] = 上 + 左，第一列、第一行都是 1

        j=0  1   2   3   4   5   6
i=0      1   1   1   1   1   1   1
i=1      1   2   3   4   5   6   7
i=2      1   3   6  10  15  21  28   ← 答案

一維覆寫第 2 列的過程（row 一開始是第 1 列）：
初始       row = [1, 2, 3, 4, 5, 6, 7]
j=1  row[1] = 2 + 1  = 3    [1, 3, 3, 4, 5, 6, 7]
j=2  row[2] = 3 + 3  = 6    [1, 3, 6, 4, 5, 6, 7]
j=3  row[3] = 4 + 6  = 10   [1, 3, 6, 10, 5, 6, 7]
j=4  row[4] = 5 + 10 = 15
j=5  row[5] = 6 + 15 = 21
j=6  row[6] = 7 + 21 = 28   ← 加號左邊是「上面」（舊值），右邊是「左邊」（新值）
```

這張表其實就是旋轉 45 度的巴斯卡三角形：`dp[i][j] = C(i + j, i)`。理由是任何一條到 (i, j) 的路徑都由 i 個「下」和 j 個「右」組成，路徑和「在 i + j 步中選哪 i 步往下」一一對應。所以答案也能直接算 `C(m + n − 2, m − 1)`，見 F2。

### 解法

```python
from math import comb
import random


def unique_paths(m: int, n: int) -> int:
    row = [1] * n                      # 第 0 列全部是 1
    for _ in range(1, m):
        for j in range(1, n):
            row[j] += row[j - 1]       # 舊 row[j] 是上方，row[j-1] 是同一列左方
    return row[n - 1]


def unique_paths_2d(m: int, n: int) -> int:
    dp = [[1] * n for _ in range(m)]
    for i in range(1, m):
        for j in range(1, n):
            dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
    return dp[m - 1][n - 1]


def unique_paths_comb(m: int, n: int) -> int:
    # 共走 m + n − 2 步，從中選 m − 1 步往下
    return comb(m + n - 2, m - 1)


assert unique_paths(3, 7) == 28
assert unique_paths(3, 2) == 3
assert unique_paths(1, 1) == 1
assert unique_paths(1, 100) == 1
assert unique_paths(100, 1) == 1
assert unique_paths(10, 10) == 48620
for _ in range(200):
    a, b = random.randint(1, 30), random.randint(1, 30)
    assert unique_paths(a, b) == unique_paths_2d(a, b) == unique_paths_comb(a, b)
print("all tests passed")
```

### 複雜度與邊界

DP 版本時間 O(m · n)，每格一次加法；一維版本空間 O(n)，若先讓 n 取 `min(m, n)`（網格轉置不改變答案）就是 O(min(m, n))。組合數版本只需要 O(min(m, n)) 次乘除，空間 O(1)。邊界情況：m = 1 或 n = 1 時內層迴圈不執行，答案是 1；1 × 1 網格答案也是 1（空路徑）。Python 整數不會溢位，但在 Java／C++ 中 100 × 100 的答案遠超 64 位元，題目才會額外保證答案 ≤ 2 × 10⁹；中間值 `row[j]` 不會超過最終答案，因為表格值沿著右、下方向只增不減。

### Follow-up

> [!question]- F1. 如果網格中有障礙物（63. Unique Paths II）呢？
> 障礙物的格子路徑數設為 0，其餘照樣是「上 + 左」。最大的差別在第一列與第一行：它們不再全是 1，一旦遇到障礙物，後面的格子都變成 0（只有一個來源，而那個來源被擋住）。用一維寫法時這件事會自動處理：`row` 初始為 `[1, 0, 0, …]`，對每一列由左到右，遇到障礙就 `row[j] = 0`，否則 `row[j] += row[j-1]`（j = 0 時不加）。起點本身是障礙物時答案是 0。時間 O(m · n)、空間 O(n)。

> [!question]- F2. 能不能不用 DP，更快地算出答案？
> 能。每條路徑恰好是 m − 1 個「下」和 n − 1 個「右」的一種排列，所以答案是 `C(m + n − 2, m − 1)`。逐步計算 `res = res * (n − 1 + k) // k`（k 從 1 到 m − 1）每一步都是整數，因為連續 k 個整數的乘積一定被 k! 整除；取 `min(m, n) − 1` 當 k 的上限，只需 O(min(m, n)) 次運算。如果答案要對質數 p 取模（網格很大時常見），就預先算階乘與反元素（Fermat 小定理：a⁻¹ ≡ a^(p−2)），每次查詢 O(1)。面試時先寫 DP 再提這個公式，可以展示你看得出表格就是巴斯卡三角形。

> [!question]- F3. 如果路徑必須經過某個格子 (r, c)，或必須避開幾個特定格子呢？
> 必須經過 (r, c)：路徑在 (r, c) 處切成獨立的兩段，答案是 `C(r + c, r) × C((m−1−r) + (n−1−c), m−1−r)`，O(1)（有預處理的組合數）。必須避開一個格子：總數減去經過它的數量。若有 k 個禁止格子而網格大到不能開表（例如 10⁵ × 10⁵），把禁止格子按 (r, c) 排序，令 `f[a]` = 從起點到第 a 個禁止格子、途中不經過其他禁止格子的路徑數，`f[a] = C(到 a) − Σ f[b] × C(b 到 a)`（b 在 a 的左上方），把終點也當成最後一個「禁止格子」，答案就是它的 f 值。時間 O(k²)，與網格大小無關。

> [!question]- F4. 用 'H'（右）和 'V'（下）表示路徑，要回傳字典序第 k 小的路徑（1643. Kth Smallest Instructions）呢？
> 逐位決定，每一位都先試字典序較小的 'H'。目前還剩 h 個 'H'、v 個 'V' 時，以 'H' 開頭的路徑有 `C(h − 1 + v, v)` 條：若 k 不超過它，這一位就放 'H'、h 減一；否則 k 減去這個數量、這一位放 'V'、v 減一。h 用完後剩下全放 'V'。每一位 O(1)（組合數可以用表格中的 dp 值代替，dp 表本身就是組合數），總共 O(m + n)。這是「計數 DP 回答第 k 個」的典型用法：用表格裡的數量當作跳過整個分支的步長。例如 destination = (2, 3) 時，第 1、2、3 小分別是 `HHHVV`、`HHVHV`、`HHVVH`。

> [!question]- F5. 如果還可以往右下斜走一步，或者網格變成三維呢？
> 斜走時 (i, j) 多了一個來源 (i − 1, j − 1)，轉移變成 `dp[i][j] = 上 + 左 + 左上`，第一列與第一行仍是 1，結果是 Delannoy 數（3 × 3 網格有 13 條）。一維壓縮時要用 22.6 節的 `prev` 變數保存對角值。三維網格只能沿三個正方向走時，`dp[i][j][k]` = 三個來源相加，時間與空間 O(a · b · c)，空間可壓成兩層 O(b · c)；組合解是多項式係數 `(a+b+c−3)! / ((a−1)! (b−1)! (c−1)!)`。

## 核心題 2｜64. Minimum Path Sum｜Medium

### 題目

給一個 m × n 的非負整數網格 `grid`，從左上角走到右下角，每一步只能往右或往下。路徑的成本是經過的所有格子（含起點與終點）的數字總和，請回傳最小成本。限制：`1 <= m, n <= 200`，`0 <= grid[i][j] <= 200`。

- 範例 1：`grid = [[1, 3, 1], [1, 5, 1], [4, 2, 1]]`，回傳 `7`，路徑是 1 → 3 → 1 → 1 → 1。
- 範例 2：`grid = [[1, 2, 3], [4, 5, 6]]`，回傳 `12`，路徑是 1 → 2 → 3 → 6。
- 範例 3（邊界）：`grid = [[5]]`，回傳 `5`。
- 範例 4（邊界）：`grid = [[1], [2], [3]]`，只有一行，回傳 `6`。

### 思路

暴力解列舉所有路徑：路徑數是 C(m + n − 2, m − 1)，每條長度 m + n − 1，200 × 200 時是天文數字。另一個直覺是貪婪：每一步走向右邊與下面中較小的那格。貪婪會失敗，因為它只看下一步，看不到後面的代價。例如下面的網格，貪婪第一步選右邊的 2，之後只能穿過一排 9；最佳解是先忍受左下的 5，換來最後一排的 1。

```text
貪婪失敗的例子
 1  2  9          貪婪：1 → 2 → 9 → 1 → 1 = 14（或 1 → 2 → 9 → 9 → 1 = 22）
 5  9  9          最佳：1 → 5 → 1 → 1 → 1 = 9
 1  1  1
```

正確的觀察是最優子結構：到 (i, j) 的最小成本路徑，最後一步來自上方或左方，而去掉最後一格的那段，一定是到它前一格的最小成本路徑（否則換成更便宜的前段，整條就更便宜）。所以 `dp[i][j] = grid[i][j] + min(dp[i-1][j], dp[i][j-1])`，第一列只能從左邊來、第一行只能從上面來。這正是 22.3 節的模板 A。和 62 題比較，結構完全相同，只是「合併兩個來源」的運算從加法變成 `min`，而且每格自己的成本要加上去。

要回傳路徑時，保留整張表，從右下角往回走：當前格的值減去自己的成本，等於上面那格就往上，否則往左（22.5 節）。

```text
grid                 dp（到該格的最小成本）
 1  3  1              1   4   5
 1  5  1              2   7   6
 4  2  1              6   8   7   ← 答案

填表過程（row-major）：
dp[0][0] = 1
第 0 列只能從左來：4 = 1 + 3，5 = 4 + 1
第 0 行只能從上來：2 = 1 + 1，6 = 2 + 4
dp[1][1] = 5 + min(上 4, 左 2) = 7
dp[1][2] = 1 + min(上 5, 左 7) = 6
dp[2][1] = 2 + min(上 7, 左 6) = 8
dp[2][2] = 1 + min(上 6, 左 8) = 7

回溯：(2,2) 7 − 1 = 6 = 上方 → (1,2) 6 − 1 = 5 = 上方 → (0,2)
      (0,2) 在第 0 列，只能往左 → (0,1) → (0,0)
路徑（反轉後）：(0,0) (0,1) (0,2) (1,2) (2,2)，數字 1 3 1 1 1
```

### 解法

```python
from itertools import combinations
import random


def min_path_sum(grid: list[list[int]]) -> int:
    m, n = len(grid), len(grid[0])
    row = [0] * n
    for i in range(m):
        for j in range(n):
            if i == 0 and j == 0:
                row[j] = grid[0][0]
            elif i == 0:
                row[j] = row[j - 1] + grid[i][j]           # 只能從左來
            elif j == 0:
                row[j] = row[j] + grid[i][j]               # 只能從上來（舊 row[0]）
            else:
                row[j] = grid[i][j] + min(row[j], row[j - 1])
    return row[n - 1]


def min_path_with_route(grid: list[list[int]]) -> tuple[int, list[tuple[int, int]]]:
    m, n = len(grid), len(grid[0])
    dp = [[0] * n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            if i == 0 and j == 0:
                dp[i][j] = grid[i][j]
            elif i == 0:
                dp[i][j] = dp[i][j - 1] + grid[i][j]
            elif j == 0:
                dp[i][j] = dp[i - 1][j] + grid[i][j]
            else:
                dp[i][j] = grid[i][j] + min(dp[i - 1][j], dp[i][j - 1])
    route = [(m - 1, n - 1)]
    i, j = m - 1, n - 1
    while (i, j) != (0, 0):
        if i > 0 and (j == 0 or dp[i - 1][j] <= dp[i][j - 1]):
            i -= 1
        else:
            j -= 1
        route.append((i, j))
    return dp[m - 1][n - 1], route[::-1]


def brute(grid):
    m, n = len(grid), len(grid[0])
    best = None
    for downs in combinations(range(m + n - 2), m - 1):
        i = j = 0
        total = grid[0][0]
        for step in range(m + n - 2):
            if step in downs:
                i += 1
            else:
                j += 1
            total += grid[i][j]
        best = total if best is None else min(best, total)
    return best


assert min_path_sum([[1, 3, 1], [1, 5, 1], [4, 2, 1]]) == 7
assert min_path_sum([[1, 2, 3], [4, 5, 6]]) == 12
assert min_path_sum([[5]]) == 5
assert min_path_sum([[1], [2], [3]]) == 6
assert min_path_sum([[1, 2, 9], [5, 9, 9], [1, 1, 1]]) == 9    # 貪婪會失敗的例子
cost, route = min_path_with_route([[1, 3, 1], [1, 5, 1], [4, 2, 1]])
assert cost == 7 and route == [(0, 0), (0, 1), (0, 2), (1, 2), (2, 2)]
for _ in range(300):
    m, n = random.randint(1, 5), random.randint(1, 5)
    g = [[random.randint(0, 9) for _ in range(n)] for _ in range(m)]
    c, r = min_path_with_route(g)
    assert min_path_sum(g) == c == brute(g) == sum(g[a][b] for a, b in r)
    assert len(r) == m + n - 1
print("all tests passed")
```

### 複雜度與邊界

時間 O(m · n)，每格一次 `min`。只求數值時空間 O(n)（或轉置後 O(min(m, n))）；也可以直接在 `grid` 上原地改寫做到 O(1) 額外空間，但會破壞輸入，面試時要先問能不能修改。要回傳路徑時需要 O(m · n) 的表，回溯 O(m + n)。邊界情況：只有一列或一行時路徑唯一，答案是總和；1 × 1 時答案是那一格；格子值為 0 時可能有多條最佳路徑，回溯任選一條（程式在平手時優先往上）。題目保證非負，但這個 DP 其實**允許負數**，因為只能往右往下、沒有環，負數不會造成無限循環；會壞掉的是四方向移動的版本（F2）。

### Follow-up

> [!question]- F1. 如果要同時回傳路徑，但記憶體只允許 O(n) 呢？
> 回溯需要知道每一格「選了上還是左」，壓成一列之後這個資訊就不見了。折衷做法是只額外存每格的選擇方向，每格 1 bit，總共 m · n bits（200 × 200 只有 5 KB），用 `bytearray` 或整數位元表示；回溯時從右下角照著方向往回走。如果連 m · n bits 都不行，可以用 Hirschberg 式的分治：在中間那一列找出最佳路徑經過的格子（正向算到中間列、反向從終點算到中間列，兩者相加最小的位置），遞迴處理左上與右下兩塊，時間仍是 O(m · n)（等比級數），空間 O(m + n)。

> [!question]- F2. 如果可以往上下左右四個方向走呢？
> 四方向會形成環，「先算上面再算下面」的順序不存在，DP 的前提失效。因為成本非負，這是格子圖上的單源最短路徑，用 Dijkstra（第 18 章）：節點是格子，進入一格的邊權是該格的值，時間 O(m · n · log(m · n))。如果格子值只有 0 和 1，可以用 0-1 BFS（deque，權重 0 放前面、1 放後面）做到 O(m · n)。如果允許負數，四方向時可能有負環（兩個相鄰的負數格來回走），最短路徑沒有定義，題目必須額外規定每格最多經過一次，那就變成 NP-hard 的最長／最短簡單路徑問題，不再有多項式解。

> [!question]- F3. 如果要走去再走回來，格子上的數字（櫻桃）只能撿一次，要最大化總收穫（741. Cherry Pickup）呢？
> 「先跑一次最佳路徑、把撿過的清零、再跑一次」是錯的：第一趟的最佳可能毀掉第二趟的好路線。正確做法是把回程倒過來看，變成**兩個人同時從左上走到右下**，每一步兩人都走一格，所以走了 t 步時兩人的 r + c = t，狀態只需要 (t, r1, r2)，c1 = t − r1、c2 = t − r2。轉移是兩人各自從上或左來，共 4 種組合；兩人站在同一格時只算一次。n × n 網格有 O(n) 個 t、O(n²) 個 (r1, r2)，總共 O(n³) 時間，空間可以只保留上一個 t 的 O(n²) 表。關鍵是「同步走」讓兩條路徑的衝突（撿同一格）可以在同一個狀態裡判斷。

> [!question]- F4. 如果網格換成三角形，每步只能往正下方或右下方（120. Triangle）呢？
> 由下往上做最自然：`dp[j] = tri[i][j] + min(dp[j], dp[j+1])`，從最後一列開始往上，最後答案就是 `dp[0]`。由下往上的好處是每一格都恰好有兩個子節點，不用處理三角形邊緣「只有一個父節點」的特判，而且最後不必在一整列中取最小值。一維陣列由左到右覆寫是安全的，因為 `dp[j]` 只依賴 `dp[j]` 和 `dp[j+1]`，而 `dp[j+1]` 還沒被這一輪覆寫。時間 O(n²)（元素總數），額外空間 O(n)。

> [!question]- F5. 如果路徑成本改成「途中經過的最大值」，要最小化它呢？
> 只能往右往下時，同一個 DP 換一個合併運算即可：`dp[i][j] = max(grid[i][j], min(dp[i-1][j], dp[i][j-1]))`，因為「到前一格的瓶頸」越小，加上這一格後的瓶頸也只會越小或不變（`max` 對參數單調），最優子結構仍成立。時間 O(m · n)。若改成四方向（例如 778. Swim in Rising Water、1631. Path With Minimum Effort），就回到圖論：用 Dijkstra 的變形（路徑成本取 max 而不是加總）、二分答案加 BFS（第 8 章的思路），或依格子值由小到大做 Union-Find 直到起點與終點連通（第 17 章難題 2）。

## 核心題 3｜1143. Longest Common Subsequence｜Medium

### 題目

給兩個只含小寫英文字母的字串 `text1` 與 `text2`，回傳它們最長共同子序列（LCS，longest common subsequence）的長度。子序列是從原字串刪掉零個或多個字元、其餘字元保持原本相對順序得到的字串，不要求連續；兩個字串都沒有共同字元時回傳 0。限制：`1 <= len(text1), len(text2) <= 1000`。

- 範例 1：`text1 = "abcde"`、`text2 = "ace"`，回傳 `3`，LCS 是 `"ace"`。
- 範例 2：`text1 = "abc"`、`text2 = "abc"`，回傳 `3`。
- 範例 3（邊界）：`text1 = "abc"`、`text2 = "def"`，回傳 `0`。
- 範例 4：`text1 = "bsbininm"`、`text2 = "jmjkbkjkv"`，回傳 `1`，只有一個 `"b"` 或 `"m"` 能配上（兩者在兩個字串中的先後順序相反，不能同時取）。

### 思路

暴力解是列舉 `text1` 的全部 2ᵐ 個子序列，逐一用 two pointers 檢查是否為 `text2` 的子序列，時間 O(2ᵐ · n)。改成遞迴後可以看出結構：只看兩個前綴的最後一個字元 `s[i-1]` 與 `t[j-1]`。

- **相同**：直接把它們配成一對，答案是 `dp[i-1][j-1] + 1`。為什麼一定可以配？假設某個最長共同子序列沒有把這兩個字元配在一起，它最後一對配對 (a, b) 中至少有一個不是 i − 1 或 j − 1；把那一對換成 (i − 1, j − 1)，長度不變、順序仍合法（i − 1 和 j − 1 是兩個前綴的最後位置，比任何其他配對都晚）。所以存在一個最佳解用到這一對。
- **不同**：這兩個字元不可能互相配對，所以至少有一個不在 LCS 裡（或者兩個都不在），答案是 `max(dp[i-1][j], dp[i][j-1])`。「兩個都不在」的情況 `dp[i-1][j-1]` 已經包含在兩者之中，不用另外列。

base case 是任何一邊為空前綴時 LCS 為 0，也就是第 0 列與第 0 行全是 0。這是 22.3 節模板 B 的標準形，轉移只用到對角、上、左三格。

```text
s = "abcde"（列），t = "ace"（行）
相同 → ↖ + 1；不同 → max(↑, ←)

          ""   a    c    e
     ""    0   0    0    0
     a     0   1↖   1←   1←
     b     0   1↑   1↑   1↑
     c     0   1↑   2↖   2←
     d     0   1↑   2↑   2↑
     e     0   1↑   2↑   3↖   ← 答案 dp[5][3] = 3

逐格說明幾個關鍵格子：
dp[1][1]：'a' = 'a' → dp[0][0] + 1 = 1
dp[3][2]：'c' = 'c' → dp[2][1] + 1 = 2
dp[4][3]：'d' ≠ 'e' → max(上 dp[3][3] = 2, 左 dp[4][2] = 2) = 2
dp[5][3]：'e' = 'e' → dp[4][2] + 1 = 3

回溯（22.5 節）：(5,3) 'e'='e' 收 e ↖ → (4,2) 'd'≠'c'，上 2 ≥ 左 1 → 往上
               (3,2) 'c'='c' 收 c ↖ → (2,1) 'b'≠'a'，上 1 ≥ 左 0 → 往上
               (1,1) 'a'='a' 收 a ↖ → (0,0) 結束；反轉得到 "ace"
```

表格的每一格都可以用一句話讀出意義，例如 `dp[4][3] = 2` 代表「`"abcd"` 與 `"ace"` 的 LCS 長度是 2」。面試時一邊畫表一邊說出這句話，面試官就知道你的狀態定義是清楚的。

### 解法

```python
from itertools import combinations
import random


def longest_common_subsequence(text1: str, text2: str) -> int:
    s, t = (text1, text2) if len(text1) >= len(text2) else (text2, text1)
    n = len(t)
    row = [0] * (n + 1)
    for i in range(1, len(s) + 1):
        prev = 0                              # dp[i-1][0]
        for j in range(1, n + 1):
            saved = row[j]                    # dp[i-1][j]，下一格的 ↖
            if s[i - 1] == t[j - 1]:
                row[j] = prev + 1
            else:
                row[j] = max(row[j], row[j - 1])
            prev = saved
    return row[n]


def lcs_table(s: str, t: str) -> list[list[int]]:
    m, n = len(s), len(t)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s[i - 1] == t[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp


def is_subsequence(a: str, b: str) -> bool:
    it = iter(b)
    return all(ch in it for ch in a)


def brute(s: str, t: str) -> int:
    for k in range(len(s), -1, -1):
        for idx in combinations(range(len(s)), k):
            if is_subsequence("".join(s[i] for i in idx), t):
                return k
    return 0


assert longest_common_subsequence("abcde", "ace") == 3
assert longest_common_subsequence("abc", "abc") == 3
assert longest_common_subsequence("abc", "def") == 0
assert longest_common_subsequence("bsbininm", "jmjkbkjkv") == 1
assert longest_common_subsequence("a", "a") == 1
assert lcs_table("abcde", "ace")[4][3] == 2
for _ in range(300):
    a = "".join(random.choice("abc") for _ in range(random.randint(1, 7)))
    b = "".join(random.choice("abc") for _ in range(random.randint(1, 7)))
    assert longest_common_subsequence(a, b) == lcs_table(a, b)[-1][-1] == brute(a, b)
print("all tests passed")
```

### 複雜度與邊界

時間 O(m · n)，長度 1000 時是 10⁶ 次格子運算，Python 大約一秒內。空間：二維表 O(m · n)，一維版本 O(min(m, n))（先把較短的字串放在行）。邊界情況：任何一邊為空時答案 0（題目限制長度 ≥ 1，但程式要能處理）；兩字串相同時答案是長度；完全沒有共同字元時整張表都是 0。一維版本最容易出錯的地方是 `prev` 的更新：每一列開始時要重設為 0（代表 `dp[i-1][0]`），每一格結束時把覆寫前的 `row[j]` 交給下一格當對角值。

### Follow-up

> [!question]- F1. 如果要回傳其中一個 LCS 字串，或回傳字典序最小的那一個呢？
> 回傳任一個：保留二維表，從 (m, n) 回溯，字元相同就收下並走對角，否則往值較大的方向（上或左）走，最後反轉，O(m + n) 回溯加 O(m · n) 建表（22.5 節）。字典序最小的 LCS 不能靠回溯的平手規則保證，要改用**後綴表** `suf[i][j]` = `s[i:]` 與 `t[j:]` 的 LCS 長度，然後從前面逐字元建構：剩餘長度 L 時，從 'a' 到 'z' 找第一個字元 c，使得在 `s[i:]`、`t[j:]` 中 c 的第一次出現位置 p、q 滿足 `suf[p+1][q+1] == L − 1`，選它並跳到 (p + 1, q + 1)。用「下一次出現位置」表 `nxt[i][c]` 可以 O(1) 找到 p、q，總時間 O(m · n + L · 26)。

> [!question]- F2. 如果要求的是最長共同子字串（必須連續，718. Maximum Length of Repeated Subarray）呢？
> 狀態改成「以 `s[i-1]` 和 `t[j-1]` **結尾**的最長共同子字串長度」：字元相同時 `dp[i][j] = dp[i-1][j-1] + 1`，不同時歸零（連續性斷了）。因為狀態綁定結尾，答案不在右下角，而是整張表的最大值。時間 O(m · n)、空間可壓到一列（只依賴對角，由右往左覆寫就不需要 `prev`）。更快的做法是二分答案長度 L 加上 rolling hash（第 25 章）：「存在長度 L 的共同子字串」對 L 單調，檢查用雜湊集合 O(m + n)，總共 O((m + n) log min(m, n))；也可以用 suffix automaton 做到線性。

> [!question]- F3. 如果其中一個序列的元素互不相同（例如 1713. Minimum Operations to Make a Subsequence），長度到 10⁵ 呢？
> O(m · n) 的表會是 10¹⁰，太慢。當 `target` 元素互不相同時，把每個值對應到它在 `target` 中的位置，再把 `arr` 中出現在 `target` 的元素換成這個位置，丟掉其他元素。這時 `arr` 與 `target` 的共同子序列，恰好對應到位置序列中的**嚴格遞增子序列**，所以 LCS = 位置序列的 LIS，用第 21 章核心題 3 的 patience sorting 做到 O(n log n)。1713 的答案是 `len(target) − LCS`。一般情況（有重複）可以推廣成 Hunt–Szymanski：列出所有配對 (i, j)，同一個 i 的 j 由大到小排，再做 LIS，時間 O((r + m) log n)，r 是配對總數；r 很大時退化回 O(m · n log n)。

> [!question]- F4. 如果要求三個字串的 LCS 呢？可以先算兩個的 LCS 再和第三個算嗎？
> 不行。兩兩合併依賴「選了哪一個 LCS」，而 LCS 可能不唯一。例如 a = "ab"、b = "ba"、c = "a"：a 與 b 的 LCS 可以是 "a" 或 "b"，若選到 "b"，再和 c 算就得到 0，但三者真正的 LCS 是 "a"，長度 1。正確做法是三維 DP：`dp[i][j][k]`，三個最後字元都相同時取 `dp[i-1][j-1][k-1] + 1`，否則取三個「各退一格」中的最大值。時間與空間 O(a · b · c)，空間可壓成兩層 O(b · c)。對任意多個字串，LCS 是 NP-hard，所以 k 個字串時表格大小必然是長度乘積的級別。

> [!question]- F5. 如果字串長度是 10⁵，記憶體放不下 m · n 的表，但仍要回傳 LCS 字串呢？
> 用 Hirschberg 演算法（分治）。把 `s` 從中間切成 `s[:mid]` 與 `s[mid:]`，用一維 DP 算出 `s[:mid]` 對 `t` 每個前綴的 LCS 長度 `F[k]`，再把 `s[mid:]` 與 `t` 都反轉，算出對 `t` 每個後綴的 LCS 長度 `B[k]`；使 `F[k] + B[k]` 最大的 k 就是最佳 LCS 在 `t` 上的切點。接著遞迴解 `(s[:mid], t[:k])` 與 `(s[mid:], t[k:])`，把兩段結果接起來。每一層的工作量是上一層的一半，總時間仍是 O(m · n)（大約兩倍常數），空間只有 O(m + n)。長度 10⁵ 時 10¹⁰ 次運算仍然太慢，這時要配合 F3 的 LIS 轉換或 bit-parallel LCS（每次處理 64 個位元）。

## 核心題 4｜72. Edit Distance｜Medium

### 題目

給兩個字串 `word1` 與 `word2`，每次可以對 `word1` 做三種操作之一：插入一個字元、刪除一個字元、把一個字元替換成另一個字元，每次操作成本 1。請回傳把 `word1` 變成 `word2` 的最少操作次數（也就是 Levenshtein 距離）。限制：`0 <= len(word1), len(word2) <= 500`，只含小寫英文字母。

- 範例 1：`word1 = "horse"`、`word2 = "ros"`，回傳 `3`：horse → rorse（h 換成 r）→ rose（刪 r）→ ros（刪 e）。
- 範例 2：`word1 = "intention"`、`word2 = "execution"`，回傳 `5`。
- 範例 3（邊界）：`word1 = ""`、`word2 = "abc"`，回傳 `3`，全部插入。
- 範例 4（邊界）：`word1 = "abc"`、`word2 = "abc"`，回傳 `0`。

### 思路

暴力解是遞迴嘗試所有操作序列：每一步對目前的字串試插入、刪除、替換，分支因子是 3 乘上位置數與字母數，指數級。先觀察到操作的順序不重要，重要的是最後**兩個字串怎麼對齊**：`word1` 的每個字元要嘛保留（對到 `word2` 的同一個字元）、要嘛被替換（對到 `word2` 的不同字元）、要嘛被刪除（對到空白）；`word2` 中沒被對到的字元就是插入。於是可以只看兩個前綴的最後一個字元，定義 `dp[i][j]` = 把 `word1[:i]` 變成 `word2[:j]` 的最少操作數。

- `word1[i-1] == word2[j-1]`：最後一個字元不用動，`dp[i][j] = dp[i-1][j-1]`。
- 不同時，三種選擇各花 1 次：替換（兩者對齊）`dp[i-1][j-1] + 1`；刪除 `word1[i-1]` 後，剩下把 `word1[:i-1]` 變成 `word2[:j]`，即 `dp[i-1][j] + 1`；插入 `word2[j-1]` 後，剩下把 `word1[:i]` 變成 `word2[:j-1]`，即 `dp[i][j-1] + 1`。取三者最小。

base case：`dp[i][0] = i`（全部刪除）、`dp[0][j] = j`（全部插入）。字元相同時為什麼可以不考慮刪除與插入？因為表格中相鄰兩格的值最多差 1（多一個字元最多多一次操作），所以 `dp[i-1][j-1] ≤ dp[i-1][j] + 1` 且 `≤ dp[i][j-1] + 1`，直接走對角永遠不會更差。這和 22.3 節的 `align_cost` 是同一份程式。

```text
word1 = "horse"（列），word2 = "ros"（行）
相同 → ↖；不同 → 1 + min(↖ 替換, ↑ 刪除, ← 插入)

          ""   r    o    s
     ""    0   1    2    3
     h     1   1↖   2    3
     o     2   2    1↖   2←
     r     3   2↖   2    2
     s     4   3    3    2↖
     e     5   4    4    3↑    ← 答案 3

幾個格子的計算：
dp[1][1] h≠r：1 + min(↖0, ↑1, ←1) = 1   （替換 h→r）
dp[2][2] o=o：dp[1][1] = 1
dp[3][3] r≠s：1 + min(↖1, ↑2, ←2) = 2
dp[5][3] e≠s：1 + min(↖3, ↑2, ←4) = 3   （刪除 e）

回溯：(5,3) 來自 ↑：刪除 e
      (4,3) s=s ↖：保留 s
      (3,2) r≠o，1 + min(↖2, ↑1, ←2)，來自 ↑：刪除 r
      (2,2) o=o ↖：保留 o
      (1,1) h≠r，來自 ↖：替換 h→r
得到操作：替換 h→r、刪除 r、刪除 e，共 3 次，和範例相同
```

### 解法

```python
from functools import cache
import random


def min_distance(word1: str, word2: str) -> int:
    m, n = len(word1), len(word2)
    row = list(range(n + 1))                 # dp[0][j] = j
    for i in range(1, m + 1):
        prev = row[0]                        # dp[i-1][0]
        row[0] = i                           # dp[i][0] = i
        for j in range(1, n + 1):
            saved = row[j]                   # dp[i-1][j]
            if word1[i - 1] == word2[j - 1]:
                row[j] = prev
            else:
                row[j] = 1 + min(prev, row[j], row[j - 1])   # 替換、刪除、插入
            prev = saved
    return row[n]


def edit_script(word1: str, word2: str) -> list[tuple]:
    """回傳一組最少操作：('keep', a)、('replace', a, b)、('delete', a)、('insert', b)。"""
    m, n = len(word1), len(word2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if word1[i - 1] == word2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j - 1], dp[i - 1][j], dp[i][j - 1])
    ops, i, j = [], m, n
    while i > 0 or j > 0:
        if i > 0 and j > 0 and word1[i - 1] == word2[j - 1]:
            ops.append(("keep", word1[i - 1])); i -= 1; j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            ops.append(("replace", word1[i - 1], word2[j - 1])); i -= 1; j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            ops.append(("delete", word1[i - 1])); i -= 1
        else:
            ops.append(("insert", word2[j - 1])); j -= 1
    return ops[::-1]


def apply_script(ops):
    src = "".join(op[1] for op in ops if op[0] != "insert")
    dst = "".join(op[-1] for op in ops if op[0] != "delete")
    cost = sum(op[0] != "keep" for op in ops)
    return src, dst, cost


def reference(a: str, b: str) -> int:
    @cache
    def go(i, j):                          # 由上而下的遞迴版本
        if i == 0 or j == 0:
            return i + j
        if a[i - 1] == b[j - 1]:
            return go(i - 1, j - 1)
        return 1 + min(go(i - 1, j - 1), go(i - 1, j), go(i, j - 1))
    return go(len(a), len(b))


assert min_distance("horse", "ros") == 3
assert min_distance("intention", "execution") == 5
assert min_distance("", "abc") == 3
assert min_distance("abc", "") == 3
assert min_distance("abc", "abc") == 0
assert edit_script("horse", "ros") == [("replace", "h", "r"), ("keep", "o"), ("delete", "r"),
                                       ("keep", "s"), ("delete", "e")]
for _ in range(300):
    a = "".join(random.choice("abc") for _ in range(random.randint(0, 7)))
    b = "".join(random.choice("abc") for _ in range(random.randint(0, 7)))
    d = min_distance(a, b)
    assert d == reference(a, b)
    assert apply_script(edit_script(a, b)) == (a, b, d)
    assert abs(len(a) - len(b)) <= d <= max(len(a), len(b))
print("all tests passed")
```

### 複雜度與邊界

時間 O(m · n)，空間一維版本 O(n)（可交換兩字串取較短者，因為編輯距離對稱：插入與刪除互為反操作）。邊界情況：任一字串為空時答案是另一個的長度，一維版本靠 `row = range(n+1)` 與每列的 `row[0] = i` 處理；兩字串相同時答案 0；答案一定落在 `|m − n|` 與 `max(m, n)` 之間，可以拿來快速檢查程式（測試中的最後一個 assert）。一維版本要注意：每一列開始時 `prev` 必須先存下舊的 `row[0]`（也就是 `dp[i-1][0] = i − 1`），再把 `row[0]` 改成 i，順序反了對角值就錯。

### Follow-up

> [!question]- F1. 如果三種操作的成本不同（插入 cᵢ、刪除 c_d、替換 c_r）呢？
> 同一張表，換成加權：`dp[i][0] = i · c_d`、`dp[0][j] = j · cᵢ`，不同字元時取 `min(↖ + c_r, ↑ + c_d, ← + cᵢ)`。字元相同時仍然走對角成本 0，但「相鄰格最多差 1」的論證要改成「最多差 max(cᵢ, c_d)」，結論不變（走對角不會更差）。若 `c_r > cᵢ + c_d`，最佳解永遠不會替換（先刪再插更便宜），`min` 會自動處理。DNA 序列比對（Needleman–Wunsch）就是這個模型，替換成本依字元對而定，`sub(a, b)` 查表即可，就是 22.3 節的 `align_cost`。

> [!question]- F2. 如果只允許插入和刪除（583. Delete Operation for Two Strings）呢？
> 沒有替換時，兩個字串保留下來的字元必須完全相同，也就是一個共同子序列；保留得越多刪得越少，所以答案是 `m + n − 2 · LCS`，直接用核心題 3。另一種寫法是把 `align_cost` 的不同字元對齊成本設成無限大（22.3 節的 `indel_distance`）。變形 712. Minimum ASCII Delete Sum 要最小化刪除字元的 ASCII 總和，就是 gap 成本改成字元的 ASCII 值的加權版本，同一張表 O(m · n)。

> [!question]- F3. 如果只要判斷兩個字串的編輯距離是否恰好為 1（161. One Edit Distance），或是否 ≤ k 呢？
> 恰好為 1 不需要 DP：長度差超過 1 直接 False；否則用 two pointers 找第一個不同的位置，長度相等時比較兩邊剩下的 `s[i+1:] == t[i+1:]`（替換），長度差 1 時比較 `s[i+1:] == t[i:]`（刪除較長者的字元），O(n)。最後還要排除兩字串完全相同（距離 0）。一般的 ≤ k：最佳路徑不會離開主對角線超過 k 格（每離開一格就要一次插入或刪除），所以只計算 `|i − j| ≤ k` 的帶狀區域，時間 O(k · n)；帶外的格子視為無限大。長度差已經大於 k 時直接回答否。

> [!question]- F4. 如果「交換相鄰兩個字元」也算一次操作呢？
> 這是 Damerau–Levenshtein 距離的受限版本（optimal string alignment）。多一條轉移：若 `i, j ≥ 2` 且 `s[i-1] == t[j-2]`、`s[i-2] == t[j-1]`，則 `dp[i][j] = min(dp[i][j], dp[i-2][j-2] + 1)`。因為依賴兩列以前，空間壓縮要保留三列輪替。例如 "ca" 到 "ac" 的距離從 2 變成 1。要注意這個版本不允許「交換後再編輯同一段」，所以它不滿足三角不等式；完整的 Damerau–Levenshtein 需要記錄每個字元上次出現的位置，複雜度 O(m · n) 但實作更長，面試中通常只要求受限版本。

> [!question]- F5. 如果要對一個很大的字典做拼字建議，找出所有和查詢字編輯距離 ≤ 2 的單字呢？
> 對每個單字跑一次 DP 是 O(字典大小 × L²)。常見的加速有兩種：第一，把字典建成 Trie（第 13 章），從根往下 DFS，每走一個字元就以「上一列 DP」算出新的一列，DP 列的最小值已經大於 2 時整棵子樹剪掉，共享前綴的單字只算一次；第二，BK-tree 利用編輯距離滿足三角不等式，只走距離可能 ≤ 2 的子樹。也可以結合 F3 的帶狀 DP，每次比較 O(k · L)。這題考的是把單次 DP 的一列看成「可以沿著 Trie 傳下去的狀態」。

## 核心題 5｜97. Interleaving String｜Medium

### 題目

給三個字串 `s1`、`s2`、`s3`，判斷 `s3` 是否能由 `s1` 與 `s2` **交錯**組成：把 `s3` 的每個字元標記成來自 `s1` 或 `s2`，標記為 `s1` 的字元依序連起來恰好是 `s1`，標記為 `s2` 的依序連起來恰好是 `s2`。兩邊被切成幾段、誰先開始都不限制。限制：`0 <= len(s1), len(s2) <= 100`，`0 <= len(s3) <= 200`，只含小寫英文字母。進階要求：只用 O(len(s2)) 的額外空間。

- 範例 1：`s1 = "aabcc"`、`s2 = "dbbca"`、`s3 = "aadbbcbcac"`，回傳 `True`：`aa`（s1）＋ `dbbc`（s2）＋ `bc`（s1）＋ `a`（s2）＋ `c`（s1）。
- 範例 2：`s1 = "aabcc"`、`s2 = "dbbca"`、`s3 = "aadbbbaccc"`，回傳 `False`。
- 範例 3（邊界）：`s1 = ""`、`s2 = ""`、`s3 = ""`，回傳 `True`。
- 範例 4（邊界）：`len(s1) + len(s2) != len(s3)` 時一定是 `False`，例如 `s1 = "a"`、`s2 = "b"`、`s3 = "a"`。

### 思路

直覺做法是 two pointers 貪婪：`s3` 的下一個字元和 `s1` 的下一個字元相同就拿 `s1` 的，否則拿 `s2` 的。問題出在兩邊的下一個字元**都**等於 `s3` 的下一個字元時，貪婪只能猜一邊，而猜錯要很久以後才會發現。例如 `s1 = "ca"`、`s2 = "cb"`、`s3 = "cbca"`：貪婪先拿 `s1` 的 c，接著 `s3` 要 b，`s1` 下一個是 a、`s2` 下一個是 c，卡住；正確答案是先拿完 `s2` 的 "cb" 再拿 `s1` 的 "ca"。暴力的回溯在每個平手處都分兩支，最差 O(2^(m+n))。

關鍵觀察：如果已經用掉 `s1` 的前 i 個字元、`s2` 的前 j 個字元，那 `s3` 一定剛好用掉前 i + j 個，所以「目前走到哪」完全由 (i, j) 決定，和之前怎麼交錯無關。回溯裡大量的分支只是用不同順序走到同一個 (i, j)。定義 `dp[i][j]` = `s1[:i]` 與 `s2[:j]` 能否交錯組成 `s3[:i+j]`，`s3` 的最後一個字元 `s3[i+j-1]` 要嘛來自 `s1[i-1]`、要嘛來自 `s2[j-1]`：

`dp[i][j] = (dp[i-1][j] and s1[i-1] == s3[i+j-1]) or (dp[i][j-1] and s2[j-1] == s3[i+j-1])`

另一個很好用的看法是**網格路徑**：(0, 0) 到 (m, n) 的網格中，往下走一步代表從 `s1` 拿一個字元，往右走一步代表從 `s2` 拿一個字元，每一步拿的字元都要等於 `s3` 的下一個字元。問題變成「有沒有一條只往右、往下的合法路徑走到右下角」，也就是核心題 1 的網格模板，只是格子的值從路徑數變成 True／False。

```text
s1 = "aabcc"（往下），s2 = "dbbca"（往右），s3 = "aadbbcbcac"
T = 這個 (i, j) 可以走到；格子 (i, j) 對應 s3[:i+j]

           ""  d   b   b   c   a        j
      ""   T   .   .   .   .   .
      a    T   .   .   .   .   .
      a    T   T   T   T   T   .
      b    .   T   T   .   T   .
      c    .   .   T   T   T   T
      c    .   .   .   T   .   T   ← dp[5][5] = T
      i

一條可行路徑（↓ 取 s1，→ 取 s2）：
(0,0) ↓a (1,0) ↓a (2,0) →d (2,1) →b (2,2) →b (2,3) →c (2,4)
      ↓b (3,4) ↓c (4,4) →a (4,5) ↓c (5,5)
拿到的字元依序：a a d b b c b c a c = s3 ✓

範例 2 的 s3 = "aadbbbaccc"：i = 2、3 兩列在 j = 3 之後全部斷掉，
i = 4 以下全是 .，dp[5][5] = False
```

### 解法

```python
from functools import cache
import random


def is_interleave(s1: str, s2: str, s3: str) -> bool:
    m, n = len(s1), len(s2)
    if m + n != len(s3):
        return False
    row = [False] * (n + 1)                 # row[j] = dp[i][j]
    for i in range(m + 1):
        for j in range(n + 1):
            if i == 0 and j == 0:
                row[j] = True
                continue
            from_s1 = i > 0 and row[j] and s1[i - 1] == s3[i + j - 1]          # 舊 row[j] 是上方
            from_s2 = j > 0 and row[j - 1] and s2[j - 1] == s3[i + j - 1]      # row[j-1] 是同列左方
            row[j] = from_s1 or from_s2
    return row[n]


def interleave_split(s1: str, s2: str, s3: str) -> str | None:
    """回傳每個 s3 字元的來源（'1' 或 '2'），做不到時回傳 None。"""
    m, n = len(s1), len(s2)
    if m + n != len(s3):
        return None
    dp = [[False] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = True
    for i in range(m + 1):
        for j in range(n + 1):
            if i > 0 and dp[i - 1][j] and s1[i - 1] == s3[i + j - 1]:
                dp[i][j] = True
            if j > 0 and dp[i][j - 1] and s2[j - 1] == s3[i + j - 1]:
                dp[i][j] = True
    if not dp[m][n]:
        return None
    labels, i, j = [], m, n
    while i > 0 or j > 0:
        if i > 0 and dp[i - 1][j] and s1[i - 1] == s3[i + j - 1]:
            labels.append("1"); i -= 1
        else:
            labels.append("2"); j -= 1
    return "".join(reversed(labels))


def brute(s1, s2, s3):
    @cache
    def go(i, j):
        if i == len(s1) and j == len(s2):
            return True
        k = i + j
        return (i < len(s1) and s1[i] == s3[k] and go(i + 1, j)) or \
               (j < len(s2) and s2[j] == s3[k] and go(i, j + 1))
    return len(s1) + len(s2) == len(s3) and go(0, 0)


assert is_interleave("aabcc", "dbbca", "aadbbcbcac") is True
assert is_interleave("aabcc", "dbbca", "aadbbbaccc") is False
assert is_interleave("", "", "") is True
assert is_interleave("a", "b", "a") is False
assert is_interleave("ca", "cb", "cbca") is True            # 貪婪會失敗的例子
assert is_interleave("", "abc", "abc") is True
assert interleave_split("ca", "cb", "cbca") == "2211"
for _ in range(500):
    a = "".join(random.choice("ab") for _ in range(random.randint(0, 5)))
    b = "".join(random.choice("ab") for _ in range(random.randint(0, 5)))
    c = "".join(random.choice("ab") for _ in range(len(a) + len(b) + random.choice([0, 0, 1])))
    ok = is_interleave(a, b, c)
    assert ok == brute(a, b, c)
    lab = interleave_split(a, b, c)
    assert (lab is not None) == ok
    if lab:
        assert "".join(ch for ch, l in zip(c, lab) if l == "1") == a
        assert "".join(ch for ch, l in zip(c, lab) if l == "2") == b
print("all tests passed")
```

### 複雜度與邊界

時間 O(m · n)，每格兩次比較。一維版本空間 O(n)，符合題目的進階要求；若要 O(min(m, n))，可以交換 `s1` 與 `s2`（交錯關係對兩者是對稱的，`s3` 不用動）。邊界情況：長度不符時第一行就回傳 False，這同時避免了 `s3[i+j-1]` 越界；三個都是空字串時 `dp[0][0] = True`；其中一個為空時退化成 `s3` 是否等於另一個字串（只走第一列或第一行）。一維寫法中 `row[j]` 在覆寫前代表上方格，`row[j-1]` 已經是同一列左方，這和核心題 1 的覆寫邏輯完全相同；`i == 0` 那一列的 `row[j]` 初始為 False，所以 `from_s1` 不會誤判。

### Follow-up

> [!question]- F1. 為什麼不能用 two pointers 貪婪？有沒有貪婪可行的特殊情況？
> 貪婪失敗的根源是平手：`s1` 和 `s2` 的下一個字元都等於 `s3` 的下一個字元時，只拿一邊可能把後面的路堵死，例如 `s1 = "ca"`、`s2 = "cb"`、`s3 = "cbca"`。如果 `s1` 與 `s2` **沒有共同字元**，平手永遠不會發生，每個 `s3` 的字元只有一個可能的來源，two pointers O(m + n) 就夠了。一般情況下，平手處的選擇要到後面才知道對不對，而 (i, j) 已經完整描述「目前狀態」，所以把所有平手分支合併成 m · n 個狀態，就是 DP 比回溯快的原因。

> [!question]- F2. 如果要計算總共有幾種不同的交錯標記方式呢？
> 把布林的 `or` 換成加法：`cnt[i][j] = (s1[i-1] == s3[i+j-1] ? cnt[i-1][j] : 0) + (s2[j-1] == s3[i+j-1] ? cnt[i][j-1] : 0)`，`cnt[0][0] = 1`。每一條從 (0, 0) 到 (m, n) 的合法網格路徑，恰好對應一種「每個 `s3` 字元來自哪個字串」的標記（路徑的第 k 步是往下或往右，就決定了 `s3[k]` 的來源），反之亦然，所以路徑數就是標記數，不會重複計算。例如 `s1 = "a"`、`s2 = "a"`、`s3 = "aa"` 答案是 2。數量可能指數成長，通常要取模。時間 O(m · n)。

> [!question]- F3. 如果要求每個字串被切成的段數差不超過 1（2 個字串交替出現：s1 一段、s2 一段……）呢？
> 原題其實已經隱含這個性質：任何交錯方式把連續來自同一個字串的字元合併成一段後，兩邊的段一定是交替出現，段數差自然 ≤ 1，所以原題不受影響。如果改成「最多只能切成 k 段」，就要在狀態上加一維記錄目前用了幾段、最後一段來自哪個字串：`dp[i][j][last]` = 最少段數，轉移時換來源就段數加一。時間 O(m · n)，空間 O(m · n) 或壓成一列（每格存兩個值）。這種「在原本的網格狀態上多掛一個小維度」的手法，在 DP 題中非常常見。

> [!question]- F4. 如果是 k 個字串交錯組成 s3 呢？
> 狀態要記錄每個字串各用了多少，`dp[i1][i2]…[ik]`，`s3` 的位置是它們的和，所以 k 個索引都必須保留，狀態數是 ∏(len + 1)，對 k 呈指數成長。實作時用 `functools.cache` 搭配 tuple 狀態最直接。k = 3 時是 O(n1 · n2 · n3)。如果某些字串完全相同，可以把它們的索引排序後當作狀態（對稱性），減少重複狀態。面試中提出「狀態數是各長度加一的乘積」並說明 k 大時不可行，就足夠了。

> [!question]- F5. 如果 s3 是串流，字元一個一個到達，要隨時回答「目前為止是否還有可能是交錯」呢？
> 讀到 `s3` 的第 k 個字元時，可能的狀態只剩對角線 `i + j = k` 上的格子，所以只需要維護一個集合「目前可達的 i」（j = k − i 自動決定）。新字元到來時，從每個可達的 i 嘗試 i + 1（若 `s1[i]` 等於新字元）與 i 不變（若 `s2[k − i]` 等於新字元），得到新的集合。每個字元 O(min(m, n, k)) 時間，空間也是 O(min(m, n))。集合變空時就可以立即回報不可能。這等於把網格 DP 改成「沿著反對角線一層層推進」的 BFS，和第 15 章的分層 BFS 思路相同。

## 難題 1｜10. Regular Expression Matching｜Hard

### 題目

實作支援 `.` 與 `*` 的正規表示式匹配。`.` 匹配任意一個字元；`*` 匹配**它前面那個元素**零次或多次（例如 `a*` 可以是空字串、a、aa、…，`.*` 可以是任意字串）。匹配必須涵蓋**整個**輸入字串，不是部分匹配。輸入：字串 `s`（小寫字母）與 pattern `p`（小寫字母、`.`、`*`），題目保證每個 `*` 前面都有一個合法的字元或 `.`。限制：`1 <= len(s) <= 20`、`1 <= len(p) <= 20`。

- 範例 1：`s = "aa"`、`p = "a"`，回傳 `False`（只匹配到一個 a，不是整串）。
- 範例 2：`s = "aa"`、`p = "a*"`，回傳 `True`（a 重複兩次）。
- 範例 3：`s = "ab"`、`p = ".*"`，回傳 `True`。
- 範例 4：`s = "aab"`、`p = "c*a*b"`，回傳 `True`（c 出現 0 次，a 出現 2 次）。
- 範例 5（邊界）：`s = "mississippi"`、`p = "mis*is*p*."`，回傳 `False`。

### 提示

> [!tip]- 提示 1
> 先把 pattern 看成一串「單元」：普通字元、`.`、以及「字元加 `*`」。`*` 永遠和前一個字元綁在一起，不要單獨處理它。

> [!tip]- 提示 2
> 定義 `dp[i][j]` = `s[:i]` 能否被 `p[:j]` 完整匹配。`p[j-1]` 不是 `*` 時，只要最後一個字元能配上，就退回 `dp[i-1][j-1]`。`p[j-1]` 是 `*` 時，`x*` 這個單元有哪兩種選擇？

> [!tip]- 提示 3
> `x*` 用零次：直接丟掉這個單元，看 `dp[i][j-2]`。用至少一次：`s[i-1]` 必須能被 x 匹配，然後**吃掉 `s[i-1]` 但保留 `x*`**（它還可以再用），看 `dp[i-1][j]`。base case 中，空字串可以被 `a*b*` 這種 pattern 匹配，第 0 列要特別算。

### 詳解

**為什麼直覺做法不行**。直接的遞迴回溯是：遇到 `x*` 時，先嘗試讓它吃 0 個、1 個、2 個…字元，每種都遞迴下去。這在多個 `*` 相鄰時會指數爆炸：`s = "aaaaaaaaaaaaaaaaaaab"`、`p = "a*a*a*a*a*a*c"`，每個 `a*` 都可以分配任意多個 a，分配方式的數量是組合數級別，而且每種都要走到最後才發現 c 配不上。這就是許多正規表示式引擎遇到的 catastrophic backtracking。但仔細看，每一次遞迴呼叫的狀態都只是「s 還剩哪個後綴、p 還剩哪個後綴」，總共只有 (m + 1)(n + 1) 種，指數級的分支其實在重複走同一批狀態。

**突破點：讓 `*` 一次只做一個決定**。上面的遞迴對 `x*` 一次決定「吃幾個」，分支數是 O(m)。更好的拆法是讓它每次只決定「再吃一個，或者停止」：停止就是 `dp[i][j-2]`（整個 `x*` 單元消失）；再吃一個要求 `s[i-1]` 能被 x 匹配（x 是 `.` 或等於 `s[i-1]`），吃完之後 `x*` **仍然留著**，所以退回 `dp[i-1][j]` 而不是 `dp[i-1][j-2]`。這樣每格只有 O(1) 個轉移，總時間 O(m · n)。

完整轉移（`dp[i][j]` = `s[:i]` 是否被 `p[:j]` 完整匹配）：

- `p[j-1]` 是普通字元或 `.`：`dp[i][j] = i > 0 and match(s[i-1], p[j-1]) and dp[i-1][j-1]`。
- `p[j-1]` 是 `*`：`dp[i][j] = dp[i][j-2] or (i > 0 and match(s[i-1], p[j-2]) and dp[i-1][j])`。

**base case 與正確性**。`dp[0][0] = True`。`dp[i][0] = False`（i > 0，空 pattern 匹配不了非空字串）。第 0 列 `dp[0][j]` 不是全 False：空字串可以被 `a*`、`a*b*`、`.*c*` 匹配，所以 `p[j-1] == '*'` 時 `dp[0][j] = dp[0][j-2]`，這一點直接由上面的轉移在 i = 0 時得到（第二個分支因為 i = 0 而不成立）。正確性用歸納法：`s[:i]` 被 `p[:j]` 匹配時，看 p 的最後一個單元；若是單一字元，它必須匹配 `s` 的最後一個字元；若是 `x*`，它吃掉的字元數是 0（對應第一個分支）或 ≥ 1（它吃掉的最後一個字元是 `s[i-1]`，剩下的 `s[:i-1]` 仍由 `p[:j]` 匹配，因為 `x*` 少吃一個仍是 `x*`），兩種情況窮盡且互相獨立地被轉移涵蓋。

```text
s = "aab"（列），p = "c*a*b"（行）
             j:  0   1   2   3   4   5
                 ""  c   *   a   *   b
i=0  ""          T   F   T   F   T   F     ← c* 與 c*a* 都能匹配空字串
i=1  a           F   F   F   T   T   F
i=2  aa          F   F   F   F   T   F
i=3  aab         F   F   F   F   F   T     ← 答案

關鍵格子：
dp[0][2]  p[1]='*'：零次 → dp[0][0] = T
dp[0][4]  p[3]='*'：零次 → dp[0][2] = T
dp[1][3]  p[2]='a' 配 s[0]='a' → dp[0][2] = T
dp[1][4]  p[3]='*'：零次 dp[1][2] = F；再吃一個：s[0]='a' 配 'a'，看 dp[0][4] = T → T
dp[2][4]  p[3]='*'：零次 dp[2][2] = F；再吃一個：s[1]='a' 配 'a'，看 dp[1][4] = T → T
dp[3][4]  p[3]='*'：零次 dp[3][2] = F；再吃一個：s[2]='b' 不配 'a' → F
dp[3][5]  p[4]='b' 配 s[2]='b' → dp[2][4] = T → T

注意 dp[2][4] 往上看的是 dp[1][4]（同一行）：a* 吃掉第二個 a 之後還留著，
這就是「再吃一個」退回 (i-1, j) 而不是 (i-1, j-2) 的原因。
```

### 解法

```python
from functools import cache
import random
import re


def is_match(s: str, p: str) -> bool:
    m, n = len(s), len(p)
    dp = [[False] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = True
    for i in range(m + 1):
        for j in range(1, n + 1):
            if p[j - 1] == "*":
                dp[i][j] = dp[i][j - 2]                               # x* 用零次
                if i > 0 and p[j - 2] in (s[i - 1], "."):
                    dp[i][j] = dp[i][j] or dp[i - 1][j]               # 再吃一個，x* 保留
            elif i > 0 and p[j - 1] in (s[i - 1], "."):
                dp[i][j] = dp[i - 1][j - 1]
    return dp[m][n]


def is_match_memo(s: str, p: str) -> bool:
    @cache
    def go(i: int, j: int) -> bool:              # s[i:] 是否被 p[j:] 匹配
        if j == len(p):
            return i == len(s)
        first = i < len(s) and p[j] in (s[i], ".")
        if j + 1 < len(p) and p[j + 1] == "*":
            return go(i, j + 2) or (first and go(i + 1, j))
        return first and go(i + 1, j + 1)
    return go(0, 0)


def random_pattern() -> str:
    out = []
    for _ in range(random.randint(0, 4)):
        out.append(random.choice("ab."))
        if random.random() < 0.5:
            out.append("*")
    return "".join(out)


assert is_match("aa", "a") is False
assert is_match("aa", "a*") is True
assert is_match("ab", ".*") is True
assert is_match("aab", "c*a*b") is True
assert is_match("mississippi", "mis*is*p*.") is False
assert is_match("", "a*b*") is True                    # 空字串
assert is_match("ab", ".*c") is False
assert is_match("a" * 19 + "b", "a*a*a*a*a*a*c") is False
for _ in range(2000):
    s = "".join(random.choice("ab") for _ in range(random.randint(0, 6)))
    p = random_pattern()
    expect = re.fullmatch(p, s) is not None
    assert is_match(s, p) == is_match_memo(s, p) == expect
print("all tests passed")
```

### 複雜度與邊界

時間 O(m · n)，每格 O(1)；空間 O(m · n)，可以壓成兩列（第 i 列只依賴第 i − 1 列的 j − 1、j 與同一列的 j − 2）。top-down 版本同樣是 O(m · n)，但只會走到可達的狀態，pattern 中沒有 `*` 時只走一條對角線，O(min(m, n))。邊界情況：`s` 為空時答案取決於 p 是否全由 `x*` 單元組成；`p` 以 `.*` 結尾時可吃掉任意尾巴；`*` 的前一個字元是 `.` 時，「再吃一個」對任何字元都成立。實作上最常見的錯誤是把 `*` 的再吃一個寫成 `dp[i-1][j-2]`，這會讓 `x*` 最多只用一次（等於把 `*` 當成 `?`），`"aa"` 對 `"a*"` 會錯判成 False。

### Follow-up

> [!question]- F1. 如果還要支援 `+`（一次或多次）與 `?`（零次或一次）呢？
> 最乾淨的做法是先把 pattern 轉成單元列表 `(字元, 最少次數, 最多次數是否無限)`，`x` 是 (x, 1, 1)、`x*` 是 (x, 0, ∞)、`x+` 是 (x, 1, ∞)、`x?` 是 (x, 0, 1)，然後 `dp[i][k]` 改成 `s[:i]` 是否被前 k 個單元匹配。轉移：`x?` 是 `dp[i][k-1] or (match and dp[i-1][k-1])`；`x+` 是 `match and (dp[i-1][k-1] or dp[i-1][k])`（吃掉的最後一個是第一次用，或已經用過至少一次後再吃一個）。也可以把 `x+` 改寫成 `xx*` 直接套原本的程式。時間仍是 O(m · 單元數)。

> [!question]- F2. top-down 和 bottom-up 該選哪一個？可以壓縮空間嗎？
> 兩者都是 O(m · n)。top-down 從 (0, 0) 出發只拜訪可達狀態，pattern 中 `*` 很少時快很多，而且程式最接近思路，是面試時最穩的寫法；遞迴深度最多 m + n（這題 ≤ 40），沒有堆疊問題。bottom-up 的優點是可以壓空間：第 i 列只依賴第 i − 1 列（`dp[i-1][j-1]` 與 `dp[i-1][j]`）和同一列左邊的 `dp[i][j-2]`，保留兩列就夠，O(n) 空間。如果 m 很大而 n 很小（長文字對短 pattern），兩列 O(n) 的 bottom-up 明顯較好。

> [!question]- F3. 真正的 regex 引擎是怎麼做的？為什麼 Python 的 `re` 有時會很慢？
> Python 的 `re`、PCRE、Java 的 regex 都是回溯式引擎，因為它們要支援 backreference 等功能，最差情況是指數時間，例如 `(a+)+b` 對一長串 a 就會爆炸。另一派是 Thompson 的 NFA 模擬（RE2、Go 的 regexp、grep）：把 pattern 編成 NFA，掃 s 時維護「目前可能在哪些 NFA 狀態」的集合，每讀一個字元更新一次，總時間 O(m · n)、保證線性於輸入長度。本題的 DP 其實就是這個模擬：固定 i 時，所有 `dp[i][j] = True` 的 j 正是讀完 `s[:i]` 後的 NFA 狀態集合。

> [!question]- F4. 如果 s 非常長（10⁶）而 p 很短，或 s 是串流呢？
> 用 F3 的觀點，只要保留一列 `cur[j]`（j = 0…n），每讀一個字元就由舊的一列算出新的一列：先算普通字元與「再吃一個」（依賴舊列），再由左到右處理「用零次」（依賴新列的 j − 2）。每個字元 O(n)、總共 O(m · n)，記憶體只有 O(n)，可以邊讀邊算。如果要回答「目前讀到的前綴是否匹配」，每次看 `cur[n]` 即可。若同一個 pattern 要比對非常多字串，可以把 NFA 轉成 DFA（subset construction），之後每個字元 O(1)，代價是 DFA 狀態數最差為 2ⁿ。

> [!question]- F5. 如果要回傳每個 `x*` 實際吃掉了幾個字元呢？
> 保留完整的 dp 表，從 (m, n) 回溯：`p[j-1]` 是普通字元就走 (i − 1, j − 1)；是 `*` 時，若 `dp[i][j-2]` 為 True 就代表這個單元在這裡停止，走 (i, j − 2)，否則必然是「再吃一個」，該單元的計數加一並走 (i − 1, j)。不同的回溯優先順序會得到不同的分配，例如先試「再吃一個」會讓前面的 `*` 盡量少吃、後面的盡量多吃（或相反），這就是 regex 中 greedy 與 lazy 量詞的差別。時間 O(m + n) 回溯加上 O(m · n) 建表。

### 心得

關鍵突破是讓 `x*` 每次只做一個決定：「整個單元消失」退回 (i, j − 2)，「再吃一個並保留自己」退回 (i − 1, j)，於是每格 O(1) 轉移、總共 O(m · n)。和本章其他題的關係：它是雙序列 DP（模板 B）的布林版本，和核心題 5 一樣只問「走不走得到」；和難題 2 共用同一張表，差別只在 `*` 的語意。面試時先把 pattern 切成單元、說清楚狀態定義，接著把 `*` 的兩條轉移與第 0 列的初始化（`a*b*` 能匹配空字串）講出來，再用 "aab" 對 "c*a*b" 畫幾格驗證；寫 top-down 版本通常最快也最不容易錯，被追問時再說明 bottom-up 可以壓成兩列。

## 難題 2｜44. Wildcard Matching｜Hard

### 題目

實作萬用字元匹配：pattern 中的 `?` 匹配任意**一個**字元，`*` 匹配任意字串（包含空字串），其他字元只匹配自己。匹配必須涵蓋整個輸入字串。輸入：字串 `s`（小寫字母）與 pattern `p`（小寫字母、`?`、`*`）。限制：`0 <= len(s), len(p) <= 2000`。

- 範例 1：`s = "aa"`、`p = "a"`，回傳 `False`。
- 範例 2：`s = "aa"`、`p = "*"`，回傳 `True`。
- 範例 3：`s = "cb"`、`p = "?a"`，回傳 `False`（`?` 配 c，但 a 配不上 b）。
- 範例 4：`s = "adceb"`、`p = "*a*b"`，回傳 `True`（第一個 `*` 配空字串，第二個 `*` 配 "dce"）。
- 範例 5：`s = "acdcb"`、`p = "a*c?b"`，回傳 `False`。
- 範例 6（邊界）：`s = ""`、`p = "***"`，回傳 `True`；`s = ""`、`p = "?"`，回傳 `False`。

### 提示

> [!tip]- 提示 1
> 和難題 1 的差別在於這裡的 `*` 是獨立的，不綁定前一個字元，可以吞下任何東西。狀態仍然是兩個前綴。

> [!tip]- 提示 2
> `dp[i][j]` = `s[:i]` 能否被 `p[:j]` 匹配。`p[j-1]` 是 `*` 時，它可以配空字串（看 `dp[i][j-1]`），或吃掉 `s[i-1]` 之後繼續保留（看 `dp[i-1][j]`）。

> [!tip]- 提示 3
> DP 已經是 O(m · n)。想要 O(1) 空間：用兩個指標掃描，遇到 `*` 時記下它的位置與當時 s 的位置；之後配不上時，回到**最近的那個** `*`，讓它多吃一個字元再試。為什麼只需要記住最近的一個？

### 詳解

**為什麼直覺做法不行**。直接遞迴時，每個 `*` 要嘗試吃 0、1、2、… 個字元，多個 `*` 時分配方式是組合數級別。例如 `s = "aaaa…a"`（2000 個）、`p = "*a*a*a*…*b"`，回溯會嘗試大量分配，最後才發現結尾的 b 配不上。和難題 1 一樣，所有遞迴狀態都只是一對 (i, j)，所以可以用 DP 把指數降成 O(m · n)。

**DP 轉移**。`dp[i][j]` = `s[:i]` 是否被 `p[:j]` 完整匹配：

- `p[j-1]` 是 `*`：`dp[i][j] = dp[i][j-1]`（`*` 配空字串）`or (i > 0 and dp[i-1][j])`（`*` 吃掉 `s[i-1]`，仍保留，可以繼續吃）。
- `p[j-1]` 是 `?` 或等於 `s[i-1]`：`dp[i][j] = dp[i-1][j-1]`。
- 其他：False。

base case：`dp[0][0] = True`；`dp[0][j]` 只有在 `p[:j]` 全是 `*` 時為 True；`dp[i][0] = False`（i > 0）。和難題 1 相比，`*` 的「用零次」退回 j − 1（只丟掉 `*` 自己）而不是 j − 2，「再吃一個」的條件不需要檢查字元（任何字元都能吃）。

**突破點：O(1) 空間的貪婪**。把 p 依 `*` 切開成段：`P0 * P1 * … * Pk`。完整匹配等價於：P0 是 s 的前綴、Pk 是 s 的後綴、中間的 P1…P(k−1) 依序、互不重疊地出現在剩下的部分（`?` 當萬用字元）。對中間每一段，**選最左邊的出現位置永遠不會更差**，因為它留給後面各段的空間最多；這是交換論證。所以掃描時只要記住「最近一個 `*` 的位置」與「它目前吃到 s 的哪裡」，配不上時讓這個 `*` 多吃一個字元，等於把目前這一段的嘗試起點右移一格，也就是在找這一段最左的出現位置。一旦越過下一個 `*`，前面那一段已經固定在最左的位置，就再也不需要回頭，所以只需要一個 `*` 的記錄。

```text
DP 表：s = "adceb"（列），p = "*a*b"（行）
           ""  *   a   *   b
      ""   T   T   F   F   F
      a    F   T   T   T   F
      ad   F   T   F   T   F
      adc  F   T   F   T   F
      adce F   T   F   T   F
      adceb F  T   F   T   T   ← 答案
第 1 行（第一個 *）整行 T：它可以吞掉任意前綴
dp[1][2]：'a' 配 'a'，看 dp[0][1] = T
dp[2][3]：*，用零次 dp[2][2] = F；再吃一個 dp[1][3] = T → T
dp[5][4]：'b' 配 'b'，看 dp[4][3] = T

貪婪雙指標：i 指 s，j 指 p，star / mark 記住最近的 * 與它開始吃的位置
步驟  i  j  s[i] p[j]  動作
 1    0  0   a    *    記 star=0、mark=0，j → 1（先讓 * 配空字串）
 2    0  1   a    a    相同，i → 1、j → 2
 3    1  2   d    *    記 star=2、mark=1，j → 3
 4    1  3   d    b    配不上 → 回到 star：mark=2，i=2，j=3（* 多吃 d）
 5    2  3   c    b    配不上 → mark=3，i=3（* 多吃 c）
 6    3  3   e    b    配不上 → mark=4，i=4（* 多吃 e）
 7    4  3   b    b    相同，i → 5、j → 4
結束  i 走完 s，j = 4 = len(p) → True
```

### 解法

```python
import fnmatch
import random


def is_match(s: str, p: str) -> bool:
    m, n = len(s), len(p)
    row = [False] * (n + 1)
    row[0] = True
    for j in range(1, n + 1):
        row[j] = row[j - 1] and p[j - 1] == "*"     # 空字串只能被全是 * 的 pattern 匹配
    for i in range(1, m + 1):
        prev = row[0]                               # dp[i-1][0]
        row[0] = False
        for j in range(1, n + 1):
            saved = row[j]                          # dp[i-1][j]
            if p[j - 1] == "*":
                row[j] = row[j - 1] or saved        # 配空字串 or 吃掉 s[i-1]
            elif p[j - 1] == "?" or p[j - 1] == s[i - 1]:
                row[j] = prev
            else:
                row[j] = False
            prev = saved
    return row[n]


def is_match_greedy(s: str, p: str) -> bool:
    i = j = 0
    star, mark = -1, 0
    while i < len(s):
        if j < len(p) and (p[j] == "?" or p[j] == s[i]):
            i += 1
            j += 1
        elif j < len(p) and p[j] == "*":
            star, mark = j, i                       # * 先配空字串
            j += 1
        elif star != -1:
            mark += 1                               # 讓最近的 * 多吃一個字元
            i, j = mark, star + 1
        else:
            return False
    while j < len(p) and p[j] == "*":
        j += 1
    return j == len(p)


assert is_match("aa", "a") is False
assert is_match("aa", "*") is True
assert is_match("cb", "?a") is False
assert is_match("adceb", "*a*b") is True
assert is_match("acdcb", "a*c?b") is False
assert is_match("", "***") is True
assert is_match("", "?") is False
assert is_match("", "") is True
for _ in range(3000):
    s = "".join(random.choice("ab") for _ in range(random.randint(0, 7)))
    p = "".join(random.choice("ab?*") for _ in range(random.randint(0, 6)))
    expect = fnmatch.fnmatchcase(s, p)              # 只用 a、b、?、* 時語意和本題相同
    assert is_match(s, p) == is_match_greedy(s, p) == expect
print("all tests passed")
```

### 複雜度與邊界

DP 時間 O(m · n)，長度 2000 時是 4 × 10⁶ 格，空間一維 O(n)。貪婪版本空間 O(1)，時間最差仍是 O(m · n)：例如 `s = "aaaa…a"`、`p = "*aaa…ab"`，每次讓 `*` 多吃一個後都要重新比對整段 "aaa…a" 才在 b 失敗；但在實際輸入上通常接近線性。邊界情況：s 為空時只有全 `*` 的 pattern 能匹配；p 為空時只有 s 為空能匹配；連續多個 `*` 等價於一個（可以先合併，減少 DP 欄數）；結尾的 `*` 在主迴圈結束後統一跳過。貪婪版本中「遇到 `*` 時先配空字串」的順序很重要，它讓每一段都從最左的位置開始嘗試。

### Follow-up

> [!question]- F1. 為什麼 44 題的 `*` 只要記住最近的一個就能貪婪，難題 1（10 題）卻不行？
> 44 題的 `*` 可以吞下**任何**字元，所以後面的 `*` 能吸收前面那段「本來可以多吃」的字元，前面的段固定在最左的出現位置永遠不會吃虧。10 題的 `x*` 只能重複特定字元 x，不同的 `*` 吸收能力不同：例如 `p = "a*b*a*"` 中，把 a 分給第一個還是第三個 `a*` 取決於中間有沒有 b，後面的 `*` 無法彌補前面的選擇，「段」的概念也不存在（`x*` 不是分隔符號，而是有限制的單元）。所以 10 題只能用 DP 或 NFA 模擬，沒有 O(1) 空間的貪婪。

> [!question]- F2. 貪婪最差是 O(m · n)，能不能做得更快？
> 先依 `*` 把 p 切成段。若 p 中沒有 `?`，每一段都是普通字串：P0 必須是前綴、Pk 必須是後綴，中間每一段用 KMP（第 25 章）在剩下的 s 中找**最左**出現位置，找到後從它的結尾繼續找下一段。每段的搜尋從上一段結尾開始，s 的每個字元在每次 KMP 中最多被看常數次，總時間 O(m + n)。有 `?` 時，KMP 的失配函數不再適用（`?` 讓「相等」不具遞移性），可以用 FFT 做帶萬用字元的字串匹配，O(m log m)，但面試中通常只需要說出 O(m · n) 的 DP 或貪婪，再點出無 `?` 時可以用 KMP 優化。

> [!question]- F3. 如果規定 `*` 至少要匹配一個字元呢？
> 把每個 `*` 改寫成 `?*` 即可：`?` 先保證吃掉一個字元，後面的 `*` 再吃任意多個。改寫後 pattern 長度最多變兩倍，直接用原本的 DP 或貪婪，複雜度不變。如果直接改 DP，`*` 的轉移變成 `dp[i][j] = i > 0 and (dp[i-1][j-1] or dp[i-1][j])`：吃掉的最後一個字元 `s[i-1]` 是這個 `*` 吃的第一個字元，或者它已經吃過至少一個。第 0 列也要改：空字串不能被任何含 `*` 的 pattern 匹配。

> [!question]- F4. 如果要找出 s 中有多少個子字串能被 p 匹配呢？
> 對每個起點各跑一次布林 DP 是 O(m² · n)。直接把布林換成計數是錯的：同一個子字串可能有好幾種「各個 `*` 吃幾個」的分配，`cnt[i][j-1] + cnt[i-1][j]` 會把同一個 (起點, 終點) 數好幾次。正確的單次掃描做法是讓每一格存「起點的集合」：`start[i][j]` = 所有讓 `s[st:i]` 被 `p[:j]` 匹配的起點 st 組成的 bitset，`start[i][0]` 只含 i 自己，轉移把布林的 `or` 換成 bitset 的聯集（`*` 取 `start[i][j-1] | start[i-1][j]`，`?` 與字元取 `start[i-1][j-1]`）。答案是 Σᵢ popcount(`start[i][n]`)，要排除空子字串時扣掉 st = i 的情況。用 Python 的整數當 bitset，時間 O(m · n · m / 64)，比逐一起點快一個字長的常數，也不會重複計數。

> [!question]- F5. 如果要回傳每個 `*` 實際匹配到的子字串呢？
> 貪婪版本本身就能給出一組分配：每個 `*` 匹配的內容是「它最後一次的 `mark`」到「下一段開始配對的位置」之間的字元，最後一個 `*` 則延伸到最後一段之前。因為每一段都放在最左的位置，這組分配的特性是**前面的 `*` 盡量少吃**（類似 regex 的 lazy 量詞）。如果要**前面的 `*` 盡量多吃**，保留 DP 表從 (m, n) 回溯：遇到 `*` 時只要 `dp[i][j-1]` 為 True 就優先選「停止」(i, j − 1)，讓後面的 `*` 盡量少吃，前面的就會吃得多；兩種優先順序對調就得到相反的分配。建表 O(m · n)、回溯 O(m + n)。

### 心得

關鍵突破是把「`*` 吃幾個字元」拆成「每次只決定再吃一個或停止」，讓每格只有兩條轉移；進一步看出 `*` 是段與段之間的分隔，中間各段取最左出現位置永遠最好，於是只需要記住最近一個 `*`，得到 O(1) 空間的貪婪。它和難題 1 的 DP 表幾乎一樣，差別只在 `*` 的「零次」退回 j − 1 還是 j − 2、「再吃一個」要不要檢查字元，面試時把兩題並排比較，能清楚展示你理解每一條轉移的意義。建議先寫 DP（保證正確、容易解釋），再主動提出貪婪做為空間優化，並說明它最差仍是 O(m · n)。

## 難題 3｜115. Distinct Subsequences｜Hard

### 題目

給兩個字串 `s` 與 `t`，回傳 `s` 有多少個子序列等於 `t`。兩個子序列只要選用的**索引集合**不同就算不同，即使字元內容一樣。題目保證答案在 32 位元有號整數範圍內。限制：`1 <= len(s), len(t) <= 1000`，由英文字母組成。

- 範例 1：`s = "rabbbit"`、`t = "rabbit"`，回傳 `3`：s 中有三個 b，刪掉其中任何一個都得到 "rabbit"。
- 範例 2：`s = "babgbag"`、`t = "bag"`，回傳 `5`。
- 範例 3（邊界）：`s = "abc"`、`t = "abcd"`，回傳 `0`（t 比 s 長）。
- 範例 4（邊界）：`t` 為空字串時答案是 1（選空集合）；這是 DP 的 base case，雖然題目限制 t 非空。

### 提示

> [!tip]- 提示 1
> 這是核心題 3（LCS）的計數版本。狀態仍是兩個前綴：`dp[i][j]` = `s[:i]` 中有幾個子序列等於 `t[:j]`。

> [!tip]- 提示 2
> 看 `s` 的最後一個字元 `s[i-1]`：任何一個符合的子序列，要嘛沒有用到它，要嘛用它來配 `t` 的最後一個字元 `t[j-1]`。這兩類互斥且窮盡。

> [!tip]- 提示 3
> `dp[i][j] = dp[i-1][j] + (s[i-1] == t[j-1] ? dp[i-1][j-1] : 0)`，`dp[i][0] = 1`。壓成一列時沒有「左」的依賴，所以 j 要由大到小更新，否則同一個字元會被用兩次。

### 詳解

**為什麼直覺做法不行**。暴力列舉 s 的 C(m, n) 個長度為 n 的子序列，m = 1000、n = 500 時是天文數字。另一個直覺是「先算 LCS 再想辦法數」，但 LCS 是在找最長的共同部分，這題要的是 t **完整**出現的次數，兩者的轉移不同：LCS 在字元不同時取 max，這題在字元相同時要**加總**兩種情況。計數題最重要的是確保**每個物件恰好被數一次**，所以轉移必須是一個「互斥且窮盡」的分類。

**突破點：用 s 的最後一個字元分類**。所有「`s[:i]` 中等於 `t[:j]` 的子序列」依照是否使用 `s[i-1]` 分成兩類。不使用：它們就是 `s[:i-1]` 中等於 `t[:j]` 的子序列，共 `dp[i-1][j]` 個。使用：`s[i-1]` 是子序列的最後一個字元，必須對到 `t[j-1]`，所以要求 `s[i-1] == t[j-1]`，剩下的部分是 `s[:i-1]` 中等於 `t[:j-1]` 的子序列，共 `dp[i-1][j-1]` 個。兩類的索引集合一個含 i − 1、一個不含，不可能重複；任何子序列都屬於其中一類，不會遺漏。這就是正確性的完整理由。

注意分類是以 **s 的字元**為主體，而不是 t 的字元：若改成「t 的最後一個字元配到 s 的哪個位置」，就要對每個可能位置求和，轉移變成 O(m)，總時間 O(m² · n)。以 s 的最後一個字元「用或不用」分類，轉移只要 O(1)。

**base case**。`dp[i][0] = 1`：空的 t 在任何前綴中都恰好出現一次（空子序列）。`dp[0][j] = 0`（j > 0）：空的 s 沒有非空子序列。還可以剪枝：`i < j` 時 `dp[i][j]` 必為 0。

```text
s = "babgbag"（列），t = "bag"（行）
dp[i][j] = ↑（不用 s[i-1]）+ ↖（用 s[i-1] 配 t[j-1]，字元相同時才有）

              ""   b    a    g
     ""        1   0    0    0
  1  b         1   1    0    0      b 配 t[0]：↑0 + ↖1 = 1
  2  a         1   1    1    0      a 配 t[1]：↑0 + ↖1 = 1
  3  b         1   2    1    0      b：↑1 + ↖1 = 2（第 1 或第 3 個 b）
  4  g         1   2    1    1      g 配 t[2]：↑0 + ↖1 = 1
  5  b         1   3    1    1      b：↑2 + ↖1 = 3
  6  a         1   3    4    1      a：↑1 + ↖3 = 4（前面 3 個 b 任選一個接這個 a）
  7  g         1   3    4    5      g：↑1 + ↖4 = 5 ← 答案

5 種選法（索引從 0 起）：
  b a g = (0,1,3) (0,1,6) (0,5,6) (2,5,6) (4,5,6)
```

表中 `dp[6][2] = 4` 的意義是「`"babgba"` 中有 4 個子序列等於 "ba"」：舊的 1 個（索引 0、1）加上「用最後這個 a」的 3 個（它前面的 3 個 b 任選一個）。每一格都可以這樣用一句話解讀，是檢查轉移是否正確最快的方法。

### 解法

```python
from collections import defaultdict
from itertools import combinations
import random


def num_distinct(s: str, t: str) -> int:
    n = len(t)
    row = [1] + [0] * n                       # row[j] = dp[i][j]；dp[0][0] = 1
    for ch in s:
        for j in range(n, 0, -1):             # 由大到小：row[j-1] 仍是上一列的值
            if t[j - 1] == ch:
                row[j] += row[j - 1]
    return row[n]


def num_distinct_2d(s: str, t: str) -> int:
    m, n = len(s), len(t)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = 1
    for i in range(1, m + 1):
        for j in range(1, min(i, n) + 1):     # i < j 時必為 0，不用算
            dp[i][j] = dp[i - 1][j]
            if s[i - 1] == t[j - 1]:
                dp[i][j] += dp[i - 1][j - 1]
    return dp[m][n]


def num_distinct_positions(s: str, t: str) -> int:
    """只更新 t 中等於目前字元的位置：時間 O(m + 配對數)。"""
    pos = defaultdict(list)
    for j in range(len(t), 0, -1):            # 預先存好由大到小的位置
        pos[t[j - 1]].append(j)
    row = [1] + [0] * len(t)
    for ch in s:
        for j in pos[ch]:
            row[j] += row[j - 1]
    return row[len(t)]


def brute(s, t):
    return sum("".join(s[i] for i in idx) == t for idx in combinations(range(len(s)), len(t)))


assert num_distinct("rabbbit", "rabbit") == 3
assert num_distinct("babgbag", "bag") == 5
assert num_distinct("abc", "abcd") == 0
assert num_distinct("abc", "") == 1
assert num_distinct("aaaa", "aa") == 6                # C(4, 2)
assert num_distinct_2d("babgbag", "bag") == 5
for _ in range(300):
    s = "".join(random.choice("ab") for _ in range(random.randint(0, 9)))
    t = "".join(random.choice("ab") for _ in range(random.randint(0, 4)))
    assert num_distinct(s, t) == num_distinct_2d(s, t) == num_distinct_positions(s, t) == brute(s, t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(m · n)，空間一維 O(n)。位置表版本只在 `t[j-1] == s[i-1]` 的格子做加法，時間 O(m + n + 配對數)，字母分布很散（例如 t 的字元都不同）時接近 O(m + n)，最差（全部同一個字母）仍是 O(m · n)。邊界情況：t 比 s 長時答案 0（二維版本用 `min(i, n)` 剪枝，一維版本自然得到 0）；t 為空時答案 1；s 與 t 相同時答案 1。題目保證**最終答案**在 32 位元內，但中間的 `dp[i][j]` 可能超過，例如很多格子對最終答案沒有貢獻卻很大；在 Java／C++ 中要用 64 位元或無號整數，或依題意取模，Python 沒有這個問題。

### Follow-up

> [!question]- F1. 為什麼壓成一列時 j 必須由大到小？正著跑會發生什麼事？
> 轉移 `dp[i][j] = dp[i-1][j] + dp[i-1][j-1]` 只依賴上一列，沒有同列左方的依賴。由大到小更新時，更新 `row[j]` 用到的 `row[j-1]` 還沒被這一列改過，仍是 `dp[i-1][j-1]`。若由小到大，`row[j-1]` 已經是 `dp[i][j-1]`，等於允許 `s[i-1]` 同時配 `t[j-2]` 和 `t[j-1]`，同一個字元用了兩次。例如 `s = "aa"`、`t = "aa"`：正確答案 1；正著跑時第一個 a 就讓 `row = [1, 1, 1]`（第一個 a 被當成兩個 a），第二個 a 後變成 `[1, 2, 3]`，答案 3。這和第 23 章 0/1 背包「容量由大到小」是同一個道理。

> [!question]- F2. 如果答案很大，要對 10⁹ + 7 取模呢？
> 每次加法後取模即可：`row[j] = (row[j] + row[j-1]) % MOD`，因為轉移只有加法，模運算可以在每一步進行而不影響結果。這也順帶解決了 Java／C++ 中「中間值溢位、但最終答案保證在範圍內」的陷阱。需要注意的是，取模後就不能再用「值是否為 0」做剪枝或判斷可行性（一個很大的數取模後可能剛好是 0），如果還需要「是否存在」，要另外維護一張布林表或記錄 min(真值, 上限)。

> [!question]- F3. 如果要計算 s 本身有多少個**內容不同**的非空子序列（940. Distinct Subsequences II）呢？
> 這題以內容區分，不是以索引區分，所以要避免重複。令 `total` 為目前為止不同子序列的數量（含空的），處理字元 c 時，每個舊的子序列後面接上 c 都得到一個新的子序列，數量翻倍；但其中「以 c 結尾」的那些，在上一次遇到 c 時已經產生過了，要扣掉：`total_new = 2 · total − last[c]`，其中 `last[c]` 是上一次處理 c 之前的 `total`（代表那時接上 c 產生的那批）。最後答案是 `total − 1`（去掉空子序列）。時間 O(m)，空間 O(字母表)。例如 "aba"：1 → 2（a）→ 4（b）→ 2·4 − 1 = 7，答案 6：a、b、ab、aa、ba、aba。

> [!question]- F4. 如果要列出所有符合的子序列的索引組合呢？
> 數量可能指數級，所以只能做到「輸出敏感」的時間。先用**後綴版本**的表 `suf[i][j]` = `s[i:]` 中有幾個子序列等於 `t[j:]`，然後 DFS：在狀態 (i, j) 時，對每個 `k ≥ i` 且 `s[k] == t[j]` 且 `suf[k+1][j+1] > 0` 的 k，選 k 並遞迴到 (k + 1, j + 1)。因為只走 `suf > 0` 的分支，每個遞迴都一定會產出至少一個答案，不會白走；用「下一次出現位置」表找 k，總時間 O(m · n + 答案數 × n)。這是「計數 DP 當作導航」的通用手法，和核心題 1 F4 的「第 k 小路徑」同源。

> [!question]- F5. 如果 t 很短而固定（例如數 s 中有幾個子序列等於 "abc"），s 長度 10⁶ 呢？
> 這是同一個 DP，只是 n = 3：維護 `cnt = [1, 0, 0, 0]`，讀到字元 c 時，對 t 中所有等於 c 的位置 j（由大到小）做 `cnt[j] += cnt[j-1]`，O(m · n) = O(3m)。這個寫法常被稱為「按前綴計數」：`cnt[1]` 是目前看過幾個 a、`cnt[2]` 是幾個 ab、`cnt[3]` 是幾個 abc。t 中有重複字元時（例如 "aab"）由大到小的順序就變得必要。若是在串流中支援「目前為止的答案」，每讀一個字元 O(n) 更新，隨時回傳 `cnt[n]`。

### 心得

關鍵突破是用「s 的最後一個字元用或不用」做互斥且窮盡的分類，讓計數不重不漏、轉移只有 O(1)；這也是所有計數型 DP 的核心檢查：每個物件是否恰好落在一個分支。它和核心題 3 的 LCS 共用同一張表的形狀，差別只在 max 換成加法、而且只有在字元相同時才有對角項。面試時建議先在小例子上把表畫出來，用一句話解讀幾個格子（例如「`dp[6][2] = 4` 是 "babgba" 中 "ba" 的個數」），再寫一維版本並主動說明 j 為什麼要倒著跑，這是面試官最常追問的地方。

## 難題 4｜174. Dungeon Game｜Hard

### 題目

騎士從 m × n 地牢的左上角出發，要走到右下角救公主，每一步只能往右或往下。每一格有一個整數：負數代表受到傷害（扣血），正數代表補血，0 代表空房間；起點與終點的格子也會生效。騎士的血量在任何時刻（包括剛進入任何一格之後）都必須 ≥ 1，降到 0 或以下就死亡。請回傳騎士**出發前**所需的最低初始血量。限制：`1 <= m, n <= 200`，`-1000 <= dungeon[i][j] <= 1000`。

- 範例 1：`dungeon = [[-2, -3, 3], [-5, -10, 1], [10, 30, -5]]`，回傳 `7`。走「右、右、下、下」：血量依序是 7 → 5 → 2 → 5 → 6 → 1，全程 ≥ 1。
- 範例 2（邊界）：`dungeon = [[0]]`，回傳 `1`（血量至少要是 1）。
- 範例 3（邊界）：`dungeon = [[100]]`，回傳 `1`，補血不會讓需求低於 1。
- 範例 4（邊界）：`dungeon = [[-5]]`，回傳 `6`。

### 提示

> [!tip]- 提示 1
> 試試從起點往終點做 DP，每格記「到這裡為止需要的最低初始血量」。找一個例子，看看在兩條路徑匯合的格子上，你能不能只保留其中一條。

> [!tip]- 提示 2
> 正向時每條路徑有兩個量：目前血量、途中需要的最低初始血量，兩者會互相牽制，無法只用一個數字比較。如果從終點往回看呢？

> [!tip]- 提示 3
> 定義 `need[i][j]` = 剛進入 (i, j) **之前**至少要有多少血，才能活著走到終點。則 `need[i][j] = max(1, min(need[i+1][j], need[i][j+1]) − dungeon[i][j])`，從右下往左上填，答案是 `need[0][0]`。

### 詳解

**為什麼正向 DP 不行**。最自然的想法是模板 A：從左上往右下，每格記錄某個「最佳」數值。但每條部分路徑其實有兩個重要的量：`low` = 途中前綴和的最低點（決定需要多少初始血），`cur` = 目前的前綴和（決定之後還能承受多少傷害）。兩條路徑匯合時，可能一條 `low` 較好、另一條 `cur` 較好，選哪一條取決於**後面**的格子，而 DP 填到這裡時還不知道後面。下面的例子中，在格子 (2, 1) 匯合的兩條路徑，正向 DP 若保留「途中最低點較高」的那條，最後會得到 8，但正確答案是 6：

```text
地牢               在 (2,1) 匯合的兩條路徑（前綴和）
 0  -3   1         A：(0,0)→(0,1)→(1,1)→(2,1)  前綴和 0, -3, -3, -2   low = -3，cur = -2
-4   0   0         B：(0,0)→(1,0)→(2,0)→(2,1)  前綴和 0, -4, -1,  0   low = -4，cur =  0
 3   1  -5
                   正向 DP 選 A（low 較高）：最後一格 -5 讓 cur = -7，需要 8
                   B 雖然 low 較低，最後一格後 cur = -5，low = -5，只需要 6
```

這說明「到目前為止的最佳」無法用一個數字定義，所以正向的最優子結構不成立。

**突破點：反過來問「之後還需要多少」**。從 (i, j) 到終點這段路，騎士在進入 (i, j) 前至少要有多少血？這個量只和**後面**的格子有關，和怎麼走到 (i, j) 無關，而且它是一個單一的數字：血量越多越安全，所以只要比較「哪個方向需要的血比較少」。進入 (i, j) 時血量 h，經過這格後變成 h + `dungeon[i][j]`，這個值必須 ≥ 1，而且要 ≥ 下一格的需求 `nxt = min(need[i+1][j], need[i][j+1])`。所以 `h ≥ nxt − dungeon[i][j]` 且 `h ≥ 1`（進入任何一格前血量也必須是正的），得到 `need[i][j] = max(1, nxt − dungeon[i][j])`。終點格的「下一格需求」定義為 1（救完公主後血量仍要 ≥ 1）。

**正確性**。用「後綴」歸納：假設右邊與下面的格子的 need 都正確，騎士在 (i, j) 只能往其中一個方向走，選需求較小的方向最好；而 `max(1, ·)` 是因為補血格不能讓需求低於 1（補血不能預支：在血量 ≤ 0 時已經死了）。依賴方向是右與下，所以要從右下往左上填（22.4 節），每一格依賴的兩格都已經算好。這題展示了「選擇填表方向」本身就是設計的一部分：正向需要兩個量，反向只需要一個。

```text
dungeon                need（進入該格前至少要的血量）
 -2   -3    3           7    5    2
 -5  -10    1           6   11    5
 10   30   -5           1    1    6

填表順序：由下到上、由右到左；表外（右邊、下面）視為 ∞，終點的下一格視為 1
(2,2)  max(1, 1 − (−5))            = 6
(2,1)  max(1, 6 − 30)              = 1     30 的補血讓需求降到下限 1
(2,0)  max(1, 1 − 10)              = 1
(1,2)  max(1, 6 − 1)               = 5
(1,1)  max(1, min(5, 1) − (−10))   = 11
(1,0)  max(1, min(11, 1) − (−5))   = 6
(0,2)  max(1, 5 − 3)               = 2
(0,1)  max(1, min(11, 2) − (−3))   = 5
(0,0)  max(1, min(6, 5) − (−2))    = 7     ← 答案

沿著較小的 need 往前走即為最佳路徑：(0,0)→(0,1)→(0,2)→(1,2)→(2,2)
```

另一個可行的思路是二分答案（第 8 章）：固定初始血量 H，問「能不能活著走到終點」。這個判定可以正向 DP：每格記「活著抵達時的最大血量」，因為血量固定的初始條件下，抵達時血越多越好，一個數字就夠了。可行性對 H 單調（血越多越容易活），總時間 O(m · n · log V)，V 是血量上界。它比反向 DP 慢一個 log，但示範了「把兩個量的最佳化問題變成一個量的判定問題」，也是一個面試時可以提出的備案。

### 解法

```python
from itertools import combinations
import random


def calculate_minimum_hp(dungeon: list[list[int]]) -> int:
    m, n = len(dungeon), len(dungeon[0])
    INF = float("inf")
    need = [INF] * (n + 1)          # need[j] 在處理第 i 列時：未覆寫前是下方 (i+1, j)
    need[n - 1] = 1                 # 終點下方的哨兵：救完公主後血量仍要 ≥ 1
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            nxt = min(need[j], need[j + 1])          # 下方（舊值）、右方（本列已更新）
            need[j] = max(1, nxt - dungeon[i][j])
    return need[0]


def calculate_minimum_hp_binary_search(dungeon: list[list[int]]) -> int:
    m, n = len(dungeon), len(dungeon[0])

    def survives(h: int) -> bool:
        NEG = float("-inf")
        best = [NEG] * n             # best[j]：活著抵達 (i, j) 時的最大血量
        for i in range(m):
            for j in range(n):
                if i == 0 and j == 0:
                    come = h
                else:
                    come = max(best[j] if i > 0 else NEG, best[j - 1] if j > 0 else NEG)
                hp = come + dungeon[i][j]
                best[j] = hp if hp >= 1 else NEG    # 死掉的狀態不能再往下走
        return best[n - 1] >= 1

    lo, hi = 1, 1 + 1000 * (m + n - 1)              # hi 一定足夠
    while lo < hi:
        mid = (lo + hi) // 2
        if survives(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


def brute(dungeon):
    m, n = len(dungeon), len(dungeon[0])
    best = None
    for downs in combinations(range(m + n - 2), m - 1):
        i = j = 0
        cur = low = dungeon[0][0]
        for step in range(m + n - 2):
            if step in downs:
                i += 1
            else:
                j += 1
            cur += dungeon[i][j]
            low = min(low, cur)
        req = max(1, 1 - low)
        best = req if best is None else min(best, req)
    return best


assert calculate_minimum_hp([[-2, -3, 3], [-5, -10, 1], [10, 30, -5]]) == 7
assert calculate_minimum_hp([[0]]) == 1
assert calculate_minimum_hp([[100]]) == 1
assert calculate_minimum_hp([[-5]]) == 6
assert calculate_minimum_hp([[0, -3, 1], [-4, 0, 0], [3, 1, -5]]) == 6   # 正向 DP 會算成 8
assert calculate_minimum_hp([[1, -3, 3], [0, -2, 0], [-3, -3, -3]]) == 3
for _ in range(300):
    m, n = random.randint(1, 4), random.randint(1, 4)
    g = [[random.randint(-8, 8) for _ in range(n)] for _ in range(m)]
    assert calculate_minimum_hp(g) == calculate_minimum_hp_binary_search(g) == brute(g)
print("all tests passed")
```

### 複雜度與邊界

反向 DP 時間 O(m · n)，空間 O(n)（一列加一個哨兵）。二分版本時間 O(m · n · log V)，V ≈ 1000 · (m + n) ≈ 4 × 10⁵，大約 19 輪。邊界情況：1 × 1 地牢時答案是 `max(1, 1 − dungeon[0][0])`；全部是補血格時答案 1；終點格是大量扣血時需求由終點決定。哨兵的設計要小心：只有「終點的下方」（或右方）設為 1，其他表外格必須是無限大，否則邊界上的格子會誤以為可以走出地牢。`max(1, …)` 不能省略：沒有它，補血格會讓需求變成 0 或負數，代表「血量不足也能撐到補血」，但騎士在血量 ≤ 0 的那一刻已經死了。

### Follow-up

> [!question]- F1. 如果要回傳最佳路徑呢？
> 保留完整的 need 表（O(m · n)），從 (0, 0) 出發，每一步往 `need` 較小的那個鄰居走（右或下，只在範圍內比較），直到終點。因為 `need[i][j]` 正是由 `min(下, 右)` 算出來的，沿著較小的方向走就重現了最佳決策，不需要再驗證。注意這裡是**從起點往終點**回溯，方向和表格填寫相反，這是反向 DP 的特徵：答案在左上角，解也從左上角開始讀。時間 O(m + n)。範例 1 得到右、右、下、下。

> [!question]- F2. 二分答案的做法什麼時候比反向 DP 更好？
> 當問題的「後綴需求」無法寫成簡單公式時。例如加上規則「某些格子會讓血量減半」或「血量有上限」等非線性效果時，反向推「進入前至少要多少」可能需要反函數，甚至不是單調的公式；但給定初始血量的正向模擬總是容易寫（一步步算就好），只要可行性對初始血量單調，就能二分。代價是多一個 O(log V) 的因子。面試時可以把它當成「先保證正確的版本」，再說明反向 DP 如何省掉 log。

> [!question]- F3. 如果血量有上限 cap（補血不能超過 cap），答案會怎麼變？
> 反向 DP 仍然成立，只要加一個可行性檢查。進入 (i, j) 時血量 h，經過後是 `min(cap, h + d)`，要 ≥ `nxt`。如果 `nxt > cap`，無論如何都達不到，這格標為不可行（∞）；否則條件等價於 `h + d ≥ nxt`，需求仍是 `max(1, nxt − d)`，但若算出的需求 > cap 也要標為不可行（進入時的血量不可能超過 cap）。也就是在原公式後面加一句「超過 cap 就設為 ∞」。最後 `need[0][0]` 為 ∞ 代表無解。時間仍是 O(m · n)。

> [!question]- F4. 如果在最低初始血量的前提下，還要讓救到公主時剩下的血量最多呢？
> 先用反向 DP 得到最低初始血量 H*，再用二分版本中的 `survives` 正向 DP（每格記活著抵達時的最大血量）跑一次 H = H*，`best` 在終點的值就是最多能剩下的血量，因為正向 DP 在 H 固定時本來就是在最大化抵達血量。要回傳路徑時，保留正向的表回溯。總時間 O(m · n)。這個 follow-up 的重點是說出：「H 固定之後，問題就只剩一個量」，正向 DP 立刻變得可行。

> [!question]- F5. 如果騎士可以往四個方向走，但每格只能踏進一次呢？
> 這時路徑是網格上的簡單路徑，而且補血格會讓「繞遠路去補血」變得有利，狀態必須記錄走過哪些格子，屬於 NP-hard 的路徑問題，沒有多項式時間的 DP。若格子可以重複踏入但效果只觸發一次，同樣需要記錄已觸發的格子集合。若重複踏入時效果每次都觸發，而存在可來回的補血格，血量可以無限增加，答案只取決於能否安全抵達某個補血循環。面試時能清楚指出「只能往右往下 = DAG」是本題能用 DP 的前提，就足夠了。

### 心得

關鍵突破是把填表方向反過來：正向時每條路徑有「目前血量」與「途中最低點」兩個互相牽制的量，無法只保留一條；反向時每格只需要回答「進來前至少要多少血」，變回單一數字，最優子結構恢復成立。它和核心題 2 的網格是同一個形狀，差別在於依賴方向是右與下、答案在左上角，以及 `max(1, ·)` 這個下限。面試時建議先舉出正向 DP 失敗的例子（這是面試官最想聽到的理解），再提出反向定義；被追問時提出二分答案作為另一種思路，說明它多一個 log 但更容易推廣到非線性的規則。

## 難題 5｜1092. Shortest Common Supersequence｜Hard

### 題目

給兩個字串 `str1` 與 `str2`，回傳一個最短的字串，使得 `str1` 與 `str2` 都是它的子序列（shortest common supersequence，SCS）。如果有多個最短答案，回傳任意一個。限制：`1 <= len(str1), len(str2) <= 1000`，只含小寫英文字母。

- 範例 1：`str1 = "abac"`、`str2 = "cab"`，回傳 `"cabac"`（長度 5；"cab" 是前三個字元，"abac" 是後四個字元）。
- 範例 2：`str1 = "aaaaaaaa"`、`str2 = "aaaaaaaa"`，回傳 `"aaaaaaaa"`。
- 範例 3（邊界）：`str1 = "abc"`、`str2 = "def"`，沒有共同字元，答案長度 6，例如 `"abcdef"` 或 `"daebfc"`。
- 範例 4（邊界）：`str1 = "a"`、`str2 = "ab"`，回傳 `"ab"`，一個字串本身就是另一個的子序列時，答案就是較長的那個。

### 提示

> [!tip]- 提示 1
> 最笨的超序列是 `str1 + str2`，長度 m + n。哪些字元可以「共用」以縮短長度？共用的字元在兩個字串中必須保持什麼關係？

> [!tip]- 提示 2
> 被共用的字元必須在兩個字串中都依序出現，也就是一個共同子序列。共用得越多越短，所以 SCS 的長度是 m + n − LCS。

> [!tip]- 提示 3
> 建好核心題 3 的 LCS 表，從 (m, n) 回溯：字元相同就輸出一次並走對角；不同就往 LCS 值較大的方向走，並輸出「被丟下」的那個字元。走到邊界後把剩下的前綴也輸出，最後反轉。

### 詳解

**為什麼直覺做法不行**。貪婪地從左到右合併（兩個字串的下一個字元相同就共用，否則隨便輸出一個）會失敗，因為「現在共用哪一對」影響後面能共用多少。例如 `str1 = "abac"`、`str2 = "cab"`，從左邊開始時 a 與 c 不同，若先輸出 a，接著 b 與 c 不同……最後得到的長度取決於每次的選擇，沒有局部準則能保證最短。暴力列舉超序列更不可能。

**突破點：SCS 的長度 = m + n − LCS**。任何一個共同超序列 S，把 `str1` 與 `str2` 分別嵌進 S（標出它們在 S 中的位置），S 中同時被兩邊用到的字元，依序排起來就是 `str1` 與 `str2` 的一個共同子序列 C，而 `|S| ≥ m + n − |C| ≥ m + n − LCS`（每個 S 中的字元最多被兩邊各用一次，共用的才省下一個位置）。反過來，給定一個 LCS，可以構造出長度剛好 m + n − LCS 的超序列：沿著 LCS 的配對，把兩個字串中配對之間的字元依序輸出，配對的字元只輸出一次。下界與構造相等，所以這就是最短長度。

**構造：在 LCS 表上回溯**。從 (m, n) 往回走，維持「已輸出的部分是 `str1[i:]` 與 `str2[j:]` 的最短超序列（反向）」：

- `str1[i-1] == str2[j-1]`：這是 LCS 的一個字元，輸出一次，走到 (i − 1, j − 1)。
- 不同且 `dp[i-1][j] ≥ dp[i][j-1]`：LCS 不需要 `str1[i-1]`，把它單獨輸出，走到 (i − 1, j)。
- 否則：輸出 `str2[j-1]`，走到 (i, j − 1)。
- 一邊走到 0 之後，另一邊剩下的前綴全部輸出。

每一步要嘛輸出一個共用字元（i、j 各減一），要嘛輸出一個非共用字元（只有一邊減一），而共用的次數恰好是 `dp[m][n]` = LCS，所以總長度是 m + n − LCS。這和 22.5 節的 LCS 回溯幾乎相同，唯一的差別是「被丟下的字元也要輸出」。

```text
str1 = "abac"（列），str2 = "cab"（行），LCS 表：
          ""   c    a    b
     ""    0   0    0    0
     a     0   0    1    1
     b     0   0    1    2
     a     0   0    1    2
     c     0   1    1    2      LCS = 2 → SCS 長度 4 + 3 − 2 = 5

回溯（輸出的字元由後往前收集）：
位置     比較           動作                           收集（反向）
(4,3)   'c' vs 'b'     ↑ 2 ≥ ← 1，輸出 str1 的 c，i−1    c
(3,3)   'a' vs 'b'     ↑ 2 ≥ ← 1，輸出 str1 的 a，i−1    c a
(2,3)   'b' = 'b'      共用 b，走對角                    c a b
(1,2)   'a' = 'a'      共用 a，走對角                    c a b a
(0,1)   i = 0          輸出 str2 剩下的 "c"              c a b a c
反轉後："cabac"
```

### 解法

```python
from functools import cache
import random


def shortest_common_supersequence(str1: str, str2: str) -> str:
    m, n = len(str1), len(str2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if str1[i - 1] == str2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    out = []
    i, j = m, n
    while i > 0 and j > 0:
        if str1[i - 1] == str2[j - 1]:
            out.append(str1[i - 1])          # 共用字元，只輸出一次
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            out.append(str1[i - 1])          # str1[i-1] 不在 LCS 中，單獨輸出
            i -= 1
        else:
            out.append(str2[j - 1])
            j -= 1
    out.extend(reversed(str1[:i]))           # 剩下的前綴（之後整體會再反轉）
    out.extend(reversed(str2[:j]))
    return "".join(reversed(out))


def is_subsequence(a: str, b: str) -> bool:
    it = iter(b)
    return all(ch in it for ch in a)


def scs_length(a: str, b: str) -> int:
    @cache
    def go(i, j):                            # a[i:] 與 b[j:] 的 SCS 長度（直接定義，不經過 LCS）
        if i == len(a) or j == len(b):
            return len(a) - i + len(b) - j
        if a[i] == b[j]:
            return 1 + go(i + 1, j + 1)
        return 1 + min(go(i + 1, j), go(i, j + 1))
    return go(0, 0)


assert shortest_common_supersequence("abac", "cab") == "cabac"
assert shortest_common_supersequence("aaaaaaaa", "aaaaaaaa") == "aaaaaaaa"
assert len(shortest_common_supersequence("abc", "def")) == 6
assert shortest_common_supersequence("a", "ab") == "ab"
for _ in range(500):
    a = "".join(random.choice("abc") for _ in range(random.randint(1, 8)))
    b = "".join(random.choice("abc") for _ in range(random.randint(1, 8)))
    res = shortest_common_supersequence(a, b)
    assert is_subsequence(a, res) and is_subsequence(b, res)
    assert len(res) == scs_length(a, b)
print("all tests passed")
```

### 複雜度與邊界

時間 O(m · n) 建表、O(m + n) 回溯；空間 O(m · n)，因為回溯需要整張表（只要長度時可以壓成 O(min(m, n))，見 F1）。長度 1000 時表格是 10⁶ 格，在 Python 中大約佔 10 MB 量級，可以接受。邊界情況：兩字串相同時答案就是它；一個是另一個的子序列時答案是較長者；沒有共同字元時答案是兩者的任意交錯，長度 m + n；回溯走到某一邊為 0 時，一定要把另一邊剩下的前綴補上，這是最常漏掉的一步（漏掉時 `"a"` 與 `"ab"` 會只輸出 `"b"`）。

### Follow-up

> [!question]- F1. 如果只要 SCS 的長度呢？
> 長度是 `m + n − LCS`，用核心題 3 的一維 LCS，時間 O(m · n)、空間 O(min(m, n))。也可以直接對 SCS 長度做 DP：`f[i][j]` = `str1[:i]` 與 `str2[:j]` 的 SCS 長度，`f[i][0] = i`、`f[0][j] = j`，字元相同時 `f[i-1][j-1] + 1`，不同時 `min(f[i-1][j], f[i][j-1]) + 1`。這個形式和編輯距離（核心題 4）幾乎一樣，只是沒有替換。兩種寫法等價，前者比較容易說明「為什麼是這個長度」。

> [!question]- F2. 如果要回傳字典序最小的最短超序列呢？
> 字典序要從前面開始決定，所以改用**後綴**版本：`f[i][j]` = `str1[i:]` 與 `str2[j:]` 的 SCS 長度（從右下往左上填，22.4 節）。接著從 (0, 0) 往前建構：若 `str1[i] == str2[j]`，輸出它並走到 (i + 1, j + 1)（共用永遠是最佳的，因為 `f[i+1][j+1] + 1 ≤` 其他選擇）；否則兩個候選字元不同，比較 `f[i+1][j]` 與 `f[i][j+1]`，只保留讓長度最小的選擇，兩者都最小時選字元較小的那個。因為兩個候選字元不同，選較小的字元就直接決定了字典序，不需要往後比較。時間 O(m · n)。

> [!question]- F3. 如果要計算有幾個不同的最短超序列呢？
> 用後綴版本的長度表 f，再算計數表 `c[i][j]`：字元相同時只有共用這條路是最佳，`c[i][j] = c[i+1][j+1]`；字元不同時，把達到 `f[i][j]` 的方向（`f[i+1][j] + 1 == f[i][j]` 或 `f[i][j+1] + 1 == f[i][j]`）的計數相加；一邊用完時 `c = 1`。不同方向輸出的第一個字元不同（`str1[i] ≠ str2[j]`），所以得到的字串一定不同，計數不會重複；而字元相同時任何最短超序列的第一個字元都必須同時嵌入兩邊，所以只有共用這一種。時間 O(m · n)，數量可能很大，通常取模。

> [!question]- F4. 如果是三個字串的最短共同超序列呢？
> 兩兩合併（先求 SCS(a, b) 再和 c 合併）不一定最短，和核心題 3 F4 的反例同理：中間結果的選擇會影響後面能共用多少。正確做法是三維 DP，`f[i][j][k]` = 三個前綴的 SCS 長度，下一個輸出字元 x 會讓所有「最後一個字元是 x」的字串同時前進（三者相同就全部前進，兩個相同就前進那兩個），取最小值。時間 O(a · b · c)。對任意多個字串，SCS 是 NP-hard，所以狀態數必然隨字串數指數成長；字串數量固定且很少時，三維或四維 DP 是可行的。

> [!question]- F5. 如果長度到 10⁵，放不下 m · n 的表，但仍要輸出 SCS 呢？
> 先用 Hirschberg（核心題 3 F5）在 O(m + n) 空間內求出一個 LCS 字串 L，再線性合併：對 L 的每個字元 c，把 `str1` 中下一個 c 之前的字元全部輸出、把 `str2` 中下一個 c 之前的字元全部輸出，再輸出 c 一次，兩個指標都跳過這個 c；最後輸出兩邊剩下的字元。因為 L 是兩者的共同子序列，每個 c 一定能在兩邊找到，用「最左的下一個 c」嵌入是安全的（最左嵌入保留最多空間給後面的字元）。結果長度是 m + n − |L|，正是最短。總時間 O(m · n)（Hirschberg）加 O(m + n)（合併），空間 O(m + n)。

### 心得

關鍵突破是把「最短超序列」轉成「最長共同子序列」：共用的字元必然構成共同子序列，所以長度是 m + n − LCS，而構造只需在 LCS 表上回溯，並把被丟下的字元也輸出。它是本章「從 DP 表回溯出解」最完整的例子，和核心題 3 共用同一張表，和核心題 4 的「只插入不刪除」版本互為對偶（583 題的刪除數也是 m + n − 2 · LCS）。面試時先說出長度公式並用嵌入論證說明下界，再寫回溯；最容易被扣分的是忘了補上剩下的前綴，以及回溯的判斷與建表條件不一致。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 網格路徑計數 | 只能往右／往下，問有幾條路 | 上 + 左；障礙物設 0；可用組合數 | 核心題 1（62）、63 Unique Paths II、1643 Kth Smallest Instructions |
| 網格最佳路徑 | 只能往右／往下，最小化總和或瓶頸 | `cost + min(上, 左)`；回溯取路徑 | 核心題 2（64）、120 Triangle、931 Minimum Falling Path Sum |
| 網格上的正方形／矩形 | 「全是 1 的最大正方形」 | `dp[i][j] = 1 + min(上, 左, 左上)`，以 (i, j) 為右下角 | 221 Maximal Square、1277 Count Square Submatrices |
| 反向網格 DP | 正向需要兩個互相牽制的量（目前值與途中最低點） | 從終點往回定義「之後還需要多少」 | 難題 4（174） |
| 多人同步走網格 | 走去再走回、兩個機器人同時收集 | 同步步數 t，狀態 (t, r1, r2)，同格只算一次 | 741 Cherry Pickup、1463 Cherry Pickup II |
| LCS 類 | 兩序列的共同子序列、只能刪除使相等 | 相同走對角 + 1，不同取 max(上, 左) | 核心題 3（1143）、583、712、1035 Uncrossed Lines |
| 編輯距離類 | 插入、刪除、替換的最少次數或加權成本 | 三方向取 min；邊界是 i 與 j | 核心題 4（72）、161 One Edit Distance |
| 最長共同子字串 | 要求連續 | 狀態綁定結尾，不同時歸零，答案取全表最大 | 718 Maximum Length of Repeated Subarray |
| 交錯／路徑可達性 | 第三個序列由前兩個交錯組成 | (i, j) 決定 s3 的位置 i + j；布林網格 | 核心題 5（97） |
| Pattern matching | `.`、`?`、`*` 的整串匹配 | `*` 拆成「停止」與「再吃一個並保留」兩條轉移 | 難題 1（10）、難題 2（44） |
| 子序列計數 | s 中有幾個子序列等於 t | 以 s 的最後一個字元「用或不用」分類；一維時 j 倒著跑 | 難題 3（115）、940 Distinct Subsequences II |
| 由表建構解 | 回傳字串、路徑、操作序列 | 從答案格回溯，判斷條件與轉移一致；字典序最小用後綴表 | 難題 5（1092）、核心題 3 F1、核心題 4 的 `edit_script` |
| 一個序列的區間（第 23 章） | `s[i..j]` 的回文、合併、切割 | 依區間長度填表 | 516 Longest Palindromic Subsequence（= LCS(s, reverse(s))）、1312 |

**下限與上限**。最簡單的形式是 62 與 64：狀態就是格子本身，依賴只有上與左，考的是轉移與邊界的初始化。進一步是雙序列的三大標準形（1143、72、97），難點在**狀態要定義成前綴對**，並說清楚最後一個字元的每種處理方式對應哪一格；能把它們看成同一份 `align_cost` 模板換成本函式，就已經掌握了這一類。上限的題目難在四個地方，常常同時出現：第一，**轉移有隱藏的「保留」語意**，例如 10 與 44 的 `*` 在吃掉一個字元後仍然留著，退回 (i − 1, j) 而不是 (i − 1, j − 1)；第二，**計數要不重不漏**，例如 115 必須用 s 的字元「用或不用」分類，一維時還要倒著跑；第三，**填表方向本身是設計的一部分**，例如 174 正向不具最優子結構、反向才成立；第四，**要從表格建構解**，例如 1092 的回溯與字典序最小、計數等追問，需要知道什麼時候用前綴表、什麼時候用後綴表。更進一步的上限是資源限制：長度 10⁵ 時 O(m · n) 的表放不下，需要 Hirschberg 分治、LIS 轉換（核心題 3 F3）或帶狀 DP（核心題 4 F3）。

**與其他 pattern 的關係**。一維 DP（第 21 章）是本章的前置：本章所有題目都遵循同樣的四步驟，只是狀態多了一個索引；很多一維題其實是二維表壓縮後的結果，例如核心題 1 的一維 `row`。區間 DP（第 23 章）也用二維表，但兩個索引是**同一個序列**的左右端點，依賴更短的區間；最長回文子序列（516）恰好等於 s 與 reverse(s) 的 LCS，是兩章的交會點。0/1 背包（第 23 章）的一維壓縮要倒著跑，和本章難題 3 是同一個原因。網格允許四個方向時就不是 DP，而是圖論：非負權重用 Dijkstra（第 18 章）、無權重用 BFS（第 15 章）；如果四方向但要求嚴格遞增（329 Longest Increasing Path in a Matrix，第 16 章難題 2），依賴關係變回 DAG，又可以用 memoization。字串比對中，「固定 pattern 找出現位置」用 KMP 或 rolling hash（第 25 章）通常更快，只有 pattern 含 `*`、要求子序列而非子字串、或要計算距離時才需要本章的 DP。最後，二分答案（第 8 章）在 174 這種「最佳化兩個量」的題目中，可以把問題變成單一量的判定，是很好的備案。

**容易混淆之處**。第一，**子序列與子字串**：LCS 的轉移在字元不同時取 max，最長共同子字串則要歸零，答案在全表最大值而不是右下角。第二，**10 題與 44 題的 `*`**：前者綁定前一個字元、「用零次」退回 j − 2；後者獨立、「用零次」退回 j − 1；只有 44 題能用 O(1) 空間的貪婪。第三，**表格大小**：雙序列用 (m + 1) × (n + 1)，網格通常用 m × n，混用會造成 off-by-one。第四，**一維壓縮的方向**：有「左」依賴時正著跑並用 `prev` 保存對角，沒有「左」依賴時倒著跑；寫錯方向不一定會讓測試失敗，要用小例子手算一列確認。第五，**兩兩合併**：三個字串的 LCS 或 SCS 不能先合併兩個再處理第三個，必須用三維狀態。

## 本章重點整理

- 二維 DP 的狀態由兩個量決定：網格上的格子 (i, j)，或兩個序列的前綴對 `(s[:i], t[:j])`；四個步驟（狀態、轉移、base case、順序）和第 21 章完全相同。
- 雙序列 DP 用 (m + 1) × (n + 1) 的表，第 0 列、第 0 行是空前綴的 base case；`dp[i][j]` 看的是 `s[i-1]` 與 `t[j-1]`，這是最常見的 off-by-one 來源。
- 轉移只看最後一個字元：配對走對角 ↖，只消耗一邊走上 ↑ 或左 ←；LCS、編輯距離、只插入刪除，都是 `align_cost` 換成不同的成本函式。
- 填表順序由依賴箭頭決定：依賴上、左、左上就由上到下、由左到右；依賴下、右就倒過來（174）；依賴更短區間就依長度（第 23 章）。
- 正向定義需要兩個互相牽制的量時，試試反向定義成「之後還需要多少」（174），或二分答案把它變成單一量的判定。
- `*` 類的 pattern matching：把「吃幾個」拆成「停止」與「再吃一個並保留自己」，10 題退回 (i, j − 2) 或 (i − 1, j)，44 題退回 (i, j − 1) 或 (i − 1, j)；44 題另有記住最近一個 `*` 的 O(1) 空間貪婪。
- 計數 DP 的分類必須互斥且窮盡：115 題以 s 的最後一個字元「用或不用」分類，每個子序列恰好被數一次。
- 回溯出解要保留整張表，從答案格往回走，判斷條件和轉移一致，收集後反轉；要字典序最小時改用後綴表、從前面逐字元決定。
- 空間壓縮：有「左」依賴時一列加一個 `prev` 保存對角值；沒有「左」依賴時 j 倒著跑；讓較短的序列當列，空間 O(min(m, n))；需要回溯又要省空間時用 Hirschberg。
- SCS 長度 = m + n − LCS，只插入刪除的距離 = m + n − 2 · LCS，最長回文子序列 = LCS(s, reverse(s))：很多序列題都能歸約到 LCS。
- 網格只能往右往下才是 DAG，可以 DP；四個方向要改用 BFS 或 Dijkstra，除非有「嚴格遞增」之類的條件讓依賴重新變成 DAG。
- 面試的標準流程：先用遞迴說清楚狀態與轉移，在小例子上畫表並用一句話解讀幾個格子，再寫 bottom-up、壓縮空間，最後主動處理回溯與邊界。
