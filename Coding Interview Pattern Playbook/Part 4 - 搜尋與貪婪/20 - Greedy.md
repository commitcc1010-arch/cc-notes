---
chapter: 20
title: Greedy
part: 4
---

# 第 20 章　Greedy

> [!abstract] 本章地圖
> **一句話**：greedy（貪婪）是每一步都做「現在看起來最好」的選擇並且永不反悔；它只有在你能證明「一定存在一個最佳解包含這個選擇」時才是對的，所以貪婪題的核心不是程式，而是證明。
>
> **辨識訊號**：
> - 只需要維護一個「進度」量就能描述狀態：目前最遠能到哪、目前油量、目前已經能湊出 `[1, miss)`
> - 排序之後結構變簡單：依結束時間、截止日、左端點、最小值處理，每一步的選擇變得「被迫」
> - 「最少幾次／最多幾個」而 n 到 10⁵，DP 的狀態（位置 × 次數、位置 × 時間）太大
> - 交換相鄰兩個選擇可以直接比較好壞（exchange argument 的訊號）
> - 「先拿了再說，不行再退掉最差的那個」：後悔式貪婪，搭配 heap
> - 一個元素受左右兩邊的約束：左右各掃一趟再合併
>
> **核心題**：55、45、134、763、846
>
> **難題**：135、330、630、871、1326

## 20.1 這個 Pattern 解決什麼問題

先看一個最小的例子。你有一間會議室和一堆會議，每場會議有開始與結束時間 `[s, e)`，兩場會議不能重疊（前一場結束的時刻剛好是下一場開始的時刻可以）。最多能排幾場？暴力解是列舉所有子集合，檢查是否兩兩不重疊，O(2ⁿ · n)。DP 也可以：依結束時間排序後 `dp[i]` = 只考慮前 i 場的最多場數，配合 binary search 找前一個相容的會議，O(n log n)。但這題還有更簡單的做法：**依結束時間排序，能排就排**。只要掃一次，O(n log n)，而且程式只有五行。

難的是選對「貪婪的標準」。直覺上至少有三種規則：最早開始的先排、最短的先排、最早結束的先排。前兩種都是錯的。最早開始：`[0, 10)、[1, 2)、[3, 4)`，它會先選 `[0, 10)`，把另外兩場都擋掉，只得到 1 場，最佳是 2 場。最短優先：`[0, 5)、[4, 7)、[6, 11)`，最短的 `[4, 7)` 同時和另外兩場衝突，選了它只剩 1 場，最佳是選 `[0, 5)` 和 `[6, 11)` 共 2 場。只有「最早結束」是對的，而它之所以對，是因為有一個可以寫下來的論證：最早結束的會議留給後面的時間最多，任何最佳解的第一場都可以換成它而不變差。

另一個經典的警告是找零。硬幣面額 `{1, 3, 4}`、要湊 6 元，「每次拿最大的面額」得到 4 + 1 + 1 共 3 枚，但 3 + 3 只要 2 枚。同樣的貪婪在 `{1, 5, 10, 25}` 卻永遠是對的。差別不在程式，而在面額結構是否讓「拿最大的」這個選擇一定安全。這就是本章反覆出現的主題：**貪婪的程式往往很短，真正的工作是說明為什麼這個局部選擇不會害到全域最佳**。

所以本章每一題都會回答三個問題：第一，貪婪的選擇是什麼（每一步選哪個）；第二，為什麼它是對的（用 exchange argument 或 stays ahead 證明）；第三，題目稍微改一下，貪婪會在哪裡失敗（給出具體的反例）。面試時，能說清楚第二點和第三點，比寫出程式更能展現 L5 的水準，因為這正是面試官用來區分「背過答案」和「真的理解」的地方。

## 20.2 辨識訊號

| 題目特徵 | 為什麼是 greedy | 本章哪一題 |
|---|---|---|
| 能到達的位置一定是一段前綴，只需要記「最遠到哪」 | 可達集合可以用一個數字完整描述，不必記住走法 | 核心題 1（55） |
| 最少步數，而每一步能到的範圍是連續區間 | BFS 的每一層是一段連續區間，用兩個邊界就能模擬 | 核心題 2（45）、難題 5（1326） |
| 環狀累加，某處失敗後前面的起點也都會失敗 | 失敗前的前綴和非負，從中間開始只會更差，可以整段跳過 | 核心題 3（134） |
| 切成最多段，每個切點的合法性互不影響 | 所有合法切點同時用上就是最多段，貪婪只是把它們找出來 | 核心題 4（763） |
| 最小的元素只能有一種用法 | 被迫的選擇不需要猜，處理完再看下一個最小的 | 核心題 5（846） |
| 一個位置同時受左鄰與右鄰約束 | 左右約束各自的最小解可以分開算，取最大值同時滿足兩邊 | 難題 1（135） |
| 「目前能湊出 `[1, miss)`」並問最少補幾個數 | 覆蓋範圍可以用一個邊界描述，補 miss 讓邊界推得最遠 | 難題 2（330） |
| 依截止日處理，超出時丟掉最差的那個 | 後悔式貪婪：維持「目前最好的集合」，heap 找出最該退掉的元素 | 難題 3（630）、難題 4（871） |
| 「最少／最多」且 n 到 10⁵，但 DP 狀態需要記時間或油量 | 狀態太大時，先找能讓狀態只剩一維的貪婪觀察 | 630、871 的 DP 都是 O(n²) 或 O(n · D) |

一個實用的反向檢查：如果你想到的貪婪規則能被一個三、四個元素的小例子打敗，它就是錯的。面試時花一分鐘在紙上試兩三個刻意刁難的例子（20.5 節會整理常見的反例長相），比寫完程式再發現錯誤便宜得多。

## 20.3 模板與原理：四種貪婪骨架

貪婪題的程式長相比其他 pattern 分散，但大致可以歸成四種骨架。記住骨架的意義是：看到題目時知道「要維護什麼量」「每一步更新什麼」，然後把力氣花在證明上。

### 骨架 A：排序後掃描

先依某個關鍵（結束時間、截止日、最小值）排序，然後從頭掃，每個元素「能拿就拿」或「被迫做某件事」。20.1 節的會議排程是標準形，第 9 章核心題 3（435. Non-overlapping Intervals）是它的另一種問法（最少刪幾個 = 總數 − 最多能留幾個）。

```python
import random
from itertools import combinations


def max_meetings(meetings: list[tuple[int, int]]) -> int:
    """最多能排幾場互不重疊的會議；[s, e) 半開區間，e == 下一場的 s 可以相接。"""
    count, last_end = 0, float("-inf")
    for s, e in sorted(meetings, key=lambda m: m[1]):   # 依結束時間排序
        if s >= last_end:                                # 和上一場不重疊就排
            count += 1
            last_end = e
    return count


def brute(meetings):
    for k in range(len(meetings), 0, -1):
        for combo in combinations(sorted(meetings), k):
            if all(combo[i][1] <= combo[i + 1][0] for i in range(k - 1)):
                return k
    return 0


assert max_meetings([(1, 3), (2, 5), (4, 6), (6, 8), (5, 9), (8, 10)]) == 4
assert max_meetings([(0, 10), (1, 2), (3, 4)]) == 2      # 最早開始會錯的例子
assert max_meetings([(0, 5), (4, 7), (6, 11)]) == 2      # 最短優先會錯的例子
assert max_meetings([]) == 0
assert max_meetings([(1, 2), (1, 2), (1, 2)]) == 1
for _ in range(300):
    ms = []
    for _ in range(random.randint(0, 7)):
        s = random.randint(0, 10)
        ms.append((s, s + random.randint(1, 5)))
    assert max_meetings(ms) == brute(ms)
print("all tests passed")
```

### 骨架 B：邊界推進

狀態只用一個「目前覆蓋到哪」的邊界描述，每一步在「目前能用的選擇」中挑讓邊界推得最遠的那個。這是 BFS 的壓縮版：每一層能到的範圍是一段連續區間，只要記住區間的右端。核心題 1、2（55、45）、難題 2（330）、難題 5（1326）都是這個骨架。下面是最一般的形式：用最少的區間覆蓋 `[0, target]`。

```python
import random
from itertools import combinations


def min_cover(target: int, intervals: list[tuple[int, int]]) -> int:
    """用最少個閉區間 [l, r] 覆蓋 [0, target]；做不到回傳 -1。"""
    intervals = sorted(intervals)
    count = covered = i = 0
    while covered < target:
        best = covered
        while i < len(intervals) and intervals[i][0] <= covered:   # 所有能接上目前覆蓋的區間
            best = max(best, intervals[i][1])
            i += 1
        if best == covered:            # 沒有任何區間能把邊界往右推
            return -1
        covered = best                 # 選右端最遠的那一個
        count += 1
    return count


def brute(target, intervals):
    for k in range(len(intervals) + 1):
        for combo in combinations(sorted(intervals), k):
            covered = 0
            for l, r in combo:
                if l <= covered:
                    covered = max(covered, r)
            if covered >= target:
                return k
    return -1


assert min_cover(10, [(0, 4), (2, 6), (5, 10)]) == 3      # (0,4) 與 (5,10) 之間的 (4,5) 要靠 (2,6) 接上
assert min_cover(10, [(0, 5), (5, 10)]) == 2              # 端點相接即可
assert min_cover(10, [(1, 10)]) == -1                     # 0 沒被覆蓋
assert min_cover(0, []) == 0
assert min_cover(6, [(0, 3), (0, 1), (2, 6), (3, 4)]) == 2
for _ in range(300):
    t = random.randint(0, 8)
    ivs = []
    for _ in range(random.randint(0, 6)):
        l = random.randint(0, 8)
        ivs.append((l, l + random.randint(0, 4)))
    assert min_cover(t, ivs) == brute(t, ivs)
print("all tests passed")
```

```text
target = 10，intervals 依左端排序：(0,4) (2,6) (5,10)

covered = 0   能接上的（l <= 0）：(0,4)            → 選 r 最大的 4，count = 1
covered = 4   能接上的（l <= 4）：(2,6)            → 推到 6，count = 2
covered = 6   能接上的（l <= 6）：(5,10)           → 推到 10，count = 3
covered = 10 >= target，結束

0    2    4    5    6         10
[=========]                        (0,4)
     [=========]                   (2,6)
               [================]  (5,10)
```

這個例子顯示「邊界推進」和「挑最長的區間」不同：`(5, 10)` 最長，但在 covered = 0 時它根本接不上。每一輪只考慮左端 ≤ covered 的區間，因為只有它們能和已覆蓋的部分相接；在這些區間裡選右端最遠的，因為覆蓋到更右邊永遠不會讓之後的選擇變少。指標 `i` 只往右走，每個區間只被看一次，所以排序後是 O(m)。

### 骨架 C：後悔式貪婪

有些題目無法事先知道哪個選擇最好，但可以「先拿，違反限制時再退掉目前最差的那個」。關鍵是 heap：它讓我們在 O(log n) 內找到最該退掉的元素。下面的例子是：從左到右走過一排藥水，每瓶會讓生命值加上 `nums[i]`（可能是負的），生命值從 0 開始、任何時刻都不能小於 0，每瓶可以選擇喝或不喝，最多能喝幾瓶？

```python
import heapq
import random
from itertools import combinations


def max_potions(nums: list[int]) -> int:
    health, taken = 0, []              # taken 是 min-heap：最上面是喝過最傷的那瓶
    for x in nums:
        health += x
        heapq.heappush(taken, x)
        if health < 0:                 # 違反限制：退掉喝過最傷的一瓶（可能就是剛喝的這瓶）
            health -= heapq.heappop(taken)
    return len(taken)


def brute(nums):
    n = len(nums)
    for k in range(n, -1, -1):
        for idx in combinations(range(n), k):
            h, ok = 0, True
            for i in idx:
                h += nums[i]
                if h < 0:
                    ok = False
                    break
            if ok:
                return k
    return 0


assert max_potions([4, -4, 1, -3, 1, -3]) == 5
assert max_potions([-1, -2]) == 0
assert max_potions([]) == 0
assert max_potions([3, -1, -1, -1, -5, 2]) == 5
for _ in range(500):
    arr = [random.randint(-5, 5) for _ in range(random.randint(0, 8))]
    assert max_potions(arr) == brute(arr)
print("all tests passed")
```

為什麼「退掉最傷的那瓶」是對的？invariant 是：處理完前 i 瓶時，heap 裡是「前 i 瓶中能喝的最大瓶數」，而且在所有同樣瓶數的選法中，它的生命值最高。加入一瓶後若生命值變負，瓶數不可能再增加（否則就和 invariant 矛盾），於是只能維持原瓶數；而在原瓶數的選法中，退掉最負的那一瓶讓剩下的生命值最高，留給未來最大的空間。難題 3（630）和難題 4（871）都是這個骨架，第 14 章難題 3（502. IPO）則是它的「先收集可選項，再挑最大」版本。

### 骨架 D：兩趟掃描

當每個位置同時受到左邊和右邊的約束時，從左往右一趟只能處理左邊的約束，從右往左一趟只能處理右邊的約束，最後逐點取最大值（或最小值）合併。下面用「每個位置到最近的字元 c 的距離」示範：左往右一趟算到左邊最近的 c，右往左一趟算到右邊最近的 c，取兩者的最小值。

```python
import random


def shortest_to_char(s: str, c: str) -> list[int]:
    n, inf = len(s), float("inf")
    ans, last = [inf] * n, -inf
    for i in range(n):                 # 左邊最近的 c
        if s[i] == c:
            last = i
        ans[i] = i - last
    last = inf
    for i in range(n - 1, -1, -1):     # 右邊最近的 c，與左邊的結果取最小
        if s[i] == c:
            last = i
        ans[i] = min(ans[i], last - i)
    return ans


def brute(s, c):
    pos = [i for i, ch in enumerate(s) if ch == c]
    return [min(abs(i - p) for p in pos) for i in range(len(s))]


assert shortest_to_char("loveleetcode", "e") == [3, 2, 1, 0, 1, 0, 0, 1, 2, 2, 1, 0]
assert shortest_to_char("aaab", "b") == [3, 2, 1, 0]
assert shortest_to_char("b", "b") == [0]
for _ in range(300):
    t = "".join(random.choice("ab") for _ in range(random.randint(1, 10)))
    if "a" in t:
        assert shortest_to_char(t, "a") == brute(t, "a")
print("all tests passed")
```

兩趟掃描的正確性來自「約束可以分解」：左約束只依賴左邊的值、右約束只依賴右邊的值，所以各自有一個逐點最小的解；取兩者的逐點最大值（像難題 1 的 135. Candy）同時滿足兩邊，而且任何合法解在每一點都至少要這麼大。這是第 5 章難題 1（42. Trapping Rain Water）的「左邊最高、右邊最高」也在用的結構。

## 20.4 怎麼證明貪婪是對的：exchange argument 與 stays ahead

貪婪的證明幾乎都落在四種寫法之一。面試時不需要寫成數學論文，但要能用兩三句話說出「我用哪一種、關鍵步驟是什麼」。

**工具一：exchange argument（交換論證）**。拿任意一個最佳解 O，找出它和貪婪解 G 第一個不同的選擇；證明把 O 的那個選擇換成 G 的選擇之後，O 仍然合法而且不會變差。重複這個交換，O 就一步步變成 G，所以 G 也是最佳。以會議排程為例：設 G 選的第一場是結束最早的 g₁，O 的第一場是 o₁。因為 g₁ 結束得最早，`end(g₁) <= end(o₁)`，把 o₁ 換成 g₁ 之後，g₁ 和 O 剩下的會議仍然不衝突（它們都在 `end(o₁)` 之後開始），場數不變。接著對「g₁ 結束後的會議」這個子問題重複同樣的論證。

```text
交換論證：把最佳解 O 的第一場換成貪婪的 g1

時間軸  0    2    4    6    8    10
O:          [==o1==]  [o2]  [==o3==]
G:      [g1]                           end(g1) <= end(o1)
O':     [g1]          [o2]  [==o3==]   o1 換成 g1：仍不衝突、場數不變
```

**工具二：greedy stays ahead（貪婪保持領先）**。定義一個「進度」量，證明對每個 k，貪婪在 k 步之後的進度都不落後於任何其他解在 k 步之後的進度；最後一步再說明「進度領先」等價於「答案不比較差」。會議排程的進度是「第 k 場的結束時間」：歸納可得 `end(g_k) <= end(o_k)`，因為 o_k 開始於 `end(o_{k-1}) >= end(g_{k-1})` 之後，所以 o_k 也是貪婪在第 k 步的候選，而貪婪選了結束最早的那個。若 O 有 k + 1 場，o_{k+1} 開始於 `end(o_k) >= end(g_k)` 之後，貪婪不會停在 k 場，矛盾。核心題 2（45）與難題 5（1326）的「k 步內最遠能到哪」就是這種寫法。

