---
chapter: 4
title: Hashing 與計數
part: 1
---

# 第 4 章　Hashing 與計數

> [!abstract] 本章地圖
> **一句話**：把「往回找某個東西」從 O(n) 的掃描變成 O(1) 的查表；關鍵在於決定**表裡存什麼（key）、存它的什麼（value）、什麼時候放進去**。
>
> **辨識訊號**：
> - 「有沒有兩個數／兩個字串滿足某個關係」，暴力解是兩層迴圈，內層只是在找「某個特定值是否出現過」
> - 「分組」「是否互為 anagram」「同一條線上」：需要一個把等價物件映射到同一個值的 canonical key（標準形）
> - 「出現幾次」「頻率相同」「最多的那個」：計數，甚至是「計數的計數」
> - 題目要 O(n)，但輸入沒有排序、排序又會破壞要回傳的索引
> - 多個陣列各選一個湊出目標值：把一半的組合先存起來，另一半來查（meet in the middle）
> - 值域 1..n 且要求 O(1) 額外空間：把陣列本身當成 hash table
>
> **核心題**：1、49、128、454、554
>
> **難題**：41、30、149、336、1224

## 4.1 這個 Pattern 解決什麼問題

先看一個最小的例子。給一份 n 筆的交易金額清單，問有沒有兩筆加起來剛好是 100。最直接的做法是兩層迴圈檢查每一對，O(n²)。仔細看內層迴圈在做什麼：外層固定了第 j 筆金額 x 之後，內層其實只在問一件事：「100 − x 這個值，在前面出現過嗎？」它是一個**查詢**，而不是一個需要逐一比較的計算。只要能在 O(1) 回答這個查詢，整個問題就是 O(n)。

Hash table（雜湊表，Python 的 `dict` 與 `set`）就是為這種查詢而生的資料結構。它用一個雜湊函式把 key 轉成陣列位置，平均 O(1) 完成插入與查詢。代價是 O(n) 的額外空間，以及「平均」兩個字：最差情況下所有 key 撞在同一個位置，每次操作會退化成 O(n)。在面試中，除非面試官特別追問，`dict` 與 `set` 的操作一律視為 O(1)，但要知道這個假設的前提（4.5 節）。

Hashing 這個 pattern 真正的難點不在 `dict` 的用法，而在三個設計決定。第一，**key 是什麼**：Two Sum 的 key 是數值；Group Anagrams 的 key 是「把字母排序後的字串」；Max Points on a Line 的 key 是「約分後的斜率」。key 必須讓「應該被視為相同的東西」剛好映射到同一個 key。第二，**value 是什麼**：存索引（要回傳位置時）、存次數（要計數時）、存一串元素（要分組時），還是存長度（要合併區段時）。第三，**什麼時候放進表裡**：先查再放，表裡永遠只有「目前元素之前」的東西，這能自然避免元素和自己配對，也讓計數不重複。

本章的十題可以看成這三個決定的各種組合。核心題 1（Two Sum）是「先查再放」的標準形；核心題 2（Group Anagrams）練 key 的設計；核心題 3（Longest Consecutive Sequence）用 set 取代排序，並引入攤銷分析；核心題 4（4Sum II）是 meet in the middle，把 O(n⁴) 拆成兩個 O(n²)；核心題 5（Brick Wall）把幾何問題轉成「哪個值出現最多次」。難題則把這些零件推到極限：把陣列當 hash table（41）、在滑動視窗中維護計數差（30）、斜率的正規化（149）、對字串的切分做查表（336）、維護「計數的計數」（1224）。

## 4.2 辨識訊號

| 題目特徵 | 為什麼是 hashing | 本章哪一題 |
|---|---|---|
| 「找兩個元素使得 f(a, b) = 目標」，而且給定 b 能直接算出需要的 a | 內層迴圈變成一次查表：查 `target − b` 或 `g(b)` 是否出現過 | 核心題 1（1） |
| 「把互相等價的東西分在一起」 | 設計 canonical key，等價 ⇔ key 相同，用 `dict[key].append` | 核心題 2（49）、難題 3（149） |
| 「最長連續數字」「下一個存在嗎」，要 O(n) 而排序是 O(n log n) | `set` 提供 O(1) 的「x + 1 在不在」，再用起點判斷避免重複工作 | 核心題 3（128） |
| 從 2–4 個集合各選一個，計算湊出目標的組合數 | 前半的組合存成 `Counter`，後半的組合來查，O(n⁴) → O(n²) | 核心題 4（454） |
| 「哪個位置／值最多人共享」 | 對每個候選值計數，取最大次數 | 核心題 5（554）、難題 3（149） |
| 值域剛好是 1..n、要求 O(1) 額外空間 | 索引本身就是 key，陣列本身就是 hash table | 難題 1（41） |
| 字串中找「由一組詞以任意順序拼成」的子字串 | 視窗內的詞頻 `Counter` 和目標詞頻比較，用滑動視窗維護 | 難題 2（30） |
| 兩個字串串接成某種性質（回文、相等） | 把每個字串切成兩半，一半要滿足性質、另一半去表裡查 | 難題 4（336） |
| 「所有值的出現次數都相同」「頻率的分佈」 | 再開一張表記錄「出現 f 次的值有幾個」（計數的計數） | 難題 5（1224） |

一個實用的反向檢查：如果你要查的不是「某個確切的值」，而是「最接近的值」「比 x 小的最大值」「某個範圍內的值」，hash table 就幫不上忙，因為它不保留順序。這時要換成排序加 binary search（第 8 章）、two pointers（第 5 章）、平衡樹，或第 26 章的 Fenwick Tree／Segment Tree 這類 range query 結構。

## 4.3 模板與原理：先查再放、分組、計數

本章的大部分題目都由下面三個模板組成。它們都只有幾行，但每一行的順序都有理由。

```python
from collections import Counter, defaultdict
from typing import Callable, Hashable, Iterable


def find_pair(nums: list[int], target: int) -> tuple[int, int] | None:
    """先查再放：回傳任一組 i < j 使 nums[i] + nums[j] == target。"""
    seen: dict[int, int] = {}            # 值 → 它在前面出現的索引
    for j, x in enumerate(nums):
        need = target - x
        if need in seen:                 # 只查 j 之前的元素
            return seen[need], j
        seen[x] = j                      # 查完才把自己放進去
    return None


def count_pairs(nums: list[int], target: int) -> int:
    """先查再放的計數版：有幾組 i < j 使 nums[i] + nums[j] == target。"""
    seen: Counter[int] = Counter()
    total = 0
    for x in nums:
        total += seen[target - x]        # 前面每個 target - x 都能和 x 配一對
        seen[x] += 1
    return total


def group_by(items: Iterable, key: Callable[[object], Hashable]) -> list[list]:
    """分組：key 相同的元素放在同一組，保留第一次出現的順序。"""
    groups: defaultdict[Hashable, list] = defaultdict(list)
    for it in items:
        groups[key(it)].append(it)
    return list(groups.values())


assert find_pair([2, 7, 11, 15], 9) == (0, 1)
assert find_pair([3, 3], 6) == (0, 1)               # 重複值也能配對
assert find_pair([3, 2, 4], 6) == (1, 2)            # 不會把 3 和自己配對
assert find_pair([1, 2], 7) is None
assert find_pair([], 0) is None
assert count_pairs([1, 1, 1], 2) == 3               # C(3, 2) 組
assert count_pairs([1, 5, 7, -1, 5], 6) == 3        # (1,5) (1,5) (7,-1)
assert count_pairs([], 0) == 0
assert group_by(["ab", "c", "ba", "d"], len) == [["ab", "ba"], ["c", "d"]]
assert group_by(["eat", "tea", "tan"], lambda s: "".join(sorted(s))) == [["eat", "tea"], ["tan"]]
assert group_by([], len) == []
print("all tests passed")
```

**Invariant（迴圈不變式）**。`find_pair` 與 `count_pairs` 在處理第 j 個元素之前，表裡恰好裝著 `nums[0..j−1]`。所以「查表」等於「問前面有沒有」，每一對 (i, j) 只會在處理較大的那個索引 j 時被看到一次。這解釋了兩件事：為什麼不會把元素和自己配對（自己還沒放進去），以及為什麼 `count_pairs` 不會重複計數（每對只在 j 被數一次）。如果把「放」寫在「查」之前，`[3]` 配 target = 6 會錯誤地回傳 (0, 0)，`[1, 1, 1]` 的計數會多出三組自己配自己的情況。

**每一行為什麼這樣寫**：

- `seen[x] = j` 會覆蓋同一個值較早的索引。對「回傳任一組」沒有影響，因為只要有一個 i 就夠了；若題目要求回傳最小的 i，改成 `seen.setdefault(x, j)`。
- `count_pairs` 用 `Counter` 而不是 `set`，因為重複值會貢獻多組配對：前面有三個 5、現在來了一個 1，就是三組。`Counter` 對不存在的 key 回傳 0，不會丟 `KeyError`，也**不會**把 key 新增進去（這點和 `defaultdict` 不同，見 4.6 節）。
- `group_by` 的 `defaultdict(list)` 讓「第一次看到某個 key」與「之後看到」寫成同一行。Python 3.7 起 `dict` 保留插入順序，所以群組的順序就是每個 key 第一次出現的順序，測試時結果穩定。
- 三個模板都是 O(n) 次表操作；若 key 的計算本身要 O(L)（例如字串），總成本是 O(n · L)。在說複雜度時，**要把算 key 的成本算進去**，這是面試中最常被追問的一點。

**第四個模板：把陣列當成 hash table**。當 key 是 `1..n` 的整數，而且題目不允許 O(n) 額外空間時，可以讓「值 v」對應到「索引 v − 1」，用交換或正負號在原陣列上標記「v 出現過」。這是難題 1（41）的核心，也是 448、442、645 這類題目的共同做法。它的限制很明確：值域必須和陣列長度相當，而且必須允許修改輸入。

## 4.4 Key 的設計：讓等價的東西撞在一起

分組與計數類題目的成敗，幾乎完全取決於 key。好的 key 要同時滿足兩個方向：**等價的物件 key 一定相同**（否則同一組被拆開），**不等價的物件 key 一定不同**（否則不同組被合併）。下表是面試中最常見的等價關係與對應的 key：

| 等價關係 | Key | 計算成本 | 例題 |
|---|---|---|---|
| 互為 anagram（字母相同、順序不同） | `"".join(sorted(s))` 或 26 格計數的 `tuple` | O(L log L) 或 O(L + 26) | 核心題 2（49） |
| 平移後相同（`abc` ~ `bcd`） | 相鄰字母差值 mod 26 的 `tuple` | O(L) | 249 Group Shifted Strings |
| 用到的字母集合相同 | `frozenset(s)` 或 26 位元的 bitmask | O(L) | 2506 Count Pairs Of Similar Strings |
| 結構相同（`egg` ~ `add`、`abba` ~ `dog cat cat dog`） | 每個元素「第一次出現的序號」組成的 `tuple` | O(L) | 205 Isomorphic Strings、290 Word Pattern |
| 兩點決定的方向相同 | 約分並統一正負號的 `(dx, dy)` | O(log V)（gcd） | 難題 3（149） |
| 同一條對角線 | `r − c`（主對角線）或 `r + c`（反對角線） | O(1) | 51 N-Queens（第 19 章難題 1） |
| 前綴和相同（子陣列和為 0） | 前綴和本身 | O(1) | 560、525（第 7 章） |

```python
from math import gcd


def anagram_key(s: str) -> tuple[int, ...]:
    counts = [0] * 26
    for ch in s:
        counts[ord(ch) - ord("a")] += 1
    return tuple(counts)                      # list 不可雜湊，要轉成 tuple


def shift_key(s: str) -> tuple[int, ...]:
    return tuple((ord(b) - ord(a)) % 26 for a, b in zip(s, s[1:]))


def pattern_key(seq) -> tuple[int, ...]:
    first: dict = {}
    return tuple(first.setdefault(x, len(first)) for x in seq)


def direction_key(dx: int, dy: int) -> tuple[int, int]:
    g = gcd(dx, dy)                           # gcd 永遠非負；(0, 0) 不是合法方向
    dx, dy = dx // g, dy // g
    if dx < 0 or (dx == 0 and dy < 0):        # 統一正負號：dx > 0，或垂直線時 dy > 0
        dx, dy = -dx, -dy
    return dx, dy


assert anagram_key("eat") == anagram_key("tea") != anagram_key("tan")
assert shift_key("abc") == shift_key("xyz") == (1, 1)
assert shift_key("az") == shift_key("ba")             # 跨過 z 也相同：差值都是 25
assert shift_key("a") == shift_key("z") == ()          # 單一字母全部同一組
assert pattern_key("egg") == pattern_key("add") == (0, 1, 1)
assert pattern_key("foo") != pattern_key("bar")
assert pattern_key("dog cat cat dog".split()) == pattern_key("abba")
assert direction_key(2, 4) == direction_key(-1, -2) == (1, 2)
assert direction_key(0, -5) == direction_key(0, 3) == (0, 1)   # 垂直
assert direction_key(-7, 0) == (1, 0)                          # 水平
assert direction_key(3, -6) == direction_key(-1, 2) == (1, -2)
print("all tests passed")
```

**三個設計原則**。第一，**key 必須不可變**：`list`、`dict`、`set` 不能當 key，要轉成 `tuple` 或 `frozenset`，因為可變物件的雜湊值會隨內容改變，放進表之後就再也找不到。第二，**避免浮點數當 key**：斜率 `1 / 3` 與 `2 / 6` 在浮點運算下通常相等，但 `0.1 + 0.2 != 0.3` 這類誤差會讓本應相同的 key 不同，垂直線還會除以零；用整數的約分形式最安全。第三，**正規化要處理所有符號情況**：`(1, 2)` 與 `(−1, −2)` 是同一個方向，必須統一，否則同一條線上的點會被拆成兩組；`gcd` 在 Python 中永遠回傳非負數，所以除完之後的符號跟原本一致，再單獨處理一次就好。

**為什麼 `pattern_key` 有效**。兩個序列「結構相同」的意思是存在一個一對一的對應，把一邊的元素換成另一邊。把每個元素換成「它是第幾個新出現的元素」之後，任何一對一的重新命名都不會改變這個序列，而結構不同的序列一定會在某個位置出現不同的序號。這讓 205 和 290 這類題目不需要兩個方向的 dict 互相檢查，一個 key 比較就完成。

## 4.5 Hash table 的真實成本

**平均 O(1) 的前提**。Hash table 的 O(1) 是期望值，前提是雜湊函式把 key 分散得夠均勻。對隨機或一般的輸入這個前提成立；但如果攻擊者知道雜湊函式，就能刻意構造大量碰撞的 key，讓每次操作退化成 O(n)，這稱為 hash flooding。Python 對 `str` 與 `bytes` 的雜湊加入了每次執行不同的隨機種子來降低這個風險，但 `int` 的雜湊大致就是數值本身。面試中若被問「最差情況」，正確的回答是：單次操作最差 O(n)，整體最差 O(n²)；需要最差保證時可以改用排序或平衡樹，以 O(log n) 換取確定的上界。

**算 key 的成本**。把長度 L 的字串當 key，計算雜湊與比較都要 O(L)（Python 的 `str` 會快取自己的雜湊值，但每次切片都會產生新字串，要重新計算）。`tuple` 的雜湊不快取，每次查詢都會重算。所以「n 個字串放進 set」是 O(n · L)，不是 O(n)；難題 2 與難題 4 的複雜度分析都要把這一項算進去。

**空間與常數**。`dict` 每個元素的記憶體成本比 `list` 高出數倍（要存雜湊值、key、value，並保留空位以維持低負載），n 到 10⁷ 量級時會成為問題。當 key 是範圍不大的整數時（例如小寫字母、`0..n`），直接用長度固定的 `list` 當計數陣列，速度與記憶體都比 `dict` 好，這就是「陣列也是一種 hash table」的意思。

**Hashing 與排序的取捨**。很多 hashing 題也能用排序解：Two Sum 可以排序後用 two pointers，Longest Consecutive Sequence 可以排序後掃描，Group Anagrams 可以把整個串列依 key 排序。排序版本通常是 O(n log n) 時間、O(1) 或 O(log n) 額外空間；hashing 版本是 O(n) 期望時間、O(n) 空間。面試官常用「如果不能用額外空間呢」來追問，這時就要能切換到排序版本，並說明它會失去原始索引（若需要索引，要排序 `(值, 索引)` 的配對，空間又回到 O(n)）。

