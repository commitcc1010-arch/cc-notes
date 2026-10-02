---
chapter: 3
title: 從限制推 Pattern：複雜度、Constraints 與決策樹
part: 0
---

# 第 3 章　從限制推 Pattern：複雜度、Constraints 與決策樹

> [!abstract] 本章地圖
> **核心問題**：面對一道沒看過的題目，怎麼在幾分鐘內縮小到一兩個候選 pattern，而且知道最佳解大概要多快？
>
> **你會學到**：
> - 從 n 的大小推出可接受的複雜度，以及其他 constraints（數值範圍、k、查詢次數）透露的訊號
> - Big-O 分析的實用方法：迴圈、調和級數、遞迴樹、Master theorem、記憶化遞迴
> - Amortized（攤銷）分析：為什麼 monotonic stack 和動態陣列是線性的
> - 題目訊號到 pattern 的決策樹，以及容易混淆的 pattern 對照
> - 26 個 pattern 的一頁總覽表（對應第 4–29 章）
> - Python 面試必備語法與資料結構（詳細版在附錄 A）

## 3.1 為什麼要先看 constraints

很多人讀題時會跳過最後幾行的限制條件，直接想做法。這是浪費資訊：constraints 是出題者留給你的最強提示。題目說 n ≤ 20，幾乎是在告訴你「指數時間可以接受」；說 n ≤ 10⁵，代表 O(n²) 一定會超時，你要找 O(n log n) 或 O(n)；說數值 ≤ 10⁹ 但要找某個「最小的最大值」，往往是在暗示對答案做 binary search。

在面試中，constraints 不一定會寫在題目上，所以第 2 章建議主動問「n 大概多大」。拿到答案後立刻換算成可接受的複雜度並說出來：「n 是 10⁵，所以我需要 O(n log n) 以內的做法。」這句話同時完成了三件事：證明你有複雜度意識、排除一整類做法、讓面試官確認你們的期待一致。

本章的方法分成兩步。第一步是用 constraints 決定**複雜度的上限**（3.2 節），第二步是用題目的結構訊號決定**pattern**（3.5 節）。兩者交叉之後，候選做法通常只剩一兩個。例如「n ≤ 10⁵ ＋ 連續子陣列 ＋ 有負數」交叉後，sliding window 被負數排除、O(n²) 被 n 排除，剩下的就是 prefix sum 加 hash map。

## 3.2 n 的大小與可接受複雜度

估算的基礎是一個粗略的數字：一般的評測環境中，編譯語言每秒大約能執行 10⁸ 量級的簡單操作，Python 大約慢一到兩個數量級（依操作而異，內建函式與 C 實作的部分快得多）。面試中沒有人會要求你精確估算，但你要能說出量級。下表是常用的經驗法則，以「在一般時間限制內可以通過」為準：

| n 的上限 | 可接受的複雜度 | 常見做法 | 本書章節 |
|---|---|---|---|
| ≤ 10–12 | O(n!)、O(n!·n) | 枚舉所有排列 | 19 |
| ≤ 20–25 | O(2ⁿ)、O(2ⁿ·n) | 枚舉子集、backtracking、bitmask DP（n ≤ 16–20 時 O(2ⁿ·n²) 也可） | 19、24 |
| ≤ 40 | O(2^(n/2)) | Meet in the middle：拆成兩半各自枚舉再合併 | 19 |
| ≤ 100–500 | O(n³) | 區間 DP、Floyd-Warshall、三層枚舉 | 18、23 |
| ≤ 10³–10⁴ | O(n²)、O(n² log n) | 二維 DP、枚舉所有配對 | 21、22 |
| ≤ 10⁵–10⁶ | O(n log n)、O(n) | 排序、heap、binary search、two pointers、sliding window、hashing | 4–14 |
| ≤ 10⁷–10⁸ | O(n) | 單趟線性掃描、計數陣列；Python 在 10⁸ 時逐一處理通常仍太慢，要靠內建函式或數學觀察 | 5–7、28 |
| ≥ 10⁹ | O(log n)、O(√n)、O(1) | 對答案 binary search、數學公式、質因數分解 | 8、28 |

這張表有幾點要注意。第一，n ≤ 10⁴ 時 O(n²) 是 10⁸，在 Python 中通常已經很緊，內層迴圈要非常簡單，否則要考慮 O(n log n)。第二，表中的「n」是**主要變數**，很多題目有多個變數，要把它們都代入：矩陣 m, n ≤ 200 時 O(m²·n) 是 8×10⁶，沒有問題；字串陣列有 n 個字、每個長度 L，複雜度通常寫成 O(n·L)。第三，限制是上限不是下限：n ≤ 10⁵ 的題目當然也接受 O(n)。

除了 n，其他 constraints 也會透露訊號：

| Constraint | 透露的訊號 | 例子 |
|---|---|---|
| 數值範圍小（例如 ≤ 10⁴） | 可以用數值當陣列索引、counting sort、對數值做 DP | 背包 DP 的容量維度（第 23 章） |
| 數值範圍很大（例如 ≤ 10⁹）且問最小化最大值 | 對答案 binary search，O(n log V) | 第 8 章核心題 4、5 |
| k 很小（例如 ≤ 10） | 狀態中可以帶 k 這一維，或對 k 個物件做 bitmask | 第 15 章難題 5 的「已拿到哪些鑰匙」（最多 6 把，用 bitmask）；第 15 章難題 3 則把「還能打破幾道牆」帶進狀態 |
| 字元集只有小寫英文 | 計數陣列長度 26，視為 O(1) | 第 6 章 anagram 類題目 |
| 查詢次數 q 很大（例如 10⁵） | 每次查詢必須 O(log n) 或 O(1)，需要預處理 | prefix sum（第 7 章）、segment tree（第 26 章） |
| 有更新又有查詢 | 靜態預處理不夠，要用支援更新的結構 | Fenwick tree、segment tree（第 26 章） |
| 答案要 mod 10⁹+7 | 計數題，結果很大，通常是 DP 或組合數學 | 第 21–24 章 |
| 「保證有解」「保證唯一」 | 可以省略無解處理，或可以提早回傳 | 第 4 章核心題 1 |

