---
chapter: 6
title: Sliding Window
part: 1
---

# 第 6 章　Sliding Window

> [!abstract] 本章地圖
> **一句話**：當「合法的子陣列縮小後仍然合法」時，對每個右端點而言最好的左端點只會往右走，於是左右兩個指標都只前進、不回頭，把 O(n²) 個子陣列的檢查壓成 O(n) 次增減。
>
> **辨識訊號**：
> - 題目問的是**連續**的子陣列或子字串（substring、subarray），而不是子序列
> - 「最長」「最短」「有幾個」滿足某條件的連續區段
> - 條件具有單調性：窗口變大只會更難（或更容易）滿足，例如元素皆為正數的和、不同字元的種類數、某字元的出現次數
> - 「長度為 k 的每一個窗口」都要算一個值（平均、最大值、字元計數）
> - 「恰好 k 個」的計數題，可以拆成兩個「最多 k 個」相減
> - n 達到 10⁵ 以上，O(n²) 列舉所有子陣列不可行
>
> **核心題**：3、209、424、567、438
>
> **難題**：76、239、992、995、2302

## 6.1 這個 Pattern 解決什麼問題

從一個具體的小問題開始：給一個**非負**整數陣列 `nums` 和上限 `limit`，找出總和不超過 `limit` 的最長連續子陣列。最直接的做法是列舉所有起點 `i` 與終點 `j`，共 n(n+1)/2 個子陣列；用 prefix sum 算區間和的話，每個 O(1)，總共 O(n²)。n = 10⁵ 時是 5 × 10⁹ 次，遠遠超過時間限制。

暴力解浪費在哪裡？假設我們已經知道 `[i, j]` 的和超過 `limit`，那麼 `[i, j+1]`、`[i, j+2]`…一定也超過，因為多加進來的數都是非負的；反過來，如果 `[i, j]` 合法，那麼它裡面任何一段（例如 `[i+1, j]`）也合法。這兩句話合起來代表：**對每一個右端點 `right`，讓窗口合法的左端點是一段連續的範圍 `[best_left, right]`，而且當 `right` 往右移時，`best_left` 只會往右、不會往左**。既然左端點不必回頭，就不需要對每個 `right` 從頭重找。

Sliding window（滑動窗口）就是把這個觀察寫成程式：用兩個指標 `left`、`right` 夾出目前的窗口，`right` 每次往右擴張一格、把新元素「加進」窗口狀態；如果窗口因此變得不合法，就把 `left` 往右收縮、把舊元素「移出」窗口狀態，直到合法為止。每個元素恰好被加入一次、最多被移出一次，所以即使內層有 `while`，總工作量仍然是 O(n)，這種分析叫做 amortized（攤銷）分析。

因此本章每一題都要先回答兩個問題：**窗口狀態是什麼**（總和、字元計數、不同種類數、單調 deque），以及**窗口的合法性是否對收縮單調**（合法的窗口縮小後仍合法，或不合法的窗口放大後仍不合法）。第一個問題決定了「加入」與「移出」要怎麼在 O(1) 內完成；第二個問題決定 sliding window 能不能用。單調性一旦不成立（例如陣列裡有負數），左指標就可能需要回頭，整個方法便會失效，那時要改用第 7 章的 prefix sum。

## 6.2 辨識訊號

| 題目特徵 | 為什麼是 sliding window | 本章哪一題 |
|---|---|---|
| 「最長、不含重複字元」「最多 k 種不同字元」 | 重複或種類數只會在窗口變大時增加，縮小後一定改善 | 核心題 1（3） |
| 正數陣列，「和至少為 target 的最短子陣列」 | 和對窗口延伸單調遞增，合法窗口再延伸仍合法 | 核心題 2（209） |
| 「最多改 k 個字元，能得到最長的全相同子字串」 | 窗口需要的修改數 = 長度 − 最多字元的次數，縮小不會變多 | 核心題 3（424） |
| 「s1 的某個排列是否是 s2 的子字串」「所有 anagram 的位置」 | 長度固定為 len(p) 的窗口，每次只進一個、出一個字元 | 核心題 4（567）、核心題 5（438） |
| 「包含 t 所有字元的最短子字串」 | 「涵蓋 t」對窗口延伸單調，求最短合法窗口 | 難題 1（76） |
| 「每個長度 k 的窗口的最大值」 | 固定窗口，但最大值無法「減掉」，需要 monotonic deque | 難題 2（239） |
| 「恰好 k 種」「恰好和為 goal」的子陣列個數 | 「恰好」不單調，「最多」單調：exactly(k) = atMost(k) − atMost(k − 1) | 難題 3（992） |
| 「每次翻轉連續 k 個」 | 每個位置受前面 k 個操作影響，用窗口維護「目前有幾個翻轉在作用」 | 難題 4（995） |
| 「分數 = 和 × 長度，小於 k 的子陣列有幾個」 | 正數下分數對收縮單調，以 right 結尾的合法子陣列有 right − left + 1 個 | 難題 5（2302） |

一個實用的反向檢查：在紙上找一個合法的窗口，把它從左邊砍掉一個元素，問「還合法嗎？」；再找一個不合法的窗口，往右多加一個元素，問「還是不合法嗎？」。兩個答案都是「是」（或對稱地都是「否」），sliding window 就成立。只要有一個反例，例如和要等於 target 而陣列有負數，就要換方法。

## 6.3 模板與原理：四種窗口

Sliding window 的程式長相很固定：外層 `for right` 擴張，內層 `while` 收縮，差別只在「答案在哪裡更新」。全書用下面四個模板，以「非負整數陣列的子陣列和」當示範；換題目時只要把 `total` 換成該題的窗口狀態。

```python
import random


def longest_at_most(nums: list[int], limit: int) -> int:
    """模板 A，最長合法窗口：和 <= limit 的最長子陣列長度（nums 非負，limit >= 0）。"""
    left = total = best = 0
    for right, x in enumerate(nums):
        total += x                       # 1. 擴張：加入 nums[right]
        while total > limit:             # 2. 不合法就收縮，直到重新合法
            total -= nums[left]
            left += 1
        best = max(best, right - left + 1)   # 3. 此時窗口合法，更新答案
    return best


def shortest_at_least(nums: list[int], target: int) -> int:
    """模板 B，最短合法窗口：和 >= target 的最短子陣列長度，不存在回傳 0（target >= 1）。"""
    left = total = 0
    best = float("inf")
    for right, x in enumerate(nums):
        total += x
        while total >= target:           # 合法時先記錄，再試著縮得更短
            best = min(best, right - left + 1)
            total -= nums[left]
            left += 1
    return 0 if best == float("inf") else best


def max_sum_fixed(nums: list[int], k: int) -> int:
    """模板 C，固定長度窗口：所有長度 k 的子陣列中最大的和（1 <= k <= len(nums)）。"""
    window = sum(nums[:k])
    best = window
    for right in range(k, len(nums)):
        window += nums[right] - nums[right - k]   # 進一個、出一個
        best = max(best, window)
    return best


def count_at_most(nums: list[int], limit: int) -> int:
    """模板 D，計數：和 <= limit 的子陣列個數（nums 非負，limit >= 0）。"""
    left = total = count = 0
    for right, x in enumerate(nums):
        total += x
        while total > limit:
            total -= nums[left]
            left += 1
        count += right - left + 1        # 以 right 結尾的合法子陣列：起點 left..right
    return count


def subarrays(nums):
    return [nums[i:j] for i in range(len(nums)) for j in range(i + 1, len(nums) + 1)]


assert longest_at_most([3, 1, 2, 1, 1], 4) == 3          # [1, 2, 1]
assert longest_at_most([5, 6], 4) == 0                   # 沒有合法的非空窗口
assert longest_at_most([], 3) == 0
assert shortest_at_least([2, 3, 1, 2, 4, 3], 7) == 2     # [4, 3]
assert shortest_at_least([1, 1, 1], 5) == 0
assert max_sum_fixed([1, 4, 2, 10, 2, 3, 1, 0, 20], 4) == 24
assert count_at_most([1, 2, 3], 3) == 4                  # [1] [2] [3] [1, 2]
for _ in range(500):
    arr = [random.randint(0, 6) for _ in range(random.randint(0, 9))]
    lim = random.randint(0, 15)
    t = random.randint(1, 15)
    subs = subarrays(arr)
    assert longest_at_most(arr, lim) == max([len(s) for s in subs if sum(s) <= lim], default=0)
    assert shortest_at_least(arr, t) == min([len(s) for s in subs if sum(s) >= t], default=0)
    assert count_at_most(arr, lim) == sum(1 for s in subs if sum(s) <= lim)
    if arr:
        k = random.randint(1, len(arr))
        assert max_sum_fixed(arr, k) == max(sum(arr[i:i + k]) for i in range(len(arr) - k + 1))
print("all tests passed")
```

**Invariant（迴圈不變式）**。模板 A 與 D 在每一輪 `for` 結束時維持：**窗口 `[left, right]` 是以 `right` 結尾、最長的合法窗口**。為什麼？因為內層 `while` 只在不合法時移動 `left`，一旦合法就停下；而停下的位置不可能太右邊，理由是 `left` 每一次被推過去時，窗口 `[left, right']`（某個 `right' <= right`）都不合法，而它再往右延伸到 `right` 也只會更不合法（非負數只會讓和變大），所以被跳過的起點對 `right` 也都不合法。這就是單調性在證明中的角色：它保證 `left` 永遠不需要回頭。

**模板 B 為什麼在 `while` 裡面更新答案**。最短合法窗口要的是「合法時盡量縮」。每次加入新元素後，只要窗口仍合法，就先記錄長度，再丟掉最左邊的元素試試看更短的；`while` 結束時窗口剛好不合法；若這一步有收縮，最後被記錄的 `[left − 1, right]` 就是以 `right` 結尾的最短合法窗口。對比模板 A：最長窗口是在 `while` **之後**更新（不合法時收縮，合法後才記錄）；最短窗口是在 `while` **之內**更新（合法時記錄，然後收縮）。這一行的位置是兩個模板唯一的本質差別，也是面試中最常寫錯的地方。

**模板 C 不需要 `while`**。固定長度時 `left = right − k + 1` 由 `right` 決定，每一步恰好進一個、出一個，狀態更新是 O(1)。困難不在指標，而在窗口狀態要支援「移出」：和可以直接相減，字元計數可以減一，但最大值無法相減，這就是難題 2 要用 monotonic deque（單調雙端佇列）的原因。

**模板 D 的 `right − left + 1`**。當合法性對收縮單調時，以 `right` 結尾的合法子陣列，起點恰好是 `left, left + 1, …, right`，共 `right − left + 1` 個；把每個 `right` 的個數加起來，就是所有合法子陣列的個數，而且每個子陣列只會在它自己的右端點被算到一次，不會重複。這個技巧讓「計數」也能 O(n) 完成，是難題 3 與難題 5 的核心。

**複雜度**。四個模板都是 O(n) 時間：`right` 走 n 步，`left` 也最多走 n 步，內層 `while` 的總次數不會超過 n。空間是窗口狀態的大小，本節是 O(1)；字串題用計數表時是 O(Σ)，Σ 是字元集大小。

## 6.4 單調性：什麼時候能用、什麼時候不能用

Sliding window 的正確性完全建立在一個性質上：**合法性對窗口的包含關係單調**。可以細分成兩種方向，對應不同的模板：

- **縮小保持合法**（subset-closed）：合法窗口的任何子窗口都合法。例如「和 ≤ limit（非負數）」「沒有重複字元」「最多 k 種字元」。這時問「最長」用模板 A，問「個數」用模板 D。
- **放大保持合法**（superset-closed）：合法窗口往外延伸仍合法。例如「和 ≥ target（正數）」「涵蓋 t 的所有字元」。這時問「最短」用模板 B；問「個數」時，以 `right` 結尾的合法起點是 `0 … 某個位置`，也能一次算出（見核心題 5 的 F2）。

最常見的破壞者是**負數**。下面的例子要找「和 ≥ 4 的最短子陣列」，答案是 `[4]`，長度 1：

```text
nums = [ 2, -1, 4 ]     target = 4
right=0  窗口 [2]          和 2  < 4
right=1  窗口 [2, -1]      和 1  < 4
right=2  窗口 [2, -1, 4]   和 5 >= 4 → 記錄長度 3，丟掉 2
         窗口 [-1, 4]      和 3  < 4 → 停止收縮
結果 3，但正確答案是 1（[4]）
```

問題出在收縮時丟掉 `2` 之後，和反而變小，模板以為「已經不合法、不必再縮」，但再丟掉 `-1` 和又會變大。也就是說，「不合法」不再保證「更短的也不合法」，左指標該停在哪裡無法用單一方向判斷。遇到負數時，正確的工具是第 7 章的 prefix sum：求「和恰好為 k 的個數」用 prefix sum 加 hash map（第 7 章核心題 2，560 題），求「和至少為 k 的最短子陣列」用 prefix sum 加 monotonic deque（第 7 章難題 3，862 題）。

第二個破壞者是**「恰好」條件**。「恰好 k 種不同數字」的窗口縮小後可能變成 k − 1 種，放大後可能變成 k + 1 種，兩個方向都不單調。解法是把它拆成兩個單調的條件：`exactly(k) = atMost(k) − atMost(k − 1)`，兩個 atMost 各用一次模板 D。這是難題 3 的主角，也適用於「恰好有 goal 個 1」（930、1248）。

## 6.5 窗口狀態的設計

模板只負責指標怎麼走；真正決定一題難易的，是窗口狀態能不能在 O(1) 內「加入」和「移出」，以及合法性能不能在 O(1) 內判斷。本章用到的狀態整理如下：

| 狀態 | 加入 | 移出 | 合法性判斷 | 本章題目 |
|---|---|---|---|---|
| 總和 | `total += x` | `total -= x` | 和 ≤ limit、和 ≥ target | 209、2302 |
| 每個值的出現次數 + 種類數 | `cnt[x] += 1`，從 0 變 1 時種類數 +1 | `cnt[x] -= 1`，變 0 時種類數 −1 | 種類數 ≤ k | 3、992 |
| 與目標計數的差異 + 「還缺幾個」 | `need[c] -= 1`，若仍 ≥ 0 則缺少數 −1 | 反向 | 缺少數 == 0 | 76、438 |
| 有幾個字母的計數與目標相同 | 更新前後各檢查一次是否相等 | 同上 | 相同字母數 == 26 | 567 |
| 最多字元的次數（歷史最大值） | `maxf = max(maxf, cnt[c])` | 不更新（見核心題 3） | 長度 − maxf ≤ k | 424 |
| 單調 deque | 從尾端彈出較小者再推入 | 隊首過期時彈出 | 隊首即為最大值 | 239 |
| 作用中的操作數 | 在 i 開始一個操作時 +1 | 操作過期（i − k）時 −1 | 奇偶決定目前位元 | 995 |

設計時的一個原則：**不要每一步重新計算整個窗口**。例如 567 題若每一步都比較兩個長度 26 的計數表，是 O(26n)，在面試中可以接受，但若把「有幾個字母的計數相同」維護成一個整數，每步只檢查進出的那兩個字母，就變成真正的 O(n)，而且同一套寫法能推廣到字元集很大的情況。另一個原則是，**當某個量不能相減（最大值、最小值、中位數）時**，就需要額外的資料結構：最大值用 monotonic deque（難題 2），中位數用兩個 heap（第 14 章難題 2，480 題）。