## 4.6 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 先放再查 | Two Sum 回傳 `[i, i]`；計數多算了自己配自己 | 固定寫成「查 → 更新答案 → 放」，表裡只有之前的元素 |
| 用 `set` 計數 | 重複值的配對數少算，例如 `[5, 5, 1]` 和為 6 只數到一組 | 需要「有幾個」就用 `Counter`；只需要「有沒有」才用 `set` |
| 用 `defaultdict` 查詢 | `if d[k] > 0` 會把 k 新增進表，之後 `len(d)` 或「表中有幾種值」算錯 | 查詢用 `k in d` 或 `d.get(k, 0)`；`Counter` 查詢不新增 key |
| 用 `list` 當 key | `TypeError: unhashable type: 'list'` | 轉成 `tuple`；集合轉成 `frozenset` |
| 用浮點數斜率當 key | 同一條線的點被拆開；垂直線除以零 | 用 gcd 約分後的整數 `(dx, dy)`，並統一正負號 |
| 正規化漏掉符號 | `(1, −2)` 與 `(−1, 2)` 被視為不同方向 | 規定 dx > 0，dx = 0 時 dy > 0，寫測試涵蓋四個象限 |
| 複雜度忘了 key 的成本 | 宣稱字串分組是 O(n)，被追問時答不出 | 寫成 O(n · L) 或 O(n · L log L)，說明 L 是什麼 |
| 遍歷 `nums` 而不是 `set` | 128 題遇到大量重複的起點時退化成 O(n²) | 去重之後再遍歷，或確保每個起點只展開一次 |
| 遍歷 dict 時同時修改 | `RuntimeError: dictionary changed size during iteration` | 先 `list(d.items())` 複製，或把要刪除的 key 收集起來最後再刪 |
| `Counter` 減法吃掉負數 | `c1 - c2` 會丟掉 ≤ 0 的項，比較兩個計數表時漏掉差異 | 需要保留負數時用 `c1.subtract(c2)`，或直接用 `c1 == c2` 比較 |

## 核心題 1｜1. Two Sum｜Easy

### 題目

給一個整數陣列 `nums` 和一個整數 `target`，找出兩個**不同位置**的元素 `nums[i]`、`nums[j]`（i ≠ j），使它們的和等於 `target`，回傳這兩個索引（順序不拘）。題目保證恰好有一組解，同一個元素不能使用兩次。限制：`2 <= len(nums) <= 10⁴`，元素與 `target` 都在 `-10⁹` 到 `10⁹` 之間。進階要求：做到比 O(n²) 更快。

- 範例 1：`nums = [2, 7, 11, 15]`、`target = 9`，回傳 `[0, 1]`，因為 2 + 7 = 9。
- 範例 2：`nums = [3, 2, 4]`、`target = 6`，回傳 `[1, 2]`。注意不能回傳 `[0, 0]`：3 + 3 = 6，但那是同一個元素用了兩次。
- 範例 3（邊界，重複值）：`nums = [3, 3]`、`target = 6`，回傳 `[0, 1]`。兩個 3 在不同位置，可以配對。
- 範例 4（邊界，負數與零）：`nums = [-3, 4, 3, 90]`、`target = 0`，回傳 `[0, 2]`。

### 思路

暴力解是兩層迴圈檢查每一對 (i, j)，O(n²) 時間、O(1) 空間；n = 10⁴ 時約 5 × 10⁷ 次比較，在 Python 中已經偏慢。第二種做法是排序後用相向的 two pointers（第 5 章核心題 1）：O(n log n)，但排序會打亂索引，必須排序 `(值, 原索引)` 的配對，空間又變回 O(n)。所以排序版本在這題沒有明顯優勢。

瓶頸在於內層迴圈。固定 j 之後，內層在找「有沒有 i 使 `nums[i] == target − nums[j]`」，這是一個查詢「某個確切的值是否出現過」，不需要逐一比較。用一個 `dict` 記錄「值 → 索引」，查詢就變成 O(1)，整體 O(n)。

細節在於**查詢與插入的順序**。我們從左往右走，對每個 j 先查 `target − nums[j]` 在不在表裡，查完才把 `nums[j]` 放進去。這維持了 4.3 節的 invariant：處理 j 時，表裡恰好是 `nums[0..j−1]`。因此範例 2 中第一個 3 查詢 3 時，表還是空的，不會和自己配對；範例 3 中第二個 3 查詢時，第一個 3 已經在表裡，於是正確配對。這個順序也意味著我們只需要走一遍，不必先建完整張表再走第二遍。

```text
nums = [3, 2, 4]，target = 6
步驟  j  nums[j]  need = 6 - nums[j]  seen（查詢前）     need 在表中？  動作
 1    0     3            3            {}                  否          seen[3] = 0
 2    1     2            4            {3: 0}              否          seen[2] = 1
 3    2     4            2            {3: 0, 2: 1}        是 → 1      回傳 [1, 2]

nums = [3, 3]，target = 6
 1    0     3            3            {}                  否          seen[3] = 0
 2    1     3            3            {3: 0}              是 → 0      回傳 [0, 1]
```

第一個例子的第 1 步，3 需要的也是 3，但此時表是空的，所以不會誤配自己；第 3 步 4 需要 2，表中記著 2 在索引 1，答案就出來了。第二個例子說明「先查再放」同時處理了重複值：第二個 3 查到的是第一個 3 的索引 0，而不是自己。

### 解法

```python
import random
from itertools import combinations


def two_sum(nums: list[int], target: int) -> list[int]:
    seen: dict[int, int] = {}                  # 值 → 索引，只包含目前位置之前的元素
    for j, x in enumerate(nums):
        i = seen.get(target - x)
        if i is not None:
            return [i, j]
        seen[x] = j
    return []                                  # 題目保證有解，這行只是防禦


def brute(nums, target):
    for i, j in combinations(range(len(nums)), 2):
        if nums[i] + nums[j] == target:
            return True
    return False


assert two_sum([2, 7, 11, 15], 9) == [0, 1]
assert two_sum([3, 2, 4], 6) == [1, 2]
assert two_sum([3, 3], 6) == [0, 1]
assert two_sum([-3, 4, 3, 90], 0) == [0, 2]
assert two_sum([10**9, -10**9], 0) == [0, 1]
assert two_sum([1, 2], 4) == []                # 無解時回傳空串列
for _ in range(500):
    arr = [random.randint(-10, 10) for _ in range(random.randint(2, 10))]
    t = random.randint(-20, 20)
    res = two_sum(arr, t)
    if res:
        i, j = res
        assert i < j and arr[i] + arr[j] == t
    else:
        assert not brute(arr, t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每個元素做一次查詢與一次插入，都是平均 O(1)。空間 O(n)：最差情況（答案在最後一對）表中會放 n − 1 個元素。邊界情況：重複值靠「先查再放」正確處理；`target − x` 可能是負數或超過 10⁹，Python 沒有溢位問題，在 Java／C++ 中 `target − x` 的範圍是 ±2 × 10⁹，超過 32 位元，要用 `long`；`seen.get` 回傳 `None` 與索引 0 要分清楚，所以寫 `is not None` 而不是 `if i:`，否則答案的第一個索引是 0 時會被當成找不到。

### Follow-up

> [!question]- F1. 如果要回傳「有幾組」i < j 滿足條件，而不是任一組呢？
> 把 `dict` 換成 `Counter`，對每個 x 先把 `seen[target − x]` 加到答案，再 `seen[x] += 1`，就是 4.3 節的 `count_pairs`，O(n) 時間、O(n) 空間。「先查再放」保證每一對只在較大的索引被數一次，也不會把自己算進去。例如 `[1, 1, 1]`、target = 2 的答案是 3，等於 C(3, 2)。若改成要列出所有索引對，輸出本身可能有 Θ(n²) 組（全部元素相同時），這時任何演算法都至少 O(n²)，要先和面試官確認輸出規模。

> [!question]- F2. 如果只要回傳所有「不重複的值配對」呢？例如 [1, 1, 2, 2, 3] 和為 4 只算 (1, 3) 和 (2, 2)。
> 用 `Counter` 統計每個值的次數，然後走過每個不同的值 a：令 b = target − a，若 a < b 且 b 在表中，輸出 (a, b)；若 a == b 且 `count[a] >= 2`，輸出 (a, a)。只檢查 a ≤ b 能避免同一對被輸出兩次。時間 O(n)，空間 O(n)。若改用排序加 two pointers，在每次找到配對後跳過所有重複值，可以做到 O(n log n) 時間、O(1) 額外空間，這是第 5 章 3Sum 去重的同一招。

> [!question]- F3. 如果輸入已經排序，能不能不用額外空間？
> 可以，這就是 167. Two Sum II（第 5 章核心題 1）：左指標從頭、右指標從尾，和太小就左指標右移、太大就右指標左移，O(n) 時間、O(1) 空間。正確性來自排序：和太小時，左指標指的元素和任何剩下的元素配對都不夠大，可以安全丟掉。這也是面試官常問的取捨題：未排序且要原索引時用 hash；已排序或不需要索引時用 two pointers 省空間。

> [!question]- F4. 如果要設計一個資料結構，支援 add(x) 加入一個數、find(t) 問是否存在兩個數和為 t（170. Two Sum III）呢？
> 有兩種取捨。一是 add 為 O(1)：用 `Counter` 存每個值的次數，find 時走過所有不同的值 a，檢查 t − a 是否存在（a == t − a 時要求次數 ≥ 2），find 為 O(D)，D 是不同值的個數。二是 find 為 O(1)：每次 add(x) 時把 x 和所有已存在的值的和都放進一個 `set`，add 為 O(D)，空間 O(D²)。要選哪一個取決於操作比例：add 多、find 少用第一種；find 遠多於 add 用第二種。面試時先問操作比例再決定，這正是面試官想聽到的。
> ```python
> from collections import Counter
>
> class TwoSum:
>     def __init__(self):
>         self.count = Counter()
>
>     def add(self, x: int) -> None:
>         self.count[x] += 1
>
>     def find(self, t: int) -> bool:
>         for a, c in self.count.items():
>             b = t - a
>             if b in self.count and (b != a or c >= 2):
>                 return True
>         return False
> ```

> [!question]- F5. 如果要找「和最接近 target」的一組，而不是剛好等於呢？
> Hash table 只能回答「某個確切的值在不在」，不能回答「最接近的值是誰」，所以這裡要換工具。排序後用相向 two pointers，每一步記錄 `|sum − target|` 的最小值，和小於 target 就移左指標、大於就移右指標，O(n log n)。若資料是一個一個進來的，可以維護一個排序結構，對每個新元素 x 用 binary search 找最接近 `target − x` 的前一個與後一個值，每次 O(log n)（Python 可用 `bisect.insort`，但插入是 O(n)，嚴格的 O(log n) 要用平衡樹）。

## 核心題 2｜49. Group Anagrams｜Medium

### 題目

給一個字串陣列 `strs`，把互為 anagram（重新排列字母後相同，也就是每個字母出現的次數完全一樣）的字串分在同一組，回傳所有組；組與組之間、組內的順序都不拘。限制：`1 <= len(strs) <= 10⁴`，`0 <= len(strs[i]) <= 100`，字串只含小寫英文字母。

- 範例 1：`strs = ["eat", "tea", "tan", "ate", "nat", "bat"]`，回傳 `[["eat", "tea", "ate"], ["tan", "nat"], ["bat"]]`。
- 範例 2（邊界，空字串）：`strs = [""]`，回傳 `[[""]]`。空字串自成一組。
- 範例 3（邊界）：`strs = ["a"]`，回傳 `[["a"]]`。
- 範例 4（重複字串）：`strs = ["ab", "ba", "ab"]`，回傳 `[["ab", "ba", "ab"]]`，重複的字串都要保留。

### 思路

暴力解是對每個字串，逐一和既有的每一組比較是不是 anagram（比較兩個字串的字母計數，O(L)），最差有 n 組，總共 O(n² · L)，n = 10⁴ 時約 10¹⁰，太慢。瓶頸在「和每一組比較」：我們真正想問的是「這個字串屬於哪一組」，如果每一組都有一個名字，而且字串能直接算出自己所屬組的名字，就能 O(1) 查到。

這就是 4.4 節的 canonical key。我們需要一個函式 f，使得 s 和 t 互為 anagram ⇔ f(s) == f(t)。有兩個自然的選擇。第一，把字母排序：`f(s) = "".join(sorted(s))`，anagram 排序後一定相同，排序後相同也一定是 anagram，成本 O(L log L)。第二，字母計數：26 格的計數表，轉成 `tuple` 才能當 key，成本 O(L + 26)。兩者都正確，第二種在 L 大時漸進更快；但 L ≤ 100 時，`sorted` 是 C 實作，實際上常常更快。

有了 key 之後，整題就是 4.3 節的 `group_by`：`groups[key(s)].append(s)`，最後回傳所有 value。Invariant 很簡單：處理完前 i 個字串後，`groups` 中每個 key 對應的串列，恰好是前 i 個字串裡所有 key 等於它的字串。

```text
strs = ["eat", "tea", "tan", "ate", "nat", "bat"]

字串    排序 key   計數 key（只列非零：字母×次數）   放入後的 groups
eat     aet        a1 e1 t1                         {aet: [eat]}
tea     aet        a1 e1 t1                         {aet: [eat, tea]}
tan     ant        a1 n1 t1                         {aet: [eat, tea], ant: [tan]}
ate     aet        a1 e1 t1                         {aet: [eat, tea, ate], ant: [tan]}
nat     ant        a1 n1 t1                         {aet: [...], ant: [tan, nat]}
bat     abt        a1 b1 t1                         {aet: [...], ant: [...], abt: [bat]}

回傳 groups.values() = [[eat, tea, ate], [tan, nat], [bat]]
```

每個字串只需要算一次 key、查一次表，不必和其他字串比較。注意 "tan" 和 "bat" 都有 a 和 t，但一個多了 n、一個多了 b，key 不同，所以不會被合併；這正是 key 的第二個要求：不等價的東西 key 一定不同。

### 解法

```python
import random
from collections import defaultdict


def group_anagrams(strs: list[str]) -> list[list[str]]:
    groups: defaultdict[str, list[str]] = defaultdict(list)
    for s in strs:
        groups["".join(sorted(s))].append(s)     # O(L log L) 的排序 key
    return list(groups.values())


def group_anagrams_count(strs: list[str]) -> list[list[str]]:
    groups: defaultdict[tuple[int, ...], list[str]] = defaultdict(list)
    for s in strs:
        counts = [0] * 26
        for ch in s:
            counts[ord(ch) - ord("a")] += 1
        groups[tuple(counts)].append(s)          # O(L + 26) 的計數 key
    return list(groups.values())


def normalize(groups):
    return sorted(sorted(g) for g in groups)


def brute(strs):
    out = []
    for s in strs:
        for g in out:
            if sorted(g[0]) == sorted(s):
                g.append(s)
                break
        else:
            out.append([s])
    return out


ex = ["eat", "tea", "tan", "ate", "nat", "bat"]
assert normalize(group_anagrams(ex)) == [["ate", "eat", "tea"], ["bat"], ["nat", "tan"]]
assert group_anagrams([""]) == [[""]]
assert group_anagrams(["a"]) == [["a"]]
assert group_anagrams(["ab", "ba", "ab"]) == [["ab", "ba", "ab"]]
assert normalize(group_anagrams(["", "", "b"])) == [["", ""], ["b"]]
for _ in range(300):
    words = ["".join(random.choice("abc") for _ in range(random.randint(0, 4)))
             for _ in range(random.randint(1, 12))]
    expect = normalize(brute(words))
    assert normalize(group_anagrams(words)) == expect == normalize(group_anagrams_count(words))
