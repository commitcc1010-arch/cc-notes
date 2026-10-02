---
chapter: 10
title: Stack 與 Monotonic Stack
part: 1
---

# 第 10 章　Stack 與 Monotonic Stack

> [!abstract] 本章地圖
> **一句話**：stack（堆疊）讓你隨時處理「最近一個還沒解決的東西」；當這些待解決的元素依大小排好隊（monotonic stack，單調堆疊），每個元素只進出一次，就能在 O(n) 內替每個位置找到左右兩側第一個比它大或小的元素。
>
> **辨識訊號**：
> - 括號、標籤、巢狀結構的配對與驗證，「最近打開的要最先關上」
> - 運算式求值、反向波蘭表示法、帶括號的計算機、需要「暫存外層狀態、先算內層」
> - 「下一個更大／更小」「往右第一個比它高的」「還要等幾天」
> - 「以 nums[i] 為最小值（或最大值）的區間能延伸多遠」「所有子陣列的最小值總和」
> - 直方圖、矩形面積、「被兩側較矮的柱子擋住」
> - 設計題要求 push、pop 之外再 O(1) 回答某個彙總值（最小值、最大值）
>
> **核心題**：20、155、150、739、503
>
> **難題**：84、85、32、224、907

## 10.1 這個 Pattern 解決什麼問題

先看一個最小的例子。一排人由左到右站好，身高是 `[5, 3, 1, 4, 6]`，每個人往右看，想知道「右邊第一個比我高的人是誰」。暴力解是每個人往右一個一個找，最差要找完整排（例如身高遞減時，每個人都找不到），總共 O(n²)。浪費在哪裡？身高 3 的人往右找時看過了 1，身高 5 的人往右找時又看了一次 1；可是 1 被 3 擋在前面、又比 3 矮，對 3 左邊的人來說，1 根本不可能是答案。

換個角度：從左往右走，把「還沒找到答案的人」放在一旁排隊。新來的人身高是 x，所有排在隊伍裡、比 x 矮的人，答案就是 x，可以直接讓他們離開；離開之後，隊伍裡剩下的人都比 x 高或一樣高，x 自己也加入隊伍。這個隊伍有兩個特性：第一，最後加入的人最先被解決（因為他離 x 最近），所以它是一個 stack；第二，隊伍裡的身高從底到頂一定是非遞增的，因為比新人矮的都已經被彈出了。這就是 monotonic stack（單調堆疊）。

為什麼這樣是 O(n)？每個人恰好被 push 一次，最多被 pop 一次，所以整個過程中 while 迴圈的總次數不超過 n，這是 amortized（攤銷）分析：單一步可能一次彈出很多人，但總量有上限。我們省下的工作，正是暴力解中「重複看那些被擋住的人」。

stack 的另一大用途是巢狀結構。括號 `{[()]}`、運算式 `1 - (4 + 5 - (3 - 2))`、HTML 標籤，都有「最近打開的要最先關上」的性質。遇到開頭就把外層的狀態壓進 stack，處理內層；遇到結尾就把外層狀態彈出來，把內層的結果合併回去。這和遞迴是同一件事，只是把系統的呼叫堆疊換成自己管理的 stack，好處是不怕遞迴深度限制，也更容易在中途檢查狀態。

本章把兩種用法放在一起，是因為它們的共同核心都是：**stack 頂端永遠是「最近一個還沒處理完的東西」**。前者「沒處理完」是指還沒遇到更大的元素，後者是指括號還沒關上。只要題目的答案取決於「最近一個尚未解決的元素」，就該想到 stack。

## 10.2 辨識訊號

| 題目特徵 | 為什麼是 stack | 本章哪一題 |
|---|---|---|
| 括號、標籤是否正確配對 | 最近打開的必須最先關上，正好是 LIFO（後進先出） | 核心題 1（20） |
| 設計 stack 並 O(1) 回答最小值 | 最小值只隨頂端改變，可以把「到這一層為止的最小值」一起存 | 核心題 2（155） |
| 後序（RPN）運算式求值 | 運算子永遠作用在最近產生的兩個值上 | 核心題 3（150） |
| 「下一個更大」「還要等幾天」 | 等待答案的元素形成單調序列，新元素一次解決一批 | 核心題 4（739）、核心題 5（503） |
| 環狀陣列的下一個更大 | 走兩圈，第二圈只解決、不再加入 | 核心題 5（503） |
| 以某根柱子為高的最大矩形 | 寬度由左右第一根更矮的柱子決定 | 難題 1（84）、難題 2（85） |
| 最長合法括號子字串 | stack 底部記住「最後一個無法配對的位置」，作為長度的起點 | 難題 3（32） |
| 帶括號與負號的計算機 | 進入括號時保存外層的結果與正負號 | 難題 4（224） |
| 所有子陣列的最小值總和 | 每個元素是多少個子陣列的最小值，由左右第一個更小的位置決定 | 難題 5（907） |
| n 到 10⁵ 且需要「左右邊界」 | O(n²) 的往外擴展不可行，monotonic stack 一次求出所有邊界 | 84、907 |

一個實用的反向檢查：如果題目要的是「某個窗口內的最大值」，而窗口的左端會往右移動，那麼元素不只會從頂端離開，也會從底端過期，這時要用 monotonic deque（雙端佇列，第 6 章難題 2 的 239 題），不是單純的 stack。

## 10.3 模板與原理：Monotonic Stack

全書的 monotonic stack 只需要兩個方向的模板：**被彈出時得到答案**（求右邊第一個更大／更小），以及**彈完之後看頂端**（求左邊最近一個更大／更小）。stack 裡一律存索引而不是值，因為索引可以換算距離與寬度，值則隨時能用 `nums[i]` 讀到。

```python
import random


def next_greater(nums: list[int]) -> list[int]:
    """每個位置右邊第一個「嚴格更大」元素的索引；沒有則為 len(nums)。"""
    n = len(nums)
    ans = [n] * n
    stack: list[int] = []                 # 還沒找到答案的索引，值由底到頂非遞增
    for i, x in enumerate(nums):
        while stack and nums[stack[-1]] < x:
            ans[stack.pop()] = i          # x 就是它們在等的第一個更大元素
        stack.append(i)
    return ans                            # 留在 stack 裡的索引，右邊沒有更大的


def prev_smaller(nums: list[int]) -> list[int]:
    """每個位置左邊最近一個「嚴格更小」元素的索引；沒有則為 -1。"""
    ans = [-1] * len(nums)
    stack: list[int] = []                 # 值由底到頂嚴格遞增
    for i, x in enumerate(nums):
        while stack and nums[stack[-1]] >= x:
            stack.pop()                   # 被 x 擋住了，之後的人不可能再選它
        ans[i] = stack[-1] if stack else -1
        stack.append(i)
    return ans


def brute_next_greater(nums):
    n = len(nums)
    return [next((j for j in range(i + 1, n) if nums[j] > nums[i]), n) for i in range(n)]


def brute_prev_smaller(nums):
    return [next((j for j in range(i - 1, -1, -1) if nums[j] < nums[i]), -1) for i in range(len(nums))]


assert next_greater([5, 3, 1, 4, 6]) == [4, 3, 3, 4, 5]
assert prev_smaller([5, 3, 1, 4, 6]) == [-1, -1, -1, 2, 3]
assert next_greater([2, 2, 2]) == [3, 3, 3]          # 相等不算更大
assert prev_smaller([2, 2, 2]) == [-1, -1, -1]       # 相等不算更小
assert next_greater([]) == [] and prev_smaller([]) == []
for _ in range(500):
    arr = [random.randint(0, 5) for _ in range(random.randint(0, 10))]
    assert next_greater(arr) == brute_next_greater(arr)
    assert prev_smaller(arr) == brute_prev_smaller(arr)
print("all tests passed")
```

**Invariant（迴圈不變式）**。以 `next_greater` 為例，處理完第 i 個元素之後，stack 裡恰好是 `[0, i]` 中「右邊到 i 為止都還沒出現更大元素」的索引，而且由底到頂對應的值非遞增。第一條成立，是因為一個索引只有在遇到比它大的元素時才會被彈出，而彈出的那一刻就寫下了答案；第二條成立，是因為新元素 x 加入前，所有比 x 小的都已被彈出，剩下的都 ≥ x。這兩條合起來說明了 while 迴圈為什麼只需要看頂端：頂端是 stack 裡最小的值，如果連它都不比 x 小，下面的更不可能。

**每一行為什麼這樣寫**：

- `while` 而不是 `if`：一個新元素可能同時是很多人的答案，例如 `[5, 3, 1, 4]` 中的 4 一次解決了 1 和 3。
- `nums[stack[-1]] < x`（嚴格小於）：題目要「嚴格更大」，相等的元素不是答案，所以要留在 stack 裡繼續等。改成 `<=` 就變成「右邊第一個大於或等於」。比較符號決定了相等時誰解決誰，10.5 節會專門討論。
- 先 `while` 再 `append`：新元素要等它右邊的人來解決，所以一定要加入；而且必須在彈完之後加入，stack 才會維持單調。
- 留在 stack 裡的索引代表「找不到」，所以 `ans` 一開始就填好預設值（這裡用 n，方便之後計算寬度 `n - i`）。
- 總時間 O(n)：每個索引 push 一次、pop 至多一次，while 迴圈的總次數不超過 n。空間 O(n)，最差情況是輸入遞減，所有人都留在 stack 裡。

**兩個方向，一次走完**。`prev_smaller` 的寫法是「彈完之後看頂端」：被彈出的元素都 ≥ x，它們被 x 擋住了，對 x 右邊的人來說，x 比它們更近也更小，所以它們永遠不會再是任何人的「左邊最近更小」。彈完之後，頂端就是 x 左邊最近一個比 x 小的元素。注意同一個迴圈其實同時算出了兩件事：x 彈出索引 j 的那一刻，x 是 j 的「右邊第一個 ≤ 它」的元素；彈完之後的頂端是 x 的「左邊最近 < 它」的元素。難題 1（84）和難題 5（907）都直接利用這一點，在一次掃描中同時得到左右邊界。

**選哪一種單調**。口訣是：**要找更大的，stack 就維持遞減；要找更小的，stack 就維持遞增**。理由是被找的東西會把比它「差」的元素彈掉：找更大時，新來的大元素把比它小的彈掉，剩下的自然遞減。方向（從左往右或從右往左掃）則可以互換：從右往左掃時，「彈完之後看頂端」得到的是右邊最近的更大／更小，核心題 4 會示範兩種寫法。

## 10.4 Stack 的三種用法

本章十題可以分成三個家族，辨識時先問自己題目屬於哪一種：

| 家族 | stack 裡放什麼 | 什麼時候 pop | 本章題目 |
|---|---|---|---|
| 配對與巢狀 | 還沒關上的開頭（括號、位置、外層狀態） | 遇到對應的結尾 | 20、32、224 |
| 延後計算 | 還沒被使用的運算元或部分結果 | 遇到需要它們的運算子 | 150、224、155（彙總值） |
| 單調 stack | 還沒找到答案的索引，值保持單調 | 遇到能解決它們的新元素 | 739、503、84、85、907 |

**配對與巢狀**。stack 的大小就是目前的巢狀深度，頂端是最內層。關鍵是想清楚「關上時要合併什麼」：20 題只要確認型別一致；32 題要用位置算長度，所以 stack 裡放索引；224 題要把括號內的結果乘上括號前的正負號再加回外層，所以進入括號時要保存外層的 `(result, sign)`。這類題目和遞迴等價，遞迴版本通常更好寫，但巢狀深度可達 10⁵ 時，Python 預設的遞迴上限（約 1000）會讓遞迴版本直接失敗，這時顯式的 stack 是必要的。

**延後計算**。後序運算式 `2 1 + 3 *` 中，看到 `+` 時才知道要把前面兩個數加起來，所以數字先放進 stack 等待。155 題的 Min Stack 也是這一族：每一層存「到這一層為止的最小值」，pop 時舊的最小值自動回來，因為 stack 只會從頂端改變，下面每一層的彙總值永遠不會失效。這個「彙總值跟著層數存」的技巧可以推廣到任何能從前一層 O(1) 算出的值，例如最大值、總和、gcd。

**單調 stack**。題目問的是每個位置的「邊界」：右邊第一個更大、左邊第一個更小、以它為最小值能延伸多遠。stack 裡的元素都在等答案，新元素一到就解決一批。難的不是模板本身，而是看出題目其實在問邊界：84 題要的是面積，但面積等於「高 × 寬」，寬由左右第一根更矮的柱子決定；907 題要的是總和，但總和可以拆成「每個元素當最小值的次數 × 它的值」，次數由左右第一個更小的位置決定。

```text
同一個陣列，三種單調 stack 的問法（nums = [3, 1, 4, 1, 5]）
index:            0  1  2  3  4
nums:             3  1  4  1  5
右邊第一個更大:    2  2  4  4  -     （stack 遞減，被彈出時記答案）
左邊最近更小:      -  -  1  -  3     （stack 遞增，彈完看頂端）
以 nums[i] 為最小值的最大區間（左右第一個嚴格更小之間）：
  i=0: [0,0]   i=1: [0,4]   i=2: [2,2]   i=3: [0,4]   i=4: [4,4]
  注意 i=1 和 i=3 的值都是 1，區間完全相同 → 907 題要處理重複計算
```

## 10.5 相等元素：嚴格與非嚴格怎麼選

monotonic stack 最常出錯的地方不是迴圈，而是 while 條件裡的 `<` 和 `<=`。它決定了相等元素之間「誰解決誰」，進而影響三件事：答案正不正確、會不會重複計算、stack 的單調性是嚴格還是非嚴格。

| while 條件（找右邊） | 被彈出的元素得到的答案 | stack 由底到頂 |
|---|---|---|
| `nums[top] < x` | 右邊第一個嚴格更大 | 非遞增（可以有相等） |
| `nums[top] <= x` | 右邊第一個大於或等於 | 嚴格遞減 |
| `nums[top] > x` | 右邊第一個嚴格更小 | 非遞減 |
| `nums[top] >= x` | 右邊第一個小於或等於 | 嚴格遞增 |

**題目明確要求時**照題目寫：739 題要「嚴格更暖」，所以相等的溫度不能解決彼此，條件是 `<`。**題目只要求極值時**（84 題的最大面積），兩種都能得到正確答案，只是某些柱子算出的寬度偏小，但同一組相等柱子中至少有一根會算出完整的寬度，最大值不受影響，難題 1 會說明理由。**題目要求計數或總和時**（907 題），左右兩側必須一邊嚴格、一邊非嚴格，否則相等元素會被重複計算或漏算。

```text
nums = [2, 2]，三個子陣列 [2]、[2]、[2, 2]，最小值總和 = 6
左右都用「嚴格更小」當邊界：
  i=0 的區間 [0,1]，左 1 種 × 右 2 種 = 2 個子陣列 → [2], [2,2]
  i=1 的區間 [0,1]，左 2 種 × 右 1 種 = 2 個子陣列 → [2], [2,2]
  [2,2] 被算了兩次，總和 8 ✗
左邊嚴格、右邊非嚴格（右邊界是第一個 <= 它的位置）：
  i=0 的右邊界停在 1，區間 [0,0]，1 個子陣列 → [2]
  i=1 的區間 [0,1]，左 2 種 × 右 1 種 = 2 個 → [2], [2,2]
  每個子陣列恰好被算一次（歸給最右邊的那個最小值），總和 6 ✓
```

規則可以這樣記：計數時，要替每個子陣列指定**唯一一個**負責的最小值，最常見的約定是「最右邊的那一個」或「最左邊的那一個」。左邊用嚴格、右邊用非嚴格，就是約定由最右邊的最小值負責；反過來就是由最左邊負責。兩者都對，只要兩邊不同。

