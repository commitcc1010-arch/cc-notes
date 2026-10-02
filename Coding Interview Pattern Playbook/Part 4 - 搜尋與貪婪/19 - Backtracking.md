---
chapter: 19
title: Backtracking
part: 4
---

# 第 19 章　Backtracking

> [!abstract] 本章地圖
> **一句話**：把「一步一步做選擇」畫成一棵決策樹，用 DFS 走這棵樹：每一步做一個選擇、往下遞迴、回來時把選擇撤銷；能提早判斷「這條路不可能成功」就整棵子樹剪掉。
>
> **辨識訊號**：
> - 題目要「列出所有」組合、排列、子集、切法、路徑、合法配置
> - n 很小：n ≤ 10 左右（排列）、n ≤ 20 左右（子集）、網格 ≤ 6 × 6、字串長度 ≤ 10
> - 答案本身的數量就是指數級，任何演算法都至少要花輸出大小的時間
> - 「填格子、放棋子、分組」並滿足一組限制（每列、每行、每條對角線、每個桶子）
> - 判定型問題是 NP-hard（分組、裝箱、精確覆蓋），而輸入規模刻意壓得很小
>
> **核心題**：78、46、39、17、79
>
> **難題**：51、37、282、698、1240

## 19.1 這個 Pattern 解決什麼問題

先看一個最小的例子：從 `[2, 3, 5]` 裡選出幾個數（可以都不選），列出所有和為 5 的選法。如果元素固定是 3 個，你可以寫三層迴圈，每層決定「選或不選」；但元素個數是輸入決定的，迴圈的層數不能寫死。這正是遞迴的用處：**一層遞迴處理一個決定**，遞迴深度跟著輸入走。把每個決定畫成樹的一層，所有可能的選法就是從根走到葉子的所有路徑，這棵樹稱為決策樹（decision tree）或狀態空間樹（state space tree）。

Backtracking（回溯）就是對這棵決策樹做 DFS。它和一般遞迴最大的差別在於**共用同一份可變的狀態**：走下去之前把選擇加進 `path`，遞迴回來之後把它拿掉，讓 `path` 恢復成進來時的樣子，再去試下一個選擇。因為每個節點不用複製整條路徑，所以每一步只花 O(1) 的狀態更新；只有在找到一個完整答案時，才把 `path` 複製一份存起來。「回溯」這個名字指的就是那一步撤銷：試完一條路之後，退回分岔點，換一條走。

Backtracking 本身沒有讓問題變簡單：所有子集仍然有 2ⁿ 個、所有排列仍然有 n! 個。它真正省下工作量的地方是**剪枝（pruning）**：在還沒走到葉子之前，如果已經能判斷「這條路不可能成為答案」，就不必再往下走，整棵子樹直接跳過。以和為 5 的例子來說，若把數字排序後已經選了 `[3]`，下一個候選 5 會讓和超過 5，那麼 5 之後更大的數也一定超過，迴圈可以直接 `break`。好的剪枝能讓理論上 9⁸¹ 種填法的數獨在幾毫秒內解完，也能讓邊長 13 以內的矩形最少正方形拼貼問題（難題 5）每個尺寸只搜尋至多約兩萬個節點。

所以本章每一題都會回答同三個問題：**決策樹的每一層在決定什麼？每個節點有哪些選擇？什麼時候可以剪枝？** 子集是「這個元素要不要」，排列是「這個位置放誰」，數獨是「這一格填幾」，N-Queens 是「這一列的皇后放哪一行」。框架完全相同，難度全在剪枝與狀態設計。

## 19.2 辨識訊號

| 題目特徵 | 為什麼是 backtracking | 本章哪一題 |
|---|---|---|
| 「回傳所有子集／組合」 | 每個元素「選或不選」，決策樹的葉子就是答案 | 核心題 1（78）、核心題 3（39） |
| 「回傳所有排列」 | 每個位置「放哪個還沒用過的元素」 | 核心題 2（46） |
| 每一位有固定幾種選擇，求所有組合 | 笛卡兒積（Cartesian product），深度 = 位數 | 核心題 4（17） |
| 網格中找一條不重複走格子的路徑 | 路徑上的 visited 只屬於這條路，回來要復原 | 核心題 5（79） |
| 放置物件並滿足多組限制（列、行、對角線、宮） | 一次填一格或一列，違反限制立刻剪枝 | 難題 1（51）、難題 2（37） |
| 在字元之間插入運算子、切字串 | 每個間隙是一個決定，運算的副作用要能 O(1) 撤銷 | 難題 3（282） |
| 「能否分成 k 組」「最少用幾塊」而 n ≤ 16 | NP-hard，只能搜尋；用排序、對稱破除、上界剪枝 | 難題 4（698）、難題 5（1240） |

一個實用的反向檢查：如果題目只問「有幾種」或「最少／最多是多少」，而子問題的答案只由一個小狀態決定（例如「從第 i 個開始、剩下 t」），那麼 backtracking 會重複走相同的子樹，應該加 memoization 變成 DP（第 21–24 章）。Backtracking 適合的是「要列出路徑本身」或「狀態太大無法記憶」的情況。

## 19.3 模板與原理

所有 backtracking 都是同一個骨架：檢查是否到達終點 → 列舉這一層的選擇 → 做選擇、遞迴、撤銷。下面三個模板涵蓋本章所有題目：**組合型**用 `start` 控制「只往後選」，**排列型**用 `used` 記錄「誰已經用過」，**判定型**找到一個解就一路回傳 `True`。

```python
def subsets_template(nums: list[int]) -> list[list[int]]:
    """組合型：每個節點本身就是一個答案；children 只能選 start 之後的元素。"""
    res, path = [], []

    def dfs(start: int) -> None:
        res.append(path[:])               # 記錄答案時一定要複製
        for i in range(start, len(nums)):
            path.append(nums[i])          # 做選擇
            dfs(i + 1)                    # 下一層只能選 i 之後的元素
            path.pop()                    # 撤銷選擇

    dfs(0)
    return res


def permutations_template(nums: list[int]) -> list[list[int]]:
    """排列型：深度 = 位置；每一層從所有還沒用過的元素中挑一個。"""
    res, path, used = [], [], [False] * len(nums)

    def dfs() -> None:
        if len(path) == len(nums):
            res.append(path[:])
            return
        for i in range(len(nums)):
            if used[i]:
                continue
            used[i] = True
            path.append(nums[i])
            dfs()
            path.pop()
            used[i] = False

    dfs()
    return res


def exists_subset_sum(nums: list[int], target: int) -> bool:
    """判定型：找到一個解就停；排序後可以用 break 剪枝。"""
    nums = sorted(nums)

    def dfs(start: int, remain: int) -> bool:
        if remain == 0:
            return True
        for i in range(start, len(nums)):
            if nums[i] > remain:          # 後面只會更大，整個迴圈都不必再試
                break
            if dfs(i + 1, remain - nums[i]):
                return True               # 一路往上回傳，不再搜尋其他分支
        return False

    return dfs(0, target)


assert sorted(subsets_template([1, 2, 3])) == sorted(
    [[], [1], [2], [3], [1, 2], [1, 3], [2, 3], [1, 2, 3]])
assert subsets_template([]) == [[]]
assert len(subsets_template(list(range(10)))) == 1024
assert sorted(permutations_template([1, 2, 3])) == [
    [1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]]
assert permutations_template([]) == [[]]
assert len(permutations_template(list(range(6)))) == 720
assert exists_subset_sum([2, 3, 5], 5) is True
assert exists_subset_sum([2, 4, 6], 5) is False
assert exists_subset_sum([], 0) is True
print("all tests passed")
```

**Invariant（不變式）**。三個模板都維持同一件事：**進入 `dfs` 時，`path`（與 `used`）精確描述「從根走到目前節點」所做的選擇；離開 `dfs` 時，狀態恢復成進入時的樣子**。只要每個「做選擇」都有對應的「撤銷」，而且兩者之間只隔著一次遞迴呼叫，這個 invariant 就自動成立：遞迴呼叫本身也遵守它，所以回來時狀態不變，我們撤銷自己的那一步，就回到了迴圈開始前的狀態。所有 backtracking 的 bug，幾乎都是破壞了這個 invariant：忘了撤銷、撤銷了別的東西、或在撤銷之前就 `return`。

**每一行為什麼這樣寫**：

- `res.append(path[:])`：`path` 是整棵樹共用的同一個串列，若直接 `res.append(path)`，最後 `res` 裡的每個元素都會指向同一個串列，而它在搜尋結束時是空的。複製的成本是 O(答案長度)，這也是為什麼列舉子集的總時間是 O(n · 2ⁿ) 而不是 O(2ⁿ)。
- `dfs(i + 1)` 而不是 `dfs(start + 1)`：下一層必須從「剛剛選的元素之後」開始，才能保證 path 中的索引嚴格遞增；寫成 `start + 1` 會讓 `[1, 3]` 之後又能選 2，產生重複的組合。若元素可以重複使用（核心題 3），就寫 `dfs(i)`。
- 排列型的 `for i in range(len(nums))` 每層都從 0 開始：排列在乎順序，`[2, 1]` 與 `[1, 2]` 是不同答案，所以每個位置都要考慮所有還沒用過的元素，靠 `used` 排除已用的。
- 判定型的 `if dfs(...): return True`：找到解之後不再撤銷也沒關係，因為整個搜尋會立刻結束；但如果題目是「找到之後還要繼續數」，就不能提前 return，必須照常撤銷。
- 組合型把 `res.append` 放在函式開頭、沒有終止條件：因為「每個節點都是一個答案」，而且迴圈在 `start == len(nums)` 時自然不執行，遞迴自動停止。

**組合型 vs 排列型，怎麼選**。問自己一句話：**`[1, 2]` 和 `[2, 1]` 算不算同一個答案？** 算同一個（子集、組合、組合總和）就用 `start`，強制只往後選，每個集合只會以「索引遞增」的一種順序出現；算不同（排列、排列式填空）就用 `used`。第三種常見結構是「每一層的選擇集合固定」，例如核心題 4 每一位數字對應幾個字母、難題 3 每個間隙有四種運算子，這時既不需要 `start` 也不需要 `used`，深度就是位置。

## 19.4 搜尋樹的大小：backtracking 的複雜度怎麼算

Backtracking 的時間 ≈ **節點數 × 每個節點的工作量 + 答案數 × 複製成本**。面試時不要只說「指數級」，要說出是哪一個指數，因為它決定了題目的 n 能開多大，也是面試官判斷你是否真的理解搜尋空間的依據。

| 搜尋類型 | 葉子數 | 總節點數 | 含複製的總時間 | 實務上可接受的 n |
|---|---|---|---|---|
| 子集（選或不選） | 2ⁿ | 2ⁿ⁺¹ − 1（二元樹）或 2ⁿ（start 寫法） | O(n · 2ⁿ) | n ≤ 20 |
| 大小為 k 的組合 | C(n, k) | O(C(n, k) · k) 以內（有剪枝） | O(k · C(n, k)) | C(n, k) ≤ 10⁶ 左右 |
| 排列 | n! | Σ n!/(n−d)! ≈ e · n! | O(n · n!) | n ≤ 9 或 10 |
| 每位 b 種選擇、深度 L | bᴸ | O(bᴸ) | O(L · bᴸ) | bᴸ ≤ 10⁶ 左右 |
| 網格路徑（不重複格子） | 至多 m · n · 3ᴸ⁻¹ | 同左 | O(m · n · 3ᴸ) | 網格與 L 都小 |

```text
排列 [1, 2, 3] 的決策樹：每一層決定一個位置
深度 0                     []                         1 個節點
                   /        |        \
深度 1          [1]        [2]        [3]             3 個節點
               /   \      /   \      /   \
深度 2     [1,2] [1,3] [2,1] [2,3] [3,1] [3,2]        3·2 = 6 個節點
             |     |     |     |     |     |
深度 3   [1,2,3] [1,3,2] ...                          3·2·1 = 6 個葉子

總節點 1 + 3 + 6 + 6 = 16 ≈ e · 3! = 16.3；每個葉子複製 3 個元素
```

兩個重要觀念。第一，**輸出大小是下限**：要列出全部 n! 個排列，就算演算法再聰明也至少要寫出 n · n! 個數字，所以 O(n · n!) 已經是最佳，面試官不會期待更好，反而會看你能不能說出這一點。第二，**有剪枝時，最差複雜度通常寫不出更緊的界**：N-Queens 的實際節點數遠小於 n!，數獨遠小於 9⁸¹，但沒有好用的封閉公式；面試時說「最差是 O(n!)，剪枝讓實際節點數小很多，例如 n = 8 時大約只走兩千個節點」比亂寫一個看起來精確的公式好。

遞迴深度也要估：深度等於決策的層數（子集是 n、排列是 n、數獨是空格數 ≤ 81），都遠小於 Python 預設的遞迴上限 1000，所以本章的題目不需要調整 `sys.setrecursionlimit`。額外空間是 O(深度)，不含輸出。

## 19.5 剪枝、去重與搜尋順序

剪枝的種類不多，記住下面五種，看到新題目時逐一問「這題能用哪幾種」：

1. **可行性剪枝**：目前的部分解已經違反限制，例如和已經超過 target、這一行已經有皇后。排序之後常能把 `continue` 升級成 `break`，因為後面的候選只會更糟。
2. **上界剪枝（branch and bound，分支定界）**：求最小值時，若「目前已用的數量 ≥ 已知最佳解」，這條路不可能更好。初始的最佳解越好，剪得越多，所以常先用一個貪婪或 DP 求一個上界（難題 5）。
3. **去重**：輸入有重複值時，同一層不要選兩個相同的值。標準寫法是先排序，再在迴圈中加 `if i > start and nums[i] == nums[i - 1]: continue`。
4. **對稱破除（symmetry breaking）**：多個選擇在結構上等價時只試一個，例如幾個桶子目前裝的和一樣，把下一個數放進其中任何一個都會得到同構的子樹（難題 4）；N-Queens 的左右鏡像只需要搜一半。
5. **搜尋順序**：先試「最可能失敗」或「限制最多」的選擇，能讓錯誤更早暴露。數獨先填候選數最少的格子（MRV，minimum remaining values），分組問題先放最大的數，拼貼問題先試最大的正方形。

**去重的精確意義**。以 `[1, 2, 2]` 的子集為例，兩個 2 分別在索引 1、2。在同一層（同一個 `start`）中，選索引 1 的 2 和選索引 2 的 2 會長出完全相同的子樹，後者必須跳過；但在**不同層**（先選索引 1 的 2，下一層再選索引 2 的 2）得到的是 `[2, 2]`，這是合法的新答案，不能跳過。條件 `i > start` 正好區分這兩種情況：`i == start` 代表它是這一層的第一個候選，一定要試；`i > start` 且和前一個相同，代表這一層已經試過這個值。

```python
def subsets_with_dup(nums: list[int]) -> list[list[int]]:
    nums = sorted(nums)                      # 相同的值必須相鄰，去重才有意義
    res, path = [], []

    def dfs(start: int) -> None:
        res.append(path[:])
        for i in range(start, len(nums)):
            if i > start and nums[i] == nums[i - 1]:
                continue                     # 同一層已經試過這個值
            path.append(nums[i])
            dfs(i + 1)
            path.pop()

    dfs(0)
    return res


assert sorted(subsets_with_dup([1, 2, 2])) == sorted(
    [[], [1], [1, 2], [1, 2, 2], [2], [2, 2]])
assert subsets_with_dup([0]) == [[], [0]]
assert len(subsets_with_dup([2, 2, 2, 2])) == 5           # 0 到 4 個 2
assert len(subsets_with_dup([1, 1, 2, 2, 3])) == 3 * 3 * 2  # 每個值選 0..次數 個
print("all tests passed")
```

```text
nums = [1, 2, 2]，同一層的第二個 2 被跳過（✗）
                     []
          /          |          \
        [1]        [2]a        [2]b ✗（i=2 > start=0 且 nums[2] == nums[1]）
       /    \        |
  [1,2]a  [1,2]b ✗  [2,2]      ← [2]a 下一層 start=2，i == start，不跳過
     |
  [1,2,2]
答案：[] [1] [1,2] [1,2,2] [2] [2,2]，共 6 個 = (1+1)·(2+1)
```

**什麼時候該改用 DP**。如果「從這個節點往下能得到什麼」只取決於一個小的狀態（例如 `(start, remain)`），不同路徑走到相同狀態時子樹完全一樣，那就該 memoization，從 backtracking 變成 DP。反之，若狀態必須包含整條路徑（例如核心題 5 的 visited 集合、N-Queens 已占用的對角線），可能的狀態太多，memoization 沒有效果。介於中間的情況是 bitmask：n ≤ 16 時「哪些元素已經用過」可以壓成一個整數，狀態只有 2ⁿ 個，難題 4 就同時給出 backtracking 與 bitmask DP 兩種解（詳見第 24 章）。

## 19.6 常見錯誤

