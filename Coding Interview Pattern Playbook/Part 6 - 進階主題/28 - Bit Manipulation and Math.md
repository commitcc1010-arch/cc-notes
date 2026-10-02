---
chapter: 28
title: Bit Manipulation 與數學
part: 6
---

# 第 28 章　Bit Manipulation 與數學

> [!abstract] 本章地圖
> **一句話**：把數字看成「一排獨立的位元」或「一個有結構的代數物件」，用 XOR 抵消、最低位技巧、快速冪、篩法、組合計數等少數工具，把看起來要列舉的問題變成 O(1)、O(log n) 或 O(√n) 的計算。
>
> **辨識訊號**：
> - 「其他元素都出現兩次（或三次），只有一個不同」，而且要求 O(1) 額外空間
> - 題目在問二進位表示本身：1 的個數、2 的冪、翻轉位元、區間 AND／OR
> - n 或指數高達 10⁹、10¹⁸，連 O(n) 都不行，只能 O(log n)、O(√n) 或公式
> - 「答案對 10⁹ + 7 取模」「有幾種方法」「第 k 個排列」
> - 質數、因數、最大公因數、整除、連續整數的和
> - 操作規則很奇怪（只能在某條件下翻某一位），而狀態空間太大無法 BFS
>
> **核心題**：136、268、191、50、204
>
> **難題**：137、201、60、829、1611

## 28.1 這個 Pattern 解決什麼問題

先看一個最小的例子。一個陣列裡每個數都出現兩次，只有一個數出現一次，要找出它。最直接的做法是用 hash table 數每個數出現幾次，時間 O(n)、空間 O(n)；或者先排序再找落單的那個，時間 O(n log n)。可是如果面試官要求 O(1) 額外空間、又不准修改陣列，這兩種做法都不行。突破口是 XOR（互斥或）：`a ^ a = 0`、`a ^ 0 = a`，而且 XOR 可以任意交換順序。把所有數 XOR 起來，成對的數互相抵消成 0，剩下的就是答案，一次掃描、一個變數。

這個例子說明了本章的核心想法：**很多題目真正需要的資訊，遠比「把每個元素都記下來」少**。只要找到一種運算，它能在掃描的過程中把無關的資訊自動抵消或合併，就能用常數空間得到答案。XOR 抵消成對的數；`x & (x - 1)` 一次消掉最低位的 1；`x & -x` 一次取出最低位的 1；逐位元計數把「每個數出現幾次」拆成「每一位出現幾次」。這些技巧之所以有效，是因為二進位的每一位彼此獨立，可以分開思考。

數學工具則解決另一類瓶頸：**輸入的數字本身很大**。算 x 的 10⁹ 次方，乘 10⁹ 次太慢，但 10⁹ 只有 30 個二進位位元，用平方再平方的快速冪只需要約 60 次乘法。找 n = 5 × 10⁶ 以內的質數，對每個數試除要 O(n√n)，篩法只要 O(n log log n)。問 10⁹ 能寫成幾種連續正整數的和，列舉起點要 O(n)，列出代數式之後只需要 O(√n)。這些題目的共同點是：暴力解在數值上列舉，好的解法在**結構**上計算。

面試中這一章的題目有兩種風險。第一種是位元細節出錯：Python 的整數沒有固定長度、負數有無限多個前導 1，照抄 C++ 的位元寫法可能無窮迴圈或得到錯的正負號。第二種是「看不出是數學題」：題目包裝成模擬或搜尋，直接寫 BFS 會超時。本章開頭的四個小節先把常用工具講清楚，28.6 節再說明面試中怎麼辨識數學題、怎麼從暴力打表走到公式。

## 28.2 辨識訊號

| 題目特徵 | 為什麼是位元或數學 | 本章哪一題 |
|---|---|---|
| 每個數都出現兩次，只有一個出現一次；要求 O(1) 空間 | `a ^ a = 0`，成對的數 XOR 後自動抵消 | 核心題 1（136） |
| 數字是 0..n 少一個、或 1..n 多一個 | 把索引和值一起 XOR（或求和），配對後只剩缺的那個 | 核心題 2（268） |
| 問二進位中 1 的個數、是不是 2 的冪 | `x & (x - 1)` 每次消掉一個 1，迴圈次數等於 1 的個數 | 核心題 3（191） |
| 指數 n 到 2³¹ 或更大，要算 xⁿ 或 aⁿ mod m | 把 n 寫成二進位，平方 log n 次 | 核心題 4（50） |
| 「小於 n 的質數」「每個數的最小質因數」「多次分解質因數」 | 篩法一次處理整個範圍，均攤到每個數幾乎是常數 | 核心題 5（204） |
| 其他數都出現三次（或 k 次） | 每一位的 1 的個數 mod k，剩下的就是答案的位元 | 難題 1（137） |
| 區間 [L, R] 所有數的 AND／OR／XOR，R − L 可達 2³¹ | 答案只取決於 L 和 R 的共同二進位前綴（或 XOR 的週期性） | 難題 2（201） |
| 第 k 個排列、第 k 個組合，k 到 n! | 每個開頭對應一整塊 (n − 1)! 個排列，用除法跳過整塊 | 難題 3（60） |
| n 到 10⁹，問「能寫成幾種……的和」 | 列出代數式，枚舉長度只到 √n，或化簡成因數個數 | 難題 4（829） |
| 規則奇怪的操作、問最少步數，狀態有 2³⁰ 個 | 打表後發現規律（Gray code），用遞迴式或公式直接算 | 難題 5（1611） |
| 「答案對 10⁹ + 7 取模」 | 答案是計數，數字會指數成長；通常是 DP 或組合數 | 28.5 節 |

**面試中數學題怎麼辨識**。最強的訊號是**限制和暴力解的落差**：題目只有一個整數輸入、範圍卻到 10⁹ 或 10¹⁸，代表面試官期待的是 O(√n)、O(log n) 或 O(1)，而這幾乎一定來自某個數學結構（第 3 章的限制對照表在這裡最好用）。第二個訊號是**題目描述中出現數學物件**：質數、因數、整除、餘數、連續整數、排列的排名、模數。第三個訊號是**O(1) 空間的要求搭配「成對」「缺一個」「出現 k 次」**，這幾乎就是在要求 XOR 或逐位元計數。

第四個訊號比較隱晦：**操作規則看起來是模擬題，但狀態數爆炸**。例如「每一輪翻轉所有第 i 個倍數的燈泡」（319. Bulb Switcher）、「每次可以拿 1–3 顆石頭」（292. Nim Game）、難題 5 的翻位元規則。這類題目要先寫暴力解把小的 n 跑出來，觀察答案的規律，再回頭證明。28.6 節會用一個完整的例子示範這個流程。

反過來，也有看起來像數學、其實是別的 pattern 的題目。「有幾種方法」且 n ≤ 1000、每一步有選擇，通常是 DP（第 21–23 章），只是答案要取模；「第 k 小」而候選是 m·n 個乘積，是第 8 章的計數二分，不是組合數學。判斷的依據是：數學解法需要一個**能直接計算的結構**（公式、遞迴式、週期、進位制），如果找不到這個結構，就回到搜尋或 DP。

## 28.3 位元技巧模板與 Python 的整數

這一節的技巧在面試中會反覆用到，每一個都要能說出「為什麼」，而不只是背結果。先看程式，再逐一解釋。

```python
def lowbit(x: int) -> int:
    """x 的最低位 1 所代表的值，例如 12 = 0b1100 → 4。"""
    return x & -x


def clear_lowbit(x: int) -> int:
    """把 x 的最低位 1 變成 0，例如 12 = 0b1100 → 8。"""
    return x & (x - 1)


def is_power_of_two(x: int) -> bool:
    return x > 0 and x & (x - 1) == 0


def submasks(mask: int) -> list[int]:
    """由大到小列出 mask 的所有非空子集合（子遮罩）。"""
    out, sub = [], mask
    while sub:
        out.append(sub)
        sub = (sub - 1) & mask
    return out


MASK32 = 0xFFFFFFFF


def to_signed32(x: int) -> int:
    """把任意 Python 整數解讀成 32 位元有號整數。"""
    x &= MASK32
    return x - (1 << 32) if x >> 31 else x


def add32(a: int, b: int) -> int:
    """不用 + 的 32 位元加法（371. Sum of Two Integers）。"""
    a, b = a & MASK32, b & MASK32
    while b:
        a, b = (a ^ b) & MASK32, ((a & b) << 1) & MASK32   # 無進位和、進位
    return to_signed32(a)


assert lowbit(12) == 4 and lowbit(7) == 1 and lowbit(0) == 0
assert clear_lowbit(12) == 8 and clear_lowbit(1) == 0
assert [x for x in range(20) if is_power_of_two(x)] == [1, 2, 4, 8, 16]
x = 0b1101                                   # 13
assert (x >> 2) & 1 == 1                     # 讀第 2 位
assert x | (1 << 1) == 0b1111                # 設第 1 位
assert x & ~(1 << 0) == 0b1100               # 清第 0 位
assert x ^ (1 << 3) == 0b0101                # 翻第 3 位
assert submasks(0b101) == [0b101, 0b100, 0b001]
a, b = 6, 9
a ^= b; b ^= a; a ^= b                       # XOR 交換
assert (a, b) == (9, 6)
# Python 的負數：概念上有無限多個前導 1
assert -5 & 0xFF == 0b11111011
assert -1 >> 10 == -1 and ~5 == -6
assert bin(-5) == "-0b101" and (-5).bit_count() == 2   # 注意：不是二補數的 1 的個數
assert to_signed32(0xFFFFFFFF) == -1 and to_signed32(1 << 31) == -(1 << 31)
assert add32(-1, 1) == 0 and add32(-5, -7) == -12
assert add32((1 << 31) - 1, 1) == -(1 << 31)           # 32 位元溢位會繞回
print("all tests passed")
```

**`x & (x - 1)`：消掉最低位的 1**。x 減 1 時，最低位的 1 變成 0，它右邊的 0 全部變成 1，左邊不變。例如 `x = 1011000`，`x − 1 = 1010111`。兩者 AND 起來，左邊保留、最低位的 1 和它右邊全部變成 0，得到 `1010000`。所以「x 是 2 的冪」等價於「x > 0 且 `x & (x − 1) == 0`」（只有一個 1），而「重複做到 x 變成 0 的次數」就是 1 的個數（核心題 3）。

**`x & -x`：取出最低位的 1**。在二補數中 `-x = ~x + 1`：先把每一位反轉，最低位的 1 變成 0、它右邊的 0 變成 1，再加 1 時進位一路傳到原本最低位 1 的位置停下。結果是：最低位的 1 和它右邊與 x 相同，左邊全部和 x 相反。AND 之後只剩最低位的 1，例如 `x = 1011000` 得到 `0001000`。這個值叫 lowbit，是 Fenwick tree（第 26 章）的核心，也是核心題 1 的 F1（260 題）用來把數字分成兩組的工具。

**XOR 的性質**。`a ^ a = 0`、`a ^ 0 = a`、交換律與結合律成立，所以一串數 XOR 起來，出現偶數次的數完全抵消，只剩出現奇數次的數。另外 `a ^ b = c` 等價於 `a = b ^ c`，所以 XOR 也是「可逆的合併」：前綴 XOR `P[i]` 存下來之後，任意區間的 XOR 是 `P[r] ^ P[l]`，和第 7 章的前綴和完全同構。逐位元來看，XOR 就是「不進位的加法」，這正是 `add32` 的原理：`a ^ b` 是不考慮進位的和，`(a & b) << 1` 是進位，重複到沒有進位為止。

**子遮罩枚舉 `(sub - 1) & mask`**。sub 減 1 會把最低位的 1 變成 0、右邊變成 1，再和 mask AND 就只保留 mask 裡有的位，得到「比 sub 小的下一個子集合」。枚舉一個 mask 的所有子集合是 O(2^popcount)；對所有 mask 各自枚舉子集合，總共是 O(3ⁿ)，因為每一位有「不在 mask」「在 mask 不在 sub」「都在」三種狀態。這在第 24 章的 bitmask DP 中常用。

**Python 的整數沒有固定長度**。這是 Python 寫位元題最容易出錯的地方。C++ 和 Java 的 `int` 是 32 位元二補數，`-1` 是 32 個 1；Python 的 `-1` 在概念上是**無限多個 1**，`-5` 是 `…11111011`。這帶來三個後果：第一，`-1 >> 1` 仍是 `-1`，所以「右移直到變成 0」的迴圈對負數永遠不會結束；第二，`~5` 是 `-6`，不是「32 位元裡反轉 5」的 `4294967290`；第三，`bin(-5)` 是 `'-0b101'`、`(-5).bit_count()` 是 2，它們描述的是絕對值，不是二補數。

**模擬 32 位元的兩個函式**。題目若要求 32 位元語意（溢位繞回、負數的二補數表示），就用 `x & 0xFFFFFFFF` 把數字限制在 32 位元的無號範圍 `[0, 2³²)`，運算過程中每一步都保持這個遮罩；最後如果第 31 位是 1，代表它是負數，減掉 `2³²` 轉回 Python 的負數。`add32` 就是這樣做的：不加遮罩時，`add32(-1, 1)` 的進位會一直往左傳，因為 Python 的 -1 有無限多個 1，迴圈永遠不會結束。

**運算子優先序**。Python 中比較運算子的優先序低於位元運算，所以 `x & 1 == 0` 是 `(x & 1) == 0`，這和 C／Java 相反（在 C 中它是 `x & (1 == 0)`）；但加減的優先序高於移位，`1 << n - 1` 是 `1 << (n - 1)`，`a + b >> 1` 是 `(a + b) >> 1`。不確定時一律加括號，面試官不會因為括號多而扣分。

## 28.4 快速冪與模運算

**快速冪（binary exponentiation）**。要算 aⁿ，把 n 寫成二進位，例如 13 = 1101₂，則 a¹³ = a⁸ · a⁴ · a¹。從 a 開始反覆平方，依序得到 a¹、a²、a⁴、a⁸……；n 的某一位是 1，就把對應的冪乘進答案。n 只有 ⌊log₂ n⌋ + 1 位，所以只需要 O(log n) 次乘法。遞迴的寫法是 aⁿ = (a^(n/2))²（n 偶數）或 a · (a^((n−1)/2))²（n 奇數），每層只做一次遞迴呼叫，深度 O(log n)。

**模運算**。計數題的答案常常是天文數字，題目會要求「對 10⁹ + 7 取模」。加法、減法、乘法都可以在每一步取模：`(a + b) % m`、`(a − b) % m`、`(a · b) % m` 的結果與先算完再取模相同。在 Python 中 `%` 對正的模數永遠回傳非負數，所以減法不必擔心負數；在 C++／Java 中 `(a − b) % m` 可能是負的，要寫成 `((a − b) % m + m) % m`。Python 的整數不會溢位，但數字越大乘法越慢，所以仍然要每一步取模，讓數字保持在 m² 以下。

**除法不能直接取模**。`(a / b) % m` 不等於 `(a % m) / (b % m)`。正確的做法是乘上 b 的**模反元素** b⁻¹，也就是滿足 b · b⁻¹ ≡ 1 (mod m) 的數。m 是質數時（10⁹ + 7 和 998244353 都是質數），由費馬小定理 b^(m−1) ≡ 1，所以 b⁻¹ = b^(m−2) mod m，用快速冪 O(log m) 算出。Python 3.8 起也可以直接寫 `pow(b, -1, m)`，它用擴展歐幾里得演算法，模數不是質數時也能用，只要 gcd(b, m) = 1；不互質時反元素不存在，會丟出 `ValueError`。

```python
MOD = 10**9 + 7


def power(a: int, e: int, m: int) -> int:
    """回傳 a^e mod m，e >= 0。"""
    result, a = 1 % m, a % m
    while e:
        if e & 1:                 # 這一位是 1：把目前的 a^(2^i) 乘進答案
            result = result * a % m
        a = a * a % m             # a^(2^i) → a^(2^(i+1))
        e >>= 1
    return result


def inverse(b: int, p: int = MOD) -> int:
    """p 是質數、b 不是 p 的倍數時，b 的模反元素。"""
    return power(b, p - 2, p)


assert power(2, 10, 1000) == 24
assert power(3, 0, 7) == 1 and power(5, 3, 1) == 0
assert power(7, 10**18, MOD) == pow(7, 10**18, MOD)
assert 3 * inverse(3) % MOD == 1 and inverse(3) == pow(3, -1, MOD)
assert 12 * inverse(4) % MOD == 3                  # 12 / 4 在模意義下仍是 3
assert (2 - 5) % MOD == MOD - 3                    # Python 的 % 回傳非負數
assert pow(3, -1, 10) == 7                         # 3 · 7 = 21 ≡ 1 (mod 10)
try:
    pow(4, -1, 6)                                  # gcd(4, 6) = 2，沒有反元素
    raise AssertionError("should not reach")
except ValueError:
    pass
print("all tests passed")
```