**工具三：下界加構造**。先證明任何合法解都至少（或至多）是某個值 L，再證明貪婪剛好達到 L。難題 1（135）的證明是這樣：每個孩子的糖果數都至少是「左邊約束的最小值」與「右邊約束的最小值」中的較大者，而逐點取最大值本身就是合法的分配。核心題 4（763）也是：分段數不可能超過合法切點數加一，而貪婪用上了每一個合法切點。

**工具四：invariant（不變式）**。對後悔式貪婪（骨架 C）最自然：說明處理完前 i 個元素時，貪婪維護的集合是「前 i 個元素中的最佳集合」，而且在同樣好的集合中，它對未來最有利（例如總時間最短、生命值最高）。歸納的每一步只需要討論「加入新元素後是否違反限制」兩種情況。難題 3（630）會完整走一次這種證明。

**面試時怎麼講**。最實用的格式是三句話：「我每一步選 X；因為任何最佳解都可以把它的那一步換成 X 而不變差（或：因為貪婪在每一步之後的 Y 都不落後）；所以貪婪是最佳的。」如果面試官追問，再把交換或歸納的細節展開。不要說「直覺上貪婪是對的」，這是最常被追問到卡住的地方。

## 20.5 貪婪什麼時候會錯：反例的長相與對拍

證明之外，另一個必備的能力是**快速找出反例**。錯的貪婪通常犯下面幾種錯誤之一，看到題目時可以逐一拿來檢查：

| 失敗的長相 | 典型例子 | 為什麼貪婪錯 | 正確做法 |
|---|---|---|---|
| 選擇會改變未來的「形狀」，而不只是推進一個量 | 0/1 背包依價值密度選：容量 50，物品 (重 10, 值 60)、(20, 100)、(30, 120)，貪婪得 160，最佳 220 | 先拿高密度的小物品，留下的空間塞不下大物品 | DP（第 23 章） |
| 有權重 | 加權的會議排程：最早結束的那場價值 1，和它重疊的那場價值 100 | 「留最多時間」不等於「價值最大」 | DP + binary search（第 21 章難題 4 的 1235） |
| 結構不具備 canonical 性質 | 面額 `{1, 3, 4}` 湊 6 | 最大面額不一定在最佳解中 | DP（第 21 章核心題 2 的 322） |
| 只看眼前的大小，不看它帶來的機會 | 跳躍遊戲「每次跳最遠」：`[2, 3, 1, 1, 4]` 跳 3 次，最佳 2 次 | 落點的「下一步能到多遠」才重要 | 選 `i + nums[i]` 最大的落點（核心題 2） |
| 加了容量上限或其他第二維限制 | 871 加油站問題若油箱有上限 | 「事後補加」的假設不成立 | DP 狀態多加一維 |
| 排序的關鍵選錯 | 會議排程依開始時間或長度排序 | 該排序沒有交換論證支撐 | 寫出交換兩個相鄰元素的比較式，看哪個關鍵讓它成立 |

**對拍**。準備時最有效的驗證方法是寫一個暴力解，用大量隨機小輸入和貪婪比較，也就是本章每段程式最後的那個 `for _ in range(...)` 迴圈。它不能證明貪婪正確，但能在幾秒內找到大部分錯誤的貪婪規則，而且找到的反例通常很小，正好可以拿來理解「為什麼錯」。下面是一個找零的例子：自動找出某組面額中，最小的「貪婪會輸」的金額。

```python
def greedy_coins(coins: list[int], amount: int) -> int:
    count = 0
    for c in sorted(coins, reverse=True):
        count += amount // c
        amount %= c
    return count if amount == 0 else -1


def dp_coins(coins: list[int], amount: int) -> int:
    inf = float("inf")
    best = [0] + [inf] * amount
    for a in range(1, amount + 1):
        best[a] = min((best[a - c] + 1 for c in coins if c <= a), default=inf)
    return best[amount] if best[amount] < inf else -1


def first_counterexample(coins: list[int], limit: int = 200) -> int | None:
    for a in range(1, limit + 1):
        if greedy_coins(coins, a) != dp_coins(coins, a):
            return a
    return None


assert first_counterexample([1, 3, 4]) == 6            # 貪婪 4+1+1，最佳 3+3
assert first_counterexample([1, 5, 10, 25]) is None     # 美國硬幣是 canonical 的
assert first_counterexample([1, 10, 25]) == 30          # 少了 5 元：25+1×5 共 6 枚，10×3 只要 3 枚
assert first_counterexample([1, 2, 5, 10, 20, 50]) is None
print("all tests passed")
```

面試時不會真的寫對拍程式，但「我先用兩三個小例子試試這個貪婪」是非常加分的行為。挑例子的技巧是：讓局部最好的選擇剛好擋住兩個「次好但能並存」的選擇（像 20.1 節的最短會議），或讓眼前的大收益把你帶進死路（像每次跳最遠）。

## 20.6 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 沒有證明就寫貪婪 | 範例都過，隱藏測資錯；面試官問「為什麼」答不出來 | 寫之前先用 20.4 節的四種工具之一說出理由，並試兩三個刁難的小例子 |
| 排序關鍵選錯 | 會議排程依開始時間排序、630 依長度排序 | 寫出「交換相鄰兩個元素」的比較，確認排序關鍵讓交換不會變差 |
| 邊界推進的迴圈多處理了最後一格 | 45 題在 `i == n - 1` 時多算一次跳躍 | 迴圈只跑到 `n - 2`，或在推進前先判斷是否已經到終點 |
| 沒處理「推不動」的情況 | 1326、45 的變形在無法覆蓋時無窮迴圈或回傳錯值 | 每次推進前檢查 `farthest <= 目前位置`，成立就回傳 -1 |
| 後悔式貪婪退錯元素 | 630 退掉剛加入的課而不是最長的課，答案偏小 | heap 存「退掉之後最划算」的鍵：最長的時長、最多的油量 |
| 兩趟掃描只做一趟 | 135 遞減序列 `[4, 3, 2, 1]` 每人只拿 1 顆 | 列出約束的方向；有兩個方向就掃兩趟再合併 |
| 把題目的前提當成理所當然 | 330 忘了 nums 已排序、134 忘了答案保證唯一、846 忘了先檢查 `n % W` | 讀題時把「已排序」「保證唯一」「必能到達」這類前提寫下來，想想拿掉後會怎樣 |
| 整數溢位或取整 | 330 在 Java 中 `miss` 超過 2³¹ − 1；1326 的區間左端變負數 | Python 沒有溢位，但要說出來；區間端點先用 `max(0, …)`、`min(n, …)` 截斷 |

## 核心題 1｜55. Jump Game｜Medium

### 題目

給一個非負整數陣列 `nums`，你一開始站在索引 0。站在索引 i 時，可以往右跳 1 到 `nums[i]` 步之間的任意步數（`nums[i] = 0` 代表在這裡動不了）。請判斷能不能到達最後一個索引 `n - 1`。限制：`1 <= n <= 10⁴`，`0 <= nums[i] <= 10⁵`。

- 範例 1：`nums = [2, 3, 1, 1, 4]`，回傳 `True`。從 0 跳 1 步到索引 1，再跳 3 步到索引 4。
- 範例 2：`nums = [3, 2, 1, 0, 4]`，回傳 `False`。不論怎麼跳都會停在索引 3，而 `nums[3] = 0`。
- 範例 3（邊界）：`nums = [0]`，回傳 `True`，起點就是終點。
- 範例 4（邊界）：`nums = [0, 1]`，回傳 `False`，第一步就動不了。

### 思路

暴力解是 DFS 或 DP：`can[i]` 表示從 i 能不能到終點，從右往左算，`can[i] = any(can[j] for j in i+1 .. i+nums[i])`。每個位置要看最多 `nums[i]` 個後繼，最差 O(n²)（例如全是大數字時）。瓶頸在於我們把「從 i 能跳到哪些位置」逐一列出，但這些位置有很強的結構。

關鍵觀察：**能到達的位置永遠是一段前綴 `[0, reach]`**。理由是：如果位置 j 能到達，那麼對任意 k < j，k 也能到達。因為到達 j 的那條路線中，一定有某一跳是從某個 i ≤ k 跳到 ≥ k 的位置（路線從 0 出發、最後在 j，必須跨過 k），而從 i 可以跳任意 1 到 `nums[i]` 步，既然能跳到 k 右邊，當然也能剛好停在 k。有了這個性質，整個可達集合只需要一個數字 `reach` 就能描述，不必記住任何路線。

於是貪婪是：從左往右掃，維護 `reach = max(i + nums[i])`，掃到的 i 必須 ≤ reach（否則 i 到不了，後面也都到不了）。invariant 是「處理完 i 之後，`[0, reach]` 恰好是只用 0..i 起跳時能到的所有位置」。這是一個 stays ahead 型的論證：`reach` 是任何走法用到目前為止的位置所能到達的最遠處，沒有任何走法能比它更遠，所以只要 `reach >= n - 1` 就一定能到，而一旦有 `i > reach`，就證明 i 以後全部到不了。

```text
範例 1：nums = [2, 3, 1, 1, 4]
i    nums[i]  i+nums[i]  reach（處理後）  說明
0      2         2           2           可達 [0, 2]
1      3         4           4           1 <= 2 可起跳，reach 推到 4 >= n-1 → True

範例 2：nums = [3, 2, 1, 0, 4]
i    nums[i]  i+nums[i]  reach（處理後）
0      3         3           3
1      2         3           3
2      1         3           3
3      0         3           3
4      ─         ─           ─           i = 4 > reach = 3 → False

index:   0  1  2  3  4
可達:    ■  ■  ■  ■  □        reach 卡在 3，索引 3 是「黑洞」
```

範例 2 中，前四個位置雖然都能到，但它們最遠都只能到索引 3，而索引 3 的 `nums[3] = 0`。掃到 i = 4 時 4 > reach，於是確定到不了。注意貪婪沒有「選擇」要跳到哪裡；它直接追蹤「所有走法的聯集」能到多遠，這正是它比 DFS 快的原因。

### 解法

```python
import random


def can_jump(nums: list[int]) -> bool:
    reach = 0
    for i, step in enumerate(nums):
        if i > reach:                  # i 到不了，之後的位置也都到不了
            return False
        reach = max(reach, i + step)
        if reach >= len(nums) - 1:     # 提早結束
            return True
    return True


def brute(nums):
    n = len(nums)
    can = [False] * n
    can[-1] = True
    for i in range(n - 2, -1, -1):
        can[i] = any(can[j] for j in range(i + 1, min(n, i + nums[i] + 1)))
    return can[0]


assert can_jump([2, 3, 1, 1, 4]) is True
assert can_jump([3, 2, 1, 0, 4]) is False
assert can_jump([0]) is True
assert can_jump([0, 1]) is False
assert can_jump([1, 0, 1]) is False
assert can_jump([10**5] + [0] * 9999) is True     # 一跳到底
for _ in range(500):
    arr = [random.randint(0, 3) for _ in range(random.randint(1, 10))]
    assert can_jump(arr) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每個位置看一次。空間 O(1)。邊界情況：n = 1 時起點就是終點，第一輪 `reach = nums[0] >= 0 = n - 1` 直接回傳 True，即使 `nums[0] = 0`；`nums[0] = 0` 且 n > 1 時，i = 1 > reach = 0，回傳 False；中間出現 0 不一定失敗，只要前面有某個位置能跳過它（例如 `[2, 0, 0]`）；`nums[i]` 很大時 `i + nums[i]` 可能遠超過 n，不影響判斷，在其他語言也不會溢位（最大約 10⁴ + 10⁵）。

貪婪會失敗的變形：如果規則改成「必須剛好跳 `nums[i]` 步」，可達集合就不再是前綴。例如 `nums = [2, 5, 0, 0]`，只能 0 → 2，然後卡住，答案是 False；但若套用本題的 reach 貪婪，會把索引 1 當成可達（因為 1 ≤ reach = 2），用它的 `1 + 5` 誤判為 True。前綴性質完全來自「可以跳任意 1 到 `nums[i]` 步」，這個前提一拿掉，就必須改用 BFS（見 F2）。

### Follow-up

> [!question]- F1. 如果要回傳最少需要跳幾次呢？
> 這就是核心題 2（45. Jump Game II）。前綴性質仍然成立，而且更強：「最少 k 跳能到的位置」也是一段連續區間，所以可以用兩個邊界模擬 BFS 的每一層，O(n) 時間、O(1) 空間。本題只需要知道「最遠能到哪」，45 題還要知道「第幾層」，所以多一個 `cur_end` 記錄這一層的右端。

> [!question]- F2. 如果每次必須剛好跳 nums[i] 步，而且可以往左或往右（1306. Jump Game III），要判斷能否到達任何值為 0 的位置？
> 可達集合不再是前綴（上面的反例），貪婪失效。把每個索引當成圖的節點，i 連到 `i + nums[i]` 和 `i - nums[i]`（在範圍內才連），從起點做 BFS 或 DFS（第 15 章），遇到 `nums[j] == 0` 就回傳 True。每個節點最多兩條邊，時間 O(n)、空間 O(n)。這個對比很適合在面試中主動說出：貪婪能成立，是因為「任意步數」讓可達集合可以用一個數字描述。

> [!question]- F3. 如果陣列是一個 0／1 字串，只能落在 '0' 上，每次跳的步數必須在 [minJump, maxJump] 之間（1871. Jump Game VII）呢？
> 可達集合又不是前綴了（'1' 的位置永遠到不了），但「能從哪些位置跳到 j」是一段連續區間 `[j - maxJump, j - minJump]`。用 sliding window 維護這段區間內可達位置的個數：j 往右時，加入 `j - minJump`、移除 `j - maxJump - 1`，個數 > 0 且 `s[j] == '0'` 就代表 j 可達。時間 O(n)、空間 O(n)。
> ```python
> def can_reach(s, lo, hi):
>     n = len(s)
>     ok = [False] * n
>     ok[0] = True
>     window = 0                                  # [j - hi, j - lo] 中可達的個數
>     for j in range(1, n):
>         if j - lo >= 0 and ok[j - lo]:
>             window += 1
>         if j - hi - 1 >= 0 and ok[j - hi - 1]:
>             window -= 1
>         ok[j] = s[j] == "0" and window > 0
>     return ok[-1]
> ```

> [!question]- F4. 如果要找出所有「從它出發能到終點」的起點呢？
> 從右往左掃，維護 `goal` = 目前已知能到終點的最左位置，一開始是 n − 1。對每個 i，若 `i + nums[i] >= goal`，i 就是好起點，並令 `goal = i`。正確性：i 是好起點若且唯若 `(i, i + nums[i]]` 中有好起點，而這段區間中最左的候選就是「i 右邊最近的好起點」，也就是目前的 `goal`；它在範圍內就代表存在。時間 O(n)。這是本題的另一種常見寫法：最後只要檢查 `goal == 0`。

> [!question]- F5. 如果每個位置有分數（可正可負），每次跳 1 到 k 步，要最大化經過位置的分數總和（1696. Jump Game VI）呢？
> 這時「跳到看起來最好的下一格」的貪婪會失敗，因為一個高分的落點可能把你逼進一段只能踩負分的路線，局部選擇會改變之後的可選集合。正確做法是 DP：`dp[i] = nums[i] + max(dp[i - k .. i - 1])`。直接算是 O(nk)；用 monotonic deque（第 6 章難題 2 的 239 Sliding Window Maximum）維護視窗內 dp 的最大值，降到 O(n)。這題說明了「到不到得了」可以貪婪，「到達的總收益」通常要 DP。

## 核心題 2｜45. Jump Game II｜Medium

### 題目

規則和核心題 1 相同：站在索引 i 時可以往右跳 1 到 `nums[i]` 步。這次題目保證一定能到達最後一個索引，請回傳最少的跳躍次數。限制：`1 <= n <= 10⁴`，`0 <= nums[i] <= 1000`。

- 範例 1：`nums = [2, 3, 1, 1, 4]`，回傳 `2`：0 → 1 → 4。
- 範例 2：`nums = [2, 3, 0, 1, 4]`，回傳 `2`：同樣是 0 → 1 → 4，中間的 0 被跳過。
- 範例 3（邊界）：`nums = [0]`，回傳 `0`，不需要跳。
- 範例 4：`nums = [1, 1, 1, 1]`，回傳 `3`，每次只能走一步。

### 思路

暴力解是 DP：`dp[j] = min(dp[i] + 1)`，對每個 i 更新它能跳到的所有 j，最差 O(n · max(nums))，n = 10⁴、跳躍長度 1000 時約 10⁷，可以接受但不優雅；BFS 把每個索引當節點，邊數同樣是 O(n · max)。瓶頸是逐一更新每條邊，而這些邊有結構。

關鍵觀察是把核心題 1 的前綴性質推進一步：**最少跳 k 次能到的位置形成一段連續區間**，而且這些區間依 k 由左往右排列。理由：令 `f_k` 是「至多 k 跳能到的最遠位置」，由核心題 1 的論證，至多 k 跳能到的位置正好是前綴 `[0, f_k]`，所以「恰好需要 k 跳」的位置就是 `(f_{k-1}, f_k]`。而 `f_{k+1} = max(i + nums[i] for i <= f_k)`，因為第 k + 1 跳的起點必須是至多 k 跳能到的位置。於是我們只要從左往右掃，記住「這一層的右端」`cur_end` 和「下一層的右端」`farthest`；掃到 `cur_end` 時代表這一層用完，跳躍數加一，進入下一層。

這個貪婪常被描述成「每次跳到能讓下一步跳最遠的位置」，它的正確性是 stays ahead：任何走法在 k 跳之後的位置都 ≤ `f_k`（歸納：k − 1 跳後的位置 ≤ `f_{k-1}`，從那裡再跳一次最遠也只到 `max(i + nums[i] for i <= f_{k-1}) = f_k`）。所以第一個讓 `f_k >= n - 1` 的 k 就是最少跳躍數。相反地，兩種看似合理的貪婪都是錯的：「每次跳最遠」在範例 1 會 0 → 2 → 3 → 4 共 3 跳；「跳到 `nums[j]` 最大的落點」在 `[3, 3, 1, 2, 1, 1]` 會 0 → 1 → 3 → 5 共 3 跳，但 0 → 3 → 5 只要 2 跳，因為索引 3 的 `3 + 2 = 5` 比索引 1 的 `1 + 3 = 4` 更遠。該比較的是 `j + nums[j]`，不是 `nums[j]`。

```text
nums = [2, 3, 1, 1, 4, 2, 1, 3]，n - 1 = 7
index:     0  1  2  3  4  5  6  7
i+nums[i]: 2  4  3  4  8  7  7  ─