| 錯誤 | 症狀 | 怎麼避免 |
|---|---|---|
| `res.append(path)` 沒有複製 | 結果全部是空串列，或全部長得一樣 | 記錄答案時寫 `path[:]` 或 `list(path)`；字串不可變則不必 |
| 做了選擇卻沒撤銷（或撤銷寫在 `return` 之後） | 答案混進上一條路徑的元素，數量不對 | 「做選擇／遞迴／撤銷」三行寫在一起；提前 return 只用在找到解就結束的判定型 |
| 組合題寫成 `dfs(start + 1)` | 出現 `[1, 3, 2]` 這類重複組合 | 下一層從 `i + 1` 開始（可重用時是 `i`） |
| 去重寫成 `i > 0` 而不是 `i > start` | `[1, 2, 2]` 的 `[2, 2]` 不見了 | 只跳過「同一層」的重複值；並記得先排序 |
| 排列去重的條件寫反 | 排列 II 少答案或仍有重複 | 用 `used[i - 1]` 為 False 時跳過，或改用 `Counter` 列舉不同的值 |
| 網格搜尋用全域 visited 而不復原 | 79 題在某些盤面誤判為找不到 | 標記只屬於目前路徑，回來時恢復原字元 |
| 沒有排序就用 `break` 剪枝 | 漏掉後面其實可行的較小候選 | `break` 依賴「後面只會更大」，必須先排序；否則只能 `continue` |
| 用字串 `+` 累積長路徑 | 每個節點 O(L) 複製，常數變大 | 用 list 當 path，到葉子才 `"".join` |
| 求最小值卻沒有上界剪枝 | 小輸入正確、大輸入超時 | 維護全域最佳解，`count >= best` 立刻 return；先用貪婪或 DP 求初始上界 |

## 核心題 1｜78. Subsets｜Medium

### 題目

給一個整數陣列 `nums`，其中**元素互不相同**。請回傳它的所有子集（power set，冪集），也就是從中挑出任意個元素（包含 0 個與全部）所能形成的所有集合。答案不能包含重複的子集，子集之間與子集內部的順序都不限。限制：`1 <= len(nums) <= 10`，`-10 <= nums[i] <= 10`。

- 範例 1：`nums = [1, 2, 3]`，回傳 `[[], [1], [2], [3], [1, 2], [1, 3], [2, 3], [1, 2, 3]]`，共 2³ = 8 個。
- 範例 2：`nums = [5, -1]`，回傳 `[[], [5], [-1], [5, -1]]`。
- 範例 3（邊界）：`nums = [0]`，回傳 `[[], [0]]`；空集合一定要包含在內。

### 思路

先想「要產生多少東西」：每個元素有「選」與「不選」兩種可能，n 個元素共 2ⁿ 種組合，每個子集平均長度 n/2，所以光是輸出就要 Θ(n · 2ⁿ)。這代表任何正確的解法都至少這麼慢，我們的目標不是降低指數，而是**每個子集恰好產生一次、且每個節點的工作量是 O(1)**（除了複製答案）。最天真的錯誤做法是「每次從所有元素中挑一個加進去」，那其實是在產生排列，`[1, 2]` 和 `[2, 1]` 都會出現，還得用 set 去重，浪費 k! 倍的工作。

有兩種等價的決策樹。**寫法 A：選或不選**。第 i 層決定 `nums[i]` 要不要放進子集，左子樹不放、右子樹放，深度固定是 n，2ⁿ 個葉子各對應一個子集，答案只在葉子收集。**寫法 B：下一個選誰**（start 寫法）。每個節點本身就是一個子集；它的子節點是「再加入一個索引比目前最後一個更大的元素」。因為 path 中的索引嚴格遞增，每個集合只會以唯一一種順序出現，所以不會重複。寫法 B 的樹恰好有 2ⁿ 個節點，每個節點就是一個答案，沒有任何浪費。

還有一個不需要遞迴的方法：把 0 到 2ⁿ − 1 的每個整數 mask 看成一個子集，第 i 個 bit 是 1 就代表選了 `nums[i]`。這和寫法 A 是同一棵樹，只是用二進位計數取代遞迴。面試時三種都可以，建議先寫寫法 B，因為它是本章其他組合題（39、40、77、90）的共同骨架，能直接延伸到 follow-up。

```text
寫法 B（start 寫法），nums = [1, 2, 3]；每個節點都記錄一次
dfs(start=0) path=[]          記錄 []
├─ 選 1 → dfs(1) path=[1]     記錄 [1]
│   ├─ 選 2 → dfs(2) [1,2]    記錄 [1,2]
│   │   └─ 選 3 → dfs(3) [1,2,3]  記錄 [1,2,3]   （迴圈 range(3,3) 為空，自然返回）
│   └─ 選 3 → dfs(3) [1,3]    記錄 [1,3]
├─ 選 2 → dfs(2) path=[2]     記錄 [2]
│   └─ 選 3 → dfs(3) [2,3]    記錄 [2,3]
└─ 選 3 → dfs(3) path=[3]     記錄 [3]

寫法 A（選或不選），葉子才是答案
                    i=0: 1?
             不選 /        \ 選
              i=1: 2?        i=1: 2?
             /    \          /    \
          i=2:3? i=2:3?   i=2:3? i=2:3?
          / \     / \      / \     / \
         [] [3] [2][2,3] [1][1,3][1,2][1,2,3]
```

寫法 B 的走訪順序就是字典序：`[] → [1] → [1,2] → [1,2,3] → [1,3] → [2] → [2,3] → [3]`。注意 `[1, 2, 3]` 之後 path 先 pop 掉 3 回到 `[1, 2]`，迴圈結束再 pop 掉 2 回到 `[1]`，接著試 3 得到 `[1, 3]`；整個過程 path 只有一份，靠撤銷恢復狀態。寫法 A 有 2ⁿ⁺¹ − 1 個節點，比寫法 B 多一倍，但兩者都是 O(2ⁿ) 個節點。

### 解法

```python
from itertools import combinations
import random


def subsets(nums: list[int]) -> list[list[int]]:
    """寫法 B：start 寫法，每個節點都是一個答案。"""
    res, path = [], []

    def dfs(start: int) -> None:
        res.append(path[:])
        for i in range(start, len(nums)):
            path.append(nums[i])
            dfs(i + 1)
            path.pop()

    dfs(0)
    return res


def subsets_take_or_skip(nums: list[int]) -> list[list[int]]:
    """寫法 A：第 i 層決定 nums[i] 選或不選，只在葉子收集。"""
    res, path = [], []

    def dfs(i: int) -> None:
        if i == len(nums):
            res.append(path[:])
            return
        dfs(i + 1)                 # 不選 nums[i]
        path.append(nums[i])
        dfs(i + 1)                 # 選 nums[i]
        path.pop()

    dfs(0)
    return res


def subsets_bitmask(nums: list[int]) -> list[list[int]]:
    n = len(nums)
    return [[nums[i] for i in range(n) if mask >> i & 1] for mask in range(1 << n)]


def normalize(sets):
    return sorted(tuple(sorted(s)) for s in sets)


assert normalize(subsets([1, 2, 3])) == normalize(
    [[], [1], [2], [3], [1, 2], [1, 3], [2, 3], [1, 2, 3]])
assert normalize(subsets([5, -1])) == normalize([[], [5], [-1], [5, -1]])
assert subsets([0]) == [[], [0]]
assert subsets([]) == [[]]
assert len(subsets(list(range(10)))) == 1024
for _ in range(200):
    arr = random.sample(range(-10, 11), random.randint(0, 7))
    expect = normalize(c for r in range(len(arr) + 1) for c in combinations(arr, r))
    assert normalize(subsets(arr)) == expect
    assert normalize(subsets_take_or_skip(arr)) == expect
    assert normalize(subsets_bitmask(arr)) == expect
print("all tests passed")
```

### 複雜度與邊界

時間 O(n · 2ⁿ)：寫法 B 有 2ⁿ 個節點，每個節點的迴圈與 append／pop 合計 O(1) 攤銷，但每個節點都要複製一次 path，平均長度 n/2，所以總共 Θ(n · 2ⁿ)，和輸出大小相同，已經是最佳。空間：遞迴深度與 path 最多 n，額外空間 O(n)；輸出本身是 O(n · 2ⁿ)。邊界情況：空陣列回傳 `[[]]`（空集合仍是唯一的子集）；負數與 0 不影響，因為我們只看索引不看值；題目保證元素互不相同，若有重複就會產生重複子集，見 F1。

### Follow-up

> [!question]- F1. 如果 nums 可以有重複元素呢（90. Subsets II）？
> 先排序讓相同的值相鄰，再在 start 寫法的迴圈中加上 `if i > start and nums[i] == nums[i - 1]: continue`，意思是「同一層已經試過這個值，就不要再試一次」，但不同層仍可以連續選相同的值，所以 `[2, 2]` 不會被漏掉（19.5 節有完整的樹）。答案個數是 Π(cᵥ + 1)，cᵥ 是每個值出現的次數，時間 O(n · 答案數)，最差仍是 O(n · 2ⁿ)。另一種寫法是用 `Counter` 列出不同的值，每一層決定「這個值選 0 到 cᵥ 個」，邏輯上完全沒有去重的陷阱。

> [!question]- F2. 如果只要大小恰好為 k 的子集呢（77. Combinations）？
> 在 path 長度到 k 時記錄並 return。關鍵剪枝是「剩下的元素不夠湊滿 k 個就不要往下走」：迴圈上界改成 `range(start, n - (k - len(path)) + 1)`，因為從 i 開始還剩 n − i 個元素，必須 ≥ k − len(path)。沒有這個剪枝時，搜尋會走進大量注定湊不滿的子樹（例如 n = 20、k = 18 時絕大多數節點都是死路）；加上之後每個走到的節點都至少能延伸出一個答案，時間是 O(k · C(n, k))，與輸出大小同階。

> [!question]- F3. 如果 n = 40，只問「有沒有子集的和恰好是 target」或「有幾個」呢？
> 2⁴⁰ ≈ 10¹² 無法列舉，但可以用 meet in the middle（折半列舉）：把陣列切成兩半，各自列舉 2²⁰ ≈ 10⁶ 個子集和，把右半的和放進 `Counter`，再對左半每個和 s 查詢 `target − s` 出現幾次，總時間 O(2^(n/2) · n)，或排序加 two pointers。若元素是非負整數且 target 不大，則改用 0/1 背包 DP（第 23 章核心題 1 的 416 題同型），時間 O(n · target)，與 n 的指數無關。這個 follow-up 的重點是：backtracking 的指數是由「要列出所有答案」決定的，只問存在或計數時就有更好的方法。

> [!question]- F4. 如果 2ⁿ 個子集放不進記憶體，或要依序處理每個子集並維護它的和呢？
> 改成 generator，用 `yield` 一次產出一個子集，記憶體只剩 O(n)。若處理每個子集時需要它的元素和，可以用 Gray code（格雷碼）順序列舉：第 i 個子集的 mask 是 `i ^ (i >> 1)`，相鄰兩個 mask 恰好只差一個 bit，所以從上一個子集到下一個只要加入或移除一個元素，和可以 O(1) 更新，總時間 O(2ⁿ) 而不是 O(n · 2ⁿ)。改變的 bit 是 `i` 的最低位 1 的位置，可以用 `(i & -i).bit_length() - 1` 求得。

> [!question]- F5. 如果元素都是正數，只要列出和 ≤ limit 的子集呢？
> 先排序，再在 start 寫法中加剪枝：若 `cur_sum + nums[i] > limit` 就 `break`，因為後面的元素更大，加進去只會更超過。這樣搜尋只會走到「本身就是答案」的節點，時間變成 O(n · 答案數)，屬於 output-sensitive（輸出敏感）的複雜度。若元素可能是負數，`break` 就不成立了：後面的負數可能把和拉回來，只能改用「剩餘負數總和」當下界做較弱的剪枝，或者直接列舉全部再過濾。

## 核心題 2｜46. Permutations｜Medium

### 題目

給一個**元素互不相同**的整數陣列 `nums`，回傳它的所有排列（permutation），也就是把所有元素各用一次、排成一列的所有方式，順序不限。限制：`1 <= len(nums) <= 6`，`-10 <= nums[i] <= 10`。

- 範例 1：`nums = [1, 2, 3]`，回傳 `[[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]]`，共 3! = 6 個。
- 範例 2：`nums = [0, 1]`，回傳 `[[0, 1], [1, 0]]`。
- 範例 3（邊界）：`nums = [7]`，回傳 `[[7]]`，只有一種排列。

### 思路

最直接的暴力做法是對 n 個位置各自從 n 個元素中任選一個，產生 nⁿ 個序列，再過濾掉有重複元素的。n = 6 時 6⁶ = 46656，其中只有 720 個是排列，98% 的工作都浪費了。浪費的原因是我們等到序列填滿才檢查「有沒有重複用到元素」，而這個檢查其實在放下第二個重複元素的當下就能做。

把檢查提前，就是 backtracking：第 d 層決定第 d 個位置放誰，只從**還沒用過**的元素中選。用一個布林陣列 `used` 記錄哪些索引已經在 path 裡，進入下一層前設 True、回來後設 False。這樣每一條根到葉的路徑都是合法排列，葉子恰好 n! 個，不再有任何無效的序列。不變式是：`used[i]` 為 True 若且唯若 `nums[i]` 在目前的 path 中。

另一種常見寫法是**原地交換**（swap）：第 d 層把 `nums[d..n-1]` 中的每個元素輪流換到位置 d，遞迴處理 d + 1，回來再換回去。它不需要 `used` 和 `path`，陣列前 d 格就是目前的 path，後面是還沒用過的元素。缺點是輸出順序不是字典序，而且「換回去」這一步很容易忘；面試時兩種都可以，`used` 寫法比較好延伸到有重複元素的版本（F1）。

```text
used 寫法，nums = [1, 2, 3]
path=[]        used=[F,F,F]  可選 {1,2,3}
├ 放 1  path=[1]      used=[T,F,F]  可選 {2,3}
│ ├ 放 2  path=[1,2]    used=[T,T,F]  可選 {3}
│ │ └ 放 3  path=[1,2,3]  記錄 → 撤銷 3
│ │ 撤銷 2  used=[T,F,F]
│ └ 放 3  path=[1,3]    used=[T,F,T]  可選 {2}
│   └ 放 2  path=[1,3,2]  記錄
├ 放 2  path=[2]  … 產生 [2,1,3]、[2,3,1]
└ 放 3  path=[3]  … 產生 [3,1,2]、[3,2,1]

swap 寫法，第 d 層把 nums[d..] 的每個元素換到位置 d
d=0  [1,2,3] → 換 (0,0) [1|2,3]、換 (0,1) [2|1,3]、換 (0,2) [3|2,1]
d=1  以 [1|2,3] 為例 → 換 (1,1) [1,2|3]、換 (1,2) [1,3|2]
```

used 寫法的每一層都把 0 到 n − 1 掃一遍，靠 `used` 跳過已用的；所以每個節點的迴圈是 O(n)，而不是 O(剩下的元素數)。這不影響總複雜度（因為葉子還要 O(n) 複製），但如果想讓每層只掃剩下的元素，swap 寫法正好做到這一點。

### 解法

```python
from itertools import permutations as it_perms
import random


def permute(nums: list[int]) -> list[list[int]]:
    res, path, used = [], [], [False] * len(nums)

    def dfs() -> None:
        if len(path) == len(nums):
            res.append(path[:])
            return
        for i, x in enumerate(nums):
            if used[i]:
                continue
            used[i] = True
            path.append(x)
            dfs()
            path.pop()
            used[i] = False

    dfs()
    return res


def permute_swap(nums: list[int]) -> list[list[int]]:
    nums = nums[:]                       # 不修改呼叫者的陣列
    res = []

    def dfs(d: int) -> None:
        if d == len(nums):
            res.append(nums[:])
            return
        for i in range(d, len(nums)):
            nums[d], nums[i] = nums[i], nums[d]
            dfs(d + 1)
            nums[d], nums[i] = nums[i], nums[d]   # 換回去，恢復進來時的狀態

    dfs(0)
    return res


assert permute([1, 2, 3]) == [[1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]]
assert sorted(permute([0, 1])) == [[0, 1], [1, 0]]
assert permute([7]) == [[7]]
assert len(permute(list(range(6)))) == 720
for _ in range(100):
    arr = random.sample(range(-10, 11), random.randint(1, 6))
    expect = sorted(list(p) for p in it_perms(arr))
    assert sorted(permute(arr)) == expect == sorted(permute_swap(arr))
print("all tests passed")
```

### 複雜度與邊界

時間 O(n · n!)：葉子 n! 個，每個複製 O(n)；內部節點總數 Σ_{d<n} n!/(n−d)! < e · n!，used 寫法每個節點掃 O(n)，所以內部節點的總工作也是 O(n · n!)。空間：遞迴深度 n，`path` 與 `used` 各 O(n)，額外空間 O(n)，輸出 O(n · n!)。邊界情況：n = 1 時只有一個排列；題目保證互不相同，若有重複值，兩種寫法都會產生重複答案（見 F1）；swap 寫法若直接修改輸入要先複製，否則呼叫者的陣列在過程中被打亂（雖然最後會恢復）。