print("all tests passed")
```

### 複雜度與邊界

令 n 為字串數、L 為最長字串長度。排序 key 版本時間 O(n · L log L)；計數 key 版本時間 O(n · (L + 26))，其中 26 是建立與雜湊 tuple 的成本。兩者空間都是 O(n · L)：每個字串都存進某個群組，再加上 key 本身。邊界情況：空字串的排序 key 是 `""`、計數 key 是 26 個 0，都能正常當 key，所有空字串會分在同一組；重複的字串會被放進同一組且保留重複；只有一個字串時回傳一組。若要求輸出順序固定（例如每組內字典序、組間依第一個字串），最後再排序，這會多出 O(n · L log n)。

### Follow-up

> [!question]- F1. 如果字串可以包含任意 Unicode 字元，而不只是小寫字母呢？
> 26 格計數表不再適用，因為字元集合可能有十幾萬種。排序 key 仍然正確，O(L log L)。若想維持 O(L)，可以用 `Counter(s)` 計數，再把它轉成可雜湊的形式：`frozenset(Counter(s).items())`，或 `tuple(sorted(Counter(s).items()))`（排序的是 D 個不同字元，D ≤ L）。前者 O(L) 期望時間；後者 O(L + D log D)。要注意 Unicode 的正規化問題：「é」可能是一個字元，也可能是「e」加上組合重音符，若題目要求視為相同，要先用 `unicodedata.normalize` 處理。

> [!question]- F2. 能不能用「每個字母對應一個質數，key 是乘積」來避免排序？
> 正確性上可以：由算術基本定理，質數乘積相同 ⇔ 每個質數的次數相同 ⇔ 互為 anagram。但乘積會非常大：26 個字母對應前 26 個質數，最大是 101，長度 100 的字串乘積可達 101¹⁰⁰，約 665 位元。Python 的大整數能處理，但每次乘法的成本隨位數增加，總成本反而比計數 key 高；在 Java／C++ 中用 64 位元整數會溢位，溢位後不同的字串可能得到相同的乘積，產生錯誤的合併。面試時提出這個想法可以加分，但要能主動指出溢位問題，並說明計數 key 才是穩健的選擇。

> [!question]- F3. 如果只需要回答「有多少組」或「最大的一組有多大」呢？
> 不需要存字串本身，把 `defaultdict(list)` 換成 `Counter`：`sizes[key(s)] += 1`。有多少組是 `len(sizes)`，最大組是 `max(sizes.values())`。時間不變，仍是 O(n · L log L) 或 O(n · L)，但空間從 O(n · L) 降到 O(G · L)，G 是組數（key 本身仍然要存）。若連 key 都想省，可以存 key 的雜湊值，但那會引入極小機率的碰撞，要說明這個風險。

> [!question]- F4. 如果改成「平移後相同」的字串分在一組（249. Group Shifted Strings），例如 abc、bcd、xyz 同組，az、ba 同組？
> 只要換 key：把字串轉成相鄰字母的差值序列 `tuple((ord(b) − ord(a)) % 26 for a, b in zip(s, s[1:]))`。平移不會改變相鄰字母的差，而 mod 26 處理了跨過 z 繞回 a 的情況，例如 az 的差是 25，ba 的差是 (0 − 1) mod 26 = 25。長度不同的字串差值序列長度不同，自然分開；所有單一字母的字串差值序列都是空 tuple，分在同一組。時間 O(n · L)。這題說明了本章的核心：分組題的工作量幾乎全在設計 key。

> [!question]- F5. 如果字串是一個接一個串流進來，每來一個就要回答「目前和它同組的有幾個」呢？
> 維護 `Counter` 從 key 到目前的數量，每個字串算 key（O(L log L) 或 O(L)），先查詢再加一（或先加一再查，取決於「包含自己」與否）。每次操作與 n 無關。若同時要支援刪除，`Counter` 減一即可，數量歸零時刪掉 key 以免記憶體累積。若 key 的計算是瓶頸、而字母種類少，可以用計數 key 並在字元進出時增量更新，這正是第 6 章核心題 5（438. Find All Anagrams in a String）在滑動視窗中維護字母計數的做法。

## 核心題 3｜128. Longest Consecutive Sequence｜Medium

### 題目

給一個**未排序**的整數陣列 `nums`，回傳其中數值能組成的最長「連續整數序列」的長度。連續整數序列指 x、x + 1、x + 2、…、x + k − 1 這 k 個值都出現在陣列中（不要求在陣列中相鄰，也不要求順序）。要求 O(n) 時間。限制：`0 <= len(nums) <= 10⁵`，元素在 `-10⁹` 到 `10⁹` 之間。

- 範例 1：`nums = [100, 4, 200, 1, 3, 2]`，回傳 `4`，最長的連續序列是 1、2、3、4。
- 範例 2：`nums = [0, 3, 7, 2, 5, 8, 4, 6, 0, 1]`，回傳 `9`（0 到 8）。
- 範例 3（邊界，重複值）：`nums = [1, 2, 0, 1]`，回傳 `3`，重複的 1 只算一次。
- 範例 4（邊界）：`nums = []`，回傳 `0`；`nums = [5]`，回傳 `1`。

### 思路

最直接的暴力解是對每個 x，不斷檢查 x + 1、x + 2… 是否在陣列中，每次檢查用線性搜尋 O(n)，整體 O(n³)；把陣列換成 `set` 之後每次檢查 O(1)，但每個 x 都可能往上走很長一段，例如 `[1, 2, …, n]` 時從 1 走 n 步、從 2 走 n − 1 步…，仍然是 O(n²)。另一個做法是排序後線性掃描，遇到差 1 就延長、相等就跳過、其他就重新開始，O(n log n)，簡單可靠，但不符合 O(n) 的要求。

O(n²) 的浪費在哪裡？從 2 開始往上走的那一段，其實是從 1 開始那一段的後半，完全重複計算了。關鍵觀察：**每一段連續序列只需要從它的起點走一次**，而「x 是起點」有一個 O(1) 的判斷：x − 1 不在集合中。所以演算法是：把所有數放進 `set`；對每個 x，只有當 x − 1 不在集合中時，才從 x 往上走，計算這一段的長度。

為什麼這是 O(n)？這是一個攤銷（amortized）論證。往上走的總步數，等於所有段的長度總和，而每個不同的數值只屬於一段，所以總步數 ≤ 不同值的個數 ≤ n。再加上每個 x 做一次「x − 1 在不在」的檢查，總共 O(n)。這裡有一個容易忽略的細節：要遍歷 `set` 而不是原陣列。若原陣列中起點 1 重複出現了 n / 2 次，遍歷原陣列時每個 1 都會判斷自己是起點，各自往上走一整段，又退化回 O(n²)。

```text
nums = [100, 4, 200, 1, 3, 2]，num_set = {1, 2, 3, 4, 100, 200}

x     x-1 在集合中？  是起點？  往上走                     段長
1     0 否            是        1 → 2 → 3 → 4 → (5 不在)    4
2     1 是            否        跳過
3     2 是            否        跳過
4     3 是            否        跳過
100   99 否           是        100 → (101 不在)            1
200   199 否          是        200 → (201 不在)            1

數軸視角：
  1  2  3  4 ……… 100 ……… 200
  ●──●──●──●      ●        ●
  ↑ 起點           ↑ 起點    ↑ 起點
往上走的總步數 = 4 + 1 + 1 = 6 = 不同值的個數
```

每一段只有起點會觸發往上走，其他元素只花一次 O(1) 的檢查就被跳過。數軸視角清楚地說明了攤銷：所有「往上走」加起來剛好把每個點踩過一次。

### 解法

```python
import random


def longest_consecutive(nums: list[int]) -> int:
    num_set = set(nums)
    best = 0
    for x in num_set:                       # 遍歷 set，重複的起點只處理一次
        if x - 1 in num_set:                # 不是起點：這一段會由它的起點處理
            continue
        y = x
        while y + 1 in num_set:
            y += 1
        best = max(best, y - x + 1)
    return best


def longest_consecutive_sort(nums: list[int]) -> int:
    """O(n log n) 的排序版本，作為對照。"""
    if not nums:
        return 0
    arr = sorted(set(nums))
    best = cur = 1
    for a, b in zip(arr, arr[1:]):
        cur = cur + 1 if b == a + 1 else 1
        best = max(best, cur)
    return best