## 6.6 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| 最長窗口在 `while` 之前更新答案 | 把不合法的窗口長度算進答案，結果偏大 | 最長：收縮完、窗口合法後才更新；最短：在 `while` 合法時更新 |
| 有負數仍用 sliding window | 某些輸入少算或漏掉最佳窗口（見 6.4 節的反例） | 先檢查「縮小保持合法」是否成立；負數改用 prefix sum（第 7 章） |
| 直接對「恰好 k」滑窗 | 計數偏少，因為同一個 right 的合法起點有很多個 | 拆成 atMost(k) − atMost(k − 1)，或同時維護兩個左指標 |
| 3 題用 `left = last[c] + 1` 而沒取 max | `"abba"` 這種輸入時左指標往回跳，答案偏大 | 只有 `last[c] >= left` 時才跳，或寫 `left = max(left, last[c] + 1)` |
| 計數表移出後沒有刪除 0 的 key | `len(cnt)` 當作種類數時偏大 | 計數變 0 時 `del cnt[x]`，或另外維護種類數 |
| 固定窗口忘了處理 `len(p) > len(s)` | 初始化 `s[:m]` 時長度不足，結果錯誤或越界 | 一開始就判斷 m > n 時直接回傳 |
| 固定窗口第一個窗口沒有檢查 | 漏掉起點 0 的答案 | 先建好第一個窗口並檢查，再從 `right = m` 開始滑 |
| deque 存值而不是索引 | 無法判斷隊首是否已經滑出窗口 | deque 存索引，比較時讀 `nums[i]`，過期用 `dq[0] <= right − k` 判斷 |
| 模板 B 的 target <= 0 | 空窗口也合法，`left` 跑到 `right` 右邊，讀到錯的元素 | 確認 target >= 1；否則答案直接是 1（或依題意處理） |

## 核心題 1｜3. Longest Substring Without Repeating Characters｜Medium

### 題目

給一個字串 `s`，回傳其中**不含重複字元**的最長子字串的長度。子字串必須是連續的一段；只是挑出幾個字元、保持順序但不連續的叫子序列，不算。限制：`0 <= len(s) <= 5 × 10⁴`，`s` 由英文字母、數字、符號與空白組成。

- 範例 1：`s = "abcabcbb"`，回傳 `3`，最長的是 `"abc"`。
- 範例 2：`s = "pwwkew"`，回傳 `3`，最長的是 `"wke"`；`"pwke"` 不連續，是子序列不是子字串。
- 範例 3：`s = "bbbbb"`，回傳 `1`。
- 範例 4（邊界）：`s = ""` 回傳 `0`；`s = " "`（一個空白）回傳 `1`，空白也是一個字元。

### 思路

暴力解是列舉每個起點 `i`，往右延伸直到遇到重複字元，記錄延伸的長度。用一個 set 檢查重複，每個起點最多延伸 min(n, Σ) 步（Σ 是字元集大小），時間 O(n · min(n, Σ))。瓶頸在於：起點從 `i` 換到 `i + 1` 時，我們把 `s[i+1 … j]` 這一段已經確認過「沒有重複」的部分全部重新檢查了一次。

關鍵觀察是單調性：如果 `s[l … r]` 沒有重複字元，那麼它的任何子字串也沒有重複；如果 `s[l … r]` 有重複，那麼再往右延伸也一定有重複。所以這是「縮小保持合法」的條件，直接套 6.3 節的模板 A：`right` 往右擴張，加入 `s[right]` 後若發生重複，就把 `left` 往右收縮到重複消失為止，再用 `right − left + 1` 更新答案。Invariant 是：每一輪結束時，`s[left … right]` 是以 `right` 結尾、最長的無重複子字串。

收縮還能更快。如果記住每個字元**最後一次出現的位置** `last[c]`，那麼加入 `s[right] = c` 而發生重複時，重複的那一個 `c` 正好在 `last[c]`，左指標必須跳到 `last[c] + 1`，中間的字元不必一個一個移出。但要小心：`last[c]` 可能早就在窗口左邊（已經被收縮掉），這時它不構成重複，`left` 不能往回跳。所以只有 `last[c] >= left` 時才跳，等價於 `left = max(left, last[c] + 1)`。

```text
s = "abba"
right  字元  last[c]  last[c] >= left?  left  窗口      長度  best
  0     a      -          否             0    "a"        1     1
  1     b      -          否             0    "ab"       2     2
  2     b      1          是 → left=2    2    "b"        1     2
  3     a      0          否（0 < 2）    2    "ba"       2     2
結果 2

如果漏掉「>= left」的檢查，right=3 時 left 會跳回 0 + 1 = 1，
窗口變成 "bba"，長度 3，答案錯誤。

s = "pwwkew"
right  字元  動作                       窗口     best
  0     p    加入                       "p"       1
  1     w    加入                       "pw"      2
  2     w    重複，left 跳到 last[w]+1=2 "w"       2
  3     k    加入                       "wk"      2
  4     e    加入                       "wke"     3
  5     w    重複，left 跳到 last[w]+1=3 "kew"     3
```

`"abba"` 是這題最好的測試案例：處理第二個 `a` 時，`last['a'] = 0` 已經在窗口左邊，因為窗口在處理第二個 `b` 時就跳到了位置 2。這正是「左指標不回頭」的具體表現。面試時寫完程式，主動用 `"abba"` 走一次，就能證明你知道這個邊界。

### 解法

```python
import random


def length_of_longest_substring(s: str) -> int:
    last: dict[str, int] = {}
    left = best = 0
    for right, ch in enumerate(s):
        if last.get(ch, -1) >= left:     # 重複字元在窗口內，才需要跳
            left = last[ch] + 1
        last[ch] = right
        best = max(best, right - left + 1)
    return best


def length_with_set(s: str) -> int:
    """模板 A 的原始寫法：一個一個移出，直到沒有重複。"""
    seen: set[str] = set()
    left = best = 0
    for right, ch in enumerate(s):
        while ch in seen:
            seen.remove(s[left])
            left += 1
        seen.add(ch)
        best = max(best, right - left + 1)
    return best


def brute(s: str) -> int:
    return max((j - i for i in range(len(s)) for j in range(i + 1, len(s) + 1)
                if len(set(s[i:j])) == j - i), default=0)


assert length_of_longest_substring("abcabcbb") == 3
assert length_of_longest_substring("pwwkew") == 3
assert length_of_longest_substring("bbbbb") == 1
assert length_of_longest_substring("") == 0
assert length_of_longest_substring(" ") == 1
assert length_of_longest_substring("abba") == 2
assert length_of_longest_substring("dvdf") == 3
for _ in range(500):
    t = "".join(random.choice("abcd ") for _ in range(random.randint(0, 12)))
    assert length_of_longest_substring(t) == length_with_set(t) == brute(t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：`right` 走一次，跳躍版本中 `left` 只做 O(1) 的指派；set 版本中每個字元最多被加入、移出各一次。空間 O(min(n, Σ))，`last` 最多存每種字元一次；若字元集固定（例如 ASCII 128 個），可以視為 O(1)。邊界情況：空字串時迴圈不執行，回傳 0；全部相同時每一步都跳，答案 1；完全沒有重複時 `left` 永遠是 0，答案 n；空白、數字、符號都是普通字元，不需要特殊處理。

### Follow-up

> [!question]- F1. 如果要回傳最長的子字串本身，而且有多個時回傳最左邊那個？
> 在更新答案時一併記錄起點：`if right - left + 1 > best: best, start = right - left + 1, left`，最後回傳 `s[start:start + best]`。用嚴格大於 `>` 而不是 `>=`，同長度時保留先出現的那個，也就是最左邊的。複雜度不變，O(n) 時間、O(Σ) 空間。若要回傳所有最長的子字串，就把 `>` 與 `==` 分開處理，用串列收集起點；由於長度相同的窗口起點都不同，最多 n 個。

> [!question]- F2. 如果改成「最多包含 k 種不同字元」的最長子字串（340 題；k = 2 是 159 題）？
> 合法性變成「種類數 ≤ k」，仍然是縮小保持合法，套模板 A。窗口狀態改成計數表 `cnt`，加入 `s[right]` 後若 `len(cnt) > k`，就移出 `s[left]`：計數減一，變 0 時 `del cnt[s[left]]`，直到 `len(cnt) <= k`。時間 O(n)，空間 O(k)。這裡不能用 `last` 跳躍，因為要丟掉的是「某一種字元的全部出現」，該跳到哪裡要看窗口中哪種字元最後一次出現得最早；可以用 `last` 加上 OrderedDict 維護，但計數表加 `while` 更簡單也不慢。

> [!question]- F3. 如果允許每個字元最多出現 k 次呢？
> 合法性是「每個字元的次數 ≤ k」，縮小保持合法。用計數表：加入 `c` 後若 `cnt[c] > k`，就從左邊一個一個移出，直到 `cnt[c] == k`（只有 c 會超標，因為只有它剛被加入）。時間 O(n)。若想保留 O(1) 跳躍，可以為每個字元存一個長度 k 的 deque 記錄最近 k 次出現的位置：加入 `c` 時若它已有 k 個位置，`left = max(left, positions[c][0] + 1)` 再彈出最舊的那個，空間 O(n)。

> [!question]- F4. 如果目標改成「沒有重複元素的子陣列中，元素和最大」（1695. Maximum Erasure Value）？
> 窗口與合法性完全相同（沒有重複），只是答案從長度換成和。額外維護 `total`：加入時 `total += x`，移出時 `total -= nums[left]`，每輪用 `total` 更新答案。注意這時用 set 加 `while` 的版本最直接，因為跳躍版本會一次跳過很多元素，必須用 prefix sum 才能 O(1) 算出窗口和：`prefix[right + 1] - prefix[left]`。兩種寫法都是 O(n)。即使元素都是正數，最長的窗口也不一定和最大，例如 `[100, 200, 1, 1, 2, 3, 4, 5]` 中最長的是 `[1, 2, 3, 4, 5]`（和 15），最大和卻是 `[100, 200, 1]`（和 301），所以答案要用 `total` 更新，不能先求最長再算和。

## 核心題 2｜209. Minimum Size Subarray Sum｜Medium

### 題目

給一個**正整數**陣列 `nums` 和正整數 `target`，找出總和**至少**為 `target` 的最短連續子陣列，回傳它的長度；如果不存在，回傳 `0`。限制：`1 <= len(nums) <= 10⁵`，`1 <= nums[i] <= 10⁴`，`1 <= target <= 10⁹`。

- 範例 1：`target = 7`、`nums = [2, 3, 1, 2, 4, 3]`，回傳 `2`，子陣列 `[4, 3]` 的和是 7。
- 範例 2：`target = 4`、`nums = [1, 4, 4]`，回傳 `1`，單一元素 `[4]` 就夠了。
- 範例 3（邊界）：`target = 11`、`nums = [1, 1, 1, 1, 1, 1, 1, 1]`，回傳 `0`，全部加起來只有 8。
- 範例 4（邊界）：`target = 15`、`nums = [1, 2, 3, 4, 5]`，回傳 `5`，必須取整個陣列。

### 思路

暴力解是列舉所有子陣列，用 prefix sum 讓每個區間和 O(1)，總時間 O(n²)；n = 10⁵ 時約 5 × 10⁹ 次，不可行。瓶頸在於對每個右端點都從頭找左端點，忽略了「元素全是正數」這個條件帶來的結構。

因為元素都是正數，固定右端點 `right` 時，左端點越往右，區間和越小。於是「和 ≥ target」對左端點是單調的：存在一個分界 `L(right)`，起點 ≤ `L(right)` 的都合法、> `L(right)` 的都不合法，最短的合法窗口就是 `[L(right), right]`。更進一步，`right` 增加時，區間和變大，分界 `L(right)` 只會往右移。這就是「放大保持合法」，套 6.3 節的模板 B：每次加入 `nums[right]`，只要窗口和仍 ≥ target，就記錄長度並丟掉 `nums[left]`，試試更短的。

Invariant：每次內層 `while` 結束時，窗口 `[left, right]` 的和 < target，而 `[left − 1, right]`（若曾經合法）是以 `right` 結尾的最短合法窗口，已經被記錄。左指標不需要回頭，因為起點 `p` 被丟掉的那一刻（某個 `right' <= right`），`[p, right']` 合法且已經被記錄；之後任何 `[p, right]` 都比它更長，不可能是更好的答案。

```text
target = 7，nums = [2, 3, 1, 2, 4, 3]
index:  0  1  2  3  4  5

right  加入  窗口           和   動作                         best
  0     2   [2]             2   < 7
  1     3   [2 3]           5   < 7
  2     1   [2 3 1]         6   < 7
  3     2   [2 3 1 2]       8   >= 7 記錄 4，丟掉 2 → 和 6       4
  4     4   [3 1 2 4]      10   >= 7 記錄 4，丟掉 3 → 和 7       4
            [1 2 4]         7   >= 7 記錄 3，丟掉 1 → 和 6       3
  5     3   [2 4 3]         9   >= 7 記錄 3，丟掉 2 → 和 7       3
            [4 3]           7   >= 7 記錄 2，丟掉 4 → 和 3       2
結果 2
```

注意 `right = 4` 那一步，內層 `while` 連續收縮了兩次：只要還合法就一直丟，丟到不合法為止。整個過程中 `right` 走過 6 個位置、`left` 從 0 前進到 5（共 5 次），兩個指標合計只移動 11 次，不超過 2n，這就是 O(n) 的由來。

### 解法

```python
import random
from bisect import bisect_right


def min_sub_array_len(target: int, nums: list[int]) -> int:
    left = total = 0
    best = len(nums) + 1                 # 比任何合法長度都大的哨兵
    for right, x in enumerate(nums):
        total += x
        while total >= target:
            best = min(best, right - left + 1)
            total -= nums[left]
            left += 1
    return best if best <= len(nums) else 0


def min_sub_array_len_bisect(target: int, nums: list[int]) -> int:
    """O(n log n)：prefix 嚴格遞增，對每個 j 找最大的 i 使 prefix[i] <= prefix[j] - target。"""
    prefix = [0]
    for x in nums:
        prefix.append(prefix[-1] + x)
    best = len(nums) + 1
    for j in range(1, len(prefix)):
        i = bisect_right(prefix, prefix[j] - target) - 1
        if i >= 0:
            best = min(best, j - i)
    return best if best <= len(nums) else 0


def brute(target, nums):
    n = len(nums)
    return min((j - i for i in range(n) for j in range(i + 1, n + 1)
                if sum(nums[i:j]) >= target), default=0)


assert min_sub_array_len(7, [2, 3, 1, 2, 4, 3]) == 2
assert min_sub_array_len(4, [1, 4, 4]) == 1
assert min_sub_array_len(11, [1] * 8) == 0
assert min_sub_array_len(15, [1, 2, 3, 4, 5]) == 5
assert min_sub_array_len(1, [1]) == 1
for _ in range(500):
    arr = [random.randint(1, 6) for _ in range(random.randint(1, 10))]
    t = random.randint(1, 30)
    assert min_sub_array_len(t, arr) == min_sub_array_len_bisect(t, arr) == brute(t, arr)