### Follow-up

> [!question]- F1. 如果 nums 有重複元素，要回傳不重複的排列呢（47. Permutations II）？
> 先排序，再在 used 寫法中加一行：`if i > 0 and nums[i] == nums[i - 1] and not used[i - 1]: continue`。意思是相同的值必須「依索引順序」使用：前一個相同的值還沒用時，不能先用後一個，於是每組相同的值在任何排列中只會以一種相對順序出現，重複自然消失。更不容易寫錯的做法是用 `Counter`：每一層列舉「目前還有剩的不同值」，選了就把次數減一、回來加一。答案數是 n! / Π cᵥ!，時間 O(n · 答案數)。

> [!question]- F2. 如果只要「下一個排列」，或要依字典序一個一個產生呢（31. Next Permutation）？
> 不需要搜尋：從右往左找第一個 `a[i] < a[i + 1]` 的位置 i（找不到代表已是最後一個排列，整個反轉回最小）；再從右往左找第一個 `a[j] > a[i]`，交換 a[i]、a[j]，最後把 i + 1 之後的後綴反轉成遞增。每次 O(n)，而且攤銷下來每次只動 O(1) 個元素。重複呼叫 n! 次就能依字典序列出所有排列，記憶體只要 O(n)，也天然處理重複元素（相同值不會產生相同的下一個排列）。

> [!question]- F3. 如果只要字典序第 k 個排列呢（60. Permutation Sequence）？
> 也不需要搜尋：以第一個位置為例，每個開頭各對應 (n − 1)! 個排列，所以開頭是剩餘元素中第 ⌊(k − 1) / (n − 1)!⌋ 小的那個，接著把 k 換成 (k − 1) mod (n − 1)! + 1，對剩下的位置重複。這是階乘進位制（factorial number system），用串列刪除元素時間 O(n²)，用 Fenwick tree 找第 k 個未用元素可降到 O(n log n)。詳見第 28 章難題 3。面試時說出「每個開頭對應一整塊 (n − 1)! 個排列」就是關鍵。

> [!question]- F4. 如果排列要滿足額外限制，例如位置 i（1-indexed）上的數必須整除 i 或被 i 整除（526. Beautiful Arrangement）呢？
> 把限制放進「做選擇」之前的檢查，違反就不往下走，這是最基本的可行性剪枝：`if not used[x] and (x % pos == 0 or pos % x == 0)`。一個小技巧是從最後一個位置往前填，因為大的位置能放的數更少，限制多的先填，錯誤更早暴露。若題目只問「有幾個」，狀態只取決於「哪些數用過了」（位置就是已用的數量），可以用 bitmask DP，O(n · 2ⁿ)，比 n! 小得多，見第 24 章核心題 3。

> [!question]- F5. 如果只要從 n 個中取 k 個的排列（長度為 k）呢？
> 把終止條件從 `len(path) == n` 改成 `len(path) == k`，其他不變。葉子數是 P(n, k) = n! / (n − k)!，內部節點數也是同階（Σ_{d<k} n!/(n−d)!，最後一層占大多數），所以時間 O(k · P(n, k))。若 k 很小而 n 很大，used 寫法每層掃 n 個元素的成本變得明顯，可以改用 swap 寫法，讓每一層只看剩下的元素；這時前 k 格就是答案，深度到 k 就停。

## 核心題 3｜39. Combination Sum｜Medium

### 題目

給一個**元素互不相同**的正整數陣列 `candidates` 和一個正整數 `target`，找出所有「和等於 target」的組合，每個候選數**可以被選任意多次**。兩個組合只要某個數被選的次數不同，就算不同的組合；`[2, 2, 3]` 與 `[3, 2, 2]` 是同一個組合，只能出現一次。回傳所有組合，順序不限。限制：`1 <= len(candidates) <= 30`，`2 <= candidates[i] <= 40`，`1 <= target <= 40`，保證答案個數少於 150。

- 範例 1：`candidates = [2, 3, 6, 7]`、`target = 7`，回傳 `[[2, 2, 3], [7]]`。
- 範例 2：`candidates = [2, 3, 5]`、`target = 8`，回傳 `[[2, 2, 2, 2], [2, 3, 3], [3, 5]]`。
- 範例 3（邊界）：`candidates = [2]`、`target = 1`，回傳 `[]`，最小的候選數就已經比 target 大。

### 思路

最直覺的遞迴是「每一步從所有候選數中任選一個加進去，直到和等於 target」。這會把同一個組合的所有順序都產生出來：`[2, 2, 3]`、`[2, 3, 2]`、`[3, 2, 2]` 各算一次，最後還得排序加 set 去重，而且順序數隨組合長度呈階乘成長。問題出在這棵決策樹是「排列樹」，但題目要的是「組合」。

解法和核心題 1 一樣：**強制 path 中的索引非遞減**，每個多重集合（multiset）就只會以唯一一種順序出現。和子集題唯一的差別在於可以重複使用，所以下一層從 `i` 開始而不是 `i + 1`：選了 `candidates[i]` 之後，下一個還可以再選它，但不能回頭選索引更小的。狀態是 `(start, remain)`，`remain == 0` 時記錄答案。

剪枝來自正整數：先把 candidates 排序，迴圈中一旦 `candidates[i] > remain`，這個數和它之後所有更大的數都不可能放進去，直接 `break`。沒有排序時只能 `continue`，會白白試完整個陣列；排序後，搜尋只會走進「至少還放得下一個數」的節點。因為每個數至少是 2，遞迴深度最多 target / min(candidates) ≤ 20。

```text
candidates = [2, 3, 6, 7]（已排序），target = 7；節點標示 path 與 remain
[] r=7
├─ 2 → [2] r=5
│   ├─ 2 → [2,2] r=3
│   │   ├─ 2 → [2,2,2] r=1
│   │   │   └─ 2 > 1 → break（3、6、7 都不必試）
│   │   └─ 3 → [2,2,3] r=0  ✓ 記錄
│   │       （6 > 3 → break）
│   ├─ 3 → [2,3] r=2
│   │   └─ 3 > 2 → break   ← 從 i=1 開始，不會回頭選 2，所以 [2,3,2] 不會出現
│   └─ 6 > 5 → break
├─ 3 → [3] r=4
│   ├─ 3 → [3,3] r=1 → 3 > 1 break
│   └─ 6 > 4 → break
├─ 6 → [6] r=1 → 6 > 1 break
└─ 7 → [7] r=0  ✓ 記錄
```

注意 `[2, 3]` 那個節點：它的下一層從索引 1（值 3）開始，只能選 3、6、7，所以 `[2, 3, 2]` 永遠不會被產生，這就是「非遞減索引」去重的效果。整棵樹只有 10 個節點（10 次 `dfs` 呼叫），break 剪掉了大部分的分支。

### 解法

```python
import random
from collections import Counter


def combination_sum(candidates: list[int], target: int) -> list[list[int]]:
    candidates = sorted(candidates)
    res, path = [], []

    def dfs(start: int, remain: int) -> None:
        if remain == 0:
            res.append(path[:])
            return
        for i in range(start, len(candidates)):
            c = candidates[i]
            if c > remain:
                break                      # 已排序：後面只會更大
            path.append(c)
            dfs(i, remain - c)             # i 而非 i + 1：同一個數可以再選
            path.pop()

    dfs(0, target)
    return res


def brute(candidates, target):
    """用 DP 列舉所有多重集合（以 Counter 表示），作為對照。"""
    ways = [set() for _ in range(target + 1)]
    ways[0].add(())
    for c in candidates:                   # 一次加入一種候選數，避免順序重複
        for t in range(c, target + 1):
            for combo in ways[t - c]:
                ways[t].add(tuple(sorted(combo + (c,))))
    return sorted(ways[target])


def normalize(res):
    return sorted(tuple(sorted(r)) for r in res)


assert normalize(combination_sum([2, 3, 6, 7], 7)) == [(2, 2, 3), (7,)]
assert normalize(combination_sum([2, 3, 5], 8)) == [(2, 2, 2, 2), (2, 3, 3), (3, 5)]
assert combination_sum([2], 1) == []
assert combination_sum([7, 3, 2, 6], 7) == [[2, 2, 3], [7]]     # 輸入未排序也可以
assert normalize(combination_sum([3], 9)) == [(3, 3, 3)]
for _ in range(200):
    cand = random.sample(range(2, 15), random.randint(1, 5))
    t = random.randint(1, 25)
    out = combination_sum(cand, t)
    assert all(sum(r) == t for r in out)
    assert len(set(map(tuple, map(sorted, out)))) == len(out)   # 沒有重複組合
    assert normalize(out) == brute(cand, t)
print("all tests passed")
```

### 複雜度與邊界

設 T = target、M = min(candidates)。遞迴深度最多 T / M，每層最多 n 個分支，所以最差的節點數上界是 O(n^(T/M))；這個上界很鬆，實際節點數接近「和 ≤ T 的非遞減序列個數」，再乘上葉子複製的 O(T / M)。比較有意義的說法是 output-sensitive：排序加 break 之後，每個走到的節點都至少放得下一個數，但不保證一定能湊到 target（例如 `[2, 2, 2]` 剩 1），所以無法嚴格以答案數界定。排序 O(n log n)。額外空間 O(T / M)。邊界情況：target 小於最小候選數時第一層就 break，回傳空串列；只有一個候選數時，答案存在若且唯若它整除 target；候選數保證 ≥ 2，若允許 1，深度會變成 T，但仍會結束。

### Follow-up

> [!question]- F1. 如果每個候選數只能用一次，而且 candidates 可能有重複值呢（40. Combination Sum II）？
> 兩個改動：下一層從 `i + 1` 開始（不能重複使用同一個索引），以及加上同層去重 `if i > start and candidates[i] == candidates[i - 1]: continue`，避免兩個相同的 1 各自產生一次 `[1, 7]`。排序後的 `break` 剪枝照樣適用。這等於核心題 1 F1（90 題）加上「和為 target」的限制，時間最差 O(n · 2ⁿ)，實際被 break 大幅剪掉。面試中這是 39 之後最常被接著問的題目，三個關鍵字是：排序、`i + 1`、`i > start`。

> [!question]- F2. 如果限定只能用 1 到 9、每個數最多一次、恰好選 k 個（216. Combination Sum III）呢？
> 候選集固定是 1..9，狀態多一個「還要選幾個」。除了 `c > remain` 的 break 之外，還能用上下界剪枝：剩下要選 r 個時，從 c 開始最小可能的和是 c + (c+1) + … + (c+r−1)，若它已經大於 remain 就 break；最大可能的和是 9 + 8 + … + (9−r+1)，若它小於 remain 就可以直接 return。搜尋空間最多 C(9, k) ≤ 126，任何寫法都很快，重點是展示你知道怎麼用「剩餘個數」做剪枝。

> [!question]- F3. 如果只要計算有幾種組合，而 target 到 10⁴ 呢？
> 答案數會爆炸，不能逐一列出。計數只取決於「用到第幾種候選數、剩下多少」，這是完全背包的組合計數，即 518. Coin Change II（第 23 章核心題 3）：`dp[t] += dp[t - c]`，外層迴圈跑候選數、內層跑金額，時間 O(n · T)。外層跑候選數的順序很重要，它對應本題「索引非遞減」的去重；如果把兩層迴圈對調，算出來的是**排列數**（377. Combination Sum IV，順序不同算不同），這是面試官常拿來確認你是否理解兩者差異的追問。

> [!question]- F4. 如果只要湊出 target 所需的最少個數呢？
> 這是 322. Coin Change（第 21 章核心題 2）。backtracking 加上界剪枝（從大的候選數開始試，`len(path) >= best` 就 return）可以做，但最差仍是指數級；而「湊出 t 所需最少個數」只取決於 t，`dp[t] = min(dp[t - c]) + 1`，O(n · T) 就解決，也可以看成在 0..T 上的 BFS。這個對比說明了一個重要判斷：題目要「所有組合本身」才用 backtracking，只要「一個最佳值」時先找 DP。

> [!question]- F5. 如果 candidates 可以包含 0 或負數呢？
> 解的個數可能變成無限：有 0 時 `[7]`、`[0, 7]`、`[0, 0, 7]` 都是解；有正有負時 `[3, -3]` 可以無限重複。所以題目必須額外限制組合長度上限 L（或每個數的使用次數）。此時 `c > remain` 的 break 不再成立，因為後面的負數可以把和拉回來，剪枝只能改用「剩下 r 個位置最多能把和改變多少」：remain 必須落在 [r · min, r · max] 之內才繼續。時間最差 O(n^L)。面試中先指出無限解的問題、要求釐清限制，比直接寫程式更重要。

## 核心題 4｜17. Letter Combinations of a Phone Number｜Medium

### 題目

傳統手機鍵盤上，數字 2 到 9 各對應幾個英文字母：2 → abc、3 → def、4 → ghi、5 → jkl、6 → mno、7 → pqrs、8 → tuv、9 → wxyz。給一個只包含 `'2'` 到 `'9'` 的字串 `digits`，回傳所有可能的字母組合（第 i 個字母來自第 i 個數字），順序不限。若 `digits` 是空字串，回傳空串列。限制：`0 <= len(digits) <= 4`。

- 範例 1：`digits = "23"`，回傳 `["ad", "ae", "af", "bd", "be", "bf", "cd", "ce", "cf"]`，3 × 3 = 9 個。
- 範例 2：`digits = "7"`，回傳 `["p", "q", "r", "s"]`。
- 範例 3（邊界）：`digits = ""`，回傳 `[]`（不是 `[""]`，這是題目的規定）。

### 思路

如果 `digits` 的長度固定是 2，兩層巢狀迴圈就解決了；困難在於長度是輸入決定的，迴圈層數不能寫死。答案就是各位數字對應字母集合的笛卡兒積，總數是 Π |letters(d)|，最多 4⁴ = 256 個。因為每個組合都要輸出，任何做法都至少要 O(L · 答案數)，所以這題沒有「暴力解太慢」的問題，考的是你能不能把「深度不固定的巢狀迴圈」寫成遞迴。

決策樹的第 i 層決定第 i 個字母，選擇集合就是 `letters[digits[i]]`。這是 19.3 節說的第三種結構：每層的選擇集合固定，不需要 `start` 也不需要 `used`，深度就是位置，走到深度 L 就記錄。用 list 當 path，到葉子再 `"".join`，避免每層都做字串拼接。

也可以用迭代的方式：從 `[""]` 開始，每處理一個數字，就把目前每個字串分別接上這個數字的每個字母，像 BFS 一層一層展開。兩者時間相同，迭代版不需要遞迴；而 Python 的 `itertools.product(*groups)` 本質上就是這個笛卡兒積。面試時通常期待你寫 backtracking，再提一句 product 或迭代版。

```text
digits = "23"，letters: 2 → abc，3 → def
深度 0                    ""
               /          |          \
深度 1        a           b           c        ← 第 1 位從 "abc" 選
            / | \       / | \       / | \
深度 2    ad ae af    bd be bf    cd ce cf     ← 第 2 位從 "def" 選

迭代版（逐位展開）：
開始       [""]
處理 '2'   ["a", "b", "c"]
處理 '3'   ["ad","ae","af","bd","be","bf","cd","ce","cf"]
```

兩種寫法產生的順序一樣（字典序），因為兩者都以第一位為最外層。遞迴版的 path 最長 L，深度 L；迭代版每一步保留整層的所有字串，記憶體與答案同階。若只是要逐一處理而不必全部存下，遞迴版可以改成 generator，記憶體只要 O(L)。

### 解法

```python
from itertools import product

KEYPAD = {"2": "abc", "3": "def", "4": "ghi", "5": "jkl",
          "6": "mno", "7": "pqrs", "8": "tuv", "9": "wxyz"}


def letter_combinations(digits: str) -> list[str]:
    if not digits:
        return []
    res, path = [], []

    def dfs(i: int) -> None:
        if i == len(digits):
            res.append("".join(path))
            return
        for ch in KEYPAD[digits[i]]:
            path.append(ch)
            dfs(i + 1)
            path.pop()

    dfs(0)
    return res


def letter_combinations_iter(digits: str) -> list[str]:
    if not digits:
        return []
    layer = [""]
    for d in digits:
        layer = [prefix + ch for prefix in layer for ch in KEYPAD[d]]
    return layer


assert letter_combinations("23") == ["ad", "ae", "af", "bd", "be", "bf", "cd", "ce", "cf"]
assert letter_combinations("7") == ["p", "q", "r", "s"]
assert letter_combinations("") == []
assert len(letter_combinations("7979")) == 256
assert len(letter_combinations("2345")) == 81
for digits in ["2", "79", "234", "9876", "2222"]:
    expect = ["".join(p) for p in product(*(KEYPAD[d] for d in digits))]
    assert letter_combinations(digits) == expect == letter_combinations_iter(digits)
print("all tests passed")
```

### 複雜度與邊界