下面的小程式把第一張表寫成函式，並示範怎麼用操作次數的量級做判斷。它不是精確的效能預測，而是讓你習慣把 n 代入複雜度、看量級的思考方式。

```python
import math


def acceptable(n: int) -> str:
    """依 n 的上限回傳經驗上可接受的最大複雜度類別。"""
    if n <= 12:
        return "O(n!)"
    if n <= 25:
        return "O(2^n * n)"
    if n <= 40:
        return "O(2^(n/2))"
    if n <= 500:
        return "O(n^3)"
    if n <= 10**4:
        return "O(n^2)"
    if n <= 10**6:
        return "O(n log n)"
    if n <= 10**8:
        return "O(n)"
    return "O(log n) or O(1)"


def ops(n: int) -> dict[str, float]:
    """代入 n，列出各複雜度的操作次數量級（取 log10）。"""
    raw = {
        "n": n,
        "n log n": n * max(1, math.log2(n)),
        "n^2": n**2,
        "n^3": n**3,
        "2^n": 2.0**n if n < 1000 else math.inf,
    }
    return {k: round(math.log10(v), 1) for k, v in raw.items()}


assert acceptable(10) == "O(n!)"
assert acceptable(20) == "O(2^n * n)"
assert acceptable(300) == "O(n^3)"
assert acceptable(10**5) == "O(n log n)"
assert acceptable(10**7) == "O(n)"
assert acceptable(10**9) == "O(log n) or O(1)"

big = ops(10**5)
assert big["n^2"] == 10.0        # 10^10：太慢
assert big["n log n"] < 7        # 約 1.7 * 10^6：沒問題
small = ops(20)
assert small["2^n"] < 6.1        # 2^20 約 10^6：可以枚舉
print("all tests passed")
```

## 3.3 Big-O 分析方法

面試中的複雜度分析大多可以用幾個固定方法完成。重點不是背公式，而是知道「該數什麼」：數每個元素被處理幾次、數遞迴樹有多少節點、數 DP 有多少狀態乘上每個狀態的轉移成本。

**方法一：數迴圈，但要看內層的實際範圍。** 兩層迴圈不一定是 O(n²)。如果內層的指標從不後退（例如 sliding window 的左指標），兩層加起來只有 O(n)。如果內層跑 n/i 次（例如枚舉每個數的倍數），總和是 n/1 + n/2 + … + n/n，這是調和級數，約為 n ln n，也就是 O(n log n)。這個結論在質數篩法（第 28 章）和枚舉倍數的題目中經常出現。

**方法二：遞迴樹。** 把遞迴畫成樹，複雜度等於「每層的工作量加總」。分支數為 b、深度為 d 的遞迴樹有 O(bᵈ) 個節點：每次分兩支、深度 n 的子集枚舉是 O(2ⁿ)；排列是 n·(n-1)·…·1 = O(n!)。每個節點若還有額外工作（例如複製長度 n 的路徑），要再乘上去。

```text
merge sort 的遞迴樹（n = 8）：每層合併的總工作量都是 n

層 0：       [8]                    工作量 8
層 1：     [4]   [4]                工作量 4 + 4 = 8
層 2：   [2] [2] [2] [2]            工作量 8
層 3：  [1][1][1][1][1][1][1][1]    工作量 8（基底）

共 log2(8) + 1 = 4 層，每層 O(n) → 總共 O(n log n)
```

**方法三：Master theorem 速算。** 對於 T(n) = a·T(n/b) + O(nᵈ) 形式的遞迴，比較 d 和 log_b(a)：d 較大時是 O(nᵈ)（工作集中在根）；相等時是 O(nᵈ log n)（每層一樣多）；d 較小時是 O(n^(log_b a))（工作集中在葉子）。面試中常見的幾個結果直接記起來即可：

| 遞迴式 | 例子 | 結果 |
|---|---|---|
| T(n) = T(n/2) + O(1) | binary search | O(log n) |
| T(n) = T(n/2) + O(n) | quickselect 的平均情況 | O(n) |
| T(n) = 2T(n/2) + O(1) | 遍歷平衡二元樹 | O(n) |
| T(n) = 2T(n/2) + O(n) | merge sort | O(n log n) |
| T(n) = T(n-1) + O(1) | 線性遞迴 | O(n) |
| T(n) = T(n-1) + O(n) | 每層掃一遍剩下的元素（例如 selection sort） | O(n²) |
| T(n) = 2T(n-1) + O(1) | 不記憶化的 Fibonacci 式遞迴 | O(2ⁿ) |

**方法四：記憶化遞迴與 DP = 狀態數 × 每個狀態的轉移成本。** 這是分析 DP 最可靠的方法。例如 LCS 的狀態是 (i, j)，共 m·n 個，每個 O(1) 轉移，所以 O(m·n)；LIS 的 O(n²) 版本有 n 個狀態、每個要掃前面所有元素，所以 O(n²)。空間則是需要同時保存的狀態數，常常可以用滾動陣列從 O(m·n) 降到 O(n)。

**方法五：輸出大小是下限。** 如果題目要求列出所有子集，輸出就有 2ⁿ 個、總長度 O(n·2ⁿ)，任何演算法都不可能更快。面試官追問「能不能更快」時，指出輸出大小是很有力的回答。