assert longest_consecutive([100, 4, 200, 1, 3, 2]) == 4
assert longest_consecutive([0, 3, 7, 2, 5, 8, 4, 6, 0, 1]) == 9
assert longest_consecutive([1, 2, 0, 1]) == 3
assert longest_consecutive([]) == 0
assert longest_consecutive([5]) == 1
assert longest_consecutive([-1, -2, -3, 10**9, -10**9]) == 3
assert longest_consecutive([1] * 50000 + list(range(2, 50001))) == 50000   # 大量重複起點仍然很快
for _ in range(500):
    arr = [random.randint(-15, 15) for _ in range(random.randint(0, 15))]
    assert longest_consecutive(arr) == longest_consecutive_sort(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：建立 set O(n)；每個不同的值做一次 `x − 1` 檢查；`while` 迴圈的總執行次數等於所有段的長度和，不超過不同值的個數。空間 O(n)，用於 set。邊界情況：空陣列時迴圈不執行，回傳 0；全部重複（`[7, 7, 7]`）時 set 只有一個元素，答案 1；負數與跨過 0 的序列（`[−1, 0, 1]`）不需要特別處理，因為只用到 ±1；值域 ±10⁹ 不影響，因為我們從不按值域開陣列。測試中的 `[1] * 50000 + …` 就是在驗證「遍歷 set 而不是 nums」：若遍歷原陣列，這個輸入會執行約 25 億步。

### Follow-up

> [!question]- F1. 如果要回傳最長序列本身（或它的起點與終點）呢？
> 在更新 `best` 時同時記錄 `(x, y)`，最後回傳 `list(range(x, y + 1))`，時間與空間都不變，O(n)。若有多段一樣長，題目通常會要求回傳起點最小的一段，那就在 `y − x + 1 == best` 時比較起點；因為遍歷 set 的順序不固定，不能依賴「先遇到的」作為平手的規則，這是面試中容易漏掉的細節。

> [!question]- F2. 如果數字是串流進來的，每加入一個數就要回報目前的最長長度呢？
> 用「區段端點」的 dict：`length[v]` 記錄以 v 為端點的那一段的長度（只保證端點上的值正確）。插入一個新的 x（已存在就忽略）時，左邊那段長度 `a = length.get(x − 1, 0)`、右邊那段 `b = length.get(x + 1, 0)`，合併後長度 `a + b + 1`，只需要更新新段的兩個端點 `x − a` 與 `x + b`，以及 x 本身（標記已存在）。每次插入 O(1)，再維護一個全域最大值。另一種做法是 Union-Find（第 17 章），把 x 和 x ± 1 合併，維護每個集合的大小，每次插入接近 O(1)。
> ```python
> class StreamConsecutive:
>     def __init__(self):
>         self.length = {}
>         self.best = 0
>
>     def add(self, x: int) -> int:
>         if x not in self.length:
>             a = self.length.get(x - 1, 0)
>             b = self.length.get(x + 1, 0)
>             total = a + b + 1
>             self.length[x] = total
>             self.length[x - a] = total     # 新段的左端點
>             self.length[x + b] = total     # 新段的右端點
>             self.best = max(self.best, total)
>         return self.best
> ```

> [!question]- F3. 如果還要支援刪除一個數呢？
> 刪除會把一段切成兩段，端點 dict 與 Union-Find 都無法有效處理（Union-Find 不支援拆分）。可以把所有區段存在一個依起點排序的結構中（例如平衡樹，或 Python 的 `sortedcontainers.SortedList`），刪除 x 時找到包含 x 的區段 [l, r]，換成 [l, x − 1] 與 [x + 1, r]；另外用一個可刪除的多重集合記錄所有區段長度，以便查詢最大值。每次操作 O(log n)。這和第 9 章難題 4（352. Data Stream as Disjoint Intervals）的區段維護是同一個結構。

> [!question]- F4. 如果要求的是「在陣列中依序出現」的最長序列，每個元素比前一個大 1（例如 1218 題 difference = 1 的版本）呢？
> 順序變得重要，set 的做法不再適用，因為它忽略了位置。改用 DP 搭配 hash：從左到右走，`dp[x] = dp.get(x − 1, 0) + 1`，表示「以值 x 結尾、在目前位置之前出現的最長序列」。每個元素 O(1)，總共 O(n) 時間、O(n) 空間。這是本題常見的混淆點：題目有沒有說「子序列」或「依序」，決定了要用 set（不看順序）還是 DP（看順序）。

> [!question]- F5. 如果記憶體只夠放輸入本身，不能再開一個 O(n) 的 set 呢？
> 在原地排序（Python 的 `list.sort()` 是 Timsort，最差需要 O(n) 的暫存空間；若要嚴格 O(1) 額外空間可以用 heapsort），然後線性掃描：相等就跳過、差 1 就延長、其他就重新計數。時間 O(n log n)，額外空間 O(1)（不計排序的暫存）。這是典型的時間換空間：hashing 用 O(n) 空間換到 O(n) 時間，排序用 O(log n) 的時間因子換回空間。

## 核心題 4｜454. 4Sum II｜Medium

### 題目

給四個長度都是 n 的整數陣列 `A`、`B`、`C`、`D`，計算有多少個索引組合 `(i, j, k, l)` 滿足 `A[i] + B[j] + C[k] + D[l] == 0`。不同的索引組合即使值相同也分開計算。限制：`1 <= n <= 200`，元素在 `-2²⁸` 到 `2²⁸` 之間（所以四數之和不會超過 32 位元整數的範圍）。

- 範例 1：`A = [1, 2]`、`B = [-2, -1]`、`C = [-1, 2]`、`D = [0, 2]`，回傳 `2`。兩組分別是 (0, 0, 0, 1)：1 + (−2) + (−1) + 2 = 0，以及 (1, 1, 0, 0)：2 + (−1) + (−1) + 0 = 0。
- 範例 2（邊界）：`A = B = C = D = [0]`，回傳 `1`。
- 範例 3（邊界，重複值）：`A = B = C = D = [0, 0]`，回傳 `16`，每個陣列兩個 0 都能選，2⁴ = 16。
- 範例 4：`A = [1]`、`B = [1]`、`C = [1]`、`D = [1]`，回傳 `0`。

### 思路

暴力解是四層迴圈，O(n⁴)，n = 200 時是 1.6 × 10⁹，太慢。第一步改進是把最內層換成查表：先用 `Counter` 統計 D 中每個值出現的次數，對每個 (i, j, k) 查 `count_D[−(A[i] + B[j] + C[k])]`，O(n³) = 8 × 10⁶，在 Python 中已經可以接受，但還能更好。

觀察式子 `A[i] + B[j] + C[k] + D[l] = 0` 可以寫成 `A[i] + B[j] = −(C[k] + D[l])`。左邊只和 (i, j) 有關，右邊只和 (k, l) 有關，兩邊**互相獨立**。所以把 n² 個 `A[i] + B[j]` 先算好、存成「和 → 出現次數」的 `Counter`，再枚舉 n² 個 `C[k] + D[l]`，每個查一次 `ab[−(c + d)]` 累加起來。這就是 meet in the middle（折半）：把一個 n⁴ 的搜尋拆成兩個 n² 的半邊，再用 hash table 把兩半接起來，總時間 O(n²)。

為什麼 value 要存次數而不是只存「有沒有」？因為題目數的是索引組合。若 `A[i] + B[j] = 3` 有 5 組 (i, j)，而某一組 (k, l) 的和是 −3，它就和那 5 組各湊成一個答案，要一次加 5。這也說明了為什麼不需要「先查再放」的順序：兩半來自不同的陣列，不存在自己和自己配對的問題，所以可以先完整建好左半的表再查。

```text
A = [1, 2]，B = [-2, -1]，C = [-1, 2]，D = [0, 2]

第一步：統計 A[i] + B[j]
          B=-2  B=-1
  A=1      -1     0
  A=2       0     1
ab = {-1: 1, 0: 2, 1: 1}

第二步：枚舉 C[k] + D[l]，查 ab[-(c + d)]
          D=0   D=2
  C=-1     -1     1
  C=2       2     4

c + d   需要 ab[-(c+d)]    次數
 -1     ab[1]               1     ← (i,j)=(1,1) 配 (k,l)=(0,0)
  1     ab[-1]              1     ← (i,j)=(0,0) 配 (k,l)=(0,1)
  2     ab[-2]              0
  4     ab[-4]              0
總計 = 2
```

第一張表有 4 格，但只有 3 種和，其中 0 出現了兩次（1 + (−1) 與 2 + (−2)），所以 `ab[0] = 2`。如果後半有某個 `c + d = 0`，就會一次貢獻 2。這個例子中後半沒有 0，最後兩組答案分別來自 ab[1] 與 ab[−1]。

### 解法

```python
import random
from collections import Counter
from itertools import product


def four_sum_count(A: list[int], B: list[int], C: list[int], D: list[int]) -> int:
    ab = Counter(a + b for a in A for b in B)            # n² 個和 → 次數
    return sum(ab[-(c + d)] for c in C for d in D)       # Counter 查不到回傳 0


def brute(A, B, C, D):
    return sum(1 for a, b, c, d in product(A, B, C, D) if a + b + c + d == 0)


assert four_sum_count([1, 2], [-2, -1], [-1, 2], [0, 2]) == 2
assert four_sum_count([0], [0], [0], [0]) == 1
assert four_sum_count([0, 0], [0, 0], [0, 0], [0, 0]) == 16
assert four_sum_count([1], [1], [1], [1]) == 0
big = 2**28
assert four_sum_count([big], [big], [-big], [-big]) == 1
for _ in range(300):
    n = random.randint(1, 5)
    arrs = [[random.randint(-3, 3) for _ in range(n)] for _ in range(4)]
    assert four_sum_count(*arrs) == brute(*arrs)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n²)：建表 n² 次插入，查詢 n² 次。空間 O(n²)：最差情況下 n² 個和都不同，n = 200 時是 4 × 10⁴ 個 entry，完全沒問題。邊界情況：重複值靠次數正確處理（範例 3）；`Counter` 查詢不存在的 key 回傳 0 且不新增 key，所以 `ab[−(c + d)]` 不會讓表膨脹；在 Java／C++ 中，四個 2²⁸ 相加是 2³⁰，仍在 32 位元範圍內，題目的限制正是為此設計，但兩兩相加的中間值也要確認不溢位。應該先建哪一半？兩半大小都是 n²，沒有差別；若四個陣列長度不同，把較小的兩個陣列配成一組來建表，可以省空間。

### Follow-up

> [!question]- F1. 如果推廣到 k 個陣列（kSum II），每個長度 n 呢？
> 把 k 個陣列分成前 ⌈k/2⌉ 個與後 ⌊k/2⌋ 個。前半所有組合的和（共 n^⌈k/2⌉ 個）存進 `Counter`，後半所有組合的和逐一查詢，時間 O(n^⌈k/2⌉)，空間 O(n^⌈k/2⌉)。實作上可以用遞迴產生某一半的所有和，或用迭代：從 `sums = Counter({0: 1})` 開始，每加入一個陣列 arr，就建一個新的 `Counter`，對 `sums` 中每個 (s, cnt) 與 arr 中每個 x 做 `new[s + x] += cnt`，再令 `sums = new`。k = 4 時就是本題的 O(n²)；k = 6 時是 O(n³)。這比直接枚舉的 O(n^k) 好得多，是 meet in the middle 的標準複雜度。

> [!question]- F2. 如果要回傳所有的索引組合，而不只是個數呢？
> 把 `Counter` 換成 `defaultdict(list)`，存「和 → 所有 (i, j)」，查詢時把每個 (k, l) 和串列中所有 (i, j) 組合輸出。時間是 O(n² + 輸出數)，但輸出數最差是 n⁴（全部是 0 時），這時無論如何都要 O(n⁴)，面試時要先指出輸出規模本身就是下限。如果只要回傳任意一組，存第一個 (i, j) 就好，O(n²)。

> [!question]- F3. 如果 n 很大，n² 個和放不進記憶體呢？
> 一種做法是用排序取代 hash：把 A + B 的和與 C + D 的和各自排序，再用相向的 two pointers 數「和為 0」的配對，遇到相同值時把兩邊的連續相同區段長度相乘。時間 O(n² log n)，記憶體用緊湊的陣列（例如 `array('q')`）而不是 dict，可以省數倍空間。若連這也放不下，就把 A + B 的和 s 依 `s mod P` 分成 P 個分區、把 C + D 的和 t 依 `(−t) mod P` 分區，寫到磁碟。能配對的 s = −t 一定落在編號相同的分區，所以每次只把第 p 號的一對分區讀進記憶體，建 `Counter` 再查詢，總時間仍是 O(n²) 加上磁碟讀寫，這是外部雜湊 join（hash join）的想法。

> [!question]- F4. 如果只有一個陣列，要找所有不重複的四元組（18. 4Sum）呢？
> 這是另一個問題。單一陣列要求四個索引互不相同，而且要對「值」去重，hash 折半的做法很難同時處理「索引不重疊」與「值去重」。標準做法是排序後固定兩個數，剩下兩個用相向 two pointers 找，並在每一層跳過重複值，O(n³) 時間、O(1) 額外空間（第 5 章 3Sum 的延伸）。面試官常把 454 和 18 一起問，就是要看你是否理解：本題能折半，是因為四個陣列互相獨立、而且只要計數。

> [!question]- F5. 如果目標不是 0 而是任意 target，或改成「和 ≤ target 的組合數」呢？
> 等於 target 時只要把查詢改成 `ab[target − (c + d)]`，其他不變。改成「≤ target」就不能用 hash，因為要查的是一個範圍：把 A + B 的 n² 個和排序，對每個 c + d 用 `bisect_right(sorted_ab, target − (c + d))` 數有幾個，O(n² log n)；或把兩邊都排序後用 two pointers 一次掃完，排序之後 O(n²)。這再次說明 hash 只能回答「等於」，範圍查詢要靠排序。

## 核心題 5｜554. Brick Wall｜Medium

### 題目

一面磚牆有 n 列，每一列由若干塊高度相同、寬度不一的磚塊從左到右排成，每一列的總寬度都相同。輸入 `wall[i]` 是第 i 列各塊磚的寬度。你要從牆的頂端到底端畫一條垂直線，線穿過某塊磚的內部就算穿過那塊磚；剛好落在兩塊磚的接縫上則不算。線不能畫在牆的最左邊或最右邊。回傳最少會穿過幾塊磚。限制：`1 <= n <= 10⁴`，每列至少一塊磚，磚塊總數不超過 `2 × 10⁴`，每列總寬度不超過 `2³¹ − 1`。

- 範例 1：`wall = [[1, 2, 2, 1], [3, 1, 2], [1, 3, 2], [2, 4], [3, 1, 2], [1, 3, 1, 1]]`，回傳 `2`。在位置 4 畫線，有 4 列剛好在接縫上，只穿過 2 塊。
- 範例 2（邊界，沒有內部接縫）：`wall = [[1], [1], [1]]`，回傳 `3`。每列只有一塊磚，任何位置都會穿過全部 3 塊。
- 範例 3：`wall = [[3], [1, 2], [2, 1]]`，回傳 `2`。接縫位置 1 只出現在第二列、位置 2 只出現在第三列，最多只能避開 1 塊。
- 範例 4（邊界，寬度很大）：`wall = [[2**31 - 2, 1], [2**31 - 1]]`，回傳 `1`。

### 思路

最直接的暴力解是把每個可能的整數位置 x（1 到 W − 1）都試一次，計算穿過幾塊磚。但 W 可以到 2³¹ − 1，這個範圍無法枚舉。第一個觀察是：只有接縫的位置值得考慮。如果 x 不是任何一列的接縫，那麼它穿過全部 n 塊磚，是最差的選擇（除非沒有任何接縫可選）。所以候選位置只有「某一列的某個接縫」，總數不超過磚塊總數。

第二個觀察把問題反過來看：線在位置 x 穿過的磚塊數 = n − （在 x 有接縫的列數）。要最小化穿過數，就是要找**被最多列共享的接縫位置**。每一列的接縫位置就是它的前綴和（不含最後一塊，因為最後一個前綴和是牆的右邊緣，不能畫線）。於是演算法變成：對每一列計算前綴和，用 `Counter` 統計每個位置出現在幾列，答案是 `n − max(count.values())`；若沒有任何內部接縫，答案是 n。

這個轉換是 hashing 題常見的思路：把「幾何上的最佳位置」變成「哪個 key 出現最多次」。每列內的前綴和嚴格遞增（磚塊寬度至少 1），所以同一列不會對同一個位置計數兩次，`count[x]` 恰好是「在 x 有接縫的列數」。

```text
wall（寬度 6）：                         各列的接縫位置（前綴和，不含最後一個）
列0  |1|  2 |  2 |1|                       1, 3, 5
列1  |  3   |1|  2 |                       3, 4
列2  |1|   3    |  2 |                     1, 4
列3  | 2 |     4     |                     2
列4  |  3   |1|  2 |                       3, 4
列5  |1|   3    |1|1|                      1, 4, 5

位置 x:     1  2  3  4  5
count[x]:   3  1  3  4  2
穿過數 n-count:  3  5  3  2  4      → 最少 2（x = 4）

      0  1  2  3  4  5  6
列0   |--|-----|-----|--|            （位置 1、3、5 是接縫）
列1   |--------|--|-----|
列2   |--|--------|-----|
列3   |-----|-----------|
列4   |--------|--|-----|
列5   |--|--------|--|--|
                  ↑ x = 4：列 1、2、4、5 在接縫上，只穿過列 0、3
```

`count[4] = 4` 表示有 4 列在位置 4 有接縫，所以線畫在那裡只穿過 6 − 4 = 2 塊。注意每列最後一個前綴和都是 6（牆的右緣），我們刻意不計入；若計入，`count[6] = 6` 會讓答案錯誤地變成 0。

### 解法

```python
import random
from collections import Counter


def least_bricks(wall: list[list[int]]) -> int:
    edges: Counter[int] = Counter()
    for row in wall:
        pos = 0
        for width in row[:-1]:              # 最後一塊的右緣是牆的邊界，不能畫線
            pos += width
            edges[pos] += 1
    return len(wall) - max(edges.values(), default=0)


def brute(wall):
    total = sum(wall[0])
    best = len(wall)
    for x in range(1, total):
        crossed = 0
        for row in wall:
            pos = 0
            for w in row:
                if pos < x < pos + w:        # x 落在這塊磚的內部
                    crossed += 1
                    break
                pos += w
        best = min(best, crossed)
    return best


assert least_bricks([[1, 2, 2, 1], [3, 1, 2], [1, 3, 2], [2, 4], [3, 1, 2], [1, 3, 1, 1]]) == 2
assert least_bricks([[1], [1], [1]]) == 3
assert least_bricks([[3], [1, 2], [2, 1]]) == 2
assert least_bricks([[2**31 - 2, 1], [2**31 - 1]]) == 1
assert least_bricks([[1, 1], [1, 1]]) == 0           # 所有列在同一處有接縫
for _ in range(300):
    width = random.randint(1, 8)
    wall = []
    for _ in range(random.randint(1, 5)):
        row, left = [], width
        while left:
            w = random.randint(1, left)
            row.append(w)
            left -= w
        wall.append(row)
    assert least_bricks(wall) == brute(wall)
print("all tests passed")
```

### 複雜度與邊界

時間 O(B)，B 是磚塊總數：每塊磚（除了每列最後一塊）做一次加法與一次計數。空間 O(B)：最差情況下所有接縫位置都不同。注意複雜度與牆的寬度 W 無關，這正是不能枚舉位置、必須只看接縫的原因。邊界情況：所有列都只有一塊磚時 `edges` 為空，`max(…, default=0)` 讓答案為 n；所有列都在同一處有接縫時答案為 0；寬度接近 2³¹ − 1 時 Python 不會溢位，在 Java 中前綴和仍在 `int` 範圍內（因為每列總寬度不超過 2³¹ − 1），但若題目放寬寬度就要用 `long`。

### Follow-up

> [!question]- F1. 如果還要回傳線要畫在哪個位置呢？若有多個最佳位置，回傳最左邊的。
> 走過 `edges` 時記錄次數最大的 key；平手時取較小的位置。`max(edges, key=lambda x: (edges[x], -x))` 一行即可，O(B)。若沒有任何接縫，任何位置都一樣，回傳 1（最左邊的合法整數位置）。面試時主動說明「平手怎麼處理」與「沒有接縫怎麼辦」，是 verification 的加分項。

> [!question]- F2. 如果可以畫 k 條不同位置的垂直線，要最小化穿過的磚塊總數呢？
> 每條線穿過的磚塊數彼此獨立（線之間不互相影響），所以只要選出共享次數最多的 k 個接縫位置，總穿過數是 k · n − （這 k 個位置的次數總和）。用 `heapq.nlargest(k, edges.values())`，O(B log k)。若不同接縫位置的數量少於 k，剩下的線只能畫在非接縫處，每條穿過 n 塊（前提是牆夠寬，有足夠的合法位置）。

> [!question]- F3. 如果牆的某些位置是空的（有缺口，線穿過缺口不算穿過磚）呢？
> 這時每列不再是首尾相接的磚塊，而是若干個區間 [l, r)，線在 x 穿過的磚塊數 = 包含 x 於內部的區間數，也就是 l < x < r 的區間個數。這變成 sweep line（第 9 章）的問題：把每個區間轉成「l + 1 處加一、r 處減一」的事件（只看整數位置時，內部是 l + 1 到 r − 1），依位置排序後掃過，找覆蓋數最小的位置，O(B log B)。若座標範圍小，也可以直接用 difference array（第 7 章）O(B + W)。

> [!question]- F4. 如果牆有 10⁹ 列，分散在很多台機器上呢？
> 每台機器對自己負責的列計算本地的 `Counter`（接縫位置 → 列數），再把所有本地 Counter 依 key 合併相加，最後取最大值，答案是總列數減去它。這是標準的 map-reduce：map 階段輸出 (位置, 1)，reduce 階段依位置加總。為了減少網路傳輸，每台機器先在本地合併（combiner），只傳 (位置, 本地次數)。若不同位置的數量也非常大，可以依位置的雜湊分到不同的 reducer，每個 reducer 回報自己的最大值，再取全域最大。

## 難題 1｜41. First Missing Positive｜Hard

### 題目

給一個未排序的整數陣列 `nums`，回傳其中**沒有出現的最小正整數**。要求 O(n) 時間，而且只使用 O(1) 的額外空間（可以修改輸入陣列）。限制：`1 <= len(nums) <= 10⁵`，元素在 `-2³¹` 到 `2³¹ − 1` 之間。

- 範例 1：`nums = [1, 2, 0]`，回傳 `3`。1 和 2 都在，3 不在。
- 範例 2：`nums = [3, 4, -1, 1]`，回傳 `2`。
- 範例 3：`nums = [7, 8, 9, 11, 12]`，回傳 `1`。所有數都太大，1 就不在。
- 範例 4（邊界）：`nums = [1]`，回傳 `2`；`nums = [1, 1]`，回傳 `2`（重複值不算多一個）；`nums = [2, 1]`，回傳 `3`。

### 提示

> [!tip]- 提示 1
> 如果沒有空間限制，把所有數放進 `set`，再從 1 開始往上找第一個不在的，這是 O(n) 時間、O(n) 空間。先想想：答案最大可能是多少？

> [!tip]- 提示 2
> 長度 n 的陣列最多只能「填滿」1 到 n 這 n 個正整數，所以答案一定落在 `[1, n + 1]`。小於 1 或大於 n 的數對答案沒有影響。那麼，能不能拿陣列本身的 n 個位置，當作記錄「1 到 n 出現過沒有」的表？

> [!tip]- 提示 3
> 讓「值 v」住在「索引 v − 1」。從左到右，只要 `nums[i]` 是 1 到 n 之間的數 v，而且 `nums[v − 1]` 還不是 v，就把它交換過去，並繼續處理換回來的數。結束後，第一個 `nums[i] != i + 1` 的位置 i，答案就是 i + 1；全部都對就是 n + 1。

### 詳解

**為什麼直覺做法不行**。`set` 的做法是 O(n) 空間；排序後掃描是 O(n log n) 時間。兩者都違反了限制。這題的限制是刻意設計的：同時要求 O(n) 時間與 O(1) 空間，意味著不能排序（比較排序的下限是 O(n log n)），也不能開新的表，唯一能用的「表」就是輸入陣列本身。

**突破點一：答案的範圍很小**。長度 n 的陣列要讓答案是 n + 2 或更大，就必須同時包含 1 到 n + 1 這 n + 1 個不同的數，但陣列只有 n 個位置，不可能（鴿籠原理）。所以答案一定在 `[1, n + 1]`，我們只需要知道 1 到 n 每個數出現過沒有。這是一個 key 為 `1..n` 的 set，而 key 的範圍剛好等於陣列長度，可以用「索引 v − 1」表示「v 出現過」。

**突破點二：用交換把每個數放回自己的家（cyclic sort）**。對每個位置 i，只要 `nums[i]` 是某個 v ∈ [1, n] 且 `nums[v − 1] != v`，就把 `nums[i]` 和 `nums[v − 1]` 交換。交換後 v 到了它的家，而換回 i 的數可能也需要搬家，所以用 `while` 繼續處理同一個位置；當 `nums[i]` 不在範圍內、或它的家已經住著正確的值（重複值的情況），就換下一個 i。全部處理完後，若 v ∈ [1, n] 出現在原陣列中，`nums[v − 1]` 一定是 v。

**為什麼是 O(n)**。雖然有兩層迴圈，但每次交換都會讓「某個值 v 第一次住進自己的家 v − 1」，而且住進去之後就不會再被換走（交換條件要求 `nums[v − 1] != v`，所以已經住對的位置永遠不會成為交換的目標）。一共只有 n 個家，所以交換總數 ≤ n，整體 O(n)。條件寫成 `nums[v − 1] != v` 而不是 `nums[i] != i + 1` 很重要：遇到重複值，例如 `[1, 1]` 處理到索引 1 時，v = 1、它的家 `nums[0]` 已經是 1，若用後者當條件，會不停地把兩個 1 交換，陷入無窮迴圈。

**另一種寫法：正負號標記**。先把所有不在 [1, n] 的數改成 n + 1（反正對答案沒影響），此時所有數都是正的；然後對每個數 v（取絕對值），若 v ≤ n，就把 `nums[v − 1]` 設成負數，表示「v 出現過」；最後第一個仍為正數的位置 i 給出答案 i + 1。這個寫法不需要交換，每個位置只被讀寫常數次，同樣是 O(n) 時間、O(1) 空間；它用「正負號」這一個位元當作 set 的成員標記。

```text
cyclic sort：nums = [3, 4, -1, 1]，n = 4

i=0  nums[0]=3，家是索引 2，nums[2]=-1 ≠ 3 → 交換   [-1, 4, 3, 1]
     nums[0]=-1 不在 [1, 4]，換下一個 i
i=1  nums[1]=4，家是索引 3，nums[3]=1 ≠ 4 → 交換    [-1, 1, 3, 4]
     nums[1]=1，家是索引 0，nums[0]=-1 ≠ 1 → 交換   [1, -1, 3, 4]
     nums[1]=-1 不在 [1, 4]，換下一個 i
i=2  nums[2]=3，家是索引 2，已經住對 → 下一個
i=3  nums[3]=4，已經住對 → 下一個

掃描：index  0   1   2   3
      值     1  -1   3   4
      應為   1   2   3   4
                 ↑ 第一個不符 → 答案 2

正負號標記：nums = [3, 4, -1, 1]
步驟1 把範圍外的數改成 n+1=5：      [3, 4, 5, 1]
步驟2 v=3 → 把 nums[2] 變負：       [3, 4, -5, 1]
      v=4 → 把 nums[3] 變負：       [3, 4, -5, -1]
      v=5 超出範圍，略過
      v=1 → 把 nums[0] 變負：       [-3, 4, -5, -1]
步驟3 第一個正數在索引 1 → 答案 2
```

cyclic sort 的過程中，i = 1 的位置連續處理了兩次交換：先把 4 送回家、換回來的 1 也再送回家，直到換回一個範圍外的 −1 才停。總共 3 次交換，不超過 n = 4。正負號標記版本中，步驟 2 讀值時一定要取絕對值，因為該位置可能已經被前面的步驟變成負數了。

### 解法

```python
import random


def first_missing_positive(nums: list[int]) -> int:
    n = len(nums)
    for i in range(n):
        while 1 <= nums[i] <= n and nums[nums[i] - 1] != nums[i]:
            v = nums[i]
            nums[i], nums[v - 1] = nums[v - 1], v       # 把 v 送回索引 v - 1
    for i in range(n):
        if nums[i] != i + 1:
            return i + 1
    return n + 1


def first_missing_positive_sign(nums: list[int]) -> int:
    n = len(nums)
    for i in range(n):
        if not 1 <= nums[i] <= n:
            nums[i] = n + 1                             # 範圍外的數不影響答案
    for i in range(n):
        v = abs(nums[i])
        if v <= n:
            nums[v - 1] = -abs(nums[v - 1])             # 標記「v 出現過」
    for i in range(n):
        if nums[i] > 0:
            return i + 1
    return n + 1


def brute(nums):
    s = set(nums)
    k = 1
    while k in s:
        k += 1
    return k


assert first_missing_positive([1, 2, 0]) == 3
assert first_missing_positive([3, 4, -1, 1]) == 2
assert first_missing_positive([7, 8, 9, 11, 12]) == 1
assert first_missing_positive([1]) == 2
assert first_missing_positive([1, 1]) == 2
assert first_missing_positive([2, 1]) == 3
assert first_missing_positive([-2**31, 2**31 - 1]) == 1
assert first_missing_positive(list(range(100000, 0, -1))) == 100001
for _ in range(1000):
    arr = [random.randint(-3, 8) for _ in range(random.randint(1, 8))]
    expect = brute(arr)
    assert first_missing_positive(arr[:]) == expect == first_missing_positive_sign(arr[:])
print("all tests passed")
```

### 複雜度與邊界

兩種寫法都是 O(n) 時間、O(1) 額外空間。cyclic sort 的 `while` 總共最多執行 n 次交換（每次讓一個家第一次住對），加上每個 i 一次失敗的檢查；正負號標記是三次線性掃描。邊界情況：重複值（`[1, 1]`）靠 `nums[v − 1] != v` 避免無窮迴圈；全部是 1 到 n 的排列時答案是 n + 1；極端值 −2³¹ 和 2³¹ − 1 直接被範圍檢查排除，在 Java／C++ 中正負號版本要注意 `abs(−2³¹)` 溢位，所以要先把範圍外的數改成 n + 1 再取絕對值；交換時 Python 的 `nums[i], nums[v − 1] = nums[v − 1], v` 要先把 v 存起來，若寫成 `nums[i], nums[nums[i] − 1] = …`，右邊算完後左邊會依序賦值，`nums[i]` 先被改掉，第二個索引就算錯了。

### Follow-up

> [!question]- F1. 如果不能修改輸入陣列呢？
> 那就無法把陣列本身當表，需要額外空間記錄 1 到 n 的出現情況。最省的做法是一個 n + 1 位元的 bit 陣列，或 `bytearray(n + 2)`，時間 O(n)、空間 O(n) 但常數很小（n = 10⁵ 時約 100 KB 的 `bytearray`，用 bit 陣列只要約 12.5 KB）。若連 O(n) 空間都不允許，簡單的做法只剩對 k = 1, 2, … 逐一線性掃描，O(n²) 時間。面試中要能說出：O(1) 空間的關鍵前提就是「可以修改輸入」，這正是題目允許修改的原因。

> [!question]- F2. 如果要找第 k 個缺少的正整數呢（輸入未排序）？
> 這時原地標記的技巧會碰到瓶頸。第 k 個缺少的正整數最大可能是 n + k（例如陣列剛好是 1 到 n），可能的答案範圍是 [1, n + k]，比陣列長度大，陣列裝不下「n + 1 到 n + k 出現過沒有」的資訊；而且大於 n 的值確實可能出現在陣列中（例如 `[2]`：1 到 n = 1 之中缺了 1 個，若假設大於 n 的都缺少，會推出第 2 個缺少的是 2，但 2 其實在陣列裡，正確答案是 3），不能假設它們都缺少。所以 O(1) 空間時改用原地排序後掃描：走過排序後的不同值，相鄰兩個值 a < b 之間缺了 b − a − 1 個（第一個值之前缺了 `nums[0] − 1` 個，只看正數），累加到 ≥ k 時就能算出答案，O(n log n) 時間。若允許 O(n + k) 空間，用一個大小 n + k 的布林陣列標記即可 O(n + k)。若輸入已經排序（1539. Kth Missing Positive Number），`nums[i] − (i + 1)` 表示「到位置 i 為止缺了幾個」，這個值單調不減，用第 8 章的 binary search 做到 O(log n)。

> [!question]- F3. 同樣的技巧還能解哪些題？例如找出 1 到 n 中所有缺少的數與所有重複的數。
> 448. Find All Numbers Disappeared in an Array、442. Find All Duplicates in an Array、645. Set Mismatch 都是值域 [1, n] 的陣列，用同一個 cyclic sort 放回家之後掃描：`nums[i] != i + 1` 的位置，i + 1 是缺少的數，而 `nums[i]` 是重複的數（它的家已經被正確的值佔了）。每題都是 O(n) 時間、O(1) 額外空間。287. Find the Duplicate Number 多了「不能修改陣列」的限制，就要改用 Floyd 判圈（第 5 章難題 2），這個對比說明了「能否修改輸入」決定了能用哪種技巧。
> ```python
> def missing_and_duplicates(nums):
>     n = len(nums)
>     for i in range(n):
>         while nums[nums[i] - 1] != nums[i]:
>             v = nums[i]
>             nums[i], nums[v - 1] = nums[v - 1], v
>     missing = [i + 1 for i in range(n) if nums[i] != i + 1]
>     dups = [nums[i] for i in range(n) if nums[i] != i + 1]
>     return missing, dups
> ```

> [!question]- F4. 如果數字會不斷加入與刪除，要隨時回答「最小的缺少正整數」呢？
> 用 `Counter` 記錄每個值目前的次數，再維護一個「目前缺少的正整數」的有序集合。答案永遠 ≤ 目前元素數 + 1，所以只需要追蹤 1 到「歷史最大元素數 + 1」的範圍：一開始這些值全部放進缺少集合；加入 v 使次數從 0 變 1 時把 v 從缺少集合移除，刪除使次數從 1 變 0 時再放回去；查詢就是缺少集合的最小值。用平衡樹（或 Python 的 `sortedcontainers.SortedList`）每次 O(log n)；若只有加入沒有刪除，答案只會變大不會變小，更簡單的做法是用一個 `set` 記錄出現過的值，再維護指標 `ans`：每次加入後 `while ans in seen: ans += 1`，指標總共只往上走 O(n) 步，攤銷 O(1)。

### 心得

關鍵突破是兩步：先用鴿籠原理把答案限制在 [1, n + 1]，再讓「值 v」住在「索引 v − 1」，把輸入陣列變成一個 key 為 1..n 的 hash set。它和本章其他題的關係是：其他題用 `dict`／`set` 換時間，這題在不能用額外空間時，指出「當 key 的範圍和陣列長度相當時，陣列本身就是完美的雜湊表」。面試時建議先說 set 的 O(n) 空間解，再說「答案一定在 1 到 n + 1」，接著提出原地標記；寫完後主動用 `[1, 1]` 驗證不會無窮迴圈，並說明交換次數為什麼不超過 n。

## 難題 2｜30. Substring with Concatenation of All Words｜Hard

### 題目

給一個字串 `s` 和一個字串陣列 `words`，`words` 中每個字串**長度都相同**（設為 L），可能有重複。一個「串聯子字串」是 `s` 中的一段連續子字串，它恰好由 `words` 中所有字串以某種順序各用一次拼接而成（重複的字串要用到相同的次數）。回傳所有串聯子字串的起始索引，順序不拘。限制：`1 <= len(s) <= 10⁴`，`1 <= len(words) <= 5000`，`1 <= L <= 30`，全部是小寫英文字母。

- 範例 1：`s = "barfoothefoobarman"`、`words = ["foo", "bar"]`，回傳 `[0, 9]`。索引 0 的 "barfoo" 與索引 9 的 "foobar" 都由 foo 和 bar 組成。
- 範例 2：`s = "wordgoodgoodgoodbestword"`、`words = ["word", "good", "best", "word"]`，回傳 `[]`。words 中 word 要用兩次，s 中找不到這樣的一段。
- 範例 3：`s = "barfoofoobarthefoobarman"`、`words = ["bar", "foo", "the"]`，回傳 `[6, 9, 12]`。
- 範例 4（邊界）：`s = "ab"`、`words = ["abc"]`，回傳 `[]`，s 比所有 words 的總長還短；`s = "aaa"`、`words = ["a", "a"]`，回傳 `[0, 1]`。

### 提示

> [!tip]- 提示 1
> 子字串的總長度固定是 m · L（m 是 words 的個數）。「由這些詞以任意順序組成」等價於「把這段切成 m 個長度 L 的詞，詞頻和 `Counter(words)` 完全相同」。

> [!tip]- 提示 2
> 暴力法對每個起點重新切詞、重新計數。如果視窗每次往右移 L 個字元，切詞的邊界不會變，只是左邊少一個詞、右邊多一個詞。但起點每次移 1 個字元時邊界會變，怎麼辦？

> [!tip]- 提示 3
> 依起點 mod L 分成 L 組（偏移量 r = 0, 1, …, L − 1），每組各自是一串「詞」的序列，在上面做 sliding window：右邊加入一個詞；若它不在 words 中就清空視窗；若它的次數超過需要，就從左邊一次移出一個詞直到合法；視窗剛好有 m 個詞時記錄起點。

### 詳解

**為什麼直覺做法不夠**。暴力法對每個起點 i（約 n 個），把 `s[i : i + m·L]` 切成 m 個詞、建一個 `Counter` 和 `Counter(words)` 比較，每次 O(m · L)，整體 O(n · m · L)。n = 10⁴、m = 5000、L = 30 時，雖然 m · L ≤ n 會限制有效的起點數，但當 m · L 約為 n / 2 時仍有 n / 2 個起點、每個 O(n)，總共約 2.5 × 10⁷ 個字元操作，在 Python 中偏慢。浪費在於：相鄰兩個起點 i 與 i + L 的視窗，共享了 m − 1 個詞，卻每次重算。

**突破點一：依偏移量分組**。如果起點從 i 移到 i + 1，切出來的詞全部改變（邊界都錯開一格），無法增量更新；但從 i 移到 i + L，邊界不變。所以把起點依 `i mod L` 分成 L 組。在偏移量 r 這一組裡，s 可以看成一串詞 `s[r : r+L]`、`s[r+L : r+2L]`、…，問題變成：在這串詞上，找所有長度恰好 m、詞頻等於 `need = Counter(words)` 的連續視窗。這就是第 6 章 sliding window 的標準形，只是視窗中的「字元」換成了「詞」。

**突破點二：視窗的維護規則**。對每個偏移量，用 `window` 記錄視窗內的詞頻，`count` 記錄視窗內的詞數，`left` 是視窗起點。每次右邊加入詞 w：
- 若 w 不在 `need` 中，任何包含它的視窗都不合法，清空視窗，`left` 跳到 w 的下一個詞。
- 否則加入；若 `window[w] > need[w]`，從左邊移出詞，直到 w 的次數回到合法（被移出的可能是別的詞，它們也必須移出，因為視窗必須連續）。
- 若 `count == m`，視窗詞頻一定等於 `need`（每個詞都不超過需要、總數又剛好是 m），記錄 `left`；然後移出最左邊一個詞，讓視窗可以繼續往右滑。

**正確性**。這個視窗維護一個 invariant：視窗內每個詞的次數都 ≤ `need` 中的次數。在這個 invariant 下，「總數等於 m」⇔「詞頻完全相等」，因為每一項都不超過、而總和相等，只能每一項都相等。被移出的起點都不可能是答案：若一個起點的視窗中某詞次數超過需要，從這個起點開始的任何長度 m 的視窗都包含這段過多的詞（或是根本不夠長），所以可以安全丟棄。每個詞最多進出視窗各一次，所以每個偏移量的工作量是 O(n / L) 次詞操作。

```text
s = "barfoothefoobarman"，words = ["foo", "bar"]，L = 3，m = 2
need = {foo: 1, bar: 1}

偏移量 r = 0，切出的詞：
位置 j:   0    3    6    9    12   15
詞:      bar  foo  the  foo  bar  man

j   詞    動作                                  window              left  記錄
0   bar   加入                                  {bar:1}             0
3   foo   加入，count = 2 = m → 記錄 0，移出 bar  {foo:1}             3     0
6   the   不在 need → 清空                       {}                  9
9   foo   加入                                  {foo:1}             9
12  bar   加入，count = 2 = m → 記錄 9，移出 foo  {bar:1}             12    9
15  man   不在 need → 清空                       {}                  18

偏移量 r = 1：切出 arf, oot, hef, oob, arm，全部不在 need，無答案
偏移量 r = 2：rfo, oth, efo, oba, rma，同樣無答案
答案 = [0, 9]

另一個例子：s = "aaa"，words = ["a", "a"]，L = 1，need = {a: 2}
j   詞  window   count  動作
0   a   {a:1}    1
1   a   {a:2}    2      count = m → 記錄 left = 0，移出 s[0]
2   a   {a:2}    2      count = m → 記錄 left = 1，移出 s[1]
答案 = [0, 1]
```

第一個例子顯示了兩種縮小方式：遇到不在 words 中的 "the" 直接清空並跳過它，記錄答案後只移出一個詞以便繼續滑動。第二個例子 L = 1，只有一個偏移量，就退化成第 6 章的「找所有 anagram」（438），說明本題是那題在「詞」上的推廣。

### 解法

```python
import random
from collections import Counter


def find_substring(s: str, words: list[str]) -> list[int]:
    if not words or not s:
        return []
    L, m = len(words[0]), len(words)
    if m * L > len(s):
        return []
    need = Counter(words)
    res = []
    for r in range(L):                              # 依起點 mod L 分組
        window: Counter[str] = Counter()
        left, count = r, 0
        for j in range(r, len(s) - L + 1, L):
            w = s[j:j + L]
            if w not in need:                       # 包含 w 的視窗都不合法
                window.clear()
                count, left = 0, j + L
                continue
            window[w] += 1
            count += 1
            while window[w] > need[w]:              # 維持「每個詞都不超過需要」
                window[s[left:left + L]] -= 1
                count -= 1
                left += L
            if count == m:                          # 每項不超過且總數相等 → 完全相等
                res.append(left)
                window[s[left:left + L]] -= 1
                count -= 1
                left += L
    return sorted(res)


def brute(s, words):
    if not words:
        return []
    L, m = len(words[0]), len(words)
    need = Counter(words)
    return [i for i in range(len(s) - m * L + 1)
            if Counter(s[i + k * L:i + (k + 1) * L] for k in range(m)) == need]


assert find_substring("barfoothefoobarman", ["foo", "bar"]) == [0, 9]
assert find_substring("wordgoodgoodgoodbestword", ["word", "good", "best", "word"]) == []
assert find_substring("barfoofoobarthefoobarman", ["bar", "foo", "the"]) == [6, 9, 12]
assert find_substring("ab", ["abc"]) == []
assert find_substring("aaa", ["a", "a"]) == [0, 1]
assert find_substring("wordgoodgoodgoodbestword", ["word", "good", "best", "good"]) == [8]
for _ in range(500):
    L = random.randint(1, 3)
    s = "".join(random.choice("ab") for _ in range(random.randint(1, 14)))
    words = ["".join(random.choice("ab") for _ in range(L)) for _ in range(random.randint(1, 4))]
    assert find_substring(s, words) == brute(s, words)
print("all tests passed")
```

### 複雜度與邊界

令 n = `len(s)`。時間 O(n · L + m · L)：L 個偏移量，每個偏移量約 n / L 個詞位置，每個詞最多進出視窗各一次，每次切片與雜湊成本 O(L)，所以每個偏移量 O(n)、全部 O(n · L)；建 `need` 要 O(m · L)。空間 O(m · L)：`need` 與 `window` 最多存 m 個不同的詞。邊界情況：`m · L > n` 時直接回傳空串列；words 有重複時靠 `need` 中的次數處理（範例 2 要兩個 word）；s 中出現 words 以外的詞時清空視窗；記錄答案後只移出一個詞，讓重疊的答案（範例 4 的 `[0, 1]`）都能被找到；結果依起點排序只是為了測試穩定，題目不要求順序。

### Follow-up

> [!question]- F1. 每個詞的切片與雜湊要 O(L)，能不能把時間降到 O(n + m · L)？
> 用 rolling hash（第 25 章）在 O(n) 內算出 s 中每個起點長度 L 的子字串雜湊值，並把 words 中每個詞的雜湊值對應到一個整數 id（同一個詞同一個 id），先算出 `ids[i]`：起點 i 的子字串對應的 id，不在 words 中就是 −1。之後滑動視窗只操作整數，每次 O(1)，所有偏移量合計 O(n)，總時間 O(n + m · L) 期望值。碰撞的風險要處理：可以用兩組不同模數的雙重雜湊，或在雜湊相同時再比較一次字串（但那會讓最差情況回到 O(n · L)）。

> [!question]- F2. 如果 words 中的詞長度不一樣呢？
> 那就沒有固定的切詞格線，偏移量分組的做法失效。對每個起點，要判斷 s 的一段能否被切成「恰好用完這組詞」，狀態是「目前位置」加上「已經用掉哪些詞」，最差是指數級。m 很小時可以把已使用的詞編成 bitmask（相同的詞要分開編號或改用次數向量），對每個起點做記憶化搜尋（第 24 章），O(n · 2^m · m · Lmax)；配合 trie（第 13 章）可以在每個位置快速列出所有能匹配的詞。面試時重點是指出「等長」是讓 sliding window 成立的關鍵前提。

> [!question]- F3. 如果所有詞的長度 L = 1 呢？
> 這時只有一個偏移量，問題就是「在 s 中找所有和 words 這組字元互為 anagram 的子字串」，也就是第 6 章核心題 5（438. Find All Anagrams in a String）；若只問存在與否，就是第 6 章核心題 4（567. Permutation in String）。字元集只有 26 種時，`need` 和 `window` 可以換成長度 26 的陣列，並維護「目前有幾個字母的次數剛好相等」來做 O(1) 的比較，整體 O(n)。這個關係值得在面試中說出來：本題就是那題把字元換成固定長度的詞。

> [!question]- F4. 如果 s 是串流（一次來一個字元）而且很長，不能存下整個 s 呢？
> 同時維護 L 個視窗，偏移量 r 的視窗負責所有起點 ≡ r (mod L) 的詞。保留最近 L 個字元的環狀緩衝區，每來一個字元，就有一個新的長度 L 的詞結束，它屬於偏移量 `(目前位置 − L + 1) mod L` 的視窗，交給那個視窗做一次「加入」。因為縮小視窗時要知道左邊被移出的詞，每個視窗用一個 deque 存自己視窗內的詞（最多 m 個）。記憶體 O(m · L²)，與 s 的長度無關，每個字元的攤銷時間 O(L)（切出新詞的成本，配合 F1 的 rolling hash 可降為 O(1)）。

### 心得

關鍵突破是依起點 mod L 分成 L 組，讓每組的切詞邊界固定，問題就變成在「詞」的序列上做 sliding window，並維持「視窗中每個詞都不超過需要」的 invariant，於是「詞數等於 m」就代表完全匹配。它和本章的關係是：計數表本身就是 4.3 節的 `Counter`，但這題的難處在於讓計數表**增量更新**，而不是每個起點重建；和第 6 章的 438 是同一題在字元與詞之間的推廣。面試時先說暴力的 O(n · m · L)，指出相鄰起點共享 m − 1 個詞，再說明為什麼移動 1 個字元無法增量、移動 L 個字元可以，最後用 `"aaa"`、`["a", "a"]` 驗證重疊答案不會漏掉。

## 難題 3｜149. Max Points on a Line｜Hard

### 題目

給平面上 n 個**互不相同**的整數座標點 `points[i] = [x, y]`，回傳最多有幾個點落在同一條直線上。限制：`1 <= n <= 300`，座標在 `-10⁴` 到 `10⁴` 之間。

- 範例 1：`points = [[1, 1], [2, 2], [3, 3]]`，回傳 `3`，三點都在 y = x 上。
- 範例 2：`points = [[1, 1], [3, 2], [5, 3], [4, 1], [2, 3], [1, 4]]`，回傳 `4`。(1, 4)、(2, 3)、(3, 2)、(4, 1) 都在 x + y = 5 上。
- 範例 3（邊界）：`points = [[0, 0]]`，回傳 `1`；任意兩個點回傳 `2`（兩點一定共線）。
- 範例 4（垂直與水平線）：`points = [[2, 1], [2, 5], [2, -3], [7, 1]]`，回傳 `3`，三點在垂直線 x = 2 上。

### 提示

> [!tip]- 提示 1
> 暴力法：每兩點決定一條線，再檢查所有點是否在線上，O(n³)。能不能固定一個點，一次找出「經過它的所有線」各有幾個點？

> [!tip]- 提示 2
> 固定錨點 p，其他點 q 和 p 共線於同一條線 ⇔ 向量 q − p 的方向相同。所以對每個錨點，把其他點依「方向」分組計數，次數最多的方向加上錨點本身就是經過 p 的最佳線。

> [!tip]- 提示 3
> 方向不要用浮點斜率：用 `(dx, dy)` 除以 `gcd(|dx|, |dy|)` 約分，再統一符號（dx > 0，或 dx = 0 時 dy > 0）。這樣垂直線、水平線、負斜率都能正確地成為 hash key。

### 詳解

**為什麼直覺做法不夠**。每兩點決定一條線，再用外積檢查其他每個點是否共線，這是 O(n³)，n = 300 時約 4.5 × 10⁶ 組三元組（C(300, 3)），其實還跑得動，但面試期待的是 O(n²)。另一個直覺是用斜率 `dy / dx` 當 key 分組，這是正確的方向，問題出在細節：浮點數除法有誤差，兩組本應相同的斜率可能得到不同的浮點值；垂直線的 dx = 0 會除以零；而且光有斜率並不能區分平行的兩條線。

**突破點一：固定錨點，讓斜率足以代表一條線**。斜率只代表方向，不代表位置；但如果所有的線都要求經過同一個錨點 p，那麼「方向相同」就等於「同一條線」。所以對每個錨點 p，把其他點 q 依方向 q − p 分組，最大的組大小加 1（錨點本身）就是經過 p 的最多點數。對所有錨點取最大值即為答案，O(n²) 次方向計算。

**突破點二：方向的 canonical key**。把 (dx, dy) 除以 g = gcd(|dx|, |dy|)，得到最簡整數比，例如 (2, 4) 與 (3, 6) 都變成 (1, 2)；再規定符號：dx > 0，或 dx = 0 時 dy > 0，讓 (−1, −2) 也變成 (1, 2)、(0, −3) 變成 (0, 1)。這正是 4.4 節的 `direction_key`。因為點互不相同，dx 與 dy 不會同時為 0，gcd 一定是正數。整數運算完全沒有精度問題，垂直線自然變成 (0, 1)、水平線變成 (1, 0)，不需要特判。

**只需要看錨點之後的點**。對錨點 i 只考慮 j > i 的點即可。理由：最佳的線上有若干個點，令其中索引最小的是 i*；以 i* 為錨點時，線上其他點的索引都大於 i*，而且方向相同，所以都會被分到同一組，這條線一定會被數到。這讓工作量減半，也帶來一個剪枝：以 i 為錨點最多只能數到 n − i 個點，若目前的最佳值已經 ≥ n − i，之後的錨點不可能更好，可以提前結束。

```text
points = [(1,1), (3,2), (5,3), (4,1), (2,3), (1,4)]
索引       0      1      2      3      4      5

錨點 0 = (1,1)：
  q      dx,dy    gcd   key
  (3,2)  (2,1)     1    (2,1)
  (5,3)  (4,2)     2    (2,1)
  (4,1)  (3,0)     3    (1,0)
  (2,3)  (1,2)     1    (1,2)
  (1,4)  (0,3)     3    (0,1)
  計數 {(2,1): 2, (1,0): 1, (1,2): 1, (0,1): 1} → 最多 2 + 1 = 3

錨點 1 = (3,2)：
  (5,3)  (2,1)     1    (2,1)
  (4,1)  (1,-1)    1    (1,-1)
  (2,3)  (-1,1)    1    (-1,1) → 統一符號 (1,-1)
  (1,4)  (-2,2)    2    (-1,1) → 統一符號 (1,-1)
  計數 {(2,1): 1, (1,-1): 3} → 最多 3 + 1 = 4

  y
  4 ●                      方向 (1,-1) 的那組：
  3 ·  ●     ●             (3,2) 和 (4,1)、(2,3)、(1,4)
  2 ·     ●                → 直線 x + y = 5
  1 ●        ●
    1  2  3  4  5  x
```

錨點 1 的例子中，(2, 3) 在錨點的左上方、(4, 1) 在右下方，原始的 (dx, dy) 一個是 (−1, 1)、一個是 (1, −1)，若沒有統一符號，它們會被分成兩組，答案就會少算。(1, 4) 的 (−2, 2) 先約分再統一符號，也落入同一組。

### 解法

```python
import random
from collections import Counter
from itertools import combinations
from math import gcd


def max_points(points: list[list[int]]) -> int:
    n = len(points)
    if n <= 2:
        return n
    best = 2
    for i in range(n):
        if best >= n - i:                        # 剩下的錨點不可能更好
            break
        x1, y1 = points[i]
        directions: Counter[tuple[int, int]] = Counter()
        for j in range(i + 1, n):
            dx, dy = points[j][0] - x1, points[j][1] - y1
            g = gcd(dx, dy)                      # 點互不相同，g > 0
            dx, dy = dx // g, dy // g
            if dx < 0 or (dx == 0 and dy < 0):
                dx, dy = -dx, -dy
            directions[(dx, dy)] += 1
        best = max(best, max(directions.values()) + 1)
    return best


def brute(points):
    n = len(points)
    if n <= 2:
        return n
    best = 2
    for (ax, ay), (bx, by) in combinations(points, 2):
        cnt = sum(1 for cx, cy in points if (bx - ax) * (cy - ay) == (by - ay) * (cx - ax))
        best = max(best, cnt)
    return best


assert max_points([[1, 1], [2, 2], [3, 3]]) == 3
assert max_points([[1, 1], [3, 2], [5, 3], [4, 1], [2, 3], [1, 4]]) == 4
assert max_points([[0, 0]]) == 1
assert max_points([[0, 0], [5, 7]]) == 2
assert max_points([[2, 1], [2, 5], [2, -3], [7, 1]]) == 3
assert max_points([[0, 0], [10**4, 10**4 - 1], [-10**4, -10**4 + 1]]) == 3   # 斜率極接近 1 也不會誤判
assert max_points([[0, 0], [94911151, 94911150], [94911152, 94911151]]) == 2  # 浮點斜率會在這裡出錯
for _ in range(300):
    pts = random.sample([[x, y] for x in range(-3, 4) for y in range(-3, 4)], random.randint(1, 10))
    assert max_points(pts) == brute(pts)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n² log V)：O(n²) 個點對，每對做一次 gcd，V 是座標差的最大值（2 × 10⁴），gcd 的成本是 O(log V)。空間 O(n)：每個錨點的 `Counter` 最多 n 個方向，用完就丟。邊界情況：n ≤ 2 直接回傳 n；垂直線 (0, dy) 的 gcd 是 |dy|，約分成 (0, ±1) 再統一成 (0, 1)；水平線約分成 (±1, 0) 再統一成 (1, 0)；Python 的 `gcd` 對負數回傳非負值，`//` 對可整除的負數結果正確；測試中的第七個例子是經典的浮點陷阱：(94911151, 94911150) 與 (94911152, 94911151) 的斜率在 double 下相等，但它們並不共線，整數 key 不會被騙。題目保證點互不相同；若有重複點，見 F1。