**面試時的建議**。Python 內建的 `pow(a, e, m)` 就是快速冪，實際寫題目時可以直接用；但面試官問到 50 題（核心題 4）或要求「不要用內建函式」時，要能寫出上面的迴圈並解釋每一行。另外，`power` 中 `result = 1 % m` 處理了 m = 1 的情況（任何數 mod 1 都是 0），這種邊界在面試中很少被問到，但寫出來能展現細心。

## 28.5 GCD、質數篩與組合數

**GCD（最大公因數）**。歐幾里得演算法依據 gcd(a, b) = gcd(b, a mod b)：任何同時整除 a 和 b 的數，也整除 a − qb = a mod b，反之亦然，所以兩組數的公因數完全相同。每兩步 a 至少減半，時間 O(log min(a, b))。最小公倍數 lcm(a, b) = a / gcd(a, b) · b，先除再乘可以在 C++／Java 中避免溢位。擴展歐幾里得演算法同時找出 x、y 使 ax + by = gcd(a, b)，它是 `pow(b, -1, m)` 的底層原理，也用來解「兩個水壺能不能量出 z 公升」（365. Water and Jug Problem：z 是 gcd 的倍數且不超過兩壺容量和）。

**質數篩（Sieve of Eratosthenes）**。要找出 [2, n] 的所有質數，從 2 開始，每遇到一個還沒被劃掉的數 p，它一定是質數，然後把 p 的倍數全部劃掉。兩個細節讓它變快：只需要讓 p 跑到 √n，因為每個合數 c ≤ n 都有一個 ≤ √c 的質因數；劃倍數時從 p² 開始，因為更小的倍數 kp（k < p）已經被 k 的某個質因數劃過。總工作量是 Σ n/p（p 為質數），等於 O(n log log n)，實務上幾乎是線性的。

**分解質因數與最小質因數篩**。單一一個數 n 的質因數分解用試除法：從 d = 2 試到 √n，能整除就一直除，最後剩下的若大於 1 也是質因數，O(√n)。如果要分解很多個 ≤ N 的數，就先用篩法記錄每個數的最小質因數 spf，之後每次分解只要反覆除以 spf，O(log n)。因數個數可以從質因數分解得到：n = p₁^e₁ · … · p_k^e_k 的因數個數是 (e₁ + 1)…(e_k + 1)，難題 4 會用到它。

**組合數**。C(n, k) 在 n 小（≤ 1000 左右）時可以用 Pascal 三角形 C(n, k) = C(n−1, k−1) + C(n−1, k) 做 DP，O(n²)，模數不必是質數。n 大而且要很多次查詢時，預先算好 0..N 的階乘與階乘的反元素，C(n, k) = n! · (k!)⁻¹ · ((n−k)!)⁻¹，每次 O(1)，前處理 O(N)：先算 N! 的反元素，再用 (i−1)!⁻¹ = i!⁻¹ · i 往回推，只需要一次快速冪。Python 的 `math.comb` 會算出精確的大整數，n 到幾千時沒問題，但 n 到 10⁶ 又要取模時太慢。

```python
from math import comb, gcd as math_gcd, isqrt


def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def ext_gcd(a: int, b: int) -> tuple[int, int, int]:
    """回傳 (g, x, y)，滿足 a·x + b·y = g = gcd(a, b)。"""
    if b == 0:
        return a, 1, 0
    g, x, y = ext_gcd(b, a % b)
    return g, y, x - (a // b) * y


def sieve(n: int) -> list[bool]:
    """is_prime[i] 表示 i 是否為質數，0 <= i <= n。"""
    is_prime = [False, False] + [True] * (n - 1) if n >= 1 else [False] * (n + 1)
    p = 2
    while p * p <= n:
        if is_prime[p]:
            for multiple in range(p * p, n + 1, p):
                is_prime[multiple] = False
        p += 1
    return is_prime


def factorize(n: int) -> dict[int, int]:
    """試除法分解質因數，O(√n)。"""
    factors, d = {}, 2
    while d * d <= n:
        while n % d == 0:
            factors[d] = factors.get(d, 0) + 1
            n //= d
        d += 1
    if n > 1:
        factors[n] = factors.get(n, 0) + 1
    return factors


class Combinatorics:
    """預處理 0..N 的階乘與反元素，C(n, k) mod p 每次 O(1)。"""

    def __init__(self, N: int, p: int = 10**9 + 7):
        self.p = p
        self.fact = [1] * (N + 1)
        for i in range(1, N + 1):
            self.fact[i] = self.fact[i - 1] * i % p
        self.inv_fact = [1] * (N + 1)
        self.inv_fact[N] = pow(self.fact[N], p - 2, p)
        for i in range(N, 0, -1):
            self.inv_fact[i - 1] = self.inv_fact[i] * i % p

    def C(self, n: int, k: int) -> int:
        if k < 0 or k > n:
            return 0
        return self.fact[n] * self.inv_fact[k] % self.p * self.inv_fact[n - k] % self.p


assert gcd(48, 18) == 6 == math_gcd(48, 18) and gcd(7, 0) == 7
g, x, y = ext_gcd(240, 46)
assert g == 2 and 240 * x + 46 * y == 2
assert [i for i, ok in enumerate(sieve(30)) if ok] == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
assert sieve(0) == [False] and sieve(1) == [False, False]
assert factorize(360) == {2: 3, 3: 2, 5: 1} and factorize(97) == {97: 1} and factorize(1) == {}
cb = Combinatorics(1000)
assert cb.C(10, 3) == 120 and cb.C(5, 7) == 0
assert cb.C(1000, 500) == comb(1000, 500) % (10**9 + 7)
catalan = [cb.C(2 * n, n) * pow(n + 1, -1, cb.p) % cb.p for n in range(6)]
assert catalan == [1, 1, 2, 5, 14, 42]                 # Catalan 數：C(2n, n) / (n + 1)
assert isqrt(10**18) == 10**9 and isqrt(10**18 - 1) == 10**9 - 1
print("all tests passed")
```

最後一行的 `math.isqrt` 值得特別記住：判斷完全平方數或計算 ⌊√n⌋ 時，`int(math.sqrt(n))` 在 n 接近 10¹⁸ 時會因為浮點誤差差 1，`isqrt` 是精確的整數平方根。

## 28.6 面試中的數學題：打表、猜規律、證明

數學題最讓人緊張的是「我不知道公式」。好消息是面試官通常也不期待你背過公式，而是想看你能不能**有系統地找到結構**。一個可靠的流程是：先寫最直接的暴力解，把小的輸入跑出來（打表），觀察答案的規律，提出猜想，最後用一兩句話證明猜想。暴力解同時也是你的測試工具。

以 319. Bulb Switcher 為例：n 個燈泡一開始全關，第 r 輪把編號是 r 的倍數的燈泡全部切換，做完 n 輪後有幾盞亮著？n 到 10⁹，模擬是 O(n log n) 而且記憶體不夠。先寫模擬，跑 n = 1..20，得到 `1 1 1 2 2 2 2 2 3 3 …`，答案在 n = 1、4、9、16 時增加，看起來是 ⌊√n⌋。證明：第 i 盞燈被切換的次數等於 i 的因數個數；因數成對出現（d 和 i/d），只有完全平方數的 √i 和自己配對，所以只有完全平方數的因數個數是奇數，最後亮著。≤ n 的完全平方數有 ⌊√n⌋ 個。

```python
from math import isqrt


def bulbs_brute(n: int) -> int:
    on = [False] * (n + 1)
    for r in range(1, n + 1):
        for i in range(r, n + 1, r):
            on[i] = not on[i]
    return sum(on)


def bulb_switch(n: int) -> int:
    return isqrt(n)


table = [bulbs_brute(n) for n in range(1, 21)]
assert table == [1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4]
assert all(bulbs_brute(n) == bulb_switch(n) for n in range(0, 300))
assert bulb_switch(10**9) == 31622
print("all tests passed")
```

```text
打表 → 猜規律 → 證明（319）
n:       1 2 3 4 5 6 7 8 9 10 … 15 16 17
答案:     1 1 1 2 2 2 2 2 3  3 …  3  4  4
跳升點:   1     4         9          16       ← 完全平方數
猜想：答案 = ⌊√n⌋
證明：燈 i 被切換「i 的因數個數」次；因數成對 (d, i/d)，
      只有完全平方數有一個自己配對的 √i → 切換奇數次 → 亮
```

這個流程在本章用了兩次：難題 4（829）從代數式出發，打表後發現答案是奇因數的個數；難題 5（1611）用 BFS 打表，發現操作規則就是 Gray code。面試時把流程說出來很重要：「我先用暴力解跑小的 n 找規律」不是放棄，而是很多資深工程師面對陌生問題時的真實做法。只要最後能給出證明（或至少是有說服力的理由），並用暴力解驗證公式，這就是一個完整的答案。

另外兩個常見的數學結構也值得記住。第一是**不變量（invariant）與奇偶性**：操作前後某個量的奇偶或 mod k 不變，就能判斷「可不可能」，例如 Nim 類遊戲的勝負（292 題：n 是 4 的倍數則先手必輸）。第二是**對稱與配對**：把答案的元素兩兩配對，像燈泡的因數配對、XOR 的成對抵消、難題 4 中 2n = k(2a + k − 1) 的因數配對。看到「奇數個」「剩下一個」時，往配對的方向想通常有收穫。

## 28.7 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 對負數做「右移到 0」或 `n &= n - 1` 的迴圈 | Python 中負數有無限多個 1，迴圈永遠不結束 | 題目要 32 位元語意時先 `n &= 0xFFFFFFFF`，或限定迴圈 32 次 |
| 以為 `~x` 是 32 位元反轉 | `~5` 得到 -6 而不是 4294967290 | 需要固定寬度時寫 `x ^ 0xFFFFFFFF` 或 `~x & 0xFFFFFFFF` |
| 用 `bin(x).count("1")` 或 `bit_count()` 數負數的二補數 | 回傳的是絕對值的 1 的個數 | 先 `x & 0xFFFFFFFF` 再數 |
| 結果需要是有號 32 位元整數卻忘了轉回 | 137 題答案是負數時回傳一個很大的正數 | 第 31 位是 1 就減 `2³²`（`to_signed32`） |
| 在 C／Java 寫 `x & 1 == 0` | 實際上是 `x & (1 == 0)`：C 中恆為 0，Java 直接編譯錯誤 | 一律寫 `(x & 1) == 0`；Python 雖然正確，習慣加括號 |
| 快速冪的 n 為負數，或 n = −2³¹ | 迴圈不結束；Java 中 `-n` 溢位仍是負數 | 先轉成 `x = 1 / x`、`n = -n`，Java 中用 `long` 存 n |
| 模運算中直接做除法 | `(a / b) % m` 得到錯的答案或浮點數 | 乘模反元素 `pow(b, m - 2, m)`（m 為質數）或 `pow(b, -1, m)` |
| 模數不是質數卻用費馬小定理求反元素 | 反元素錯誤，答案錯 | 改用 `pow(b, -1, m)`；不互質時改用 Pascal 三角形 |
| 篩法外層跑到 n、內層從 2p 開始 | 正確但慢好幾倍，n = 5 × 10⁶ 時可能超時 | 外層 `p * p < n` 就停，內層從 `p * p` 開始 |
| 用 `int(math.sqrt(n))` 判斷完全平方數 | n 接近 10¹⁸ 時誤差 1 | 用 `math.isqrt(n)`，再檢查 `r * r == n` |
| 用浮點數算組合數或大數除法 | `math.factorial(50) / ...` 精度不足 | 全部用整數：`math.comb`、`//`，或模反元素 |

## 核心題 1｜136. Single Number｜Easy

### 題目

給一個非空的整數陣列 `nums`，其中**每個元素都恰好出現兩次，只有一個元素出現一次**，請找出那個只出現一次的元素。要求時間 O(n)、額外空間 O(1)。限制：`1 <= len(nums) <= 3 × 10⁴`，元素介於 `-3 × 10⁴` 到 `3 × 10⁴`，而且保證恰好一個元素只出現一次。

- 範例 1：`nums = [2, 2, 1]`，回傳 `1`。
- 範例 2：`nums = [4, 1, 2, 1, 2]`，回傳 `4`。成對的數不一定相鄰。
- 範例 3（邊界）：`nums = [1]`，只有一個元素，回傳 `1`。
- 範例 4（邊界）：`nums = [-3, 7, -3]`，回傳 `7`；負數也要能處理。

### 思路

暴力解是對每個元素再掃一次整個陣列數它出現幾次，O(n²)。用 hash table（或 `Counter`）數一次就好，時間 O(n)，但空間 O(n)。排序後兩兩比對相鄰元素，O(n log n) 時間，而且會修改陣列。還有一個數學做法：`2 · sum(set(nums)) − sum(nums)`，因為每個數在 set 中出現一次、在原陣列中出現兩次，差值就是落單的數；但 `set` 一樣要 O(n) 空間。這些做法的瓶頸都是「記住看過哪些數」，而題目只要求一個答案。

關鍵觀察是 XOR 的三個性質：`a ^ a = 0`、`a ^ 0 = a`、可交換可結合。把所有元素 XOR 起來，可以想像成把它們重新排列，讓相同的數排在一起，每一對都抵消成 0，最後剩下 `0 ^ 0 ^ … ^ single = single`。因為交換律，實際掃描時不需要真的排列，按原順序累積即可。

從位元的角度看更清楚：XOR 在每一位上都是「這一位的 1 出現奇數次就是 1，偶數次就是 0」。成對的數在每一位上貢獻的 1 都是偶數個，所以答案的每一位，正好等於落單那個數的那一位。這個「逐位元看奇偶」的觀點很重要，難題 1 會把它推廣成「逐位元數 mod 3」。負數也沒問題，因為 Python 的 XOR 在無限長的二補數上逐位運算，`-3 ^ -3` 仍然是 0。

```text
nums = [4, 1, 2, 1, 2]
步驟  x    x 的二進位   ans 的二進位   ans
 0    -       -            000          0
 1    4      100           100          4
 2    1      001           101          5
 3    2      010           111          7
 4    1      001           110          6   ← 第二個 1 把 bit0 抵消
 5    2      010           100          4   ← 第二個 2 把 bit1 抵消

逐位元看（每一位 1 的個數）：
        4   1   2   1   2   │ 個數  奇偶  答案位
bit2    1   0   0   0   0   │  1    奇     1
bit1    0   0   1   0   1   │  2    偶     0
bit0    0   1   0   1   0   │  2    偶     0
→ 答案 = 100₂ = 4
```

步驟 3 之後 ans 是 7，看起來和答案無關，這是正常的：中間值是「目前出現奇數次的數」的 XOR，等到它們的另一半出現才會被抵消。逐位元的表格說明了為什麼最後一定正確：每一位只看 1 的個數的奇偶，成對的數貢獻偶數個。

### 解法