下面的程式用實際計數驗證方法一的兩個結論：「指標不後退的兩層迴圈是線性的」與「枚舉倍數是 n log n」。

```python
import math


def count_window_steps(nums: list[int], limit: int) -> int:
    """sliding window：計算總共移動指標幾次（含 right 與 left）。"""
    steps = left = total = 0
    for right in range(len(nums)):
        total += nums[right]
        steps += 1
        while total > limit:          # 內層 while，但 left 從不後退
            total -= nums[left]
            left += 1
            steps += 1
    return steps


def count_multiple_steps(n: int) -> int:
    """對每個 i 枚舉它在 [1, n] 內的倍數：n/1 + n/2 + ... + n/n。"""
    steps = 0
    for i in range(1, n + 1):
        for _ in range(i, n + 1, i):
            steps += 1
    return steps


nums = [3, 1, 4, 1, 5, 9, 2, 6] * 500
n = len(nums)
assert count_window_steps(nums, 10) <= 2 * n          # 每個元素進出各一次
assert count_window_steps([], 10) == 0

for n in (1, 10, 1000, 20000):
    s = count_multiple_steps(n)
    assert s <= n * (math.log(n) + 1)                 # 調和級數上界
assert count_multiple_steps(1) == 1
assert count_multiple_steps(4) == 4 + 2 + 1 + 1
print("all tests passed")
```

## 3.4 Amortized 分析

Amortized（攤銷）複雜度是「一連串操作的總成本除以操作次數」。有些操作偶爾很貴，但貴的情況不可能常常發生，平均下來每次仍然便宜。面試中最常見的三個例子是動態陣列擴容、monotonic stack、以及 union-find。

**動態陣列。** Python 的 `list.append` 平均是 O(1)，但陣列滿了時要配置更大的空間並複製所有元素，那一次是 O(n)。關鍵在於容量是**倍數**成長（實際的成長倍率依實作而定，這裡用 2 倍說明）：從 1 長到 n 的過程中，複製次數是 1 + 2 + 4 + … < 2n，所以 n 次 append 總成本 O(n)，每次攤銷 O(1)。如果容量每次只加 1，複製次數就變成 1 + 2 + … + n = O(n²)。

**Monotonic stack。** 求每個元素的下一個更大元素時，內層有一個 `while` 迴圈不斷 pop，看起來像 O(n²)。但每個元素最多被 push 一次、pop 一次，所以整個演算法的 push 與 pop 總次數不超過 2n，總時間 O(n)。這個「每個元素進出各一次」的論證，也適用於 sliding window 的左右指標與 monotonic deque。

```text
nums = [2, 1, 5, 3, 6]，求下一個更大元素；stack 存索引，維持值遞減
（為了好讀，右欄的 stack 寫的是索引對應的值）

i=0 (2)：stack 空，push 0                         stack = [2]
i=1 (1)：1 < 2，push 1                            stack = [2, 1]
i=2 (5)：pop 1（答案 5）、pop 2（答案 5），push 2   stack = [5]
i=3 (3)：3 < 5，push 3                            stack = [5, 3]
i=4 (6)：pop 3（答案 6）、pop 5（答案 6），push 4   stack = [6]

push 5 次、pop 4 次，總共 9 ≤ 2n = 10
i=2 那一步 pop 了 2 次，但那兩個元素之後永遠不會再被處理
```

**Union-find。** 同時使用 path compression 與 union by rank（或 size）時，每次操作的攤銷成本是 O(α(n))，α 是反 Ackermann 函數，在任何實際的 n 下都不超過 4，面試中可以說「近乎常數」。只用其中一種優化時是 O(log n)。詳細說明在第 17 章。

講 amortized 複雜度時要說出理由，而不只是結論：「雖然內層有 while，但每個索引最多 push 一次、pop 一次，所以總共 O(n)。」下面的程式用計數驗證動態陣列與 monotonic stack 的攤銷結論。

```python
def append_copies(n: int, grow) -> int:
    """模擬 n 次 append，回傳總共複製了幾個元素。grow(cap) 回傳新容量。"""
    cap, size, copies = 1, 0, 0
    for _ in range(n):
        if size == cap:
            copies += size            # 擴容時複製所有現有元素
            cap = grow(cap)
        size += 1
    return copies


def next_greater(nums: list[int]) -> tuple[list[int], int]:
    """回傳每個元素的下一個更大元素（沒有則 -1），以及 push+pop 總次數。"""
    ans = [-1] * len(nums)
    stack: list[int] = []
    work = 0
    for i, x in enumerate(nums):
        while stack and nums[stack[-1]] < x:
            ans[stack.pop()] = x
            work += 1
        stack.append(i)
        work += 1
    return ans, work


n = 10_000
assert append_copies(n, lambda c: c * 2) < 2 * n            # 倍數成長：線性
assert append_copies(n, lambda c: c + 1) == n * (n - 1) // 2 # 每次加 1：平方

assert next_greater([2, 1, 5, 3, 6]) == ([5, 5, 6, 6, -1], 9)
assert next_greater([]) == ([], 0)
desc = list(range(n, 0, -1)) + [n + 1]       # 最壞情況：最後一個元素 pop 掉全部
ans, work = next_greater(desc)
assert ans[:-1] == [n + 1] * n and work <= 2 * len(desc)
print("all tests passed")
```

## 3.5 從題目訊號到 pattern：決策樹

有了複雜度上限之後，下一步是從題目的結構判斷 pattern。下面的決策樹依「最容易辨識的訊號」排序，括號內是本書章號。實際使用時不必從頭走到尾：找到第一個強烈符合的分支，再用 3.2 節的複雜度上限確認它是否夠快。如果有兩個分支都符合，通常代表題目是兩個 pattern 的組合，這正是很多難題的形狀。