### Follow-up

> [!question]- F1. 如果點可以重複呢？
> 重複的點和錨點沒有方向（dx = dy = 0），gcd 為 0 會除以零。對每個錨點另外計數 `dup`：j > i 且座標與錨點相同的點數，不放進方向表。經過錨點的最佳線點數是 `max(directions.values(), default=0) + dup + 1`，因為重複點落在經過錨點的每一條線上。若所有點都相同，方向表是空的，答案是 dup + 1 = n。提前結束的剪枝仍然成立。時間不變，O(n² log V)。

> [!question]- F2. 如果要回傳那條線的方程式，而不只是點數呢？
> 用直線的 canonical 形式 ax + by = c 當 key：經過 (x1, y1)、(x2, y2) 的線取 a = y2 − y1、b = x1 − x2、c = a · x1 + b · y1，再除以 gcd(|a|, |b|, |c|)，並統一符號（a > 0，或 a = 0 時 b > 0）。這個 key 同時包含方向與位置，所以不需要錨點：對所有 C(n, 2) 個點對，對 key 計數，一條含 k 個點的線會被數到 C(k, 2) 次，由最大的次數 p 反推 k = (1 + √(1 + 8p)) / 2。時間 O(n² log V)、空間 O(n²)，比錨點法多用空間，但能直接得到線的方程式；或者沿用錨點法，在找到最佳方向時記下錨點與方向，就能寫出 (x1, y1) + t · (dx, dy)。

