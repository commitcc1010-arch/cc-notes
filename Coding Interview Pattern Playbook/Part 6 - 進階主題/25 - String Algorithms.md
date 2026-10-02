---
chapter: 25
title: 字串演算法：KMP、Rolling Hash 與回文
part: 6
---

# 第 25 章　字串演算法：KMP、Rolling Hash 與回文

> [!abstract] 本章地圖
> **一句話**：字串比對慢，是因為每次失敗都把已經比過的字元丟掉重來；KMP 與 Z-function 把「已經比對過的資訊」存成前綴的自我重疊表，rolling hash 把子字串壓成可以 O(1) 更新的數字，回文則利用「鏡像位置的答案已經知道」來避免重複擴張。
>
> **辨識訊號**：
> - 在長字串中找一個 pattern 的出現位置，n、m 都到 10⁴–10⁵，O(n·m) 會超時
> - 題目在問「前綴等於後綴」「字串由某段重複組成」「最短週期」
> - 「最長的重複子字串」「多個字串的最長共同片段」：長度有單調性，可以二分長度再用雜湊檢查
> - 「每個後綴和整個字串的最長共同前綴」：Z-function 的定義本身
> - 最長／計數回文子字串、在前面補字元變成回文：中心擴張、Manacher，或「回文前綴」轉成 KMP
>
> **核心題**：5、647、28、459、686
>
> **難題**：214、1044、1392、1923、2223

## 25.1 這個 Pattern 解決什麼問題

先看最基本的問題：在文字 `text`（長度 n）裡找 pattern `pat`（長度 m）第一次出現的位置。暴力解是把 pat 對齊 text 的每個起點，逐字比對，失敗就把 pat 往右移一格重來，最差 O(n·m)。最差情況長這樣：`text = "aaaa…ab"`、`pat = "aaab"`，每個起點都要比到 pat 的最後一個字元才發現不同，然後往右移一格，前面比對成功的三個 `a` 全部重比一次。

浪費的根源是：比對失敗時，我們其實已經知道 text 最近的 k 個字元等於 `pat[:k]`，這是可以重複利用的資訊。如果 `pat[:k]` 的某個後綴恰好等於 pat 的某個前綴，那麼 pat 往右移之後，這一段不用重比，可以直接從那個前綴的長度繼續。KMP（Knuth–Morris–Pratt）演算法預先算出 pat 每個前綴「最長的、既是前綴又是後綴的長度」，稱為 failure function 或 prefix function，比對時 text 的指標永遠不後退，總時間 O(n + m)。Z-function 是同一個想法的另一種表達：對每個位置 i，直接記錄「從 i 開始的子字串和整個字串的最長共同前綴」。

第二類工具是 rolling hash（滾動雜湊）。把一個長度 L 的子字串當成一個 B 進位的大數，再取模數 M，就得到一個整數指紋；相鄰兩個窗口的指紋可以 O(1) 互相推出來，於是「比較兩個子字串是否相等」從 O(L) 變成 O(1)（以極小的碰撞機率為代價）。它特別適合「同時比較大量子字串」的題目，例如找最長的重複子字串：把長度二分，每個長度用一個 set 裝下所有窗口的指紋，O(n) 檢查有沒有重複。

第三類是回文。暴力找最長回文子字串要枚舉 O(n²) 個子字串、每個 O(n) 檢查，總共 O(n³)。改成「枚舉中心、往兩邊擴」立刻降到 O(n²) 且只用 O(1) 空間，這是面試最常見的答案；Manacher 演算法再利用「大回文裡的鏡像位置答案相同」把它降到 O(n)。另外，很多回文題可以轉成前綴與後綴的比對，例如「最長的回文前綴」等於「s 的前綴和 reverse(s) 的後綴最長相等多少」，直接用 KMP 解決。

本章的五道核心題各對應一個工具：5 與 647 是中心擴張與 Manacher，28 是 KMP 本身，459 是 failure function 的週期性質，686 是「把問題化成一次子字串搜尋」。五道難題則是上限：214 把回文轉成 KMP，1392 是 failure function 的最後一格，2223 是 Z-function 的總和，1044 與 1923 是「二分長度＋rolling hash」。

## 25.2 辨識訊號

| 題目特徵 | 為什麼是這個工具 | 本章哪一題 |
|---|---|---|
| 在 text 中找 pat 的位置或出現次數，n、m 都很大 | KMP／Z-function 是 O(n + m) 的確定性解；rolling hash 是期望 O(n + m) | 核心題 3（28） |
| 「最長的前綴同時也是後綴」 | 這就是 failure function 最後一格的定義 | 難題 3（1392） |
| 「字串是否由某個子字串重複多次構成」「最短週期」 | 最短週期 = n − π[n−1]，再檢查是否整除 n | 核心題 4（459） |
| 「重複 a 幾次才能讓 b 成為子字串」 | 重複次數有明確上界，化成一次子字串搜尋 | 核心題 5（686） |
| 「每個後綴和原字串的最長共同前綴」 | Z-function 的定義 | 難題 5（2223） |
| 「最長的出現兩次以上的子字串」「多個序列的最長共同片段」 | 長度 L 可行則 L − 1 也可行，二分長度；每個長度用 rolling hash 的 set 檢查 | 難題 2（1044）、難題 4（1923） |
| 最長回文子字串、回文子字串個數 | 每個回文由中心決定，枚舉 2n − 1 個中心擴張；要 O(n) 就用 Manacher | 核心題 1（5）、核心題 2（647） |
| 「在前面補最少字元變成回文」 | 等價於求最長回文前綴，用 s 與 reverse(s) 做 KMP | 難題 1（214） |

反向檢查：如果題目要的是 **subsequence**（可以跳著選），例如最長回文子序列、最長共同子序列，那是第 22、23 章的 DP，本章的工具都只處理**連續**的子字串。

## 25.3 模板一：KMP 的 failure function

**定義**。對字串 s，`pi[i]` 是 `s[:i+1]`（長度 i + 1 的前綴）的**最長真 border** 長度。border 是「既是前綴、又是後綴」的子字串，「真」代表不能是整個字串本身。例如 `s[:5] = "aabaa"` 的 border 有 `"a"`、`"aa"`，最長是 2，所以 `pi[4] = 2`。

**為什麼這個表有用**。比對時如果 text 最近的 k 個字元等於 `pat[:k]`，下一個字元卻對不上 `pat[k]`，我們要找下一個「仍然可能成功」的對齊方式。新的對齊必須讓 pat 的某個前綴對上 text 最近的那些字元，而那些字元就是 `pat[:k]` 的後綴，所以新的匹配長度一定是 `pat[:k]` 的某個 border。最長的 border 就是 `pi[k-1]`，次長的 border 是 `pi[pi[k-1]-1]`，依此類推：**一個字串的所有 border，就是沿著 `pi` 一路往回跳得到的那條鏈**。這個性質讓建表和比對都能用同一個「失敗就沿鏈回跳」的迴圈。

**怎麼建表**。假設已經知道 `pi[i-1] = k`，也就是 `s[:k]` 是 `s[:i]` 的最長 border。要算 `pi[i]`，就看 border 能不能往右延長一格：如果 `s[i] == s[k]`，新的 border 長度是 k + 1；否則退到次長的 border `k = pi[k-1]` 再試，直到成功或 k 變成 0。下面一步一步建 `s = "aabaaab"` 的表：

```text
s:      a  a  b  a  a  a  b
index:  0  1  2  3  4  5  6

i=1  k=pi[0]=0  比 s[1]=a 與 s[0]=a，相等 → k=1             pi[1]=1   border "a"
i=2  k=pi[1]=1  比 s[2]=b 與 s[1]=a，不等 → k=pi[0]=0
                比 s[2]=b 與 s[0]=a，不等，k 已是 0          pi[2]=0
i=3  k=pi[2]=0  比 s[3]=a 與 s[0]=a，相等 → k=1             pi[3]=1   border "a"
i=4  k=pi[3]=1  比 s[4]=a 與 s[1]=a，相等 → k=2             pi[4]=2   border "aa"
i=5  k=pi[4]=2  比 s[5]=a 與 s[2]=b，不等 → k=pi[1]=1        （退到 "aa" 的最長 border "a"）
                比 s[5]=a 與 s[1]=a，相等 → k=2             pi[5]=2   border "aa"
i=6  k=pi[5]=2  比 s[6]=b 與 s[2]=b，相等 → k=3             pi[6]=3   border "aab"

pi:     0  1  0  1  2  2  3

i=5 的回跳畫成圖：
  s[:5] = a a b a a      目前 border 長度 2："aa" … "aa"
                         想延長成 "aab" 但 s[5] = a ≠ s[2] = b
  "aa" 的最長 border 是 "a"（pi[1] = 1），改試延長 "a" → "aa"，s[5] = a == s[1] = a，成功
```

`i = 5` 是整個演算法的精華：延長最長 border 失敗時，不必從頭試所有長度，只要沿著 `pi` 跳到次長的 border，因為介於中間的長度一定不是 border。

**為什麼是 O(n)**。k 每一輪最多加 1，所以 n 輪合計最多加 n；每次回跳 k 至少減 1，k 又不會小於 0，所以所有回跳的總次數也不超過 n。這是一個 amortized（攤銷）論證：單一步可能回跳很多次，但總數有上限。比對階段同理，text 的指標從不後退，總時間 O(n + m)。

```python
import random


def prefix_function(s: str) -> list[int]:
    """pi[i] = s[:i+1] 的最長真 border 長度。"""
    pi = [0] * len(s)
    for i in range(1, len(s)):
        k = pi[i - 1]                      # 目前最長的 border
        while k > 0 and s[i] != s[k]:      # 延長失敗：退到次長的 border
            k = pi[k - 1]
        if s[i] == s[k]:
            k += 1
        pi[i] = k
    return pi


def kmp_search(text: str, pat: str) -> list[int]:
    """回傳 pat 在 text 中所有（可重疊的）出現起點。"""
    if not pat:
        return list(range(len(text) + 1))
    pi = prefix_function(pat)
    res, k = [], 0                         # k = 目前已經對上的 pat 前綴長度
    for i, ch in enumerate(text):
        while k > 0 and ch != pat[k]:
            k = pi[k - 1]
        if ch == pat[k]:
            k += 1
        if k == len(pat):                  # 完整匹配；退到最長 border 繼續找重疊的下一個
            res.append(i - len(pat) + 1)
            k = pi[k - 1]
    return res


def brute_pi(s):
    return [max(L for L in range(i + 1) if s[:L] == s[i + 1 - L:i + 1]) for i in range(len(s))]


assert prefix_function("aabaaab") == [0, 1, 0, 1, 2, 2, 3]
assert prefix_function("ababaca") == [0, 0, 1, 2, 3, 0, 1]
assert prefix_function("") == []
assert prefix_function("aaaa") == [0, 1, 2, 3]
assert kmp_search("abababa", "aba") == [0, 2, 4]          # 可重疊
assert kmp_search("hello", "ll") == [2]
assert kmp_search("aaa", "aaaa") == []
for _ in range(500):
    s = "".join(random.choice("ab") for _ in range(random.randint(0, 12)))
    p = "".join(random.choice("ab") for _ in range(random.randint(1, 3)))
    assert prefix_function(s) == brute_pi(s)
    assert kmp_search(s, p) == [i for i in range(len(s) - len(p) + 1) if s[i:i + len(p)] == p]
print("all tests passed")
```

**每一行為什麼這樣寫**：

- `k = pi[i - 1]`：`pi[i]` 的 border 去掉最後一個字元後，一定是 `s[:i]` 的某個 border，所以只要從 `s[:i]` 的 border 鏈中找「下一個字元也對得上」的最長那個。
- `while k > 0 and s[i] != s[k]`：`s[k]` 正是長度 k 的 border 後面那個字元，比對它就是在問「這個 border 能不能延長」。
- 比對階段完整匹配後寫 `k = pi[k - 1]` 而不是 `k = 0`：這樣才能找到重疊的出現（`"aba"` 在 `"ababa"` 中出現在 0 和 2）。若題目要不重疊的出現，改成 `k = 0`。
- 另一種常見寫法是對 `pat + "#" + text` 直接建一次 `prefix_function`，`pi` 值等於 m 的位置就是匹配結尾。分隔字元必須不出現在兩個字串中，否則 border 會跨過分隔處；上面的串流寫法不需要分隔字元，也只用 O(m) 額外空間。

## 25.4 模板二：Z-function

**定義**。`z[i]` 是 s 和 `s[i:]` 的最長共同前綴長度。本書約定 `z[0] = n`（整個字串和自己完全相同），有些資料把它定為 0，使用前要確認。例如 `s = "aabxaab"`：

```text
s:      a  a  b  x  a  a  b
index:  0  1  2  3  4  5  6
z:      7  1  0  0  3  1  0

z[4] = 3：s[4:] = "aab" 和 s 的前 3 個字 "aab" 相同
z[1] = 1：s[1:] = "abxaab"，第一個字 a 相同，第二個 b ≠ a
```

**Z-box**。暴力算每個 `z[i]` 是 O(n²)。加速的關鍵是維護目前「右端最遠」的匹配區間 `[l, r)`，稱為 Z-box：它代表 `s[l:r] == s[0:r-l]`。當 i 落在 box 內，`s[i:r]` 等於 `s[i-l:r-l]`，而後者從 `i - l` 開始和 s 的共同前綴已經算過，是 `z[i-l]`。所以 `z[i]` 至少是 `min(r - i, z[i-l])`；只有當這個值碰到 box 的右端 r 時，才需要往外逐字比較，而每次往外比較成功都會把 r 往右推。

```text
s = a a b x a a b，算到 i = 5 時，Z-box 是 [l, r) = [4, 7)（由 z[4] = 3 產生）

index:     0  1  2  3  4  5  6
s:         a  a  b  x  a  a  b
                      └─ box ─┘       s[4:7] == s[0:3]
i = 5 的鏡像位置是 i - l = 1，z[1] = 1，r - i = 2
→ z[5] 至少 min(2, 1) = 1；1 < r - i，答案已經在 box 內決定，不必再往外比
→ 從 z[5] = 1 開始試延長：s[1] = a vs s[6] = b，不等，z[5] = 1
```

總時間是 O(n)：每次逐字比較成功都讓 r 增加 1，r 最多到 n；比較失敗每個 i 最多一次。

```python
import random


def z_function(s: str) -> list[int]:
    """z[i] = s 與 s[i:] 的最長共同前綴長度，約定 z[0] = n。"""
    n = len(s)
    z = [0] * n
    if n:
        z[0] = n
    l = r = 0                              # Z-box [l, r)：s[l:r] == s[:r-l]
    for i in range(1, n):
        if i < r:
            z[i] = min(r - i, z[i - l])    # 借用鏡像位置的答案，但不能超出 box
        while i + z[i] < n and s[z[i]] == s[i + z[i]]:
            z[i] += 1
        if i + z[i] > r:
            l, r = i, i + z[i]
    return z


def brute_z(s):
    out = []
    for i in range(len(s)):
        k = 0
        while i + k < len(s) and s[k] == s[i + k]:
            k += 1
        out.append(k)
    return out


assert z_function("aabxaab") == [7, 1, 0, 0, 3, 1, 0]
assert z_function("aaaaa") == [5, 4, 3, 2, 1]
assert z_function("") == []
assert z_function("abc") == [3, 0, 0]
for _ in range(500):
    s = "".join(random.choice("ab") for _ in range(random.randint(0, 15)))
    assert z_function(s) == brute_z(s)
print("all tests passed")
```

**KMP 與 Z 怎麼選**。兩者能解的問題幾乎一樣，都是 O(n)：找 pat 在 text 中的位置，可以對 `pat + "#" + text` 算 Z，`z[i] >= m` 的位置就是匹配。習慣上，問題的形狀是「以每個位置**結尾**的前綴匹配」（border、週期、串流比對）時用 prefix function；形狀是「從每個位置**開始**和整個字串比」（每個後綴的 LCP、難題 5）時用 Z-function。面試時挑自己最熟的一個寫熟即可，另一個知道定義與用途。

## 25.5 模板三：Rabin-Karp rolling hash

**把字串變成數字**。把每個字元對應成一個整數（例如 `ord(ch)`），把長度 L 的字串 `c0 c1 … c(L-1)` 視為一個 B 進位數 `c0·B^(L-1) + c1·B^(L-2) + … + c(L-1)`，再對模數 M 取餘數，得到雜湊值。相等的字串雜湊一定相等；不相等的字串雜湊相等稱為碰撞（collision）。

**為什麼能滾動**。窗口往右移一格時，最左邊的字元要拿掉、最右邊加一個新的。拿掉最左邊等於減去 `c0·B^(L-1)`，剩下的每個字元權重乘上 B，再加上新字元：`h' = (h − c0·B^(L-1))·B + c_new (mod M)`，O(1)。下面用 B = 10、不取模、字元 a = 1、b = 2、c = 3 示範，數字就是窗口本身：