時間 O(L · 4ᴸ)：最多 4ᴸ 個葉子，每個葉子 join 一次 O(L)；內部節點數是 1 + 4 + … + 4ᴸ⁻¹ < 4ᴸ / 3，每個 O(1)。更精確地說是 O(L · Π |letters(dᵢ)|)，只有 7 和 9 有 4 個字母，其餘是 3 個。空間：遞迴深度與 path 是 O(L)，不含輸出。邊界情況：空字串必須回傳 `[]` 而不是 `[""]`，所以要特判；若輸入可能出現 `'0'` 或 `'1'`（沒有對應字母），題目通常視為無效輸入，若要求「略過」或「視為空集合」，要先和面試官確認，後者會讓整個答案變成空串列，因為笛卡兒積中有一個空集合。

### Follow-up

> [!question]- F1. 如果只回傳字典裡存在的單字呢？
> 把字典建成 trie（第 13 章核心題 4），讓 DFS 同時走在決策樹與 trie 上：選了字母 ch 之後，如果目前 trie 節點沒有 ch 這個子節點，代表沒有任何單字以這個前綴開頭，整棵子樹剪掉；走到深度 L 時，只有 trie 節點標記為單字結尾才記錄。這讓搜尋只走在「是某個單字前綴」的路徑上，節點數不超過 trie 中長度 ≤ L 的節點數，與 4ᴸ 無關。若字典很大而 digits 很長（例如 10 位），這個剪枝是唯一可行的方式。

> [!question]- F2. 如果只要字典序第 k 個組合（0-indexed）呢？
> 不需要列舉。答案就是把 k 寫成混合進位制（mixed radix）：從最後一位往前，每位的基數是該數字的字母個數 bᵢ，第 i 位的字母是 `letters[i][k % bᵢ]`，然後 `k //= bᵢ`。時間 O(L)。這和核心題 2 F3 的「第 k 個排列」是同一個想法：每個前綴對應一整塊大小已知的子樹，用除法直接跳到正確的子樹。若 k ≥ Π bᵢ 則不存在，要回報錯誤。

> [!question]- F3. 如果 digits 長度到 20，只問有幾種組合，或只要逐一處理而不能全存呢？
> 計數就是 Π |letters(dᵢ)|，O(L)，最多 4²⁰ ≈ 10¹²，Python 整數不會溢位，其他語言要用 64 位元。若要逐一處理，把 dfs 改成 generator（`yield "".join(path)`），或直接用 `itertools.product`，它也是惰性產生的，記憶體只要 O(L)；迭代版每層保留整層字串，記憶體會是 O(L · 4ᴸ)，這時不能用。這個 follow-up 在測你是否知道「遞迴 DFS 的記憶體是深度，BFS 式展開的記憶體是寬度」。

> [!question]- F4. 反過來：給一份單字清單和一串數字，找出所有按出來剛好是這串數字的單字呢？
> 不要對數字做 backtracking 再查字典（那是 4ᴸ），而是反過來把每個單字轉成數字：建一個字母到數字的反查表，`"".join(rev[ch] for ch in word)`，和輸入比較，或預先建 `defaultdict(list)` 從數字字串對應到單字。前處理 O(總字元數)，之後每次查詢 O(L)。這是 T9 輸入法的做法；若要支援「只輸入前綴就提示」，把單字的數字序列插進 trie，每個節點存經過它的單字。

> [!question]- F5. 如果要把整串數字切成多個字典中的單字（例如 "4663" 可以是 "good" 或 "go" + "of"）呢？
> 這是 backtracking 加 word break（139. Word Break，第 21 章核心題 4）：先把字典的每個單字轉成數字序列，存成 `digit_seq → [words]`。DFS 的狀態是目前的起點 i，選擇是「從 i 開始的某個長度 ℓ，使 `digits[i:i+ℓ]` 在表中」，對每個符合的單字往下遞迴。為了避免在無解的後綴上重複搜尋，先用 DP 算出 `ok[i]`（後綴 `digits[i:]` 能否被切完），DFS 只走 `ok[i + ℓ]` 為真的分支；這樣每條路徑都通往至少一個答案，時間與輸出大小同階。

## 核心題 5｜79. Word Search｜Medium

### 題目

給一個 m × n 的字元網格 `board` 和一個字串 `word`，判斷 word 是否能由網格中**相鄰**格子的字母依序連成；相鄰指上下左右四個方向，**同一個格子在一條路徑中最多使用一次**。回傳 True 或 False。限制：`1 <= m, n <= 6`，`1 <= len(word) <= 15`，board 和 word 只含大小寫英文字母。

```text
board =
  A B C E
  S F C S
  A D E E
```

- 範例 1：`word = "ABCCED"`，回傳 `True`（A(0,0) → B(0,1) → C(0,2) → C(1,2) → E(2,2) → D(2,1)）。
- 範例 2：`word = "SEE"`，回傳 `True`（S(1,3) → E(2,3) → E(2,2)）。
- 範例 3：`word = "ABCB"`，回傳 `False`：A → B → C 之後唯一相鄰的 B 就是剛剛用過的 (0,1)，不能重複使用。
- 範例 4（邊界）：`board = [["a"]]`、`word = "a"`，回傳 `True`；`word = "aa"` 則回傳 `False`。

### 思路

暴力做法是列舉網格中所有不重複格子的路徑，檢查是否有一條拼出 word；路徑數量是指數級，而且大部分路徑在第一、二個字母就已經不符合了。Backtracking 的做法是把 word 當作決策樹的深度：從每個等於 `word[0]` 的格子出發，第 k 層決定 `word[k]` 要用哪個相鄰格子，**只有字母相符的鄰居才往下走**。這個逐字比對的剪枝讓搜尋在第一個不符的字母就停下。

和第 15 章的 BFS／DFS 最大的不同是 visited 的語意。在圖的連通性問題中，visited 是全域的：一個格子被任何路徑走過就不必再走。這題的 visited 只屬於**目前這一條路徑**：格子在這條路徑上用過就不能再用，但這條路失敗回溯之後，另一條路徑仍然可以經過它。所以必須在離開格子時把標記撤銷。最省空間的做法是直接把 `board[r][c]` 暫時改成一個不會出現在 word 裡的字元（例如 `'#'`），回來時改回原字元；這同時完成了「已用過」和「字母不符」兩種檢查。

複雜度：起點有 m · n 個，第一步最多 4 個方向，之後每一步最多 3 個（不能走回上一格），所以最差 O(m · n · 4 · 3^(L−1))。實務上可以再加兩個便宜的預檢：若 word 中某個字母的數量多於網格中的數量，直接回傳 False；若 word 的第一個字母在網格中比最後一個字母更常見，就把 word 反轉再搜尋（路徑反過來一樣合法），讓起點變少。

```text
word = "ABCB"，從 (0,0) 出發；#（已用）表示目前路徑上的格子
k=0 A(0,0) ✓       k=1 B(0,1) ✓       k=2 C(0,2) ✓
  # B C E            # # C E            # # # E
  S F C S            S F C S            S F C S
  A D E E            A D E E            A D E E
k=3 要找 B：C(0,2) 的鄰居是 (0,1)=#、(0,3)=E、(1,2)=C → 沒有 B
回溯：(0,2) 改回 C；B(0,1) 的其他鄰居 (1,1)=F 不是 C → 回溯；A(0,0) 的鄰居 (1,0)=S 不是 B
其他起點：網格中沒有其他 A 能接 B → 回傳 False

word = "SEE"，從 (1,3) 出發
k=0 S(1,3) → k=1 鄰居 (0,3)=E ✓ → k=2 (0,3) 的鄰居 (0,2)=C、(1,3)=# → 失敗，回溯
          → k=1 鄰居 (2,3)=E ✓ → k=2 (2,3) 的鄰居 (2,2)=E ✓ → k=3 == len，回傳 True
```

「ABCB」的失敗正是因為 (0,1) 在路徑上被標成 `#`；若用全域 visited 而不撤銷，「SEE」從 (1,3) 先走 (0,3) 失敗後，(0,3) 會一直被標記，雖然這個例子不受影響，但在其他盤面上就會漏掉必須經過「先前失敗路徑上的格子」的解。

### 解法

```python
import random
from collections import Counter


def exist(board: list[list[str]], word: str) -> bool:
    m, n = len(board), len(board[0])
    have = Counter(ch for row in board for ch in row)
    if any(have[ch] < cnt for ch, cnt in Counter(word).items()):
        return False                                  # 字母數量不夠，不可能拼出
    if have[word[0]] > have[word[-1]]:
        word = word[::-1]                             # 從較稀有的一端開始，起點較少

    def dfs(r: int, c: int, k: int) -> bool:
        if board[r][c] != word[k]:
            return False
        if k == len(word) - 1:
            return True
        saved, board[r][c] = board[r][c], "#"         # 標記：只屬於目前路徑
        found = False
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < m and 0 <= nc < n and dfs(nr, nc, k + 1):
                found = True
                break
        board[r][c] = saved                           # 撤銷：找到與否都要還原
        return found

    return any(dfs(r, c, 0) for r in range(m) for c in range(n))


def brute(board, word):
    """列舉所有不重複格子的路徑（只適合很小的網格）。"""
    m, n = len(board), len(board[0])

    def go(r, c, k, seen):
        if board[r][c] != word[k]:
            return False
        if k == len(word) - 1:
            return True
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < m and 0 <= nc < n and (nr, nc) not in seen:
                if go(nr, nc, k + 1, seen | {(nr, nc)}):
                    return True
        return False

    return any(go(r, c, 0, {(r, c)}) for r in range(m) for c in range(n))


B = [list("ABCE"), list("SFCS"), list("ADEE")]
assert exist(B, "ABCCED") is True
assert exist(B, "SEE") is True
assert exist(B, "ABCB") is False
assert exist([["a"]], "a") is True
assert exist([["a"]], "aa") is False
assert B == [list("ABCE"), list("SFCS"), list("ADEE")]   # 網格已完全還原
for _ in range(500):
    m, n = random.randint(1, 4), random.randint(1, 4)
    g = [[random.choice("ab") for _ in range(n)] for _ in range(m)]
    w = "".join(random.choice("ab") for _ in range(random.randint(1, 7)))
    assert exist([row[:] for row in g], w) == brute(g, w)
print("all tests passed")
```

### 複雜度與邊界

時間最差 O(m · n · 3^L)：每個起點最多展開 4 · 3^(L−1) 條路徑，每步 O(1)；兩個預檢各 O(m · n + L)。最差情況出現在網格全是同一個字母、word 是「同一字母重複、最後一個字母不同」，例如全 a 的網格找 `"aaaaab"`，此時字母數量預檢會直接擋下（沒有 b）；但若網格中恰好有一個 b 藏在角落，搜尋仍可能很慢，反轉 word 就讓起點只剩那一個 b。空間：遞迴深度 L，原地標記不需額外的 visited，O(L)。邊界情況：word 比格子數還長時字母數量檢查會回傳 False；標記字元 `'#'` 必須不會出現在 word 中（題目保證只有英文字母）；找到答案後仍要先還原格子再回傳，否則呼叫端的 board 被改壞，這在面試中常被扣分。

### Follow-up

> [!question]- F1. 如果要同時找一整份單字清單中，哪些單字出現在網格裡呢（212. Word Search II）？
> 對每個單字各跑一次本題，會在網格上重複走相同的前綴，總成本是 單字數 × m · n · 3^L。正解是把所有單字建成 trie，讓一次 DFS 同時走在網格與 trie 上：目前的 trie 節點沒有下一個字母就剪枝，走到單字結尾就記錄並把該單字從 trie 中移除（避免重複回報，也讓之後的搜尋更快剪枝）。詳細推導見第 13 章難題 1。時間最差 O(m · n · 3^L)，與單字數量無關，只多了建 trie 的 O(總字元數)。

> [!question]- F2. 如果同一個格子可以重複使用（只是不能原地停留）呢？
> 那就不需要 visited，路徑能否拼出 word 的後綴只取決於「目前在哪一格、已經比對到第幾個字母」，狀態是 `(r, c, k)`，總共 m · n · L 個，可以用 DP 或 memoization：`ok[r][c][k] = board[r][c] == word[k] and any(ok[鄰居][k + 1])`。時間 O(m · n · L · 4)，從指數變成多項式。這個對比點出原題的本質：正是「不能重複使用」讓狀態必須包含整條路徑的 visited 集合，才無法 memoize，只能 backtracking。

> [!question]- F3. 為什麼原題不能對 (r, c, k) 做 memoization？
> 因為從 (r, c) 比對 `word[k:]` 是否成功，還取決於「哪些格子已經被目前的路徑用掉」。同一個 (r, c, k) 從不同路徑抵達時，被占用的格子不同，答案也可能不同：例如一條路徑先經過某個必經的格子 X，再抵達 (r, c)，就無法再用 X；另一條路徑沒經過 X，就能成功。若把「失敗」記成 memo，會讓第二條路徑誤判。要正確 memoize，key 必須包含 visited 集合，狀態數變成指數級，沒有意義。面試官問這題是在確認你理解 DP 需要「子問題只由狀態決定」。

> [!question]- F4. 如果要回傳拼出 word 的所有路徑（或路徑數）呢？
> 不能在找到第一條時 `break` 或提前 return，必須試完所有方向；每次 k 到達最後一個字母時，把目前的座標路徑複製一份存起來（或計數加一）。撤銷照常進行。時間仍是 O(m · n · 3^L)，但不再有提前結束的好處，最差情況會走滿整棵搜尋樹。若只要路徑數且允許重複使用格子，就回到 F2 的 DP，把布林改成計數即可，O(m · n · L)。

> [!question]- F5. 如果允許八個方向移動（含斜向）呢？
> 鄰居列表換成八個方向即可，其餘不變。分支因子從 3 變成 7，最差時間 O(m · n · 8 · 7^(L−1))，所以預檢與剪枝更重要：字母數量檢查、從較稀有的一端開始，以及「網格中與 word 相鄰字母對的出現情況」等更細的預檢。若 L 很長、網格很大，可以先找出 word 中最稀有的字母，從它在網格中的每個位置往兩個方向同時搜尋，讓起點與每條路徑的長度都減少。

## 難題 1｜51. N-Queens｜Hard

### 題目

在 n × n 的西洋棋盤上放 n 個皇后，使得任兩個皇后都不能互相攻擊：皇后可以攻擊同一列、同一行、以及兩條對角線上的任何格子。回傳所有不同的放法，每個放法以 n 個字串表示，第 r 個字串的第 c 個字元是 `'Q'`（有皇后）或 `'.'`（空格）。順序不限。限制：`1 <= n <= 9`。

- 範例 1：`n = 4`，回傳兩個解：`[".Q..", "...Q", "Q...", "..Q."]` 與 `["..Q.", "Q...", "...Q", ".Q.."]`。
- 範例 2（邊界）：`n = 1`，回傳 `[["Q"]]`。
- 範例 3（邊界）：`n = 2` 或 `n = 3`，回傳 `[]`，沒有任何合法放法。
- 參考：n = 5、6、7、8 的解數分別是 10、4、40、92。

### 提示

> [!tip]- 提示 1
> 每一列恰好有一個皇后（n 個皇后、n 列、同列不能有兩個）。所以不必在 n² 個格子中選 n 個，只要決定「第 r 列的皇后放在第幾行」。

> [!tip]- 提示 2
> 一列一列往下放，第 r 層的選擇是行號 c。放之前要能 O(1) 判斷 (r, c) 會不會被前面的皇后攻擊：同一行、同一條「╲」對角線、同一條「╱」對角線。每條對角線能不能用一個數字代表？

> [!tip]- 提示 3
> 同一條「╲」對角線上 `r − c` 相同，同一條「╱」對角線上 `r + c` 相同。用三個集合（或三個 bitmask）記錄已占用的行、`r − c`、`r + c`；放下時加入，回溯時移除。

### 詳解

**為什麼直覺做法不夠**。最直接的暴力是從 n² 個格子中選 n 個放皇后，C(n², n) 種，n = 8 時約 44 億；每個再花 O(n²) 檢查是否互相攻擊。第一個觀察「每列恰好一個」把搜尋空間縮成 nⁿ（每列選一個行號），n = 8 時 1677 萬；第二個觀察「每行也恰好一個」再把它縮成 n!（行號是 0..n−1 的一個排列），n = 8 時 40320。但如果等到排列完成才檢查對角線，仍然會走完所有 n! 個葉子。真正的突破是把對角線檢查**提前到放下每個皇后的那一刻**，衝突就立刻剪掉整棵子樹。

**用一個數字代表一條對角線**。從左上往右下的「╲」對角線，每往下一列、行號也加一，所以 `r − c` 在整條線上不變；從右上往左下的「╱」對角線，`r + c` 不變。n × n 棋盤共有 2n − 1 條「╲」（`r − c` 從 −(n−1) 到 n−1）和 2n − 1 條「╱」（`r + c` 從 0 到 2n−2）。維護三個集合 `cols`、`diag1`（存 `r − c`）、`diag2`（存 `r + c`），檢查一個格子是否安全只要三次 O(1) 查詢，不必掃描已放的皇后。這和第 4 章用 hash 記錄「已出現的鍵」是同一個想法。