第 0 層：[0, 0]
第 1 層：(0, 2]   = {1, 2}       f1 = max(0+2) = 2
第 2 層：(2, 4]   = {3, 4}       f2 = max(1+3, 2+1) = 4
第 3 層：(4, 8]   ∋ 7            f3 = max(3+1, 4+4) = 8 >= 7

掃描過程（只掃到 n - 2 = 6）
i  i+nums[i]  farthest  cur_end  jumps  動作
0      2          2        0       0     i == cur_end → jumps = 1, cur_end = 2
1      4          4        2       1
2      3          4        2       1     i == cur_end → jumps = 2, cur_end = 4
3      4          4        4       2
4      8          8        4       2     i == cur_end → jumps = 3, cur_end = 8
5      7          8        8       3
6      7          8        8       3
結束：jumps = 3（例如 0 → 1 → 4 → 7）
```

每次 i 走到 `cur_end`，代表「這一層所有位置都看過了，下一層最遠能到 farthest」，於是跳躍數加一。迴圈只跑到 n − 2，因為站在 n − 1 時已經到了，不需要再跳；若跑到 n − 1，在 `i == cur_end == n - 1` 的情況（例如 `[1, 1]`）會多算一次。

### 解法

```python
import random
from collections import deque


def jump(nums: list[int]) -> int:
    jumps = cur_end = farthest = 0
    for i in range(len(nums) - 1):     # 不處理最後一格：到了就不用再跳
        farthest = max(farthest, i + nums[i])
        if i == cur_end:               # 這一層用完，必須再跳一次
            jumps += 1
            cur_end = farthest
            if cur_end >= len(nums) - 1:
                break
    return jumps


def brute(nums):
    n = len(nums)
    dist = [-1] * n
    dist[0] = 0
    q = deque([0])
    while q:
        i = q.popleft()
        for j in range(i + 1, min(n, i + nums[i] + 1)):
            if dist[j] < 0:
                dist[j] = dist[i] + 1
                q.append(j)
    return dist[-1]


assert jump([2, 3, 1, 1, 4]) == 2
assert jump([2, 3, 0, 1, 4]) == 2
assert jump([0]) == 0
assert jump([1, 1, 1, 1]) == 3
assert jump([3, 3, 1, 2, 1, 1]) == 2
assert jump([2, 3, 1, 1, 4, 2, 1, 3]) == 3
assert jump([1, 1]) == 1
for _ in range(500):
    n = random.randint(1, 10)
    arr = [random.randint(1, 4) for _ in range(n)]     # 全部 >= 1，保證可達
    assert jump(arr) == brute(arr)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)，空間 O(1)。邊界情況：n = 1 時迴圈不執行，回傳 0；`range(len(nums) - 1)` 確保不在終點多跳一次；`cur_end >= n - 1` 時提早結束只是常數優化；題目保證可達，所以不會出現「`i == cur_end` 但 `farthest == i`」的卡死情況，若不保證可達就要加檢查（F2）。這個演算法本質上是 BFS，只是因為每層是連續區間，所以不需要 queue。

### Follow-up

> [!question]- F1. 如果要回傳一條最少跳躍的路線呢？
> 在每一層掃描時，記下讓 `farthest` 達到最大的那個索引 `best`；層結束時把 `best` 加入路線。正確性：在保證可達的情況下，每一層的 farthest 一定嚴格變大，所以下一層的 `best` 落在 `(cur_end, farthest]`，而這段區間正是上一層 `best` 一跳能到的範圍，路線一定合法。時間仍是 O(n)。
> ```python
> def jump_path(nums):
>     n, path = len(nums), [0]
>     cur_end = farthest = best = 0
>     for i in range(n - 1):
>         if i + nums[i] > farthest:
>             farthest, best = i + nums[i], i
>         if i == cur_end:
>             if best != path[-1]:
>                 path.append(best)
>             cur_end = farthest
>             if cur_end >= n - 1:
>                 break
>     if path[-1] != n - 1:
>         path.append(n - 1)
>     return path                    # [2, 3, 1, 1, 4] → [0, 1, 4]
> ```

> [!question]- F2. 如果不保證能到達，到不了要回傳 -1 呢？
> 在 `i == cur_end` 時檢查 `farthest <= i`：成立代表這一層的所有位置都無法把邊界往右推，終點不可達，回傳 -1。另外 `i > cur_end` 不會發生，因為我們在 `cur_end` 處就會先判斷。時間仍 O(n)。這個檢查就是 20.6 節「沒處理推不動」的那一項，也是難題 5（1326）一定要加的判斷。

> [!question]- F3. 如果每次跳躍的成本不同（例如從 i 跳到 j 的成本是 `cost[j]`），要最小化總成本呢？
> 「最少次數」的層次結構不再有用，因為少跳一次不代表成本較低。這是最短路問題，但因為只能往右跳，圖是 DAG，不論成本正負都可以依索引順序做 DP：`dp[j] = cost[j] + min(dp[i])`，其中 i 是能跳到 j 的位置；若跳躍範圍是固定的視窗（1 到 k 步），用 monotonic deque 維護視窗最小值，O(n)；若每個位置的跳躍範圍不同，能跳到 j 的 i 不是一段連續區間，可以用 segment tree 做區間最小值，或直接 Dijkstra（第 18 章），O(E log n)。

> [!question]- F4. 這題和「用最少的區間覆蓋 [0, n]」有什麼關係？
> 完全相同。把位置 i 看成區間 `[i, i + nums[i]]`，「最少跳躍」就是「從 0 開始，用最少的區間一段接一段覆蓋到 n − 1」，這正是 20.3 節骨架 B 的 `min_cover`。難題 5（1326. Minimum Number of Taps）和 1024 Video Stitching 都是先把輸入轉成這種區間，再套本題的層次掃描。面試時看出這個對應，就能直接重用同一段程式。

> [!question]- F5. 如果要回傳到達每個位置的最少跳躍數呢？
> 由於「最少 k 跳的位置」是連續區間 `(f_{k-1}, f_k]`，最少跳躍數對索引是非遞減的。同一次掃描中，每當進入新的一層就把這一層的區間填上 k，整個陣列一次 O(n) 就算完，不需要 BFS 的 queue，也不需要 O(n · max) 的 DP。這個性質（距離對索引單調）也解釋了為什麼本題的貪婪成立：BFS 的層剛好是索引的連續分段。

## 核心題 3｜134. Gas Station｜Medium

### 題目

環狀道路上有 n 個加油站，編號 0 到 n − 1。在站 i 可以加 `gas[i]` 公升油，從站 i 開到下一站 `(i + 1) % n` 要消耗 `cost[i]` 公升。車子油箱沒有上限，一開始是空的，從某一站出發（出發時先加那一站的油）。如果能順時針繞一圈回到出發站，回傳出發站的編號，否則回傳 -1。題目保證如果有解，解是唯一的。限制：`1 <= n <= 10⁵`，`0 <= gas[i], cost[i] <= 10⁴`。

- 範例 1：`gas = [1, 2, 3, 4, 5]`、`cost = [3, 4, 5, 1, 2]`，回傳 `3`。從站 3 出發：加 4 開到站 4 剩 3，加 5 開到站 0 剩 6，加 1 開到站 1 剩 4，加 2 開到站 2 剩 2，加 3 開回站 3 剩 0。
- 範例 2：`gas = [2, 3, 4]`、`cost = [3, 4, 3]`，回傳 `-1`。總油量 9 小於總消耗 10，不可能繞完。
- 範例 3（邊界）：`gas = [5]`、`cost = [4]`，回傳 `0`；`gas = [3]`、`cost = [4]`，回傳 `-1`。
- 範例 4：`gas = [4, 1, 3, 3]`、`cost = [1, 7, 1, 1]`，回傳 `2`。注意淨油量 `gas - cost` 最大的是站 0（+3），但從站 0 出發在第二段就會沒油。

### 思路

令 `diff[i] = gas[i] - cost[i]`，代表經過站 i 這一段的淨油量。暴力解是對每個起點模擬一圈，看油量是否始終非負，O(n²)，n = 10⁵ 時太慢。瓶頸在於每次失敗後，我們從下一個起點重新開始，重複計算了大量相同的區段。

第一個關鍵觀察（失敗可以整段跳過）：如果從 s 出發，第一次油量變負是在走完站 j 那一段之後，那麼 s 到 j 之間的任何站 k 當起點，也一定在 j 或更早失敗。理由：從 s 開到 k 時，油量是 `diff[s] + … + diff[k-1]`，因為 j 之前都沒失敗，這個值 ≥ 0。從 k 出發等於「到達 k 時油箱是空的」，比從 s 一路開來到 k 時的油量少（或相同），在同樣的路段上只會更早沒油。所以失敗後可以直接把起點設成 j + 1，不必一一嘗試 s + 1 … j。

第二個關鍵觀察（總和決定有沒有解）：如果 `sum(diff) >= 0`，一次掃描結束時留下的起點 s 一定可行。用前綴和來看最清楚：令 `P[k] = diff[0] + … + diff[k-1]`，從 s 出發到達 k 時的油量是 `P[k] - P[s]`（k > s）或 `P[n] - P[s] + P[k]`（繞過尾端，k ≤ s）。貪婪每次在油量變負時重設起點，代表 `P[j+1] < P[s]`，也就是 P 創下新低；所以最後的 s 是 P 在 `[0, n)` 的最小值位置。最小值位置出發時，第一種油量 `P[k] - P[s] >= 0`，第二種 `P[n] + (P[k] - P[s]) >= 0`（因為總和 `P[n] >= 0`），整圈都不會沒油。這把「為什麼對」講成了一句話：**從前綴和最低點的下一步出發，之後永遠不會比出發時更低**。

```text
範例 1：gas = [1, 2, 3, 4, 5]，cost = [3, 4, 5, 1, 2]
站 i:        0    1    2    3    4
diff:       -2   -2   -2   +3   +3      總和 = 0 >= 0，有解
前綴 P[i]:   0   -2   -4   -6   -3   (P[5] = 0)
                             ↑ 最低點 P[3] = -6 → 從站 3 出發

貪婪掃描
i  diff  tank（加完）  動作
0   -2      -2         < 0 → start = 1，tank = 0
1   -2      -2         < 0 → start = 2，tank = 0
2   -2      -2         < 0 → start = 3，tank = 0
3   +3       3
4   +3       6
結束：total = 0 >= 0 → 回傳 start = 3

範例 4：diff = [+3, -6, +2, +2]，總和 = +1
i  diff  tank  動作
0   +3     3
1   -6    -3   < 0 → start = 2，tank = 0   （從 0 或 1 出發都會在這裡失敗）
2   +2     2
3   +2     4
結束：回傳 2
```

範例 4 顯示「從淨油量最多的站出發」這種直覺貪婪是錯的：站 0 的 +3 抵不過下一段的 −6。正確的貪婪看的不是單一站，而是累積的前綴和。

### 解法

```python
import random


def can_complete_circuit(gas: list[int], cost: list[int]) -> int:
    total = tank = start = 0
    for i, (g, c) in enumerate(zip(gas, cost)):
        total += g - c
        tank += g - c
        if tank < 0:                   # 從 start 到 i 之間任何一站出發都會失敗
            start, tank = i + 1, 0
    return start if total >= 0 else -1


def brute(gas, cost):
    n = len(gas)
    for s in range(n):
        tank = 0
        for k in range(n):
            i = (s + k) % n
            tank += gas[i] - cost[i]
            if tank < 0:
                break
        else:
            return s
    return -1


assert can_complete_circuit([1, 2, 3, 4, 5], [3, 4, 5, 1, 2]) == 3
assert can_complete_circuit([2, 3, 4], [3, 4, 3]) == -1
assert can_complete_circuit([5], [4]) == 0
assert can_complete_circuit([3], [4]) == -1
assert can_complete_circuit([4, 1, 3, 3], [1, 7, 1, 1]) == 2
assert can_complete_circuit([0, 0], [0, 0]) == 0       # 全部為 0：任何站都可以，回傳 0
for _ in range(1000):
    n = random.randint(1, 7)
    g = [random.randint(0, 6) for _ in range(n)]
    c = [random.randint(0, 6) for _ in range(n)]
    b = brute(g, c)
    got = can_complete_circuit(g, c)
    if b == -1:
        assert got == -1
    else:                                               # 有多解時，貪婪回傳的也必須可行
        assert brute(g[got:] + g[:got], c[got:] + c[:got]) == 0
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：一次掃描。空間 O(1)。邊界情況：n = 1 時只看 `gas[0] >= cost[0]`；總和小於 0 時直接回傳 -1，不管 start 是多少；`start` 可能在最後一輪被設成 n（例如最後一段讓 tank 變負），但這時總和必定小於 0（因為 P[n] 創新低代表 `P[n] < P[0] = 0`），所以不會回傳越界的 n；油量為 0 剛好到站是允許的，所以條件是 `tank < 0` 而不是 `<= 0`。隨機測試中允許多解，是因為「保證唯一」是題目的前提，而貪婪在多解時回傳的是前綴和第一個最低點，仍然可行。

### Follow-up

> [!question]- F1. 如果不保證唯一，要回傳所有可行的起點呢？
> 從 s 出發可行的條件是：對所有 k > s 有 `P[k] >= P[s]`，且對所有 k < s 有 `P[k] + total >= P[s]`（繞過尾端的那些位置）。先算前綴和 P，再算後綴最小值 `suf[s] = min(P[s..n])` 和前綴最小值 `pre[s] = min(P[0..s-1])`，起點 s 可行若且唯若 `P[s] <= suf[s]` 且 `P[s] <= pre[s] + total`。兩次掃描，O(n) 時間、O(n) 空間。當 total = 0 時，第二個條件等價於「P[s] 是全域最小值」，所以可行起點就是所有最低點的位置。

> [!question]- F2. 如果油箱有容量上限 C 呢？
> 「總和 ≥ 0 就有解」不再成立：`gas = [10, 0]`、`cost = [5, 5]`、C = 5 時總和是 0，但從站 0 出發只能裝 5 公升，開到站 1 剩 0，站 1 沒油可加，下一段就失敗；從站 1 出發一開始就沒油。不過第一個觀察仍然成立：每一段的油量更新是 `min(tank + gas, C) - cost`，它對「到達時的油量」單調不減，所以到達 k 時有油永遠不比空箱差，失敗後仍可整段跳過。做法是在兩倍長度的環上模擬：從 s 開始走，若在第 s + k 段失敗就把起點設成 s + k + 1，若走滿 n 段就回傳 s，起點超過 n − 1 就回傳 -1。每個位置最多被走過兩次，O(n)。

> [!question]- F3. 如果可以選擇順時針或逆時針開呢？
> 兩個方向分別處理即可。逆時針時從站 i 開到站 i − 1，消耗的是連接兩站那段路的成本，在原題的定義下是 `cost[i - 1]`。把陣列重新排成逆時針的順序（站的油量序列反轉，路段成本對應地平移一格），再呼叫同一個函式，最後把回傳的索引換回原本的編號。兩次 O(n) 掃描，總共 O(n)。

> [!question]- F4. 如果 gas 和 cost 會被修改，每次修改後都要回答起點呢？
> 用 segment tree 維護 `diff` 的區間，每個節點存兩個值：區間總和 `sum`、區間內的最小前綴和 `min_prefix`，以及它出現的位置。合併左右子區間時，`min_prefix = min(左.min_prefix, 左.sum + 右.min_prefix)`。根節點的 sum 就是 total，最小前綴和的位置 + 1 就是起點（若位置是 n − 1，起點回到 0）。每次修改 O(log n)，查詢 O(1)。這是把本題「前綴和最低點」的觀察直接資料結構化。

> [!question]- F5. 如果起點固定，問出發時至少要額外帶多少油呢？
> 沿著環從起點 s 模擬一圈，記錄每段路走完後油量的最小值 m，答案是 `max(0, -m)`，O(n)。若要對每個起點都回答，用前綴和 P：從 s 出發，走完沒繞過尾端的路段後油量是 `P[t] - P[s]`（t = s+1..n），繞過尾端後是 `total + P[t] - P[s]`（t = 1..s）。所以最低油量是 `min(min(P[s+1..n]), total + min(P[1..s])) - P[s]`，先算出前綴最小值與後綴最小值，每個起點 O(1)，總共 O(n)。答案為 0 的起點，正好就是 F1 中的可行起點。

## 核心題 4｜763. Partition Labels｜Medium

### 題目

給一個只含小寫英文字母的字串 s，把它切成**盡可能多**的連續片段，使得每個字母最多只出現在一個片段中（同一個字母的所有出現位置都在同一段）。依序回傳每個片段的長度。限制：`1 <= len(s) <= 500`。

- 範例 1：`s = "ababcbacadefegdehijhklij"`，回傳 `[9, 7, 8]`，片段是 `"ababcbaca"`、`"defegde"`、`"hijhklij"`。
- 範例 2：`s = "eccbbbbdec"`，回傳 `[10]`。第一個 e 和倒數第二個字元 e 把幾乎整個字串綁在一起，最後的 c 又和前面的 c 相連。
- 範例 3（邊界）：`s = "a"`，回傳 `[1]`；`s = "abc"`，回傳 `[1, 1, 1]`，所有字母都不重複時每個字元自成一段。

### 思路

暴力解是嘗試所有切法（2ⁿ⁻¹ 種），或對每個可能的切點檢查「左邊出現的字母右邊都沒有」，每個切點 O(n)，總共 O(n²)。這題的 n 只有 500，O(n²) 也能過，但它背後的結構才是重點。

關鍵觀察：**一個切法合法，若且唯若它的每一刀都合法**，而「在位置 i 之後切一刀」是否合法，只看 `s[0..i]` 中所有字母的最後出現位置是否都 ≤ i，和其他刀切在哪裡無關。所以合法切點的集合是固定的，每一個合法切點都可以同時使用，用上全部合法切點就是最多段。這是 20.4 節的「下界加構造」：任何合法分法的段數不超過「合法切點數 + 1」，而貪婪剛好用上每一個合法切點。

找合法切點的方法：先記錄每個字母的最後出現位置 `last[c]`。從左往右掃，維護 `end = max(last[s[0..i]])`，也就是目前這一段「至少要延伸到哪裡」。當 `i == end` 時，代表 `s[0..i]` 中所有字母都不會再出現在 i 之後，這是一個合法切點，切下這一段並從 i + 1 開始新的一段。反過來，`i < end` 時一定不能切，因為某個已出現的字母還會在 end 處出現。

```text
s = "ababcbacadefegdehijhklij"
last: a=8 b=5 c=7 d=14 e=15 f=11 g=13 h=19 i=22 j=23 k=20 l=21