```text
s = a b c a b，L = 3，B = 10
窗口 [0,3) "abc" → 1·100 + 2·10 + 3       = 123
窗口 [1,4) "bca" → (123 − 1·100)·10 + 1   = 231
窗口 [2,5) "cab" → (231 − 2·100)·10 + 2   = 312

前綴雜湊 H[i] = s[:i] 的雜湊：H = [0, 1, 12, 123, 1231, 12312]
任意子字串 s[l:r] 的雜湊 = H[r] − H[l]·B^(r−l)
例如 s[2:5] = 12312 − 12·10³ = 312 ✓
```

實務上更常用「前綴雜湊」：預先算 `H[i]` 與 `P[i] = B^i mod M`，任何子字串 `s[l:r]` 的雜湊都是 `(H[r] − H[l]·P[r−l]) mod M`，O(1)。這讓我們能在 O(1) 比較任意兩個子字串，也能比較一個子字串和另一個字串（只要兩者用同一組 B、M）。

**模數與碰撞**。對兩個不同、長度 L 的字串，如果 B 是在 `[0, M)` 中隨機選的、M 是質數，兩者雜湊相等的機率至多 (L − 1)/M，因為「兩字串的差」是一個 B 的 L − 1 次多項式，在模質數下最多 L − 1 個根。單次比較的風險很小，但要注意**比較次數**：把 10⁵ 個窗口放進 set，等於兩兩比較約 5 × 10⁹ 對；若 M ≈ 10⁹，期望碰撞數就是好幾個，答案幾乎一定會錯（這是生日悖論）。所以：

- **大模數**：用 Mersenne 質數 M = 2⁶¹ − 1，碰撞機率約 10⁻¹⁸ 量級，5 × 10⁹ 對也只有約 10⁻⁹ 的總風險。Python 整數不會溢位，直接寫 `% M` 即可；在 C++／Java 要用 128 位元乘法或特殊的取模技巧。
- **雙 hash**：用兩組 (B, M)，例如 M₁ = 10⁹ + 7、M₂ = 998244353，把兩個雜湊值組成 tuple 當 key，碰撞機率大約變成兩者相乘。
- **隨機 base**：B 要隨機選，不要寫死。固定 B 時，出題者可以構造出必定碰撞的字串；寫死 M = 2⁶⁴（靠整數溢位取模）更危險，存在不論 B 是多少都會碰撞的經典構造（Thue–Morse 字串）。
- **驗證**：雜湊相等時再用 `s[i:i+L] == s[j:j+L]` 直接比較一次，就能讓答案永遠正確（Las Vegas 演算法），代價是最差情況可能變慢。面試時說出「雜湊相等時我會再驗證」通常就足夠。

```python
import random

MOD = (1 << 61) - 1                        # Mersenne 質數


class PrefixHash:
    """s 的前綴雜湊；get(l, r) 在 O(1) 回傳 s[l:r] 的雜湊。"""

    def __init__(self, s, base: int):
        n = len(s)
        self.h = [0] * (n + 1)
        self.p = [1] * (n + 1)
        for i, ch in enumerate(s):
            v = ord(ch) if isinstance(ch, str) else ch
            self.h[i + 1] = (self.h[i] * base + v) % MOD
            self.p[i + 1] = self.p[i] * base % MOD

    def get(self, l: int, r: int) -> int:
        return (self.h[r] - self.h[l] * self.p[r - l]) % MOD


def rabin_karp(text: str, pat: str) -> int:
    """回傳 pat 第一次出現的位置；雜湊相等時再驗證，結果一定正確。"""
    n, m = len(text), len(pat)
    if m == 0:
        return 0
    if m > n:
        return -1
    base = random.randrange(256, MOD - 1)
    target = PrefixHash(pat, base).get(0, m)
    top = pow(base, m - 1, MOD)            # 最左邊字元的權重 B^(m-1)
    h = 0
    for i in range(m):
        h = (h * base + ord(text[i])) % MOD
    for i in range(n - m + 1):
        if h == target and text[i:i + m] == pat:
            return i
        if i + m < n:                      # 滾動：移除 text[i]、加入 text[i+m]
            h = ((h - ord(text[i]) * top) * base + ord(text[i + m])) % MOD
    return -1


ph = PrefixHash("abcab", random.randrange(256, MOD - 1))
assert ph.get(0, 2) == ph.get(3, 5)        # "ab" == "ab"
assert ph.get(0, 3) != ph.get(1, 4)        # "abc" != "bca"（碰撞機率可忽略）
assert ph.get(2, 2) == 0                   # 空字串
assert rabin_karp("sadbutsad", "sad") == 0
assert rabin_karp("leetcode", "leeto") == -1
assert rabin_karp("aaab", "ab") == 2
assert rabin_karp("a", "") == 0
for _ in range(300):
    t = "".join(random.choice("ab") for _ in range(random.randint(0, 12)))
    p = "".join(random.choice("ab") for _ in range(random.randint(1, 4)))
    assert rabin_karp(t, p) == t.find(p)
print("all tests passed")
```

**什麼時候 rolling hash 比 KMP 好**。單一 pattern 的搜尋，KMP 是確定性的 O(n + m)，比較好。但當題目要「同時比較大量長度相同的子字串」（例如所有長度 L 的窗口有沒有重複、多個字串有沒有共同的長度 L 片段），KMP 無從下手，rolling hash 卻能把每個窗口變成一個整數丟進 set。另外，rolling hash 可以 O(1) 比較**任意兩個**子字串，配合 binary search 就能 O(log n) 求任意兩個後綴的最長共同前綴，這是很多進階題的零件。

## 25.6 模板四：回文——中心擴張與 Manacher

**中心擴張（expand around center）**。每個回文都有一個中心：奇數長度的中心是一個字元，偶數長度的中心是兩個字元之間的縫隙，長度 n 的字串共有 2n − 1 個中心。固定中心後，往兩邊同時擴張，只要兩端字元相同就繼續；一旦不同，以這個中心的回文就到此為止，因為更長的回文必須包含這對不相同的字元。每個中心最多擴張 O(n) 次，總共 O(n²) 時間、O(1) 空間。比起「枚舉子字串再檢查」的 O(n³)，中心擴張的省力之處是：同一個中心的所有回文是**巢狀**的，檢查最長的那一個時，順便確認了所有比較短的。

**Manacher 的直覺：鏡像**。中心擴張的浪費在於，大回文的右半邊和左半邊完全對稱，左半邊每個中心的擴張結果其實已經算過。設目前右端最遠的回文是以 c 為中心、覆蓋到 r。對於 c 右邊、r 以內的中心 i，它的鏡像位置是 `j = 2c − i`。在大回文內，i 附近的字元和 j 附近的字元是鏡像相同的，所以 i 的回文半徑至少是 `min(r − i, 半徑[j])`；只有碰到 r 的時候，才需要往外逐字擴張，而每次擴張成功都會把 r 往右推。這和 Z-function 的 Z-box 是同一種攤銷論證：r 只會往右走，總共 O(n)。

```text
s = a b a c a b a，只看奇數長度回文，d[i] = 以 i 為中心的最長回文半徑（含中心）
index:  0  1  2  3  4  5  6
s:      a  b  a  c  a  b  a
d:      1  2  1  4  1  2  1

算完 i = 3 時，最右回文是中心 c = 3、覆蓋 [0, 6]，r = 6
i = 4：鏡像 j = 2，d[2] = 1，離右端還有 r − i + 1 = 3 格 → d[4] = 1，不需擴張
i = 5：鏡像 j = 1，d[1] = 2，"bab" 完全在大回文內 → d[5] 至少 2
       試著往外擴：左邊 s[3] = c、右邊 s[7] 超出字串 → d[5] = 2
i = 6：鏡像 j = 0，d[0] = 1 → d[6] = 1，右邊已到盡頭

         ┌────── 大回文 [0, 6] ──────┐
index:   0   1   2   3   4   5   6
         a  [b]  a   c   a  [b]  a
             j ←── 鏡像 ──→ i
```

**統一奇偶：插入分隔字元**。偶數長度的回文中心落在字元之間，直接處理需要兩套陣列。標準技巧是在每個字元之間與兩端插入 `#`，再在最前後放兩個不同的哨兵 `^`、`$`：`"abba"` 變成 `"^#a#b#b#a#$"`，所有回文都變成奇數長度、中心都是一個字元。在轉換後的字串 t 上，`p[i]` 定義為以 i 為中心、往單邊擴張的長度，它恰好等於原字串中對應回文的長度；原字串中的起點是 `(i − p[i] − 1) // 2`。哨兵讓擴張迴圈不必檢查邊界，因為 `^` 和 `$` 不會和任何字元相等。前提是原字串不包含這三個符號，否則要換成其他不會出現的字元。

```python
import random


def manacher(s: str) -> list[int]:
    """回傳轉換字串 t = '^#' + '#'.join(s) + '#$' 上的 p 陣列。
    p[i] = 以 t[i] 為中心的回文在原字串中的長度。"""
    t = "^#" + "#".join(s) + "#$"
    p = [0] * len(t)
    c = r = 0                              # 目前右端最遠的回文：中心 c、右端 r
    for i in range(1, len(t) - 1):
        if i < r:
            p[i] = min(r - i, p[2 * c - i])        # 借用鏡像位置的答案
        while t[i + p[i] + 1] == t[i - p[i] - 1]:  # 哨兵保證不會越界
            p[i] += 1
        if i + p[i] > r:
            c, r = i, i + p[i]
    return p


def longest_pal_center(s: str) -> str:
    def expand(lo: int, hi: int) -> tuple[int, int]:
        while lo >= 0 and hi < len(s) and s[lo] == s[hi]:
            lo, hi = lo - 1, hi + 1
        return lo + 1, hi                  # 回文是 s[lo+1:hi]

    best = (0, 0)
    for c in range(len(s)):
        for lo, hi in (expand(c, c), expand(c, c + 1)):
            if hi - lo > best[1] - best[0]:
                best = (lo, hi)
    return s[best[0]:best[1]]


def longest_pal_manacher(s: str) -> str:
    p = manacher(s)
    i = max(range(len(p)), key=p.__getitem__)
    start = (i - p[i] - 1) // 2
    return s[start:start + p[i]]


def count_pal(s: str) -> int:
    return sum((v + 1) // 2 for v in manacher(s))


assert manacher("abba") == [0, 0, 1, 0, 1, 4, 1, 0, 1, 0, 0]
assert longest_pal_manacher("abacaba") == "abacaba"
assert longest_pal_manacher("cbbd") == "bb"
assert longest_pal_manacher("") == ""
assert count_pal("aaa") == 6
for _ in range(500):
    s = "".join(random.choice("ab") for _ in range(random.randint(0, 12)))
    subs = [s[i:j] for i in range(len(s)) for j in range(i + 1, len(s) + 1)]
    pals = [x for x in subs if x == x[::-1]]
    best = max((len(x) for x in pals), default=0)
    a, b = longest_pal_center(s), longest_pal_manacher(s)
    assert len(a) == len(b) == best and a == a[::-1] and b == b[::-1] and a in s and b in s
    assert count_pal(s) == len(pals)
print("all tests passed")
```

`count_pal` 為什麼是 `(v + 1) // 2`：以 t 中某個位置為中心、原長度為 v 的最長回文，往內縮每次減 2，得到長度 v、v − 2、…，直到 1 或 2，共 ⌈v / 2⌉ 個回文；中心是 `#` 時 v 是偶數（或 0），中心是字元時 v 是奇數，公式都成立。

面試中，中心擴張幾乎總是期待的答案：程式短、O(1) 空間、容易說明。Manacher 適合當作 follow-up「能不能 O(n)」的回答，能說出「鏡像位置的半徑可以直接借用，只有碰到右端才需要擴張，右端只往右走所以總共 O(n)」，就已經展現了理解；能寫出來是加分。

## 25.7 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 建 failure function 時回跳寫成 `k = pi[k]` | 跳到錯的 border，表的值偏大或 index 越界 | 長度 k 的 border 的最長 border 是 `pi[k - 1]`，「長度」與「索引」差 1 |
| 完整匹配後把 k 歸零 | 找不到重疊的出現，例如 `"aa"` 在 `"aaa"` 中只找到一次 | 找所有出現時寫 `k = pi[k - 1]`；只有題目要求不重疊才歸零 |
| `pat + text` 串接時沒有分隔字元 | border 跨過接縫，π 值大於 m，判斷錯誤 | 用不會出現的分隔字元（如 `"#"`），或改用串流比對 |
| Z-function 忘了 `min(r - i, z[i - l])` 的 `r - i` | 借用的值超出 Z-box，z 值偏大 | box 外的字元沒有比對過，只能信任 box 內的部分 |
| rolling hash 用小模數又放進 set | 大量窗口時生日碰撞，答案隨機錯 | 用 2⁶¹ − 1 或雙 hash；必要時雜湊相等再驗證 |
| 固定 base 或依賴 2⁶⁴ 溢位 | 遇到刻意構造的測資必定碰撞 | base 隨機選、模數用質數 |
| 滾動時減法後沒有取模（其他語言） | 出現負數雜湊，相等的字串雜湊不同 | `(h - x * top) % M` 在 Python 永遠非負；Java／C++ 要再加 M |
| 中心擴張只考慮奇數中心 | `"abba"`、`"cbbd"` 這類偶數回文漏掉 | 每個 c 都試 `(c, c)` 與 `(c, c + 1)` |
| Manacher 原字串包含 `#` 或哨兵字元 | 回文跨過分隔字元被誤判 | 先確認字元集，或改用不會出現的字元／整數陣列 |
| 把 subsequence 題當成 substring 題 | 516 最長回文子序列用中心擴張，答案偏小 | 先確認題目要的是連續子字串還是可跳選的子序列（後者是第 23 章的 DP） |

## 核心題 1｜5. Longest Palindromic Substring｜Medium

### 題目

給一個字串 `s`，回傳它最長的回文子字串（連續的一段，正著讀和倒著讀相同）。如果有多個一樣長的答案，回傳任意一個即可。限制：`1 <= len(s) <= 1000`，`s` 只包含英文字母與數字。

- 範例 1：`s = "babad"`，回傳 `"bab"`（`"aba"` 也是正確答案）。
- 範例 2：`s = "cbbd"`，回傳 `"bb"`，最長的回文是偶數長度。
- 範例 3（邊界）：`s = "a"`，回傳 `"a"`；`s = "ac"`，回傳 `"a"` 或 `"c"`，任何單一字元都是回文。
- 範例 4（邊界）：`s = "aaaa"`，回傳 `"aaaa"`，整個字串就是回文。

### 思路

暴力解枚舉所有 O(n²) 個子字串，每個用 O(n) 檢查是否回文，總共 O(n³)，n = 1000 時是 10⁹ 級，太慢。常見的第二個想法是區間 DP：`pal[i][j]` 表示 `s[i..j]` 是否回文，`pal[i][j] = (s[i] == s[j]) and pal[i+1][j-1]`，時間 O(n²) 但要 O(n²) 空間，而且要注意填表順序（必須先填短的區間）。

瓶頸在於暴力解把同一個中心的回文檢查了很多次：檢查 `s[1..5]` 是否回文時，順便已經知道 `s[2..4]` 是回文，卻在另一次枚舉中重新檢查。關鍵觀察是：**回文由中心決定，而且同一個中心的回文是巢狀的**。只要 `s[lo] == s[hi]` 就往外擴一格；一旦不相等，以這個中心的更長回文全都不可能存在，因為它們都包含這對不同的字元。所以每個中心只需要一次擴張，就同時得到了以它為中心的所有回文。

中心有兩種：奇數長度的中心是字元 `(c, c)`，偶數長度的中心是兩個相鄰字元 `(c, c + 1)`，共 2n − 1 個。每次擴張 O(n)，總共 O(n²) 時間、O(1) 空間，和 DP 同樣的時間但不需要表格。如果面試官追問 O(n)，就是 25.6 節的 Manacher。

```text
s = b a b a d
index: 0 1 2 3 4

中心        擴張過程                          回文        長度
(0,0)      b                                 "b"          1
(0,1)      b≠a，停                            ""           0
(1,1)      a → s[0]=b == s[2]=b → 左端越界    "bab"        3   ← 目前最佳
(1,2)      a≠b，停                            ""           0
(2,2)      b → s[1]=a == s[3]=a → s[0]=b≠s[4]=d  "aba"     3   （沒有比 3 長，不更新）
(2,3)      b≠a，停                            ""           0
(3,3)      a → s[2]=b ≠ s[4]=d                "a"          1
(3,4)      a≠d，停                            ""           0
(4,4)      d                                 "d"          1
答案 "bab"
```