print("all tests passed")
```

### 複雜度與邊界

Sliding window 版本時間 O(n)，每個元素最多加入一次、移出一次；空間 O(1)。Prefix sum 加 bisect 的版本時間 O(n log n)、空間 O(n)。邊界情況：總和不足 target 時 `best` 保持哨兵值，回傳 0；單一元素就 ≥ target 時，加入後立刻收縮，記錄長度 1；需要整個陣列時，直到 `right = n − 1` 才第一次合法。這個寫法依賴「正數」：若有 0，仍然正確（和對收縮不增），但若有負數就會出錯，見 6.4 節的反例。哨兵用 `len(nums) + 1` 而不是無限大，可以讓回傳值保持整數。

### Follow-up

> [!question]- F1. 題目附註要求再寫一個 O(n log n) 的解，怎麼做？為什麼要會這個較慢的解？
> 建 prefix sum `P`，因為元素為正，`P` 嚴格遞增。子陣列 `(i, j]` 的和 ≥ target 等價於 `P[i] <= P[j] − target`，所以對每個 j，用 `bisect_right(P, P[j] − target) − 1` 找最大的合法 i，長度 `j − i`，時間 O(n log n)。它的價值在於推廣性：sliding window 一次只能回答一個 target，但 prefix sum 建好後，可以對任何 j 單獨查詢；若元素可以是 0，P 非遞減，bisect 仍然正確。面試時寫出兩種並比較，能展示你理解單調性從哪裡來。

> [!question]- F2. 如果陣列中有負數呢（862. Shortest Subarray with Sum at Least K）？
> Sliding window 失效，因為丟掉一個負數會讓和變大，「不合法」不再代表「更短的也不合法」。正確做法是 prefix sum 加 monotonic deque：對每個 j，deque 中保存 prefix 值遞增的候選起點；當 `P[j] − P[dq[0]] >= k` 時，記錄長度並彈出隊首（之後的 j 只會更長，它沒有用了）；加入 j 前，從尾端彈出所有 `P[...] >= P[j]` 的起點（j 更新、值更小，嚴格更好）。時間 O(n)，詳細推導在第 7 章難題 3。

> [!question]- F3. 如果改成「和恰好等於 target」的最短子陣列？
> 元素為正時仍可用 sliding window：加入後收縮到 `total <= target`，若 `total == target` 就記錄長度；因為和對左端點嚴格遞減，每個 right 最多只有一個起點使和恰好等於 target，收縮後的窗口就是它。時間 O(n)。若元素可以是負數或 0，就改用 prefix sum 加 hash map：記錄每個 prefix 值最後一次出現的位置，對每個 j 查 `P[j] − target` 的最後位置，時間 O(n)，這是第 7 章核心題 2 的變形。

> [!question]- F4. 如果陣列是環狀的（子陣列可以從尾端繞回開頭）？
> 把陣列接成兩倍長 `nums + nums`，在上面跑同樣的 sliding window，但窗口長度不能超過 n（同一個元素不能用兩次）。由於最短答案若存在，長度一定 ≤ n（整個環的和是所有可能中最大的），只要答案 ≤ n 就一定對應環上一段合法的子陣列；若整個環的和 < target 則回傳 0。時間 O(n)，空間可以用索引取餘數 `nums[i % n]` 做到 O(1)。

## 核心題 3｜424. Longest Repeating Character Replacement｜Medium

### 題目

給一個只含大寫英文字母的字串 `s` 和整數 `k`。你可以做最多 `k` 次操作，每次把任意一個位置的字元改成任意大寫字母。回傳操作後，**由同一個字母組成**的最長子字串的長度。限制：`1 <= len(s) <= 10⁵`，`0 <= k <= len(s)`。

- 範例 1：`s = "ABAB"`、`k = 2`，回傳 `4`，把兩個 `A` 改成 `B`（或反過來）。
- 範例 2：`s = "AABABBA"`、`k = 1`，回傳 `4`，把位置 2 的 `B` 改成 `A`，位置 0–3 的 `"AABA"` 就變成 `"AAAA"`；改位置 3 的 `A` 也能讓位置 2–5 的 `"BABB"` 變成 `"BBBB"`。
- 範例 3（邊界）：`s = "ABC"`、`k = 0`，回傳 `1`，不能改，只能取單一字元。
- 範例 4（邊界）：`s = "AB"`、`k = 5`，回傳 `2`，k 比長度大時答案就是整個字串。

### 思路

先把問題轉成窗口的合法性。一個子字串要變成全部相同，最省的做法是保留出現最多的那個字母、把其他全部改掉，需要的操作數是 `長度 − 最多字母的次數`。所以窗口合法當且僅當 `(right − left + 1) − maxf <= k`，其中 `maxf` 是窗口內出現最多的字母次數。暴力解列舉所有子字串並計數，O(n²)（每個起點往右延伸時累加計數）。

這個條件縮小保持合法：窗口縮小一格時，長度減一，`maxf` 最多減一，所以需要的操作數不會變多。因此可以套模板 A。第一個 O(n) 版本是**對每個字母分別做一次**：固定目標字母 `c`，合法條件變成「窗口中非 `c` 的字元 ≤ k 個」，這是最單純的 sliding window（就是 1004 題），26 個字母各掃一次，O(26n)。這個版本很容易證明正確，面試時先講它是很好的起點。

第二個版本只掃一次：維護 26 個計數與 `maxf`，但**收縮時不更新 `maxf`**，而且每次最多只收縮一格（`if` 而不是 `while`）。這看起來是錯的，因為 `maxf` 可能已經過時（比窗口內的真實最大次數大），但答案仍然正確，理由有兩點。第一，窗口長度從不縮小：每一步要嘛長度加一（擴張後合法），要嘛不變（擴張一格、收縮一格），所以最後的窗口長度就是過程中出現過的最大長度。第二，窗口變長時 `left` 沒有動，所以創造 `maxf` 的那些字母仍然在窗口裡，變長後的窗口是真的合法；而窗口一旦開始平移，就代表長度已經等於 `maxf + k`，要再變長，只能等某個字母在當前窗口中的次數超過 `maxf`，這個新次數一定是真實的（剛加入的那個字母在當前窗口的計數）。所以「答案 = 歷史最大的 maxf + k，但不超過 n」。用過時的 `maxf` 只會讓窗口保持原來的長度平移，不會讓它錯誤地變長。

```text
s = "AABABBA"，k = 1
right  加入  cnt(A,B)  maxf  長度−maxf  動作                 窗口       長度
  0     A     1,0       1       0      合法                 [A]          1
  1     A     2,0       2       0      合法                 [AA]         2
  2     B     2,1       2       1      合法                 [AAB]        3
  3     A     3,1       3       1      合法                 [AABA]       4
  4     B     3,2       3       2      > 1，left 右移一格    [ABAB]       4
  5     B     2,3       3       2      > 1，left 右移一格    [BABB]       4
  6     A     2,3       3       2      > 1，left 右移一格    [ABBA]       4
結果 4
```

`right = 4` 之後，窗口一直保持長度 4 往右平移。`right = 6` 時，窗口 `ABBA` 的真實最大次數是 2，`maxf = 3` 已經過時；但我們只是讓窗口平移，沒有讓它變成 5，所以答案仍然是正確的 4。要讓答案變成 5，必須有某個字母在一個長度 5 的窗口中出現 4 次，那時 `maxf` 會被真實地更新到 4。

### 解法

```python
import random


def character_replacement(s: str, k: int) -> int:
    cnt = [0] * 26
    left = maxf = 0
    for right, ch in enumerate(s):
        idx = ord(ch) - 65
        cnt[idx] += 1
        maxf = max(maxf, cnt[idx])               # 只會增加，不因收縮而下修
        if right - left + 1 - maxf > k:          # 最多超過一格，所以 if 就夠
            cnt[ord(s[left]) - 65] -= 1
            left += 1
    return len(s) - left                         # 窗口長度從不縮小，最後的長度就是答案


def character_replacement_per_letter(s: str, k: int) -> int:
    """O(26n)：對每個目標字母，求「非該字母 <= k 個」的最長窗口。"""
    best = 0
    for target in set(s):
        left = others = 0
        for right, ch in enumerate(s):
            others += ch != target
            while others > k:
                others -= s[left] != target
                left += 1
            best = max(best, right - left + 1)
    return best


def brute(s, k):
    n = len(s)
    return max(j - i for i in range(n) for j in range(i + 1, n + 1)
               if (j - i) - max(s[i:j].count(c) for c in set(s[i:j])) <= k)


assert character_replacement("ABAB", 2) == 4
assert character_replacement("AABABBA", 1) == 4
assert character_replacement("ABC", 0) == 1
assert character_replacement("AB", 5) == 2
assert character_replacement("A", 0) == 1
for _ in range(500):
    t = "".join(random.choice("ABC") for _ in range(random.randint(1, 10)))
    kk = random.randint(0, 4)
    assert character_replacement(t, kk) == character_replacement_per_letter(t, kk) == brute(t, kk)
print("all tests passed")
```

### 複雜度與邊界

單次掃描版本時間 O(n)、空間 O(26) = O(1)；逐字母版本時間 O(Σ · n)，Σ 是實際出現的字母種類數。邊界情況：k = 0 時答案是最長的連續相同字母段；k ≥ n 時窗口從不收縮，回傳 n；只有一個字元時回傳 1。單次掃描版本回傳 `len(s) − left` 而不是在迴圈中記錄 `best`，兩者等價，因為窗口長度單調不減。要特別注意，迴圈結束時的窗口**本身不一定合法**（範例中最後的 `ABBA` 需要 2 次操作），它只是長度等於答案，所以不能直接拿它當「答案的子字串」。

### Follow-up

> [!question]- F1. 如果輸入是 0／1 陣列，最多把 k 個 0 翻成 1，求最長的連續 1（1004. Max Consecutive Ones III）？
> 這是本題固定目標字母為 1 的特例，就是上面 `character_replacement_per_letter` 的內層迴圈：維護窗口中 0 的個數，超過 k 就收縮，時間 O(n)、空間 O(1)。若改成「最多翻一個 0」（487 題）而且輸入是串流、不能回頭讀，就只記住窗口中最後一個 0 的位置，超過時左指標直接跳到它的下一格，不需要保存窗口內容。

> [!question]- F2. 如果要回傳實際的子字串，以及要改成哪個字母？
> 單次掃描版本最後的窗口不一定合法（見複雜度一節），不能直接回傳。有兩種做法：一是用逐字母版本，在 `best` 更新時記錄 `(left, right, target)`，O(26n)；二是先用單次掃描得到長度 L，再用長度 L 的固定窗口重掃一次，維護 26 個計數，找到第一個 `L − max(cnt) <= k` 的窗口，回傳它和它的最多字母，O(26n) 或配合 F3 的技巧做到 O(n)。

> [!question]- F3. 如果字元集很大（例如任意 Unicode），而且需要窗口內「真實的」最多次數？
> 逐字母版本會變成 O(Σ · n)，不可行；單次掃描版本用 dict 計數仍是 O(n)，因為它只需要歷史最大值。若需要真實的最大次數（例如 F2 的驗證），可以維護「次數的次數」：`freq_of[c]` 是字母 c 的次數，`bucket[f]` 是次數為 f 的字母有幾個。加入時把 c 從 bucket[f] 移到 bucket[f + 1]，若 f + 1 > maxf 則 maxf 加一；移出時從 bucket[f] 移到 bucket[f − 1]，若 bucket[maxf] 變 0 則 maxf 減一。因為每次只變動 1，maxf 也只變動 1，所有操作 O(1)。

> [!question]- F4. 如果反過來問：要得到長度至少為 L 的全相同子字串，最少要幾次操作？
> 只看長度恰好 L 的窗口就夠了（更長的窗口需要的操作只會更多或相等，取它裡面長度 L 的一段即可）。用固定窗口模板滑過所有長度 L 的窗口，每個窗口的成本是 `L − max(cnt)`，取最小值。用 F3 的 bucket 技巧維護真實最大次數，時間 O(n)；字元集只有 26 個時直接 `max(cnt)` 是 O(26n)。另一個角度是利用「最少操作數 g(L) 對 L 不減」，以及「g(L) ≤ k 等價於本題在 k 下的答案 ≥ L」：在 [0, L] 上對 k 做 binary search（第 8 章），每次用本題的單次掃描 O(n) 檢查，單一查詢 O(n log n)。它比直接滑固定窗口慢一個 log，但檢查時只需要歷史最大的 `maxf`，不必維護真實最大次數；面試時兩種都能說出來，並指出直接滑窗才是最佳解。

## 核心題 4｜567. Permutation in String｜Medium

### 題目

給兩個只含小寫英文字母的字串 `s1` 和 `s2`，如果 `s1` 的**某一個排列**（重新排列字母的順序）是 `s2` 的子字串，回傳 `True`，否則回傳 `False`。換句話說，問 `s2` 中有沒有一段長度為 `len(s1)` 的子字串，它的各字母次數和 `s1` 完全相同。限制：`1 <= len(s1), len(s2) <= 10⁴`。

- 範例 1：`s1 = "ab"`、`s2 = "eidbaooo"`，回傳 `True`，`s2` 中有 `"ba"`。
- 範例 2：`s1 = "ab"`、`s2 = "eidboaoo"`，回傳 `False`，`b` 和 `a` 中間隔了一個 `o`。
- 範例 3（邊界）：`s1 = "abc"`、`s2 = "ab"`，回傳 `False`，`s1` 比 `s2` 長。
- 範例 4（邊界）：`s1 = "aab"`、`s2 = "aba"`，回傳 `True`，整個 `s2` 就是一個排列；次數必須一致，`s2 = "abb"` 時回傳 `False`。

### 思路

暴力解是產生 `s1` 的所有排列並逐一在 `s2` 中搜尋，有 m! 個排列，完全不可行。稍好的做法是對 `s2` 每一段長度 m 的子字串排序或計數，再和 `s1` 比較，共 n − m + 1 段、每段 O(m)，時間 O(n · m)，最差約 2.5 × 10⁷ 次。瓶頸是相鄰兩段只差頭尾兩個字元，卻每次都重算整段的計數。

「排列」等價於「各字母次數相同」，而窗口長度固定為 m，所以用 6.3 節的模板 C：先建好 `s2[0:m]` 的計數，之後每往右滑一格，只加入 `s2[right]`、移出 `s2[right − m]`。如果每一步都比較兩個長度 26 的陣列，是 O(26n)，已經足夠快。更好的做法是維護一個整數 `matches`：26 個字母中，有幾個字母在窗口裡的次數剛好等於在 `s1` 裡的次數。`matches == 26` 就代表找到排列。

更新 `matches` 的技巧是：某個字母 c 的計數改變前，若它原本相等，`matches` 減一；改變後，若它變得相等，`matches` 加一。每次滑動只有兩個字母改變，所以是 O(1)。這個寫法的好處是不依賴字元集大小，換成 dict 後也能處理任意字元（見 F1）。

```text
s1 = "ab"（需要 a:1, b:1），s2 = "eidbaooo"，m = 2
以下只列出 a、b 兩個字母；其他 24 個字母在 s1 中次數為 0，
只要窗口裡沒有它們就算相等。