```python
import random
from collections import Counter
from functools import reduce
from operator import xor


def single_number(nums: list[int]) -> int:
    ans = 0
    for x in nums:
        ans ^= x
    return ans


def single_number_reduce(nums: list[int]) -> int:
    return reduce(xor, nums, 0)


assert single_number([2, 2, 1]) == 1
assert single_number([4, 1, 2, 1, 2]) == 4
assert single_number([1]) == 1
assert single_number([-3, 7, -3]) == 7
assert single_number([0, -1, 0]) == -1
assert single_number([30000, -30000, 30000]) == -30000
for _ in range(500):
    pool = random.sample(range(-50, 50), random.randint(1, 10))
    single, pairs = pool[0], pool[1:]
    arr = pairs * 2 + [single]
    random.shuffle(arr)
    expect = next(v for v, c in Counter(arr).items() if c == 1)
    assert single_number(arr) == expect == single_number_reduce(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)，每個元素做一次 XOR；空間 O(1)，只用一個變數。邊界情況：只有一個元素時迴圈結束 ans 就是它；答案是 0 時（例如 `[0, 5, 5]`）回傳 0，不需要特判；負數在 Python 中直接運作，在 C++／Java 中也一樣，因為固定寬度的二補數同樣滿足 XOR 的性質。這個解法完全依賴「其他元素恰好出現偶數次」的前提，若前提不成立，XOR 的結果沒有意義，見 F5。

### Follow-up

> [!question]- F1. 如果有兩個元素只出現一次，其他都出現兩次呢（260. Single Number III）？
> 全部 XOR 之後得到 `x = a ^ b`，因為 a ≠ b，x 至少有一位是 1，也就是 a 和 b 在這一位不同。取 `low = x & -x`（最低位的 1），把所有數依照「這一位是不是 1」分成兩組：a 和 b 一定分在不同組，而每一對相同的數一定分在同一組。每組各自 XOR，就分別得到 a 和 b。兩次掃描，O(n) 時間、O(1) 空間。
> ```python
> def single_number_iii(nums):
>     x = 0
>     for v in nums:
>         x ^= v
>     low = x & -x
>     a = 0
>     for v in nums:
>         if v & low:
>             a ^= v
>     return sorted([a, x ^ a])
> ```

> [!question]- F2. 如果其他元素都出現三次（或 k 次）呢？
> XOR 只能抵消偶數次，三次會留下一份。改成逐位元計數：對每一位 i，數所有元素中第 i 位是 1 的個數，取 mod 3；出現三次的數貢獻 0 或 3，mod 3 後消失，剩下的就是答案在第 i 位的值。時間 O(32n)、空間 O(1)；推廣到 k 次時改成 mod k。也可以用兩個變數 `ones`、`twos` 組成的狀態機做到 O(n)，詳見難題 1（137），那裡也處理了負數在 Python 中的轉換。

> [!question]- F3. 如果陣列已經排序，能不能做到 O(log n)（540. Single Element in a Sorted Array）？
> 可以用第 8 章的 binary search。落單元素之前，每一對都從偶數索引開始（`nums[2t] == nums[2t + 1]`）；落單元素之後，配對整體往右移一格，變成從奇數索引開始。所以在「對的索引」t 上，`pred(t) = nums[2t] != nums[2t + 1]` 是 F…F T…T，第一個 True 的 t 就是答案的位置 2t。搜尋範圍是 `[0, n // 2)`，全為 False 時答案是最後一個元素 `nums[n - 1]`。時間 O(log n)。這個例子說明：多了排序這個結構，就不需要逐一 XOR。

> [!question]- F4. 如果其他元素是出現「偶數次」（不一定是兩次），或是給兩個字串找多出來的字元呢？
> 只要其他元素出現偶數次、目標出現奇數次，XOR 的論證完全不變，因為每一位只看 1 的個數的奇偶。389. Find the Difference（t 是 s 打亂後多加一個字元）就是同一題：把兩個字串所有字元的 `ord` XOR 起來，剩下的就是多出來的字元，O(n) 時間、O(1) 空間。反過來，如果有元素出現三次、目標出現一次，XOR 就會失效，要回到 F2 的逐位元計數。

> [!question]- F5. 如果不保證輸入合法，要怎麼確認 XOR 的結果真的是答案？
> XOR 只在前提成立時有意義：輸入 `[1, 2, 3]` 會得到 0，而 0 根本不在陣列中。如果面試官要求驗證，可以再掃一次陣列數 XOR 結果出現的次數，確認它恰好出現一次，仍然是 O(n) 時間、O(1) 空間。但「其他元素都恰好成對」這個前提本身無法在 O(1) 空間內完整驗證，因為那等價於元素唯一性判定，在比較模型下需要 Ω(n log n) 時間或額外空間。面試時說出「XOR 的正確性依賴前提，我可以驗證結果出現一次，但無法便宜地驗證整個前提」就很完整。

## 核心題 2｜268. Missing Number｜Easy

### 題目

給一個長度為 n 的陣列 `nums`，裡面是 `0, 1, …, n` 這 n + 1 個數中的 n 個，**每個數最多出現一次**，所以恰好缺了一個。請回傳缺的那個數。要求時間 O(n)、額外空間 O(1)。限制：`1 <= n <= 10⁴`，`0 <= nums[i] <= n`，元素互不相同。

- 範例 1：`nums = [3, 0, 1]`，n = 3，範圍是 0..3，回傳 `2`。
- 範例 2：`nums = [9, 6, 4, 2, 3, 5, 7, 0, 1]`，n = 9，回傳 `8`。
- 範例 3（邊界）：`nums = [0, 1]`，n = 2，缺的是最大的 `2`。
- 範例 4（邊界）：`nums = [1]`，n = 1，缺的是 `0`。

### 思路

暴力解是對 0..n 的每個數檢查它在不在陣列中，O(n²)。用 set 可以降到 O(n) 時間，但要 O(n) 空間；排序後找第一個 `nums[i] != i` 的位置，O(n log n)。這些做法都在「記住每個數有沒有出現」，但題目只問一個數。

第一個 O(1) 空間的做法是求和：0..n 的總和是 n(n + 1)/2，減去陣列的總和就是缺的數。這在 Python 中完全正確；在 C++／Java 中 n(n + 1)/2 對大的 n 會溢位（本題 n ≤ 10⁴ 不會，但面試官常追問），可以改成邊走邊累加 `i − nums[i]`，讓中間值保持很小。

第二個做法是 XOR，和核心題 1 是同一個想法：把 0..n 的每個「索引」和陣列中的每個「值」全部 XOR 起來。出現在陣列中的數，作為索引一次、作為值一次，恰好成對抵消；缺的數只作為索引出現一次，最後留下來。實作時，索引 0..n−1 來自 `enumerate`，多出來的 n 用 `ans = n` 當初始值。XOR 沒有溢位問題，也是面試官最想看到的答案，因為它把「找缺的數」轉化成核心題 1 的「找落單的數」。

```text
nums = [3, 0, 1]，n = 3
要 XOR 的東西：索引 0, 1, 2, 3（3 是初始值）與值 3, 0, 1

索引:  0   1   2   3
值:    3   0   1
配對:  0↔0  1↔1  3↔3     2 只出現在索引中 → 剩下 2

逐步：
ans = 3（初始值 = n）
i=0  ans ^= 0 ^ 3  → 3 ^ 0 ^ 3 = 0
i=1  ans ^= 1 ^ 0  → 0 ^ 1 ^ 0 = 1
i=2  ans ^= 2 ^ 1  → 1 ^ 2 ^ 1 = 2
結果 2

求和法：0 + 1 + 2 + 3 = 6，sum(nums) = 4，6 − 4 = 2
```

逐步過程中，ans 的中間值沒有直觀意義，重點是最後的「配對表」：除了缺的數，每個數都同時出現在索引列與值列，所以全部 XOR 起來只剩缺的那個。這和核心題 1 的差別只在於「成對」是由我們自己補上的索引造成的。

### 解法

```python
import random


def missing_number(nums: list[int]) -> int:
    ans = len(nums)                      # 索引 n 沒有對應的 enumerate，先放進來
    for i, v in enumerate(nums):
        ans ^= i ^ v
    return ans


def missing_number_sum(nums: list[int]) -> int:
    n = len(nums)
    return n * (n + 1) // 2 - sum(nums)


def missing_number_no_overflow(nums: list[int]) -> int:
    diff = len(nums)
    for i, v in enumerate(nums):
        diff += i - v                    # 中間值始終很小，C++／Java 不會溢位
    return diff


assert missing_number([3, 0, 1]) == 2
assert missing_number([9, 6, 4, 2, 3, 5, 7, 0, 1]) == 8
assert missing_number([0, 1]) == 2
assert missing_number([1]) == 0
assert missing_number([0]) == 1
for _ in range(500):
    n = random.randint(1, 30)
    full = list(range(n + 1))
    miss = random.choice(full)
    arr = [x for x in full if x != miss]
    random.shuffle(arr)
    assert missing_number(arr) == missing_number_sum(arr) == missing_number_no_overflow(arr) == miss
print("all tests passed")
```

### 複雜度與邊界

三種寫法時間都是 O(n)，空間 O(1)。邊界情況：缺 0 時（範例 4）初始值 n 會和值 n 抵消，剩下索引 0；缺 n 時（範例 3）初始值 n 沒有被抵消，正確回傳 n；n = 1 時兩種情況都要測。求和法在 Python 不會溢位，在 C++／Java 中 n 到 10⁵ 時 n(n + 1)/2 約 5 × 10⁹，超過 32 位元，所以面試中用 XOR 或逐步累加 `i − v` 更穩妥。

### Follow-up

> [!question]- F1. 如果缺了兩個數呢（範圍 0..n+1，陣列長度 n）？
> 把索引與值全部 XOR 起來得到 `x = a ^ b`（a、b 是缺的兩個數），接下來和核心題 1 的 F1 一樣：取 `low = x & -x`，把「0..n+1 的所有數」和「陣列中的所有值」都依照這一位分成兩組，各自 XOR 就分別得到 a 和 b。另一個做法是同時求和與平方和：得到 a + b = S 與 a² + b² = Q，解出 a − b = √(2Q − S²)，在 Python 中用 `math.isqrt` 精確計算。兩種都是 O(n) 時間、O(1) 空間；XOR 不會溢位，平方和法在固定寬度整數下要小心。

> [!question]- F2. 如果是 1..n 中有一個數重複、一個數缺失呢（645. Set Mismatch）？
> 把 1..n 和陣列全部 XOR，重複的數出現三次、缺的數出現一次、其他出現兩次，結果是 `dup ^ miss`。用最低位的 1 分組後得到兩個候選值 p、q，再掃一次陣列看哪一個出現過，出現過的就是重複的數。O(n) 時間、O(1) 空間。如果允許修改陣列，也可以把 `nums[|v| − 1]` 標成負數：標記時發現已經是負的，就是重複的數；最後仍是正數的位置就是缺的數，這是第 4 章難題 1（41）「把索引當 hash」的同一招。

> [!question]- F3. 如果陣列已經排序，能不能更快？
> 排序後，缺的數 m 之前每個位置都滿足 `nums[i] == i`，之後都滿足 `nums[i] == i + 1`，所以 `pred(i) = nums[i] != i` 是 F…F T…T，第一個 True 的索引就是缺的數；全部 False 時答案是 n。用第 8 章的 `first_true(0, n, pred)` 直接回傳，O(log n)。這個對比值得說出來：無序時需要 O(n) 看過每個元素，有序時資訊結構讓我們只看 log n 個。

> [!question]- F4. 如果陣列是唯讀的串流，只能讀一次，而且可能有多個數缺失呢？
> 只缺一個時 XOR 或求和都是單趟、O(1) 記憶體，天然適合串流。缺 k 個時，一般做法是維護 k 個冪次和 Σxʲ（j = 1..k），和完整範圍的冪次和相減，得到缺失數的冪次和，再用 Newton 恆等式解出這 k 個數，O(nk) 時間、O(k) 空間；實務上 k 很小時才划算。如果允許 O(n) 位元的空間，直接用一個 bitmap（n + 1 個位元，約 n/8 bytes）記錄出現過的數最簡單。

> [!question]- F5. 如果是 40 億個 32 位元整數存在檔案裡，記憶體只有幾 MB，要找出任何一個沒出現的數呢？
> 這是經典的外部記憶體題。32 位元有 2³² 個可能值，而檔案只有 40 億 < 2³² 個數，所以一定有數沒出現。第一趟：依照高 16 位分成 65536 個桶，只數每個桶的元素個數（65536 個計數器，約 256 KB）；某個桶的個數 < 65536，代表它裡面一定缺數。第二趟：只看高 16 位等於那個桶的數，用 65536 個位元（8 KB）的 bitmap 記錄低 16 位，找到沒被標記的低 16 位即可。兩趟掃描，記憶體 O(√U)，U = 2³²。

## 核心題 3｜191. Number of 1 Bits｜Easy

### 題目

給一個正整數 n，回傳它的二進位表示中 1 的個數（也叫 Hamming weight 或 population count）。限制：`1 <= n <= 2³¹ − 1`。舊版題目把輸入當作 32 位元**無號**整數，範圍到 `2³² − 1`，本書的解法兩者都支援，並在 F2 討論負數。

- 範例 1：`n = 11`，二進位 `1011`，回傳 `3`。
- 範例 2：`n = 128`，二進位 `10000000`，回傳 `1`。
- 範例 3：`n = 2147483645`，二進位是 31 位中只有第 1 位是 0，回傳 `30`。
- 範例 4（邊界）：`n = 0` 回傳 `0`；`n = 2³² − 1`（32 個 1）回傳 `32`。

### 思路

最直接的做法是逐位檢查：看 `n & 1`，然後 `n >>= 1`，重複到 n 變成 0。迴圈次數等於 n 的位元長度，最多 32 次，時間 O(log n)。這已經很快，但面試官通常會追問：「能不能讓迴圈次數只和 1 的個數有關？」例如 n = 2³¹ 只有一個 1，逐位檢查卻要跑 32 次。

關鍵觀察是 28.3 節的 `n & (n − 1)`：它把 n 最低位的 1 變成 0，其他位不變。所以每做一次，1 的個數就恰好少一個；重複到 n 變成 0 的次數，就是 1 的個數。這叫 Brian Kernighan 演算法，迴圈次數是 popcount(n)，對稀疏的數特別快。在 Python 3.10 以後也可以直接用 `n.bit_count()`，或 `bin(n).count("1")`，面試時可以提，但要能寫出 Kernighan 版本並解釋原理。

如果面試官繼續追問「完全不用迴圈呢？」，答案是 SWAR（SIMD within a register）並行計數：把 32 位元看成 16 組 2 位元，先在每組內數 1 的個數，再兩兩相加成 8 組 4 位元，再加成 4 組 8 位元，最後用一次乘法把 4 個 byte 加總。這是硬體 popcount 指令出現之前的標準寫法，五六個運算就完成，與 n 的值無關，見 F3。

```text
Kernighan：n = 44
步驟  n（二進位）  n − 1（二進位）  n & (n − 1)  count
 1     101100        101011          101000        1
 2     101000        100111          100000        2
 3     100000        011111          000000        3
結束 n = 0，回傳 3

每一步：n − 1 把最低位的 1 變成 0、右邊的 0 變成 1
        AND 之後最低位的 1 及其右邊全為 0，左邊不變
逐位檢查需要 6 次迴圈（44 的位元長度），Kernighan 只要 3 次
```

第 1 步 44 = `101100` 的最低位 1 在第 2 位，減 1 後第 2 位變 0、第 0 和 1 位變 1，AND 之後剩 `101000`；第 2、3 步依序消掉第 3 位和第 5 位的 1。迴圈次數剛好是 1 的個數，這就是這個技巧的價值。

### 解法

```python
import random


def hamming_weight(n: int) -> int:
    count = 0
    while n:
        n &= n - 1          # 消掉最低位的 1
        count += 1
    return count


def hamming_weight_shift(n: int) -> int:
    count = 0
    while n:
        count += n & 1
        n >>= 1
    return count


def hamming_weight_swar(n: int) -> int:
    """32 位元的並行計數，不需要迴圈。"""
    n = n - ((n >> 1) & 0x55555555)                    # 每 2 位一組的計數
    n = (n & 0x33333333) + ((n >> 2) & 0x33333333)     # 每 4 位一組
    n = (n + (n >> 4)) & 0x0F0F0F0F                    # 每 8 位一組
    return ((n * 0x01010101) & 0xFFFFFFFF) >> 24       # 四個 byte 加總到最高 byte


assert hamming_weight(11) == 3
assert hamming_weight(128) == 1
assert hamming_weight(2147483645) == 30
assert hamming_weight(0) == 0
assert hamming_weight(2**32 - 1) == 32
assert hamming_weight(-3 & 0xFFFFFFFF) == 31         # 負數先轉成 32 位元無號
for _ in range(2000):
    x = random.getrandbits(32)
    expect = bin(x).count("1")
    assert hamming_weight(x) == hamming_weight_shift(x) == hamming_weight_swar(x) == x.bit_count() == expect
print("all tests passed")
```

### 複雜度與邊界

Kernighan 版本時間 O(popcount(n))，最多 32 次；逐位檢查是 O(log n)；SWAR 是 O(1)（固定幾個運算）。三者空間都是 O(1)。邊界情況：n = 0 時迴圈一次都不執行，回傳 0；32 個 1 時 Kernighan 跑 32 次；Python 中如果輸入是負數，`n &= n − 1` 永遠不會變成 0（-1 & -2 = -2，-2 & -3 = -4，……一直是負數），必須先 `n &= 0xFFFFFFFF`，見 F2。SWAR 最後的乘法在 C 中會自然截斷成 32 位元，Python 要手動 `& 0xFFFFFFFF`。

### Follow-up

> [!question]- F1. 如果要算 0..n 每個數的 1 的個數呢（338. Counting Bits）？
> 對每個數各算一次是 O(n log n)。用 DP 可以做到 O(n)：`bits[i] = bits[i >> 1] + (i & 1)`，因為 i 右移一位就是去掉最低位，1 的個數只差最低位那一個；或者 `bits[i] = bits[i & (i − 1)] + 1`，因為 `i & (i − 1)` 恰好少一個 1 而且比 i 小，已經算過。兩種都是 O(n) 時間、O(n) 空間（輸出本身）。這是第 24 章核心題 2 的題目，那裡從 DP 的角度再講一次。

> [!question]- F2. 如果輸入是有號 32 位元整數，可能是負數，在 Python 要怎麼處理？
> C／Java 中負數的二補數有固定 32 位，例如 -3 是 `11111111111111111111111111111101`，有 31 個 1。Python 的 -3 有無限多個前導 1，所以 Kernighan 和右移迴圈都不會結束，`bin(-3).count("1")` 又只回傳 1（它算的是 `-0b11` 的絕對值部分）。正確做法是先 `n &= 0xFFFFFFFF` 轉成 32 位元的無號表示，再用任何一種方法計數。這是 Python 位元題最常見的陷阱，主動提出來能讓面試官知道你理解語言之間的差異。

> [!question]- F3. 能不能不用迴圈，在常數個運算內算出來？請解釋 SWAR 的原理。
> 第一步 `n − ((n >> 1) & 0x55555555)`：把 32 位分成 16 組 2 位，每組的值 v 減去它的高位，剛好等於這組 1 的個數（`11 − 1 = 10`、`10 − 1 = 01`、`01 − 0 = 01`）。第二步用遮罩 `0x33333333` 把相鄰兩組 2 位的計數加起來，變成 8 組 4 位的計數（每組最多 4，不會溢出）。第三步同理加成 4 組 8 位，最多 8。最後乘以 `0x01010101`，相當於把四個 byte 加到最高的 byte，右移 24 位取出。五個步驟，與 n 的值無關。現代 CPU 有 `popcnt` 指令，C++ 的 `__builtin_popcount`、Java 的 `Integer.bitCount` 會直接用它。

> [!question]- F4. 如果要算兩個數的 Hamming distance，或陣列中所有數對的 Hamming distance 總和呢？
> 兩個數的 Hamming distance（461）是 `popcount(x ^ y)`，因為 XOR 恰好在兩數不同的位上是 1。所有數對的總和（477. Total Hamming Distance）如果兩兩計算是 O(n² · 32)；改成逐位元統計：第 i 位有 c 個數是 1、n − c 個是 0，這一位對總和的貢獻是 c · (n − c)，因為每一對「一個 1 一個 0」貢獻 1。總時間 O(32n)。這種「把數對問題拆成每一位獨立計數」的想法，和難題 1 的逐位元計數是同一個工具。

> [!question]- F5. 如果要把 32 位元整數的位元順序反轉呢（190. Reverse Bits）？
> 逐位做：迴圈 32 次，每次 `result = (result << 1) | (n & 1)`、`n >>= 1`，O(32)。注意必須固定跑 32 次，而不是跑到 n 變成 0，否則 n 的高位 0 不會被放到結果的低位，例如 1 反轉後應該是 `2³¹`。如果同一個函式被呼叫很多次，可以預先建 256 個 byte 的反轉表，把 32 位拆成 4 個 byte 分別查表再交換位置；或用和 SWAR 類似的分治交換：先交換相鄰 16 位、再交換相鄰 8 位……最後交換相鄰 1 位，共 5 步。

## 核心題 4｜50. Pow(x, n)｜Medium

### 題目

實作 `my_pow(x, n)`，計算浮點數 x 的整數 n 次方 xⁿ。n 可以是負數或 0。限制：`-100.0 < x < 100.0`，`-2³¹ <= n <= 2³¹ − 1`，保證 x 不為 0 或 n > 0，而且答案的絕對值不超過 10⁴。面試中通常要求不能直接用內建的 `**` 或 `pow`。

- 範例 1：`x = 2.0, n = 10`，回傳 `1024.0`。
- 範例 2：`x = 2.1, n = 3`，回傳約 `9.261`。
- 範例 3：`x = 2.0, n = -2`，回傳 `0.25`，因為 2⁻² = 1 / 2²。
- 範例 4（邊界）：`n = 0` 時回傳 `1.0`；`x = 1.0, n = -2³¹` 回傳 `1.0`；`x = -1.0, n = -2³¹` 回傳 `1.0`（偶數次方）。

### 思路

暴力解是把 x 連乘 |n| 次，n 到 2³¹ 時需要 21 億次乘法，太慢。瓶頸是我們一次只讓指數加 1，但乘法有更強的結構：x^(2k) = (x^k)²。所以只要知道 x^k，一次平方就能讓指數加倍。

遞迴的想法：xⁿ = (x^(n/2))²（n 偶數）或 x · (x^((n−1)/2))²（n 奇數）。每層指數減半，深度 ⌊log₂ n⌋ + 1，每層一兩次乘法，總共 O(log n)。要注意每層**只能遞迴呼叫一次**、把結果存起來再平方；如果寫成 `my_pow(x, n // 2) * my_pow(x, n // 2)`，每層會分裂成兩個呼叫，總呼叫次數回到 O(n)。

迭代的想法更直接：把 n 寫成二進位，例如 13 = 1101₂，則 x¹³ = x⁸ · x⁴ · x¹。從 `base = x` 開始，每輪把 base 平方，依序得到 x¹、x²、x⁴、x⁸；n 的最低位是 1 就把目前的 base 乘進答案，然後 n 右移一位。負指數先轉換：xⁿ = (1/x)^(−n)。在 Python 中 −(−2³¹) 不會溢位；在 C++／Java 中 `-n` 對 `INT_MIN` 會溢位，必須先轉成 64 位元整數，這是這題最經典的陷阱。

```text
x = 3，n = 13 = 1101₂
輪次  n（二進位）  最低位  result           base（平方前）
 1      1101        1      1 · 3¹ = 3¹      3¹ → 平方得 3²
 2       110        0      3¹               3² → 3⁴
 3        11        1      3¹ · 3⁴ = 3⁵     3⁴ → 3⁸
 4         1        1      3⁵ · 3⁸ = 3¹³    3⁸ → 3¹⁶（之後不再使用）
結束 n = 0，result = 3¹³ = 1594323
乘法次數：4 次平方 + 3 次乘進答案 = 7 次，而不是 12 次
```

每一輪 base 都代表 x^(2^i)，而 n 的第 i 位決定要不要乘進答案，所以 result 最後恰好是 n 的二進位中每個 1 所代表的冪的乘積。最後一次平方是多算的，不影響答案；在浮點數中它可能溢位成 `inf`，但因為不會再乘進 result，也不影響結果。

### 解法

```python
import math
import random


def my_pow(x: float, n: int) -> float:
    if n < 0:
        x, n = 1 / x, -n                  # Python 的 int 不會溢位；Java 要先轉成 long
    result = 1.0
    while n:
        if n & 1:
            result *= x
        x *= x
        n >>= 1
    return result


def my_pow_recursive(x: float, n: int) -> float:
    if n < 0:
        return my_pow_recursive(1 / x, -n)
    if n == 0:
        return 1.0
    half = my_pow_recursive(x, n // 2)    # 只遞迴一次，結果重複使用
    return half * half * (x if n & 1 else 1.0)


assert my_pow(2.0, 10) == 1024.0
assert math.isclose(my_pow(2.1, 3), 9.261)
assert my_pow(2.0, -2) == 0.25
assert my_pow(5.0, 0) == 1.0
assert my_pow(1.0, -2**31) == 1.0
assert my_pow(-1.0, -2**31) == 1.0 and my_pow(-1.0, 2**31 - 1) == -1.0
assert my_pow(2.0, -2**31) == 0.0                    # 下溢成 0
assert my_pow(0.0, 5) == 0.0
for _ in range(1000):
    x = random.uniform(-3, 3)
    n = random.randint(-20, 20)
    if x == 0 and n <= 0:
        continue
    expect = x ** n
    assert math.isclose(my_pow(x, n), expect, rel_tol=1e-9, abs_tol=1e-12)
    assert math.isclose(my_pow_recursive(x, n), expect, rel_tol=1e-9, abs_tol=1e-12)
print("all tests passed")
```

### 複雜度與邊界

時間 O(log |n|)，n 到 2³¹ 時最多 32 輪；迭代版空間 O(1)，遞迴版 O(log |n|) 的呼叫堆疊。邊界情況：n = 0 時迴圈不執行，回傳 1.0；n = −2³¹ 在 Python 中取負不溢位，Java／C++ 必須用 `long`；x = −1 時依 n 的奇偶回傳 ±1；x = 0 且 n < 0 是除以零，題目保證不會出現，實作中 `1 / x` 會丟出例外；中間的 `x *= x` 可能溢位成 `inf` 或下溢成 0，只要那個值最後沒有被乘進答案就無妨，而題目保證答案在 10⁴ 以內。

### Follow-up

> [!question]- F1. 如果要算 aᵇ mod m，而且 b 是一個用十進位數字陣列表示的超大數呢（372. Super Pow）？
> 整數版本把每次乘法都改成乘完取模，就是 28.4 節的 `power`。b 太大無法轉成整數時，利用 a^(10q + d) = (a^q)¹⁰ · a^d：從 b 的最高位開始，每讀一位數字 d，就把目前的結果做 10 次方再乘上 a^d。b 有 L 位時，總共 O(L) 次 `pow(·, 10, m)` 和 `pow(a, d, m)`，每次 O(log 10) 次乘法，時間 O(L)。
> ```python
> def super_pow(a: int, digits: list[int], m: int = 1337) -> int:
>     result = 1
>     for d in digits:
>         result = pow(result, 10, m) * pow(a, d, m) % m
>     return result
> ```

> [!question]- F2. 如果要算第 n 個 Fibonacci 數 mod 10⁹ + 7，n 到 10¹⁸ 呢？
> DP 一步一步走是 O(n)，太慢。Fibonacci 的轉移可以寫成矩陣：`[F(n+1), F(n)]ᵀ = [[1, 1], [1, 0]] · [F(n), F(n−1)]ᵀ`，所以 F(n) 是這個 2×2 矩陣 n 次方的右上角。用同樣的快速冪，只是把數字乘法換成矩陣乘法，O(8 log n) 次乘法。推廣：任何 k 階線性遞迴（例如 1137 Tribonacci、「每次走 1、2 或 3 步」的走法數）都能寫成 k×k 矩陣，O(k³ log n)。
> ```python
> def fib_mod(n: int, mod: int = 10**9 + 7) -> int:
>     def mul(A, B):
>         return [[(A[0][0] * B[0][0] + A[0][1] * B[1][0]) % mod, (A[0][0] * B[0][1] + A[0][1] * B[1][1]) % mod],
>                 [(A[1][0] * B[0][0] + A[1][1] * B[1][0]) % mod, (A[1][0] * B[0][1] + A[1][1] * B[1][1]) % mod]]
>     result, base = [[1, 0], [0, 1]], [[1, 1], [1, 0]]
>     while n:
>         if n & 1:
>             result = mul(result, base)
>         base = mul(base, base)
>         n >>= 1
>     return result[0][1]
> ```

> [!question]- F3. 快速冪和連乘 n 次，在浮點精度上有什麼差別？
> 直覺上「乘法次數少，誤差就小」，但這是錯的。每次浮點乘法帶來約 ε ≈ 1.1 × 10⁻¹⁶ 的相對誤差；連乘 n 次時，n 個誤差各自只出現一次，最壞上界約 nε，而且正負常常互相抵消，實際誤差通常更接近 √n · ε。快速冪的問題在平方：(x(1 + δ))² ≈ x²(1 + 2δ)，每平方一次相對誤差就加倍，最早產生的誤差會被後面約 log₂ n 次平方放大約 n 倍，所以最壞上界同樣是 O(nε)，而且沒有抵消的效果。實測 x ≈ 1、n = 10⁵ 時，快速冪的相對誤差約是連乘的數百倍。另外，x 本身的表示誤差 δ 在 xⁿ 中一定會被放大成約 nδ，這是問題本身的病態性（conditioning），跟用哪種演算法無關。所以快速冪的價值是速度而不是精度；這題的測試允許相對誤差，答案又限制在 10⁴ 以內，兩種精度都夠用。真的需要高精度時，可以用 `decimal` 模組提高位數，或在 x 是有理數時用 `fractions.Fraction` 精確計算後再轉回浮點數。

> [!question]- F4. 在 Python 中用快速冪算精確的大整數（例如 3 的 10⁶ 次方），複雜度還是 O(log n) 嗎？
> 乘法次數仍是 O(log n)，但大整數的每次乘法不是 O(1)：3^(10⁶) 約有 160 萬個十進位位數，最後幾次平方的成本主導全部。若 d 位數乘法的成本是 M(d)（Python 對大數用 Karatsuba，約 d^1.585），總成本約 M(n log 3) 的常數倍，因為各輪的位數是幾何級數。這就是為什麼計數題要「每一步取模」：取模讓每次乘法都是固定大小的數。面試時說出「乘法次數 O(log n) 不等於時間 O(log n)」，能展現你對位元複雜度的理解。

> [!question]- F5. 反過來，如果要算整數平方根或 n 次方根呢（69. Sqrt(x)）？
> 整數平方根可以用第 8 章的 binary search：找最後一個 `m * m <= x` 的 m，O(log x)。更快的是 Newton 法：`r = (r + x // r) // 2` 從一個 ≥ √x 的初值開始，單調遞減收斂到 ⌊√x⌋，迭代次數約 O(log log x)（每次正確位數加倍）。Python 中直接用 `math.isqrt`，它是精確的；不要用 `int(x ** 0.5)`，x 接近 10¹⁸ 時浮點誤差會讓結果差 1。n 次方根同理，二分的判斷改成 `m ** k <= x`，或用 Newton 法 `r = ((k − 1) r + x // r^(k−1)) // k`。

## 核心題 5｜204. Count Primes｜Medium

### 題目

給一個整數 n，回傳**嚴格小於 n** 的質數個數。質數是大於 1、只能被 1 和自己整除的整數。限制：`0 <= n <= 5 × 10⁶`。

- 範例 1：`n = 10`，小於 10 的質數是 2、3、5、7，回傳 `4`。
- 範例 2：`n = 30`，回傳 `10`（2、3、5、7、11、13、17、19、23、29）。
- 範例 3（邊界）：`n = 0`、`n = 1`、`n = 2` 都回傳 `0`；注意 n = 2 時不包含 2 本身。
- 範例 4（邊界）：`n = 3` 回傳 `1`。

### 思路

暴力解是對每個 k < n 做試除，檢查 2..√k 有沒有能整除 k 的數，單一數 O(√k)，總共 O(n√n)；n = 5 × 10⁶ 時大約 10¹⁰ 次運算，太慢。瓶頸是每個數都獨立地從頭試除，沒有共用資訊：判斷 91 時要試到 7，判斷 98 時又從 2 開始，而「7 的倍數不是質數」這件事其實可以一次標記完。

Eratosthenes 篩法把方向反過來：不是問「k 有沒有因數」，而是「質數 p 會劃掉哪些數」。從 2 開始，如果 p 還沒被劃掉，它就是質數，因為所有比它小的質數都已經劃過它們的倍數，p 卻沒被劃到；接著劃掉 p 的倍數。兩個關鍵優化：**從 p² 開始劃**，因為更小的倍數 kp（k < p）一定有一個小於 p 的質因數，早就被劃過了；**p 只需要跑到 p² < n**，因為每個合數 c < n 都有一個 ≤ √c 的質因數，在那時就被劃掉了。

複雜度是 Σ_{p ≤ √n} (n / p)，而質數倒數和 Σ 1/p ≈ ln ln n，所以是 O(n log log n)。n = 5 × 10⁶ 時 ln ln n ≈ 2.7，幾乎就是線性。在 Python 中，內層迴圈要用 slice assignment `is_prime[p*p::p] = ...` 一次劃掉整串倍數，由 C 層級完成，比 Python 的 for 迴圈快一個數量級；用 `bytearray` 存標記，每個數一個 byte，5 × 10⁶ 只要 5 MB。

```text
n = 30，劃掉 0..29 中的合數
初始：  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29

p = 2（2² = 4 < 30）：從 4 開始每 2 個劃掉
        2  3  ×  5  ×  7  ×  9  × 11  × 13  × 15  × 17  × 19  × 21  × 23  × 25  × 27  × 29
p = 3（3² = 9 < 30）：從 9 開始每 3 個劃掉（6 已經被 2 劃過，所以不必從 6 開始）
        2  3  ×  5  ×  7  ×  ×  × 11  × 13  ×  ×  × 17  × 19  ×  ×  × 23  × 25  ×  ×  × 29
p = 4：已被劃掉，跳過
p = 5（5² = 25 < 30）：從 25 開始，只劃掉 25
        2  3  ×  5  ×  7  ×  ×  × 11  × 13  ×  ×  × 17  × 19  ×  ×  × 23  ×  ×  ×  ×  × 29
p = 6：6² = 36 ≥ 30，停止
剩下：2 3 5 7 11 13 17 19 23 29 → 10 個
```

p = 5 時只劃掉 25，因為 10、15、20 已經分別被 2 或 3 劃過；這就是「從 p² 開始」省下的工作。到 p = 6 就停止，因為任何 < 30 的合數，都有一個 ≤ 5 的質因數，早就被劃掉了。

### 解法

```python
from math import isqrt


def count_primes(n: int) -> int:
    if n < 3:
        return 0
    is_prime = bytearray([1]) * n          # 索引 0..n-1
    is_prime[0] = is_prime[1] = 0
    for p in range(2, isqrt(n - 1) + 1):    # p * p <= n - 1
        if is_prime[p]:
            is_prime[p * p::p] = bytes(len(range(p * p, n, p)))
    return sum(is_prime)


def count_primes_brute(n: int) -> int:
    def is_prime(k):
        if k < 2:
            return False
        d = 2
        while d * d <= k:
            if k % d == 0:
                return False
            d += 1
        return True
    return sum(is_prime(k) for k in range(n))


assert count_primes(10) == 4
assert count_primes(30) == 10
assert count_primes(0) == count_primes(1) == count_primes(2) == 0
assert count_primes(3) == 1
assert count_primes(5) == 2                  # 2、3；不含 5 本身
assert count_primes(10**6) == 78498
assert count_primes(5 * 10**6) == 348513     # 最大規模
for n in range(0, 400):
    assert count_primes(n) == count_primes_brute(n)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n log log n)，空間 O(n)（`bytearray` 每個數一個 byte）。邊界情況：n ≤ 2 時沒有任何質數，直接回傳 0，也避免了 `bytearray` 長度不足時設定索引 1 出錯；「嚴格小於 n」所以陣列長度是 n，索引 n 不在其中；外層上限 `isqrt(n - 1)` 確保只處理 p² ≤ n − 1 的 p，例如 n = 26 時 p 會跑到 5，正確劃掉 25；用 `range(p * p, n, p)` 的長度產生全零的 bytes，正好和 slice 的長度一致，若長度不符 Python 會丟出例外。

### Follow-up

> [!question]- F1. 如果還要對很多個數做質因數分解呢？能不能做到每個數只被劃一次？
> 線性篩（Euler sieve）讓每個合數只被它的**最小質因數**劃掉一次，總時間 O(n)，同時得到每個數的最小質因數 spf。做法：對每個 i，遍歷已知質數 p ≤ spf[i]，令 spf[i·p] = p；遇到 p == spf[i] 就停。之後分解任何 x ≤ n 只要反覆除以 spf[x]，O(log x)。實務上 Python 中線性篩因為內層是 Python 迴圈，常數比 slice 版的 Eratosthenes 大，n = 5 × 10⁶ 時反而較慢；它的價值在於附帶的 spf。
> ```python
> def linear_sieve(n: int) -> tuple[list[int], list[int]]:
>     spf, primes = [0] * (n + 1), []
>     for i in range(2, n + 1):
>         if spf[i] == 0:
>             spf[i] = i
>             primes.append(i)
>         for p in primes:
>             if p > spf[i] or i * p > n:
>                 break
>             spf[i * p] = p
>     return primes, spf
> ```

> [!question]- F2. 如果要數 [L, R] 之間的質數，R 到 10¹²，但 R − L ≤ 10⁶ 呢？
> 用分段篩（segmented sieve）。先用普通篩法找出 ≤ √R = 10⁶ 的所有質數；再開一個長度 R − L + 1 的標記陣列代表 [L, R]，對每個小質數 p，從 max(p², ⌈L/p⌉·p) 開始在區間內劃掉 p 的倍數。最後記得把 0 和 1 標成非質數（若 L ≤ 1）。時間 O(√R log log R + (R − L) log log R)，空間 O(√R + R − L)。
> ```python
> def primes_in_range(lo: int, hi: int) -> list[int]:
>     from math import isqrt
>     r = isqrt(hi)
>     is_small = bytearray([1]) * (r + 1)            # 先用普通篩法找出 <= √hi 的質數
>     is_small[:2] = b"\x00\x00"[: r + 1]
>     for p in range(2, isqrt(r) + 1):
>         if is_small[p]:
>             is_small[p * p::p] = bytes(len(range(p * p, r + 1, p)))
>     mark = bytearray([1]) * (hi - lo + 1)
>     for p in (i for i in range(2, r + 1) if is_small[i]):
>         start = max(p * p, (lo + p - 1) // p * p)
>         mark[start - lo::p] = bytes(len(range(start, hi + 1, p)))
>     for x in (0, 1):
>         if lo <= x <= hi:
>             mark[x - lo] = 0
>     return [lo + i for i, ok in enumerate(mark) if ok]
> ```

> [!question]- F3. 如果 n 到 10⁹，記憶體只有幾十 MB 呢？
> 一個 byte 存一個數需要 1 GB，太多。三個層次的優化：只存奇數（2 單獨處理），空間減半；用 bitset 每個數一個位元，再除以 8；最根本的是分段篩，把 [0, n) 切成長度約 2¹⁸ 的區塊（剛好放進 CPU cache），每個區塊用 F2 的方法處理，只需要 O(√n) 的小質數表加一個區塊的記憶體。分段篩不只省記憶體，也因為 cache 命中率高而更快，這是實務上篩到 10⁹ 以上的標準做法。

> [!question]- F4. 如果只要判斷一個很大的數（例如 10¹⁸ 以內）是不是質數呢？
> 篩法不適用，試除到 √n = 10⁹ 也太慢。標準做法是 Miller–Rabin 機率性測試：把 n − 1 寫成 2ˢ · d，對底數 a 檢查 a^d ≡ 1 或某個 a^(2ʳd) ≡ −1 (mod n)，不滿足就一定是合數。對 64 位元範圍內的 n，只要用前 12 個質數（2 到 37）當底數，結果就是確定性的。每個底數 O(log n) 次模乘法，總共 O(k log n)。面試中通常只需要說出名稱與想法，並知道它依賴快速冪（核心題 4）。

> [!question]- F5. 如果 n 到 10¹¹，只要數質數個數、不需要列出它們呢？
> 篩法是 O(n)，太慢。有專門的質數計數演算法：Legendre 公式的改良 Meissel–Lehmer，以及實作較簡單的 Lucy_Hedgehog 方法（對所有形如 ⌊n/k⌋ 的值做類似篩法的 DP），時間約 O(n^(3/4))，n = 10¹¹ 約 10⁸ 次運算。這超出一般面試的範圍，但若面試官問「篩法是不是最佳」，能指出「列出所有質數需要 Ω(n / log n) 的輸出，但只計數可以做到次線性」，就是一個很好的回答。

## 難題 1｜137. Single Number II｜Medium

### 題目

給一個整數陣列 `nums`，其中**每個元素都恰好出現三次，只有一個元素出現一次**，找出那個元素。要求時間 O(n)、額外空間 O(1)。限制：`1 <= len(nums) <= 3 × 10⁴`，元素是 32 位元有號整數（`-2³¹ <= nums[i] <= 2³¹ − 1`），保證恰好一個元素出現一次。

- 範例 1：`nums = [2, 2, 3, 2]`，回傳 `3`。
- 範例 2：`nums = [0, 1, 0, 1, 0, 1, 99]`，回傳 `99`。
- 範例 3（邊界）：`nums = [-2, -2, 1, 1, -3, 1, -3, -3, -4, -2]`，回傳 `-4`；答案是負數時要回傳負數，不是它的 32 位元無號值。
- 範例 4（邊界）：`nums = [7]`，回傳 `7`。

### 提示

> [!tip]- 提示 1
> 核心題 1 的 XOR 之所以有效，是因為它在每一位上做「1 的個數 mod 2」。這題的其他元素出現三次，你需要在每一位上做什麼？

> [!tip]- 提示 2
> 對每一位 i，數所有元素中第 i 位是 1 的個數，取 mod 3。出現三次的數貢獻 0 或 3，mod 3 後消失，剩下的就是答案的第 i 位。在 Python 中，第 31 位是 1 代表答案是負數，要轉換。

> [!tip]- 提示 3
> 想要一趟 O(n) 完成：每一位需要一個 mod 3 的計數器（0、1、2 三種狀態），用兩個位元 `(twos, ones)` 表示。把 32 個位的計數器並排在兩個整數 `ones`、`twos` 裡，推導出 `ones = (ones ^ x) & ~twos`、`twos = (twos ^ x) & ~ones`。

### 詳解

**為什麼直覺做法不行**。hash table 計數是 O(n) 空間；排序後每三個一組比較是 O(n log n)；`(3 · sum(set(nums)) − sum(nums)) / 2` 也需要 set。直接套用核心題 1 的 XOR 會失敗：出現三次的數 XOR 三次等於它自己，不會抵消，最後得到的是所有不同元素的 XOR，沒有意義。關鍵是要理解 XOR 真正在做的事：**它是每一位上的 mod 2 計數器**。換成 mod 3 計數器，就能抵消出現三次的數。

**突破點一：逐位元 mod 3**。對每一位 i（0..31），數陣列中第 i 位為 1 的元素個數 cᵢ。出現三次的數，對 cᵢ 的貢獻是 0 或 3；落單的數貢獻 0 或 1。所以 cᵢ mod 3 恰好是答案的第 i 位。這個做法時間 O(32n)、空間 O(1)，最容易解釋，也最容易推廣到「其他元素出現 k 次」。在 Python 中，`(x >> i) & 1` 對負數會讀到二補數的位元（因為負數有無限多個前導 1，第 0..31 位就是 32 位元二補數），所以計數本身是對的；但組出來的答案是 `[0, 2³²)` 的無號數，若第 31 位是 1，要減掉 2³² 轉回負數。

**突破點二：狀態機一趟完成**。每一位需要一個在 0 → 1 → 2 → 0 之間循環的計數器，遇到 1 就前進一格、遇到 0 不動。用兩個位元 (twos, ones) 編碼這三個狀態：00、01、10。把 32 位的計數器並排，`ones` 這個整數的第 i 位就是第 i 個計數器的低位，`twos` 是高位。轉移規則：讀到 x 的某一位是 1 時，00 → 01 → 10 → 00。可以驗證這兩行恰好實現它：先更新 `ones = (ones ^ x) & ~twos`（twos 為 1 時 ones 必須保持 0），再用**新的** ones 更新 `twos = (twos ^ x) & ~ones`。

**正確性與負數**。三種狀態逐一代入（x 的該位為 1）：00 時 ones = 1 & ~0 = 1、twos = 1 & ~1 = 0，得 01；01 時 ones = 0 & ~0 = 0、twos = 1 & ~0 = 1，得 10；10 時 ones = 1 & ~1 = 0、twos = 0 & ~0 = 0，得 00。x 的該位為 0 時兩式都不變。所有數讀完後，每一位的計數是 cᵢ mod 3，而它只可能是 0 或 1（落單的數只貢獻一次），所以 twos 全是 0、ones 就是答案。這個版本在 Python 中**不需要處理負數**：位元運算在無限長的二補數上逐位進行，所有高位（包括無限多個符號位）都跑同一個狀態機，落單的數若是負的，ones 的無限高位最後也是 1，自然就是負數。

```text
狀態機：每一位的 (twos, ones)，讀到 1 時前進
        讀到 1         讀到 1         讀到 1
  00  ────────▶  01  ────────▶  10  ────────▶  00
 (0 次)         (1 次)         (2 次)        (3 次 = 0 次)

nums = [2, 2, 3, 2]（2 = 10₂，3 = 11₂），只看 bit1、bit0
步驟  x(二進位)   ones   twos   bit1 計數   bit0 計數
 0       -         00     00       0           0
 1      10         10     00       1           0
 2      10         00     10       2           0
 3      11         01     00       0（3）      1
 4      10         11     00       1（4）      1
結束：ones = 11₂ = 3，twos = 00 → 答案 3

逐位元 mod 3 對照：
bit1：2,2,3,2 都有 → 4 個 → 4 mod 3 = 1
bit0：只有 3 有  → 1 個 → 1 mod 3 = 1   → 答案 11₂ = 3
```

步驟 3 讀到 3 = `11` 時，bit1 的計數器從 2 走到 0（第三次），bit0 從 0 走到 1；步驟 4 再讀到 2，bit1 從 0 走到 1。最後 bit1 和 bit0 的計數都是 1，和右邊逐位元計數的結果一致。兩種做法本質相同，狀態機只是把 32 個計數器壓進兩個整數一起更新。

### 解法

```python
import random


def single_number_ii(nums: list[int]) -> int:
    ones = twos = 0
    for x in nums:
        ones = (ones ^ x) & ~twos
        twos = (twos ^ x) & ~ones
    return ones                                   # Python 的負數自動正確


def single_number_ii_bits(nums: list[int]) -> int:
    ans = 0
    for i in range(32):
        count = sum((x >> i) & 1 for x in nums)   # 負數的第 0..31 位就是二補數
        if count % 3:
            ans |= 1 << i
    return ans - (1 << 32) if ans >> 31 else ans  # 第 31 位是 1 → 負數


assert single_number_ii([2, 2, 3, 2]) == 3
assert single_number_ii([0, 1, 0, 1, 0, 1, 99]) == 99
assert single_number_ii([-2, -2, 1, 1, -3, 1, -3, -3, -4, -2]) == -4
assert single_number_ii([7]) == 7
assert single_number_ii([-2**31, 5, 5, 5]) == -2**31
assert single_number_ii_bits([-2, -2, 1, 1, -3, 1, -3, -3, -4, -2]) == -4
assert single_number_ii_bits([2**31 - 1, 0, 0, 0]) == 2**31 - 1
for _ in range(500):
    pool = random.sample(range(-2**31, 2**31), random.randint(1, 8))
    arr = pool[1:] * 3 + [pool[0]]
    random.shuffle(arr)
    assert single_number_ii(arr) == single_number_ii_bits(arr) == pool[0]
print("all tests passed")
```

### 複雜度與邊界

狀態機版本時間 O(n)、空間 O(1)；逐位元版本時間 O(32n)、空間 O(1)。邊界情況：答案是負數時，逐位元版本必須把第 31 位為 1 的結果減去 2³²，否則會回傳 2³² − 4 這種大正數；狀態機版本因為 Python 的無限長二補數而不需要轉換，但如果移植到 Java，兩個版本都直接得到正確的 32 位元結果；答案是 −2³¹ 或 2³¹ − 1 這兩個極值都要測；兩行更新的**順序不能交換**，twos 必須用更新後的 ones。

### Follow-up

> [!question]- F1. 推廣：其他元素都出現 k 次，答案出現 p 次（p 不是 k 的倍數），怎麼找？
> 逐位元計數直接推廣：第 i 位的計數 cᵢ mod k，若不為 0（它會等於 p mod k），答案的第 i 位就是 1。時間 O(32n)，空間 O(1)。負數的轉換和本題相同。這個寫法對任何 k 都成立，是面試時最穩的通用答案。
> ```python
> def single_number_k(nums: list[int], k: int) -> int:
>     ans = 0
>     for i in range(32):
>         if sum((x >> i) & 1 for x in nums) % k:
>             ans |= 1 << i
>     return ans - (1 << 32) if ans >> 31 else ans
> ```

> [!question]- F2. 如果落單的元素出現兩次（其他出現三次）呢？
> 逐位元版本不變：落單元素的位讓 cᵢ mod 3 = 2，條件仍是「不為 0」。狀態機版本中，讀完所有數後，答案的每一位計數器停在狀態 10，也就是 ones 為 0、twos 為 1，所以答案是 `twos` 而不是 `ones`。這個追問用來確認你真的理解狀態機的意義，而不是背了兩行程式：ones 和 twos 分別代表「目前計數為 1」和「目前計數為 2」的位元集合。

> [!question]- F3. 狀態機是怎麼推導出來的？如果 k = 5 要怎麼做？
> 一般方法：k 個狀態需要 ⌈log₂ k⌉ 個位元，k = 5 需要 3 個（b2, b1, b0），狀態 0..4 用二進位編碼。列出真值表：輸入位 x = 0 時狀態不變；x = 1 時狀態 s → (s + 1) mod 5。對每個輸出位元寫出它關於 (b2, b1, b0, x) 的布林式並化簡（可用卡諾圖），再把每個變數換成整數做位元運算，就得到 32 位並行的版本。k = 3 的兩行式子就是這樣化簡出來的。面試中通常寫逐位元計數就足夠，能說出推導方法即可。

> [!question]- F4. 用 (3 · sum(set) − sum) / 2 這個數學做法有什麼問題？
> 它是正確的：set 中每個數出現一次，乘 3 後相當於每個數出現三次，減去原陣列的總和，剩下 2 · 答案。但它需要 O(n) 空間存 set，違反題目要求；在 C++／Java 中總和會溢位（n 個 2³¹ 量級的數）。如果面試官允許 O(n) 空間，它是一行就寫完的好答案；否則就要回到位元的做法。說出這個取捨，比只寫一種解法更完整。

> [!question]- F5. 如果陣列已經排序，能不能比 O(n) 更快？
> 可以用第 8 章的 binary search。排序後，落單元素之前，每組三個相同的數都從 3 的倍數索引開始；落單元素之後，組的起點整體往右移一格。對組號 g（`0 <= g < n // 3`），`pred(g) = nums[3g] != nums[3g + 2]`：答案之前每組完整，pred 為 False；答案所在的組或之後，pred 為 True。第一個 True 的 g 給出答案 `nums[3g]`；全部 False 時答案是最後一個元素。時間 O(log n)，和核心題 1 的 F3（540）是同一個想法。

### 心得

關鍵突破是把 XOR 理解成「每一位的 mod 2 計數器」，於是出現三次就換成 mod 3 計數器；狀態機只是把 32 個計數器並排在兩個整數裡同時更新。它和核心題 1 的關係是同一個框架的兩個參數：k = 2 時計數器只要一個位元，退化成 XOR。面試時建議先講逐位元計數（容易解釋、容易推廣、O(32n) 也是線性），主動提出 Python 的負數轉換，再視時間補上狀態機，並用三個狀態的轉移逐一驗證兩行式子，而不是只說「這是背下來的」。

## 難題 2｜201. Bitwise AND of Numbers Range｜Medium

### 題目

給兩個整數 `left` 和 `right`（`0 <= left <= right <= 2³¹ − 1`），回傳區間 `[left, right]` 中**所有整數**做位元 AND 的結果。

- 範例 1：`left = 5, right = 7`，5 & 6 & 7 = `101 & 110 & 111 = 100`，回傳 `4`。
- 範例 2：`left = 0, right = 0`，回傳 `0`。
- 範例 3（邊界）：`left = 1, right = 2147483647`，區間跨越很多個 2 的冪，回傳 `0`。
- 範例 4：`left = 26, right = 30`，回傳 `24`；`left = right = 6` 時回傳 `6`。

### 提示

> [!tip]- 提示 1
> 直接 AND 整個區間最多要 2³¹ 次運算。試著把 [26, 30] 的每個數寫成二進位、上下對齊，看看哪些位在所有數中都是 1。

> [!tip]- 提示 2
> 從最高位往下看，left 和 right 相同的那一段前綴，在區間內每個數都相同。第一個不同的位以及它右邊的所有位，在區間內一定會出現 0。

> [!tip]- 提示 3
> 答案就是 left 和 right 的共同二進位前綴，後面補 0。可以把兩者同時右移直到相等、再左移回去；或者反覆用 `right &= right − 1` 消掉 right 最低位的 1，直到 right ≤ left。

### 詳解

**為什麼直覺做法不行**。從 left AND 到 right，最多 2³¹ 次運算，太慢。一個常見的小優化是「結果變成 0 就提早停止」，在 left 很小時有效，但對 `left = 2³⁰, right = 2³⁰ + 2²⁹` 這種區間，結果在很久之後才變成 0（或根本不會變成 0），仍然是 O(right − left)。我們需要一個不依賴區間長度的性質。

**突破點：共同前綴**。把 left 和 right 寫成同長度的二進位，從最高位往下找到第一個不同的位 k：在第 k 位上，left 是 0、right 是 1（因為 left ≤ right 且更高位都相同）。令共同前綴為 P，那麼區間內一定包含 `P 0 111…1`（第 k 位為 0、更低位全為 1，它 ≥ left）和 `P 1 000…0`（第 k 位為 1、更低位全為 0，它 ≤ right）這兩個相鄰的數。這兩個數 AND 起來，第 k 位以及更低的每一位都是 0。而高於第 k 位的前綴 P，區間內每個數都相同，AND 之後保留。所以答案就是「P 後面補 0」。

**兩種實作**。第一種：把 left 和 right 同時右移，直到兩者相等，此時剩下的就是共同前綴，再左移回原本的位數。最多 31 次。第二種是 Kernighan 的變形：只要 right > left，就用 `right &= right − 1` 消掉 right 最低位的 1。每消一次，right 變小但仍保持「高位與原本相同」；當 right ≤ left 時，right 恰好只剩共同前綴（因為不同位的那一段已經被消光，而共同前綴中的 1 永遠不會被消到，否則 right 會小於 left 的前綴）。兩種都是 O(log right)；也可以一步算出：`left & ~((1 << (left ^ right).bit_length()) − 1)`，因為 `left ^ right` 的最高位就是第一個不同的位。

```text
left = 26，right = 30
26 = 1 1 0 1 0
27 = 1 1 0 1 1
28 = 1 1 1 0 0
29 = 1 1 1 0 1
30 = 1 1 1 1 0
     ↑ ↑ └─┴─┴── 第 2 位開始 left 與 right 不同：從這裡往右都會出現 0
   共同前綴 11
AND = 1 1 0 0 0 = 24
區間內一定有 27 = 11 0 11 和 28 = 11 1 00，兩者 AND 讓低 3 位全為 0

方法一：同時右移
shift  left   right
  0    11010  11110
  1     1101   1111
  2      110    111
  3       11     11   ← 相等，前綴 = 11
答案 = 11 << 3 = 11000 = 24

方法二：right &= right − 1
right = 11110 (30) > 26 → 11100 (28) > 26 → 11000 (24) ≤ 26，停止，答案 24
```

方法一的第 3 步兩者都變成 `11`，代表共同前綴是 `11`，之後補回 3 個 0。方法二只用兩步就停下：消掉 30 的最低位 1 得到 28，還是比 26 大，再消一次得到 24，已經不大於 26，此時 right 只剩共同前綴。

### 解法

```python
import random
from functools import reduce


def range_bitwise_and(left: int, right: int) -> int:
    shift = 0
    while left != right:
        left >>= 1
        right >>= 1
        shift += 1
    return left << shift


def range_bitwise_and_kernighan(left: int, right: int) -> int:
    while right > left:
        right &= right - 1          # 消掉 right 最低位的 1
    return right


def range_bitwise_and_oneline(left: int, right: int) -> int:
    return left & ~((1 << (left ^ right).bit_length()) - 1)


def brute(left, right):
    return reduce(lambda a, b: a & b, range(left, right + 1))


assert range_bitwise_and(5, 7) == 4
assert range_bitwise_and(0, 0) == 0
assert range_bitwise_and(1, 2**31 - 1) == 0
assert range_bitwise_and(26, 30) == 24
assert range_bitwise_and(6, 6) == 6
assert range_bitwise_and(2**30, 2**30 + 2**29) == 2**30
for _ in range(1000):
    lo = random.randint(0, 3000)
    hi = random.randint(lo, lo + random.choice([0, 1, 5, 50, 500]))
    expect = brute(lo, hi)
    assert range_bitwise_and(lo, hi) == expect
    assert range_bitwise_and_kernighan(lo, hi) == expect
    assert range_bitwise_and_oneline(lo, hi) == expect
print("all tests passed")
```

### 複雜度與邊界

三種寫法時間都是 O(log right)，最多 31 次迴圈；空間 O(1)。邊界情況：left = right 時迴圈不執行，直接回傳 left；left = 0 時答案必為 0（共同前綴為空）；區間跨過 2 的冪（例如 [7, 8]）時最高位就不同，答案為 0；Kernighan 版本的迴圈次數是「right 中低於共同前綴的 1 的個數」，對範例 3 是 31 次。這些寫法都假設非負，負數在 Python 中的行為見 F5。

### Follow-up

> [!question]- F1. 如果改成區間內所有數的 OR 呢？
> 對稱的論證：共同前綴以上的位保持不變；第一個不同的位 k 以及更低的位，因為區間內有 `P 0 111…1` 和 `P 1 000…0`，OR 起來全是 1。所以答案是共同前綴後面補 1：`right | ((1 << (left ^ right).bit_length()) − 1)`。O(1)（或 O(log right) 的迴圈版本）。例如 [26, 30] 的 OR 是 `11111 = 31`。

> [!question]- F2. 如果改成區間內所有數的 XOR 呢？
> XOR 沒有共同前綴的性質，但有可逆性：xor(L..R) = f(R) ^ f(L − 1)，其中 f(n) = 0 ^ 1 ^ … ^ n。f(n) 有週期 4 的規律：n mod 4 為 0、1、2、3 時，f(n) 分別是 n、1、n + 1、0。原因是每組 `4t, 4t+1, 4t+2, 4t+3` 的 XOR 為 0（高位兩兩抵消，低兩位 00^01^10^11 = 0）。O(1)。這和第 7 章的前綴和是同一個想法。
> ```python
> def xor_upto(n: int) -> int:
>     return [n, 1, n + 1, 0][n % 4]
>
> def range_xor(left: int, right: int) -> int:
>     return xor_upto(right) ^ (xor_upto(left - 1) if left > 0 else 0)
> ```

> [!question]- F3. 如果不是連續整數，而是一個陣列，要找某個子陣列的 AND 最接近 target 呢（1521）？
> 枚舉所有子陣列是 O(n²)。關鍵觀察：固定右端點 i，所有以 i 結尾的子陣列 AND 值，隨著左端點往左延伸只會讓位元變少（單調不增），每次改變至少少一個 1，所以最多只有 31 個不同的值。維護一個集合 `cur = {v & nums[i] for v in prev} ∪ {nums[i]}`，大小 ≤ 31，每個 i 更新一次，並對集合中每個值計算與 target 的差。總時間 O(n log V)。同樣的技巧也適用於 OR（898. Bitwise ORs of Subarrays）和 GCD。

> [!question]- F4. 如果要數 [0, n] 中所有數的二進位 1 的總個數呢（n 到 10¹⁸）？
> 逐位元計算：第 i 位的值以週期 2^(i+1) 循環，每個週期中前 2^i 個是 0、後 2^i 個是 1。所以 [0, n] 共 n + 1 個數中，第 i 位為 1 的個數是 `(n + 1) // 2^(i+1) · 2^i + max(0, (n + 1) % 2^(i+1) − 2^i)`。對每一位加總，O(log n)。區間 [L, R] 用 g(R) − g(L − 1)。這是數位計數的入門版，第 24 章的 digit DP（233. Number of Digit One）是十進位的同類問題。
> ```python
> def total_set_bits(n: int) -> int:
>     total, i = 0, 0
>     while (1 << i) <= n:
>         cycle = 1 << (i + 1)
>         total += (n + 1) // cycle * (1 << i) + max(0, (n + 1) % cycle - (1 << i))
>         i += 1
>     return total
> ```

> [!question]- F5. 如果 left 和 right 可以是負數，Python 的寫法會怎樣？
> 若區間包含 0（left < 0 ≤ right），區間裡有 0，答案一定是 0；但兩種迴圈都會出問題：方法一中負數右移最終停在 −1、非負數停在 0，兩者永遠不相等，無窮迴圈；方法二中 right 被消成 0 後仍大於 left，`0 & −1 = 0` 不再變小，也是無窮迴圈。若兩者都是負數，Python 的負數有無限多個前導 1，方法一仍然正確（例如 [−8, −5] 會在右移 2 次後都變成 −2，答案 −8）。所以穩健的寫法是先判斷「區間跨過 0 就回傳 0」，再套用原本的方法；32 位元語意下則先轉成無號數處理。

### 心得

關鍵突破是「區間內第一個不同的位以下，一定同時出現 `0111…1` 和 `1000…0`」，所以答案只取決於 left 和 right 的共同前綴，與區間長度無關。它和本章其他題的關係：核心題 3 的 `x & (x − 1)` 在這裡變成「逐步消掉 right 中不屬於前綴的 1」；F2 的 XOR 版本則用了核心題 1 的抵消性質加上週期規律。面試時先寫出 [26, 30] 的二進位對齊圖，指出共同前綴，再說明那兩個相鄰數的存在性，最後寫右移版本；這張圖本身就是證明。

## 難題 3｜60. Permutation Sequence｜Hard

### 題目

集合 `[1, 2, …, n]` 共有 n! 種排列。把它們依照字典序（lexicographic order）由小到大排好，回傳第 k 個排列（1-indexed），以字串表示。限制：`1 <= n <= 9`，`1 <= k <= n!`。

- 範例 1：`n = 3, k = 3`，排列依序是 `123, 132, 213, 231, 312, 321`，第 3 個是 `"213"`。
- 範例 2：`n = 4, k = 9`，回傳 `"2314"`。
- 範例 3（邊界）：`n = 3, k = 1` 回傳 `"123"`；`n = 3, k = 6` 回傳 `"321"`（最後一個）。
- 範例 4（邊界）：`n = 1, k = 1`，回傳 `"1"`。

### 提示

> [!tip]- 提示 1
> 不要產生前 k − 1 個排列。想想：以 1 開頭的排列有幾個？以 2 開頭的呢？

> [!tip]- 提示 2
> 每個開頭各對應 (n − 1)! 個排列，而且它們在字典序中是連續的一整塊。所以第 k 個排列的開頭，由 (k − 1) // (n − 1)! 決定。

> [!tip]- 提示 3
> 把 k 改成 0-indexed。每一位用 `idx, k = divmod(k, (剩餘個數 − 1)!)`，從剩餘的數字中取出第 idx 小的，放進答案並移除，對剩下的位置重複。這就是階乘進位制。

### 詳解

**為什麼直覺做法不行**。用 backtracking（第 19 章核心題 2）依序產生排列，數到第 k 個就停，最差要產生 n! 個，每個 O(n)，n = 9 時約 3 × 10⁶，勉強可以，但 n 稍大就完全不可行。用 next permutation（31 題）從 `123…n` 開始走 k − 1 步，每步 O(n)，總共 O(kn)，同樣受 k 的大小限制。這些做法的共同問題是**逐一走過**比答案小的排列，而題目真正需要的只是「答案前面有幾個排列」這個數字的結構。

**突破點：整塊跳過**。字典序中，所有以 1 開頭的排列排在最前面，共 (n − 1)! 個；接著是所有以 2 開頭的，也是 (n − 1)! 個；依此類推。所以把 k 轉成 0-indexed 的 r = k − 1 之後，開頭是剩餘數字中第 ⌊r / (n − 1)!⌋ 小的那個，而在這一塊中的排名是 r mod (n − 1)!。第二位同理：剩下 n − 1 個數字，每個各對應 (n − 2)! 個排列。每一步都是一次 divmod，完全不需要列舉。

**為什麼這是進位制**。上面的過程等於把 r 寫成 r = d₁ · (n−1)! + d₂ · (n−2)! + … + d_n · 0!，其中 0 ≤ dᵢ ≤ n − i，這叫階乘進位制（factorial number system），每個 r ∈ [0, n!) 都有唯一的表示，正好對應一個排列。dᵢ 的意義是「第 i 位選剩餘數字中第 dᵢ 小的」，也叫 Lehmer code。用 0-indexed 很重要：若直接用 k，`k // (n−1)!` 在 k 剛好是 (n−1)! 的倍數時會多算一塊，例如 n = 3、k = 2 會錯誤地選到開頭 2。

```text
n = 4，k = 9 → r = 8，剩餘數字 [1, 2, 3, 4]
位置  剩餘數字      區塊大小    divmod(r, 區塊)   取第幾小   答案
 1    [1, 2, 3, 4]   3! = 6     8 = 1·6 + 2         1  → 2     "2"
 2    [1, 3, 4]      2! = 2     2 = 1·2 + 0         1  → 3     "23"
 3    [1, 4]         1! = 1     0 = 0·1 + 0         0  → 1     "231"
 4    [4]            0! = 1     0 = 0·1 + 0         0  → 4     "2314"

字典序中的位置（0-indexed）：
1xxx：0–5   │ 2xxx：6–11  ← r = 8 落在這塊，塊內排名 2
            │   21xx：6–7 │ 23xx：8–9 ← 塊內排名 2 落在這塊，塊內排名 0
            │                 2314：8 ✓
```

第 1 步：r = 8，每個開頭佔 6 個，8 // 6 = 1，跳過 1 開頭的整塊，開頭是 2，剩下的排名是 2。第 2 步：剩下 [1, 3, 4]，每個開頭佔 2 個，2 // 2 = 1，選 3，排名變 0。之後排名為 0，代表剩下的數字照原順序排，得到 "2314"。

### 解法

```python
import random
from itertools import permutations
from math import factorial


def get_permutation(n: int, k: int) -> str:
    digits = [str(i) for i in range(1, n + 1)]
    r = k - 1                                   # 轉成 0-indexed
    out = []
    for remaining in range(n, 0, -1):
        block = factorial(remaining - 1)
        idx, r = divmod(r, block)
        out.append(digits.pop(idx))
    return "".join(out)


assert get_permutation(3, 3) == "213"
assert get_permutation(4, 9) == "2314"
assert get_permutation(3, 1) == "123"
assert get_permutation(3, 6) == "321"
assert get_permutation(1, 1) == "1"
assert get_permutation(9, factorial(9)) == "987654321"
for n in range(1, 7):
    perms = ["".join(p) for p in permutations("123456"[:n])]
    for k in range(1, factorial(n) + 1):
        assert get_permutation(n, k) == perms[k - 1]
print("all tests passed")
```

### 複雜度與邊界

時間 O(n²)：n 步，每步 `list.pop(idx)` 最差 O(n)；n ≤ 9 時這完全不是問題。空間 O(n)。邊界情況：k = 1 時 r = 0，每一步都選最小的，得到 `12…n`；k = n! 時 r = n! − 1，每一步都選最大的，得到 `n…21`；最後一步區塊大小是 0! = 1，idx 一定是 0。最常見的錯誤是沒有把 k 轉成 0-indexed，導致 k 為區塊大小倍數時多跳一塊。

### Follow-up

> [!question]- F1. 反過來：給一個排列，求它在字典序中排第幾（排列的 rank）？
> 對每個位置 i，數它右邊比它小的數字有幾個（這就是 Lehmer code 的 dᵢ），rank = Σ dᵢ · (n − 1 − i)! + 1。直接數是 O(n²)；用 Fenwick tree（第 26 章）從右往左掃，查詢「已加入的數中比 p[i] 小的個數」，O(n log n)。這和第 26 章核心題 2（315. Count of Smaller Numbers After Self）是同一個計數。
> ```python
> from math import factorial
>
> def permutation_rank(p: list[int]) -> int:
>     n, rank = len(p), 0
>     for i in range(n):
>         smaller = sum(1 for j in range(i + 1, n) if p[j] < p[i])
>         rank += smaller * factorial(n - 1 - i)
>     return rank + 1
> ```

> [!question]- F2. 如果 n 到 10⁵，k 是 64 位元整數（≤ 10¹⁸）呢？
> 兩個觀察。第一，20! ≈ 2.4 × 10¹⁸ > 10¹⁸，所以 r < 20!，在階乘進位制中所有 (n − 1 − i)! ≥ 20! 的位置，dᵢ 都是 0，也就是前 n − 20 個位置保持 `1, 2, …, n − 20` 不變，只有最後 20 個位置需要計算。第二，若 k 真的可以到 n!（用大整數表示），每一步「取出第 idx 小的剩餘數字」用 list 是 O(n)，改用 Fenwick tree 或 segment tree 的「找第 k 個 1」操作，每步 O(log n)，總時間 O(n log n)；而大整數的 divmod 本身也有成本，通常會先把 r 轉成階乘進位制的各位數字。

> [!question]- F3. 如果集合中有重複數字，要求第 k 個「不重複的」排列呢？
> 每個開頭對應的區塊大小不再相同，要用多重集合排列數：剩下 m 個字元、各字元個數為 c₁, c₂, … 時，排列數是 m! / (c₁! c₂! …)。每一位依序嘗試每個還有剩的字元（由小到大），算出「選它當這一位」之後的排列數 t；若 k ≤ t 就選它，否則 k −= t 並嘗試下一個。每一位最多嘗試 σ 個字元（σ 是不同字元數），總共 O(n · σ) 次排列數計算。
> ```python
> from collections import Counter
> from math import factorial
>
> def kth_multiset_perm(s: str, k: int) -> str:
>     cnt = Counter(s)
>     def total() -> int:
>         r = factorial(sum(cnt.values()))
>         for v in cnt.values():
>             r //= factorial(v)
>         return r
>     out = []
>     for _ in range(len(s)):
>         for ch in sorted(cnt):
>             if cnt[ch] == 0:
>                 continue
>             cnt[ch] -= 1
>             t = total()
>             if k <= t:
>                 out.append(ch)
>                 break
>             k -= t
>             cnt[ch] += 1
>     return "".join(out)
> ```

> [!question]- F4. 如果只要求「下一個排列」呢？和這題有什麼關係？
> 31. Next Permutation：從右往左找第一個 `p[i] < p[i + 1]` 的位置 i，再從右邊找第一個比 p[i] 大的 p[j]，交換後把 i 右邊反轉，O(n) 時間、O(1) 空間。它對應到階乘進位制中的「r 加 1」：最右邊幾位已經是各自的最大值（遞減段），加 1 會進位，交換與反轉就是在做進位。所以走 k − 1 次 next permutation 是 O(kn)，而本題的 divmod 直接把 r 寫成階乘進位制，O(n²)，兩者算的是同一件事。

> [!question]- F5. 如果改成 [1, n] 所有整數依字典序排列，求第 k 個呢（440. K-th Smallest in Lexicographical Order）？
> 結構從「排列」變成「十叉 trie 的先序走訪」：所有整數依字典序排列，等於在數字前綴樹上做先序走訪。和本題同樣是「整塊跳過」：從前綴 1 開始，計算以目前前綴開頭、而且 ≤ n 的整數有幾個（逐層計算 `min(n + 1, next_prefix) − prefix`，每層乘 10），若 k 大於這個數量就跳到下一個兄弟前綴（prefix + 1），否則往下一層（prefix × 10）。每次計算 O(log n)，最多走 O(log n) 層、每層最多 10 個兄弟，總時間 O(log² n)。

### 心得

關鍵突破是「每個開頭對應連續的一整塊 (n − 1)! 個排列」，所以第 k 個排列可以用一連串 divmod 直接算出，這就是階乘進位制。它和本章其他題的共同精神是**計數取代列舉**：核心題 5 的篩法、難題 4 的代數式都在避免逐一走過。和第 19 章的關係是：backtracking 列出所有排列，這題只要其中一個，所以用計數直接定位。面試時先畫出「1 開頭佔 6 個、2 開頭佔 6 個」的區塊圖，強調 0-indexed 的轉換，再寫程式；被問到反向問題（F1）時，能說出這是同一個進位制的逆運算。

## 難題 4｜829. Consecutive Numbers Sum｜Hard

### 題目

給一個正整數 n，回傳 n **能寫成連續正整數之和的方法數**。一個方法是一段長度 ≥ 1 的連續正整數 `a, a + 1, …, a + k − 1`，其和等於 n；只有一個數 `n` 本身也算一種。限制：`1 <= n <= 10⁹`。

- 範例 1：`n = 5`，5 = 5 = 2 + 3，回傳 `2`。
- 範例 2：`n = 9`，9 = 9 = 4 + 5 = 2 + 3 + 4，回傳 `3`。
- 範例 3：`n = 15`，15 = 15 = 7 + 8 = 4 + 5 + 6 = 1 + 2 + 3 + 4 + 5，回傳 `4`。
- 範例 4（邊界）：`n = 1` 回傳 `1`；`n = 8`（2 的冪）回傳 `1`，只有它自己。

### 提示

> [!tip]- 提示 1
> n 到 10⁹，枚舉起點 a 再往後加是 O(n) 甚至 O(n²)。改成枚舉「有幾項」k：k 項、從 a 開始的連續整數和是多少？

> [!tip]- 提示 2
> 和是 k · a + k(k − 1)/2 = n，所以 a = (n − k(k − 1)/2) / k。a 必須是正整數，這給出 k 的上限與一個整除條件。k 最多到多少？

> [!tip]- 提示 3
> a ≥ 1 等價於 k(k + 1)/2 ≤ n，所以 k ≤ √(2n)，只要枚舉約 44721 個 k。進一步，把式子寫成 2n = k(2a + k − 1)，兩個因數一奇一偶，答案恰好是 n 的奇因數個數。

### 詳解

**為什麼直覺做法不行**。最直接的是枚舉起點 a，從 a 往上累加直到和 ≥ n，O(n²)；用 sliding window（第 6 章）維護一段和，左右指標都只往右移，O(n)。但 n = 10⁹ 時 O(n) 也要十億步，在 Python 中需要數分鐘。問題在於起點 a 的候選有 n 個，而絕大多數起點都不會成功。

**突破點一：改枚舉長度並列出代數式**。k 項、首項 a 的連續整數和是 k · a + (0 + 1 + … + (k − 1)) = k · a + k(k − 1)/2。令它等於 n，得到 a = (n − k(k − 1)/2) / k。對每個 k，方法存在若且唯若這個 a 是正整數：分子必須能被 k 整除，而且 a ≥ 1。a ≥ 1 等價於 n − k(k − 1)/2 ≥ k，也就是 k(k + 1)/2 ≤ n，所以 k < √(2n)。n = 10⁹ 時只要枚舉約 44721 個 k，每個 O(1)，總共 O(√n)。

**突破點二：化簡成奇因數個數**。把等式乘 2：2n = k · (2a + k − 1)。令 p = k、q = 2a + k − 1，則 q − p = 2a − 1 是正奇數，所以 p < q 且兩者一奇一偶。反過來，任何把 2n 拆成 p · q、p < q、一奇一偶的方式，都對應一組合法的 (k, a) = (p, (q − p + 1)/2)。現在數這種拆法：寫 n = 2^e · m（m 為奇數），2n = 2^(e+1) · m。一奇一偶代表 2^(e+1) 必須整個落在其中一個因數，另一個是 m 的某個奇因數 d。每個 d 對應唯一的拆法 {d, 2n/d}，兩者奇偶不同所以不相等，恰好一種順序滿足 p < q。所以**答案 = n 的奇因數個數**。

**驗證與意義**。15 = 3 · 5 的奇因數是 1、3、5、15，答案 4 ✓；9 的奇因數 1、3、9，答案 3 ✓；8 = 2³ 只有奇因數 1，答案 1 ✓，所以「2 的冪不能寫成兩個以上連續正整數之和」。計算奇因數個數：先除掉所有的 2，再用試除法分解 m，套用 (e₁ + 1)(e₂ + 1)… 的因數個數公式，O(√n)。兩種做法複雜度相同，但第二種給出結構性的理解，也能回答 F3、F4 這類追問。

```text
n = 15，枚舉長度 k（條件 k(k+1)/2 ≤ 15 → k ≤ 5）
 k   k(k−1)/2   n − k(k−1)/2   整除 k？   a = (…)/k   序列
 1      0          15             ✓          15        15
 2      1          14             ✓           7        7 + 8
 3      3          12             ✓           4        4 + 5 + 6
 4      6           9             ✗           -        -
 5     10           5             ✓           1        1 + 2 + 3 + 4 + 5
 6     15  → k(k+1)/2 = 21 > 15，停止
答案 4

奇因數觀點：2n = 30 = p · q，p < q 且一奇一偶
 奇因數 d   {d, 30/d}   (p, q)    k = p   a = (q − p + 1)/2
    1        {1, 30}    (1, 30)     1         15
    3        {3, 10}    (3, 10)     3          4
    5        {5, 6}     (5, 6)      5          1
   15        {15, 2}    (2, 15)     2          7
```

第一張表中 k = 4 失敗，因為 9 不能被 4 整除；其他四個 k 都成功。第二張表說明了為什麼答案恰好是奇因數個數：每個奇因數 d 和 30/d 組成一對一奇一偶的因數，較小者是長度 k、較大者決定首項 a。注意 d = 15 時較小的是 2，所以長度是 2 而不是 15。

### 解法

```python
def consecutive_numbers_sum(n: int) -> int:
    count, k = 0, 1
    while k * (k + 1) // 2 <= n:              # 保證首項 a >= 1
        if (n - k * (k - 1) // 2) % k == 0:
            count += 1
        k += 1
    return count


def consecutive_numbers_sum_odd_divisors(n: int) -> int:
    while n % 2 == 0:                          # 去掉 2 的因數，只剩奇數部分 m
        n //= 2
    result, d = 1, 3
    while d * d <= n:
        e = 0
        while n % d == 0:
            n //= d
            e += 1
        result *= e + 1
        d += 2
    if n > 1:                                  # 剩下一個大於 √m 的質因數
        result *= 2
    return result


def brute(n):
    count = 0
    for a in range(1, n + 1):
        s, x = 0, a
        while s < n:
            s += x
            x += 1
        count += s == n
    return count


assert consecutive_numbers_sum(5) == 2
assert consecutive_numbers_sum(9) == 3
assert consecutive_numbers_sum(15) == 4
assert consecutive_numbers_sum(1) == 1
assert consecutive_numbers_sum(8) == 1
assert consecutive_numbers_sum(10**9) == consecutive_numbers_sum_odd_divisors(10**9) == 10
for n in range(1, 400):
    assert consecutive_numbers_sum(n) == consecutive_numbers_sum_odd_divisors(n) == brute(n)
print("all tests passed")
```

### 複雜度與邊界

枚舉長度的版本時間 O(√n)：k 最多約 √(2n) ≈ 44721；奇因數版本也是 O(√n)，但只試奇數，常數約一半。兩者空間 O(1)。邊界情況：n = 1 時只有 k = 1；n 是 2 的冪時奇數部分 m = 1，答案 1；n 是奇質數 p 時奇因數是 1 和 p，答案 2（p 本身和 (p−1)/2 + (p+1)/2）；10⁹ = 2⁹ · 5⁹，奇因數個數是 10。迴圈條件必須是 `k(k + 1)/2 <= n` 而不是 `k <= n`：否則會枚舉到 a ≤ 0 的長度，此時分子 n − k(k − 1)/2 是 0 或負數，卻仍可能被 k 整除（例如 n = 3、k = 3 時分子為 0），於是把不合法的「從 0 或負數開始」的序列也算進去；而且迴圈會退化成 O(n)。

### Follow-up

> [!question]- F1. 如果要列出所有的表示方式呢？
> 用枚舉長度的版本，每個成功的 k 輸出 `range(a, a + k)` 即可。方法數是 n 的奇因數個數 τ(m)，對 n ≤ 10⁹ 最多只有幾百個；但每個表示的長度可達 √(2n)，所以輸出總長度可能到 O(τ(m) · √n)。通常題目會要求輸出 (a, k) 或 (a, b) 的區間端點，這樣總時間仍是 O(√n)。面試時說出「輸出大小可能主導複雜度，所以用端點表示」是很好的細節。

> [!question]- F2. 如果允許 0 和負整數（連續整數即可，不限正數）呢？
> 每個正整數的表示 a, …, b（a ≥ 1）都可以往左延伸成 −(a − 1), …, b：多出來的 −(a−1)..(a−1) 正負抵消，和仍是 n。反過來，任何起點 ≤ 0 的表示（和為正，所以終點 b > 0），抵消掉對稱的部分後會剩下一個正整數表示。這是一對一的對應，而且兩類表示互不重疊，所以答案恰好是 2 × 奇因數個數。例如 n = 1 有 [1] 和 [0, 1] 兩種。O(√n)。

> [!question]- F3. 如果有 10⁵ 個查詢，每個 n ≤ 10⁷ 呢？
> 每次 O(√n) 共 10⁵ × 3162 ≈ 3 × 10⁸，偏慢。先用最小質因數篩（核心題 5 的 F1）預處理到 10⁷，之後每個查詢去掉 2 的因數後，用 spf 在 O(log n) 內分解奇數部分，套因數個數公式。或者直接用類似篩法的方式，對每個奇數 d 把它的所有倍數的計數加 1，預處理 O(N log N)，查詢 O(1)。預處理一次、查詢多次，是數論題常見的取捨。

> [!question]- F4. 判斷 n 能不能寫成「至少兩個」連續正整數之和？
> 至少兩項的方法數是「奇因數個數 − 1」（扣掉只有 n 自己那一種），所以可以若且唯若 n 有大於 1 的奇因數，也就是 n 不是 2 的冪。判斷式是一行 `n & (n − 1) != 0`，O(1)。這是本章位元技巧和數論交會的漂亮例子：28.3 節的 `x & (x − 1)` 判斷 2 的冪，在這裡變成「能不能拆成連續整數」的答案。

> [!question]- F5. 如果 n 到 10¹⁸ 呢？
> O(√n) 是 10⁹ 次，太慢。答案仍是奇因數個數，所以問題變成大數的質因數分解：先用試除法除掉 10⁶ 以下的小質因數，剩下的部分 r 若 > 1，它最多是兩個大質數的乘積（因為 r < 10¹⁸ 且沒有 ≤ 10⁶ 的因數），用 Miller–Rabin（核心題 5 的 F4）判斷 r 是質數、完全平方數，或是兩個不同質數的乘積，分別讓因數個數乘 2、3、4。更一般的做法是 Pollard's rho 分解，期望 O(n^(1/4))。面試中能說出「瓶頸變成分解質因數」就足夠。

### 心得

關鍵突破是改枚舉長度並寫出 a = (n − k(k−1)/2) / k，搜尋空間從 n 縮到 √(2n)；再把 2n = k(2a + k − 1) 看成一奇一偶的因數配對，答案就是奇因數個數。它和 28.6 節的燈泡題是同一種思路：列出代數式，找到因數配對的結構。面試時建議先講 O(n) 的 sliding window 作為基準，再說「改枚舉長度」得到 O(√n) 的版本並寫出來；如果時間允許，再推導奇因數的結論，並用 F4 的「2 的冪」作為漂亮的收尾。

## 難題 5｜1611. Minimum One Bit Operations to Make Integers Zero｜Hard

### 題目

給一個非負整數 n，你可以重複對它的二進位表示做下列兩種操作之一：

- 操作 1：翻轉最低位（第 0 位）。
- 操作 2：翻轉第 i 位（i ≥ 1），前提是第 i − 1 位是 1，而且第 i − 2 位到第 0 位全是 0。

回傳把 n 變成 0 的最少操作次數。限制：`0 <= n <= 10⁹`。

- 範例 1：`n = 3`（`11`），`11 → 01`（操作 2 翻第 1 位）`→ 00`（操作 1），回傳 `2`。
- 範例 2：`n = 6`（`110`），`110 → 010 → 011 → 001 → 000`，回傳 `4`。
- 範例 3（邊界）：`n = 0` 回傳 `0`；`n = 1` 回傳 `1`。
- 範例 4：`n = 2` 回傳 `3`（`10 → 11 → 01 → 00`）；`n = 4` 回傳 `7`。

### 提示

> [!tip]- 提示 1
> 先寫 BFS 暴力解，把 n = 0..16 的答案印出來。觀察 n 是 2 的冪時的答案，以及每個狀態有幾個鄰居。

> [!tip]- 提示 2
> 操作 2 能翻的位是唯一的：最低位的 1 的上一位。所以每個非零狀態恰好有兩個鄰居，整張狀態圖是一條路徑。0 在路徑的一端，答案就是 n 在路徑上的位置。

> [!tip]- 提示 3
> 從 0 出發沿著路徑走，得到的序列 `0, 1, 3, 2, 6, 7, 5, 4, …` 就是 Gray code。位置 i 的 Gray code 是 `i ^ (i >> 1)`，所以答案是它的反函數：`n ^ (n >> 1) ^ (n >> 2) ^ …`。

### 詳解

**為什麼直覺做法不行**。這是一個最短路問題，狀態是整數，邊是兩種操作，直接 BFS 是正確的。但 n 到 10⁹ 時，從 n 到 0 的最短路長度可能接近 2³⁰（例如 n = 2²⁹ 時答案是 2³⁰ − 1），BFS 要拜訪十億級的狀態，時間與記憶體都不夠。這類「規則奇怪、狀態爆炸」的題目，正是 28.6 節「打表找規律」的時機。

**突破點一：狀態圖是一條路徑**。看操作 2 的條件：「第 i − 1 位是 1，且更低位全是 0」，意思是第 i − 1 位就是**最低位的 1**。一個非零的數只有一個最低位的 1，所以操作 2 最多只有一個選擇：翻轉最低位 1 的上一位。加上永遠可用的操作 1，每個非零狀態恰好有兩個鄰居；0 只能做操作 1，只有一個鄰居。兩種操作做兩次都會回到原狀態，所以圖是無向的。每個點度數 ≤ 2、只有 0 的度數是 1 的連通圖就是一條從 0 出發的路徑，而 n 到 0 的最短距離，就是 n 在這條路徑上的位置。

**突破點二：這條路徑就是 Gray code**。從 0 開始交替做操作 1 和操作 2（不能立刻做同一種，否則會走回頭），得到 `0, 1, 3, 2, 6, 7, 5, 4, 12, …`，每一步只改一位，這正是反射二進位 Gray code 的順序：第 i 個 Gray code 是 g(i) = i ^ (i >> 1)。所以答案是 g 的反函數：給定 g，求 i。由 g = i ^ (i >> 1) 可推出 i 的每一位是 g 從最高位到這一位的 XOR（前綴 XOR），也就是 i = g ^ (g >> 1) ^ (g >> 2) ^ …，迴圈 O(log n)。

**另一個推導：遞迴式**。不知道 Gray code 也能從打表得到遞迴。令 f(n) 為答案，打表得到 f(1) = 1、f(2) = 3、f(4) = 7、f(8) = 15，猜測 f(2^k) = 2^(k+1) − 1，因為路徑上 [0, 2^(k+1)) 的狀態恰好排成一段，2^k 在這段的最末端。對最高位為 k 的 n，路徑從 0 走到 2^k 用了 2^(k+1) − 1 步；而 n 位於路徑的「反射」那一半，它到 2^k 的距離等於 n ^ 2^k 到 0 的距離，所以 f(n) = 2^(k+1) − 1 − f(n ^ 2^k)。兩種方法得到相同的答案，面試時能從打表推出遞迴式，就已經是完整的解。

```text
3 位元的狀態圖（每個狀態的兩個鄰居）
位置:   0     1     2     3     4     5     6     7
狀態:  000 ─ 001 ─ 011 ─ 010 ─ 110 ─ 111 ─ 101 ─ 100
操作:     op1   op2   op1   op2   op1   op2   op1
          (翻 bit0)(翻最低位 1 的上一位)

n = 6 = 110 在位置 4 → 答案 4    （110 → 010 → 011 → 001 → 000）
n = 4 = 100 在位置 7 → 答案 7    （2 的冪在一段的末端：2^(k+1) − 1）

反 Gray code：n = 6 = 110₂
i 的最高位   = 1                    = 1
i 的第 1 位  = 1 ^ 1                = 0
i 的第 0 位  = 1 ^ 1 ^ 0            = 0
i = 100₂ = 4 ✓       （迴圈寫法：6 ^ 3 ^ 1 ^ 0 = 4）

遞迴式：f(6) = (2³ − 1) − f(6 ^ 4) = 7 − f(2) = 7 − 3 = 4 ✓
```

狀態圖中，前四個位置 000、001、011、010 是 2 位元的 Gray code，後四個 110、111、101、100 是它們加上最高位後**反過來**排，這就是「反射」的意思，也是遞迴式 f(n) = 2^(k+1) − 1 − f(n ^ 2^k) 的來源：去掉最高位後，位置從尾巴往回數。

### 解法

```python
from collections import deque


def minimum_one_bit_operations(n: int) -> int:
    ans = 0
    while n:                       # 反 Gray code：所有右移版本的 XOR
        ans ^= n
        n >>= 1
    return ans


def minimum_one_bit_operations_recursive(n: int) -> int:
    if n == 0:
        return 0
    k = n.bit_length() - 1         # 最高位
    return (1 << (k + 1)) - 1 - minimum_one_bit_operations_recursive(n ^ (1 << k))


def bfs_distances(bits: int) -> list[int]:
    """從 0 出發 BFS，回傳 [0, 2^bits) 每個狀態的最短距離。"""
    size = 1 << bits
    dist = [-1] * size
    dist[0] = 0
    queue = deque([0])
    while queue:
        s = queue.popleft()
        nexts = [s ^ 1]
        if s:
            nexts.append(s ^ ((s & -s) << 1))   # 操作 2：翻最低位 1 的上一位
        for t in nexts:
            if t < size and dist[t] == -1:
                dist[t] = dist[s] + 1
                queue.append(t)
    return dist


assert minimum_one_bit_operations(3) == 2
assert minimum_one_bit_operations(6) == 4
assert minimum_one_bit_operations(0) == 0
assert minimum_one_bit_operations(1) == 1
assert minimum_one_bit_operations(2) == 3
assert minimum_one_bit_operations(4) == 7
assert minimum_one_bit_operations(2**29) == 2**30 - 1
assert minimum_one_bit_operations(10**9) == minimum_one_bit_operations_recursive(10**9)
dist = bfs_distances(12)
for n in range(1 << 12):
    assert minimum_one_bit_operations(n) == minimum_one_bit_operations_recursive(n) == dist[n]
print("all tests passed")
```

### 複雜度與邊界

迴圈版本時間 O(log n)，最多 30 次；遞迴版本每層去掉一個最高位，深度 ≤ 30，也是 O(log n)。空間 O(1)（遞迴是 O(log n) 的堆疊）。邊界情況：n = 0 直接回傳 0；n 是 2 的冪時答案是 2^(k+1) − 1，是同樣位數中最大的；答案不會超過 2³⁰ − 1，Python 不必擔心溢位。BFS 驗證時限制狀態在 [0, 2^bits) 內是安全的，因為路徑上位置 < 2^bits 的狀態恰好就是所有 bits 位元以內的數。

### Follow-up

> [!question]- F1. 如果要把 a 變成 b（而不是變成 0），最少要幾步？
> 狀態圖是一條路徑，任兩點的最短距離就是位置差：`|G⁻¹(a) − G⁻¹(b)|`，其中 G⁻¹ 是本題的函式。O(log max(a, b))。這是把題目「看成圖」之後最大的收穫：一旦知道整張圖是一條路徑，任何兩點之間的問題都變成位置相減。如果只會遞迴式而沒有看出路徑結構，這個追問就很難回答。

> [!question]- F2. 請產生 n 位元的 Gray code 序列（89. Gray Code）。
> 兩種做法。公式：第 i 個是 `i ^ (i >> 1)`，i 從 0 到 2ⁿ − 1，O(2ⁿ)。反射構造：n 位元的序列 = (n − 1) 位元的序列，接上「它反過來、每個都加上最高位 2^(n−1)」，這就是本題狀態圖中前半段與後半段的關係。兩者產生的序列相同，相鄰兩項都只差一位，而且首尾也只差一位（循環 Gray code）。
> ```python
> def gray_code(n: int) -> list[int]:
>     return [i ^ (i >> 1) for i in range(1 << n)]
> ```

> [!question]- F3. 這題和九連環或 Hanoi 塔有什麼關係？
> 這題的兩種操作正是九連環的規則：第一個環可以隨時上下，其他環只有在「前一個環在上、更前面的環都在下」時才能上下。九連環全部在上的狀態是 n = 2⁹ − 1 = 511，答案是 G⁻¹(511) = `101010101₂` = 341，所以以每次動一個環計算，解開九連環最少需要 341 步。Hanoi 塔的最佳解也和 Gray code 有關：第 t 步移動的盤子編號，等於 t 的最低位 1 的位置，和 Gray code 第 t 步翻轉的位相同。

> [!question]- F4. 反 Gray code 能不能比 O(log n) 次迴圈更快？
> 可以用倍增的前綴 XOR：`n ^= n >> 1; n ^= n >> 2; n ^= n >> 4; n ^= n >> 8; n ^= n >> 16`，對 32 位元的數只要 5 步，O(log log n)。原理是每一步讓「已經累積了 XOR 的位數」加倍：第一步後每一位是自己和上一位的 XOR，第二步後是 4 位的 XOR，依此類推，和第 7 章前綴和的倍增是同一個想法。對任意長度的 Python 整數，把移位量從 1 一直加倍到超過 `bit_length()` 即可。
> ```python
> def inverse_gray(n: int) -> int:
>     shift = 1
>     while shift < n.bit_length():
>         n ^= n >> shift
>         shift <<= 1
>     return n
> ```

> [!question]- F5. 如果 n 以長度 10⁵ 的二進位字串給出，要以二進位字串回傳答案呢？
> 答案的第 i 位（從最高位數）是輸入字串前 i 個字元的 XOR，所以從左到右掃一次，維護一個前綴 XOR 位元並逐位輸出，O(L) 時間、O(L) 輸出空間。不需要把字串轉成大整數；即使轉成 Python 大整數再用 `while n: ans ^= n; n >>= 1`，每一輪都是 O(L) 的大數運算，總共 O(L²)，L = 10⁵ 時是 10¹⁰ 次位元操作，明顯比較慢。這個追問在檢查你是否理解公式的逐位意義，而不是只會套迴圈。

### 心得

關鍵突破是看出操作 2 只有唯一的選擇，於是狀態圖是一條路徑，最短距離就是 n 在路徑上的位置，而這條路徑就是 Gray code。它是本章「打表找規律」的代表：先寫 BFS 跑出小的答案，看出 2 的冪的規律與反射結構，再得到遞迴式或公式，最後用 BFS 驗證。面試時不必一開始就說出 Gray code；從「每個狀態只有兩個鄰居」講到「圖是一條路徑」，再寫出遞迴式 f(n) = 2^(k+1) − 1 − f(n ^ 2^k)，就已經是完整且有說服力的解法。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| XOR 抵消 | 成對出現、找落單或缺失、O(1) 空間 | `a ^ a = 0`，必要時用 lowbit 分組 | 核心題 1（136）、核心題 2（268）、260、389、645 |
| 逐位元計數 | 其他元素出現 k 次；數對的位元差異總和 | 每一位的 1 的個數 mod k；每位獨立貢獻 c·(n − c) | 難題 1（137）、477 Total Hamming Distance |
| 最低位技巧 | 1 的個數、2 的冪、子集合枚舉、Fenwick tree | `x & (x − 1)` 消最低位、`x & −x` 取最低位 | 核心題 3（191）、231、338（第 24 章）、第 26 章 |
| 位元前綴與區間 | 區間 [L, R] 的 AND／OR／XOR | 共同前綴；XOR 的週期 4 與前綴可逆性 | 難題 2（201）、1486、1521 |
| 固定寬度模擬 | 要求 32 位元語意、不用加減號、負數 | `& 0xFFFFFFFF`、第 31 位判斷正負 | 371 Sum of Two Integers、190 Reverse Bits |
| 位元表示集合 | n ≤ 20 的子集合、狀態壓縮 | bitmask 狀態、`(sub − 1) & mask` | 第 24 章（526、1986、943）、第 7 章難題 4（1371） |
| XOR 最大化 | 兩數 XOR 最大、限制條件下的最大 XOR | 從高位貪婪 + binary trie | 421、第 13 章難題 3（1707） |
| 快速冪 | 指數到 10⁹ 以上、線性遞迴第 n 項 | 二進位拆解指數；矩陣快速冪 | 核心題 4（50）、372、509、1137 |
| 模運算與組合數 | 「對 10⁹ + 7 取模」「有幾種方法」 | 每步取模、反元素、預處理階乘 | 62 Unique Paths（組合公式）、1359、1922 |
| 質數與因數 | 質數個數、質因數分解、因數個數、GCD | 篩法、試除到 √n、spf 篩、歐幾里得 | 核心題 5（204）、難題 4（829）、365、1979 |
| 進位制與排名 | 第 k 個排列、排列的排名、字典序第 k 個 | 階乘進位制、整塊跳過 | 難題 3（60）、31 Next Permutation、440 |
| 代數化簡 | 單一整數輸入到 10⁹、問方法數或存在性 | 列式化簡、因數配對、奇偶性 | 難題 4（829）、319 Bulb Switcher、292 Nim Game |
| 打表找規律 | 規則奇怪、狀態數爆炸的操作題 | BFS 小 n → 猜遞迴式／公式 → 證明 → 驗證 | 難題 5（1611）、89 Gray Code、319 |

**下限與上限**。最簡單的形式是直接套一個性質：136 的 XOR、191 的 `x & (x − 1)`、231 的 2 的冪判斷，考的是知不知道這個技巧，以及能不能解釋它為什麼成立。中間層需要把性質推廣或組合：137 把 mod 2 推廣成 mod 3、260 用 lowbit 分組、50 把指數拆成二進位、204 用篩法共用工作。上限的題目難在三個地方：第一，**看不出是數學題**，例如 1611 包裝成操作題、829 包裝成計數題，必須先意識到暴力解在數值上列舉，而答案藏在結構裡；第二，**需要一個非顯然的結構觀察**，例如 201 的「兩個相鄰數一定在區間內」、829 的「一奇一偶的因數配對」、1611 的「狀態圖是一條路徑」；第三，**語言與數值細節**，例如 Python 負數的無限前導 1、C++／Java 的溢位、模運算的除法、浮點誤差，這些在面試中往往比演算法本身更容易出錯。

**與其他 pattern 的關係**。位元技巧是許多其他 pattern 的零件：Fenwick tree（第 26 章）的 `i & −i`、bitmask DP（第 24 章）的狀態壓縮、prefix XOR（第 7 章難題 4 用位元記錄母音的奇偶）、binary trie（第 13 章）的最大 XOR。數學工具也一樣：計數 DP（第 21–23 章）的答案要取模、組合數常常是 DP 的封閉解（62 Unique Paths 的答案是 C(m + n − 2, m − 1)）、rolling hash（第 25 章）完全建立在模運算上、二分答案（第 8 章）常需要整數開根號。反過來，本章的題目也會借用其他 pattern：540 和 137 F5 用 binary search，1521 用「以 i 結尾的值集合」的類 DP 技巧，60 的 F1 用 Fenwick tree 計數。

**容易混淆之處**。第一，「出現 k 次」的題目不要一律用 XOR，只有 k 為偶數、目標出現奇數次時 XOR 才成立。第二，「有幾種方法」不一定有公式：如果每一步有依賴前面的選擇，通常是 DP，數學只負責取模；只有當問題有乾淨的代數結構（連續整數和、排列的區塊）時，才能直接計算。第三，看到「質數」不要立刻篩：只判斷一個數用試除或 Miller–Rabin，範圍內很多數才用篩法，區間在很遠的地方用分段篩。第四，Python 的整數不會溢位，不代表可以忽略數字大小：大整數的運算成本隨位數成長，計數題仍然要每步取模。

## 本章重點整理

- XOR 的本質是「每一位的 mod 2 計數器」：成對的數抵消，所以 136 一趟 XOR 解決；其他元素出現 k 次時，改成每一位 mod k（137）。
- `x & (x − 1)` 消掉最低位的 1，用來數 1 的個數（191）、判斷 2 的冪、逐步消去區間的非共同位（201）；`x & −x` 取出最低位的 1，用來分組（260）與 Fenwick tree。
- Python 的整數沒有固定長度，負數有無限多個前導 1：右移與 Kernighan 迴圈對負數不會結束，`~x`、`bin`、`bit_count` 都不是 32 位元語意；需要時用 `& 0xFFFFFFFF`，結果第 31 位為 1 就減 2³²。
- 缺失數字（268）是「索引與值配對」的 XOR，或用求和；固定寬度語言中要注意求和溢位。
- 快速冪把指數寫成二進位，O(log n) 次乘法；遞迴時每層只能呼叫一次；負指數先轉成 1/x，Java／C++ 中 −2³¹ 取負會溢位（50）。
- 模運算：加減乘可以每步取模，除法要乘模反元素；模數是質數時用 `pow(b, m − 2, m)`，一般情況用 `pow(b, −1, m)`。
- 篩法從 p² 開始劃、p 只跑到 √n，O(n log log n)（204）；多次分解用最小質因數篩，大區間用分段篩，單一大數用 Miller–Rabin。
- 組合數：小 n 用 Pascal 三角形，大 n 多次查詢預處理階乘與反元素；平方根一律用 `math.isqrt`。
- 第 k 個排列用階乘進位制：先轉 0-indexed，每一位一次 divmod，整塊跳過 (n − 1)! 個排列（60）。
- 單一整數輸入到 10⁹ 時，列出代數式、找因數配對或奇偶結構：連續正整數和的方法數等於奇因數個數（829）。
- 規則奇怪的操作題先 BFS 打表，觀察鄰居數、2 的冪的答案、反射結構，再推出遞迴式或公式並用暴力驗證（1611 是 Gray code）。
- 面試時說清楚每個技巧「為什麼成立」，並主動提出語言細節（Python 負數、溢位、浮點誤差），這往往比演算法本身更能展現 L5 的嚴謹度。