i:    0 1 2 3 4 5 6 7 8 | 9 10 11 12 13 14 15 | 16 17 18 19 20 21 22 23
s:    a b a b c b a c a | d e  f  e  g  d  e  | h  i  j  h  k  l  i  j
end:  8 8 8 8 8 8 8 8 8 | 14 15 15 15 15 15 15 | 19 22 23 23 23 23 23 23
                      ↑ i == end → 切              ↑ i == end → 切                    ↑ 切
片段長度：9 | 7 | 8

i = 0 讀到 a，a 最後在 8，所以這段至少到 8；
中間讀到的 b（最後在 5）、c（最後在 7）都沒有超過 8，end 不變；
i = 8 時 i == end，切。
```

第二段從 d 開始：d 最後在 14，讀到 e 時 end 被推到 15，之後的 f、g 都在 15 之內，於是在 15 切。每一段的 end 只會往右推，不會縮回，所以一次掃描就夠了。

### 解法

```python
import random


def partition_labels(s: str) -> list[int]:
    last = {c: i for i, c in enumerate(s)}      # 每個字母最後出現的位置
    sizes, start, end = [], 0, 0
    for i, c in enumerate(s):
        end = max(end, last[c])                 # 這一段至少要延伸到 end
        if i == end:                            # s[start..i] 的字母都不會再出現
            sizes.append(i - start + 1)
            start = i + 1
    return sizes


def brute(s):
    n = len(s)
    valid = [i for i in range(n - 1)
             if not set(s[:i + 1]) & set(s[i + 1:])]   # 在 i 之後切一刀是否合法
    cuts = [-1] + valid + [n - 1]
    return [b - a for a, b in zip(cuts, cuts[1:])]