> [!question]- F3. 如果座標是浮點數（例如 GPS 經緯度）呢？
> gcd 正規化不再適用。若座標有固定的小數位數（例如 6 位），可以乘上 10⁶ 轉成整數再用原方法，這是最穩健的。若是任意浮點數，「共線」本身就要定義容差：例如點到線的距離小於 ε。這時對每個錨點把其他點依角度 `atan2(dy, dx)`（並把方向 θ 與 θ + π 視為相同）排序，再用 sliding window 找角度差小於 δ 的最大群組，O(n² log n)。要和面試官說明：容差會讓「共線」失去傳遞性（a 與 b 接近、b 與 c 接近，a 與 c 未必接近），所以結果依賴容差的定義。

> [!question]- F4. 如果 n 是 10⁵，但已知最佳的線上至少有 n / 10 個點呢？
> O(n²) 太慢，可以用隨機抽樣：隨機選兩個不同的點，算出它們決定的線，再用 O(n) 的外積檢查有幾個點在線上。若最佳線上的點占比為 f = 1/10，一次抽到的兩點都在最佳線上的機率約為 f² = 1/100，所以重複約 T = 500 次，失敗機率約 (1 − 1/100)⁵⁰⁰ ≈ e⁻⁵ ≈ 0.7%，總時間 O(T · n)。這是 RANSAC 類方法的核心想法，適合「答案很大」的情況；答案很小（例如只有 3 個點共線）時抽樣幾乎不可能命中，只能回到 O(n²)。

### 心得