中心 (1,1) 擴張到左端越界才停，得到 `"bab"`；中心 (2,2) 擴到 `"aba"` 後，下一對 b 與 d 不同就停下，不必再檢查 `"babad"`。偶數中心在這個例子都立刻失敗，但在 `"cbbd"` 中 (1,2) 會得到 `"bb"`，如果只檢查奇數中心就會漏掉。

### 解法

```python
import random


def longest_palindrome(s: str) -> str:
    def expand(lo: int, hi: int) -> tuple[int, int]:
        while lo >= 0 and hi < len(s) and s[lo] == s[hi]:
            lo -= 1
            hi += 1
        return lo + 1, hi                  # 最後一次成功的回文是 s[lo+1:hi]

    best_lo, best_hi = 0, 0
    for c in range(len(s)):
        for lo, hi in (expand(c, c), expand(c, c + 1)):
            if hi - lo > best_hi - best_lo:
                best_lo, best_hi = lo, hi
    return s[best_lo:best_hi]


def longest_palindrome_manacher(s: str) -> str:
    t = "^#" + "#".join(s) + "#$"
    p = [0] * len(t)
    c = r = 0
    for i in range(1, len(t) - 1):
        if i < r:
            p[i] = min(r - i, p[2 * c - i])
        while t[i + p[i] + 1] == t[i - p[i] - 1]:
            p[i] += 1
        if i + p[i] > r:
            c, r = i, i + p[i]
    i = max(range(len(t)), key=p.__getitem__)
    start = (i - p[i] - 1) // 2
    return s[start:start + p[i]]


def brute(s):
    return max((len(s[i:j]) for i in range(len(s)) for j in range(i + 1, len(s) + 1)
                if s[i:j] == s[i:j][::-1]), default=0)


assert longest_palindrome("babad") in ("bab", "aba")
assert longest_palindrome("cbbd") == "bb"
assert longest_palindrome("a") == "a"
assert longest_palindrome("ac") in ("a", "c")
assert longest_palindrome("aaaa") == "aaaa"
assert longest_palindrome_manacher("forgeeksskeegfor") == "geeksskeeg"
for _ in range(500):
    s = "".join(random.choice("abc") for _ in range(random.randint(1, 14)))
    for f in (longest_palindrome, longest_palindrome_manacher):
        ans = f(s)
        assert ans == ans[::-1] and ans in s and len(ans) == brute(s)
print("all tests passed")
```

### 複雜度與邊界

中心擴張：時間 O(n²)，2n − 1 個中心、每個最多擴 n/2 次，最差情況是全部相同的字串（例如 `"aaaa…"`），每個中心都擴到邊界；空間 O(1)，只記錄最佳區間，最後切一次字串。Manacher：時間 O(n)、空間 O(n)。邊界情況：長度 1 時直接回傳該字元；長度 2 且兩字相異時回傳任一字元（`best` 初始為空區間，第一個奇數中心就會把它更新為長度 1）；全部相同時答案是整個字串；擴張迴圈先檢查 `lo >= 0 and hi < len(s)` 再比較字元，順序不能反，否則 `s[-1]` 在 Python 中不會報錯，而是悄悄讀到最後一個字元。

### Follow-up

> [!question]- F1. 能不能做到 O(n)？
> 用 25.6 節的 Manacher。維護右端最遠的回文（中心 c、右端 r），對 r 以內的中心 i，先借用鏡像位置 `2c − i` 的半徑（但不超過 `r − i`），只有碰到 r 時才往外逐字擴張；每次成功擴張都把 r 往右推，r 最多走 2n 步，所以總共 O(n)。插入 `#` 把奇偶兩種中心統一，`p[i]` 直接等於原字串的回文長度，起點是 `(i − p[i] − 1) // 2`。面試中通常先寫中心擴張，再口述 Manacher 的鏡像想法與攤銷論證；本題 n ≤ 1000，O(n²) 已足夠。

> [!question]- F2. 如果改成最長回文「子序列」（516. Longest Palindromic Subsequence）呢？
> 子序列可以跳著選，回文不再由一個中心連續擴張而成，中心擴張不適用。要用區間 DP：`dp[i][j]` 是 `s[i..j]` 的最長回文子序列，`s[i] == s[j]` 時為 `dp[i+1][j-1] + 2`，否則為 `max(dp[i+1][j], dp[i][j-1])`，O(n²) 時間，空間可以壓到 O(n)。它也等於 s 和 reverse(s) 的最長共同子序列。詳見第 23 章核心題 4。面試時先問清楚「substring 還是 subsequence」，兩者的解法完全不同。

> [!question]- F3. 如果允許修改最多 k 個字元，最長能變成回文的子字串有多長？
> 一個子字串能用 ≤ k 次修改變成回文，若且唯若它「對稱位置不相同的字元對」不超過 k 對，每對改一個字元即可。固定中心往外擴時，不相同的對數只增不減，所以仍然可以擴張：遇到不相同的一對就把計數加一，計數超過 k 才停。每個中心最多擴 n/2 次，總共 O(n²) 時間、O(1) 空間。k = 0 就退化成原題。這也說明中心擴張的本質：沿著中心往外，「是否還合法」是單調的。

> [!question]- F4. 能不能用 rolling hash 做到 O(n log n)？
> 可以，但要把奇偶分開。若存在長度 L 的回文，去掉頭尾就得到長度 L − 2 的回文，所以「存在長度 L 的回文」在奇數長度上單調、在偶數長度上也單調，但兩者之間不單調（例如 `"aba"` 有長度 3 卻沒有長度 2）。對奇數與偶數各做一次 binary search（第 8 章）；檢查長度 L 時，對每個起點 i 比較 `s[i:i+L]` 的正向雜湊與它在 reverse(s) 中對應片段 `rev[n−i−L : n−i]` 的雜湊，O(n)。總時間 O(n log n)，比 Manacher 慢，但用的是通用零件，難題 2、4 也是同一套「二分長度＋雜湊」。

> [!question]- F5. 如果有 q 次查詢「s[l..r] 是不是回文」呢？
> 先跑一次 Manacher，O(n)。在轉換字串 t 中，原字串的 `s[j]` 位於索引 `2j + 2`，所以 `s[l..r]` 的中心在 t 的索引 `l + r + 2`；它是回文若且唯若 `p[l + r + 2] >= r − l + 1`，因為以同一個中心的回文是巢狀的，最長的那個夠長就涵蓋了它。每次查詢 O(1)，總共 O(n + q)。另一種做法是正向與反向的前綴雜湊，每次比較 `s[l..r]` 與它的反轉是否雜湊相同，也是 O(1)，但有極小的碰撞機率；或者 O(n²) 預先建好 `pal[i][j]` 表，n 小時最簡單。

## 核心題 2｜647. Palindromic Substrings｜Medium

### 題目

給一個字串 `s`，回傳它有幾個回文子字串。位置不同的子字串分開計算，即使內容相同也一樣，例如 `"aa"` 的兩個 `"a"` 算兩個。限制：`1 <= len(s) <= 1000`，只包含小寫英文字母。

- 範例 1：`s = "abc"`，回傳 `3`，只有 `"a"`、`"b"`、`"c"`。
- 範例 2：`s = "aaa"`，回傳 `6`：三個 `"a"`、兩個 `"aa"`、一個 `"aaa"`。
- 範例 3：`s = "abba"`，回傳 `6`：四個單字元、`"bb"`、`"abba"`。
- 範例 4（邊界）：`s = "z"`，回傳 `1`。

### 思路

暴力解枚舉全部 n(n + 1)/2 個子字串並逐一檢查，O(n³)。區間 DP 可以在 O(n²) 時間、O(n²) 空間內填出 `pal[i][j]` 再數 True 的個數。

和核心題 1 一樣，關鍵是「同一個中心的回文是巢狀的」：從中心往外擴，每成功一次就多一個以該中心的回文，第一次失敗之後就不會再有。所以答案是「每個中心能成功擴張的次數」的總和，計數和找最長用的是同一個迴圈，只是把「更新最佳」換成「計數加一」。2n − 1 個中心，總共 O(n²) 時間、O(1) 空間。

換個角度看，這也說明了為什麼答案最多是 O(n²)，因此任何「逐一列出每個回文」的演算法都至少要 O(n²)；要做到 O(n) 就不能逐一列出，而是要對每個中心直接算出個數。Manacher 正好給出每個中心的最長半徑：以 t 的位置 i 為中心、原長度 `p[i]` 的回文，往內每縮一層長度減 2，共有 `(p[i] + 1) // 2` 個，加總起來就是答案。

```text
s = a a a
index: 0 1 2

中心     成功擴張的回文                   個數
(0,0)    "a"                             1
(0,1)    "aa"            （再擴：左越界）  1
(1,1)    "a" → "aaa"     （再擴：越界）    2
(1,2)    "aa"            （再擴：右越界）  1
(2,2)    "a"                             1
(2,3)    hi 越界，0 個                    0
總和 = 6

Manacher 的 p（t = ^ # a # a # a # $）：
t:     ^  #  a  #  a  #  a  #  $
p:     0  0  1  2  3  2  1  0  0
(p+1)//2: 0 0 1  1  2  1  1  0  0     總和 = 6
```

中心 (1,1) 的回文 `"a"` 和 `"aaa"` 是巢狀的，一次擴張就數到兩個；Manacher 的 `p = 3` 在中間那個 `a` 上，`(3 + 1) // 2 = 2` 也正是這兩個。兩種算法得到同樣的分解，只是 Manacher 不需要逐層擴張。

### 解法

```python
import random


def count_substrings(s: str) -> int:
    n, total = len(s), 0
    for c in range(n):
        for lo, hi in ((c, c), (c, c + 1)):
            while lo >= 0 and hi < n and s[lo] == s[hi]:
                total += 1                 # 每次成功擴張就是一個新的回文
                lo -= 1
                hi += 1
    return total


def count_substrings_manacher(s: str) -> int:
    t = "^#" + "#".join(s) + "#$"
    p = [0] * len(t)
    c = r = 0
    for i in range(1, len(t) - 1):
        if i < r:
            p[i] = min(r - i, p[2 * c - i])
        while t[i + p[i] + 1] == t[i - p[i] - 1]:
            p[i] += 1
        if i + p[i] > r:
            c, r = i, i + p[i]
    return sum((v + 1) // 2 for v in p)


def brute(s):
    return sum(s[i:j] == s[i:j][::-1] for i in range(len(s)) for j in range(i + 1, len(s) + 1))


assert count_substrings("abc") == 3
assert count_substrings("aaa") == 6
assert count_substrings("abba") == 6
assert count_substrings("z") == 1
assert count_substrings("a" * 1000) == 1000 * 1001 // 2        # 最差情況
assert count_substrings_manacher("aaa") == 6
for _ in range(500):
    s = "".join(random.choice("ab") for _ in range(random.randint(1, 12)))
    assert count_substrings(s) == count_substrings_manacher(s) == brute(s)
print("all tests passed")
```

### 複雜度與邊界

中心擴張 O(n²) 時間、O(1) 空間；最差是全部相同的字串，答案本身就是 n(n + 1)/2，而這個版本每次成功擴張只多數一個，所以時間至少和答案一樣大。Manacher 是 O(n) 時間、O(n) 空間，不受答案大小影響。邊界情況：長度 1 時只有一個奇數中心，答案 1；偶數中心 `(c, c + 1)` 在 `c = n − 1` 時 hi 直接越界，迴圈不執行，不需要特判；答案最大約 5 × 10⁵，任何語言的 32 位元整數都夠，但若 n 到 10⁵ 以上，答案會超過 2³¹，在 Java／C++ 要用 64 位元。

### Follow-up

> [!question]- F1. 如果相同內容只算一次，要數「不同的」回文子字串有幾個呢？
> 有一個漂亮的性質：在字串尾端加一個字元，**最多只會新增一個**之前沒出現過的回文，就是新的最長回文後綴。理由是：若 Q 是較短的回文後綴，它也是最長回文後綴 P 的後綴；P 是回文，所以 Q 反轉後也出現在 P 的開頭，而 Q 本身是回文，因此 Q 在 P 的開頭已經出現過。所以不同回文子字串最多 n 個。O(n) 的標準做法是 eertree（palindromic tree，回文樹），每個節點代表一個不同的回文；面試中較實際的做法是中心擴張時把每個回文的 rolling hash（25.5 節）放進 set，O(n²) 期望時間。

> [!question]- F2. 如果有 q 次查詢「s[l..r] 裡有幾個回文子字串」呢？
> 先 O(n²) 建 `pal[i][j]`，再定義 `cnt[l][r]` = `s[l..r]` 內的回文子字串數，用排容原理遞推：`cnt[l][r] = cnt[l+1][r] + cnt[l][r−1] − cnt[l+1][r−1] + pal[l][r]`，因為 `s[l..r]` 的子字串要嘛不含 l、要嘛不含 r、要嘛兩端都含（就是整段本身）。預處理 O(n²) 時間與空間，每次查詢 O(1)。n = 1000 時表格有 10⁶ 格，可以接受；n 更大時要改用離線處理與資料結構，超出面試範圍。

> [!question]- F3. 如果要把 s 切成若干段，每段都是回文，最少要切幾刀（132. Palindrome Partitioning II）？
> 令 `cut[i]` 是 `s[:i]` 的最少刀數，`cut[0] = −1`。中心擴張時，每找到一個回文 `s[lo..hi]`，就更新 `cut[hi + 1] = min(cut[hi + 1], cut[lo] + 1)`。所有回文都會被列舉一次，總共 O(n²) 時間、O(n) 空間，不需要 O(n²) 的 `pal` 表。
> ```python
> def min_cut(s):
>     n = len(s)
>     cut = [i - 1 for i in range(n + 1)]   # 最差每個字元各一段
>     for c in range(n):
>         for lo, hi in ((c, c), (c, c + 1)):
>             while lo >= 0 and hi < n and s[lo] == s[hi]:
>                 cut[hi + 1] = min(cut[hi + 1], cut[lo] + 1)
>                 lo, hi = lo - 1, hi + 1
>     return cut[n]
> ```

> [!question]- F4. 如果改成數回文「子序列」（位置不同就算不同）呢？
> 子序列不連續，要用區間 DP。令 `dp[l][r]` 是 `s[l..r]` 中回文子序列的個數，排容後 `dp[l][r] = dp[l+1][r] + dp[l][r−1] − dp[l+1][r−1]`；若 `s[l] == s[r]`，再加上 `dp[l+1][r−1] + 1`，因為每個內部的回文子序列（以及空的那個）都可以在兩端各加上 `s[l]`、`s[r]` 形成新的回文。O(n²) 時間與空間，數字很大時題目通常要求取模。要求「不同的」回文子序列是 730 題，需要再處理重複字元的扣除，做法見第 23 章核心題 4（516）的 F5。

> [!question]- F5. 如果只數長度至少 k 的回文子字串呢？
> 用 Manacher 拿到每個中心的最長長度 v（即 `p[i]`）後，以該中心的回文長度是 v、v − 2、v − 4、…，其中 ≥ k 的個數可以直接算：若 v < k 則為 0，否則是 `(v − k') // 2 + 1`，k' 是和 v 同奇偶、且 ≥ k 的最小長度（k 與 v 同奇偶時 k' = k，否則 k' = k + 1）。每個中心 O(1)，總共 O(n)。中心擴張版本則是在 `hi − lo + 1 >= k` 時才計數，仍是 O(n²)。這個 follow-up 在考你是否理解「每個中心的回文長度是一個等差數列」。

## 核心題 3｜28. Find the Index of the First Occurrence in a String｜Easy

### 題目

給兩個字串 `haystack`（文字，長度 n）與 `needle`（pattern，長度 m），回傳 `needle` 在 `haystack` 中第一次出現的起始索引；如果沒有出現，回傳 `-1`。限制：`1 <= n, m <= 10⁴`，兩者都只包含小寫英文字母。面試時通常會要求不使用內建的 `find`／`index`，並問你能不能做到線性時間。

- 範例 1：`haystack = "sadbutsad"`、`needle = "sad"`，回傳 `0`；`"sad"` 出現在 0 和 6，取第一個。
- 範例 2：`haystack = "leetcode"`、`needle = "leeto"`，回傳 `-1`。
- 範例 3：`haystack = "mississippi"`、`needle = "issip"`，回傳 `4`。
- 範例 4（邊界）：`needle` 比 `haystack` 長，例如 `haystack = "ab"`、`needle = "abc"`，回傳 `-1`；兩者相同時回傳 `0`。

### 思路

暴力解對每個起點 `i ∈ [0, n − m]` 逐字比較 `haystack[i:i+m]` 與 `needle`，最差約 (n − m + 1)·m 次比較，n = 10⁴、m = n/2 = 5000 時約 2.5 × 10⁷ 次，在這題的限制下其實能過，所以面試時先寫它沒有問題。但面試官真正想看的是：你能不能說出暴力解的浪費在哪，並用 KMP 做到 O(n + m)。