```text
讀完題目，先用 3.2 節決定複雜度上限，然後依序問：

├─ n ≤ 20 左右，要求所有方案或最佳方案？
│    ├─ 列出所有子集／排列／組合 ──────────── Backtracking（19）
│    └─ 只要最佳值或方案數，狀態是「用過哪些」── Bitmask DP（24）
│
├─ 輸入已排序，或排序後不影響答案？
│    ├─ 找某個值、第一個／最後一個位置 ──────── Binary Search（8）
│    ├─ 找成對／三元組，從兩端往中間收斂 ────── Two Pointers（5）
│    └─ 區間：合併、重疊、同時進行的數量 ────── Intervals／Sweep Line（9）
│
├─ 問「最小的最大值」「最大的最小值」「最少需要多少才夠」，
│  而且「x 可行 ⇒ x+1 也可行」？ ──────────── Binary Search on Answer（8）
│
├─ 連續子陣列／子字串？
│    ├─ 元素非負，或條件隨窗口擴大而單調 ────── Sliding Window（6）
│    ├─ 有負數、和等於 k、多次區間和查詢 ────── Prefix Sum＋Hashing（7、4）
│    ├─ 窗口內的最大／最小值 ──────────────── Monotonic Deque（6）
│    └─ 陣列會更新，又要區間查詢 ──────────── Fenwick／Segment Tree（26）
│
├─ 「下一個更大／更小」「以每個元素為最小值的範圍」、括號、巢狀？
│    └─ Stack／Monotonic Stack（10）
│
├─ 前 k 大、第 k 小、合併 k 個有序序列、反覆取最小？
│    └─ Heap（14）；k 很大且答案可判定時，考慮 Binary Search（8）
│
├─ 計數、配對、分組、去重、「之前看過沒有」？ ── Hashing（4）
│
├─ Linked list：反轉、找中點、找環、合併，要求 O(1) 額外空間？
│    └─ Linked List（11），快慢指標
│
├─ 樹？
│    ├─ 路徑、深度、子樹資訊、逐層處理 ──────── Binary Tree DFS／BFS（12）
│    ├─ 有序、中序遍歷、BST 性質 ────────────── BST（13）
│    ├─ 字首、字典、多個字串同時搜尋 ────────── Trie（13）
│    └─ 每個節點選或不選、子樹的最佳值 ──────── Tree DP（24）
│
├─ 物件之間有關係（格子鄰居、單字轉換、依賴、連線）→ 先建成圖
│    ├─ 無權圖的最少步數、逐層擴散 ──────────── BFS（15）
│    ├─ 連通塊、可達性、塗色 ────────────────── DFS／BFS（15）
│    ├─ 動態合併群組、判斷是否同一組 ────────── Union-Find（17）
│    ├─ 先後順序、依賴、偵測有向環 ──────────── Topological Sort（16）
│    ├─ 有權最短路、最小成本或最小瓶頸 ──────── Dijkstra 等（18）
│    └─ 以最小總成本連通所有點 ──────────────── MST（18）
│
├─ 求「最多／最少／方案數」，而且每一步的選擇會影響之後？
│    ├─ 能用交換論證證明「局部最佳就是全域最佳」── Greedy（20）
│    └─ 否則：定義狀態、找重疊子問題 ──────────── DP
│         ├─ 一維序列、帶狀態（持有、冷卻、次數）─── 21
│         ├─ 兩個序列比對、格子路徑 ────────────── 22
│         ├─ 選物品湊容量；區間合併或切割 ───────── 23
│         └─ 樹上、子集（n ≤ 20）、數位統計 ─────── 24
│
├─ 字串比對、重複子字串、回文 ──────────────────── String Algorithms（25）
├─ 設計一個支援多種操作、每個操作有複雜度要求的類別 ── Data Structure Design（27）
├─ XOR、位元、質數、數學性質、n 到 10⁹ 以上 ────── Bit Manipulation／Math（28）
└─ 照規則模擬、矩陣旋轉、解析運算式或格式 ──────── Matrix／Simulation／Parsing（29）
```

使用決策樹時，有兩個習慣可以提高命中率。第一，**先轉換題目再判斷**：很多題目的表面形式和本質不同，例如「最少操作次數讓陣列連續」本質上是「排序去重後，找一個值域寬度固定的窗口內最多保留幾個元素」，轉換後才看得出是同向雙指標的 sliding window（第 5 章難題 5）。第二，**用複雜度上限反推**：如果 n ≤ 10⁵ 而你想到的做法是 O(n²)，那一定還有一個觀察沒找到，回頭問「哪個查詢在重複做」（第 2 章 2.3 節）。

## 3.6 容易混淆的 pattern

決策樹的分支之間有些邊界很模糊，下表整理最常混淆的幾組，以及用哪個問題區分。這些區分點在各 pattern 章的「Pattern 歸納」中會再詳細展開。