窗口    進  出  a  b  其他字母   matches   結果
"ei"    -   -   0  0  e:1 i:1    22+0=22   否（a、b 不足，e、i 多出）
"id"    d   e   0  0  i:1 d:1    22        否
"db"    b   i   0  1  d:1        24        否（b 相等了，a 還差一個）
"ba"    a   d   1  1  -          26        是 → 回傳 True
```

這個表的 `matches` 從 22 開始，因為 `s1` 只用到 a、b，其餘 24 個字母在 `s1` 中是 0；第一個窗口 `"ei"` 讓 e、i 不相等，a、b 也不相等，所以是 26 − 4 = 22。之後每滑一格只重新檢查進出的兩個字母，直到 26 個全部相等。

### 解法

```python
import random
from collections import Counter


def check_inclusion(s1: str, s2: str) -> bool:
    m, n = len(s1), len(s2)
    if m > n:
        return False
    need = [0] * 26
    have = [0] * 26
    for ch in s1:
        need[ord(ch) - 97] += 1
    for ch in s2[:m]:
        have[ord(ch) - 97] += 1
    matches = sum(need[i] == have[i] for i in range(26))

    def change(i: int, delta: int) -> None:
        nonlocal matches
        if have[i] == need[i]:
            matches -= 1
        have[i] += delta
        if have[i] == need[i]:
            matches += 1

    for right in range(m, n):
        if matches == 26:
            return True
        change(ord(s2[right]) - 97, +1)
        change(ord(s2[right - m]) - 97, -1)
    return matches == 26


def check_inclusion_counter(s1: str, s2: str) -> bool:
    """O(26n) 的直觀版本：每一步直接比較計數表。"""
    m = len(s1)
    need, window = Counter(s1), Counter(s2[:m])
    if window == need:
        return True
    for right in range(m, len(s2)):
        window[s2[right]] += 1
        window[s2[right - m]] -= 1
        if window == need:           # Python 3.10+ 的 Counter 比較會忽略值為 0 的 key
            return True
    return False


assert check_inclusion("ab", "eidbaooo") is True
assert check_inclusion("ab", "eidboaoo") is False
assert check_inclusion("abc", "ab") is False
assert check_inclusion("aab", "aba") is True
assert check_inclusion("aab", "abb") is False
assert check_inclusion("a", "a") is True
assert check_inclusion("adc", "dcda") is True        # 最後一個窗口才符合
for _ in range(500):
    a = "".join(random.choice("abc") for _ in range(random.randint(1, 4)))
    b = "".join(random.choice("abc") for _ in range(random.randint(1, 10)))
    expect = any(sorted(b[i:i + len(a)]) == sorted(a) for i in range(len(b) - len(a) + 1))
    assert check_inclusion(a, b) == check_inclusion_counter(a, b) == expect
print("all tests passed")
```

### 複雜度與邊界

`matches` 版本時間 O(m + n + Σ)，建表 O(m)、初始化 matches O(Σ)、滑動 O(n)；空間 O(Σ) = O(26)。Counter 版本每次比較 O(Σ)，總共 O(Σ · n)。邊界情況：`m > n` 必須先判斷，否則第一個窗口長度不足；第一個窗口不能漏掉（程式在每輪開頭檢查上一個窗口，所以第一個窗口在 `right = m` 那輪被檢查）；最後一個窗口在迴圈結束後檢查，`"adc"` 與 `"dcda"` 這個測試就是為此而設；`m == n` 時迴圈不執行，直接比較整個字串。

### Follow-up

> [!question]- F1. 如果字串可以包含任意 Unicode 字元呢？
> 不能用長度 26 的陣列，也不能用「26 個字母中有幾個相等」，因為字元集太大。改成維護 `diff = Counter(s1)` 減去窗口計數，以及 `nonzero` = diff 中非零的 key 數量：加入字元 c 時 `diff[c] -= 1`，移出時 `diff[c] += 1`，每次更新前後檢查它是否從 0 變非 0（nonzero 加一）或從非 0 變 0（nonzero 減一）。`nonzero == 0` 時找到排列。時間 O(m + n)、空間 O(不同字元數)，與字元集大小無關。

> [!question]- F2. 如果 s1 可以包含萬用字元 '?'，可以配對任何字母呢？
> 設 s1 有 q 個 '?'，其餘字母的需求是 need。長度 m 的窗口能配對，當且僅當每個字母 c 的窗口次數 ≥ need[c]：先把需要的字母配好，剩下的 m − (m − q) = q 個字元剛好交給 '?'。所以只要維護 `deficit` = 窗口次數 < need 的字母數量，滑動時只檢查進出的兩個字母是否跨過 need 的門檻，`deficit == 0` 即成立。時間仍是 O(n + m)。

> [!question]- F3. 如果不要求「恰好是排列」，而是找 s2 中包含 s1 所有字母（含次數）的最短子字串？
> 窗口長度不再固定，問題變成「涵蓋 s1」的最短窗口，這就是難題 1（76. Minimum Window Substring）。合法性從「每個字母次數相等」放寬成「每個字母次數 ≥ 需求」，後者對窗口延伸單調，所以改用模板 B：擴張到涵蓋後盡量收縮。複雜度仍是 O(m + n)。

> [!question]- F4. 如果同一個 s2 要回答很多個不同的 s1 查詢呢？
> 對每個查詢重跑一次是 O(n) per query。若查詢很多，可以依長度分組：對每個出現過的長度 L，用固定窗口滑過 s2 一次，計算每個窗口的「多重集合雜湊」：給每個字母一個隨機 64 位元整數 `r[c]`，窗口雜湊是 `sum(r[c])` 取 mod 2⁶⁴，加入加、移出減，O(1) 更新；把所有雜湊放進 set。查詢時算 s1 的雜湊，O(m) 查表。不同長度最多 O(√(總查詢長度)) 種，預處理 O(n · 不同長度數)。雜湊可能碰撞，必要時對命中的窗口用計數表再驗證一次；這和第 25 章的 rolling hash 是同一種想法。

## 核心題 5｜438. Find All Anagrams in a String｜Medium

### 題目

給兩個只含小寫英文字母的字串 `s` 和 `p`，找出 `s` 中所有是 `p` 的 anagram（相同字母、相同次數、順序任意）的子字串，回傳它們的起始索引，順序不限（下面一律由小到大）。限制：`1 <= len(s), len(p) <= 3 × 10⁴`。

- 範例 1：`s = "cbaebabacd"`、`p = "abc"`，回傳 `[0, 6]`，分別是 `"cba"` 與 `"bac"`。
- 範例 2：`s = "abab"`、`p = "ab"`，回傳 `[0, 1, 2]`，`"ab"`、`"ba"`、`"ab"` 都是，窗口可以重疊。
- 範例 3（邊界）：`s = "a"`、`p = "ab"`，回傳 `[]`，`p` 比 `s` 長。
- 範例 4（邊界）：`s = "aaaa"`、`p = "aa"`，回傳 `[0, 1, 2]`。

### 思路

這題是核心題 4 的「全部找出來」版本，暴力解同樣是對每個長度 m 的窗口重新計數，O(n · m)；用核心題 4 的固定窗口加 `matches`，每次 `matches == 26` 時記錄起點 `right − m + 1`，就是 O(n)。這裡示範另一種寫法，它把固定窗口看成可變窗口的一種特例，邏輯更緊湊，也能直接推廣到難題 1。

令 `need[c]` 為「窗口還需要多少個 c」，初始為 `p` 的計數。`right` 每加入一個字元 c，就 `need[c] -= 1`。如果 `need[c]` 變成負數，代表窗口裡的 c 比 `p` 多，這個窗口不可能是 anagram，任何包含這麼多 c 的窗口都不是；於是從左邊收縮，把字元還回 `need`，直到 `need[c] >= 0`。Invariant 是：**每一輪結束時，窗口中每個字母的次數都不超過它在 `p` 中的次數**。在這個 invariant 下，窗口長度若剛好等於 m，代表窗口用完了 `p` 的所有字母、沒有多也沒有少，就是一個 anagram。

為什麼這樣不會漏掉答案？「每個字母都不超過 `p`」這個條件縮小保持合法，所以這是模板 A：窗口是以 `right` 結尾、最長的「不超量」窗口。若某個以 `right` 結尾的 anagram 存在，它本身不超量、長度 m，所以最長的不超量窗口長度 ≥ m；而不超量的窗口長度不可能超過 m（總量受限於 `p`），因此窗口長度恰好是 m，且就是那個 anagram。

```text
s = "cbaebabacd"，p = "abc"，m = 3，need 初始 a:1 b:1 c:1
right  加入  need 變化            收縮                         窗口    長度  記錄
  0     c    c:0                  -                            [c]      1
  1     b    b:0                  -                            [cb]     2
  2     a    a:0                  -                            [cba]    3    0
  3     e    e:-1                 移出 c b a e → 全部還回        []       0
  4     b    b:0                  -                            [b]      1
  5     a    a:0                  -                            [ba]     2
  6     b    b:-1                 移出 b → b:0                  [ab]     2
  7     a    a:-1                 移出 a → a:0                  [ba]     2
  8     c    c:0                  -                            [bac]    3    6
  9     d    d:-1                 移出 b a c d                  []       0
結果 [0, 6]
```

`right = 3` 的 `e` 不在 `p` 中，`need['e']` 一開始是 0，減一變 −1，左指標必須一路收縮到 `e` 的右邊，窗口變成空的。`right = 6` 時多了一個 `b`，左指標只要丟掉最左邊那個 `b` 就恢復合法。整個過程左指標同樣只往右走，總共 O(n)。

### 解法

```python
import random
from collections import Counter


def find_anagrams(s: str, p: str) -> list[int]:
    m = len(p)
    need = Counter(p)
    result: list[int] = []
    left = 0
    for right, ch in enumerate(s):
        need[ch] -= 1
        while need[ch] < 0:              # ch 超量：收縮直到把多的那個 ch 還回去
            need[s[left]] += 1
            left += 1
        if right - left + 1 == m:        # 不超量且長度為 m，就是 anagram
            result.append(left)
    return result


def find_anagrams_fixed(s: str, p: str) -> list[int]:
    """固定窗口 + matches 的版本（同核心題 4）。"""
    m, n = len(p), len(s)
    if m > n:
        return []
    need, have = [0] * 26, [0] * 26
    for ch in p:
        need[ord(ch) - 97] += 1
    matches = sum(need[i] == 0 for i in range(26))   # 空窗口時，需求為 0 的字母都相等

    def change(i: int, delta: int) -> None:
        nonlocal matches
        matches -= have[i] == need[i]
        have[i] += delta
        matches += have[i] == need[i]

    result = []
    for right in range(n):
        change(ord(s[right]) - 97, +1)
        if right >= m:
            change(ord(s[right - m]) - 97, -1)
        if right >= m - 1 and matches == 26:
            result.append(right - m + 1)
    return result


def brute(s, p):
    m, target = len(p), Counter(p)
    return [i for i in range(len(s) - m + 1) if Counter(s[i:i + m]) == target]


assert find_anagrams("cbaebabacd", "abc") == [0, 6]
assert find_anagrams("abab", "ab") == [0, 1, 2]
assert find_anagrams("a", "ab") == []
assert find_anagrams("aaaa", "aa") == [0, 1, 2]
assert find_anagrams("baa", "aa") == [1]
for _ in range(500):
    a = "".join(random.choice("abc") for _ in range(random.randint(1, 10)))
    b = "".join(random.choice("abc") for _ in range(random.randint(1, 4)))
    assert find_anagrams(a, b) == find_anagrams_fixed(a, b) == brute(a, b)