浪費在於失敗時 text 的指標會「後退」：從起點 i 比到 i + k 失敗後，下一輪從 i + 1 重新比，前面 k 個已知相等的字元又被比一次。KMP 的關鍵觀察是：失敗時我們知道 text 最近的 k 個字元正是 `needle[:k]`，所以下一個可能成功的對齊，只取決於 `needle[:k]` 自身的結構，和 text 無關。具體來說，新的匹配長度必須是 `needle[:k]` 的 border，而且越長越好（越長代表 pattern 往右移得越少，不會跳過任何可能的出現），也就是 `pi[k − 1]`。

因此演算法維持一個 invariant：**處理完 `haystack[i]` 後，k 是「`needle` 的前綴中，同時是 `haystack[:i+1]` 後綴的最長那一個」的長度**。讀進下一個字元時，若它等於 `needle[k]` 就 k + 1；否則沿著 `pi` 回跳到次長的 border 再試。k 達到 m 就是找到了。text 的指標只往前走，k 的回跳總次數被 k 的總增量 n 限制住，所以比對 O(n)，加上建表 O(m)。

```text
haystack = m i s s i s s i p p i，needle = i s s i p
needle 的 pi：  i  s  s  i  p
               0  0  0  1  0       （"issi" 的最長 border 是 "i"）

i  字元  比對前 k  動作                                       比對後 k
0   m     0      m ≠ needle[0]=i                              0
1   i     0      i == needle[0]                               1
2   s     1      s == needle[1]                               2
3   s     2      s == needle[2]                               3
4   i     3      i == needle[3]                               4   已對上 "issi"
5   s     4      s ≠ needle[4]=p → k = pi[3] = 1（保留 "i"）
                 s == needle[1]                               2
6   s     2      s == needle[2]                               3
7   i     3      i == needle[3]                               4
8   p     4      p == needle[4]                               5 = m → 起點 8 − 5 + 1 = 4
```

第 5 步是 KMP 和暴力解的分水嶺：暴力解會回到起點 2 重新比對，KMP 則知道剛對上的 `"issi"` 結尾的 `"i"` 正是 needle 的開頭，直接保留 k = 1，text 指標不動，從 `needle[1]` 繼續比。

### 解法

```python
import random


def str_str(haystack: str, needle: str) -> int:
    m = len(needle)
    if m == 0:
        return 0
    pi = [0] * m                           # failure function
    for i in range(1, m):
        k = pi[i - 1]
        while k > 0 and needle[i] != needle[k]:
            k = pi[k - 1]
        if needle[i] == needle[k]:
            k += 1
        pi[i] = k
    k = 0
    for i, ch in enumerate(haystack):
        while k > 0 and ch != needle[k]:
            k = pi[k - 1]
        if ch == needle[k]:
            k += 1
        if k == m:
            return i - m + 1
    return -1


def str_str_z(haystack: str, needle: str) -> int:
    """Z-function 版本：在 needle + '#' + haystack 上找 z 值 >= m 的位置。"""
    s = needle + "#" + haystack
    n, m = len(s), len(needle)
    z, l, r = [0] * n, 0, 0
    for i in range(1, n):
        if i < r:
            z[i] = min(r - i, z[i - l])
        while i + z[i] < n and s[z[i]] == s[i + z[i]]:
            z[i] += 1
        if i + z[i] > r:
            l, r = i, i + z[i]
        if i > m and z[i] >= m:
            return i - m - 1
    return -1


def brute(h, nd):
    for i in range(len(h) - len(nd) + 1):
        if h[i:i + len(nd)] == nd:
            return i
    return -1


assert str_str("sadbutsad", "sad") == 0
assert str_str("leetcode", "leeto") == -1
assert str_str("mississippi", "issip") == 4
assert str_str("ab", "abc") == -1
assert str_str("abc", "abc") == 0
assert str_str("aaaaaaaab", "aaab") == 5                   # 暴力解的最差型態
assert str_str_z("mississippi", "issip") == 4
for _ in range(500):
    h = "".join(random.choice("ab") for _ in range(random.randint(1, 15)))
    nd = "".join(random.choice("ab") for _ in range(random.randint(1, 4)))
    assert str_str(h, nd) == str_str_z(h, nd) == brute(h, nd) == h.find(nd)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n + m)：建表 O(m)、比對 O(n)，兩者都用「k 每步最多加 1、每次回跳至少減 1」的攤銷論證。空間 O(m)，只存 needle 的 `pi`，haystack 可以是串流。邊界情況：needle 比 haystack 長時，k 永遠到不了 m，自然回傳 −1；needle 為空字串時依慣例回傳 0（本題限制排除了這種情況，但寫上一行比較穩）；needle 全部相同字元（`"aaaa"`）時 pi 是 `0, 1, 2, 3`，失敗時一次只退一格，仍然是線性；Z 版本的分隔字元 `#` 必須不在字母表中，否則 z 值會跨過接縫。

### Follow-up

> [!question]- F1. 如果要回傳所有出現的位置，包括互相重疊的呢？
> 在 `k == m` 時記錄 `i − m + 1`，然後令 `k = pi[m − 1]` 繼續，而不是回傳。退到最長 border 而不是 0，才能抓到重疊的出現，例如 `"aa"` 在 `"aaaa"` 中出現在 0、1、2。總時間仍是 O(n + m)，輸出最多 n − m + 1 個位置。若題目要的是**不重疊**的出現（例如計算最多能替換幾次），就把 k 歸零，這等價於從匹配結尾之後重新開始的貪婪，貪婪取最左邊的匹配能得到最多的不重疊次數。

> [!question]- F2. 如果有很多個 pattern 要同時在同一段 text 中搜尋呢？
> 對每個 pattern 各跑一次 KMP 是 O(k · n + Σm)，k 個 pattern 時 text 被掃 k 次。更好的做法是 Aho-Corasick：把所有 pattern 插入 trie（第 13 章），再用 BFS 為每個節點建立 failure link，意義和 KMP 的 `pi` 相同，只是從「一條鏈」推廣到「一棵樹」；之後掃 text 一次，總時間 O(n + Σm + 匹配數)。如果所有 pattern 長度相同（都是 L），也可以用 rolling hash：把 pattern 的雜湊放進 set，用長度 L 的窗口掃過 text，O(n + Σm) 期望時間，這正是第 4 章難題 2（30 題）的優化方向。

> [!question]- F3. 如果 text 是即時串流，每來一個字元都要立刻回報「是否剛好完成一次匹配」，而且要求每個字元嚴格 O(1) 呢？
> KMP 的比對本身只需要狀態 k 和 `pi`，所以天然支援串流、只用 O(m) 記憶體；但單一字元可能觸發多次回跳，只有攤銷 O(1)。若要嚴格的最差 O(1)，就把 KMP 展開成有限狀態自動機：`aut[k][c]` = 目前狀態 k、讀入字元 c 後的新狀態，建法是 `aut[k][c] = k + 1`（若 `needle[k] == c`）否則 `aut[pi[k − 1]][c]`（k = 0 時為 0），O(m · Σ) 時間與空間，Σ 是字母表大小（本題 26）。之後每個字元只查一次表。

> [!question]- F4. 如果 needle 中可以有萬用字元 `?`（可配任何一個字元）呢？
> KMP 會失效，因為「配對」不再有遞移性：`a` 配 `?`、`?` 配 `b`，但 `a` 不配 `b`，border 的推理就不成立了。實際可行的做法有兩種。一是 Shift-And（bitap）：為每個字元建一個位元遮罩，`?` 的位置在所有遮罩中都設為 1，掃描時 `D = ((D << 1) | 1) & mask[c]`，D 的第 m − 1 位為 1 就是匹配；Python 的大整數可以當作任意長度的 bitset，時間 O(n · ⌈m / w⌉)，w 是機器字長。二是用 FFT 計算卷積，O((n + m) log(n + m))，屬於競賽範圍，面試說出思路即可。

> [!question]- F5. 如果要判斷 goal 是不是 s 旋轉後的結果（796. Rotate String）呢？
> s 的所有旋轉都恰好是 `s + s` 中長度 n 的子字串，所以條件是 `len(s) == len(goal) and goal in s + s`。用本題的 KMP 在 `s + s` 中搜尋 goal，O(n)。長度檢查不能省，否則 goal 比 s 短時（例如 `s = "ab"`、`goal = "b"`）會被誤判為真。這個「把循環結構攤平成兩倍長度」的技巧，在核心題 4、5 也會再出現。

## 核心題 4｜459. Repeated Substring Pattern｜Easy

### 題目

給一個非空字串 `s`，判斷它能不能由它的某個子字串重複**至少兩次**串接而成。限制：`1 <= len(s) <= 10⁴`，只包含小寫英文字母。

- 範例 1：`s = "abab"`，回傳 `True`，由 `"ab"` 重複兩次。
- 範例 2：`s = "aba"`，回傳 `False`。
- 範例 3：`s = "abcabcabcabc"`，回傳 `True`，可以是 `"abc"` × 4，也可以是 `"abcabc"` × 2。
- 範例 4（邊界）：`s = "a"`，回傳 `False`（至少要兩次）；`s = "aaaa"` 回傳 `True`；`s = "abababa"` 回傳 `False`，它有週期 2，但 7 不能被 2 整除。

### 思路

暴力解枚舉單位長度 d：d 必須整除 n 且 d < n，再檢查 `s == s[:d] * (n // d)`。每次檢查 O(n)，n ≤ 10⁴ 的因數個數最多幾十個，所以 O(n · 因數個數) 其實很快。面試中先說這個，再提出 O(n) 而且能推廣的做法：用 failure function 直接算出**最短週期**。

週期的定義：若對所有合法的 i 都有 `s[i] == s[i + p]`，就說 p 是 s 的週期。關鍵觀察是 **p 是週期 ⟺ s 有長度 n − p 的 border**，因為 `s[i] == s[i + p]` 對所有 i 成立，正好就是「前 n − p 個字元等於後 n − p 個字元」。所以最長的 border `pi[n − 1]` 對應最短的週期 `p = n − pi[n − 1]`。

最短週期有了，還要判斷 s 能不能「整齊地」被切成若干份。若 p 整除 n 且 p < n，則 s 就是 `s[:p]` 重複 n / p 次。反過來，若 s 能由長度 d 的單位重複組成（d 整除 n、d ≤ n/2），d 也是週期，因為 p ≤ d，有 p + d ≤ 2d ≤ n，由週期引理（Fine–Wilf：兩個週期 p、d 滿足 p + d − gcd(p, d) ≤ n 時，gcd(p, d) 也是週期）可知 gcd(p, d) 是週期，再由 p 最短得 gcd(p, d) = p，所以 p 整除 d、也整除 n。因此**答案就是 `p < n and n % p == 0`**。

```text
s = a b c a b c a b c a b c   （n = 12）
pi: 0 0 0 1 2 3 4 5 6 7 8 9   pi[11] = 9
最短週期 p = 12 − 9 = 3，12 % 3 == 0 → True，單位是 "abc"

s = a b a b a b a             （n = 7）
pi: 0 0 1 2 3 4 5             pi[6] = 5
最短週期 p = 7 − 5 = 2，7 % 2 == 1 → False
  a b a b a b a
      a b a b a b a           往右移 2 格後重疊部分完全相同（週期 2），
                              但最後一份 "a" 不完整，切不整齊

另一個角度：s 出現在 (s + s)[1:-1] 中嗎？
s + s       = a b a b a b a b      （s = "abab"）
(s+s)[1:-1] =   b a b a b a
                  a b a b          在位置 1 找到 s → True
```

第二個角度是另一種常見的一行解：s 是重複字串，若且唯若把 s 旋轉某個 0 < k < n 格後還等於自己，而所有旋轉都是 `s + s` 的子字串；去掉頭尾一個字元，是為了排除 k = 0 與 k = n 這兩個「旋轉等於沒動」的位置。

### 解法

```python
import random


def repeated_substring_pattern(s: str) -> bool:
    n = len(s)
    pi = [0] * n
    for i in range(1, n):
        k = pi[i - 1]
        while k > 0 and s[i] != s[k]:
            k = pi[k - 1]
        if s[i] == s[k]:
            k += 1
        pi[i] = k
    p = n - pi[-1]                         # 最短週期
    return p < n and n % p == 0


def repeated_substring_pattern_rotate(s: str) -> bool:
    return s in (s + s)[1:-1]


def brute(s):
    n = len(s)
    return any(n % d == 0 and s[:d] * (n // d) == s for d in range(1, n // 2 + 1))


assert repeated_substring_pattern("abab") is True
assert repeated_substring_pattern("aba") is False
assert repeated_substring_pattern("abcabcabcabc") is True
assert repeated_substring_pattern("a") is False
assert repeated_substring_pattern("aaaa") is True
assert repeated_substring_pattern("abababa") is False
assert repeated_substring_pattern("abaababaab") is True     # "abaab" × 2，最短週期 5
for _ in range(1000):
    unit = "".join(random.choice("ab") for _ in range(random.randint(1, 4)))
    s = unit * random.randint(1, 4) if random.random() < 0.5 else \
        "".join(random.choice("ab") for _ in range(random.randint(1, 10)))
    assert repeated_substring_pattern(s) == repeated_substring_pattern_rotate(s) == brute(s)
print("all tests passed")
```

### 複雜度與邊界

failure function 版本 O(n) 時間、O(n) 空間。`(s + s)[1:-1]` 版本建了一個 2n 的字串，O(n) 空間，時間取決於 `in` 的實作；CPython 的子字串搜尋在實務上很快，但若面試官要求保證線性，就換成 KMP 搜尋。暴力解 O(n · d(n))，d(n) 是因數個數。邊界情況：n = 1 時 `pi[-1] = 0`、p = 1 = n，回傳 False；全部相同字元時 p = 1，只要 n ≥ 2 就是 True；`"abababa"` 這類「有週期但不整除」的字串是最容易誤判的情況，只看 `pi[-1] > 0` 會錯，一定要檢查整除。

### Follow-up

> [!question]- F1. 如果要回傳最短的重複單位和重複次數呢？
> 單位就是 `s[:p]`、次數是 `n // p`，其中 `p = n − pi[n − 1]`，前提是 `n % p == 0`；否則 s 不是重複字串，可以回傳 `(s, 1)`。O(n)。由思路中的週期引理，任何合法的單位長度都是 p 的倍數，所以 `s[:p]` 一定是最短的。例如 `"abcabcabcabc"` 回傳 `("abc", 4)`，即使 `"abcabc"` 也是合法單位。

> [!question]- F2. 為什麼 `s in (s + s)[1:-1]` 是對的？請證明。
> 若 s 是 u 重複 k ≥ 2 次，則 s 在 `s + s` 中的位置 |u| 也出現（0 < |u| < n），去頭去尾後仍在範圍內。反過來，若 s 出現在 `s + s` 的位置 r（0 < r < n），代表把 s 往左旋轉 r 格等於自己，也就是 `s[i] == s[(i + r) % n]` 對所有 i 成立；那麼 s 以 g = gcd(r, n) 為循環週期（重複套用旋轉 r 可以得到旋轉 g 的效果，因為 r 的倍數模 n 能湊出 g），g 整除 n 且 g ≤ r < n，所以 s 是 `s[:g]` 重複 n / g ≥ 2 次。

> [!question]- F3. 如果有 q 次查詢「子字串 s[l:r] 是不是重複字串」呢？
> 先建前綴雜湊（25.5 節），任意子字串可 O(1) 比較。長度 L = r − l 的子字串以 d 為週期，若且唯若 `s[l : r − d]` 與 `s[l + d : r]` 雜湊相同。它是重複字串若且唯若存在**某個質因數** q 整除 L，使 L / q 是週期：因為若最短單位是 p，L / p ≥ 2，取 L / p 的某個質因數 q，L / q 是 p 的倍數，也是週期。所以每次查詢只要檢查 L 的每個不同質因數，最多約 log L 個，用篩法預先算好最小質因數即可。總時間 O(n + q log n)。

> [!question]- F4. 所有可能的重複單位有哪些？s 的所有週期又有哪些？
> 所有**週期**對應所有 border：沿著 border 鏈 `b₁ = pi[n − 1]`、`b₂ = pi[b₁ − 1]`、…，週期就是 `n − b₁ < n − b₂ < …`，O(n) 全部列出。所有**重複單位**則是「最短週期 p 的倍數、且整除 n」的那些長度（p 本身必須整除 n），例如 n = 12、p = 2 時單位長度是 2、4、6（12 本身不算，因為要至少兩次）。週期與重複單位的區別正是範例 `"abababa"`：它的週期有 2、4、6，但沒有任何一個整除 7。