**正確性**。演算法按列遞增放皇后，第 r 層列舉所有安全的行號。任何合法解在每一列恰有一個皇后，而且它的前 r 個皇后對任何 r 都是互不攻擊的，所以這個解的每個前綴都會通過檢查、被搜尋走到，最後在第 n 層被記錄，不會漏掉；反過來，被記錄的每個放法每一步都通過了三種檢查，所以一定合法。因為每列只放一個、按列的順序固定，同一個解只會以一條路徑出現，不會重複。

**剪枝的效果**。n = 8 時，這個搜尋（包含根節點）只走過 2057 個節點，而 8! = 40320、8⁸ ≈ 1677 萬。只要解數本身要全部輸出，複雜度的上界就仍是 O(n!) 量級，但實際節點數遠小於此。若只要計數，可以把三個集合換成三個整數 bitmask，用位元運算一次算出這一列所有可放的位置，速度再快一個常數級（F1）。

```text
n = 4，一列一列放；x 表示被攻擊的格子，Q 是皇后
第 0 列放 c=0           第 1 列：c=0 同行、c=1 同 ╲ → 試 c=2
  Q . . .                 Q . . .
  x x . .                 . . Q .
  x . x .                 x x x x   ← 第 2 列全被攻擊：c=0 同行、c=1 同╱(r+c=3)、
  x . . x                              c=2 同行、c=3 同╲(r−c=−1) → 回溯
第 1 列改試 c=3           第 2 列只能放 c=1       第 3 列：全被攻擊 → 回溯到第 0 列
  Q . . .                 Q . . .
  . . . Q                 . . . Q
  x . x x                 . Q . .
  x x . x                 x x x x
第 0 列改放 c=1 → 第 1 列 c=3 → 第 2 列 c=0 → 第 3 列 c=2 ✓ 記錄 [1,3,0,2]
  . Q . .
  . . . Q
  Q . . .
  . . Q .
集合狀態（找到解時）：cols={1,3,0,2}，r−c={−1,−2,2,1}，r+c={1,4,2,5}，各 4 個互不相同
```

第 0 列放在 c = 0 時，整棵子樹在第 2 或第 3 列就全部被剪掉，沒有任何解；這正是剪枝省下的工作。第二個解 `[2, 0, 3, 1]` 是第一個解的左右鏡像，F3 會利用這種對稱性把搜尋量減半。

### 解法

```python
def solve_n_queens(n: int) -> list[list[str]]:
    res, cols_of_row = [], []
    cols, diag1, diag2 = set(), set(), set()

    def dfs(r: int) -> None:
        if r == n:
            res.append(["." * c + "Q" + "." * (n - c - 1) for c in cols_of_row])
            return
        for c in range(n):
            if c in cols or (r - c) in diag1 or (r + c) in diag2:
                continue
            cols.add(c); diag1.add(r - c); diag2.add(r + c)
            cols_of_row.append(c)
            dfs(r + 1)
            cols_of_row.pop()
            cols.remove(c); diag1.remove(r - c); diag2.remove(r + c)

    dfs(0)
    return res


def total_n_queens(n: int) -> int:
    """只計數：用 bitmask 一次算出這一列所有可放的位置。"""
    full = (1 << n) - 1

    def dfs(cols: int, d1: int, d2: int) -> int:
        if cols == full:
            return 1
        count = 0
        free = full & ~(cols | d1 | d2)          # 這一列還能放的行
        while free:
            bit = free & -free                   # 取最低位的 1
            free ^= bit
            # 往下一列時，╲ 對角線的攻擊位置右移一格、╱ 左移一格
            count += dfs(cols | bit, ((d1 | bit) << 1) & full, (d2 | bit) >> 1)
        return count

    return dfs(0, 0, 0)


def is_valid(board):
    n = len(board)
    qs = [(r, row.index("Q")) for r, row in enumerate(board)]
    return (all(row.count("Q") == 1 for row in board)
            and len({c for _, c in qs}) == n
            and len({r - c for r, c in qs}) == n
            and len({r + c for r, c in qs}) == n)


assert sorted(solve_n_queens(4)) == sorted(
    [[".Q..", "...Q", "Q...", "..Q."], ["..Q.", "Q...", "...Q", ".Q.."]])
assert solve_n_queens(1) == [["Q"]]
assert solve_n_queens(2) == [] and solve_n_queens(3) == []
expected = [1, 0, 0, 2, 10, 4, 40, 92, 352]
assert [len(solve_n_queens(n)) for n in range(1, 10)] == expected
assert [total_n_queens(n) for n in range(1, 10)] == expected
assert all(is_valid(b) for b in solve_n_queens(8))
assert len({tuple(b) for b in solve_n_queens(8)}) == 92        # 沒有重複的解
print("all tests passed")
```

### 複雜度與邊界

時間：最差上界 O(n!) 個葉子量級的節點，每個節點 O(n) 掃描行號，加上每個解 O(n²) 建立字串輸出，所以是 O(n · n! + S · n²)，S 是解數；實際節點數遠小於 n!（n = 8 時 2057 個）。空間：遞迴深度 n，三個集合各 O(n)，額外空間 O(n)，不含輸出。邊界情況：n = 1 只有一個解；n = 2、3 無解，搜尋會在幾步內把所有分支剪光並回傳空串列；`r − c` 可能是負數，用 set 沒問題，若改用陣列要加上偏移 n − 1；bitmask 版本中 `<< 1` 之後要 `& full`，否則超出棋盤的位元會累積，雖然不影響正確性（`free` 會再 `& full`），但整數會越來越大。

### Follow-up

> [!question]- F1. 如果只要解的個數呢（52. N-Queens II）？
> 不需要建立棋盤字串，直接計數；並用 bitmask 取代集合：`cols`、`d1`、`d2` 三個整數分別表示「這一列中被同行、╲、╱ 攻擊的行」，`free = full & ~(cols | d1 | d2)` 一次算出所有可放位置，`free & -free` 取出最低位逐一嘗試。往下一列時 ╲ 的攻擊範圍整體右移一格（`<< 1`）、╱ 左移一格（`>> 1`），所以對角線狀態不需要用 r 計算。時間仍是 O(n!) 量級，但常數小得多，n = 12 在 Python 中也只要零點幾秒。

> [!question]- F2. 如果 n = 10⁶，只要任意一個解呢？
> 搜尋不可行，但 n ≥ 4 時有明確的構造：把 1..n 的偶數依序排在前面、奇數排在後面，作為第 1..n 列皇后的行號；若 n mod 6 == 2，奇數部分改成 `3, 1, 7, 9, …, 5`（交換 1 和 3、把 5 移到最後）；若 n mod 6 == 3，偶數部分把 2 移到最後、奇數部分把 1、3 移到最後。時間 O(n)。面試中通常不要求背出這個構造，能說出「大的 n 有構造解，搜尋只適合小 n」，或改用 min-conflicts 局部搜尋（隨機起點、每次把衝突最多的皇后移到衝突最少的位置，實務上對百萬級的 n 也很快收斂）就是好的回答。
> ```python
> def one_queens(n):
>     evens, odds = list(range(2, n + 1, 2)), list(range(1, n + 1, 2))
>     if n % 6 == 2:
>         odds = [3, 1] + odds[3:] + [5]
>     elif n % 6 == 3:
>         evens, odds = evens[1:] + [2], odds[2:] + [1, 3]
>     return [c - 1 for c in evens + odds]   # 第 r 列的皇后在第 cols[r] 行
> ```

> [!question]- F3. 能不能利用對稱性加速？
> 棋盤的左右鏡像會把解對應到解：第 0 列皇后在 c 的解，鏡像後在 n − 1 − c。所以第 0 列只需要試左半邊 `c < n // 2`，把找到的解數乘以 2；n 為奇數時，第 0 列放在正中間的那些解要另外算、而且不能乘 2（它們的鏡像仍是「中間開頭」的解）。這讓計數版的搜尋量大約減半。若要列出所有解，對每個找到的解再輸出它的鏡像即可。更進一步可以用旋轉與鏡像組成的 8 種對稱只找「本質不同」的解（n = 8 時 92 個解中有 12 個本質不同），但實作複雜，面試中說明想法就夠了。

> [!question]- F4. 如果棋盤上有些格子被封住不能放、或已經預先放了幾個皇后呢？
> 預先放好的皇后在開始搜尋前就加入三個集合，並把它們所在的列標記為「已完成」，DFS 遇到這些列直接跳到下一列；若預放的皇后彼此衝突，直接回傳空結果。被封住的格子在列舉 c 時跳過，bitmask 版本則對每一列準備一個 `blocked[r]`，`free = full & ~(cols | d1 | d2 | blocked[r])`。剪枝機制完全不變。額外的小優化是改成「先處理可放位置最少的那一列」（類似難題 2 的 MRV），限制越多的盤面效果越明顯。

> [!question]- F5. 如果要回傳字典序最小的一個解呢？
> 按列遞增、每列行號由小到大嘗試的 DFS，第一個找到的解就是字典序最小的（以「每列皇后的行號序列」比較），因為 DFS 的走訪順序本身就是字典序：在第一個不同的列上，它先試較小的行號。所以把列舉改成判定型模板（找到就一路 return True），不必列出所有解。對 n ≤ 30 左右通常很快，但最差情況的回溯仍可能很深；若 n 很大，就改用 F2 的構造，但構造出來的不保證是字典序最小。

### 心得

關鍵突破是兩個觀察：「每列恰好一個皇后」把問題變成按列填行號的排列搜尋，而「對角線可用 `r − c`、`r + c` 編號」讓衝突檢查變成 O(1)，於是可以在放下每個皇后時立刻剪枝。它是核心題 2（排列）加上可行性剪枝的典型：`cols` 就是排列模板中的 `used`，兩個對角線集合是額外的限制。面試時先說 C(n², n) → nⁿ → n! 的縮減過程，再說明對角線編號，寫完集合版後主動提 bitmask 版與對稱性，通常就涵蓋了面試官所有的追問。

## 難題 2｜37. Sudoku Solver｜Hard

### 題目

給一個 9 × 9 的數獨盤面 `board`，已填的格子是 `'1'` 到 `'9'`，空格是 `'.'`。請**原地修改** board，把所有空格填上數字，使得每一列、每一行、每一個 3 × 3 的宮（box）中，1 到 9 各恰好出現一次。題目保證輸入的盤面有且只有一個解。

```text
範例 1（輸入，. 為空格）           解
5 3 . | . 7 . | . . .             5 3 4 | 6 7 8 | 9 1 2
6 . . | 1 9 5 | . . .             6 7 2 | 1 9 5 | 3 4 8
. 9 8 | . . . | . 6 .             1 9 8 | 3 4 2 | 5 6 7
------+-------+------             ------+-------+------
8 . . | . 6 . | . . 3             8 5 9 | 7 6 1 | 4 2 3
4 . . | 8 . 3 | . . 1             4 2 6 | 8 5 3 | 7 9 1
7 . . | . 2 . | . . 6             7 1 3 | 9 2 4 | 8 5 6
------+-------+------             ------+-------+------
. 6 . | . . . | 2 8 .             9 6 1 | 5 3 7 | 2 8 4
. . . | 4 1 9 | . . 5             2 8 7 | 4 1 9 | 6 3 5
. . . | . 8 . | . 7 9             3 4 5 | 2 8 6 | 1 7 9
```

- 範例 2（邊界）：把上面的解任意挖掉一格，solver 只需要填回那一格；盤面已經填滿時，什麼都不用做。
- 範例 3（困難盤面）：只有 21 個提示數、需要大量回溯的盤面（例如解法中的 `HARD`），好的剪枝要能在一秒內解完。

### 提示

> [!tip]- 提示 1
> 一格一格填，每格試 1 到 9，違反列／行／宮的限制就換下一個數字，全部失敗就回溯。先讓「檢查能不能填」變成 O(1)。

> [!tip]- 提示 2
> 為每一列、每一行、每一宮各維護一個 9 位元的 bitmask，記錄已用過的數字。某格的候選數字就是 `~(row | col | box)` 的那幾個 bit。

> [!tip]- 提示 3
> 不要按固定順序填格子。每次挑「候選數最少」的空格先填（MRV）：候選數為 0 立刻回溯，為 1 等於沒有分岔。這個順序讓困難盤面的搜尋量少好幾個數量級。

### 詳解

**為什麼直覺做法不夠**。最天真的暴力是對每個空格試 9 個數字，等全部填完才檢查，9^(空格數)，50 個空格就是 10⁴⁷。把檢查提前到「填每一格的當下」之後，就是標準的 backtracking，對報紙上的簡單盤面已經很快；但它有兩個浪費。第一，檢查一個數字能不能放，若要掃描整列、整行、整宮，是 O(27)；第二，**按固定順序（左到右、上到下）填格子**，會在一個其實只剩一種可能的格子之前，先在另一個有很多選擇的格子上反覆分岔，讓錯誤要很久之後才暴露。

**突破點一：bitmask 讓檢查 O(1)**。`rows[r]`、`cols[c]`、`boxes[b]` 各是一個 9 位元整數，第 d − 1 個 bit 為 1 代表數字 d 已經用過；宮的編號是 `b = (r // 3) * 3 + c // 3`。空格 (r, c) 的候選集合就是 `FULL & ~(rows[r] | cols[c] | boxes[b])`，候選個數是它的 popcount（`int.bit_count()`），逐一取出候選用 `mask & -mask`。填數字是三個 `|=`，撤銷是三個 `^=`，都是 O(1)。

**突破點二：MRV（最少剩餘值）選格子**。每次遞迴時掃描所有空格，挑候選數最少的那一格來分岔。候選數為 0 代表目前的部分解已經無解，立刻回溯，這比固定順序早很多步發現矛盾；候選數為 1 則是「被迫填入」，不會產生分岔，相當於自動做了人類解數獨時的「唯一候選」推理。掃描空格要 O(空格數)，看起來讓每個節點變貴，但它讓節點總數大幅減少，總體快很多。這是一般限制滿足問題（constraint satisfaction problem）的標準啟發法，「先處理最難滿足的變數」。

**正確性**。每一步都只填入不違反三種限制的數字，所以填滿時一定是合法解；演算法對每個空格列舉了所有候選，任何合法解都在搜尋樹中，而題目保證有解，所以一定會找到。選格子的順序（MRV）不影響正確性，因為不論先填哪一格，最後每一格都要填，而對選定的格子我們試了它所有可能的值。

```text
範例 1 開始時，計算 (4, 4)（第 5 列第 5 行，正中央）的候選：
rows[4]  已用 {4, 8, 3, 1}       → 位元 9..1: 0 1 0 0 0 1 1 0 1
cols[4]  已用 {7, 9, 6, 2, 1, 8} → 位元 9..1: 1 1 1 1 0 0 0 1 1
boxes[4] 已用 {6, 8, 3, 2}       → 位元 9..1: 0 1 0 1 0 0 1 1 0
OR                                 位元 9..1: 1 1 1 1 0 1 1 1 1
候選 = FULL & ~OR                  位元 9..1: 0 0 0 0 1 0 0 0 0  → 只有 5

MRV：第一輪掃描所有空格，發現 (4, 4) 只剩 1 個候選 → 直接填 5，不分岔
填入後 rows[4]、cols[4]、boxes[4] 都多了 5，其他格的候選跟著減少，
新的唯一候選格又出現……範例 1 整個過程都不需要真正的分岔。
```

範例 1 是簡單盤面，MRV 讓它每一步都恰好只有一個候選，搜尋樹退化成一條直線。困難盤面則會在某些時候出現「最少的候選也有 2 個」的格子，這時才真正分岔；MRV 保證分岔時分支數最少，錯誤的分支也會很快因為某格候選變成 0 而被剪掉。

### 解法