assert partition_labels("ababcbacadefegdehijhklij") == [9, 7, 8]
assert partition_labels("eccbbbbdec") == [10]
assert partition_labels("a") == [1]
assert partition_labels("abc") == [1, 1, 1]
assert partition_labels("abca") == [4]
assert partition_labels("aabbcc") == [2, 2, 2]
for _ in range(500):
    t = "".join(random.choice("abcd") for _ in range(random.randint(1, 12)))
    assert partition_labels(t) == brute(t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：建 `last` 一次、掃描一次。空間 O(Σ)，Σ 是字母種類數，本題是 26，可以視為 O(1)。邊界情況：長度 1 時回傳 `[1]`；整個字串首尾是同一個字母時只有一段；全部字母不同時每個字元一段；字元集很大（Unicode 或任意整數）時演算法不變，`last` 用 dict 即可，空間變成 O(不同字元數)。

貪婪會失敗的變形：1520. Maximum Number of Non-Overlapping Substrings 不要求片段蓋滿整個字串，而是要挑出最多個互不重疊的子字串，每個子字串都要包含其中每個字母的所有出現位置。這時「從左往右，能切就切」不再正確：`s = "adefaddaccc"` 中，從左邊開始的 a 把 `"adefadda"` 綁成一段，貪婪得到 `"adefadda"`、`"ccc"` 兩個；但最佳解是 `"e"`、`"f"`、`"ccc"` 三個，因為不必蓋滿，選短的子字串能留下更多空間（見 F1）。

### Follow-up

> [!question]- F1. 如果不必蓋滿整個字串，而是挑出最多個互不重疊、且各自包含其字母所有出現位置的子字串（1520）呢？
> 先對每個字母 c 算出「封閉區間」：從 `[first[c], last[c]]` 開始，掃描區間內的字母，若某個字母的 first 或 last 超出區間就把區間擴大，直到穩定；若擴大過程中某個字母的 first 在原本的 first[c] 左邊，這個區間就不是以 c 開頭的最小候選，可以丟掉。得到最多 26 個候選區間後，問題變成 20.3 節骨架 A 的「最多不重疊區間」：依右端排序，能選就選。每個候選區間的計算 O(n)，總共 O(26 · n)。例子 `"adefaddaccc"` 的候選是 `[0, 7]`（a 與 d 互相綁住）、`[2, 2]`（e）、`[3, 3]`（f）、`[8, 10]`（c），依右端選出 e、f、ccc 三個。

> [!question]- F2. 如果規定最多只能切成 k 段，要讓最長的那段盡量短呢？
> 合法切點集合 C 仍然固定，現在只能從中挑最多 k − 1 個。這是第 8 章難題 2（410）的結構：二分答案 X，檢查時從左往右，每次跳到「離目前起點 X 以內最遠的合法切點」，看需要幾段是否 ≤ k。合法切點已排序，可以用 `bisect` 找最遠切點，每次檢查 O(k log n) 或 O(n)，總共 O(n log n)。若要求恰好 k 段，只要 `len(C) + 1 >= k` 就能做到（任選 k − 1 個合法切點）。

> [!question]- F3. 如果字串是串流，不能先掃一遍算出 last 呢？
> 沒有 last 就不知道一段何時能結束，但可以用「合併區間」的方式在線維護目前的分段：用一個 stack 存目前的片段 `[start, end]`，以及每個字母第一次出現的位置。讀到位置 i 的字母 c，若 c 出現過，就把 stack 頂端所有 `end >= first[c]` 的片段彈出，和 i 合併成一段 `[那些片段中最小的 start, i]`；若 c 沒出現過，就推入新的片段 `[i, i]`。每個片段最多被推入、彈出各一次，均攤 O(1)。串流結束時，stack 中的片段就是答案；中途只能回報「目前的暫定分段」，因為未來的字母可能把它們合併。

> [!question]- F4. 同樣的「切點彼此獨立」論證還能解哪一題？
> 768. Max Chunks To Make Sorted II：把陣列切成最多塊，使得每塊各自排序後串起來等於整個陣列排序的結果。在 i 之後切一刀合法，若且唯若 `max(arr[0..i]) <= min(arr[i+1..])`，而且整個切法合法若且唯若每一刀都合法，所以答案就是合法切點數加一。先算後綴最小值，再從左往右維護前綴最大值，O(n) 時間、O(n) 空間（也可以用 monotonic stack 做到一次掃描，第 10 章）。這兩題的共同點是：一旦證明「切法合法 ⇔ 每刀合法」，貪婪就只是把所有合法切點找出來。

> [!question]- F5. 一共有多少種合法的分法（不要求最多段）？
> 因為每一刀的合法性互不影響，任何合法切點的子集合都對應一個合法分法，而且不同子集合對應不同分法。若貪婪切出 p 段，合法切點有 p − 1 個，所以合法分法共有 2^(p−1) 種，O(n) 算出 p 後直接得到答案（題目要求取模時用快速冪）。這個問題是檢查你是否真的理解「切點獨立」的好方法：如果切點之間會互相影響，就必須改用 DP 計數。

## 核心題 5｜846. Hand of Straights｜Medium

### 題目

給一個整數陣列 `hand` 代表手上的牌，以及整數 `groupSize`（以下記為 W）。請判斷能否把所有牌分成若干組，每組恰好 W 張，而且每組的牌是 W 個連續的整數（例如 W = 3 時 `[2, 3, 4]` 是一組）。限制：`1 <= len(hand) <= 10⁴`，`0 <= hand[i] <= 10⁹`，`1 <= W <= len(hand)`。

- 範例 1：`hand = [1, 2, 3, 6, 2, 3, 4, 7, 8]`、`W = 3`，回傳 `True`：`[1, 2, 3]`、`[2, 3, 4]`、`[6, 7, 8]`。
- 範例 2：`hand = [1, 2, 3, 4, 5]`、`W = 4`，回傳 `False`，5 張牌不能分成每組 4 張。
- 範例 3：`hand = [1, 1, 2, 2, 3, 3]`、`W = 3`，回傳 `True`，兩組 `[1, 2, 3]`。
- 範例 4（邊界）：`W = 1` 時永遠是 `True`；`hand = [1, 2, 4, 5]`、`W = 2` 回傳 `True`，但 `hand = [1, 3]`、`W = 2` 回傳 `False`。

### 思路

暴力解是 backtracking：每次挑一張牌當某組的起點，嘗試所有可能，指數級。即使用記憶化，狀態是「每種牌還剩幾張」，仍然太大。瓶頸在於我們把「哪張牌當起點」當成需要猜的選擇。

關鍵觀察：**目前最小的那張牌 x，只有一種用法**。它一定屬於某一組；那一組的最小值不可能比 x 小（手上已經沒有更小的牌），所以那一組只能是 `[x, x+1, …, x+W−1]`。這是一個被迫的選擇，不需要交換論證：任何合法分法都必須包含這一組，所以我們直接拿走它，剩下的牌形成一個規模更小的同類問題，再看新的最小牌。如果某一張需要的牌不夠，就證明了無解。

實作上不必一組一組拿。用 `Counter` 記每個值的張數，依值由小到大處理：若 x 還剩 c 張，這 c 張全都只能當起點（理由同上），所以一次開 c 組，把 x 到 x + W − 1 每個值都扣掉 c 張；任何一個值不夠扣就回傳 False。另一個要先檢查的前提是 `len(hand) % W == 0`。

反過來，「隨便挑一張牌當起點」的貪婪是錯的：`hand = [1, 2, 3, 4, 5, 6]`、W = 3，若先拿 `[2, 3, 4]`，剩下 `{1, 5, 6}` 無法成組，但正確答案是 `[1, 2, 3]`、`[4, 5, 6]`。從最小值（或對稱地，從最大值）出發之所以對，正是因為只有極端值的用法是被迫的。

```text
hand = [1, 2, 3, 6, 2, 3, 4, 7, 8]，W = 3
計數：  值:   1  2  3  4  6  7  8
       張數: 1  2  2  1  1  1  1

處理 x = 1（剩 1 張）：開 1 組 [1,2,3]
       張數: 0  1  1  1  1  1  1
處理 x = 2（剩 1 張）：開 1 組 [2,3,4]
       張數: 0  0  0  0  1  1  1
處理 x = 3、4：已經是 0，跳過
處理 x = 6（剩 1 張）：開 1 組 [6,7,8]
       張數: 0  0  0  0  0  0  0      → True

反例：hand = [1, 2, 2, 3, 3, 5]，W = 3
處理 x = 1：開 [1,2,3]，剩 {2:1, 3:1, 5:1}
處理 x = 2：需要 2, 3, 4，但 4 有 0 張 → False
```

每次處理的 x 是「目前最小的非零值」，因為我們依排序後的值走，而比 x 小的值都已經扣成 0。

### 解法

```python
import random
from collections import Counter


def is_n_straight_hand(hand: list[int], W: int) -> bool:
    if len(hand) % W:
        return False
    count = Counter(hand)
    for x in sorted(count):
        c = count[x]
        if c == 0:
            continue
        for v in range(x, x + W):      # 最小的 x 只能當起點：一次開 c 組
            if count[v] < c:
                return False
            count[v] -= c
    return True


def brute(hand, W):
    if not hand:
        return True
    if len(hand) % W:
        return False
    rest = sorted(hand)
    for start in set(rest):            # 嘗試每一種起點（不假設最小值）
        r = rest[:]
        ok = True
        for v in range(start, start + W):
            if v in r:
                r.remove(v)
            else:
                ok = False
                break
        if ok and brute(r, W):
            return True
    return False


assert is_n_straight_hand([1, 2, 3, 6, 2, 3, 4, 7, 8], 3) is True
assert is_n_straight_hand([1, 2, 3, 4, 5], 4) is False
assert is_n_straight_hand([1, 1, 2, 2, 3, 3], 3) is True
assert is_n_straight_hand([5, 9, 7], 1) is True
assert is_n_straight_hand([1, 2, 4, 5], 2) is True
assert is_n_straight_hand([1, 3], 2) is False
assert is_n_straight_hand([1, 2, 2, 3, 3, 5], 3) is False
assert is_n_straight_hand([10**9 - 1, 10**9], 2) is True
for _ in range(400):
    h = [random.randint(1, 6) for _ in range(random.randint(1, 8))]
    w = random.randint(1, 4)
    assert is_n_straight_hand(h, w) == brute(h, w)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n log n)：排序不同的值 O(D log D)，D ≤ n；內層迴圈只在 `c > 0` 時執行，而每次執行至少開一組、扣掉 W 張牌，所以內層總共最多執行 n / W 次，每次 W 步，合計 O(n)。空間 O(D)。邊界情況：`n % W != 0` 先回傳 False；W = 1 時每張牌自成一組；值可以到 10⁹，`range(x, x + W)` 中不存在的值在 `Counter` 中讀到 0，自然觸發 False（讀取不存在的鍵不會把它加入 Counter，而且 `sorted(count)` 在迴圈開始前就已經固定）；重複的牌靠「一次開 c 組」處理，不需要一張一張拿。

### Follow-up

> [!question]- F1. 如果每組不必恰好 W 張，而是長度至少 3 的連續整數（659. Split Array into Consecutive Subsequences，輸入已排序）呢？
> 「最小值被迫」仍然成立，但被迫的只有「它要接在某組後面或開新組」，長度不再固定。正確的貪婪是：處理 x 時，**優先接到一個以 x − 1 結尾的現有組**，沒有才開新組，而開新組時必須立刻拿走 x + 1 和 x + 2（否則這組長度不夠 3）。交換論證：如果最佳解讓 x 開新組而有一組停在 x − 1，把 x 開頭的那組整段接到 x − 1 那組後面，兩組的長度都仍 ≥ 3（或合併成一組），所以優先延長不會變差。用兩個 Counter（剩餘張數、以某值結尾的組數）實作，O(n)。

> [!question]- F2. 如果要輸出實際的分組呢？
> 演算法不變，在「開 c 組」時把 c 個 `list(range(x, x + W))` 加入答案即可。總輸出大小是 n，時間 O(n log n)。若要求每組以原陣列中的索引表示，就為每個值維護一個索引的 queue，開組時從每個值的 queue 各取一個索引。

> [!question]- F3. 如果牌是以 (值, 張數) 的形式給出，張數可達 10⁹，不能逐張展開呢？
> 原解法本來就是一次開 c 組，但內層迴圈要看 W 個值，W 很大時（例如 10⁵）會變慢。改用「開組事件」：依值排序後掃描，維護一個 deque 記錄 `(開組的起點, 組數)` 和目前「仍需要牌」的組數 `active`。處理值 v：若 v 和前一個值不相鄰而 `active > 0`，代表有組斷掉，回傳 False；若 v 的張數 < active，回傳 False；否則多出來的 `張數 - active` 張都要在 v 開新組，加入 deque；最後把起點等於 v − W + 1 的那批組（它們在 v 收尾）移出 deque 並從 active 扣掉。結束時 active 必須為 0。時間 O(D log D)，與 W 和張數無關。

> [!question]- F4. 「最小元素的用法被迫」這個論證還能解哪些題？
> 2007. Find Original Array From Doubled Array：給一個由原陣列和「每個元素乘 2」混在一起的陣列，還原原陣列。排序後最小的 x 不可能是別人的兩倍（沒有更小的數了），所以它一定是原陣列的元素，它的配對 2x 必須存在，拿走兩者再看下一個最小值。0 要特別處理（0 的兩倍還是 0，張數必須是偶數）。954. Array of Doubled Pairs 允許負數，負數的「兩倍」更小，所以改成依絕對值排序，論證不變。兩題都是 O(n log n)。

> [!question]- F5. 如果牌非常多（例如 10⁷ 張）但值域很小（0 到 10⁶），能不能不排序？
> 可以做到 O(n + V)，V 是值域大小。用長度 V 的陣列計數取代 `Counter` 與排序，然後由小到大掃過每個值 v，同時維護「在 v 之前 W − 1 個值內開的組數總和」`active`（這些組都還需要一張 v）。若 `cnt[v] < active` 就回傳 False；否則在 v 開 `opened[v] = cnt[v] - active` 組，`active` 加上它，再減掉 `opened[v - W + 1]`（那批組在 v 收尾）。掃完後 `active` 必須為 0。這和 F3 是同一個想法，只是用陣列代替 deque，每個值 O(1)。

## 難題 1｜135. Candy｜Hard

### 題目

n 個孩子站成一排，第 i 個孩子的評分是 `ratings[i]`。你要發糖果，規則是：每個孩子至少一顆；如果一個孩子的評分**嚴格高於**相鄰的孩子，他拿到的糖果必須比那個鄰居多。請回傳最少需要的糖果總數。評分相同的鄰居之間沒有限制。限制：`1 <= n <= 2 × 10⁴`，`0 <= ratings[i] <= 2 × 10⁴`。

- 範例 1：`ratings = [1, 0, 2]`，回傳 `5`，分配 `[2, 1, 2]`。
- 範例 2：`ratings = [1, 2, 2]`，回傳 `4`，分配 `[1, 2, 1]`；第三個孩子和第二個評分相同，可以只拿 1 顆。
- 範例 3：`ratings = [1, 3, 2, 2, 1]`，回傳 `7`，分配 `[1, 2, 1, 2, 1]`。
- 範例 4（邊界）：`ratings = [5]`，回傳 `1`；`ratings = [4, 3, 2, 1]`，回傳 `10`，分配 `[4, 3, 2, 1]`。

### 提示

> [!tip]- 提示 1
> 每個孩子受到兩個方向的約束：和左鄰比、和右鄰比。如果只有「左鄰」這一種約束，最少的分配長什麼樣子？

> [!tip]- 提示 2
> 只看左約束時，從左往右掃：比左鄰高就是左鄰加一，否則給 1。只看右約束時，從右往左做同樣的事。這兩個陣列分別是各自約束下的「最小可能值」。

> [!tip]- 提示 3
> 任何合法分配在每個位置都至少是兩者的最大值；而逐點取最大值本身就同時滿足兩種約束。所以答案是 `sum(max(L[i], R[i]))`。

### 詳解

**為什麼直覺做法不夠**。最直覺的做法是從左往右掃一次：比左鄰高就給左鄰加一，否則給 1。這在遞增序列上是對的，但在遞減序列 `[4, 3, 2, 1]` 上每個人都拿 1 顆，違反了「比右鄰高要拿更多」。修補的方式是「發現違規就往回調整」，但一段長遞減序列的最後一個人被調整後，前面整段都可能要連鎖調整，最差 O(n²)。另一個想法是依評分由小到大處理，每個人拿「比他低的鄰居中最多的那個 + 1」，這是對的（評分低的人先定好，高的人只依賴已經定好的值），但要排序，O(n log n)。

**突破點：把兩個方向的約束拆開**。約束分成兩類：左約束「若 `r[i] > r[i-1]` 則 `c[i] > c[i-1]`」和右約束「若 `r[i] > r[i+1]` 則 `c[i] > c[i+1]`」。只考慮左約束時，最小的分配是 `L[i] = L[i-1] + 1`（若 `r[i] > r[i-1]`）否則 `L[i] = 1`；歸納可知任何滿足左約束的分配 c 都有 `c[i] >= L[i]`：遞增段的每一步都至少加一，而段的起點至少是 1。同理從右往左得到 R，任何滿足右約束的分配都有 `c[i] >= R[i]`。所以任何合法分配都有 `c[i] >= max(L[i], R[i])`，這是一個下界。

**下界可以達到**。令 `M[i] = max(L[i], R[i])`，證明 M 本身合法。看左約束：若 `r[i] > r[i-1]`，則 `L[i] = L[i-1] + 1`；而 `r[i-1] < r[i]` 代表 i − 1 沒有對 i 的右約束，所以 `R[i-1] = 1`，於是 `M[i-1] = max(L[i-1], 1) = L[i-1] < L[i] <= M[i]`，成立。右約束對稱。所以 M 是合法分配，而且逐點等於下界，總和最小。這是 20.4 節的「下界加構造」：兩趟掃描只是分別算出兩個方向的下界。

```text
ratings = [1, 2, 87, 87, 87, 2, 1]
index:      0  1   2   3   4  5  6

左→右 L：比左鄰高就 +1，否則 1
L:          1  2   3   1   1  1  1
右→左 R：比右鄰高就 +1，否則 1
R:          1  1   1   1   3  2  1
max(L, R):  1  2   3   1   3  2  1     總和 = 13

逐段解讀：
[1, 2, 87]   遞增，L 負責：1, 2, 3
[87, 87, 87] 相同評分之間沒有約束，中間的 87 可以只拿 1
[87, 2, 1]   遞減，R 負責：3, 2, 1
```

中間那個 87 只拿 1 顆，看起來很奇怪，但它和兩個鄰居的評分相同，題目沒有要求它要比誰多；而兩端的 87 各自比 2 高，所以分別由 L 和 R 推高。這個例子同時展示了為什麼一定要取 max：位置 2 的 L = 3 而 R = 1，位置 4 的 L = 1 而 R = 3，只做任一趟都會漏掉一邊。

**O(1) 空間的做法**。也可以一次掃描，把序列看成「上坡、下坡」：上坡長度為 k 時，坡上的人依序拿 1, 2, …, k + 1；下坡同理。唯一的難點是山頂同時屬於上坡和下坡，它要拿兩者中較大的。實作時記錄目前上坡長度 `up`、下坡長度 `down`、以及剛結束的上坡高度 `peak`：每往下走一步，下坡上的每個人都要多拿一顆，等於總數加上 `down`（再加上新來的那個人的 1 顆）；當 `down` 超過 `peak` 時，山頂也要跟著加一。這個寫法容易出錯，面試中先寫兩趟掃描，再口頭說明可以優化到 O(1) 空間即可。

### 解法

```python
import random


def candy(ratings: list[int]) -> int:
    n = len(ratings)
    left, right = [1] * n, [1] * n
    for i in range(1, n):                      # 左約束的最小解
        if ratings[i] > ratings[i - 1]:
            left[i] = left[i - 1] + 1
    for i in range(n - 2, -1, -1):             # 右約束的最小解
        if ratings[i] > ratings[i + 1]:
            right[i] = right[i + 1] + 1
    return sum(max(a, b) for a, b in zip(left, right))


def candy_constant_space(ratings: list[int]) -> int:
    total, up, down, peak = 1, 0, 0, 0
    for i in range(1, len(ratings)):
        if ratings[i] > ratings[i - 1]:        # 上坡：新的人拿 up + 1
            up += 1
            peak, down = up, 0
            total += up + 1
        elif ratings[i] == ratings[i - 1]:     # 平地：重新開始
            up = down = peak = 0
            total += 1
        else:                                  # 下坡：整段下坡每人多一顆
            up = 0
            down += 1
            total += down + 1 - (1 if peak >= down else 0)   # 山頂夠高就不用再加
    return total


def brute(ratings):
    n = len(ratings)
    c = [1] * n
    changed = True
    while changed:                             # 反覆修正直到沒有違規：最小不動點
        changed = False
        for i in range(n):
            for j in (i - 1, i + 1):
                if 0 <= j < n and ratings[i] > ratings[j] and c[i] <= c[j]:
                    c[i] = c[j] + 1
                    changed = True
    return sum(c)


assert candy([1, 0, 2]) == 5
assert candy([1, 2, 2]) == 4
assert candy([1, 3, 2, 2, 1]) == 7
assert candy([5]) == 1
assert candy([4, 3, 2, 1]) == 10
assert candy([1, 2, 87, 87, 87, 2, 1]) == 13
assert candy([1, 2, 3, 1]) == 7                # 山頂 3 個人的上坡、1 個人的下坡
for _ in range(1000):
    r = [random.randint(0, 4) for _ in range(random.randint(1, 10))]
    assert candy(r) == candy_constant_space(r) == brute(r)
print("all tests passed")
```

### 複雜度與邊界

兩趟掃描：時間 O(n)，空間 O(n)。坡道版本：時間 O(n)，空間 O(1)。邊界情況：n = 1 時回傳 1；評分全相同時每人 1 顆，總數 n；嚴格遞增或遞減時總數是 n(n + 1)/2；相同評分的鄰居沒有約束，這是最容易誤解的地方（很多人以為相同評分要拿相同糖果，那是 F3 的變形）。坡道版本中，`peak >= down` 的判斷是用來決定山頂是否需要加高：下坡長度還沒超過上坡時，山頂原本的高度已經夠了。

### Follow-up

> [!question]- F1. 如果孩子圍成一圈（第一個和最後一個也相鄰）呢？
> 找出評分最小的孩子 m（有多個時任選一個），他不比任何鄰居高，所以在最佳解中一定只拿 1 顆，也不會把約束傳過他。把環從 m 剪開，排成 `r[m], r[m+1], …, r[m-1], r[m]`（m 在頭尾各出現一次），對這個長度 n + 1 的序列做兩趟掃描，加總前 n 個位置的 max(L, R)。兩個 m 的位置 L 與 R 都是 1，所以複製不會產生矛盾。時間 O(n)。如果沒有最小值這個「斷點」，環上的約束就可能互相傳遞，正是因為最小值一定存在，環形版本才能化成線性。

> [!question]- F2. 如果孩子站在二維網格上，和上下左右四個鄰居比呢？
> 兩趟掃描無法推廣，因為約束不再只有兩個方向。但「最少糖果 = 1 + 從這個孩子出發、評分嚴格遞減的最長路徑長度」仍然成立：約束圖是一個 DAG（評分嚴格遞減的邊不可能形成環），每個點的最小值是它在 DAG 中往下走的最長路徑長度加一。用記憶化 DFS 或依評分排序後依序計算，O(mn) 或 O(mn log(mn))。這正是第 16 章難題 2（329. Longest Increasing Path in a Matrix）的結構。

> [!question]- F3. 如果規則改成「評分相同的鄰居必須拿相同數量」呢？
> 把相鄰且評分相同的孩子壓縮成一個區塊，區塊內每個人拿一樣多。區塊之間的約束和原題相同，所以對壓縮後的序列做兩趟掃描，每個區塊的值乘上區塊大小再加總即可。正確性：區塊內強制相等之後，一個區塊對左鄰區塊和右鄰區塊的約束仍然只有兩個方向，L 與 R 的下界論證完全不變。時間 O(n)。

> [!question]- F4. 為什麼「依評分由小到大，每人拿比他低的鄰居中的最大值加一」也是對的？它和兩趟掃描有什麼關係？
> 這是一般化的做法：約束圖是 DAG，依評分由小到大處理就是一種拓撲排序，每個點在處理時，它需要比較的鄰居（評分更低的）都已經定好，給它「那些鄰居的最大值加一」就是它能拿的最小值。正確性和 F2 相同，時間 O(n log n)。兩趟掃描是把這個想法特化到一維：一維時，最長的遞減路徑只可能一路往左或一路往右，所以 L 與 R 分別就是兩個方向的最長路徑，取 max 就是最長路徑。面試時說出這層關係，代表你理解兩趟掃描背後的結構，而不只是背了技巧。

### 心得

關鍵突破是「把雙向約束拆成兩個單向約束，各自的最小解逐點取最大值」，而它之所以正確，是下界加構造：任何合法解都不小於 max(L, R)，而 max(L, R) 本身合法。和本章的關係：這是 20.3 節骨架 D 的代表題，也是第 5 章難題 1（42. Trapping Rain Water）同一類「左右各掃一趟」的結構。面試時先講單趟掃描為什麼在遞減序列上失敗，再提出兩趟掃描，然後用一句話說出「下界可以達到」的證明（遞增時 i − 1 的 R 一定是 1）。O(1) 空間的坡道寫法可以作為 follow-up 口頭說明。

## 難題 2｜330. Patching Array｜Hard

### 題目

給一個由小到大排序的正整數陣列 `nums` 和一個整數 n。你可以往陣列中「補」任意正整數。請回傳最少需要補幾個數，才能讓 `[1, n]` 中的每一個整數都能表示成陣列中某些元素的和（每個元素最多用一次）。限制：`1 <= len(nums) <= 1000`，`1 <= nums[i] <= 10⁴`，`1 <= n <= 2³¹ − 1`。

- 範例 1：`nums = [1, 3]`、`n = 6`，回傳 `1`。原本能湊出 1、3、4，補一個 2 之後能湊出 1 到 6。
- 範例 2：`nums = [1, 5, 10]`、`n = 20`，回傳 `2`，補 2 和 4。
- 範例 3：`nums = [1, 2, 2]`、`n = 5`，回傳 `0`，1 到 5 都已經湊得出來。
- 範例 4（邊界）：`nums = []`（本題的變形允許空陣列）、`n = 7`，回傳 `3`，補 1、2、4；`n = 8` 時要再補 8，回傳 `4`。

### 提示

> [!tip]- 提示 1
> 假設目前已經能湊出 `[1, miss)` 中的每一個數，而 miss 本身湊不出來。加入一個數 x 之後，能湊出的範圍會變成什麼？x 要滿足什麼條件，範圍才會連續？

> [!tip]- 提示 2
> 若 x ≤ miss，範圍變成 `[1, miss + x)`；若 x > miss，miss 仍然湊不出來，而且之後的數都更大，永遠幫不上忙，所以一定要補一個 ≤ miss 的數。

> [!tip]- 提示 3
> 要補的話，補 miss 本身讓範圍變成 `[1, 2·miss)`，是所有可補的數中推得最遠的。依序處理 nums：`nums[i] <= miss` 就吸收（`miss += nums[i]`），否則補 miss（`miss *= 2`），直到 miss > n。

### 詳解

**為什麼直覺做法不夠**。暴力解是嘗試所有補法：補 k 個數，每個數在 `[1, n]` 中任選，再檢查子集合和是否覆蓋 `[1, n]`。光是檢查覆蓋就要做 subset sum，O(len · n)，n 可達 2³¹，完全不可行。即使想到「缺什麼補什麼」，也很容易選錯要補的值：補最小缺的那個數 miss 是對的，但為什麼不是補別的？需要一個能說服面試官的理由。

**突破點：覆蓋範圍可以用一個邊界描述**。維持 invariant：「目前用過的數（已處理的 nums 加上補的數）能湊出 `[1, miss)` 的每一個整數」。一開始什麼都沒有，miss = 1。若下一個數 x ≤ miss，原本能湊出的每個 v ∈ `[1, miss)` 加上 x 得到 `[x, miss + x)`，再加上 x 本身與原本的範圍，因為 x ≤ miss，兩段 `[1, miss)` 和 `[x, miss + x)` 相接沒有縫隙，新的範圍是 `[1, miss + x)`。若 x > miss，miss 湊不出來：要湊出 miss，只能用 ≤ miss 的數，而 nums 剩下的數都 ≥ x > miss，所以必須補一個 ≤ miss 的數。補 p ≤ miss 讓範圍變成 `[1, miss + p)`，p 越大越好，所以補 miss 本身。

**為什麼補 miss 是最佳的（交換論證）**。先換個角度描述覆蓋：一個多重集合 T 能湊出 `[1, n]` 的每個數，若且唯若對每個 v ∈ `[1, n]`，T 中所有 ≤ v 的元素總和 `S_T(v) >= v`。必要性很直觀，因為湊 v 只能用 ≤ v 的元素；充分性來自上一段的「x ≤ miss 就能接上」。現在拿任意一個最佳補法 P，假設它和貪婪在前面的補法相同，而貪婪接下來要補 m（此時所有 ≤ m 的 nums 都已經被吸收，加上共同的補數總和恰好是 m − 1）。因為 P 也要湊出 m，`S(m) >= m`，所以 P 一定還有一個額外的補數 p ≤ m。把 p 換成 m：對 v ≥ m，`S(v)` 只增加 m − p ≥ 0；對 v < m，共同的部分已經能湊出 `[1, m)`，`S(v) >= v` 不受影響。換完之後 P 仍合法、大小不變，而且和貪婪多一個相同的補數。重複下去，P 變成貪婪的補法，所以貪婪的補數個數最少。

```text
nums = [1, 5, 10]，n = 20

步驟  miss  下一個 nums  動作                     新的範圍
 1     1        1        1 <= 1，吸收              [1, 2)
 2     2        5        5 > 2，補 2（patch 1）     [1, 4)
 3     4        5        5 > 4，補 4（patch 2）     [1, 8)
 4     8        5        5 <= 8，吸收               [1, 13)
 5    13       10        10 <= 13，吸收             [1, 23)
結束：miss = 23 > 20，共補 2 個

範圍的成長：
吸收 x：  [1 ........ miss) + x  →  [1 ........ miss + x)
補 miss： [1 ........ miss)      →  [1 ................ 2·miss)
```

第 2 步時 miss = 2，但下一個數是 5：不論之後怎麼組合，都湊不出 2（只有 1 和 ≥ 5 的數），所以一定要補。補 2 讓範圍變成 `[1, 4)`；若補 1，範圍只到 `[1, 3)`，之後還要再補。第 4 步範圍是 `[1, 8)`，5 ≤ 8 可以吸收，範圍一口氣擴大到 `[1, 13)`。

### 解法

```python
import random
from itertools import combinations_with_replacement


def min_patches(nums: list[int], n: int) -> int:
    miss, i, patches = 1, 0, 0                 # invariant：[1, miss) 都湊得出來
    while miss <= n:
        if i < len(nums) and nums[i] <= miss:
            miss += nums[i]                    # 吸收：範圍變成 [1, miss + nums[i])
            i += 1
        else:
            miss += miss                       # 補 miss：範圍變成 [1, 2·miss)
            patches += 1
    return patches


def covers(values, n):
    reach = 1                                  # bitmask：第 v 位為 1 代表 v 湊得出來
    for v in values:
        reach |= reach << v
    full = (1 << (n + 1)) - 1
    return reach & full == full


def brute(nums, n):
    for k in range(n + 1):
        for extra in combinations_with_replacement(range(1, n + 1), k):
            if covers(list(nums) + list(extra), n):
                return k


assert min_patches([1, 3], 6) == 1
assert min_patches([1, 5, 10], 20) == 2
assert min_patches([1, 2, 2], 5) == 0
assert min_patches([], 7) == 3
assert min_patches([], 8) == 4
assert min_patches([2], 1) == 1                # 2 幫不上 1
assert min_patches([1, 2, 31, 33], 2**31 - 1) == 28
for _ in range(200):
    arr = sorted(random.randint(1, 8) for _ in range(random.randint(0, 4)))
    t = random.randint(1, 12)
    assert min_patches(arr, t) == brute(arr, t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(len(nums) + log n)：每一輪不是吸收一個 nums 元素，就是讓 miss 翻倍，而 miss 翻倍最多 log₂ n ≈ 31 次。空間 O(1)。邊界情況：nums 為空時只會補 1、2、4、…，答案是 ⌊log₂ n⌋ + 1；nums 的第一個數大於 1 時一開始就要補 1；nums 中比 n 大的數不會被吸收也無害；miss 可能超過 2³¹ − 1（例如 miss 為 2³⁰ 時再翻倍），Python 沒問題，但在 Java／C++ 中 miss 必須用 64 位元整數，否則溢位後變成負數，迴圈永遠不會結束。

貪婪會失敗的變形：如果目標不是「`[1, n]` 的每一個數」，而是某幾個特定的數，補 miss 就不再最佳。例如 nums 為空、只要求湊出 5：補 miss 的貪婪會補 1、2、4 共 3 個，但直接補 5 只要 1 個。本題的貪婪完全依賴「前綴必須連續」這個結構：只有當 miss 一定要被湊出來時，補 miss 才是被迫而且最划算的選擇。

### Follow-up

> [!question]- F1. 如果要回傳實際補了哪些數呢？
> 在 `else` 分支中把當下的 miss 加入結果串列即可，補的數就是 miss 在補之前的值，它們形成一個嚴格遞增的序列，每個至少是前一個的兩倍。時間與空間都是 O(len(nums) + log n)。以範例 2 為例，回傳 `[2, 4]`。

> [!question]- F2. 如果不能補數，而是問陣列（未排序）最多能湊出從 0 開始多少個連續的數（1798. Maximum Number of Consecutive Values You Can Make）呢？
> 先排序，再用同樣的 invariant：`miss` 從 1 開始，依序吸收 `x <= miss` 的數；遇到第一個 x > miss 就停，因為之後的數都更大，miss 永遠湊不出來。答案是 miss（包含 0 的話，能湊出 `0..miss-1` 共 miss 個值）。時間 O(n log n)。這題是本題「只吸收、不補」的版本，排序是必要的，因為未排序時一個大數可能要等小數補齊範圍後才能被吸收。

> [!question]- F3. 如果每個數最多可以用 c 次（或無限次）呢？
> 若 x ≤ miss，x 的第一個複本讓範圍變成 `[1, miss + x)`，此時 x ≤ miss + x 仍成立，第二個複本也能吸收，依此類推，所以 c 個複本一起吸收：`miss += c · x`。補數時仍補 miss。若可以無限次使用，只要陣列中有 1（或補一個 1），任何正整數都湊得出來，答案是 0 或 1；這說明本題的難點完全來自「每個元素最多用一次」，它讓覆蓋範圍的成長受限於元素總和。

> [!question]- F4. 2952. Minimum Number of Coins to be Added 和這題是什麼關係？
> 幾乎相同：給一組未排序的硬幣和 target，最少要加幾枚硬幣，才能讓 `[1, target]` 中每個值都能用硬幣的子集合湊出。先排序，然後完全套用本題的程式。時間 O(m log m + log target)。面試中遇到這種「換了故事」的題目，關鍵是認出「覆蓋前綴 `[1, miss)`」這個 invariant，以及「補 miss 是推得最遠的」這個論證。

> [!question]- F5. 如果要求 [1, n] 之間的數能用「至多 k 個元素」的和湊出呢？
> 加了元素個數的限制後，「`S(v) >= v` 就能湊出」不再成立，因為湊 v 可能需要超過 k 個小元素，覆蓋範圍也不再只用一個邊界描述，補 miss 的貪婪就失效了。例如 k = 1 時每個數都只能單獨出現，必須補上 `[1, n]` 中所有不在陣列裡的數，答案是 n 減去陣列中落在 `[1, n]` 的不同值個數。一般的 k 需要搜尋或 DP。這個對比可以用來說明本題的貪婪依賴哪個結構。

### 心得

關鍵突破是 invariant「`[1, miss)` 都湊得出來」：它把指數大小的子集合和資訊壓成一個數字，而且讓「下一步該補什麼」變成被迫的選擇（一定要補 ≤ miss 的數，補 miss 推得最遠）。和本章的關係：它是 20.3 節骨架 B「邊界推進」的數值版本，和核心題 1、2 的 reach 是同一個想法；證明用的是交換論證，把任何最佳解中的某個補數換成 miss。面試時先說 invariant，再說兩種情況（吸收或補），最後用 `S_T(v) >= v` 的刻畫或「p 越大範圍越大」說明為什麼補 miss，最後主動提到 Java 的溢位。

## 難題 3｜630. Course Schedule III｜Hard

### 題目

有 n 門線上課程，第 i 門是 `courses[i] = [duration, lastDay]`：上這門課需要連續 `duration` 天，而且必須在第 `lastDay` 天結束時（含）完成。你從第 1 天開始，一次只能上一門課，一門上完才能上下一門，課與課之間可以沒有空檔。請回傳最多能完成幾門課。限制：`1 <= n <= 10⁴`，`1 <= duration, lastDay <= 10⁴`。

- 範例 1：`courses = [[100, 200], [200, 1300], [1000, 1250], [2000, 3200]]`，回傳 `3`。依序上第 1 門（第 1–100 天）、第 3 門（第 101–1100 天）、第 2 門（第 1101–1300 天），第 4 門需要到第 3300 天，趕不上。
- 範例 2：`courses = [[5, 5], [4, 6], [2, 6]]`，回傳 `2`。選 `[4, 6]` 和 `[2, 6]`（第 1–4 天、第 5–6 天）；若先選了 `[5, 5]`，之後兩門都趕不上。
- 範例 3（邊界）：`courses = [[1, 2]]`，回傳 `1`；`courses = [[3, 2], [4, 3]]`，回傳 `0`，每門課本身就比期限長。

### 提示

> [!tip]- 提示 1
> 先回答一個比較簡單的問題：如果已經決定要上哪些課，應該用什麼順序上，才最有可能全部趕上？

> [!tip]- 提示 2
> 固定一組課時，依 lastDay 由早到晚上是最好的順序（交換相鄰兩門順序顛倒的課不會變差）。所以依 lastDay 排序，逐一考慮要不要加入。加入後若總天數超過這門課的 lastDay，該怎麼辦？

> [!tip]- 提示 3
> 超過時，從目前選的課中（包含剛加入的）丟掉 duration 最長的那一門。課數不變，但總天數最小，給後面的課留最多空間。用 max-heap 維護目前選的課的 duration。

### 詳解

**為什麼直覺做法不夠**。暴力解是列舉所有子集合，檢查能否排進去，O(2ⁿ · n)。DP 的狀態是「考慮了前 i 門（依 lastDay 排序）、目前用了 t 天時最多幾門」，O(n · maxDay) = 10⁸，在 Python 中太慢。直覺的貪婪也都不對：依 lastDay 排序、能上就上（不後悔），在範例 2 會先選 `[5, 5]`，之後 `[4, 6]` 和 `[2, 6]` 都上不了，只得到 1 門；依 duration 由短到長、按這個順序依序上課，在 `[[2, 2], [1, 3]]` 會先上 `[1, 3]`（第 1 天），再上 `[2, 2]` 要到第 3 天，超過期限，只得到 1 門，但依期限的順序兩門都趕得上。

**第一步：固定一組課，依期限排序上課最好**。這是一個交換論證：若某個排程中有相鄰的兩門課 a、b，a 在前但 `lastDay(a) > lastDay(b)`，把它們對調。對調後 b 提早結束，一定趕得上；a 現在的結束時間等於原本 b 的結束時間，而原本 b 趕得上，`lastDay(a) > lastDay(b)` 又更寬鬆，所以 a 也趕得上。反覆對調消除所有逆序，就得到依 lastDay 排序的排程。結論：一組課可行若且唯若「依 lastDay 排序後，每門的累積天數都 ≤ 它的 lastDay」。

**第二步：依期限處理，超過就丟最長的**。依 lastDay 排序後逐一處理，維護目前選的課（max-heap 存 duration）與總天數 `total`。加入課程 c 後若 `total <= lastDay(c)`，c 排在最後仍趕得上，保留；否則丟掉 heap 中 duration 最長的那門（可能就是 c）。丟掉後的集合仍然可行：被移除的課之後，所有課都提早結束；c 的結束時間是新的 total，它 ≤ 加入 c 之前的 total，而加入 c 之前的 total ≤ 前一門的 lastDay ≤ `lastDay(c)`。

**為什麼這是最多的（invariant）**。令 H 是處理完前 i 門課後 heap 中的集合，證明更強的性質：對前 i 門中任何可行的子集合 S，有 `|S| <= |H|`，而且 S 的總天數 ≥ H 中最短的 |S| 門課的天數總和。歸納時分兩種情況。若 c 可以直接加入：S 不含 c 時由歸納假設直接成立；S 含 c 時，`S − {c}` 的總天數 ≥ H 中最短的 |S| − 1 門，加上 c 的天數，恰好 ≥ 新 H 中某 |S| 門的總和。若 c 加入後超過期限、丟掉最長的 m：S 若含 c 且 `|S| = |H| + 1`，則 S 的總天數 ≥ `total(H) + duration(c)` > `lastDay(c)`，S 不可行，所以 `|S| <= |H|`；S 含 c 且 `|S| <= |H|` 時，`S − {c}` 的總天數 ≥ H 中最短的 |S| − 1 門（它們不包含被丟掉的最長那門），再加上 c，正是新 H 中某 |S| 門的總和；S 不含 c 時，新 H 是把最長的 m 換成不更長的 c，「最短的 j 門」的總和只會變小，不等式繼續成立。這個 invariant 保證 heap 的大小始終是最多課數，而且總天數盡可能小，給未來的課留最多空間。

```text
範例 2：courses = [[5, 5], [4, 6], [2, 6]]，依 lastDay 排序後順序不變

課程      加入後 heap     total  lastDay  動作
[5, 5]   {5}              5       5      5 <= 5，保留
[4, 6]   {5, 4}           9       6      9 > 6 → 丟最長的 5，total = 4，heap {4}
[2, 6]   {4, 2}           6       6      6 <= 6，保留
結束：heap 大小 2

範例 1：依 lastDay 排序 → [100,200] [1000,1250] [200,1300] [2000,3200]
課程          heap                 total  lastDay  動作
[100, 200]   {100}                 100     200     保留
[1000,1250]  {1000, 100}           1100    1250    保留
[200, 1300]  {1000, 200, 100}      1300    1300    保留
[2000,3200]  {2000,1000,200,100}   3300    3200    超過 → 丟 2000，total = 1300
結束：heap 大小 3
```

範例 2 的關鍵是第二步：`[5, 5]` 已經選了，但加入 `[4, 6]` 時超過期限。丟掉 5 天的那門而不是 4 天的這門，課數仍是 1，但總天數從 5 降到 4，正是這 1 天讓 `[2, 6]` 趕得上。這就是「後悔」：當初選 `[5, 5]` 是合理的，但出現了更短的替代品時，換掉它對未來更有利。

### 解法

```python
import heapq
import random
from itertools import combinations


def schedule_course(courses: list[list[int]]) -> int:
    taken, total = [], 0                       # taken 是 max-heap（存負數）
    for duration, last_day in sorted(courses, key=lambda c: c[1]):
        heapq.heappush(taken, -duration)
        total += duration
        if total > last_day:                   # 超過期限：丟掉最長的一門（可能是剛加入的）
            total += heapq.heappop(taken)
    return len(taken)


def feasible(subset):
    t = 0
    for d, last in sorted(subset, key=lambda c: c[1]):
        t += d
        if t > last:
            return False
    return True


def brute(courses):
    for k in range(len(courses), 0, -1):
        if any(feasible(s) for s in combinations(courses, k)):
            return k
    return 0


assert schedule_course([[100, 200], [200, 1300], [1000, 1250], [2000, 3200]]) == 3
assert schedule_course([[5, 5], [4, 6], [2, 6]]) == 2
assert schedule_course([[1, 2]]) == 1
assert schedule_course([[3, 2], [4, 3]]) == 0
assert schedule_course([[2, 2], [1, 3]]) == 2
assert schedule_course([[1, 10**4]] * 5) == 5
for _ in range(500):
    cs = [[random.randint(1, 6), random.randint(1, 12)] for _ in range(random.randint(1, 7))]
    assert schedule_course(cs) == brute(cs)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n log n)：排序一次，每門課最多推入、彈出 heap 各一次。空間 O(n)。邊界情況：duration > lastDay 的課推入後一定超過期限，而它是 heap 中最長的之一（或被換成另一門同樣長或更長的），彈出後 total 不會比加入前大，所以不需要特判；期限相同的課之間順序不影響結果；每次最多只需要彈出一個，因為加入一門課之前 total 已經合法，彈出最長的那門（≥ 剛加入的 duration）就能讓 total 回到不超過原本的值；總天數最多 10⁸，Python 沒問題，在 Java 中 `int` 也足夠，但習慣上用 `long` 更安全。

### Follow-up

> [!question]- F1. 如果每門課有不同的學分，要最大化總學分呢？
> 貪婪失效：丟掉最長的課可能丟掉學分最高的課，「數量最多」與「學分最多」不再一致。例如 `[3, 3]` 值 10 分，`[1, 3]` 和 `[1, 3]` 各 1 分，最多課數是 2（共 2 分），但最高學分是只上 `[3, 3]` 的 10 分。正確做法是依 lastDay 排序後做 0/1 背包式的 DP：`dp[t]` = 恰好在第 t 天結束時的最大學分，每門課從大到小更新 `dp[t] = max(dp[t], dp[t − d] + v)`（t ≤ lastDay），O(n · maxDay)。排序仍然必要，因為它保證每個子集合都只需要檢查依期限排序這一種順序。

> [!question]- F2. 如果要回傳要上哪些課，以及上課的順序呢？
> heap 中存 `(-duration, index)`，結束時 heap 裡的就是選中的課。上課順序依 lastDay 排序即可（第一步的交換論證保證這個順序可行），O(n log n)。要注意：最大課數的選法可能不唯一，這個演算法回傳的是「總天數最小」的那一組，面試時可以主動說明。

> [!question]- F3. 如果每門課還有最早開始日（release day），在那之前不能開始呢？
> 這是排程理論中的 1|r_j|ΣU_j 問題，在一般情況下是 strongly NP-hard，沒有已知的多項式演算法，排序加後悔的貪婪也不再正確，因為期限早的課可能還沒開放。面試中可以說明：小規模用 backtracking 或時間軸上的 DP；若所有課都只需要一天，就變成 F4 的 1353 題，有簡單的貪婪解。能指出「加了開始時間就變難」是很好的回答，不需要硬湊一個錯的貪婪。

> [!question]- F4. 如果每個活動只需要一天，但有可以參加的日期區間 [start, end]，最多能參加幾個（1353. Maximum Number of Events That Can Be Attended）呢？
> 依日期掃描：每一天把當天開放的活動的 end 推入 min-heap，丟掉已經過期的（end < 今天），然後參加 end 最早的那一個。交換論證：今天若參加了 end 較晚的活動 b 而不是 end 最早的 a，在最佳解中把今天換成 a、把 a 原本的日子（若有）換給 b，b 的期限更晚所以仍然合法。時間 O((n + D) log n)，D 是日期範圍；也可以只在有活動的日期之間跳躍，降到 O(n log n)。

> [!question]- F5. 如果所有課都必須上，要最小化最大延遲（完成時間超過 lastDay 的天數的最大值）呢？
> 依 lastDay 排序上課（Jackson's rule，earliest due date first）就是最佳的，證明正是第一步的相鄰交換：對調一對逆序的相鄰課程，不會讓兩者中較大的延遲變大。時間 O(n log n)。對比一下：「最小化最大延遲」只需要排序，「最大化準時完成的數量」需要排序加上後悔式 heap，「最大化準時完成的學分」需要 DP，三者是同一組資料在不同目標下的三種難度。

### 心得

關鍵突破是兩步：先用交換論證確定「固定一組課時依期限排序上課」，把問題變成「依期限掃描、決定選誰」；再用後悔式貪婪，超過期限時丟掉最長的課，維持「課數最多、總天數最少」的集合。和本章的關係：這是 20.3 節骨架 C 的代表題，和難題 4（871）的結構相同（都是先接受、超出時用 heap 退掉最不划算的），也和第 14 章難題 3（502. IPO）同屬「排序 + heap」。面試時建議先舉範例 2 說明「不後悔」的貪婪為什麼錯，再提出丟掉最長課的規則，最後說明 invariant：丟掉最長的課讓課數不變、總天數最小。

## 難題 4｜871. Minimum Number of Refueling Stops｜Hard

### 題目

一輛車從位置 0 往東開，目的地在位置 `target`。車子一開始有 `startFuel` 公升油，每開 1 單位距離消耗 1 公升，油箱容量無限。路上有若干加油站，`stations[i] = [position, fuel]`，依位置由小到大排列；車子到達加油站時可以選擇停下，把那個加油站的 `fuel` 公升油全部加進油箱。油剛好用完時到達加油站或目的地都算成功。請回傳到達目的地最少需要停幾次加油，到不了回傳 -1。限制：`1 <= target, startFuel <= 10⁹`，`0 <= len(stations) <= 500`，`1 <= position < target`，`1 <= fuel <= 10⁹`。

- 範例 1：`target = 1`、`startFuel = 1`、`stations = []`，回傳 `0`。
- 範例 2：`target = 100`、`startFuel = 1`、`stations = [[10, 100]]`，回傳 `-1`，連第一個加油站都到不了。
- 範例 3：`target = 100`、`startFuel = 10`、`stations = [[10, 60], [20, 30], [30, 30], [60, 40]]`，回傳 `2`：在位置 10 加 60 公升（可以開到 70），在位置 60 加 40 公升（可以開到 110）。
- 範例 4（邊界）：`target = 28`、`startFuel = 11`、`stations = [[2, 18], [4, 4]]`，回傳 `1`，只在位置 2 加 18 公升即可。

### 提示

> [!tip]- 提示 1
> 「要不要在這一站停」很難當下決定。換個角度：先一路開，等到油不夠開到下一個地方時，再「回頭決定」之前應該在哪一站停。這樣做為什麼合法？

> [!tip]- 提示 2
> 因為油箱無限大，在經過的任何一站加油，效果都等於「現在突然多了那麼多油」。所以油不夠時，可以從所有已經經過、還沒用過的站中挑一個。挑哪一個最好？

> [!tip]- 提示 3
> 挑油量最多的那一站。用 max-heap 存經過的加油站的油量：油不夠到下一個目標時，就彈出最大的加上去並計數一次；heap 空了還不夠就回傳 -1。

### 詳解

**為什麼直覺做法不夠**。暴力解是列舉所有停站的子集合，O(2ⁿ)。DP 可以做到 O(n²)：`dp[k]` = 停 k 次時最遠能開到哪裡，依序處理每個加油站 i，對 k 由大到小更新 `dp[k + 1] = max(dp[k + 1], dp[k] + fuel_i)`（前提是 `dp[k] >= position_i`）。n = 500 時 O(n²) 完全可以接受，面試中也是一個好答案。但直覺的貪婪很容易錯：「沒油時在最近經過的那站加」在範例 4 會在位置 11 卡住時選位置 4 的 4 公升，開到 15 還不夠，又要加 18 公升，共 2 次；「看到加油站就加」更不用說，會停很多次。

**突破點：把「當下決定」改成「事後補決定」**。因為油箱無限大，在位置 p 的加油站加 f 公升，和「之後任何時刻突然多出 f 公升」對能到達的範圍是一樣的，只要那個時刻車子已經經過 p。所以我們可以一路開到油用完的地方，再從所有經過的站中挑一個「假裝當初有停」。這把每一步的選擇從「要不要停」變成「從一堆候選中選一個」，而 heap 正好擅長這件事。

**為什麼選油量最多的（stays ahead 加交換論證）**。令 `R_k` 是貪婪停 k 次後能到的最遠位置。證明對任何停 k 次的合法方案 S，S 能到的最遠位置 ≤ `R_k`。歸納：S 的前 l − 1 次停站能到的最遠處 ≤ `R_{l-1}`，所以 S 的第 l 個停站位置 ≤ `R_{l-1}`，也就是說，S 的每一個停站都落在貪婪對應步驟的候選池中。接著是交換論證：貪婪第一步選的是候選池 `R_0` 內油量最多的站 g；若 S 沒有用 g，把 S 的第一個停站換成 g，油量只增不減，而且因為候選池是逐步擴大的（`R_0 ⊆ R_1 ⊆ …`），S 的其他停站仍然落在對應的池中；若 S 已經用了 g，就把它從 S 拿掉，剩下的問題是同樣結構的較小問題。由此得到貪婪 k 次的總油量 ≥ S 的總油量，`R_k = startFuel + 總油量`，所以 `R_k` 最遠。答案是第一個讓 `R_k >= target` 的 k。

```text
target = 100，startFuel = 10，stations = [[10,60], [20,30], [30,30], [60,40]]

reach = 10
  經過（position <= 10）：推入 60            heap {60}
  10 < 100，油不夠 → 彈出 60，reach = 70    stops = 1
reach = 70
  經過（position <= 70）：推入 30, 30, 40    heap {40, 30, 30}
  70 < 100，油不夠 → 彈出 40，reach = 110   stops = 2
reach = 110 >= 100，結束 → 2

位置:  0    10    20    30    40    50    60    70   ...  100  110
       |=====|                                               startFuel = 10
             |============== +60 ===============|            第 1 次：位置 10 的 60
                                                |== +40 ====|=====|  第 2 次：位置 60 的 40
```

注意第 2 次「停」在位置 60，但我們是在 reach = 70 時才決定的；因為車子確實經過了位置 60，這個決定是合法的。heap 中剩下的兩個 30 從來沒有用到，代表實際上不需要在那兩站停。

### 解法

```python
import heapq
import random
from itertools import combinations


def min_refuel_stops(target: int, start_fuel: int, stations: list[list[int]]) -> int:
    passed, reach, stops, i = [], start_fuel, 0, 0     # passed 是 max-heap（存負數）
    while reach < target:
        while i < len(stations) and stations[i][0] <= reach:
            heapq.heappush(passed, -stations[i][1])    # 經過的站都成為候選
            i += 1
        if not passed:                                 # 沒有任何候選能補油
            return -1
        reach -= heapq.heappop(passed)                 # 事後補決定：在油最多的那站停
        stops += 1
    return stops


def min_refuel_stops_dp(target, start_fuel, stations):
    dp = [start_fuel] + [0] * len(stations)            # dp[k]：停 k 次最遠到哪
    for i, (pos, fuel) in enumerate(stations):
        for k in range(i, -1, -1):
            if dp[k] >= pos:
                dp[k + 1] = max(dp[k + 1], dp[k] + fuel)
    return next((k for k, d in enumerate(dp) if d >= target), -1)


def brute(target, start_fuel, stations):
    for k in range(len(stations) + 1):
        for chosen in combinations(stations, k):
            fuel, pos, ok = start_fuel, 0, True
            for p, f in chosen:
                fuel -= p - pos
                if fuel < 0:
                    ok = False
                    break
                fuel, pos = fuel + f, p
            if ok and fuel >= target - pos:
                return k
    return -1


assert min_refuel_stops(1, 1, []) == 0
assert min_refuel_stops(100, 1, [[10, 100]]) == -1
assert min_refuel_stops(100, 10, [[10, 60], [20, 30], [30, 30], [60, 40]]) == 2
assert min_refuel_stops(28, 11, [[2, 18], [4, 4]]) == 1
assert min_refuel_stops(100, 50, [[25, 25], [50, 50]]) == 1      # 油剛好用完時到站
assert min_refuel_stops(10**9, 10**9, [[1, 1]]) == 0
for _ in range(500):
    n = random.randint(0, 5)
    pos = sorted(random.sample(range(1, 30), n))
    st = [[p, random.randint(1, 15)] for p in pos]
    t, s = random.randint(1, 40), random.randint(1, 15)
    st = [x for x in st if x[0] < t]
    assert min_refuel_stops(t, s, st) == min_refuel_stops_dp(t, s, st) == brute(t, s, st)
print("all tests passed")
```

### 複雜度與邊界

Heap 版本：時間 O(n log n)，每個加油站最多推入、彈出各一次；空間 O(n)。DP 版本：時間 O(n²)，空間 O(n)。邊界情況：`startFuel >= target` 時不進迴圈，回傳 0；沒有加油站或第一站就到不了時，heap 為空回傳 -1；油剛好用完時到站算成功，所以條件是 `position <= reach`；燃料總量可達 500 × 10⁹，Python 不溢位，Java／C++ 要用 64 位元整數。

### Follow-up

> [!question]- F1. 如果油箱容量有上限 C 呢？
> 「事後補決定」的前提消失了：在位置 p 加油時，油箱可能裝不下那個站的全部油量，而且能裝多少取決於當時的油量，所以「之後突然多出 f 公升」不再等價。貪婪不再正確，要改用 DP，狀態多一維「在每個站時的油量」，或用 Dijkstra／BFS 在（站, 油量）的狀態空間上搜尋，油量範圍很大時需要離散化。面試中能說出「無限油箱是讓後悔式貪婪成立的關鍵」就是重點。

> [!question]- F2. 如果每個站的油價不同、可以加任意量，油箱容量 C，要最小化總花費呢？
> 這是另一個經典貪婪：在每一站，看 C 公升能開到的範圍內是否有比這站更便宜的站。有的話，只加剛好夠開到「第一個更便宜的站」的油；沒有的話，在這站加滿，然後開到範圍內最便宜的站。交換論證：任何在較貴的站多買的油，都可以改在之後較便宜的站買。用 monotonic stack（第 10 章）預先算出每站的「下一個更便宜的站」，總時間 O(n)；若範圍內沒有更便宜的站，要找範圍內最便宜的站，可以用 sparse table 或 heap，O(n log n)。

> [!question]- F3. 如果要回傳實際在哪些站停呢？
> heap 中存 `(-fuel, index)`，每次彈出時記錄 index。最後依 index（也就是位置）排序，就是實際停站的順序。正確性：由於每個被選中的站在被選中時已經「經過」，依位置排序後的實際行程一定合法（每一站都在前面累積的可達範圍內）。時間 O(n log n)。

> [!question]- F4. 如果最多只能停 k 次，最遠能開到哪裡？
> 執行同樣的迴圈，但目標改成無限遠，停滿 k 次或 heap 空了就停下，回傳當時的 reach。根據詳解中的 stays ahead 論證，貪婪停 k 次的 `R_k` 就是所有停 k 次方案中最遠的。時間 O(n log n)。DP 版本的 `dp[k]` 也直接給出這個答案，而且一次得到所有 k 的結果。

> [!question]- F5. 為什麼面試時也值得提 DP 版本？
> 因為 DP 的正確性不依賴任何交換論證，容易說服自己和面試官，而且在 F1（有容量上限）這類變形中仍然可以擴充；而 heap 版本更快，但需要清楚解釋「事後補決定」為什麼合法。一個好的敘事是：先給 O(n²) 的 DP `dp[k]` = 停 k 次最遠距離，再觀察「`dp` 的每一步都是在可到的站中挑油最多的」，自然引出 heap 版本 O(n log n)。兩者互為驗證，本題的解法程式也正是這樣對拍的。

### 心得

關鍵突破是「油箱無限大，所以停不停可以事後決定」，把線上的抉擇變成「從經過的站中選油最多的」，這是後悔式貪婪最乾淨的例子。和本章的關係：和難題 3（630）同屬 20.3 節骨架 C，630 是超出限制時退掉最差的，這題是不夠時補上最好的；也和核心題 1、2 的邊界推進相通，`reach` 就是能到的最遠處。面試時先說 DP，再說「事後補決定」，最後用 stays ahead 說明為什麼選油最多的：任何方案的每個停站，都落在貪婪當時的候選池裡。

## 難題 5｜1326. Minimum Number of Taps to Open to Water a Garden｜Hard

### 題目

一個一維花園從位置 0 延伸到位置 n。在位置 0, 1, …, n 各有一個水龍頭，共 n + 1 個；第 i 個水龍頭打開後可以澆到區間 `[i − ranges[i], i + ranges[i]]`。請回傳最少要打開幾個水龍頭才能澆到整個花園 `[0, n]`，做不到回傳 -1。花園是連續的，所以兩個區間只要端點相接（例如 `[0, 2]` 和 `[2, 5]`）就算接上。限制：`1 <= n <= 10⁴`，`len(ranges) == n + 1`，`0 <= ranges[i] <= 100`。

- 範例 1：`n = 5`、`ranges = [3, 4, 1, 1, 0, 0]`，回傳 `1`。位置 1 的水龍頭澆到 `[-3, 5]`，已經涵蓋整個花園。
- 範例 2：`n = 3`、`ranges = [0, 0, 0, 0]`，回傳 `-1`，每個水龍頭都只澆到一個點。
- 範例 3：`n = 7`、`ranges = [1, 2, 1, 0, 2, 1, 0, 1]`，回傳 `3`：位置 1 澆 `[-1, 3]`、位置 4 澆 `[2, 6]`、位置 7 澆 `[6, 8]`。
- 範例 4（邊界）：`n = 8`、`ranges = [4, 0, 0, 0, 0, 0, 0, 0, 4]`，回傳 `2`，兩端的水龍頭在位置 4 相接；`ranges = [4, 0, 0, 0, 4, 0, 0, 0, 4]` 回傳 `1`，中間那個就夠了。

### 提示

> [!tip]- 提示 1
> 每個水龍頭就是一個區間。先把區間截到花園範圍 `[0, n]` 內，問題變成「用最少的區間覆蓋 `[0, n]`」。

> [!tip]- 提示 2
> 對每個左端點 l，只需要知道「從 l 出發最遠能澆到哪裡」：`max_reach[l] = max(右端點)`。這樣就變成核心題 2（45）的跳躍遊戲：站在 l 最遠可以跳到 `max_reach[l]`。

> [!tip]- 提示 3
> 套用 45 題的層次掃描：維護目前覆蓋的右端 `cur_end` 和候選中最遠的 `farthest`；掃到 `cur_end` 時就得再開一個水龍頭，若此時 `farthest` 沒有超過 `cur_end`，代表有一段澆不到，回傳 -1。

### 詳解

**為什麼直覺做法不夠**。暴力解是列舉水龍頭的子集合，O(2ⁿ⁺¹ · n)。DP 可以做：`dp[x]` = 覆蓋 `[0, x]` 的最少水龍頭數，每個區間 `[l, r]` 讓 `dp[r] = min(dp[r], min(dp[l..r]) + 1)`，直接算是 O(n · 區間長度)，n = 10⁴、半徑 100 時約 2 × 10⁶，可以接受。直覺的貪婪「先開澆得最廣的」是錯的：`n = 8`、`ranges = [0, 0, 2, 0, 3, 0, 2, 0, 0]`，最廣的是位置 4 的 `[1, 7]`，開了它之後兩端 `[0, 1]` 和 `[7, 8]` 還得各開一個，共 3 個；但位置 2 的 `[0, 4]` 加上位置 6 的 `[4, 8]` 只要 2 個。最廣的區間不一定在最佳解中，因為它可能覆蓋的是「本來就容易覆蓋的中間」。

**突破點：化成跳躍遊戲**。把第 i 個水龍頭截成 `[max(0, i − r), min(n, i + r)]`。用最少的區間覆蓋 `[0, n]`，等價於：從位置 0 出發，每次選一個左端 ≤ 目前覆蓋右端的區間，把右端推到它的右端點，問最少推幾次能到 n。同一個左端點的區間只需要保留右端最遠的，於是令 `max_reach[l] = max(右端點 for 左端點為 l 的區間)`，這個陣列就是 45 題的 `i + nums[i]`：站在 l，最遠可以跳到 `max_reach[l]`。之後完全套用核心題 2 的層次掃描。

**正確性（stays ahead）**。和 45 題相同：令 `f_k` 是開 k 個水龍頭時能從 0 連續覆蓋到的最遠位置，`f_{k+1} = max(max_reach[l] for l <= f_k)`，因為第 k + 1 個水龍頭必須和已覆蓋的部分相接（左端 ≤ `f_k`），否則中間會有縫隙。任何方案開 k 個之後的連續覆蓋範圍都不超過 `f_k`，所以第一個讓 `f_k >= n` 的 k 就是答案；若某一層 `f_{k+1} == f_k < n`，代表沒有任何區間能跨過 `f_k`，花園澆不完。

```text
n = 7，ranges = [1, 2, 1, 0, 2, 1, 0, 1]
水龍頭 i：     0      1      2      3      4      5      6      7
截斷後區間： [0,1]  [0,3]  [1,3]  [3,3]  [2,6]  [4,6]  [6,6]  [6,7]

max_reach[l]（左端點為 l 的最遠右端）：
l:           0  1  2  3  4  5  6  7
max_reach:   3  3  6  3  6  0  7  0      （沒有區間以 l 為左端時是 0）

層次掃描（只掃 x = 0 .. n-1）
x  max_reach[x]  farthest  cur_end  taps  動作
0       3            3        0       0    x == cur_end → taps = 1，cur_end = 3
1       3            3        3       1
2       6            6        3       1
3       3            6        3       1    x == cur_end → taps = 2，cur_end = 6
4       6            6        6       2
5       0            6        6       2
6       7            7        6       2    x == cur_end → taps = 3，cur_end = 7
結束：taps = 3（例如 [0,3]、[2,6]、[6,7]）
```

第一層從 0 出發，最遠能到 3（水龍頭 1）；第二層考慮所有左端 ≤ 3 的區間，最遠是 `[2, 6]`；第三層考慮左端 ≤ 6 的區間，`[6, 7]` 把覆蓋推到 7 = n。每一層都在「已經接上的區間」中挑右端最遠的，這正是 20.3 節骨架 B 的 `min_cover`，只是因為座標是 0 到 n 的整數，可以用陣列取代排序。

### 解法

```python
import random
from itertools import combinations


def min_taps(n: int, ranges: list[int]) -> int:
    max_reach = [0] * (n + 1)
    for i, r in enumerate(ranges):
        left, right = max(0, i - r), min(n, i + r)
        max_reach[left] = max(max_reach[left], right)
    taps = cur_end = farthest = 0
    for x in range(n):                         # 和 45 題一樣，不處理終點 n
        farthest = max(farthest, max_reach[x])
        if x == cur_end:                       # 目前覆蓋到 x 為止，必須再開一個
            if farthest <= x:                  # 沒有區間能跨過 x：澆不到
                return -1
            taps += 1
            cur_end = farthest
    return taps


def brute(n, ranges):
    taps = list(range(n + 1))
    for k in range(n + 2):
        for chosen in combinations(taps, k):
            covered = [False] * n              # covered[x]：線段 [x, x+1] 是否被澆到
            for i in chosen:
                for x in range(max(0, i - ranges[i]), min(n, i + ranges[i])):
                    covered[x] = True
            if all(covered):
                return k
    return -1


assert min_taps(5, [3, 4, 1, 1, 0, 0]) == 1
assert min_taps(3, [0, 0, 0, 0]) == -1
assert min_taps(7, [1, 2, 1, 0, 2, 1, 0, 1]) == 3
assert min_taps(8, [4, 0, 0, 0, 0, 0, 0, 0, 4]) == 2
assert min_taps(8, [4, 0, 0, 0, 4, 0, 0, 0, 4]) == 1
assert min_taps(8, [0, 0, 2, 0, 3, 0, 2, 0, 0]) == 2      # 先開最廣的會用 3 個
assert min_taps(1, [1, 0]) == 1
for _ in range(300):
    n = random.randint(1, 7)
    rs = [random.randint(0, 3) for _ in range(n + 1)]
    assert min_taps(n, rs) == brute(n, rs)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：建 `max_reach` 是 O(n)，層次掃描 O(n)。空間 O(n)。邊界情況：區間左端可能是負數、右端可能超過 n，先截斷到 `[0, n]`；`max_reach` 預設 0，對沒有區間以 x 為左端的位置不影響 max；「推不動」的判斷 `farthest <= x` 必須在 `x == cur_end` 時檢查，這是和 45 題（保證可達）唯一的差別；`range(n)` 不處理 x = n，因為覆蓋到 n 就結束了；所有 ranges 都是 0 時每個區間只是一個點，x = 0 時 farthest = 0 立即回傳 -1。

### Follow-up

> [!question]- F1. 1024. Video Stitching 和這題有什麼不同？
> 1024 給的是一堆影片片段 `[start, end]`，要用最少的片段拼出 `[0, time]`。結構完全相同，差別只在輸入已經是區間（不需要從半徑換算），而且片段可能超出 time，要截斷。把每個片段的左端記成 `max_reach[start] = max(…, end)`，再套同一個層次掃描，O(片段數 + time)。若 time 很大但片段數少，用 20.3 節骨架 B 的排序版本，O(m log m)。

> [!question]- F2. 如果花園長度到 10⁹，但只有 m 個水龍頭（座標稀疏）呢？
> 不能開長度 n 的陣列，改用排序：把每個水龍頭轉成截斷後的區間，依左端排序，用 20.3 節的 `min_cover`，每一輪把所有左端 ≤ covered 的區間掃過，取右端最大值推進。指標只往右走，排序後 O(m)，總共 O(m log m)，與 n 無關。座標是實數時也一樣，只要「端點相接算接上」的規則不變。

> [!question]- F3. 如果每個水龍頭打開有不同的成本，要最小化總成本呢？
> 最少個數的貪婪失效：兩個便宜的小水龍頭可能比一個昂貴的大水龍頭好。例如花園 `[0, 2]`，水龍頭 A 覆蓋 `[0, 2]` 成本 10，B 覆蓋 `[0, 1]`、C 覆蓋 `[1, 2]` 各成本 1，最少個數是 1（A），最小成本是 2（B + C）。改用 DP：`dp[x]` = 覆蓋 `[0, x]` 的最小成本，依右端排序處理區間 `[l, r]`，`dp[r] = min(dp[r], cost + min(dp[l..r]))`，區間最小值用 segment tree（第 26 章），O(m log n)；也可以建圖跑 Dijkstra（第 18 章）：點是位置，區間 `[l, r]` 是從 l 到 r 的邊，再加上從 x 到 x − 1 成本 0 的邊（往回退不花錢）。

> [!question]- F4. 如果花園是環形的（位置 n 接回位置 0）呢？
> 環沒有固定的起點，但最佳解一定包含某個覆蓋位置 0 的區間。一種做法是枚舉這個區間當起點，把環剪開成一條長度 n 的線段，再做一次線性的層次掃描，O(m · n)。更快的做法是 binary lifting（倍增）：先對每個區間算出「下一個能接上、右端最遠的區間」，建出跳 2^j 次的表，然後對每個起點用 O(log m) 次跳躍判斷最少幾次能繞一圈，總共 O(m log m)。這是面試中較少見但很好的延伸，能說出「先剪開成線段」的想法就足夠。

> [!question]- F5. 如果要回傳打開哪些水龍頭呢？
> 在建 `max_reach` 時同時記錄是哪個水龍頭提供了這個最遠右端：`who[l] = i`。層次掃描中，記住讓 `farthest` 達到最大的那個左端點 `best_l`，每當 `x == cur_end` 開新水龍頭時，把 `who[best_l]` 加入答案。這和核心題 2 F1 的路線還原是同一個技巧，時間 O(n)。

### 心得

關鍵突破是把「最少水龍頭」轉成「每個左端點最遠能到哪」，問題立刻變成核心題 2 的跳躍遊戲，證明也直接沿用 stays ahead：開 k 個水龍頭能連續覆蓋的最遠處，貪婪永遠不落後。和本章的關係：這是 20.3 節骨架 B 的完整應用，和 45、1024 是同一題的三種包裝；唯一新增的細節是「推不動就回傳 -1」。面試時先指出「先開最廣的」的反例，再說明截斷區間、建 `max_reach`、套層次掃描三個步驟；若面試官追問成本版本（F3），要能說出貪婪為什麼失效並轉成 DP 或最短路。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 排序後掃描：區間排程 | 最多不重疊、最少刪除、最少箭射破氣球 | 依右端排序，能選就選；證明用交換論證 | 20.3 節骨架 A、435（第 9 章核心題 3）、452、646 |
| 邊界推進／BFS 分層 | 能否到達、最少步數、最少區間覆蓋 | 維護 `reach` 或 `cur_end`／`farthest`；每層是連續區間 | 核心題 1（55）、核心題 2（45）、難題 5（1326）、1024 |
| 前綴和重設起點 | 環狀累加、失敗後前面的起點也失敗 | 前綴和最低點的下一步出發；`tank < 0` 就重設 | 核心題 3（134）、53 Maximum Subarray 的 Kadane 也是同一種重設 |
| 合法切點彼此獨立 | 切成最多段，每刀的合法性只看自己 | 證明「切法合法 ⇔ 每刀合法」，然後用上所有合法切點 | 核心題 4（763）、768、769 Max Chunks To Make Sorted |
| 被迫選擇 | 最小（或最大）元素只有一種用法 | 由極端值開始處理，一次處理同值的所有複本 | 核心題 5（846）、659、954、2007 |
| 兩趟掃描 | 一個位置受左右兩個方向的約束 | 各方向的最小解逐點取 max（或 min） | 難題 1（135）、821、42（第 5 章難題 1）、238（第 7 章核心題 1） |
| 覆蓋前綴 `[1, miss)` | 子集合和要覆蓋一段連續整數 | 吸收 ≤ miss 的數，否則補 miss | 難題 2（330）、1798、2952 |
| 後悔式貪婪 | 先接受，違反限制時退掉最差的；或不夠時從候選中補最好的 | heap 存「退掉／補上最划算」的鍵 | 難題 3（630）、難題 4（871）、502（第 14 章難題 3）、1353、1642 Furthest Building You Can Reach |
| 排序規則由交換論證決定 | 「排成什麼順序最好」 | 比較相鄰兩個元素對調前後的代價，推出排序鍵 | 179 Largest Number、406 Queue Reconstruction by Height、1029 Two City Scheduling、621（第 14 章核心題 4） |
| 貪婪當作檢查函式 | 答案空間二分中「給定 x，做得到嗎」 | 貪婪檢查加單調性 | 1011（第 8 章核心題 5）、410（第 8 章難題 2）、875 |

**下限與上限**。最簡單的貪婪題是骨架 A 的區間排程或核心題 1 的 reach：選擇規則很明顯，證明一兩句就能說完。中間層是核心題 2–5：規則本身不難，但要看出背後的結構（BFS 的層是連續區間、前綴和最低點、合法切點獨立、最小值被迫），才能說清楚為什麼對。上限的題目難在三個地方，常常同時出現：第一，**正確的貪婪標準不直觀**，直覺的規則都有反例，例如 630 必須先排序再後悔、1326 不能先選最廣的；第二，**證明需要較強的 invariant**，例如 630 要同時維持「課數最多」與「總天數最小」，330 要用 `S_T(v) >= v` 的刻畫做交換；第三，**需要先轉換問題**，例如 1326 要先轉成跳躍遊戲、871 要先想到「事後補決定」。

**與其他 pattern 的關係**。貪婪和 DP（第 21–23 章）是同一個問題的兩端：DP 考慮所有選擇再取最好，貪婪證明了「只需要考慮一個選擇」。很多題目兩者都能解（871 的 O(n²) DP 與 O(n log n) heap、630 的 O(n · D) DP 與 heap），面試時先給 DP 再優化成貪婪，是一個安全的敘事；反過來，當貪婪找不到證明、而小反例又容易構造時，就該切換到 DP。貪婪也常常是其他 pattern 的零件：答案空間二分（第 8 章）的檢查函式幾乎都是貪婪；區間題（第 9 章）多半是排序後貪婪；heap（第 14 章）是後悔式貪婪的工具；Dijkstra 與 Prim（第 18 章）本身就是貪婪演算法，它們的正確性同樣來自 stays ahead 與 cut property。

**容易混淆之處**。第一，「最少／最多」不代表一定能貪婪：加了權重、容量上限、或每個元素的選擇會改變之後的可選集合（不只是推進一個量）時，貪婪通常會失敗，要回到 DP。第二，貪婪的「選擇」不一定是顯式的：核心題 1 沒有選要跳到哪裡，而是直接追蹤所有走法的聯集；871 的選擇是事後才做的。第三，兩趟掃描和 prefix sum（第 7 章）長得很像，差別是兩趟掃描處理的是「約束」，取 max 合併；prefix sum 處理的是「累加」，用減法合併。

## 本章重點整理

- 貪婪是每一步做局部最好的選擇而且永不反悔；它的程式通常很短，真正的工作是證明「存在一個最佳解包含這個選擇」。
- 四種證明工具：exchange argument（把最佳解的選擇換成貪婪的而不變差）、stays ahead（每一步的進度都不落後）、下界加構造（任何解至少是 L，貪婪剛好達到 L）、invariant（後悔式貪婪維護「目前最好的集合」）。
- 面試時用三句話說證明：「我每一步選 X；因為任何最佳解都能換成 X 而不變差（或貪婪的進度永遠不落後）；所以貪婪最佳。」
- 寫之前先試兩三個刁難的小例子，常見的反例長相是：選擇會改變未來的形狀、有權重、面額不 canonical、只看眼前大小、加了容量上限。
- 四種骨架：排序後掃描（區間排程）、邊界推進（55、45、1326、330）、後悔式 heap（630、871）、兩趟掃描（135）。
- 跳躍遊戲的關鍵是「可達集合是前綴」，最少跳躍的關鍵是「BFS 的每一層是連續區間」；要比較的是落點的 `j + nums[j]`，不是 `nums[j]`，也不是跳最遠。
- 加油站問題：失敗前的前綴和非負，所以失敗後可以整段跳過；總和 ≥ 0 時，從前綴和最低點的下一站出發一定可行。
- 切成最多段時，先證明「每刀的合法性彼此獨立」，貪婪就只是找出所有合法切點；分組問題中，最小元素的用法是被迫的。
- 330 的 invariant「`[1, miss)` 都湊得出來」把子集合和壓成一個數；補 miss 讓範圍推得最遠，Java 中 miss 要用 64 位元。
- 後悔式貪婪：630 依期限排序、超過就丟最長的；871 油不夠時從經過的站中補油最多的；兩者都靠 heap 在 O(log n) 內找出最該退掉或補上的元素。
- 1326 與 1024 先轉成「每個左端點最遠能到哪」，再套 45 題的層次掃描；不保證可達時，在 `x == cur_end` 處檢查是否推不動。
- 貪婪失敗時的退路通常是 DP；能同時給出 DP 與貪婪、並說明貪婪依賴哪個前提（無限油箱、非負數、連續前綴、任意步數），是 L5 水準的回答。