> [!question]- F5. s 的 n 個旋轉中，有幾個和 s 本身相同？
> 旋轉 r 格等於 s，若且唯若 s 出現在 `s + s` 的位置 r（0 ≤ r < n）。由 F2 的論證，這些 r 恰好是「最短重複單位 p」的倍數（若 p 整除 n）；否則只有 r = 0。所以答案是 `n // p`（p 整除 n 時）或 1。也可以直接用 KMP 在 `(s + s)[:-1]` 中數 s 出現幾次，O(n)。這個量在環狀字串、項鍊計數類題目中常被用到。

## 核心題 5｜686. Repeated String Match｜Medium

### 題目

給兩個字串 `a` 與 `b`，回傳最少要把 `a` 重複串接幾次，`b` 才會成為結果的子字串；如果不論重複幾次都不可能，回傳 `-1`。重複 0 次是空字串。限制：`1 <= len(a), len(b) <= 10⁴`，只包含小寫英文字母。

- 範例 1：`a = "abcd"`、`b = "cdabcdab"`，回傳 `3`；`"abcdabcdabcd"` 包含 b，重複兩次的 `"abcdabcd"` 不包含。
- 範例 2：`a = "a"`、`b = "aa"`，回傳 `2`。
- 範例 3：`a = "abc"`、`b = "wxyz"`，回傳 `-1`。
- 範例 4（邊界）：`a = "abc"`、`b = "cabcabca"`，回傳 `4`；b 的長度 8 只需要 3 份 a 的長度，但 b 從 a 的中間開始，必須多一份。`a = "aa"`、`b = "a"` 回傳 `1`。

### 思路

暴力解是從 k = 1 開始，建 `a * k` 並檢查 b 是否為子字串，直到 k 夠大。問題是：要試到多大才能確定答案是 −1？如果沒有上界，這個迴圈不會停。所以第一個關鍵是**證明重複次數的上界**。

令 `q = ⌈len(b) / len(a)⌉`，這是長度上的下界：少於 q 份連長度都不夠。上界是 q + 1：如果 b 出現在 a 無限重複的字串 `a a a …` 中，從某個位置 s 開始，那麼把 s 往左移 len(a) 的整數倍，內容不變（因為 a^∞ 有週期 len(a)），所以可以假設 `0 <= s < len(a)`。此時 b 結束於 `s + len(b) <= len(a) − 1 + q·len(a) < (q + 1)·len(a)`，完全落在 q + 1 份 a 之內。所以只要在 `a * (q + 1)` 中搜尋一次：找不到就是 −1；找到第一次出現的位置 `idx`，答案就是包住 `[idx, idx + len(b))` 所需的份數 `⌈(idx + len(b)) / len(a)⌉`。第一次出現的 idx 最小，所需份數也最少。

第二個重點是搜尋本身用 KMP，總長度 O(len(a) + len(b))，所以整題 O(n + m)。若用暴力比對，最差是 O((q + 1)·n·m)，在 `a = "aaaa…a"`、`b = "aaa…ab"` 時會很慢。

```text
a = a b c，b = c a b c a b c a（長度 8）
q = ⌈8 / 3⌉ = 3，在 a × 4 中搜尋

index:  0 1 2 | 3 4 5 | 6 7 8 | 9 10 11
a × 4:  a b c | a b c | a b c | a b  c
b:          c   a b c   a b c   a          從 idx = 2 開始，結束於 10（不含）

所需份數 = ⌈(2 + 8) / 3⌉ = ⌈10 / 3⌉ = 4
只建 a × 3（長度 9）時，b 需要到索引 9，超出範圍 → 只檢查 q 份會答錯
```

這個例子同時說明了上界為什麼是 q + 1 而不是 q：b 的長度只需要 3 份，但它從第一份 a 的中間（索引 2）開始，尾巴就跨進了第 4 份。

### 解法