```python
def solve_sudoku(board: list[list[str]]) -> None:
    FULL = 0x1FF
    rows, cols, boxes = [0] * 9, [0] * 9, [0] * 9
    empty = []
    for r in range(9):
        for c in range(9):
            if board[r][c] == ".":
                empty.append((r, c))
            else:
                bit = 1 << (int(board[r][c]) - 1)
                rows[r] |= bit
                cols[c] |= bit
                boxes[r // 3 * 3 + c // 3] |= bit

    def dfs() -> bool:
        if not empty:
            return True
        best, best_mask, best_cnt = -1, 0, 10
        for idx, (r, c) in enumerate(empty):          # MRV：找候選最少的空格
            mask = FULL & ~(rows[r] | cols[c] | boxes[r // 3 * 3 + c // 3])
            cnt = mask.bit_count()
            if cnt < best_cnt:
                best, best_mask, best_cnt = idx, mask, cnt
                if cnt <= 1:
                    break
        if best_cnt == 0:
            return False                              # 某格無數字可填：立刻回溯
        empty[best], empty[-1] = empty[-1], empty[best]
        r, c = empty.pop()
        b = r // 3 * 3 + c // 3
        mask = best_mask
        while mask:
            bit = mask & -mask
            mask ^= bit
            rows[r] |= bit; cols[c] |= bit; boxes[b] |= bit
            board[r][c] = str(bit.bit_length())
            if dfs():
                return True
            rows[r] ^= bit; cols[c] ^= bit; boxes[b] ^= bit
        board[r][c] = "."
        empty.append((r, c))                          # 撤銷：把空格放回原位置
        empty[best], empty[-1] = empty[-1], empty[best]
        return False

    dfs()


def check(board, original):
    groups = [[board[r][c] for c in range(9)] for r in range(9)]
    groups += [[board[r][c] for r in range(9)] for c in range(9)]
    groups += [[board[r][c] for r in range(br, br + 3) for c in range(bc, bc + 3)]
               for br in (0, 3, 6) for bc in (0, 3, 6)]
    keeps = all(original[r][c] in (".", board[r][c]) for r in range(9) for c in range(9))
    return keeps and all(sorted(g) == list("123456789") for g in groups)


EASY = ["53..7....", "6..195...", ".98....6.", "8...6...3", "4..8.3..1",
        "7...2...6", ".6....28.", "...419..5", "....8..79"]
SOLVED = ["534678912", "672195348", "198342567", "859761423", "426853791",
          "713924856", "961537284", "287419635", "345286179"]
HARD = ["8........", "..36.....", ".7..9.2..", ".5...7...", "....457..",
        "...1...3.", "..1....68", "..85...1.", ".9....4.."]

b = [list(row) for row in EASY]
solve_sudoku(b)
assert ["".join(row) for row in b] == SOLVED

one_blank = [list(row) for row in SOLVED]
one_blank[8][8] = "."
solve_sudoku(one_blank)
assert one_blank[8][8] == "9"

full = [list(row) for row in SOLVED]
solve_sudoku(full)
assert ["".join(row) for row in full] == SOLVED

h = [list(row) for row in HARD]
solve_sudoku(h)
assert check(h, HARD)
assert "".join(h[0]) == "812753649"
print("all tests passed")
```

### 複雜度與邊界

最差時間是指數級，上界 O(9^E)，E 是空格數（≤ 81）；每個節點的 MRV 掃描 O(E)。由於 9 × 9 的盤面大小固定，嚴格來說是 O(1)，但這種說法沒有資訊量，面試中應該說「指數級的搜尋，靠 bitmask 讓每步 O(1)、靠 MRV 讓分岔數最少」。空間：遞迴深度最多 E ≤ 81，三組 bitmask 和空格列表都是 O(81)。邊界情況：盤面已滿時 `empty` 為空，直接回傳 True；失敗回溯時必須把 `board[r][c]` 改回 `'.'`，否則上層換另一條路時，這格會殘留錯誤的數字；空格列表用「和最後一個交換再 pop」移除，撤銷時要完全反向操作，才能讓上層記住的索引 `best` 仍然正確。

### Follow-up

> [!question]- F1. 如何判斷一個盤面是否有唯一解？
> 把 solver 改成計數模式：找到一個解時不 return True，而是把計數加一並繼續搜尋，計數到 2 就立刻停止（不需要知道全部有幾個解）。回傳 0 代表無解、1 代表唯一、2 代表不唯一。因為只要找到第二個解就停，額外成本最多是再搜尋一棵到第二個解為止的子樹。這是出題程式必備的檢查，也是 F2 的基礎。注意計數模式下回溯時一定要撤銷，因為搜尋不會提前結束。

> [!question]- F2. 如何產生一個有唯一解的數獨題目？
> 兩步。第一步產生一個完整的解：對空盤面跑 solver，但候選數字的嘗試順序隨機打亂，就能得到隨機的終盤。第二步挖洞：隨機排列 81 個格子，依序嘗試挖掉每一格，挖掉後用 F1 檢查是否仍有唯一解，不唯一就把它填回去。整個過程呼叫 solver 約 81 次，每次在接近唯一解的盤面上都很快。若要控制難度，可以記錄 solver 的分岔次數或需要用到的推理技巧，作為難度分數。

> [!question]- F3. 如果是 16 × 16（4 × 4 宮）或更大的 n² × n² 數獨呢？
> 程式只需要把 9 換成 N = n²、宮的大小換成 n，bitmask 變成 N 位元。但搜尋空間成長極快，單純 MRV 在 25 × 25 時可能不夠。進一步的做法是把數獨建模成精確覆蓋（exact cover）問題：每個「(格, 數字)」選擇覆蓋四個限制（這格有數字、這列有這個數字、這行有、這宮有），用 Knuth 的 Algorithm X 搭配 Dancing Links 實作，它的「選擇覆蓋次數最少的限制」就是 MRV 的推廣，同時考慮「某個數字在某列只能放一個位置」這類隱藏的唯一性。

> [!question]- F4. 能不能在搜尋前先用推理減少分岔？
> 可以，這叫限制傳播（constraint propagation）。最常用的兩條規則：naked single（某格只剩一個候選，直接填入）與 hidden single（某個數字在某列／行／宮中只剩一個可放的格子，直接填入）。每填一格就更新相關的 bitmask，重複套用直到沒有新的推論，再進入分岔。MRV 已經隱含了 naked single，加上 hidden single 能讓大部分盤面完全不需要分岔。代價是每個節點的工作量變大，而且回溯時要撤銷整批推論，通常用「在遞迴前複製三組 bitmask」來實作最簡單（每組只有 27 個整數）。

> [!question]- F5. 如果只要檢查盤面目前是否合法（36. Valid Sudoku）呢？
> 不需要搜尋：掃描 81 格，對每個已填的數字檢查它所在的列、行、宮是否已經出現過，用三組集合或 bitmask，O(81)。詳見第 29 章核心題 4。注意「合法」不代表「有解」：一個沒有重複數字的盤面仍可能無解，要判斷有解必須跑 solver。面試官常把兩題連在一起問，先問 36 的檢查，再問「那怎麼解」，這時就把 36 的三組 bitmask 直接沿用成本題的狀態。

### 心得

關鍵突破是把「能不能填」做成 O(1) 的 bitmask 查詢，並用 MRV 每次挑候選最少的格子分岔，讓矛盾最早暴露。它和難題 1（N-Queens）是同一種結構：每個限制（列、行、宮或對角線）一份「已用」的狀態，做選擇時加入、回溯時移除；差別在於 N-Queens 的處理順序是固定的（一列一列），數獨則需要動態選擇順序。面試時先寫出固定順序的版本確保正確，再說明 MRV 為什麼能大幅減少分岔，以及撤銷時要注意 board 與空格列表都要復原。

## 難題 3｜282. Expression Add Operators｜Hard

### 題目

給一個只含數字的字串 `num` 和一個整數 `target`。你可以在 num 的相鄰數字之間插入 `'+'`、`'-'`、`'*'` 三種二元運算子之一，或什麼都不插入（讓相鄰數字連成一個多位數）。請回傳所有計算結果等於 target 的運算式，計算時依照一般的運算優先序（先乘後加減）。運算元**不能有前導零**：`"05"` 不是合法的運算元，但單獨的 `"0"` 可以。回傳順序不限。限制：`1 <= len(num) <= 10`，`-2³¹ <= target <= 2³¹ − 1`。

- 範例 1：`num = "123"`、`target = 6`，回傳 `["1+2+3", "1*2*3"]`。
- 範例 2：`num = "232"`、`target = 8`，回傳 `["2+3*2", "2*3+2"]`。
- 範例 3：`num = "105"`、`target = 5`，回傳 `["1*0+5", "10-5"]`；`"1*05"` 不合法，因為 `05` 有前導零。
- 範例 4（邊界）：`num = "00"`、`target = 0`，回傳 `["0+0", "0-0", "0*0"]`；`num = "3456237490"`、`target = 9191`，回傳 `[]`。

### 提示

> [!tip]- 提示 1
> 每次決定「下一個運算元有幾位數」以及「它前面放哪個運算子」。第一個運算元前面不放運算子。

> [!tip]- 提示 2
> 不要每次組出完整字串再 `eval`。一邊遞迴一邊維護目前的值。加法、減法很容易；乘法會破壞這個做法，因為 `2 + 3 * 2` 中的 3 已經被加進去了。

> [!tip]- 提示 3
> 額外記住「最後一個被加進去的項」`last`（含正負號）。遇到 `* x` 時，把 last 從總和中扣掉、換成 `last * x`：新值 = `value − last + last * x`，新的 last = `last * x`。連續乘法也成立。

### 詳解

**為什麼直覺做法不夠**。n 個數字之間有 n − 1 個間隙，每個間隙有 4 種選擇（三種運算子或不插入），共 4^(n−1) 種運算式，n = 10 時約 26 萬種。暴力做法是全部組出來、過濾前導零、再逐一求值，每次求值 O(n)，總共 O(n · 4ⁿ)，在 Python 中用 `eval` 會非常慢。更根本的問題是：相同的前綴（例如 `"1+2"`）會在幾萬個運算式中被重複計算。Backtracking 讓前綴的值沿著遞迴傳下去，每個節點只做 O(1) 的更新。

**加減很簡單，乘法是難點**。若只有加減，狀態只要 `(i, value)`：遇到 `+ x` 就 `value + x`，`- x` 就 `value − x`。乘法的優先序比加減高，`2 + 3 * 2` 不能算成 `(2 + 3) * 2`。觀察一個只有加減乘的運算式：它是幾個「乘積項」相加減，例如 `1 + 2 * 3 * 4 − 5 * 6` 是 `1`、`+24`、`−30` 三項。我們把目前這一項（含正負號）記成 `last`。遇到 `* x` 時，最後一項從 `last` 變成 `last * x`，而之前的項不受影響，所以新值 = `value − last + last * x`。遇到 `+ x` 或 `- x` 時開始新的一項，`last` 變成 `x` 或 `−x`。

**前導零**。從位置 i 開始取運算元 `num[i..j]`，若 `num[i] == '0'` 且 j > i，就是有前導零的多位數，不合法；而且更長的 j 也都不合法，所以直接 `break`。單獨的 `'0'`（j == i）是合法的。

**正確性**。每個合法的運算式都可以唯一分解成「第一個運算元，接著一串（運算子，運算元）」，而遞迴的每一層正好決定下一個（運算子，運算元）的組合，所以每個運算式恰好對應一條根到葉的路徑；`value` 與 `last` 的更新規則保證了每個節點上的 `value` 就是目前前綴依優先序計算的結果。走到字串結尾時比較 `value == target` 即可。

```text
num = "232"，target = 8；節點記錄 (path, value, last)
i=0 取 "2"          → ("2", 2, 2)
  i=1 取 "3"
    + → ("2+3", 5, 3)
        i=2 取 "2":  + → ("2+3+2", 7, 2)
                     - → ("2+3-2", 3, -2)
                     * → ("2+3*2", 5 - 3 + 3*2 = 8, 6)   ✓
    - → ("2-3", -1, -3)
        i=2 取 "2":  * → ("2-3*2", -1 - (-3) + (-3)*2 = -4, -6)
    * → ("2*3", 2 - 2 + 2*3 = 6, 6)
        i=2 取 "2":  + → ("2*3+2", 8, 2)   ✓
                     * → ("2*3*2", 6 - 6 + 6*2 = 12, 12)   ← 連續乘法：last 從 6 變 12
  i=1 取 "32"  + → ("2+32", 34, 32) …（i=3 結束，34 ≠ 8）
i=0 取 "23" … ；取 "232" → value 232 ≠ 8
```

`"2+3*2"` 那一步：在 `"2+3"` 時 value = 5 已經把 3 加進去了，last = 3 記住這一項；乘上 2 時先扣掉 3（回到 2），再加上 3 × 2 = 6，得到 8。`"2-3*2"` 展示負號：last = −3，乘上 2 後最後一項是 −6，value = −1 + 3 − 6 = −4，正確。`"2*3*2"` 展示連續乘法：last 從 6 變成 12，value 也從 6 變成 12。

### 解法

```python
import random
from itertools import product


def add_operators(num: str, target: int) -> list[str]:
    n = len(num)
    res, path = [], []

    def dfs(i: int, value: int, last: int) -> None:
        if i == n:
            if value == target:
                res.append("".join(path))
            return
        for j in range(i, n):
            if j > i and num[i] == "0":
                break                                  # 前導零：更長的也都不合法
            s = num[i:j + 1]
            x = int(s)
            if i == 0:
                path.append(s)
                dfs(j + 1, x, x)
                path.pop()
                continue
            for op, nv, nl in (("+", value + x, x),
                               ("-", value - x, -x),
                               ("*", value - last + last * x, last * x)):
                path.append(op)
                path.append(s)
                dfs(j + 1, nv, nl)
                path.pop()
                path.pop()

    dfs(0, 0, 0)
    return res


def brute(num, target):
    out = []
    for ops in product(["", "+", "-", "*"], repeat=len(num) - 1):
        expr = num[0] + "".join(o + d for o, d in zip(ops, num[1:]))
        operands = expr.replace("+", " ").replace("-", " ").replace("*", " ").split()
        if any(len(t) > 1 and t[0] == "0" for t in operands):
            continue
        if eval(expr) == target:
            out.append(expr)
    return sorted(out)


assert sorted(add_operators("123", 6)) == ["1*2*3", "1+2+3"]
assert sorted(add_operators("232", 8)) == ["2*3+2", "2+3*2"]
assert sorted(add_operators("105", 5)) == ["1*0+5", "10-5"]
assert sorted(add_operators("00", 0)) == ["0*0", "0+0", "0-0"]
assert add_operators("3456237490", 9191) == []
assert add_operators("5", 5) == ["5"] and add_operators("5", 3) == []
assert add_operators("2147483648", -2147483648) == []
for _ in range(150):
    s = "".join(random.choice("0123") for _ in range(random.randint(1, 6)))
    t = random.randint(-15, 15)
    assert sorted(add_operators(s, t)) == brute(s, t)
print("all tests passed")
```

### 複雜度與邊界

時間 O(n · 4ⁿ)：節點數最多是 4^(n−1) 種運算式的前綴總數，同階為 O(4ⁿ)；每個節點的 value／last 更新是 O(1)，但取子字串 `num[i:j+1]` 與 `int(s)` 是 O(n)，葉子 join 也是 O(n)，所以總共 O(n · 4ⁿ)。n = 10 時約 26 萬個葉子，可以接受。空間：遞迴深度 n，path 最長 2n − 1，額外空間 O(n)。邊界情況：前導零用 `break` 處理，`"0"` 本身合法；n = 1 時只有一個運算式，就是 num 本身；連續的 0（`"000"`）會產生很多合法運算式；Python 整數不溢位，但 10 位數的運算元可達 9999999999，乘積可達 10¹⁹ 以上，在 Java／C++ 中 `value` 與 `last` 要用 `long`，而且即使用 `long`，`last * x` 仍可能溢位，需要額外判斷。

### Follow-up

> [!question]- F1. 如果還允許整數除法 '/'（向零取整）呢？
> 除法和乘法同優先序，同樣作用在最後一項上：新的 last = `trunc(last / x)`，新值 = `value − last + 新的 last`。但要注意兩件事：x 為 0 時不能除，要跳過這個分支；向零取整在負數時和 Python 的 `//` 不同，要寫 `int(last / x)` 或 `-(-last // x)` 依符號處理。另外整數除法會讓「乘法再除法」不可交換，`6 / 4 * 2` 是 2 而不是 3，所以 last 必須依照從左到右的順序累積，本題的遞迴順序剛好就是從左到右，不需要額外處理。每個間隙的選擇從 4 種變成 5 種，時間變成 O(n · 5ⁿ) 量級。

> [!question]- F2. 如果運算子之外還允許任意加括號呢？
> 括號讓「最後一項」的技巧失效，因為任何子運算式都可以先算。標準做法是區間分治：對 `num` 的每個區間 [i, j] 計算「這段能算出的所有值」，枚舉最後一個運算子的位置 k，左右兩段的所有值兩兩組合，再加上整段不插運算子當成一個數的情況（需檢查前導零）；用 memoization 存每個區間的值集合。這是 241. Different Ways to Add Parentheses 的推廣，屬於區間 DP（第 23 章），值集合的大小可能是指數級，但比列舉所有括號方式（Catalan 數）好得多。

> [!question]- F3. 如果只允許 '+' 和 '-'、且每個數字必須單獨作為運算元，問有幾種方式能得到 target 呢？
> 這就是 494. Target Sum（第 23 章核心題 2）：每個數字前面選正號或負號，2ⁿ 種。計數只取決於「處理到第幾個數字、目前的和」，可以用 DP：`dp[i][s]` 是前 i 個數字和為 s 的方法數，時間 O(n · S)，S 是可能的和的範圍。也可以轉成子集和：設正號那組的和為 P，則 P − (total − P) = target，P = (total + target) / 2，變成「和為 P 的子集有幾個」的 0/1 背包。本題之所以不能這樣做，是因為乘法讓 value 不再只由「位置與目前和」決定，還需要 last，而且值的範圍很大。