| 容易混淆 | 區分的問題 | 判斷 |
|---|---|---|
| Sliding window vs Prefix sum | 窗口擴大時，條件是否單調變化？ | 元素非負時單調，用 sliding window；有負數時不單調，用 prefix sum＋hash（第 6、7 章） |
| Greedy vs DP | 能否證明局部最佳選擇不會讓後面變差？ | 能用交換論證證明就 greedy；找得到反例就 DP（第 20、21 章） |
| Backtracking vs DP | 要列出所有方案，還是只要數量或最佳值？ | 列出全部用 backtracking；只要數量或最佳值，且子問題重疊，用 DP（第 19、21 章） |
| BFS vs Dijkstra | 邊有沒有權重？權重是否相同？ | 無權或權重相同用 BFS；權重只有 0 和 1 可用 0-1 BFS；一般非負權重用 Dijkstra（第 15、18 章） |
| DFS／BFS vs Union-Find | 圖是一次給定，還是邊會陸續加入？ | 靜態圖兩者都可；邊陸續加入、需要反覆問是否連通時 union-find 較自然（第 15、17 章） |
| Heap vs 排序 vs Quickselect | 是一次性問題還是串流？需要 k 個還是第 k 個？ | 串流或持續更新用 heap；一次性取第 k 個可用 quickselect 平均 O(n)；k 接近 n 時直接排序（第 14 章） |
| Binary search on index vs on answer | 搜尋的是陣列位置，還是一個數值範圍？ | 陣列有序時搜尋位置；答案有單調可行性時對數值範圍搜尋（第 8 章） |
| Two pointers vs Hashing | 輸入有序嗎？要回傳原始索引嗎？ | 有序或可排序且不需要原索引時 two pointers 省空間；需要原索引且無序時用 hash（第 4、5 章） |
| Topological sort vs DFS 找環 | 只要知道有沒有環，還是要順序？ | 兩者都能偵測有向環；要輸出順序或做依賴上的 DP 時用 topological sort（第 16 章） |

## 3.7 26 個 pattern 一頁總覽

下表是全書 26 個 pattern 的總覽，每列對應一章。「辨識訊號」是最常見的題目特徵，「典型複雜度」是標準形的複雜度，「代表題」是該章的第一道核心題。建議在讀完每個 Part 後回來看一次這張表，並試著不看表說出每一列的內容。

| 章 | Pattern | 本質 | 辨識訊號 | 典型複雜度 | 代表題 |
|---|---|---|---|---|---|
| 4 | Hashing 與計數 | 用空間換時間，O(1) 查詢「看過沒、出現幾次」 | 配對、計數、分組、去重 | O(n) | 1 Two Sum |
| 5 | Two Pointers | 利用有序性，每一步排除一整排候選 | 排序陣列、成對、從兩端收斂、原地操作 | O(n) 或 O(n log n) | 167 Two Sum II |
| 6 | Sliding Window | 維護一個滿足條件的連續窗口，左右指標都不後退 | 最長／最短連續子陣列、子字串、元素非負 | O(n) | 3 Longest Substring Without Repeating Characters |
| 7 | Prefix Sum 與 Difference Array | 區間和 = 兩個前綴相減；區間更新 = 兩端打標記 | 子陣列和、區間查詢、有負數、多次區間加值 | O(n) 預處理、O(1) 查詢 | 238 Product of Array Except Self |
| 8 | Binary Search | 在單調的判定上每次砍半 | 有序、旋轉陣列、最小化最大值、答案範圍很大 | O(log n) 或 O(n log V) | 34 Find First and Last Position |
| 9 | Intervals 與 Sweep Line | 依端點排序，掃描時維護目前狀態 | 區間合併、重疊、同時進行的最大數量 | O(n log n) | 56 Merge Intervals |
| 10 | Stack 與 Monotonic Stack | 保留尚未得到答案的候選，維持單調 | 括號、巢狀、下一個更大／更小、柱狀圖 | O(n) | 20 Valid Parentheses |
| 11 | Linked List | 指標操作、dummy 節點、快慢指標 | 反轉、合併、找環、找中點、O(1) 空間 | O(n) 時間、O(1) 空間 | 206 Reverse Linked List |
| 12 | Binary Tree：DFS 與 BFS | 子樹回傳資訊給父節點，或逐層處理 | 深度、路徑、直徑、層序、建樹 | O(n) | 102 Level Order Traversal |
| 13 | BST 與 Trie | BST 的中序有序；Trie 共用字首 | 驗證或查詢 BST、第 k 小、字首搜尋、字典 | O(h) 或 O(L) | 98 Validate BST |
| 14 | Heap：Top-K 與 K-way Merge | 只維護目前最需要的 k 個候選 | 前 k 大、第 k 小、合併 k 個序列、中位數 | O(n log k) | 215 Kth Largest Element |
| 15 | Graph：BFS 與 DFS | 把問題建成圖，逐層擴散或深入探索 | 格子、島嶼、最少步數、擴散、可達性 | O(V + E) | 200 Number of Islands |
| 16 | Topological Sort | 依入度逐步移除沒有依賴的節點 | 課程先修、依賴順序、偵測有向環 | O(V + E) | 207 Course Schedule |
| 17 | Union-Find | 用樹表示集合，合併與查詢近乎常數 | 動態連通、合併群組、找多餘的邊 | O(α(n)) 攤銷 | 547 Number of Provinces |
| 18 | Shortest Path 與 MST | 用 heap 依距離擴展；用最小邊連通 | 有權最短路、最小成本、限制步數、連通所有點 | O(E log V) | 743 Network Delay Time |
| 19 | Backtracking | 有系統地枚舉選擇，走不通就撤回 | 所有子集、排列、組合、n 很小、棋盤放置 | O(2ⁿ) 或 O(n!) | 78 Subsets |
| 20 | Greedy | 每一步做局部最佳選擇，用交換論證證明正確 | 跳躍、加油站、區間選擇、排程 | O(n) 或 O(n log n) | 55 Jump Game |
| 21 | DP：一維與狀態機 | 以前綴為狀態，或在有限個狀態間轉移 | 搶劫、硬幣、LIS、字串切分、買賣股票 | O(n) 到 O(n²) | 198 House Robber |
| 22 | DP：二維與序列比對 | 狀態是兩個序列的前綴或格子座標 | 兩個字串比對、編輯距離、格子路徑 | O(m·n) | 62 Unique Paths |
| 23 | DP：背包與區間 | 容量為狀態；或以區間 [i, j] 為狀態 | 湊出目標和、分割、回文子序列、戳氣球 | O(n·W) 或 O(n³) | 416 Partition Equal Subset Sum |
| 24 | DP：樹、Bitmask 與數位 | 狀態放在樹節點、子集或數字的位數上 | 樹上選點、n ≤ 20 的分配、計算 ≤ N 的數字個數 | O(n)、O(2ⁿ·n)、O(位數) | 337 House Robber III |
| 25 | 字串演算法 | 重用已比對的資訊：failure function、雜湊、中心擴展 | 子字串比對、重複子字串、回文 | O(n + m) | 5 Longest Palindromic Substring |
| 26 | Range Query | 用樹狀結構把區間拆成 log n 段 | 單點更新加區間查詢、逆序對、區間覆蓋 | O(log n) 每次操作 | 307 Range Sum Query Mutable |
| 27 | 資料結構設計 | 組合多個基本結構，讓每個操作都達到要求 | 設計 cache、O(1) 操作、時間版本、迭代器 | 依操作要求 | 146 LRU Cache |
| 28 | Bit Manipulation 與數學 | 利用位元或數學性質直接算出答案 | 只出現一次、XOR、質數、快速冪、n 很大 | O(1) 到 O(n log log n) | 136 Single Number |
| 29 | Matrix、模擬與解析 | 精準地照規則操作，拆成清楚的步驟 | 螺旋、旋轉、原地標記、運算式與格式解析 | O(m·n) 或 O(n) | 54 Spiral Matrix |