關鍵突破是「固定一個錨點後，方向相同就等於在同一條線上」，讓斜率足以當作直線的 key，再用 gcd 約分與統一符號把方向變成精確的整數 key。它和本章的關係是：核心題 2 的 key 是字母計數，這題的 key 是約分後的方向，兩題的難處都在讓「等價」剛好對應到「key 相同」；只看 j > i 的點則和 Two Sum 的「先查再放」一樣，是為了讓每條線只在它的第一個點被數一次。面試時先說 O(n³) 的外積解，再提出錨點加方向計數，並主動說明為什麼不用浮點斜率（精度、除以零），最後用垂直線與兩個相反方向的點驗證正規化。

## 難題 4｜336. Palindrome Pairs｜Hard

### 題目

給一個由**互不相同**的字串組成的陣列 `words`，找出所有索引對 `(i, j)`（i ≠ j），使得 `words[i] + words[j]`（依序串接）是一個回文。回傳所有這樣的索引對，順序不拘。限制：`1 <= len(words) <= 5000`，`0 <= len(words[i]) <= 300`，只含小寫英文字母。

- 範例 1：`words = ["abcd", "dcba", "lls", "s", "sssll"]`，回傳 `[[0, 1], [1, 0], [3, 2], [2, 4]]`。四個回文分別是 "abcddcba"、"dcbaabcd"、"slls"、"llssssll"。
- 範例 2：`words = ["bat", "tab", "cat"]`，回傳 `[[0, 1], [1, 0]]`。
- 範例 3（邊界，空字串）：`words = ["a", ""]`，回傳 `[[0, 1], [1, 0]]`。空字串和任何回文串接都還是回文。
- 範例 4（邊界）：`words = ["abc"]`，回傳 `[]`；同一個字串不能和自己配對。

### 提示

> [!tip]- 提示 1
> 暴力法是檢查所有 n² 個有序對，每次串接後判斷回文，O(n² · k)，k 是字串長度。n = 5000 時有 2.5 × 10⁷ 對，太多了。能不能固定一個字串，直接「算出」它需要的另一半，再去 hash table 查？

> [!tip]- 提示 2
> 假設 `w + u` 是回文，而且 w 比較長（或一樣長）。那麼 u 反過來，一定等於 w 的開頭一段，而 w 剩下的部分本身必須是回文。所以把 w 切成 `w[:c] + w[c:]`，若 `w[c:]` 是回文，需要的另一半就是 `w[:c]` 的反轉。

> [!tip]- 提示 3
> 對稱地，若 `w[:c]` 是回文，`reverse(w[c:]) + w` 就是回文。對每個 w 嘗試所有切點 c，兩種情況各查一次「反轉後的那一半」是否在 `{字串: 索引}` 中。要小心 c = 0 與 c = len(w) 的兩種情況會把同一對算兩次，其中一種要排除空的一半。

### 詳解

**為什麼直覺做法不夠**。暴力法 O(n² · k)，在最大限制下約 2.5 × 10⁷ 對、每對最多比較 600 個字元，遠遠超過時限。瓶頸在於：對每個 w，我們不知道哪些 u 可能配對，只好全部試。如果能從 w 本身推出「它的搭檔必須長什麼樣子」，就能把試配對變成查表。

**突破點：回文的結構決定了搭檔**。設 S = w + u 是回文，|w| = a、|u| = b。回文反轉後不變，所以 S 的前 b 個字元等於 u 的反轉。分兩種情況：
- 若 a ≥ b：S 的前 b 個字元都在 w 裡，所以 `w[:b] = reverse(u)`；而 S 中間剩下的 `w[b:]` 必須自己是回文（回文去掉對稱的頭尾仍是回文）。換句話說：切點 c = b，`w[c:]` 是回文，且 `reverse(w[:c])` 是某個字串 u。
- 若 a < b：對稱地看 S 的後 a 個字元，`u[b−a:] = reverse(w)`，`u[:b−a]` 是回文。從 u 的角度看：切點 c = b − a ≥ 1，`u[:c]` 是回文，且 `reverse(u[c:])` 是 w，配對是 (w 的索引, u 的索引)。

於是演算法是：把所有字串放進 `{字串: 索引}`；對每個字串 w（索引 i）與每個切點 c ∈ [0, |w|]：情況一，若 `w[c:]` 是回文且 `reverse(w[:c])` 在表中（索引 j ≠ i），輸出 (i, j)；情況二，若 c ≥ 1、`w[:c]` 是回文且 `reverse(w[c:])` 在表中（索引 j），輸出 (j, i)。

**為什麼每一對恰好被找到一次**。由上面的推導，每個回文對 (i, j) 在 a ≥ b 時由 w = words[i] 的情況一以 c = b 找到；在 a < b 時由 u = words[j] 的情況二以 c = b − a 找到。情況一的搭檔長度是 c、情況二的搭檔長度是 |u| − c，所以給定一對，切點是唯一的；而 a ≥ b 與 a < b 互斥，所以不會被兩種情況各找一次。情況二要求 c ≥ 1 正是為了這個互斥：若允許 c = 0，就變成「u 整個反轉是 w，且 a = b」，這一對已經被 w 的情況一（c = |w|）找過了。

```text
words = ["abcd", "dcba", "lls", "s", "sssll"]
index = {abcd: 0, dcba: 1, lls: 2, s: 3, sssll: 4}

w = "lls"（i = 2），切點 c 從 0 到 3：
 c   w[:c]  w[c:]   情況一：w[c:] 回文？→ 查 rev(w[:c])   情況二：c≥1 且 w[:c] 回文？→ 查 rev(w[c:])
 0   ""     "lls"   否                                    （c = 0 不做）
 1   "l"    "ls"    否                                    是 → 查 "sl"：無
 2   "ll"   "s"     是 → 查 "ll"：無                       是 → 查 "s"：索引 3 → 輸出 (3, 2)  "s"+"lls" = "slls"
 3   "lls"  ""      是 → 查 "sll"：無                      否

w = "sssll"（i = 4）：
 c=2  w[:2] = "ss" 回文 → 情況二查 rev("sll") = "lls"：索引 2 → 輸出 (2, 4)
      "lls" + "sssll" = "llssssll"
      l l s s | s s l l     ← 外層的 "lls" 和 "sll" 互為反轉，中間的 "ss" 是回文

w = "abcd"（i = 0）：
 c=4  w[4:] = "" 回文 → 情況一查 rev("abcd") = "dcba"：索引 1 → 輸出 (0, 1)
w = "dcba"（i = 1）：
 c=4  同理輸出 (1, 0)；c=0 時情況二不做，所以 (0, 1) 不會被重複輸出
```

"lls" 的 c = 2 說明了情況二：前半 "ll" 自己是回文，所以只要在前面接上後半 "s" 的反轉 "s"，整體就是回文。"sssll" 的例子說明為什麼要用「回文去掉頭尾仍是回文」：外層由 "lls" 與它的反轉配對，中間剩下的 "ss" 必須自己對稱。

### 解法

```python
import random


def palindrome_pairs(words: list[str]) -> list[list[int]]:
    index = {w: i for i, w in enumerate(words)}
    res = []
    for i, w in enumerate(words):
        for c in range(len(w) + 1):
            pre, suf = w[:c], w[c:]
            if suf == suf[::-1]:                       # 情況一：w + rev(pre)
                j = index.get(pre[::-1])
                if j is not None and j != i:
                    res.append([i, j])
            if c > 0 and pre == pre[::-1]:             # 情況二：rev(suf) + w，c ≥ 1 避免重複
                j = index.get(suf[::-1])
                if j is not None and j != i:
                    res.append([j, i])
    return res


def brute(words):
    return [[i, j] for i in range(len(words)) for j in range(len(words))
            if i != j and (words[i] + words[j]) == (words[i] + words[j])[::-1]]


assert sorted(palindrome_pairs(["abcd", "dcba", "lls", "s", "sssll"])) == [[0, 1], [1, 0], [2, 4], [3, 2]]
assert sorted(palindrome_pairs(["bat", "tab", "cat"])) == [[0, 1], [1, 0]]
assert sorted(palindrome_pairs(["a", ""])) == [[0, 1], [1, 0]]
assert palindrome_pairs(["abc"]) == []
assert sorted(palindrome_pairs(["", "aba", "ab"])) == [[0, 1], [1, 0], [2, 1]]   # "ab" + "aba" = "ababa"
for _ in range(500):
    pool = {"".join(random.choice("ab") for _ in range(random.randint(0, 4))) for _ in range(random.randint(1, 8))}
    words = list(pool)
    got = palindrome_pairs(words)
    assert len(got) == len(set(map(tuple, got)))         # 沒有重複輸出
    assert sorted(got) == sorted(brute(words))
print("all tests passed")
```

### 複雜度與邊界

令 n 為字串數、k 為最長長度。時間 O(n · k²)：每個字串有 k + 1 個切點，每個切點做常數次 O(k) 的切片、反轉、回文判斷與雜湊查詢。空間 O(n · k)，用於 `index` 表（加上輸出）。和暴力法的 O(n² · k) 比，當 n 遠大於 k 時（本題 n = 5000、k = 300）大幅改善。邊界情況：空字串會和每個回文字串配成兩對（情況一 c = 0 時 `rev("") = ""`，情況二 c = |w| 時查到空字串），空字串自己的 c = 0 查到自己，被 `j != i` 排除；回文字串 w 的情況一 c = |w| 會查到 `rev(w) = w` 本身，同樣被排除；題目保證字串互不相同，若有重複，見 F2。

### Follow-up

> [!question]- F1. O(n · k²) 還能更快嗎？
> 瓶頸有兩個：每個切點的回文判斷是 O(k)，每次查詢的切片與雜湊也是 O(k)。回文判斷可以先用 Manacher 演算法（第 25 章）或 Z-function，對每個字串 O(k) 算出「哪些前綴是回文、哪些後綴是回文」的布林陣列，之後每次 O(1)。查詢可以改用 trie：把所有字串反轉後插入 trie，並在每個節點記錄「從這個節點往下、剩下部分是回文的字串有哪些」。對每個 w 沿著 trie 往下走，走的過程中依照預先算好的回文旗標收集答案，每個字串 O(k + 輸出數)。總時間 O(n · k + 輸出數)。實作比 hash 版本長很多，面試中通常先寫 hash 版本，再口述 trie 的優化方向。

> [!question]- F2. 如果 words 中可以有重複的字串呢？
> 把 `index` 改成「字串 → 索引串列」，查到時對串列中每個 j ≠ i 都輸出。要特別注意相同字串互相配對的情況：若 w 是回文且出現多次，任兩個不同索引的 w 串接都是回文，情況一 c = |w| 時查到的串列中排除自己後，其他每個都能配對；而 w 不是回文時，相同的 w 串接一定不是回文（w + w 回文 ⇔ w 是回文）。輸出數可能是 Θ(n²)（例如所有字串都是 "a"），這時任何演算法都至少 Θ(n²)。

> [!question]- F3. 如果只要知道有多少對，或任意選一些字串串接成最長回文呢？
> 只計數時把 `res.append` 換成計數器即可，複雜度不變。「任意選字串串接成最長回文」是另一類題，例如 2131. Longest Palindrome by Concatenating Two Letter Words：每個詞都是兩個字母，用 `Counter` 計數，`xy` 和 `yx` 能成對放在兩側，貢獻 `min(cnt[xy], cnt[yx])` 對；`xx` 型的詞自己和自己成對，若有剩下一個奇數的 `xx`，可以放在正中間。O(n) 時間。這類題共同的工具都是「用 hash 找反轉後的搭檔」。

> [!question]- F4. 如果字串數 n 很小（例如 10），但每個字串很長（k 到 10⁵）呢？
> 這時本題的 O(n · k²) 約 10¹¹，反而比暴力的 O(n² · k) ≈ 10⁷ 慢得多，所以要依 n 與 k 的相對大小選演算法。n 小 k 大時，直接枚舉 n² 個有序對；判斷 `words[i] + words[j]` 是否回文時，不必真的串接，可以先對每個字串算好正向與反向的 rolling hash（第 25 章），串接字串的雜湊可以由兩段組合出來，回文判斷就變成比較「正向雜湊」與「反向雜湊」，每對 O(1)。總時間 O(n · k + n²)，加上雜湊碰撞的極小風險（可用雙重雜湊降低）。面試中主動問「n 和 k 哪個大」，並說明兩種演算法的交叉點，是很好的取捨討論。

### 心得

關鍵突破是「回文的結構決定了搭檔的樣子」：較長的字串切成兩段，一段自己是回文，另一段的反轉就是搭檔，於是 n² 次配對變成 n · k 次查表。和本章的關係：它是 Two Sum 的字串版本，Two Sum 由 x 算出需要的 target − x，這題由 w 的每個切點算出需要的 reverse(w[:c])；也和核心題 2 一樣，難處在定義「要查什麼」。面試時先講暴力法，再用 a ≥ b 與 a < b 兩種情況推出切點的條件，最後主動說明 c ≥ 1 為什麼能避免重複，並用空字串測試，這三件事都講清楚就是很完整的答案。

## 難題 5｜1224. Maximum Equal Frequency｜Hard

### 題目

給一個正整數陣列 `nums`，找出最長的前綴長度 ℓ，使得這個前綴 `nums[0 : ℓ]` **恰好刪除一個元素**之後，所有出現過的數字出現次數都相同。如果刪除後前綴變成空的，也視為符合（沒有數字，次數自然「都相同」）。限制：`2 <= len(nums) <= 10⁵`，`1 <= nums[i] <= 10⁵`。

- 範例 1：`nums = [2, 2, 1, 1, 5, 3, 3, 5]`，回傳 `7`。前綴 `[2, 2, 1, 1, 5, 3, 3]` 刪掉 5 之後，2、1、3 各出現兩次。長度 8 的整個陣列中 2、1、5、3 各出現兩次，刪掉任何一個都會讓某個數變成一次，不符合。
- 範例 2：`nums = [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5]`，回傳 `13`。刪掉 5，其他各三次。
- 範例 3（邊界）：`nums = [1, 1]`，回傳 `2`。刪掉一個 1，剩下 `[1]`，只有一個數，次數都相同。
- 範例 4：`nums = [1, 1, 1, 2, 2, 2]`，回傳 `5`。前綴 `[1, 1, 1, 2, 2]` 刪掉一個 1，兩個數各兩次；整個陣列各三次，刪任何一個都會不一致。

### 提示

> [!tip]- 提示 1
> 對每個前綴都試著刪掉每個元素再檢查，是 O(n³) 甚至更慢。先想想：判斷一個前綴是否合格，只需要知道哪些資訊？答案和「哪個數出現幾次」的細節無關，只和「次數的分佈」有關。

> [!tip]- 提示 2
> 維護兩張表：`freq[x]` 是 x 目前出現的次數，`cnt[f]` 是「目前出現恰好 f 次的數有幾個」。每加入一個元素，兩張表都可以 O(1) 更新。再維護目前的最大次數 `maxf`。

> [!tip]- 提示 3
> 前綴長度 ℓ 合格只有三種情況：(1) `maxf == 1`，所有數都只出現一次，刪任何一個都行；(2) `maxf * cnt[maxf] + 1 == ℓ`，除了一個只出現一次的數，其他都出現 maxf 次，刪掉那個數；(3) `maxf + (maxf − 1) * cnt[maxf − 1] == ℓ`，恰好一個數出現 maxf 次，其他都是 maxf − 1 次，從那個數刪一個。

### 詳解

**為什麼直覺做法不夠**。對每個前綴 ℓ，嘗試刪掉每個位置，再用 `Counter` 檢查所有次數是否相同，是 O(n³)。稍微聰明一點，對每個前綴只需要嘗試刪掉「每個不同的值各一次」，並且增量維護 `freq`，但每次檢查「所有次數是否相同」仍要掃過所有不同的值，O(n · D)，D 可達 n，最差 O(n²) = 10¹⁰。瓶頸是「檢查所有次數是否相同」需要看過每個值。

**突破點一：只看次數的分佈**。一個前綴是否合格，只和「出現 f 次的數有幾個」有關，與具體是哪些數無關。所以除了 `freq`（值 → 次數），再維護 `cnt`（次數 → 有幾個值），也就是**計數的計數**。加入 x 時，x 的次數從 f 變成 f + 1：`cnt[f] −= 1`、`cnt[f + 1] += 1`、`freq[x] += 1`，三個 O(1) 操作。最大次數 `maxf` 只會增加，每次更新為 `max(maxf, freq[x])`。