## 10.6 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| stack 裡存值而不是索引 | 算不出距離、寬度，或重複值時分不清是哪一個 | 一律存索引，值用 `nums[i]` 讀 |
| 用 `if` 代替 `while` | 一個新元素只解決一個等待者，答案錯一大片 | 新元素可能是很多人的答案，一定用 `while` |
| 單調方向反了 | 找更大卻維持遞增 stack，答案完全不對 | 「找更大 → 遞減，找更小 → 遞增」；寫之前畫三個數驗證 |
| 嚴格／非嚴格選錯 | 739 題相等溫度互相解決；907 題重複計算 | 先決定相等時誰解決誰；計數題左右一邊嚴格、一邊非嚴格 |
| 掃描結束後忘了處理 stack 裡剩下的 | 84 題遞增的柱子永遠沒被計算面積 | 在尾端加一個哨兵（高度 0），或迴圈後再清一次 stack |
| 寬度算錯 | 84 題面積少一格或多一格 | 被彈出的柱子寬度是 `i - stack[-1] - 1`，stack 為空時是 `i` |
| pop 空 stack | `IndexError`，例如 20 題輸入 `")"` | pop 前先檢查 `stack` 是否為空，或放一個哨兵在底部 |
| 運算元順序反了 | 150 題 `["4", "13", "5", "/", "+"]` 算出 4 而不是 6（把 13 / 5 算成 5 / 13） | 先彈出的是右運算元：`b = pop()`，`a = pop()`，算 `a op b` |
| 除法取整方向 | Python `-7 // 2 == -4`，題目要向零取整 `-3` | 用 `int(a / b)` 或先取絕對值再補號 |
| 括號內的負號沒有傳遞 | 224 題 `1 - (2 - 3)` 算成 -4 | 進入括號時保存外層 sign，離開時乘回去 |
| 遞迴解巢狀結構 | 深度 10⁵ 時 `RecursionError` | 用顯式 stack；或說明並提高遞迴上限的風險 |

## 核心題 1｜20. Valid Parentheses｜Easy

### 題目

給一個只包含 `(`、`)`、`[`、`]`、`{`、`}` 六種字元的字串 `s`，判斷它是否為合法的括號序列。合法的條件是：每個開括號都必須被**同類型**的閉括號關上；關上的順序必須正確，也就是較晚打開的必須較早關上；每個閉括號都要有一個對應的開括號。限制：`1 <= len(s) <= 10⁴`。

- 範例 1：`s = "()[]{}"`，回傳 `True`。
- 範例 2：`s = "{[()]}"`，回傳 `True`，三層巢狀，由內往外依序關上。
- 範例 3：`s = "([)]"`，回傳 `False`。每種括號的個數都對，但 `[` 比 `(` 晚打開，卻比它晚關上，順序錯了。
- 範例 4（邊界）：`s = "]"`，回傳 `False`，閉括號前面沒有任何開括號；`s = "(("`，回傳 `False`，結束時還有沒關上的開括號。

### 思路

暴力解是反覆刪除相鄰的配對：只要字串裡還有 `()`、`[]`、`{}` 就把它刪掉，直到刪不動為止，最後字串為空就合法。每一輪掃描 O(n)，最多刪 n/2 輪，總共 O(n²)。這個做法其實已經抓到正確的直覺：**最內層的配對一定是相鄰的**，刪掉它之後，外一層就變成相鄰。瓶頸在於每刪一對就要重新掃一次，我們重複檢查了很多早就確定無法配對的字元。

關鍵觀察：從左往右讀的時候，遇到閉括號，它唯一能配對的對象就是「最近一個還沒關上的開括號」。如果它要配對更早的開括號，中間那個較晚打開的就會被跨過，違反「較晚打開的較早關上」。所以把還沒關上的開括號依序放進 stack：遇到開括號就 push；遇到閉括號就看頂端，型別相同就 pop（配對成功），不同或 stack 為空就立刻回傳 False。讀完整個字串後，stack 必須是空的，否則有開括號沒被關上。

invariant 是：**處理完前綴 `s[:i]` 之後，stack 由底到頂恰好是這個前綴中尚未配對的開括號，依打開的順序排列**。頂端永遠是最內層。這等於把暴力解「刪除相鄰配對」的過程一次做完：每個閉括號到來時，頂端的開括號就是刪除完內層之後和它相鄰的那個字元。

```text
s = "{[()]}"
步驟  字元  動作                         stack（底 → 頂）
 1     {    開括號，push                  {
 2     [    開括號，push                  { [
 3     (    開括號，push                  { [ (
 4     )    頂端是 ( ，配對成功，pop       { [
 5     ]    頂端是 [ ，配對成功，pop       {
 6     }    頂端是 { ，配對成功，pop       （空）
結束  stack 為空 → True

s = "([)]"
步驟  字元  動作                         stack
 1     (    push                          (
 2     [    push                          ( [
 3     )    頂端是 [ ，和 ) 不同型別 → 回傳 False
```

第二個例子在第 3 步就停下來了：`)` 想配對的 `(` 被 `[` 擋住，而 `[` 還沒關上。暴力解在這個例子中找不到任何相鄰配對，也會得到 False，但 stack 版本只看了三個字元就確定答案，而且每個字元只被處理一次。

### 解法