```python
import random


def repeated_string_match(a: str, b: str) -> int:
    n, m = len(a), len(b)
    q = -(-m // n)                          # ⌈m / n⌉
    text = a * (q + 1)
    pi = [0] * m
    for i in range(1, m):
        k = pi[i - 1]
        while k > 0 and b[i] != b[k]:
            k = pi[k - 1]
        if b[i] == b[k]:
            k += 1
        pi[i] = k
    k = 0
    for i, ch in enumerate(text):
        while k > 0 and ch != b[k]:
            k = pi[k - 1]
        if ch == b[k]:
            k += 1
        if k == m:
            end = i + 1                    # b 佔據 text[end - m : end]
            return -(-end // n)            # ⌈end / n⌉
    return -1


def brute(a, b):
    for k in range(1, len(b) // len(a) + 3):
        if b in a * k:
            return k
    return -1


assert repeated_string_match("abcd", "cdabcdab") == 3
assert repeated_string_match("a", "aa") == 2
assert repeated_string_match("abc", "wxyz") == -1
assert repeated_string_match("abc", "cabcabca") == 4
assert repeated_string_match("aa", "a") == 1
assert repeated_string_match("abc", "cab") == 2
assert repeated_string_match("ab", "aba") == 2
for _ in range(1000):
    a = "".join(random.choice("ab") for _ in range(random.randint(1, 4)))
    b = "".join(random.choice("ab") for _ in range(random.randint(1, 9)))
    assert repeated_string_match(a, b) == brute(a, b)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n + m)：text 的長度是 `(q + 1)·n <= m + 2n`，KMP 建表 O(m)、比對 O(m + n)。空間 O(n + m)，主要是 text；若不想建 text，見 F1。邊界情況：b 比 a 短時 q = 1，仍要搜尋 `a * 2`，因為 b 可能跨過 a 的結尾（`a = "abc"`、`b = "ca"` 的答案是 2）；b 完全在一份 a 之內時答案 1；b 含有 a 沒有的字元時，搜尋自然失敗回傳 −1，也可以先用 `set(b) <= set(a)` 提早結束。向上取整用 `-(-x // n)`，避免浮點數。

### Follow-up

> [!question]- F1. 如果 a 很長、不想真的建出 a × (q + 1) 這個字串呢？
> KMP 的比對只需要逐一讀 text 的字元，所以可以用虛擬索引：`for i in range((q + 1) * n): ch = a[i % n]`，其餘邏輯完全不變。額外空間只剩 b 的 `pi`，O(m)；時間仍是 O(n + m)。這也是 KMP 適合串流的體現：它不需要隨機存取 text，也不需要回頭。

> [!question]- F2. 用 rolling hash 怎麼做？
> 在虛擬 text 上用長度 m 的窗口滾動計算雜湊，和 b 的雜湊比較，雜湊相同時再逐字驗證；第一個驗證成功的起點 idx 給出答案 `⌈(idx + m) / n⌉`。而且起點只需要試 `0 <= idx < n`，因為思路已經證明只要有解，就存在起點小於 n 的出現。期望時間 O(n + m)，但最差（大量碰撞或大量雜湊相同卻不匹配的情況）可能退化；KMP 是確定性的，所以這題 KMP 更好。

> [!question]- F3. 如果改成「b 是 a 重複若干次之後的子序列」，最少要幾份（1055. Shortest Way to Form String 的變形）呢？
> 子序列可以跳著選，所以用貪婪：每份 a 盡可能多地配對 b 的下一個字元，配不下了才開新的一份。先建 `nxt[i][c]` = a 中位置 ≥ i 的第一個字元 c 的位置（從右往左填，O(26n)），掃 b 時沿著 `nxt` 跳，跳到 a 的結尾就份數加一並從 0 重來；若某個字元在 a 中根本不存在就回傳 −1。總時間 O(26n + m)。貪婪最佳的理由是：在同一份 a 中越早配對，留給後面的選擇只會更多。

> [!question]- F4. 如果同一個 a 要回答很多個 b 的查詢呢？
> 每次重跑是 O(n + m) per query，主要成本是 n。更好的觀察是：當 `len(b) >= len(a)` 時，b 若在 a^∞ 中出現，b 本身必須以 n 為週期，也就是 `b[i] == b[i + n]` 對所有 i 成立（O(m) 檢查），而且 `b[:n]` 必須是 a 的某個旋轉。把 a 的 n 個旋轉的雜湊預先放進 dict（用 `a + a` 的前綴雜湊 O(n) 算出），每次查詢就能 O(m) 找出起點 r（同一個雜湊對應多個旋轉時取最小的 r），答案是 `⌈(r + m) / n⌉`。若 `len(b) < len(a)`，則要判斷 b 是否為 `a + a` 的子字串，可以預先建 `a + a` 的 suffix automaton，每次 O(m) 查詢。這樣每次查詢都和 n 無關。

## 難題 1｜214. Shortest Palindrome｜Hard

### 題目

給一個字串 `s`，你只能在它的**前面**加上字元，請回傳用這種方式能得到的最短回文。限制：`0 <= len(s) <= 5 × 10⁴`，只包含小寫英文字母。

- 範例 1：`s = "aacecaaa"`，回傳 `"aaacecaaa"`，只需要在前面補一個 `a`。
- 範例 2：`s = "abcd"`，回傳 `"dcbabcd"`，補上 `"dcb"`。
- 範例 3（邊界）：`s = ""`，回傳 `""`；`s = "aba"` 本身就是回文，回傳 `"aba"`。
- 範例 4（邊界）：`s = "aaaab"`，回傳 `"baaaab"`；最長的回文前綴是 `"aaaa"`，只要把剩下的 `"b"` 反轉補到前面。

### 提示

> [!tip]- 提示 1
> 補在前面的字元是 X，`X + s` 是回文。想一想：在這個回文裡，s 的哪一部分會和自己對稱？那一部分有什麼性質？

> [!tip]- 提示 2
> 答案只取決於 s 的**最長回文前綴** `s[:L]`：把剩下的 `s[L:]` 反轉後補到前面就是最短的回文。問題變成「O(n) 求最長回文前綴」。

> [!tip]- 提示 3
> `s[:L]` 是回文 ⟺ `s[:L]` 等於 `reverse(s)` 的長度 L 後綴。所以 L 是「s 的前綴」與「reverse(s) 的後綴」最長的相等長度：對 `s + "#" + reverse(s)` 算 failure function，最後一格就是 L。

### 詳解

**化簡成最長回文前綴**。設 `T = X + s` 是回文，`|X| = k < n`。因為 T 是回文，位置 i 和 `n + k − 1 − i` 的字元相同；區間 `[k, n)` 在這個鏡像下對應到自己（k ↔ n − 1），所以 `T[k:n] = s[:n − k]` 本身就是回文。也就是說，**不論補什麼，s 都必須有一個長度 n − k 的回文前綴**；要讓 k 最小，就要找最長的回文前綴 `s[:L]`，k 至少是 n − L。反過來，補上 `reverse(s[L:])` 剛好就能構成回文：`reverse(s[L:]) + s[:L] + s[L:]`，中間是回文、兩側互為反轉。所以答案是 `reverse(s[L:]) + s`。

**為什麼直覺做法太慢**。最直接的找法是從 L = n 往下試，每個 L 用 O(L) 檢查 `s[:L]` 是否回文，最差 O(n²)。最差情況是像 `"aaaa…a" + "b" + "aaaa…a"` 這種字串：很多長度的前綴「幾乎」是回文，每次都要比到中間附近才失敗。n = 5 × 10⁴ 時是 10⁹ 級，不可行。用 Manacher 也可以（見 F5），但有一個更短、更不容易寫錯的轉換。

**突破點：回文前綴 = 前綴與反轉字串後綴的 border**。`s[:L]` 是回文，若且唯若 `s[:L] == reverse(s[:L])`，而 `reverse(s[:L])` 正是 `r = reverse(s)` 的最後 L 個字元。所以要找的是「最長的 L，使 s 的長度 L 前綴等於 r 的長度 L 後綴」，這就是字串 `s + "#" + r` 的最長 border，failure function 的最後一格。分隔字元 `#` 保證 border 不會跨過中間，因此 L ≤ n（見 F1）。整個演算法 O(n)，而且是確定性的。

```text
s = a a c e c a a a，r = reverse(s) = a a a c e c a a
t = s + "#" + r

t:   a a c e c a a a # a a a c e c a a
pi:  0 1 0 0 0 1 2 2 0 1 2 2 3 4 5 6 7
                                    ↑ pi[-1] = 7

L = 7：s[:7] = "aacecaa" 是回文
      r 的最後 7 個字 = "aacecaa"，正是 s[:7] 的反轉
答案 = reverse(s[7:]) + s = "a" + "aacecaaa" = "aaacecaaa"

s = a b c d：t = a b c d # d c b a，pi[-1] = 1 → L = 1（"a"）
答案 = reverse("bcd") + s = "dcb" + "abcd" = "dcbabcd"
```

在第一個例子中，`pi` 在 `#` 之後一路從 1 長到 7：r 的後半段 `"aacecaa"` 逐字對上 s 的開頭，代表 s 的前 7 個字元與自己的反轉完全相同。正確性只依賴 border 的定義，不需要額外的回文檢查。

### 解法

```python
import random


def shortest_palindrome(s: str) -> str:
    t = s + "#" + s[::-1]
    pi = [0] * len(t)
    for i in range(1, len(t)):
        k = pi[i - 1]
        while k > 0 and t[i] != t[k]:
            k = pi[k - 1]
        if t[i] == t[k]:
            k += 1
        pi[i] = k
    L = pi[-1] if s else 0                 # 最長回文前綴的長度
    return s[L:][::-1] + s


def brute(s):
    for L in range(len(s), -1, -1):
        if s[:L] == s[:L][::-1]:
            return s[L:][::-1] + s


assert shortest_palindrome("aacecaaa") == "aaacecaaa"
assert shortest_palindrome("abcd") == "dcbabcd"
assert shortest_palindrome("") == ""
assert shortest_palindrome("aba") == "aba"
assert shortest_palindrome("aaaab") == "baaaab"
big = "a" * 25000 + "b" + "a" * 25001
assert shortest_palindrome(big) == "a" + big   # 暴力法的最差型態，KMP 仍是線性
for _ in range(1000):
    s = "".join(random.choice("ab") for _ in range(random.randint(0, 10)))
    assert shortest_palindrome(s) == brute(s)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：t 的長度是 2n + 1，failure function 線性。空間 O(n)。邊界情況：空字串時 t = `"#"`，直接回傳 `""`；s 本身是回文時 L = n，什麼都不補；只有一個字元時 L = 1；`#` 不在小寫字母中，所以 border 不會跨過中間。若字元集可能包含任意字元，可以改成對整數陣列操作，用 −1 當分隔，或改用 F1 提到的「以 r 為 text、s 為 pattern 跑 KMP 比對」的寫法，完全不需要分隔字元。

### Follow-up

> [!question]- F1. 為什麼一定要有分隔字元？不加會怎樣？
> 不加分隔字元時，border 可以跨過 s 與 r 的接縫，長度可能超過 n。例如 `s = "aa"`，`s + r = "aaaa"` 的最長 border 是 3，但 s 只有 2 個字元，`s[3:]` 的計算就會錯。加上不在字母表裡的 `#` 後，任何 border 都不能包含 `#`（因為 t 的開頭沒有 `#` 可以對上），所以長度最多 n。另一種完全不需要分隔字元的寫法：建 s 的 `pi`，再把 r 當作 text、s 當作 pattern 跑 KMP 比對，掃完 r 時的狀態 k 就是 L，因為 k 永遠不超過 pattern 長度 n。

> [!question]- F2. 如果改成只能在**後面**加字元呢？
> 對稱地，答案取決於最長的**回文後綴** `s[n − L:]`，結果是 `s + reverse(s[:n − L])`。回文後綴等於「reverse(s) 的前綴與 s 的後綴最長相等」，所以對 `reverse(s) + "#" + s` 算 failure function，最後一格就是 L。也可以直接把原函式套用在 `reverse(s)` 上再整體反轉：`shortest_palindrome(s[::-1])[::-1]`。時間 O(n)。

> [!question]- F3. 如果可以在任意位置插入字元，最少要插入幾個（1312. Minimum Insertion Steps to Make a String Palindrome）？
> 這時不再只是前綴問題，要用區間 DP：答案是 `n − LPS(s)`，LPS 是最長回文**子序列**的長度，因為保留一個最長回文子序列、為其餘每個字元在對稱位置補一個字元就是最佳。DP 為 O(n²) 時間、O(n) 空間，詳見第 23 章核心題 5。本題能做到 O(n)，是因為「只能補在前面」把問題限制成了前綴與後綴的比對。

> [!question]- F4. 能用 rolling hash 一次掃描做到嗎？
> 可以。從左到右掃描，同時維護 `s[:i+1]` 的正向雜湊 `f = f·B + c` 和反向雜湊 `g = g + c·B^i`（反向雜湊就是把 `s[:i+1]` 倒過來讀的雜湊值），兩者相等代表 `s[:i+1]` 很可能是回文，記下最大的這種 i + 1 作為 L。每步 O(1)，總共 O(n) 期望時間、O(1) 額外空間。風險是碰撞會讓 L 偏大：最後用 `s[:L] == s[:L][::-1]` 驗證一次，若失敗就退回 KMP，或使用 2⁶¹ − 1 的大模數與隨機 base 讓機率可以忽略。

> [!question]- F5. 用 Manacher 怎麼做？
> 回文前綴就是「左端碰到字串開頭」的回文。跑完 Manacher 後，在轉換字串 t 中，以 i 為中心、長度 `p[i]` 的回文左端在原字串的位置是 `(i − p[i] − 1) // 2`，等於 0 時它就是回文前綴；取所有這種 i 中最大的 `p[i]` 就是 L。O(n) 時間與空間，和 KMP 一樣好，但常數與實作細節較多，所以面試中 KMP 的轉換通常是首選。

### 心得

關鍵突破是兩步化簡：「只能補在前面」⟹「找最長回文前綴」⟹「s 的前綴與 reverse(s) 的後綴的最長 border」，最後一步把回文問題變成了純粹的 failure function。它和本章其他題的關係是：難題 3（1392）是同一個 failure function 的最後一格，只是字串換成 s 本身；核心題 1、2 的回文工具（中心擴張、Manacher）在這裡也可用，但 KMP 的轉換更短。面試時先說明「為什麼只看回文前綴就夠」（鏡像論證），再提出 O(n²) 的直接檢查，最後提出 `s + "#" + reverse(s)`，並主動解釋分隔字元的用途。

## 難題 2｜1044. Longest Duplicate Substring｜Hard

### 題目

給一個字串 `s`，找出所有「在 s 中出現至少兩次」的子字串中最長的一個並回傳（兩次出現可以重疊）；有多個同樣長的答案時回傳任意一個，沒有任何重複子字串時回傳空字串。限制：`2 <= len(s) <= 3 × 10⁴`，只包含小寫英文字母。

- 範例 1：`s = "banana"`，回傳 `"ana"`，它出現在索引 1 與 3，兩次出現重疊了一個 `a`。
- 範例 2：`s = "abcd"`，回傳 `""`，沒有任何字元出現兩次。
- 範例 3（邊界）：`s = "aaaaa"`，回傳 `"aaaa"`，出現在 0 與 1。
- 範例 4：`s = "abcabcx"`，回傳 `"abc"`。

### 提示

> [!tip]- 提示 1
> 如果某個長度 L 的子字串出現兩次，那麼它去掉最後一個字元後，長度 L − 1 的子字串也出現兩次。答案的長度有單調性。

> [!tip]- 提示 2
> 對長度 L 做 binary search（第 8 章）。剩下的問題是：給定 L，能不能在 O(n) 內判斷「有沒有兩個相同的長度 L 子字串」？

> [!tip]- 提示 3
> 用 rolling hash 在 O(n) 內算出所有長度 L 窗口的雜湊，放進 dict；遇到重複的雜湊時再逐字比較確認，避免碰撞造成錯誤。總時間 O(n log n) 期望值。

### 詳解

**為什麼直覺做法太慢**。暴力枚舉所有子字串放進 set，O(n²) 個子字串、每個 O(n) 的雜湊成本，總共 O(n³)。稍好的做法是 DP：`lcp[i][j]` = 從 i 和 j 開始的最長共同前綴，`lcp[i][j] = lcp[i+1][j+1] + 1`（若 `s[i] == s[j]`），答案是最大的 `lcp[i][j]`（i < j），O(n²) 時間；n = 3 × 10⁴ 時是 4.5 × 10⁸ 次運算與同等級的記憶體，在 Python 不可行。KMP 在這裡也幫不上忙，因為我們不知道要找的 pattern 是什麼，而是要在 O(n²) 個候選中找重複。

**突破點一：長度可以二分**。「存在出現兩次的長度 L 子字串」對 L 是 T…T F…F：長度 L 的重複子字串取前 L − 1 個字元，仍然在同樣的兩個起點出現。所以答案長度是最後一個 True，可以用第 8 章的模板：找第一個「沒有重複」的 L，減一就是答案。L 的範圍是 `[1, n)`，長度 n 只有一個窗口，一定沒有重複，可以當作哨兵。

**突破點二：固定長度的重複用 rolling hash 檢查**。給定 L，所有 n − L + 1 個窗口的雜湊可以用前綴雜湊 O(1) 各算一個，放進 dict 就能 O(n) 判斷有沒有重複。碰撞的處理很重要：這裡一次會比較約 n²/2 對窗口（隱含在 dict 中），所以必須用大模數 2⁶¹ − 1 與隨機 base（25.5 節）；再加上雜湊相同時逐字比較，答案就一定正確，只有碰撞時才會多花 O(L) 時間，而碰撞極少。

```text
s = b a n a n a（n = 6），在 L ∈ [1, 6) 中找第一個「沒有重複」的 L

L = 3 的窗口：ban  ana  nan  ana
              0    1    2    3      ana 的雜湊在起點 3 再次出現 → 驗證 s[1:4] == s[3:6] ✓ → 有重複

二分過程（pred(L) = 「長度 L 沒有重複」）
步驟  lo  hi  mid  窗口                                   有重複？  pred  動作
 1     1   6   3   ban ana nan ana                          是        F    lo = 4
 2     4   6   5   banan anana                              否        T    hi = 5
 3     4   5   4   bana anan nana                           否        T    hi = 4
結束  lo = 4 → 答案長度 4 − 1 = 3，回傳 s[1:4] = "ana"
```

二分只需要 log₂ n ≈ 15 次檢查，每次 O(n)，所以總共約 4.5 × 10⁵ 次雜湊運算。第 1 步長度 3 找到 `"ana"` 的重複；第 2、3 步確認 5 和 4 都沒有，答案長度就是 3。

### 解法

```python
import random

MOD = (1 << 61) - 1


def longest_dup_substring(s: str) -> str:
    n = len(s)
    base = random.randrange(256, MOD - 1)
    h, p = [0] * (n + 1), [1] * (n + 1)
    for i, ch in enumerate(s):
        h[i + 1] = (h[i] * base + ord(ch)) % MOD
        p[i + 1] = p[i] * base % MOD

    def find(L: int) -> int:
        """回傳某個長度 L 重複子字串的起點；沒有就回傳 -1。"""
        seen: dict[int, list[int]] = {}
        for i in range(n - L + 1):
            x = (h[i + L] - h[i] * p[L]) % MOD
            for j in seen.get(x, ()):
                if s[j:j + L] == s[i:i + L]:   # 驗證，排除碰撞
                    return i
            seen.setdefault(x, []).append(i)
        return -1

    lo, hi = 1, n                          # 找第一個「沒有重複」的 L；L = n 一定沒有
    while lo < hi:
        mid = (lo + hi) // 2
        if find(mid) == -1:
            hi = mid
        else:
            lo = mid + 1
    best = lo - 1
    if best == 0:
        return ""
    start = find(best)
    return s[start:start + best]


def brute(s):
    best = 0
    for L in range(1, len(s)):
        subs = [s[i:i + L] for i in range(len(s) - L + 1)]
        if len(set(subs)) < len(subs):
            best = L
    return best


assert longest_dup_substring("banana") == "ana"
assert longest_dup_substring("abcd") == ""
assert longest_dup_substring("aaaaa") == "aaaa"
assert longest_dup_substring("abcabcx") == "abc"
rnd = "".join(random.choice("ab") for _ in range(30000))
ans = rnd and longest_dup_substring(rnd)
assert rnd.count(ans) >= 1 and rnd.find(ans) != rnd.rfind(ans)  # 最大規模也很快
for _ in range(400):
    s = "".join(random.choice("abc") for _ in range(random.randint(2, 12)))
    ans = longest_dup_substring(s)
    assert len(ans) == brute(s)
    if ans:
        assert s.find(ans) != s.rfind(ans)    # 確實出現至少兩次
print("all tests passed")
```

### 複雜度與邊界

時間 O(n log n) 期望值：二分 O(log n) 輪，每輪 O(n) 個窗口，每個雜湊 O(1)；驗證只在雜湊相同時發生，第一次真正的重複就立即回傳，碰撞造成的額外比較期望值可忽略。空間 O(n)：前綴雜湊與 dict。邊界情況：沒有任何重複字元時 `find(1)` 就失敗，lo 停在 1，回傳空字串；全部相同時答案長度 n − 1；兩次出現可以重疊，所以 find 不檢查起點間距（若題目要求不重疊，見 F3）。若不想依賴隨機性，可以改用 suffix array（F1），O(n log n) 而且是確定性的。

### Follow-up

> [!question]- F1. 有沒有確定性、不依賴雜湊的 O(n log n) 解？
> 用 suffix array：把 s 的所有後綴排序，相鄰兩個後綴的最長共同前綴（LCP）的最大值就是答案，因為任兩個後綴的 LCP 等於它們在排序中間所有相鄰 LCP 的最小值，所以最大值一定出現在某對相鄰後綴上。建 suffix array 可以用倍增法 O(n log n)（或 O(n log² n) 的排序版本），LCP 陣列用 Kasai 演算法 O(n)。程式比雜湊版本長很多，面試中通常說出思路與複雜度即可；能指出「雜湊版本是 Monte Carlo 或需要驗證，suffix array 是確定性的」就是很好的取捨討論。

> [!question]- F2. 如果改成「出現至少 k 次」的最長子字串呢？
> 單調性仍然成立（出現 k 次的子字串，其前綴也出現至少 k 次），二分框架不變；檢查函式改成用 dict 計數，某個雜湊的出現次數達到 k 時（必要時逐字驗證）回傳 True。總時間仍是 O(n log n)。用 suffix array 的話，答案是「任意連續 k − 1 個相鄰 LCP 的最小值」的最大值，可以用 sliding window 加 monotonic deque（第 6 章難題 2）在 O(n) 內求出。

> [!question]- F3. 如果兩次出現不能重疊呢（例如 1062 的變形或「最長不重疊重複子字串」）？
> 單調性仍然成立：長度 L 的兩次不重疊出現，各自去掉最後一個字元後仍不重疊。檢查函式改成：對每個雜湊記錄**最早**的起點 `first[x]`，掃到起點 i 時若 `i − first[x] >= L`（且逐字驗證相同），就找到兩次不重疊的出現。因為只需要最早的起點，dict 只存一個值。答案長度最多 n // 2，二分範圍可以縮小。總時間 O(n log n)。

> [!question]- F4. 如果要找兩個字串 A、B 的最長共同子字串呢？
> 一樣二分長度 L：把 A 所有長度 L 窗口的雜湊放進 set，再掃 B 的窗口，有任何一個在 set 中（並驗證）就代表存在長度 L 的共同子字串。單調性與本題相同，時間 O((|A| + |B|) log min(|A|, |B|)) 期望值。對比 O(|A|·|B|) 的 DP（718. Maximum Length of Repeated Subarray 的標準解，和第 22 章 LCS 的二維表同型），當兩個字串都很長時雜湊版本快得多。推廣到很多個字串就是難題 4（1923）。

> [!question]- F5. 如果要數 s 有幾個不同的子字串呢？
> 用 suffix array：每個後綴貢獻「它的長度減去它和前一個（排序後）後綴的 LCP」個新的子字串，所以答案是 `n(n + 1)/2 − Σ LCP`，O(n log n)。用雜湊的話，要對每個長度 L 分別把所有窗口雜湊放進 set 再加總大小，O(n²) 期望時間，適合 n 只有幾千的情況。另一個 O(n) 的結構是 suffix automaton，不同子字串數是 Σ (len(v) − len(link(v)))，屬於進階內容。

### 心得

關鍵突破是把「最長」拆成「二分長度」加「固定長度是否有重複」，而後者用 rolling hash 的 dict 只要 O(n)。它和本章其他題的關係是：KMP 與 Z-function 擅長「一個已知 pattern」，rolling hash 擅長「大量未知的候選同時比較」，這題是後者的代表；難題 4（1923）是同一個框架推廣到多個序列。面試時先說 O(n²) 的 LCP DP，再提出二分長度（說明單調性），然後說明雜湊的碰撞處理：大模數、隨機 base、雜湊相同時驗證；最後提一句 suffix array 是確定性的替代方案，展示你知道取捨。

## 難題 3｜1392. Longest Happy Prefix｜Hard

### 題目

一個字串的 happy prefix 是指「既是它的前綴、也是它的後綴」，但不等於整個字串本身的非空子字串。給一個字串 `s`，回傳它最長的 happy prefix；如果不存在，回傳空字串。前綴與後綴可以重疊。限制：`1 <= len(s) <= 10⁵`，只包含小寫英文字母。

- 範例 1：`s = "level"`，回傳 `"l"`；`"le"` 與 `"el"` 不同，`"lev"` 與 `"vel"` 也不同。
- 範例 2：`s = "ababab"`，回傳 `"abab"`；前綴 `"abab"`（索引 0–3）與後綴 `"abab"`（索引 2–5）重疊。
- 範例 3（邊界）：`s = "a"`，回傳 `""`，唯一的前綴就是整個字串。
- 範例 4（邊界）：`s = "aaaa"`，回傳 `"aaa"`；`s = "abc"` 回傳 `""`。

### 提示

> [!tip]- 提示 1
> 這就是 25.3 節「最長真 border」的定義，只是問的是整個字串。暴力檢查每個長度為什麼太慢？

> [!tip]- 提示 2
> 若 `s[:k]` 是 `s[:i]` 的 border，那麼 `s[:i+1]` 的 border 一定是某個 `s[:i]` 的 border 再延長一個字元。從前往後，一個一個前綴地維護最長 border。

> [!tip]- 提示 3
> 延長失敗時，次長的 border 是 `pi[k − 1]`，沿著這條鏈回跳。整個 failure function 是 O(n)，答案是 `s[:pi[n − 1]]`。

### 詳解

**為什麼直覺做法太慢**。從 L = n − 1 往下，檢查 `s[:L] == s[n − L:]`，第一個成立的就是答案。每次比較 O(L)，最差 O(n²)：例如 `"aaaa…ab"`，每個 L 都要比到最後一個字元才發現不同，n = 10⁵ 時約 5 × 10⁹ 次字元比較。Python 的切片比較是 C 實作，常數小，但漸進複雜度仍不可接受，在最差測資會超時。

**突破點：一次算出所有前綴的最長 border**。我們只要最後一個值，但「只算最後一個」並不比「算全部」容易；反而是把問題拆成每個前綴，才能利用上一個前綴的答案。設 `pi[i − 1] = k`。`s[:i+1]` 的任何 border，去掉最後一個字元後都是 `s[:i]` 的 border（或空字串），所以候選只有 `s[:i]` 的 border 鏈：k、`pi[k − 1]`、`pi[pi[k − 1] − 1]`、…，依序檢查哪一個後面接的字元等於 `s[i]`。第一個成功的就是最長的，因為鏈是由長到短排列的，而且鏈上不會漏掉任何 border（25.3 節的性質）。

**為什麼 O(n)**。k 每處理一個字元最多加 1，每次回跳至少減 1，所以回跳總次數 ≤ n。答案就是 `s[:pi[n − 1]]`。另一種同樣 O(n) 的做法是 rolling hash：從長到短比較 `s[:L]` 與 `s[n − L:]` 的前綴雜湊，每次 O(1)，第一個相等（並驗證）的就是答案。

```text
s = a b a c a b a b
index: 0 1 2 3 4 5 6 7

i  字元  起始 k=pi[i-1]  過程                                  pi[i]
1   b       0            b ≠ s[0]=a                              0
2   a       0            a == s[0]                               1   "a"
3   c       1            c ≠ s[1]=b → k=pi[0]=0；c ≠ s[0]=a       0
4   a       0            a == s[0]                               1   "a"
5   b       1            b == s[1]                               2   "ab"
6   a       2            a == s[2]                               3   "aba"
7   b       3            b ≠ s[3]=c → k=pi[2]=1（"aba" 的 border "a"）
                         b == s[1]                               2   "ab"

pi = 0 0 1 0 1 2 3 2，答案 s[:2] = "ab"

i = 7 的回跳：
  目前 border "aba"（s[0..2]）＝ s[4..6]，想延長成 "abac"，但 s[7] = b ≠ c
  "aba" 的最長 border 是 "a"，試延長成 "ab"：s[1] = b == s[7] ✓
```

最後一步展示了 failure function 為什麼能跳過中間長度：`"aba"` 延長失敗後，下一個可能的候選直接是 `"a"`，長度 2 的 `"ab"` 根本不是 `"aba"` 的 border，不必檢查。

### 解法

```python
import random

MOD = (1 << 61) - 1


def longest_prefix(s: str) -> str:
    pi = [0] * len(s)
    for i in range(1, len(s)):
        k = pi[i - 1]
        while k > 0 and s[i] != s[k]:
            k = pi[k - 1]
        if s[i] == s[k]:
            k += 1
        pi[i] = k
    return s[:pi[-1]]


def longest_prefix_hash(s: str) -> str:
    """rolling hash 版本：從長到短比較前綴與後綴的雜湊，相等時再驗證。"""
    n = len(s)
    base = random.randrange(256, MOD - 1)
    h, p = [0] * (n + 1), [1] * (n + 1)
    for i, ch in enumerate(s):
        h[i + 1] = (h[i] * base + ord(ch)) % MOD
        p[i + 1] = p[i] * base % MOD
    for L in range(n - 1, 0, -1):
        suffix = (h[n] - h[n - L] * p[L]) % MOD
        if h[L] == suffix and s[:L] == s[n - L:]:
            return s[:L]
    return ""


def brute(s):
    return next((s[:L] for L in range(len(s) - 1, 0, -1) if s[:L] == s[-L:]), "")


assert longest_prefix("level") == "l"
assert longest_prefix("ababab") == "abab"
assert longest_prefix("a") == ""
assert longest_prefix("aaaa") == "aaa"
assert longest_prefix("abc") == ""
assert longest_prefix("abacabab") == "ab"
worst = "a" * 99999 + "b"
assert longest_prefix(worst) == ""                           # 暴力解的最差型態
for _ in range(1000):
    s = "".join(random.choice("ab") for _ in range(random.randint(1, 12)))
    assert longest_prefix(s) == longest_prefix_hash(s) == brute(s)
print("all tests passed")
```

### 複雜度與邊界

KMP 版本時間 O(n)、空間 O(n)。雜湊版本時間 O(n) 期望值：前綴雜湊 O(n)，從長到短每個長度 O(1)，驗證只在雜湊相等時發生，第一個通過的就是答案。邊界情況：n = 1 時 `pi = [0]`，回傳空字串；全部相同時答案是長度 n − 1；前綴與後綴可以重疊（`"ababab"` → `"abab"`），failure function 本來就允許重疊，不需要特別處理。如果題目要求不重疊，見 F5。

### Follow-up

> [!question]- F1. 如果要列出所有 happy prefix（所有 border）呢？
> 沿著 border 鏈走：`L = pi[n − 1]`，記錄 `s[:L]`，再令 `L = pi[L − 1]`，直到 L = 0。這條鏈恰好列出所有 border，由長到短，因為「border 的 border 還是 border」，而且最長 border 之後的次長 border 一定是最長 border 的 border。鏈的長度最多 n − 1（例如全部相同的字串），總時間 O(n)。若只要個數，不必實際切出字串。

> [!question]- F2. 用 Z-function 怎麼做？
> 長度 L 的 border 存在，若且唯若後綴 `s[n − L:]` 和 s 的共同前綴長度至少是 L，也就是 `z[n − L] == L`（因為後綴的長度就是 L，等號等價於 ≥）。所以由小到大找第一個 `i ≥ 1` 滿足 `i + z[i] == n`，答案是 `s[:n − i]`，沒有這樣的 i 就是空字串。Z-function 建表 O(n)，掃描 O(n)。這個寫法和 KMP 版本一樣快，選哪一個取決於你比較熟哪個模板。

> [!question]- F3. 如果要找最長的子字串 t，使它同時是前綴、後綴，而且還在中間出現過一次（既不是前綴位置也不是後綴位置）呢？
> 候選一定是 border。最長的 border 是 `L = pi[n − 1]`；它在中間出現，若且唯若某個 `i ∈ [0, n − 2]` 有 `pi[i] >= L`（`pi[i] = M >= L` 代表 `s[:M]` 出現在 `[i − M + 1, i]`，而 `s[:L]` 是 `s[:M]` 的前綴，所以 `s[:L]` 從 `i − M + 1 >= 1` 開始、在 `i − M + L <= n − 2` 結束，確實在中間；反過來，`s[:L]` 若在中間某個位置 e 結尾，就有 `pi[e] >= L`）。若不成立，就改用次長的 border `pi[L − 1]`：它是 `s[:L]` 的後綴，在 L − 1 結尾出現，而 L − 1 < n − 1 且起點 > 0，所以一定在中間出現過，只要長度大於 0 就是答案。總時間 O(n)。
> ```python
> def password(s):
>     n, pi = len(s), prefix_function(s)          # prefix_function 見 25.3 節
>     if n < 3:
>         return ""
>     L = pi[-1]
>     if L and L <= max(pi[:n - 1]):
>         return s[:L]
>     return s[:pi[L - 1]] if L else ""
> ```

> [!question]- F4. 如果要算出每個前綴在 s 中出現的次數呢？
> 每個位置 i 結尾的所有 border 都是「在 i 結尾的某個前綴出現」，所以先令 `cnt[pi[i]] += 1`，再由長到短傳遞：`for L in range(n − 1, 0, −1): cnt[pi[L − 1]] += cnt[L]`，把長度 L 的 border 出現次數加給它的最長 border（border 的 border 也同時出現），最後每個長度再加 1（前綴本身的那一次）。O(n) 時間，得到所有前綴的出現次數，常用於「出現次數 × 長度」最大化之類的題目。

> [!question]- F5. 如果要求前綴和後綴不能重疊呢？
> 不重疊代表長度 L ≤ n // 2。沿著 F1 的 border 鏈由長到短走，第一個 ≤ n // 2 的長度就是答案；因為鏈列出了所有 border，不會漏掉。最差仍是 O(n)。例如 `"ababab"` 的 border 鏈是 4、2，第一個 ≤ 3 的是 2，答案 `"ab"`。也可以用雜湊直接從 L = n // 2 往下比較，O(n) 期望值。

### 心得

關鍵突破是：只要整個字串的最長 border，卻要先算出每個前綴的最長 border，因為後者有「沿 border 鏈延長」的遞推結構。這題就是 failure function 本身，難題 1（214）把它套在 `s + "#" + reverse(s)` 上、核心題 4（459）把 `n − pi[n − 1]` 解讀成最短週期，核心題 3（28）把同一個鏈用在比對上。面試時先說 O(n²) 的直接比較並指出最差情況，再說「我維護每個前綴的最長 border」，並把一次回跳畫出來（例如本題的 `"abacabab"`），最後用攤銷論證說明 O(n)。

## 難題 4｜1923. Longest Common Subpath｜Hard

### 題目

一個國家有 n 座城市，編號 0 到 n − 1。有 m 位朋友，第 i 位朋友走過的路徑是城市序列 `paths[i]`（相鄰城市不同，但同一座城市可以出現多次）。回傳所有朋友的路徑**共同擁有**的最長連續子路徑長度；沒有任何共同城市時回傳 0。限制：`1 <= n <= 10⁵`，`2 <= m <= 10⁵`，所有路徑總長度 ≤ 10⁵，`0 <= paths[i][j] < n`。

- 範例 1：`n = 5`，`paths = [[0,1,2,3,4], [2,3,4], [4,0,1,2,3]]`，回傳 `2`，共同子路徑是 `[2, 3]`。
- 範例 2：`n = 3`，`paths = [[0], [1], [2]]`，回傳 `0`。
- 範例 3：`n = 5`，`paths = [[0,1,2,3,4], [4,3,2,1,0]]`，回傳 `1`；方向相反不算相同的子路徑。
- 範例 4（邊界）：所有路徑都相同時，答案是路徑長度。

### 提示

> [!tip]- 提示 1
> 共同子路徑長度 L 存在，則 L − 1 也存在。可以對 L 做 binary search，上界是最短路徑的長度。

> [!tip]- 提示 2
> 給定 L，對每條路徑算出所有長度 L 窗口的「指紋」，取所有路徑的指紋集合的交集，非空就代表存在長度 L 的共同子路徑。

> [!tip]- 提示 3
> 指紋用 rolling hash，把城市編號當作字元。總長度 N ≤ 10⁵，每次檢查 O(N)，總共 O(N log N)。碰撞要用大模數或雙 hash，因為交集比較的對數很多。

### 詳解

**為什麼直覺做法太慢**。兩條路徑的最長共同子陣列可以用 O(|A|·|B|) 的 DP（718 題），但 m 條路徑的共同子路徑不能兩兩合併：A 和 B 的最長共同片段不一定是三者的共同片段的來源，必須保留「所有共同片段」，資訊量太大。枚舉最短路徑的所有 O(len²) 個子路徑、逐一到其他路徑中搜尋，也是 O(N²) 以上，總長度 10⁵ 時不可行。

**突破點：二分長度，每個長度用雜湊集合求交集**。若長度 L 的子路徑 P 是所有人共有的，P 的前 L − 1 個城市也是共有的，所以可行性對 L 單調，用第 8 章的模板二分，範圍 `[0, min_len]`。給定 L，對每條路徑用 rolling hash 在 O(len) 內算出所有長度 L 窗口的雜湊，放進一個 set（同一條路徑裡重複的窗口自動去重），再和前面所有路徑的 set 取交集；交集一旦變空就提早結束。每次檢查 O(N)，二分 O(log N) 次。

**碰撞的分析**。這題沒辦法像難題 2 一樣在雜湊相同時「驗證」，因為交集裡的一個雜湊可能來自不同路徑的不同位置，要驗證就得記錄位置並逐一比較，成本很高。所以必須讓碰撞機率本身可以忽略：使用模數 2⁶¹ − 1 與隨機 base，每次檢查中兩兩可能碰撞的窗口對最多約 N² = 10¹⁰ 對，每對碰撞機率至多 L / M ≈ 10⁵ / 2.3 × 10¹⁸，每次檢查的風險上界約 10⁻³ 量級（這是很鬆的上界，實際遠小於此）；若要更保險，就用兩組模數的雙 hash，把雜湊值組成 tuple。城市編號直接當作字元值，加 1 避免 0 號城市讓不同長度的序列有相同的值（固定長度的窗口其實不會受影響，但加 1 是好習慣）。

```text
paths = [[0,1,2,3,4], [2,3,4], [4,0,1,2,3]]，min_len = 3，範圍 L ∈ [0, 3]

L = 2：
  路徑 0 的窗口：(0,1) (1,2) (2,3) (3,4)
  路徑 1 的窗口：(2,3) (3,4)
  路徑 2 的窗口：(4,0) (0,1) (1,2) (2,3)
  交集 = {(2,3)} → 非空，可行

L = 3：
  路徑 0：(0,1,2) (1,2,3) (2,3,4)
  路徑 1：(2,3,4)
  路徑 2：(4,0,1) (0,1,2) (1,2,3)
  路徑 0 ∩ 路徑 1 = {(2,3,4)}，再 ∩ 路徑 2 = ∅ → 不可行

二分（找第一個「不可行」的 L，範圍 [1, 4)，L = 4 超過最短路徑一定不可行）
步驟  lo  hi  mid  可行？  動作
 1     1   4   2    是     lo = 3
 2     3   4   3    否     hi = 3
結束  lo = 3 → 答案 3 − 1 = 2
```

在 L = 3 時，路徑 0 與路徑 1 共有 `(2,3,4)`，但路徑 2 在 3 之後就結束了，所以交集變空。實作中，從最短的路徑開始建 set、之後只保留交集，可以讓 set 越來越小。

### 解法

```python
import random

MOD = (1 << 61) - 1


def longest_common_subpath(n: int, paths: list[list[int]]) -> int:
    base = random.randrange(n + 2, MOD - 1)
    paths = sorted(paths, key=len)          # 從最短的開始，交集最小
    prefix = []
    for path in paths:
        h = [0] * (len(path) + 1)
        for i, city in enumerate(path):
            h[i + 1] = (h[i] * base + city + 1) % MOD
        prefix.append(h)
    max_len = len(paths[0])
    pw = [1] * (max_len + 1)
    for i in range(max_len):
        pw[i + 1] = pw[i] * base % MOD

    def common(L: int) -> bool:
        shared = None
        for path, h in zip(paths, prefix):
            cur = {(h[i + L] - h[i] * pw[L]) % MOD for i in range(len(path) - L + 1)}
            shared = cur if shared is None else shared & cur
            if not shared:
                return False
        return True

    lo, hi = 1, max_len + 1                 # 找第一個不可行的 L；max_len + 1 一定不可行
    while lo < hi:
        mid = (lo + hi) // 2
        if not common(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo - 1


def brute(paths):
    best = 0
    first = paths[0]
    for i in range(len(first)):
        for j in range(i + 1, len(first) + 1):
            sub = first[i:j]
            L = len(sub)
            if L > best and all(any(p[k:k + L] == sub for k in range(len(p) - L + 1)) for p in paths):
                best = L
    return best


assert longest_common_subpath(5, [[0, 1, 2, 3, 4], [2, 3, 4], [4, 0, 1, 2, 3]]) == 2
assert longest_common_subpath(3, [[0], [1], [2]]) == 0
assert longest_common_subpath(5, [[0, 1, 2, 3, 4], [4, 3, 2, 1, 0]]) == 1
assert longest_common_subpath(4, [[0, 1, 2, 3], [0, 1, 2, 3]]) == 4
big = [random.randrange(100000) for _ in range(50000)]
assert longest_common_subpath(100000, [big, list(big)]) == 50000   # 總長 10⁵ 也很快
for _ in range(400):
    k = random.randint(2, 4)
    ps = [[random.randrange(3) for _ in range(random.randint(1, 7))] for _ in range(k)]
    assert longest_common_subpath(3, ps) == brute(ps)
print("all tests passed")
```

### 複雜度與邊界

時間 O(N log L_min) 期望值，N 是路徑總長、L_min 是最短路徑長度：每次檢查對每條路徑做 O(len) 的雜湊與 set 運算，二分 O(log L_min) 次。空間 O(N)，存每條路徑的前綴雜湊與一個 set。邊界情況：沒有共同城市時 `common(1)` 就失敗，回傳 0；只有一座城市出現在所有路徑時答案 1；同一條路徑內重複的子路徑由 set 自動去重，不會被誤認為「出現在兩條路徑」；所有路徑都相同時答案是 L_min，hi 的哨兵 `max_len + 1` 不會真的被檢查到（在 `common` 中它的窗口數是 0，交集為空，邏輯上也正確）。注意這裡的 `max_len` 指排序後最短路徑的長度。

### Follow-up

> [!question]- F1. 如果要回傳那條共同子路徑本身呢？
> 二分得到答案長度 L* 之後，再跑一次 `common(L*)`，但讓第一條路徑的 set 改成 dict：雜湊 → 起點。最後交集中任意一個雜湊，都能從 dict 找回第一條路徑中的起點 i，回傳 `paths[0][i : i + L*]`。若擔心碰撞，可以拿這個候選到每條路徑中用 KMP（核心題 3）驗證一次，O(N)，驗證失敗再換交集中的下一個雜湊。

> [!question]- F2. 如果只要求「至少 k 位朋友」共有，而不是全部呢？
> 單調性仍然成立。檢查函式改成：對每條路徑算出它的窗口雜湊 set（同一路徑內去重），用一個 Counter 累計每個雜湊出現在幾條路徑中，有任何雜湊的計數 ≥ k 就可行。每次檢查 O(N)，總時間仍是 O(N log L)。注意二分的上界要改成「第 k 長的路徑長度」，因為長度 L 的子路徑只能出現在長度 ≥ L 的路徑中，比第 k 長的路徑還長時，夠長的路徑不到 k 條。

> [!question]- F3. 有沒有不依賴雜湊的確定性解？
> 用 suffix array：把所有路徑串接起來，中間放互不相同、且不出現在城市編號中的分隔符（例如 n、n + 1、…），每個後綴標記它屬於哪條路徑。在 suffix array 上用 sliding window 找「包含所有 m 種標記的最短連續區間」，區間內相鄰 LCP 的最小值（用 monotonic deque 維護）就是一個候選答案，取最大值。建 suffix array O(N log N)，sliding window O(N)。實作量大，面試中說出結構即可；雜湊解的程式短很多，是實務上更常見的答案。

> [!question]- F4. 如果路徑數 m 很大（例如 10⁵ 條，每條長度 1）呢？
> 總長度 N 的限制讓複雜度仍然是 O(N log L_min)，因為每次檢查只對每條路徑做 O(len) 的工作。重點是實作細節：從最短的路徑開始建 set，交集只會越來越小；一旦交集為空立即回傳 False，避免繼續處理後面的路徑。此外 L_min = 1 時，二分只需要檢查 L = 1，等於問「是否有一座城市出現在每條路徑中」，可以直接用 set 交集 O(N) 解決。

> [!question]- F5. 為什麼這題要特別在意雜湊的碰撞機率？用 10⁹ + 7 會怎樣？
> 交集運算中，任何兩條路徑的任何兩個窗口雜湊相同都會被當成「共同」，所以有效的比較次數是 N² 級（約 10¹⁰）。若模數只有 10⁹ 左右，期望碰撞數就是好幾個，答案很可能偏大，而且這種錯誤無法從結果看出來。解法是模數 2⁶¹ − 1（Python 不會溢位，直接取模）、隨機 base，或兩組 10⁹ 級模數的雙 hash 組成 tuple。這正是 25.5 節「生日悖論」的實際體現：單次比較的機率很小，但比較次數太多。

### 心得

關鍵突破是「多個序列的共同片段」不能兩兩合併，但「固定長度的共同片段」可以用 set 交集一次判斷，再加上長度的單調性就能二分。它是難題 2（1044）的直接推廣：1044 問「一個字串裡兩個位置相同」，這題問「m 條序列裡都有」，兩者都是二分長度加 rolling hash，差別只在檢查函式從 dict 找重複變成 set 求交集。面試時先說明單調性與二分範圍，再說明為什麼要用 set 去重（同一條路徑內的重複不算），最後主動討論碰撞：比較次數是 N² 級，所以模數要大到 2⁶¹ 或用雙 hash。

## 難題 5｜2223. Sum of Scores of Built Strings｜Hard

### 題目

你從空字串開始，每次在**前面**加上一個字元，依序得到長度 1、2、…、n 的字串 s₁、s₂、…、sₙ，最後 sₙ 等於給定的字串 `s`。換句話說，sᵢ 是 s 長度 i 的後綴。sᵢ 的分數是 sᵢ 與 s 的最長共同前綴長度。回傳所有 sᵢ 的分數總和。限制：`1 <= len(s) <= 10⁵`，只包含小寫英文字母。

- 範例 1：`s = "babab"`，s₁ = `"b"`（分數 1）、s₂ = `"ab"`（0）、s₃ = `"bab"`（3）、s₄ = `"abab"`（0）、s₅ = `"babab"`（5），總和 `9`。
- 範例 2：`s = "azbazbzaz"`，總和 `14`：s₉ 貢獻 9、s₆ = `"azbzaz"` 貢獻 3、s₂ = `"az"` 貢獻 2，其餘為 0。
- 範例 3（邊界）：`s = "a"`，回傳 `1`。
- 範例 4（邊界）：`s = "aaaa"`，回傳 `4 + 3 + 2 + 1 = 10`。

### 提示

> [!tip]- 提示 1
> sᵢ 就是 `s[n − i:]`。所有分數的總和，就是「每個後綴 `s[j:]` 和 s 的最長共同前綴」加總。

> [!tip]- 提示 2
> 這正是 25.4 節 Z-function 的定義：`z[j]` = s 和 `s[j:]` 的最長共同前綴，`z[0] = n`。

> [!tip]- 提示 3
> 答案是 `sum(z)`。Z-box 讓建表成為 O(n)：在 box `[l, r)` 內借用 `z[i − l]`，只有碰到 r 才往外比較。

### 詳解

**為什麼直覺做法太慢**。對每個後綴逐字和 s 比較，O(n²)；`"aaaa…a"` 時每個後綴都要比到底，n = 10⁵ 時是 5 × 10⁹。用 rolling hash 加二分可以把每個後綴的 LCP 降到 O(log n)，總共 O(n log n)，已經能過（見 F1）；但這題就是 Z-function 的定義，可以做到 O(n) 而且沒有碰撞風險。

**突破點：Z-box 的重複利用**。假設已經知道某個 `[l, r)` 滿足 `s[l:r] == s[0:r − l]`（右端 r 是目前最遠的）。對 box 內的位置 i，`s[i:r]` 和 `s[i − l : r − l]` 是同一段字串，所以 `s[i:]` 和 s 的共同前綴，在 r 之前的部分和 `s[i − l:]` 與 s 的共同前綴相同，也就是 `z[i − l]`。若 `z[i − l] < r − i`，答案就是 `z[i − l]`，完全不需要比較；若 `z[i − l] >= r − i`，我們只確定至少有 `r − i`，從 r 開始往外逐字比較，每比對成功一次 r 就往右推一格。r 只往右走，最多走 n 步，所以總共 O(n)。

**正確性與答案大小**。`z[0] = n` 對應 sₙ = s 本身的分數 n，題目也把它算進去，所以答案是 `sum(z)`，不用另外加。答案最大是 `"aaaa…"` 的 n(n + 1)/2 ≈ 5 × 10⁹，超過 32 位元，在 Java／C++ 要用 64 位元。

```text
s = b a b a b（n = 5）
index:  0  1  2  3  4
s:      b  a  b  a  b

i=1  不在 box 內，逐字比：s[1]=a vs s[0]=b ✗                   z[1]=0
i=2  不在 box 內，逐字比：bab vs bab ✓✓✓，到達結尾               z[2]=3，box=[2,5)
i=3  在 box [2,5) 內，鏡像 i−l = 1，z[1] = 0 < r−i = 2           z[3]=0（不必比較）
i=4  在 box 內，鏡像 i−l = 2，z[2] = 3 ≥ r−i = 1 → 至少 1
     從 r = 5 往外比：已到字串結尾                                z[4]=1

z = 5 0 3 0 1
     │   │   └ s₁ = "b"     分數 1
     │   └──── s₃ = "bab"   分數 3
     └──────── s₅ = "babab" 分數 5
總和 = 9
```

i = 3 與 i = 4 都落在 box 內：i = 3 直接借用鏡像的 0，完全沒有比較字元；i = 4 借用的值被 box 的右端截斷成 1，再嘗試往外延伸時已經到了字串尾端。

### 解法

```python
import random


def sum_scores(s: str) -> int:
    n = len(s)
    z = [0] * n
    z[0] = n
    l = r = 0
    for i in range(1, n):
        if i < r:
            z[i] = min(r - i, z[i - l])
        while i + z[i] < n and s[z[i]] == s[i + z[i]]:
            z[i] += 1
        if i + z[i] > r:
            l, r = i, i + z[i]
    return sum(z)


def brute(s):
    total = 0
    for j in range(len(s)):
        k = 0
        while j + k < len(s) and s[k] == s[j + k]:
            k += 1
        total += k
    return total


assert sum_scores("babab") == 9
assert sum_scores("azbazbzaz") == 14
assert sum_scores("a") == 1
assert sum_scores("aaaa") == 10
assert sum_scores("a" * 100000) == 100000 * 100001 // 2      # 最差情況仍是線性
for _ in range(1000):
    s = "".join(random.choice("ab") for _ in range(random.randint(1, 14)))
    assert sum_scores(s) == brute(s)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每個 i 的「借用」是 O(1)，逐字比較中成功的次數總和不超過 n（每次讓 r 加 1），失敗的次數每個 i 最多一次。空間 O(n) 存 z 陣列；只要總和的話，z 仍然需要保留，因為後面的位置會借用前面的值。邊界情況：n = 1 時答案 1；全部相同時 `z = n, n − 1, …, 1`，總和 n(n + 1)/2；`min(r − i, z[i − l])` 中的 `r − i` 不能省，否則會把 box 外沒有比對過的部分當成已知。

### Follow-up

> [!question]- F1. 如果不用 Z-function，用 rolling hash 怎麼做？
> 建前綴雜湊後，任何兩個子字串可以 O(1) 比較相等。對每個起點 j，用 binary search（第 8 章）找最大的 L 使 `s[j : j + L]` 與 `s[:L]` 雜湊相同，這個「相等」對 L 是 T…T F…F，所以二分成立。每個 j 是 O(log n)，總共 O(n log n) 期望時間。這個「雜湊＋二分求 LCP」的零件比 Z-function 更通用：它能回答**任意兩個**位置的 LCP，而 Z-function 只能回答「和整個字串開頭」的 LCP。

> [!question]- F2. 如果分數改成和另一個字串 t 的最長共同前綴呢？
> 對 `t + "#" + s` 算 Z-function，`#` 不出現在兩個字串中；s 的每個後綴 `s[j:]` 在新字串的位置是 `len(t) + 1 + j`，它的 z 值就是和 t 的最長共同前綴（`#` 保證不會超過 len(t)）。總和就是這些 z 值的總和，O(|s| + |t|)。這也是用 Z-function 做字串搜尋的原理：z 值等於 len(t) 的位置就是 t 的出現。

> [!question]- F3. 如果有 q 次查詢「後綴 i 和後綴 j 的最長共同前綴」呢？
> Z-function 只處理「和開頭比」，任意兩個後綴需要別的工具。做法一：前綴雜湊加二分，每次 O(log n)，總共 O(n + q log n) 期望值，實作最短。做法二：suffix array 加 LCP 陣列，兩個後綴的 LCP 等於它們在 suffix array 中位置之間的 LCP 區間最小值，用 sparse table 做到每次 O(1)，預處理 O(n log n)。面試中通常回答做法一，並提到做法二是確定性且查詢更快的版本。

> [!question]- F4. 能用 prefix function（KMP 的表）算出同樣的答案嗎？
> 可以。總和等於「所有 (起點 j, 長度 L ≥ 1) 使 `s[j : j + L] == s[:L]`」的配對數；換成以結尾 e = j + L − 1 來數，就是「在 e 結尾、而且等於某個前綴的子字串個數」，也就是 `s[:e + 1]` 的 border 鏈長度加 1（前綴本身）。令 `cnt[e] = 1 + cnt[pi[e] − 1]`（`pi[e] = 0` 時為 1），答案是 `sum(cnt)`，O(n)。
> ```python
> def sum_scores_pi(s):
>     pi, cnt = prefix_function(s), [0] * len(s)    # prefix_function 見 25.3 節
>     for e in range(len(s)):
>         cnt[e] = 1 + (cnt[pi[e] - 1] if pi[e] else 0)
>     return sum(cnt)
> ```
> 這個對照說明了 Z-function 與 prefix function 是同一份資訊的兩種排列：一個以起點為索引，一個以終點為索引。

### 心得

關鍵突破是看出「每個 built string 的分數」正是 Z-function 的定義，於是整題變成 Z-function 加總。真正需要理解的是 Z-box：box 內的位置可以借用鏡像位置的答案，但只能信任到 box 的右端，之後必須自己比；r 只往右走，所以總時間 O(n)。這和 25.6 節 Manacher 的「鏡像借用、右端推進」是同一個攤銷論證。和本章其他題的關係：Z-function 和 prefix function 可以互相轉換（F4），所以難題 3（1392）也能用 Z 解，本題也能用 KMP 的表解。面試時先說 O(n²) 的直接比較，再指出這是 Z-function，畫出 Z-box 的借用過程，並提醒答案要用 64 位元整數。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 單一 pattern 搜尋 | 在 text 中找 pat，n、m 都大 | KMP 的 failure function（串流、O(m) 空間），或對 `pat + "#" + text` 做 Z | 核心題 3（28）、796、1408 |
| Border 與週期 | 「前綴等於後綴」「由某段重複而成」「最短週期」 | `pi[n − 1]` 是最長 border；`n − pi[n − 1]` 是最短週期，整除 n 才是重複字串 | 核心題 4（459）、難題 3（1392）、1668 |
| 循環結構攤平 | 旋轉、無限重複、環狀字串 | 用 `s + s` 或 `a × (q + 1)` 把循環變成線性，再做一次搜尋；先證明重複次數上界 | 核心題 5（686）、796、1888 |
| 每個後綴對開頭的 LCP | 「每個後綴和原字串共同前綴」「以每個位置開始的匹配長度」 | Z-function，Z-box 借用鏡像值 | 難題 5（2223）、3031 |
| 回文轉成 border | 在前面／後面補字元成回文、最長回文前綴 | `s + "#" + reverse(s)` 的 failure function | 難題 1（214） |
| 回文子字串 | 最長、計數、判斷區間是否回文 | 中心擴張 O(n²)／O(1) 空間；Manacher O(n) | 核心題 1（5）、核心題 2（647）、132、1745 |
| 二分長度＋雜湊 | 「最長的重複／共同子字串」，候選太多無法逐一搜尋 | 長度有單調性；固定長度時把所有窗口雜湊放進 set／dict，大模數、隨機 base、必要時驗證 | 難題 2（1044）、難題 4（1923）、718、1062 |
| 雜湊作為零件 | 大量子字串比較、O(1) 判斷兩段是否相同 | 前綴雜湊 `H[r] − H[l]·B^(r−l)`；搭配二分求任意 LCP | 30（第 4 章難題 2）、336（第 4 章難題 4）、1316 |
| 多 pattern 搜尋 | 很多個 pattern 同時找 | Trie 加 failure link（Aho-Corasick） | 1032 Stream of Characters、第 13 章 |

**下限與上限**。最簡單的形式是「一個 pattern 找一次」（28），只要正確寫出 failure function 與比對迴圈；或是「找最長回文」（5），中心擴張就足夠。中間層考的是對表的**解讀**：459 把 `n − pi[n − 1]` 讀成週期、686 要先證明重複次數的上界、214 要把回文前綴轉成 border。上限的題目難在三件事：第一，**工具本身沒有直接給答案**，必須做一次轉換（214 的反轉串接、2223 看出 Z 的定義）；第二，**要和其他 pattern 組合**，1044 與 1923 是第 8 章的二分答案加上 rolling hash，檢查函式還要考慮去重與交集；第三，**要對隨機性負責**，說清楚碰撞機率、為什麼要大模數與隨機 base、什麼時候可以驗證、什麼時候只能讓機率可忽略。

**與其他 pattern 的關係**。KMP 的 failure link 推廣到 trie 上就是 Aho-Corasick（第 13 章）；固定長度窗口的雜湊是第 6 章 sliding window 的一種，只是窗口內維護的是指紋而不是計數；「二分長度」完全是第 8 章答案空間二分的模板。回文問題和第 23 章的區間 DP 最容易混淆：**子字串**（連續）用本章的中心擴張或 Manacher，**子序列**（可跳選）用 DP，例如 516 最長回文子序列、1312 最少插入次數。最長共同**子序列**（1143，第 22 章）也是 DP，但最長共同**子字串**可以用本章的二分加雜湊做到接近線性。

**容易混淆之處**。第一，`pi` 的索引與長度差 1：`pi[i]` 是長度 i + 1 前綴的 border 長度，回跳寫 `pi[k − 1]`。第二，「有週期」不等於「是重複字串」：`"abababa"` 有週期 2，但不能整齊切成重複單位，必須檢查整除。第三，rolling hash 的碰撞機率要看**比較次數**，而不是單次機率：放進 set 的 n 個窗口隱含 n² 對比較。第四，Python 的內建 `in`／`find` 在面試中通常可以用來寫暴力解或驗證，但若題目本身就是「實作字串搜尋」，要先問清楚能不能用。

## 本章重點整理

- 字串比對的浪費來自「失敗後丟掉已比對的資訊」；KMP 與 Z-function 把 pattern 自身的重疊結構預先算好，讓 text 的指標永不後退，O(n + m)。
- `pi[i]` 是 `s[:i+1]` 的最長真 border；所有 border 是沿著 `pi[k − 1]` 回跳得到的鏈，建表與比對都是「能延長就延長，否則沿鏈回跳」。
- KMP 的 O(n) 來自攤銷論證：k 每步最多加 1、每次回跳至少減 1；Z-function 與 Manacher 則是「右端 r 只往右走」。
- 最短週期是 `n − pi[n − 1]`，只有整除 n 時字串才是重複字串；`s in (s + s)[1:-1]` 是等價的一行判斷。
- Z-function 的 `z[i]` 是 s 與 `s[i:]` 的 LCP；Z-box 內借用 `z[i − l]`，但不能超過 `r − i`。以起點為索引的問題用 Z，以終點為索引的問題用 prefix function。
- Rolling hash 把子字串變成可 O(1) 更新與比較的整數；前綴雜湊 `H[r] − H[l]·B^(r−l)` 讓任意子字串 O(1) 取得指紋。
- 碰撞風險取決於比較次數：大量窗口放進 set 時用 2⁶¹ − 1 或雙 hash、base 要隨機；能驗證時就在雜湊相同後逐字比較一次。
- 「最長的重複／共同子字串」用二分長度加雜湊：長度有單調性，固定長度時用 dict 找重複（1044）或 set 求交集（1923）。
- 回文由中心決定且同中心的回文巢狀：中心擴張 O(n²)、O(1) 空間是面試首選；2n − 1 個中心，奇偶都要試。
- Manacher 用「鏡像位置的半徑可以借用、碰到右端才擴張」做到 O(n)；插入 `#` 統一奇偶，`p[i]` 即原回文長度。
- 在前面補字元成回文 = 找最長回文前綴 = `s + "#" + reverse(s)` 的最後一個 `pi`；分隔字元防止 border 跨過接縫。
- 先分辨 substring 與 subsequence：本章工具只處理連續片段，子序列問題請回到第 22、23 章的 DP。