## 3.8 三個例子：從 constraints 到 pattern

下面用三道本書沒有收錄的自創題目，示範怎麼把 3.2 節的複雜度上限和 3.5 節的決策樹交叉使用。重點是推導過程，所以這裡只給思路，不給完整程式。

**例一：分配任務。** 有 n ≤ 15 個任務與 n 個工人，cost[i][j] 是工人 i 做任務 j 的時間，每人恰做一個任務，求最小總時間。

```text
constraints：n ≤ 15 → 指數可以接受，2^15 × 15 ≈ 5 × 10^5
訊號：每個任務「用過或沒用過」→ 狀態是一個子集
決策樹：n ≤ 20 且只要最佳值 → Bitmask DP（24）
狀態：dp[mask] = 前 popcount(mask) 個工人已分配到 mask 中的任務時的最小成本
轉移：下一個工人選一個不在 mask 中的任務
複雜度：O(2^n · n)，若用排列枚舉是 O(n!)，15! 約 1.3 × 10^12，太慢
```

**例二：最少的會議室容量。** 有 n ≤ 10⁵ 場活動依序排在 d 天內舉辦，活動 i 有 people[i] 人（≤ 10⁹），每天的活動要連續且順序不變，每天場地容量是當天活動人數的總和。求最小的「單日最大人數」。

```text
constraints：n ≤ 10^5 → 需要 O(n log n) 或 O(n log V)
訊號：「最小化最大值」，而且容量 C 可行 ⇒ C+1 也可行（單調）
決策樹：Binary Search on Answer（8）
判定：給定容量 C，從左到右貪婪地塞，數需要幾天，O(n)
範圍：答案介於 max(people) 和 sum(people) 之間
複雜度：O(n log(sum))，sum ≤ 10^14，log 約 47 次判定
（這是第 8 章核心題 5 與難題 2 的同一個形狀）
```

**例三：溫度變化的連續區段。** 給 n ≤ 10⁵ 個每日溫度變化（可能為負），求有多少個連續區段的變化總和恰好為 0。

```text
constraints：n ≤ 10^5 → O(n^2) 是 10^10，太慢
訊號：連續子陣列、和等於定值、有負數
決策樹：有負數 → sliding window 不成立（窗口擴大時和不單調）
        → Prefix Sum＋Hashing（7、4）
觀察：區段 (i, j] 的和為 0 ⇔ prefix[j] == prefix[i]
做法：邊掃邊用 hash map 記錄每個前綴和出現幾次
複雜度：O(n) 時間、O(n) 空間
（這是第 7 章核心題 2 在 k = 0 時的特例）
```

三個例子的共同步驟是：先用 constraints 定上限，再從題目找出最強的結構訊號，最後確認做法的複雜度落在上限內。如果做法超過上限，就回到第 2 章 2.3 節的瓶頸問句繼續優化。

## 3.9 Python 面試必備語法與資料結構

面試中用 Python 的好處是語法精簡，可以把時間花在演算法上；風險是有些操作的複雜度不直觀。下表列出最常用的工具與它們的複雜度，附錄 A 有每一項的詳細說明與更多陷阱。

| 工具 | 常用操作 | 複雜度 | 典型用途 |
|---|---|---|---|
| `list` | `append`、`pop()`、索引 | 攤銷 O(1) | stack、動態陣列 |
| `list` | `pop(0)`、`insert(0, x)`、`x in lst` | O(n) | 避免在迴圈中使用 |
| `dict`／`set` | 查詢、插入、刪除 | 平均 O(1) | hashing（第 4 章） |
| `collections.Counter` | 計數、`most_common(k)` | O(n) 建立 | 頻率統計 |
| `collections.defaultdict` | 自動初始化 | 平均 O(1) | 建圖、分組 |
| `collections.deque` | `append`、`appendleft`、`popleft` | O(1) | BFS、monotonic deque |
| `heapq` | `heappush`、`heappop` | O(log n) | min-heap；max-heap 存負值（第 14 章） |
| `heapq` | `heapify` | O(n) | 一次建 heap |
| `bisect` | `bisect_left`、`bisect_right` | O(log n) | 有序陣列查位置（第 8 章） |
| `sorted`／`list.sort` | `key=`、`reverse=` | O(n log n) | 排序，穩定排序 |
| `functools.cache` | 記憶化遞迴 | 依狀態數 | top-down DP（第 21 章） |
| `str` | 切片、`+` 串接、`join` | O(長度) | 迴圈中累積字串用 list 再 `join` |