**突破點二：列舉所有合格的形狀**。刪掉一個元素後所有次數相同，意思是刪除前的次數分佈只能「差一點」就全部相同。刪掉的元素屬於某個值 v，v 的次數從 f 變 f − 1，其他值不變。設刪除後大家都是 t 次（或 v 消失、其他都是 t 次）：
- 若 v 刪除後消失（f = 1）：其他值都是 t 次，也就是「一個值出現 1 次、其他都出現 maxf 次」，總長度 ℓ = maxf · cnt[maxf] + 1。「只有一個值、出現一次」的情況 maxf = 1，交給最後的特例處理。
- 若 v 刪除後還在（f − 1 = t）：其他值都是 t = f − 1 次，也就是「恰好一個值出現 maxf 次、其他都出現 maxf − 1 次」，ℓ = maxf + (maxf − 1) · cnt[maxf − 1]。這包括「只有一個值」的情況（cnt[maxf − 1] = 0、ℓ = maxf），刪掉一個後仍只有一個值。
- 特例 maxf = 1：所有值都只出現一次，刪掉任何一個，剩下的都是一次（或空），一定合格。

為什麼用長度等式就能判斷？以第二條為例：`cnt[maxf] · maxf` 是所有出現 maxf 次的值的元素總數，若它加 1 等於 ℓ，代表剩下恰好 1 個元素，它所屬的值次數 < maxf 且 ≥ 1，只能是出現 1 次的單一值。第三條同理：maxf 次的值至少一個，加上所有 maxf − 1 次的值的元素總數剛好是 ℓ，代表恰好一個值是 maxf 次（多一個就超過 ℓ），沒有其他次數的值。用總長度做檢查，就不需要知道「有幾種不同的次數」。

```text
nums = [2, 2, 1, 1, 5, 3, 3, 5]

ℓ  加入  freq（非零）            cnt（非零）     maxf  條件(1)  條件(2) maxf·cnt[maxf]+1  條件(3) maxf+(maxf-1)·cnt[maxf-1]  合格？
1   2    {2:1}                   {1:1}            1    是       —                          —                                 是
2   2    {2:2}                   {2:1}            2    否       2·1+1=3 ≠ 2                2+1·0=2 = 2                       是
3   1    {2:2,1:1}               {1:1,2:1}        2    否       2·1+1=3 = 3                —                                 是
4   1    {2:2,1:2}               {2:2}            2    否       2·2+1=5 ≠ 4                2+1·0=2 ≠ 4                       否
5   5    {2:2,1:2,5:1}           {1:1,2:2}        2    否       2·2+1=5 = 5                —                                 是
6   3    {2:2,1:2,5:1,3:1}       {1:2,2:2}        2    否       2·2+1=5 ≠ 6                2+1·2=4 ≠ 6                       否
7   3    {2:2,1:2,5:1,3:2}       {1:1,2:3}        2    否       2·3+1=7 = 7                —                                 是 ← 刪 5
8   5    {2:2,1:2,5:2,3:2}       {2:4}            2    否       2·4+1=9 ≠ 8                2+1·0=2 ≠ 8                       否
答案 = 7（「—」表示前面的條件已經成立，不必再算）
```

ℓ = 2 時只有一個值 2 出現兩次，條件 (3) 成立（刪掉一個 2 剩 `[2]`）；ℓ = 7 時 cnt 告訴我們有三個值出現兩次、一個值出現一次，條件 (2) 成立。整個過程只看 `cnt[maxf]` 與 `cnt[maxf − 1]` 兩個數，所以每一步 O(1)，不需要掃過所有值。

### 解法

```python
import random
from collections import Counter


def max_equal_freq(nums: list[int]) -> int:
    freq: Counter[int] = Counter()           # 值 → 出現次數
    cnt: Counter[int] = Counter()            # 次數 → 有幾個值出現這麼多次
    maxf = best = 0
    for length, x in enumerate(nums, 1):
        f = freq[x]
        if f > 0:
            cnt[f] -= 1
        freq[x] = f + 1
        cnt[f + 1] += 1
        maxf = max(maxf, f + 1)
        if (maxf == 1                                        # 全部只出現一次
                or maxf * cnt[maxf] + 1 == length            # 一個值出現一次，其他都是 maxf
                or maxf + (maxf - 1) * cnt[maxf - 1] == length):   # 一個值 maxf 次，其他 maxf - 1 次
            best = length
    return best


def brute(nums):
    best = 0
    for length in range(1, len(nums) + 1):
        prefix = nums[:length]
        for r in range(length):
            rest = Counter(prefix[:r] + prefix[r + 1:])
            if len(set(rest.values())) <= 1:
                best = length
                break
    return best


assert max_equal_freq([2, 2, 1, 1, 5, 3, 3, 5]) == 7
assert max_equal_freq([1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5]) == 13
assert max_equal_freq([1, 1]) == 2
assert max_equal_freq([1, 2]) == 2
assert max_equal_freq([1, 1, 1, 2, 2, 2]) == 5
assert max_equal_freq([10, 2, 8, 9, 3, 8, 1, 5, 2, 3, 7, 6]) == 8
assert max_equal_freq([7] * 1000) == 1000                  # 只有一個值：刪一個仍只有一個值
for _ in range(500):
    arr = [random.randint(1, 4) for _ in range(random.randint(2, 10))]
    assert max_equal_freq(arr) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每個元素做常數次 `Counter` 更新與三個 O(1) 的條件判斷。空間 O(D)，D 是不同值的個數（`freq` 最多 D 項，`cnt` 最多 D 項，因為次數的種類不超過值的種類）。邊界情況：只有一個值時（`[7] * 1000`）條件 (3) 的 `cnt[maxf − 1]` 是 0，ℓ = maxf 成立；maxf = 1 時條件 (3) 會讀 `cnt[0]`，我們刻意在 f = 0 時不做 `cnt[0] −= 1`，讓 `cnt[0]` 保持 0，不過 maxf = 1 已經被條件 (1) 接住；條件 (2) 在 maxf = 1 時會變成 `cnt[1] + 1 == ℓ`，不會成立，但也不需要它。題目要求「恰好刪一個」，所以「刪除前就全部相同」本身不算合格，例如 ℓ = 4 的 `[2, 2, 1, 1]`，這正是條件中沒有 `maxf · cnt[maxf] == ℓ` 的原因（除非 maxf = 1 或只有一個值，那兩種情況刪一個仍然合格，已被涵蓋）。

### Follow-up

> [!question]- F1. 如果改成「最多刪除一個」（也可以不刪）呢？
> 多一個條件：`maxf * cnt[maxf] == length`，代表所有出現過的值都恰好出現 maxf 次，不刪就已經合格。加上原本的三個條件即可，仍是 O(n)。這個變形常被用來檢查你是否真的理解每個條件的意義：原題中 `[2, 2, 1, 1]` 不合格，在「最多刪一個」的版本中就合格。

> [!question]- F2. 如果只有一個字串，問「刪掉恰好一個字元後，所有字母的次數是否相同」呢（2423. Remove Letter To Equalize Frequency）？
> 這是本題對單一前綴（整個字串）的判斷版本。可以直接用同樣的三個條件：算出 `freq`、`cnt`、`maxf`，ℓ = 字串長度，檢查 (1)(2)(3) 是否有一個成立。因為字母只有 26 種，也可以暴力地對每個出現過的字母試著減一、檢查剩下的非零次數是否全部相同，O(26²)。這題的陷阱和原題一樣：`"aazz"` 不刪的話各兩次，但題目要求一定要刪，刪掉後變成 1 與 2，答案是 False。

> [!question]- F3. 如果要求的是最長的「子陣列」（任意起點）而不只是前綴呢？
> 合格與否對子陣列的端點沒有單調性：合格的子陣列延長一格可能不合格，再延長又可能合格（例如前綴長度 3 合格、4 不合格、5 又合格），所以不能用 sliding window 的雙指標收縮。直接的做法是對每個起點 s，從 s 開始用本題的增量方法往右延伸，記錄最長合格的長度，每個起點 O(n)，總共 O(n²)。若面試官要求更快，誠實地說明「合格性不單調，標準的 sliding window 不適用」，並給出 O(n²) 的正確解，比硬套錯誤的視窗更好。

> [!question]- F4. 如果要支援從尾端刪除（pop），隨時回答目前的前綴是否合格呢？
> `freq` 和 `cnt` 的更新是可逆的：pop 掉 x 時，`cnt[freq[x]] −= 1`、`freq[x] −= 1`，若新的次數 > 0 就 `cnt[freq[x]] += 1`。比較麻煩的是 `maxf`：pop 可能讓最大次數變小，但因為每次只有一個值的次數減 1，若 `cnt[maxf]` 變成 0，新的最大次數一定是 maxf − 1（被 pop 的那個值現在就是 maxf − 1 次），所以 `maxf −= 1` 即可。push 與 pop 都是 O(1)，查詢也是 O(1)。這個「次數每次只變 1，所以最大值也只變 1」的性質，和第 27 章難題 4（895. Maximum Frequency Stack）是同一個觀察。

### 心得

關鍵突破是把「所有值的次數是否相同」這個需要掃過全部值的檢查，換成只看「計數的計數」`cnt` 與總長度的三個 O(1) 等式。和本章其他題的關係：前面的題目都是「值 → 次數」的一層計數，這題多了一層「次數 → 有幾個值」，這是處理「頻率分佈」類題目的通用工具，在 LFU Cache（第 27 章難題 1）與 Maximum Frequency Stack 中都會再出現。面試時先說明只需要看次數分佈，再逐一列出三種合格形狀並解釋為什麼長度等式足以判斷，最後用 `[1, 1]` 與 `[1, 1, 1, 2, 2, 2]` 手動驗證；把「恰好刪一個」與「最多刪一個」的差別主動點出來，能展現你對邊界的敏感度。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 補數查詢（先查再放） | 「兩個元素滿足某個等式」，給定一個能算出另一個 | 表裡只放目前之前的元素，查 `target − x` 或 `g(x)` | 核心題 1（1）、219 Contains Duplicate II、1010 Pairs of Songs |
| 配對計數 | 「有幾對」而不是「找一對」 | `Counter` 版的先查再放，累加次數 | 4.3 節 `count_pairs`、1512 Number of Good Pairs、2364 |
| Canonical key 分組 | 「等價的分在一起」「是否同構／同一條線」 | 設計 key：排序、計數 tuple、差值序列、首次出現序號、約分方向 | 核心題 2（49）、難題 3（149）、249、205、290 |
| 存在性與攤銷 | 「下一個存在嗎」「最長連續」，要 O(n) | `set` 查詢＋只從起點展開，或端點長度合併 | 核心題 3（128）、41 的 set 解、217 Contains Duplicate |
| Meet in the middle | 從多個獨立集合各選一個湊目標 | 前半組合存 `Counter`，後半組合查詢，指數減半 | 核心題 4（454）、1755 Closest Subsequence Sum（折半＋排序） |
| 頻率最大值 | 「哪個位置／值被最多共享」 | 把幾何或結構轉成 key，對 key 計數取最大 | 核心題 5（554）、169 Majority Element、347（第 14 章核心題 2） |
| 陣列當 hash table | 值域 1..n、O(1) 額外空間、可修改輸入 | cyclic sort 放回家，或用正負號標記 | 難題 1（41）、448、442、645 |
| 視窗內計數 | 子字串／子陣列的「組成」等於目標 | `Counter` 在視窗中增量更新，維持「不超過需要」的 invariant | 難題 2（30）、438、567、76（第 6 章） |
| 由結構推出搭檔 | 兩個物件組合後滿足某性質 | 把一方切開，一半檢查性質、另一半去表中查 | 難題 4（336）、Two Sum 的字串版本 |
| 計數的計數 | 「所有頻率相同」「最大頻率」隨時變動 | `freq[x]` 加上 `cnt[f]`，maxf 每次只變 1 | 難題 5（1224）、2423、895（第 27 章難題 4） |
| 前綴和＋hash | 子陣列和等於 k、0 與 1 數量相等 | 前綴和當 key，先查再放，表中存次數或最早索引 | 560、525（第 7 章核心題 2、3）、1371（第 7 章難題 4） |
| Hash＋其他結構 | 需要 O(1) 查找又需要順序或隨機存取 | dict 存位置，搭配 linked list、陣列或 heap | 146 LRU、380（第 27 章核心題 1、2）、460 LFU |

**下限與上限**。最簡單的形式是「看過沒有」：217 Contains Duplicate 只是把元素丟進 `set`，考的是知道 `set` 是 O(1)。往上一層是核心題 1 的補數查詢，難點只在「先查再放」的順序。中間層是 key 與 value 的設計（49、128、454、554）：要能說出 key 為什麼讓等價物件剛好相撞、value 為什麼要存次數而不是布林值、以及攤銷分析為什麼成立。上限的題目難在三個地方，常常同時出現：第一，**key 不明顯**，必須先做一個結構觀察，例如 149 的「固定錨點後方向等於直線」、336 的「回文決定搭檔的形狀」；第二，**表要和其他 pattern 結合**，例如 30 的計數表必須放在 sliding window 中增量維護、1224 需要第二層的「計數的計數」；第三，**不允許額外空間**，例如 41 必須看出值域與長度相當，把輸入陣列本身變成表。

**與其他 pattern 的關係**。Hashing 與 two pointers（第 5 章）常是同一題的兩種解法：Two Sum 未排序時用 hash（O(n) 時間、O(n) 空間），已排序時用 two pointers（O(n) 時間、O(1) 空間）；3Sum 與 4Sum 則因為需要對值去重，排序加 two pointers 比 hash 乾淨。和 sliding window（第 6 章）的關係最緊密：幾乎所有字串視窗題都在視窗裡維護一個 `Counter`，難題 2 就是例子。和 prefix sum（第 7 章）結合時，hash 的 key 變成前綴和，處理「子陣列和為 k」這類 sliding window 無法處理的負數情況。當 key 是字串而且需要前綴查詢時，hash 要換成 trie（第 13 章），例如 336 的優化版本；當需要快速比較大量子字串時，hash 的概念延伸成 rolling hash（第 25 章）。核心題 3 的串流版本可以用 Union-Find（第 17 章）。

**容易混淆之處**。第一，hash table 不保留順序，所以「最接近」「範圍內」「第 k 小」這類查詢不能用它，要換成排序、binary search（第 8 章）或平衡樹；看到「等於」才想 hash。第二，「O(1)」是平均值，最差情況是 O(n)，而且算 key 本身可能是 O(L)，複雜度要把 key 的成本算進去。第三，「子序列」與「子集合」不同：128 不看順序所以能用 set，若題目要求元素在陣列中依序出現，就要用 hash 加 DP（核心題 3 F4）。第四，計數題要分清楚「有沒有」（`set`）、「有幾個」（`Counter`）、「在哪裡」（`dict` 存索引）、「最早／最晚在哪裡」（`setdefault` 或覆蓋），選錯會導致重複計數或漏算。

## 本章重點整理

- Hashing 的本質是把「往回找某個確切的值」從 O(n) 的掃描變成 O(1) 的查表；看到內層迴圈只在找特定值，就想到它。
- 每題先回答三個問題：key 是什麼、value 是什麼（索引、次數、串列、長度）、什麼時候放進表裡。
- 「先查再放」維持「表中只有目前之前的元素」的 invariant，自然避免自己配自己，也讓配對計數不重複。
- 需要「有幾個」用 `Counter`，只需要「有沒有」用 `set`；`defaultdict` 查詢會新增 key，查詢時用 `in` 或 `get`。
- 分組題的工作量幾乎全在 key：anagram 用排序或 26 格計數 tuple，平移用差值序列，同構用首次出現序號，方向用 gcd 約分並統一正負號；key 必須不可變，避免浮點數。
- 128 的 O(n) 來自攤銷：只從起點（x − 1 不在集合中）往上走，每個值最多被踩一次；要遍歷 set 而不是原陣列。
- Meet in the middle：互相獨立的多個集合，把一半的組合存成 `Counter`、另一半來查，O(n⁴) → O(n²)，k 個集合是 O(n^⌈k/2⌉)。
- 幾何或結構上的「最佳位置」常能轉成「哪個 key 出現最多次」，例如 554 的接縫位置、149 的方向。
- 值域 1..n 且要求 O(1) 空間時，讓值 v 住在索引 v − 1（cyclic sort 或正負號標記），陣列本身就是 hash table；交換條件要寫成 `nums[v − 1] != v` 才能處理重複值。
- 視窗內的計數要維護「每項不超過需要」的 invariant，這時「總數相等」就等於「完全相等」；詞長固定時依偏移量分成 L 組各自滑動。
- 「計數的計數」`cnt[f]` 讓「所有頻率是否相同」變成 O(1) 檢查；頻率每次只變 1，所以最大頻率也每次只變 1。
- 複雜度要把算 key 的成本算進去（字串是 O(L)），並知道 hash table 最差是 O(n)；被要求不用額外空間時，切換到排序加 two pointers，並說明會失去原始索引。