> [!question]- F4. 如何讓每個節點的成本真正是 O(1)，避免反覆取子字串與轉整數？
> 在 `for j` 迴圈中逐位累積運算元：`x = x * 10 + int(num[j])`，不必每次 `int(num[i:j+1])`；path 用 list 存 token，只在葉子 `"".join`。這樣內部節點的工作是 O(1)，只有記錄答案時 O(n)，總時間變成 O(4ⁿ + 答案數 · n)。另一個常數優化是剪枝：若剩下的數字全部連成一個數、再以最大的方式加上去都達不到 target，就提前返回；但乘法讓上下界很難估得緊（乘以 0 可以清掉一切），實務上效果有限，面試時說明即可。

### 心得

關鍵突破是用 `last` 記住最後一個乘積項，讓乘法的優先序也能在 O(1) 內撤銷與重算：`value − last + last * x`。它和本章其他題的差別在於「狀態不只是 path」：回溯模板裡要傳遞的是 `(i, value, last)` 三元組，而撤銷由遞迴參數自動完成（每一層的 value、last 是區域變數），只有 path 需要手動 pop。面試時先說清楚 4^(n−1) 的搜尋空間與暴力 eval 的成本，再用 `"2+3*2"` 一個例子解釋 last 的作用，最後補上前導零的 break；這三點講清楚，程式本身很短。

## 難題 4｜698. Partition to K Equal Sum Subsets｜Medium

### 題目

給一個正整數陣列 `nums` 和整數 k，判斷能否把 nums 的所有元素分成 k 個**非空**的子集，使每個子集的元素和都相等。每個元素必須恰好屬於一個子集。回傳 True 或 False。限制：`1 <= k <= len(nums) <= 16`，`1 <= nums[i] <= 10⁴`。

- 範例 1：`nums = [4, 3, 2, 3, 5, 2, 1]`、`k = 4`，回傳 `True`：總和 20，每組 5，分法 `{5}`、`{1, 4}`、`{2, 3}`、`{2, 3}`。
- 範例 2：`nums = [1, 2, 3, 4]`、`k = 3`，回傳 `False`：總和 10 不能被 3 整除。
- 範例 3：`nums = [2, 2, 2, 2, 3, 4, 5]`、`k = 4`，回傳 `False`：總和 20、每組 5，但 4 需要搭配 1，而陣列中沒有 1。
- 範例 4（邊界）：`k = 1` 時一定是 `True`；`nums = [4, 4, 3, 3, 2, 2]`、`k = 2` 回傳 `True`（`{4, 3, 2}` 兩組）。

### 提示

> [!tip]- 提示 1
> 先做必要條件：總和必須能被 k 整除，且最大的元素不能超過每組的目標和 `target = total / k`。之後這是一個 NP-hard 的分組問題，n ≤ 16 就是在暗示要搜尋。

> [!tip]- 提示 2
> 一個一個元素決定它要放進哪個桶子，桶子的和不能超過 target。搜尋空間是 kⁿ，要怎麼大量剪枝？想想：兩個目前都是空的桶子，把下一個數放進哪一個有差別嗎？

> [!tip]- 提示 3
> 三個剪枝：元素由大到小排序（大的數最難放，衝突早暴露）；同一層中，和目前相同的桶子只試一個（包含所有空桶子只試一個）；放進去會超過 target 就跳過。另一種解法是 bitmask DP：`dp[mask]` 表示用 mask 中的元素能否依序填滿若干個桶子，目前的桶子和是 `sum(mask) % target`。

### 詳解

**為什麼直覺做法不夠**。一個常見的錯誤直覺是貪婪：由大到小排序，每個桶子盡量塞最大的、放得下的數，塞滿一個再開下一個。範例 4 的 `[4, 4, 3, 3, 2, 2]`、k = 2、target = 9 就會失敗：第一個桶子貪婪地放 4、4，和是 8，剩下的 3、2 都放不進去，於是回報 False；但正確的分法是 `{4, 3, 2}` 兩組。分組問題是 NP-hard（k = 2 時就是 partition problem），沒有已知的多項式演算法，n ≤ 16 的限制正是在告訴你：用搜尋，但要剪得夠狠。

**搜尋空間一：以元素為層，選擇放進哪個桶子**。第 i 層決定 `nums[i]` 要放進 k 個桶子中的哪一個，條件是放進去之後不超過 target。所有元素都放完時，因為每個桶子 ≤ target 而總和恰好是 k · target，每個桶子一定都恰好等於 target，所以不需要再檢查。這棵樹最多有 kⁿ 個葉子，16 個元素、k = 4 時是 4¹⁶ ≈ 4 × 10⁹，不剪枝不可能跑完。

**三個剪枝**。第一，**對稱破除**：桶子之間沒有編號的意義，如果兩個桶子目前的和相同，把 `nums[i]` 放進其中任何一個，長出來的子樹都是同構的，只需要試一個。實作上在每一層用一個 `seen` 集合記錄「已經試過的桶子和」，遇到相同的和就跳過；所有空桶子的和都是 0，所以這也自動處理了「放進空桶子只試一次」。這個剪枝在無解的輸入上最重要，它能讓節點數少好幾個數量級。第二，**由大到小排序**：大的數可放的桶子少，先放它們能讓樹的上層分支數變小，而且「放不下」的矛盾在淺層就會暴露。第三，**超過 target 就跳過**，這是基本的可行性剪枝。

**搜尋空間二：bitmask DP**。換個角度：如果我們規定「先把一個桶子填滿，才開始填下一個」，那麼目前的狀態只取決於「哪些元素已經用掉了」（mask），因為已用元素的總和 `sum(mask)` 決定了已經填滿幾個桶子（`sum(mask) // target`）以及目前桶子裡有多少（`sum(mask) % target`）。定義 `dp[mask]` 為「mask 中的元素能否按這個規則放好」，轉移是對每個不在 mask 中的 i，若 `sum(mask) % target + nums[i] <= target`，則 `dp[mask | 1 << i]` 為真。最後回傳 `dp[全集]`。時間 O(n · 2ⁿ)，n = 16 時約一百萬個狀態，與 k 無關，是有保證的最差複雜度；backtracking 則是在有解時通常非常快，最差時沒有好的保證。

```text
nums = [4, 4, 3, 3, 2, 2]（已由大到小），k = 2，target = 9
桶子狀態 [B0, B1]；seen 記錄這一層試過的桶子和

i=0 放 4：B0=0、B1=0 和相同 → 只試 B0            [4, 0]
i=1 放 4：B0=4 → [8, 0]；B1=0 → [4, 4]（和不同，都要試）
  ├ [8, 0] i=2 放 3：B0 8+3>9 ✗；B1 → [8, 3]
  │   i=3 放 3：B0 ✗；B1 → [8, 6]
  │   i=4 放 2：B0 ✗；B1 → [8, 8]
  │   i=5 放 2：B0 ✗；B1 8+2>9 ✗ → 失敗，一路回溯
  └ [4, 4] i=2 放 3：B0=4、B1=4 和相同 → 只試 B0  [7, 4]
      i=3 放 3：B0 7+3>9 ✗；B1 → [7, 7]
      i=4 放 2：B0=7、B1=7 相同 → 只試 B0          [9, 7]
      i=5 放 2：B0 已滿 ✗；B1 → [9, 9] ✓ 回傳 True
```

整個搜尋中有三次「和相同只試一個」：i = 0、i = 2、i = 4，每次都把分支數減半；若沒有這個剪枝，`[4, 4]` 之後放 3 時會分別試 B0 和 B1，兩者完全對稱。左邊那條路徑就是貪婪的選擇（先把 B0 塞到 8），backtracking 在發現它走不通之後回到 i = 1，換成 `[4, 4]`，這正是貪婪做不到的事。

### 解法

```python
import random
from itertools import product


def can_partition_k_subsets(nums: list[int], k: int) -> bool:
    total = sum(nums)
    if total % k:
        return False
    target = total // k
    nums = sorted(nums, reverse=True)                # 大的先放，矛盾早暴露
    if nums[0] > target:
        return False
    buckets = [0] * k

    def dfs(i: int) -> bool:
        if i == len(nums):
            return True                              # 每桶 <= target 且總和 = k·target
        seen = set()
        for b in range(k):
            s = buckets[b]
            if s + nums[i] > target or s in seen:
                continue                             # 超過、或和相同的桶子已經試過
            seen.add(s)
            buckets[b] += nums[i]
            if dfs(i + 1):
                return True
            buckets[b] -= nums[i]
        return False

    return dfs(0)


def can_partition_k_subsets_dp(nums: list[int], k: int) -> bool:
    """bitmask DP：dp[mask] = mask 中的元素能否「一桶填滿再填下一桶」地放好。"""
    total, n = sum(nums), len(nums)
    if total % k:
        return False
    target = total // k
    if max(nums) > target:
        return False
    dp = [False] * (1 << n)
    subset_sum = [0] * (1 << n)
    dp[0] = True
    for mask in range(1 << n):
        if not dp[mask]:
            continue
        cur = subset_sum[mask] % target              # 目前這一桶已經裝了多少
        for i in range(n):
            bit = 1 << i
            if mask & bit or cur + nums[i] > target:
                continue
            nxt = mask | bit
            if not dp[nxt]:
                dp[nxt] = True
                subset_sum[nxt] = subset_sum[mask] + nums[i]
    return dp[(1 << n) - 1]


def brute(nums, k):
    total = sum(nums)
    if total % k:
        return False
    for assign in product(range(k), repeat=len(nums)):
        sums = [0] * k
        for x, b in zip(nums, assign):
            sums[b] += x
        if len(set(sums)) == 1:
            return True
    return False


assert can_partition_k_subsets([4, 3, 2, 3, 5, 2, 1], 4) is True
assert can_partition_k_subsets([1, 2, 3, 4], 3) is False
assert can_partition_k_subsets([2, 2, 2, 2, 3, 4, 5], 4) is False
assert can_partition_k_subsets([4, 4, 3, 3, 2, 2], 2) is True
assert can_partition_k_subsets([7], 1) is True
assert can_partition_k_subsets([10**4] * 16, 16) is True
assert can_partition_k_subsets([1] * 15 + [10**4], 4) is False
assert can_partition_k_subsets_dp([4, 3, 2, 3, 5, 2, 1], 4) is True
assert can_partition_k_subsets_dp([4, 4, 3, 3, 2, 2], 2) is True
for _ in range(400):
    arr = [random.randint(1, 8) for _ in range(random.randint(1, 7))]
    kk = random.randint(1, min(4, len(arr)))
    expect = brute(arr, kk)
    assert can_partition_k_subsets(arr, kk) == expect == can_partition_k_subsets_dp(arr, kk)
print("all tests passed")
```

### 複雜度與邊界

Backtracking 版本最差 O(kⁿ)，對稱破除與排序讓實際節點數小很多（在一組 n = 16、k = 5 的隨機無解輸入上實測，有無 `seen` 剪枝的節點數相差上百倍），但沒有好的理論保證；空間 O(n + k)。Bitmask DP 版本時間 O(n · 2ⁿ)、空間 O(2ⁿ)，n = 16 時約 10⁶ 個狀態，最差情況有保證，但在 Python 中常數較大。邊界情況：總和不能被 k 整除、或最大元素大於 target，都要在搜尋前直接回傳 False；k = 1 一定成立；k = n 時每個元素必須相等；所有元素都是正數這個前提很重要，「每桶 ≤ target 且總和正確 ⇒ 每桶恰好 = target」這一步依賴它，也是「超過 target 就跳過」剪枝成立的原因。

### Follow-up

> [!question]- F1. 用火柴拼出一個正方形呢（473. Matchsticks to Square）？
> 這就是 k = 4 的特例：每根火柴必須用上，四條邊等長，等價於把長度分成 4 組和相等的子集。程式直接呼叫 `can_partition_k_subsets(matchsticks, 4)`，同樣的三個剪枝都適用。限制是 n ≤ 15、長度可達 10⁸，因為長度很大，任何「以和為狀態」的 DP 都不可行，只能用 backtracking 或 bitmask DP（O(n · 2ⁿ)，與長度無關）。這也是一個好例子：看到 n ≤ 15 或 16，就該想到 2ⁿ 的狀態或強剪枝的搜尋。

> [!question]- F2. 如果要回傳實際的分組呢？
> Backtracking 版本中額外維護 `owner[i]`，記錄每個元素被放進哪個桶子（排序前先保存原始索引）；回傳 True 時 owner 就是一個合法分組，按桶子收集即可，O(n)。Bitmask DP 版本則要記錄每個 dp 狀態是從哪個 mask、加入哪個 i 轉移來的（parent 陣列），從全集一路往回追；因為是「一桶填滿再填下一桶」，追蹤時每當累積和到達 target 的倍數就切一組。兩者的額外空間分別是 O(n) 和 O(2ⁿ)。

> [!question]- F3. 如果不要求相等，而是把工作分給 k 個工人，最小化最大的工作量呢（1723. Find Minimum Time to Finish All Jobs）？
> 這是最佳化版本，可以用 branch and bound：同樣把工作由大到小一個一個分給工人，維護目前的最佳答案 best，若某個工人的負擔 + 這份工作 ≥ best 就剪掉，同樣用「負擔相同的工人只試一個」做對稱破除。另一個做法是對答案二分（第 8 章）：猜一個上限 X，問「每人 ≤ X 時能否分完」，判定就是本題的 backtracking 把 target 換成 X（不要求恰好）。也可以用子集 DP：`f[j][mask]` 為前 j 個工人完成 mask 的最小最大值，列舉子集 O(k · 3ⁿ)。

> [!question]- F4. 如果 k = 2 呢？
> 變成 416. Partition Equal Subset Sum（第 23 章核心題 1）：只要找到一個子集的和是 total / 2，剩下的自動也是。這時不需要搜尋，0/1 背包 DP 用一個布林陣列或一個大整數的 bitset 就能在 O(n · total) 時間內完成，偽多項式（pseudo-polynomial），與 n 的指數無關。這個對比說明：k = 2 時「一個子集」就決定了整個分法，所以可以只追蹤和；k ≥ 3 時要同時追蹤多個桶子的和，狀態爆炸，才回到 bitmask 或搜尋。

> [!question]- F5. 為什麼一定要由大到小排序？由小到大會怎樣？
> 由小到大時，前幾層放的都是小數，它們幾乎可以放進任何桶子，樹的上層分支很多；等到後面要放大數時才發現某個大數放不下，這時要回溯很多層，而上面那些小數的各種排列都會被重新試一次。由大到小則相反：大數只能放進少數幾個桶子，上層分支少，而且「4 需要搭配 1 但沒有 1」這種矛盾會在放完大數之後很快暴露。這是「先處理限制最多的變數」原則的又一個例子，和難題 2 的 MRV、難題 5 的「先試最大正方形」是同一種想法。

### 心得

關鍵突破是對稱破除：桶子沒有身份，和相同的桶子只試一個，讓指數級的搜尋在無解時也能很快結束；再配合由大到小排序讓矛盾早暴露。它和本章其他題的差別是「選擇」對應的是桶子而不是元素，而 bitmask DP 的版本則把它和第 24 章連起來：當「已用元素的集合」就足以決定未來時，2ⁿ 個狀態可以全部記下來。面試時先講必要條件（整除、最大值），再講桶子 backtracking 的三個剪枝，最後提 O(n · 2ⁿ) 的 DP 作為有保證的替代方案，並能說出兩者在有解／無解時的表現差異。

## 難題 5｜1240. Tiling a Rectangle with the Fewest Squares｜Hard

### 題目

給一個 n × m 的矩形，用邊長為整數的正方形把它**恰好鋪滿**（不重疊、不超出邊界），正方形的大小可以各不相同。回傳最少需要幾個正方形。限制：`1 <= n, m <= 13`。

- 範例 1：`n = 2, m = 3`，回傳 `3`：一個 2 × 2 加兩個 1 × 1。
- 範例 2：`n = 5, m = 8`，回傳 `5`：5 × 5、3 × 3、2 × 2、1 × 1、1 × 1。
- 範例 3：`n = 11, m = 13`，回傳 `6`。這是一個「切一刀分成兩個矩形」永遠得不到的答案（見詳解）。
- 範例 4（邊界）：`n = m` 時回傳 `1`；`n = 1` 時回傳 `m`。

### 提示

> [!tip]- 提示 1
> 兩個常見直覺都不對：「每次放最大的正方形」是貪婪，「切一刀變成兩個小矩形再遞迴」是 DP。先找出它們在 11 × 13 上為什麼失敗。

> [!tip]- 提示 2
> 改成填格子：每次找「最低、最靠左」還沒被覆蓋的格子，它一定是某個正方形的左下角。所以只要決定那個正方形的邊長。已覆蓋的區域可以用每一行的高度（skyline，天際線）描述。

> [!tip]- 提示 3
> 找最低的高度 h 和它最左的位置 i，往右數出連續同高的寬度 w，可放的邊長是 1 到 min(w, n − h)，從大到小試。用全域最佳解剪枝：目前個數已經 ≥ best 就返回；best 的初始值用「切一刀」的 DP 求，它一定是一個可行的上界。

### 詳解