幾個面試中最常見的 Python 陷阱：

- **二維陣列的淺複製**。`[[0] * n] * m` 會產生 m 個指向同一個 list 的參考，改一格會改到整欄，要寫成 `[[0] * n for _ in range(m)]`。
- **可變的預設參數**。`def f(path=[])` 的 `path` 在多次呼叫間共用，改用 `None` 再在函式內建立。
- **遞迴深度**。Python 預設的遞迴上限約 1000 層，深度可能到 10⁵ 的 DFS 要改成迭代，或提高 `sys.setrecursionlimit`（但仍可能耗盡 C stack）。
- **整數除法與負數**。`//` 向負無窮取整，`-7 // 2 == -4`；要向零取整用 `int(a / b)`（數值很大時注意浮點精度）。
- **heap 中的元組比較**。`heapq` 比較元組時第一個欄位相同會比第二個，第二個欄位若是不能比較的物件會出錯，可以加入遞增的計數器當第二個欄位。

下面的程式示範這些工具的典型用法，也把幾個陷阱寫成測試，可以當成考前的快速複習。

```python
import heapq
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict, deque
from functools import cache

# Counter 與 most_common
freq = Counter("mississippi")
assert freq["s"] == 4 and freq.most_common(2) == [("i", 4), ("s", 4)]  # 同次數依首次出現順序

# defaultdict 建圖
graph: defaultdict[int, list[int]] = defaultdict(list)
for u, v in [(0, 1), (0, 2), (1, 3)]:
    graph[u].append(v)
    graph[v].append(u)
assert sorted(graph[0]) == [1, 2] and graph[3] == [1]

# deque 做 BFS：求從 0 出發到每個點的步數
dist = {0: 0}
q = deque([0])
while q:
    u = q.popleft()
    for v in graph[u]:
        if v not in dist:
            dist[v] = dist[u] + 1
            q.append(v)
assert dist == {0: 0, 1: 1, 2: 1, 3: 2}

# heapq 是 min-heap；max-heap 存負值
nums = [5, 1, 8, 3, 9, 2]
assert heapq.nlargest(3, nums) == [9, 8, 5]
max_heap = [-x for x in nums]
heapq.heapify(max_heap)
assert -heapq.heappop(max_heap) == 9

# bisect：有序陣列中某個值的出現範圍
arr = [1, 2, 2, 2, 5, 7]
assert (bisect_left(arr, 2), bisect_right(arr, 2)) == (1, 4)
assert bisect_left(arr, 6) == 5            # 第一個 >= 6 的位置

# sorted 搭配 key：先依長度、再依字母
words = ["bb", "a", "ccc", "ab"]
assert sorted(words, key=lambda w: (len(w), w)) == ["a", "ab", "bb", "ccc"]

# functools.cache 做記憶化：爬樓梯方法數
@cache
def ways(n: int) -> int:
    return 1 if n <= 1 else ways(n - 1) + ways(n - 2)
assert ways(50) == 20365011074

# 陷阱 1：二維陣列淺複製
bad = [[0] * 3] * 2
bad[0][0] = 1
assert bad[1][0] == 1                      # 兩列是同一個物件
good = [[0] * 3 for _ in range(2)]
good[0][0] = 1
assert good[1][0] == 0

# 陷阱 2：可變預設參數
def append_bad(x, acc=[]):
    acc.append(x)
    return acc
append_bad(1)
assert append_bad(2) == [1, 2]             # 上一次呼叫的值還在

# 陷阱 3：整數除法向負無窮取整
assert -7 // 2 == -4 and int(-7 / 2) == -3

# 陷阱 4：heap 中第一欄相同時，用計數器避免比較到不可比較的物件
heap: list[tuple[int, int, dict]] = []
for i, (pri, payload) in enumerate([(1, {"a": 1}), (1, {"b": 2})]):
    heapq.heappush(heap, (pri, i, payload))
assert heapq.heappop(heap)[2] == {"a": 1}
print("all tests passed")
```

## 本章重點整理

- Constraints 是出題者給的最強提示：先用 n 決定複雜度上限，再用題目結構決定 pattern，兩者交叉後候選通常只剩一兩個。
- 經驗法則：n ≤ 12 → O(n!)；≤ 20–25 → O(2ⁿ·n)；≤ 500 → O(n³)；≤ 10⁴ → O(n²)；≤ 10⁶ → O(n log n)；≤ 10⁸ → O(n)；更大 → O(log n) 或 O(1)。Python 中 10⁸ 次操作通常已經太慢。
- 其他 constraints 也是訊號：數值範圍小可以當索引、問最小化最大值暗示對答案 binary search、k 很小可以放進狀態、查詢很多需要預處理、有更新又有查詢需要 Fenwick 或 segment tree。
- 複雜度分析的五個方法：數迴圈的實際範圍（含調和級數）、遞迴樹、Master theorem、DP = 狀態數 × 轉移成本、輸出大小是下限。
- 指標不後退的兩層迴圈是 O(n)；枚舉倍數的總和是 O(n log n)。
- Amortized 分析要說出理由：動態陣列倍數成長所以複製總量 < 2n；monotonic stack 每個元素最多 push、pop 各一次；union-find 雙優化是 O(α(n))。
- 決策樹依最強的結構訊號分支：n 很小、有序、單調可行性、連續子陣列、下一個更大、前 k 個、計數配對、樹、圖、最佳化、字串、設計、數學、模擬。
- 容易混淆的組合要用一個問題區分：有負數嗎（sliding window vs prefix sum）、能證明局部最佳嗎（greedy vs DP）、要列出全部嗎（backtracking vs DP）、邊有權重嗎（BFS vs Dijkstra）。
- 26 個 pattern 對應第 4–29 章，讀完每個 Part 後用總覽表自我測驗。
- Python 要注意 `list.pop(0)` 是 O(n)、`heapq` 是 min-heap、二維陣列淺複製、可變預設參數、遞迴深度與負數整數除法。