```python
import random


def is_valid(s: str) -> bool:
    if len(s) % 2 == 1:                 # 奇數長度不可能全部配對，提早結束
        return False
    match = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []
    for ch in s:
        if ch in match:                 # 閉括號：必須和最近一個未關上的開括號同型別
            if not stack or stack[-1] != match[ch]:
                return False
            stack.pop()
        else:                           # 開括號：等待之後的閉括號
            stack.append(ch)
    return not stack                    # 還有沒關上的開括號就不合法


def brute(s: str) -> bool:
    prev = None
    while prev != s:
        prev = s
        s = s.replace("()", "").replace("[]", "").replace("{}", "")
    return s == ""


assert is_valid("()[]{}")
assert is_valid("{[()]}")
assert not is_valid("([)]")
assert not is_valid("]")
assert not is_valid("((")
assert not is_valid("){")
assert is_valid("([]{})[]")
for _ in range(2000):
    t = "".join(random.choice("()[]{}") for _ in range(random.randint(1, 10)))
    assert is_valid(t) == brute(t), t
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每個字元 push 或 pop 一次，字典查詢 O(1)。空間 O(n)：最差情況是全部都是開括號（例如 `"(((("`），全部留在 stack 裡；奇數長度的提早結束不影響最差情況，因為 `"(((("` 是偶數長度。邊界情況：只有閉括號時第一個字元就因為 stack 為空而回傳 False，這是 pop 前一定要檢查 `not stack` 的原因；只有開括號時迴圈正常結束，但 stack 非空；長度為 1 一定不合法。若題目允許空字串，迴圈不執行，回傳 True，符合「空序列是合法的」定義。

### Follow-up

> [!question]- F1. 如果只有一種括號 `(` 和 `)`，能不能做到 O(1) 空間？
> 可以。stack 裡只會有 `(`，所以只需要記住它的大小：用一個整數 `depth`，遇到 `(` 加一、遇到 `)` 減一，任何時刻 `depth < 0` 就回傳 False，結束時 `depth == 0` 才合法。時間 O(n)、空間 O(1)。這個做法在多種括號時不成立，因為計數器只記得「有幾個沒關上」，記不得「頂端是哪一種」，`"([)]"` 用三個計數器檢查會誤判為合法。

> [!question]- F2. 如果要回傳「最少要插入幾個括號才能變合法」（921. Minimum Add to Make Parentheses Valid）呢？
> 只有一種括號時，用 F1 的 `depth` 掃一次：遇到 `)` 而 `depth == 0` 時，這個 `)` 一定要在前面補一個 `(`，答案加一並維持 `depth = 0`；掃完後剩下的 `depth` 是沒關上的 `(`，每個都要補一個 `)`。答案是兩者之和，O(n) 時間、O(1) 空間。這個貪婪是最佳的，因為每一個「無法配對」的字元都至少需要一個插入，而上面的做法恰好替每個無法配對的字元插入一個。

> [!question]- F3. 如果要刪掉最少的括號，並回傳刪完之後的合法字串（1249. Minimum Remove to Make Valid Parentheses）呢？
> 字串裡還可能有字母。用 stack 存 `(` 的**索引**：遇到 `(` push 索引；遇到 `)` 時若 stack 非空就 pop（配對成功），否則把這個 `)` 的索引標記為刪除。掃完後 stack 裡剩下的索引是沒關上的 `(`，也全部標記刪除。最後把沒被標記的字元串起來。O(n) 時間與空間。這裡 stack 從存字元改成存索引，是因為我們需要知道「哪一個」括號沒配對，這和難題 3（32）的技巧相同。

> [!question]- F4. 如果字串裡還有萬用字元 `*`，可以當作 `(`、`)` 或空字串（678. Valid Parenthesis String）呢？
> 不必用 stack。維護「目前未關上的 `(` 個數」可能的範圍 `[lo, hi]`：遇到 `(` 兩者都加一；遇到 `)` 兩者都減一；遇到 `*` 時 `lo` 減一（當作 `)`）、`hi` 加一（當作 `(`）。`hi < 0` 代表就算所有 `*` 都當 `(` 也不夠，立刻回傳 False；`lo` 低於 0 時截成 0，因為未關上的數量不能是負的。結束時 `lo == 0` 就合法。O(n) 時間、O(1) 空間。另一種做法是兩個 stack 分別存 `(` 和 `*` 的索引，最後檢查每個剩下的 `(` 右邊都有一個 `*`，同樣 O(n)。

> [!question]- F5. 如果要像編譯器一樣，回報第一個錯誤的位置呢？
> 在原本的迴圈中，遇到不匹配的閉括號時回傳它的索引 i（「意外的閉括號」）；如果迴圈正常結束但 stack 非空，錯誤是「未關上的開括號」，應該回報 stack **底部**那個開括號的位置，因為它是最早打開、最外層沒關上的，所以 stack 要改存 `(字元, 索引)`。也可以回報頂端（最內層），這取決於錯誤訊息想指向哪裡；實務上兩者都會列出。時間仍是 O(n)。

## 核心題 2｜155. Min Stack｜Medium

### 題目

設計一個 stack 類別 `MinStack`，支援四個操作，**每個都要 O(1) 時間**：`push(val)` 把 val 放到頂端；`pop()` 移除頂端元素；`top()` 回傳頂端元素；`getMin()` 回傳目前 stack 中的最小值。題目保證 `pop`、`top`、`getMin` 只會在 stack 非空時被呼叫。限制：值在 `-2³¹` 到 `2³¹ − 1` 之間，總操作數最多 3 × 10⁴。

- 範例 1：依序 `push(-2)`、`push(0)`、`push(-3)`，`getMin()` 回傳 `-3`；`pop()` 之後，`top()` 回傳 `0`，`getMin()` 回傳 `-2`。
- 範例 2：依序 `push(5)`、`push(5)`、`push(7)`，`getMin()` 回傳 `5`；`pop()`、`pop()` 之後 `getMin()` 仍是 `5`（重複的最小值要正確處理）。
- 範例 3（邊界）：只 `push(2³¹ − 1)` 一個元素，`top()` 與 `getMin()` 都回傳 `2147483647`。

### 思路

暴力解是用普通的 list 當 stack，`getMin()` 時掃一遍，O(n)。另一個直覺是用一個變數 `cur_min` 記住目前最小值，push 時更新很容易；問題出在 pop：如果被彈出的剛好是最小值，新的最小值是誰？這時只能重新掃描，又回到 O(n)。用 heap 或排序結構可以把最小值的維護降到 O(log n)，但仍不是 O(1)，而且大材小用。

關鍵觀察：stack 只會在頂端改變，所以**任何時刻，第 k 層以下的元素集合，就是當初第 k 層被 push 時下面的那些元素**。換句話說，「從底部到第 k 層的最小值」一旦算出來就永遠不會失效，因為第 k 層以下的內容在第 k 層被彈出之前不會改變。於是每一層除了存值，也存「到這一層為止的最小值」：push 時新的最小值是 `min(val, 下一層的最小值)`，O(1)；pop 時把這一層連同它的最小值一起丟掉，下一層存的最小值剛好就是 pop 之後的答案。

invariant：**`stack[k] = (值, stack[0..k] 中的最小值)`**。push 維持它是因為新的前綴最小值只取決於舊的前綴最小值和新值；pop 維持它是因為剩下的每一層都沒被動過。這是 10.4 節「延後計算」家族的典型：彙總值跟著層數存。

```text
操作序列：push(-2), push(0), push(-3), getMin, pop, top, getMin
stack 存 (值, 到這層為止的最小值)，左邊是底

push(-2)  [(-2,-2)]
push(0)   [(-2,-2), (0,-2)]              min(0, -2) = -2
push(-3)  [(-2,-2), (0,-2), (-3,-3)]     min(-3, -2) = -3
getMin    頂端的第二欄 → -3
pop       [(-2,-2), (0,-2)]              丟掉 (-3,-3)，最小值自動回到 -2
top       頂端的第一欄 → 0
getMin    頂端的第二欄 → -2
```

第 5 步 pop 掉 -3 之後，我們不需要重新找最小值，因為 `(0, -2)` 這一層在被 push 的時候就已經記下了「當時」的最小值 -2，而從那時到現在，它下面的內容沒有改變過。

另一種常見的寫法是用兩個 stack：主 stack 存所有值，min stack 只在 `val <= 目前最小值` 時才 push；pop 時如果彈出的值等於 min stack 的頂端，就一起彈出。這樣在大部分元素都不是新最小值時能省空間。注意條件必須是 `<=` 而不是 `<`：範例 2 中兩個 5 都要進 min stack，否則 pop 掉第二個 5 時會把唯一的 5 從 min stack 彈出，最小值就錯了。

### 解法

```python
import random


class MinStack:
    """每一層存 (值, 到這一層為止的最小值)。"""

    def __init__(self) -> None:
        self.stack: list[tuple[int, int]] = []

    def push(self, val: int) -> None:
        cur_min = min(val, self.stack[-1][1]) if self.stack else val
        self.stack.append((val, cur_min))

    def pop(self) -> None:
        self.stack.pop()

    def top(self) -> int:
        return self.stack[-1][0]

    def getMin(self) -> int:
        return self.stack[-1][1]


class MinStackTwo:
    """主 stack 存全部的值，min stack 只存「新的或相等的最小值」。"""

    def __init__(self) -> None:
        self.data: list[int] = []
        self.mins: list[int] = []

    def push(self, val: int) -> None:
        self.data.append(val)
        if not self.mins or val <= self.mins[-1]:   # 相等也要 push，否則重複最小值會出錯
            self.mins.append(val)

    def pop(self) -> None:
        if self.data.pop() == self.mins[-1]:
            self.mins.pop()

    def top(self) -> int:
        return self.data[-1]

    def getMin(self) -> int:
        return self.mins[-1]


for cls in (MinStack, MinStackTwo):
    s = cls()
    s.push(-2); s.push(0); s.push(-3)
    assert s.getMin() == -3
    s.pop()
    assert s.top() == 0 and s.getMin() == -2
    t = cls()
    t.push(5); t.push(5); t.push(7)
    assert t.getMin() == 5
    t.pop(); t.pop()
    assert t.getMin() == 5 and t.top() == 5        # 重複的最小值
    u = cls()
    u.push(2**31 - 1)
    assert u.top() == u.getMin() == 2**31 - 1
    for _ in range(300):                            # 隨機操作和 list + min() 比對
        st, ref = cls(), []
        for _ in range(40):
            if ref and random.random() < 0.4:
                st.pop(); ref.pop()
            else:
                v = random.randint(-5, 5)
                st.push(v); ref.append(v)
            if ref:
                assert st.top() == ref[-1] and st.getMin() == min(ref)
print("all tests passed")
```

### 複雜度與邊界

四個操作都是 O(1) 時間。空間：第一種寫法每層存兩個數，O(n)；第二種寫法 min stack 的大小介於 1 到 n 之間，輸入遞增時只有 1 層，輸入遞減時和主 stack 一樣大，最差仍是 O(n)，但常數較小。邊界情況：重複的最小值是第二種寫法最常見的 bug，push 條件必須是 `<=`；`2³¹ − 1` 和 `-2³¹` 在 Python 沒有溢位問題，在 Java 中如果用「差值編碼」（見 F1）就必須改用 `long`；題目保證不會對空 stack 呼叫 `pop` 或 `getMin`，面試時仍值得說一句「如果不保證，我會丟出例外」。

### Follow-up

> [!question]- F1. 能不能只用一個 stack，而且不額外為每一層存最小值（O(1) 額外空間）？
> 可以用差值編碼：只維護一個變數 `mn`，stack 裡存 `val - mn`（push 前的最小值）。push 時若差值為負，代表 val 是新的最小值，更新 `mn = val`。pop 時若彈出的差值 d 為負，代表被彈出的正是目前的最小值，而舊的最小值是 `mn - d`（因為 `d = val - 舊mn` 且 `val = mn`）。top 時若頂端差值為負，頂端就是 `mn`，否則是 `mn + d`。每個操作 O(1)，額外空間只有一個變數。代價是差值可能超出 32 位元（例如 `2³¹ − 1 − (−2³¹)`），在 Java／C++ 要用 64 位元整數。
> ```python
> class MinStackDiff:
>     def __init__(self):
>         self.s, self.mn = [], None
>     def push(self, x):
>         if not self.s:
>             self.s.append(0); self.mn = x
>         else:
>             d = x - self.mn
>             self.s.append(d)
>             if d < 0:
>                 self.mn = x
>     def pop(self):
>         d = self.s.pop()
>         if d < 0:
>             self.mn -= d          # 還原舊的最小值
>     def top(self):
>         d = self.s[-1]
>         return self.mn if d < 0 else self.mn + d
>     def getMin(self):
>         return self.mn
> ```

> [!question]- F2. 如果還要支援 popMax()，也就是刪除並回傳目前最大的元素（716. Max Stack）呢？
> 「每層存彙總值」的技巧在這裡失效，因為 popMax 會從 stack **中間**刪除元素，下面各層存的彙總值仍然正確，但上面各層的彙總值就錯了。常見解法有兩種：一是 heap 存 `(-值, -序號)` 加上 lazy deletion（延遲刪除），配合一個集合記錄已刪除的序號，pop 與 popMax 都是 amortized O(log n)；二是雙向 linked list 存 stack 順序，加上一個有序結構把值對應到節點，所有操作 O(log n)。這是第 27 章難題 3 的內容。重點是說出為什麼 O(1) 的寫法不再成立：刪除不再只發生在頂端。

> [!question]- F3. 如果要的是一個能 O(1) 回答最小值的 queue（佇列）呢？
> 用兩個 Min Stack 組成 queue：`push` 一律放進 in-stack；`pop` 時若 out-stack 為空，就把 in-stack 全部倒進 out-stack（順序反轉，變成先進先出），再從 out-stack 彈出。兩個 stack 各自維護「到這層為止的最小值」，queue 的最小值就是 `min(in 的最小值, out 的最小值)`。每個元素最多被搬一次，所以所有操作 amortized O(1)。這個結構可以直接解 sliding window minimum，但第 6 章難題 2（239）的 monotonic deque 更直接，兩者都是 O(n)。

> [!question]- F4. 如果還要支援 increment(k, val)：把底部 k 個元素都加上 val（1381. Design a Stack With Increment Operation）呢？
> 直接改 k 個元素是 O(k)。改用 lazy（延遲）陣列 `inc`：`increment(k, val)` 只做 `inc[min(k, size) - 1] += val`，代表「從這一層往下都要加 val」。pop 第 i 層時，回傳 `stack[i] + inc[i]`，並把 `inc[i]` 往下傳給 `inc[i - 1]`，再把 `inc[i]` 清零。每個操作 O(1)。若同時要 getMin，就不能再把最小值存死在每層：底部 k 層加上 val 之後，上面各層記錄的前綴最小值有的要跟著變、有的不用，無法 O(1) 修正。這時可以改用支援「區間加值、區間最小值」的 segment tree（線段樹），每個操作 O(log n)；面試中能說清楚 O(1) 寫法為什麼失效，比硬寫出來更重要。

## 核心題 3｜150. Evaluate Reverse Polish Notation｜Medium

### 題目

給一個字串陣列 `tokens`，代表一個用反向波蘭表示法（Reverse Polish Notation，RPN，也叫後序表示法）寫成的算術式，請計算它的值並回傳整數。在 RPN 中，運算子寫在兩個運算元**之後**，例如中序的 `(2 + 1) * 3` 寫成 `2 1 + 3 *`，因此不需要括號。每個 token 是 `+`、`-`、`*`、`/` 之一，或是一個整數（可能是負數，例如 `"-11"`）。除法是整數除法，**向零取整**（例如 `-7 / 2 = -3`）。保證輸入是合法的 RPN、不會除以零，所有中間結果與答案都在 32 位元整數範圍內。限制：`1 <= len(tokens) <= 10⁴`。

- 範例 1：`tokens = ["2", "1", "+", "3", "*"]`，即 `(2 + 1) * 3`，回傳 `9`。
- 範例 2：`tokens = ["4", "13", "5", "/", "+"]`，即 `4 + 13 / 5`，回傳 `6`（13 / 5 向零取整為 2）。
- 範例 3：`tokens = ["10", "6", "9", "3", "+", "-11", "*", "/", "*", "17", "+", "5", "+"]`，回傳 `22`。
- 範例 4（邊界）：`tokens = ["42"]`，只有一個數，回傳 `42`；`tokens = ["-7", "2", "/"]`，回傳 `-3` 而不是 `-4`。

### 思路

暴力解是反覆在陣列裡找「數、數、運算子」三個連續的 token，把它們換成計算結果，直到只剩一個數。每次找與替換都是 O(n)，總共 O(n²)。這個做法揭示了 RPN 的結構：**每個運算子都作用在它左邊最近的兩個「已經算好的值」上**。

既然運算子要的是「最近的兩個值」，就用 stack 保存已經算好、但還沒被使用的值：讀到數字就 push；讀到運算子就 pop 兩次，先彈出的是**右運算元** b、後彈出的是左運算元 a，算出 `a op b` 再 push 回去。讀完所有 token 後，stack 裡恰好剩下一個值，就是答案。invariant 是：**處理完前 i 個 token 後，stack 由底到頂是這段前綴中各個「已完成、尚未被使用的子運算式」的值，依出現順序排列**。運算子消耗兩個子運算式、產生一個，所以 stack 的大小變化是 +1（數字）或 −1（運算子）。

兩個細節最容易出錯。第一是運算元順序：減法和除法不可交換，`["4", "13", "5", "/", "+"]` 中先彈出的是 5，所以是 13 / 5 而不是 5 / 13。第二是向零取整：Python 的 `//` 是向下取整，`-7 // 2 == -4`，題目要的是 `-3`。可以寫 `int(a / b)`，在 32 位元範圍內浮點除法不會有誤差；更穩健的寫法是先用絕對值做整數除法、再補上正負號，完全不經過浮點數。另外，判斷 token 是不是運算子要用 `tok in ops`，不能用「第一個字元是不是 `-`」，因為 `"-11"` 是一個負數。

```text
tokens = ["4", "13", "5", "/", "+"]
步驟  token  動作                                stack（底 → 頂）
 1     4     數字，push                           4
 2     13    數字，push                           4 13
 3     5     數字，push                           4 13 5
 4     /     b = pop() = 5, a = pop() = 13        4
             13 / 5 = 2（向零取整），push          4 2
 5     +     b = 2, a = 4，4 + 2 = 6，push        6
結束  stack 只剩 6 → 回傳 6

範例 3 的關鍵段落（從 "+" 開始）：
stack: 10 6 9 3      讀 "+"   → 9 + 3 = 12        10 6 12
                     讀 "-11" → push              10 6 12 -11
                     讀 "*"   → 12 * -11 = -132   10 6 -132
                     讀 "/"   → 6 / -132 = 0      10 0     （向零取整，-0.045 → 0）
                     讀 "*"   → 10 * 0 = 0        0
                     讀 "17" "+" "5" "+"          → 22
```

範例 3 中 `6 / -132` 的結果是 -0.045…，向零取整是 0；若誤用 Python 的 `//` 會得到 -1，最後答案變成 12 而不是 22。這是面試時最值得主動手算一次的地方。

### 解法

```python
import operator
import random


def div_trunc(a: int, b: int) -> int:
    """整數除法，向零取整，不經過浮點數。"""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


OPS = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": div_trunc}


def eval_rpn(tokens: list[str]) -> int:
    stack: list[int] = []
    for tok in tokens:
        if tok in OPS:                  # 不能用 tok[0] == "-" 判斷，"-11" 是數字
            b = stack.pop()             # 先彈出的是右運算元
            a = stack.pop()
            stack.append(OPS[tok](a, b))
        else:
            stack.append(int(tok))
    return stack[-1]


assert eval_rpn(["2", "1", "+", "3", "*"]) == 9
assert eval_rpn(["4", "13", "5", "/", "+"]) == 6
assert eval_rpn(["10", "6", "9", "3", "+", "-11", "*", "/", "*", "17", "+", "5", "+"]) == 22
assert eval_rpn(["42"]) == 42
assert eval_rpn(["-7", "2", "/"]) == -3
assert eval_rpn(["7", "-2", "/"]) == -3
assert eval_rpn(["3", "5", "-"]) == -2           # 減法順序
for a in range(-9, 10):
    for b in [x for x in range(-9, 10) if x != 0]:
        assert div_trunc(a, b) == int(a / b)
for _ in range(300):                             # 隨機產生合法 RPN，和直接遞迴計算比對
    def build(depth):
        if depth == 0 or random.random() < 0.3:
            v = random.randint(-20, 20)
            return [str(v)], v
        lt, lv = build(depth - 1)
        rt, rv = build(depth - 1)
        op = random.choice("+-*/")
        if op == "/" and rv == 0:
            op = "+"
        return lt + rt + [op], OPS[op](lv, rv)
    toks, val = build(4)
    assert eval_rpn(toks) == val
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每個 token 處理一次，每次 O(1)。空間 O(n)：最差情況是所有數字都在前面、運算子都在後面（例如 `1 2 3 4 + + +`），stack 會長到約 n/2。邊界情況：只有一個數字時直接回傳它；負數 token 要被當成數字；除法向零取整，`a` 或 `b` 為負時要特別處理；`0 / 負數` 的結果是 0，`div_trunc` 中 `a >= 0` 讓 0 走正號分支，不會產生 `-0` 的困擾（Python 的整數也沒有 -0）。題目保證輸入合法，若不保證，pop 前要檢查 stack 至少有兩個元素，結束時檢查恰好剩一個，見 F2。

### Follow-up

> [!question]- F1. 如果輸入是一般的中序運算式（有括號與優先順序），怎麼先轉成 RPN？
> 用 shunting-yard（調度場）演算法：數字直接輸出；遇到運算子 t，先把運算子 stack 頂端「優先順序 ≥ t」的運算子彈出輸出（`>=` 讓同級運算子左結合，`1 - 2 - 3` 才會是 `1 2 - 3 -`），再 push t；遇到 `(` 直接 push；遇到 `)` 一路彈出輸出到 `(` 為止，丟掉那對括號；最後把剩下的運算子全部輸出。O(n) 時間。轉完再用本題求值，就得到一個完整的計算機，這是難題 4（224）之外的另一條路。
> ```python
> def to_rpn(tokens):
>     prec = {"+": 1, "-": 1, "*": 2, "/": 2}
>     out, ops = [], []
>     for t in tokens:
>         if t in prec:
>             while ops and ops[-1] != "(" and prec[ops[-1]] >= prec[t]:
>                 out.append(ops.pop())
>             ops.append(t)
>         elif t == "(":
>             ops.append(t)
>         elif t == ")":
>             while ops[-1] != "(":
>                 out.append(ops.pop())
>             ops.pop()
>         else:
>             out.append(t)
>     return out + ops[::-1]
> ```

> [!question]- F2. 如果不保證輸入合法，怎麼在 O(1) 額外空間內判斷它是不是合法的 RPN？
> 不需要真的計算，只要追蹤 stack 的「大小」：用計數器 `size`，數字加一，運算子要求 `size >= 2`（否則不合法）然後減一。結束時 `size == 1` 才合法。時間 O(n)，空間 O(1)。這和核心題 1 的 F1 是同一個想法：當我們只關心結構而不關心內容時，stack 可以壓縮成一個計數器。若還要檢查除以零，就必須真的求值。

> [!question]- F3. 如果是波蘭表示法（前序，運算子在前，例如 `* + 2 1 3`）呢？
> 從右往左掃描，其他規則相同：數字 push；遇到運算子時 pop 兩次，但這時**先彈出的是左運算元**（因為從右往左讀，左運算元比較晚被讀到、比較靠近頂端），算 `a op b` 後 push。O(n)。也可以從左往右用遞迴：讀到運算子就遞迴讀兩個子運算式。面試官問這題通常是想確認你真的理解「為什麼後序要先彈出右運算元」，而不是背下來。

> [!question]- F4. 如果要建出運算式樹，並能用最少的括號印出中序運算式（1628. Design an Expression Tree With Evaluate Function）呢？
> stack 改存節點：數字建成葉節點 push；運算子 pop 兩個節點當作右子與左子，建成內部節點 push。最後 stack 裡唯一的節點是根，O(n)。求值是一次後序遍歷（第 12 章）。印中序時，子節點的運算子優先順序低於父節點才需要加括號；右子節點在減法或除法下優先順序**相等**也要加，例如 `a - (b - c)`。這個設計讓「新增運算子」只需要新增一種節點，是面試官喜歡追問的物件導向延伸。

## 核心題 4｜739. Daily Temperatures｜Medium

### 題目

給一個整數陣列 `temperatures`，`temperatures[i]` 是第 i 天的氣溫。請回傳陣列 `answer`，其中 `answer[i]` 是從第 i 天起，還要等幾天才會出現**嚴格更高**的氣溫；如果之後都沒有更暖的日子，`answer[i] = 0`。限制：`1 <= n <= 10⁵`，`30 <= temperatures[i] <= 100`。

- 範例 1：`temperatures = [73, 74, 75, 71, 69, 72, 76, 73]`，回傳 `[1, 1, 4, 2, 1, 1, 0, 0]`。第 2 天的 75 要等到第 6 天的 76，共 4 天。
- 範例 2：`temperatures = [30, 40, 50, 60]`，回傳 `[1, 1, 1, 0]`。
- 範例 3（邊界）：`temperatures = [60, 50, 40]`，嚴格遞減，回傳 `[0, 0, 0]`。
- 範例 4（邊界）：`temperatures = [70, 70, 71]`，回傳 `[2, 1, 0]`；相等的 70 不算更暖，第 0 天要等到第 2 天。

### 思路

暴力解是每一天往右掃，找到第一個更高的氣溫為止，最差 O(n²)；在嚴格遞減的輸入下，每一天都要掃到底，n = 10⁵ 時約 5 × 10⁹ 次比較，太慢。瓶頸和 10.1 節一樣：如果第 j 天比第 i 天熱（j > i），那麼第 i 天之前的每一天往右找時，都不需要看第 i 天和第 j 天之間「比第 j 天冷」的日子，可是暴力解每次都重新看一遍。

這正是 10.3 節 `next_greater` 的直接應用，只是答案從「索引」換成「距離」。從左往右走，stack 存「還沒等到更暖日子」的索引。第 i 天的氣溫 x 到來時，所有 stack 頂端比 x 冷的日子，答案就是 `i - 它的索引`，把它們彈出；然後把 i 放進去等待。invariant 是：**stack 裡的索引由底到頂，氣溫非遞增**（相等的會並存，因為相等不算更暖）。每天最多進出一次，總時間 O(n)。

為什麼只需要比較頂端？因為頂端是 stack 中氣溫最低的一天；如果 x 連它都不比它熱，就不可能比下面任何一天熱，while 迴圈可以停下。這也解釋了為什麼一次可能彈出很多天：例如第 6 天的 76 一次解決了 72、75 兩天。

另一種同樣 O(n) 的寫法是**從右往左**：stack 存「右邊可能成為答案的候選日」，處理第 i 天時，先把所有氣溫 ≤ x 的候選彈掉（它們被第 i 天擋住了，對更左邊的日子來說，第 i 天比它們近而且不比它們冷），彈完後的頂端就是第 i 天右邊第一個更暖的日子。這是 10.3 節「彈完之後看頂端」的寫法。兩種寫法都好，面試時選一個講清楚 invariant 即可。

```text
temperatures = [73, 74, 75, 71, 69, 72, 76, 73]
index:          0   1   2   3   4   5   6   7
stack 存索引，括號內是氣溫，左邊是底

i  x    彈出（answer[j] = i - j）           stack 之後
0  73   —                                  0(73)
1  74   0: answer[0] = 1                   1(74)
2  75   1: answer[1] = 1                   2(75)
3  71   —（71 < 75）                        2(75) 3(71)
4  69   —                                  2(75) 3(71) 4(69)
5  72   4: answer[4] = 1；3: answer[3] = 2  2(75) 5(72)
6  76   5: answer[5] = 1；2: answer[2] = 4  6(76)
7  73   —                                  6(76) 7(73)
結束  6、7 留在 stack 裡 → answer = 0
answer = [1, 1, 4, 2, 1, 1, 0, 0]
```

第 5 天的 72 先解決了 69（等 1 天），再解決 71（等 2 天），然後遇到 75 停下，因為 72 不比 75 熱。第 6 天的 76 再把 72 和 75 一起解決。注意 stack 在每一步之後都是由底到頂遞減的：`75, 71, 69` → `75, 72` → `76` → `76, 73`。

### 解法

```python
import random


def daily_temperatures(temperatures: list[int]) -> list[int]:
    n = len(temperatures)
    answer = [0] * n
    stack: list[int] = []                       # 還沒等到更暖日子的索引，氣溫非遞增
    for i, x in enumerate(temperatures):
        while stack and temperatures[stack[-1]] < x:   # 嚴格更暖才算
            j = stack.pop()
            answer[j] = i - j
        stack.append(i)
    return answer


def daily_temperatures_backward(temperatures: list[int]) -> list[int]:
    n = len(temperatures)
    answer = [0] * n
    stack: list[int] = []                       # 右邊的候選日，氣溫由底到頂嚴格遞減
    for i in range(n - 1, -1, -1):
        while stack and temperatures[stack[-1]] <= temperatures[i]:
            stack.pop()                         # 被第 i 天擋住，不可能是更左邊的答案
        answer[i] = stack[-1] - i if stack else 0
        stack.append(i)
    return answer


def brute(t):
    n = len(t)
    return [next((j - i for j in range(i + 1, n) if t[j] > t[i]), 0) for i in range(n)]


for f in (daily_temperatures, daily_temperatures_backward):
    assert f([73, 74, 75, 71, 69, 72, 76, 73]) == [1, 1, 4, 2, 1, 1, 0, 0]
    assert f([30, 40, 50, 60]) == [1, 1, 1, 0]
    assert f([60, 50, 40]) == [0, 0, 0]
    assert f([70, 70, 71]) == [2, 1, 0]
    assert f([50]) == [0]
for _ in range(500):
    t = [random.randint(30, 35) for _ in range(random.randint(1, 12))]
    assert daily_temperatures(t) == daily_temperatures_backward(t) == brute(t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每個索引 push 一次、pop 至多一次，while 迴圈的總次數不超過 n。空間 O(n)：最差情況是嚴格遞減（或全部相等）的輸入，所有索引都留在 stack 裡，再加上答案陣列。邊界情況：相等的氣溫不能互相解決，正向寫法用 `<`、反向寫法用 `<=`，兩者對「相等」的處理剛好互補；最後留在 stack 裡的日子答案是 0，`answer` 預先填 0 就不必另外處理；只有一天時直接回傳 `[0]`。

### Follow-up

> [!question]- F1. 氣溫只有 30 到 100 共 71 種，能不能利用這點？
> 可以從右往左掃，維護 `next_day[t]` = 「目前看過的日子中，氣溫恰好是 t 的最近一天」。處理第 i 天時，檢查所有 `t > temperatures[i]` 的 `next_day[t]`，取最小的索引就是答案，再更新 `next_day[temperatures[i]] = i`。時間 O(n · W)，W = 71，空間 O(W)（不算答案）。這比 monotonic stack 的 O(n) 慢一個常數倍，但額外空間是 O(1) 級的；當值域很小而面試官要求「不要 O(n) 的 stack」時，這是一個好答案。

> [!question]- F2. 如果改成「股票價格的跨度」：今天往前連續幾天（含今天）的價格都 ≤ 今天（901. Online Stock Span），而且價格是一天一天線上給的呢？
> 這是「左邊最近一個嚴格更大」的問題，而且要線上回答。stack 存 `(價格, 跨度)`，價格由底到頂嚴格遞減。新價格 p 到來時，`span = 1`，while 頂端價格 ≤ p 就把它彈出並 `span += 它的跨度`（它涵蓋的那些天也都 ≤ p），最後 push `(p, span)` 並回傳 span。每個價格進出一次，amortized O(1)。和本題相比，方向從「往右等」變成「往左看」，所以答案是在 push 當下算出，而不是被 pop 時算出。

> [!question]- F3. 如果資料是串流，每天結束時要輸出「哪些日子今天終於等到了更暖的天氣」，記憶體有限呢？
> 正向寫法天生就是線上的：第 i 天到來時被彈出的索引，就是今天剛好得到答案的日子，可以立刻輸出 `(j, i - j)`。記憶體只需要 stack 本身，不需要保存整個歷史陣列，但 stack 的大小在最壞情況（氣溫一直下降）仍是 O(n)，這是資訊本身的下限：那些日子都還在等答案，必須記住。若可以接受「超過 D 天沒等到就放棄」，就從 stack 底部丟掉過期的日子，這時 stack 變成 deque，和第 6 章難題 2（239）同一個結構。

> [!question]- F4. 如果要回答「每個人往右看，能看到幾個人」：i 能看到 j 的條件是兩人之間的人都比 `min(h[i], h[j])` 矮，身高互不相同（1944. Number of Visible People in a Queue）呢？
> 從右往左維護一個由底到頂遞減的 stack。處理第 i 個人時，所有比他矮的人都會被彈出，而**每一個被彈出的人他都看得到**（他們之間沒有更高的人擋住，否則那些人早就被彈出了）；彈完之後若 stack 非空，頂端是第一個比他高（或一樣高）的人，他也看得到，再加一。最後把 i push。每個人進出一次，O(n)。這題說明了被彈出的元素不只能「得到答案」，也能「貢獻答案」，和難題 1（84）的想法相同。

## 核心題 5｜503. Next Greater Element II｜Medium

### 題目

給一個**環狀**整數陣列 `nums`（最後一個元素的下一個是第一個元素），對每個元素，回傳沿著環往後走遇到的第一個**嚴格更大**的元素的值；如果繞一圈都找不到，回傳 -1。限制：`1 <= n <= 10⁴`，元素在 `-10⁹` 到 `10⁹` 之間，可能重複。

- 範例 1：`nums = [1, 2, 1]`，回傳 `[2, -1, 2]`。最後一個 1 往後繞回開頭，先遇到 1（不算更大），再遇到 2。
- 範例 2：`nums = [1, 2, 3, 4, 3]`，回傳 `[2, 3, 4, -1, 4]`。最後的 3 繞回開頭，1、2 都不夠大，遇到 3 也不算（相等），再遇到 4。
- 範例 3（邊界）：`nums = [5, 5, 5]`，所有元素相等，回傳 `[-1, -1, -1]`。
- 範例 4（邊界）：`nums = [3]`，只有一個元素，繞一圈只會遇到自己，回傳 `[-1]`。

### 思路

暴力解是對每個 i，沿著 `(i + 1) % n, (i + 2) % n, …` 走 n − 1 步，找第一個更大的，O(n²)。另一個直覺是把陣列複製一份接在後面變成 `nums + nums`，在長度 2n 的陣列上做普通的 next greater，前 n 個位置的答案就是所求；這已經是 O(n)，只是多用了 O(n) 的空間來存複製品。

關鍵觀察是：**環狀只影響「走到尾端之後還能繞回開頭」**，而繞回開頭最多只需要再走一圈。所以不必真的複製，只要讓索引 i 從 0 跑到 2n − 1，用 `nums[i % n]` 讀值即可。第一圈（i < n）和普通版本完全一樣：解決能解決的，然後把 i push 進去等待；第二圈（i ≥ n）只負責「解決」stack 裡剩下的元素，**不再 push**，因為第一圈已經替每個位置建立過等待項，再 push 會讓同一個位置等兩次。

為什麼兩圈一定夠？第一圈結束時，stack 裡剩下的是「右邊到尾端都沒有更大」的元素，它們的答案只可能在自己左邊（繞回去之後）。第二圈從開頭走到 n − 1，涵蓋了每個元素左邊的所有位置，所以該找到的都會找到。還留在 stack 裡的就是整個陣列的最大值（以及和它相等的元素），答案是 -1。

```text
nums = [1, 2, 3, 4, 3]，n = 5
i 從 0 到 9，值 = nums[i % 5]；stack 存索引（括號內是值）

圈  i  值  彈出並記答案                    push?  stack 之後
一  0  1   —                               是     0(1)
一  1  2   0 → ans[0] = 2                  是     1(2)
一  2  3   1 → ans[1] = 3                  是     2(3)
一  3  4   2 → ans[2] = 4                  是     3(4)
一  4  3   —（3 < 4）                       是     3(4) 4(3)
二  5  1   —                               否     3(4) 4(3)
二  6  2   —                               否     3(4) 4(3)
二  7  3   —（3 不嚴格大於 3）               否     3(4) 4(3)
二  8  4   4 → ans[4] = 4                  否     3(4)
二  9  3   —                               否     3(4)
結束  索引 3（最大值 4）留在 stack → ans[3] = -1
答案 [2, 3, 4, -1, 4]
```

第二圈的 i = 7 讀到的是 `nums[2] = 3`，和等待中的 `nums[4] = 3` 相等，不能解決它；直到 i = 8 讀到 4 才解決。這也說明了「相等不算更大」在環狀版本中同樣重要：若條件寫成 `<=`，最後的 3 會錯誤地得到 3。

### 解法

```python
import random


def next_greater_elements(nums: list[int]) -> list[int]:
    n = len(nums)
    ans = [-1] * n
    stack: list[int] = []                    # 還在等答案的索引，值由底到頂非遞增
    for i in range(2 * n):
        x = nums[i % n]
        while stack and nums[stack[-1]] < x:
            ans[stack.pop()] = x
        if i < n:                            # 第二圈只解決，不再加入
            stack.append(i)
    return ans


def next_greater_from_max(nums: list[int]) -> list[int]:
    """另一種寫法：從最大值的下一格開始走一圈，剛好把環切成一條鏈。"""
    n = len(nums)
    start = max(range(n), key=nums.__getitem__) + 1
    ans = [-1] * n
    stack: list[int] = []
    for k in range(n):
        i = (start + k) % n
        while stack and nums[stack[-1]] < nums[i]:
            ans[stack.pop()] = nums[i]
        stack.append(i)
    return ans


def brute(nums):
    n = len(nums)
    return [next((nums[(i + d) % n] for d in range(1, n) if nums[(i + d) % n] > nums[i]), -1)
            for i in range(n)]


for f in (next_greater_elements, next_greater_from_max):
    assert f([1, 2, 1]) == [2, -1, 2]
    assert f([1, 2, 3, 4, 3]) == [2, 3, 4, -1, 4]
    assert f([5, 5, 5]) == [-1, -1, -1]
    assert f([3]) == [-1]
    assert f([5, 4, 3, 2, 1]) == [-1, 5, 5, 5, 5]
for _ in range(500):
    arr = [random.randint(-3, 3) for _ in range(random.randint(1, 10))]
    assert next_greater_elements(arr) == next_greater_from_max(arr) == brute(arr)
print("all tests passed")
```

第二種寫法利用了一個觀察：最大值的答案一定是 -1，而且任何元素往後找時都不可能「越過」最大值（最大值本身就是一個更大或相等的阻擋）。所以從最大值的下一格開始、走到最大值為止，這條鏈上的 next greater 就等於環上的答案，只要走一圈。兩種寫法都是 O(n)，第一種更通用，不需要先找最大值。

### 複雜度與邊界

時間 O(n)：迴圈跑 2n 次，每個索引最多 push 一次、pop 一次。空間 O(n)：stack 加上答案陣列，沒有複製陣列。邊界情況：n = 1 時第一圈 push 索引 0，第二圈讀到自己但不嚴格更大，答案 -1；全部相等時沒有任何元素被解決；最大值出現多次時，每一個最大值的答案都是 -1，而其他元素會找到「沿環往後第一個」最大值或更早的更大元素；嚴格遞減時，第二圈讀到開頭的最大值，一次解決所有其他元素。

### Follow-up

> [!question]- F1. 如果是非環狀版本，而且要回答的是另一個陣列 nums1 中每個元素（nums1 是 nums2 的子集、元素互不相同）在 nums2 中的下一個更大（496. Next Greater Element I）呢？
> 先對 nums2 做一次普通的 monotonic stack，把結果存在雜湊表 `nxt[值] = 下一個更大的值`（元素互不相同，所以值可以當 key），再對 nums1 每個元素查表。時間 O(m + n)，空間 O(n)。這題的重點是「把查詢和計算分開」：monotonic stack 一次替所有元素算好答案，查詢只是 O(1) 的查表。

> [!question]- F2. 如果要的是「下一個更大元素」的距離（沿環要走幾步），而不是值呢？
> 被彈出時記錄 `ans[j] = i - j` 即可，其中 i 是第二圈的「虛擬索引」（還沒取模），所以距離自動包含了繞回開頭的步數。例如 `[1, 2, 1]` 中最後一個 1（索引 2）在 i = 4（實際索引 1）被解決，距離是 4 − 2 = 2。找不到的設為 -1 或 0，依題目約定。時間空間都不變。這和核心題 4 的 739 合起來，就是「環狀的 Daily Temperatures」。

> [!question]- F3. 如果輸入是 linked list（1019. Next Greater Node In Linked List，非環狀）呢？
> 不知道長度，也不能用索引隨機存取。邊走邊把節點值放進一個 list `vals`，同時 stack 存 `vals` 的索引，做法和 739 完全相同：每走到一個新節點，就用它解決 stack 裡比它小的索引。走完之後答案陣列就是結果。O(n) 時間與空間。若題目要求不用額外 O(n) 空間，可以先反轉 linked list（第 11 章核心題 1）再從「右往左」做，但 stack 本身在最差情況仍是 O(n)，無法避免。

> [!question]- F4. 如果要找的是「第二個」更大的元素：i 右邊第二個比 nums[i] 大的值（2454. Next Greater Element IV）呢？
> 用兩個 stack。s1 存「還沒遇到任何更大元素」的索引，s2 存「已經遇到一個、在等第二個」的索引，兩者都由底到頂非遞增。新元素 x 到來時：先用 x 解決 s2 頂端所有比 x 小的（它們的答案就是 x）；再把 s1 頂端所有比 x 小的彈出，**保持原本的相對順序**搬到 s2（它們剛遇到第一個更大元素 x）；最後把 x 的索引 push 到 s1。搬到 s2 的元素都比 x 小，而 s2 剩下的都 ≥ x，所以 s2 仍然單調。每個索引最多進出兩個 stack 各一次，O(n)。
> ```python
> def second_greater(nums):
>     ans = [-1] * len(nums)
>     s1, s2 = [], []
>     for i, x in enumerate(nums):
>         while s2 and nums[s2[-1]] < x:
>             ans[s2.pop()] = x
>         moved = []
>         while s1 and nums[s1[-1]] < x:
>             moved.append(s1.pop())
>         s2.extend(reversed(moved))      # 維持原本由底到頂的順序
>         s1.append(i)
>     return ans
> ```

## 難題 1｜84. Largest Rectangle in Histogram｜Hard

### 題目

給一個非負整數陣列 `heights`，代表一張直方圖中每根柱子的高度，每根柱子寬度都是 1、彼此緊鄰。請回傳直方圖中能畫出的最大矩形面積，矩形必須完全落在柱子內部（底邊貼齊 x 軸、由連續的若干根柱子組成，高度不能超過其中最矮的那根）。限制：`1 <= n <= 10⁵`，`0 <= heights[i] <= 10⁴`。

- 範例 1：`heights = [2, 1, 5, 6, 2, 3]`，回傳 `10`，由高度 5、6 兩根柱子組成高 5、寬 2 的矩形。
- 範例 2：`heights = [2, 4]`，回傳 `4`，可以是單獨的 4，或是高 2、寬 2。
- 範例 3：`heights = [2, 1, 2]`，回傳 `3`，高度 1、橫跨三根柱子。
- 範例 4（邊界）：`heights = [3, 3, 3]`，回傳 `9`；`heights = [0]`，回傳 `0`。

### 提示

> [!tip]- 提示 1
> 最大矩形的高度一定等於它所涵蓋的某根柱子的高度（否則可以再長高一點）。所以可以換個問法：對每根柱子 i，「以 heights[i] 為高、包含 i 的矩形」最寬能多寬？

> [!tip]- 提示 2
> 以 heights[i] 為高的矩形，會往左右延伸，直到遇到第一根比 heights[i] 矮的柱子。寬度就是「右邊第一根更矮的位置」減「左邊第一根更矮的位置」再減一。這兩個位置都是 monotonic stack 的標準問題。

> [!tip]- 提示 3
> 維護一個高度遞增的 stack。當新柱子比頂端矮時，頂端那根柱子的右邊界就是新柱子，左邊界就是它在 stack 中下面那一根；彈出時就能算出它的面積。在尾端放一根高度 0 的哨兵，把所有柱子都逼出來。

### 詳解

**為什麼直覺做法不夠**。最直接的暴力是枚舉所有區間 `[l, r]`，用區間最小值乘寬度，固定 l 往右擴展時順便更新最小值，O(n²)；n = 10⁵ 時約 5 × 10⁹，太慢。另一個直覺是分治：整段的最小值那根柱子，要嘛是答案的高（矩形橫跨整段），要嘛答案完全在它左邊或右邊，遞迴下去；平均 O(n log n)，但輸入已排序時每次只切掉一根，退化成 O(n²)，要用 segment tree 找最小值才能穩定 O(n log n)，寫起來也長。

**突破點：以每根柱子為高**。最大矩形的高度一定是它範圍內最矮那根柱子的高度，所以答案 = `max over i (heights[i] × width(i))`，其中 width(i) 是以 heights[i] 為高、包含 i 的最寬矩形。這個矩形往左延伸到「左邊第一根比它矮的柱子」L 為止（不含 L），往右延伸到「右邊第一根比它矮的柱子」R 為止（不含 R），寬度是 `R − L − 1`。於是問題變成：對每個 i 求左右第一個更小的位置，這就是 10.3 節的 monotonic stack。

**一次掃描同時得到左右邊界**。維護一個由底到頂高度遞增的 stack。新柱子 i 的高度 h 比頂端 t 的高度矮（或相等）時，彈出 t：此時 i 是 t 右邊第一根「≤ 它」的柱子，可以當作 R；彈出 t 之後的新頂端，是 t 左邊第一根「< 它」的柱子，就是 L（stack 遞增，而 L 和 t 之間的柱子都曾被 t 或 t 之前的柱子彈出，高度都 ≥ heights[t]）。所以在彈出的那一刻算 `heights[t] × (i − L − 1)` 即可，stack 為空時 L = −1。在陣列尾端加一根高度 0 的哨兵，保證最後所有柱子都會被彈出計算。

**相等的柱子為什麼不會出錯**。用 `>=` 彈出時，對於一組相等的柱子，前面那根在遇到後面那根時就被彈出，R 被設成後面那根，寬度偏小。但最後一根相等的柱子會在遇到真正更矮的柱子時才被彈出，而且它下面的頂端是更矮的柱子（前面那些相等的已被彈掉），所以它算出的寬度是完整的。最大值只需要有一根算對，因此結果正確。用 `>` 彈出也對，對稱地由第一根算出完整寬度。

```text
heights = [2, 1, 5, 6, 2, 3]，尾端加哨兵 0
index:     0  1  2  3  4  5  6(哨兵)
stack 存索引（括號內是高度），由底到頂高度遞增

i  h   彈出 t  高    L（新頂端）  寬 = i - L - 1   面積   stack 之後
0  2   —                                                   0(2)
1  1   0      2     -1            1 - (-1) - 1 = 1   2     1(1)
2  5   —                                                   1(1) 2(5)
3  6   —                                                   1(1) 2(5) 3(6)
4  2   3      6      2            4 - 2 - 1 = 1      6
       2      5      1            4 - 1 - 1 = 2     10 ★   1(1) 4(2)
5  3   —                                                   1(1) 4(2) 5(3)
6  0   5      3      4            6 - 4 - 1 = 1      3
       4      2      1            6 - 1 - 1 = 4      8
       1      1     -1            6 - (-1) - 1 = 6   6     6(0)
最大面積 = 10
```

第 4 步是關鍵：高度 2 的柱子到來，先彈出高度 6 的柱子（它只能延伸自己一格），再彈出高度 5 的柱子，它的左邊界是索引 1（高度 1），右邊界是索引 4，中間涵蓋索引 2、3，寬度 2，面積 10。高度 1 的柱子一直留到哨兵才被彈出，此時 stack 為空，代表它左邊沒有更矮的，寬度是整個陣列 6。

**正確性**。每根柱子恰好被彈出一次，彈出時算出的就是「以它為高」的矩形（或在相等時偏小、但同組中有一根完整）。最佳矩形的高度等於其中最矮柱子 i 的高度，而以 heights[i] 為高的最寬矩形至少和它一樣寬，所以 max 一定涵蓋最佳解。

### 解法

```python
import random


def largest_rectangle_area(heights: list[int]) -> int:
    best = 0
    stack: list[int] = []                  # 索引，高度由底到頂遞增
    for i, h in enumerate(heights + [0]):  # 尾端哨兵 0 把所有柱子逼出來
        while stack and heights[stack[-1]] >= h:
            top = stack.pop()
            left = stack[-1] if stack else -1      # 左邊第一根更矮的
            best = max(best, heights[top] * (i - left - 1))
        stack.append(i)
    return best


def largest_rectangle_two_pass(heights: list[int]) -> int:
    """先分別求左右第一根嚴格更矮的位置，再逐根計算，邏輯更直觀。"""
    n = len(heights)
    left, right, stack = [-1] * n, [n] * n, []
    for i, h in enumerate(heights):
        while stack and heights[stack[-1]] > h:
            right[stack.pop()] = i
        left[i] = stack[-1] if stack and heights[stack[-1]] < h else (
            left[stack[-1]] if stack else -1)   # 相等時沿用前一根的左邊界
        stack.append(i)
    return max((heights[i] * (right[i] - left[i] - 1) for i in range(n)), default=0)


def brute(heights):
    best = 0
    for l in range(len(heights)):
        low = heights[l]
        for r in range(l, len(heights)):
            low = min(low, heights[r])
            best = max(best, low * (r - l + 1))
    return best


for f in (largest_rectangle_area, largest_rectangle_two_pass):
    assert f([2, 1, 5, 6, 2, 3]) == 10
    assert f([2, 4]) == 4
    assert f([2, 1, 2]) == 3
    assert f([3, 3, 3]) == 9
    assert f([0]) == 0
    assert f([1, 2, 3, 4, 5]) == 9          # 遞增：全靠哨兵
    assert f([5, 4, 3, 2, 1]) == 9          # 遞減
for _ in range(1000):
    arr = [random.randint(0, 6) for _ in range(random.randint(1, 10))]
    assert largest_rectangle_area(arr) == largest_rectangle_two_pass(arr) == brute(arr)
print("all tests passed")
```

第二種寫法中，`left[i]` 遇到相等高度時沿用前一根的左邊界，讓每根柱子都得到完整的寬度；這在需要「每根柱子的真實邊界」時（例如 F1 要回傳座標、或難題 5 的計數）比較安全。只求最大面積時，第一種寫法最短，面試時建議用它。

### 複雜度與邊界

時間 O(n)：每個索引 push、pop 各一次；空間 O(n)：stack 最差存下所有索引（輸入遞增時）。`heights + [0]` 會複製一份陣列，若要省這 O(n)，可以用 `for i in range(n + 1)` 並令 `h = heights[i] if i < n else 0`。邊界情況：只有一根柱子時答案是它的高度；有高度 0 的柱子時，它會把左邊全部彈出，自己算出的面積是 0，相當於把直方圖切成兩段；全部相等時靠 `>=` 與哨兵算出 n × h；面積最大 10⁴ × 10⁵ = 10⁹，Python 無溢位，Java 的 `int` 也還夠。

### Follow-up

> [!question]- F1. 如果要回傳最大矩形的位置（左右邊界與高度）呢？
> 在更新 best 的同時記錄 `(left + 1, i - 1, heights[top])` 即可，因為彈出時算出的就是這個矩形的完整範圍（相等柱子時偏小的那些不會成為最大值，除非它們和完整的那個面積相同，此時兩者都是合法答案）。時間空間都不變。若要回傳**所有**面積最大的矩形，要用第二種寫法得到每根柱子的真實邊界，再去重，因為同一個矩形可能由多根同高的柱子算出。

> [!question]- F2. 如果柱子的寬度不全是 1，第 i 根的寬度是 w[i] 呢？
> 邊界的計算完全不變（左右第一根更矮的柱子只和高度有關），只是寬度要從「索引差」改成「寬度總和」：先建前綴和 `P[k] = w[0] + … + w[k-1]`，以柱子 t 為高、左邊界 L、右邊界 R 時，矩形寬度是 `P[R] − P[L + 1]`。時間 O(n)，空間 O(n)。這說明 monotonic stack 負責找邊界，面積怎麼算是另一件事，可以和 prefix sum（第 7 章）自由組合。

> [!question]- F3. 如果矩形必須包含指定的柱子 k，要最大化 `min(heights[i..j]) × (j − i + 1)`（1793. Maximum Score of a Good Subarray）呢？
> 可以直接用本題的 stack：只有當柱子 t 的範圍 `[L + 1, R − 1]` 包含 k 時，才把它的面積納入最大值，O(n)。另一種更短的做法是第 5 章難題 4 的 two pointers：從 k 往兩邊擴展，每次往較高的那一側走一格，並更新目前的最小值與分數，同樣 O(n)。兩種做法的正確性都來自「最佳區間的最小值一定是某根柱子」。

> [!question]- F4. 如果要的是直方圖中最大的**正方形**呢？
> 以柱子 t 為最矮的那根，最寬能延伸 `W = R − L − 1`，所以能放進去的正方形邊長是 `min(heights[t], W)`。答案是所有柱子中這個值的最大值，O(n)。正確性：最佳正方形邊長 s 對應一段長度 s、最小值 ≥ s 的區間，區間中最矮的柱子 t 滿足 heights[t] ≥ s，而它的最大寬度 W ≥ s，所以 `min(heights[t], W) ≥ s`，不會漏掉。這是把本題的「每根柱子的最大範圍」重新組合成另一個目標函數的典型例子。

> [!question]- F5. 如果直方圖是一行一行（或一根一根）串流進來，要隨時回報目前的最大面積呢？
> 只考慮「新增柱子在右端」的情況，stack 版本是線上的，但有一個問題：還在 stack 裡的柱子尚未被彈出，面積還沒算。要隨時回報，就必須在查詢時把 stack 裡每根柱子當作「右邊界延伸到目前尾端」計算一次，這是 O(stack 大小)。已被彈出的柱子面積固定，用一個變數記住最大值即可；麻煩的是還在 stack 裡的層，第 t 層的面積是 `heights[t] × (尾端 − L)`，對「尾端」是一條斜率為 heights[t] 的直線，尾端每增加一格，各層增加的量都不同。若查詢頻繁，查詢就變成「多條直線在某一點的最大值」，可以用 Li Chao tree 這類支援插入與回滾的結構做到 O(log n)，但這已超出面試範圍。面試中通常回答「查詢時掃一遍 stack，最差 O(n)」並說明為什麼無法 O(1) 即可。

### 心得

關鍵突破是「最大矩形的高一定是某根柱子的高」，把二維的面積最佳化轉成一維的邊界問題：每根柱子往左右延伸到第一根更矮的柱子。它和核心題 4、5 的關係是：739 與 503 只需要「右邊第一個更大」，這題需要「左右第一個更小」，而 monotonic stack 在彈出的那一刻同時給出兩者。面試時建議先說 O(n²) 的區間枚舉，再說「我改成固定高度、問寬度」，畫出 `L | t … | R` 的邊界圖，然後寫單次掃描加哨兵的版本，最後主動說明相等高度的處理。這題也是難題 2（85）的子程序，兩題要一起練。

## 難題 2｜85. Maximal Rectangle｜Hard

### 題目

給一個 rows × cols 的二元矩陣 `matrix`，每格是字元 `"0"` 或 `"1"`。找出只包含 `"1"` 的最大**軸對齊矩形**，回傳它的面積（格子數）。限制：`1 <= rows, cols <= 200`。

- 範例 1：
  ```text
  1 0 1 0 0
  1 0 1 1 1
  1 1 1 1 1
  1 0 0 1 0
  ```
  回傳 `6`，由第 1、2 列（從 0 開始）的第 2 到 4 行組成，高 2、寬 3。
- 範例 2：`matrix = [["0"]]`，回傳 `0`。
- 範例 3：`matrix = [["1"]]`，回傳 `1`。
- 範例 4（邊界）：全部是 `"1"` 的 3 × 4 矩陣，回傳 `12`；只有一列 `["1", "1", "0", "1"]`，回傳 `2`。

### 提示

> [!tip]- 提示 1
> 枚舉矩形的「底邊」在哪一列。固定底邊之後，每一行往上連續有幾個 1，看起來像什麼？

> [!tip]- 提示 2
> 以第 r 列為底，第 c 行往上連續的 1 的個數 `h[c]` 構成一張直方圖。底邊在第 r 列的最大全 1 矩形，就是這張直方圖的最大矩形（難題 1）。

> [!tip]- 提示 3
> `h[c]` 可以逐列更新：這一格是 1 就 `h[c] += 1`，是 0 就歸零。每列 O(cols) 更新、再 O(cols) 跑一次 monotonic stack，總共 O(rows × cols)。

### 詳解

**為什麼直覺做法不夠**。枚舉所有矩形需要選兩列和兩行，共 O(rows² × cols²) 個，每個再用二維 prefix sum（第 7 章核心題 4）O(1) 檢查是否全為 1，總共約 (200²)² = 1.6 × 10⁹，太慢。改成固定上下兩列，把中間壓成一維「這一行是否全為 1」，再在一維上找最長連續的 1，是 O(rows² × cols) = 8 × 10⁶，可以接受，但還不是最好的，而且沒有利用上一列已經算過的資訊。

**突破點：每一列當作直方圖的底**。任何全 1 矩形都有一條底邊，落在某一列 r。固定 r 之後，令 `h[c]` 為「從第 r 列往上，第 c 行連續有幾個 1」。一個以第 r 列為底、橫跨行 `[a, b]` 的全 1 矩形，高度最多是 `min(h[a..b])`；反過來，高度 `min(h[a..b])` 的矩形一定全為 1。所以「底邊在第 r 列的最大矩形」恰好等於直方圖 h 的最大矩形，直接用難題 1 的 O(cols) 演算法。

**逐列更新直方圖**。第 r 列的 h 可以從第 r − 1 列的 h 得到：`matrix[r][c] == "1"` 時 `h[c] = h[c] + 1`，否則 `h[c] = 0`。這是一個一維的 DP，每列 O(cols)。整體是 rows 次「更新 + 直方圖最大矩形」，O(rows × cols)，每一格只被看常數次，已經是最佳，因為每一格至少要讀一次。

```text
matrix:              以每一列為底的直方圖 h，以及該列的最大矩形
列 0: 1 0 1 0 0      h = [1, 0, 1, 0, 0]   最大 1
列 1: 1 0 1 1 1      h = [2, 0, 2, 1, 1]   最大 3（高 1，行 2..4）
列 2: 1 1 1 1 1      h = [3, 1, 3, 2, 2]   最大 6（高 2，行 2..4）★
列 3: 1 0 0 1 0      h = [4, 0, 0, 3, 0]   最大 4（高 4，行 0）
答案 = 6

列 2 的直方圖：
        #       #
        #       #   #   #
        #   #   #   #   #
行:     0   1   2   3   4
h:      3   1   3   2   2
以行 3 的高度 2 為高：左邊第一根更矮是行 1（高 1），右邊沒有更矮 → 寬 3，面積 6
```

列 2 的直方圖中，行 2 高 3、行 3 和行 4 高 2。以高度 2 為高，矩形從行 2 延伸到行 4（行 1 的高度 1 擋住左邊），寬 3、面積 6，對應原矩陣中第 1、2 列的第 2 到 4 行。列 3 的 h 中第 2 行歸零了，因為 `matrix[3][2] == "0"`，所以以列 3 為底的矩形不能再使用那一行。

**另一種 DP 寫法**。也可以對每一格維護 `height`、`left`、`right` 三個值：以這一格為底、高度為 `height[c]` 的矩形，左右最遠能延伸到哪裡，每列從左往右、從右往左各更新一次，同樣 O(rows × cols)。它和 stack 版本本質相同，都是在找「以 h[c] 為高的最大寬度」，只是 DP 版利用了上一列的邊界。面試中 stack 版本更容易講清楚，因為它直接重用難題 1。

### 解法

```python
import random


def largest_rectangle_area(heights: list[int]) -> int:
    best, stack = 0, []
    for i, h in enumerate(heights + [0]):
        while stack and heights[stack[-1]] >= h:
            top = stack.pop()
            left = stack[-1] if stack else -1
            best = max(best, heights[top] * (i - left - 1))
        stack.append(i)
    return best


def maximal_rectangle(matrix: list[list[str]]) -> int:
    if not matrix or not matrix[0]:
        return 0
    h = [0] * len(matrix[0])
    best = 0
    for row in matrix:
        for c, cell in enumerate(row):
            h[c] = h[c] + 1 if cell == "1" else 0   # 以這一列為底，往上連續的 1
        best = max(best, largest_rectangle_area(h))
    return best


def brute(matrix):
    R, C = len(matrix), len(matrix[0])
    best = 0
    for r1 in range(R):
        for r2 in range(r1, R):
            for c1 in range(C):
                for c2 in range(c1, C):
                    if all(matrix[r][c] == "1" for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)):
                        best = max(best, (r2 - r1 + 1) * (c2 - c1 + 1))
    return best


grid = [list("10100"), list("10111"), list("11111"), list("10010")]
assert maximal_rectangle(grid) == 6
assert maximal_rectangle([["0"]]) == 0
assert maximal_rectangle([["1"]]) == 1
assert maximal_rectangle([["1"] * 4 for _ in range(3)]) == 12
assert maximal_rectangle([list("1101")]) == 2
assert maximal_rectangle([["1"], ["1"], ["0"], ["1"]]) == 2     # 只有一行
for _ in range(300):
    R, C = random.randint(1, 5), random.randint(1, 5)
    g = [[random.choice("01") for _ in range(C)] for _ in range(R)]
    assert maximal_rectangle(g) == brute(g)
print("all tests passed")
```

### 複雜度與邊界

時間 O(rows × cols)：每列更新 h 是 O(cols)，跑一次直方圖也是 O(cols)。空間 O(cols)：h 陣列與 stack（`heights + [0]` 的複製也是 O(cols)）。邊界情況：全為 0 時每列的直方圖都是 0，答案 0；只有一列時 h 就是那一列本身，答案是最長連續 1 的長度；只有一行時 h 會累積成往上的連續長度，直方圖只有一根柱子；矩陣中的元素是**字元** `"1"`，和整數 1 比較會永遠不相等，這是很常見的低級錯誤。若 rows 遠大於 cols，按列處理最好；反之可以轉置，讓直方圖長度是較短的那一維，空間變成 O(min(rows, cols))。

### Follow-up

> [!question]- F1. 如果要的是最大的全 1 **正方形**（221. Maximal Square）呢？
> 正方形有更簡單的 DP：`dp[r][c]` = 以 (r, c) 為右下角的最大正方形邊長，`dp[r][c] = min(dp[r-1][c], dp[r][c-1], dp[r-1][c-1]) + 1`（該格為 1 時），答案是最大邊長的平方。O(rows × cols) 時間，滾動陣列可降到 O(cols) 空間。也可以沿用本題的直方圖，把難題 1 F4 的「直方圖最大正方形」套進每一列，同樣 O(rows × cols)。DP 版本通常更短，是面試時的首選。

> [!question]- F2. 如果要數「全 1 子矩形」總共有幾個（1504. Count Submatrices With All Ones）呢？
> 仍然逐列建直方圖 h，但改成計數：以第 r 列為底、右下角在第 c 行的全 1 矩形個數 `cnt[c]`，等於「以 c 左邊第一根嚴格更矮的柱子 p 為界」的兩部分之和：`cnt[c] = cnt[p] + h[c] × (c − p)`。前半段是右邊界延伸到 c 之後高度受 h[p] 限制的那些（和以 p 為右下角的個數相同），後半段是左邊界落在 `(p, c]` 時，高度可以是 1 到 h[c] 任一個。p 用 monotonic stack 求，每列 O(cols)，總共 O(rows × cols)。這和難題 5（907）的 DP 寫法是同一個遞迴式。
> ```python
> def num_submat(mat):
>     n = len(mat[0]); h = [0] * n; total = 0
>     for row in mat:
>         for j in range(n):
>             h[j] = h[j] + 1 if row[j] else 0
>         cnt, st = [0] * n, []
>         for j in range(n):
>             while st and h[st[-1]] >= h[j]:
>                 st.pop()
>             p = st[-1] if st else -1
>             cnt[j] = (cnt[p] if p >= 0 else 0) + h[j] * (j - p)
>             st.append(j)
>             total += cnt[j]
>     return total
> ```

> [!question]- F3. 如果可以任意重新排列矩陣的「行」（1727. Largest Submatrix With Rearrangements）呢？
> 每一列的直方圖 h 照舊計算，但因為行可以重排，最好的排法是把高的柱子放在一起：把 h 由大到小排序得到 `s`，則以這一列為底的最大矩形是 `max over k (s[k] × (k + 1))`，也就是「取最高的 k + 1 根，高度受第 k + 1 高的限制」。注意每一列都可以有自己的排法，因為 h 已經記住了往上的連續長度，重排是對整行一起移動，不會破壞 h。時間 O(rows × cols log cols)；也可以利用「h 每列只會加一或歸零」維護排序順序，做到 O(rows × cols)。

> [!question]- F4. 如果矩陣太大放不進記憶體，只能一列一列讀進來（例如 rows = 10⁷、cols = 1000）呢？
> 本題的演算法天生就是串流的：任何時刻只需要目前的直方圖 h（O(cols)）和一個 stack，讀完一列就可以丟掉。總時間仍是 O(rows × cols)，記憶體 O(cols)。若連 cols 都很大，就要把每一列也分塊讀取，此時 stack 演算法仍然是從左往右單向掃描，可以邊讀邊處理，h 本身則要存在磁碟上，每列讀寫一次。這個性質讓它比「固定上下兩列」的 O(rows² × cols) 做法更適合大資料。

### 心得

關鍵突破是「固定底邊之後，二維問題就變成一維的直方圖」，而直方圖可以逐列 O(cols) 更新，所以整題只是 rows 次難題 1。它和本章的關係是：難題 1 提供子程序，這題示範如何把二維的「全 1 矩形」降維；F2 再把「最大值」換成「計數」，就和難題 5 的遞迴式接上。面試時先說枚舉矩形的 O(rows² × cols²)，再說「我把每一列當成直方圖的底」，畫出範例的四張直方圖，指出列 2 的答案 6，最後說明 h 為什麼遇到 0 要歸零。如果面試官先問過 84，這題幾乎是送分題；如果沒有，能自己把它拆成 84 就是最大的加分。

## 難題 3｜32. Longest Valid Parentheses｜Hard

### 題目

給一個只包含 `(` 和 `)` 的字串 `s`，回傳其中最長的**合法括號子字串**的長度。子字串必須連續；合法的定義同核心題 1：每個 `(` 都有之後的 `)` 與之配對，順序正確。限制：`0 <= len(s) <= 3 × 10⁴`。

- 範例 1：`s = "(()"`，回傳 `2`，最長的合法子字串是 `"()"`。
- 範例 2：`s = ")()())"`，回傳 `4`，是中間的 `"()()"`。
- 範例 3：`s = "()(())"`，回傳 `6`，整個字串都合法；注意它是「並列」加「巢狀」的組合。
- 範例 4（邊界）：`s = ""`，回傳 `0`；`s = "))(("`，沒有任何合法子字串，回傳 `0`。

### 提示

> [!tip]- 提示 1
> 用核心題 1 的 stack 配對時，被配對成功的括號會形成一段一段合法的區間。把「無法配對」的括號位置記下來，它們會把字串切成若干段，每一段內部都合法嗎？

> [!tip]- 提示 2
> stack 裡改存索引。在 stack 底部放一個「最後一個無法配對的位置」當作基準，初始值是 -1。每次配對成功後，目前合法子字串的長度可以用「目前索引 − 新的頂端」算出來。

> [!tip]- 提示 3
> 遇到 `(` push 索引；遇到 `)` 先 pop。pop 之後 stack 若為空，代表這個 `)` 無法配對，把它的索引 push 進去當新的基準；否則長度是 `i - stack[-1]`。另有 O(1) 空間的解法：左右各掃一次，只用兩個計數器。

### 詳解

**為什麼直覺做法不夠**。暴力解是枚舉所有偶數長度的子字串，每個用計數器 O(n) 檢查是否合法，O(n³)；固定左端往右擴展並維護計數器，可以降到 O(n²)：計數器 < 0 時停止擴展，計數器 = 0 時更新答案。n = 3 × 10⁴ 時約 4.5 × 10⁸，在 Python 中仍太慢。直覺上「用 stack 配對，數配對成功的括號有幾個」也不對：`"()(()"` 中有兩對成功配對，總數 4，但它們不連續，中間隔著一個沒配對的 `(`，正確答案是 2。

**突破點：無法配對的位置是分隔線**。用核心題 1 的方式配對之後，所有無法配對的括號（多出來的 `)`，以及最後留在 stack 裡的 `(`）會把字串切成若干段，每一段內部的括號全部配對成功，因此每一段都是合法的；而任何合法子字串都不可能跨過一個無法配對的括號。所以答案就是「相鄰兩個無法配對位置之間的最大距離」。這可以在掃描時直接算：stack 底部永遠保留「最後一個無法配對的 `)` 的位置」（一開始是 -1，代表字串開頭之前），上面放還沒配對的 `(` 的索引。

**invariant 與長度計算**。處理完 `s[:i+1]` 後，stack 的底部是最近一個無法配對的 `)` 的索引（或 -1），上面是它之後所有還沒配對的 `(` 的索引。遇到 `)` 時先 pop：如果 pop 掉的是 `(`，配對成功，此時新的頂端是「最近一個還沒配對的位置」，從它的下一格到 i 全部配對成功，長度是 `i - stack[-1]`；如果 pop 掉的是底部的基準，stack 變空，代表這個 `)` 沒有 `(` 可以配對，它成為新的分隔線，push i。這個公式自動處理了並列的情況：`"()()"` 第二個 `)` 配對後，頂端仍是 -1，長度是 3 − (−1) = 4，前一對被自動接上。

```text
s = ")()())"
index:  0 1 2 3 4 5
stack 存索引，底部是基準

i  字元  動作                                  stack       長度
-                                              [-1]
0   )    pop -1 → 空，無法配對，push 0 當基準     [0]
1   (    push 1                                [0, 1]
2   )    pop 1 → 頂端 0                         [0]         2 - 0 = 2
3   (    push 3                                [0, 3]
4   )    pop 3 → 頂端 0                         [0]         4 - 0 = 4 ★
5   )    pop 0 → 空，無法配對，push 5 當基準     [5]
答案 4

s = "()(()"
i  字元  動作                                  stack       長度
0   (    push                                  [-1, 0]
1   )    pop 0 → 頂端 -1                        [-1]        1 - (-1) = 2
2   (    push                                  [-1, 2]
3   (    push                                  [-1, 2, 3]
4   )    pop 3 → 頂端 2                         [-1, 2]     4 - 2 = 2
結束  索引 2 的 ( 沒配對，把 [0,1] 和 [3,4] 隔開 → 答案 2
```

第二個例子說明了為什麼不能只數配對數：i = 4 配對成功時，頂端是還沒配對的索引 2，長度只算到它之後，所以得到 2 而不是 4。

**O(1) 空間的雙向掃描**。從左往右掃，維護 `open` 和 `close` 的個數：兩者相等時，目前這段是合法的，長度 `2 × close`；`close > open` 時，這個 `)` 一定無法配對，兩者歸零重新開始。這個做法會漏掉一種情況：`"(()"` 這類 `(` 一直多於 `)` 的字串，計數永遠不相等。所以再從右往左掃一次，規則對稱（`open > close` 時歸零），就能補上。兩次掃描各 O(n)，空間 O(1)。它的正確性和 stack 版本相同：左往右的歸零點是多出來的 `)`，右往左的歸零點是多出來的 `(`。

**DP 寫法**。`dp[i]` = 以 i 結尾的最長合法子字串長度。`s[i] == ")"` 時：若 `s[i-1] == "("`，`dp[i] = dp[i-2] + 2`；若 `s[i-1] == ")"`，看 `j = i - dp[i-1] - 1`，`s[j] == "("` 時 `dp[i] = dp[i-1] + 2 + dp[j-1]`（把前面並列的也接上）。O(n) 時間與空間。三種解法都值得知道，面試中 stack 版本最好解釋。

### 解法

```python
import random


def longest_valid_parentheses(s: str) -> int:
    stack = [-1]                       # 底部：最後一個無法配對的位置
    best = 0
    for i, ch in enumerate(s):
        if ch == "(":
            stack.append(i)
        else:
            stack.pop()
            if not stack:              # 這個 ) 無法配對，成為新的分隔線
                stack.append(i)
            else:
                best = max(best, i - stack[-1])
    return best


def longest_valid_two_pass(s: str) -> int:
    best = 0
    for seq, opener in ((s, "("), (reversed(s), ")")):
        open_cnt = close_cnt = 0
        for ch in seq:
            if ch == opener:
                open_cnt += 1
            else:
                close_cnt += 1
            if open_cnt == close_cnt:
                best = max(best, 2 * close_cnt)
            elif close_cnt > open_cnt:  # 多出來的「關」，這段不可能再合法
                open_cnt = close_cnt = 0
    return best


def longest_valid_dp(s: str) -> int:
    n = len(s)
    dp = [0] * n
    for i in range(1, n):
        if s[i] == ")":
            if s[i - 1] == "(":
                dp[i] = (dp[i - 2] if i >= 2 else 0) + 2
            else:
                j = i - dp[i - 1] - 1
                if j >= 0 and s[j] == "(":
                    dp[i] = dp[i - 1] + 2 + (dp[j - 1] if j >= 1 else 0)
    return max(dp, default=0)


def brute(s):
    def ok(t):
        d = 0
        for c in t:
            d += 1 if c == "(" else -1
            if d < 0:
                return False
        return d == 0
    n = len(s)
    return max((j - i for i in range(n + 1) for j in range(i, n + 1) if ok(s[i:j])), default=0)


for f in (longest_valid_parentheses, longest_valid_two_pass, longest_valid_dp):
    assert f("(()") == 2
    assert f(")()())") == 4
    assert f("()(())") == 6
    assert f("") == 0
    assert f("))((") == 0
    assert f("()(()") == 2
    assert f("(()())") == 6
for _ in range(2000):
    t = "".join(random.choice("()") for _ in range(random.randint(0, 12)))
    assert longest_valid_parentheses(t) == longest_valid_two_pass(t) == longest_valid_dp(t) == brute(t), t
print("all tests passed")
```

### 複雜度與邊界

三種解法時間都是 O(n)。空間：stack 版本 O(n)（最差情況全是 `(`）；雙向掃描 O(1)；DP 版本 O(n)。邊界情況：空字串回傳 0，stack 版本的迴圈不執行，雙向掃描與 DP 的 `max(..., default=0)` 也正確；開頭是 `)` 時，基準 -1 被彈出，該位置成為新基準；結尾有多出來的 `(` 時，stack 版本不需要特別處理，因為它們只會讓之後的長度從它們的位置算起；雙向掃描必須兩個方向都做，只做左往右會讓 `"(()"` 回傳 0。

### Follow-up

> [!question]- F1. 如果要回傳最長的合法子字串本身（或它的起訖位置）呢？
> 在 stack 版本中更新 best 時，同時記錄起點 `stack[-1] + 1` 與終點 i，最後回傳 `s[start:end + 1]`，O(n)。若有多個一樣長的，題目通常要求最左邊的，因為我們只在嚴格更大時更新，自然保留最先出現的那個。雙向掃描也能記錄位置，但右往左那一輪的索引要換算回原字串，容易出錯，這是 stack 版本在面試中更實用的原因之一。

> [!question]- F2. 如果還要回傳「最長合法子字串有幾個」呢？
> stack 版本在位置 i 算出的 `i - stack[-1]`，正好是「以 i 結尾的最長合法子字串」長度。每個最長的合法子字串都有唯一的結尾，而且在它的結尾處一定會被算到（以那裡結尾的最長合法子字串至少和它一樣長，又不可能更長），所以只要在算出的長度等於目前最大值時計數加一、嚴格更大時重設為 1 即可。沒有任何合法子字串時，依慣例回傳長度 0、個數 1。O(n)。

> [!question]- F3. 如果有三種括號 `()`、`[]`、`{}` 呢？
> stack 版本仍然適用，只要多檢查型別：遇到閉括號時，如果頂端是同型別的開括號（而且不是底部的基準），就 pop 並用 `i - stack[-1]` 更新長度；否則（型別不符，或只剩基準）這個位置不可能出現在任何合法子字串中，把 stack 整個清成 `[i]`，讓它成為新的分隔線。型別不符時頂端那些開括號也不可能再被配對，因為任何包含它們的合法子字串都會跨過 i。O(n)。雙向計數的 O(1) 解法在這裡失效，原因和核心題 1 F1 相同：計數器記不住型別。

> [!question]- F4. 如果要的是最長的合法括號**子序列**（可以刪掉字元，不必連續）呢？
> 問題變得簡單很多：用核心題 1 F2 的計數器貪婪配對，從左往右，遇到 `(` 計數加一，遇到 `)` 而計數 > 0 時配對成功、計數減一並把配對數加一。答案是 `2 × 配對數`，O(n) 時間、O(1) 空間。貪婪最佳的原因是：任何一個 `)` 只要前面有未配對的 `(` 就應該配對，延後配對不會讓結果變好。對比之下，子字串版本的難點全在「連續」，無法配對的字元會把字串切斷。

### 心得

關鍵突破是「無法配對的括號是分隔線，答案是相鄰分隔線之間的最大距離」，再用 stack 底部的基準把這個距離在掃描中直接算出來。它和核心題 1（20）的差別是：20 只問「全部合法嗎」，所以 stack 存字元；這題要算長度，所以 stack 改存索引，並多了一個基準元素。面試時建議先說 O(n²) 的固定左端擴展，再說 stack 版本，畫出 `")()())"` 的過程，強調 `-1` 基準與「pop 後為空就 push 自己」這兩個細節；若面試官追問 O(1) 空間，再說雙向掃描，並主動指出只掃一個方向會漏掉 `"(()"`。

## 難題 4｜224. Basic Calculator｜Hard

### 題目

給一個代表合法算術式的字串 `s`，計算並回傳它的值，**不能使用** `eval` 之類的內建求值函式。`s` 由數字、`+`、`-`、`(`、`)` 和空白組成；`+` 只作為二元運算子，`-` 可以是二元運算子，也可以是**一元負號**（例如 `"-1"`、`"-(2 + 3)"`、`"1 - (-2)"`）；不會有兩個運算子連續出現。所有數字與中間結果都在 32 位元整數範圍內。限制：`1 <= len(s) <= 3 × 10⁵`。

- 範例 1：`s = "1 + 1"`，回傳 `2`。
- 範例 2：`s = " 2-1 + 2 "`，回傳 `3`，空白可以出現在任何地方。
- 範例 3：`s = "(1+(4+5+2)-3)+(6+8)"`，回傳 `23`。
- 範例 4：`s = "1 - (4 + 5 - (3 - 2))"`，回傳 `-7`，括號前的負號要作用到整個括號。
- 範例 5（邊界）：`s = "-(2 + 3)"`，回傳 `-5`；`s = "2147483647"`，回傳 `2147483647`，單一個多位數。

### 提示

> [!tip]- 提示 1
> 只有加減法時，整個運算式就是一串「帶正負號的數字」相加。如果沒有括號，你只需要一個累加的 result 和「下一個數字的正負號」sign。括號帶來了什麼麻煩？

> [!tip]- 提示 2
> 遇到 `(` 時，括號外面的計算要暫停：目前的 result 還沒加完，括號前的 sign 要等括號算完之後才作用在整個括號上。把這兩個值存起來，從頭開始算括號裡面。

> [!tip]- 提示 3
> 遇到 `(` 就 push `(result, sign)`，然後 `result = 0, sign = 1`；遇到 `)` 就先把最後一個數字加進 result，再 pop 出 `(prev_result, prev_sign)`，令 `result = prev_result + prev_sign × result`。數字要累積多位數，空白直接跳過。

### 詳解

**為什麼直覺做法不夠**。一個直覺是遞迴：遇到 `(` 就遞迴計算括號內的值，遇到 `)` 就回傳。這是正確的 O(n) 做法，但 `s` 可以長到 3 × 10⁵，括號巢狀深度可能到 10⁵ 級，超過 Python 預設的遞迴上限（約 1000），直接 `RecursionError`；就算提高上限，深遞迴在 CPython 中也可能讓 C 層級的 stack 溢位而崩潰。另一個直覺是先用 shunting-yard（核心題 3 F1）轉成 RPN 再求值，可行，但一元負號需要額外處理（例如把它當成 `0 - x`），而且要兩遍掃描和額外的 token 陣列，對只有加減法的題目來說太重了。

**突破點：只有加減法時，每個數字的貢獻就是 ±它自己**。把 `1 - (4 + 5 - (3 - 2))` 完全展開，每個數字最後都只是帶著一個正負號被加進答案：`+1 −4 −5 +3 −2`。一個數字的最終正負號，是它前面的運算子與所有包住它的括號前的正負號的乘積。所以不需要真正的「運算子 stack」，只要在進入括號時記住外層的狀態，離開時合併。具體地，維護三個變數：`result`（目前這層括號內已經加總的值）、`sign`（下一個數字的正負號）、`num`（正在讀的多位數）。

**四種字元的處理**。數字：`num = num × 10 + digit`。`+` 或 `-`：前一個數字讀完了，`result += sign × num`，然後 `num = 0`，`sign` 設成 +1 或 −1；一元負號也走這條路，因為此時 `num = 0`，加進去不影響結果，只是把 sign 設成 −1。`(`：push `result` 和 `sign`，然後 `result = 0, sign = 1`，開始計算括號內。`)`：先 `result += sign × num` 收尾，再 pop 出外層的 `prev_sign` 與 `prev_result`，`result = prev_result + prev_sign × result`。最後迴圈結束時還要再加一次 `sign × num`，因為最後一個數字後面沒有運算子觸發它。

**正確性**。invariant：任何時刻，stack 中每一層存的是「進入那層括號之前，外層已經累積的 result」與「那層括號前的正負號」，目前的 `result` 是最內層括號中到目前為止的值。`)` 時把內層的值乘上括號前的正負號加回外層，正好就是展開括號的規則。stack 的大小等於目前的括號深度，和遞迴版本的呼叫深度相同，但存在 heap 上的 list 裡，不受遞迴上限影響。

```text
s = "1 - (4 + 5 - (3 - 2))"
步驟  字元  動作                                  result  sign  num  stack
 1    1     num = 1                                0      +1    1    []
 2    -     result += +1·1 = 1，sign = -1          1      -1    0    []
 3    (     push (1, -1)，result = 0，sign = +1    0      +1    0    [(1,-1)]
 4    4     num = 4                                0      +1    4
 5    +     result += 4，sign = +1                 4      +1    0
 6    5     num = 5                                4      +1    5
 7    -     result += 5 = 9，sign = -1             9      -1    0
 8    (     push (9, -1)，result = 0，sign = +1    0      +1    0    [(1,-1), (9,-1)]
 9    3     num = 3
10    -     result += 3 = 3，sign = -1             3      -1    0
11    2     num = 2
12    )     result += -1·2 = 1；pop (9,-1)
            result = 9 + (-1)·1 = 8                8      ...   0    [(1,-1)]
13    )     result += 0；pop (1,-1)
            result = 1 + (-1)·8 = -7              -7            0    []
結束  result + sign·num = -7
```

第 12 步把最內層 `(3 - 2) = 1` 乘上它前面的負號，併入外層得到 `9 − 1 = 8`；第 13 步再把 8 乘上最外層括號前的負號，併入 1 得到 −7。每個 `)` 只做常數次運算，所以整體 O(n)。

### 解法

```python
import random


def calculate(s: str) -> int:
    result, sign, num = 0, 1, 0
    stack: list[int] = []
    for ch in s:
        if ch.isdigit():
            num = num * 10 + int(ch)
        elif ch in "+-":
            result += sign * num            # 前一個數字讀完了
            num = 0
            sign = 1 if ch == "+" else -1   # 一元負號也走這裡：此時 num 為 0
        elif ch == "(":
            stack.append(result)            # 暫存外層的累積值與括號前的正負號
            stack.append(sign)
            result, sign = 0, 1
        elif ch == ")":
            result += sign * num
            num = 0
            result *= stack.pop()           # 括號前的正負號
            result += stack.pop()           # 外層的累積值
        # 空白直接略過
    return result + sign * num


def calculate_recursive(s: str) -> int:
    """遞迴版本：邏輯相同，但深度受限於 Python 的遞迴上限。"""
    pos = 0

    def parse() -> int:
        nonlocal pos
        result, sign, num = 0, 1, 0
        while pos < len(s):
            ch = s[pos]
            pos += 1
            if ch.isdigit():
                num = num * 10 + int(ch)
            elif ch in "+-":
                result += sign * num
                num, sign = 0, (1 if ch == "+" else -1)
            elif ch == "(":
                num = parse()                # 括號內的值當作一個數字
            elif ch == ")":
                break
        return result + sign * num

    return parse()


def gen(depth: int) -> str:
    """隨機產生合法運算式：一元負號只出現在開頭或左括號之後。"""
    def term(d):
        if d == 0 or random.random() < 0.4:
            return str(random.randint(0, 30))
        return "(" + expr(d - 1, True) + ")"

    def expr(d, allow_unary):
        parts = [("-" if allow_unary and random.random() < 0.3 else "") + term(d)]
        for _ in range(random.randint(0, 3)):
            parts.append(random.choice([" + ", " - ", "+", "-"]) + term(d))
        return "".join(parts)

    return expr(depth, True)


assert calculate("1 + 1") == 2
assert calculate(" 2-1 + 2 ") == 3
assert calculate("(1+(4+5+2)-3)+(6+8)") == 23
assert calculate("1 - (4 + 5 - (3 - 2))") == -7
assert calculate("-(2 + 3)") == -5
assert calculate("1 - (-2)") == 3
assert calculate("2147483647") == 2147483647
deep = "(" * 50000 + "1" + ")" * 50000          # 深度 5 萬：遞迴版本會失敗
assert calculate(deep) == 1
for _ in range(500):
    e = gen(4)
    assert calculate(e) == calculate_recursive(e) == eval(e), e   # eval 只用於測試
print("all tests passed")
```

### 複雜度與邊界

時間 O(n)：每個字元處理一次，每次 O(1)。空間 O(d)，d 是括號的最大巢狀深度，最差 O(n)。邊界情況：開頭的一元負號，因為 `result = 0`、`num = 0`，`result += sign × num` 不影響結果，只設定 sign；括號開頭的一元負號（`"(-2)"`）同理；`)` 之後緊接著運算子時，`num` 在 `)` 已經歸零，下一個運算子的 `result += sign × num` 加的是 0，不會重複計算括號的值；多位數要累積；空白可以出現在數字中間以外的任何地方，直接跳過；最後一個數字要在迴圈外加上。遞迴版本在深度 5 萬時會 `RecursionError`，這正是解法中用顯式 stack 的原因，測試裡也只對淺層運算式比對兩者。

### Follow-up

> [!question]- F1. 如果沒有括號，但有 `*` 和 `/`（227. Basic Calculator II）呢？
> 乘除的優先順序較高，所以不能邊讀邊加。用一個 stack 存「要被加總的項」，並記住前一個運算子 `op`：讀完一個數字 num 後，若 op 是 `+` 就 push num，`-` 就 push −num，`*` 就把頂端換成 `頂端 × num`，`/` 就換成「頂端除以 num 並向零取整」。最後回傳 stack 的總和。O(n) 時間；stack 其實可以壓縮成兩個變數（「已完成的總和」與「目前這一項」），空間 O(1)。
> ```python
> def calculate2(s):
>     stack, num, op = [], 0, "+"
>     for ch in s + "+":                   # 哨兵運算子，觸發最後一個數字
>         if ch.isdigit():
>             num = num * 10 + int(ch)
>         elif ch in "+-*/":
>             if op == "+": stack.append(num)
>             elif op == "-": stack.append(-num)
>             elif op == "*": stack.append(stack.pop() * num)
>             else: stack.append(int(stack.pop() / num))
>             op, num = ch, 0
>     return sum(stack)
> ```

> [!question]- F2. 如果同時有括號和 `+ - * /`（772. Basic Calculator III）呢？
> 把 F1 的邏輯包成一個函式 `parse()`，處理到 `)` 或字串結尾時回傳 stack 的總和；遇到 `(` 時遞迴呼叫 `parse()`，把回傳值當作一個數字 num，再照 op 處理。O(n) 時間、O(d) 空間。若擔心遞迴深度，可以把「每一層的 (stack, op)」存進一個外層的顯式 stack：遇到 `(` 就 push 目前的 `(stack, op)` 並重新開始，遇到 `)` 就算出總和、pop 回外層並把總和當作 num 處理。另一條路是 shunting-yard 轉 RPN（核心題 3 F1）再求值，一元負號可以在 `(` 之後或開頭補一個 0。

> [!question]- F3. 如果運算式裡有變數，例如 `"e + 8 - a + 5"` 並給定部分變數的值，要回傳化簡後的多項式（770. Basic Calculator IV）呢？
> 數值換成「多項式」：用字典把「變數的排序組合」對應到係數，例如 `{("a", "b"): 3, (): -2}` 代表 `3·a·b − 2`。加減是對應項的係數相加；乘法是兩兩項相乘、變數組合合併後排序。求值框架仍然是本題或 F2 的 stack，只是 stack 裡放多項式。這是第 29 章難題 5 的內容，難點在多項式的表示與輸出格式，stack 的部分和本題完全相同。

> [!question]- F4. 能不能只用一個「正負號的 stack」，不必保存外層的 result？
> 可以。每個數字的最終貢獻是 `±num`，正負號是「它前面的運算子」乘上「所有包住它的括號的正負號」。維護一個 stack，頂端是「目前這層括號的整體正負號」，初始為 `[1]`。讀到運算子時，`sign = stack[-1] × (±1)`；讀到 `(` 時 push 目前的 sign（括號前的運算子已經合併進去）；讀到 `)` 時 pop；讀完數字就 `result += sign × num`。result 只有一個，全程累加。O(n) 時間、O(d) 空間。這個寫法直接對應「展開括號」的數學，面試中說出它能展現對結構的理解。

### 心得

關鍵突破是「只有加減法時，括號只會改變正負號」，所以進入括號時只需要保存外層的 `(result, sign)`，離開時用一次乘法和一次加法合併回去。它和本章的關係是：核心題 1（20）用 stack 處理巢狀的「配對」，核心題 3（150）用 stack 處理「延後計算」，這題兩者都有：stack 的深度是括號的巢狀深度，每一層保存的是外層還沒完成的計算。面試時先釐清規則（有沒有乘除、`-` 能不能是一元、有沒有空白），再說「我用 stack 取代遞迴，避免深度問題」，寫完後用 `"1 - (4 + 5 - (3 - 2))"` 手動追一次，並主動測 `"-(2+3)"` 與 `"1-(-2)"` 兩個一元負號的情況。

## 難題 5｜907. Sum of Subarray Minimums｜Medium

### 題目

給一個正整數陣列 `arr`，考慮它所有 n(n + 1)/2 個**非空連續子陣列**，把每個子陣列的最小值加總，回傳總和對 `10⁹ + 7` 取餘數的結果。限制：`1 <= n <= 3 × 10⁴`，`1 <= arr[i] <= 3 × 10⁴`。

- 範例 1：`arr = [3, 1, 2, 4]`，子陣列有 `[3]、[1]、[2]、[4]、[3,1]、[1,2]、[2,4]、[3,1,2]、[1,2,4]、[3,1,2,4]`，最小值分別是 3、1、2、4、1、1、2、1、1、1，總和 `17`。
- 範例 2：`arr = [11, 81, 94, 43, 3]`，回傳 `444`。
- 範例 3（邊界）：`arr = [5]`，只有一個子陣列，回傳 `5`。
- 範例 4（邊界，重複值）：`arr = [2, 2, 2]`，六個子陣列的最小值都是 2，回傳 `12`。

### 提示

> [!tip]- 提示 1
> 不要枚舉子陣列，改成問：每個元素 `arr[i]` 是「多少個子陣列」的最小值？答案就是 `Σ arr[i] × 次數`。

> [!tip]- 提示 2
> `arr[i]` 是子陣列 `[l, r]` 的最小值，條件是 l 和 r 都沒有越過左右兩側第一個比它小的元素。若左邊第一個更小在 L、右邊第一個更小在 R，l 有 `i − L` 種選法，r 有 `R − i` 種選法。

> [!tip]- 提示 3
> 重複值會讓同一個子陣列被兩個相等的最小值重複計算。左邊用「嚴格更小」、右邊用「小於或等於」當邊界，讓每個子陣列只歸給最右邊的那個最小值。一次 monotonic stack 掃描同時得到兩個邊界。

### 詳解

**為什麼直覺做法不夠**。暴力解是固定左端 l、往右擴展 r，同時維護目前的最小值，每個子陣列 O(1)，總共 O(n²)；n = 3 × 10⁴ 時約 4.5 × 10⁸ 次操作，在 Python 中需要數分鐘。這個做法的問題是逐一處理子陣列，而子陣列的數量本身就是 O(n²)。要突破，就不能讓子陣列一個一個出現。

**突破點：貢獻法（contribution technique）**。換一個加總的順序：與其對每個子陣列找最小值，不如對每個元素數它是幾個子陣列的最小值。`arr[i]` 是子陣列 `[l, r]`（l ≤ i ≤ r）的最小值，當且僅當 `[l, r]` 裡沒有比 `arr[i]` 更小的元素。令 L 為 i 左邊第一個比 `arr[i]` 小的位置（沒有則為 −1），R 為右邊第一個比它小的位置（沒有則為 n），那麼 l 可以是 `L + 1 … i` 中任一個（`i − L` 種），r 可以是 `i … R − 1` 中任一個（`R − i` 種），共 `(i − L) × (R − i)` 個子陣列。L 和 R 正是 monotonic stack 的「左右第一個更小」。

**重複值：一邊嚴格、一邊非嚴格**。如果左右都用「嚴格更小」，`[2, 2]` 中兩個 2 都會認為 `[2, 2]` 這個子陣列以自己為最小值，重複計算（10.5 節的例子）。解法是替每個子陣列指定唯一負責的元素：**左邊界用嚴格更小，右邊界用小於或等於**。這樣 i 負責的子陣列 `[l, r]` 滿足「`[l, i)` 中沒有 < arr[i] 的元素」且「`(i, r]` 中沒有 ≤ arr[i] 的元素」，也就是說 arr[i] 是最小值，而且是最小值中最右邊的那一個。每個子陣列的「最右邊的最小值」是唯一的，所以恰好被算一次。

**一次掃描**。維護一個由底到頂嚴格遞增的 stack，條件 `arr[top] >= arr[i]` 時彈出 top。被彈出的那一刻，i 是 top 右邊第一個 ≤ 它的元素，也就是 R；彈出後的新頂端是 top 左邊第一個 < 它的元素，也就是 L（理由同難題 1）。於是在彈出時直接加上 `arr[top] × (top − L) × (i − top)`。尾端用 i = n 的哨兵（值視為 0）把所有剩下的元素逼出來。

```text
arr = [3, 1, 2, 4]，尾端哨兵 0（i = 4）
stack 存索引（括號內是值），由底到頂嚴格遞增

i  值  彈出 t  L（新頂端）  左選法 t-L  右選法 i-t  貢獻 arr[t]×左×右   stack 之後
0  3   —                                                           0(3)
1  1   0      -1           1           1           3 × 1 × 1 = 3   1(1)
2  2   —                                                           1(1) 2(2)
3  4   —                                                           1(1) 2(2) 3(4)
4  0   3       2           1           1           4 × 1 × 1 = 4
       2       1           1           2           2 × 1 × 2 = 4
       1      -1           2           3           1 × 2 × 3 = 6   4(0)
總和 = 3 + 4 + 4 + 6 = 17

檢查 arr[1] = 1 的 6 個子陣列：l ∈ {0, 1}，r ∈ {1, 2, 3}
  [3,1] [3,1,2] [3,1,2,4] [1] [1,2] [1,2,4]   → 每個的最小值都是 1 ✓
```

**另一種寫法：以 i 結尾的 DP**。令 `dp[i]` 為「所有以 i 結尾的子陣列的最小值總和」。若 p 是 i 左邊第一個嚴格更小的位置，那麼起點在 `(p, i]` 的子陣列最小值都是 `arr[i]`，共 `i − p` 個；起點在 `[0, p]` 的子陣列最小值和「以 p 結尾、起點相同」的子陣列一樣（因為 `arr[p] < arr[i]`，加上 `(p, i]` 的元素不會改變最小值），總和就是 `dp[p]`。所以 `dp[i] = dp[p] + arr[i] × (i − p)`，答案是 `Σ dp[i]`。這個寫法只需要「左邊第一個更小」，不必處理重複值的不對稱問題，也天生支援線上（見 F4）。

### 解法

```python
import random

MOD = 10**9 + 7


def sum_subarray_mins(arr: list[int]) -> int:
    n = len(arr)
    total = 0
    stack: list[int] = []                         # 索引，值由底到頂嚴格遞增
    for i in range(n + 1):
        cur = arr[i] if i < n else 0              # 哨兵：比所有元素都小
        while stack and arr[stack[-1]] >= cur:    # i 是 top 右邊第一個 <= 它的
            top = stack.pop()
            left = stack[-1] if stack else -1     # top 左邊第一個 < 它的
            total += arr[top] * (top - left) * (i - top)
        stack.append(i)
    return total % MOD


def sum_subarray_mins_dp(arr: list[int]) -> int:
    n = len(arr)
    dp = [0] * n                                  # dp[i]：以 i 結尾的子陣列最小值總和
    stack: list[int] = []
    for i, x in enumerate(arr):
        while stack and arr[stack[-1]] >= x:
            stack.pop()
        p = stack[-1] if stack else -1            # 左邊第一個嚴格更小
        dp[i] = (dp[p] if p >= 0 else 0) + x * (i - p)
        stack.append(i)
    return sum(dp) % MOD


def brute(arr):
    total = 0
    for l in range(len(arr)):
        low = arr[l]
        for r in range(l, len(arr)):
            low = min(low, arr[r])
            total += low
    return total % MOD


for f in (sum_subarray_mins, sum_subarray_mins_dp):
    assert f([3, 1, 2, 4]) == 17
    assert f([11, 81, 94, 43, 3]) == 444
    assert f([5]) == 5
    assert f([2, 2, 2]) == 12
    assert f([30000] * 30000) == 30000 * (30000 * 30001 // 2) % MOD   # 最大規模，檢查取餘
for _ in range(1000):
    a = [random.randint(1, 4) for _ in range(random.randint(1, 10))]
    assert sum_subarray_mins(a) == sum_subarray_mins_dp(a) == brute(a), a
print("all tests passed")
```

### 複雜度與邊界

兩種寫法時間都是 O(n)：每個索引 push、pop 各一次。空間 O(n)：stack（以及 DP 版本的 dp 陣列）。邊界情況：只有一個元素時，哨兵把它彈出，貢獻 `arr[0] × 1 × 1`；全部相等時，嚴格／非嚴格的不對稱保證每個子陣列只被算一次，`[2, 2, 2]` 的貢獻依序是 2 × 1 × 1、2 × 2 × 1、2 × 3 × 1，總和 12；陣列嚴格遞增時所有元素都留到哨兵才彈出。取餘：Python 整數不會溢位，所以最後再取一次餘數即可；總和最大約 3 × 10⁴ × (3 × 10⁴)² / 2 ≈ 1.35 × 10¹³，在 Java／C++ 中要用 64 位元整數，並在每次相加後取餘，因為單一項的乘積 `arr × 左 × 右` 最大約 3 × 10⁴ × (n / 2)² ≈ 6.75 × 10¹²，已經遠超過 32 位元。

### Follow-up

> [!question]- F1. 如果要的是所有子陣列「最大值減最小值」的總和（2104. Sum of Subarray Ranges）呢？
> 總和可以拆開：`Σ (max − min) = Σ max − Σ min`。最小值的總和就是本題；最大值的總和用對稱的方法，把 stack 改成由底到頂嚴格遞減、條件改成 `arr[top] <= cur`，哨兵改成正無限大。兩次 O(n) 掃描，總共 O(n)。這是「貢獻法」最直接的推廣：任何「對所有子陣列求某個極值的總和」，都可以拆成「每個元素當極值的次數 × 值」。

> [!question]- F2. 如果要最大化 `min(子陣列) × sum(子陣列)`（1856. Maximum Subarray Min-Product）呢？
> 對每個元素 i，以 `arr[i]` 為最小值的子陣列中，因為元素都是正數，範圍取到最大（L + 1 到 R − 1）時總和最大，所以只需要考慮這一個區間。用 prefix sum（第 7 章）O(1) 算出區間和，答案是 `max over i (arr[i] × (P[R] − P[L + 1]))`，最後才取餘。O(n)。注意這裡只要求極值，相等元素時左右都用嚴格或都用非嚴格都對；但若改成「求總和」，就要回到本題的不對稱規則。

> [!question]- F3. 如果每個子陣列的「強度」是 `min × sum`，要求所有子陣列強度的總和（2281. Sum of Total Strength of Wizards）呢？
> 仍然對每個 i 用貢獻法得到範圍 `(L, R)`（左嚴格、右非嚴格），但現在要加總的不是子陣列個數，而是所有包含 i 的子陣列 `[l, r]` 的 `sum(l..r)`。把 `sum(l..r) = P[r + 1] − P[l]` 代入，對 l 和 r 分別加總，會用到「prefix sum 的 prefix sum」，每個 i 可以 O(1) 算出。總時間 O(n)。這是第 7 章難題 5，本題是它的骨架。

> [!question]- F4. 如果陣列是串流，每來一個新元素，就要回報「到目前為止所有子陣列的最小值總和」呢？
> 用 DP 寫法：新元素 x 進來（索引 i）時，用 monotonic stack 找左邊第一個嚴格更小的 p，`dp[i] = dp[p] + x × (i − p)`，總答案 `ans += dp[i]`，因為新增的子陣列恰好是所有以 i 結尾的子陣列。每次更新 amortized O(1)。貢獻法的寫法在這裡不適用，因為元素的右邊界要等到未來才知道；這是兩種寫法最重要的差異。若只需要保存 stack 裡索引對應的 dp 值，記憶體是 O(stack 大小)，不必保存整個陣列。

### 心得

關鍵突破是貢獻法：把「對每個子陣列取最小值再加總」換成「每個元素乘上它當最小值的次數」，而次數由左右第一個更小的位置決定。它和難題 1（84）是同一個邊界問題：84 用「以 heights[i] 為高的最大寬度」求最大值，這題用「以 arr[i] 為最小值的子陣列個數」求總和；求總和時必須一邊嚴格、一邊非嚴格，這是本題最容易錯、也最常被追問的地方。面試時先說 O(n²) 的固定左端擴展，再說「我改成算每個元素的貢獻」，畫出 `(i − L) × (R − i)` 的選法，接著主動提出重複值的問題並用 `[2, 2]` 示範，最後才寫程式。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 括號配對與驗證 | 巢狀結構、「最近打開的最先關上」 | stack 存開括號；只有一種括號時壓成計數器 | 核心題 1（20）、921、1249、678 |
| 配對 + 長度 | 最長合法區間、要知道「哪一個」沒配對 | stack 存索引，底部放基準 -1 | 難題 3（32）、1249 |
| 巢狀狀態保存 | 帶括號的計算、解碼 `3[a2[c]]`、檔案路徑 | 進入時 push 外層狀態，離開時合併 | 難題 4（224）、772、394 Decode String、71 Simplify Path |
| 延後計算 | 後序運算式、運算子作用在最近的值上 | stack 存運算元，注意 pop 順序 | 核心題 3（150）、227、1628 |
| 每層彙總值 | 設計 stack 並 O(1) 查最小／最大 | 每層存「到這層為止」的彙總，或差值編碼 | 核心題 2（155）、716（第 27 章難題 3）、895（第 27 章難題 4） |
| 下一個更大／更小 | 「往右第一個」「要等幾天」 | 被彈出時記答案；找更大用遞減 stack | 核心題 4（739）、496、901、1019 |
| 環狀與第二個更大 | 環狀陣列、「第二個比它大」 | 走兩圈只在第一圈 push；兩個 stack 接力 | 核心題 5（503）、2454 |
| 以元素為高的最大矩形 | 面積、「被兩側較矮的擋住」 | 彈出時同時得到左右邊界；尾端哨兵 0 | 難題 1（84）、難題 2（85）、1793、221 |
| 貢獻法（計數／總和） | 「所有子陣列的最小值／最大值總和」 | `值 × (i − L) × (R − i)`，一邊嚴格一邊非嚴格 | 難題 5（907）、2104、1856、2281（第 7 章難題 5）、1504 |
| 貪婪刪除成最小序列 | 「刪 k 個數字讓結果最小」「字典序最小的子序列」 | 新元素較小就彈出較大的頂端，直到額度用完 | 402 Remove K Digits、316 Remove Duplicate Letters、1673 |
| 會過期的單調結構 | 滑動窗口的最大值／最小值 | monotonic deque：頂端解決、底端過期 | 第 6 章難題 2（239）、第 7 章難題 3（862） |

**下限與上限**。最簡單的形式是 20 題：stack 的用途一目了然，考的是 pop 前檢查是否為空、結束時檢查是否清空。往上一層是 739、503：模板本身不長，但要理解「被彈出時得到答案」與 amortized O(n) 的論證，並能處理嚴格與相等。上限的題目難在三個地方，常常同時出現：第一，**看出題目其實在問邊界**，84 問的是面積、907 問的是總和，都要先轉換成「每個元素往左右能延伸多遠」才會想到 monotonic stack；第二，**相等元素的不對稱處理**，求極值時隨便選都對，求總和或計數時必須一邊嚴格、一邊非嚴格，否則重複計算；第三，**和其他 pattern 組合**，85 把二維降成一維再套 84，2281 在 907 的骨架上再疊兩層 prefix sum，224 要同時處理巢狀、正負號與多位數解析。

**與其他 pattern 的關係**。stack 處理巢狀結構，本質上就是把遞迴改寫成迭代：224 的遞迴版本與 stack 版本一一對應，二元樹的 iterative inorder／preorder（第 12 章）、DFS 的迭代版本（第 15 章）也都是同一件事。monotonic stack 與 monotonic deque（第 6 章難題 2）的差別只在於元素會不會從底端「過期」：窗口固定或往右滑動時用 deque，否則用 stack。和 two pointers（第 5 章）的關係是：第 5 章難題 1 的 42 Trapping Rain Water 可以用 two pointers 做到 O(1) 空間，也可以用 monotonic stack 一層一層算水量，兩者都是 O(n)；1793 也同時有 stack 與 two pointers 兩種解法。和 DP（第 21 章）的關係是：32 與 907 都有 DP 寫法，而 907 的 DP 遞迴式 `dp[i] = dp[p] + arr[i] × (i − p)` 中的 p 正是用 monotonic stack 求的，stack 在這裡是 DP 的加速器。

**容易混淆之處**。第一，「下一個更大」不一定要 monotonic stack：如果值域很小（739 的 30 到 100），從右往左維護「每個值最近出現的位置」也行；如果要「右邊所有更大的元素中最小的那個」，那是有序集合（BST）的問題，不是 stack。第二，「最小值」相關的題目不一定能用貢獻法：若子陣列有長度限制（例如長度恰好是 k），範圍不再只由左右第一個更小決定，要改用 monotonic deque 或其他方法。第三，括號題不一定要 stack：只有一種括號時計數器就夠了，有萬用字元時（678）範圍計數比 stack 更簡潔；但多種括號、或需要知道位置時，stack 是必要的。

## 本章重點整理

- stack 頂端永遠是「最近一個還沒處理完的東西」；括號沒關上、運算元沒被使用、元素還沒等到答案，都是同一個結構。
- 巢狀結構用 stack 等同於遞迴，但不受遞迴深度限制；輸入可達 10⁵ 層時，顯式 stack 是必要的。
- monotonic stack 模板：`while stack and 比較(nums[stack[-1]], x): pop`，然後 `push(i)`；stack 一律存索引。
- 「被彈出時得到答案」求右邊第一個更大／更小；「彈完之後看頂端」求左邊最近的更大／更小；同一次掃描可以同時得到兩者。
- 口訣：找更大用遞減 stack、找更小用遞增 stack；每個索引進出各一次，總時間 amortized O(n)。
- 嚴格與非嚴格決定相等元素誰解決誰：題目要「嚴格更大」就用 `<`；只求極值時兩種都對；求總和或計數時左右必須一邊嚴格、一邊非嚴格。
- 尾端哨兵（84 的高度 0、907 的值 0）把所有剩下的元素逼出來，省掉迴圈後的清理程式。
- 環狀陣列走兩圈、第二圈只解決不 push；或從最大值的下一格開始走一圈。
- 最大矩形 = 對每根柱子求「以它為高」的最大寬度 `R − L − 1`；二維全 1 矩形逐列建直方圖，O(rows × cols)。
- 貢獻法：`Σ 子陣列最小值 = Σ arr[i] × (i − L) × (R − i)`；DP 寫法 `dp[i] = dp[p] + arr[i] × (i − p)` 只需要左邊界，且天生支援串流。
- Min Stack 每層存「到這層為止的最小值」，因為 stack 只從頂端改變，下面的彙總值永遠有效；從中間刪除（popMax）就失效。
- 運算式求值：RPN 先彈出的是右運算元；向零取整不能用 Python 的 `//`；只有加減法的計算機，括號只會改變正負號，進入時保存 `(result, sign)`。
- 最長合法括號：stack 底部保留「最後一個無法配對的位置」，長度是 `i − stack[-1]`；O(1) 空間要左右各掃一次。