**為什麼直覺做法不夠**。貪婪「先放最大的正方形」在 11 × 13 上會放一個 11 × 11，剩下 11 × 2 的長條，只能用五個 2 × 2 和兩個 1 × 1 填滿，共 8 個。另一個看起來更聰明的做法是 guillotine DP（一刀切 DP）：`f(a, b)` 等於把 a × b 矩形橫切或直切成兩塊的所有方式中，兩塊的 f 相加的最小值（a == b 時為 1）。它在 13 以內的所有尺寸中只有 11 × 13 算錯，答案是 8，但正確答案是 6。原因是最佳鋪法中**沒有任何一條直線能把整個矩形切成兩塊而不切過正方形**，見下圖。這種結構只有搜尋能找到。

```text
11 × 13 的最佳鋪法（6 個正方形）；每個字母是一個正方形
列 10  E E E E F F F F D D D D D
列  9  E E E E F F F F D D D D D
列  8  E E E E F F F F D D D D D
列  7  E E E E F F F F D D D D D      A = 7×7，B = 6×6，C = 1×1
列  6  A A A A A A A C D D D D D      D = 5×5，E = 4×4，F = 4×4
列  5  A A A A A A A B B B B B B
列  4  A A A A A A A B B B B B B
 …     （列 0 到 5 同列 5）
任何一條水平或垂直的直線都會切過某個正方形 → 一刀切 DP 找不到它
```

**突破點：每次填「最低最左」的空格**。把列（高度）從下往上數。在任何一個部分鋪好的狀態下，找出最低、且在同一高度中最靠左的空格 (h, i)。覆蓋它的正方形，左下角一定就是 (h, i)：如果左下角在更左邊，正方形會蓋到同一高度、更左邊的格子，但那些格子已經被覆蓋了；如果左下角在更低處，會蓋到更低的格子，那些也已經被覆蓋了（因為 h 是最低的空格高度）。所以每一步只需要決定一個數：邊長 s。

**為什麼狀態是一條天際線**。因為每次都從最低處開始放，而且只能放在「與 i 同高、連續的那幾行」上（若正方形跨到更高的行就會重疊），放完之後每一行被覆蓋的部分仍然是從底部開始連續的一段。所以整個狀態可以用長度為 m 的陣列 `heights` 描述：第 j 行已經被覆蓋到多高。找最低最左就是 `h = min(heights)`、`i = heights.index(h)`；可放的最大邊長 `w` 是從 i 往右連續高度為 h 的行數，同時不能超出上邊界 n − h。

**剪枝**。這是求最小值的搜尋，用 branch and bound：維護目前找到的最佳解 best，若已用的正方形數 ≥ best 就返回。剪枝的威力取決於 best 有多好，所以用 guillotine DP 的結果當初始值（它一定可行），再從大到小嘗試邊長，讓好的解更早被找到、best 更早變小。在 13 × 13 以內的所有尺寸上，這個搜尋都只需要很短的時間。

```text
n = 2（高）、m = 3（寬）；heights 是每一行已覆蓋的高度
初始 best = guillotine DP 的 3
heights [0,0,0]  h=0, i=0, 同高寬度 3, 上限 n-h=2 → 邊長試 2、1
├ s=2 → [2,2,0]  count=1
│   h=0, i=2, 寬度 1 → s=1 → [2,2,1] count=2
│      h=1, i=2 → s=1 → [2,2,2]，進入 dfs(3) 時 3 >= best → 直接返回，不更新
└ s=1 → [1,0,0]  count=1
    h=0, i=1, 寬度 2, 上限 2 → s=2 → [1,2,2] count=2
       h=1, i=0, 寬度 1 → s=1 → [2,2,2] count=3 >= best → 剪枝
    …其餘分支 count 很快到達 3，全部剪掉
答案 3
```

### 解法

```python
from functools import cache


def tiling_rectangle(n: int, m: int) -> int:
    if n > m:
        n, m = m, n                              # 讓 heights 沿較長的一邊，深度較淺

    @cache
    def guillotine(a: int, b: int) -> int:       # 一刀切 DP：一定可行的上界
        if a == b:
            return 1
        best = a * b
        for c in range(1, a // 2 + 1):
            best = min(best, guillotine(c, b) + guillotine(a - c, b))
        for c in range(1, b // 2 + 1):
            best = min(best, guillotine(a, c) + guillotine(a, b - c))
        return best

    best = guillotine(n, m)
    heights = [0] * m                            # 每一行已覆蓋的高度（上限 n）

    def dfs(count: int) -> None:
        nonlocal best
        if count >= best:
            return                               # branch and bound
        h = min(heights)
        if h == n:
            best = count                         # 全部鋪滿
            return
        i = heights.index(h)                     # 最低最左的空格在 (h, i)
        j = i
        while j < m and heights[j] == h and j - i < n - h:
            j += 1                               # 同高且不超出上邊界的最大寬度
        for s in range(j - i, 0, -1):            # 大的先試，較快找到好解
            for x in range(i, i + s):
                heights[x] += s
            dfs(count + 1)
            for x in range(i, i + s):
                heights[x] -= s

    dfs(0)
    return best


def guillotine_only(n, m):
    @cache
    def g(a, b):
        if a == b:
            return 1
        return min([g(c, b) + g(a - c, b) for c in range(1, a)] +
                   [g(a, c) + g(a, b - c) for c in range(1, b)])
    return g(n, m)


assert tiling_rectangle(2, 3) == 3
assert tiling_rectangle(5, 8) == 5
assert tiling_rectangle(11, 13) == 6
assert tiling_rectangle(13, 11) == 6
assert tiling_rectangle(7, 7) == 1
assert tiling_rectangle(1, 13) == 13
assert guillotine_only(11, 13) == 8                    # 一刀切 DP 在這裡算錯
mismatch = [(a, b) for a in range(1, 14) for b in range(a, 14)
            if tiling_rectangle(a, b) != guillotine_only(a, b)]
assert mismatch == [(11, 13)]                          # 13 以內唯一的例外
print("all tests passed")
```

### 複雜度與邊界

搜尋是指數級，沒有好的封閉上界；粗略的上界是：深度最多 n · m（全用 1 × 1），每層最多 min(n, m) 個分支。實際上 branch and bound 加上好的初始上界，讓 13 以內的每個尺寸都在毫秒級完成，上面的測試把所有 91 種尺寸都跑了一遍。每個節點的工作是 O(m)（找最小值與更新 heights）。Guillotine DP 本身是 O(n · m · (n + m))。空間：遞迴深度最多 n · m，heights 是 O(m)，DP 表 O(n · m)。邊界情況：n == m 時 guillotine 直接回傳 1，搜尋放下一個 n × n 之後 count = 1 ≥ best 就被剪掉，回傳初始值 1；n = 1 時只能用 1 × 1；交換 n、m 不影響答案，但讓 heights 沿長邊、每個正方形的高度上限是短邊，分支數較少。

### Follow-up

> [!question]- F1. 如果要輸出實際的鋪法呢？
> 搜尋時多維護一個 `placed` 串列，每放一個正方形就 append `(h, i, s)`（左下角高度、行、邊長），回溯時 pop；每次更新 best 時把 placed 複製一份存起來。最後存下的就是一個最佳鋪法，上面 11 × 13 的圖就是這樣畫出來的。要注意初始 best 來自 guillotine DP，若搜尋從未找到比它更好的解，就沒有記錄到任何鋪法；這時要另外從 DP 回推切法（記錄每個 f(a, b) 的最佳切點），或把初始 best 設成 DP 值 + 1 讓搜尋至少找到一個等值的解。

> [!question]- F2. 能不能加上更強的下界剪枝？
> 可以。目前已用 count 個，剩下未覆蓋的面積是 A = n · m − Σ heights，每個正方形的面積最多 min(n, m)²，所以至少還要 ⌈A / min(n, m)²⌉ 個；若 `count + ⌈A / s_max²⌉ >= best` 就剪掉。更緊的下界是用「目前能放的最大正方形」取代 min(n, m)，但要小心它必須真的是之後所有正方形邊長的上界（例如剩下區域中最大的空白正方形）。下界越緊、剪得越多，這和 A* 搜尋中的 admissible heuristic（不高估的估計）是同一個概念。

> [!question]- F3. 能不能對 skyline 狀態做 memoization？
> 可以：狀態就是 `tuple(heights)`，「從這個天際線鋪滿剩下區域的最少個數」只取決於它本身，不取決於怎麼走到這裡，所以可以 `@cache`。可能的天際線數上界是 (n + 1)^m，但實際可達的遠少於此。要注意 memoization 和 branch and bound 不容易同時用：被 `count >= best` 剪掉的子樹沒有算出真正的值，不能當作答案存起來。常見做法是二選一：純 memoization（每個狀態算出精確值），或純 branch and bound；本題的規模下後者已經足夠快。

> [!question]- F4. 如果規定只能用「一刀切」的方式（guillotine cut）分割呢？
> 那就正好是解法中的 guillotine DP：`f(a, b) = 1` 若 a == b，否則取所有橫切 `f(c, b) + f(a − c, b)` 與直切 `f(a, c) + f(a, b − c)` 的最小值。狀態 n · m 個，每個 O(n + m) 個切點，總時間 O(n · m · (n + m))，n、m 到幾百都可以。這也是一個好的面試敘事：先給出這個多項式 DP，說明它在 11 × 13 上給出 8，再指出最佳解不是一刀切的結構，所以必須搜尋。這比直接寫 backtracking 更能展現你的判斷過程。

> [!question]- F5. 如果不是求最少個數，而是問「用 1 × 2 的骨牌鋪滿 n × m 有幾種方式」呢？
> 計數問題不能用 branch and bound，但同樣的「每次填最低最左（或逐格掃描的第一個）空格」觀念能變成 DP：逐格掃描時，未來只受「目前這條掃描線上哪些格子已被上一排伸出的骨牌占用」影響，這是一個 m 位元的 bitmask，稱為 broken profile DP（輪廓線 DP），時間 O(n · m · 2^m)。詳見第 24 章。這個對比說明：同一個「填最左上的空格」框架，求最佳解時配搜尋與剪枝，求計數時若狀態能壓縮就配 DP。

### 心得

關鍵突破是「最低最左的空格一定是某個正方形的左下角」，把一個二維的擺放問題變成每步只選一個邊長的搜尋，狀態只是一條天際線；再用 guillotine DP 當初始上界做 branch and bound。它是本章「求最佳值的搜尋」的代表：和難題 4 一樣先放大的，和難題 2 一樣靠好的選擇順序讓搜尋早點收斂。面試時，先提 guillotine DP 並主動指出 11 × 13 的反例，說明為什麼需要搜尋；接著畫出 skyline 與「最低最左」的論證；最後說明剪枝與從大到小的順序。這題的 n、m ≤ 13 本身就是提示：作者知道它只能靠搜尋。

## Pattern 歸納

| 變形 | 辨識方式 | 關鍵技巧 | 本章題目／其他經典題 |
|---|---|---|---|
| 子集與組合 | 「所有子集／組合」，`[1, 2]` 與 `[2, 1]` 算同一個 | `start` 參數讓索引遞增；可重複用時下一層傳 `i` | 核心題 1（78）、核心題 3（39）、77、90、40、216 |
| 排列 | 「所有排列」、順序不同算不同 | `used` 陣列或原地 swap；有重複時排序加 `not used[i-1]` | 核心題 2（46）、47、526（第 24 章核心題 3） |
| 笛卡兒積與受限生成 | 每一位有固定幾種選擇 | 深度 = 位置；可加計數限制（括號數、字母大小寫） | 核心題 4（17）、22 Generate Parentheses、784 |
| 字串切分 | 在間隙插入運算子或切點 | 逐位延伸運算元、前導零 `break`、狀態隨參數傳遞 | 難題 3（282）、131 Palindrome Partitioning、93 Restore IP Addresses |
| 網格路徑 | 不重複走格子拼出字串或走完全部格子 | 原地標記、回來復原；字母數量預檢 | 核心題 5（79）、212（第 13 章難題 1）、980 Unique Paths III |
| 限制滿足 | 填格子／放棋子，滿足列、行、宮、對角線限制 | 每組限制一份 set 或 bitmask，O(1) 檢查；MRV 選格子 | 難題 1（51）、難題 2（37）、52 |
| 分組與裝箱 | 「能否分成 k 組」、n ≤ 16 | 由大到小排序、和相同的桶子只試一個；或 bitmask DP | 難題 4（698）、473、1723、2305 |
| 求最佳值的搜尋 | 最少／最多，但沒有可分解的子結構 | branch and bound、好的初始上界、下界估計、先試大的 | 難題 5（1240）、1986（第 24 章核心題 4） |
| 列出所有解，但子問題會重複 | 列出所有「切法」且後綴的切法可共用 | 先用 DP 判斷哪些後綴可行，再只沿可行分支回溯 | 140 Word Break II、核心題 4 F5 |

**下限與上限**。最簡單的形式是子集與排列：決策樹的結構固定，沒有剪枝，考的是模板寫對（複製 path、撤銷選擇、`i + 1` 與 `start`），以及能說出 O(n · 2ⁿ) 與 O(n · n!) 為什麼已經是最佳。中間層是加上限制與去重：39、40、90、47 考的是「排序之後 `break`」與「同層去重」這兩個小技巧，79 考的是 visited 只屬於目前路徑。上限的題目難在三個地方：第一，**狀態設計**，例如 282 的 `last` 讓乘法能 O(1) 撤銷、1240 的天際線讓二維擺放變成一維陣列；第二，**剪枝的論證**，例如 698 的對稱破除為什麼不會漏解、1240 的「最低最左必是左下角」；第三，**選擇順序**，例如數獨的 MRV、分組的由大到小，它們不影響正確性，卻決定能不能在時限內跑完。

**與其他 pattern 的關係**。Backtracking 是 DFS（第 15 章）在「隱式決策樹」上的應用：圖的 DFS 用全域 visited 確保每個節點只走一次，backtracking 則刻意讓同一個狀態可以從不同路徑重新進入，所以 visited 要撤銷。它和樹的遞迴（第 12 章）共用「函式回傳時恢復狀態」的思維。當子問題只由一個小狀態決定、不同路徑會走到相同狀態時，backtracking 加上 memoization 就是 DP（第 21–24 章）：39 的計數版是 518、698 的 bitmask 版是第 24 章的典型、79 允許重複用格子時變成 `(r, c, k)` 的 DP。和 trie（第 13 章）結合，可以在字串搜尋中做前綴剪枝（212、核心題 4 F1）。和 binary search（第 8 章）結合，「最小化最大值」可以二分答案、用 backtracking 做判定（難題 4 F3）。

**容易混淆之處**。第一，「列出所有」才是 backtracking 的主場；只問「有幾種」或「最少幾個」時，先檢查能不能 DP（39 對 518、322），能 DP 就不要搜尋。第二，「最短路徑」類的問題（最少步數）通常是 BFS（第 15 章），用 DFS 加回溯去找最短路徑會走遍所有路徑，指數級又沒有必要。第三，看起來能貪婪的分組與鋪磚問題（698、1240）往往是 NP-hard，貪婪有反例；看到 n ≤ 16、≤ 13 這種小得不自然的限制，就該懷疑題目要你搜尋，並先舉出貪婪的反例來說服自己與面試官。

## 本章重點整理

- Backtracking 是在決策樹上做 DFS：做選擇、遞迴、撤銷，三行一組；每一題先回答「每一層在決定什麼、有哪些選擇、何時剪枝」。
- 核心 invariant：進入與離開 `dfs` 時，共用狀態（path、used、集合、網格標記）完全相同；記錄答案時一定要複製 `path[:]`。
- 組合型用 `start` 讓索引遞增（可重複用時下一層傳 `i`，否則傳 `i + 1`）；排列型用 `used` 或原地 swap；每位選擇固定時深度就是位置。
- 去重：先排序，同一層跳過與前一個相同的值，條件是 `i > start`（組合）或 `not used[i - 1]`（排列），不同層的相同值不能跳過。
- 複雜度 ≈ 節點數 × 每節點成本 + 答案數 × 複製成本；子集 O(n · 2ⁿ)、排列 O(n · n!)，列出全部答案時這已是下限。
- 五種剪枝：可行性（排序後 `break`）、上界（branch and bound）、去重、對稱破除（相同狀態的桶子只試一個）、搜尋順序（MRV、大的先放）。
- 網格路徑的 visited 只屬於目前路徑，原地改成 `'#'` 並在回來時還原；因為狀態包含整個 visited 集合，不能對 `(r, c, k)` memoize。
- 限制滿足題（N-Queens、數獨）為每組限制維護一份 set 或 bitmask，讓「能不能放」變成 O(1)；對角線用 `r − c`、`r + c` 編號。
- 狀態不只是 path 時（282 的 `value` 與 `last`），把它們放進遞迴參數，撤銷就由函式返回自動完成。
- 分組問題（698）先檢查整除與最大值，再用由大到小與對稱破除；n ≤ 16 時 O(n · 2ⁿ) 的 bitmask DP 是有保證的替代方案。
- 求最佳值的搜尋（1240）用 branch and bound，初始上界取一個可行解（例如 guillotine DP），並用「最低最左的空格」讓每步只剩一個決定。
- 只問計數或最佳值、而子問題由小狀態決定時，backtracking 應該改成 DP；問最少步數時通常是 BFS。