## 延伸問答

> [!question]- Q1. 面試時題目沒有給 constraints，面試官也說「你覺得呢」，該怎麼辦？
> 這時面試官通常是想看你能不能自己提出合理假設並討論取捨。可以這樣回答：「如果 n 在幾千以內，O(n²) 的做法最簡單也最不容易錯；如果到 10⁵ 以上，就需要 O(n log n)。我先說明 O(n²) 的做法，再優化到 O(n log n)。」這樣既展示了複雜度意識，也給了面試官選擇的空間。多數情況下面試官會期待你走到最佳解，所以先講暴力解作為基準，再把主要時間花在最佳解上，是最穩的策略。

> [!question]- Q2. 我想到的做法是 O(n log n)，但 constraints 看起來允許 O(n²)，要用哪個？
> 先確認兩者在時間內都能寫對。如果 O(n log n) 的做法同樣清楚而且你有把握，就用它，並說明 O(n²) 也能通過，這顯示你知道還有更好的做法。如果 O(n log n) 的做法明顯更複雜、容易出錯，可以先寫 O(n²) 並說明理由：「n ≤ 1000，O(n²) 是 10⁶，完全足夠，而且程式比較不容易出錯；如果 n 變大，我會改用排序加 binary search。」面試官通常會接受這種有根據的取捨，甚至把它當成 follow-up 的起點。

> [!question]- Q3. Hash table 的操作真的是 O(1) 嗎？面試官追問最壞情況怎麼回答？
> 平均情況是 O(1)，前提是雜湊函數把鍵分散得夠均勻。最壞情況下所有鍵都碰撞到同一個位置，單次操作會退化成 O(n)，Python 的 dict 使用開放定址法，理論最壞情況同樣是線性。實務上，內建型別的雜湊在一般輸入下表現良好，所以面試中以平均 O(1) 討論是慣例。如果面試官追問，可以補充兩點：一是字串鍵的雜湊要花 O(L) 時間，二是需要最壞情況保證時，可以改用平衡樹結構，代價是每次操作 O(log n)。

> [!question]- Q4. 遞迴解的空間複雜度怎麼算？明明沒有開陣列。
> 遞迴呼叫會佔用 call stack，每一層保存參數、區域變數與返回位置，所以空間至少是最大遞迴深度乘上每層的大小。例如平衡二元樹的 DFS 深度是 O(log n)，但退化成鏈狀的樹深度是 O(n)，所以要說「O(h)，最壞 O(n)」。Backtracking 的空間通常是遞迴深度加上目前路徑的長度，不計輸出。記憶化遞迴還要加上快取的大小，也就是狀態數。另外 Python 預設遞迴上限約 1000 層，深度可能很大時要改寫成迭代。

> [!question]- Q5. 為什麼排序陣列不一定要用 binary search？什麼時候 two pointers 比較好？
> 兩者都利用了有序性，但用法不同。Binary search 適合「對一個固定目標，找它的位置」，每次查詢 O(log n)；如果要對 n 個元素各查一次，總共 O(n log n)。Two pointers 適合「兩個位置的關係隨著移動而單調變化」，例如在排序陣列找和為 target 的兩數：和太小就移左指標、太大就移右指標，每一步排除一整排候選，總共 O(n)。所以當問題涉及兩個元素的配對且移動方向可以確定時，two pointers 通常更快；只需要定位單一值時才用 binary search。

> [!question]- Q6. 怎麼判斷一題是 greedy 還是 DP？我常常用 greedy 結果是錯的。
> 先嘗試找反例，這是最快的方法：用三到四個元素的小例子，比較 greedy 的結果和窮舉的結果。例如硬幣面額 {1, 3, 4} 湊 6，每次拿最大的會得到 4+1+1 三枚，但最佳是 3+3 兩枚，greedy 就不成立，要用 DP。如果找不到反例，再嘗試交換論證：假設最佳解在某一步沒有做 greedy 的選擇，證明換成 greedy 的選擇不會變差。說得出這個論證才能放心用 greedy。第 20 章會為每題寫出這個論證。

> [!question]- Q7. n ≤ 10⁵ 但我的 DP 是 O(n²)，該往哪個方向優化？
> 先看轉移在做什麼。如果每個狀態要掃過前面所有狀態取最大或最小，常見的優化有四種：一是轉移只依賴一個滑動範圍，用 monotonic deque 把每次轉移降到攤銷 O(1)；二是轉移是「前面所有值中滿足某條件的最大值」，用 binary search 或 Fenwick tree 降到 O(log n)，例如 LIS 從 O(n²) 降到 O(n log n)；三是狀態定義本身可以換，例如把「長度」和「值」的角色對調；四是重新檢查是否其實有 greedy 性質。這些技巧分別在第 21、26 章的難題中出現。

> [!question]- Q8. 決策樹走完還是不知道用什麼 pattern，怎麼辦？
> 先試著換一個角度描述題目，因為很多題目的表面形式掩蓋了本質。可以問自己：能不能把「操作次數最少」改成「保留的元素最多」？能不能把二維問題壓成一維（例如固定上下兩列，變成一維的子陣列問題）？能不能把物件之間的關係畫成圖？接著手算一個小例子，觀察自己的大腦用什麼方法得到答案，那個方法往往就是 greedy 或 DP 的雛形。如果還是沒有方向，就寫出暴力解，再用第 2 章 2.3 節的瓶頸問句一步一步優化。