print("all tests passed")
```

### 複雜度與邊界

兩個版本時間都是 O(n + m)：可變窗口版本中每個字元最多加入、移出各一次；固定窗口版本每步更新兩個字母。空間 O(Σ)，Counter 版本會為 `s` 中不在 `p` 的字元也建立 key，最多 26 個。邊界情況：`m > n` 時，可變窗口版本自然不會出現長度 m 的窗口，不需要特判，固定窗口版本則要先判斷；不在 `p` 中的字元會讓窗口清空；`p` 有重複字母（`"aa"`）時，計數而不是 set 才能正確處理。輸出可能有 n − m + 1 個索引，這是輸出大小的下限。

### Follow-up

> [!question]- F1. 如果 s 是一個字元一個字元送進來的串流，要即時回報 anagram 的結束位置呢？
> 可變窗口版本需要讀 `s[left]`，所以要保存窗口內容；但窗口長度永遠 ≤ m，用一個長度上限 m 的 deque 存窗口中的字元即可，記憶體 O(m + Σ)，與串流總長無關。每收到一個字元，做一次 `need[ch] -= 1` 與收縮，長度等於 m 時回報。每個字元攤銷 O(1)。固定窗口版本同樣只需要最近 m 個字元。

> [!question]- F2. 如果要計數：s 中有多少個子字串「包含」p 的所有字母（每個字母的次數 ≥ p 中的次數）？
> 「涵蓋 p」對延伸單調，以 `right` 結尾的合法子字串，起點是 0 到某個位置 L(right)，共 L(right) + 1 個，而且 L 隨 right 不減。做法：加入 `s[right]` 後，只要窗口仍涵蓋 p，就移出 `s[left]` 並 `left += 1`；收縮停下時 `[left, right]` 不涵蓋、`[left − 1, right]` 涵蓋，所以起點 0 … left − 1 都合法，答案加 `left`。用「還缺幾個字元」的計數 `missing` 判斷涵蓋（同難題 1），時間 O(n + m)。1358 題（含有 a、b、c 三種字元的子字串個數）就是 p = "abc" 的特例。

> [!question]- F3. 如果允許 anagram 有一個字母不同（窗口和 p 只差一次替換）呢？
> 長度仍固定為 m，窗口可以由一次替換變成 anagram，當且僅當 `sum(|have[c] − need[c]|) <= 2`（一個字母多一個、另一個字母少一個）。維護這個 L1 距離 `dist`：每次某個字母的計數變動 ±1，dist 的變化是 `|新差| − |舊差|`，O(1) 更新。固定窗口模板滑過去，`dist <= 2` 時記錄起點，時間 O(n + m)。推廣到「最多 d 次替換」只要把門檻改成 2d。

> [!question]- F4. 如果 p 是由多個單字組成，要找 s 中「所有單字各用一次、順序任意地串接起來」的起點（30. Substring with Concatenation of All Words）？
> 單位從字元變成長度 w 的單字。把 s 依起點 mod w 分成 w 條「單字序列」，每條序列上跑本題的可變窗口版本：need 是單字的計數，加入一個單字後若超量就從左收縮，窗口單字數等於總單字數時記錄起點。每條序列 O(n / w) 個單字，每個單字的切片與雜湊 O(w)，總時間 O(n · w)。這是第 4 章難題 2 的主題，關鍵就是把本題的不超量窗口提升到單字層級。

## 難題 1｜76. Minimum Window Substring｜Hard

### 題目

給兩個字串 `s` 和 `t`，找出 `s` 中最短的子字串，使得 `t` 的每個字元（**包含重複次數**）都出現在這個子字串裡；如果不存在，回傳空字串 `""`。測試資料保證答案唯一。限制：`1 <= len(s), len(t) <= 10⁵`，字元為大小寫英文字母（大小寫視為不同字元）。要求 O(len(s) + len(t))。

- 範例 1：`s = "ADOBECODEBANC"`、`t = "ABC"`，回傳 `"BANC"`。
- 範例 2：`s = "a"`、`t = "a"`，回傳 `"a"`。
- 範例 3（邊界）：`s = "a"`、`t = "aa"`，回傳 `""`，`t` 需要兩個 a，`s` 只有一個。
- 範例 4：`s = "aaflslflsldkalskaaa"`、`t = "aaa"`，回傳 `"aaa"`（結尾的三個 a）。

### 提示

> [!tip]- 提示 1
> 「涵蓋 t」這個性質，對窗口往外延伸有什麼單調性？一個已經涵蓋 t 的窗口，再多加幾個字元會怎樣？

> [!tip]- 提示 2
> 這是「最短合法窗口」：右指標擴張到涵蓋 t，接著左指標盡量收縮，直到再縮就不涵蓋為止，這時記錄長度。要怎麼在 O(1) 內知道窗口是否涵蓋 t？

> [!tip]- 提示 3
> 維護 `need[c]`（窗口還欠幾個 c，可以是負數代表多了）以及一個整數 `missing` = 所有正的 `need` 加起來。加入 c 時若 `need[c] > 0`，`missing` 減一；移出 c 後若 `need[c] > 0`，`missing` 加一。`missing == 0` 就是涵蓋。

### 詳解

**為什麼直覺做法不行**。暴力解列舉所有 O(n²) 個子字串，每個用計數表檢查是否涵蓋，O(n² · Σ)，n = 10⁵ 時不可能。也不能用核心題 4、5 的固定窗口，因為答案長度未知：最短的涵蓋窗口可能是 `len(t)`，也可能長得多（範例 1 的 `"BANC"` 比 `t` 長一個）。若對長度做 binary search（長度 L 可行則 L + 1 也可行，確實單調），每次用固定窗口檢查，可以做到 O(n log n · Σ)，但題目要求線性。

**突破點：涵蓋對延伸單調**。如果 `s[l … r]` 涵蓋 t，那麼任何包含它的窗口也涵蓋 t。所以固定右端點時，合法的左端點是 `0 … L(r)` 這一段，以 `r` 結尾的最短涵蓋窗口是 `[L(r), r]`；而 `r` 增加時，窗口只會擁有更多字元，`L(r)` 不會往左退。這正是 6.3 節的模板 B：`right` 擴張，`missing == 0` 時記錄並收縮。

**O(1) 判斷涵蓋**。直接比較兩個計數表是 O(Σ)，n · Σ = 5 × 10⁶（Σ = 52），其實也能過，但有更乾淨的寫法。令 `need[c]` 一開始是 `t` 中 c 的次數，`missing = len(t)`。加入字元 c：若 `need[c] > 0`，代表這個 c 補上了一個缺口，`missing -= 1`；然後 `need[c] -= 1`（可能變負，代表窗口中的 c 多於需求）。移出字元 c：先 `need[c] += 1`，若之後 `need[c] > 0`，代表剛剛丟掉的是一個必要的 c，`missing += 1`。在任何時刻，`missing` 等於所有正的 `need[c]` 的和，所以 `missing == 0` 恰好代表每種字元都不欠。不在 `t` 裡的字元，`need` 從 0 開始只會變成負數，永遠不影響 `missing`。

**正確性**。設最短答案是 `[a, b]`。處理到 `right = b` 之前，`left` 不可能已經越過 a：若 `left` 從 a 被推到 a + 1，那一刻窗口 `[a, right']` 涵蓋 t（只有涵蓋時才會收縮），而 `right' < b` 代表找到比答案更短的涵蓋窗口，矛盾。所以 `right = b` 時 `left <= a`，而 `[left, b]` 到 `[a, b]` 都包含 `[a, b]`、都涵蓋 t，收縮迴圈會一路縮到 a，在窗口等於 `[a, b]` 時記錄它的長度。反過來，程式只在 `missing == 0` 時記錄，記錄到的窗口一定真的涵蓋 t，不會回傳比答案更短的錯誤結果。

```text
s = "ADOBECODEBANC"，t = "ABC"，missing 初始 3
index: 0 1 2 3 4 5 6 7 8 9 10 11 12
       A D O B E C O D E B A  N  C

right  加入  missing  收縮過程                                    記錄
  0     A      2
  3     B      1
  5     C      0      窗口 [0,5] "ADOBEC" 長 6 → 記錄；移出 A → missing 1   6
  6–8   O D E  1
  9     B      1      （多一個 B，need[B] = -1，missing 不變）
 10     A      0      窗口 [1,10] "DOBECODEBA" 長 10，移出 D O；
                      [3,10] 移出 B → need[B]=0 仍不欠；
                      [4,10] 移出 E；[5,10] "CODEBA" 長 6，移出 C → missing 1
 12     C      0      窗口 [6,12] "ODEBANC" 長 7，移出 O D E；
                      [9,12] "BANC" 長 4 → 記錄；移出 B → missing 1         4
結果 "BANC"
```

注意 `right = 10` 時，收縮過程中移出位置 3 的 B，但 `need[B]` 從 −1 回到 0，仍然不欠，所以窗口繼續涵蓋；這就是用計數而不是 set 的原因，窗口中有兩個 B，丟掉一個不影響。最後在 `right = 12` 縮到 `[9, 12]` 時得到最短的 4。

### 解法

```python
import random
from collections import Counter


def min_window(s: str, t: str) -> str:
    need = Counter(t)
    missing = len(t)
    left = 0
    best_len, best_start = len(s) + 1, 0
    for right, ch in enumerate(s):
        if need[ch] > 0:
            missing -= 1
        need[ch] -= 1
        while missing == 0:                          # 涵蓋 t：記錄後盡量收縮
            if right - left + 1 < best_len:
                best_len, best_start = right - left + 1, left
            out = s[left]
            need[out] += 1
            if need[out] > 0:
                missing += 1
            left += 1
    return "" if best_len > len(s) else s[best_start:best_start + best_len]


def brute(s, t):
    target = Counter(t)
    best = ""
    for i in range(len(s)):
        for j in range(i + 1, len(s) + 1):
            if not target - Counter(s[i:j]) and (not best or j - i < len(best)):
                best = s[i:j]
    return best


assert min_window("ADOBECODEBANC", "ABC") == "BANC"
assert min_window("a", "a") == "a"
assert min_window("a", "aa") == ""
assert min_window("aaflslflsldkalskaaa", "aaa") == "aaa"
assert min_window("ab", "b") == "b"
assert min_window("abc", "ABC") == ""                   # 大小寫不同
for _ in range(500):
    a = "".join(random.choice("abc") for _ in range(random.randint(1, 10)))
    b = "".join(random.choice("abc") for _ in range(random.randint(1, 3)))
    got, expect = min_window(a, b), brute(a, b)
    assert len(got) == len(expect)                      # 長度一定相同
    assert not Counter(b) - Counter(got) or got == ""   # 回傳值確實涵蓋 t
print("all tests passed")
```

### 複雜度與邊界

時間 O(|s| + |t|)：建 `need` 是 O(|t|)，`right` 與 `left` 各最多走 |s| 步。空間 O(Σ)，Counter 會為 `s` 中出現的字元建立 key，最多 52 個。邊界情況：`len(t) > len(s)` 時 `missing` 永遠不會歸零，回傳 `""`；`t` 有重複字元時（`"aa"`）必須用計數；不在 `t` 中的字元只會讓 `need` 變負，不影響 `missing`；用 `best_len = len(s) + 1` 當哨兵，最後判斷是否找到。題目保證答案唯一；若有多個同樣短的窗口，`<` 會保留最左邊那個，隨機測試只比較長度就是因為這一點。

### Follow-up

> [!question]- F1. 如果 t 的字元必須依照順序出現（727. Minimum Window Subsequence），也就是找 s 中最短的子字串，使 t 是它的子序列？
> 「t 是子序列」對延伸仍然單調，但窗口狀態無法 O(1) 更新：移出一個字元後，t 的配對方式可能整個改變。常見做法是「前進再後退」：從某個位置往右貪婪配對 t，配完時的位置是 end；再從 end 往左反向配對 t，得到最晚的起點 start，記錄 `[start, end]`，然後從 start + 1 繼續。最差 O(|s| · |t|)。另一種是 DP：`dp[j]` = 以目前位置結尾、配對完 t 的前 j 個字元時最晚的起點，逐字元更新，O(|s| · |t|) 時間、O(|t|) 空間。

> [!question]- F2. 如果 s 很長，而 t 的字元在 s 中很少出現呢？
> 先過濾：建一個串列 `filtered = [(i, c) for i, c in enumerate(s) if c in need]`，只保留 t 中有的字元與它們的原始位置，再在 filtered 上跑同樣的 sliding window，窗口長度用原始位置算 `filtered[r][0] − filtered[l][0] + 1`。過濾是 O(|s|)，但窗口的移動次數降為 O(|filtered|)，當 t 的字元稀疏時，收縮迴圈與 Counter 的操作大幅減少。漸進複雜度不變，是常數上的優化，面試官常問來看你是否會找出「無關字元」。

> [!question]- F3. 如果不需要回傳窗口，而是問 s 中有幾個子字串涵蓋 t？
> 同樣的窗口，但每個 `right` 不只記錄最短，而是計數：收縮迴圈結束時，`[left, right]` 不涵蓋、`[left − 1, right]` 涵蓋，所以以 `right` 結尾、涵蓋 t 的子字串起點是 `0 … left − 1`，共 `left` 個，答案加上 `left`。時間 O(|s| + |t|)。答案最多約 n²/2 ≈ 5 × 10⁹，Python 的整數沒問題，在 Java 要用 long。這與核心題 5 的 F2 是同一個技巧。

> [!question]- F4. 如果只要求 t 中每種字元至少出現一次（忽略次數）呢？
> 把 `need` 改成 `{c: 1 for c in set(t)}`，`missing = len(set(t))`，其餘程式完全不變；因為 `missing` 的定義是「還欠幾個」，換掉初始值就自動得到新語意。這個形式常以「包含所有種類的最短子陣列」出現，例如「最短的子陣列包含陣列中所有不同的值」，就是令 t = 整個陣列的 set。

### 心得

關鍵突破是「涵蓋 t」對窗口延伸單調，所以最短涵蓋窗口就是模板 B；真正的技巧在於用 `need` 加 `missing` 讓「是否涵蓋」變成 O(1) 判斷，而且 `need` 允許變負，自然處理了重複字元與無關字元。它是核心題 5（438）的推廣：438 的窗口要求「不超量」且長度固定，這題要求「不欠缺」而長度自由，兩者用的是同一張 `need` 表，只是一個看負數、一個看正數。面試時先說明單調性與模板 B，再解釋 `missing` 的定義（所有正的 need 之和），最後用範例走一次「多一個 B 時移出不影響涵蓋」，就能同時展示正確性與邊界處理。

## 難題 2｜239. Sliding Window Maximum｜Hard

### 題目

給一個整數陣列 `nums` 和窗口大小 `k`，一個長度為 k 的窗口從最左邊開始，每次往右移動一格，直到碰到最右邊。回傳每個窗口位置的最大值，共 `n − k + 1` 個。限制：`1 <= len(nums) <= 10⁵`，`-10⁴ <= nums[i] <= 10⁴`，`1 <= k <= len(nums)`。

- 範例 1：`nums = [1, 3, -1, -3, 5, 3, 6, 7]`、`k = 3`，回傳 `[3, 3, 5, 5, 6, 7]`。
- 範例 2（邊界）：`nums = [1]`、`k = 1`，回傳 `[1]`。
- 範例 3：`nums = [9, 8, 7, 6]`、`k = 2`，回傳 `[9, 8, 7]`，遞減陣列中每個窗口的最大值都是最左邊那個。
- 範例 4（邊界）：`nums = [4, 2, 12, 3]`、`k = 4`，回傳 `[12]`，k = n 時只有一個窗口。

### 提示

> [!tip]- 提示 1
> 窗口的和可以「加入加、移出減」，最大值為什麼不行？如果用 heap 維護窗口，移出元素時遇到什麼麻煩，可以怎麼繞過？

> [!tip]- 提示 2
> 如果窗口中有 `nums[i] <= nums[j]` 而且 `i < j`，`nums[i]` 還有可能成為之後任何窗口的最大值嗎？

> [!tip]- 提示 3
> 只保留「可能成為最大值」的元素：它們的索引遞增、值嚴格遞減，存在一個 deque 中。加入新元素前，從尾端彈出所有不比它大的；隊首若已滑出窗口就彈出；隊首就是目前的最大值。

### 詳解

**為什麼直覺做法不行**。暴力解是每個窗口掃一次求最大值，O(n · k)，k = n / 2 時是 O(n²)。問題在於最大值不能「移出」：窗口和可以減掉離開的元素，但最大值離開窗口時，我們不知道第二大的是誰。用 max-heap 存 `(−值, 索引)` 可以解決：每次查詢時，若堆頂的索引已經滑出窗口就彈掉（lazy deletion，延遲刪除），否則堆頂就是答案。這是 O(n log n)，在面試中是可以接受的第一版，但仍有更好的。

**突破點：被支配的元素永遠沒用**。若 `i < j` 且 `nums[i] <= nums[j]`，那麼在 j 進入窗口之後，任何同時包含 i 的窗口也包含 j（j 比 i 晚離開），所以 `nums[i]` 永遠不會是唯一的最大值，可以立刻丟掉。把所有被支配的元素丟掉之後，剩下的候選滿足：**索引由小到大，值嚴格遞減**。這就是 monotonic deque（單調雙端佇列）：隊首是最舊、最大的候選，也就是目前窗口的最大值；隊尾是最新、最小的候選。

**三個操作**。加入 `nums[right]`：從隊尾彈出所有值 `<= nums[right]` 的索引（它們被新元素支配了），再把 `right` 推入隊尾，維持嚴格遞減。過期：若隊首索引 `<= right − k`，它已經滑出窗口，彈出；因為每一步窗口只移動一格，最多彈一個。查詢：`right >= k − 1` 時，`nums[dq[0]]` 就是答案。每個索引最多被推入、彈出各一次，所以總時間 O(n)。deque 必須存**索引**而不是值，否則無法判斷隊首是否過期。

**另一種 O(n)：分塊的前綴與後綴最大值**。把陣列切成長度 k 的區塊，計算每個位置在自己區塊內的前綴最大值 `pre[i]` 和後綴最大值 `suf[i]`。任何長度 k 的窗口 `[i, i + k − 1]` 最多跨兩個相鄰區塊，前段是 i 所在區塊的後綴、後段是 `i + k − 1` 所在區塊的前綴，所以最大值是 `max(suf[i], pre[i + k − 1])`。這個做法不需要 deque，三次線性掃描即可，而且容易平行化。

```text
nums = [1, 3, -1, -3, 5, 3, 6, 7]，k = 3
deque 存索引，括號內是值；隊首在左

right  加入   彈出隊尾        過期隊首   deque               最大值
  0     1     -               -         [0(1)]
  1     3     0(1)            -         [1(3)]
  2    -1     -               -         [1(3) 2(-1)]          3
  3    -3     -               -         [1(3) 2(-1) 3(-3)]    3
  4     5     3 2 1           -         [4(5)]                5
  5     3     -               -         [4(5) 5(3)]           5
  6     6     5 4             -         [6(6)]                6
  7     7     6               -         [7(7)]                7
結果 [3, 3, 5, 5, 6, 7]
```

`right = 3` 時 deque 有三個元素，值 3 > −1 > −3 嚴格遞減，隊首 3 仍在窗口 `[1, 3]` 中。`right = 4` 加入 5，三個候選都不比 5 大，全部被彈出；之後只要 5 還在窗口裡，它就是最大值。這個例子剛好沒有用到「過期」，換成 `[5, 4, 3, 2]`、k = 2 就會看到：`right = 2` 時隊首 0(5) 的索引 0 ≤ 2 − 2，被當作過期彈掉。

### 解法

```python
import heapq
import random
from collections import deque


def max_sliding_window(nums: list[int], k: int) -> list[int]:
    dq: deque[int] = deque()                 # 索引，對應的值嚴格遞減
    result = []
    for right, x in enumerate(nums):
        while dq and nums[dq[-1]] <= x:      # 被新元素支配的候選
            dq.pop()
        dq.append(right)
        if dq[0] <= right - k:               # 隊首滑出窗口
            dq.popleft()
        if right >= k - 1:
            result.append(nums[dq[0]])
    return result


def max_sliding_window_heap(nums: list[int], k: int) -> list[int]:
    """O(n log n)：max-heap + lazy deletion。"""
    heap: list[tuple[int, int]] = []
    result = []
    for right, x in enumerate(nums):
        heapq.heappush(heap, (-x, right))
        while heap[0][1] <= right - k:       # 堆頂已過期才刪
            heapq.heappop(heap)
        if right >= k - 1:
            result.append(-heap[0][0])
    return result


def max_sliding_window_blocks(nums: list[int], k: int) -> list[int]:
    """O(n)：區塊內的前綴最大值與後綴最大值。"""
    n = len(nums)
    pre, suf = nums[:], nums[:]
    for i in range(1, n):
        if i % k:
            pre[i] = max(pre[i - 1], nums[i])
    for i in range(n - 2, -1, -1):
        if (i + 1) % k:
            suf[i] = max(suf[i + 1], nums[i])
    return [max(suf[i], pre[i + k - 1]) for i in range(n - k + 1)]


assert max_sliding_window([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]
assert max_sliding_window([1], 1) == [1]
assert max_sliding_window([9, 8, 7, 6], 2) == [9, 8, 7]
assert max_sliding_window([4, 2, 12, 3], 4) == [12]
assert max_sliding_window([5, 4, 3, 2], 2) == [5, 4, 3]
assert max_sliding_window([2, 2, 2], 2) == [2, 2]
for _ in range(500):
    arr = [random.randint(-5, 5) for _ in range(random.randint(1, 12))]
    kk = random.randint(1, len(arr))
    expect = [max(arr[i:i + kk]) for i in range(len(arr) - kk + 1)]
    assert max_sliding_window(arr, kk) == expect
    assert max_sliding_window_heap(arr, kk) == expect
    assert max_sliding_window_blocks(arr, kk) == expect
print("all tests passed")
```

### 複雜度與邊界

Deque 版本時間 O(n)，每個索引最多進出 deque 各一次；額外空間 O(k)，deque 最多 k 個索引（不含輸出的 n − k + 1 個）。Heap 版本時間 O(n log n)，空間 O(n)，因為過期元素只在到達堆頂時才刪除。分塊版本時間 O(n)、空間 O(n)。邊界情況：k = 1 時每個元素自己就是答案；k = n 時只有一個窗口；有重複值時用 `<=` 彈出，讓 deque 嚴格遞減，寫成 `<` 也正確（保留較舊的相同值，過期時再彈），但 deque 會變長；遞減陣列時 deque 不會從尾端彈出，全靠過期彈出，是測試過期邏輯最好的案例。

### Follow-up

> [!question]- F1. 如果要找「最大值減最小值 ≤ limit」的最長子陣列（1438 題）？
> 窗口長度不固定，但「max − min ≤ limit」縮小保持合法，可以套模板 A。同時維護兩個 deque：遞減的 `maxq` 與遞增的 `minq`。加入 `nums[right]` 後，若 `nums[maxq[0]] − nums[minq[0]] > limit`，就把 `left` 加一，並在隊首索引 `< left` 時彈出。每個索引進出各 deque 最多一次，時間 O(n)、空間 O(n)。這是本題與模板 A 的組合，難度在於過期條件從「`<= right − k`」變成「`< left`」。

> [!question]- F2. 如果要的是每個窗口的中位數（480. Sliding Window Median）？
> 中位數既不能相減，也沒有「被支配就沒用」的性質，deque 不適用。標準做法是兩個 heap：max-heap 存較小的一半、min-heap 存較大的一半，移出元素時用 lazy deletion（記錄待刪除的值，等它到堆頂再刪），並維護兩邊「有效元素」的數量平衡，每步 O(log k)，總共 O(n log k)。也可以用排序容器（例如 `sortedcontainers.SortedList`，面試時要先問能否使用）做 O(log k) 插入刪除。詳細推導在第 14 章難題 2。

> [!question]- F3. 如果資料是串流，而且要支援「最近 k 個元素的最大值」這個查詢穿插在插入之間？
> deque 版本本身就是線上的：每次插入做一次「彈出尾端較小者、推入、過期彈出隊首」，攤銷 O(1)；查詢直接讀隊首，O(1)。記憶體 O(k)，不需要保存整個串流。若窗口改成「最近 T 秒」而不是最近 k 個，過期條件改成比較時間戳 `time[dq[0]] <= now − T`，可能一次彈出多個，但仍是攤銷 O(1)。分塊版本則需要整個陣列，不適合串流。

> [!question]- F4. 如果查詢不再是滑動的，而是任意區間 [l, r] 的最大值，總共 q 次？
> 窗口不再單調移動，deque 的「只往右」假設不成立。若陣列不變，用 sparse table：`st[j][i]` 是 `[i, i + 2^j)` 的最大值，O(n log n) 預處理，查詢時取兩個重疊的 2 的冪區間，O(1)。若陣列會更新，用 segment tree，更新與查詢都是 O(log n)，見第 26 章。若查詢可以離線並依右端點排序，也可以用 monotonic stack 加 binary search，每次 O(log n)。

### 心得

關鍵突破是「被較新、較大的元素支配的舊元素永遠不會再是最大值」，所以候選集合可以維持成一個值遞減的 deque，每個元素進出各一次。它和本章其他題的差別在於窗口狀態：其他題的狀態（和、計數）都能直接相減，這題的最大值不能，所以需要一個專門的資料結構。這個 monotonic deque 會在第 7 章難題 3（862）再出現，用在 prefix sum 上，也和第 10 章的 monotonic stack 是同一個想法的兩種形狀。面試時建議先講 O(n log n) 的 heap 加 lazy deletion，說明它的瓶頸是 log，再提出支配關係與 deque，並主動用遞減陣列測試過期邏輯。

## 難題 3｜992. Subarrays with K Different Integers｜Hard

### 題目

給一個正整數陣列 `nums` 和整數 `k`。如果一個連續子陣列中**恰好**有 `k` 種不同的整數，就稱它為「好的子陣列」。回傳好的子陣列的個數。例如 `[1, 2, 3, 1, 2]` 中有 3 種不同的整數。限制：`1 <= len(nums) <= 2 × 10⁴`，`1 <= nums[i], k <= len(nums)`。

- 範例 1：`nums = [1, 2, 1, 2, 3]`、`k = 2`，回傳 `7`：`[1,2]`、`[2,1]`、`[1,2]`、`[2,3]`、`[1,2,1]`、`[2,1,2]`、`[1,2,1,2]`。
- 範例 2：`nums = [1, 2, 1, 3, 4]`、`k = 3`，回傳 `3`：`[1,2,1,3]`、`[2,1,3]`、`[1,3,4]`。
- 範例 3（邊界）：`nums = [1, 1, 1]`、`k = 1`，回傳 `6`，所有子陣列都只有一種數字。
- 範例 4（邊界）：`nums = [1, 2]`、`k = 3`，回傳 `0`，整個陣列也只有兩種。

### 提示

> [!tip]- 提示 1
> 試著直接用一個窗口：固定右端點時，讓窗口恰好有 k 種的左端點有幾個？它們是一個點還是一段？

> [!tip]- 提示 2
> 「恰好 k 種」不單調，但「最多 k 種」縮小保持合法。用 6.3 節的模板 D 可以 O(n) 算出「最多 k 種」的子陣列個數。

> [!tip]- 提示 3
> exactly(k) = atMost(k) − atMost(k − 1)。或者在同一次掃描中維護兩個左指標：一個是「最多 k 種」的最左起點，一個是「最多 k − 1 種」的最左起點，兩者的差就是以 right 結尾、恰好 k 種的起點個數。

### 詳解

**為什麼直覺做法不行**。暴力解是對每個起點往右延伸，同時維護種類數，O(n²)，n = 2 × 10⁴ 時是 2 × 10⁸，在 Python 中太慢。直接套一個窗口也不行：若窗口在「恰好 k 種」時記錄一個答案，會嚴重少算。以範例 1 的 `right = 3` 為例，以它結尾、恰好 2 種的子陣列有 `[1,2,1,2]`、`[2,1,2]`、`[1,2]` 三個，起點分別是 0、1、2，是一整段而不是一個點。單一窗口只能表示一個左端點，無法同時代表三個。

**突破點一：把「恰好」拆成兩個「最多」**。「最多 k 種」對收縮單調：子陣列縮小，種類數不會增加。所以以 `right` 結尾、最多 k 種的起點是一段後綴 `[L_k(right), right]`，個數 `right − L_k(right) + 1`，這就是模板 D，加總起來是 atMost(k)。恰好 k 種的子陣列 = 最多 k 種的 − 最多 k − 1 種的，因為「最多 k 種」的集合恰好分成「恰好 k 種」與「最多 k − 1 種」兩個不相交的部分。所以答案是 `atMost(k) − atMost(k − 1)`，兩次 O(n)。

**突破點二：同一次掃描的兩個左指標**。把上面的減法拆到每個 `right`：最多 k 種的起點是 `[L_k, right]`，最多 k − 1 種的起點是 `[L_{k−1}, right]`，而且 `L_k <= L_{k−1}`（條件越嚴，起點越靠右）。恰好 k 種的起點就是兩段的差 `[L_k, L_{k−1} − 1]`，個數 `L_{k−1} − L_k`。兩個左指標各自單調右移，所以一次掃描、兩個計數表，O(n)。這個角度把「起點是一整段」畫得很清楚，面試時用它來解釋為什麼要相減最直觀。

```text
nums = [1, 2, 1, 2, 3]，k = 2
far  = 最多 2 種的最左起點，near = 最多 1 種的最左起點
恰好 2 種的起點 = [far, near − 1]，個數 near − far

right  加入  far 的窗口       far  near 的窗口  near  恰好 2 種的子陣列          個數
  0     1    [1]               0   [1]           0    -                           0
  1     2    [1 2]             0   [2]           1    [1 2]                       1
  2     1    [1 2 1]           0   [1]           2    [1 2 1] [2 1]               2
  3     2    [1 2 1 2]         0   [2]           3    [1 2 1 2] [2 1 2] [1 2]     3
  4     3    [2 3]             3   [3]           4    [2 3]                       1
合計 0 + 1 + 2 + 3 + 1 = 7

拆成兩個 atMost：
atMost(2)：每個 right 的個數 right − far + 1 = 1 2 3 4 2，合計 12
atMost(1)：每個 right 的個數 right − near + 1 = 1 1 1 1 1，合計 5
12 − 5 = 7
```

`right = 4` 加入 3 之後窗口有 3 種，far 必須收縮：丟掉 1、2、1，直到窗口 `[2, 3]` 只剩兩種，far 從 0 跳到 3。注意 far 跳過的起點 0、1、2，對 `right = 4` 都是 3 種，對之後的 right 也不可能變回 2 種，這正是單調性保證的。

### 解法

```python
import random
from collections import defaultdict


def at_most(nums: list[int], k: int) -> int:
    """最多 k 種不同整數的子陣列個數（模板 D）。"""
    cnt: defaultdict[int, int] = defaultdict(int)
    left = kinds = total = 0
    for right, x in enumerate(nums):
        if cnt[x] == 0:
            kinds += 1
        cnt[x] += 1
        while kinds > k:
            y = nums[left]
            cnt[y] -= 1
            if cnt[y] == 0:
                kinds -= 1
            left += 1
        total += right - left + 1
    return total


def subarrays_with_k_distinct(nums: list[int], k: int) -> int:
    return at_most(nums, k) - at_most(nums, k - 1)


def subarrays_with_k_distinct_one_pass(nums: list[int], k: int) -> int:
    """同一次掃描：far 維持最多 k 種，near 維持最多 k − 1 種。"""
    n = len(nums)
    cnt_far, cnt_near = [0] * (n + 1), [0] * (n + 1)
    kinds_far = kinds_near = far = near = answer = 0
    for x in nums:
        kinds_far += cnt_far[x] == 0
        cnt_far[x] += 1
        kinds_near += cnt_near[x] == 0
        cnt_near[x] += 1
        while kinds_far > k:
            cnt_far[nums[far]] -= 1
            kinds_far -= cnt_far[nums[far]] == 0
            far += 1
        while kinds_near > k - 1:
            cnt_near[nums[near]] -= 1
            kinds_near -= cnt_near[nums[near]] == 0
            near += 1
        answer += near - far
    return answer


def brute(nums, k):
    n = len(nums)
    return sum(len(set(nums[i:j])) == k for i in range(n) for j in range(i + 1, n + 1))


assert subarrays_with_k_distinct([1, 2, 1, 2, 3], 2) == 7
assert subarrays_with_k_distinct([1, 2, 1, 3, 4], 3) == 3
assert subarrays_with_k_distinct([1, 1, 1], 1) == 6
assert subarrays_with_k_distinct([1, 2], 3) == 0
assert at_most([1, 2, 3], 0) == 0                     # k − 1 = 0 時 atMost 為 0
for _ in range(500):
    n = random.randint(1, 10)
    arr = [random.randint(1, n) for _ in range(n)]
    kk = random.randint(1, n)
    expect = brute(arr, kk)
    assert subarrays_with_k_distinct(arr, kk) == expect
    assert subarrays_with_k_distinct_one_pass(arr, kk) == expect
print("all tests passed")
```

### 複雜度與邊界

兩種寫法時間都是 O(n)：拆成兩次 atMost 是兩次線性掃描；單次掃描版本中 `far`、`near`、`right` 各走最多 n 步。空間 O(n)，計數表的大小；題目保證值在 1 到 n 之間，所以可以用長度 n + 1 的陣列取代 dict，常數更小。邊界情況：k − 1 = 0 時，`at_most(nums, 0)` 的窗口一加入就超過，`left` 跑到 `right + 1`，每步加 0，結果是 0，正確；k 大於陣列中的種類數時，兩個 atMost 相等，答案 0；答案最大約 n²/2 = 2 × 10⁸，Python 不會溢位，在 Java 要注意用 int 仍夠（2 × 10⁸ < 2³¹），但推廣到 n = 10⁵ 就要用 long。

### Follow-up

> [!question]- F1. 如果是 0／1 陣列，問和恰好為 goal 的子陣列個數（930. Binary Subarrays With Sum）？或者「恰好 k 個奇數」（1248）？
> 「和 ≤ goal」在非負陣列中縮小保持合法，所以同樣是 `atMost(goal) − atMost(goal − 1)`，其中 atMost 用總和當窗口狀態。要注意 goal = 0 時 `atMost(−1)` 必須回傳 0，而且要在函式開頭直接判斷 `goal < 0` 就回傳：若讓它進入迴圈，窗口清空後 `total = 0 > −1` 仍成立，收縮迴圈會讀到 `nums[right + 1]` 而越界。1248 把奇數看成 1、偶數看成 0 就是同一題。這類題也能用 prefix sum 加 hash map 做到 O(n)（第 7 章核心題 2），差別是 sliding window 只需要 O(1) 空間。

> [!question]- F2. 如果問「至少 k 種」不同整數的子陣列個數呢？
> 「至少 k 種」放大保持合法，可以直接計數：以 `right` 結尾、至少 k 種的起點是 `0 … p`，其中 p 是最右的合法起點。維護「最多 k − 1 種」的窗口 `[near, right]`，那麼起點 < near 的都至少 k 種，答案加 `near`。也可以用總數相減：`n(n+1)/2 − atMost(k − 1)`。兩者都是 O(n)，前者不需要知道總數，適合串流。

> [!question]- F3. 如果要找「恰好 k 種」的最長子陣列呢？
> 最長的問題不需要拆兩個 atMost。求「最多 k 種」的最長窗口（模板 A，即核心題 1 的 F2）。若整個陣列的種類數 ≥ k，這個最長窗口一定恰好有 k 種：若它少於 k 種，又不是整個陣列，就能再往某一邊延伸一格而種類數最多加一，仍然 ≤ k，與「最長」矛盾；若它是整個陣列，那整個陣列的種類數 < k，與假設矛盾。若整個陣列的種類數 < k，答案不存在。所以一次 O(n) 掃描加一次種類數檢查即可。

> [!question]- F4. 如果要求「恰好 k 種，而且每種都恰好出現 m 次」的子陣列個數呢？
> 這個條件沒有任何方向的單調性，相減技巧也不適用。但它隱含窗口長度一定是 k · m，於是變成固定窗口：用模板 C 滑過所有長度 k · m 的窗口，維護計數表、種類數，以及「次數恰好為 m 的種類數」`good`，每次進出時檢查計數跨過 m 的前後變化，`good == k` 且種類數 == k 時加一。時間 O(n)。把限制轉換成「長度固定」，是處理不單調條件的常用招式（類似核心題 4、5）。

### 心得

關鍵突破是看出「恰好」不單調，而「最多」單調，於是 exactly(k) = atMost(k) − atMost(k − 1)；更深一層的理解是，以 `right` 結尾的合法起點是一整段 `[L_k, L_{k−1} − 1]`，單一窗口只能表示一個端點，兩個左指標才能夾出這一段。它把模板 D 的「以 right 結尾的個數 = right − left + 1」用到了極致，也和難題 5（2302）的計數方法相同。面試時先用範例說明單一窗口為什麼少算，再寫兩個 atMost 相減，最後提出單次掃描的版本；這個相減技巧在 930、1248、2062 等題都會再出現。

## 難題 4｜995. Minimum Number of K Consecutive Bit Flips｜Hard

### 題目

給一個只含 0 和 1 的陣列 `nums` 和整數 `k`。一次「k 位元翻轉」是選一段長度恰好為 k 的連續子陣列，把其中每個 0 變成 1、每個 1 變成 0。回傳讓陣列全部變成 1 所需的最少翻轉次數；如果做不到，回傳 `-1`。限制：`1 <= k <= len(nums) <= 10⁵`。

- 範例 1：`nums = [0, 1, 0]`、`k = 1`，回傳 `2`，分別翻轉位置 0 與位置 2。
- 範例 2：`nums = [1, 1, 0]`、`k = 2`，回傳 `-1`：翻 `[1, 2]` 會讓位置 1 變成 0，翻 `[0, 1]` 不影響位置 2，怎麼翻都不行。
- 範例 3：`nums = [0, 0, 0, 1, 0, 1, 1, 0]`、`k = 3`，回傳 `3`，翻轉起點 0、4、5。
- 範例 4（邊界）：`nums = [1, 1, 1]`、`k = 2`，回傳 `0`，已經全部是 1。

### 提示

> [!tip]- 提示 1
> 翻轉的順序重要嗎？同一段翻兩次有意義嗎？所以一組解其實就是「哪些起點被翻了一次」。

> [!tip]- 提示 2
> 看最左邊的位置 0：只有一個翻轉能改變它，就是起點為 0 的那段。所以它要不要翻是確定的。接著位置 1 呢？

> [!tip]- 提示 3
> 從左往右，位置 i 的目前值 = 原值 XOR（起點在 `[i − k + 1, i]` 的翻轉次數的奇偶）。用一個窗口維護「目前還在作用的翻轉有幾個」，起點滑出窗口時減一，就不必真的去改那 k 個元素。

### 詳解

**為什麼直覺做法不行**。直接模擬「找到最左邊的 0，把從它開始的 k 個元素真的翻轉」，每次翻轉 O(k)，最多 n 次，總共 O(n · k)；n = 10⁵、k = 5 × 10⁴ 時是 5 × 10⁹，太慢。而想用 BFS 或 DP 搜尋所有翻轉組合，狀態數是 2ⁿ，更不可行。所以需要兩個觀察：一個說明「怎麼翻」是確定的，另一個讓每次翻轉的成本變成 O(1)。

**突破點一：解是被逼出來的**。翻轉是 XOR，彼此可交換，而且同一段翻兩次等於沒翻，所以任何一組解都可以化簡成「每個起點翻 0 次或 1 次」，順序無關。位置 0 只被起點 0 的翻轉覆蓋，所以若 `nums[0] = 0`，起點 0 必須翻；若是 1，必須不翻。決定好起點 0 之後，位置 1 只被起點 0 和起點 1 覆蓋，起點 0 已經確定，所以起點 1 也被唯一決定。依此類推，起點 i 的翻與不翻由「位置 i 在考慮了起點 `i − k + 1 … i − 1` 之後的值」唯一決定。這代表**可行的解只有一組**，貪婪「遇到 0 就從這裡翻」不只是最佳，而是唯一的解；若某個需要翻的起點 i 滿足 `i + k > n`，就無解。

**突破點二：用窗口記錄作用中的翻轉**。位置 i 的目前值是 `nums[i] XOR (起點在 [i − k + 1, i] 中的翻轉數 mod 2)`。這些起點剛好是一個長度 k 的窗口，於是維護 `active` = 窗口內的翻轉數：走到 i 時，若起點 `i − k` 有翻轉，它剛滑出窗口，`active -= 1`；若 `nums[i] XOR (active & 1)` 是 0，就在 i 開始一個翻轉，`active += 1`。每個位置 O(1)，總共 O(n)。這是 difference array（差分陣列）的想法：只記錄效果的開始與結束，而不是逐一修改區間內每個元素。

```text
nums = [0, 0, 0, 1, 0, 1, 1, 0]，k = 3
flip[i] = 1 代表在 i 開始一次翻轉；active = 起點在 [i−2, i] 的翻轉數

i  nums[i]  滑出的起點    active  目前值 = nums ^ (active&1)  動作            flip
0    0       -              0       0                        翻（0..2）       1 0 0 0 0 0 0 0
1    0       -              1       1                        -
2    0       -              1       1                        -
3    1      起點 0 滑出     0       1                        -
4    0       -              0       0                        翻（4..6）       1 0 0 0 1 0 0 0
5    1       -              1       0                        翻（5..7）       1 0 0 0 1 1 0 0
6    1       -              2       1                        -
7    0      起點 4 滑出     1       1                        -
結果 3 次（起點 0、4、5）
```

`i = 5` 時原值是 1，但起點 4 的翻轉還在作用，目前值變成 0，所以必須在 5 再開一次翻轉；`5 + 3 = 8` 沒有超出長度 8，可以翻。`i = 6` 時有兩個翻轉作用，偶數次等於沒翻，原值 1 保持 1。若把範例改成最後一個元素需要翻，例如範例 2 的 `[1, 1, 0]`、k = 2：位置 2 是 0、需要從 2 開始翻，但 `2 + 2 > 3`，回傳 −1。

### 解法

```python
import random
from itertools import product


def min_k_bit_flips(nums: list[int], k: int) -> int:
    n = len(nums)
    flip = [0] * n                    # flip[i] = 1：在 i 開始一次翻轉
    active = ops = 0
    for i in range(n):
        if i >= k:
            active -= flip[i - k]     # 起點 i − k 的翻轉不再覆蓋 i
        if nums[i] ^ (active & 1) == 0:
            if i + k > n:
                return -1
            flip[i] = 1
            active += 1
            ops += 1
    return ops


def min_k_bit_flips_inplace(nums: list[int], k: int) -> int:
    """O(1) 額外空間：在 nums[i] 加 2 標記「從 i 開始翻轉」（會修改輸入）。"""
    n = len(nums)
    active = ops = 0
    for i in range(n):
        if i >= k and nums[i - k] >= 2:
            active -= 1
        if (nums[i] & 1) ^ (active & 1) == 0:
            if i + k > n:
                return -1
            nums[i] += 2
            active += 1
            ops += 1
    return ops


def brute(nums, k):
    n, best = len(nums), -1
    for choice in product((0, 1), repeat=n - k + 1):
        arr = nums[:]
        for start, c in enumerate(choice):
            if c:
                for j in range(start, start + k):
                    arr[j] ^= 1
        if all(arr) and (best == -1 or sum(choice) < best):
            best = sum(choice)
    return best


assert min_k_bit_flips([0, 1, 0], 1) == 2
assert min_k_bit_flips([1, 1, 0], 2) == -1
assert min_k_bit_flips([0, 0, 0, 1, 0, 1, 1, 0], 3) == 3
assert min_k_bit_flips([1, 1, 1], 2) == 0
assert min_k_bit_flips([0], 1) == 1
assert min_k_bit_flips([0, 0], 2) == 1
for _ in range(400):
    n = random.randint(1, 9)
    arr = [random.randint(0, 1) for _ in range(n)]
    kk = random.randint(1, n)
    expect = brute(arr, kk)
    assert min_k_bit_flips(arr, kk) == expect
    assert min_k_bit_flips_inplace(arr[:], kk) == expect
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)，每個位置做常數次操作。空間：`flip` 陣列 O(n)；in-place 版本 O(1) 額外空間，但會修改輸入，面試時要先徵得同意或說明。也可以用一個 deque 存「作用中翻轉的起點」，空間 O(k)。邊界情況：k = 1 時每個 0 自己翻，答案就是 0 的個數；k = n 時只有一個可能的翻轉，陣列必須全 0（翻一次）或全 1（不翻）；已經全 1 時回傳 0；`i + k > n` 的檢查要在**決定要翻**時才做，不能在迴圈開頭就中斷，因為最後 k − 1 個位置若不需要翻是合法的。

### Follow-up

> [!question]- F1. 如果還要回傳每次翻轉的起點，而且要求額外空間 O(1)（不含輸出）？
> 在 in-place 版本中，每次決定翻轉時把 i 加入輸出串列即可；輸出串列本身是答案，不算額外空間。in-place 標記的原理是：`nums[i]` 原本只用最低位元，加 2 不影響 `nums[i] & 1`，而之後走到 `i + k` 時只要檢查 `nums[i] >= 2` 就知道 i 曾開始翻轉。結束後若要還原輸入，再掃一次把 `>= 2` 的減 2，並依翻轉次數的奇偶計算新值。時間仍是 O(n)。

> [!question]- F2. 如果每次只能翻轉長度 3（3191 題），或者每次翻轉「從 i 到結尾」的整個後綴（3192 題）？
> 長度 3 是本題 k = 3 的特例，可以直接模擬，因為 k 是常數，O(n · 3) 已經是線性。後綴翻轉時，位置 i 被所有起點 ≤ i 的翻轉影響，不需要窗口，只要記錄目前翻轉總次數的奇偶 `parity`：`nums[i] ^ parity == 0` 時翻一次、`parity ^= 1`。答案恰好是「相鄰元素不同」的位置數，加上第一個元素是否為 0，O(n) 時間、O(1) 空間。比較這三題可以看出：窗口長度決定了「作用中的操作」要記多久。

> [!question]- F3. 如果改成二維：按一個格子會翻轉它和上下左右四個鄰居，要把整個 m × n 網格變成全 0（1284 題的一般化，Lights Out）？
> 一維的「位置 0 只被一個操作影響」在二維中變成：若第一列每個格子要不要按已經決定，那麼第 r 列第 c 格要不要按，就由第 r − 1 列第 c 格目前的狀態唯一決定（只有正下方的按鈕還能改變它）。所以只要列舉第一列的 2ⁿ 種按法，其餘每列都被逼出來，最後檢查最後一列是否全 0。時間 O(2ⁿ · m · n)，適合 n 很小的情況（取較短的一邊當 n）。這正是本題「解是被逼出來的」觀察的推廣。

> [!question]- F4. 如果操作改成「把長度 k 的一段全部設為 1」（不是翻轉），最少幾次？
> 設為 1 不會把 1 變回 0，所以不需要追蹤奇偶。貪婪：找到最左邊的 0（位置 i），從 `min(i, n − k)` 開始設一段（若 i + k > n，就讓這段靠右對齊，仍然能蓋住 i），然後從這段的結尾之後繼續找下一個 0。被蓋住的位置不必再看，所以是 O(n)。這個貪婪的正確性理由和本題類似：最左邊的 0 一定要被某段蓋住，而在所有能蓋住它的段中，越靠右的段蓋住的未來位置越多（第 20 章 Greedy 的交換論證）。

### 心得

關鍵突破有兩個：翻轉可交換且自己是自己的反操作，所以最左邊的位置被唯一決定，貪婪就是唯一解；再用一個長度 k 的窗口記錄「作用中的翻轉數」，把每次 O(k) 的區間修改換成 O(1) 的開始與結束記號。這題的窗口不是在找子陣列，而是在維護「影響目前位置的操作」，這是 sliding window 與 difference array（第 7 章）的交界。面試時先說清楚「為什麼不用搜尋」（解是被逼出來的），再從 O(n · k) 的模擬出發，指出瓶頸是重複修改同一段，最後引入 `active`；用範例 3 走一次「兩個翻轉作用時等於沒翻」，能讓面試官確認你理解奇偶的處理。

## 難題 5｜2302. Count Subarrays With Score Less Than K｜Hard

### 題目

一個陣列的「分數」定義為它的元素和乘以它的長度，例如 `[1, 2, 3, 4, 5]` 的分數是 `15 × 5 = 75`。給一個**正整數**陣列 `nums` 和整數 `k`，回傳分數**嚴格小於** `k` 的非空連續子陣列個數。限制：`1 <= len(nums) <= 10⁵`，`1 <= nums[i] <= 10⁵`，`1 <= k <= 10¹⁵`。

- 範例 1：`nums = [2, 1, 4, 3, 5]`、`k = 10`，回傳 `6`：`[2]`（2）、`[1]`（1）、`[4]`（4）、`[3]`（3）、`[5]`（5）、`[2, 1]`（6）；`[1, 4]` 的分數是 10，不嚴格小於 10。
- 範例 2：`nums = [1, 1, 1]`、`k = 5`，回傳 `5`：三個 `[1]`（1）與兩個 `[1, 1]`（4）；`[1, 1, 1]` 的分數是 9。
- 範例 3（邊界）：`nums = [3]`、`k = 1`，回傳 `0`，任何分數都至少是 1。
- 範例 4（邊界）：`nums = [1, 2]`、`k = 10¹⁵`，回傳 `3`，所有子陣列都合法。

### 提示

> [!tip]- 提示 1
> 分數是兩個量的乘積，不能拆成「每個元素各貢獻多少」。但是當子陣列縮小時，這兩個量各自怎麼變化？

> [!tip]- 提示 2
> 元素為正，所以縮小子陣列時和變小、長度也變小，乘積一定變小。這代表「分數 < k」縮小保持合法。

> [!tip]- 提示 3
> 套模板 D：加入 `nums[right]` 後，只要 `total × (right − left + 1) >= k` 就收縮；之後以 right 結尾的合法子陣列有 `right − left + 1` 個。

### 詳解

**為什麼直覺做法不行**。暴力解列舉所有子陣列，用 prefix sum 算和，O(n²)，n = 10⁵ 時約 5 × 10⁹。這題容易讓人卡住的原因是分數的形狀：它不是一個能「加入加、移出減」的量，`sum × len` 在加入一個元素後同時改變兩個因子。很多人因此以為不能用 sliding window，轉而去想 DP 或更複雜的結構。

**突破點：單調性不需要可加性**。Sliding window 需要的不是窗口狀態可以相減，而是兩件事：合法性對收縮單調，以及能在 O(1) 內從窗口狀態算出合法性。第一件：若 `[l, r]` 合法，把它縮成 `[l', r']`，和因為元素為正而變小（或不變），長度變小，兩個非負因子都不增，乘積不增，仍然 < k。第二件：維護窗口的 `total`（可以加減）與長度 `right − left + 1`，分數就是兩者相乘，O(1)。所以分數本身不需要被維護，只要維護能算出它的零件。

**計數與正確性**。由單調性，以 `right` 結尾的合法起點是一段後綴 `[left, right]`；而 `right` 往右時，同一個起點的分數只會變大，所以最左合法起點 `left` 只會往右。這就是模板 D：收縮到合法後加上 `right − left + 1`。若加入 `nums[right]` 後連單一元素都不合法（`nums[right] >= k`），收縮會讓 `left = right + 1`、`total = 0`，加上 0，正確。每個子陣列只在自己的右端點被算到一次，所以總和就是答案。

```text
nums = [2, 1, 4, 3, 5]，k = 10
right  加入  收縮前窗口      分數         收縮                     窗口      個數  累計
  0     2    [2]            2×1 = 2      -                        [2]        1     1
  1     1    [2 1]          3×2 = 6      -                        [2 1]      2     3
  2     4    [2 1 4]        7×3 = 21     丟 2 → [1 4] 5×2 = 10    [4]        1     4
                                         丟 1 → [4]   4×1 = 4
  3     3    [4 3]          7×2 = 14     丟 4 → [3]   3×1 = 3     [3]        1     5
  4     5    [3 5]          8×2 = 16     丟 3 → [5]   5×1 = 5     [5]        1     6
結果 6
```

`right = 2` 時連續收縮了兩次：丟掉 2 之後分數 10 仍然不 < 10（題目是嚴格小於），要再丟掉 1。這裡的收縮條件是 `>= k`，寫成 `> k` 就會多算 `[1, 4]`。

### 解法

```python
import random


def count_subarrays(nums: list[int], k: int) -> int:
    left = total = count = 0
    for right, x in enumerate(nums):
        total += x
        while total * (right - left + 1) >= k:
            total -= nums[left]
            left += 1
        count += right - left + 1
    return count


def count_subarrays_bisect(nums: list[int], k: int) -> int:
    """O(n log n)：對每個 right，二分搜尋第一個合法的 left。"""
    prefix = [0]
    for x in nums:
        prefix.append(prefix[-1] + x)
    count = 0
    for right in range(len(nums)):
        lo, hi = 0, right + 1                       # 在 [0, right + 1) 找第一個合法的 left
        while lo < hi:
            mid = (lo + hi) // 2
            if (prefix[right + 1] - prefix[mid]) * (right - mid + 1) < k:
                hi = mid
            else:
                lo = mid + 1
        count += right + 1 - lo                     # lo == right + 1 代表沒有合法起點
    return count


def brute(nums, k):
    n = len(nums)
    return sum(sum(nums[i:j]) * (j - i) < k for i in range(n) for j in range(i + 1, n + 1))


assert count_subarrays([2, 1, 4, 3, 5], 10) == 6
assert count_subarrays([1, 1, 1], 5) == 5
assert count_subarrays([3], 1) == 0
assert count_subarrays([1, 2], 10**15) == 3
assert count_subarrays([10**5] * 4, 10**15) == 10   # 大數相乘，Python 整數不會溢位
for _ in range(500):
    arr = [random.randint(1, 6) for _ in range(random.randint(1, 10))]
    kk = random.randint(1, 120)
    assert count_subarrays(arr, kk) == count_subarrays_bisect(arr, kk) == brute(arr, kk)
print("all tests passed")
```

### 複雜度與邊界

Sliding window 版本時間 O(n)、空間 O(1)；二分版本時間 O(n log n)、空間 O(n)，它依賴「分數對起點單調」，同樣是單調性的另一種用法。邊界情況：k = 1 時沒有任何子陣列合法，每一步 `left` 都跑到 `right + 1`，加 0；單一元素 ≥ k 時同理，窗口清空後 `total` 回到 0，下一步重新開始；最大分數約 `10⁵ × 10⁵ × 10⁵ = 10¹⁵`，在 Java／C++ 必須用 64 位元整數，Python 沒有溢位問題；答案最多約 5 × 10⁹，同樣要用 64 位元。收縮條件 `>= k` 對應題目的「嚴格小於」。

### Follow-up

> [!question]- F1. 如果分數改成「最大值 × 長度」呢？或者「和 × 最小值」？
> 「最大值 × 長度」在縮小時兩個因子都不增，仍然單調，可以用 sliding window；但最大值不能相減，要用難題 2 的 monotonic deque 維護窗口最大值，收縮時若隊首索引 `< left` 就彈出，時間 O(n)。「和 × 最小值」則不單調：縮小時和變小，最小值卻可能變大，例如 `[1, 10, 10]` 的分數是 21，縮成 `[10, 10]` 卻是 200。這時 sliding window 失效，類似的 1856 題（Maximum Subarray Min-Product）要改用 monotonic stack 找每個元素作為最小值的最大範圍，見第 10 章。

> [!question]- F2. 如果要找分數 < k 的最長子陣列，或分數 ≥ k 的最短子陣列？
> 單調性相同，只是換模板。最長合法子陣列用模板 A：收縮到合法後用 `right − left + 1` 更新最大值。分數 ≥ k 放大保持合法，最短用模板 B：合法時記錄長度並收縮。兩者都是 O(n)。若要計數「分數 ≥ k」的子陣列，可以用總數 `n(n+1)/2` 減去本題答案，或直接在模板 B 的收縮後加上 `left`（起點 0 … left − 1 都合法）。

> [!question]- F3. 如果 nums 可以包含 0，或包含負數呢？
> 包含 0 時仍然正確：縮小時和不增（丟掉的是非負數），長度變小，乘積不增，單調性成立，程式不用改。包含負數時單調性被破壞，例如 `[−5, 3]` 的分數是 −4，縮成 `[3]` 卻是 3；而且「和 × 長度」在和為負時，越長分數越小，合法起點不再是一段後綴。沒有通用的線性解，n 小時用 prefix sum 加 O(n²) 列舉；面試時能指出「正數」是本題的必要條件，並舉出反例，就是好的回答。

> [!question]- F4. 如果只計算長度在 [L, R] 之間、分數 < k 的子陣列呢？
> 單調窗口不變，仍然維護最左合法起點 `left`；以 `right` 結尾的子陣列中，長度限制要求起點落在 `[right − R + 1, right − L + 1]`。兩個限制取交集：起點範圍是 `[max(left, right − R + 1), right − L + 1]`，個數是 `max(0, (right − L + 1) − max(left, right − R + 1) + 1)`。每個 right 仍是 O(1)，總時間 O(n)。這種「單調窗口再與固定長度限制取交集」的寫法，也能用在難題 3 的「恰好 k 種且長度至少 L」等變形。

### 心得

關鍵突破是：sliding window 需要的是合法性的單調性，而不是窗口狀態可以相減；只要維護能 O(1) 算出合法性的零件（這裡是和與長度），乘積這種非線性分數也能滑。它和難題 3 一樣用「以 right 結尾有 right − left + 1 個」來計數，也和核心題 2 一樣依賴「元素為正」來保證單調。面試時先證明「縮小時兩個因子都不增」，再寫模板 D，並指出嚴格小於對應 `>= k` 的收縮條件；被追問時，用 F1 的「和 × 最小值」反例說明哪些分數不能滑，能展示你真正理解這個 pattern 的邊界。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 最長合法窗口 | 「最長」且條件縮小保持合法（無重複、最多 k 種、和 ≤ limit） | 模板 A：不合法就收縮，收縮後更新答案 | 核心題 1（3）、核心題 3（424）、340、904 Fruit Into Baskets、1004 |
| 最短合法窗口 | 「最短」且條件放大保持合法（和 ≥ target、涵蓋 t） | 模板 B：合法時記錄並收縮 | 核心題 2（209）、難題 1（76）、1234 Replace the Substring for Balanced String |
| 固定長度窗口 | 「每個長度 k 的窗口」「排列」「anagram」 | 模板 C：進一個、出一個；`matches` 或 `need` 計數 | 核心題 4（567）、核心題 5（438）、643、1456、30（第 4 章難題 2） |
| 計數：最多型 | 「有幾個子陣列滿足 ≤／<」 | 模板 D：每個 right 加 `right − left + 1` | 難題 5（2302）、713 Subarray Product Less Than K |
| 計數：恰好型 | 「恰好 k 種」「恰好和為 goal」 | atMost(k) − atMost(k − 1)，或兩個左指標 | 難題 3（992）、930、1248 |
| 計數：至少型 | 「至少涵蓋」「至少 k 種」 | 收縮到不合法後加 `left` | 核心題 5 的 F2、1358 |
| 窗口極值 | 窗口最大／最小值，不能相減 | monotonic deque，存索引、值單調 | 難題 2（239）、1438、1696 Jump Game VI |
| 窗口中位數 | 窗口中位數或第 k 小 | 兩個 heap + lazy deletion | 480（第 14 章難題 2） |
| 作用範圍窗口 | 每個操作影響接下來 k 個位置 | 記錄作用中的操作數，過期時扣除 | 難題 4（995）、1109 Corporate Flight Bookings（差分陣列） |
| 不單調 → 換方法 | 有負數、和要恰好等於 k、和 × 最小值 | prefix sum + hash、prefix sum + deque、monotonic stack | 560（第 7 章核心題 2）、862（第 7 章難題 3）、1856（第 10 章） |

**下限與上限**。最簡單的形式是固定長度窗口加上可以直接相減的狀態，例如 643 Maximum Average Subarray，只考「進一個、出一個」的寫法；下一層是可變長度的模板 A 與模板 B，考的是單調性的判斷與答案更新的位置（核心題 1、2）。中間層的難點轉到**窗口狀態的設計**：424 要看出「長度 − 最多字元次數」並理解過時的 `maxf` 為何無害，567、438、76 要用一個整數（`matches`、`missing`）把計數表的比較變成 O(1)。上限的題目難在三種地方：第一，**條件本身不單調**，要先改寫，例如 992 把「恰好」拆成兩個「最多」，或把不單調的條件轉成固定長度；第二，**狀態不能相減**，需要額外的資料結構，例如 239 的 monotonic deque、480 的兩個 heap；第三，**窗口不是答案而是工具**，例如 995 的窗口維護的是「作用中的翻轉」，真正的難點是先證明貪婪是唯一解。

**與其他 pattern 的關係**。Sliding window 是 two pointers（第 5 章）的一種：兩個指標同向移動、夾出一個區間，而第 5 章的相向 two pointers 通常用在排序陣列上。和 prefix sum（第 7 章）的分界最重要：元素非負、條件單調時用 sliding window（O(1) 空間）；有負數或要求「恰好等於」時用 prefix sum 加 hash map 或 monotonic deque。和 binary search（第 8 章）也常是同一題的兩種解：209 與 2302 都能對每個右端點二分左端點，O(n log n)；而「最長窗口」的長度本身也對可行性單調，可以二分長度，再用固定窗口檢查（核心題 3 的 F4）。Monotonic deque 和第 10 章的 monotonic stack 是同一個「丟掉被支配的候選」的想法，差別只在 deque 還要從隊首移除過期元素。字串題中，固定窗口加上 rolling hash（第 25 章）能把「窗口內容是否等於某個字串」也變成 O(1) 判斷。

**容易混淆之處**。第一，「子序列」不是子陣列：題目一旦允許跳過元素（例如 727 Minimum Window Subsequence、最長遞增子序列），窗口的單調性就不成立，要改用 DP（第 21–22 章）或貪婪配對。第二，「最長」與「最短」的模板只差答案更新的位置，但混用就會出錯：最長在 `while` 之後、最短在 `while` 之內。第三，計數時單一窗口只能代表「一個端點」，若合法起點是一整段，就要用 `right − left + 1`（最多型）、`left`（至少型）或兩個左指標（恰好型）計數，不能只在合法時加一。第四，看到「連續子陣列」不代表一定是 sliding window：最大子陣列和（53 題）是 DP（Kadane），因為「和最大」不是一個能判斷合法與否的條件。

## 本章重點整理

- Sliding window 的本質是單調性：若合法窗口縮小後仍合法（或不合法窗口放大後仍不合法），每個右端點最好的左端點只會往右，兩個指標都不回頭，總共 O(n)。
- 動手前先回答兩個問題：窗口狀態是什麼、如何 O(1) 加入與移出；合法性是否對收縮單調。後者不成立（負數、「恰好」）時，換成 prefix sum 或拆成兩個 atMost。
- 四個模板：A 最長（不合法就收縮，之後更新）、B 最短（合法時更新並收縮）、C 固定長度（進一個、出一個）、D 計數（每個 right 加 `right − left + 1`）。
- 最長與最短的唯一差別是答案在 `while` 之後還是之內更新；這是最常見的錯誤來源。
- 3 題的跳躍寫法要用 `max(left, last[c] + 1)`，`"abba"` 是必測的邊界。
- 424 題的合法條件是「長度 − 最多字元次數 ≤ k」；`maxf` 只增不減仍正確，因為窗口長度從不縮小，只有真實的新最大次數才能讓窗口變長；最後的窗口本身不一定合法。
- 固定窗口比較計數時，用 `matches`（相等的字母數）或 `need` 加 `missing` 把 O(Σ) 的比較降成 O(1)；76 題的 `need` 允許變負，自然處理了重複與無關字元。
- 「恰好 k」= atMost(k) − atMost(k − 1)；以 right 結尾的合法起點是一整段，單一窗口只能代表一個端點。
- 窗口最大值不能相減，用存索引、值嚴格遞減的 monotonic deque，每個元素進出各一次；中位數則要兩個 heap（第 14 章）。
- 995 題的窗口維護的是「作用中的操作」：最左邊的位置被唯一決定，貪婪就是唯一解，再用差分的方式讓每次區間翻轉 O(1)。
- 合法性的判斷不需要可加：2302 題的「和 × 長度」只要維護和與長度兩個零件，就能在 O(1) 內判斷。
- 面試時主動說明單調性的理由（「元素為正，所以縮小時和不增」），並用負數或「和 × 最小值」這類反例說明方法的邊界，這比寫出模板本身更能展示理解。
